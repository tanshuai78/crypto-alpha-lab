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


def run_stageA_v1_backtest(daily_bars: list[dict]) -> dict:
    from datetime import timedelta

    import numpy as np

    from research.cross_sectional_factor_lab.factors import compute_rebalance_factor_frame
    from research.cross_sectional_factor_lab.panel import (
        forward_fill_close_by_symbol,
        load_daily_panel,
    )
    from research.cross_sectional_factor_lab.portfolio import (
        build_equal_weight_targets,
        eligible_monday_rebalance_dates,
    )
    from research.cross_sectional_factor_lab.summary import (
        decide_stageA_v1,
        summarize_rebalance_quality,
    )

    base_summary = {
        "run_mode": "stageA_v1_momentum_backtest",
        "market": "binance_spot",
        "bias_label": "survivorship_bias_not_controlled",
        "primary_portfolio": "top10_equal_weight",
        "live_usage": "not_allowed",
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
    }

    if not daily_bars:
        base_summary.update({
            "decision": "stageA_v1_data_unavailable",
            "primary_blocker": "empty_daily_bars",
            "rebalance_quality": summarize_rebalance_quality(0, 0, [], []),
        })
        return base_summary

    try:
        panel = load_daily_panel(daily_bars)
    except Exception as e:
        base_summary.update({
            "decision": "stageA_v1_data_unavailable",
            "primary_blocker": f"load_panel_failed: {str(e)}",
            "rebalance_quality": summarize_rebalance_quality(0, 0, [], []),
        })
        return base_summary

    if panel.empty:
        base_summary.update({
            "decision": "stageA_v1_data_unavailable",
            "primary_blocker": "empty_daily_bars",
            "rebalance_quality": summarize_rebalance_quality(0, 0, [], []),
        })
        return base_summary

    # Forward fill Close prices
    panel, ffill_count = forward_fill_close_by_symbol(panel)

    all_dates = panel["date_utc"].unique()
    rebalance_dates = eligible_monday_rebalance_dates(all_dates)

    if not rebalance_dates:
        base_summary.update({
            "decision": "stageA_v1_data_unavailable",
            "primary_blocker": "insufficient_rebalance_dates",
            "rebalance_quality": summarize_rebalance_quality(0, 0, [], []),
        })
        return base_summary

    # Backtest Loop
    prev_weights_top10 = {}
    prev_weights_top5 = {}
    prev_weights_ew = {}

    top10_net_returns_30 = []
    top10_net_returns_50 = []
    top10_net_returns_80 = []

    top5_net_returns_30 = []
    ew_net_returns_30 = []

    # Rebalance quality tracking
    rebalance_count = 0
    insufficient_universe_count = 0
    selected_counts = []
    turnovers_top10 = []

    # Symbol PnL contribution tracking
    symbol_pnl_contributions = {}
    month_pnl_contributions = {}

    for i, t_i in enumerate(rebalance_dates):
        # We need an exit date to compute return. Default is t_i + 7 days
        exit_date = t_i + timedelta(days=7)

        # Check if exit date is present in the panel for at least one symbol
        if panel[panel["date_utc"] == exit_date].empty:
            # Drop final incomplete period
            continue

        rebalance_count += 1
        factors = compute_rebalance_factor_frame(panel, t_i)

        # Check insufficient universe
        if len(factors) < 10:
            insufficient_universe_count += 1

        selected_counts.append(min(len(factors), 10))

        # Build portfolios
        targets_top10 = build_equal_weight_targets(factors, top_n=10)
        weights_top10 = dict(zip(targets_top10["symbol"], targets_top10["target_weight"])) if not targets_top10.empty else {}

        targets_top5 = build_equal_weight_targets(factors, top_n=5)
        weights_top5 = dict(zip(targets_top5["symbol"], targets_top5["target_weight"])) if not targets_top5.empty else {}

        targets_ew = universe_equal_weight_targets(factors)
        weights_ew = dict(zip(targets_ew["symbol"], targets_ew["target_weight"])) if not targets_ew.empty else {}

        # Period returns
        gross_ret_top10 = compute_strategy_period_return(panel, weights_top10, t_i, exit_date)
        gross_ret_top5 = compute_strategy_period_return(panel, weights_top5, t_i, exit_date)
        gross_ret_ew = compute_strategy_period_return(panel, weights_ew, t_i, exit_date)

        # Turnover
        to_top10 = compute_turnover(prev_weights_top10, weights_top10)
        to_top5 = compute_turnover(prev_weights_top5, weights_top5)
        to_ew = compute_turnover(prev_weights_ew, weights_ew)

        turnovers_top10.append(to_top10)

        # Net returns
        net_ret_30 = apply_turnover_cost(gross_ret_top10, to_top10, 30.0)
        net_ret_50 = apply_turnover_cost(gross_ret_top10, to_top10, 50.0)
        net_ret_80 = apply_turnover_cost(gross_ret_top10, to_top10, 80.0)

        top10_net_returns_30.append(net_ret_30)
        top10_net_returns_50.append(net_ret_50)
        top10_net_returns_80.append(net_ret_80)

        net_ret_top5_30 = apply_turnover_cost(gross_ret_top5, to_top5, 30.0)
        top5_net_returns_30.append(net_ret_top5_30)

        net_ret_ew_30 = apply_turnover_cost(gross_ret_ew, to_ew, 30.0)
        ew_net_returns_30.append(net_ret_ew_30)

        # Track symbol contributions under 30 bps cost (base scenario)
        month_str = t_i.strftime("%Y-%m")
        month_pnl_contributions[month_str] = month_pnl_contributions.get(month_str, 0.0) + net_ret_30

        for symbol, weight in weights_top10.items():
            symbol_data = panel[panel["symbol"] == symbol]
            entry_row = symbol_data[symbol_data["date_utc"] == t_i]
            exit_row = symbol_data[symbol_data["date_utc"] == exit_date]
            if not entry_row.empty and not exit_row.empty:
                p_entry = float(entry_row["open"].iloc[0])
                p_exit = float(exit_row["open"].iloc[0])
                if p_entry > 0:
                    symbol_return = (p_exit / p_entry) - 1.0
                    gross_contrib = symbol_return * weight
                    sym_prev_w = prev_weights_top10.get(symbol, 0.0)
                    sym_to = abs(weight - sym_prev_w)
                    sym_cost = sym_to * (30.0 / 10000.0) / 2.0
                    net_contrib = gross_contrib - sym_cost
                    symbol_pnl_contributions[symbol] = symbol_pnl_contributions.get(symbol, 0.0) + net_contrib

        # Account for symbols sold completely (weight goes to 0)
        for symbol in (set(prev_weights_top10.keys()) - set(weights_top10.keys())):
            sym_prev_w = prev_weights_top10[symbol]
            sym_to = sym_prev_w
            sym_cost = sym_to * (30.0 / 10000.0) / 2.0
            symbol_pnl_contributions[symbol] = symbol_pnl_contributions.get(symbol, 0.0) - sym_cost

        # Update prev weights
        prev_weights_top10 = weights_top10
        prev_weights_top5 = weights_top5
        prev_weights_ew = weights_ew

    # Helper to calculate max drawdown as float percentage
    def get_max_drawdown(returns: list[float]) -> float:
        if not returns:
            return 0.0
        equity = [1.0]
        for r in returns:
            equity.append(equity[-1] * (1.0 + r))
        equity = np.array(equity)
        cum_max = np.maximum.accumulate(equity)
        drawdowns = np.where(cum_max > 0, (cum_max - equity) / cum_max, 0.0)
        return float(np.max(drawdowns)) * 100.0

    # Compound returns
    def get_total_return(returns: list[float]) -> float:
        if not returns:
            return 0.0
        return float(np.prod([1.0 + r for r in returns]) - 1.0) * 100.0

    # Calculate metrics
    tot_ret_30 = get_total_return(top10_net_returns_30)
    tot_ret_50 = get_total_return(top10_net_returns_50)
    tot_ret_80 = get_total_return(top10_net_returns_80)

    dd_30 = get_max_drawdown(top10_net_returns_30)

    tot_ret_top5_30 = get_total_return(top5_net_returns_30)
    dd_top5_30 = get_max_drawdown(top5_net_returns_30)

    tot_ret_ew_30 = get_total_return(ew_net_returns_30)
    dd_ew_30 = get_max_drawdown(ew_net_returns_30)

    # Benchmarks buy & hold
    btc_bh_return_pct = 0.0
    eth_bh_return_pct = 0.0

    if rebalance_count > 0:
        start_date = rebalance_dates[0]
        end_date = start_date + timedelta(days=rebalance_count * 7)
        lookup_close_date = end_date - timedelta(days=1)

        # BTC buy & hold
        btc_data = panel[panel["symbol"] == "BTCUSDT"]
        if not btc_data.empty:
            start_row = btc_data[btc_data["date_utc"] == start_date]
            end_row = btc_data[btc_data["date_utc"] == lookup_close_date]
            if not start_row.empty and not end_row.empty:
                btc_bh_return_pct = compute_benchmark_buy_and_hold_net(
                    float(start_row["open"].iloc[0]),
                    float(end_row["close"].iloc[0]),
                    30.0
                ) * 100.0

        # ETH buy & hold
        eth_data = panel[panel["symbol"] == "ETHUSDT"]
        if not eth_data.empty:
            start_row = eth_data[eth_data["date_utc"] == start_date]
            end_row = eth_data[eth_data["date_utc"] == lookup_close_date]
            if not start_row.empty and not end_row.empty:
                eth_bh_return_pct = compute_benchmark_buy_and_hold_net(
                    float(start_row["open"].iloc[0]),
                    float(end_row["close"].iloc[0]),
                    30.0
                ) * 100.0

    # Calculate Concentration Shares
    def get_concentration(contributions: dict[str, float]) -> tuple[float, float, float, float]:
        if not contributions:
            return 0.0, 0.0, 0.0, 0.0

        contrib_values = list(contributions.values())

        pos_contribs = [v for v in contrib_values if v > 0]
        sum_pos = sum(pos_contribs)
        max_pos_share = max(pos_contribs) / sum_pos if sum_pos > 0 and pos_contribs else 0.0

        abs_contribs = [abs(v) for v in contrib_values]
        sum_abs = sum(abs_contribs)
        max_abs_share = max(abs_contribs) / sum_abs if sum_abs > 0 and abs_contribs else 0.0

        return max_pos_share, max_abs_share, sum_pos, sum_abs

    # Symbol concentration
    max_sym_pos_share, max_sym_abs_share, _, _ = get_concentration(symbol_pnl_contributions)

    # Monthly concentration
    max_mon_pos_share, max_mon_abs_share, _, _ = get_concentration(month_pnl_contributions)

    # Rebalance quality
    quality = summarize_rebalance_quality(
        rebalance_count, insufficient_universe_count, selected_counts, turnovers_top10
    )

    # Construct final summary
    result_summary = {
        "run_mode": "stageA_v1_momentum_backtest",
        "market": "binance_spot",
        "bias_label": "survivorship_bias_not_controlled",
        "primary_portfolio": "top10_equal_weight",
        "live_usage": "not_allowed",
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "ffill_count": ffill_count,
        "performance": {
            "by_cost_scenario": {
                "base_30_bps_round_trip": {
                    "strategy_total_return_pct": tot_ret_30,
                    "strategy_max_drawdown_pct": dd_30,
                },
                "stress_50_bps_round_trip": {
                    "strategy_total_return_pct": tot_ret_50,
                },
                "crash_80_bps_round_trip": {
                    "strategy_total_return_pct": tot_ret_80,
                },
            }
        },
        "benchmarks": {
            "btc_buy_and_hold_net_with_entry_exit_cost_pct": btc_bh_return_pct,
            "eth_buy_and_hold_net_with_entry_exit_cost_pct": eth_bh_return_pct,
            "universe_equal_weight_total_return_pct": tot_ret_ew_30,
            "universe_equal_weight_max_drawdown_pct": dd_ew_30,
        },
        "concentration": {
            "max_single_symbol_positive_pnl_share": max_sym_pos_share,
            "max_single_symbol_abs_pnl_share": max_sym_abs_share,
            "max_single_month_positive_pnl_share": max_mon_pos_share,
            "max_single_month_abs_pnl_share": max_mon_abs_share,
        },
        "rebalance_quality": quality,
        "diagnostic_top5_performance": {
            "strategy_total_return_pct": tot_ret_top5_30,
            "strategy_max_drawdown_pct": dd_top5_30,
        },
    }

    # Excess performance
    excess_ret = tot_ret_30 - tot_ret_ew_30
    result_summary["excess_performance"] = {
        "vs_equal_weight_total_return_pct": excess_ret
    }

    # Decide
    decision = decide_stageA_v1(result_summary)
    result_summary["decision"] = decision

    return result_summary
