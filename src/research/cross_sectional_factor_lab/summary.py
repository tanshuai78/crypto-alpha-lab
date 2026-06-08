from __future__ import annotations

from typing import Any

import numpy as np

import configs.base as cfg


def summarize_rebalance_quality(
    rebalance_count: int,
    insufficient_universe_count: int,
    selected_counts: list[int],
    turnovers: list[float],
) -> dict[str, Any]:
    ratio = (
        float(insufficient_universe_count) / rebalance_count
        if rebalance_count > 0
        else 0.0
    )
    median_count = float(np.median(selected_counts)) if selected_counts else 0.0
    median_to = float(np.median(turnovers)) if turnovers else 0.0

    return {
        "rebalance_count": rebalance_count,
        "insufficient_universe_count": insufficient_universe_count,
        "insufficient_universe_ratio": ratio,
        "median_selected_symbol_count": median_count,
        "median_turnover": median_to,
    }


def decide_stageA_v1(summary: dict[str, Any]) -> str:
    try:
        rebalance_quality = summary["rebalance_quality"]
        rebalance_count = rebalance_quality["rebalance_count"]

        # Calculate ratio dynamically if not present
        insufficient_universe_ratio = rebalance_quality.get(
            "insufficient_universe_ratio",
            float(rebalance_quality.get("insufficient_universe_count", 0)) / rebalance_count
            if rebalance_count > 0
            else 0.0
        )

        # Check 1: min rebalance count
        if rebalance_count < cfg.FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT:
            return "stageA_v1_failed"

        # Check 2: insufficient universe ratio
        if insufficient_universe_ratio > cfg.FACTOR_LAB_STAGEA_MAX_INSUFFICIENT_UNIVERSE_RATIO:
            return "stageA_v1_failed"

        # Cost scenarios performance
        perf = summary["performance"]["by_cost_scenario"]
        base_perf = perf["base_30_bps_round_trip"]
        strategy_return = base_perf["strategy_total_return_pct"]
        strategy_dd = base_perf["strategy_max_drawdown_pct"]

        stress_perf = perf["stress_50_bps_round_trip"]
        stress_return = stress_perf["strategy_total_return_pct"]

        # Benchmarks
        bench = summary["benchmarks"]
        ew_return = bench["universe_equal_weight_total_return_pct"]
        ew_dd = bench["universe_equal_weight_max_drawdown_pct"]

        # Check 3: strategy beats equal weight benchmark under base cost
        if strategy_return <= ew_return:
            return "stageA_v1_failed"

        # Check 4: strategy max drawdown limit
        max_dd_allowed = ew_dd * cfg.FACTOR_LAB_STAGEA_MAX_DRAWDOWN_VS_EW_MULTIPLIER
        if strategy_dd > max_dd_allowed:
            return "stageA_v1_failed"

        # Check 5: stress return must not be negative
        if stress_return < 0.0:
            return "stageA_v1_failed"

        # Check 6: Concentration limits (positive PnL contribution)
        conc = summary["concentration"]
        max_sym_pnl = conc["max_single_symbol_positive_pnl_share"]
        max_mon_pnl = conc["max_single_month_positive_pnl_share"]

        if max_sym_pnl > cfg.FACTOR_LAB_STAGEA_MAX_SINGLE_SYMBOL_PNL_CONTRIBUTION_SHARE:
            return "stageA_v1_failed"

        if max_mon_pnl > cfg.FACTOR_LAB_STAGEA_MAX_SINGLE_MONTH_PNL_CONTRIBUTION_SHARE:
            return "stageA_v1_failed"

        return "stageA_v1_passed"

    except KeyError:
        return "stageA_v1_failed"
