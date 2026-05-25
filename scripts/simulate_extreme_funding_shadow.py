from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any

from configs.base import (
    EXTREME_FUNDING_FEE_BPS,
    EXTREME_FUNDING_ROLLBACK_RESERVE_BPS,
    EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
    EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS,
)
from src.research.extreme_funding_replay import (
    detect_extreme_funding_segments,
    load_settled_funding_rows,
)


def build_shadow_replay_summary(segments: list[dict[str, Any]]) -> dict[str, Any]:
    total_cost_bps = (
        EXTREME_FUNDING_FEE_BPS
        + EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS
        + EXTREME_FUNDING_ROLLBACK_RESERVE_BPS
    )
    funding_minus_cost_values: list[float] = []

    for segment in segments:
        capped_income = float(segment["funding_income_bps"])
        if int(segment["row_count"]) > EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS:
            capped_income = (
                capped_income
                * EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS
                / int(segment["row_count"])
            )
        funding_minus_cost_values.append(capped_income - total_cost_bps)

    return {
        "shadow_trade_count": len(funding_minus_cost_values),
        "median_funding_minus_cost_bps": (
            median(funding_minus_cost_values)
            if funding_minus_cost_values
            else 0.0
        ),
        "mean_funding_minus_cost_bps": (
            sum(funding_minus_cost_values) / len(funding_minus_cost_values)
            if funding_minus_cost_values
            else 0.0
        ),
        "positive_funding_minus_cost_rate": (
            sum(1 for value in funding_minus_cost_values if value > 0.0)
            / len(funding_minus_cost_values)
            if funding_minus_cost_values
            else 0.0
        ),
        "coverage_quality": "funding_only_insufficient_for_basis",
        "notes": [
            "funding_only_replay_does_not_validate_basis_absorption",
            "funding_only_replay_does_not_validate_net_pnl",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate extreme funding Phase 1C funding-only diagnostics."
    )
    parser.add_argument(
        "--input-glob",
        default="data/funding_settled/binance_*_settled.jsonl",
    )
    parser.add_argument("--threshold-pct", type=float, default=100.0)
    parser.add_argument(
        "--output",
        default="reports/extreme_funding/2026-05-25_shadow_replay_summary.json",
    )
    args = parser.parse_args()

    segments: list[dict[str, Any]] = []
    for path in sorted(Path().glob(args.input_glob)):
        segments.extend(
            detect_extreme_funding_segments(
                load_settled_funding_rows(path),
                threshold_pct=args.threshold_pct,
            )
        )

    summary = build_shadow_replay_summary(segments)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
