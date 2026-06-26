from src.research.external_signal_shadow.stage1_5e_execution_feasibility_proxy import (
    compute_entry_proxy_metrics,
)


def test_compute_entry_proxy_metrics_uses_entry_and_forward_bars():
    bars = []
    interval = 15 * 60 * 1000

    # Prepend 96 pre-entry bars (24 hours) to have valid volume baseline
    # starting from time 0 to 95 * interval
    for i in range(96):
        bars.append({
            "symbol": "ABCUSDT",
            "bar_start_ms": i * interval,
            "open": 100.0,
            "high": 100.0,
            "low": 100.0,
            "close": 100.0,
            "quote_volume": 1_000_000.0,
        })

    entry_time_ms = 96 * interval

    # Entry bar and forward bars: 16 bars from index 96 to 111
    for i in range(16):
        bars.append({
            "symbol": "ABCUSDT",
            "bar_start_ms": entry_time_ms + i * interval,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "quote_volume": 1_000_000.0,
        })

    metrics = compute_entry_proxy_metrics(
        symbol="ABCUSDT",
        entry_time_ms=entry_time_ms,
        bars=bars,
    )

    assert metrics["entry_bar_found"] is True
    assert metrics["entry_bar_range_bps"] == 200.0
    assert 200.0 <= metrics["entry_1h_range_bps"] <= 205.0
    assert 200.0 <= metrics["entry_4h_range_bps"] <= 205.0
    assert metrics["post_entry_1h_quote_volume_usdt"] == 4_000_000.0
    assert metrics["volume_collapse_ratio_1h"] == 1.0
    assert "spread_proxy_bps" not in metrics
    assert "historical_spread_proxy" not in metrics


def test_compute_entry_proxy_metrics_missing_entry_bar_is_not_pass():
    metrics = compute_entry_proxy_metrics(
        symbol="ABCUSDT",
        entry_time_ms=999_999,
        bars=[],
    )

    assert metrics["entry_bar_found"] is False
    assert metrics["historical_proxy_status"] == "missing_entry_bar"


def test_volume_collapse_ratio_denominator_uses_pre_entry_24h_only():
    interval = 15 * 60 * 1000
    entry_time_ms = 100 * interval
    bars = []
    for i in range(120):
        quote_volume = 1_000_000.0 if i < 100 else 100_000_000.0
        bars.append({
            "symbol": "ABCUSDT",
            "bar_start_ms": i * interval,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "quote_volume": quote_volume,
        })

    metrics = compute_entry_proxy_metrics(
        symbol="ABCUSDT",
        entry_time_ms=entry_time_ms,
        bars=bars,
    )

    assert metrics["median_same_symbol_pre_entry_24h_hourly_volume"] == 4_000_000.0
    assert metrics["volume_collapse_ratio_1h"] == 100.0
