from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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

    # 3. States
    states = _load_jsonl_file(root / "observer_state.jsonl", loader_blockers, state_errors)

    # 4. Accepted/Rejected events
    accepted_events = _load_jsonl_glob(root, "events_accepted/*.jsonl", loader_blockers, state_errors)
    rejected_events = _load_jsonl_glob(root, "events_rejected/*.jsonl", loader_blockers, state_errors)

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


@dataclass(frozen=True)
class EvidenceIntegrityResult:
    blockers: list[str]
    warnings: list[str]
    evidence_label_counts: dict[str, int]
    formal_announcement_and_launch_count: int
    formal_completed_event_symbol_ids: set[str]


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

    # 2. Verify Accepted Events
    evidence_label_counts = {lbl: 0 for lbl in VALID_EVIDENCE_LABELS}
    for event in accepted_events:
        label = event.get("evidence_label")
        if not label:
            blockers.append("missing_evidence_label")
            continue
        if label not in VALID_EVIDENCE_LABELS:
            blockers.append("unknown_evidence_label")
            continue

        evidence_label_counts[label] += 1

        # Watermark version check
        if watermark:
            if event.get("watermark_version") != watermark.get("watermark_version"):
                blockers.append("watermark_version_mismatch")
            if event.get("watermark_max_seen_detected_at_ms") != watermark.get("max_seen_detected_at_ms"):
                blockers.append("watermark_max_seen_detected_at_ms_mismatch")

    # 3. Cross-Validation Join Checks
    state_by_id = {st.get("event_symbol_id"): st for st in states_list if st.get("event_symbol_id")}
    snapshots_by_id = {}
    for sn in snapshots_list:
        es_id = sn.get("event_symbol_id")
        if es_id:
            snapshots_by_id.setdefault(es_id, []).append(sn)

    # Completed state count verification
    completed_states = [st for st in states_list if st.get("status") == "completed"]
    if summary_dict:
        expected_completed = summary_dict.get("completed_observation_count", 0)
        if len(completed_states) != expected_completed:
            blockers.append("summary_state_count_mismatch")

    # Completed state must have snapshot files/rows
    for st in completed_states:
        es_id = st.get("event_symbol_id")
        if not es_id or es_id not in snapshots_by_id or not snapshots_by_id[es_id]:
            blockers.append("completed_state_without_snapshots")

    # Compute formal counts
    formal_announcement_and_launch_count = 0
    formal_completed_event_symbol_ids = set()

    for event in accepted_events:
        es_id = event.get("event_symbol_id")
        label = event.get("evidence_label")
        if es_id and es_id in state_by_id:
            st = state_by_id[es_id]
            # Must join with completed state AND snapshots must exist
            if st.get("status") == "completed" and es_id in snapshots_by_id and snapshots_by_id[es_id]:
                if label == "announcement_and_launch_time":
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


def compute_coverage_metrics(
    states: list[dict],
    request_manifest_rows: list[dict],
    summary: dict | None = None,
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

    # Validate each symbol state
    for st in states:
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
        total_requests = len(request_manifest_rows)
        success_requests = sum(
            1 for r in request_manifest_rows
            if 200 <= r.get("http_status", 0) < 300
        )
        global_request_success_rate = success_requests / total_requests if total_requests > 0 else 0.0

        if global_request_success_rate < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_REQUEST_SUCCESS_RATE:
            blockers.append("global_request_success_rate_below_threshold")

        completed_states = [st for st in states if st.get("status") == "completed"]

        def is_depth_manifest_row(row: dict) -> bool:
            if row.get("event_symbol_id") or row.get("symbol"):
                return True
            return row.get("requested_path") == base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_PATH

        depth_manifest_rows = [r for r in request_manifest_rows if is_depth_manifest_row(r)]

        if completed_states and any(
            not (r.get("event_symbol_id") or r.get("symbol"))
            for r in depth_manifest_rows
        ):
            blockers.append("request_manifest_symbol_key_missing")

        # Group by symbol key (using event_symbol_id if present, otherwise symbol).
        # Rows without a key cannot support per-symbol health and are blocked above.
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

        if symbol_rates:
            per_symbol_request_success_rate_min = min(symbol_rates)

        if per_symbol_request_success_rate_min < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_PER_SYMBOL_REQUEST_SUCCESS_RATE:
            blockers.append("per_symbol_request_success_rate_below_threshold")
    else:
        # If there are states/events but request_manifest is empty, this is handled in decision engine as invalid
        pass

    return {
        "expected_snapshot_count": expected_snapshot_count,
        "min_snapshot_count_required": min_snapshot_count_required,
        "snapshot_interval_ms": snapshot_interval_ms,
        "computed_max_gap_ms": computed_max_gap_ms,
        "per_symbol_request_success_rate_min": per_symbol_request_success_rate_min,
        "global_request_success_rate": global_request_success_rate,
        "blockers": blockers,
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
                "evidence_label": event.get("evidence_label"),
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


def build_stage1_5g_review_summary(
    summary: dict,
    watermark: dict,
    states: list[dict],
    accepted_events: list[dict],
    snapshots: list[dict],
    request_manifest_rows: list[dict],
    output_root: str | Path | None = None,
    loader_blockers: list[str] | None = None,
) -> dict:
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
    if any(b in all_blockers for b in ["jsonl_parse_error", "missing_or_unreadable_summary"]):
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
    if integrity_result.blockers:
        all_blockers.extend(integrity_result.blockers)
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
    if raw_integrity_result.blockers:
        all_blockers.extend(raw_integrity_result.blockers)
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
        }, integrity_result.formal_completed_event_symbol_ids)

    # 8. No Completed Formal Evidence Check
    if integrity_result.formal_announcement_and_launch_count == 0:
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
        }, integrity_result.formal_completed_event_symbol_ids)

    # 9. Depth Quality Check
    depth_quality_result = compute_depth_quality_metrics(snapshots)
    if depth_quality_result["blockers"]:
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
    # Group unique symbols and articles from completed formal evidence symbols
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

    return finish({
        "schema_version": base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION,
        "decision": "stage1_5g_depth_evidence_sufficient_for_stage1_5h_plan",
        "allowed_next_action": "write_stage1_5h_shadow_execution_simulator_design",
        "evidence_scope": evidence_scope,
        "event_family_conclusion_allowed": event_family_conclusion_allowed,
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

    lines.append("## 6. 深度与滑点审计 (Depth & Slippage Quality)")
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

    lines.append("## 7. 风险与局限性声明 (Risks & Limitations)")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> 本审计所用到的 1-minute 静态深度/滑点，仅仅代表 Polling 采样时刻的静态订单簿数据截面（static lower-bound proxy），不能代表实盘高频爆拉或砸盘撮合下的真实 execution 可行性与深度。")
    lines.append("> 本阶段依然严禁进行任何形式的实盘/模拟盘交易，或下达任何执行信号。")
    lines.append("")

    return "\n".join(lines)




