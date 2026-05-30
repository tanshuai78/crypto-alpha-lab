import pytest
from scripts.build_liquidation_shock_event_dataset import build_aligned_1m_dataset


def test_build_aligned_1m_dataset_basic():
    price_rows = [
        {"symbol": "BTC/USDT", "timestamp_ms": 1716800000000, "open": 60000.0, "high": 60100.0, "low": 59900.0, "close": 60050.0},
        {"symbol": "BTC/USDT", "timestamp_ms": 1716800060000, "open": 60050.0, "high": 60200.0, "low": 60000.0, "close": 60150.0},
    ]

    liq_rows = [
        {"symbol": "BTC/USDT", "bar_start_ms": 1716800000000, "long_liquidation_notional_1m_usdt": 10000.0, "short_liquidation_notional_1m_usdt": 0.0, "total_liquidation_notional_1m_usdt": 10000.0},
    ]

    joined, audit = build_aligned_1m_dataset(price_rows, liq_rows)

    assert len(joined) == 2
    assert audit["price_rows"] == 2
    assert audit["liquidation_rows"] == 1
    assert audit["joined_rows"] == 2
    assert audit["missing_liquidation_bar_count"] == 1

    # First row has liquidation
    r0 = next(x for x in joined if x["bar_start_ms"] == 1716800000000)
    assert r0["open_price"] == 60000.0
    assert r0["close_price"] == 60050.0
    assert r0["long_liquidation_notional_1m_usdt"] == 10000.0
    assert r0["short_liquidation_notional_1m_usdt"] == 0.0
    assert r0["total_liquidation_notional_1m_usdt"] == 10000.0

    # Second row has zero liquidation (filled gap)
    r1 = next(x for x in joined if x["bar_start_ms"] == 1716800060000)
    assert r1["open_price"] == 60050.0
    assert r1["close_price"] == 60150.0
    assert r1["long_liquidation_notional_1m_usdt"] == 0.0
    assert r1["short_liquidation_notional_1m_usdt"] == 0.0
    assert r1["total_liquidation_notional_1m_usdt"] == 0.0
