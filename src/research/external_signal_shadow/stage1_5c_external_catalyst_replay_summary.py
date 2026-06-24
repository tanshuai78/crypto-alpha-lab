from datetime import datetime, timezone

from configs import base


def compute_concentration_metrics(
    rows: list[dict],
    primary_forward_window_hours: int = 4,
    primary_cost_bps: int = 50
) -> dict:
    # Filter rows to keep only primary window/cost if present
    filtered = []
    for r in rows:
        if "forward_window_hours" in r and r["forward_window_hours"] != primary_forward_window_hours:
            continue
        if "cost_bps" in r and r["cost_bps"] != primary_cost_bps:
            continue
        filtered.append(r)

    total_count = len(filtered)
    if total_count == 0:
        return {
            "event_count": 0,
            "max_single_symbol_event_share": 0.0,
            "max_single_day_event_share": 0.0,
        }

    # Single symbol counts
    symbol_counts = {}
    for ev in filtered:
        sym = ev["symbol"]
        symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
    max_symbol_count = max(symbol_counts.values())

    # Single day counts
    day_counts = {}
    for ev in filtered:
        t_ms = ev["event_time_ms"]
        dt = datetime.fromtimestamp(t_ms / 1000.0, tz=timezone.utc)
        day_str = dt.strftime("%Y-%m-%d")
        day_counts[day_str] = day_counts.get(day_str, 0) + 1
    max_day_count = max(day_counts.values())

    return {
        "event_count": total_count,
        "max_single_symbol_event_share": max_symbol_count / total_count,
        "max_single_day_event_share": max_day_count / total_count,
    }


def decide_stage1_5c_replay_summary(summary: dict) -> dict:
    res = dict(summary)
    # Ensure safety overrides
    res["paper_trading_allowed"] = False
    res["live_trading_allowed"] = False
    res["execution_engine_allowed"] = False
    res["alpha_interpretation_allowed"] = False

    research_valid = res.get("research_result_valid", True)
    fixture_run = res.get("fixture_run", False)

    # If it is a cell summary evaluation (individual cell level)
    if "cell_summaries" not in res:
        # Evaluate as a single cell summary
        blockers = []
        if not research_valid:
            blockers.append("research_result_invalid")
        if fixture_run:
            blockers.append("fixture_run_not_allowed")

        trials = res.get("random_baseline_trials", 500)
        if trials < 500:
            blockers.append("insufficient_baseline_trials")
        if res.get("baseline_sampling_insufficient", False):
            blockers.append("baseline_sampling_insufficient")

        # Density checks
        density_passed = True
        event_count = res.get("event_count", 0)
        if event_count < base.EXTERNAL_SIGNAL_STAGE1_5C_MIN_EVENT_COUNT:
            blockers.append("insufficient_event_count")
            density_passed = False

        event_days = res.get("event_days", 0)
        if event_days < base.EXTERNAL_SIGNAL_STAGE1_5C_MIN_EVENT_DAYS:
            blockers.append("insufficient_event_days")
            density_passed = False

        symbols = res.get("symbols_with_events", 0)
        if symbols < base.EXTERNAL_SIGNAL_STAGE1_5C_MIN_SYMBOLS_WITH_EVENTS:
            blockers.append("insufficient_symbols_with_events")
            density_passed = False

        # Return & baseline checks
        median_ret = res.get("median_net_return_after_50bps_4h", 0.0)
        if median_ret <= 0:
            blockers.append("median_net_return_after_50bps_not_positive")

        baseline_excess = res.get("baseline_excess_net_bps_4h", 0.0)
        if baseline_excess <= 0:
            blockers.append("baseline_excess_net_bps_not_positive")

        price_baseline_excess = res.get("price_baseline_excess_net_bps_4h", 0.0)
        if price_baseline_excess <= 0:
            blockers.append("price_baseline_excess_net_bps_not_positive")

        # Left tail check
        left_tail = res.get("left_tail_p05_after_50bps_4h", 0.0)
        rand_left_tail = res.get("random_baseline_left_tail_p05_after_50bps_4h", 0.0)
        if left_tail < rand_left_tail:
            blockers.append("left_tail_drawdown_exceeds_random_baseline")

        # Concentration checks
        top5_share = res.get("top_5_positive_events_gross_profit_share", 0.0)
        if top5_share > base.EXTERNAL_SIGNAL_STAGE1_5C_MAX_TOP5_POSITIVE_GROSS_PROFIT_SHARE:
            blockers.append("top5_profit_share_exceeds_limit")

        max_day_share = res.get("max_single_day_event_share", 0.0)
        if max_day_share > base.EXTERNAL_SIGNAL_STAGE1_5C_MAX_SINGLE_DAY_EVENT_SHARE:
            blockers.append("max_single_day_event_share_exceeds_limit")

        max_sym_share = res.get("max_single_symbol_event_share", 0.0)
        if max_sym_share > base.EXTERNAL_SIGNAL_STAGE1_5C_MAX_SINGLE_SYMBOL_EVENT_SHARE:
            blockers.append("max_single_symbol_event_share_exceeds_limit")

        res["blockers"] = blockers
        if not research_valid:
            res["cell_decision"] = "stage1_5c_cell_invalid"
        elif blockers:
            if not density_passed:
                res["cell_decision"] = "stage1_5c_cell_sparse_inconclusive"
            else:
                res["cell_decision"] = "stage1_5c_cell_failed"
        else:
            res["cell_decision"] = "stage1_5c_cell_promising"

        return res

    # Otherwise, it is a top-level summary JSON containing multiple cells
    coverage_funnel = res.get("coverage_attrition_funnel") or {}
    coverage_invalid = False
    coverage_blockers = []
    if coverage_funnel:
        if coverage_funnel.get("allowed_event_type_events", 0) > 0:
            if coverage_funnel.get("price_history_coverage_pass_count", 0) <= 0:
                coverage_invalid = True
                coverage_blockers.append("no_price_history_coverage")
            if coverage_funnel.get("replay_result_primary_rows", 0) <= 0:
                coverage_invalid = True
                coverage_blockers.append("no_replay_primary_rows")
            if coverage_funnel.get("market_pair_existence_verified_count", 0) <= 0:
                coverage_blockers.append("no_market_pair_overlap_with_price_archive")
    if coverage_invalid:
        res["research_result_valid"] = False
        research_valid = False

    cells = res.get("cell_summaries", {})
    promising_cells = []
    for k, v in cells.items():
        # Evaluate cell
        cell_res = decide_stage1_5c_replay_summary(v)
        cells[k] = cell_res
        if cell_res.get("cell_decision") == "stage1_5c_cell_promising":
            promising_cells.append(k)

    res["promising_cells"] = promising_cells

    top_blockers = list(coverage_blockers)
    if res.get("baseline_trials_override_used", False) and not coverage_invalid:
        res["top_level_decision"] = "stage1_5c_replay_completed"
    elif not research_valid:
        res["top_level_decision"] = "stage1_5c_replay_invalid"
    else:
        res["top_level_decision"] = "stage1_5c_replay_completed"

    if not promising_cells:
        top_blockers.append("no_cell_level_promising_result")

    res["blockers"] = top_blockers
    return res
