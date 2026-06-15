"""
src/research/external_signal_shadow/stage1_4a_summary.py
"""

from configs.base import (
    EXTERNAL_SIGNAL_STAGE1_4_BAR_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_FUNDING_FIELD_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_FUNDING_SETTLEMENT_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN,
    EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_FIELD_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_TIME_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_MIN_USABLE_SYMBOLS,
    EXTERNAL_SIGNAL_STAGE1_4_OI_FIELD_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_OI_TIME_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_PREVIEW_MIN_COMPOSITE_OVERLAP_DAYS,
    EXTERNAL_SIGNAL_STAGE1_4_PREVIEW_MIN_COMPOSITE_OVERLAP_WINDOWS,
)


def evaluate_feasibility_summary(
    symbol_audits: dict[str, dict],
    preview_counts: dict,
    global_metadata: dict,
) -> dict:
    """
    Evaluates the final data feasibility outcome across 18 gates.
    """
    # 1. Safety and scope violation check
    safety_violation = global_metadata.get("safety_violation", False)
    # Master switch check: if live_trading_allowed is set to True in output but it's not validated, it's a safety violation
    if global_metadata.get("live_trading_allowed", False):
        safety_violation = True

    if safety_violation:
        return {
            "outcome": "stage1_4_data_unavailable",
            "primary_blocker": "safety_or_scope_violation",
            "research_result_valid": False,
            "fixture_run": global_metadata.get("fixture_run", False),
            "stage1_4b_candidate_replay_allowed": False,
            "composite_replay_allowed": False,
            "live_trading_allowed": False,
            "feasible_symbol_count": 0,
            "preview_metrics": preview_counts,
        }

    # 2. Fixture run check
    fixture_run = global_metadata.get("fixture_run", False)
    if fixture_run:
        return {
            "outcome": "stage1_4_data_degraded",
            "primary_blocker": "fixture_smoke_only",
            "research_result_valid": False,
            "fixture_run": True,
            "stage1_4b_candidate_replay_allowed": False,
            "composite_replay_allowed": False,
            "live_trading_allowed": False,
            "feasible_symbol_count": 0,
            "preview_metrics": preview_counts,
        }

    # 3. Usable symbols check (must have audits for at least some symbols)
    symbols_with_data = []
    for sym, audits in symbol_audits.items():
        # A symbol is usable if it has non-empty fields in its audits
        has_some_data = False
        for k in ("funding", "oi", "liquidation", "price"):
            audit = audits.get(k, {})
            record_count_keys = (
                "funding_record_count",
                "oi_record_count",
                "liquidation_nonzero_window_count",
                "price_bar_count",
            )
            for rkey in record_count_keys:
                if audit.get(rkey, 0) > 0:
                    has_some_data = True
                    break
        if has_some_data:
            symbols_with_data.append(sym)

    if len(symbols_with_data) < EXTERNAL_SIGNAL_STAGE1_4_MIN_USABLE_SYMBOLS:
        return {
            "outcome": "stage1_4_data_unavailable",
            "primary_blocker": "insufficient_usable_symbols",
            "research_result_valid": True,
            "fixture_run": False,
            "stage1_4b_candidate_replay_allowed": False,
            "composite_replay_allowed": False,
            "live_trading_allowed": False,
            "feasible_symbol_count": 0,
            "preview_metrics": preview_counts,
        }

    # Evaluate each symbol's feasibility individually
    feasible_symbols = []
    symbol_blockers = {}

    for sym in symbols_with_data:
        audits = symbol_audits[sym]
        funding = audits.get("funding", {})
        oi = audits.get("oi", {})
        liquidation = audits.get("liquidation", {})
        price = audits.get("price", {})

        blocker = None

        # Gate 4: notional conversion quality
        notional_qual = liquidation.get("notional_conversion_quality")
        if notional_qual != "verified_by_sample":
            blocker = "notional_conversion_unverified"

        # Gate 5: CM proxy without explicit full replay acceptance
        elif liquidation.get("cm_to_um_proxy_used") is True and not liquidation.get(
            "liquidation_proxy_accepted_for_full_replay", False
        ):
            blocker = "cm_proxy_unaccepted"

        # Gate 6: OI history >= 90 days
        elif oi.get("oi_history_days", 0.0) < EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN:
            blocker = "oi_history_insufficient"

        # Gate 7: OI time coverage >= 0.90
        elif oi.get("oi_time_coverage_ratio", 0.0) < EXTERNAL_SIGNAL_STAGE1_4_OI_TIME_COVERAGE_MIN_RATIO:
            blocker = "oi_time_coverage_insufficient"

        # Gate 8: OI field coverage >= 0.90
        elif oi.get("oi_field_coverage_ratio", 0.0) < EXTERNAL_SIGNAL_STAGE1_4_OI_FIELD_COVERAGE_MIN_RATIO:
            blocker = "oi_field_coverage_insufficient"

        # Gate 9: funding history >= 90 days
        elif funding.get("funding_history_days", 0.0) < EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN:
            blocker = "funding_history_insufficient"

        # Gate 10: funding settlement coverage >= 0.95
        elif (
            funding.get("funding_settlement_coverage_ratio", 0.0)
            < EXTERNAL_SIGNAL_STAGE1_4_FUNDING_SETTLEMENT_COVERAGE_MIN_RATIO
        ):
            blocker = "funding_settlement_coverage_insufficient"

        # Gate 11: funding field coverage >= 0.95
        elif (
            funding.get("funding_field_coverage_ratio", 0.0)
            < EXTERNAL_SIGNAL_STAGE1_4_FUNDING_FIELD_COVERAGE_MIN_RATIO
        ):
            blocker = "funding_field_coverage_insufficient"

        # Gate 12: liquidation history >= 90 days
        elif liquidation.get("liquidation_history_days", 0.0) < EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN:
            blocker = "liquidation_history_insufficient"

        # Gate 13: liquidation time coverage >= 0.90
        elif (
            liquidation.get("liquidation_time_coverage_ratio", 0.0)
            < EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_TIME_COVERAGE_MIN_RATIO
        ):
            blocker = "liquidation_time_coverage_insufficient"

        # Gate 14: liquidation field coverage >= 0.90
        elif (
            liquidation.get("liquidation_field_coverage_ratio", 0.0)
            < EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_FIELD_COVERAGE_MIN_RATIO
        ):
            blocker = "liquidation_field_coverage_insufficient"

        # Gate 15: price history >= 90 days
        elif price.get("price_history_days", 0.0) < EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN:
            blocker = "price_history_insufficient"

        # Gate 16: price coverage >= 0.95
        elif price.get("price_bar_coverage_ratio", 0.0) < EXTERNAL_SIGNAL_STAGE1_4_BAR_COVERAGE_MIN_RATIO:
            blocker = "price_coverage_insufficient"

        if blocker is None:
            feasible_symbols.append(sym)
        else:
            symbol_blockers[sym] = blocker

    feasible_symbol_count = len(feasible_symbols)

    # If feasible symbols < 3, it's degraded. Pick the most frequent blocker.
    if feasible_symbol_count < EXTERNAL_SIGNAL_STAGE1_4_MIN_USABLE_SYMBOLS:
        all_blockers = list(symbol_blockers.values())
        primary_blocker = max(set(all_blockers), key=all_blockers.count) if all_blockers else "unknown"
        return {
            "outcome": "stage1_4_data_degraded",
            "primary_blocker": primary_blocker,
            "research_result_valid": True,
            "fixture_run": False,
            "stage1_4b_candidate_replay_allowed": False,
            "composite_replay_allowed": False,
            "live_trading_allowed": False,
            "feasible_symbol_count": feasible_symbol_count,
            "preview_metrics": preview_counts,
        }

    # 17-18. Preview density check
    overlap_windows = preview_counts.get("composite_overlap_window_count", 0)
    overlap_days = preview_counts.get("composite_overlap_event_days", 0)

    if (
        overlap_windows < EXTERNAL_SIGNAL_STAGE1_4_PREVIEW_MIN_COMPOSITE_OVERLAP_WINDOWS
        or overlap_days < EXTERNAL_SIGNAL_STAGE1_4_PREVIEW_MIN_COMPOSITE_OVERLAP_DAYS
    ):
        return {
            "outcome": "stage1_4_data_degraded",
            "primary_blocker": "insufficient_preview_density",
            "research_result_valid": True,
            "fixture_run": False,
            "stage1_4b_candidate_replay_allowed": False,
            "composite_replay_allowed": False,
            "live_trading_allowed": False,
            "feasible_symbol_count": feasible_symbol_count,
            "preview_metrics": preview_counts,
        }

    # All checks passed!
    return {
        "outcome": "stage1_4_data_feasible",
        "primary_blocker": None,
        "research_result_valid": True,
        "fixture_run": False,
        "stage1_4b_candidate_replay_allowed": True,
        "composite_replay_allowed": True,
        "live_trading_allowed": False,
        "feasible_symbol_count": feasible_symbol_count,
        "preview_metrics": preview_counts,
    }
