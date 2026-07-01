import argparse
import json
import sys
import time
from pathlib import Path

from configs import base
from src.research.external_signal_shadow.stage1_5d_live_event_source_client import (
    build_announcement_list_url,
    fetch_public_json,
    fetch_public_payload,
    validate_announcement_detail_url,
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
    PARSER_VERSION,
    SYMBOL_EXTRACTION_VERSION,
    extract_symbol_candidates_from_detail_payload,
    normalize_live_event,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import (
    append_jsonl,
    build_stream_paths,
    enforce_payload_budget,
    write_detail_payload,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_summary import (
    build_smoke_summary,
)


def main():
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

    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_summary_path = (
        Path(args.output_summary)
        if args.output_summary
        else output_root / "binance_futures_launch_smoke_summary.json"
    )

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
        output_summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_summary_path, "w", encoding="utf-8") as f:
            json.dump(invalid_summary, f, indent=2)
        print("Error: missing --live-public-readonly or --fixture-json")
        return 2

    # 2. Validate Upstream Evidence
    evidence_res = validate_upstream_evidence(args.stage1_5c1_summary, args.stage1_5c_summary)
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
        output_summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_summary_path, "w", encoding="utf-8") as f:
            json.dump(invalid_summary, f, indent=2)
        print("Error: upstream evidence invalid")
        return 0

    # 3. Main Polling Loop
    start_time = time.time()
    poll_count = 0
    heartbeats = []
    events_detected = []
    seen_event_ids = set()
    first_bar_queue = []
    request_manifest = []
    raw_futures_launch_article_count = 0
    symbol_parsed_event_count = 0
    symbol_parse_failed_count = 0
    last_poll_started_at_ms = None

    detail_retry_state = {}
    detail_fetch_attempted_count = 0
    detail_fetch_success_count = 0
    detail_fetch_failed_count = 0
    detail_fetch_budget_deferred_count = 0
    detail_fetch_url_rejected_count = 0
    detail_symbol_extracted_count = 0
    detail_symbol_parse_failed_count = 0
    title_symbol_extracted_count = 0
    symbol_empty_event_count = 0


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

    output_root.mkdir(parents=True, exist_ok=True)

    while True:
        if args.max_polls is not None and poll_count >= args.max_polls:
            break
        if args.max_seconds is not None and (time.time() - start_time) >= args.max_seconds:
            break

        poll_count += 1
        now_ms = int(time.time() * 1000)
        actual_poll_interval_sec = None
        poll_schedule_drift_ms = None
        if last_poll_started_at_ms is not None:
            actual_interval_ms = now_ms - last_poll_started_at_ms
            actual_poll_interval_sec = actual_interval_ms / 1000.0
            poll_schedule_drift_ms = actual_interval_ms - (args.poll_interval_sec * 1000)
        last_poll_started_at_ms = now_ms

        stream_paths = build_stream_paths(output_root, now_ms)

        active_symbols_cache = None
        ex_ok_cache = None

        def get_active_symbols():
            nonlocal active_symbols_cache, ex_ok_cache
            if active_symbols_cache is not None:
                return active_symbols_cache, ex_ok_cache

            if args.fixture_json:
                active_symbols_cache = set()
                ex_ok_cache = False
                return active_symbols_cache, ex_ok_cache

            ex_path = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_PATH", "/fapi/v1/exchangeInfo")
            ex_url = ex_path if ex_path.startswith("http") else "https://fapi.binance.com" + ex_path

            ex_ok = False
            active_symbols = set()
            ex_manifest = {
                "request_id": f"exchangeInfo_{int(time.time()*1000)}",
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
                        if s_info.get("status") == "TRADING" and s_info.get("contractType") == "PERPETUAL":
                            active_symbols.add(s_info.get("symbol"))
                else:
                    ex_manifest["error"] = ex_res.get("error")
            except Exception as e:
                ex_manifest["error"] = str(e)
            append_jsonl(stream_paths["request_manifest"], ex_manifest)
            request_manifest.append(ex_manifest)

            active_symbols_cache = active_symbols
            ex_ok_cache = ex_ok
            return active_symbols_cache, ex_ok_cache


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
        append_jsonl(stream_paths["request_manifest"], manifest_row)
        request_manifest.append(manifest_row)

        if payload:
            cycle_res = run_one_poll_cycle(
                payload=payload,
                detected_at_ms=now_ms,
                source_parent_url="https://www.binance.com/en/support/announcement",
                first_bar_queue=first_bar_queue,
            )
            for ev in cycle_res["events"]:
                raw_futures_launch_article_count += 1

                code = ev["source_article_id"]
                catalogs = payload.get("data", {}).get("catalogs", [])
                raw_articles = catalogs[0].get("articles", []) if catalogs else []
                raw_art = next((art for art in raw_articles if art.get("code") == code), {})

                if ev.get("symbols"):
                    title_symbol_extracted_count += 1
                    symbol_parsed_event_count += 1

                    norm_event = normalize_live_event(
                        raw=raw_art,
                        source_parent_url="https://www.binance.com/en/support/announcement",
                        detected_at_ms=ev["detected_at_ms"],
                        source_published_at_ms=ev["source_published_at_ms"],
                        source_published_at_ms_confidence=ev["source_published_at_ms_confidence"],
                    )

                    event_id = norm_event["event_id"]
                    if event_id not in seen_event_ids:
                        seen_event_ids.add(event_id)
                        append_jsonl(stream_paths["events"], norm_event)
                        events_detected.append(norm_event)
                else:
                    if code not in seen_event_ids and code not in detail_retry_state:
                        detail_retry_state[code] = {
                            "raw": raw_art,
                            "first_detected_at_ms": now_ms,
                            "retry_count": 0,
                            "last_retry_at_ms": 0,
                            "source_published_at_ms_confidence": ev["source_published_at_ms_confidence"]
                        }

            # Clean up first_bar_queue to remove empty symbol events
            first_bar_queue = [
                q for q in cycle_res["first_bar_queue"]
                if q.get("symbols") or q.get("source_article_id") not in detail_retry_state
            ]

            # Detail fallback processing
            detail_budget_remaining = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL", 3)
            source_parent_url = "https://www.binance.com/en/support/announcement"

            for code, state in list(detail_retry_state.items()):
                # 1. Check max-age expiry
                max_age_limit = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 3600)
                age_sec = (now_ms - state["first_detected_at_ms"]) / 1000.0
                if age_sec > max_age_limit:
                    symbol_empty_event_count += 1
                    symbol_parse_failed_count += 1
                    detail_symbol_parse_failed_count += 1

                    is_derived = "derived_candidates" in state
                    norm_event = normalize_live_event(
                        raw=state["raw"],
                        source_parent_url=source_parent_url,
                        detected_at_ms=state["first_detected_at_ms"],
                        source_published_at_ms=state["raw"].get("releaseDate"),
                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                        symbols_override=(),
                        extraction_metadata={
                            "symbol_extraction_source": state.get("symbol_extraction_source", "none"),
                            "symbol_derivation_method": state.get("symbol_derivation_method", None),
                            "symbol_validation_status": "rejected" if is_derived else None,
                            "detail_fetch_attempted": state["retry_count"] > 0,
                            "detail_fetch_status": "max_age_exceeded",
                            "symbol_parse_failed_reason": "detail_retry_max_age_exceeded",
                            "symbol_parse_status": "terminal_failed",
                        }
                    )
                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                    norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
                    norm_event["symbol_resolved_at_ms"] = now_ms
                    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                    event_id = norm_event["event_id"]
                    if event_id not in seen_event_ids:
                        seen_event_ids.add(event_id)
                        append_jsonl(stream_paths["events"], norm_event)
                        events_detected.append(norm_event)

                    detail_retry_state.pop(code, None)
                    continue

                # 2. Check max retries exhausted
                max_retries_limit = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES", 3)
                if state["retry_count"] >= max_retries_limit and "derived_candidates" not in state:
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
                            "detail_fetch_status": "retry_exhausted",
                            "symbol_parse_failed_reason": "detail_retry_exhausted",
                            "symbol_parse_status": "terminal_failed",
                        }
                    )
                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                    norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
                    norm_event["symbol_resolved_at_ms"] = now_ms
                    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                    event_id = norm_event["event_id"]
                    if event_id not in seen_event_ids:
                        seen_event_ids.add(event_id)
                        append_jsonl(stream_paths["events"], norm_event)
                        events_detected.append(norm_event)

                    detail_retry_state.pop(code, None)
                    continue

                # 2.5 Check if we already have derived candidates pending validation
                if "derived_candidates" in state:
                    active_symbols, ex_ok = get_active_symbols()
                    if not ex_ok:
                        continue

                    validated_symbols = [s for s in state["derived_candidates"] if s in active_symbols]
                    if validated_symbols:
                        detail_fetch_success_count += 1
                        detail_symbol_extracted_count += 1

                        norm_event = normalize_live_event(
                            raw=state["raw"],
                            source_parent_url=source_parent_url,
                            detected_at_ms=state["first_detected_at_ms"],
                            source_published_at_ms=state["raw"].get("releaseDate"),
                            source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                            symbols_override=validated_symbols,
                            extraction_metadata={
                                "symbol_extraction_source": state["symbol_extraction_source"],
                                "symbol_derivation_method": state["symbol_derivation_method"],
                                "quote_derivation_source": "exchange_info",
                                "symbol_validation_status": "validated",
                                "detail_fetch_attempted": True,
                                "detail_fetch_status": "success",
                                "symbol_parse_failed_reason": None,
                                "symbol_parse_status": "parsed",
                            }
                        )
                        norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                        norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
                        norm_event["symbol_resolved_at_ms"] = now_ms
                        norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                        event_id = norm_event["event_id"]
                        if event_id not in seen_event_ids:
                            seen_event_ids.add(event_id)
                            append_jsonl(stream_paths["events"], norm_event)
                            events_detected.append(norm_event)

                            # Add to first_bar_queue
                            eq_item = dict(norm_event)
                            eq_item["first_futures_bar_status"] = "not_yet_available"
                            eq_item["first_futures_bar_start_ms"] = None
                            first_bar_queue.append(eq_item)

                        detail_retry_state.pop(code, None)
                    else:
                        # Candidate exists but not trading. Retry handled via max-age expiry.
                        pass
                    continue

                # 3. Check budget
                if detail_budget_remaining <= 0:
                    detail_fetch_budget_deferred_count += 1
                    continue

                # 4. Attempt fetch
                detail_budget_remaining -= 1
                state["retry_count"] += 1
                state["last_retry_at_ms"] = now_ms
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
                        seen_event_ids.add(event_id)
                        append_jsonl(stream_paths["events"], norm_event)
                        events_detected.append(norm_event)

                    detail_retry_state.pop(code, None)
                    continue

                # Perform fetch
                fetch_res = None
                if args.fixture_json:
                    detail_payload = state["raw"].get("detailPayload")
                    if detail_payload is not None:
                        fetch_res = {
                            "ok": True,
                            "payload": detail_payload,
                            "final_url": detail_url,
                            "http_status": 200,
                            "error": None,
                        }
                    else:
                        fetch_res = {
                            "ok": False,
                            "payload": None,
                            "final_url": detail_url,
                            "http_status": None,
                            "error": "fixture_missing",
                        }
                else:
                    try:
                        fetch_res = fetch_public_payload(
                            detail_url,
                            live_public_readonly=args.live_public_readonly,
                            timeout_sec=getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_REQUEST_TIMEOUT_SEC", 10.0),
                            retry_budget=0
                        )
                    except Exception as e:
                        fetch_res = {
                            "ok": False,
                            "payload": None,
                            "final_url": detail_url,
                            "http_status": None,
                            "error": str(e),
                        }

                if fetch_res["ok"]:
                    # Validate final URL
                    final_url = fetch_res["final_url"]
                    try:
                        validate_announcement_detail_url(final_url)
                    except ValueError:
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
                            }
                        )
                        norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                        norm_event["detail_fetched_at_ms"] = now_ms
                        norm_event["symbol_resolved_at_ms"] = now_ms
                        norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                        event_id = norm_event["event_id"]
                        if event_id not in seen_event_ids:
                            seen_event_ids.add(event_id)
                            append_jsonl(stream_paths["events"], norm_event)
                            events_detected.append(norm_event)

                        detail_retry_state.pop(code, None)
                        continue

                    # Write detail payload
                    write_res = write_detail_payload(output_root, now_ms, code, fetch_res["payload"])
                    state["detail_fetched_at_ms"] = now_ms

                    # Append manifest row
                    detail_manifest = {
                        "request_id": f"detail_{now_ms}_{code}",
                        "source_type": "announcement_detail" if not args.fixture_json else "fixture_detail",
                        "symbol": "ALL",
                        "url": detail_url,
                        "final_url": final_url,
                        "http_status": fetch_res["http_status"],
                        "row_count": 0,
                        "error": None,
                        "fetched_at_ms": now_ms,
                        "payload_sha256": write_res["payload_sha256"],
                        "payload_size_bytes": write_res["payload_size_bytes"],
                        "payload_path": write_res["payload_path"],
                        "parser_version": PARSER_VERSION,
                        "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                    }
                    append_jsonl(stream_paths["request_manifest"], detail_manifest)
                    request_manifest.append(detail_manifest)

                    # Extract symbols
                    max_symbols = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS", 30)
                    title_context = state["raw"].get("title")
                    extraction_res = extract_symbol_candidates_from_detail_payload(
                        fetch_res["payload"], max_symbols, title=title_context
                    )

                    if extraction_res["symbols"]:
                        if extraction_res["symbol_validation_status"] == "validated_by_exact_text":
                            # Exact symbols matched. Emit immediately!
                            detail_fetch_success_count += 1
                            detail_symbol_extracted_count += 1

                            norm_event = normalize_live_event(
                                raw=state["raw"],
                                source_parent_url=source_parent_url,
                                detected_at_ms=state["first_detected_at_ms"],
                                source_published_at_ms=state["raw"].get("releaseDate"),
                                source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                symbols_override=extraction_res["symbols"],
                                extraction_metadata={
                                    "symbol_extraction_source": extraction_res["symbol_extraction_source"],
                                    "symbol_derivation_method": extraction_res["symbol_derivation_method"],
                                    "quote_derivation_source": None,
                                    "symbol_validation_status": "validated_by_exact_text",
                                    "detail_fetch_attempted": True,
                                    "detail_fetch_status": "success",
                                    "symbol_parse_failed_reason": None,
                                    "symbol_parse_status": "parsed",
                                }
                            )
                            norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                            norm_event["detail_fetched_at_ms"] = now_ms
                            norm_event["symbol_resolved_at_ms"] = now_ms
                            norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                            event_id = norm_event["event_id"]
                            if event_id not in seen_event_ids:
                                seen_event_ids.add(event_id)
                                append_jsonl(stream_paths["events"], norm_event)
                                events_detected.append(norm_event)

                                # Add to first_bar_queue
                                eq_item = dict(norm_event)
                                eq_item["first_futures_bar_status"] = "not_yet_available"
                                eq_item["first_futures_bar_start_ms"] = None
                                first_bar_queue.append(eq_item)

                            detail_retry_state.pop(code, None)
                        else:
                            # Derived candidates. Cache in state for exchangeInfo validation
                            state["derived_candidates"] = extraction_res["symbols"]
                            state["symbol_extraction_source"] = extraction_res["symbol_extraction_source"]
                            state["symbol_derivation_method"] = extraction_res["symbol_derivation_method"]
                            state["quote_derivation_source"] = "exchange_info"
                            state["symbol_validation_status"] = "unverified"

                            # Validate candidates immediately in same poll cycle
                            active_symbols, ex_ok = get_active_symbols()
                            if ex_ok:
                                validated_symbols = [s for s in state["derived_candidates"] if s in active_symbols]
                                if validated_symbols:
                                    detail_fetch_success_count += 1
                                    detail_symbol_extracted_count += 1

                                    norm_event = normalize_live_event(
                                        raw=state["raw"],
                                        source_parent_url=source_parent_url,
                                        detected_at_ms=state["first_detected_at_ms"],
                                        source_published_at_ms=state["raw"].get("releaseDate"),
                                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                        symbols_override=validated_symbols,
                                        extraction_metadata={
                                            "symbol_extraction_source": state["symbol_extraction_source"],
                                            "symbol_derivation_method": state["symbol_derivation_method"],
                                            "quote_derivation_source": "exchange_info",
                                            "symbol_validation_status": "validated",
                                            "detail_fetch_attempted": True,
                                            "detail_fetch_status": "success",
                                            "symbol_parse_failed_reason": None,
                                            "symbol_parse_status": "parsed",
                                        }
                                    )
                                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                                    norm_event["detail_fetched_at_ms"] = now_ms
                                    norm_event["symbol_resolved_at_ms"] = now_ms
                                    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                                    event_id = norm_event["event_id"]
                                    if event_id not in seen_event_ids:
                                        seen_event_ids.add(event_id)
                                        append_jsonl(stream_paths["events"], norm_event)
                                        events_detected.append(norm_event)

                                        # Add to first_bar_queue
                                        eq_item = dict(norm_event)
                                        eq_item["first_futures_bar_status"] = "not_yet_available"
                                        eq_item["first_futures_bar_start_ms"] = None
                                        first_bar_queue.append(eq_item)

                                    detail_retry_state.pop(code, None)
                    else:
                        detail_fetch_success_count += 1
                        detail_symbol_parse_failed_count += 1
                        symbol_empty_event_count += 1
                        symbol_parse_failed_count += 1

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
                                "detail_fetch_status": "success",
                                "symbol_parse_failed_reason": "detail_symbols_empty",
                                "symbol_parse_status": "terminal_failed",
                            }
                        )
                        norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                        norm_event["detail_fetched_at_ms"] = now_ms
                        norm_event["symbol_resolved_at_ms"] = now_ms
                        norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                        event_id = norm_event["event_id"]
                        if event_id not in seen_event_ids:
                            seen_event_ids.add(event_id)
                            append_jsonl(stream_paths["events"], norm_event)
                            events_detected.append(norm_event)

                        detail_retry_state.pop(code, None)
                else:
                    detail_fetch_failed_count += 1

                    # Write failed detail request manifest row
                    detail_manifest = {
                        "request_id": f"detail_{now_ms}_{code}",
                        "source_type": "announcement_detail" if not args.fixture_json else "fixture_detail",
                        "symbol": "ALL",
                        "url": detail_url,
                        "final_url": detail_url,
                        "http_status": fetch_res.get("http_status"),
                        "row_count": 0,
                        "error": fetch_res.get("error") or "fetch_failed",
                        "fetched_at_ms": now_ms,
                        "payload_sha256": None,
                        "payload_size_bytes": 0,
                        "payload_path": None,
                        "parser_version": PARSER_VERSION,
                        "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                    }
                    append_jsonl(stream_paths["request_manifest"], detail_manifest)
                    request_manifest.append(detail_manifest)

            append_jsonl(stream_paths["raw_payloads"], {"timestamp_ms": now_ms, "payload": payload})

            hb = cycle_res["heartbeat"]

        else:
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
        append_jsonl(stream_paths["heartbeats"], hb)
        heartbeats.append(hb)

        # 4. Check First Futures Bar for events in queue (only if live/readonly)
        if first_bar_queue and args.live_public_readonly and not args.fixture_json:
            budget = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_CHECK_BUDGET_PER_POLL", 3)

            active_symbols, ex_ok = get_active_symbols()

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

                if symbol not in active_symbols:
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
                    "source_type": "klines",
                    "symbol": symbol,
                    "url": klines_url,
                    "final_url": klines_url,
                    "http_status": 200 if kline_res else 400,
                    "row_count": len(kline_res) if kline_res else 0,
                    "error": kline_err,
                    "fetched_at_ms": int(time.time() * 1000),
                }
                append_jsonl(stream_paths["request_manifest"], k_manifest)
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
            "detail_fetch_attempted_count": detail_fetch_attempted_count,
            "detail_fetch_success_count": detail_fetch_success_count,
            "detail_fetch_failed_count": detail_fetch_failed_count,
            "detail_fetch_budget_deferred_count": detail_fetch_budget_deferred_count,
            "detail_fetch_url_rejected_count": detail_fetch_url_rejected_count,
            "detail_symbol_extracted_count": detail_symbol_extracted_count,
            "detail_symbol_parse_failed_count": detail_symbol_parse_failed_count,
            "title_symbol_extracted_count": title_symbol_extracted_count,
            "symbol_empty_event_count": symbol_empty_event_count,
        },
    )


    output_summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Summary written to {output_summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
