from strategies.extreme_funding.scanner import (
    ExtremeFundingWatchEvent,
    ExtremeFundingWatchlistScanner,
    classify_extreme_funding_snapshot,
    compute_micro_persistence,
)


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
