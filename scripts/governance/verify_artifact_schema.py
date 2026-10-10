#!/usr/bin/env python3
"""Governance Cross-Boundary Artifact Schema Integrity Verifier.

Rule 17 independent read-only verifier CLI.
Standard-library only. Derives acceptance solely from literal profile constants
and disk artifact bytes.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Profile Constants: stage1_5j_a_receipt_v1
# -----------------------------------------------------------------------------

PROFILE_ID = "stage1_5j_a_receipt_v1"
PROFILE_CONTRACT_VERSION = 1
NETWORK_PROFILE_ID = "stage1_5j_a_public_archive_inventory_v1"

SUPPORTED_PROFILES = frozenset({PROFILE_ID})

# Stage 1.5J-A Profile Authority Constants
TARGET_STAGE_DESIGN_PATH = (
    "docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-"
    "historical-archive-coverage-inventory-design_CN.md"
)
TARGET_STAGE_DESIGN_SHA256 = (
    "b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a"
)
TARGET_STAGE_DELTA_PATH = (
    "docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-"
    "conformance-remediation-design-delta_CN.md"
)
TARGET_STAGE_DELTA_SHA256 = (
    "6063ed103d31fcf6c60ad8106eb13650f54b74272182c78bf8e81f9ba48a91ac"
)

ALLOWED_APPROVED_DESIGNS = frozenset(
    {
        (TARGET_STAGE_DESIGN_PATH, TARGET_STAGE_DESIGN_SHA256),
        (TARGET_STAGE_DELTA_PATH, TARGET_STAGE_DELTA_SHA256),
    }
)

AUDITED_CORE_RELATIVE_PATH = (
    "src/research/external_signal_shadow/"
    "stage1_5j_a_historical_archive_coverage_inventory.py"
)
AUDITED_CLI_RELATIVE_PATH = (
    "scripts/external_signal_shadow/"
    "run_stage1_5j_a_historical_archive_coverage_inventory.py"
)
AUDITED_CONFIG_RELATIVE_PATH = "configs/base.py"
FROZEN_PARSER_RELATIVE_PATH = (
    "src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py"
)

SUMMARY_SCHEMA_VERSION = "stage1_5j_a_historical_archive_coverage_inventory_v1"
MANIFEST_SCHEMA_VERSION = "stage1_5j_a_historical_archive_coverage_inventory_manifest_v1"

RUN_ID_PATTERN = re.compile(
    r"^stage1_5j_a_historical_archive_coverage_inventory_[0-9]{8}T[0-9]{6}Z$"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
HEX32_PATTERN = re.compile(r"^[0-9a-f]{32}$")
DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
POSITIVE_INT_PATTERN = re.compile(r"^[1-9][0-9]*$")
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]+USDT$")

MANIFEST_EXACT_KEYS = frozenset(
    {"artifacts", "root_relative_path", "run_id", "schema_version"}
)
MANIFEST_ARTIFACT_EXACT_KEYS = frozenset({"byte_count", "relative_path", "sha256"})

SUMMARY_EXACT_KEYS = frozenset(
    {
        "analysis_state",
        "archive_package_records",
        "authority_flags",
        "authority_packet",
        "catalog_denominator_records",
        "catalog_scan",
        "coverage_inventory",
        "decision",
        "parent_records",
        "request_records",
        "run_id",
        "schema_version",
        "universe_window",
    }
)

AUTHORITY_FLAG_EXACT_KEYS = frozenset(
    {
        "alpha_claim_allowed",
        "alpha_interpretation_allowed",
        "commit_allowed",
        "deployment_allowed",
        "execution_allowed",
        "live_trading_allowed",
        "network_allowed_after_run",
        "paper_trading_allowed",
        "pnl_calculation_allowed",
        "price_response_calculation_allowed",
        "receipt_generation_allowed_without_authorization",
        "replay_allowed",
        "signal_generation_allowed",
    }
)

UNIVERSE_WINDOW_EXACT_KEYS = frozenset({"end_exclusive_ms", "start_ms"})
CATALOG_SCAN_EXACT_KEYS = frozenset(
    {
        "page_limit_per_pass",
        "scan_a_page_count",
        "scan_b_page_count",
        "sentinel_page_no",
        "stable_tuple_sha256",
    }
)

AUTHORITY_PACKET_EXACT_KEYS = frozenset(
    {
        "approved_design",
        "approved_plan",
        "audited_cli",
        "audited_config",
        "audited_core",
        "frozen_parser",
        "network_authorization",
    }
)
AUTHORITY_MEMBER_EXACT_KEYS = frozenset({"relative_path", "sha256"})
NETWORK_AUTH_EXACT_KEYS = frozenset(
    {"authorized_run_id", "network_profile_id", "relative_path", "sha256"}
)

CATALOG_DENOMINATOR_EXACT_KEYS = frozenset(
    {
        "candidate_status",
        "detail_request_id",
        "release_date_ms",
        "source_article_id",
        "title",
    }
)
PARENT_RECORD_EXACT_KEYS = frozenset(
    {
        "children",
        "detail_payload_sha256",
        "detail_request_id",
        "detail_status",
        "parent_state",
        "source_article_id",
    }
)
CHILD_EXACT_KEYS = frozenset({"child_scope", "symbol", "symbol_launch_time_ms"})

ARCHIVE_PACKAGE_EXACT_KEYS = frozenset(
    {
        "checksum_request_id",
        "child_state",
        "first_post_launch_trade_delay_ms",
        "first_post_launch_trade_time_ms",
        "last_post_launch_trade_time_ms",
        "logical_archive_identity",
        "parent_article_id",
        "post_launch_row_count",
        "symbol",
        "utc_date",
        "zip_request_id",
    }
)
LOGICAL_ARCHIVE_IDENTITY_EXACT_KEYS = frozenset(
    {"market", "metric", "parent_article_id", "symbol", "utc_date"}
)

COVERAGE_INVENTORY_EXACT_KEYS = frozenset(
    {
        "catalog_denominator_count",
        "child_coverage_complete_count",
        "child_coverage_gap_count",
        "in_scope_usdt_child_count",
        "out_of_scope_child_count",
        "parent_coverage_complete_count",
        "parent_coverage_gap_count",
        "resolved_parent_count",
        "target_parent_count",
    }
)

INTENT_EXACT_KEYS = frozenset(
    {
        "event",
        "parent_article_id",
        "request_id",
        "request_kind",
        "request_state",
        "symbol",
        "url",
        "utc_date",
    }
)
TERMINAL_EXACT_KEYS = frozenset(
    {
        "event",
        "http_status",
        "request_id",
        "request_state",
        "response_bytes",
        "response_relative_path",
        "response_sha256",
        "transport_error",
    }
)

REQUEST_KINDS = frozenset({"catalog", "detail", "archive", "checksum"})
TERMINAL_STATES = frozenset(
    {
        "response_persisted",
        "http_not_found",
        "transport_inconclusive",
        "response_rejected",
    }
)

PROJECTION_EXACT_KEYS = frozenset(
    {
        "http_status_or_transport_error",
        "request_id",
        "request_kind",
        "request_state",
        "response_bytes",
        "response_relative_path",
        "response_sha256",
        "url",
    }
)


# -----------------------------------------------------------------------------
# Canonical JSON Verification Helper
# -----------------------------------------------------------------------------


def _verify_canonical_json(path: Path):

    """Verify that file at path is canonical JSON without BOM, with sorted keys and single terminal newline."""
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return {}, f"File {path.name} contains UTF-8 BOM"
    if not raw.endswith(b"\n") or raw.endswith(b"\r\n") or raw.endswith(b"\n\n"):
        return {}, f"File {path.name} must end with exactly one terminal newline '\\n'"

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return {}, f"File {path.name} is not valid UTF-8: {e}"

    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return {}, f"File {path.name} JSON decode error: {e}"

    # Re-encode canonical bytes
    canonical_bytes = (
        json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if canonical_bytes != raw:
        # Identify whether it was unsorted keys or formatting
        try:
            non_sorted_bytes = (
                json.dumps(obj, sort_keys=False, ensure_ascii=False, separators=(",", ":")) + "\n"
            ).encode("utf-8")
            if non_sorted_bytes == raw:
                return {}, f"File {path.name} does not use sorted keys"
            with_spaces_bytes = (
                json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(", ", ": ")) + "\n"
            ).encode("utf-8")
            if with_spaces_bytes == raw or b": " in raw or b", " in raw:
                return {}, f"File {path.name} does not use canonical separators (',', ':')"
        except Exception:
            pass
        return {}, f"File {path.name} canonical byte encoding mismatch"

    return obj, None


def _is_safe_relative_path(path_str: str) -> bool:
    """Validate that path_str is a safe, normalized relative path."""
    if not path_str or path_str.startswith("/") or path_str.startswith("\\"):
        return False
    parts = path_str.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        return False
    return True


def _is_allowed_manifest_artifact_path(rel_path: str) -> bool:
    """Validate that rel_path matches exact frozen artifact path grammar for stage1_5j_a_receipt_v1."""
    if rel_path in ("summary.json", "review_CN.md", "request_journal.jsonl"):
        return True
    parts = rel_path.split("/")
    if len(parts) == 3 and parts[0] == "raw":
        sub = parts[1]
        fname = parts[2]
        if sub in ("catalog_scan_a", "catalog_scan_b"):
            if fname.endswith(".json"):
                stem = fname[:-5]
                return bool(POSITIVE_INT_PATTERN.match(stem))
            return False
        if sub == "article_details":
            if fname.endswith(".json"):
                stem = fname[:-5]
                return bool(HEX32_PATTERN.match(stem))
            return False
    elif len(parts) == 4 and parts[0] == "raw" and parts[1] == "archive":
        symbol = parts[2]
        fname = parts[3]
        if not SYMBOL_PATTERN.match(symbol):
            return False
        prefix = f"{symbol}-aggTrades-"
        if not fname.startswith(prefix):
            return False
        rest = fname[len(prefix):]
        if rest.endswith(".zip"):
            date_str = rest[:-4]
            return bool(DATE_PATTERN.match(date_str))
        if rest.endswith(".zip.CHECKSUM"):
            date_str = rest[:-13]
            return bool(DATE_PATTERN.match(date_str))
        return False
    return False


def _check_no_symlinks(root: Path):

    """Recursively verify that no file or directory in root is a symlink."""
    if os.path.islink(root):
        return f"Artifact root itself is a symlink: {root}"
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for d in dirnames:
            p = os.path.join(dirpath, d)
            if os.path.islink(p):
                return f"Directory symlink detected: {p}"
        for f in filenames:
            p = os.path.join(dirpath, f)
            if os.path.islink(p):
                return f"File symlink detected: {p}"
    return None


# -----------------------------------------------------------------------------
# Core Verification Logic
# -----------------------------------------------------------------------------


def verify_stage1_5j_a_receipt_v1(project_root: Path, artifact_root_rel: str):

    """Validate artifact tree under project_root against stage1_5j_a_receipt_v1 profile.

    Returns diagnostic string on failure, None on success.
    """
    root_path = project_root / artifact_root_rel

    # 1. Symlink check
    cur = root_path.parent
    while cur != project_root and cur != cur.parent:
        if os.path.islink(cur):
            return f"Ancestor directory symlink detected: {cur}"
        cur = cur.parent

    symlink_err = _check_no_symlinks(root_path)
    if symlink_err:
        return symlink_err

    # 2. Manifest check
    manifest_file = root_path / "manifest.json"
    if not manifest_file.exists():
        return f"Required manifest.json missing from {artifact_root_rel}"

    manifest, err = _verify_canonical_json(manifest_file)
    if err:
        return f"manifest.json canonical validation failed: {err}"

    if set(manifest.keys()) != MANIFEST_EXACT_KEYS:
        unexpected = set(manifest.keys()) - MANIFEST_EXACT_KEYS
        missing = MANIFEST_EXACT_KEYS - set(manifest.keys())
        return f"manifest.json keys mismatch: unexpected={sorted(unexpected)}, missing={sorted(missing)}"

    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        return (
            f"manifest.json schema_version mismatch: "
            f"expected '{MANIFEST_SCHEMA_VERSION}', observed '{manifest['schema_version']}'"
        )

    run_id = manifest["run_id"]
    if not RUN_ID_PATTERN.match(run_id):
        return f"manifest.json run_id invalid format: observed '{run_id}'"

    expected_root_rel = f"data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/{run_id}"
    if manifest["root_relative_path"] != expected_root_rel:
        return (
            f"manifest.json root_relative_path mismatch: "
            f"expected '{expected_root_rel}', observed '{manifest['root_relative_path']}'"
        )

    if artifact_root_rel != expected_root_rel:
        return (
            f"artifact-root argument mismatch with manifest: "
            f"expected '{expected_root_rel}', observed '{artifact_root_rel}'"
        )

    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, list):
        return "manifest.json artifacts must be a list"

    manifest_paths = []
    seen_paths = set()
    manifest_map = {}

    for idx, art in enumerate(artifacts):
        if not isinstance(art, dict):
            return f"manifest.json artifact[{idx}] must be an object"
        if set(art.keys()) != MANIFEST_ARTIFACT_EXACT_KEYS:
            unexpected = set(art.keys()) - MANIFEST_ARTIFACT_EXACT_KEYS
            missing = MANIFEST_ARTIFACT_EXACT_KEYS - set(art.keys())
            return (
                f"manifest.json artifact[{idx}] keys mismatch: "
                f"unexpected={sorted(unexpected)}, missing={sorted(missing)}"
            )

        rel = art["relative_path"]
        if not _is_safe_relative_path(rel):
            return f"manifest.json artifact[{idx}] invalid safe relative path: '{rel}'"
        if not _is_allowed_manifest_artifact_path(rel):
            return f"manifest.json artifact[{idx}] path does not match allowed pattern: '{rel}'"

        if rel in seen_paths:
            return f"manifest.json duplicate artifact entry: '{rel}'"
        seen_paths.add(rel)

        # Check sorting
        if manifest_paths and rel <= manifest_paths[-1]:
            return f"manifest.json artifacts list is unsorted: '{rel}' after '{manifest_paths[-1]}'"
        manifest_paths.append(rel)

        byte_count = art["byte_count"]
        if type(byte_count) is not int or isinstance(byte_count, bool) or byte_count < 0:
            return f"manifest.json artifact[{idx}] invalid byte_count: observed {byte_count}"

        sha = art["sha256"]
        if not (isinstance(sha, str) and SHA256_PATTERN.match(sha)):
            return f"manifest.json artifact[{idx}] invalid sha256: observed '{sha}'"

        manifest_map[rel] = art

    # Manifest must not list manifest.json
    if "manifest.json" in seen_paths:
        return "manifest.json must not list itself in artifacts"

    # Required members
    for req in ("summary.json", "review_CN.md", "request_journal.jsonl"):
        if req not in seen_paths:
            return f"manifest.json missing required member: '{req}'"

    # Compute implied directories from manifest-listed paths
    implied_dirs = set()
    for p_str in seen_paths:
        p = Path(p_str).parent
        while str(p) not in (".", ""):
            implied_dirs.add(p.as_posix())
            p = p.parent

    # Verify disk files and directories against manifest
    disk_files = set()
    for dirpath, dirnames, filenames in os.walk(root_path):
        rel_dir = os.path.relpath(dirpath, root_path)
        if rel_dir != ".":
            rel_dir_posix = Path(rel_dir).as_posix()
            if rel_dir_posix not in implied_dirs:
                return f"Found unimplied directory on disk: '{rel_dir_posix}'"
        for d in dirnames:
            rel_d = os.path.normpath(os.path.join(rel_dir, d)) if rel_dir != "." else d
            rel_d_posix = Path(rel_d).as_posix()
            if rel_d_posix not in implied_dirs:
                return f"Found unimplied directory on disk: '{rel_d_posix}'"

        for f in filenames:
            rel_f = os.path.normpath(os.path.join(rel_dir, f)) if rel_dir != "." else f
            rel_f_posix = rel_f.replace("\\", "/")
            if rel_f_posix == "manifest.json":
                continue
            disk_files.add(rel_f_posix)

    # Every file on disk must be in manifest
    unlisted_files = disk_files - seen_paths
    if unlisted_files:
        return f"Found unlisted files on disk not in manifest: {sorted(unlisted_files)}"

    # Every file in manifest must exist on disk and match size & sha256
    missing_files = seen_paths - disk_files
    if missing_files:
        return f"Files listed in manifest missing on disk: {sorted(missing_files)}"

    for rel_f, art in manifest_map.items():
        fp = root_path / rel_f
        actual_bytes = fp.read_bytes()
        if len(actual_bytes) != art["byte_count"]:
            return (
                f"File '{rel_f}' byte count mismatch: "
                f"manifest={art['byte_count']}, observed={len(actual_bytes)}"
            )
        actual_sha = hashlib.sha256(actual_bytes).hexdigest()
        if actual_sha != art["sha256"]:
            return (
                f"File '{rel_f}' sha256 mismatch: "
                f"manifest={art['sha256']}, observed={actual_sha}"
            )

    # 3. Summary check
    summary_file = root_path / "summary.json"
    summary, err = _verify_canonical_json(summary_file)
    if err:
        return f"summary.json canonical validation failed: {err}"

    if set(summary.keys()) != SUMMARY_EXACT_KEYS:
        unexpected = set(summary.keys()) - SUMMARY_EXACT_KEYS
        missing = SUMMARY_EXACT_KEYS - set(summary.keys())
        return f"summary.json keys mismatch: unexpected={sorted(unexpected)}, missing={sorted(missing)}"

    if summary["schema_version"] != SUMMARY_SCHEMA_VERSION:
        return (
            f"summary.json schema_version mismatch: "
            f"expected '{SUMMARY_SCHEMA_VERSION}', observed '{summary['schema_version']}'"
        )
    if summary["run_id"] != run_id:
        return (
            f"summary.json run_id mismatch: expected '{run_id}', observed '{summary['run_id']}'"
        )

    # Authority flags
    auth_flags = summary["authority_flags"]
    if not isinstance(auth_flags, dict) or set(auth_flags.keys()) != AUTHORITY_FLAG_EXACT_KEYS:
        return "summary.json authority_flags keys mismatch"
    for k, v in auth_flags.items():
        if v is not False or type(v) is not bool:
            return f"summary.json authority_flags['{k}'] must be literal False, observed {v}"

    # Universe window
    u_win = summary["universe_window"]
    if not isinstance(u_win, dict) or set(u_win.keys()) != UNIVERSE_WINDOW_EXACT_KEYS:
        return "summary.json universe_window keys mismatch"
    for k in ("start_ms", "end_exclusive_ms"):
        val = u_win[k]
        if type(val) is not int or isinstance(val, bool):
            return f"summary.json universe_window['{k}'] must be integer, observed {val}"

    # Catalog scan
    c_scan = summary["catalog_scan"]
    if not isinstance(c_scan, dict) or set(c_scan.keys()) != CATALOG_SCAN_EXACT_KEYS:
        return "summary.json catalog_scan keys mismatch"
    for k in ("page_limit_per_pass", "scan_a_page_count", "scan_b_page_count", "sentinel_page_no"):
        val = c_scan[k]
        if type(val) is not int or isinstance(val, bool) or val <= 0:
            return f"summary.json catalog_scan['{k}'] must be positive integer, observed {val}"
    if not (isinstance(c_scan["stable_tuple_sha256"], str) and SHA256_PATTERN.match(c_scan["stable_tuple_sha256"])):
        return "summary.json catalog_scan stable_tuple_sha256 invalid sha256"

    # Authority packet
    a_packet = summary["authority_packet"]
    if not isinstance(a_packet, dict) or set(a_packet.keys()) != AUTHORITY_PACKET_EXACT_KEYS:
        return "summary.json authority_packet keys mismatch"
    for member in ("approved_design", "approved_plan", "audited_cli", "audited_config", "audited_core", "frozen_parser"):
        m_obj = a_packet[member]
        if not isinstance(m_obj, dict) or set(m_obj.keys()) != AUTHORITY_MEMBER_EXACT_KEYS:
            return f"summary.json authority_packet['{member}'] keys mismatch"
        if not _is_safe_relative_path(m_obj["relative_path"]):
            return f"summary.json authority_packet['{member}'] invalid relative_path"
        if not (isinstance(m_obj["sha256"], str) and SHA256_PATTERN.match(m_obj["sha256"])):
            return f"summary.json authority_packet['{member}'] invalid sha256"

    # Verify frozen profile authority bindings
    design_tuple = (
        a_packet["approved_design"]["relative_path"],
        a_packet["approved_design"]["sha256"],
    )
    if design_tuple not in ALLOWED_APPROVED_DESIGNS:
        return (
            f"summary.json authority_packet approved_design mismatch: "
            f"observed {design_tuple} not in allowed profile design bindings"
        )

    if a_packet["audited_core"]["relative_path"] != AUDITED_CORE_RELATIVE_PATH:
        return (
            f"summary.json authority_packet audited_core relative_path mismatch: "
            f"expected '{AUDITED_CORE_RELATIVE_PATH}', observed '{a_packet['audited_core']['relative_path']}'"
        )

    if a_packet["audited_cli"]["relative_path"] != AUDITED_CLI_RELATIVE_PATH:
        return (
            f"summary.json authority_packet audited_cli relative_path mismatch: "
            f"expected '{AUDITED_CLI_RELATIVE_PATH}', observed '{a_packet['audited_cli']['relative_path']}'"
        )

    if a_packet["audited_config"]["relative_path"] != AUDITED_CONFIG_RELATIVE_PATH:
        return (
            f"summary.json authority_packet audited_config relative_path mismatch: "
            f"expected '{AUDITED_CONFIG_RELATIVE_PATH}', observed '{a_packet['audited_config']['relative_path']}'"
        )

    if a_packet["frozen_parser"]["relative_path"] != FROZEN_PARSER_RELATIVE_PATH:
        return (
            f"summary.json authority_packet frozen_parser relative_path mismatch: "
            f"expected '{FROZEN_PARSER_RELATIVE_PATH}', observed '{a_packet['frozen_parser']['relative_path']}'"
        )

    net_auth = a_packet["network_authorization"]
    if not isinstance(net_auth, dict) or set(net_auth.keys()) != NETWORK_AUTH_EXACT_KEYS:
        return "summary.json authority_packet network_authorization keys mismatch"
    if net_auth["authorized_run_id"] != run_id:
        return f"network_authorization authorized_run_id mismatch: expected '{run_id}'"
    if net_auth["network_profile_id"] != NETWORK_PROFILE_ID:
        return (
            f"network_authorization network_profile_id mismatch: "
            f"expected '{NETWORK_PROFILE_ID}', observed '{net_auth['network_profile_id']}'"
        )

    if not _is_safe_relative_path(net_auth["relative_path"]):
        return "network_authorization invalid relative_path"
    if not (isinstance(net_auth["sha256"], str) and SHA256_PATTERN.match(net_auth["sha256"])):
        return "network_authorization invalid sha256"

    # Catalog denominator records
    denom = summary["catalog_denominator_records"]
    if not isinstance(denom, list):
        return "summary.json catalog_denominator_records must be a list"
    denom_sort_keys = []
    for idx, d in enumerate(denom):
        if not isinstance(d, dict) or set(d.keys()) != CATALOG_DENOMINATOR_EXACT_KEYS:
            return f"summary.json catalog_denominator_records[{idx}] keys mismatch"
        status = d["candidate_status"]
        if status not in ("not_target_event_type", "catalog_detail_unresolved", "resolved_target_parent"):
            return f"catalog_denominator_records[{idx}] invalid candidate_status: '{status}'"
        if not (isinstance(d["source_article_id"], str) and HEX32_PATTERN.match(d["source_article_id"])):
            return f"catalog_denominator_records[{idx}] invalid source_article_id"
        if not isinstance(d["title"], str):
            return f"catalog_denominator_records[{idx}] title must be string"
        if type(d["release_date_ms"]) is not int or isinstance(d["release_date_ms"], bool):
            return f"catalog_denominator_records[{idx}] release_date_ms must be integer"
        det_id = d["detail_request_id"]
        if status == "not_target_event_type":
            if det_id is not None:
                return f"catalog_denominator_records[{idx}] detail_request_id must be null for not_target_event_type"
        else:
            if type(det_id) is not int or isinstance(det_id, bool) or det_id <= 0:
                return f"catalog_denominator_records[{idx}] detail_request_id must be positive integer"

        sort_k = (d["release_date_ms"], d["source_article_id"])
        if denom_sort_keys and sort_k < denom_sort_keys[-1]:
            return f"catalog_denominator_records is not sorted: index {idx}"
        denom_sort_keys.append(sort_k)

    # Parent records
    parents = summary["parent_records"]
    if not isinstance(parents, list):
        return "summary.json parent_records must be a list"
    parent_sort_keys = []
    for idx, p in enumerate(parents):
        if not isinstance(p, dict) or set(p.keys()) != PARENT_RECORD_EXACT_KEYS:
            return f"summary.json parent_records[{idx}] keys mismatch"
        if not (isinstance(p["source_article_id"], str) and HEX32_PATTERN.match(p["source_article_id"])):
            return f"parent_records[{idx}] invalid source_article_id"
        det_id = p["detail_request_id"]
        if type(det_id) is not int or isinstance(det_id, bool) or det_id <= 0:
            return f"parent_records[{idx}] detail_request_id must be positive integer"

        d_status = p["detail_status"]
        if d_status not in (
            "validated_target_detail",
            "detail_nonpersisted",
            "detail_title_disagreement",
            "detail_parser_unresolved",
        ):
            return f"parent_records[{idx}] invalid detail_status: '{d_status}'"

        p_state = p["parent_state"]
        if p_state not in (
            "coverage_complete",
            "coverage_evidence_gap_detail",
            "coverage_evidence_gap_no_in_scope_usdt_child",
            "coverage_evidence_gap_archive",
        ):
            return f"parent_records[{idx}] invalid parent_state: '{p_state}'"

        sha = p["detail_payload_sha256"]
        children = p["children"]
        if not isinstance(children, list):
            return f"parent_records[{idx}] children must be a list"

        if d_status == "validated_target_detail":
            if not (isinstance(sha, str) and SHA256_PATTERN.match(sha)):
                return f"parent_records[{idx}] detail_payload_sha256 invalid sha256 for validated_target_detail"
        elif d_status == "detail_nonpersisted":
            if sha is not None:
                return f"parent_records[{idx}] detail_payload_sha256 must be null for detail_nonpersisted"
            if children:
                return f"parent_records[{idx}] children must be empty for detail_nonpersisted"
            if p_state != "coverage_evidence_gap_detail":
                return f"parent_records[{idx}] parent_state must be coverage_evidence_gap_detail for detail_nonpersisted"
        else:  # detail_title_disagreement or detail_parser_unresolved
            if not (isinstance(sha, str) and SHA256_PATTERN.match(sha)):
                return f"parent_records[{idx}] detail_payload_sha256 must be sha256 for {d_status}"
            if children:
                return f"parent_records[{idx}] children must be empty for {d_status}"
            if p_state != "coverage_evidence_gap_detail":
                return f"parent_records[{idx}] parent_state must be coverage_evidence_gap_detail for {d_status}"

        for c_idx, c in enumerate(children):
            if not isinstance(c, dict) or set(c.keys()) != CHILD_EXACT_KEYS:
                return f"parent_records[{idx}] children[{c_idx}] keys mismatch"
            if c["child_scope"] not in ("in_scope_usdt", "out_of_scope_non_usdt"):
                return f"parent_records[{idx}] children[{c_idx}] invalid child_scope"
            if not (isinstance(c["symbol"], str) and c["symbol"] and c["symbol"].isupper()):
                return f"parent_records[{idx}] children[{c_idx}] symbol must be nonempty uppercase string"
            if type(c["symbol_launch_time_ms"]) is not int or isinstance(c["symbol_launch_time_ms"], bool):
                return f"parent_records[{idx}] children[{c_idx}] symbol_launch_time_ms must be integer"

        sort_k = p["source_article_id"]
        if parent_sort_keys and sort_k < parent_sort_keys[-1]:
            return f"parent_records is not sorted: index {idx}"
        parent_sort_keys.append(sort_k)

    # Archive package records
    archives = summary["archive_package_records"]
    if not isinstance(archives, list):
        return "summary.json archive_package_records must be a list"
    archive_sort_keys = []
    for idx, a in enumerate(archives):
        if not isinstance(a, dict) or set(a.keys()) != ARCHIVE_PACKAGE_EXACT_KEYS:
            return f"summary.json archive_package_records[{idx}] keys mismatch"
        if not (isinstance(a["parent_article_id"], str) and HEX32_PATTERN.match(a["parent_article_id"])):
            return f"archive_package_records[{idx}] invalid parent_article_id"
        if not (isinstance(a["symbol"], str) and a["symbol"] and a["symbol"].isupper()):
            return f"archive_package_records[{idx}] symbol must be nonempty uppercase string"
        if not (isinstance(a["utc_date"], str) and DATE_PATTERN.match(a["utc_date"])):
            return f"archive_package_records[{idx}] invalid utc_date"

        c_state = a["child_state"]
        if c_state not in (
            "archive_verified_with_post_launch_rows",
            "archive_verified_zero_post_launch_rows",
            "archive_request_nonpersisted",
        ):
            return f"archive_package_records[{idx}] invalid child_state: '{c_state}'"

        row_count = a["post_launch_row_count"]
        delay = a["first_post_launch_trade_delay_ms"]
        first_t = a["first_post_launch_trade_time_ms"]
        last_t = a["last_post_launch_trade_time_ms"]

        if c_state == "archive_verified_with_post_launch_rows":
            if type(a["checksum_request_id"]) is not int or isinstance(a["checksum_request_id"], bool) or a["checksum_request_id"] <= 0:
                return f"archive_package_records[{idx}] checksum_request_id must be positive integer"
            if type(a["zip_request_id"]) is not int or isinstance(a["zip_request_id"], bool) or a["zip_request_id"] <= 0:
                return f"archive_package_records[{idx}] zip_request_id must be positive integer"
            if type(row_count) is not int or isinstance(row_count, bool) or row_count <= 0:
                return f"archive_package_records[{idx}] post_launch_row_count must be positive integer"
            for f_name, f_val in [("trade_delay", delay), ("trade_time_first", first_t), ("trade_time_last", last_t)]:
                if type(f_val) is not int or isinstance(f_val, bool):
                    return f"archive_package_records[{idx}] {f_name} must be integer"
        elif c_state == "archive_verified_zero_post_launch_rows":
            if type(a["checksum_request_id"]) is not int or isinstance(a["checksum_request_id"], bool) or a["checksum_request_id"] <= 0:
                return f"archive_package_records[{idx}] checksum_request_id must be positive integer"
            if type(a["zip_request_id"]) is not int or isinstance(a["zip_request_id"], bool) or a["zip_request_id"] <= 0:
                return f"archive_package_records[{idx}] zip_request_id must be positive integer"
            if row_count != 0 or type(row_count) is not int or isinstance(row_count, bool):
                return f"archive_package_records[{idx}] post_launch_row_count must be 0"
            if delay is not None or first_t is not None or last_t is not None:
                return f"archive_package_records[{idx}] timestamps and trade_delay must be null for zero rows"
        else:  # archive_request_nonpersisted
            if row_count is not None:
                return f"archive_package_records[{idx}] archive_request_nonpersisted.post_launch_row_count expected null, observed {row_count}"
            if delay is not None:
                return f"archive_package_records[{idx}] archive_request_nonpersisted.first_post_launch_trade_delay_ms expected null, observed {delay}"
            if first_t is not None:
                return f"archive_package_records[{idx}] archive_request_nonpersisted.first_post_launch_trade_time_ms expected null, observed {first_t}"
            if last_t is not None:
                return f"archive_package_records[{idx}] archive_request_nonpersisted.last_post_launch_trade_time_ms expected null, observed {last_t}"

        # Logical archive identity
        ident = a["logical_archive_identity"]
        if not isinstance(ident, dict) or set(ident.keys()) != LOGICAL_ARCHIVE_IDENTITY_EXACT_KEYS:
            return f"archive_package_records[{idx}] logical_archive_identity keys mismatch"
        if ident["market"] != "futures_um" or ident["metric"] != "aggTrades":
            return f"archive_package_records[{idx}] logical_archive_identity literals mismatch"
        if (
            ident["parent_article_id"] != a["parent_article_id"]
            or ident["symbol"] != a["symbol"]
            or ident["utc_date"] != a["utc_date"]
        ):
            return f"archive_package_records[{idx}] logical_archive_identity fields mismatch containing record"

        sort_k = (a["parent_article_id"], a["symbol"], a["utc_date"])
        if archive_sort_keys and sort_k < archive_sort_keys[-1]:
            return f"archive_package_records is not sorted: index {idx}"
        archive_sort_keys.append(sort_k)

    # Coverage inventory
    cov = summary["coverage_inventory"]
    if not isinstance(cov, dict) or set(cov.keys()) != COVERAGE_INVENTORY_EXACT_KEYS:
        return "summary.json coverage_inventory keys mismatch"
    for k, v in cov.items():
        if type(v) is not int or isinstance(v, bool) or v < 0:
            return f"summary.json coverage_inventory['{k}'] must be nonnegative integer, observed {v}"

    # Decision & Analysis state
    a_state = summary["analysis_state"]
    decision = summary["decision"]
    valid_pairs = {
        ("coverage_inventory_complete", "stage1_5j_a_historical_archive_coverage_inventory_published"),
        ("coverage_inventory_evidence_gap", "stage1_5j_a_historical_archive_coverage_evidence_gap_published"),
    }
    if (a_state, decision) not in valid_pairs:
        return (
            f"summary.json invalid analysis_state and decision pair: "
            f"observed ('{a_state}', '{decision}')"
        )

    # 4. Request Journal & Completed Projection Check
    journal_file = root_path / "request_journal.jsonl"
    journal_raw = journal_file.read_bytes()
    if journal_raw.startswith(b"\xef\xbb\xbf"):
        return "request_journal.jsonl contains UTF-8 BOM"

    lines = journal_raw.splitlines(keepends=True)
    intents = {}
    terminals = {}
    ordered_request_ids = []

    for line_idx, line in enumerate(lines, 1):
        if not line.endswith(b"\n") or line.endswith(b"\r\n"):
            return f"request_journal.jsonl line {line_idx} must end with '\\n'"
        try:
            rec = json.loads(line.decode("utf-8"))
        except Exception as e:
            return f"request_journal.jsonl line {line_idx} decode error: {e}"

        if not isinstance(rec, dict):
            return f"request_journal.jsonl line {line_idx} must be an object"

        evt = rec.get("event")
        if evt == "request_intent":
            if set(rec.keys()) != INTENT_EXACT_KEYS:
                unexpected = set(rec.keys()) - INTENT_EXACT_KEYS
                missing = INTENT_EXACT_KEYS - set(rec.keys())
                return f"request_journal.jsonl line {line_idx} intent keys mismatch: unexpected={sorted(unexpected)}, missing={sorted(missing)}"
            req_id = rec["request_id"]
            if type(req_id) is not int or isinstance(req_id, bool) or req_id <= 0:
                return f"request_journal.jsonl line {line_idx} invalid request_id"
            if req_id in intents:
                return f"request_journal.jsonl duplicate intent request_id {req_id}"

            # Contiguous ascending request IDs
            expected_next_id = len(ordered_request_ids) + 1
            if req_id != expected_next_id:
                return f"request_journal.jsonl non-contiguous request_id {req_id}, expected {expected_next_id}"
            ordered_request_ids.append(req_id)

            if rec["request_state"] != "admitted_pending":
                return f"request_journal.jsonl line {line_idx} request_state must be 'admitted_pending'"

            kind = rec["request_kind"]
            if kind not in REQUEST_KINDS:
                return f"request_journal.jsonl line {line_idx} invalid request_kind '{kind}'"

            # Context applicability
            p_id = rec["parent_article_id"]
            sym = rec["symbol"]
            u_date = rec["utc_date"]
            if kind == "catalog":
                if p_id is not None or sym is not None or u_date is not None:
                    return f"request_journal.jsonl line {line_idx} catalog intent context fields must be null"
            elif kind == "detail":
                if not (isinstance(p_id, str) and HEX32_PATTERN.match(p_id)) or sym is not None or u_date is not None:
                    return f"request_journal.jsonl line {line_idx} detail intent context mismatch"
            else:  # archive or checksum
                if (
                    not (isinstance(p_id, str) and HEX32_PATTERN.match(p_id))
                    or not (isinstance(sym, str) and sym and sym.isupper())
                    or not (isinstance(u_date, str) and DATE_PATTERN.match(u_date))
                ):
                    return f"request_journal.jsonl line {line_idx} {kind} intent context mismatch"

            intents[req_id] = rec

        elif evt == "request_terminal":
            if set(rec.keys()) != TERMINAL_EXACT_KEYS:
                unexpected = set(rec.keys()) - TERMINAL_EXACT_KEYS
                missing = TERMINAL_EXACT_KEYS - set(rec.keys())
                return f"request_journal.jsonl line {line_idx} terminal keys mismatch: unexpected={sorted(unexpected)}, missing={sorted(missing)}"
            req_id = rec["request_id"]
            if req_id not in intents:
                return f"request_journal.jsonl terminal before intent for request_id {req_id}"
            if req_id in terminals:
                return f"request_journal.jsonl duplicate terminal for request_id {req_id}"

            t_state = rec["request_state"]
            if t_state not in TERMINAL_STATES:
                return f"request_journal.jsonl invalid terminal request_state '{t_state}'"

            status = rec["http_status"]
            err = rec["transport_error"]
            r_bytes = rec["response_bytes"]
            r_path = rec["response_relative_path"]
            r_sha = rec["response_sha256"]

            if t_state == "response_persisted":
                if status != 200 or err is not None:
                    return "request_journal.jsonl response_persisted must have status=200, err=null"
                if type(r_bytes) is not int or isinstance(r_bytes, bool) or r_bytes <= 0:
                    return "request_journal.jsonl response_persisted invalid response_bytes"
                if not (isinstance(r_path, str) and _is_safe_relative_path(r_path)):
                    return "request_journal.jsonl response_persisted invalid response_relative_path"
                if not (isinstance(r_sha, str) and SHA256_PATTERN.match(r_sha)):
                    return "request_journal.jsonl response_persisted invalid response_sha256"
            elif t_state == "http_not_found":
                if status != 404 or err is not None or r_bytes is not None or r_path is not None or r_sha is not None:
                    return "request_journal.jsonl http_not_found fields mismatch"
            elif t_state == "transport_inconclusive":
                if status is not None or not (isinstance(err, str) and err) or r_bytes is not None or r_path is not None or r_sha is not None:
                    return "request_journal.jsonl transport_inconclusive fields mismatch"
            else:  # response_rejected
                if type(status) is not int or isinstance(status, bool) or status in (200, 404) or err is not None or r_bytes is not None or r_path is not None or r_sha is not None:
                    return "request_journal.jsonl response_rejected fields mismatch"


            terminals[req_id] = rec
        else:
            return f"request_journal.jsonl line {line_idx} unknown event: '{evt}'"

    # Check for dangling intents
    if len(intents) != len(terminals):
        dangling = set(intents.keys()) - set(terminals.keys())
        return f"request_journal.jsonl dangling intents without terminal: {sorted(dangling)}"

    # Build completed projection and compare with summary.request_records
    completed_projection = []
    for req_id in ordered_request_ids:
        intent = intents[req_id]
        terminal = terminals[req_id]
        t_state = terminal["request_state"]
        http_status_or_transport_error = (
            terminal["http_status"]
            if t_state != "transport_inconclusive"
            else terminal["transport_error"]
        )
        row = {
            "http_status_or_transport_error": http_status_or_transport_error,
            "request_id": intent["request_id"],
            "request_kind": intent["request_kind"],
            "request_state": terminal["request_state"],
            "response_bytes": terminal["response_bytes"],
            "response_relative_path": terminal["response_relative_path"],
            "response_sha256": terminal["response_sha256"],
            "url": intent["url"],
        }
        completed_projection.append(row)

    observed_requests = summary["request_records"]
    if observed_requests != completed_projection:
        return (
            f"summary.json request_records projection mismatch with journal: "
            f"expected {completed_projection}, observed {observed_requests}"
        )

    # Persisted response paths must point to manifest members with matching sha
    for row in completed_projection:
        p_path = row["response_relative_path"]
        if p_path is not None:
            # Must point to root_relative_path/<subpath>
            prefix = f"{manifest['root_relative_path']}/"
            if not p_path.startswith(prefix):
                return f"request_records response_relative_path '{p_path}' does not start with '{prefix}'"
            subpath = p_path[len(prefix):]
            if subpath not in manifest_map:
                return f"request_records response_relative_path '{subpath}' not found in manifest"
            if manifest_map[subpath]["sha256"] != row["response_sha256"]:
                return f"request_records response_sha256 mismatch with manifest member '{subpath}'"

    return None


# -----------------------------------------------------------------------------
# Main CLI Entrypoint
# -----------------------------------------------------------------------------


def main(argv=None) -> int:
    """CLI Entrypoint.

    Returns:
        0: Verified conformant
        1: Contract violation
        2: CLI / usage error
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Governance Cross-Boundary Artifact Schema Integrity Verifier"
    )
    parser.add_argument("--profile", required=True, help="Profile ID to verify against")
    parser.add_argument("--artifact-root", required=True, help="Project-relative artifact root path")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    if args.profile not in SUPPORTED_PROFILES:
        sys.stderr.write(f"Error: Unsupported profile '{args.profile}'. Supported: {sorted(SUPPORTED_PROFILES)}\n")
        return 2

    # Path sanitization
    artifact_root_arg = args.artifact_root
    if not artifact_root_arg:
        sys.stderr.write("Error: --artifact-root cannot be empty\n")
        return 2

    if artifact_root_arg.startswith("/") or artifact_root_arg.startswith("\\"):
        sys.stderr.write("Error: --artifact-root must be a project-relative path, not absolute\n")
        return 2

    parts = artifact_root_arg.replace("\\", "/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        sys.stderr.write("Error: --artifact-root contains invalid segments (empty, '.', or '..')\n")
        return 2

    # Project root is fixed relative to this file: parents[2]
    project_root = Path(__file__).resolve().parents[2]
    target_path = project_root / artifact_root_arg

    if not target_path.exists():
        sys.stderr.write(f"Error: Artifact root does not exist: {target_path}\n")
        return 2

    # Check symlinks in lexical path ancestors from project_root to target_path
    curr = project_root
    for segment in parts:
        curr = curr / segment
        if os.path.islink(curr):
            sys.stderr.write(f"Contract violation: Path component is a symlink: {curr}\n")
            return 1

    # Execute verification
    diag = verify_stage1_5j_a_receipt_v1(project_root, artifact_root_arg)
    if diag:
        sys.stderr.write(f"Contract violation [{args.profile}]: {diag}\n")
        return 1

    sys.stdout.write(f"SUCCESS: Artifact root '{artifact_root_arg}' is conformant with '{args.profile}'\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
