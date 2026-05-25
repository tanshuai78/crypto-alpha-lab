from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from configs.base import (
    EXTREME_FUNDING_FEE_BPS,
    EXTREME_FUNDING_ROLLBACK_RESERVE_BPS,
    EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
    EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS,
    RISK_MAX_SINGLE_POSITION_USDT,
)
from scripts.replay_extreme_funding_basis_aware_candidates import load_basis_rows_jsonl
from src.research.extreme_funding_basis_replay import HistoricalBasisRow
from src.strategies.extreme_funding.shadow_simulator import (
    ExtremeFundingShadowPosition,
    simulate_extreme_funding_shadow,
)


def build_basis_aware_shadow_summary(rows: list[HistoricalBasisRow]) -> dict:
    if len(rows) < 2:
        return {
            "shadow_trade_count": 0,
            "coverage_quality": "insufficient_basis_data",
            "status": "insufficient_basis_path",
        }

    total_cost_bps = (
        EXTREME_FUNDING_FEE_BPS
        + EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS
        + EXTREME_FUNDING_ROLLBACK_RESERVE_BPS
    )
    pnl_values: list[float] = []
    exit_counts: dict[str, int] = {}
    symbols_seen: set[str] = set()

    rows_by_symbol: dict[str, list[HistoricalBasisRow]] = defaultdict(list)
    for row in rows:
        rows_by_symbol[row.symbol].append(row)

    for symbol, symbol_rows in rows_by_symbol.items():
        sorted_rows = sorted(symbol_rows, key=lambda row: row.funding_time_ms)
        for index, first in enumerate(sorted_rows[:-1]):
            path_rows = sorted_rows[
                index + 1 : index + 1 + EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS
            ]
            if not path_rows:
                continue
            symbols_seen.add(symbol)
            position = ExtremeFundingShadowPosition(
                symbol=first.symbol,
                side="long_spot_short_perp",
                entry_time_ms=first.funding_time_ms,
                entry_basis_bps=first.basis_bps,
                estimated_total_cost_bps=total_cost_bps,
                notional_usdt=RISK_MAX_SINGLE_POSITION_USDT,
                max_holding_intervals=EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
                coverage_quality="historical_basis_proxy_not_depth_aware",
            )
            result = simulate_extreme_funding_shadow(
                position,
                [
                    {
                        "funding_time_ms": row.funding_time_ms,
                        "funding_rate": row.funding_rate,
                        "basis_bps": row.basis_bps,
                        "annualized_pct": row.annualized_pct,
                    }
                    for row in path_rows
                ],
            )
            pnl_values.append(result.net_pnl_bps)
            exit_counts[result.exit_reason] = exit_counts.get(result.exit_reason, 0) + 1

    return {
        "shadow_trade_count": len(pnl_values),
        "median_net_pnl_bps": median(pnl_values) if pnl_values else 0.0,
        "mean_net_pnl_bps": mean(pnl_values) if pnl_values else 0.0,
        "win_rate": (
            sum(1 for value in pnl_values if value > 0.0) / len(pnl_values)
            if pnl_values
            else 0.0
        ),
        "exit_reason_counts": dict(sorted(exit_counts.items())),
        "coverage_quality": "historical_basis_proxy_not_depth_aware",
        "depth_aware": False,
        "depth_source": "static_min_capacity_proxy" if rows else None,
        "symbols": sorted(symbols_seen),
        "status": "ok" if pnl_values else "insufficient_basis_path",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate basis-aware extreme funding shadow replay.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = load_basis_rows_jsonl(args.input)
    summary = build_basis_aware_shadow_summary(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
