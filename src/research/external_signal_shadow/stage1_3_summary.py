from __future__ import annotations

from configs import base

PRIMARY_CANDIDATES = {
    "volume_spike_1h",
    "relative_strength_vs_btc",
    "volume_confirmed_relative_strength",
}


def decide_candidate(candidate: dict) -> dict:
    result = dict(candidate)
    blocker = None
    decision = "candidate_promising_for_live_smoke"
    live_smoke_allowed = True

    if candidate.get("event_count", 0) < base.EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_COUNT:
        decision = "candidate_data_insufficient"
        blocker = "event_count_below_min"
    elif candidate.get("symbols_with_events", 0) < base.EXTERNAL_SIGNAL_STAGE1_3_MIN_SYMBOLS_WITH_EVENTS:
        decision = "candidate_data_insufficient"
        blocker = "symbols_with_events_below_min"
    elif candidate.get("event_days", 0) < base.EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_DAYS:
        decision = "candidate_data_insufficient"
        blocker = "event_days_below_min"
    elif candidate.get("max_single_symbol_event_share", 1.0) > base.EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_SYMBOL_EVENT_SHARE:
        decision = "candidate_failed"
        blocker = "single_symbol_event_share_high"
    elif candidate.get("max_single_day_event_share", 1.0) > base.EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_DAY_EVENT_SHARE:
        decision = "candidate_failed"
        blocker = "single_day_event_share_high"
    elif candidate.get("top_5_positive_events_gross_profit_share", 1.0) > base.EXTERNAL_SIGNAL_STAGE1_3_MAX_TOP5_POSITIVE_PNL_SHARE:
        decision = "candidate_failed"
        blocker = "top5_positive_pnl_concentration_high"
    elif candidate.get("baseline_excess_net_bps", 0.0) <= 0:
        decision = "candidate_failed"
        blocker = "no_positive_baseline_excess"
    elif candidate.get("median_net_return_after_50bps", 0.0) <= 0:
        decision = "candidate_diagnostic_promising"
        blocker = "median_net_return_not_positive"
        live_smoke_allowed = False

    if decision != "candidate_promising_for_live_smoke":
        live_smoke_allowed = False

    result["candidate_decision"] = decision
    result["primary_blocker"] = blocker
    result["live_smoke_allowed"] = live_smoke_allowed
    return result


def decide_stage1_3_summary(summary: dict) -> dict:
    decided = [decide_candidate(item) for item in summary.get("candidate_results", [])]
    if summary.get("fixture_run") is True:
        return {
            **summary,
            "candidate_results": decided,
            "decision": "stage1_3_fixture_smoke_completed",
            "next_action": "run_real_historical_bars_replay",
            "alpha_interpretation_allowed": False,
            "collector_expansion_allowed": False,
            "live_shadow_required_now": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
        }

    primary = [item for item in decided if item.get("candidate_name") in PRIMARY_CANDIDATES]
    promising = [item for item in primary if item.get("candidate_decision") == "candidate_promising_for_live_smoke"]
    next_action = "proceed_to_24h_live_smoke_design" if promising else "stop_gate_ticker_direction"
    return {
        **summary,
        "candidate_results": decided,
        "decision": "stage1_3_candidate_signal_discovery_completed",
        "next_action": next_action,
        "alpha_interpretation_allowed": False,
        "collector_expansion_allowed": False,
        "live_shadow_required_now": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
    }
