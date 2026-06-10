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
        btc_return = bench["btc_buy_and_hold_net_with_entry_exit_cost_pct"]
        eth_return = bench["eth_buy_and_hold_net_with_entry_exit_cost_pct"]
        ew_return = bench["universe_equal_weight_total_return_pct"]
        ew_dd = bench["universe_equal_weight_max_drawdown_pct"]

        # Check 3: strategy beats BTC/ETH and equal-weight benchmarks under base cost
        if strategy_return <= btc_return:
            return "stageA_v1_failed"

        if strategy_return <= eth_return:
            return "stageA_v1_failed"

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


def decide_stageA2_variant(variant_summary: dict[str, Any]) -> str:
    rebalance_quality = variant_summary.get("rebalance_quality", {})
    rebalance_count = int(rebalance_quality.get("rebalance_count", 0))
    if rebalance_count < cfg.FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT:
        return "regime_filter_data_insufficient"

    performance = variant_summary["performance"]
    benchmarks = variant_summary["benchmarks"]
    regime_filter = variant_summary["regime_filter"]
    concentration = variant_summary["concentration"]

    drawdown_reduction = performance["max_drawdown_vs_v1_reduction_pct"]
    strategy_return = performance["base_30bps_total_return_pct"]
    ew_return = benchmarks["universe_equal_weight_pct"]
    btc_return = benchmarks["btc_buy_and_hold_net_pct"]
    eth_return = benchmarks["eth_buy_and_hold_net_pct"]
    cash_days_share = regime_filter["cash_days_share"]
    month_share = concentration["max_single_month_positive_pnl_share"]

    if drawdown_reduction < cfg.FACTOR_LAB_STAGEA2_MIN_DRAWDOWN_REDUCTION_PCT:
        return "regime_filter_failed"

    benchmark_floor = cfg.FACTOR_LAB_STAGEA2_MAX_BENCHMARK_UNDERPERFORMANCE_PCT
    passes_alpha = strategy_return > ew_return
    passes_btc = strategy_return >= btc_return - benchmark_floor
    passes_eth = strategy_return >= eth_return - benchmark_floor
    passes_cash = cash_days_share <= cfg.FACTOR_LAB_STAGEA2_MAX_CASH_DAYS_SHARE
    passes_month_concentration = (
        month_share <= cfg.FACTOR_LAB_STAGEA_MAX_SINGLE_MONTH_PNL_CONTRIBUTION_SHARE
    )

    if passes_alpha and passes_btc and passes_eth and passes_cash and passes_month_concentration:
        return "regime_filter_promising"

    return "regime_filter_reduces_damage_but_no_alpha"


def decide_stageA2_round1(variant_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    promising = [
        item
        for item in variant_summaries
        if item.get("variant") != "regime_none"
        and item.get("decision") == "regime_filter_promising"
    ]

    if not promising:
        return {"winner_variant": None, "can_enter_stageA2_round2": False}

    winner = max(
        promising,
        key=lambda item: (
            item["performance"]["max_drawdown_vs_v1_reduction_pct"],
            item["performance"]["base_30bps_total_return_pct"],
        ),
    )
    return {"winner_variant": winner["variant"], "can_enter_stageA2_round2": True}


def decide_stageA2_cmom(summary: dict[str, Any]) -> dict[str, Any]:
    mom = summary["factor_variants"]["momentum_30d_skip_1d"]
    cmom = summary["factor_variants"]["cmom_14d_skip_1d"]

    mom_quality = mom["rebalance_quality"]
    cmom_quality = cmom["rebalance_quality"]

    mom_rebalance_count = mom_quality["rebalance_count"]
    cmom_rebalance_count = cmom_quality["rebalance_count"]

    if (
        mom_rebalance_count < cfg.FACTOR_LAB_STAGEA2_CMOM_MIN_REBALANCE_COUNT
        or cmom_rebalance_count < cfg.FACTOR_LAB_STAGEA2_CMOM_MIN_REBALANCE_COUNT
    ):
        return {
            "decision": "stageA2_cmom_data_unavailable",
            "primary_blocker": "insufficient_rebalance_count",
        }

    mom_perf = mom["performance"]
    cmom_perf = cmom["performance"]

    mom_bench = mom["benchmarks"]
    cmom_bench = cmom["benchmarks"]

    mom_return = mom_perf["base_30bps_total_return_pct"]
    cmom_return = cmom_perf["base_30bps_total_return_pct"]

    mom_dd = mom_perf["max_drawdown_pct"]
    cmom_dd = cmom_perf["max_drawdown_pct"]

    mom_vs_ew = mom_bench["vs_universe_equal_weight_total_return_pct"]
    cmom_vs_ew = cmom_bench["vs_universe_equal_weight_total_return_pct"]

    cmom_vs_btc = cmom_bench["vs_btc_total_return_pct"]
    cmom_vs_eth = cmom_bench["vs_eth_total_return_pct"]

    cmom_top5_return = cmom["diagnostic_top5_performance"]["strategy_total_return_pct"]

    cmom_month_share = cmom["concentration"]["max_single_month_positive_pnl_share"]

    # Compute comparison metrics
    cmom_vs_30d_return_diff_pct = cmom_return - mom_return
    cmom_vs_30d_drawdown_diff_pct = cmom_dd - mom_dd
    cmom_vs_30d_vs_universe_ew_diff_pct = cmom_vs_ew - mom_vs_ew

    cmom_beats_30d_after_30bps = cmom_vs_30d_return_diff_pct >= cfg.FACTOR_LAB_STAGEA2_CMOM_MIN_RETURN_DIFF_PCT
    cmom_top5_not_worse_than_top10 = cmom_top5_return >= cmom_return - 10.0

    primary_comparison = {
        "cmom_vs_30d_return_diff_pct": cmom_vs_30d_return_diff_pct,
        "cmom_vs_30d_drawdown_diff_pct": cmom_vs_30d_drawdown_diff_pct,
        "cmom_vs_30d_vs_universe_ew_diff_pct": cmom_vs_30d_vs_universe_ew_diff_pct,
        "cmom_beats_30d_after_30bps": cmom_beats_30d_after_30bps,
        "cmom_top5_not_worse_than_top10": cmom_top5_not_worse_than_top10,
    }

    # Evaluate gates
    # Hard gates for regime-gated CMOM:
    passes_hard_gates = (
        cmom_beats_30d_after_30bps
        and cmom_dd <= mom_dd
        and cmom_vs_ew > 0.0
        and cmom_vs_btc >= -cfg.FACTOR_LAB_STAGEA2_CMOM_MAX_BTC_UNDERPERFORMANCE_PCT
        and cmom_vs_eth >= -cfg.FACTOR_LAB_STAGEA2_CMOM_MAX_ETH_UNDERPERFORMANCE_PCT
        and cmom_return > cfg.FACTOR_LAB_STAGEA2_CMOM_MIN_PROCEED_TOTAL_RETURN_PCT
        and cmom_perf["stress_50bps_total_return_pct"] > cfg.FACTOR_LAB_STAGEA2_CMOM_MIN_PROCEED_STRESS_50BPS_RETURN_PCT
        and cmom_top5_not_worse_than_top10
        and cmom_month_share <= 0.30
    )

    # Stricter 3d failure diagnostic gates:
    passes_3d_gates = (
        cmom_beats_30d_after_30bps
        and cmom_vs_30d_vs_universe_ew_diff_pct >= cfg.FACTOR_LAB_STAGEA2_CMOM_MIN_EW_IMPROVEMENT_DIFF_PCT
        and cmom_dd <= mom_dd + cfg.FACTOR_LAB_STAGEA2_CMOM_MAX_3D_DIAGNOSTIC_DRAWDOWN_WORSENING_PCT
        and cmom_top5_return >= cmom_return - cfg.FACTOR_LAB_STAGEA2_CMOM_MAX_3D_DIAGNOSTIC_TOP5_UNDERPERFORMANCE_PCT
        and cmom_month_share <= cfg.FACTOR_LAB_STAGEA2_CMOM_MAX_3D_DIAGNOSTIC_MONTH_SHARE
    )

    if passes_hard_gates:
        next_action = "proceed_to_regime_gated_cmom_diagnostic_design"
    elif passes_3d_gates:
        next_action = "run_3d_failure_diagnostic"
    else:
        next_action = "stop_price_only_momentum"

    return {
        "decision": "cmom_diagnostic_completed",
        "primary_comparison": primary_comparison,
        "next_action": next_action,
    }

