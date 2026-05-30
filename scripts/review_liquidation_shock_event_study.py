from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

from configs.base import (
    LIQUIDATION_SHOCK_MAX_SINGLE_SYMBOL_EVENT_SHARE,
    LIQUIDATION_SHOCK_MIN_ABS_MEDIAN_RESPONSE_BPS,
    LIQUIDATION_SHOCK_MIN_DIRECTIONAL_BIAS,
    LIQUIDATION_SHOCK_MIN_EVENTS_PER_24H,
    LIQUIDATION_SHOCK_MIN_MINMOVE_DIRECTIONAL_BIAS,
    LIQUIDATION_SHOCK_MIN_POSITIVE_SYMBOL_COUNT,
    LIQUIDATION_SHOCK_MIN_SYMBOL_EVENTS,
    LIQUIDATION_SHOCK_MIN_TOTAL_EVENTS,
    LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES,
)
from src.research.liquidation_shock_event_study.event_contract import LiquidationShockEvent
from src.research.liquidation_shock_event_study.response_map import build_response_map

logger = logging.getLogger(__name__)


def evaluate_events(
    eval_results: list[dict[str, Any]],
    total_duration_days: float,
) -> dict[str, Any]:
    event_count = len(eval_results)
    events_per_24h = event_count / total_duration_days if total_duration_days > 0 else 0.0

    # Symbol distribution
    symbol_dist = {}
    for r in eval_results:
        sym = r["symbol"]
        symbol_dist[sym] = symbol_dist.get(sym, 0) + 1

    # Initialize statistics
    direction_dist = {}
    mm_direction_dist = {}
    bps_dist = {}
    directional_bias = {}
    mm_directional_bias = {}
    median_bps = {}

    for h in LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES:
        # Direction distributions
        up_count = sum(1 for r in eval_results if r["sign_directions"][h] == 1)
        down_count = sum(1 for r in eval_results if r["sign_directions"][h] == -1)
        flat_count = sum(1 for r in eval_results if r["sign_directions"][h] == 0)

        direction_dist[h] = {"up": up_count, "down": down_count, "flat": flat_count}
        total_directional = up_count + down_count
        directional_bias[h] = (
            max(up_count, down_count) / total_directional if total_directional > 0 else 0.5
        )

        # Min-move filtered direction distributions
        mm_up = sum(1 for r in eval_results if r["min_move_directions"][h] == 1)
        mm_down = sum(1 for r in eval_results if r["min_move_directions"][h] == -1)
        mm_flat = sum(1 for r in eval_results if r["min_move_directions"][h] == 0)

        mm_direction_dist[h] = {"up": mm_up, "down": mm_down, "flat": mm_flat}
        total_mm = mm_up + mm_down
        mm_directional_bias[h] = max(mm_up, mm_down) / total_mm if total_mm > 0 else 0.5

        # Bps statistics
        all_bps = [r["bps_changes"][h] for r in eval_results]
        all_dir_bps = [r["directional_bps"][h] for r in eval_results]

        all_bps_sorted = sorted(all_bps)
        all_dir_bps_sorted = sorted(all_dir_bps)

        bps_dist[h] = {
            "min": round(all_bps_sorted[0], 2) if all_bps_sorted else 0.0,
            "max": round(all_bps_sorted[-1], 2) if all_bps_sorted else 0.0,
            "mean": round(sum(all_bps) / len(all_bps), 2) if all_bps else 0.0,
            "median": round(all_bps_sorted[len(all_bps_sorted) // 2], 2) if all_bps_sorted else 0.0,
        }

        median_bps[h] = (
            round(all_dir_bps_sorted[len(all_dir_bps_sorted) // 2], 2)
            if all_dir_bps_sorted
            else 0.0
        )

    return {
        "event_count": event_count,
        "events_per_24h": round(events_per_24h, 2),
        "symbol_distribution": symbol_dist,
        "direction_distribution_by_horizon": direction_dist,
        "minimum_move_filtered_direction_distribution": mm_direction_dist,
        "bps_distribution_by_horizon": bps_dist,
        "directional_bias_by_horizon": directional_bias,
        "minimum_move_filtered_directional_bias": mm_directional_bias,
        "median_response_bps_by_horizon": median_bps,
    }


def make_decision(summary: dict[str, Any]) -> tuple[str, str, list[str], str]:
    failed_checks = []

    # 1. Total event count check
    event_count = summary["event_count"]
    if event_count < LIQUIDATION_SHOCK_MIN_TOTAL_EVENTS:
        failed_checks.append(
            f"event_count < {LIQUIDATION_SHOCK_MIN_TOTAL_EVENTS} (actual: {event_count})"
        )

    # 2. Events per 24h check
    events_per_24h = summary["events_per_24h"]
    if events_per_24h < LIQUIDATION_SHOCK_MIN_EVENTS_PER_24H:
        failed_checks.append(
            f"events_per_24h < {LIQUIDATION_SHOCK_MIN_EVENTS_PER_24H} (actual: {events_per_24h})"
        )

    # 3. Symbol distribution checks
    symbol_dist = summary["symbol_distribution"]
    positive_symbols = [
        sym for sym, count in symbol_dist.items() if count >= LIQUIDATION_SHOCK_MIN_SYMBOL_EVENTS
    ]
    if len(positive_symbols) < LIQUIDATION_SHOCK_MIN_POSITIVE_SYMBOL_COUNT:
        failed_checks.append(
            f"positive_symbols < {LIQUIDATION_SHOCK_MIN_POSITIVE_SYMBOL_COUNT} "
            f"(actual: {len(positive_symbols)}, symbols: {positive_symbols})"
        )

    # 4. Symbol concentration check
    if event_count > 0:
        max_share = max(symbol_dist.values()) / event_count
        if max_share > LIQUIDATION_SHOCK_MAX_SINGLE_SYMBOL_EVENT_SHARE:
            failed_checks.append(
                f"max_single_symbol_share > {LIQUIDATION_SHOCK_MAX_SINGLE_SYMBOL_EVENT_SHARE} "
                f"(actual: {round(max_share, 2)})"
            )

    # 5. Adjacent horizons passing check
    # Check which horizons pass the 3 conditions: bias >= 0.55, mm_bias >= 0.55, abs_median_bps >= 2.0
    passed_horizons = set()
    for h in [5, 10, 15]:
        bias = summary["directional_bias_by_horizon"].get(h, 0.0)
        mm_bias = summary["minimum_move_filtered_directional_bias"].get(h, 0.0)
        med_bps = summary["median_response_bps_by_horizon"].get(h, 0.0)

        if (
            bias >= LIQUIDATION_SHOCK_MIN_DIRECTIONAL_BIAS
            and mm_bias >= LIQUIDATION_SHOCK_MIN_MINMOVE_DIRECTIONAL_BIAS
            and abs(med_bps) >= LIQUIDATION_SHOCK_MIN_ABS_MEDIAN_RESPONSE_BPS
        ):
            passed_horizons.add(h)

    # Check adjacency (e.g. {5, 10} or {10, 15})
    has_adjacent_pass = (5 in passed_horizons and 10 in passed_horizons) or (
        10 in passed_horizons and 15 in passed_horizons
    )

    if not has_adjacent_pass:
        failed_checks.append(
            f"no adjacent horizons passed criteria (passed: {sorted(list(passed_horizons))}, "
            f"bias: {summary['directional_bias_by_horizon']}, mm_bias: {summary['minimum_move_filtered_directional_bias']}, "
            f"median_bps: {summary['median_response_bps_by_horizon']})"
        )

    # Determine decision state
    if not failed_checks:
        return (
            "continue_to_context_bucketing",
            "All success criteria satisfied.",
            [],
            "proceed_to_context_bucketing",
        )

    # If density or data depth failed
    if "event_count" in "".join(failed_checks) or "events_per_24h" in "".join(failed_checks):
        decision = "insufficient_event_density"
    elif "no adjacent horizons" in "".join(failed_checks):
        decision = "retire_liquidation_shock_event_study"
    else:
        decision = "retire_liquidation_shock_event_study"

    reason = f"Failed checks: {', '.join(failed_checks)}"
    next_action = (
        "improve_data_or_event_density"
        if decision == "insufficient_event_density"
        else "stop_liquidation_shock_line"
    )
    return decision, reason, failed_checks, next_action


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review liquidation shock 1m event study outcomes."
    )
    parser.add_argument(
        "--dataset-jsonl",
        default="reports/liquidation_shock_event_study/liquidation_shock_1m_dataset.jsonl",
        help="Path to the aligned dataset JSONL",
    )
    parser.add_argument(
        "--events-jsonl",
        default="reports/liquidation_shock_event_study/liquidation_shock_1m_events.jsonl",
        help="Path to the detected events JSONL",
    )
    parser.add_argument(
        "--summary-output",
        default="reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_summary.json",
        help="Output path for the review summary JSON",
    )
    parser.add_argument(
        "--review-output-md",
        default="docs/reviews/2026-05-30-liquidation-shock-event-study-review.md",
        help="Output path for the review markdown report",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    # 1. Load aligned dataset into price map
    price_map = {}
    if not os.path.exists(args.dataset_jsonl):
        logger.error(f"Dataset file {args.dataset_jsonl} does not exist. Cannot run review.")
        return 1

    min_ts = None
    max_ts = None
    with open(args.dataset_jsonl, "r") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                ts = row["bar_start_ms"]
                price_map[ts] = row
                if min_ts is None or ts < min_ts:
                    min_ts = ts
                if max_ts is None or ts > max_ts:
                    max_ts = ts

    total_duration_days = (
        (max_ts - min_ts) / (86400.0 * 1000.0) if min_ts is not None and max_ts is not None else 0.0
    )

    # 2. Load events and build response map
    if not os.path.exists(args.events_jsonl):
        logger.error(f"Events file {args.events_jsonl} does not exist. Cannot run review.")
        return 1

    eval_results = []
    with open(args.events_jsonl, "r") as f:
        for line in f:
            if line.strip():
                ev_dict = json.loads(line)
                # Reconstruct dataclass
                ev = LiquidationShockEvent(
                    symbol=ev_dict["symbol"],
                    shock_bar_start_ms=ev_dict["shock_bar_start_ms"],
                    liquidated_position_side=ev_dict["liquidated_position_side"],
                    dominant_liquidation_side=ev_dict["dominant_liquidation_side"],
                    shock_notional_usdt=ev_dict["shock_notional_usdt"],
                    relative_score=ev_dict["relative_score"],
                    relative_score_method=ev_dict["relative_score_method"],
                    reference_count=ev_dict["reference_count"],
                    required_reference_count=ev_dict["required_reference_count"],
                    dominance_ratio=ev_dict["dominance_ratio"],
                    dedup_bucket_start_ms=ev_dict["dedup_bucket_start_ms"],
                    source_namespace=ev_dict["source_namespace"],
                )

                res = build_response_map(ev, price_map)
                if res:
                    eval_results.append(res)

    # 3. Evaluate events
    summary = evaluate_events(eval_results, total_duration_days)

    # 4. Make decision
    decision, reason, failed_checks, next_action = make_decision(summary)

    summary["decision"] = decision
    summary["primary_falsification_reason"] = reason if failed_checks else ""
    summary["failed_checks"] = failed_checks
    summary["next_action"] = next_action

    # Save summary report
    os.makedirs(os.path.dirname(os.path.abspath(args.summary_output)), exist_ok=True)
    with open(args.summary_output, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Saved review summary report to {args.summary_output}")

    # Generate markdown report
    markdown_report = f"""# Liquidation Shock 1m Event Study Review

**Review Date:** 2026-05-30
**Data Range:** {total_duration_days:.2f} Days
**Decision:** `{decision.upper()}`
**Details:** {reason}

---

## 1. Executive Summary

- **Total Deduplicated Shock Events:** {summary["event_count"]}
- **Event Frequency (per 24h):** {summary["events_per_24h"]}
- **Success Criteria Checks:** {"Passed" if not failed_checks else "Failed"}

### Symbol Distribution:
"""
    for sym, count in summary["symbol_distribution"].items():
        markdown_report += f"- **{sym}:** {count} events ({count / summary['event_count']:.1%})\n"

    markdown_report += """
---

## 2. Response Analysis by Horizon

| Horizon | Raw Up Count | Raw Down Count | Raw Flat Count | Directional Bias | Min-Move Up | Min-Move Down | Min-Move Flat | Min-Move Bias | Median Dir Return (bps) |
|---|---|---|---|---|---|---|---|---|---|
"""
    for h in LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES:
        dd = summary["direction_distribution_by_horizon"][h]
        bias = summary["directional_bias_by_horizon"][h]
        mm_dd = summary["minimum_move_filtered_direction_distribution"][h]
        mm_bias = summary["minimum_move_filtered_directional_bias"][h]
        med_b = summary["median_response_bps_by_horizon"][h]

        markdown_report += (
            f"| {h}m | {dd['up']} | {dd['down']} | {dd['flat']} | {bias:.1%} | "
            f"{mm_dd['up']} | {mm_dd['down']} | {mm_dd['flat']} | {mm_bias:.1%} | {med_b:+.2f} bps |\n"
        )

    markdown_report += """
---

## 3. Return Distribution Stats

| Horizon | Min Return (bps) | Max Return (bps) | Mean Return (bps) | Median Return (bps) |
|---|---|---|---|---|
"""
    for h in LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES:
        bps_s = summary["bps_distribution_by_horizon"][h]
        markdown_report += (
            f"| {h}m | {bps_s['min']:+.2f} bps | {bps_s['max']:+.2f} bps | "
            f"{bps_s['mean']:+.2f} bps | {bps_s['median']:+.2f} bps |\n"
        )

    markdown_report += """
---

## 4. Failed Checks Details

"""
    if failed_checks:
        for fc in failed_checks:
            markdown_report += f"- [x] **FAIL**: {fc}\n"
    else:
        markdown_report += "- None. All checks passed!\n"

    markdown_report += """
---

## 5. Conclusion & Action Item

Based on the quantitative criteria, the event study has determined that:
"""
    if decision == "continue_to_context_bucketing":
        markdown_report += (
            "\n**PROCEED TO CONTEXT BUCKETING (Phase 2)**: There is a statistically stable directional "
            "bias across adjacent horizons. Next action: "
            f"`{next_action}`.\n"
        )
    else:
        markdown_report += (
            f"\n**RETIRE / STOP CURRENT LINE**: The directional signal structure failed due to: {reason}. "
            f"Next action: `{next_action}`.\n"
        )

    os.makedirs(os.path.dirname(os.path.abspath(args.review_output_md)), exist_ok=True)
    with open(args.review_output_md, "w") as f:
        f.write(markdown_report)
    logger.info(f"Saved markdown review report to {args.review_output_md}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
