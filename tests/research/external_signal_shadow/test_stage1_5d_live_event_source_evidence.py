import json

from src.research.external_signal_shadow.stage1_5d_live_event_source_evidence import (
    validate_upstream_evidence,
)


def test_validate_upstream_evidence_passes_required_decisions(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": ["futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is True
    assert result["blockers"] == []


def test_validate_upstream_evidence_accepts_g2_12h_long_attention_cell(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": ["futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is True
    assert result["matched_promising_cell"] == "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only"


def test_validate_upstream_evidence_rejects_non_12h_or_wrong_mode_cells(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [
            "futures_contract_launch|futures_launch_long_attention_diagnostic|4h|G2_price_coverage_only",
            "futures_contract_launch|futures_launch_short_access_diagnostic|12h|G2_price_coverage_only",
        ],
    }))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is False
    assert "missing_futures_launch_long_attention_12h_promising_cell" in result["blockers"]


def test_validate_upstream_evidence_blocks_missing_promising_cell(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    c.write_text(json.dumps({"top_level_decision": "stage1_5c_replay_completed", "research_result_valid": True, "promising_cells": []}))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is False
    assert "missing_futures_launch_long_attention_12h_promising_cell" in result["blockers"]


def test_validate_upstream_evidence_rejects_paper_live_flags(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({"decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun"}))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": ["futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"],
        "paper_trading_allowed": True,
    }))
    result = validate_upstream_evidence(c1, c)
    assert result["upstream_evidence_valid"] is False
    assert "unsafe_upstream_trading_flag" in result["blockers"]
