from __future__ import annotations

import pandas as pd
import pytest

from research.cross_sectional_factor_lab.backtest import (
    apply_turnover_cost,
    compute_benchmark_buy_and_hold_net,
    compute_strategy_period_return,
    compute_turnover,
    universe_equal_weight_targets,
)


def test_turnover_is_sum_abs_target_minus_previous_weight() -> None:
    prev = {"AAAUSDT": 0.5, "BBBUSDT": 0.5}
    target = {"CCCUSDT": 0.5, "DDDUSDT": 0.5}

    assert compute_turnover(prev, target) == pytest.approx(2.0)


def test_apply_turnover_cost_uses_one_way_cost_from_round_trip() -> None:
    after_cost = apply_turnover_cost(gross_return=0.10, turnover=2.0, round_trip_cost_bps=30.0)

    assert after_cost == pytest.approx(0.10 - 0.003)


def test_btc_eth_buy_and_hold_applies_entry_exit_cost() -> None:
    net = compute_benchmark_buy_and_hold_net(
        start_open=100.0,
        end_close=120.0,
        round_trip_cost_bps=30.0,
    )

    assert net < 0.20


def test_universe_equal_weight_uses_same_point_in_time_eligible_universe() -> None:
    eligible = pd.DataFrame({"symbol": ["AAAUSDT", "BBBUSDT"]})

    targets = universe_equal_weight_targets(eligible)

    assert set(targets["symbol"]) == {"AAAUSDT", "BBBUSDT"}
    assert targets["target_weight"].sum() == pytest.approx(1.0)


def test_strategy_period_return_uses_rebalance_open_to_next_rebalance_open() -> None:
    panel = pd.DataFrame(
        [
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-02"), "open": 100.0, "close": 999.0},
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-09"), "open": 110.0, "close": 1.0},
        ]
    )

    result = compute_strategy_period_return(
        panel=panel,
        weights={"AAAUSDT": 1.0},
        entry_date=pd.Timestamp("2026-02-02"),
        exit_date=pd.Timestamp("2026-02-09"),
    )

    assert result == pytest.approx(0.10)


def test_does_not_use_rebalance_day_close_for_entry() -> None:
    panel = pd.DataFrame(
        [
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-02"), "open": 100.0, "close": 10_000.0},
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-09"), "open": 100.0, "close": 1.0},
        ]
    )

    result = compute_strategy_period_return(
        panel=panel,
        weights={"AAAUSDT": 1.0},
        entry_date=pd.Timestamp("2026-02-02"),
        exit_date=pd.Timestamp("2026-02-09"),
    )

    assert result == pytest.approx(0.0)


def test_final_period_without_available_exit_open_is_dropped() -> None:
    panel = pd.DataFrame(
        [{"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-02"), "open": 100.0, "close": 120.0}]
    )

    result = compute_strategy_period_return(
        panel=panel,
        weights={"AAAUSDT": 1.0},
        entry_date=pd.Timestamp("2026-02-02"),
        exit_date=pd.Timestamp("2026-02-09"),
    )

    assert result is None
