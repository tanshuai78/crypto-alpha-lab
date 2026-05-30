from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

# Reuse existing fetching utilities
from scripts.fetch_third_party_liquidation_history import fetch_historical_liquidations

logger = logging.getLogger(__name__)


def determine_decision(
    rows_per_symbol: dict[str, int],
    requested_symbols: list[str],
    api_status: str,
) -> str:
    if api_status in ("no_api_key", "api_auth_failed", "api_rate_limited") or api_status.startswith(
        "api_error"
    ):
        return "api_unavailable"

    required_bars = 2016 + 288  # 2304 bars

    sufficient_symbols = []
    insufficient_symbols = []

    for symbol in requested_symbols:
        count = rows_per_symbol.get(symbol, 0)
        if count >= required_bars:
            sufficient_symbols.append(symbol)
        else:
            insufficient_symbols.append(symbol)

    if len(sufficient_symbols) == len(requested_symbols):
        return "proceed"
    elif len(sufficient_symbols) > 0:
        return "partial_symbol_support"
    else:
        return "insufficient_5m_depth"


def probe_feasibility(
    symbols: list[str],
    lookback_days: int = 8,
    api_key: str | None = None,
) -> dict[str, Any]:
    if not api_key:
        api_key = os.environ.get("COINALYZE_API_KEY", "")

    to_ts_sec = int(time.time())
    from_ts_sec = to_ts_sec - (lookback_days * 86400)

    rows_per_symbol: dict[str, int] = {}
    min_bar_start_ms: dict[str, int | None] = {}
    max_bar_start_ms: dict[str, int | None] = {}
    span_days_per_symbol: dict[str, float] = {}

    api_statuses = []

    for idx, symbol in enumerate(symbols):
        if idx > 0:
            time.sleep(1.0)

        logger.info(f"Probing 5m feasibility for {symbol}...")
        try:
            payload, status = fetch_historical_liquidations(
                symbol=symbol,
                from_ts_sec=from_ts_sec,
                to_ts_sec=to_ts_sec,
                interval="5min",
                api_key=api_key,
            )
        except Exception as e:
            logger.error(f"Error fetching for {symbol}: {e}")
            payload, status = [], "api_error"

        api_statuses.append(status)

        history_rows = []
        if payload:
            for item in payload:
                if isinstance(item, dict) and isinstance(item.get("history"), list):
                    history_rows.extend(item["history"])
                elif isinstance(item, dict):
                    history_rows.append(item)

        valid_rows = [r for r in history_rows if r.get("t") is not None]
        row_count = len(valid_rows)

        span_bars = 0
        if row_count > 0:
            timestamps_ms = [int(r["t"]) * 1000 for r in valid_rows]
            min_ms = min(timestamps_ms)
            max_ms = max(timestamps_ms)
            min_bar_start_ms[symbol] = min_ms
            max_bar_start_ms[symbol] = max_ms
            span_days = (max_ms - min_ms) / 1000 / 86400
            span_days_per_symbol[symbol] = round(span_days, 2)
            span_bars = int((max_ms - min_ms) // 1000 // 300 + 1)
        else:
            min_bar_start_ms[symbol] = None
            max_bar_start_ms[symbol] = None
            span_days_per_symbol[symbol] = 0.0

        # Usable bars count for checking feasibility is the timeline span we can reconstruct (via padding),
        # or the raw row count, whichever is larger.
        rows_per_symbol[symbol] = max(row_count, span_bars)

    # Determine final API status to feed into decision maker
    if not api_key:
        final_api_status = "no_api_key"
    elif any(s == "api_auth_failed" for s in api_statuses):
        final_api_status = "api_auth_failed"
    elif any(s == "api_rate_limited" for s in api_statuses):
        final_api_status = "api_rate_limited"
    elif any(s == "api_ok_non_empty_rows" for s in api_statuses):
        final_api_status = "api_ok_non_empty_rows"
    else:
        final_api_status = "api_ok_empty_rows"

    decision = determine_decision(
        rows_per_symbol=rows_per_symbol,
        requested_symbols=symbols,
        api_status=final_api_status,
    )

    # Check if supports 7d lookback (meaning all symbols have >= 2304 bars)
    required_bars = 2016 + 288
    supports_7d_lookback = (
        all(count >= required_bars for count in rows_per_symbol.values())
        if rows_per_symbol
        else False
    )

    return {
        "vendor": "coinalyze",
        "interval": "5min",
        "symbols_requested": symbols,
        "rows_per_symbol": rows_per_symbol,
        "min_bar_start_ms": min_bar_start_ms,
        "max_bar_start_ms": max_bar_start_ms,
        "span_days_per_symbol": span_days_per_symbol,
        "supports_7d_lookback": supports_7d_lookback,
        "decision": decision,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Probe 5m Route B feasibility from Coinalyze.")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"],
        help="Symbols to probe",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=8,
        help="Lookback window in days (default: 8)",
    )
    parser.add_argument(
        "--output",
        default="reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_feasibility.json",
        help="Output path for feasibility JSON report",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    report = probe_feasibility(
        symbols=args.symbols,
        lookback_days=args.lookback_days,
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Saved feasibility report to {args.output}")
    print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
