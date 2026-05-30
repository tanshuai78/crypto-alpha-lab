from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any

from scripts.fetch_third_party_liquidation_history import fetch_historical_liquidations
from src.research.liquidation_shock_event_study.coinalyze_1m import (
    normalize_coinalyze_1m_payload,
    normalize_interval,
)

logger = logging.getLogger(__name__)


def build_1m_fetch_summary(
    rows: list[dict[str, Any]],
    status_code: str | None = None,
    *,
    request_count: int = 0,
    requested_symbols: list[str] | None = None,
    interval: str = "1min",
    from_ts_sec: int = 0,
    to_ts_sec: int = 0,
) -> dict[str, Any]:
    symbols = sorted(list(set(row["symbol"] for row in rows)))
    symbol_count = len(symbols)
    row_count = len(rows)
    requested_symbols = sorted(requested_symbols or [])

    if rows:
        start_ts = min(row["bar_start_ms"] for row in rows)
        end_ts = max(row["bar_start_ms"] for row in rows)
        time_span_hours = int((end_ts - start_ts) / 3600000)
    else:
        start_ts = 0
        end_ts = 0
        time_span_hours = 0

    rows_per_symbol = {}
    for row in rows:
        sym = row["symbol"]
        rows_per_symbol[sym] = rows_per_symbol.get(sym, 0) + 1

    if status_code is None:
        api_key = os.environ.get("COINALYZE_API_KEY", "")
        if not api_key:
            status_code = "no_api_key"
        elif row_count == 0:
            status_code = "api_ok_empty_rows"
        else:
            status_code = "api_ok_non_empty_rows"

    return {
        "vendor": "coinalyze",
        "fetch_status": status_code,
        "symbol_count": symbol_count,
        "symbols": symbols,
        "request_count": request_count,
        "requested_symbols": requested_symbols,
        "interval": normalize_interval(interval),
        "from_ts_sec": from_ts_sec,
        "to_ts_sec": to_ts_sec,
        "row_count": row_count,
        "start_timestamp_ms": start_ts,
        "end_timestamp_ms": end_ts,
        "time_span_hours": time_span_hours,
        "rows_per_symbol": rows_per_symbol,
        "coverage_quality": "historical_vendor_dataset",
        "deduplicated_rows_count": row_count,
        "convert_to_usd": True,
        "vendor_granularity": "1min",
        "normalized_granularity": "1m",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch 1m third party liquidation history from Coinalyze."
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"],
        help="Symbols to fetch",
    )
    parser.add_argument("--interval", default="1min", help="Granularity interval, default 1min")
    parser.add_argument("--lookback-days", type=int, default=8, help="Lookback duration in days")
    parser.add_argument(
        "--output-jsonl",
        default="reports/liquidation_shock_event_study/liquidation_shock_1m_raw.jsonl",
        help="Output path for JSONL formatted rows",
    )
    parser.add_argument(
        "--summary-output",
        default="reports/liquidation_shock_event_study/liquidation_shock_1m_fetch_summary.json",
        help="Output path for the summary report",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    to_ts_sec = int(time.time())
    from_ts_sec = to_ts_sec - (args.lookback_days * 86400)

    symbol_statuses = []
    all_normalized_rows = []

    api_key = os.environ.get("COINALYZE_API_KEY", "")

    if not api_key:
        logger.error("COINALYZE_API_KEY environment variable is not set. Cannot run fetcher.")
        symbol_statuses.append("no_api_key")
    else:
        for idx, symbol in enumerate(args.symbols):
            # Strictly enforce 1.0s sleep frequency control between symbol requests
            if idx > 0:
                logger.info("Enforcing rate limit: sleeping for 1.0 seconds...")
                time.sleep(1.0)

            logger.info(f"Fetching 1m liquidation history for {symbol}...")
            try:
                payload, status = fetch_historical_liquidations(
                    symbol=symbol,
                    from_ts_sec=from_ts_sec,
                    to_ts_sec=to_ts_sec,
                    interval=args.interval,
                    api_key=api_key,
                )
                symbol_statuses.append(status)

                if payload:
                    normalized = normalize_coinalyze_1m_payload(payload, symbol=symbol)
                    all_normalized_rows.extend(normalized)
                    logger.info(
                        f"Successfully fetched and normalized {len(normalized)} rows for {symbol}."
                    )
                else:
                    logger.warning(f"No payload returned for {symbol}, status: {status}")
            except Exception as e:
                logger.error(f"Error processing symbol {symbol}: {e}")
                symbol_statuses.append("api_error")

    if not api_key:
        final_status = "no_api_key"
    elif any(s == "api_auth_failed" for s in symbol_statuses):
        final_status = "api_auth_failed"
    elif any(s == "api_rate_limited" for s in symbol_statuses):
        final_status = "api_rate_limited"
    elif any(s == "api_ok_non_empty_rows" for s in symbol_statuses):
        final_status = "api_ok_non_empty_rows"
    else:
        final_status = "api_ok_empty_rows"

    summary = build_1m_fetch_summary(
        all_normalized_rows,
        status_code=final_status,
        request_count=len(args.symbols),
        requested_symbols=args.symbols,
        interval=args.interval,
        from_ts_sec=from_ts_sec,
        to_ts_sec=to_ts_sec,
    )

    if args.output_jsonl:
        os.makedirs(os.path.dirname(os.path.abspath(args.output_jsonl)), exist_ok=True)
        sorted_rows = sorted(all_normalized_rows, key=lambda x: (x["symbol"], x["bar_start_ms"]))
        with open(args.output_jsonl, "w") as f:
            for row in sorted_rows:
                f.write(json.dumps(row) + "\n")
        logger.info(f"Saved normalized 1m rows to {args.output_jsonl}")

    if args.summary_output:
        os.makedirs(os.path.dirname(os.path.abspath(args.summary_output)), exist_ok=True)
        with open(args.summary_output, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved summary report to {args.summary_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
