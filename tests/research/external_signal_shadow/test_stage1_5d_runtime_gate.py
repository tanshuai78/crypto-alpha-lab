from pathlib import Path

from src.research.external_signal_shadow.stage1_5d_runtime_gate import (
    build_stage1_5d_runtime_gate,
    get_stage1_5d_runtime_gate_filename,
    write_stage1_5d_runtime_gate,
    write_stage1_5d_runtime_gate_atomic,
)


def _build_test_gate_context(**kwargs):
    default_context = {
        "output_root": Path("/tmp/test_root"),
        "run_id": "test_run",
        "events_stream_relative_path": "events/*.jsonl",
        "generated_at_ms": 100_000,
        "first_poll_started_at_ms": 10_000,
        "last_poll_finished_at_ms": 90_000,
        "poll_attempt_count": 10,
        "successful_poll_count": 10,
        "failed_poll_count": 0,
        "consecutive_failed_polls": 0,
        "fatal_blockers": [],
        "prior_stage_safety_prerequisite_met": True,
        "fixture_run": False,
        "source_format_drift_active": False,
        "schema_parse_error_active": False,
        "storage_budget_passed": True,
        "detail_endpoint_degraded_active": False,
        "bapi_trusted_payload_rate": 1.0,
        "symbol_parse_success_rate": 1.0,
        "symbol_validation_success_rate": 1.0,
        "scheduler_starved_expired_count": 0,
    }
    default_context.update(kwargs)
    return default_context


def test_runtime_gate_config_defaults():
    from configs import base
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_STALENESS_SEC >= 120
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_REVALIDATION_INTERVAL_SEC >= 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_CONSECUTIVE_FAILURES >= 1


def test_stage1_5d_runtime_gate_filename():
    assert get_stage1_5d_runtime_gate_filename() == "live_safety_gate_summary.json"


def test_stage1_5d_runtime_gate_initial_state_is_initializing():
    ctx = _build_test_gate_context(successful_poll_count=0, poll_attempt_count=0)
    gate = build_stage1_5d_runtime_gate(ctx)
    assert gate["decision"] == "stage1_5d_runtime_gate_initializing"
    assert gate["status"] == "INITIALIZING"
    assert gate.get("request_success_rate") is None
    assert gate["trade_signal_allowed"] is False
    assert gate["execution_feasibility_claim_allowed"] is False


def test_stage1_5d_runtime_gate_requires_prior_stage_safety_prerequisite_met():
    ctx = _build_test_gate_context(prior_stage_safety_prerequisite_met=False)
    gate = build_stage1_5d_runtime_gate(ctx)
    assert gate["decision"] == "stage1_5d_runtime_gate_initializing"
    assert gate["prior_stage_safety_prerequisite_met"] is False


def test_stage1_5d_runtime_gate_ready_state():
    ctx = _build_test_gate_context()
    gate = build_stage1_5d_runtime_gate(ctx)
    assert gate["runtime_gate_schema_version"] == 1
    assert gate["decision"] == "stage1_5d_runtime_gate_ready"
    assert gate["source_root"] == str(Path("/tmp/test_root").resolve())
    assert gate["events_stream_relative_path"] == "events/*.jsonl"
    assert gate["consumable_by_stage1_5f"] is True
    assert gate["formal_event_contract_versions_supported"] == [2]
    assert gate["formal_schedule_revision_contract_versions_supported"] == [1]
    assert gate["anchor_precedence_policy"] == "official_schedule_priority_v1"
    assert gate["shared_anchor_validator_enabled"] is True
    for field in (
        "execution_feasibility_claim_allowed",
        "trade_signal_allowed",
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_engine_allowed",
        "alpha_interpretation_allowed",
    ):
        assert gate[field] is False


def test_stage1_5d_runtime_gate_degraded_state():
    ctx = _build_test_gate_context(consecutive_failed_polls=3)
    gate = build_stage1_5d_runtime_gate(ctx)
    assert gate["decision"] == "stage1_5d_runtime_gate_degraded"
    assert gate["consumable_by_stage1_5f"] is False


def test_stage1_5d_runtime_gate_failed_state():
    ctx = _build_test_gate_context(fatal_blockers=["bapi_body_schema_drift"])
    gate = build_stage1_5d_runtime_gate(ctx)
    assert gate["decision"] == "stage1_5d_runtime_gate_failed"
    assert gate["consumable_by_stage1_5f"] is False


def test_stage1_5d_runtime_gate_atomic_write(tmp_path):
    ctx = _build_test_gate_context(output_root=tmp_path)
    gate = build_stage1_5d_runtime_gate(ctx)
    written_path = write_stage1_5d_runtime_gate_atomic(tmp_path, gate)
    assert written_path.exists()
    assert written_path.name == "live_safety_gate_summary.json"
    assert write_stage1_5d_runtime_gate(tmp_path, gate).exists()
