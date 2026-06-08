from __future__ import annotations

import pandas as pd


def compute_turnover(previous_weights: dict[str, float], target_weights: dict[str, float]) -> float:
    all_symbols = set(previous_weights.keys()) | set(target_weights.keys())
    turnover = 0.0
    for symbol in all_symbols:
        w_prev = previous_weights.get(symbol, 0.0)
        w_target = target_weights.get(symbol, 0.0)
        turnover += abs(w_target - w_prev)
    return turnover


def apply_turnover_cost(gross_return: float, turnover: float, round_trip_cost_bps: float) -> float:
    # one-way cost in decimals
    one_way_cost = (round_trip_cost_bps / 10000.0) / 2.0
    return gross_return - (turnover * one_way_cost)


def compute_benchmark_buy_and_hold_net(
    start_open: float, end_close: float, round_trip_cost_bps: float
) -> float:
    gross_return = (end_close / start_open) - 1.0
    cost = round_trip_cost_bps / 10000.0
    return gross_return - cost


def universe_equal_weight_targets(eligible: pd.DataFrame) -> pd.DataFrame:
    if eligible.empty:
        return pd.DataFrame(columns=["symbol", "target_weight"])
    n = len(eligible)
    result = eligible.copy()
    result["target_weight"] = 1.0 / n
    return result[["symbol", "target_weight"]]


def compute_strategy_period_return(
    panel: pd.DataFrame, weights: dict[str, float], entry_date: pd.Timestamp, exit_date: pd.Timestamp
) -> float | None:
    if not weights:
        return 0.0

    # If the exit date is not in the panel at all, it's the final incomplete period past the end of the dataset.
    # We must drop it.
    if panel[panel["date_utc"] == exit_date].empty:
        return None

    total_return = 0.0
    for symbol, weight in weights.items():
        symbol_data = panel[panel["symbol"] == symbol]
        entry_row = symbol_data[symbol_data["date_utc"] == entry_date]
        exit_row = symbol_data[symbol_data["date_utc"] == exit_date]

        if entry_row.empty or exit_row.empty:
            continue

        p_entry = float(entry_row["open"].iloc[0])
        p_exit = float(exit_row["open"].iloc[0])

        if p_entry <= 0:
            continue

        symbol_return = (p_exit / p_entry) - 1.0
        total_return += symbol_return * weight

    return total_return
