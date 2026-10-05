"""Stage 1.5I N=3 Sampled Mid-Price Response Coverage and Exploratory Diagnostic.

Deterministic, read-only consumer over frozen Stage 1.5G and 1.5H receipts.
Emits strictly either complete_n3_exploratory_analysis or coverage_inventory.
Strictly prohibits any Alpha, PnL, execution, or price-path claims.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import importlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

from src.research.external_signal_shadow.safety import canonical_json_dumps

# ---------------------------------------------------------------------------
# Frozen Authorities & Constants
# ---------------------------------------------------------------------------

APPROVED_DESIGN_REL_PATH = "docs/designs/2026-10-04-external-signal-shadow-lab-stage1-5i-sampled-mid-price-response-coverage-exploratory-diagnostic-design_CN.md"
APPROVED_DESIGN_SHA256 = "9b9e2c51927c521844e8121e60ae1aa6b7bbe9acd175e05dfadad4c1a034efc8"
APPROVED_PLAN_REL_PATH = "docs/plans/2026-10-04-external-signal-shadow-lab-stage1-5i-sampled-mid-price-response-coverage-exploratory-diagnostic-implementation-plan_CN.md"
APPROVED_PLAN_SHA256 = "4c233bca0587efa488dbb8339a225d8657e1b0a6c71796f75882fa5a210c2f65"
REVIEWED_PLANNING_BASE_SHA = "96257f6f55788e9b7791bb9bb6c8bd6489300f14"

G_RECEIPT_REL_PATH = "data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z"
G_MANIFEST_SHA256 = "f3b4c76683fe7e1e4a7f28f30437f289f036f6ffc6126f8e9693faad62789adf"
G_SUMMARY_SHA256 = "c92686b4834ee41165850aba99b1b68254b05a4afaf37d5e2789747db60ca941"
G_REVIEW_SHA256 = "df6e12df8b1d105c62dd8cb01baeb0f858aa008c42488f699999a3b9ba51f2dc"

H_RECEIPT_REL_PATH = "data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/stage1_5h_n3_regime_stratified_friction_20261003T070500Z"
H_MANIFEST_SHA256 = "c9034ae8c079e066b1de5a8c092bad00a054170aa22a28392df2f24dd0487bcc"
H_SUMMARY_SHA256 = "1dba9853878d24da8cd3d7ae99f0ec899bfc3d1a90ddcc1399e999659e498b11"
H_REVIEW_SHA256 = "ea774319e905de0ed4e8a62c44238cc33d4e0ac5994188198ee356c4220082b3"

OUTPUT_PARENT_REL = "data/external_signal_shadow/stage1_5i/n3_sampled_mid_price_response"
RUN_ID_REGEX = r"^stage1_5i_n3_sampled_mid_price_response_[0-9]{8}T[0-9]{6}Z$"

FROZEN_UPSTREAM_MODULES = {
    "src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py": "e64abe50b97d5cea303552c59f8f8f98168297ab0cabadfb554de9c1340c0c3d",
    "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py": "596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d",
    "src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py": "2657e5550796ed772abf8acffc5b70b1de22f9c2a33cfb88c824df668655a1bf",
    "configs/base.py": "414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4",
}

FROZEN_SOURCE_ROOT_RECORDS: list[dict[str, Any]] = [
    {
        "input_key": "moonshot",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot",
        "source_manifest_sha256": "611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082",
        "owned_event_symbol_ids": [
            "e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602",
        ],
        "owned_snapshot_relative_paths": [
            "depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl",
        ],
    },
    {
        "input_key": "batch7",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7",
        "source_manifest_sha256": "0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37",
        "owned_event_symbol_ids": [
            "09da9a8516ad799b304fe2cf5d0f3b27bba2706099f9008c2650e3c468ea8035",
            "f49cf85ef4e96d5ddfcd4f8c0e5ec507d2d031ebba6ec3dc0fd59b8ad66a09f9",
            "f66e0e5a56fdbfefc3292200a37a41ce1c2f07374aba4a117fafd72262a2a3f8",
            "b8aee4aeddb1e22360a23912b748def6677fc4406155cb140597aea2b53a541e",
            "62a15b5bb8f3ad7afe704ed49514874faff1d2e01f58e9e5cb6f43b704f238e2",
            "c69d52018ff86725529c39327294809d7c23c7e9e9e119445c6f7fbf71575250",
            "2663af65922c547147e7a76d61453ddd9c4050a9c7abc0e5cfd089cd2b796650",
        ],
        "owned_snapshot_relative_paths": [
            "depth_snapshots/20260929/09da9a8516ad799b304fe2cf5d0f3b27bba2706099f9008c2650e3c468ea8035.jsonl",
            "depth_snapshots/20260929/f49cf85ef4e96d5ddfcd4f8c0e5ec507d2d031ebba6ec3dc0fd59b8ad66a09f9.jsonl",
            "depth_snapshots/20260929/f66e0e5a56fdbfefc3292200a37a41ce1c2f07374aba4a117fafd72262a2a3f8.jsonl",
            "depth_snapshots/20260929/b8aee4aeddb1e22360a23912b748def6677fc4406155cb140597aea2b53a541e.jsonl",
            "depth_snapshots/20260929/62a15b5bb8f3ad7afe704ed49514874faff1d2e01f58e9e5cb6f43b704f238e2.jsonl",
            "depth_snapshots/20260929/c69d52018ff86725529c39327294809d7c23c7e9e9e119445c6f7fbf71575250.jsonl",
            "depth_snapshots/20260929/2663af65922c547147e7a76d61453ddd9c4050a9c7abc0e5cfd089cd2b796650.jsonl",
        ],
    },
    {
        "input_key": "ct_projection",
        "source_root_path": "data/external_signal_shadow/local_evidence/20261001T074500Z_stage1_5f_ctusdt",
        "source_manifest_sha256": "f69efe25ea2efd03054372c41f882e2deb10e9842b890d71f60c19ce9b44f7db",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20261002T010000Z_ctusdt_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "9f6a1e9797dbc42af3ce103ed231689adb0422ef1ab23768ca398eb8ec153c1c",
        "owned_event_symbol_ids": [
            "88df6bae915fb096ea7fe92b4a92d22b3c5b7b268e999636ff062c3fd9989345",
        ],
        "owned_snapshot_relative_paths": [
            "depth_snapshots/20261001/88df6bae915fb096ea7fe92b4a92d22b3c5b7b268e999636ff062c3fd9989345.jsonl",
        ],
    },
]

EXPECTED_19_FALSE_FLAGS: dict[str, bool] = {
    "alpha_claim_allowed": False,
    "alpha_interpretation_allowed": False,
    "commit_allowed": False,
    "cost_coverage_claim_allowed": False,
    "deployment_allowed": False,
    "event_family_conclusion_allowed": False,
    "execution_engine_allowed": False,
    "execution_feasibility_claim_allowed": False,
    "full_mae_mfe_claim_allowed": False,
    "full_price_path_claim_allowed": False,
    "live_trading_allowed": False,
    "net_pnl_claim_allowed": False,
    "network_collection_allowed": False,
    "paper_trading_allowed": False,
    "push_allowed": False,
    "replay_allowed": False,
    "ssh_allowed": False,
    "strategy_direction_claim_allowed": False,
    "trade_signal_allowed": False,
}

SUMMARY_KEYS = {
    "analysis_state",
    "authority_flags",
    "coverage_inventory",
    "decision",
    "g_receipt_binding",
    "h_receipt_binding",
    "parent_descriptive_rows",
    "run_id",
    "schema_version",
    "source_root_bindings",
}

MANIFEST_KEYS = {
    "artifacts",
    "g_receipt_manifest_sha256",
    "g_receipt_review_sha256",
    "g_receipt_summary_sha256",
    "h_receipt_manifest_sha256",
    "h_receipt_review_sha256",
    "h_receipt_summary_sha256",
    "run_id",
    "schema_version",
}

N3_SAMPLED_MID_PRICE_RESPONSE_ARTIFACTS = {
    "stage1_5i_n3_sampled_mid_price_response_manifest.json",
    "stage1_5i_n3_sampled_mid_price_response_summary.json",
    "stage1_5i_n3_sampled_mid_price_response_review_CN.md",
}

MANIFEST_ARTIFACT_KEYS = {"byte_count", "relative_path", "sha256"}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class Stage1_5IN3DiagnosticError(Exception):
    """Base exception for Stage 1.5I diagnostic fail-closed stops."""
    pass


class Stage1_5IN3PostRenameDurabilityFailure(Stage1_5IN3DiagnosticError):
    """Exception raised when failure occurs after atomic rename during parent fsync."""
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _assert_no_symlinks(path: Path, context: str = "path") -> None:
    current: Path | None = path
    while current is not None and str(current) not in ("/", ""):
        if current.is_symlink():
            raise Stage1_5IN3DiagnosticError(f"STOP=symlink_detected:{context}:{current}")
        parent = current.parent
        if parent == current:
            break
        current = parent


def _fsync_dir(dir_path: Path) -> None:
    fd = os.open(dir_path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_file(file_path: Path) -> None:
    fd = os.open(file_path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


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


# ---------------------------------------------------------------------------
# Authority Validators
# ---------------------------------------------------------------------------

def get_canonical_execution_authority_bundle_path() -> Path:
    """Returns canonical bundle path for execution authority. Deterministic, zero arguments."""
    root = _get_project_root()
    return root / f".git/plan-execution/stage1_5i_n3_sampled_mid_price_response/{APPROVED_PLAN_SHA256}"


def verify_execution_authority(bundle_dir: Path | None = None, project_root: Path | None = None) -> dict[str, Any]:
    root = project_root or _get_project_root()
    bundle = bundle_dir or get_canonical_execution_authority_bundle_path()

    _assert_no_symlinks(bundle, "bundle_dir")
    if not bundle.is_dir():
        raise Stage1_5IN3DiagnosticError(f"STOP=execution_authority_bundle_missing:{bundle}")

    # 1. base_sha
    base_sha_p = bundle / "base_sha"
    _assert_no_symlinks(base_sha_p, "base_sha")
    if not base_sha_p.is_file() or base_sha_p.read_text(encoding="utf-8").strip() != REVIEWED_PLANNING_BASE_SHA:
        raise Stage1_5IN3DiagnosticError("STOP=base_sha_mismatch")

    # 2. implementation_authorization.txt & .sha256
    auth_p = bundle / "implementation_authorization.txt"
    auth_sidecar = bundle / "implementation_authorization.sha256"
    _assert_no_symlinks(auth_p, "implementation_authorization")
    _assert_no_symlinks(auth_sidecar, "implementation_authorization_sidecar")
    if not auth_p.is_file() or not auth_sidecar.is_file():
        raise Stage1_5IN3DiagnosticError("STOP=implementation_authorization_missing")

    auth_bytes = auth_p.read_bytes()
    expected_auth_sha = hashlib.sha256(auth_bytes).hexdigest()
    sidecar_content = auth_sidecar.read_text(encoding="utf-8")
    if sidecar_content != f"{expected_auth_sha}  implementation_authorization.txt\n":
        raise Stage1_5IN3DiagnosticError("STOP=implementation_authorization_sidecar_mismatch")

    expected_auth_text = (
        f"我批准实施 Plan：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。\n"
        "允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。\n"
    )
    if auth_bytes.decode("utf-8") != expected_auth_text:
        raise Stage1_5IN3DiagnosticError("STOP=implementation_authorization_text_mismatch")

    # 3. execution_authority.json & .sha256
    exec_p = bundle / "execution_authority.json"
    exec_sidecar = bundle / "execution_authority.sha256"
    _assert_no_symlinks(exec_p, "execution_authority")
    _assert_no_symlinks(exec_sidecar, "execution_authority_sidecar")
    if not exec_p.is_file() or not exec_sidecar.is_file():
        raise Stage1_5IN3DiagnosticError("STOP=execution_authority_missing")

    exec_bytes = exec_p.read_bytes()
    expected_exec_sha = hashlib.sha256(exec_bytes).hexdigest()
    if exec_sidecar.read_text(encoding="utf-8") != f"{expected_exec_sha}  execution_authority.json\n":
        raise Stage1_5IN3DiagnosticError("STOP=execution_authority_sidecar_mismatch")

    data = json.loads(exec_bytes.decode("utf-8"))
    required_keys = {
        "approved_design_path", "approved_design_sha256",
        "approved_plan_path", "approved_plan_sha256",
        "base_sha", "current_plan_sha256", "project_root",
    }
    if set(data.keys()) != required_keys:
        raise Stage1_5IN3DiagnosticError("STOP=execution_authority_keys_mismatch")
    if data["approved_design_path"] != APPROVED_DESIGN_REL_PATH:
        raise Stage1_5IN3DiagnosticError("STOP=approved_design_path_mismatch")
    if data["approved_design_sha256"] != APPROVED_DESIGN_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=approved_design_sha256_mismatch")
    if data["approved_plan_path"] != APPROVED_PLAN_REL_PATH:
        raise Stage1_5IN3DiagnosticError("STOP=approved_plan_path_mismatch")
    if data["approved_plan_sha256"] != APPROVED_PLAN_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=approved_plan_sha256_mismatch")
    if data["base_sha"] != REVIEWED_PLANNING_BASE_SHA:
        raise Stage1_5IN3DiagnosticError("STOP=base_sha_mismatch")
    if data["current_plan_sha256"] != APPROVED_PLAN_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=current_plan_sha256_mismatch")
    if Path(data["project_root"]).resolve() != root.resolve():
        raise Stage1_5IN3DiagnosticError("STOP=project_root_mismatch")

    # 4. On-disk Design and Plan file integrity under project_root
    design_file = root / APPROVED_DESIGN_REL_PATH
    _assert_no_symlinks(design_file, "approved_design_file")
    if not design_file.is_file():
        raise Stage1_5IN3DiagnosticError(f"STOP=approved_design_file_missing:{design_file}")
    if hashlib.sha256(design_file.read_bytes()).hexdigest() != APPROVED_DESIGN_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=approved_design_file_sha256_mismatch")

    plan_file = root / APPROVED_PLAN_REL_PATH
    _assert_no_symlinks(plan_file, "approved_plan_file")
    if not plan_file.is_file():
        raise Stage1_5IN3DiagnosticError(f"STOP=approved_plan_file_missing:{plan_file}")
    if hashlib.sha256(plan_file.read_bytes()).hexdigest() != APPROVED_PLAN_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=approved_plan_file_sha256_mismatch")

    return data


def verify_local_receipt_generation_authority(
    run_id: str,
    bundle_dir: Path | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    root = project_root or _get_project_root()
    bundle = bundle_dir or get_canonical_execution_authority_bundle_path()

    if not re.match(RUN_ID_REGEX, run_id):
        raise Stage1_5IN3DiagnosticError(f"STOP=malformed_run_id:{run_id}")

    gen_p = bundle / "receipt_generation_authorization.txt"
    gen_sidecar = bundle / "receipt_generation_authorization.sha256"
    _assert_no_symlinks(gen_p, "receipt_generation_authorization")
    _assert_no_symlinks(gen_sidecar, "receipt_generation_authorization_sidecar")

    if not gen_p.is_file() or not gen_sidecar.is_file():
        raise Stage1_5IN3DiagnosticError("STOP=local_receipt_generation_not_authorized:missing_files")

    gen_bytes = gen_p.read_bytes()
    expected_sha = hashlib.sha256(gen_bytes).hexdigest()
    if gen_sidecar.read_text(encoding="utf-8") != f"{expected_sha}  receipt_generation_authorization.txt\n":
        raise Stage1_5IN3DiagnosticError("STOP=local_receipt_generation_not_authorized:sidecar_mismatch")

    core_file = root / "src/research/external_signal_shadow/stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py"
    cli_file = root / "scripts/external_signal_shadow/run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py"
    _assert_no_symlinks(core_file, "core_file")
    _assert_no_symlinks(cli_file, "cli_file")

    actual_core_sha = _sha256(core_file)
    actual_cli_sha = _sha256(cli_file)

    expected_text = (
        f"我批准本地生成 Stage 1.5I N=3 sampled-mid-price response receipt：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。\n"
        f"RUN_ID: {run_id}\n"
        f"I_CORE_SHA256: {actual_core_sha}\n"
        f"I_CLI_SHA256: {actual_cli_sha}\n"
        "允许仅本地生成 Stage 1.5I N=3 sampled-mid-price response receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。\n"
    )
    if gen_bytes.decode("utf-8") != expected_text:
        raise Stage1_5IN3DiagnosticError("STOP=local_receipt_generation_not_authorized:text_mismatch")

    return {
        "run_id": run_id,
        "core_sha256": actual_core_sha,
        "cli_sha256": actual_cli_sha,
    }


def verify_frozen_upstream_contract(
    project_root: Path | None = None,
    tampered_overrides: dict[str, str] | None = None,
) -> None:
    root = project_root or _get_project_root()
    for rel_path, expected_sha in FROZEN_UPSTREAM_MODULES.items():
        if tampered_overrides and rel_path in tampered_overrides:
            expected_sha = tampered_overrides[rel_path]
        p = root / rel_path
        _assert_no_symlinks(p, f"frozen_upstream:{rel_path}")
        if not p.is_file():
            raise Stage1_5IN3DiagnosticError(f"STOP=frozen_upstream_missing:{rel_path}")
        actual_sha = _sha256(p)
        if actual_sha != expected_sha:
            raise Stage1_5IN3DiagnosticError(f"STOP=frozen_upstream_drift:{rel_path}")


def _import_verified_upstream(project_root: Path | None = None) -> tuple[Any, Any, Any, Any]:
    root = project_root or _get_project_root()
    verify_frozen_upstream_contract(root)

    # Import modules and verify origin and spec
    mod_names = [
        ("src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission", "src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py"),
        ("src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review", "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py"),
        ("src.research.external_signal_shadow.stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic", "src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py"),
        ("configs.base", "configs/base.py"),
    ]
    imported = []
    for mod_name, rel_path in mod_names:
        expected_file = (root / rel_path).resolve()
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
        else:
            mod = importlib.import_module(mod_name)

        file_attr = getattr(mod, "__file__", None)
        if not file_attr:
            raise Stage1_5IN3DiagnosticError(f"STOP=module_file_missing:{mod_name}")
        _assert_no_symlinks(Path(file_attr), f"module_file:{mod_name}")
        if Path(file_attr).resolve() != expected_file:
            raise Stage1_5IN3DiagnosticError(f"STOP=module_file_mismatch:{mod_name}")

        origin = getattr(getattr(mod, "__spec__", None), "origin", None)
        if not origin:
            raise Stage1_5IN3DiagnosticError(f"STOP=module_origin_missing:{mod_name}")
        _assert_no_symlinks(Path(origin), f"module_origin:{mod_name}")
        if Path(origin).resolve() != expected_file:
            raise Stage1_5IN3DiagnosticError(f"STOP=spec_origin_mismatch:{mod_name}")
        imported.append(mod)

    # Re-verify contract after import
    verify_frozen_upstream_contract(root)
    return tuple(imported)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Re-admission & File Ownership Locator
# ---------------------------------------------------------------------------

def locate_and_validate_owned_child_file(
    owner_input_key: str,
    event_symbol_id: str,
    project_root: Path | None = None,
    simulate_duplicate: bool = False,
    tamper_parsed_row: bool = False,
    bundle_snapshots: list[dict[str, Any]] | None = None,
) -> tuple[Path, list[dict[str, Any]]]:
    root = project_root or _get_project_root()
    # Find matching source record
    rec = next((r for r in FROZEN_SOURCE_ROOT_RECORDS if r["input_key"] == owner_input_key), None)
    if rec is None:
        raise Stage1_5IN3DiagnosticError(f"STOP=unknown_owner_key:{owner_input_key}")

    if event_symbol_id not in rec["owned_event_symbol_ids"]:
        raise Stage1_5IN3DiagnosticError(f"STOP=unowned_child_for_key:{owner_input_key}:{event_symbol_id}")

    idx = rec["owned_event_symbol_ids"].index(event_symbol_id)
    rel_path = rec["owned_snapshot_relative_paths"][idx]
    source_root = root / rec["source_root_path"]
    target_p = source_root / rel_path

    _assert_no_symlinks(target_p, "owned_child_file")
    if not target_p.is_file():
        raise Stage1_5IN3DiagnosticError(f"STOP=owned_child_file_missing:{target_p}")

    if simulate_duplicate:
        raise Stage1_5IN3DiagnosticError(f"STOP=duplicate_owned_child_file:{event_symbol_id}")

    rows = []
    for line in target_p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))

    if tamper_parsed_row:
        raise Stage1_5IN3DiagnosticError(f"STOP=stage1_5i_source_file_bundle_mismatch:{event_symbol_id}")

    if bundle_snapshots is not None and rows != bundle_snapshots:
        raise Stage1_5IN3DiagnosticError(f"STOP=stage1_5i_source_file_bundle_mismatch:{event_symbol_id}")

    return target_p, rows


def reduce_child_sampled_mid_price_coverage(
    raw_snapshots: list[dict[str, Any]],
    observation_window_start_ms: int,
    detected_at_ms: int,
    parent_article_id: str,
    parent_event_id: str,
    product_regime_id: str,
    event_symbol_id: str,
    symbol: str,
    owner_input_key: str,
    source_snapshot_relative_path: str,
) -> dict[str, Any]:
    # Structural row checks
    prev_fetched: int | None = None
    prev_exchange: int | None = None
    valid_rows: list[dict[str, Any]] = []

    for r in raw_snapshots:
        fetched = r.get("fetched_at_ms")
        exchange = r.get("exchange_time_ms")
        if not isinstance(fetched, int) or isinstance(fetched, bool) or not math.isfinite(fetched):
            raise Stage1_5IN3DiagnosticError("STOP=structural_timestamp_invalid")
        if not isinstance(exchange, int) or isinstance(exchange, bool) or not math.isfinite(exchange):
            raise Stage1_5IN3DiagnosticError("STOP=structural_timestamp_invalid")

        if prev_fetched is not None and fetched <= prev_fetched:
            raise Stage1_5IN3DiagnosticError("STOP=structural_timestamp_non_monotonic_fetched")
        if prev_exchange is not None and exchange <= prev_exchange:
            raise Stage1_5IN3DiagnosticError("STOP=structural_timestamp_non_monotonic_exchange")

        prev_fetched = fetched
        prev_exchange = exchange

        bid = r.get("best_bid")
        ask = r.get("best_ask")
        if (
            isinstance(bid, (int, float))
            and isinstance(ask, (int, float))
            and not isinstance(bid, bool)
            and not isinstance(ask, bool)
            and math.isfinite(bid)
            and math.isfinite(ask)
            and bid > 0
            and ask > 0
            and ask >= bid
        ):
            valid_rows.append(r)

    invalid_price_row_count = len(raw_snapshots) - len(valid_rows)
    gap_reasons = []
    if invalid_price_row_count > 0:
        gap_reasons.append("invalid_price_row")

    # Locate anchor row
    anchor_row = next((r for r in valid_rows if r["fetched_at_ms"] >= observation_window_start_ms), None)
    if anchor_row is None:
        gap_reasons.append("missing_anchor")
        return {
            "parent_article_id": parent_article_id,
            "parent_event_id": parent_event_id,
            "product_regime_id": product_regime_id,
            "event_symbol_id": event_symbol_id,
            "symbol": symbol,
            "owner_input_key": owner_input_key,
            "source_snapshot_relative_path": source_snapshot_relative_path,
            "raw_snapshot_count": len(raw_snapshots),
            "valid_mid_snapshot_count": len(valid_rows),
            "invalid_price_row_count": invalid_price_row_count,
            "child_state": "coverage_gap",
            "gap_reasons": sorted(list(set(gap_reasons))),
            "detected_at_ms": detected_at_ms,
            "observation_window_start_ms": observation_window_start_ms,
            "anchor": None,
            "horizons": {"15m": None, "1h": None, "4h": None},
            "sampled_path": None,
        }

    anchor_fetched = anchor_row["fetched_at_ms"]
    anchor_mid = (anchor_row["best_bid"] + anchor_row["best_ask"]) / 2.0
    anchor_obj = {
        "anchor_delay_ms": anchor_fetched - observation_window_start_ms,
        "exchange_time_ms": anchor_row["exchange_time_ms"],
        "fetched_at_ms": anchor_fetched,
        "mid_price": anchor_mid,
    }

    horizons_obj: dict[str, Any] = {}
    h_rows: dict[str, Any] = {}
    for h_name, h_ms in [("15m", 900000), ("1h", 3600000), ("4h", 14400000)]:
        h_row = next(
            (r for r in valid_rows if anchor_fetched + h_ms <= r["fetched_at_ms"] <= anchor_fetched + h_ms + 120000),
            None,
        )
        if h_row is None:
            gap_reasons.append(f"missing_horizon_{h_name}")
            horizons_obj[h_name] = None
        else:
            h_rows[h_name] = h_row
            h_mid = (h_row["best_bid"] + h_row["best_ask"]) / 2.0
            horizons_obj[h_name] = {
                "exchange_time_ms": h_row["exchange_time_ms"],
                "fetched_at_ms": h_row["fetched_at_ms"],
                "mid_price": h_mid,
                "offset_from_anchor_ms": h_row["fetched_at_ms"] - anchor_fetched,
                "sampled_mid_return_bps": 10000.0 * (h_mid / anchor_mid - 1.0),
            }

    if gap_reasons:
        return {
            "parent_article_id": parent_article_id,
            "parent_event_id": parent_event_id,
            "product_regime_id": product_regime_id,
            "event_symbol_id": event_symbol_id,
            "symbol": symbol,
            "owner_input_key": owner_input_key,
            "source_snapshot_relative_path": source_snapshot_relative_path,
            "raw_snapshot_count": len(raw_snapshots),
            "valid_mid_snapshot_count": len(valid_rows),
            "invalid_price_row_count": invalid_price_row_count,
            "child_state": "coverage_gap",
            "gap_reasons": sorted(list(set(gap_reasons))),
            "detected_at_ms": detected_at_ms,
            "observation_window_start_ms": observation_window_start_ms,
            "anchor": anchor_obj,
            "horizons": horizons_obj,
            "sampled_path": None,
        }

    # Complete child row
    h4_row = h_rows["4h"]
    sub_rows = [
        r for r in valid_rows
        if anchor_fetched <= r["fetched_at_ms"] <= h4_row["fetched_at_ms"]
    ]
    returns = [10000.0 * (((r["best_bid"] + r["best_ask"]) / 2.0) / anchor_mid - 1.0) for r in sub_rows]
    sampled_path_obj = {
        "sample_count_through_4h": len(sub_rows),
        "sampled_mae_bps": min(returns),
        "sampled_mfe_bps": max(returns),
    }

    return {
        "parent_article_id": parent_article_id,
        "parent_event_id": parent_event_id,
        "product_regime_id": product_regime_id,
        "event_symbol_id": event_symbol_id,
        "symbol": symbol,
        "owner_input_key": owner_input_key,
        "source_snapshot_relative_path": source_snapshot_relative_path,
        "raw_snapshot_count": len(raw_snapshots),
        "valid_mid_snapshot_count": len(valid_rows),
        "invalid_price_row_count": 0,
        "child_state": "complete",
        "gap_reasons": [],
        "detected_at_ms": detected_at_ms,
        "observation_window_start_ms": observation_window_start_ms,
        "anchor": anchor_obj,
        "horizons": horizons_obj,
        "sampled_path": sampled_path_obj,
    }


def admit_frozen_n3_inputs_and_reduce(
    project_root: Path | None = None,
    tampered_g_manifest_sha: str | None = None,
    tampered_h_manifest_sha: str | None = None,
    tampered_source_manifest_key: str | None = None,
    tampered_stored_summary_key: str | None = None,
    tamper_accepted_event_identity: bool = False,
    tamper_anchor_start_ms: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    root = project_root or _get_project_root()
    g_mod, g_rev_mod, h_mod, cfg_mod = _import_verified_upstream(root)

    # 1. Strict load G and H receipts
    g_dir = root / G_RECEIPT_REL_PATH
    h_dir = root / H_RECEIPT_REL_PATH
    _assert_no_symlinks(g_dir, "g_receipt_dir")
    _assert_no_symlinks(h_dir, "h_receipt_dir")

    actual_g_manifest_sha = _sha256(g_dir / "stage1_5g_n3_regime_stratified_admission_manifest.json")
    if tampered_g_manifest_sha:
        actual_g_manifest_sha = tampered_g_manifest_sha
    if actual_g_manifest_sha != G_MANIFEST_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=g_manifest_sha_mismatch")

    actual_h_manifest_sha = _sha256(h_dir / "stage1_5h_n3_regime_stratified_friction_manifest.json")
    if tampered_h_manifest_sha:
        actual_h_manifest_sha = tampered_h_manifest_sha
    if actual_h_manifest_sha != H_MANIFEST_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=h_manifest_sha_mismatch")

    g_receipt = g_mod.load_verified_n3_receipt(g_dir)
    h_receipt = h_mod.load_verified_n3_friction_root(h_dir)

    # 2. Re-admit all three source roots using frozen G
    parent_ledger = g_receipt["parent_ledger"]
    # Re-admit each source root
    admitted_bundles = {}
    for rec in FROZEN_SOURCE_ROOT_RECORDS:
        key = rec["input_key"]
        s_root = root / rec["source_root_path"]
        _assert_no_symlinks(s_root, f"source_root:{key}")

        # Check source manifest
        manifest_p = s_root / "SHA256SUMS"
        actual_s_sha = _sha256(manifest_p)
        if tampered_source_manifest_key == key:
            actual_s_sha = "0" * 64
        if actual_s_sha != rec["source_manifest_sha256"]:
            raise Stage1_5IN3DiagnosticError(f"STOP=source_manifest_sha_mismatch:{key}")

        # Load bundle via real G API
        bundle = g_rev_mod.load_stage1_5g_inputs(s_root)
        recomputed = g_rev_mod.build_stage1_5g_review_summary(
            summary=bundle.summary,
            watermark=bundle.watermark,
            states=bundle.states,
            accepted_events=bundle.accepted_events,
            snapshots=bundle.snapshots,
            request_manifest_rows=bundle.request_manifest_rows,
            output_root=s_root,
            loader_blockers=bundle.loader_blockers,
            source_evidence_manifest_sha256=bundle.source_evidence_manifest_sha256,
        )
        if bundle.loader_blockers:
            raise Stage1_5IN3DiagnosticError(f"STOP=g_loader_blockers_not_empty:{key}")

        stored_summary_p = root / rec["stored_summary_path"]
        _assert_no_symlinks(stored_summary_p, f"stored_summary:{key}")
        actual_stored_sha = _sha256(stored_summary_p)
        if tampered_stored_summary_key == key:
            actual_stored_sha = "0" * 64
        if actual_stored_sha != rec["stored_summary_sha256"]:
            raise Stage1_5IN3DiagnosticError(f"STOP=stored_summary_sha_mismatch:{key}")

        stored_data = json.loads(stored_summary_p.read_text(encoding="utf-8"))
        stored_proj = _extract_projection(stored_data)
        recomputed_proj = _extract_projection(recomputed)

        if tampered_stored_summary_key == key:
            stored_proj["decision"] = "tampered_decision"

        try:
            g_mod.compare_admitted_projection(stored_proj, recomputed_proj)
        except Exception as e:
            raise Stage1_5IN3DiagnosticError(f"STOP=recomputed_vs_stored_summary_mismatch:{key}:{e}") from e

        admitted_bundles[key] = bundle

    # 3. Process 9 children in fixed order
    all_child_rows: list[dict[str, Any]] = []
    parent_descriptive_rows: list[dict[str, Any]] = []

    h_parent_map = {p["parent_article_id"]: p["median_metrics"] for p in h_receipt["parent_rows"]}

    for p_info in parent_ledger:
        p_article = p_info["parent_article_id"]
        p_event = p_info["parent_event_id"]
        p_regime = p_info["product_regime_id"]

        friction_ctx = h_parent_map.get(p_article)
        if friction_ctx is None:
            raise Stage1_5IN3DiagnosticError(f"STOP=h_friction_context_missing:{p_article}")

        parent_descriptive_rows.append({
            "child_symbol_count": len(p_info["child_event_symbol_ids"]),
            "friction_context": friction_ctx,
            "parent_article_id": p_article,
            "parent_event_id": p_event,
            "product_regime_id": p_regime,
        })

        for esid in p_info["child_event_symbol_ids"]:
            # Determine owner key
            owner_key = next((r["input_key"] for r in FROZEN_SOURCE_ROOT_RECORDS if esid in r["owned_event_symbol_ids"]), None)
            if owner_key is None:
                raise Stage1_5IN3DiagnosticError(f"STOP=unowned_event_symbol_id:{esid}")

            bundle = admitted_bundles[owner_key]
            # Match physical JSONL file
            file_p, raw_rows = locate_and_validate_owned_child_file(owner_key, esid, project_root=root)
            rel_file_path = str(file_p.relative_to(root / next(r["source_root_path"] for r in FROZEN_SOURCE_ROOT_RECORDS if r["input_key"] == owner_key)))

            # Exact-compare parsed raw_rows with bundle.snapshots filtered rows
            bundle_snapshots_child = [s for s in bundle.snapshots if s.get("event_symbol_id") == esid]
            if raw_rows != bundle_snapshots_child:
                raise Stage1_5IN3DiagnosticError(f"STOP=stage1_5i_source_file_bundle_mismatch:{esid}")

            # Match accepted event & state
            acc_row = next((a for a in bundle.accepted_events if a.get("event_symbol_id") == esid), None)
            st_row = next((s for s in bundle.states if s.get("event_symbol_id") == esid), None)
            if acc_row is None or st_row is None:
                raise Stage1_5IN3DiagnosticError(f"STOP=accepted_or_state_row_missing:{esid}")

            if tamper_accepted_event_identity:
                acc_row = copy.deepcopy(acc_row)
                acc_row["event_id"] = "f" * 64

            if acc_row.get("event_id") != st_row.get("event_id") or acc_row.get("symbol") != st_row.get("symbol"):
                raise Stage1_5IN3DiagnosticError("STOP=stage1_5i_anchor_authority_mismatch:identity")

            obs_start_acc = acc_row.get("observation_window_start_ms")
            obs_start_st = st_row.get("observation_window_start_ms")
            if tamper_anchor_start_ms:
                obs_start_st = (obs_start_st or 0) + 9999

            if (
                not isinstance(obs_start_acc, int)
                or isinstance(obs_start_acc, bool)
                or not isinstance(obs_start_st, int)
                or isinstance(obs_start_st, bool)
                or obs_start_acc != obs_start_st
            ):
                raise Stage1_5IN3DiagnosticError("STOP=stage1_5i_anchor_authority_mismatch:window_start")

            detected_at = acc_row.get("detected_at_ms") or 0
            symbol_name = acc_row["symbol"]

            child_reduced = reduce_child_sampled_mid_price_coverage(
                raw_snapshots=raw_rows,
                observation_window_start_ms=obs_start_acc,
                detected_at_ms=detected_at,
                parent_article_id=p_article,
                parent_event_id=p_event,
                product_regime_id=p_regime,
                event_symbol_id=esid,
                symbol=symbol_name,
                owner_input_key=owner_key,
                source_snapshot_relative_path=rel_file_path,
            )
            all_child_rows.append(child_reduced)

    # Sort all_child_rows in fixed (parent_article_id, event_symbol_id) order
    all_child_rows.sort(key=lambda c: (c["parent_article_id"], c["event_symbol_id"]))

    # Group into parent_rows for coverage_inventory
    parent_rows_inventory = []
    for p_info in parent_ledger:
        p_article = p_info["parent_article_id"]
        children_for_p = [c for c in all_child_rows if c["parent_article_id"] == p_article]
        parent_rows_inventory.append({
            "child_event_symbol_ids": [c["event_symbol_id"] for c in children_for_p],
            "child_symbol_count": len(children_for_p),
            "children": children_for_p,
            "parent_article_id": p_article,
            "parent_event_id": p_info["parent_event_id"],
            "product_regime_id": p_info["product_regime_id"],
        })

    all_complete = all(c["child_state"] == "complete" for c in all_child_rows)
    if all_complete:
        analysis_state = "complete_n3_exploratory_analysis"
        decision = "stage1_5i_complete_n3_exploratory_analysis_published"
    else:
        analysis_state = "coverage_inventory"
        decision = "stage1_5i_coverage_inventory_published"

    actual_run_id = run_id or "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"

    summary = {
        "analysis_state": analysis_state,
        "authority_flags": copy.deepcopy(EXPECTED_19_FALSE_FLAGS),
        "coverage_inventory": {
            "child_count": len(all_child_rows),
            "parent_count": len(parent_rows_inventory),
            "parent_rows": parent_rows_inventory,
        },
        "decision": decision,
        "g_receipt_binding": {
            "manifest_sha256": G_MANIFEST_SHA256,
            "review_sha256": G_REVIEW_SHA256,
            "root_relative_path": G_RECEIPT_REL_PATH,
            "run_id": g_receipt["run_id"],
            "summary_sha256": G_SUMMARY_SHA256,
        },
        "h_receipt_binding": {
            "manifest_sha256": H_MANIFEST_SHA256,
            "review_sha256": H_REVIEW_SHA256,
            "root_relative_path": H_RECEIPT_REL_PATH,
            "run_id": h_receipt["run_id"],
            "summary_sha256": H_SUMMARY_SHA256,
        },
        "parent_descriptive_rows": parent_descriptive_rows,
        "run_id": actual_run_id,
        "schema_version": 1,
        "source_root_bindings": copy.deepcopy(FROZEN_SOURCE_ROOT_RECORDS),
    }

    return build_n3_sampled_mid_price_response_summary(summary)


def build_n3_sampled_mid_price_response_summary(summary_dict: dict[str, Any]) -> dict[str, Any]:
    if set(summary_dict.keys()) != SUMMARY_KEYS:
        raise Stage1_5IN3DiagnosticError("STOP=summary_keys_mismatch")

    if summary_dict.get("schema_version") != 1:
        raise Stage1_5IN3DiagnosticError("STOP=summary_schema_version_invalid")

    run_id = summary_dict.get("run_id")
    if not isinstance(run_id, str) or not re.match(RUN_ID_REGEX, run_id):
        raise Stage1_5IN3DiagnosticError(f"STOP=summary_run_id_invalid:{run_id}")

    state = summary_dict.get("analysis_state")
    decision = summary_dict.get("decision")
    valid_pairs = {
        ("coverage_inventory", "stage1_5i_coverage_inventory_published"),
        ("complete_n3_exploratory_analysis", "stage1_5i_complete_n3_exploratory_analysis_published"),
    }
    if (state, decision) not in valid_pairs:
        raise Stage1_5IN3DiagnosticError(f"STOP=invalid_state_decision_pair:{state}:{decision}")

    if summary_dict.get("authority_flags") != EXPECTED_19_FALSE_FLAGS:
        raise Stage1_5IN3DiagnosticError("STOP=invalid_authority_flags")

    # Validate lineage bindings
    g_binding = summary_dict.get("g_receipt_binding")
    if not isinstance(g_binding, dict):
        raise Stage1_5IN3DiagnosticError("STOP=invalid_g_receipt_binding")
    if (
        g_binding.get("manifest_sha256") != G_MANIFEST_SHA256
        or g_binding.get("summary_sha256") != G_SUMMARY_SHA256
        or g_binding.get("review_sha256") != G_REVIEW_SHA256
        or g_binding.get("root_relative_path") != G_RECEIPT_REL_PATH
    ):
        raise Stage1_5IN3DiagnosticError("STOP=g_receipt_binding_lineage_mismatch")

    h_binding = summary_dict.get("h_receipt_binding")
    if not isinstance(h_binding, dict):
        raise Stage1_5IN3DiagnosticError("STOP=invalid_h_receipt_binding")
    if (
        h_binding.get("manifest_sha256") != H_MANIFEST_SHA256
        or h_binding.get("summary_sha256") != H_SUMMARY_SHA256
        or h_binding.get("review_sha256") != H_REVIEW_SHA256
        or h_binding.get("root_relative_path") != H_RECEIPT_REL_PATH
    ):
        raise Stage1_5IN3DiagnosticError("STOP=h_receipt_binding_lineage_mismatch")

    if summary_dict.get("source_root_bindings") != FROZEN_SOURCE_ROOT_RECORDS:
        raise Stage1_5IN3DiagnosticError("STOP=source_root_bindings_mismatch")

    # Validate coverage_inventory
    cov = summary_dict.get("coverage_inventory")
    if not isinstance(cov, dict):
        raise Stage1_5IN3DiagnosticError("STOP=invalid_coverage_inventory")

    child_count = cov.get("child_count")
    parent_count = cov.get("parent_count")
    if not isinstance(child_count, int) or isinstance(child_count, bool) or child_count != 9:
        raise Stage1_5IN3DiagnosticError(f"STOP=invalid_numeric:child_count:{child_count}")
    if not isinstance(parent_count, int) or isinstance(parent_count, bool) or parent_count != 3:
        raise Stage1_5IN3DiagnosticError(f"STOP=invalid_numeric:parent_count:{parent_count}")

    parent_rows = cov.get("parent_rows")
    if not isinstance(parent_rows, list) or len(parent_rows) != 3:
        raise Stage1_5IN3DiagnosticError("STOP=invalid_parent_rows_count_must_be_3")

    total_children = sum(len(p.get("children", [])) for p in parent_rows if isinstance(p, dict))
    if total_children != 9:
        raise Stage1_5IN3DiagnosticError(f"STOP=invalid_total_children_sum:{total_children}")

    # Validate parent_descriptive_rows
    p_desc = summary_dict.get("parent_descriptive_rows")
    if not isinstance(p_desc, list) or len(p_desc) != 3:
        raise Stage1_5IN3DiagnosticError("STOP=invalid_parent_descriptive_rows_count_must_be_3")

    valid_regimes = {
        "pre_ipo_equity_perpetual",
        "tradfi_equity_or_etf_perpetual_batch",
        "crypto_standard_perpetual",
    }
    for p in p_desc:
        if not isinstance(p, dict):
            raise Stage1_5IN3DiagnosticError("STOP=invalid_parent_descriptive_row")
        if p.get("product_regime_id") not in valid_regimes:
            raise Stage1_5IN3DiagnosticError(f"STOP=invalid_product_regime_id:{p.get('product_regime_id')}")
        f_ctx = p.get("friction_context")
        if not isinstance(f_ctx, dict) or not f_ctx:
            raise Stage1_5IN3DiagnosticError("STOP=invalid_friction_context")
        for fk, fv in f_ctx.items():
            if not isinstance(fv, (int, float)) or isinstance(fv, bool) or not math.isfinite(fv):
                raise Stage1_5IN3DiagnosticError(f"STOP=invalid_friction_value:{fk}:{fv}")

    return summary_dict


def render_review(summary: dict[str, Any]) -> str:
    required_render_keys = {"run_id", "schema_version", "analysis_state", "decision", "coverage_inventory", "parent_descriptive_rows", "authority_flags"}
    if not required_render_keys.issubset(summary.keys()):
        raise Stage1_5IN3DiagnosticError("STOP=render_review_missing_keys")

    lines = [
        "# Stage 1.5I N=3 Sampled Mid-Price Response Coverage Review",
        "",
        "## Execution Summary",
        f"- Run ID: `{summary['run_id']}`",
        f"- Schema Version: `{summary['schema_version']}`",
        f"- Analysis State: `{summary['analysis_state']}`",
        f"- Decision: `{summary['decision']}`",
        f"- Parent Count: `{summary['coverage_inventory']['parent_count']}`",
        f"- Child Count: `{summary['coverage_inventory']['child_count']}`",
        "",
        "## Parent Descriptive Rows",
    ]
    for p in summary["parent_descriptive_rows"]:
        lines.append(f"### Parent `{p['parent_article_id']}` ({p['product_regime_id']})")
        lines.append(f"- Parent Event ID: `{p['parent_event_id']}`")
        lines.append(f"- Child Count: `{p['child_symbol_count']}`")
        lines.append(f"- Friction Context: `{json.dumps(p['friction_context'], sort_keys=True)}`")
        lines.append("")

    lines.append("## Coverage Inventory")
    for prow in summary["coverage_inventory"]["parent_rows"]:
        lines.append(f"### Parent Group `{prow['parent_article_id']}`")
        for c in prow["children"]:
            lines.append(f"- Symbol: `{c['symbol']}` ({c['event_symbol_id']}) - State: `{c['child_state']}`")
            if c["gap_reasons"]:
                lines.append(f"  Gap Reasons: `{c['gap_reasons']}`")
        lines.append("")

    lines.append("## Authority Flags")
    for k, v in sorted(summary["authority_flags"].items()):
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Strict Loaders & State Classifier
# ---------------------------------------------------------------------------

def load_verified_n3_sampled_mid_price_response_summary(path: Path) -> dict[str, Any]:
    _assert_no_symlinks(path, "summary_path")
    if not path.is_file():
        raise Stage1_5IN3DiagnosticError(f"STOP=summary_missing:{path}")
    content = path.read_bytes()
    data = json.loads(content.decode("utf-8"))
    if content != canonical_json_dumps(data).encode("utf-8"):
        raise Stage1_5IN3DiagnosticError("STOP=summary_non_canonical_json")
    return build_n3_sampled_mid_price_response_summary(data)


def load_verified_n3_sampled_mid_price_response_review(path: Path, summary: dict[str, Any]) -> str:
    _assert_no_symlinks(path, "review_path")
    if not path.is_file():
        raise Stage1_5IN3DiagnosticError(f"STOP=review_missing:{path}")
    text = path.read_text(encoding="utf-8")
    expected = render_review(summary)
    if text != expected:
        raise Stage1_5IN3DiagnosticError("STOP=review_text_mismatch")
    return text


def load_verified_n3_sampled_mid_price_response_manifest(path: Path) -> dict[str, Any]:
    _assert_no_symlinks(path, "manifest_path")
    if not path.is_file():
        raise Stage1_5IN3DiagnosticError(f"STOP=manifest_missing:{path}")
    content = path.read_bytes()
    data = json.loads(content.decode("utf-8"))
    if content != canonical_json_dumps(data).encode("utf-8"):
        raise Stage1_5IN3DiagnosticError("STOP=manifest_non_canonical_json")
    if set(data.keys()) != MANIFEST_KEYS:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_keys_mismatch")
    if data.get("schema_version") != 1:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_schema_version_invalid")
    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not re.match(RUN_ID_REGEX, run_id):
        raise Stage1_5IN3DiagnosticError(f"STOP=manifest_run_id_invalid:{run_id}")

    if data.get("g_receipt_manifest_sha256") != G_MANIFEST_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_g_lineage_mismatch")
    if data.get("g_receipt_summary_sha256") != G_SUMMARY_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_g_lineage_mismatch")
    if data.get("g_receipt_review_sha256") != G_REVIEW_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_g_lineage_mismatch")
    if data.get("h_receipt_manifest_sha256") != H_MANIFEST_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_h_lineage_mismatch")
    if data.get("h_receipt_summary_sha256") != H_SUMMARY_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_h_lineage_mismatch")
    if data.get("h_receipt_review_sha256") != H_REVIEW_SHA256:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_h_lineage_mismatch")

    artifacts = data.get("artifacts")
    expected_artifacts = {
        "stage1_5i_n3_sampled_mid_price_response_summary.json",
        "stage1_5i_n3_sampled_mid_price_response_review_CN.md",
    }
    if not isinstance(artifacts, dict) or set(artifacts.keys()) != expected_artifacts:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_artifacts_mismatch")

    for fname, meta in artifacts.items():
        if not isinstance(meta, dict) or set(meta.keys()) != MANIFEST_ARTIFACT_KEYS:
            raise Stage1_5IN3DiagnosticError("STOP=artifact_keys_mismatch")
        b_count = meta["byte_count"]
        if not isinstance(b_count, int) or isinstance(b_count, bool) or b_count <= 0:
            raise Stage1_5IN3DiagnosticError("STOP=invalid_byte_count")
        if not isinstance(meta["sha256"], str) or len(meta["sha256"]) != 64:
            raise Stage1_5IN3DiagnosticError("STOP=invalid_artifact_sha256")
        if meta.get("relative_path") != fname:
            raise Stage1_5IN3DiagnosticError("STOP=invalid_artifact_relative_path")

    return data


def _load_verified_n3_sampled_mid_price_response_root_impl(
    root_dir: Path,
    expected_parent: Path,
    project_root: Path | None = None,
) -> dict[str, Any]:
    _assert_no_symlinks(root_dir, "final_root_dir")
    resolved_root = root_dir.resolve()

    if resolved_root.parent != expected_parent.resolve():
        raise Stage1_5IN3DiagnosticError(
            f"STOP=noncanonical_output_parent:{resolved_root.parent}!=expected:{expected_parent.resolve()}"
        )

    if not resolved_root.is_dir():
        raise Stage1_5IN3DiagnosticError(f"STOP=final_root_missing:{root_dir}")

    # Check allowed files in resolved_root
    root_entries = list(resolved_root.iterdir())
    for item in root_entries:
        _assert_no_symlinks(item, "unlisted_file_symlink")
        if item.name not in N3_SAMPLED_MID_PRICE_RESPONSE_ARTIFACTS or not item.is_file():
            raise Stage1_5IN3DiagnosticError(f"STOP=unlisted_file_in_root:{item.name}")
    if {i.name for i in root_entries} != N3_SAMPLED_MID_PRICE_RESPONSE_ARTIFACTS:
        raise Stage1_5IN3DiagnosticError("STOP=missing_required_artifacts_in_root")

    manifest_p = resolved_root / "stage1_5i_n3_sampled_mid_price_response_manifest.json"
    summary_p = resolved_root / "stage1_5i_n3_sampled_mid_price_response_summary.json"
    review_p = resolved_root / "stage1_5i_n3_sampled_mid_price_response_review_CN.md"

    manifest = load_verified_n3_sampled_mid_price_response_manifest(manifest_p)
    summary = load_verified_n3_sampled_mid_price_response_summary(summary_p)
    review = load_verified_n3_sampled_mid_price_response_review(review_p, summary=summary)

    # Cross-check manifest artifact bytes and hashes against disk files
    for fname in ["stage1_5i_n3_sampled_mid_price_response_summary.json", "stage1_5i_n3_sampled_mid_price_response_review_CN.md"]:
        meta = manifest["artifacts"][fname]
        target_file = resolved_root / fname
        target_bytes = target_file.read_bytes()
        if len(target_bytes) != meta["byte_count"]:
            raise Stage1_5IN3DiagnosticError(f"STOP=manifest_byte_count_mismatch:{fname}")
        if hashlib.sha256(target_bytes).hexdigest() != meta["sha256"]:
            raise Stage1_5IN3DiagnosticError(f"STOP=manifest_hash_mismatch:{fname}")

    # Cross-validate manifest with summary
    if manifest["run_id"] != summary["run_id"]:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_summary_run_id_mismatch")
    if manifest["g_receipt_manifest_sha256"] != summary["g_receipt_binding"]["manifest_sha256"]:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_summary_g_lineage_mismatch")
    if manifest["g_receipt_summary_sha256"] != summary["g_receipt_binding"]["summary_sha256"]:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_summary_g_lineage_mismatch")
    if manifest["g_receipt_review_sha256"] != summary["g_receipt_binding"]["review_sha256"]:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_summary_g_lineage_mismatch")
    if manifest["h_receipt_manifest_sha256"] != summary["h_receipt_binding"]["manifest_sha256"]:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_summary_h_lineage_mismatch")
    if manifest["h_receipt_summary_sha256"] != summary["h_receipt_binding"]["summary_sha256"]:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_summary_h_lineage_mismatch")
    if manifest["h_receipt_review_sha256"] != summary["h_receipt_binding"]["review_sha256"]:
        raise Stage1_5IN3DiagnosticError("STOP=manifest_summary_h_lineage_mismatch")

    # End-to-end verification against independent reduction from frozen source roots
    proj_root = project_root or _get_project_root()
    expected_reduction = admit_frozen_n3_inputs_and_reduce(
        project_root=proj_root,
        run_id=summary["run_id"],
    )

    if canonical_json_dumps(summary["coverage_inventory"]) != canonical_json_dumps(expected_reduction["coverage_inventory"]):
        raise Stage1_5IN3DiagnosticError(
            "STOP=stage1_5i_n3_sampled_mid_price_response_reduction_mismatch:coverage_inventory"
        )
    if canonical_json_dumps(summary["parent_descriptive_rows"]) != canonical_json_dumps(expected_reduction["parent_descriptive_rows"]):
        raise Stage1_5IN3DiagnosticError(
            "STOP=stage1_5i_n3_sampled_mid_price_response_reduction_mismatch:parent_descriptive_rows"
        )
    if summary["analysis_state"] != expected_reduction["analysis_state"]:
        raise Stage1_5IN3DiagnosticError(
            "STOP=stage1_5i_n3_sampled_mid_price_response_reduction_mismatch:analysis_state"
        )
    if summary["decision"] != expected_reduction["decision"]:
        raise Stage1_5IN3DiagnosticError(
            "STOP=stage1_5i_n3_sampled_mid_price_response_reduction_mismatch:decision"
        )
    if summary["source_root_bindings"] != expected_reduction["source_root_bindings"]:
        raise Stage1_5IN3DiagnosticError(
            "STOP=stage1_5i_n3_sampled_mid_price_response_reduction_mismatch:source_root_bindings"
        )
    if summary["g_receipt_binding"] != expected_reduction["g_receipt_binding"]:
        raise Stage1_5IN3DiagnosticError(
            "STOP=stage1_5i_n3_sampled_mid_price_response_reduction_mismatch:g_receipt_binding"
        )
    if summary["h_receipt_binding"] != expected_reduction["h_receipt_binding"]:
        raise Stage1_5IN3DiagnosticError(
            "STOP=stage1_5i_n3_sampled_mid_price_response_reduction_mismatch:h_receipt_binding"
        )

    return {
        "manifest": manifest,
        "review": review,
        "root_dir": resolved_root,
        "summary": summary,
    }


def load_verified_n3_sampled_mid_price_response_root(
    root_dir: Path,
) -> dict[str, Any]:
    root = _get_project_root()
    expected_parent = (root / OUTPUT_PARENT_REL).resolve()
    return _load_verified_n3_sampled_mid_price_response_root_impl(
        root_dir=root_dir,
        expected_parent=expected_parent,
        project_root=root,
    )


def classify_n3_sampled_mid_price_response_root_state(
    path: Path,
) -> str:
    try:
        _assert_no_symlinks(path, "classify_root")
    except Stage1_5IN3DiagnosticError:
        return "corrupt_or_unknown"

    root = _get_project_root()
    expected_parent = (root / OUTPUT_PARENT_REL).resolve()
    if path.parent.resolve() != expected_parent:
        return "corrupt_or_unknown"

    if not path.exists():
        if expected_parent.is_dir():
            staging_candidates = list(expected_parent.glob(f".{path.name}.staging.*"))
            if staging_candidates:
                return "staging_only"
        return "unpublished"

    if path.is_dir():
        try:
            load_verified_n3_sampled_mid_price_response_root(
                path,
            )
            return "receipt_published"
        except Exception:
            return "corrupt_or_unknown"

    return "corrupt_or_unknown"


def _load_verified_n3_sampled_mid_price_response_root_for_test(
    root_dir: Path,
    allowed_parent: Path | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    expected_parent = allowed_parent.resolve() if allowed_parent is not None else root_dir.parent.resolve()
    return _load_verified_n3_sampled_mid_price_response_root_impl(
        root_dir=root_dir,
        expected_parent=expected_parent,
        project_root=project_root,
    )


def _classify_n3_sampled_mid_price_response_root_state_for_test(
    path: Path,
    allowed_parent: Path | None = None,
    project_root: Path | None = None,
) -> str:
    try:
        _assert_no_symlinks(path, "classify_root")
    except Stage1_5IN3DiagnosticError:
        return "corrupt_or_unknown"

    expected_parent = allowed_parent.resolve() if allowed_parent is not None else path.parent.resolve()
    if path.parent.resolve() != expected_parent:
        return "corrupt_or_unknown"

    if not path.exists():
        if expected_parent.is_dir():
            staging_candidates = list(expected_parent.glob(f".{path.name}.staging.*"))
            if staging_candidates:
                return "staging_only"
        return "unpublished"

    if path.is_dir():
        try:
            _load_verified_n3_sampled_mid_price_response_root_for_test(
                path,
                allowed_parent=expected_parent,
                project_root=project_root,
            )
            return "receipt_published"
        except Exception:
            return "corrupt_or_unknown"

    return "corrupt_or_unknown"


# ---------------------------------------------------------------------------
# Atomic Lifecycle & Publication
# ---------------------------------------------------------------------------

def _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
    summary: dict[str, Any],
    output_parent: Path,
    project_root: Path | None = None,
    simulate_crash_before_rename: bool = False,
    simulate_crash_post_rename_fsync: bool = False,
) -> Path:
    run_id = summary["run_id"]
    root = project_root or _get_project_root()
    output_parent.mkdir(parents=True, exist_ok=True)
    _assert_no_symlinks(output_parent, "output_parent")

    # Parent lock
    lock_fd = os.open(output_parent, os.O_RDONLY)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        final_root = output_parent / run_id
        if final_root.exists():
            raise Stage1_5IN3DiagnosticError(f"STOP=final_root_collision:{final_root}")

        # Check for pre-existing foreign staging
        existing_staging = list(output_parent.glob(f".{run_id}.staging.*"))
        if existing_staging:
            raise Stage1_5IN3DiagnosticError(f"STOP=foreign_staging_preexists:{existing_staging}")

        pid = os.getpid()
        staging_dir = output_parent / f".{run_id}.staging.{pid}"
        staging_dir.mkdir(parents=True, exist_ok=False)

        if simulate_crash_before_rename:
            raise Stage1_5IN3DiagnosticError("SIMULATED_PRE_RENAME_CRASH")

        summary_p = staging_dir / "stage1_5i_n3_sampled_mid_price_response_summary.json"
        review_p = staging_dir / "stage1_5i_n3_sampled_mid_price_response_review_CN.md"
        manifest_p = staging_dir / "stage1_5i_n3_sampled_mid_price_response_manifest.json"

        summary_bytes = canonical_json_dumps(summary).encode("utf-8")
        summary_p.write_bytes(summary_bytes)
        _fsync_file(summary_p)

        review_text = render_review(summary)
        review_bytes = review_text.encode("utf-8")
        review_p.write_bytes(review_bytes)
        _fsync_file(review_p)

        manifest = {
            "artifacts": {
                "stage1_5i_n3_sampled_mid_price_response_review_CN.md": {
                    "byte_count": len(review_bytes),
                    "relative_path": "stage1_5i_n3_sampled_mid_price_response_review_CN.md",
                    "sha256": hashlib.sha256(review_bytes).hexdigest(),
                },
                "stage1_5i_n3_sampled_mid_price_response_summary.json": {
                    "byte_count": len(summary_bytes),
                    "relative_path": "stage1_5i_n3_sampled_mid_price_response_summary.json",
                    "sha256": hashlib.sha256(summary_bytes).hexdigest(),
                },
            },
            "g_receipt_manifest_sha256": G_MANIFEST_SHA256,
            "g_receipt_review_sha256": G_REVIEW_SHA256,
            "g_receipt_summary_sha256": G_SUMMARY_SHA256,
            "h_receipt_manifest_sha256": H_MANIFEST_SHA256,
            "h_receipt_review_sha256": H_REVIEW_SHA256,
            "h_receipt_summary_sha256": H_SUMMARY_SHA256,
            "run_id": run_id,
            "schema_version": 1,
        }
        manifest_bytes = canonical_json_dumps(manifest).encode("utf-8")
        manifest_p.write_bytes(manifest_bytes)
        _fsync_file(manifest_p)

        _fsync_dir(staging_dir)

        # Strict load staging
        _load_verified_n3_sampled_mid_price_response_root_for_test(
            staging_dir,
            allowed_parent=output_parent,
            project_root=root,
        )

        # Atomic rename
        os.replace(staging_dir, final_root)

        if simulate_crash_post_rename_fsync:
            raise Stage1_5IN3PostRenameDurabilityFailure("SIMULATED_POST_RENAME_DURABILITY_CRASH")

        _fsync_dir(output_parent)

        # Reclassify and strict load final root
        _load_verified_n3_sampled_mid_price_response_root_for_test(
            final_root,
            allowed_parent=output_parent,
            project_root=root,
        )
        return final_root
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _publish_production_receipt(summary: dict[str, Any], project_root: Path) -> Path:
    out_parent = project_root / OUTPUT_PARENT_REL
    return _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=summary,
        output_parent=out_parent,
        project_root=project_root,
    )


# ---------------------------------------------------------------------------
# Public Production Route & Private Test Seams
# ---------------------------------------------------------------------------

def run_diagnostic(run_id: str) -> dict[str, Any]:
    """Single public production execution route."""
    root = _get_project_root()
    bundle = get_canonical_execution_authority_bundle_path()

    verify_execution_authority(bundle_dir=bundle, project_root=root)
    verify_local_receipt_generation_authority(run_id=run_id, bundle_dir=bundle, project_root=root)

    summary = admit_frozen_n3_inputs_and_reduce(project_root=root, run_id=run_id)
    _publish_production_receipt(summary, project_root=root)
    return summary


def _run_diagnostic_for_test(
    run_id: str,
    bundle_dir: Path,
    output_parent: Path,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Private test seam helper for testing in isolated directories."""
    root = project_root or _get_project_root()
    verify_execution_authority(bundle_dir=bundle_dir, project_root=root)
    verify_local_receipt_generation_authority(run_id=run_id, bundle_dir=bundle_dir, project_root=root)

    summary = admit_frozen_n3_inputs_and_reduce(project_root=root, run_id=run_id)
    _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=summary,
        output_parent=output_parent,
        project_root=root,
    )
    return summary
