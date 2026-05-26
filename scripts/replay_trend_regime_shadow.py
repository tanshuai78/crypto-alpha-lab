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
from src.strategies.trend_regime.scanner import classify_trend_regime_snapshot
from src.strategies.trend_regime.shadow_simulator import (
    TrendRegimeShadowPosition,
    simulate_trend_regime_shadow,
)


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _summarize_pnl(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "trade_count": 0,
            "mean_net_pnl_bps": 0.0,
            "median_net_pnl_bps": 0.0,
            "win_rate": 0.0,
            "worst_trade_net_pnl_bps": 0.0,
        }

    net_values = [float(item["net_pnl_bps"]) for item in results]
    wins = [value for value in net_values if value > 0.0]
    return {
        "trade_count": len(results),
        "mean_net_pnl_bps": round(mean(net_values), 10),
        "median_net_pnl_bps": round(median(net_values), 10),
        "win_rate": round(len(wins) / len(results), 10),
        "worst_trade_net_pnl_bps": round(min(net_values), 10),
    }


def _grouped_summary(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        key = f"{item['regime']}|{item['direction']}|{item['symbol_tier']}"
        buckets[key].append(item)

    grouped: dict[str, dict[str, Any]] = {}
    for key, members in buckets.items():
        grouped[key] = _summarize_pnl(members)
    return grouped


def build_shadow_summary(rows: list[dict[str, Any]], *, estimated_cost_bps: float) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    entry_event_count = 0
    insufficient_path_count = 0
    missing_entry_price_count = 0

    for index, row in enumerate(rows):
        classification = classify_trend_regime_snapshot(row)
        if classification.event is None:
            continue

        event = classification.event
        entry_event_count += 1

        entry_price = _number_or_none(row.get("close_price"))
        entry_time_ms = int(_number_or_none(row.get("timestamp_ms")) or 0)
        if entry_price is None or entry_time_ms <= 0:
            missing_entry_price_count += 1
            continue

        path_rows = [
            item
            for item in rows[index + 1 :]
            if item.get("symbol") == event.symbol
            and int(_number_or_none(item.get("timestamp_ms")) or 0) > entry_time_ms
        ]

        if not path_rows:
            insufficient_path_count += 1
            continue

        position = TrendRegimeShadowPosition(
            symbol=event.symbol,
            direction=event.direction,
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            estimated_cost_bps=estimated_cost_bps,
            max_holding_hours=float(TREND_REGIME_MAX_HOLDING_HOURS),
            stop_loss_pct=float(TREND_REGIME_STOP_LOSS_PCT),
            regime=event.regime,
            symbol_tier=str(event.metadata.get("symbol_tier") or "unknown"),
        )
        simulated = simulate_trend_regime_shadow(position, path_rows)
        results.append(
            {
                "symbol": simulated.symbol,
                "regime": simulated.regime,
                "direction": simulated.direction,
                "symbol_tier": simulated.symbol_tier,
                "entry_time_ms": simulated.entry_time_ms,
                "exit_time_ms": simulated.exit_time_ms,
                "entry_price": simulated.entry_price,
                "exit_price": simulated.exit_price,
                "exit_reason": simulated.exit_reason,
                "gross_pnl_pct": simulated.gross_pnl_pct,
                "net_pnl_bps": simulated.net_pnl_bps,
            }
        )

    summary = {
        "input_row_count": len(rows),
        "entry_event_count": entry_event_count,
        "shadow_trade_count": len(results),
        "insufficient_path_count": insufficient_path_count,
        "missing_entry_price_count": missing_entry_price_count,
        "estimated_cost_bps": estimated_cost_bps,
        "coverage_quality": "historical_basis_proxy_not_depth_aware",
        "depth_aware": False,
        "results": results,
        "grouped_summary": _grouped_summary(results),
    }
    summary.update(_summarize_pnl(results))
    return summary


def build_dual_cost_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    base = build_shadow_summary(rows, estimated_cost_bps=float(TREND_REGIME_OBSERVATION_COST_BPS))
    stress = build_shadow_summary(rows, estimated_cost_bps=float(TREND_REGIME_STRESS_COST_BPS))
    return {
        "base_cost_bps": float(TREND_REGIME_OBSERVATION_COST_BPS),
        "stress_cost_bps": float(TREND_REGIME_STRESS_COST_BPS),
        "base": base,
        "stress": stress,
    }


def load_rows_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay trend-regime shadow from raw rows")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = load_rows_jsonl(args.input)
    summary = build_dual_cost_summary(rows)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
