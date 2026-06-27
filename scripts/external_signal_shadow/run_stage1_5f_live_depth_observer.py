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
        watermark = bootstrap_watermark_from_stage1_5d_events(events)
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
        compact_observer_state_jsonl,
        load_latest_state_by_event_symbol_id,
    )
    state_file = os.path.join(output_root, "observer_state.jsonl")
    compact_observer_state_jsonl(state_file)
    states = load_latest_state_by_event_symbol_id(state_file)

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
        }

        # 6.2 Load Stage 1.5D events and classify event-symbols
        events = load_all_events(args.fixture_events_jsonl, args.stage1_5d_events_glob)
        logger.info(f"Loaded {len(events)} events. events={events}")

        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_budget import (
            can_start_new_observation,
            classify_budget_status,
            estimate_requests_per_min,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
            classify_event_symbol_eligibility,
            flatten_event_symbols,
            make_event_symbol_id,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
            finalize_observation_if_due,
            start_observation,
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

        for event in events:
            for flat_event in flatten_event_symbols(event):
                symbol = flat_event["symbol"]
                event_symbol_id = make_event_symbol_id(flat_event, symbol)

                if event_symbol_id in states:
                    continue

                status, reason = classify_event_symbol_eligibility(
                    row=flat_event,
                    symbol=symbol,
                    now_ms=now_ms,
                    watermark=watermark,
                    exchangeinfo_state=exchangeinfo_state,
                    budget_state=budget_state,
                )
                logger.info(f"Classified event {event_symbol_id} ({symbol}): status={status}, reason={reason}")

                if status == "eligible":
                    new_est_rate = estimate_requests_per_min(
                        active_count + 1,
                        1,
                        base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC,
                        0.2
                    )
                    if can_start_new_observation(active_count, new_est_rate):
                        flat_event["event_symbol_id"] = event_symbol_id
                        new_state = start_observation(flat_event, now_ms)

                        states[event_symbol_id] = new_state
                        active_states.append(new_state)
                        active_count += 1
                        post_watermark_accepted += 1

                        append_jsonl(state_file, new_state.to_dict())

                        accepted_path = build_daily_path(output_root, "events_accepted", now_ms)
                        append_jsonl(accepted_path, {
                            "event_symbol_id": event_symbol_id,
                            "symbol": symbol,
                            "event_id": flat_event.get("event_id"),
                            "detected_at_ms": flat_event.get("detected_at_ms"),
                            "accepted_at_ms": now_ms,
                        })
                        watermark = update_watermark_with_event(watermark, flat_event)
                        write_watermark_atomic(watermark_path, watermark)
                    else:
                        reason = "budget_exceeded"
                        status = "rejected"

                if status == "rejected":
                    if reason == "pre_watermark":
                        pre_watermark_ignored += 1
                    else:
                        rejected_path = build_daily_path(output_root, "events_rejected", now_ms)
                        append_jsonl(rejected_path, {
                            "event_symbol_id": event_symbol_id,
                            "symbol": symbol,
                            "rejection_reason": reason,
                            "depth_observation_started": False,
                            "rejected_at_ms": now_ms,
                        })

        # 6.3 Fetch public depth for active observations
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_client import (
            fetch_depth_snapshot,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_metrics import (
            parse_depth_payload,
        )
        from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
            record_depth_snapshot,
        )

        for state in list(active_states):
            symbol = state.symbol
            payload = None

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
            else:
                res = fetch_depth_snapshot(symbol, live_public_readonly=args.live_public_readonly)
                manifest_row = res["manifest_row"]
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
        )
        write_json(os.path.join(output_root, "live_depth_observer_summary.json"), summary.to_dict())

        poll_index += 1
        sleep_sec = 0.01 if args.mock_response_dir else 60
        time.sleep(sleep_sec)
    sys.exit(0)


if __name__ == "__main__":
    main()
