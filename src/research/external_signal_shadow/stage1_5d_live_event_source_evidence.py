import json
from pathlib import Path


def validate_upstream_evidence(stage1_5c1_summary_path: str | Path, stage1_5c_summary_path: str | Path) -> dict:
    blockers = []
    stage1_5c1_decision = None
    stage1_5c_top_level_decision = None
    matched_promising_cell = None

    c1_path = Path(stage1_5c1_summary_path)
    c_path = Path(stage1_5c_summary_path)

    # 1. Check file existence and load JSON
    c1_data = None
    if not c1_path.exists():
        blockers.append("stage1_5c1_summary_missing")
    else:
        try:
            with open(c1_path, "r", encoding="utf-8") as f:
                c1_data = json.load(f)
        except Exception:
            blockers.append("stage1_5c1_summary_parse_failed")

    c_data = None
    if not c_path.exists():
        blockers.append("stage1_5c_summary_missing")
    else:
        try:
            with open(c_path, "r", encoding="utf-8") as f:
                c_data = json.load(f)
        except Exception:
            blockers.append("stage1_5c_summary_parse_failed")

    if blockers:
        return {
            "upstream_evidence_valid": False,
            "blockers": blockers,
            "stage1_5c1_decision": stage1_5c1_decision,
            "stage1_5c_top_level_decision": stage1_5c_top_level_decision,
            "matched_promising_cell": matched_promising_cell,
        }

    # 2. Check 1.5C.1 decisions & safety
    stage1_5c1_decision = c1_data.get("decision")
    if stage1_5c1_decision != "stage1_5c1_price_coverage_ready_for_1_5c_rerun":
        blockers.append("stage1_5c1_decision_invalid")

    for flag in ["paper_trading_allowed", "live_trading_allowed", "alpha_interpretation_allowed"]:
        if c1_data.get(flag) is True:
            blockers.append("unsafe_upstream_trading_flag")

    # 3. Check 1.5C decisions & safety
    stage1_5c_top_level_decision = c_data.get("top_level_decision")
    if stage1_5c_top_level_decision != "stage1_5c_replay_completed":
        blockers.append("stage1_5c_decision_invalid")

    if c_data.get("research_result_valid") is not True:
        blockers.append("stage1_5c_research_result_invalid")

    for flag in ["paper_trading_allowed", "live_trading_allowed", "execution_engine_allowed", "alpha_interpretation_allowed"]:
        if c_data.get(flag) is True:
            blockers.append("unsafe_upstream_trading_flag")

    # 4. Check promising cells
    promising_cells = c_data.get("promising_cells", [])
    has_valid_cell = False
    for cell in promising_cells:
        if not isinstance(cell, str):
            continue
        parts = cell.split("|")
        if len(parts) >= 3:
            event_type = parts[0]
            signed_mode = parts[1]
            entry_delay = parts[2]
            if (
                event_type == "futures_contract_launch"
                and signed_mode == "futures_launch_long_attention_diagnostic"
                and entry_delay == "12h"
            ):
                has_valid_cell = True
                matched_promising_cell = cell
                break

    if not has_valid_cell:
        blockers.append("missing_futures_launch_long_attention_12h_promising_cell")

    # Deduplicate blockers list
    blockers = list(dict.fromkeys(blockers))

    return {
        "upstream_evidence_valid": len(blockers) == 0,
        "blockers": blockers,
        "stage1_5c1_decision": stage1_5c1_decision,
        "stage1_5c_top_level_decision": stage1_5c_top_level_decision,
        "matched_promising_cell": matched_promising_cell,
    }
