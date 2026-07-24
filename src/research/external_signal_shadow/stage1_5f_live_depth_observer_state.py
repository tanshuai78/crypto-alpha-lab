import datetime
import hashlib
import json
import os
import shutil

from loguru import logger

from configs import base
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
    DepthSnapshot,
    EventSymbolState,
)
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
    make_event_symbol_id,
    make_stable_event_symbol_key,
)
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_watermark import (
    get_stable_event_key,
)


def make_acceptance_id(state: EventSymbolState) -> str:
    stable_key = state.stable_event_symbol_key or state.event_symbol_id
    anchor = state.observation_anchor_ms or state.observation_window_start_ms or 0
    return hashlib.sha256(f"{stable_key}|{anchor}".encode("utf-8")).hexdigest()


def make_terminal_hygiene_id(
    stable_event_symbol_key: str,
    terminal_status: str,
    normalized_anchor_class: str,
    bootstrap_root_id: str,
) -> str:
    payload = f"{stable_event_symbol_key}|{terminal_status}|{normalized_anchor_class}|{bootstrap_root_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_terminal_ignored_state(
    flat_event: dict,
    terminal_reason: str,
    terminal_status: str,
    now_ms: int,
    diagnostics: dict,
) -> EventSymbolState:
    sym = str(flat_event.get("symbol") or "").strip().upper()
    source_article_id = str(flat_event.get("source_article_id") or "").strip()
    event_id = str(flat_event.get("event_id") or "").strip()
    detected_at_ms = flat_event.get("detected_at_ms")

    if (not source_article_id and not event_id) or not sym or not detected_at_ms:
        raise ValueError("terminal ignored state requires source_article_id or event_id, symbol, detected_at_ms")

    stable_key = flat_event.get("stable_event_symbol_key") or make_stable_event_symbol_key(flat_event, sym)
    anchor_class = diagnostics.get("normalized_anchor_class", "all_pre_bootstrap")
    boot_root_id = diagnostics.get("bootstrap_root_id", "")
    terminal_hygiene_id = make_terminal_hygiene_id(stable_key, terminal_status, anchor_class, boot_root_id)
    payload_hash = str(
        flat_event.get("detail_payload_hash")
        or flat_event.get("payload_hash")
        or flat_event.get("raw_payload_hash")
        or ""
    )

    d = dict(diagnostics)
    return EventSymbolState(
        event_symbol_id=flat_event.get("event_symbol_id") or make_event_symbol_id(flat_event, sym),
        event_id=event_id,
        symbol=sym,
        detected_at_ms=int(detected_at_ms),
        status=terminal_status,
        terminal_hygiene_id=terminal_hygiene_id,
        terminal_status=terminal_status,
        terminal_reason=terminal_reason,
        terminal_at_ms=now_ms,
        consumable_by_stage1_5g=False,
        source_article_id=source_article_id,
        stable_event_symbol_key=stable_key,
        stable_event_key=flat_event.get("stable_event_key") or get_stable_event_key(flat_event),
        first_seen_at_ms=d.get("first_seen_at_ms") or int(detected_at_ms),
        announcement_capture_time_ms=d.get("announcement_capture_time_ms") or int(detected_at_ms),
        bootstrap_watermark_max_seen_detected_at_ms=d.get("bootstrap_watermark_max_seen_detected_at_ms"),
        admission_watermark_at_first_seen_ms=d.get("admission_watermark_at_first_seen_ms"),
        announcement_capture_post_bootstrap_watermark=d.get("announcement_capture_post_bootstrap_watermark"),
        launch_anchor_post_bootstrap_watermark=d.get("launch_anchor_post_bootstrap_watermark"),
        observation_anchor_candidates=d.get("normalized_anchor_candidates") or d.get("observation_anchor_candidates", {}),
        source_event_payload_hash=payload_hash,
        latest_event_payload_hash=payload_hash,
        terminal_audit_type="historical_anchor_hygiene_diagnostics",
    )


def build_historical_anchor_hygiene_diagnostic(state: EventSymbolState, diagnostic_at_ms: int) -> dict:
    return {
        "audit_metadata_version": 2,
        "diagnostic_type": "historical_anchor_pre_bootstrap_ignored",
        "terminal_hygiene_id": state.terminal_hygiene_id,
        "event_symbol_id": state.event_symbol_id,
        "event_id": state.event_id,
        "source_article_id": state.source_article_id,
        "stable_event_symbol_key": state.stable_event_symbol_key,
        "stable_event_key": state.stable_event_key,
        "symbol": state.symbol,
        "detected_at_ms": state.detected_at_ms,
        "terminal_status": state.terminal_status,
        "terminal_reason": state.terminal_reason,
        "terminal_at_ms": state.terminal_at_ms or diagnostic_at_ms,
        "diagnostic_at_ms": diagnostic_at_ms,
        "observation_anchor_candidates": state.observation_anchor_candidates,
        "bootstrap_watermark_max_seen_detected_at_ms": state.bootstrap_watermark_max_seen_detected_at_ms,
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
    sym = str(flat_event.get("symbol") or "").strip().upper()
    source_article_id = str(flat_event.get("source_article_id") or "").strip()
    event_id = str(flat_event.get("event_id") or "").strip()
    detected_at_ms = flat_event.get("detected_at_ms")
    event_symbol_id = flat_event.get("event_symbol_id")

    if not event_symbol_id or not sym or (not source_article_id and not event_id) or not detected_at_ms or not rejected_reason:
        raise ValueError("rejected event symbol row requires event_symbol_id, symbol, source_article_id or event_id, detected_at_ms, rejected_reason")

    e_diag = dict(eligibility_diag or {})
    b_diag = dict(basis_diag or {})

    anchor_age_ms = e_diag.get("selected_anchor_age_ms") or e_diag.get("event_age_ms")

    row = {
        "audit_metadata_version": 2,
        "event_symbol_id": event_symbol_id,
        "event_id": event_id,
        "source_article_id": source_article_id,
        "stable_event_key": flat_event.get("stable_event_key") or get_stable_event_key(flat_event),
        "stable_event_symbol_key": flat_event.get("stable_event_symbol_key") or make_stable_event_symbol_key(flat_event, sym),
        "symbol": sym,
        "event_type": flat_event.get("event_type", ""),
        "title": flat_event.get("title", ""),
        "detected_at_ms": detected_at_ms,
        "available_at_ms": flat_event.get("available_at_ms"),
        "source_published_at_ms": flat_event.get("source_published_at_ms"),
        "source_detail_url_normalized": flat_event.get("source_detail_url_normalized", ""),
        "rejected_reason": rejected_reason,
        "rejection_reason": rejected_reason,
        "status": "rejected",
        "depth_observation_started": False,
        "rejected_at_ms": now_ms,
        "terminal_hygiene_id": terminal_hygiene_id,
        "watermark_max_seen_detected_at_ms": watermark_max_seen_detected_at_ms,
        "watermark_version": watermark_version,
        "consumable_by_stage1_5g": True,
    }
    row.update(e_diag)
    row.update(b_diag)

    row["rejected_reason"] = rejected_reason
    row["rejection_reason"] = rejected_reason
    if anchor_age_ms is not None:
        row["event_age_ms"] = anchor_age_ms
        row["selected_anchor_age_ms"] = anchor_age_ms

    return row


def load_latest_state_by_event_symbol_id(observer_state_jsonl: str) -> dict:
    # Advisory B: clean up temporary compacted file if it exists (indicating a crash before rename)
    tmp_file = observer_state_jsonl + ".compacted.tmp"
    if os.path.exists(tmp_file):
        try:
            logger.info(f"Advisory B: Discarding temp state file {tmp_file} on startup.")
            os.remove(tmp_file)
        except Exception as e:
            logger.warning(f"Failed to remove temp state file: {e}")

    latest = {}
    if not os.path.exists(observer_state_jsonl):
        return latest

    with open(observer_state_jsonl, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                state = EventSymbolState.from_dict(data)
                latest[state.event_symbol_id] = state
            except Exception as e:
                logger.warning(f"Failed to parse state row: {e}")
    return latest


def compact_observer_state_jsonl(observer_state_jsonl: str) -> None:
    latest = load_latest_state_by_event_symbol_id(observer_state_jsonl)
    if not latest:
        return

    dir_name = os.path.dirname(os.path.abspath(observer_state_jsonl))
    os.makedirs(dir_name, exist_ok=True)

    tmp_file = observer_state_jsonl + ".compacted.tmp"
    try:
        fd = os.open(tmp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        with os.fdopen(fd, "w") as f:
            for state in latest.values():
                f.write(json.dumps(state.to_dict()) + "\n")
                f.flush()
            os.fsync(fd)
    except Exception as e:
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass
        raise e

    # Write backup of the original state file
    if os.path.exists(observer_state_jsonl):
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{observer_state_jsonl}.{timestamp}.jsonl.bak"
        try:
            shutil.copy2(observer_state_jsonl, backup_file)
            logger.info(f"State file backed up to {backup_file}")
        except Exception as e:
            logger.warning(f"Failed to write backup of state file: {e}")

    # Atomic rename
    os.replace(tmp_file, observer_state_jsonl)

    try:
        parent_fd = os.open(dir_name, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except Exception:
        pass


def create_pending_observation_state(event_symbol_row: dict, status: str, diagnostics: dict, now_ms: int) -> EventSymbolState:
    d = dict(diagnostics)
    first_seen = d.get("first_seen_at_ms") or getattr(event_symbol_row, "first_seen_at_ms", None) or now_ms
    retry_interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_ANCHOR_RESOLUTION_RETRY_INTERVAL_SEC * 1000
    deadline_ms = d.get("anchor_resolution_deadline_ms") or (now_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS)

    anchor_ms = d.get("observation_anchor_ms")
    next_check = d.get("next_admission_check_at_ms") or (anchor_ms if anchor_ms else now_ms + retry_interval_ms)
    next_res = d.get("next_anchor_resolution_at_ms") or (now_ms + retry_interval_ms)

    return EventSymbolState(
        event_symbol_id=event_symbol_row["event_symbol_id"],
        event_id=event_symbol_row.get("event_id", ""),
        symbol=event_symbol_row["symbol"],
        detected_at_ms=event_symbol_row.get("detected_at_ms", now_ms),
        status=status,
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
        anchor_resolution_deadline_ms=deadline_ms,
        bootstrap_watermark_max_seen_detected_at_ms=d.get("bootstrap_watermark_max_seen_detected_at_ms"),
        admission_watermark_at_first_seen_ms=d.get("admission_watermark_at_first_seen_ms"),
        announcement_capture_post_bootstrap_watermark=d.get("announcement_capture_post_bootstrap_watermark"),
        launch_anchor_post_bootstrap_watermark=d.get("launch_anchor_post_bootstrap_watermark"),
        capacity_defer_count=d.get("capacity_defer_count", 0),
        anchor_resolution_attempt_count=d.get("anchor_resolution_attempt_count", 0),
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



def record_depth_request(state: EventSymbolState, now_ms: int) -> EventSymbolState:
    if state.status != "active":
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
    if state.status != "active":
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
    if state.status != "active":
        return state

    if now_ms < state.observation_window_end_ms:
        return state

    cov = compute_snapshot_time_coverage(state, snapshots)
    status = "completed" if cov["research_result_valid"] else "expired_without_depth"

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
