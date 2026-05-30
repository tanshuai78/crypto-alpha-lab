from __future__ import annotations

import statistics
from typing import Any

import configs.base as cfg
from src.research.liquidation_only_5m.baseline import LiquidationOnly5mEvent


def compute_event_forward_returns(
    event: LiquidationOnly5mEvent,
    sym_rows: list[dict[str, Any]],
    event_index: int,
) -> dict[str, Any] | None:
    # We require at least 3 bars after the event index to cover the max horizon (+3 bars)
    max_horizon = 3
    if event_index + max_horizon >= len(sym_rows):
        return None

    entry_row = sym_rows[event_index + 1]
    entry_price = float(entry_row.get("open_price") or entry_row.get("open") or 0.0)
    close_entry_price = float(
        sym_rows[event_index].get("close_price") or sym_rows[event_index].get("close") or 0.0
    )

    if entry_price <= 0.0 or close_entry_price <= 0.0:
        return None

    cost_bps = cfg.LIQUIDATION_ONLY_5M_ASSUMED_MIN_ROUND_TRIP_COST_BPS

    horizons = {}
    for h in range(1, max_horizon + 1):
        exit_row = sym_rows[event_index + h]
        exit_price = float(exit_row.get("close_price") or exit_row.get("close") or 0.0)
        if exit_price <= 0.0:
            return None

        # Continuation
        if event.continuation_trade_side == "long":
            gross_next_open = (exit_price / entry_price - 1.0) * 10_000.0
            gross_close_close = (exit_price / close_entry_price - 1.0) * 10_000.0
        else:
            gross_next_open = (1.0 - exit_price / entry_price) * 10_000.0
            gross_close_close = (1.0 - exit_price / close_entry_price) * 10_000.0

        cost_adj_next_open = gross_next_open - cost_bps
        cost_adj_close_close = gross_close_close - cost_bps

        # Mean Reversion (opposite direction of continuation)
        gross_next_open_rev = -gross_next_open
        gross_close_close_rev = -gross_close_close
        cost_adj_next_open_rev = gross_next_open_rev - cost_bps
        cost_adj_close_close_rev = gross_close_close_rev - cost_bps

        horizons[h] = {
            "continuation": {
                "gross_next_open_to_horizon_close_bps": gross_next_open,
                "cost_adjusted_next_open_to_horizon_close_bps": cost_adj_next_open,
                "gross_close_to_close_bps": gross_close_close,
                "cost_adjusted_close_to_close_bps": cost_adj_close_close,
            },
            "mean_reversion": {
                "gross_next_open_to_horizon_close_bps": gross_next_open_rev,
                "cost_adjusted_next_open_to_horizon_close_bps": cost_adj_next_open_rev,
                "gross_close_to_close_bps": gross_close_close_rev,
                "cost_adjusted_close_to_close_bps": cost_adj_close_close_rev,
            },
        }

    return {
        "symbol": event.symbol,
        "bar_start_ms": event.bar_start_ms,
        "liquidated_position_side": event.liquidated_position_side,
        "dominance_ratio": event.dominance_ratio,
        "horizons": horizons,
    }


def aggregate_forward_returns(
    event_returns: list[dict[str, Any]],
) -> dict[int, dict[str, dict[str, Any]]]:
    # Aggregate stats per horizon (1, 2, 3) and per hypothesis (continuation, mean_reversion)
    horizons = [1, 2, 3]
    hypotheses = ["continuation", "mean_reversion"]

    summary: dict[int, dict[str, dict[str, Any]]] = {}

    for h in horizons:
        summary[h] = {}
        for hyp in hypotheses:
            next_open_gross = []
            next_open_cost_adj = []
            close_close_gross = []
            close_close_cost_adj = []

            for r in event_returns:
                if h in r["horizons"]:
                    stats = r["horizons"][h][hyp]
                    next_open_gross.append(stats["gross_next_open_to_horizon_close_bps"])
                    next_open_cost_adj.append(stats["cost_adjusted_next_open_to_horizon_close_bps"])
                    close_close_gross.append(stats["gross_close_to_close_bps"])
                    close_close_cost_adj.append(stats["cost_adjusted_close_to_close_bps"])

            event_count = len(next_open_gross)
            if event_count > 0:
                mean_gross = sum(next_open_gross) / event_count
                median_gross = statistics.median(next_open_gross)
                worst_gross = min(next_open_gross)
                win_rate_gross = sum(1 for x in next_open_gross if x > 0) / event_count

                mean_cost = sum(next_open_cost_adj) / event_count
                median_cost = statistics.median(next_open_cost_adj)
                worst_cost = min(next_open_cost_adj)
                win_rate_cost = sum(1 for x in next_open_cost_adj if x > 0) / event_count

                mean_cc_gross = sum(close_close_gross) / event_count
                median_cc_gross = statistics.median(close_close_gross)
                worst_cc_gross = min(close_close_gross)
                win_rate_cc_gross = sum(1 for x in close_close_gross if x > 0) / event_count

                mean_cc_cost = sum(close_close_cost_adj) / event_count
                median_cc_cost = statistics.median(close_close_cost_adj)
                worst_cc_cost = min(close_close_cost_adj)
                win_rate_cc_cost = sum(1 for x in close_close_cost_adj if x > 0) / event_count
            else:
                mean_gross = median_gross = worst_gross = win_rate_gross = 0.0
                mean_cost = median_cost = worst_cost = win_rate_cost = 0.0
                mean_cc_gross = median_cc_gross = worst_cc_gross = win_rate_cc_gross = 0.0
                mean_cc_cost = median_cc_cost = worst_cc_cost = win_rate_cc_cost = 0.0

            summary[h][hyp] = {
                "event_count": event_count,
                "mean_gross_bps": mean_gross,
                "median_gross_bps": median_gross,
                "worst_gross_bps": worst_gross,
                "gross_win_rate": win_rate_gross,
                "mean_cost_adjusted_bps": mean_cost,
                "median_cost_adjusted_bps": median_cost,
                "worst_cost_adjusted_bps": worst_cost,
                "cost_adjusted_win_rate": win_rate_cost,
                "mean_close_to_close_gross_bps": mean_cc_gross,
                "median_close_to_close_gross_bps": median_cc_gross,
                "worst_close_to_close_gross_bps": worst_cc_gross,
                "close_to_close_gross_win_rate": win_rate_cc_gross,
                "mean_close_to_close_cost_adjusted_bps": mean_cc_cost,
                "median_close_to_close_cost_adjusted_bps": median_cc_cost,
                "worst_close_to_close_cost_adjusted_bps": worst_cc_cost,
                "close_to_close_cost_adjusted_win_rate": win_rate_cc_cost,
            }

    return summary
