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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEMANTICS_TAG = "partial_snapshot_lower_bound"


def hour_bucket_ms(timestamp_ms: int) -> int:
    return timestamp_ms // 3_600_000 * 3_600_000


def _hour_bucket_utc_to_ms(value: str) -> int | None:
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return int(dt.timestamp() * 1000)


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
    """Aggregate raw forceOrder records into one row per (symbol, hour_bucket_ms)."""
    # key: (symbol, hour_bucket_ms)
    buckets: dict[tuple[str, int], dict[str, float | int]] = defaultdict(
        lambda: {"long": 0.0, "short": 0.0, "long_count": 0, "short_count": 0}
    )

    for rec in records:
        symbol = str(rec.get("symbol") or "")
        hour_bucket = rec.get("hour_bucket_ms")
        if hour_bucket is None:
            legacy_bucket = str(rec.get("hour_bucket_utc") or "")
            hour_bucket = _hour_bucket_utc_to_ms(legacy_bucket) if legacy_bucket else None
        if not symbol or hour_bucket is None:
            continue
        notional = float(rec.get("notional_usdt") or 0.0)
        liq_side = str(rec.get("liquidation_side") or "unknown")
        key = (symbol, int(hour_bucket))
        if liq_side in ("long", "long_liquidation"):
            buckets[key]["long"] += notional
            buckets[key]["long_count"] += 1
        elif liq_side in ("short", "short_liquidation"):
            buckets[key]["short"] += notional
            buckets[key]["short_count"] += 1
        # unknown side: skip directional attribution

    rows: list[dict[str, Any]] = []
    for (symbol, hour_bucket), sums in sorted(buckets.items()):
        long_notional = float(sums["long"])
        short_notional = float(sums["short"])
        long_count = int(sums["long_count"])
        short_count = int(sums["short_count"])
        total = long_notional + short_notional
        rows.append(
            {
                "symbol": symbol,
                "hour_bucket_ms": hour_bucket,
                "liquidation_notional_1h_usdt": round(total, 10),
                "long_liquidation_notional_1h_usdt": round(long_notional, 10),
                "short_liquidation_notional_1h_usdt": round(short_notional, 10),
                "long_liquidation_event_count": long_count,
                "short_liquidation_event_count": short_count,
                "event_count": long_count + short_count,
                "liquidation_source": "binance_forceorder_ws",
                "source_quality": "self_collected_partial_history",
                "liquidation_notional_semantics": SEMANTICS_TAG,
                "liquidation_bucket_semantics": "utc_hour_floor_of_row_timestamp",
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
