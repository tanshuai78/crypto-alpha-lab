import hashlib
import json
import os
from pathlib import Path
from typing import Any

from loguru import logger

from configs import base
from src.research.external_signal_shadow.stage1_5_storage_guard import require_storage_write
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
    DepthSnapshot,
    EventSymbolState,
)


def make_acceptance_id(state: EventSymbolState) -> str:
    return f"acc_{state.event_symbol_id}"


def make_terminal_hygiene_id(stable_event_symbol_key: str, terminal_status: str, normalized_anchor_class: str, bootstrap_root_id: str) -> str:
    raw = f"{stable_event_symbol_key}|{terminal_status}|{normalized_anchor_class}|{bootstrap_root_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_terminal_ignored_state(
    flat_event: dict,
    terminal_reason: str,
    terminal_status: str,
    now_ms: int,
    diagnostics: dict,
) -> EventSymbolState:
    stable_key = flat_event.get("stable_event_symbol_key", "")
    boot_root_id = diagnostics.get("bootstrap_root_id", "")
    norm_class = diagnostics.get("normalized_anchor_class", "")
    term_id = make_terminal_hygiene_id(stable_key, terminal_status, norm_class, boot_root_id)
    payload_hash = flat_event.get("detail_payload_hash") or flat_event.get("payload_hash") or ""

    src_art_id = flat_event.get("source_article_id") or ""
    ev_id = flat_event.get("event_id") or ""

    return EventSymbolState(
        event_symbol_id=flat_event["event_symbol_id"],
        event_id=ev_id,
        symbol=flat_event.get("symbol", ""),
        detected_at_ms=flat_event.get("detected_at_ms", now_ms),
        status=terminal_status,
        terminal_hygiene_id=term_id,
        terminal_status=terminal_status,
        terminal_reason=terminal_reason,
        terminal_at_ms=now_ms,
        consumable_by_stage1_5g=False,
        source_event_payload_hash=payload_hash,
        latest_event_payload_hash=payload_hash,
        source_article_id=src_art_id,
        stable_event_symbol_key=stable_key,
    )


def build_historical_anchor_hygiene_diagnostic(state: EventSymbolState, diagnostic_at_ms: int) -> dict:
    return {
        "event_symbol_id": state.event_symbol_id,
        "symbol": state.symbol,
        "terminal_hygiene_id": state.terminal_hygiene_id,
        "terminal_status": state.terminal_status,
        "terminal_reason": state.terminal_reason,
        "diagnostic_type": "historical_anchor_pre_bootstrap_ignored",
        "diagnostic_at_ms": diagnostic_at_ms,
        "consumable_by_stage1_5g": False,
    }


def build_rejected_event_symbol_row(
    flat_event: dict,
    terminal_hygiene_id: str,
    rejected_reason: str,
    now_ms: int,
    watermark_max_seen_detected_at_ms: int,
    watermark_version: int,
    eligibility_diag: dict,
    basis_diag: dict,
) -> dict:
    if not flat_event.get("event_symbol_id"):
        raise ValueError("event_symbol_id_required")
    res = {
        "event_symbol_id": flat_event["event_symbol_id"],
        "event_id": flat_event.get("event_id", ""),
        "source_article_id": flat_event.get("source_article_id", ""),
        "symbol": flat_event.get("symbol", ""),
        "terminal_hygiene_id": terminal_hygiene_id,
        "rejected_reason": rejected_reason,
        "rejection_reason": rejected_reason,
        "rejected_at_ms": now_ms,
        "detected_at_ms": flat_event.get("detected_at_ms", now_ms),
        "consumable_by_stage1_5g": True,
        "watermark_max_seen_detected_at_ms": watermark_max_seen_detected_at_ms,
        "watermark_version": watermark_version,
    }
    if eligibility_diag:
        res.update(eligibility_diag)
    if basis_diag:
        res.update(basis_diag)
    return res


def is_depth_collection_active_status(status: str) -> bool:
    return status in {"active", "active_anchor_revision_contaminated"}


def make_stable_event_symbol_key(event_row: dict, symbol: str) -> str:
    src_article_id = (event_row.get("source_article_id") or "").strip()
    sym = symbol.strip().upper()
    event_type = event_row.get("event_type") or "futures_contract_launch"
    return f"{event_type}|{src_article_id}|{sym}"



def load_latest_state_by_event_symbol_id(
    observer_state_jsonl: str | os.PathLike,
    *,
    fail_on_malformed: bool = False,
) -> dict[str, EventSymbolState] | dict[str, Any]:
    path = Path(observer_state_jsonl)
    tmp_file = path.parent / f".{path.name}.compact.tmp"
    if tmp_file.exists():
        try:
            logger.info(f"Advisory B: Discarding temp state file {tmp_file} on startup.")
            tmp_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to remove temp state file: {e}")

    if not path.exists():
        return {} if not fail_on_malformed else {"integrity_passed": True, "latest": {}, "malformed_row": None}

    latest: dict[str, EventSymbolState] = {}
    malformed_row = None
    malformed_error = None

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                st = EventSymbolState.from_dict(data)
                if st.event_symbol_id:
                    latest[st.event_symbol_id] = st
            except Exception as e:
                logger.warning(f"Failed to parse EventSymbolState at line {line_num}: {e}")
                malformed_row = line_str
                malformed_error = str(e)
                if fail_on_malformed:
                    break

    if malformed_row is not None and fail_on_malformed:
        return {
            "integrity_passed": False,
            "latest": latest,
            "malformed_row": malformed_row,
            "error": malformed_error,
        }

    return latest


def compact_observer_state_jsonl(
    observer_state_jsonl: str | os.PathLike,
    *,
    storage_guard: Any,
) -> dict[str, Any]:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    path = Path(observer_state_jsonl)
    if not path.exists():
        return {"integrity_passed": True, "compacted": False, "blocker": None}

    # Phase A: Physical-last scan & malformed check
    scan_res = load_latest_state_by_event_symbol_id(path, fail_on_malformed=True)
    if isinstance(scan_res, dict) and scan_res.get("integrity_passed") is False:
        logger.error(f"Checkpoint integrity failure in {path}: preserve file and fail closed.")
        return {
            "integrity_passed": False,
            "compacted": False,
            "blocker": "blocked_checkpoint_integrity",
            "malformed_row": scan_res.get("malformed_row"),
        }

    latest = scan_res if isinstance(scan_res, dict) and "latest" not in scan_res else scan_res.get("latest", scan_res)
    if not latest:
        return {"integrity_passed": True, "compacted": False, "blocker": None}

    # Phase B: Incremental line-by-line byte calculation (no giant joined string)
    candidate_bytes = 0
    serialized_rows = []
    for state in latest.values():
        row_json = json.dumps(state.to_dict(), sort_keys=True) + "\n"
        row_bytes = row_json.encode("utf-8")
        candidate_bytes += len(row_bytes)
        serialized_rows.append(row_bytes)

    old_size = path.stat().st_size if path.exists() else 0
    persistent_delta = candidate_bytes - old_size
    transient_peak = candidate_bytes

    pid = os.getpid()
    tmp_path = path.parent / f".{path.name}.compact.{pid}.tmp"

    def _write_compact_action():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "wb") as f:
            for row_b in serialized_rows:
                f.write(row_b)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, path)

        try:
            parent_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        except Exception:
            pass

    res = storage_guard.reserve_and_write(
        artifact_class="normal_data",
        transient_peak_bytes=transient_peak,
        persistent_delta_bytes=persistent_delta,
        write_func=_write_compact_action,
    )

    if res["status"] != "ready" or not res.get("written", False):
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        require_storage_write(storage_guard, res)

    return {"integrity_passed": True, "compacted": True, "blocker": None}


def create_pending_observation_state(event_symbol_row: dict, status: str, diagnostics: dict, now_ms: int) -> EventSymbolState:
    d = dict(diagnostics)
    first_seen = d.get("first_seen_at_ms") or getattr(event_symbol_row, "first_seen_at_ms", None) or now_ms
    retry_interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_ANCHOR_RESOLUTION_RETRY_INTERVAL_SEC * 1000
    legacy_wait_ms = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_LEGACY_SOURCE_REVISION_WAIT_MS", 24 * 60 * 60 * 1000)
    legacy_deadline_ms = d.get("legacy_source_revision_wait_deadline_ms") or (now_ms + legacy_wait_ms)

    anchor_ms = d.get("observation_anchor_ms")
    if status == "pending_launch_time_in_future" and anchor_ms is not None:
        deadline_ms = None
        resolution_started_ms = None
        next_check = anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS
        next_res = d.get("next_anchor_resolution_at_ms") or (now_ms + retry_interval_ms)
    else:
        deadline_ms = d.get("anchor_resolution_deadline_ms") or (now_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS)
        resolution_started_ms = d.get("anchor_resolution_started_at_ms") or now_ms
        next_check = d.get("next_admission_check_at_ms") or (anchor_ms if anchor_ms else now_ms + retry_interval_ms)
        next_res = d.get("next_anchor_resolution_at_ms") or (now_ms + retry_interval_ms)

    is_formal_v2 = (
        event_symbol_row.get("formal_event_contract_version") == 2
        or d.get("formal_event_contract_version") == 2
        or d.get("anchor_contract_version") == 2
    )
    eff_source = d.get("effective_observation_anchor_source") if is_formal_v2 else (
        d.get("effective_observation_anchor_source") or event_symbol_row.get("effective_observation_anchor_source")
    )

    return EventSymbolState(
        event_symbol_id=event_symbol_row["event_symbol_id"],
        event_id=event_symbol_row.get("event_id", ""),
        symbol=event_symbol_row["symbol"],
        detected_at_ms=event_symbol_row.get("detected_at_ms", now_ms),
        status=status,
        observer_state_schema_version=3,
        source_contract_status=d.get("source_contract_status"),
        pending_source_event_unvalidated=d.get("pending_source_event_unvalidated", False),
        required_source_revision=d.get("required_source_revision"),
        pending_reason=d.get("pending_reason") or status,
        pending_terminal_reason=d.get("pending_terminal_reason", ""),
        legacy_source_revision_wait_started_at_ms=d.get("legacy_source_revision_wait_started_at_ms", now_ms),
        legacy_source_revision_wait_deadline_ms=legacy_deadline_ms,
        observation_anchor_ms=anchor_ms,
        observation_anchor_basis=d.get("observation_anchor_basis", ""),
        observation_anchor_confidence=d.get("observation_anchor_confidence", ""),
        observation_anchor_candidates=d.get("observation_anchor_candidates", {}),
        observation_anchor_disagreement_max_ms=d.get("observation_anchor_disagreement_max_ms", 0),
        observation_anchor_conflict_active=d.get("observation_anchor_conflict_active", False),
        source_article_id=str(event_symbol_row.get("source_article_id") or ""),
        stable_event_symbol_key=event_symbol_row.get("stable_event_symbol_key", ""),
        stable_event_key=event_symbol_row.get("stable_event_key", ""),
        latest_event_payload_hash=event_symbol_row.get("detail_payload_hash") or event_symbol_row.get("payload_hash") or "",
        first_seen_at_ms=first_seen,
        announcement_capture_time_ms=d.get("announcement_capture_time_ms") or event_symbol_row.get("detected_at_ms"),
        next_admission_check_at_ms=next_check,
        next_anchor_resolution_at_ms=next_res,
        anchor_resolution_started_at_ms=resolution_started_ms,
        anchor_resolution_deadline_ms=deadline_ms,
        bootstrap_watermark_max_seen_detected_at_ms=d.get("bootstrap_watermark_max_seen_detected_at_ms"),
        admission_watermark_at_first_seen_ms=d.get("admission_watermark_at_first_seen_ms"),
        announcement_capture_post_bootstrap_watermark=d.get("announcement_capture_post_bootstrap_watermark"),
        launch_anchor_post_bootstrap_watermark=d.get("launch_anchor_post_bootstrap_watermark"),
        capacity_defer_count=d.get("capacity_defer_count", 0),
        anchor_resolution_attempt_count=d.get("anchor_resolution_attempt_count", 0),
        source_detail_url_normalized=str(event_symbol_row.get("source_detail_url_normalized") or d.get("source_detail_url_normalized") or ""),
        source_published_at_ms=event_symbol_row.get("source_published_at_ms") or d.get("source_published_at_ms"),
        formal_event_contract_version=event_symbol_row.get("formal_event_contract_version") or d.get("formal_event_contract_version"),
        formal_event_consumable_by_stage1_5f=event_symbol_row.get("formal_event_consumable_by_stage1_5f") if event_symbol_row.get("formal_event_consumable_by_stage1_5f") is not None else d.get("formal_event_consumable_by_stage1_5f"),
        symbol_identity_validation_status=event_symbol_row.get("symbol_identity_validation_status") or d.get("symbol_identity_validation_status"),
        launch_anchor_evidence_level=event_symbol_row.get("launch_anchor_evidence_level") or d.get("launch_anchor_evidence_level"),
        effective_observation_anchor_source=eff_source,
        launch_anchor_validation_status=event_symbol_row.get("launch_anchor_validation_status") or d.get("launch_anchor_validation_status"),
        source_anchor_contract_hash=d.get("source_anchor_contract_hash", ""),
        admission_anchor_contract_hash=d.get("admission_anchor_contract_hash", ""),
        latest_anchor_contract_hash=d.get("latest_anchor_contract_hash", ""),
        anchor_contract_version=d.get("anchor_contract_version"),
        anchor_precedence_policy=d.get("anchor_precedence_policy", ""),
        anchor_contract_decision_at_ms=d.get("anchor_contract_decision_at_ms"),
        admission_anchor_evidence_level=d.get("admission_anchor_evidence_level", ""),
        latest_anchor_evidence_level=d.get("latest_anchor_evidence_level", ""),
        admission_max_evidence_class=d.get("admission_max_evidence_class", ""),
        latest_max_evidence_class=d.get("latest_max_evidence_class", ""),
        clean_start_sla_pass=d.get("clean_start_sla_pass", False),
        clean_evidence_start_allowed=d.get("clean_evidence_start_allowed", False),
        latest_source_semantic_fingerprint=str(d.get("latest_source_semantic_fingerprint") or ""),
    )


def promote_pending_to_active_observation(pending_state: EventSymbolState, now_ms: int, evidence_start_class: str) -> EventSymbolState:
    anchor_ms = pending_state.observation_anchor_ms
    win_start = anchor_ms if anchor_ms is not None else now_ms
    win_end = win_start + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS

    d = pending_state.to_dict()
    acceptance_id = pending_state.acceptance_id or make_acceptance_id(pending_state)
    d.update({
        "status": "active",
        "observation_admitted_at_ms": now_ms,
        "observation_started_at_ms": now_ms,
        "observation_window_start_ms": win_start,
        "observation_window_end_ms": win_end,
        "evidence_start_class": evidence_start_class,
        "first_depth_request_at_ms": None,
        "acceptance_id": acceptance_id,
        "acceptance_state": "accepted_state_committed",
    })
    return EventSymbolState.from_dict(d)


def start_observation(event_symbol_row: dict, now_ms: int) -> EventSymbolState:
    window_end_ms = now_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS
    return EventSymbolState(
        event_symbol_id=event_symbol_row["event_symbol_id"],
        event_id=event_symbol_row["event_id"],
        symbol=event_symbol_row["symbol"],
        detected_at_ms=event_symbol_row["detected_at_ms"],
        observation_started_at_ms=now_ms,
        observation_window_start_ms=now_ms,
        observation_window_end_ms=window_end_ms,
        status="active",
        depth_snapshot_count=0,
        last_snapshot_ms=0,
        max_gap_ms=0,
        coverage_ratio_pass=False,
        max_gap_pass=False,
        research_result_valid=False,
    )


def apply_anchor_contract_revision_to_state(state: EventSymbolState, revision: dict, now_ms: int) -> EventSymbolState:
    from src.research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        compute_latest_anchor_contract_hash,
    )

    if state.status == "pending_cancelled":
        return state

    is_formal_v2 = (
        state.formal_event_contract_version == 2
        or state.anchor_contract_version == 2
        or getattr(state, "source_contract_status", "") == "formal_v2_valid"
    )
    if state.status.startswith("pending_") and is_formal_v2:
        return state

    revision_application_id = str(revision.get("revision_application_id") or "")
    applied_ids = list(getattr(state, "applied_schedule_revision_ids", []) or [])
    if revision_application_id and revision_application_id in applied_ids:
        return state

    d = state.to_dict()
    rev_anchor = (revision.get("symbol_revised_anchor_ms") or {}).get(state.symbol)
    d["anchor_contract_revision_count"] = (state.anchor_contract_revision_count or 0) + 1
    if revision_application_id:
        d["applied_schedule_revision_ids"] = [*applied_ids, revision_application_id]

    previous_latest_hash = state.latest_anchor_contract_hash or state.admission_anchor_contract_hash or state.source_anchor_contract_hash
    if revision_application_id and previous_latest_hash:
        d["latest_anchor_contract_hash"] = compute_latest_anchor_contract_hash(
            previous_latest_anchor_contract_hash=previous_latest_hash,
            revision_application_id=revision_application_id,
            latest_contract={
                "symbol": state.symbol,
                "symbol_revised_anchor_ms": rev_anchor,
                "revision_id": revision.get("revision_id"),
                "revision_payload_hash": revision.get("revision_payload_hash"),
                "anchor_precedence_policy": revision.get("anchor_precedence_policy"),
            },
        )

    status_for_sym = (revision.get("symbol_official_schedule_statuses") or {}).get(state.symbol)
    rev_intent = revision.get("revision_intent") or ("cancelled" if status_for_sym == "cancelled" else "")
    is_cancelled = rev_intent == "cancelled" or status_for_sym == "cancelled"
    is_conflict = bool(revision.get("is_late_conflict")) or rev_intent == "late_conflict" or status_for_sym == "official_schedule_conflict"
    is_postponed_without_anchor = status_for_sym == "postponed_without_anchor"

    is_new_application = bool(revision_application_id) and revision_application_id not in applied_ids

    if state.status.startswith("pending_"):
        if is_cancelled:
            d.update({
                "status": "pending_cancelled",
                "pending_reason": "official_schedule_cancelled",
                "pending_terminal_reason": "",
                "observation_anchor_ms": None,
                "next_admission_check_at_ms": None,
                "next_anchor_resolution_at_ms": None,
                "anchor_resolution_started_at_ms": None,
                "anchor_resolution_deadline_ms": None,
            })
        elif is_conflict or is_postponed_without_anchor:
            new_status = "pending_anchor_conflict" if is_conflict else "pending_launch_anchor_missing"
            new_reason = "official_schedule_conflict" if is_conflict else "postponed_without_anchor"
            d["status"] = new_status
            d["pending_reason"] = new_reason
            d["pending_terminal_reason"] = ""
            d["observation_anchor_ms"] = None
            d["next_admission_check_at_ms"] = None

            if is_new_application or state.anchor_resolution_started_at_ms is None:
                d["anchor_resolution_started_at_ms"] = now_ms
                d["anchor_resolution_deadline_ms"] = now_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS
        elif rev_anchor is not None:
            new_status = "pending_launch_time_in_future" if now_ms < rev_anchor + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS else "pending_ready_for_admission"
            d.update({
                "status": new_status,
                "pending_reason": new_status,
                "pending_terminal_reason": "",
                "observation_anchor_ms": rev_anchor,
                "anchor_contract_decision_at_ms": now_ms,
                "latest_anchor_evidence_level": "official_schedule",
                "latest_max_evidence_class": "clean_or_recovery",
                "next_admission_check_at_ms": rev_anchor + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS,
                "anchor_resolution_started_at_ms": None,
                "anchor_resolution_deadline_ms": None,
            })
    elif is_depth_collection_active_status(state.status):
        if is_cancelled:
            d["status"] = "active_anchor_revision_contaminated"
            d["observation_anchor_revision_contaminated"] = True
            d["anchor_revision_contamination_reason"] = "official_schedule_cancelled"
            d["latest_max_evidence_class"] = "none"
        elif is_conflict:
            d["status"] = "active_anchor_revision_contaminated"
            d["observation_anchor_revision_contaminated"] = True
            d["anchor_revision_contamination_reason"] = "late_conflict_official_schedule"
            d["latest_max_evidence_class"] = "none"
        elif rev_anchor is not None and rev_anchor != state.observation_anchor_ms:
            d["status"] = "active_anchor_revision_contaminated"
            d["observation_anchor_revision_contaminated"] = True
            d["anchor_revision_contamination_reason"] = "fallback_anchor_replaced_by_official_schedule"
            d["latest_max_evidence_class"] = "none"
        elif rev_anchor == state.observation_anchor_ms:
            d["latest_anchor_evidence_level"] = "official_schedule"
    elif state.status.startswith("completed"):
        if is_cancelled:
            d["status"] = "completed_anchor_revision_contaminated"
            d["observation_anchor_revision_contaminated"] = True
            d["anchor_revision_contamination_reason"] = "official_schedule_cancelled"
            d["latest_max_evidence_class"] = "none"
        elif is_conflict:
            d["status"] = "completed_anchor_revision_contaminated"
            d["observation_anchor_revision_contaminated"] = True
            d["anchor_revision_contamination_reason"] = "late_conflict_official_schedule"
            d["latest_max_evidence_class"] = "none"
        elif rev_anchor is not None and rev_anchor != state.observation_anchor_ms:
            d["status"] = "completed_anchor_revision_contaminated"
            d["observation_anchor_revision_contaminated"] = True
            d["anchor_revision_contamination_reason"] = "post_completion_official_schedule_revision_mismatch"
            d["latest_max_evidence_class"] = "none"

    return EventSymbolState.from_dict(d)


def record_depth_request(state: EventSymbolState, now_ms: int) -> EventSymbolState:
    if not is_depth_collection_active_status(state.status):
        return state

    req_at = state.first_depth_request_at_ms if state.first_depth_request_at_ms is not None else now_ms
    anchor_ms = state.observation_anchor_ms
    req_lat = (req_at - anchor_ms) if anchor_ms is not None else None

    d = state.to_dict()
    d["first_depth_request_at_ms"] = req_at
    d["first_depth_request_latency_ms"] = req_lat
    d["attempted_snapshot_count"] = state.attempted_snapshot_count + 1
    return EventSymbolState.from_dict(d)


def record_depth_snapshot(state: EventSymbolState, snapshot: DepthSnapshot) -> EventSymbolState:
    if not is_depth_collection_active_status(state.status):
        return state

    fetched_at = snapshot.fetched_at_ms
    count = state.depth_snapshot_count + 1
    last_ts = state.last_snapshot_ms or 0

    if last_ts > 0:
        gap = fetched_at - last_ts
        max_gap = max(state.max_gap_ms, gap)
    else:
        max_gap = state.max_gap_ms

    d = state.to_dict()
    d["depth_snapshot_count"] = count
    d["last_snapshot_ms"] = fetched_at
    d["max_gap_ms"] = max_gap
    d["successful_http_snapshot_count"] = state.successful_http_snapshot_count + 1

    if snapshot.depth_status == "healthy":
        d["valid_book_snapshot_count"] = state.valid_book_snapshot_count + 1
        if state.first_healthy_snapshot_at_ms is None:
            d["first_healthy_snapshot_at_ms"] = fetched_at
            anchor_ms = state.observation_anchor_ms
            if anchor_ms is not None:
                d["first_valid_book_latency_ms"] = fetched_at - anchor_ms
            req_at = state.first_depth_request_at_ms
            if req_at is not None:
                d["market_valid_book_latency_after_first_request_ms"] = fetched_at - req_at
    elif getattr(snapshot, "slippage_status", "") == "empty":
        d["empty_book_snapshot_count"] = state.empty_book_snapshot_count + 1
    else:
        d["invalid_book_snapshot_count"] = state.invalid_book_snapshot_count + 1

    return EventSymbolState.from_dict(d)


def compute_snapshot_time_coverage(state: EventSymbolState, snapshots: list) -> dict:
    poll_interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC * 1000
    expected = int(base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS // poll_interval_ms)
    min_required = int(expected * base.EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COVERAGE_RATIO)
    win_start = state.observation_window_start_ms or state.observation_started_at_ms or 0
    win_end = state.observation_window_end_ms or (win_start + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS)
    obs_started = state.observation_started_at_ms or win_start
    pre_start_expected = 0
    if obs_started > win_start:
        pre_start_expected = min(expected, int((min(obs_started, win_end) - win_start) // poll_interval_ms))

    if not snapshots:
        return {
            "coverage_ratio_pass": False,
            "max_gap_pass": False,
            "max_gap_ms": 0,
            "research_result_valid": False,
            "coverage_ratio": 0.0,
            "expected_snapshot_count": expected,
            "unique_snapshot_bucket_count": 0,
            "duplicate_snapshot_row_count": 0,
            "out_of_window_snapshot_row_count": 0,
            "missing_snapshot_bucket_count": expected,
            "pre_start_expected_snapshot_count": pre_start_expected,
            "pre_start_missing_snapshot_count": pre_start_expected,
        }

    sorted_snaps = sorted(snapshots, key=lambda s: s.fetched_at_ms)
    in_window_snaps = [s for s in sorted_snaps if s.fetched_at_ms >= win_start and s.fetched_at_ms < win_end]
    out_of_window_count = len(sorted_snaps) - len(in_window_snaps)
    unique_buckets = set()
    duplicate_count = 0
    for s in in_window_snaps:
        bucket_idx = int((s.fetched_at_ms - win_start) // poll_interval_ms)
        if 0 <= bucket_idx < expected:
            if bucket_idx in unique_buckets:
                duplicate_count += 1
            unique_buckets.add(bucket_idx)
        else:
            out_of_window_count += 1

    unique_bucket_count = len(unique_buckets)
    coverage_ratio = unique_bucket_count / float(expected) if expected > 0 else 0.0
    count_pass = unique_bucket_count >= min_required

    if in_window_snaps:
        first_ts = in_window_snaps[0].fetched_at_ms
        last_ts = in_window_snaps[-1].fetched_at_ms

        first_boundary_pass = first_ts <= win_start + 2 * poll_interval_ms
        last_boundary_pass = last_ts >= win_end - 2 * poll_interval_ms
    else:
        first_boundary_pass = False
        last_boundary_pass = False

    max_gap = 0
    for i in range(1, len(in_window_snaps)):
        gap = in_window_snaps[i].fetched_at_ms - in_window_snaps[i - 1].fetched_at_ms
        if gap > max_gap:
            max_gap = gap

    max_gap_pass = max_gap <= base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_SNAPSHOT_GAP_MS

    coverage_ratio_pass = count_pass and first_boundary_pass and last_boundary_pass
    research_result_valid = coverage_ratio_pass and max_gap_pass
    missing_count = max(0, expected - unique_bucket_count)

    return {
        "coverage_ratio_pass": coverage_ratio_pass,
        "max_gap_pass": max_gap_pass,
        "max_gap_ms": max_gap,
        "research_result_valid": research_result_valid,
        "coverage_ratio": coverage_ratio,
        "expected_snapshot_count": expected,
        "unique_snapshot_bucket_count": unique_bucket_count,
        "duplicate_snapshot_row_count": duplicate_count,
        "out_of_window_snapshot_row_count": out_of_window_count,
        "missing_snapshot_bucket_count": missing_count,
        "pre_start_expected_snapshot_count": pre_start_expected,
        "pre_start_missing_snapshot_count": pre_start_expected,
    }


def finalize_observation_if_due(state: EventSymbolState, now_ms: int, snapshots: list) -> EventSymbolState:
    if not is_depth_collection_active_status(state.status):
        return state

    if now_ms < state.observation_window_end_ms:
        return state

    cov = compute_snapshot_time_coverage(state, snapshots)
    status = "completed" if cov["research_result_valid"] else "expired_without_depth"
    if state.observation_anchor_revision_contaminated:
        status = "completed_anchor_revision_contaminated"

    if not snapshots:
        status = "expired_without_depth"

    d = state.to_dict()
    d.update({
        "status": status,
        "depth_snapshot_count": len(snapshots),
        "last_snapshot_ms": snapshots[-1].fetched_at_ms if snapshots else 0,
        "max_gap_ms": cov["max_gap_ms"],
        "coverage_ratio_pass": cov["coverage_ratio_pass"],
        "max_gap_pass": cov["max_gap_pass"],
        "research_result_valid": cov["research_result_valid"],
        "expected_snapshot_count": cov.get("expected_snapshot_count", 0),
        "unique_snapshot_bucket_count": cov.get("unique_snapshot_bucket_count", 0),
        "duplicate_snapshot_row_count": cov.get("duplicate_snapshot_row_count", 0),
        "out_of_window_snapshot_row_count": cov.get("out_of_window_snapshot_row_count", 0),
        "missing_snapshot_bucket_count": cov.get("missing_snapshot_bucket_count", 0),
        "pre_start_expected_snapshot_count": cov.get("pre_start_expected_snapshot_count", 0),
        "pre_start_missing_snapshot_count": cov.get("pre_start_missing_snapshot_count", 0),
        "coverage_ratio": cov.get("coverage_ratio", 0.0),
    })
    return EventSymbolState.from_dict(d)


def load_latest_states_by_event_symbol_id(observer_state_jsonl: str | os.PathLike) -> dict[str, EventSymbolState]:
    res = load_latest_state_by_event_symbol_id(observer_state_jsonl)
    if isinstance(res, dict) and "latest" in res:
        return res["latest"]
    return res


def rebuild_missing_stable_event_symbol_key_if_safe(state: EventSymbolState) -> tuple[EventSymbolState, dict]:
    if state.stable_event_symbol_key and state.stable_event_symbol_key.strip():
        return state, {"stable_key_rebuilt": False, "identity_missing": False}

    src_article_id = (state.source_article_id or "").strip()
    sym = (state.symbol or "").strip().upper()
    if src_article_id and sym:
        event_type = getattr(state, "event_type", None) or "futures_contract_launch"
        mock_event = {"source_article_id": src_article_id, "event_type": event_type}
        rebuilt_key = make_stable_event_symbol_key(mock_event, sym)
        d = state.to_dict()
        d["stable_event_symbol_key"] = rebuilt_key
        return EventSymbolState.from_dict(d), {"stable_key_rebuilt": True, "identity_missing": False}

    return state, {
        "stable_key_rebuilt": False,
        "identity_missing": True,
        "block_reason": "unrebuildable_active_identity_missing",
    }


def detect_stable_event_symbol_key_collisions(grouped: dict[str, list[EventSymbolState]]) -> list[dict]:
    collisions = []
    for key, states in grouped.items():
        if key == "__MISSING_STABLE_KEY__":
            continue
        distinct_ids = sorted(list({st.event_symbol_id for st in states if st.event_symbol_id}))
        if len(distinct_ids) > 1:
            collisions.append({
                "stable_event_symbol_key": key,
                "distinct_event_symbol_ids": distinct_ids,
                "state_count": len(states),
                "states": [st.to_dict() for st in states],
            })
    return collisions



def group_latest_states_by_stable_event_symbol_key(latest: dict[str, EventSymbolState]) -> dict[str, list[EventSymbolState]]:
    grouped: dict[str, list[EventSymbolState]] = {}
    for st in latest.values():
        key = (st.stable_event_symbol_key or "").strip()
        if not key:
            key = "__MISSING_STABLE_KEY__"
        grouped.setdefault(key, []).append(st)
    return grouped


EVENT_BATCH_REGISTRY_FILENAME = "event_batch_registry.jsonl"


def build_event_batch_id(event_row: dict, candidate_set_hash: str = "") -> str:
    src_article_id = (event_row.get("source_article_id") or "").strip()
    ev_id = (event_row.get("event_id") or "").strip()
    c_hash = candidate_set_hash or event_row.get("multi_symbol_candidate_set_hash") or event_row.get("candidate_set_hash") or ""
    raw_id = f"{src_article_id}|{ev_id}|{c_hash}"
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()


def load_latest_event_batch_registry(
    output_root: str | Path,
    *,
    fail_on_malformed: bool = False,
) -> dict[str, dict] | dict[str, Any]:
    path = Path(output_root) / EVENT_BATCH_REGISTRY_FILENAME
    if not path.exists():
        return {} if not fail_on_malformed else {"integrity_passed": True, "latest": {}}

    latest: dict[str, dict] = {}
    malformed_row = None

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                row = json.loads(line_str)
                b_id = row.get("event_batch_id")
                if b_id:
                    latest[b_id] = row
            except Exception as e:
                logger.warning(f"Failed to parse event_batch_registry row at line {line_num}: {e}")
                malformed_row = line_str
                if fail_on_malformed:
                    break

    if malformed_row is not None and fail_on_malformed:
        return {"integrity_passed": False, "latest": latest, "malformed_row": malformed_row}

    return latest


def compact_event_batch_registry_jsonl(
    output_root: str | Path,
    *,
    storage_guard: Any,
) -> dict[str, Any]:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    path = Path(output_root) / EVENT_BATCH_REGISTRY_FILENAME
    if not path.exists():
        return {"integrity_passed": True, "compacted": False, "blocker": None}

    scan_res = load_latest_event_batch_registry(output_root, fail_on_malformed=True)
    if isinstance(scan_res, dict) and scan_res.get("integrity_passed") is False:
        return {
            "integrity_passed": False,
            "compacted": False,
            "blocker": "blocked_checkpoint_integrity",
            "malformed_row": scan_res.get("malformed_row"),
        }

    latest = scan_res.get("latest", scan_res) if isinstance(scan_res, dict) else scan_res
    if not latest:
        return {"integrity_passed": True, "compacted": False, "blocker": None}

    candidate_bytes = 0
    serialized_rows = []
    for row in latest.values():
        row_json = json.dumps(row, sort_keys=True) + "\n"
        row_bytes = row_json.encode("utf-8")
        candidate_bytes += len(row_bytes)
        serialized_rows.append(row_bytes)

    old_size = path.stat().st_size if path.exists() else 0
    persistent_delta = candidate_bytes - old_size
    transient_peak = candidate_bytes

    pid = os.getpid()
    tmp_path = path.parent / f".{path.name}.compact.{pid}.tmp"

    def _write_compact_batch():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "wb") as f:
            for row_b in serialized_rows:
                f.write(row_b)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)

    res = storage_guard.reserve_and_write(
        artifact_class="normal_data",
        transient_peak_bytes=transient_peak,
        persistent_delta_bytes=persistent_delta,
        write_func=_write_compact_batch,
    )

    if res["status"] != "ready" or not res.get("written", False):
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        require_storage_write(storage_guard, res)

    return {"integrity_passed": True, "compacted": True, "blocker": None}


def update_batch_registry_status(
    output_root: str | Path,
    event_batch_id: str,
    status: str,
    now_ms: int,
    durable_stable_keys: list[str] | None = None,
    block_reason: str | None = None,
    registry_map: dict[str, dict] | None = None,
    *,
    storage_guard: Any,
) -> dict:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    if registry_map is None:
        registry_map = load_latest_event_batch_registry(output_root)

    existing = registry_map.get(event_batch_id, {})
    existing_status = existing.get("status")

    # Monotonicity checks: final statuses cannot regress
    if existing_status in {"watermark_committed", "batch_blocked"}:
        if status != existing_status:
            logger.warning(f"Batch registry monotonicity violation: cannot transition batch {event_batch_id} from {existing_status} to {status}")
            return existing

    sorted_keys = sorted(list(dict.fromkeys(durable_stable_keys))) if durable_stable_keys is not None else existing.get("durable_stable_keys", [])

    # Suppress equal transition append
    if existing_status == status and existing.get("durable_stable_keys") == sorted_keys and existing.get("block_reason") == block_reason:
        return existing

    new_row = dict(existing)
    new_row["event_batch_id"] = event_batch_id
    new_row["status"] = status
    new_row["updated_at_ms"] = now_ms
    if "created_at_ms" not in new_row:
        new_row["created_at_ms"] = now_ms
    new_row["durable_stable_keys"] = sorted_keys
    if block_reason is not None:
        new_row["block_reason"] = block_reason

    row_bytes = (json.dumps(new_row) + "\n").encode("utf-8")
    path = Path(output_root) / EVENT_BATCH_REGISTRY_FILENAME

    def _write_row():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "ab") as f:
            f.write(row_bytes)
            f.flush()
            os.fsync(f.fileno())

    res = storage_guard.reserve_and_write(
        artifact_class="normal_data",
        transient_peak_bytes=len(row_bytes),
        persistent_delta_bytes=len(row_bytes),
        write_func=_write_row,
    )
    require_storage_write(storage_guard, res)

    registry_map[event_batch_id] = new_row
    return new_row
