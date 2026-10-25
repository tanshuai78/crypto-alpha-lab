#!/usr/bin/env python3
"""Stage 1.5J-C Receipt Closure Audit Evidence Recorder.

Single-purpose standalone script: records a verified AuditDecisionPayload
into the existing validation authority evidence directory with directory flock,
atomic non-overwriting publication, and directory fsync durability.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

PARENT_DESIGN_PATH = "docs/designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md"
PARENT_DESIGN_SHA = "32d5130806489c0848748060835a7c0fb8f1715a3f9fb6b479c2f02cff5d4e45"

PARENT_R1_PLAN_PATH = "docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md"
PARENT_R1_PLAN_SHA = "827d1bbcabdd02f1d9d566752f1185e2e7aef49bb2a236660c8fc6a621d0ebe3"

DELTA_DESIGN_PATH = "docs/designs/2026-10-25-external-signal-shadow-lab-stage1-5j-c-receipt-closure-lifecycle-design-delta_CN.md"
DELTA_DESIGN_SHA = "da901f94fd441f3070c744cacf6337dd1d181e8ecae5f2076c62e1e8c76b584d"

DELTA_PLAN_PATH = "docs/plans/2026-10-25-external-signal-shadow-lab-stage1-5j-c-receipt-closure-lifecycle-implementation-plan_CN.md"
DELTA_PLAN_SHA = "3dc23e936bc5d5ab02f9977ed8e025377e38e0c0a64642486fd62b7144818fca"

RECORDER_RELATIVE_PATH = "scripts/governance/record_stage1_5j_c_receipt_closure_audit.py"
VERIFIER_RELATIVE_PATH = "scripts/governance/verify_stage1_5j_c_receipt_schema.py"
REPORT_RELATIVE_PATH = "evidence/receipt_closure_audit_report.md"

OPERATION_LITERAL = "record_stage1_5j_c_receipt_closure_audit_once"

PAYLOAD_EXACT_KEYS = (
    "artifact_kind",
    "audit_payload_schema_version",
    "manifest_sha256",
    "receipt_root_absolute_path",
    "recorder_delta_design",
    "recorder_implementation_plan",
    "recorder_relative_path",
    "recorder_source_sha256",
    "report_relative_path",
    "report_sha256",
    "report_utf8",
    "review_sha256",
    "run_id",
    "summary_sha256",
    "validation_authorization_release",
    "validation_design",
    "validation_plan",
    "validation_run_authorization",
    "validation_user_receipt_generation_approval",
    "verdict",
    "verifier_relative_path",
    "verifier_source_sha256",
)

RELEASE_EXACT_KEYS = (
    "alpha_claim_allowed",
    "audit_decision_payload_sha256",
    "consumer_promotion_allowed",
    "execution_allowed",
    "live_trading_allowed",
    "network_allowed",
    "paper_trading_allowed",
    "receipt_regeneration_allowed",
    "recorder",
    "recorder_delta_design",
    "recorder_implementation_plan",
    "release_schema_version",
    "release_state",
    "report_relative_path",
    "run_id",
    "signal_allowed",
    "user_audit_recording_approval",
    "validation_design",
    "validation_plan",
    "validation_receipt_root_absolute_path",
)

PERMISSION_KEYS = (
    "alpha_claim_allowed",
    "consumer_promotion_allowed",
    "execution_allowed",
    "live_trading_allowed",
    "network_allowed",
    "paper_trading_allowed",
    "receipt_regeneration_allowed",
    "signal_allowed",
)

LIFECYCLE_EVIDENCE_EXACT_KEYS = (
    "artifact_kind",
    "authorization_release",
    "design",
    "evidence_schema_version",
    "final_root",
    "manifest_sha256",
    "operation",
    "plan",
    "producer_returned_success",
    "publish_terminal",
    "review_sha256",
    "run_authorization",
    "run_id",
    "summary_sha256",
    "user_receipt_generation_approval",
)


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _is_valid_sha256(s: Any) -> bool:
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _check_no_symlink_ancestors(path: Path) -> None:
    curr = path
    while True:
        try:
            st = os.lstat(curr)
        except OSError:
            raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_symlink_or_escape:inaccessible:{curr}")
        if stat.S_ISLNK(st.st_mode):
            raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_symlink_or_escape:symlink_detected:{curr}")
        parent = curr.parent
        if parent == curr:
            break
        curr = parent


def _parse_canonical_json_with_duplicate_detection(b: bytes, context_name: str) -> dict[str, Any]:
    try:
        text = b.decode("utf-8")
    except UnicodeDecodeError:
        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_payload_mismatch:non_utf8:{context_name}")

    if not b.endswith(b"\n") or b.endswith(b"\n\n"):
        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_payload_mismatch:trailing_lf:{context_name}")

    def _pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k, v in pairs:
            if k in d:
                raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_payload_mismatch:duplicate_key:{k}:{context_name}")
            d[k] = v
        return d

    try:
        obj = json.loads(text, object_pairs_hook=_pairs_hook)
    except Exception as e:
        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_payload_mismatch:malformed_json:{context_name}:{e}")

    if not isinstance(obj, dict):
        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_payload_mismatch:not_dict:{context_name}")

    canonical_bytes = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if b != canonical_bytes:
        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_payload_mismatch:non_canonical_formatting:{context_name}")

    return obj


def _verify_two_space_sidecar(sidecar_path: Path, target_name: str, expected_sha: str) -> None:
    _check_no_symlink_ancestors(sidecar_path)
    b = sidecar_path.read_bytes()
    expected_content = f"{expected_sha}  {target_name}\n".encode("utf-8")
    if b != expected_content:
        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_authority_mismatch:sidecar_mismatch:{target_name}")


def _verify_file_seal(expected_seal: dict[str, Any], actual_path: Path, seal_name: str) -> None:
    if not isinstance(expected_seal, dict):
        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_payload_mismatch:seal_not_dict:{seal_name}")
    if set(expected_seal.keys()) != {"relative_path", "sha256", "size_bytes"}:
        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_payload_mismatch:seal_keys_mismatch:{seal_name}")

    _check_no_symlink_ancestors(actual_path)
    b = actual_path.read_bytes()
    actual_sha = _sha256_bytes(b)
    actual_size = len(b)

    if actual_sha != expected_seal["sha256"] or actual_size != expected_seal["size_bytes"]:
        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_authority_mismatch:seal_bytes_mismatch:{seal_name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 1.5J-C Receipt Closure Audit Evidence Recorder"
    )
    parser.add_argument(
        "payload_path",
        type=Path,
        help="Path to repository-external AuditDecisionPayload JSON file",
    )
    args = parser.parse_args()

    payload_path = args.payload_path

    # Check payload file
    _check_no_symlink_ancestors(payload_path)
    if not payload_path.is_file():
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_symlink_or_escape:not_regular_file")

    payload_bytes = payload_path.read_bytes()
    payload_sha = _sha256_bytes(payload_bytes)

    # Parse and validate canonical payload JSON
    payload = _parse_canonical_json_with_duplicate_detection(payload_bytes, "payload")
    if tuple(sorted(payload.keys())) != tuple(sorted(PAYLOAD_EXACT_KEYS)):
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:keys_mismatch")

    # Primitive types and enums
    if payload["audit_payload_schema_version"] != 1:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:schema_version")
    if payload["artifact_kind"] != "validation_only":
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:artifact_kind")
    if payload["verdict"] not in ("receipt_closure_audited", "receipt_closure_incomplete"):
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:verdict")
    if payload["report_relative_path"] != REPORT_RELATIVE_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:report_relative_path")
    if payload["recorder_relative_path"] != RECORDER_RELATIVE_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:recorder_relative_path")
    if payload["verifier_relative_path"] != VERIFIER_RELATIVE_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:verifier_relative_path")

    # Check report projection and report_sha256
    report_utf8 = payload["report_utf8"]
    if not isinstance(report_utf8, str) or not report_utf8:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:empty_report")
    report_bytes = report_utf8.encode("utf-8")
    if _sha256_bytes(report_bytes) != payload["report_sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:report_sha256_mismatch")

    report_lines = report_utf8.splitlines(keepends=True)
    expected_first_line = f"closure_verdict={payload['verdict']}\n"
    if not report_lines or report_lines[0] != expected_first_line:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:report_first_line_projection")

    for idx, line in enumerate(report_lines[1:], start=2):
        if line.startswith("closure_verdict="):
            raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_payload_mismatch:multiple_verdict_lines:{idx}")

    # Resolve project root
    self_path = Path(__file__)
    _check_no_symlink_ancestors(self_path)
    proj_root = self_path.resolve().parent.parent.parent

    # Recompute self script SHA-256
    self_bytes = self_path.read_bytes()
    self_sha = _sha256_bytes(self_bytes)
    if self_sha != payload["recorder_source_sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_payload_mismatch:recorder_source_sha_mismatch")

    # Verify Delta Plan SHA and Delta Design SHA in payload
    delta_plan_file = proj_root / DELTA_PLAN_PATH
    _check_no_symlink_ancestors(delta_plan_file)
    actual_delta_plan_sha = _sha256_bytes(delta_plan_file.read_bytes())
    if actual_delta_plan_sha != DELTA_PLAN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:delta_plan_file_sha_mismatch")
    if payload["recorder_implementation_plan"]["sha256"] != DELTA_PLAN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:payload_delta_plan_sha_mismatch")
    if payload["recorder_implementation_plan"]["relative_path"] != DELTA_PLAN_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:payload_delta_plan_path_mismatch")

    delta_des_file = proj_root / DELTA_DESIGN_PATH
    _check_no_symlink_ancestors(delta_des_file)
    actual_delta_des_sha = _sha256_bytes(delta_des_file.read_bytes())
    if actual_delta_des_sha != DELTA_DESIGN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:delta_design_file_sha_mismatch")
    if payload["recorder_delta_design"]["sha256"] != DELTA_DESIGN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:payload_delta_design_sha_mismatch")
    if payload["recorder_delta_design"]["relative_path"] != DELTA_DESIGN_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:payload_delta_design_path_mismatch")

    # Verify validation design and plan in payload
    parent_des_file = proj_root / PARENT_DESIGN_PATH
    _check_no_symlink_ancestors(parent_des_file)
    actual_parent_des_sha = _sha256_bytes(parent_des_file.read_bytes())
    if actual_parent_des_sha != PARENT_DESIGN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:parent_design_file_sha_mismatch")
    if payload["validation_design"]["sha256"] != PARENT_DESIGN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:payload_parent_design_sha_mismatch")
    if payload["validation_design"]["relative_path"] != PARENT_DESIGN_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:payload_parent_design_path_mismatch")

    parent_plan_file = proj_root / PARENT_R1_PLAN_PATH
    _check_no_symlink_ancestors(parent_plan_file)
    actual_parent_plan_sha = _sha256_bytes(parent_plan_file.read_bytes())
    if actual_parent_plan_sha != PARENT_R1_PLAN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:parent_plan_file_sha_mismatch")
    if payload["validation_plan"]["sha256"] != PARENT_R1_PLAN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:payload_parent_plan_sha_mismatch")
    if payload["validation_plan"]["relative_path"] != PARENT_R1_PLAN_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:payload_parent_plan_path_mismatch")

    # Locate validation authority directory
    val_plan_sha = payload["validation_plan"]["sha256"]
    run_id = payload["run_id"]
    auth_dir = proj_root / ".git/plan-execution/stage1_5j_c" / val_plan_sha / run_id
    _check_no_symlink_ancestors(auth_dir)
    if not auth_dir.is_dir():
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:auth_dir_not_found")

    # Verify validation authority files
    u_app_file = auth_dir / "user_receipt_generation_approval.txt"
    _verify_two_space_sidecar(
        auth_dir / "user_receipt_generation_approval.txt.sha256",
        "user_receipt_generation_approval.txt",
        payload["validation_user_receipt_generation_approval"]["sha256"],
    )
    _verify_file_seal(payload["validation_user_receipt_generation_approval"], u_app_file, "val_approval")

    rel_file = auth_dir / "authorization_release.json"
    _verify_two_space_sidecar(
        auth_dir / "authorization_release.json.sha256",
        "authorization_release.json",
        payload["validation_authorization_release"]["sha256"],
    )
    _verify_file_seal(payload["validation_authorization_release"], rel_file, "val_release")

    run_auth_file = auth_dir / "run_authorization.json"
    _verify_file_seal(payload["validation_run_authorization"], run_auth_file, "val_run_auth")

    # Verify validation root triplet
    receipt_root = Path(payload["receipt_root_absolute_path"])
    _check_no_symlink_ancestors(receipt_root)
    if not receipt_root.is_dir():
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:receipt_root_not_found")

    m_file = receipt_root / "manifest.json"
    s_file = receipt_root / "summary.json"
    r_file = receipt_root / "review_CN.md"

    _check_no_symlink_ancestors(m_file)
    _check_no_symlink_ancestors(s_file)
    _check_no_symlink_ancestors(r_file)

    if _sha256_bytes(m_file.read_bytes()) != payload["manifest_sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:manifest_sha_mismatch")
    if _sha256_bytes(s_file.read_bytes()) != payload["summary_sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:summary_sha_mismatch")
    if _sha256_bytes(r_file.read_bytes()) != payload["review_sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:review_sha_mismatch")

    # Verify producer lifecycle evidence with complete schema & identity checks
    ev_dir = auth_dir / "evidence"
    _check_no_symlink_ancestors(ev_dir)
    prod_ev_file = ev_dir / "producer_lifecycle_evidence.json"
    _check_no_symlink_ancestors(prod_ev_file)
    prod_ev_bytes = prod_ev_file.read_bytes()
    _verify_two_space_sidecar(
        ev_dir / "producer_lifecycle_evidence.json.sha256",
        "producer_lifecycle_evidence.json",
        _sha256_bytes(prod_ev_bytes),
    )
    prod_ev = _parse_canonical_json_with_duplicate_detection(prod_ev_bytes, "producer_lifecycle_evidence")
    if tuple(sorted(prod_ev.keys())) != tuple(sorted(LIFECYCLE_EVIDENCE_EXACT_KEYS)):
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_keys_mismatch")
    if prod_ev["evidence_schema_version"] != 1:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_schema_version")
    if prod_ev["artifact_kind"] != "validation_only":
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_artifact_kind")
    if prod_ev["operation"] != "offline_time_path_validation_once":
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_operation")
    if prod_ev["run_id"] != run_id:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_run_id")
    if prod_ev["final_root"] != str(receipt_root):
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_final_root")
    if prod_ev["producer_returned_success"] is not True:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_producer_not_success")
    if prod_ev["publish_terminal"] != "parent_directory_fsynced":
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_terminal_not_fsynced")
    if prod_ev["manifest_sha256"] != payload["manifest_sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_manifest")
    if prod_ev["summary_sha256"] != payload["summary_sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_summary")
    if prod_ev["review_sha256"] != payload["review_sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_triplet_mismatch:prod_ev_review")
    if prod_ev["user_receipt_generation_approval"]["sha256"] != payload["validation_user_receipt_generation_approval"]["sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:prod_ev_approval_seal")
    if prod_ev["authorization_release"]["sha256"] != payload["validation_authorization_release"]["sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:prod_ev_release_seal")
    if prod_ev["run_authorization"]["sha256"] != payload["validation_run_authorization"]["sha256"]:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:prod_ev_run_auth_seal")
    if prod_ev["design"]["sha256"] != PARENT_DESIGN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:prod_ev_design_seal")
    if prod_ev["plan"]["sha256"] != PARENT_R1_PLAN_SHA:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:prod_ev_plan_seal")

    # Verify 15-line recording approval strictly
    rec_app_file = auth_dir / "user_audit_recording_approval.txt"
    _check_no_symlink_ancestors(rec_app_file)
    rec_app_bytes = rec_app_file.read_bytes()
    _verify_two_space_sidecar(
        auth_dir / "user_audit_recording_approval.txt.sha256",
        "user_audit_recording_approval.txt",
        _sha256_bytes(rec_app_bytes),
    )
    try:
        rec_app_text = rec_app_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_app_non_utf8")
    if not rec_app_bytes.endswith(b"\n") or rec_app_bytes.endswith(b"\n\n"):
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_app_trailing_lf")

    rec_app_lines = rec_app_text.splitlines()
    if len(rec_app_lines) != 15:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_app_line_count")

    expected_rec_app_lines = [
        f"operation={OPERATION_LITERAL}",
        f"run_id={run_id}",
        f"validation_receipt_root_absolute_path={receipt_root}",
        f"report_relative_path={REPORT_RELATIVE_PATH}",
        f"audit_decision_payload_sha256={payload_sha}",
        f"validation_design_relative_path={PARENT_DESIGN_PATH}",
        f"validation_design_sha256={PARENT_DESIGN_SHA}",
        f"validation_plan_relative_path={PARENT_R1_PLAN_PATH}",
        f"validation_plan_sha256={PARENT_R1_PLAN_SHA}",
        f"recorder_delta_design_relative_path={DELTA_DESIGN_PATH}",
        f"recorder_delta_design_sha256={DELTA_DESIGN_SHA}",
        f"recorder_implementation_plan_relative_path={DELTA_PLAN_PATH}",
        f"recorder_implementation_plan_sha256={DELTA_PLAN_SHA}",
        f"recorder_relative_path={RECORDER_RELATIVE_PATH}",
        f"recorder_source_sha256={self_sha}",
    ]
    if rec_app_lines != expected_rec_app_lines:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_app_lines_mismatch")

    # Verify recording release strictly
    rec_rel_file = auth_dir / "audit_recording_release.json"
    _check_no_symlink_ancestors(rec_rel_file)
    rec_rel_bytes = rec_rel_file.read_bytes()
    _verify_two_space_sidecar(
        auth_dir / "audit_recording_release.json.sha256",
        "audit_recording_release.json",
        _sha256_bytes(rec_rel_bytes),
    )
    rec_rel = _parse_canonical_json_with_duplicate_detection(rec_rel_bytes, "audit_recording_release")
    if tuple(sorted(rec_rel.keys())) != tuple(sorted(RELEASE_EXACT_KEYS)):
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_keys")
    if rec_rel["release_schema_version"] != 1:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_schema_version")
    if rec_rel["release_state"] != "user_message_verified_and_released":
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_state")
    if rec_rel["run_id"] != run_id:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_run_id")
    if rec_rel["audit_decision_payload_sha256"] != payload_sha:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_payload_sha")
    if rec_rel["validation_receipt_root_absolute_path"] != str(receipt_root):
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_receipt_root")
    if rec_rel["report_relative_path"] != REPORT_RELATIVE_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_report_path")

    for pk in PERMISSION_KEYS:
        if rec_rel[pk] is not False:
            raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_authority_mismatch:permission_not_false:{pk}")

    _verify_file_seal(rec_rel["user_audit_recording_approval"], rec_app_file, "rec_app_seal")
    _verify_file_seal(rec_rel["recorder"], self_path, "recorder_seal")
    if rec_rel["recorder_delta_design"]["sha256"] != DELTA_DESIGN_SHA or rec_rel["recorder_delta_design"]["relative_path"] != DELTA_DESIGN_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_delta_design")
    if rec_rel["recorder_implementation_plan"]["sha256"] != DELTA_PLAN_SHA or rec_rel["recorder_implementation_plan"]["relative_path"] != DELTA_PLAN_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_delta_plan")
    if rec_rel["validation_design"]["sha256"] != PARENT_DESIGN_SHA or rec_rel["validation_design"]["relative_path"] != PARENT_DESIGN_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_parent_design")
    if rec_rel["validation_plan"]["sha256"] != PARENT_R1_PLAN_SHA or rec_rel["validation_plan"]["relative_path"] != PARENT_R1_PLAN_PATH:
        raise RuntimeError("STOP=stage1_5j_c_audit_recording_authority_mismatch:rec_rel_parent_plan")

    # Now enter evidence directory with directory flock
    dfd = os.open(str(ev_dir), os.O_RDONLY)
    try:
        try:
            fcntl.flock(dfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            raise RuntimeError("STOP=stage1_5j_c_audit_recording_lock_unavailable")

        report_target = ev_dir / "receipt_closure_audit_report.md"
        sidecar_target = ev_dir / "receipt_closure_audit_report.md.sha256"
        expected_sidecar_bytes = f"{payload['report_sha256']}  receipt_closure_audit_report.md\n".encode("utf-8")

        staging_r_name = f".receipt_closure_audit_report.{payload_sha}.staging"
        staging_s_name = f".receipt_closure_audit_report.sha256.{payload_sha}.staging"
        staging_r = ev_dir / staging_r_name
        staging_s = ev_dir / staging_s_name

        def _classify_state() -> str:
            entries = sorted([p.name for p in ev_dir.iterdir()])
            allowed_base = {"producer_lifecycle_evidence.json", "producer_lifecycle_evidence.json.sha256"}

            # Check symlinks and file types for every entry
            for e in entries:
                p = ev_dir / e
                try:
                    st = os.lstat(p)
                except OSError:
                    raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_symlink_or_escape:inaccessible:{e}")
                if stat.S_ISLNK(st.st_mode):
                    raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_symlink_or_escape:symlink_detected:{e}")
                if not stat.S_ISREG(st.st_mode):
                    raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_target_exists_mismatch:non_regular_file:{e}")

            if not allowed_base.issubset(set(entries)):
                return "S3"

            extra = set(entries) - allowed_base
            if not extra:
                return "S0"

            stagings = {e for e in extra if e.endswith(".staging")}
            non_stagings = extra - stagings

            if stagings:
                if len(stagings) != 1:
                    return "S3"
                stg_name = next(iter(stagings))
                stg_path = ev_dir / stg_name
                stg_bytes = stg_path.read_bytes()

                # Legal S4 combinations according to Delta Design §6.3:
                # 1. S0 + T_R: non_stagings == empty, stg_name == staging_r_name, stg_bytes == report_bytes
                if not non_stagings and stg_name == staging_r_name and stg_bytes == report_bytes:
                    return "S4_R_from_S0"
                # 2. S1 + T_R: non_stagings == {R}, stg_name == staging_r_name, stg_bytes == report_bytes, R valid
                if (
                    non_stagings == {"receipt_closure_audit_report.md"}
                    and stg_name == staging_r_name
                    and stg_bytes == report_bytes
                    and _sha256_bytes(report_target.read_bytes()) == payload["report_sha256"]
                ):
                    return "S4_R_from_S1"
                # 3. S1 + T_S: non_stagings == {R}, stg_name == staging_s_name, stg_bytes == expected_sidecar_bytes, R valid
                if (
                    non_stagings == {"receipt_closure_audit_report.md"}
                    and stg_name == staging_s_name
                    and stg_bytes == expected_sidecar_bytes
                    and _sha256_bytes(report_target.read_bytes()) == payload["report_sha256"]
                ):
                    return "S4_S_from_S1"
                # 4. S2 + T_S: non_stagings == {R, S}, stg_name == staging_s_name, stg_bytes == expected_sidecar_bytes, R & S valid
                if (
                    non_stagings == {"receipt_closure_audit_report.md", "receipt_closure_audit_report.md.sha256"}
                    and stg_name == staging_s_name
                    and stg_bytes == expected_sidecar_bytes
                    and _sha256_bytes(report_target.read_bytes()) == payload["report_sha256"]
                    and sidecar_target.read_bytes() == expected_sidecar_bytes
                ):
                    return "S4_S_from_S2"

                # Any other staging state (including S0 + T_S, content mismatch) is S3
                return "S3"

            # No staging
            if non_stagings == {"receipt_closure_audit_report.md"}:
                r_bytes = report_target.read_bytes()
                if _sha256_bytes(r_bytes) == payload["report_sha256"]:
                    return "S1"
                return "S3"

            if non_stagings == {"receipt_closure_audit_report.md", "receipt_closure_audit_report.md.sha256"}:
                r_bytes = report_target.read_bytes()
                s_bytes = sidecar_target.read_bytes()
                if _sha256_bytes(r_bytes) == payload["report_sha256"] and s_bytes == expected_sidecar_bytes:
                    return "S2"
                return "S3"

            return "S3"

        state = _classify_state()

        # Handle legal S4 cleanup and reclassification
        if state in ("S4_R_from_S0", "S4_R_from_S1"):
            staging_r.unlink()
            try:
                os.fsync(dfd)
            except OSError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_dir")
            state = _classify_state()
        elif state in ("S4_S_from_S1", "S4_S_from_S2"):
            staging_s.unlink()
            try:
                os.fsync(dfd)
            except OSError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_dir")
            state = _classify_state()

        if state == "S3":
            raise RuntimeError("STOP=stage1_5j_c_audit_recording_target_exists_mismatch:anomalous_state")

        if state == "S0":
            # Write staging report
            staging_r.write_bytes(report_bytes)
            with staging_r.open("rb") as f:
                try:
                    os.fsync(f.fileno())
                except OSError:
                    raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_file")

            try:
                os.link(str(staging_r), str(report_target))
            except FileExistsError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_target_exists_mismatch:collision")

            try:
                os.fsync(dfd)
            except OSError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_dir")

            staging_r.unlink()
            try:
                os.fsync(dfd)
            except OSError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_dir")

            state = "S1"

        if state == "S1":
            try:
                os.fsync(dfd)
            except OSError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_dir")

            staging_s.write_bytes(expected_sidecar_bytes)
            with staging_s.open("rb") as f:
                try:
                    os.fsync(f.fileno())
                except OSError:
                    raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_file")

            try:
                os.link(str(staging_s), str(sidecar_target))
            except FileExistsError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_target_exists_mismatch:collision")

            try:
                os.fsync(dfd)
            except OSError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_dir")

            staging_s.unlink()
            try:
                os.fsync(dfd)
            except OSError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_dir")

            state = "S2"

        if state == "S2":
            try:
                os.fsync(dfd)
            except OSError:
                raise RuntimeError("STOP=stage1_5j_c_audit_recording_persistence_failure:fsync_dir")
            return 0

        raise RuntimeError(f"STOP=stage1_5j_c_audit_recording_target_exists_mismatch:unhandled_state:{state}")

    finally:
        try:
            fcntl.flock(dfd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(dfd)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        msg = str(e)
        if msg.startswith("STOP="):
            sys.stderr.write(f"{msg}\n")
            sys.exit(1)
        raise
