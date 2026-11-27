"""Stage 1.3 fixed-universe mean-return diagnostic domain module.

Reuses canonical Stage 1.3 models, candidate detectors, replay timing helpers,
and forward metrics helper without importing legacy orchestrator/baseline/summary/R10.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
import random
import zipfile
from collections import Counter, deque
from datetime import date, datetime, timedelta, timezone
from statistics import median
from typing import Any

from configs import base
from research.external_signal_shadow.stage1_3_candidates import (
    detect_relative_strength_vs_btc,
    detect_volume_spike_1h,
)
from research.external_signal_shadow.stage1_3_metrics import (
    compute_forward_metrics_from_entry_index,
)
from research.external_signal_shadow.stage1_3_models import (
    STAGE1_3_BAR_INTERVAL_MS,
    HistoricalBar,
    find_duplicate_bar_starts,
    group_bars_by_symbol,
)
from research.external_signal_shadow.stage1_3_replay import (
    build_one_hour_window,
    historical_available_at_ms,
    one_hour_quote_volume,
    one_hour_return,
    select_entry_bar,
)
from risk.limits import RiskLimits

EXPECTED_SYMBOLS: tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
)
EXPECTED_CANDIDATES: tuple[str, ...] = (
    "volume_spike_1h",
    "relative_strength_vs_btc",
)
WARMUP_START_UTC = "2026-06-08T00:00:00Z"
EVAL_START_UTC = "2026-06-15T00:00:00Z"
EVAL_END_UTC = "2026-11-23T00:00:00Z"
BLOCK_COUNT = 23
BLOCK_DAYS = 7
FIRST_HALF_BLOCK_COUNT = 11
SECOND_HALF_BLOCK_COUNT = 12
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20261123
MS_PER_HOUR = 3_600_000
MS_PER_DAY = 86_400_000


class DiagnosticStopError(RuntimeError):
    """Explicit fail-closed error carrying a stable STOP code."""

    def __init__(self, stop_code: str, detail: str = "") -> None:
        self.stop_code = stop_code
        self.detail = detail
        msg = f"STOP={stop_code}" if not detail else f"STOP={stop_code}: {detail}"
        super().__init__(msg)


def _iso_to_utc_ms(iso_utc: str) -> int:
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise DiagnosticStopError("source_manifest_mismatch", f"timestamp missing tzinfo: {iso_utc}")
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def _sign_bucket(val: float) -> int:
    if val > 0.0:
        return 1
    if val < 0.0:
        return -1
    return 0


def verify_base_and_safety_config() -> dict[str, Any]:
    """Verify safety invariants and Design-frozen Stage 1.3 constants from configs.base."""
    if (
        base.RISK_LIVE_TRADING_ENABLED is not False
        or RiskLimits().live_trading_enabled is not False
        or base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is not False
    ):
        raise DiagnosticStopError(
            "safety_config_mismatch",
            "live trading or local producer safety flag is not False",
        )

    expected_constants: tuple[tuple[str, Any], ...] = (
        ("EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_SYMBOLS", EXPECTED_SYMBOLS),
        ("EXTERNAL_SIGNAL_STAGE1_3_VOLUME_SPIKE_THRESHOLD", 3.0),
        ("EXTERNAL_SIGNAL_STAGE1_3_REL_STRENGTH_Z_THRESHOLD", 1.5),
        ("EXTERNAL_SIGNAL_STAGE1_3_ROLLING_DAYS", 7),
        ("EXTERNAL_SIGNAL_STAGE1_3_SAME_HOUR_MIN_SAMPLES", 5),
        ("EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES", 48),
        ("EXTERNAL_SIGNAL_STAGE1_3_SNAPSHOT_INTERVAL_MINUTES", 15),
        ("EXTERNAL_SIGNAL_STAGE1_3_ONE_HOUR_BAR_COUNT", 4),
        ("EXTERNAL_SIGNAL_STAGE1_3_FORWARD_4H_BAR_COUNT", 16),
        ("EXTERNAL_SIGNAL_STAGE1_3_CONFIGURED_DATA_LAG_MS", 60_000),
        ("EXTERNAL_SIGNAL_STAGE1_3_ENTRY_DELAY_BARS", 1),
        ("EXTERNAL_SIGNAL_STAGE1_3_COST_SCENARIOS_ROUND_TRIP_BPS", (30.0, 50.0, 80.0)),
    )
    for attr_name, expected_val in expected_constants:
        actual_val = getattr(base, attr_name, None)
        if actual_val != expected_val:
            raise DiagnosticStopError(
                "source_manifest_mismatch",
                f"configs.base.{attr_name}={actual_val!r} != expected {expected_val!r}",
            )

    return {
        "RISK_LIVE_TRADING_ENABLED": base.RISK_LIVE_TRADING_ENABLED,
        "risk_limits_live_trading_enabled": RiskLimits().live_trading_enabled,
        "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED": (
            base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED
        ),
        "symbols": base.EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_SYMBOLS,
        "volume_spike_threshold": base.EXTERNAL_SIGNAL_STAGE1_3_VOLUME_SPIKE_THRESHOLD,
        "rel_strength_z_threshold": base.EXTERNAL_SIGNAL_STAGE1_3_REL_STRENGTH_Z_THRESHOLD,
        "rolling_days": base.EXTERNAL_SIGNAL_STAGE1_3_ROLLING_DAYS,
        "same_hour_min_samples": base.EXTERNAL_SIGNAL_STAGE1_3_SAME_HOUR_MIN_SAMPLES,
        "rolling_std_min_samples": base.EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES,
        "snapshot_interval_minutes": base.EXTERNAL_SIGNAL_STAGE1_3_SNAPSHOT_INTERVAL_MINUTES,
        "one_hour_bar_count": base.EXTERNAL_SIGNAL_STAGE1_3_ONE_HOUR_BAR_COUNT,
        "forward_4h_bar_count": base.EXTERNAL_SIGNAL_STAGE1_3_FORWARD_4H_BAR_COUNT,
        "configured_data_lag_ms": base.EXTERNAL_SIGNAL_STAGE1_3_CONFIGURED_DATA_LAG_MS,
        "entry_delay_bars": base.EXTERNAL_SIGNAL_STAGE1_3_ENTRY_DELAY_BARS,
        "cost_scenarios_round_trip_bps": base.EXTERNAL_SIGNAL_STAGE1_3_COST_SCENARIOS_ROUND_TRIP_BPS,
    }


def build_default_protocol() -> dict[str, Any]:
    """Return the fixed Design protocol validated against configs.base."""
    cfg = verify_base_and_safety_config()
    warmup_start_ms = _iso_to_utc_ms(WARMUP_START_UTC)
    eval_start_ms = _iso_to_utc_ms(EVAL_START_UTC)
    eval_end_ms = _iso_to_utc_ms(EVAL_END_UTC)
    return {
        "symbols": list(cfg["symbols"]),
        "candidates": list(EXPECTED_CANDIDATES),
        "warmup_start_utc": WARMUP_START_UTC,
        "eval_start_utc": EVAL_START_UTC,
        "eval_end_utc": EVAL_END_UTC,
        "warmup_start_ms": warmup_start_ms,
        "eval_start_ms": eval_start_ms,
        "eval_end_ms": eval_end_ms,
        "block_count": BLOCK_COUNT,
        "block_days": BLOCK_DAYS,
        "first_half_block_count": FIRST_HALF_BLOCK_COUNT,
        "second_half_block_count": SECOND_HALF_BLOCK_COUNT,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bar_interval_ms": STAGE1_3_BAR_INTERVAL_MS,
        "one_hour_bar_count": cfg["one_hour_bar_count"],
        "forward_4h_bar_count": cfg["forward_4h_bar_count"],
        "configured_data_lag_ms": cfg["configured_data_lag_ms"],
        "entry_delay_bars": cfg["entry_delay_bars"],
        "rolling_days": cfg["rolling_days"],
        "same_hour_min_samples": cfg["same_hour_min_samples"],
        "rolling_std_min_samples": cfg["rolling_std_min_samples"],
        "volume_spike_threshold": cfg["volume_spike_threshold"],
        "rel_strength_z_threshold": cfg["rel_strength_z_threshold"],
        "cost_scenarios_round_trip_bps": list(cfg["cost_scenarios_round_trip_bps"]),
    }


def validate_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    """Validate that caller-supplied protocol matches the Design-frozen specification."""
    expected = build_default_protocol()
    if not isinstance(protocol, dict):
        raise DiagnosticStopError("source_manifest_mismatch", "protocol must be a dict")
    if set(protocol.keys()) != set(expected.keys()):
        raise DiagnosticStopError(
            "source_manifest_mismatch",
            f"protocol keys mismatch: extra={sorted(set(protocol) - set(expected))}, "
            f"missing={sorted(set(expected) - set(protocol))}",
        )
    for key, exp_val in expected.items():
        if protocol[key] != exp_val:
            raise DiagnosticStopError(
                "source_manifest_mismatch",
                f"protocol[{key!r}]={protocol[key]!r} != expected {exp_val!r}",
            )
    return expected


def _validate_and_index_bars(
    bars: list[HistoricalBar],
    protocol: dict[str, Any],
) -> tuple[dict[str, list[HistoricalBar]], dict[str, int]]:
    allowed_symbols = set(protocol["symbols"])
    interval_ms = int(protocol["bar_interval_ms"])
    warmup_start_ms = int(protocol["warmup_start_ms"])
    eval_end_ms = int(protocol["eval_end_ms"])
    expected_bar_count = (eval_end_ms - warmup_start_ms) // interval_ms

    for bar in bars:
        if not isinstance(bar, HistoricalBar):
            raise DiagnosticStopError("coverage_incomplete", "bars must contain HistoricalBar instances")
        if bar.symbol not in allowed_symbols:
            raise DiagnosticStopError("source_manifest_mismatch", f"unexpected symbol: {bar.symbol}")
        for field_name in ("open_price", "high_price", "low_price", "close_price", "quote_volume"):
            val = getattr(bar, field_name)
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise DiagnosticStopError("nonfinite_value", f"{bar.symbol} {field_name}={val!r}")
        if bar.bar_start_ms % interval_ms != 0:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"{bar.symbol} unaligned bar_start_ms={bar.bar_start_ms}",
            )

    duplicates = find_duplicate_bar_starts(bars)
    if duplicates:
        raise DiagnosticStopError("coverage_incomplete", f"duplicate bar_start_ms detected: {sorted(duplicates)}")

    grouped_raw = group_bars_by_symbol(bars)
    sliced: dict[str, list[HistoricalBar]] = {}
    excluded_outside_counts: dict[str, int] = {}

    for sym in protocol["symbols"]:
        sym_bars = grouped_raw.get(sym, [])
        in_range = [b for b in sym_bars if warmup_start_ms <= b.bar_start_ms < eval_end_ms]
        excluded_outside_counts[sym] = len(sym_bars) - len(in_range)
        if len(in_range) != expected_bar_count:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"{sym} has {len(in_range)} bars in [warmup, eval_end), expected {expected_bar_count}",
            )
        for idx, b in enumerate(in_range):
            expected_start = warmup_start_ms + idx * interval_ms
            if b.bar_start_ms != expected_start:
                raise DiagnosticStopError(
                    "coverage_incomplete",
                    f"{sym} missing/misaligned bar at index {idx}: got {b.bar_start_ms}, expected {expected_start}",
                )
        sliced[sym] = in_range

    return sliced, excluded_outside_counts


def _build_symbol_1h_features(
    s_bars: list[HistoricalBar],
    *,
    one_hour_bar_count: int,
    configured_data_lag_ms: int,
) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for idx, bar in enumerate(s_bars):
        window = build_one_hour_window(
            s_bars,
            end_index=idx,
            one_hour_bar_count=one_hour_bar_count,
        )
        if len(window) < one_hour_bar_count:
            features.append(
                {
                    "bar_index": idx,
                    "window_complete": False,
                    "window_start_ms": None,
                    "window_end_ms": bar.bar_end_ms,
                    "available_at_ms": historical_available_at_ms(
                        bar, configured_lag_ms=configured_data_lag_ms
                    ),
                    "utc_end_hour": (bar.bar_end_ms // MS_PER_HOUR) % 24,
                    "quote_volume_1h": None,
                    "r1h": None,
                }
            )
            continue
        qvol = one_hour_quote_volume(window)
        r1h = one_hour_return(window)
        features.append(
            {
                "bar_index": idx,
                "window_complete": r1h is not None,
                "window_start_ms": window[0].bar_start_ms,
                "window_end_ms": bar.bar_end_ms,
                "available_at_ms": historical_available_at_ms(
                    bar, configured_lag_ms=configured_data_lag_ms
                ),
                "utc_end_hour": (bar.bar_end_ms // MS_PER_HOUR) % 24,
                "quote_volume_1h": qvol,
                "r1h": r1h,
            }
        )
    return features


def build_event_ledger(
    bars: list[HistoricalBar],
    *,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    """Build causal, non-overlapping decision-point and admitted-event ledgers for both candidates."""
    proto = validate_protocol(protocol)
    grouped, excluded_outside_counts = _validate_and_index_bars(bars, proto)

    interval_ms = int(proto["bar_interval_ms"])
    one_hour_bar_count = int(proto["one_hour_bar_count"])
    forward_4h_bar_count = int(proto["forward_4h_bar_count"])
    lag_ms = int(proto["configured_data_lag_ms"])
    entry_delay_bars = int(proto["entry_delay_bars"])
    rolling_ms = int(proto["rolling_days"]) * MS_PER_DAY
    same_hour_min = int(proto["same_hour_min_samples"])
    rs_min = int(proto["rolling_std_min_samples"])
    vol_threshold = float(proto["volume_spike_threshold"])
    rs_threshold = float(proto["rel_strength_z_threshold"])
    eval_start_ms = int(proto["eval_start_ms"])
    eval_end_ms = int(proto["eval_end_ms"])
    block_ms = int(proto["block_days"]) * MS_PER_DAY

    # Precompute 1h features per symbol (including BTC for aligned RS calculation)
    features_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for sym in proto["symbols"]:
        features_by_symbol[sym] = _build_symbol_1h_features(
            grouped[sym],
            one_hour_bar_count=one_hour_bar_count,
            configured_data_lag_ms=lag_ms,
        )

    btc_r1h_by_end_ms: dict[int, float] = {
        feat["window_end_ms"]: feat["r1h"]
        for feat in features_by_symbol["BTCUSDT"]
        if feat["window_complete"] and feat["r1h"] is not None
    }

    def _locate_entry_and_exit(
        s_bars: list[HistoricalBar],
        bar_idx: int,
        available_at_ms: int,
    ) -> tuple[int | None, int | None, int | None]:
        # Pass small contiguous window starting at bar_idx to real select_entry_bar helper
        local_slice = s_bars[bar_idx : bar_idx + entry_delay_bars + 4]
        entry_bar = select_entry_bar(
            local_slice,
            event_time_ms=available_at_ms,
            entry_delay_bars=entry_delay_bars,
        )
        if entry_bar is None:
            return None, None, None
        entry_idx = bar_idx + (entry_bar.bar_start_ms - s_bars[bar_idx].bar_start_ms) // interval_ms
        if entry_idx < 0 or entry_idx + forward_4h_bar_count > len(s_bars):
            return entry_idx, entry_bar.bar_start_ms, None
        exit_bar_end_ms = s_bars[entry_idx + forward_4h_bar_count - 1].bar_end_ms
        return entry_idx, entry_bar.bar_start_ms, exit_bar_end_ms

    candidates_out: dict[str, dict[str, Any]] = {}

    for cand_name in proto["candidates"]:
        applicable_symbols = (
            list(proto["symbols"])
            if cand_name == "volume_spike_1h"
            else [s for s in proto["symbols"] if s != "BTCUSDT"]
        )
        decision_points: list[dict[str, Any]] = []
        admitted_events: list[dict[str, Any]] = []
        warmup_count = 0
        outside_eval_count = 0
        counts = {
            "total_eval_decision_points": 0,
            "feature_not_estimable": 0,
            "block_boundary_censored": 0,
            "not_triggered": 0,
            "overlap_suppressed": 0,
            "admitted": 0,
        }

        for sym in applicable_symbols:
            s_bars = grouped[sym]
            s_feats = features_by_symbol[sym]
            hour_history: dict[int, deque[tuple[int, float]]] = {h: deque() for h in range(24)}
            spread_history: deque[tuple[int, float]] = deque()
            active_exit_ms: int | None = None

            for feat in s_feats:
                idx = feat["bar_index"]
                t_ms = feat["window_end_ms"]
                avail_ms = feat["available_at_ms"]
                utc_end_hour = feat["utc_end_hour"]
                btc_r1h = btc_r1h_by_end_ms.get(t_ms)
                self_r1h = feat["r1h"]

                # Step A: read strictly prior causal history BEFORE updating history with current window
                if cand_name == "volume_spike_1h":
                    dq = hour_history[utc_end_hour]
                    while dq and t_ms - dq[0][0] > rolling_ms:
                        dq.popleft()
                    hist_count = len(dq)
                    hist_first_ms = dq[0][0] if dq else None
                    hist_last_ms = dq[-1][0] if dq else None
                    hist_vals = [v for _, v in dq] if feat["window_complete"] else []
                    feature_ok = (
                        feat["window_complete"]
                        and btc_r1h is not None
                        and hist_count >= same_hour_min
                        and median(hist_vals) > 0.0
                    )
                else:
                    while spread_history and t_ms - spread_history[0][0] > rolling_ms:
                        spread_history.popleft()
                    hist_count = len(spread_history)
                    hist_first_ms = spread_history[0][0] if spread_history else None
                    hist_last_ms = spread_history[-1][0] if spread_history else None
                    hist_vals = [v for _, v in spread_history] if feat["window_complete"] else []
                    # Exact mathematical equivalence for pstdev > 0 on finite floats: min < max
                    feature_ok = (
                        feat["window_complete"]
                        and btc_r1h is not None
                        and self_r1h is not None
                        and hist_count >= rs_min
                        and min(hist_vals) < max(hist_vals)
                    )

                # Separate warmup and outside-eval points from evaluation denominator
                if avail_ms < eval_start_ms:
                    warmup_count += 1
                elif avail_ms >= eval_end_ms:
                    outside_eval_count += 1
                else:
                    counts["total_eval_decision_points"] += 1
                    block_id = (avail_ms - eval_start_ms) // block_ms
                    block_end_ms = eval_start_ms + (block_id + 1) * block_ms
                    avail_utc_hour = (avail_ms // MS_PER_HOUR) % 24
                    is_occupied = active_exit_ms is not None and avail_ms <= active_exit_ms

                    point: dict[str, Any] = {
                        "candidate": cand_name,
                        "symbol": sym,
                        "bar_index": idx,
                        "window_start_ms": feat["window_start_ms"],
                        "window_end_ms": t_ms,
                        "available_at_ms": avail_ms,
                        "utc_end_hour": utc_end_hour,
                        "available_at_utc_hour": avail_utc_hour,
                        "block_id": block_id,
                        "self_r1h": self_r1h,
                        "btc_r1h": btc_r1h,
                        "self_r1h_sign": _sign_bucket(self_r1h) if self_r1h is not None else None,
                        "btc_r1h_sign": _sign_bucket(btc_r1h) if btc_r1h is not None else None,
                        "history_sample_count": hist_count,
                        "history_first_window_end_ms": hist_first_ms,
                        "history_last_window_end_ms": hist_last_ms,
                        "occupied_by_admitted_event": is_occupied,
                        "entry_index": None,
                        "entry_bar_start_ms": None,
                        "exit_bar_end_ms": None,
                        "entry_open_price": None,
                        "exit_close_price": None,
                        "trigger_value": None,
                        "y_gross_bps": None,
                        "mfe_4h_bps": None,
                        "mae_4h_bps": None,
                        "status": "",
                    }

                    # Filter order (Design §4.2):
                    # 1) Feature estimability -> 2) Predetermined boundary -> 3) Trigger -> 4) Occupation/Admission
                    if not feature_ok:
                        point["status"] = "feature_not_estimable"
                        counts["feature_not_estimable"] += 1
                    else:
                        entry_idx, entry_start_ms, exit_end_ms = _locate_entry_and_exit(
                            s_bars, idx, avail_ms
                        )
                        if (
                            entry_idx is None
                            or entry_start_ms is None
                            or exit_end_ms is None
                            or exit_end_ms > block_end_ms
                        ):
                            point["status"] = "block_boundary_censored"
                            counts["block_boundary_censored"] += 1
                        else:
                            point["entry_index"] = entry_idx
                            point["entry_bar_start_ms"] = entry_start_ms
                            point["exit_bar_end_ms"] = exit_end_ms

                            if cand_name == "volume_spike_1h":
                                detected = detect_volume_spike_1h(
                                    symbol=sym,
                                    current_1h_quote_volume=feat["quote_volume_1h"],
                                    same_hour_historical_volumes=hist_vals,
                                    event_time_ms=avail_ms,
                                    threshold=vol_threshold,
                                    min_samples=same_hour_min,
                                )
                            else:
                                detected = detect_relative_strength_vs_btc(
                                    symbol=sym,
                                    alt_1h_return=self_r1h,
                                    btc_1h_return=btc_r1h,
                                    historical_spread_returns=hist_vals,
                                    event_time_ms=avail_ms,
                                    z_threshold=rs_threshold,
                                    min_samples=rs_min,
                                )

                            if detected is None:
                                point["status"] = "not_triggered"
                                counts["not_triggered"] += 1
                            else:
                                point["trigger_value"] = (
                                    detected.metadata["volume_ratio"]
                                    if cand_name == "volume_spike_1h"
                                    else detected.metadata["z_score"]
                                )
                                if is_occupied:
                                    point["status"] = "overlap_suppressed"
                                    counts["overlap_suppressed"] += 1
                                else:
                                    fwd = compute_forward_metrics_from_entry_index(
                                        s_bars,
                                        entry_index=entry_idx,
                                        cost_round_trip_bps=0.0,
                                        signed_direction=1,
                                    )
                                    if fwd.get("status") != "success":
                                        raise DiagnosticStopError(
                                            "coverage_incomplete",
                                            f"forward metric failed for {sym} at entry_idx={entry_idx}",
                                        )
                                    point["status"] = "admitted"
                                    point["entry_open_price"] = fwd["entry_open_price"]
                                    point["exit_close_price"] = fwd["exit_close_price"]
                                    point["y_gross_bps"] = fwd["terminal_return_4h_net_bps"]
                                    point["mfe_4h_bps"] = fwd["mfe_4h_bps"]
                                    point["mae_4h_bps"] = fwd["mae_4h_bps"]
                                    active_exit_ms = exit_end_ms
                                    counts["admitted"] += 1
                                    admitted_events.append(point)

                    decision_points.append(point)

                # Step B: AFTER decision evaluation, append completed window to causal history
                if feat["window_complete"]:
                    if cand_name == "volume_spike_1h" and feat["quote_volume_1h"] is not None:
                        hour_history[utc_end_hour].append((t_ms, feat["quote_volume_1h"]))
                    elif (
                        cand_name == "relative_strength_vs_btc"
                        and self_r1h is not None
                        and btc_r1h is not None
                    ):
                        spread_history.append((t_ms, self_r1h - btc_r1h))

        candidates_out[cand_name] = {
            "candidate": cand_name,
            "applicable_symbols": applicable_symbols,
            "warmup_decision_point_count": warmup_count,
            "outside_eval_decision_point_count": outside_eval_count,
            "counts": counts,
            "decision_points": decision_points,
            "admitted_events": admitted_events,
        }

    return {
        "protocol": proto,
        "excluded_outside_study_range_bar_counts": excluded_outside_counts,
        "candidates": candidates_out,
    }


def linear_quantile(values: list[float], p: float) -> float | None:
    """Linear-interpolation quantile with h = (n - 1) * p; returns None on empty input."""
    if not values:
        return None
    if p < 0.0 or p > 1.0:
        raise ValueError(f"quantile p must be in [0, 1], got {p}")
    ordered = sorted(values)
    n = len(ordered)
    h = (n - 1) * p
    lo = math.floor(h)
    hi = math.ceil(h)
    if lo == hi:
        return float(ordered[lo])
    return float(ordered[lo] + (h - lo) * (ordered[hi] - ordered[lo]))


def positive_contribution(values: list[float]) -> dict[str, Any]:
    """Compute Top-1, Top-3, and Top-10% positive gross return concentration per Design §5.2."""
    n = len(values)
    pos = sorted((float(v) for v in values if v > 0.0), reverse=True)
    m = len(pos)
    if m == 0:
        return {
            "n": n,
            "positive_count": 0,
            "positive_total_bps": 0.0,
            "top_1_share": None,
            "top_3_share": None,
            "top_10pct_share": None,
        }
    total_pos = sum(pos)
    k10 = math.ceil(0.1 * n)
    return {
        "n": n,
        "positive_count": m,
        "positive_total_bps": total_pos,
        "top_1_share": sum(pos[: min(1, m)]) / total_pos,
        "top_3_share": sum(pos[: min(3, m)]) / total_pos,
        "top_10pct_share": sum(pos[: min(k10, m)]) / total_pos,
    }


def reduce_block_sample(
    block_stats: list[dict[str, Any]],
    drawn_blocks: list[int],
) -> dict[str, float | None]:
    """Reduce a resampled block index list to (mu_gross_bps, delta_bps) from raw numerators/denominators."""
    sum_y = 0.0
    n = 0
    sum_d = 0.0
    m = 0
    for b in drawn_blocks:
        bs = block_stats[b]
        sum_y += float(bs["sum_y"])
        n += int(bs["n"])
        sum_d += float(bs["sum_d"])
        m += int(bs["m"])
    return {
        "mu_gross_bps": (sum_y / n) if n > 0 else None,
        "delta_bps": (sum_d / m) if m > 0 else None,
    }


def classify_result(metrics: dict[str, Any]) -> dict[str, str]:
    """Apply Design §8 top-down first-matching routing rule."""
    alpha_status = "evidence_insufficient"
    mu_gross = metrics["mu_gross_bps"]
    delta = metrics["delta_bps"]
    unmatched = int(metrics["unmatched_count"])

    if (
        not metrics["prerequisites_valid"]
        or mu_gross is None
        or delta is None
    ):
        return {
            "observation_label": "not_estimable",
            "resource_decision": "stop_due_to_evidence_or_cost",
            "alpha_research_status": alpha_status,
        }

    if unmatched > 0:
        return {
            "observation_label": "inconclusive_or_concentrated",
            "resource_decision": "pause_for_new_evidence",
            "alpha_research_status": alpha_status,
        }

    if delta <= 0.0:
        return {
            "observation_label": "no_increment_observed",
            "resource_decision": "stop_fixed_candidate_this_round",
            "alpha_research_status": alpha_status,
        }

    if mu_gross <= 0.0:
        return {
            "observation_label": "relative_increment_without_positive_gross",
            "resource_decision": "stop_fixed_candidate_this_round",
            "alpha_research_status": alpha_status,
        }

    # Both mu_gross > 0 and delta > 0 with full matching; verify full stability conditions
    mu_ci_low = metrics["mu_ci_low"]
    delta_ci_low = metrics["delta_ci_low"]
    first_half_mu = metrics["first_half_mu"]
    first_half_delta = metrics["first_half_delta"]
    second_half_mu = metrics["second_half_mu"]
    second_half_delta = metrics["second_half_delta"]
    without_best_mu = metrics["without_best_mu"]
    without_best_delta = metrics["without_best_delta"]

    full_positive_ok = (
        bool(metrics["mu_ci_complete"])
        and bool(metrics["delta_ci_complete"])
        and mu_ci_low is not None
        and mu_ci_low > 0.0
        and delta_ci_low is not None
        and delta_ci_low > 0.0
        and first_half_mu is not None
        and first_half_mu > 0.0
        and first_half_delta is not None
        and first_half_delta > 0.0
        and second_half_mu is not None
        and second_half_mu > 0.0
        and second_half_delta is not None
        and second_half_delta > 0.0
        and bool(metrics["leave_one_symbol_all_positive"])
        and bool(metrics["leave_one_block_all_positive"])
        and without_best_mu is not None
        and without_best_mu > 0.0
        and without_best_delta is not None
        and without_best_delta > 0.0
        and not bool(metrics["has_unexplained_dependency_or_data_issue"])
    )
    if full_positive_ok:
        return {
            "observation_label": "bounded_positive_pattern",
            "resource_decision": "consider_independent_validation_only",
            "alpha_research_status": alpha_status,
        }
    return {
        "observation_label": "inconclusive_or_concentrated",
        "resource_decision": "pause_for_new_evidence",
        "alpha_research_status": alpha_status,
    }


def _summarize_return_distribution(
    events: list[dict[str, Any]],
    *,
    cost_bps: float,
    delta_bps: float | None,
    applicable_symbols: list[str],
) -> dict[str, Any]:
    values = [float(e["y_gross_bps"]) - cost_bps for e in events]
    n = len(values)
    if n == 0:
        return {
            "cost_round_trip_bps": cost_bps,
            "n": 0,
            "mean_bps": None,
            "median_bps": None,
            "delta_bps": delta_bps,
            "win_rate": None,
            "avg_win_bps": None,
            "avg_loss_bps": None,
            "payoff_ratio": None,
            "quantiles_bps": {
                "p05": None,
                "p10": None,
                "p25": None,
                "p50": None,
                "p75": None,
                "p90": None,
            },
            "worst_event_bps": None,
            "max_consecutive_losses_by_symbol": {sym: 0 for sym in applicable_symbols},
        }
    wins = [v for v in values if v > 0.0]
    losses = [v for v in values if v < 0.0]
    avg_win = (sum(wins) / len(wins)) if wins else None
    avg_loss = (sum(losses) / len(losses)) if losses else None
    payoff = (
        (avg_win / abs(avg_loss))
        if (avg_win is not None and avg_loss is not None and avg_loss < 0.0)
        else None
    )

    max_consec_by_sym: dict[str, int] = {}
    for sym in applicable_symbols:
        sym_evs = sorted(
            (e for e in events if e["symbol"] == sym),
            key=lambda item: item["available_at_ms"],
        )
        best_streak = 0
        cur_streak = 0
        for e in sym_evs:
            if float(e["y_gross_bps"]) - cost_bps < 0.0:
                cur_streak += 1
                if cur_streak > best_streak:
                    best_streak = cur_streak
            else:
                cur_streak = 0
        max_consec_by_sym[sym] = best_streak

    return {
        "cost_round_trip_bps": cost_bps,
        "n": n,
        "mean_bps": sum(values) / n,
        "median_bps": linear_quantile(values, 0.50),
        "delta_bps": delta_bps,
        "win_rate": len(wins) / n,
        "avg_win_bps": avg_win,
        "avg_loss_bps": avg_loss,
        "payoff_ratio": payoff,
        "quantiles_bps": {
            "p05": linear_quantile(values, 0.05),
            "p10": linear_quantile(values, 0.10),
            "p25": linear_quantile(values, 0.25),
            "p50": linear_quantile(values, 0.50),
            "p75": linear_quantile(values, 0.75),
            "p90": linear_quantile(values, 0.90),
        },
        "worst_event_bps": min(values),
        "max_consecutive_losses_by_symbol": max_consec_by_sym,
    }


def _summarize_subset_stats(events: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(events)
    sum_y = sum(float(e["y_gross_bps"]) for e in events)
    matched = [e for e in events if e["d_bps"] is not None]
    m = len(matched)
    sum_d = sum(float(e["d_bps"]) for e in matched)
    return {
        "admitted_count": n,
        "matched_count": m,
        "unmatched_count": n - m,
        "sum_y_bps": sum_y,
        "mu_gross_bps": (sum_y / n) if n > 0 else None,
        "sum_d_bps": sum_d,
        "delta_bps": (sum_d / m) if m > 0 else None,
    }


def analyze_bars(
    bars: list[HistoricalBar],
    *,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    """Run full deterministic control matching, joint 23-block bootstrap, diagnostics, and §8 routing."""
    proto = validate_protocol(protocol)
    grouped, _ = _validate_and_index_bars(bars, proto)
    ledger = build_event_ledger(bars, protocol=proto)

    block_count = int(proto["block_count"])
    first_half_n = int(proto["first_half_block_count"])
    bootstrap_replicates = int(proto["bootstrap_replicates"])
    bootstrap_seed = int(proto["bootstrap_seed"])
    cost_scenarios = [float(c) for c in proto["cost_scenarios_round_trip_bps"]]

    # Cache control forward metrics by (symbol, entry_index) using real Stage 1.3 helper
    fwd_cache: dict[tuple[str, int], dict[str, Any]] = {}

    def _get_forward_metrics(sym: str, entry_index: int) -> dict[str, Any]:
        key = (sym, entry_index)
        if key not in fwd_cache:
            fwd = compute_forward_metrics_from_entry_index(
                grouped[sym],
                entry_index=entry_index,
                cost_round_trip_bps=0.0,
                signed_direction=1,
            )
            if fwd.get("status") != "success":
                raise DiagnosticStopError(
                    "coverage_incomplete",
                    f"control forward metric failed for {sym} entry_index={entry_index}",
                )
            fwd_cache[key] = fwd
        return fwd_cache[key]

    # Step 1: Match deterministic controls per candidate and prepare block summaries for joint bootstrap
    event_records_by_cand: dict[str, list[dict[str, Any]]] = {}
    block_stats_by_cand: dict[str, list[dict[str, Any]]] = {}
    control_reuse_by_cand: dict[str, dict[str, Any]] = {}

    for cand_name in proto["candidates"]:
        cand_data = ledger["candidates"][cand_name]
        # Index eligible control points: not_triggered & not occupied_by_admitted_event
        controls_by_key: dict[tuple[str, int, int, int, int], list[dict[str, Any]]] = {}
        for pt in cand_data["decision_points"]:
            if pt["status"] == "not_triggered" and not pt["occupied_by_admitted_event"]:
                match_key = (
                    pt["symbol"],
                    pt["block_id"],
                    pt["available_at_utc_hour"],
                    pt["self_r1h_sign"],
                    pt["btc_r1h_sign"],
                )
                if match_key not in controls_by_key:
                    controls_by_key[match_key] = []
                controls_by_key[match_key].append(pt)

        control_use_counter: Counter[tuple[str, str, int]] = Counter()
        event_records: list[dict[str, Any]] = []
        matched_count = 0
        unmatched_count = 0

        for ev in cand_data["admitted_events"]:
            match_key = (
                ev["symbol"],
                ev["block_id"],
                ev["available_at_utc_hour"],
                ev["self_r1h_sign"],
                ev["btc_r1h_sign"],
            )
            ctrl_pts = controls_by_key.get(match_key, [])
            ctrl_keys: list[list[Any]] = []
            ctrl_ys: list[float] = []
            for cp in ctrl_pts:
                ck = (cand_name, cp["symbol"], cp["available_at_ms"])
                control_use_counter[ck] += 1
                ctrl_keys.append([cand_name, cp["symbol"], cp["available_at_ms"]])
                fwd = _get_forward_metrics(cp["symbol"], cp["entry_index"])
                ctrl_ys.append(float(fwd["terminal_return_4h_net_bps"]))

            rec = dict(ev)
            rec["control_keys"] = ctrl_keys
            rec["control_count"] = len(ctrl_ys)
            if ctrl_ys:
                ctrl_mean = sum(ctrl_ys) / len(ctrl_ys)
                rec["control_mean_bps"] = ctrl_mean
                rec["d_bps"] = float(ev["y_gross_bps"]) - ctrl_mean
                rec["match_status"] = "matched"
                matched_count += 1
            else:
                rec["control_mean_bps"] = None
                rec["d_bps"] = None
                rec["match_status"] = "unmatched_control"
                unmatched_count += 1
            event_records.append(rec)

        event_records_by_cand[cand_name] = event_records
        control_reuse_by_cand[cand_name] = {
            "total_control_references": sum(control_use_counter.values()),
            "unique_controls_used": len(control_use_counter),
            "reused_control_count": sum(1 for c in control_use_counter.values() if c > 1),
            "max_control_reuse_count": max(control_use_counter.values(), default=0),
            "matched_events": matched_count,
            "unmatched_events": unmatched_count,
        }

        b_stats: list[dict[str, Any]] = []
        for b_id in range(block_count):
            b_evs = [e for e in event_records if e["block_id"] == b_id]
            b_matched = [e for e in b_evs if e["d_bps"] is not None]
            b_stats.append(
                {
                    "block_id": b_id,
                    "sum_y": sum(float(e["y_gross_bps"]) for e in b_evs),
                    "n": len(b_evs),
                    "sum_d": sum(float(e["d_bps"]) for e in b_matched),
                    "m": len(b_matched),
                }
            )
        block_stats_by_cand[cand_name] = b_stats

    # Step 2: Joint 23-block bootstrap shared across ALL symbols and BOTH candidates
    rng = random.Random(bootstrap_seed)
    boot_mu_draws: dict[str, list[float]] = {c: [] for c in proto["candidates"]}
    boot_delta_draws: dict[str, list[float]] = {c: [] for c in proto["candidates"]}
    boot_empty_mu: dict[str, int] = {c: 0 for c in proto["candidates"]}
    boot_empty_delta: dict[str, int] = {c: 0 for c in proto["candidates"]}

    block_indices = list(range(block_count))
    for _ in range(bootstrap_replicates):
        drawn = rng.choices(block_indices, k=block_count)
        for cand_name in proto["candidates"]:
            red = reduce_block_sample(block_stats_by_cand[cand_name], drawn)
            if red["mu_gross_bps"] is None:
                boot_empty_mu[cand_name] += 1
            else:
                boot_mu_draws[cand_name].append(red["mu_gross_bps"])
            if red["delta_bps"] is None:
                boot_empty_delta[cand_name] += 1
            else:
                boot_delta_draws[cand_name].append(red["delta_bps"])

    # Step 3: Assemble summaries, diagnostics, and Design §8 routing per candidate
    candidates_result: dict[str, Any] = {}
    for cand_name in proto["candidates"]:
        cand_data = ledger["candidates"][cand_name]
        applicable_symbols = cand_data["applicable_symbols"]
        evs = event_records_by_cand[cand_name]
        b_stats = block_stats_by_cand[cand_name]
        reuse_info = control_reuse_by_cand[cand_name]

        overall = _summarize_subset_stats(evs)
        mu_gross = overall["mu_gross_bps"]
        delta = overall["delta_bps"]

        # Counts with exact conservation
        base_counts = dict(cand_data["counts"])
        counts = {
            **base_counts,
            "triggered": base_counts["overlap_suppressed"] + base_counts["admitted"],
            "matched": reuse_info["matched_events"],
            "unmatched": reuse_info["unmatched_events"],
        }

        # Cost scenarios (gross + 30/50/80 bps)
        gross_dist = _summarize_return_distribution(
            evs,
            cost_bps=0.0,
            delta_bps=delta,
            applicable_symbols=applicable_symbols,
        )
        cost_scenario_dists: dict[str, Any] = {}
        for c_bps in cost_scenarios:
            cost_scenario_dists[f"{c_bps:.1f}"] = _summarize_return_distribution(
                evs,
                cost_bps=c_bps,
                delta_bps=delta,
                applicable_symbols=applicable_symbols,
            )

        # MAE / MFE path summaries (gross reference prices only, non-executable)
        mfe_vals = [float(e["mfe_4h_bps"]) for e in evs]
        mae_vals = [float(e["mae_4h_bps"]) for e in evs]
        path_summary = {
            "mfe_4h_gross_bps": {
                "mean": (sum(mfe_vals) / len(mfe_vals)) if mfe_vals else None,
                "p50": linear_quantile(mfe_vals, 0.50),
                "p90": linear_quantile(mfe_vals, 0.90),
                "max": max(mfe_vals) if mfe_vals else None,
            },
            "mae_4h_gross_bps": {
                "mean": (sum(mae_vals) / len(mae_vals)) if mae_vals else None,
                "p10": linear_quantile(mae_vals, 0.10),
                "p50": linear_quantile(mae_vals, 0.50),
                "min": min(mae_vals) if mae_vals else None,
            },
            "bar_internal_ordering_known": False,
            "executable_stop_claim_allowed": False,
        }

        # Bootstrap nominal CIs
        mu_draws = boot_mu_draws[cand_name]
        delta_draws = boot_delta_draws[cand_name]
        mu_ci_low = linear_quantile(mu_draws, 0.025)
        mu_ci_high = linear_quantile(mu_draws, 0.975)
        delta_ci_low = linear_quantile(delta_draws, 0.025)
        delta_ci_high = linear_quantile(delta_draws, 0.975)
        mu_ci_complete = boot_empty_mu[cand_name] == 0 and len(mu_draws) == bootstrap_replicates
        delta_ci_complete = boot_empty_delta[cand_name] == 0 and len(delta_draws) == bootstrap_replicates

        bootstrap_summary = {
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "block_count": block_count,
            "mu_gross_bps": {
                "valid_replicates": len(mu_draws),
                "empty_replicates": boot_empty_mu[cand_name],
                "ci_complete": mu_ci_complete,
                "ci_025": mu_ci_low,
                "ci_975": mu_ci_high,
            },
            "delta_bps": {
                "valid_replicates": len(delta_draws),
                "empty_replicates": boot_empty_delta[cand_name],
                "ci_complete": delta_ci_complete,
                "ci_025": delta_ci_low,
                "ci_975": delta_ci_high,
            },
        }

        # Fixed diagnostics: halves, per-symbol, per-block, leave-one-out, without-best, Top-K
        first_half = _summarize_subset_stats([e for e in evs if e["block_id"] < first_half_n])
        second_half = _summarize_subset_stats([e for e in evs if e["block_id"] >= first_half_n])

        per_symbol = {
            sym: _summarize_subset_stats([e for e in evs if e["symbol"] == sym])
            for sym in applicable_symbols
        }
        per_block = [
            {
                "block_id": bs["block_id"],
                "admitted_count": bs["n"],
                "matched_count": bs["m"],
                "unmatched_count": bs["n"] - bs["m"],
                "sum_y_bps": bs["sum_y"],
                "mu_gross_bps": (bs["sum_y"] / bs["n"]) if bs["n"] > 0 else None,
                "sum_d_bps": bs["sum_d"],
                "delta_bps": (bs["sum_d"] / bs["m"]) if bs["m"] > 0 else None,
            }
            for bs in b_stats
        ]
        leave_one_symbol_out = {
            sym: _summarize_subset_stats([e for e in evs if e["symbol"] != sym])
            for sym in applicable_symbols
        }
        leave_one_block_out = {
            str(b_id): _summarize_subset_stats([e for e in evs if e["block_id"] != b_id])
            for b_id in range(block_count)
        }

        if evs:
            best_idx = max(
                range(len(evs)),
                key=lambda i: (float(evs[i]["y_gross_bps"]), -evs[i]["available_at_ms"]),
            )
            without_best = _summarize_subset_stats([e for i, e in enumerate(evs) if i != best_idx])
        else:
            without_best = _summarize_subset_stats([])

        pos_contrib = positive_contribution([float(e["y_gross_bps"]) for e in evs])

        loso_all_pos = bool(leave_one_symbol_out) and all(
            v["mu_gross_bps"] is not None
            and v["mu_gross_bps"] > 0.0
            and v["delta_bps"] is not None
            and v["delta_bps"] > 0.0
            for v in leave_one_symbol_out.values()
        )
        lobo_all_pos = bool(leave_one_block_out) and all(
            v["mu_gross_bps"] is not None
            and v["mu_gross_bps"] > 0.0
            and v["delta_bps"] is not None
            and v["delta_bps"] > 0.0
            for v in leave_one_block_out.values()
        )

        routing = classify_result(
            {
                "prerequisites_valid": True,
                "mu_gross_bps": mu_gross,
                "delta_bps": delta,
                "admitted_count": counts["admitted"],
                "matched_count": counts["matched"],
                "unmatched_count": counts["unmatched"],
                "mu_ci_low": mu_ci_low,
                "delta_ci_low": delta_ci_low,
                "mu_ci_complete": mu_ci_complete,
                "delta_ci_complete": delta_ci_complete,
                "first_half_mu": first_half["mu_gross_bps"],
                "first_half_delta": first_half["delta_bps"],
                "second_half_mu": second_half["mu_gross_bps"],
                "second_half_delta": second_half["delta_bps"],
                "leave_one_symbol_all_positive": loso_all_pos,
                "leave_one_block_all_positive": lobo_all_pos,
                "without_best_mu": without_best["mu_gross_bps"],
                "without_best_delta": without_best["delta_bps"],
                "has_unexplained_dependency_or_data_issue": False,
            }
        )

        candidates_result[cand_name] = {
            "candidate": cand_name,
            "applicable_symbols": applicable_symbols,
            "event_records": evs,
            "decision_points": cand_data["decision_points"],
            "summary": {
                "candidate": cand_name,
                "applicable_symbols": applicable_symbols,
                "warmup_decision_point_count": cand_data["warmup_decision_point_count"],
                "outside_eval_decision_point_count": cand_data["outside_eval_decision_point_count"],
                "counts": counts,
                "mu_gross_bps": mu_gross,
                "delta_bps": delta,
                "c_break_even_bps": mu_gross,
                "minimum_economically_meaningful_gain": None,
                "cost_mode": "cost_context_only",
                "gross_distribution": gross_dist,
                "cost_scenarios": cost_scenario_dists,
                "path_summary": path_summary,
                "control_reuse_summary": reuse_info,
                "bootstrap": bootstrap_summary,
                "positive_contribution": pos_contrib,
                "diagnostics": {
                    "first_half_blocks_0_10": first_half,
                    "second_half_blocks_11_22": second_half,
                    "per_symbol": per_symbol,
                    "per_block": per_block,
                    "leave_one_symbol_out": leave_one_symbol_out,
                    "leave_one_block_out": leave_one_block_out,
                    "without_best_event": without_best,
                },
                "routing": routing,
            },
        }

    return {
        "protocol": proto,
        "governance": {
            "exploratory_only": True,
            "independent_out_of_sample_claim_allowed": False,
            "full_market_alpha_claim_allowed": False,
            "r10_readmission_claim_allowed": False,
            "cost_mode": "cost_context_only",
            "minimum_economically_meaningful_gain": None,
            "live_trading_enabled": False,
            "paper_trading_allowed": False,
            "execution_engine_allowed": False,
            "execution_feasibility_claim_allowed": False,
            "portfolio_pnl_reported": False,
        },
        "excluded_outside_study_range_bar_counts": ledger["excluded_outside_study_range_bar_counts"],
        "candidates": candidates_result,
    }


US_15M = STAGE1_3_BAR_INTERVAL_MS * 1000
MONTHLY_ARCHIVE_PERIODS: tuple[str, ...] = (
    "2026-06",
    "2026-07",
    "2026-08",
    "2026-09",
    "2026-10",
)
DAILY_ARCHIVE_START_DATE = date(2026, 11, 1)
DAILY_ARCHIVE_END_DATE = date(2026, 11, 22)
BINANCE_VISION_SPOT_BASE = "https://data.binance.vision/data/spot"


def _calendar_dates_in_month(ym: str) -> list[str]:
    year_s, month_s = ym.split("-")
    cur = date(int(year_s), int(month_s), 1)
    out: list[str] = []
    while cur.month == int(month_s):
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def build_expected_archive_objects(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the fixed 135 archive objects (5 symbols x [5 monthly + 22 daily]) for the study."""
    proto = validate_protocol(protocol)
    objects: list[dict[str, Any]] = []
    for sym in proto["symbols"]:
        for ym in MONTHLY_ARCHIVE_PERIODS:
            zip_name = f"{sym}-15m-{ym}.zip"
            csv_name = f"{sym}-15m-{ym}.csv"
            zip_url = f"{BINANCE_VISION_SPOT_BASE}/monthly/klines/{sym}/15m/{zip_name}"
            objects.append(
                {
                    "object_id": f"{sym}:monthly:{ym}",
                    "symbol": sym,
                    "granularity": "monthly",
                    "period": ym,
                    "zip_filename": zip_name,
                    "checksum_filename": f"{zip_name}.CHECKSUM",
                    "csv_filename": csv_name,
                    "zip_url": zip_url,
                    "checksum_url": f"{zip_url}.CHECKSUM",
                    "expected_utc_dates": _calendar_dates_in_month(ym),
                }
            )
        cur = DAILY_ARCHIVE_START_DATE
        while cur <= DAILY_ARCHIVE_END_DATE:
            d_iso = cur.isoformat()
            zip_name = f"{sym}-15m-{d_iso}.zip"
            csv_name = f"{sym}-15m-{d_iso}.csv"
            zip_url = f"{BINANCE_VISION_SPOT_BASE}/daily/klines/{sym}/15m/{zip_name}"
            objects.append(
                {
                    "object_id": f"{sym}:daily:{d_iso}",
                    "symbol": sym,
                    "granularity": "daily",
                    "period": d_iso,
                    "zip_filename": zip_name,
                    "checksum_filename": f"{zip_name}.CHECKSUM",
                    "csv_filename": csv_name,
                    "zip_url": zip_url,
                    "checksum_url": f"{zip_url}.CHECKSUM",
                    "expected_utc_dates": [d_iso],
                }
            )
            cur += timedelta(days=1)
    return objects


def parse_kline_zip_bytes(
    zip_bytes: bytes,
    *,
    checksum_text: str,
    expected_zip_filename: str,
    expected_csv_filename: str,
    expected_symbol: str,
    expected_utc_dates: list[str],
) -> tuple[list[HistoricalBar], dict[str, Any]]:
    """Verify CHECKSUM filename+SHA-256 and parse 12-col microsecond 15m CSV into canonical HistoricalBars."""
    stripped = checksum_text.strip()
    parts = stripped.split()
    if len(parts) < 2:
        raise DiagnosticStopError("checksum_mismatch", f"malformed CHECKSUM text for {expected_zip_filename}")
    expected_sha = parts[0].lower()
    target_filename = parts[1].lstrip("*")
    if target_filename != expected_zip_filename:
        raise DiagnosticStopError(
            "checksum_mismatch",
            f"CHECKSUM target filename {target_filename!r} != expected {expected_zip_filename!r}",
        )
    actual_sha = hashlib.sha256(zip_bytes).hexdigest().lower()
    if actual_sha != expected_sha:
        raise DiagnosticStopError(
            "checksum_mismatch",
            f"ZIP SHA-256 {actual_sha} != CHECKSUM {expected_sha} for {expected_zip_filename}",
        )

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes), "r")
    except zipfile.BadZipFile as exc:
        raise DiagnosticStopError("coverage_incomplete", f"corrupt zip {expected_zip_filename}: {exc}") from exc

    with zf:
        members = zf.namelist()
        if members != [expected_csv_filename]:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"unexpected zip members {members!r}, expected {[expected_csv_filename]!r}",
            )
        with zf.open(expected_csv_filename, "r") as raw_fh:
            text_fh = io.TextIOWrapper(raw_fh, encoding="utf-8", newline="")
            rows = [r for r in csv.reader(text_fh) if r]

    expected_starts_ms: list[int] = []
    for d_iso in expected_utc_dates:
        y_s, m_s, d_s = d_iso.split("-")
        day_start = int(datetime(int(y_s), int(m_s), int(d_s), tzinfo=timezone.utc).timestamp() * 1000)
        for slot in range(96):
            expected_starts_ms.append(day_start + slot * STAGE1_3_BAR_INTERVAL_MS)

    bars: list[HistoricalBar] = []
    seen_starts: set[int] = set()
    zero_vol_count = 0

    for row_idx, row in enumerate(rows):
        if len(row) != 12:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"{expected_csv_filename} row {row_idx} has {len(row)} columns, expected 12",
            )
        open_str = row[0].strip()
        close_str = row[6].strip()
        if not (open_str.isdigit() and close_str.isdigit()):
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"{expected_csv_filename} row {row_idx} non-integer timestamp",
            )
        if len(open_str) != 16 or len(close_str) != 16:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"{expected_csv_filename} row {row_idx} timestamp not 16-digit microseconds: {open_str}",
            )
        open_us = int(open_str)
        close_us = int(close_str)
        if open_us % US_15M != 0 or close_us != open_us + US_15M - 1:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"{expected_csv_filename} row {row_idx} invalid 15m microsecond boundaries: {open_us}..{close_us}",
            )
        bar_start_ms = open_us // 1000
        bar_end_ms = bar_start_ms + STAGE1_3_BAR_INTERVAL_MS
        if bar_start_ms in seen_starts:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"{expected_csv_filename} duplicate bar_start_ms={bar_start_ms}",
            )
        seen_starts.add(bar_start_ms)

        try:
            open_p = float(row[1])
            high_p = float(row[2])
            low_p = float(row[3])
            close_p = float(row[4])
            quote_vol = float(row[7])
        except ValueError as exc:
            raise DiagnosticStopError(
                "nonfinite_value",
                f"{expected_csv_filename} row {row_idx} unparseable numeric field: {exc}",
            ) from exc

        for fname, fval in (
            ("open_price", open_p),
            ("high_price", high_p),
            ("low_price", low_p),
            ("close_price", close_p),
            ("quote_volume", quote_vol),
        ):
            if not math.isfinite(fval):
                raise DiagnosticStopError(
                    "nonfinite_value",
                    f"{expected_csv_filename} row {row_idx} non-finite {fname}={fval!r}",
                )
        if quote_vol == 0.0:
            zero_vol_count += 1

        try:
            bar = HistoricalBar(
                symbol=expected_symbol,
                bar_start_ms=bar_start_ms,
                bar_end_ms=bar_end_ms,
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                close_price=close_p,
                quote_volume=quote_vol,
            )
        except ValueError as exc:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"{expected_csv_filename} row {row_idx} invalid HistoricalBar: {exc}",
            ) from exc
        bars.append(bar)

    actual_starts_ms = [b.bar_start_ms for b in bars]
    if actual_starts_ms != expected_starts_ms:
        raise DiagnosticStopError(
            "coverage_incomplete",
            f"{expected_csv_filename} bar start grid mismatch: got {len(actual_starts_ms)} bars, "
            f"expected {len(expected_starts_ms)} exact ascending 15m bars",
        )

    meta = {
        "zip_filename": expected_zip_filename,
        "csv_filename": expected_csv_filename,
        "zip_sha256": actual_sha,
        "zip_bytes": len(zip_bytes),
        "row_count": len(bars),
        "first_bar_start_ms": bars[0].bar_start_ms if bars else None,
        "last_bar_end_ms": bars[-1].bar_end_ms if bars else None,
        "zero_quote_volume_bar_count": zero_vol_count,
    }
    return bars, meta
