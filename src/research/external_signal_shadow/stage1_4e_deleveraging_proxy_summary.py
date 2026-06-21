from configs import base
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    DECISION_FAILED,
    DECISION_INCONCLUSIVE,
    DECISION_SURVIVES,
    SECONDARY_NONE,
    SECONDARY_PROMISING_SPARSE,
)


def decide_stage1_4e_summary(
    *,
    event_count: int,
    event_days: int,
    symbols_with_events: int,
    candidate_median_bps: float,
    random_baseline_median_bps: float,
    price_baseline_median_bps: float,
    candidate_left_tail_bps: float,
    random_baseline_left_tail_bps: float,
    top5_positive_gross_profit_share: float,
    max_single_day_event_share: float,
    max_single_symbol_event_share: float,
    data_supported: bool,
) -> tuple[str, str]:
    if not data_supported:
        return DECISION_INCONCLUSIVE, SECONDARY_NONE

    # Baseline performance check: must outperform both random baseline and price-only baseline
    outperformed_baselines = (candidate_median_bps > random_baseline_median_bps) and (candidate_median_bps > price_baseline_median_bps)
    left_tail_ok = candidate_left_tail_bps >= random_baseline_left_tail_bps

    # Pass gates (density criteria)
    min_pass_count = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_PASS_EVENT_COUNT
    min_pass_days = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_PASS_EVENT_DAYS
    min_symbols = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_SYMBOLS_WITH_EVENTS
    max_day_share = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MAX_SINGLE_DAY_EVENT_SHARE
    max_symbol_share = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MAX_SINGLE_SYMBOL_EVENT_SHARE
    max_top5_share = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MAX_TOP5_POSITIVE_GROSS_PROFIT_SHARE

    # Sparse gates (density criteria)
    min_sparse_count = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_SPARSE_EVENT_COUNT
    min_sparse_days = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_SPARSE_EVENT_DAYS

    concentration_ok = (
        top5_positive_gross_profit_share <= max_top5_share
        and max_single_day_event_share <= max_day_share
        and max_single_symbol_event_share <= max_symbol_share
    )
    coverage_ok = symbols_with_events >= min_symbols

    if outperformed_baselines and left_tail_ok:
        if (
            event_count >= min_pass_count
            and event_days >= min_pass_days
            and coverage_ok
            and concentration_ok
        ):
            return DECISION_SURVIVES, SECONDARY_NONE
        elif (
            event_count >= min_sparse_count
            and event_days >= min_sparse_days
            and coverage_ok
            and concentration_ok
        ):
            return DECISION_INCONCLUSIVE, SECONDARY_PROMISING_SPARSE
        else:
            # Not enough events to be even promising
            return DECISION_INCONCLUSIVE, SECONDARY_NONE
    else:
        # Weak performance
        return DECISION_FAILED, SECONDARY_NONE

def build_candidate_summary(
    *,
    candidate_name: str,
    events_detected: int,
    distinct_days: int,
    replayed_median_bps_1h: float,
    replayed_median_bps_4h: float,
    replayed_median_bps_12h: float,
    random_baseline_4h_median_bps: float,
    price_baseline_4h_median_bps: float,
    symbols_with_events: int,
    candidate_left_tail_bps: float,
    random_baseline_left_tail_bps: float,
    top5_positive_gross_profit_share: float,
    max_single_day_event_share: float,
    max_single_symbol_event_share: float,
    source_quality: dict,
    random_baseline_trials: int,
    baseline_sampling_failure_count: int,
    funding_context_summary: dict | None = None,
    fixture_run: bool = False,
    research_result_valid: bool = True,
) -> dict:
    # Determine support for this candidate name overall
    data_supported = source_quality.get("candidate_window_supported_overall", {}).get(candidate_name, False)

    decision, secondary = decide_stage1_4e_summary(
        event_count=events_detected,
        event_days=distinct_days,
        symbols_with_events=symbols_with_events,
        candidate_median_bps=replayed_median_bps_4h,
        random_baseline_median_bps=random_baseline_4h_median_bps,
        price_baseline_median_bps=price_baseline_4h_median_bps,
        candidate_left_tail_bps=candidate_left_tail_bps,
        random_baseline_left_tail_bps=random_baseline_left_tail_bps,
        top5_positive_gross_profit_share=top5_positive_gross_profit_share,
        max_single_day_event_share=max_single_day_event_share,
        max_single_symbol_event_share=max_single_symbol_event_share,
        data_supported=data_supported,
    )

    # 2nd review suggestion: output source quality metrics in the summary
    source_quality_summary = {
        "oi_source_quality": source_quality.get("oi_source_quality", "unknown"),
        "price_source_quality": source_quality.get("price_source_quality", "unknown"),
        "oi_data_granularity_minutes": source_quality.get("oi_data_granularity_minutes", 0.0),
        "price_data_granularity_minutes": source_quality.get("price_data_granularity_minutes", 0.0),
        "oi_history_days": source_quality.get("oi_history_days", 0.0),
        "price_history_days": source_quality.get("price_history_days", 0.0),
        "candidate_window_supported": data_supported,
        "research_result_valid": research_result_valid
    }

    return {
        "candidate_name": candidate_name,
        "decision": decision,
        "secondary_status": secondary,
        "events_detected_count": events_detected,
        "distinct_days_count": distinct_days,
        "symbols_with_events": symbols_with_events,
        "candidate_left_tail_bps_after_50bps": candidate_left_tail_bps,
        "random_baseline_left_tail_bps_after_50bps": random_baseline_left_tail_bps,
        "top_5_positive_events_gross_profit_share": top5_positive_gross_profit_share,
        "max_single_day_event_share": max_single_day_event_share,
        "max_single_symbol_event_share": max_single_symbol_event_share,

        # Returns
        "replayed_median_bps_1h": replayed_median_bps_1h,
        "replayed_median_bps_4h": replayed_median_bps_4h,
        "replayed_median_bps_12h": replayed_median_bps_12h,

        # Baselines
        "random_baseline_trials": random_baseline_trials,
        "random_baseline_4h_median_bps": random_baseline_4h_median_bps,
        "baseline_sampling_failure_count": baseline_sampling_failure_count,
        "price_baseline_4h_median_bps": price_baseline_4h_median_bps,

        # Safety & Scope Flags
        "deleveraging_proxy_only": True,
        "liquidation_used": False,
        "force_order_used": False,
        "vendor_data_used": False,
        "liquidation_claim_allowed": False,
        "full_composite_claim_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "not_b_lite_restart": True,
        "previous_b_lite_crowding_only_branch_stopped": True,
        "stage1_5_allowed_only_as_filter": True,
        "fixture_run": fixture_run,
        "research_result_valid": research_result_valid,

        # Source Quality Context
        "source_quality_summary": source_quality_summary,
        "funding_context_summary": funding_context_summary or {
            "funding_context_used": False,
            "funding_rows_loaded": 0,
        },
    }
