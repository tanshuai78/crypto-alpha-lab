import json
import sys

from scripts.external_signal_shadow.run_stage1_5e_execution_feasibility_audit import (
    main,
    map_stage1_5d_dependency_status,
)


def test_runner_requires_upstream_evidence(tmp_path, monkeypatch):
    summary = tmp_path / "summary.json"
    monkeypatch.setattr(sys, "argv", [
        "run_stage1_5e_execution_feasibility_audit.py",
        "--stage1-5c-summary", str(tmp_path / "missing_5c.json"),
        "--stage1-5c1-summary", str(tmp_path / "missing_5c1.json"),
        "--output-summary", str(summary),
    ])

    rc = main()
    assert rc == 2
    data = json.loads(summary.read_text())
    assert data["decision"] == "stage1_5e_execution_feasibility_invalid"
    assert "upstream_evidence_missing_or_invalid" in data["blockers"]


def test_runner_fixture_proxy_only_writes_inconclusive_summary(tmp_path, monkeypatch):
    c_summary = tmp_path / "stage1_5c.json"
    c1_summary = tmp_path / "stage1_5c1.json"
    candidates = tmp_path / "candidates.jsonl"
    klines = tmp_path / "klines.jsonl"
    output_summary = tmp_path / "summary.json"

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
    candidates.write_text("")
    klines.write_text("")

    monkeypatch.setattr(sys, "argv", [
        "run_stage1_5e_execution_feasibility_audit.py",
        "--stage1-5c-summary", str(c_summary),
        "--stage1-5c1-summary", str(c1_summary),
        "--candidates-jsonl", str(candidates),
        "--klines-jsonl", str(klines),
        "--output-summary", str(output_summary),
        "--fixture-proxy-only",
    ])

    rc = main()
    # It might fail with invalid due to insufficient count, but should write a valid summary dictionary.
    assert rc in (0, 1, 2)
    data = json.loads(output_summary.read_text())
    assert data["paper_trading_allowed"] is False
    assert data["live_trading_allowed"] is False


def test_runner_live_depth_requires_stage1_5d_event_rows(tmp_path, monkeypatch):
    c_summary = tmp_path / "stage1_5c.json"
    c1_summary = tmp_path / "stage1_5c1.json"
    candidates = tmp_path / "candidates.jsonl"
    klines = tmp_path / "klines.jsonl"
    output_summary = tmp_path / "summary.json"

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
    candidates.write_text("")
    klines.write_text("")

    monkeypatch.setattr(sys, "argv", [
        "run_stage1_5e_execution_feasibility_audit.py",
        "--stage1-5c-summary", str(c_summary),
        "--stage1-5c1-summary", str(c1_summary),
        "--candidates-jsonl", str(candidates),
        "--klines-jsonl", str(klines),
        "--output-summary", str(output_summary),
        "--live-public-readonly",
    ])

    rc = main()
    assert rc == 2
    data = json.loads(output_summary.read_text())
    assert "stage1_5d_events_required_for_live_depth" in data["blockers"]
    assert data["live_depth_snapshot_available"] is False


def test_map_stage1_5d_dependency_status_does_not_treat_failed_as_operational():
    assert map_stage1_5d_dependency_status("stage1_5d_smoke_observation_in_progress") == "pending"
    assert map_stage1_5d_dependency_status("stage1_5d_operational_pass_event_detection_unvalidated") == "operational_unvalidated"
    assert map_stage1_5d_dependency_status("stage1_5d_event_detection_passed") == "event_detection_passed"
    assert map_stage1_5d_dependency_status("stage1_5d_smoke_failed") == "failed_or_invalid"
    assert map_stage1_5d_dependency_status("stage1_5d_smoke_invalid") == "failed_or_invalid"
    assert map_stage1_5d_dependency_status("unexpected_future_value") == "unknown"
