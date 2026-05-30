"""Aggregate raw forceOrder JSONL events into multi-granularity symbol-level liquidation proxies.

Usage:
    python scripts/aggregate_trend_regime_liquidations.py \\
        --input data/trend_regime_force_orders_raw.jsonl \\
        --bucket 1m \\
        --output data/trend_regime_liquidation_1m.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEMANTICS_TAG = "partial_snapshot_lower_bound"


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


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def canonical_liquidation_timestamp_ms(rec: dict[str, Any]) -> int | None:
    for key in ("event_time_ms", "trade_time_ms", "E", "T", "timestamp_ms"):
        value = _int_or_none(rec.get(key))
        if value and value > 0:
            return value
    fallback = _int_or_none(rec.get("hour_bucket_ms"))
    return fallback if fallback and fallback > 0 else None


def aggregate_raw_to_bucket(
    records: list[dict[str, Any]],
    bucket: str = "1h",
    fill_empty_buckets: bool = False,
    start_ms: int | None = None,
    end_ms: int | None = None,
    symbols: list[str] | None = None,
) -> list[dict[str, Any]]:
    rows, _ = aggregate_raw_to_bucket_with_audit(
        records,
        bucket=bucket,
        fill_empty_buckets=fill_empty_buckets,
        start_ms=start_ms,
        end_ms=end_ms,
        symbols=symbols,
    )
    return rows


def aggregate_raw_to_bucket_with_audit(
    records: list[dict[str, Any]],
    bucket: str = "1h",
    fill_empty_buckets: bool = False,
    start_ms: int | None = None,
    end_ms: int | None = None,
    symbols: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if bucket not in ("1m", "5m", "1h"):
        raise ValueError(f"unsupported bucket: {bucket}")

    bucket_size_ms = {
        "1m": 60_000,
        "5m": 300_000,
        "1h": 3_600_000,
    }[bucket]

    audit = {
        "missing_timestamp_count": 0,
        "bucket_event_time_mismatch_count": 0,
        "non_hour_aligned_bucket_count": 0,
        "fallback_to_legacy_hour_bucket_count": 0,
        "duplicate_event_id_count": 0,
    }

    # Deduplicate rows by event_id before aggregating
    seen_event_ids: set[str] = set()
    deduped_records = []

    for rec in records:
        # Resolve event_id
        event_id = rec.get("event_id")
        if not event_id:
            # Reconstruct fallback event_id
            source = rec.get("source") or "binance_forceorder_ws"
            symbol = rec.get("symbol") or ""
            event_ts_ms = canonical_liquidation_timestamp_ms(rec) or 0
            trade_ts_ms = (
                _int_or_none(
                    rec.get("order_trade_time_ms") or rec.get("trade_time_ms") or event_ts_ms
                )
                or 0
            )
            side = rec.get("side") or (
                "SELL" if rec.get("liquidation_side") == "long_liquidation" else "BUY"
            )
            price = float(rec.get("price") or rec.get("average_price") or 0.0)
            quantity = float(rec.get("quantity") or 0.0)
            event_id = f"{source}|{symbol}|{event_ts_ms}|{trade_ts_ms}|{side}|{price}|{quantity}"

        if event_id in seen_event_ids:
            audit["duplicate_event_id_count"] += 1
            continue
        seen_event_ids.add(event_id)
        deduped_records.append(rec)

    # Key: (symbol, bucket_start_ms)
    buckets: dict[tuple[str, int], dict[str, Any]] = defaultdict(
        lambda: {
            "long": 0.0,
            "short": 0.0,
            "long_count": 0,
            "short_count": 0,
            "filled_empty_bucket": False,
        }
    )

    for rec in deduped_records:
        symbol = str(rec.get("symbol") or "")
        if not symbol:
            continue

        event_ts_ms = canonical_liquidation_timestamp_ms(rec)
        if event_ts_ms is None:
            # Fallback to legacy hour bucket check
            raw_provided = rec.get("hour_bucket_ms")
            if raw_provided is not None:
                event_ts_ms = _int_or_none(raw_provided)
            else:
                legacy_bucket = str(rec.get("hour_bucket_utc") or "")
                event_ts_ms = _hour_bucket_utc_to_ms(legacy_bucket) if legacy_bucket else None

            if event_ts_ms is not None:
                audit["fallback_to_legacy_hour_bucket_count"] += 1
            else:
                audit["missing_timestamp_count"] += 1
                continue

        computed_bucket_ms = (event_ts_ms // bucket_size_ms) * bucket_size_ms

        # Audit legacy mismatch checks
        provided_bucket_ms = None
        raw_provided = rec.get("hour_bucket_ms")
        if raw_provided is not None:
            provided_bucket_ms = _int_or_none(raw_provided)
        else:
            legacy_bucket = str(rec.get("hour_bucket_utc") or "")
            provided_bucket_ms = _hour_bucket_utc_to_ms(legacy_bucket) if legacy_bucket else None

        if provided_bucket_ms is not None:
            if provided_bucket_ms % 3_600_000 != 0:
                audit["non_hour_aligned_bucket_count"] += 1
            # Check mismatched bucket floor (hourly floor of provided vs computed hourly floor of event time)
            comp_hour_ms = (event_ts_ms // 3_600_000) * 3_600_000
            prov_hour_ms = (provided_bucket_ms // 3_600_000) * 3_600_000
            if prov_hour_ms != comp_hour_ms:
                audit["bucket_event_time_mismatch_count"] += 1

        notional = float(rec.get("notional_usdt") or 0.0)
        liq_side = str(rec.get("liquidation_side") or "unknown")

        key = (symbol, computed_bucket_ms)
        if liq_side in ("long", "long_liquidation"):
            buckets[key]["long"] += notional
            buckets[key]["long_count"] += 1
        elif liq_side in ("short", "short_liquidation"):
            buckets[key]["short"] += notional
            buckets[key]["short_count"] += 1

    # Zero-fill empty buckets for 1m and 5m when requested
    if (
        fill_empty_buckets
        and bucket in ("1m", "5m")
        and start_ms is not None
        and end_ms is not None
        and symbols
    ):
        grid_start = (start_ms // bucket_size_ms) * bucket_size_ms
        grid_end = (end_ms // bucket_size_ms) * bucket_size_ms
        for sym in symbols:
            current = grid_start
            while current <= grid_end:
                key = (sym, current)
                if key not in buckets:
                    buckets[key] = {
                        "long": 0.0,
                        "short": 0.0,
                        "long_count": 0,
                        "short_count": 0,
                        "filled_empty_bucket": True,
                    }
                current += bucket_size_ms

    rows: list[dict[str, Any]] = []
    for (symbol, computed_bucket), sums in sorted(buckets.items()):
        long_notional = float(sums["long"])
        short_notional = float(sums["short"])
        long_count = int(sums["long_count"])
        short_count = int(sums["short_count"])
        total = long_notional + short_notional
        event_count = long_count + short_count

        if bucket == "1m":
            rows.append(
                {
                    "symbol": symbol,
                    "bar_start_ms": computed_bucket,
                    "long_liquidation_notional_1m_usdt": round(long_notional, 10),
                    "short_liquidation_notional_1m_usdt": round(short_notional, 10),
                    "total_liquidation_notional_1m_usdt": round(total, 10),
                    "event_count_1m": event_count,
                    "source": "binance_forceorder_raw_archive",
                    "filled_empty_bucket": sums.get("filled_empty_bucket", False),
                }
            )
        elif bucket == "5m":
            rows.append(
                {
                    "symbol": symbol,
                    "bar_start_ms": computed_bucket,
                    "long_liquidation_notional_5m_usdt": round(long_notional, 10),
                    "short_liquidation_notional_5m_usdt": round(short_notional, 10),
                    "total_liquidation_notional_5m_usdt": round(total, 10),
                    "event_count_5m": event_count,
                    "source": "binance_forceorder_raw_archive",
                    "filled_empty_bucket": sums.get("filled_empty_bucket", False),
                }
            )
        elif bucket == "1h":
            rows.append(
                {
                    "symbol": symbol,
                    "hour_bucket_ms": computed_bucket,
                    "liquidation_notional_1h_usdt": round(total, 10),
                    "long_liquidation_notional_1h_usdt": round(long_notional, 10),
                    "short_liquidation_notional_1h_usdt": round(short_notional, 10),
                    "long_liquidation_event_count": long_count,
                    "short_liquidation_event_count": short_count,
                    "event_count": event_count,
                    "liquidation_source": "binance_forceorder_ws",
                    "source_quality": "self_collected_partial_history",
                    "liquidation_notional_semantics": SEMANTICS_TAG,
                    "liquidation_bucket_semantics": "utc_hour_floor_of_row_timestamp",
                }
            )

    return rows, audit


def aggregate_raw_to_hourly(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate raw forceOrder records into one row per (symbol, hour_bucket_ms)."""
    return aggregate_raw_to_bucket(records, bucket="1h")


def aggregate_raw_to_hourly_with_audit(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return aggregate_raw_to_bucket_with_audit(records, bucket="1h")


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

    parser = argparse.ArgumentParser(
        description="Aggregate forceOrder events to multi-granularity proxies."
    )
    parser.add_argument(
        "--input",
        default=f"data/{TREND_REGIME_FORCE_ORDER_RAW_JSONL}",
        help="Path to raw forceOrder JSONL (default: data/<config>)",
    )
    parser.add_argument(
        "--output",
        default=f"data/{TREND_REGIME_LIQUIDATION_HOURLY_JSONL}",
        help="Path to aggregated output JSONL (default: hourly liquidation proxy)",
    )
    parser.add_argument(
        "--bucket",
        default="1h",
        choices=["1m", "5m", "1h"],
        help="Aggregation bucket size (default: 1h)",
    )
    parser.add_argument(
        "--fill-empty-buckets",
        action="store_true",
        help="Zero-fill empty buckets for 1m and 5m research data.",
    )
    parser.add_argument(
        "--start-ms",
        type=int,
        help="Start timestamp in milliseconds for zero-filling bounds.",
    )
    parser.add_argument(
        "--end-ms",
        type=int,
        help="End timestamp in milliseconds for zero-filling bounds.",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        help="List of symbols to zero-fill (e.g. BTC/USDT ETH/USDT).",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    records = load_raw_jsonl(args.input)
    fill_empty = args.fill_empty_buckets
    if not records and not fill_empty:
        print(f"[aggregate] No records found in {args.input}. Writing empty output.")
        write_hourly_jsonl([], args.output)
        return
    rows = aggregate_raw_to_bucket(
        records,
        bucket=args.bucket,
        fill_empty_buckets=fill_empty,
        start_ms=args.start_ms,
        end_ms=args.end_ms,
        symbols=args.symbols,
    )
    write_hourly_jsonl(rows, args.output)
    print(f"[aggregate] {len(records)} raw events → {len(rows)} {args.bucket} rows → {args.output}")


if __name__ == "__main__":
    main()
