#!/usr/bin/env python3
"""Incremental information analysis of launch price, open interest, and basis at Parent level.

Evaluates whether Open Interest and Basis provide descriptive incremental predictive information
beyond baseline pre-observation price change using leave-one-Parent-out OLS regressions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

# Approved snapshot restricted status set per Design §2 (only 'ok' and 'missing_jb_anchor_time')
VALID_OI_STATUSES: Set[str] = {
    "ok",
    "missing_jb_anchor_time",
}

# Fixed Design & Plan bindings per Design §2
FIXED_DESIGN_RELATIVE_PATH: str = (
    "docs/designs/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-design_CN.md"
)
FIXED_DESIGN_SHA256: str = (
    "f38fd9c4609a52cc9d2d6529cceabca35c778e84c374fad4e386029d0493519e"
)
FIXED_PLAN_RELATIVE_PATH: str = (
    "docs/plans/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-implementation-plan_CN.md"
)
FIXED_PLAN_SHA256: str = (
    "fe8dc877323f91725773502eaf606822350f47ed703fc484c5d199e5265fda6f"
)

# Exact snapshot inputs specified in Design §2
FIXED_INPUT_CSV_PATH: Path = Path(
    "/private/tmp/launch_open_interest_basis_exploratory_run_20261103/child_rows.csv"
)
FIXED_INPUT_CSV_SHA256: str = (
    "56afc76bc30dea5b8d0414e320e2d49842ed3b137c4e0bf37c6dca51ce9447c4"
)
FIXED_INPUT_REVIEW_PATH: Path = Path(
    "/private/tmp/launch_open_interest_basis_exploratory_run_20261103/review_CN.md"
)
FIXED_INPUT_REVIEW_SHA256: str = (
    "af4e277728cdabbb5cb4c8e9abf0da6722b001470a66a6c256034e67cc6104dd"
)

# Exact 99 columns written by write_exploratory_outputs
EXPECTED_CSV_HEADER: Tuple[str, ...] = (
    "parent_article_id",
    "symbol",
    "listing_regime",
    "utc_date",
    "is_complete",
    "missing_reason",
    "path_status",
    "oi_status",
    "oi_change",
    "terminal_return",
    "long_mae",
    "long_mfe",
    "basis",
    "entry_price",
    "entry_delay_ms",
    "endpoint_price",
    "oi_l0_time_ms",
    "oi_l1_time_ms",
    "oi_l0",
    "oi_l1",
    "oi_age_ms",
    "oi_assumed_info_l0_ms",
    "oi_assumed_info_l1_ms",
    "oi_assumed_avail_l0_ms",
    "oi_assumed_avail_l1_ms",
    "oi_assumed_avail_age_ms",
    "oi_a_status",
    "oi_a_change",
    "oi_a_l0_time_ms",
    "oi_a_l1_time_ms",
    "oi_a_l0",
    "oi_a_l1",
    "oi_a_age_ms",
    "oi_a_assumed_info_l0_ms",
    "oi_a_assumed_info_l1_ms",
    "oi_a_assumed_avail_l0_ms",
    "oi_a_assumed_avail_l1_ms",
    "oi_a_assumed_avail_age_ms",
    "oi_b_status",
    "oi_b_change",
    "oi_b_l0_time_ms",
    "oi_b_l1_time_ms",
    "oi_b_l0",
    "oi_b_l1",
    "oi_b_age_ms",
    "oi_b_assumed_info_l0_ms",
    "oi_b_assumed_info_l1_ms",
    "oi_b_assumed_avail_l0_ms",
    "oi_b_assumed_avail_l1_ms",
    "oi_b_assumed_avail_age_ms",
    "oi_c_status",
    "oi_c_change",
    "oi_c_l0_time_ms",
    "oi_c_l1_time_ms",
    "oi_c_l0",
    "oi_c_l1",
    "oi_c_age_ms",
    "oi_c_assumed_info_l0_ms",
    "oi_c_assumed_info_l1_ms",
    "oi_c_assumed_avail_l0_ms",
    "oi_c_assumed_avail_l1_ms",
    "oi_c_assumed_avail_age_ms",
    "grid_status",
    "grid_oi_change",
    "grid_l0_time_ms",
    "grid_l1_time_ms",
    "grid_l0",
    "grid_l1",
    "grid_t0_minus_l0_ms",
    "grid_scheduled_minus_l0_ms",
    "grid_coincides_with_main",
    "grid_a_status",
    "grid_a_oi_change",
    "grid_a_l0_time_ms",
    "grid_a_l1_time_ms",
    "grid_a_oi_l0",
    "grid_a_oi_l1",
    "grid_a_coincides",
    "grid_b_status",
    "grid_b_oi_change",
    "grid_b_l0_time_ms",
    "grid_b_l1_time_ms",
    "grid_b_oi_l0",
    "grid_b_oi_l1",
    "grid_b_coincides",
    "grid_c_status",
    "grid_c_oi_change",
    "grid_c_l0_time_ms",
    "grid_c_l1_time_ms",
    "grid_c_oi_l0",
    "grid_c_oi_l1",
    "grid_c_coincides",
    "basis_status",
    "basis_age_ms",
    "baseline_price_change",
    "baseline_total_notional",
    "baseline_taker_buy_share",
    "pit_verification_status",
    "interpretation_status",
)


class IncrementalAnalysisError(Exception):
    """Base exception for launch price, OI, and basis incremental analysis."""


def _compute_sha256_chunked(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _parse_finite_float(val: str, field_name: str, row_loc: str) -> float:
    if not val or not val.strip():
        raise IncrementalAnalysisError(
            f"non_finite_or_empty_value: {field_name} is empty at {row_loc}"
        )
    try:
        fval = float(val.strip())
    except ValueError as exc:
        raise IncrementalAnalysisError(
            f"non_finite_or_empty_value: {field_name} malformed '{val}' at {row_loc}"
        ) from exc
    if not math.isfinite(fval):
        raise IncrementalAnalysisError(
            f"non_finite_or_empty_value: {field_name} is non-finite '{val}' at {row_loc}"
        )
    return fval


def load_snapshot(csv_path: Path, *, expected_sha256: str) -> list[dict[str, Any]]:
    """Loads and strictly validates child_rows.csv snapshot against schema and expected hash."""
    if not csv_path.is_file():
        raise IncrementalAnalysisError(f"snapshot_file_not_found: {csv_path}")

    actual_sha = _compute_sha256_chunked(csv_path)
    if actual_sha.lower() != expected_sha256.lower():
        raise IncrementalAnalysisError(
            f"snapshot_sha256_mismatch: expected {expected_sha256}, got {actual_sha}"
        )

    try:
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                raise IncrementalAnalysisError("snapshot_is_empty")
            if len(header) != len(EXPECTED_CSV_HEADER) or tuple(header) != EXPECTED_CSV_HEADER:
                if len(header) != len(set(header)):
                    raise IncrementalAnalysisError("snapshot_header_mismatch: duplicate_column")
                missing = set(EXPECTED_CSV_HEADER) - set(header)
                if missing:
                    raise IncrementalAnalysisError(
                        f"snapshot_header_mismatch: missing_column: {missing}"
                    )
                raise IncrementalAnalysisError(
                    f"snapshot_header_mismatch: expected {len(EXPECTED_CSV_HEADER)} columns, got {len(header)}"
                )

            rows_out: list[dict[str, Any]] = []
            seen_keys: set[tuple[str, str]] = set()

            for line_idx, raw_row in enumerate(reader, start=2):
                if not raw_row:
                    continue
                if len(raw_row) != len(EXPECTED_CSV_HEADER):
                    raise IncrementalAnalysisError(
                        f"row_field_count_mismatch: line {line_idx} has {len(raw_row)} fields, expected {len(EXPECTED_CSV_HEADER)}"
                    )
                r = dict(zip(EXPECTED_CSV_HEADER, raw_row))
                pid = r["parent_article_id"].strip()
                sym = r["symbol"].strip()
                row_loc = f"{pid}:{sym}:line{line_idx}"

                if not pid or not sym:
                    raise IncrementalAnalysisError(
                        f"missing_identity_key: line {line_idx} has empty pid or sym"
                    )

                key = (pid, sym)
                if key in seen_keys:
                    raise IncrementalAnalysisError(
                        f"duplicate_parent_symbol_key: {pid}, {sym} at line {line_idx}"
                    )
                seen_keys.add(key)

                regime = r["listing_regime"].strip()
                if regime not in ("pre_market", "standard"):
                    raise IncrementalAnalysisError(
                        f"invalid_listing_regime: '{regime}' at {row_loc}"
                    )

                pit_st = r["pit_verification_status"].strip()
                if pit_st != "unverified_scenario_assumption":
                    raise IncrementalAnalysisError(
                        f"unsupported_pit_status: '{pit_st}' at {row_loc}"
                    )

                interp_st = r["interpretation_status"].strip()
                if interp_st != "historical_scenario_only":
                    raise IncrementalAnalysisError(
                        f"unsupported_interpretation_status: '{interp_st}' at {row_loc}"
                    )

                # B alias consistency check
                oi_st = r["oi_status"].strip()
                oi_b_st = r["oi_b_status"].strip()
                if oi_st != oi_b_st:
                    raise IncrementalAnalysisError(
                        f"alias_status_mismatch: oi_status '{oi_st}' != oi_b_status '{oi_b_st}' at {row_loc}"
                    )
                if oi_st not in VALID_OI_STATUSES:
                    raise IncrementalAnalysisError(
                        f"invalid_oi_status: '{oi_st}' at {row_loc}"
                    )

                oi_chg_raw = r["oi_change"].strip()
                oi_b_chg_raw = r["oi_b_change"].strip()
                if (oi_chg_raw == "") != (oi_b_chg_raw == ""):
                    raise IncrementalAnalysisError(
                        f"alias_value_mismatch: oi_change '{oi_chg_raw}' vs oi_b_change '{oi_b_chg_raw}' at {row_loc}"
                    )
                if oi_chg_raw != "":
                    try:
                        v1 = float(oi_chg_raw)
                        v2 = float(oi_b_chg_raw)
                        if not math.isfinite(v1) or not math.isfinite(v2):
                            raise IncrementalAnalysisError(
                                f"non_finite_or_empty_value: alias float is non-finite at {row_loc}"
                            )
                        if abs(v1 - v2) > 1e-9:
                            raise IncrementalAnalysisError(
                                f"alias_value_mismatch: oi_change {v1} != oi_b_change {v2} at {row_loc}"
                            )
                    except ValueError as exc:
                        raise IncrementalAnalysisError(
                            f"non_finite_or_empty_value: alias float parse error at {row_loc}"
                        ) from exc

                path_st = r["path_status"].strip()
                if path_st not in ("ok", "missing_jb_anchor_time"):
                    raise IncrementalAnalysisError(
                        f"invalid_path_status: '{path_st}' at {row_loc}"
                    )

                parsed_row: dict[str, Any] = {
                    "parent_article_id": pid,
                    "symbol": sym,
                    "listing_regime": regime,
                    "utc_date": r["utc_date"].strip(),
                    "is_complete": r["is_complete"].strip().lower() == "true",
                    "missing_reason": r["missing_reason"].strip(),
                    "path_status": path_st,
                    "oi_status": oi_st,
                    "oi_b_status": oi_b_st,
                    "pit_verification_status": pit_st,
                    "interpretation_status": interp_st,
                }

                if path_st == "ok":
                    if oi_st != "ok":
                        raise IncrementalAnalysisError(
                            f"ok_path_has_non_ok_oi_status: oi_status='{oi_st}' at {row_loc}"
                        )
                    # B completeness and missing_reason consistency check
                    is_comp = r["is_complete"].strip().lower() == "true"
                    if not is_comp:
                        raise IncrementalAnalysisError(
                            f"complete_b_has_is_complete_false at {row_loc}"
                        )
                    if r["missing_reason"].strip() != "":
                        raise IncrementalAnalysisError(
                            f"ok_path_has_missing_reason: '{r['missing_reason']}' at {row_loc}"
                        )

                    # Valid UTC date check
                    utc_date_str = r["utc_date"].strip()
                    if not utc_date_str:
                        raise IncrementalAnalysisError(f"ok_path_missing_utc_date at {row_loc}")
                    try:
                        datetime.strptime(utc_date_str, "%Y-%m-%d")
                    except ValueError as exc:
                        raise IncrementalAnalysisError(
                            f"invalid_utc_date_format: '{utc_date_str}' at {row_loc}"
                        ) from exc

                    parsed_row["baseline_price_change"] = _parse_finite_float(
                        r["baseline_price_change"], "baseline_price_change", row_loc
                    )
                    parsed_row["terminal_return"] = _parse_finite_float(
                        r["terminal_return"], "terminal_return", row_loc
                    )
                    parsed_row["long_mae"] = _parse_finite_float(
                        r["long_mae"], "long_mae", row_loc
                    )
                    parsed_row["long_mfe"] = _parse_finite_float(
                        r["long_mfe"], "long_mfe", row_loc
                    )

                    # Scenario OI fields
                    for scn in ("a", "b", "c"):
                        st_key = f"oi_{scn}_status"
                        chg_key = f"oi_{scn}_change"
                        st_val = r[st_key].strip()
                        if st_val not in VALID_OI_STATUSES:
                            raise IncrementalAnalysisError(
                                f"invalid_scenario_oi_status: {st_key}='{st_val}' at {row_loc}"
                            )
                        if st_val != "ok":
                            raise IncrementalAnalysisError(
                                f"invalid_scenario_oi_status: {st_key}='{st_val}' on ok_path at {row_loc}"
                            )
                        parsed_row[st_key] = st_val
                        parsed_row[chg_key] = _parse_finite_float(r[chg_key], chg_key, row_loc)

                    # Basis fields
                    b_st = r["basis_status"].strip()
                    parsed_row["basis_status"] = b_st
                    if b_st == "ok":
                        parsed_row["basis"] = _parse_finite_float(r["basis"], "basis", row_loc)
                    elif b_st == "unverified_product_mapping":
                        if r["basis"].strip() != "":
                            raise IncrementalAnalysisError(
                                f"unverified_basis_has_value: '{r['basis']}' at {row_loc}"
                            )
                        parsed_row["basis"] = None
                    else:
                        raise IncrementalAnalysisError(
                            f"invalid_basis_status_for_ok_path: '{b_st}' at {row_loc}"
                        )
                else:  # missing_jb_anchor_time
                    if r["is_complete"].strip().lower() != "false":
                        raise IncrementalAnalysisError(
                            f"missing_anchor_is_complete_not_false at {row_loc}"
                        )
                    if r["missing_reason"].strip() != "missing_jb_anchor_time":
                        raise IncrementalAnalysisError(
                            f"missing_anchor_reason_mismatch: '{r['missing_reason']}' at {row_loc}"
                        )
                    if oi_st != "missing_jb_anchor_time":
                        raise IncrementalAnalysisError(
                            f"missing_anchor_oi_status_mismatch: oi_status='{oi_st}' at {row_loc}"
                        )
                    if oi_b_st != "missing_jb_anchor_time":
                        raise IncrementalAnalysisError(
                            f"missing_anchor_oi_b_status_mismatch: oi_b_status='{oi_b_st}' at {row_loc}"
                        )
                    for scn in ("a", "b", "c"):
                        scn_st = r[f"oi_{scn}_status"].strip()
                        if scn_st != "missing_jb_anchor_time":
                            raise IncrementalAnalysisError(
                                f"missing_anchor_scenario_status_mismatch: oi_{scn}_status='{scn_st}' at {row_loc}"
                            )
                        parsed_row[f"oi_{scn}_status"] = scn_st
                    if r["basis_status"].strip() != "":
                        raise IncrementalAnalysisError(
                            f"missing_anchor_has_basis_status: '{r['basis_status']}' at {row_loc}"
                        )
                    for fld in (
                        "baseline_price_change",
                        "terminal_return",
                        "long_mae",
                        "long_mfe",
                        "utc_date",
                        "oi_change",
                        "oi_a_change",
                        "oi_b_change",
                        "oi_c_change",
                        "basis",
                    ):
                        if r[fld].strip() != "":
                            raise IncrementalAnalysisError(
                                f"missing_anchor_row_has_finite_values: {fld}='{r[fld]}' at {row_loc}"
                            )
                        parsed_row[fld] = None
                    parsed_row["basis_status"] = ""

                rows_out.append(parsed_row)

            return rows_out
    except Exception as exc:
        if isinstance(exc, IncrementalAnalysisError):
            raise
        raise IncrementalAnalysisError(f"csv_read_error: {exc}") from exc


def _child_is_complete_for_scenario(c: dict[str, Any], scenario: str) -> bool:
    scn_lower = scenario.lower()
    return (
        c["path_status"] == "ok"
        and c.get(f"oi_{scn_lower}_status") == "ok"
        and c.get(f"oi_{scn_lower}_change") is not None
        and c.get("baseline_price_change") is not None
        and c.get("terminal_return") is not None
        and c.get("long_mae") is not None
        and c.get("long_mfe") is not None
        and bool(c.get("utc_date"))
    )


def build_parent_panel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregates child-level rows to Parent-level panel records by regime and scenario."""
    regimes = sorted(set(r["listing_regime"] for r in rows))
    scenarios = ["A", "B", "C"]
    panel: list[dict[str, Any]] = []

    for regime in regimes:
        reg_rows = [r for r in rows if r["listing_regime"] == regime]
        parent_ids = sorted(set(r["parent_article_id"] for r in reg_rows))

        for pid in parent_ids:
            p_children = sorted(
                [r for r in reg_rows if r["parent_article_id"] == pid],
                key=lambda x: x["symbol"],
            )
            req_count = len(p_children)
            child_symbols_str = ",".join(c["symbol"] for c in p_children)

            known_dates = sorted(set(c["utc_date"] for c in p_children if c.get("utc_date")))
            if len(known_dates) == 1:
                parent_utc_date = known_dates[0]
            elif len(known_dates) == 0:
                parent_utc_date = "unknown"
            else:
                parent_utc_date = f"multi_date_conflict:{','.join(known_dates)}"

            for scenario in scenarios:
                scn_lower = scenario.lower()
                complete_children = [
                    c for c in p_children if _child_is_complete_for_scenario(c, scenario)
                ]
                oi_complete = len(complete_children) == req_count

                if oi_complete:
                    p_val = statistics.median([c["baseline_price_change"] for c in p_children])
                    o_val = statistics.median([c[f"oi_{scn_lower}_change"] for c in p_children])
                    y_val = statistics.median([c["terminal_return"] for c in p_children])
                    mae_val = statistics.median([c["long_mae"] for c in p_children])
                    mfe_val = statistics.median([c["long_mfe"] for c in p_children])
                    missing_reasons = ""
                else:
                    p_val = None
                    o_val = None
                    y_val = None
                    mae_val = None
                    mfe_val = None
                    reasons = sorted(
                        set(
                            c.get("missing_reason") or c.get(f"oi_{scn_lower}_status") or "incomplete"
                            for c in p_children
                            if not _child_is_complete_for_scenario(c, scenario)
                        )
                    )
                    missing_reasons = ",".join(reasons)

                basis_eligible = (
                    oi_complete
                    and all(
                        c.get("basis_status") == "ok" and c.get("basis") is not None
                        for c in p_children
                    )
                )
                if basis_eligible:
                    b_val = statistics.median([c["basis"] for c in p_children])
                else:
                    b_val = None

                panel.append(
                    {
                        "parent_article_id": pid,
                        "listing_regime": regime,
                        "scenario": scenario,
                        "utc_date": parent_utc_date,
                        "child_symbols": child_symbols_str,
                        "required_child_count": req_count,
                        "scenario_complete_child_count": len(complete_children),
                        "oi_complete": oi_complete,
                        "basis_complete": basis_eligible,
                        "missing_reasons": missing_reasons,
                        "p": p_val,
                        "o": o_val,
                        "b": b_val,
                        "y": y_val,
                        "long_mae": mae_val,
                        "long_mfe": mfe_val,
                    }
                )

    return panel


def _fit_and_predict_ols(
    X_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray
) -> Optional[float]:
    """Fits OLS using numpy.linalg.lstsq, strictly checking full column rank and N > K."""
    n_train, k_cols = X_train.shape
    if n_train <= k_cols:
        return None
    if np.linalg.matrix_rank(X_train) < k_cols:
        return None
    try:
        beta, residuals, rank, s = np.linalg.lstsq(X_train, y_train, rcond=None)
        pred = float(np.dot(x_test, beta))
        if not math.isfinite(pred):
            return None
        return pred
    except Exception:
        return None


def evaluate_comparisons(panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Evaluates fixed leave-one-Parent-out model comparisons on parent panel."""
    # Group panel by (listing_regime, scenario)
    regimes = sorted(set(r["listing_regime"] for r in panel))
    scenarios = ["A", "B", "C"]
    folds_out: list[dict[str, Any]] = []

    # Comparison configurations per scenario:
    # A/C: oi_complete -> M1_vs_M0
    # B: oi_complete -> M1_vs_M0; basis_complete -> M1_vs_M0, M2_vs_M1
    for regime in regimes:
        for scenario in scenarios:
            comp_specs = []
            if scenario in ("A", "C"):
                comp_specs.append(("oi_complete", "M1_vs_M0", "M0", "M1"))
            elif scenario == "B":
                comp_specs.append(("oi_complete", "M1_vs_M0", "M0", "M1"))
                comp_specs.append(("basis_complete", "M1_vs_M0", "M0", "M1"))
                comp_specs.append(("basis_complete", "M2_vs_M1", "M1", "M2"))

            for cohort, comparison, base_model, ext_model in comp_specs:
                # Filter eligible parents in this regime & scenario
                if cohort == "oi_complete":
                    eligible_pool = [
                        r
                        for r in panel
                        if r["listing_regime"] == regime
                        and r["scenario"] == scenario
                        and r["oi_complete"]
                    ]
                else:  # basis_complete
                    eligible_pool = [
                        r
                        for r in panel
                        if r["listing_regime"] == regime
                        and r["scenario"] == scenario
                        and r["basis_complete"]
                    ]

                eligible_pool = sorted(eligible_pool, key=lambda x: x["parent_article_id"])

                for holdout in eligible_pool:
                    holdout_pid = holdout["parent_article_id"]
                    holdout_y = float(holdout["y"])

                    # Cross-regime exclusion: remove any record with holdout_pid across all regimes
                    train_pool = [
                        r for r in eligible_pool if r["parent_article_id"] != holdout_pid
                    ]
                    n_train = len(train_pool)

                    pred_base: Optional[float] = None
                    pred_ext: Optional[float] = None
                    error_base: Optional[float] = None
                    error_ext: Optional[float] = None
                    d_i: Optional[float] = None
                    fold_status = "not_estimable"

                    if n_train > 0:
                        train_p = np.array([r["p"] for r in train_pool], dtype=np.float64)
                        train_o = np.array([r["o"] for r in train_pool], dtype=np.float64)
                        train_y = np.array([r["y"] for r in train_pool], dtype=np.float64)

                        mu_p = float(np.mean(train_p))
                        std_p = float(np.std(train_p, ddof=0))
                        mu_o = float(np.mean(train_o))
                        std_o = float(np.std(train_o, ddof=0))

                        # Check non-zero variance for p and o
                        if std_p > 1e-12 and std_o > 1e-12:
                            z_p_train = (train_p - mu_p) / std_p
                            z_o_train = (train_o - mu_o) / std_o
                            z_po_train = z_p_train * z_o_train

                            z_p_test = (float(holdout["p"]) - mu_p) / std_p
                            z_o_test = (float(holdout["o"]) - mu_o) / std_o
                            z_po_test = z_p_test * z_o_test

                            ones_train = np.ones((n_train, 1), dtype=np.float64)

                            # Build M0 design matrix
                            X_m0 = np.column_stack([ones_train, z_p_train])
                            x_m0_test = np.array([1.0, z_p_test], dtype=np.float64)

                            # Build M1 design matrix
                            X_m1 = np.column_stack(
                                [ones_train, z_p_train, z_o_train, z_po_train]
                            )
                            x_m1_test = np.array(
                                [1.0, z_p_test, z_o_test, z_po_test], dtype=np.float64
                            )

                            if base_model == "M0":
                                pred_base = _fit_and_predict_ols(X_m0, train_y, x_m0_test)
                            elif base_model == "M1":
                                pred_base = _fit_and_predict_ols(X_m1, train_y, x_m1_test)

                            if ext_model == "M1":
                                pred_ext = _fit_and_predict_ols(X_m1, train_y, x_m1_test)
                            elif ext_model == "M2":
                                train_b = np.array(
                                    [r["b"] for r in train_pool], dtype=np.float64
                                )
                                mu_b = float(np.mean(train_b))
                                std_b = float(np.std(train_b, ddof=0))
                                if std_b > 1e-12:
                                    z_b_train = (train_b - mu_b) / std_b
                                    z_b_test = (float(holdout["b"]) - mu_b) / std_b
                                    X_m2 = np.column_stack(
                                        [
                                            ones_train,
                                            z_p_train,
                                            z_o_train,
                                            z_po_train,
                                            z_b_train,
                                        ]
                                    )
                                    x_m2_test = np.array(
                                        [1.0, z_p_test, z_o_test, z_po_test, z_b_test],
                                        dtype=np.float64,
                                    )
                                    pred_ext = _fit_and_predict_ols(X_m2, train_y, x_m2_test)

                    if pred_base is not None and pred_ext is not None:
                        fold_status = "ok"
                        error_base = holdout_y - pred_base
                        error_ext = holdout_y - pred_ext
                        d_i = (error_base**2) - (error_ext**2)

                    folds_out.append(
                        {
                            "listing_regime": regime,
                            "scenario": scenario,
                            "cohort": cohort,
                            "comparison": comparison,
                            "parent_article_id": holdout_pid,
                            "fold_status": fold_status,
                            "train_parent_count": n_train,
                            "actual_y": holdout_y,
                            "pred_base": pred_base,
                            "pred_extended": pred_ext,
                            "error_base": error_base,
                            "error_extended": error_ext,
                            "d_i": d_i,
                        }
                    )

    return folds_out


def summarize(panel: list[dict[str, Any]], folds: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarizes comparison results, error metrics, and contribution diagnostics."""
    comparisons_summary: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    regimes = sorted(set(r["listing_regime"] for r in panel))
    if not regimes:
        regimes = ["standard"]

    # Always include all 5 required comparisons per regime per Design §3.2
    expected_templates = [
        ("A", "oi_complete", "M1_vs_M0"),
        ("B", "oi_complete", "M1_vs_M0"),
        ("C", "oi_complete", "M1_vs_M0"),
        ("B", "basis_complete", "M1_vs_M0"),
        ("B", "basis_complete", "M2_vs_M1"),
    ]
    all_keys: set[tuple[str, str, str, str]] = set()
    for reg in regimes:
        for scn, coh, cmp in expected_templates:
            all_keys.add((reg, scn, coh, cmp))
    for f in folds:
        all_keys.add((f["listing_regime"], f["scenario"], f["cohort"], f["comparison"]))
    comp_keys = sorted(all_keys)

    for k in comp_keys:
        regime, scenario, cohort, comparison = k
        grp_folds = [
            f
            for f in folds
            if f["listing_regime"] == regime
            and f["scenario"] == scenario
            and f["cohort"] == cohort
            and f["comparison"] == comparison
        ]

        total_folds = len(grp_folds)
        estimable_folds = sum(1 for f in grp_folds if f["fold_status"] == "ok")
        all_est = total_folds > 0 and estimable_folds == total_folds

        if all_est:
            errors_base = [f["error_base"] for f in grp_folds]
            errors_ext = [f["error_extended"] for f in grp_folds]
            d_vals = [f["d_i"] for f in grp_folds]

            mse_b = float(np.mean([e**2 for e in errors_base]))
            mse_e = float(np.mean([e**2 for e in errors_ext]))
            mean_d = float(np.mean(d_vals))
            med_abs_b = float(np.median([abs(e) for e in errors_base]))
            med_abs_e = float(np.median([abs(e) for e in errors_ext]))

            # Sensitivity range: leave out each calculated d_i and compute mean of remaining
            if len(d_vals) > 1:
                minus_k_means = [
                    float(np.mean([d for idx, d in enumerate(d_vals) if idx != i]))
                    for i in range(len(d_vals))
                ]
                sens_range: Optional[tuple[float, float]] = (
                    min(minus_k_means),
                    max(minus_k_means),
                )
            else:
                sens_range = (mean_d, mean_d)

            # Top positive contributions (up to 3, sorted descending by d_i, ties broken by pid)
            pos_contribs = [
                {"parent_article_id": f["parent_article_id"], "d_i": float(f["d_i"])}
                for f in grp_folds
                if f["d_i"] is not None and f["d_i"] > 0
            ]
            pos_contribs.sort(key=lambda x: (-x["d_i"], x["parent_article_id"]))
            top_pos = pos_contribs[:3]
        else:
            mse_b = None
            mse_e = None
            mean_d = None
            med_abs_b = None
            med_abs_e = None
            sens_range = None
            top_pos = []

        comparisons_summary[k] = {
            "listing_regime": regime,
            "scenario": scenario,
            "cohort": cohort,
            "comparison": comparison,
            "total_folds": total_folds,
            "estimable_folds": estimable_folds,
            "all_estimable": all_est,
            "mse_base": mse_b,
            "mse_extended": mse_e,
            "mean_d_i": mean_d,
            "median_abs_error_base": med_abs_b,
            "median_abs_error_extended": med_abs_e,
            "sensitivity_mean_d_i_range": sens_range,
            "top_positive_contributions": top_pos,
        }

    # Also compute cohort-level distributions of y, long_mae, long_mfe
    cohort_summaries: dict[tuple[str, str, str], dict[str, Any]] = {}
    cohort_keys = sorted(
        set(
            (r["listing_regime"], r["scenario"], "oi_complete")
            for r in panel
        ).union(
            set(
                (r["listing_regime"], r["scenario"], "basis_complete")
                for r in panel
                if r["scenario"] == "B"
            )
        )
    )

    for reg, scn, coh in cohort_keys:
        subset = [
            r
            for r in panel
            if r["listing_regime"] == reg and r["scenario"] == scn and r[coh]
        ]
        count = len(subset)
        if count > 0:
            y_vals = [r["y"] for r in subset]
            mae_vals = [r["long_mae"] for r in subset]
            mfe_vals = [r["long_mfe"] for r in subset]

            def _stats(arr: list[float]) -> dict[str, float]:
                return {
                    "count": float(len(arr)),
                    "mean": float(np.mean(arr)),
                    "median": float(np.median(arr)),
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                }

            cohort_summaries[(reg, scn, coh)] = {
                "parent_count": count,
                "y": _stats(y_vals),
                "long_mae": _stats(mae_vals),
                "long_mfe": _stats(mfe_vals),
            }
        else:
            cohort_summaries[(reg, scn, coh)] = {
                "parent_count": 0,
                "y": None,
                "long_mae": None,
                "long_mfe": None,
            }

    return {
        "comparisons": comparisons_summary,
        "cohorts": cohort_summaries,
    }


REQUIRED_AUTH_KEYS: Set[str] = {
    "operation",
    "design_relative_path",
    "design_sha256",
    "plan_relative_path",
    "plan_sha256",
    "input_csv_path",
    "input_csv_sha256",
    "input_review_path",
    "input_review_sha256",
    "output_dir",
    "allowed_actions",
    "network_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_allowed",
    "signal_allowed",
}


def validate_authorization(
    auth_data: Dict[str, Any],
    required_action: str = "research_run",
    expected_output_dir: Optional[Path] = None,
) -> None:
    """Validates authorization dictionary strictly against Design §2 invariants."""
    if set(auth_data.keys()) != REQUIRED_AUTH_KEYS:
        missing = REQUIRED_AUTH_KEYS - set(auth_data.keys())
        extra = set(auth_data.keys()) - REQUIRED_AUTH_KEYS
        raise IncrementalAnalysisError(f"invalid_auth_keys: missing={missing}, extra={extra}")

    if auth_data["operation"] != "offline_research_once":
        raise IncrementalAnalysisError(f"invalid_operation: {auth_data['operation']}")

    if auth_data["design_relative_path"] != FIXED_DESIGN_RELATIVE_PATH:
        raise IncrementalAnalysisError(
            f"design_relative_path_mismatch: {auth_data['design_relative_path']} vs {FIXED_DESIGN_RELATIVE_PATH}"
        )
    if auth_data["design_sha256"] != FIXED_DESIGN_SHA256:
        raise IncrementalAnalysisError(
            f"design_sha256_mismatch: {auth_data['design_sha256']} vs {FIXED_DESIGN_SHA256}"
        )
    design_p = Path(auth_data["design_relative_path"])
    if not design_p.is_file():
        raise IncrementalAnalysisError(f"design_file_not_found: {design_p}")
    actual_design_sha = _compute_sha256_chunked(design_p)
    if actual_design_sha != FIXED_DESIGN_SHA256:
        raise IncrementalAnalysisError(
            f"actual_design_file_sha_mismatch: {actual_design_sha} vs {FIXED_DESIGN_SHA256}"
        )

    if auth_data["plan_relative_path"] != FIXED_PLAN_RELATIVE_PATH:
        raise IncrementalAnalysisError(
            f"plan_relative_path_mismatch: {auth_data['plan_relative_path']} vs {FIXED_PLAN_RELATIVE_PATH}"
        )
    if auth_data["plan_sha256"] != FIXED_PLAN_SHA256:
        raise IncrementalAnalysisError(
            f"plan_sha256_mismatch: {auth_data['plan_sha256']} vs {FIXED_PLAN_SHA256}"
        )
    plan_p = Path(auth_data["plan_relative_path"])
    if not plan_p.is_file():
        raise IncrementalAnalysisError(f"plan_file_not_found: {plan_p}")
    actual_plan_sha = _compute_sha256_chunked(plan_p)
    if actual_plan_sha != FIXED_PLAN_SHA256:
        raise IncrementalAnalysisError(
            f"actual_plan_file_sha_mismatch: {actual_plan_sha} vs {FIXED_PLAN_SHA256}"
        )

    try:
        auth_in_csv = Path(auth_data["input_csv_path"]).resolve()
        fixed_in_csv = FIXED_INPUT_CSV_PATH.resolve()
        if auth_in_csv != fixed_in_csv:
            raise IncrementalAnalysisError(
                f"input_csv_path_mismatch: {auth_in_csv} vs {fixed_in_csv}"
            )
    except Exception as exc:
        raise IncrementalAnalysisError(f"cannot_resolve_input_csv_path: {exc}") from exc

    if auth_data["input_csv_sha256"] != FIXED_INPUT_CSV_SHA256:
        raise IncrementalAnalysisError(
            f"input_csv_sha256_mismatch: {auth_data['input_csv_sha256']} vs {FIXED_INPUT_CSV_SHA256}"
        )

    try:
        auth_in_rev = Path(auth_data["input_review_path"]).resolve()
        fixed_in_rev = FIXED_INPUT_REVIEW_PATH.resolve()
        if auth_in_rev != fixed_in_rev:
            raise IncrementalAnalysisError(
                f"input_review_path_mismatch: {auth_in_rev} vs {fixed_in_rev}"
            )
    except Exception as exc:
        raise IncrementalAnalysisError(f"cannot_resolve_input_review_path: {exc}") from exc

    if auth_data["input_review_sha256"] != FIXED_INPUT_REVIEW_SHA256:
        raise IncrementalAnalysisError(
            f"input_review_sha256_mismatch: {auth_data['input_review_sha256']} vs {FIXED_INPUT_REVIEW_SHA256}"
        )

    if expected_output_dir is not None:
        try:
            auth_out = Path(auth_data["output_dir"]).resolve()
            exp_out = expected_output_dir.resolve()
            if auth_out != exp_out:
                raise IncrementalAnalysisError(
                    f"output_dir_mismatch: {auth_out} vs {exp_out}"
                )
        except Exception as exc:
            raise IncrementalAnalysisError(f"cannot_resolve_output_dir: {exc}") from exc

    for flag in [
        "network_allowed",
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_allowed",
        "signal_allowed",
    ]:
        val = auth_data[flag]
        if type(val) is not bool or val is not False:
            raise IncrementalAnalysisError(f"forbidden_permission_active: {flag}={val}")

    actions = auth_data.get("allowed_actions")
    if not isinstance(actions, list) or len(actions) == 0:
        raise IncrementalAnalysisError(f"empty_or_invalid_allowed_actions: {actions}")
    valid_action_set = {"snapshot_validation", "research_run"}
    if not set(actions).issubset(valid_action_set):
        raise IncrementalAnalysisError(f"unknown_allowed_actions: {actions}")
    if len(actions) != len(set(actions)):
        raise IncrementalAnalysisError(f"duplicate_allowed_actions: {actions}")
    if required_action not in actions:
        raise IncrementalAnalysisError(
            f"missing_required_action: {required_action} not in {actions}"
        )


def validate_output_directory(
    output_dir: Path, input_csv_path: Path, input_review_path: Path
) -> None:
    """Validates output directory isolation and safe creation."""
    if output_dir.exists():
        raise IncrementalAnalysisError(f"output_dir_already_exists: {output_dir}")

    # Check for symlinks in path components
    curr = output_dir
    while curr != curr.parent:
        if curr.is_symlink():
            raise IncrementalAnalysisError(f"symlink_not_allowed_in_output_dir: {curr}")
        if curr.exists():
            break
        curr = curr.parent

    out_res = output_dir.resolve()
    if out_res == Path("/"):
        raise IncrementalAnalysisError("cannot_use_root_as_output_dir")

    in_csv_res = input_csv_path.resolve()
    in_rev_res = input_review_path.resolve()
    in_csv_dir = in_csv_res.parent
    in_rev_dir = in_rev_res.parent

    # Output cannot be equal to input files or input directories
    if out_res in {in_csv_res, in_rev_res, in_csv_dir, in_rev_dir}:
        raise IncrementalAnalysisError(f"output_dir_collides_with_inputs: {out_res}")

    # Output cannot be inside input directories
    if in_csv_dir in out_res.parents or in_rev_dir in out_res.parents:
        raise IncrementalAnalysisError(f"output_dir_inside_input_dir: {out_res}")

    # Output cannot contain input files or input directories
    if out_res in in_csv_res.parents or out_res in in_rev_res.parents:
        raise IncrementalAnalysisError(f"output_dir_contains_inputs: {out_res}")


def _fmt_float(val: Optional[float]) -> str:
    return f"{val:.8f}" if val is not None else ""


def write_parent_panel_csv(panel: List[Dict[str, Any]], out_path: Path) -> None:
    """Writes parent_panel.csv artifact sorted by regime, scenario, parent_article_id."""
    headers = [
        "parent_article_id",
        "listing_regime",
        "scenario",
        "utc_date",
        "child_symbols",
        "required_child_count",
        "scenario_complete_child_count",
        "oi_complete",
        "basis_complete",
        "missing_reasons",
        "p",
        "o",
        "b",
        "y",
        "long_mae",
        "long_mfe",
    ]
    sorted_panel = sorted(
        panel, key=lambda r: (r["listing_regime"], r["scenario"], r["parent_article_id"])
    )

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in sorted_panel:
            writer.writerow([
                r["parent_article_id"],
                r["listing_regime"],
                r["scenario"],
                r["utc_date"],
                r["child_symbols"],
                r["required_child_count"],
                r["scenario_complete_child_count"],
                "true" if r["oi_complete"] else "false",
                "true" if r["basis_complete"] else "false",
                r["missing_reasons"],
                _fmt_float(r["p"]),
                _fmt_float(r["o"]),
                _fmt_float(r["b"]),
                _fmt_float(r["y"]),
                _fmt_float(r["long_mae"]),
                _fmt_float(r["long_mfe"]),
            ])


def write_fold_diagnostics_csv(folds: List[Dict[str, Any]], out_path: Path) -> None:
    """Writes fold_diagnostics.csv artifact sorted by 5-tuple key."""
    headers = [
        "listing_regime",
        "scenario",
        "cohort",
        "comparison",
        "parent_article_id",
        "fold_status",
        "train_parent_count",
        "actual_y",
        "pred_base",
        "pred_extended",
        "error_base",
        "error_extended",
        "d_i",
    ]
    sorted_folds = sorted(
        folds,
        key=lambda f: (
            f["listing_regime"],
            f["scenario"],
            f["cohort"],
            f["comparison"],
            f["parent_article_id"],
        ),
    )

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for fld in sorted_folds:
            writer.writerow([
                fld["listing_regime"],
                fld["scenario"],
                fld["cohort"],
                fld["comparison"],
                fld["parent_article_id"],
                fld["fold_status"],
                (
                    str(fld["train_parent_count"])
                    if fld["train_parent_count"] is not None
                    else ""
                ),
                _fmt_float(fld["actual_y"]),
                _fmt_float(fld["pred_base"]),
                _fmt_float(fld["pred_extended"]),
                _fmt_float(fld["error_base"]),
                _fmt_float(fld["error_extended"]),
                _fmt_float(fld["d_i"]),
            ])


def write_review_report_md(
    summary: Dict[str, Any],
    panel: List[Dict[str, Any]],
    folds: List[Dict[str, Any]],
    auth_data: Dict[str, Any],
    out_path: Path,
) -> None:
    """Writes review_CN.md markdown report with final EXECUTION_SUCCESSFUL marker."""
    lines: List[str] = [
        "# 新合约价格状态与 OI／基差增量信息有限探索报告",
        "",
        "**研究状态：** `exploratory / historical_scenario_only / no_alpha_claim`",
        "",
        "> [!IMPORTANT]",
        "> **核心边界与局限说明：**",
        "> 1. 本研究仅为离线只读派生探索，不声称任何可交易 Alpha（`no_alpha_claim`），不构成实盘交易许可。",
        "> 2. 真实发布时间与可用点位（PIT）未经验证，特征时间约束仅为情景假设。",
        "> 3. 留一 Parent（LOPO）检验仅是同一已观察历史上的内部模型误差检查，其他折包含较晚日期，不是前瞻测试（walk-forward）或未见样本预测。",
        "> 4. 严禁以此结论开启实盘、测试网、纸面交易或生成交易信号；交易与执行权限严格为 `False`。",
        "",
        "## 1. 任务身份与输入绑定",
        "",
        f"- **操作类型：** `{auth_data['operation']}`",
        f"- **设计文档：** `{auth_data['design_relative_path']}` (SHA-256: `{auth_data['design_sha256']}`)",
        f"- **实施计划：** `{auth_data['plan_relative_path']}` (SHA-256: `{auth_data['plan_sha256']}`)",
        f"- **输入数据 CSV：** `{auth_data['input_csv_path']}` (SHA-256: `{auth_data['input_csv_sha256']}`)",
        f"- **输入回顾报告：** `{auth_data['input_review_path']}` (SHA-256: `{auth_data['input_review_sha256']}`)",
        f"- **输出目录：** `{auth_data['output_dir']}`",
    ]

    code_path = Path(__file__).resolve()
    code_sha = _compute_sha256_chunked(code_path) if code_path.is_file() else "N/A"
    lines.extend([
        "- **分析代码相对路径：** `scripts/external_signal_shadow/run_launch_price_oi_basis_incremental_information.py`",
        f"- **分析代码 SHA-256：** `{code_sha}`",
        "",
        "## 2. Parent 样本与资格守恒",
        "",
        "| 上市机制 | 情景 | 样本全集 (Universe) | OI 完整 Parent | 基差完整 Parent (仅B) | 日期冲突/未知 |",
        "| --- | --- | --- | --- | --- | --- |",
    ])

    regimes = sorted(set(r["listing_regime"] for r in panel))
    scenarios = ["A", "B", "C"]
    for reg in regimes:
        for scn in scenarios:
            sub = [r for r in panel if r["listing_regime"] == reg and r["scenario"] == scn]
            if not sub:
                continue
            univ = len(sub)
            oi_c = sum(1 for r in sub if r["oi_complete"])
            basis_c = (
                str(sum(1 for r in sub if r["basis_complete"])) if scn == "B" else "N/A"
            )
            dates_conflict = sum(1 for r in sub if "conflict" in r["utc_date"])
            dates_unk = sum(1 for r in sub if r["utc_date"] == "unknown")
            date_note = f"冲突:{dates_conflict}, 未知:{dates_unk}"
            lines.append(f"| {reg} | {scn} | {univ} | {oi_c} | {basis_c} | {date_note} |")

    lines.extend([
        "",
        "### 跨情景样本交集统计",
        "",
        "| 上市机制 | 样本全集 | A完整 | B完整 | C完整 | A∩B交集 | B∩C交集 | A∩B∩C交集 | B基差完整 | B(OI)∩B(基差)交集 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for reg in regimes:
        sub_univ = set(r["parent_article_id"] for r in panel if r["listing_regime"] == reg)
        set_a = set(
            r["parent_article_id"]
            for r in panel
            if r["listing_regime"] == reg and r["scenario"] == "A" and r["oi_complete"]
        )
        set_b = set(
            r["parent_article_id"]
            for r in panel
            if r["listing_regime"] == reg and r["scenario"] == "B" and r["oi_complete"]
        )
        set_c = set(
            r["parent_article_id"]
            for r in panel
            if r["listing_regime"] == reg and r["scenario"] == "C" and r["oi_complete"]
        )
        set_b_basis = set(
            r["parent_article_id"]
            for r in panel
            if r["listing_regime"] == reg and r["scenario"] == "B" and r["basis_complete"]
        )

        lines.append(
            f"| {reg} | {len(sub_univ)} | {len(set_a)} | {len(set_b)} | {len(set_c)} | "
            f"{len(set_a & set_b)} | {len(set_b & set_c)} | {len(set_a & set_b & set_c)} | "
            f"{len(set_b_basis)} | {len(set_b & set_b_basis)} |"
        )

    lines.extend([
        "",
        "### UTC 日期分布与集中度诊断",
        "",
    ])
    for reg in regimes:
        sub_panel = [r for r in panel if r["listing_regime"] == reg and r["scenario"] == "B"]
        if not sub_panel:
            continue
        univ_dates: dict[str, int] = {}
        for r in sub_panel:
            d = r["utc_date"]
            univ_dates[d] = univ_dates.get(d, 0) + 1

        b_comp_panel = [r for r in sub_panel if r["oi_complete"]]
        b_dates: dict[str, int] = {}
        for r in b_comp_panel:
            d = r["utc_date"]
            b_dates[d] = b_dates.get(d, 0) + 1

        lines.append(f"#### {reg} 机制日期分布")
        lines.append("")
        lines.append("| 统计口径 | 样本数 | 唯一日期数 | Top 1 日期及占比 | Top 3 日期累计占比 |")
        lines.append("| --- | --- | --- | --- | --- |")

        for lbl, d_dict, tot in [
            ("样本全集 (Universe)", univ_dates, len(sub_panel)),
            ("情景 B 完整样本", b_dates, len(b_comp_panel)),
        ]:
            if tot == 0:
                lines.append(f"| {lbl} | 0 | 0 | N/A | N/A |")
                continue
            sorted_dates = sorted(d_dict.items(), key=lambda x: -x[1])
            top1_str = f"{sorted_dates[0][0]} ({sorted_dates[0][1]}/{tot}, {sorted_dates[0][1]/tot*100:.1f}%)"
            top3_sum = sum(cnt for _, cnt in sorted_dates[:3])
            top3_str = f"{top3_sum}/{tot} ({top3_sum/tot*100:.1f}%)"
            lines.append(f"| {lbl} | {tot} | {len(d_dict)} | {top1_str} | {top3_str} |")

        lines.append("")
        sorted_all_dates = sorted(univ_dates.items(), key=lambda x: (-x[1], x[0]))
        date_entries = [f"`{d}`: {cnt}个" for d, cnt in sorted_all_dates]
        lines.append(f"**{reg} 详细日期列表（降序）：** " + ", ".join(date_entries))
        lines.append("")

    lines.extend([
        "## 3. 模型比较与增量信息评估",
        "",
        "比较约定：`d_i = error_base_i^2 - error_extended_i^2`。`mean(d_i) > 0` 仅表示内部均方误差下降。",
        "",
        "| 机制 | 情景 | 样本集合 (Cohort) | 模型比较 | 总折数 | 可估折数 | 全可估 | MSE基准 | MSE扩展 | Mean d_i | 中位绝对误(基准) | 中位绝对误(扩展) | Mean d_i 剔除单折敏感范围 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])

    for k, comp in summary["comparisons"].items():
        reg, scn, coh, comparison = k
        if comp["total_folds"] == 0:
            lines.append(
                f"| {reg} | {scn} | {coh} | {comparison} | 0 | 0 | 否 | "
                f"evidence_insufficient | evidence_insufficient | evidence_insufficient | "
                f"evidence_insufficient | evidence_insufficient | evidence_insufficient |"
            )
        else:
            all_est = "是" if comp["all_estimable"] else "否"
            mse_b = _fmt_float(comp["mse_base"])
            mse_e = _fmt_float(comp["mse_extended"])
            mean_d = _fmt_float(comp["mean_d_i"])
            med_b = _fmt_float(comp["median_abs_error_base"])
            med_e = _fmt_float(comp["median_abs_error_extended"])
            sens = comp["sensitivity_mean_d_i_range"]
            sens_str = f"[{_fmt_float(sens[0])}, {_fmt_float(sens[1])}]" if sens else "N/A"

            lines.append(
                f"| {reg} | {scn} | {coh} | {comparison} | {comp['total_folds']} | "
                f"{comp['estimable_folds']} | {all_est} | {mse_b} | {mse_e} | {mean_d} | "
                f"{med_b} | {med_e} | {sens_str} |"
            )

    lines.extend([
        "",
        "### 前三正向贡献 Parent 诊断",
        "",
    ])

    for k, comp in summary["comparisons"].items():
        reg, scn, coh, comparison = k
        top_pos = comp["top_positive_contributions"]
        lines.append(f"- **{reg} / {scn} / {coh} / {comparison}**:")
        if comp["total_folds"] == 0:
            lines.append("  - 无可用样本（evidence_insufficient）。")
        elif not top_pos:
            lines.append("  - 无正向贡献折（所有折均未改善或不可估）。")
        else:
            for p_contrib in top_pos:
                lines.append(
                    f"  - Parent `{p_contrib['parent_article_id']}`: `d_i = {p_contrib['d_i']:.8f}`"
                )

    lines.extend([
        "",
        "## 4. 收益与极端路径分布 (y, long_mae, long_mfe)",
        "",
        "| 机制 | 情景 | 样本集合 | 指标 | 样本量 | 均值 | 中位数 | 最小值 | 最大值 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])

    for k, c_stat in summary["cohorts"].items():
        reg, scn, coh = k
        for metric_name in ["y", "long_mae", "long_mfe"]:
            m_data = c_stat[metric_name]
            if m_data:
                lines.append(
                    f"| {reg} | {scn} | {coh} | {metric_name} | {int(m_data['count'])} | "
                    f"{m_data['mean']:.8f} | {m_data['median']:.8f} | {m_data['min']:.8f} | "
                    f"{m_data['max']:.8f} |"
                )
            else:
                lines.append(
                    f"| {reg} | {scn} | {coh} | {metric_name} | 0 | N/A | N/A | N/A | N/A |"
                )

    lines.extend([
        "",
        "## 5. 结论与后续延期说明",
        "",
        "1. **增量信息结论：** 本次探索严格按照已获批固定模型（M0, M1, M2）及 LOPO 进行评估，不调整参数，不事后搜索阈值。",
        "2. **交易与风险：** 策略执行、滑点、手续费、资金费率吸收、持仓期风险及实盘安全等指标在本阶段属于延期范围（`N/A`）。",
        "3. **状态标记：** 全部文件生成完毕，运行成功结束。",
        "",
        "EXECUTION_SUCCESSFUL",
    ])

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for launch price, OI, and basis incremental analysis."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Launch price, OI, and basis incremental analysis CLI"
    )
    parser.add_argument("--auth-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    except Exception as exc:
        sys.stderr.write(f"CLI argument parsing error: {exc}\n")
        return 2

    auth_path: Path = args.auth_file
    output_dir: Path = args.output_dir

    try:
        if not auth_path.is_file():
            sys.stderr.write(f"Auth file not found: {auth_path}\n")
            return 1

        try:
            auth_data = json.loads(auth_path.read_text(encoding="utf-8"))
        except Exception as exc:
            sys.stderr.write(f"Auth file is not valid JSON: {exc}\n")
            return 1

        # 1. Validate authorization
        validate_authorization(
            auth_data, required_action="research_run", expected_output_dir=output_dir
        )

        # 2. Validate output directory isolation
        validate_output_directory(output_dir, FIXED_INPUT_CSV_PATH, FIXED_INPUT_REVIEW_PATH)

        # 3. Validate input files on disk
        if not FIXED_INPUT_CSV_PATH.is_file():
            sys.stderr.write(f"Input CSV file not found: {FIXED_INPUT_CSV_PATH}\n")
            return 1
        actual_csv_sha = _compute_sha256_chunked(FIXED_INPUT_CSV_PATH)
        if actual_csv_sha != FIXED_INPUT_CSV_SHA256:
            sys.stderr.write(
                f"Input CSV SHA-256 mismatch: {actual_csv_sha} vs {FIXED_INPUT_CSV_SHA256}\n"
            )
            return 1

        if not FIXED_INPUT_REVIEW_PATH.is_file():
            sys.stderr.write(f"Input review file not found: {FIXED_INPUT_REVIEW_PATH}\n")
            return 1
        actual_rev_sha = _compute_sha256_chunked(FIXED_INPUT_REVIEW_PATH)
        if actual_rev_sha != FIXED_INPUT_REVIEW_SHA256:
            sys.stderr.write(
                f"Input review SHA-256 mismatch: {actual_rev_sha} vs {FIXED_INPUT_REVIEW_SHA256}\n"
            )
            return 1

        # 4. Load snapshot and run analysis pipeline
        rows = load_snapshot(FIXED_INPUT_CSV_PATH, expected_sha256=FIXED_INPUT_CSV_SHA256)
        panel = build_parent_panel(rows)
        folds = evaluate_comparisons(panel)
        summary = summarize(panel, folds)

        # 5. Safe creation and writing to output_dir
        output_dir.mkdir(parents=True, exist_ok=False)

        panel_out = output_dir / "parent_panel.csv"
        write_parent_panel_csv(panel, panel_out)

        folds_out = output_dir / "fold_diagnostics.csv"
        write_fold_diagnostics_csv(folds, folds_out)

        review_out = output_dir / "review_CN.md"
        write_review_report_md(summary, panel, folds, auth_data, review_out)

        return 0

    except IncrementalAnalysisError as err:
        sys.stderr.write(f"Incremental analysis error: {err}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"Unexpected error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
