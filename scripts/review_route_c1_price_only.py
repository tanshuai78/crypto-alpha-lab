# -*- coding: utf-8 -*-
"""
scripts/review_route_c1_price_only.py

Route C1 Price-Only Proxy Precheck Script.

Implements:
  - Anti-leakage 5m response window calculation
  - Price risk metrics (vol, range, MAE) from 1m bars
  - C1 event detection (percentile rank + dominance + abs threshold)
  - Matched baseline selection (pre30_vol matching, zero-liq constraint)
  - Per-event ratio summary with decision gate
  - CLI + markdown review renderer

Usage:
  PYTHONPATH=src uv run python scripts/review_route_c1_price_only.py \\
    --run-mode proxy_snapshot \\
    --dataset data/binance_liquidation_snapshot/processed/binance_snapshot_dataset.jsonl \\
    --kline-root data/binance_liquidation_snapshot/extracted/klines \\
    --symbols BTCUSDT ETHUSDT SOLUSDT \\
    --output reports/route_c1/route_c1_price_only_proxy_summary.json \\
    --review-output docs/reviews/2026-06-02-route-c1-price-only-proxy-review.md
"""

from __future__ import annotations

import argparse
import bisect
import csv
import datetime
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

import configs.base as cfg

# ─── Constants ────────────────────────────────────────────────────────────────

_MS_PER_MIN = 60_000
_MS_PER_5M = 300_000
_RANDOM_SEED = 7  # fixed seed for repeatability

_MAJOR_SYMBOLS = {"BTCUSDT", "ETHUSDT"}  # 50k threshold
_ALT_SYMBOLS = {"SOLUSDT", "XRPUSDT", "DOGEUSDT"}  # 10k threshold

ALLOWED_C1_PRICE_ONLY_DECISIONS = (
    "route_c1_data_unavailable",
    "route_c1_baseline_match_failed",
    "route_c1_price_risk_not_confirmed",
    "route_c1_price_risk_proxy_promising_wait_for_live_overlap",
    "route_c1_price_risk_live_smoke_promising_continue_to_30d",
    "route_c1_price_risk_forward_provisional_pass",
    "route_c1_price_risk_forward_failed_stop_route_c",
)


# ─── Symbol Normalization ─────────────────────────────────────────────────────


def normalize_symbol(sym: str) -> str:
    return sym.replace("/", "").replace(":USDT", "").upper()


# ─── Task 2: Response Window & Price Risk Metrics ─────────────────────────────


def first_complete_5m_response_start_ms(shock_bar_start_ms: int) -> int:
    """Return the start ms of the first complete 5m bar after the shock bar.

    Anti-leakage rule:
      - shock at 12:03 is inside [12:00–12:04] 5m bar → response starts at 12:05
      - shock at 12:05 is inside [12:05–12:09] 5m bar → response starts at 12:10

    Formula: ((shock_bar_start_ms // MS_PER_5M) + 1) * MS_PER_5M
    """
    return ((shock_bar_start_ms // _MS_PER_5M) + 1) * _MS_PER_5M


def compute_price_risk_metrics(
    rows: list[dict],
    start_ms: int,
    horizon_minutes: int = 5,
) -> dict | None:
    """Compute direction-agnostic price risk metrics over a response window.

    Args:
        rows:            list of 1m bar dicts with bar_start_ms, open/high/low/close_price
        start_ms:        first bar start ms of the response window
        horizon_minutes: number of 1m bars to include (default 5)

    Returns:
        dict with risk metrics, or None if the window is incomplete.

    Entry price = first_response_row["open_price"] (anti-leakage).
    """
    # Filter rows belonging to the response window
    window = [
        r for r in rows if start_ms <= r["bar_start_ms"] < start_ms + horizon_minutes * _MS_PER_MIN
    ]

    if len(window) < horizon_minutes:
        return None

    # Sort by bar_start_ms
    window = sorted(window, key=lambda r: r["bar_start_ms"])

    entry = window[0]["open_price"]
    if any(r.get("high_price") is None or r.get("low_price") is None for r in window):
        return None
    high = max(float(r["high_price"]) for r in window)
    low = min(float(r["low_price"]) for r in window)

    # Direction-agnostic metrics
    high_low_range_bps = (high / low - 1) * 10_000
    max_abs_excursion_bps = max(abs(high / entry - 1), abs(low / entry - 1)) * 10_000

    # Strategy-conditioned MAE
    mae_if_long_bps = max(0.0, (1.0 - low / entry)) * 10_000
    mae_if_short_bps = max(0.0, (high / entry - 1.0)) * 10_000

    # Realized vol: std of log returns of closes
    closes = [r["close_price"] for r in window]
    if len(closes) >= 2:
        log_returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
        realized_vol_bps = statistics.stdev(log_returns) * 10_000
    else:
        realized_vol_bps = 0.0

    return {
        "realized_vol_5m_bps": realized_vol_bps,
        "high_low_range_5m_bps": high_low_range_bps,
        "max_abs_excursion_5m_bps": max_abs_excursion_bps,
        "mae_if_long_5m_bps": mae_if_long_bps,
        "mae_if_short_5m_bps": mae_if_short_bps,
    }


# ─── Task 3: Event Detection ──────────────────────────────────────────────────


def compute_percentile_rank(value: float, previous_values: list[float]) -> float:
    """Return fraction of previous_values that are strictly less than value.

    If previous_values is empty, return 0.0.
    """
    if not previous_values:
        return 0.0
    n_below = sum(1 for v in previous_values if v < value)
    return n_below / len(previous_values)


def _get_abs_threshold(symbol: str) -> float:
    """Return the absolute liquidation notional threshold for a symbol."""
    norm = normalize_symbol(symbol)
    if norm in _MAJOR_SYMBOLS:
        return cfg.ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT
    return cfg.ROUTE_C1_ALT_ABS_THRESHOLD_USDT


def detect_c1_events(rows: list[dict]) -> list[dict]:
    """Detect C1 liquidation shock events from a list of 1m liquidation rows.

    Rules (from plan §3.1):
    - reference_window = previous 1440 bars (same symbol + side)
    - percentile_rank >= ROUTE_C1_EVENT_PERCENTILE_THRESHOLD (0.995)
    - dominance_ratio >= ROUTE_C1_DOMINANCE_RATIO_MIN (0.65)
    - absolute notional >= threshold (major: 50k, alt: 10k USDT)
    - dedup by symbol + dominant_side + 5m bucket, keep max notional

    Returns:
        list of event dicts
    """
    # Group rows by symbol, sort by bar_start_ms
    by_sym: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        sym = normalize_symbol(str(row.get("symbol", "")))
        by_sym[sym].append(row)

    for sym in by_sym:
        by_sym[sym].sort(key=lambda r: r["bar_start_ms"])

    raw_events: list[dict] = []

    for sym, sym_rows in by_sym.items():
        abs_threshold = _get_abs_threshold(sym)
        side_reference: dict[str, list[float]] = {"long": [], "short": []}

        for row in sym_rows:
            long_notional = float(row.get("long_liquidation_notional_1m_usdt", 0.0) or 0.0)
            short_notional = float(row.get("short_liquidation_notional_1m_usdt", 0.0) or 0.0)
            # Prefer explicit total; fall back to long + short when field absent
            _raw_total = row.get("total_liquidation_notional_1m_usdt")
            total_notional = (
                float(_raw_total) if _raw_total is not None else long_notional + short_notional
            )
            bar_ms = int(row["bar_start_ms"])
            dominant_side = "long" if long_notional >= short_notional else "short"
            dominant_notional = max(long_notional, short_notional)
            dominant_reference = side_reference[dominant_side]

            # Check reference window is sufficient (must have 1440 reference bars for the same side)
            if len(dominant_reference) >= cfg.ROUTE_C1_REQUIRED_REFERENCE_BARS:
                ref_window = dominant_reference[-cfg.ROUTE_C1_REQUIRED_REFERENCE_BARS :]
                pct_rank = compute_percentile_rank(dominant_notional, ref_window)

                if pct_rank >= cfg.ROUTE_C1_EVENT_PERCENTILE_THRESHOLD:
                    # Absolute threshold check
                    if total_notional >= abs_threshold:
                        # Dominance check
                        if total_notional > 0:
                            dominance_ratio = dominant_notional / total_notional
                        else:
                            dominance_ratio = 0.0
                            dominant_side = "none"

                        if dominance_ratio >= cfg.ROUTE_C1_DOMINANCE_RATIO_MIN:
                            dedup_bucket_start_ms = (
                                bar_ms // (cfg.ROUTE_C1_DEDUP_BUCKET_MINUTES * _MS_PER_MIN)
                            ) * (cfg.ROUTE_C1_DEDUP_BUCKET_MINUTES * _MS_PER_MIN)

                            raw_events.append(
                                {
                                    "symbol": sym,
                                    "shock_bar_start_ms": bar_ms,
                                    "dominant_liquidation_side": dominant_side,
                                    "shock_notional_usdt": total_notional,
                                    "relative_score": pct_rank,
                                    "reference_count": len(ref_window),
                                    "dominance_ratio": dominance_ratio,
                                    "dedup_bucket_start_ms": dedup_bucket_start_ms,
                                }
                            )

            side_reference["long"].append(long_notional)
            side_reference["short"].append(short_notional)

    # Deduplicate
    return deduplicate_c1_events(raw_events)


def deduplicate_c1_events(events: list[dict]) -> list[dict]:
    """Deduplicate events by symbol + dominant_side + 5m bucket, keeping max notional."""
    bucket_map: dict[tuple, dict] = {}

    for event in events:
        key = (
            event["symbol"],
            event["dominant_liquidation_side"],
            event["dedup_bucket_start_ms"],
        )
        if key not in bucket_map:
            bucket_map[key] = event
        elif event["shock_notional_usdt"] > bucket_map[key]["shock_notional_usdt"]:
            bucket_map[key] = event

    return sorted(bucket_map.values(), key=lambda e: e["shock_bar_start_ms"])


# ─── Task 4: Baseline Matching ────────────────────────────────────────────────


def annotate_pre30_vol_buckets(rows: list[dict]) -> list[dict]:
    """Annotate rows with pre30_vol (std of 30 log returns before each bar).

    pre30_vol is None for the first 30 rows (insufficient history).
    Uses log(close_t / close_t_minus_1).

    Modifies rows in place and returns them.
    """
    closes = []
    annotated = []

    for row in rows:
        close = float(row.get("close_price", 0.0))

        if len(closes) >= 30:
            # 30 most recent closes before this bar
            prev_closes = closes[-30:]
            log_returns = [
                math.log(prev_closes[i] / prev_closes[i - 1])
                for i in range(1, len(prev_closes))
                if prev_closes[i - 1] > 0 and prev_closes[i] > 0
            ]
            if len(log_returns) >= 2:
                pre30_vol = statistics.stdev(log_returns)
            elif log_returns:
                pre30_vol = 0.0
            else:
                pre30_vol = None
        else:
            pre30_vol = None

        annotated_row = dict(row)
        annotated_row["pre30_vol"] = pre30_vol
        annotated.append(annotated_row)
        closes.append(close)

    return annotated


def _build_contaminated_bar_set(rows_by_ms: dict[int, dict]) -> set[int]:
    """Precompute the set of bar_start_ms with nonzero liquidation notional.

    Called once per symbol; O(n) build, then O(1) lookup in guard checks.
    """
    contaminated: set[int] = set()
    for bar_ms, row in rows_by_ms.items():
        _raw_total = row.get("total_liquidation_notional_1m_usdt")
        if _raw_total is not None:
            notional = float(_raw_total or 0.0)
        else:
            notional = float(row.get("long_liquidation_notional_1m_usdt", 0.0) or 0.0) + float(
                row.get("short_liquidation_notional_1m_usdt", 0.0) or 0.0
            )
        if notional > 0.0:
            contaminated.add(bar_ms)
    return contaminated


def _has_any_liquidation_in_range(
    rows_by_ms: dict[int, dict],
    start_ms: int,
    end_ms: int,
) -> bool:
    """Check whether any bar in [start_ms, end_ms) has nonzero liquidation notional.

    Kept for backward compatibility with tests; internally does dict lookups.
    """
    bar_ms = start_ms
    while bar_ms < end_ms:
        row = rows_by_ms.get(bar_ms)
        if row is not None:
            _raw_total = row.get("total_liquidation_notional_1m_usdt")
            if _raw_total is not None:
                notional = float(_raw_total or 0.0)
            else:
                notional = float(row.get("long_liquidation_notional_1m_usdt", 0.0) or 0.0) + float(
                    row.get("short_liquidation_notional_1m_usdt", 0.0) or 0.0
                )
            if notional > 0.0:
                return True
        bar_ms += _MS_PER_MIN
    return False


def _guard_is_clean(cand_ms: int, contaminated: set[int]) -> bool:
    """O(65) set-membership guard: candidate + future 5m + ±30m guard must be liq-free."""
    guard_start = cand_ms - 30 * _MS_PER_MIN
    guard_end = cand_ms + (5 + 30) * _MS_PER_MIN
    bar_ms = guard_start
    while bar_ms < guard_end:
        if bar_ms in contaminated:
            return False
        bar_ms += _MS_PER_MIN
    return True


def has_complete_response_window(rows_by_ms: dict[int, dict], cand_ms: int) -> bool:
    """Return True when the first complete post-candidate 5m response window exists."""
    response_start_ms = first_complete_5m_response_start_ms(cand_ms)
    for i in range(5):
        if response_start_ms + i * _MS_PER_MIN not in rows_by_ms:
            return False
    return True


def _compute_vol_bucket(
    vol: float | None,
    pre30_vols_sorted: list[float],
    n_buckets: int = 10,
) -> int | None:
    if vol is None or not pre30_vols_sorted:
        return None
    rank = bisect.bisect_left(pre30_vols_sorted, vol) / len(pre30_vols_sorted)
    return int(rank * n_buckets)


def match_baselines_for_event(
    event: dict,
    candidate_rows: list[dict],
    k: int = 20,
    _contaminated: set[int] | None = None,
    _rows_by_ms: dict[int, dict] | None = None,
    _pre30_vols_sorted: list[float] | None = None,
    _candidate_infos: list[tuple[int, int, int | None]] | None = None,
) -> list[dict]:
    """Match up to k baseline windows for a single event.

    Matching rules (plan §3.4):
    Primary:
      1. same symbol
      2. same hour-of-day ±1h
      3. pre30_vol percentile in same 10% bucket
      4. zero liquidation in candidate + future 5m + ±30m guard
      5. no overlap with event response window

    Fallback 1: relax hour-of-day constraint
    Fallback 2: relax vol bucket by ±2 buckets

    Performance notes (vs. original):
    - Candidate pool pre-filtered once (anti-leakage + completeness + clean).
    - Contamination guard uses precomputed set → O(65) set lookups vs O(65) dict probes.
    - Vol bucket uses bisect on sorted array → O(log n) vs O(n) per call.
    - shuffle done once; fallback loops just re-filter the same shuffled list.

    Returns a list of baseline dicts with keys:
      candidate_bar_start_ms, has_complete_future_window, contamination_free
    """
    event_shock_ms = int(event["shock_bar_start_ms"])
    event_response_start_ms = first_complete_5m_response_start_ms(event_shock_ms)
    event_response_end_ms = event_response_start_ms + 5 * _MS_PER_MIN
    event_month = _month_key(event_shock_ms)

    # Index rows by bar_start_ms
    rows_by_ms: dict[int, dict] = (
        _rows_by_ms
        if _rows_by_ms is not None
        else {int(r["bar_start_ms"]): r for r in candidate_rows}
    )
    all_bar_ms_sorted = sorted(rows_by_ms.keys())

    # ── Contamination set (O(n) build, O(1) lookup) ─────────────────────────
    if _contaminated is None:
        _contaminated = _build_contaminated_bar_set(rows_by_ms)

    # ── Vol bucket: O(n log n) sort once, O(log n) per lookup ───────────────
    month_rows = [r for r in candidate_rows if _month_key(int(r["bar_start_ms"])) == event_month]
    pre30_vols_sorted = (
        _pre30_vols_sorted
        if _pre30_vols_sorted is not None
        else sorted(v for r in month_rows if (v := r.get("pre30_vol")) is not None)
    )
    _MS_PER_HOUR = 3_600_000

    event_row = rows_by_ms.get(event_shock_ms)
    event_vol = event_row.get("pre30_vol") if event_row else None
    event_vol_bucket = _compute_vol_bucket(event_vol, pre30_vols_sorted)
    event_hour = (event_shock_ms % (24 * _MS_PER_HOUR)) // _MS_PER_HOUR

    # ── Pre-filter candidates once (most expensive checks first) ────────────
    def _overlaps_event_window(cand_ms: int) -> bool:
        cand_resp_start = first_complete_5m_response_start_ms(cand_ms)
        cand_resp_end = cand_resp_start + 5 * _MS_PER_MIN
        return not (
            cand_resp_end <= event_response_start_ms or cand_resp_start >= event_response_end_ms
        )

    if _candidate_infos is None:
        rng = random.Random(_RANDOM_SEED)
        candidates_pre: list[tuple[int, int, int | None]] = []
        for cand_ms in all_bar_ms_sorted:
            if cand_ms >= event_shock_ms:
                continue
            if _month_key(cand_ms) != event_month:
                continue
            if _overlaps_event_window(cand_ms):
                continue
            if not has_complete_response_window(rows_by_ms, cand_ms):
                continue
            if not _guard_is_clean(cand_ms, _contaminated):
                continue
            cand_hour = (cand_ms % (24 * _MS_PER_HOUR)) // _MS_PER_HOUR
            cand_row = rows_by_ms.get(cand_ms)
            cand_bucket = _compute_vol_bucket(
                cand_row.get("pre30_vol") if cand_row else None,
                pre30_vols_sorted,
            )
            candidates_pre.append((cand_ms, cand_hour, cand_bucket))
        rng.shuffle(candidates_pre)
    else:
        candidates_pre = _candidate_infos

    def _try_match(relax_time: bool, vol_bucket_slack: int) -> list[dict]:
        matched = []
        for cand_ms, cand_hour, cand_bucket in candidates_pre:
            if len(matched) >= k:
                break
            if cand_ms >= event_shock_ms:
                continue
            if _overlaps_event_window(cand_ms):
                continue
            if not relax_time and abs(int(cand_hour) - int(event_hour)) > 1:
                continue
            if cand_bucket is not None and event_vol_bucket is not None:
                if abs(cand_bucket - event_vol_bucket) > vol_bucket_slack:
                    continue
            matched.append(
                {
                    "candidate_bar_start_ms": cand_ms,
                    "has_complete_future_window": True,
                    "contamination_free": True,
                    "relaxed_time": relax_time,
                    "vol_bucket_slack": vol_bucket_slack,
                }
            )
        return matched

    # Primary: strict hour + strict vol bucket
    matched = _try_match(relax_time=False, vol_bucket_slack=0)

    # Fallback 2: relax vol bucket to ±2
    if len(matched) < k:
        matched = _try_match(relax_time=True, vol_bucket_slack=2)

    return matched[:k]


def build_event_baseline_pairs(
    events: list[dict],
    rows_by_symbol: dict[str, list[dict]],
    k: int = 20,
) -> list[dict]:
    """Build matched event-baseline pairs, excluding unmatched events.

    Args:
        events:          list of event dicts (from detect_c1_events)
        rows_by_symbol:  {normalized_symbol: [annotated rows]}
        k:               target baseline count per event

    Returns:
        list of pair dicts with keys: event, event_metrics, baseline_metrics
        Unmatched events (0 baselines) are excluded.

    Performance: contamination set is computed once per symbol (not per event).
    """
    pairs = []

    rows_by_sym_month: dict[tuple[str, str], list[dict]] = {}
    rows_by_ms_by_sym_month: dict[tuple[str, str], dict[int, dict]] = {}
    contaminated_by_sym_month: dict[tuple[str, str], set[int]] = {}
    pre30_vols_sorted_by_sym_month: dict[tuple[str, str], list[float]] = {}
    candidate_infos_by_sym_month: dict[tuple[str, str], list[tuple[int, int, int | None]]] = {}

    for sym, sym_rows in rows_by_symbol.items():
        month_buckets: dict[str, list[dict]] = defaultdict(list)
        for row in sym_rows:
            month_buckets[_month_key(int(row["bar_start_ms"]))].append(row)
        for month_key, month_rows in month_buckets.items():
            key = (sym, month_key)
            rows_by_sym_month[key] = month_rows
            rows_by_ms = {int(r["bar_start_ms"]): r for r in month_rows}
            rows_by_ms_by_sym_month[key] = rows_by_ms
            contaminated = _build_contaminated_bar_set(rows_by_ms)
            contaminated_by_sym_month[key] = contaminated
            pre30_vols_sorted = sorted(v for r in month_rows if (v := r.get("pre30_vol")) is not None)
            pre30_vols_sorted_by_sym_month[key] = pre30_vols_sorted
            rng = random.Random(_RANDOM_SEED)
            candidate_infos: list[tuple[int, int, int | None]] = []
            for cand_ms in sorted(rows_by_ms.keys()):
                if not has_complete_response_window(rows_by_ms, cand_ms):
                    continue
                if not _guard_is_clean(cand_ms, contaminated):
                    continue
                cand_hour = (cand_ms % (24 * 3_600_000)) // 3_600_000
                cand_row = rows_by_ms.get(cand_ms)
                cand_bucket = _compute_vol_bucket(
                    cand_row.get("pre30_vol") if cand_row else None,
                    pre30_vols_sorted,
                )
                candidate_infos.append((cand_ms, cand_hour, cand_bucket))
            rng.shuffle(candidate_infos)
            candidate_infos_by_sym_month[key] = candidate_infos

    for event in events:
        sym = normalize_symbol(event["symbol"])
        month_key = _month_key(int(event["shock_bar_start_ms"]))
        key = (sym, month_key)
        sym_rows = rows_by_sym_month.get(key, [])

        if not sym_rows:
            continue

        contaminated = contaminated_by_sym_month.get(key)
        baselines = match_baselines_for_event(
            event,
            sym_rows,
            k=k,
            _contaminated=contaminated,
            _rows_by_ms=rows_by_ms_by_sym_month[key],
            _pre30_vols_sorted=pre30_vols_sorted_by_sym_month[key],
            _candidate_infos=candidate_infos_by_sym_month[key],
        )

        if not baselines:
            continue  # unmatched → excluded from stats

        # Compute event price risk metrics
        shock_ms = int(event["shock_bar_start_ms"])
        response_start_ms = first_complete_5m_response_start_ms(shock_ms)
        rows_by_ms = rows_by_ms_by_sym_month[key]
        response_rows = [
            rows_by_ms[response_start_ms + i * _MS_PER_MIN]
            for i in range(5)
            if response_start_ms + i * _MS_PER_MIN in rows_by_ms
        ]

        event_metrics = compute_price_risk_metrics(response_rows, response_start_ms)

        # Compute baseline price risk metrics
        baseline_metrics_list = []
        for bl in baselines:
            cand_ms = int(bl["candidate_bar_start_ms"])
            cand_response_start = first_complete_5m_response_start_ms(cand_ms)
            cand_response_rows = [
                rows_by_ms[cand_response_start + i * _MS_PER_MIN]
                for i in range(5)
                if cand_response_start + i * _MS_PER_MIN in rows_by_ms
            ]
            bl_metrics = compute_price_risk_metrics(cand_response_rows, cand_response_start)
            if bl_metrics is not None:
                baseline_metrics_list.append(bl_metrics)

        if event_metrics is None or not baseline_metrics_list:
            continue

        pairs.append(
            {
                "event": event,
                "event_metrics": event_metrics,
                "baseline_metrics": baseline_metrics_list,
            }
        )

    return pairs


# ─── Task 5: Summary & Decision Gate ─────────────────────────────────────────


def _percentile(values: list[float], pct: float) -> float:
    """Return the pct-th percentile of values (linear interpolation)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    idx = pct * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _median_safe(values: list[float]) -> float:
    if not values:
        return 0.0
    return statistics.median(values)


def build_c1_price_only_summary(
    pairs: list[dict],
    metadata: dict,
) -> dict:
    """Build the C1 price-only summary dict from matched event-baseline pairs.

    Ratio aggregation contract:
      For each matched event:
        baseline_anchor = median(metric across K matched baseline windows)
        event_ratio = event_metric / baseline_anchor (if anchor > 0)
      Summary ratio = median(event_ratio across matched events)

    Not: median(all events) / median(all baselines) — that loses matched-control structure.
    """
    run_mode = metadata.get("run_mode", "proxy_snapshot")
    data_source = metadata.get("data_source", "unknown")

    n_matched = len(pairs)
    total_events = metadata.get("total_events", n_matched)

    # Collect per-event ratios
    vol_ratios: list[float] = []
    range_ratios: list[float] = []
    excursion_ratios: list[float] = []

    # Collect raw event excursion and MAE p90
    event_excursions: list[float] = []
    event_mae_long: list[float] = []
    event_mae_short: list[float] = []

    # Concentration tracking
    events_by_symbol: dict[str, int] = defaultdict(int)
    events_by_month: dict[str, int] = defaultdict(int)
    events_by_day: dict[str, int] = defaultdict(int)

    for pair in pairs:
        ev = pair["event"]
        em = pair["event_metrics"]
        bms = pair["baseline_metrics"]

        sym = normalize_symbol(str(ev["symbol"]))
        shock_ms = int(ev["shock_bar_start_ms"])

        # Concentration
        events_by_symbol[sym] += 1
        # month: YYYY-MM from ms
        day_str = _ms_to_date_str(shock_ms)
        month_str = day_str[:7]
        events_by_month[month_str] += 1
        events_by_day[day_str] += 1

        # Baseline median anchors
        bl_vol_med = _median_safe([b["realized_vol_5m_bps"] for b in bms])
        bl_range_med = _median_safe([b["high_low_range_5m_bps"] for b in bms])
        bl_excursion_med = _median_safe([b["max_abs_excursion_5m_bps"] for b in bms])

        if bl_vol_med > 0:
            vol_ratios.append(em["realized_vol_5m_bps"] / bl_vol_med)
        if bl_range_med > 0:
            range_ratios.append(em["high_low_range_5m_bps"] / bl_range_med)
        if bl_excursion_med > 0:
            excursion_ratios.append(em["max_abs_excursion_5m_bps"] / bl_excursion_med)

        event_excursions.append(em["max_abs_excursion_5m_bps"])
        event_mae_long.append(em["mae_if_long_5m_bps"])
        event_mae_short.append(em["mae_if_short_5m_bps"])

    # Concentration metrics
    matched_events = n_matched
    max_sym_share = max(events_by_symbol.values()) / matched_events if matched_events > 0 else 0.0
    max_month_share = max(events_by_month.values()) / matched_events if matched_events > 0 else 0.0
    max_day_share = max(events_by_day.values()) / matched_events if matched_events > 0 else 0.0

    # Gate inputs
    post_event_vol_ratio_median = _median_safe(vol_ratios)
    post_event_range_ratio_median = _median_safe(range_ratios)
    post_event_abs_excursion_p90_ratio = (
        _percentile(excursion_ratios, 0.90) if excursion_ratios else 0.0
    )

    # Proxy weak kill-switch
    proxy_kill_switch_weak = (
        post_event_vol_ratio_median < cfg.ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX
        and post_event_range_ratio_median < cfg.ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX
        and post_event_abs_excursion_p90_ratio < cfg.ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX
    )

    # Route C1 params snapshot
    route_c1_params = {
        "ROUTE_C1_EVENT_PERCENTILE_THRESHOLD": cfg.ROUTE_C1_EVENT_PERCENTILE_THRESHOLD,
        "ROUTE_C1_REQUIRED_REFERENCE_BARS": cfg.ROUTE_C1_REQUIRED_REFERENCE_BARS,
        "ROUTE_C1_DOMINANCE_RATIO_MIN": cfg.ROUTE_C1_DOMINANCE_RATIO_MIN,
        "ROUTE_C1_DEDUP_BUCKET_MINUTES": cfg.ROUTE_C1_DEDUP_BUCKET_MINUTES,
        "ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT": cfg.ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT,
        "ROUTE_C1_ALT_ABS_THRESHOLD_USDT": cfg.ROUTE_C1_ALT_ABS_THRESHOLD_USDT,
        "ROUTE_C1_BASELINE_MATCH_COUNT": cfg.ROUTE_C1_BASELINE_MATCH_COUNT,
        "ROUTE_C1_BASELINE_MATCH_RATE_MIN": cfg.ROUTE_C1_BASELINE_MATCH_RATE_MIN,
        "ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX": cfg.ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX,
        "ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX": cfg.ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX,
        "ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX": cfg.ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX,
    }

    summary = {
        "run_mode": run_mode,
        "data_source": data_source,
        "data_semantics": "snapshot_proxy_not_complete_liquidation_tape",
        "generalization_allowed": False,
        "can_promote_live_filter": False,
        "event_count": total_events,
        "matched_event_count": n_matched,
        "unmatched_event_count": total_events - n_matched,
        "matched_baseline_count": sum(len(p["baseline_metrics"]) for p in pairs),
        "baseline_match_rate": (n_matched / total_events)
        if total_events > 0
        else 0.0,
        "post_event_vol_ratio_median": post_event_vol_ratio_median,
        "post_event_range_ratio_median": post_event_range_ratio_median,
        "post_event_abs_excursion_p90_ratio": post_event_abs_excursion_p90_ratio,
        "max_abs_excursion_p90_bps": _percentile(event_excursions, 0.90),
        "mae_if_long_p90_bps": _percentile(event_mae_long, 0.90),
        "mae_if_short_p90_bps": _percentile(event_mae_short, 0.90),
        "events_by_symbol": dict(events_by_symbol),
        "events_by_month": dict(events_by_month),
        "events_by_day": dict(events_by_day),
        "sample_days": len(events_by_day),
        "max_single_symbol_event_share": max_sym_share,
        "max_single_month_event_share": max_month_share,
        "max_single_day_event_share": max_day_share,
        "route_c1_params": route_c1_params,
        "proxy_kill_switch_weak": proxy_kill_switch_weak,
        "decision": "route_c1_price_risk_not_confirmed",  # placeholder; set by compute_c1_price_only_decision
    }

    return summary


def compute_c1_price_only_decision(summary: dict, run_mode: str) -> str:
    """Compute the C1 price-only decision label from a summary dict.

    Run-mode specific gates (plan §3.5):
      proxy_snapshot:    require months_passing >= 2, always can_promote_live_filter=False
      live_smoke_7d:     require overlap_hours >= 168, no months gate
      forward_30d:       require sample_days >= 30, use day concentration gate

    Returns one of ALLOWED_C1_PRICE_ONLY_DECISIONS.
    """
    n_events = summary.get("event_count", 0)
    n_matched = summary.get("matched_event_count", 0)

    if n_events == 0:
        return "route_c1_data_unavailable"

    match_rate = summary.get("baseline_match_rate", 0.0)
    if n_matched == 0 or match_rate < cfg.ROUTE_C1_BASELINE_MATCH_RATE_MIN:
        return "route_c1_baseline_match_failed"

    vol_ratio = summary.get("post_event_vol_ratio_median", 0.0)
    range_ratio = summary.get("post_event_range_ratio_median", 0.0)
    excursion_p90_ratio = summary.get("post_event_abs_excursion_p90_ratio", 0.0)

    # Hard gate checks
    vol_pass = vol_ratio >= 1.5
    range_pass = range_ratio >= 1.4
    excursion_pass = excursion_p90_ratio >= 1.3

    # Symbol diversity (need >= 2 of BTC/ETH/SOL passing)
    events_by_symbol = summary.get("events_by_symbol", {})
    major_sym_count = sum(
        1 for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT") if events_by_symbol.get(sym, 0) > 0
    )

    # Concentration limits
    max_sym_share = summary.get("max_single_symbol_event_share", 1.0)
    max_month_share = summary.get("max_single_month_event_share", 1.0)
    max_day_share = summary.get("max_single_day_event_share", 1.0)

    sym_concentration_ok = max_sym_share <= 0.60
    month_concentration_ok = max_month_share <= 0.60
    day_concentration_ok = max_day_share <= 0.60

    # Run-mode specific decisions
    if run_mode == "proxy_snapshot":
        # Requires months_passing >= 2
        events_by_month = summary.get("events_by_month", {})
        months_passing = len(events_by_month)

        all_hard_gates = (
            vol_pass
            and range_pass
            and excursion_pass
            and n_events >= 100
            and n_matched >= 70
            and major_sym_count >= 2
            and months_passing >= 2
            and sym_concentration_ok
            and month_concentration_ok
        )

        if all_hard_gates:
            return "route_c1_price_risk_proxy_promising_wait_for_live_overlap"
        else:
            return "route_c1_price_risk_not_confirmed"

    elif run_mode == "live_smoke_7d":
        # Does not require months_passing; requires overlap_hours >= 168
        overlap_hours = summary.get("overlap_hours", 0.0)
        if overlap_hours < 168.0:
            # Not enough overlap time
            return "route_c1_price_risk_not_confirmed"

        ratio_gates_pass = vol_pass and range_pass and excursion_pass
        if ratio_gates_pass and sym_concentration_ok:
            return "route_c1_price_risk_live_smoke_promising_continue_to_30d"
        else:
            return "route_c1_price_risk_not_confirmed"

    elif run_mode == "forward_30d":
        # Requires sample_days >= 30, use day concentration instead of month
        sample_days = summary.get("sample_days", 0)
        if sample_days < 30:
            return "route_c1_price_risk_not_confirmed"

        all_gates = (
            vol_pass
            and range_pass
            and excursion_pass
            and n_events >= 100
            and n_matched >= 70
            and major_sym_count >= 2
            and sym_concentration_ok
            and day_concentration_ok
        )

        if all_gates:
            return "route_c1_price_risk_forward_provisional_pass"
        else:
            return "route_c1_price_risk_forward_failed_stop_route_c"

    # Unknown run_mode fallback
    return "route_c1_price_risk_not_confirmed"


# ─── Task 6: CLI & Dataset Loading ───────────────────────────────────────────


def normalize_symbol(sym: str) -> str:  # noqa: F811 (re-export)
    return sym.replace("/", "").replace(":USDT", "").upper()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for review_route_c1_price_only.py."""
    parser = argparse.ArgumentParser(
        description="Route C1 Price-Only Proxy Precheck",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--run-mode",
        dest="run_mode",
        choices=["proxy_snapshot", "live_smoke_7d", "forward_30d"],
        default="proxy_snapshot",
        help="Run mode",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to JSONL dataset (processed Binance snapshot or live 1m aggs)",
    )
    parser.add_argument(
        "--kline-root",
        dest="kline_root",
        default=None,
        help="Root directory of extracted 1m kline CSVs (symbol subdirs)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        help="Symbols to include",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for JSON summary",
    )
    parser.add_argument(
        "--review-output",
        dest="review_output",
        default=None,
        help="Output path for markdown review",
    )
    return parser.parse_args(argv)


def load_dataset(
    dataset_path: str,
    kline_root: str | None = None,
    symbols: list[str] | None = None,
) -> list[dict]:
    """Load JSONL dataset, optionally merging high/low from kline CSVs.

    Symbol normalization is applied before kline join.

    Args:
        dataset_path: path to JSONL file
        kline_root:   directory with per-symbol kline CSV subdirs
        symbols:      list of normalized symbols to include (None = all)

    Returns:
        list of row dicts with open/high/low/close prices
    """
    target_symbols = {normalize_symbol(s) for s in symbols} if symbols else None

    # Load base dataset
    rows: list[dict] = []
    try:
        with open(dataset_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # Normalize symbol
                raw_sym = row.get("symbol", "")
                norm_sym = normalize_symbol(str(raw_sym))
                if target_symbols and norm_sym not in target_symbols:
                    continue
                row["symbol"] = norm_sym
                rows.append(row)
    except (OSError, IOError):
        return []

    # Merge high/low from kline CSVs if kline_root is provided
    if kline_root:
        kline_root_path = Path(kline_root)
        # Build kline index: {(normalized_symbol, bar_start_ms): {high_price, low_price}}
        kline_index: dict[tuple[str, int], dict] = {}

        for row in rows:
            sym = row["symbol"]
            if (sym, row.get("bar_start_ms")) in kline_index:
                continue  # already indexed

        def _parse_kline_row(krow: dict) -> tuple[int, float, float] | None:
            if "bar_start_ms" in krow:
                ts_key = "bar_start_ms"
                high_key = "high_price"
                low_key = "low_price"
            elif "open_time" in krow:
                ts_key = "open_time"
                high_key = "high"
                low_key = "low"
            else:
                return None
            try:
                return (int(krow[ts_key]), float(krow[high_key]), float(krow[low_key]))
            except (KeyError, TypeError, ValueError):
                return None

        # Load klines per symbol
        if target_symbols:
            sym_dirs = [kline_root_path / sym for sym in target_symbols]
        else:
            sym_dirs = [d for d in kline_root_path.iterdir() if d.is_dir()]

        for sym_dir in sym_dirs:
            if not sym_dir.is_dir():
                continue
            sym = normalize_symbol(sym_dir.name)
            for csv_file in sym_dir.rglob("*.csv"):
                try:
                    with open(csv_file, newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for krow in reader:
                            parsed = _parse_kline_row(krow)
                            if parsed is None:
                                continue
                            bar_ms, high_price, low_price = parsed
                            kline_index[(sym, bar_ms)] = {
                                "high_price": high_price,
                                "low_price": low_price,
                            }
                except (OSError, IOError):
                    continue

        # Merge into rows
        for row in rows:
            sym = row["symbol"]
            bar_ms = row.get("bar_start_ms")
            key = (sym, bar_ms)
            if key in kline_index:
                kline_data = kline_index[key]
                # Only merge if missing in dataset row
                if "high_price" not in row or row["high_price"] is None:
                    row["high_price"] = kline_data["high_price"]
                if "low_price" not in row or row["low_price"] is None:
                    row["low_price"] = kline_data["low_price"]

    missing_hilo = [
        row for row in rows if row.get("high_price") is None or row.get("low_price") is None
    ]
    if missing_hilo:
        raise ValueError("high_price/low_price missing after dataset load; kline merge required")

    return rows


def render_review_markdown(summary: dict, output_path: str) -> None:
    """Render a markdown review file from a C1 price-only summary dict."""
    decision = summary.get("decision", "unknown")
    run_mode = summary.get("run_mode", "unknown")
    n_events = summary.get("event_count", 0)
    n_matched = summary.get("matched_event_count", 0)
    match_rate = summary.get("baseline_match_rate", 0.0)
    vol_ratio = summary.get("post_event_vol_ratio_median", 0.0)
    range_ratio = summary.get("post_event_range_ratio_median", 0.0)
    excursion_ratio = summary.get("post_event_abs_excursion_p90_ratio", 0.0)
    proxy_weak = summary.get("proxy_kill_switch_weak", False)
    can_promote = summary.get("can_promote_live_filter", False)
    data_source = summary.get("data_source", "unknown")
    data_semantics = summary.get("data_semantics", "unknown")
    generalization_allowed = summary.get("generalization_allowed", False)

    lines = [
        "# Route C1 Price-Only Proxy Precheck Review",
        "",
        f"> **IMPORTANT:** This proxy cannot promote to live filter (`can_promote_live_filter: {str(can_promote).lower()}`).  ",
        f"> Generalization allowed: `{str(generalization_allowed).lower()}`.  ",
        f"> Data semantics: `{data_semantics}`.",
        "",
        "## Run Mode",
        "",
        f"- `run_mode`: `{run_mode}`",
        f"- `data_source`: `{data_source}`",
        "",
        "## Data Coverage",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| events detected | {n_events} |",
        f"| matched events | {n_matched} |",
        f"| baseline match rate | {match_rate:.3f} |",
        f"| sample_days | {summary.get('sample_days', 0)} |",
        "",
        "## Price Risk Ratios (Event / Baseline Median)",
        "",
        "| Metric | Value | Gate |",
        "|---|---|---|",
        f"| post_event_vol_ratio_median | {vol_ratio:.3f} | >= 1.5 |",
        f"| post_event_range_ratio_median | {range_ratio:.3f} | >= 1.4 |",
        f"| post_event_abs_excursion_p90_ratio | {excursion_ratio:.3f} | >= 1.3 |",
        "",
        "## Proxy Kill-Switch",
        "",
        f"- `proxy_kill_switch_weak`: `{str(proxy_weak).lower()}`",
        f"  - vol_ratio < 1.2: {vol_ratio < 1.2}",
        f"  - range_ratio < 1.2: {range_ratio < 1.2}",
        f"  - excursion_p90_ratio < 1.1: {excursion_ratio < 1.1}",
        "",
        "## Event Distribution",
        "",
        "### By Symbol",
        "",
    ]

    for sym, count in sorted(summary.get("events_by_symbol", {}).items()):
        lines.append(f"- `{sym}`: {count}")

    lines += [
        "",
        "### By Month",
        "",
    ]
    for month, count in sorted(summary.get("events_by_month", {}).items()):
        lines.append(f"- `{month}`: {count}")

    lines += [
        "",
        "## Decision",
        "",
        "```",
        f"decision: {decision}",
        "```",
        "",
        "## Next Path",
        "",
    ]

    if decision == "route_c1_price_risk_proxy_promising_wait_for_live_overlap":
        lines += [
            "- `continue_collect_7d_overlap`",
            "- `stop_after_7d_if_live_smoke_weak`",
            "- `continue_to_30d_only_if_live_smoke_promising`",
        ]
    elif proxy_weak:
        lines += [
            "- Proxy kill-switch fired. Continue collecting live liquidation data.",
            "- After 7d live overlap: run live smoke audit.",
            "- If 7d live smoke also weak → stop Route C1.",
            "- Do not wait 30 days if both proxy and 7d smoke are weak.",
        ]
    else:
        lines += [
            "- Ratios below gate thresholds. Continue 7d live overlap collection.",
            "- Run `audit_route_c1_data_overlap.py --mode live_overlap` after 7 days.",
        ]

    lines += [
        "",
        "## Anti-Leakage Contract",
        "",
        "- Entry price = `first_response_row[open_price]` (first complete 5m response bar).",
        "- Response window excludes the shock bar and any partial 5m bar containing it.",
        "- Baseline matched windows must have zero liquidation in candidate + ±30m guard + future 5m.",
        "",
        "## Algorithm Parameters",
        "",
        "```json",
        json.dumps(summary.get("route_c1_params", {}), indent=2),
        "```",
    ]

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    output_path_obj.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ms_to_date_str(ms: int) -> str:
    """Return YYYY-MM-DD string from ms timestamp."""
    dt = datetime.datetime.utcfromtimestamp(ms / 1000.0)
    return dt.strftime("%Y-%m-%d")


def _month_key(ms: int) -> str:
    dt = datetime.datetime.utcfromtimestamp(ms / 1000.0)
    return dt.strftime("%Y-%m")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    print(f"[route-c1] run_mode={args.run_mode} dataset={args.dataset}")

    # Load dataset
    rows = load_dataset(args.dataset, kline_root=args.kline_root, symbols=args.symbols)
    print(f"[route-c1] loaded {len(rows)} rows")

    if not rows:
        print("[route-c1] no rows loaded; aborting")
        return

    # Normalize symbols in rows
    for row in rows:
        row["symbol"] = normalize_symbol(str(row.get("symbol", "")))

    # Group by symbol and annotate pre30_vol
    rows_by_symbol: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        rows_by_symbol[row["symbol"]].append(row)

    for sym in rows_by_symbol:
        rows_by_symbol[sym].sort(key=lambda r: r["bar_start_ms"])
        rows_by_symbol[sym] = annotate_pre30_vol_buckets(rows_by_symbol[sym])

    all_rows = []
    for sym_rows in rows_by_symbol.values():
        all_rows.extend(sym_rows)

    # Detect events
    events = detect_c1_events(all_rows)
    total_events = len(events)
    print(f"[route-c1] detected {total_events} events")

    # Build matched pairs
    pairs = build_event_baseline_pairs(
        events,
        dict(rows_by_symbol),
        k=cfg.ROUTE_C1_BASELINE_MATCH_COUNT,
    )
    n_matched = len(pairs)
    print(f"[route-c1] matched {n_matched}/{total_events} events")

    # Build summary
    metadata = {
        "run_mode": args.run_mode,
        "data_source": "binance_vision_liquidation_snapshot",
        "total_events": total_events,
    }
    summary = build_c1_price_only_summary(pairs, metadata)
    summary["decision"] = compute_c1_price_only_decision(summary, run_mode=args.run_mode)

    # Write JSON output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"[route-c1] written: {output_path}")

    # Write markdown review
    if args.review_output:
        render_review_markdown(summary, args.review_output)
        print(f"[route-c1] review: {args.review_output}")

    # Print key results
    print(f"\n{'=' * 60}")
    print(f"  decision                      : {summary['decision']}")
    print(f"  proxy_kill_switch_weak        : {summary['proxy_kill_switch_weak']}")
    print(f"  event_count                   : {summary['event_count']}")
    print(f"  matched_event_count           : {summary['matched_event_count']}")
    print(f"  baseline_match_rate           : {summary['baseline_match_rate']:.3f}")
    print(f"  post_event_vol_ratio_median   : {summary['post_event_vol_ratio_median']:.3f}")
    print(f"  post_event_range_ratio_median : {summary['post_event_range_ratio_median']:.3f}")
    print(f"  post_event_abs_excursion_p90  : {summary['post_event_abs_excursion_p90_ratio']:.3f}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
