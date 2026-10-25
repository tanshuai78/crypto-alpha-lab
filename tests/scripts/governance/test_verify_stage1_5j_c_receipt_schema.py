"""Unit and mutation-matrix tests for standalone J-C Rule 17 schema verifier."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VERIFIER_PATH = PROJECT_ROOT / "scripts/governance/verify_stage1_5j_c_receipt_schema.py"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dump_canonical_json(obj: Any) -> bytes:
    return (
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _test_parse_fraction(s: Any) -> Fraction:
    parts = s.split("/")
    return Fraction(int(parts[0]), int(parts[1]))


def _test_format_fraction(f: Fraction) -> str:
    return f"{f.numerator}/{f.denominator}"


def _test_compute_distribution(values: list[Fraction]) -> dict[str, Any]:
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
        "max": _test_format_fraction(s[-1]),
        "mean": _test_format_fraction(mean_v),
        "median": _test_format_fraction(med_v),
        "min": _test_format_fraction(s[0]),
        "n": n,
        "p10": _test_format_fraction(_q(1, 10)),
        "p25": _test_format_fraction(_q(1, 4)),
        "p75": _test_format_fraction(_q(3, 4)),
        "p90": _test_format_fraction(_q(9, 10)),
    }


def _test_compute_parents_and_groups(
    child_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_parent: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for c in child_rows:
        k = (str(c["parent_article_id"]), str(c["listing_regime"]), str(c["direction"]))
        by_parent.setdefault(k, []).append(c)

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
            terms = sorted(_test_parse_fraction(m["terminal_bps"]) for m in comp_m)
            mfes = sorted(_test_parse_fraction(m["mfe_bps"]) for m in comp_m)
            maes = sorted(_test_parse_fraction(m["mae_bps"]) for m in comp_m)

            def _med(arr: list[Fraction]) -> str:
                ln = len(arr)
                v = (
                    arr[ln // 2]
                    if ln % 2 == 1
                    else (arr[ln // 2 - 1] + arr[ln // 2]) / Fraction(2, 1)
                )
                return _test_format_fraction(v)

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

        c_term = [_test_parse_fraction(c["terminal_bps"]) for c in comp_c]
        c_mfe = [_test_parse_fraction(c["mfe_bps"]) for c in comp_c]
        c_mae = [_test_parse_fraction(c["mae_bps"]) for c in comp_c]

        p_term = [_test_parse_fraction(p["terminal_bps"]) for p in comp_p]
        p_mfe = [_test_parse_fraction(p["mfe_bps"]) for p in comp_p]
        p_mae = [_test_parse_fraction(p["mae_bps"]) for p in comp_p]

        c_stats = {
            "mae": _test_compute_distribution(c_mae),
            "mfe": _test_compute_distribution(c_mfe),
            "n_complete": len(comp_c),
            "n_gap": len(gap_c),
            "n_total": len(g_c),
            "terminal": _test_compute_distribution(c_term),
        }
        p_stats = {
            "mae": _test_compute_distribution(p_mae),
            "mfe": _test_compute_distribution(p_mfe),
            "n_complete": len(comp_p),
            "n_gap": len(gap_p),
            "n_total": len(g_p),
            "terminal": _test_compute_distribution(p_term),
        }
        g_tc = {"neither": 0, "risk": 0, "target": 0}
        for c in comp_c:
            g_tc[str(c["first_touch"])] += 1

        if len(comp_p) == 0:
            p_tf: dict[str, Any] = {"neither": None, "risk": None, "target": None}
        else:
            denom = Fraction(len(comp_p), 1)
            t_s = sum(
                (
                    Fraction(int(p["touch_counts"]["target"]), int(p["n_complete"]))
                    for p in comp_p
                ),
                Fraction(0, 1),
            )
            r_s = sum(
                (
                    Fraction(int(p["touch_counts"]["risk"]), int(p["n_complete"]))
                    for p in comp_p
                ),
                Fraction(0, 1),
            )
            n_s = sum(
                (
                    Fraction(int(p["touch_counts"]["neither"]), int(p["n_complete"]))
                    for p in comp_p
                ),
                Fraction(0, 1),
            )
            p_tf = {
                "neither": _test_format_fraction(n_s / denom),
                "risk": _test_format_fraction(r_s / denom),
                "target": _test_format_fraction(t_s / denom),
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
                    "child": _test_compute_distribution(ca),
                    "child_positive": cp_cnt,
                    "cost_bps": cbps,
                    "parent": _test_compute_distribution(pa),
                    "parent_positive": pp_cnt,
                    "space_status": sp,
                }
            )

        s_cp = sorted(
            comp_p,
            key=lambda p: (
                -_test_parse_fraction(p["mfe_bps"]),
                str(p["parent_article_id"]),
            ),
        )
        t1_ids = [str(p["parent_article_id"]) for p in s_cp[:1]]
        t3_ids = [str(p["parent_article_id"]) for p in s_cp[:3]]
        tot_mfe = sum((_test_parse_fraction(p["mfe_bps"]) for p in s_cp), Fraction(0, 1))
        if tot_mfe <= 0:
            t1_sh = None
            t3_sh = None
        else:
            t1_m = sum((_test_parse_fraction(p["mfe_bps"]) for p in s_cp[:1]), Fraction(0, 1))
            t3_m = sum((_test_parse_fraction(p["mfe_bps"]) for p in s_cp[:3]), Fraction(0, 1))
            t1_sh = _test_format_fraction(t1_m / tot_mfe)
            t3_sh = _test_format_fraction(t3_m / tot_mfe)

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


def _test_render_review(summary: dict[str, Any]) -> str:
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


FIXTURE_PROFILE_ID = "stage1_5j_c_time_path_v1"
FIXTURE_PROFILE_CONTRACT_VERSION = 1

FIXTURE_APPROVED_DESIGN_RELATIVE_PATH = (
    "docs/designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md"
)
FIXTURE_APPROVED_DESIGN_SHA256 = (
    "32d5130806489c0848748060835a7c0fb8f1715a3f9fb6b479c2f02cff5d4e45"
)

FIXTURE_APPROVED_PLAN_RELATIVE_PATH = (
    "docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md"
)

FIXTURE_PROTOCOL_RELATIVE_PATH = (
    "docs/production_artifacts/stage1_5j_c_time_path_protocol_v1.json"
)
FIXTURE_PROTOCOL_SHA256 = (
    "4dd353751256191d75fc52388413d97e5a7b177e499bbee28e2dd2ff356e1cbe"
)
FIXTURE_EXPECTED_PROTOCOL_OBJECT = {
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

FIXTURE_PERMISSIONS_EXACT_KEYS = (
    "alpha_claim_allowed",
    "consumer_promotion_allowed",
    "execution_allowed",
    "live_trading_allowed",
    "network_allowed",
    "paper_trading_allowed",
    "receipt_regeneration_allowed",
    "signal_allowed",
)

FIXTURE_FROZEN_SOURCE_FILE_HASHES: dict[str, str] = {
    "configs/base.py": "473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc",
    "configs/stage1_5j_b_historical_aggtrades_launch_response.py": "771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4",
    "scripts/external_signal_shadow/export_stage1_5j_dataset_v2.py": "b70faa18f4da875d1c3db950b312d97f49551b4887f22c2baf3b96531e6926d8",
    "scripts/external_signal_shadow/verify_stage1_5j_dataset_v2.py": "52623af3d766ad52e45b0ca61dd748340cd664644f855b800f5cd7ffc28fb3ee",
    "scripts/governance/verify_artifact_schema.py": "7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473",
    "scripts/governance/verify_stage1_5j_b_receipt_schema.py": "442c527fb7f49d78eff4e13fd68e5fabfff12ba1e74089cd5e5133977cde90f1",
    "src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py": "250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18",
    "src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py": "b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f",
}

FIXTURE_J_C_SOURCE_RELATIVE_PATHS: tuple[str, ...] = (
    "scripts/external_signal_shadow/run_stage1_5j_c_launch_time_path_feasibility.py",
    "scripts/governance/verify_stage1_5j_c_receipt_schema.py",
    "src/research/external_signal_shadow/stage1_5j_c_launch_time_path_feasibility.py",
)

FIXTURE_ALL_11_SOURCE_RELATIVE_PATHS: tuple[str, ...] = tuple(
    sorted(
        list(FIXTURE_FROZEN_SOURCE_FILE_HASHES.keys())
        + list(FIXTURE_J_C_SOURCE_RELATIVE_PATHS)
    )
)

FIXTURE_FROZEN_INPUT_FILE_HASHES: dict[str, str] = {
    ".git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/64e14726202b53727a7627139578369cb6af54f08d5a785d4df006009eb25a2d/evidence/receipt_closure_evidence.json": "8d535303d61b3860eaa69018eff3f76645f91b3e27af1af89e1e956b948f8b6d",
    ".git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/64e14726202b53727a7627139578369cb6af54f08d5a785d4df006009eb25a2d/evidence/receipt_closure_evidence.json.sha256": "c3856c2e9e6d5086a543891902d57246fa64a93acdbba97a1130e541f949c5d9",
    "data/exports/stage1_5j_token_launch_classification_ledger_v2.csv": "36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b",
    "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/manifest.json": "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf",
    "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/summary.json": "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b",
    "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z/manifest.json": "f0a8ac724925084161f6b9aa2dced5139b261707fda0f0f21ebd0eb6de3087fb",
    "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z/review_CN.md": "17e9ffaa973923868621a8ee925dc811c15e12459924ee63897f9c21fcac317e",
    "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z/summary.json": "5ea0f1c87803114c4c6917cd0c3d24292948fa0e7066a80e0a2bce611e32546b",
    "docs/production_artifacts/stage1_5j_c_time_path_protocol_v1.json": "4dd353751256191d75fc52388413d97e5a7b177e499bbee28e2dd2ff356e1cbe",
}

FIXTURE_ALL_9_INPUT_RELATIVE_PATHS: tuple[str, ...] = tuple(
    sorted(FIXTURE_FROZEN_INPUT_FILE_HASHES.keys())
)


def _build_schema_unit_receipt_dicts(
    *,
    run_id: str = "stage1_5j_c_launch_time_path_feasibility_20261024T150000Z",
    artifact_kind: str = "validation_only",
) -> tuple[dict[str, Any], dict[str, Any], str, dict[str, Any]]:
    """Construct a test-local, tmp_path-only schema unit fixture per Plan R1 Section 0 & 7.

    Tier: schema_unit_only.
    Makes no source provenance or raw semantic claim.
    Built by an independent literal test serializer without importing or calling producer/domain loader/CLI.
    Derives zero values from the verifier module under test.
    """
    # Explicit tier labelling and non-claim assertion per Plan R1 Section 0 & 7
    schema_unit_evidence = {
        "tier": "schema_unit_only",
        "provenance_claim": False,
        "semantic_claim": False,
        "source_backed_claim": False,
    }
    assert schema_unit_evidence["tier"] == "schema_unit_only"
    assert schema_unit_evidence["provenance_claim"] is False
    assert schema_unit_evidence["semantic_claim"] is False
    assert schema_unit_evidence["source_backed_claim"] is False

    plan_path = PROJECT_ROOT / FIXTURE_APPROVED_PLAN_RELATIVE_PATH
    plan_sha = _sha256_bytes(plan_path.read_bytes())
    plan_size = plan_path.stat().st_size
    design_size = (
        PROJECT_ROOT / FIXTURE_APPROVED_DESIGN_RELATIVE_PATH
    ).stat().st_size

    auth_prefix = f".git/plan-execution/stage1_5j_c/{plan_sha}/{run_id}"

    source_files = []
    for rel in FIXTURE_ALL_11_SOURCE_RELATIVE_PATHS:
        sha = (
            FIXTURE_FROZEN_SOURCE_FILE_HASHES[rel]
            if rel in FIXTURE_FROZEN_SOURCE_FILE_HASHES
            else "0" * 64
        )
        source_files.append({"relative_path": rel, "sha256": sha, "size_bytes": 100})

    input_files = []
    for rel in FIXTURE_ALL_9_INPUT_RELATIVE_PATHS:
        sha = FIXTURE_FROZEN_INPUT_FILE_HASHES[rel]
        input_files.append({"relative_path": rel, "sha256": sha, "size_bytes": 100})

    # Grammar FileSeals per Plan R1 Section 7
    authority_obj = {
        "authorization_release": {
            "relative_path": f"{auth_prefix}/authorization_release.json",
            "sha256": "0" * 64,
            "size_bytes": 100,
        },
        "design": {
            "relative_path": FIXTURE_APPROVED_DESIGN_RELATIVE_PATH,
            "sha256": FIXTURE_APPROVED_DESIGN_SHA256,
            "size_bytes": design_size,
        },
        "input_files": input_files,
        "plan": {
            "relative_path": FIXTURE_APPROVED_PLAN_RELATIVE_PATH,
            "sha256": plan_sha,
            "size_bytes": plan_size,
        },
        "run_authorization": {
            "relative_path": f"{auth_prefix}/run_authorization.json",
            "sha256": "0" * 64,
            "size_bytes": 100,
        },
        "source_files": source_files,
        "user_receipt_generation_approval": {
            "relative_path": f"{auth_prefix}/user_receipt_generation_approval.txt",
            "sha256": "0" * 64,
            "size_bytes": 100,
        },
    }

    universe_rows: list[dict[str, Any]] = []
    child_rows: list[dict[str, Any]] = []

    t0_ref = {
        "agg_trade_id": 100,
        "physical_row": 1,
        "price": "1.0000",
        "time_ms": 1760000000000,
        "utc_date": "2025-10-09",
    }
    entry_ref = {
        "agg_trade_id": 101,
        "physical_row": 2,
        "price": "1.0000",
        "time_ms": 1760000063500,
        "utc_date": "2025-10-09",
    }
    end_ref = {
        "agg_trade_id": 102,
        "physical_row": 3,
        "price": "1.3000",
        "time_ms": 1760000899500,
        "utc_date": "2025-10-09",
    }

    for i in range(281):
        pid = f"{i + 1:032x}"
        sym = f"SYM{i:03d}USDT"
        if i < 71:
            reg = "pre_market" if i < 10 else "standard"
            u_row = {
                "asset_class": "crypto",
                "classification_status": "confirmed",
                "in_scope": True,
                "listing_regime": reg,
                "parent_article_id": pid,
                "symbol": sym,
            }
            universe_rows.append(u_row)
            if i == 0:
                # 1 complete child pair
                child_rows.append(
                    {
                        "direction": "long",
                        "endpoint": dict(end_ref),
                        "entry": dict(entry_ref),
                        "first_touch": "target",
                        "listing_regime": reg,
                        "mae_bps": "0/1",
                        "mae_trade": dict(entry_ref),
                        "max_intertrade_gap_ms": 836000,
                        "mfe_bps": "3000/1",
                        "mfe_trade": dict(end_ref),
                        "parent_article_id": pid,
                        "state": "complete",
                        "symbol": sym,
                        "t0": dict(t0_ref),
                        "terminal_bps": "3000/1",
                        "touch_trade": dict(end_ref),
                    }
                )
                child_rows.append(
                    {
                        "direction": "short",
                        "endpoint": dict(end_ref),
                        "entry": dict(entry_ref),
                        "first_touch": "risk",
                        "listing_regime": reg,
                        "mae_bps": "-3000/1",
                        "mae_trade": dict(end_ref),
                        "max_intertrade_gap_ms": 836000,
                        "mfe_bps": "0/1",
                        "mfe_trade": dict(entry_ref),
                        "parent_article_id": pid,
                        "state": "complete",
                        "symbol": sym,
                        "t0": dict(t0_ref),
                        "terminal_bps": "-3000/1",
                        "touch_trade": dict(end_ref),
                    }
                )
            else:
                for d_name in ("long", "short"):
                    child_rows.append(
                        {
                            "direction": d_name,
                            "endpoint": None,
                            "entry": None,
                            "first_touch": "unavailable",
                            "listing_regime": reg,
                            "mae_bps": None,
                            "mae_trade": None,
                            "max_intertrade_gap_ms": None,
                            "mfe_bps": None,
                            "mfe_trade": None,
                            "parent_article_id": pid,
                            "state": "entry_unavailable",
                            "symbol": sym,
                            "t0": dict(t0_ref),
                            "terminal_bps": None,
                            "touch_trade": None,
                        }
                    )
        else:
            universe_rows.append(
                {
                    "asset_class": "equity",
                    "classification_status": "confirmed",
                    "in_scope": False,
                    "listing_regime": "standard",
                    "parent_article_id": pid,
                    "symbol": sym,
                }
            )

    parent_rows, group_rows = _test_compute_parents_and_groups(child_rows)
    permissions_obj = {k: False for k in sorted(FIXTURE_PERMISSIONS_EXACT_KEYS)}
    summary_obj = {
        "analysis_state": "time_path_evidence_gap",
        "artifact_kind": artifact_kind,
        "authority": authority_obj,
        "child_rows": child_rows,
        "group_rows": group_rows,
        "parent_rows": parent_rows,
        "permissions": permissions_obj,
        "profile_contract_version": FIXTURE_PROFILE_CONTRACT_VERSION,
        "profile_id": FIXTURE_PROFILE_ID,
        "protocol": dict(FIXTURE_EXPECTED_PROTOCOL_OBJECT),
        "run_id": run_id,
        "universe_rows": universe_rows,
    }
    review_str = _test_render_review(summary_obj)
    summary_bytes = _dump_canonical_json(summary_obj)
    review_bytes = review_str.encode("utf-8")
    manifest_obj = {
        "artifact_kind": artifact_kind,
        "files": [
            {
                "relative_path": "review_CN.md",
                "sha256": _sha256_bytes(review_bytes),
                "size_bytes": len(review_bytes),
            },
            {
                "relative_path": "summary.json",
                "sha256": _sha256_bytes(summary_bytes),
                "size_bytes": len(summary_bytes),
            },
        ],
        "profile_contract_version": FIXTURE_PROFILE_CONTRACT_VERSION,
        "profile_id": FIXTURE_PROFILE_ID,
        "run_id": run_id,
    }
    return manifest_obj, summary_obj, review_str, schema_unit_evidence


def _build_valid_canonical_shaped_receipt_dicts(
    *,
    run_id: str = "stage1_5j_c_launch_time_path_feasibility_20261024T150000Z",
    artifact_kind: str = "validation_only",
) -> tuple[dict[str, Any], dict[str, Any], str]:
    m, s, r, _ = _build_schema_unit_receipt_dicts(
        run_id=run_id, artifact_kind=artifact_kind
    )
    return m, s, r


def _write_receipt_bundle(
    root_dir: Path,
    manifest_obj: dict[str, Any],
    summary_obj: dict[str, Any],
    review_str: str,
    *,
    recompute_manifest_seals: bool = True,
) -> Path:
    if root_dir.is_absolute():
        root_dir = root_dir.resolve()
    root_dir.mkdir(parents=True, exist_ok=True)
    summary_bytes = _dump_canonical_json(summary_obj)
    review_bytes = review_str.encode("utf-8")
    if recompute_manifest_seals:
        manifest_obj = copy.deepcopy(manifest_obj)
        manifest_obj["files"] = [
            {
                "relative_path": "review_CN.md",
                "sha256": _sha256_bytes(review_bytes),
                "size_bytes": len(review_bytes),
            },
            {
                "relative_path": "summary.json",
                "sha256": _sha256_bytes(summary_bytes),
                "size_bytes": len(summary_bytes),
            },
        ]
    manifest_bytes = _dump_canonical_json(manifest_obj)
    (root_dir / "manifest.json").write_bytes(manifest_bytes)
    (root_dir / "summary.json").write_bytes(summary_bytes)
    (root_dir / "review_CN.md").write_bytes(review_bytes)
    return root_dir


def test_verifier_stdlib_isolation_and_no_git_authority_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove standalone Rule 17 verifier imports only stdlib and never reads .git authority files."""
    from scripts.governance import verify_stage1_5j_c_receipt_schema as verifier

    source = VERIFIER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_prefixes = ("src", "research", "configs", "scripts", "tests", "subprocess", "importlib", "runpy")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(forbidden_prefixes), f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert not mod.startswith(forbidden_prefixes), f"Forbidden from-import: {mod}"

    # Verify this test file does not call any private verifier helper
    test_source = Path(__file__).read_text(encoding="utf-8")
    test_tree = ast.parse(test_source)
    for node in ast.walk(test_tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "verifier"
        ):
            assert node.attr == "main", (
                f"Test accesses verifier attribute other than main: verifier.{node.attr}"
            )

    run_id = "stage1_5j_c_launch_time_path_feasibility_20261024T150000Z"
    manifest_obj, summary_obj, review_str, evidence = _build_schema_unit_receipt_dicts(
        run_id=run_id, artifact_kind="validation_only"
    )
    assert evidence["tier"] == "schema_unit_only"
    assert evidence["provenance_claim"] is False
    assert evidence["semantic_claim"] is False
    assert evidence["source_backed_claim"] is False

    root_dir = _write_receipt_bundle(
        tmp_path / run_id, manifest_obj, summary_obj, review_str
    )

    orig_read_bytes = Path.read_bytes

    def _sentinel_read_bytes(self: Path) -> bytes:
        s = str(self)
        if ".git" in s or "user_receipt_generation_approval" in s or "authorization_release" in s:
            raise AssertionError(f"Verifier attempted to read external authority file: {s}")
        return orig_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", _sentinel_read_bytes)

    rc = verifier.main(
        ["--profile", "stage1_5j_c_time_path_v1", "--artifact-root", str(root_dir)]
    )
    assert rc == 0


def test_verifier_positive_validation_and_production_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify RC=0 for both absolute validation_only root and relative production_diagnostic root."""
    from scripts.governance import verify_stage1_5j_c_receipt_schema as verifier

    run_id = "stage1_5j_c_launch_time_path_feasibility_20261024T150100Z"

    # 1. Absolute validation_only root
    m_val, s_val, r_val = _build_valid_canonical_shaped_receipt_dicts(
        run_id=run_id, artifact_kind="validation_only"
    )
    val_root = _write_receipt_bundle(tmp_path / "val" / run_id, m_val, s_val, r_val)
    assert (
        verifier.main(
            ["--profile", "stage1_5j_c_time_path_v1", "--artifact-root", str(val_root)]
        )
        == 0
    )

    # 2. Relative production_diagnostic root
    m_prod, s_prod, r_prod = _build_valid_canonical_shaped_receipt_dicts(
        run_id=run_id, artifact_kind="production_diagnostic"
    )
    rel_prod_str = f"data/external_signal_shadow/stage1_5j_c/launch_time_path_feasibility/{run_id}"
    prod_root = _write_receipt_bundle(tmp_path / "repo" / rel_prod_str, m_prod, s_prod, r_prod)
    assert prod_root.is_dir()
    monkeypatch.chdir((tmp_path / "repo").resolve())
    assert (
        verifier.main(
            ["--profile", "stage1_5j_c_time_path_v1", "--artifact-root", rel_prod_str]
        )
        == 0
    )


def test_verifier_complete_negative_mutation_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify all 6 rows of the Plan Task 4 negative mutation matrix fail closed with RC=1."""
    from scripts.governance import verify_stage1_5j_c_receipt_schema as verifier

    run_id = "stage1_5j_c_launch_time_path_feasibility_20261024T150200Z"
    base_m, base_s, base_r, evidence = _build_schema_unit_receipt_dicts(
        run_id=run_id, artifact_kind="validation_only"
    )
    assert evidence["tier"] == "schema_unit_only"
    assert evidence["provenance_claim"] is False

    case_idx = 0

    def _run_mutated_bundle(
        m_obj: dict[str, Any],
        s_obj: dict[str, Any],
        r_str: str | None = None,
        *,
        recompute_seals: bool = True,
    ) -> int:
        nonlocal case_idx
        case_idx += 1
        rev = r_str if r_str is not None else _test_render_review(s_obj)
        r_dir = _write_receipt_bundle(
            tmp_path / f"mut_{case_idx}" / run_id,
            m_obj,
            s_obj,
            rev,
            recompute_manifest_seals=recompute_seals,
        )
        return verifier.main(
            ["--profile", "stage1_5j_c_time_path_v1", "--artifact-root", str(r_dir)]
        )

    # --- Row 1: profile/root/tree ---
    # 1a. Wrong profile_id in summary
    s = copy.deepcopy(base_s)
    s["profile_id"] = "wrong_profile"
    assert _run_mutated_bundle(base_m, s) == 1

    # 1b. Wrong artifact_kind / root pairing (absolute path with production_diagnostic)
    m_p, s_p, r_p = _build_valid_canonical_shaped_receipt_dicts(
        run_id=run_id, artifact_kind="production_diagnostic"
    )
    abs_prod = _write_receipt_bundle(tmp_path / "abs_prod" / run_id, m_p, s_p, r_p)
    assert (
        verifier.main(
            ["--profile", "stage1_5j_c_time_path_v1", "--artifact-root", str(abs_prod)]
        )
        == 1
    )

    # 1c. Relative path with validation_only
    _write_receipt_bundle(tmp_path / "rel_val" / run_id, base_m, base_s, base_r)
    monkeypatch.chdir((tmp_path / "rel_val").resolve())
    assert (
        verifier.main(
            ["--profile", "stage1_5j_c_time_path_v1", "--artifact-root", run_id]
        )
        == 1
    )
    monkeypatch.chdir(PROJECT_ROOT)

    # 1d. Extra file in sealed tree
    r_extra = _write_receipt_bundle(tmp_path / "extra" / run_id, base_m, base_s, base_r)
    (r_extra / "summary.json.sha256").write_text("0" * 64 + "  summary.json\n", encoding="utf-8")
    assert (
        verifier.main(
            ["--profile", "stage1_5j_c_time_path_v1", "--artifact-root", str(r_extra)]
        )
        == 1
    )

    # 1e. Symlink on artifact root
    r_sym_target = _write_receipt_bundle(tmp_path / "sym_target" / run_id, base_m, base_s, base_r)
    r_sym_link = tmp_path / "sym_link" / run_id
    r_sym_link.parent.mkdir(parents=True, exist_ok=True)
    r_sym_link.symlink_to(r_sym_target)
    assert (
        verifier.main(
            ["--profile", "stage1_5j_c_time_path_v1", "--artifact-root", str(r_sym_link)]
        )
        == 1
    )

    # 1f. Duplicate key in JSON
    r_dup = _write_receipt_bundle(tmp_path / "dup_json" / run_id, base_m, base_s, base_r)
    (r_dup / "manifest.json").write_text(
        '{"artifact_kind":"validation_only","artifact_kind":"validation_only","files":[],"profile_contract_version":1,"profile_id":"stage1_5j_c_time_path_v1","run_id":"'
        + run_id
        + '"}\n',
        encoding="utf-8",
    )
    assert (
        verifier.main(
            ["--profile", "stage1_5j_c_time_path_v1", "--artifact-root", str(r_dup)]
        )
        == 1
    )

    # --- Row 2: receipt-local authority/protocol/permissions ---
    # 2a. Wrong Design SHA
    s = copy.deepcopy(base_s)
    s["authority"]["design"]["sha256"] = "0" * 64
    assert _run_mutated_bundle(base_m, s) == 1

    # 2b. Malformed embedded seal (path escape '..')
    s = copy.deepcopy(base_s)
    s["authority"]["run_authorization"]["relative_path"] = "../escape.json"
    assert _run_mutated_bundle(base_m, s) == 1

    # 2c. Altered protocol value
    s = copy.deepcopy(base_s)
    s["protocol"]["target_bps"] = 2500
    assert _run_mutated_bundle(base_m, s) == 1

    # 2d. True permission
    s = copy.deepcopy(base_s)
    s["permissions"]["alpha_claim_allowed"] = True
    assert _run_mutated_bundle(base_m, s) == 1

    # --- Row 3: source/input identity sets ---
    # 3a. Missing source file (10 instead of 11)
    s = copy.deepcopy(base_s)
    s["authority"]["source_files"] = s["authority"]["source_files"][:-1]
    assert _run_mutated_bundle(base_m, s) == 1

    # 3b. Unsorted input_files
    s = copy.deepcopy(base_s)
    s["authority"]["input_files"] = list(reversed(s["authority"]["input_files"]))
    assert _run_mutated_bundle(base_m, s) == 1

    # 3c. Wrong frozen SHA on input_files
    s = copy.deepcopy(base_s)
    s["authority"]["input_files"][0]["sha256"] = "f" * 64
    assert _run_mutated_bundle(base_m, s) == 1

    # --- Row 4: universe/child conditional contract ---
    # 4a. Duplicate universe key
    s = copy.deepcopy(base_s)
    s["universe_rows"][1] = copy.deepcopy(s["universe_rows"][0])
    assert _run_mutated_bundle(base_m, s) == 1

    # 4b. Gap child with fabricated mfe_bps
    s = copy.deepcopy(base_s)
    s["child_rows"][2]["mfe_bps"] = "100/1"
    assert _run_mutated_bundle(base_m, s) == 1

    # 4c. Complete child with null terminal_bps
    s = copy.deepcopy(base_s)
    s["child_rows"][0]["terminal_bps"] = None
    assert _run_mutated_bundle(base_m, s) == 1

    # 4d. Complete child with first_touch='target' but touch_trade=None
    s = copy.deepcopy(base_s)
    s["child_rows"][0]["touch_trade"] = None
    assert _run_mutated_bundle(base_m, s) == 1

    # --- Row 5: Parent/Group projection contract ---
    # 5a. Incomplete Parent with non-null mfe_bps
    s = copy.deepcopy(base_s)
    s["parent_rows"][2]["mfe_bps"] = "500/1"
    assert _run_mutated_bundle(base_m, s) == 1

    # 5b. Wrong Parent median mfe_bps on complete Parent
    s = copy.deepcopy(base_s)
    s["parent_rows"][0]["mfe_bps"] = "2999/1"
    assert _run_mutated_bundle(base_m, s) == 1

    # 5c. Wrong Group cost_bps list
    s = copy.deepcopy(base_s)
    s["group_rows"][0]["costs"][1]["cost_bps"] = 90
    assert _run_mutated_bundle(base_m, s) == 1

    # 5d. Malformed unreduced fraction string
    s = copy.deepcopy(base_s)
    s["child_rows"][0]["mfe_bps"] = "6000/2"
    assert _run_mutated_bundle(base_m, s) == 1

    # --- Row 6: review projection ---
    # 6a. Review text mutated even when manifest seal is updated
    bad_rev = base_r.replace("universe_children: 281", "universe_children: 280")
    assert _run_mutated_bundle(base_m, base_s, bad_rev, recompute_seals=True) == 1

    # 6b. Manifest hash mismatch for summary.json
    bad_m = copy.deepcopy(base_m)
    bad_m["files"][1]["sha256"] = "0" * 64
    assert _run_mutated_bundle(bad_m, base_s, base_r, recompute_seals=False) == 1
