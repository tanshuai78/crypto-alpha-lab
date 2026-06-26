import json
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from configs import base


def validate_stage1_5e_upstream_evidence(
    stage1_5c1_summary_path: Any,
    stage1_5c_summary_path: Any
) -> Dict[str, Any]:
    """
    Validate that Stage 1.5C and Stage 1.5C.1 summaries exist and meet the requirements
    for executing the Stage 1.5E execution feasibility audit.
    """
    blockers = []
    c1_path = Path(stage1_5c1_summary_path)
    c_path = Path(stage1_5c_summary_path)

    if not c_path.exists():
        blockers.append("stage1_5c_summary_missing")
        return {"valid": False, "primary_promising_cell_present": False, "blockers": blockers}

    if not c1_path.exists():
        blockers.append("stage1_5c1_summary_missing")
        return {"valid": False, "primary_promising_cell_present": False, "blockers": blockers}

    try:
        with open(c_path, "r", encoding="utf-8") as f:
            c_data = json.load(f)
    except Exception as e:
        blockers.append(f"stage1_5c_summary_parse_error: {str(e)}")
        return {"valid": False, "primary_promising_cell_present": False, "blockers": blockers}

    try:
        with open(c1_path, "r", encoding="utf-8") as f:
            c1_data = json.load(f)
    except Exception as e:
        blockers.append(f"stage1_5c1_summary_parse_error: {str(e)}")
        return {"valid": False, "primary_promising_cell_present": False, "blockers": blockers}

    # Verify Stage 1.5C decision and validity
    if c_data.get("top_level_decision") != "stage1_5c_replay_completed":
        blockers.append("stage1_5c_not_completed")

    if not c_data.get("research_result_valid", False):
        blockers.append("stage1_5c_research_result_invalid")

    # Verify Stage 1.5C.1 decision
    if c1_data.get("decision") != "stage1_5c1_price_coverage_ready_for_1_5c_rerun":
        blockers.append("stage1_5c1_price_coverage_not_ready")

    # Safety checks: all safety-related flags must be False
    for flag in ["paper_trading_allowed", "live_trading_allowed", "execution_engine_allowed", "alpha_interpretation_allowed"]:
        if c_data.get(flag, False) is not False:
            blockers.append(f"stage1_5c_{flag}_is_not_false")
        if c1_data.get(flag, False) is not False:
            blockers.append(f"stage1_5c1_{flag}_is_not_false")

    # Check for promising 12h long_attention cells
    promising_cells = c_data.get("promising_cells", [])
    primary_promising_cell_present = False

    # We look for G1 and G2 cells specifically matching:
    # futures_contract_launch | futures_launch_long_attention_diagnostic | 12h
    for cell in promising_cells:
        parts = cell.split("|")
        if len(parts) == 4:
            evt_type, signed_mode, delay, group = parts
            if (
                evt_type == base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_EVENT_TYPE
                and signed_mode == base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_SIGNED_MODE
                and delay == f"{base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_ENTRY_DELAY_HOURS}h"
                and group in base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_FILTER_GROUPS
            ):
                primary_promising_cell_present = True

    if not primary_promising_cell_present:
        blockers.append("missing_futures_launch_long_attention_12h_promising_cell")

    valid = len(blockers) == 0
    return {
        "valid": valid,
        "primary_promising_cell_present": primary_promising_cell_present,
        "blockers": blockers
    }


def load_promising_12h_long_attention_candidates(candidates_jsonl_path: Any) -> List[Dict[str, Any]]:
    """
    Read candidates JSONL and return only 12h long_attention primary rows.
    Deduplicates rows by symbol_event_id + signed_mode + entry_delay_hours + filter_group.
    """
    c_path = Path(candidates_jsonl_path)
    if not c_path.exists():
        logger.warning(f"Candidates file {c_path} does not exist.")
        return []

    loaded_rows = []
    seen_keys = set()
    quarantine_count = 0

    with open(c_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                quarantine_count += 1
                continue

            # Filtering requirements
            evt_type = row.get("event_type")
            signed_mode = row.get("signed_mode")
            entry_delay = row.get("entry_delay_hours")

            if (
                evt_type != base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_EVENT_TYPE
                or signed_mode != base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_SIGNED_MODE
                or entry_delay != base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_ENTRY_DELAY_HOURS
            ):
                continue

            # Determine filter groups to process
            filter_groups = []
            if "filter_group" in row:
                filter_groups.append(row["filter_group"])
            else:
                # Dynamically construct G1 and G2 from candidates file flags
                filter_groups.append("G1_source_event_after_first_hour_delay")
                if row.get("replay_allowed") is True:
                    filter_groups.append("G2_price_coverage_only")

            for fg in filter_groups:
                if fg in base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_FILTER_GROUPS:
                    row_copy = dict(row)
                    row_copy["filter_group"] = fg
                    if "entry_time_ms" not in row_copy:
                        row_copy["entry_time_ms"] = row_copy.get("entry_bar_start_ms") or row_copy.get("entry_candidate_time_ms")
                    # Deduplication key
                    key = (
                        row_copy.get("symbol_event_id"),
                        signed_mode,
                        entry_delay,
                        fg
                    )
                    if key not in seen_keys:
                        seen_keys.add(key)
                        loaded_rows.append(row_copy)

    if quarantine_count > 0:
        logger.warning(f"Quarantined {quarantine_count} malformed rows while loading candidates.")

    return loaded_rows
