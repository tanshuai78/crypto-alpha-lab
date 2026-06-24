from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_quality import (
    build_price_index,
    compute_price_interval_stats,
    evaluate_event_price_coverage,
)


def _bar(symbol, t, close=100.0, quote_volume=10_000_000):
    return {
        "symbol": symbol,
        "bar_start_ms": t,
        "bar_end_ms": t + 900_000,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "quote_volume": quote_volume,
    }


def test_price_interval_stats_accepts_15m_bars():
    bars = [_bar("ABCUSDT", i * 900_000) for i in range(10)]
    stats = compute_price_interval_stats(bars)
    assert stats["median_interval_ms"] == 900_000
    assert stats["p95_interval_ms"] == 900_000
    assert stats["price_interval_supported"] is True


def test_event_price_coverage_rejects_missing_entry_bar():
    price_index = build_price_index([_bar("ABCUSDT", 0)])
    report = evaluate_event_price_coverage(
        event={"symbol": "ABCUSDT", "available_at_ms": 0},
        price_index=price_index,
        entry_delay_hours=1,
        forward_windows_hours=(1, 4),
    )
    assert report["price_coverage_gate_passed"] is False
    assert report["candidate_allowed_for_close_price_replay"] is False
    assert report["coverage_reject_reason"] == "missing_entry_bar"


def test_event_price_coverage_accepts_complete_forward_windows():
    bars = [_bar("ABCUSDT", i * 900_000, close=100 + i) for i in range(0, 30 * 24 * 4 + 30)]
    event_time = 30 * 24 * 4 * 900_000
    price_index = build_price_index(bars)
    report = evaluate_event_price_coverage(
        event={"symbol": "ABCUSDT", "available_at_ms": event_time},
        price_index=price_index,
        entry_delay_hours=1,
        forward_windows_hours=(1, 4),
    )
    assert report["price_coverage_gate_passed"] is True
    assert report["candidate_allowed_for_close_price_replay"] is True
    assert report["market_pair_existence_verified"] is True
    assert report["price_history_coverage_verified"] is True


def test_price_coverage_and_liquidity_proxy_are_reported_separately():
    bars = [_bar("ABCUSDT", i * 900_000, close=100 + i, quote_volume=1_000) for i in range(0, 30 * 24 * 4 + 30)]
    event_time = 30 * 24 * 4 * 900_000
    report = evaluate_event_price_coverage(
        event={"symbol": "ABCUSDT", "available_at_ms": event_time},
        price_index=build_price_index(bars),
        entry_delay_hours=1,
        forward_windows_hours=(1, 4),
    )
    assert report["price_coverage_gate_passed"] is True
    assert report["candidate_allowed_for_close_price_replay"] is True
    assert report["liquidity_proxy_pass"] is False
    assert report["candidate_allowed_for_execution_relevance"] is False
