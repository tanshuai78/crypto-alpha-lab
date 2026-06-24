import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from configs import base
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_baseline import (
    compute_price_move_baseline_events,
    sample_symbol_hour_event_type_matched_random_baseline,
)
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_candidates import (
    apply_event_cooldown,
    build_replay_candidates,
)
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_engine import (
    replay_candidates,
)
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_loader import (
    assert_stage1_5b_ready,
    load_price_bars,
    load_stage1_5b_symbol_events,
)
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_models import (
    ExternalCatalystReplayCandidate,
)
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_quality import (
    build_price_index,
    evaluate_event_price_coverage,
    find_first_bar_at_or_after,
    percentiles,
)
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_summary import (
    compute_concentration_metrics,
    decide_stage1_5c_replay_summary,
)


def _make_baseline_candidate_from_event(
    event: dict,
    price_index: dict,
    entry_delay_hours: int,
    signed_mode: str,
) -> ExternalCatalystReplayCandidate | None:
    symbol = event["symbol"]
    symbol_bars = price_index.get(symbol, [])
    available_at_ms = int(event["available_at_ms"])
    entry_candidate_time_ms = available_at_ms + entry_delay_hours * 3600_000
    entry_bar = find_first_bar_at_or_after(symbol_bars, entry_candidate_time_ms)
    if entry_bar is None:
        return None

    return ExternalCatalystReplayCandidate(
        symbol_event_id=event.get("symbol_event_id", f"{signed_mode}_{symbol}_{available_at_ms}"),
        event_type=event.get("event_type", signed_mode),
        signed_mode=signed_mode,
        signed_direction=int(event["signed_direction"]),
        symbol=symbol,
        event_time_ms=int(event["event_time_ms"]),
        available_at_ms=available_at_ms,
        entry_delay_hours=entry_delay_hours,
        entry_candidate_time_ms=entry_candidate_time_ms,
        entry_bar_start_ms=int(entry_bar["bar_start_ms"]),
        entry_price=float(entry_bar["open"]),
        price_history_coverage_verified=True,
        market_pair_existence_verified=True,
        liquidity_proxy_verified=False,
        replay_allowed=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Run Stage 1.5C External Catalyst Replay")
    parser.add_argument("--events-jsonl", required=True, help="Path to Stage 1.5B normalized events JSONL")
    parser.add_argument("--stage1-5b-summary", required=True, help="Path to Stage 1.5B normalization summary JSON")
    parser.add_argument("--price-jsonl", required=True, help="Path to price archive JSONL")
    parser.add_argument("--output-candidates-jsonl", required=True, help="Path to write replay candidates JSONL")
    parser.add_argument("--output-results-jsonl", required=True, help="Path to write replay results JSONL")
    parser.add_argument("--output-summary", required=True, help="Path to write replay summary JSON")
    parser.add_argument("--random-baseline-trials", type=int, default=500, help="Number of random baseline trials")

    args = parser.parse_args()

    # 1. Assert Stage 1.5B ready
    assert_stage1_5b_ready(args.stage1_5b_summary)

    # 2. Load events and prices
    events = load_stage1_5b_symbol_events(args.events_jsonl)
    price_bars = load_price_bars(args.price_jsonl)
    price_index = build_price_index(price_bars)

    # 3. Evaluate coverage for all events across all entry delays
    coverage_reports = {}
    delays = base.EXTERNAL_SIGNAL_STAGE1_5C_ENTRY_DELAY_HOURS
    for ev in events:
        for delay in delays:
            report = evaluate_event_price_coverage(
                ev, price_index, delay, base.EXTERNAL_SIGNAL_STAGE1_5C_FORWARD_WINDOWS_HOURS
            )
            coverage_reports[(ev["symbol_event_id"], delay)] = report

    # 4. Coverage Attrition Funnel calculations (evaluated at primary delay 1h)
    primary_delay = base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_ENTRY_DELAY_HOURS
    total_loaded = len(events)
    existence_count = 0
    coverage_pass_count = 0
    liquidity_pass_count = 0
    reject_reason_counts = {}

    for ev in events:
        rep = coverage_reports.get((ev["symbol_event_id"], primary_delay))
        if rep:
            if rep["market_pair_existence_verified"]:
                existence_count += 1
            if rep["price_coverage_gate_passed"]:
                coverage_pass_count += 1
            if rep["liquidity_proxy_pass"]:
                liquidity_pass_count += 1
            reason = rep["coverage_reject_reason"]
            if reason:
                reject_reason_counts[reason] = reject_reason_counts.get(reason, 0) + 1

    # 5. Build candidates across all delays
    all_candidates = []
    cooldown_candidates = []
    for delay in delays:
        delay_candidates = build_replay_candidates(events, coverage_reports, delay)
        # convert candidates to dicts temporarily for apply_event_cooldown
        candidate_dicts = []
        for c in delay_candidates:
            d = c.__dict__.copy()
            candidate_dicts.append(d)

        # apply cooldown
        cooldown_dicts = apply_event_cooldown(candidate_dicts, base.EXTERNAL_SIGNAL_STAGE1_5C_EVENT_COOLDOWN_HOURS)
        # reconstruct candidate objects
        for d in cooldown_dicts:
            # remove fields not in class init if any, but since it's just dict, we can match constructor
            c_obj = ExternalCatalystReplayCandidate(
                symbol_event_id=d["symbol_event_id"],
                event_type=d["event_type"],
                signed_mode=d["signed_mode"],
                signed_direction=d["signed_direction"],
                symbol=d["symbol"],
                event_time_ms=d["event_time_ms"],
                available_at_ms=d["available_at_ms"],
                entry_delay_hours=d["entry_delay_hours"],
                entry_candidate_time_ms=d["entry_candidate_time_ms"],
                entry_bar_start_ms=d["entry_bar_start_ms"],
                entry_price=d["entry_price"],
                price_history_coverage_verified=d["price_history_coverage_verified"],
                market_pair_existence_verified=d["market_pair_existence_verified"],
                liquidity_proxy_verified=d["liquidity_proxy_verified"],
                close_price_replay_only=d["close_price_replay_only"],
                execution_feasibility_unknown=d["execution_feasibility_unknown"],
                replay_allowed=d["replay_allowed"],
                paper_trading_allowed=d["paper_trading_allowed"],
                live_trading_allowed=d["live_trading_allowed"],
                short_execution_intent_allowed=d["short_execution_intent_allowed"],
                execution_engine_allowed=d["execution_engine_allowed"],
            )
            cooldown_candidates.append(c_obj)
            if delay == primary_delay:
                all_candidates.append(c_obj)

    # 6. Replay candidates
    windows = base.EXTERNAL_SIGNAL_STAGE1_5C_FORWARD_WINDOWS_HOURS
    costs = base.EXTERNAL_SIGNAL_STAGE1_5C_COST_SCENARIOS_BPS
    replay_results = replay_candidates(cooldown_candidates, price_index, windows, costs)

    # 7. Write candidate and results outputs
    # Ensure parent dir exists
    Path(args.output_candidates_jsonl).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_candidates_jsonl, "w", encoding="utf-8") as f:
        for c in cooldown_candidates:
            f.write(json.dumps(c.__dict__) + "\n")

    with open(args.output_results_jsonl, "w", encoding="utf-8") as f:
        for r in replay_results:
            f.write(json.dumps(r.__dict__) + "\n")

    # 8. Check baseline trials limit override
    baseline_trials_override_used = False
    research_result_valid = True
    if args.random_baseline_trials < base.EXTERNAL_SIGNAL_STAGE1_5C_RANDOM_BASELINE_TRIALS:
        baseline_trials_override_used = True
        research_result_valid = False

    # 9. Compute baselines (on primary delay and G2 price coverage only candidates)
    # Filter candidates for baseline generation
    baseline_candidates = [
        c for c in cooldown_candidates
        if c.entry_delay_hours == primary_delay and c.replay_allowed
    ]

    # Matched random baseline
    random_baseline_medians = []
    random_baseline_all_returns = []
    if baseline_candidates:
        trial_event_lists = sample_symbol_hour_event_type_matched_random_baseline(
            [c.__dict__ for c in baseline_candidates],
            price_index,
            trials=args.random_baseline_trials,
            random_seed=base.EXTERNAL_SIGNAL_STAGE1_5C_RANDOM_BASELINE_SEED,
        )

        for trial in trial_event_lists:
            trial_candidate_objs = []
            for ev in trial:
                candidate = _make_baseline_candidate_from_event(
                    ev,
                    price_index,
                    entry_delay_hours=ev["entry_delay_hours"],
                    signed_mode="random_baseline",
                )
                if candidate is not None:
                    trial_candidate_objs.append(candidate)
            # Replay this trial
            trial_results = replay_candidates(
                trial_candidate_objs, price_index,
                forward_windows_hours=(base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_FORWARD_WINDOW_HOURS,),
                cost_scenarios_bps=(base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_COST_BPS,),
            )
            trial_net_returns = [r.net_return_bps for r in trial_results]
            if trial_net_returns:
                random_baseline_medians.append(sum(trial_net_returns) / len(trial_net_returns))
                random_baseline_all_returns.extend(trial_net_returns)

    random_baseline_median = (
        sum(random_baseline_medians) / len(random_baseline_medians)
        if random_baseline_medians else 0.0
    )
    random_baseline_left_tail = (
        percentiles(random_baseline_all_returns, base.EXTERNAL_SIGNAL_STAGE1_5C_LEFT_TAIL_PERCENTILE)
        if random_baseline_all_returns else 0.0
    )

    # Price move baseline
    price_move_baseline_returns = []
    if baseline_candidates:
        # Generate price move triggers
        # Gather all excluded times per symbol
        excluded_times = {}
        for c in baseline_candidates:
            if c.symbol not in excluded_times:
                excluded_times[c.symbol] = []
            excluded_times[c.symbol].append(c.event_time_ms)

        all_pm_events = []
        for sym, times in excluded_times.items():
            # Generate for long direction (1) and short direction (-1)
            for s_dir in [1, -1]:
                pm_evs = compute_price_move_baseline_events(
                    price_index=price_index,
                    symbol=sym,
                    signed_direction=s_dir,
                    threshold_bps=base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_MOVE_BASELINE_1H_RETURN_BPS,
                    excluded_event_times_ms=times,
                    cooldown_hours=base.EXTERNAL_SIGNAL_STAGE1_5C_EVENT_COOLDOWN_HOURS,
                )
                all_pm_events.extend(pm_evs)

        pm_candidate_objs = []
        for ev in all_pm_events:
            candidate = _make_baseline_candidate_from_event(
                ev,
                price_index,
                entry_delay_hours=primary_delay,
                signed_mode="price_move_baseline",
            )
            if candidate is not None:
                pm_candidate_objs.append(candidate)
        pm_results = replay_candidates(
            pm_candidate_objs, price_index,
            forward_windows_hours=(base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_FORWARD_WINDOW_HOURS,),
            cost_scenarios_bps=(base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_COST_BPS,),
        )
        price_move_baseline_returns = [r.net_return_bps for r in pm_results]

    price_baseline_median = (
        percentiles(price_move_baseline_returns, 50)
        if price_move_baseline_returns else 0.0
    )

    # 10. Group results and construct Cell Summaries
    # Cell keys: (event_type, signed_mode, entry_delay_hours, filter_group)
    cell_groups = {}
    for r in replay_results:
        # Find the candidate matching this result to determine filter group status
        # Since candidate properties define filter groups:
        # G1: all candidates
        # G2: candidate.replay_allowed == True
        # G3: candidate.liquidity_proxy_verified == True
        # Let's map this result to the filter groups it belongs to:
        matching_cand = None
        for c in cooldown_candidates:
            if (
                c.symbol_event_id == r.symbol_event_id
                and c.signed_mode == r.signed_mode
                and c.entry_delay_hours == r.entry_delay_hours
            ):
                matching_cand = c
                break

        if not matching_cand:
            continue

        groups_to_add = ["G1_source_event_after_first_hour_delay"]
        if matching_cand.replay_allowed:
            groups_to_add.append("G2_price_coverage_only")
        if matching_cand.liquidity_proxy_verified:
            groups_to_add.append("G3_price_coverage_plus_liquidity_proxy")

        for fg in groups_to_add:
            key = f"{r.event_type}|{r.signed_mode}|{r.entry_delay_hours}h|{fg}"
            if key not in cell_groups:
                cell_groups[key] = []
            cell_groups[key].append(r)

    cell_summaries = {}
    for key, group_results in cell_groups.items():
        parts = key.split("|")
        parts[0]
        parts[1]
        int(parts[2].replace("h", ""))
        fg = parts[3]

        # Calculate metrics for this cell
        # Filter for primary window (4h) and cost (50bps) to calculate event counts and returns
        primary_results = [
            res for res in group_results
            if res.forward_window_hours == base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_FORWARD_WINDOW_HOURS
            and res.cost_bps == base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_COST_BPS
        ]

        if not primary_results:
            continue

        cell_event_count = len(primary_results)
        len(set(
            datetime.fromtimestamp(res.entry_price, tz=timezone.utc).strftime("%Y-%m-%d") # Use entry_price dummy or mock time?
            for res in primary_results
        ))
        # Wait, datetime from entry_price is nonsense. Let's find the event_time_ms of the matching candidate to get date.
        event_times = []
        cell_symbols = set()
        for res in primary_results:
            cell_symbols.add(res.symbol)
            # Find candidate
            for c in cooldown_candidates:
                if (
                    c.symbol_event_id == res.symbol_event_id
                    and c.signed_mode == res.signed_mode
                    and c.entry_delay_hours == res.entry_delay_hours
                ):
                    event_times.append(c.event_time_ms)
                    break

        cell_event_days = len(set(
            datetime.fromtimestamp(t / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
            for t in event_times
        ))
        cell_symbols_with_events = len(cell_symbols)

        # Net returns
        net_returns_4h = [res.net_return_bps for res in primary_results]
        cell_median = percentiles(net_returns_4h, 50) if net_returns_4h else 0.0
        cell_left_tail = percentiles(net_returns_4h, base.EXTERNAL_SIGNAL_STAGE1_5C_LEFT_TAIL_PERCENTILE) if net_returns_4h else 0.0

        # Concentration metrics
        conc_metrics = compute_concentration_metrics(
            [
                {
                    "symbol": res.symbol,
                    "event_time_ms": next((c.event_time_ms for c in cooldown_candidates if c.symbol_event_id == res.symbol_event_id), 0),
                }
                for res in primary_results
            ]
        )

        # Top 5 positive events gross profit share
        gross_returns = [res.signed_gross_return_bps for res in primary_results]
        positive_gross = [g for g in gross_returns if g > 0]
        positive_gross.sort(reverse=True)
        top5_profit_share = 0.0
        if positive_gross:
            sum_top5 = sum(positive_gross[:5])
            sum_all = sum(positive_gross)
            top5_profit_share = sum_top5 / sum_all if sum_all > 0 else 0.0

        # Cell dict
        cell_dict = {
            "fixture_run": False,
            "research_result_valid": research_result_valid,
            "event_count": cell_event_count,
            "event_days": cell_event_days,
            "symbols_with_events": cell_symbols_with_events,
            "primary_event_type_events": cell_event_count, # Since cell is event_type specific
            "median_net_return_after_50bps_4h": cell_median,
            "baseline_excess_net_bps_4h": cell_median - random_baseline_median,
            "price_baseline_excess_net_bps_4h": cell_median - price_baseline_median,
            "left_tail_p05_after_50bps_4h": cell_left_tail,
            "random_baseline_left_tail_p05_after_50bps_4h": random_baseline_left_tail,
            "top_5_positive_events_gross_profit_share": top5_profit_share,
            "max_single_day_event_share": conc_metrics["max_single_day_event_share"],
            "max_single_symbol_event_share": conc_metrics["max_single_symbol_event_share"],
            "baseline_sampling_insufficient": False,
            "random_baseline_trials": args.random_baseline_trials,
        }

        # Run decision
        decided_cell = decide_stage1_5c_replay_summary(cell_dict)
        cell_summaries[key] = decided_cell

    # 11. Futures launch density counts
    futures_launch_density = {
        "raw_symbol_event_count": sum(1 for ev in events if ev["event_type"] == "futures_contract_launch"),
        "signed_mode_count": {
            "futures_launch_long_attention_diagnostic": sum(
                1 for c in cooldown_candidates
                if c.event_type == "futures_contract_launch"
                and c.signed_mode == "futures_launch_long_attention_diagnostic"
                and c.entry_delay_hours == primary_delay
            ),
            "futures_launch_short_access_diagnostic": sum(
                1 for c in cooldown_candidates
                if c.event_type == "futures_contract_launch"
                and c.signed_mode == "futures_launch_short_access_diagnostic"
                and c.entry_delay_hours == primary_delay
            ),
        },
        "do_not_sum_signed_modes_for_density_gate": True,
    }

    # Attrition funnel
    coverage_attrition_funnel = {
        "stage1_5b_symbol_events": total_loaded,
        "allowed_event_type_events": total_loaded,
        "market_pair_existence_verified_count": existence_count,
        "price_history_coverage_pass_count": coverage_pass_count,
        "liquidity_proxy_pass_count": liquidity_pass_count,
        "candidate_count_after_cooldown": len(all_candidates),
        "replay_result_primary_rows": len([
            r for r in replay_results
            if r.entry_delay_hours == primary_delay
            and r.forward_window_hours == base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_FORWARD_WINDOW_HOURS
            and r.cost_bps == base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_COST_BPS
        ]),
        "coverage_reject_reason_counts": reject_reason_counts,
    }

    # Top-level aggregate status
    top_level_summary = {
        "fixture_run": False,
        "research_result_valid": research_result_valid,
        "baseline_trials_override_used": baseline_trials_override_used,
        "random_baseline_trials": args.random_baseline_trials,
        "random_baseline_median_net_bps_after_50bps_4h": random_baseline_median,
        "price_baseline_median_net_bps_after_50bps_4h": price_baseline_median,
        "random_baseline_left_tail_p05_after_50bps_4h": random_baseline_left_tail,
        "futures_launch_density": futures_launch_density,
        "coverage_attrition_funnel": coverage_attrition_funnel,
        "cell_summaries": cell_summaries,
    }

    decided_summary = decide_stage1_5c_replay_summary(top_level_summary)

    # 12. Write final summary JSON
    with open(args.output_summary, "w", encoding="utf-8") as f:
        json.dump(decided_summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
