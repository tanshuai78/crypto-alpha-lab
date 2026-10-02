from __future__ import annotations

import copy
import fcntl
import hashlib
import importlib
import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any


class Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(Exception):
    pass


APPROVED_DESIGN_REL_PATH: str = (
    "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-design_CN.md"
)
APPROVED_DESIGN_SHA256: str = (
    "416b394bf809e1dcc159f9d39ecd175b57962022434d09478f5e0d97fa5a9276"
)
APPROVED_PLAN_REL_PATH: str = (
    "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-implementation-plan_CN.md"
)
APPROVED_PLAN_SHA256: str = (
    "7a1e8a5a2b0f803677bb9342d5167b8a2ec8d9458dc3c7cf8abf543c4ec53ceb"
)
CROSS_ROOT_ROOT_REL: str = (
    "data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z"
)
CROSS_ROOT_MANIFEST_SHA256: str = (
    "a3b9a45d3c4fbed9ed1136add956a0d0266236298f9be4b754d11134feb65467"
)
CROSS_ROOT_SUMMARY_SHA256: str = (
    "9f45b4c184f4cb3d76944eb3e5bef51af3cd7a3277028196e0fb84eb293516c0"
)

OUTPUT_PARENT_REL: str = "data/external_signal_shadow/stage1_5h/v3_cross_root_friction"

_RUN_ID_REGEX = re.compile(r"^stage1_5h_v3_cross_root_friction_[0-9]{8}T[0-9]{6}Z$")

FROZEN_UPSTREAM_CONTRACT: dict[str, str] = {
    "src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py": "b6a1c9f1348985a7407d41b67b240656faac84cb0e362e7191a2731a2f098570",
    "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py": "596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d",
    "configs/base.py": "414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4",
    "src/research/external_signal_shadow/safety.py": "1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d",
}

UPSTREAM_MODULE_REL_PATHS: dict[str, str] = {
    "src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission": "src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py",
    "src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review": "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py",
    "configs.base": "configs/base.py",
    "src.research.external_signal_shadow.safety": "src/research/external_signal_shadow/safety.py",
}

EXPECTED_13_FALSE_FLAGS: dict[str, bool] = {
    "alpha_interpretation_allowed": False,
    "commit_allowed": False,
    "deployment_allowed": False,
    "event_family_conclusion_allowed": False,
    "execution_engine_allowed": False,
    "execution_feasibility_claim_allowed": False,
    "live_trading_allowed": False,
    "network_collection_allowed": False,
    "paper_trading_allowed": False,
    "push_allowed": False,
    "replay_allowed": False,
    "ssh_allowed": False,
    "trade_signal_allowed": False,
}

FROZEN_INPUT_RECORDS: list[dict[str, Any]] = [
    {
        "input_key": "moonshot",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot",
        "source_manifest_sha256": "611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db",
        "expected_parent_article_id": "7379b99aa0f349a49c3b3feca1b4bbd6",
        "expected_parent_event_id": "e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5",
        "expected_symbols": ["MOONSHOTUSDT"],
    },
    {
        "input_key": "batch7",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7",
        "source_manifest_sha256": "0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280",
        "expected_parent_article_id": "0c6ea14ba89b451db6ec9ec364045d22",
        "expected_parent_event_id": "d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0",
        "expected_symbols": ["ACNUSDT", "BWETUSDT", "CRMLUSDT", "MPUSDT", "NKEUSDT", "SECZUSDT", "UNHUSDT"],
    },
]

ALLOWED_QUALITY_METRIC_KEYS: tuple[str, ...] = (
    "buy_slippage_bps_500usdt_p50",
    "buy_slippage_bps_500usdt_p95",
    "depth_capacity_ratio_to_risk_cap_p50",
    "healthy_window_ratio",
    "sell_slippage_bps_500usdt_p50",
    "sell_slippage_bps_500usdt_p95",
    "spread_bps_p50",
    "spread_bps_p95",
    "sum_of_marginal_p95_slippage_bps",
    "top_ask_depth_usdt_p05",
    "top_ask_depth_usdt_p50",
    "top_bid_depth_usdt_p05",
    "top_bid_depth_usdt_p50",
)

PER_SYMBOL_ROW_KEYS: tuple[str, ...] = (
    "book_availability_ratio",
    "buy_slippage_bps_500usdt_p50",
    "buy_slippage_bps_500usdt_p95",
    "depth_capacity_ratio_to_risk_cap_p50",
    "event_id",
    "event_symbol_id",
    "healthy_window_ratio",
    "input_key",
    "invalid_book_row_count",
    "sell_slippage_bps_500usdt_p50",
    "sell_slippage_bps_500usdt_p95",
    "source_article_id",
    "spread_bps_p50",
    "spread_bps_p95",
    "sum_of_marginal_p95_slippage_bps",
    "symbol",
    "top_ask_depth_usdt_p05",
    "top_ask_depth_usdt_p50",
    "top_bid_depth_usdt_p05",
    "top_bid_depth_usdt_p50",
    "valid_snapshot_count_after_quarantine",
)

SUMMARY_KEYS: tuple[str, ...] = (
    "authority_flags",
    "cohort_summary",
    "decision",
    "input_receipt_manifest_sha256",
    "input_receipt_summary_sha256",
    "input_source_roots",
    "parent_rows",
    "per_symbol_rows",
    "research_classification",
    "run_id",
    "schema_version",
    "stage1_5g_gate3_complete",
)

MANIFEST_KEYS: tuple[str, ...] = (
    "artifacts",
    "input_receipt_manifest_sha256",
    "input_receipt_summary_sha256",
    "run_id",
    "schema_version",
)

_CACHED_UPSTREAM_MODULES: dict[str, Any] = {}
_FAILPOINT_HOOK: Any = None


def _project_root_from_core_file() -> Path:
    return Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_execution_authority(
    execution_baseline_dir: Path | str,
    supplied_approval_bindings: dict[str, str],
    project_root: Path | None = None,
) -> dict[str, Any]:
    root = (project_root or _project_root_from_core_file()).resolve()
    bundle = Path(execution_baseline_dir).resolve()

    if bundle.is_symlink() or not bundle.is_dir():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:invalid_baseline_dir"
        )

    auth_json = bundle / "execution_authority.json"
    auth_sha_file = bundle / "execution_authority.json.sha256"
    if not auth_sha_file.is_file() and (bundle / "execution_authority.sha256").is_file():
        auth_sha_file = bundle / "execution_authority.sha256"

    ledger_jsonl = bundle / "preexisting_path_ledger.jsonl"
    ledger_sha_file = bundle / "preexisting_path_ledger.sha256"
    if not ledger_sha_file.is_file() and (bundle / "preexisting_path_ledger.jsonl.sha256").is_file():
        ledger_sha_file = bundle / "preexisting_path_ledger.jsonl.sha256"

    impl_auth_txt = bundle / "implementation_authorization.txt"
    impl_auth_sha = bundle / "implementation_authorization.txt.sha256"
    if not impl_auth_sha.is_file() and (bundle / "implementation_authorization.sha256").is_file():
        impl_auth_sha = bundle / "implementation_authorization.sha256"

    for p in (auth_json, auth_sha_file, ledger_jsonl, ledger_sha_file, impl_auth_txt, impl_auth_sha):
        if p.is_symlink() or not p.is_file():
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                "STOP=approved_authority_mismatch:missing_authority_record"
            )

    if _sha256(auth_json) != auth_sha_file.read_text(encoding="utf-8").strip():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:auth_sha_mismatch"
        )

    if _sha256(ledger_jsonl) != ledger_sha_file.read_text(encoding="utf-8").strip():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:ledger_sha_mismatch"
        )

    if _sha256(impl_auth_txt) != impl_auth_sha.read_text(encoding="utf-8").strip():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:impl_auth_sha_mismatch"
        )

    auth_lines = impl_auth_txt.read_text(encoding="utf-8").splitlines()
    if len(auth_lines) != 2:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:impl_auth_syntax_line_count"
        )
    m = re.match(r"^我批准实施 Plan：(.+)（SHA-256: ([0-9a-f]{64})）。$", auth_lines[0].strip())
    if not m:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:impl_auth_syntax_line1"
        )
    parsed_plan_path, parsed_plan_sha = m.group(1), m.group(2)
    expected_line2 = "允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。"
    if auth_lines[1].strip() != expected_line2:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:impl_auth_syntax_line2"
        )
    if parsed_plan_path != APPROVED_PLAN_REL_PATH or parsed_plan_sha != APPROVED_PLAN_SHA256:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:impl_auth_plan_mismatch"
        )

    try:
        authority = json.loads(auth_json.read_text(encoding="utf-8"))
    except Exception as exc:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:auth_json_unreadable"
        ) from exc

    required_keys = {
        "project_root",
        "base_sha",
        "approved_design_path",
        "approved_design_sha256",
        "approved_plan_path",
        "approved_plan_sha256",
        "current_plan_sha256",
    }
    if set(authority.keys()) != required_keys:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:authority_keys_mismatch"
        )

    if authority["project_root"] != str(root):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=approved_authority_mismatch:project_root_mismatch:{authority['project_root']}"
        )

    if authority["approved_design_path"] != APPROVED_DESIGN_REL_PATH:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=approved_authority_mismatch:approved_design_path_mismatch:{authority['approved_design_path']}"
        )

    if authority["approved_plan_path"] != APPROVED_PLAN_REL_PATH:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=approved_authority_mismatch:approved_plan_path_mismatch:{authority['approved_plan_path']}"
        )

    if authority["current_plan_sha256"] != authority["approved_plan_sha256"]:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:current_plan_sha_not_equal_to_approved_plan_sha"
        )

    try:
        head_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(root)
        ).decode().strip()
    except Exception as exc:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:git_rev_parse_failed"
        ) from exc

    if authority["base_sha"] != head_sha:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=approved_authority_mismatch:base_sha_mismatch:{authority['base_sha']}_vs_{head_sha}"
        )

    for k in (
        "approved_design_path",
        "approved_design_sha256",
        "approved_plan_path",
        "approved_plan_sha256",
    ):
        supplied_val = supplied_approval_bindings.get(k)
        if supplied_val != authority[k]:
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=approved_authority_mismatch:{k}_mismatch"
            )

    # Verify actual Design and Plan files exist and match hashes
    design_file = root / APPROVED_DESIGN_REL_PATH
    plan_file = root / APPROVED_PLAN_REL_PATH
    for f in (design_file, plan_file):
        if f.is_symlink() or not f.is_file():
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                "STOP=approved_authority_mismatch:design_or_plan_not_regular_file"
            )

    if _sha256(design_file) != APPROVED_DESIGN_SHA256:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:design_file_sha_mismatch"
        )

    if _sha256(plan_file) != APPROVED_PLAN_SHA256:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=approved_authority_mismatch:plan_file_sha_mismatch"
        )

    return authority


def verify_frozen_upstream_contract(project_root: Path | None = None) -> dict[str, str]:
    root = (project_root or _project_root_from_core_file()).resolve()
    hashes: dict[str, str] = {}
    for rel_path, expected_hash in FROZEN_UPSTREAM_CONTRACT.items():
        file_path = root / rel_path
        if file_path.is_symlink() or not file_path.is_file():
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_upstream_contract_drift:file_not_found:{rel_path}"
            )
        actual_hash = _sha256(file_path)
        if actual_hash != expected_hash:
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_upstream_contract_drift:{rel_path}:{actual_hash}"
            )
        hashes[rel_path] = actual_hash
    return hashes


def _validate_module_binding(mod: Any, root: Path, expected_rel: str, name: str) -> None:
    mod_file = getattr(mod, "__file__", None)
    if not mod_file:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_upstream_contract_drift:module_no_file:{name}"
        )
    mod_spec = getattr(mod, "__spec__", None)
    spec_origin = getattr(mod_spec, "origin", None) if mod_spec is not None else None
    if not spec_origin:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_upstream_contract_drift:module_no_spec_origin:{name}"
        )

    raw_file = Path(mod_file)
    raw_origin = Path(spec_origin)
    if raw_file.is_symlink() or raw_origin.is_symlink():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_upstream_contract_drift:symlink_module:{name}"
        )

    file_p = raw_file.resolve()
    origin_p = raw_origin.resolve()
    expected_p = (root / expected_rel).resolve()

    if file_p != expected_p or origin_p != expected_p:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_upstream_contract_drift:path_mismatch:{name}"
        )

    expected_hash = FROZEN_UPSTREAM_CONTRACT[expected_rel]
    if _sha256(file_p) != expected_hash or _sha256(origin_p) != expected_hash:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_upstream_contract_drift:hash_mismatch:{name}"
        )


def _import_verified_upstream(project_root: Path | None = None) -> dict[str, Any]:
    global _CACHED_UPSTREAM_MODULES
    root = (project_root or _project_root_from_core_file()).resolve()
    verify_frozen_upstream_contract(project_root=root)

    for name, expected_rel in UPSTREAM_MODULE_REL_PATHS.items():
        if name in sys.modules:
            _validate_module_binding(sys.modules[name], root, expected_rel, name)

        mod = importlib.import_module(name)
        _validate_module_binding(mod, root, expected_rel, name)
        _CACHED_UPSTREAM_MODULES[name] = mod

    return _CACHED_UPSTREAM_MODULES


def compare_quality_projections(
    stored_projection: dict[str, Any], recomputed_projection: dict[str, Any]
) -> None:
    for k in (
        "spread_bps_p50",
        "spread_bps_p95",
        "buy_slippage_bps_500usdt_p50",
        "buy_slippage_bps_500usdt_p95",
        "sell_slippage_bps_500usdt_p50",
        "sell_slippage_bps_500usdt_p95",
        "top_bid_depth_usdt_p05",
        "top_bid_depth_usdt_p50",
        "top_ask_depth_usdt_p05",
        "top_ask_depth_usdt_p50",
        "healthy_window_ratio",
        "depth_capacity_ratio_to_risk_cap_p50",
    ):
        v1 = stored_projection.get(k)
        v2 = recomputed_projection.get(k)
        if v1 is None or v2 is None:
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_quality_projection_mismatch:missing_metric:{k}"
            )
        if float(v1) != float(v2):
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_quality_projection_mismatch:{k}:{v1}_vs_{v2}"
            )

    for k in (
        "valid_snapshot_count_after_quarantine",
        "invalid_book_row_count",
        "book_availability_ratio",
    ):
        if k in stored_projection and k in recomputed_projection:
            if stored_projection[k] != recomputed_projection[k]:
                raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                    f"STOP=stage1_5h_v3_quality_projection_mismatch:context_{k}"
                )


def admit_frozen_cross_root_inputs(project_root: Path | None = None) -> list[dict[str, Any]]:
    root = (project_root or _project_root_from_core_file()).resolve()
    modules = _import_verified_upstream(project_root=root)

    load_stage1_5g_inputs = modules[
        "src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review"
    ].load_stage1_5g_inputs
    build_stage1_5g_review_summary = modules[
        "src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review"
    ].build_stage1_5g_review_summary

    admitted_results: list[dict[str, Any]] = []

    for item in FROZEN_INPUT_RECORDS:
        key = item["input_key"]
        stored_path = root / item["stored_summary_path"]
        source_root = root / item["source_root_path"]

        if stored_path.is_symlink() or not stored_path.is_file():
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_cross_root_authority_mismatch:stored_summary_missing:{key}"
            )
        if _sha256(stored_path) != item["stored_summary_sha256"]:
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_cross_root_authority_mismatch:stored_summary_sha_mismatch:{key}"
            )

        manifest_file = source_root / "SHA256SUMS"
        if manifest_file.is_symlink() or not manifest_file.is_file():
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_cross_root_authority_mismatch:source_manifest_missing:{key}"
            )
        if _sha256(manifest_file) != item["source_manifest_sha256"]:
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_cross_root_authority_mismatch:source_manifest_sha_mismatch:{key}"
            )

        stored_summary = json.loads(stored_path.read_text(encoding="utf-8"))

        loaded_bundle = load_stage1_5g_inputs(source_root)
        if getattr(loaded_bundle, "loader_blockers", None):
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_cross_root_authority_mismatch:upstream_loader_blocked:{key}"
            )

        recomputed_summary = build_stage1_5g_review_summary(
            summary=loaded_bundle.summary,
            watermark=loaded_bundle.watermark,
            states=loaded_bundle.states,
            accepted_events=loaded_bundle.accepted_events,
            snapshots=loaded_bundle.snapshots,
            request_manifest_rows=loaded_bundle.request_manifest_rows,
            output_root=source_root,
            loader_blockers=loaded_bundle.loader_blockers,
        )

        if (
            recomputed_summary.get("schema_version") != 2
            or recomputed_summary.get("decision") != "stage1_5g_depth_evidence_clean_pass"
            or recomputed_summary.get("clean_depth_evidence_pass") is not True
            or recomputed_summary.get("quarantined_depth_evidence_pass") is not False
            or recomputed_summary.get("blockers") != []
        ):
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_cross_root_authority_mismatch:upstream_recomputed_not_clean_pass:{key}"
            )

        # Extract quality metrics per symbol
        stored_quar = stored_summary.get("quarantine", {}).get("per_symbol_quarantine_metrics", {})
        recomp_quar = recomputed_summary.get("quarantine", {}).get("per_symbol_quarantine_metrics", {})

        stored_quality: dict[str, Any] = {}
        recomputed_quality: dict[str, Any] = {}
        child_records: list[dict[str, Any]] = []

        elds = recomputed_summary.get("event_level_decisions", [])
        formal_children = []
        for eld in elds:
            if (
                eld.get("evidence_label") == "announcement_and_launch_time"
                and eld.get("state_status") == "completed"
                and eld.get("formal_completed") is True
            ):
                formal_children.append(eld)

        for child in formal_children:
            sym_id = child["event_symbol_id"]
            if sym_id not in stored_quar or sym_id not in recomp_quar:
                raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                    f"STOP=stage1_5h_v3_cross_root_authority_mismatch:symbol_missing_in_quarantine:{sym_id}"
                )

            st_met = stored_quar[sym_id]["quarantined_depth_quality"]
            rc_met = recomp_quar[sym_id]["quarantined_depth_quality"]

            compare_quality_projections(st_met, rc_met)

            # Store quality projection + context fields
            st_dict = dict(st_met)
            rc_dict = dict(rc_met)
            for c_key in (
                "valid_snapshot_count_after_quarantine",
                "invalid_book_row_count",
                "book_availability_ratio",
            ):
                st_dict[c_key] = stored_quar[sym_id][c_key]
                rc_dict[c_key] = recomp_quar[sym_id][c_key]

            stored_quality[sym_id] = st_dict
            recomputed_quality[sym_id] = rc_dict

            child_records.append({
                "event_id": child["event_id"],
                "event_symbol_id": sym_id,
                "evidence_label": child["evidence_label"],
                "formal_completed": child["formal_completed"],
                "source_article_id": child["source_article_id"],
                "state_status": child["state_status"],
                "symbol": child["symbol"],
            })

        admitted_results.append({
            "input_key": key,
            "input_records": child_records,
            "recomputed_formal_projection": {
                "formal_children": child_records,
                "formal_completed_event_symbol_ids_sha256": hashlib.sha256(
                    "".join(sorted(c["event_symbol_id"] for c in child_records)).encode("utf-8")
                ).hexdigest(),
            },
            "stored_summary_path": item["stored_summary_path"],
            "stored_summary_sha256": item["stored_summary_sha256"],
            "source_root_path": item["source_root_path"],
            "source_manifest_sha256": item["source_manifest_sha256"],
            "formal_completed_event_symbol_ids": [c["event_symbol_id"] for c in child_records],
            "stored_per_symbol_quality": stored_quality,
            "recomputed_per_symbol_quality": recomputed_quality,
        })

    return admitted_results


def validate_receipt_identity(
    receipt: dict[str, Any], admitted_inputs: list[dict[str, Any]]
) -> None:
    if len(admitted_inputs) != 2:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_cross_root_authority_mismatch:admitted_inputs_count"
        )

    receipt_summary = receipt.get("summary", receipt)
    receipt_records = receipt_summary.get("input_records")
    if not isinstance(receipt_records, list) or len(receipt_records) != 2:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_cross_root_authority_mismatch:receipt_input_records_count"
        )

    # Check total child count across admitted inputs == 8
    all_admitted_children = []
    for inp in admitted_inputs:
        children = inp.get("input_records", [])
        all_admitted_children.extend(children)
    if len(all_admitted_children) != 8:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_cross_root_authority_mismatch:admitted_children_count:{len(all_admitted_children)}"
        )

    # Check child IDs uniqueness
    child_ids = [c["event_symbol_id"] for c in all_admitted_children]
    if len(set(child_ids)) != 8:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_cross_root_authority_mismatch:duplicate_child_ids"
        )

    # Validate against frozen membership and receipt
    for idx, frozen_spec in enumerate(FROZEN_INPUT_RECORDS):
        rec_item = receipt_records[idx]
        adm_item = admitted_inputs[idx]

        if (
            rec_item.get("input_key") != frozen_spec["input_key"]
            or adm_item.get("input_key") != frozen_spec["input_key"]
        ):
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                "STOP=stage1_5h_v3_cross_root_authority_mismatch:input_key_mismatch"
            )

        if (
            rec_item.get("source_manifest_sha256") != frozen_spec["source_manifest_sha256"]
            or adm_item.get("source_manifest_sha256") != frozen_spec["source_manifest_sha256"]
            or rec_item.get("stored_summary_sha256") != frozen_spec["stored_summary_sha256"]
            or adm_item.get("stored_summary_sha256") != frozen_spec["stored_summary_sha256"]
            or rec_item.get("source_root_path") != frozen_spec["source_root_path"]
            or adm_item.get("source_root_path") != frozen_spec["source_root_path"]
            or rec_item.get("stored_summary_path") != frozen_spec["stored_summary_path"]
            or adm_item.get("stored_summary_path") != frozen_spec["stored_summary_path"]
        ):
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                "STOP=stage1_5h_v3_cross_root_authority_mismatch:input_metadata_mismatch"
            )

        adm_children = adm_item.get("input_records", [])
        if len(adm_children) != len(frozen_spec["expected_symbols"]):
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                "STOP=stage1_5h_v3_cross_root_authority_mismatch:child_symbol_count_mismatch"
            )

        for child in adm_children:
            if child["symbol"] not in frozen_spec["expected_symbols"]:
                raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                    f"STOP=stage1_5h_v3_cross_root_authority_mismatch:unexpected_symbol:{child['symbol']}"
                )
            if child["source_article_id"] != frozen_spec["expected_parent_article_id"]:
                raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                    "STOP=stage1_5h_v3_cross_root_authority_mismatch:parent_article_mismatch"
                )
            if child["event_id"] != frozen_spec["expected_parent_event_id"]:
                raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                    "STOP=stage1_5h_v3_cross_root_authority_mismatch:parent_event_mismatch"
                )


def derive_cross_root_friction_summary(
    admitted_inputs: list[dict[str, Any]], run_id: str, receipt: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(run_id, str) or not _RUN_ID_REGEX.match(run_id):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_cross_root_authority_mismatch:invalid_run_id:{run_id}"
        )

    validate_receipt_identity(receipt, admitted_inputs)

    # 1. Build per_symbol_rows
    per_symbol_rows: list[dict[str, Any]] = []
    parent_map: dict[str, list[dict[str, Any]]] = {}
    parent_article_map: dict[str, str] = {}

    for inp in admitted_inputs:
        key = inp["input_key"]
        quality_map = inp["recomputed_per_symbol_quality"]
        for child in inp["input_records"]:
            sym_id = child["event_symbol_id"]
            if sym_id not in quality_map:
                raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                    f"STOP=stage1_5h_v3_cross_root_authority_mismatch:missing_quality:{sym_id}"
                )
            q = quality_map[sym_id]

            # Validate all values finite numbers
            for m in (
                "buy_slippage_bps_500usdt_p50",
                "buy_slippage_bps_500usdt_p95",
                "depth_capacity_ratio_to_risk_cap_p50",
                "healthy_window_ratio",
                "sell_slippage_bps_500usdt_p50",
                "sell_slippage_bps_500usdt_p95",
                "spread_bps_p50",
                "spread_bps_p95",
                "top_ask_depth_usdt_p05",
                "top_ask_depth_usdt_p50",
                "top_bid_depth_usdt_p05",
                "top_bid_depth_usdt_p50",
            ):
                val = q[m]
                if not isinstance(val, (int, float)) or type(val) is bool:
                    raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                        f"STOP=stage1_5h_v3_cross_root_authority_mismatch:non_finite_metric:{m}"
                    )

            # Derived arithmetic metric
            sum_p95 = float(q["buy_slippage_bps_500usdt_p95"]) + float(q["sell_slippage_bps_500usdt_p95"])

            row: dict[str, Any] = {
                "book_availability_ratio": float(q["book_availability_ratio"]),
                "buy_slippage_bps_500usdt_p50": float(q["buy_slippage_bps_500usdt_p50"]),
                "buy_slippage_bps_500usdt_p95": float(q["buy_slippage_bps_500usdt_p95"]),
                "depth_capacity_ratio_to_risk_cap_p50": float(q["depth_capacity_ratio_to_risk_cap_p50"]),
                "event_id": child["event_id"],
                "event_symbol_id": sym_id,
                "healthy_window_ratio": float(q["healthy_window_ratio"]),
                "input_key": key,
                "invalid_book_row_count": int(q["invalid_book_row_count"]),
                "sell_slippage_bps_500usdt_p50": float(q["sell_slippage_bps_500usdt_p50"]),
                "sell_slippage_bps_500usdt_p95": float(q["sell_slippage_bps_500usdt_p95"]),
                "source_article_id": child["source_article_id"],
                "spread_bps_p50": float(q["spread_bps_p50"]),
                "spread_bps_p95": float(q["spread_bps_p95"]),
                "sum_of_marginal_p95_slippage_bps": sum_p95,
                "symbol": child["symbol"],
                "top_ask_depth_usdt_p05": float(q["top_ask_depth_usdt_p05"]),
                "top_ask_depth_usdt_p50": float(q["top_ask_depth_usdt_p50"]),
                "top_bid_depth_usdt_p05": float(q["top_bid_depth_usdt_p05"]),
                "top_bid_depth_usdt_p50": float(q["top_bid_depth_usdt_p50"]),
                "valid_snapshot_count_after_quarantine": int(q["valid_snapshot_count_after_quarantine"]),
            }

            per_symbol_rows.append(row)

            p_id = child["event_id"]
            if p_id not in parent_map:
                parent_map[p_id] = []
                parent_article_map[p_id] = child["source_article_id"]
            parent_map[p_id].append(row)

    if len(per_symbol_rows) != 8:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_cross_root_authority_mismatch:per_symbol_rows_count:{len(per_symbol_rows)}"
        )

    # Sort per_symbol_rows canonically by event_symbol_id
    per_symbol_rows.sort(key=lambda r: r["event_symbol_id"])

    # 2. Build parent_rows
    if len(parent_map) != 2:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_cross_root_authority_mismatch:parent_event_count:{len(parent_map)}"
        )

    parent_rows: list[dict[str, Any]] = []
    parent_median_metric_dict: dict[str, dict[str, float]] = {}

    for p_id in sorted(parent_map.keys()):
        p_children = sorted(parent_map[p_id], key=lambda c: c["event_symbol_id"])
        p_article = parent_article_map[p_id]

        median_metrics: dict[str, float] = {}
        for m in ALLOWED_QUALITY_METRIC_KEYS:
            vals = [c[m] for c in p_children]
            median_metrics[m] = float(statistics.median(vals))

        parent_median_metric_dict[p_id] = median_metrics

        parent_rows.append({
            "child_event_symbol_ids": [c["event_symbol_id"] for c in p_children],
            "child_symbol_count": len(p_children),
            "median_metrics": median_metrics,
            "parent_article_id": p_article,
            "parent_event_id": p_id,
        })

    # Sort parent_rows by parent_event_id
    parent_rows.sort(key=lambda p: p["parent_event_id"])

    # 3. Build cohort_summary
    parent_metric_ranges: dict[str, dict[str, float]] = {}
    p_ids = [p["parent_event_id"] for p in parent_rows]
    for m in ALLOWED_QUALITY_METRIC_KEYS:
        med1 = parent_median_metric_dict[p_ids[0]][m]
        med2 = parent_median_metric_dict[p_ids[1]][m]
        parent_metric_ranges[m] = {
            "parent_median_max": max(med1, med2),
            "parent_median_min": min(med1, med2),
        }

    cohort_summary = {
        "independent_parent_event_count": 2,
        "parent_event_ids": p_ids,
        "parent_metric_ranges": parent_metric_ranges,
    }

    # 4. Input source roots
    input_source_roots: list[dict[str, Any]] = []
    for inp in sorted(admitted_inputs, key=lambda x: x["input_key"]):
        input_source_roots.append({
            "input_key": inp["input_key"],
            "source_manifest_sha256": inp["source_manifest_sha256"],
            "source_root_path": inp["source_root_path"],
            "stored_summary_path": inp["stored_summary_path"],
            "stored_summary_sha256": inp["stored_summary_sha256"],
        })

    # 5. Assemble summary
    summary = {
        "authority_flags": copy.deepcopy(EXPECTED_13_FALSE_FLAGS),
        "cohort_summary": cohort_summary,
        "decision": "stage1_5h_v3_cross_root_friction_diagnostic_generated",
        "input_receipt_manifest_sha256": CROSS_ROOT_MANIFEST_SHA256,
        "input_receipt_summary_sha256": CROSS_ROOT_SUMMARY_SHA256,
        "input_source_roots": input_source_roots,
        "parent_rows": parent_rows,
        "per_symbol_rows": per_symbol_rows,
        "research_classification": "evidence_insufficient",
        "run_id": run_id,
        "schema_version": 1,
        "stage1_5g_gate3_complete": False,
    }

    return summary


def render_review(summary: dict[str, Any]) -> str:
    modules = _import_verified_upstream()
    canonical_json_dumps = modules["src.research.external_signal_shadow.safety"].canonical_json_dumps

    run_id = summary["run_id"]
    authority_flags_json = canonical_json_dumps(summary["authority_flags"])

    input_lineage = {
        "input_receipt_manifest_sha256": summary["input_receipt_manifest_sha256"],
        "input_receipt_summary_sha256": summary["input_receipt_summary_sha256"],
        "input_source_roots": summary["input_source_roots"],
    }
    input_lineage_json = canonical_json_dumps(input_lineage)
    per_symbol_rows_json = canonical_json_dumps(summary["per_symbol_rows"])
    parent_rows_json = canonical_json_dumps(summary["parent_rows"])
    cohort_summary_json = canonical_json_dumps(summary["cohort_summary"])

    template = f"""# Stage 1.5H V3 Cross-Root Liquidity Friction Diagnostic Review

## Scope

- `run_id`: `{run_id}`
- `decision`: `stage1_5h_v3_cross_root_friction_diagnostic_generated`
- `research_classification`: `evidence_insufficient`
- `stage1_5g_gate3_complete`: `false`
- 本报告仅为冻结 L2 quality metrics 的描述性投影；不构成 phenomenon、Alpha、strategy 或 execution-feasibility evidence。

## Authority Flags

```json
{authority_flags_json}
```

## Input Lineage

```json
{input_lineage_json}
```

## Per-Symbol Rows

```json
{per_symbol_rows_json}
```

## Parent Rows

```json
{parent_rows_json}
```

## Cohort Summary

```json
{cohort_summary_json}
```
"""
    return template


_MACOS_SYSTEM_ROOT_SYMLINKS: set[Path] = {Path("/tmp"), Path("/var"), Path("/etc")}


def _has_symlink_components(path: Path | str) -> bool:
    curr = Path(path)
    while True:
        if curr.is_symlink() and curr not in _MACOS_SYSTEM_ROOT_SYMLINKS:
            return True
        if curr.parent == curr:
            break
        curr = curr.parent
    return False


def _assert_no_symlink_components(path: Path | str, error_tag: str) -> None:
    curr = Path(path)
    while True:
        if curr.is_symlink() and curr not in _MACOS_SYSTEM_ROOT_SYMLINKS:
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_publication_integrity_failure:{error_tag}:{curr}"
            )
        if curr.parent == curr:
            break
        curr = curr.parent


def load_verified_v3_summary(summary_path: Path | str) -> dict[str, Any]:
    modules = _import_verified_upstream()
    canonical_json_dumps = modules["src.research.external_signal_shadow.safety"].canonical_json_dumps

    raw_sum = Path(summary_path)
    _assert_no_symlink_components(raw_sum, "summary_symlink")
    sum_p = raw_sum.resolve()
    if not sum_p.is_file():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:summary_not_file"
        )

    sum_bytes = sum_p.read_bytes()
    try:
        summary = json.loads(sum_bytes.decode("utf-8"))
    except Exception as exc:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:summary_unreadable"
        ) from exc

    if canonical_json_dumps(summary).encode("utf-8") != sum_bytes:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:summary_not_canonical"
        )

    if set(summary.keys()) != set(SUMMARY_KEYS):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:summary_keys"
        )

    if (
        summary.get("schema_version") != 1
        or summary.get("decision") != "stage1_5h_v3_cross_root_friction_diagnostic_generated"
        or summary.get("research_classification") != "evidence_insufficient"
        or summary.get("stage1_5g_gate3_complete") is not False
        or type(summary.get("stage1_5g_gate3_complete")) is not bool
    ):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:summary_scalar_invariants"
        )

    if (
        summary.get("input_receipt_manifest_sha256") != CROSS_ROOT_MANIFEST_SHA256
        or summary.get("input_receipt_summary_sha256") != CROSS_ROOT_SUMMARY_SHA256
    ):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:receipt_lineage_mismatch"
        )

    if summary.get("authority_flags") != EXPECTED_13_FALSE_FLAGS:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:authority_flags_mismatch"
        )

    return summary


def load_verified_v3_review(review_path: Path | str, summary: dict[str, Any]) -> str:
    raw_rev = Path(review_path)
    _assert_no_symlink_components(raw_rev, "review_symlink")
    rev_p = raw_rev.resolve()
    if not rev_p.is_file():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:review_not_file"
        )

    actual_md = rev_p.read_text(encoding="utf-8")
    expected_md = render_review(summary)

    if actual_md != expected_md:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:review_text_mismatch"
        )

    return actual_md


def load_verified_v3_manifest(
    manifest_path: Path | str,
    expected_run_id: str,
    summary_sha256: str,
    review_sha256: str,
    expected_summary_byte_count: int | None = None,
    expected_review_byte_count: int | None = None,
) -> dict[str, Any]:
    modules = _import_verified_upstream()
    canonical_json_dumps = modules["src.research.external_signal_shadow.safety"].canonical_json_dumps

    raw_man = Path(manifest_path)
    _assert_no_symlink_components(raw_man, "manifest_symlink")
    man_p = raw_man.resolve()
    if not man_p.is_file():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:manifest_not_file"
        )

    man_bytes = man_p.read_bytes()
    try:
        manifest = json.loads(man_bytes.decode("utf-8"))
    except Exception as exc:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:manifest_unreadable"
        ) from exc

    if canonical_json_dumps(manifest).encode("utf-8") != man_bytes:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:manifest_not_canonical"
        )

    if set(manifest.keys()) != set(MANIFEST_KEYS):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:manifest_keys"
        )

    if (
        manifest.get("schema_version") != 1
        or manifest.get("run_id") != expected_run_id
        or manifest.get("input_receipt_manifest_sha256") != CROSS_ROOT_MANIFEST_SHA256
        or manifest.get("input_receipt_summary_sha256") != CROSS_ROOT_SUMMARY_SHA256
    ):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:manifest_invariants"
        )

    arts = manifest.get("artifacts")
    if not isinstance(arts, dict) or set(arts.keys()) != {"review", "summary"}:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:manifest_artifacts_keys"
        )

    expected_meta_keys = {"byte_count", "relative_path", "sha256"}
    for art_name in ("summary", "review"):
        meta = arts[art_name]
        if not isinstance(meta, dict) or set(meta.keys()) != expected_meta_keys:
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_publication_integrity_failure:manifest_artifact_meta_keys:{art_name}"
            )
        bc = meta.get("byte_count")
        if not isinstance(bc, int) or isinstance(bc, bool) or bc <= 0:
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_publication_integrity_failure:manifest_artifact_byte_count_invalid:{art_name}"
            )

    if (
        arts["summary"]["relative_path"] != "stage1_5h_v3_cross_root_friction_summary.json"
        or arts["summary"]["sha256"] != summary_sha256
        or (expected_summary_byte_count is not None and arts["summary"]["byte_count"] != expected_summary_byte_count)
        or arts["review"]["relative_path"] != "stage1_5h_v3_cross_root_friction_review_CN.md"
        or arts["review"]["sha256"] != review_sha256
        or (expected_review_byte_count is not None and arts["review"]["byte_count"] != expected_review_byte_count)
    ):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:manifest_artifact_meta_mismatch"
        )

    return manifest


def load_verified_v3_root(final_root: Path | str) -> dict[str, Any]:
    raw_root = Path(final_root)
    _assert_no_symlink_components(raw_root, "final_root_symlink")
    f_root = raw_root.resolve()
    if not f_root.is_dir():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:final_root_not_dir"
        )

    items = list(f_root.iterdir())
    item_names = {i.name for i in items}
    expected_files = {
        "stage1_5h_v3_cross_root_friction_summary.json",
        "stage1_5h_v3_cross_root_friction_review_CN.md",
        "stage1_5h_v3_cross_root_friction_manifest.json",
    }
    if item_names != expected_files:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:unlisted_files_in_root"
        )

    for item in items:
        if item.is_symlink() or not item.is_file():
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                "STOP=stage1_5h_v3_publication_integrity_failure:symlink_or_not_file"
            )

    sum_path = f_root / "stage1_5h_v3_cross_root_friction_summary.json"
    rev_path = f_root / "stage1_5h_v3_cross_root_friction_review_CN.md"
    man_path = f_root / "stage1_5h_v3_cross_root_friction_manifest.json"

    summary = load_verified_v3_summary(sum_path)
    review = load_verified_v3_review(rev_path, summary)

    sum_sha = _sha256(sum_path)
    rev_sha = _sha256(rev_path)
    sum_len = sum_path.stat().st_size
    rev_len = rev_path.stat().st_size

    manifest = load_verified_v3_manifest(
        man_path,
        expected_run_id=summary["run_id"],
        summary_sha256=sum_sha,
        review_sha256=rev_sha,
        expected_summary_byte_count=sum_len,
        expected_review_byte_count=rev_len,
    )

    return {"summary": summary, "review": review, "manifest": manifest}


def classify_v3_root_state(parent_dir: Path | str, run_id: str) -> str:
    raw_p = Path(parent_dir)
    if _has_symlink_components(raw_p):
        return "corrupt_or_unknown"
    p = raw_p.resolve()
    if not isinstance(run_id, str) or not _RUN_ID_REGEX.match(run_id):
        return "corrupt_or_unknown"

    final_root = p / run_id
    staging_pattern = re.compile(rf"^\.{re.escape(run_id)}\.staging\.[1-9][0-9]*$")
    staging_found = False
    if p.is_dir():
        for child in p.iterdir():
            if staging_pattern.match(child.name):
                staging_found = True
                break

    if not final_root.exists() and not final_root.is_symlink():
        if staging_found:
            return "staging_only"
        return "unpublished"

    if final_root.is_symlink() or not final_root.is_dir():
        return "corrupt_or_unknown"

    try:
        load_verified_v3_root(final_root)
        return "receipt_published"
    except Exception:
        return "corrupt_or_unknown"


def _publish_v3_diagnostic_to_parent(
    summary: dict[str, Any],
    run_id: str,
    parent_dir: Path,
) -> Path:
    if not isinstance(run_id, str) or not _RUN_ID_REGEX.match(run_id) or summary.get("run_id") != run_id:
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            "STOP=stage1_5h_v3_publication_integrity_failure:invalid_run_id"
        )

    _assert_no_symlink_components(parent_dir, "parent_dir_symlink")

    parent_dir.mkdir(parents=True, exist_ok=True)
    final_root = parent_dir / run_id
    if final_root.exists() or final_root.is_symlink():
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_publication_integrity_failure:final_root_preexists:{final_root}"
        )
    _assert_no_symlink_components(final_root, "final_root_symlink")

    staging_pattern = re.compile(rf"^\.{re.escape(run_id)}\.staging\.[1-9][0-9]*$")
    for child in parent_dir.iterdir():
        if staging_pattern.match(child.name):
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_publication_integrity_failure:matching_staging_sibling_preexists:{child.name}"
            )

    pid = os.getpid()
    staging_dir = parent_dir / f".{run_id}.staging.{pid}"
    staging_dir.mkdir(parents=True, exist_ok=False)

    def _trigger_failpoint(position: str) -> None:
        if _FAILPOINT_HOOK is not None:
            _FAILPOINT_HOOK(position)

    modules = _import_verified_upstream()
    canonical_json_dumps = modules["src.research.external_signal_shadow.safety"].canonical_json_dumps

    # 1. Summary
    summary_bytes = canonical_json_dumps(summary).encode("utf-8")
    tmp_sum = staging_dir / f".tmp_summary_{pid}"
    fd = os.open(str(tmp_sum), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.write(fd, summary_bytes)
    os.fsync(fd)
    os.close(fd)
    _trigger_failpoint("after_summary_write")
    os.replace(tmp_sum, staging_dir / "stage1_5h_v3_cross_root_friction_summary.json")
    _trigger_failpoint("after_summary_fsync")

    # 2. Review
    review_text = render_review(summary)
    review_bytes = review_text.encode("utf-8")
    tmp_rev = staging_dir / f".tmp_review_{pid}"
    fd = os.open(str(tmp_rev), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.write(fd, review_bytes)
    os.fsync(fd)
    os.close(fd)
    _trigger_failpoint("after_review_write")
    os.replace(tmp_rev, staging_dir / "stage1_5h_v3_cross_root_friction_review_CN.md")
    _trigger_failpoint("after_review_fsync")

    # 3. Manifest last
    manifest_payload = {
        "artifacts": {
            "review": {
                "byte_count": len(review_bytes),
                "relative_path": "stage1_5h_v3_cross_root_friction_review_CN.md",
                "sha256": hashlib.sha256(review_bytes).hexdigest(),
            },
            "summary": {
                "byte_count": len(summary_bytes),
                "relative_path": "stage1_5h_v3_cross_root_friction_summary.json",
                "sha256": hashlib.sha256(summary_bytes).hexdigest(),
            },
        },
        "input_receipt_manifest_sha256": CROSS_ROOT_MANIFEST_SHA256,
        "input_receipt_summary_sha256": CROSS_ROOT_SUMMARY_SHA256,
        "run_id": run_id,
        "schema_version": 1,
    }
    manifest_bytes = canonical_json_dumps(manifest_payload).encode("utf-8")
    tmp_man = staging_dir / f".tmp_manifest_{pid}"
    fd = os.open(str(tmp_man), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.write(fd, manifest_bytes)
    os.fsync(fd)
    os.close(fd)
    _trigger_failpoint("after_manifest_write")
    os.replace(tmp_man, staging_dir / "stage1_5h_v3_cross_root_friction_manifest.json")
    _trigger_failpoint("after_manifest_fsync")

    # Strict load staging root
    load_verified_v3_root(staging_dir)

    # Fsync staging directory
    st_fd = os.open(str(staging_dir), os.O_RDONLY)
    os.fsync(st_fd)
    os.close(st_fd)
    _trigger_failpoint("after_staging_fsync")

    # Lock parent directory, re-check, atomic replace, fsync parent
    p_fd = os.open(str(parent_dir), os.O_RDONLY)
    fcntl.flock(p_fd, fcntl.LOCK_EX)
    renamed = False
    try:
        _trigger_failpoint("before_rename")
        if final_root.exists() or final_root.is_symlink():
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                f"STOP=stage1_5h_v3_publication_integrity_failure:collision:{run_id}"
            )
        os.replace(staging_dir, final_root)
        renamed = True
        _trigger_failpoint("after_rename")
        os.fsync(p_fd)
        _trigger_failpoint("after_parent_fsync")
    except Exception as exc:
        if renamed:
            raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
                "STOP=stage1_5h_v3_post_rename_durability_failure"
            ) from exc
        raise
    finally:
        fcntl.flock(p_fd, fcntl.LOCK_UN)
        os.close(p_fd)

    # Strict load final root
    load_verified_v3_root(final_root)

    return final_root


def run_diagnostic(run_id: str, authority_packet: dict[str, Any]) -> dict[str, Any]:
    project_root = _project_root_from_core_file()
    parent_dir_raw = project_root / OUTPUT_PARENT_REL
    _assert_no_symlink_components(parent_dir_raw, "output_parent_symlink")

    parent_dir = parent_dir_raw.resolve()
    expected_parent = (project_root.resolve() / OUTPUT_PARENT_REL)
    if parent_dir != expected_parent or not parent_dir.is_relative_to(project_root.resolve()):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_publication_integrity_failure:output_parent_outside_project:{parent_dir}"
        )

    baseline_dir = authority_packet["execution_baseline_dir"]
    bindings = {
        "approved_design_path": authority_packet["approved_design_path"],
        "approved_design_sha256": authority_packet["approved_design_sha256"],
        "approved_plan_path": authority_packet["approved_plan_path"],
        "approved_plan_sha256": authority_packet["approved_plan_sha256"],
    }
    verify_execution_authority(baseline_dir, bindings, project_root=project_root)

    modules = _import_verified_upstream(project_root=project_root)
    load_verified_cross_root_receipt = modules[
        "src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission"
    ].load_verified_cross_root_receipt

    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)

    summary = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id, receipt=receipt)
    final_root = _publish_v3_diagnostic_to_parent(summary, run_id=run_id, parent_dir=parent_dir)
    if not final_root.resolve().is_relative_to(expected_parent):
        raise Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(
            f"STOP=stage1_5h_v3_publication_integrity_failure:final_root_outside_project:{final_root}"
        )

    return load_verified_v3_root(final_root)
