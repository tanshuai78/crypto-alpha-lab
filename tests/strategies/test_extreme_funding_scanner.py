from strategies.extreme_funding.scanner import (
    ExtremeFundingWatchEvent,
    ExtremeFundingWatchlistScanner,
    ExtremeFundingClassification,
    classify_extreme_funding_snapshot,
    compute_micro_persistence,
)
import pytest


def test_watch_event_contract_is_observation_only():
    event = ExtremeFundingWatchEvent(
        strategy_type="extreme_funding",
        symbol="DOGE/USDT",
        exchange="binance",
        level="watch_level_1",
        premium_annualized_estimate_pct=35.0,
        micro_persistence=0.55,
        oi_change_1h_pct=None,
        reason="premium_persistent",
        reject_reason=None,
        executable=False,
        metadata={
            "mode": "observation",
            "estimate_type": "naive_premium_annualization",
            "not_settled_funding": True,
        },
    )

    assert event.strategy_type == "extreme_funding"
    assert event.executable is False
    assert event.metadata["mode"] == "observation"
    assert event.metadata["estimate_type"] == "naive_premium_annualization"
    assert event.metadata["not_settled_funding"] is True


def test_missing_premium_is_rejected():
    result = classify_extreme_funding_snapshot({"symbol": "DOGE/USDT", "timestamp_ms": 1})
    assert result.reject_reason == "missing_premium"
    assert result.event is None


def test_stale_mark_data_is_rejected():
    result = classify_extreme_funding_snapshot(
        {
            "symbol": "DOGE/USDT",
            "timestamp_ms": 1,
            "premium_index": 0.001,
            "mark_data_age_sec": 31,
        }
    )
    assert result.reject_reason == "api_stale"
    assert result.event is None


def test_symbol_outside_watchlist_is_rejected():
    result = classify_extreme_funding_snapshot(
        {
            "symbol": "UNKNOWN/USDT",
            "timestamp_ms": 1,
            "premium_index": 0.001,
            "mark_data_age_sec": 1,
        }
    )
    assert result.reject_reason == "symbol_not_in_watchlist"
    assert result.event is None


def test_micro_persistence_counts_fraction_above_threshold():
    values = [10.0, 35.0, 40.0, 20.0]
    assert compute_micro_persistence(values, threshold_pct=30.0) == 0.5


def test_micro_persistence_empty_window_is_zero():
    assert compute_micro_persistence([], threshold_pct=30.0) == 0.0


def test_micro_persistence_uses_timestamp_window_not_sample_count():
    scanner = ExtremeFundingWatchlistScanner()
    scanner.append_observation("DOGE/USDT", timestamp_ms=0, annualized_pct=120.0)
    scanner.append_observation("DOGE/USDT", timestamp_ms=31 * 60_000, annualized_pct=10.0)

    values = scanner.get_window_values("DOGE/USDT", now_ms=31 * 60_000)

    assert values == [10.0]


def _snapshot(**overrides):
    base = {
        "symbol": "DOGE/USDT",
        "exchange": "binance",
        "timestamp_ms": 1,
        "premium_index": 0.001,
        "estimated_funding_rate": 0.0008,
        "open_interest": 1_000_000.0,
        "oi_change_1h_pct": 0.0,
        "volume_24h_usdt": 100_000_000.0,
        "mark_data_age_sec": 1.0,
        "oi_data_age_sec": 1.0,
    }
    base.update(overrides)
    return base


def test_premium_spike_without_persistence_is_rejected():
    scanner = ExtremeFundingWatchlistScanner()
    result = scanner.classify(_snapshot(premium_annualized_estimate_pct=80.0))
    assert result.event is None
    assert result.reject_reason == "micro_persistence_below_threshold"


def test_persistent_premium_with_weak_oi_returns_level_1():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(20):
        scanner.classify(
            _snapshot(
                timestamp_ms=minute * 60_000,
                premium_annualized_estimate_pct=35.0,
            )
        )
    result = scanner.classify(
        _snapshot(
            timestamp_ms=20 * 60_000,
            premium_annualized_estimate_pct=35.0,
        )
    )
    assert result.event is not None
    assert result.event.level == "watch_level_1"
    assert result.event.executable is False


def test_persistent_premium_with_oi_expansion_returns_level_2():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        scanner.classify(
            _snapshot(
                timestamp_ms=minute * 60_000,
                premium_annualized_estimate_pct=60.0,
                oi_change_1h_pct=1.0,
            )
        )
    result = scanner.classify(
        _snapshot(
            timestamp_ms=30 * 60_000,
            premium_annualized_estimate_pct=60.0,
            oi_change_1h_pct=1.0,
        )
    )
    assert result.event is not None
    assert result.event.level == "watch_level_2"


def test_strong_premium_with_strong_oi_returns_level_3():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        scanner.classify(
            _snapshot(
                timestamp_ms=minute * 60_000,
                premium_annualized_estimate_pct=120.0,
                oi_change_1h_pct=4.0,
            )
        )
    result = scanner.classify(
        _snapshot(
            timestamp_ms=30 * 60_000,
            premium_annualized_estimate_pct=120.0,
            oi_change_1h_pct=4.0,
        )
    )
    assert result.event is not None
    assert result.event.level == "watch_level_3"


def test_persistent_premium_with_missing_oi_returns_level_1_with_oi_missing_metadata():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        scanner.classify(
            _snapshot(
                timestamp_ms=minute * 60_000,
                premium_annualized_estimate_pct=60.0,
                oi_change_1h_pct=None,
            )
        )
    result = scanner.classify(
        _snapshot(
            timestamp_ms=30 * 60_000,
            premium_annualized_estimate_pct=60.0,
            oi_change_1h_pct=None,
        )
    )
    assert result.event is not None
    assert result.event.level == "watch_level_1"
    assert result.event.metadata["oi_status"] == "missing"
    assert result.reject_reason is None


def test_persistent_premium_with_stale_oi_returns_level_1_with_oi_stale_metadata():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        scanner.classify(
            _snapshot(
                timestamp_ms=minute * 60_000,
                premium_annualized_estimate_pct=60.0,
                oi_data_age_sec=181,
            )
        )
    result = scanner.classify(
        _snapshot(
            timestamp_ms=30 * 60_000,
            premium_annualized_estimate_pct=60.0,
            oi_data_age_sec=181,
        )
    )

    assert result.event is not None
    assert result.event.level == "watch_level_1"
    assert result.event.metadata["oi_status"] == "stale"
    assert result.reject_reason is None


@pytest.mark.asyncio
async def test_scan_returns_watch_events_not_signal_candidates():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        await scanner.scan(
            _snapshot(
                timestamp_ms=minute * 60_000,
                premium_annualized_estimate_pct=60.0,
                oi_change_1h_pct=1.0,
            )
        )

    events = await scanner.scan(
        _snapshot(
            timestamp_ms=30 * 60_000,
            premium_annualized_estimate_pct=60.0,
            oi_change_1h_pct=1.0,
        )
    )

    assert len(events) == 1
    assert isinstance(events[0], ExtremeFundingWatchEvent)
    assert events[0].executable is False
