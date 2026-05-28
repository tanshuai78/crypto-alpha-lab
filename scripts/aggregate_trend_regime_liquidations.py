"""Aggregate raw forceOrder JSONL events into hourly symbol-level liquidation proxy.

Usage:
    python scripts/aggregate_trend_regime_liquidations.py \\
        --input data/trend_regime_force_orders_raw.jsonl \\
        --output data/trend_regime_liquidation_hourly.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

SEMANTICS_TAG = "forceOrder_aggregated_from_local_ws"


def load_raw_jsonl(path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    p = Path(path)
    if not p.exists():
        return records
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def aggregate_raw_to_hourly(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate raw forceOrder records into one row per (symbol, hour_bucket_utc)."""
    # key: (symbol, hour_bucket_utc)
    buckets: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {"long": 0.0, "short": 0.0}
    )

    for rec in records:
        symbol = str(rec.get("symbol") or "")
        hour_bucket = str(rec.get("hour_bucket_utc") or "")
        if not symbol or not hour_bucket:
            continue
        notional = float(rec.get("notional_usdt") or 0.0)
        liq_side = str(rec.get("liquidation_side") or "unknown")
        key = (symbol, hour_bucket)
        if liq_side == "long":
            buckets[key]["long"] += notional
        elif liq_side == "short":
            buckets[key]["short"] += notional
        # unknown side: skip directional attribution

    rows: list[dict[str, Any]] = []
    for (symbol, hour_bucket), sums in sorted(buckets.items()):
        long_notional = sums["long"]
        short_notional = sums["short"]
        total = long_notional + short_notional
        dominant = "long" if long_notional >= short_notional else "short"
        rows.append(
            {
                "symbol": symbol,
                "hour_bucket_utc": hour_bucket,
                "long_liquidation_notional_usdt": long_notional,
                "short_liquidation_notional_usdt": short_notional,
                "total_liquidation_notional_usdt": total,
                "dominant_side": dominant,
                "semantics": SEMANTICS_TAG,
            }
        )
    return rows


def write_hourly_jsonl(rows: list[dict[str, Any]], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    from configs.base import (
        TREND_REGIME_FORCE_ORDER_RAW_JSONL,
        TREND_REGIME_LIQUIDATION_HOURLY_JSONL,
    )

    parser = argparse.ArgumentParser(description="Aggregate forceOrder events to hourly proxy.")
    parser.add_argument(
        "--input",
        default=f"data/{TREND_REGIME_FORCE_ORDER_RAW_JSONL}",
        help="Path to raw forceOrder JSONL (default: data/<config>)",
    )
    parser.add_argument(
        "--output",
        default=f"data/{TREND_REGIME_LIQUIDATION_HOURLY_JSONL}",
        help="Path to hourly liquidation proxy JSONL (default: data/<config>)",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    records = load_raw_jsonl(args.input)
    if not records:
        print(f"[aggregate] No records found in {args.input}. Writing empty output.")
        write_hourly_jsonl([], args.output)
        return
    rows = aggregate_raw_to_hourly(records)
    write_hourly_jsonl(rows, args.output)
    print(f"[aggregate] {len(records)} raw events → {len(rows)} hourly rows → {args.output}")


if __name__ == "__main__":
    main()
