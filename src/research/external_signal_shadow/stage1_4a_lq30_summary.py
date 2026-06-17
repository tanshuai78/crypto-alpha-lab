from __future__ import annotations

from typing import Any

import configs.base as base


def build_source_quality_report(
    loader_stats: dict[str, Any],
    parsed_rows: list[dict[str, Any]],
    expected_symbols: set[str],
    parse_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parse_stats = parse_stats or {}
    if not parsed_rows:
        return {
            "raw_row_count": loader_stats.get("raw_line_count", 0),
            "raw_history_days": 0.0,
            "raw_recent_event_count_24h": 0,
            "duplicate_event_count": loader_stats.get("duplicate_event_count", 0),
            "invalid_json_line_count": loader_stats.get("invalid_json_line_count", 0),
            "invalid_json_line_ratio": loader_stats.get("invalid_json_line_ratio", 0.0),
            "missing_timestamp_count": parse_stats.get("missing_timestamp_count", 0),
            "expected_symbol_coverage": len(expected_symbols),
            "actual_symbol_coverage": 0,
            "unknown_schema_count": parse_stats.get("unknown_schema_count", 0),
            "missing_required_field_count": parse_stats.get("missing_required_field_count", 0),
            "parse_error_count": parse_stats.get("parse_error_count", 0),
            "rotation_fragment_count": max(loader_stats.get("resolved_path_count", 0) - 1, 0),
            "collector_gap_verifiable": False,
            "archive_gap_observations": "event_sparse_stream_cannot_prove_uptime",
        }

    timestamps = [int(r["timestamp_ms"]) for r in parsed_rows]
    min_ts, max_ts = min(timestamps), max(timestamps)
    raw_history_days = round((max_ts - min_ts) / (24 * 60 * 60 * 1000), 2)

    # Recent 24h count
    cutoff = max_ts - 24 * 60 * 60 * 1000
    recent_count = sum(1 for ts in timestamps if ts >= cutoff)

    actual_symbols = {r["symbol"] for r in parsed_rows}

    return {
        "raw_row_count": loader_stats.get("raw_line_count", 0),
        "raw_history_days": raw_history_days,
        "raw_recent_event_count_24h": recent_count,
        "duplicate_event_count": loader_stats.get("duplicate_event_count", 0),
        "invalid_json_line_count": loader_stats.get("invalid_json_line_count", 0),
        "invalid_json_line_ratio": loader_stats.get("invalid_json_line_ratio", 0.0),
        "missing_timestamp_count": parse_stats.get("missing_timestamp_count", 0),
        "expected_symbol_coverage": len(expected_symbols),
        "actual_symbol_coverage": len(actual_symbols),
        "unknown_schema_count": parse_stats.get("unknown_schema_count", 0),
        "missing_required_field_count": parse_stats.get("missing_required_field_count", 0),
        "parse_error_count": parse_stats.get("parse_error_count", 0),
        "rotation_fragment_count": max(loader_stats.get("resolved_path_count", 0) - 1, 0),
        "collector_gap_verifiable": False,
        "archive_gap_observations": "event_sparse_stream_cannot_prove_uptime",
    }


def evaluate_lq30_summary(
    *,
    density_report: dict[str, Any],
    overlap_report: dict[str, Any],
    concentration_report: dict[str, Any],
    source_quality_report: dict[str, Any],
) -> dict[str, Any]:
    actual_symbol_coverage = source_quality_report.get("actual_symbol_coverage")
    parse_error_count = source_quality_report.get("parse_error_count")

    overlap_ok = (
        overlap_report.get("alignment_overlap_available") is True
        and overlap_report.get("data_alignment_overlap_event_days", 0)
        >= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ALIGNMENT_OVERLAP_EVENT_DAYS
    )

    passes_core = (
        density_report["liquidation_history_days"] >= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_HISTORY_DAYS
        and density_report["symbols_with_events"] >= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_SYMBOLS_WITH_EVENTS
        and density_report["event_days"] >= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_EVENT_DAYS
        and overlap_ok
        and density_report["max_single_symbol_event_share"] <= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_SYMBOL_EVENT_SHARE
        and density_report["max_single_day_event_share"] <= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_DAY_EVENT_SHARE
        and density_report["top_1_day_notional_share"] <= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_DAY_NOTIONAL_SHARE
        and density_report["top_3_days_notional_share"] <= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP3_DAYS_NOTIONAL_SHARE
        and density_report["top_1_symbol_notional_share"] <= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_SYMBOL_NOTIONAL_SHARE
        and source_quality_report["invalid_json_line_ratio"] <= base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_INVALID_JSON_LINE_RATIO
    )

    fails_hard = (
        density_report["liquidation_history_days"] <= 0.0
        or density_report["symbols_with_events"] <= 0
        or density_report["event_days"] <= 0
        or source_quality_report.get("invalid_json_line_ratio", 0.0)
        > base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_INVALID_JSON_LINE_RATIO
        or (actual_symbol_coverage is not None and actual_symbol_coverage <= 0)
        or (parse_error_count is not None and parse_error_count > 0)
    )

    if passes_core:
        decision = "liquidation_diagnostic_promising"
        next_action = "continue_accumulating_exact_history"
    elif fails_hard:
        decision = "liquidation_diagnostic_unusable"
        next_action = "stop_waiting_for_90d_until_source_quality_or_density_improves"
    elif density_report["liquidation_history_days"] > 0:
        decision = "liquidation_diagnostic_weak"
        if overlap_report.get("alignment_overlap_available") is True:
            next_action = "prioritize_vendor_sample"
        else:
            next_action = "continue_accumulating_but_do_not_wait_for_90d"

    return {
        "decision": decision,
        "next_action": next_action,
        "liquidation_source_truth_level": "local_force_order_snapshot_rows_not_complete_tape",
        "complete_liquidation_tape_claim_allowed": False,
        "full_composite_claim_allowed": False,
        "alpha_interpretation_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
    }
