import argparse
import json
import os
import sys
from collections import Counter
from typing import Sequence

from configs import base
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_baseline import (
    compute_left_tail,
    compute_price_move_baseline,
    compute_random_baseline_summary,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_loader import (
    load_json_or_jsonl_paths,
    normalize_funding_rows,
    normalize_oi_rows,
    normalize_price_rows,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    CANDIDATE_1H,
    CANDIDATE_15M,
    DECISION_INCONCLUSIVE,
    SECONDARY_NONE,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_quality import (
    build_source_quality_report,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_replay import (
    replay_deleveraging_proxy_events,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_signals import (
    detect_deleveraging_proxy_events,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_summary import (
    build_candidate_summary,
)


def _median_net_bps(replayed_rows: list[dict], hours: int) -> float:
    vals = [r["net_return_bps_after_50bps"] for r in replayed_rows if r["forward_window_hours"] == hours]
    if not vals:
        return 0.0
    vals.sort()
    n = len(vals)
    if n % 2 == 1:
        return float(vals[n // 2])
    return float((vals[n // 2 - 1] + vals[n // 2]) / 2.0)


def _event_concentration(events: list) -> dict:
    if not events:
        return {
            "symbols_with_events": 0,
            "max_single_day_event_share": 0.0,
            "max_single_symbol_event_share": 0.0,
        }
    total = len(events)
    day_counts = Counter(event.event_time_ms // (24 * 3600 * 1000) for event in events)
    symbol_counts = Counter(event.symbol for event in events)
    return {
        "symbols_with_events": len(symbol_counts),
        "max_single_day_event_share": max(day_counts.values(), default=0) / total,
        "max_single_symbol_event_share": max(symbol_counts.values(), default=0) / total,
    }


def _top5_positive_gross_profit_share(replayed_rows: list[dict]) -> float:
    positive_gross = [
        r["gross_return_bps"]
        for r in replayed_rows
        if r["forward_window_hours"] == 4 and r["gross_return_bps"] > 0
    ]
    total_positive = sum(positive_gross)
    if total_positive <= 0:
        return 0.0
    return sum(sorted(positive_gross, reverse=True)[:5]) / total_positive


def _left_tail_4h_net_bps(replayed_rows: list[dict]) -> float:
    values = [
        r["net_return_bps_after_50bps"]
        for r in replayed_rows
        if r["forward_window_hours"] == 4
    ]
    return compute_left_tail(
        values,
        base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_LEFT_TAIL_PERCENTILE,
    )


def _build_funding_context_summary(funding_rows: list[dict]) -> dict:
    symbols = sorted({row["symbol"] for row in funding_rows})
    min_time = min((row["funding_time_ms"] for row in funding_rows), default=0)
    max_time = max((row["funding_time_ms"] for row in funding_rows), default=0)
    history_days = (max_time - min_time) / (24.0 * 3600.0 * 1000.0) if max_time > min_time else 0.0
    return {
        "funding_context_used": bool(funding_rows),
        "funding_rows_loaded": len(funding_rows),
        "funding_symbols": symbols,
        "funding_history_days": history_days,
        "funding_source": "binance_settled_funding_rate",
        "funding_source_quality": "settled_rate_not_realtime_prediction",
        "funding_used_for_signal_generation": False,
    }


def run_pipeline(
    oi_archive: str,
    price_archive: str,
    funding_archive: str | None,
    output_summary: str,
    random_baseline_trials_override: int | None,
    fixture_run: bool,
) -> None:
    expected_symbols = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "XRPUSDT")

    # 1. Load data
    print("Loading OI archive...")
    raw_oi = load_json_or_jsonl_paths([oi_archive])
    print("Loading Price archive...")
    raw_price = load_json_or_jsonl_paths([price_archive])
    raw_funding = []
    if funding_archive:
        print("Loading Funding archive...")
        raw_funding = load_json_or_jsonl_paths([funding_archive])

    normalized_oi = normalize_oi_rows(raw_oi)
    normalized_price = normalize_price_rows(raw_price)
    normalized_funding = normalize_funding_rows(raw_funding) if raw_funding else []
    funding_context_summary = _build_funding_context_summary(normalized_funding)

    # 2. Build quality report
    print("Building source quality report...")
    quality = build_source_quality_report(normalized_oi, normalized_price, expected_symbols)

    summary_output = {}

    for candidate in (CANDIDATE_15M, CANDIDATE_1H):
        print(f"\nProcessing candidate: {candidate}...")

        # 3. Detect events
        events, status = detect_deleveraging_proxy_events(
            oi_rows=normalized_oi,
            price_rows=normalized_price,
            candidate_name=candidate,
            source_quality=quality,
            expected_symbols=expected_symbols
        )
        print(f"Detected {len(events)} events for {candidate}. Status: {status}")

        # 4. Replay candidate events
        replayed_candidate = replay_deleveraging_proxy_events(events, normalized_price)
        med_1h = _median_net_bps(replayed_candidate, 1)
        med_4h = _median_net_bps(replayed_candidate, 4)
        med_12h = _median_net_bps(replayed_candidate, 12)
        candidate_left_tail_4h = _left_tail_4h_net_bps(replayed_candidate)
        top5_positive_share = _top5_positive_gross_profit_share(replayed_candidate)
        concentration = _event_concentration(events)

        # 5. Price baseline
        price_events = compute_price_move_baseline(normalized_price, candidate, expected_symbols)
        replayed_price_baseline = replay_deleveraging_proxy_events(price_events, normalized_price)
        price_baseline_4h_med = _median_net_bps(replayed_price_baseline, 4)
        print(f"Price baseline events: {len(price_events)}. 4h Median: {price_baseline_4h_med:.2f} bps")

        # 6. Random baseline
        trials = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_RANDOM_BASELINE_TRIALS
        baseline_trials_override_used = False
        if random_baseline_trials_override is not None:
            trials = random_baseline_trials_override
            baseline_trials_override_used = True

        print(f"Running random baseline with {trials} trials...")
        random_seed = 42
        random_summary = compute_random_baseline_summary(
            candidate_events=events,
            price_bars=normalized_price,
            trials=trials,
            random_seed=random_seed
        )
        random_baseline_4h_med = random_summary["median_net_return_bps_after_50bps"]
        random_left_tail_4h = random_summary["left_tail_net_return_bps_after_50bps_4h"]
        print(f"Random baseline 4h Median: {random_baseline_4h_med:.2f} bps")

        # 7. Check research result validity
        research_result_valid = True
        research_result_notes = []

        if baseline_trials_override_used:
            research_result_valid = False
            research_result_notes.append("debug_baseline_override_used")

        min_history_days = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_RESEARCH_RESULT_HISTORY_DAYS
        min_history = min(quality["oi_history_days"], quality["price_history_days"])
        if min_history < min_history_days:
            research_result_valid = False
            research_result_notes.append("insufficient_history_duration")

        data_supported = quality.get("candidate_window_supported_overall", {}).get(candidate, False)
        if not data_supported:
            research_result_valid = False
            research_result_notes.append("data_unsupported")

        # 8. Build Summary
        candidate_sum = build_candidate_summary(
            candidate_name=candidate,
            events_detected=len(events),
            distinct_days=len(set(r.event_time_ms // (24 * 3600 * 1000) for r in events)),
            replayed_median_bps_1h=med_1h,
            replayed_median_bps_4h=med_4h,
            replayed_median_bps_12h=med_12h,
            random_baseline_4h_median_bps=random_baseline_4h_med,
            price_baseline_4h_median_bps=price_baseline_4h_med,
            symbols_with_events=concentration["symbols_with_events"],
            candidate_left_tail_bps=candidate_left_tail_4h,
            random_baseline_left_tail_bps=random_left_tail_4h,
            top5_positive_gross_profit_share=top5_positive_share,
            max_single_day_event_share=concentration["max_single_day_event_share"],
            max_single_symbol_event_share=concentration["max_single_symbol_event_share"],
            source_quality=quality,
            random_baseline_trials=trials,
            baseline_sampling_failure_count=random_summary["baseline_sampling_failure_count"],
            funding_context_summary=funding_context_summary,
            fixture_run=fixture_run,
            research_result_valid=research_result_valid
        )

        candidate_sum["baseline_trials_override_used"] = baseline_trials_override_used
        candidate_sum["research_result_notes"] = research_result_notes

        if not research_result_valid:
            candidate_sum["decision"] = DECISION_INCONCLUSIVE
            candidate_sum["secondary_status"] = SECONDARY_NONE

        summary_output[candidate] = candidate_sum

    # Write summary
    os.makedirs(os.path.dirname(output_summary), exist_ok=True)
    with open(output_summary, "w", encoding="utf-8") as f:
        json.dump(summary_output, f, indent=2)
    print(f"\nWritten summary JSON to {output_summary}")

def main(args: Sequence[str] | None = None) -> None:
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Stage 1.4E Deleveraging Proxy Review Runner")
    parser.add_argument("--oi-archive", required=True, help="Path/glob to Open Interest data file(s)")
    parser.add_argument("--price-archive", required=True, help="Path/glob to Price data file(s)")
    parser.add_argument("--funding-archive", help="Path/glob to Funding data file(s)")
    parser.add_argument("--output-summary", required=True, help="Path to output summary JSON file")
    parser.add_argument("--random-baseline-trials", type=int, help="Override random baseline trials for debug")
    parser.add_argument("--fixture-run", action="store_true", help="Mark run as fixture smoke run")

    parsed = parser.parse_args(args)
    run_pipeline(
        oi_archive=parsed.oi_archive,
        price_archive=parsed.price_archive,
        funding_archive=parsed.funding_archive,
        output_summary=parsed.output_summary,
        random_baseline_trials_override=parsed.random_baseline_trials,
        fixture_run=parsed.fixture_run
    )

if __name__ == "__main__":
    main()
