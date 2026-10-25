"""Standalone stdlib-only Rule 17 artifact schema verifier for Stage 1.5J-C."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any

PROFILE_ID = "stage1_5j_c_time_path_v1"
PROFILE_CONTRACT_VERSION = 1

APPROVED_DESIGN_RELATIVE_PATH = (
    "docs/designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md"
)
APPROVED_DESIGN_SHA256 = "32d5130806489c0848748060835a7c0fb8f1715a3f9fb6b479c2f02cff5d4e45"

APPROVED_PLAN_RELATIVE_PATH = (
    "docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md"
)

PROTOCOL_RELATIVE_PATH = "docs/production_artifacts/stage1_5j_c_time_path_protocol_v1.json"
PROTOCOL_SHA256 = "4dd353751256191d75fc52388413d97e5a7b177e499bbee28e2dd2ff356e1cbe"
EXPECTED_PROTOCOL_OBJECT: dict[str, Any] = {
    "endpoint_max_age_ms": 1000,
    "entry_max_wait_ms": 1000,
    "friction_bps": [50, 80, 150],
    "horizon_ms": 900000,
    "latency_ms": 3000,
    "observation_ms": 60000,
    "protocol_id": "stage1_5j_c_time_path_v1",
    "protocol_version": 1,
    "risk_bps": 200,
    "target_bps": 3000,
}

J_A_ROOT_RELATIVE_PATH = (
    "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/"
    "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
)
J_B_ROOT_RELATIVE_PATH = (
    "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/"
    "stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"
)
LEDGER_RELATIVE_PATH = "data/exports/stage1_5j_token_launch_classification_ledger_v2.csv"
J_B_CLOSURE_JSON_RELATIVE_PATH = (
    ".git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/"
    "64e14726202b53727a7627139578369cb6af54f08d5a785d4df006009eb25a2d/"
    "evidence/receipt_closure_evidence.json"
)
J_B_CLOSURE_SIDECAR_RELATIVE_PATH = f"{J_B_CLOSURE_JSON_RELATIVE_PATH}.sha256"

FROZEN_SOURCE_FILE_HASHES: dict[str, str] = {
    "configs/base.py": "473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc",
    "configs/stage1_5j_b_historical_aggtrades_launch_response.py": "771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4",
    "scripts/external_signal_shadow/export_stage1_5j_dataset_v2.py": "b70faa18f4da875d1c3db950b312d97f49551b4887f22c2baf3b96531e6926d8",
    "scripts/external_signal_shadow/verify_stage1_5j_dataset_v2.py": "52623af3d766ad52e45b0ca61dd748340cd664644f855b800f5cd7ffc28fb3ee",
    "scripts/governance/verify_artifact_schema.py": "7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473",
    "scripts/governance/verify_stage1_5j_b_receipt_schema.py": "442c527fb7f49d78eff4e13fd68e5fabfff12ba1e74089cd5e5133977cde90f1",
    "src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py": "250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18",
    "src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py": "b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f",
}

J_C_SOURCE_RELATIVE_PATHS: tuple[str, ...] = (
    "scripts/external_signal_shadow/run_stage1_5j_c_launch_time_path_feasibility.py",
    "scripts/governance/verify_stage1_5j_c_receipt_schema.py",
    "src/research/external_signal_shadow/stage1_5j_c_launch_time_path_feasibility.py",
)

ALL_11_SOURCE_RELATIVE_PATHS: list[str] = sorted(
    list(FROZEN_SOURCE_FILE_HASHES.keys()) + list(J_C_SOURCE_RELATIVE_PATHS)
)

FROZEN_INPUT_FILE_HASHES: dict[str, str] = {
    J_B_CLOSURE_JSON_RELATIVE_PATH: "8d535303d61b3860eaa69018eff3f76645f91b3e27af1af89e1e956b948f8b6d",
    J_B_CLOSURE_SIDECAR_RELATIVE_PATH: "c3856c2e9e6d5086a543891902d57246fa64a93acdbba97a1130e541f949c5d9",
    LEDGER_RELATIVE_PATH: "36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b",
    f"{J_A_ROOT_RELATIVE_PATH}/manifest.json": "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf",
    f"{J_A_ROOT_RELATIVE_PATH}/summary.json": "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b",
    f"{J_B_ROOT_RELATIVE_PATH}/manifest.json": "f0a8ac724925084161f6b9aa2dced5139b261707fda0f0f21ebd0eb6de3087fb",
    f"{J_B_ROOT_RELATIVE_PATH}/review_CN.md": "17e9ffaa973923868621a8ee925dc811c15e12459924ee63897f9c21fcac317e",
    f"{J_B_ROOT_RELATIVE_PATH}/summary.json": "5ea0f1c87803114c4c6917cd0c3d24292948fa0e7066a80e0a2bce611e32546b",
    PROTOCOL_RELATIVE_PATH: PROTOCOL_SHA256,
}

ALL_9_INPUT_RELATIVE_PATHS: list[str] = sorted(FROZEN_INPUT_FILE_HASHES.keys())

OUTPUT_PARENT_RELATIVE_PATH = (
    "data/external_signal_shadow/stage1_5j_c/launch_time_path_feasibility"
)

RUN_ID_REGEX = re.compile(
    r"^stage1_5j_c_launch_time_path_feasibility_([0-9]{8}T[0-9]{6}Z)$"
)
SHA256_REGEX = re.compile(r"^[0-9a-f]{64}$")
HEX32_REGEX = re.compile(r"^[0-9a-f]{32}$")
DATE_REGEX = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
FRACTION_REGEX = re.compile(r"^(?:0/1|-?[1-9][0-9]*/[1-9][0-9]*)$")

MANIFEST_EXACT_KEYS = {
    "profile_id",
    "profile_contract_version",
    "artifact_kind",
    "run_id",
    "files",
}
SUMMARY_EXACT_KEYS = {
    "profile_id",
    "profile_contract_version",
    "artifact_kind",
    "run_id",
    "authority",
    "protocol",
    "permissions",
    "analysis_state",
    "universe_rows",
    "child_rows",
    "parent_rows",
    "group_rows",
}
AUTHORITY_EXACT_KEYS = {
    "design",
    "plan",
    "user_receipt_generation_approval",
    "authorization_release",
    "run_authorization",
    "source_files",
    "input_files",
}
PERMISSIONS_EXACT_KEYS = {
    "network_allowed",
    "receipt_regeneration_allowed",
    "signal_allowed",
    "consumer_promotion_allowed",
    "alpha_claim_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_allowed",
}
FILE_SEAL_EXACT_KEYS = {"relative_path", "size_bytes", "sha256"}
UNIVERSE_EXACT_KEYS = {
    "parent_article_id",
    "symbol",
    "asset_class",
    "listing_regime",
    "classification_status",
    "in_scope",
}
TRADE_REF_EXACT_KEYS = {
    "utc_date",
    "physical_row",
    "agg_trade_id",
    "time_ms",
    "price",
}
CHILD_EXACT_KEYS = {
    "parent_article_id",
    "symbol",
    "listing_regime",
    "direction",
    "state",
    "t0",
    "entry",
    "endpoint",
    "mfe_trade",
    "mae_trade",
    "terminal_bps",
    "mfe_bps",
    "mae_bps",
    "first_touch",
    "touch_trade",
    "max_intertrade_gap_ms",
}
PARENT_EXACT_KEYS = {
    "parent_article_id",
    "listing_regime",
    "direction",
    "state",
    "symbols",
    "utc_dates",
    "n_complete",
    "n_gap",
    "terminal_bps",
    "mfe_bps",
    "mae_bps",
    "touch_counts",
}
TOUCH_COUNTS_EXACT_KEYS = {"target", "risk", "neither"}
DISTRIBUTION_EXACT_KEYS = {
    "n",
    "mean",
    "median",
    "min",
    "max",
    "p10",
    "p25",
    "p75",
    "p90",
}
LEVEL_STATS_EXACT_KEYS = {
    "n_total",
    "n_complete",
    "n_gap",
    "terminal",
    "mfe",
    "mae",
}
COST_STATS_EXACT_KEYS = {
    "cost_bps",
    "space_status",
    "child",
    "parent",
    "child_positive",
    "parent_positive",
}
CONCENTRATION_EXACT_KEYS = {
    "top1_parent_ids",
    "top3_parent_ids",
    "top1_share",
    "top3_share",
}
GROUP_EXACT_KEYS = {
    "listing_regime",
    "direction",
    "child",
    "parent",
    "touch_counts",
    "parent_touch_fraction_mean",
    "costs",
    "concentration",
}

ALLOWED_ASSET_CLASSES = {"crypto", "equity", "etf", "commodity", "index", "unknown"}
ALLOWED_LISTING_REGIMES = {"standard", "pre_market", "pre_ipo", "unknown"}
ALLOWED_CLASSIFICATION_STATUS = {"confirmed", "unknown"}
ALLOWED_CHILD_STATES = {
    "inherited_j_a_parent_gap",
    "anchor_unavailable",
    "required_package_unavailable",
    "entry_unavailable",
    "endpoint_unavailable",
    "sequence_gap",
    "complete",
}


class SchemaViolationError(Exception):
    """Raised when any Rule 17 structural or projection check fails."""


def _is_strict_int(v: Any) -> bool:
    return type(v) is int


def _has_symlink_ancestor(path: Path, stop_at: Path | None = None) -> bool:
    cur = path
    stop_res = stop_at.resolve() if stop_at is not None and stop_at.exists() else None
    while True:
        if os.path.islink(cur):
            return True
        if stop_res is not None:
            try:
                if cur.resolve() == stop_res:
                    break
            except OSError:
                pass
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return False


def _parse_canonical_json_bytes(raw_bytes: bytes, label: str) -> Any:
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SchemaViolationError(f"{label}: invalid UTF-8") from exc
    if not text.endswith("\n"):
        raise SchemaViolationError(f"{label}: missing trailing LF")

    def _no_dups(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in pairs:
            if k in out:
                raise SchemaViolationError(f"{label}: duplicate key {k!r}")
            out[k] = v
        return out

    def _no_nan(val: str) -> Any:
        raise SchemaViolationError(f"{label}: NaN/Infinity forbidden ({val})")

    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_no_dups,
            parse_constant=_no_nan,
        )
    except SchemaViolationError:
        raise
    except ValueError as exc:
        raise SchemaViolationError(f"{label}: malformed JSON ({exc})") from exc

    canonical = (
        json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    if raw_bytes != canonical:
        raise SchemaViolationError(f"{label}: non-canonical JSON formatting")
    return parsed


def _parse_fraction(s: Any, label: str) -> Fraction:
    if not isinstance(s, str) or not FRACTION_REGEX.match(s):
        raise SchemaViolationError(f"{label}: invalid fraction syntax {s!r}")
    num_s, den_s = s.split("/", 1)
    num = int(num_s)
    den = int(den_s)
    f = Fraction(num, den)
    expected_s = "0/1" if f.numerator == 0 else f"{f.numerator}/{f.denominator}"
    if s != expected_s:
        raise SchemaViolationError(f"{label}: unreduced fraction {s!r} != {expected_s!r}")
    return f


def _format_fraction(f: Fraction) -> str:
    if f.numerator == 0:
        return "0/1"
    return f"{f.numerator}/{f.denominator}"


def _parse_positive_decimal(s: Any, label: str) -> Decimal:
    if (
        not isinstance(s, str)
        or not s
        or s != s.strip()
        or s.startswith("+")
    ):
        raise SchemaViolationError(f"{label}: invalid decimal string {s!r}")
    try:
        d = Decimal(s)
    except InvalidOperation as exc:
        raise SchemaViolationError(f"{label}: invalid Decimal {s!r}") from exc
    if not d.is_finite() or d <= 0:
        raise SchemaViolationError(f"{label}: non-positive or non-finite Decimal {s!r}")
    return d


def _validate_file_seal(seal: Any, label: str) -> None:
    if not isinstance(seal, dict) or set(seal.keys()) != FILE_SEAL_EXACT_KEYS:
        raise SchemaViolationError(f"{label}: invalid FileSeal keyset")
    rel = seal["relative_path"]
    size_b = seal["size_bytes"]
    sha = seal["sha256"]
    if (
        not isinstance(rel, str)
        or not rel
        or rel.startswith("/")
        or "\\" in rel
        or ".." in Path(rel).parts
    ):
        raise SchemaViolationError(f"{label}: invalid relative_path {rel!r}")
    if not _is_strict_int(size_b) or size_b <= 0:
        raise SchemaViolationError(f"{label}: invalid size_bytes {size_b!r}")
    if not isinstance(sha, str) or not SHA256_REGEX.match(sha):
        raise SchemaViolationError(f"{label}: invalid sha256 {sha!r}")


def _validate_trade_ref(ref: Any, label: str) -> Decimal:
    if not isinstance(ref, dict) or set(ref.keys()) != TRADE_REF_EXACT_KEYS:
        raise SchemaViolationError(f"{label}: invalid TradeRef keyset")
    utc_d = ref["utc_date"]
    prow = ref["physical_row"]
    tid = ref["agg_trade_id"]
    tms = ref["time_ms"]
    price = ref["price"]
    if not isinstance(utc_d, str) or not DATE_REGEX.match(utc_d):
        raise SchemaViolationError(f"{label}: invalid utc_date {utc_d!r}")
    if not _is_strict_int(prow) or prow < 1:
        raise SchemaViolationError(f"{label}: invalid physical_row {prow!r}")
    if not _is_strict_int(tid) or tid < 0:
        raise SchemaViolationError(f"{label}: invalid agg_trade_id {tid!r}")
    if not _is_strict_int(tms) or tms <= 0:
        raise SchemaViolationError(f"{label}: invalid time_ms {tms!r}")
    return _parse_positive_decimal(price, f"{label}.price")


def _compute_distribution(values: list[Fraction]) -> dict[str, Any]:
    n = len(values)
    if n == 0:
        return {
            "max": None,
            "mean": None,
            "median": None,
            "min": None,
            "n": 0,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
        }
    s = sorted(values)
    mean_v = sum(s, Fraction(0, 1)) / Fraction(n, 1)
    med_v = s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / Fraction(2, 1)

    def _q(num: int, den: int) -> Fraction:
        rank = (num * n + den - 1) // den
        return s[rank - 1]

    return {
        "max": _format_fraction(s[-1]),
        "mean": _format_fraction(mean_v),
        "median": _format_fraction(med_v),
        "min": _format_fraction(s[0]),
        "n": n,
        "p10": _format_fraction(_q(1, 10)),
        "p25": _format_fraction(_q(1, 4)),
        "p75": _format_fraction(_q(3, 4)),
        "p90": _format_fraction(_q(9, 10)),
    }


def _recompute_parents_and_groups(
    child_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_parent: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for c in child_rows:
        k = (str(c["parent_article_id"]), str(c["listing_regime"]), str(c["direction"]))
        if k not in by_parent:
            by_parent[k] = []
        by_parent[k].append(c)

    parent_rows: list[dict[str, Any]] = []
    for k in sorted(by_parent.keys()):
        pid, reg, direction = k
        members = sorted(by_parent[k], key=lambda x: str(x["symbol"]))
        syms = [str(m["symbol"]) for m in members]
        dates: set[str] = set()
        comp_m: list[dict[str, Any]] = []
        n_gap = 0
        for m in members:
            if m["t0"] is not None:
                dates.add(str(m["t0"]["utc_date"]))
            if m["state"] == "complete":
                comp_m.append(m)
            else:
                n_gap += 1
        n_comp = len(comp_m)
        if n_gap == 0 and n_comp > 0:
            terms = sorted(_parse_fraction(m["terminal_bps"], "c.terminal") for m in comp_m)
            mfes = sorted(_parse_fraction(m["mfe_bps"], "c.mfe") for m in comp_m)
            maes = sorted(_parse_fraction(m["mae_bps"], "c.mae") for m in comp_m)

            def _med(arr: list[Fraction]) -> str:
                ln = len(arr)
                v = arr[ln // 2] if ln % 2 == 1 else (arr[ln // 2 - 1] + arr[ln // 2]) / Fraction(2, 1)
                return _format_fraction(v)

            tc = {"neither": 0, "risk": 0, "target": 0}
            for m in comp_m:
                tc[str(m["first_touch"])] += 1
            parent_rows.append(
                {
                    "direction": direction,
                    "listing_regime": reg,
                    "mae_bps": _med(maes),
                    "mfe_bps": _med(mfes),
                    "n_complete": n_comp,
                    "n_gap": 0,
                    "parent_article_id": pid,
                    "state": "complete",
                    "symbols": syms,
                    "terminal_bps": _med(terms),
                    "touch_counts": tc,
                    "utc_dates": sorted(dates),
                }
            )
        else:
            parent_rows.append(
                {
                    "direction": direction,
                    "listing_regime": reg,
                    "mae_bps": None,
                    "mfe_bps": None,
                    "n_complete": n_comp,
                    "n_gap": n_gap,
                    "parent_article_id": pid,
                    "state": "gap",
                    "symbols": syms,
                    "terminal_bps": None,
                    "touch_counts": None,
                    "utc_dates": sorted(dates),
                }
            )

    group_rows: list[dict[str, Any]] = []
    for reg, direction in (
        ("pre_market", "long"),
        ("pre_market", "short"),
        ("standard", "long"),
        ("standard", "short"),
    ):
        g_c = [c for c in child_rows if c["listing_regime"] == reg and c["direction"] == direction]
        g_p = [p for p in parent_rows if p["listing_regime"] == reg and p["direction"] == direction]
        comp_c = [c for c in g_c if c["state"] == "complete"]
        gap_c = [c for c in g_c if c["state"] != "complete"]
        comp_p = [p for p in g_p if p["state"] == "complete"]
        gap_p = [p for p in g_p if p["state"] != "complete"]

        c_term = [_parse_fraction(c["terminal_bps"], "c.term") for c in comp_c]
        c_mfe = [_parse_fraction(c["mfe_bps"], "c.mfe") for c in comp_c]
        c_mae = [_parse_fraction(c["mae_bps"], "c.mae") for c in comp_c]

        p_term = [_parse_fraction(p["terminal_bps"], "p.term") for p in comp_p]
        p_mfe = [_parse_fraction(p["mfe_bps"], "p.mfe") for p in comp_p]
        p_mae = [_parse_fraction(p["mae_bps"], "p.mae") for p in comp_p]

        c_stats = {
            "mae": _compute_distribution(c_mae),
            "mfe": _compute_distribution(c_mfe),
            "n_complete": len(comp_c),
            "n_gap": len(gap_c),
            "n_total": len(g_c),
            "terminal": _compute_distribution(c_term),
        }
        p_stats = {
            "mae": _compute_distribution(p_mae),
            "mfe": _compute_distribution(p_mfe),
            "n_complete": len(comp_p),
            "n_gap": len(gap_p),
            "n_total": len(g_p),
            "terminal": _compute_distribution(p_term),
        }
        g_tc = {"neither": 0, "risk": 0, "target": 0}
        for c in comp_c:
            g_tc[str(c["first_touch"])] += 1

        if len(comp_p) == 0:
            p_tf: dict[str, Any] = {"neither": None, "risk": None, "target": None}
        else:
            denom = Fraction(len(comp_p), 1)
            t_s = sum((Fraction(int(p["touch_counts"]["target"]), int(p["n_complete"])) for p in comp_p), Fraction(0, 1))
            r_s = sum((Fraction(int(p["touch_counts"]["risk"]), int(p["n_complete"])) for p in comp_p), Fraction(0, 1))
            n_s = sum((Fraction(int(p["touch_counts"]["neither"]), int(p["n_complete"])) for p in comp_p), Fraction(0, 1))
            p_tf = {
                "neither": _format_fraction(n_s / denom),
                "risk": _format_fraction(r_s / denom),
                "target": _format_fraction(t_s / denom),
            }

        costs: list[dict[str, Any]] = []
        for cbps in (50, 80, 150):
            cf = Fraction(cbps, 1)
            ca = [m - cf for m in c_mfe]
            pa = [m - cf for m in p_mfe]
            cp_cnt = sum(1 for v in ca if v > 0)
            pp_cnt = sum(1 for v in pa if v > 0)
            if len(g_c) == 0 or len(gap_c) > 0:
                sp = "evidence_insufficient"
            elif cp_cnt > 0:
                sp = "observed_space"
            else:
                sp = "no_observed_space"
            costs.append(
                {
                    "child": _compute_distribution(ca),
                    "child_positive": cp_cnt,
                    "cost_bps": cbps,
                    "parent": _compute_distribution(pa),
                    "parent_positive": pp_cnt,
                    "space_status": sp,
                }
            )

        s_cp = sorted(
            comp_p,
            key=lambda p: (-_parse_fraction(p["mfe_bps"], "p.mfe"), str(p["parent_article_id"])),
        )
        t1_ids = [str(p["parent_article_id"]) for p in s_cp[:1]]
        t3_ids = [str(p["parent_article_id"]) for p in s_cp[:3]]
        tot_mfe = sum((_parse_fraction(p["mfe_bps"], "p.mfe") for p in s_cp), Fraction(0, 1))
        if tot_mfe <= 0:
            t1_sh = None
            t3_sh = None
        else:
            t1_m = sum((_parse_fraction(p["mfe_bps"], "p.mfe") for p in s_cp[:1]), Fraction(0, 1))
            t3_m = sum((_parse_fraction(p["mfe_bps"], "p.mfe") for p in s_cp[:3]), Fraction(0, 1))
            t1_sh = _format_fraction(t1_m / tot_mfe)
            t3_sh = _format_fraction(t3_m / tot_mfe)

        group_rows.append(
            {
                "child": c_stats,
                "concentration": {
                    "top1_parent_ids": t1_ids,
                    "top1_share": t1_sh,
                    "top3_parent_ids": t3_ids,
                    "top3_share": t3_sh,
                },
                "costs": costs,
                "direction": direction,
                "listing_regime": reg,
                "parent": p_stats,
                "parent_touch_fraction_mean": p_tf,
                "touch_counts": g_tc,
            }
        )
    return parent_rows, group_rows


def _render_expected_review(summary: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Stage 1.5J-C 时间与路径诊断",
        f"run_id: {summary['run_id']}",
        f"profile_id: {summary['profile_id']}",
        f"artifact_kind: {summary['artifact_kind']}",
        f"analysis_state: {summary['analysis_state']}",
        "universe_children: 281",
        "selected_children: 71",
    ]
    for grp in summary["group_rows"]:
        cs = grp["child"]
        ps = grp["parent"]
        tc = grp["touch_counts"]
        lines.append(f"## {grp['listing_regime']} / {grp['direction']}")
        lines.append(
            f"children: {cs['n_total']}; complete: {cs['n_complete']}; gap: {cs['n_gap']}"
        )
        lines.append(
            f"parents: {ps['n_total']}; complete: {ps['n_complete']}; gap: {ps['n_gap']}"
        )
        lines.append(
            f"first_touch: target={tc['target']}; risk={tc['risk']}; neither={tc['neither']}"
        )
        for cr in grp["costs"]:
            lines.append(f"cost_bps={cr['cost_bps']}; space_status={cr['space_status']}")
    lines.append(
        "Exploratory price-path diagnosis only; no alpha, execution, paper or live trading authority."
    )
    return "\n".join(lines) + "\n"


def verify_artifact_root(artifact_root_str: str, profile_id: str) -> None:
    """Verify Stage 1.5J-C receipt root against literal profile constants and artifact bytes."""
    if profile_id != PROFILE_ID:
        raise SchemaViolationError(f"Unsupported profile: {profile_id!r}")

    is_abs = os.path.isabs(artifact_root_str)
    root_path = Path(artifact_root_str)

    if is_abs:
        if _has_symlink_ancestor(root_path):
            raise SchemaViolationError(f"Symlink in absolute root path: {root_path}")
        expected_kind = "validation_only"
    else:
        cwd = Path.cwd()
        full_rel = cwd / root_path
        if _has_symlink_ancestor(full_rel, stop_at=cwd):
            raise SchemaViolationError(f"Symlink in relative root path: {root_path}")
        expected_kind = "production_diagnostic"

    if not root_path.is_dir():
        raise SchemaViolationError(f"Artifact root is not a directory: {root_path}")

    entries = sorted(os.listdir(root_path))
    if entries != ["manifest.json", "review_CN.md", "summary.json"]:
        raise SchemaViolationError(f"Sealed-tree violation: entries={entries}")
    for fname in entries:
        fp = root_path / fname
        if os.path.islink(fp) or not fp.is_file():
            raise SchemaViolationError(f"Non-regular file or symlink in root: {fp}")

    manifest_bytes = (root_path / "manifest.json").read_bytes()
    summary_bytes = (root_path / "summary.json").read_bytes()
    review_bytes = (root_path / "review_CN.md").read_bytes()

    manifest = _parse_canonical_json_bytes(manifest_bytes, "manifest.json")
    summary = _parse_canonical_json_bytes(summary_bytes, "summary.json")

    if not isinstance(manifest, dict) or set(manifest.keys()) != MANIFEST_EXACT_KEYS:
        raise SchemaViolationError("manifest.json exact keyset violation")
    if not isinstance(summary, dict) or set(summary.keys()) != SUMMARY_EXACT_KEYS:
        raise SchemaViolationError("summary.json exact keyset violation")

    if (
        manifest["profile_id"] != PROFILE_ID
        or manifest["profile_contract_version"] != PROFILE_CONTRACT_VERSION
        or not _is_strict_int(manifest["profile_contract_version"])
        or summary["profile_id"] != PROFILE_ID
        or summary["profile_contract_version"] != PROFILE_CONTRACT_VERSION
        or not _is_strict_int(summary["profile_contract_version"])
    ):
        raise SchemaViolationError("profile_id or profile_contract_version mismatch")

    run_id = summary["run_id"]
    if not isinstance(run_id, str) or manifest["run_id"] != run_id or root_path.name != run_id:
        raise SchemaViolationError("run_id mismatch across root, manifest, and summary")
    m_run = RUN_ID_REGEX.match(run_id)
    if not m_run:
        raise SchemaViolationError(f"Invalid run_id grammar: {run_id!r}")
    try:
        datetime.strptime(m_run.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise SchemaViolationError(f"Invalid UTC timestamp in run_id: {run_id!r}") from exc

    if (
        manifest["artifact_kind"] != expected_kind
        or summary["artifact_kind"] != expected_kind
    ):
        raise SchemaViolationError(
            f"artifact_kind mismatch with root type: expected {expected_kind!r}"
        )
    if not is_abs:
        expected_rel = f"{OUTPUT_PARENT_RELATIVE_PATH}/{run_id}"
        if artifact_root_str.rstrip("/") != expected_rel:
            raise SchemaViolationError(
                f"production_diagnostic root must be {expected_rel!r}, got {artifact_root_str!r}"
            )

    expected_files = [
        {
            "relative_path": "review_CN.md",
            "sha256": hashlib.sha256(review_bytes).hexdigest(),
            "size_bytes": len(review_bytes),
        },
        {
            "relative_path": "summary.json",
            "sha256": hashlib.sha256(summary_bytes).hexdigest(),
            "size_bytes": len(summary_bytes),
        },
    ]
    if manifest["files"] != expected_files:
        raise SchemaViolationError("manifest.files seal mismatch")

    # Authority, protocol, permissions
    if summary["protocol"] != EXPECTED_PROTOCOL_OBJECT:
        raise SchemaViolationError("protocol mismatch")

    perms = summary["permissions"]
    if not isinstance(perms, dict) or set(perms.keys()) != PERMISSIONS_EXACT_KEYS:
        raise SchemaViolationError("permissions keyset violation")
    for pk, pv in perms.items():
        if pv is not False or type(pv) is not bool:
            raise SchemaViolationError(f"permission {pk!r} must be strictly False")

    auth = summary["authority"]
    if not isinstance(auth, dict) or set(auth.keys()) != AUTHORITY_EXACT_KEYS:
        raise SchemaViolationError("authority keyset violation")

    for sk in (
        "design",
        "plan",
        "user_receipt_generation_approval",
        "authorization_release",
        "run_authorization",
    ):
        _validate_file_seal(auth[sk], f"authority.{sk}")

    if (
        auth["design"]["relative_path"] != APPROVED_DESIGN_RELATIVE_PATH
        or auth["design"]["sha256"] != APPROVED_DESIGN_SHA256
    ):
        raise SchemaViolationError("authority.design path or SHA mismatch")
    if auth["plan"]["relative_path"] != APPROVED_PLAN_RELATIVE_PATH:
        raise SchemaViolationError("authority.plan relative_path mismatch")

    plan_sha = auth["plan"]["sha256"]
    expected_auth_prefix = f".git/plan-execution/stage1_5j_c/{plan_sha}/{run_id}"
    if (
        auth["user_receipt_generation_approval"]["relative_path"]
        != f"{expected_auth_prefix}/user_receipt_generation_approval.txt"
        or auth["authorization_release"]["relative_path"]
        != f"{expected_auth_prefix}/authorization_release.json"
        or auth["run_authorization"]["relative_path"]
        != f"{expected_auth_prefix}/run_authorization.json"
    ):
        raise SchemaViolationError("authority embedded .git path grammar mismatch")

    src_files = auth["source_files"]
    if not isinstance(src_files, list) or len(src_files) != 11:
        raise SchemaViolationError("authority.source_files must have 11 entries")
    for sf in src_files:
        _validate_file_seal(sf, "authority.source_files")
    if [sf["relative_path"] for sf in src_files] != ALL_11_SOURCE_RELATIVE_PATHS:
        raise SchemaViolationError("authority.source_files paths or ordering mismatch")
    for sf in src_files:
        rp = sf["relative_path"]
        if rp in FROZEN_SOURCE_FILE_HASHES and sf["sha256"] != FROZEN_SOURCE_FILE_HASHES[rp]:
            raise SchemaViolationError(f"Frozen source SHA mismatch for {rp}")

    inp_files = auth["input_files"]
    if not isinstance(inp_files, list) or len(inp_files) != 9:
        raise SchemaViolationError("authority.input_files must have 9 entries")
    for inf in inp_files:
        _validate_file_seal(inf, "authority.input_files")
    if [inf["relative_path"] for inf in inp_files] != ALL_9_INPUT_RELATIVE_PATHS:
        raise SchemaViolationError("authority.input_files paths or ordering mismatch")
    for inf in inp_files:
        rp = inf["relative_path"]
        if inf["sha256"] != FROZEN_INPUT_FILE_HASHES[rp]:
            raise SchemaViolationError(f"Frozen input SHA mismatch for {rp}")

    # Universe validation
    u_rows = summary["universe_rows"]
    if not isinstance(u_rows, list) or len(u_rows) != 281:
        raise SchemaViolationError("universe_rows must have 281 rows")
    u_keys: list[tuple[str, str]] = []
    selected_u_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for idx, u in enumerate(u_rows):
        if not isinstance(u, dict) or set(u.keys()) != UNIVERSE_EXACT_KEYS:
            raise SchemaViolationError(f"universe_rows[{idx}] keyset violation")
        pid = u["parent_article_id"]
        sym = u["symbol"]
        ac = u["asset_class"]
        reg = u["listing_regime"]
        cs = u["classification_status"]
        in_sc = u["in_scope"]
        if not isinstance(pid, str) or not HEX32_REGEX.match(pid):
            raise SchemaViolationError(f"universe_rows[{idx}] invalid parent_article_id")
        if not isinstance(sym, str) or not sym.endswith("USDT") or sym != sym.upper():
            raise SchemaViolationError(f"universe_rows[{idx}] invalid symbol")
        if ac not in ALLOWED_ASSET_CLASSES or reg not in ALLOWED_LISTING_REGIMES or cs not in ALLOWED_CLASSIFICATION_STATUS:
            raise SchemaViolationError(f"universe_rows[{idx}] invalid classification enum")
        if type(in_sc) is not bool:
            raise SchemaViolationError(f"universe_rows[{idx}] in_scope not bool")
        expected_in_scope = (
            ac == "crypto"
            and reg in ("standard", "pre_market")
            and cs == "confirmed"
        )
        if in_sc != expected_in_scope:
            raise SchemaViolationError(f"universe_rows[{idx}] in_scope predicate mismatch")
        k = (pid, sym)
        u_keys.append(k)
        if in_sc:
            selected_u_by_key[k] = u

    if u_keys != sorted(u_keys) or len(set(u_keys)) != 281:
        raise SchemaViolationError("universe_rows must be strictly sorted and unique")
    if len(selected_u_by_key) != 71:
        raise SchemaViolationError(f"selected universe count must be 71, got {len(selected_u_by_key)}")

    # Child rows validation
    c_rows = summary["child_rows"]
    if not isinstance(c_rows, list) or len(c_rows) != 142:
        raise SchemaViolationError("child_rows must have 142 rows")
    c_keys: list[tuple[str, str, str]] = []
    c_by_pair: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}

    for idx, c in enumerate(c_rows):
        if not isinstance(c, dict) or set(c.keys()) != CHILD_EXACT_KEYS:
            raise SchemaViolationError(f"child_rows[{idx}] keyset violation")
        pid = c["parent_article_id"]
        sym = c["symbol"]
        reg = c["listing_regime"]
        direction = c["direction"]
        state = c["state"]
        uk = (pid, sym)
        if uk not in selected_u_by_key or selected_u_by_key[uk]["listing_regime"] != reg:
            raise SchemaViolationError(f"child_rows[{idx}] not in selected universe or regime mismatch")
        if direction not in ("long", "short") or state not in ALLOWED_CHILD_STATES:
            raise SchemaViolationError(f"child_rows[{idx}] invalid direction or state")
        ck = (pid, sym, direction)
        c_keys.append(ck)
        if uk not in c_by_pair:
            c_by_pair[uk] = {}
        c_by_pair[uk][direction] = c

        # Conditional state validation
        t0 = c["t0"]
        entry = c["entry"]
        endpoint = c["endpoint"]
        mfe_tr = c["mfe_trade"]
        mae_tr = c["mae_trade"]
        term_bps = c["terminal_bps"]
        mfe_bps = c["mfe_bps"]
        mae_bps = c["mae_bps"]
        ft = c["first_touch"]
        touch_tr = c["touch_trade"]
        max_gap = c["max_intertrade_gap_ms"]

        if state != "complete":
            if (
                mfe_tr is not None
                or mae_tr is not None
                or term_bps is not None
                or mfe_bps is not None
                or mae_bps is not None
                or ft != "unavailable"
                or touch_tr is not None
                or max_gap is not None
            ):
                raise SchemaViolationError(f"child_rows[{idx}] non-complete state has non-null metrics")
            if state in ("inherited_j_a_parent_gap", "anchor_unavailable"):
                if t0 is not None or entry is not None or endpoint is not None:
                    raise SchemaViolationError(f"child_rows[{idx}] {state} must have null t0/entry/endpoint")
            elif state in ("required_package_unavailable", "entry_unavailable"):
                _validate_trade_ref(t0, f"child_rows[{idx}].t0")
                if entry is not None or endpoint is not None:
                    raise SchemaViolationError(f"child_rows[{idx}] {state} must have null entry/endpoint")
            elif state == "endpoint_unavailable":
                _validate_trade_ref(t0, f"child_rows[{idx}].t0")
                if entry is not None:
                    _validate_trade_ref(entry, f"child_rows[{idx}].entry")
                if endpoint is not None:
                    raise SchemaViolationError(f"child_rows[{idx}] endpoint_unavailable must have null endpoint")
            elif state == "sequence_gap":
                _validate_trade_ref(t0, f"child_rows[{idx}].t0")
                _validate_trade_ref(entry, f"child_rows[{idx}].entry")
                _validate_trade_ref(endpoint, f"child_rows[{idx}].endpoint")
        else:
            _validate_trade_ref(t0, f"child_rows[{idx}].t0")
            pe_dec = _validate_trade_ref(entry, f"child_rows[{idx}].entry")
            pend_dec = _validate_trade_ref(endpoint, f"child_rows[{idx}].endpoint")
            pmfe_dec = _validate_trade_ref(mfe_tr, f"child_rows[{idx}].mfe_trade")
            pmae_dec = _validate_trade_ref(mae_tr, f"child_rows[{idx}].mae_trade")
            if not _is_strict_int(max_gap) or max_gap < 0:
                raise SchemaViolationError(f"child_rows[{idx}] invalid max_intertrade_gap_ms")

            term_f = _parse_fraction(term_bps, f"child_rows[{idx}].terminal_bps")
            mfe_f = _parse_fraction(mfe_bps, f"child_rows[{idx}].mfe_bps")
            mae_f = _parse_fraction(mae_bps, f"child_rows[{idx}].mae_bps")
            if mfe_f < 0 or mae_f > 0:
                raise SchemaViolationError(f"child_rows[{idx}] MFE/MAE sign violation")

            pe_f = Fraction(pe_dec)

            def _dir_bps(p_d: Decimal) -> Fraction:
                pf = Fraction(p_d)
                if direction == "long":
                    return Fraction(10000, 1) * (pf / pe_f - Fraction(1, 1))
                return Fraction(10000, 1) * (Fraction(1, 1) - pf / pe_f)

            if (
                term_f != _dir_bps(pend_dec)
                or mfe_f != _dir_bps(pmfe_dec)
                or mae_f != _dir_bps(pmae_dec)
            ):
                raise SchemaViolationError(f"child_rows[{idx}] TradeRef price vs bps formula mismatch")

            if ft == "neither":
                if touch_tr is not None or mfe_f >= Fraction(3000, 1) or mae_f <= Fraction(-200, 1):
                    raise SchemaViolationError(f"child_rows[{idx}] invalid neither first_touch")
            elif ft in ("target", "risk"):
                if touch_tr is None:
                    raise SchemaViolationError(f"child_rows[{idx}] {ft} requires touch_trade")
                pt_dec = _validate_trade_ref(touch_tr, f"child_rows[{idx}].touch_trade")
                tbps = _dir_bps(pt_dec)
                if ft == "target" and tbps < Fraction(3000, 1):
                    raise SchemaViolationError(f"child_rows[{idx}] target touch_trade < 3000 bps")
                if ft == "risk" and tbps > Fraction(-200, 1):
                    raise SchemaViolationError(f"child_rows[{idx}] risk touch_trade > -200 bps")
            else:
                raise SchemaViolationError(f"child_rows[{idx}] invalid first_touch {ft!r}")

    if c_keys != sorted(c_keys) or len(set(c_keys)) != 142:
        raise SchemaViolationError("child_rows must be strictly sorted and unique")

    for uk, pair_map in c_by_pair.items():
        if set(pair_map.keys()) != {"long", "short"}:
            raise SchemaViolationError(f"Missing long/short pair for {uk}")
        c_l = pair_map["long"]
        c_s = pair_map["short"]
        if (
            c_l["state"] != c_s["state"]
            or c_l["t0"] != c_s["t0"]
            or c_l["entry"] != c_s["entry"]
            or c_l["endpoint"] != c_s["endpoint"]
            or c_l["max_intertrade_gap_ms"] != c_s["max_intertrade_gap_ms"]
        ):
            raise SchemaViolationError(f"long/short shared path reference mismatch for {uk}")

    # Parent and Group structural & projection validation
    p_rows = summary["parent_rows"]
    g_rows = summary["group_rows"]
    if not isinstance(p_rows, list) or not isinstance(g_rows, list):
        raise SchemaViolationError("parent_rows and group_rows must be lists")
    for p in p_rows:
        if not isinstance(p, dict) or set(p.keys()) != PARENT_EXACT_KEYS:
            raise SchemaViolationError("parent_rows keyset violation")
        if p["touch_counts"] is not None:
            if not isinstance(p["touch_counts"], dict) or set(p["touch_counts"].keys()) != TOUCH_COUNTS_EXACT_KEYS:
                raise SchemaViolationError("parent touch_counts keyset violation")
    for g in g_rows:
        if not isinstance(g, dict) or set(g.keys()) != GROUP_EXACT_KEYS:
            raise SchemaViolationError("group_rows keyset violation")
        for lk in ("child", "parent"):
            if not isinstance(g[lk], dict) or set(g[lk].keys()) != LEVEL_STATS_EXACT_KEYS:
                raise SchemaViolationError(f"group.{lk} keyset violation")
            for dk in ("terminal", "mfe", "mae"):
                if not isinstance(g[lk][dk], dict) or set(g[lk][dk].keys()) != DISTRIBUTION_EXACT_KEYS:
                    raise SchemaViolationError(f"group.{lk}.{dk} keyset violation")
        if not isinstance(g["touch_counts"], dict) or set(g["touch_counts"].keys()) != TOUCH_COUNTS_EXACT_KEYS:
            raise SchemaViolationError("group.touch_counts keyset violation")
        if not isinstance(g["parent_touch_fraction_mean"], dict) or set(g["parent_touch_fraction_mean"].keys()) != TOUCH_COUNTS_EXACT_KEYS:
            raise SchemaViolationError("group.parent_touch_fraction_mean keyset violation")
        if not isinstance(g["concentration"], dict) or set(g["concentration"].keys()) != CONCENTRATION_EXACT_KEYS:
            raise SchemaViolationError("group.concentration keyset violation")
        if not isinstance(g["costs"], list) or len(g["costs"]) != 3:
            raise SchemaViolationError("group.costs must have 3 entries")
        for cr in g["costs"]:
            if not isinstance(cr, dict) or set(cr.keys()) != COST_STATS_EXACT_KEYS:
                raise SchemaViolationError("CostStats keyset violation")

    expected_parents, expected_groups = _recompute_parents_and_groups(c_rows)
    if p_rows != expected_parents:
        raise SchemaViolationError("parent_rows projection mismatch")
    if g_rows != expected_groups:
        raise SchemaViolationError("group_rows projection mismatch")

    expected_analysis_state = (
        "time_path_described"
        if all(c["state"] == "complete" for c in c_rows)
        else "time_path_evidence_gap"
    )
    if summary["analysis_state"] != expected_analysis_state:
        raise SchemaViolationError("analysis_state mismatch")

    try:
        review_str = review_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SchemaViolationError("review_CN.md invalid UTF-8") from exc
    if review_str != _render_expected_review(summary):
        raise SchemaViolationError("review_CN.md deterministic projection mismatch")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_stage1_5j_c_receipt_schema.py",
        description="Verify Stage 1.5J-C receipt root against Rule 17 profile stage1_5j_c_time_path_v1.",
    )
    parser.add_argument(
        "--profile",
        required=True,
        help="Rule 17 profile ID (must be stage1_5j_c_time_path_v1).",
    )
    parser.add_argument(
        "--artifact-root",
        required=True,
        help="Path to the Stage 1.5J-C receipt root.",
    )
    args = parser.parse_args(argv)

    try:
        verify_artifact_root(str(args.artifact_root), str(args.profile))
    except (SchemaViolationError, Exception) as exc:
        sys.stderr.write(f"Contract violation [{args.profile}]: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
