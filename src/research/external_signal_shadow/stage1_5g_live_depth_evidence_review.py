from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Stage1_5GInputBundle:
    output_root: Path
    summary: dict
    watermark: dict
    states: list[dict]
    accepted_events: list[dict]
    rejected_events: list[dict]
    snapshots: list[dict]
    request_manifest_rows: list[dict]
    heartbeat_rows: list[dict]
    loader_blockers: list[str]
    loader_warnings: list[str]
    parse_error_count: int
    total_jsonl_line_count: int


def _load_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _load_jsonl_file(
    path: Path,
    loader_blockers: list[str],
    state_errors: dict[str, int],
) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                state_errors["total"] += 1
                try:
                    rows.append(json.loads(stripped))
                except json.JSONDecodeError:
                    state_errors["errors"] += 1
                    if "jsonl_parse_error" not in loader_blockers:
                        loader_blockers.append("jsonl_parse_error")
    except Exception:
        if "jsonl_parse_error" not in loader_blockers:
            loader_blockers.append("jsonl_parse_error")
    return rows


def _load_jsonl_glob(
    root: Path,
    pattern: str,
    loader_blockers: list[str],
    state_errors: dict[str, int],
) -> list[dict]:
    rows = []
    # Use glob to find files matching pattern
    for path in sorted(root.glob(pattern)):
        if path.is_file():
            rows.extend(_load_jsonl_file(path, loader_blockers, state_errors))
    return rows


def _stable_event_symbol_key_for_review(row: dict) -> str:
    key = str(row.get("stable_event_symbol_key") or "").strip()
    if key:
        return key
    source_article_id = str(row.get("source_article_id") or "").strip()
    event_type = str(row.get("event_type") or "futures_contract_launch").strip()
    symbol = str(row.get("symbol") or "").strip().upper()
    if source_article_id and event_type and symbol:
        return f"{event_type}|{source_article_id}|{symbol}"
    return ""


def detect_duplicate_stable_event_symbol_identity(rows: list[dict]) -> list[dict]:
    by_key: dict[str, set[str]] = {}
    for row in rows:
        event_symbol_id = str(row.get("event_symbol_id") or "").strip()
        key = _stable_event_symbol_key_for_review(row)
        if not event_symbol_id or not key:
            continue
        by_key.setdefault(key, set()).add(event_symbol_id)
    return [
        {
            "stable_event_symbol_key": key,
            "event_symbol_ids": sorted(ids),
        }
        for key, ids in sorted(by_key.items())
        if len(ids) > 1
    ]


def _load_observer_states_reduced(
    path: Path,
    loader_blockers: list[str],
    state_errors: dict[str, int],
) -> list[dict]:
    if not path.exists():
        return []

    latest: dict[str, dict] = {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                state_errors["total"] += 1
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError:
                    state_errors["errors"] += 1
                    if "jsonl_parse_error" not in loader_blockers:
                        loader_blockers.append("jsonl_parse_error")
                    continue

                es_id = row.get("event_symbol_id")
                if not es_id:
                    continue

                # JSONL append order is the durable state transition order.
                latest[es_id] = row
    except Exception:
        if "jsonl_parse_error" not in loader_blockers:
            loader_blockers.append("jsonl_parse_error")

    return list(latest.values())


def load_stage1_5g_inputs(output_root: str | Path) -> Stage1_5GInputBundle:
    root = Path(output_root)
    loader_blockers: list[str] = []
    loader_warnings: list[str] = []

    # State tracking for errors across JSONL parsing
    state_errors = {"total": 0, "errors": 0}

    # 1. Summary
    summary_path = root / "live_depth_observer_summary.json"
    if not summary_path.exists():
        loader_blockers.append("missing_or_unreadable_summary")
        summary = {}
    else:
        summary = _load_json_file(summary_path)
        if not summary:
            loader_blockers.append("missing_or_unreadable_summary")

    # 2. Watermark
    watermark_path = root / "watermark.json"
    if not watermark_path.exists():
        loader_blockers.append("missing_or_unreadable_watermark")
        watermark = {}
    else:
        watermark = _load_json_file(watermark_path)
        if not watermark:
            loader_blockers.append("missing_or_unreadable_watermark")

    # 3. States (streaming physical-last reduction)
    states = _load_observer_states_reduced(root / "observer_state.jsonl", loader_blockers, state_errors)


    # 4. Accepted/Rejected events
    accepted_events = _load_jsonl_glob(root, "events_accepted/*.jsonl", loader_blockers, state_errors)
    rejected_events = _load_jsonl_glob(root, "events_rejected/*.jsonl", loader_blockers, state_errors)
    duplicate_stable_identity_rows = detect_duplicate_stable_event_symbol_identity(
        accepted_events + [
            row for row in states
            if str(row.get("status") or "") in {"active", "completed"}
        ]
    )
    if duplicate_stable_identity_rows:
        loader_blockers.append("duplicate_stable_event_symbol_identity")
        loader_warnings.append(
            "duplicate_stable_event_symbol_identity_count="
            + str(len(duplicate_stable_identity_rows))
        )

    # 5. Snapshots
    snapshots = _load_jsonl_glob(root, "depth_snapshots/**/*.jsonl", loader_blockers, state_errors)

    # 6. Request manifest & heartbeat
    request_manifest_rows = _load_jsonl_glob(root, "request_manifest/*.jsonl", loader_blockers, state_errors)
    heartbeat_rows = _load_jsonl_glob(root, "heartbeat/*.jsonl", loader_blockers, state_errors)

    # Cross-reference snapshots to update states when matching snapshots are missing
    seen_snapshot_event_symbol_ids = {s.get("event_symbol_id") for s in snapshots if s.get("event_symbol_id")}
    updated_states = []
    for st in states:
        es_id = st.get("event_symbol_id")
        if es_id not in seen_snapshot_event_symbol_ids:
            # Overwrite snapshot count to 0 if the physical snapshot file is missing
            st = dict(st)
            st["depth_snapshot_count"] = 0
        updated_states.append(st)

    return Stage1_5GInputBundle(
        output_root=root,
        summary=summary,
        watermark=watermark,
        states=updated_states,
        accepted_events=accepted_events,
        rejected_events=rejected_events,
        snapshots=snapshots,
        request_manifest_rows=request_manifest_rows,
        heartbeat_rows=heartbeat_rows,
        loader_blockers=loader_blockers,
        loader_warnings=loader_warnings,
        parse_error_count=state_errors["errors"],
        total_jsonl_line_count=state_errors["total"],
    )


VALID_EVIDENCE_LABELS = {
    "announcement_and_launch_time",
    "launch_time_only",
    "recovery_validation_only",
}


def get_event_evidence_label(event: dict) -> str | None:
    return event.get("evidence_label") or event.get("live_depth_evidence_basis")


@dataclass(frozen=True)
class EvidenceIntegrityResult:
    blockers: list[str]
    warnings: list[str]
    evidence_label_counts: dict[str, int]
    formal_announcement_and_launch_count: int
    formal_completed_event_symbol_ids: set[str]


def reduce_latest_states_by_event_symbol_id(states: list[dict]) -> dict[str, dict]:
    """
    Reduce observer_state rows to latest state per event_symbol_id.
    Uses (ts, seq_num) tuple to guarantee deterministic monotonic ordering.
    """
    latest: dict[str, tuple[tuple[int, int], dict]] = {}
    for seq_num, row in enumerate(states):
        es_id = row.get("event_symbol_id")
        if not es_id:
            continue
        ts = int(row.get("updated_at_ms") or row.get("state_written_at_ms") or 0)
        sort_key = (ts, seq_num)
        if es_id not in latest or sort_key > latest[es_id][0]:
            latest[es_id] = (sort_key, row)
    return {es_id: item[1] for es_id, item in latest.items()}


def _validate_formal_v2_lineage(
    accepted_event: dict,
    latest_st: dict | None,
    completed_st: dict | None = None,
) -> tuple[bool, str | None]:
    is_v2_declared = (
        accepted_event.get("formal_event_contract_version") == 2
        or (latest_st and (latest_st.get("formal_event_contract_version") == 2 or latest_st.get("anchor_contract_version") == 2))
        or (completed_st and (completed_st.get("formal_event_contract_version") == 2 or completed_st.get("anchor_contract_version") == 2))
    )
    if not is_v2_declared:
        return True, None  # Legacy v1 fallback allowed

    if not latest_st:
        return False, "anchor_contract_lineage_state_missing"

    required_pairs = (
        ("anchor_precedence_policy", "official_schedule_priority_v1"),
        ("source_anchor_contract_hash", None),
        ("admission_anchor_contract_hash", None),
    )
    for field, expected in required_pairs:
        accepted_value = accepted_event.get(field)
        state_value = latest_st.get(field)
        if not accepted_value or not state_value or accepted_value != state_value:
            return False, "formal_v2_lineage_incomplete_or_mismatch"
        if expected is not None and accepted_value != expected:
            return False, "formal_v2_lineage_incomplete_or_mismatch"

    acc_source = accepted_event.get("effective_observation_anchor_source")
    lat_source = latest_st.get("effective_observation_anchor_source")
    acc_basis = accepted_event.get("observation_anchor_basis")
    lat_basis = latest_st.get("observation_anchor_basis")

    source_basis_valid = (
        acc_source == "official_schedule_anchor"
        and lat_source == "official_schedule_anchor"
        and acc_source == lat_source
        and acc_basis == acc_source
        and lat_basis == lat_source
        and acc_basis == lat_basis
    )
    if not source_basis_valid:
        return False, "formal_v2_lineage_incomplete_or_mismatch"

    v2_valid = (
        accepted_event.get("formal_event_contract_version") == 2
        and latest_st.get("anchor_contract_version") == 2
        and accepted_event.get("source_contract_status") == "formal_v2_valid"
        and accepted_event.get("launch_anchor_evidence_level") == "official_schedule"
        and latest_st.get("latest_anchor_evidence_level") == "official_schedule"
        and bool(accepted_event.get("source_article_id"))
        and accepted_event.get("source_article_id") == latest_st.get("source_article_id")
        and not latest_st.get("observation_anchor_revision_contaminated")
        and latest_st.get("latest_max_evidence_class") == "clean_or_recovery"
        and bool(latest_st.get("latest_anchor_contract_hash"))
    )
    if not v2_valid:
        return False, "formal_v2_lineage_incomplete_or_mismatch"

    if completed_st:
        latest_hash = latest_st.get("latest_anchor_contract_hash")
        comp_hash = completed_st.get("latest_anchor_contract_hash")
        if not comp_hash or latest_hash != comp_hash:
            return False, "formal_v2_lineage_incomplete_or_mismatch"

    return True, None


def validate_evidence_integrity(
    accepted_events: list[dict],
    watermark: dict,
    states: list[dict] | None = None,
    snapshots: list[dict] | None = None,
    summary: dict | None = None,
) -> EvidenceIntegrityResult:
    blockers: list[str] = []
    warnings: list[str] = []

    states_list = states or []
    snapshots_list = snapshots or []
    summary_dict = summary or {}

    # 1. Verify Watermark Presence
    if not watermark or "watermark_version" not in watermark:
        blockers.append("missing_or_unreadable_watermark")

    state_by_id = reduce_latest_states_by_event_symbol_id(states_list)

    evidence_label_counts = {lbl: 0 for lbl in VALID_EVIDENCE_LABELS}
    for event in accepted_events:
        label = get_event_evidence_label(event)
        if not label:
            blockers.append("missing_evidence_label")
            continue
        if label not in VALID_EVIDENCE_LABELS:
            blockers.append("unknown_evidence_label")
            continue

        evidence_label_counts[label] += 1

        if watermark:
            if "watermark_version" in event and event.get("watermark_version") != watermark.get("watermark_version"):
                blockers.append("watermark_version_mismatch")
            event_watermark_ms = event.get("watermark_max_seen_detected_at_ms")
            current_watermark_ms = watermark.get("max_seen_detected_at_ms")
            if (
                event_watermark_ms is not None
                and (current_watermark_ms is None or int(event_watermark_ms) > int(current_watermark_ms))
            ):
                blockers.append("watermark_max_seen_detected_at_ms_mismatch")

        es_id = event.get("event_symbol_id")
        latest_st = state_by_id.get(es_id) if es_id else None
        if not latest_st and es_id:
            blockers.append("anchor_contract_lineage_state_missing")
        elif latest_st:
            adm_acc = event.get("admission_anchor_contract_hash")
            adm_st = latest_st.get("admission_anchor_contract_hash")
            if adm_acc and adm_st and adm_acc != adm_st:
                blockers.append("anchor_contract_lineage_mismatch")
            if latest_st.get("observation_anchor_revision_contaminated"):
                blockers.append("anchor_revision_contaminated")
            if latest_st.get("validation_status") == "malformed" or event.get("validation_status") == "malformed":
                blockers.append("malformed_anchor_contract")

        v2_valid, v2_blocker = _validate_formal_v2_lineage(event, latest_st)
        if not v2_valid and v2_blocker and v2_blocker not in blockers:
            blockers.append(v2_blocker)

        if (
            event.get("effective_observation_anchor_source") == "exchangeinfo_onboard_date"
            or event.get("anchor_evidence_level") == "exchangeinfo_fallback"
        ):
            blockers.append("exchangeinfo_fallback_anchor")

    # 3. Cross-Validation Join Checks
    snapshots_by_id = {}
    for sn in snapshots_list:
        es_id = sn.get("event_symbol_id")
        if es_id:
            snapshots_by_id.setdefault(es_id, []).append(sn)

    # Completed state count verification
    completed_states = [st for st in state_by_id.values() if st.get("status") == "completed"]
    if summary_dict:
        expected_completed = summary_dict.get("completed_observation_count", 0)
        if len(completed_states) != expected_completed:
            blockers.append("summary_state_count_mismatch")

    # Completed state must have snapshot files/rows
    for st in completed_states:
        es_id = st.get("event_symbol_id")
        if not es_id or es_id not in snapshots_by_id or not snapshots_by_id[es_id]:
            blockers.append("completed_state_without_snapshots")
            continue

        expected_snapshot_count = st.get("depth_snapshot_count")
        if expected_snapshot_count is None:
            continue
        try:
            expected_snapshot_count_int = int(expected_snapshot_count)
        except (TypeError, ValueError):
            blockers.append("state_snapshot_count_invalid")
            continue
        if len(snapshots_by_id[es_id]) != expected_snapshot_count_int:
            blockers.append("state_snapshot_count_mismatch")

    # Compute formal counts
    formal_announcement_and_launch_count = 0
    formal_completed_event_symbol_ids = set()

    for event in accepted_events:
        es_id = event.get("event_symbol_id")
        label = get_event_evidence_label(event)
        if es_id and es_id in state_by_id:
            st = state_by_id[es_id]
            # Must join with completed state AND snapshots must exist
            if st.get("status") == "completed" and es_id in snapshots_by_id and snapshots_by_id[es_id]:
                if label == "announcement_and_launch_time":
                    v2_pass, _ = _validate_formal_v2_lineage(event, st, completed_st=st)
                    if v2_pass:
                        formal_announcement_and_launch_count += 1
                        formal_completed_event_symbol_ids.add(es_id)

    return EvidenceIntegrityResult(
        blockers=blockers,
        warnings=warnings,
        evidence_label_counts=evidence_label_counts,
        formal_announcement_and_launch_count=formal_announcement_and_launch_count,
        formal_completed_event_symbol_ids=formal_completed_event_symbol_ids,
    )


def resolve_observation_config(
    summary: dict,
    states: list[dict],
) -> tuple[dict, list[str]]:
    blockers = []
    config = {}

    from configs import base

    # 1. Try summary config snapshot
    win = summary.get("observation_window_ms")
    interval = summary.get("snapshot_interval_ms")
    cov = summary.get("min_snapshot_coverage_ratio")

    # 2. Try states config snapshot
    if (win is None or interval is None or cov is None) and states:
        for st in states:
            if st.get("observation_window_ms") is not None:
                win = st.get("observation_window_ms")
            if st.get("snapshot_interval_ms") is not None:
                interval = st.get("snapshot_interval_ms")
            if st.get("min_snapshot_coverage_ratio") is not None:
                cov = st.get("min_snapshot_coverage_ratio")

    # 3. Try configs/base.py
    if win is None:
        win = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS", None)
    if interval is None:
        poll_sec = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC", None)
        if poll_sec is not None:
            interval = poll_sec * 1000
    if cov is None:
        cov = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COVERAGE_RATIO", None)

    if win is None or interval is None or cov is None:
        blockers.append("missing_stage1_5f_observation_config")
    else:
        config["observation_window_ms"] = int(win)
        config["snapshot_interval_ms"] = int(interval)
        config["min_snapshot_coverage_ratio"] = float(cov)

    return config, blockers


def classify_stage1_5d_terminal_failure(event: dict) -> str:
    terminal_failure_type = event.get("terminal_failure_type")
    if terminal_failure_type in {
        "detail_never_attempted_budget_starved",
        "detail_transient_timeout",
        "detail_unavailable_timeout",
    }:
        return "collection_failure"
    if terminal_failure_type == "detail_success_symbols_empty":
        return "content_or_parser_empty"
    if terminal_failure_type == "candidate_validation_rejected":
        return "validation_rejected"
    if event.get("symbol_parse_status") == "terminal_failed":
        return "unknown_terminal_failure"
    return "not_terminal_failure"


@dataclass(frozen=True)
class DepthRequestHealthResult:
    depth_request_manifest_rows_count: int
    scheduler_diagnostic_rows_count: int
    per_symbol_request_success_rate_min: float | None
    global_request_success_rate: float
    blockers: list[str]


def compute_depth_request_health(
    request_manifest_rows: list[dict],
    completed_states: list[dict] = None,
) -> DepthRequestHealthResult:
    from configs import base
    completed_states = completed_states or []
    blockers = []

    # Filter depth snapshot rows vs scheduler diagnostic rows
    depth_manifest_rows = []
    scheduler_diagnostic_rows_count = 0
    for r in request_manifest_rows:
        req_type = r.get("request_type")
        if req_type is not None:
            if req_type == "depth_snapshot":
                depth_manifest_rows.append(r)
            elif req_type in {"announcement_detail_deferred", "announcement_list", "announcement_detail", "exchange_info", "first_futures_bar_klines"}:
                scheduler_diagnostic_rows_count += 1
        else:
            # Legacy check fallback
            is_depth = bool(
                r.get("event_symbol_id")
                or r.get("symbol")
                or r.get("requested_path") == base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_PATH
            )
            if is_depth:
                depth_manifest_rows.append(r)

    total_requests = len(depth_manifest_rows)
    success_requests = sum(
        1 for r in depth_manifest_rows
        if 200 <= r.get("http_status", 0) < 300
    )
    global_request_success_rate = (
        success_requests / total_requests if total_requests > 0 else 1.0
    )

    if total_requests > 0 and global_request_success_rate < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_REQUEST_SUCCESS_RATE:
        blockers.append("global_request_success_rate_below_threshold")

    if completed_states and any(
        not (r.get("event_symbol_id") or r.get("symbol"))
        for r in depth_manifest_rows
    ):
        blockers.append("request_manifest_symbol_key_missing")

    symbol_success = {}
    symbol_total = {}
    for r in depth_manifest_rows:
        key = r.get("event_symbol_id") or r.get("symbol")
        if not key:
            continue
        symbol_total[key] = symbol_total.get(key, 0) + 1
        if 200 <= r.get("http_status", 0) < 300:
            symbol_success[key] = symbol_success.get(key, 0) + 1

    symbol_rates = []
    for key, total in symbol_total.items():
        success = symbol_success.get(key, 0)
        rate = success / total
        symbol_rates.append(rate)

    per_symbol_request_success_rate_min = None
    if symbol_rates:
        per_symbol_request_success_rate_min = min(symbol_rates)

    if (
        per_symbol_request_success_rate_min is not None
        and per_symbol_request_success_rate_min
        < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_PER_SYMBOL_REQUEST_SUCCESS_RATE
    ):
        blockers.append("per_symbol_request_success_rate_below_threshold")

    return DepthRequestHealthResult(
        depth_request_manifest_rows_count=total_requests,
        scheduler_diagnostic_rows_count=scheduler_diagnostic_rows_count,
        per_symbol_request_success_rate_min=per_symbol_request_success_rate_min,
        global_request_success_rate=global_request_success_rate,
        blockers=blockers,
    )


def compute_coverage_metrics(
    states: list[dict],
    request_manifest_rows: list[dict],
    summary: dict | None = None,
    event_symbol_ids: set[str] | None = None,
) -> dict:
    from configs import base

    summary_dict = summary or {}
    blockers: list[str] = []
    warnings: list[str] = []

    config, config_blockers = resolve_observation_config(summary_dict, states)
    if config_blockers:
        blockers.extend(config_blockers)
        return {
            "expected_snapshot_count": 0,
            "min_snapshot_count_required": 0,
            "snapshot_interval_ms": 0,
            "blockers": blockers,
            "warnings": warnings,
        }

    observation_window_ms = config["observation_window_ms"]
    snapshot_interval_ms = config["snapshot_interval_ms"]

    expected_snapshot_count = int(observation_window_ms // snapshot_interval_ms)
    # Use Stage 1.5G min coverage ratio threshold
    min_snapshot_count_required = int(expected_snapshot_count * base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_SNAPSHOT_COVERAGE_RATIO)
    computed_max_gap_ms = max(
        base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_SNAPSHOT_GAP_MULTIPLIER * snapshot_interval_ms,
        base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_SNAPSHOT_GAP_FLOOR_MS,
    )

    latest_state_by_id: dict[str, dict] = {}
    for st in states:
        es_id = st.get("event_symbol_id")
        if es_id:
            latest_state_by_id[es_id] = st

    states_to_check = list(latest_state_by_id.values()) if latest_state_by_id else states
    if event_symbol_ids is not None:
        states_to_check = [
            st
            for st in states_to_check
            if st.get("event_symbol_id") in event_symbol_ids
        ]

    # Validate formal completed event-symbol states only when caller supplies
    # event_symbol_ids. Other accepted/active states are not part of 1.5G formal evidence.
    for st in states_to_check:
        count = st.get("depth_snapshot_count", 0)
        max_gap = st.get("max_gap_ms", 0)
        if count < min_snapshot_count_required:
            blockers.append("insufficient_depth_snapshot_count")
        if max_gap > computed_max_gap_ms:
            blockers.append("snapshot_gap_exceeded")

    # Request success rate analysis
    per_symbol_request_success_rate_min = 1.0
    global_request_success_rate = 1.0

    if request_manifest_rows:
        completed_states = [st for st in states_to_check if st.get("status") == "completed"]
        health = compute_depth_request_health(request_manifest_rows, completed_states)
        per_symbol_request_success_rate_min = health.per_symbol_request_success_rate_min if health.per_symbol_request_success_rate_min is not None else 1.0
        global_request_success_rate = health.global_request_success_rate
        blockers.extend(health.blockers)

    return {
        "expected_snapshot_count": expected_snapshot_count,
        "min_snapshot_count_required": min_snapshot_count_required,
        "snapshot_interval_ms": snapshot_interval_ms,
        "computed_max_gap_ms": computed_max_gap_ms,
        "checked_event_symbol_ids": sorted(
            st.get("event_symbol_id")
            for st in states_to_check
            if st.get("event_symbol_id")
        ),
        "per_symbol_request_success_rate_min": per_symbol_request_success_rate_min,
        "global_request_success_rate": global_request_success_rate,
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
    }


@dataclass(frozen=True)
class RawSnapshotIntegrityResult:
    blockers: list[str]
    warnings: list[str]
    null_ratio_max: float
    jsonl_parse_error_ratio: float
    jsonl_parse_error_count: int
    duplicate_snapshot_ratio_max: float
    non_monotonic_timestamp_count: int
    invalid_book_count: int


@dataclass(frozen=True)
class RawSnapshotQuarantineResult:
    blockers: list[str]
    warnings: list[str]
    clean_depth_evidence_pass: bool
    quarantined_depth_evidence_pass: bool
    quarantine_candidate: bool
    observed_snapshot_count: int
    expected_snapshot_count: int
    invalid_book_row_count: int
    invalid_book_minute_bucket_count: int
    invalid_book_ratio: float
    invalid_book_ratio_observed: float
    valid_snapshot_count_after_quarantine: int
    book_availability_ratio: float
    book_unavailable_ratio: float
    invalid_book_by_phase: dict[str, int]
    invalid_book_by_reason: dict[str, int]
    launch_warmup_invalid_row_count: int
    launch_warmup_invalid_minute_bucket_count: int
    midrun_invalid_book_count: int
    midrun_invalid_minute_bucket_count: int
    crossed_or_negative_book_count: int
    schema_invalid_count: int
    max_consecutive_invalid: int
    max_consecutive_invalid_after_warmup: int
    first_valid_book_latency_ms: int | None
    depth_quality_input_rows: list[dict]
    quarantined_invalid_book_rows: list[dict]


def _minute_bucket_ms(ts_ms: int) -> int:
    return int(ts_ms) // 60000 * 60000


def _is_schema_invalid_snapshot(row: dict) -> bool:
    return not row.get("event_symbol_id") or not row.get("symbol") or row.get("fetched_at_ms") is None


def _is_empty_book_snapshot(row: dict) -> bool:
    return row.get("best_bid") is None or row.get("best_ask") is None or row.get("spread_bps") is None


def _is_crossed_or_negative_book(row: dict) -> bool:
    bid = row.get("best_bid")
    ask = row.get("best_ask")
    spread = row.get("spread_bps")
    if bid is None or ask is None:
        return False
    try:
        bid_f = float(bid)
        ask_f = float(ask)
        spread_f = None if spread is None else float(spread)
    except (TypeError, ValueError):
        return True
    return bid_f <= 0 or ask_f <= 0 or bid_f >= ask_f or (spread_f is not None and spread_f < 0)



def _resolve_event_launch_time_ms(event: dict, state: dict | None = None) -> int | None:
    symbol = event.get("symbol") or (state or {}).get("symbol")
    for field in ("symbol_effective_launch_times_ms", "symbol_onboard_times_ms"):
        mapping = event.get(field) or (state or {}).get(field) or {}
        if symbol and isinstance(mapping, dict) and mapping.get(symbol) is not None:
            return int(mapping[symbol])
    for obj in (event, state or {}):
        basis = obj.get("observation_age_basis")
        if basis in {"symbol_effective_launch_time", "symbol_onboard_time"} and obj.get("observation_age_base_ms") is not None:
            return int(obj["observation_age_base_ms"])
    return None


def _resolve_observation_start_ms(event_symbol_id: str, snapshots: list[dict], event: dict, state: dict | None = None) -> int | None:
    for obj in (state or {}, event):
        for field in ("observation_started_at_ms", "accepted_at_ms"):
            if obj.get(field) is not None:
                return int(obj[field])
    times = [int(s["fetched_at_ms"]) for s in snapshots if s.get("event_symbol_id") == event_symbol_id and s.get("fetched_at_ms") is not None]
    return min(times) if times else None


def compute_raw_snapshot_quarantine_metrics(
    snapshots: list[dict],
    states: list[dict],
    accepted_events: list[dict],
    expected_snapshot_count: int,
) -> RawSnapshotQuarantineResult:
    from configs import base

    blockers: list[str] = []
    warnings: list[str] = []

    events_by_id = {e["event_symbol_id"]: e for e in accepted_events if e.get("event_symbol_id")}
    states_by_id = {s["event_symbol_id"]: s for s in states if s.get("event_symbol_id")}

    # Group valid snapshots by event_symbol_id
    schema_invalid_rows = []
    valid_schema_rows = []
    for r in snapshots:
        if _is_schema_invalid_snapshot(r):
            schema_invalid_rows.append(r)
        else:
            valid_schema_rows.append(r)

    schema_invalid_count = len(schema_invalid_rows)

    # Sort valid_schema_rows by (event_symbol_id, fetched_at_ms)
    valid_schema_rows.sort(key=lambda x: (x["event_symbol_id"], x["fetched_at_ms"]))

    # Group valid rows by event_symbol_id
    from collections import defaultdict
    rows_by_symbol = defaultdict(list)
    for r in valid_schema_rows:
        rows_by_symbol[r["event_symbol_id"]].append(r)

    quarantined_invalid_book_rows = []
    depth_quality_input_rows = []

    invalid_book_row_count = 0
    crossed_or_negative_book_count = 0
    launch_warmup_invalid_row_count = 0
    midrun_invalid_book_count = 0

    invalid_book_by_phase = {"launch_warmup": 0, "observation_initial": 0, "midrun": 0}
    invalid_book_by_reason = {
        "launch_warmup_empty_book": 0,
        "observation_initial_empty_book": 0,
        "midrun_empty_book": 0,
        "crossed_or_negative_book": 0,
        "schema_invalid": 0,
    }

    # Track consecutive invalid rows
    max_consecutive_invalid = 0
    max_consecutive_invalid_after_warmup = 0

    # Calculate first valid book latency
    first_valid_book_ts_by_symbol = {}
    launch_ts_by_symbol = {}
    observation_start_ts_by_symbol = {}

    for event_symbol_id, symbol_rows in rows_by_symbol.items():
        # Get event and state
        event = events_by_id.get(event_symbol_id, {})
        state = states_by_id.get(event_symbol_id, {})

        launch_time_ms = _resolve_event_launch_time_ms(event, state)
        observation_start_ms = _resolve_observation_start_ms(event_symbol_id, snapshots, event, state)

        launch_ts_by_symbol[event_symbol_id] = launch_time_ms
        observation_start_ts_by_symbol[event_symbol_id] = observation_start_ms

        if launch_time_ms is None:
            warnings.append("launch_time_missing_warmup_anchor_degraded")

        # Track consecutive counts for this symbol
        curr_consec = 0
        curr_consec_after_warmup = 0

        first_valid_ts = None

        for r in symbol_rows:
            fetched_at_ms = r["fetched_at_ms"]
            # Determine phase
            if launch_time_ms is not None:
                is_warmup = (
                    launch_time_ms
                    <= fetched_at_ms
                    < launch_time_ms + base.EXTERNAL_SIGNAL_STAGE1_5G_LAUNCH_WARMUP_WINDOW_MS
                )
                phase = "launch_warmup" if is_warmup else "midrun"
            else:
                is_warmup = observation_start_ms is not None and fetched_at_ms < observation_start_ms + base.EXTERNAL_SIGNAL_STAGE1_5G_LAUNCH_WARMUP_WINDOW_MS
                phase = "observation_initial" if is_warmup else "midrun"

            # Check validity
            is_crossed = _is_crossed_or_negative_book(r)
            is_empty = _is_empty_book_snapshot(r)

            if is_crossed or is_empty:
                # Invalid book
                invalid_book_row_count += 1
                curr_consec += 1
                if phase == "midrun":
                    curr_consec_after_warmup += 1
                else:
                    curr_consec_after_warmup = 0

                reason = ""
                if is_crossed:
                    reason = "crossed_or_negative_book"
                    crossed_or_negative_book_count += 1
                else:
                    # is_empty
                    if phase == "launch_warmup":
                        reason = "launch_warmup_empty_book"
                        launch_warmup_invalid_row_count += 1
                    elif phase == "observation_initial":
                        reason = "observation_initial_empty_book"
                    else:
                        reason = "midrun_empty_book"
                        midrun_invalid_book_count += 1

                invalid_book_by_phase[phase] += 1
                invalid_book_by_reason[reason] += 1

                # Keep copy of row and attach reason & phase
                quarantined_row = dict(r)
                quarantined_row["quarantine_reason"] = reason
                quarantined_row["quarantine_phase"] = phase
                quarantined_invalid_book_rows.append(quarantined_row)
            else:
                # Valid book
                depth_quality_input_rows.append(r)
                curr_consec = 0
                curr_consec_after_warmup = 0
                if first_valid_ts is None:
                    first_valid_ts = fetched_at_ms

            max_consecutive_invalid = max(max_consecutive_invalid, curr_consec)
            max_consecutive_invalid_after_warmup = max(max_consecutive_invalid_after_warmup, curr_consec_after_warmup)

        if first_valid_ts is not None:
            first_valid_book_ts_by_symbol[event_symbol_id] = first_valid_ts

    # Add schema invalid rows to quarantined_invalid_book_rows
    for r in schema_invalid_rows:
        quarantined_row = dict(r)
        quarantined_row["quarantine_reason"] = "schema_invalid"
        quarantined_row["quarantine_phase"] = "none"
        quarantined_invalid_book_rows.append(quarantined_row)
        invalid_book_by_reason["schema_invalid"] += 1
        invalid_book_row_count += 1

    # Let's count minute buckets for invalid rows
    # A minute bucket is identified by _minute_bucket_ms(fetched_at_ms)
    invalid_buckets = set()
    launch_warmup_invalid_buckets = set()
    midrun_invalid_buckets = set()

    for r in quarantined_invalid_book_rows:
        fetched_at_ms = r.get("fetched_at_ms")
        if fetched_at_ms is not None:
            bucket = _minute_bucket_ms(fetched_at_ms)
            invalid_buckets.add(bucket)
            phase = r.get("quarantine_phase")
            if phase == "launch_warmup":
                launch_warmup_invalid_buckets.add(bucket)
            elif phase == "midrun":
                midrun_invalid_buckets.add(bucket)

    invalid_book_minute_bucket_count = len(invalid_buckets)
    launch_warmup_invalid_minute_bucket_count = len(launch_warmup_invalid_buckets)
    midrun_invalid_minute_bucket_count = len(midrun_invalid_buckets)

    # First valid book latency
    first_valid_book_latency_ms = None
    if first_valid_book_ts_by_symbol:
        latencies = []
        for event_symbol_id, first_ts in first_valid_book_ts_by_symbol.items():
            anchor = launch_ts_by_symbol.get(event_symbol_id)
            if anchor is None:
                anchor = observation_start_ts_by_symbol.get(event_symbol_id)
            if anchor is not None:
                latencies.append(first_ts - anchor)
        if latencies:
            first_valid_book_latency_ms = max(latencies)

    observed_snapshot_count = len(snapshots)
    valid_snapshot_count_after_quarantine = len(depth_quality_input_rows)

    # Ratios
    invalid_book_ratio = invalid_book_row_count / observed_snapshot_count if observed_snapshot_count > 0 else 0.0
    invalid_book_ratio_observed = invalid_book_ratio
    book_availability_ratio = valid_snapshot_count_after_quarantine / expected_snapshot_count if expected_snapshot_count > 0 else 0.0
    book_unavailable_ratio = invalid_book_row_count / expected_snapshot_count if expected_snapshot_count > 0 else 0.0

    # Gates & Blockers
    if expected_snapshot_count <= 0:
        blockers.append("expected_snapshot_count_missing")
    else:
        if book_availability_ratio < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_BOOK_AVAILABILITY_RATIO:
            blockers.append("book_availability_ratio_below_threshold")

    if invalid_book_ratio > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_INVALID_BOOK_RATIO:
        blockers.append("invalid_book_ratio_above_threshold")

    if first_valid_book_latency_ms is not None and first_valid_book_latency_ms > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_FIRST_VALID_BOOK_LATENCY_MS:
        blockers.append("first_valid_book_latency_too_high")

    if launch_warmup_invalid_row_count > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_LAUNCH_WARMUP_INVALID_ROW_COUNT:
        blockers.append("launch_warmup_invalid_row_count_exceeded")

    if launch_warmup_invalid_minute_bucket_count > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_LAUNCH_WARMUP_INVALID_MINUTE_BUCKET_COUNT:
        blockers.append("launch_warmup_invalid_minute_bucket_count_exceeded")

    if observed_snapshot_count > 0 and (midrun_invalid_book_count / observed_snapshot_count) > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_MIDRUN_INVALID_BOOK_RATIO:
        blockers.append("midrun_invalid_book_ratio_exceeded")

    if midrun_invalid_book_count > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_MIDRUN_INVALID_BOOK_COUNT:
        blockers.append("midrun_invalid_book_count_exceeded")

    if max_consecutive_invalid_after_warmup > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_CONSECUTIVE_INVALID_AFTER_WARMUP:
        blockers.append("max_consecutive_invalid_after_warmup_exceeded")

    if valid_snapshot_count_after_quarantine < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_VALID_SNAPSHOTS_AFTER_QUARANTINE:
        blockers.append("valid_snapshot_count_after_quarantine_below_threshold")

    if crossed_or_negative_book_count > 0 and not base.EXTERNAL_SIGNAL_STAGE1_5G_CROSSED_OR_NEGATIVE_BOOK_ALLOWED:
        blockers.append("crossed_or_negative_book")

    if schema_invalid_count > 0:
        blockers.append("schema_invalid")

    clean_depth_evidence_pass = (invalid_book_row_count == 0) and (not blockers)
    quarantine_candidate = (invalid_book_row_count > 0) and (crossed_or_negative_book_count == 0) and (schema_invalid_count == 0)
    quarantined_depth_evidence_pass = quarantine_candidate and (not blockers)

    return RawSnapshotQuarantineResult(
        blockers=sorted(list(set(blockers))),
        warnings=sorted(list(set(warnings))),
        clean_depth_evidence_pass=clean_depth_evidence_pass,
        quarantined_depth_evidence_pass=quarantined_depth_evidence_pass,
        quarantine_candidate=quarantine_candidate,
        observed_snapshot_count=observed_snapshot_count,
        expected_snapshot_count=expected_snapshot_count,
        invalid_book_row_count=invalid_book_row_count,
        invalid_book_minute_bucket_count=invalid_book_minute_bucket_count,
        invalid_book_ratio=invalid_book_ratio,
        invalid_book_ratio_observed=invalid_book_ratio_observed,
        valid_snapshot_count_after_quarantine=valid_snapshot_count_after_quarantine,
        book_availability_ratio=book_availability_ratio,
        book_unavailable_ratio=book_unavailable_ratio,
        invalid_book_by_phase=invalid_book_by_phase,
        invalid_book_by_reason=invalid_book_by_reason,
        launch_warmup_invalid_row_count=launch_warmup_invalid_row_count,
        launch_warmup_invalid_minute_bucket_count=launch_warmup_invalid_minute_bucket_count,
        midrun_invalid_book_count=midrun_invalid_book_count,
        midrun_invalid_minute_bucket_count=midrun_invalid_minute_bucket_count,
        crossed_or_negative_book_count=crossed_or_negative_book_count,
        schema_invalid_count=schema_invalid_count,
        max_consecutive_invalid=max_consecutive_invalid,
        max_consecutive_invalid_after_warmup=max_consecutive_invalid_after_warmup,
        first_valid_book_latency_ms=first_valid_book_latency_ms,
        depth_quality_input_rows=depth_quality_input_rows,
        quarantined_invalid_book_rows=quarantined_invalid_book_rows,
    )


def validate_raw_snapshot_integrity(

    snapshots: list[dict],
    parse_error_count: int = 0,
    total_jsonl_line_count: int = 0,
) -> RawSnapshotIntegrityResult:
    from configs import base

    blockers: list[str] = []
    warnings: list[str] = []

    # 1. JSONL Parse Errors
    jsonl_parse_error_ratio = 0.0
    if parse_error_count > 0:
        blockers.append("jsonl_parse_error")
        if total_jsonl_line_count > 0:
            jsonl_parse_error_ratio = parse_error_count / total_jsonl_line_count

    # Group snapshots by event_symbol_id
    snapshots_by_symbol: dict[str, list[dict]] = {}
    for sn in snapshots:
        es_id = sn.get("event_symbol_id") or "unknown"
        snapshots_by_symbol.setdefault(es_id, []).append(sn)

    # 2. Crossed Books & Null Ratio & Duplicates & Monotonicity & Symbol Conflict
    invalid_book_count = 0
    non_monotonic_timestamp_count = 0
    null_ratio_max = 0.0
    duplicate_snapshot_ratio_max = 0.0

    symbol_mapping: dict[str, set[str]] = {}

    required_fields = ["event_symbol_id", "symbol", "fetched_at_ms", "best_bid", "best_ask", "spread_bps"]

    for es_id, sym_snapshots in snapshots_by_symbol.items():
        # Keep track of mapping event_symbol_id -> symbol
        for sn in sym_snapshots:
            sym = sn.get("symbol")
            if sym:
                symbol_mapping.setdefault(es_id, set()).add(sym)

        # Check crossed books
        for sn in sym_snapshots:
            bid = sn.get("best_bid")
            ask = sn.get("best_ask")
            mid = sn.get("mid_price")
            spread = sn.get("spread_bps")
            if mid is None and bid is not None and ask is not None:
                mid = (float(bid) + float(ask)) / 2.0

            is_invalid = False
            if bid is None or ask is None or mid is None or spread is None:
                is_invalid = True
            elif bid <= 0 or ask <= 0 or mid <= 0 or spread < 0 or bid >= ask:
                is_invalid = True

            if is_invalid:
                invalid_book_count += 1

        # Check Monotonicity of fetched_at_ms (as loaded in file sequence)
        last_t = None
        for sn in sym_snapshots:
            t = sn.get("fetched_at_ms")
            if t is not None:
                if last_t is not None and t < last_t:
                    non_monotonic_timestamp_count += 1
                last_t = t

        # Calculate null ratio for this symbol
        total_fields = len(sym_snapshots) * len(required_fields)
        null_fields = 0
        for sn in sym_snapshots:
            for f in required_fields:
                if sn.get(f) is None:
                    null_fields += 1
        null_ratio = null_fields / total_fields if total_fields > 0 else 0.0
        if null_ratio > null_ratio_max:
            null_ratio_max = null_ratio

        # Calculate duplicate ratio for this symbol
        # Duplicates by (event_symbol_id, fetched_at_ms, best_bid, best_ask)
        unique_keys = set()
        for sn in sym_snapshots:
            k = (
                sn.get("event_symbol_id"),
                sn.get("fetched_at_ms"),
                sn.get("best_bid"),
                sn.get("best_ask"),
            )
            unique_keys.add(k)
        total_rows = len(sym_snapshots)
        dup_rows = total_rows - len(unique_keys)
        dup_ratio = dup_rows / total_rows if total_rows > 0 else 0.0
        if dup_ratio > duplicate_snapshot_ratio_max:
            duplicate_snapshot_ratio_max = dup_ratio

    # Emit blockers
    if invalid_book_count > 0:
        blockers.append("invalid_book")

    if non_monotonic_timestamp_count > 0:
        blockers.append("non_monotonic_timestamp")

    for es_id, symbols in symbol_mapping.items():
        if len(symbols) > 1:
            blockers.append("symbol_event_symbol_id_mapping_conflict")
            break

    if null_ratio_max > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_NULL_RATIO:
        blockers.append("null_ratio_above_threshold")

    if duplicate_snapshot_ratio_max > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_DUPLICATE_SNAPSHOT_RATIO:
        blockers.append("duplicate_snapshot_ratio_above_threshold")

    return RawSnapshotIntegrityResult(
        blockers=sorted(list(set(blockers))),
        warnings=warnings,
        null_ratio_max=null_ratio_max,
        jsonl_parse_error_ratio=jsonl_parse_error_ratio,
        jsonl_parse_error_count=parse_error_count,
        duplicate_snapshot_ratio_max=duplicate_snapshot_ratio_max,
        non_monotonic_timestamp_count=non_monotonic_timestamp_count,
        invalid_book_count=invalid_book_count,
    )


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * pct
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return sorted_vals[-1]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1


def compute_depth_quality_metrics(snapshots: list[dict]) -> dict:
    from configs import base

    blockers: list[str] = []
    warnings: list[str] = []

    if not snapshots:
        return {
            "spread_bps_p50": None,
            "spread_bps_p95": None,
            "buy_slippage_bps_500usdt_p50": None,
            "buy_slippage_bps_500usdt_p95": None,
            "sell_slippage_bps_500usdt_p50": None,
            "sell_slippage_bps_500usdt_p95": None,
            "top_bid_depth_usdt_p05": None,
            "top_bid_depth_usdt_p50": None,
            "top_ask_depth_usdt_p05": None,
            "top_ask_depth_usdt_p50": None,
            "healthy_window_ratio": 0.0,
            "depth_capacity_ratio_to_risk_cap_p50": 0.0,
            "blockers": ["no_depth_snapshots_collected"],
            "warnings": warnings,
        }

    spreads = [s.get("spread_bps") for s in snapshots if s.get("spread_bps") is not None]
    buy_slips = [s.get("buy_slippage_bps") for s in snapshots if s.get("buy_slippage_bps") is not None]
    sell_slips = [s.get("sell_slippage_bps") for s in snapshots if s.get("sell_slippage_bps") is not None]
    bid_depths = [s.get("top_bid_depth_usdt") for s in snapshots if s.get("top_bid_depth_usdt") is not None]
    ask_depths = [s.get("top_ask_depth_usdt") for s in snapshots if s.get("top_ask_depth_usdt") is not None]

    spread_bps_p50 = percentile(spreads, 0.50)
    spread_bps_p95 = percentile(spreads, 0.95)
    buy_slippage_bps_500usdt_p50 = percentile(buy_slips, 0.50)
    buy_slippage_bps_500usdt_p95 = percentile(buy_slips, 0.95)
    sell_slippage_bps_500usdt_p50 = percentile(sell_slips, 0.50)
    sell_slippage_bps_500usdt_p95 = percentile(sell_slips, 0.95)
    top_bid_depth_usdt_p05 = percentile(bid_depths, 0.05)
    top_bid_depth_usdt_p50 = percentile(bid_depths, 0.50)
    top_ask_depth_usdt_p05 = percentile(ask_depths, 0.05)
    top_ask_depth_usdt_p50 = percentile(ask_depths, 0.50)

    # Calculate healthy window ratio
    healthy_count = 0
    for s in snapshots:
        spr = s.get("spread_bps")
        bsl = s.get("buy_slippage_bps")
        ssl = s.get("sell_slippage_bps")
        tbd = s.get("top_bid_depth_usdt")
        tad = s.get("top_ask_depth_usdt")

        is_healthy = True
        if spr is None or spr > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_SPREAD_BPS_P95:
            is_healthy = False
        if bsl is None or bsl > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_BUY_SLIPPAGE_BPS_P95:
            is_healthy = False
        if ssl is None or ssl > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_SELL_SLIPPAGE_BPS_P95:
            is_healthy = False
        if tbd is None or tbd < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_BID_DEPTH_USDT_P05:
            is_healthy = False
        if tad is None or tad < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_ASK_DEPTH_USDT_P05:
            is_healthy = False

        if is_healthy:
            healthy_count += 1

    healthy_window_ratio = healthy_count / len(snapshots)

    # depth capacity ratio: min(top_bid_depth_usdt_p50, top_ask_depth_usdt_p50) / 500.0
    min_mid_depth = 0.0
    if top_bid_depth_usdt_p50 is not None and top_ask_depth_usdt_p50 is not None:
        min_mid_depth = min(top_bid_depth_usdt_p50, top_ask_depth_usdt_p50)
    depth_capacity_ratio = min_mid_depth / base.EXTERNAL_SIGNAL_STAGE1_5G_SLIPPAGE_TEST_NOTIONAL_USDT

    # Check thresholds and add blockers
    if spread_bps_p50 is not None and spread_bps_p50 > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_SPREAD_BPS_P50:
        blockers.append("spread_p50_above_threshold")
    if spread_bps_p95 is not None and spread_bps_p95 > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_SPREAD_BPS_P95:
        blockers.append("spread_p95_above_threshold")
    if buy_slippage_bps_500usdt_p50 is not None and buy_slippage_bps_500usdt_p50 > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_BUY_SLIPPAGE_BPS_P50:
        blockers.append("buy_slippage_p50_above_threshold")
    if buy_slippage_bps_500usdt_p95 is not None and buy_slippage_bps_500usdt_p95 > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_BUY_SLIPPAGE_BPS_P95:
        blockers.append("buy_slippage_p95_above_threshold")
    if sell_slippage_bps_500usdt_p50 is not None and sell_slippage_bps_500usdt_p50 > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_SELL_SLIPPAGE_BPS_P50:
        blockers.append("sell_slippage_p50_above_threshold")
    if sell_slippage_bps_500usdt_p95 is not None and sell_slippage_bps_500usdt_p95 > base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_SELL_SLIPPAGE_BPS_P95:
        blockers.append("sell_slippage_p95_above_threshold")
    if top_bid_depth_usdt_p05 is not None and top_bid_depth_usdt_p05 < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_BID_DEPTH_USDT_P05:
        blockers.append("top_bid_depth_p05_below_threshold")
    if top_bid_depth_usdt_p50 is not None and top_bid_depth_usdt_p50 < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_BID_DEPTH_USDT_P50:
        blockers.append("top_bid_depth_p50_below_threshold")
    if top_ask_depth_usdt_p05 is not None and top_ask_depth_usdt_p05 < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_ASK_DEPTH_USDT_P05:
        blockers.append("top_ask_depth_p05_below_threshold")
    if top_ask_depth_usdt_p50 is not None and top_ask_depth_usdt_p50 < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_ASK_DEPTH_USDT_P50:
        blockers.append("top_ask_depth_p50_below_threshold")
    if healthy_window_ratio < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_HEALTHY_WINDOW_RATIO:
        blockers.append("healthy_window_ratio_below_threshold")

    return {
        "spread_bps_p50": spread_bps_p50,
        "spread_bps_p95": spread_bps_p95,
        "buy_slippage_bps_500usdt_p50": buy_slippage_bps_500usdt_p50,
        "buy_slippage_bps_500usdt_p95": buy_slippage_bps_500usdt_p95,
        "sell_slippage_bps_500usdt_p50": sell_slippage_bps_500usdt_p50,
        "sell_slippage_bps_500usdt_p95": sell_slippage_bps_500usdt_p95,
        "top_bid_depth_usdt_p05": top_bid_depth_usdt_p05,
        "top_bid_depth_usdt_p50": top_bid_depth_usdt_p50,
        "top_ask_depth_usdt_p05": top_ask_depth_usdt_p05,
        "top_ask_depth_usdt_p50": top_ask_depth_usdt_p50,
        "healthy_window_ratio": healthy_window_ratio,
        "depth_capacity_ratio_to_risk_cap_p50": depth_capacity_ratio,
        "blockers": sorted(list(set(blockers))),
        "warnings": warnings,
    }


def compute_quarantined_depth_quality(quarantine_result: RawSnapshotQuarantineResult) -> dict:
    quality = compute_depth_quality_metrics(quarantine_result.depth_quality_input_rows)
    return {
        "depth_quality_clean_mode_available": False,
        "depth_quality_quarantined_mode_available": True,
        "quarantined_depth_quality": {
            **quality,
            "input_valid_rows": quarantine_result.valid_snapshot_count_after_quarantine,
            "excluded_invalid_rows": quarantine_result.invalid_book_row_count,
        },
        "book_availability_quality": {
            "availability_ratio": quarantine_result.book_availability_ratio,
            "unavailable_ratio": quarantine_result.book_unavailable_ratio,
            "max_consecutive_invalid": quarantine_result.max_consecutive_invalid,
            "max_consecutive_invalid_after_warmup": quarantine_result.max_consecutive_invalid_after_warmup,
            "first_valid_book_latency_ms": quarantine_result.first_valid_book_latency_ms,
        },
        "depth_quality_input_mode": "quarantined_valid_rows",
        "depth_quality_input_row_count": quarantine_result.valid_snapshot_count_after_quarantine,
        "excluded_invalid_book_row_count": quarantine_result.invalid_book_row_count,
        "blockers": quality.get("blockers", []),
        "warnings": quality.get("warnings", []),
    }



def _build_event_level_decisions(
    accepted_events: list[dict],
    states: list[dict],
    formal_completed_event_symbol_ids: set[str] | None = None,
) -> list[dict]:
    formal_ids = formal_completed_event_symbol_ids or set()
    state_by_id = {
        st.get("event_symbol_id"): st
        for st in states
        if st.get("event_symbol_id")
    }
    decisions = []
    for event in accepted_events:
        es_id = event.get("event_symbol_id")
        st = state_by_id.get(es_id, {})
        decisions.append(
            {
                "event_symbol_id": es_id,
                "event_id": event.get("event_id"),
                "symbol": event.get("symbol"),
                "source_article_id": event.get("source_article_id"),
                "evidence_label": get_event_evidence_label(event),
                "state_status": st.get("status"),
                "depth_snapshot_count": st.get("depth_snapshot_count", 0),
                "formal_completed": es_id in formal_ids,
            }
        )
    return decisions


def _with_stage1_5g_audit_fields(
    result: dict,
    *,
    output_root: str | Path | None,
    watermark: dict,
    accepted_events: list[dict],
    states: list[dict],
    formal_completed_event_symbol_ids: set[str] | None = None,
) -> dict:
    reviewed_event_symbols = sorted(
        {
            event.get("event_symbol_id")
            for event in accepted_events
            if event.get("event_symbol_id")
        }
    )
    enriched = {
        "config_version": "configs/base.py:EXTERNAL_SIGNAL_STAGE1_5G_*",
        "stage1_5f_output_root": str(output_root) if output_root is not None else "",
        "watermark_max_seen_detected_at_ms": watermark.get("max_seen_detected_at_ms") if watermark else None,
        "reviewed_event_symbols": reviewed_event_symbols,
        "event_level_decisions": _build_event_level_decisions(
            accepted_events,
            states,
            formal_completed_event_symbol_ids=formal_completed_event_symbol_ids,
        ),
    }
    enriched.update(result)
    return enriched


def summarize_raw_snapshot_quarantine_result(quarantine_result: RawSnapshotQuarantineResult) -> dict:
    return {
        "blockers": quarantine_result.blockers,
        "warnings": quarantine_result.warnings,
        "clean_depth_evidence_pass": quarantine_result.clean_depth_evidence_pass,
        "quarantined_depth_evidence_pass": quarantine_result.quarantined_depth_evidence_pass,
        "quarantine_candidate": quarantine_result.quarantine_candidate,
        "observed_snapshot_count": quarantine_result.observed_snapshot_count,
        "expected_snapshot_count": quarantine_result.expected_snapshot_count,
        "invalid_book_row_count": quarantine_result.invalid_book_row_count,
        "invalid_book_minute_bucket_count": quarantine_result.invalid_book_minute_bucket_count,
        "invalid_book_ratio": quarantine_result.invalid_book_ratio,
        "invalid_book_ratio_observed": quarantine_result.invalid_book_ratio_observed,
        "valid_snapshot_count_after_quarantine": quarantine_result.valid_snapshot_count_after_quarantine,
        "book_availability_ratio": quarantine_result.book_availability_ratio,
        "book_unavailable_ratio": quarantine_result.book_unavailable_ratio,
        "invalid_book_by_phase": quarantine_result.invalid_book_by_phase,
        "invalid_book_by_reason": quarantine_result.invalid_book_by_reason,
        "launch_warmup_invalid_row_count": quarantine_result.launch_warmup_invalid_row_count,
        "launch_warmup_invalid_minute_bucket_count": quarantine_result.launch_warmup_invalid_minute_bucket_count,
        "midrun_invalid_book_count": quarantine_result.midrun_invalid_book_count,
        "midrun_invalid_minute_bucket_count": quarantine_result.midrun_invalid_minute_bucket_count,
        "crossed_or_negative_book_count": quarantine_result.crossed_or_negative_book_count,
        "schema_invalid_count": quarantine_result.schema_invalid_count,
        "max_consecutive_invalid": quarantine_result.max_consecutive_invalid,
        "max_consecutive_invalid_after_warmup": quarantine_result.max_consecutive_invalid_after_warmup,
        "first_valid_book_latency_ms": quarantine_result.first_valid_book_latency_ms,
        "depth_quality_input_row_count": len(quarantine_result.depth_quality_input_rows),
        "quarantined_invalid_book_row_count": len(quarantine_result.quarantined_invalid_book_rows),
    }


def write_stage1_5g_quarantine_artifacts(review_output_root: Path, quarantine_result: RawSnapshotQuarantineResult) -> dict[str, str]:
    review_output_root.mkdir(parents=True, exist_ok=True)
    invalid_path = review_output_root / "quarantined_invalid_book_rows.jsonl"
    valid_path = review_output_root / "depth_quality_input_rows.jsonl"
    summary_path = review_output_root / "stage1_5g_quarantine_summary.json"

    with invalid_path.open("w", encoding="utf-8") as fh:
        for row in quarantine_result.quarantined_invalid_book_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    with valid_path.open("w", encoding="utf-8") as fh:
        for row in quarantine_result.depth_quality_input_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summarize_raw_snapshot_quarantine_result(quarantine_result), fh, indent=2, ensure_ascii=False)

    return {
        "quarantined_rows_path": str(invalid_path),
        "depth_quality_input_rows_path": str(valid_path),
        "quarantine_summary_path": str(summary_path),
    }


def build_stage1_5g_review_summary(
    summary: dict,
    watermark: dict,
    states: list[dict],
    accepted_events: list[dict],
    snapshots: list[dict],
    request_manifest_rows: list[dict],
    output_root: str | Path | None = None,
    loader_blockers: list[str] | None = None,
    *,
    review_output_root: str | Path | None = None,
) -> dict:
    """
    Build Stage 1.5G review summary.

    :param output_root: Stage 1.5F source artifact root (read-only audit provenance).
    :param review_output_root: Stage 1.5G review output root (where derived quarantine artifacts may be written).
    """
    from configs import base

    all_blockers: list[str] = []
    all_warnings: list[str] = []

    if loader_blockers:
        all_blockers.extend(loader_blockers)

    def finish(result: dict, formal_completed_event_symbol_ids: set[str] | None = None) -> dict:
        return _with_stage1_5g_audit_fields(
            result,
            output_root=output_root,
            watermark=watermark,
            accepted_events=accepted_events,
            states=states,
            formal_completed_event_symbol_ids=formal_completed_event_symbol_ids,
        )

    # 1. Loader Blockers Check
    if any(b in all_blockers for b in ["jsonl_parse_error", "missing_or_unreadable_summary", "duplicate_stable_event_symbol_identity"]):
        return finish({
            "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
            "decision": "stage1_5g_depth_evidence_invalid",
            "allowed_next_action": "continue_observation",
            "evidence_scope": "none",
            "event_family_conclusion_allowed": False,
            "blockers": sorted(list(set(all_blockers))),
            "warnings": all_warnings,
            "evidence_label_counts": {},
            "formal_announcement_and_launch_count": 0,
            "trade_signal_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
            "execution_feasibility_claim_allowed": False,
        })

    # 2. Watermark Presence Check
    if not watermark or "watermark_version" not in watermark:
        all_blockers.append("missing_or_unreadable_watermark")
        return finish({
            "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
            "decision": "stage1_5g_depth_evidence_invalid",
            "allowed_next_action": "continue_observation",
            "evidence_scope": "none",
            "event_family_conclusion_allowed": False,
            "blockers": sorted(list(set(all_blockers))),
            "warnings": all_warnings,
            "evidence_label_counts": {},
            "formal_announcement_and_launch_count": 0,
            "trade_signal_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
            "execution_feasibility_claim_allowed": False,
        })

    # 3. Evidence Integrity Validator
    integrity_result = validate_evidence_integrity(
        accepted_events=accepted_events,
        watermark=watermark,
        states=states,
        snapshots=snapshots,
        summary=summary,
    )
    ANCHOR_LINEAGE_INVALID_BLOCKERS = {
        "anchor_contract_lineage_state_missing",
        "anchor_contract_lineage_mismatch",
        "anchor_revision_contaminated",
        "malformed_anchor_contract",
        "exchangeinfo_fallback_anchor",
        "exchangeinfo_fallback_clean_claim",
    }
    has_anchor_lineage_blocker = bool(set(integrity_result.blockers).intersection(ANCHOR_LINEAGE_INVALID_BLOCKERS))

    if integrity_result.blockers:
        all_blockers.extend(integrity_result.blockers)
        if has_anchor_lineage_blocker:
            return finish({
                "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
                "decision": "stage1_5g_depth_evidence_invalid",
                "allowed_next_action": "collect_official_anchor_evidence_or_wait_for_next_event",
                "evidence_scope": "none",
                "event_family_conclusion_allowed": False,
                "clean_depth_evidence_pass": False,
                "quarantined_depth_evidence_pass": False,
                "quarantine_candidate": False,
                "blockers": sorted(list(set(all_blockers))),
                "warnings": all_warnings,
                "evidence_label_counts": integrity_result.evidence_label_counts,
                "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
                "trade_signal_allowed": False,
                "paper_trading_allowed": False,
                "live_trading_allowed": False,
                "execution_engine_allowed": False,
                "alpha_interpretation_allowed": False,
                "execution_feasibility_claim_allowed": False,
            }, set())
        else:
            return finish({
                "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
                "decision": "stage1_5g_depth_evidence_invalid",
                "allowed_next_action": "recollect_events_or_fix_data_source",
                "evidence_scope": "none",
                "event_family_conclusion_allowed": False,
                "clean_depth_evidence_pass": False,
                "quarantined_depth_evidence_pass": False,
                "quarantine_candidate": False,
                "blockers": sorted(list(set(all_blockers))),
                "warnings": all_warnings,
                "evidence_label_counts": integrity_result.evidence_label_counts,
                "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
                "trade_signal_allowed": False,
                "paper_trading_allowed": False,
                "live_trading_allowed": False,
                "execution_engine_allowed": False,
                "alpha_interpretation_allowed": False,
                "execution_feasibility_claim_allowed": False,
            }, set())

    # 4. Completed Observation Manifest Check
    completed_obs_count = summary.get("completed_observation_count", 0)
    if completed_obs_count > 0 and not request_manifest_rows:
        all_blockers.append("missing_request_manifest_for_completed_observation")
        return finish({
            "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
            "decision": "stage1_5g_depth_evidence_invalid",
            "allowed_next_action": "continue_observation",
            "evidence_scope": "none",
            "event_family_conclusion_allowed": False,
            "blockers": sorted(list(set(all_blockers))),
            "warnings": all_warnings,
            "evidence_label_counts": integrity_result.evidence_label_counts,
            "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
            "trade_signal_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
            "execution_feasibility_claim_allowed": False,
        }, integrity_result.formal_completed_event_symbol_ids)

    # 5. Not Ready Check (no completed observations)
    if completed_obs_count == 0:
        return finish({
            "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
            "decision": "stage1_5g_not_ready_no_completed_observation",
            "allowed_next_action": "continue_observation",
            "evidence_scope": "none",
            "event_family_conclusion_allowed": False,
            "blockers": sorted(list(set(all_blockers))),
            "warnings": all_warnings,
            "evidence_label_counts": integrity_result.evidence_label_counts,
            "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
            "trade_signal_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
            "execution_feasibility_claim_allowed": False,
        }, integrity_result.formal_completed_event_symbol_ids)

    # 6. Coverage & Per-Symbol Health Check
    coverage_result = compute_coverage_metrics(
        states=states,
        request_manifest_rows=request_manifest_rows,
        summary=summary,
        event_symbol_ids=integrity_result.formal_completed_event_symbol_ids,
    )
    if coverage_result["blockers"]:
        all_blockers.extend(coverage_result["blockers"])
        return finish({
            "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
            "decision": "stage1_5g_depth_evidence_invalid",
            "allowed_next_action": "continue_observation",
            "evidence_scope": "none",
            "event_family_conclusion_allowed": False,
            "blockers": sorted(list(set(all_blockers))),
            "warnings": all_warnings,
            "evidence_label_counts": integrity_result.evidence_label_counts,
            "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
            "trade_signal_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
            "execution_feasibility_claim_allowed": False,
            "coverage_metrics": coverage_result,
        }, integrity_result.formal_completed_event_symbol_ids)

    # 7. Raw Snapshot Integrity Check
    raw_integrity_result = validate_raw_snapshot_integrity(
        snapshots=snapshots,
        parse_error_count=summary.get("parse_error_count", 0),  # passed down from bundle if available
        total_jsonl_line_count=summary.get("total_jsonl_line_count", 0),
    )

    expected_snapshot_count = coverage_result.get("expected_snapshot_count", 0)
    quarantine_result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=states,
        accepted_events=accepted_events,
        expected_snapshot_count=expected_snapshot_count,
    )

    has_invalid_book = (raw_integrity_result.invalid_book_count > 0)
    raw_integrity_blockers_other_than_invalid = [b for b in raw_integrity_result.blockers if b != "invalid_book"]

    # Write quarantine artifacts if there are invalid rows and output root is given
    quarantine_dict = summarize_raw_snapshot_quarantine_result(quarantine_result) if quarantine_result else {}
    if quarantine_result and quarantine_result.invalid_book_row_count > 0 and review_output_root is not None:
        from pathlib import Path
        paths = write_stage1_5g_quarantine_artifacts(Path(review_output_root), quarantine_result)
        quarantine_dict.update(paths)

    # 7a. Hard Fail on raw integrity other than invalid_book
    if raw_integrity_blockers_other_than_invalid:
        all_blockers.extend(raw_integrity_blockers_other_than_invalid)
        if has_invalid_book:
            all_blockers.append("invalid_book")
        return finish({
            "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
            "decision": "stage1_5g_depth_evidence_invalid",
            "allowed_next_action": "continue_observation",
            "evidence_scope": "none",
            "event_family_conclusion_allowed": False,
            "blockers": sorted(list(set(all_blockers))),
            "warnings": all_warnings,
            "evidence_label_counts": integrity_result.evidence_label_counts,
            "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
            "trade_signal_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
            "execution_feasibility_claim_allowed": False,
            "coverage_metrics": coverage_result,
            "raw_integrity": raw_integrity_result.__dict__,
            "quarantine": quarantine_dict,
        }, integrity_result.formal_completed_event_symbol_ids)

    # 7b. If invalid_book exists and quarantine has blockers, it's invalid
    if has_invalid_book and not quarantine_result.quarantined_depth_evidence_pass:
        all_blockers.extend(quarantine_result.blockers)
        if "invalid_book" not in all_blockers:
            all_blockers.append("invalid_book")
        return finish({
            "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
            "decision": "stage1_5g_depth_evidence_invalid",
            "allowed_next_action": "continue_observation",
            "evidence_scope": "none",
            "event_family_conclusion_allowed": False,
            "blockers": sorted(list(set(all_blockers))),
            "warnings": all_warnings,
            "evidence_label_counts": integrity_result.evidence_label_counts,
            "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
            "trade_signal_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
            "execution_feasibility_claim_allowed": False,
            "coverage_metrics": coverage_result,
            "raw_integrity": raw_integrity_result.__dict__,
            "quarantine": quarantine_dict,
        }, integrity_result.formal_completed_event_symbol_ids)

    # 8. No Completed Formal Evidence Check
    if integrity_result.formal_announcement_and_launch_count == 0:
        if has_invalid_book:
            depth_quality_result = compute_quarantined_depth_quality(quarantine_result)
        else:
            quality = compute_depth_quality_metrics(snapshots)
            depth_quality_result = {
                **quality,
                "depth_quality_clean_mode_available": True,
                "depth_quality_quarantined_mode_available": False,
                "depth_quality_input_mode": "clean_all_rows",
                "depth_quality_input_row_count": len(snapshots),
                "excluded_invalid_book_row_count": 0,
            }

        return finish({
            "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
            "decision": "stage1_5g_depth_evidence_observation_only",
            "allowed_next_action": "continue_observation",
            "evidence_scope": "none",
            "event_family_conclusion_allowed": False,
            "blockers": sorted(list(set(all_blockers))),
            "warnings": all_warnings,
            "evidence_label_counts": integrity_result.evidence_label_counts,
            "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
            "trade_signal_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
            "execution_feasibility_claim_allowed": False,
            "coverage_metrics": coverage_result,
            "raw_integrity": raw_integrity_result.__dict__,
            "quarantine": quarantine_dict,
            "depth_quality": depth_quality_result,
        }, integrity_result.formal_completed_event_symbol_ids)

    # 9. Depth Quality Check
    if has_invalid_book:
        depth_quality_result = compute_quarantined_depth_quality(quarantine_result)
    else:
        quality = compute_depth_quality_metrics(snapshots)
        depth_quality_result = {
            **quality,
            "depth_quality_clean_mode_available": True,
            "depth_quality_quarantined_mode_available": False,
            "depth_quality_input_mode": "clean_all_rows",
            "depth_quality_input_row_count": len(snapshots),
            "excluded_invalid_book_row_count": 0,
        }

    # If depth quality blockers exists:
    if depth_quality_result.get("blockers"):
        if has_invalid_book:
            all_blockers.extend(depth_quality_result["blockers"])
            return finish({
                "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
                "decision": "stage1_5g_depth_evidence_invalid",
                "allowed_next_action": "continue_observation",
                "evidence_scope": "none",
                "event_family_conclusion_allowed": False,
                "blockers": sorted(list(set(all_blockers))),
                "warnings": all_warnings,
                "evidence_label_counts": integrity_result.evidence_label_counts,
                "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
                "trade_signal_allowed": False,
                "paper_trading_allowed": False,
                "live_trading_allowed": False,
                "execution_engine_allowed": False,
                "alpha_interpretation_allowed": False,
                "execution_feasibility_claim_allowed": False,
                "coverage_metrics": coverage_result,
                "raw_integrity": raw_integrity_result.__dict__,
                "quarantine": quarantine_dict,
                "depth_quality": depth_quality_result,
            }, integrity_result.formal_completed_event_symbol_ids)
        else:
            all_blockers.extend(depth_quality_result["blockers"])
            return finish({
                "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
                "decision": "stage1_5g_depth_evidence_observation_only",
                "allowed_next_action": "continue_observation",
                "evidence_scope": "none",
                "event_family_conclusion_allowed": False,
                "blockers": sorted(list(set(all_blockers))),
                "warnings": all_warnings,
                "evidence_label_counts": integrity_result.evidence_label_counts,
                "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
                "trade_signal_allowed": False,
                "paper_trading_allowed": False,
                "live_trading_allowed": False,
                "execution_engine_allowed": False,
                "alpha_interpretation_allowed": False,
                "execution_feasibility_claim_allowed": False,
                "coverage_metrics": coverage_result,
                "raw_integrity": raw_integrity_result.__dict__,
                "depth_quality": depth_quality_result,
            }, integrity_result.formal_completed_event_symbol_ids)

    # 10. Sufficient Check and Scope Determination
    formal_ids = integrity_result.formal_completed_event_symbol_ids
    unique_symbols = set()
    unique_articles = set()

    for event in accepted_events:
        es_id = event.get("event_symbol_id")
        if es_id in formal_ids:
            sym = event.get("symbol")
            art = event.get("source_article_id")
            if sym:
                unique_symbols.add(sym)
            if art:
                unique_articles.add(art)

    event_family_conclusion_allowed = False
    evidence_scope = "single_event"

    if (
        len(unique_symbols) >= base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_EVENT_FAMILY_SAMPLE_REQUIRED
        and len(unique_articles) >= base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_SOURCE_ARTICLES_REQUIRED
    ):
        event_family_conclusion_allowed = True
        evidence_scope = "event_family"

    if has_invalid_book:
        decision = "stage1_5g_depth_evidence_quarantined_pass"
        allowed_next_action = "write_stage1_5h_design_only"
        clean_pass_val = False
        quarantined_pass_val = True
        quarantine_candidate_val = True
    else:
        decision = "stage1_5g_depth_evidence_clean_pass"
        allowed_next_action = "write_stage1_5h_design_or_shadow_simulator_design"
        clean_pass_val = True
        quarantined_pass_val = False
        quarantine_candidate_val = False

    return finish({
        "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
        "decision": decision,
        "allowed_next_action": allowed_next_action,
        "clean_depth_evidence_pass": clean_pass_val,
        "quarantined_depth_evidence_pass": quarantined_pass_val,
        "quarantine_candidate": quarantine_candidate_val,
        "evidence_scope": evidence_scope,
        "event_family_conclusion_allowed": event_family_conclusion_allowed,
        "blockers": sorted(list(set(all_blockers))),
        "warnings": all_warnings,
        "evidence_label_counts": integrity_result.evidence_label_counts,
        "formal_announcement_and_launch_count": integrity_result.formal_announcement_and_launch_count,
        "stage1_5h_implementation_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "execution_feasibility_claim_allowed": False,
        "coverage_metrics": coverage_result,
        "raw_integrity": raw_integrity_result.__dict__,
        "quarantine": quarantine_dict,
        "depth_quality": depth_quality_result,
    }, integrity_result.formal_completed_event_symbol_ids)



def generate_stage1_5g_chinese_review(summary: dict) -> str:
    decision = summary.get("decision", "unknown")
    allowed_next_action = summary.get("allowed_next_action", "unknown")
    blockers = summary.get("blockers", [])
    warnings = summary.get("warnings", [])

    coverage = summary.get("coverage_metrics", {})
    raw_integrity = summary.get("raw_integrity", {})
    depth_quality = summary.get("depth_quality", {})
    labels = summary.get("evidence_label_counts", {})

    lines = []
    lines.append("# Stage 1.5G Live Depth Evidence Review Report")
    lines.append("")
    lines.append(f"**审计结论 (Decision):** `{decision}`")
    lines.append(f"**允许的下一步行动 (Allowed Next Action):** `{allowed_next_action}`")
    lines.append(f"**证据范围 (Evidence Scope):** `{summary.get('evidence_scope')}`")
    lines.append(f"**是否允许推导家族级结论 (Event-Family Conclusion Allowed):** `{summary.get('event_family_conclusion_allowed')}`")
    lines.append("")

    lines.append("## 1. 安全边界审计 (Safety Boundaries)")
    lines.append("")
    lines.append("| 安全控制项 (Safety Item) | 状态 (Status) |")
    lines.append("| --- | --- |")
    lines.append(f"| 实盘下单 (trade_signal_allowed) | `{summary.get('trade_signal_allowed')}` |")
    lines.append(f"| 模拟盘下单 (paper_trading_allowed) | `{summary.get('paper_trading_allowed')}` |")
    lines.append(f"| 实盘交易 (live_trading_allowed) | `{summary.get('live_trading_allowed')}` |")
    lines.append(f"| 执行引擎介入 (execution_engine_allowed) | `{summary.get('execution_engine_allowed')}` |")
    lines.append(f"| Alpha判定解释 (alpha_interpretation_allowed) | `{summary.get('alpha_interpretation_allowed')}` |")
    lines.append(f"| 执行可行性确认 (execution_feasibility_claim_allowed) | `{summary.get('execution_feasibility_claim_allowed')}` |")
    lines.append("")

    lines.append("## 2. 阻断器与警告 (Blockers & Warnings)")
    lines.append("")
    if blockers:
        lines.append("### 阻断项 (Blockers):")
        for b in blockers:
            lines.append(f"- :x: `{b}`")
    else:
        lines.append("- :white_check_mark: 无阻断项 (No blockers)")
    lines.append("")
    if warnings:
        lines.append("### 警告项 (Warnings):")
        for w in warnings:
            lines.append(f"- :warning: `{w}`")
    lines.append("")

    lines.append("## 3. 水印审计与证据分类 (Watermark & Evidence Labels)")
    lines.append("")
    lines.append(f"- **正式证据数量 (Formal announcement_and_launch_time count):** `{summary.get('formal_announcement_and_launch_count')}`")
    lines.append("- **各证据标签统计 (Evidence label counts):**")
    for k, v in labels.items():
        lines.append(f"  - `{k}`: {v}")
    lines.append("")

    lines.append("## 4. 覆盖率与请求健康度审计 (Coverage & Request Health)")
    lines.append("")
    if coverage:
        lines.append(f"- **预估快照总数 (Expected snapshot count):** `{coverage.get('expected_snapshot_count')}`")
        lines.append(f"- **要求的最低快照数 (Min snapshot count required):** `{coverage.get('min_snapshot_count_required')}`")
        lines.append(f"- **快照采样间隔 (Snapshot interval ms):** `{coverage.get('snapshot_interval_ms')} ms`")
        lines.append(f"- **最大快照间隔时间 (Computed max gap allowed):** `{coverage.get('computed_max_gap_ms')} ms`")
        lines.append(f"- **全局请求成功率 (Global request success rate):** `{coverage.get('global_request_success_rate')}`")
        lines.append(f"- **单币最低请求成功率 (Per-symbol min request success rate):** `{coverage.get('per_symbol_request_success_rate_min')}`")
    else:
        lines.append("- 未计算 (Not evaluated)")
    lines.append("")

    lines.append("## 5. 裸快照完整性审计 (Raw Snapshot Integrity)")
    lines.append("")
    if raw_integrity:
        lines.append(f"- **JSONL 解析错误行数 (JSONL parse error count):** `{raw_integrity.get('jsonl_parse_error_count')}`")
        lines.append(f"- **JSONL 解析错误率 (JSONL parse error ratio):** `{raw_integrity.get('jsonl_parse_error_ratio')}`")
        lines.append(f"- **交叉盘/非法订单簿数 (Invalid book count):** `{raw_integrity.get('invalid_book_count')}`")
        lines.append(f"- **非单调递增时间戳数 (Non-monotonic timestamp count):** `{raw_integrity.get('non_monotonic_timestamp_count')}`")
        lines.append(f"- **最大重复快照占比 (Max duplicate snapshot ratio):** `{raw_integrity.get('duplicate_snapshot_ratio_max')}`")
        lines.append(f"- **最大空值率 (Max null ratio):** `{raw_integrity.get('null_ratio_max')}`")
    else:
        lines.append("- 未计算 (Not evaluated)")
    lines.append("")

    quarantine = summary.get("quarantine")
    if quarantine:
        lines.append("## 6. Quarantine 审计")
        lines.append("")
        lines.append(f"- **隔离的无效订单簿行数 (invalid_book_row_count):** `{quarantine.get('invalid_book_row_count')}`")
        lines.append(f"- **隔离的无效订单簿分钟数 (invalid_book_minute_bucket_count):** `{quarantine.get('invalid_book_minute_bucket_count')}`")
        lines.append(f"- **订单簿可用率 (book_availability_ratio):** `{quarantine.get('book_availability_ratio')}`")
        lines.append(f"- **订单簿不可用率 (book_unavailable_ratio):** `{quarantine.get('book_unavailable_ratio')}`")
        lines.append(f"- **首个有效订单簿延迟时间 (first_valid_book_latency_ms):** `{quarantine.get('first_valid_book_latency_ms')} ms`")
        lines.append(f"- **最大连续无效行数 (max_consecutive_invalid):** `{quarantine.get('max_consecutive_invalid')}`")
        lines.append(f"- **Warmup后最大连续无效行数 (max_consecutive_invalid_after_warmup):** `{quarantine.get('max_consecutive_invalid_after_warmup')}`")
        lines.append(f"- **执行可用性声明 (execution_availability_claim):** `{quarantine.get('execution_availability_claim')}`")
        lines.append(f"- **隔离无效行路径 (quarantined_rows_path):** `{quarantine.get('quarantined_rows_path')}`")
        lines.append(f"- **深度质量输入行路径 (depth_quality_input_rows_path):** `{quarantine.get('depth_quality_input_rows_path')}`")
        lines.append("")
        lines.append("> [!WARNING]")
        lines.append("> quarantined pass 只能支持 1.5H design，不允许 execution feasibility claim / paper / live。")
        lines.append("")

    lines.append("## 7. 深度与滑点审计 (Depth & Slippage Quality)")
    lines.append("")
    if depth_quality:
        lines.append(f"- **P50 价差 (Spread bps P50):** `{depth_quality.get('spread_bps_p50')} bps`")
        lines.append(f"- **P95 价差 (Spread bps P95):** `{depth_quality.get('spread_bps_p95')} bps`")
        lines.append(f"- **P50 买滑点 (Buy slippage bps P50):** `{depth_quality.get('buy_slippage_bps_500usdt_p50')} bps`")
        lines.append(f"- **P95 买滑点 (Buy slippage bps P95):** `{depth_quality.get('buy_slippage_bps_500usdt_p95')} bps`")
        lines.append(f"- **P50 卖滑点 (Sell slippage bps P50):** `{depth_quality.get('sell_slippage_bps_500usdt_p50')} bps`")
        lines.append(f"- **P95 卖滑点 (Sell slippage bps P95):** `{depth_quality.get('sell_slippage_bps_500usdt_p95')} bps`")
        lines.append(f"- **P05 买盘深度 (Top bid depth P05):** `{depth_quality.get('top_bid_depth_usdt_p05')} USDT`")
        lines.append(f"- **P50 买盘深度 (Top bid depth P50):** `{depth_quality.get('top_bid_depth_usdt_p50')} USDT`")
        lines.append(f"- **P05 卖盘深度 (Top ask depth P05):** `{depth_quality.get('top_ask_depth_usdt_p05')} USDT`")
        lines.append(f"- **P50 卖盘深度 (Top ask depth P50):** `{depth_quality.get('top_ask_depth_usdt_p50')} USDT`")
        lines.append(f"- **健康时间占比 (Healthy window ratio):** `{depth_quality.get('healthy_window_ratio')}`")
        lines.append(f"- **深度与持仓上限容量比 (Depth capacity ratio to risk cap P50):** `{depth_quality.get('depth_capacity_ratio_to_risk_cap_p50')}`")
    else:
        lines.append("- 未计算 (Not evaluated)")
    lines.append("")

    lines.append("## 8. 风险与局限性声明 (Risks & Limitations)")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> 本审计所用到的 1-minute 静态深度/滑点，仅仅代表 Polling 采样时刻的静态订单簿数据截面（static lower-bound proxy），不能代表实盘高频爆拉或砸盘撮合下的真实 execution 可行性与深度。")
    lines.append("> 本阶段依然严禁进行任何形式的实盘/模拟盘交易，或下达任何执行信号。")
    lines.append("")

    return "\n".join(lines)
