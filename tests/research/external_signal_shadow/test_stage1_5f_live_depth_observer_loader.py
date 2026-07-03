import json

import pytest

from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
    classify_event_symbol_eligibility,
    classify_event_symbol_eligibility_with_diagnostics,
    classify_live_depth_evidence_basis,
    flatten_event_symbols,
    iter_stage1_5d_event_rows,
    make_event_symbol_id,
    resolve_announcement_capture_time_ms,
    resolve_observation_age_base_ms,
    validate_stage1_5d_summary,
)
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import Watermark


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
    assert status == "rejected"
    assert reason == "age_exceeded"


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
    assert len(h1) == 64
    assert h1.lower() == h1


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
    assert reason == "ok"


def test_legacy_event_without_launch_time_still_rejected_by_detected_age():
    now_ms = 1_000_000_000
    event = {
        "event_id": "e-legacy",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "age_exceeded"


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
    assert reason == "launch_time_in_future"


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
    assert reason == "ok"


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
    assert reason == "age_exceeded"


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
    assert reason == "ok"
    assert diag["observation_age_basis"] == "symbol_effective_launch_time"
    assert diag["event_age_ms"] == 5 * 60 * 1000
    assert diag["watermark_max_seen_detected_at_ms"] == w.max_seen_detected_at_ms
    assert diag["watermark_version"] == w.watermark_version


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
    assert reason == "age_exceeded"
    assert diag["observation_age_base_ms"] == launch_ms
    assert diag["observation_age_basis"] == "symbol_effective_launch_time"
    assert diag["event_age_ms"] == (15 * 60 * 1000) + 1_000
    assert diag["max_event_age_ms"] == 15 * 60 * 1000
    assert diag["watermark_max_seen_detected_at_ms"] == w.max_seen_detected_at_ms
    assert diag["watermark_version"] == w.watermark_version


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
    assert reason == "ok"
    assert diag["observation_age_basis"] == "symbol_effective_launch_time"
    assert diag["event_age_ms"] == 334532  # 1783069534532 - 1783069200000

    # Verify evidence labeling
    basis = classify_live_depth_evidence_basis(event, w)
    assert basis["live_depth_evidence_basis"] == "announcement_and_launch_time"
    assert basis["announcement_time_capture_evidence_allowed"] is True
    assert basis["launch_time_depth_evidence_allowed"] is True
