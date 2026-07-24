import argparse
import glob
import json
import os
import sys
import time

from loguru import logger

from configs import base


def parse_args():
    parser = argparse.ArgumentParser(description="Stage 1.5F Live Depth Observer")
    parser.add_argument("--stage1-5d-events-glob", type=str, default="")
    parser.add_argument("--stage1-5d-summary", type=str, default="")
    parser.add_argument("--stage1-5e-summary", type=str, default="")
    parser.add_argument("--output-root", type=str, required=True)
    parser.add_argument("--bootstrap-watermark", action="store_true")
    parser.add_argument("--max-polls", type=int, default=None)
    parser.add_argument("--max-seconds", type=int, default=None)
    parser.add_argument("--live-public-readonly", action="store_true")
    parser.add_argument("--fixture-events-jsonl", type=str, default="")
    parser.add_argument("--mock-response-dir", type=str, default="")
    return parser.parse_args()


def emit_sample_capped_diagnostic(output_root: str, subfolder: str, row: dict, diag_type: str, now_ms: int, counts_map: dict) -> bool:
    max_cap = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_REJECTION_HYGIENE_DIAGNOSTIC_SAMPLES_PER_TYPE
    curr = counts_map.get(diag_type, 0)
    if curr >= max_cap:
        return False
    counts_map[diag_type] = curr + 1
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
        append_jsonl,
        build_daily_path,
    )
    diag_path = build_daily_path(output_root, subfolder, now_ms)
    append_jsonl(diag_path, row)
    return True


def load_terminal_hygiene_diagnostic_sample_counts(output_root: str) -> dict:
    counts = {}
    for stream_name in ("historical_anchor_hygiene_diagnostics", "rejection_hygiene_diagnostics"):
        for row in load_all_jsonl_from_subdirs(output_root, stream_name):
            dtype = row.get("diagnostic_type")
            if not dtype:
                continue
            counts[dtype] = counts.get(dtype, 0) + 1
    return counts


def load_all_events(fixture_path: str, glob_pattern: str):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
        iter_stage1_5d_event_rows,
    )
    if fixture_path:
        return list(iter_stage1_5d_event_rows(fixture_path))
    elif glob_pattern:
        return list(iter_stage1_5d_event_rows(glob_pattern))
    return []


def load_all_jsonl_from_subdirs(root: str, stream_name: str) -> list:
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import read_jsonl
    pattern = os.path.join(root, stream_name, "**", "*.jsonl")
    rows = []
    for filepath in sorted(glob.glob(pattern, recursive=True)):
        rows.extend(read_jsonl(filepath))
    return rows


def load_all_snapshots_for_event_symbol(root: str, event_symbol_id: str) -> list:
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        DepthSnapshot,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import read_jsonl
    pattern = os.path.join(root, "depth_snapshots", "*", f"{event_symbol_id}.jsonl")
    snapshots = []
    for filepath in sorted(glob.glob(pattern)):
        snapshots.extend(DepthSnapshot.from_dict(row) for row in read_jsonl(filepath))
    return snapshots


def get_mock_json_response(mock_dir: str, name: str) -> dict:
    candidates = [
        os.path.join(mock_dir, f"binance_{name}_payload.json"),
        os.path.join(mock_dir, f"{name}.json"),
    ]
    if "depth" in name:
        candidates.append(os.path.join(mock_dir, "binance_depth_payload_healthy.json"))
        candidates.append(os.path.join(mock_dir, "binance_depth_payload_insufficient_depth.json"))

    for path in candidates:
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
    raise FileNotFoundError(f"Mock response not found for {name} in {mock_dir}")


def enrich_depth_request_manifest_row(
    manifest_row: dict,
    *,
    event_symbol_id: str,
    event_id: str,
    symbol: str,
) -> dict:
    if not event_symbol_id:
        raise ValueError("event_symbol_id_required")
    if not event_id:
        raise ValueError("event_id_required")
    if not symbol:
        raise ValueError("symbol_required")

    row = dict(manifest_row or {})
    row["request_type"] = "depth_snapshot"
    row["audit_metadata_version"] = 1
    row["event_symbol_id"] = event_symbol_id
    row["event_id"] = event_id
    row["symbol"] = symbol
    return row


def build_accepted_row_from_state(state, watermark, now_ms: int) -> dict:
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
        classify_live_depth_evidence_basis,
    )

    basis_diag = classify_live_depth_evidence_basis(state.to_dict(), watermark)
    accepted_at_ms = state.observation_admitted_at_ms or now_ms
    return {
        "event_symbol_id": state.event_symbol_id,
        "symbol": state.symbol,
        "event_id": state.event_id,
        "detected_at_ms": state.detected_at_ms,
        "accepted_at_ms": accepted_at_ms,
        "acceptance_id": state.acceptance_id,
        "evidence_start_class": state.evidence_start_class,
        "observation_anchor_ms": state.observation_anchor_ms,
        "observation_anchor_basis": state.observation_anchor_basis,
        "observation_anchor_confidence": state.observation_anchor_confidence,
        "observation_window_start_ms": state.observation_window_start_ms,
        "observation_window_end_ms": state.observation_window_end_ms,
        "bootstrap_watermark_max_seen_detected_at_ms": state.bootstrap_watermark_max_seen_detected_at_ms,
        "admission_watermark_at_first_seen_ms": state.admission_watermark_at_first_seen_ms,
        "announcement_capture_post_bootstrap_watermark": state.announcement_capture_post_bootstrap_watermark,
        "launch_anchor_post_bootstrap_watermark": state.launch_anchor_post_bootstrap_watermark,
        **basis_diag,
    }


def reconcile_missing_accepted_rows(output_root: str, states: dict, watermark, now_ms: int) -> list[dict]:
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        make_acceptance_id,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
        append_jsonl,
        build_daily_path,
    )

    existing_rows = load_all_jsonl_from_subdirs(output_root, "events_accepted")
    existing_acceptance_ids = {row.get("acceptance_id") for row in existing_rows if row.get("acceptance_id")}
    existing_event_symbol_ids = {row.get("event_symbol_id") for row in existing_rows if row.get("event_symbol_id")}
    backfilled = []

    for state in states.values():
        if state.status != "active":
            continue
        acceptance_id = state.acceptance_id or make_acceptance_id(state)
        if acceptance_id in existing_acceptance_ids or state.event_symbol_id in existing_event_symbol_ids:
            continue
        if not state.observation_anchor_ms:
            continue
        d = state.to_dict()
        d["acceptance_id"] = acceptance_id
        state_with_id = state.__class__.from_dict(d)
        row = build_accepted_row_from_state(state_with_id, watermark, now_ms)
        accepted_path = build_daily_path(output_root, "events_accepted", row["accepted_at_ms"])
        append_jsonl(accepted_path, row)
        existing_acceptance_ids.add(acceptance_id)
        existing_event_symbol_ids.add(state.event_symbol_id)
        backfilled.append(row)

    return backfilled


def reconcile_missing_terminal_ignored_rows(output_root: str, states: dict, now_ms: int) -> list[dict]:
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        build_historical_anchor_hygiene_diagnostic,
    )
    existing_rows = load_all_jsonl_from_subdirs(output_root, "historical_anchor_hygiene_diagnostics")
    existing_hygiene_ids = {r.get("terminal_hygiene_id") for r in existing_rows if r.get("terminal_hygiene_id")}
    existing_event_symbol_ids = {r.get("event_symbol_id") for r in existing_rows if r.get("event_symbol_id")}

    counts_map = {}
    for r in existing_rows:
        dtype = r.get("diagnostic_type", "historical_anchor_pre_bootstrap_ignored")
        counts_map[dtype] = counts_map.get(dtype, 0) + 1

    reconciled = []
    for state in states.values():
        if state.status != "ignored_historical_anchor_pre_bootstrap":
            continue
        if (
            getattr(state, "terminal_audit_type", "") == "historical_anchor_hygiene_diagnostics"
            and not getattr(state, "diagnostic_expected", False)
            and not getattr(state, "diagnostic_emitted", False)
        ):
            continue
        hygiene_id = getattr(state, "terminal_hygiene_id", "")
        if (hygiene_id and hygiene_id in existing_hygiene_ids) or (state.event_symbol_id in existing_event_symbol_ids):
            continue

        diag_row = build_historical_anchor_hygiene_diagnostic(state, now_ms)
        emitted = emit_sample_capped_diagnostic(
            output_root,
            "historical_anchor_hygiene_diagnostics",
            diag_row,
            "historical_anchor_pre_bootstrap_ignored",
            now_ms,
            counts_map,
        )
        if emitted:
            if hygiene_id:
                existing_hygiene_ids.add(hygiene_id)
            existing_event_symbol_ids.add(state.event_symbol_id)
            reconciled.append(diag_row)

    return reconciled


def reconcile_terminal_hygiene_artifacts(output_root: str, state_file: str, states: dict, now_ms: int) -> dict:
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
        append_jsonl,
    )

    by_hygiene_id = {
        s.terminal_hygiene_id: s
        for s in states.values()
        if getattr(s, "terminal_hygiene_id", "")
    }
    by_event_symbol_id = {
        s.event_symbol_id: s
        for s in states.values()
        if getattr(s, "event_symbol_id", "")
    }

    rebuilt_ignored = 0
    rebuilt_rejected = 0

    diagnostic_rows = load_all_jsonl_from_subdirs(output_root, "historical_anchor_hygiene_diagnostics")
    for row in diagnostic_rows:
        if row.get("diagnostic_type") != "historical_anchor_pre_bootstrap_ignored":
            continue
        event_symbol_id = str(row.get("event_symbol_id") or "")
        hygiene_id = str(row.get("terminal_hygiene_id") or "")
        if (event_symbol_id and event_symbol_id in by_event_symbol_id) or (hygiene_id and hygiene_id in by_hygiene_id):
            continue
        if not event_symbol_id or not hygiene_id:
            continue

        state = EventSymbolState(
            event_symbol_id=event_symbol_id,
            event_id=str(row.get("event_id") or ""),
            source_article_id=str(row.get("source_article_id") or ""),
            stable_event_symbol_key=str(row.get("stable_event_symbol_key") or ""),
            stable_event_key=str(row.get("stable_event_key") or ""),
            symbol=str(row.get("symbol") or "").upper(),
            detected_at_ms=int(row.get("detected_at_ms") or row.get("terminal_at_ms") or now_ms),
            status="ignored_historical_anchor_pre_bootstrap",
            terminal_hygiene_id=hygiene_id,
            terminal_status="ignored_historical_anchor_pre_bootstrap",
            terminal_reason=str(row.get("terminal_reason") or "historical_anchor_pre_bootstrap"),
            terminal_at_ms=row.get("terminal_at_ms") or row.get("diagnostic_at_ms") or now_ms,
            consumable_by_stage1_5g=False,
            observation_anchor_candidates=row.get("observation_anchor_candidates") or {},
            bootstrap_watermark_max_seen_detected_at_ms=row.get("bootstrap_watermark_max_seen_detected_at_ms"),
            terminal_audit_type="historical_anchor_hygiene_diagnostics",
            terminal_audit_row=row,
            diagnostic_expected=True,
            diagnostic_sample_reserved=True,
            diagnostic_emitted=True,
        )
        states[event_symbol_id] = state
        by_event_symbol_id[event_symbol_id] = state
        by_hygiene_id[hygiene_id] = state
        append_jsonl(state_file, state.to_dict())
        rebuilt_ignored += 1

    rejected_rows = load_all_jsonl_from_subdirs(output_root, "events_rejected")
    for row in rejected_rows:
        event_symbol_id = str(row.get("event_symbol_id") or "")
        hygiene_id = str(row.get("terminal_hygiene_id") or "")
        if (event_symbol_id and event_symbol_id in by_event_symbol_id) or (hygiene_id and hygiene_id in by_hygiene_id):
            continue
        if not event_symbol_id or not hygiene_id:
            continue

        state = EventSymbolState(
            event_symbol_id=event_symbol_id,
            event_id=str(row.get("event_id") or ""),
            source_article_id=str(row.get("source_article_id") or ""),
            stable_event_symbol_key=str(row.get("stable_event_symbol_key") or ""),
            stable_event_key=str(row.get("stable_event_key") or ""),
            symbol=str(row.get("symbol") or "").upper(),
            detected_at_ms=int(row.get("detected_at_ms") or row.get("rejected_at_ms") or now_ms),
            status="rejected",
            terminal_hygiene_id=hygiene_id,
            terminal_status="rejected",
            terminal_reason=str(row.get("rejected_reason") or row.get("rejection_reason") or ""),
            terminal_at_ms=row.get("rejected_at_ms") or now_ms,
            consumable_by_stage1_5g=True,
            terminal_audit_type="events_rejected",
            terminal_audit_row=row,
        )
        states[event_symbol_id] = state
        by_event_symbol_id[event_symbol_id] = state
        by_hygiene_id[hygiene_id] = state
        append_jsonl(state_file, state.to_dict())
        rebuilt_rejected += 1

    return {
        "terminal_ignored_state_rebuilt_count": rebuilt_ignored,
        "rejected_state_rebuilt_count": rebuilt_rejected,
    }


def main():
    args = parse_args()
    output_root = args.output_root
    os.makedirs(output_root, exist_ok=True)

    # 1. Check watermark bootstrap mode
    if args.bootstrap_watermark:
        logger.info("Watermark bootstrap mode requested.")
        events = load_all_events(args.fixture_events_jsonl, args.stage1_5d_events_glob)

        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_watermark import (
            bootstrap_watermark_from_stage1_5d_events,
            write_watermark_atomic,
        )
        watermark = bootstrap_watermark_from_stage1_5d_events(
            events,
            source_root=args.stage1_5d_events_glob or args.fixture_events_jsonl or "",
            output_root=output_root,
            now_ms=int(time.time() * 1000),
        )
        write_watermark_atomic(os.path.join(output_root, "watermark.json"), watermark)

        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
            write_json,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_summary import (
            build_live_depth_observer_summary,
        )

        summary = build_live_depth_observer_summary(
            decision="stage1_5f_observer_bootstrap_watermark_only",
            bootstrap_watermark_allowed=True,
            live_depth_observation_allowed=False,
            stage1_5d_summary_path=args.stage1_5d_summary,
            stage1_5e_summary_path=args.stage1_5e_summary,
            stage1_5e_context_missing=True,
            stage1_5e_context_suspicious=False,
            watermark_present=True,
            watermark_version=watermark.watermark_version,
            max_seen_detected_at_ms=watermark.max_seen_detected_at_ms,
            pre_watermark_events_ignored=len(events),
            post_watermark_events_accepted=0,
            active_states=[],
            completed_states=[],
            expired_states=[],
            failed_states=[],
            request_manifest_rows=[],
            heartbeat_rows=[],
        )
        write_json(os.path.join(output_root, "live_depth_observer_summary.json"), summary.to_dict())
        logger.info("Watermark bootstrapped and summary written. Exiting.")
        sys.exit(0)

    # 2. Validate Stage 1.5D summary
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
        validate_stage1_5d_summary,
    )
    try:
        validate_stage1_5d_summary(args.stage1_5d_summary)
    except Exception as e:
        logger.error(f"Stage 1.5D summary validation failed: {e}")
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
            write_json,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_summary import (
            build_live_depth_observer_summary,
        )
        summary = build_live_depth_observer_summary(
            decision="stage1_5f_observer_invalid",
            bootstrap_watermark_allowed=False,
            live_depth_observation_allowed=False,
            stage1_5d_summary_path=args.stage1_5d_summary,
            stage1_5e_summary_path=args.stage1_5e_summary,
            stage1_5e_context_missing=True,
            stage1_5e_context_suspicious=False,
            watermark_present=False,
            watermark_version=None,
            max_seen_detected_at_ms=0,
            pre_watermark_events_ignored=0,
            post_watermark_events_accepted=0,
            active_states=[],
            completed_states=[],
            expired_states=[],
            failed_states=[],
            request_manifest_rows=[],
            heartbeat_rows=[],
        )
        summary_dict = summary.to_dict()
        summary_dict["blocker"] = "stage1_5d_summary_invalid_or_unsafe"
        write_json(os.path.join(output_root, "live_depth_observer_summary.json"), summary_dict)
        sys.exit(1)

    # 3. Validate Stage 1.5E summary safety check (Advisory C)
    stage1_5e_context_missing = True
    stage1_5e_context_suspicious = False
    if args.stage1_5e_summary and os.path.exists(args.stage1_5e_summary):
        stage1_5e_context_missing = False
        try:
            with open(args.stage1_5e_summary, "r") as f:
                e_data = json.load(f)
            unsafe_fields = [
                "execution_feasibility_claim_allowed",
                "trade_signal_allowed",
                "paper_trading_allowed",
                "live_trading_allowed",
                "execution_engine_allowed",
                "alpha_interpretation_allowed",
            ]
            unsafe_values = {
                field: e_data.get(field)
                for field in unsafe_fields
                if e_data.get(field, False) is not False
            }
            if unsafe_values:
                logger.warning("Stage 1.5E summary safety check failed! Setting stage1_5e_context_suspicious = True")
                stage1_5e_context_suspicious = True
        except Exception as e:
            logger.warning(f"Failed to read/parse Stage 1.5E summary: {e}")
            stage1_5e_context_suspicious = True

    if stage1_5e_context_missing:
        logger.error("Stage 1.5E summary missing. Cannot run observation mode.")
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
            write_json,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_summary import (
            build_live_depth_observer_summary,
        )
        summary = build_live_depth_observer_summary(
            decision="stage1_5f_observer_invalid",
            bootstrap_watermark_allowed=False,
            live_depth_observation_allowed=False,
            stage1_5d_summary_path=args.stage1_5d_summary,
            stage1_5e_summary_path=args.stage1_5e_summary,
            stage1_5e_context_missing=True,
            stage1_5e_context_suspicious=False,
            watermark_present=False,
            watermark_version=None,
            max_seen_detected_at_ms=0,
            pre_watermark_events_ignored=0,
            post_watermark_events_accepted=0,
            active_states=[],
            completed_states=[],
            expired_states=[],
            failed_states=[],
            request_manifest_rows=[],
            heartbeat_rows=[],
        )
        summary_dict = summary.to_dict()
        summary_dict["blocker"] = "stage1_5e_context_missing_for_observation"
        write_json(os.path.join(output_root, "live_depth_observer_summary.json"), summary_dict)
        sys.exit(1)

    if stage1_5e_context_suspicious:
        logger.error("Stage 1.5E summary is unsafe. Cannot run observation mode.")
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
            write_json,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_summary import (
            build_live_depth_observer_summary,
        )
        summary = build_live_depth_observer_summary(
            decision="stage1_5f_observer_invalid",
            bootstrap_watermark_allowed=False,
            live_depth_observation_allowed=False,
            stage1_5d_summary_path=args.stage1_5d_summary,
            stage1_5e_summary_path=args.stage1_5e_summary,
            stage1_5e_context_missing=False,
            stage1_5e_context_suspicious=True,
            watermark_present=False,
            watermark_version=None,
            max_seen_detected_at_ms=0,
            pre_watermark_events_ignored=0,
            post_watermark_events_accepted=0,
            active_states=[],
            completed_states=[],
            expired_states=[],
            failed_states=[],
            request_manifest_rows=[],
            heartbeat_rows=[],
        )
        summary_dict = summary.to_dict()
        summary_dict["blocker"] = "stage1_5e_summary_invalid_or_unsafe"
        write_json(os.path.join(output_root, "live_depth_observer_summary.json"), summary_dict)
        sys.exit(1)

    # 4. Load watermark
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_watermark import (
        load_watermark,
        update_watermark_with_event,
        write_watermark_atomic,
    )
    watermark_path = os.path.join(output_root, "watermark.json")
    if not os.path.exists(watermark_path):
        logger.error(f"Watermark file not found at {watermark_path}. Must bootstrap watermark first.")
        sys.exit(1)
    watermark = load_watermark(watermark_path)

    # 5. Load/compact/resume observer state
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        build_historical_anchor_hygiene_diagnostic,
        build_rejected_event_symbol_row,
        build_terminal_ignored_state,
        compact_observer_state_jsonl,
        load_latest_state_by_event_symbol_id,
        make_terminal_hygiene_id,
    )
    state_file = os.path.join(output_root, "observer_state.jsonl")
    compact_observer_state_jsonl(state_file)
    states = load_latest_state_by_event_symbol_id(state_file)
    reconcile_terminal_hygiene_artifacts(output_root, state_file, states, now_ms=int(time.time() * 1000))
    reconcile_missing_accepted_rows(output_root, states, watermark, now_ms=int(time.time() * 1000))
    reconcile_missing_terminal_ignored_rows(output_root, states, now_ms=int(time.time() * 1000))

    terminal_states_by_stable_event_symbol_key = {
        s.stable_event_symbol_key: s
        for s in states.values()
        if s.stable_event_symbol_key and s.status in ("ignored_historical_anchor_pre_bootstrap", "rejected")
    }
    terminal_states_by_terminal_hygiene_id = {
        s.terminal_hygiene_id: s
        for s in states.values()
        if getattr(s, "terminal_hygiene_id", "")
    }
    historical_diagnostic_samples_by_type = load_terminal_hygiene_diagnostic_sample_counts(output_root)
    historical_anchor_newly_ignored_this_poll = 0
    bootstrap_watermark_missing_diagnostic_count = 0
    malformed_terminal_diagnostic_count = 0

    # 6. Load daily rotated stream history
    request_manifest_rows = load_all_jsonl_from_subdirs(output_root, "request_manifest")
    heartbeat_rows = load_all_jsonl_from_subdirs(output_root, "heartbeat")

    pre_watermark_ignored = 0
    post_watermark_accepted = 0

    poll_index = 0
    start_sec = time.time()

    max_polls = args.max_polls
    max_seconds = args.max_seconds
    previous_exchangeinfo_cache = None

    # Main observation loop
    while True:
        now_ms = int(time.time() * 1000)
        elapsed = time.time() - start_sec

        if max_polls is not None and poll_index >= max_polls:
            logger.info(f"Reached max polls limit: {max_polls}")
            break
        if max_seconds is not None and elapsed >= max_seconds:
            logger.info(f"Reached max seconds limit: {max_seconds}")
            break

        logger.info(f"Starting poll {poll_index} at {now_ms} ms")
        last_error_str = None

        # 6.1 Refresh exchangeInfo cache
        mock_exinfo_payload = None
        if args.mock_response_dir:
            try:
                mock_exinfo_payload = get_mock_json_response(args.mock_response_dir, "exchangeinfo")
            except Exception as e:
                logger.error(f"Failed to load mock exchangeinfo: {e}")
                last_error_str = str(e)

        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_client import (
            refresh_exchangeinfo_cache,
        )
        exchangeinfo_cache = refresh_exchangeinfo_cache(
            now_ms=now_ms,
            previous_cache=previous_exchangeinfo_cache,
            live_public_readonly=args.live_public_readonly,
            mock_exchangeinfo_payload=mock_exinfo_payload,
        )

        if exchangeinfo_cache.get("manifest_row"):
            from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
                append_jsonl,
                build_daily_path,
            )
            row = exchangeinfo_cache["manifest_row"]
            request_manifest_rows.append(row)
            manifest_path = build_daily_path(output_root, "request_manifest", now_ms)
            append_jsonl(manifest_path, row)

        previous_exchangeinfo_cache = exchangeinfo_cache
        exchangeinfo_state = {
            "available": exchangeinfo_cache.get("available", False),
            "symbols": exchangeinfo_cache.get("symbols", set()),
            "symbol_rows": exchangeinfo_cache.get("symbol_rows", {}),
            "payload_sha256": exchangeinfo_cache.get("payload_sha256", ""),
            "raw_payload_path": exchangeinfo_cache.get("raw_payload_path", ""),
            "fetched_at_ms": exchangeinfo_cache.get("fetched_at_ms", 0),
        }

        # 6.2 Load Stage 1.5D events and process pending/new event-symbols
        events = load_all_events(args.fixture_events_jsonl, args.stage1_5d_events_glob)
        logger.info(f"Loaded {len(events)} events. events={events}")

        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
            EventSymbolState,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_budget import (
            can_start_new_observation,
            classify_budget_status,
            estimate_requests_per_min,
        )

        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
            classify_event_symbol_eligibility_with_diagnostics,
            classify_live_depth_evidence_basis,
            flatten_event_symbols,
            make_event_symbol_id,
            make_stable_event_symbol_key,
            re_resolve_pending_anchor,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
            create_pending_observation_state,
            finalize_observation_if_due,
            promote_pending_to_active_observation,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
            append_jsonl,
            build_daily_path,
        )

        for state in list(states.values()):
            if state.status != "active" or now_ms < state.observation_window_end_ms:
                continue
            snapshots = load_all_snapshots_for_event_symbol(output_root, state.event_symbol_id)
            final_state = finalize_observation_if_due(state, now_ms, snapshots)
            states[state.event_symbol_id] = final_state
            append_jsonl(state_file, final_state.to_dict())

        active_states = [s for s in states.values() if s.status == "active"]
        active_count = len(active_states)

        estimated_req_rate = estimate_requests_per_min(
            active_count,
            1,
            base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC,
            0.2
        )
        budget_status = classify_budget_status(active_count, estimated_req_rate)
        budget_state = {"budget_exceeded": budget_status == "rate_limit_budget_exceeded"}

        # 6.2.1 Re-evaluate existing pending states
        for pending_id, pending_state in list(states.items()):
            if not pending_state.status.startswith("pending_"):
                continue

            if (pending_state.next_anchor_resolution_at_ms is not None and now_ms >= pending_state.next_anchor_resolution_at_ms) or (
                pending_state.next_admission_check_at_ms is not None and now_ms >= pending_state.next_admission_check_at_ms
            ):
                updated_pending = re_resolve_pending_anchor(pending_state, events, exchangeinfo_state, now_ms)
                if updated_pending.status in ("pending_ready_for_admission", "eligible_clean_start", "eligible_recovery_only") or (
                    updated_pending.observation_anchor_ms is not None and now_ms >= updated_pending.observation_anchor_ms
                ):
                    new_est_rate = estimate_requests_per_min(active_count + 1, 1, base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC, 0.2)
                    if can_start_new_observation(active_count, new_est_rate):
                        ev_start_class = updated_pending.evidence_start_class or ("clean_start" if updated_pending.observation_anchor_ms and now_ms - updated_pending.observation_anchor_ms <= base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS else "recovery_start")
                        promoted_state = promote_pending_to_active_observation(updated_pending, now_ms, evidence_start_class=ev_start_class)
                        states[pending_id] = promoted_state
                        active_states.append(promoted_state)
                        active_count += 1
                        post_watermark_accepted += 1
                        append_jsonl(state_file, promoted_state.to_dict())

                        target_event = {}
                        for ev in events:
                            if promoted_state.symbol in ev.get("symbols", []) or promoted_state.event_id == ev.get("event_id"):
                                target_event = ev
                                break
                        accepted_path = build_daily_path(output_root, "events_accepted", now_ms)
                        append_jsonl(accepted_path, build_accepted_row_from_state(promoted_state, watermark, now_ms))

                        if target_event:
                            watermark = update_watermark_with_event(watermark, target_event)
                            write_watermark_atomic(watermark_path, watermark)


                    else:
                        d = updated_pending.to_dict()
                        d["capacity_defer_count"] = updated_pending.capacity_defer_count + 1
                        states[pending_id] = EventSymbolState.from_dict(d)
                        append_jsonl(state_file, d)
                else:
                    states[pending_id] = updated_pending
                    append_jsonl(state_file, updated_pending.to_dict())

        # 6.2.2 Classify new incoming events
        for event in events:
            for flat_event in flatten_event_symbols(event):
                symbol = flat_event["symbol"]
                event_symbol_id = make_event_symbol_id(flat_event, symbol)
                stable_key = make_stable_event_symbol_key(flat_event, symbol)
                flat_event["event_symbol_id"] = event_symbol_id
                flat_event["stable_event_symbol_key"] = stable_key

                if event_symbol_id in states:
                    existing_state = states[event_symbol_id]
                    if existing_state.status == "ignored_historical_anchor_pre_bootstrap":
                        new_hash = flat_event.get("detail_payload_hash") or flat_event.get("payload_hash") or ""
                        if new_hash and getattr(existing_state, "source_event_payload_hash", "") and new_hash != existing_state.source_event_payload_hash:
                            d = existing_state.to_dict()
                            d["terminal_ignored_revision_seen_count"] = existing_state.terminal_ignored_revision_seen_count + 1
                            d["latest_event_payload_hash"] = new_hash
                            updated = EventSymbolState.from_dict(d)
                            states[event_symbol_id] = updated
                            append_jsonl(state_file, updated.to_dict())
                    continue

                if stable_key in terminal_states_by_stable_event_symbol_key:
                    existing_terminal = terminal_states_by_stable_event_symbol_key[stable_key]
                    d = existing_terminal.to_dict()
                    d["duplicate_suppressed_count"] = getattr(existing_terminal, "duplicate_suppressed_count", 0) + 1
                    d["last_duplicate_seen_at_ms"] = now_ms
                    updated = EventSymbolState.from_dict(d)
                    states[existing_terminal.event_symbol_id] = updated
                    terminal_states_by_stable_event_symbol_key[stable_key] = updated
                    append_jsonl(state_file, updated.to_dict())
                    continue

                status, reason, eligibility_diag = classify_event_symbol_eligibility_with_diagnostics(
                    row=flat_event,
                    symbol=symbol,
                    now_ms=now_ms,
                    watermark=watermark,
                    exchangeinfo_state=exchangeinfo_state,
                    budget_state=budget_state,
                )
                logger.info(f"Classified event {event_symbol_id} ({symbol}): status={status}, reason={reason}")

                if status == "ignored" and reason == "ignored_historical_anchor_pre_bootstrap":
                    boot_root_id = getattr(watermark, "bootstrap_root_id", "")
                    eligibility_diag["bootstrap_root_id"] = boot_root_id
                    terminal_state = build_terminal_ignored_state(flat_event, reason, "ignored_historical_anchor_pre_bootstrap", now_ms, eligibility_diag)
                    diag_row = build_historical_anchor_hygiene_diagnostic(terminal_state, now_ms)
                    diag_emitted = emit_sample_capped_diagnostic(
                        output_root,
                        "historical_anchor_hygiene_diagnostics",
                        diag_row,
                        "historical_anchor_pre_bootstrap_ignored",
                        now_ms,
                        historical_diagnostic_samples_by_type,
                    )
                    d = terminal_state.to_dict()
                    d["diagnostic_expected"] = bool(diag_emitted)
                    d["diagnostic_sample_reserved"] = bool(diag_emitted)
                    d["diagnostic_emitted"] = bool(diag_emitted)
                    d["terminal_audit_type"] = "historical_anchor_hygiene_diagnostics"
                    if diag_emitted:
                        d["terminal_audit_row"] = diag_row
                    terminal_state = EventSymbolState.from_dict(d)
                    states[event_symbol_id] = terminal_state
                    terminal_states_by_stable_event_symbol_key[terminal_state.stable_event_symbol_key] = terminal_state
                    if terminal_state.terminal_hygiene_id:
                        terminal_states_by_terminal_hygiene_id[terminal_state.terminal_hygiene_id] = terminal_state

                    append_jsonl(state_file, terminal_state.to_dict())
                    historical_anchor_newly_ignored_this_poll += 1
                    continue

                if status == "diagnostic_only":
                    logger.info(f"Diagnostic-only event {event_symbol_id} ({symbol}): reason={reason}")
                    if reason == "historical_classification_bootstrap_watermark_missing":
                        bootstrap_watermark_missing_diagnostic_count += 1
                        emit_sample_capped_diagnostic(
                            output_root,
                            "rejection_hygiene_diagnostics",
                            {
                                "audit_metadata_version": 2,
                                "diagnostic_type": "bootstrap_watermark_missing",
                                "event_symbol_id": event_symbol_id,
                                "symbol": symbol,
                                "reason": reason,
                                "diagnostic_at_ms": now_ms,
                                **eligibility_diag,
                            },
                            "bootstrap_watermark_missing",
                            now_ms,
                            historical_diagnostic_samples_by_type,
                        )
                    elif reason == "malformed_source_identity":
                        malformed_terminal_diagnostic_count += 1
                        emit_sample_capped_diagnostic(
                            output_root,
                            "rejection_hygiene_diagnostics",
                            {
                                "audit_metadata_version": 2,
                                "diagnostic_type": "malformed_source_identity",
                                "event_symbol_id": event_symbol_id,
                                "symbol": symbol,
                                "reason": reason,
                                "diagnostic_at_ms": now_ms,
                                **eligibility_diag,
                            },
                            "malformed_source_identity",
                            now_ms,
                            historical_diagnostic_samples_by_type,
                        )
                    continue

                if status == "pending":
                    pending_state = create_pending_observation_state(flat_event, reason, eligibility_diag, now_ms)
                    states[event_symbol_id] = pending_state
                    append_jsonl(state_file, pending_state.to_dict())

                    pending_path = build_daily_path(output_root, "events_pending", now_ms)
                    append_jsonl(pending_path, {
                        "event_symbol_id": event_symbol_id,
                        "stable_event_symbol_key": flat_event["stable_event_symbol_key"],
                        "symbol": symbol,
                        "status": pending_state.status,
                        "pending_reason": reason,
                        "observation_anchor_ms": pending_state.observation_anchor_ms,
                        "observation_anchor_basis": pending_state.observation_anchor_basis,
                        "first_seen_at_ms": pending_state.first_seen_at_ms,
                        "next_admission_check_at_ms": pending_state.next_admission_check_at_ms,
                        "anchor_resolution_deadline_ms": pending_state.anchor_resolution_deadline_ms,
                    })
                    continue

                if status == "eligible":
                    new_est_rate = estimate_requests_per_min(
                        active_count + 1,
                        1,
                        base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC,
                        0.2
                    )
                    if can_start_new_observation(active_count, new_est_rate):
                        ev_start_class = eligibility_diag.get("evidence_start_class", "clean_start")
                        pending_state = create_pending_observation_state(flat_event, reason, eligibility_diag, now_ms)
                        new_state = promote_pending_to_active_observation(
                            pending_state,
                            now_ms,
                            evidence_start_class=ev_start_class,
                        )

                        states[event_symbol_id] = new_state
                        active_states.append(new_state)
                        active_count += 1
                        post_watermark_accepted += 1

                        append_jsonl(state_file, new_state.to_dict())

                        accepted_path = build_daily_path(output_root, "events_accepted", now_ms)
                        accepted_row = {**eligibility_diag, **build_accepted_row_from_state(new_state, watermark, now_ms)}
                        append_jsonl(accepted_path, accepted_row)
                        watermark = update_watermark_with_event(watermark, flat_event)
                        write_watermark_atomic(watermark_path, watermark)
                    else:
                        reason = "budget_exceeded"
                        status = "rejected"

                if status == "rejected":
                    if reason == "pre_watermark":
                        pre_watermark_ignored += 1
                    else:
                        basis_diag = classify_live_depth_evidence_basis(flat_event, watermark)
                        boot_root_id = getattr(watermark, "bootstrap_root_id", "")
                        term_hygiene_id = make_terminal_hygiene_id(flat_event["stable_event_symbol_key"], "rejected", "post_bootstrap_rejected", boot_root_id)
                        rejected_row = build_rejected_event_symbol_row(
                            flat_event=flat_event,
                            terminal_hygiene_id=term_hygiene_id,
                            rejected_reason=reason,
                            now_ms=now_ms,
                            watermark_max_seen_detected_at_ms=watermark.max_seen_detected_at_ms,
                            watermark_version=watermark.watermark_version,
                            eligibility_diag=eligibility_diag,
                            basis_diag=basis_diag,
                        )
                        rejected_path = build_daily_path(output_root, "events_rejected", now_ms)
                        append_jsonl(rejected_path, rejected_row)

                        rejected_state = EventSymbolState(
                            event_symbol_id=event_symbol_id,
                            event_id=str(flat_event.get("event_id") or ""),
                            symbol=symbol,
                            detected_at_ms=int(flat_event.get("detected_at_ms") or now_ms),
                            status="rejected",
                            terminal_hygiene_id=term_hygiene_id,
                            terminal_status="rejected",
                            terminal_reason=reason,
                            terminal_at_ms=now_ms,
                            consumable_by_stage1_5g=True,
                            source_article_id=str(flat_event.get("source_article_id") or ""),
                            stable_event_symbol_key=flat_event["stable_event_symbol_key"],
                            stable_event_key=str(flat_event.get("stable_event_key") or ""),
                            terminal_audit_type="events_rejected",
                            terminal_audit_row=rejected_row,
                        )
                        states[event_symbol_id] = rejected_state
                        terminal_states_by_stable_event_symbol_key[flat_event["stable_event_symbol_key"]] = rejected_state
                        if term_hygiene_id:
                            terminal_states_by_terminal_hygiene_id[term_hygiene_id] = rejected_state
                        append_jsonl(state_file, rejected_state.to_dict())
                    continue


        # 6.3 Fetch public depth for active observations
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_client import (
            fetch_depth_snapshot,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_metrics import (
            parse_depth_payload,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
            record_depth_request,
            record_depth_snapshot,
        )

        for state in list(active_states):
            symbol = state.symbol
            payload = None

            state = record_depth_request(state, now_ms)
            states[state.event_symbol_id] = state

            if args.mock_response_dir:

                try:
                    payload = get_mock_json_response(args.mock_response_dir, f"depth_{symbol}")
                except Exception:
                    if "insufficient" in symbol.lower():
                        payload = get_mock_json_response(args.mock_response_dir, "depth_payload_insufficient_depth")
                    else:
                        payload = get_mock_json_response(args.mock_response_dir, "depth_payload_healthy")

                manifest_row = {
                    "requested_host": "fapi.binance.com",
                    "requested_path": "/fapi/v1/depth",
                    "requested_url_hash": "mock",
                    "final_url_hash": "mock",
                    "http_status": 200,
                    "payload_size_bytes": 100,
                    "response_payload_hash": "mock",
                    "retry_count": 0,
                    "error": None,
                    "fetched_at_ms": now_ms,
                }
                manifest_row = enrich_depth_request_manifest_row(
                    manifest_row,
                    event_symbol_id=state.event_symbol_id,
                    event_id=state.event_id,
                    symbol=symbol,
                )
                request_manifest_rows.append(manifest_row)
                manifest_path = build_daily_path(output_root, "request_manifest", now_ms)
                append_jsonl(manifest_path, manifest_row)
            else:
                res = fetch_depth_snapshot(symbol, live_public_readonly=args.live_public_readonly)
                manifest_row = enrich_depth_request_manifest_row(
                    res["manifest_row"],
                    event_symbol_id=state.event_symbol_id,
                    event_id=state.event_id,
                    symbol=symbol,
                )
                request_manifest_rows.append(manifest_row)
                manifest_path = build_daily_path(output_root, "request_manifest", now_ms)
                append_jsonl(manifest_path, manifest_row)

                if res["ok"]:
                    payload = res["data"]
                else:
                    last_error_str = res.get("error")

            if payload:
                snapshot = parse_depth_payload(symbol, payload, now_ms, state.event_symbol_id)
            else:
                from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
                    DepthSnapshot,
                )
                snapshot = DepthSnapshot(
                    event_symbol_id=state.event_symbol_id,
                    symbol=symbol,
                    fetched_at_ms=now_ms,
                    exchange_time_ms=None,
                    best_bid=None,
                    best_ask=None,
                    spread_bps=None,
                    top_bid_depth_usdt=0.0,
                    top_ask_depth_usdt=0.0,
                    buy_slippage_bps=None,
                    sell_slippage_bps=None,
                    slippage_status="invalid_depth",
                    depth_status="invalid",
                )

            snapshot_path = build_daily_path(output_root, "depth_snapshots", now_ms, event_symbol_id=state.event_symbol_id)
            append_jsonl(snapshot_path, snapshot.to_dict())

            updated_state = record_depth_snapshot(state, snapshot)
            all_snapshots = load_all_snapshots_for_event_symbol(output_root, state.event_symbol_id)

            final_state = finalize_observation_if_due(updated_state, now_ms, all_snapshots)
            states[state.event_symbol_id] = final_state
            append_jsonl(state_file, final_state.to_dict())

        # 6.4 Write heartbeat row at the end of every poll
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
            HeartbeatRow,
        )
        active_states = [s for s in states.values() if s.status == "active"]
        completed_states = [s for s in states.values() if s.status == "completed"]

        hb_row = HeartbeatRow(
            poll_index=poll_index,
            poll_at_ms=now_ms,
            active_count=len(active_states),
            completed_count=len(completed_states),
            last_error=last_error_str,
            budget_status=budget_status,
            watermark_updated_at_ms=watermark.updated_at_ms,
        )
        heartbeat_rows.append(hb_row.to_dict())
        hb_path = build_daily_path(output_root, "heartbeat", now_ms)
        append_jsonl(hb_path, hb_row.to_dict())

        # 6.5 Write summary generator
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
            write_json,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_summary import (
            build_live_depth_observer_summary,
        )

        expired_states = [s for s in states.values() if s.status == "expired_without_depth"]
        failed_states = [s for s in states.values() if s.status == "failed"]

        if len(active_states) > 0:
            dec = "stage1_5f_observer_event_observation_in_progress"
        elif len(completed_states) > 0:
            dec = "stage1_5f_observer_depth_evidence_collected"
        else:
            dec = "stage1_5f_observer_running_no_new_event"

        summary = build_live_depth_observer_summary(
            decision=dec,
            bootstrap_watermark_allowed=True,
            live_depth_observation_allowed=True,
            stage1_5d_summary_path=args.stage1_5d_summary,
            stage1_5e_summary_path=args.stage1_5e_summary,
            stage1_5e_context_missing=False,
            stage1_5e_context_suspicious=stage1_5e_context_suspicious,
            watermark_present=True,
            watermark_version=watermark.watermark_version,
            max_seen_detected_at_ms=watermark.max_seen_detected_at_ms,
            pre_watermark_events_ignored=pre_watermark_ignored,
            post_watermark_events_accepted=post_watermark_accepted,
            active_states=active_states,
            completed_states=completed_states,
            expired_states=expired_states,
            failed_states=failed_states,
            request_manifest_rows=request_manifest_rows,
            heartbeat_rows=heartbeat_rows,
            pending_states=[s for s in states.values() if s.status.startswith("pending_")],
            terminal_states=[s for s in states.values() if s.status in ("ignored_historical_anchor_pre_bootstrap", "rejected")],
            historical_anchor_newly_ignored_this_poll=historical_anchor_newly_ignored_this_poll,
            bootstrap_watermark_missing_diagnostic_count=bootstrap_watermark_missing_diagnostic_count,
            malformed_terminal_diagnostic_count=malformed_terminal_diagnostic_count,
        )
        write_json(os.path.join(output_root, "live_depth_observer_summary.json"), summary.to_dict())

        poll_index += 1
        sleep_sec = 0.01 if args.mock_response_dir else 60
        time.sleep(sleep_sec)
    sys.exit(0)


if __name__ == "__main__":
    main()
