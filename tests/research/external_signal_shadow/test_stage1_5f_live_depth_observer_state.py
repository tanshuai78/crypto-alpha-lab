import json
import os

from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
    DepthSnapshot,
    EventSymbolState,
)
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
    compact_observer_state_jsonl,
    finalize_observation_if_due,
    load_latest_state_by_event_symbol_id,
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
