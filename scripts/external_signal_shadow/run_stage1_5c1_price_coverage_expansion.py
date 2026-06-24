import argparse
import json
import os
import sys
import time
from pathlib import Path

from configs import base
from src.research.external_signal_shadow.stage1_5c1_price_coverage_builder import (
    build_event_coverage_report,
    dedupe_kline_rows,
    filter_futures_coverage_pass_events,
    summarize_coverage_reports,
)
from src.research.external_signal_shadow.stage1_5c1_price_coverage_client import (
    build_klines_url,
    build_request_manifest_row,
    filter_exchange_symbols,
    iter_kline_request_slices,
    next_start_after_kline_batch,
    parse_kline_array,
    public_get_json,
)
from src.research.external_signal_shadow.stage1_5c1_price_coverage_loader import (
    build_event_request_window,
    load_stage1_5b_events,
    merge_symbol_windows,
)


def write_jsonl(path: str | Path, rows: list[dict]):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def write_json(path: str | Path, data: dict):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1.5C.1: Price Coverage Expansion")
    parser.add_argument("--events-jsonl", required=True, help="Path to Stage 1.5B events")
    parser.add_argument("--stage1-5b-summary", required=True, help="Path to Stage 1.5B summary")
    parser.add_argument("--output-futures-jsonl", required=True, help="Path to write futures price archive")
    parser.add_argument("--output-spot-proxy-jsonl", required=False, help="Path to write spot proxy archive")
    parser.add_argument("--output-event-report-jsonl", required=True, help="Path to write event coverage report")
    parser.add_argument("--output-summary", required=True, help="Path to write summary JSON")
    parser.add_argument("--output-request-manifest-jsonl", required=True, help="Path to write request manifest")
    parser.add_argument("--output-futures-coverage-pass-events-jsonl", required=True, help="Path to write coverage-pass events")
    parser.add_argument("--include-spot-proxy", action="store_true", help="Fetch spot klines as reference proxy")
    parser.add_argument("--live-public-readonly", action="store_true", help="Explicit switch to permit public REST calls")
    parser.add_argument("--mock-response-dir", required=False, help="Local directory containing mock json responses")

    args = parser.parse_args()

    # 1. Assert Stage 1.5B ready
    if not os.path.exists(args.stage1_5b_summary):
        print(f"Error: Stage 1.5B summary not found at {args.stage1_5b_summary}")
        return 1
    with open(args.stage1_5b_summary, "r", encoding="utf-8") as f:
        summary_1_5b = json.load(f)
    if summary_1_5b.get("decision") != "stage1_5b_event_table_ready":
        print(f"Error: Stage 1.5B is not ready. Decision was: {summary_1_5b.get('decision')}")
        return 1

    # 2. Check permission for live network
    if not args.live_public_readonly and not args.mock_response_dir:
        print("Error: Running in public readonly mode requires --live-public-readonly or --mock-response-dir.")
        # Write invalid/blocker summary
        summary_err = {
            "decision": "stage1_5c1_price_coverage_invalid",
            "blockers": ["live_public_readonly_permission_required"],
            "api_key_used": False,
            "private_endpoint_used": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False
        }
        write_json(args.output_summary, summary_err)
        return 2

    # 3. Load events
    if not os.path.exists(args.events_jsonl):
        print(f"Error: Events file not found at {args.events_jsonl}")
        return 1
    events = load_stage1_5b_events(args.events_jsonl)
    if not events:
        summary_err = {
            "decision": "stage1_5c1_price_coverage_invalid",
            "blockers": ["empty_input_event_table"],
            "api_key_used": False,
            "private_endpoint_used": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False
        }
        write_json(args.output_summary, summary_err)
        return 0

    # 4. Load or fetch exchangeInfo
    futures_exchange_info = None
    spot_exchange_info = None

    if args.mock_response_dir:
        mock_dir = Path(args.mock_response_dir)
        with open(mock_dir / "futures_exchange_info.json", "r", encoding="utf-8") as f:
            futures_exchange_info = json.load(f)
        with open(mock_dir / "spot_exchange_info.json", "r", encoding="utf-8") as f:
            spot_exchange_info = json.load(f)
    else:
        # Fetch live public readonly exchangeInfo
        futures_url = f"{base.EXTERNAL_SIGNAL_STAGE1_5C1_BINANCE_FAPI_BASE_URL}{base.EXTERNAL_SIGNAL_STAGE1_5C1_FUTURES_EXCHANGE_INFO_PATH}"
        futures_res = public_get_json(futures_url, live_public_readonly=True, timeout_sec=base.EXTERNAL_SIGNAL_STAGE1_5C1_TIMEOUT_SEC)
        if not futures_res["ok"]:
            print(f"Error fetching futures exchangeInfo: {futures_res['error']}")
            summary_err = {
                "decision": "stage1_5c1_price_coverage_invalid",
                "blockers": ["futures_exchangeinfo_api_failure"],
                "api_key_used": False,
                "private_endpoint_used": False
            }
            write_json(args.output_summary, summary_err)
            return 1
        futures_exchange_info = futures_res["payload"]

        # Save raw cache
        write_json("data/external_signal_shadow/stage1_5c1/price_coverage/futures_exchange_info_raw.json", futures_exchange_info)

        if args.include_spot_proxy:
            spot_url = f"{base.EXTERNAL_SIGNAL_STAGE1_5C1_BINANCE_SPOT_BASE_URL}{base.EXTERNAL_SIGNAL_STAGE1_5C1_SPOT_EXCHANGE_INFO_PATH}"
            spot_res = public_get_json(spot_url, live_public_readonly=True, timeout_sec=base.EXTERNAL_SIGNAL_STAGE1_5C1_TIMEOUT_SEC)
            if spot_res["ok"]:
                spot_exchange_info = spot_res["payload"]
                write_json("data/external_signal_shadow/stage1_5c1/price_coverage/spot_exchange_info_raw.json", spot_exchange_info)

    # Validate symbols against current exchangeInfo
    futures_verified_symbols = filter_exchange_symbols(futures_exchange_info, market_type="futures")
    spot_verified_symbols = filter_exchange_symbols(spot_exchange_info, market_type="spot") if spot_exchange_info else set()

    # 5. Build and merge request windows
    now_ms = int(time.time() * 1000)

    futures_windows = []
    spot_windows = []

    for e in events:
        w = build_event_request_window(e, now_ms)
        # Verify if symbol currently exists on futures
        symbol = w["symbol"]

        # Futures request window
        if symbol in futures_verified_symbols:
            futures_windows.append({
                "source_type": "futures",
                "symbol": symbol,
                "start_ms": w["start_ms"],
                "end_ms": w["end_ms"]
            })

        # Spot request window (if requested)
        if args.include_spot_proxy and symbol in spot_verified_symbols:
            spot_windows.append({
                "source_type": "spot",
                "symbol": symbol,
                "start_ms": w["start_ms"],
                "end_ms": w["end_ms"]
            })

    merged_futures_windows = merge_symbol_windows(futures_windows, base.EXTERNAL_SIGNAL_STAGE1_5C1_MERGE_GAP_MS)
    merged_spot_windows = merge_symbol_windows(spot_windows, base.EXTERNAL_SIGNAL_STAGE1_5C1_MERGE_GAP_MS)

    # 6. Safety check: request budget
    # Estimate total requests: count number of slices per merged window
    limit = base.EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_LIMIT
    interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_INTERVAL_MS

    estimated_kline_requests = 0
    for w in merged_futures_windows:
        slices = iter_kline_request_slices(w["start_ms"], w["end_ms"], interval_ms, limit)
        estimated_kline_requests += len(slices)
    for w in merged_spot_windows:
        slices = iter_kline_request_slices(w["start_ms"], w["end_ms"], interval_ms, limit)
        estimated_kline_requests += len(slices)

    unique_symbols = set(w["symbol"] for w in (merged_futures_windows + merged_spot_windows))

    if len(unique_symbols) > base.EXTERNAL_SIGNAL_STAGE1_5C1_MAX_SYMBOLS_PER_RUN or \
       estimated_kline_requests > base.EXTERNAL_SIGNAL_STAGE1_5C1_MAX_KLINE_REQUESTS_PER_RUN:
        print(f"Safety Block: Request budget exceeded! Symbols: {len(unique_symbols)} (Max: {base.EXTERNAL_SIGNAL_STAGE1_5C1_MAX_SYMBOLS_PER_RUN}), Requests: {estimated_kline_requests} (Max: {base.EXTERNAL_SIGNAL_STAGE1_5C1_MAX_KLINE_REQUESTS_PER_RUN})")
        summary_err = {
            "decision": "stage1_5c1_price_coverage_invalid",
            "blockers": ["request_budget_exceeded"],
            "api_key_used": False,
            "private_endpoint_used": False
        }
        write_json(args.output_summary, summary_err)
        return 0

    # 7. Fetch klines
    futures_bars = []
    spot_bars = []
    manifest_rows = []
    request_counter = 0

    # Downloader loop helper
    def download_kline_archive(merged_windows: list[dict], source_type: str, base_url: str, path: str) -> list[dict]:
        nonlocal request_counter
        fetched_rows = []

        for w in merged_windows:
            symbol = w["symbol"]
            start_ms = w["start_ms"]
            end_ms = w["end_ms"]

            if args.mock_response_dir:
                # Load mock
                mock_file = Path(args.mock_response_dir) / f"{source_type}_{symbol}_{start_ms}_{end_ms}.json"
                if mock_file.exists():
                    with open(mock_file, "r", encoding="utf-8") as f:
                        raw_klines = json.load(f)
                    for k in raw_klines:
                        row = parse_kline_array(k, symbol, "binance_um_futures_15m" if source_type == "futures" else "binance_spot_15m_proxy")
                        fetched_rows.append(row)

                    # Record manifest
                    manifest_rows.append(build_request_manifest_row(
                        request_id=f"req_{request_counter}",
                        source_type=source_type,
                        symbol=symbol,
                        url=f"mock://{source_type}/{symbol}",
                        start_ms=start_ms,
                        end_ms=end_ms,
                        http_status=200,
                        row_count=len(raw_klines),
                        retry_count=0,
                        error=None
                    ))
                    request_counter += 1
                continue

            # Real network download with pagination
            current_start = start_ms
            while current_start < end_ms:
                # Sleep between requests to respect rate limits
                if request_counter > 0:
                    time.sleep(base.EXTERNAL_SIGNAL_STAGE1_5C1_REQUEST_SLEEP_SEC)

                # Determine endpoint limit
                chunk_ms = limit * interval_ms
                current_end = min(current_start + chunk_ms, end_ms)

                url = build_klines_url(base_url, path, symbol, base.EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_INTERVAL, current_start, current_end, limit)

                req_id = f"req_{request_counter}"
                res = public_get_json(url, live_public_readonly=True, timeout_sec=base.EXTERNAL_SIGNAL_STAGE1_5C1_TIMEOUT_SEC, retry_budget=base.EXTERNAL_SIGNAL_STAGE1_5C1_RETRY_BUDGET)
                request_counter += 1

                if not res["ok"]:
                    print(f"Error fetching klines for {symbol}: {res['error']}")
                    manifest_rows.append(build_request_manifest_row(
                        request_id=req_id,
                        source_type=source_type,
                        symbol=symbol,
                        url=url,
                        start_ms=current_start,
                        end_ms=current_end,
                        http_status=res["http_status"],
                        row_count=0,
                        retry_count=base.EXTERNAL_SIGNAL_STAGE1_5C1_RETRY_BUDGET,
                        error=res["error"]
                    ))
                    # Stop paginating this symbol window on error (graceful degradation)
                    break

                raw_klines = res["payload"]
                if not raw_klines:
                    # Empty payload, stop paginating
                    manifest_rows.append(build_request_manifest_row(
                        request_id=req_id,
                        source_type=source_type,
                        symbol=symbol,
                        url=url,
                        start_ms=current_start,
                        end_ms=current_end,
                        http_status=200,
                        row_count=0,
                        retry_count=0,
                        error=None
                    ))
                    break

                for k in raw_klines:
                    row = parse_kline_array(k, symbol, "binance_um_futures_15m" if source_type == "futures" else "binance_spot_15m_proxy")
                    fetched_rows.append(row)

                manifest_rows.append(build_request_manifest_row(
                    request_id=req_id,
                    source_type=source_type,
                    symbol=symbol,
                    url=url,
                    start_ms=current_start,
                    end_ms=current_end,
                    http_status=200,
                    row_count=len(raw_klines),
                    retry_count=0,
                    error=None
                ))

                # Advance startTime using pagination helper
                next_start = next_start_after_kline_batch(raw_klines, interval_ms)
                if not next_start or next_start <= current_start:
                    break
                current_start = next_start

        return fetched_rows

    # 7.1 Fetch futures klines
    futures_bars = download_kline_archive(
        merged_windows=merged_futures_windows,
        source_type="futures",
        base_url=base.EXTERNAL_SIGNAL_STAGE1_5C1_BINANCE_FAPI_BASE_URL,
        path=base.EXTERNAL_SIGNAL_STAGE1_5C1_FUTURES_KLINES_PATH
    )

    # 7.2 Fetch spot klines (optional)
    if args.include_spot_proxy:
        spot_bars = download_kline_archive(
            merged_windows=merged_spot_windows,
            source_type="spot",
            base_url=base.EXTERNAL_SIGNAL_STAGE1_5C1_BINANCE_SPOT_BASE_URL,
            path=base.EXTERNAL_SIGNAL_STAGE1_5C1_SPOT_KLINES_PATH
        )

    # 8. Deduplicate K-lines
    deduped_futures = dedupe_kline_rows(futures_bars)
    deduped_spot = dedupe_kline_rows(spot_bars)

    # 9. Build event coverage reports
    coverage_reports = []
    for e in events:
        symbol = e["symbol"]
        f_verified = symbol in futures_verified_symbols
        s_verified = symbol in spot_verified_symbols

        report = build_event_coverage_report(
            event=e,
            futures_bars=deduped_futures,
            spot_bars=deduped_spot,
            futures_symbol_verified=f_verified,
            spot_symbol_verified=s_verified,
            current_time_ms=now_ms
        )
        coverage_reports.append(report)

    # 10. Write output files
    write_jsonl(args.output_futures_jsonl, deduped_futures)
    if args.output_spot_proxy_jsonl:
        write_jsonl(args.output_spot_proxy_jsonl, deduped_spot)

    write_jsonl(args.output_event_report_jsonl, coverage_reports)
    write_jsonl(args.output_request_manifest_jsonl, manifest_rows)

    # 11. Write coverage-pass events for Stage 1.5C
    pass_events = filter_futures_coverage_pass_events(events, coverage_reports)
    write_jsonl(args.output_futures_coverage_pass_events_jsonl, pass_events)

    # 12. Write summary
    summary_data = summarize_coverage_reports(coverage_reports)
    write_json(args.output_summary, summary_data)

    print(f"Stage 1.5C.1 Expansion completed. Decision: {summary_data['decision']}")
    print(f"Rerun Candidates: {summary_data['futures_coverage_pass_event_count']} / {summary_data['stage1_5b_symbol_events']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
