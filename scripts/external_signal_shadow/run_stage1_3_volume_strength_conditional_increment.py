#!/usr/bin/env python3
"""Stage 1.3 volume-strength conditional increment diagnostic CLI and cohort statistics.

Consumes audited Stage 1.3 fixed-universe ledger/summary/coverage/manifest derivatives
to evaluate within-(symbol, 7d-block) volume-spike conditional increment on the fixed
relative-strength admitted queue Q without re-detecting signals or reading raw ZIPs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import research.external_signal_shadow.stage1_3_fixed_universe_diagnostic as diag_mod
from research.external_signal_shadow.stage1_3_fixed_universe_diagnostic import (
    DiagnosticStopError,
    build_default_protocol,
    linear_quantile,
    positive_contribution,
    reduce_block_sample,
    validate_protocol,
    verify_base_and_safety_config,
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
MS_PER_HOUR = 3_600_000
MS_PER_DAY = 86_400_000

EXPECTED_UPSTREAM_RUN_ROOT = Path(
    "/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-24-stage1-3-fixed-universe/20261125T062144Z"
)
FIXED_INPUT_SPECS: dict[str, tuple[Path, str]] = {
    "ledger_jsonl": (
        EXPECTED_UPSTREAM_RUN_ROOT / "results" / "ledger.jsonl",
        "c26e4da31c2836e4c2119aed8ad2120417e5b5339c75d41bc36bc4ee95df1638",
    ),
    "summary_json": (
        EXPECTED_UPSTREAM_RUN_ROOT / "results" / "summary.json",
        "624d26de18a22ed9a4474e78cd1e844bf148b29e33a7c4d47050aa80015edec2",
    ),
    "coverage_json": (
        EXPECTED_UPSTREAM_RUN_ROOT / "coverage.json",
        "98818c6b073fedfcca0946fea90f2e725944ab50082827c2b23a255b1e39ed9f",
    ),
    "source_manifest_json": (
        Path("/private/tmp/stage13-fixed-universe-implementation-20261124T022723Z/remediation_r4/source_manifest.json"),
        "c6aca62b38dc1e28604062ab6dbd7f4bb3fc6aa96b5734c4c35aecc415d1f997",
    ),
}
ALLOWED_OUTPUT_PARENT = Path(
    "/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-25-stage1-3-volume-strength-conditional-increment"
)
EXPECTED_B_ADMITTED_COUNT = 964

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_REL_PATH = "docs/designs/2026-11-25-stage1-3-volume-strength-conditional-increment-design_CN.md"
EXPECTED_DESIGN_SHA256 = "a7680d7984c9eba95c12cdda152a989e42d1df25a125bd6d7e2657de20458797"
PLAN_REL_PATH = "docs/plans/2026-11-25-stage1-3-volume-strength-conditional-increment-implementation-plan_CN.md"

PRIOR_DESIGN_REL_PATH = "docs/designs/2026-11-23-stage1-3-fixed-universe-mean-return-diagnostic-design_CN.md"
PRIOR_DESIGN_SHA256 = "8622d06b75c17a7bdfd103224cb11b75d147a7b92b1f3a06be6b81cd4417bd23"
PRIOR_PLAN_REL_PATH = "docs/plans/2026-11-24-stage1-3-fixed-universe-mean-return-diagnostic-implementation-plan_CN.md"
PRIOR_PLAN_SHA256 = "bf066b19f0bd43c2378bf6c34553dd10f7c9747ea070815627818c05db8e1e3a"

OLD_CORE_REL_PATH = "src/research/external_signal_shadow/stage1_3_fixed_universe_diagnostic.py"
EXPECTED_OLD_CORE_SHA256 = "e233a8af052c92b5746e5456c93cbde3a13056172d5151b4e2fab530146e04ee"

CODE_BINDING_SPECS: tuple[tuple[str, str], ...] = (
    ("scripts/external_signal_shadow/run_stage1_3_volume_strength_conditional_increment.py", "new_cli"),
    ("tests/scripts/external_signal_shadow/test_run_stage1_3_volume_strength_conditional_increment.py", "new_test"),
    (OLD_CORE_REL_PATH, "reused_diagnostic_helper"),
    ("configs/base.py", "reused_config"),
    ("src/risk/limits.py", "reused_safety"),
)
STREAM_CHUNK_BYTES = 65536

__all__ = [
    "DiagnosticStopError",
    "build_cohort",
    "build_default_protocol",
    "classify_observation",
    "linear_quantile",
    "main",
    "positive_contribution",
    "reduce_block_sample",
    "summarize_cohort",
    "validate_protocol",
    "verify_base_and_safety_config",
]


def _req_str(obj: dict[str, Any], key: str, stop_code: str, ctx: str) -> str:
    if key not in obj:
        raise DiagnosticStopError(stop_code, f"{ctx} missing required string key {key!r}")
    val = obj[key]
    if not isinstance(val, str) or not val.strip():
        raise DiagnosticStopError(stop_code, f"{ctx}.{key} must be non-empty str, got {val!r}")
    return val


def _req_int(obj: dict[str, Any], key: str, stop_code: str, ctx: str) -> int:
    if key not in obj:
        raise DiagnosticStopError(stop_code, f"{ctx} missing required int key {key!r}")
    val = obj[key]
    if isinstance(val, bool) or not isinstance(val, int):
        raise DiagnosticStopError(stop_code, f"{ctx}.{key} must be int (not bool), got {val!r}")
    return val


def _opt_int(obj: dict[str, Any], key: str, stop_code: str, ctx: str) -> int | None:
    if key not in obj:
        raise DiagnosticStopError(stop_code, f"{ctx} missing key {key!r}")
    val = obj[key]
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, int):
        raise DiagnosticStopError(stop_code, f"{ctx}.{key} must be int or None, got {val!r}")
    return val


def _req_finite_float(obj: dict[str, Any], key: str, stop_code: str, ctx: str) -> float:
    if key not in obj:
        raise DiagnosticStopError(stop_code, f"{ctx} missing required float key {key!r}")
    val = obj[key]
    if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(float(val)):
        raise DiagnosticStopError(stop_code, f"{ctx}.{key} must be finite number, got {val!r}")
    return float(val)


def _opt_finite_float(obj: dict[str, Any], key: str, stop_code: str, ctx: str) -> float | None:
    if key not in obj:
        raise DiagnosticStopError(stop_code, f"{ctx} missing key {key!r}")
    val = obj[key]
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(float(val)):
        raise DiagnosticStopError(stop_code, f"{ctx}.{key} must be finite number or None, got {val!r}")
    return float(val)


def _validate_decision_row(
    row: Any,
    *,
    proto: dict[str, Any],
    target_symbols_set: set[str],
    all_symbols_set: set[str],
) -> tuple[tuple[str, str, int], dict[str, Any]]:
    if not isinstance(row, dict):
        raise DiagnosticStopError("cohort_contract_mismatch", "ledger row must be dict")

    cand = _req_str(row, "candidate", "cohort_contract_mismatch", "row")
    if cand not in ALLOWED_CANDIDATES:
        raise DiagnosticStopError("cohort_contract_mismatch", f"unexpected candidate {cand!r}")

    sym = _req_str(row, "symbol", "cohort_contract_mismatch", f"row[{cand}]")
    if cand == CAND_A and sym not in all_symbols_set:
        raise DiagnosticStopError("cohort_contract_mismatch", f"unexpected symbol {sym!r} for {cand}")
    if cand == CAND_B and sym not in target_symbols_set:
        raise DiagnosticStopError("cohort_contract_mismatch", f"unexpected symbol {sym!r} for {cand}")

    avail_ms = _req_int(row, "available_at_ms", "cohort_time_mismatch", f"row[{cand},{sym}]")
    ctx = f"row[{cand},{sym},{avail_ms}]"

    status = _req_str(row, "status", "cohort_contract_mismatch", ctx)
    if status not in ALLOWED_ROW_STATUSES:
        raise DiagnosticStopError("cohort_contract_mismatch", f"{ctx} unknown status {status!r}")

    eval_start_ms = int(proto["eval_start_ms"])
    eval_end_ms = int(proto["eval_end_ms"])
    lag_ms = int(proto["configured_data_lag_ms"])
    interval_ms = int(proto["bar_interval_ms"])
    one_hour_bars = int(proto["one_hour_bar_count"])
    forward_bars = int(proto["forward_4h_bar_count"])
    entry_delay_bars = int(proto["entry_delay_bars"])
    block_count = int(proto["block_count"])
    block_ms = int(proto["block_days"]) * MS_PER_DAY
    vol_thresh = float(proto["volume_spike_threshold"])
    rs_thresh = float(proto["rel_strength_z_threshold"])

    if not (eval_start_ms <= avail_ms < eval_end_ms):
        raise DiagnosticStopError("cohort_time_mismatch", f"{ctx} available_at_ms outside eval range")

    win_end_ms = _req_int(row, "window_end_ms", "cohort_time_mismatch", ctx)
    if avail_ms != win_end_ms + lag_ms:
        raise DiagnosticStopError(
            "cohort_time_mismatch",
            f"{ctx} available_at_ms={avail_ms} != window_end_ms+lag={win_end_ms + lag_ms}",
        )
    if win_end_ms % interval_ms != 0:
        raise DiagnosticStopError("cohort_time_mismatch", f"{ctx} unaligned window_end_ms={win_end_ms}")

    win_start_ms = _opt_int(row, "window_start_ms", "cohort_time_mismatch", ctx)
    if win_start_ms is not None and (win_end_ms - win_start_ms) != one_hour_bars * interval_ms:
        raise DiagnosticStopError(
            "cohort_time_mismatch",
            f"{ctx} window_start_ms={win_start_ms} inconsistent with window_end_ms={win_end_ms}",
        )

    block_id = _req_int(row, "block_id", "cohort_time_mismatch", ctx)
    expected_block_id = (avail_ms - eval_start_ms) // block_ms
    if block_id != expected_block_id or not (0 <= block_id < block_count):
        raise DiagnosticStopError(
            "cohort_time_mismatch",
            f"{ctx} block_id={block_id} != expected {expected_block_id}",
        )
    block_end_ms = eval_start_ms + (block_id + 1) * block_ms

    utc_end_hour = _req_int(row, "utc_end_hour", "cohort_time_mismatch", ctx)
    avail_utc_hour = _req_int(row, "available_at_utc_hour", "cohort_time_mismatch", ctx)
    if utc_end_hour != (win_end_ms // MS_PER_HOUR) % 24:
        raise DiagnosticStopError("cohort_time_mismatch", f"{ctx} utc_end_hour mismatch")
    if avail_utc_hour != (avail_ms // MS_PER_HOUR) % 24:
        raise DiagnosticStopError("cohort_time_mismatch", f"{ctx} available_at_utc_hour mismatch")

    # Validate optional numeric fields for finiteness on all rows
    self_r1h = _opt_finite_float(row, "self_r1h", "cohort_contract_mismatch", ctx)
    btc_r1h = _opt_finite_float(row, "btc_r1h", "cohort_contract_mismatch", ctx)
    trig_val = _opt_finite_float(row, "trigger_value", "cohort_contract_mismatch", ctx)
    entry_open = _opt_finite_float(row, "entry_open_price", "cohort_contract_mismatch", ctx)
    exit_close = _opt_finite_float(row, "exit_close_price", "cohort_contract_mismatch", ctx)
    y_gross = _opt_finite_float(row, "y_gross_bps", "cohort_contract_mismatch", ctx)
    mfe_bps = _opt_finite_float(row, "mfe_4h_bps", "cohort_contract_mismatch", ctx)
    mae_bps = _opt_finite_float(row, "mae_4h_bps", "cohort_contract_mismatch", ctx)
    entry_start_ms = _opt_int(row, "entry_bar_start_ms", "cohort_time_mismatch", ctx)
    exit_end_ms = _opt_int(row, "exit_bar_end_ms", "cohort_time_mismatch", ctx)

    min_thresh = vol_thresh if cand == CAND_A else rs_thresh
    if "occupied_by_admitted_event" in row:
        occ = row["occupied_by_admitted_event"]
        if not isinstance(occ, bool):
            raise DiagnosticStopError("cohort_contract_mismatch", f"{ctx} occupied_by_admitted_event must be bool")
        if status == "admitted" and occ is True:
            raise DiagnosticStopError("cohort_contract_mismatch", f"{ctx} admitted row cannot have occupied=True")
        if status == "overlap_suppressed" and occ is False:
            raise DiagnosticStopError(
                "cohort_contract_mismatch", f"{ctx} overlap_suppressed row must have occupied=True"
            )

    if status in ("not_triggered", "feature_not_estimable", "block_boundary_censored"):
        if trig_val is not None:
            raise DiagnosticStopError(
                "cohort_contract_mismatch",
                f"{ctx} status={status} must have trigger_value=None, got {trig_val}",
            )
    elif status in ("admitted", "overlap_suppressed"):
        if trig_val is None or trig_val < min_thresh:
            raise DiagnosticStopError(
                "cohort_contract_mismatch",
                f"{ctx} status={status} requires trigger_value>={min_thresh}, got {trig_val}",
            )

    if status in ("not_triggered", "overlap_suppressed", "admitted"):
        if win_start_ms is None or self_r1h is None or btc_r1h is None:
            raise DiagnosticStopError("cohort_contract_mismatch", f"{ctx} missing 1h feature fields")
        if entry_start_ms is None or exit_end_ms is None:
            raise DiagnosticStopError("cohort_time_mismatch", f"{ctx} missing entry/exit timestamps")
        expected_entry_ms = win_end_ms + entry_delay_bars * interval_ms
        expected_exit_ms = expected_entry_ms + forward_bars * interval_ms
        if entry_start_ms <= avail_ms or entry_start_ms != expected_entry_ms:
            raise DiagnosticStopError(
                "cohort_time_mismatch",
                f"{ctx} entry_bar_start_ms={entry_start_ms} != expected {expected_entry_ms}",
            )
        if exit_end_ms != expected_exit_ms or exit_end_ms > block_end_ms:
            raise DiagnosticStopError(
                "cohort_time_mismatch",
                f"{ctx} exit_bar_end_ms={exit_end_ms} != expected {expected_exit_ms} or exceeds block end",
            )

    if status == "admitted" and cand == CAND_B:
        if (
            entry_open is None
            or exit_close is None
            or y_gross is None
            or mfe_bps is None
            or mae_bps is None
            or entry_open <= 0.0
            or exit_close <= 0.0
        ):
            raise DiagnosticStopError("cohort_contract_mismatch", f"{ctx} missing admitted B return/price fields")
        expected_y = 10000.0 * (exit_close / entry_open - 1.0)
        if abs(y_gross - expected_y) > 1e-6:
            raise DiagnosticStopError(
                "cohort_contract_mismatch",
                f"{ctx} y_gross_bps={y_gross} != 10000*(exit_close/entry_open-1)={expected_y}",
            )
        if mfe_bps < max(0.0, y_gross) - 1e-6 or mae_bps > min(0.0, y_gross) + 1e-6:
            raise DiagnosticStopError(
                "cohort_contract_mismatch",
                f"{ctx} invalid MAE/MFE envelope ({mae_bps}, {y_gross}, {mfe_bps})",
            )

    return (cand, sym, avail_ms), row


def build_cohort(rows: list[dict[str, Any]], *, protocol: dict[str, Any]) -> dict[str, Any]:
    """Construct fixed B admitted queue Q, pair A conditions, and determine (symbol, block) support S."""
    proto = validate_protocol(protocol)
    if not isinstance(rows, list) or not rows:
        raise DiagnosticStopError("cohort_contract_mismatch", "rows must be non-empty list")

    all_symbols = list(proto["symbols"])
    target_symbols = [s for s in all_symbols if s != "BTCUSDT"]
    all_symbols_set = set(all_symbols)
    target_symbols_set = set(target_symbols)
    block_count = int(proto["block_count"])
    vol_thresh = float(proto["volume_spike_threshold"])

    indexed: dict[tuple[str, str, int], dict[str, Any]] = {}
    b_admitted_rows: list[dict[str, Any]] = []
    status_counts_by_cand: dict[str, dict[str, int]] = {
        CAND_A: {st: 0 for st in ALLOWED_ROW_STATUSES},
        CAND_B: {st: 0 for st in ALLOWED_ROW_STATUSES},
    }

    for raw_row in rows:
        key, validated = _validate_decision_row(
            raw_row,
            proto=proto,
            target_symbols_set=target_symbols_set,
            all_symbols_set=all_symbols_set,
        )
        if key in indexed:
            raise DiagnosticStopError("cohort_contract_mismatch", f"duplicate decision key {key!r}")
        indexed[key] = validated
        status_counts_by_cand[key[0]][validated["status"]] += 1
        if key[0] == CAND_B and validated["status"] == "admitted":
            b_admitted_rows.append(validated)

    sym_order = {sym: i for i, sym in enumerate(target_symbols)}
    b_admitted_rows.sort(key=lambda r: (sym_order[r["symbol"]], int(r["available_at_ms"])))

    prev_exit_by_sym: dict[str, int] = {}
    for b_row in b_admitted_rows:
        sym = b_row["symbol"]
        avail_ms = int(b_row["available_at_ms"])
        if sym in prev_exit_by_sym and avail_ms <= prev_exit_by_sym[sym]:
            raise DiagnosticStopError(
                "cohort_time_mismatch",
                f"overlapping B admitted event ({sym}, {avail_ms}) <= previous exit {prev_exit_by_sym[sym]}",
            )
        prev_exit_by_sym[sym] = int(b_row["exit_bar_end_ms"])

    # Step 1: Pair each fixed B admitted event with same-(symbol, available_at_ms) A row and determine A condition
    provisional_members: list[dict[str, Any]] = []
    strata_joint: dict[tuple[str, int], list[dict[str, Any]]] = {
        (sym, b_id): [] for sym in target_symbols for b_id in range(block_count)
    }
    strata_b_only: dict[tuple[str, int], list[dict[str, Any]]] = {
        (sym, b_id): [] for sym in target_symbols for b_id in range(block_count)
    }

    for b_row in b_admitted_rows:
        sym = b_row["symbol"]
        avail_ms = int(b_row["available_at_ms"])
        a_key = (CAND_A, sym, avail_ms)
        if a_key not in indexed:
            raise DiagnosticStopError(
                "cohort_contract_mismatch",
                f"missing paired {CAND_A} decision row for ({sym}, {avail_ms})",
            )
        a_row = indexed[a_key]
        a_status = a_row["status"]
        a_trig = a_row["trigger_value"]

        if a_status in ("admitted", "overlap_suppressed"):
            if a_trig is None or float(a_trig) < vol_thresh:
                raise DiagnosticStopError(
                    "cohort_contract_mismatch",
                    f"paired {CAND_A} row {a_key} has status={a_status} with invalid trigger_value={a_trig}",
                )
            a_triggered = True
        elif a_status == "not_triggered" and a_trig is None:
            a_triggered = False
        else:
            raise DiagnosticStopError(
                "cohort_contract_mismatch",
                f"paired {CAND_A} row {a_key} has inadmissible status={a_status!r}, trigger_value={a_trig!r}",
            )

        # Cross-check exact causal window, block, and reference entry/exit alignment between B and A
        for time_field in (
            "window_start_ms",
            "window_end_ms",
            "available_at_ms",
            "block_id",
            "entry_bar_start_ms",
            "exit_bar_end_ms",
        ):
            if a_row[time_field] != b_row[time_field]:
                raise DiagnosticStopError(
                    "cohort_time_mismatch",
                    f"B/A {time_field} mismatch at ({sym}, {avail_ms}): B={b_row[time_field]} vs A={a_row[time_field]}",
                )

        stratum_key = (sym, int(b_row["block_id"]))
        member: dict[str, Any] = {
            "candidate": CAND_B,
            "symbol": sym,
            "available_at_ms": avail_ms,
            "block_id": int(b_row["block_id"]),
            "window_start_ms": int(b_row["window_start_ms"]),
            "window_end_ms": int(b_row["window_end_ms"]),
            "utc_end_hour": int(b_row["utc_end_hour"]),
            "available_at_utc_hour": int(b_row["available_at_utc_hour"]),
            "entry_bar_start_ms": int(b_row["entry_bar_start_ms"]),
            "exit_bar_end_ms": int(b_row["exit_bar_end_ms"]),
            "entry_open_price": float(b_row["entry_open_price"]),
            "exit_close_price": float(b_row["exit_close_price"]),
            "self_r1h": float(b_row["self_r1h"]),
            "btc_r1h": float(b_row["btc_r1h"]),
            "b_trigger_value": float(b_row["trigger_value"]),
            "y_gross_bps": float(b_row["y_gross_bps"]),
            "mfe_4h_bps": float(b_row["mfe_4h_bps"]),
            "mae_4h_bps": float(b_row["mae_4h_bps"]),
            "a_key": [CAND_A, sym, avail_ms],
            "a_status": a_status,
            "a_trigger_value": float(a_trig) if a_trig is not None else None,
            "a_triggered": a_triggered,
            "group": "joint" if a_triggered else "b_only",
        }
        provisional_members.append(member)
        if a_triggered:
            strata_joint[stratum_key].append(member)
        else:
            strata_b_only[stratum_key].append(member)

    # Step 2: Determine common support S = {s=(symbol, block_id) : n_s1 > 0 and n_s0 > 0} strictly from counts
    strata_records: list[dict[str, Any]] = []
    support_map: dict[tuple[str, int], bool] = {}
    supported_strata_count = 0
    for sym in target_symbols:
        for b_id in range(block_count):
            sk = (sym, b_id)
            n_s1 = len(strata_joint[sk])
            n_s0 = len(strata_b_only[sk])
            in_supp = n_s1 > 0 and n_s0 > 0
            support_map[sk] = in_supp
            if in_supp:
                supported_strata_count += 1
            strata_records.append(
                {
                    "symbol": sym,
                    "block_id": b_id,
                    "n_q": n_s1 + n_s0,
                    "n_s1_joint": n_s1,
                    "n_s0_b_only": n_s0,
                    "in_common_support": in_supp,
                }
            )

    # Step 3: Attach support & control identity keys (without inspecting or mixing outcome Y)
    joint_all_count = 0
    b_only_all_count = 0
    joint_supported_count = 0
    joint_unmatched_count = 0
    b_only_in_support_count = 0

    for m in provisional_members:
        sk = (m["symbol"], m["block_id"])
        in_supp = support_map[sk]
        m["in_common_support"] = in_supp
        if m["a_triggered"]:
            joint_all_count += 1
            if in_supp:
                joint_supported_count += 1
                m["support_status"] = "supported"
                m["conditional_control_keys"] = [
                    [CAND_B, ctrl["symbol"], ctrl["available_at_ms"]]
                    for ctrl in strata_b_only[sk]
                ]
            else:
                joint_unmatched_count += 1
                m["support_status"] = "unmatched"
                m["conditional_control_keys"] = []
        else:
            b_only_all_count += 1
            if in_supp:
                b_only_in_support_count += 1
                m["support_status"] = "control_in_support"
            else:
                m["support_status"] = "b_only_unpaired_stratum"
            m["conditional_control_keys"] = []

    return {
        "protocol": proto,
        "target_symbols": target_symbols,
        "status_counts_by_candidate": status_counts_by_cand,
        "counts": {
            "q_total": len(provisional_members),
            "joint_all_count": joint_all_count,
            "b_only_all_count": b_only_all_count,
            "joint_supported_count": joint_supported_count,
            "joint_unmatched_count": joint_unmatched_count,
            "b_only_in_support_count": b_only_in_support_count,
            "b_only_unpaired_stratum_count": b_only_all_count - b_only_in_support_count,
            "total_strata": len(strata_records),
            "common_support_strata_count": supported_strata_count,
        },
        "strata": strata_records,
        "members": provisional_members,
    }


def classify_observation(metrics: dict[str, Any]) -> dict[str, str]:
    """Apply Design §6 first-matching routing rule."""
    alpha_status = "evidence_insufficient"
    mu_joint = metrics["mu_joint_all_bps"]
    delta = metrics["delta_bps"]

    if not bool(metrics["prerequisites_valid"]) or mu_joint is None or delta is None:
        return {
            "observation_label": "not_estimable",
            "resource_decision": "stop_due_to_evidence",
            "alpha_research_status": alpha_status,
        }

    if float(delta) <= 0.0:
        return {
            "observation_label": "no_increment_observed",
            "resource_decision": "stop_fixed_spec_this_round",
            "alpha_research_status": alpha_status,
        }

    if float(mu_joint) <= 0.0:
        return {
            "observation_label": "relative_increment_without_positive_gross",
            "resource_decision": "stop_fixed_spec_this_round",
            "alpha_research_status": alpha_status,
        }

    mu_ci_low = metrics["mu_ci_low"]
    delta_ci_low = metrics["delta_ci_low"]
    fh_mu = metrics["first_half_mu"]
    fh_delta = metrics["first_half_delta"]
    sh_mu = metrics["second_half_mu"]
    sh_delta = metrics["second_half_delta"]
    wb_mu = metrics["without_best_mu"]
    wb_delta = metrics["without_best_delta"]

    stable = (
        bool(metrics["mu_ci_complete"])
        and bool(metrics["delta_ci_complete"])
        and mu_ci_low is not None
        and float(mu_ci_low) > 0.0
        and delta_ci_low is not None
        and float(delta_ci_low) > 0.0
        and fh_mu is not None
        and float(fh_mu) > 0.0
        and fh_delta is not None
        and float(fh_delta) > 0.0
        and sh_mu is not None
        and float(sh_mu) > 0.0
        and sh_delta is not None
        and float(sh_delta) > 0.0
        and bool(metrics["leave_one_symbol_all_positive"])
        and bool(metrics["leave_one_block_all_positive"])
        and wb_mu is not None
        and float(wb_mu) > 0.0
        and wb_delta is not None
        and float(wb_delta) > 0.0
        and not bool(metrics["has_unexplained_input_issue"])
    )
    if not stable:
        return {
            "observation_label": "inconclusive_or_concentrated",
            "resource_decision": "pause_for_new_evidence",
            "alpha_research_status": alpha_status,
        }

    if bool(metrics["any_cost_scenario_mean_positive"]):
        return {
            "observation_label": "bounded_positive_pattern",
            "resource_decision": "consider_independent_validation_only",
            "alpha_research_status": alpha_status,
        }
    return {
        "observation_label": "bounded_positive_pattern",
        "resource_decision": "stop_strategy_development_this_round",
        "alpha_research_status": alpha_status,
    }


def _summarize_group_distribution(
    events: list[dict[str, Any]],
    *,
    cost_bps: float,
    delta_bps: float | None,
    include_delta: bool,
) -> dict[str, Any]:
    values = [float(e["y_gross_bps"]) - cost_bps for e in events]
    mfe_vals = [float(e["mfe_4h_bps"]) for e in events]
    mae_vals = [float(e["mae_4h_bps"]) for e in events]
    n = len(values)

    if n == 0:
        out: dict[str, Any] = {
            "cost_round_trip_bps": cost_bps,
            "n": 0,
            "mean_bps": None,
            "median_bps": None,
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
            "mfe_4h_gross_bps": {"mean": None, "p50": None, "p90": None, "max": None},
            "mae_4h_gross_bps": {"mean": None, "p10": None, "p50": None, "min": None},
            "bar_internal_ordering_known": False,
            "executable_stop_claim_allowed": False,
        }
        if include_delta:
            out["delta_bps"] = delta_bps
        return out

    wins = [v for v in values if v > 0.0]
    losses = [v for v in values if v < 0.0]
    avg_win = (sum(wins) / len(wins)) if wins else None
    avg_loss = (sum(losses) / len(losses)) if losses else None
    payoff = (
        (avg_win / abs(avg_loss))
        if (avg_win is not None and avg_loss is not None and avg_loss < 0.0)
        else None
    )

    out = {
        "cost_round_trip_bps": cost_bps,
        "n": n,
        "mean_bps": sum(values) / n,
        "median_bps": linear_quantile(values, 0.50),
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
        "mfe_4h_gross_bps": {
            "mean": sum(mfe_vals) / n,
            "p50": linear_quantile(mfe_vals, 0.50),
            "p90": linear_quantile(mfe_vals, 0.90),
            "max": max(mfe_vals),
        },
        "mae_4h_gross_bps": {
            "mean": sum(mae_vals) / n,
            "p10": linear_quantile(mae_vals, 0.10),
            "p50": linear_quantile(mae_vals, 0.50),
            "min": min(mae_vals),
        },
        "bar_internal_ordering_known": False,
        "executable_stop_claim_allowed": False,
    }
    if include_delta:
        out["delta_bps"] = delta_bps
    return out


def _summarize_scalar_feature(vals: list[float]) -> dict[str, Any]:
    if not vals:
        return {"n": 0, "mean": None, "p10": None, "p50": None, "p90": None}
    return {
        "n": len(vals),
        "mean": sum(vals) / len(vals),
        "p10": linear_quantile(vals, 0.10),
        "p50": linear_quantile(vals, 0.50),
        "p90": linear_quantile(vals, 0.90),
    }


def _summarize_joint_subset(joint_events: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(joint_events)
    sum_y = sum(float(e["y_gross_bps"]) for e in joint_events)
    supp = [e for e in joint_events if e["conditional_d_bps"] is not None]
    m = len(supp)
    sum_d = sum(float(e["conditional_d_bps"]) for e in supp)
    return {
        "joint_all_count": n,
        "joint_supported_count": m,
        "joint_unmatched_count": n - m,
        "sum_y_bps": sum_y,
        "mu_joint_all_bps": (sum_y / n) if n > 0 else None,
        "sum_d_bps": sum_d,
        "delta_bps": (sum_d / m) if m > 0 else None,
    }


def summarize_cohort(cohort: dict[str, Any], *, protocol: dict[str, Any]) -> dict[str, Any]:
    """Compute conditional increment Delta, group distributions, 23-block bootstrap, and diagnostics."""
    proto = validate_protocol(protocol)
    target_symbols = list(cohort["target_symbols"])
    block_count = int(proto["block_count"])
    first_half_n = int(proto["first_half_block_count"])
    bootstrap_replicates = int(proto["bootstrap_replicates"])
    bootstrap_seed = int(proto["bootstrap_seed"])
    cost_scenarios = [float(c) for c in proto["cost_scenarios_round_trip_bps"]]

    # Index members by stratum (keeping original cohort support fixed)
    strata_j: dict[tuple[str, int], list[dict[str, Any]]] = {
        (s, b): [] for s in target_symbols for b in range(block_count)
    }
    strata_b: dict[tuple[str, int], list[dict[str, Any]]] = {
        (s, b): [] for s in target_symbols for b in range(block_count)
    }
    enriched_members: list[dict[str, Any]] = []
    for raw_m in cohort["members"]:
        m = dict(raw_m)
        sk = (m["symbol"], int(m["block_id"]))
        enriched_members.append(m)
        if m["a_triggered"]:
            strata_j[sk].append(m)
        else:
            strata_b[sk].append(m)

    # Compute fixed stratum means & attach conditional_control_mean_bps / conditional_d_bps
    stratum_ctrl_mean: dict[tuple[str, int], float | None] = {}
    enriched_strata: list[dict[str, Any]] = []
    sum_s_weighted_y1 = 0.0
    sum_s_weighted_y0 = 0.0
    total_supported_n1 = 0

    for s in target_symbols:
        for b in range(block_count):
            sk = (s, b)
            j_list = strata_j[sk]
            b_list = strata_b[sk]
            n1 = len(j_list)
            n0 = len(b_list)
            in_supp = n1 > 0 and n0 > 0
            mean_y1 = (sum(float(x["y_gross_bps"]) for x in j_list) / n1) if n1 > 0 else None
            mean_y0 = (sum(float(x["y_gross_bps"]) for x in b_list) / n0) if n0 > 0 else None
            stratum_ctrl_mean[sk] = mean_y0 if in_supp else None
            if in_supp and mean_y1 is not None and mean_y0 is not None:
                sum_s_weighted_y1 += n1 * mean_y1
                sum_s_weighted_y0 += n1 * mean_y0
                total_supported_n1 += n1
            enriched_strata.append(
                {
                    "symbol": s,
                    "block_id": b,
                    "n_q": n1 + n0,
                    "n_s1_joint": n1,
                    "n_s0_b_only": n0,
                    "in_common_support": in_supp,
                    "mean_y_s1_bps": mean_y1,
                    "mean_y_s0_bps": mean_y0,
                    "stratum_diff_bps": (mean_y1 - mean_y0) if (in_supp and mean_y1 is not None and mean_y0 is not None) else None,
                }
            )

    joint_all_events: list[dict[str, Any]] = []
    b_only_all_events: list[dict[str, Any]] = []
    joint_supported_events: list[dict[str, Any]] = []
    b_only_in_support_events: list[dict[str, Any]] = []

    for m in enriched_members:
        sk = (m["symbol"], int(m["block_id"]))
        if m["a_triggered"]:
            joint_all_events.append(m)
            c_mean = stratum_ctrl_mean[sk]
            if m["in_common_support"] and c_mean is not None:
                m["conditional_control_mean_bps"] = c_mean
                m["conditional_d_bps"] = float(m["y_gross_bps"]) - c_mean
                joint_supported_events.append(m)
            else:
                m["conditional_control_mean_bps"] = None
                m["conditional_d_bps"] = None
        else:
            b_only_all_events.append(m)
            if m["in_common_support"]:
                b_only_in_support_events.append(m)
            m["conditional_control_mean_bps"] = None
            m["conditional_d_bps"] = None

    n_joint_all = len(joint_all_events)
    sum_y_joint_all = sum(float(e["y_gross_bps"]) for e in joint_all_events)
    mu_joint_all_bps = (sum_y_joint_all / n_joint_all) if n_joint_all > 0 else None

    if total_supported_n1 > 0:
        mu_joint_supported_bps: float | None = sum_s_weighted_y1 / total_supported_n1
        mu_control_reweighted_bps: float | None = sum_s_weighted_y0 / total_supported_n1
        delta_bps: float | None = mu_joint_supported_bps - mu_control_reweighted_bps
    else:
        mu_joint_supported_bps = None
        mu_control_reweighted_bps = None
        delta_bps = None

    # Build 23-block stats (exact structure consumed by reduce_block_sample)
    block_stats: list[dict[str, Any]] = []
    for b_id in range(block_count):
        b_joint = [e for e in joint_all_events if int(e["block_id"]) == b_id]
        b_supp = [e for e in b_joint if e["conditional_d_bps"] is not None]
        block_stats.append(
            {
                "block_id": b_id,
                "sum_y": sum(float(e["y_gross_bps"]) for e in b_joint),
                "n": len(b_joint),
                "sum_d": sum(float(e["conditional_d_bps"]) for e in b_supp),
                "m": len(b_supp),
            }
        )

    # Joint 23-block bootstrap (10,000 replicates, seed 20261123) via reused reduce_block_sample
    rng = random.Random(bootstrap_seed)
    mu_draws: list[float] = []
    delta_draws: list[float] = []
    empty_mu_replicates = 0
    empty_delta_replicates = 0
    block_indices = list(range(block_count))

    for _ in range(bootstrap_replicates):
        drawn = rng.choices(block_indices, k=block_count)
        red = reduce_block_sample(block_stats, drawn)
        if red["mu_gross_bps"] is None:
            empty_mu_replicates += 1
        else:
            mu_draws.append(float(red["mu_gross_bps"]))
        if red["delta_bps"] is None:
            empty_delta_replicates += 1
        else:
            delta_draws.append(float(red["delta_bps"]))

    mu_ci_low = linear_quantile(mu_draws, 0.025)
    mu_ci_high = linear_quantile(mu_draws, 0.975)
    delta_ci_low = linear_quantile(delta_draws, 0.025)
    delta_ci_high = linear_quantile(delta_draws, 0.975)
    mu_ci_complete = empty_mu_replicates == 0 and len(mu_draws) == bootstrap_replicates
    delta_ci_complete = empty_delta_replicates == 0 and len(delta_draws) == bootstrap_replicates

    # Group distributions & cost scenarios
    dist_joint_all = _summarize_group_distribution(
        joint_all_events, cost_bps=0.0, delta_bps=delta_bps, include_delta=True
    )
    dist_b_only_all = _summarize_group_distribution(
        b_only_all_events, cost_bps=0.0, delta_bps=None, include_delta=False
    )
    dist_joint_supported = _summarize_group_distribution(
        joint_supported_events, cost_bps=0.0, delta_bps=delta_bps, include_delta=True
    )

    cost_scenarios_out: dict[str, Any] = {}
    any_cost_pos = False
    for c_bps in cost_scenarios:
        cd = _summarize_group_distribution(
            joint_all_events, cost_bps=c_bps, delta_bps=delta_bps, include_delta=True
        )
        if cd["mean_bps"] is not None and float(cd["mean_bps"]) > 0.0:
            any_cost_pos = True
        cost_scenarios_out[f"{c_bps:.1f}"] = cd

    pos_contrib = positive_contribution([float(e["y_gross_bps"]) for e in joint_all_events])

    # Fixed diagnostics (subtracting original contributions without re-matching or relaxing support)
    first_half = _summarize_joint_subset([e for e in joint_all_events if int(e["block_id"]) < first_half_n])
    second_half = _summarize_joint_subset([e for e in joint_all_events if int(e["block_id"]) >= first_half_n])

    per_symbol_diag: dict[str, Any] = {}
    for sym in target_symbols:
        sym_j = [e for e in joint_all_events if e["symbol"] == sym]
        sym_b = [e for e in b_only_all_events if e["symbol"] == sym]
        sub = _summarize_joint_subset(sym_j)
        sub["b_only_count"] = len(sym_b)
        sub["q_count"] = len(sym_j) + len(sym_b)
        per_symbol_diag[sym] = sub

    per_block_diag: list[dict[str, Any]] = []
    for bs in block_stats:
        b_id = bs["block_id"]
        b_bonly = [e for e in b_only_all_events if int(e["block_id"]) == b_id]
        per_block_diag.append(
            {
                "block_id": b_id,
                "q_count": bs["n"] + len(b_bonly),
                "joint_all_count": bs["n"],
                "b_only_count": len(b_bonly),
                "joint_supported_count": bs["m"],
                "joint_unmatched_count": bs["n"] - bs["m"],
                "sum_y_bps": bs["sum_y"],
                "mu_joint_all_bps": (bs["sum_y"] / bs["n"]) if bs["n"] > 0 else None,
                "sum_d_bps": bs["sum_d"],
                "delta_bps": (bs["sum_d"] / bs["m"]) if bs["m"] > 0 else None,
            }
        )

    leave_one_symbol_out = {
        sym: _summarize_joint_subset([e for e in joint_all_events if e["symbol"] != sym])
        for sym in target_symbols
    }
    leave_one_block_out = {
        str(b_id): _summarize_joint_subset([e for e in joint_all_events if int(e["block_id"]) != b_id])
        for b_id in range(block_count)
    }

    if joint_all_events:
        best_idx = min(
            range(len(joint_all_events)),
            key=lambda i: (
                -float(joint_all_events[i]["y_gross_bps"]),
                int(joint_all_events[i]["available_at_ms"]),
                str(joint_all_events[i]["symbol"]),
            ),
        )
        without_best = _summarize_joint_subset(
            [e for i, e in enumerate(joint_all_events) if i != best_idx]
        )
    else:
        without_best = _summarize_joint_subset([])

    loso_all_pos = bool(leave_one_symbol_out) and all(
        v["mu_joint_all_bps"] is not None
        and float(v["mu_joint_all_bps"]) > 0.0
        and v["delta_bps"] is not None
        and float(v["delta_bps"]) > 0.0
        for v in leave_one_symbol_out.values()
    )
    lobo_all_pos = bool(leave_one_block_out) and all(
        v["mu_joint_all_bps"] is not None
        and float(v["mu_joint_all_bps"]) > 0.0
        and v["delta_bps"] is not None
        and float(v["delta_bps"]) > 0.0
        for v in leave_one_block_out.values()
    )

    routing = classify_observation(
        {
            "prerequisites_valid": True,
            "mu_joint_all_bps": mu_joint_all_bps,
            "delta_bps": delta_bps,
            "mu_ci_complete": mu_ci_complete,
            "mu_ci_low": mu_ci_low,
            "delta_ci_complete": delta_ci_complete,
            "delta_ci_low": delta_ci_low,
            "first_half_mu": first_half["mu_joint_all_bps"],
            "first_half_delta": first_half["delta_bps"],
            "second_half_mu": second_half["mu_joint_all_bps"],
            "second_half_delta": second_half["delta_bps"],
            "leave_one_symbol_all_positive": loso_all_pos,
            "leave_one_block_all_positive": lobo_all_pos,
            "without_best_mu": without_best["mu_joint_all_bps"],
            "without_best_delta": without_best["delta_bps"],
            "any_cost_scenario_mean_positive": any_cost_pos,
            "has_unexplained_input_issue": False,
        }
    )

    # Comparability disclosure on pre-entry features (self_r1h in bps and B z-score trigger_value)
    comparability = {
        "joint_all": {
            "self_r1h_bps": _summarize_scalar_feature([float(e["self_r1h"]) * 10000.0 for e in joint_all_events]),
            "b_trigger_z": _summarize_scalar_feature([float(e["b_trigger_value"]) for e in joint_all_events]),
        },
        "b_only_all": {
            "self_r1h_bps": _summarize_scalar_feature([float(e["self_r1h"]) * 10000.0 for e in b_only_all_events]),
            "b_trigger_z": _summarize_scalar_feature([float(e["b_trigger_value"]) for e in b_only_all_events]),
        },
        "joint_supported": {
            "self_r1h_bps": _summarize_scalar_feature([float(e["self_r1h"]) * 10000.0 for e in joint_supported_events]),
            "b_trigger_z": _summarize_scalar_feature([float(e["b_trigger_value"]) for e in joint_supported_events]),
        },
        "b_only_in_support": {
            "self_r1h_bps": _summarize_scalar_feature([float(e["self_r1h"]) * 10000.0 for e in b_only_in_support_events]),
            "b_trigger_z": _summarize_scalar_feature([float(e["b_trigger_value"]) for e in b_only_in_support_events]),
        },
    }

    q_total = int(cohort["counts"]["q_total"])
    counts_summary = {
        **cohort["counts"],
        "joint_share_of_q": (n_joint_all / q_total) if q_total > 0 else None,
        "supported_share_of_joint": (total_supported_n1 / n_joint_all) if n_joint_all > 0 else None,
        "unmatched_share_of_joint": ((n_joint_all - total_supported_n1) / n_joint_all) if n_joint_all > 0 else None,
        "non_empty_joint_block_count": sum(1 for bs in block_stats if bs["n"] > 0),
        "non_empty_supported_block_count": sum(1 for bs in block_stats if bs["m"] > 0),
    }

    summary_payload: dict[str, Any] = {
        "protocol": proto,
        "target_symbols": target_symbols,
        "counts": counts_summary,
        "numerators_denominators": {
            "sum_y_joint_all_bps": sum_y_joint_all,
            "n_joint_all": n_joint_all,
            "sum_y_joint_supported_bps": sum_s_weighted_y1,
            "sum_control_reweighted_bps": sum_s_weighted_y0,
            "sum_d_joint_supported_bps": sum(float(e["conditional_d_bps"]) for e in joint_supported_events),
            "n_joint_supported": total_supported_n1,
        },
        "mu_joint_all_bps": mu_joint_all_bps,
        "mu_joint_supported_bps": mu_joint_supported_bps,
        "mu_control_reweighted_bps": mu_control_reweighted_bps,
        "delta_bps": delta_bps,
        "c_break_even_bps": mu_joint_all_bps,
        "minimum_economically_meaningful_gain": None,
        "cost_mode": "cost_context_only",
        "strata": enriched_strata,
        "block_stats": block_stats,
        "distributions": {
            "joint_all": dist_joint_all,
            "b_only_all": dist_b_only_all,
            "joint_supported": dist_joint_supported,
        },
        "cost_scenarios_joint_all": cost_scenarios_out,
        "positive_contribution_joint_all": pos_contrib,
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "block_count": block_count,
            "mu_joint_all_bps": {
                "valid_replicates": len(mu_draws),
                "empty_replicates": empty_mu_replicates,
                "ci_complete": mu_ci_complete,
                "ci_025": mu_ci_low,
                "ci_975": mu_ci_high,
            },
            "delta_bps": {
                "valid_replicates": len(delta_draws),
                "empty_replicates": empty_delta_replicates,
                "ci_complete": delta_ci_complete,
                "ci_025": delta_ci_low,
                "ci_975": delta_ci_high,
            },
        },
        "diagnostics": {
            "first_half_blocks_0_10": first_half,
            "second_half_blocks_11_22": second_half,
            "per_symbol": per_symbol_diag,
            "per_block": per_block_diag,
            "leave_one_symbol_out": leave_one_symbol_out,
            "leave_one_block_out": leave_one_block_out,
            "without_best_joint_event": without_best,
        },
        "comparability": comparability,
        "governance": {
            "exploratory_only": True,
            "exposed_evaluation_window": True,
            "independent_out_of_sample_claim_allowed": False,
            "full_market_alpha_claim_allowed": False,
            "r10_readmission_claim_allowed": False,
            "causal_effect_claim_allowed": False,
            "four_cell_interaction_claimed": False,
            "cost_mode": "cost_context_only",
            "minimum_economically_meaningful_gain": None,
            "live_trading_enabled": False,
            "paper_trading_allowed": False,
            "execution_engine_allowed": False,
            "execution_feasibility_claim_allowed": False,
            "portfolio_pnl_reported": False,
            "distributions_bar_ordering_known": False,
        },
        "routing": routing,
    }

    return {
        "members": enriched_members,
        "summary": summary_payload,
    }


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stream_sha256(path: Path, *, stop_code: str = "input_identity_mismatch") -> str:
    if path.is_symlink():
        raise DiagnosticStopError("input_path_mismatch", f"symlink rejected: {path}")
    if not path.is_file():
        raise DiagnosticStopError(stop_code, f"missing regular file: {path}")
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(STREAM_CHUNK_BYTES)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _git_head(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise DiagnosticStopError("source_binding_mismatch", f"failed to read git HEAD: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _reject_nonfinite_constant(val: str) -> Any:
    raise DiagnosticStopError("cohort_contract_mismatch", f"non-finite JSON constant rejected: {val}")


def _loads_strict_json(text: str, *, stop_code: str, ctx: str) -> Any:
    try:
        return json.loads(text, parse_constant=_reject_nonfinite_constant)
    except DiagnosticStopError:
        raise
    except json.JSONDecodeError as exc:
        raise DiagnosticStopError(stop_code, f"{ctx} invalid JSON: {exc}") from exc


_MACOS_ROOT_ALIASES = frozenset({"/tmp", "/var", "/etc"})


def _expected_canonical_path(path: Path) -> Path:
    if sys.platform == "darwin" and len(path.parts) >= 2 and f"/{path.parts[1]}" in _MACOS_ROOT_ALIASES:
        return Path("/private", *path.parts[1:])
    return path


def _reject_symlink_chain(path: Path, *, stop_code: str, label: str) -> None:
    if not path.is_absolute() or ".." in path.parts:
        raise DiagnosticStopError(stop_code, f"{label} must be clean absolute path: {path}")
    for anc in (path, *path.parents):
        if anc.is_symlink():
            if sys.platform == "darwin" and str(anc) in _MACOS_ROOT_ALIASES:
                continue
            raise DiagnosticStopError(stop_code, f"{label} symlink component rejected: {anc}")


def _verify_helper_origin_and_code_bindings() -> list[dict[str, str]]:
    _reject_symlink_chain(REPO_ROOT, stop_code="code_identity_mismatch", label="repo_root")
    mod_file = getattr(diag_mod, "__file__", None)
    if not isinstance(mod_file, str) or not mod_file:
        raise DiagnosticStopError("code_identity_mismatch", "helper module missing __file__")
    expected_helper = (REPO_ROOT / OLD_CORE_REL_PATH).resolve()
    if Path(mod_file).resolve() != expected_helper:
        raise DiagnosticStopError(
            "code_identity_mismatch",
            f"helper module origin {mod_file} != expected {expected_helper}",
        )

    bindings: list[dict[str, str]] = []
    for rel_path, role in CODE_BINDING_SPECS:
        abs_p = REPO_ROOT / rel_path
        _reject_symlink_chain(abs_p, stop_code="code_identity_mismatch", label=rel_path)
        if not abs_p.is_file():
            raise DiagnosticStopError("code_identity_mismatch", f"missing bound code file: {abs_p}")
        sha = _stream_sha256(abs_p, stop_code="code_identity_mismatch")
        if rel_path == OLD_CORE_REL_PATH and sha.lower() != EXPECTED_OLD_CORE_SHA256.lower():
            raise DiagnosticStopError(
                "code_identity_mismatch",
                f"{OLD_CORE_REL_PATH} SHA {sha} != frozen {EXPECTED_OLD_CORE_SHA256}",
            )
        bindings.append({"path": rel_path, "role": role, "sha256": sha})
    return bindings


def _verify_confined_fixed_input(
    *,
    key: str,
    candidate_path: Path,
    expected_path: Path,
    expected_sha: str,
    upstream_run_root: Path,
) -> tuple[str, Path, tuple[int, int]]:
    if candidate_path != expected_path:
        raise DiagnosticStopError(
            "input_path_mismatch",
            f"{key} path {candidate_path} != frozen path {expected_path}",
        )
    _reject_symlink_chain(candidate_path, stop_code="input_path_mismatch", label=key)
    resolved_cand = candidate_path.resolve()
    if resolved_cand != _expected_canonical_path(expected_path):
        raise DiagnosticStopError(
            "input_path_mismatch",
            f"{key} resolved path {resolved_cand} != canonical {_expected_canonical_path(expected_path)}",
        )

    # Verify full confinement inside upstream_run_root (including all ancestors above upstream_run_root)
    if key in ("ledger_jsonl", "summary_json", "coverage_json"):
        _reject_symlink_chain(upstream_run_root, stop_code="input_path_mismatch", label="upstream_run_root")
        if not upstream_run_root.is_dir():
            raise DiagnosticStopError("input_path_mismatch", f"upstream_run_root is not directory: {upstream_run_root}")
        resolved_up = upstream_run_root.resolve()
        if resolved_up != _expected_canonical_path(upstream_run_root):
            raise DiagnosticStopError(
                "input_path_mismatch",
                f"upstream_run_root resolved path {resolved_up} != canonical {_expected_canonical_path(upstream_run_root)}",
            )
        try:
            rel_sub = expected_path.relative_to(upstream_run_root)
        except ValueError as exc:
            raise DiagnosticStopError(
                "input_path_mismatch", f"{key} not inside upstream_run_root {upstream_run_root}"
            ) from exc
        if not resolved_cand.is_relative_to(resolved_up) or resolved_cand != (resolved_up / rel_sub):
            raise DiagnosticStopError("input_path_mismatch", f"{key} resolved path escaped upstream_run_root")

    if not candidate_path.is_file():
        raise DiagnosticStopError("input_identity_mismatch", f"{key} missing regular file: {candidate_path}")

    st = candidate_path.lstat()
    actual_sha = _stream_sha256(candidate_path, stop_code="input_identity_mismatch")
    if actual_sha.lower() != expected_sha.lower():
        raise DiagnosticStopError(
            "input_identity_mismatch",
            f"{key} SHA-256 {actual_sha} != expected {expected_sha}",
        )
    return actual_sha, resolved_cand, (int(st.st_dev), int(st.st_ino))


def _validate_new_output_root(output_root: Path, allowed_parent: Path) -> None:
    if not output_root.is_absolute() or ".." in output_root.parts:
        raise DiagnosticStopError("output_path_invalid", f"output_root must be clean absolute path: {output_root}")
    if output_root.parent != allowed_parent or not output_root.name.strip():
        raise DiagnosticStopError(
            "output_path_invalid",
            f"output_root {output_root} must be a direct child of {allowed_parent}",
        )
    _reject_symlink_chain(allowed_parent, stop_code="output_path_invalid", label="allowed_output_parent")
    _reject_symlink_chain(output_root, stop_code="output_path_invalid", label="output_root")
    if allowed_parent.exists() and not allowed_parent.is_dir():
        raise DiagnosticStopError("output_path_invalid", f"allowed_parent is not a directory: {allowed_parent}")
    resolved_parent = allowed_parent.resolve()
    resolved_out = output_root.resolve()
    if resolved_out.parent != resolved_parent or not resolved_out.is_relative_to(resolved_parent):
        raise DiagnosticStopError(
            "output_path_invalid",
            f"resolved output_root {resolved_out} escaped allowed_parent {resolved_parent}",
        )
    if output_root.exists():
        raise DiagnosticStopError("existing_output_path", f"output_root already exists: {output_root}")


def _validate_binding_payload(
    binding: Any,
    *,
    expected_plan_sha: str | None,
) -> tuple[dict[str, Any], Path, dict[str, tuple[Path, tuple[int, int]]]]:
    if not isinstance(binding, dict):
        raise DiagnosticStopError("source_binding_mismatch", "source_binding root must be object")
    if _req_int(binding, "binding_version", "source_binding_mismatch", "binding") != 1:
        raise DiagnosticStopError("source_binding_mismatch", "unsupported binding_version")

    auth = binding["authority"] if "authority" in binding and isinstance(binding["authority"], dict) else None
    if auth is None:
        raise DiagnosticStopError("source_binding_mismatch", "missing authority object")
    if _req_str(auth, "repo_root", "source_binding_mismatch", "authority") != str(REPO_ROOT):
        raise DiagnosticStopError("source_binding_mismatch", "repo_root mismatch")
    if _req_str(auth, "design_path", "source_binding_mismatch", "authority") != DESIGN_REL_PATH:
        raise DiagnosticStopError("source_binding_mismatch", "design_path mismatch")
    design_sha = _req_str(auth, "design_sha256", "source_binding_mismatch", "authority")
    if design_sha.lower() != EXPECTED_DESIGN_SHA256.lower():
        raise DiagnosticStopError("source_binding_mismatch", "design_sha256 mismatch")
    _reject_symlink_chain(REPO_ROOT / DESIGN_REL_PATH, stop_code="source_binding_mismatch", label="design_path")
    if _stream_sha256(REPO_ROOT / DESIGN_REL_PATH, stop_code="source_binding_mismatch").lower() != design_sha.lower():
        raise DiagnosticStopError("source_binding_mismatch", "on-disk Design SHA-256 mismatch")

    if _req_str(auth, "plan_path", "source_binding_mismatch", "authority") != PLAN_REL_PATH:
        raise DiagnosticStopError("source_binding_mismatch", "plan_path mismatch")
    plan_sha = _req_str(auth, "plan_sha256", "source_binding_mismatch", "authority")
    if expected_plan_sha is not None and plan_sha.lower() != expected_plan_sha.lower():
        raise DiagnosticStopError("source_binding_mismatch", "plan_sha256 != approved-plan-sha")
    _reject_symlink_chain(REPO_ROOT / PLAN_REL_PATH, stop_code="source_binding_mismatch", label="plan_path")
    if _stream_sha256(REPO_ROOT / PLAN_REL_PATH, stop_code="source_binding_mismatch").lower() != plan_sha.lower():
        raise DiagnosticStopError("source_binding_mismatch", "on-disk Plan SHA-256 mismatch")
    rec_head = _req_str(auth, "git_head", "source_binding_mismatch", "authority")
    if rec_head != _git_head(REPO_ROOT):
        raise DiagnosticStopError("source_binding_mismatch", "git_head mismatch against current repository HEAD")

    if "environment" not in binding or not isinstance(binding["environment"], dict):
        raise DiagnosticStopError("source_binding_mismatch", "missing environment object")
    env = binding["environment"]
    if _req_str(env, "python_executable", "code_identity_mismatch", "environment") != str(
        Path(sys.executable).resolve()
    ):
        raise DiagnosticStopError("code_identity_mismatch", "python_executable mismatch against active interpreter")
    if _req_str(env, "python_version", "code_identity_mismatch", "environment") != platform.python_version():
        raise DiagnosticStopError("code_identity_mismatch", "python_version mismatch against active interpreter")
    mod_file = getattr(diag_mod, "__file__", None)
    if not isinstance(mod_file, str) or _req_str(
        env, "helper_module_file", "code_identity_mismatch", "environment"
    ) != str(Path(mod_file).resolve()):
        raise DiagnosticStopError("code_identity_mismatch", "helper_module_file mismatch")

    verify_base_and_safety_config()
    if "protocol" not in binding or not isinstance(binding["protocol"], dict):
        raise DiagnosticStopError("source_binding_mismatch", "missing protocol object")
    if any(isinstance(v, bool) for v in binding["protocol"].values()):
        raise DiagnosticStopError("source_binding_mismatch", "protocol values must not be bool")
    proto = validate_protocol(binding["protocol"])

    # Verify code bindings against current files on disk
    actual_code = _verify_helper_origin_and_code_bindings()
    if "code_bindings" not in binding or binding["code_bindings"] != actual_code:
        raise DiagnosticStopError(
            "code_identity_mismatch",
            "code_bindings mismatch against on-disk implementation/helper/config files",
        )

    # Verify all 4 fixed inputs strictly against FIXED_INPUT_SPECS (zero recursion into raw ZIPs)
    if "fixed_inputs" not in binding or not isinstance(binding["fixed_inputs"], dict):
        raise DiagnosticStopError("source_binding_mismatch", "missing fixed_inputs object")
    fi = binding["fixed_inputs"]
    if set(fi.keys()) != set(FIXED_INPUT_SPECS.keys()):
        raise DiagnosticStopError("source_binding_mismatch", "fixed_inputs key set mismatch")
    input_snapshots: dict[str, tuple[Path, tuple[int, int]]] = {}
    for k, (exp_p, exp_sha) in FIXED_INPUT_SPECS.items():
        entry = fi[k]
        if not isinstance(entry, dict):
            raise DiagnosticStopError("source_binding_mismatch", f"fixed_inputs.{k} must be object")
        raw_path_str = _req_str(entry, "path", "input_path_mismatch", f"fixed_inputs.{k}")
        if raw_path_str != str(exp_p):
            raise DiagnosticStopError(
                "input_path_mismatch",
                f"fixed_inputs.{k}.path {raw_path_str!r} != frozen {str(exp_p)!r}",
            )
        rec_path = Path(raw_path_str)
        rec_sha = _req_str(entry, "sha256", "input_identity_mismatch", f"fixed_inputs.{k}")
        if rec_sha.lower() != exp_sha.lower():
            raise DiagnosticStopError("input_identity_mismatch", f"fixed_inputs.{k} recorded sha256 mismatch")
        _v_sha, resolved_p, dev_ino = _verify_confined_fixed_input(
            key=k,
            candidate_path=rec_path,
            expected_path=exp_p,
            expected_sha=exp_sha,
            upstream_run_root=EXPECTED_UPSTREAM_RUN_ROOT,
        )
        input_snapshots[k] = (resolved_p, dev_ino)
    up_st = EXPECTED_UPSTREAM_RUN_ROOT.lstat()
    input_snapshots["__upstream_run_root__"] = (
        EXPECTED_UPSTREAM_RUN_ROOT.resolve(),
        (int(up_st.st_dev), int(up_st.st_ino)),
    )

    if "output" not in binding or not isinstance(binding["output"], dict):
        raise DiagnosticStopError("source_binding_mismatch", "missing output object")
    out_raw_str = _req_str(binding["output"], "output_root", "output_path_invalid", "output")
    out_root = Path(out_raw_str)
    _validate_new_output_root(out_root, ALLOWED_OUTPUT_PARENT)

    return proto, out_root, input_snapshots


def _cmd_prepare(args: argparse.Namespace) -> int:
    binding_out = Path(args.binding_output)
    output_root = Path(args.output_root)

    if not binding_out.is_absolute() or ".." in binding_out.parts:
        raise DiagnosticStopError("output_path_invalid", f"binding_output must be clean absolute path: {binding_out}")
    if binding_out.is_symlink() or binding_out.exists():
        raise DiagnosticStopError("existing_output_path", f"binding_output already exists: {binding_out}")
    _reject_symlink_chain(binding_out, stop_code="output_path_invalid", label="binding_output")
    resolved_bout = binding_out.resolve()
    if resolved_bout.is_relative_to(REPO_ROOT.resolve()) or resolved_bout.is_relative_to(
        EXPECTED_UPSTREAM_RUN_ROOT.resolve()
    ):
        raise DiagnosticStopError(
            "output_path_invalid",
            f"binding_output {binding_out} must not reside inside repository or upstream run root",
        )
    _validate_new_output_root(output_root, ALLOWED_OUTPUT_PARENT)

    verify_base_and_safety_config()
    proto = build_default_protocol()

    design_sha = _stream_sha256(REPO_ROOT / DESIGN_REL_PATH, stop_code="source_binding_mismatch")
    if design_sha.lower() != EXPECTED_DESIGN_SHA256.lower():
        raise DiagnosticStopError("source_binding_mismatch", "Design SHA-256 mismatch on disk")

    plan_sha = _stream_sha256(REPO_ROOT / PLAN_REL_PATH, stop_code="source_binding_mismatch")
    if plan_sha.lower() != str(args.approved_plan_sha).strip().lower():
        raise DiagnosticStopError(
            "source_binding_mismatch",
            f"Plan SHA-256 {plan_sha} != --approved-plan-sha {args.approved_plan_sha}",
        )

    code_bindings = _verify_helper_origin_and_code_bindings()

    # Stream byte digests ONLY of the 4 fixed inputs (DO NOT parse ledger.jsonl in prepare!)
    fixed_inputs_out: dict[str, dict[str, str]] = {}
    for k, (exp_p, exp_sha) in FIXED_INPUT_SPECS.items():
        verified_sha, _res_p, _dev_ino = _verify_confined_fixed_input(
            key=k,
            candidate_path=exp_p,
            expected_path=exp_p,
            expected_sha=exp_sha,
            upstream_run_root=EXPECTED_UPSTREAM_RUN_ROOT,
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
            "helper_module_file": str(Path(diag_mod.__file__).resolve()),
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

    # Self-validate written binding via shared validator
    written_parsed = _loads_strict_json(
        binding_out.read_text(encoding="utf-8"),
        stop_code="source_binding_mismatch",
        ctx="source_binding",
    )
    _validate_binding_payload(written_parsed, expected_plan_sha=args.approved_plan_sha)
    b_sha = _stream_sha256(binding_out, stop_code="source_binding_mismatch")
    print(f"PREPARED_BINDING={binding_out} SHA256={b_sha}")
    return 0


def _render_report_markdown(summary: dict[str, Any], binding_sha: str, output_root: Path) -> str:
    def f4(x: float | None) -> str:
        return "null" if x is None else f"{x:.4f}"

    def fpct(x: float | None) -> str:
        return "null" if x is None else f"{x * 100.0:.2f}%"

    cnt = summary["counts"]
    rt = summary["routing"]
    boot_mu = summary["bootstrap"]["mu_joint_all_bps"]
    boot_de = summary["bootstrap"]["delta_bps"]
    eval_start = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)

    lines: list[str] = [
        "# Stage 1.3 量价共振：固定走强事件的放量条件增量诊断报告（`report_CN.md`）",
        "",
        f"- **生成时间（UTC）**：`{summary['generated_at_utc']}`",
        f"- **输出目录（`output_root`）**：`{output_root}`",
        f"- **绑定 `source_binding.json` SHA-256**：`{binding_sha}`",
        "- **阶段与权限边界**：`exploratory_only = true`（已暴露区间探索）、`cost_mode = cost_context_only`、"
        "`live_trading_enabled = false`、`paper_trading_allowed = false`、`execution_engine_allowed = false`。"
        "本报告仅回答固定 `relative_strength_vs_btc` 接纳队列 `Q` 内附加既有放量条件 `A>=3.0` 的同币同周样本差异，"
        "**不构成独立样本外证明、因果识别、四格交互效应、全市场 Alpha、旧组合候选恢复或任何交易权限**。",
        "",
        "## 1. 核心结果与分流",
        "",
        f"- **固定队列分母守恒**：`N(Q) = {cnt['q_total']}` = 全共振 `N(A=1,B=1) = {cnt['joint_all_count']}` "
        f"+ 仅走强 `N(A=0,B=1) = {cnt['b_only_all_count']}`",
        f"- **共同支持划分**：支持内共振 `{cnt['joint_supported_count']}` / 未匹配共振 `{cnt['joint_unmatched_count']}`；"
        f"共同支持层数 `{cnt['common_support_strata_count']} / {cnt['total_strata']}`",
        "- **四个核心估计量（bps）**：",
        f"  - 全体共振均值 `mu_joint_all_bps` = `{f4(summary['mu_joint_all_bps'])}`",
        f"  - 支持内共振均值 `mu_joint_supported_bps` = `{f4(summary['mu_joint_supported_bps'])}`",
        f"  - 同层重加权对照均值 `mu_control_reweighted_bps` = `{f4(summary['mu_control_reweighted_bps'])}`",
        f"  - 条件增量 `delta_bps`（仅描述共同支持 `S` 内） = `{f4(summary['delta_bps'])}`",
        "- **23 块联合重采样（10,000 次，seed `20261123`）名义区间**：",
        f"  - `mu_joint_all_bps`：`[{f4(boot_mu['ci_025'])}, {f4(boot_mu['ci_975'])}]` "
        f"（有效 `{boot_mu['valid_replicates']}` / 空 `{boot_mu['empty_replicates']}`，`ci_complete={boot_mu['ci_complete']}`）",
        f"  - `delta_bps`：`[{f4(boot_de['ci_025'])}, {f4(boot_de['ci_975'])}]` "
        f"（有效 `{boot_de['valid_replicates']}` / 空 `{boot_de['empty_replicates']}`，`ci_complete={boot_de['ci_complete']}`）",
        f"- **全共振组往返成本情景（`cost_context_only`，`c_break_even_bps = {f4(summary['c_break_even_bps'])}`，`minimum_economically_meaningful_gain = null`）**：",
        f"  - `30 bps`：`mean={f4(summary['cost_scenarios_joint_all']['30.0']['mean_bps'])}`，"
        f"`P05={f4(summary['cost_scenarios_joint_all']['30.0']['quantiles_bps']['p05'])}`，"
        f"`P10={f4(summary['cost_scenarios_joint_all']['30.0']['quantiles_bps']['p10'])}`，"
        f"`P50={f4(summary['cost_scenarios_joint_all']['30.0']['quantiles_bps']['p50'])}`，"
        f"`worst={f4(summary['cost_scenarios_joint_all']['30.0']['worst_event_bps'])}`",
        f"  - `50 bps`：`mean={f4(summary['cost_scenarios_joint_all']['50.0']['mean_bps'])}`，"
        f"`P05={f4(summary['cost_scenarios_joint_all']['50.0']['quantiles_bps']['p05'])}`，"
        f"`P10={f4(summary['cost_scenarios_joint_all']['50.0']['quantiles_bps']['p10'])}`，"
        f"`P50={f4(summary['cost_scenarios_joint_all']['50.0']['quantiles_bps']['p50'])}`，"
        f"`worst={f4(summary['cost_scenarios_joint_all']['50.0']['worst_event_bps'])}`",
        f"  - `80 bps`：`mean={f4(summary['cost_scenarios_joint_all']['80.0']['mean_bps'])}`，"
        f"`P05={f4(summary['cost_scenarios_joint_all']['80.0']['quantiles_bps']['p05'])}`，"
        f"`P10={f4(summary['cost_scenarios_joint_all']['80.0']['quantiles_bps']['p10'])}`，"
        f"`P50={f4(summary['cost_scenarios_joint_all']['80.0']['quantiles_bps']['p50'])}`，"
        f"`worst={f4(summary['cost_scenarios_joint_all']['80.0']['worst_event_bps'])}`",
        f"- **结果分流**：`observation_label = {rt['observation_label']}`，"
        f"`resource_decision = {rt['resource_decision']}`，`alpha_research_status = {rt['alpha_research_status']}`",
        "",
        "## 2. 组分布与路径包络（Gross 4h）",
        "",
        "| 组别 | `n` | `mean` (bps) | `median` (bps) | `win_rate` | `P10` | `P25` | `P75` | `P90` | `worst` (bps) | `MFE P50/max` | `MAE P50/min` |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for gkey, glabel in (
        ("joint_all", "全共振 `A=1,B=1`"),
        ("joint_supported", "支持内共振 `(A=1,B=1) in S`"),
        ("b_only_all", "全部仅走强 `A=0,B=1`"),
    ):
        d = summary["distributions"][gkey]
        q = d["quantiles_bps"]
        mfe = d["mfe_4h_gross_bps"]
        mae = d["mae_4h_gross_bps"]
        lines.append(
            f"| {glabel} | {d['n']} | {f4(d['mean_bps'])} | {f4(d['median_bps'])} | {fpct(d['win_rate'])} | "
            f"{f4(q['p10'])} | {f4(q['p25'])} | {f4(q['p75'])} | {f4(q['p90'])} | {f4(d['worst_event_bps'])} | "
            f"`{f4(mfe['p50'])} / {f4(mfe['max'])}` | `{f4(mae['p50'])} / {f4(mae['min'])}` |"
        )

    pc = summary["positive_contribution_joint_all"]
    diag = summary["diagnostics"]
    lines.extend(
        [
            "",
            "## 3. 正收益集中度、两半切分与剔除稳健性",
            "",
            f"- **全共振正贡献（分母 `N_joint = {pc['n']}`，正收益数 `{pc['positive_count']}`）**："
            f"`top_1 = {fpct(pc['top_1_share'])}`，`top_3 = {fpct(pc['top_3_share'])}`，"
            f"`top_10pct = {fpct(pc['top_10pct_share'])}`",
            f"- **去掉最佳共振单事件后**：`mu_joint_all_bps = {f4(diag['without_best_joint_event']['mu_joint_all_bps'])}`，"
            f"`delta_bps = {f4(diag['without_best_joint_event']['delta_bps'])}`",
            f"- **前半段（Blocks 0–10）**：`n={diag['first_half_blocks_0_10']['joint_all_count']}` "
            f"（支持 `{diag['first_half_blocks_0_10']['joint_supported_count']}`），"
            f"`mu={f4(diag['first_half_blocks_0_10']['mu_joint_all_bps'])}`，"
            f"`delta={f4(diag['first_half_blocks_0_10']['delta_bps'])}`",
            f"- **后半段（Blocks 11–22）**：`n={diag['second_half_blocks_11_22']['joint_all_count']}` "
            f"（支持 `{diag['second_half_blocks_11_22']['joint_supported_count']}`），"
            f"`mu={f4(diag['second_half_blocks_11_22']['mu_joint_all_bps'])}`，"
            f"`delta={f4(diag['second_half_blocks_11_22']['delta_bps'])}`",
            "",
            "### 3.1 逐币统计与逐币剔除（Leave-One-Symbol-Out）",
            "",
            "| 交易对 | `Q` | `joint_all` (`supported`/`unmatched`) | `b_only` | 该币 `mu_joint_all` | 该币 `delta` | 剔除该币后 `mu_joint_all` | 剔除该币后 `delta` |",
            "|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for sym in summary["target_symbols"]:
        ps = diag["per_symbol"][sym]
        lo = diag["leave_one_symbol_out"][sym]
        lines.append(
            f"| `{sym}` | {ps['q_count']} | {ps['joint_all_count']} ({ps['joint_supported_count']}/{ps['joint_unmatched_count']}) | "
            f"{ps['b_only_count']} | {f4(ps['mu_joint_all_bps'])} | {f4(ps['delta_bps'])} | "
            f"{f4(lo['mu_joint_all_bps'])} | {f4(lo['delta_bps'])} |"
        )

    lines.extend(
        [
            "",
            "### 3.2 23 个 7d 市场块明细与逐块剔除（Leave-One-Block-Out）",
            "",
            "| `block_id` | UTC 周区间 | `Q` | `joint` (`supp`/`unm`) | `b_only` | 块内 `mu_joint_all` | 块内 `delta` | 剔除该块后 `mu_joint_all` | 剔除该块后 `delta` |",
            "|---:|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for pb in diag["per_block"]:
        bid = int(pb["block_id"])
        s_dt = eval_start + timedelta(days=7 * bid)
        e_dt = s_dt + timedelta(days=7)
        lb = diag["leave_one_block_out"][str(bid)]
        lines.append(
            f"| {bid} | `{s_dt.strftime('%Y-%m-%d')}..{e_dt.strftime('%Y-%m-%d')}` | {pb['q_count']} | "
            f"{pb['joint_all_count']} ({pb['joint_supported_count']}/{pb['joint_unmatched_count']}) | {pb['b_only_count']} | "
            f"{f4(pb['mu_joint_all_bps'])} | {f4(pb['delta_bps'])} | "
            f"{f4(lb['mu_joint_all_bps'])} | {f4(lb['delta_bps'])} |"
        )

    comp = summary["comparability"]
    lines.extend(
        [
            "",
            "## 4. 入场前特征可比性披露与方法边界",
            "",
            f"- **全共振组入场前特征**：`self_r1h` 均值 `{f4(comp['joint_all']['self_r1h_bps']['mean'])} bps` "
            f"（`P50={f4(comp['joint_all']['self_r1h_bps']['p50'])}`），"
            f"B 走强 `z_score` 均值 `{f4(comp['joint_all']['b_trigger_z']['mean'])}` "
            f"（`P50={f4(comp['joint_all']['b_trigger_z']['p50'])}`）",
            f"- **全部 B-only 组入场前特征**：`self_r1h` 均值 `{f4(comp['b_only_all']['self_r1h_bps']['mean'])} bps` "
            f"（`P50={f4(comp['b_only_all']['self_r1h_bps']['p50'])}`），"
            f"B 走强 `z_score` 均值 `{f4(comp['b_only_all']['b_trigger_z']['mean'])}` "
            f"（`P50={f4(comp['b_only_all']['b_trigger_z']['p50'])}`）",
            "- **限制声明**：",
            "  1. `mu_joint_all_bps` 描述固定 `Q` 的全部共振事件，而 `delta_bps` 仅描述共同支持 `S` 内的同币同周条件差异；存在未匹配层时严禁将 `delta_bps` 外推至全队列。",
            "  2. 共同支持与同周 B-only 对照包含事件后同周观察，属事后回顾性状态对照，不可作为实时交易过滤器。",
            "  3. 同币同周仅粗略控制币种与周度市场环境，未控制走强幅度、波动率、beta 或盘口深度；4h `MAE`/`MFE` 不提供同根 bar 先后顺序，不可推导可执行止损；成本仅为 `30/50/80 bps` 情景扣减。",
            "  4. 评价区间 `[2026-06-15, 2026-11-23)` 已在既有研究中暴露，非独立样本外（OOS）；最多 23 个观察块且相邻块可能相关。",
        ]
    )
    return "\n".join(lines) + "\n"


def _validate_upstream_provenance(
    *,
    manifest_obj: Any,
    coverage_obj: Any,
    summary_obj: Any,
    expected_manifest_sha: str,
    protocol: dict[str, Any],
) -> dict[str, dict[str, int]]:
    if not isinstance(manifest_obj, dict) or not isinstance(coverage_obj, dict) or not isinstance(summary_obj, dict):
        raise DiagnosticStopError("upstream_provenance_mismatch", "manifest/coverage/summary must be JSON objects")

    if (
        "coverage_qualified" not in coverage_obj
        or coverage_obj["coverage_qualified"] is not True
        or "stop_code" not in coverage_obj
        or coverage_obj["stop_code"] is not None
    ):
        raise DiagnosticStopError("upstream_provenance_mismatch", "upstream coverage.json is not qualified")

    cov_msha = _req_str(coverage_obj, "manifest_sha256", "upstream_provenance_mismatch", "coverage")
    sum_msha = _req_str(summary_obj, "manifest_sha256", "upstream_provenance_mismatch", "summary")
    if cov_msha.lower() != expected_manifest_sha.lower() or sum_msha.lower() != expected_manifest_sha.lower():
        raise DiagnosticStopError("upstream_provenance_mismatch", "upstream manifest_sha256 mismatch")

    if "output" not in manifest_obj or not isinstance(manifest_obj["output"], dict):
        raise DiagnosticStopError("upstream_provenance_mismatch", "manifest missing output object")
    manifest_run_root_str = _req_str(manifest_obj["output"], "run_root", "upstream_provenance_mismatch", "manifest.output")
    if manifest_run_root_str != str(EXPECTED_UPSTREAM_RUN_ROOT):
        raise DiagnosticStopError("upstream_provenance_mismatch", "manifest run_root != EXPECTED_UPSTREAM_RUN_ROOT")

    for label, doc in (("manifest", manifest_obj), ("summary", summary_obj)):
        if "authority" not in doc or not isinstance(doc["authority"], dict):
            raise DiagnosticStopError("upstream_provenance_mismatch", f"{label} missing authority")
        au = doc["authority"]
        if (
            _req_str(au, "design_path", "upstream_provenance_mismatch", f"{label}.authority") != PRIOR_DESIGN_REL_PATH
            or _req_str(au, "design_sha256", "upstream_provenance_mismatch", f"{label}.authority").lower()
            != PRIOR_DESIGN_SHA256.lower()
            or _req_str(au, "plan_path", "upstream_provenance_mismatch", f"{label}.authority") != PRIOR_PLAN_REL_PATH
            or _req_str(au, "plan_sha256", "upstream_provenance_mismatch", f"{label}.authority").lower()
            != PRIOR_PLAN_SHA256.lower()
        ):
            raise DiagnosticStopError("upstream_provenance_mismatch", f"{label} prior authority mismatch")
        if "protocol" not in doc or not isinstance(doc["protocol"], dict):
            raise DiagnosticStopError("upstream_provenance_mismatch", f"{label} missing protocol")
        if any(isinstance(v, bool) for v in doc["protocol"].values()):
            raise DiagnosticStopError("upstream_provenance_mismatch", f"{label} protocol values must not be bool")
        try:
            validate_protocol(doc["protocol"])
        except DiagnosticStopError as exc:
            raise DiagnosticStopError("upstream_provenance_mismatch", f"{label} protocol mismatch: {exc}") from exc

    if "candidates" not in summary_obj or not isinstance(summary_obj["candidates"], dict):
        raise DiagnosticStopError("upstream_provenance_mismatch", "upstream summary missing candidates")

    dp_per_sym = (int(protocol["eval_end_ms"]) - int(protocol["eval_start_ms"])) // int(protocol["bar_interval_ms"])
    expected_dp_total_by_cand = {
        CAND_A: len(protocol["symbols"]) * dp_per_sym,
        CAND_B: (len(protocol["symbols"]) - 1) * dp_per_sym,
    }
    expected_counts: dict[str, dict[str, int]] = {}
    for cand in (CAND_A, CAND_B):
        if cand not in summary_obj["candidates"] or not isinstance(summary_obj["candidates"][cand], dict):
            raise DiagnosticStopError("upstream_provenance_mismatch", f"upstream summary missing candidate {cand}")
        cand_obj = summary_obj["candidates"][cand]
        if "counts" not in cand_obj or not isinstance(cand_obj["counts"], dict):
            raise DiagnosticStopError("upstream_provenance_mismatch", f"upstream summary.{cand} missing counts")
        c_counts = cand_obj["counts"]
        st_map = {
            st: _req_int(c_counts, st, "upstream_provenance_mismatch", f"summary.{cand}.counts")
            for st in ALLOWED_ROW_STATUSES
        }
        total_eval_dp = _req_int(
            c_counts, "total_eval_decision_points", "upstream_provenance_mismatch", f"summary.{cand}.counts"
        )
        if sum(st_map.values()) != total_eval_dp or total_eval_dp != expected_dp_total_by_cand[cand]:
            raise DiagnosticStopError(
                "upstream_provenance_mismatch",
                f"upstream summary.{cand} decision-point denominator mismatch: sum={sum(st_map.values())}, total={total_eval_dp}",
            )
        expected_counts[cand] = st_map
    return expected_counts


def _verify_binding_file_identity(binding_path: Path, expected_bsha: str) -> tuple[str, Path, tuple[int, int]]:
    _reject_symlink_chain(binding_path, stop_code="source_binding_mismatch", label="binding_path")
    resolved_b = binding_path.resolve()
    if resolved_b != _expected_canonical_path(binding_path):
        raise DiagnosticStopError(
            "source_binding_mismatch",
            f"binding_path resolved {resolved_b} != canonical {_expected_canonical_path(binding_path)}",
        )
    if not binding_path.is_file():
        raise DiagnosticStopError("source_binding_mismatch", f"missing regular binding file: {binding_path}")
    bst = binding_path.lstat()
    actual_bsha = _stream_sha256(binding_path, stop_code="source_binding_mismatch")
    if actual_bsha.lower() != expected_bsha.lower():
        raise DiagnosticStopError(
            "source_binding_mismatch",
            f"binding SHA-256 {actual_bsha} != --binding-sha {expected_bsha}",
        )
    return actual_bsha, resolved_b, (int(bst.st_dev), int(bst.st_ino))


def _cmd_run(args: argparse.Namespace) -> int:
    binding_path = Path(args.binding)
    expected_bsha = str(args.binding_sha).strip()
    actual_bsha, pre_b_resolved, pre_b_dev_ino = _verify_binding_file_identity(binding_path, expected_bsha)

    binding_obj = _loads_strict_json(
        binding_path.read_text(encoding="utf-8"),
        stop_code="source_binding_mismatch",
        ctx="source_binding",
    )
    proto, output_root, pre_input_snapshots = _validate_binding_payload(binding_obj, expected_plan_sha=None)

    # Read ONLY the 4 fixed files (NEVER touch raw archives or identity files referenced inside them)
    ledger_path, _ledger_sha = FIXED_INPUT_SPECS["ledger_jsonl"]
    summary_path, _summary_sha = FIXED_INPUT_SPECS["summary_json"]
    coverage_path, _coverage_sha = FIXED_INPUT_SPECS["coverage_json"]
    manifest_path, manifest_sha = FIXED_INPUT_SPECS["source_manifest_json"]

    manifest_obj = _loads_strict_json(
        manifest_path.read_text(encoding="utf-8"),
        stop_code="upstream_provenance_mismatch",
        ctx="source_manifest.json",
    )
    coverage_obj = _loads_strict_json(
        coverage_path.read_text(encoding="utf-8"),
        stop_code="upstream_provenance_mismatch",
        ctx="coverage.json",
    )
    up_summary_obj = _loads_strict_json(
        summary_path.read_text(encoding="utf-8"),
        stop_code="upstream_provenance_mismatch",
        ctx="summary.json",
    )
    expected_up_counts = _validate_upstream_provenance(
        manifest_obj=manifest_obj,
        coverage_obj=coverage_obj,
        summary_obj=up_summary_obj,
        expected_manifest_sha=manifest_sha,
        protocol=proto,
    )

    rows: list[dict[str, Any]] = []
    with ledger_path.open("r", encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, 1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            rows.append(
                _loads_strict_json(
                    stripped,
                    stop_code="cohort_contract_mismatch",
                    ctx=f"ledger.jsonl:{line_no}",
                )
            )

    cohort = build_cohort(rows, protocol=proto)

    # Cross-check full decision-point counts against upstream summary & fixed B admitted count
    for cand in (CAND_A, CAND_B):
        if cohort["status_counts_by_candidate"][cand] != expected_up_counts[cand]:
            raise DiagnosticStopError(
                "cohort_contract_mismatch",
                f"{cand} status counts {cohort['status_counts_by_candidate'][cand]} != upstream summary {expected_up_counts[cand]}",
            )
    if int(cohort["counts"]["q_total"]) != int(EXPECTED_B_ADMITTED_COUNT):
        raise DiagnosticStopError(
            "cohort_contract_mismatch",
            f"B admitted count {cohort['counts']['q_total']} != expected {EXPECTED_B_ADMITTED_COUNT}",
        )

    result = summarize_cohort(cohort, protocol=proto)
    summary_out = dict(result["summary"])
    summary_out["generated_at_utc"] = _utc_now()
    summary_out["source_binding_sha256"] = actual_bsha.lower()
    summary_out["fixed_inputs"] = {
        k: {"path": str(p), "sha256": s} for k, (p, s) in FIXED_INPUT_SPECS.items()
    }

    # Serialize all outputs strictly (allow_nan=False) in memory BEFORE creating output_root
    members_lines = [
        json.dumps(m, ensure_ascii=False, allow_nan=False) for m in result["members"]
    ]
    members_text = ("\n".join(members_lines) + "\n") if members_lines else ""
    summary_text = json.dumps(summary_out, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    report_text = _render_report_markdown(summary_out, actual_bsha.lower(), output_root)

    # Unified post-read / pre-publish full path, ancestor-symlink, inode, code, and SHA-256 re-verification
    try:
        _post_bsha, post_b_resolved, post_b_dev_ino = _verify_binding_file_identity(binding_path, actual_bsha)
        if post_b_resolved != pre_b_resolved or post_b_dev_ino != pre_b_dev_ino:
            raise DiagnosticStopError("input_mutated_during_run", "binding_path relocated or replaced during run")
        post_binding_obj = _loads_strict_json(
            binding_path.read_text(encoding="utf-8"),
            stop_code="input_mutated_during_run",
            ctx="source_binding_post_read",
        )
        _post_proto, _post_out_root, post_input_snapshots = _validate_binding_payload(
            post_binding_obj, expected_plan_sha=None
        )
        if post_input_snapshots != pre_input_snapshots:
            raise DiagnosticStopError(
                "input_mutated_during_run",
                "fixed input or upstream_run_root resolved path / inode changed during run",
            )
    except DiagnosticStopError as exc:
        if exc.stop_code in ("existing_output_path", "output_path_invalid"):
            raise
        raise DiagnosticStopError("input_mutated_during_run", f"{exc.stop_code}: {exc.detail}") from exc

    ALLOWED_OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=False, exist_ok=False)

    (output_root / "members.jsonl").write_text(members_text, encoding="utf-8")
    (output_root / "summary.json").write_text(summary_text, encoding="utf-8")
    (output_root / "report_CN.md").write_text(report_text, encoding="utf-8")
    (output_root / "EXECUTION_FINISHED").write_text(
        f"EXECUTION_FINISHED_UTC={_utc_now()}\nNOTE=execution_completed_pending_independent_audit_not_complete\n",
        encoding="utf-8",
    )
    print(f"RUN_FINISHED OUTPUT_ROOT={output_root}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage 1.3 volume-strength conditional increment controlled diagnostic CLI."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser("prepare", help="Verify input/code digests and write source_binding.json")
    p_prep.add_argument("--approved-plan-sha", required=True)
    p_prep.add_argument("--binding-output", required=True)
    p_prep.add_argument("--output-root", required=True)

    p_run = sub.add_parser("run", help="Verify binding and execute offline conditional increment diagnostic")
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
        raise DiagnosticStopError("source_binding_mismatch", f"unknown command: {args.command}")
    except DiagnosticStopError as exc:
        print(f"STOP={exc.stop_code} ({exc.detail})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
