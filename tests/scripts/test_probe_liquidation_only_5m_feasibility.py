import os
from unittest.mock import patch

from scripts.probe_liquidation_only_5m_feasibility import (
    determine_decision,
    probe_feasibility,
)


def test_probe_feasibility_schema():
    # Mock network call to return sufficient data for all symbols
    dummy_history = [{"t": 1716800000 + i * 300, "l": 100, "s": 100} for i in range(2500)]
    mock_payload = [{"symbol": "BTCUSDT_PERP.A", "history": dummy_history}]

    with patch(
        "scripts.probe_liquidation_only_5m_feasibility.fetch_historical_liquidations",
        return_value=(mock_payload, "api_ok_non_empty_rows"),
    ):
        with patch.dict(os.environ, {"COINALYZE_API_KEY": "test_key"}):
            res = probe_feasibility(
                symbols=["BTC/USDT", "ETH/USDT"],
                lookback_days=8,
            )

    assert res["vendor"] == "coinalyze"
    assert res["interval"] == "5min"
    assert "BTC/USDT" in res["symbols_requested"]
    assert "ETH/USDT" in res["symbols_requested"]
    assert "BTC/USDT" in res["rows_per_symbol"]
    assert "ETH/USDT" in res["rows_per_symbol"]
    assert "BTC/USDT" in res["min_bar_start_ms"]
    assert "BTC/USDT" in res["max_bar_start_ms"]
    assert "BTC/USDT" in res["span_days_per_symbol"]
    assert res["supports_7d_lookback"] is True
    assert res["decision"] == "proceed"


def test_probe_feasibility_fails_if_insufficient_bars():
    # If a symbol has fewer than 2016 + 288 = 2304 bars, it doesn't support 7d lookback, decision is insufficient_5m_depth
    # Here we mock 2303 bars (one less than required)
    dummy_history = [{"t": 1716800000 + i * 300, "l": 100, "s": 100} for i in range(2303)]
    mock_payload = [{"symbol": "BTCUSDT_PERP.A", "history": dummy_history}]

    with patch(
        "scripts.probe_liquidation_only_5m_feasibility.fetch_historical_liquidations",
        return_value=(mock_payload, "api_ok_non_empty_rows"),
    ):
        with patch.dict(os.environ, {"COINALYZE_API_KEY": "test_key"}):
            res = probe_feasibility(
                symbols=["BTC/USDT"],
                lookback_days=8,
            )

    assert res["supports_7d_lookback"] is False
    assert res["decision"] == "insufficient_5m_depth"


def test_determine_decision_logic():
    # Test cases for decision maker
    # 1. proceed: all symbols have enough bars
    assert (
        determine_decision(
            rows_per_symbol={"BTC/USDT": 2304, "ETH/USDT": 2304},
            requested_symbols=["BTC/USDT", "ETH/USDT"],
            api_status="api_ok_non_empty_rows",
        )
        == "proceed"
    )

    # 2. partial_symbol_support: some symbols have enough, some don't
    assert (
        determine_decision(
            rows_per_symbol={"BTC/USDT": 2304, "ETH/USDT": 2000},
            requested_symbols=["BTC/USDT", "ETH/USDT"],
            api_status="api_ok_non_empty_rows",
        )
        == "partial_symbol_support"
    )

    # 3. insufficient_5m_depth: none of the symbols have enough
    assert (
        determine_decision(
            rows_per_symbol={"BTC/USDT": 2000, "ETH/USDT": 1000},
            requested_symbols=["BTC/USDT", "ETH/USDT"],
            api_status="api_ok_non_empty_rows",
        )
        == "insufficient_5m_depth"
    )

    # 4. api_unavailable: status is api error or no api key
    assert (
        determine_decision(
            rows_per_symbol={},
            requested_symbols=["BTC/USDT"],
            api_status="no_api_key",
        )
        == "api_unavailable"
    )
