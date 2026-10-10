"""Stage 1.5J-A Historical Archive Coverage Inventory.

Production core module implementing:
- Authority packet verification (implementation authority and future network authorization)
- Append-only durable request journal state machine
- Stable two-pass catalog denominator and sentinel logic
- Detail envelope validation and frozen parser symbol projection
- Daily USD-M aggTrades archive package (ZIP/CHECKSUM/CSV) streaming validation
- Descriptive coverage inventory reduction
- Atomic sealed receipt publication with shared parent flock
- Strict loader replaying raw journal/parser/archive reductions
"""

from __future__ import annotations

import csv
import fcntl
import hashlib
import http.client
import importlib
import io
import json
import os
import re
import sys
import urllib.parse
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from configs.base import (
    EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE,
    EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_LIMIT_PER_PASS,
    EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_SIZE,
    EXTERNAL_SIGNAL_STAGE1_5J_A_HTTP_TIMEOUT_SEC,
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_COMPRESSION_RATIO,
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_REQUESTS,
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_ZIP_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_BAPI_RESPONSE_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CATALOG_REQUESTS,
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CHECKSUM_RESPONSE_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_DETAIL_REQUESTS,
    RISK_LIVE_TRADING_ENABLED,
)

__all__ = [
    "run_inventory",
    "verify_execution_authority",
    "verify_network_authorization",
    "load_verified_stage1_5j_a_historical_archive_coverage_root",
    "classify_stage1_5j_a_historical_archive_coverage_root_state",
]

# Immutable Design & Plan Bindings
APPROVED_DESIGN_REL_PATH = "docs/designs/2026-10-09-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-design-delta_CN.md"
APPROVED_DESIGN_SHA256 = "f427df9435c8b9c8dd2b4b45c24bbbbd595df2c7e8d209f40f6fe2cd13b00f3c"
APPROVED_PLAN_REL_PATH = "docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan-r1_CN.md"
APPROVED_PLAN_SHA256 = "b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82"
PLANNING_BASE_SHA = "647fae2cf3ba09efc1971bb1a87a30e18b86dd5b"
FROZEN_PARSER_REL_PATH = "src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py"
FROZEN_PARSER_SHA256 = "7e0e696647acf158facbdd8d3d39351bbc68c33b039871f26f4a38bc75ad56e5"

OUTPUT_PARENT_REL = Path("data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory")

UNIVERSE_START_MS = 1759276800000  # 2025-10-01T00:00:00.000Z
UNIVERSE_END_MS = 1790812800000    # 2026-10-01T00:00:00.000Z, exclusive
PRESENCE_WINDOW_MS = 14400000      # 4 hours

NETWORK_PROFILE_ID = "stage1_5j_a_public_archive_inventory_v1"

EXPECTED_13_FALSE_FLAGS: dict[str, bool] = {
    "alpha_claim_allowed": False,
    "alpha_interpretation_allowed": False,
    "commit_allowed": False,
    "deployment_allowed": False,
    "execution_allowed": False,
    "live_trading_allowed": False,
    "network_allowed_after_run": False,
    "paper_trading_allowed": False,
    "pnl_calculation_allowed": False,
    "price_response_calculation_allowed": False,
    "receipt_generation_allowed_without_authorization": False,
    "replay_allowed": False,
    "signal_generation_allowed": False,
}

AUTHORITY_EXACT_KEYS = {
    "approved_design_path",
    "approved_design_sha256",
    "approved_plan_path",
    "approved_plan_sha256",
    "base_sha",
    "current_plan_sha256",
    "project_root",
}

AUTHORITY_PACKET_EXACT_KEYS = {
    "approved_design",
    "approved_plan",
    "audited_cli",
    "audited_config",
    "audited_core",
    "frozen_parser",
    "network_authorization",
}

SUMMARY_EXACT_KEYS = {
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

INTENT_EXACT_KEYS = frozenset({
    "event",
    "parent_article_id",
    "request_id",
    "request_kind",
    "request_state",
    "symbol",
    "url",
    "utc_date",
})

TERMINAL_EXACT_KEYS = frozenset({
    "event",
    "http_status",
    "request_id",
    "request_state",
    "response_bytes",
    "response_relative_path",
    "response_sha256",
    "transport_error",
})

VALID_TERMINAL_STATES = frozenset({
    "response_persisted",
    "http_not_found",
    "transport_inconclusive",
    "response_rejected",
})

RUN_ID_REGEX = re.compile(r"^stage1_5j_a_historical_archive_coverage_inventory_\d{8}T\d{6}Z$")


class Stage1_5JADiagnosticError(Exception):
    """Base exception for Stage 1.5J-A diagnostic errors."""
    pass


class Stage1_5JAPostRenameDurabilityFailure(Stage1_5JADiagnosticError):
    """Raised when fsync fails after atomic rename, indicating durability failure."""
    pass


def _is_positive_non_bool_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _validate_archive_package_record(record: dict[str, Any]) -> None:
    """Validates archive package record nullability invariants for archive_request_nonpersisted."""
    if record.get("child_state") == "archive_request_nonpersisted":
        if (
            record.get("post_launch_row_count") is not None
            or record.get("first_post_launch_trade_delay_ms") is not None
            or record.get("first_post_launch_trade_time_ms") is not None
            or record.get("last_post_launch_trade_time_ms") is not None
        ):
            raise Stage1_5JADiagnosticError(
                "STOP=stage1_5j_a_archive_package_record_invalid:archive_request_nonpersisted_trade_fields_must_be_null"
            )


def _admit_parent_detail(
    row: dict[str, Any],
    detail_payload: dict[str, Any],
    detail_sha: str | None,
    parser_mod: Any = None,
) -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
    """Admits target parent detail in producer pipeline.

    Evaluates event classification, parsed structure, and positive non-bool integer launch times.
    Mutates row["candidate_status"] and returns (parent_record, in_scope_children).
    When admission fails (unresolved), in_scope_children is None.
    """
    if parser_mod is None:
        parser_mod = _import_verified_frozen_parser()
    source_article_id = row["source_article_id"]
    detail_data = validate_detail_envelope(detail_payload, source_article_id)
    detail_title = detail_data["title"]

    detail_cat_type = parser_mod.classify_event_type(detail_title)
    if detail_cat_type != EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE:
        row["candidate_status"] = "catalog_detail_unresolved"
        parent_rec = {
            "children": [],
            "detail_payload_sha256": detail_sha,
            "detail_request_id": row["detail_request_id"],
            "detail_status": "detail_title_disagreement",
            "parent_state": "coverage_evidence_gap_detail",
            "source_article_id": source_article_id,
        }
        return parent_rec, None

    extracted = parser_mod.extract_symbol_candidates_from_bapi_article_payload(detail_payload)
    if extracted.get("parser_status") != "parsed":
        row["candidate_status"] = "catalog_detail_unresolved"
        parent_rec = {
            "children": [],
            "detail_payload_sha256": detail_sha,
            "detail_request_id": row["detail_request_id"],
            "detail_status": "detail_parser_unresolved",
            "parent_state": "coverage_evidence_gap_detail",
            "source_article_id": source_article_id,
        }
        return parent_rec, None

    all_launch_valid = all(
        _is_positive_non_bool_integer(extracted.get("symbol_launch_times_ms", {}).get(s))
        for s in extracted.get("symbols", [])
    )
    if not all_launch_valid:
        row["candidate_status"] = "catalog_detail_unresolved"
        parent_rec = {
            "children": [],
            "detail_payload_sha256": detail_sha,
            "detail_request_id": row["detail_request_id"],
            "detail_status": "detail_parser_unresolved",
            "parent_state": "coverage_evidence_gap_detail",
            "source_article_id": source_article_id,
        }
        return parent_rec, None

    row["candidate_status"] = "resolved_target_parent"
    children = []
    for sym in extracted.get("symbols", []):
        child_scope = "in_scope_usdt" if sym.endswith("USDT") else "out_of_scope_non_usdt"
        launch_time = extracted.get("symbol_launch_times_ms", {}).get(sym)
        children.append({
            "child_scope": child_scope,
            "symbol": sym,
            "symbol_launch_time_ms": launch_time,
        })
    in_scope_children = [c for c in children if c["child_scope"] == "in_scope_usdt"]
    parent_rec = {
        "children": children,
        "detail_payload_sha256": detail_sha,
        "detail_request_id": row["detail_request_id"],
        "detail_status": "validated_target_detail",
        "parent_state": "coverage_complete",
        "source_article_id": source_article_id,
    }
    return parent_rec, in_scope_children


def _replay_parent_detail_admission(
    detail_payload: dict[str, Any],
    parent_record: dict[str, Any],
    denominator_record: dict[str, Any] | None = None,
    parser_mod: Any = None,
) -> None:
    """Replays target parent detail parsing and launch-time admission per Sections 5.3 and 7."""
    if parser_mod is None:
        parser_mod = _import_verified_frozen_parser()
    pid = parent_record["source_article_id"]
    detail_data = validate_detail_envelope(detail_payload, pid)
    detail_title = detail_data["title"]
    det_type = parser_mod.classify_event_type(detail_title)
    if det_type != EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE:
        if parent_record["detail_status"] != "detail_title_disagreement":
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_detail_status:{pid}")
        if denominator_record is not None and denominator_record.get("candidate_status") != "catalog_detail_unresolved":
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:candidate_status_mismatch:{pid}")
        return

    extracted = parser_mod.extract_symbol_candidates_from_bapi_article_payload(detail_payload)
    if extracted.get("parser_status") != "parsed":
        if parent_record["detail_status"] != "detail_parser_unresolved":
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_detail_status:{pid}")
        if denominator_record is not None and denominator_record.get("candidate_status") != "catalog_detail_unresolved":
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:candidate_status_mismatch:{pid}")
        return

    all_launch_valid = all(
        _is_positive_non_bool_integer(extracted.get("symbol_launch_times_ms", {}).get(sym))
        for sym in extracted.get("symbols", [])
    )
    if not all_launch_valid:
        if denominator_record is not None and denominator_record.get("candidate_status") != "catalog_detail_unresolved":
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:candidate_status_mismatch:{pid}")
        if parent_record["detail_status"] != "detail_parser_unresolved":
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_detail_status:{pid}")
        if parent_record.get("children") != []:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:children_mismatch:{pid}")
        if parent_record.get("parent_state") != "coverage_evidence_gap_detail":
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_state_mismatch:{pid}")
        return

    if denominator_record is not None and denominator_record.get("candidate_status") != "resolved_target_parent":
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:candidate_status_mismatch:{pid}")
    if parent_record["detail_status"] != "validated_target_detail":
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_detail_status:{pid}")

    exp_children = []
    for sym in extracted.get("symbols", []):
        child_scope = "in_scope_usdt" if sym.endswith("USDT") else "out_of_scope_non_usdt"
        launch_time = extracted.get("symbol_launch_times_ms", {}).get(sym)
        exp_children.append({
            "child_scope": child_scope,
            "symbol": sym,
            "symbol_launch_time_ms": launch_time,
        })
    if parent_record.get("children") != exp_children:
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:children_mismatch:{pid}")


def _compute_required_archive_utc_dates(launch_time_ms: int) -> list[str]:
    """Computes sorted deduplicated UTC calendar dates intersecting [launch_time_ms, launch_time_ms + PRESENCE_WINDOW_MS]."""
    if not isinstance(launch_time_ms, int) or isinstance(launch_time_ms, bool):
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_invalid_launch_time: {launch_time_ms}")
    end_time_ms = launch_time_ms + PRESENCE_WINDOW_MS
    start_day = launch_time_ms // 86_400_000
    end_day = end_time_ms // 86_400_000
    dates = []
    for d in range(start_day, end_day + 1):
        dt = datetime.fromtimestamp(d * 86400, tz=timezone.utc)
        dates.append(dt.strftime("%Y-%m-%d"))
    return sorted(set(dates))


def _validate_intent_context_applicability(
    kind: str,
    parent_article_id: Any,
    symbol: Any,
    utc_date: Any,
) -> None:
    """Validates intent context fields per approved Delta Section 3.1:

    parent_article_id, symbol, and utc_date are null only when not applicable to that request kind.
    - catalog: parent_article_id, symbol, and utc_date must all be null.
    - detail: parent_article_id must be a non-empty string; symbol and utc_date must be null.
    - archive, checksum: parent_article_id, symbol, and utc_date must all be non-empty strings.
    """
    if kind == "catalog":
        if parent_article_id is not None or symbol is not None or utc_date is not None:
            raise Stage1_5JADiagnosticError(
                "STOP=stage1_5j_a_journal_invalid:intent_context_inapplicable:catalog"
            )
    elif kind == "detail":
        if (
            not isinstance(parent_article_id, str)
            or not parent_article_id
            or symbol is not None
            or utc_date is not None
        ):
            raise Stage1_5JADiagnosticError(
                "STOP=stage1_5j_a_journal_invalid:intent_context_inapplicable:detail"
            )
    elif kind in ("archive", "checksum"):
        if (
            not isinstance(parent_article_id, str)
            or not parent_article_id
            or not isinstance(symbol, str)
            or not symbol
            or not isinstance(utc_date, str)
            or not utc_date
        ):
            raise Stage1_5JADiagnosticError(
                f"STOP=stage1_5j_a_journal_invalid:intent_context_inapplicable:{kind}"
            )
    else:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_journal_invalid:intent_kind_invalid:{kind}"
        )


def _validate_request_journal_lines(
    journal_lines: list[str],
) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]], list[dict[str, Any]]]:
    """Validates raw request journal lines per approved Delta Section 3.1 and returns intents, terminals, replayed_records."""
    seen_intent_rids: set[int] = set()
    seen_terminal_rids: set[int] = set()
    intents: dict[int, dict[str, Any]] = {}
    terminals: dict[int, dict[str, Any]] = {}

    for line in journal_lines:
        line_str = line.strip()
        if not line_str:
            continue
        try:
            entry = json.loads(line_str)
        except Exception as e:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_journal_invalid: {e}") from e

        ev = entry.get("event")
        rid = entry.get("request_id")
        if not isinstance(rid, int) or isinstance(rid, bool) or rid <= 0:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_journal_invalid:invalid_request_id:{rid}")

        if ev == "request_intent":
            if set(entry.keys()) != INTENT_EXACT_KEYS:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:intent_keys_mismatch")
            if entry.get("request_state") != "admitted_pending":
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:intent_state_invalid")
            kind = entry.get("request_kind")
            if kind not in ("catalog", "detail", "archive", "checksum"):
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:intent_kind_invalid")
            _validate_intent_context_applicability(
                kind=kind,
                parent_article_id=entry.get("parent_article_id"),
                symbol=entry.get("symbol"),
                utc_date=entry.get("utc_date"),
            )
            if rid in seen_intent_rids:
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_journal_invalid:duplicate_intent:{rid}")
            seen_intent_rids.add(rid)
            intents[rid] = entry

        elif ev == "request_terminal":
            if set(entry.keys()) != TERMINAL_EXACT_KEYS:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:terminal_keys_mismatch")
            if rid in seen_terminal_rids:
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_journal_invalid:duplicate_terminal:{rid}")
            if rid not in seen_intent_rids:
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_journal_invalid:terminal_without_intent:{rid}")

            req_state = entry.get("request_state")
            if req_state not in VALID_TERMINAL_STATES:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:terminal_state_invalid")

            status = entry.get("http_status")
            err = entry.get("transport_error")
            resp_bytes = entry.get("response_bytes")
            resp_rel = entry.get("response_relative_path")
            resp_sha = entry.get("response_sha256")

            # Check state combinations per Delta Section 3.1
            if req_state == "response_persisted":
                if (
                    status != 200
                    or err is not None
                    or not isinstance(resp_rel, str)
                    or not resp_rel
                    or not isinstance(resp_sha, str)
                    or len(resp_sha) != 64
                    or not isinstance(resp_bytes, int)
                    or isinstance(resp_bytes, bool)
                    or resp_bytes <= 0
                ):
                    raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:terminal_combination_invalid")
            elif req_state == "http_not_found":
                if status != 404 or err is not None or resp_rel is not None or resp_sha is not None or resp_bytes is not None:
                    raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:terminal_combination_invalid")
            elif req_state == "transport_inconclusive":
                if status is not None or not isinstance(err, str) or not err or resp_rel is not None or resp_sha is not None or resp_bytes is not None:
                    raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:terminal_combination_invalid")
            elif req_state == "response_rejected":
                if not isinstance(status, int) or isinstance(status, bool) or status in (200, 404) or err is not None or resp_rel is not None or resp_sha is not None or resp_bytes is not None:
                    raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:terminal_combination_invalid")

            seen_terminal_rids.add(rid)
            terminals[rid] = entry
        else:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_journal_invalid:unknown_event:{ev}")

    if seen_intent_rids != seen_terminal_rids:
        missing_terminals = seen_intent_rids - seen_terminal_rids
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_journal_invalid:intent_terminal_mismatch:{missing_terminals}")

    all_rids = sorted(terminals.keys())
    if all_rids != list(range(1, len(all_rids) + 1)):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_journal_invalid:non_contiguous_request_ids")

    replayed_records = []
    for rid in all_rids:
        intent = intents[rid]
        term = terminals[rid]
        http_or_err = term["http_status"] if term["http_status"] is not None else term["transport_error"]
        replayed_records.append({
            "http_status_or_transport_error": http_or_err,
            "request_id": rid,
            "request_kind": intent["request_kind"],
            "request_state": term["request_state"],
            "response_bytes": term["response_bytes"],
            "response_relative_path": term["response_relative_path"],
            "response_sha256": term["response_sha256"],
            "url": intent["url"],
        })

    return intents, terminals, replayed_records


def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


_MACOS_SYSTEM_ROOT_SYMLINKS: set[Path] = {Path("/tmp"), Path("/var"), Path("/etc")}


def _assert_no_symlinks(path: Path) -> None:
    current = path
    while True:
        if current.is_symlink() and current not in _MACOS_SYSTEM_ROOT_SYMLINKS:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_symlink_detected: {current}")
        parent = current.parent
        if parent == current:
            break
        current = parent


def _resolve_project_root() -> Path:
    # Anchor to directory containing this file: src/research/external_signal_shadow
    here = Path(__file__).resolve()
    _assert_no_symlinks(Path(__file__))
    project_root = here.parent.parent.parent.parent
    _assert_no_symlinks(project_root)
    return project_root


def get_canonical_execution_authority_bundle_path(project_root: Path | None = None) -> Path:
    root = project_root or _resolve_project_root()
    return root / ".git" / "plan-execution" / "stage1_5j_a" / APPROVED_PLAN_SHA256


def _fsync_file(fd: int) -> None:
    os.fsync(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


# =========================================================================
# Authority Verification
# =========================================================================


def _verify_execution_authority_for_test(
    authority_bundle_dir: Path,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Internal validator for Task 0 implementation authority packet, supporting test isolation."""
    root = project_root or _resolve_project_root()
    bundle_dir = authority_bundle_dir

    if RISK_LIVE_TRADING_ENABLED is not False:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_financial_safety_violated:live_trading_enabled")

    if not bundle_dir.is_dir():
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_execution_authority_missing: {bundle_dir}"
        )

    _assert_no_symlinks(bundle_dir)

    # Must contain exactly the 5 authority files (ignoring optional evidence/ directory)
    entries = sorted([p.name for p in bundle_dir.iterdir() if p.name != "evidence"])
    expected_entries = sorted([
        "base_sha",
        "execution_authority.json",
        "execution_authority.sha256",
        "implementation_authorization.sha256",
        "implementation_authorization.txt",
    ])
    missing = set(expected_entries) - set(entries)
    if missing:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_execution_authority_packet_invalid:missing_entries:{sorted(missing)}"
        )

    optional_network_entries = {"network_authorization.txt", "network_authorization.sha256"}
    net_present = optional_network_entries.intersection(entries)
    if len(net_present) == 1:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_execution_authority_packet_invalid:network_authorization_incomplete:{sorted(net_present)}"
        )

    extra = set(entries) - set(expected_entries) - optional_network_entries
    if extra:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_execution_authority_packet_invalid:unexpected_entries:{sorted(extra)}"
        )

    for name in expected_entries:
        p = bundle_dir / name
        if p.is_symlink():
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_execution_authority_symlink_detected: {p}")
        if not p.is_file():
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_execution_authority_not_regular_file: {p}")

    if len(net_present) == 2:
        for name in sorted(optional_network_entries):
            p = bundle_dir / name
            if p.is_symlink():
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_execution_authority_symlink_detected: {p}")
            if not p.is_file():
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_execution_authority_not_regular_file: {p}")

    # Validate implementation_authorization.txt
    auth_file = bundle_dir / "implementation_authorization.txt"
    auth_bytes = auth_file.read_bytes()
    expected_auth_line1 = (
        f"我批准实施 Plan：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。\n"
    )
    expected_auth_line2 = (
        "允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action.\n"
    )
    expected_auth_text = expected_auth_line1 + expected_auth_line2
    if auth_bytes.decode("utf-8") != expected_auth_text:
        raise Stage1_5JADiagnosticError(
            "STOP=stage1_5j_a_execution_authority_sidecar_mismatch:implementation_authorization"
        )

    # Validate implementation_authorization.sha256 sidecar (exact bytes, trailing LF required)
    auth_sidecar_bytes = (bundle_dir / "implementation_authorization.sha256").read_bytes()
    expected_auth_sidecar = f"{_sha256(auth_bytes)}  implementation_authorization.txt\n".encode("utf-8")
    if auth_sidecar_bytes != expected_auth_sidecar:
        raise Stage1_5JADiagnosticError(
            "STOP=stage1_5j_a_execution_authority_sidecar_mismatch:implementation_authorization"
        )

    # Validate execution_authority.json sidecar (exact bytes, trailing LF required)
    json_file = bundle_dir / "execution_authority.json"
    json_bytes = json_file.read_bytes()
    json_sidecar_bytes = (bundle_dir / "execution_authority.sha256").read_bytes()
    expected_json_sidecar = f"{_sha256(json_bytes)}  execution_authority.json\n".encode("utf-8")
    if json_sidecar_bytes != expected_json_sidecar:
        raise Stage1_5JADiagnosticError(
            "STOP=stage1_5j_a_execution_authority_sidecar_mismatch:execution_authority"
        )

    # Parse and validate JSON content
    try:
        authority_data = json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_execution_authority_json_invalid: {e}"
        ) from e

    # Require exact canonical JSON format with trailing LF
    expected_canonical_json = canonical_json_dumps(authority_data) + "\n"
    if json_bytes.decode("utf-8") != expected_canonical_json:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_json_not_canonical")

    if set(authority_data.keys()) != AUTHORITY_EXACT_KEYS:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_execution_authority_json_keys_invalid: {sorted(authority_data.keys())}"
        )

    if authority_data["approved_design_path"] != APPROVED_DESIGN_REL_PATH:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:design_path_mismatch")
    if authority_data["approved_design_sha256"] != APPROVED_DESIGN_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:design_sha_mismatch")
    if authority_data["approved_plan_path"] != APPROVED_PLAN_REL_PATH:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:plan_path_mismatch")
    if authority_data["approved_plan_sha256"] != APPROVED_PLAN_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:plan_sha_mismatch")
    if authority_data["current_plan_sha256"] != APPROVED_PLAN_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:current_plan_sha_mismatch")
    if authority_data["base_sha"] != PLANNING_BASE_SHA:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:base_sha_mismatch")

    # Validate base_sha file (exact bytes, trailing LF required)
    base_sha_bytes = (bundle_dir / "base_sha").read_bytes()
    expected_base_sha_bytes = f"{PLANNING_BASE_SHA}\n".encode("utf-8")
    if base_sha_bytes != expected_base_sha_bytes:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:base_sha_file_mismatch")

    # Validate project root
    if Path(authority_data["project_root"]).resolve() != root.resolve():
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:project_root_mismatch")

    # Validate actual current approved Design and Plan files on disk
    current_design_file = root / APPROVED_DESIGN_REL_PATH
    if not current_design_file.is_file() or _file_sha256(current_design_file) != APPROVED_DESIGN_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:current_design_file_sha_mismatch")

    current_plan_file = root / APPROVED_PLAN_REL_PATH
    if not current_plan_file.is_file() or _file_sha256(current_plan_file) != APPROVED_PLAN_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_execution_authority_drift:current_plan_file_sha_mismatch")

    return authority_data


def verify_execution_authority() -> dict[str, Any]:
    """Sole public validator for Task 0 implementation authority packet.

    Takes strictly zero arguments. Binds only the canonical project authority bundle.
    """
    root = _resolve_project_root()
    bundle_dir = get_canonical_execution_authority_bundle_path(root)
    return _verify_execution_authority_for_test(authority_bundle_dir=bundle_dir, project_root=root)


def _verify_network_authorization_for_test(
    run_id: str,
    bundle_dir: Path,
    project_root: Path | None = None,
) -> dict[str, str]:
    """Validates future network authorization packet, supporting isolated test bundles."""
    root = project_root or _resolve_project_root()
    bundle = bundle_dir

    _assert_no_symlinks(bundle)

    net_auth_file = bundle / "network_authorization.txt"
    net_sidecar_file = bundle / "network_authorization.sha256"

    if not net_auth_file.is_file():
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_network_authorization_absent: {net_auth_file}"
        )
    if not net_sidecar_file.is_file():
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_network_authorization_sidecar_missing: {net_sidecar_file}"
        )

    _assert_no_symlinks(net_auth_file)
    _assert_no_symlinks(net_sidecar_file)

    auth_bytes = net_auth_file.read_bytes()
    sidecar_bytes = net_sidecar_file.read_bytes()
    expected_sidecar_bytes = f"{_sha256(auth_bytes)}  network_authorization.txt\n".encode("utf-8")
    if sidecar_bytes != expected_sidecar_bytes:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_sidecar_mismatch")

    lines = auth_bytes.decode("utf-8").splitlines()
    expected_line_count = 12
    if len(lines) != expected_line_count:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:grammar_invalid")

    parsed: dict[str, str] = {}
    expected_keys = [
        "APPROVED_DESIGN_SHA256",
        "APPROVED_PLAN_SHA256",
        "AUTHORIZED_RUN_ID",
        "APPROVED_J_A_CORE_SHA256",
        "APPROVED_J_A_CLI_SHA256",
        "APPROVED_CONFIG_SHA256",
        "APPROVED_PARSER_SHA256",
        "NETWORK_PROFILE_ID",
        "CATALOG_PAGE_LIMIT_PER_PASS",
        "MAX_CATALOG_REQUESTS",
        "MAX_DETAIL_REQUESTS",
        "MAX_ARCHIVE_REQUESTS",
    ]

    for i, line in enumerate(lines):
        if "=" not in line:
            raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:grammar_invalid")
        k, v = line.split("=", 1)
        if k != expected_keys[i]:
            raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:grammar_invalid")
        parsed[k] = v

    if parsed["APPROVED_DESIGN_SHA256"] != APPROVED_DESIGN_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:design_sha_mismatch")
    if parsed["APPROVED_PLAN_SHA256"] != APPROVED_PLAN_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:plan_sha_mismatch")
    if parsed["AUTHORIZED_RUN_ID"] != run_id:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:run_id_mismatch")
    if parsed["APPROVED_PARSER_SHA256"] != FROZEN_PARSER_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:parser_sha_mismatch")
    if parsed["NETWORK_PROFILE_ID"] != NETWORK_PROFILE_ID:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:profile_id_invalid")

    if parsed["CATALOG_PAGE_LIMIT_PER_PASS"] != str(EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_LIMIT_PER_PASS):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:cap_mismatch:CATALOG_PAGE_LIMIT_PER_PASS")
    if parsed["MAX_CATALOG_REQUESTS"] != str(EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CATALOG_REQUESTS):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:cap_mismatch:MAX_CATALOG_REQUESTS")
    if parsed["MAX_DETAIL_REQUESTS"] != str(EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_DETAIL_REQUESTS):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:cap_mismatch:MAX_DETAIL_REQUESTS")
    if parsed["MAX_ARCHIVE_REQUESTS"] != str(EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_REQUESTS):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:cap_mismatch:MAX_ARCHIVE_REQUESTS")

    # Verify actual source hashes on disk
    config_file = root / "configs" / "base.py"
    if parsed["APPROVED_CONFIG_SHA256"] != _file_sha256(config_file):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:config_sha_mismatch")

    core_file = root / "src" / "research" / "external_signal_shadow" / "stage1_5j_a_historical_archive_coverage_inventory.py"
    if parsed["APPROVED_J_A_CORE_SHA256"] != _file_sha256(core_file):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:core_sha_mismatch")

    cli_file = root / "scripts" / "external_signal_shadow" / "run_stage1_5j_a_historical_archive_coverage_inventory.py"
    if not cli_file.is_file() or parsed["APPROVED_J_A_CLI_SHA256"] != _file_sha256(cli_file):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_network_authorization_mismatch:cli_sha_mismatch")

    parsed["file_sha256"] = _sha256(auth_bytes)
    return parsed


def verify_network_authorization(run_id: str) -> dict[str, str]:
    """Sole public validator for future network authorization packet.

    Takes strictly only run_id. Binds only the canonical project authority bundle.
    """
    root = _resolve_project_root()
    bundle = get_canonical_execution_authority_bundle_path(root)
    return _verify_network_authorization_for_test(run_id=run_id, bundle_dir=bundle, project_root=root)


def _import_verified_frozen_parser(project_root: Path | None = None) -> Any:
    """Verifies and imports the frozen parser module with strict origin and SHA check."""
    root = project_root or _resolve_project_root()
    parser_path = root / FROZEN_PARSER_REL_PATH
    if not parser_path.is_file():
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_frozen_parser_missing: {parser_path}")
    _assert_no_symlinks(parser_path)
    if _file_sha256(parser_path) != FROZEN_PARSER_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_frozen_parser_sha_mismatch")

    mod_name = "src.research.external_signal_shadow.stage1_5d_live_event_source_parser"
    if mod_name in sys.modules:
        mod = sys.modules[mod_name]
    else:
        mod = importlib.import_module(mod_name)

    file_attr = getattr(mod, "__file__", None)
    if not file_attr:
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_parser_file_missing: {mod_name}")
    _assert_no_symlinks(Path(file_attr))
    if Path(file_attr).resolve() != parser_path.resolve():
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_parser_file_mismatch: {mod_name}")

    origin = getattr(getattr(mod, "__spec__", None), "origin", None)
    if not origin:
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_parser_origin_missing: {mod_name}")
    _assert_no_symlinks(Path(origin))
    if Path(origin).resolve() != parser_path.resolve():
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_parser_origin_mismatch: {mod_name}")

    if _file_sha256(parser_path) != FROZEN_PARSER_SHA256:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_frozen_parser_sha_mismatch")

    return mod


# =========================================================================
# Catalog & Detail Parsing & Reduction
# =========================================================================


def validate_catalog_scans(
    scan_a_pages: list[dict[str, Any]],
    scan_b_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validates two-pass catalog scans per Section 4.1."""
    if len(scan_a_pages) != len(scan_b_pages):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:scan_page_count_mismatch")

    def _extract_tuples(pages: list[dict[str, Any]]) -> list[tuple[int, str, int, str]]:
        tuples = []
        for page_no, page in enumerate(pages, start=1):
            catalogs = page.get("data", {}).get("catalogs", [])
            target_cats = [catalogs[0]] if isinstance(catalogs, list) and len(catalogs) > 1 else catalogs
            for cat in target_cats:
                for art in cat.get("articles", []):
                    code = art.get("code")
                    rel_date = art.get("releaseDate")
                    title = art.get("title")
                    if not isinstance(code, str) or len(code) != 32:
                        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:invalid_article_code")
                    if isinstance(rel_date, bool) or not isinstance(rel_date, int):
                        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:invalid_release_date")
                    if not isinstance(title, str):
                        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:invalid_title")
                    tuples.append((page_no, code, rel_date, title))
        return tuples

    tuples_a = _extract_tuples(scan_a_pages)
    tuples_b = _extract_tuples(scan_b_pages)

    if tuples_a != tuples_b:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:scan_a_b_mismatch")

    # Check non-increasing release dates and cross-page ordering
    has_sentinel = False
    seen_codes: set[str] = set()

    for i, t in enumerate(tuples_a):
        _, code, rel_date, _ = t
        if code in seen_codes:
            raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:duplicate_article_code")
        seen_codes.add(code)

        if rel_date < UNIVERSE_START_MS:
            has_sentinel = True

        if i > 0:
            prev_rel_date = tuples_a[i - 1][2]
            if rel_date > prev_rel_date:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:cross_page_inversion")

    if not has_sentinel:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:sentinel_missing")

    # Construct denominator records
    denominator: list[dict[str, Any]] = []
    for _, code, rel_date, title in tuples_a:
        if UNIVERSE_START_MS <= rel_date < UNIVERSE_END_MS:
            denominator.append({
                "source_article_id": code,
                "release_date_ms": rel_date,
                "title": title,
            })

    # Sort by (release_date_ms, source_article_id)
    denominator.sort(key=lambda r: (r["release_date_ms"], r["source_article_id"]))
    return denominator


def validate_detail_envelope(payload: dict[str, Any], requested_article_code: str) -> dict[str, Any]:
    """Validates detail envelope per Section 4.2."""
    expected_top_keys = {"code", "data", "message", "messageDetail", "success"}
    if set(payload.keys()) != expected_top_keys:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_detail_envelope_invalid:keys_mismatch")

    if payload.get("code") != "000000" or payload.get("success") is not True:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_detail_envelope_invalid:status_error")

    data = payload.get("data")
    if not isinstance(data, dict):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_detail_envelope_invalid:data_not_object")

    data_code = data.get("code")
    if data_code != requested_article_code:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_detail_envelope_invalid:code_mismatch")

    title = data.get("title")
    body = data.get("body")
    if not isinstance(title, str) or not isinstance(body, str):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_detail_envelope_invalid:fields_type_mismatch")

    return data


# =========================================================================
# Archive Package Validation (ZIP / Checksum / CSV)
# =========================================================================


def validate_archive_package(
    zip_path: Path,
    checksum_path: Path,
    symbol: str,
    utc_date: str,
    launch_time_ms: int,
) -> dict[str, Any]:
    """Validates archive package per Section 5.2."""
    if not zip_path.is_file():
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_archive_package_missing:zip:{zip_path}")
    if not checksum_path.is_file():
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_archive_package_missing:checksum:{checksum_path}")

    _assert_no_symlinks(zip_path)
    _assert_no_symlinks(checksum_path)

    # 1. Parse checksum file
    chk_text = checksum_path.read_text(encoding="utf-8").strip()
    parts = chk_text.split()
    if len(parts) != 2:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:checksum_grammar_invalid")

    expected_hash, referenced_basename = parts[0], parts[1]
    if referenced_basename != zip_path.name:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:checksum_basename_mismatch")

    actual_zip_hash = _file_sha256(zip_path)
    if actual_zip_hash != expected_hash:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:checksum_mismatch")

    # 2. Check ZIP structure
    zip_size = zip_path.stat().st_size
    if zip_size > EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_ZIP_BYTES:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:zip_size_exceeded")

    with zipfile.ZipFile(zip_path, "r") as zf:
        infolist = zf.infolist()
        if len(infolist) != 1:
            raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:zip_multiple_members")

        member = infolist[0]
        expected_csv_name = f"{symbol}-aggTrades-{utc_date}.csv"
        if member.filename != expected_csv_name:
            raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:zip_member_name_mismatch")

        uncompressed_size = member.file_size
        if uncompressed_size > EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES:
            raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:csv_uncompressed_size_exceeded")

        if zip_size > 0 and (uncompressed_size / zip_size) > EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_COMPRESSION_RATIO:
            raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:compression_ratio_exceeded")

        # 3. Stream CSV
        post_launch_row_count = 0
        first_post_launch_time: int | None = None
        last_post_launch_time: int | None = None
        prev_time = 0

        with zf.open(member, "r") as raw_csv:
            text_stream = io.TextIOWrapper(raw_csv, encoding="utf-8")
            reader = csv.reader(text_stream)
            try:
                header = next(reader)
            except StopIteration:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:empty_csv")

            expected_header = [
                "agg_trade_id", "price", "quantity", "first_trade_id",
                "last_trade_id", "transact_time", "is_buyer_maker"
            ]
            if header != expected_header:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:csv_header_mismatch")

            for row in reader:
                if len(row) != 7:
                    raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:csv_row_column_count")

                try:
                    trade_id = int(row[0])
                    price = Decimal(row[1])
                    qty = Decimal(row[2])
                    first_id = int(row[3])
                    last_id = int(row[4])
                    transact_time = int(row[5])
                    maker = row[6].strip().lower()
                except (ValueError, InvalidOperation) as e:
                    raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_archive_package_invalid:csv_type_error: {e}") from e

                if (
                    trade_id < 0
                    or first_id < 0
                    or last_id < 0
                    or transact_time <= 0
                    or not price.is_finite()
                    or price <= 0
                    or not qty.is_finite()
                    or qty <= 0
                ):
                    raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:csv_value_range_error")
                if maker not in ("true", "false"):
                    raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:csv_maker_invalid")

                if transact_time < prev_time:
                    raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_archive_package_invalid:csv_timestamp_decreasing")
                prev_time = transact_time

                if transact_time >= launch_time_ms:
                    post_launch_row_count += 1
                    if first_post_launch_time is None:
                        first_post_launch_time = transact_time
                    last_post_launch_time = transact_time

    if post_launch_row_count > 0 and first_post_launch_time is not None:
        delay_ms = first_post_launch_time - launch_time_ms
        child_state = "archive_verified_with_post_launch_rows"
    else:
        delay_ms = None
        child_state = "archive_verified_zero_post_launch_rows"

    return {
        "child_state": child_state,
        "post_launch_row_count": post_launch_row_count,
        "first_post_launch_trade_time_ms": first_post_launch_time,
        "last_post_launch_trade_time_ms": last_post_launch_time,
        "first_post_launch_trade_delay_ms": delay_ms,
    }


# =========================================================================
# Summary & Review Generation
# =========================================================================


def build_inventory_summary(
    run_id: str,
    catalog_scans_data: dict[str, Any],
    denominator_records: list[dict[str, Any]],
    parent_records: list[dict[str, Any]],
    archive_package_records: list[dict[str, Any]],
    request_records: list[dict[str, Any]],
    authority_packet: dict[str, Any],
) -> dict[str, Any]:
    """Constructs canonical summary matching Section 5.3."""
    target_parent_count = sum(1 for r in denominator_records if r["candidate_status"] != "not_target_event_type")
    resolved_parent_count = sum(1 for r in denominator_records if r["candidate_status"] == "resolved_target_parent")

    in_scope_usdt_child_count = 0
    out_of_scope_child_count = 0
    for p in parent_records:
        for c in p.get("children", []):
            if c.get("child_scope") == "in_scope_usdt":
                in_scope_usdt_child_count += 1
            else:
                out_of_scope_child_count += 1

    # child_coverage_complete_count: unique (parent_article_id, symbol) where every required package verified with rows
    child_packages: dict[tuple[str, str], list[str]] = {}
    for ap in archive_package_records:
        key = (ap["parent_article_id"], ap["symbol"])
        if key not in child_packages:
            child_packages[key] = []
        child_packages[key].append(ap["child_state"])

    child_coverage_complete_count = sum(
        1 for states in child_packages.values()
        if states and all(s == "archive_verified_with_post_launch_rows" for s in states)
    )
    child_coverage_gap_count = in_scope_usdt_child_count - child_coverage_complete_count

    parent_coverage_complete_count = sum(1 for p in parent_records if p["parent_state"] == "coverage_complete")
    parent_coverage_gap_count = target_parent_count - parent_coverage_complete_count

    coverage_inventory = {
        "catalog_denominator_count": len(denominator_records),
        "child_coverage_complete_count": child_coverage_complete_count,
        "child_coverage_gap_count": child_coverage_gap_count,
        "in_scope_usdt_child_count": in_scope_usdt_child_count,
        "out_of_scope_child_count": out_of_scope_child_count,
        "parent_coverage_complete_count": parent_coverage_complete_count,
        "parent_coverage_gap_count": parent_coverage_gap_count,
        "resolved_parent_count": resolved_parent_count,
        "target_parent_count": target_parent_count,
    }

    if parent_coverage_gap_count == 0:
        analysis_state = "coverage_inventory_complete"
        decision = "stage1_5j_a_historical_archive_coverage_inventory_published"
    else:
        analysis_state = "coverage_inventory_evidence_gap"
        decision = "stage1_5j_a_historical_archive_coverage_evidence_gap_published"

    return {
        "analysis_state": analysis_state,
        "archive_package_records": sorted(archive_package_records, key=lambda r: (r["parent_article_id"], r["symbol"], r["utc_date"])),
        "authority_flags": EXPECTED_13_FALSE_FLAGS,
        "authority_packet": authority_packet,
        "catalog_denominator_records": sorted(denominator_records, key=lambda r: (r["release_date_ms"], r["source_article_id"])),
        "catalog_scan": catalog_scans_data,
        "coverage_inventory": coverage_inventory,
        "decision": decision,
        "parent_records": sorted(parent_records, key=lambda r: r["source_article_id"]),
        "request_records": sorted(request_records, key=lambda r: r["request_id"]),
        "run_id": run_id,
        "schema_version": "stage1_5j_a_historical_archive_coverage_inventory_v1",
        "universe_window": {
            "end_exclusive_ms": UNIVERSE_END_MS,
            "start_ms": UNIVERSE_START_MS,
        },
    }


def render_stage1_5j_a_review(summary: dict[str, Any]) -> str:
    """Renders review_CN.md markdown byte-for-byte matching Section 5.3."""
    lines = [
        "# Stage 1.5J-A 历史数据归档覆盖度报告",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Analysis State: `{summary['analysis_state']}`",
        f"- Decision: `{summary['decision']}`",
        f"- Universe Window: `[{summary['universe_window']['start_ms']}, {summary['universe_window']['end_exclusive_ms']})`",
        "",
        "## 目录扫描与分母",
        f"- Denominator Articles: {summary['coverage_inventory']['catalog_denominator_count']}",
        f"- Target Parents: {summary['coverage_inventory']['target_parent_count']}",
        f"- Resolved Parents: {summary['coverage_inventory']['resolved_parent_count']}",
        "",
        "## 覆盖度统计",
        f"- In-Scope USDT Children: {summary['coverage_inventory']['in_scope_usdt_child_count']}",
        f"- Out-Of-Scope Children: {summary['coverage_inventory']['out_of_scope_child_count']}",
        f"- Child Coverage Complete: {summary['coverage_inventory']['child_coverage_complete_count']}",
        f"- Child Coverage Gap: {summary['coverage_inventory']['child_coverage_gap_count']}",
        f"- Parent Coverage Complete: {summary['coverage_inventory']['parent_coverage_complete_count']}",
        f"- Parent Coverage Gap: {summary['coverage_inventory']['parent_coverage_gap_count']}",
        "",
        "## 父事件明细",
        "| Source Article ID | Parent State | Children Count |",
        "| --- | --- | --- |",
    ]
    for p in summary["parent_records"]:
        lines.append(f"| {p['source_article_id']} | {p['parent_state']} | {len(p.get('children', []))} |")

    lines.extend([
        "",
        "## 归档包明细",
        "| Parent Article ID | Symbol | UTC Date | Child State | Post-Launch Rows |",
        "| --- | --- | --- | --- | --- |",
    ])
    for a in summary["archive_package_records"]:
        lines.append(
            f"| {a['parent_article_id']} | {a['symbol']} | {a['utc_date']} | "
            f"{a['child_state']} | {a['post_launch_row_count']} |"
        )

    lines.extend([
        "",
        "## 权限向量",
        "| Permission | Value |",
        "| --- | --- |",
    ])
    for k, v in sorted(summary["authority_flags"].items()):
        lines.append(f"| {k} | {v} |")

    lines.append("")
    return "\n".join(lines)


# =========================================================================
# Lifecycle, State Classification & Strict Loader
# =========================================================================


def classify_stage1_5j_a_historical_archive_coverage_root_state(
    output_parent: Path,
    run_id: str,
) -> str:
    """Classifies output state according to the Section 5.3 / 7 matrix."""
    _assert_no_symlinks(output_parent)

    final_dir = output_parent / run_id
    staging_dirs = list(output_parent.glob(f".{run_id}.staging.*"))

    has_final = final_dir.is_dir()
    has_staging = len(staging_dirs) > 0

    if not has_final and not has_staging:
        return "absent"
    elif not has_final and has_staging:
        return "staging_only"
    elif has_final and not has_staging:
        return "final_only"
    else:
        return "final_plus_staging"


def _classify_root_state_for_test(output_parent: Path, run_id: str) -> str:
    return classify_stage1_5j_a_historical_archive_coverage_root_state(output_parent, run_id)


def _validate_authority_packet(summary_data: dict[str, Any], project_root: Path | None = None) -> None:
    """Strictly validates authority_packet schema, paths, and hashes."""
    auth_packet = summary_data.get("authority_packet")
    if not isinstance(auth_packet, dict):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_packet_invalid:not_object")

    if set(auth_packet.keys()) != AUTHORITY_PACKET_EXACT_KEYS:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_packet_invalid:keys_mismatch")

    proj_root = project_root or _resolve_project_root()

    standard_components = {
        "approved_design": (APPROVED_DESIGN_REL_PATH, APPROVED_DESIGN_SHA256),
        "approved_plan": (APPROVED_PLAN_REL_PATH, APPROVED_PLAN_SHA256),
        "audited_cli": ("scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py", None),
        "audited_config": ("configs/base.py", None),
        "audited_core": ("src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py", None),
        "frozen_parser": (FROZEN_PARSER_REL_PATH, FROZEN_PARSER_SHA256),
    }

    for comp, (expected_rel_path, expected_const_sha) in standard_components.items():
        sub = auth_packet.get(comp)
        if not isinstance(sub, dict) or set(sub.keys()) != {"relative_path", "sha256"}:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_authority_packet_invalid:sub_keys_mismatch:{comp}")
        if sub.get("relative_path") != expected_rel_path:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_authority_packet_invalid:rel_path_mismatch:{comp}")
        sha = sub.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64 or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_authority_packet_invalid:sha_invalid:{comp}")
        if expected_const_sha is not None and sha != expected_const_sha:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_authority_packet_invalid:const_sha_mismatch:{comp}")

        target_path = proj_root / expected_rel_path
        _assert_no_symlinks(target_path)
        if not target_path.is_file():
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_authority_packet_invalid:disk_file_missing:{comp}")
        if _file_sha256(target_path) != sha:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_authority_packet_invalid:disk_sha_mismatch:{comp}")

    net_auth = auth_packet.get("network_authorization")
    if not isinstance(net_auth, dict) or set(net_auth.keys()) != {
        "authorized_run_id",
        "network_profile_id",
        "relative_path",
        "sha256",
    }:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_packet_invalid:network_authorization_keys_mismatch")

    if net_auth.get("authorized_run_id") != summary_data.get("run_id"):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_packet_invalid:run_id_mismatch")

    if net_auth.get("network_profile_id") != NETWORK_PROFILE_ID:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_packet_invalid:network_profile_id_mismatch")

    expected_net_rel = f".git/plan-execution/stage1_5j_a/{APPROVED_PLAN_SHA256}/network_authorization.txt"
    if net_auth.get("relative_path") != expected_net_rel:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_packet_invalid:network_auth_rel_path_mismatch")

    net_sha = net_auth.get("sha256")
    if not isinstance(net_sha, str) or len(net_sha) != 64 or not re.fullmatch(r"[0-9a-f]{64}", net_sha):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_packet_invalid:network_auth_sha_invalid")

    net_path = proj_root / expected_net_rel
    _assert_no_symlinks(net_path)
    if not net_path.is_file():
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_packet_invalid:network_auth_disk_file_missing")
    if _file_sha256(net_path) != net_sha:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_packet_invalid:network_auth_disk_sha_mismatch")


def load_verified_stage1_5j_a_historical_archive_coverage_root(
    root_dir: Path,
) -> dict[str, Any]:
    """Strict loader replaying journal/parser/package/count/render reductions per Section 5.3."""
    return _load_verified_stage1_5j_a_historical_archive_coverage_root_internal(
        root_dir=root_dir,
        project_root=_resolve_project_root(),
    )


def _load_verified_stage1_5j_a_historical_archive_coverage_root_for_test(
    root_dir: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Private test helper: loads and validates root against an isolated test project_root."""
    return _load_verified_stage1_5j_a_historical_archive_coverage_root_internal(
        root_dir=root_dir,
        project_root=project_root,
    )


def _load_verified_stage1_5j_a_historical_archive_coverage_root_internal(
    root_dir: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Internal strict loader implementation."""
    _assert_no_symlinks(root_dir)
    root = project_root
    _assert_no_symlinks(root)

    # 1. Output-parent containment and run_id format
    expected_output_parent = (root / OUTPUT_PARENT_REL).resolve()
    if root_dir.resolve().parent != expected_output_parent:
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_root_invalid:not_under_output_parent:{root_dir}")
    if not RUN_ID_REGEX.match(root_dir.name):
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_root_invalid:run_id_format:{root_dir.name}")
    if not root_dir.is_dir():
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_root_missing: {root_dir}")

    manifest_file = root_dir / "manifest.json"
    summary_file = root_dir / "summary.json"
    review_file = root_dir / "review_CN.md"
    journal_file = root_dir / "request_journal.jsonl"

    for f in (manifest_file, summary_file, review_file, journal_file):
        if not f.is_file():
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_root_invalid:missing_file:{f.name}")

    # Read manifest
    manifest_bytes = manifest_file.read_bytes()
    try:
        manifest_data = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as e:
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_manifest_invalid: {e}") from e

    expected_manifest_bytes = (canonical_json_dumps(manifest_data) + "\n").encode("utf-8")
    if manifest_bytes != expected_manifest_bytes:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_manifest_not_canonical")

    if manifest_data.get("run_id") != root_dir.name:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_manifest_mismatch:run_id_mismatch")
    if manifest_data.get("root_relative_path") != str(OUTPUT_PARENT_REL / root_dir.name):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_manifest_mismatch:root_relative_path_mismatch")

    # Recheck all artifacts listed in manifest
    artifacts = manifest_data.get("artifacts", [])
    artifact_paths: set[Path] = set()
    for art in artifacts:
        rel = art.get("relative_path")
        exp_sha = art.get("sha256")
        exp_bytes = art.get("byte_count")
        p = root_dir / rel
        if not p.is_file():
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_manifest_mismatch:missing_artifact:{rel}")
        if p.stat().st_size != exp_bytes or _file_sha256(p) != exp_sha:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_manifest_mismatch:hash_mismatch:{rel}")
        artifact_paths.add(p)

    # Check no extra regular files
    for p in root_dir.rglob("*"):
        if p.is_file() and p != manifest_file and p not in artifact_paths:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_root_invalid:unexpected_entries:{p}")

    # Read and validate summary
    summary_bytes = summary_file.read_bytes()
    try:
        summary_data = json.loads(summary_bytes.decode("utf-8"))
    except Exception as e:
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_summary_invalid: {e}") from e

    expected_summary_bytes = (canonical_json_dumps(summary_data) + "\n").encode("utf-8")
    if summary_bytes != expected_summary_bytes:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_summary_not_canonical")

    if set(summary_data.keys()) != SUMMARY_EXACT_KEYS:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_summary_invalid:keys_mismatch")

    if summary_data.get("run_id") != root_dir.name:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_summary_invalid:run_id_mismatch")

    # Validate authority flags are all False
    flags = summary_data.get("authority_flags", {})
    if flags != EXPECTED_13_FALSE_FLAGS:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_authority_flag_violation")

    # Validate authority packet
    _validate_authority_packet(summary_data, root)

    # Re-verify review markdown rendering
    expected_review = render_stage1_5j_a_review(summary_data)
    actual_review = review_file.read_text(encoding="utf-8")
    if actual_review != expected_review:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_review_projection_mismatch")

    # Replay Journal
    journal_lines = [line.strip() for line in journal_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not journal_lines:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_root_invalid:empty_journal")

    intents, terminals, replayed_request_records = _validate_request_journal_lines(journal_lines)

    if summary_data.get("request_records") != replayed_request_records:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_reduction_mismatch:request_records_mismatch")

    # Replay Raw Catalog Scans
    scan_a_dir = root_dir / "raw" / "catalog_scan_a"
    scan_b_dir = root_dir / "raw" / "catalog_scan_b"
    if not scan_a_dir.is_dir() or not scan_b_dir.is_dir():
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_root_invalid:missing_catalog_scans")

    def _read_scan_pages(s_dir: Path) -> list[dict[str, Any]]:
        page_files = sorted(s_dir.glob("*.json"), key=lambda p: int(p.stem) if p.stem.isdigit() else 999999)
        if not page_files:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_root_invalid:empty_catalog_scan:{s_dir.name}")
        pages = []
        for i, pf in enumerate(page_files, 1):
            if pf.stem != str(i):
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_root_invalid:non_contiguous_pages:{pf.name}")
            pages.append(json.loads(pf.read_text(encoding="utf-8")))
        return pages

    scan_a_pages = _read_scan_pages(scan_a_dir)
    scan_b_pages = _read_scan_pages(scan_b_dir)
    replayed_denominator = validate_catalog_scans(scan_a_pages, scan_b_pages)

    parser_mod = _import_verified_frozen_parser()
    # Replay denominator records
    target_pids: set[str] = set()
    replayed_denom_by_id: dict[str, dict[str, Any]] = {}
    for row in replayed_denominator:
        code = row["source_article_id"]
        title = row["title"]
        cat_type = parser_mod.classify_event_type(title)
        if cat_type == EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE:
            target_pids.add(code)
        replayed_denom_by_id[code] = row

    summary_denom = summary_data.get("catalog_denominator_records", [])
    if len(summary_denom) != len(replayed_denominator):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_reduction_mismatch:denominator_count_mismatch")

    replayed_ids_list = [r["source_article_id"] for r in replayed_denominator]
    summary_ids_list = [r.get("source_article_id") for r in summary_denom]
    if summary_ids_list != replayed_ids_list:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_reduction_mismatch:denominator_ids_mismatch")

    for r in summary_denom:
        code = r.get("source_article_id")
        rep_row = replayed_denom_by_id[code]
        if r.get("release_date_ms") != rep_row["release_date_ms"]:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:denominator_field_mismatch:release_date_ms:{code}")
        if r.get("title") != rep_row["title"]:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:denominator_field_mismatch:title:{code}")

        status = r.get("candidate_status")
        if code in target_pids:
            if status == "not_target_event_type":
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:target_demoted:{code}")
            if status not in ("resolved_target_parent", "catalog_detail_unresolved"):
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:invalid_target_status:{code}")
        else:
            if status != "not_target_event_type":
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:non_target_promoted:{code}")
            if r.get("detail_request_id") is not None:
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:non_target_has_detail_request:{code}")

    # Replay parent records & detail parsing
    details_dir = root_dir / "raw" / "article_details"
    parents = summary_data.get("parent_records", [])
    summary_parent_pids = [p.get("source_article_id") for p in parents]
    if sorted(summary_parent_pids) != sorted(target_pids):
        diff = set(target_pids) ^ set(summary_parent_pids)
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_pids_mismatch:{diff}")
    if len(parents) != len(target_pids):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_reduction_mismatch:parent_count_mismatch")

    summary_denom_by_id = {r["source_article_id"]: r for r in summary_denom}
    for p in parents:
        pid = p["source_article_id"]
        denom_row = summary_denom_by_id.get(pid)
        detail_file = details_dir / f"{pid}.json" if details_dir.is_dir() else None
        if detail_file and detail_file.is_file():
            detail_payload = json.loads(detail_file.read_text(encoding="utf-8"))
            _replay_parent_detail_admission(detail_payload, p, denom_row, parser_mod)
        else:
            if p["detail_status"] != "detail_nonpersisted":
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_detail_status:{pid}")
            if denom_row is not None and denom_row.get("candidate_status") != "catalog_detail_unresolved":
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:candidate_status_mismatch:{pid}")

    # Replay archive packages
    archive_dir = root_dir / "raw" / "archive"
    packages = summary_data.get("archive_package_records", [])

    # Replay required date sets per child
    expected_package_keys: set[tuple[str, str, str]] = set()
    for p in parents:
        pid = p["source_article_id"]
        if p.get("detail_status") == "validated_target_detail":
            for c in p.get("children", []):
                if c.get("child_scope") == "in_scope_usdt":
                    sym = c["symbol"]
                    launch_time = c.get("symbol_launch_time_ms")
                    if launch_time is not None:
                        for d in _compute_required_archive_utc_dates(launch_time):
                            expected_package_keys.add((pid, sym, d))

    actual_package_keys = {
        (ap["parent_article_id"], ap["symbol"], ap["utc_date"])
        for ap in packages
        if ap.get("utc_date") != "unknown"
    }
    if actual_package_keys != expected_package_keys:
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_reduction_mismatch:archive_package_date_set_mismatch")

    for ap in packages:
        _validate_archive_package_record(ap)
        sym = ap["symbol"]
        utc_date = ap["utc_date"]
        pid = ap["parent_article_id"]
        state = ap["child_state"]

        exp_logical_id = {
            "market": "futures_um",
            "metric": "aggTrades",
            "parent_article_id": pid,
            "symbol": sym,
            "utc_date": utc_date,
        }
        if ap.get("logical_archive_identity") != exp_logical_id:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:logical_archive_identity_mismatch:{sym}:{utc_date}")

        zip_path = archive_dir / sym / f"{sym}-aggTrades-{utc_date}.zip" if archive_dir.is_dir() else None
        chk_path = archive_dir / sym / f"{sym}-aggTrades-{utc_date}.zip.CHECKSUM" if archive_dir.is_dir() else None
        if zip_path and zip_path.is_file() and chk_path and chk_path.is_file():
            # Find launch time from parent record
            launch_time = None
            for p in parents:
                if p["source_article_id"] == pid:
                    for c in p.get("children", []):
                        if c["symbol"] == sym:
                            launch_time = c.get("symbol_launch_time_ms")
            if launch_time is not None:
                pkg_res = validate_archive_package(
                    zip_path=zip_path,
                    checksum_path=chk_path,
                    symbol=sym,
                    utc_date=utc_date,
                    launch_time_ms=launch_time,
                )
                if ap["child_state"] != pkg_res["child_state"] or ap["post_launch_row_count"] != pkg_res["post_launch_row_count"]:
                    raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:archive_package_mismatch:{sym}")
        else:
            if state != "archive_request_nonpersisted":
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:archive_package_mismatch:{sym}")

    # Re-verify coverage counts formulas
    inv = summary_data.get("coverage_inventory", {})
    denom = summary_data.get("catalog_denominator_records", [])

    calc_denom_count = len(denom)
    calc_target_parent_count = sum(1 for r in denom if r.get("candidate_status") != "not_target_event_type")
    calc_resolved_parent_count = sum(1 for r in denom if r.get("candidate_status") == "resolved_target_parent")

    calc_in_scope = 0
    calc_out_of_scope = 0
    for p in parents:
        for c in p.get("children", []):
            if c.get("child_scope") == "in_scope_usdt":
                calc_in_scope += 1
            else:
                calc_out_of_scope += 1

    child_pkgs: dict[tuple[str, str], list[str]] = {}
    for ap in packages:
        k = (ap["parent_article_id"], ap["symbol"])
        if k not in child_pkgs:
            child_pkgs[k] = []
        child_pkgs[k].append(ap["child_state"])

    calc_child_complete = sum(
        1 for states in child_pkgs.values()
        if states and all(s == "archive_verified_with_post_launch_rows" for s in states)
    )
    calc_child_gap = calc_in_scope - calc_child_complete
    calc_parent_complete = sum(1 for p in parents if p["parent_state"] == "coverage_complete")
    calc_parent_gap = calc_target_parent_count - calc_parent_complete

    if (
        inv.get("catalog_denominator_count") != calc_denom_count
        or inv.get("target_parent_count") != calc_target_parent_count
        or inv.get("resolved_parent_count") != calc_resolved_parent_count
        or inv.get("in_scope_usdt_child_count") != calc_in_scope
        or inv.get("out_of_scope_child_count") != calc_out_of_scope
        or inv.get("child_coverage_complete_count") != calc_child_complete
        or inv.get("child_coverage_gap_count") != calc_child_gap
        or inv.get("parent_coverage_complete_count") != calc_parent_complete
        or inv.get("parent_coverage_gap_count") != calc_parent_gap
    ):
        raise Stage1_5JADiagnosticError(
            "STOP=stage1_5j_a_reduction_mismatch:coverage_inventory_recomputation_failed"
        )

    # Validate parent state recomputation
    for p in parents:
        pid = p["source_article_id"]
        pstate = p["parent_state"]
        pchildren = p.get("children", [])
        in_scope_children = [c for c in pchildren if c.get("child_scope") == "in_scope_usdt"]

        if p.get("detail_status") != "validated_target_detail":
            if pstate != "coverage_evidence_gap_detail":
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_record_mismatch:{pid}")
        else:
            if not in_scope_children:
                if pstate != "coverage_evidence_gap_no_in_scope_usdt_child":
                    raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_record_mismatch:{pid}")
            else:
                all_children_complete = all(
                    child_pkgs.get((pid, c["symbol"])) is not None
                    and all(s == "archive_verified_with_post_launch_rows" for s in child_pkgs[(pid, c["symbol"])])
                    for c in in_scope_children
                )
                if all_children_complete and pstate != "coverage_complete":
                    raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_record_mismatch:{pid}")
                elif not all_children_complete and pstate != "coverage_evidence_gap_archive":
                    raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_reduction_mismatch:parent_record_mismatch:{pid}")

    expected_analysis_state = (
        "coverage_inventory_complete" if calc_parent_gap == 0
        else "coverage_inventory_evidence_gap"
    )
    expected_decision = (
        "stage1_5j_a_historical_archive_coverage_inventory_published" if calc_parent_gap == 0
        else "stage1_5j_a_historical_archive_coverage_evidence_gap_published"
    )

    if summary_data.get("analysis_state") != expected_analysis_state:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_reduction_mismatch:analysis_state_mismatch:{summary_data.get('analysis_state')}"
        )
    if summary_data.get("decision") != expected_decision:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_reduction_mismatch:decision_mismatch:{summary_data.get('decision')}"
        )

    return summary_data


def _load_verified_root_for_test(root_dir: Path, project_root: Path) -> dict[str, Any]:
    return _load_verified_stage1_5j_a_historical_archive_coverage_root_internal(root_dir=root_dir, project_root=project_root)



# =========================================================================
# Production Transport & Request Journaling
# =========================================================================


class RequestManager:
    """Manages append-only journal, request admissions, and stdlib HTTPS transport."""

    def __init__(self, staging_dir: Path):
        self.staging_dir = staging_dir
        self.journal_file = staging_dir / "request_journal.jsonl"
        self.request_id = 0
        self.catalog_requests = 0
        self.detail_requests = 0
        self.archive_requests = 0

    def validate_url(self, kind: str, url: str) -> None:
        if kind == "catalog":
            if not re.match(rf"^https://www\.binance\.com/bapi/composite/v1/public/cms/article/list/query\?type=1&pageNo=([1-9]\d*)&pageSize={EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_SIZE}$", url):
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_request_admission_failure:catalog_url:{url}")
            self.catalog_requests += 1
            if self.catalog_requests > EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CATALOG_REQUESTS:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_request_admission_failure:catalog_cap_exceeded")
        elif kind == "detail":
            if not re.match(r"^https://www\.binance\.com/bapi/composite/v1/public/cms/article/detail/query\?articleCode=([0-9a-f]{32})$", url):
                raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_request_admission_failure:detail_url:{url}")
            self.detail_requests += 1
            if self.detail_requests > EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_DETAIL_REQUESTS:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_request_admission_failure:detail_cap_exceeded")
        elif kind in ("archive", "checksum"):
            if kind == "archive":
                if not re.match(r"^https://data\.binance\.vision/data/futures/um/daily/aggTrades/([A-Z0-9]+)/\1-aggTrades-(\d{4}-\d{2}-\d{2})\.zip$", url):
                    raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_request_admission_failure:archive_url:{url}")
            else:
                if not re.match(r"^https://data\.binance\.vision/data/futures/um/daily/aggTrades/([A-Z0-9]+)/\1-aggTrades-(\d{4}-\d{2}-\d{2})\.zip\.CHECKSUM$", url):
                    raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_request_admission_failure:checksum_url:{url}")
            self.archive_requests += 1
            if self.archive_requests > EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_REQUESTS:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_request_admission_failure:archive_cap_exceeded")
        else:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_request_admission_failure:unknown_kind:{kind}")

    def request(
        self,
        kind: str,
        url: str,
        rel_path: str,
        parent_article_id: str | None = None,
        symbol: str | None = None,
        utc_date: str | None = None,
    ) -> bytes | None:
        # 1. Validate admission and intent context applicability
        self.validate_url(kind, url)
        _validate_intent_context_applicability(kind, parent_article_id, symbol, utc_date)

        self.request_id += 1
        req_id = self.request_id

        # 2. Append-only write intent
        intent = {
            "event": "request_intent",
            "parent_article_id": parent_article_id,
            "request_id": req_id,
            "request_kind": kind,
            "request_state": "admitted_pending",
            "symbol": symbol,
            "url": url,
            "utc_date": utc_date,
        }
        with open(self.journal_file, "a", encoding="utf-8") as jf:
            jf.write(canonical_json_dumps(intent) + "\n")
            jf.flush()
            _fsync_file(jf.fileno())

        # 3. Transport
        body_bytes: bytes | None = None
        http_status: int | None = None
        transport_err: str | None = None

        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.port not in (None, 443):
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_request_admission_failure:scheme_port:{url}")
        if parsed.username or parsed.password or parsed.fragment:
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_request_admission_failure:url_syntax:{url}")

        path_query = parsed.path
        if parsed.query:
            path_query += "?" + parsed.query

        try:
            conn = http.client.HTTPSConnection(
                parsed.hostname,
                port=443,
                timeout=EXTERNAL_SIGNAL_STAGE1_5J_A_HTTP_TIMEOUT_SEC,
            )
            conn.request("GET", path_query, headers={"Host": parsed.hostname, "User-Agent": "crypto-alpha-lab/1.5j-a"})
            resp = conn.getresponse()
            http_status = resp.status
            if http_status in (301, 302, 303, 307, 308):
                transport_err = f"redirect_prohibited:{http_status}"
                http_status = None
                body_bytes = None
            else:
                max_bytes = (
                    EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_BAPI_RESPONSE_BYTES if kind in ("catalog", "detail")
                    else EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CHECKSUM_RESPONSE_BYTES if kind == "checksum"
                    else EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_ZIP_BYTES
                )
                content = resp.read(max_bytes + 1)
                if len(content) > max_bytes:
                    transport_err = "max_bytes_exceeded"
                    http_status = None
                    body_bytes = None
                else:
                    body_bytes = content
            conn.close()
        except Exception as e:
            transport_err = str(e)
            http_status = None
            body_bytes = None

        # 4. Handle transport error / inconclusive
        if transport_err is not None or http_status is None:
            term = {
                "event": "request_terminal",
                "http_status": None,
                "request_id": req_id,
                "request_state": "transport_inconclusive",
                "response_bytes": None,
                "response_relative_path": None,
                "response_sha256": None,
                "transport_error": transport_err or "transport_inconclusive",
            }
            with open(self.journal_file, "a", encoding="utf-8") as jf:
                jf.write(canonical_json_dumps(term) + "\n")
                jf.flush()
                _fsync_file(jf.fileno())
            return None

        if http_status == 404:
            term = {
                "event": "request_terminal",
                "http_status": 404,
                "request_id": req_id,
                "request_state": "http_not_found",
                "response_bytes": None,
                "response_relative_path": None,
                "response_sha256": None,
                "transport_error": None,
            }
            with open(self.journal_file, "a", encoding="utf-8") as jf:
                jf.write(canonical_json_dumps(term) + "\n")
                jf.flush()
                _fsync_file(jf.fileno())
            return None

        if http_status != 200:
            term = {
                "event": "request_terminal",
                "http_status": http_status,
                "request_id": req_id,
                "request_state": "response_rejected",
                "response_bytes": None,
                "response_relative_path": None,
                "response_sha256": None,
                "transport_error": None,
            }
            with open(self.journal_file, "a", encoding="utf-8") as jf:
                jf.write(canonical_json_dumps(term) + "\n")
                jf.flush()
                _fsync_file(jf.fileno())
            return None

        if not body_bytes:
            term = {
                "event": "request_terminal",
                "http_status": None,
                "request_id": req_id,
                "request_state": "transport_inconclusive",
                "response_bytes": None,
                "response_relative_path": None,
                "response_sha256": None,
                "transport_error": "empty_response_body",
            }
            with open(self.journal_file, "a", encoding="utf-8") as jf:
                jf.write(canonical_json_dumps(term) + "\n")
                jf.flush()
                _fsync_file(jf.fileno())
            return None

        # Persist response bytes and write response_persisted terminal
        out_file = self.staging_dir / rel_path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(body_bytes)
        out_fd = os.open(out_file, os.O_RDONLY)
        try:
            _fsync_file(out_fd)
        finally:
            os.close(out_fd)

        term = {
            "event": "request_terminal",
            "http_status": 200,
            "request_id": req_id,
            "request_state": "response_persisted",
            "response_bytes": len(body_bytes),
            "response_relative_path": rel_path,
            "response_sha256": _file_sha256(out_file),
            "transport_error": None,
        }
        with open(self.journal_file, "a", encoding="utf-8") as jf:
            jf.write(canonical_json_dumps(term) + "\n")
            jf.flush()
            _fsync_file(jf.fileno())

        return body_bytes


# =========================================================================
# Public Production Entrypoint
# =========================================================================


def run_inventory(run_id: str) -> dict[str, Any]:
    """Sole public production entrypoint for Stage 1.5J-A.

    Enforces:
    1. RUN_ID regex grammar
    2. verify_execution_authority()
    3. verify_network_authorization(run_id) - fails closed during implementation
    4. Two-pass catalog scan, detail resolution, archive validation
    5. Sealed atomic publication
    """
    if not RUN_ID_REGEX.match(run_id):
        raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_run_id_invalid: {run_id}")

    verify_execution_authority()
    net_auth_dict = verify_network_authorization(run_id=run_id)
    project_root = _resolve_project_root()

    output_parent = project_root / OUTPUT_PARENT_REL
    if not output_parent.is_absolute() or output_parent.resolve() != (project_root.resolve() / OUTPUT_PARENT_REL):
        raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_output_parent_namespace_mismatch")
    _assert_no_symlinks(output_parent)

    output_parent.mkdir(parents=True, exist_ok=True)
    staging_dir = output_parent / f".{run_id}.staging.{os.getpid()}"

    p_fd = os.open(output_parent, os.O_RDONLY)
    try:
        fcntl.flock(p_fd, fcntl.LOCK_EX)
        st = classify_stage1_5j_a_historical_archive_coverage_root_state(output_parent, run_id)
        if st != "absent":
            raise Stage1_5JADiagnosticError(f"STOP=stage1_5j_a_publication_collision:{st}")

        staging_dir.mkdir(parents=True, exist_ok=False)

        req_mgr = RequestManager(staging_dir=staging_dir)

        # 1. Scan A
        scan_a_pages: list[dict[str, Any]] = []
        sentinel_page: int | None = None
        for page_no in range(1, EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_LIMIT_PER_PASS + 1):
            url = f"https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo={page_no}&pageSize={EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_SIZE}"
            rel_path = f"raw/catalog_scan_a/{page_no}.json"
            raw_bytes = req_mgr.request(kind="catalog", url=url, rel_path=rel_path)
            if raw_bytes is None:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:transport_failed")
            page_data = json.loads(raw_bytes.decode("utf-8"))
            scan_a_pages.append(page_data)

            # Check for sentinel row
            catalogs = page_data.get("data", {}).get("catalogs", [])
            target_cats = [catalogs[0]] if isinstance(catalogs, list) and len(catalogs) > 1 else catalogs
            has_sentinel = False
            for cat in target_cats:
                for art in cat.get("articles", []):
                    rel_date = art.get("releaseDate")
                    if isinstance(rel_date, int) and not isinstance(rel_date, bool):
                        if rel_date < UNIVERSE_START_MS:
                            has_sentinel = True
                            break
                if has_sentinel:
                    break
            if has_sentinel:
                sentinel_page = page_no
                break

        if sentinel_page is None:
            raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:sentinel_missing")

        # 2. Scan B
        scan_b_pages: list[dict[str, Any]] = []
        for page_no in range(1, sentinel_page + 1):
            url = f"https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo={page_no}&pageSize={EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_SIZE}"
            rel_path = f"raw/catalog_scan_b/{page_no}.json"
            raw_bytes = req_mgr.request(kind="catalog", url=url, rel_path=rel_path)
            if raw_bytes is None:
                raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_catalog_completeness_unproven:transport_failed")
            page_data = json.loads(raw_bytes.decode("utf-8"))
            scan_b_pages.append(page_data)

        # 3. Validate catalog scans
        denominator_records = validate_catalog_scans(scan_a_pages, scan_b_pages)

        # 4. Details resolution
        parser_mod = _import_verified_frozen_parser(project_root)
        parent_records: list[dict[str, Any]] = []
        archive_package_records: list[dict[str, Any]] = []
        downloaded_archives: dict[tuple[str, str], tuple[int, int, bytes | None, bytes | None]] = {}

        for row in denominator_records:
            title = row["title"]
            source_article_id = row["source_article_id"]
            cat_type = parser_mod.classify_event_type(title)

            if cat_type != EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE:
                row["candidate_status"] = "not_target_event_type"
                row["detail_request_id"] = None
                continue

            # Target candidate!
            detail_url = f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode={source_article_id}"
            detail_rel = f"raw/article_details/{source_article_id}.json"
            detail_bytes = req_mgr.request(
                kind="detail",
                url=detail_url,
                rel_path=detail_rel,
                parent_article_id=source_article_id,
                symbol=None,
                utc_date=None,
            )
            row["detail_request_id"] = req_mgr.request_id

            if detail_bytes is None:
                row["candidate_status"] = "catalog_detail_unresolved"
                parent_records.append({
                    "children": [],
                    "detail_payload_sha256": None,
                    "detail_request_id": row["detail_request_id"],
                    "detail_status": "detail_nonpersisted",
                    "parent_state": "coverage_evidence_gap_detail",
                    "source_article_id": source_article_id,
                })
                continue

            detail_payload = json.loads(detail_bytes.decode("utf-8"))
            validate_detail_envelope(detail_payload, source_article_id)
            detail_sha = _sha256(detail_bytes)
            parent_rec, in_scope_children = _admit_parent_detail(row, detail_payload, detail_sha, parser_mod)
            if in_scope_children is None:
                parent_records.append(parent_rec)
                continue


            # 5. Archive packages for in-scope USDT children
            child_states: list[str] = []
            for c in in_scope_children:
                sym = c["symbol"]
                launch_time_ms = c["symbol_launch_time_ms"]
                required_dates = _compute_required_archive_utc_dates(launch_time_ms)
                child_date_states: list[str] = []
                for utc_date in required_dates:
                    logical_id = {
                        "market": "futures_um",
                        "metric": "aggTrades",
                        "parent_article_id": source_article_id,
                        "symbol": sym,
                        "utc_date": utc_date,
                    }

                    archive_base_url = f"https://data.binance.vision/data/futures/um/daily/aggTrades/{sym}/{sym}-aggTrades-{utc_date}.zip"
                    chk_url = archive_base_url + ".CHECKSUM"
                    zip_url = archive_base_url

                    chk_rel = f"raw/archive/{sym}/{sym}-aggTrades-{utc_date}.zip.CHECKSUM"
                    zip_rel = f"raw/archive/{sym}/{sym}-aggTrades-{utc_date}.zip"

                    phys_key = (sym, utc_date)
                    if phys_key not in downloaded_archives:
                        chk_bytes = req_mgr.request(
                            kind="checksum",
                            url=chk_url,
                            rel_path=chk_rel,
                            parent_article_id=source_article_id,
                            symbol=sym,
                            utc_date=utc_date,
                        )
                        chk_req_id = req_mgr.request_id

                        zip_bytes = req_mgr.request(
                            kind="archive",
                            url=zip_url,
                            rel_path=zip_rel,
                            parent_article_id=source_article_id,
                            symbol=sym,
                            utc_date=utc_date,
                        )
                        zip_req_id = req_mgr.request_id
                        downloaded_archives[phys_key] = (chk_req_id, zip_req_id, chk_bytes, zip_bytes)
                    else:
                        chk_req_id, zip_req_id, chk_bytes, zip_bytes = downloaded_archives[phys_key]

                    if chk_bytes is None or zip_bytes is None:
                        rec = {
                            "checksum_request_id": chk_req_id,
                            "child_state": "archive_request_nonpersisted",
                            "first_post_launch_trade_delay_ms": None,
                            "first_post_launch_trade_time_ms": None,
                            "last_post_launch_trade_time_ms": None,
                            "logical_archive_identity": logical_id,
                            "parent_article_id": source_article_id,
                            "post_launch_row_count": None,
                            "symbol": sym,
                            "utc_date": utc_date,
                            "zip_request_id": zip_req_id,
                        }
                        _validate_archive_package_record(rec)
                        archive_package_records.append(rec)
                        child_date_states.append("archive_request_nonpersisted")
                    else:
                        zip_file_path = staging_dir / zip_rel
                        chk_file_path = staging_dir / chk_rel
                        pkg_result = validate_archive_package(
                            zip_path=zip_file_path,
                            checksum_path=chk_file_path,
                            symbol=sym,
                            utc_date=utc_date,
                            launch_time_ms=launch_time_ms,
                        )
                        archive_package_records.append({
                            "checksum_request_id": chk_req_id,
                            "child_state": pkg_result["child_state"],
                            "first_post_launch_trade_delay_ms": pkg_result["first_post_launch_trade_delay_ms"],
                            "first_post_launch_trade_time_ms": pkg_result["first_post_launch_trade_time_ms"],
                            "last_post_launch_trade_time_ms": pkg_result["last_post_launch_trade_time_ms"],
                            "logical_archive_identity": logical_id,
                            "parent_article_id": source_article_id,
                            "post_launch_row_count": pkg_result["post_launch_row_count"],
                            "symbol": sym,
                            "utc_date": utc_date,
                            "zip_request_id": zip_req_id,
                        })
                        child_date_states.append(pkg_result["child_state"])

                if all(s == "archive_verified_with_post_launch_rows" for s in child_date_states):
                    child_states.append("archive_verified_with_post_launch_rows")
                else:
                    child_states.append("archive_request_nonpersisted")

            # Determine parent_state
            if not in_scope_children:
                parent_state = "coverage_evidence_gap_no_in_scope_usdt_child"
            elif all(s == "archive_verified_with_post_launch_rows" for s in child_states):
                parent_state = "coverage_complete"
            else:
                parent_state = "coverage_evidence_gap_archive"

            parent_rec["parent_state"] = parent_state
            parent_records.append(parent_rec)

        # 6. Extract request records from journal using canonical validator
        journal_lines = (staging_dir / "request_journal.jsonl").read_text(encoding="utf-8").splitlines()
        _, _, request_records = _validate_request_journal_lines(journal_lines)

        # 7. Catalog scan summary info
        tuples_a = [
            (p, a["code"], a["releaseDate"], a["title"])
            for p, page in enumerate(scan_a_pages, 1)
            for cat in ([page.get("data", {}).get("catalogs", [])[0]] if isinstance(page.get("data", {}).get("catalogs"), list) and page.get("data", {}).get("catalogs") else [])
            for a in cat.get("articles", [])
        ]
        stable_tuple_sha = _sha256(canonical_json_dumps(tuples_a))
        catalog_scans_data = {
            "page_limit_per_pass": EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_LIMIT_PER_PASS,
            "scan_a_page_count": len(scan_a_pages),
            "scan_b_page_count": len(scan_b_pages),
            "sentinel_page_no": sentinel_page,
            "stable_tuple_sha256": stable_tuple_sha,
        }

        # 8. Authority packet for summary
        core_path = project_root / "src" / "research" / "external_signal_shadow" / "stage1_5j_a_historical_archive_coverage_inventory.py"
        cli_path = project_root / "scripts" / "external_signal_shadow" / "run_stage1_5j_a_historical_archive_coverage_inventory.py"
        config_path = project_root / "configs" / "base.py"
        parser_path = project_root / FROZEN_PARSER_REL_PATH
        design_path = project_root / APPROVED_DESIGN_REL_PATH
        plan_path = project_root / APPROVED_PLAN_REL_PATH

        authority_packet = {
            "approved_design": {"relative_path": APPROVED_DESIGN_REL_PATH, "sha256": _file_sha256(design_path)},
            "approved_plan": {"relative_path": APPROVED_PLAN_REL_PATH, "sha256": _file_sha256(plan_path)},
            "audited_cli": {"relative_path": "scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py", "sha256": _file_sha256(cli_path)},
            "audited_config": {"relative_path": "configs/base.py", "sha256": _file_sha256(config_path)},
            "audited_core": {"relative_path": "src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py", "sha256": _file_sha256(core_path)},
            "frozen_parser": {"relative_path": FROZEN_PARSER_REL_PATH, "sha256": _file_sha256(parser_path)},
            "network_authorization": {
                "authorized_run_id": run_id,
                "network_profile_id": NETWORK_PROFILE_ID,
                "relative_path": f".git/plan-execution/stage1_5j_a/{APPROVED_PLAN_SHA256}/network_authorization.txt",
                "sha256": net_auth_dict["file_sha256"],
            },
        }

        summary = build_inventory_summary(
            run_id=run_id,
            catalog_scans_data=catalog_scans_data,
            denominator_records=denominator_records,
            parent_records=parent_records,
            archive_package_records=archive_package_records,
            request_records=request_records,
            authority_packet=authority_packet,
        )

        summary_file = staging_dir / "summary.json"
        summary_file.write_text(canonical_json_dumps(summary) + "\n", encoding="utf-8")

        review_file = staging_dir / "review_CN.md"
        review_file.write_text(render_stage1_5j_a_review(summary), encoding="utf-8")

        # Build manifest
        artifacts = []
        for p in sorted(staging_dir.rglob("*")):
            if p.is_file() and p.name != "manifest.json":
                rel = str(p.relative_to(staging_dir))
                artifacts.append({
                    "byte_count": p.stat().st_size,
                    "relative_path": rel,
                    "sha256": _file_sha256(p),
                })

        manifest = {
            "artifacts": artifacts,
            "root_relative_path": str(OUTPUT_PARENT_REL / run_id),
            "run_id": run_id,
            "schema_version": "stage1_5j_a_historical_archive_coverage_inventory_manifest_v1",
        }
        manifest_file = staging_dir / "manifest.json"
        manifest_file.write_text(canonical_json_dumps(manifest) + "\n", encoding="utf-8")

        # Fsync all
        for p in staging_dir.rglob("*"):
            if p.is_file():
                fd = os.open(p, os.O_RDONLY)
                try:
                    _fsync_file(fd)
                finally:
                    os.close(fd)
            elif p.is_dir():
                _fsync_dir(p)
        _fsync_dir(staging_dir)

        final_dir = output_parent / run_id
        if final_dir.exists():
            raise Stage1_5JADiagnosticError("STOP=stage1_5j_a_publication_collision:final_preexists")
        os.rename(staging_dir, final_dir)
        try:
            _fsync_dir(output_parent)
        except Exception as e:
            raise Stage1_5JAPostRenameDurabilityFailure(
                f"STOP=stage1_5j_a_publication_durability_failure: {e}"
            ) from e

        return summary
    finally:
        fcntl.flock(p_fd, fcntl.LOCK_UN)
        os.close(p_fd)
