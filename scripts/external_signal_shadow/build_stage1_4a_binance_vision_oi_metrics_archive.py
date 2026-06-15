#!/usr/bin/env python3
"""
scripts/external_signal_shadow/build_stage1_4a_binance_vision_oi_metrics_archive.py

Downloads and converts daily metrics ZIP files from Binance Vision to populate
local Open Interest (OI) historical archives.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))
from configs import base


def build_metrics_zip_url(base_url: str, symbol: str, date_str: str) -> str:
    """
    Build the URL for the daily metrics ZIP archive on Binance Vision.
    Template: /data/futures/um/daily/metrics/{symbol}/{symbol}-metrics-{date}.zip
    """
    return f"{base_url.rstrip('/')}/data/futures/um/daily/metrics/{symbol}/{symbol}-metrics-{date_str}.zip"


def parse_metrics_create_time_ms(time_str: str) -> int:
    """
    Parse create_time in local-like format from CSV (e.g. '2024-01-01 00:00:00')
    using UTC timezone-aware parsing to prevent local machine offset issues.
    Returns timestamp in milliseconds.
    """
    dt = datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def convert_metrics_csv_line(header: list[str], line: list[str], source_file: str) -> dict:
    """
    Convert a single CSV metrics row to the Stage 1.4 target Open Interest format.
    """
    symbol_idx = header.index("symbol")
    oi_idx = header.index("sum_open_interest")
    oiv_idx = header.index("sum_open_interest_value")
    time_idx = header.index("create_time")

    return {
        "symbol": line[symbol_idx].strip(),
        "sumOpenInterest": line[oi_idx].strip(),
        "sumOpenInterestValue": line[oiv_idx].strip(),
        "timestamp": parse_metrics_create_time_ms(line[time_idx]),
        "source": "binance_vision_um_daily_metrics",
        "source_file": source_file,
    }


def infer_interval_ms(rows: list[dict]) -> int:
    """
    Dynamically infer the metrics row interval in milliseconds by computing
    the median of positive deltas between sorted timestamps.
    """
    if len(rows) < 2:
        return 0
    timestamps = sorted(list(set(r["timestamp"] for r in rows)))
    deltas = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
    positive_deltas = [d for d in deltas if d > 0]
    if not positive_deltas:
        return 0
    positive_deltas.sort()
    n = len(positive_deltas)
    if n % 2 == 1:
        return positive_deltas[n // 2]
    else:
        return (positive_deltas[n // 2 - 1] + positive_deltas[n // 2]) // 2


def convert_metrics_zip_to_jsonl(zip_path: str, target_symbol: str) -> tuple[list[dict], int, int]:
    """
    Reads the ZIP archive, parses the CSV file inside, and maps records to target format.
    Returns (valid_rows, malformed_count, duplicate_count).
    """
    rows = []
    malformed = 0
    duplicates = 0
    seen_timestamps = set()

    source_file = os.path.basename(zip_path)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Locate CSV file in the zip
            csv_files = [name for name in zf.namelist() if name.endswith(".csv")]
            if not csv_files:
                return [], 0, 0

            # Read first CSV file content
            with zf.open(csv_files[0], "r") as f:
                content = f.read().decode("utf-8")
                reader = csv.reader(content.splitlines())

                header = next(reader, None)
                if not header:
                    return [], 0, 0

                # Check for required headers
                required = ["create_time", "symbol", "sum_open_interest", "sum_open_interest_value"]
                for req in required:
                    if req not in header:
                        return [], 0, 0

                for line in reader:
                    if len(line) < len(header):
                        malformed += 1
                        continue
                    try:
                        row = convert_metrics_csv_line(header, line, source_file)
                        # Filter for target symbol
                        if row["symbol"].upper() != target_symbol.upper():
                            continue

                        ts = row["timestamp"]
                        if ts in seen_timestamps:
                            duplicates += 1
                            continue
                        seen_timestamps.add(ts)
                        rows.append(row)
                    except Exception:
                        malformed += 1
    except Exception:
        # ZIP file error or general parsing crash
        malformed += 1

    return rows, malformed, duplicates


def main(args_list: list[str] = None) -> int:
    parser = argparse.ArgumentParser(description="Binance Vision Daily Metrics Open Interest Downloader/Converter")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"])
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--end-date", type=str, help="YYYY-MM-DD end date (default UTC today)")
    parser.add_argument("--output", type=str, default=base.EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_OI_OUTPUT_JSONL)
    parser.add_argument("--output-summary", type=str, help="Optional JSON path to write downloader execution summary")
    parser.add_argument("--live-public-readonly", action="store_true", help="Authorize actual public HTTP requests")
    parser.add_argument("--mock-zip-dir", type=str, help="Local directory path to read mock ZIP files from instead of download")

    args = parser.parse_args(args_list)

    # Calculate end date and list of dates
    if args.end_date:
        end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        end_dt = datetime.now(timezone.utc)

    dates = []
    for i in range(args.days):
        date_dt = end_dt - timedelta(days=i)
        dates.append(date_dt.strftime("%Y-%m-%d"))
    dates.reverse()  # Chronological

    # Ensure parent output directories exist
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    if args.output_summary:
        Path(args.output_summary).parent.mkdir(parents=True, exist_ok=True)

    # Track downloader stats
    summary = {
        "source": "binance_vision_um_daily_metrics",
        "requested_symbol_count": len(args.symbols),
        "requested_days": args.days,
        "download_success_count": 0,
        "download_failure_count": 0,
        "row_count": 0,
        "symbol_row_counts": {},
        "history_days_by_symbol": {},
        "inferred_interval_ms_by_symbol": {},
        "duplicate_row_count": 0,
        "malformed_row_count": 0,
        "output_file": args.output,
        "live_trading_allowed": False,
        "api_key_used": False,
    }

    all_rows = []
    total_duplicates = 0
    total_malformed = 0

    # Create a local cache dir for downloaded zips if running --live-public-readonly
    cache_dir = Path("data/external_signal_shadow/derivatives_stress/cache")
    if args.live_public_readonly:
        cache_dir.mkdir(parents=True, exist_ok=True)

    for symbol in args.symbols:
        symbol_rows = []
        symbol_success_days = 0

        for date_str in dates:
            zip_filename = f"{symbol}-metrics-{date_str}.zip"
            zip_path = None

            if args.mock_zip_dir:
                # Local mock ZIP path
                candidate = Path(args.mock_zip_dir) / symbol / zip_filename
                if not candidate.exists():
                    # Fallback directly in the mock dir
                    candidate = Path(args.mock_zip_dir) / zip_filename

                if candidate.exists():
                    zip_path = str(candidate)
                    summary["download_success_count"] += 1
                    symbol_success_days += 1
                else:
                    summary["download_failure_count"] += 1
            elif args.live_public_readonly:
                # Live download
                url = build_metrics_zip_url(base.EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_BASE_URL, symbol, date_str)
                local_dest = cache_dir / zip_filename

                # Check if already cached
                if local_dest.exists():
                    zip_path = str(local_dest)
                    summary["download_success_count"] += 1
                    symbol_success_days += 1
                else:
                    try:
                        # Polite delay
                        time.sleep(base.EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC)
                        urllib.request.urlretrieve(url, str(local_dest))
                        zip_path = str(local_dest)
                        summary["download_success_count"] += 1
                        symbol_success_days += 1
                    except urllib.error.HTTPError:
                        # ZIP does not exist or rate-limited
                        summary["download_failure_count"] += 1
                    except Exception:
                        summary["download_failure_count"] += 1
            else:
                # No network access allowed and no mock dir
                summary["download_failure_count"] += 1

            if zip_path:
                rows, malformed, duplicates = convert_metrics_zip_to_jsonl(zip_path, symbol)
                symbol_rows.extend(rows)
                total_malformed += malformed
                total_duplicates += duplicates

        # Post-process per-symbol data
        if symbol_rows:
            # Sort by timestamp
            symbol_rows.sort(key=lambda x: x["timestamp"])

            # Infer interval
            inferred_int = infer_interval_ms(symbol_rows)
            summary["inferred_interval_ms_by_symbol"][symbol] = inferred_int

            # Calculate history days span
            min_ts = symbol_rows[0]["timestamp"]
            max_ts = symbol_rows[-1]["timestamp"]
            days_span = (max_ts - min_ts) / (1000 * 60 * 60 * 24)
            summary["history_days_by_symbol"][symbol] = round(days_span, 2)
            summary["symbol_row_counts"][symbol] = len(symbol_rows)
            all_rows.extend(symbol_rows)
        else:
            summary["inferred_interval_ms_by_symbol"][symbol] = 0
            summary["history_days_by_symbol"][symbol] = 0.0
            summary["symbol_row_counts"][symbol] = 0

    # Sort final combined dataset by symbol and timestamp
    all_rows.sort(key=lambda x: (x["symbol"], x["timestamp"]))

    # Deduplicate final rows (just in case across files, though zip parsing checks this)
    deduped_rows = []
    seen = set()
    for row in all_rows:
        key = (row["symbol"], row["timestamp"])
        if key in seen:
            total_duplicates += 1
            continue
        seen.add(key)
        deduped_rows.append(row)

    # Write JSONL output
    with open(args.output, "w", encoding="utf-8") as f:
        for row in deduped_rows:
            f.write(json.dumps(row) + "\n")

    summary["row_count"] = len(deduped_rows)
    summary["duplicate_row_count"] = total_duplicates
    summary["malformed_row_count"] = total_malformed

    # Write summary
    if args.output_summary:
        with open(args.output_summary, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

    # Console logging loguru style
    print(f"Build metrics completed. Output: {args.output}, Rows: {len(deduped_rows)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
