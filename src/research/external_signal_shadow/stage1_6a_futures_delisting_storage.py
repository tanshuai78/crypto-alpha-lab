"""
Stage 1.6A USD-M Futures Delisting Isolated Persistence and Completion Manifest Storage Engine.
Design Reference: docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md
"""

import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SUMMARY_FILENAME = "stage1_6a_futures_delisting_source_audit_summary.json"
COMPLETION_MANIFEST_FILENAME = "completion_manifest.json"
STAGE1_6A_OUTPUT_PARENT = Path("data/external_signal_shadow/stage1_6a").resolve()
REQUIRED_ARTIFACT_FILENAMES = (
    "capture_bundle.jsonl",
    "audit_candidate_manifest.json",
    "detail_revisions.jsonl",
    "semantic_extractions.jsonl",
    "delisting_notices.jsonl",
    "delisting_contracts.jsonl",
    "audit_diagnostics.jsonl",
    SUMMARY_FILENAME,
)


def validate_output_root_path(output_root: Path, *, require_new: bool = True) -> Path:
    """Validates a Stage 1.6A-only output root and optionally requires it to be new."""
    resolved = output_root.resolve()
    if resolved == STAGE1_6A_OUTPUT_PARENT or not resolved.is_relative_to(STAGE1_6A_OUTPUT_PARENT):
        raise ValueError(f"Output root must be a descendant of Stage 1.6A output parent: {STAGE1_6A_OUTPUT_PARENT}")
    if require_new and resolved.exists():
        raise ValueError(f"Output root already exists; a new descendant is required: {resolved}")
    return resolved


def compute_file_sha256(file_path: Path) -> str:
    """Computes SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def write_atomic_json(target_path: Path, data: Any) -> str:
    """Writes a JSON file atomically using a temporary file in the same directory."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target_path.with_name(f"{target_path.name}.tmp_{tempfile.mktemp(dir='')}")
    raw_str = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)
    temp_file.write_text(raw_str, encoding="utf-8")
    temp_file.replace(target_path)
    return compute_file_sha256(target_path)


def write_append_jsonl(target_path: Path, rows: List[Dict[str, Any]]) -> str:
    """Writes rows to a JSONL file atomically."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target_path.with_name(f"{target_path.name}.tmp_{tempfile.mktemp(dir='')}")
    with open(temp_file, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
    temp_file.replace(target_path)
    return compute_file_sha256(target_path)


def write_atomic_bytes(target_path: Path, data: bytes) -> str:
    """Persists raw capture bytes without reserializing their evidence representation."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target_path.with_name(f"{target_path.name}.tmp_{tempfile.mktemp(dir='')}")
    temp_file.write_bytes(data)
    temp_file.replace(target_path)
    return compute_file_sha256(target_path)


def persist_audit_artifacts(
    output_root: Path,
    audit_result: Dict[str, Any],
    summary_dict: Dict[str, Any],
    capture_bundle_bytes: bytes,
    run_id: Optional[str] = None,
) -> Path:
    """
    Persists all Stage 1.6A audit artifacts into output_root with a 2-stage commit:
    1. Write artifacts and pre-completion summary.
    2. Write completion_manifest.json with all component hashes.
    """
    output_root = validate_output_root_path(output_root)
    output_root.mkdir(parents=True, exist_ok=False)

    if not run_id:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    manifest = audit_result["manifest"]
    detail_revisions = audit_result.get("detail_revisions", [])
    semantic_extractions = audit_result.get("semantic_extractions", [])
    notices = audit_result.get("notices", [])
    contracts = audit_result.get("contracts", [])

    artifact_hashes: Dict[str, str] = {}

    # 1. Immutable input capture
    capture_path = output_root / "capture_bundle.jsonl"
    artifact_hashes["capture_bundle.jsonl"] = write_atomic_bytes(capture_path, capture_bundle_bytes)

    # 2. Manifest
    manifest_path = output_root / "audit_candidate_manifest.json"
    artifact_hashes["audit_candidate_manifest.json"] = write_atomic_json(manifest_path, manifest.to_dict())

    # 3. Detail Revisions JSONL
    revisions_path = output_root / "detail_revisions.jsonl"
    artifact_hashes["detail_revisions.jsonl"] = write_append_jsonl(revisions_path, detail_revisions)

    # 4. Semantic Extractions JSONL
    extractions_path = output_root / "semantic_extractions.jsonl"
    artifact_hashes["semantic_extractions.jsonl"] = write_append_jsonl(extractions_path, semantic_extractions)

    # 5. Delisting Notices JSONL
    notices_path = output_root / "delisting_notices.jsonl"
    artifact_hashes["delisting_notices.jsonl"] = write_append_jsonl(notices_path, notices)

    # 6. Delisting Contracts JSONL
    contracts_path = output_root / "delisting_contracts.jsonl"
    contract_rows = [c.to_dict() for c in contracts]
    artifact_hashes["delisting_contracts.jsonl"] = write_append_jsonl(contracts_path, contract_rows)

    # 7. Diagnostic-only reducer outcome
    diagnostics_path = output_root / "audit_diagnostics.jsonl"
    artifact_hashes["audit_diagnostics.jsonl"] = write_append_jsonl(
        diagnostics_path,
        [{"metrics_raw": audit_result["metrics_raw"], "diagnostic_scope": "fixture_historical_contract_only"}],
    )

    # 8. Summary (with pre_completion state)
    summary_copy = dict(summary_dict)
    summary_copy["audit_summary_state"] = "pre_completion"
    summary_path = output_root / SUMMARY_FILENAME
    artifact_hashes[SUMMARY_FILENAME] = write_atomic_json(summary_path, summary_copy)

    if set(artifact_hashes) != set(REQUIRED_ARTIFACT_FILENAMES):
        raise ValueError("Internal error: incomplete authoritative artifact hash set")

    # 9. Write completion_manifest.json LAST
    bundle_sha256 = hashlib.sha256(capture_bundle_bytes).hexdigest()
    completion_manifest = {
        "status": "complete",
        "run_id": run_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "capture_bundle_sha256": bundle_sha256,
        "candidate_manifest_sha256": artifact_hashes["audit_candidate_manifest.json"],
        "summary_sha256": artifact_hashes[SUMMARY_FILENAME],
        "artifact_hashes": artifact_hashes,
        "counts": {
            "candidate_count": len(manifest.items),
            "notice_count": len(notices),
            "contract_count": len(contracts),
            "eligible_contract_count": sum(1 for c in contracts if c.source_audit_eligible),
            "authoritative_artifact_count": len(artifact_hashes),
        },
    }

    completion_path = output_root / COMPLETION_MANIFEST_FILENAME
    write_atomic_json(completion_path, completion_manifest)

    return completion_path


def load_completed_audit(output_root: Path) -> Dict[str, Any]:
    """
    Loads a completed audit root, verifying completion_manifest.json and all artifact SHA-256 hashes.
    Raises ValueError if root is partial, crashed, missing, or corrupted.
    """
    output_root = validate_output_root_path(output_root, require_new=False)
    completion_path = output_root / COMPLETION_MANIFEST_FILENAME
    if not completion_path.exists():
        raise ValueError(f"Incomplete or unverified audit root (missing {COMPLETION_MANIFEST_FILENAME}): {output_root}")

    try:
        manifest_data = json.loads(completion_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Malformed {COMPLETION_MANIFEST_FILENAME}: {e}")

    if manifest_data.get("status") != "complete":
        raise ValueError(f"Audit root status is not complete: {manifest_data.get('status')}")

    recorded_hashes = manifest_data.get("artifact_hashes", {})
    if set(recorded_hashes) != set(REQUIRED_ARTIFACT_FILENAMES):
        raise ValueError("Completion manifest artifact hash set is incomplete or unexpected")
    if manifest_data.get("candidate_manifest_sha256") != recorded_hashes["audit_candidate_manifest.json"]:
        raise ValueError("Completion manifest candidate_manifest_sha256 does not match artifact hash")
    if manifest_data.get("summary_sha256") != recorded_hashes[SUMMARY_FILENAME]:
        raise ValueError("Completion manifest summary_sha256 does not match artifact hash")
    for filename, expected_hash in recorded_hashes.items():
        file_path = output_root / filename
        if not file_path.exists():
            raise ValueError(f"Missing artifact {filename} in {output_root}")
        actual_hash = compute_file_sha256(file_path)
        if actual_hash != expected_hash:
            raise ValueError(f"Hash mismatch for {filename}: expected {expected_hash}, got {actual_hash}")

    summary_path = output_root / SUMMARY_FILENAME
    summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary_data.get("audit_summary_state") != "pre_completion" or summary_data.get("status") == "complete":
        raise ValueError("Summary cannot claim authoritative completion")

    return {
        "completion_manifest": manifest_data,
        "summary": summary_data,
    }
