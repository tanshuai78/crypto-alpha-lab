import json
from pathlib import Path

from configs import base
from src.risk.limits import RiskLimits

STAGE1_5D_RUNTIME_GATE_FILENAME = "live_safety_gate_summary.json"
RUNTIME_GATE_SCHEMA_VERSION = 1

SAFETY_FALSE_FIELDS = (
    "execution_feasibility_claim_allowed",
    "trade_signal_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_engine_allowed",
    "alpha_interpretation_allowed",
)


def get_stage1_5d_runtime_gate_filename() -> str:
    return STAGE1_5D_RUNTIME_GATE_FILENAME


def _decision_to_status(decision: str) -> str:
    return {
        "stage1_5d_runtime_gate_initializing": "INITIALIZING",
        "stage1_5d_runtime_gate_ready": "READY",
        "stage1_5d_runtime_gate_degraded": "DEGRADED",
        "stage1_5d_runtime_gate_stopped": "STOPPED",
        "stage1_5d_runtime_gate_failed": "FAILED",
    }.get(decision, "UNKNOWN")


def _build_not_ready_reasons(context: dict) -> list[str]:
    reasons = []
    if context.get("fixture_run", False):
        reasons.append("fixture_run_active")
    if context.get("source_format_drift_active", False):
        reasons.append("source_format_drift_active")
    if context.get("schema_parse_error_active", False):
        reasons.append("schema_parse_error_active")
    if not context.get("prior_stage_safety_prerequisite_met", True):
        reasons.append("prior_stage_safety_prerequisite_not_met")
    if context.get("fatal_blockers"):
        reasons.append("fatal_blockers_present")
    if int(context.get("successful_poll_count") or 0) < 1:
        reasons.append("successful_poll_count_zero")
    if int(context.get("consecutive_failed_polls") or 0) >= getattr(
        base, "EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_CONSECUTIVE_FAILURES", 3
    ):
        reasons.append("consecutive_failed_polls_exceeded")
    if not context.get("storage_budget_passed", True):
        reasons.append("storage_budget_failed")
    if context.get("detail_endpoint_degraded_active", False):
        reasons.append("detail_endpoint_degraded_active")
    if int(context.get("scheduler_starved_expired_count") or 0) > 0:
        reasons.append("scheduler_starved_expired_count_nonzero")
    if RiskLimits.live_trading_enabled:
        reasons.append("live_trading_enabled_violates_invariant")
    return reasons


def build_stage1_5d_runtime_gate(context: dict | None = None, **kwargs) -> dict:
    ctx = dict(context or {})
    ctx.update(kwargs)

    output_root = Path(ctx.get("output_root") or ".").resolve()
    fatal_blockers = list(ctx.get("fatal_blockers") or [])
    prior_met = bool(ctx.get("prior_stage_safety_prerequisite_met", True))
    successful_polls = int(ctx.get("successful_poll_count") or 0)
    poll_attempts = int(ctx.get("poll_attempt_count") or ctx.get("poll_count") or 0)
    consecutive_failed = int(ctx.get("consecutive_failed_polls") or ctx.get("consecutive_poll_failure_count") or 0)
    max_failures = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_CONSECUTIVE_FAILURES", 3)

    if fatal_blockers:
        decision = "stage1_5d_runtime_gate_failed"
    elif not prior_met or successful_polls < 1:
        decision = "stage1_5d_runtime_gate_initializing"
    elif consecutive_failed >= max_failures:
        decision = "stage1_5d_runtime_gate_degraded"
    elif _build_not_ready_reasons(ctx):
        decision = "stage1_5d_runtime_gate_degraded"
    else:
        decision = "stage1_5d_runtime_gate_ready"

    status = _decision_to_status(decision)
    generated_at_ms = int(ctx.get("generated_at_ms") or ctx.get("now_ms") or 0)
    request_success_rate = None
    if poll_attempts > 0:
        request_success_rate = successful_polls / float(poll_attempts)

    gate = {
        "runtime_gate_schema_version": RUNTIME_GATE_SCHEMA_VERSION,
        "gate_version": RUNTIME_GATE_SCHEMA_VERSION,
        "decision": decision,
        "status": status,
        "consumable_by_stage1_5f": decision == "stage1_5d_runtime_gate_ready",
        "source_root": str(output_root),
        "run_id": str(ctx.get("run_id") or output_root.name),
        "events_stream_relative_path": str(ctx.get("events_stream_relative_path") or "events/*.jsonl"),
        "formal_event_contract_versions_supported": [getattr(base, "EXTERNAL_SIGNAL_STAGE1_5_FORMAL_EVENT_CONTRACT_VERSION", 2)],
        "formal_schedule_revision_contract_versions_supported": [
            getattr(base, "EXTERNAL_SIGNAL_STAGE1_5_FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION", 1)
        ],
        "anchor_precedence_policy": getattr(
            base,
            "EXTERNAL_SIGNAL_STAGE1_5_ANCHOR_PRECEDENCE_POLICY",
            "official_schedule_priority_v1",
        ),
        "shared_anchor_validator_enabled": True,
        "live_public_readonly": bool(ctx.get("live_public_readonly", False)),
        "prior_stage_safety_prerequisite_met": prior_met,
        "not_ready_reasons": _build_not_ready_reasons(ctx),
        "generated_at_ms": generated_at_ms,
        "first_poll_started_at_ms": int(ctx.get("first_poll_started_at_ms") or 0),
        "last_poll_finished_at_ms": int(ctx.get("last_poll_finished_at_ms") or 0),
        "last_heartbeat_at_ms": int(ctx.get("last_heartbeat_at_ms") or ctx.get("last_poll_finished_at_ms") or 0),
        "last_successful_poll_at_ms": int(ctx.get("last_successful_poll_at_ms") or ctx.get("last_poll_finished_at_ms") or 0),
        "poll_attempt_count": poll_attempts,
        "successful_poll_count": successful_polls,
        "failed_poll_count": int(ctx.get("failed_poll_count") or 0),
        "consecutive_failed_polls": consecutive_failed,
        "request_success_rate": request_success_rate,
        "multi_symbol_candidate_set_emission_enabled": bool(ctx.get("multi_symbol_candidate_set_emission_enabled", True)),
        "multi_symbol_candidate_set_ready_count": int(ctx.get("multi_symbol_candidate_set_ready_count") or 0),
        "multi_symbol_candidate_set_pending_count": int(ctx.get("multi_symbol_candidate_set_pending_count") or 0),
        "multi_symbol_full_emit_count": int(ctx.get("multi_symbol_full_emit_count") or 0),
        "multi_symbol_emission_registry_count": int(ctx.get("multi_symbol_emission_registry_count") or 0),
        "live_trading_enabled": bool(RiskLimits.live_trading_enabled),
    }
    for field in SAFETY_FALSE_FIELDS:
        gate[field] = False
    return gate


def write_stage1_5d_runtime_gate_atomic(output_root: str | Path, gate_summary: dict) -> Path:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    gate_file = root / STAGE1_5D_RUNTIME_GATE_FILENAME
    tmp_file = gate_file.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(gate_summary, indent=2, sort_keys=True), encoding="utf-8")
    tmp_file.replace(gate_file)
    return gate_file


def write_stage1_5d_runtime_gate(output_root: str | Path, gate_summary: dict) -> Path:
    return write_stage1_5d_runtime_gate_atomic(output_root, gate_summary)
