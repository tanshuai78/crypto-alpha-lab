"""
tests/research/external_signal_shadow/test_stage1_4a_price.py
"""

from research.external_signal_shadow.stage1_4a_price import audit_price_source_rows


def test_price_history_days_is_computed_not_stubbed():
    # 15m kline interval = 900,000 ms
    interval = 15 * 60 * 1000

    # 10 days of price bars (10 * 24 * 4 = 960 bars)
    total_bars = 960
    timestamps = [i * interval for i in range(total_bars)]

    rows = [
        {"symbol": "BTCUSDT", "close_price": 50000.0 + i, "bar_start_ms": ts}
        for i, ts in enumerate(timestamps)
    ]

    res = audit_price_source_rows(rows, "BTCUSDT", "futures_klines")

    # The history days should be exactly (959 * 15 * 60 * 1000) / (24 * 3600 * 1000) = 9.9895...
    assert 9.9 < res["price_history_days"] < 10.0
    assert res["price_bar_count"] == 960
    assert res["price_bar_coverage_ratio"] == 1.0
    assert res["time_coverage_ratio"] == 1.0


def test_price_coverage_below_min_can_block_summary():
    interval = 15 * 60 * 1000
    # Create 100 bars but drop 10 in the middle
    timestamps = [i * interval for i in range(100)]
    for idx in range(40, 50):
        timestamps.remove(idx * interval)

    rows = [
        {"symbol": "BTCUSDT", "close_price": 50000.0, "bar_start_ms": ts}
        for ts in timestamps
    ]

    res = audit_price_source_rows(rows, "BTCUSDT", "futures_klines")
    # Coverage: 90 / 100 = 0.90
    assert res["time_coverage_ratio"] == 0.90
    assert res["gap_count"] == 1
    assert res["max_gap_ms"] == 11 * interval


def test_price_source_defaults_to_futures_klines():
    rows = [{"symbol": "BTCUSDT", "close_price": 50000.0, "bar_start_ms": 0}]
    res = audit_price_source_rows(rows, "BTCUSDT", "futures_klines")
    assert res["price_source"] == "futures_klines"
    assert res["price_venue_proxy_used"] is False


def test_spot_proxy_is_marked_as_proxy():
    rows = [{"symbol": "BTCUSDT", "close_price": 50000.0, "bar_start_ms": 0}]
    res = audit_price_source_rows(rows, "BTCUSDT", "spot_klines_proxy")
    assert res["price_source"] == "spot_klines_proxy"
    assert res["price_venue_proxy_used"] is True
