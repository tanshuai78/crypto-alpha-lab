from pathlib import Path
import json
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
    validate_stage1_5d_runtime_gate,
    validate_historical_stage1_5d_safety_gate,
)


def _build_ready_gate(output_root: Path, generated_at_ms: int = 100_000) -> dict:
    return {
        "runtime_gate_schema_version": 1,
        "decision": "stage1_5d_runtime_gate_ready",
        "source_root": str(output_root.resolve()),
        "run_id": "test_run",
        "events_stream_relative_path": "events/*.jsonl",
        "live_public_readonly": True,
        "gate_version": 1,
        "status": "READY",
        "consumable_by_stage1_5f": True,
        "prior_stage_safety_prerequisite_met": True,
        "not_ready_reasons": [],
        "generated_at_ms": generated_at_ms,
        "first_poll_started_at_ms": generated_at_ms - 60_000,
        "last_poll_finished_at_ms": generated_at_ms - 1000,
        "poll_attempt_count": 10,
        "successful_poll_count": 10,
        "failed_poll_count": 0,
        "consecutive_failed_polls": 0,
        "fatal_blockers": [],
        "execution_feasibility_claim_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "live_trading_enabled": False,
    }


def test_1_5f_loader_validates_healthy_ready_runtime_gate(tmp_path):
    gate_data = _build_ready_gate(tmp_path)
    gate_file = tmp_path / "live_safety_gate_summary.json"
    gate_file.write_text(json.dumps(gate_data))

    res = validate_stage1_5d_runtime_gate(gate_file, str(tmp_path / "events" / "*.jsonl"), now_ms=101_000)
    assert res["valid"] is True
    assert res["decision"] == "stage1_5d_runtime_gate_ready"


def test_1_5f_loader_rejects_missing_runtime_gate(tmp_path):
    res = validate_stage1_5d_runtime_gate(tmp_path / "live_safety_gate_summary.json", str(tmp_path / "events" / "*.jsonl"), now_ms=101_000)
    assert res["valid"] is False
    assert res["reason"] == "runtime_gate_file_missing_or_corrupt"


def test_1_5f_loader_rejects_initializing_runtime_gate(tmp_path):
    gate_data = _build_ready_gate(tmp_path)
    gate_data["decision"] = "stage1_5d_runtime_gate_initializing"
    gate_data["status"] = "INITIALIZING"
    gate_data["consumable_by_stage1_5f"] = False
    gate_file = tmp_path / "live_safety_gate_summary.json"
    gate_file.write_text(json.dumps(gate_data))

    res = validate_stage1_5d_runtime_gate(gate_file, str(tmp_path / "events" / "*.jsonl"), now_ms=101_000)
    assert res["valid"] is False
    assert res["reason"] == "runtime_gate_not_ready"


def test_1_5f_loader_rejects_degraded_runtime_gate(tmp_path):
    gate_data = _build_ready_gate(tmp_path)
    gate_data["decision"] = "stage1_5d_runtime_gate_degraded"
    gate_data["status"] = "DEGRADED"
    gate_data["consumable_by_stage1_5f"] = False
    gate_file = tmp_path / "live_safety_gate_summary.json"
    gate_file.write_text(json.dumps(gate_data))

    res = validate_stage1_5d_runtime_gate(gate_file, str(tmp_path / "events" / "*.jsonl"), now_ms=101_000)
    assert res["valid"] is False
    assert res["reason"] == "runtime_gate_not_ready"


def test_1_5f_loader_rejects_failed_runtime_gate(tmp_path):
    gate_data = _build_ready_gate(tmp_path)
    gate_data["decision"] = "stage1_5d_runtime_gate_failed"
    gate_data["status"] = "FAILED"
    gate_data["fatal_blockers"] = ["schema_drift"]
    gate_data["consumable_by_stage1_5f"] = False
    gate_file = tmp_path / "live_safety_gate_summary.json"
    gate_file.write_text(json.dumps(gate_data))

    res = validate_stage1_5d_runtime_gate(gate_file, str(tmp_path / "events" / "*.jsonl"), now_ms=101_000)
    assert res["valid"] is False
    assert res["reason"] == "runtime_gate_fatal_blockers_present"


def test_1_5f_loader_rejects_runtime_gate_root_mismatch(tmp_path):
    root = tmp_path / "root"
    other = tmp_path / "other"
    root.mkdir()
    other.mkdir()
    gate_data = _build_ready_gate(root)
    gate_file = root / "live_safety_gate_summary.json"
    gate_file.write_text(json.dumps(gate_data))

    res = validate_stage1_5d_runtime_gate(gate_file, str(other / "events" / "*.jsonl"), now_ms=101_000)
    assert res["valid"] is False
    assert res["reason"] == "runtime_gate_root_mismatch"


def test_1_5f_loader_rejects_stale_runtime_gate(tmp_path):
    gate_data = _build_ready_gate(tmp_path, generated_at_ms=100_000)
    gate_file = tmp_path / "live_safety_gate_summary.json"
    gate_file.write_text(json.dumps(gate_data))

    res = validate_stage1_5d_runtime_gate(gate_file, str(tmp_path / "events" / "*.jsonl"), now_ms=400_000)
    assert res["valid"] is False
    assert res["reason"] == "runtime_gate_stale"
    assert res["stale"] is True


def test_1_5f_loader_rejects_missing_or_true_safety_fields(tmp_path):
    gate_data = _build_ready_gate(tmp_path)
    gate_data.pop("trade_signal_allowed")
    gate_file = tmp_path / "live_safety_gate_summary.json"
    gate_file.write_text(json.dumps(gate_data))

    res = validate_stage1_5d_runtime_gate(gate_file, str(tmp_path / "events" / "*.jsonl"), now_ms=101_000)
    assert res["valid"] is False
    assert res["reason"] == "runtime_gate_safety_field_missing_or_true"

    gate_data = _build_ready_gate(tmp_path)
    gate_data["trade_signal_allowed"] = True
    gate_file.write_text(json.dumps(gate_data))
    res = validate_stage1_5d_runtime_gate(gate_file, str(tmp_path / "events" / "*.jsonl"), now_ms=101_000)
    assert res["valid"] is False
    assert res["reason"] == "runtime_gate_safety_field_missing_or_true"


def test_1_5f_loader_historical_override_requires_bootstrap_watermark(tmp_path):
    summary_data = {
        "decision": "stage1_5d_smoke_ready",
        "fatal_blockers": [],
        "live_trading_enabled": False,
    }
    summary_file = tmp_path / "historical_summary.json"
    summary_file.write_text(json.dumps(summary_data))

    res = validate_historical_stage1_5d_safety_gate(
        summary_path=summary_file,
        bootstrap_watermark_ms=None,
    )
    assert res["valid"] is False
    assert res["reason"] == "historical_classification_bootstrap_watermark_missing"
