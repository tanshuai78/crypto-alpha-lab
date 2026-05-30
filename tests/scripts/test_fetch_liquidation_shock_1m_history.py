from src.research.liquidation_shock_event_study.coinalyze_1m import (
    normalize_coinalyze_1m_payload,
    normalize_interval,
)


def test_normalize_interval_1m():
    assert normalize_interval("1m") == "1min"
    assert normalize_interval("1min") == "1min"


def test_normalize_coinalyze_1m_payload():
    raw_payload = [
        {
            "symbol": "BTCUSDT_PERP.A",
            "history": [
                {"t": 1716800000, "l": 50000.0, "s": 0.0},
                {"t": 1716800000, "l": 10000.0, "s": 20000.0},  # Duplicate t
                {"t": 1716800060, "l": 0.0, "s": 30000.0},
            ],
        }
    ]

    normalized = normalize_coinalyze_1m_payload(raw_payload, symbol="BTC/USDT")
    assert len(normalized) == 2

    # Sort to verify order
    normalized_sorted = sorted(normalized, key=lambda x: x["bar_start_ms"])

    row1 = normalized_sorted[0]
    assert row1["symbol"] == "BTC/USDT"
    assert row1["bar_start_ms"] == 1716800000000
    assert row1["long_liquidation_notional_1m_usdt"] == 60000.0
    assert row1["short_liquidation_notional_1m_usdt"] == 20000.0
    assert row1["total_liquidation_notional_1m_usdt"] == 80000.0
    assert row1["source_namespace"] == "liquidation_shock_event_study"

    row2 = normalized_sorted[1]
    assert row2["symbol"] == "BTC/USDT"
    assert row2["bar_start_ms"] == 1716800060000
    assert row2["long_liquidation_notional_1m_usdt"] == 0.0
    assert row2["short_liquidation_notional_1m_usdt"] == 30000.0
    assert row2["total_liquidation_notional_1m_usdt"] == 30000.0
    assert row2["source_namespace"] == "liquidation_shock_event_study"
