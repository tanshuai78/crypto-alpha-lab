import pytest
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    compute_raw_snapshot_quarantine_metrics,
)


def _valid_snapshot(i: int, *, event_symbol_id="es1", symbol="SKHYUSDT", fetched_at_ms=None):
    t = i * 60_000 if fetched_at_ms is None else fetched_at_ms
    return {
        "event_symbol_id": event_symbol_id,
        "symbol": symbol,
        "fetched_at_ms": t,
        "best_bid": 100.0,
        "best_ask": 100.1,
        "mid_price": 100.05,
        "spread_bps": 10.0,
        "buy_slippage_bps": 5.0,
        "sell_slippage_bps": 5.0,
        "top_bid_depth_usdt": 1000.0,
        "top_ask_depth_usdt": 1000.0,
    }


def _empty_snapshot(i: int, *, event_symbol_id="es1", symbol="SKHYUSDT", fetched_at_ms=None):
    row = _valid_snapshot(i, event_symbol_id=event_symbol_id, symbol=symbol, fetched_at_ms=fetched_at_ms)
    row.update({
        "best_bid": None,
        "best_ask": None,
        "mid_price": None,
        "spread_bps": None,
        "depth_status": "invalid",
        "slippage_status": "invalid_depth",
        "top_bid_depth_usdt": 0.0,
        "top_ask_depth_usdt": 0.0,
        "buy_slippage_bps": None,
        "sell_slippage_bps": None,
    })
    return row


def test_warmup_phase_uses_launch_time_not_observation_start_when_available():
    launch_ms = 1_000_000
    observation_start_ms = launch_ms + 30 * 60_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=observation_start_ms),
        _valid_snapshot(1, fetched_at_ms=observation_start_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": observation_start_ms}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_by_reason["midrun_empty_book"] == 1
    assert result.invalid_book_by_reason["launch_warmup_empty_book"] == 0
    assert "launch_time_missing_warmup_anchor_degraded" not in result.warnings


def test_pre_launch_snapshot_is_not_launch_warmup_when_launch_time_available():
    launch_ms = 1_000_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=launch_ms - 60_000),
        _valid_snapshot(1, fetched_at_ms=launch_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": launch_ms - 60_000}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_by_reason["launch_warmup_empty_book"] == 0
    assert result.invalid_book_by_reason["midrun_empty_book"] == 1
    assert result.invalid_book_by_phase["midrun"] == 1


def test_missing_launch_time_uses_observation_initial_label_with_warning():
    observation_start_ms = 2_000_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=observation_start_ms),
        _valid_snapshot(1, fetched_at_ms=observation_start_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": observation_start_ms}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_by_reason["observation_initial_empty_book"] == 1
    assert result.invalid_book_by_phase["observation_initial"] == 1
    assert "launch_time_missing_warmup_anchor_degraded" in result.warnings


def test_invalid_book_reason_classification_precedence():
    snapshots = [
        {"event_symbol_id": None, "symbol": "SKHYUSDT", "fetched_at_ms": 0, "best_bid": None, "best_ask": -1, "spread_bps": -5},
        {"event_symbol_id": "es1", "symbol": "SKHYUSDT", "fetched_at_ms": 60_000, "best_bid": 101.0, "best_ask": 100.0, "spread_bps": -1},
        _empty_snapshot(2, fetched_at_ms=120_000),
        _valid_snapshot(3, fetched_at_ms=180_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.schema_invalid_count == 1
    assert result.crossed_or_negative_book_count == 1
    assert result.invalid_book_by_reason["observation_initial_empty_book"] == 1


def test_invalid_rows_and_minute_buckets_are_counted_separately():
    launch_ms = 1_000_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=launch_ms),
        _empty_snapshot(1, fetched_at_ms=launch_ms + 10_000),
        _valid_snapshot(2, fetched_at_ms=launch_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_row_count == 2
    assert result.invalid_book_minute_bucket_count == 1
    assert result.launch_warmup_invalid_row_count == 2
    assert result.launch_warmup_invalid_minute_bucket_count == 1


def test_book_availability_ratio_uses_expected_snapshot_count():
    snapshots = [_valid_snapshot(i) for i in range(706)] + [_empty_snapshot(706 + i) for i in range(12)]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.valid_snapshot_count_after_quarantine == 706
    assert round(result.book_availability_ratio, 4) == round(706 / 720, 4)
    assert round(result.book_unavailable_ratio, 4) == round(12 / 720, 4)


def test_invalid_book_ratio_uses_observed_snapshot_count_not_expected_count():
    snapshots = [_valid_snapshot(i) for i in range(706)] + [_empty_snapshot(706 + i) for i in range(12)]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.observed_snapshot_count == 718
    assert result.expected_snapshot_count == 720
    assert round(result.invalid_book_ratio, 4) == round(12 / 718, 4)
    assert round(result.invalid_book_ratio_observed, 4) == round(12 / 718, 4)
    assert round(result.book_availability_ratio, 4) == round(706 / 720, 4)


def test_first_valid_book_latency_above_threshold_blocks_quarantined_pass():
    launch_ms = 1_000_000
    snapshots = [_empty_snapshot(i, fetched_at_ms=launch_ms + i * 60_000) for i in range(16)]
    snapshots.extend(_valid_snapshot(16 + i, fetched_at_ms=launch_ms + (16 + i) * 60_000) for i in range(700))

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert "first_valid_book_latency_too_high" in result.blockers
    assert result.quarantined_depth_evidence_pass is False


def test_midrun_invalid_count_two_blocks_quarantined_pass():
    launch_ms = 1_000_000
    snapshots = [_valid_snapshot(i, fetched_at_ms=launch_ms + i * 60_000) for i in range(718)]
    snapshots[30] = _empty_snapshot(30, fetched_at_ms=launch_ms + 30 * 60_000)
    snapshots[60] = _empty_snapshot(60, fetched_at_ms=launch_ms + 60 * 60_000)

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.midrun_invalid_book_count == 2
    assert "midrun_invalid_book_count_exceeded" in result.blockers
    assert result.quarantined_depth_evidence_pass is False


def test_max_consecutive_invalid_uses_fetched_at_ms_order_not_jsonl_order():
    launch_ms = 1_000_000
    snapshots = [
        _empty_snapshot(2, fetched_at_ms=launch_ms + 2 * 60_000),
        _valid_snapshot(0, fetched_at_ms=launch_ms),
        _empty_snapshot(3, fetched_at_ms=launch_ms + 3 * 60_000),
        _valid_snapshot(1, fetched_at_ms=launch_ms + 1 * 60_000),
        _empty_snapshot(4, fetched_at_ms=launch_ms + 4 * 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.max_consecutive_invalid == 3
