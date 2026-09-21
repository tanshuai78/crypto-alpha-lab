"""Stage 1.6F Candidate W1 sealed diagnostic storage and strict loader.

Invariants: INV-CA06 through INV-CA11.
Zero-permission boundary: RISK_LIVE_TRADING_ENABLED = False.
Descriptive transformations only; no signal, alpha, PnL, or execution logic.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import (
    VerifiedCandidateEvidence,
)
from src.research.external_signal_shadow.stage1_6f_candidate_w1_descriptive_diagnostic import (
    DENOMINATOR_SCHEMA_VERSION,
    EXPECTED_19_METRIC_HORIZON_TUPLES,
    HORIZON_MS,
    METRIC_SCHEMA_VERSION,
    CandidateW1DiagnosticResult,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    ALL_PERMISSION_FLAGS_FALSE,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    VerifiedCInput,
)

DENOMINATOR_FILENAME = "stage1_6f_candidate_w1_denominator.jsonl"
METRICS_FILENAME = "stage1_6f_candidate_w1_metrics.jsonl"
SUMMARY_FILENAME = "stage1_6f_candidate_w1_summary.json"
MANIFEST_FILENAME = "stage1_6f_candidate_w1_bundle_manifest.json"

REQUIRED_NON_MANIFEST_ARTIFACTS: Tuple[str, ...] = (
    DENOMINATOR_FILENAME,
    METRICS_FILENAME,
    SUMMARY_FILENAME,
)

EXPECTED_OUTPUT_FILENAMES: Set[str] = {
    DENOMINATOR_FILENAME,
    METRICS_FILENAME,
    SUMMARY_FILENAME,
    MANIFEST_FILENAME,
}

SUMMARY_SCHEMA_VERSION = "stage1_6f_candidate_w1_summary_v1"
MANIFEST_SCHEMA_VERSION = "stage1_6f_candidate_w1_descriptive_bundle_v1"
BUNDLE_STATE_AT_WRITE = "sealed_valid_at_write"
NON_INDEPENDENCE_NOTICE = (
    "historical_ex_post_descriptive_rows_may_share_parent_articles_and_are_not_independent_samples"
)

EXPECTED_PUBLICATION_TIME_AUTHORITY = (
    "parent_audit_outcomes.source_published_at_ms_selected_trusted_bapi_publishDate"
)
EXPECTED_CAPTURE_TIME_STATUS = "historical_unknown"
EXPECTED_CANDIDATE_ROOT_STATE = "collection_terminal_with_gaps_or_unproven_data"

ALLOWED_GATE_FAILURES: Set[str] = {
    "candidate_coverage_not_admissible",
    "horizon_grid_incomplete",
    "horizon_duplicate_or_conflict",
    "insufficient_complete_post_publication_bars",
    "missing_aligned_complete_bars",
    "missing_positive_index_close",
    "no_horizon_funding_observation",
    "no_complete_horizon_depth_ladder",
    "no_horizon_agg_trade_observation",
    "zero_price_path_denominator",
    "missing_required_reducer_field",
    "non_finite_reducer_value",
}

EXPECTED_DESCRIPTOR_KEY_SETS: Dict[str, Set[str]] = {
    "hourly_bar_observation": {
        "first_open_time_ms",
        "first_close_time_ms",
        "first_open",
        "first_high",
        "first_low",
        "first_close",
        "last_open_time_ms",
        "last_close_time_ms",
        "last_open",
        "last_high",
        "last_low",
        "last_close",
        "row_count",
        "note",
    },
    "price_path": {
        "first_close_time_ms",
        "last_close_time_ms",
        "first_complete_bar_close",
        "last_complete_bar_close",
        "bar_close_change_bps",
        "bar_count",
        "note",
    },
    "perp_index_basis": {
        "first_basis_bps",
        "last_basis_bps",
        "median_basis_bps",
        "bar_count",
        "note",
    },
    "mark_index_basis": {
        "first_mark_basis_bps",
        "last_mark_basis_bps",
        "median_mark_basis_bps",
        "bar_count",
        "note",
    },
    "funding_observations": {
        "observations",
        "count",
        "note",
    },
    "open_interest": {
        "first_oi_value",
        "last_oi_value",
        "delta_oi_value",
        "latest_toptrader_long_short_ratio",
        "bar_count",
        "note",
    },
    "visible_depth_proxy": {
        "pct_neg_5",
        "pct_neg_4",
        "pct_neg_3",
        "pct_neg_2",
        "pct_neg_1",
        "pct_pos_1",
        "pct_pos_2",
        "pct_pos_3",
        "pct_pos_4",
        "pct_pos_5",
        "note",
    },
    "agg_trade_observations": {
        "total_trades",
        "total_notional",
        "buyer_maker_true_count",
        "buyer_maker_true_notional",
        "buyer_maker_false_count",
        "buyer_maker_false_notional",
        "note",
    },
}

ALLOWED_SUMMARY_GROUPS: List[Tuple[str, str, str, Optional[int]]] = (
    [("price_path", h, "bar_close_change_bps", None) for h in ("H4", "H12")]
    + [("perp_index_basis", h, "median_basis_bps", None) for h in ("H4", "H12")]
    + [("mark_index_basis", h, "median_mark_basis_bps", None) for h in ("H4", "H12")]
    + [("funding_observations", h, "count", None) for h in ("H1", "H4", "H12")]
    + [("open_interest", h, "delta_oi_value", None) for h in ("H1", "H4", "H12")]
    + [
        ("visible_depth_proxy", h, "median_notional", pct)
        for h in ("H1", "H4", "H12")
        for pct in (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5)
    ]
    + [("agg_trade_observations", h, "total_notional", None) for h in ("H1", "H4", "H12")]
)


class CandidateW1StorageError(Exception):
    """Raised when candidate W1 storage write, serialization, or load fails."""


@dataclass(frozen=True)
class VerifiedCandidateW1Bundle:
    manifest: Dict[str, Any]
    denominator_rows: List[Dict[str, Any]]
    metric_records: List[Dict[str, Any]]
    summary: Dict[str, Any]
    output_root: Path


def _reject_duplicate_keys_pairs_hook(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    d: Dict[str, Any] = {}
    for k, v in pairs:
        if k in d:
            raise CandidateW1StorageError(f"duplicate_key_rejected: {k}")
        d[k] = v
    return d


def _reject_constant(val: str) -> None:
    raise CandidateW1StorageError(f"non_finite_constant_rejected: {val}")


def _strict_json_loads(text: str) -> Any:
    try:
        res = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys_pairs_hook,
            parse_constant=_reject_constant,
        )
    except Exception as exc:
        if isinstance(exc, CandidateW1StorageError):
            raise
        raise CandidateW1StorageError(f"malformed_json: {exc}") from exc
    _validate_finite_and_types_recursive(res)
    return res


def _validate_finite_and_types_recursive(val: Any) -> None:
    if isinstance(val, dict):
        for k, v in val.items():
            if not isinstance(k, str):
                raise CandidateW1StorageError(f"dict_key_not_string: {k}")
            _validate_finite_and_types_recursive(v)
    elif isinstance(val, list):
        for item in val:
            _validate_finite_and_types_recursive(item)
    elif isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise CandidateW1StorageError("non_finite_number_rejected")


def _compute_deterministic_median(sorted_vals: List[Any]) -> Any:
    n = len(sorted_vals)
    if n == 0:
        raise CandidateW1StorageError("median_of_empty_list")
    if n % 2 == 1:
        return sorted_vals[n // 2]
    return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2


def _canonical_json_dumps(obj: Any) -> str:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def compute_candidate_w1_summary_data(
    diagnostic_result: CandidateW1DiagnosticResult,
    verified_candidate: VerifiedCandidateEvidence,
) -> Dict[str, Any]:
    """Compute the fixed 45-group summary data from candidate W1 results."""
    denom_rows = diagnostic_result.denominator_rows
    metric_recs = diagnostic_result.metric_records

    n_denom = len(denom_rows)
    unique_parent_ids = len({r.parent_article_id for r in denom_rows})

    metrics_by_tuple: Dict[Tuple[str, str], List[Any]] = {}
    for r in metric_recs:
        metrics_by_tuple.setdefault((r.metric_name, r.horizon), []).append(r)

    groups: List[Dict[str, Any]] = []
    for m_name, horiz, desc_name, depth_pct in ALLOWED_SUMMARY_GROUPS:
        tuple_recs = metrics_by_tuple.get((m_name, horiz), [])
        descriptive_recs = [r for r in tuple_recs if r.status == "descriptive_only"]
        incomplete_recs = [r for r in tuple_recs if r.status == "diagnostic_incomplete"]

        n_descriptive = len(descriptive_recs)
        n_incomplete = len(incomplete_recs)
        group_parent_ids = len({r.parent_article_id for r in descriptive_recs})

        if n_descriptive == 0:
            minimum = None
            median = None
            maximum = None
        else:
            raw_vals: List[Any] = []
            for r in descriptive_recs:
                if m_name == "visible_depth_proxy":
                    pct_key = (
                        f"pct_neg_{abs(depth_pct)}"
                        if depth_pct is not None and depth_pct < 0
                        else f"pct_pos_{depth_pct}"
                    )
                    v = r.descriptors[pct_key]["median_notional"]
                else:
                    v = r.descriptors[desc_name]
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise CandidateW1StorageError(
                        f"invalid_descriptor_scalar_type: {m_name} {desc_name} got {type(v)}"
                    )
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    raise CandidateW1StorageError(
                        f"non_finite_descriptor_value: {m_name} {desc_name}"
                    )
                raw_vals.append(v)
            raw_vals.sort()
            minimum = raw_vals[0]
            maximum = raw_vals[-1]
            median = _compute_deterministic_median(raw_vals)

        group_item: Dict[str, Any] = {
            "metric_name": m_name,
            "horizon": horiz,
            "descriptor_name": desc_name,
            "depth_percentage": depth_pct,
            "n_denominator": n_denom,
            "n_descriptive": n_descriptive,
            "n_diagnostic_incomplete": n_incomplete,
            "n_unique_parent_article_ids": group_parent_ids,
            "minimum": minimum,
            "median": median,
            "maximum": maximum,
        }
        groups.append(group_item)

    # Sort groups by (metric_name, horizon, descriptor_name, depth_percentage)
    groups.sort(
        key=lambda g: (
            g["metric_name"],
            g["horizon"],
            g["descriptor_name"],
            0 if g["depth_percentage"] is None else g["depth_percentage"],
        )
    )

    if len(groups) != 45:
        raise CandidateW1StorageError(f"summary_groups_count_mismatch: expected 45, got {len(groups)}")

    summary_data = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "candidate_root_relative_path": verified_candidate.candidate_root_relative_path,
        "candidate_manifest_sha256": verified_candidate.manifest_sha256,
        "candidate_run_id": verified_candidate.run_id,
        "candidate_root_state": verified_candidate.root_state,
        "publication_time_authority": EXPECTED_PUBLICATION_TIME_AUTHORITY,
        "point_in_time_source_validated": False,
        "capture_time_status": EXPECTED_CAPTURE_TIME_STATUS,
        "system_available_at_ms": None,
        "fact_available_at_ms": None,
        "n_denominator": n_denom,
        "n_unique_parent_article_ids": unique_parent_ids,
        "metric_horizon_groups": groups,
        "authority_flags": ALL_PERMISSION_FLAGS_FALSE,
        "non_independence_notice": NON_INDEPENDENCE_NOTICE,
    }
    return summary_data


def compute_candidate_w1_status_counts(
    metric_records: List[Any],
) -> List[Dict[str, Any]]:
    """Compute the 38 sorted metric status count rows."""
    counts_map: Dict[Tuple[str, str, str], int] = {}
    for r in metric_records:
        key = (r.metric_name, r.horizon, r.status)
        counts_map[key] = counts_map.get(key, 0) + 1

    status_rows: List[Dict[str, Any]] = []
    for m_name, horiz in EXPECTED_19_METRIC_HORIZON_TUPLES:
        for st in ("descriptive_only", "diagnostic_incomplete"):
            cnt = counts_map.get((m_name, horiz, st), 0)
            status_rows.append({
                "metric_name": m_name,
                "horizon": horiz,
                "status": st,
                "count": cnt,
            })

    # Sort lexicographically by (metric_name, horizon, status)
    status_rows.sort(key=lambda r: (r["metric_name"], r["horizon"], r["status"]))
    if len(status_rows) != 38:
        raise CandidateW1StorageError(f"metric_status_counts_mismatch: expected 38, got {len(status_rows)}")
    return status_rows


def write_candidate_w1_bundle(
    *,
    output_root: Path,
    diagnostic_result: CandidateW1DiagnosticResult,
    verified_candidate: VerifiedCandidateEvidence,
    verified_c: VerifiedCInput,
    approved_design_path: Path,
    approved_design_sha: str,
) -> Path:
    """Atomically write a sealed candidate W1 diagnostic bundle."""
    if output_root.exists():
        raise CandidateW1StorageError(
            f"output_root_collision: output directory already exists: {output_root}"
        )

    output_root.mkdir(parents=True, exist_ok=False)

    temp_files: List[Path] = []
    try:
        # 1. Prepare Denominator bytes (JSONL: one newline per record, no trailing blank)
        denom_records = [r.to_dict() for r in diagnostic_result.denominator_rows]
        denom_lines = [_canonical_json_dumps(r) for r in denom_records]
        denom_bytes = ("\n".join(denom_lines) + "\n").encode("utf-8")

        # 2. Prepare Metrics bytes (JSONL: one newline per record, no trailing blank)
        metric_records = [r.to_dict() for r in diagnostic_result.metric_records]
        metric_lines = [_canonical_json_dumps(r) for r in metric_records]
        metrics_bytes = ("\n".join(metric_lines) + "\n").encode("utf-8")

        # 3. Prepare Summary bytes (JSON: no trailing newline)
        summary_data = compute_candidate_w1_summary_data(
            diagnostic_result=diagnostic_result,
            verified_candidate=verified_candidate,
        )
        summary_bytes = _canonical_json_dumps(summary_data).encode("utf-8")

        files_to_write: List[Tuple[str, bytes]] = [
            (DENOMINATOR_FILENAME, denom_bytes),
            (METRICS_FILENAME, metrics_bytes),
            (SUMMARY_FILENAME, summary_bytes),
        ]

        verified_data_artifacts: List[Dict[str, Any]] = []

        # Write non-manifest files to temp files, fsync, read-back verify
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
                raise CandidateW1StorageError(
                    f"readback_length_mismatch: {filename} expected {len(content_bytes)}, got {len(read_bytes)}"
                )
            calc_sha = hashlib.sha256(read_bytes).hexdigest()
            exp_sha = hashlib.sha256(content_bytes).hexdigest()
            if calc_sha != exp_sha:
                raise CandidateW1StorageError(
                    f"readback_sha_mismatch: {filename} expected {exp_sha}, got {calc_sha}"
                )

            verified_data_artifacts.append({
                "relative_path": filename,
                "byte_length": len(content_bytes),
                "sha256": calc_sha,
            })
            pending_renames.append((temp_path, target_path))

        # Rename the 3 data files atomically
        for temp_path, target_path in pending_renames:
            os.replace(temp_path, target_path)

        # Sort artifacts by relative_path
        verified_data_artifacts.sort(key=lambda a: a["relative_path"])

        # Compute status counts for manifest
        status_counts = compute_candidate_w1_status_counts(diagnostic_result.metric_records)

        c_completion_sha = (
            getattr(verified_c, "completion_manifest_sha256", None)
            or verified_candidate.authority_packet["c_completion_manifest"]["sha256"]
        )

        # 4. Prepare Manifest bytes
        manifest_data = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "bundle_run_id": output_root.name,
            "bundle_state_at_write": BUNDLE_STATE_AT_WRITE,
            "design_authority": {
                "path": str(approved_design_path),
                "sha256": approved_design_sha,
            },
            "candidate_input_authority": {
                "root_relative_path": verified_candidate.candidate_root_relative_path,
                "manifest_sha256": verified_candidate.manifest_sha256,
                "run_id": verified_candidate.run_id,
                "root_state": verified_candidate.root_state,
            },
            "c_input_authority": {
                "completion_manifest_sha256": c_completion_sha,
                "source_export_receipt_sha256": verified_c.source_export_receipt_sha256,
            },
            "point_in_time_authority": {
                "publication_time_authority": EXPECTED_PUBLICATION_TIME_AUTHORITY,
                "point_in_time_source_validated": False,
                "capture_time_status": EXPECTED_CAPTURE_TIME_STATUS,
                "system_available_at_ms": None,
                "fact_available_at_ms": None,
            },
            "output_artifacts": verified_data_artifacts,
            "denominator_count": len(diagnostic_result.denominator_rows),
            "metric_status_counts": status_counts,
            "authority_flags": ALL_PERMISSION_FLAGS_FALSE,
        }
        manifest_bytes = _canonical_json_dumps(manifest_data).encode("utf-8")

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

        read_manifest_bytes = manifest_temp.read_bytes()
        if len(read_manifest_bytes) != len(manifest_bytes):
            raise CandidateW1StorageError("readback_manifest_length_mismatch")
        if hashlib.sha256(read_manifest_bytes).hexdigest() != hashlib.sha256(manifest_bytes).hexdigest():
            raise CandidateW1StorageError("readback_manifest_sha_mismatch")

        # Atomically seal by replacing manifest LAST
        os.replace(manifest_temp, manifest_target)
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


def load_candidate_w1_bundle(
    *,
    output_root: Path,
) -> VerifiedCandidateW1Bundle:
    """Strict reader and verifier for candidate W1 sealed diagnostic bundle."""
    if not output_root.is_dir() or output_root.is_symlink():
        raise CandidateW1StorageError(f"output_root_invalid: not a directory or is symlink: {output_root}")

    # Check directory entries: no symlinks, no temp files, exactly 4 files
    entries = list(output_root.iterdir())
    for e in entries:
        if e.is_symlink():
            raise CandidateW1StorageError(f"symlink_detected_in_output_root: {e.name}")
        if e.name.startswith("."):
            raise CandidateW1StorageError(f"stale_temporary_file_detected: {e.name}")

    entry_names = {e.name for e in entries}
    if entry_names != EXPECTED_OUTPUT_FILENAMES:
        missing = EXPECTED_OUTPUT_FILENAMES - entry_names
        extra = entry_names - EXPECTED_OUTPUT_FILENAMES
        raise CandidateW1StorageError(
            f"unexpected_files_in_output_root: missing={sorted(missing)}, unlisted={sorted(extra)}"
        )

    # 1. Load and validate manifest
    manifest_path = output_root / MANIFEST_FILENAME
    manifest_bytes = manifest_path.read_bytes()
    manifest = _strict_json_loads(manifest_bytes.decode("utf-8"))

    expected_manifest_keys = {
        "schema_version",
        "bundle_run_id",
        "bundle_state_at_write",
        "design_authority",
        "candidate_input_authority",
        "c_input_authority",
        "point_in_time_authority",
        "output_artifacts",
        "denominator_count",
        "metric_status_counts",
        "authority_flags",
    }
    if set(manifest.keys()) != expected_manifest_keys:
        raise CandidateW1StorageError(
            f"manifest_keys_mismatch: missing={expected_manifest_keys - set(manifest.keys())}, extra={set(manifest.keys()) - expected_manifest_keys}"
        )

    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise CandidateW1StorageError(
            f"manifest_schema_version_mismatch: {manifest['schema_version']}"
        )
    if manifest["bundle_run_id"] != output_root.name:
        raise CandidateW1StorageError(
            f"bundle_run_id_mismatch: manifest {manifest['bundle_run_id']} != dir {output_root.name}"
        )
    if manifest["bundle_state_at_write"] != BUNDLE_STATE_AT_WRITE:
        raise CandidateW1StorageError(
            f"bundle_state_mismatch: {manifest['bundle_state_at_write']}"
        )
    if manifest["denominator_count"] != 41:
        raise CandidateW1StorageError(
            f"denominator_count_mismatch: {manifest['denominator_count']}"
        )

    # Authority flags check
    flags = manifest["authority_flags"]
    if set(flags.keys()) != set(ALL_PERMISSION_FLAGS_FALSE.keys()) or any(
        v is not False or not isinstance(v, bool) for v in flags.values()
    ):
        raise CandidateW1StorageError("authority_flag_not_false_in_manifest")

    # Design authority
    design_auth = manifest["design_authority"]
    if set(design_auth.keys()) != {"path", "sha256"}:
        raise CandidateW1StorageError("design_authority_keys_mismatch")
    if not isinstance(design_auth["path"], str) or len(design_auth["sha256"]) != 64:
        raise CandidateW1StorageError("design_authority_values_invalid")

    # Candidate input authority
    cand_auth = manifest["candidate_input_authority"]
    if set(cand_auth.keys()) != {"root_relative_path", "manifest_sha256", "run_id", "root_state"}:
        raise CandidateW1StorageError("candidate_input_authority_keys_mismatch")
    if cand_auth["root_state"] != EXPECTED_CANDIDATE_ROOT_STATE:
        raise CandidateW1StorageError("candidate_root_state_invalid")

    # C input authority
    c_auth = manifest["c_input_authority"]
    if set(c_auth.keys()) != {"completion_manifest_sha256", "source_export_receipt_sha256"}:
        raise CandidateW1StorageError("c_input_authority_keys_mismatch")

    # Point in time authority
    pit_auth = manifest["point_in_time_authority"]
    expected_pit_keys = {
        "publication_time_authority",
        "point_in_time_source_validated",
        "capture_time_status",
        "system_available_at_ms",
        "fact_available_at_ms",
    }
    if set(pit_auth.keys()) != expected_pit_keys:
        raise CandidateW1StorageError("point_in_time_authority_keys_mismatch")
    if (
        pit_auth["publication_time_authority"] != EXPECTED_PUBLICATION_TIME_AUTHORITY
        or pit_auth["point_in_time_source_validated"] is not False
        or pit_auth["capture_time_status"] != EXPECTED_CAPTURE_TIME_STATUS
        or pit_auth["system_available_at_ms"] is not None
        or pit_auth["fact_available_at_ms"] is not None
    ):
        raise CandidateW1StorageError("point_in_time_authority_values_invalid")

    # Output artifacts check
    output_artifacts = manifest["output_artifacts"]
    if not isinstance(output_artifacts, list) or len(output_artifacts) != 3:
        raise CandidateW1StorageError("output_artifacts_invalid_length")
    expected_rel_paths = sorted(list(REQUIRED_NON_MANIFEST_ARTIFACTS))
    actual_rel_paths = [a.get("relative_path") for a in output_artifacts]
    if actual_rel_paths != expected_rel_paths:
        raise CandidateW1StorageError("output_artifacts_paths_mismatch")

    artifacts_by_path: Dict[str, Dict[str, Any]] = {}
    for art in output_artifacts:
        if set(art.keys()) != {"relative_path", "byte_length", "sha256"}:
            raise CandidateW1StorageError("output_artifact_item_keys_invalid")
        rel_p = art["relative_path"]
        file_p = output_root / rel_p
        if not file_p.is_file() or file_p.is_symlink():
            raise CandidateW1StorageError(f"artifact_missing_or_symlink: {rel_p}")
        b = file_p.read_bytes()
        if len(b) != art["byte_length"]:
            raise CandidateW1StorageError(
                f"artifact_length_mismatch: {rel_p} expected {art['byte_length']}, got {len(b)}"
            )
        act_sha = hashlib.sha256(b).hexdigest()
        if act_sha != art["sha256"]:
            raise CandidateW1StorageError(
                f"artifact_sha_mismatch: {rel_p} expected {art['sha256']}, got {act_sha}"
            )
        artifacts_by_path[rel_p] = art

    # Metric status counts check
    metric_status_counts = manifest["metric_status_counts"]
    if not isinstance(metric_status_counts, list) or len(metric_status_counts) != 38:
        raise CandidateW1StorageError("metric_status_counts_length_mismatch")
    expected_status_tuples = sorted([
        (m, h, s)
        for (m, h) in EXPECTED_19_METRIC_HORIZON_TUPLES
        for s in ("descriptive_only", "diagnostic_incomplete")
    ])
    actual_status_tuples = [
        (r.get("metric_name"), r.get("horizon"), r.get("status")) for r in metric_status_counts
    ]
    if actual_status_tuples != expected_status_tuples:
        raise CandidateW1StorageError("metric_status_counts_tuples_order_mismatch")

    total_metric_count = sum(r["count"] for r in metric_status_counts)
    if total_metric_count != 779:
        raise CandidateW1StorageError(
            f"metric_status_counts_total_sum_mismatch: expected 779, got {total_metric_count}"
        )

    # 2. Load and validate Denominator
    denom_path = output_root / DENOMINATOR_FILENAME
    denom_text = denom_path.read_bytes().decode("utf-8")
    denom_lines = denom_text.splitlines(keepends=False)
    if len(denom_lines) != 41:
        raise CandidateW1StorageError(f"denominator_lines_mismatch: expected 41, got {len(denom_lines)}")

    expected_denom_keys = {
        "schema_version",
        "parent_article_id",
        "contract_id",
        "canonical_symbol",
        "eligibility_passed",
        "ineligibility_reasons",
        "publication_time_authority",
        "t_pub_ms",
        "point_in_time_source_validated",
        "capture_time_status",
        "system_available_at_ms",
        "fact_available_at_ms",
        "candidate_root_relative_path",
        "candidate_manifest_sha256",
        "authority_flags",
    }

    denominator_rows: List[Dict[str, Any]] = []
    denom_identities: Set[Tuple[str, str, str]] = set()
    denom_by_key: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for line in denom_lines:
        row = _strict_json_loads(line)
        if set(row.keys()) != expected_denom_keys:
            raise CandidateW1StorageError("denominator_row_keys_mismatch")
        if row["schema_version"] != DENOMINATOR_SCHEMA_VERSION:
            raise CandidateW1StorageError("denominator_schema_version_mismatch")
        if row["eligibility_passed"] is not True:
            raise CandidateW1StorageError("denominator_eligibility_not_true")
        if row["ineligibility_reasons"] != []:
            raise CandidateW1StorageError("denominator_ineligibility_reasons_not_empty")
        if (
            row["publication_time_authority"] != EXPECTED_PUBLICATION_TIME_AUTHORITY
            or row["point_in_time_source_validated"] is not False
            or row["capture_time_status"] != EXPECTED_CAPTURE_TIME_STATUS
            or row["system_available_at_ms"] is not None
            or row["fact_available_at_ms"] is not None
        ):
            raise CandidateW1StorageError("denominator_pit_fields_invalid")
        if (
            row["candidate_root_relative_path"] != cand_auth["root_relative_path"]
            or row["candidate_manifest_sha256"] != cand_auth["manifest_sha256"]
        ):
            raise CandidateW1StorageError("denominator_candidate_authority_mismatch")
        d_flags = row["authority_flags"]
        if set(d_flags.keys()) != set(ALL_PERMISSION_FLAGS_FALSE.keys()) or any(
            v is not False or not isinstance(v, bool) for v in d_flags.values()
        ):
            raise CandidateW1StorageError("denominator_authority_flag_not_false")

        ident = (row["parent_article_id"], row["contract_id"], row["canonical_symbol"])
        if ident in denom_identities:
            raise CandidateW1StorageError(f"duplicate_denominator_identity: {ident}")
        denom_identities.add(ident)
        denom_by_key[ident] = row
        denominator_rows.append(row)

    if len(denom_identities) != 41:
        raise CandidateW1StorageError("denominator_identities_count_mismatch")

    # 3. Load and validate Metrics
    metrics_path = output_root / METRICS_FILENAME
    metrics_text = metrics_path.read_bytes().decode("utf-8")
    metrics_lines = metrics_text.splitlines(keepends=False)
    if len(metrics_lines) != 779:
        raise CandidateW1StorageError(f"metrics_lines_mismatch: expected 779, got {len(metrics_lines)}")

    expected_metric_keys = {
        "schema_version",
        "parent_article_id",
        "contract_id",
        "canonical_symbol",
        "metric_name",
        "horizon",
        "requested_interval",
        "publication_time_authority",
        "t_pub_ms",
        "point_in_time_source_validated",
        "capture_time_status",
        "system_available_at_ms",
        "fact_available_at_ms",
        "source_family_audits",
        "source_logical_archive_record_ids",
        "gate_failures",
        "status",
        "descriptors",
        "authority_flags",
    }

    expected_family_audit_keys = {
        "family_name",
        "coverage_status",
        "coverage_reason",
        "logical_record_ids",
        "timestamp_field",
        "first_observed_ms",
        "last_observed_ms",
        "row_count",
        "duplicate_count",
        "conflict_count",
        "gap_count",
    }

    seen_metric_tuples: Set[Tuple[str, str, str, str, str]] = set()
    metric_records: List[Dict[str, Any]] = []
    for line in metrics_lines:
        rec = _strict_json_loads(line)
        if set(rec.keys()) != expected_metric_keys:
            raise CandidateW1StorageError("metric_record_keys_mismatch")
        if rec["schema_version"] != METRIC_SCHEMA_VERSION:
            raise CandidateW1StorageError("metric_schema_version_mismatch")

        m_ident = (rec["parent_article_id"], rec["contract_id"], rec["canonical_symbol"])
        if m_ident not in denom_identities:
            raise CandidateW1StorageError("metric_not_in_denominator_identities")

        denom_row = denom_by_key[m_ident]
        if rec["t_pub_ms"] != denom_row["t_pub_ms"]:
            raise CandidateW1StorageError("metric_t_pub_ms_mismatch_with_denominator")

        m_tuple = (rec["metric_name"], rec["horizon"])
        if m_tuple not in EXPECTED_19_METRIC_HORIZON_TUPLES:
            raise CandidateW1StorageError(f"metric_horizon_tuple_unrecognized: {m_tuple}")

        full_m_key = (
            rec["parent_article_id"],
            rec["contract_id"],
            rec["canonical_symbol"],
            rec["metric_name"],
            rec["horizon"],
        )
        if full_m_key in seen_metric_tuples:
            raise CandidateW1StorageError(f"duplicate_metric_tuple_record: {full_m_key}")
        seen_metric_tuples.add(full_m_key)

        # requested_interval
        req_int = rec["requested_interval"]
        if set(req_int.keys()) != {"start_ms", "end_ms"}:
            raise CandidateW1StorageError("requested_interval_keys_mismatch")
        if req_int["start_ms"] != rec["t_pub_ms"]:
            raise CandidateW1StorageError("requested_interval_start_not_t_pub")
        if req_int["end_ms"] - req_int["start_ms"] != HORIZON_MS[rec["horizon"]]:
            raise CandidateW1StorageError("requested_interval_duration_mismatch")

        # PIT
        if (
            rec["publication_time_authority"] != EXPECTED_PUBLICATION_TIME_AUTHORITY
            or rec["point_in_time_source_validated"] is not False
            or rec["capture_time_status"] != EXPECTED_CAPTURE_TIME_STATUS
            or rec["system_available_at_ms"] is not None
            or rec["fact_available_at_ms"] is not None
        ):
            raise CandidateW1StorageError("metric_pit_fields_invalid")

        # Status & Descriptors & Gate failures
        st = rec["status"]
        if st not in ("descriptive_only", "diagnostic_incomplete"):
            raise CandidateW1StorageError(f"unrecognized_metric_status: {st}")

        if st == "descriptive_only":
            if rec["gate_failures"] != []:
                raise CandidateW1StorageError("descriptive_only_gate_failures_not_empty")
            expected_desc_keys = EXPECTED_DESCRIPTOR_KEY_SETS[rec["metric_name"]]
            if set(rec["descriptors"].keys()) != expected_desc_keys:
                raise CandidateW1StorageError("descriptor_keys_mismatch")
        else:
            if not rec["gate_failures"] or not isinstance(rec["gate_failures"], list):
                raise CandidateW1StorageError("diagnostic_incomplete_gate_failures_empty")
            for gf in rec["gate_failures"]:
                if gf not in ALLOWED_GATE_FAILURES:
                    raise CandidateW1StorageError(f"unrecognized_gate_failure: {gf}")
            if rec["gate_failures"] != sorted(list(set(rec["gate_failures"]))):
                raise CandidateW1StorageError("gate_failures_not_sorted_unique")
            if rec["descriptors"] != {}:
                raise CandidateW1StorageError("diagnostic_incomplete_descriptors_not_empty")

        # Family audits & logical record IDs
        family_audits = rec["source_family_audits"]
        if not family_audits or not isinstance(family_audits, list):
            raise CandidateW1StorageError("source_family_audits_empty")

        audit_logical_ids: Set[str] = set()
        prev_fam = ""
        for fa in family_audits:
            if set(fa.keys()) != expected_family_audit_keys:
                raise CandidateW1StorageError("source_family_audit_item_keys_mismatch")
            fam_name = fa["family_name"]
            if fam_name <= prev_fam:
                raise CandidateW1StorageError("source_family_audits_not_sorted_strictly")
            prev_fam = fam_name

            for lid in fa["logical_record_ids"]:
                audit_logical_ids.add(lid)

        if sorted(list(audit_logical_ids)) != sorted(rec["source_logical_archive_record_ids"]):
            raise CandidateW1StorageError("source_logical_archive_record_ids_mismatch")

        # Authority flags
        m_flags = rec["authority_flags"]
        if set(m_flags.keys()) != set(ALL_PERMISSION_FLAGS_FALSE.keys()) or any(
            v is not False or not isinstance(v, bool) for v in m_flags.values()
        ):
            raise CandidateW1StorageError("metric_authority_flag_not_false")

        metric_records.append(rec)

    if len(seen_metric_tuples) != 779:
        raise CandidateW1StorageError("seen_metric_tuples_count_mismatch")

    # 4. Load and validate Summary
    summary_path = output_root / SUMMARY_FILENAME
    summary_bytes = summary_path.read_bytes()
    summary = _strict_json_loads(summary_bytes.decode("utf-8"))

    expected_summary_keys = {
        "schema_version",
        "candidate_root_relative_path",
        "candidate_manifest_sha256",
        "candidate_run_id",
        "candidate_root_state",
        "publication_time_authority",
        "point_in_time_source_validated",
        "capture_time_status",
        "system_available_at_ms",
        "fact_available_at_ms",
        "n_denominator",
        "n_unique_parent_article_ids",
        "metric_horizon_groups",
        "authority_flags",
        "non_independence_notice",
    }
    if set(summary.keys()) != expected_summary_keys:
        raise CandidateW1StorageError("summary_keys_mismatch")

    if summary["schema_version"] != SUMMARY_SCHEMA_VERSION:
        raise CandidateW1StorageError("summary_schema_version_mismatch")
    if summary["candidate_root_relative_path"] != cand_auth["root_relative_path"]:
        raise CandidateW1StorageError("summary_candidate_root_path_mismatch")
    if summary["candidate_manifest_sha256"] != cand_auth["manifest_sha256"]:
        raise CandidateW1StorageError("summary_candidate_manifest_sha_mismatch")
    if summary["candidate_run_id"] != cand_auth["run_id"]:
        raise CandidateW1StorageError("summary_candidate_run_id_mismatch")
    if summary["candidate_root_state"] != cand_auth["root_state"]:
        raise CandidateW1StorageError("summary_candidate_root_state_mismatch")

    if (
        summary["publication_time_authority"] != EXPECTED_PUBLICATION_TIME_AUTHORITY
        or summary["point_in_time_source_validated"] is not False
        or summary["capture_time_status"] != EXPECTED_CAPTURE_TIME_STATUS
        or summary["system_available_at_ms"] is not None
        or summary["fact_available_at_ms"] is not None
    ):
        raise CandidateW1StorageError("summary_pit_fields_invalid")

    if summary["n_denominator"] != 41:
        raise CandidateW1StorageError("summary_n_denominator_mismatch")
    expected_unique_parent_ids = len({r["parent_article_id"] for r in denominator_rows})
    if summary["n_unique_parent_article_ids"] != expected_unique_parent_ids:
        raise CandidateW1StorageError("summary_n_unique_parent_article_ids_mismatch")
    if summary["non_independence_notice"] != NON_INDEPENDENCE_NOTICE:
        raise CandidateW1StorageError("summary_non_independence_notice_mismatch")

    s_flags = summary["authority_flags"]
    if set(s_flags.keys()) != set(ALL_PERMISSION_FLAGS_FALSE.keys()) or any(
        v is not False or not isinstance(v, bool) for v in s_flags.values()
    ):
        raise CandidateW1StorageError("summary_authority_flag_not_false")

    groups = summary["metric_horizon_groups"]
    if not isinstance(groups, list) or len(groups) != 45:
        raise CandidateW1StorageError(f"summary_groups_count_mismatch: {len(groups)}")

    expected_group_keys = {
        "metric_name",
        "horizon",
        "descriptor_name",
        "depth_percentage",
        "n_denominator",
        "n_descriptive",
        "n_diagnostic_incomplete",
        "n_unique_parent_article_ids",
        "minimum",
        "median",
        "maximum",
    }

    for g in groups:
        if set(g.keys()) != expected_group_keys:
            raise CandidateW1StorageError("summary_group_item_keys_mismatch")
        if g["n_denominator"] != 41:
            raise CandidateW1StorageError("summary_group_denominator_not_41")
        if g["n_descriptive"] + g["n_diagnostic_incomplete"] != 41:
            raise CandidateW1StorageError("summary_group_counts_sum_not_41")
        if g["n_descriptive"] == 0:
            if g["minimum"] is not None or g["median"] is not None or g["maximum"] is not None:
                raise CandidateW1StorageError("summary_group_extrema_not_null_when_zero_descriptive")
        else:
            if g["minimum"] is None or g["median"] is None or g["maximum"] is None:
                raise CandidateW1StorageError("summary_group_extrema_null_when_has_descriptive")

    return VerifiedCandidateW1Bundle(
        manifest=manifest,
        denominator_rows=denominator_rows,
        metric_records=metric_records,
        summary=summary,
        output_root=output_root,
    )
