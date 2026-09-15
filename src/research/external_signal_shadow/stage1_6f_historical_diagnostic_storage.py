"""Stage 1.6F Diagnostic storage: atomic bundle writer and read-only reviewer core."""

import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    ALL_PERMISSION_FLAGS_FALSE,
    DenominatorRow,
    DiagnosticMetricResult,
    compute_window_intervals,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    AUXILIARY_ARTIFACT_SPECS,
    VerifiedCInput,
    VerifiedMarketEvidence,
)


class DiagnosticStorageError(Exception):
    """Raised when bundle storage write or load operations fail."""
    pass


REQUIRED_BUNDLE_NON_MANIFEST_ARTIFACTS: Tuple[str, ...] = (
    "stage1_6f_input_receipt.json",
    "stage1_6f_event_denominator.jsonl",
    "stage1_6f_metric_diagnostics.jsonl",
    "stage1_6f_diagnostic_summary.json",
)

BUNDLE_MANIFEST_FILENAME = "stage1_6f_diagnostic_bundle_manifest.json"
BUNDLE_MANIFEST_SCHEMA_VERSION = "stage1_6f_diagnostic_bundle_manifest_v1"
RECORD_SCHEMA_VERSION = "stage1_6f_historical_mechanism_diagnostic_v1"
VALID_BUNDLE_STATES = ("diagnostic_incomplete", "protocol_executed_complete")


def _write_atomic_bytes(target_path: Path, content: bytes) -> None:
    """Atomically write bytes to file using a temporary file in the same directory."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(dir=target_path.parent, prefix=".tmp_atomic_")
    try:
        with os.fdopen(temp_fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, target_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def _write_atomic_json(target_path: Path, data: Any) -> None:
    serialized = json.dumps(data, indent=2, sort_keys=True)
    _write_atomic_bytes(target_path, serialized.encode("utf-8"))


def _write_atomic_jsonl(target_path: Path, records: List[Dict[str, Any]]) -> None:
    serialized = "\n".join(json.dumps(r, sort_keys=True) for r in records)
    if serialized:
        serialized += "\n"
    _write_atomic_bytes(target_path, serialized.encode("utf-8"))


def write_diagnostic_bundle(
    output_root: Path,
    verified_c: VerifiedCInput,
    verified_market: VerifiedMarketEvidence,
    denominator_rows: List[DenominatorRow],
    diagnostic_metrics: List[DiagnosticMetricResult],
    bundle_state: str = "diagnostic_incomplete",
) -> Path:
    """
    Atomically writes a complete Stage 1.6F diagnostic bundle to output_root.
    1. Rejects if output_root already contains a completed bundle.
    2. Writes non-manifest files atomically.
    3. Reads back each file, measures byte length, and computes SHA-256.
    4. Writes stage1_6f_diagnostic_bundle_manifest.json LAST.
    """
    resolved_root = output_root.resolve()
    manifest_p = resolved_root / BUNDLE_MANIFEST_FILENAME
    if manifest_p.exists():
        raise DiagnosticStorageError("output_root_already_completed: bundle manifest already exists")

    if bundle_state not in VALID_BUNDLE_STATES:
        raise DiagnosticStorageError(f"invalid_bundle_state: {bundle_state}")

    resolved_root.mkdir(parents=True, exist_ok=True)

    # 1. stage1_6f_input_receipt.json
    receipt_data = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "input_export_id": verified_c.input_export_id,
        "input_manifest_sha256": verified_c.input_manifest_sha256,
        "source_export_receipt_sha256": verified_c.source_export_receipt_sha256,
        "c_authoritative_artifacts": list(verified_c.authoritative_artifacts),
        "c_retained_bytes_sha256": verified_c.retained_sha256,
        "market_evidence_manifest_sha256": verified_market.manifest_sha256,
        "market_evidence_manifest_byte_length": verified_market.manifest_byte_length,
        "auxiliary_artifacts": {
            rel: {
                "sha256": AUXILIARY_ARTIFACT_SPECS[rel]["sha256"],
                "byte_length": AUXILIARY_ARTIFACT_SPECS[rel]["byte_length"],
            }
            for rel in sorted(AUXILIARY_ARTIFACT_SPECS.keys())
        },
        "authority_flags": ALL_PERMISSION_FLAGS_FALSE,
    }
    _write_atomic_json(resolved_root / "stage1_6f_input_receipt.json", receipt_data)

    # 2. stage1_6f_event_denominator.jsonl
    denominator_records: List[Dict[str, Any]] = []
    for row in denominator_rows:
        rec = {
            "schema_version": RECORD_SCHEMA_VERSION,
            "input_export_id": verified_c.input_export_id,
            "input_manifest_sha256": verified_c.input_manifest_sha256,
            "source_export_receipt_sha256": verified_c.source_export_receipt_sha256,
            "market_evidence_manifest_sha256": verified_market.manifest_sha256,
            "parent_article_id": row.parent_article_id,
            "contract_id": row.contract_id,
            "symbol": row.symbol,
            "quote_asset": row.quote_asset,
            "settlement_asset": row.settlement_asset,
            "margin_family": row.margin_family,
            "contract_type": row.contract_type,
            "underlying_family": row.underlying_family,
            "eligibility_passed": row.eligibility_passed,
            "ineligibility_reasons": list(row.ineligibility_reasons),
            "t_pub_ms": row.t_pub_ms,
            "t_settle_ms": row.t_settle_ms,
            "system_available_at_ms": None,
            "fact_available_at_ms": None,
            "capture_time_status": "historical_unknown",
            "match_status": row.match_status,
            "selected_controls": list(row.selected_controls),
        }
        rec.update(ALL_PERMISSION_FLAGS_FALSE)
        denominator_records.append(rec)
    _write_atomic_jsonl(resolved_root / "stage1_6f_event_denominator.jsonl", denominator_records)

    # 3. stage1_6f_metric_diagnostics.jsonl
    diagnostic_records: List[Dict[str, Any]] = []
    for m in diagnostic_metrics:
        m_rec = {
            "schema_version": RECORD_SCHEMA_VERSION,
            "input_export_id": verified_c.input_export_id,
            "input_manifest_sha256": verified_c.input_manifest_sha256,
            "source_export_receipt_sha256": verified_c.source_export_receipt_sha256,
            "market_evidence_manifest_sha256": verified_market.manifest_sha256,
            "parent_article_id": m.parent_article_id,
            "contract_id": m.contract_id,
            "symbol": m.symbol,
            "original_interval": m.original_interval,
            "observed_interval": m.observed_interval,
            "controls_or_exclusion_reasons": list(m.controls_or_exclusion_reasons),
            "metric_name": m.metric_name,
            "window": m.window,
            "status": m.status,
            "descriptors": m.descriptors,
        }
        m_rec.update(ALL_PERMISSION_FLAGS_FALSE)
        diagnostic_records.append(m_rec)
    _write_atomic_jsonl(resolved_root / "stage1_6f_metric_diagnostics.jsonl", diagnostic_records)

    # 4. stage1_6f_diagnostic_summary.json
    total_denom = len(denominator_rows)
    eligible_count = sum(1 for r in denominator_rows if r.eligibility_passed)
    ineligible_count = total_denom - eligible_count
    announcements_count = len({r.parent_article_id for r in denominator_rows})
    matched_count = sum(1 for r in denominator_rows if r.match_status == "matched")
    unmatched_count = total_denom - matched_count
    status_counts = dict(Counter(m.status for m in diagnostic_metrics))
    descriptive_only_count = sum(1 for m in diagnostic_metrics if m.status == "descriptive_only")
    unavailable_count = len(diagnostic_metrics) - descriptive_only_count

    summary_data = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "bundle_state": bundle_state,
        "input_export_id": verified_c.input_export_id,
        "input_manifest_sha256": verified_c.input_manifest_sha256,
        "source_export_receipt_sha256": verified_c.source_export_receipt_sha256,
        "market_evidence_manifest_sha256": verified_market.manifest_sha256,
        "counts": {
            "total_denominator_count": total_denom,
            "eligible_count": eligible_count,
            "ineligible_count": ineligible_count,
            "independent_announcements_count": announcements_count,
            "matched_count": matched_count,
            "unmatched_count": unmatched_count,
            "metrics_total_count": len(diagnostic_metrics),
            "metrics_descriptive_only_count": descriptive_only_count,
            "metrics_unavailable_count": unavailable_count,
            "metrics_by_status": status_counts,
        },
        "authority_flags": ALL_PERMISSION_FLAGS_FALSE,
    }
    _write_atomic_json(resolved_root / "stage1_6f_diagnostic_summary.json", summary_data)

    # Read back and hash each non-manifest artifact
    artifacts_meta: List[Dict[str, Any]] = []
    for rel_p in REQUIRED_BUNDLE_NON_MANIFEST_ARTIFACTS:
        file_p = resolved_root / rel_p
        if not file_p.is_file():
            raise DiagnosticStorageError(f"written_artifact_missing_on_readback: {rel_p}")
        data = file_p.read_bytes()
        artifacts_meta.append({
            "relative_path": rel_p,
            "byte_length": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })

    # Sort deterministically
    artifacts_meta.sort(key=lambda a: a["relative_path"])

    # 5. Write manifest LAST
    manifest_data = {
        "schema_version": BUNDLE_MANIFEST_SCHEMA_VERSION,
        "bundle_state": bundle_state,
        "artifacts": artifacts_meta,
        "authority_flags": ALL_PERMISSION_FLAGS_FALSE,
    }
    _write_atomic_json(manifest_p, manifest_data)

    return manifest_p


def load_diagnostic_bundle(output_root: Path) -> Dict[str, Any]:
    """
    Read-only reviewer core for Stage 1.6F diagnostic bundles.
    1. Validates bundle manifest exists, has valid schema and state.
    2. Validates authority_flags are strictly False.
    3. Validates exact required artifacts with matching SHA-256 and byte length.
    4. Validates record-level provenance contract and permission flags in JSON/JSONL.
    """
    resolved_root = output_root.resolve(strict=True)
    manifest_p = resolved_root / BUNDLE_MANIFEST_FILENAME
    if not manifest_p.is_file() or manifest_p.is_symlink():
        raise DiagnosticStorageError("bundle_manifest_missing: completed manifest not found")

    try:
        manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DiagnosticStorageError(f"bundle_manifest_invalid: malformed_manifest: {exc}") from exc

    if manifest.get("schema_version") != BUNDLE_MANIFEST_SCHEMA_VERSION:
        raise DiagnosticStorageError(
            f"bundle_manifest_invalid: schema_mismatch: {manifest.get('schema_version')}"
        )

    bundle_state = manifest.get("bundle_state")
    if bundle_state not in VALID_BUNDLE_STATES:
        raise DiagnosticStorageError(
            f"bundle_manifest_invalid: unknown_bundle_state: {bundle_state}"
        )

    # Authority flags check
    flags = manifest.get("authority_flags", {})
    if set(flags.keys()) != set(ALL_PERMISSION_FLAGS_FALSE.keys()) or any(v is not False for v in flags.values()):
        raise DiagnosticStorageError("permission_or_side_effect_violation: manifest authority flags invalid")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise DiagnosticStorageError("bundle_manifest_invalid: artifacts_not_list")

    seen_rel = set()
    for art in artifacts:
        rel = art.get("relative_path")
        if rel in seen_rel:
            raise DiagnosticStorageError(f"bundle_manifest_invalid: duplicate_artifact: {rel}")
        seen_rel.add(rel)

    if seen_rel != set(REQUIRED_BUNDLE_NON_MANIFEST_ARTIFACTS):
        raise DiagnosticStorageError(
            f"bundle_manifest_invalid: artifact_set_mismatch (missing: {set(REQUIRED_BUNDLE_NON_MANIFEST_ARTIFACTS) - seen_rel}, extra: {seen_rel - set(REQUIRED_BUNDLE_NON_MANIFEST_ARTIFACTS)})"
        )

    # Verify each artifact on disk
    persisted_bytes: Dict[str, bytes] = {}
    for art in artifacts:
        rel = art["relative_path"]
        exp_len = art["byte_length"]
        exp_sha = art["sha256"]

        file_p = resolved_root / rel
        if not file_p.is_file() or file_p.is_symlink():
            raise DiagnosticStorageError(f"missing_bundle_artifact: {rel}")

        data = file_p.read_bytes()
        if len(data) != exp_len:
            raise DiagnosticStorageError(
                f"bundle_artifact_hash_mismatch: byte length mismatch for {rel}: expected {exp_len}, got {len(data)}"
            )
        act_sha = hashlib.sha256(data).hexdigest()
        if act_sha != exp_sha:
            raise DiagnosticStorageError(
                f"bundle_artifact_hash_mismatch: sha256 mismatch for {rel}: expected {exp_sha}, got {act_sha}"
            )
        persisted_bytes[rel] = data

    # Load parsed artifacts
    receipt = json.loads(persisted_bytes["stage1_6f_input_receipt.json"].decode("utf-8"))
    summary = json.loads(persisted_bytes["stage1_6f_diagnostic_summary.json"].decode("utf-8"))

    # Validate receipt and summary authority flags
    for item_name, item_dict in [("receipt", receipt), ("summary", summary)]:
        item_flags = item_dict.get("authority_flags", {})
        if set(item_flags.keys()) != set(ALL_PERMISSION_FLAGS_FALSE.keys()) or any(v is not False for v in item_flags.values()):
            raise DiagnosticStorageError(f"permission_or_side_effect_violation: {item_name} authority flags invalid")

    expected_input_export_id = receipt.get("input_export_id")
    expected_input_manifest_sha = receipt.get("input_manifest_sha256")
    expected_source_receipt_sha = receipt.get("source_export_receipt_sha256")
    expected_market_manifest_sha = receipt.get("market_evidence_manifest_sha256")

    # Validate denominator JSONL records
    denominator_rows: List[Dict[str, Any]] = []
    denom_lines = [line.strip() for line in persisted_bytes["stage1_6f_event_denominator.jsonl"].decode("utf-8").splitlines() if line.strip()]
    for line in denom_lines:
        row = json.loads(line)
        if row.get("schema_version") != RECORD_SCHEMA_VERSION:
            raise DiagnosticStorageError("record_provenance_contract_invalid: schema_version mismatch in denominator")
        if (
            row.get("input_export_id") != expected_input_export_id
            or row.get("input_manifest_sha256") != expected_input_manifest_sha
            or row.get("source_export_receipt_sha256") != expected_source_receipt_sha
            or row.get("market_evidence_manifest_sha256") != expected_market_manifest_sha
        ):
            raise DiagnosticStorageError("record_provenance_contract_invalid: input identity mismatch in denominator row")
        if not row.get("parent_article_id") or not row.get("contract_id") or not row.get("symbol"):
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing linkage identifiers in denominator row")
        for flag_name in ALL_PERMISSION_FLAGS_FALSE:
            if row.get(flag_name) is not False:
                raise DiagnosticStorageError(f"permission_or_side_effect_violation: denominator flag {flag_name} not False")
        denominator_rows.append(row)

    # Map denominator identities to denominator records to enforce exact provenance linkage
    denom_by_identity: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for d in denominator_rows:
        d_key = (d["parent_article_id"], d["contract_id"], d["symbol"])
        denom_by_identity[d_key] = d

    # Validate metric diagnostics JSONL records
    diagnostic_rows: List[Dict[str, Any]] = []
    seen_metric_keys: set = set()
    diag_lines = [line.strip() for line in persisted_bytes["stage1_6f_metric_diagnostics.jsonl"].decode("utf-8").splitlines() if line.strip()]
    for line in diag_lines:
        row = json.loads(line)
        if row.get("schema_version") != RECORD_SCHEMA_VERSION:
            raise DiagnosticStorageError("record_provenance_contract_invalid: schema_version mismatch in diagnostic metric")
        if (
            row.get("input_export_id") != expected_input_export_id
            or row.get("input_manifest_sha256") != expected_input_manifest_sha
            or row.get("source_export_receipt_sha256") != expected_source_receipt_sha
            or row.get("market_evidence_manifest_sha256") != expected_market_manifest_sha
        ):
            raise DiagnosticStorageError("record_provenance_contract_invalid: input identity mismatch in diagnostic metric row")

        parent_id = row.get("parent_article_id")
        contract_id = row.get("contract_id")
        symbol = row.get("symbol")
        if not parent_id or not isinstance(parent_id, str):
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing or invalid parent_article_id in metric row")
        if not contract_id or not isinstance(contract_id, str):
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing or invalid contract_id in metric row")
        if not symbol or not isinstance(symbol, str):
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing or invalid symbol in metric row")

        metric_key = (parent_id, contract_id, symbol)
        if metric_key not in denom_by_identity:
            raise DiagnosticStorageError("record_provenance_contract_invalid: metric row not present in denominator")
        denom_row = denom_by_identity[metric_key]

        metric_window = row.get("window")
        if not metric_window or not isinstance(metric_window, str):
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing or invalid window in metric row")

        # Verify exact original_interval linkage to corresponding denominator row
        if denom_row.get("t_pub_ms") is not None:
            windows = compute_window_intervals(
                t_pub_ms=denom_row["t_pub_ms"],
                t_settle_ms=denom_row.get("t_settle_ms"),
            )
            if metric_window == "W1":
                expected_orig = {
                    "requested_window": "W1",
                    "start_ms": windows["w1_start_ms"],
                    "end_ms": windows["w1_end_ms"],
                }
            elif metric_window == "W2":
                expected_orig = {
                    "requested_window": "W2",
                    "nominal_start_ms": windows["nominal_w2_start_ms"],
                    "nominal_end_ms": windows["nominal_w2_end_ms"],
                    "paired_start_ms": windows["paired_w2_start_ms"],
                    "paired_end_ms": windows["paired_w2_end_ms"],
                    "is_truncated_by_tpub": windows["is_truncated_by_tpub"],
                    "truncation_reason": windows["truncation_reason"],
                }
            else:
                raise DiagnosticStorageError(f"record_provenance_contract_invalid: unrecognized window {metric_window}")
        else:
            expected_orig = {
                "requested_window": metric_window,
                "start_ms": None,
                "end_ms": None,
            }

        orig_int = row.get("original_interval")
        if not isinstance(orig_int, dict) or orig_int != expected_orig:
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing or invalid original_interval in metric row")

        obs_int = row.get("observed_interval")
        if not isinstance(obs_int, dict):
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing or invalid observed_interval in metric row")

        # Verify exact controls_or_exclusion_reasons linkage to corresponding denominator row
        raw_controls = denom_row.get("selected_controls") or []
        ctrl_symbols: List[str] = []
        for c in raw_controls:
            if isinstance(c, dict):
                s = c.get("symbol") or c.get("canonical_symbol")
                if s:
                    ctrl_symbols.append(str(s))
            elif isinstance(c, str) and c:
                ctrl_symbols.append(c)

        if ctrl_symbols:
            expected_controls = ctrl_symbols
        elif denom_row.get("ineligibility_reasons"):
            expected_controls = list(denom_row["ineligibility_reasons"])
        elif denom_row.get("t_pub_ms") is None:
            expected_controls = ["missing_t_pub_ms"]
        else:
            expected_controls = ["unmatched"]

        controls_reasons = row.get("controls_or_exclusion_reasons")
        if not isinstance(controls_reasons, list) or controls_reasons != expected_controls:
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing or invalid controls_or_exclusion_reasons in metric row")

        metric_name = row.get("metric_name")
        if not metric_name or not isinstance(metric_name, str):
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing or invalid metric_name in metric row")

        full_metric_key = (parent_id, contract_id, symbol, metric_name, metric_window)
        if full_metric_key in seen_metric_keys:
            raise DiagnosticStorageError(f"record_provenance_contract_invalid: duplicate metric {full_metric_key}")
        seen_metric_keys.add(full_metric_key)

        status = row.get("status")
        if not status or not isinstance(status, str):
            raise DiagnosticStorageError("record_provenance_contract_invalid: missing or invalid status in metric row")

        for flag_name in ALL_PERMISSION_FLAGS_FALSE:
            if row.get(flag_name) is not False:
                raise DiagnosticStorageError(f"permission_or_side_effect_violation: diagnostic metric flag {flag_name} not False")
        diagnostic_rows.append(row)

    return {
        "manifest": manifest,
        "receipt": receipt,
        "summary": summary,
        "denominator": denominator_rows,
        "diagnostics": diagnostic_rows,
    }
