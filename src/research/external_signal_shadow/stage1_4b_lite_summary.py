from configs import base


def compute_concentration_stats(events: list, replay_rows: list[dict]) -> dict:
    if not events:
        return {
            "max_single_symbol_event_share": 0.0,
            "max_single_day_event_share": 0.0,
            "top_5_positive_events_gross_profit_share": 0.0,
            "top_5_abs_pnl_share": 0.0,
        }

    total_events = len(events)

    symbol_counts: dict[str, int] = {}
    day_counts: dict[int, int] = {}

    for e in events:
        symbol = getattr(e, "symbol", None) or e.get("symbol")
        time_ms = getattr(e, "event_time_ms", None) or e.get("event_time_ms")

        if symbol:
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        if time_ms is not None:
            day = int(time_ms) // (24 * 3600 * 1000)
            day_counts[day] = day_counts.get(day, 0) + 1

    max_symbol_share = max(symbol_counts.values()) / total_events if symbol_counts else 0.0
    max_day_share = max(day_counts.values()) / total_events if day_counts else 0.0

    positive_returns = []
    abs_returns = []
    for r in replay_rows:
        ret = float(r.get("terminal_return_4h_net_bps_after_50bps", 0.0))
        if ret > 0:
            positive_returns.append(ret)
        abs_returns.append(abs(ret))

    if positive_returns:
        positive_returns.sort(reverse=True)
        total_pos = sum(positive_returns)
        top_5_pos = sum(positive_returns[:5])
        pos_share = top_5_pos / total_pos if total_pos > 0 else 0.0
    else:
        pos_share = 0.0

    if abs_returns:
        abs_returns.sort(reverse=True)
        total_abs = sum(abs_returns)
        top_5_abs = sum(abs_returns[:5])
        abs_share = top_5_abs / total_abs if total_abs > 0 else 0.0
    else:
        abs_share = 0.0

    return {
        "max_single_symbol_event_share": max_symbol_share,
        "max_single_day_event_share": max_day_share,
        "top_5_positive_events_gross_profit_share": pos_share,
        "top_5_abs_pnl_share": abs_share,
    }


def decide_candidate_family_summary(result: dict) -> dict:
    event_count = int(result.get("event_count", 0))
    event_days = int(result.get("event_days", 0))
    symbols_count = int(result.get("symbols_count", 0))
    max_symbol_share = float(result.get("max_single_symbol_event_share", 0.0))
    max_day_share = float(result.get("max_single_day_event_share", 0.0))
    top5_pos_share = float(result.get("top_5_positive_events_gross_profit_share", 0.0))

    if event_count < base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_COUNT:
        return {
            "decision": "crowding_lite_failed",
            "blocker": "candidate_event_count_below_min",
        }
    if event_days < base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_DAYS:
        return {
            "decision": "crowding_lite_failed",
            "blocker": "candidate_event_days_below_min",
        }
    if symbols_count < base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_SYMBOLS_WITH_EVENTS:
        return {
            "decision": "crowding_lite_failed",
            "blocker": "candidate_symbols_below_min",
        }
    if max_symbol_share > base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_SYMBOL_EVENT_SHARE:
        return {
            "decision": "crowding_lite_failed",
            "blocker": "candidate_symbol_concentration_limit_exceeded",
        }
    if max_day_share > base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_DAY_EVENT_SHARE:
        return {
            "decision": "crowding_lite_failed",
            "blocker": "candidate_day_concentration_limit_exceeded",
        }
    if top5_pos_share > base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_TOP5_POSITIVE_GROSS_PROFIT_SHARE:
        return {
            "decision": "crowding_lite_failed",
            "blocker": "candidate_profit_concentration_limit_exceeded",
        }

    cand_median = float(result.get("median_net_return_bps", 0.0))
    rand_median = float(result.get("random_baseline_median_bps", 0.0))
    price_median = float(result.get("price_move_baseline_median_bps", 0.0))

    if cand_median <= 0:
        return {
            "decision": "crowding_lite_weak",
            "blocker": "median_net_return_not_positive",
        }

    if cand_median <= rand_median:
        return {
            "decision": "crowding_lite_weak",
            "blocker": "no_positive_random_baseline_excess",
        }

    if cand_median <= price_median:
        return {
            "decision": "crowding_lite_weak",
            "blocker": "no_positive_price_baseline_excess",
        }

    return {
        "decision": "crowding_lite_promising",
        "blocker": None,
    }


def decide_stage1_4b_lite_summary(summary: dict) -> dict:
    # Safe boundaries output
    res = {
        "liquidation_used": False,
        "full_derivatives_stress_composite_claim_allowed": False,
        "stage1_4b_full_composite_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "signed_replay_only": True,
        "execution_intent_allowed": False,
        "b_lite_failure_interpretation": "crowding_only_failed_not_full_composite_failed",
        "liquidation_missing_leg_remains_unresolved": True,
        "fixture_run": summary.get("fixture_run", False),
        "research_result_valid": not summary.get("fixture_run", False),
    }

    # Evaluate candidates
    cand_results = summary.get("candidates", {})
    promising_count = 0
    weak_count = 0
    failed_count = 0

    for name, cand in cand_results.items():
        if cand.get("decision") == "crowding_lite_promising":
            promising_count += 1
        elif cand.get("decision") == "crowding_lite_weak":
            weak_count += 1
        elif cand.get("decision") == "crowding_lite_failed":
            failed_count += 1

    # Check safety violations at overall level (from summary stats)
    # E.g. concentration metrics
    symbol_share = float(summary.get("max_single_symbol_event_share", 0.0))
    day_share = float(summary.get("max_single_day_event_share", 0.0))
    gp_share = float(summary.get("top_5_positive_events_gross_profit_share", 0.0))

    safety_blocker = None
    if symbol_share > base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_SYMBOL_EVENT_SHARE:
        safety_blocker = "symbol_concentration_limit_exceeded"
    elif day_share > base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_DAY_EVENT_SHARE:
        safety_blocker = "day_concentration_limit_exceeded"
    elif gp_share > base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_TOP5_POSITIVE_GROSS_PROFIT_SHARE:
        safety_blocker = "profit_concentration_limit_exceeded"

    # Check density gates
    total_events = int(summary.get("total_events", 0))
    total_days = int(summary.get("total_days", 0))
    total_symbols = int(summary.get("total_symbols", 0))

    density_blocker = None
    if total_events < base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_COUNT:
        density_blocker = "total_event_count_below_min"
    elif total_days < base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_DAYS:
        density_blocker = "total_event_days_below_min"
    elif total_symbols < base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_SYMBOLS_WITH_EVENTS:
        density_blocker = "total_symbols_below_min"

    # Overall decision
    if safety_blocker:
        decision = "crowding_lite_failed"
        blocker = safety_blocker
    elif density_blocker:
        decision = "crowding_lite_failed"
        blocker = density_blocker
    elif promising_count > 0:
        decision = "crowding_lite_promising"
        blocker = None
    elif weak_count > 0:
        decision = "crowding_lite_weak"
        blocker = "no_promising_candidates"
    elif failed_count == len(cand_results) and cand_results:
        decision = "crowding_lite_failed"
        blocker = "no_promising_candidates"
    else:
        decision = "crowding_lite_weak"
        blocker = None

    res["decision"] = decision
    res["primary_blocker"] = blocker

    # Next Action Mapping
    if decision == "crowding_lite_promising":
        res["next_action"] = "prepare_stage1_4c_joint_decision_review"
    elif decision == "crowding_lite_weak":
        res["next_action"] = "keep_as_secondary_track_only"
    else:
        res["next_action"] = "stop_crowding_only_branch"

    return res
