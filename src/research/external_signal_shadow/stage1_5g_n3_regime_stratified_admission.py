"""
src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py

Stage 1.5G N=3 Cross-Root Deduplicated and Product-Regime Stratified Admission Module.
Enforces pure read-only structural validation, AST import boundary, parent-aware
deduplication (projecting only CTUSDT from CT root), frozen product-regime declarations,
atomic directory publication, and 13 false authority governance flags.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.research.external_signal_shadow.safety import canonical_json_dumps

APPROVED_DESIGN_REL_PATH = "docs/designs/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-design_CN.md"
APPROVED_DESIGN_SHA256 = "81f7da45c882cc16430f57e4252e5530e457a95b7f36ff045d262ded9e755da0"
APPROVED_PLAN_REL_PATH = "docs/plans/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-implementation-plan_CN.md"
APPROVED_PLAN_SHA256 = "f0582a5ba03db3be8340dfa8d5d47b5c1dcb63caac19cebb5888a2c1d56eb5bb"

FROZEN_UPSTREAM_CONTRACT: dict[str, str] = {
    "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py": "596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d",
    "configs/base.py": "414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4",
    "src/research/external_signal_shadow/safety.py": "1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d",
}

FROZEN_INPUT_RECORDS: list[dict[str, Any]] = [
    {
        "input_key": "moonshot",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot",
        "source_manifest_sha256": "611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db",
    },
    {
        "input_key": "batch7",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7",
        "source_manifest_sha256": "0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280",
    },
    {
        "input_key": "ct_projection",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20261002T010000Z_ctusdt_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "9f6a1e9797dbc42af3ce103ed231689adb0422ef1ab23768ca398eb8ec153c1c",
        "source_root_path": "data/external_signal_shadow/local_evidence/20261001T074500Z_stage1_5f_ctusdt",
        "source_manifest_sha256": "f69efe25ea2efd03054372c41f882e2deb10e9842b890d71f60c19ce9b44f7db",
    },
]

FROZEN_PRODUCT_REGIME_DECLARATIONS: dict[str, dict[str, Any]] = {
    "crypto_standard_perpetual": {
        "parent_article_id": "6bd26adeb6f742fe88eb72faca183566",
        "official_url": "https://www.binance.com/en/support/announcement/6bd26adeb6f742fe88eb72faca183566",
        "underlying_economic_type": "crypto_token",
        "lifecycle_regime": "standard",
        "reference_market_availability": "not_asserted",
        "mark_price_regime": "not_asserted",
    },
    "pre_ipo_equity_perpetual": {
        "parent_article_id": "7379b99aa0f349a49c3b3feca1b4bbd6",
        "official_url": "https://www.binance.com/en/support/announcement/7379b99aa0f349a49c3b3feca1b4bbd6",
        "underlying_economic_type": "equity",
        "lifecycle_regime": "pre_ipo",
        "reference_market_availability": "unavailable_pre_ipo",
        "mark_price_regime": "exchange_trade_derived",
    },
    "tradfi_equity_or_etf_perpetual_batch": {
        "parent_article_id": "0c6ea14ba89b451db6ec9ec364045d22",
        "official_url": "https://www.binance.com/en/support/announcement/0c6ea14ba89b451db6ec9ec364045d22",
        "underlying_economic_type": "tradfi_equity_or_etf",
        "lifecycle_regime": "standard",
        "reference_market_availability": "not_asserted",
        "mark_price_regime": "not_asserted",
    },
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

EXPECTED_UPSTREAM_FALSE_KEYS: tuple[str, ...] = (
    "trade_signal_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_engine_allowed",
    "alpha_interpretation_allowed",
    "execution_feasibility_claim_allowed",
)

RUN_ID_REGEX = re.compile(r"^stage1_5g_n3_regime_stratified_admission_[0-9]{8}T[0-9]{6}Z$")
DEFAULT_ADMISSION_PARENT = "data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions"

_CACHED_UPSTREAM_MODULES: dict[str, Any] = {}
_FAILPOINT_HOOK: Any = None


class Stage1_5GN3RegimeAdmissionError(Exception):
    """Specific error for Stage 1.5G N=3 admission failures."""
    pass


class Stage1_5GN3PostRenameDurabilityFailure(Stage1_5GN3RegimeAdmissionError):
    """Raised when publication failure occurs after atomic rename or during parent fsync."""
    pass


_MACOS_SYSTEM_ROOT_SYMLINKS: set[Path] = {Path("/tmp"), Path("/var"), Path("/etc")}


def _has_symlink_components(path: Path | str) -> bool:
    curr = Path(path)
    if not curr.is_absolute():
        curr = curr.absolute()
    while True:
        if curr.is_symlink() and curr not in _MACOS_SYSTEM_ROOT_SYMLINKS:
            return True
        if curr == curr.parent:
            break
        curr = curr.parent
    return False


def _assert_no_symlinks(path: Path | str, error_tag: str = "symlink_detected") -> None:
    curr = Path(path)
    if not curr.is_absolute():
        curr = curr.absolute()
    while True:
        if curr.is_symlink() and curr not in _MACOS_SYSTEM_ROOT_SYMLINKS:
            raise Stage1_5GN3RegimeAdmissionError(
                f"STOP=stage1_5g_n3_regime_publication_integrity_failure:{error_tag}:{curr}"
            )
        if curr == curr.parent:
            break
        curr = curr.parent


def _trigger_failpoint(point: str) -> None:
    global _FAILPOINT_HOOK
    if _FAILPOINT_HOOK is not None:
        _FAILPOINT_HOOK(point)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project_root_from_core_file() -> Path:
    return Path(__file__).resolve().parents[3]


def verify_execution_authority(project_root: Path | None = None) -> dict[str, Any]:
    root = (project_root or _project_root_from_core_file()).resolve()
    bundle_dir = root / ".git" / "plan-execution" / "stage1_5g_n3_regime" / APPROVED_PLAN_SHA256
    _assert_no_symlinks(bundle_dir)

    if not bundle_dir.is_dir():
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:bundle_missing")

    # 1. Implementation authorization record
    p_auth = bundle_dir / "implementation_authorization.txt"
    p_auth_sidecar = bundle_dir / "implementation_authorization.sha256"
    p_auth_sidecar_alt = bundle_dir / "implementation_authorization.txt.sha256"
    if p_auth.is_symlink() or not p_auth.is_file():
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:auth_missing")

    auth_bytes = p_auth.read_bytes()
    calc_auth_sha = hashlib.sha256(auth_bytes).hexdigest()
    sidecar_p = p_auth_sidecar if p_auth_sidecar.exists() else p_auth_sidecar_alt
    if not sidecar_p.exists() or sidecar_p.is_symlink():
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:auth_sidecar_missing")
    if calc_auth_sha not in sidecar_p.read_text(encoding="utf-8"):
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:auth_sidecar_mismatch")

    auth_text = auth_bytes.decode("utf-8")
    lines = auth_text.strip().splitlines()
    if len(lines) != 2:
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:auth_grammar")

    m = re.match(r"^我批准实施 Plan：(.*)（SHA-256: ([0-9a-f]{64})）。$", lines[0])
    if not m:
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:auth_grammar")
    parsed_plan_path, parsed_plan_sha = m.group(1), m.group(2)
    if parsed_plan_path != APPROVED_PLAN_REL_PATH or parsed_plan_sha != APPROVED_PLAN_SHA256:
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:plan_binding_mismatch")
    if lines[1] != "允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。":
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:auth_permissions_clause")

    # 2. Execution authority JSON
    p_exec = bundle_dir / "execution_authority.json"
    p_exec_sidecar = bundle_dir / "execution_authority.sha256"
    p_exec_sidecar_alt = bundle_dir / "execution_authority.json.sha256"
    if p_exec.is_symlink() or not p_exec.is_file():
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:exec_auth_missing")

    exec_bytes = p_exec.read_bytes()
    calc_exec_sha = hashlib.sha256(exec_bytes).hexdigest()
    exec_sidecar_p = p_exec_sidecar if p_exec_sidecar.exists() else p_exec_sidecar_alt
    if not exec_sidecar_p.exists() or exec_sidecar_p.is_symlink():
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:exec_sidecar_missing")
    if calc_exec_sha not in exec_sidecar_p.read_text(encoding="utf-8"):
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:exec_sidecar_mismatch")

    try:
        authority = json.loads(exec_bytes.decode("utf-8"))
    except Exception as exc:
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:exec_auth_json") from exc

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
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:exec_auth_keys")

    if authority["project_root"] != str(root):
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:project_root_mismatch")
    if authority["approved_design_path"] != APPROVED_DESIGN_REL_PATH or authority["approved_design_sha256"] != APPROVED_DESIGN_SHA256:
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:design_binding_mismatch")
    if authority["approved_plan_path"] != APPROVED_PLAN_REL_PATH or authority["approved_plan_sha256"] != APPROVED_PLAN_SHA256:
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:plan_binding_mismatch")
    if authority["current_plan_sha256"] != APPROVED_PLAN_SHA256:
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:current_plan_sha_mismatch")

    # Assert Git HEAD == base_sha
    base_sha = authority["base_sha"]
    if not isinstance(base_sha, str) or len(base_sha) != 40 or not all(c in "0123456789abcdefABCDEF" for c in base_sha):
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:invalid_base_sha_format")

    res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise Stage1_5GN3RegimeAdmissionError(
            f"STOP=approved_authority_mismatch:git_rev_parse_failed:{res.stderr.strip()}"
        )
    current_head = res.stdout.strip()
    if current_head != base_sha:
        raise Stage1_5GN3RegimeAdmissionError(
            f"STOP=approved_authority_mismatch:head_sha_mismatch:{current_head}_vs_{base_sha}"
        )

    # 3. Verify Design and Plan bytes on disk
    p_design = root / APPROVED_DESIGN_REL_PATH
    p_plan = root / APPROVED_PLAN_REL_PATH
    if p_design.is_symlink() or not p_design.is_file() or _sha256(p_design) != APPROVED_DESIGN_SHA256:
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:design_bytes_drift")
    if p_plan.is_symlink() or not p_plan.is_file() or _sha256(p_plan) != APPROVED_PLAN_SHA256:
        raise Stage1_5GN3RegimeAdmissionError("STOP=approved_authority_mismatch:plan_bytes_drift")

    return authority


def verify_local_receipt_generation_authority(project_root: Path | None = None) -> dict[str, Any]:
    root = (project_root or _project_root_from_core_file()).resolve()
    bundle_dir = root / ".git" / "plan-execution" / "stage1_5g_n3_regime" / APPROVED_PLAN_SHA256
    _assert_no_symlinks(bundle_dir)

    p_receipt_auth = bundle_dir / "receipt_generation_authorization.txt"
    p_receipt_sidecar = bundle_dir / "receipt_generation_authorization.sha256"
    if not p_receipt_auth.exists() or p_receipt_auth.is_symlink() or not p_receipt_auth.is_file():
        raise Stage1_5GN3RegimeAdmissionError("STOP=local_receipt_generation_not_authorized")
    if not p_receipt_sidecar.exists() or p_receipt_sidecar.is_symlink():
        raise Stage1_5GN3RegimeAdmissionError("STOP=local_receipt_generation_not_authorized")

    auth_bytes = p_receipt_auth.read_bytes()
    calc_sha = hashlib.sha256(auth_bytes).hexdigest()
    if calc_sha not in p_receipt_sidecar.read_text(encoding="utf-8"):
        raise Stage1_5GN3RegimeAdmissionError("STOP=local_receipt_generation_not_authorized")

    lines = auth_bytes.decode("utf-8").strip().splitlines()
    if len(lines) != 2:
        raise Stage1_5GN3RegimeAdmissionError("STOP=local_receipt_generation_not_authorized")

    m = re.match(r"^我批准本地生成 N=3 receipt：(.*)（SHA-256: ([0-9a-f]{64})）。$", lines[0])
    if not m or m.group(1) != APPROVED_PLAN_REL_PATH or m.group(2) != APPROVED_PLAN_SHA256:
        raise Stage1_5GN3RegimeAdmissionError("STOP=local_receipt_generation_not_authorized")

    if lines[1] != "允许仅本地生成 receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。":
        raise Stage1_5GN3RegimeAdmissionError("STOP=local_receipt_generation_not_authorized")

    return {"status": "authorized", "plan_sha256": APPROVED_PLAN_SHA256}


def verify_frozen_upstream_contract(project_root: Path | None = None) -> None:
    root = (project_root or _project_root_from_core_file()).resolve()
    for rel_path, expected_sha in FROZEN_UPSTREAM_CONTRACT.items():
        p = root / rel_path
        if p.is_symlink() or not p.is_file():
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")
        if _sha256(p) != expected_sha:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")


def _import_verified_upstream(project_root: Path | None = None) -> dict[str, Any]:
    global _CACHED_UPSTREAM_MODULES
    root = (project_root or _project_root_from_core_file()).resolve()

    target_modules = {
        "src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review": "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py",
        "configs.base": "configs/base.py",
        "src.research.external_signal_shadow.safety": "src/research/external_signal_shadow/safety.py",
    }

    if not _CACHED_UPSTREAM_MODULES:
        for mod_name, rel_path in target_modules.items():
            if mod_name in sys.modules:
                mod = sys.modules[mod_name]
                expected_origin = str((root / rel_path).resolve())
                mod_file = getattr(mod, "__file__", None)
                spec_origin = getattr(getattr(mod, "__spec__", None), "origin", None)
                if (mod_file and str(Path(mod_file).resolve()) != expected_origin) or (
                    spec_origin and str(Path(spec_origin).resolve()) != expected_origin
                ):
                    raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")

        verify_frozen_upstream_contract(project_root=root)

        loaded = {}
        for mod_name, rel_path in target_modules.items():
            mod = importlib.import_module(mod_name)
            expected_origin = str((root / rel_path).resolve())
            mod_file = getattr(mod, "__file__", None)
            spec_origin = getattr(getattr(mod, "__spec__", None), "origin", None)
            if not mod_file or str(Path(mod_file).resolve()) != expected_origin:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")
            if not spec_origin or str(Path(spec_origin).resolve()) != expected_origin:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")
            if _sha256(Path(mod_file)) != FROZEN_UPSTREAM_CONTRACT[rel_path]:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")
            loaded[mod_name] = mod

        _CACHED_UPSTREAM_MODULES = loaded
    else:
        for mod_name, cached_mod in _CACHED_UPSTREAM_MODULES.items():
            if sys.modules.get(mod_name) is not cached_mod:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")
            rel_path = target_modules[mod_name]
            expected_origin = str((root / rel_path).resolve())
            mod_file = getattr(cached_mod, "__file__", None)
            spec_origin = getattr(getattr(cached_mod, "__spec__", None), "origin", None)
            if not mod_file or str(Path(mod_file).resolve()) != expected_origin:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")
            if not spec_origin or str(Path(spec_origin).resolve()) != expected_origin:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")
            if _sha256(Path(mod_file)) != FROZEN_UPSTREAM_CONTRACT[rel_path]:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_upstream_contract_drift")

    return _CACHED_UPSTREAM_MODULES


def compare_admitted_projection(stored_proj: dict[str, Any], recomputed_proj: dict[str, Any]) -> None:
    required_keys = {
        "schema_version",
        "decision",
        "clean_depth_evidence_pass",
        "source_evidence_manifest_sha256",
        "formal_completed_event_symbol_ids_sha256",
        "formal_children",
    }
    if set(stored_proj.keys()) != required_keys or set(recomputed_proj.keys()) != required_keys:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

    for k in (
        "schema_version",
        "decision",
        "clean_depth_evidence_pass",
        "source_evidence_manifest_sha256",
        "formal_completed_event_symbol_ids_sha256",
    ):
        if stored_proj[k] != recomputed_proj[k] or type(stored_proj[k]) is not type(recomputed_proj[k]):
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

    s_children = stored_proj["formal_children"]
    r_children = recomputed_proj["formal_children"]
    if not isinstance(s_children, list) or not isinstance(r_children, list):
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")
    if len(s_children) != len(r_children) or len(s_children) == 0:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

    child_keys = {
        "event_symbol_id",
        "event_id",
        "symbol",
        "source_article_id",
        "evidence_label",
        "state_status",
        "formal_completed",
    }
    for sc, rc in zip(s_children, r_children):
        if set(sc.keys()) != child_keys or set(rc.keys()) != child_keys:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")
        for ck in child_keys:
            if sc[ck] != rc[ck] or type(sc[ck]) is not type(rc[ck]):
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")


def admit_frozen_n3_inputs(
    project_root: Path | None = None,
    input_records_override: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    root = (project_root or _project_root_from_core_file()).resolve()
    modules = _import_verified_upstream(project_root=root)
    rev_mod = modules["src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review"]
    load_stage1_5g_inputs = rev_mod.load_stage1_5g_inputs
    build_stage1_5g_review_summary = rev_mod.build_stage1_5g_review_summary

    records_to_process = input_records_override if input_records_override is not None else FROZEN_INPUT_RECORDS
    if len(records_to_process) != 3:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

    expected_keys_order = ["moonshot", "batch7", "ct_projection"]
    if [r.get("input_key") for r in records_to_process] != expected_keys_order:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

    admitted_results: list[dict[str, Any]] = []

    for record in records_to_process:
        # 1. Stored summary checks
        if "stored_summary_path" not in record or "stored_summary_sha256" not in record:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")
        stored_p = root / record["stored_summary_path"]
        _assert_no_symlinks(stored_p)
        if not stored_p.is_file() or _sha256(stored_p) != record["stored_summary_sha256"]:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

        try:
            stored_summary = json.loads(stored_p.read_bytes().decode("utf-8"))
        except Exception as exc:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch") from exc

        # 2. Source root checks
        if "source_root_path" not in record or "source_manifest_sha256" not in record:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")
        source_p = root / record["source_root_path"]
        _assert_no_symlinks(source_p)
        if not source_p.is_dir():
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

        manifest_p = source_p / "SHA256SUMS"
        _assert_no_symlinks(manifest_p)
        if not manifest_p.is_file() or _sha256(manifest_p) != record["source_manifest_sha256"]:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

        # 3. Production loader & reducer
        bundle = load_stage1_5g_inputs(source_p)
        if getattr(bundle, "loader_blockers", None):
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

        recomputed = build_stage1_5g_review_summary(
            summary=bundle.summary,
            watermark=bundle.watermark,
            states=bundle.states,
            accepted_events=bundle.accepted_events,
            snapshots=bundle.snapshots,
            request_manifest_rows=bundle.request_manifest_rows,
            output_root=source_p,
            loader_blockers=bundle.loader_blockers,
        )

        if (
            recomputed.get("schema_version") != 2
            or recomputed.get("decision") != "stage1_5g_depth_evidence_clean_pass"
            or recomputed.get("clean_depth_evidence_pass") is not True
            or len(recomputed.get("blockers", [])) > 0
            or recomputed.get("source_evidence_manifest_sha256") != record.get("source_manifest_sha256")
        ):
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

        for fk in EXPECTED_UPSTREAM_FALSE_KEYS:
            if recomputed.get(fk) is not False or type(recomputed.get(fk)) is not bool:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

        # 4. Extract formal projection
        def _extract_projection(s: dict[str, Any]) -> dict[str, Any]:
            elds = s.get("event_level_decisions", [])
            children = []
            for eld in elds:
                children.append({
                    "event_symbol_id": eld["event_symbol_id"],
                    "event_id": eld["event_id"],
                    "symbol": eld["symbol"],
                    "source_article_id": eld["source_article_id"],
                    "evidence_label": eld["evidence_label"],
                    "state_status": eld["state_status"],
                    "formal_completed": eld["formal_completed"],
                })
            return {
                "schema_version": s["schema_version"],
                "decision": s["decision"],
                "clean_depth_evidence_pass": s["clean_depth_evidence_pass"],
                "source_evidence_manifest_sha256": s["source_evidence_manifest_sha256"],
                "formal_completed_event_symbol_ids_sha256": s["formal_completed_event_symbol_ids_sha256"],
                "formal_children": children,
            }

        stored_proj = _extract_projection(stored_summary)
        recomputed_proj = _extract_projection(recomputed)
        compare_admitted_projection(stored_proj, recomputed_proj)

        # 5. Extract lineage mapping from canonical bundle.accepted_events
        accepted_events_lineage = []
        for ev in bundle.accepted_events:
            accepted_events_lineage.append({
                "symbol": ev.get("symbol"),
                "event_symbol_id": ev.get("event_symbol_id"),
                "event_id": ev.get("event_id"),
                "source_article_id": ev.get("source_article_id"),
                "source_detail_url_normalized": ev.get("source_detail_url_normalized"),
                "source_anchor_contract_hash": ev.get("source_anchor_contract_hash"),
            })

        admitted_results.append({
            "input_key": record["input_key"],
            "stored_summary_path": record["stored_summary_path"],
            "stored_summary_sha256": record["stored_summary_sha256"],
            "source_root_path": record["source_root_path"],
            "source_manifest_sha256": record["source_manifest_sha256"],
            "stored_formal_projection": stored_proj,
            "recomputed_formal_projection": recomputed_proj,
            "accepted_events_lineage": accepted_events_lineage,
        })

    return admitted_results


def build_n3_summary(
    admitted_inputs: list[dict[str, Any]],
    run_id: str,
    declarations_override: dict[str, dict[str, Any]] | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if not RUN_ID_REGEX.match(run_id):
        raise Stage1_5GN3RegimeAdmissionError(
            f"STOP=stage1_5g_n3_regime_publication_integrity_failure:invalid_run_id:{run_id}"
        )

    if len(admitted_inputs) != 3:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

    input_map = {item["input_key"]: item for item in admitted_inputs}
    if set(input_map.keys()) != {"moonshot", "batch7", "ct_projection"}:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch")

    # 1. CT Re-projection and duplicate exclusion
    ct_item = input_map["ct_projection"]
    batch7_item = input_map["batch7"]
    moonshot_item = input_map["moonshot"]

    ct_children = ct_item["recomputed_formal_projection"]["formal_children"]
    batch7_children = batch7_item["recomputed_formal_projection"]["formal_children"]

    if len(ct_children) != 8:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_ct_projection_mismatch:expected_8_children")
    if len(batch7_children) != 7:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_input_authority_mismatch:batch7_children")

    # Locate CTUSDT child
    ct_candidates = [c for c in ct_children if c["symbol"] == "CTUSDT"]
    if len(ct_candidates) != 1:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_ct_projection_mismatch:missing_ct")
    ct_child = ct_candidates[0]

    # Verify CT child exact identity
    if (
        ct_child["event_symbol_id"] != "88df6bae915fb096ea7fe92b4a92d22b3c5b7b268e999636ff062c3fd9989345"
        or ct_child["event_id"] != "374345c5e4527ca0f061155796909acb385fbd084172f175bd8accb00cdbd963"
        or ct_child["source_article_id"] != "6bd26adeb6f742fe88eb72faca183566"
    ):
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_ct_projection_mismatch:ct_identity_mismatch")

    # Verify that the 7 non-CT children in CT root exactly match Batch 7 children
    non_ct_children = [c for c in ct_children if c["symbol"] != "CTUSDT"]
    if len(non_ct_children) != 7:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_ct_projection_mismatch:non_ct_count")

    # Compare non-CT children to batch7 children
    batch7_by_symbol = {c["symbol"]: c for c in batch7_children}
    for nct in non_ct_children:
        sym = nct["symbol"]
        if sym not in batch7_by_symbol:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_ct_projection_mismatch:symbol_mismatch")
        b7_c = batch7_by_symbol[sym]
        if (
            nct["event_symbol_id"] != b7_c["event_symbol_id"]
            or nct["event_id"] != b7_c["event_id"]
            or nct["source_article_id"] != b7_c["source_article_id"]
        ):
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_ct_projection_mismatch:duplicate_differs")

    # 2. Assemble 3 parents:
    # Parent 1: Moonshot
    m_children = moonshot_item["recomputed_formal_projection"]["formal_children"]
    if len(m_children) != 1 or m_children[0]["symbol"] != "MOONSHOTUSDT":
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_parent_identity_mismatch")
    m_parent = {
        "child_event_symbol_ids": [m_children[0]["event_symbol_id"]],
        "child_symbols": ["MOONSHOTUSDT"],
        "parent_article_id": m_children[0]["source_article_id"],
        "parent_event_id": m_children[0]["event_id"],
        "product_regime_id": "pre_ipo_equity_perpetual",
    }

    # Parent 2: Batch 7
    b7_parent = {
        "child_event_symbol_ids": [c["event_symbol_id"] for c in batch7_children],
        "child_symbols": [c["symbol"] for c in batch7_children],
        "parent_article_id": batch7_children[0]["source_article_id"],
        "parent_event_id": batch7_children[0]["event_id"],
        "product_regime_id": "tradfi_equity_or_etf_perpetual_batch",
    }

    # Parent 3: CT (single child)
    ct_parent = {
        "child_event_symbol_ids": [ct_child["event_symbol_id"]],
        "child_symbols": ["CTUSDT"],
        "parent_article_id": ct_child["source_article_id"],
        "parent_event_id": ct_child["event_id"],
        "product_regime_id": "crypto_standard_perpetual",
    }

    parent_ledger = [m_parent, b7_parent, ct_parent]

    # Verify counts and distinctness
    distinct_articles = {p["parent_article_id"] for p in parent_ledger}
    distinct_events = {p["parent_event_id"] for p in parent_ledger}
    all_symbols = [sym for p in parent_ledger for sym in p["child_symbols"]]
    all_esids = [esid for p in parent_ledger for esid in p["child_event_symbol_ids"]]

    if len(distinct_articles) != 3 or len(distinct_events) != 3:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_parent_identity_mismatch")
    if len(all_symbols) != 9 or len(set(all_symbols)) != 9:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_parent_identity_mismatch")
    if len(all_esids) != 9 or len(set(all_esids)) != 9:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_parent_identity_mismatch")

    # 3. Product-regime ledger construction
    decls = declarations_override if declarations_override is not None else FROZEN_PRODUCT_REGIME_DECLARATIONS
    product_regime_ledger = []

    # Map input lineage by input_key
    lineage_map = {
        "moonshot": moonshot_item["accepted_events_lineage"],
        "batch7": batch7_item["accepted_events_lineage"],
        "ct_projection": [ev for ev in ct_item["accepted_events_lineage"] if ev["symbol"] == "CTUSDT"],
    }

    for p in parent_ledger:
        regime_id = p["product_regime_id"]
        if regime_id not in decls or regime_id not in FROZEN_PRODUCT_REGIME_DECLARATIONS:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_classification_mismatch")
        decl = decls[regime_id]
        frozen_decl = FROZEN_PRODUCT_REGIME_DECLARATIONS[regime_id]

        for field in ("underlying_economic_type", "lifecycle_regime", "reference_market_availability", "mark_price_regime"):
            if decl.get(field) != frozen_decl[field]:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_classification_mismatch")

        if decl.get("parent_article_id") != p["parent_article_id"] or decl.get("parent_article_id") != frozen_decl["parent_article_id"]:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_classification_mismatch")

        expected_url = f"https://www.binance.com/en/support/announcement/{p['parent_article_id']}"
        if decl.get("official_url") != expected_url or decl.get("official_url") != frozen_decl["official_url"]:
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_classification_mismatch")

        # Determine lineage rows for this parent
        if regime_id == "pre_ipo_equity_perpetual":
            rows = lineage_map["moonshot"]
        elif regime_id == "tradfi_equity_or_etf_perpetual_batch":
            rows = lineage_map["batch7"]
        else:
            rows = lineage_map["ct_projection"]

        # Validate URL in bundle
        for r in rows:
            if r.get("source_detail_url_normalized") != expected_url:
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_classification_mismatch")

        anchor_hashes = [r["source_anchor_contract_hash"] for r in rows]
        if len(anchor_hashes) != len(p["child_symbols"]):
            raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_classification_mismatch")
        for ah in anchor_hashes:
            if not isinstance(ah, str) or len(ah) != 64 or not re.match(r"^[0-9a-f]{64}$", ah):
                raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_classification_mismatch")

        regime_entry = {
            "classification_status": "classified",
            "lifecycle_regime": decl["lifecycle_regime"],
            "mark_price_regime": decl["mark_price_regime"],
            "parent_article_id": p["parent_article_id"],
            "product_regime_id": regime_id,
            "reference_market_availability": decl["reference_market_availability"],
            "source_detail_url_normalized": expected_url,
            "source_anchor_contract_hashes": anchor_hashes,
            "underlying_economic_type": decl["underlying_economic_type"],
        }
        product_regime_ledger.append(regime_entry)

    # Clean input records for serializing (omit raw lineage objects from persistent summary)
    persistent_input_records = []
    for item in admitted_inputs:
        persistent_input_records.append({
            "input_key": item["input_key"],
            "stored_summary_path": item["stored_summary_path"],
            "stored_summary_sha256": item["stored_summary_sha256"],
            "source_root_path": item["source_root_path"],
            "source_manifest_sha256": item["source_manifest_sha256"],
            "stored_formal_projection": item["stored_formal_projection"],
            "recomputed_formal_projection": item["recomputed_formal_projection"],
        })

    summary = {
        "authority_flags": copy.deepcopy(EXPECTED_13_FALSE_FLAGS),
        "cross_root_evidence_count_status": "sufficient",
        "decision": "stage1_5g_n3_regime_stratified_admission_pass",
        "distinct_source_article_count": 3,
        "formal_symbol_count": 9,
        "independent_parent_event_count": 3,
        "input_records": persistent_input_records,
        "parent_ledger": parent_ledger,
        "product_regime_ledger": product_regime_ledger,
        "run_id": run_id,
        "schema_version": 1,
        "stage1_5g_gate3_complete": False,
    }

    return summary


def render_review(summary: dict[str, Any]) -> str:
    lines = [
        "# Stage 1.5G N=3 Regime-Stratified Admission Receipt",
        "",
        f"- `run_id`: `{summary['run_id']}`",
        f"- `schema_version`: `{summary['schema_version']}`",
        f"- `decision`: `{summary['decision']}`",
        f"- `cross_root_evidence_count_status`: `{summary['cross_root_evidence_count_status']}`",
        f"- `distinct_source_article_count`: `{summary['distinct_source_article_count']}`",
        f"- `independent_parent_event_count`: `{summary['independent_parent_event_count']}`",
        f"- `formal_symbol_count`: `{summary['formal_symbol_count']}`",
        f"- `stage1_5g_gate3_complete`: `{summary['stage1_5g_gate3_complete']}`",
        "",
        "## Admitted Inputs",
        "",
    ]
    for rec in summary["input_records"]:
        lines.append(f"### Input: `{rec['input_key']}`")
        lines.append(f"- Stored Summary Path: `{rec['stored_summary_path']}`")
        lines.append(f"- Stored Summary SHA-256: `{rec['stored_summary_sha256']}`")
        lines.append(f"- Source Root Path: `{rec['source_root_path']}`")
        lines.append(f"- Source Manifest SHA-256: `{rec['source_manifest_sha256']}`")
        lines.append("")

    lines.append("## Parent Ledger")
    lines.append("")
    for p in summary["parent_ledger"]:
        lines.append(f"### Parent Article: `{p['parent_article_id']}`")
        lines.append(f"- Parent Event ID: `{p['parent_event_id']}`")
        lines.append(f"- Product Regime ID: `{p['product_regime_id']}`")
        lines.append(f"- Child Symbols ({len(p['child_symbols'])}): `{', '.join(sorted(p['child_symbols']))}`")
        lines.append("")

    lines.append("## Product Regime Ledger")
    lines.append("")
    for r in summary["product_regime_ledger"]:
        lines.append(f"### Regime: `{r['product_regime_id']}` (Article `{r['parent_article_id']}`)")
        lines.append(f"- Classification Status: `{r['classification_status']}`")
        lines.append(f"- Underlying Economic Type: `{r['underlying_economic_type']}`")
        lines.append(f"- Lifecycle Regime: `{r['lifecycle_regime']}`")
        lines.append(f"- Reference Market Availability: `{r['reference_market_availability']}`")
        lines.append(f"- Mark Price Regime: `{r['mark_price_regime']}`")
        lines.append(f"- Normalized Announcement URL: `{r['source_detail_url_normalized']}`")
        lines.append(f"- Source Anchor Hashes: `{', '.join(r['source_anchor_contract_hashes'])}`")
        lines.append("")

    lines.append("## Authority Vector")
    lines.append("")
    for k, v in sorted(summary["authority_flags"].items()):
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")

    return "\n".join(lines) + "\n"


def _write_and_fsync_file(path: Path, data: bytes) -> None:
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def load_verified_n3_receipt(
    receipt_dir: Path | str,
    project_root: Path | None = None,
    future_consumer_allowed: bool = False,
) -> dict[str, Any]:
    if future_consumer_allowed:
        raise Stage1_5GN3RegimeAdmissionError("STOP=stage1_5g_n3_regime_future_consumer_not_authorized")

    raw_receipt_dir = Path(receipt_dir)
    _assert_no_symlinks(raw_receipt_dir, "receipt_dir_symlink")
    final_root = raw_receipt_dir.resolve()
    _assert_no_symlinks(final_root, "final_root_symlink")

    if not final_root.is_dir():
        raise Stage1_5GN3RegimeAdmissionError(
            f"STOP=stage1_5g_n3_regime_publication_integrity_failure:not_dir:{final_root}"
        )

    # Check allowed files in final_root
    allowed_files = {
        "stage1_5g_n3_regime_stratified_admission_manifest.json",
        "stage1_5g_n3_regime_stratified_admission_summary.json",
        "stage1_5g_n3_regime_stratified_admission_review_CN.md",
    }
    for item in final_root.iterdir():
        _assert_no_symlinks(item, "unlisted_file_symlink")
        if item.name not in allowed_files or not item.is_file():
            raise Stage1_5GN3RegimeAdmissionError(
                f"STOP=stage1_5g_n3_regime_publication_integrity_failure:unlisted_file:{item.name}"
            )

    # 1. Manifest verification
    manifest_p = final_root / "stage1_5g_n3_regime_stratified_admission_manifest.json"
    _assert_no_symlinks(manifest_p, "manifest_symlink")
    if not manifest_p.is_file():
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:manifest_missing"
        )

    manifest_bytes = manifest_p.read_bytes()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as exc:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:manifest_json"
        ) from exc

    if canonical_json_dumps(manifest).encode("utf-8") != manifest_bytes:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:manifest_not_canonical"
        )

    if set(manifest.keys()) != {"schema_version", "run_id", "artifacts"}:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:manifest_keys"
        )

    if (
        manifest.get("schema_version") != 1
        or not isinstance(manifest.get("run_id"), str)
        or not re.match(r"^stage1_5g_n3_regime_stratified_admission_[0-9]{8}T[0-9]{6}Z$", manifest["run_id"])
    ):
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:manifest_schema"
        )

    expected_artifacts = {
        "stage1_5g_n3_regime_stratified_admission_summary.json",
        "stage1_5g_n3_regime_stratified_admission_review_CN.md",
    }
    if not isinstance(manifest.get("artifacts"), dict) or set(manifest["artifacts"].keys()) != expected_artifacts:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:manifest_artifact_keys"
        )

    for art_name, art_meta in manifest["artifacts"].items():
        if not isinstance(art_meta, dict) or set(art_meta.keys()) != {"relative_path", "byte_count", "sha256"}:
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:metadata_keys"
            )
        if art_meta["relative_path"] != art_name:
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:metadata_relative_path"
            )
        if not isinstance(art_meta["byte_count"], int) or isinstance(art_meta["byte_count"], bool) or art_meta["byte_count"] <= 0:
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:metadata_byte_count"
            )
        if not isinstance(art_meta["sha256"], str) or len(art_meta["sha256"]) != 64 or not all(c in "0123456789abcdef" for c in art_meta["sha256"]):
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:metadata_sha256_format"
            )

        art_p = final_root / art_name
        _assert_no_symlinks(art_p, "artifact_symlink")
        if not art_p.is_file():
            raise Stage1_5GN3RegimeAdmissionError(
                f"STOP=stage1_5g_n3_regime_publication_integrity_failure:artifact_missing:{art_name}"
            )
        actual_bytes = art_p.read_bytes()
        actual_sha = hashlib.sha256(actual_bytes).hexdigest()
        if len(actual_bytes) != art_meta["byte_count"] or actual_sha != art_meta["sha256"]:
            raise Stage1_5GN3RegimeAdmissionError(
                f"STOP=stage1_5g_n3_regime_publication_integrity_failure:artifact_hash_mismatch:{art_name}"
            )

    # 2. Summary verification
    summary_p = final_root / "stage1_5g_n3_regime_stratified_admission_summary.json"
    _assert_no_symlinks(summary_p, "summary_symlink")
    if not summary_p.is_file():
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:summary_missing"
        )
    summary_bytes = summary_p.read_bytes()
    try:
        summary = json.loads(summary_bytes.decode("utf-8"))
    except Exception as exc:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:summary_json"
        ) from exc

    if canonical_json_dumps(summary).encode("utf-8") != summary_bytes:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:summary_not_canonical"
        )

    required_keys = {
        "authority_flags",
        "cross_root_evidence_count_status",
        "decision",
        "distinct_source_article_count",
        "formal_symbol_count",
        "independent_parent_event_count",
        "input_records",
        "parent_ledger",
        "product_regime_ledger",
        "run_id",
        "schema_version",
        "stage1_5g_gate3_complete",
    }
    if set(summary.keys()) != required_keys:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:summary_keys"
        )

    if (
        summary["schema_version"] != 1
        or summary["run_id"] != manifest["run_id"]
        or summary["decision"] != "stage1_5g_n3_regime_stratified_admission_pass"
        or summary["cross_root_evidence_count_status"] != "sufficient"
        or summary["formal_symbol_count"] != 9
        or summary["distinct_source_article_count"] != 3
        or summary["independent_parent_event_count"] != 3
        or summary["stage1_5g_gate3_complete"] is not False
    ):
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:summary_scalars"
        )

    if summary["authority_flags"] != EXPECTED_13_FALSE_FLAGS:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:authority_flags"
        )

    # Validate product_regime_ledger against frozen declarations
    regime_ledger = summary.get("product_regime_ledger")
    if not isinstance(regime_ledger, list) or len(regime_ledger) != 3:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:product_regime_ledger"
        )
    expected_articles = [
        "7379b99aa0f349a49c3b3feca1b4bbd6",
        "0c6ea14ba89b451db6ec9ec364045d22",
        "6bd26adeb6f742fe88eb72faca183566",
    ]
    for r_item, exp_art in zip(regime_ledger, expected_articles):
        if (
            not isinstance(r_item, dict)
            or r_item.get("parent_article_id") != exp_art
            or r_item.get("classification_status") != "classified"
        ):
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:product_regime_ledger"
            )
        reg_id = r_item.get("product_regime_id")
        if reg_id not in FROZEN_PRODUCT_REGIME_DECLARATIONS:
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:product_regime_ledger"
            )
        decl = FROZEN_PRODUCT_REGIME_DECLARATIONS[reg_id]
        if decl["parent_article_id"] != exp_art:
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:product_regime_ledger"
            )
        for fld in (
            "underlying_economic_type",
            "lifecycle_regime",
            "reference_market_availability",
            "mark_price_regime",
        ):
            if r_item.get(fld) != decl[fld]:
                raise Stage1_5GN3RegimeAdmissionError(
                    "STOP=stage1_5g_n3_regime_publication_integrity_failure:product_regime_ledger"
                )
        if (
            r_item.get("source_detail_url_normalized")
            != f"https://www.binance.com/en/support/announcement/{exp_art}"
        ):
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:product_regime_ledger"
            )
        hashes = r_item.get("source_anchor_contract_hashes")
        if (
            not isinstance(hashes, list)
            or not hashes
            or not all(isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h) for h in hashes)
        ):
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:product_regime_ledger"
            )

    # Validate parent_ledger
    parent_ledger = summary.get("parent_ledger")
    if not isinstance(parent_ledger, list) or len(parent_ledger) != 3:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:parent_ledger"
        )
    expected_parents = [
        ("7379b99aa0f349a49c3b3feca1b4bbd6", "e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5", ["MOONSHOTUSDT"], "pre_ipo_equity_perpetual"),
        ("0c6ea14ba89b451db6ec9ec364045d22", "d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0", ["ACNUSDT", "BWETUSDT", "CRMLUSDT", "MPUSDT", "NKEUSDT", "SECZUSDT", "UNHUSDT"], "tradfi_equity_or_etf_perpetual_batch"),
        ("6bd26adeb6f742fe88eb72faca183566", "374345c5e4527ca0f061155796909acb385fbd084172f175bd8accb00cdbd963", ["CTUSDT"], "crypto_standard_perpetual"),
    ]
    for p_item, (exp_art, exp_ev, exp_syms, exp_reg) in zip(parent_ledger, expected_parents):
        if (
            not isinstance(p_item, dict)
            or p_item.get("parent_article_id") != exp_art
            or p_item.get("parent_event_id") != exp_ev
            or set(p_item.get("child_symbols", [])) != set(exp_syms)
            or p_item.get("product_regime_id") != exp_reg
        ):
            raise Stage1_5GN3RegimeAdmissionError(
                "STOP=stage1_5g_n3_regime_publication_integrity_failure:parent_ledger"
            )

    # Validate input_records
    input_records = summary.get("input_records")
    if (
        not isinstance(input_records, list)
        or len(input_records) != len(FROZEN_INPUT_RECORDS)
        or [r.get("input_key") for r in input_records] != [r["input_key"] for r in FROZEN_INPUT_RECORDS]
    ):
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:input_records"
        )

    # 3. Review verification
    review_p = final_root / "stage1_5g_n3_regime_stratified_admission_review_CN.md"
    _assert_no_symlinks(review_p, "review_symlink")
    if not review_p.is_file():
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:review_missing"
        )
    expected_md = render_review(summary)
    actual_md = review_p.read_text(encoding="utf-8")
    if actual_md != expected_md:
        raise Stage1_5GN3RegimeAdmissionError(
            "STOP=stage1_5g_n3_regime_publication_integrity_failure:review_projection_mismatch"
        )

    return summary


def classify_receipt_state(output_parent: Path, run_id: str) -> str:
    raw_parent = Path(output_parent)
    if _has_symlink_components(raw_parent):
        return "corrupt_or_unknown"
    p_parent = raw_parent.resolve()
    if _has_symlink_components(p_parent):
        return "corrupt_or_unknown"

    final_root = p_parent / run_id
    if _has_symlink_components(final_root):
        return "corrupt_or_unknown"

    # Sibling scan
    matching_siblings = []
    has_malformed_sibling = False
    if p_parent.exists():
        for child in p_parent.iterdir():
            if child.name.startswith(f".{run_id}.staging."):
                m = re.match(rf"^\.{re.escape(run_id)}\.staging\.([0-9]+)$", child.name)
                if not m or child.is_symlink() or not child.is_dir() or _has_symlink_components(child):
                    has_malformed_sibling = True
                else:
                    matching_siblings.append(child)

    final_exists = final_root.exists() or final_root.is_symlink()

    if has_malformed_sibling:
        return "corrupt_or_unknown"

    if not final_exists:
        if len(matching_siblings) == 0:
            return "unpublished"
        return "staging_only"
    else:
        # Final exists
        if len(matching_siblings) > 0 or final_root.is_symlink() or _has_symlink_components(final_root):
            return "corrupt_or_unknown"
        try:
            load_verified_n3_receipt(final_root)
            return "receipt_published"
        except Exception:
            return "corrupt_or_unknown"


def _publish_n3_receipt_for_lifecycle_test(
    summary: dict[str, Any],
    output_parent: Path,
    project_root: Path | None = None,
) -> Path:
    raw_parent = Path(output_parent)
    _assert_no_symlinks(raw_parent, "parent_dir_symlink")

    raw_root = project_root or _project_root_from_core_file()
    _assert_no_symlinks(raw_root, "project_root_symlink")
    root = raw_root.resolve()
    _assert_no_symlinks(root, "project_root_symlink")

    p_dir = raw_parent.resolve()
    _assert_no_symlinks(p_dir, "parent_dir_symlink")
    p_dir.mkdir(parents=True, exist_ok=True)

    p_fd = os.open(str(p_dir), os.O_RDONLY)
    try:
        fcntl.flock(p_fd, fcntl.LOCK_EX)

        run_id = summary["run_id"]
        final_root = p_dir / run_id

        initial_state = classify_receipt_state(p_dir, run_id)
        if initial_state != "unpublished":
            raise Stage1_5GN3RegimeAdmissionError(
                f"STOP=stage1_5g_n3_regime_publication_integrity_failure:not_fresh:{initial_state}"
            )

        pid = os.getpid()
        staging_dir = p_dir / f".{run_id}.staging.{pid}"
        staging_dir.mkdir(parents=False, exist_ok=False)

        # 1. Summary
        _trigger_failpoint("before_summary_write")
        summary_bytes = canonical_json_dumps(summary).encode("utf-8")
        tmp_sum = staging_dir / f".tmp_summary_{pid}"
        _write_and_fsync_file(tmp_sum, summary_bytes)
        os.replace(tmp_sum, staging_dir / "stage1_5g_n3_regime_stratified_admission_summary.json")
        _trigger_failpoint("after_summary_write")

        # 2. Review
        _trigger_failpoint("before_review_write")
        review_text = render_review(summary)
        review_bytes = review_text.encode("utf-8")
        tmp_rev = staging_dir / f".tmp_review_{pid}"
        _write_and_fsync_file(tmp_rev, review_bytes)
        os.replace(tmp_rev, staging_dir / "stage1_5g_n3_regime_stratified_admission_review_CN.md")
        _trigger_failpoint("after_review_write")

        # 3. Manifest
        _trigger_failpoint("before_manifest_write")
        manifest = {
            "schema_version": 1,
            "run_id": run_id,
            "artifacts": {
                "stage1_5g_n3_regime_stratified_admission_summary.json": {
                    "relative_path": "stage1_5g_n3_regime_stratified_admission_summary.json",
                    "byte_count": len(summary_bytes),
                    "sha256": hashlib.sha256(summary_bytes).hexdigest(),
                },
                "stage1_5g_n3_regime_stratified_admission_review_CN.md": {
                    "relative_path": "stage1_5g_n3_regime_stratified_admission_review_CN.md",
                    "byte_count": len(review_bytes),
                    "sha256": hashlib.sha256(review_bytes).hexdigest(),
                },
            },
        }
        manifest_bytes = canonical_json_dumps(manifest).encode("utf-8")
        tmp_man = staging_dir / f".tmp_manifest_{pid}"
        _write_and_fsync_file(tmp_man, manifest_bytes)
        os.replace(tmp_man, staging_dir / "stage1_5g_n3_regime_stratified_admission_manifest.json")
        _trigger_failpoint("after_manifest_write")

        # Strict test load on staged tree
        load_verified_n3_receipt(staging_dir, project_root=root)

        # Fsync staging directory
        s_fd = os.open(str(staging_dir), os.O_RDONLY)
        try:
            os.fsync(s_fd)
        finally:
            os.close(s_fd)

        # Reclassify under lock before rename
        _trigger_failpoint("before_rename")

        if final_root.exists() or final_root.is_symlink():
            raise Stage1_5GN3RegimeAdmissionError(
                f"STOP=stage1_5g_n3_regime_publication_integrity_failure:collision:{final_root}"
            )

        # Check zero foreign matching siblings
        for child in p_dir.iterdir():
            if child.name.startswith(f".{run_id}.staging.") and child.name != staging_dir.name:
                raise Stage1_5GN3RegimeAdmissionError(
                    f"STOP=stage1_5g_n3_regime_publication_integrity_failure:foreign_staging_sibling_detected:{child.name}"
                )

        current_staging_state = classify_receipt_state(p_dir, run_id)
        if current_staging_state != "staging_only":
            raise Stage1_5GN3RegimeAdmissionError(
                f"STOP=stage1_5g_n3_regime_publication_integrity_failure:invalid_staging_state:{current_staging_state}"
            )

        renamed = False
        try:
            os.replace(staging_dir, final_root)
            renamed = True
            _trigger_failpoint("after_rename")

            # Durability fsync on parent dir
            os.fsync(p_fd)
            _trigger_failpoint("after_parent_fsync")

            post_state = classify_receipt_state(p_dir, run_id)
            if post_state != "receipt_published":
                raise Stage1_5GN3PostRenameDurabilityFailure(
                    f"STOP=POST_RENAME_DURABILITY_FAILURE:invalid_post_state:{post_state}"
                )

            final_load = load_verified_n3_receipt(final_root, project_root=root)
            if final_load["run_id"] != run_id:
                raise Stage1_5GN3PostRenameDurabilityFailure(
                    "STOP=POST_RENAME_DURABILITY_FAILURE:post_rename_verify"
                )
        except Exception as exc:
            if renamed:
                if isinstance(exc, Stage1_5GN3PostRenameDurabilityFailure):
                    raise
                raise Stage1_5GN3PostRenameDurabilityFailure(
                    f"STOP=POST_RENAME_DURABILITY_FAILURE:{exc}"
                ) from exc
            raise

        return final_root
    finally:
        fcntl.flock(p_fd, fcntl.LOCK_UN)
        os.close(p_fd)


def publish_n3_receipt(summary: dict[str, Any], project_root: Path | None = None) -> Path:
    raw_root = project_root or _project_root_from_core_file()
    _assert_no_symlinks(raw_root, "project_root_symlink")
    root = raw_root.resolve()
    _assert_no_symlinks(root, "project_root_symlink")

    # Public writer requires both authorities
    verify_execution_authority(project_root=root)
    verify_local_receipt_generation_authority(project_root=root)

    raw_parent = root / DEFAULT_ADMISSION_PARENT
    _assert_no_symlinks(raw_parent, "parent_dir_symlink")
    p_dir = raw_parent.resolve()
    _assert_no_symlinks(p_dir, "parent_dir_symlink")
    p_dir.mkdir(parents=True, exist_ok=True)
    return _publish_n3_receipt_for_lifecycle_test(summary, output_parent=p_dir, project_root=root)


def run_admission(run_id: str, project_root: Path | None = None) -> dict[str, Any]:
    raw_root = project_root or _project_root_from_core_file()
    _assert_no_symlinks(raw_root, "project_root_symlink")
    root = raw_root.resolve()
    _assert_no_symlinks(root, "project_root_symlink")

    # 1. Authority validation
    verify_execution_authority(project_root=root)

    # 2. Local receipt generation authority validation
    verify_local_receipt_generation_authority(project_root=root)

    # 3. Admittance & publication
    admitted = admit_frozen_n3_inputs(project_root=root)
    summary = build_n3_summary(admitted, run_id=run_id, project_root=root)
    final_root = publish_n3_receipt(summary, project_root=root)
    return load_verified_n3_receipt(final_root, project_root=root)
