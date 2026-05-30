from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.research.liquidation_shock_event_study.shock_detection import (
    detect_shocks,
    deduplicate_events,
)

logger = logging.getLogger(__name__)


def build_aligned_1m_dataset(
    price_rows: list[dict[str, Any]],
    liq_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # Mapping of (symbol, bar_start_ms) -> liq_row
    liq_map = {}
    for r in liq_rows:
        key = (r["symbol"], r["bar_start_ms"])
        liq_map[key] = r

    joined = []
    missing_liq_count = 0

    for pr in price_rows:
        sym = pr["symbol"]
        ts = pr["timestamp_ms"]
        key = (sym, ts)

        # Build joined row
        row = {
            "symbol": sym,
            "bar_start_ms": ts,
            "open_price": float(pr.get("open") or pr.get("open_price") or 0.0),
            "high_price": float(pr.get("high") or pr.get("high_price") or 0.0),
            "low_price": float(pr.get("low") or pr.get("low_price") or 0.0),
            "close_price": float(pr.get("close") or pr.get("close_price") or 0.0),
        }

        if key in liq_map:
            lr = liq_map[key]
            row["long_liquidation_notional_1m_usdt"] = float(
                lr.get("long_liquidation_notional_1m_usdt") or 0.0
            )
            row["short_liquidation_notional_1m_usdt"] = float(
                lr.get("short_liquidation_notional_1m_usdt") or 0.0
            )
            row["total_liquidation_notional_1m_usdt"] = float(
                lr.get("total_liquidation_notional_1m_usdt") or 0.0
            )
        else:
            row["long_liquidation_notional_1m_usdt"] = 0.0
            row["short_liquidation_notional_1m_usdt"] = 0.0
            row["total_liquidation_notional_1m_usdt"] = 0.0
            missing_liq_count += 1

        joined.append(row)

    audit = {
        "price_rows": len(price_rows),
        "liquidation_rows": len(liq_rows),
        "joined_rows": len(joined),
        "missing_price_bar_count": 0,
        "missing_liquidation_bar_count": missing_liq_count,
    }

    return joined, audit


def fetch_binance_1m_klines(
    symbol: str, start_time_ms: int, end_time_ms: int
) -> list[dict[str, Any]]:
    binance_symbol = symbol.replace("/", "")
    base_url = "https://fapi.binance.com/fapi/v1/klines"

    klines_collected = []
    current_start = start_time_ms

    logger.info(f"Fetching Binance 1m klines for {symbol} from {start_time_ms} to {end_time_ms}...")

    # Fetch in chunks of 1500
    while current_start < end_time_ms:
        params = {
            "symbol": binance_symbol,
            "interval": "1m",
            "startTime": str(current_start),
            "endTime": str(end_time_ms),
            "limit": "1500",
        }
        url = f"{base_url}?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": "crypto-alpha-lab/dataset-builder"})
        try:
            with urlopen(req, timeout=15.0) as response:
                data = json.loads(response.read().decode("utf-8"))
                if not data:
                    break
                for k in data:
                    klines_collected.append(
                        {
                            "symbol": symbol,
                            "timestamp_ms": int(k[0]),
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                        }
                    )
                # Next chunk starts after the last kline open time
                last_open = int(data[-1][0])
                if last_open <= current_start:
                    break
                current_start = last_open + 60_000  # advance by 1m
                time.sleep(0.3)
        except Exception as e:
            logger.error(f"Error fetching klines from Binance: {e}")
            break

    # Deduplicate and sort by timestamp
    seen = set()
    unique_klines = []
    for k in klines_collected:
        if k["timestamp_ms"] not in seen:
            seen.add(k["timestamp_ms"])
            unique_klines.append(k)

    unique_klines.sort(key=lambda x: x["timestamp_ms"])
    return unique_klines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build liquidation shock 1m dataset by joining price and liquidations."
    )
    parser.add_argument(
        "--liquidation-jsonl",
        default="reports/liquidation_shock_event_study/liquidation_shock_1m_raw.jsonl",
        help="Path to 1m normalized liquidation JSONL",
    )
    parser.add_argument(
        "--price-jsonl",
        help="Optional path to pre-fetched 1m price JSONL. If not provided, will fetch from Binance.",
    )
    parser.add_argument(
        "--output-jsonl",
        default="reports/liquidation_shock_event_study/liquidation_shock_1m_dataset.jsonl",
        help="Output path for the combined dataset JSONL",
    )
    parser.add_argument(
        "--events-output-jsonl",
        default="reports/liquidation_shock_event_study/liquidation_shock_1m_events.jsonl",
        help="Output path for the detected events JSONL",
    )
    parser.add_argument(
        "--summary-output",
        default="reports/liquidation_shock_event_study/liquidation_shock_1m_dataset_summary.json",
        help="Output path for the join summary JSON",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    # 1. Read liquidation rows
    liq_rows = []
    if os.path.exists(args.liquidation_jsonl):
        with open(args.liquidation_jsonl, "r") as f:
            for line in f:
                if line.strip():
                    liq_rows.append(json.loads(line))
        logger.info(f"Loaded {len(liq_rows)} liquidation rows from {args.liquidation_jsonl}")
    else:
        logger.warning(f"Liquidation file {args.liquidation_jsonl} does not exist.")

    # 2. Get price rows
    price_rows = []
    if args.price_jsonl and os.path.exists(args.price_jsonl):
        with open(args.price_jsonl, "r") as f:
            for line in f:
                if line.strip():
                    price_rows.append(json.loads(line))
        logger.info(f"Loaded {len(price_rows)} price rows from {args.price_jsonl}")
    else:
        # Fetch from Binance based on time range of liquidation rows
        if not liq_rows:
            logger.error("No liquidation rows available to determine time range for price fetch.")
            return 1

        # Group by symbol and find min/max timestamps
        symbols = set(r["symbol"] for r in liq_rows)
        for symbol in symbols:
            sym_liq = [r for r in liq_rows if r["symbol"] == symbol]
            min_ts = min(r["bar_start_ms"] for r in sym_liq)
            max_ts = max(r["bar_start_ms"] for r in sym_liq)

            # Pad slightly to ensure full coverage (trailing window requires 24h, forward evaluations need ~2h)
            start_fetch = min_ts - 3600_000 * 25  # 25h safety padding before
            end_fetch = max_ts + 3600_000 * 2     # 2h safety padding after

            klines = fetch_binance_1m_klines(symbol, start_fetch, end_fetch)
            price_rows.extend(klines)

    # 3. Align datasets
    joined, audit = build_aligned_1m_dataset(price_rows, liq_rows)

    # 4. Detect and deduplicate shock events
    raw_events = detect_shocks(joined)
    deduped_events = deduplicate_events(raw_events)

    audit["raw_events_detected"] = len(raw_events)
    audit["deduplicated_events"] = len(deduped_events)

    # Group event counts by symbol
    events_per_symbol = {}
    for ev in deduped_events:
        events_per_symbol[ev.symbol] = events_per_symbol.get(ev.symbol, 0) + 1
    audit["events_per_symbol"] = events_per_symbol

    # 5. Save results
    os.makedirs(os.path.dirname(os.path.abspath(args.output_jsonl)), exist_ok=True)
    sorted_joined = sorted(joined, key=lambda x: (x["symbol"], x["bar_start_ms"]))
    with open(args.output_jsonl, "w") as f:
        for row in sorted_joined:
            f.write(json.dumps(row) + "\n")
    logger.info(f"Saved {len(sorted_joined)} aligned rows to {args.output_jsonl}")

    os.makedirs(os.path.dirname(os.path.abspath(args.events_output_jsonl)), exist_ok=True)
    with open(args.events_output_jsonl, "w") as f:
        for ev in deduped_events:
            ev_dict = {
                "symbol": ev.symbol,
                "shock_bar_start_ms": ev.shock_bar_start_ms,
                "liquidated_position_side": ev.liquidated_position_side,
                "dominant_liquidation_side": ev.dominant_liquidation_side,
                "shock_notional_usdt": ev.shock_notional_usdt,
                "relative_score": ev.relative_score,
                "relative_score_method": ev.relative_score_method,
                "reference_count": ev.reference_count,
                "required_reference_count": ev.required_reference_count,
                "dominance_ratio": ev.dominance_ratio,
                "dedup_bucket_start_ms": ev.dedup_bucket_start_ms,
                "source_namespace": ev.source_namespace,
                "expected_price_direction": ev.expected_price_direction,
            }
            f.write(json.dumps(ev_dict) + "\n")
    logger.info(f"Saved {len(deduped_events)} deduplicated shock events to {args.events_output_jsonl}")

    os.makedirs(os.path.dirname(os.path.abspath(args.summary_output)), exist_ok=True)
    with open(args.summary_output, "w") as f:
        json.dump(audit, f, indent=2)
    logger.info(f"Saved dataset join summary to {args.summary_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
