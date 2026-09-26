"""Stage 1.6F-W2-0 immutable bundle writer and strict reader.

Invariants:
- INV-W20-07: Output is create-exclusive, atomic, fsynced, readback verified, and manifest-last.
- INV-W20-08: bundle authority_flags must be exact 20-field false superset.
- Zero-permission boundary: RISK_LIVE_TRADING_ENABLED = False.
- Strictly offline, descriptive transformations only. No raw prices, no OHLC, no PnL.
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from src.research.external_signal_shadow.stage1_6f_w2_0_exploratory_terminal_basis_diagnostic import (
    FROZEN_20_FALSE_FLAGS,
    W20Admission,
    W20DiagnosticResult,
)
from src.research.external_signal_shadow.stage1_6f_w2_evidence_source import (
    VerifiedW2Evidence,
)

DENOMINATOR_FILENAME = "stage1_6f_w2_0_denominator.jsonl"
CONTRACT_METRICS_FILENAME = "stage1_6f_w2_0_contract_metrics.jsonl"
PARENT_METRICS_FILENAME = "stage1_6f_w2_0_parent_metrics.jsonl"
SUMMARY_FILENAME = "stage1_6f_w2_0_summary.json"
MANIFEST_FILENAME = "stage1_6f_w2_0_bundle_manifest.json"

EXPECTED_OUTPUT_FILENAMES: Set[str] = {
    DENOMINATOR_FILENAME,
    CONTRACT_METRICS_FILENAME,
    PARENT_METRICS_FILENAME,
    SUMMARY_FILENAME,
    MANIFEST_FILENAME,
}

NON_MANIFEST_ARTIFACTS: Tuple[str, ...] = (
    DENOMINATOR_FILENAME,
    CONTRACT_METRICS_FILENAME,
    PARENT_METRICS_FILENAME,
    SUMMARY_FILENAME,
)

MANIFEST_SCHEMA_VERSION = "stage1_6f_w2_0_exploratory_bundle_manifest_v1"
SUMMARY_SCHEMA_VERSION = "stage1_6f_w2_0_summary_v1"
BUNDLE_STATE_AT_WRITE = "sealed_valid_at_write"

EXPECTED_AUTHORITY_KEYS: Set[str] = {
    "w2_0_design",
    "w2_0_plan",
    "w2_design",
    "w2_plan",
    "w2_network_auth",
    "w2_candidate_manifest",
    "external_audit",
    "historical_receipt",
}

FORBIDDEN_RAW_KEYS: Set[str] = {
    "close",
    "open",
    "high",
    "low",
    "volume",
    "quote_volume",
    "pnl",
    "return",
    "perp_close",
    "index_close",
    "mark_close",
    "funding",
    "trade_signal",
    "alpha_candidate",
    "alpha_validated",
    "position_size",
}


class W20StorageError(Exception):
    """Exception raised when W2-0 bundle writing or strict reading fails."""
    pass


def _reject_constant(constant: str) -> None:
    raise W20StorageError(f"STOP=w2_0_bundle_invalid:nonfinite_constant:{constant}")


def _strict_json_object_pairs_hook(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    d: Dict[str, Any] = {}
    for k, v in pairs:
        if k in d:
            raise W20StorageError(f"STOP=w2_0_bundle_invalid:duplicate_json_key:{k}")
        d[k] = v
    return d


def parse_strict_json(raw_bytes: bytes) -> Any:
    """Parse JSON enforcing duplicate key rejection and nonfinite constant rejection."""
    try:
        text = raw_bytes.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=_strict_json_object_pairs_hook,
            parse_constant=_reject_constant,
        )
    except W20StorageError:
        raise
    except Exception as exc:
        raise W20StorageError(f"STOP=w2_0_bundle_invalid:json_decode_error:{exc}") from exc


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize object to canonical UTF-8 bytes with sorted keys and no trailing space."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")


def canonical_json_line(obj: Any) -> str:
    """Serialize object to single canonical JSON line without newlines."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def check_for_forbidden_keys(obj: Any, path: str = "") -> None:
    """Recursively search for forbidden raw price, OHLC, PnL or signal keys."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_RAW_KEYS:
                raise W20StorageError(f"STOP=w2_0_bundle_invalid:forbidden_field_detected:{k} at {path}")
            check_for_forbidden_keys(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, (list, tuple)):
        for idx, item in enumerate(obj):
            check_for_forbidden_keys(item, f"{path}[{idx}]")


@dataclass(frozen=True)
class VerifiedW20Bundle:
    bundle_run_id: str
    bundle_root: Path
    outcome_inspection_status: str
    research_classification: str
    metric_evidence_status: Dict[str, str]
    authority_packet: Dict[str, Any]
    conserved_counts: Dict[str, int]
    artifacts: Dict[str, Any]
    authority_flags: Dict[str, bool]
    denominator_records: Tuple[Dict[str, Any], ...]
    contract_records: Tuple[Dict[str, Any], ...]
    parent_records: Tuple[Dict[str, Any], ...]
    summary: Dict[str, Any]


def write_w2_0_exploratory_bundle(
    *,
    output_root: Path,
    diagnostic_result: W20DiagnosticResult,
    verified_w2: VerifiedW2Evidence,
    admission: W20Admission,
) -> Path:
    """Atomically writes an immutable sealed W2-0 exploratory diagnostic bundle."""
    # 1. Output directory validation
    if output_root.is_symlink() or (output_root.exists() and not output_root.is_dir()):
        raise W20StorageError(f"STOP=w2_0_output_root_collision:symlink_or_existing_file:{output_root}")
    if output_root.exists():
        raise W20StorageError(f"STOP=w2_0_output_root_collision:{output_root}")

    run_id = output_root.name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id):
        raise W20StorageError(f"STOP=w2_0_output_root_invalid:invalid_run_id_format:{run_id}")

    output_root.mkdir(parents=True, exist_ok=False)

    temp_files: List[Path] = []
    try:
        # 2. Prepare Denominator bytes (JSONL: 41 records)
        denom_records = list(verified_w2.denominator_records)
        denom_lines = [canonical_json_line(r) for r in denom_records]
        denom_bytes = ("\n".join(denom_lines) + "\n").encode("utf-8")

        # 3. Prepare Contract metrics bytes (JSONL: 41 records)
        contract_records = [dataclasses.asdict(r) for r in diagnostic_result.contract_records]
        contract_lines = [canonical_json_line(r) for r in contract_records]
        contract_bytes = ("\n".join(contract_lines) + "\n").encode("utf-8")

        # 4. Prepare Parent metrics bytes (JSONL: 27 records)
        parent_records = [dataclasses.asdict(r) for r in diagnostic_result.parent_records]
        parent_lines = [canonical_json_line(r) for r in parent_records]
        parent_bytes = ("\n".join(parent_lines) + "\n").encode("utf-8")

        # 5. Prepare Summary bytes (JSON)
        perp_status = diagnostic_result.summary.perp_index_summary.metric_evidence_status
        mark_status = diagnostic_result.summary.mark_index_summary.metric_evidence_status
        metric_evidence_status = {
            "perp_index_basis": perp_status,
            "mark_index_basis": mark_status,
        }
        res_class = diagnostic_result.summary.research_classification
        non_indep_notice = diagnostic_result.summary.non_independence_notice

        summary_dict = {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "run_id": admission.candidate_run_id,
            "outcome_inspection_status": "outcome_seen",
            "research_classification": res_class,
            "metric_evidence_status": metric_evidence_status,
            "non_independence_notice": non_indep_notice,
            "conserved_counts": {
                "n_denominator_contracts": diagnostic_result.summary.n_denominator_contracts,
                "n_denominator_parents": diagnostic_result.summary.n_parent_denominator,
                "n_window_defined_contracts": 31,
                "n_window_defined_parents": 21,
                "n_complete_contracts": diagnostic_result.summary.n_contract_exploratory_described,
                "n_complete_parents": diagnostic_result.summary.n_parent_exploratory_described,
            },
            "perp_index_basis": dataclasses.asdict(diagnostic_result.summary.perp_index_summary),
            "mark_index_basis": dataclasses.asdict(diagnostic_result.summary.mark_index_summary),
        }
        check_for_forbidden_keys(summary_dict)
        summary_bytes = canonical_json_bytes(summary_dict)

        # 6. Write the 4 data files to temporary files first
        files_to_write: List[Tuple[str, bytes]] = [
            (DENOMINATOR_FILENAME, denom_bytes),
            (CONTRACT_METRICS_FILENAME, contract_bytes),
            (PARENT_METRICS_FILENAME, parent_bytes),
            (SUMMARY_FILENAME, summary_bytes),
        ]

        verified_artifacts: Dict[str, Dict[str, Any]] = {}
        pending_renames: List[Tuple[Path, Path]] = []

        for filename, content_bytes in files_to_write:
            target_path = output_root / filename
            temp_fd, temp_path_str = tempfile.mkstemp(
                dir=output_root,
                prefix=f".tmp_{filename}_",
            )
            temp_path = Path(temp_path_str)
            temp_files.append(temp_path)

            with os.fdopen(temp_fd, "wb") as f:
                f.write(content_bytes)
                f.flush()
                os.fsync(f.fileno())

            read_bytes = temp_path.read_bytes()
            if len(read_bytes) != len(content_bytes):
                raise W20StorageError(
                    f"STOP=w2_0_bundle_invalid:readback_len_mismatch:{filename}:{len(read_bytes)}!={len(content_bytes)}"
                )
            calc_sha = hashlib.sha256(read_bytes).hexdigest()
            exp_sha = hashlib.sha256(content_bytes).hexdigest()
            if calc_sha != exp_sha:
                raise W20StorageError(
                    f"STOP=w2_0_bundle_invalid:readback_sha_mismatch:{filename}:{calc_sha}!={exp_sha}"
                )

            verified_artifacts[filename] = {
                "relative_path": filename,
                "byte_length": len(content_bytes),
                "sha256": calc_sha,
            }
            pending_renames.append((temp_path, target_path))

        # Rename the 4 data files
        for temp_path, target_path in pending_renames:
            os.replace(temp_path, target_path)

        # 7. Prepare and write Manifest (MANIFEST-LAST invariant)
        manifest_data = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "bundle_run_id": run_id,
            "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "bundle_state_at_write": BUNDLE_STATE_AT_WRITE,
            "outcome_inspection_status": "outcome_seen",
            "research_classification": res_class,
            "metric_evidence_status": metric_evidence_status,
            "authority_packet": {
                "w2_0_design": {
                    "path": str(admission.w2_0_design_path),
                    "sha256": admission.w2_0_design_sha,
                },
                "w2_0_plan": {
                    "path": str(admission.w2_0_plan_path),
                    "sha256": admission.w2_0_plan_sha,
                },
                "w2_design": {
                    "path": str(admission.w2_design_path),
                    "sha256": admission.w2_design_sha,
                },
                "w2_plan": {
                    "path": str(admission.w2_plan_path),
                    "sha256": admission.w2_plan_sha,
                },
                "w2_network_auth": {
                    "path": str(admission.w2_network_auth_path),
                    "sha256": admission.w2_network_auth_sha,
                },
                "w2_candidate_manifest": {
                    "path": str(verified_w2.completed_root / "candidate_manifest.json"),
                    "sha256": admission.candidate_manifest_sha256,
                },
                "external_audit": {
                    "path": str(admission.external_audit_path),
                    "sha256": admission.external_audit_sha256,
                },
                "historical_receipt": {
                    "path": str(admission.historical_receipt_path),
                    "sha256": admission.historical_receipt_sha256,
                },
            },
            "conserved_counts": {
                "n_denominator_contracts": 41,
                "n_denominator_parents": 27,
                "n_window_defined_contracts": 31,
                "n_window_defined_parents": 21,
                "n_complete_contracts": diagnostic_result.summary.n_contract_exploratory_described,
                "n_complete_parents": diagnostic_result.summary.n_parent_exploratory_described,
            },
            "artifacts": verified_artifacts,
            "authority_flags": dict(FROZEN_20_FALSE_FLAGS),
        }

        check_for_forbidden_keys(manifest_data)
        manifest_bytes = canonical_json_bytes(manifest_data)

        manifest_target = output_root / MANIFEST_FILENAME
        manifest_temp_fd, manifest_temp_str = tempfile.mkstemp(
            dir=output_root,
            prefix=f".tmp_{MANIFEST_FILENAME}_",
        )
        manifest_temp = Path(manifest_temp_str)
        temp_files.append(manifest_temp)

        with os.fdopen(manifest_temp_fd, "wb") as f:
            f.write(manifest_bytes)
            f.flush()
            os.fsync(f.fileno())

        read_man_bytes = manifest_temp.read_bytes()
        if len(read_man_bytes) != len(manifest_bytes):
            raise W20StorageError("STOP=w2_0_bundle_invalid:readback_manifest_len_mismatch")
        if hashlib.sha256(read_man_bytes).hexdigest() != hashlib.sha256(manifest_bytes).hexdigest():
            raise W20StorageError("STOP=w2_0_bundle_invalid:readback_manifest_sha_mismatch")

        # Atomic seal: replace manifest LAST
        os.replace(manifest_temp, manifest_target)

        # Directory fsync
        try:
            dir_fd = os.open(str(output_root), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass

        return manifest_target

    except Exception:
        # Clean up any leftover temporary files on failure
        for tf in temp_files:
            if tf.exists():
                try:
                    tf.unlink()
                except OSError:
                    pass
        raise


def load_verified_w2_0_bundle(
    *,
    output_root: Path,
    project_root: Path,
) -> VerifiedW20Bundle:
    """Strict reader and verifier for sealed W2-0 exploratory diagnostic bundle."""
    if output_root.is_symlink() or not output_root.is_dir():
        raise W20StorageError(f"STOP=w2_0_bundle_invalid:output_root_not_directory_or_symlink:{output_root}")

    # 1. Directory entry check: exactly the 5 expected files, no symlinks, no stray files
    entries = sorted(list(output_root.iterdir()))
    for e in entries:
        if e.is_symlink():
            raise W20StorageError(f"STOP=w2_0_bundle_invalid:symlink_entry_detected:{e}")
        if e.name not in EXPECTED_OUTPUT_FILENAMES:
            raise W20StorageError(f"STOP=w2_0_bundle_invalid:unexpected_or_stale_file:{e.name}")

    manifest_path = output_root / MANIFEST_FILENAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise W20StorageError("STOP=w2_0_bundle_invalid:missing_manifest")

    if len(entries) != len(EXPECTED_OUTPUT_FILENAMES):
        raise W20StorageError(
            f"STOP=w2_0_bundle_invalid:file_count_mismatch:{len(entries)}!={len(EXPECTED_OUTPUT_FILENAMES)}"
        )

    # 2. Strict parse manifest
    manifest_bytes = manifest_path.read_bytes()
    manifest_data = parse_strict_json(manifest_bytes)
    check_for_forbidden_keys(manifest_data)

    if manifest_data.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise W20StorageError(f"STOP=w2_0_bundle_invalid:manifest_schema_mismatch:{manifest_data.get('schema_version')}")
    if manifest_data.get("bundle_run_id") != output_root.name:
        raise W20StorageError(f"STOP=w2_0_bundle_invalid:run_id_mismatch:{manifest_data.get('bundle_run_id')}!={output_root.name}")
    if manifest_data.get("outcome_inspection_status") != "outcome_seen":
        raise W20StorageError(
            f"STOP=w2_0_bundle_invalid:outcome_inspection_status:{manifest_data.get('outcome_inspection_status')}"
        )

    res_class = manifest_data.get("research_classification")
    if res_class not in ("exploratory_only", "evidence_insufficient"):
        raise W20StorageError(f"STOP=w2_0_bundle_invalid:invalid_research_classification:{res_class}")

    # 3. Check authority flags: exact 20-field boolean False dictionary
    auth_flags = manifest_data.get("authority_flags")
    if not isinstance(auth_flags, dict) or set(auth_flags.keys()) != set(FROZEN_20_FALSE_FLAGS.keys()):
        raise W20StorageError("STOP=w2_0_bundle_invalid:authority_flags_invalid:keys_mismatch")
    for k, exp_val in FROZEN_20_FALSE_FLAGS.items():
        val = auth_flags.get(k)
        if val is not exp_val or type(val) is not bool:
            raise W20StorageError(f"STOP=w2_0_bundle_invalid:authority_flags_invalid:{k}={val}")

    # 4. Check authority packet against on-disk files
    auth_packet = manifest_data.get("authority_packet")
    if not isinstance(auth_packet, dict) or set(auth_packet.keys()) != EXPECTED_AUTHORITY_KEYS:
        raise W20StorageError(
            f"STOP=w2_0_bundle_invalid:authority_packet_keys_mismatch:{set(auth_packet.keys()) if isinstance(auth_packet, dict) else type(auth_packet)}"
        )
    for auth_key in sorted(EXPECTED_AUTHORITY_KEYS):
        auth_info = auth_packet[auth_key]
        rel_or_abs = auth_info["path"]
        p = Path(rel_or_abs)
        target_file = p if p.is_absolute() else project_root / p
        if not target_file.is_file() or target_file.is_symlink():
            raise W20StorageError(f"STOP=w2_0_bundle_invalid:authority_file_missing_or_symlink:{auth_key}:{target_file}")
        actual_sha = hashlib.sha256(target_file.read_bytes()).hexdigest()
        if actual_sha != auth_info["sha256"]:
            raise W20StorageError(
                f"STOP=w2_0_bundle_invalid:authority_sha_mismatch:{auth_key}:{actual_sha}!={auth_info['sha256']}"
            )

    # 5. Check and read each artifact
    artifacts_map = manifest_data.get("artifacts", {})
    if set(artifacts_map.keys()) != set(NON_MANIFEST_ARTIFACTS):
        raise W20StorageError(f"STOP=w2_0_bundle_invalid:manifest_artifacts_keys_mismatch:{set(artifacts_map.keys())}")

    for filename in NON_MANIFEST_ARTIFACTS:
        file_path = output_root / filename
        meta = artifacts_map[filename]
        raw_bytes = file_path.read_bytes()
        if len(raw_bytes) != meta["byte_length"]:
            raise W20StorageError(
                f"STOP=w2_0_bundle_invalid:byte_length_mismatch:{filename}:{len(raw_bytes)}!={meta['byte_length']}"
            )
        actual_sha = hashlib.sha256(raw_bytes).hexdigest()
        if actual_sha != meta["sha256"]:
            raise W20StorageError(
                f"STOP=w2_0_bundle_invalid:sha256_mismatch:{filename}:{actual_sha}!={meta['sha256']}"
            )

    # Parse and validate individual files
    # Denominator (41 lines)
    denom_raw = (output_root / DENOMINATOR_FILENAME).read_bytes().decode("utf-8")
    denom_lines = [line for line in denom_raw.splitlines() if line]
    if len(denom_lines) != 41:
        raise W20StorageError(f"STOP=w2_0_bundle_invalid:denominator_count_mismatch:{len(denom_lines)}!=41")
    parsed_denom: List[Dict[str, Any]] = []
    for line in denom_lines:
        rec = parse_strict_json(line.encode("utf-8"))
        check_for_forbidden_keys(rec)
        parsed_denom.append(rec)

    # Contract metrics (41 lines)
    contract_raw = (output_root / CONTRACT_METRICS_FILENAME).read_bytes().decode("utf-8")
    contract_lines = [line for line in contract_raw.splitlines() if line]
    if len(contract_lines) != 41:
        raise W20StorageError(f"STOP=w2_0_bundle_invalid:contract_count_mismatch:{len(contract_lines)}!=41")
    parsed_contracts: List[Dict[str, Any]] = []
    for line in contract_lines:
        rec = parse_strict_json(line.encode("utf-8"))
        check_for_forbidden_keys(rec)
        parsed_contracts.append(rec)

    # Parent metrics (27 lines)
    parent_raw = (output_root / PARENT_METRICS_FILENAME).read_bytes().decode("utf-8")
    parent_lines = [line for line in parent_raw.splitlines() if line]
    if len(parent_lines) != 27:
        raise W20StorageError(f"STOP=w2_0_bundle_invalid:parent_count_mismatch:{len(parent_lines)}!=27")
    parsed_parents: List[Dict[str, Any]] = []
    for line in parent_lines:
        rec = parse_strict_json(line.encode("utf-8"))
        check_for_forbidden_keys(rec)
        parsed_parents.append(rec)

    # Summary
    summary_raw = (output_root / SUMMARY_FILENAME).read_bytes()
    summary_dict = parse_strict_json(summary_raw)
    check_for_forbidden_keys(summary_dict)

    return VerifiedW20Bundle(
        bundle_run_id=manifest_data["bundle_run_id"],
        bundle_root=output_root,
        outcome_inspection_status=manifest_data["outcome_inspection_status"],
        research_classification=manifest_data["research_classification"],
        metric_evidence_status=manifest_data["metric_evidence_status"],
        authority_packet=manifest_data["authority_packet"],
        conserved_counts=manifest_data["conserved_counts"],
        artifacts=manifest_data["artifacts"],
        authority_flags=manifest_data["authority_flags"],
        denominator_records=tuple(parsed_denom),
        contract_records=tuple(parsed_contracts),
        parent_records=tuple(parsed_parents),
        summary=summary_dict,
    )
