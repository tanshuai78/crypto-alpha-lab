#!/usr/bin/env python3
"""
scripts/external_signal_shadow/run_stage1_4a_derivatives_stress_data_feasibility.py
"""

import argparse
import glob
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from configs.base import (
    EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_BASE_URL,
    EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC,
    EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS,
    EXTERNAL_SIGNAL_STAGE1_4_TIMEOUT_SEC,
)
from research.external_signal_shadow.stage1_4a_orchestrator import run_stage1_4a_feasibility_audit
from research.external_signal_shadow.stage1_4a_public_client import build_binance_public_url


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Stage 1.4A Derivatives Stress Data Feasibility Audit CLI"
    )
    parser.add_argument(
        "--fixture-summary-input",
        type=str,
        help="Path to fixture summary input JSON file.",
    )
    parser.add_argument(
        "--live-public-readonly",
        action="store_true",
        help="Trigger live readonly public REST probes to Binance.",
    )
    parser.add_argument(
        "--local-oi-archive",
        type=str,
        help="Glob pattern or path to local Open Interest JSONL archive files.",
    )
    parser.add_argument(
        "--local-force-order-archive",
        type=str,
        help="Glob pattern or path to local force order (liquidation) JSONL archive files.",
    )
    parser.add_argument(
        "--output-summary",
        type=str,
        required=True,
        help="Output path for feasibility summary JSON.",
    )
    return parser.parse_args(args)


def safe_http_get(url: str) -> bytes:
    """
    Performs an HTTP GET request. Propagates URLError to allow network detection.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "crypto-alpha-lab-research-readonly/0.1"}
    )
    with urllib.request.urlopen(req, timeout=EXTERNAL_SIGNAL_STAGE1_4_TIMEOUT_SEC) as response:
        return response.read()


def safe_http_head(url: str) -> bool:
    """
    Performs an HTTP HEAD request to check availability.
    Propagates URLError to caller, returns False on HTTP 404/etc.
    """
    req = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "crypto-alpha-lab-research-readonly/0.1"}
    )
    try:
        with urllib.request.urlopen(req, timeout=EXTERNAL_SIGNAL_STAGE1_4_TIMEOUT_SEC):
            return True
    except urllib.error.HTTPError:
        return False


def normalize_derivatives_symbol(symbol: str) -> str:
    """
    Normalizes CEX/CCXT symbols to UM uppercase clean format (e.g. BTC/USDT -> BTCUSDT).
    """
    return str(symbol).upper().replace("/", "").replace(":USDT", "")


def fetch_funding_history_pages(symbol: str, start_ms: int, end_ms: int) -> list[dict]:
    """
    Paginates and fetches funding rate history from Binance public REST.
    Deduplicates, sorts, and filters records after end_ms. Stops on stalls.
    """
    import time

    from configs.base import (
        EXTERNAL_SIGNAL_STAGE1_4_FUNDING_RATE_PATH,
        EXTERNAL_SIGNAL_STAGE1_4_PUBLIC_REST_PAGE_LIMIT,
        EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC,
    )

    rows = []
    current_start = start_ms
    page_count = 0
    stalled = False
    max_pages = 50

    while current_start <= end_ms and page_count < max_pages:
        time.sleep(EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC)
        url = build_binance_public_url(
            EXTERNAL_SIGNAL_STAGE1_4_FUNDING_RATE_PATH,
            {
                "symbol": symbol,
                "startTime": current_start,
                "endTime": end_ms,
                "limit": EXTERNAL_SIGNAL_STAGE1_4_PUBLIC_REST_PAGE_LIMIT,
            },
        )
        try:
            res_bytes = safe_http_get(url)
        except Exception:
            raise

        if not res_bytes:
            break

        res_data = json.loads(res_bytes.decode("utf-8"))
        if not isinstance(res_data, list) or len(res_data) == 0:
            break

        page_count += 1
        res_data.sort(key=lambda x: int(x.get("fundingTime", 0)))
        rows.extend(res_data)

        max_ts = max(int(r.get("fundingTime", 0)) for r in res_data)
        next_start = max_ts + 1

        if next_start <= current_start:
            stalled = True
            break

        current_start = next_start

    # Deduplicate by fundingTime
    seen_ts = set()
    deduped = []
    duplicate_count = 0
    for r in rows:
        ts = int(r.get("fundingTime", 0))
        if ts in seen_ts:
            duplicate_count += 1
            continue
        seen_ts.add(ts)
        deduped.append(r)

    deduped.sort(key=lambda x: int(x.get("fundingTime", 0)))
    filtered = [r for r in deduped if int(r.get("fundingTime", 0)) <= end_ms]

    class StatsList(list):
        pass

    res_list = StatsList(filtered)
    res_list.page_count = page_count
    res_list.duplicate_count = duplicate_count
    res_list.stalled = stalled
    return res_list


def fetch_futures_kline_pages(symbol: str, start_ms: int, end_ms: int) -> list[list]:
    """
    Paginates and fetches futures kline history (15m interval) from Binance public REST.
    Validates intervals and format, dedupes, and stops on stalls.
    """
    import time

    from configs.base import (
        EXTERNAL_SIGNAL_STAGE1_4_FUTURES_KLINES_PATH,
        EXTERNAL_SIGNAL_STAGE1_4_PUBLIC_REST_PAGE_LIMIT,
        EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC,
    )

    rows = []
    current_start = start_ms
    page_count = 0
    stalled = False
    max_pages = 100
    interval_ms = 15 * 60 * 1000

    malformed_count = 0
    duplicate_count = 0
    mismatch_count = 0

    while current_start < end_ms and page_count < max_pages:
        time.sleep(EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC)
        url = build_binance_public_url(
            EXTERNAL_SIGNAL_STAGE1_4_FUTURES_KLINES_PATH,
            {
                "symbol": symbol,
                "interval": "15m",
                "startTime": current_start,
                "endTime": end_ms,
                "limit": EXTERNAL_SIGNAL_STAGE1_4_PUBLIC_REST_PAGE_LIMIT,
            },
        )
        try:
            res_bytes = safe_http_get(url)
        except Exception:
            raise

        if not res_bytes:
            break

        res_data = json.loads(res_bytes.decode("utf-8"))
        if not isinstance(res_data, list) or len(res_data) == 0:
            break

        page_count += 1
        res_data.sort(key=lambda x: int(x[0]) if isinstance(x, list | tuple) and len(x) > 0 else 0)

        for item in res_data:
            if not isinstance(item, list | tuple) or len(item) < 8:
                malformed_count += 1
                continue

            open_time = int(item[0])
            close_time = int(item[6])

            if close_time - open_time + 1 != interval_ms:
                mismatch_count += 1

            rows.append(item)

        last_open = int(res_data[-1][0])
        next_start = last_open + interval_ms

        if next_start <= current_start:
            stalled = True
            break

        current_start = next_start

    # Deduplicate by open_time
    seen_ts = set()
    deduped = []
    for item in rows:
        ts = int(item[0])
        if ts in seen_ts:
            duplicate_count += 1
            continue
        seen_ts.add(ts)
        deduped.append(item)

    deduped.sort(key=lambda x: int(x[0]))
    filtered = [item for item in deduped if int(item[0]) < end_ms]

    class StatsList(list):
        pass

    res_list = StatsList(filtered)
    res_list.page_count = page_count
    res_list.malformed_count = malformed_count
    res_list.duplicate_count = duplicate_count
    res_list.mismatch_count = mismatch_count
    res_list.stalled = stalled
    return res_list



def load_jsonl_rows(glob_pattern: str) -> list[dict]:
    """
    Safely expands glob pattern and loads dictionary rows from JSONL files.
    """
    rows = []
    files = glob.glob(glob_pattern)
    for f in files:
        if not os.path.isfile(f):
            continue
        try:
            with open(f, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def main(args=None):
    parsed = parse_args(args)

    # Validate mutual exclusions
    if parsed.fixture_summary_input and parsed.live_public_readonly:
        print("ERROR: --fixture-summary-input and --live-public-readonly are mutually exclusive.", file=sys.stderr)
        return 1

    output_path = Path(parsed.output_summary)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Handle fixture mode
    if parsed.fixture_summary_input:
        try:
            with open(parsed.fixture_summary_input, "r", encoding="utf-8") as f:
                fixture_data = json.load(f)
        except Exception as e:
            print(f"ERROR: failed to load fixture summary input: {e}", file=sys.stderr)
            return 1

        # Enforce fixture_run = True, research_result_valid = False
        fixture_data["fixture_run"] = True
        fixture_data["research_result_valid"] = False
        fixture_data["expected_default_outcome"] = "stage1_4_data_degraded"
        fixture_data["preview_not_alpha"] = True
        fixture_data["candidate_replay_implemented"] = False
        fixture_data["forward_return_computed"] = False
        fixture_data["random_baseline_computed"] = False

        summary = run_stage1_4a_feasibility_audit(
            symbol_funding_rows={},
            symbol_oi_rows={},
            symbol_liquidation_rows={},
            symbol_price_rows={},
            preview_counts={"composite_overlap_window_count": 0, "composite_overlap_event_days": 0},
            global_metadata={"fixture_run": True},
        )
        summary.update(fixture_data)

        with open(output_path, "w", encoding="utf-8") as out:
            json.dump(summary, out, indent=2)
        print(f"Fixture summary written to {output_path}")
        return 0

    # Real feasibility run (live / local archives / mixed)
    symbol_funding_rows = {sym: [] for sym in EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS}
    symbol_oi_rows = {sym: [] for sym in EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS}
    symbol_liquidation_rows = {sym: [] for sym in EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS}
    symbol_price_rows = {sym: [] for sym in EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS}

    global_metadata = {
        "fixture_run": False,
        "live_trading_allowed": False,
        "safety_violation": False,
        "local_oi_archive_found": False,
        "local_force_order_archive_found": False,
        "network_mode": "local_archive",
    }

    # Load local open interest archive
    if parsed.local_oi_archive:
        oi_rows = load_jsonl_rows(parsed.local_oi_archive)
        if oi_rows:
            global_metadata["local_oi_archive_found"] = True
            for r in oi_rows:
                sym = r.get("symbol")
                if sym:
                    norm_sym = normalize_derivatives_symbol(sym)
                    if norm_sym in symbol_oi_rows:
                        r["symbol"] = norm_sym
                        r["source"] = "local_archive"
                        symbol_oi_rows[norm_sym].append(r)

    # Load local force order archive
    global_metadata["liquidation_unknown_schema_count"] = 0
    if parsed.local_force_order_archive:
        liq_rows = load_jsonl_rows(parsed.local_force_order_archive)
        if liq_rows:
            global_metadata["local_force_order_archive_found"] = True
            global_metadata["liquidation_source_type"] = "force_order_archive"
            for r in liq_rows:
                parsed_row = None
                if "o" in r and isinstance(r["o"], dict):
                    o = r["o"]
                    if all(k in o for k in ("s", "S", "p", "q", "T")):
                        parsed_row = {
                            "symbol": normalize_derivatives_symbol(o["s"]),
                            "side": o["S"].upper(),
                            "price": float(o["p"]),
                            "qty": float(o["q"]),
                            "origQty": float(o["q"]),
                            "time": int(o["T"]),
                        }
                elif all(k in r for k in ("symbol", "side", "price", "origQty", "time")):
                    parsed_row = {
                        "symbol": normalize_derivatives_symbol(r["symbol"]),
                        "side": r["side"].upper(),
                        "price": float(r["price"]),
                        "qty": float(r["origQty"]),
                        "origQty": float(r["origQty"]),
                        "time": int(r["time"]),
                    }
                elif all(k in r for k in ("symbol", "side", "price", "quantity")) and ("trade_time_ms" in r or "event_time_ms" in r):
                    t = r.get("trade_time_ms") or r.get("event_time_ms")
                    parsed_row = {
                        "symbol": normalize_derivatives_symbol(r["symbol"]),
                        "side": r["side"].upper(),
                        "price": float(r["price"]),
                        "qty": float(r["quantity"]),
                        "origQty": float(r["quantity"]),
                        "time": int(t),
                    }
                else:
                    global_metadata["liquidation_unknown_schema_count"] += 1
                    continue

                if parsed_row:
                    sym = parsed_row["symbol"]
                    if sym in symbol_liquidation_rows:
                        symbol_liquidation_rows[sym].append(parsed_row)

    network_error_occurred = False
    failure_reason = None

    # Run live probes
    if parsed.live_public_readonly:
        import time
        from datetime import timezone

        from configs.base import EXTERNAL_SIGNAL_STAGE1_4_REAL_AUDIT_HISTORY_DAYS
        global_metadata["network_mode"] = "live_public_readonly"

        end_ms = int(time.time() * 1000)
        start_ms = end_ms - (EXTERNAL_SIGNAL_STAGE1_4_REAL_AUDIT_HISTORY_DAYS * 24 * 60 * 60 * 1000)

        liquidation_manifest_available_days_by_symbol = {sym: 0 for sym in EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS}
        liquidation_manifest_history_days_by_symbol = {sym: 0 for sym in EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS}
        liquidation_manifest_coverage_ratio_by_symbol = {sym: 0.0 for sym in EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS}

        dates = []
        for i in range(EXTERNAL_SIGNAL_STAGE1_4_REAL_AUDIT_HISTORY_DAYS):
            dates.append((datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d"))

        summary_pagination_stats = {
            "funding_pagination_page_count": 0,
            "funding_duplicate_record_count": 0,
            "funding_pagination_stalled": False,
            "price_malformed_kline_count": 0,
            "price_duplicate_open_time_count": 0,
            "price_interval_mismatch_count": 0,
            "liquidation_manifest_requested_days": EXTERNAL_SIGNAL_STAGE1_4_REAL_AUDIT_HISTORY_DAYS,
            "liquidation_manifest_available_days_by_symbol": liquidation_manifest_available_days_by_symbol,
            "liquidation_manifest_history_days_by_symbol": liquidation_manifest_history_days_by_symbol,
            "liquidation_manifest_coverage_ratio_by_symbol": liquidation_manifest_coverage_ratio_by_symbol,
        }

        for sym in EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS:
            # 1. Paginate fundingRate
            try:
                funding_list = fetch_funding_history_pages(sym, start_ms, end_ms)
                symbol_funding_rows[sym].extend(funding_list)
                summary_pagination_stats["funding_pagination_page_count"] += getattr(funding_list, "page_count", 0)
                summary_pagination_stats["funding_duplicate_record_count"] += getattr(funding_list, "duplicate_count", 0)
                if getattr(funding_list, "stalled", False):
                    summary_pagination_stats["funding_pagination_stalled"] = True
            except urllib.error.URLError as e:
                network_error_occurred = True
                failure_reason = str(e.reason) if hasattr(e, "reason") else str(e)
                break
            except Exception as e:
                network_error_occurred = True
                failure_reason = str(e)
                break

            # 2. Paginate klines
            try:
                kline_list = fetch_futures_kline_pages(sym, start_ms, end_ms)
                symbol_price_rows[sym].extend(kline_list)
                summary_pagination_stats["price_malformed_kline_count"] += getattr(kline_list, "malformed_count", 0)
                summary_pagination_stats["price_duplicate_open_time_count"] += getattr(kline_list, "duplicate_count", 0)
                summary_pagination_stats["price_interval_mismatch_count"] += getattr(kline_list, "mismatch_count", 0)
            except urllib.error.URLError as e:
                network_error_occurred = True
                failure_reason = str(e.reason) if hasattr(e, "reason") else str(e)
                break
            except Exception as e:
                network_error_occurred = True
                failure_reason = str(e)
                break

            # 3. Daily probe for Binance Vision CM liquidationSnapshot manifest
            cm_sym = None
            from configs.base import EXTERNAL_SIGNAL_STAGE1_4_CM_TO_UM_SYMBOL_MAP
            for cm_k, um_v in EXTERNAL_SIGNAL_STAGE1_4_CM_TO_UM_SYMBOL_MAP.items():
                if um_v == sym:
                    cm_sym = cm_k
                    break

            if cm_sym:
                # If local force order archive is present, manifest probe is ignored by orchestrator.
                # Skip 900+ HEAD requests to prevent unnecessary network delay and rate-limits.
                if global_metadata.get("local_force_order_archive_found", False):
                    continue

                avail_count = 0
                for date_str in dates:
                    vision_url = (
                        f"{EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_BASE_URL.rstrip('/')}"
                        f"/data/futures/cm/daily/liquidationSnapshot/{cm_sym}"
                        f"/{cm_sym}-liquidationSnapshot-{date_str}.zip"
                    )
                    try:
                        time.sleep(EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC)
                        if safe_http_head(vision_url):
                            avail_count += 1
                    except urllib.error.URLError as e:
                        network_error_occurred = True
                        failure_reason = str(e.reason) if hasattr(e, "reason") else str(e)
                        break
                    except Exception as e:
                        network_error_occurred = True
                        failure_reason = str(e)
                        break

                if network_error_occurred:
                    break

                liquidation_manifest_available_days_by_symbol[sym] = avail_count
                liquidation_manifest_history_days_by_symbol[sym] = avail_count
                liquidation_manifest_coverage_ratio_by_symbol[sym] = float(avail_count / EXTERNAL_SIGNAL_STAGE1_4_REAL_AUDIT_HISTORY_DAYS)

        global_metadata.update(summary_pagination_stats)
        global_metadata["liquidation_manifest_available_days_by_symbol"] = liquidation_manifest_available_days_by_symbol

    # If network error occurred, write failure summary
    if network_error_occurred:
        failure_summary = {
            "outcome": "stage1_4_data_unavailable",
            "primary_blocker": "network_probe_error",
            "failure_reason": failure_reason,
            "usable": False,
            "research_result_valid": True,
            "fixture_run": False,
            "stage1_4b_candidate_replay_allowed": False,
            "composite_replay_allowed": False,
            "live_trading_allowed": False,
            "local_oi_archive_found": global_metadata["local_oi_archive_found"],
            "local_force_order_archive_found": global_metadata["local_force_order_archive_found"],
            "network_mode": global_metadata["network_mode"],
        }
        with open(output_path, "w", encoding="utf-8") as out:
            json.dump(failure_summary, out, indent=2)
        print(f"Network failure summary written to {output_path}. Reason: {failure_reason}")
        return 0


    # Calculate preview counts
    overlap_days = 0
    overlap_windows = 0

    liq_timestamps = []
    price_timestamps = []

    for sym in EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS:
        for r in symbol_liquidation_rows.get(sym, []):
            t = r.get("time") or r.get("timestamp")
            if t is not None:
                liq_timestamps.append(int(t))
        for r in symbol_price_rows.get(sym, []):
            t = r[0] if isinstance(r, list | tuple) else r.get("bar_start_ms")
            if t is not None:
                price_timestamps.append(int(t))

    if liq_timestamps and price_timestamps:
        liq_days_set = {ts // (24 * 60 * 60 * 1000) for ts in liq_timestamps}
        price_days_set = {ts // (24 * 60 * 60 * 1000) for ts in price_timestamps}
        overlap_days = len(liq_days_set & price_days_set)
        overlap_windows = len(liq_timestamps)

    preview_counts = {
        "composite_overlap_window_count": overlap_windows,
        "composite_overlap_event_days": overlap_days,
    }

    # Run orchestrator
    summary = run_stage1_4a_feasibility_audit(
        symbol_funding_rows=symbol_funding_rows,
        symbol_oi_rows=symbol_oi_rows,
        symbol_liquidation_rows=symbol_liquidation_rows,
        symbol_price_rows=symbol_price_rows,
        preview_counts=preview_counts,
        global_metadata=global_metadata,
        liquidation_proxy_accepted_for_full_replay=False,
    )

    # Inject required metadata details
    summary.update(global_metadata)


    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(summary, out, indent=2)

    print(f"Feasibility summary written to {output_path}")
    return 0



if __name__ == "__main__":
    sys.exit(main())
