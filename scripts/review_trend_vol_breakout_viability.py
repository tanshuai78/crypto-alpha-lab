from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

from configs.base import (
    TREND_REGIME_MAX_HOLDING_HOURS,
    TREND_REGIME_OBSERVATION_COST_BPS,
    TREND_REGIME_STOP_LOSS_PCT,
    TREND_REGIME_STRESS_COST_BPS,
)
from scripts.replay_trend_regime_shadow import normalize_rows_for_historical_replay
from src.research.trend_vol_breakout_viability import (
    VolBreakoutReviewThresholds,
    classify_vol_breakout_only_for_review,
)
from src.strategies.trend_regime.scanner import _number_or_none
from src.strategies.trend_regime.shadow_simulator import (
    TrendRegimeShadowPosition,
    simulate_trend_regime_shadow,
)


def load_rows_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def build_vol_breakout_audit_summary(
    rows: list[dict[str, Any]],
    *,
    thresholds: VolBreakoutReviewThresholds | None = None,
) -> dict[str, Any]:
    reject_counts: dict[str, int] = defaultdict(int)
    reject_counts_by_symbol: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    entry_event_count = 0
    entry_event_count_by_symbol: dict[str, int] = defaultdict(int)
    entry_event_count_by_regime: dict[str, int] = defaultdict(int)
    symbols: set[str] = set()
    timestamp_values: list[int] = []

    for row in rows:
        symbol = str(row.get("symbol") or "")
        if symbol:
            symbols.add(symbol)

        ts_ms = int(_number_or_none(row.get("timestamp_ms")) or 0)
        if ts_ms > 0:
            timestamp_values.append(ts_ms)

        classification = classify_vol_breakout_only_for_review(row, thresholds=thresholds)
        if classification.event is None:
            reject_reason = str(classification.reject_reason or "unknown")
            reject_counts[reject_reason] += 1
            reject_counts_by_symbol[symbol or "unknown"][reject_reason] += 1
            continue

        entry_event_count += 1
        entry_event_count_by_symbol[symbol or "unknown"] += 1
        entry_event_count_by_regime[str(classification.event.regime)] += 1

    start_timestamp_ms = min(timestamp_values) if timestamp_values else 0
    end_timestamp_ms = max(timestamp_values) if timestamp_values else 0
    time_span_hours = (
        (end_timestamp_ms - start_timestamp_ms) / 3_600_000.0
        if end_timestamp_ms > start_timestamp_ms
        else 0.0
    )

    events_per_30d = 0.0
    if time_span_hours > 0.0:
        events_per_30d = round((entry_event_count / time_span_hours) * 24.0 * 30.0, 10)

    events_per_symbol_30d: dict[str, float] = {}
    for sym in symbols:
        cnt = entry_event_count_by_symbol.get(sym, 0)
        if time_span_hours > 0.0:
            events_per_symbol_30d[sym] = round((cnt / time_span_hours) * 24.0 * 30.0, 10)
        else:
            events_per_symbol_30d[sym] = 0.0

    capital_utilization_label = "acceptable" if events_per_30d >= 10.0 else "too_sparse"

    return {
        "input_row_count": len(rows),
        "symbol_count": len(symbols),
        "symbols": sorted(symbols),
        "start_timestamp_ms": start_timestamp_ms,
        "end_timestamp_ms": end_timestamp_ms,
        "time_span_hours": round(time_span_hours, 10),
        "entry_event_count": entry_event_count,
        "entry_event_count_by_symbol": dict(entry_event_count_by_symbol),
        "entry_event_count_by_regime": dict(entry_event_count_by_regime),
        "classification_reject_counts": dict(reject_counts),
        "reject_counts_by_symbol": {
            key: dict(value) for key, value in reject_counts_by_symbol.items()
        },
        "events_per_30d": events_per_30d,
        "events_per_symbol_30d": events_per_symbol_30d,
        "capital_utilization_label": capital_utilization_label,
    }


def build_vol_breakout_shadow_summary(
    rows: list[dict[str, Any]],
    *,
    estimated_cost_bps: float,
    holding_hours: int,
    thresholds: VolBreakoutReviewThresholds | None = None,
) -> dict[str, Any]:
    normalized_rows, _ = normalize_rows_for_historical_replay(rows)
    audit = build_vol_breakout_audit_summary(normalized_rows, thresholds=thresholds)

    results: list[Any] = []
    accepted_entries_with_path_count = 0

    for index, row in enumerate(normalized_rows):
        classification = classify_vol_breakout_only_for_review(row, thresholds=thresholds)
        if classification.event is None:
            continue

        event = classification.event
        entry_price = _number_or_none(row.get("close_price"))
        entry_time_ms = int(_number_or_none(row.get("timestamp_ms")) or 0)
        if entry_price is None or entry_time_ms <= 0:
            continue

        path_rows = [
            item
            for item in normalized_rows[index + 1 :]
            if item.get("symbol") == event.symbol
            and int(_number_or_none(item.get("timestamp_ms")) or 0) > entry_time_ms
        ]

        if not path_rows:
            continue

        accepted_entries_with_path_count += 1

        position = TrendRegimeShadowPosition(
            symbol=event.symbol,
            direction=event.direction,
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            estimated_cost_bps=estimated_cost_bps,
            max_holding_hours=float(holding_hours),
            stop_loss_pct=float(TREND_REGIME_STOP_LOSS_PCT),
            regime=event.regime,
            symbol_tier=str(event.metadata.get("symbol_tier") or "unknown"),
        )
        simulated = simulate_trend_regime_shadow(position, path_rows)
        results.append(simulated)

    summary = {
        "input_row_count": audit["input_row_count"],
        "symbol_count": audit["symbol_count"],
        "symbols": audit["symbols"],
        "start_timestamp_ms": audit["start_timestamp_ms"],
        "end_timestamp_ms": audit["end_timestamp_ms"],
        "time_span_hours": audit["time_span_hours"],
        "entry_event_count": audit["entry_event_count"],
        "entry_event_count_by_symbol": audit["entry_event_count_by_symbol"],
        "entry_event_count_by_regime": audit["entry_event_count_by_regime"],
        "classification_reject_counts": audit["classification_reject_counts"],
        "reject_counts_by_symbol": audit["reject_counts_by_symbol"],
        "events_per_30d": audit["events_per_30d"],
        "events_per_symbol_30d": audit["events_per_symbol_30d"],
        "capital_utilization_label": audit["capital_utilization_label"],
        "holding_hours": holding_hours,
        "shadow_trade_count": len(results),
        "accepted_entries_with_path_count": accepted_entries_with_path_count,
        "mean_net_pnl_bps": 0.0,
        "median_net_pnl_bps": 0.0,
        "win_rate": 0.0,
        "worst_trade_net_pnl_bps": 0.0,
        "stop_loss_exit_rate": 0.0,
        "coverage_quality": "historical_rows_replay_not_live_freshness_aware",
        "strategy_slice": "vol_breakout_only",
        "edge_status": "unknown_until_shadow",
    }

    if results:
        net_values = [float(r.net_pnl_bps) for r in results]
        stop_losses = [1 for r in results if r.exit_reason == "stop_loss_hit"]
        wins = [v for v in net_values if v > 0.0]

        summary.update({
            "mean_net_pnl_bps": round(mean(net_values), 10),
            "median_net_pnl_bps": round(median(net_values), 10),
            "win_rate": round(len(wins) / len(results), 10),
            "worst_trade_net_pnl_bps": round(min(net_values), 10),
            "stop_loss_exit_rate": round(len(stop_losses) / len(results), 10),
        })

    return summary


def run_vol_breakout_sensitivity(
    rows: list[dict[str, Any]],
    *,
    threshold_sets: list[VolBreakoutReviewThresholds],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    # Use baseline cost (30 bps) for sensitivity analysis as standard cost boundary
    cost = float(TREND_REGIME_OBSERVATION_COST_BPS)
    holding = int(TREND_REGIME_MAX_HOLDING_HOURS)

    for t in threshold_sets:
        sh = build_vol_breakout_shadow_summary(
            rows,
            estimated_cost_bps=cost,
            holding_hours=holding,
            thresholds=t,
        )
        summaries.append({
            "threshold_set_name": t.name,
            "assumption_level": t.assumption_level,
            "eligible_for_redefinition": t.eligible_for_redefinition,
            "entry_event_count": sh["entry_event_count"],
            "shadow_trade_count": sh["shadow_trade_count"],
            "mean_net_pnl_bps": sh["mean_net_pnl_bps"],
            "median_net_pnl_bps": sh["median_net_pnl_bps"],
            "win_rate": sh["win_rate"],
            "worst_trade_net_pnl_bps": sh["worst_trade_net_pnl_bps"],
            "stop_loss_exit_rate": sh["stop_loss_exit_rate"],
        })
    return summaries


def build_dual_cost_viability_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    shadow_by_holding_hours: dict[str, dict[str, Any]] = {}
    base_cost = float(TREND_REGIME_OBSERVATION_COST_BPS)
    stress_cost = float(TREND_REGIME_STRESS_COST_BPS)

    fields_to_extract = [
        "entry_event_count",
        "shadow_trade_count",
        "median_net_pnl_bps",
        "mean_net_pnl_bps",
        "win_rate",
        "worst_trade_net_pnl_bps",
        "stop_loss_exit_rate",
    ]

    for hours in [4, 8, 12, 24]:
        base_sh = build_vol_breakout_shadow_summary(
            rows, estimated_cost_bps=base_cost, holding_hours=hours
        )
        stress_sh = build_vol_breakout_shadow_summary(
            rows, estimated_cost_bps=stress_cost, holding_hours=hours
        )

        shadow_by_holding_hours[str(hours)] = {
            "base": {k: base_sh[k] for k in fields_to_extract},
            "stress": {k: stress_sh[k] for k in fields_to_extract},
        }

    return {
        "base_cost_bps": base_cost,
        "stress_cost_bps": stress_cost,
        "shadow_by_holding_hours": shadow_by_holding_hours,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit vol breakout viability & sensitivity")
    parser.add_argument("--input", required=True, help="Path to input historical rows JSONL")
    parser.add_argument("--summary-output", required=True, help="Path to write viability summary JSON")
    parser.add_argument("--sensitivity-output", required=True, help="Path to write sensitivity summary JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = load_rows_jsonl(args.input)

    # 1. Generate viability summary
    # Base summary uses standard configs (estimated cost = 30 bps, default holding hours = 12)
    # Plus the shadow_by_holding_hours matrix
    summary = build_vol_breakout_shadow_summary(
        rows,
        estimated_cost_bps=float(TREND_REGIME_OBSERVATION_COST_BPS),
        holding_hours=int(TREND_REGIME_MAX_HOLDING_HOURS),
    )
    dual_cost_details = build_dual_cost_viability_summary(rows)
    summary.update(dual_cost_details)

    # Ensure no detailed results array is committed
    summary.pop("results", None)

    summary_path = Path(args.summary-summary_output if hasattr(args, "summary_output") else args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(args.summary_output, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, sort_keys=True)

    # 2. Generate sensitivity summary
    thresholds = [
        VolBreakoutReviewThresholds.baseline_current(),
        VolBreakoutReviewThresholds.moderately_relaxed(),
        VolBreakoutReviewThresholds.aggressive_relaxed(),
    ]
    sensitivity_list = run_vol_breakout_sensitivity(rows, threshold_sets=thresholds)

    sensitivity_path = Path(args.sensitivity_output)
    sensitivity_path.parent.mkdir(parents=True, exist_ok=True)
    with open(args.sensitivity_output, "w", encoding="utf-8") as f:
        json.dump(sensitivity_list, f, ensure_ascii=False, indent=2, sort_keys=True)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
