# -*- coding: utf-8 -*-
"""
scripts/audit_route_c1_data_overlap.py

Route C1 Data Overlap Audit Script.

Audits the time-span overlap between:
  - live liquidation 1m aggregates
  - price 1m data
  - historical orderbook snapshots

and produces a decision on whether data is ready for:
  - price-only C1 research
  - orderbook-aware C1 research

Usage (live_overlap mode):
  PYTHONPATH=src uv run python scripts/audit_route_c1_data_overlap.py \\
    --mode live_overlap \\
    --liquidation-1m data/trend_regime_liquidation_1m.jsonl \\
    --price-1m reports/liquidation_shock_event_study/liquidation_shock_1m_dataset.jsonl \\
    --orderbook-dir /path/to/historical_orderbook \\
    --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \\
    --output reports/route_c1/route_c1_data_overlap_audit_summary.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path


# ─── Pure Functions ───────────────────────────────────────────────────────────


def normalize_symbol(sym: str) -> str:
    """Normalize symbol to no-slash uppercase format.

    Examples:
      BTC/USDT       -> BTCUSDT
      BTCUSDT        -> BTCUSDT
      BTC/USDT:USDT  -> BTCUSDT
      eth/usdt       -> ETHUSDT
    """
    return sym.replace("/", "").replace(":USDT", "").upper()


def compute_time_span(
    rows: list[dict],
    timestamp_key: str,
) -> tuple[int | None, int | None, float]:
    """Return (earliest_ms, latest_ms, span_hours) for a list of rows.

    Returns (None, None, 0.0) when rows is empty.
    span_hours is computed as (latest_ms - earliest_ms) / 3_600_000.
    """
    if not rows:
        return (None, None, 0.0)

    timestamps = [r[timestamp_key] for r in rows if timestamp_key in r]
    if not timestamps:
        return (None, None, 0.0)

    earliest = min(timestamps)
    latest = max(timestamps)
    span_hours = (latest - earliest) / 3_600_000.0
    return (earliest, latest, span_hours)


def compute_overlap_hours_by_symbol(
    liquidation_spans: dict[str, tuple[int, int]],
    price_spans: dict[str, tuple[int, int]],
    orderbook_spans: dict[str, tuple[int, int]],
) -> dict[str, float]:
    """Compute 3-way (liq ∩ price ∩ orderbook) overlap in hours per symbol.

    If orderbook span is absent for a symbol, fall back to 2-way (liq ∩ price).
    Overlap of zero or negative is reported as 0.0.

    Args:
        liquidation_spans: {normalized_symbol: (start_ms, end_ms)}
        price_spans:        {normalized_symbol: (start_ms, end_ms)}
        orderbook_spans:    {normalized_symbol: (start_ms, end_ms)}, may be empty

    Returns:
        {normalized_symbol: overlap_hours}
    """
    result: dict[str, float] = {}
    all_symbols = set(liquidation_spans) | set(price_spans) | set(orderbook_spans)

    for sym in all_symbols:
        if sym not in liquidation_spans or sym not in price_spans:
            result[sym] = 0.0
            continue

        liq_start, liq_end = liquidation_spans[sym]
        prc_start, prc_end = price_spans[sym]

        # two-way intersection
        overlap_start = max(liq_start, prc_start)
        overlap_end = min(liq_end, prc_end)

        if sym in orderbook_spans:
            ob_start, ob_end = orderbook_spans[sym]
            overlap_start = max(overlap_start, ob_start)
            overlap_end = min(overlap_end, ob_end)

        span_ms = overlap_end - overlap_start
        result[sym] = max(0.0, span_ms / 3_600_000.0)

    return result


def compute_coverage_ratio(rows: list[dict], expected_minutes: int) -> float:
    """Return fraction of expected 1-minute bars present.

    Args:
        rows:             list of row dicts (each must have a timestamp field)
        expected_minutes: number of minutes expected in the window

    Returns:
        ratio in [0.0, 1.0]; 0.0 when rows is empty.
    """
    if not rows or expected_minutes <= 0:
        return 0.0
    return min(1.0, len(rows) / expected_minutes)


def compute_overlap_decision(summary: dict) -> dict:
    """Apply decision logic to a partial summary dict and return updated copy.

    Mutates and returns the summary dict with updated fields:
        primary_blocker, ready_for_price_only, ready_for_orderbook_aware, decision.

    Rules:
    - If liquidation_input_exists is False:
        primary_blocker = "missing_liquidation_1m_input"
        decision = "route_c1_overlap_not_ready"
    - ready_for_price_only requires:
        liquidation_input_exists = True
        price_input_exists = True
        price_1m_coverage_24h >= 0.95
        at least one symbol has overlap > 0
    - ready_for_orderbook_aware additionally requires:
        orderbook_dir_exists = True
        orderbook_snapshot_coverage_24h >= 0.80
        at least 2 of BTC/ETH/SOL have overlap > 0
    - decision priority:
        route_c1_overlap_ready_for_orderbook_aware  (highest)
        route_c1_overlap_ready_for_price_only
        route_c1_overlap_not_ready
    """
    updated = dict(summary)

    # Check liquidation blocker
    if not updated.get("liquidation_input_exists", False):
        updated["primary_blocker"] = "missing_liquidation_1m_input"
        updated["ready_for_price_only"] = False
        updated["ready_for_orderbook_aware"] = False
        updated["decision"] = "route_c1_overlap_not_ready"
        return updated

    # Check price-only readiness
    price_ok = (
        updated.get("price_input_exists", False)
        and updated.get("price_1m_coverage_24h", 0.0) >= 0.95
    )
    overlap_by_symbol: dict[str, float] = updated.get("overlap_hours_by_symbol", {})
    any_overlap = any(v > 0.0 for v in overlap_by_symbol.values())

    ready_for_price_only = price_ok and any_overlap
    updated["ready_for_price_only"] = ready_for_price_only

    # Check orderbook-aware readiness
    ready_for_orderbook_aware = False
    if ready_for_price_only and updated.get("orderbook_dir_exists", False):
        ob_coverage_ok = updated.get("orderbook_snapshot_coverage_24h", 0.0) >= 0.80
        if ob_coverage_ok:
            major_symbols_with_overlap = sum(
                1
                for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT")
                if overlap_by_symbol.get(sym, 0.0) > 0.0
            )
            if major_symbols_with_overlap >= 2:
                ready_for_orderbook_aware = True

    updated["ready_for_orderbook_aware"] = ready_for_orderbook_aware

    # Set decision
    if ready_for_orderbook_aware:
        updated["decision"] = "route_c1_overlap_ready_for_orderbook_aware"
    elif ready_for_price_only:
        updated["decision"] = "route_c1_overlap_ready_for_price_only"
    else:
        updated["decision"] = "route_c1_overlap_not_ready"

    return updated


# ─── I/O Helpers ──────────────────────────────────────────────────────────────


def _load_jsonl(path: str) -> list[dict]:
    """Load a JSONL file and return list of parsed dicts. Returns [] on error."""
    rows: list[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except (OSError, IOError):
        return []
    return rows


def _extract_timestamp_ms(row: dict, preferred_key: str) -> int | None:
    value = row.get(preferred_key)
    if value is None:
        value = row.get("bar_start_ms")
    if value is None:
        value = row.get("timestamp_ms")
    if value is None:
        value = row.get("timestamp")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compute_24h_coverage(rows: list[dict], timestamp_key: str = "timestamp_ms") -> float:
    """Return coverage ratio over the latest 24h using unique minute buckets."""
    timestamps = []
    for row in rows:
        ts = _extract_timestamp_ms(row, timestamp_key)
        if ts is not None:
            timestamps.append(ts)
    if not timestamps:
        return 0.0

    latest_ts = max(timestamps)
    window_start = latest_ts - 24 * 60 * 60 * 1000
    unique_minutes = {ts for ts in timestamps if window_start <= ts <= latest_ts}
    return compute_coverage_ratio(
        [{"timestamp_ms": ts} for ts in unique_minutes],
        expected_minutes=1440,
    )


def _build_spans_from_rows(
    rows: list[dict],
    symbol_key: str,
    timestamp_key: str,
) -> dict[str, tuple[int, int]]:
    """Build {normalized_symbol: (min_ts, max_ts)} from a list of rows."""
    by_sym: dict[str, list[int]] = {}
    for row in rows:
        raw_sym = row.get(symbol_key)
        if raw_sym is None:
            continue
        sym = normalize_symbol(str(raw_sym))
        ts = _extract_timestamp_ms(row, timestamp_key)
        if ts is None:
            continue
        by_sym.setdefault(sym, []).append(ts)

    return {sym: (min(tss), max(tss)) for sym, tss in by_sym.items()}


def _iter_orderbook_files(orderbook_dir: str, target_symbols: list[str]):
    ob_path = Path(orderbook_dir)
    if not ob_path.is_dir():
        return

    ob_path = Path(orderbook_dir)
    norm_targets = {normalize_symbol(s) for s in target_symbols}
    for orderbook_file in ob_path.glob("*.jsonl"):
        stem_parts = orderbook_file.stem.split("_")
        if len(stem_parts) < 3:
            continue
        exchange = stem_parts[0]
        raw_symbol = stem_parts[1]
        if raw_symbol.lower() == "funding":
            continue
        sym = normalize_symbol(raw_symbol)
        if norm_targets and sym not in norm_targets:
            continue
        yield exchange, sym, orderbook_file


def _orderbook_file_date(orderbook_file: Path) -> str | None:
    stem_parts = orderbook_file.stem.split("_")
    if len(stem_parts) < 3:
        return None
    return stem_parts[-1]


def _read_orderbook_file_boundary_timestamps(orderbook_file: Path) -> tuple[int | None, int | None]:
    first_ts: int | None = None
    last_ts: int | None = None
    with open(orderbook_file, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _extract_timestamp_ms(row, "timestamp")
            if ts is None:
                continue
            if first_ts is None:
                first_ts = ts
            last_ts = ts
    return first_ts, last_ts


def _read_orderbook_file_timestamps(orderbook_file: Path, fallback_symbol: str) -> dict[str, list[int]]:
    timestamps_by_symbol: dict[str, list[int]] = defaultdict(list)
    with open(orderbook_file, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _extract_timestamp_ms(row, "timestamp")
            if ts is None:
                continue
            row_symbol = normalize_symbol(str(row.get("symbol", fallback_symbol)))
            timestamps_by_symbol[row_symbol].append(ts)
    return timestamps_by_symbol


def _build_orderbook_stats(
    orderbook_dir: str,
    target_symbols: list[str],
) -> tuple[dict[str, tuple[int, int]], dict[str, float], list[str]]:
    """Build orderbook spans and latest-24h minute coverage from flat JSONL files."""
    spans: dict[str, tuple[int, int]] = {}
    coverage_by_symbol = {normalize_symbol(sym): 0.0 for sym in target_symbols}
    files_by_symbol: dict[str, list[Path]] = defaultdict(list)
    for _, file_symbol, orderbook_file in _iter_orderbook_files(orderbook_dir, target_symbols) or []:
        files_by_symbol[file_symbol].append(orderbook_file)

    symbols_with_data: list[str] = []
    for sym, symbol_files in files_by_symbol.items():
        if not symbol_files:
            continue
        symbols_with_data.append(sym)

        symbol_files = sorted(symbol_files, key=lambda path: (_orderbook_file_date(path) or "", path.name))
        earliest_file = symbol_files[0]
        latest_file = symbol_files[-1]

        earliest_first_ts, _ = _read_orderbook_file_boundary_timestamps(earliest_file)
        _, latest_last_ts = _read_orderbook_file_boundary_timestamps(latest_file)
        if earliest_first_ts is not None and latest_last_ts is not None:
            spans[sym] = (earliest_first_ts, latest_last_ts)

        latest_dates = sorted(
            {date_str for date_str in (_orderbook_file_date(path) for path in symbol_files) if date_str},
        )[-2:]
        timestamps: list[int] = []
        for orderbook_file in symbol_files:
            if _orderbook_file_date(orderbook_file) not in latest_dates:
                continue
            timestamps.extend(_read_orderbook_file_timestamps(orderbook_file, sym).get(sym, []))
        if not timestamps:
            continue

        latest = max(timestamps)
        window_start = latest - 24 * 60 * 60 * 1000
        unique_minutes = {
            (ts // 60_000) * 60_000
            for ts in timestamps
            if window_start <= ts <= latest
        }
        coverage_by_symbol[sym] = compute_coverage_ratio(
            [{"timestamp_ms": minute_ts} for minute_ts in unique_minutes],
            expected_minutes=1440,
        )

    return spans, coverage_by_symbol, sorted(symbols_with_data)


# ─── CLI ──────────────────────────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Route C1 Data Overlap Audit",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["live_overlap", "proxy_snapshot"],
        default="live_overlap",
        help="Audit mode",
    )
    parser.add_argument(
        "--liquidation-1m",
        dest="liquidation_1m",
        default=None,
        help="Path to live liquidation 1m JSONL (required for live_overlap mode)",
    )
    parser.add_argument(
        "--price-1m",
        dest="price_1m",
        default=None,
        help="Path to price 1m JSONL",
    )
    parser.add_argument(
        "--orderbook-dir",
        dest="orderbook_dir",
        default=None,
        help="Path to historical orderbook directory",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"],
        help="Target symbols",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for JSON summary",
    )
    return parser.parse_args(argv)


def run_audit(args: argparse.Namespace) -> dict:
    """Run the overlap audit and return the summary dict."""
    mode = args.mode
    target_symbols = [normalize_symbol(s) for s in args.symbols]

    # --- Check inputs exist ---
    liq_path = args.liquidation_1m
    price_path = args.price_1m
    ob_dir = args.orderbook_dir

    liq_exists = liq_path is not None and Path(liq_path).is_file()
    price_exists = price_path is not None and Path(price_path).is_file()
    ob_exists = ob_dir is not None and Path(ob_dir).is_dir()

    # --- Load data ---
    liq_rows = _load_jsonl(liq_path) if liq_exists else []
    price_rows = _load_jsonl(price_path) if price_exists else []

    # --- Build spans per symbol ---
    liq_spans = _build_spans_from_rows(liq_rows, "symbol", "timestamp_ms") if liq_rows else {}
    price_spans = _build_spans_from_rows(price_rows, "symbol", "timestamp_ms") if price_rows else {}
    if ob_exists:
        ob_spans, ob_coverage_by_symbol, ob_symbols_with_data = _build_orderbook_stats(
            ob_dir,
            args.symbols,
        )
    else:
        ob_spans = {}
        ob_coverage_by_symbol = {sym: 0.0 for sym in target_symbols}
        ob_symbols_with_data = []

    # Filter to target symbols only
    liq_spans = {s: v for s, v in liq_spans.items() if s in target_symbols}
    price_spans = {s: v for s, v in price_spans.items() if s in target_symbols}
    ob_spans = {s: v for s, v in ob_spans.items() if s in target_symbols}

    # --- Compute coverages ---
    liq_coverage_24h = _compute_24h_coverage(liq_rows)
    price_coverage_24h = _compute_24h_coverage(price_rows)
    if ob_symbols_with_data:
        ob_coverage_24h = sum(
            ob_coverage_by_symbol[sym] for sym in ob_symbols_with_data
        ) / len(ob_symbols_with_data)
    else:
        ob_coverage_24h = 0.0

    # --- Compute overlap ---
    overlap_hours_by_symbol = compute_overlap_hours_by_symbol(
        liq_spans, price_spans, ob_spans
    )

    # --- Build initial summary ---
    summary: dict = {
        "mode": mode,
        "liquidation_input_exists": liq_exists,
        "price_input_exists": price_exists,
        "orderbook_dir_exists": ob_exists,
        "primary_blocker": None,
        "liquidation_1m_zero_fill_coverage_24h": liq_coverage_24h,
        "orderbook_snapshot_coverage_24h": ob_coverage_24h,
        "orderbook_snapshot_coverage_by_symbol_24h": ob_coverage_by_symbol,
        "orderbook_symbols_with_data": ob_symbols_with_data,
        "price_1m_coverage_24h": price_coverage_24h,
        "overlap_hours_by_symbol": overlap_hours_by_symbol,
        "ready_for_price_only": False,
        "ready_for_orderbook_aware": False,
        "decision": None,
    }

    # --- Validate mode-specific requirements ---
    if mode == "live_overlap" and not liq_exists:
        summary["primary_blocker"] = "missing_liquidation_1m_input"

    # --- Apply decision logic ---
    summary = compute_overlap_decision(summary)

    return summary


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    summary = run_audit(args)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print(f"Written: {output_path}")
    print(f"  decision                 : {summary['decision']}")
    print(f"  ready_for_price_only     : {summary['ready_for_price_only']}")
    print(f"  ready_for_orderbook_aware: {summary['ready_for_orderbook_aware']}")
    print(f"  primary_blocker          : {summary.get('primary_blocker')}")
    liq_cov = summary.get("liquidation_1m_zero_fill_coverage_24h", 0.0)
    price_cov = summary.get("price_1m_coverage_24h", 0.0)
    print(f"  liq_coverage_24h         : {liq_cov:.3f}")
    print(f"  price_coverage_24h       : {price_cov:.3f}")
    for sym, hrs in summary.get("overlap_hours_by_symbol", {}).items():
        print(f"  overlap {sym:<10}: {hrs:.1f}h")


if __name__ == "__main__":
    main()
