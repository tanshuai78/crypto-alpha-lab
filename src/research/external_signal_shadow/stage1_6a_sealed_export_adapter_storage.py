"""Persistence and independent consumer verification for Stage 1.6A sealed export adapter."""

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter import (
    ARTIFACT_PROFILE_VERSION,
    AdapterInputError,
    AdapterReduction,
    VerifiedSourceSnapshot,
    build_precompletion_summary,
    deterministic_projection_view,
    load_verified_source_snapshot,
    reduce_verified_snapshot,
)

ADAPTER_OUTPUT_PARENT = Path("data/external_signal_shadow/stage1_6a/sealed_export_source_audits")

DERIVED_ARTIFACT_NAMES = [
    "source_export_receipt.json",
    "audit_candidate_manifest.json",
    "parent_audit_outcomes.jsonl",
    "detail_revisions.jsonl",
    "semantic_extractions.jsonl",
    "delisting_notices.jsonl",
    "delisting_contracts.jsonl",
    "audit_diagnostics.jsonl",
    "stage1_6a_futures_delisting_source_audit_summary.json",
]


def _write_atomic_json(target_path: Path, data: Any) -> tuple[str, int]:
    """Atomically write JSON data to file and return (sha256, byte_count)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, sort_keys=True) if isinstance(data, dict) else json.dumps(data)
    content_bytes = serialized.encode("utf-8")
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    byte_count = len(content_bytes)

    temp_fd, temp_path = tempfile.mkstemp(dir=target_path.parent, prefix=".tmp_atomic_")
    with os.fdopen(temp_fd, "wb") as f:
        f.write(content_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, target_path)
    return sha256, byte_count


def _write_atomic_jsonl(target_path: Path, rows: List[Dict[str, Any]]) -> tuple[str, int]:
    """Atomically write JSONL data to file and return (sha256, byte_count)."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows]
    content_bytes = ("\n".join(lines) + "\n" if lines else "").encode("utf-8")
    sha256 = hashlib.sha256(content_bytes).hexdigest()
    byte_count = len(content_bytes)

    temp_fd, temp_path = tempfile.mkstemp(dir=target_path.parent, prefix=".tmp_atomic_")
    with os.fdopen(temp_fd, "wb") as f:
        f.write(content_bytes)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, target_path)
    return sha256, byte_count


def persist_adapter_audit(
    output_root: Path,
    *,
    audit_run_id: str,
    snapshot: VerifiedSourceSnapshot,
    reduction: AdapterReduction,
    semantic_extracted_at_ms: int,
) -> Path:
    """Persists all derived Stage 1.6A artifacts, summary, and atomic completion manifest last."""
    if output_root.exists():
        raise AdapterInputError(f"output_root_already_exists: {output_root}")

    if output_root.name != audit_run_id:
        raise AdapterInputError(f"output_root_basename_mismatch: {output_root.name} != {audit_run_id}")

    output_parent = (snapshot.project_root / ADAPTER_OUTPUT_PARENT).resolve()
    if output_root.resolve().parent != output_parent:
        raise AdapterInputError("output_root_outside_adapter_output_family")

    output_root.mkdir(parents=True, exist_ok=True)

    input_manifest_bytes = snapshot.manifest_bytes
    input_manifest_sha256 = hashlib.sha256(input_manifest_bytes).hexdigest()

    # 1. Build source export receipt
    consumed_tuples = []
    for art in snapshot.manifest.get("authoritative_artifacts", []):
        rel_p = art.get("relative_path", "")
        sha = art.get("sha256", "")
        size = art.get("byte_count", 0)
        art_class = "control" if rel_p.endswith(".json") and not rel_p.startswith("raw_payloads/") else "data"
        consumed_tuples.append({
            "artifact_class": art_class,
            "relative_path": rel_p,
            "sha256": sha,
            "byte_length": size,
        })
    consumed_tuples.sort(key=lambda x: (x["artifact_class"], x["relative_path"], x["sha256"]))

    receipt_dict = {
        "schema_version": "stage1_6a_source_export_receipt_v1",
        "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
        "input_export_id": snapshot.export_id,
        "input_manifest_sha256": input_manifest_sha256,
        "capture_mode": "historical_backfill",
        "source_profile_id": snapshot.manifest.get("source_profile_id", ""),
        "historical_range_from_ms": snapshot.manifest.get("historical_range_from_ms"),
        "historical_range_to_ms": snapshot.manifest.get("historical_range_to_ms"),
        "historical_coverage_sha256": snapshot.manifest.get("historical_coverage_sha256"),
        "capture_run_contract_sha256": hashlib.sha256(snapshot.artifact_bytes["capture_run_contract.json"]).hexdigest(),
        "source_profile_probe_attestation_sha256": hashlib.sha256(snapshot.artifact_bytes["source_profile_probe_attestation.json"]).hexdigest(),
        "consumed_artifacts": consumed_tuples,
    }

    authoritative_meta: Dict[str, tuple[str, int]] = {}

    # Write receipt
    receipt_sha, receipt_bytes = _write_atomic_json(output_root / "source_export_receipt.json", receipt_dict)
    authoritative_meta["source_export_receipt.json"] = (receipt_sha, receipt_bytes)

    # Write candidate manifest
    cand_sha, cand_bytes = _write_atomic_json(output_root / "audit_candidate_manifest.json", reduction.candidate_manifest)
    authoritative_meta["audit_candidate_manifest.json"] = (cand_sha, cand_bytes)

    # Write JSONL artifacts
    po_sha, po_bytes = _write_atomic_jsonl(output_root / "parent_audit_outcomes.jsonl", list(reduction.parent_outcomes))
    authoritative_meta["parent_audit_outcomes.jsonl"] = (po_sha, po_bytes)

    rev_sha, rev_bytes = _write_atomic_jsonl(output_root / "detail_revisions.jsonl", list(reduction.detail_revision_projection))
    authoritative_meta["detail_revisions.jsonl"] = (rev_sha, rev_bytes)

    sem_sha, sem_bytes = _write_atomic_jsonl(output_root / "semantic_extractions.jsonl", list(reduction.semantic_extractions))
    authoritative_meta["semantic_extractions.jsonl"] = (sem_sha, sem_bytes)

    not_sha, not_bytes = _write_atomic_jsonl(output_root / "delisting_notices.jsonl", list(reduction.notices))
    authoritative_meta["delisting_notices.jsonl"] = (not_sha, not_bytes)

    con_sha, con_bytes = _write_atomic_jsonl(output_root / "delisting_contracts.jsonl", list(reduction.contracts))
    authoritative_meta["delisting_contracts.jsonl"] = (con_sha, con_bytes)

    diag_sha, diag_bytes = _write_atomic_jsonl(output_root / "audit_diagnostics.jsonl", list(reduction.diagnostics))
    authoritative_meta["audit_diagnostics.jsonl"] = (diag_sha, diag_bytes)

    # Build and write summary
    summary_dict = build_precompletion_summary(
        reduction,
        audit_run_id=audit_run_id,
        source_export_receipt_sha256=receipt_sha,
        candidate_manifest_sha256=cand_sha,
    )
    sum_sha, sum_bytes = _write_atomic_json(output_root / "stage1_6a_futures_delisting_source_audit_summary.json", summary_dict)
    authoritative_meta["stage1_6a_futures_delisting_source_audit_summary.json"] = (sum_sha, sum_bytes)

    # Prepare authoritative artifacts list for completion manifest
    auth_artifacts = []
    for rel_name in DERIVED_ARTIFACT_NAMES:
        sha, size = authoritative_meta[rel_name]
        auth_artifacts.append({
            "relative_path": rel_name,
            "sha256": sha,
            "byte_length": size,
        })
    auth_artifacts.sort(key=lambda x: (x["relative_path"], x["sha256"]))

    passed = summary_dict["source_audit_evidence_candidate_passed"]
    allowed_action = "write_live_source_observation_design_only" if passed else "source_audit_failed_or_inconclusive"
    permitted_options = [
        "write_live_source_observation_design_only",
        "write_ex_post_diagnostic_design_only",
    ] if passed else []

    completion_manifest_dict = {
        "schema_version": "stage1_6a_source_audit_completion_manifest_v1",
        "artifact_profile_version": ARTIFACT_PROFILE_VERSION,
        "audit_run_id": audit_run_id,
        "status": "complete",
        "input_export_id": snapshot.export_id,
        "input_manifest_sha256": input_manifest_sha256,
        "audit_metric_definition_version": summary_dict["audit_metric_definition_version"],
        "body_normalization_version": summary_dict["body_normalization_version"],
        "semantic_extractor_version": summary_dict["semantic_extractor_version"],
        "threshold_snapshot": summary_dict["threshold_snapshot"],
        "metrics": summary_dict["metrics"],
        "available_at_policy_defined": summary_dict["available_at_policy_defined"],
        "source_schema_integrity_passed": summary_dict["source_schema_integrity_passed"],
        "sample_sufficiency_passed": summary_dict["sample_sufficiency_passed"],
        "source_audit_evidence_candidate_passed": passed,
        "source_export_receipt_sha256": receipt_sha,
        "source_audit_passed": passed,
        "allowed_next_action": allowed_action,
        "permitted_design_options": permitted_options,
        "authoritative_artifacts": auth_artifacts,
        "authority_flags": summary_dict["authority_flags"],
        "completed_at_ms": int(time.time() * 1000),
    }

    # Write completion manifest LAST
    _write_atomic_json(output_root / "completion_manifest.json", completion_manifest_dict)
    return output_root / "completion_manifest.json"


def load_completed_adapter_audit(
    project_root: Path,
    output_root: Path,
    source_export: Path,
) -> Dict[str, Any]:
    """
    Independent consumer verification: verifies hashes, re-reduces source bytes,
    and exact-compares all derived artifacts and metric populations.
    """
    root = project_root.resolve(strict=True)
    out_root = output_root.resolve(strict=True)

    manifest_p = out_root / "completion_manifest.json"
    if not manifest_p.is_file():
        raise AdapterInputError(f"completion_manifest_missing in {out_root}")

    try:
        manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdapterInputError(f"malformed_completion_manifest: {exc}") from exc

    if manifest_data.get("status") != "complete":
        raise AdapterInputError("completion_manifest_status_not_complete")

    if manifest_data.get("schema_version") != "stage1_6a_source_audit_completion_manifest_v1":
        raise AdapterInputError("completion_manifest_schema_invalid")

    if manifest_data.get("artifact_profile_version") != ARTIFACT_PROFILE_VERSION:
        raise AdapterInputError("completion_manifest_profile_invalid")

    # 1. Verify all listed authoritative artifacts on disk
    artifacts = manifest_data.get("authoritative_artifacts", [])
    if not artifacts:
        raise AdapterInputError("completion_manifest_has_zero_artifacts")

    persisted_bytes: Dict[str, bytes] = {}
    for art in artifacts:
        rel_p = art.get("relative_path", "")
        expected_sha = art.get("sha256", "")
        expected_size = art.get("byte_length", 0)

        file_p = out_root / rel_p
        if not file_p.is_file():
            raise AdapterInputError(f"missing_authoritative_artifact: {rel_p}")
        data = file_p.read_bytes()
        if len(data) != expected_size:
            raise AdapterInputError(f"artifact_size_mismatch: {rel_p}")
        if hashlib.sha256(data).hexdigest() != expected_sha:
            raise AdapterInputError(f"artifact_hash_mismatch: {rel_p}")
        persisted_bytes[rel_p] = data

    # 2. Check summary pre-completion state
    summary_data = json.loads(persisted_bytes["stage1_6a_futures_delisting_source_audit_summary.json"].decode("utf-8"))
    receipt_data = json.loads(persisted_bytes["source_export_receipt.json"].decode("utf-8"))
    expected_receipt_keys = {
        "schema_version", "artifact_profile_version", "input_export_id", "input_manifest_sha256",
        "capture_mode", "source_profile_id", "historical_range_from_ms", "historical_range_to_ms",
        "historical_coverage_sha256", "capture_run_contract_sha256",
        "source_profile_probe_attestation_sha256", "consumed_artifacts",
    }
    if set(receipt_data) != expected_receipt_keys or receipt_data.get("schema_version") != "stage1_6a_source_export_receipt_v1":
        raise AdapterInputError("receipt_exact_schema_invalid")
    expected_summary_keys = {
        "schema_version", "artifact_profile_version", "audit_run_id", "source_export_receipt_sha256",
        "input_export_id", "input_manifest_sha256", "audit_metric_definition_version",
        "candidate_discovery_rule_version", "audit_candidate_manifest_sha256",
        "body_normalization_version", "semantic_extractor_version", "threshold_snapshot", "metrics",
        "available_at_policy_defined", "source_schema_integrity_passed", "sample_sufficiency_passed",
        "source_audit_evidence_candidate_passed", "audit_summary_state", "source_audit_passed",
        "allowed_next_action", "permitted_design_options", "authority_flags",
    }
    expected_completion_keys = {
        "schema_version", "artifact_profile_version", "status", "audit_run_id",
        "source_export_receipt_sha256", "input_export_id", "input_manifest_sha256",
        "audit_metric_definition_version", "body_normalization_version", "semantic_extractor_version",
        "threshold_snapshot", "metrics", "available_at_policy_defined",
        "source_schema_integrity_passed", "sample_sufficiency_passed",
        "source_audit_evidence_candidate_passed", "source_audit_passed", "allowed_next_action",
        "permitted_design_options", "authority_flags", "authoritative_artifacts", "completed_at_ms",
    }
    if set(manifest_data) != expected_completion_keys:
        raise AdapterInputError("completion_manifest_exact_schema_invalid")
    if set(summary_data) != expected_summary_keys or summary_data.get("schema_version") != "stage1_6a_source_audit_summary_v1":
        raise AdapterInputError("summary_exact_schema_invalid")
    if summary_data.get("audit_summary_state") != "pre_completion":
        raise AdapterInputError("summary_state_not_pre_completion")
    if summary_data.get("source_audit_passed") is not False:
        raise AdapterInputError("precompletion_summary_must_have_source_audit_passed_false")
    if "status" in summary_data and summary_data.get("status") == "complete":
        raise AdapterInputError("precompletion_summary_must_not_claim_complete")

    # 3. Check authority flags in completion manifest
    expected_flag_names = {
        "RISK_LIVE_TRADING_ENABLED", "trade_signal_allowed", "paper_trading_allowed",
        "live_trading_allowed", "execution_engine_allowed", "alpha_interpretation_allowed",
        "execution_feasibility_claim_allowed", "risk_veto_candidate", "replay_allowed",
        "point_in_time_directional_replay_allowed", "point_in_time_source_validated",
        "market_data_coverage_passed",
    }
    if set(manifest_data.get("authority_flags", {})) != expected_flag_names or any(
        value is not False for value in manifest_data["authority_flags"].values()
    ):
        raise AdapterInputError("authority_flags_exact_false_required")

    # 4. Load source snapshot and re-reduce
    snapshot = load_verified_source_snapshot(root, source_export)
    if snapshot.export_id != manifest_data.get("input_export_id"):
        raise AdapterInputError("input_export_id_mismatch")
    expected_manifest_sha = hashlib.sha256(snapshot.manifest_bytes).hexdigest()
    if any(value != expected_manifest_sha for value in (
        manifest_data.get("input_manifest_sha256"), receipt_data.get("input_manifest_sha256"),
    )):
        raise AdapterInputError("input_manifest_sha256_mismatch")
    if manifest_data.get("source_export_receipt_sha256") != hashlib.sha256(
        persisted_bytes["source_export_receipt.json"]
    ).hexdigest():
        raise AdapterInputError("source_export_receipt_sha256_mismatch")
    if (
        receipt_data.get("input_export_id") != snapshot.export_id
        or receipt_data.get("capture_mode") != "historical_backfill"
        or receipt_data.get("source_profile_id") != snapshot.manifest.get("source_profile_id")
        or receipt_data.get("historical_range_from_ms") != snapshot.manifest.get("historical_range_from_ms")
        or receipt_data.get("historical_range_to_ms") != snapshot.manifest.get("historical_range_to_ms")
        or receipt_data.get("historical_coverage_sha256") != snapshot.manifest.get("historical_coverage_sha256")
        or receipt_data.get("capture_run_contract_sha256") != hashlib.sha256(snapshot.artifact_bytes["capture_run_contract.json"]).hexdigest()
        or receipt_data.get("source_profile_probe_attestation_sha256") != hashlib.sha256(snapshot.artifact_bytes["source_profile_probe_attestation.json"]).hexdigest()
    ):
        raise AdapterInputError("receipt_source_binding_mismatch")

    rebuilt_reduction = reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000000000)

    # 5. Exact comparison of derived projections using deterministic_projection_view
    persisted_manifest = json.loads(persisted_bytes["audit_candidate_manifest.json"].decode("utf-8"))
    if deterministic_projection_view(persisted_manifest) != deterministic_projection_view(rebuilt_reduction.candidate_manifest):
        raise AdapterInputError("candidate_manifest_projection_mismatch")

    def _load_jsonl(raw: bytes) -> List[Dict[str, Any]]:
        return [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]

    persisted_outcomes = _load_jsonl(persisted_bytes["parent_audit_outcomes.jsonl"])
    if deterministic_projection_view(persisted_outcomes) != deterministic_projection_view(list(rebuilt_reduction.parent_outcomes)):
        raise AdapterInputError("parent_outcomes_projection_mismatch")

    persisted_revisions = _load_jsonl(persisted_bytes["detail_revisions.jsonl"])
    if deterministic_projection_view(persisted_revisions) != deterministic_projection_view(list(rebuilt_reduction.detail_revision_projection)):
        raise AdapterInputError("detail_revisions_projection_mismatch")

    persisted_extractions = _load_jsonl(persisted_bytes["semantic_extractions.jsonl"])
    if deterministic_projection_view(persisted_extractions) != deterministic_projection_view(list(rebuilt_reduction.semantic_extractions)):
        raise AdapterInputError("semantic_extractions_projection_mismatch")

    persisted_notices = _load_jsonl(persisted_bytes["delisting_notices.jsonl"])
    if deterministic_projection_view(persisted_notices) != deterministic_projection_view(list(rebuilt_reduction.notices)):
        raise AdapterInputError("delisting_notices_projection_mismatch")

    persisted_contracts = _load_jsonl(persisted_bytes["delisting_contracts.jsonl"])
    if deterministic_projection_view(persisted_contracts) != deterministic_projection_view(list(rebuilt_reduction.contracts)):
        raise AdapterInputError("delisting_contracts_projection_mismatch")

    persisted_diagnostics = _load_jsonl(persisted_bytes["audit_diagnostics.jsonl"])
    if deterministic_projection_view(persisted_diagnostics) != deterministic_projection_view(list(rebuilt_reduction.diagnostics)):
        raise AdapterInputError("audit_diagnostics_projection_mismatch")

    # 6. Rebuild summary and compare
    rebuilt_summary = build_precompletion_summary(
        rebuilt_reduction,
        audit_run_id=manifest_data.get("audit_run_id", ""),
        source_export_receipt_sha256=manifest_data.get("source_export_receipt_sha256", ""),
        candidate_manifest_sha256=hashlib.sha256(persisted_bytes["audit_candidate_manifest.json"]).hexdigest(),
    )

    if deterministic_projection_view(summary_data) != deterministic_projection_view(rebuilt_summary):
        raise AdapterInputError("summary_projection_mismatch")

    expected_passed = rebuilt_summary["source_audit_evidence_candidate_passed"]
    if manifest_data.get("source_audit_passed") != expected_passed:
        raise AdapterInputError("completion_manifest_source_audit_passed_mismatch")

    expected_action = "write_live_source_observation_design_only" if expected_passed else "source_audit_failed_or_inconclusive"
    if manifest_data.get("allowed_next_action") != expected_action:
        raise AdapterInputError("completion_manifest_allowed_next_action_mismatch")

    expected_options = [
        "write_live_source_observation_design_only",
        "write_ex_post_diagnostic_design_only",
    ] if expected_passed else []
    if manifest_data.get("permitted_design_options") != expected_options:
        raise AdapterInputError("completion_manifest_permitted_options_mismatch")

    return {
        "completion_manifest": manifest_data,
        "summary": summary_data,
        "receipt": receipt_data,
    }
