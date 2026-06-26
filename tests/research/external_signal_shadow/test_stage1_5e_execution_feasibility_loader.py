import json

from src.research.external_signal_shadow.stage1_5e_execution_feasibility_loader import (
    load_promising_12h_long_attention_candidates,
    validate_stage1_5e_upstream_evidence,
)


def test_validate_upstream_requires_stage1_5c_promising_12h_cell(tmp_path):
    c_summary = tmp_path / "stage1_5c_summary.json"
    c1_summary = tmp_path / "stage1_5c1_summary.json"
    c_summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [
            "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
        ],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c1_summary.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))

    result = validate_stage1_5e_upstream_evidence(c1_summary, c_summary)
    assert result["valid"] is True
    assert result["primary_promising_cell_present"] is True


def test_validate_upstream_rejects_missing_promising_cell(tmp_path):
    c_summary = tmp_path / "stage1_5c_summary.json"
    c1_summary = tmp_path / "stage1_5c1_summary.json"
    c_summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c1_summary.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))

    result = validate_stage1_5e_upstream_evidence(c1_summary, c_summary)
    assert result["valid"] is False
    assert "missing_futures_launch_long_attention_12h_promising_cell" in result["blockers"]


def test_validate_upstream_accepts_g2_only_cell(tmp_path):
    c_summary = tmp_path / "stage1_5c_summary.json"
    c1_summary = tmp_path / "stage1_5c1_summary.json"
    c_summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [
            "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only"
        ],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c1_summary.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))

    result = validate_stage1_5e_upstream_evidence(c1_summary, c_summary)
    assert result["valid"] is True
    assert result["primary_promising_cell_present"] is True


def test_load_promising_candidates_filters_only_12h_long_attention_primary_rows(tmp_path):
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(
        "\n".join([
            json.dumps({
                "symbol": "ABCUSDT",
                "symbol_event_id": "evt-1",
                "event_type": "futures_contract_launch",
                "signed_mode": "futures_launch_long_attention_diagnostic",
                "entry_delay_hours": 12,
                "filter_group": "G1_source_event_after_first_hour_delay",
                "entry_time_ms": 1_000,
            }),
            json.dumps({
                "symbol": "ABCUSDT",
                "symbol_event_id": "evt-1",
                "event_type": "futures_contract_launch",
                "signed_mode": "futures_launch_short_access_diagnostic",
                "entry_delay_hours": 12,
                "filter_group": "G1_source_event_after_first_hour_delay",
                "entry_time_ms": 1_000,
            }),
            json.dumps({
                "symbol": "XYZUSDT",
                "symbol_event_id": "evt-2",
                "event_type": "futures_contract_launch",
                "signed_mode": "futures_launch_long_attention_diagnostic",
                "entry_delay_hours": 12,
                "filter_group": "G2_price_coverage_only",
                "entry_time_ms": 2_000,
            }),
        ])
    )

    loaded = load_promising_12h_long_attention_candidates(candidates)
    assert len(loaded) == 2
    assert {row["filter_group"] for row in loaded} == {
        "G1_source_event_after_first_hour_delay",
        "G2_price_coverage_only",
    }
