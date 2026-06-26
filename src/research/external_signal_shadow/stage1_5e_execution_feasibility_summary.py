import math
from typing import Any, Dict, List, Optional

from configs import base


def calculate_percentile(data: List[float], pct: float) -> Optional[float]:
    if not data:
        return None
    sorted_data = sorted(data)
    index = pct * (len(sorted_data) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return float(sorted_data[int(index)])
    return float(sorted_data[lower] + (sorted_data[upper] - sorted_data[lower]) * (index - lower))


def build_execution_feasibility_summary(
    upstream_valid: bool,
    candidate_rows: List[Dict[str, Any]],
    proxy_rows: List[Dict[str, Any]],
    live_depth_rows: List[Dict[str, Any]] = None,
    historical_orderbook_depth_available: bool = False,
    historical_depth_rows: List[Dict[str, Any]] = None,
    historical_depth_coverage: Dict[str, Any] = None,
    request_manifest_rows: List[Dict[str, Any]] = None,
    stage1_5d_dependency_status: str = "pending",
) -> Dict[str, Any]:
    """
    Build the Stage 1.5E execution feasibility audit summary decision.
    """
    blockers = []
    live_depth_rows = live_depth_rows or []
    historical_depth_rows = historical_depth_rows or []
    historical_depth_coverage = historical_depth_coverage or {}
    request_manifest_rows = request_manifest_rows or []

    if historical_depth_coverage:
        effective_historical_depth_available = bool(
            historical_depth_coverage.get("historical_orderbook_depth_available")
            and historical_depth_coverage.get("matched_snapshot_count", 0) > 0
        )
    else:
        effective_historical_depth_available = bool(historical_orderbook_depth_available)

    if not upstream_valid:
        blockers.append("upstream_evidence_missing_or_invalid")
        return {
            "decision": "stage1_5e_execution_feasibility_invalid",
            "research_result_valid": False,
            "execution_feasibility_proven": False,
            "historical_orderbook_depth_available": False,
            "historical_proxy_audit_valid": False,
            "live_depth_snapshot_available": False,
            "top_level_unique_symbol_event_count": 0,
            "cell_summaries": {},
            "ready_cells": [],
            "proxy_failed_cells": [],
            "inconclusive_cells": [],
            "candidate_event_days": 0,
            "symbols_with_events": 0,
            "blockers": blockers,
            "allowed_next_action": "none_fix_upstream",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False
        }

    # Count unique events
    unique_symbol_event_ids = {row.get("symbol_event_id") for row in candidate_rows if row.get("symbol_event_id")}
    top_level_unique_symbol_event_count = len(unique_symbol_event_ids)

    # Count days
    unique_days = set()
    for row in candidate_rows:
        day = row.get("event_day")
        if not day and row.get("entry_time_ms"):
            # Simple format conversion if time is timestamp
            from datetime import datetime, timezone
            try:
                dt = datetime.fromtimestamp(row["entry_time_ms"] / 1000.0, timezone.utc)
                day = dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        if day:
            unique_days.add(day)

    candidate_event_days = len(unique_days)

    # Count symbols
    unique_symbols = {row.get("symbol") for row in candidate_rows if row.get("symbol")}
    symbols_with_events = len(unique_symbols)

    # Perform top level validation
    min_event_count = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_MIN_AUDIT_EVENT_COUNT", 30)
    min_event_days = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_MIN_AUDIT_EVENT_DAYS", 10)
    min_symbols = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_MIN_AUDIT_SYMBOLS", 3)

    if top_level_unique_symbol_event_count < min_event_count:
        blockers.append("insufficient_candidate_event_count")
    if candidate_event_days < min_event_days:
        blockers.append("insufficient_candidate_event_days")
    if symbols_with_events < min_symbols:
        blockers.append("insufficient_candidate_symbols")

    # Map candidate and proxy rows to cells
    # cell key format: event_type|signed_mode|entry_delay_hours|filter_group
    cell_candidates: Dict[str, List[Dict[str, Any]]] = {}
    cell_proxies: Dict[str, List[Dict[str, Any]]] = {}

    for row in candidate_rows:
        cell_key = row.get("cell_key")
        if not cell_key:
            cell_key = f"{row.get('event_type')}|{row.get('signed_mode')}|{row.get('entry_delay_hours')}h|{row.get('filter_group')}"
        cell_candidates.setdefault(cell_key, []).append(row)

    for row in proxy_rows:
        cell_key = row.get("cell_key")
        if not cell_key:
            cell_key = f"{row.get('event_type')}|{row.get('signed_mode')}|{row.get('entry_delay_hours')}h|{row.get('filter_group')}"
        cell_proxies.setdefault(cell_key, []).append(row)

    cell_summaries = {}
    ready_cells = []
    proxy_failed_cells = []
    inconclusive_cells = []

    # Process each cell that has candidates
    for cell_key, candidates in cell_candidates.items():
        proxies = cell_proxies.get(cell_key, [])

        # Calculate cell unique events
        cell_event_ids = {r.get("symbol_event_id") for r in candidates if r.get("symbol_event_id")}
        cell_event_count = len(cell_event_ids)

        # Collect metrics for percentiles
        entry_bar_ranges = []
        entry_1h_ranges = []
        entry_4h_ranges = []
        pre_entry_volumes = []

        passed_quote_volume = 0
        total_valid_proxies = 0

        min_pre_entry_vol = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_MIN_PRE_ENTRY_24H_QUOTE_VOLUME_USDT", 50_000_000)

        for p in proxies:
            if p.get("entry_bar_found"):
                total_valid_proxies += 1
                entry_bar_ranges.append(p.get("entry_bar_range_bps", 0.0))
                entry_1h_ranges.append(p.get("entry_1h_range_bps", 0.0))
                entry_4h_ranges.append(p.get("entry_4h_range_bps", 0.0))
                pre_vol = p.get("pre_entry_24h_quote_volume_usdt", 0.0)
                pre_entry_volumes.append(pre_vol)
                if pre_vol >= min_pre_entry_vol:
                    passed_quote_volume += 1

        # Quote volume pass rate
        quote_volume_pass_rate = 0.0
        if total_valid_proxies > 0:
            quote_volume_pass_rate = passed_quote_volume / total_valid_proxies

        # Percentiles
        median_entry_bar_range = calculate_percentile(entry_bar_ranges, 0.5)
        p95_entry_bar_range = calculate_percentile(entry_bar_ranges, 0.95)
        median_entry_1h_range = calculate_percentile(entry_1h_ranges, 0.5)
        p95_entry_1h_range = calculate_percentile(entry_1h_ranges, 0.95)
        median_entry_4h_range = calculate_percentile(entry_4h_ranges, 0.5)
        p95_entry_4h_range = calculate_percentile(entry_4h_ranges, 0.95)
        median_pre_entry_vol = calculate_percentile(pre_entry_volumes, 0.5)
        p05_pre_entry_vol = calculate_percentile(pre_entry_volumes, 0.05)

        # Blocker checks for this cell
        cell_failed = False

        max_15m_range = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_MAX_ENTRY_15M_RANGE_BPS", 300.0)
        p95_multiplier = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_P95_RANGE_MULTIPLIER_BLOCK", 2.0)
        max_1h_range = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_MAX_ENTRY_1H_RANGE_BPS", 600.0)
        max_4h_range = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_MAX_ENTRY_4H_RANGE_BPS", 1_200.0)
        min_pass_rate = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_MIN_QUOTE_VOLUME_PASS_RATE", 0.70)

        # 1. Median 15m range check
        if median_entry_bar_range is not None and median_entry_bar_range > max_15m_range:
            cell_failed = True
            blockers.append("entry_15m_range_too_wide")

        # 2. P95 15m range multiplier check
        if p95_entry_bar_range is not None and p95_entry_bar_range > (max_15m_range * p95_multiplier):
            cell_failed = True
            blockers.append("p95_entry_15m_range_exceeds_multiplier_threshold")

        # 3. Median 1h range check
        if median_entry_1h_range is not None and median_entry_1h_range > max_1h_range:
            cell_failed = True
            blockers.append("entry_1h_range_too_wide")

        # 4. Median 4h range check
        if median_entry_4h_range is not None and median_entry_4h_range > max_4h_range:
            cell_failed = True
            blockers.append("entry_4h_range_too_wide")

        # 5. Quote volume pass rate check
        if quote_volume_pass_rate < min_pass_rate:
            cell_failed = True
            blockers.append("quote_volume_pass_rate_below_threshold")

        # Process live depth if available
        # Find depth rows matching this cell's symbols
        cell_symbols = {r.get("symbol") for r in candidates if r.get("symbol")}
        matching_depths = []
        if live_depth_rows:
            matching_depths.extend(d for d in live_depth_rows if d.get("symbol") in cell_symbols)
        if historical_depth_rows:
            matching_depths.extend(d for d in historical_depth_rows if d.get("symbol") in cell_symbols)

        spreads = [d["spread_bps"] for d in matching_depths if "spread_bps" in d]
        slippages = [d["slippage_estimate_bps_for_500usdt_buy"] for d in matching_depths if "slippage_estimate_bps_for_500usdt_buy" in d]

        median_spread_bps = calculate_percentile(spreads, 0.5)
        p95_spread_bps = calculate_percentile(spreads, 0.95)
        median_slippage_bps = calculate_percentile(slippages, 0.5)
        p95_slippage_bps = calculate_percentile(slippages, 0.95)

        # Decide cell status
        if cell_failed:
            cell_status = "proxy_failed"
            proxy_failed_cells.append(cell_key)
        elif effective_historical_depth_available and len(matching_depths) > 0:
            cell_status = "ready_for_live_depth_observer"
            ready_cells.append(cell_key)
        elif live_depth_rows and len(matching_depths) > 0:
            cell_status = "ready_for_live_depth_observer"
            ready_cells.append(cell_key)
        elif stage1_5d_dependency_status in ("operational_unvalidated", "event_detection_passed"):
            cell_status = "ready_for_live_depth_observer"
            ready_cells.append(cell_key)
        elif stage1_5d_dependency_status == "pending":
            cell_status = "inconclusive_pending_stage1_5d"
            inconclusive_cells.append(cell_key)
        else:
            cell_status = "inconclusive_depth_missing"
            inconclusive_cells.append(cell_key)

        cell_summaries[cell_key] = {
            "cell_event_count": cell_event_count,
            "cell_status": cell_status,
            "median_entry_bar_range_bps": median_entry_bar_range,
            "p95_entry_bar_range_bps": p95_entry_bar_range,
            "median_entry_1h_range_bps": median_entry_1h_range,
            "p95_entry_1h_range_bps": p95_entry_1h_range,
            "median_entry_4h_range_bps": median_entry_4h_range,
            "p95_entry_4h_range_bps": p95_entry_4h_range,
            "median_pre_entry_24h_quote_volume_usdt": median_pre_entry_vol,
            "p05_pre_entry_24h_quote_volume_usdt": p05_pre_entry_vol,
            "quote_volume_pass_rate": quote_volume_pass_rate,
            "median_spread_bps_if_live_depth_available": median_spread_bps,
            "p95_spread_bps_if_live_depth_available": p95_spread_bps,
            "median_slippage_bps_for_500usdt_buy_if_live_depth_available": median_slippage_bps,
            "p95_slippage_bps_for_500usdt_buy_if_live_depth_available": p95_slippage_bps,
        }

    # Top-level decision logic
    # Clean duplicates in blockers
    if historical_depth_coverage and not effective_historical_depth_available:
        blockers.append("historical_orderbook_depth_no_matched_snapshots")
        reject_reason = historical_depth_coverage.get("coverage_reject_reason")
        if reject_reason:
            blockers.append(reject_reason)

    blockers = list(dict.fromkeys(blockers))

    if "insufficient_candidate_event_count" in blockers or "insufficient_candidate_event_days" in blockers or "insufficient_candidate_symbols" in blockers:
        decision = "stage1_5e_execution_feasibility_invalid"
    elif len(proxy_failed_cells) > 0:
        decision = "stage1_5e_execution_feasibility_proxy_failed"
    elif not effective_historical_depth_available and not (live_depth_rows and len(live_depth_rows) > 0) and stage1_5d_dependency_status == "pending":
        decision = "stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d"
    elif not effective_historical_depth_available and not (live_depth_rows and len(live_depth_rows) > 0) and stage1_5d_dependency_status not in ("operational_unvalidated", "event_detection_passed"):
        decision = "stage1_5e_execution_feasibility_inconclusive_depth_missing"
    else:
        decision = "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer"

    # Aggregated top level statistics
    all_entry_bar_ranges = [p.get("entry_bar_range_bps", 0.0) for p in proxy_rows if p.get("entry_bar_found")]
    all_entry_1h_ranges = [p.get("entry_1h_range_bps", 0.0) for p in proxy_rows if p.get("entry_bar_found")]
    all_entry_4h_ranges = [p.get("entry_4h_range_bps", 0.0) for p in proxy_rows if p.get("entry_bar_found")]
    all_pre_vols = [p.get("pre_entry_24h_quote_volume_usdt", 0.0) for p in proxy_rows if p.get("entry_bar_found")]

    all_spreads = []
    all_slippages = []
    if live_depth_rows:
        all_spreads = [d["spread_bps"] for d in live_depth_rows if "spread_bps" in d]
        all_slippages = [d["slippage_estimate_bps_for_500usdt_buy"] for d in live_depth_rows if "slippage_estimate_bps_for_500usdt_buy" in d]

    allowed_next_action = "none_reassess"
    if decision == "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer":
        allowed_next_action = "write_stage1_5f_live_execution_feasibility_observer_design"

    return {
        "decision": decision,
        "research_result_valid": decision == "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
        "execution_feasibility_proven": False,
        "historical_orderbook_depth_available": effective_historical_depth_available,
        "historical_depth_coverage": historical_depth_coverage,
        "mark_index_proxy_available": False,
        "mark_index_divergence_status": "not_audited",
        "historical_proxy_audit_valid": len(proxy_failed_cells) == 0 and len(inconclusive_cells) >= 0 and decision != "stage1_5e_execution_feasibility_invalid",
        "live_depth_snapshot_available": bool(live_depth_rows and len(live_depth_rows) > 0),
        "source_smoke_dependency_status": stage1_5d_dependency_status,
        "top_level_unique_symbol_event_count": top_level_unique_symbol_event_count,
        "cell_summaries": cell_summaries,
        "ready_cells": ready_cells,
        "proxy_failed_cells": proxy_failed_cells,
        "inconclusive_cells": inconclusive_cells,
        "candidate_event_days": candidate_event_days,
        "symbols_with_events": symbols_with_events,
        "median_entry_bar_range_bps": calculate_percentile(all_entry_bar_ranges, 0.5),
        "p95_entry_bar_range_bps": calculate_percentile(all_entry_bar_ranges, 0.95),
        "median_entry_1h_range_bps": calculate_percentile(all_entry_1h_ranges, 0.5),
        "p95_entry_1h_range_bps": calculate_percentile(all_entry_1h_ranges, 0.95),
        "median_entry_4h_range_bps": calculate_percentile(all_entry_4h_ranges, 0.5),
        "p95_entry_4h_range_bps": calculate_percentile(all_entry_4h_ranges, 0.95),
        "median_pre_entry_24h_quote_volume_usdt": calculate_percentile(all_pre_vols, 0.5),
        "median_live_spread_bps": calculate_percentile(all_spreads, 0.5),
        "median_live_slippage_bps_for_500usdt_buy": calculate_percentile(all_slippages, 0.5),
        "blockers": blockers,
        "allowed_next_action": allowed_next_action,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False
    }
