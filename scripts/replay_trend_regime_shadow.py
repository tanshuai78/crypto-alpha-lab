from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

from configs.base import (
    TREND_REGIME_MAX_DATA_AGE_SEC,
    TREND_REGIME_MAX_HOLDING_HOURS,
    TREND_REGIME_OBSERVATION_COST_BPS,
    TREND_REGIME_STOP_LOSS_PCT,
    TREND_REGIME_STRESS_COST_BPS,
    TREND_REGIME_WATCH_SYMBOLS,
)
from src.strategies.trend_regime.scanner import classify_trend_regime_snapshot
from src.strategies.trend_regime.shadow_simulator import (
    TrendRegimeShadowPosition,
    simulate_trend_regime_shadow,
)


def normalize_rows_for_historical_replay(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    normalized: list[dict[str, Any]] = []
    rows_originally_api_stale_count = 0

    for row in rows:
        patched = dict(row)
        value = _number_or_none(row.get("data_age_sec"))
        if value is None or value > float(TREND_REGIME_MAX_DATA_AGE_SEC):
            rows_originally_api_stale_count += 1
        patched["data_age_sec"] = 0.0
        normalized.append(patched)

    return normalized, rows_originally_api_stale_count


def build_classification_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reject_counts: dict[str, int] = defaultdict(int)
    reject_counts_by_symbol: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    entry_event_count = 0
    entry_event_count_by_symbol: dict[str, int] = defaultdict(int)
    entry_event_count_by_regime: dict[str, int] = defaultdict(int)
    rows_missing_liquidation_notional_count = 0
    rows_with_liquidation_notional_count = 0
    symbols: set[str] = set()
    timestamp_values: list[int] = []

    for row in rows:
        symbol = str(row.get("symbol") or "")
        if symbol:
            symbols.add(symbol)

        ts_ms = int(_number_or_none(row.get("timestamp_ms")) or 0)
        if ts_ms > 0:
            timestamp_values.append(ts_ms)

        liquidation_notional = _number_or_none(row.get("liquidation_notional_1h_usdt"))
        if liquidation_notional is None:
            rows_missing_liquidation_notional_count += 1
        else:
            rows_with_liquidation_notional_count += 1

        classification = classify_trend_regime_snapshot(row)
        if classification.event is None:
            reject_reason = str(classification.reject_reason or "unknown")
            reject_counts[reject_reason] += 1
            reject_counts_by_symbol[symbol or "unknown"][reject_reason] += 1
            continue
        entry_event_count += 1
        entry_event_count_by_symbol[symbol or "unknown"] += 1
        entry_event_count_by_regime[str(classification.event.regime)] += 1

    start_timestamp_ms = min(timestamp_values) if timestamp_values else 0
    end_timestamp_ms = max(timestamp_values) if timestamp_values else 0
    time_span_hours = (
        (end_timestamp_ms - start_timestamp_ms) / 3_600_000.0
        if end_timestamp_ms > start_timestamp_ms
        else 0.0
    )

    return {
        "input_row_count": len(rows),
        "symbol_count": len(symbols),
        "symbols": sorted(symbols),
        "start_timestamp_ms": start_timestamp_ms,
        "end_timestamp_ms": end_timestamp_ms,
        "time_span_hours": round(time_span_hours, 10),
        "entry_event_count": entry_event_count,
        "entry_event_count_by_symbol": dict(entry_event_count_by_symbol),
        "entry_event_count_by_regime": dict(entry_event_count_by_regime),
        "classification_reject_counts": dict(reject_counts),
        "reject_counts_by_symbol": {
            key: dict(value) for key, value in reject_counts_by_symbol.items()
        },
        "rows_missing_liquidation_notional_count": rows_missing_liquidation_notional_count,
        "rows_with_liquidation_notional_count": rows_with_liquidation_notional_count,
        "liquidation_coverage_ratio": round(rows_with_liquidation_notional_count / len(rows), 10)
        if rows
        else 0.0,
    }


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _summarize_pnl(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "trade_count": 0,
            "mean_net_pnl_bps": 0.0,
            "median_net_pnl_bps": 0.0,
            "win_rate": 0.0,
            "worst_trade_net_pnl_bps": 0.0,
        }

    net_values = [float(item["net_pnl_bps"]) for item in results]
    wins = [value for value in net_values if value > 0.0]
    return {
        "trade_count": len(results),
        "mean_net_pnl_bps": round(mean(net_values), 10),
        "median_net_pnl_bps": round(median(net_values), 10),
        "win_rate": round(len(wins) / len(results), 10),
        "worst_trade_net_pnl_bps": round(min(net_values), 10),
    }


def _grouped_summary(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        key = f"{item['regime']}|{item['direction']}|{item['symbol_tier']}"
        buckets[key].append(item)

    grouped: dict[str, dict[str, Any]] = {}
    for key, members in buckets.items():
        grouped[key] = _summarize_pnl(members)
    return grouped


def _universe_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    watch = set(TREND_REGIME_WATCH_SYMBOLS)
    missing_symbol_count = 0
    non_watchlist_count = 0
    non_watchlist_symbols: set[str] = set()

    for row in rows:
        symbol = str(row.get("symbol") or "")
        if not symbol:
            missing_symbol_count += 1
        elif symbol not in watch:
            non_watchlist_count += 1
            non_watchlist_symbols.add(symbol)

    return {
        "missing_symbol_row_count": missing_symbol_count,
        "non_watchlist_row_count": non_watchlist_count,
        "non_watchlist_symbols": sorted(non_watchlist_symbols),
    }


def build_shadow_summary(
    rows: list[dict[str, Any]], *, estimated_cost_bps: float
) -> dict[str, Any]:
    normalized_rows, rows_originally_api_stale_count = normalize_rows_for_historical_replay(rows)
    audit = build_classification_audit(normalized_rows)

    results: list[dict[str, Any]] = []
    entry_event_count = 0
    insufficient_path_count = 0
    missing_entry_price_count = 0

    for index, row in enumerate(normalized_rows):
        classification = classify_trend_regime_snapshot(row)
        if classification.event is None:
            continue

        event = classification.event
        entry_event_count += 1

        entry_price = _number_or_none(row.get("close_price"))
        entry_time_ms = int(_number_or_none(row.get("timestamp_ms")) or 0)
        if entry_price is None or entry_time_ms <= 0:
            missing_entry_price_count += 1
            continue

        path_rows = [
            item
            for item in normalized_rows[index + 1 :]
            if item.get("symbol") == event.symbol
            and int(_number_or_none(item.get("timestamp_ms")) or 0) > entry_time_ms
        ]

        if not path_rows:
            insufficient_path_count += 1
            continue

        position = TrendRegimeShadowPosition(
            symbol=event.symbol,
            direction=event.direction,
            entry_time_ms=entry_time_ms,
            entry_price=entry_price,
            estimated_cost_bps=estimated_cost_bps,
            max_holding_hours=float(TREND_REGIME_MAX_HOLDING_HOURS),
            stop_loss_pct=float(TREND_REGIME_STOP_LOSS_PCT),
            regime=event.regime,
            symbol_tier=str(event.metadata.get("symbol_tier") or "unknown"),
        )
        simulated = simulate_trend_regime_shadow(position, path_rows)
        results.append(
            {
                "symbol": simulated.symbol,
                "regime": simulated.regime,
                "direction": simulated.direction,
                "symbol_tier": simulated.symbol_tier,
                "entry_time_ms": simulated.entry_time_ms,
                "exit_time_ms": simulated.exit_time_ms,
                "entry_price": simulated.entry_price,
                "exit_price": simulated.exit_price,
                "exit_reason": simulated.exit_reason,
                "gross_pnl_pct": simulated.gross_pnl_pct,
                "net_pnl_bps": simulated.net_pnl_bps,
            }
        )

    summary = {
        "input_row_count": audit["input_row_count"],
        "symbol_count": audit["symbol_count"],
        "symbols": audit["symbols"],
        "start_timestamp_ms": audit["start_timestamp_ms"],
        "end_timestamp_ms": audit["end_timestamp_ms"],
        "time_span_hours": audit["time_span_hours"],
        "entry_event_count": entry_event_count,
        "entry_event_count_by_symbol": audit["entry_event_count_by_symbol"],
        "entry_event_count_by_regime": audit["entry_event_count_by_regime"],
        "shadow_trade_count": len(results),
        "insufficient_path_count": insufficient_path_count,
        "missing_entry_price_count": missing_entry_price_count,
        "estimated_cost_bps": estimated_cost_bps,
        "historical_mode": True,
        "historical_freshness_normalized_count": len(normalized_rows),
        "rows_originally_api_stale_count": rows_originally_api_stale_count,
        "classification_reject_counts": audit["classification_reject_counts"],
        "reject_counts_by_symbol": audit["reject_counts_by_symbol"],
        "rows_missing_liquidation_notional_count": audit["rows_missing_liquidation_notional_count"],
        "rows_with_liquidation_notional_count": audit["rows_with_liquidation_notional_count"],
        "liquidation_coverage_ratio": audit["liquidation_coverage_ratio"],
        "coverage_quality": "historical_rows_replay_not_live_freshness_aware",
        "depth_aware": False,
        "results": results,
        "grouped_summary": _grouped_summary(results),
    }
    summary.update(_summarize_pnl(results))
    summary.update(_universe_summary(rows))
    return summary


def build_dual_cost_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    base = build_shadow_summary(rows, estimated_cost_bps=float(TREND_REGIME_OBSERVATION_COST_BPS))
    stress = build_shadow_summary(rows, estimated_cost_bps=float(TREND_REGIME_STRESS_COST_BPS))
    return {
        "base_cost_bps": float(TREND_REGIME_OBSERVATION_COST_BPS),
        "stress_cost_bps": float(TREND_REGIME_STRESS_COST_BPS),
        "base": base,
        "stress": stress,
    }


def load_rows_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_optional_jsonl(path: str) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    records: list[dict[str, Any]] = []
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


def apply_hourly_liquidation_history(
    rows: list[dict[str, Any]],
    hourly_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lookup: dict[tuple[str, int], dict[str, Any]] = {}
    bucket_values: list[int] = []
    for rec in hourly_records:
        symbol = str(rec.get("symbol") or "")
        bucket = int(_number_or_none(rec.get("hour_bucket_ms")) or 0)
        notional = _number_or_none(rec.get("liquidation_notional_1h_usdt"))
        if symbol and bucket > 0 and notional is not None:
            lookup[(symbol, bucket)] = rec
            bucket_values.append(bucket)

    joined_count = 0
    patched: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        symbol = str(r.get("symbol") or "")
        ts_ms = int(_number_or_none(r.get("timestamp_ms")) or 0)
        bucket = ts_ms // 3_600_000 * 3_600_000 if ts_ms > 0 else 0
        matched = lookup.get((symbol, bucket))
        existing = _number_or_none(r.get("liquidation_notional_1h_usdt"))

        if existing is None and matched is not None:
            r["liquidation_notional_1h_usdt"] = _number_or_none(
                matched.get("liquidation_notional_1h_usdt")
            )
            r["long_liquidation_notional_1h_usdt"] = _number_or_none(
                matched.get("long_liquidation_notional_1h_usdt")
            )
            r["short_liquidation_notional_1h_usdt"] = _number_or_none(
                matched.get("short_liquidation_notional_1h_usdt")
            )
            r["liquidation_source"] = str(
                matched.get("liquidation_source") or "binance_forceorder_ws"
            )
            r["liquidation_source_quality"] = str(
                matched.get("source_quality") or "self_collected_partial_history"
            )
            r["liquidation_notional_semantics"] = str(
                matched.get("liquidation_notional_semantics") or "partial_snapshot_lower_bound"
            )
            r["liquidation_bucket_semantics"] = str(
                matched.get("liquidation_bucket_semantics")
                or "utc_hour_floor_of_row_timestamp"
            )
            joined_count += 1
        patched.append(r)

    start_ms = min(bucket_values) if bucket_values else 0
    end_ms = max(bucket_values) if bucket_values else 0
    duration_hours = (end_ms - start_ms) / 3_600_000.0 if end_ms > start_ms else 0.0
    join_summary = {
        "liquidation_history_input_count": len(hourly_records),
        "liquidation_rows_joined_count": joined_count,
        "liquidation_history_source": "binance_forceorder_ws" if hourly_records else "none",
        "liquidation_history_source_quality": (
            "self_collected_partial_history" if hourly_records else "missing"
        ),
        "liquidation_notional_semantics": (
            "partial_snapshot_lower_bound" if hourly_records else "missing"
        ),
        "liquidation_bucket_semantics": "utc_hour_floor_of_row_timestamp",
        "liquidation_raw_start_ms": start_ms,
        "liquidation_raw_end_ms": end_ms,
        "liquidation_raw_duration_hours": round(duration_hours, 10),
    }
    return patched, join_summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay trend-regime shadow from raw rows")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--liquidation-hourly-jsonl",
        default=None,
        help="Optional path to hourly liquidation proxy JSONL for backfilling liquidation_notional_1h_usdt.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = load_rows_jsonl(args.input)
    join_summary = {
        "liquidation_history_input_count": 0,
        "liquidation_rows_joined_count": 0,
        "liquidation_history_source": "none",
        "liquidation_history_source_quality": "missing",
        "liquidation_notional_semantics": "missing",
        "liquidation_bucket_semantics": "utc_hour_floor_of_row_timestamp",
        "liquidation_raw_start_ms": 0,
        "liquidation_raw_end_ms": 0,
        "liquidation_raw_duration_hours": 0.0,
    }
    if args.liquidation_hourly_jsonl:
        hourly = load_optional_jsonl(args.liquidation_hourly_jsonl)
        rows, join_summary = apply_hourly_liquidation_history(rows, hourly)
    summary = build_dual_cost_summary(rows)
    summary["liquidation_history_join_summary"] = join_summary
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
