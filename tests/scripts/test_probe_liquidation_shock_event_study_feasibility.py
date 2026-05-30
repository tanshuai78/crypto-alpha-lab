import os
from unittest.mock import patch

from scripts.probe_liquidation_shock_event_study_feasibility import (
    determine_decision,
    probe_feasibility,
)


def test_probe_feasibility_schema():
    # Mock network response with enough continuous data
    # 2880 bars of 1m intervals (2 days of data: 2880 minutes)
    dummy_history = [{"t": 1716800000 + i * 60, "l": 100, "s": 100} for i in range(2900)]
    mock_payload = [{"symbol": "BTCUSDT_PERP.A", "history": dummy_history}]

    with patch(
        "scripts.probe_liquidation_shock_event_study_feasibility.fetch_historical_liquidations",
        return_value=(mock_payload, "api_ok_non_empty_rows"),
    ):
        with patch.dict(os.environ, {"COINALYZE_API_KEY": "test_key"}):
            res = probe_feasibility(
                symbols=["BTC/USDT", "ETH/USDT"],
                lookback_days=2.5,
            )

    assert res["vendor"] == "coinalyze"
    assert res["interval"] == "1min"
    assert "BTC/USDT" in res["symbols_requested"]
    assert res["supports_24h_lookback"] is True
    assert res["decision"] == "proceed"

    # Check that required output fields exist
    assert "coverage_ratio" in res
    assert "max_gap_minutes" in res
    assert "usable_eval_hours_after_lookback" in res
    assert "qualified_symbols" in res


def test_probe_feasibility_fails_if_gaps_too_large():
    # If the maximum gap between consecutive returned bars is larger than threshold, it fails
    # Let's mock a gap of 200 minutes (threshold is 180)
    dummy_history = [
        {"t": 1716800000, "l": 100, "s": 100},
        {"t": 1716800000 + 200 * 60, "l": 100, "s": 100},  # 200 minute gap
    ]
    # Fill up the rest so actual_1m_bars is large enough
    dummy_history.extend(
        [{"t": 1716800000 + (200 + i) * 60, "l": 100, "s": 100} for i in range(2800)]
    )
    mock_payload = [{"symbol": "BTCUSDT_PERP.A", "history": dummy_history}]

    with patch(
        "scripts.probe_liquidation_shock_event_study_feasibility.fetch_historical_liquidations",
        return_value=(mock_payload, "api_ok_non_empty_rows"),
    ):
        with patch.dict(os.environ, {"COINALYZE_API_KEY": "test_key"}):
            res = probe_feasibility(
                symbols=["BTC/USDT"],
                lookback_days=2.5,
            )

    assert res["supports_24h_lookback"] is False
    assert res["decision"] == "insufficient_1m_data_depth"


def test_determine_decision_logic():
    # Test decision maker with different values

    # 1. proceed: all symbols qualify
    assert (
        determine_decision(
            symbol_stats={
                "BTC/USDT": {"qualified": True},
                "ETH/USDT": {"qualified": True},
            },
            requested_symbols=["BTC/USDT", "ETH/USDT"],
            api_status="api_ok_non_empty_rows",
        )
        == "proceed"
    )

    # 2. partial_symbol_support: some qualify, some don't
    assert (
        determine_decision(
            symbol_stats={
                "BTC/USDT": {"qualified": True},
                "ETH/USDT": {"qualified": False},
            },
            requested_symbols=["BTC/USDT", "ETH/USDT"],
            api_status="api_ok_non_empty_rows",
        )
        == "partial_symbol_support"
    )

    # 3. insufficient_1m_data_depth: none qualify
    assert (
        determine_decision(
            symbol_stats={
                "BTC/USDT": {"qualified": False},
                "ETH/USDT": {"qualified": False},
            },
            requested_symbols=["BTC/USDT", "ETH/USDT"],
            api_status="api_ok_non_empty_rows",
        )
        == "insufficient_1m_data_depth"
    )

    # 4. api_unavailable: status is api error
    assert (
        determine_decision(
            symbol_stats={},
            requested_symbols=["BTC/USDT"],
            api_status="no_api_key",
        )
        == "api_unavailable"
    )
