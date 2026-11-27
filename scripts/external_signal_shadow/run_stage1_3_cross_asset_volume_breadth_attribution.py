#!/usr/bin/env python3
"""Stage 1.3 cross-asset volume breadth and Block-9 contribution attribution CLI."""
from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import research.external_signal_shadow.stage1_3_fixed_universe_diagnostic as diag_mod
import scripts.external_signal_shadow.run_stage1_3_volume_strength_conditional_increment as old_cli_mod
from research.external_signal_shadow.stage1_3_fixed_universe_diagnostic import (
    DiagnosticStopError,
    build_default_protocol,
    linear_quantile,
    validate_protocol,
    verify_base_and_safety_config,
)
from scripts.external_signal_shadow.run_stage1_3_volume_strength_conditional_increment import (
    _reject_symlink_chain,
    _stream_sha256,
)

CAND_A = "volume_spike_1h"
CAND_B = "relative_strength_vs_btc"
ALLOWED_CANDIDATES = frozenset({CAND_A, CAND_B})
ALLOWED_ROW_STATUSES = frozenset(
    {
        "feature_not_estimable",
        "block_boundary_censored",
        "not_triggered",
        "overlap_suppressed",
        "admitted",
    }
)
ALLOWED_ERROR_CAUSES = frozenset(
    {
        "path_mismatch",
        "hash_mismatch",
        "reference_mismatch",
        "protocol_mismatch",
        "cohort_mismatch",
        "time_or_price_mismatch",
        "nonfinite_value",
        "duplicate_key",
        "input_changed_during_run",
        "output_not_new",
        "code_or_authority_mismatch",
    }
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_REL_PATH = "docs/designs/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution-design_CN.md"
EXPECTED_DESIGN_SHA256 = "327641761e2b6c625e873c1c2592418a2b43c640935eed78507b9e36617e30fa"
PLAN_REL_PATH = "docs/plans/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution-implementation-plan_CN.md"

PRIOR_1125_DESIGN_REL_PATH = "docs/designs/2026-11-25-stage1-3-volume-strength-conditional-increment-design_CN.md"
PRIOR_1125_DESIGN_SHA256 = "a7680d7984c9eba95c12cdda152a989e42d1df25a125bd6d7e2657de20458797"
PRIOR_1125_PLAN_REL_PATH = (
    "docs/plans/2026-11-25-stage1-3-volume-strength-conditional-increment-implementation-plan_CN.md"
)
PRIOR_1125_PLAN_SHA256 = "751dcc7b4ec9b9de4b788ffe648f8166253568fb59e2f450ffe8c06e3fc28a5d"

PRIOR_1124_DESIGN_REL_PATH = "docs/designs/2026-11-23-stage1-3-fixed-universe-mean-return-diagnostic-design_CN.md"
PRIOR_1124_DESIGN_SHA256 = "8622d06b75c17a7bdfd103224cb11b75d147a7b92b1f3a06be6b81cd4417bd23"
PRIOR_1124_PLAN_REL_PATH = (
    "docs/plans/2026-11-24-stage1-3-fixed-universe-mean-return-diagnostic-implementation-plan_CN.md"
)
PRIOR_1124_PLAN_SHA256 = "bf066b19f0bd43c2378bf6c34553dd10f7c9747ea070815627818c05db8e1e3a"

OLD_CLI_REL_PATH = "scripts/external_signal_shadow/run_stage1_3_volume_strength_conditional_increment.py"
EXPECTED_OLD_CLI_SHA256 = "f4c570faf674a4bdeea9397b193fd62d7e8d103059209bf7f81f78a82d3b30e2"
CORE_REL_PATH = "src/research/external_signal_shadow/stage1_3_fixed_universe_diagnostic.py"
EXPECTED_CORE_SHA256 = "e233a8af052c92b5746e5456c93cbde3a13056172d5151b4e2fab530146e04ee"

CODE_BINDING_SPECS: tuple[tuple[str, str], ...] = (
    ("scripts/external_signal_shadow/run_stage1_3_cross_asset_volume_breadth_attribution.py", "new_cli"),
    ("tests/scripts/external_signal_shadow/test_run_stage1_3_cross_asset_volume_breadth_attribution.py", "new_test"),
    (OLD_CLI_REL_PATH, "reused_prior_cli_helper"),
    (CORE_REL_PATH, "reused_diagnostic_helper"),
    ("configs/base.py", "reused_config"),
    ("src/risk/limits.py", "reused_safety"),
)

EXPECTED_R_ROOT = Path(
    "/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-25-stage1-3-volume-strength-conditional-increment/20261125T124130Z"
)
EXPECTED_U_ROOT = Path(
    "/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-24-stage1-3-fixed-universe/20261125T062144Z"
)
FIXED_INPUT_SPECS: dict[str, tuple[Path, str]] = {
    "r_members_jsonl": (
        EXPECTED_R_ROOT / "members.jsonl",
        "660bd1fe1d6a7ea608c6cb4accba497e7a66dc58d83a60ae5fac86900b2a2956",
    ),
    "r_summary_json": (
        EXPECTED_R_ROOT / "summary.json",
        "09400e8a7203338291741b0ad20c4c5c16ebeb2605c9cdb0dc16aa65bc38e300",
    ),
    "u_ledger_jsonl": (
        EXPECTED_U_ROOT / "results" / "ledger.jsonl",
        "c26e4da31c2836e4c2119aed8ad2120417e5b5339c75d41bc36bc4ee95df1638",
    ),
    "u_summary_json": (
        EXPECTED_U_ROOT / "results" / "summary.json",
        "624d26de18a22ed9a4474e78cd1e844bf148b29e33a7c4d47050aa80015edec2",
    ),
    "old_source_binding_json": (
        Path("/private/tmp/stage13-volume-strength-implementation-20261125T124130Z/remediation_r1/source_binding.json"),
        "201472847ddb45a4575a98f39132830a672d69f7a101f4d032f92b1ad0cd0007",
    ),
}
ALLOWED_OUTPUT_PARENT = Path(
    "/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-26-stage1-3-cross-asset-volume-breadth-attribution"
)
EXPECTED_COUNTS: dict[str, int] = {
    "q_total": 964,
    "j_joint_total": 155,
    "b_only_total": 809,
    "focus_week_q_total": 62,
    "focus_week_joint_count": 40,
    "focus_week_b_only_count": 22,
}


class AttributionStopError(DiagnosticStopError):
    """Fail-closed stop error carrying outer STOP=input_invalid and exact verifiable cause."""

    def __init__(self, cause: str, detail: str, *, stop_code: str = "input_invalid") -> None:
        if stop_code == "input_invalid" and cause not in ALLOWED_ERROR_CAUSES:
            raise ValueError(f"unsupported error cause: {cause!r}")
        self.cause = cause
        self.raw_detail = detail
        super().__init__(stop_code, f"cause={cause}: {detail}")


def _validate_protocol_strict(protocol: Any) -> dict[str, Any]:
    if not isinstance(protocol, dict):
        raise AttributionStopError("protocol_mismatch", "protocol must be dict")
    if any(isinstance(v, bool) for v in protocol.values()):
        raise AttributionStopError("protocol_mismatch", "protocol values must not be bool")
    try:
        return validate_protocol(protocol)
    except DiagnosticStopError as exc:
        if exc.stop_code in ("safety_config_mismatch", "safety_invariant_violation"):
            raise AttributionStopError("code_or_authority_mismatch", exc.detail) from exc
        raise AttributionStopError("protocol_mismatch", exc.detail) from exc


def _check_any_nonfinite_numbers(obj: Any, ctx: str) -> None:
    if isinstance(obj, float) and not math.isfinite(obj):
        raise AttributionStopError("nonfinite_value", f"{ctx} contains non-finite float {obj!r}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _check_any_nonfinite_numbers(v, f"{ctx}.{k}")
    elif isinstance(obj, (list, tuple)):
        for idx, item in enumerate(obj):
            _check_any_nonfinite_numbers(item, f"{ctx}[{idx}]")


def _req_str(obj: dict[str, Any], key: str, cause: str, ctx: str) -> str:
    if key not in obj:
        raise AttributionStopError(cause, f"{ctx} missing required string key {key!r}")
    val = obj[key]
    if not isinstance(val, str) or not val.strip():
        raise AttributionStopError(cause, f"{ctx}.{key} must be non-empty str, got {val!r}")
    return val


def _req_int(obj: dict[str, Any], key: str, cause: str, ctx: str) -> int:
    if key not in obj:
        raise AttributionStopError(cause, f"{ctx} missing required int key {key!r}")
    val = obj[key]
    if isinstance(val, bool) or not isinstance(val, int):
        raise AttributionStopError(cause, f"{ctx}.{key} must be int (not bool), got {val!r}")
    return val


def _opt_int(obj: dict[str, Any], key: str, cause: str, ctx: str) -> int | None:
    if key not in obj:
        raise AttributionStopError(cause, f"{ctx} missing key {key!r}")
    val = obj[key]
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, int):
        raise AttributionStopError(cause, f"{ctx}.{key} must be int or None, got {val!r}")
    return val


def _opt_finite_float(obj: dict[str, Any], key: str, cause: str, ctx: str) -> float | None:
    if key not in obj:
        raise AttributionStopError(cause, f"{ctx} missing key {key!r}")
    val = obj[key]
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise AttributionStopError(cause, f"{ctx}.{key} must be number or None, got {val!r}")
    fval = float(val)
    if not math.isfinite(fval):
        raise AttributionStopError("nonfinite_value", f"{ctx}.{key} must be finite, got {val!r}")
    return fval


def _validate_and_project_a_row(
    raw_row: Any,
    *,
    all_symbols_set: set[str],
    eval_start_ms: int,
    eval_end_ms: int,
    lag_ms: int,
    interval_ms: int,
    lookback_ms: int,
    vol_thresh: float,
) -> tuple[tuple[str, str, int], dict[str, Any]]:
    if not isinstance(raw_row, dict):
        raise AttributionStopError("cohort_mismatch", "a_row must be dict")
    _check_any_nonfinite_numbers(raw_row, "a_row")

    cand = _req_str(raw_row, "candidate", "cohort_mismatch", "a_row")
    if cand != CAND_A:
        raise AttributionStopError("cohort_mismatch", f"a_rows must only contain {CAND_A!r}, got {cand!r}")
    sym = _req_str(raw_row, "symbol", "cohort_mismatch", "a_row")
    if sym not in all_symbols_set:
        raise AttributionStopError("cohort_mismatch", f"unexpected symbol {sym!r} in a_rows")

    avail_ms = _req_int(raw_row, "available_at_ms", "time_or_price_mismatch", f"a_row[{sym}]")
    ctx = f"a_row[{sym},{avail_ms}]"
    if not (eval_start_ms <= avail_ms < eval_end_ms):
        raise AttributionStopError("time_or_price_mismatch", f"{ctx} available_at_ms outside eval range")

    win_end_ms = _req_int(raw_row, "window_end_ms", "time_or_price_mismatch", ctx)
    if avail_ms != win_end_ms + lag_ms or win_end_ms % interval_ms != 0:
        raise AttributionStopError(
            "time_or_price_mismatch",
            f"{ctx} window_end_ms={win_end_ms} misaligned with available_at_ms={avail_ms}",
        )
    win_start_ms = _opt_int(raw_row, "window_start_ms", "time_or_price_mismatch", ctx)
    if win_start_ms is not None and (win_end_ms - win_start_ms) != lookback_ms:
        raise AttributionStopError(
            "time_or_price_mismatch",
            f"{ctx} window_start_ms={win_start_ms} != window_end_ms-L={win_end_ms - lookback_ms}",
        )

    status = _req_str(raw_row, "status", "cohort_mismatch", ctx)
    if status not in ALLOWED_ROW_STATUSES:
        raise AttributionStopError("cohort_mismatch", f"{ctx} unknown status {status!r}")
    trig_val = _opt_finite_float(raw_row, "trigger_value", "cohort_mismatch", ctx)

    if status in ("admitted", "overlap_suppressed"):
        if win_start_ms is None:
            raise AttributionStopError("cohort_mismatch", f"{ctx} triggered row missing window_start_ms")
        if trig_val is None or trig_val < vol_thresh:
            raise AttributionStopError(
                "cohort_mismatch",
                f"{ctx} status={status} requires trigger_value>={vol_thresh}, got {trig_val!r}",
            )
    else:
        if status == "not_triggered" and win_start_ms is None:
            raise AttributionStopError("cohort_mismatch", f"{ctx} not_triggered row missing window_start_ms")
        if trig_val is not None:
            raise AttributionStopError(
                "cohort_mismatch",
                f"{ctx} status={status} must have trigger_value=None, got {trig_val!r}",
            )

    # Explicit projection: retain ONLY causal A timing/status/trigger_value (strip any outcome/block fields)
    projected = {
        "candidate": CAND_A,
        "symbol": sym,
        "window_start_ms": win_start_ms,
        "window_end_ms": win_end_ms,
        "available_at_ms": avail_ms,
        "status": status,
        "trigger_value": trig_val,
    }
    return (CAND_A, sym, avail_ms), projected


def annotate_breadth(
    target_keys: list[tuple[str, str, int]],
    a_rows: list[dict[str, Any]],
    *,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    """Annotate fixed J resonance target keys with causal 3-valued H_j(t) and breadth G_i."""
    proto = _validate_protocol_strict(protocol)
    if not isinstance(target_keys, list) or not isinstance(a_rows, list):
        raise AttributionStopError("cohort_mismatch", "target_keys and a_rows must be lists")

    all_symbols = list(proto["symbols"])
    target_symbols = [s for s in all_symbols if s != "BTCUSDT"]
    all_symbols_set = set(all_symbols)
    target_symbols_set = set(target_symbols)
    eval_start_ms = int(proto["eval_start_ms"])
    eval_end_ms = int(proto["eval_end_ms"])
    lag_ms = int(proto["configured_data_lag_ms"])
    interval_ms = int(proto["bar_interval_ms"])
    one_hour_bars = int(proto["one_hour_bar_count"])
    lookback_ms = one_hour_bars * interval_ms
    vol_thresh = float(proto["volume_spike_threshold"])

    # Step 1: Validate target_keys strictly (B identity keys ONLY; outcome Y never enters this function)
    validated_targets: list[tuple[str, str, int]] = []
    seen_targets: set[tuple[str, str, int]] = set()
    for raw_tk in target_keys:
        if not isinstance(raw_tk, (tuple, list)) or len(raw_tk) != 3:
            raise AttributionStopError("cohort_mismatch", f"invalid target_key tuple: {raw_tk!r}")
        t_cand, t_sym, t_avail = raw_tk[0], raw_tk[1], raw_tk[2]
        if not isinstance(t_cand, str) or t_cand != CAND_B:
            raise AttributionStopError("cohort_mismatch", f"target_key candidate must be {CAND_B!r}, got {t_cand!r}")
        if not isinstance(t_sym, str) or t_sym not in target_symbols_set:
            raise AttributionStopError("cohort_mismatch", f"invalid target_key symbol: {t_sym!r}")
        if isinstance(t_avail, bool) or not isinstance(t_avail, int):
            raise AttributionStopError("time_or_price_mismatch", f"invalid target_key timestamp: {t_avail!r}")
        if not (eval_start_ms <= t_avail < eval_end_ms) or (t_avail - lag_ms) % interval_ms != 0:
            raise AttributionStopError(
                "time_or_price_mismatch",
                f"target_key timestamp {t_avail} misaligned or outside eval range",
            )
        tk = (t_cand, t_sym, t_avail)
        if tk in seen_targets:
            raise AttributionStopError("duplicate_key", f"duplicate target_key {tk!r}")
        seen_targets.add(tk)
        validated_targets.append(tk)

    # Step 2: Validate ALL a_rows upfront (preventing any short-circuit H=1 from masking contradictions) and project
    indexed_a: dict[tuple[str, str, int], dict[str, Any]] = {}
    for raw_row in a_rows:
        akey, proj = _validate_and_project_a_row(
            raw_row,
            all_symbols_set=all_symbols_set,
            eval_start_ms=eval_start_ms,
            eval_end_ms=eval_end_ms,
            lag_ms=lag_ms,
            interval_ms=interval_ms,
            lookback_ms=lookback_ms,
            vol_thresh=vol_thresh,
        )
        if akey in indexed_a:
            raise AttributionStopError("duplicate_key", f"duplicate A decision key {akey!r}")
        indexed_a[akey] = proj

    # Step 3: Evaluate 4 expected points in (t - L, t] on each of the other 3 target symbols
    annotations: list[dict[str, Any]] = []
    breadth_counts: dict[str, int] = {"0": 0, "1": 0, "2": 0, "3": 0, "unknown": 0}
    slot_gap_counts: dict[str, int] = {
        "missing_row": 0,
        "feature_not_estimable": 0,
        "block_boundary_censored": 0,
    }
    unknown_gaps: list[dict[str, Any]] = []
    known_g_count = 0
    unknown_g_count = 0

    for t_cand, t_sym, t_ms in validated_targets:
        expected_u_ms = [t_ms - (one_hour_bars - 1 - idx) * interval_ms for idx in range(one_hour_bars)]
        # Sanity guarantee: strictly (t_ms - lookback_ms) < u <= t_ms
        other_syms = [s for s in target_symbols if s != t_sym]
        slots_by_symbol: dict[str, list[dict[str, Any]]] = {}
        h_by_symbol: dict[str, int | None] = {}
        triggered_evidence: list[dict[str, Any]] = []
        unknown_slots: list[dict[str, Any]] = []

        for j_sym in other_syms:
            j_slots: list[dict[str, Any]] = []
            for u_ms in expected_u_ms:
                exp_key = (CAND_A, j_sym, u_ms)
                found = indexed_a.get(exp_key)
                if found is None:
                    slot = {
                        "expected_key": [CAND_A, j_sym, u_ms],
                        "symbol": j_sym,
                        "available_at_ms": u_ms,
                        "present": False,
                        "window_start_ms": None,
                        "window_end_ms": None,
                        "actual_status": None,
                        "trigger_value": None,
                        "fact": "unknown",
                        "gap_reason": "missing_row",
                    }
                    slot_gap_counts["missing_row"] += 1
                    unknown_slots.append(slot)
                else:
                    st = found["status"]
                    tv = found["trigger_value"]
                    if st in ("admitted", "overlap_suppressed"):
                        fact = "triggered"
                        gap_reason = None
                    elif st == "not_triggered":
                        fact = "not_triggered"
                        gap_reason = None
                    else:
                        fact = "unknown"
                        gap_reason = st
                        slot_gap_counts[st] += 1
                    slot = {
                        "expected_key": [CAND_A, j_sym, u_ms],
                        "symbol": j_sym,
                        "available_at_ms": u_ms,
                        "present": True,
                        "window_start_ms": found["window_start_ms"],
                        "window_end_ms": found["window_end_ms"],
                        "actual_status": st,
                        "trigger_value": tv,
                        "fact": fact,
                        "gap_reason": gap_reason,
                    }
                    if fact == "triggered":
                        triggered_evidence.append(slot)
                    elif fact == "unknown":
                        unknown_slots.append(slot)
                j_slots.append(slot)

            slots_by_symbol[j_sym] = j_slots
            if any(s["fact"] == "triggered" for s in j_slots):
                h_by_symbol[j_sym] = 1
            elif all(s["fact"] == "not_triggered" for s in j_slots):
                h_by_symbol[j_sym] = 0
            else:
                h_by_symbol[j_sym] = None

        if all(v is not None for v in h_by_symbol.values()):
            g_val: int | None = sum(int(v) for v in h_by_symbol.values() if v is not None)
            known_g_count += 1
            breadth_counts[str(g_val)] += 1
        else:
            g_val = None
            unknown_g_count += 1
            breadth_counts["unknown"] += 1
            blocking_gaps = [
                s
                for j_sym, h_val in h_by_symbol.items()
                if h_val is None
                for s in slots_by_symbol[j_sym]
                if s["fact"] == "unknown"
            ]
            unknown_gaps.append(
                {
                    "target_key": [t_cand, t_sym, t_ms],
                    "h_by_symbol": h_by_symbol,
                    "blocking_unknown_slots": blocking_gaps,
                }
            )

        annotations.append(
            {
                "target_key": [t_cand, t_sym, t_ms],
                "candidate": t_cand,
                "symbol": t_sym,
                "available_at_ms": t_ms,
                "lookback_ms": lookback_ms,
                "expected_u_ms": expected_u_ms,
                "other_symbols": other_syms,
                "h_by_symbol": h_by_symbol,
                "breadth_g": g_val,
                "g_estimable": g_val is not None,
                "slots_by_symbol": slots_by_symbol,
                "triggered_evidence": triggered_evidence,
                "unknown_slots": unknown_slots,
            }
        )

    return {
        "lookback_ms": lookback_ms,
        "target_count": len(annotations),
        "known_g_count": known_g_count,
        "unknown_g_count": unknown_g_count,
        "all_g_estimable": unknown_g_count == 0,
        "breadth_counts": breadth_counts,
        "slot_gap_counts_by_reason": slot_gap_counts,
        "unknown_gaps": unknown_gaps,
        "annotations": annotations,
    }


def _ms_to_iso_utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ms_to_utc_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")


def _req_bool(obj: dict[str, Any], key: str, cause: str, ctx: str) -> bool:
    if key not in obj:
        raise AttributionStopError(cause, f"{ctx} missing required bool key {key!r}")
    val = obj[key]
    if not isinstance(val, bool):
        raise AttributionStopError(cause, f"{ctx}.{key} must be bool, got {val!r}")
    return val


def _req_finite_float(obj: dict[str, Any], key: str, cause: str, ctx: str) -> float:
    val = _opt_finite_float(obj, key, cause, ctx)
    if val is None:
        raise AttributionStopError(cause, f"{ctx}.{key} must not be None")
    return val


def _verify_safety_strict() -> dict[str, Any]:
    try:
        return verify_base_and_safety_config()
    except DiagnosticStopError as exc:
        raise AttributionStopError("code_or_authority_mismatch", exc.detail) from exc


def _validate_member_row(
    raw_m: Any,
    *,
    target_symbols_set: set[str],
    eval_start_ms: int,
    eval_end_ms: int,
    lag_ms: int,
    interval_ms: int,
    entry_delay_bars: int,
    lookback_ms: int,
    horizon_ms: int,
    block_ms: int,
    num_blocks: int,
    vol_thresh: float,
) -> tuple[tuple[str, str, int], dict[str, Any]]:
    if not isinstance(raw_m, dict):
        raise AttributionStopError("cohort_mismatch", "member row must be dict")
    _check_any_nonfinite_numbers(raw_m, "member")

    cand = _req_str(raw_m, "candidate", "cohort_mismatch", "member")
    if cand != CAND_B:
        raise AttributionStopError("cohort_mismatch", f"member candidate must be {CAND_B!r}, got {cand!r}")
    sym = _req_str(raw_m, "symbol", "cohort_mismatch", "member")
    if sym not in target_symbols_set:
        raise AttributionStopError("cohort_mismatch", f"member symbol {sym!r} outside target universe")
    avail_ms = _req_int(raw_m, "available_at_ms", "time_or_price_mismatch", f"member[{sym}]")
    ctx = f"member[{sym},{avail_ms}]"
    if not (eval_start_ms <= avail_ms < eval_end_ms):
        raise AttributionStopError("time_or_price_mismatch", f"{ctx} available_at_ms outside eval range")

    win_end_ms = _req_int(raw_m, "window_end_ms", "time_or_price_mismatch", ctx)
    win_start_ms = _req_int(raw_m, "window_start_ms", "time_or_price_mismatch", ctx)
    if avail_ms != win_end_ms + lag_ms or win_end_ms % interval_ms != 0 or (win_end_ms - win_start_ms) != lookback_ms:
        raise AttributionStopError("time_or_price_mismatch", f"{ctx} window/lag alignment invalid")

    block_id = _req_int(raw_m, "block_id", "time_or_price_mismatch", ctx)
    expected_block = (avail_ms - eval_start_ms) // block_ms
    if not (0 <= block_id < num_blocks) or block_id != expected_block:
        raise AttributionStopError(
            "time_or_price_mismatch",
            f"{ctx} block_id={block_id} != expected_block={expected_block}",
        )
    block_end_ms = eval_start_ms + (block_id + 1) * block_ms

    entry_ms = _req_int(raw_m, "entry_bar_start_ms", "time_or_price_mismatch", ctx)
    exit_ms = _req_int(raw_m, "exit_bar_end_ms", "time_or_price_mismatch", ctx)
    expected_entry_ms = win_end_ms + entry_delay_bars * interval_ms
    if (
        entry_ms != expected_entry_ms
        or entry_ms <= avail_ms
        or (exit_ms - entry_ms) != horizon_ms
        or exit_ms > block_end_ms
    ):
        raise AttributionStopError("time_or_price_mismatch", f"{ctx} entry/exit 4h horizon alignment invalid")

    entry_open = _req_finite_float(raw_m, "entry_open_price", "time_or_price_mismatch", ctx)
    exit_close = _req_finite_float(raw_m, "exit_close_price", "time_or_price_mismatch", ctx)
    if entry_open <= 0.0 or exit_close <= 0.0:
        raise AttributionStopError("time_or_price_mismatch", f"{ctx} non-positive reference price")

    y_bps = _req_finite_float(raw_m, "y_gross_bps", "time_or_price_mismatch", ctx)
    expected_y = 10000.0 * (exit_close / entry_open - 1.0)
    if abs(y_bps - expected_y) > 1e-6:
        raise AttributionStopError(
            "time_or_price_mismatch",
            f"{ctx} y_gross_bps={y_bps} != formula={expected_y}",
        )
    mae_bps = _req_finite_float(raw_m, "mae_4h_bps", "time_or_price_mismatch", ctx)
    mfe_bps = _req_finite_float(raw_m, "mfe_4h_bps", "time_or_price_mismatch", ctx)
    if mae_bps > min(0.0, y_bps) + 1e-6 or mfe_bps < max(0.0, y_bps) - 1e-6 or mae_bps > mfe_bps + 1e-6:
        raise AttributionStopError("time_or_price_mismatch", f"{ctx} MAE/MFE envelope contradicts y_gross_bps")

    b_trig = _req_finite_float(raw_m, "b_trigger_value", "cohort_mismatch", ctx)
    self_r1h = _req_finite_float(raw_m, "self_r1h", "cohort_mismatch", ctx)
    btc_r1h = _req_finite_float(raw_m, "btc_r1h", "cohort_mismatch", ctx)
    grp = _req_str(raw_m, "group", "cohort_mismatch", ctx)
    if grp not in ("joint", "b_only"):
        raise AttributionStopError("cohort_mismatch", f"{ctx} invalid group {grp!r}")
    a_trig_flag = _req_bool(raw_m, "a_triggered", "cohort_mismatch", ctx)
    if a_trig_flag != (grp == "joint"):
        raise AttributionStopError("cohort_mismatch", f"{ctx} group={grp!r} contradicts a_triggered={a_trig_flag!r}")

    a_status = _req_str(raw_m, "a_status", "cohort_mismatch", ctx)
    a_tv = _opt_finite_float(raw_m, "a_trigger_value", "cohort_mismatch", ctx)
    if a_trig_flag:
        if a_status not in ("admitted", "overlap_suppressed") or a_tv is None or a_tv < vol_thresh:
            raise AttributionStopError("cohort_mismatch", f"{ctx} joint member has invalid A trigger fields")
    else:
        if a_status != "not_triggered" or a_tv is not None:
            raise AttributionStopError("cohort_mismatch", f"{ctx} b_only member must have not_triggered/None")

    if "a_key" not in raw_m or list(raw_m["a_key"]) != [CAND_A, sym, avail_ms]:
        raise AttributionStopError("cohort_mismatch", f"{ctx} invalid a_key")
    in_sup = _req_bool(raw_m, "in_common_support", "cohort_mismatch", ctx)
    sup_status = _req_str(raw_m, "support_status", "cohort_mismatch", ctx)
    if "conditional_control_keys" not in raw_m or not isinstance(raw_m["conditional_control_keys"], list):
        raise AttributionStopError("cohort_mismatch", f"{ctx} conditional_control_keys must be list")
    ctrl_mean = _opt_finite_float(raw_m, "conditional_control_mean_bps", "cohort_mismatch", ctx)
    cond_d = _opt_finite_float(raw_m, "conditional_d_bps", "cohort_mismatch", ctx)

    validated = {
        "candidate": cand,
        "symbol": sym,
        "available_at_ms": avail_ms,
        "block_id": block_id,
        "window_start_ms": win_start_ms,
        "window_end_ms": win_end_ms,
        "entry_bar_start_ms": entry_ms,
        "exit_bar_end_ms": exit_ms,
        "entry_open_price": entry_open,
        "exit_close_price": exit_close,
        "self_r1h": self_r1h,
        "btc_r1h": btc_r1h,
        "b_trigger_value": b_trig,
        "y_gross_bps": y_bps,
        "mfe_4h_bps": mfe_bps,
        "mae_4h_bps": mae_bps,
        "a_key": [CAND_A, sym, avail_ms],
        "a_status": a_status,
        "a_trigger_value": a_tv,
        "a_triggered": a_trig_flag,
        "group": grp,
        "in_common_support": in_sup,
        "support_status": sup_status,
        "conditional_control_keys": list(raw_m["conditional_control_keys"]),
        "conditional_control_mean_bps": ctrl_mean,
        "conditional_d_bps": cond_d,
    }
    return (cand, sym, avail_ms), validated


def _cell_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    sum_y = float(sum(float(r["y_gross_bps"]) for r in rows))
    return {
        "n": n,
        "sum_y_bps": sum_y,
        "mean_bps": (sum_y / n) if n > 0 else None,
    }


def _summarize_single_g_level(
    breadth_g: int,
    rows_g: list[dict[str, Any]],
    *,
    target_symbols: list[str],
    cost_bps_list: list[float],
) -> dict[str, Any]:
    n = len(rows_g)
    present_syms = [s for s in target_symbols if any(r["symbol"] == s for r in rows_g)]
    non_empty_blocks = sorted({int(r["block_id"]) for r in rows_g})
    if n == 0:
        return {
            "breadth_g": breadth_g,
            "n": 0,
            "denominator_n": 0,
            "symbol_count": 0,
            "symbols_present": [],
            "non_empty_block_count": 0,
            "non_empty_blocks": [],
            "sum_y_bps": 0.0,
            "mean_bps": None,
            "median_bps": None,
            "win_count": 0,
            "loss_count": 0,
            "zero_count": 0,
            "win_rate": None,
            "avg_win_bps": None,
            "avg_loss_bps": None,
            "payoff_ratio": None,
            "worst_event_bps": None,
            "quantiles_bps": {
                "p05": None,
                "p10": None,
                "p25": None,
                "p50": None,
                "p75": None,
                "p90": None,
            },
            "mae_4h_gross_bps": {"mean": None, "p10": None, "p50": None, "min": None},
            "mfe_4h_gross_bps": {"mean": None, "p50": None, "p90": None, "max": None},
            "cost_scenarios": {
                f"{float(c):.1f}": {
                    "cost_round_trip_bps": float(c),
                    "mean_bps": None,
                    "p10_bps": None,
                    "worst_event_bps": None,
                }
                for c in cost_bps_list
            },
        }

    ys = [float(r["y_gross_bps"]) for r in rows_g]
    maes = [float(r["mae_4h_bps"]) for r in rows_g]
    mfes = [float(r["mfe_4h_bps"]) for r in rows_g]
    wins = [y for y in ys if y > 0.0]
    losses = [y for y in ys if y < 0.0]
    zeros = [y for y in ys if y == 0.0]

    sum_y = float(sum(ys))
    mean_y = sum_y / n
    p05 = linear_quantile(ys, 0.05)
    p10 = linear_quantile(ys, 0.10)
    p25 = linear_quantile(ys, 0.25)
    p50 = linear_quantile(ys, 0.50)
    p75 = linear_quantile(ys, 0.75)
    p90 = linear_quantile(ys, 0.90)

    win_rate = len(wins) / n
    avg_win = (sum(wins) / len(wins)) if wins else None
    avg_loss = (sum(losses) / len(losses)) if losses else None
    payoff = (
        (avg_win / abs(avg_loss))
        if (avg_win is not None and avg_loss is not None and abs(avg_loss) > 0.0)
        else None
    )

    cost_scenarios: dict[str, dict[str, Any]] = {}
    for c in cost_bps_list:
        c_val = float(c)
        shifted = [y - c_val for y in ys]
        cost_scenarios[f"{c_val:.1f}"] = {
            "cost_round_trip_bps": c_val,
            "mean_bps": sum(shifted) / n,
            "p10_bps": linear_quantile(shifted, 0.10),
            "worst_event_bps": min(shifted),
        }

    return {
        "breadth_g": breadth_g,
        "n": n,
        "denominator_n": n,
        "symbol_count": len(present_syms),
        "symbols_present": present_syms,
        "non_empty_block_count": len(non_empty_blocks),
        "non_empty_blocks": non_empty_blocks,
        "sum_y_bps": sum_y,
        "mean_bps": mean_y,
        "median_bps": p50,
        "win_count": len(wins),
        "loss_count": len(losses),
        "zero_count": len(zeros),
        "win_rate": win_rate,
        "avg_win_bps": avg_win,
        "avg_loss_bps": avg_loss,
        "payoff_ratio": payoff,
        "worst_event_bps": min(ys),
        "quantiles_bps": {
            "p05": p05,
            "p10": p10,
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "p90": p90,
        },
        "mae_4h_gross_bps": {
            "mean": sum(maes) / n,
            "p10": linear_quantile(maes, 0.10),
            "p50": linear_quantile(maes, 0.50),
            "min": min(maes),
        },
        "mfe_4h_gross_bps": {
            "mean": sum(mfes) / n,
            "p50": linear_quantile(mfes, 0.50),
            "p90": linear_quantile(mfes, 0.90),
            "max": max(mfes),
        },
        "cost_scenarios": cost_scenarios,
    }


def _summarize_four_g_levels(
    joined_rows: list[dict[str, Any]],
    *,
    target_symbols: list[str],
    cost_bps_list: list[float],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for g in (0, 1, 2, 3):
        rows_g = [r for r in joined_rows if r["breadth_g"] == g]
        out[str(g)] = _summarize_single_g_level(
            g,
            rows_g,
            target_symbols=target_symbols,
            cost_bps_list=cost_bps_list,
        )
    if sum(out[str(g)]["n"] for g in (0, 1, 2, 3)) != len(joined_rows):
        raise AttributionStopError("cohort_mismatch", "4-level breadth denominator conservation failed")
    return out


def describe_attribution(
    members: list[dict[str, Any]],
    breadth: dict[str, Any],
    *,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    """Produce Block-9 timeline passthrough and 4-level breadth description (or gap report)."""
    _verify_safety_strict()
    proto = _validate_protocol_strict(protocol)
    if not isinstance(members, list) or not members or not isinstance(breadth, dict):
        raise AttributionStopError("cohort_mismatch", "members must be non-empty list and breadth must be dict")
    _check_any_nonfinite_numbers(breadth, "breadth")

    all_symbols = list(proto["symbols"])
    target_symbols = [s for s in all_symbols if s != "BTCUSDT"]
    target_symbols_set = set(target_symbols)
    eval_start_ms = int(proto["eval_start_ms"])
    eval_end_ms = int(proto["eval_end_ms"])
    lag_ms = int(proto["configured_data_lag_ms"])
    interval_ms = int(proto["bar_interval_ms"])
    entry_delay_bars = int(proto["entry_delay_bars"])
    lookback_ms = int(proto["one_hour_bar_count"]) * interval_ms
    horizon_ms = int(proto["forward_4h_bar_count"]) * interval_ms
    block_ms = int(proto["block_days"]) * 86_400_000
    num_blocks = int(proto["block_count"])
    vol_thresh = float(proto["volume_spike_threshold"])
    cost_bps_list = [float(c) for c in proto["cost_scenarios_round_trip_bps"]]

    # Step 1: Validate all Q member rows and index unique keys
    validated_members: list[dict[str, Any]] = []
    member_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for raw_m in members:
        mkey, vm = _validate_member_row(
            raw_m,
            target_symbols_set=target_symbols_set,
            eval_start_ms=eval_start_ms,
            eval_end_ms=eval_end_ms,
            lag_ms=lag_ms,
            interval_ms=interval_ms,
            entry_delay_bars=entry_delay_bars,
            lookback_ms=lookback_ms,
            horizon_ms=horizon_ms,
            block_ms=block_ms,
            num_blocks=num_blocks,
            vol_thresh=vol_thresh,
        )
        if mkey in member_by_key:
            raise AttributionStopError("duplicate_key", f"duplicate member key {mkey!r}")
        member_by_key[mkey] = vm
        validated_members.append(vm)

    j_members = [m for m in validated_members if m["group"] == "joint"]
    b_only_members = [m for m in validated_members if m["group"] == "b_only"]
    j_key_set = {(m["candidate"], m["symbol"], int(m["available_at_ms"])) for m in j_members}

    # Step 2: Validate locked breadth annotations strictly match J key set BEFORE joining outcomes
    if "annotations" not in breadth or not isinstance(breadth["annotations"], list):
        raise AttributionStopError("cohort_mismatch", "breadth missing annotations list")
    ann_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    actual_counts = {"0": 0, "1": 0, "2": 0, "3": 0, "unknown": 0}
    known_n = 0
    unknown_n = 0

    for raw_ann in breadth["annotations"]:
        if not isinstance(raw_ann, dict) or "target_key" not in raw_ann:
            raise AttributionStopError("cohort_mismatch", "invalid breadth annotation entry")
        tk_raw = raw_ann["target_key"]
        if not isinstance(tk_raw, list) or len(tk_raw) != 3:
            raise AttributionStopError("cohort_mismatch", f"invalid breadth target_key {tk_raw!r}")
        a_cand = _req_str(raw_ann, "candidate", "cohort_mismatch", "annotation")
        a_sym = _req_str(raw_ann, "symbol", "cohort_mismatch", "annotation")
        a_ms = _req_int(raw_ann, "available_at_ms", "time_or_price_mismatch", "annotation")
        if [a_cand, a_sym, a_ms] != tk_raw or a_cand != CAND_B or a_sym not in target_symbols_set:
            raise AttributionStopError("cohort_mismatch", f"annotation key mismatch: {tk_raw!r}")
        akey = (a_cand, a_sym, a_ms)
        if akey in ann_by_key:
            raise AttributionStopError("duplicate_key", f"duplicate breadth annotation key {akey!r}")

        if "h_by_symbol" not in raw_ann or not isinstance(raw_ann["h_by_symbol"], dict):
            raise AttributionStopError("cohort_mismatch", f"annotation {akey!r} missing h_by_symbol")
        expected_others = [s for s in target_symbols if s != a_sym]
        h_map = raw_ann["h_by_symbol"]
        if set(h_map.keys()) != set(expected_others):
            raise AttributionStopError("cohort_mismatch", f"annotation {akey!r} h_by_symbol keys invalid")
        for hs, hv in h_map.items():
            if hv is not None and (isinstance(hv, bool) or hv not in (0, 1)):
                raise AttributionStopError("cohort_mismatch", f"annotation {akey!r} h_by_symbol[{hs}]={hv!r}")

        g_val = _opt_int(raw_ann, "breadth_g", "cohort_mismatch", f"annotation[{a_sym},{a_ms}]")
        g_est = _req_bool(raw_ann, "g_estimable", "cohort_mismatch", f"annotation[{a_sym},{a_ms}]")
        if all(hv is not None for hv in h_map.values()):
            expected_g = sum(int(hv) for hv in h_map.values() if hv is not None)
            if g_val != expected_g or not g_est:
                raise AttributionStopError("cohort_mismatch", f"annotation {akey!r} breadth_g contradicts h_by_symbol")
            known_n += 1
            actual_counts[str(g_val)] += 1
        else:
            if g_val is not None or g_est:
                raise AttributionStopError("cohort_mismatch", f"annotation {akey!r} unknown H must yield breadth_g=None")
            unknown_n += 1
            actual_counts["unknown"] += 1

        ann_by_key[akey] = raw_ann

    if set(ann_by_key.keys()) != j_key_set or len(ann_by_key) != len(j_members):
        raise AttributionStopError(
            "cohort_mismatch",
            f"breadth annotation keys (n={len(ann_by_key)}) != J member keys (n={len(j_members)})",
        )
    if (
        breadth.get("target_count") != len(j_members)
        or breadth.get("known_g_count") != known_n
        or breadth.get("unknown_g_count") != unknown_n
        or breadth.get("all_g_estimable") != (unknown_n == 0)
        or breadth.get("breadth_counts") != actual_counts
    ):
        raise AttributionStopError("cohort_mismatch", "breadth top-level counts contradict annotations")

    all_g_estimable = unknown_n == 0

    # Step 3: Build Block-9 timeline & passthrough (always deliverable from original Q Block-9 rows)
    focus_block_id = 9
    b9_start_ms = eval_start_ms + focus_block_id * block_ms
    b9_end_ms = b9_start_ms + block_ms
    b9_dates = [_ms_to_utc_date(b9_start_ms + d * 86_400_000) for d in range(int(proto["block_days"]))]

    b9_sorted = sorted(
        [m for m in validated_members if int(m["block_id"]) == focus_block_id],
        key=lambda r: (int(r["available_at_ms"]), str(r["symbol"])),
    )
    timeline: list[dict[str, Any]] = []
    for m in b9_sorted:
        mkey = (m["candidate"], m["symbol"], int(m["available_at_ms"]))
        ann = ann_by_key.get(mkey)
        timeline.append(
            {
                "candidate": m["candidate"],
                "symbol": m["symbol"],
                "available_at_ms": m["available_at_ms"],
                "available_at_utc": _ms_to_iso_utc(m["available_at_ms"]),
                "utc_date": _ms_to_utc_date(m["available_at_ms"]),
                "entry_bar_start_ms": m["entry_bar_start_ms"],
                "entry_bar_start_utc": _ms_to_iso_utc(m["entry_bar_start_ms"]),
                "exit_bar_end_ms": m["exit_bar_end_ms"],
                "exit_bar_end_utc": _ms_to_iso_utc(m["exit_bar_end_ms"]),
                "block_id": m["block_id"],
                "group": m["group"],
                "a_status": m["a_status"],
                "a_trigger_value": m["a_trigger_value"],
                "b_trigger_value": m["b_trigger_value"],
                "self_r1h": m["self_r1h"],
                "btc_r1h": m["btc_r1h"],
                "y_gross_bps": m["y_gross_bps"],
                "mae_4h_bps": m["mae_4h_bps"],
                "mfe_4h_bps": m["mfe_4h_bps"],
                "in_common_support": m["in_common_support"],
                "support_status": m["support_status"],
                "conditional_control_keys": [
                    list(k) if isinstance(k, (list, tuple)) else k for k in m["conditional_control_keys"]
                ],
                "conditional_control_mean_bps": m["conditional_control_mean_bps"],
                "conditional_d_bps": m["conditional_d_bps"],
                "breadth_g": ann["breadth_g"] if ann is not None else None,
                "h_by_symbol": dict(ann["h_by_symbol"]) if ann is not None else None,
            }
        )

    def _b9_slice_summary(slice_rows: list[dict[str, Any]]) -> dict[str, Any]:
        j_slice = [r for r in slice_rows if r["group"] == "joint"]
        bo_slice = [r for r in slice_rows if r["group"] == "b_only"]
        j_sum = float(sum(float(r["y_gross_bps"]) for r in j_slice))
        bo_sum = float(sum(float(r["y_gross_bps"]) for r in bo_slice))
        return {
            "q_count": len(slice_rows),
            "joint_count": len(j_slice),
            "b_only_count": len(bo_slice),
            "joint_sum_y_bps": j_sum,
            "joint_mean_y_bps": (j_sum / len(j_slice)) if j_slice else None,
            "b_only_sum_y_bps": bo_sum,
            "b_only_mean_y_bps": (bo_sum / len(bo_slice)) if bo_slice else None,
        }

    all_b9_dates = sorted(set(b9_dates) | {r["utc_date"] for r in timeline})
    by_utc_date = [
        {"utc_date": d, **_b9_slice_summary([r for r in timeline if r["utc_date"] == d])}
        for d in all_b9_dates
    ]
    by_utc_date_and_symbol = [
        {
            "utc_date": d,
            "symbol": sym,
            **_b9_slice_summary([r for r in timeline if r["utc_date"] == d and r["symbol"] == sym]),
        }
        for d in all_b9_dates
        for sym in target_symbols
    ]
    b9_by_symbol = {
        sym: {"symbol": sym, **_b9_slice_summary([r for r in timeline if r["symbol"] == sym])}
        for sym in target_symbols
    }
    doge_controls = [
        {
            "utc_date": r["utc_date"],
            "symbol": r["symbol"],
            "available_at_ms": r["available_at_ms"],
            "available_at_utc": r["available_at_utc"],
            "entry_bar_start_utc": r["entry_bar_start_utc"],
            "exit_bar_end_utc": r["exit_bar_end_utc"],
            "b_trigger_value": r["b_trigger_value"],
            "self_r1h": r["self_r1h"],
            "btc_r1h": r["btc_r1h"],
            "y_gross_bps": r["y_gross_bps"],
            "mae_4h_bps": r["mae_4h_bps"],
            "mfe_4h_bps": r["mfe_4h_bps"],
            "support_status": r["support_status"],
        }
        for r in timeline
        if r["symbol"] == "DOGEUSDT" and r["group"] == "b_only"
    ]

    focus_week = {
        "block_id": focus_block_id,
        "block_start_utc": _ms_to_iso_utc(b9_start_ms),
        "block_end_utc": _ms_to_iso_utc(b9_end_ms),
        **_b9_slice_summary(timeline),
        "by_utc_date": by_utc_date,
        "by_utc_date_and_symbol": by_utc_date_and_symbol,
        "by_symbol": b9_by_symbol,
        "doge_controls": doge_controls,
        "comparability_limitation": (
            "same_block_same_symbol_controls_do_not_control_for_intra_week_regime_phase_or_late_week_sparse_controls"
        ),
        "timeline": timeline,
    }

    # Step 4: Build deterministic breadth_members (155 J keys preserved whether G is known or unknown)
    j_sorted = sorted(j_members, key=lambda r: (int(r["available_at_ms"]), str(r["symbol"])))
    breadth_members: list[dict[str, Any]] = []
    for jm in j_sorted:
        jkey = (jm["candidate"], jm["symbol"], int(jm["available_at_ms"]))
        ann = ann_by_key[jkey]
        row_out: dict[str, Any] = {
            "target_key": [jm["candidate"], jm["symbol"], jm["available_at_ms"]],
            "candidate": jm["candidate"],
            "symbol": jm["symbol"],
            "available_at_ms": jm["available_at_ms"],
            "available_at_utc": _ms_to_iso_utc(jm["available_at_ms"]),
            "block_id": jm["block_id"],
            "window_start_ms": jm["window_start_ms"],
            "window_end_ms": jm["window_end_ms"],
            "a_key": jm["a_key"],
            "a_status": jm["a_status"],
            "a_trigger_value": jm["a_trigger_value"],
            "b_trigger_value": jm["b_trigger_value"],
            "lookback_ms": ann["lookback_ms"],
            "expected_u_ms": list(ann["expected_u_ms"]),
            "other_symbols": list(ann["other_symbols"]),
            "h_by_symbol": dict(ann["h_by_symbol"]),
            "breadth_g": ann["breadth_g"],
            "g_estimable": ann["g_estimable"],
            "slots_by_symbol": ann["slots_by_symbol"],
            "triggered_evidence": ann["triggered_evidence"],
            "unknown_slots": ann["unknown_slots"],
        }
        if all_g_estimable:
            row_out["outcome_joined"] = True
            row_out["entry_bar_start_ms"] = jm["entry_bar_start_ms"]
            row_out["exit_bar_end_ms"] = jm["exit_bar_end_ms"]
            row_out["entry_open_price"] = jm["entry_open_price"]
            row_out["exit_close_price"] = jm["exit_close_price"]
            row_out["y_gross_bps"] = jm["y_gross_bps"]
            row_out["mae_4h_bps"] = jm["mae_4h_bps"]
            row_out["mfe_4h_bps"] = jm["mfe_4h_bps"]
        else:
            row_out["outcome_joined"] = False
            row_out["entry_bar_start_ms"] = None
            row_out["exit_bar_end_ms"] = None
            row_out["entry_open_price"] = None
            row_out["exit_close_price"] = None
            row_out["y_gross_bps"] = None
            row_out["mae_4h_bps"] = None
            row_out["mfe_4h_bps"] = None
        breadth_members.append(row_out)

    # Step 5: Constructibility gate — only compute 4-level return tables when ALL J targets have known G
    if all_g_estimable:
        full_sample: dict[str, Any] | None = _summarize_four_g_levels(
            breadth_members,
            target_symbols=target_symbols,
            cost_bps_list=cost_bps_list,
        )
        without_b9_rows = [r for r in breadth_members if int(r["block_id"]) != focus_block_id]
        without_block_9: dict[str, Any] | None = _summarize_four_g_levels(
            without_b9_rows,
            target_symbols=target_symbols,
            cost_bps_list=cost_bps_list,
        )

        per_symbol: dict[str, Any] | None = {}
        for sym in target_symbols:
            sym_rows = [r for r in breadth_members if r["symbol"] == sym]
            sym_tot = _cell_summary(sym_rows)
            per_symbol[sym] = {
                "symbol": sym,
                "total_n": sym_tot["n"],
                "sum_y_bps": sym_tot["sum_y_bps"],
                "mean_bps": sym_tot["mean_bps"],
                "by_g": {
                    str(g): _cell_summary([r for r in sym_rows if r["breadth_g"] == g])
                    for g in (0, 1, 2, 3)
                },
            }
        if sum(per_symbol[s]["by_g"][str(g)]["n"] for s in target_symbols for g in (0, 1, 2, 3)) != len(breadth_members):
            raise AttributionStopError("cohort_mismatch", "per_symbol cell conservation failed")

        per_block: list[dict[str, Any]] | None = []
        for b_id in range(num_blocks):
            blk_start = eval_start_ms + b_id * block_ms
            blk_end = blk_start + block_ms
            blk_rows = [r for r in breadth_members if int(r["block_id"]) == b_id]
            blk_tot = _cell_summary(blk_rows)
            per_block.append(
                {
                    "block_id": b_id,
                    "block_start_utc": _ms_to_iso_utc(blk_start),
                    "block_end_utc": _ms_to_iso_utc(blk_end),
                    "total_n": blk_tot["n"],
                    "sum_y_bps": blk_tot["sum_y_bps"],
                    "mean_bps": blk_tot["mean_bps"],
                    "by_g": {
                        str(g): _cell_summary([r for r in blk_rows if r["breadth_g"] == g])
                        for g in (0, 1, 2, 3)
                    },
                }
            )
        if sum(b["by_g"][str(g)]["n"] for b in per_block for g in (0, 1, 2, 3)) != len(breadth_members):
            raise AttributionStopError("cohort_mismatch", "per_block cell conservation failed")

        routing = {
            "conclusion": "descriptive_attribution_only",
            "observation_label": "descriptive_attribution_only",
            "resource_decision": "pause_for_new_evidence",
            "alpha_research_status": "evidence_insufficient",
        }
    else:
        full_sample = None
        without_block_9 = None
        per_symbol = None
        per_block = None
        routing = {
            "conclusion": "breadth_not_estimable",
            "observation_label": "breadth_not_estimable",
            "resource_decision": "stop_due_to_evidence",
            "alpha_research_status": "evidence_insufficient",
        }

    if "slot_gap_counts_by_reason" not in breadth or not isinstance(breadth["slot_gap_counts_by_reason"], dict):
        raise AttributionStopError("cohort_mismatch", "breadth missing slot_gap_counts_by_reason dict")
    if "unknown_gaps" not in breadth or not isinstance(breadth["unknown_gaps"], list):
        raise AttributionStopError("cohort_mismatch", "breadth missing unknown_gaps list")

    return {
        "counts": {
            "q_total": len(validated_members),
            "j_joint_total": len(j_members),
            "b_only_total": len(b_only_members),
            "focus_week_q_total": len(timeline),
            "focus_week_joint_count": focus_week["joint_count"],
            "focus_week_b_only_count": focus_week["b_only_count"],
            "breadth_counts": dict(actual_counts),
        },
        "coverage": {
            "lookback_ms": lookback_ms,
            "target_count": len(j_members),
            "known_g_count": known_n,
            "unknown_g_count": unknown_n,
            "all_g_estimable": all_g_estimable,
            "slot_gap_counts_by_reason": dict(breadth["slot_gap_counts_by_reason"]),
            "unknown_targets": list(breadth["unknown_gaps"]),
        },
        "focus_week": focus_week,
        "full_sample": full_sample,
        "without_block_9": without_block_9,
        "per_symbol": per_symbol,
        "per_block": per_block,
        "cost_mode": "cost_context_only",
        "cost_scenarios_round_trip_bps": cost_bps_list,
        "minimum_economically_meaningful_gain": None,
        "dependency_unit": "23_shared_7d_market_blocks_approximate_not_independent_oos",
        "prior_exposure_disclosure": (
            "Q=964, J=155, B-only=809, Block-9 (2026-08-17..2026-08-24, 40 joint / 22 b_only), "
            "daily breakdown, volume multiples, and DOGE 2026-08-23 controls (-473.71 / -86.23 bps) "
            "were already exposed prior to this diagnostic; without_block_9 is a fixed dependency "
            "diagnostic and NOT an independent out-of-sample validation set."
        ),
        "governance": {
            "live_trading_enabled": False,
            "paper_trading_allowed": False,
            "execution_engine_allowed": False,
            "producer_enabled": False,
            "strategy_promotion_allowed": False,
            "best_g_selection_or_threshold_merge_allowed": False,
            "causal_or_marginal_effect_claim_allowed": False,
            "executable_net_edge_claim_allowed": False,
            "independent_out_of_sample_claim_allowed": False,
            "prior_stage_conclusions_modified": False,
        },
        "routing": routing,
        "breadth_members": breadth_members,
    }


_MACOS_ROOT_ALIASES = frozenset({"/tmp", "/var", "/etc"})


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expected_canonical_path(path: Path) -> Path:
    if sys.platform == "darwin" and len(path.parts) >= 2 and f"/{path.parts[1]}" in _MACOS_ROOT_ALIASES:
        return Path("/private", *path.parts[1:])
    return path


def _reject_symlink_chain_strict(path: Path, *, cause: str, label: str) -> None:
    try:
        _reject_symlink_chain(path, stop_code="input_path_mismatch", label=label)
    except DiagnosticStopError as exc:
        raise AttributionStopError(cause, exc.detail) from exc


def _stream_sha256_strict(path: Path, *, missing_cause: str = "hash_mismatch") -> str:
    try:
        return _stream_sha256(path, stop_code="input_identity_mismatch")
    except DiagnosticStopError as exc:
        if exc.stop_code == "input_path_mismatch":
            raise AttributionStopError("path_mismatch", exc.detail) from exc
        raise AttributionStopError(missing_cause, exc.detail) from exc


def _git_head(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise AttributionStopError(
            "code_or_authority_mismatch",
            f"failed to read git HEAD: {proc.stderr.strip()}",
        )
    return proc.stdout.strip()


def _reject_nonfinite_constant(val: str) -> Any:
    raise AttributionStopError("nonfinite_value", f"non-finite JSON constant rejected: {val}")


def _loads_strict_json(text: str, *, syntax_cause: str, ctx: str) -> Any:
    try:
        obj = json.loads(text, parse_constant=_reject_nonfinite_constant)
    except AttributionStopError:
        raise
    except json.JSONDecodeError as exc:
        raise AttributionStopError(syntax_cause, f"{ctx} invalid JSON: {exc}") from exc
    _check_any_nonfinite_numbers(obj, ctx)
    return obj


def _verify_helper_origins_and_code_bindings() -> list[dict[str, str]]:
    _reject_symlink_chain_strict(REPO_ROOT, cause="code_or_authority_mismatch", label="repo_root")
    core_file = getattr(diag_mod, "__file__", None)
    old_cli_file = getattr(old_cli_mod, "__file__", None)
    if not isinstance(core_file, str) or not core_file:
        raise AttributionStopError("code_or_authority_mismatch", "diag_mod missing __file__")
    if not isinstance(old_cli_file, str) or not old_cli_file:
        raise AttributionStopError("code_or_authority_mismatch", "old_cli_mod missing __file__")
    if Path(core_file).resolve() != (REPO_ROOT / CORE_REL_PATH).resolve():
        raise AttributionStopError(
            "code_or_authority_mismatch",
            f"core helper origin {core_file} != {(REPO_ROOT / CORE_REL_PATH).resolve()}",
        )
    if Path(old_cli_file).resolve() != (REPO_ROOT / OLD_CLI_REL_PATH).resolve():
        raise AttributionStopError(
            "code_or_authority_mismatch",
            f"prior CLI helper origin {old_cli_file} != {(REPO_ROOT / OLD_CLI_REL_PATH).resolve()}",
        )

    bindings: list[dict[str, str]] = []
    for rel_path, role in CODE_BINDING_SPECS:
        abs_p = REPO_ROOT / rel_path
        _reject_symlink_chain_strict(abs_p, cause="code_or_authority_mismatch", label=rel_path)
        if not abs_p.is_file():
            raise AttributionStopError("code_or_authority_mismatch", f"missing bound code file: {abs_p}")
        sha = _stream_sha256_strict(abs_p, missing_cause="code_or_authority_mismatch")
        if rel_path == CORE_REL_PATH and sha.lower() != EXPECTED_CORE_SHA256.lower():
            raise AttributionStopError(
                "code_or_authority_mismatch",
                f"{CORE_REL_PATH} SHA {sha} != frozen {EXPECTED_CORE_SHA256}",
            )
        if rel_path == OLD_CLI_REL_PATH and sha.lower() != EXPECTED_OLD_CLI_SHA256.lower():
            raise AttributionStopError(
                "code_or_authority_mismatch",
                f"{OLD_CLI_REL_PATH} SHA {sha} != frozen {EXPECTED_OLD_CLI_SHA256}",
            )
        bindings.append({"path": rel_path, "role": role, "sha256": sha})
    return bindings


def _verify_confined_fixed_input(
    *,
    key: str,
    candidate_path: Path,
    expected_path: Path,
    expected_sha: str,
) -> tuple[str, Path, tuple[int, int]]:
    if candidate_path != expected_path:
        raise AttributionStopError(
            "path_mismatch",
            f"{key} path {candidate_path} != frozen path {expected_path}",
        )
    _reject_symlink_chain_strict(candidate_path, cause="path_mismatch", label=key)
    resolved_cand = candidate_path.resolve()
    if resolved_cand != _expected_canonical_path(expected_path):
        raise AttributionStopError(
            "path_mismatch",
            f"{key} resolved path {resolved_cand} != canonical {_expected_canonical_path(expected_path)}",
        )

    confining_root: Path | None = None
    if key in ("r_members_jsonl", "r_summary_json"):
        confining_root = EXPECTED_R_ROOT
    elif key in ("u_ledger_jsonl", "u_summary_json"):
        confining_root = EXPECTED_U_ROOT

    if confining_root is not None:
        _reject_symlink_chain_strict(confining_root, cause="path_mismatch", label=f"{key}_root")
        if not confining_root.is_dir():
            raise AttributionStopError("path_mismatch", f"confining root is not directory: {confining_root}")
        resolved_root = confining_root.resolve()
        if resolved_root != _expected_canonical_path(confining_root):
            raise AttributionStopError(
                "path_mismatch",
                f"confining root resolved {resolved_root} != canonical {_expected_canonical_path(confining_root)}",
            )
        try:
            rel_sub = expected_path.relative_to(confining_root)
        except ValueError as exc:
            raise AttributionStopError("path_mismatch", f"{key} outside confining root {confining_root}") from exc
        if not resolved_cand.is_relative_to(resolved_root) or resolved_cand != (resolved_root / rel_sub):
            raise AttributionStopError("path_mismatch", f"{key} resolved path escaped confining root")
    else:
        parent_dir = expected_path.parent
        _reject_symlink_chain_strict(parent_dir, cause="path_mismatch", label=f"{key}_parent")
        if not parent_dir.is_dir() or parent_dir.resolve() != _expected_canonical_path(parent_dir):
            raise AttributionStopError("path_mismatch", f"{key} parent directory invalid: {parent_dir}")

    if not candidate_path.is_file():
        raise AttributionStopError("hash_mismatch", f"{key} missing regular file: {candidate_path}")
    st = candidate_path.lstat()
    actual_sha = _stream_sha256_strict(candidate_path, missing_cause="hash_mismatch")
    if actual_sha.lower() != expected_sha.lower():
        raise AttributionStopError(
            "hash_mismatch",
            f"{key} SHA-256 {actual_sha} != expected {expected_sha}",
        )
    return actual_sha, resolved_cand, (int(st.st_dev), int(st.st_ino))


def _validate_new_output_root(output_root: Path, allowed_parent: Path) -> None:
    if not output_root.is_absolute() or ".." in output_root.parts:
        raise AttributionStopError("path_mismatch", f"output_root must be clean absolute path: {output_root}")
    if output_root.parent != allowed_parent or not output_root.name.strip():
        raise AttributionStopError(
            "path_mismatch",
            f"output_root {output_root} must be a direct child of {allowed_parent}",
        )
    _reject_symlink_chain_strict(allowed_parent, cause="path_mismatch", label="allowed_output_parent")
    if output_root.is_symlink():
        raise AttributionStopError("path_mismatch", f"output_root must not be symlink: {output_root}")
    if allowed_parent.exists() and not allowed_parent.is_dir():
        raise AttributionStopError("path_mismatch", f"allowed_parent is not a directory: {allowed_parent}")
    resolved_parent = allowed_parent.resolve()
    resolved_out = output_root.resolve()
    if resolved_out.parent != resolved_parent or not resolved_out.is_relative_to(resolved_parent):
        raise AttributionStopError(
            "path_mismatch",
            f"resolved output_root {resolved_out} escaped allowed_parent {resolved_parent}",
        )
    if output_root.exists():
        raise AttributionStopError("output_not_new", f"output_root already exists: {output_root}")


def _validate_binding_payload(
    binding: Any,
    *,
    expected_plan_sha: str | None,
) -> tuple[dict[str, Any], Path, dict[str, tuple[Path, tuple[int, int]]]]:
    if not isinstance(binding, dict):
        raise AttributionStopError("code_or_authority_mismatch", "source_binding root must be object")
    if _req_int(binding, "binding_version", "code_or_authority_mismatch", "binding") != 1:
        raise AttributionStopError("code_or_authority_mismatch", "unsupported binding_version")
    if (
        _req_str(binding, "note", "code_or_authority_mismatch", "binding")
        != "provenance_record_only_not_execution_authorization"
    ):
        raise AttributionStopError("code_or_authority_mismatch", "invalid binding note")

    if "authority" not in binding or not isinstance(binding["authority"], dict):
        raise AttributionStopError("code_or_authority_mismatch", "missing authority object")
    auth = binding["authority"]
    if _req_str(auth, "repo_root", "code_or_authority_mismatch", "authority") != str(REPO_ROOT):
        raise AttributionStopError("code_or_authority_mismatch", "repo_root mismatch")
    if _req_str(auth, "design_path", "code_or_authority_mismatch", "authority") != DESIGN_REL_PATH:
        raise AttributionStopError("code_or_authority_mismatch", "design_path mismatch")
    design_sha = _req_str(auth, "design_sha256", "code_or_authority_mismatch", "authority")
    if design_sha.lower() != EXPECTED_DESIGN_SHA256.lower():
        raise AttributionStopError("code_or_authority_mismatch", "design_sha256 mismatch")
    _reject_symlink_chain_strict(
        REPO_ROOT / DESIGN_REL_PATH, cause="code_or_authority_mismatch", label="design_path"
    )
    if (
        _stream_sha256_strict(REPO_ROOT / DESIGN_REL_PATH, missing_cause="code_or_authority_mismatch").lower()
        != design_sha.lower()
    ):
        raise AttributionStopError("code_or_authority_mismatch", "on-disk Design SHA-256 mismatch")

    if _req_str(auth, "plan_path", "code_or_authority_mismatch", "authority") != PLAN_REL_PATH:
        raise AttributionStopError("code_or_authority_mismatch", "plan_path mismatch")
    plan_sha = _req_str(auth, "plan_sha256", "code_or_authority_mismatch", "authority")
    if expected_plan_sha is not None and plan_sha.lower() != expected_plan_sha.lower():
        raise AttributionStopError("code_or_authority_mismatch", "plan_sha256 != approved-plan-sha")
    _reject_symlink_chain_strict(REPO_ROOT / PLAN_REL_PATH, cause="code_or_authority_mismatch", label="plan_path")
    if (
        _stream_sha256_strict(REPO_ROOT / PLAN_REL_PATH, missing_cause="code_or_authority_mismatch").lower()
        != plan_sha.lower()
    ):
        raise AttributionStopError("code_or_authority_mismatch", "on-disk Plan SHA-256 mismatch")
    if _req_str(auth, "git_head", "code_or_authority_mismatch", "authority") != _git_head(REPO_ROOT):
        raise AttributionStopError("code_or_authority_mismatch", "git_head mismatch against repository HEAD")

    if "environment" not in binding or not isinstance(binding["environment"], dict):
        raise AttributionStopError("code_or_authority_mismatch", "missing environment object")
    env = binding["environment"]
    if _req_str(env, "python_executable", "code_or_authority_mismatch", "environment") != str(
        Path(sys.executable).resolve()
    ):
        raise AttributionStopError("code_or_authority_mismatch", "python_executable mismatch")
    if _req_str(env, "python_version", "code_or_authority_mismatch", "environment") != platform.python_version():
        raise AttributionStopError("code_or_authority_mismatch", "python_version mismatch")
    if _req_str(env, "core_module_file", "code_or_authority_mismatch", "environment") != str(
        Path(str(diag_mod.__file__)).resolve()
    ):
        raise AttributionStopError("code_or_authority_mismatch", "core_module_file mismatch")
    if _req_str(env, "prior_cli_module_file", "code_or_authority_mismatch", "environment") != str(
        Path(str(old_cli_mod.__file__)).resolve()
    ):
        raise AttributionStopError("code_or_authority_mismatch", "prior_cli_module_file mismatch")

    _verify_safety_strict()
    if "protocol" not in binding or not isinstance(binding["protocol"], dict):
        raise AttributionStopError("protocol_mismatch", "missing protocol object in binding")
    proto = _validate_protocol_strict(binding["protocol"])

    actual_code = _verify_helper_origins_and_code_bindings()
    if "code_bindings" not in binding or binding["code_bindings"] != actual_code:
        raise AttributionStopError(
            "code_or_authority_mismatch",
            "code_bindings mismatch against on-disk implementation/helper/config files",
        )

    if "fixed_inputs" not in binding or not isinstance(binding["fixed_inputs"], dict):
        raise AttributionStopError("reference_mismatch", "missing fixed_inputs object in binding")
    fi = binding["fixed_inputs"]
    if set(fi.keys()) != set(FIXED_INPUT_SPECS.keys()):
        raise AttributionStopError("reference_mismatch", "fixed_inputs key set mismatch")

    input_snapshots: dict[str, tuple[Path, tuple[int, int]]] = {}
    for k, (exp_p, exp_sha) in FIXED_INPUT_SPECS.items():
        entry = fi[k]
        if not isinstance(entry, dict):
            raise AttributionStopError("reference_mismatch", f"fixed_inputs.{k} must be object")
        raw_p_str = _req_str(entry, "path", "path_mismatch", f"fixed_inputs.{k}")
        if raw_p_str != str(exp_p):
            raise AttributionStopError("path_mismatch", f"fixed_inputs.{k}.path {raw_p_str!r} != {str(exp_p)!r}")
        rec_sha = _req_str(entry, "sha256", "hash_mismatch", f"fixed_inputs.{k}")
        if rec_sha.lower() != exp_sha.lower():
            raise AttributionStopError("hash_mismatch", f"fixed_inputs.{k} recorded sha256 mismatch")
        _v_sha, res_p, dev_ino = _verify_confined_fixed_input(
            key=k,
            candidate_path=Path(raw_p_str),
            expected_path=exp_p,
            expected_sha=exp_sha,
        )
        input_snapshots[k] = (res_p, dev_ino)

    r_st = EXPECTED_R_ROOT.lstat()
    u_st = EXPECTED_U_ROOT.lstat()
    ob_parent = FIXED_INPUT_SPECS["old_source_binding_json"][0].parent
    obp_st = ob_parent.lstat()
    input_snapshots["__r_root__"] = (EXPECTED_R_ROOT.resolve(), (int(r_st.st_dev), int(r_st.st_ino)))
    input_snapshots["__u_root__"] = (EXPECTED_U_ROOT.resolve(), (int(u_st.st_dev), int(u_st.st_ino)))
    input_snapshots["__old_binding_parent__"] = (ob_parent.resolve(), (int(obp_st.st_dev), int(obp_st.st_ino)))

    if "output" not in binding or not isinstance(binding["output"], dict):
        raise AttributionStopError("path_mismatch", "missing output object in binding")
    out_raw = _req_str(binding["output"], "output_root", "path_mismatch", "output")
    out_root = Path(out_raw)
    _validate_new_output_root(out_root, ALLOWED_OUTPUT_PARENT)
    return proto, out_root, input_snapshots


def _verify_binding_file_identity(binding_path: Path, expected_bsha: str) -> tuple[str, Path, tuple[int, int]]:
    _reject_symlink_chain_strict(binding_path, cause="path_mismatch", label="binding_path")
    resolved_b = binding_path.resolve()
    if resolved_b != _expected_canonical_path(binding_path):
        raise AttributionStopError(
            "path_mismatch",
            f"binding_path resolved {resolved_b} != canonical {_expected_canonical_path(binding_path)}",
        )
    if not binding_path.is_file():
        raise AttributionStopError("hash_mismatch", f"missing regular binding file: {binding_path}")
    bst = binding_path.lstat()
    actual_bsha = _stream_sha256_strict(binding_path, missing_cause="hash_mismatch")
    if actual_bsha.lower() != expected_bsha.lower():
        raise AttributionStopError(
            "hash_mismatch",
            f"binding SHA-256 {actual_bsha} != --binding-sha {expected_bsha}",
        )
    return actual_bsha, resolved_b, (int(bst.st_dev), int(bst.st_ino))


def _cmd_prepare(args: argparse.Namespace) -> int:
    binding_out = Path(args.binding_output)
    output_root = Path(args.output_root)

    if not binding_out.is_absolute() or ".." in binding_out.parts:
        raise AttributionStopError("path_mismatch", f"binding_output must be clean absolute path: {binding_out}")
    if binding_out.is_symlink():
        raise AttributionStopError("path_mismatch", f"binding_output must not be symlink: {binding_out}")
    if binding_out.exists():
        raise AttributionStopError("output_not_new", f"binding_output already exists: {binding_out}")
    _reject_symlink_chain_strict(binding_out, cause="path_mismatch", label="binding_output")
    resolved_bout = binding_out.resolve()
    for forbidden_root in (REPO_ROOT, EXPECTED_R_ROOT, EXPECTED_U_ROOT, ALLOWED_OUTPUT_PARENT):
        if forbidden_root.exists() and resolved_bout.is_relative_to(forbidden_root.resolve()):
            raise AttributionStopError(
                "path_mismatch",
                f"binding_output {binding_out} must not reside inside {forbidden_root}",
            )
    _validate_new_output_root(output_root, ALLOWED_OUTPUT_PARENT)

    _verify_safety_strict()
    proto = build_default_protocol()

    _reject_symlink_chain_strict(REPO_ROOT / DESIGN_REL_PATH, cause="code_or_authority_mismatch", label="design_path")
    design_sha = _stream_sha256_strict(REPO_ROOT / DESIGN_REL_PATH, missing_cause="code_or_authority_mismatch")
    if design_sha.lower() != EXPECTED_DESIGN_SHA256.lower():
        raise AttributionStopError("code_or_authority_mismatch", "Design SHA-256 mismatch on disk")

    _reject_symlink_chain_strict(REPO_ROOT / PLAN_REL_PATH, cause="code_or_authority_mismatch", label="plan_path")
    plan_sha = _stream_sha256_strict(REPO_ROOT / PLAN_REL_PATH, missing_cause="code_or_authority_mismatch")
    if plan_sha.lower() != str(args.approved_plan_sha).strip().lower():
        raise AttributionStopError(
            "code_or_authority_mismatch",
            f"Plan SHA-256 {plan_sha} != --approved-plan-sha {args.approved_plan_sha}",
        )

    code_bindings = _verify_helper_origins_and_code_bindings()

    # Stream byte digests ONLY of the 5 fixed inputs (NEVER JSON-parse any of the 5 inputs in prepare!)
    fixed_inputs_out: dict[str, dict[str, str]] = {}
    for k, (exp_p, exp_sha) in FIXED_INPUT_SPECS.items():
        verified_sha, _res_p, _dev_ino = _verify_confined_fixed_input(
            key=k,
            candidate_path=exp_p,
            expected_path=exp_p,
            expected_sha=exp_sha,
        )
        fixed_inputs_out[k] = {"path": str(exp_p), "sha256": verified_sha}

    payload: dict[str, Any] = {
        "binding_version": 1,
        "generated_at_utc": _utc_now(),
        "note": "provenance_record_only_not_execution_authorization",
        "authority": {
            "repo_root": str(REPO_ROOT),
            "design_path": DESIGN_REL_PATH,
            "design_sha256": design_sha,
            "plan_path": PLAN_REL_PATH,
            "plan_sha256": plan_sha,
            "git_head": _git_head(REPO_ROOT),
        },
        "environment": {
            "python_executable": str(Path(sys.executable).resolve()),
            "python_version": platform.python_version(),
            "core_module_file": str(Path(str(diag_mod.__file__)).resolve()),
            "prior_cli_module_file": str(Path(str(old_cli_mod.__file__)).resolve()),
        },
        "protocol": proto,
        "code_bindings": code_bindings,
        "fixed_inputs": fixed_inputs_out,
        "output": {
            "output_root": str(output_root),
        },
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    binding_out.parent.mkdir(parents=True, exist_ok=True)
    binding_out.write_text(text, encoding="utf-8")

    written_parsed = _loads_strict_json(
        binding_out.read_text(encoding="utf-8"),
        syntax_cause="code_or_authority_mismatch",
        ctx="source_binding",
    )
    _validate_binding_payload(written_parsed, expected_plan_sha=str(args.approved_plan_sha).strip())
    b_sha = _stream_sha256_strict(binding_out, missing_cause="code_or_authority_mismatch")
    print(f"PREPARED_BINDING={binding_out} SHA256={b_sha}")
    return 0


def _validate_five_input_cross_references(
    *,
    old_binding_obj: Any,
    r_summary_obj: Any,
    u_summary_obj: Any,
    protocol: dict[str, Any],
) -> dict[str, dict[str, int]]:
    if (
        not isinstance(old_binding_obj, dict)
        or not isinstance(r_summary_obj, dict)
        or not isinstance(u_summary_obj, dict)
    ):
        raise AttributionStopError("reference_mismatch", "old_binding / r_summary / u_summary must be JSON objects")

    # 1. Validate old_binding authority, protocol, output_root, and fixed_inputs (without opening coverage/manifest)
    if _req_int(old_binding_obj, "binding_version", "reference_mismatch", "old_binding") != 1:
        raise AttributionStopError("reference_mismatch", "old_binding binding_version != 1")
    if "authority" not in old_binding_obj or not isinstance(old_binding_obj["authority"], dict):
        raise AttributionStopError("reference_mismatch", "old_binding missing authority")
    ob_auth = old_binding_obj["authority"]
    if (
        _req_str(ob_auth, "design_path", "reference_mismatch", "old_binding.authority") != PRIOR_1125_DESIGN_REL_PATH
        or _req_str(ob_auth, "design_sha256", "reference_mismatch", "old_binding.authority").lower()
        != PRIOR_1125_DESIGN_SHA256.lower()
        or _req_str(ob_auth, "plan_path", "reference_mismatch", "old_binding.authority") != PRIOR_1125_PLAN_REL_PATH
        or _req_str(ob_auth, "plan_sha256", "reference_mismatch", "old_binding.authority").lower()
        != PRIOR_1125_PLAN_SHA256.lower()
    ):
        raise AttributionStopError("reference_mismatch", "old_binding 11-25 authority mismatch")
    if "protocol" not in old_binding_obj:
        raise AttributionStopError("protocol_mismatch", "old_binding missing protocol")
    _validate_protocol_strict(old_binding_obj["protocol"])

    if "output" not in old_binding_obj or not isinstance(old_binding_obj["output"], dict):
        raise AttributionStopError("reference_mismatch", "old_binding missing output")
    if _req_str(old_binding_obj["output"], "output_root", "reference_mismatch", "old_binding.output") != str(
        EXPECTED_R_ROOT
    ):
        raise AttributionStopError("reference_mismatch", "old_binding output_root != EXPECTED_R_ROOT")

    if "fixed_inputs" not in old_binding_obj or not isinstance(old_binding_obj["fixed_inputs"], dict):
        raise AttributionStopError("reference_mismatch", "old_binding missing fixed_inputs")
    ob_fi = old_binding_obj["fixed_inputs"]
    if set(ob_fi.keys()) != {"ledger_jsonl", "summary_json", "coverage_json", "source_manifest_json"}:
        raise AttributionStopError("reference_mismatch", "old_binding fixed_inputs keys mismatch")

    u_ledger_exp_p, u_ledger_exp_sha = FIXED_INPUT_SPECS["u_ledger_jsonl"]
    u_sum_exp_p, u_sum_exp_sha = FIXED_INPUT_SPECS["u_summary_json"]
    if (
        not isinstance(ob_fi["ledger_jsonl"], dict)
        or _req_str(ob_fi["ledger_jsonl"], "path", "reference_mismatch", "old_binding.ledger_jsonl")
        != str(u_ledger_exp_p)
        or _req_str(ob_fi["ledger_jsonl"], "sha256", "reference_mismatch", "old_binding.ledger_jsonl").lower()
        != u_ledger_exp_sha.lower()
    ):
        raise AttributionStopError("reference_mismatch", "old_binding ledger_jsonl reference mismatch")
    if (
        not isinstance(ob_fi["summary_json"], dict)
        or _req_str(ob_fi["summary_json"], "path", "reference_mismatch", "old_binding.summary_json")
        != str(u_sum_exp_p)
        or _req_str(ob_fi["summary_json"], "sha256", "reference_mismatch", "old_binding.summary_json").lower()
        != u_sum_exp_sha.lower()
    ):
        raise AttributionStopError("reference_mismatch", "old_binding summary_json reference mismatch")
    if not isinstance(ob_fi["source_manifest_json"], dict):
        raise AttributionStopError("reference_mismatch", "old_binding source_manifest_json must be object")
    expected_manifest_sha = _req_str(
        ob_fi["source_manifest_json"], "sha256", "reference_mismatch", "old_binding.source_manifest_json"
    )

    # 2. Validate R/summary.json cross-references and counts
    _ob_p, ob_expected_sha = FIXED_INPUT_SPECS["old_source_binding_json"]
    r_bsha = _req_str(r_summary_obj, "source_binding_sha256", "reference_mismatch", "r_summary")
    if r_bsha.lower() != ob_expected_sha.lower():
        raise AttributionStopError(
            "reference_mismatch",
            f"r_summary source_binding_sha256 {r_bsha} != old_source_binding {ob_expected_sha}",
        )
    if "fixed_inputs" not in r_summary_obj or r_summary_obj["fixed_inputs"] != ob_fi:
        raise AttributionStopError("reference_mismatch", "r_summary fixed_inputs != old_binding fixed_inputs")
    if "protocol" not in r_summary_obj:
        raise AttributionStopError("protocol_mismatch", "r_summary missing protocol")
    _validate_protocol_strict(r_summary_obj["protocol"])
    if "counts" not in r_summary_obj or not isinstance(r_summary_obj["counts"], dict):
        raise AttributionStopError("cohort_mismatch", "r_summary missing counts")
    rc = r_summary_obj["counts"]
    if (
        _req_int(rc, "q_total", "cohort_mismatch", "r_summary.counts") != int(EXPECTED_COUNTS["q_total"])
        or _req_int(rc, "joint_all_count", "cohort_mismatch", "r_summary.counts")
        != int(EXPECTED_COUNTS["j_joint_total"])
        or _req_int(rc, "b_only_all_count", "cohort_mismatch", "r_summary.counts")
        != int(EXPECTED_COUNTS["b_only_total"])
    ):
        raise AttributionStopError("cohort_mismatch", "r_summary counts != EXPECTED_COUNTS")

    # 3. Validate U/results/summary.json manifest reference, 11-24 authority, protocol, and decision counts
    u_msha = _req_str(u_summary_obj, "manifest_sha256", "reference_mismatch", "u_summary")
    if u_msha.lower() != expected_manifest_sha.lower():
        raise AttributionStopError(
            "reference_mismatch",
            f"u_summary manifest_sha256 {u_msha} != old_binding manifest sha {expected_manifest_sha}",
        )
    if "authority" not in u_summary_obj or not isinstance(u_summary_obj["authority"], dict):
        raise AttributionStopError("reference_mismatch", "u_summary missing authority")
    ua = u_summary_obj["authority"]
    if (
        _req_str(ua, "design_path", "reference_mismatch", "u_summary.authority") != PRIOR_1124_DESIGN_REL_PATH
        or _req_str(ua, "design_sha256", "reference_mismatch", "u_summary.authority").lower()
        != PRIOR_1124_DESIGN_SHA256.lower()
        or _req_str(ua, "plan_path", "reference_mismatch", "u_summary.authority") != PRIOR_1124_PLAN_REL_PATH
        or _req_str(ua, "plan_sha256", "reference_mismatch", "u_summary.authority").lower()
        != PRIOR_1124_PLAN_SHA256.lower()
    ):
        raise AttributionStopError("reference_mismatch", "u_summary 11-24 authority mismatch")
    if "protocol" not in u_summary_obj:
        raise AttributionStopError("protocol_mismatch", "u_summary missing protocol")
    _validate_protocol_strict(u_summary_obj["protocol"])

    if "candidates" not in u_summary_obj or not isinstance(u_summary_obj["candidates"], dict):
        raise AttributionStopError("cohort_mismatch", "u_summary missing candidates")
    dp_per_sym = (int(protocol["eval_end_ms"]) - int(protocol["eval_start_ms"])) // int(protocol["bar_interval_ms"])
    expected_dp_total_by_cand = {
        CAND_A: len(protocol["symbols"]) * dp_per_sym,
        CAND_B: (len(protocol["symbols"]) - 1) * dp_per_sym,
    }
    expected_dp_counts: dict[str, dict[str, int]] = {}
    for cand in (CAND_A, CAND_B):
        if cand not in u_summary_obj["candidates"] or not isinstance(u_summary_obj["candidates"][cand], dict):
            raise AttributionStopError("cohort_mismatch", f"u_summary missing candidate {cand}")
        cand_obj = u_summary_obj["candidates"][cand]
        if "counts" not in cand_obj or not isinstance(cand_obj["counts"], dict):
            raise AttributionStopError("cohort_mismatch", f"u_summary.{cand} missing counts")
        c_counts = cand_obj["counts"]
        st_map = {
            st: _req_int(c_counts, st, "cohort_mismatch", f"u_summary.{cand}.counts")
            for st in ALLOWED_ROW_STATUSES
        }
        tot_dp = _req_int(c_counts, "total_eval_decision_points", "cohort_mismatch", f"u_summary.{cand}.counts")
        if sum(st_map.values()) != tot_dp or tot_dp != expected_dp_total_by_cand[cand]:
            raise AttributionStopError("cohort_mismatch", f"u_summary.{cand} decision-point denominator mismatch")
        expected_dp_counts[cand] = st_map
    return expected_dp_counts


def _validate_and_reconcile_ledger_and_members(
    *,
    ledger_rows: list[dict[str, Any]],
    member_rows: list[dict[str, Any]],
    expected_dp_counts: dict[str, dict[str, int]],
    protocol: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_symbols = list(protocol["symbols"])
    target_symbols = [s for s in all_symbols if s != "BTCUSDT"]
    all_symbols_set = set(all_symbols)
    target_symbols_set = set(target_symbols)
    eval_start_ms = int(protocol["eval_start_ms"])
    eval_end_ms = int(protocol["eval_end_ms"])
    lag_ms = int(protocol["configured_data_lag_ms"])
    interval_ms = int(protocol["bar_interval_ms"])
    entry_delay_bars = int(protocol["entry_delay_bars"])
    lookback_ms = int(protocol["one_hour_bar_count"]) * interval_ms
    horizon_ms = int(protocol["forward_4h_bar_count"]) * interval_ms
    block_ms = int(protocol["block_days"]) * 86_400_000
    num_blocks = int(protocol["block_count"])
    vol_thresh = float(protocol["volume_spike_threshold"])
    rs_thresh = float(protocol["rel_strength_z_threshold"])

    seen_ledger: dict[tuple[str, str, int], dict[str, Any]] = {}
    a_rows: list[dict[str, Any]] = []
    b_admitted_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    actual_dp_counts: dict[str, dict[str, int]] = {
        CAND_A: {st: 0 for st in ALLOWED_ROW_STATUSES},
        CAND_B: {st: 0 for st in ALLOWED_ROW_STATUSES},
    }

    for raw_r in ledger_rows:
        if not isinstance(raw_r, dict):
            raise AttributionStopError("cohort_mismatch", "ledger row must be dict")
        _check_any_nonfinite_numbers(raw_r, "ledger_row")
        cand = _req_str(raw_r, "candidate", "cohort_mismatch", "ledger_row")
        if cand not in ALLOWED_CANDIDATES:
            raise AttributionStopError("cohort_mismatch", f"unknown candidate {cand!r} in ledger")
        sym = _req_str(raw_r, "symbol", "cohort_mismatch", f"ledger[{cand}]")
        allowed_s = all_symbols_set if cand == CAND_A else target_symbols_set
        if sym not in allowed_s:
            raise AttributionStopError("cohort_mismatch", f"invalid symbol {sym!r} for {cand}")
        avail_ms = _req_int(raw_r, "available_at_ms", "time_or_price_mismatch", f"ledger[{cand},{sym}]")
        ctx = f"ledger[{cand},{sym},{avail_ms}]"
        if not (eval_start_ms <= avail_ms < eval_end_ms):
            raise AttributionStopError("time_or_price_mismatch", f"{ctx} available_at_ms outside eval range")
        win_end_ms = _req_int(raw_r, "window_end_ms", "time_or_price_mismatch", ctx)
        if avail_ms != win_end_ms + lag_ms or win_end_ms % interval_ms != 0:
            raise AttributionStopError("time_or_price_mismatch", f"{ctx} window_end_ms/lag misaligned")
        win_start_ms = _opt_int(raw_r, "window_start_ms", "time_or_price_mismatch", ctx)
        if win_start_ms is not None and (win_end_ms - win_start_ms) != lookback_ms:
            raise AttributionStopError("time_or_price_mismatch", f"{ctx} window_start_ms misaligned")
        blk_id = _req_int(raw_r, "block_id", "time_or_price_mismatch", ctx)
        exp_blk = (avail_ms - eval_start_ms) // block_ms
        if blk_id != exp_blk or not (0 <= blk_id < num_blocks):
            raise AttributionStopError("time_or_price_mismatch", f"{ctx} block_id mismatch")
        blk_end_ms = eval_start_ms + (blk_id + 1) * block_ms

        status = _req_str(raw_r, "status", "cohort_mismatch", ctx)
        if status not in ALLOWED_ROW_STATUSES:
            raise AttributionStopError("cohort_mismatch", f"{ctx} unknown status {status!r}")
        trig_val = _opt_finite_float(raw_r, "trigger_value", "cohort_mismatch", ctx)
        min_th = vol_thresh if cand == CAND_A else rs_thresh
        if status in ("admitted", "overlap_suppressed"):
            if win_start_ms is None or trig_val is None or trig_val < min_th:
                raise AttributionStopError("cohort_mismatch", f"{ctx} triggered row missing threshold/window")
        else:
            if status == "not_triggered" and win_start_ms is None:
                raise AttributionStopError("cohort_mismatch", f"{ctx} not_triggered missing window_start_ms")
            if trig_val is not None:
                raise AttributionStopError("cohort_mismatch", f"{ctx} non-triggered row has trigger_value")

        if cand == CAND_B and status == "admitted":
            ent_ms = _req_int(raw_r, "entry_bar_start_ms", "time_or_price_mismatch", ctx)
            ext_ms = _req_int(raw_r, "exit_bar_end_ms", "time_or_price_mismatch", ctx)
            exp_ent = win_end_ms + entry_delay_bars * interval_ms
            if ent_ms != exp_ent or ent_ms <= avail_ms or (ext_ms - ent_ms) != horizon_ms or ext_ms > blk_end_ms:
                raise AttributionStopError("time_or_price_mismatch", f"{ctx} admitted B entry/exit invalid")
            eo = _req_finite_float(raw_r, "entry_open_price", "time_or_price_mismatch", ctx)
            ec = _req_finite_float(raw_r, "exit_close_price", "time_or_price_mismatch", ctx)
            yg = _req_finite_float(raw_r, "y_gross_bps", "time_or_price_mismatch", ctx)
            mae = _req_finite_float(raw_r, "mae_4h_bps", "time_or_price_mismatch", ctx)
            mfe = _req_finite_float(raw_r, "mfe_4h_bps", "time_or_price_mismatch", ctx)
            if eo <= 0.0 or ec <= 0.0 or abs(yg - 10000.0 * (ec / eo - 1.0)) > 1e-6:
                raise AttributionStopError("time_or_price_mismatch", f"{ctx} admitted B price/return formula mismatch")
            if mae > min(0.0, yg) + 1e-6 or mfe < max(0.0, yg) - 1e-6:
                raise AttributionStopError("time_or_price_mismatch", f"{ctx} admitted B MAE/MFE envelope mismatch")

        lkey = (cand, sym, avail_ms)
        if lkey in seen_ledger:
            raise AttributionStopError("duplicate_key", f"duplicate ledger key {lkey!r}")
        seen_ledger[lkey] = raw_r
        actual_dp_counts[cand][status] += 1
        if cand == CAND_A:
            a_rows.append(raw_r)
        elif status == "admitted":
            b_admitted_by_key[lkey] = raw_r

    for cand in (CAND_A, CAND_B):
        if actual_dp_counts[cand] != expected_dp_counts[cand]:
            raise AttributionStopError("cohort_mismatch", f"{cand} ledger status counts != u_summary")

    # Verify non-overlapping B admitted events per symbol
    for sym in target_symbols:
        sym_b = sorted(
            [r for (c, s, _), r in b_admitted_by_key.items() if c == CAND_B and s == sym],
            key=lambda x: int(x["available_at_ms"]),
        )
        prev_exit: int | None = None
        for br in sym_b:
            if prev_exit is not None and int(br["available_at_ms"]) <= prev_exit:
                raise AttributionStopError("time_or_price_mismatch", f"overlapping B admitted on {sym}")
            prev_exit = int(br["exit_bar_end_ms"])

    # Validate members.jsonl and reconcile 1-to-1 with B admitted rows & paired A rows
    validated_members: list[dict[str, Any]] = []
    member_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for raw_m in member_rows:
        mkey, vm = _validate_member_row(
            raw_m,
            target_symbols_set=target_symbols_set,
            eval_start_ms=eval_start_ms,
            eval_end_ms=eval_end_ms,
            lag_ms=lag_ms,
            interval_ms=interval_ms,
            entry_delay_bars=entry_delay_bars,
            lookback_ms=lookback_ms,
            horizon_ms=horizon_ms,
            block_ms=block_ms,
            num_blocks=num_blocks,
            vol_thresh=vol_thresh,
        )
        if mkey in member_by_key:
            raise AttributionStopError("duplicate_key", f"duplicate member key {mkey!r}")
        member_by_key[mkey] = vm
        validated_members.append(vm)

    if set(member_by_key.keys()) != set(b_admitted_by_key.keys()) or len(validated_members) != len(b_admitted_by_key):
        raise AttributionStopError("cohort_mismatch", "members.jsonl key set != ledger B admitted key set")

    for mkey, vm in member_by_key.items():
        brow = b_admitted_by_key[mkey]
        for int_col in ("block_id", "window_start_ms", "window_end_ms", "entry_bar_start_ms", "exit_bar_end_ms"):
            if int(vm[int_col]) != int(brow[int_col]):
                raise AttributionStopError("time_or_price_mismatch", f"{mkey!r} {int_col} disagrees with ledger B row")
        for price_col in ("entry_open_price", "exit_close_price", "y_gross_bps", "mfe_4h_bps", "mae_4h_bps"):
            if abs(float(vm[price_col]) - float(brow[price_col])) > 1e-9:
                raise AttributionStopError("time_or_price_mismatch", f"{mkey!r} {price_col} disagrees with ledger B row")
        if (
            abs(float(vm["self_r1h"]) - float(brow["self_r1h"])) > 1e-9
            or abs(float(vm["btc_r1h"]) - float(brow["btc_r1h"])) > 1e-9
            or abs(float(vm["b_trigger_value"]) - float(brow["trigger_value"])) > 1e-9
        ):
            raise AttributionStopError("cohort_mismatch", f"{mkey!r} feature/trigger disagrees with ledger B row")

        akey = (CAND_A, mkey[1], mkey[2])
        if akey not in seen_ledger:
            raise AttributionStopError("cohort_mismatch", f"missing paired A row {akey!r} in ledger")
        arow = seen_ledger[akey]
        if (
            int(arow["window_end_ms"]) != int(vm["window_end_ms"])
            or int(arow["available_at_ms"]) != int(vm["available_at_ms"])
        ):
            raise AttributionStopError("time_or_price_mismatch", f"{akey!r} A row time disagrees with member")
        a_st = str(arow["status"])
        a_tv = arow["trigger_value"]
        if vm["a_status"] != a_st:
            raise AttributionStopError("cohort_mismatch", f"{mkey!r} a_status != ledger A status")
        if (vm["a_trigger_value"] is None) != (a_tv is None) or (
            a_tv is not None and abs(float(vm["a_trigger_value"]) - float(a_tv)) > 1e-9
        ):
            raise AttributionStopError("cohort_mismatch", f"{mkey!r} a_trigger_value != ledger A trigger_value")

    return a_rows, validated_members


def _render_report_markdown(summary: dict[str, Any], binding_sha: str, output_root: Path) -> str:
    def f4(x: float | None) -> str:
        return "null" if x is None else f"{x:.4f}"

    def fpct(x: float | None) -> str:
        return "null" if x is None else f"{x * 100.0:.2f}%"

    cnt = summary["counts"]
    cov = summary["coverage"]
    fw = summary["focus_week"]
    rt = summary["routing"]

    lines: list[str] = [
        "# Stage 1.3 跨币放量广度与特殊周贡献归因探索报告（`report_CN.md`）",
        "",
        f"- **生成时间（UTC）**：`{summary['generated_at_utc']}`",
        f"- **输出目录（`output_root`）**：`{output_root}`",
        f"- **绑定 `source_binding.json` SHA-256**：`{binding_sha}`",
        f"- **执行状态**：`{summary['execution_status']}`",
        f"- **结论与分流**：`conclusion = {rt['conclusion']}`，"
        f"`observation_label = {rt['observation_label']}`，"
        f"`resource_decision = {rt['resource_decision']}`，"
        f"`alpha_research_status = {rt['alpha_research_status']}`",
        "- **治理与先验暴露声明**：",
        f"  - `{summary['prior_exposure_disclosure']}`",
        "  - `cost_mode = cost_context_only`，`minimum_economically_meaningful_gain = null`，"
        "`live_trading_enabled = false`，`paper_trading_allowed = false`，`execution_engine_allowed = false`，"
        "`independent_out_of_sample_claim_allowed = false`。",
        "  - 本报告仅对固定 `J`（`N=155`）做因果时间窗 `(t-3600000, t]` 其他三币放量广度 `G in {0,1,2,3}` 描述及 `block_id=9` 原事件透传；"
        "**不挑选最佳 G 级别、不合并门槛、不声称边际/因果效应、不产生交易规则或样本外验证声明**。",
        "",
        "## 1. 固定分母与广度可构造性（Constructibility）",
        "",
        f"- **固定队列核对**：`N(Q) = {cnt['q_total']}` = 原共振 `N(J) = {cnt['j_joint_total']}` + 原仅走强 `{cnt['b_only_total']}`",
        f"- **广度覆盖**：`all_g_estimable = {cov['all_g_estimable']}`，已知 `G` `{cov['known_g_count']}` / 未知 `G` `{cov['unknown_g_count']}`",
        f"- **广度计数**：`G=0: {cnt['breadth_counts']['0']}`，`G=1: {cnt['breadth_counts']['1']}`，"
        f"`G=2: {cnt['breadth_counts']['2']}`，`G=3: {cnt['breadth_counts']['3']}`，`unknown: {cnt['breadth_counts']['unknown']}`",
        f"- **逐槽位缺口原因计数**：`{json.dumps(cov['slot_gap_counts_by_reason'], ensure_ascii=False)}`",
    ]

    if cov["unknown_targets"]:
        lines.extend(["", "### 1.1 未知广度目标缺口明细", ""])
        for ug in cov["unknown_targets"]:
            lines.append(
                f"- 目标 `{ug['target_key']}`：`H={json.dumps(ug['h_by_symbol'], ensure_ascii=False)}`，"
                f"阻塞槽位数 `{len(ug['blocking_unknown_slots'])}`"
            )

    lines.extend(
        [
            "",
            f"## 2. 特殊周（`block_id=9`，`{fw['block_start_utc']} .. {fw['block_end_utc']}`）事件时间线与原对照透传",
            "",
            f"- **该周原计数**：`Q = {fw['q_count']}`（原共振 `{fw['joint_count']}`，原仅走强 `{fw['b_only_count']}`），"
            f"原共振 `sum_y = {f4(fw['joint_sum_y_bps'])} bps` / `mean_y = {f4(fw['joint_mean_y_bps'])} bps`",
            f"- **同周对照可比性限制**：`{fw['comparability_limitation']}`（原同币同周对照稀疏且不控制周内阶段混杂；下列 `conditional_d_bps` 仅为上轮原值透传，非本轮广度控制效应）。",
            "",
            "### 2.1 按 UTC 日汇总（Block 9）",
            "",
            "| UTC 日期 | `Q` | 原共振 `n` | 原共振 `sum_y` (bps) | 原共振 `mean_y` (bps) | 原 `b_only` `n` | 原 `b_only` `mean_y` (bps) |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for drow in fw["by_utc_date"]:
        lines.append(
            f"| `{drow['utc_date']}` | {drow['q_count']} | {drow['joint_count']} | {f4(drow['joint_sum_y_bps'])} | "
            f"{f4(drow['joint_mean_y_bps'])} | {drow['b_only_count']} | {f4(drow['b_only_mean_y_bps'])} |"
        )

    lines.extend(
        [
            "",
            "### 2.2 DOGE 原同周仅走强对照单列",
            "",
            "| UTC 日期 | `available_at_utc` | `b_trigger_value` | `y_gross_bps` | `mae_4h_bps` | `mfe_4h_bps` |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for dc in fw["doge_controls"]:
        lines.append(
            f"| `{dc['utc_date']}` | `{dc['available_at_utc']}` | {f4(dc['b_trigger_value'])} | "
            f"{f4(dc['y_gross_bps'])} | {f4(dc['mae_4h_bps'])} | {f4(dc['mfe_4h_bps'])} |"
        )

    lines.extend(
        [
            "",
            "### 2.3 Block 9 完整原 Q 时间线",
            "",
            "| `available_at_utc` | 币种 | 原分组 | `G` | `a_trigger` | `b_trigger` | `y_gross_bps` | `mae_4h_bps` | `mfe_4h_bps` | 原 `conditional_d_bps` |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for trow in fw["timeline"]:
        g_disp = "null" if trow["breadth_g"] is None else str(trow["breadth_g"])
        lines.append(
            f"| `{trow['available_at_utc']}` | `{trow['symbol']}` | `{trow['group']}` | {g_disp} | "
            f"{f4(trow['a_trigger_value'])} | {f4(trow['b_trigger_value'])} | {f4(trow['y_gross_bps'])} | "
            f"{f4(trow['mae_4h_bps'])} | {f4(trow['mfe_4h_bps'])} | {f4(trow['conditional_d_bps'])} |"
        )

    if not cov["all_g_estimable"]:
        lines.extend(
            [
                "",
                "## 3. 四级广度描述（因存在未知 `G` 按契约停止分组收益计算）",
                "",
                "- 至少一个固定目标 `G` 未知，按 Design §3.3 / §5 保留全部目标行与缺口，`full_sample / without_block_9 / per_symbol / per_block` 均为 `null`，结论为 `breadth_not_estimable / stop_due_to_evidence`。",
            ]
        )
        return "\n".join(lines) + "\n"

    for sec_title, tbl_key in (
        ("3. 全样本四级广度描述（`full_sample`）", "full_sample"),
        ("4. 剔除 `block_id=9` 后固定依赖诊断（`without_block_9`，非独立样本外）", "without_block_9"),
    ):
        tbl = summary[tbl_key]
        lines.extend(
            [
                "",
                f"## {sec_title}",
                "",
                "| `G` | `n` | 币种数 | 非空周块数 | `sum_y` | `mean` | `median` | `win_rate` | `avg_win` | `avg_loss` | `payoff` | `P10` | `P90` | `worst` | `MAE mean/P10/min` | `MFE mean/P90/max` | `cost 30/50/80 mean` |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
            ]
        )
        for g_str in ("0", "1", "2", "3"):
            d = tbl[g_str]
            q = d["quantiles_bps"]
            mae = d["mae_4h_gross_bps"]
            mfe = d["mfe_4h_gross_bps"]
            cs = d["cost_scenarios"]
            lines.append(
                f"| `{g_str}` | {d['n']} | {d['symbol_count']} | {d['non_empty_block_count']} | "
                f"{f4(d['sum_y_bps'])} | {f4(d['mean_bps'])} | {f4(d['median_bps'])} | {fpct(d['win_rate'])} | "
                f"{f4(d['avg_win_bps'])} | {f4(d['avg_loss_bps'])} | {f4(d['payoff_ratio'])} | "
                f"{f4(q['p10'])} | {f4(q['p90'])} | {f4(d['worst_event_bps'])} | "
                f"`{f4(mae['mean'])}/{f4(mae['p10'])}/{f4(mae['min'])}` | "
                f"`{f4(mfe['mean'])}/{f4(mfe['p90'])}/{f4(mfe['max'])}` | "
                f"`{f4(cs['30.0']['mean_bps'])}/{f4(cs['50.0']['mean_bps'])}/{f4(cs['80.0']['mean_bps'])}` |"
            )

    lines.extend(
        [
            "",
            "## 5. 每币 × 四级广度构成表（零单元保留）",
            "",
            "| 币种 | `total_n` | `G=0 (n / mean)` | `G=1 (n / mean)` | `G=2 (n / mean)` | `G=3 (n / mean)` |",
            "|---|---:|---|---|---|---|",
        ]
    )
    for sym, ps in summary["per_symbol"].items():
        bg = ps["by_g"]
        lines.append(
            f"| `{sym}` | {ps['total_n']} | "
            f"`{bg['0']['n']} / {f4(bg['0']['mean_bps'])}` | "
            f"`{bg['1']['n']} / {f4(bg['1']['mean_bps'])}` | "
            f"`{bg['2']['n']} / {f4(bg['2']['mean_bps'])}` | "
            f"`{bg['3']['n']} / {f4(bg['3']['mean_bps'])}` |"
        )

    lines.extend(
        [
            "",
            "## 6. 23 个 7d 市场块 × 四级广度构成表（零单元保留）",
            "",
            "| `block_id` | UTC 周区间 | `total_n` | `G=0 (n / mean)` | `G=1 (n / mean)` | `G=2 (n / mean)` | `G=3 (n / mean)` |",
            "|---:|---|---:|---|---|---|---|",
        ]
    )
    for pb in summary["per_block"]:
        bg = pb["by_g"]
        lines.append(
            f"| {pb['block_id']} | `{pb['block_start_utc'][:10]}..{pb['block_end_utc'][:10]}` | {pb['total_n']} | "
            f"`{bg['0']['n']} / {f4(bg['0']['mean_bps'])}` | "
            f"`{bg['1']['n']} / {f4(bg['1']['mean_bps'])}` | "
            f"`{bg['2']['n']} / {f4(bg['2']['mean_bps'])}` | "
            f"`{bg['3']['n']} / {f4(bg['3']['mean_bps'])}` |"
        )

    return "\n".join(lines) + "\n"


def _cmd_run(args: argparse.Namespace) -> int:
    binding_path = Path(args.binding)
    expected_bsha = str(args.binding_sha).strip()
    actual_bsha, pre_b_resolved, pre_b_dev_ino = _verify_binding_file_identity(binding_path, expected_bsha)

    binding_obj = _loads_strict_json(
        binding_path.read_text(encoding="utf-8"),
        syntax_cause="code_or_authority_mismatch",
        ctx="source_binding",
    )
    proto, output_root, pre_input_snapshots = _validate_binding_payload(binding_obj, expected_plan_sha=None)

    # Read ONLY the 5 fixed files (NEVER open coverage.json, source_manifest.json, or raw ZIPs)
    r_members_path, _ = FIXED_INPUT_SPECS["r_members_jsonl"]
    r_summary_path, _ = FIXED_INPUT_SPECS["r_summary_json"]
    u_ledger_path, _ = FIXED_INPUT_SPECS["u_ledger_jsonl"]
    u_summary_path, _ = FIXED_INPUT_SPECS["u_summary_json"]
    old_binding_path, _ = FIXED_INPUT_SPECS["old_source_binding_json"]

    old_binding_obj = _loads_strict_json(
        old_binding_path.read_text(encoding="utf-8"),
        syntax_cause="reference_mismatch",
        ctx="old_source_binding.json",
    )
    r_summary_obj = _loads_strict_json(
        r_summary_path.read_text(encoding="utf-8"),
        syntax_cause="reference_mismatch",
        ctx="r_summary.json",
    )
    u_summary_obj = _loads_strict_json(
        u_summary_path.read_text(encoding="utf-8"),
        syntax_cause="reference_mismatch",
        ctx="u_summary.json",
    )
    expected_dp_counts = _validate_five_input_cross_references(
        old_binding_obj=old_binding_obj,
        r_summary_obj=r_summary_obj,
        u_summary_obj=u_summary_obj,
        protocol=proto,
    )

    ledger_rows: list[dict[str, Any]] = []
    with u_ledger_path.open("r", encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, 1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            ledger_rows.append(
                _loads_strict_json(
                    stripped,
                    syntax_cause="cohort_mismatch",
                    ctx=f"u_ledger.jsonl:{line_no}",
                )
            )

    member_rows: list[dict[str, Any]] = []
    with r_members_path.open("r", encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, 1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            member_rows.append(
                _loads_strict_json(
                    stripped,
                    syntax_cause="cohort_mismatch",
                    ctx=f"r_members.jsonl:{line_no}",
                )
            )

    a_rows, validated_members = _validate_and_reconcile_ledger_and_members(
        ledger_rows=ledger_rows,
        member_rows=member_rows,
        expected_dp_counts=expected_dp_counts,
        protocol=proto,
    )

    # Step 1 of causal chain: pass ONLY J identity keys and A rows into annotate_breadth
    j_target_keys = [
        (m["candidate"], m["symbol"], int(m["available_at_ms"]))
        for m in validated_members
        if m["group"] == "joint"
    ]
    breadth = annotate_breadth(j_target_keys, a_rows, protocol=proto)

    # Step 2 of causal chain: pass original Q members and locked breadth into describe_attribution
    desc = describe_attribution(validated_members, breadth, protocol=proto)
    for cnt_key, exp_val in EXPECTED_COUNTS.items():
        if int(desc["counts"][cnt_key]) != int(exp_val):
            raise AttributionStopError(
                "cohort_mismatch",
                f"counts.{cnt_key}={desc['counts'][cnt_key]} != expected {exp_val}",
            )

    breadth_members = desc["breadth_members"]
    summary_out: dict[str, Any] = {
        "generated_at_utc": _utc_now(),
        "execution_status": "execution_completed_pending_independent_audit",
        "source_binding_sha256": actual_bsha.lower(),
        "authority": binding_obj["authority"],
        "fixed_inputs": {k: {"path": str(p), "sha256": s} for k, (p, s) in FIXED_INPUT_SPECS.items()},
        "protocol": proto,
        "target_symbols": [s for s in proto["symbols"] if s != "BTCUSDT"],
        "counts": desc["counts"],
        "coverage": desc["coverage"],
        "focus_week": desc["focus_week"],
        "full_sample": desc["full_sample"],
        "without_block_9": desc["without_block_9"],
        "per_symbol": desc["per_symbol"],
        "per_block": desc["per_block"],
        "cost_mode": desc["cost_mode"],
        "cost_scenarios_round_trip_bps": desc["cost_scenarios_round_trip_bps"],
        "minimum_economically_meaningful_gain": desc["minimum_economically_meaningful_gain"],
        "dependency_unit": desc["dependency_unit"],
        "prior_exposure_disclosure": desc["prior_exposure_disclosure"],
        "governance": desc["governance"],
        "routing": desc["routing"],
    }

    # Serialize all 3 artifacts in memory (rejecting NaN) BEFORE creating output_root
    bm_lines = [json.dumps(r, ensure_ascii=False, allow_nan=False) for r in breadth_members]
    bm_text = ("\n".join(bm_lines) + "\n") if bm_lines else ""
    report_text = _render_report_markdown(summary_out, actual_bsha.lower(), output_root)
    summary_text = json.dumps(summary_out, indent=2, ensure_ascii=False, allow_nan=False) + "\n"

    # Unified pre-publish full path, ancestor-symlink, inode, code, and SHA-256 re-verification
    try:
        _post_bsha, post_b_resolved, post_b_dev_ino = _verify_binding_file_identity(binding_path, actual_bsha)
        if post_b_resolved != pre_b_resolved or post_b_dev_ino != pre_b_dev_ino:
            raise AttributionStopError("input_changed_during_run", "binding_path relocated or replaced during run")
        post_binding_obj = _loads_strict_json(
            binding_path.read_text(encoding="utf-8"),
            syntax_cause="input_changed_during_run",
            ctx="source_binding_post_read",
        )
        _post_proto, _post_out_root, post_input_snapshots = _validate_binding_payload(
            post_binding_obj, expected_plan_sha=None
        )
        if post_input_snapshots != pre_input_snapshots:
            raise AttributionStopError(
                "input_changed_during_run",
                "fixed input or confining root resolved path / inode changed during run",
            )
    except AttributionStopError as exc:
        if exc.cause == "output_not_new":
            raise
        raise AttributionStopError("input_changed_during_run", f"{exc.cause}: {exc.raw_detail}") from exc

    ALLOWED_OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=False, exist_ok=False)

    # Write ONLY the 3 approved result files; summary.json MUST be written LAST!
    (output_root / "breadth_members.jsonl").write_text(bm_text, encoding="utf-8")
    (output_root / "report_CN.md").write_text(report_text, encoding="utf-8")
    (output_root / "summary.json").write_text(summary_text, encoding="utf-8")
    print(f"RUN_FINISHED OUTPUT_ROOT={output_root}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage 1.3 cross-asset volume breadth and Block-9 attribution controlled CLI."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser("prepare", help="Stream-verify 5 fixed inputs and write source_binding.json")
    p_prep.add_argument("--approved-plan-sha", required=True)
    p_prep.add_argument("--binding-output", required=True)
    p_prep.add_argument("--output-root", required=True)

    p_run = sub.add_parser("run", help="Verify binding and execute offline breadth attribution diagnostic")
    p_run.add_argument("--binding", required=True)
    p_run.add_argument("--binding-sha", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Controlled CLI entrypoint supporting prepare and run."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            return _cmd_prepare(args)
        if args.command == "run":
            return _cmd_run(args)
        raise AttributionStopError("code_or_authority_mismatch", f"unknown command: {args.command}")
    except AttributionStopError as exc:
        print(f"STOP={exc.stop_code} ({exc.detail})", file=sys.stderr)
        return 2
    except DiagnosticStopError as exc:
        print(f"STOP=input_invalid (cause=code_or_authority_mismatch: {exc.stop_code}: {exc.detail})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ALLOWED_ERROR_CAUSES",
    "AttributionStopError",
    "DiagnosticStopError",
    "_reject_symlink_chain",
    "_stream_sha256",
    "annotate_breadth",
    "build_default_protocol",
    "describe_attribution",
    "linear_quantile",
    "main",
    "validate_protocol",
    "verify_base_and_safety_config",
]
