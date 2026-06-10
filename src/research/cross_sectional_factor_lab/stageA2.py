from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

import configs.base as cfg
from research.cross_sectional_factor_lab.backtest import (
    apply_turnover_cost,
    compute_strategy_period_return,
    compute_turnover,
    universe_equal_weight_targets,
)
from research.cross_sectional_factor_lab.factors import compute_rebalance_factor_frame
from research.cross_sectional_factor_lab.panel import forward_fill_close_by_symbol, load_daily_panel
from research.cross_sectional_factor_lab.portfolio import (
    build_equal_weight_targets,
    eligible_monday_rebalance_dates,
)
from research.cross_sectional_factor_lab.regime import (
    AltUniverseRegimeResult,
    decide_stageA2_regime_exposure,
)
from research.cross_sectional_factor_lab.summary import (
    decide_stageA2_round1,
    decide_stageA2_variant,
    summarize_rebalance_quality,
)


def next_weekly_exit_date(rebalance_date: pd.Timestamp) -> pd.Timestamp:
    return rebalance_date + timedelta(days=7)


def compound_returns_pct(returns: list[float]) -> float:
    if not returns:
        return 0.0
    return float(np.prod([1.0 + r for r in returns]) - 1.0) * 100.0


def max_drawdown_pct(returns: list[float]) -> float:
    if not returns:
        return 0.0
    equity = np.array([1.0] + list(np.cumprod([1.0 + r for r in returns])))
    peaks = np.maximum.accumulate(equity)
    drawdowns = np.where(peaks > 0, (peaks - equity) / peaks, 0.0)
    return float(np.max(drawdowns)) * 100.0


def _positive_and_abs_concentration(contributions: dict[str, float]) -> tuple[float, float]:
    positives = [v for v in contributions.values() if v > 0]
    positive_total = sum(positives)
    positive_share = max(positives) / positive_total if positive_total > 0 and positives else 0.0
    absolutes = [abs(v) for v in contributions.values()]
    abs_total = sum(absolutes)
    abs_share = max(absolutes) / abs_total if abs_total > 0 and absolutes else 0.0
    return float(positive_share), float(abs_share)


def _benchmark_open_to_open_net_pct(
    panel: pd.DataFrame,
    symbol: str,
    start_date: pd.Timestamp,
    exit_date: pd.Timestamp,
    round_trip_cost_bps: float = 30.0,
) -> float:
    data = panel[panel["symbol"] == symbol]
    start = data[data["date_utc"] == start_date]
    end = data[data["date_utc"] == exit_date]
    if start.empty or end.empty:
        return 0.0
    gross = (float(end["open"].iloc[0]) / float(start["open"].iloc[0])) - 1.0
    return (gross - round_trip_cost_bps / 10000.0) * 100.0


def _symbol_open_to_open_return(
    panel: pd.DataFrame,
    symbol: str,
    entry_date: pd.Timestamp,
    exit_date: pd.Timestamp,
) -> float | None:
    symbol_data = panel[panel["symbol"] == symbol]
    entry_row = symbol_data[symbol_data["date_utc"] == entry_date]
    exit_row = symbol_data[symbol_data["date_utc"] == exit_date]
    if entry_row.empty or exit_row.empty:
        return None
    entry_open = float(entry_row["open"].iloc[0])
    exit_open = float(exit_row["open"].iloc[0])
    if entry_open <= 0:
        return None
    return (exit_open / entry_open) - 1.0


def _universe_equal_weight_benchmark_pct(panel: pd.DataFrame, rebalance_dates: list[pd.Timestamp]) -> float:
    previous_weights: dict[str, float] = {}
    returns: list[float] = []
    for rebalance_date in rebalance_dates:
        exit_date = next_weekly_exit_date(rebalance_date)
        if panel[panel["date_utc"] == exit_date].empty:
            continue
        factors = compute_rebalance_factor_frame(panel, rebalance_date)
        targets = universe_equal_weight_targets(factors)
        weights = dict(zip(targets["symbol"], targets["target_weight"])) if not targets.empty else {}
        gross_return = compute_strategy_period_return(panel, weights, rebalance_date, exit_date)
        if gross_return is None:
            continue
        turnover = compute_turnover(previous_weights, weights)
        returns.append(apply_turnover_cost(gross_return, turnover, 30.0))
        previous_weights = weights
    return compound_returns_pct(returns)


def _empty_alt_diagnostics() -> dict[str, Any]:
    return {
        "eligible_symbols_count": 0,
        "symbols_with_valid_20d_return": 0,
        "coverage_ratio": 0.0,
        "included_btc_eth": False,
    }


def _alt_diagnostics(result: AltUniverseRegimeResult | None) -> dict[str, Any]:
    if result is None:
        return _empty_alt_diagnostics()
    return {
        "eligible_symbols_count": result.eligible_symbols_count,
        "symbols_with_valid_20d_return": result.symbols_with_valid_20d_return,
        "coverage_ratio": result.coverage_ratio,
        "included_btc_eth": result.included_btc_eth,
    }


def _run_variant(
    panel: pd.DataFrame,
    rebalance_dates: list[pd.Timestamp],
    variant: str,
    baseline_drawdown_pct: float,
    btc_return_pct: float,
    eth_return_pct: float,
    universe_equal_weight_pct: float,
) -> dict[str, Any]:
    previous_weights: dict[str, float] = {}
    returns_30: list[float] = []
    returns_50: list[float] = []
    returns_80: list[float] = []
    exposed_returns: list[float] = []
    cash_returns: list[float] = []
    turnovers: list[float] = []
    selected_counts: list[int] = []
    insufficient_universe_count = 0
    cash_period_count = 0
    symbol_contrib: dict[str, float] = {}
    month_contrib: dict[str, float] = {}
    latest_alt_result: AltUniverseRegimeResult | None = None

    for rebalance_date in rebalance_dates:
        exit_date = next_weekly_exit_date(rebalance_date)
        if panel[panel["date_utc"] == exit_date].empty:
            continue
        factors = compute_rebalance_factor_frame(panel, rebalance_date)
        if len(factors) < cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N:
            insufficient_universe_count += 1
        selected_counts.append(min(len(factors), cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N))

        targets = build_equal_weight_targets(factors, top_n=cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N)
        alt_weights = dict(zip(targets["symbol"], targets["target_weight"])) if not targets.empty else {}
        eligible_symbols = tuple(factors["symbol"].tolist()) if not factors.empty else ()
        is_exposed, alt_result = decide_stageA2_regime_exposure(variant, panel, rebalance_date, eligible_symbols)
        if alt_result is not None:
            latest_alt_result = alt_result
        weights = alt_weights if is_exposed else {}
        if not is_exposed:
            cash_period_count += 1

        gross_return = compute_strategy_period_return(panel, weights, rebalance_date, exit_date)
        if gross_return is None:
            continue
        turnover = compute_turnover(previous_weights, weights)
        turnovers.append(turnover)

        net_30 = apply_turnover_cost(gross_return, turnover, 30.0)
        returns_30.append(net_30)
        returns_50.append(apply_turnover_cost(gross_return, turnover, 50.0))
        returns_80.append(apply_turnover_cost(gross_return, turnover, 80.0))
        if is_exposed:
            exposed_returns.append(net_30)
        else:
            cash_returns.append(net_30)

        month = rebalance_date.strftime("%Y-%m")
        month_contrib[month] = month_contrib.get(month, 0.0) + net_30

        one_way_30bps_cost = (30.0 / 10000.0) / 2.0
        for symbol, weight in weights.items():
            symbol_return = _symbol_open_to_open_return(panel, symbol, rebalance_date, exit_date)
            if symbol_return is None:
                continue
            symbol_turnover = abs(weight - previous_weights.get(symbol, 0.0))
            symbol_cost = symbol_turnover * one_way_30bps_cost
            symbol_contrib[symbol] = (
                symbol_contrib.get(symbol, 0.0)
                + (symbol_return * weight)
                - symbol_cost
            )

        for symbol in set(previous_weights) - set(weights):
            symbol_cost = previous_weights[symbol] * one_way_30bps_cost
            symbol_contrib[symbol] = symbol_contrib.get(symbol, 0.0) - symbol_cost

        previous_weights = weights

    total_30 = compound_returns_pct(returns_30)
    dd = max_drawdown_pct(returns_30)
    if variant == "regime_none":
        dd_reduction = 0.0
    else:
        dd_reduction = ((baseline_drawdown_pct - dd) / baseline_drawdown_pct * 100.0) if baseline_drawdown_pct > 0 else 0.0
    cash_share = float(cash_period_count / len(returns_30)) if returns_30 else 0.0
    symbol_pos, symbol_abs = _positive_and_abs_concentration(symbol_contrib)
    month_pos, month_abs = _positive_and_abs_concentration(month_contrib)

    summary = {
        "variant": variant,
        "regime_filter": {
            "filtered_rebalance_share": cash_share,
            "cash_rebalance_period_share": cash_share,
            "alt_exposure_rebalance_period_share": 1.0 - cash_share if returns_30 else 0.0,
            "cash_days_share": cash_share,
            "alt_exposure_days_share": 1.0 - cash_share if returns_30 else 0.0,
            "strategy_return_when_exposed": compound_returns_pct(exposed_returns),
            "strategy_return_when_cash": compound_returns_pct(cash_returns),
            "mostly_cash_strategy": cash_share > cfg.FACTOR_LAB_STAGEA2_MAX_CASH_DAYS_SHARE,
        },
        "alt_universe_regime_diagnostics": _alt_diagnostics(latest_alt_result),
        "performance": {
            "base_30bps_total_return_pct": total_30,
            "stress_50bps_total_return_pct": compound_returns_pct(returns_50),
            "crash_80bps_total_return_pct": compound_returns_pct(returns_80),
            "max_drawdown_pct": dd,
            "max_drawdown_vs_v1_reduction_pct": dd_reduction,
            "turnover_median": float(np.median(turnovers)) if turnovers else 0.0,
        },
        "benchmarks": {
            "btc_buy_and_hold_net_pct": btc_return_pct,
            "eth_buy_and_hold_net_pct": eth_return_pct,
            "universe_equal_weight_pct": universe_equal_weight_pct,
            "vs_btc_total_return_pct": total_30 - btc_return_pct,
            "vs_eth_total_return_pct": total_30 - eth_return_pct,
            "vs_universe_equal_weight_total_return_pct": total_30 - universe_equal_weight_pct,
        },
        "concentration": {
            "max_single_symbol_positive_pnl_share": symbol_pos,
            "max_single_symbol_abs_pnl_share": symbol_abs,
            "max_single_month_positive_pnl_share": month_pos,
            "max_single_month_abs_pnl_share": month_abs,
        },
        "rebalance_quality": summarize_rebalance_quality(len(returns_30), insufficient_universe_count, selected_counts, turnovers),
    }
    summary["decision"] = decide_stageA2_variant(summary)
    return summary


def run_stageA2_regime_cash_fallback_diagnostic(daily_bars: list[dict]) -> dict[str, Any]:
    base = {
        "run_mode": "stageA2_regime_cash_fallback_diagnostic",
        "scope": "regime_cash_fallback_only",
        "live_usage": "not_allowed",
        "paper_shadow_allowed": False,
        "bias_label": "survivorship_bias_not_controlled",
        "benchmark_price_policy": "first_rebalance_open_to_last_valid_exit_open",
        "period_share_note": "weekly_equal_length_periods_make_period_share_equal_day_share_in_round1",
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
    }
    if not daily_bars:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": "empty_daily_bars", "variants": []}
    try:
        panel = load_daily_panel(daily_bars)
    except Exception as exc:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": f"load_panel_failed: {exc}", "variants": []}
    if panel.empty:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": "empty_daily_bars", "variants": []}

    panel, ffill_count = forward_fill_close_by_symbol(panel)
    rebalance_dates = eligible_monday_rebalance_dates(panel["date_utc"].unique())
    if not rebalance_dates:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": "insufficient_rebalance_dates", "variants": []}
    valid_exit_dates = [next_weekly_exit_date(dt) for dt in rebalance_dates if not panel[panel["date_utc"] == next_weekly_exit_date(dt)].empty]
    if not valid_exit_dates:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": "no_complete_rebalance_periods", "variants": []}

    start_date = rebalance_dates[0]
    last_exit_date = valid_exit_dates[-1]
    btc_return = _benchmark_open_to_open_net_pct(panel, "BTCUSDT", start_date, last_exit_date)
    eth_return = _benchmark_open_to_open_net_pct(panel, "ETHUSDT", start_date, last_exit_date)
    ew_return = _universe_equal_weight_benchmark_pct(panel, rebalance_dates)

    regime_none = _run_variant(panel, rebalance_dates, "regime_none", 0.0, btc_return, eth_return, ew_return)
    baseline_drawdown = regime_none["performance"]["max_drawdown_pct"]
    variants = [regime_none]
    for variant in ("btc_ma20_cash", "alt_universe_20d_return_cash"):
        variants.append(_run_variant(panel, rebalance_dates, variant, baseline_drawdown, btc_return, eth_return, ew_return))

    round1 = decide_stageA2_round1(variants)
    return {
        **base,
        "decision": "stageA2_round1_completed",
        "primary_blocker": None,
        "ffill_count": ffill_count,
        "variants": variants,
        "winner_variant": round1["winner_variant"],
        "can_enter_stageA2_round2": round1["can_enter_stageA2_round2"],
    }
