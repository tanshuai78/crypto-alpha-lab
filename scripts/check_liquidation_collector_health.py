#!/usr/bin/env python
"""Inspect liquidation collector archive integrity and research readiness."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from configs.base import TREND_REGIME_WATCH_SYMBOLS


def inspect_liquidation_collector_health(
    data_dir: Path | str,
    now_ms: int | None = None,
    expected_symbols: list[str] | None = None,
) -> dict[str, Any]:
    if now_ms is None:
        now_ms = int(time.time() * 1000)

    dir_path = Path(data_dir)
    raw_path = dir_path / "trend_regime_force_orders_raw.jsonl"
    agg_1m_path = dir_path / "trend_regime_liquidation_1m.jsonl"
    agg_5m_path = dir_path / "trend_regime_liquidation_5m.jsonl"
    agg_1h_path = dir_path / "trend_regime_liquidation_hourly.jsonl"

    summary: dict[str, Any] = {
        "raw_exists": False,
        "raw_row_count": 0,
        "raw_latest_timestamp_ms": None,
        "raw_invalid_json_line_count": 0,
        "raw_last_line_valid": False,
        "raw_duplicate_event_count": 0,
        "raw_time_span_hours": 0.0,
        "raw_recent_event_count_1h": 0,
        "raw_recent_event_count_24h": 0,
        "aggregate_1m_exists": False,
        "aggregate_1m_row_count": 0,
        "aggregate_1m_latest_bucket_ms": None,
        "aggregate_1m_coverage_ratio_24h": 0.0,
        "aggregate_1m_missing_bucket_count_24h": 1440,
        "aggregate_1m_max_gap_minutes_24h": 1440,
        "aggregate_1m_symbol_stats_24h": {},
        "aggregate_5m_exists": False,
        "aggregate_5m_row_count": 0,
        "aggregate_5m_latest_bucket_ms": None,
        "aggregate_1h_exists": False,
        "aggregate_1h_row_count": 0,
        "aggregate_1h_latest_bucket_ms": None,
        "research_ready_1m_24h": False,
    }

    # 1. Inspect Raw Archive
    raw_exists = raw_path.exists()
    summary["raw_exists"] = raw_exists

    raw_event_times: list[int] = []
    raw_recent_symbols: set[str] = set()
    seen_event_ids: set[str] = set()
    raw_duplicate_count = 0
    raw_row_count = 0
    invalid_line_count = 0
    last_line_valid = False

    if raw_exists:
        with open(raw_path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                raw_row_count += 1
                try:
                    record = json.loads(stripped)
                    last_line_valid = True

                    # Extract event_id for duplication check
                    event_id = record.get("event_id")
                    if event_id:
                        if event_id in seen_event_ids:
                            raw_duplicate_count += 1
                        else:
                            seen_event_ids.add(event_id)

                    # Extract timestamp for coverage checks
                    # Try keys in canonical order
                    event_time = None
                    for key in ("event_time_ms", "trade_time_ms", "timestamp_ms", "E", "T"):
                        val = record.get(key)
                        if val is not None:
                            try:
                                event_time = int(float(val))
                                break
                            except (ValueError, TypeError):
                                pass

                    if event_time and event_time > 0:
                        raw_event_times.append(event_time)
                        if event_time >= now_ms - 86_400_000:
                            symbol = record.get("symbol")
                            if isinstance(symbol, str) and symbol:
                                raw_recent_symbols.add(symbol)
                except json.JSONDecodeError:
                    invalid_line_count += 1
                    last_line_valid = False

        summary["raw_row_count"] = raw_row_count
        summary["raw_invalid_json_line_count"] = invalid_line_count
        summary["raw_last_line_valid"] = last_line_valid if raw_row_count > 0 else False
        summary["raw_duplicate_event_count"] = raw_duplicate_count

        if raw_event_times:
            min_ts = min(raw_event_times)
            max_ts = max(raw_event_times)
            summary["raw_latest_timestamp_ms"] = max_ts
            summary["raw_time_span_hours"] = round((max_ts - min_ts) / 3_600_000, 2)

            summary["raw_recent_event_count_1h"] = sum(
                1 for ts in raw_event_times if ts >= now_ms - 3_600_000
            )
            summary["raw_recent_event_count_24h"] = sum(
                1 for ts in raw_event_times if ts >= now_ms - 86_400_000
            )

    # 2. Inspect Aggregated Files Existence
    agg_1m_exists = agg_1m_path.exists()
    summary["aggregate_1m_exists"] = agg_1m_exists
    summary["aggregate_5m_exists"] = agg_5m_path.exists()
    summary["aggregate_1h_exists"] = agg_1h_path.exists()

    # 3. Analyze 1m Aggregation Gaps & Coverage
    if agg_1m_exists:
        agg_1m_rows = []
        with open(agg_1m_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    agg_1m_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        summary["aggregate_1m_row_count"] = len(agg_1m_rows)
        if agg_1m_rows:
            summary["aggregate_1m_latest_bucket_ms"] = max(
                int(row["bar_start_ms"]) for row in agg_1m_rows if "bar_start_ms" in row
            )

        # 24h trailing coverage grid
        start_24h_ago = now_ms - 24 * 3600 * 1000
        grid_start = (start_24h_ago // 60000) * 60000
        expected_buckets = [grid_start + m * 60000 for m in range(1440)]
        expected_set = set(expected_buckets)

        rows_by_symbol: dict[str, set[int]] = {}
        agg_1m_symbols: set[str] = set()
        for row in agg_1m_rows:
            symbol = row.get("symbol")
            if not isinstance(symbol, str) or "bar_start_ms" not in row:
                continue
            agg_1m_symbols.add(symbol)
            bar_start_ms = int(row["bar_start_ms"])
            if bar_start_ms in expected_set:
                rows_by_symbol.setdefault(symbol, set()).add(bar_start_ms)

        symbol_scope = expected_symbols or sorted(raw_recent_symbols | agg_1m_symbols)
        symbol_stats: dict[str, dict[str, Any]] = {}

        for symbol in symbol_scope:
            present_set = rows_by_symbol.get(symbol, set())
            missing_count = 1440 - len(present_set)
            coverage_ratio = len(present_set) / 1440

            if len(present_set) == 1440:
                max_gap_minutes = 1
            elif len(present_set) == 0:
                max_gap_minutes = 1440
            else:
                sorted_present = sorted(present_set)
                max_gap_ms = 0
                for i in range(len(sorted_present) - 1):
                    gap = sorted_present[i + 1] - sorted_present[i]
                    if gap > max_gap_ms:
                        max_gap_ms = gap
                max_gap_minutes = int(max_gap_ms // 60000)

            symbol_stats[symbol] = {
                "coverage_ratio": coverage_ratio,
                "missing_bucket_count": missing_count,
                "max_gap_minutes": max_gap_minutes,
            }

        if symbol_stats:
            summary["aggregate_1m_symbol_stats_24h"] = symbol_stats
            summary["aggregate_1m_coverage_ratio_24h"] = min(
                stat["coverage_ratio"] for stat in symbol_stats.values()
            )
            summary["aggregate_1m_missing_bucket_count_24h"] = max(
                stat["missing_bucket_count"] for stat in symbol_stats.values()
            )
            summary["aggregate_1m_max_gap_minutes_24h"] = max(
                stat["max_gap_minutes"] for stat in symbol_stats.values()
            )

    if summary["aggregate_5m_exists"]:
        agg_5m_rows = []
        with open(agg_5m_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    agg_5m_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        summary["aggregate_5m_row_count"] = len(agg_5m_rows)
        if agg_5m_rows:
            summary["aggregate_5m_latest_bucket_ms"] = max(
                int(row["bar_start_ms"]) for row in agg_5m_rows if "bar_start_ms" in row
            )

    if summary["aggregate_1h_exists"]:
        agg_1h_rows = []
        with open(agg_1h_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    agg_1h_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        summary["aggregate_1h_row_count"] = len(agg_1h_rows)
        if agg_1h_rows:
            summary["aggregate_1h_latest_bucket_ms"] = max(
                int(row["hour_bucket_ms"]) for row in agg_1h_rows if "hour_bucket_ms" in row
            )

    # 4. Assess Research Readiness Gate
    # Readiness criteria: raw exists, 1m agg exists, raw timespan >= 24h,
    # 1m coverage >= 99%, and no symbol shows a 1m gap wider than one minute.
    is_ready = (
        summary["raw_exists"]
        and summary["aggregate_1m_exists"]
        and summary["raw_time_span_hours"] >= 24.0
        and summary["aggregate_1m_coverage_ratio_24h"] >= 0.99
        and summary["aggregate_1m_max_gap_minutes_24h"] <= 1
    )
    summary["research_ready_1m_24h"] = is_ready

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Check health of liquidation collector archive.")
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Path to data directory containing raw and aggregate files.",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=list(TREND_REGIME_WATCH_SYMBOLS),
        help="Expected symbols that must satisfy 1m archive readiness.",
    )
    args = parser.parse_args()

    summary = inspect_liquidation_collector_health(args.data_dir, expected_symbols=args.symbols)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
