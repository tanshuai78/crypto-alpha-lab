import pytest

from src.research.liquidation_only_5m.baseline import LiquidationOnly5mEvent
from src.research.liquidation_only_5m.forward_returns import (
    aggregate_forward_returns,
    compute_event_forward_returns,
)


def test_forward_returns_for_single_event():
    event = LiquidationOnly5mEvent(
        symbol="BTC/USDT",
        bar_start_ms=1000,
        liquidated_position_side="short",  # continuation is long, reversion is short
        dominant_liquidation_side="short",
        continuation_trade_side="long",
        mean_reversion_trade_side="short",
        dominance_ratio=1.0,
    )

    # 4 bars: index 0 (event at 1000ms), 1 (next bar open/close), 2 (+2 close), 3 (+3 close)
    sym_rows = [
        {"bar_start_ms": 1000, "open_price": 100.0, "close_price": 100.0},
        {"bar_start_ms": 1300, "open_price": 101.0, "close_price": 102.0},  # h=1
        {"bar_start_ms": 1600, "open_price": 102.0, "close_price": 103.0},  # h=2
        {"bar_start_ms": 1900, "open_price": 103.0, "close_price": 104.0},  # h=3
    ]

    ret = compute_event_forward_returns(event, sym_rows, event_index=0)
    assert ret is not None
    assert ret["symbol"] == "BTC/USDT"
    assert ret["bar_start_ms"] == 1000

    h1 = ret["horizons"][1]
    # continuation is long: entry = 101.0, exit = 102.0. Gross return = (102.0/101.0 - 1.0) * 10000.0 = 99.0099 bps
    # Cost = 16 bps, cost adjusted return = 99.0099 - 16 = 83.0099 bps
    assert pytest.approx(h1["continuation"]["gross_next_open_to_horizon_close_bps"], 0.01) == 99.01
    assert (
        pytest.approx(h1["continuation"]["cost_adjusted_next_open_to_horizon_close_bps"], 0.01)
        == 83.01
    )

    # close to close: entry = 100.0, exit = 102.0. Return = (102.0/100.0 - 1.0) * 10000 = 200 bps
    assert pytest.approx(h1["continuation"]["gross_close_to_close_bps"], 0.01) == 200.0
    assert pytest.approx(h1["continuation"]["cost_adjusted_close_to_close_bps"], 0.01) == 184.0

    # reversion is short: negative of continuation
    assert (
        pytest.approx(h1["mean_reversion"]["gross_next_open_to_horizon_close_bps"], 0.01) == -99.01
    )
    assert (
        pytest.approx(h1["mean_reversion"]["cost_adjusted_next_open_to_horizon_close_bps"], 0.01)
        == -115.01
    )


def test_event_without_full_horizon_is_dropped():
    event = LiquidationOnly5mEvent(
        symbol="BTC/USDT",
        bar_start_ms=1000,
        liquidated_position_side="short",
        dominant_liquidation_side="short",
        continuation_trade_side="long",
        mean_reversion_trade_side="short",
        dominance_ratio=1.0,
    )

    # Insufficient bars for horizon +3
    sym_rows = [
        {"bar_start_ms": 1000, "open_price": 100.0, "close_price": 100.0},
        {"bar_start_ms": 1300, "open_price": 101.0, "close_price": 102.0},
    ]

    ret = compute_event_forward_returns(event, sym_rows, event_index=0)
    assert ret is None


def test_aggregate_forward_returns():
    event_returns = [
        {
            "symbol": "BTC/USDT",
            "bar_start_ms": 1000,
            "horizons": {
                1: {
                    "continuation": {
                        "gross_next_open_to_horizon_close_bps": 10.0,
                        "cost_adjusted_next_open_to_horizon_close_bps": -6.0,
                        "gross_close_to_close_bps": 15.0,
                        "cost_adjusted_close_to_close_bps": -1.0,
                    },
                    "mean_reversion": {
                        "gross_next_open_to_horizon_close_bps": -10.0,
                        "cost_adjusted_next_open_to_horizon_close_bps": -26.0,
                        "gross_close_to_close_bps": -15.0,
                        "cost_adjusted_close_to_close_bps": -31.0,
                    },
                }
            },
        },
        {
            "symbol": "BTC/USDT",
            "bar_start_ms": 2000,
            "horizons": {
                1: {
                    "continuation": {
                        "gross_next_open_to_horizon_close_bps": -5.0,
                        "cost_adjusted_next_open_to_horizon_close_bps": -21.0,
                        "gross_close_to_close_bps": -10.0,
                        "cost_adjusted_close_to_close_bps": -26.0,
                    },
                    "mean_reversion": {
                        "gross_next_open_to_horizon_close_bps": 5.0,
                        "cost_adjusted_next_open_to_horizon_close_bps": -11.0,
                        "gross_close_to_close_bps": 10.0,
                        "cost_adjusted_close_to_close_bps": -6.0,
                    },
                }
            },
        },
    ]

    summary = aggregate_forward_returns(event_returns)
    assert summary[1]["continuation"]["event_count"] == 2
    # Gross: [10.0, -5.0]. Mean = 2.5, Median = 2.5, Win rate = 0.5, worst = -5.0
    assert summary[1]["continuation"]["mean_gross_bps"] == 2.5
    assert summary[1]["continuation"]["median_gross_bps"] == 2.5
    assert summary[1]["continuation"]["gross_win_rate"] == 0.5
    assert summary[1]["continuation"]["worst_gross_bps"] == -5.0

    # Cost adjusted: [-6.0, -21.0]. Mean = -13.5, Median = -13.5, Win rate = 0.0, worst = -21.0
    assert summary[1]["continuation"]["mean_cost_adjusted_bps"] == -13.5
    assert summary[1]["continuation"]["median_cost_adjusted_bps"] == -13.5
    assert summary[1]["continuation"]["cost_adjusted_win_rate"] == 0.0
    assert summary[1]["continuation"]["worst_cost_adjusted_bps"] == -21.0
