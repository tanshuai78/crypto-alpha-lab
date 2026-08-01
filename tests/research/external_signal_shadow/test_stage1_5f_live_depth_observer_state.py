import json
import os

from configs import base
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
    DepthSnapshot,
    EventSymbolState,
)
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
    build_historical_anchor_hygiene_diagnostic,
    build_rejected_event_symbol_row,
    build_terminal_ignored_state,
    compact_observer_state_jsonl,
    compute_snapshot_time_coverage,
    create_pending_observation_state,
    finalize_observation_if_due,
    load_latest_state_by_event_symbol_id,
    promote_pending_to_active_observation,
)


def test_restart_resumes_active_observation_without_resetting_window():
    # Active state loaded from file
    state = EventSymbolState(
        event_symbol_id="id1",
        event_id="e1",
        symbol="BTCUSDT",
        detected_at_ms=1000,
        observation_started_at_ms=2000,
        observation_window_end_ms=2000 + 12 * 3600 * 1000,
        status="active",
        depth_snapshot_count=10,
        last_snapshot_ms=5000,
        max_gap_ms=0,
        coverage_ratio_pass=False,
        max_gap_pass=False,
        research_result_valid=False,
    )
    # Restart at now = 6000
    # The active state should still be active with the same start and end times
    assert state.status == "active"
    assert state.observation_started_at_ms == 2000
    assert state.observation_window_end_ms == 2000 + 12 * 3600 * 1000


def test_restart_expires_old_active_observation_without_enough_snapshots():
    # An active observation whose window has already ended, but it doesn't have enough snapshots
    state = EventSymbolState(
        event_symbol_id="id1",
        event_id="e1",
        symbol="BTCUSDT",
        detected_at_ms=1000,
        observation_started_at_ms=2000,
        observation_window_end_ms=2000 + 12 * 3600 * 1000, # ends at 43202000
        status="active",
        depth_snapshot_count=10, # only 10 snapshots! Needs 576
        last_snapshot_ms=5000,
        max_gap_ms=0,
        coverage_ratio_pass=False,
        max_gap_pass=False,
        research_result_valid=False,
    )

    # Check if due for finalization at now = 43203000 (after end)
    # Empty snapshots
    updated = finalize_observation_if_due(state, 2000 + 12 * 3600 * 1000 + 1000, [])
    assert updated.status == "expired_without_depth"
    assert updated.research_result_valid is False


def test_observation_completes_after_12h_and_min_snapshot_count():
    started_at = 2000
    end_at = started_at + 12 * 3600 * 1000 # 43202000

    state = EventSymbolState(
        event_symbol_id="id1",
        event_id="e1",
        symbol="BTCUSDT",
        detected_at_ms=1000,
        observation_started_at_ms=started_at,
        observation_window_end_ms=end_at,
        status="active",
        depth_snapshot_count=580,
        last_snapshot_ms=end_at - 1000,
        max_gap_ms=30000,
        coverage_ratio_pass=False,
        max_gap_pass=False,
        research_result_valid=False,
    )

    snapshots = []
    first_ts = started_at + 1000
    last_ts = end_at - 1000
    interval = (last_ts - first_ts) / 579
    for i in range(580):
        t = int(first_ts + i * interval)
        snapshots.append(DepthSnapshot(
            event_symbol_id="id1",
            symbol="BTCUSDT",
            fetched_at_ms=t,
            exchange_time_ms=t,
            best_bid=100.0,
            best_ask=101.0,
            spread_bps=100.0,
            top_bid_depth_usdt=1000.0,
            top_ask_depth_usdt=1000.0,
            buy_slippage_bps=1.0,
            sell_slippage_bps=1.0,
            slippage_status="ok",
            depth_status="healthy"
        ))

    updated = finalize_observation_if_due(state, end_at + 1000, snapshots)
    assert updated.status == "completed"
    assert updated.coverage_ratio_pass is True
    assert updated.max_gap_pass is True
    assert updated.research_result_valid is True


def test_research_result_valid_requires_snapshot_time_coverage_not_only_count():
    started_at = 2000
    end_at = started_at + 12 * 3600 * 1000

    state = EventSymbolState(
        event_symbol_id="id1",
        event_id="e1",
        symbol="BTCUSDT",
        detected_at_ms=1000,
        observation_started_at_ms=started_at,
        observation_window_end_ms=end_at,
        status="active",
        depth_snapshot_count=600,
        last_snapshot_ms=end_at - 1000,
        max_gap_ms=10 * 60000,  # 10 minutes gap (max allowed is 5min)
        coverage_ratio_pass=False,
        max_gap_pass=False,
        research_result_valid=False,
    )

    snapshots = []
    first_ts = started_at + 1000
    last_ts = end_at - 1000
    for i in range(300):
        t = int(first_ts + i * (15000000 / 299))
        snapshots.append(DepthSnapshot(
            event_symbol_id="id1",
            symbol="BTCUSDT",
            fetched_at_ms=t,
            exchange_time_ms=t,
            best_bid=100.0,
            best_ask=101.0,
            spread_bps=100.0,
            top_bid_depth_usdt=1000.0,
            top_ask_depth_usdt=1000.0,
            buy_slippage_bps=1.0,
            sell_slippage_bps=1.0,
            slippage_status="ok",
            depth_status="healthy"
        ))
    for i in range(300):
        start_t2 = first_ts + 15600000
        t = int(start_t2 + i * ((last_ts - start_t2) / 299))
        snapshots.append(DepthSnapshot(
            event_symbol_id="id1",
            symbol="BTCUSDT",
            fetched_at_ms=t,
            exchange_time_ms=t,
            best_bid=100.0,
            best_ask=101.0,
            spread_bps=100.0,
            top_bid_depth_usdt=1000.0,
            top_ask_depth_usdt=1000.0,
            buy_slippage_bps=1.0,
            sell_slippage_bps=1.0,
            slippage_status="ok",
            depth_status="healthy"
        ))

    updated = finalize_observation_if_due(state, end_at + 1000, snapshots)
    assert updated.status == "expired_without_depth"
    assert updated.max_gap_pass is False  # fails gap check
    assert updated.research_result_valid is False


def test_terminal_observation_is_not_restarted():
    # Completed state should not be restarted
    state = EventSymbolState(
        event_symbol_id="id1",
        event_id="e1",
        symbol="BTCUSDT",
        detected_at_ms=1000,
        observation_started_at_ms=2000,
        observation_window_end_ms=2000 + 12 * 3600 * 1000,
        status="completed",
        depth_snapshot_count=580,
        last_snapshot_ms=10000,
        max_gap_ms=0,
        coverage_ratio_pass=True,
        max_gap_pass=True,
        research_result_valid=True,
    )
    # Check finalize on already completed state
    updated = finalize_observation_if_due(state, 50000000, [])
    assert updated.status == "completed"
    assert updated.research_result_valid is True


def test_startup_compacts_observer_state_to_latest_row_per_event_symbol(tmp_path):
    state_file = tmp_path / "observer_state.jsonl"
    # Write duplicate rows for same event_symbol_id
    rows = [
        {"event_symbol_id": "id1", "symbol": "BTCUSDT", "status": "active"},
        {"event_symbol_id": "id2", "symbol": "ETHUSDT", "status": "active"},
        {"event_symbol_id": "id1", "symbol": "BTCUSDT", "status": "completed"}, # latest for id1
    ]
    with open(state_file, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    # Compact
    compact_observer_state_jsonl(str(state_file))

    # Reload and check
    latest = load_latest_state_by_event_symbol_id(str(state_file))
    assert len(latest) == 2
    assert latest["id1"].status == "completed"
    assert latest["id2"].status == "active"


def test_state_compaction_writes_backup_before_replace(tmp_path):
    state_file = tmp_path / "observer_state.jsonl"
    with open(state_file, "w") as f:
        f.write(json.dumps({"event_symbol_id": "id1", "symbol": "BTCUSDT", "status": "active"}) + "\n")

    compact_observer_state_jsonl(str(state_file))

    # Check if a .bak file exists in the directory
    files = os.listdir(tmp_path)
    bak_files = [f for f in files if f.endswith(".bak")]
    assert len(bak_files) == 1
    assert "observer_state" in bak_files[0]


def test_create_pending_launch_state_survives_state_reload(tmp_path):
    state_file = tmp_path / "observer_state.jsonl"
    event = {
        "event_symbol_id": "es1",
        "event_id": "e1",
        "source_article_id": "article1",
        "stable_event_symbol_key": "futures_contract_launch|article1|ABCUSDT",
        "symbol": "ABCUSDT",
        "detected_at_ms": 1_000,
    }
    diag = {
        "observation_anchor_ms": 10_000,
        "observation_anchor_basis": "symbol_effective_launch_time",
        "observation_anchor_confidence": "high",
        "next_admission_check_at_ms": 10_000,
        "bootstrap_watermark_max_seen_detected_at_ms": 500,
        "announcement_capture_post_bootstrap_watermark": True,
        "launch_anchor_post_bootstrap_watermark": True,
    }

    state = create_pending_observation_state(event, "pending_launch_time_in_future", diag, now_ms=2_000)
    state_file.write_text(json.dumps(state.to_dict()) + "\n")

    loaded = load_latest_state_by_event_symbol_id(str(state_file))["es1"]
    assert loaded.status == "pending_launch_time_in_future"
    assert loaded.observation_anchor_ms == 10_000


def test_promote_pending_to_active_sets_window_from_anchor_not_now():
    pending = EventSymbolState(
        event_symbol_id="es1",
        event_id="e1",
        symbol="ABCUSDT",
        detected_at_ms=1_000,
        status="pending_launch_time_in_future",
        observation_anchor_ms=10_000,
        observation_anchor_basis="symbol_effective_launch_time",
        observation_anchor_confidence="high",
        observation_anchor_candidates={"symbol_effective_launch_time": 10_000},
        announcement_capture_post_bootstrap_watermark=True,
        launch_anchor_post_bootstrap_watermark=True,
    )

    active = promote_pending_to_active_observation(pending, now_ms=10_500, evidence_start_class="clean_start")

    assert active.status == "active"
    assert active.observation_started_at_ms == 10_500
    assert active.observation_window_start_ms == 10_000
    assert active.observation_window_end_ms == 10_000 + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS
    assert active.first_depth_request_at_ms is None
    assert active.acceptance_id


def test_build_terminal_ignored_state_persists_source_payload_hash_for_revision_detection():
    state = build_terminal_ignored_state(
        flat_event={
            "event_symbol_id": "es-historical",
            "event_id": "event-historical",
            "event_type": "futures_contract_launch",
            "source_article_id": "article-historical",
            "stable_event_symbol_key": "futures_contract_launch|article-historical|OLDUSDT",
            "stable_event_key": "binance_article_historical",
            "symbol": "OLDUSDT",
            "detected_at_ms": 1784822376255,
            "detail_payload_hash": "payload-hash-v1",
        },
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        now_ms=1784850000000,
        diagnostics={
            "normalized_anchor_class": "all_pre_bootstrap",
            "bootstrap_watermark_max_seen_detected_at_ms": 1784822376255,
            "bootstrap_root_id": "root-id",
        },
    )

    assert state.source_event_payload_hash == "payload-hash-v1"
    assert state.latest_event_payload_hash == "payload-hash-v1"


def test_finalize_preserves_launch_anchor_and_request_metrics():
    anchor_ms = 10_000
    end_ms = anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS
    state = EventSymbolState(
        event_symbol_id="es1",
        event_id="e1",
        symbol="ABCUSDT",
        detected_at_ms=1_000,
        status="active",
        observation_started_at_ms=anchor_ms + 500,
        observation_anchor_ms=anchor_ms,
        observation_anchor_basis="symbol_effective_launch_time",
        observation_anchor_confidence="high",
        observation_window_start_ms=anchor_ms,
        observation_window_end_ms=end_ms,
        first_depth_request_at_ms=anchor_ms + 500,
        first_depth_request_latency_ms=500,
        acceptance_id="acceptance-1",
        evidence_start_class="clean_start",
    )
    snapshots = [
        DepthSnapshot(
            event_symbol_id="es1",
            symbol="ABCUSDT",
            fetched_at_ms=anchor_ms + i * base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC * 1000,
            exchange_time_ms=anchor_ms,
            best_bid=100.0,
            best_ask=101.0,
            spread_bps=100.0,
            depth_status="healthy",
        )
        for i in range(720)
    ]

    final = finalize_observation_if_due(state, end_ms + 1, snapshots)

    assert final.status == "completed"
    assert final.observation_anchor_ms == anchor_ms
    assert final.observation_anchor_basis == "symbol_effective_launch_time"
    assert final.observation_window_start_ms == anchor_ms
    assert final.first_depth_request_at_ms == anchor_ms + 500
    assert final.first_depth_request_latency_ms == 500
    assert final.acceptance_id == "acceptance-1"
    assert final.expected_snapshot_count == 720
    assert final.unique_snapshot_bucket_count == 720
    assert final.missing_snapshot_bucket_count == 0


def test_snapshot_at_exact_window_end_does_not_create_extra_bucket():
    anchor_ms = 10_000
    state = EventSymbolState(
        event_symbol_id="es1",
        symbol="ABCUSDT",
        status="active",
        observation_anchor_ms=anchor_ms,
        observation_window_start_ms=anchor_ms,
        observation_window_end_ms=anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS,
    )
    snapshots = [
        DepthSnapshot(
            event_symbol_id="es1",
            symbol="ABCUSDT",
            fetched_at_ms=anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS,
            depth_status="healthy",
        )
    ]

    cov = compute_snapshot_time_coverage(state, snapshots)

    assert cov["expected_snapshot_count"] == 720
    assert cov["unique_snapshot_bucket_count"] == 0
    assert cov["out_of_window_snapshot_row_count"] == 1


def test_make_terminal_hygiene_id_uses_stable_key_not_event_symbol_id():
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import make_terminal_hygiene_id
    a = make_terminal_hygiene_id(
        stable_event_symbol_key="article|futures_contract_launch|EBAYUSDT",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        normalized_anchor_class="all_pre_bootstrap",
        bootstrap_root_id="root-id",
    )
    b = make_terminal_hygiene_id(
        stable_event_symbol_key="article|futures_contract_launch|EBAYUSDT",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        normalized_anchor_class="all_pre_bootstrap",
        bootstrap_root_id="root-id",
    )
    assert a == b
    assert len(a) == 64


def test_terminal_ignored_state_roundtrip_defaults():
    state = EventSymbolState(
        event_symbol_id="volatile-id",
        event_id="event-1",
        source_article_id="article-1",
        symbol="EBAYUSDT",
        detected_at_ms=1784822376255,
        stable_event_symbol_key="article-1|futures_contract_launch|EBAYUSDT",
        status="ignored_historical_anchor_pre_bootstrap",
        terminal_hygiene_id="abc",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_at_ms=1784850000000,
        consumable_by_stage1_5g=False,
    )
    loaded = EventSymbolState.from_dict(state.to_dict())
    assert loaded.status == "ignored_historical_anchor_pre_bootstrap"
    assert loaded.terminal_hygiene_id == "abc"
    assert loaded.consumable_by_stage1_5g is False


def test_build_terminal_ignored_state_preserves_identity_and_is_not_1_5g_consumable():
    flat_event = {
        "event_symbol_id": "volatile-id",
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "article-ebay",
        "stable_event_key": "binance_article_MULTI",
        "stable_event_symbol_key": "article-ebay|futures_contract_launch|EBAYUSDT",
        "symbol": "EBAYUSDT",
        "detected_at_ms": 1784822376255,
    }
    state = build_terminal_ignored_state(
        flat_event=flat_event,
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        now_ms=1784850000000,
        diagnostics={
            "normalized_anchor_class": "all_pre_bootstrap",
            "bootstrap_watermark_max_seen_detected_at_ms": 1784822376255,
        },
    )
    assert state.status == "ignored_historical_anchor_pre_bootstrap"
    assert state.terminal_hygiene_id
    assert state.source_article_id == "article-ebay"
    assert state.detected_at_ms == 1784822376255
    assert state.consumable_by_stage1_5g is False


def test_build_historical_anchor_diagnostic_is_not_1_5g_consumable():
    flat_event = {
        "event_symbol_id": "volatile-id",
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "article-ebay",
        "stable_event_key": "binance_article_MULTI",
        "stable_event_symbol_key": "article-ebay|futures_contract_launch|EBAYUSDT",
        "symbol": "EBAYUSDT",
        "detected_at_ms": 1784822376255,
    }
    state = build_terminal_ignored_state(
        flat_event=flat_event,
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        now_ms=1784850000000,
        diagnostics={
            "normalized_anchor_class": "all_pre_bootstrap",
            "bootstrap_watermark_max_seen_detected_at_ms": 1784822376255,
        },
    )
    row = build_historical_anchor_hygiene_diagnostic(state, diagnostic_at_ms=1784850000000)
    assert row["diagnostic_type"] == "historical_anchor_pre_bootstrap_ignored"
    assert row["consumable_by_stage1_5g"] is False
    assert row["terminal_hygiene_id"] == state.terminal_hygiene_id


def test_build_terminal_ignored_state_allows_event_id_when_source_article_id_missing():
    flat_event = {
        "event_symbol_id": "volatile-id",
        "event_id": "event-only-id",
        "event_type": "futures_contract_launch",
        "stable_event_symbol_key": "event-only-id|futures_contract_launch|EBAYUSDT",
        "symbol": "EBAYUSDT",
        "detected_at_ms": 1784822376255,
    }
    state = build_terminal_ignored_state(
        flat_event=flat_event,
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        now_ms=1784850000000,
        diagnostics={
            "normalized_anchor_class": "all_pre_bootstrap",
            "bootstrap_watermark_max_seen_detected_at_ms": 1784822376255,
            "bootstrap_root_id": "root-id",
        },
    )
    assert state.event_id == "event-only-id"
    assert state.source_article_id == ""
    assert state.status == "ignored_historical_anchor_pre_bootstrap"


def test_build_rejected_event_symbol_row_contains_identity_and_reason_alias():
    import pytest
    flat_event = {
        "event_symbol_id": "event-symbol-id",
        "event_id": "event-1",
        "event_type": "futures_contract_launch",
        "source_article_id": "article-1",
        "stable_event_key": "binance_article_SYMBOL",
        "stable_event_symbol_key": "article-1|futures_contract_launch|XYZUSDT",
        "symbol": "XYZUSDT",
        "symbols": ["XYZUSDT"],
        "title": "Binance Futures Will Launch XYZUSDT",
        "detected_at_ms": 1784820000000,
        "available_at_ms": 1784820000000,
    }
    row = build_rejected_event_symbol_row(
        flat_event=flat_event,
        terminal_hygiene_id="abc",
        rejected_reason="rejected_launch_anchor_age_exceeded",
        now_ms=1784850000000,
        watermark_max_seen_detected_at_ms=1784822376255,
        watermark_version=1,
        eligibility_diag={"observation_anchor_ms": 1780995600000, "selected_anchor_age_ms": 3854400000},
        basis_diag={"live_depth_evidence_basis": "recovery_validation_only"},
    )
    assert row["rejected_reason"] == "rejected_launch_anchor_age_exceeded"
    assert row["rejection_reason"] == row["rejected_reason"]
    assert row["event_id"] == "event-1"
    assert row["source_article_id"] == "article-1"
    assert row["detected_at_ms"] == 1784820000000
    assert row["consumable_by_stage1_5g"] is True


def test_build_rejected_event_symbol_row_rejects_missing_identity():
    import pytest
    with pytest.raises(ValueError):
        build_rejected_event_symbol_row(
            flat_event={"symbol": "XYZUSDT"},
            terminal_hygiene_id="abc",
            rejected_reason="bad",
            now_ms=1,
            watermark_max_seen_detected_at_ms=0,
            watermark_version=1,
            eligibility_diag={},
            basis_diag={},
        )


def test_pending_active_completed_history_same_event_symbol_id_is_not_collision(tmp_path):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        load_latest_states_by_event_symbol_id,
        group_latest_states_by_stable_event_symbol_key,
        detect_stable_event_symbol_key_collisions,
    )
    p = tmp_path / "state.jsonl"
    s1 = EventSymbolState(event_symbol_id="es1", symbol="BTCUSDT", detected_at_ms=1000, status="pending", stable_event_symbol_key="art1|launch|BTCUSDT")
    s2 = EventSymbolState(event_symbol_id="es1", symbol="BTCUSDT", detected_at_ms=1000, status="active", stable_event_symbol_key="art1|launch|BTCUSDT")
    s3 = EventSymbolState(event_symbol_id="es1", symbol="BTCUSDT", detected_at_ms=1000, status="completed", stable_event_symbol_key="art1|launch|BTCUSDT")

    with open(p, "w", encoding="utf-8") as f:
        for s in [s1, s2, s3]:
            f.write(json.dumps(s.to_dict()) + "\n")

    latest = load_latest_states_by_event_symbol_id(p)
    assert len(latest) == 1
    assert latest["es1"].status == "completed"

    grouped = group_latest_states_by_stable_event_symbol_key(latest)
    collisions = detect_stable_event_symbol_key_collisions(grouped)
    assert len(collisions) == 0


def test_same_stable_key_two_distinct_event_symbol_ids_is_collision(tmp_path):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        load_latest_states_by_event_symbol_id,
        group_latest_states_by_stable_event_symbol_key,
        detect_stable_event_symbol_key_collisions,
    )
    p = tmp_path / "state.jsonl"
    s1 = EventSymbolState(event_symbol_id="es1", symbol="BTCUSDT", detected_at_ms=1000, status="active", stable_event_symbol_key="art1|launch|BTCUSDT")
    s2 = EventSymbolState(event_symbol_id="es2", symbol="BTCUSDT", detected_at_ms=2000, status="active", stable_event_symbol_key="art1|launch|BTCUSDT")

    with open(p, "w", encoding="utf-8") as f:
        for s in [s1, s2]:
            f.write(json.dumps(s.to_dict()) + "\n")

    latest = load_latest_states_by_event_symbol_id(p)
    assert len(latest) == 2
    grouped = group_latest_states_by_stable_event_symbol_key(latest)
    collisions = detect_stable_event_symbol_key_collisions(grouped)
    assert len(collisions) == 1
    assert collisions[0]["stable_event_symbol_key"] == "art1|launch|BTCUSDT"
    assert collisions[0]["distinct_event_symbol_ids"] == ["es1", "es2"]


def test_compaction_and_collision_detection_produce_same_result(tmp_path):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        compact_observer_state_jsonl,
        load_latest_states_by_event_symbol_id,
        group_latest_states_by_stable_event_symbol_key,
        detect_stable_event_symbol_key_collisions,
    )
    p = tmp_path / "state.jsonl"
    s1 = EventSymbolState(event_symbol_id="es1", symbol="BTCUSDT", detected_at_ms=1000, status="pending", stable_event_symbol_key="k1")
    s2 = EventSymbolState(event_symbol_id="es1", symbol="BTCUSDT", detected_at_ms=1000, status="active", stable_event_symbol_key="k1")
    s3 = EventSymbolState(event_symbol_id="es2", symbol="BTCUSDT", detected_at_ms=2000, status="active", stable_event_symbol_key="k1")

    with open(p, "w", encoding="utf-8") as f:
        for s in [s1, s2, s3]:
            f.write(json.dumps(s.to_dict()) + "\n")

    latest1 = load_latest_states_by_event_symbol_id(p)
    collisions1 = detect_stable_event_symbol_key_collisions(group_latest_states_by_stable_event_symbol_key(latest1))

    compact_observer_state_jsonl(p)
    latest2 = load_latest_states_by_event_symbol_id(p)
    collisions2 = detect_stable_event_symbol_key_collisions(group_latest_states_by_stable_event_symbol_key(latest2))

    assert collisions1 == collisions2
    assert len(latest2) == 2


def test_startup_detects_two_active_states_with_same_stable_key(tmp_path):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        load_latest_states_by_event_symbol_id,
        group_latest_states_by_stable_event_symbol_key,
        detect_stable_event_symbol_key_collisions,
    )
    p = tmp_path / "state.jsonl"
    s1 = EventSymbolState(event_symbol_id="es1", symbol="ETHUSDT", detected_at_ms=1000, status="active", stable_event_symbol_key="art2|launch|ETHUSDT")
    s2 = EventSymbolState(event_symbol_id="es2", symbol="ETHUSDT", detected_at_ms=1500, status="active", stable_event_symbol_key="art2|launch|ETHUSDT")
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps(s1.to_dict()) + "\n")
        f.write(json.dumps(s2.to_dict()) + "\n")

    latest = load_latest_states_by_event_symbol_id(p)
    collisions = detect_stable_event_symbol_key_collisions(group_latest_states_by_stable_event_symbol_key(latest))
    assert len(collisions) == 1


def test_startup_detects_active_and_completed_same_stable_key(tmp_path):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        load_latest_states_by_event_symbol_id,
        group_latest_states_by_stable_event_symbol_key,
        detect_stable_event_symbol_key_collisions,
    )
    p = tmp_path / "state.jsonl"
    s1 = EventSymbolState(event_symbol_id="es1", symbol="ETHUSDT", detected_at_ms=1000, status="completed", stable_event_symbol_key="art2|launch|ETHUSDT")
    s2 = EventSymbolState(event_symbol_id="es2", symbol="ETHUSDT", detected_at_ms=1500, status="active", stable_event_symbol_key="art2|launch|ETHUSDT")
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps(s1.to_dict()) + "\n")
        f.write(json.dumps(s2.to_dict()) + "\n")

    latest = load_latest_states_by_event_symbol_id(p)
    collisions = detect_stable_event_symbol_key_collisions(group_latest_states_by_stable_event_symbol_key(latest))
    assert len(collisions) == 1


def test_identity_collision_does_not_delete_existing_state(tmp_path):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        load_latest_states_by_event_symbol_id,
        group_latest_states_by_stable_event_symbol_key,
        detect_stable_event_symbol_key_collisions,
    )
    p = tmp_path / "state.jsonl"
    s1 = EventSymbolState(event_symbol_id="es1", symbol="SOLUSDT", detected_at_ms=1000, status="active", stable_event_symbol_key="k_sol")
    s2 = EventSymbolState(event_symbol_id="es2", symbol="SOLUSDT", detected_at_ms=1500, status="pending", stable_event_symbol_key="k_sol")
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps(s1.to_dict()) + "\n")
        f.write(json.dumps(s2.to_dict()) + "\n")

    latest = load_latest_states_by_event_symbol_id(p)
    collisions = detect_stable_event_symbol_key_collisions(group_latest_states_by_stable_event_symbol_key(latest))
    assert len(collisions) == 1
    # Both states are preserved in latest map
    assert "es1" in latest
    assert "es2" in latest


def test_missing_stable_key_is_rebuilt_only_from_complete_identity():
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        rebuild_missing_stable_event_symbol_key_if_safe,
    )
    s_complete = EventSymbolState(event_symbol_id="es1", source_article_id="art1", symbol="BTCUSDT", detected_at_ms=1000, status="active", stable_event_symbol_key="")
    rebuilt, diag = rebuild_missing_stable_event_symbol_key_if_safe(s_complete)
    assert diag["stable_key_rebuilt"] is True
    assert diag["identity_missing"] is False
    assert rebuilt.stable_event_symbol_key == "futures_contract_launch|art1|BTCUSDT"

    s_incomplete = EventSymbolState(event_symbol_id="es2", source_article_id="", symbol="BTCUSDT", detected_at_ms=1000, status="active", stable_event_symbol_key="")
    rebuilt_inc, diag_inc = rebuild_missing_stable_event_symbol_key_if_safe(s_incomplete)
    assert diag_inc["stable_key_rebuilt"] is False
    assert diag_inc["identity_missing"] is True
    assert rebuilt_inc.stable_event_symbol_key == ""


def test_active_missing_identity_blocks_new_admission():
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        rebuild_missing_stable_event_symbol_key_if_safe,
    )
    s = EventSymbolState(event_symbol_id="es_no_id", source_article_id="", symbol="", detected_at_ms=1000, status="active", stable_event_symbol_key="")
    _, diag = rebuild_missing_stable_event_symbol_key_if_safe(s)
    assert diag["identity_missing"] is True
    assert diag["block_reason"] == "unrebuildable_active_identity_missing"


def test_missing_identity_does_not_delete_or_merge_state():
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        rebuild_missing_stable_event_symbol_key_if_safe,
    )
    s = EventSymbolState(event_symbol_id="es_keep", source_article_id="", symbol="BTCUSDT", detected_at_ms=1000, status="active", stable_event_symbol_key="")
    rebuilt, diag = rebuild_missing_stable_event_symbol_key_if_safe(s)
    assert rebuilt.event_symbol_id == "es_keep"
    assert rebuilt.status == "active"
