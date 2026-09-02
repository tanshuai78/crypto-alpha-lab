import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

from configs import base
from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
    build_formal_event_anchor_contract_row,
    build_symbol_anchor_contract,
    validate_launch_anchor_contract,
    validate_schedule_revision_contract,
)
from src.research.external_signal_shadow.stage1_5_launch_event_contract import (
    coerce_legacy_launch_event_to_formal,
    validate_formal_launch_event,
)
from src.research.external_signal_shadow.stage1_5_storage_guard import (
    StorageWriteBlocked,
    require_storage_write,
    terminal_write_set_peak_bytes,
)
from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
    ALLOWED_OVERDUE_DETAIL_RETRY_FAILURE_CLASSES,
    DETAIL_RETRY_SCHEDULER_STATE_FILENAME,
    STAGE1_5D_V3_ALLOWED_TERMINAL_REASONS,
    _canonical_json_bytes,
    classify_never_attempted_defer_state,
    compute_detail_transient_backoff_ms,
    is_detail_source_degraded,
    select_detail_retry_attempts,
    serialize_stage1_5d_v3_articles,
    summarize_detail_retry_overdue_state,
    summarize_detail_source_health,
    update_detail_endpoint_health,
    update_detail_endpoint_health_by_source,
    update_detail_endpoint_health_by_variant,
    validate_stage1_5d_v3_scheduler_state,
    write_detail_retry_scheduler_state,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_client import (
    build_announcement_detail_fallback_urls,
    build_announcement_list_url,
    build_bapi_article_detail_url,
    fetch_public_bapi_article_detail,
    fetch_public_json,
    fetch_public_payload,
    validate_announcement_detail_url,
    validate_bapi_article_detail_payload,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_collector import (
    run_one_poll_cycle,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_evidence import (
    validate_upstream_evidence,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_first_bar import (
    check_first_bar_for_event,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
    LAUNCH_SCHEDULE_PARSER_VERSION,
    PARSER_VERSION,
    SYMBOL_EXTRACTION_VERSION,
    extract_symbol_candidates_from_bapi_article_payload,
    extract_symbol_candidates_from_detail_payload,
    extract_symbol_candidates_from_title,
    normalize_live_event,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import (
    append_jsonl,
    build_stream_paths,
    enforce_payload_budget,
    load_payload_version_first_observed,
    record_payload_version_first_observed,
    write_detail_payload,
    write_detail_payload_append_only,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_summary import (
    build_smoke_summary,
)
from src.research.external_signal_shadow.stage1_5d_runtime_gate import (
    build_stage1_5d_runtime_gate,
    write_stage1_5d_runtime_gate,
)
from src.research.external_signal_shadow.stage1_5d_schedule_revision_producer import (
    build_revision_diagnostic,
    classify_schedule_revision_candidates,
    emit_schedule_revision_batch,
    is_schedule_revision_listing_candidate,
    load_emitted_revision_semantic_ids,
    load_valid_formal_launch_identity_index,
    rebuild_missing_formal_launch_identity_index,
)

PROTECTED_TREE_MANIFEST = [
    "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py",
    "src/research/external_signal_shadow/stage1_5d_live_event_source_client.py",
    "src/research/external_signal_shadow/stage1_5d_live_event_source_collector.py",
    "src/research/external_signal_shadow/stage1_5d_live_event_source_evidence.py",
    "src/research/external_signal_shadow/stage1_5d_live_event_source_first_bar.py",
    "src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py",
    "src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py",
    "src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py",
    "src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py",
    "src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py",
    "src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py",
    "src/research/external_signal_shadow/stage1_5_launch_event_contract.py",
    "src/research/external_signal_shadow/stage1_5d_runtime_gate.py",
]

CONSUMER_RUNTIME_MANIFEST = [
    "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py",
    "scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_budget.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_metrics.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py",
    "src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py",
    "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py",
    "src/risk/limits.py",
]

ALLOWED_CONFIG_DELTA_ASSIGNMENTS = {
    "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA": str,
    "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED": bool,
    "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED": bool,
    "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED": bool,
}


def canonical_manifest_sha256(policy_version: str, paths: list[str]) -> str:
    payload = policy_version + "\n" + "\n".join(sorted(paths)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_root_id(path: str | Path) -> str:
    canonical_path = str(Path(path).resolve())
    return hashlib.sha256(canonical_path.encode("utf-8")).hexdigest()


def canonical_root_contract_sha256(root_contract: dict) -> str:
    payload = json.dumps(
        root_contract,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


_DATE_JSONL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.jsonl$")
_BIN_PAYLOAD_RE = re.compile(r"^(bapi_article_detail_query|primary|detail_path_fallback)\.[0-9a-f]{64}\.bin$")
_SAFE_ARTICLE_ID_RE = re.compile(r"^[0-9a-zA-Z_\-]+$")


def build_stage1_5d_v3_resume_provenance(output_root: Path, startup_head_sha: str) -> dict[str, object]:
    configs_base_path = Path("configs/base.py")
    cfg_sha = hashlib.sha256(configs_base_path.read_bytes()).hexdigest() if configs_base_path.exists() else "0" * 64

    manifest_path = output_root / "protected_tree_manifest.json"
    if manifest_path.exists():
        tree_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    else:
        tree_sha = hashlib.sha256(
            json.dumps(PROTECTED_TREE_MANIFEST, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    return {
        "root_id": output_root.name,
        "scheduler_contract_version": 3,
        "producer_startup_head_sha": startup_head_sha,
        "protected_tree_manifest_sha256": tree_sha,
        "configs_base_sha256": cfg_sha,
    }


def _is_allowlisted_relative_path(rel_path: Path, is_dir: bool) -> bool:
    parts = rel_path.parts
    if not parts:
        return True

    stream_dirs = {
        "raw_payloads",
        "announcement_events",
        "events",
        "heartbeats",
        "request_manifest",
        "detail_retry_scheduler_diagnostics",
        "detail_retry_terminal_diagnostics",
        "detail_retry_deferred_diagnostics",
        "schedule_revision_diagnostics",
        "bapi_parse_results",
        "first_bar_observations",
    }

    if len(parts) == 1:
        name = parts[0]
        if is_dir:
            return name in stream_dirs
        else:
            return name in {
                DETAIL_RETRY_SCHEDULER_STATE_FILENAME,
                "live_safety_gate_summary.json",
                "binance_futures_launch_smoke_summary.json",
                "formal_launch_identity_index.jsonl",
                "protected_tree_manifest.json",
                "storage_failure_diagnostic.json",
                "revision_payload_versions.jsonl",
            }

    if len(parts) == 2:
        top, child = parts
        if top in stream_dirs:
            if not is_dir and _DATE_JSONL_RE.match(child):
                return True
        if top == "raw_payloads" and child == "announcement_detail" and is_dir:
            return True
        if top == "announcement_events" and child == "futures_contract_launch" and is_dir:
            return True
        return False

    if len(parts) == 3:
        p0, p1, p2 = parts
        if p0 == "announcement_events" and p1 == "futures_contract_launch" and not is_dir:
            return bool(_DATE_JSONL_RE.match(p2))
        if p0 == "raw_payloads" and p1 == "announcement_detail" and is_dir:
            return bool(_SAFE_ARTICLE_ID_RE.match(p2))
        return False

    if len(parts) == 4:
        p0, p1, p2, p3 = parts
        if p0 == "raw_payloads" and p1 == "announcement_detail" and not is_dir:
            return bool(_SAFE_ARTICLE_ID_RE.match(p2) and _BIN_PAYLOAD_RE.match(p3))
        return False

    return False


def preflight_stage1_5d_v3_root(
    output_root: Path,
    output_summary_path: Path,
    *,
    expected_resume_provenance: dict[str, object],
) -> dict[str, object]:
    # 1. Output summary relation check
    expected_summary_path = (output_root.resolve(strict=False) / "binance_futures_launch_smoke_summary.json")
    if output_summary_path.resolve(strict=False) != expected_summary_path:
        return {
            "kind": "rejected",
            "reason": "stage1_5d_v3_output_summary_relation_rejected",
            "state": None,
            "formal_completed_source_article_ids": set(),
            "crash_cleanup_row": None,
        }

    # 2. Fresh check
    if not output_root.exists():
        return {
            "kind": "fresh",
            "reason": None,
            "state": None,
            "formal_completed_source_article_ids": set(),
            "crash_cleanup_row": None,
        }

    # 3. Existing check
    if output_root.is_symlink() or not output_root.is_dir():
        return {
            "kind": "rejected",
            "reason": "stage1_5d_v3_output_root_not_regular_dir",
            "state": None,
            "formal_completed_source_article_ids": set(),
            "crash_cleanup_row": None,
        }

    # 4. Closed tree check
    for p in output_root.rglob("*"):
        if p.is_symlink():
            return {
                "kind": "rejected",
                "reason": f"stage1_5d_v3_symlink_discovered:{p.relative_to(output_root)}",
                "state": None,
                "formal_completed_source_article_ids": set(),
                "crash_cleanup_row": None,
            }
        rel = p.relative_to(output_root)
        if not _is_allowlisted_relative_path(rel, is_dir=p.is_dir()):
            return {
                "kind": "rejected",
                "reason": f"closed_tree_unallowlisted_path:{rel}",
                "state": None,
                "formal_completed_source_article_ids": set(),
                "crash_cleanup_row": None,
            }

    # 5. Read state file
    state_path = output_root / DETAIL_RETRY_SCHEDULER_STATE_FILENAME
    if not state_path.exists() or not state_path.is_file():
        return {
            "kind": "rejected",
            "reason": "stage1_5d_v3_scheduler_state_missing",
            "state": None,
            "formal_completed_source_article_ids": set(),
            "crash_cleanup_row": None,
        }

    try:
        raw_state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "kind": "rejected",
            "reason": f"stage1_5d_v3_scheduler_state_json_decode_error:{exc}",
            "state": None,
            "formal_completed_source_article_ids": set(),
            "crash_cleanup_row": None,
        }

    blockers = validate_stage1_5d_v3_scheduler_state(raw_state, expected_resume_provenance=expected_resume_provenance)
    if blockers:
        return {
            "kind": "rejected",
            "reason": f"stage1_5d_v3_scheduler_state_invalid:{blockers}",
            "state": None,
            "formal_completed_source_article_ids": set(),
            "crash_cleanup_row": None,
        }

    # 6. Read formal event and index projection
    formal_projections = {}
    index_path = output_root / "formal_launch_identity_index.jsonl"
    if index_path.exists() and index_path.is_file():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                return {
                    "kind": "rejected",
                    "reason": "stage1_5d_v3_formal_index_malformed",
                    "state": None,
                    "formal_completed_source_article_ids": set(),
                    "crash_cleanup_row": None,
                }
            src_id = row.get("source_article_id")
            ev_id = row.get("event_id")
            syms = row.get("symbols")
            if not (src_id and ev_id and isinstance(syms, list) and syms):
                return {
                    "kind": "rejected",
                    "reason": f"stage1_5d_v3_formal_index_row_invalid:{src_id}",
                    "state": None,
                    "formal_completed_source_article_ids": set(),
                    "crash_cleanup_row": None,
                }
            formal_projections[src_id] = {"event_id": ev_id, "symbols": sorted(syms)}

    # Check Table 6.2.1 exclusivity matrix
    formal_completed_ids = set()
    crash_cleanup_row = None
    articles = raw_state.get("articles", {})

    for src_id, f_proj in formal_projections.items():
        if src_id not in articles:
            formal_completed_ids.add(src_id)
        else:
            row = articles[src_id]
            if row.get("terminal_state"):
                return {
                    "kind": "rejected",
                    "reason": f"terminal_plus_complete_formal_rejected:{src_id}",
                    "state": None,
                    "formal_completed_source_article_ids": set(),
                    "crash_cleanup_row": None,
                }
            inflight = row.get("inflight_cycle")
            if inflight is None:
                return {
                    "kind": "rejected",
                    "reason": f"active_null_plus_complete_formal_rejected:{src_id}",
                    "state": None,
                    "formal_completed_source_article_ids": set(),
                    "crash_cleanup_row": None,
                }
            op = inflight.get("operation")
            if op in ("detail_request", "exchangeinfo_request"):
                return {
                    "kind": "rejected",
                    "reason": f"active_intent_plus_complete_formal_rejected:{src_id}:{op}",
                    "state": None,
                    "formal_completed_source_article_ids": set(),
                    "crash_cleanup_row": None,
                }
            if op == "formal_emission":
                target = inflight.get("request_target") or {}
                t_ev_id = target.get("event_id")
                t_syms = sorted(target.get("symbols") or [])
                if t_ev_id == f_proj["event_id"] and t_syms == f_proj["symbols"]:
                    crash_cleanup_row = row
                    formal_completed_ids.add(src_id)
                else:
                    return {
                        "kind": "rejected",
                        "reason": f"formal_intent_projection_mismatch_rejected:{src_id}",
                        "state": None,
                        "formal_completed_source_article_ids": set(),
                        "crash_cleanup_row": None,
                    }

    detached_state = json.loads(json.dumps(raw_state))
    return {
        "kind": "resumable",
        "reason": None,
        "state": detached_state,
        "formal_completed_source_article_ids": formal_completed_ids,
        "crash_cleanup_row": crash_cleanup_row,
    }


_STAGE1_5D_V3_INFLIGHT_KEYS = {
    "operation",
    "poll_cycle_index",
    "stage_work_type",
    "candidate_symbols",
    "candidate_symbol_set_hash",
    "request_target",
    "intent_created_at_ms",
}

_STAGE1_5D_V3_ALLOWED_INFLIGHT_OPERATIONS = {
    "detail_request",
    "exchangeinfo_request",
    "formal_emission",
}

_STAGE1_5D_V3_ALLOWED_INFLIGHT_STAGE_WORK_TYPES = {
    "catalog_bootstrap",
    "new_listing",
    "launch_schedule_revision_detail",
    "retry_backoff",
}


def validate_stage1_5d_v3_inflight_intent(intent: dict | None) -> list[str]:
    if intent is None:
        return []
    if not isinstance(intent, dict):
        return ["inflight_intent_not_dict"]

    blockers = []
    keys = set(intent.keys())
    extra_keys = keys - _STAGE1_5D_V3_INFLIGHT_KEYS
    if extra_keys:
        blockers.append(f"inflight_intent_unknown_keys:{sorted(extra_keys)}")
    missing_keys = _STAGE1_5D_V3_INFLIGHT_KEYS - keys
    if missing_keys:
        blockers.append(f"inflight_intent_missing_keys:{sorted(missing_keys)}")
        return blockers

    op = intent.get("operation")
    if op not in _STAGE1_5D_V3_ALLOWED_INFLIGHT_OPERATIONS:
        blockers.append(f"inflight_intent_invalid_operation:{op}")

    p_idx = intent.get("poll_cycle_index")
    if not isinstance(p_idx, int) or isinstance(p_idx, bool) or p_idx < 0:
        blockers.append(f"inflight_intent_invalid_poll_cycle_index:{p_idx}")

    swt = intent.get("stage_work_type")
    if swt not in _STAGE1_5D_V3_ALLOWED_INFLIGHT_STAGE_WORK_TYPES:
        blockers.append(f"inflight_intent_invalid_stage_work_type:{swt}")

    c_syms = intent.get("candidate_symbols")
    if not isinstance(c_syms, list) or not all(isinstance(s, str) and s.isupper() for s in c_syms):
        blockers.append(f"inflight_intent_invalid_candidate_symbols:{c_syms}")

    c_hash = intent.get("candidate_symbol_set_hash")
    if not isinstance(c_hash, str) or not re.match(r"^[0-9a-f]{64}$", c_hash):
        blockers.append(f"inflight_intent_invalid_candidate_symbol_set_hash:{c_hash}")

    req_target = intent.get("request_target")
    if not isinstance(req_target, dict):
        blockers.append(f"inflight_intent_invalid_request_target:{req_target}")

    c_at = intent.get("intent_created_at_ms")
    if not isinstance(c_at, int) or isinstance(c_at, bool) or c_at <= 0:
        blockers.append(f"inflight_intent_invalid_intent_created_at_ms:{c_at}")

    return blockers


def classify_stage1_5d_catalog_admission(
    article: dict,
    *,
    cutoff_ms: int | None,
    detected_at_ms: int,
    formal_completed_ids: set[str],
    persisted_row: dict | None,
) -> str:
    code = article.get("code") or article.get("source_article_id")
    if code and code in formal_completed_ids:
        return "formal_completed"
    if persisted_row is not None and persisted_row.get("terminal_state") is True:
        return "persisted_terminal"

    raw_date = article.get("releaseDate")
    if raw_date is None or isinstance(raw_date, bool) or not isinstance(raw_date, int) or raw_date <= 0:
        return "source_published_at_invalid"

    max_skew_ms = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS", 30 * 1000)
    if raw_date > detected_at_ms + max_skew_ms:
        return "source_published_at_invalid"

    if cutoff_ms is not None and raw_date < cutoff_ms:
        return "historical_prebootstrap_catalog_article"

    return "active"


def build_stage1_5d_terminal_tombstone(
    existing: dict | None,
    *,
    source_article_id: str,
    title: str,
    source_detail_url_normalized: str,
    source_parent_url: str,
    detected_at_ms: int,
    first_detected_at_ms: int,
    reason: str,
    now_ms: int,
    source_published_at_ms: int | None,
) -> dict:
    row = {
        "source_article_id": source_article_id,
        "title": title,
        "source_detail_url_normalized": source_detail_url_normalized,
        "source_parent_url": source_parent_url,
        "source_published_at_ms": source_published_at_ms,
        "detected_at_ms": detected_at_ms,
        "first_detected_at_ms": first_detected_at_ms,
        "event_type": "futures_contract_launch",
        "detail_work_type": None,
        "catalog_id": None,
        "catalog_title": None,
        "symbol_extraction_source": "none",
        "symbol_parse_failed_reason": None,
        "pending_reason": None,
        "source_published_at_ms_confidence": "high" if source_published_at_ms is not None else None,
        "detail_http_request_count": int((existing.get("detail_http_request_count") if existing else 0) or 0),
        "detail_retry_cycle_count": int((existing.get("detail_retry_cycle_count") if existing else 0) or 0),
        "detail_fetch_attempt_count": int((existing.get("detail_fetch_attempt_count") if existing else 0) or 0),
        "transient_detail_error_count": int((existing.get("transient_detail_error_count") if existing else 0) or 0),
        "non_transient_detail_error_count": int((existing.get("non_transient_detail_error_count") if existing else 0) or 0),
        "last_retry_at_ms": int((existing.get("last_retry_at_ms") if existing else 0) or 0),
        "next_detail_retry_at_ms": int((existing.get("next_detail_retry_at_ms") if existing else 0) or 0),
        "first_deferred_at_ms": None,
        "last_deferred_at_ms": None,
        "last_deferred_manifest_at_ms": 0,
        "defer_count": 0,
        "terminal_state": True,
        "terminal_failure_type": STAGE1_5D_V3_ALLOWED_TERMINAL_REASONS.get(reason),
        "candidate_symbols": None,
        "symbol_derivation_method": None,
        "symbol_validation_status": None,
        "symbol_launch_times_ms": None,
        "symbol_onboard_times_ms": None,
        "symbol_effective_launch_times_ms": None,
        "launch_time_source": None,
        "last_detail_failure_class": None,
        "detail_retryable": False,
        "last_bapi_detail_status": None,
        "last_bapi_payload_hash": None,
        "last_bapi_parser_version": None,
        "last_bapi_parser_status": None,
        "last_bapi_parser_failure_reason": None,
        "last_bapi_parse_attempt_at_ms": None,
        "last_support_detail_status": None,
        "last_support_failure_class": None,
        "parsed_candidate_symbols": None,
        "candidate_provenance": None,
        "launch_time_resolution_status": None,
        "launch_anchor_policy": None,
        "required_launch_anchor_source": None,
        "consumable_event_allowed": None,
        "symbol_launch_time_candidates_ms": None,
        "launch_time_conflict_ms": None,
        "status": None,
        "terminal_reason": reason,
        "terminal_at_ms": now_ms,
        "emission_id": None,
        "candidate_symbol_set_hash": None,
        "candidate_symbol_set_hash_version": None,
        "candidate_symbols_ordered": None,
        "candidate_symbols_normalized": None,
        "event_id": None,
        "event_stream_path": None,
        "parser_payload_hash": None,
        "symbol_effective_launch_time_sources": None,
        "exchangeinfo_visible_symbols": None,
        "exchangeinfo_missing_symbols": None,
        "hard_rejected_symbols": None,
        "symbol_exchangeinfo_statuses": None,
        "inflight_cycle": None,
        "detail_budget_deferred_count": 0,
        "detail_fetch_attempted": None,
        "detail_fetch_status": None,
        "detail_fetch_url_used": None,
        "detail_fetch_variant": None,
        "detail_fetched_at_ms": None,
        "detail_parse_status": None,
        "detail_payload_hash": None,
        "detail_payload_trusted": None,
        "exchangeinfo_validation_attempt_count": 0,
        "exchangeinfo_validation_retryable": None,
        "last_exchangeinfo_validation_at_ms": None,
        "next_exchangeinfo_validation_at_ms": None,
        "quote_derivation_source": None,
        "retry_count": int((existing.get("retry_count") if existing else 0) or 0),
        "schedule_revision_producer_status": None,
    }
    return row


def build_stage1_5d_v3_active_article(
    existing: dict | None = None,
    *,
    source_article_id: str,
    title: str,
    source_detail_url_normalized: str,
    source_parent_url: str,
    detected_at_ms: int,
    first_detected_at_ms: int,
    source_published_at_ms: int | None,
    raw: dict | None = None,
    event_type: str = "futures_contract_launch",
    detail_work_type: str | None = None,
    candidate_symbols: list[str] | None = None,
    symbol_extraction_source: str = "none",
    symbol_derivation_method: str | None = None,
    symbol_validation_status: str | None = None,
    quote_derivation_source: str | None = None,
    symbol_launch_times_ms: dict | None = None,
    symbol_onboard_times_ms: dict | None = None,
    source_published_at_ms_confidence: str = "high",
    pending_reason: str | None = None,
    detail_fetch_attempted: bool | None = None,
    detail_fetch_status: str | None = None,
) -> dict:
    row = {
        "raw": raw or {},
        "source_article_id": source_article_id,
        "title": title,
        "source_detail_url_normalized": source_detail_url_normalized,
        "source_parent_url": source_parent_url,
        "source_published_at_ms": source_published_at_ms,
        "detected_at_ms": detected_at_ms,
        "first_detected_at_ms": first_detected_at_ms,
        "event_type": event_type,
        "detail_work_type": detail_work_type,
        "catalog_id": existing.get("catalog_id") if existing else None,
        "catalog_title": existing.get("catalog_title") if existing else None,
        "symbol_extraction_source": symbol_extraction_source,
        "symbol_parse_failed_reason": existing.get("symbol_parse_failed_reason") if existing else None,
        "pending_reason": pending_reason,
        "source_published_at_ms_confidence": source_published_at_ms_confidence,
        "detail_http_request_count": int((existing.get("detail_http_request_count") if existing else 0) or 0),
        "detail_retry_cycle_count": int((existing.get("detail_retry_cycle_count") if existing else 0) or 0),
        "detail_fetch_attempt_count": int((existing.get("detail_fetch_attempt_count") if existing else 0) or 0),
        "transient_detail_error_count": int((existing.get("transient_detail_error_count") if existing else 0) or 0),
        "non_transient_detail_error_count": int((existing.get("non_transient_detail_error_count") if existing else 0) or 0),
        "last_retry_at_ms": int((existing.get("last_retry_at_ms") if existing else 0) or 0),
        "next_detail_retry_at_ms": int((existing.get("next_detail_retry_at_ms") if existing else 0) or 0),
        "first_deferred_at_ms": existing.get("first_deferred_at_ms") if existing else None,
        "last_deferred_at_ms": existing.get("last_deferred_at_ms") if existing else None,
        "last_deferred_manifest_at_ms": int((existing.get("last_deferred_manifest_at_ms") if existing else 0) or 0),
        "defer_count": int((existing.get("defer_count") if existing else 0) or 0),
        "terminal_state": False,
        "terminal_failure_type": None,
        "candidate_symbols": candidate_symbols,
        "symbol_derivation_method": symbol_derivation_method,
        "symbol_validation_status": symbol_validation_status,
        "symbol_launch_times_ms": symbol_launch_times_ms,
        "symbol_onboard_times_ms": symbol_onboard_times_ms,
        "symbol_effective_launch_times_ms": existing.get("symbol_effective_launch_times_ms") if existing else None,
        "launch_time_source": existing.get("launch_time_source") if existing else None,
        "last_detail_failure_class": existing.get("last_detail_failure_class") if existing else None,
        "detail_retryable": existing.get("detail_retryable", True) if existing else True,
        "last_bapi_detail_status": existing.get("last_bapi_detail_status") if existing else None,
        "last_bapi_payload_hash": existing.get("last_bapi_payload_hash") if existing else None,
        "last_bapi_parser_version": existing.get("last_bapi_parser_version") if existing else None,
        "last_bapi_parser_status": existing.get("last_bapi_parser_status") if existing else None,
        "last_bapi_parser_failure_reason": existing.get("last_bapi_parser_failure_reason") if existing else None,
        "last_bapi_parse_attempt_at_ms": existing.get("last_bapi_parse_attempt_at_ms") if existing else None,
        "last_support_detail_status": existing.get("last_support_detail_status") if existing else None,
        "last_support_failure_class": existing.get("last_support_failure_class") if existing else None,
        "parsed_candidate_symbols": existing.get("parsed_candidate_symbols") if existing else None,
        "candidate_provenance": existing.get("candidate_provenance") if existing else None,
        "launch_time_resolution_status": existing.get("launch_time_resolution_status") if existing else None,
        "launch_anchor_policy": existing.get("launch_anchor_policy") if existing else None,
        "required_launch_anchor_source": existing.get("required_launch_anchor_source") if existing else None,
        "consumable_event_allowed": existing.get("consumable_event_allowed") if existing else None,
        "symbol_launch_time_candidates_ms": existing.get("symbol_launch_time_candidates_ms") if existing else None,
        "launch_time_conflict_ms": existing.get("launch_time_conflict_ms") if existing else None,
        "status": existing.get("status") if existing else None,
        "terminal_reason": None,
        "terminal_at_ms": None,
        "emission_id": existing.get("emission_id") if existing else None,
        "candidate_symbol_set_hash": existing.get("candidate_symbol_set_hash") if existing else None,
        "candidate_symbol_set_hash_version": existing.get("candidate_symbol_set_hash_version") if existing else None,
        "candidate_symbols_ordered": existing.get("candidate_symbols_ordered") if existing else None,
        "candidate_symbols_normalized": existing.get("candidate_symbols_normalized") if existing else None,
        "event_id": existing.get("event_id") if existing else None,
        "event_stream_path": existing.get("event_stream_path") if existing else None,
        "parser_payload_hash": existing.get("parser_payload_hash") if existing else None,
        "symbol_effective_launch_time_sources": existing.get("symbol_effective_launch_time_sources") if existing else None,
        "exchangeinfo_visible_symbols": existing.get("exchangeinfo_visible_symbols") if existing else None,
        "exchangeinfo_missing_symbols": existing.get("exchangeinfo_missing_symbols") if existing else None,
        "hard_rejected_symbols": existing.get("hard_rejected_symbols") if existing else None,
        "symbol_exchangeinfo_statuses": existing.get("symbol_exchangeinfo_statuses") if existing else None,
        "inflight_cycle": existing.get("inflight_cycle") if existing else None,
        "detail_budget_deferred_count": int((existing.get("detail_budget_deferred_count") if existing else 0) or 0),
        "detail_fetch_attempted": detail_fetch_attempted,
        "detail_fetch_status": detail_fetch_status,
        "detail_fetch_url_used": existing.get("detail_fetch_url_used") if existing else None,
        "detail_fetch_variant": existing.get("detail_fetch_variant") if existing else None,
        "detail_fetched_at_ms": existing.get("detail_fetched_at_ms") if existing else None,
        "detail_parse_status": existing.get("detail_parse_status") if existing else None,
        "detail_payload_hash": existing.get("detail_payload_hash") if existing else None,
        "detail_payload_trusted": existing.get("detail_payload_trusted") if existing else None,
        "exchangeinfo_validation_attempt_count": int((existing.get("exchangeinfo_validation_attempt_count") if existing else 0) or 0),
        "exchangeinfo_validation_retryable": existing.get("exchangeinfo_validation_retryable") if existing else None,
        "last_exchangeinfo_validation_at_ms": existing.get("last_exchangeinfo_validation_at_ms") if existing else None,
        "next_exchangeinfo_validation_at_ms": existing.get("next_exchangeinfo_validation_at_ms") if existing else None,
        "quote_derivation_source": quote_derivation_source,
        "retry_count": int((existing.get("retry_count") if existing else 0) or 0),
        "schedule_revision_producer_status": existing.get("schedule_revision_producer_status") if existing else None,
    }
    return row


def validate_configs_base_ast_delta(content_a: str, content_b: str) -> bool:
    """Allow literal changes to exactly the four producer-attestation settings."""
    try:
        tree_a = ast.parse(content_a)
        tree_b = ast.parse(content_b)
    except SyntaxError:
        return False

    if len(tree_a.body) != len(tree_b.body):
        return False

    def allowed_assignments(tree: ast.Module) -> dict[str, int] | None:
        positions: dict[str, int] = {}
        for index, node in enumerate(tree.body):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name) or target.id not in ALLOWED_CONFIG_DELTA_ASSIGNMENTS:
                continue
            expected_type = ALLOWED_CONFIG_DELTA_ASSIGNMENTS[target.id]
            if not isinstance(node.value, ast.Constant) or type(node.value.value) is not expected_type:
                return None
            if target.id in positions:
                return None
            positions[target.id] = index
        if set(positions) != set(ALLOWED_CONFIG_DELTA_ASSIGNMENTS):
            return None
        return positions

    positions_a = allowed_assignments(tree_a)
    positions_b = allowed_assignments(tree_b)
    if positions_a is None or positions_b is None or positions_a != positions_b:
        return False

    def normalize_assign(node: ast.AST):
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name in ALLOWED_CONFIG_DELTA_ASSIGNMENTS:
                    expected_type = ALLOWED_CONFIG_DELTA_ASSIGNMENTS[name]
                    if isinstance(node.value, ast.Constant) and type(node.value.value) is expected_type:
                        return ast.Assign(
                            targets=[ast.Name(id=name, ctx=ast.Store())],
                            value=ast.Constant(value="SENTINEL"),
                        )
        return node

    new_body_a = [normalize_assign(n) for n in tree_a.body]
    new_body_b = [normalize_assign(n) for n in tree_b.body]

    tree_a.body = new_body_a
    tree_b.body = new_body_b

    return ast.dump(tree_a) == ast.dump(tree_b)


def verify_git_ancestry_and_static_proof(
    *,
    repo_root: Path,
    prerequisite_sha: str,
    protected_manifest: list[str],
    deadline_monotonic: float | None = None,
) -> dict:
    prereq = prerequisite_sha.strip()
    if not prereq or len(prereq) != 40 or not all(c in "0123456789abcdefABCDEF" for c in prereq):
        return {"valid": False, "reason": "invalid_prerequisite_sha_format"}

    def run_git(args: list[str]) -> tuple[int, str]:
        timeout_sec = 5.0
        if deadline_monotonic is not None:
            timeout_sec = deadline_monotonic - time.monotonic()
            if timeout_sec <= 0:
                return -1, "timeout"
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=repo_root,
                capture_output=True,
                text=True,
                env=dict(os.environ, GIT_NO_REPLACE_OBJECTS="1"),
                timeout=min(5.0, timeout_sec),
            )
            return res.returncode, res.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return -1, ""

    code, toplevel = run_git(["rev-parse", "--show-toplevel"])
    if code != 0 or Path(toplevel).resolve() != repo_root.resolve():
        return {"valid": False, "reason": "git_toplevel_mismatch"}

    code, fmt = run_git(["rev-parse", "--show-object-format"])
    if code != 0 or fmt != "sha1":
        return {"valid": False, "reason": "non_sha1_object_format"}

    code, is_shallow = run_git(["rev-parse", "--is-shallow-repository"])
    if code != 0 or is_shallow != "false":
        return {"valid": False, "reason": "shallow_repository_rejected"}

    code, head_sha = run_git(["rev-parse", "HEAD"])
    if code != 0 or len(head_sha) != 40:
        return {"valid": False, "reason": "cannot_read_head_sha"}

    code, obj_type = run_git(["cat-file", "-t", prereq])
    if code != 0 or obj_type != "commit":
        return {"valid": False, "reason": "prerequisite_not_a_commit_object"}

    code, _ = run_git(["merge-base", "--is-ancestor", prereq, head_sha])
    if code != 0:
        return {"valid": False, "reason": "prerequisite_not_ancestor_of_head"}

    for commit in (prereq, head_sha):
        for path in protected_manifest:
            code, object_type = run_git(["cat-file", "-t", f"{commit}:{path}"])
            if code != 0 or object_type != "blob":
                return {"valid": False, "reason": "protected_manifest_path_not_tracked_blob"}

    for path in protected_manifest:
        resolved_path = (repo_root / path).resolve()
        if not resolved_path.is_relative_to(repo_root.resolve()) or not resolved_path.is_file():
            return {"valid": False, "reason": "protected_manifest_path_unavailable_at_runtime"}

    code, diff_out = run_git(["diff", "--quiet", prereq, head_sha, "--"] + protected_manifest)
    if code != 0:
        return {"valid": False, "reason": "protected_manifest_modified_between_commits"}

    code, cat_a = run_git(["show", f"{prereq}:configs/base.py"])
    if code != 0:
        return {"valid": False, "reason": "cannot_read_base_py_at_prerequisite"}

    code, cat_b = run_git(["show", f"{head_sha}:configs/base.py"])
    if code != 0:
        return {"valid": False, "reason": "cannot_read_base_py_at_head"}

    if not validate_configs_base_ast_delta(cat_a, cat_b):
        return {"valid": False, "reason": "unapproved_config_ast_delta"}

    code, status_out = run_git(["status", "--porcelain", "--"] + protected_manifest + ["configs/base.py"])
    if code != 0 or status_out:
        return {"valid": False, "reason": "protected_worktree_dirty"}

    protected_dirs = [
        "scripts/external_signal_shadow",
        "src/research/external_signal_shadow",
        "src/risk",
        "configs",
    ]
    for ignored in (False, True):
        args = ["ls-files", "--others", "--exclude-standard"]
        if ignored:
            args.append("-i")
        code, python_paths = run_git(args + ["--"] + protected_dirs)
        if code != 0:
            return {"valid": False, "reason": "cannot_check_untracked_python_sources"}
        if any(path.endswith(".py") for path in python_paths.splitlines()):
            return {"valid": False, "reason": "untracked_python_source_present"}

    return {
        "valid": True,
        "startup_head_sha": head_sha,
        "reason": "static_proof_passed",
    }


def verify_stage1_5d_runtime_attestation(
    repo_root: Path,
    startup_head_sha: str,
    protected_manifest: list[str],
    deadline_monotonic: float,
) -> dict:
    def run_git(args: list[str]) -> tuple[int, str]:
        timeout_sec = deadline_monotonic - time.monotonic()
        if timeout_sec <= 0:
            return -1, "timeout"
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=repo_root,
                capture_output=True,
                text=True,
                env=dict(os.environ, GIT_NO_REPLACE_OBJECTS="1"),
                timeout=timeout_sec,
            )
            return result.returncode, result.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return -1, ""

    code, head_sha = run_git(["rev-parse", "HEAD"])
    if code != 0 or head_sha != startup_head_sha:
        return {"valid": False, "reason": "startup_head_changed"}
    code, status_out = run_git(["status", "--porcelain", "--"] + protected_manifest + ["configs/base.py"])
    if code != 0 or status_out:
        return {"valid": False, "reason": "protected_worktree_dirty"}
    for path in protected_manifest:
        resolved_path = (repo_root / path).resolve()
        if not resolved_path.is_relative_to(repo_root.resolve()) or not resolved_path.is_file():
            return {"valid": False, "reason": "protected_manifest_path_unavailable_at_runtime"}

    protected_dirs = [
        "scripts/external_signal_shadow",
        "src/research/external_signal_shadow",
        "src/risk",
        "configs",
    ]
    for ignored in (False, True):
        args = ["ls-files", "--others", "--exclude-standard"]
        if ignored:
            args.append("-i")
        code, python_paths = run_git(args + ["--"] + protected_dirs)
        if code != 0:
            return {"valid": False, "reason": "cannot_check_untracked_python_sources"}
        if any(path.endswith(".py") for path in python_paths.splitlines()):
            return {"valid": False, "reason": "untracked_python_source_present"}
    return {"valid": True, "reason": "runtime_attestation_passed"}


def update_stage1_5d_runtime_attestation_latch(lifecycle: dict, result: dict) -> None:
    if not lifecycle.get("runtime_attestation_compromised", False) and not result.get("valid", False):
        lifecycle["runtime_attestation_compromised"] = True


def verify_stage1_5f_consumer_proof(
    *,
    consumer_root_contract_path: str | Path,
    consumer_summary_path: str | Path,
    expected_d_output_root_id: str,
    expected_d_startup_head_sha: str,
    expected_consumer_manifest_sha256: str,
    armed_consumer_state: dict | None = None,
    now_ms: int | None = None,
) -> dict:
    if not consumer_root_contract_path or not consumer_summary_path:
        return {"valid": False, "reason": "consumer_paths_unspecified"}

    contract_p = Path(consumer_root_contract_path)
    summary_p = Path(consumer_summary_path)

    if not contract_p.is_file() or not summary_p.is_file():
        return {"valid": False, "reason": "consumer_artifact_file_missing"}

    try:
        contract = json.loads(contract_p.read_text(encoding="utf-8"))
        summary = json.loads(summary_p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"valid": False, "reason": "consumer_artifact_corrupt"}

    if summary.get("stale", False):
        return {"valid": False, "reason": "consumer_summary_stale"}

    if now_ms is not None:
        last_hb = summary.get("last_heartbeat_at_ms") or summary.get("created_at_ms") or 0
        if now_ms - last_hb > 10_000:
            return {"valid": False, "reason": "consumer_summary_heartbeat_expired"}

    computed_contract_sha = canonical_root_contract_sha256(contract)
    if summary.get("consumer_root_contract_sha256") != computed_contract_sha:
        return {"valid": False, "reason": "consumer_root_contract_hash_mismatch"}

    if contract.get("root_mode") != "v2_production":
        return {"valid": False, "reason": "consumer_root_mode_not_v2_production"}
    if contract.get("formal_event_contract_versions_allowed") != [2]:
        return {"valid": False, "reason": "consumer_formal_event_versions_mismatch"}
    if contract.get("formal_schedule_revision_contract_versions_allowed") != [1, 2]:
        return {"valid": False, "reason": "consumer_formal_revision_versions_mismatch"}
    if not contract.get("consumer_static_attestation_verified", False):
        return {"valid": False, "reason": "consumer_contract_static_attestation_unverified"}

    for field in (
        "consumer_root_id",
        "consumer_startup_commit_sha",
        "consumer_runtime_manifest_sha256",
    ):
        if not summary.get(field) or summary.get(field) != contract.get(field):
            return {"valid": False, "reason": f"{field}_cross_artifact_mismatch"}

    if contract.get("consumer_startup_commit_sha") != expected_d_startup_head_sha:
        return {"valid": False, "reason": "consumer_startup_commit_mismatch"}

    if contract.get("consumer_runtime_manifest_sha256") != expected_consumer_manifest_sha256:
        return {"valid": False, "reason": "consumer_runtime_manifest_mismatch"}

    if not summary.get("consumer_static_attestation_verified", False):
        return {"valid": False, "reason": "consumer_static_attestation_unverified"}

    if not summary.get("consumer_runtime_attestation_verified", False):
        return {"valid": False, "reason": "consumer_runtime_attestation_unverified"}

    if summary.get("consumer_runtime_attestation_compromised", False):
        return {"valid": False, "reason": "consumer_runtime_attestation_compromised"}

    source_d_root = contract.get("source_stage1_5d_output_root_id")
    source_d_events = contract.get("source_stage1_5d_events_root_id")
    source_d_gate = contract.get("source_stage1_5d_runtime_gate_root_id")

    if not (source_d_root and source_d_root == source_d_events == source_d_gate == expected_d_output_root_id):
        return {"valid": False, "reason": "consumer_source_root_binding_mismatch"}

    if summary.get("blocker"):
        return {"valid": False, "reason": "consumer_blocker_present"}

    if summary.get("block_new_event_admission", False):
        return {"valid": False, "reason": "consumer_admission_blocked"}

    consumer_root_id = contract.get("consumer_root_id")
    consumer_process_id = summary.get("consumer_process_instance_id")

    if armed_consumer_state is not None:
        if consumer_root_id != armed_consumer_state.get("consumer_root_id"):
            return {"valid": False, "reason": "armed_consumer_root_id_mismatch"}
        if consumer_process_id != armed_consumer_state.get("consumer_process_instance_id"):
            return {"valid": False, "reason": "armed_consumer_process_id_mismatch"}
        if str(contract_p.resolve()) != armed_consumer_state.get("consumer_root_contract_path"):
            return {"valid": False, "reason": "armed_consumer_contract_path_mismatch"}
        if str(summary_p.resolve()) != armed_consumer_state.get("consumer_summary_path"):
            return {"valid": False, "reason": "armed_consumer_summary_path_mismatch"}

    return {
        "valid": True,
        "consumer_root_id": consumer_root_id,
        "consumer_process_instance_id": consumer_process_id,
        "consumer_root_contract_path": str(contract_p.resolve()),
        "consumer_summary_path": str(summary_p.resolve()),
        "reason": "consumer_proof_passed",
    }



def read_current_commit_sha() -> str:
    """Return the checked-out commit, or an empty value when it cannot attest."""
    repo_root = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def build_schedule_revision_producer_attestation(
    *,
    integration_health: str,
    static_proof_result: dict | None = None,
    consumer_proof_result: dict | None = None,
) -> dict:
    """Compute the only gate evidence allowed to enable formal revisions."""
    configured = bool(base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED)
    prerequisite_commit = str(base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA).strip()

    current_commit_sha = read_current_commit_sha()
    static_valid = bool(
        static_proof_result
        and static_proof_result.get("valid", False)
        and static_proof_result.get("startup_head_sha") == current_commit_sha
    )

    consumer_valid = not configured
    if configured:
        consumer_valid = bool(consumer_proof_result and consumer_proof_result.get("valid", False))

    prerequisites_verified = bool(
        prerequisite_commit
        and static_valid
        and consumer_valid
        and base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED
        and base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED
    )
    effective = configured and prerequisites_verified and integration_health == "ready"
    if effective:
        health = "ready"
    elif not configured:
        health = "producer_disabled"
    elif not prerequisites_verified:
        health = "prerequisites_unmet"
    else:
        health = integration_health or "integration_health_missing"
    return {
        "schedule_revision_producer_supported": True,
        "schedule_revision_producer_configured_enabled": configured,
        "schedule_revision_producer_consumer_prerequisites_verified": prerequisites_verified,
        "schedule_revision_producer_effective_enabled": effective,
        "schedule_revision_producer_health": health,
    }



def append_stage1_5d_diagnostic(stream_paths: dict, row: dict) -> None:
    diagnostics_path = stream_paths.get("detail_retry_terminal_diagnostics")
    if diagnostics_path is None:
        diagnostics_path = stream_paths.get("diagnostics")
    if diagnostics_path is None:
        return
    append_jsonl(diagnostics_path, row, storage_guard=stream_paths["storage_guard"])


def append_formal_futures_launch_event(stream_paths: dict, row: dict) -> dict | None:
    symbols = row.get("symbols", [])

    # Check v2 contract validation for all symbols
    blockers = []
    if row.get("formal_event_contract_version") == 2:
        if not symbols:
            blockers.append("symbols_empty")
        for sym in symbols:
            val = validate_launch_anchor_contract(row, sym, compatibility_mode=False)
            if not val["valid"]:
                blockers.extend([f"{sym}:{b}" for b in val.get("blockers", [])])
        if row.get("event_all_symbols_consumable_by_stage1_5f") is False:
            blockers.append("batch_not_consumable")
    else:
        row = coerce_legacy_launch_event_to_formal(row)
        validation = validate_formal_launch_event(row)
        if not validation["valid"]:
            blockers.extend(validation.get("blockers", []))

    if blockers:
        append_stage1_5d_diagnostic(
            stream_paths,
            {
                "diagnostic_stream": "formal_contract_validation_failed",
                "diagnostic_type": "formal_event_contract_invalid",
                "formal_contract_blockers": blockers,
                "source_article_id": row.get("source_article_id"),
                "event_id": row.get("event_id"),
                "symbols": row.get("symbols"),
                "parser_version": row.get("parser_version"),
                "symbol_extraction_version": row.get("symbol_extraction_version"),
                "raw_event": row,
            },
        )
        return None
    append_jsonl(stream_paths["events"], row, storage_guard=stream_paths["storage_guard"])
    return row


def append_formal_schedule_revision(stream_paths: dict, row: dict) -> dict | None:
    validation = validate_schedule_revision_contract(row)
    if not validation["valid"]:
        append_stage1_5d_diagnostic(
            stream_paths,
            {
                "diagnostic_stream": "formal_schedule_revision_contract_validation_failed",
                "diagnostic_type": "formal_schedule_revision_contract_invalid",
                "formal_contract_blockers": validation.get("blockers", []),
                "source_article_id": row.get("source_article_id"),
                "supersedes_source_article_id": row.get("supersedes_source_article_id"),
                "symbols": row.get("symbols"),
                "revision_id": row.get("revision_id"),
                "raw_event": row,
            },
        )
        return None
    append_jsonl(stream_paths["events"], row, storage_guard=stream_paths["storage_guard"])
    return row



def process_trusted_schedule_revision_detail(
    *,
    stream_paths: dict,
    source_article_id: str,
    title: str,
    detail_text: str,
    symbols: list[str],
    symbol_launch_times_ms: dict[str, int] | None,
    payload_sha256: str,
    available_at_ms: int,
    producer_effective_enabled: bool,
    formal_launch_identity_index_snapshot: str | None = None,
    emitted_revision_semantic_ids: set[str] | None = None,
) -> dict:
    """Classify one trusted detail and emit only fully linked v2 revisions."""
    candidates = classify_schedule_revision_candidates(detail_text, title=title)
    if not candidates:
        return {"status": "not_revision", "emitted_count": 0}

    linked_articles = set(re.findall(r"(?:announcement(?:/detail)?/|articleCode=)([0-9a-fA-F]{32})", detail_text))
    linked_articles.discard(source_article_id)
    supersedes_source_article_id = next(iter(linked_articles), "") if len(linked_articles) == 1 else ""
    index_rows, index_blockers = load_valid_formal_launch_identity_index(
        stream_paths["formal_launch_identity_index"],
        as_of_ms=available_at_ms,
        snapshot_path=formal_launch_identity_index_snapshot,
    )

    launch_times = symbol_launch_times_ms or {}
    candidate = dict(candidates[0])
    candidate.update(
        {
            "source_article_id": source_article_id,
            "symbols": [str(symbol).upper() for symbol in symbols if str(symbol).strip()],
            "payload_sha256": payload_sha256,
            "symbol_candidates": {
                str(symbol).upper(): {
                    "symbol": str(symbol).upper(),
                    "supersedes_source_article_id": supersedes_source_article_id,
                    "link_level_candidate": "L1_exact_article_id" if supersedes_source_article_id else "L4_symbol_only",
                    "revised_anchor_ms": launch_times.get(str(symbol).upper()),
                }
                for symbol in symbols
                if str(symbol).strip()
            },
        }
    )
    if index_blockers or not candidate["symbols"]:
        append_stage1_5d_diagnostic(
            stream_paths,
            build_revision_diagnostic(candidate, {"link_status": "blocked", "blockers": index_blockers}, producer_decision_at_ms=available_at_ms),
        )
        return {
            "status": "revision_diagnostic",
            "emitted_count": 0,
            "producer_health": "blocked_index_collision" if "index_collision" in index_blockers else "blocked_index",
        }
    if candidate["revision_intent"] == "rescheduled_with_new_anchor" and any(
        entry.get("revised_anchor_ms") is None for entry in candidate["symbol_candidates"].values()
    ):
        append_stage1_5d_diagnostic(
            stream_paths,
            build_revision_diagnostic(candidate, {"link_status": "blocked", "reason": "revised_anchor_missing"}, producer_decision_at_ms=available_at_ms),
        )
        return {"status": "revision_diagnostic", "emitted_count": 0}

    rows, batch_result = emit_schedule_revision_batch(
        candidate,
        index_rows,
        available_at_ms=available_at_ms,
        lookback_days=base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_LOOKBACK_DAYS,
        emitted_ids=emitted_revision_semantic_ids,
    )
    if batch_result["batch_status"] == "already_emitted":
        return {"status": "revision_replay_noop", "emitted_count": 0}
    if not producer_effective_enabled or not rows:
        reason = "producer_disabled_or_prerequisites_unmet" if not producer_effective_enabled else batch_result
        append_stage1_5d_diagnostic(
            stream_paths,
            build_revision_diagnostic(candidate, {"link_status": "blocked", "reason": reason}, producer_decision_at_ms=available_at_ms),
        )
        return {"status": "revision_diagnostic", "emitted_count": 0}

    emitted = [append_formal_schedule_revision(stream_paths, row) for row in rows]
    if any(row is None for row in emitted):
        append_stage1_5d_diagnostic(
            stream_paths,
            build_revision_diagnostic(candidate, {"link_status": "blocked", "reason": "formal_append_failed"}, producer_decision_at_ms=available_at_ms),
        )
        return {"status": "revision_diagnostic", "emitted_count": 0}
    if emitted_revision_semantic_ids is not None:
        emitted_revision_semantic_ids.update(
            str(row["revision_semantic_id"]) for row in emitted if row is not None
        )
    return {"status": "revision_emitted", "emitted_count": len(emitted)}


def record_formal_futures_launch_event(
    *,
    stream_paths: dict,
    row: dict,
    seen_event_ids: set,
    events_detected: list,
) -> dict | None:
    from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import (
        append_jsonl,
    )
    from src.research.external_signal_shadow.stage1_5d_schedule_revision_producer import (
        build_formal_launch_identity_index_rows,
    )

    event_id = row.get("event_id")
    if event_id in seen_event_ids:
        return None
    row_copy = dict(row)
    rec_auth = stream_paths.get("active_root_recovery_authority")
    if rec_auth and row_copy.get("source_article_id") == rec_auth.get("article_id"):
        row_copy["detail_recovery_provenance"] = rec_auth["provenance"]
    written = append_formal_futures_launch_event(stream_paths, row_copy)
    if written is None:
        return None
    seen_event_ids.add(written["event_id"])
    events_detected.append(written)

    # Poll Ordering Rule: append launch event first, then append identity index.
    index_path = Path(stream_paths.get("formal_launch_identity_index", ""))
    index_rows = build_formal_launch_identity_index_rows(
        written,
        source_root_id=str(index_path.parent.resolve()) if index_path else "",
        commit_sha=read_current_commit_sha(),
        durable_at_ms=int(time.time() * 1000),
    )
    if index_rows and "formal_launch_identity_index" in stream_paths:
        for idx_row in index_rows:
            append_jsonl(stream_paths["formal_launch_identity_index"], idx_row, storage_guard=stream_paths["storage_guard"])


    return written





def validate_candidate_symbols_against_exchangeinfo(
    candidates: list[str],
    exchangeinfo_by_symbol: dict[str, dict],
    allowed_margin_assets: tuple[str, ...],
    allowed_quote_assets: tuple[str, ...],
    allowed_contract_types: tuple[str, ...],
    validatable_statuses: tuple[str, ...],
    emittable_statuses: tuple[str, ...],
    now_ms: int,
) -> dict:
    validated_symbols = []
    pending_symbols = []
    rejected_symbols = []
    pending_reasons = {}
    rejection_reasons = {}
    symbol_exchangeinfo = {}
    symbol_onboard_times_ms = {}

    for c in candidates:
        target_symbol = c
        if target_symbol not in exchangeinfo_by_symbol:
            pending_symbols.append(c)
            pending_reasons[c] = "exchange_info_symbol_missing"
            continue

        meta = exchangeinfo_by_symbol[target_symbol]
        required_keys = ("status", "contractType", "quoteAsset", "marginAsset")
        if not all(k in meta for k in required_keys):
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_incomplete_metadata"
            continue

        if meta.get("contractType") not in allowed_contract_types:
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_disallowed_contract_type"
            continue

        if meta.get("marginAsset") not in allowed_margin_assets:
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_disallowed_margin_asset"
            continue

        if meta.get("quoteAsset") not in allowed_quote_assets:
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_disallowed_quote_asset"
            continue

        status = meta.get("status")
        if status in emittable_statuses:
            validated_symbols.append(target_symbol)
            symbol_exchangeinfo[target_symbol] = meta
            if "onboardDate" in meta:
                try:
                    symbol_onboard_times_ms[target_symbol] = int(meta["onboardDate"])
                except (ValueError, TypeError):
                    pass
        elif status in validatable_statuses:
            pending_symbols.append(c)
            pending_reasons[c] = "exchange_info_symbol_status_not_trading_prelaunch"
            symbol_exchangeinfo[target_symbol] = meta
            if "onboardDate" in meta:
                try:
                    symbol_onboard_times_ms[target_symbol] = int(meta["onboardDate"])
                except (ValueError, TypeError):
                    pass
        else:
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_unrecognized_status"


    return {
        "validated_symbols": validated_symbols,
        "pending_symbols": pending_symbols,
        "rejected_symbols": rejected_symbols,
        "pending_reasons": pending_reasons,
        "rejection_reasons": rejection_reasons,
        "symbol_exchangeinfo": symbol_exchangeinfo,
        "symbol_onboard_times_ms": symbol_onboard_times_ms,
    }


def build_effective_launch_times_ms(
    candidate_symbols: list[str],
    symbol_onboard_times_ms: dict,
    symbol_launch_times_ms: dict,
    source_published_at_ms: int,
    first_detected_at_ms: int,
    allow_release_date_fallback: bool = True,
    allow_legacy_max_age_fallback: bool = True,
) -> dict:
    effective = {}
    per_symbol_sources = {}
    sources = set()
    for s in candidate_symbols:
        if s in symbol_onboard_times_ms and symbol_onboard_times_ms[s] > 0:
            effective[s] = symbol_onboard_times_ms[s]
            per_symbol_sources[s] = "exchangeinfo_onboard_date"
            sources.add("exchange_info")
        elif s in symbol_launch_times_ms and symbol_launch_times_ms[s] > 0:
            effective[s] = symbol_launch_times_ms[s]
            per_symbol_sources[s] = "detail_symbol_launch_time"
            sources.add("detail")
        elif allow_release_date_fallback and source_published_at_ms > 0:
            effective[s] = source_published_at_ms
            per_symbol_sources[s] = "article_release_date"
            sources.add("article_release_date")
        elif allow_legacy_max_age_fallback:
            legacy_max_age_ms = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 3600) * 1000
            effective[s] = first_detected_at_ms + legacy_max_age_ms
            per_symbol_sources[s] = "legacy_max_age"
            sources.add("legacy_max_age")
        else:
            effective[s] = 0
            per_symbol_sources[s] = "none"
            sources.add("none")

    if "exchange_info" in sources:
        source_str = "exchange_info"
    elif "detail" in sources:
        source_str = "detail"
    elif "article_release_date" in sources:
        source_str = "article_release_date"
    elif "legacy_max_age" in sources:
        source_str = "legacy_max_age"
    else:
        source_str = "none"

    return {
        "symbol_effective_launch_times_ms": effective,
        "launch_time_source": source_str,
        "symbol_effective_launch_time_sources": per_symbol_sources,
    }


def build_candidate_symbol_set_identity(candidate_symbols: list[str]) -> dict:
    ordered = []
    seen = set()
    for sym in candidate_symbols or []:
        norm = str(sym or "").strip().upper()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        ordered.append(norm)
    normalized = sorted(ordered)
    payload = json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))
    return {
        "candidate_symbols_ordered": ordered,
        "candidate_symbols_normalized": normalized,
        "candidate_symbol_set_hash_version": 1,
        "candidate_symbol_set_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def is_multi_symbol_article_state(state: dict, extraction_result: dict | None = None) -> bool:
    if extraction_result and extraction_result.get("symbols"):
        ext_symbols = list(extraction_result.get("symbols") or [])
        if len(ext_symbols) > 1:
            return True
    if state.get("candidate_symbols") is not None:
        return len(state.get("candidate_symbols") or []) > 1
    if state.get("parsed_candidate_symbols") is not None:
        return len(state.get("parsed_candidate_symbols") or []) > 1
    if state.get("candidate_symbols_ordered") is not None:
        return len(state.get("candidate_symbols_ordered") or []) > 1
    symbols = state.get("symbols")
    if symbols and isinstance(symbols, (list, tuple)):
        return len(symbols) > 1
    return False


def build_symbol_effective_launch_time_sources(
    candidate_symbols: list[str],
    symbol_launch_times_ms: dict,
    symbol_onboard_times_ms: dict,
    effective_launch: dict,
) -> dict[str, str]:
    res = {}
    eff_times = (effective_launch or {}).get("symbol_effective_launch_times_ms") or {}
    eff_sources = (effective_launch or {}).get("symbol_effective_launch_time_sources") or {}
    for sym in candidate_symbols or []:
        norm = str(sym or "").strip().upper()
        if not norm:
            continue
        if norm in eff_sources:
            res[norm] = eff_sources[norm]
        elif int((symbol_launch_times_ms or {}).get(norm) or 0) > 0:
            res[norm] = "detail_symbol_launch_time"
        elif int((symbol_onboard_times_ms or {}).get(norm) or 0) > 0:
            res[norm] = "exchangeinfo_onboard_date"
        elif int(eff_times.get(norm) or 0) > 0:
            res[norm] = "effective_launch_time"
        else:
            res[norm] = "none"
    return res


def is_multi_symbol_candidate_set_ready_to_emit(
    candidate_symbols: list[str],
    validation_result: dict,
    effective_launch_times: dict,
    allowed_anchor_sources: tuple[str, ...] = (
        "detail_symbol_launch_time",
        "exchangeinfo_onboard_date",
    ),
) -> bool:
    candidates = [str(s or "").strip().upper() for s in (candidate_symbols or []) if str(s or "").strip()]
    if len(candidates) <= 1:
        return False
    candidate_set = set(candidates)
    if len(candidate_set) != len(candidates):
        return False

    validated = set(validation_result.get("validated_symbols") or [])
    pending = set(validation_result.get("pending_symbols") or [])
    rejected = list(validation_result.get("rejected_symbols") or [])

    if rejected:
        return False

    if validated & pending != set():
        return False
    if (validated | pending) != candidate_set:
        return False

    symbol_exchangeinfo = validation_result.get("symbol_exchangeinfo") or {}
    launch_times = (effective_launch_times or {}).get("symbol_effective_launch_times_ms") or {}
    anchor_sources = (effective_launch_times or {}).get("symbol_effective_launch_time_sources")
    if not anchor_sources:
        top_source = (effective_launch_times or {}).get("launch_time_source")
        if top_source in ("detail", "exchange_info"):
            anchor_sources = {sym: top_source for sym in candidates}
        else:
            anchor_sources = build_symbol_effective_launch_time_sources(candidates, {}, {}, effective_launch_times)

    allowed_statuses = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES", ("PENDING_TRADING", "PRE_TRADING", "TRADING"))
    pending_reasons = validation_result.get("pending_reasons") or {}
    for sym in candidates:
        if str(pending_reasons.get(sym) or "").startswith("exchange_info_symbol_missing") or pending_reasons.get(sym) == "exchange_info_missing":
            return False

        meta = symbol_exchangeinfo.get(sym)
        if meta:
            status = meta.get("status")
        elif sym in validated:
            status = "TRADING"
        elif sym in pending:
            status = "PENDING_TRADING"
        else:
            return False

        if status not in allowed_statuses:
            return False

        t = int(launch_times.get(sym) or 0)
        if t <= 0:
            return False

        src = str(anchor_sources.get(sym) or "").strip()
        if src not in allowed_anchor_sources:
            return False

    return True


def is_multi_symbol_article_ready_to_emit(
    candidate_symbols: list[str],
    validation_result: dict,
    effective_launch: dict,
    state: dict | None = None,
) -> bool:
    return is_multi_symbol_candidate_set_ready_to_emit(candidate_symbols, validation_result, effective_launch)


def build_multi_symbol_emission_id(source_article_id: str, event_type: str, candidate_symbol_set_hash: str) -> str:
    schema_version = 1
    namespace = "binance_futures_announcement"
    raw_key = f"{schema_version}|{namespace}|{event_type}|{source_article_id}|{candidate_symbol_set_hash}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def apply_multi_symbol_candidate_set_contract(
    norm_event: dict,
    state: dict,
    validation_result: dict,
    symbols_override: list[str],
    identity: dict,
    emission_id: str,
    effective_launch: dict,
    now_ms: int,
) -> None:
    norm_event["multi_symbol_emission_mode"] = "all_or_none_candidate_set"
    norm_event["multi_symbol_candidate_set_hash"] = identity["candidate_symbol_set_hash"]
    norm_event["candidate_symbol_set_hash_version"] = identity["candidate_symbol_set_hash_version"]
    norm_event["candidate_symbols_ordered"] = identity["candidate_symbols_ordered"]
    norm_event["candidate_symbols_normalized"] = identity["candidate_symbols_normalized"]
    norm_event["emission_id"] = emission_id
    norm_event["symbol_validation_status"] = "validated_candidate_set"
    norm_event["symbol_exchangeinfo_statuses"] = {
        s: validation_result.get("symbol_exchangeinfo", {}).get(s, {}).get("status")
        for s in symbols_override
    }
    norm_event["symbol_effective_launch_time_sources"] = (
        effective_launch.get("symbol_effective_launch_time_sources") or {}
    )
    norm_event["launch_anchor_policy"] = "bapi_multi_contract_strict"

    state["terminal_state"] = True
    state["terminal_reason"] = "multi_symbol_candidate_set_emitted"
    state["terminal_at_ms"] = now_ms
    state["status"] = "emitted_all_symbols"
    state["symbol_validation_status"] = "emitted_all_symbols"
    state["emission_id"] = emission_id
    state["candidate_symbol_set_hash"] = identity["candidate_symbol_set_hash"]
    state["candidate_symbol_set_hash_version"] = identity["candidate_symbol_set_hash_version"]
    state["candidate_symbols_ordered"] = identity["candidate_symbols_ordered"]
    state["candidate_symbols_normalized"] = identity["candidate_symbols_normalized"]
    state["symbol_effective_launch_time_sources"] = norm_event["symbol_effective_launch_time_sources"]
    state["symbol_exchangeinfo_statuses"] = norm_event["symbol_exchangeinfo_statuses"]
    state["launch_anchor_policy"] = norm_event["launch_anchor_policy"]


def build_emission_index_key(source_article_id: str, candidate_symbol_set_hash: str) -> str:
    return f"{source_article_id}|{candidate_symbol_set_hash}"


def validate_emitted_candidate_set_event_row(row: dict) -> tuple[bool, str, dict]:
    source_article_id = str(row.get("source_article_id") or "").strip()
    if not source_article_id:
        return False, "missing_source_article_id", {}

    symbols = list(row.get("symbols") or [])
    if len(symbols) <= 1 and row.get("multi_symbol_emission_mode") != "all_or_none_candidate_set":
        return False, "not_candidate_set_event_row", {}
    if len(symbols) <= 1:
        return False, "missing_symbols", {}

    mode = row.get("multi_symbol_emission_mode")
    if mode != "all_or_none_candidate_set":
        return False, "invalid_multi_symbol_emission_mode", {}
    if row.get("symbol_validation_status") != "validated_candidate_set":
        return False, "invalid_candidate_set_validation_status", {}
    if row.get("event_type") != "futures_contract_launch":
        return False, "invalid_event_type", {}

    identity = build_candidate_symbol_set_identity(symbols)
    computed_hash = identity["candidate_symbol_set_hash"]
    stored_hash = row.get("multi_symbol_candidate_set_hash")
    if not stored_hash:
        return False, "missing_candidate_set_hash", {}
    if stored_hash != computed_hash:
        return False, "candidate_set_hash_mismatch", {}

    event_type = str(row.get("event_type") or "futures_contract_launch")
    computed_emission_id = build_multi_symbol_emission_id(source_article_id, event_type, computed_hash)
    stored_emission_id = row.get("emission_id")
    if not stored_emission_id:
        return False, "missing_emission_id", {}
    if stored_emission_id != computed_emission_id:
        return False, "emission_id_mismatch", {}

    key = build_emission_index_key(source_article_id, computed_hash)
    info = {
        "key": key,
        "source_article_id": source_article_id,
        "candidate_symbol_set_hash": computed_hash,
        "emission_id": computed_emission_id,
        "event_id": row.get("event_id"),
        "symbols": symbols,
        "parser_payload_hash": row.get("parser_payload_hash"),
    }
    return True, "valid", info


def rebuild_emission_index_from_events(output_root: Path) -> tuple[dict, list[dict]]:
    index = {}
    diagnostics = []
    events_dir = Path(output_root) / "events"
    if not events_dir.exists():
        return index, diagnostics

    seen_emission_ids = {}

    for event_file in sorted(events_dir.glob("*.jsonl")):
        try:
            lines = event_file.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            diagnostics.append({"file": str(event_file), "reason": f"read_error: {e}"})
            continue

        for line_no, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                row = json.loads(line_str)
            except Exception:
                diagnostics.append({
                    "file": str(event_file),
                    "line": line_no,
                    "reason": "malformed_jsonl",
                })
                continue

            valid, reason, info = validate_emitted_candidate_set_event_row(row)
            if not valid:
                if reason == "not_candidate_set_event_row":
                    continue
                diagnostics.append({
                    "file": str(event_file),
                    "line": line_no,
                    "reason": reason,
                    "source_article_id": row.get("source_article_id"),
                })
                continue

            em_id = info["emission_id"]
            if em_id in seen_emission_ids and seen_emission_ids[em_id] != info["parser_payload_hash"]:
                diagnostics.append({
                    "file": str(event_file),
                    "line": line_no,
                    "reason": "duplicate_emission_id_different_payload",
                    "emission_id": em_id,
                })
                continue
            seen_emission_ids[em_id] = info["parser_payload_hash"]

            try:
                rel_path = str(event_file.relative_to(output_root))
            except ValueError:
                rel_path = str(event_file)
            info["event_stream_path"] = rel_path
            index[info["key"]] = info

    return index, diagnostics


def check_article_emission_eligibility(
    state: dict,
    validation_result: dict,
    effective_launch: dict,
    extraction_res: dict | None = None,
) -> tuple[bool, bool, list[str]]:
    is_multi = is_multi_symbol_article_state(state, extraction_res)
    if is_multi:
        candidates = state.get("candidate_symbols") or (extraction_res.get("symbols") if extraction_res else None) or []
        ready = is_multi_symbol_candidate_set_ready_to_emit(candidates, validation_result, effective_launch)
        return ready, True, list(candidates)
    else:
        valid_symbols = list(validation_result.get("validated_symbols") or [])
        effective_times = (effective_launch or {}).get("symbol_effective_launch_times_ms") or {}
        effective_sources = (effective_launch or {}).get("symbol_effective_launch_time_sources") or {}
        ready_symbols = []
        for sym in valid_symbols:
            norm = str(sym or "").strip().upper()
            if int(effective_times.get(norm) or 0) <= 0:
                continue
            if str(effective_sources.get(norm) or "") not in ("detail_symbol_launch_time", "exchangeinfo_onboard_date"):
                continue
            ready_symbols.append(norm)
        return bool(ready_symbols), False, ready_symbols


def title_candidate_needs_detail_launch_anchor(state: dict) -> bool:
    if state.get("detail_fetch_attempted"):
        return False
    if state.get("detail_fetch_status") not in (None, "", "not_needed"):
        return False
    if state.get("symbol_extraction_source") not in ("title", "title_contract_symbol", "title_base_asset_derived"):
        return False
    candidates = state.get("candidate_symbols") or []
    if not candidates:
        return False
    launch_times = state.get("symbol_launch_times_ms") or {}
    effective_sources = state.get("symbol_effective_launch_time_sources") or {}
    for sym in candidates:
        norm = str(sym or "").strip().upper()
        if int(launch_times.get(norm) or 0) > 0:
            return False
        if str(effective_sources.get(norm) or "") in ("detail_symbol_launch_time", "exchangeinfo_onboard_date"):
            return False
    return True


def apply_formal_launch_event_contract(
    norm_event: dict,
    state: dict,
    validation_result: dict,
    symbols_override: list[str],
    effective_launch: dict,
) -> None:
    symbols = [str(s or "").strip().upper() for s in symbols_override if str(s or "").strip()]
    launch_times = dict(state.get("symbol_launch_times_ms") or {})
    onboard_times = dict(state.get("symbol_onboard_times_ms") or validation_result.get("symbol_onboard_times_ms") or {})

    detail_status = str(norm_event.get("detail_fetch_status") or state.get("detail_fetch_status") or "")
    detail_attempted = bool(norm_event.get("detail_fetch_attempted", state.get("detail_fetch_attempted", False)))

    norm_event["detail_fetch_attempted"] = detail_attempted
    norm_event["detail_fetch_status"] = detail_status

    decision_at_ms = int(
        norm_event.get("symbol_resolved_at_ms")
        or norm_event.get("detail_fetched_at_ms")
        or norm_event.get("detected_at_ms")
        or time.time() * 1000
    )
    article_id = str(norm_event.get("source_article_id") or state.get("source_article_id") or "")
    payload_hash = str(
        norm_event.get("detail_payload_hash")
        or norm_event.get("payload_sha256")
        or state.get("last_bapi_payload_sha256")
        or state.get("payload_sha256")
        or ""
    )
    parser_version = str(norm_event.get("parser_version") or PARSER_VERSION)
    title = str(norm_event.get("title") or state.get("title") or "")
    mapping_confidence = "exact_single_symbol" if len(symbols) == 1 else "exact_per_symbol_row"

    symbol_contracts = {}
    for sym in symbols:
        official_ms = int(launch_times.get(sym) or 0) or None
        onboard_ms = int(onboard_times.get(sym) or 0) or None
        raw_time_text = str(
            (state.get("symbol_launch_times_utc") or {}).get(sym)
            or (state.get("symbol_effective_launch_times_utc") or {}).get(sym)
            or official_ms
            or onboard_ms
            or ""
        )
        provenance = {
            "payload_sha256": payload_hash,
            "parser_version": parser_version,
            "raw_time_text": raw_time_text,
            "timezone_text": "UTC",
            "node_path": "bapi_article_body" if detail_attempted else "title_or_exchangeinfo",
            "logical_block_id": f"{article_id}:{sym}" if article_id else sym,
            "schedule_text_context": title,
            "mapping_method": "per_symbol_official_schedule" if official_ms is not None else "exchangeinfo_fallback",
            "mapping_confidence": mapping_confidence,
        }
        symbol_contracts[sym] = build_symbol_anchor_contract(
            symbol=sym,
            official_schedule_anchor_ms=official_ms,
            exchangeinfo_onboard_date_ms=onboard_ms,
            anchor_contract_decision_at_ms=decision_at_ms,
            official_schedule_revision_id=f"{article_id}:{sym}:initial_official_schedule" if official_ms is not None and article_id else None,
            official_schedule_available_at_ms=int(norm_event.get("source_published_at_ms") or norm_event.get("detected_at_ms") or decision_at_ms),
            mapping_confidence=mapping_confidence,
            provenance=provenance,
        )

    formal_row = build_formal_event_anchor_contract_row(
        base_event=norm_event,
        symbol_contracts=symbol_contracts,
    )
    norm_event.clear()
    norm_event.update(formal_row)

    effective_observation_times = dict(norm_event.get("symbol_effective_observation_anchor_ms") or {})
    effective_observation_sources = dict(norm_event.get("symbol_effective_observation_anchor_sources") or {})
    norm_event["symbol_launch_times_ms"] = launch_times
    norm_event["symbol_onboard_times_ms"] = onboard_times
    norm_event["symbol_effective_launch_times_ms"] = effective_observation_times
    norm_event["symbol_effective_launch_time_sources"] = effective_observation_sources
    norm_event["symbol_launch_time_candidates_ms"] = {
        sym: launch_times.get(sym) or onboard_times.get(sym) or effective_observation_times.get(sym)
        for sym in symbols
        if int((launch_times.get(sym) or onboard_times.get(sym) or effective_observation_times.get(sym) or 0)) > 0
    }
    norm_event["launch_time_source"] = "official_schedule_priority_v1"
    norm_event["formal_event_consumable_by_stage1_5f"] = bool(norm_event.get("event_all_symbols_consumable_by_stage1_5f"))
    norm_event["source_contract_status"] = "formal_v2_valid" if norm_event["formal_event_consumable_by_stage1_5f"] else "formal_v2_invalid"
    norm_event["symbol_identity_validation_status"] = "validated_by_exchangeinfo"
    norm_event["launch_anchor_validation_status"] = "valid" if norm_event["formal_event_consumable_by_stage1_5f"] else "invalid"
    norm_event["launch_anchor_evidence_level"] = "official_schedule" if any(
        source == "official_schedule_anchor" for source in effective_observation_sources.values()
    ) else "exchangeinfo_fallback"
    norm_event["launch_anchor_comparison_status"] = norm_event.get("event_anchor_aggregate_status")
    norm_event["launch_anchor_disagreement_ms"] = norm_event.get("event_max_anchor_disagreement_ms")
    norm_event["detail_confirmation_missing"] = not any(int(launch_times.get(sym) or 0) > 0 for sym in symbols)

    state["symbol_launch_time_candidates_ms"] = norm_event["symbol_launch_time_candidates_ms"]
    state["symbol_effective_launch_time_sources"] = effective_observation_sources


def apply_pending_candidate_validation_state(state: dict, validation_result: dict) -> str:
    pending_reasons = validation_result.get("pending_reasons") or {}
    is_prelaunch = any(
        reason == "exchange_info_symbol_status_not_trading_prelaunch"
        for reason in pending_reasons.values()
    )
    if is_prelaunch:
        status = "pending_pre_trading"
        pending_reason = "exchange_info_symbol_status_not_trading_prelaunch"
    else:
        status = "pending_exchangeinfo_missing"
        pending_reason = "exchangeinfo_symbol_not_yet_visible"

    state["symbol_validation_status"] = status
    state["pending_reason"] = pending_reason
    state["exchangeinfo_visible_symbols"] = list(validation_result.get("symbol_exchangeinfo", {}).keys())
    state["exchangeinfo_missing_symbols"] = [
        s for s in state.get("candidate_symbols", []) if s not in validation_result.get("symbol_exchangeinfo", {})
    ]
    state["hard_rejected_symbols"] = list(validation_result.get("rejected_symbols", []))
    state["symbol_exchangeinfo_statuses"] = {
        s: meta.get("status") for s, meta in validation_result.get("symbol_exchangeinfo", {}).items()
    }
    return status


def should_expire_candidate_validation(state: dict, now_ms: int) -> bool:
    first_detected_at_ms = state["first_detected_at_ms"]
    absolute_max_ms = first_detected_at_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_MAX_TOTAL_SEC * 1000

    effective_launch_times = state.get("symbol_effective_launch_times_ms") or {}
    positive_effective_launch_times = [
        int(v) for v in effective_launch_times.values()
        if isinstance(v, (int, float)) and int(v) > 0
    ]
    if positive_effective_launch_times:
        latest_effective_launch_ms = max(positive_effective_launch_times)
        launch_grace_ms = latest_effective_launch_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_GRACE_AFTER_LAUNCH_SEC * 1000
        return now_ms > min(absolute_max_ms, launch_grace_ms)

    if effective_launch_times:
        return now_ms > absolute_max_ms

    legacy_max_age_ms = first_detected_at_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC * 1000
    return now_ms > min(absolute_max_ms, legacy_max_age_ms)


def build_candidate_terminal_event(
    state: dict,
    source_parent_url: str,
    now_ms: int,
    reason: str,
    detail_fetch_status: str = "success",
    symbol_validation_status: str = "rejected",
) -> dict:
    norm_event = normalize_live_event(
        raw=state["raw"],
        source_parent_url=source_parent_url,
        detected_at_ms=state["first_detected_at_ms"],
        source_published_at_ms=state["raw"].get("releaseDate"),
        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
        symbols_override=() if symbol_validation_status == "rejected" else tuple(state.get("candidate_symbols") or ()),
        extraction_metadata={
            "symbol_extraction_source": state.get("symbol_extraction_source", "none"),
            "symbol_derivation_method": state.get("symbol_derivation_method"),
            "quote_derivation_source": state.get("quote_derivation_source"),
            "symbol_validation_status": symbol_validation_status,
            "detail_fetch_attempted": state.get("detail_fetch_attempted", True),
            "detail_fetch_status": detail_fetch_status,
            "symbol_parse_failed_reason": reason,
            "symbol_parse_status": "terminal_failed",
        },
    )
    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
    norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
    norm_event["symbol_resolved_at_ms"] = now_ms
    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]
    norm_event["symbol_launch_times_ms"] = state.get("symbol_launch_times_ms", {})
    norm_event["symbol_onboard_times_ms"] = state.get("symbol_onboard_times_ms", {})
    norm_event["symbol_effective_launch_times_ms"] = state.get("symbol_effective_launch_times_ms", {})
    norm_event["launch_time_source"] = state.get("launch_time_source")
    return norm_event


TRANSIENT_DETAIL_HTTP_STATUSES = {202, 408, 425, 429, 500, 502, 503, 504}

def is_transient_detail_fetch_error(fetch_res: dict) -> bool:
    error = fetch_res.get("error") or ""
    status = fetch_res.get("http_status")
    if error in {"empty_detail_payload", "fixture_missing"}:
        return True
    if status in TRANSIENT_DETAIL_HTTP_STATUSES:
        return True
    if error.startswith("detail_payload_http_status_5"):
        return True
    return False


def is_overdue_retryable_failure_class(state: dict) -> bool:
    return (
        state.get("detail_retryable") is not False
        and state.get("last_detail_failure_class") in ALLOWED_OVERDUE_DETAIL_RETRY_FAILURE_CLASSES
    )


def build_detail_retry_scheduler_diagnostic_row(
    *,
    detail_retry_state: dict[str, dict],
    attempt_codes: list[str],
    now_ms: int,
    endpoint_degraded_until_ms: int,
    detail_budget_per_poll: int,
    min_never_attempted_slots_per_poll: int,
    overdue_attempted_min_interval_ms: int,
    max_article_ids: int = 20,
) -> dict:
    selected = set(attempt_codes)
    selected_overdue = []
    deferred_reason_counts: dict[str, int] = {}
    deferred_count = 0
    never_attempted_exists = any(
        int((state.get("detail_http_request_count") if state.get("detail_http_request_count") is not None else state.get("detail_fetch_attempt_count", 0)) or 0) <= 0
        and not state.get("terminal_state")
        for state in detail_retry_state.values()
    )

    def add_defer(reason: str) -> None:
        nonlocal deferred_count
        deferred_count += 1
        deferred_reason_counts[reason] = deferred_reason_counts.get(reason, 0) + 1

    for code, state in detail_retry_state.items():
        if state.get("terminal_state"):
            continue
        http_count = int(state.get("detail_http_request_count") or 0)
        fetch_count = int(state.get("detail_fetch_attempt_count") or 0)
        next_retry = int(state.get("next_detail_retry_at_ms") or 0)
        if http_count <= 0:
            continue
        if next_retry <= 0:
            add_defer("missing_next_retry_at")
            continue
        if now_ms < next_retry:
            continue

        if code in selected:
            selected_overdue.append(code)
            continue

        if now_ms < endpoint_degraded_until_ms:
            add_defer("endpoint_degraded_active")
        elif not is_overdue_retryable_failure_class(state):
            add_defer("state_not_retryable")
        elif now_ms < int(state.get("last_retry_at_ms") or 0) + overdue_attempted_min_interval_ms:
            add_defer("minimum_interval_not_elapsed")
        elif detail_budget_per_poll <= 0:
            add_defer("http_request_budget_exhausted")
        elif never_attempted_exists and detail_budget_per_poll <= min_never_attempted_slots_per_poll:
            add_defer("never_attempted_slot_protection")
        else:
            add_defer("logical_retry_budget_exhausted")

        if http_count == 0 and fetch_count > 0:
            deferred_reason_counts["attempt_manifest_mismatch"] = (
                deferred_reason_counts.get("attempt_manifest_mismatch", 0) + 1
            )

    return {
        "timestamp_ms": now_ms,
        "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
        "detail_retry_overdue_selected_count": len(selected_overdue),
        "detail_retry_overdue_deferred_count": deferred_count,
        "detail_retry_overdue_deferred_reason_counts": deferred_reason_counts,
        "detail_retry_overdue_selected_article_ids": selected_overdue[:max_article_ids],
        "detail_retry_overdue_selected_article_ids_truncated": len(selected_overdue) > max_article_ids,
    }


def write_smoke_summary_atomically(
    summary_path: str | Path,
    summary_data: dict,
    *,
    storage_guard: Any,
) -> None:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    path = Path(summary_path)
    tmp_path = path.with_suffix(".json.tmp")
    serialized = json.dumps(summary_data, indent=2).encode("utf-8")
    old_size = path.stat().st_size if path.exists() else 0

    def _write_action() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "wb") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)

    result = storage_guard.reserve_and_write(
        artifact_class=(
            "terminal_control_plane"
            if summary_data.get("storage_blocker")
            else "ordinary_control_plane"
        ),
        transient_peak_bytes=len(serialized),
        persistent_delta_bytes=max(0, len(serialized) - old_size),
        write_func=_write_action,
    )
    require_storage_write(storage_guard, result)


def _build_storage_failure_artifacts(
    output_root: str | Path,
    storage_blocker: str,
    storage_guard_status: str,
) -> tuple[dict, dict, dict]:
    storage_blocker = str(storage_blocker)[:512]
    storage_guard_status = str(storage_guard_status)[:128]
    terminal_gate = build_stage1_5d_runtime_gate({
        "output_root": output_root,
        "fatal_blockers": [storage_blocker],
        "storage_budget_passed": False,
    })
    terminal_summary = {
        "decision": "stage1_5d_smoke_invalid",
        "blockers": [storage_blocker],
        "storage_blocker": storage_blocker,
        "storage_guard_status": storage_guard_status,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }
    terminal_diagnostic = {
        "diagnostic_type": "storage_write_blocked",
        "stage": "1.5D",
        "storage_blocker": storage_blocker,
        "storage_guard_status": storage_guard_status,
    }
    return terminal_gate, terminal_summary, terminal_diagnostic


def _storage_failure_write_set_peak(
    terminal_gate: dict,
    terminal_summary: dict,
    terminal_diagnostic: dict,
) -> int:
    return terminal_write_set_peak_bytes([
        json.dumps(terminal_gate, indent=2, sort_keys=True).encode("utf-8"),
        json.dumps(terminal_summary, indent=2).encode("utf-8"),
        json.dumps(terminal_diagnostic, indent=2).encode("utf-8"),
    ])


def classify_detail_attempt_result(fetch_res: dict) -> str:
    if fetch_res.get("error") == "empty_detail_payload":
        return "http_200_empty_untrusted_payload"
    if fetch_res.get("ok"):
        status = fetch_res.get("http_status")
        if status == 202:
            return "http_202_empty"
        return "success"
    else:
        status = fetch_res.get("http_status")
        error = fetch_res.get("error") or ""
        if status == 202 or error == "detail_payload_http_status_202":
            return "http_202_empty"
        if status == 429:
            return "http_429"
        if status and status >= 500:
            return "http_5xx"
        if is_transient_detail_fetch_error(fetch_res):
            return "network_error"
        return "non_transient_error"


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-public-readonly", action="store_true")
    parser.add_argument("--fixture-json", type=str)
    parser.add_argument("--poll-interval-sec", type=int, default=60)
    parser.add_argument("--max-polls", type=int)
    parser.add_argument("--max-seconds", type=int)
    parser.add_argument(
        "--stage1-5c1-summary",
        type=str,
        default="data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json",
    )
    parser.add_argument(
        "--stage1-5c-summary",
        type=str,
        default="data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="data/external_signal_shadow/stage1_5d/live_event_source_smoke/",
    )
    parser.add_argument("--output-summary", type=str)
    parser.add_argument("--formal-launch-identity-index-snapshot", type=str)
    parser.add_argument("--stage1-5f-consumer-root-contract", type=str, default="")
    parser.add_argument("--stage1-5f-consumer-summary", type=str, default="")
    parser.add_argument("--active-root-recovery-source-article-id", type=str, default=None)
    parser.add_argument(
        "--active-root-recovery-provenance",
        type=str,
        choices=["active_root_retry_cycle_recovery_v1"],
        default=None,
    )

    args = parser.parse_args(argv)

    has_art = bool(args.active_root_recovery_source_article_id)
    has_prov = bool(args.active_root_recovery_provenance)
    if has_art != has_prov:
        parser.error("Both --active-root-recovery-source-article-id and --active-root-recovery-provenance must be provided together.")
    if has_art:
        import re
        if not re.fullmatch(r"[0-9a-f]{32}", args.active_root_recovery_source_article_id):
            parser.error("Invalid --active-root-recovery-source-article-id: must be exactly 32 lowercase hex characters.")

    return args


def _main():
    args = parse_args()


    output_root = Path(args.output_root)
    output_summary_path = (
        Path(args.output_summary)
        if args.output_summary
        else output_root / "binance_futures_launch_smoke_summary.json"
    )

    startup_head_sha = "0" * 40
    try:
        git_res = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        if re.match(r"^[0-9a-f]{40}$", git_res):
            startup_head_sha = git_res
    except Exception:
        pass

    expected_resume_provenance = build_stage1_5d_v3_resume_provenance(output_root, startup_head_sha)
    preflight_res = preflight_stage1_5d_v3_root(
        output_root,
        output_summary_path,
        expected_resume_provenance=expected_resume_provenance,
    )

    if preflight_res["kind"] == "rejected":
        print(f"stage1_5d_v3_resume_preflight_rejected: {preflight_res['reason']}")
        sys.exit(1)

    if preflight_res["kind"] == "fresh":
        try:
            output_root.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            print("stage1_5d_v3_fresh_root_creation_rejected: root already exists")
            sys.exit(1)
        if not output_root.is_dir() or output_root.is_symlink():
            print("stage1_5d_v3_fresh_root_creation_rejected: root not regular directory")
            sys.exit(1)

    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard
    startup_gate, startup_summary, startup_diagnostic = _build_storage_failure_artifacts(
        output_root,
        "x" * 512,
        "x" * 128,
    )
    storage_guard = StorageGuard(
        output_root=output_root,
        stage="1.5D",
        terminal_write_set_peak_bytes=_storage_failure_write_set_peak(
            startup_gate,
            startup_summary,
            startup_diagnostic,
        ),
    )
    process_instance_id = f"proc_{os.getpid()}_{int(time.time())}"
    storage_guard.cleanup_owned_temp_files(process_instance_id)

    startup_res = storage_guard.validate_startup()
    if startup_res["status"] != "ready":
        storage_blocker = str(startup_res.get("storage_blocker") or startup_res["status"])
        terminal_gate, terminal_summary, terminal_diagnostic = _build_storage_failure_artifacts(
            output_root,
            storage_blocker,
            startup_res["status"],
        )
        for path, artifact in (
            (output_root / "live_safety_gate_summary.json", terminal_gate),
            (output_summary_path, terminal_summary),
            (output_root / "storage_failure_diagnostic.json", terminal_diagnostic),
        ):
            try:
                if path.name == "live_safety_gate_summary.json":
                    write_stage1_5d_runtime_gate(output_root, artifact, storage_guard=storage_guard)
                else:
                    write_smoke_summary_atomically(path, artifact, storage_guard=storage_guard)
            except RuntimeError as exc:
                print(f"StorageGuard terminal evidence write failed: {exc}")
        print(f"StorageGuard startup validation failed: {startup_res['storage_blocker']}")
        sys.exit(1)


    # 1. Safety Check: must have live-public-readonly or fixture-json BEFORE checking evidence files
    if not args.live_public_readonly and not args.fixture_json:
        invalid_summary = {
            "decision": "stage1_5d_smoke_invalid",
            "blockers": ["missing_live_flag_or_fixture"],
            "fixture_run": False,
            "debug_short_run": False,
            "observation_hours": 0.0,
            "research_result_valid": False,
            "event_detection_validated": False,
            "poll_count": 0,
            "new_futures_launch_event_count": 0,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }
        write_smoke_summary_atomically(
            output_summary_path,
            invalid_summary,
            storage_guard=storage_guard,
        )
        print("Error: missing --live-public-readonly or --fixture-json")
        return 2

    # 2. Validate Upstream Evidence
    evidence_res = validate_upstream_evidence(args.stage1_5c1_summary, args.stage1_5c_summary)
    prior_stage_safety_prerequisite_met = bool(evidence_res.get("upstream_evidence_valid", True))
    if not evidence_res["upstream_evidence_valid"]:

        invalid_summary = {
            "decision": "stage1_5d_smoke_invalid",
            "blockers": ["upstream_evidence_missing_or_invalid"] + evidence_res["blockers"],
            "fixture_run": bool(args.fixture_json),
            "debug_short_run": True,
            "observation_hours": 0.0,
            "research_result_valid": False,
            "event_detection_validated": False,
            "poll_count": 0,
            "new_futures_launch_event_count": 0,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }
        write_smoke_summary_atomically(
            output_summary_path,
            invalid_summary,
            storage_guard=storage_guard,
        )
        print("Error: upstream evidence invalid")
        return 0

    # 3. Main Polling Loop
    start_time = time.time()
    poll_count = 0
    poll_success_count = 0
    poll_failed_count = 0
    consecutive_failed_polls = 0
    source_format_drift_count = 0
    schema_parse_error_count = 0
    storage_budget_passed = True
    detail_budget_starved_count = 0
    heartbeats = []
    events_detected = []
    seen_event_ids = set()
    first_bar_queue = []
    request_manifest = []
    raw_futures_launch_article_count = 0
    symbol_parsed_event_count = 0
    symbol_parse_failed_count = 0
    last_poll_started_at_ms = None
    first_poll_started_at_ms = None



    detail_retry_state = {}
    if preflight_res["kind"] == "resumable":
        scheduler_state = preflight_res["state"]
        catalog_bootstrap_cutoff_ms = scheduler_state.get("catalog_bootstrap_cutoff_ms")
        formal_completed_source_article_ids = set(preflight_res.get("formal_completed_source_article_ids") or set())
    else:
        scheduler_state = {
            "metadata_version": 3,
            "catalog_bootstrap_cutoff_ms": None,
            "resume_provenance": expected_resume_provenance,
            "articles": {},
            "endpoint_health": {
                "recent_detail_attempt_results": [],
                "detail_endpoint_degraded_until_ms": 0,
                "detail_endpoint_transient_error_rate": 0.0,
                "by_variant": {},
                "endpoint_health_by_source": {},
            },
        }
        catalog_bootstrap_cutoff_ms = None
        formal_completed_source_article_ids = set()

    payload_version_first_observed = load_payload_version_first_observed(
        output_root / "revision_payload_versions.jsonl"
    )
    emitted_revision_semantic_ids = load_emitted_revision_semantic_ids(output_root / "events")
    persisted_articles = scheduler_state.get("articles", {})
    endpoint_health = scheduler_state.get("endpoint_health", {})
    if not isinstance(endpoint_health, dict):
        endpoint_health = {}
    if "recent_detail_attempt_results" not in endpoint_health:
        endpoint_health["recent_detail_attempt_results"] = []
    if "detail_endpoint_degraded_until_ms" not in endpoint_health:
        endpoint_health["detail_endpoint_degraded_until_ms"] = 0

    startup_now_ms = int(time.time() * 1000)
    for code, article in persisted_articles.items():
        if article.get("terminal_state"):
            continue
        raw_art = {
            "code": article["source_article_id"],
            "title": article["title"],
            "releaseDate": article.get("source_published_at_ms"),
        }
        art_row = dict(article)
        art_row["raw"] = raw_art
        detail_retry_state[code] = art_row


    detail_fetch_attempted_count = 0
    detail_fetch_fallback_attempt_count = 0
    detail_fetch_fallback_success_count = 0
    detail_fetch_success_count = 0
    detail_fetch_failed_count = 0
    detail_fetch_budget_deferred_count = 0
    detail_fetch_url_rejected_count = 0
    detail_symbol_extracted_count = 0
    detail_symbol_parse_failed_count = 0
    detail_empty_payload_count = 0
    detail_http_not_ready_count = 0
    detail_terminal_failed_count = 0
    detail_transient_timeout_count = 0
    title_symbol_extracted_count = 0
    symbol_empty_event_count = 0

    # New scheduler counters
    detail_budget_starved_count = 0
    detail_never_attempted_expired_count = 0
    detail_first_attempt_sla_breach_count = 0
    detail_scheduler_pending_count = 0
    detail_scheduler_backoff_count = 0
    detail_endpoint_degraded_count = 0
    detail_endpoint_degraded_active = 0
    detail_degraded_recent_retry_count = 0
    detail_success_symbols_empty_count = 0
    detail_retry_overdue_selected_total = 0
    detail_retry_overdue_deferred_total = 0
    detail_retry_overdue_retry_cycle_total = 0

    bapi_detail_request_count = 0
    bapi_detail_success_count = 0
    bapi_detail_trusted_payload_count = 0
    bapi_detail_schema_drift_count = 0
    bapi_detail_identity_mismatch_count = 0
    bapi_detail_rate_limited_count = 0
    bapi_to_support_fallback_count = 0
    bapi_symbol_parse_success_count = 0
    bapi_symbol_validation_pending_count = 0
    bapi_symbol_validation_success_count = 0
    bapi_payload_revision_count = 0
    bapi_payload_hash_change_count = 0
    schedule_revision_emitted_count = 0
    schedule_revision_diagnostic_count = 0
    schedule_revision_index_collision_count = 0
    schedule_revision_integration_health = "initializing"
    repo_root = Path(__file__).resolve().parents[2]
    prereq_sha = str(base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA).strip()
    static_proof_result = verify_git_ancestry_and_static_proof(
        repo_root=repo_root,
        prerequisite_sha=prereq_sha,
        protected_manifest=PROTECTED_TREE_MANIFEST + CONSUMER_RUNTIME_MANIFEST,
        deadline_monotonic=time.monotonic() + 10.0,
    )
    current_commit_sha = static_proof_result.get("startup_head_sha") or read_current_commit_sha()
    stage1_5d_out_id = canonical_root_id(output_root)
    consumer_manifest_sha = canonical_manifest_sha256("1.5F_v1", CONSUMER_RUNTIME_MANIFEST)
    runtime_protected_manifest = PROTECTED_TREE_MANIFEST + CONSUMER_RUNTIME_MANIFEST
    attestation_lifecycle = {
        "producer_armed_once": False,
        "runtime_attestation_compromised": False,
    }

    armed_consumer_state = None
    consumer_proof_result = None
    if base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED:
        consumer_proof_result = verify_stage1_5f_consumer_proof(
            consumer_root_contract_path=args.stage1_5f_consumer_root_contract,
            consumer_summary_path=args.stage1_5f_consumer_summary,
            expected_d_output_root_id=stage1_5d_out_id,
            expected_d_startup_head_sha=current_commit_sha,
            expected_consumer_manifest_sha256=consumer_manifest_sha,
            armed_consumer_state=armed_consumer_state,
            now_ms=int(time.time() * 1000),
        )
    schedule_revision_producer_attestation = build_schedule_revision_producer_attestation(
        integration_health="initializing",
        static_proof_result=static_proof_result,
        consumer_proof_result=consumer_proof_result,
    )
    schedule_revision_producer_effective_enabled = schedule_revision_producer_attestation[
        "schedule_revision_producer_effective_enabled"
    ]


    candidate_validation_pending_count = 0

    candidate_validation_success_count = 0
    candidate_validation_failed_count = 0
    candidate_validation_expired_count = 0
    u_settlement_symbol_extracted_count = 0
    pre_launch_validation_deferred_count = 0
    max_symbols = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS", 30)



    query_params = getattr(
        base,
        "EXTERNAL_SIGNAL_STAGE1_5D_ANNOUNCEMENT_QUERY_PARAMS",
        {"type": "1", "pageNo": "1", "pageSize": "50"},
    )
    base_url = getattr(
        base,
        "EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_BASE_URL",
        "https://www.binance.com",
    )
    list_path = getattr(
        base,
        "EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_LIST_PATH",
        "/bapi/composite/v1/public/cms/article/list/query",
    )
    fatal_blockers = []
    source_parent_url = "https://www.binance.com/en/support/announcement"
    output_root.mkdir(parents=True, exist_ok=True)
    active_root_recovery_authority = None
    if args.active_root_recovery_source_article_id:
        target_art = args.active_root_recovery_source_article_id
        art_info = persisted_articles.get(target_art)
        if not art_info:
            logger.error("Active root recovery target article not found in scheduler state: {}", target_art)
            sys.exit(1)
        if art_info.get("terminal_state"):
            logger.error("Active root recovery target article is already terminal: {}", target_art)
            sys.exit(1)
        if not art_info.get("detail_retryable", True):
            logger.error("Active root recovery target article is not detail_retryable: {}", target_art)
            sys.exit(1)

        events_dir = output_root / "events"
        if events_dir.exists():
            for event_file in events_dir.glob("*.jsonl"):
                try:
                    lines = event_file.read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError) as exc:
                    logger.error("Active root recovery cannot read event stream {}: {}", event_file, exc)
                    sys.exit(1)
                for line_number, line in enumerate(lines, start=1):
                    if not line.strip():
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError as exc:
                        logger.error(
                            "Active root recovery found malformed event row {}:{}: {}",
                            event_file,
                            line_number,
                            exc,
                        )
                        sys.exit(1)
                    if not isinstance(ev, dict):
                        logger.error(
                            "Active root recovery found non-object event row {}:{}",
                            event_file,
                            line_number,
                        )
                        sys.exit(1)
                    if ev.get("source_article_id") == target_art:
                        logger.error(
                            "Active root recovery target article already has formal event in {}: {}",
                            event_file,
                            target_art,
                        )
                        sys.exit(1)

        active_root_recovery_authority = {
            "article_id": target_art,
            "provenance": args.active_root_recovery_provenance,
        }

    startup_stream_paths = build_stream_paths(output_root, startup_now_ms, storage_guard=storage_guard)
    if active_root_recovery_authority:
        startup_stream_paths["active_root_recovery_authority"] = active_root_recovery_authority
    rebuilt_index_rows, index_rebuild_diagnostics = rebuild_missing_formal_launch_identity_index(
        events_dir=output_root / "events",
        index_path=startup_stream_paths["formal_launch_identity_index"],
        source_root_id=str(output_root.resolve()),
        commit_sha=current_commit_sha,
        storage_guard=storage_guard,
    )
    for diagnostic in index_rebuild_diagnostics:
        append_stage1_5d_diagnostic(
            startup_stream_paths,
            {"diagnostic_type": "formal_launch_identity_index_rebuild", **diagnostic},
        )

    # Recover any pre-crash inflight_cycle reservations and formal emission cleanup
    inflight_recovered = False
    crash_cleanup = preflight_res.get("crash_cleanup_row")
    if crash_cleanup:
        cleanup_id = str(crash_cleanup.get("source_article_id") or "")
        if cleanup_id:
            if cleanup_id in persisted_articles:
                persisted_articles[cleanup_id]["terminal_state"] = True
                persisted_articles[cleanup_id]["terminal_reason"] = "emitted_to_events"
                persisted_articles[cleanup_id]["terminal_at_ms"] = startup_now_ms
                persisted_articles[cleanup_id]["inflight_cycle"] = None
                persisted_articles[cleanup_id]["status"] = "emitted_all_symbols"
            detail_retry_state.pop(cleanup_id, None)
            formal_completed_source_article_ids.add(cleanup_id)
            diag = {
                "diagnostic_type": "formal_emission_crash_recovered_row_purged",
                "source_article_id": cleanup_id,
                "recovered_at_ms": startup_now_ms,
            }
            append_jsonl(startup_stream_paths["detail_retry_scheduler_diagnostics"], diag, storage_guard=storage_guard)
            inflight_recovered = True

    for code, article in list(persisted_articles.items()):
        inflight = article.get("inflight_cycle")
        if inflight:
            inflight_recovered = True
            op = inflight.get("operation") or "unknown"
            diag_type = "request_manifest_persistence_unknown" if op == "detail_request" else f"inflight_op_recovered_{op}"
            diag = {
                "diagnostic_type": diag_type,
                "source_article_id": code,
                "reserved_cycle": inflight.get("cycle"),
                "inflight_cycle": inflight,
                "detected_at_ms": startup_now_ms,
            }
            append_jsonl(startup_stream_paths["detail_retry_scheduler_diagnostics"], diag, storage_guard=storage_guard)
            article["inflight_cycle"] = None
            if code in detail_retry_state:
                detail_retry_state[code]["inflight_cycle"] = None

    if inflight_recovered:
        scheduler_state["articles"] = serialize_stage1_5d_v3_articles(persisted_articles)
        write_detail_retry_scheduler_state(
            output_root,
            scheduler_state,
            metadata_version=3,
            storage_guard=storage_guard,
        )

    # Write startup runtime gate (INITIALIZING)
    init_gate_context = {
        "output_root": output_root,
        "run_id": output_root.name,
        "events_stream_relative_path": "events/*.jsonl",
        "live_public_readonly": args.live_public_readonly,
        "generated_at_ms": int(time.time() * 1000),
        "first_poll_started_at_ms": 0,
        "last_poll_finished_at_ms": 0,
        "last_successful_poll_at_ms": 0,
        "poll_attempt_count": 0,
        "successful_poll_count": 0,
        "failed_poll_count": 0,
        "consecutive_failed_polls": 0,
        "current_fatal_blockers": fatal_blockers,
        "events_detected_count": 0,
        "first_bar_recorded_count": 0,
        "exchangeinfo_status": "PENDING",
        "poll_interval_sec": args.poll_interval_sec,
        "status": "INITIALIZING",
        "decision": "stage1_5d_runtime_gate_initializing",
        "prior_stage_safety_prerequisite_met": prior_stage_safety_prerequisite_met,

        "fixture_run": bool(args.fixture_json),
        "source_format_drift_active": False,
        "schema_parse_error_active": False,
        "storage_budget_passed": True,
        "detail_endpoint_degraded_active": False,
        "bapi_trusted_payload_rate": 1.0,
        "symbol_parse_success_rate": 1.0,
        "symbol_validation_success_rate": 1.0,
        "scheduler_starved_expired_count": sum(
            1 for row in persisted_articles.values()
            if row.get("terminal_failure_type") == "detail_never_attempted_budget_starved"
        ),
        **schedule_revision_producer_attestation,
    }
    write_stage1_5d_runtime_gate(
        output_root,
        build_stage1_5d_runtime_gate(init_gate_context),
        storage_guard=storage_guard,
    )

    while True:
        if args.max_polls is not None and poll_count >= args.max_polls:
            break
        if args.max_seconds is not None and (time.time() - start_time) >= args.max_seconds:
            break

        poll_count += 1
        now_ms = int(time.time() * 1000)
        if first_poll_started_at_ms is None:
            first_poll_started_at_ms = now_ms

        actual_poll_interval_sec = None

        if base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED:
            runtime_result = verify_stage1_5d_runtime_attestation(
                repo_root,
                current_commit_sha,
                runtime_protected_manifest,
                time.monotonic() + 1.0,
            )
            update_stage1_5d_runtime_attestation_latch(attestation_lifecycle, runtime_result)

        poll_schedule_drift_ms = None
        if last_poll_started_at_ms is not None:
            actual_interval_ms = now_ms - last_poll_started_at_ms
            actual_poll_interval_sec = actual_interval_ms / 1000.0
            poll_schedule_drift_ms = actual_interval_ms - (args.poll_interval_sec * 1000)
        last_poll_started_at_ms = now_ms

        stream_paths = build_stream_paths(output_root, now_ms, storage_guard=storage_guard)
        if active_root_recovery_authority:
            stream_paths["active_root_recovery_authority"] = active_root_recovery_authority


        exchangeinfo_by_symbol_cache = None
        ex_ok_cache = None

        def get_exchangeinfo_by_symbol():
            nonlocal exchangeinfo_by_symbol_cache, ex_ok_cache
            if exchangeinfo_by_symbol_cache is not None:
                return exchangeinfo_by_symbol_cache, ex_ok_cache

            if args.fixture_json:
                ex_by_sym = {}
                ex_ok = False
                try:
                    with open(args.fixture_json, "r", encoding="utf-8") as f:
                        fixture_data = json.load(f)
                    if "exchangeInfoPayload" in fixture_data:
                        syms = fixture_data["exchangeInfoPayload"].get("symbols", [])
                        for s_info in syms:
                            symbol_name = s_info.get("symbol")
                            if symbol_name:
                                ex_by_sym[symbol_name] = s_info
                        ex_ok = True
                except Exception as e:
                    print(f"Error parsing fixture exchangeInfoPayload: {e}")

                ex_manifest = {
                    "request_id": f"exchangeInfo_fixture_{int(time.time()*1000)}",
                    "request_type": "exchange_info",
                    "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                    "source_type": "fixture_exchangeinfo",
                    "symbol": "ALL",
                    "url": f"file://{args.fixture_json}#exchangeInfoPayload",
                    "final_url": f"file://{args.fixture_json}#exchangeInfoPayload",
                    "http_status": 200 if ex_ok else None,
                    "row_count": len(ex_by_sym),
                    "error": None if ex_ok else "fixture_exchangeinfo_missing",
                    "fetched_at_ms": int(time.time() * 1000),
                }
                append_jsonl(stream_paths["request_manifest"], ex_manifest, storage_guard=storage_guard)
                request_manifest.append(ex_manifest)

                exchangeinfo_by_symbol_cache = ex_by_sym
                ex_ok_cache = ex_ok
                return exchangeinfo_by_symbol_cache, ex_ok_cache

            ex_path = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_PATH", "/fapi/v1/exchangeInfo")
            ex_url = ex_path if ex_path.startswith("http") else "https://fapi.binance.com" + ex_path

            ex_ok = False
            ex_by_sym = {}
            ex_manifest = {
                "request_id": f"exchangeInfo_{int(time.time()*1000)}",
                "request_type": "exchange_info",
                "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                "source_type": "exchangeInfo",
                "symbol": "ALL",
                "url": ex_url,
                "final_url": ex_url,
                "http_status": None,
                "row_count": 0,
                "error": None,
                "fetched_at_ms": int(time.time() * 1000),
            }
            try:
                ex_res = fetch_public_json(ex_url, live_public_readonly=args.live_public_readonly, timeout_sec=10.0)
                ex_manifest["final_url"] = ex_res.get("final_url", ex_url)
                ex_manifest["http_status"] = ex_res.get("http_status")
                if ex_res["ok"]:
                    ex_ok = True
                    syms = ex_res["payload"].get("symbols", [])
                    ex_manifest["row_count"] = len(syms)
                    for s_info in syms:
                        symbol_name = s_info.get("symbol")
                        if symbol_name:
                            ex_by_sym[symbol_name] = s_info
                else:
                    ex_manifest["error"] = ex_res.get("error")
            except Exception as e:
                ex_manifest["error"] = str(e)
            append_jsonl(stream_paths["request_manifest"], ex_manifest, storage_guard=storage_guard)
            request_manifest.append(ex_manifest)

            exchangeinfo_by_symbol_cache = ex_by_sym
            ex_ok_cache = ex_ok
            return exchangeinfo_by_symbol_cache, ex_ok_cache



        budget_res = enforce_payload_budget(
            stream_paths["raw_payloads"],
            getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_MAX_RAW_PAYLOAD_BYTES_PER_DAY", 50_000_000),
        )
        if not budget_res["storage_budget_passed"]:
            print(f"Error: storage budget exceeded: {budget_res['blocker']}")
            break

        payload = None
        fetch_err = None
        req_url = ""
        final_url = ""
        http_status = None

        if args.fixture_json:
            try:
                with open(args.fixture_json, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                req_url = f"file://{args.fixture_json}"
                final_url = req_url
                http_status = 200
            except Exception as e:
                fetch_err = str(e)
        else:
            req_url = build_announcement_list_url(base_url, list_path, query_params)
            try:
                fetch_res = fetch_public_json(
                    req_url,
                    live_public_readonly=args.live_public_readonly,
                    timeout_sec=getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_REQUEST_TIMEOUT_SEC", 10.0),
                    retry_budget=getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_RETRY_BUDGET", 2),
                )
                if fetch_res["ok"]:
                    payload = fetch_res["payload"]
                    final_url = fetch_res["final_url"]
                    http_status = fetch_res["http_status"]
                else:
                    fetch_err = fetch_res["error"]
                    http_status = fetch_res["http_status"]
            except Exception as e:
                fetch_err = str(e)

        manifest_row = {
            "request_id": f"req_{now_ms}_{poll_count}",
            "request_type": "announcement_list",
            "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
            "source_type": "announcements" if not args.fixture_json else "fixture",
            "symbol": "ALL",
            "url": req_url,
            "final_url": final_url or req_url,
            "http_status": http_status,
            "row_count": len(payload.get("data", {}).get("catalogs", [{}])[0].get("articles", []))
            if payload
            else 0,
            "error": fetch_err,
            "fetched_at_ms": now_ms,
        }
        append_jsonl(stream_paths["request_manifest"], manifest_row, storage_guard=storage_guard)
        request_manifest.append(manifest_row)

        if payload:
            poll_success_count += 1
            consecutive_failed_polls = 0
            cycle_res = run_one_poll_cycle(

                payload=payload,
                detected_at_ms=now_ms,
                source_parent_url="https://www.binance.com/en/support/announcement",
                first_bar_queue=first_bar_queue,
            )
            if base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED:
                consumer_proof_result = verify_stage1_5f_consumer_proof(
                    consumer_root_contract_path=args.stage1_5f_consumer_root_contract,
                    consumer_summary_path=args.stage1_5f_consumer_summary,
                    expected_d_output_root_id=stage1_5d_out_id,
                    expected_d_startup_head_sha=current_commit_sha,
                    expected_consumer_manifest_sha256=consumer_manifest_sha,
                    armed_consumer_state=armed_consumer_state,
                    now_ms=now_ms,
                )
                if attestation_lifecycle["producer_armed_once"] and not consumer_proof_result.get("valid"):
                    attestation_lifecycle["runtime_attestation_compromised"] = True

            schedule_revision_producer_attestation = build_schedule_revision_producer_attestation(
                integration_health=(
                    "runtime_attestation_compromised"
                    if attestation_lifecycle["runtime_attestation_compromised"]
                    else "ready"
                ),
                static_proof_result=static_proof_result,
                consumer_proof_result=consumer_proof_result,
            )
            schedule_revision_producer_effective_enabled = schedule_revision_producer_attestation[
                "schedule_revision_producer_effective_enabled"
            ]
            if schedule_revision_producer_effective_enabled and not attestation_lifecycle["producer_armed_once"]:
                armed_consumer_state = consumer_proof_result
                attestation_lifecycle["producer_armed_once"] = True

            catalogs = payload.get("data", {}).get("catalogs", [])
            raw_articles = catalogs[0].get("articles", []) if catalogs else []
            poll_ok = bool(cycle_res.get("heartbeat", {}).get("poll_success")) and isinstance(raw_articles, list)

            # 1. First trusted poll bootstrap
            if catalog_bootstrap_cutoff_ms is None:
                if poll_ok:
                    catalog_bootstrap_cutoff_ms = now_ms
                    scheduler_state["catalog_bootstrap_cutoff_ms"] = catalog_bootstrap_cutoff_ms
                    for raw_art in raw_articles:
                        code = str(raw_art.get("code") or "")
                        if not code:
                            continue
                        raw_date = (
                            raw_art.get("releaseDate")
                            if (
                                isinstance(raw_art.get("releaseDate"), int)
                                and not isinstance(raw_art.get("releaseDate"), bool)
                                and raw_art.get("releaseDate") > 0
                            )
                            else None
                        )
                        tomb = build_stage1_5d_terminal_tombstone(
                            existing=None,
                            source_article_id=code,
                            title=str(raw_art.get("title") or ""),
                            source_detail_url_normalized=f"{source_parent_url.rstrip('/')}/{code}",
                            source_parent_url=source_parent_url,
                            detected_at_ms=now_ms,
                            first_detected_at_ms=now_ms,
                            reason="catalog_bootstrap_preexisting",
                            now_ms=now_ms,
                            source_published_at_ms=raw_date,
                        )
                        persisted_articles[code] = tomb
                        diag = {
                            "source_article_id": code,
                            "terminal_reason": "catalog_bootstrap_preexisting",
                            "terminal_at_ms": now_ms,
                        }
                        append_jsonl(stream_paths["detail_retry_terminal_diagnostics"], diag, storage_guard=storage_guard)

                    scheduler_state["articles"] = serialize_stage1_5d_v3_articles(persisted_articles)
                    write_detail_retry_scheduler_state(
                        output_root,
                        scheduler_state,
                        metadata_version=3,
                        storage_guard=storage_guard,
                    )
                    cycle_res["events"] = []
                    first_bar_queue.clear()
                    raw_articles = []

            for ev in cycle_res["events"]:
                code = ev["source_article_id"]
                raw_art = next((art for art in raw_articles if art.get("code") == code), {})

                admission = classify_stage1_5d_catalog_admission(
                    raw_art,
                    cutoff_ms=catalog_bootstrap_cutoff_ms,
                    detected_at_ms=now_ms,
                    formal_completed_ids=formal_completed_source_article_ids,
                    persisted_row=persisted_articles.get(code),
                )
                if admission in ("formal_completed", "persisted_terminal"):
                    continue
                if admission in ("source_published_at_invalid", "historical_prebootstrap_catalog_article"):
                    if code not in persisted_articles or not persisted_articles[code].get("terminal_state"):
                        raw_date = (
                            raw_art.get("releaseDate")
                            if (
                                admission != "source_published_at_invalid"
                                and isinstance(raw_art.get("releaseDate"), int)
                                and not isinstance(raw_art.get("releaseDate"), bool)
                                and raw_art.get("releaseDate") > 0
                            )
                            else None
                        )
                        tomb = build_stage1_5d_terminal_tombstone(
                            existing=persisted_articles.get(code),
                            source_article_id=code,
                            title=str(raw_art.get("title") or ""),
                            source_detail_url_normalized=f"{source_parent_url.rstrip('/')}/{code}",
                            source_parent_url=source_parent_url,
                            detected_at_ms=now_ms,
                            first_detected_at_ms=now_ms,
                            reason=admission,
                            now_ms=now_ms,
                            source_published_at_ms=raw_date,
                        )
                        persisted_articles[code] = tomb
                        scheduler_state["articles"] = serialize_stage1_5d_v3_articles(persisted_articles)
                        write_detail_retry_scheduler_state(
                            output_root,
                            scheduler_state,
                            metadata_version=3,
                            storage_guard=storage_guard,
                        )
                        diag = {
                            "source_article_id": code,
                            "terminal_reason": admission,
                            "terminal_at_ms": now_ms,
                        }
                        append_jsonl(stream_paths["detail_retry_terminal_diagnostics"], diag, storage_guard=storage_guard)
                    continue

                raw_futures_launch_article_count += 1
                if ev.get("symbols"):
                    title_symbol_extracted_count += 1
                    symbol_parsed_event_count += 1

                if code not in seen_event_ids and code not in detail_retry_state and not persisted_articles.get(code, {}).get("terminal_state"):
                    persisted = persisted_articles.get(code, {})
                    title_candidate_res = extract_symbol_candidates_from_title(raw_art.get("title") or "", max_symbols)
                    if title_candidate_res["symbol_validation_status"] == "requires_exchange_info_validation":
                        detail_retry_state[code] = build_stage1_5d_v3_active_article(
                            existing=persisted,
                            source_article_id=code,
                            title=raw_art.get("title") or persisted.get("title") or "",
                            source_detail_url_normalized=persisted.get("source_detail_url_normalized") or f"{source_parent_url.rstrip('/')}/{code}",
                            source_parent_url=source_parent_url,
                            source_published_at_ms=raw_art.get("releaseDate") or persisted.get("source_published_at_ms"),
                            detected_at_ms=persisted.get("detected_at_ms", now_ms),
                            first_detected_at_ms=persisted.get("first_detected_at_ms", now_ms),
                            raw=raw_art,
                            event_type="futures_contract_launch",
                            candidate_symbols=title_candidate_res["symbols"],
                            symbol_extraction_source=title_candidate_res["symbol_extraction_source"],
                            symbol_derivation_method=title_candidate_res["symbol_derivation_method"],
                            symbol_validation_status="pending_exchangeinfo_missing",
                            quote_derivation_source="exchange_info",
                            symbol_launch_times_ms=title_candidate_res.get("symbol_launch_times_ms", {}),
                            symbol_onboard_times_ms={},
                            source_published_at_ms_confidence=ev["source_published_at_ms_confidence"],
                            detail_fetch_attempted=False,
                            detail_fetch_status="not_needed",
                        )
                    else:
                        detail_retry_state[code] = build_stage1_5d_v3_active_article(
                            existing=persisted,
                            source_article_id=code,
                            title=raw_art.get("title") or persisted.get("title") or "",
                            source_detail_url_normalized=persisted.get("source_detail_url_normalized") or f"{source_parent_url.rstrip('/')}/{code}",
                            source_parent_url=source_parent_url,
                            source_published_at_ms=raw_art.get("releaseDate") or persisted.get("source_published_at_ms"),
                            detected_at_ms=persisted.get("detected_at_ms", now_ms),
                            first_detected_at_ms=persisted.get("first_detected_at_ms", now_ms),
                            raw=raw_art,
                            event_type="futures_contract_launch",
                            source_published_at_ms_confidence=ev["source_published_at_ms_confidence"],
                            symbol_extraction_source=persisted.get("symbol_extraction_source", "none"),
                            pending_reason=persisted.get("pending_reason", "title_symbol_missing"),
                        )

            # Revision titles are not launch events, but their trusted BAPI
            # detail may supersede a prior launch. Reuse the existing queue.
            for raw_art in raw_articles:
                code = str(raw_art.get("code") or "")
                if not code or code in detail_retry_state or not is_schedule_revision_listing_candidate(
                    str(raw_art.get("title") or "")
                ):
                    continue
                persisted = persisted_articles.get(code, {})
                detail_retry_state[code] = build_stage1_5d_v3_active_article(
                    existing=persisted,
                    source_article_id=code,
                    title=str(raw_art.get("title") or persisted.get("title") or ""),
                    source_detail_url_normalized=persisted.get(
                        "source_detail_url_normalized"
                    ) or f"{source_parent_url.rstrip('/')}/{code}",
                    source_parent_url=source_parent_url,
                    source_published_at_ms=raw_art.get("releaseDate"),
                    detected_at_ms=now_ms,
                    first_detected_at_ms=now_ms,
                    raw=raw_art,
                    event_type="futures_contract_launch",
                    detail_work_type="launch_schedule_revision_detail",
                    source_published_at_ms_confidence="medium",
                    symbol_extraction_source="none",
                    pending_reason="revision_detail_required",
                    detail_fetch_status="pending",
                )


            # Clean up first_bar_queue to remove empty symbol events
            first_bar_queue = [
                q for q in cycle_res["first_bar_queue"]
                if q.get("symbols") or q.get("source_article_id") not in detail_retry_state
            ]

            # Detail fallback processing
            detail_budget_remaining = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL", 3)
            detail_http_requests_remaining = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL", 4)
            source_parent_url = "https://www.binance.com/en/support/announcement"
            bapi_article_code_pattern = getattr(
                base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_CODE_PATTERN", r"^[0-9a-fA-F]{32}$"
            )
            bapi_eligible_pending_exists = any(
                bool(code and re.match(bapi_article_code_pattern, str(code)))
                for code in detail_retry_state
            )

            bapi_degraded_active = is_detail_source_degraded(endpoint_health, "bapi_article_detail_query", now_ms)
            support_degraded_active = is_detail_source_degraded(endpoint_health, "support_article_detail", now_ms)
            endpoint_degraded_until_ms = (
                endpoint_health.get("detail_endpoint_degraded_until_ms", 0)
                if (
                    (bapi_eligible_pending_exists and bapi_degraded_active and support_degraded_active)
                    or (not bapi_eligible_pending_exists and support_degraded_active)
                )
                else 0
            )

            if now_ms < endpoint_degraded_until_ms:
                detail_endpoint_degraded_active = 1
                detail_endpoint_degraded_count += 1
            else:
                detail_endpoint_degraded_active = 0


            attempt_codes = select_detail_retry_attempts(
                detail_retry_state=detail_retry_state,
                now_ms=now_ms,
                detail_budget_per_poll=detail_budget_remaining,
                endpoint_degraded_until_ms=endpoint_degraded_until_ms,
                degraded_recent_article_window_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_ARTICLE_WINDOW_SEC * 1000,
                degraded_recent_retry_interval_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_INTERVAL_SEC * 1000,
                degraded_recent_retry_budget_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_BUDGET_PER_POLL,
                degraded_recent_retry_max_cycles=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_MAX_CYCLES,
                max_first_attempt_delay_polls=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS,
                max_first_attempt_delay_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS,
                overdue_attempted_retry_budget_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_RETRY_BUDGET_PER_POLL,
                overdue_attempted_min_interval_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_MIN_INTERVAL_SEC * 1000,
                min_never_attempted_slots_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL,
            )
            if now_ms < endpoint_degraded_until_ms:
                detail_degraded_recent_retry_count += sum(
                    1
                    for code in attempt_codes
                    if int(detail_retry_state.get(code, {}).get("detail_http_request_count") or 0) > 0
                    and int(detail_retry_state.get(code, {}).get("transient_detail_error_count") or 0) > 0
                )
            scheduler_diag = build_detail_retry_scheduler_diagnostic_row(
                detail_retry_state=detail_retry_state,
                attempt_codes=attempt_codes,
                now_ms=now_ms,
                endpoint_degraded_until_ms=endpoint_degraded_until_ms,
                detail_budget_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL,
                min_never_attempted_slots_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL,
                overdue_attempted_min_interval_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_MIN_INTERVAL_SEC * 1000,
            )
            if (
                scheduler_diag["detail_retry_overdue_selected_count"] > 0
                or scheduler_diag["detail_retry_overdue_deferred_count"] > 0
            ):
                append_jsonl(stream_paths["detail_retry_scheduler_diagnostics"], scheduler_diag, storage_guard=storage_guard)
                detail_retry_overdue_selected_total += scheduler_diag["detail_retry_overdue_selected_count"]
                detail_retry_overdue_deferred_total += scheduler_diag["detail_retry_overdue_deferred_count"]
                detail_retry_overdue_retry_cycle_total += scheduler_diag["detail_retry_overdue_selected_count"]

            # Pass 1: Expiry, validation, and scheduling checks
            to_fetch_codes = []
            for code in list(detail_retry_state.keys()):
                if code not in detail_retry_state:
                    continue
                state = detail_retry_state[code]
                if state.get("terminal_state"):
                    continue

                # 1. Check max-age expiry
                max_age_limit = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 3600)
                age_sec = (now_ms - state["first_detected_at_ms"]) / 1000.0
                has_candidate_symbols = bool(state.get("candidate_symbols"))
                has_transient_detail_errors = state.get("transient_detail_error_count", 0) > 0
                if has_candidate_symbols:
                    expire = should_expire_candidate_validation(state, now_ms)
                elif has_transient_detail_errors:
                    transient_max_age = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC", 86400)
                    expire = age_sec >= transient_max_age
                else:
                    expire = age_sec >= max_age_limit

                if expire:
                    if state.get("detail_fetch_attempt_count", 0) == 0:
                        detail_budget_starved_count += 1
                        detail_never_attempted_expired_count += 1
                        detail_terminal_failed_count += 1
                        fetch_status = "budget_starved"
                        failed_reason = "detail_never_attempted_budget_starved"
                        terminal_fail_type = "detail_never_attempted_budget_starved"
                    else:
                        if has_transient_detail_errors and not has_candidate_symbols:
                            detail_terminal_failed_count += 1
                            detail_transient_timeout_count += 1
                            fetch_status = "transient_detail_max_age_exceeded"
                            failed_reason = "transient_detail_max_age_exceeded"
                            terminal_fail_type = "detail_unavailable_timeout"
                        else:
                            symbol_empty_event_count += 1
                            symbol_parse_failed_count += 1
                            detail_symbol_parse_failed_count += 1
                            detail_terminal_failed_count += 1
                            fetch_status = "max_age_exceeded"
                            failed_reason = "detail_retry_max_age_exceeded"
                            terminal_fail_type = None

                    if has_candidate_symbols:
                        candidate_validation_expired_count += len(state["candidate_symbols"])

                    is_derived = state.get("candidate_symbols") is not None
                    norm_event = normalize_live_event(
                        raw=state["raw"],
                        source_parent_url=source_parent_url,
                        detected_at_ms=state["first_detected_at_ms"],
                        source_published_at_ms=state["raw"].get("releaseDate"),
                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                        symbols_override=tuple(state.get("candidate_symbols") or ()),
                        extraction_metadata={
                            "symbol_extraction_source": state.get("symbol_extraction_source", "none"),
                            "symbol_derivation_method": state.get("symbol_derivation_method", None),
                            "symbol_validation_status": "rejected" if is_derived else None,
                            "detail_fetch_attempted": state["retry_count"] > 0 or state.get("detail_fetch_attempt_count", 0) > 0,
                            "detail_fetch_status": fetch_status,
                            "symbol_parse_failed_reason": failed_reason,
                            "symbol_parse_status": "terminal_failed",
                        }
                    )
                    if terminal_fail_type:
                        norm_event["terminal_failure_type"] = terminal_fail_type
                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                    norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
                    norm_event["symbol_resolved_at_ms"] = now_ms
                    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]
                    norm_event["symbol_launch_times_ms"] = state.get("symbol_launch_times_ms", {})
                    norm_event["symbol_onboard_times_ms"] = state.get("symbol_onboard_times_ms", {})
                    norm_event["symbol_effective_launch_times_ms"] = state.get("symbol_effective_launch_times_ms", {})
                    norm_event["launch_time_source"] = state.get("launch_time_source")

                    event_id = norm_event["event_id"]
                    if terminal_fail_type == "detail_unavailable_timeout":
                        terminal_diag = dict(norm_event)
                        terminal_diag["consumable_by_stage1_5f"] = False
                        terminal_diag["diagnostic_stream"] = "detail_retry_terminal_diagnostics"
                        append_jsonl(stream_paths["detail_retry_terminal_diagnostics"], terminal_diag, storage_guard=storage_guard)
                    elif event_id not in seen_event_ids:
                        record_formal_futures_launch_event(
                            stream_paths=stream_paths,
                            row=norm_event,
                            seen_event_ids=seen_event_ids,
                            events_detected=events_detected,
                        )

                    state["terminal_state"] = True
                    state["terminal_reason"] = failed_reason
                    state["terminal_at_ms"] = now_ms
                    persisted_articles[code] = state
                    detail_retry_state.pop(code, None)
                    continue

                # 2. Check max retries exhausted or non-retryable hard failure
                max_retries_limit = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES", 3)
                is_non_retryable = (
                    state.get("detail_retryable") is False
                    and int(state.get("detail_fetch_attempt_count") or 0) > 0
                    and int(state.get("retry_count") or 0) > 0
                )
                if (
                    (state["retry_count"] >= max_retries_limit or is_non_retryable)
                    and not state.get("candidate_symbols")
                    and state.get("transient_detail_error_count", 0) == 0
                ):
                    symbol_empty_event_count += 1
                    symbol_parse_failed_count += 1
                    detail_symbol_parse_failed_count += 1
                    detail_terminal_failed_count += 1

                    norm_event = normalize_live_event(
                        raw=state["raw"],
                        source_parent_url=source_parent_url,
                        detected_at_ms=state["first_detected_at_ms"],
                        source_published_at_ms=state["raw"].get("releaseDate"),
                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                        symbols_override=(),
                        extraction_metadata={
                            "symbol_extraction_source": "none",
                            "detail_fetch_attempted": True,
                            "detail_fetch_status": "retry_exhausted",
                            "symbol_parse_failed_reason": "detail_retry_exhausted",
                            "symbol_parse_status": "terminal_failed",
                        }
                    )
                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                    norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
                    norm_event["symbol_resolved_at_ms"] = now_ms
                    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                    terminal_diag = dict(norm_event)
                    terminal_diag["consumable_by_stage1_5f"] = False
                    terminal_diag["diagnostic_stream"] = "detail_retry_terminal_diagnostics"
                    append_jsonl(stream_paths["detail_retry_terminal_diagnostics"], terminal_diag, storage_guard=storage_guard)

                    state["terminal_state"] = True
                    state["terminal_reason"] = "detail_retry_exhausted"
                    state["terminal_at_ms"] = now_ms
                    persisted_articles[code] = state
                    detail_retry_state.pop(code, None)
                    continue

                # 2.5 Check if we already have candidates pending validation
                if bool(state.get("candidate_symbols")) and not title_candidate_needs_detail_launch_anchor(state):
                    exchangeinfo_by_symbol, ex_ok = get_exchangeinfo_by_symbol()
                    if not ex_ok:
                        continue

                    validation_result = validate_candidate_symbols_against_exchangeinfo(
                        candidates=state["candidate_symbols"],
                        exchangeinfo_by_symbol=exchangeinfo_by_symbol,
                        allowed_margin_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS,
                        allowed_quote_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS,
                        allowed_contract_types=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES,
                        validatable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES,
                        emittable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_EMITTABLE_SYMBOL_STATUSES,
                        now_ms=now_ms,
                    )

                    # Update timings
                    state["symbol_onboard_times_ms"] = validation_result.get("symbol_onboard_times_ms", {})
                    effective_launch = build_effective_launch_times_ms(
                        candidate_symbols=state["candidate_symbols"],
                        symbol_onboard_times_ms=state["symbol_onboard_times_ms"],
                        symbol_launch_times_ms=state.get("symbol_launch_times_ms", {}),
                        source_published_at_ms=state.get("source_published_at_ms") or state["raw"].get("releaseDate") or 0,
                        first_detected_at_ms=state["first_detected_at_ms"],
                        allow_release_date_fallback=False,
                        allow_legacy_max_age_fallback=False,
                    )
                    state["symbol_effective_launch_times_ms"] = effective_launch["symbol_effective_launch_times_ms"]
                    state["launch_time_source"] = effective_launch["launch_time_source"]

                    should_emit, is_multi, symbols_override = check_article_emission_eligibility(
                        state, validation_result, effective_launch
                    )
                    if should_emit:
                        if state.get("detail_fetch_attempted", True):
                            detail_fetch_success_count += 1
                        detail_symbol_extracted_count += 1
                        candidate_validation_success_count += len(symbols_override)

                        for sym in symbols_override:
                            meta = validation_result["symbol_exchangeinfo"].get(sym, {})
                            if meta.get("quoteAsset") == "U" or meta.get("marginAsset") == "U":
                                u_settlement_symbol_extracted_count += 1

                        identity = build_candidate_symbol_set_identity(symbols_override)
                        c_hash = identity["candidate_symbol_set_hash"]
                        em_id = build_multi_symbol_emission_id(code, state.get("event_type", "futures_contract_launch"), c_hash)

                        norm_event = normalize_live_event(
                            raw=state["raw"],
                            source_parent_url=source_parent_url,
                            detected_at_ms=state["first_detected_at_ms"],
                            source_published_at_ms=state["raw"].get("releaseDate"),
                            source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                            symbols_override=symbols_override,
                            extraction_metadata={
                                "symbol_extraction_source": state["symbol_extraction_source"],
                                "symbol_derivation_method": state["symbol_derivation_method"],
                                "quote_derivation_source": "exchange_info",
                                "symbol_validation_status": "validated_candidate_set" if is_multi else "validated",
                                "detail_fetch_attempted": state.get("detail_fetch_attempted", True),
                                "detail_fetch_status": state.get("detail_fetch_status", "success"),
                                "symbol_parse_failed_reason": None,
                                "symbol_parse_status": "parsed",
                                "detail_fetch_variant": state.get("detail_fetch_variant"),
                                "detail_fetch_url_used": state.get("detail_fetch_url_used"),
                                "detail_payload_hash": state.get("detail_payload_hash"),
                                "detail_payload_trusted": state.get("detail_payload_trusted"),
                            }
                        )
                        norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                        norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
                        norm_event["symbol_resolved_at_ms"] = now_ms
                        norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]
                        norm_event["symbol_launch_times_ms"] = state.get("symbol_launch_times_ms", {})
                        norm_event["symbol_onboard_times_ms"] = state.get("symbol_onboard_times_ms", {})
                        norm_event["symbol_effective_launch_times_ms"] = state.get("symbol_effective_launch_times_ms", {})
                        norm_event["launch_time_source"] = state.get("launch_time_source")

                        apply_formal_launch_event_contract(
                            norm_event,
                            state,
                            validation_result,
                            symbols_override,
                            effective_launch,
                        )

                        if is_multi:
                            apply_multi_symbol_candidate_set_contract(
                                norm_event,
                                state,
                                validation_result,
                                symbols_override,
                                identity,
                                em_id,
                                effective_launch,
                                now_ms,
                            )

                        event_id = norm_event["event_id"]

                        if event_id not in seen_event_ids:
                            written_event = record_formal_futures_launch_event(
                                stream_paths=stream_paths,
                                row=norm_event,
                                seen_event_ids=seen_event_ids,
                                events_detected=events_detected,
                            )

                            # Add to first_bar_queue
                            if written_event is not None:
                                eq_item = dict(written_event)
                                eq_item["first_futures_bar_status"] = "not_yet_available"
                                eq_item["first_futures_bar_start_ms"] = None
                                first_bar_queue.append(eq_item)

                        if is_multi:
                            state["event_id"] = event_id
                        else:
                            detail_retry_state.pop(code, None)
                    else:
                        if is_multi and (validation_result.get("pending_symbols") or len(state.get("candidate_symbols", [])) == 0):
                            state["symbol_validation_status"] = "pending_candidate_set_readiness"
                            state["pending_reason"] = "multi_symbol_candidate_set_not_ready" if validation_result.get("pending_symbols") else "multi_symbol_candidate_symbols_empty"
                            state["exchangeinfo_visible_symbols"] = list(validation_result.get("symbol_exchangeinfo", {}).keys())
                            state["exchangeinfo_missing_symbols"] = [s for s in state.get("candidate_symbols", []) if s not in validation_result.get("symbol_exchangeinfo", {})]
                            state["hard_rejected_symbols"] = list(validation_result.get("rejected_symbols", []))
                            state["symbol_exchangeinfo_statuses"] = {s: meta.get("status") for s, meta in validation_result.get("symbol_exchangeinfo", {}).items()}
                        elif validation_result["pending_symbols"]:
                            is_prelaunch = any(
                                reason == "exchange_info_symbol_status_not_trading_prelaunch"
                                  for reason in validation_result["pending_reasons"].values()
                            )
                            if is_prelaunch:
                                state["symbol_validation_status"] = "pending_pre_trading"
                                pre_launch_validation_deferred_count += len(validation_result["pending_symbols"])
                            else:
                                state["symbol_validation_status"] = "pending_exchangeinfo_missing"
                                candidate_validation_pending_count += len(validation_result["pending_symbols"])
                        elif not state.get("candidate_symbols") and (not state.get("detail_fetch_attempted", False) or state.get("status") == "pending_detail_retry"):
                            state["status"] = "pending_detail_retry"
                            state["symbol_validation_status"] = "pending_detail_retry"
                            state["pending_reason"] = state.get("pending_reason") or "title_symbol_missing"
                            detail_retry_state[code] = state
                        else:
                            state["symbol_validation_status"] = "rejected"
                            reason = next(
                                iter(validation_result.get("rejection_reasons", {}).values()),
                                "exchange_info_candidate_rejected",
                            )
                            symbol_empty_event_count += 1
                            symbol_parse_failed_count += 1
                            detail_symbol_parse_failed_count += 1
                            if state.get("detail_fetch_attempted", True):
                                detail_fetch_success_count += 1

                            norm_event = build_candidate_terminal_event(
                                state=state,
                                source_parent_url=source_parent_url,
                                now_ms=now_ms,
                                reason=reason,
                                detail_fetch_status=state.get("detail_fetch_status", "success"),
                                symbol_validation_status="rejected",
                            )
                            norm_event["terminal_failure_type"] = "candidate_validation_rejected"
                            event_id = norm_event["event_id"]
                            if event_id not in seen_event_ids:
                                record_formal_futures_launch_event(
                                    stream_paths=stream_paths,
                                    row=norm_event,
                                    seen_event_ids=seen_event_ids,
                                    events_detected=events_detected,
                                )
                            state["terminal_state"] = True
                            state["terminal_reason"] = "candidate_validation_rejected"
                            state["terminal_at_ms"] = now_ms
                            state["symbol_validation_status"] = "rejected"
                    continue

                # 3. Check if this code is allowed to fetch in this poll (scheduling check)
                if code not in attempt_codes:
                    if state.get("detail_fetch_attempt_count", 0) == 0:
                        defer_classification = classify_never_attempted_defer_state(
                            detail_fetch_attempt_count=0,
                            first_detected_at_ms=state["first_detected_at_ms"],
                            now_ms=now_ms,
                            never_attempted_max_defer_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_NEVER_ATTEMPTED_MAX_DEFER_SEC,
                            detail_fetch_max_age_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC,
                            defer_count=state.get("defer_count", 0),
                            max_first_attempt_delay_polls=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS,
                            max_first_attempt_delay_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS,
                        )
                        if defer_classification["classification"] == "detail_first_attempt_sla_breach":
                            detail_first_attempt_sla_breach_count += 1
                            if not state.get("first_deferred_at_ms"):
                                state["first_deferred_at_ms"] = now_ms
                            state["last_deferred_at_ms"] = now_ms
                            state["defer_count"] = state.get("defer_count", 0) + 1

                            deferred_manifest_min_interval_sec = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEFERRED_MANIFEST_MIN_INTERVAL_SEC", 15 * 60)
                            last_deferred_manifest_at_ms = state.get("last_deferred_manifest_at_ms", 0)
                            if (now_ms - last_deferred_manifest_at_ms) >= deferred_manifest_min_interval_sec * 1000:
                                state["last_deferred_manifest_at_ms"] = now_ms
                                deferred_manifest = {
                                    "request_id": f"detail_deferred_{now_ms}_{code}",
                                    "request_type": "announcement_detail_deferred",
                                    "audit_metadata_version": base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION,
                                    "source_type": "announcement_detail_deferred",
                                    "symbol": "ALL",
                                    "url": state["source_detail_url_normalized"],
                                    "final_url": state["source_detail_url_normalized"],
                                    "http_status": None,
                                    "row_count": 0,
                                    "error": "detail_budget_exhausted",
                                    "fetched_at_ms": now_ms,
                                    "payload_sha256": None,
                                    "payload_size_bytes": 0,
                                    "payload_path": None,
                                    "parser_version": PARSER_VERSION,
                                    "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                                }
                                append_jsonl(stream_paths["request_manifest"], deferred_manifest, storage_guard=storage_guard)
                                request_manifest.append(deferred_manifest)
                        else:
                            if not state.get("first_deferred_at_ms"):
                                state["first_deferred_at_ms"] = now_ms
                            state["last_deferred_at_ms"] = now_ms
                            state["defer_count"] = state.get("defer_count", 0) + 1

                        detail_fetch_budget_deferred_count += 1
                        detail_scheduler_pending_count += 1
                    else:
                        detail_scheduler_backoff_count += 1

                    continue

                to_fetch_codes.append(code)

            # Sort to_fetch_codes to match prioritized order in attempt_codes
            to_fetch_codes.sort(key=lambda c: attempt_codes.index(c))

            # Pre-HTTP durable reservation: reserve logical cycle for all selected attempts
            if to_fetch_codes:
                for code in to_fetch_codes:
                    if code in detail_retry_state:
                        st = detail_retry_state[code]
                        cycle = int(st.get("detail_retry_cycle_count") or 0) + 1
                        st["detail_retry_cycle_count"] = cycle
                        st["last_retry_at_ms"] = now_ms
                        target = {
                            "endpoint_kind": "bapi_article_detail_query",
                            "source_article_id": code,
                            "detail_fetch_variant": "bapi_article_detail_query",
                            "requested_url": f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode={code}",
                        }
                        ident_payload = {
                            "cycle": cycle,
                            "operation": "detail_request",
                            "request_ordinal": 1,
                            "request_target": target,
                            "source_article_id": code,
                            "symbol": None,
                        }
                        req_ident = hashlib.sha256(_canonical_json_bytes(ident_payload)).hexdigest()
                        st["inflight_cycle"] = {
                            "operation": "detail_request",
                            "cycle": cycle,
                            "request_ordinal": 1,
                            "reserved_at_ms": now_ms,
                            "symbol": None,
                            "request_target": target,
                            "request_identity": req_ident,
                        }
                        persisted_articles[code] = st
                scheduler_state["articles"] = serialize_stage1_5d_v3_articles(persisted_articles)
                scheduler_state["endpoint_health"] = endpoint_health
                write_detail_retry_scheduler_state(
                    output_root,
                    scheduler_state,
                    metadata_version=3,
                    storage_guard=storage_guard,
                )

            # Pass 2: Perform fetches in the priority order of attempt_codes!
            for code in to_fetch_codes:
                if code not in detail_retry_state:
                    continue
                state = detail_retry_state[code]

                # 4. Attempt fetch
                detail_budget_remaining -= 1
                state["inflight_cycle"] = None
                detail_fetch_attempted_count += 1

                detail_url = f"{source_parent_url.rstrip('/')}/{code}"

                # URL validation (Requested URL)
                try:
                    if not code:
                        raise ValueError("detail_url_missing")
                    validate_announcement_detail_url(detail_url)
                except ValueError as e:
                    detail_fetch_url_rejected_count += 1
                    symbol_empty_event_count += 1
                    symbol_parse_failed_count += 1
                    detail_symbol_parse_failed_count += 1

                    norm_event = normalize_live_event(
                        raw=state["raw"],
                        source_parent_url=source_parent_url,
                        detected_at_ms=state["first_detected_at_ms"],
                        source_published_at_ms=state["raw"].get("releaseDate"),
                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                        symbols_override=(),
                        extraction_metadata={
                            "symbol_extraction_source": "none",
                            "detail_fetch_attempted": False,
                            "detail_fetch_status": "url_missing" if str(e) == "detail_url_missing" else "url_not_allowlisted",
                            "symbol_parse_failed_reason": "detail_url_rejected",
                            "symbol_parse_status": "terminal_failed",
                        }
                    )
                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                    norm_event["detail_fetched_at_ms"] = None
                    norm_event["symbol_resolved_at_ms"] = now_ms
                    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                    event_id = norm_event["event_id"]
                    if event_id not in seen_event_ids:
                        record_formal_futures_launch_event(
                            stream_paths=stream_paths,
                            row=norm_event,
                            seen_event_ids=seen_event_ids,
                            events_detected=events_detected,
                        )
                    detail_retry_state.pop(code, None)
                    continue

                # Perform fetch
                bapi_degraded = is_detail_source_degraded(endpoint_health, "bapi_article_detail_query", now_ms)
                bapi_recheck_interval_ms = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_NO_SYMBOL_RECHECK_INTERVAL_SEC", 3600) * 1000
                is_bapi_no_symbol_deduped = (
                    state.get("last_bapi_payload_hash") is not None
                    and state.get("last_bapi_parser_version") == PARSER_VERSION
                    and state.get("last_bapi_parser_status") == "no_symbols"
                    and (now_ms - int(state.get("last_bapi_parse_attempt_at_ms") or 0) < bapi_recheck_interval_ms)
                )
                bapi_handled = False
                pattern = bapi_article_code_pattern

                if not bapi_degraded and not is_bapi_no_symbol_deduped and detail_http_requests_remaining > 0 and code and re.match(pattern, code):
                    bapi_url = build_bapi_article_detail_url(code)

                    bapi_res = None
                    if args.fixture_json:
                        bapi_payload = state["raw"].get("bapiPayload")
                        if bapi_payload is not None:
                            payload_obj = bapi_payload if isinstance(bapi_payload, dict) else json.loads(bapi_payload)
                            raw_b_data = json.dumps(bapi_payload).encode("utf-8") if isinstance(bapi_payload, dict) else bapi_payload.encode("utf-8")
                            bapi_res = {
                                "ok": True,
                                "payload": payload_obj,
                                "raw_bytes": raw_b_data,
                                "final_url": bapi_url,
                                "http_status": 200,
                                "error": None,
                            }
                        else:
                            bapi_res = {
                                "ok": False,
                                "payload": None,
                                "raw_bytes": b"",
                                "final_url": bapi_url,
                                "http_status": None,
                                "error": "fixture_missing",
                            }
                    else:
                        try:
                            bapi_res = fetch_public_bapi_article_detail(
                                code,
                                live_public_readonly=args.live_public_readonly,
                                timeout_sec=getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_REQUEST_TIMEOUT_SEC", 10.0),
                                retry_budget=0,
                            )
                        except Exception as e:
                            bapi_res = {
                                "ok": False,
                                "payload": None,
                                "raw_bytes": b"",
                                "final_url": bapi_url,
                                "http_status": None,
                                "error": str(e),
                            }

                    detail_http_requests_remaining -= 1
                    bapi_detail_request_count += 1
                    state["detail_http_request_count"] = state.get("detail_http_request_count", 0) + 1
                    state["detail_fetch_attempt_count"] = state["detail_http_request_count"]

                    bapi_trusted_info = None
                    if bapi_res["ok"] and bapi_res.get("payload"):
                        bapi_trusted_info = validate_bapi_article_detail_payload(
                            bapi_res["payload"],
                            requested_article_code=code,
                            catalog_title=state["raw"].get("title"),
                        )

                    bapi_is_trusted = bool(bapi_trusted_info and bapi_trusted_info.get("payload_trusted"))

                    bapi_raw_bytes = bapi_res.get("raw_bytes") or (
                        json.dumps(bapi_res["payload"]).encode("utf-8") if bapi_res.get("payload") else b""
                    )
                    bapi_write_res = write_detail_payload_append_only(
                        root=output_root,
                        timestamp_ms=now_ms,
                        source_article_id=code,
                        detail_fetch_variant="bapi_article_detail_query",
                        raw_bytes=bapi_raw_bytes,
                        parsed_payload=bapi_res.get("payload"),
                        http_status=bapi_res.get("http_status"),
                        storage_guard=stream_paths["storage_guard"],
                    )

                    bapi_manifest = {
                        "request_id": f"detail_bapi_{now_ms}_{code}",
                        "request_type": "announcement_detail",
                        "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 2),
                        "source_article_id": code,
                        "source_detail_url_normalized": state["source_detail_url_normalized"],
                        "source_type": "announcement_detail",
                        "symbol": "ALL",
                        "url": bapi_url,
                        "final_url": bapi_res.get("final_url") or bapi_url,
                        "http_status": bapi_res.get("http_status"),
                        "row_count": 0,
                        "error": bapi_res.get("error") if not bapi_is_trusted else None,

                        "fetched_at_ms": now_ms,
                        "payload_sha256": bapi_write_res.get("raw_payload_sha256"),
                        "payload_size_bytes": bapi_write_res.get("payload_size_bytes") or 0,
                        "payload_path": bapi_write_res.get("payload_path"),
                        "payload_trusted": bapi_is_trusted,
                        "response_payload_size_bytes": bapi_res.get("payload_size_bytes") or 0,
                        "detail_fetch_variant": "bapi_article_detail_query",
                        "source_transport": "binance_first_party_public_web_bapi_undocumented",
                        "content_provenance": "binance_official_announcement",
                        "parser_version": PARSER_VERSION,
                        "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                    }
                    append_jsonl(stream_paths["request_manifest"], bapi_manifest, storage_guard=storage_guard)
                    request_manifest.append(bapi_manifest)

                    bapi_attempt_result = classify_detail_attempt_result(bapi_res) if not bapi_is_trusted else "success"
                    endpoint_health = update_detail_endpoint_health_by_source(
                        endpoint_health,
                        now_ms=now_ms,
                        source="bapi_article_detail_query",
                        result_code=bapi_attempt_result,
                        degraded_rate_threshold=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD,
                        degraded_min_sample=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE,
                        degraded_backoff_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC,
                    )

                    state["last_bapi_detail_status"] = "success" if bapi_is_trusted else "failure"
                    state["last_bapi_payload_hash"] = bapi_write_res.get("raw_payload_sha256")
                    state["last_bapi_parser_version"] = PARSER_VERSION
                    state["last_bapi_parse_attempt_at_ms"] = now_ms

                    if bapi_is_trusted:
                        bapi_detail_success_count += 1
                        bapi_detail_trusted_payload_count += 1
                        payload_version_available_at_ms = record_payload_version_first_observed(
                            stream_paths["revision_payload_versions"],
                            source_article_id=code,
                            payload_sha256=str(bapi_write_res.get("raw_payload_sha256") or ""),
                            # Each request needs its own arrival time. A poll-wide
                            # timestamp can predate a launch made durable earlier
                            # in the same poll.
                            observed_at_ms=int(time.time() * 1000),
                            registry=payload_version_first_observed,
                            storage_guard=storage_guard,
                        )

                        max_symbols = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS", 30)
                        bapi_extraction = extract_symbol_candidates_from_bapi_article_payload(
                            bapi_res["payload"], max_symbols=max_symbols, title=state["raw"].get("title")
                        )

                        bapi_parsed_symbols = bapi_extraction.get("symbols") or []
                        state["last_bapi_parser_status"] = bapi_extraction.get("parser_status", "no_symbols" if not bapi_parsed_symbols else "parsed")
                        state["last_bapi_parser_failure_reason"] = bapi_extraction.get("symbol_parse_failed_reason")
                        state["parsed_candidate_symbols"] = bapi_parsed_symbols
                        state["candidate_provenance"] = bapi_extraction.get("candidate_provenance")
                        state["launch_time_resolution_status"] = bapi_extraction.get("launch_time_resolution_status")
                        state["consumable_event_allowed"] = bapi_extraction.get("consumable_event_allowed")

                        bapi_parse_audit_row = {
                            "request_id": bapi_manifest["request_id"],
                            "source_article_id": code,
                            "payload_sha256": bapi_write_res.get("raw_payload_sha256"),
                            "parser_version": PARSER_VERSION,
                            "launch_schedule_parser_version": bapi_extraction.get("launch_schedule_parser_version", LAUNCH_SCHEDULE_PARSER_VERSION),
                            "parser_status": bapi_extraction.get("parser_status", "no_symbols" if not bapi_parsed_symbols else "parsed"),
                            "parser_failure_reason": bapi_extraction.get("symbol_parse_failed_reason"),
                            "symbol_count": len(bapi_parsed_symbols),
                            "launch_time_count": len(bapi_extraction.get("symbol_launch_times_ms") or {}),
                            "fallback_reason": "bapi_trusted_parser_no_match" if not bapi_parsed_symbols else None,
                            "candidate_provenance": bapi_extraction.get("candidate_provenance") or [],
                            "parsed_at_ms": now_ms,
                        }
                        append_jsonl(stream_paths["bapi_parse_results"], bapi_parse_audit_row, storage_guard=storage_guard)

                        revision_result = process_trusted_schedule_revision_detail(
                            stream_paths=stream_paths,
                            source_article_id=code,
                            title=state["raw"].get("title") or "",
                            detail_text=str(bapi_extraction.get("extracted_text") or ""),
                            symbols=bapi_parsed_symbols,
                            symbol_launch_times_ms=bapi_extraction.get("symbol_launch_times_ms"),
                            payload_sha256=str(bapi_write_res.get("raw_payload_sha256") or ""),
                            available_at_ms=payload_version_available_at_ms,
                            producer_effective_enabled=schedule_revision_producer_effective_enabled,
                            formal_launch_identity_index_snapshot=args.formal_launch_identity_index_snapshot,
                            emitted_revision_semantic_ids=emitted_revision_semantic_ids,
                        )
                        state["schedule_revision_producer_status"] = revision_result["status"]
                        if revision_result["status"] == "revision_emitted":
                            schedule_revision_emitted_count += revision_result["emitted_count"]
                        elif revision_result["status"] == "revision_diagnostic":
                            schedule_revision_diagnostic_count += 1
                            if revision_result.get("producer_health") == "blocked_index_collision":
                                schedule_revision_index_collision_count += 1
                                schedule_revision_integration_health = "blocked_index_collision"

                        if state.get("detail_work_type") == "launch_schedule_revision_detail":
                            state["detail_fetch_status"] = "success"
                            state["detail_retryable"] = False
                            detail_retry_state.pop(code, None)
                            continue

                        if bapi_parsed_symbols:
                            bapi_symbol_parse_success_count += 1
                            state["candidate_symbols"] = bapi_parsed_symbols
                            exchangeinfo_by_symbol, ex_ok = get_exchangeinfo_by_symbol()
                            validation_res = {}
                            if ex_ok:
                                validation_res = validate_candidate_symbols_against_exchangeinfo(
                                    candidates=bapi_parsed_symbols,
                                    exchangeinfo_by_symbol=exchangeinfo_by_symbol,
                                    allowed_margin_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS,
                                    allowed_quote_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS,
                                    allowed_contract_types=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES,
                                    validatable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES,
                                    emittable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_EMITTABLE_SYMBOL_STATUSES,
                                    now_ms=now_ms,
                                )
                            state["symbol_onboard_times_ms"] = validation_res.get("symbol_onboard_times_ms", {})
                            state["symbol_launch_times_ms"] = bapi_extraction.get("symbol_launch_times_ms", {})
                            effective_launch = build_effective_launch_times_ms(
                                candidate_symbols=bapi_parsed_symbols,
                                symbol_onboard_times_ms=state.get("symbol_onboard_times_ms", {}),
                                symbol_launch_times_ms=state.get("symbol_launch_times_ms", {}),
                                source_published_at_ms=state["raw"].get("releaseDate") or 0,
                                first_detected_at_ms=state["first_detected_at_ms"],
                                allow_release_date_fallback=False,
                                allow_legacy_max_age_fallback=False,
                            )
                            state["symbol_effective_launch_times_ms"] = effective_launch.get("symbol_effective_launch_times_ms", {})
                            state["launch_time_source"] = effective_launch.get("launch_time_source")
                            should_emit, is_multi, symbols_override = check_article_emission_eligibility(
                                state,
                                validation_res,
                                effective_launch,
                                bapi_extraction,
                            )

                            if should_emit:
                                bapi_symbol_validation_success_count += 1
                                bapi_handled = True
                                symbol_validation_status = "validated_candidate_set" if is_multi else "validated_by_exchangeinfo"
                                norm_event = normalize_live_event(
                                    raw=state["raw"],
                                    source_parent_url=source_parent_url,
                                    detected_at_ms=state["first_detected_at_ms"],
                                    source_published_at_ms=state["raw"].get("releaseDate"),
                                    source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                    symbols_override=tuple(symbols_override),
                                    extraction_metadata={
                                        "evidence_source": "official_article_body_confirmed",
                                        "detail_transport": "bapi_article_detail_query",
                                        "symbol_extraction_source": "bapi_article_body",
                                        "content_provenance": "binance_official_announcement",
                                        "source_transport": "binance_first_party_public_web_bapi_undocumented",
                                        "detail_fetch_attempted": True,
                                        "detail_fetch_status": "success",
                                        "detail_fetch_variant": "bapi_article_detail_query",
                                        "detail_payload_trusted": True,
                                        "symbol_validation_status": symbol_validation_status,
                                    },
                                )
                                norm_event["symbol_launch_times_ms"] = state.get("symbol_launch_times_ms", {})
                                norm_event["symbol_onboard_times_ms"] = state.get("symbol_onboard_times_ms", {})
                                norm_event["symbol_effective_launch_times_ms"] = effective_launch.get("symbol_effective_launch_times_ms", {})
                                norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                                norm_event["detail_fetched_at_ms"] = now_ms
                                norm_event["symbol_resolved_at_ms"] = now_ms
                                norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                                apply_formal_launch_event_contract(
                                    norm_event,
                                    state,
                                    validation_res,
                                    symbols_override,
                                    effective_launch,
                                )

                                if is_multi:
                                    identity = build_candidate_symbol_set_identity(symbols_override)
                                    c_hash = identity["candidate_symbol_set_hash"]
                                    em_id = build_multi_symbol_emission_id(code, state.get("event_type", "futures_contract_launch"), c_hash)
                                    apply_multi_symbol_candidate_set_contract(
                                        norm_event,
                                        state,
                                        validation_res,
                                        symbols_override,
                                        identity,
                                        em_id,
                                        effective_launch,
                                        now_ms,
                                    )

                                event_id = norm_event["event_id"]
                                if event_id not in seen_event_ids:
                                    written_event = record_formal_futures_launch_event(
                                        stream_paths=stream_paths,
                                        row=norm_event,
                                        seen_event_ids=seen_event_ids,
                                        events_detected=events_detected,
                                    )

                                    if written_event is not None:
                                        eq_item = dict(written_event)
                                        eq_item["first_futures_bar_status"] = "not_yet_available"
                                        eq_item["first_futures_bar_start_ms"] = None
                                        first_bar_queue.append(eq_item)

                                if is_multi:
                                    state["event_id"] = event_id
                                else:
                                    detail_retry_state.pop(code, None)
                                continue
                            else:
                                bapi_symbol_validation_pending_count += 1
                                bapi_handled = True
                                state["candidate_symbols"] = bapi_parsed_symbols
                                state["detail_parse_status"] = "parsed"
                                state["parsed_candidate_symbols"] = bapi_parsed_symbols
                                pending_status = apply_pending_candidate_validation_state(state, validation_res)
                                if pending_status == "pending_pre_trading":
                                    pre_launch_validation_deferred_count += len(validation_res.get("pending_symbols") or [])
                                else:
                                    candidate_validation_pending_count += len(validation_res.get("pending_symbols") or [])
                                state["detail_fetch_status"] = "success"
                                state["detail_retryable"] = False
                                state["exchangeinfo_validation_retryable"] = True
                                state["next_exchangeinfo_validation_at_ms"] = now_ms + getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_RETRY_INTERVAL_SEC", 60) * 1000
                                state["last_exchangeinfo_validation_at_ms"] = now_ms
                                state["exchangeinfo_validation_attempt_count"] = state.get("exchangeinfo_validation_attempt_count", 0) + 1
                                state["symbol_launch_times_ms"] = bapi_extraction.get("symbol_launch_times_ms", {})
                                state["symbol_extraction_source"] = "bapi_article_body"
                                state["symbol_derivation_method"] = "none"
                                state["detail_fetch_variant"] = "bapi_article_detail_query"
                                state["detail_payload_trusted"] = True
                                continue
                    else:
                        bapi_to_support_fallback_count += 1

                if bapi_handled:
                    continue

                fallback_urls = build_announcement_detail_fallback_urls(detail_url)

                max_urls_cap = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FALLBACK_MAX_URLS_PER_ARTICLE", 2)
                fallback_urls = fallback_urls[:max_urls_cap]

                final_fetch_res = None
                chosen_url_idx = -1
                chosen_url = None
                chosen_extraction_res = None
                chosen_payload_sha256 = None
                is_trusted = False
                immediate_terminal_failed = False

                for url_idx, active_url in enumerate(fallback_urls):
                    if detail_http_requests_remaining <= 0:
                        detail_fetch_budget_deferred_count += 1
                        state["detail_budget_deferred_count"] = state.get("detail_budget_deferred_count", 0) + 1
                        break

                    detail_http_requests_remaining -= 1

                    if url_idx > 0:
                        detail_fetch_fallback_attempt_count += 1


                    state["detail_http_request_count"] = state.get("detail_http_request_count", 0) + 1
                    state["detail_fetch_attempt_count"] = state["detail_http_request_count"]

                    variant_name = "primary" if url_idx == 0 else "detail_path_fallback"

                    current_res = None
                    if args.fixture_json:
                        detail_payload = state["raw"].get("detailPayload")
                        if detail_payload is not None:
                            current_res = {
                                "ok": True,
                                "payload": detail_payload,
                                "final_url": active_url,
                                "http_status": 200,
                                "error": None,
                            }
                        else:
                            current_res = {
                                "ok": False,
                                "payload": None,
                                "final_url": active_url,
                                "http_status": None,
                                "error": "fixture_missing",
                            }
                    else:
                        try:
                            current_res = fetch_public_payload(
                                active_url,
                                live_public_readonly=args.live_public_readonly,
                                timeout_sec=getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_REQUEST_TIMEOUT_SEC", 10.0),
                                retry_budget=0
                            )
                        except Exception as e:
                            current_res = {
                                "ok": False,
                                "payload": None,
                                "final_url": active_url,
                                "http_status": None,
                                "error": str(e),
                            }

                    # Validate final URL host
                    is_url_valid = True
                    if current_res["ok"]:
                        try:
                            validate_announcement_detail_url(current_res["final_url"])
                        except ValueError:
                            # Immediate terminal failure for URL validation rejection
                            detail_fetch_url_rejected_count += 1
                            symbol_empty_event_count += 1
                            symbol_parse_failed_count += 1
                            detail_symbol_parse_failed_count += 1

                            norm_event = normalize_live_event(
                                raw=state["raw"],
                                source_parent_url=source_parent_url,
                                detected_at_ms=state["first_detected_at_ms"],
                                source_published_at_ms=state["raw"].get("releaseDate"),
                                source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                symbols_override=(),
                                extraction_metadata={
                                    "symbol_extraction_source": "none",
                                    "detail_fetch_attempted": True,
                                    "detail_fetch_status": "final_url_not_allowlisted",
                                    "symbol_parse_failed_reason": "final_url_rejected",
                                    "symbol_parse_status": "terminal_failed",
                                    "detail_fetch_variant": variant_name,
                                }
                            )
                            norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                            norm_event["detail_fetched_at_ms"] = now_ms
                            norm_event["symbol_resolved_at_ms"] = now_ms
                            norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                            event_id = norm_event["event_id"]
                            if event_id not in seen_event_ids:
                                record_formal_futures_launch_event(
                                    stream_paths=stream_paths,
                                    row=norm_event,
                                    seen_event_ids=seen_event_ids,
                                    events_detected=events_detected,
                                )

                            # Append manifest row
                            detail_manifest = {
                                "request_id": f"detail_{now_ms}_{code}_{url_idx}",
                                "request_type": "announcement_detail",
                                "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                                "source_article_id": code,
                                "source_detail_url_normalized": state["source_detail_url_normalized"],
                                "source_type": "announcement_detail" if not args.fixture_json else "fixture_detail",
                                "symbol": "ALL",
                                "url": active_url,
                                "final_url": current_res["final_url"],
                                "http_status": current_res.get("http_status"),
                                "row_count": 0,
                                "error": "final_url_rejected",
                                "fetched_at_ms": now_ms,
                                "payload_sha256": None,
                                "payload_size_bytes": 0,
                                "payload_path": None,
                                "payload_trusted": False,
                                "response_payload_size_bytes": current_res.get("payload_size_bytes") or 0,
                                "detail_fetch_variant": variant_name,
                                "parser_version": PARSER_VERSION,
                                "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                            }
                            append_jsonl(stream_paths["request_manifest"], detail_manifest, storage_guard=storage_guard)
                            request_manifest.append(detail_manifest)

                            detail_retry_state.pop(code, None)
                            is_url_valid = False
                            immediate_terminal_failed = True
                            break

                    is_trusted = False
                    current_extraction_res = None
                    payload_sha256 = None
                    payload_size_bytes = 0
                    payload_path = None

                    if current_res["ok"] and is_url_valid:
                        write_res = write_detail_payload(
                            output_root,
                            now_ms,
                            code,
                            current_res["payload"],
                            storage_guard=storage_guard,
                        )
                        payload_sha256 = write_res["payload_sha256"]
                        payload_size_bytes = write_res["payload_size_bytes"]
                        payload_path = write_res["payload_path"]

                        max_symbols = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS", 30)
                        title_context = state["raw"].get("title")
                        current_extraction_res = extract_symbol_candidates_from_detail_payload(
                            current_res["payload"], max_symbols, title=title_context
                        )

                        is_trusted = bool(current_extraction_res and current_extraction_res.get("symbols"))
                        if not is_trusted:
                            current_res = dict(current_res)
                            current_res["error"] = "empty_detail_payload"

                    detail_manifest = {
                        "request_id": f"detail_{now_ms}_{code}_{url_idx}",
                        "request_type": "announcement_detail",
                        "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                        "source_article_id": code,
                        "source_detail_url_normalized": state["source_detail_url_normalized"],
                        "source_type": "announcement_detail" if not args.fixture_json else "fixture_detail",
                        "symbol": "ALL",
                        "url": active_url,
                        "final_url": current_res.get("final_url") or active_url,
                        "http_status": current_res.get("http_status"),
                        "row_count": 0,
                        "error": current_res.get("error"),
                        "fetched_at_ms": now_ms,
                        "payload_sha256": payload_sha256,
                        "payload_size_bytes": payload_size_bytes,
                        "payload_path": payload_path,
                        "payload_trusted": is_trusted,
                        "response_payload_size_bytes": current_res.get("payload_size_bytes") or 0,
                        "detail_fetch_variant": variant_name,
                        "parser_version": PARSER_VERSION,
                        "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                    }
                    append_jsonl(stream_paths["request_manifest"], detail_manifest, storage_guard=storage_guard)
                    request_manifest.append(detail_manifest)

                    # Update health based on this request
                    attempt_result = classify_detail_attempt_result(current_res)
                    endpoint_health = update_detail_endpoint_health(
                        endpoint_health,
                        now_ms=now_ms,
                        result_code=attempt_result,
                        degraded_rate_threshold=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD,
                        degraded_min_sample=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE,
                        degraded_backoff_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC,
                    )

                    # Update variant health
                    endpoint_health = update_detail_endpoint_health_by_variant(
                        endpoint_health,
                        now_ms=now_ms,
                        variant=variant_name,
                        result_code=attempt_result,
                        degraded_rate_threshold=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD,
                        degraded_min_sample=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE,
                        degraded_backoff_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC,
                    )
                    endpoint_health = update_detail_endpoint_health_by_source(
                        endpoint_health,
                        now_ms=now_ms,
                        source="support_article_detail",
                        result_code=attempt_result,
                        degraded_rate_threshold=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD,
                        degraded_min_sample=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE,
                        degraded_backoff_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC,
                    )

                    if current_res["ok"] and is_url_valid and is_trusted:
                        final_fetch_res = current_res
                        chosen_url_idx = url_idx
                        chosen_url = active_url
                        chosen_extraction_res = current_extraction_res
                        chosen_payload_sha256 = payload_sha256
                        if url_idx > 0:
                            detail_fetch_fallback_success_count += 1
                        break

                    if url_idx == 0:
                        is_allowed = False
                        if attempt_result == "http_202_empty" or current_res.get("error") == "empty_detail_payload":
                            is_allowed = True
                        if not is_allowed:
                            final_fetch_res = current_res
                            break

                    final_fetch_res = current_res

                if immediate_terminal_failed:
                    continue

                # Post-fetch handling
                if final_fetch_res and final_fetch_res.get("ok") and (chosen_url_idx == 0 or (chosen_extraction_res and chosen_extraction_res.get("symbols"))):
                    detail_fetch_success_count += 1
                    detail_symbol_extracted_count += 1
                    extraction_res = chosen_extraction_res
                    state["detail_fetched_at_ms"] = now_ms
                    variant_name = "primary" if chosen_url_idx == 0 else "detail_path_fallback"

                    if extraction_res["symbols"]:
                        state["candidate_symbols"] = extraction_res["symbols"]
                        state["symbol_extraction_source"] = "detail_path_fallback" if chosen_url_idx > 0 else extraction_res["symbol_extraction_source"]
                        state["symbol_derivation_method"] = extraction_res["symbol_derivation_method"]
                        state["quote_derivation_source"] = "exchange_info"
                        state["symbol_validation_status"] = "pending_exchangeinfo_missing"
                        state["symbol_launch_times_ms"] = extraction_res.get("symbol_launch_times_ms", {})
                        state["symbol_onboard_times_ms"] = {}
                        state["detail_fetch_variant"] = variant_name
                        state["detail_fetch_url_used"] = chosen_url
                        state["detail_payload_hash"] = chosen_payload_sha256
                        state["detail_payload_trusted"] = True

                        effective_launch = build_effective_launch_times_ms(
                            candidate_symbols=state["candidate_symbols"],
                            symbol_onboard_times_ms=state["symbol_onboard_times_ms"],
                            symbol_launch_times_ms=state["symbol_launch_times_ms"],
                            source_published_at_ms=state["raw"].get("releaseDate") or 0,
                            first_detected_at_ms=state["first_detected_at_ms"],
                            allow_release_date_fallback=False,
                            allow_legacy_max_age_fallback=False,
                        )
                        state["symbol_effective_launch_times_ms"] = effective_launch["symbol_effective_launch_times_ms"]
                        state["launch_time_source"] = effective_launch["launch_time_source"]

                        exchangeinfo_by_symbol, ex_ok = get_exchangeinfo_by_symbol()
                        if ex_ok:
                            validation_result = validate_candidate_symbols_against_exchangeinfo(
                                candidates=state["candidate_symbols"],
                                exchangeinfo_by_symbol=exchangeinfo_by_symbol,
                                allowed_margin_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS,
                                allowed_quote_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS,
                                allowed_contract_types=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES,
                                validatable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES,
                                emittable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_EMITTABLE_SYMBOL_STATUSES,
                                now_ms=now_ms,
                            )

                            state["symbol_onboard_times_ms"] = validation_result.get("symbol_onboard_times_ms", {})
                            effective_launch = build_effective_launch_times_ms(
                                candidate_symbols=state["candidate_symbols"],
                                symbol_onboard_times_ms=state["symbol_onboard_times_ms"],
                                symbol_launch_times_ms=state["symbol_launch_times_ms"],
                                source_published_at_ms=state["raw"].get("releaseDate") or 0,
                                first_detected_at_ms=state["first_detected_at_ms"],
                                allow_release_date_fallback=False,
                                allow_legacy_max_age_fallback=False,
                            )
                            state["symbol_effective_launch_times_ms"] = effective_launch["symbol_effective_launch_times_ms"]
                            state["launch_time_source"] = effective_launch["launch_time_source"]

                            should_emit, is_multi, symbols_override = check_article_emission_eligibility(
                                state, validation_result, effective_launch
                            )
                            if should_emit:
                                candidate_validation_success_count += len(symbols_override)

                                for sym in symbols_override:
                                    meta = validation_result["symbol_exchangeinfo"].get(sym, {})
                                    if meta.get("quoteAsset") == "U" or meta.get("marginAsset") == "U":
                                        u_settlement_symbol_extracted_count += 1

                                identity = build_candidate_symbol_set_identity(symbols_override)
                                c_hash = identity["candidate_symbol_set_hash"]
                                em_id = build_multi_symbol_emission_id(code, state.get("event_type", "futures_contract_launch"), c_hash)

                                norm_event = normalize_live_event(
                                    raw=state["raw"],
                                    source_parent_url=source_parent_url,
                                    detected_at_ms=state["first_detected_at_ms"],
                                    source_published_at_ms=state["raw"].get("releaseDate"),
                                    source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                    symbols_override=symbols_override,
                                    extraction_metadata={
                                        "symbol_extraction_source": state["symbol_extraction_source"],
                                        "symbol_derivation_method": state["symbol_derivation_method"],
                                        "quote_derivation_source": "exchange_info",
                                        "symbol_validation_status": "validated_candidate_set" if is_multi else "validated",
                                        "detail_fetch_attempted": True,
                                        "detail_fetch_status": "success",
                                        "symbol_parse_failed_reason": None,
                                        "symbol_parse_status": "parsed",
                                        "detail_fetch_variant": state.get("detail_fetch_variant", variant_name),
                                        "detail_fetch_url_used": state.get("detail_fetch_url_used", chosen_url),
                                        "detail_payload_hash": state.get("detail_payload_hash", chosen_payload_sha256),
                                        "detail_payload_trusted": state.get("detail_payload_trusted", True),
                                    }
                                )
                                norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                                norm_event["detail_fetched_at_ms"] = now_ms
                                norm_event["symbol_resolved_at_ms"] = now_ms
                                norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                                apply_formal_launch_event_contract(
                                    norm_event,
                                    state,
                                    validation_result,
                                    symbols_override,
                                    effective_launch,
                                )

                                if is_multi:
                                    apply_multi_symbol_candidate_set_contract(
                                        norm_event,
                                        state,
                                        validation_result,
                                        symbols_override,
                                        identity,
                                        em_id,
                                        effective_launch,
                                        now_ms,
                                    )

                                event_id = norm_event["event_id"]
                                if event_id not in seen_event_ids:
                                    written_event = record_formal_futures_launch_event(
                                        stream_paths=stream_paths,
                                        row=norm_event,
                                        seen_event_ids=seen_event_ids,
                                        events_detected=events_detected,
                                    )

                                    if written_event is not None:
                                        eq_item = dict(written_event)
                                        eq_item["first_futures_bar_status"] = "not_yet_available"
                                        eq_item["first_futures_bar_start_ms"] = None
                                        first_bar_queue.append(eq_item)

                                if is_multi:
                                    state["event_id"] = event_id
                                else:
                                    detail_retry_state.pop(code, None)
                            else:
                                if is_multi and (validation_result.get("pending_symbols") or len(state.get("candidate_symbols", [])) == 0):
                                    state["symbol_validation_status"] = "pending_candidate_set_readiness"
                                    state["pending_reason"] = "multi_symbol_candidate_set_not_ready" if validation_result.get("pending_symbols") else "multi_symbol_candidate_symbols_empty"
                                    state["exchangeinfo_visible_symbols"] = list(validation_result.get("symbol_exchangeinfo", {}).keys())
                                    state["exchangeinfo_missing_symbols"] = [s for s in state.get("candidate_symbols", []) if s not in validation_result.get("symbol_exchangeinfo", {})]
                                    state["hard_rejected_symbols"] = list(validation_result.get("rejected_symbols", []))
                                    state["symbol_exchangeinfo_statuses"] = {s: meta.get("status") for s, meta in validation_result.get("symbol_exchangeinfo", {}).items()}
                                elif validation_result["rejected_symbols"]:
                                    candidate_validation_failed_count += len(validation_result["rejected_symbols"])

                                    reason = next(
                                        iter(validation_result.get("rejection_reasons", {}).values()),
                                        "exchange_info_candidate_rejected",
                                    )
                                    symbol_empty_event_count += 1
                                    symbol_parse_failed_count += 1
                                    detail_symbol_parse_failed_count += 1

                                    norm_event = normalize_live_event(
                                        raw=state["raw"],
                                        source_parent_url=source_parent_url,
                                        detected_at_ms=state["first_detected_at_ms"],
                                        source_published_at_ms=state["raw"].get("releaseDate"),
                                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                        symbols_override=(),
                                        extraction_metadata={
                                            "symbol_extraction_source": state["symbol_extraction_source"],
                                            "symbol_derivation_method": state["symbol_derivation_method"],
                                            "quote_derivation_source": "exchange_info",
                                            "symbol_validation_status": "rejected",
                                            "detail_fetch_attempted": True,
                                            "detail_fetch_status": "success",
                                            "symbol_parse_failed_reason": reason,
                                            "symbol_parse_status": "terminal_failed",
                                            "detail_fetch_variant": state.get("detail_fetch_variant", variant_name),
                                            "detail_fetch_url_used": state.get("detail_fetch_url_used", chosen_url),
                                            "detail_payload_hash": state.get("detail_payload_hash", chosen_payload_sha256),
                                            "detail_payload_trusted": state.get("detail_payload_trusted", True),
                                        }
                                    )
                                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                                    norm_event["detail_fetched_at_ms"] = now_ms
                                    norm_event["symbol_resolved_at_ms"] = now_ms
                                    event_id = norm_event["event_id"]
                                    if event_id not in seen_event_ids:
                                        record_formal_futures_launch_event(
                                            stream_paths=stream_paths,
                                            row=norm_event,
                                            seen_event_ids=seen_event_ids,
                                            events_detected=events_detected,
                                        )

                                    state["terminal_state"] = True
                                    state["terminal_reason"] = "candidate_validation_rejected"
                                    state["terminal_at_ms"] = now_ms
                                    state["symbol_validation_status"] = "rejected"
                                elif validation_result["pending_symbols"]:
                                    pending_status = apply_pending_candidate_validation_state(state, validation_result)
                                    if pending_status == "pending_pre_trading":
                                        pre_launch_validation_deferred_count += len(validation_result["pending_symbols"])
                                    else:
                                        candidate_validation_pending_count += len(validation_result["pending_symbols"])
                        else:
                            if extraction_res and extraction_res.get("symbol_validation_status") == "validated_by_exact_text":
                                norm_event = normalize_live_event(
                                    raw=state["raw"],
                                    source_parent_url=source_parent_url,
                                    detected_at_ms=state["first_detected_at_ms"],
                                    source_published_at_ms=state["raw"].get("releaseDate"),
                                    source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                    symbols_override=extraction_res["symbols"],
                                    extraction_metadata={
                                        "symbol_extraction_source": "detail_path_fallback" if chosen_url_idx > 0 else extraction_res["symbol_extraction_source"],
                                        "symbol_derivation_method": extraction_res["symbol_derivation_method"],
                                        "quote_derivation_source": None,
                                        "symbol_validation_status": "validated_by_exact_text",
                                        "detail_fetch_attempted": True,
                                        "detail_fetch_status": "success",
                                        "symbol_parse_failed_reason": None,
                                        "symbol_parse_status": "parsed",
                                        "detail_fetch_variant": variant_name,
                                        "detail_fetch_url_used": chosen_url,
                                        "detail_payload_hash": chosen_payload_sha256,
                                        "detail_payload_trusted": True,
                                    }
                                )
                                norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                                norm_event["detail_fetched_at_ms"] = now_ms
                                norm_event["symbol_resolved_at_ms"] = now_ms
                                norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                                event_id = norm_event["event_id"]
                                if event_id not in seen_event_ids:
                                    written_event = record_formal_futures_launch_event(
                                        stream_paths=stream_paths,
                                        row=norm_event,
                                        seen_event_ids=seen_event_ids,
                                        events_detected=events_detected,
                                    )

                                    if written_event is not None:
                                        eq_item = dict(written_event)
                                        eq_item["first_futures_bar_status"] = "not_yet_available"
                                        eq_item["first_futures_bar_start_ms"] = None
                                        first_bar_queue.append(eq_item)

                                detail_retry_state.pop(code, None)
                    else:
                        symbol_empty_event_count += 1
                        symbol_parse_failed_count += 1
                        detail_symbol_parse_failed_count += 1

                        norm_event = normalize_live_event(
                            raw=state["raw"],
                            source_parent_url=source_parent_url,
                            detected_at_ms=state["first_detected_at_ms"],
                            source_published_at_ms=state["raw"].get("releaseDate"),
                            source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                            symbols_override=tuple(state.get("candidate_symbols") or ()),
                            extraction_metadata={
                                "symbol_extraction_source": extraction_res["symbol_extraction_source"],
                                "symbol_derivation_method": extraction_res["symbol_derivation_method"],
                                "quote_derivation_source": None,
                                "symbol_validation_status": "rejected",
                                "detail_fetch_attempted": True,
                                "detail_fetch_status": "success",
                                "symbol_parse_failed_reason": "detail_symbols_empty",
                                "symbol_parse_status": "terminal_failed",
                                "detail_fetch_variant": variant_name,
                                "detail_fetch_url_used": chosen_url,
                                "detail_payload_hash": chosen_payload_sha256,
                                "detail_payload_trusted": True,
                            }
                        )
                        norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                        norm_event["detail_fetched_at_ms"] = now_ms
                        norm_event["symbol_resolved_at_ms"] = now_ms
                        norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                        event_id = norm_event["event_id"]
                        if event_id not in seen_event_ids:
                            record_formal_futures_launch_event(
                                stream_paths=stream_paths,
                                row=norm_event,
                                seen_event_ids=seen_event_ids,
                                events_detected=events_detected,
                            )

                        detail_retry_state.pop(code, None)
                else:
                    detail_fetch_failed_count += 1

                    if final_fetch_res is None:
                        continue

                    attempt_result = classify_detail_attempt_result(final_fetch_res)
                    err_reason = final_fetch_res.get("error") or "fetch_failed"

                    if final_fetch_res.get("ok") and not is_trusted:
                        err_reason = "empty_detail_payload"

                    if err_reason == "empty_detail_payload" or final_fetch_res.get("payload_size_bytes") == 0:
                        detail_empty_payload_count += 1

                    status = final_fetch_res.get("http_status")
                    if status in TRANSIENT_DETAIL_HTTP_STATUSES:
                        detail_http_not_ready_count += 1

                    chk_res = dict(final_fetch_res)
                    if err_reason == "empty_detail_payload":
                        chk_res["error"] = "empty_detail_payload"

                    status = chk_res.get("http_status")
                    if status == 202:
                        attempt_res_class = "http_202_empty"
                    elif status == 200 and chk_res.get("payload_size_bytes") == 0:
                        attempt_res_class = "http_200_empty_untrusted_payload"
                    elif status:
                        attempt_res_class = f"http_{status}"
                    else:
                        attempt_res_class = "network_or_fixture_error"
                    if is_transient_detail_fetch_error(chk_res):
                        state["transient_detail_error_count"] = state.get("transient_detail_error_count", 0) + 1
                        state["retry_count"] = int(state.get("retry_count") or 0) + 1
                        state["detail_fetch_attempted"] = True
                        state["status"] = "pending_detail_retry"
                        state["pending_reason"] = err_reason
                        state["last_retry_at_ms"] = now_ms
                        state["last_detail_failure_class"] = attempt_res_class
                        state["detail_retryable"] = True
                        state["next_detail_retry_at_ms"] = now_ms + compute_detail_transient_backoff_ms(
                            state["transient_detail_error_count"],
                            base_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC,
                            max_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC,
                        )
                        continue
                    else:
                        state["non_transient_detail_error_count"] = state.get("non_transient_detail_error_count", 0) + 1
                        state["retry_count"] = state["non_transient_detail_error_count"]
                        state["last_retry_at_ms"] = now_ms
                        state["next_detail_retry_at_ms"] = now_ms
                        state["last_detail_failure_class"] = f"http_{chk_res.get('http_status')}" if chk_res.get("http_status") else "non_transient_error"
                        state["detail_retryable"] = False

                        max_retries_limit = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES", 3)
                        if state["retry_count"] >= max_retries_limit:
                            symbol_empty_event_count += 1
                            symbol_parse_failed_count += 1
                            detail_symbol_parse_failed_count += 1
                            detail_terminal_failed_count += 1

                            norm_event = normalize_live_event(
                                raw=state["raw"],
                                source_parent_url=source_parent_url,
                                detected_at_ms=state["first_detected_at_ms"],
                                source_published_at_ms=state["raw"].get("releaseDate"),
                                source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                symbols_override=(),
                                extraction_metadata={
                                    "symbol_extraction_source": "none",
                                    "detail_fetch_attempted": True,
                                    "detail_fetch_status": err_reason,
                                    "symbol_parse_failed_reason": err_reason,
                                    "symbol_parse_status": "terminal_failed",
                                }
                            )
                            norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                            norm_event["detail_fetched_at_ms"] = now_ms
                            norm_event["symbol_resolved_at_ms"] = now_ms
                            norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                            terminal_diag = dict(norm_event)
                            terminal_diag["consumable_by_stage1_5f"] = False
                            terminal_diag["diagnostic_stream"] = "detail_retry_terminal_diagnostics"
                            append_jsonl(stream_paths["detail_retry_terminal_diagnostics"], terminal_diag, storage_guard=storage_guard)

                            state["terminal_state"] = True
                            state["terminal_reason"] = err_reason
                            state["terminal_at_ms"] = now_ms
                            persisted_articles[code] = state
                            detail_retry_state.pop(code, None)
                        continue

            # Persist scheduler state
            for code, st in detail_retry_state.items():
                persisted_articles[code] = st
            scheduler_state["articles"] = serialize_stage1_5d_v3_articles(persisted_articles)
            scheduler_state["endpoint_health"] = endpoint_health
            write_detail_retry_scheduler_state(
                output_root,
                scheduler_state,
                metadata_version=3,
                storage_guard=storage_guard,
            )


            append_jsonl(stream_paths["raw_payloads"], {"timestamp_ms": now_ms, "payload": payload}, storage_guard=storage_guard)

            hb = cycle_res["heartbeat"]

        else:
            poll_failed_count += 1
            consecutive_failed_polls += 1
            hb = {

                "poll_started_at_ms": now_ms,
                "poll_completed_at_ms": int(time.time() * 1000),
                "configured_poll_interval_sec": args.poll_interval_sec,
                "poll_success": False,
                "source_format_drift": False,
                "schema_parse_error": False,
                "heartbeat_gap": False,
                "error": fetch_err,
            }

        hb["configured_poll_interval_sec"] = args.poll_interval_sec
        hb["actual_poll_interval_sec"] = actual_poll_interval_sec
        hb["poll_schedule_drift_ms"] = poll_schedule_drift_ms
        append_jsonl(stream_paths["heartbeats"], hb, storage_guard=storage_guard)

        heartbeats.append(hb)

        # 4. Check First Futures Bar for events in queue (only if live/readonly)
        if first_bar_queue and args.live_public_readonly and not args.fixture_json:
            budget = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_CHECK_BUDGET_PER_POLL", 3)

            exchangeinfo_by_symbol, ex_ok = get_exchangeinfo_by_symbol()

            to_process = first_bar_queue[:budget]
            remaining = first_bar_queue[budget:]
            processed = []

            for eq_item in to_process:
                symbols = eq_item.get("symbols", [])
                if not symbols:
                    eq_item["first_futures_bar_status"] = "current_exchangeinfo_not_found"
                    processed.append(eq_item)
                    continue

                symbol = symbols[0]
                if not ex_ok:
                    eq_item["first_futures_bar_status"] = "network_error"
                    processed.append(eq_item)
                    continue

                if symbol not in exchangeinfo_by_symbol:
                    eq_item["first_futures_bar_status"] = "current_exchangeinfo_not_found"
                    processed.append(eq_item)
                    continue


                klines_url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=15m&limit=5"
                kline_res = None
                kline_err = None
                try:
                    k_res = fetch_public_json(klines_url, live_public_readonly=True, timeout_sec=10.0)
                    if k_res["ok"]:
                        kline_res = k_res["payload"]
                    else:
                        kline_err = k_res["error"]
                except Exception as e:
                    kline_err = str(e)

                k_manifest = {
                    "request_id": f"kline_{int(time.time()*1000)}_{symbol}",
                    "request_type": "first_futures_bar_klines",
                    "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                    "source_type": "klines",
                    "symbol": symbol,
                    "url": klines_url,
                    "final_url": klines_url,
                    "http_status": 200 if kline_res else 400,
                    "row_count": len(kline_res) if kline_res else 0,
                    "error": kline_err,
                    "fetched_at_ms": int(time.time() * 1000),
                }
                append_jsonl(stream_paths["request_manifest"], k_manifest, storage_guard=storage_guard)
                request_manifest.append(k_manifest)

                if kline_res is not None:
                    bars_by_symbol = {symbol: [{"bar_start_ms": bar[0]} for bar in kline_res]}
                    checked = check_first_bar_for_event(
                        eq_item, bars_by_symbol, int(time.time() * 1000)
                    )
                    processed.append(checked)
                else:
                    eq_item["first_futures_bar_status"] = "network_error"
                    processed.append(eq_item)

            first_bar_queue = processed + remaining

        schedule_revision_producer_attestation = build_schedule_revision_producer_attestation(
            integration_health=(
                "runtime_attestation_compromised"
                if attestation_lifecycle["runtime_attestation_compromised"]
                else (
                    schedule_revision_integration_health
                    if schedule_revision_integration_health != "initializing"
                    else ("ready" if hb.get("poll_success") else "poll_failed")
                )
            ),
            static_proof_result=static_proof_result,
            consumer_proof_result=consumer_proof_result,
        )

        schedule_revision_producer_effective_enabled = schedule_revision_producer_attestation[
            "schedule_revision_producer_effective_enabled"
        ]
        loop_gate_context = {
            "output_root": output_root,
            "run_id": output_root.name,
            "events_stream_relative_path": "events/*.jsonl",
            "live_public_readonly": args.live_public_readonly,
            "generated_at_ms": int(time.time() * 1000),
            "first_poll_started_at_ms": first_poll_started_at_ms or int(time.time() * 1000),
            "last_poll_finished_at_ms": int(time.time() * 1000),
            "last_successful_poll_at_ms": int(time.time() * 1000) if hb.get("poll_success") else 0,
            "poll_attempt_count": poll_count,
            "successful_poll_count": poll_success_count,
            "failed_poll_count": poll_failed_count,
            "consecutive_failed_polls": consecutive_failed_polls,
            "fatal_blockers": fatal_blockers,
            "prior_stage_safety_prerequisite_met": prior_stage_safety_prerequisite_met,
            "fixture_run": bool(args.fixture_json),
            "source_format_drift_active": source_format_drift_count > 0,
            "schema_parse_error_active": schema_parse_error_count > 0,
            "storage_budget_passed": storage_budget_passed,
            **storage_guard.status_snapshot(),
            "detail_endpoint_degraded_active": is_detail_source_degraded(endpoint_health, "bapi_article_detail_query", int(time.time() * 1000)),
            "bapi_trusted_payload_rate": 1.0 if bapi_detail_request_count == 0 else (bapi_detail_trusted_payload_count / float(bapi_detail_request_count)),
            "symbol_parse_success_rate": 1.0 if bapi_detail_trusted_payload_count == 0 else (bapi_symbol_parse_success_count / float(bapi_detail_trusted_payload_count)),
            "symbol_validation_success_rate": 1.0 if bapi_symbol_parse_success_count == 0 else (bapi_symbol_validation_success_count / float(bapi_symbol_parse_success_count)),
            "scheduler_starved_expired_count": sum(
                1 for row in persisted_articles.values()
                if row.get("terminal_failure_type") == "detail_never_attempted_budget_starved"
            ),
            **schedule_revision_producer_attestation,
        }
        write_stage1_5d_runtime_gate(
            output_root,
            build_stage1_5d_runtime_gate(loop_gate_context),
            storage_guard=storage_guard,
        )

        if args.max_polls is not None and poll_count >= args.max_polls:
            break

        time.sleep(args.poll_interval_sec)


    end_time = time.time()
    observation_hours = (end_time - start_time) / 3600.0
    debug_short_run = (
        args.max_polls is not None or args.max_seconds is not None or observation_hours < 24.0
    )

    final_events = []
    for ev in events_detected:
        updated = None
        for q_item in first_bar_queue:
            if q_item.get("event_id") == ev.get("event_id"):
                updated = q_item
                break
        if updated:
            final_events.append(updated)
        else:
            final_events.append(ev)

    detail_pending_retry_count = sum(
        1
        for state in detail_retry_state.values()
        if state.get("detail_fetch_attempt_count", 0) > 0
        or state.get("transient_detail_error_count", 0) > 0
    )
    detail_manifest_counts_by_article = {}
    request_manifest_root = output_root / "request_manifest"
    for manifest_path in sorted(request_manifest_root.glob("*.jsonl")) if request_manifest_root.exists() else []:
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("request_type") != "announcement_detail":
                continue
            source_article_id = row.get("source_article_id")
            if not source_article_id:
                continue
            detail_manifest_counts_by_article[source_article_id] = (
                detail_manifest_counts_by_article.get(source_article_id, 0) + 1
            )
    detail_fetch_attempt_manifest_mismatch_count = sum(
        1
        for code, state in detail_retry_state.items()
        if int(state.get("detail_http_request_count") or 0) != detail_manifest_counts_by_article.get(code, 0)
    )

    summary_now_ms = int(time.time() * 1000)
    overdue_diag = summarize_detail_retry_overdue_state(
        detail_retry_state,
        now_ms=summary_now_ms,
        warn_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_WARN_SEC * 1000,
        hard_warn_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_HARD_WARN_SEC * 1000,
    )
    source_health_diag = summarize_detail_source_health(endpoint_health, summary_now_ms)

    summary = build_smoke_summary(
        upstream_evidence=evidence_res,
        heartbeats=heartbeats,
        events=final_events,
        request_manifest=request_manifest,
        fixture_run=bool(args.fixture_json),
        debug_short_run=debug_short_run,
        observation_hours=observation_hours,
        counters={
            "raw_futures_launch_article_count": raw_futures_launch_article_count,
            "symbol_parsed_event_count": symbol_parsed_event_count,
            "symbol_parse_failed_count": symbol_parse_failed_count,
            "deduped_new_event_count": len(events_detected),
            "detail_retry_overdue_pending_count": overdue_diag["detail_retry_overdue_pending_count"],
            "detail_retry_overdue_attempted_count": overdue_diag["detail_retry_overdue_attempted_count"],
            "detail_retry_overdue_never_attempted_count": overdue_diag["detail_retry_overdue_never_attempted_count"],
            "detail_retry_due_timestamp_missing_count": overdue_diag["detail_retry_due_timestamp_missing_count"],
            "detail_attempt_manifest_mismatch_count": detail_fetch_attempt_manifest_mismatch_count,
            "detail_retry_oldest_overdue_ms": overdue_diag["detail_retry_oldest_overdue_ms"],
            "detail_retry_overdue_warn_active": overdue_diag["detail_retry_overdue_warn_active"],
            "detail_retry_overdue_hard_warn_active": overdue_diag["detail_retry_overdue_hard_warn_active"],
            "detail_retry_overdue_selected_total": detail_retry_overdue_selected_total,
            "detail_retry_overdue_deferred_total": detail_retry_overdue_deferred_total,
            "detail_retry_overdue_retry_cycle_total": detail_retry_overdue_retry_cycle_total,
            "detail_fetch_attempted_count": detail_fetch_attempted_count,
            "detail_fetch_success_count": detail_fetch_success_count,
            "detail_fetch_failed_count": detail_fetch_failed_count,
            "detail_fetch_budget_deferred_count": detail_fetch_budget_deferred_count,
            "detail_fetch_url_rejected_count": detail_fetch_url_rejected_count,
            "detail_symbol_extracted_count": detail_symbol_extracted_count,
            "detail_symbol_parse_failed_count": detail_symbol_parse_failed_count,
            "title_symbol_extracted_count": title_symbol_extracted_count,
            "symbol_empty_event_count": symbol_empty_event_count,
            "candidate_validation_pending_count": candidate_validation_pending_count,
            "candidate_validation_success_count": candidate_validation_success_count,
            "candidate_validation_expired_count": candidate_validation_expired_count,
            "u_settlement_symbol_extracted_count": u_settlement_symbol_extracted_count,
            "pre_launch_validation_deferred_count": pre_launch_validation_deferred_count,
            "detail_pending_retry_count": detail_pending_retry_count,
            "detail_empty_payload_count": detail_empty_payload_count,
            "detail_http_not_ready_count": detail_http_not_ready_count,
            "detail_terminal_failed_count": detail_terminal_failed_count,
            "detail_transient_timeout_count": detail_transient_timeout_count,
            "detail_budget_starved_count": detail_budget_starved_count,
            "detail_never_attempted_expired_count": detail_never_attempted_expired_count,
            "detail_first_attempt_sla_breach_count": detail_first_attempt_sla_breach_count,
            "detail_scheduler_pending_count": detail_scheduler_pending_count,
            "detail_scheduler_backoff_count": detail_scheduler_backoff_count,
            "detail_endpoint_degraded_count": detail_endpoint_degraded_count,
            "detail_endpoint_degraded_active": detail_endpoint_degraded_active,
            "detail_success_symbols_empty_count": detail_success_symbols_empty_count,
            "detail_degraded_recent_retry_count": detail_degraded_recent_retry_count,
            "detail_fetch_fallback_attempt_count": detail_fetch_fallback_attempt_count,
            "detail_fetch_fallback_success_count": detail_fetch_fallback_success_count,
            "detail_fetch_attempt_manifest_mismatch_count": detail_fetch_attempt_manifest_mismatch_count,
            "bapi_detail_request_count": bapi_detail_request_count,
            "bapi_detail_success_count": bapi_detail_success_count,
            "bapi_detail_trusted_payload_count": bapi_detail_trusted_payload_count,
            "bapi_detail_schema_drift_count": bapi_detail_schema_drift_count,
            "bapi_detail_identity_mismatch_count": bapi_detail_identity_mismatch_count,
            "bapi_detail_rate_limited_count": bapi_detail_rate_limited_count,
            "bapi_to_support_fallback_count": bapi_to_support_fallback_count,
            "bapi_symbol_parse_success_count": bapi_symbol_parse_success_count,
            "bapi_symbol_validation_pending_count": bapi_symbol_validation_pending_count,
            "bapi_symbol_validation_success_count": bapi_symbol_validation_success_count,
            "support_fallback_success_count": detail_fetch_fallback_success_count,
            "detail_http_manifest_mismatch_count": detail_fetch_attempt_manifest_mismatch_count,
            "bapi_payload_revision_count": bapi_payload_revision_count,
            "bapi_payload_hash_change_count": bapi_payload_hash_change_count,
            "schedule_revision_emitted_count": schedule_revision_emitted_count,
            "schedule_revision_diagnostic_count": schedule_revision_diagnostic_count,
            "schedule_revision_index_collision_count": schedule_revision_index_collision_count,
            "formal_launch_identity_index_rebuilt_count": rebuilt_index_rows,
            "bapi_detail_source_degraded": source_health_diag["bapi_detail_source_degraded"],
            "support_detail_source_degraded": source_health_diag["support_detail_source_degraded"],
            "all_detail_sources_degraded": source_health_diag["all_detail_sources_degraded"],
        },
    )



    write_smoke_summary_atomically(
        output_summary_path,
        summary,
        storage_guard=storage_guard,
    )

    print(f"Summary written to {output_summary_path}")
    return 0


def _write_runtime_storage_terminal_evidence(error: StorageWriteBlocked) -> None:
    output_root = Path(error.storage_guard.output_root)
    terminal_gate, terminal_summary, terminal_diagnostic = _build_storage_failure_artifacts(
        output_root,
        error.storage_blocker,
        error.result.get("storage_guard_status") or error.result.get("status"),
    )
    for path, artifact in (
        (output_root / "live_safety_gate_summary.json", terminal_gate),
        (output_root / "binance_futures_launch_smoke_summary.json", terminal_summary),
        (output_root / "storage_failure_diagnostic.json", terminal_diagnostic),
    ):
        try:
            if path.name == "live_safety_gate_summary.json":
                write_stage1_5d_runtime_gate(output_root, artifact, storage_guard=error.storage_guard)
            else:
                write_smoke_summary_atomically(path, artifact, storage_guard=error.storage_guard)
        except RuntimeError as terminal_error:
            print(f"StorageGuard terminal evidence write failed: {terminal_error}")


def main():
    try:
        return _main()
    except StorageWriteBlocked as error:
        _write_runtime_storage_terminal_evidence(error)
        print(f"StorageGuard runtime write blocked: {error.storage_blocker}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
