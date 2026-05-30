import pytest
from src.research.liquidation_shock_event_study.event_contract import LiquidationShockEvent
from src.research.liquidation_shock_event_study.response_map import (
    build_response_map,
)


def test_build_response_map_success():
    event = LiquidationShockEvent(
        symbol="BTC/USDT",
        shock_bar_start_ms=1716800000000,  # M = 0
        liquidated_position_side="long",
        dominant_liquidation_side="long",
        shock_notional_usdt=60000.0,
        relative_score=0.995,
        relative_score_method="percentile_rank",
        reference_count=1440,
        required_reference_count=1440,
        dominance_ratio=1.0,
        dedup_bucket_start_ms=1716800000000,
    )

    # We need price bars at:
    # entry: M+1 = 1716800060000
    # exit_5m: M+5 = 1716800300000
    # exit_10m: M+10 = 1716800600000
    # exit_15m: M+15 = 1716800900000
    price_map = {
        1716800060000: {"open_price": 60000.0, "close_price": 60050.0},
        1716800300000: {"open_price": 59950.0, "close_price": 59900.0},  # Price down 100 bps
        1716800600000: {"open_price": 59850.0, "close_price": 59800.0},  # Price down 200 bps
        1716800900000: {"open_price": 60100.0, "close_price": 60060.0},  # Price up 10 bps
    }

    # Expected direction is "down" (long liquidation)
    # entry_price = 60000.0 (open of M+1)
    # exit_5m = 59900.0 (close of M+5). Change = (59900 - 60000)/60000 * 10000 = -16.67 bps.
    # Expected is down, so directional_change = +16.67 bps.

    res = build_response_map(event, price_map, min_move_bps=10.0)
    assert res is not None
    assert res["entry_price"] == 60000.0
    assert res["exit_prices"] == {5: 59900.0, 10: 59800.0, 15: 60060.0}

    # 5m horizon
    assert round(res["bps_changes"][5], 2) == -16.67
    assert round(res["directional_bps"][5], 2) == 16.67
    assert res["sign_directions"][5] == 1  # Moved in expected direction (down)
    assert res["min_move_directions"][5] == 1  # 16.67 bps > 10.0 bps threshold

    # 15m horizon
    # exit_15m = 60060.0. Change = (60060 - 60000)/60000 * 10000 = +10 bps.
    # Expected is down, so directional_change = -10 bps.
    assert round(res["bps_changes"][15], 2) == 10.0
    assert round(res["directional_bps"][15], 2) == -10.0
    assert res["sign_directions"][15] == -1
    assert res["min_move_directions"][15] == -1


def test_build_response_map_missing_exit_returns_none():
    event = LiquidationShockEvent(
        symbol="BTC/USDT",
        shock_bar_start_ms=1716800000000,
        liquidated_position_side="long",
        dominant_liquidation_side="long",
        shock_notional_usdt=60000.0,
        relative_score=0.995,
        relative_score_method="percentile_rank",
        reference_count=1440,
        required_reference_count=1440,
        dominance_ratio=1.0,
        dedup_bucket_start_ms=1716800000000,
    )

    price_map = {
        1716800060000: {"open_price": 60000.0, "close_price": 60050.0},
        1716800300000: {"open_price": 59950.0, "close_price": 59900.0},
        # Missing M+10 and M+15
    }

    res = build_response_map(event, price_map, min_move_bps=10.0)
    assert res is None
