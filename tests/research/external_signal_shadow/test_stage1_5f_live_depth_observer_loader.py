import json

import pytest

from configs import base


from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
    build_first_seen_watermark_diagnostics,
    classify_event_symbol_eligibility,
    classify_event_symbol_eligibility_with_diagnostics,
    classify_live_depth_evidence_basis,
    delayed_launch_event_symbol_is_post_bootstrap_watermark,
    flatten_event_symbols,
    historical_anchor_classification_allowed,
    iter_stage1_5d_event_rows,
    make_event_symbol_id,
    make_stable_event_symbol_key,
    merge_first_seen_watermark_fields,
    normalize_anchor_candidates,
    normalize_event_symbol_identity,
    re_resolve_pending_anchor,
    resolve_announcement_capture_time_ms,
    resolve_depth_observation_anchor_ms,
    resolve_observation_age_base_ms,
    upsert_pending_state_with_event_revision,
    validate_stage1_5d_summary,
)
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import EventSymbolState, Watermark



def test_only_futures_contract_launch_is_eligible():
    event = {
        "event_id": "e1",
        "event_type": "spot_listing",  # Wrong type
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    # mock exchangeinfo_state (available=True, symbols=["ABCUSDT"])
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    # Classify
    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "rejected"
    assert reason == "wrong_event_type"


def test_event_age_gate_skips_old_event():
    # Age exceeds 15min (900_000 ms)
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    # now is 1000 + 15*60*1000 + 1 = 901001
    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000 + 15 * 60 * 1000 + 1, w, exinfo, {})
    assert status == "pending"
    assert reason == "pending_launch_anchor_missing"



def test_symbol_not_in_current_exchangeinfo_is_skipped_not_failed():
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    exinfo = {"available": True, "symbols": {"XYZUSDT"}}  # ABCUSDT missing

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "rejected"
    assert reason == "symbol_not_in_exchangeinfo"


def test_exchangeinfo_unavailable_keeps_event_pending_not_symbol_not_found():
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    exinfo = {"available": False, "symbols": set()}  # exchangeInfo unavailable

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "pending"
    assert reason == "exchangeinfo_unavailable"


def test_multiple_symbols_are_flattened_to_event_symbol_rows():
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT", "XYZUSDT"],
    }
    rows = list(flatten_event_symbols(event))
    assert len(rows) == 2
    assert rows[0]["symbol"] == "ABCUSDT"
    assert rows[1]["symbol"] == "XYZUSDT"


def test_event_symbol_id_is_stable():
    event = {"event_id": "e1"}
    h1 = make_event_symbol_id(event, "ABCUSDT")
    h2 = make_event_symbol_id(event, "ABCUSDT")
    assert h1 == h2


def test_stable_event_symbol_key_uses_article_symbol_and_event_type_not_revision_hash():
    row1 = {
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "event_id": "revision-a",
        "symbols": ["ABCUSDT"],
        "detail_payload_hash": "hash-a",
    }
    row2 = {
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "event_id": "revision-b",
        "symbols": ["ABCUSDT"],
        "detail_payload_hash": "hash-b",
    }

    assert make_stable_event_symbol_key(row1, "ABCUSDT") == make_stable_event_symbol_key(row2, "ABCUSDT")


def test_pending_state_upserts_new_event_revision_by_stable_key_preserving_first_seen_fields():
    pending = EventSymbolState(
        event_symbol_id="old-es",
        event_id="revision-a",
        symbol="ABCUSDT",
        status="pending_launch_anchor_missing",
        stable_event_symbol_key="futures_contract_launch|article1|ABCUSDT",
        first_seen_at_ms=1_000,
        bootstrap_watermark_max_seen_detected_at_ms=500,
        announcement_capture_post_bootstrap_watermark=True,
    )
    revision = {
        "event_id": "revision-b",
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "symbols": ["ABCUSDT"],
        "symbol_effective_launch_times_ms": {"ABCUSDT": 10_000},
        "detail_payload_hash": "hash-b",
    }

    updated = upsert_pending_state_with_event_revision(pending, revision, "ABCUSDT")

    assert updated.event_id == "revision-b"
    assert updated.latest_event_payload_hash == "hash-b"
    assert updated.first_seen_at_ms == 1_000
    assert updated.bootstrap_watermark_max_seen_detected_at_ms == 500
    assert updated.announcement_capture_post_bootstrap_watermark is True


def test_resolve_depth_observation_anchor_prefers_effective_launch_time():
    row = {
        "symbol_effective_launch_times_ms": {"ABCUSDT": 10_000},
        "symbol_onboard_times_ms": {"ABCUSDT": 10_030},
    }
    exchangeinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    result = resolve_depth_observation_anchor_ms(row, "ABCUSDT", exchangeinfo, now_ms=9_000)

    assert result["observation_anchor_ms"] == 10_000
    assert result["observation_anchor_basis"] == "symbol_effective_launch_time"
    assert result["observation_anchor_confidence"] == "high"
    assert result["observation_anchor_conflict_active"] is False


def test_anchor_conflict_blocks_silent_priority_selection():
    row = {
        "symbol_effective_launch_times_ms": {"ABCUSDT": 10_000},
        "symbol_onboard_times_ms": {"ABCUSDT": 100_000},
    }
    exchangeinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    result = resolve_depth_observation_anchor_ms(row, "ABCUSDT", exchangeinfo, now_ms=9_000)

    assert result["observation_anchor_conflict_active"] is True
    assert result["observation_anchor_disagreement_max_ms"] == 90_000



def test_timely_exchangeinfo_anchor_can_be_medium_confidence_clean_start():
    row = {
        "event_type": "futures_contract_launch",
        "symbol_validation_status": "validated",
    }
    exchangeinfo = {
        "available": True,
        "symbols": {"ABCUSDT"},
        "symbol_rows": {
            "ABCUSDT": {
                "symbol": "ABCUSDT",
                "status": "PENDING_TRADING",
                "contractType": "PERPETUAL",
                "quoteAsset": "USDT",
                "marginAsset": "USDT",
                "onboardDate": 10_000,
            }
        },
        "fetched_at_ms": 9_000,
        "payload_sha256": "hash",
        "raw_payload_path": "raw/exchangeinfo.jsonl",
    }

    result = resolve_depth_observation_anchor_ms(row, "ABCUSDT", exchangeinfo, now_ms=9_000)

    assert result["observation_anchor_ms"] == 10_000
    assert result["observation_anchor_basis"] == "exchangeinfo_current_onboard_time"
    assert result["observation_anchor_confidence"] == "medium"
    assert result["exchangeinfo_anchor_clean_eligible"] is True


def test_exchangeinfo_anchor_without_payload_hash_is_recovery_only():
    row = {"event_type": "futures_contract_launch", "symbol_validation_status": "validated"}
    exchangeinfo = {
        "available": True,
        "symbols": {"ABCUSDT"},
        "symbol_rows": {"ABCUSDT": {"symbol": "ABCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 10_000}},
        "fetched_at_ms": 9_000,
        "payload_sha256": "",
        "raw_payload_path": "",
    }

    result = resolve_depth_observation_anchor_ms(row, "ABCUSDT", exchangeinfo, now_ms=9_000)

    assert result["observation_anchor_basis"] == "exchangeinfo_current_onboard_time"
    assert result["exchangeinfo_anchor_clean_eligible"] is False


def test_first_seen_computes_frozen_bootstrap_watermark_fields():
    event = {"event_id": "e1", "event_type": "futures_contract_launch", "detected_at_ms": 2_000, "symbols": ["ABCUSDT"]}
    diag = {"observation_anchor_ms": 10_000}
    watermark = Watermark(1, 5_000, [], [], [], 5_000)
    bootstrap_watermark_ms = 1_000

    frozen = build_first_seen_watermark_diagnostics(event, "ABCUSDT", diag, watermark, bootstrap_watermark_ms)

    assert frozen["bootstrap_watermark_max_seen_detected_at_ms"] == 1_000
    assert frozen["admission_watermark_at_first_seen_ms"] == 5_000
    assert frozen["announcement_capture_post_bootstrap_watermark"] is True
    assert frozen["launch_anchor_post_bootstrap_watermark"] is True


def test_pending_recheck_does_not_recompute_frozen_evidence_flags():
    existing = EventSymbolState(
        event_symbol_id="es1",
        status="pending_launch_time_in_future",
        bootstrap_watermark_max_seen_detected_at_ms=1_000,
        admission_watermark_at_first_seen_ms=5_000,
        announcement_capture_post_bootstrap_watermark=True,
        launch_anchor_post_bootstrap_watermark=True,
    )
    new_diag = {
        "bootstrap_watermark_max_seen_detected_at_ms": 9_000,
        "admission_watermark_at_first_seen_ms": 9_000,
        "announcement_capture_post_bootstrap_watermark": False,
        "launch_anchor_post_bootstrap_watermark": False,
    }

    merged = merge_first_seen_watermark_fields(existing, new_diag)

    assert merged["bootstrap_watermark_max_seen_detected_at_ms"] == 1_000
    assert merged["announcement_capture_post_bootstrap_watermark"] is True


def test_missing_anchor_rechecks_latest_event_revision():
    pending = EventSymbolState(
        event_symbol_id="es1",
        event_id="rev1",
        symbol="ABCUSDT",
        status="pending_launch_anchor_missing",
        stable_event_symbol_key="futures_contract_launch|article1|ABCUSDT",
        next_anchor_resolution_at_ms=10_000,
        anchor_resolution_deadline_ms=20_000,
    )
    revision = {
        "event_id": "rev2",
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "symbols": ["ABCUSDT"],
        "symbol_effective_launch_times_ms": {"ABCUSDT": 15_000},
    }

    result = re_resolve_pending_anchor(pending, [revision], {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}, now_ms=10_000)

    assert result.status == "pending_launch_time_in_future"
    assert result.event_id == "rev2"
    assert result.observation_anchor_ms == 15_000


def test_missing_anchor_timeout_returns_terminal_rejection_state():
    pending = EventSymbolState(
        event_symbol_id="es1",
        symbol="ABCUSDT",
        status="pending_launch_anchor_missing",
        next_anchor_resolution_at_ms=10_000,
        anchor_resolution_deadline_ms=9_999,
    )

    result = re_resolve_pending_anchor(pending, [], {"available": True, "symbols": set(), "symbol_rows": {}}, now_ms=10_000)

    assert result.status == "rejected_launch_anchor_unavailable_timeout"
    assert result.pending_terminal_reason == "rejected_launch_anchor_unavailable_timeout"


def test_anchor_conflict_can_resolve_after_event_revision():
    pending = EventSymbolState(
        event_symbol_id="es1",
        event_id="rev1",
        symbol="ABCUSDT",
        status="pending_anchor_conflict",
        stable_event_symbol_key="futures_contract_launch|article1|ABCUSDT",
        observation_anchor_candidates={"symbol_effective_launch_time": 10_000, "symbol_onboard_time": 100_000},
        anchor_resolution_deadline_ms=30_000,
        next_anchor_resolution_at_ms=10_000,
    )
    revision = {
        "event_id": "rev2",
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "symbols": ["ABCUSDT"],
        "symbol_effective_launch_times_ms": {"ABCUSDT": 10_000},
        "symbol_onboard_times_ms": {"ABCUSDT": 10_000},
    }

    result = re_resolve_pending_anchor(pending, [revision], {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}, now_ms=9_000)

    assert result.status == "pending_launch_time_in_future"
    assert result.observation_anchor_conflict_active is False
    assert result.observation_anchor_ms == 10_000


def test_launch_time_in_future_is_persisted_pending_status():
    now_ms = 1_000_000
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 60_000,
        "symbols": ["ABCUSDT"],
        "symbol_effective_launch_times_ms": {"ABCUSDT": now_ms + 600_000},
    }
    w = Watermark(1, now_ms - 120_000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(event, "ABCUSDT", now_ms, w, exinfo, {})

    assert status == "pending"
    assert reason == "pending_launch_time_in_future"
    assert diag["observation_anchor_ms"] == now_ms + 600_000
    assert diag["next_admission_check_at_ms"] == now_ms + 600_000


def test_missing_launch_anchor_does_not_fallback_to_detected_time_for_clean_observation():
    now_ms = 1_000_000
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 60_000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, now_ms - 120_000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(event, "ABCUSDT", now_ms, w, exinfo, {})

    assert status == "pending"
    assert reason == "pending_launch_anchor_missing"
    assert diag["observation_anchor_ms"] is None


def test_late_launch_start_is_recovery_only_not_clean():
    now_ms = 1_000_000
    launch_ms = now_ms - base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS - 1
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 60_000,
        "symbols": ["ABCUSDT"],
        "symbol_effective_launch_times_ms": {"ABCUSDT": launch_ms},
    }
    w = Watermark(1, now_ms - 120_000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(event, "ABCUSDT", now_ms, w, exinfo, {})

    assert status == "eligible"
    assert reason == "eligible_recovery_only"
    assert diag["evidence_start_class"] == "recovery_start"








def test_event_symbol_id_is_stable_across_restarts_with_same_input():
    event = {"event_id": "e1"}
    h1 = make_event_symbol_id(event, "ABCUSDT")

    # Re-run
    h2 = make_event_symbol_id({"event_id": "e1"}, "ABCUSDT")
    assert h1 == h2


def test_event_symbol_id_fallback_is_stable_when_event_id_missing():
    event = {
        "source_name": "s1",
        "source_article_id": "art1",
        "source_detail_url": "https://binance.com/announcement/123/",
        "source_published_at_ms": 1000,
    }
    h1 = make_event_symbol_id(event, "ABCUSDT")

    event2 = {
        "source_name": "s1",
        "source_article_id": "art1",
        "source_detail_url": "https://binance.com/announcement/123",  # slightly different trailing slash
        "source_published_at_ms": 1000,
    }
    h2 = make_event_symbol_id(event2, "ABCUSDT")
    # Due to URL normalization (Advisory A), they should produce the exact same ID
    assert h1 == h2


def test_stage1_5f_rejects_invalid_stage1_5d_summary(tmp_path):
    summary_path = tmp_path / "summary.json"
    summary_data = {
        "decision": "stage1_5d_smoke_invalid",  # invalid decision
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }
    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    with pytest.raises(ValueError) as exc:
        validate_stage1_5d_summary(str(summary_path))
    assert "invalid" in str(exc.value)


def test_stage1_5f_rejects_stage1_5d_summary_with_trading_flag_true(tmp_path):
    summary_path = tmp_path / "summary.json"
    summary_data = {
        "decision": "stage1_5d_event_detection_passed",
        "paper_trading_allowed": True,  # should be False
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }
    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    with pytest.raises(ValueError) as exc:
        validate_stage1_5d_summary(str(summary_path))
    assert "safety" in str(exc.value) or "trading" in str(exc.value)


def test_rejected_event_rows_include_rejection_reason():
    event = {
        "event_id": "e1",
        "event_type": "spot_listing",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "rejected"
    assert reason == "wrong_event_type"


def test_pre_watermark_rejection_reason_is_ignored_not_failure():
    # event is pre-watermark
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 400,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, ["e1"], [], [], 500)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "rejected"
    assert reason == "pre_watermark"


def test_delayed_launch_event_with_launch_time_after_watermark_bypasses_detected_pre_watermark():
    now_ms = 1_000_000_000
    launch_ms = now_ms - 5 * 60 * 1000
    event = {
        "event_id": "spcx-event",
        "event_type": "futures_contract_launch",
        "source_article_id": "6cbb1b11a9c843949624cf2eacaac8b4",
        "detected_at_ms": 100_000,
        "symbols": ["SPCXUSD1"],
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "symbol_effective_launch_times_ms": {"SPCXUSD1": launch_ms},
        "symbol_onboard_times_ms": {"SPCXUSD1": launch_ms},
    }
    w = Watermark(1, now_ms - 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"SPCXUSD1"}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        event, "SPCXUSD1", now_ms, w, exinfo, {}
    )

    assert status == "eligible"
    assert reason == "eligible_recovery_only"
    assert diag["observation_anchor_basis"] == "symbol_effective_launch_time"



def test_delayed_launch_event_seen_by_watermark_still_rejected_as_pre_watermark():
    now_ms = 1_000_000_000
    launch_ms = now_ms - 5 * 60 * 1000
    event = {
        "event_id": "spcx-event",
        "event_type": "futures_contract_launch",
        "source_article_id": "6cbb1b11a9c843949624cf2eacaac8b4",
        "detected_at_ms": 100_000,
        "symbols": ["SPCXUSD1"],
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "symbol_effective_launch_times_ms": {"SPCXUSD1": launch_ms},
    }
    w = Watermark(
        1,
        now_ms - 60 * 60 * 1000,
        [],
        ["6cbb1b11a9c843949624cf2eacaac8b4"],
        [],
        now_ms,
    )
    exinfo = {"available": True, "symbols": {"SPCXUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "SPCXUSD1", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "pre_watermark"


def test_detected_pre_watermark_without_per_symbol_launch_time_remains_rejected():
    event = {
        "event_id": "old-event",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 100_000,
        "symbols": ["ABCUSDT"],
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
    }
    w = Watermark(1, 200_000, [], [], [], 200_000)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 210_000, w, exinfo, {})

    assert status == "rejected"
    assert reason == "pre_watermark"


def test_stage1_5f_loader_accepts_legacy_1_5d_event_rows_without_symbol_extraction_diagnostics(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(json.dumps({
        "event_id": "legacy-event",
        "event_type": "futures_contract_launch",
        "symbols": ["ABCUSDT"],
        "detected_at_ms": 1_000,
        "source_article_id": "abc",
    }) + "\n")

    rows = list(iter_stage1_5d_event_rows(str(events)))
    flattened = list(flatten_event_symbols(rows[0]))

    assert flattened[0]["symbol"] == "ABCUSDT"
    assert make_event_symbol_id(rows[0], "ABCUSDT")


def test_resolve_observation_age_base_prefers_symbol_effective_launch_time():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_onboard_times_ms": {"ETHUSD1": 20_000},
        "symbol_effective_launch_times_ms": {"ETHUSD1": 30_000},
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 30_000
    assert basis == "symbol_effective_launch_time"


def test_resolve_observation_age_base_falls_back_to_symbol_onboard_time():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_onboard_times_ms": {"ETHUSD1": 20_000},
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 20_000
    assert basis == "symbol_onboard_time"


def test_symbol_resolved_time_not_used_for_ordinary_late_parser_retry_without_launch_time():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_extraction_source": "detail",
        "symbol_validation_status": "validated_by_exact_text",
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 1_000
    assert basis == "detected_time"


def test_symbol_resolved_time_used_only_when_delayed_launch_flag_present():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "delayed_launch_observation_allowed": True,
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 10_000
    assert basis == "symbol_resolved_time"


def test_symbol_resolved_time_not_used_when_contract_source_has_no_per_symbol_launch_evidence():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "symbol_onboard_times_ms": {"OTHER": 9_000},
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 1_000
    assert basis == "detected_time"


def test_resolve_observation_age_base_falls_back_to_detected_time_for_legacy_rows():
    row = {"detected_at_ms": 1_000}

    ms, basis = resolve_observation_age_base_ms(row, "ABCUSDT")

    assert ms == 1_000
    assert basis == "detected_time"


def test_delayed_launch_event_uses_symbol_effective_launch_time_for_age_gate():
    now_ms = 1_000_000_000
    event = {
        "event_id": "e-delayed",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms - 5 * 60 * 1000},
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "eligible"
    assert reason == "eligible_recovery_only"


def test_legacy_event_without_launch_time_still_rejected_by_detected_age():
    now_ms = 1_000_000_000
    event = {
        "event_id": "e-legacy",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": ["ABCUSDT"]}

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", now_ms, w, exinfo, {})

    assert status == "pending"
    assert reason == "pending_launch_anchor_missing"



def test_launch_time_in_future_is_pending_not_age_rejected_or_eligible():
    now_ms = 1_000_000_000
    event = {
        "event_id": "e-future",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 60_000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms + 10 * 60 * 1000},
    }
    w = Watermark(1, now_ms - 120_000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "pending"
    assert reason == "pending_launch_time_in_future"


def test_launch_time_age_just_inside_15m_window_is_eligible():
    now_ms = 1_000_000_000
    launch_ms = now_ms - (15 * 60 * 1000) + 1_000
    event = {
        "event_id": "e-inside",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": launch_ms},
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "eligible"
    assert reason == "eligible_recovery_only"


def test_launch_time_age_just_outside_15m_window_is_rejected():
    now_ms = 1_000_000_000
    launch_ms = now_ms - (15 * 60 * 1000) - 1_000
    event = {
        "event_id": "e-outside",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": launch_ms},
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "rejected_launch_anchor_age_exceeded"



def test_pre_watermark_seen_event_still_ignored_even_if_launch_time_after_watermark():
    now_ms = 1_000_000_000
    event = {
        "event_id": "e-seen",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 5_000,
        "source_article_id": "article-seen",
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms - 5 * 60 * 1000},
    }
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=5_000,
        seen_event_ids=["e-seen"],
        seen_source_article_ids=["article-seen"],
        seen_stable_event_keys=[],
        updated_at_ms=5_000,
    )
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "pre_watermark"


def test_launch_time_after_watermark_does_not_bypass_seen_event_symbol_id():
    now_ms = 1_000_000_000
    event = {
        "event_id": "e-seen2",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 150_000,
        "source_article_id": "article-seen2",
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms - 5 * 60 * 1000},
    }
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=now_ms - 120_000,
        seen_event_ids=["e-seen2"],
        seen_source_article_ids=["article-seen2"],
        seen_stable_event_keys=[],
        updated_at_ms=now_ms - 120_000,
    )
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "pre_watermark"


def test_eligibility_diagnostics_expose_observation_age_basis():
    now_ms = 1_000_000_000
    event = {
        "event_id": "e-delayed",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms - 5 * 60 * 1000},
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        event, "ETHUSD1", now_ms, w, exinfo, {}
    )

    assert status == "eligible"
    assert reason == "eligible_recovery_only"
    assert diag["observation_anchor_basis"] == "symbol_effective_launch_time"


def test_rejected_age_exceeded_diagnostics_expose_observation_age_basis():
    now_ms = 1_000_000_000
    launch_ms = now_ms - (15 * 60 * 1000) - 1_000
    event = {
        "event_id": "e-outside",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": launch_ms},
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        event, "ETHUSD1", now_ms, w, exinfo, {}
    )

    assert status == "rejected"
    assert reason == "rejected_launch_anchor_age_exceeded"
    assert diag["observation_anchor_ms"] == launch_ms
    assert diag["observation_anchor_basis"] == "symbol_effective_launch_time"


def test_evidence_basis_launch_time_only_when_announcement_before_watermark_but_launch_after():
    row = {
        "symbol": "ETHUSD1",
        "source_published_at_ms": 1_000,
        "detected_at_ms": 2_000,
        "symbol_effective_launch_times_ms": {"ETHUSD1": 10_000},
    }
    w = Watermark(1, 5_000, [], [], [], 5_000)

    basis = classify_live_depth_evidence_basis(row, w)

    assert basis["announcement_time_capture_evidence_allowed"] is False
    assert basis["launch_time_depth_evidence_allowed"] is True
    assert basis["live_depth_evidence_basis"] == "launch_time_only"
    assert basis["announcement_capture_time_ms"] == 2_000
    assert basis["announcement_capture_time_source"] == "detected_at_ms"


def test_frozen_evidence_basis_preserves_launch_time_only_after_watermark_moves():
    row = {
        "symbol": "ETHUSD1",
        "announcement_capture_time_ms": 2_000,
        "announcement_capture_time_source": "detected_at_ms",
        "announcement_capture_post_bootstrap_watermark": False,
        "launch_anchor_post_bootstrap_watermark": True,
        "evidence_start_class": "clean_start",
    }
    moving_watermark = Watermark(1, 20_000, [], [], [], 20_000)

    basis = classify_live_depth_evidence_basis(row, moving_watermark)

    assert basis["announcement_time_capture_evidence_allowed"] is False
    assert basis["launch_time_depth_evidence_allowed"] is True
    assert basis["live_depth_evidence_basis"] == "launch_time_only"


def test_evidence_basis_uses_detected_at_ms_not_source_published_at_ms_for_capture():
    row = {
        "symbol": "ETHUSD1",
        "source_published_at_ms": 1_000,
        "detected_at_ms": 6_000,
        "symbol_effective_launch_times_ms": {"ETHUSD1": 10_000},
    }
    w = Watermark(1, 5_000, [], [], [], 5_000)

    basis = classify_live_depth_evidence_basis(row, w)

    assert basis["announcement_capture_time_ms"] == 6_000
    assert basis["announcement_capture_time_source"] == "detected_at_ms"
    assert basis["announcement_time_capture_evidence_allowed"] is True
    assert basis["live_depth_evidence_basis"] == "announcement_and_launch_time"


def test_regression_ethusd1_onboard_launch_time_delay_accepts():
    event = {
        "event_id": "ethusd1-event",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1783023648791,
        "symbols": ["ETHUSD1"],
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "symbol_effective_launch_times_ms": {"ETHUSD1": 1783069200000},
        "symbol_onboard_times_ms": {"ETHUSD1": 1783069200000},
        "symbol_resolved_at_ms": 1783023650000,
    }
    w = Watermark(1, 1783009167053, [], [], [], 1783009167053)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    # Verify eligibility classification
    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        event, "ETHUSD1", 1783069534532, w, exinfo, {}
    )

    assert status == "eligible"
    assert reason == "eligible_recovery_only"
    assert diag["observation_anchor_basis"] == "symbol_effective_launch_time"

    assert diag["event_age_ms"] == 334532  # 1783069534532 - 1783069200000

    # Verify evidence labeling
    basis = classify_live_depth_evidence_basis(event, w)
    assert basis["live_depth_evidence_basis"] == "announcement_and_launch_time"
    assert basis["announcement_time_capture_evidence_allowed"] is True
    assert basis["launch_time_depth_evidence_allowed"] is True


def test_re_resolve_pending_anchor_ignores_revision_with_same_symbol_but_different_stable_key():
    pending = EventSymbolState(
        event_symbol_id="es1",
        event_id="old-event",
        symbol="ABCUSDT",
        status="pending_launch_anchor_missing",
        stable_event_symbol_key="futures_contract_launch|article1|ABCUSDT",
        anchor_resolution_deadline_ms=50_000,
        next_anchor_resolution_at_ms=9_000,
    )
    unrelated_revision = {
        "event_id": "wrong-event",
        "event_type": "futures_contract_launch",
        "source_article_id": "article2",
        "symbols": ["ABCUSDT"],
        "symbol_effective_launch_times_ms": {"ABCUSDT": 20_000},
    }

    result = re_resolve_pending_anchor(
        pending,
        [unrelated_revision],
        {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}},
        now_ms=10_000,
    )

    assert result.event_id == "old-event"
    assert result.status == "pending_launch_anchor_missing"
    assert result.observation_anchor_ms is None


def test_historical_classification_requires_immutable_bootstrap_watermark():
    assert historical_anchor_classification_allowed(Watermark(max_seen_detected_at_ms=1000)) is False
    assert historical_anchor_classification_allowed(Watermark(
        max_seen_detected_at_ms=2000,
        watermark_schema_version=2,
        bootstrap_max_seen_detected_at_ms=1000,
        bootstrap_created_at_ms=900,
    )) is True


def test_invalid_zero_anchor_is_not_counted_as_historical_candidate():
    candidates = normalize_anchor_candidates({
        "symbol_effective_launch_time": 0,
        "exchangeinfo_current_onboard_time": 1781170800000,
    })
    assert "symbol_effective_launch_time" not in candidates
    assert candidates["exchangeinfo_current_onboard_time"] == 1781170800000


def test_all_valid_anchors_pre_bootstrap_short_circuits_conflict():
    watermark = Watermark(
        watermark_schema_version=2,
        bootstrap_max_seen_detected_at_ms=1784822376255,
        bootstrap_created_at_ms=1784822584716,
        max_seen_detected_at_ms=1784822376255,
    )
    row = {
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
        "detected_at_ms": 1784822376255,
        "symbol": "EBAYUSDT",
        "symbols": ["EBAYUSDT"],
        "stable_event_key": "binance_f598_MULTI",
        "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
    }
    exchangeinfo_state = {
        "available": True,
        "symbols": {"EBAYUSDT"},
        "symbol_rows": {"EBAYUSDT": {"symbol": "EBAYUSDT", "status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1780996800000}},
    }
    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        row=row,
        symbol="EBAYUSDT",
        now_ms=1784850000000,
        watermark=watermark,
        exchangeinfo_state=exchangeinfo_state,
        budget_state={},
    )
    assert status == "ignored"
    assert reason == "ignored_historical_anchor_pre_bootstrap"
    assert diag["terminal_status"] == "ignored_historical_anchor_pre_bootstrap"


def test_missing_bootstrap_watermark_does_not_fall_through_to_conflict():
    watermark = Watermark(max_seen_detected_at_ms=1784822376255)
    row = {
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
        "detected_at_ms": 1784822376255,
        "symbol": "EBAYUSDT",
        "symbols": ["EBAYUSDT"],
        "stable_event_key": "binance_f598_MULTI",
        "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
    }
    exchangeinfo_state = {
        "available": True,
        "symbols": {"EBAYUSDT"},
        "symbol_rows": {"EBAYUSDT": {"symbol": "EBAYUSDT", "status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1780996800000}},
    }
    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        row=row,
        symbol="EBAYUSDT",
        now_ms=1784850000000,
        watermark=watermark,
        exchangeinfo_state=exchangeinfo_state,
        budget_state={},
    )
    assert status == "diagnostic_only"
    assert reason == "historical_classification_bootstrap_watermark_missing"
    assert diag["bootstrap_watermark_missing"] is True


def test_delayed_launch_exception_uses_immutable_bootstrap_cutoff():
    row = {
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1784820000000,
        "symbols": ["FUTUREUSDT"],
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "symbol_effective_launch_times_ms": {"FUTUREUSDT": 1784900000000},
    }
    assert delayed_launch_event_symbol_is_post_bootstrap_watermark(
        row,
        "FUTUREUSDT",
        bootstrap_watermark_ms=1784810000000,
    ) is True
    assert delayed_launch_event_symbol_is_post_bootstrap_watermark(
        row,
        "FUTUREUSDT",
        bootstrap_watermark_ms=1784910000000,
    ) is False


def test_one_post_bootstrap_anchor_prevents_historical_ignore():
    watermark = Watermark(
        watermark_schema_version=2,
        bootstrap_max_seen_detected_at_ms=1784822376255,
        bootstrap_created_at_ms=1784822584716,
        bootstrap_root_id="root-id",
        max_seen_detected_at_ms=1784822376255,
    )
    row = {
        "event_id": "event-mixed",
        "event_type": "futures_contract_launch",
        "source_article_id": "article-mixed",
        "detected_at_ms": 1784822376255,
        "symbol": "MIXEDUSDT",
        "symbols": ["MIXEDUSDT"],
        "stable_event_key": "binance_mixed_MULTI",
        "symbol_effective_launch_times_ms": {"MIXEDUSDT": 1780995600000},
    }
    exchangeinfo_state = {
        "available": True,
        "symbols": {"MIXEDUSDT"},
        "symbol_rows": {"MIXEDUSDT": {"symbol": "MIXEDUSDT", "status": "PENDING_TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1784825976255}},
    }
    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        row=row,
        symbol="MIXEDUSDT",
        now_ms=1784823000000,
        watermark=watermark,
        exchangeinfo_state=exchangeinfo_state,
        budget_state={},
    )
    assert status != "ignored"
    assert reason != "ignored_historical_anchor_pre_bootstrap"


def test_malformed_production_fixture_routes_to_diagnostic_only(tmp_path):
    fixture_path = "tests/fixtures/external_signal_shadow/stage1_5f/rejected_hygiene/malformed_historical_rejected_rows.jsonl"
    with open(fixture_path, "r") as f:
        row = json.loads(f.readline())

    norm_id = normalize_event_symbol_identity(row, row.get("symbol", ""))
    assert norm_id["identity_valid"] is False
    assert "detected_at_ms_invalid_or_missing" in norm_id["identity_errors"]

    w = Watermark(
        watermark_schema_version=2,
        bootstrap_max_seen_detected_at_ms=1784822376255,
        bootstrap_created_at_ms=1784822584716,
        max_seen_detected_at_ms=1784822376255,
    )
    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        row=row,
        symbol="GLWUSDT",
        now_ms=1784850000000,
        watermark=w,
        exchangeinfo_state={"available": True, "symbols": {"GLWUSDT"}},
        budget_state={},
    )
    assert status == "diagnostic_only"
    assert reason == "malformed_source_identity"


def test_missing_source_article_id_never_enters_normal_terminal_state():
    row = {
        "event_type": "futures_contract_launch",
        "symbol": "GLWUSDT",
        "detected_at_ms": 1784822376255,
    }
    norm_id = normalize_event_symbol_identity(row, "GLWUSDT")
    assert norm_id["identity_valid"] is False
    assert "source_article_id_and_event_id_both_missing" in norm_id["identity_errors"]
