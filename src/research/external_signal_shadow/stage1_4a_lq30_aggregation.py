from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def aggregate_forceorder_windows(
    rows: list[dict[str, Any]], *, bucket_ms: int, configured_lag_ms: int
) -> list[dict[str, Any]]:
    buckets = {}
    for row in rows:
        bucket_start_ms = (int(row["timestamp_ms"]) // bucket_ms) * bucket_ms
        key = (row["symbol"], bucket_start_ms)
        if key not in buckets:
            buckets[key] = {
                "symbol": row["symbol"],
                "bucket_start_ms": bucket_start_ms,
                "bucket_end_ms": bucket_start_ms + bucket_ms,
                "available_at_ms": bucket_start_ms + bucket_ms + configured_lag_ms,
                "long_liquidation_notional_usd": 0.0,
                "short_liquidation_notional_usd": 0.0,
                "event_count": 0,
            }
        window = buckets[key]
        if row["liquidation_side"] == "long_liquidation":
            window["long_liquidation_notional_usd"] += float(row["notional_usd"])
        elif row["liquidation_side"] == "short_liquidation":
            window["short_liquidation_notional_usd"] += float(row["notional_usd"])
        window["event_count"] += 1

    aggregated = []
    for window in buckets.values():
        total = (
            window["long_liquidation_notional_usd"] +
            window["short_liquidation_notional_usd"]
        )
        day_key = datetime.fromtimestamp(
            window["bucket_start_ms"] / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        window["total_liquidation_notional_usd"] = round(total, 10)
        window["day_key"] = day_key
        aggregated.append(window)
    return sorted(aggregated, key=lambda row: (row["symbol"], row["bucket_start_ms"]))


def compute_concentration_stats(windows: list[dict[str, Any]]) -> dict[str, Any]:
    total_windows = len(windows)
    total_events = sum(int(w["event_count"]) for w in windows)
    total_notional = sum(float(w["total_liquidation_notional_usd"]) for w in windows)

    # 1. Window concentration
    by_day_window = defaultdict(int)
    by_symbol_window = defaultdict(int)
    for window in windows:
        by_day_window[window["day_key"]] += 1
        by_symbol_window[window["symbol"]] += 1

    top_day_windows = sorted(by_day_window.values(), reverse=True)
    top_symbol_windows = sorted(by_symbol_window.values(), reverse=True)

    window_concentration = {
        "top_1_day_window_share": (top_day_windows[0] / total_windows) if total_windows else 0.0,
        "top_3_days_window_share": (sum(top_day_windows[:3]) / total_windows) if total_windows else 0.0,
        "top_1_symbol_window_share": (top_symbol_windows[0] / total_windows) if total_windows else 0.0,
    }

    # 2. Event count concentration
    by_day_event = defaultdict(int)
    by_symbol_event = defaultdict(int)
    for window in windows:
        by_day_event[window["day_key"]] += int(window["event_count"])
        by_symbol_event[window["symbol"]] += int(window["event_count"])

    top_day_events = sorted(by_day_event.values(), reverse=True)
    top_symbol_events = sorted(by_symbol_event.values(), reverse=True)

    event_count_concentration = {
        "top_1_day_event_share": (top_day_events[0] / total_events) if total_events else 0.0,
        "top_3_days_event_share": (sum(top_day_events[:3]) / total_events) if total_events else 0.0,
        "top_1_symbol_event_share": (top_symbol_events[0] / total_events) if total_events else 0.0,
        "top_3_symbols_event_share": (sum(top_symbol_events[:3]) / total_events) if total_events else 0.0,
    }

    # 3. Notional concentration
    by_day_notional = defaultdict(float)
    by_symbol_notional = defaultdict(float)
    for window in windows:
        by_day_notional[window["day_key"]] += float(window["total_liquidation_notional_usd"])
        by_symbol_notional[window["symbol"]] += float(window["total_liquidation_notional_usd"])

    top_day_notional = sorted(by_day_notional.values(), reverse=True)
    top_symbol_notional = sorted(by_symbol_notional.values(), reverse=True)

    notional_concentration = {
        "top_1_day_notional_share": (top_day_notional[0] / total_notional) if total_notional else 0.0,
        "top_3_days_notional_share": (sum(top_day_notional[:3]) / total_notional) if total_notional else 0.0,
        "top_1_symbol_notional_share": (top_symbol_notional[0] / total_notional) if total_notional else 0.0,
    }

    return {
        "window_concentration": window_concentration,
        "event_count_concentration": event_count_concentration,
        "notional_concentration": notional_concentration,
    }


def build_density_report(parsed_rows: list[dict[str, Any]], windows_15m: list[dict[str, Any]]) -> dict[str, Any]:
    if not parsed_rows:
        return {
            "raw_history_days": 0.0,
            "liquidation_history_days": 0.0,
            "symbols_with_events": 0,
            "event_days": 0,
            "max_single_symbol_event_share": 0.0,
            "max_single_day_event_share": 0.0,
            "top_1_day_notional_share": 0.0,
            "top_3_days_notional_share": 0.0,
            "top_1_symbol_notional_share": 0.0,
        }

    timestamps = [int(r["timestamp_ms"]) for r in parsed_rows]
    min_ts, max_ts = min(timestamps), max(timestamps)
    history_days = round((max_ts - min_ts) / (24 * 60 * 60 * 1000), 2)

    unique_symbols = {r["symbol"] for r in parsed_rows}
    unique_days = {w["day_key"] for w in windows_15m}

    concentration = compute_concentration_stats(windows_15m)

    return {
        "raw_history_days": history_days,
        "liquidation_history_days": history_days,
        "symbols_with_events": len(unique_symbols),
        "event_days": len(unique_days),
        "max_single_symbol_event_share": concentration["event_count_concentration"]["top_1_symbol_event_share"],
        "max_single_day_event_share": concentration["event_count_concentration"]["top_1_day_event_share"],
        "top_1_day_notional_share": concentration["notional_concentration"]["top_1_day_notional_share"],
        "top_3_days_notional_share": concentration["notional_concentration"]["top_3_days_notional_share"],
        "top_1_symbol_notional_share": concentration["notional_concentration"]["top_1_symbol_notional_share"],
    }


def build_imbalance_distribution(
    windows_15m: list[dict[str, Any]], windows_1h: list[dict[str, Any]]
) -> dict[str, Any]:
    long_total_15m = sum(float(w["long_liquidation_notional_usd"]) for w in windows_15m)
    short_total_15m = sum(float(w["short_liquidation_notional_usd"]) for w in windows_15m)
    total_15m = long_total_15m + short_total_15m
    long_ratio_15m = (long_total_15m / total_15m) if total_15m else 0.5
    short_ratio_15m = (short_total_15m / total_15m) if total_15m else 0.5

    long_total_1h = sum(float(w["long_liquidation_notional_usd"]) for w in windows_1h)
    short_total_1h = sum(float(w["short_liquidation_notional_usd"]) for w in windows_1h)
    total_1h = long_total_1h + short_total_1h
    long_ratio_1h = (long_total_1h / total_1h) if total_1h else 0.5
    short_ratio_1h = (short_total_1h / total_1h) if total_1h else 0.5

    return {
        "long_short_imbalance_distribution_15m": {
            "long_ratio": round(long_ratio_15m, 4),
            "short_ratio": round(short_ratio_15m, 4),
        },
        "long_short_imbalance_distribution_1h": {
            "long_ratio": round(long_ratio_1h, 4),
            "short_ratio": round(short_ratio_1h, 4),
        },
        "long_liquidation_notional_total": round(long_total_15m, 4),
        "short_liquidation_notional_total": round(short_total_15m, 4),
    }
