import argparse
import json
import os
import sys
from typing import List

from configs import base
from research.external_signal_shadow.stage1_4b_lite_baseline import (
    compute_price_move_1h_baseline,
    compute_random_baseline_summary,
)
from research.external_signal_shadow.stage1_4b_lite_loader import (
    load_funding_rows,
    load_oi_rows,
    load_price_rows,
)
from research.external_signal_shadow.stage1_4b_lite_replay import (
    replay_candidate_events,
)
from research.external_signal_shadow.stage1_4b_lite_signals import (
    detect_candidate_events,
)
from research.external_signal_shadow.stage1_4b_lite_summary import (
    compute_concentration_stats,
    decide_candidate_family_summary,
    decide_stage1_4b_lite_summary,
)


def run_pipeline(
    funding_path: str,
    oi_path: str,
    price_path: str,
    fixture_run: bool,
    random_baseline_trials: int,
) -> dict:
    # 1. Load data
    funding = load_funding_rows(funding_path)
    oi = load_oi_rows(oi_path)
    price = load_price_rows(price_path)

    # Whitelisted symbols
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]

    # 2. Detect events
    all_events = []
    for symbol in symbols:
        symbol_events = detect_candidate_events(
            symbol=symbol,
            funding_rows=funding,
            oi_rows=oi,
            price_bars=price,
        )
        all_events.extend(symbol_events)

    # 3. Replay candidate events
    replay_results = replay_candidate_events(all_events, price)

    # 4. Matched price baseline
    price_move_events = compute_price_move_1h_baseline(price, default_symbols=symbols)
    price_move_results = replay_candidate_events(price_move_events, price)
    price_move_returns = [r["terminal_return_4h_net_bps_after_50bps"] for r in price_move_results]

    if price_move_returns:
        price_move_returns.sort()
        n = len(price_move_returns)
        price_move_median = price_move_returns[n // 2] if n % 2 == 1 else (price_move_returns[n // 2 - 1] + price_move_returns[n // 2]) / 2.0
    else:
        price_move_median = 0.0

    # 5. Evaluate per family
    candidates_results = {}
    families = [
        "oi_expansion_trend_confirmation",
        "funding_oi_crowding_unwind",
        "oi_contraction_after_price_flush",
    ]

    for family in families:
        family_events = [e for e in all_events if e.candidate_name == family]
        family_replays = [r for r in replay_results if r["candidate_name"] == family]

        family_returns = [r["terminal_return_4h_net_bps_after_50bps"] for r in family_replays]
        if family_returns:
            family_returns.sort()
            n = len(family_returns)
            family_median = family_returns[n // 2] if n % 2 == 1 else (family_returns[n // 2 - 1] + family_returns[n // 2]) / 2.0
        else:
            family_median = 0.0

        # Matched random baseline for this family specifically
        family_random = compute_random_baseline_summary(
            family_events,
            price,
            trials=random_baseline_trials,
            random_seed=42
        )

        # Calculate stats
        family_days = len({int(e.event_time_ms) // (24 * 3600 * 1000) for e in family_events})
        family_symbols = len({e.symbol for e in family_events})

        family_stats = compute_concentration_stats(family_events, family_replays)

        # Candidate-level decision
        cand_data = {
            "candidate_name": family,
            "event_count": len(family_events),
            "event_days": family_days,
            "symbols_count": family_symbols,
            "median_net_return_bps": family_median,
            "random_baseline_median_bps": family_random["median_net_return_bps_after_50bps"],
            "price_move_baseline_median_bps": price_move_median,
            "max_single_symbol_event_share": family_stats["max_single_symbol_event_share"],
            "max_single_day_event_share": family_stats["max_single_day_event_share"],
            "top_5_positive_events_gross_profit_share": family_stats["top_5_positive_events_gross_profit_share"],
            "top_5_abs_pnl_share": family_stats["top_5_abs_pnl_share"],
        }

        family_decision = decide_candidate_family_summary(cand_data)
        cand_data["decision"] = family_decision["decision"]
        cand_data["blocker"] = family_decision["blocker"]

        candidates_results[family] = cand_data

    # 6. Overall stats
    overall_stats = compute_concentration_stats(all_events, replay_results)
    overall_days = len({int(e.event_time_ms) // (24 * 3600 * 1000) for e in all_events})
    overall_symbols = len({e.symbol for e in all_events})

    summary_data = {
        "fixture_run": fixture_run,
        "total_events": len(all_events),
        "total_days": overall_days,
        "total_symbols": overall_symbols,
        "max_single_symbol_event_share": overall_stats["max_single_symbol_event_share"],
        "max_single_day_event_share": overall_stats["max_single_day_event_share"],
        "top_5_positive_events_gross_profit_share": overall_stats["top_5_positive_events_gross_profit_share"],
        "top_5_abs_pnl_share": overall_stats["top_5_abs_pnl_share"],
        "random_baseline_trials": random_baseline_trials,
        "candidates": candidates_results,
    }

    # 7. Final overall decision and safety fields
    final_summary = decide_stage1_4b_lite_summary(summary_data)
    final_summary.update(summary_data)

    return final_summary


def main(args_list: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Stage 1.4B-Lite crowding-only replay runner")
    parser.add_argument("--funding-input", required=True, help="Path to funding rates input")
    parser.add_argument("--oi-input", required=True, help="Path to open interest input")
    parser.add_argument("--price-input", required=True, help="Path to futures price klines input")
    parser.add_argument("--output-summary", required=True, help="Path to write the summary JSON")
    parser.add_argument("--fixture-run", action="store_true", help="Set to true for fixture smoketest runs")
    parser.add_argument(
        "--random-baseline-trials",
        type=int,
        default=base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_RANDOM_BASELINE_TRIALS,
        help="Override random baseline trial count for debug or controlled runs",
    )

    args = parser.parse_args(args_list)

    try:
        summary = run_pipeline(
            funding_path=args.funding_input,
            oi_path=args.oi_input,
            price_path=args.price_input,
            fixture_run=args.fixture_run,
            random_baseline_trials=args.random_baseline_trials,
        )

        # Ensure parent directories exist
        os.makedirs(os.path.dirname(os.path.abspath(args.output_summary)), exist_ok=True)

        with open(args.output_summary, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"Summary successfully written to {args.output_summary}")
        return 0
    except Exception as e:
        print(f"Error executing Stage 1.4B-Lite pipeline: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
