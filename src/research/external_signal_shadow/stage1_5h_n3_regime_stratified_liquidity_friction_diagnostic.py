import copy
import fcntl
import hashlib
import importlib
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.research.external_signal_shadow.safety import canonical_json_dumps

# ---------------------------------------------------------------------------
# Frozen Authorities and Lineage Constants
# ---------------------------------------------------------------------------

APPROVED_DESIGN_REL_PATH = "docs/designs/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-design_CN.md"
APPROVED_DESIGN_SHA256 = "edc2dd3348fbf86f233ae4d236ed8202e69fc659a80d4a2b4376a0f7931d86a2"
APPROVED_PLAN_REL_PATH = "docs/plans/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-implementation-plan_CN.md"
APPROVED_PLAN_SHA256 = "9d9ebe80fa0560d9ae60df412d32fec3b5e839ec3073e93b4be9a661a5fded42"
REVIEWED_PLANNING_BASE_SHA = "9484dd3eedbc10a2edd4a2ded46a1ecc2ab54e91"

N3_RECEIPT_REL_PATH = "data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z"
N3_MANIFEST_SHA256 = "f3b4c76683fe7e1e4a7f28f30437f289f036f6ffc6126f8e9693faad62789adf"
N3_SUMMARY_SHA256 = "c92686b4834ee41165850aba99b1b68254b05a4afaf37d5e2789747db60ca941"
N3_REVIEW_SHA256 = "df6e12df8b1d105c62dd8cb01baeb0f858aa008c42488f699999a3b9ba51f2dc"

OUTPUT_PARENT_REL = "data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction"
RUN_ID_REGEX = re.compile(r"^stage1_5h_n3_regime_stratified_friction_[0-9]{8}T[0-9]{6}Z$")

EXPECTED_13_FALSE_FLAGS: Dict[str, bool] = {
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

FROZEN_UPSTREAM_MODULES: Dict[str, Tuple[str, str]] = {
    "src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission": (
        "src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py",
        "e64abe50b97d5cea303552c59f8f8f98168297ab0cabadfb554de9c1340c0c3d",
    ),
    "src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review": (
        "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py",
        "596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d",
    ),
    "src.research.external_signal_shadow.safety": (
        "src/research/external_signal_shadow/safety.py",
        "1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d",
    ),
    "configs.base": (
        "configs/base.py",
        "414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4",
    ),
}

FROZEN_SOURCE_ROOT_RECORDS = [
    {
        "input_key": "moonshot",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot",
        "source_manifest_sha256": "611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082",
    },
    {
        "input_key": "batch7",
        "source_root_path": "data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7",
        "source_manifest_sha256": "0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37",
    },
    {
        "input_key": "ct_projection",
        "source_root_path": "data/external_signal_shadow/local_evidence/20261001T074500Z_stage1_5f_ctusdt",
        "source_manifest_sha256": "f69efe25ea2efd03054372c41f882e2deb10e9842b890d71f60c19ce9b44f7db",
        "stored_summary_path": "data/external_signal_shadow/stage1_5g/reviews/20261002T010000Z_ctusdt_review/stage1_5g_live_depth_evidence_review_summary.json",
        "stored_summary_sha256": "9f6a1e9797dbc42af3ce103ed231689adb0422ef1ab23768ca398eb8ec153c1c",
    },
]

FROZEN_PRODUCT_REGIME_IDS = (
    "pre_ipo_equity_perpetual",
    "tradfi_equity_or_etf_perpetual_batch",
    "crypto_standard_perpetual",
)

SUMMARY_KEYS = (
    "authority_flags",
    "decision",
    "independent_parent_event_count",
    "input_receipt",
    "input_source_roots",
    "parent_rows",
    "per_symbol_rows",
    "research_classification",
    "run_id",
    "schema_version",
    "stage1_5g_gate3_complete",
)

PER_SYMBOL_ROW_KEYS = (
    "book_availability_ratio",
    "buy_slippage_bps_500usdt_p50",
    "buy_slippage_bps_500usdt_p95",
    "depth_capacity_ratio_to_risk_cap_p50",
    "event_symbol_id",
    "healthy_window_ratio",
    "invalid_book_row_count",
    "parent_article_id",
    "parent_event_id",
    "product_regime_id",
    "sell_slippage_bps_500usdt_p50",
    "sell_slippage_bps_500usdt_p95",
    "source_anchor_contract_hash",
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

PARENT_ROW_KEYS = (
    "child_event_symbol_ids",
    "child_symbol_count",
    "median_metrics",
    "parent_article_id",
    "parent_event_id",
    "product_regime_id",
)

MANIFEST_KEYS = (
    "artifacts",
    "input_receipt_manifest_sha256",
    "input_receipt_review_sha256",
    "input_receipt_summary_sha256",
    "run_id",
    "schema_version",
)

MANIFEST_ARTIFACT_KEYS = (
    "byte_count",
    "relative_path",
    "sha256",
)

INPUT_RECEIPT_KEYS = (
    "manifest_sha256",
    "review_sha256",
    "root_relative_path",
    "run_id",
    "summary_sha256",
)

INPUT_SOURCE_ROOTS_KEYS = (
    "input_key",
    "source_manifest_sha256",
    "source_root_path",
    "stored_summary_path",
    "stored_summary_sha256",
)

ALLOWED_QUALITY_METRIC_KEYS = (
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
)

ALLOWED_CONTEXT_METRIC_KEYS = (
    "book_availability_ratio",
    "invalid_book_row_count",
    "valid_snapshot_count_after_quarantine",
)

ALLOWED_DERIVED_METRIC_KEYS = (
    "sum_of_marginal_p95_slippage_bps",
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class Stage1_5HN3RegimeFrictionError(RuntimeError):
    """Base exception for Stage 1.5H N=3 regime stratified friction diagnostic errors."""
    pass


class Stage1_5HN3PostRenameDurabilityFailure(Stage1_5HN3RegimeFrictionError):
    """Raised when durability operations fail after atomic rename."""
    pass


# ---------------------------------------------------------------------------
# Internal Helpers: Project Root and Path Guards
# ---------------------------------------------------------------------------

def _get_project_root() -> Path:
    """Derive project root strictly from this module's file location."""
    return Path(__file__).resolve().parents[3]


def _assert_no_symlinks_before_resolve(path: Path) -> None:
    """Fail-closed check rejecting symlink on target and all ancestor components."""
    curr = path
    while True:
        if curr.is_symlink():
            raise Stage1_5HN3RegimeFrictionError(
                f"STOP=stage1_5h_n3_regime_publication_integrity_failure:parent_dir_symlink:{curr}"
            )
        parent = curr.parent
        if parent == curr:
            break
        curr = parent


def get_canonical_execution_authority_bundle_path() -> Path:
    """Returns canonical bundle path without reading environment overrides or caller input."""
    root = _get_project_root().resolve()
    return root / f".git/plan-execution/stage1_5h_n3_regime/{APPROVED_PLAN_SHA256}"


# ---------------------------------------------------------------------------
# Upstream Contract and Authority Verification
# ---------------------------------------------------------------------------

def verify_frozen_upstream_contract(
    project_root: Optional[Path] = None,
    expected_override: Optional[Dict[str, str]] = None,
) -> None:
    """Verifies SHA256 hashes of all four frozen upstream modules and imports them."""
    root = (project_root or _get_project_root()).resolve()
    overrides = expected_override or {}

    for mod_name, (rel_path, expected_hash) in FROZEN_UPSTREAM_MODULES.items():
        exp_h = overrides.get(rel_path, expected_hash)
        full_path = root / rel_path
        if not full_path.is_file() or full_path.is_symlink():
            raise Stage1_5HN3RegimeFrictionError(
                f"STOP=stage1_5h_n3_regime_upstream_contract_drift:frozen_module_missing:{rel_path}"
            )
        actual_h = hashlib.sha256(full_path.read_bytes()).hexdigest()
        if actual_h != exp_h:
            raise Stage1_5HN3RegimeFrictionError(
                f"STOP=stage1_5h_n3_regime_upstream_contract_drift:frozen_module_hash_mismatch:{rel_path}:{actual_h}!={exp_h}"
            )
        if expected_override is None:
            _import_verified_upstream(mod_name, project_root=root)


def _import_verified_upstream(
    module_name: str,
    project_root: Optional[Path] = None,
) -> Any:
    """Verifies origin, containment, and hash before and after importing an upstream module."""
    root = (project_root or _get_project_root()).resolve()
    if module_name not in FROZEN_UPSTREAM_MODULES:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_upstream_contract_drift:unauthorized_upstream_module:{module_name}"
        )

    rel_path, expected_sha = FROZEN_UPSTREAM_MODULES[module_name]
    expected_file = (root / rel_path).resolve()
    if not expected_file.is_file() or expected_file.is_symlink():
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_upstream_contract_drift:frozen_module_invalid:{rel_path}"
        )

    if module_name in sys.modules:
        existing = sys.modules[module_name]
        existing_file = getattr(existing, "__file__", None)
        existing_spec = getattr(existing, "__spec__", None)
        existing_origin = getattr(existing_spec, "origin", None) if existing_spec is not None else None

        if existing_spec is None or existing_origin is None or Path(existing_origin).is_symlink() or Path(existing_origin).resolve() != expected_file:
            raise Stage1_5HN3RegimeFrictionError(
                f"STOP=stage1_5h_n3_regime_upstream_contract_drift:preloaded_shadow_module_origin:{module_name}"
            )
        if existing_file is None or Path(existing_file).is_symlink() or Path(existing_file).resolve() != expected_file:
            raise Stage1_5HN3RegimeFrictionError(
                f"STOP=stage1_5h_n3_regime_upstream_contract_drift:preloaded_shadow_module:{module_name}"
            )

    mod = importlib.import_module(module_name)
    mod_file = getattr(mod, "__file__", None)
    mod_spec = getattr(mod, "__spec__", None)
    mod_origin = getattr(mod_spec, "origin", None) if mod_spec is not None else None

    if mod_spec is None or mod_origin is None or Path(mod_origin).is_symlink() or Path(mod_origin).resolve() != expected_file:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_upstream_contract_drift:imported_module_origin_mismatch:{module_name}"
        )
    if mod_file is None or Path(mod_file).is_symlink() or Path(mod_file).resolve() != expected_file:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_upstream_contract_drift:imported_module_origin_mismatch:{module_name}"
        )

    mod_sha = hashlib.sha256(Path(mod_file).read_bytes()).hexdigest()
    if mod_sha != expected_sha:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_upstream_contract_drift:imported_module_hash_mismatch:{module_name}"
        )

    return mod


def verify_execution_authority(
    bundle_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Validates the create-once execution authority bundle in .git/plan-execution."""
    root = (project_root or _get_project_root()).resolve()
    bundle = (bundle_dir or get_canonical_execution_authority_bundle_path()).resolve()

    _assert_no_symlinks_before_resolve(bundle)
    if not bundle.is_dir():
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_receipt_authority_mismatch:bundle_dir_missing:{bundle}"
        )

    # 1. base_sha
    base_sha_path = bundle / "base_sha"
    if not base_sha_path.is_file():
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:base_sha_missing")
    base_sha = base_sha_path.read_bytes().decode("ascii").strip()
    if base_sha != REVIEWED_PLANNING_BASE_SHA:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_upstream_contract_drift:base_sha_mismatch:{base_sha}!={REVIEWED_PLANNING_BASE_SHA}"
        )

    # 2. implementation_authorization.txt and sidecar
    auth_txt_path = bundle / "implementation_authorization.txt"
    auth_sidecar_path = bundle / "implementation_authorization.sha256"
    if not auth_txt_path.is_file() or not auth_sidecar_path.is_file():
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:implementation_auth_missing")
    if auth_txt_path.is_symlink() or auth_sidecar_path.is_symlink():
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:implementation_auth_symlink")

    auth_bytes = auth_txt_path.read_bytes()
    expected_auth_sha = hashlib.sha256(auth_bytes).hexdigest()
    sidecar_content = auth_sidecar_path.read_text(encoding="utf-8").strip()
    sidecar_parts = sidecar_content.split(None, 1)
    if not sidecar_parts or sidecar_parts[0] != expected_auth_sha:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:implementation_sidecar_mismatch")

    auth_lines = auth_bytes.decode("utf-8").splitlines()
    if len(auth_lines) != 2:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:implementation_auth_grammar_invalid")

    expected_line1 = f"我批准实施 Plan：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。"
    expected_line2 = "允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。"
    if auth_lines[0] != expected_line1 or auth_lines[1] != expected_line2:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:implementation_auth_content_mismatch")

    # Verify actual Design and Plan disk bytes match approved SHA256
    design_disk = (root / APPROVED_DESIGN_REL_PATH).read_bytes()
    if hashlib.sha256(design_disk).hexdigest() != APPROVED_DESIGN_SHA256:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:design_disk_bytes_mismatch")

    plan_disk = (root / APPROVED_PLAN_REL_PATH).read_bytes()
    if hashlib.sha256(plan_disk).hexdigest() != APPROVED_PLAN_SHA256:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:plan_disk_bytes_mismatch")

    # 3. execution_authority.json and sidecar
    exec_json_path = bundle / "execution_authority.json"
    exec_sidecar_path = bundle / "execution_authority.sha256"
    if not exec_json_path.is_file() or not exec_sidecar_path.is_file():
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:execution_auth_missing")
    if exec_json_path.is_symlink() or exec_sidecar_path.is_symlink():
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:execution_auth_symlink")

    exec_bytes = exec_json_path.read_bytes()
    expected_exec_sha = hashlib.sha256(exec_bytes).hexdigest()
    exec_sidecar_content = exec_sidecar_path.read_text(encoding="utf-8").strip()
    exec_sidecar_parts = exec_sidecar_content.split(None, 1)
    if not exec_sidecar_parts or exec_sidecar_parts[0] != expected_exec_sha:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:authority_sidecar_mismatch")

    data = json.loads(exec_bytes)
    required_keys = {
        "approved_design_path",
        "approved_design_sha256",
        "approved_plan_path",
        "approved_plan_sha256",
        "base_sha",
        "current_plan_sha256",
        "project_root",
    }
    if set(data.keys()) != required_keys:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:authority_keys_mismatch")

    if data["approved_design_path"] != APPROVED_DESIGN_REL_PATH:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:design_path_mismatch")
    if data["approved_design_sha256"] != APPROVED_DESIGN_SHA256:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:design_sha256_mismatch")
    if data["approved_plan_path"] != APPROVED_PLAN_REL_PATH:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:plan_path_mismatch")
    if data["approved_plan_sha256"] != APPROVED_PLAN_SHA256:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:plan_sha256_mismatch")
    if data["current_plan_sha256"] != APPROVED_PLAN_SHA256:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:current_plan_sha256_mismatch")
    if data["base_sha"] != REVIEWED_PLANNING_BASE_SHA:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:base_sha_mismatch")
    if Path(data["project_root"]).resolve() != root:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_upstream_contract_drift:project_root_mismatch")

    return data


def verify_local_receipt_generation_authority(
    bundle_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
    run_id: str = "",
) -> None:
    """Checks receipt_generation_authorization.txt and sidecar in the execution bundle."""
    root = (project_root or _get_project_root()).resolve()
    bundle = (bundle_dir or get_canonical_execution_authority_bundle_path()).resolve()

    gen_auth_path = bundle / "receipt_generation_authorization.txt"
    gen_sidecar_path = bundle / "receipt_generation_authorization.sha256"

    if not gen_auth_path.is_file() or not gen_sidecar_path.is_file():
        raise Stage1_5HN3RegimeFrictionError(
            "STOP=stage1_5h_n3_regime_receipt_authority_mismatch:generation_authorization_missing"
        )
    if gen_auth_path.is_symlink() or gen_sidecar_path.is_symlink():
        raise Stage1_5HN3RegimeFrictionError(
            "STOP=stage1_5h_n3_regime_receipt_authority_mismatch:generation_auth_symlink"
        )

    gen_bytes = gen_auth_path.read_bytes()
    expected_sha = hashlib.sha256(gen_bytes).hexdigest()
    sidecar_content = gen_sidecar_path.read_text(encoding="utf-8").strip()
    sidecar_parts = sidecar_content.split(None, 1)
    if not sidecar_parts or sidecar_parts[0] != expected_sha or (len(sidecar_parts) > 1 and sidecar_parts[1] != "receipt_generation_authorization.txt"):
        raise Stage1_5HN3RegimeFrictionError(
            "STOP=stage1_5h_n3_regime_receipt_authority_mismatch:generation_sidecar_mismatch"
        )

    lines = gen_bytes.decode("utf-8").splitlines()
    if len(lines) != 5:
        raise Stage1_5HN3RegimeFrictionError(
            "STOP=stage1_5h_n3_regime_receipt_authority_mismatch:generation_authorization_grammar_invalid"
        )

    if not RUN_ID_REGEX.match(run_id):
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_receipt_authority_mismatch:malformed_run_id:{run_id}"
        )

    expected_line1 = f"我批准本地生成 Stage 1.5H N=3 diagnostic receipt：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。"
    expected_line2 = f"RUN_ID: {run_id}"

    core_file = root / "src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py"
    cli_file = root / "scripts/external_signal_shadow/run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py"
    actual_core_sha = hashlib.sha256(core_file.read_bytes()).hexdigest()
    actual_cli_sha = hashlib.sha256(cli_file.read_bytes()).hexdigest()

    expected_line3 = f"H_CORE_SHA256: {actual_core_sha}"
    expected_line4 = f"H_CLI_SHA256: {actual_cli_sha}"
    expected_line5 = "允许仅本地生成 Stage 1.5H N=3 diagnostic receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。"

    if lines[0] != expected_line1:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_receipt_authority_mismatch:generation_authorization_plan_mismatch:{lines[0]}"
        )
    if lines[1] != expected_line2:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_receipt_authority_mismatch:generation_authorization_run_id_mismatch:{lines[1]}"
        )
    if lines[2] != expected_line3:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_receipt_authority_mismatch:generation_authorization_core_sha_mismatch:{lines[2]}"
        )
    if lines[3] != expected_line4:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_receipt_authority_mismatch:generation_authorization_cli_sha_mismatch:{lines[3]}"
        )
    if lines[4] != expected_line5:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_receipt_authority_mismatch:generation_authorization_permission_mismatch:{lines[4]}"
        )


# ---------------------------------------------------------------------------
# Re-admission and Comparator
# ---------------------------------------------------------------------------

def admit_frozen_n3_source_inputs(
    project_root: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Re-admits the three fixed source roots using Stage 1.5G loaders and compares with stored summaries."""
    root = (project_root or _get_project_root()).resolve()

    # Import verified upstream modules
    s15g_n3_mod = _import_verified_upstream("src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission", root)
    s15g_review_mod = _import_verified_upstream("src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review", root)

    # 1. Strict load N=3 receipt
    n3_receipt_path = (root / N3_RECEIPT_REL_PATH).resolve()
    _assert_no_symlinks_before_resolve(n3_receipt_path)
    n3_summary = s15g_n3_mod.load_verified_n3_receipt(n3_receipt_path)

    # 2. Re-admit the 3 source roots in fixed order
    admitted_sources: List[Dict[str, Any]] = []

    for item in FROZEN_SOURCE_ROOT_RECORDS:
        key = item["input_key"]
        src_root = (root / item["source_root_path"]).resolve()
        stored_summary_path = (root / item["stored_summary_path"]).resolve()

        _assert_no_symlinks_before_resolve(src_root)
        _assert_no_symlinks_before_resolve(stored_summary_path)

        # Check source manifest/sums sha
        sums_file = src_root / "SHA256SUMS"
        if not sums_file.is_file():
            raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_source_authority_mismatch:missing_sums:{key}")
        sums_sha = hashlib.sha256(sums_file.read_bytes()).hexdigest()
        if sums_sha != item["source_manifest_sha256"]:
            raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_source_authority_mismatch:sums_sha_mismatch:{key}")

        # Check stored summary sha
        stored_summary_bytes = stored_summary_path.read_bytes()
        stored_sha = hashlib.sha256(stored_summary_bytes).hexdigest()
        if stored_sha != item["stored_summary_sha256"]:
            raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_source_authority_mismatch:stored_summary_sha_mismatch:{key}")
        stored_summary = json.loads(stored_summary_bytes)

        # Re-admission
        bundle = s15g_review_mod.load_stage1_5g_inputs(src_root)
        if getattr(bundle, "loader_blockers", None):
            raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_source_authority_mismatch:loader_blockers:{key}")

        recomputed_summary = s15g_review_mod.build_stage1_5g_review_summary(
            summary=bundle.summary,
            watermark=bundle.watermark,
            states=bundle.states,
            accepted_events=bundle.accepted_events,
            snapshots=bundle.snapshots,
            request_manifest_rows=bundle.request_manifest_rows,
            output_root=src_root,
            loader_blockers=bundle.loader_blockers,
        )

        # Assert clean decision and no blockers
        if (
            recomputed_summary.get("schema_version") != 2
            or recomputed_summary.get("decision") != "stage1_5g_depth_evidence_clean_pass"
            or recomputed_summary.get("clean_depth_evidence_pass") is not True
            or len(recomputed_summary.get("blockers", [])) > 0
        ):
            raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_source_authority_mismatch:not_clean_pass:{key}")

        # Extract quality projection and contract hashes
        quality_proj: Dict[str, Dict[str, Any]] = {}
        contract_hashes: Dict[str, str] = {}
        all_child_identities: List[Dict[str, Any]] = []

        q_metrics = recomputed_summary["quarantine"]["per_symbol_quarantine_metrics"]
        for ev in bundle.accepted_events:
            ev_id = ev["event_symbol_id"]
            if ev_id not in q_metrics:
                continue

            metrics = q_metrics[ev_id]
            contract_hashes[ev_id] = ev["source_anchor_contract_hash"]
            all_child_identities.append({
                "event_symbol_id": ev_id,
                "symbol": ev["symbol"],
                "parent_article_id": ev["source_article_id"],
                "parent_event_id": ev["event_id"],
                "contract_hash": ev["source_anchor_contract_hash"],
            })

            # Check 12 depth quality metrics
            depth_q = metrics["quarantined_depth_quality"]
            depth_q_dict = {k: depth_q[k] for k in ALLOWED_QUALITY_METRIC_KEYS}

            # Check 3 context metrics
            context_dict = {
                "valid_snapshot_count_after_quarantine": metrics["valid_snapshot_count_after_quarantine"],
                "invalid_book_row_count": metrics["invalid_book_row_count"],
                "book_availability_ratio": metrics["book_availability_ratio"],
            }

            quality_proj[ev_id] = {
                "quarantined_depth_quality": depth_q_dict,
                "context_metrics": context_dict,
            }

        admitted_sources.append({
            "input_key": key,
            "source_record": item,
            "bundle": bundle,
            "stored_summary": stored_summary,
            "recomputed_summary": recomputed_summary,
            "quality_projection": quality_proj,
            "contract_hashes": contract_hashes,
            "all_child_identities": all_child_identities,
        })

    # Compare sources identity and quality projections
    compare_source_identity_and_quality(admitted_sources, n3_summary=n3_summary)
    return admitted_sources


def compare_source_identity_and_quality(
    admitted_sources: List[Dict[str, Any]],
    n3_summary: Optional[Dict[str, Any]] = None,
) -> None:
    """Verifies that admitted source metrics and child identities match exact expectations and CT duplicate edge."""
    # 1. Stored vs Recomputed quality metrics comparison
    for source in admitted_sources:
        stored_q_metrics = source["stored_summary"]["quarantine"]["per_symbol_quarantine_metrics"]
        for ev_id, q_data in source["quality_projection"].items():
            if ev_id not in stored_q_metrics:
                raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_metric_projection_mismatch:ev_not_in_stored:{ev_id}")
            stored_depth_q = stored_q_metrics[ev_id]["quarantined_depth_quality"]
            recomputed_depth_q = q_data["quarantined_depth_quality"]
            for k in ALLOWED_QUALITY_METRIC_KEYS:
                if recomputed_depth_q[k] != stored_depth_q[k]:
                    raise Stage1_5HN3RegimeFrictionError(
                        f"STOP=stage1_5h_n3_regime_metric_projection_mismatch:stored_vs_recomputed:{k}:{recomputed_depth_q[k]}!={stored_depth_q[k]}"
                    )

    # 2. Find batch7 and ct sources for CT duplicate verification (INV-HN3-04)
    batch7 = next(s for s in admitted_sources if s["input_key"] == "batch7")
    ct = next(s for s in admitted_sources if s["input_key"] == "ct_projection")

    # CT root has 8 children total: 1 CTUSDT and 7 duplicate Batch 7 children
    ct_children = ct["all_child_identities"]
    b7_children = batch7["all_child_identities"]

    b7_symbols = {c["symbol"] for c in b7_children}
    ct_symbols = {c["symbol"] for c in ct_children}

    if "CTUSDT" not in ct_symbols or ct_symbols - {"CTUSDT"} != b7_symbols:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_source_authority_mismatch:ct_duplicate_mismatch")

    # Verify duplicate equality for the 7 non-CT children
    for c_child in ct_children:
        if c_child["symbol"] == "CTUSDT":
            continue
        matching_b7 = next((b for b in b7_children if b["symbol"] == c_child["symbol"]), None)
        if matching_b7 is None:
            raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_source_authority_mismatch:ct_duplicate_mismatch")
        if (
            c_child["parent_article_id"] != matching_b7["parent_article_id"]
            or c_child["parent_event_id"] != matching_b7["parent_event_id"]
            or c_child["contract_hash"] != matching_b7["contract_hash"]
        ):
            raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_source_authority_mismatch:ct_duplicate_mismatch")

    # 3. Verify contract hashes against N=3 receipt product_regime_ledger
    if n3_summary is None:
        s15g_n3_mod = _import_verified_upstream("src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission")
        n3_receipt_path = (_get_project_root() / N3_RECEIPT_REL_PATH).resolve()
        n3_summary = s15g_n3_mod.load_verified_n3_receipt(n3_receipt_path)

    allowed_hashes_by_article: Dict[str, Set[str]] = {
        r["parent_article_id"]: set(r["source_anchor_contract_hashes"])
        for r in n3_summary["product_regime_ledger"]
    }

    for source in admitted_sources:
        for child in source["all_child_identities"]:
            art_id = child["parent_article_id"]
            ev_id = child["event_symbol_id"]
            c_hash = source["contract_hashes"].get(ev_id)
            allowed = allowed_hashes_by_article.get(art_id, set())
            if c_hash not in allowed:
                raise Stage1_5HN3RegimeFrictionError(
                    f"STOP=stage1_5h_n3_regime_source_authority_mismatch:contract_hash_mismatch:{c_hash}_not_in_{allowed}"
                )

    # Verify each quality metric is finite and valid
    for source in admitted_sources:
        for ev_id, q_data in source["quality_projection"].items():
            depth_q = q_data["quarantined_depth_quality"]
            for k in ALLOWED_QUALITY_METRIC_KEYS:
                if k not in depth_q:
                    raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_metric_projection_mismatch:missing_{k}")
                val = depth_q[k]
                if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val):
                    raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_metric_projection_mismatch:non_finite:{k}")

            context_q = q_data["context_metrics"]
            for k in ALLOWED_CONTEXT_METRIC_KEYS:
                if k not in context_q:
                    raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_metric_projection_mismatch:missing_{k}")
                val = context_q[k]
                if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val):
                    raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_metric_projection_mismatch:non_finite:{k}")


# ---------------------------------------------------------------------------
# Reducer & Summary Derivation
# ---------------------------------------------------------------------------

def derive_n3_friction_summary(
    admitted_sources: List[Dict[str, Any]],
    run_id: str,
    extra_test_injection: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Derives exact Stage 1.5H N=3 summary with 9 per_symbol_rows and 3 parent_rows."""
    if not RUN_ID_REGEX.match(run_id):
        raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_receipt_authority_mismatch:malformed_run_id:{run_id}")

    regime_map = {
        "moonshot": "pre_ipo_equity_perpetual",
        "batch7": "tradfi_equity_or_etf_perpetual_batch",
        "ct_projection": "crypto_standard_perpetual",
    }

    per_symbol_rows: List[Dict[str, Any]] = []

    for source in admitted_sources:
        key = source["input_key"]
        regime_id = regime_map[key]

        for child in source["all_child_identities"]:
            # If ct_projection, emit only CTUSDT
            if key == "ct_projection" and child["symbol"] != "CTUSDT":
                continue

            ev_id = child["event_symbol_id"]
            q_data = source["quality_projection"][ev_id]
            depth_q = q_data["quarantined_depth_quality"]
            context_q = q_data["context_metrics"]

            # Derive sum_of_marginal_p95_slippage_bps
            buy_p95 = depth_q["buy_slippage_bps_500usdt_p95"]
            sell_p95 = depth_q["sell_slippage_bps_500usdt_p95"]
            marginal_sum = float(buy_p95 + sell_p95)

            row: Dict[str, Any] = {
                "event_symbol_id": ev_id,
                "symbol": child["symbol"],
                "parent_article_id": child["parent_article_id"],
                "parent_event_id": child["parent_event_id"],
                "product_regime_id": regime_id,
                "source_anchor_contract_hash": child["contract_hash"],
                "spread_bps_p50": depth_q["spread_bps_p50"],
                "spread_bps_p95": depth_q["spread_bps_p95"],
                "buy_slippage_bps_500usdt_p50": depth_q["buy_slippage_bps_500usdt_p50"],
                "buy_slippage_bps_500usdt_p95": depth_q["buy_slippage_bps_500usdt_p95"],
                "sell_slippage_bps_500usdt_p50": depth_q["sell_slippage_bps_500usdt_p50"],
                "sell_slippage_bps_500usdt_p95": depth_q["sell_slippage_bps_500usdt_p95"],
                "top_bid_depth_usdt_p05": depth_q["top_bid_depth_usdt_p05"],
                "top_bid_depth_usdt_p50": depth_q["top_bid_depth_usdt_p50"],
                "top_ask_depth_usdt_p05": depth_q["top_ask_depth_usdt_p05"],
                "top_ask_depth_usdt_p50": depth_q["top_ask_depth_usdt_p50"],
                "depth_capacity_ratio_to_risk_cap_p50": depth_q["depth_capacity_ratio_to_risk_cap_p50"],
                "healthy_window_ratio": depth_q["healthy_window_ratio"],
                "valid_snapshot_count_after_quarantine": context_q["valid_snapshot_count_after_quarantine"],
                "invalid_book_row_count": context_q["invalid_book_row_count"],
                "book_availability_ratio": context_q["book_availability_ratio"],
                "sum_of_marginal_p95_slippage_bps": marginal_sum,
            }

            # Check finiteness and schema
            for k in PER_SYMBOL_ROW_KEYS:
                if k not in row:
                    raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_metric_projection_mismatch:missing_row_key:{k}")
                val = row[k]
                if isinstance(val, float) and (not math.isfinite(val) or isinstance(val, bool)):
                    raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_metric_projection_mismatch:non_finite:{k}")

            per_symbol_rows.append(row)

    if len(per_symbol_rows) != 9:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_membership_mismatch:expected_9_rows:got_{len(per_symbol_rows)}"
        )

    # Sort per_symbol_rows by (product_regime_id, parent_event_id, event_symbol_id)
    per_symbol_rows.sort(key=lambda r: (r["product_regime_id"], r["parent_event_id"], r["event_symbol_id"]))

    # Group into parent_rows
    parent_groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in per_symbol_rows:
        pid = r["parent_event_id"]
        if pid not in parent_groups:
            parent_groups[pid] = []
        parent_groups[pid].append(r)

    parent_rows: List[Dict[str, Any]] = []
    for p_id, children in parent_groups.items():
        children.sort(key=lambda c: c["event_symbol_id"])
        child_ids = [c["event_symbol_id"] for c in children]
        regime_id = children[0]["product_regime_id"]
        article_id = children[0]["parent_article_id"]

        # Compute median_metrics over the 12 depth quality metrics + sum_of_marginal_p95_slippage_bps (13 keys total)
        median_metrics: Dict[str, float] = {}
        target_keys = list(ALLOWED_QUALITY_METRIC_KEYS) + ["sum_of_marginal_p95_slippage_bps"]
        target_keys.sort()

        for k in target_keys:
            vals = [float(c[k]) for c in children]
            med_val = statistics.median(vals)
            median_metrics[k] = med_val

        parent_rows.append({
            "product_regime_id": regime_id,
            "parent_article_id": article_id,
            "parent_event_id": p_id,
            "child_event_symbol_ids": child_ids,
            "child_symbol_count": len(child_ids),
            "median_metrics": median_metrics,
        })

    # Sort parent_rows by parent_event_id
    parent_rows.sort(key=lambda p: p["parent_event_id"])

    if len(parent_rows) != 3:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_membership_mismatch:expected_3_parents:got_{len(parent_rows)}"
        )

    # Build input_receipt dictionary
    input_receipt_dict = {
        "manifest_sha256": N3_MANIFEST_SHA256,
        "review_sha256": N3_REVIEW_SHA256,
        "root_relative_path": N3_RECEIPT_REL_PATH,
        "run_id": "stage1_5g_n3_regime_stratified_admission_20261002T110403Z",
        "summary_sha256": N3_SUMMARY_SHA256,
    }

    # Summary dictionary
    summary: Dict[str, Any] = {
        "schema_version": 1,
        "decision": "stage1_5h_n3_regime_stratified_friction_diagnostic_generated",
        "research_classification": "evidence_insufficient",
        "independent_parent_event_count": 3,
        "stage1_5g_gate3_complete": False,
        "authority_flags": copy.deepcopy(EXPECTED_13_FALSE_FLAGS),
        "input_receipt": input_receipt_dict,
        "input_source_roots": copy.deepcopy(FROZEN_SOURCE_ROOT_RECORDS),
        "parent_rows": parent_rows,
        "per_symbol_rows": per_symbol_rows,
        "run_id": run_id,
    }

    if extra_test_injection:
        summary.update(extra_test_injection)

    # Validate exact top-level keys
    if set(summary.keys()) != set(SUMMARY_KEYS):
        forbidden = set(summary.keys()) - set(SUMMARY_KEYS)
        if any("pooled" in k or "cohort" in k or "summary" in k for k in forbidden):
            raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_scope_violation:forbidden_aggregate_key")
        raise Stage1_5HN3RegimeFrictionError(f"STOP=stage1_5h_n3_regime_scope_violation:invalid_summary_keys:{forbidden}")

    return summary


# ---------------------------------------------------------------------------
# Markdown Rendering
# ---------------------------------------------------------------------------

def render_review(summary: Dict[str, Any]) -> str:
    """Renders authoritative Markdown projection strictly byte-for-byte matching Design §5.3."""
    lines: List[str] = [
        "# Stage 1.5H N=3 产品机制分层流动性摩擦诊断报告",
        "",
        "> 本报告仅描述三个冻结 parent event 的静态 L2 quality metrics；不同 product regime 不作池化、比较、成本地板、执行可行性、Alpha 或交易结论。",
        "",
        "## 1. 诊断元数据与执行边界",
        "",
        f"- **run_id**: `{summary['run_id']}`",
        f"- **decision**: `{summary['decision']}`",
        f"- **research_classification**: `{summary['research_classification']}`",
        f"- **independent_parent_event_count**: `{summary['independent_parent_event_count']}`",
        f"- **stage1_5g_gate3_complete**: `{str(summary['stage1_5g_gate3_complete']).lower()}`",
        f"- **input_receipt_run_id**: `{summary['input_receipt']['run_id']}`",
        "",
        "## 2. 治理与权限向量 (Authority Flags)",
        "",
        "| Authority Flag | Value |",
        "| --- | --- |",
    ]

    for k in sorted(summary["authority_flags"].keys()):
        lines.append(f"| `{k}` | `{str(summary['authority_flags'][k]).lower()}` |")

    lines.extend([
        "",
        "## 3. 分层 Parent Event 诊断概览",
        "",
        "| Product Regime | Parent Article ID | Parent Event ID | Child Count | Median Spread (p50/p95 bps) | Median Slippage (buy/sell p95 bps) | Sum Marginal p95 bps |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])

    for p in summary["parent_rows"]:
        med = p["median_metrics"]
        spread_str = f"{med['spread_bps_p50']:.2f} / {med['spread_bps_p95']:.2f}"
        slip_str = f"{med['buy_slippage_bps_500usdt_p95']:.2f} / {med['sell_slippage_bps_500usdt_p95']:.2f}"
        sum_str = f"{med['sum_of_marginal_p95_slippage_bps']:.2f}"
        lines.append(
            f"| `{p['product_regime_id']}` | `{p['parent_article_id']}` | `{p['parent_event_id']}` | {p['child_symbol_count']} | {spread_str} | {slip_str} | {sum_str} |"
        )

    lines.extend([
        "",
        "## 4. 全量合约明细 (9 Formal Children)",
        "",
        "| Symbol | Product Regime | Parent Event ID | Spread p50 (bps) | Spread p95 (bps) | Buy p95 (bps) | Sell p95 (bps) | Sum p95 (bps) | Depth Ratio p50 | Book Avail |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])

    for r in summary["per_symbol_rows"]:
        lines.append(
            f"| `{r['symbol']}` | `{r['product_regime_id']}` | `{r['parent_event_id'][:16]}...` | {r['spread_bps_p50']:.2f} | {r['spread_bps_p95']:.2f} | {r['buy_slippage_bps_500usdt_p95']:.2f} | {r['sell_slippage_bps_500usdt_p95']:.2f} | {r['sum_of_marginal_p95_slippage_bps']:.2f} | {r['depth_capacity_ratio_to_risk_cap_p50']:.4f} | {r['book_availability_ratio']:.4f} |"
        )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Strict Artifact Loaders & State Classifier
# ---------------------------------------------------------------------------

def classify_n3_friction_root_state(final_root: Path) -> str:
    """Classifies directory state strictly into unpublished, staging_only, receipt_published, corrupt_or_unknown."""
    _assert_no_symlinks_before_resolve(final_root)
    parent_dir = final_root.parent
    run_id = final_root.name

    matching_stagings: List[Path] = []
    if parent_dir.is_dir():
        for item in parent_dir.iterdir():
            if item.name.startswith(f".{run_id}.staging."):
                matching_stagings.append(item)

    final_exists = final_root.exists()

    if not final_exists:
        if not matching_stagings:
            return "unpublished"
        return "staging_only"

    if matching_stagings:
        return "corrupt_or_unknown"

    try:
        load_verified_n3_friction_root(final_root)
        return "receipt_published"
    except Exception:
        return "corrupt_or_unknown"


def _classify_n3_friction_root_state_for_test(
    final_root: Path,
    allowed_parent: Path,
) -> str:
    """Internal test helper for state classification in test directories."""
    _assert_no_symlinks_before_resolve(final_root)
    parent_dir = final_root.parent
    run_id = final_root.name

    matching_stagings: List[Path] = []
    if parent_dir.is_dir():
        for item in parent_dir.iterdir():
            if item.name.startswith(f".{run_id}.staging."):
                matching_stagings.append(item)

    final_exists = final_root.exists()

    if not final_exists:
        if not matching_stagings:
            return "unpublished"
        return "staging_only"

    if matching_stagings:
        return "corrupt_or_unknown"

    try:
        _load_verified_n3_friction_root_for_test(final_root, allowed_parent=allowed_parent)
        return "receipt_published"
    except Exception:
        return "corrupt_or_unknown"


def _validate_n3_friction_root_contents(resolved_root: Path) -> Dict[str, Any]:
    """Strictly validates artifacts and schemas inside a validated root directory."""
    manifest_p = resolved_root / "stage1_5h_n3_regime_stratified_friction_manifest.json"
    summary_p = resolved_root / "stage1_5h_n3_regime_stratified_friction_summary.json"
    review_p = resolved_root / "stage1_5h_n3_regime_stratified_friction_review_CN.md"

    if not (manifest_p.is_file() and summary_p.is_file() and review_p.is_file()):
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:missing_artifact")

    expected_artifacts = {
        "stage1_5h_n3_regime_stratified_friction_manifest.json",
        "stage1_5h_n3_regime_stratified_friction_summary.json",
        "stage1_5h_n3_regime_stratified_friction_review_CN.md",
    }
    actual_items = {item.name for item in resolved_root.iterdir()}
    if actual_items != expected_artifacts:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_publication_integrity_failure:foreign_artifact:{actual_items - expected_artifacts}"
        )

    manifest = load_verified_n3_friction_manifest(manifest_p)
    summary = load_verified_n3_friction_summary(summary_p)
    review_text = load_verified_n3_friction_review(review_p)

    # Check manifest bindings
    sum_art = manifest["artifacts"]["stage1_5h_n3_regime_stratified_friction_summary.json"]
    sum_bytes = summary_p.read_bytes()
    if len(sum_bytes) != sum_art["byte_count"] or hashlib.sha256(sum_bytes).hexdigest() != sum_art["sha256"]:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:summary_manifest_mismatch")

    rev_art = manifest["artifacts"]["stage1_5h_n3_regime_stratified_friction_review_CN.md"]
    rev_bytes = review_p.read_bytes()
    if len(rev_bytes) != rev_art["byte_count"] or hashlib.sha256(rev_bytes).hexdigest() != rev_art["sha256"]:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:review_manifest_mismatch")

    # Byte-compare rendered markdown
    expected_md = render_review(summary)
    if review_text != expected_md:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:markdown_projection_mismatch")

    # Cross-validate manifest lineage with summary lineage
    if manifest["run_id"] != summary["run_id"]:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_summary_run_id_mismatch")
    if manifest["input_receipt_manifest_sha256"] != summary["input_receipt"]["manifest_sha256"]:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_summary_lineage_mismatch")
    if manifest["input_receipt_review_sha256"] != summary["input_receipt"]["review_sha256"]:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_summary_lineage_mismatch")
    if manifest["input_receipt_summary_sha256"] != summary["input_receipt"]["summary_sha256"]:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_summary_lineage_mismatch")

    return summary


def load_verified_n3_friction_root(final_root: Path) -> Dict[str, Any]:
    """Strictly loads and validates all 3 artifacts in canonical final_root."""
    _assert_no_symlinks_before_resolve(final_root)
    resolved_root = final_root.resolve()

    canonical_parent = (_get_project_root().resolve() / OUTPUT_PARENT_REL).resolve()
    if resolved_root.parent != canonical_parent:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_publication_integrity_failure:noncanonical_output_parent:{resolved_root.parent}"
        )

    return _validate_n3_friction_root_contents(resolved_root)


def _load_verified_n3_friction_root_for_test(
    final_root: Path,
    allowed_parent: Path,
) -> Dict[str, Any]:
    """Private test helper: strictly loads and validates all 3 artifacts under an isolated test parent."""
    _assert_no_symlinks_before_resolve(final_root)
    resolved_root = final_root.resolve()
    resolved_allowed = allowed_parent.resolve()

    if resolved_root.parent != resolved_allowed:
        raise Stage1_5HN3RegimeFrictionError(
            f"STOP=stage1_5h_n3_regime_publication_integrity_failure:noncanonical_output_parent:{resolved_root.parent}"
        )

    return _validate_n3_friction_root_contents(resolved_root)


def load_verified_n3_friction_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Strictly loads and validates manifest schema."""
    _assert_no_symlinks_before_resolve(manifest_path)
    content = manifest_path.read_bytes()
    data = json.loads(content)

    if set(data.keys()) != set(MANIFEST_KEYS):
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_keys_mismatch")

    if data.get("schema_version") != 1:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_schema_version")

    if data.get("input_receipt_manifest_sha256") != N3_MANIFEST_SHA256:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_lineage_mismatch")

    if data.get("input_receipt_review_sha256") != N3_REVIEW_SHA256:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_lineage_mismatch")

    if data.get("input_receipt_summary_sha256") != N3_SUMMARY_SHA256:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_lineage_mismatch")

    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_REGEX.match(run_id):
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_run_id")

    artifacts = data["artifacts"]
    expected_files = {
        "stage1_5h_n3_regime_stratified_friction_summary.json",
        "stage1_5h_n3_regime_stratified_friction_review_CN.md",
    }
    if set(artifacts.keys()) != expected_files:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_artifacts_mismatch")

    parent_dir = manifest_path.parent
    for fname, meta in artifacts.items():
        if set(meta.keys()) != set(MANIFEST_ARTIFACT_KEYS):
            raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:artifact_keys_mismatch")
        b_count = meta["byte_count"]
        if not isinstance(b_count, int) or isinstance(b_count, bool) or b_count <= 0:
            raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_byte_count")

        target_file = parent_dir / fname
        if target_file.is_file():
            actual_bytes = target_file.read_bytes()
            if len(actual_bytes) != b_count:
                raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_byte_count_mismatch")
            if hashlib.sha256(actual_bytes).hexdigest() != meta["sha256"]:
                raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:manifest_hash_mismatch")

    return data


def load_verified_n3_friction_summary(summary_path: Path) -> Dict[str, Any]:
    """Strictly loads and validates summary schema and canonical bytes."""
    _assert_no_symlinks_before_resolve(summary_path)
    content = summary_path.read_bytes()
    data = json.loads(content)

    # Canonical bytes check
    canonical_bytes = canonical_json_dumps(data).encode("utf-8")
    if content != canonical_bytes:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:non_canonical_json")

    if set(data.keys()) != set(SUMMARY_KEYS):
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:summary_keys_mismatch")

    if data.get("schema_version") != 1:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_schema_version")

    if data.get("decision") != "stage1_5h_n3_regime_stratified_friction_diagnostic_generated":
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_decision")

    if data.get("research_classification") != "evidence_insufficient":
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_research_classification")

    if data.get("independent_parent_event_count") != 3:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_parent_count")

    if data.get("stage1_5g_gate3_complete") is not False:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:stage1_5g_gate3_complete_must_be_false")

    if data.get("authority_flags") != EXPECTED_13_FALSE_FLAGS:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_authority_flags")

    # Validate input_receipt
    expected_input_receipt = {
        "manifest_sha256": N3_MANIFEST_SHA256,
        "review_sha256": N3_REVIEW_SHA256,
        "root_relative_path": N3_RECEIPT_REL_PATH,
        "run_id": "stage1_5g_n3_regime_stratified_admission_20261002T110403Z",
        "summary_sha256": N3_SUMMARY_SHA256,
    }
    if data.get("input_receipt") != expected_input_receipt:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_input_receipt")

    # Validate input_source_roots
    if data.get("input_source_roots") != FROZEN_SOURCE_ROOT_RECORDS:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_input_source_roots")

    # Validate parent_rows lineage
    parent_rows = data.get("parent_rows")
    if not isinstance(parent_rows, list) or len(parent_rows) != 3:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_parent_rows")

    expected_regimes = set(FROZEN_PRODUCT_REGIME_IDS)
    actual_regimes = {p.get("product_regime_id") for p in parent_rows}
    if actual_regimes != expected_regimes:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_product_regimes")

    # Validate per_symbol_rows
    per_symbol_rows = data.get("per_symbol_rows")
    if not isinstance(per_symbol_rows, list) or len(per_symbol_rows) != 9:
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:invalid_per_symbol_rows_count")

    return data


def load_verified_n3_friction_review(review_path: Path) -> str:
    """Strictly loads and validates review markdown text."""
    _assert_no_symlinks_before_resolve(review_path)
    return review_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Lifecycle and Atomic Publication
# ---------------------------------------------------------------------------

def _publish_n3_friction_receipt_for_lifecycle_test(
    summary: Dict[str, Any],
    parent_dir: Path,
    _failpoint: Optional[str] = None,
) -> Path:
    """Internal atomic publication routine under parent directory flock."""
    _assert_no_symlinks_before_resolve(parent_dir)
    parent_dir.mkdir(parents=True, exist_ok=True)

    parent_fd = os.open(str(parent_dir), os.O_RDONLY)
    try:
        fcntl.flock(parent_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError) as e:
        os.close(parent_fd)
        raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:concurrent_writer_collision") from e

    final_root: Optional[Path] = None
    try:
        run_id = summary["run_id"]
        final_root = parent_dir / run_id

        if final_root.exists():
            raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:final_root_preexists")

        # Check foreign staging siblings
        for item in parent_dir.iterdir():
            if item.name.startswith(f".{run_id}.staging."):
                raise Stage1_5HN3RegimeFrictionError("STOP=stage1_5h_n3_regime_publication_integrity_failure:foreign_staging_sibling")

        staging_dir = parent_dir / f".{run_id}.staging.{os.getpid()}"
        staging_dir.mkdir(parents=False, exist_ok=False)

        summary_p = staging_dir / "stage1_5h_n3_regime_stratified_friction_summary.json"
        review_p = staging_dir / "stage1_5h_n3_regime_stratified_friction_review_CN.md"
        manifest_p = staging_dir / "stage1_5h_n3_regime_stratified_friction_manifest.json"

        # 1. Write summary
        sum_bytes = canonical_json_dumps(summary).encode("utf-8")
        with open(summary_p, "wb") as f:
            f.write(sum_bytes)
            f.flush()
            os.fsync(f.fileno())

        # 2. Write review
        rev_text = render_review(summary)
        rev_bytes = rev_text.encode("utf-8")
        with open(review_p, "wb") as f:
            f.write(rev_bytes)
            f.flush()
            os.fsync(f.fileno())

        # 3. Write manifest-last
        manifest_dict = {
            "artifacts": {
                "stage1_5h_n3_regime_stratified_friction_review_CN.md": {
                    "byte_count": len(rev_bytes),
                    "relative_path": "stage1_5h_n3_regime_stratified_friction_review_CN.md",
                    "sha256": hashlib.sha256(rev_bytes).hexdigest(),
                },
                "stage1_5h_n3_regime_stratified_friction_summary.json": {
                    "byte_count": len(sum_bytes),
                    "relative_path": "stage1_5h_n3_regime_stratified_friction_summary.json",
                    "sha256": hashlib.sha256(sum_bytes).hexdigest(),
                },
            },
            "input_receipt_manifest_sha256": N3_MANIFEST_SHA256,
            "input_receipt_review_sha256": N3_REVIEW_SHA256,
            "input_receipt_summary_sha256": N3_SUMMARY_SHA256,
            "run_id": run_id,
            "schema_version": 1,
        }
        man_bytes = canonical_json_dumps(manifest_dict).encode("utf-8")
        with open(manifest_p, "wb") as f:
            f.write(man_bytes)
            f.flush()
            os.fsync(f.fileno())

        # Fsync staging directory
        staging_fd = os.open(str(staging_dir), os.O_RDONLY)
        try:
            os.fsync(staging_fd)
        finally:
            os.close(staging_fd)

        if _failpoint == "before_rename":
            raise RuntimeError("simulated_pre_rename_crash")

        # Atomic rename
        os.replace(staging_dir, final_root)

        if _failpoint == "after_rename_before_fsync":
            raise RuntimeError("simulated_post_rename_durability_failure")

        # Fsync parent directory
        os.fsync(parent_fd)

        # Strict reload final root via test helper
        _load_verified_n3_friction_root_for_test(final_root, allowed_parent=parent_dir)
        return final_root

    except Stage1_5HN3RegimeFrictionError:
        raise
    except Exception as e:
        if final_root is not None and final_root.exists():
            raise Stage1_5HN3PostRenameDurabilityFailure(
                f"STOP=stage1_5h_n3_regime_publication_integrity_failure:post_rename_failure:{e}"
            ) from e
        raise
    finally:
        fcntl.flock(parent_fd, fcntl.LOCK_UN)
        os.close(parent_fd)


def publish_n3_friction_receipt(summary: Dict[str, Any]) -> Path:
    """Public writer: enforces generation authority and writes to fixed production parent."""
    root = _get_project_root().resolve()
    bundle_dir = get_canonical_execution_authority_bundle_path()

    # 1. Authority guards
    verify_execution_authority(bundle_dir=bundle_dir, project_root=root)
    verify_local_receipt_generation_authority(
        bundle_dir=bundle_dir,
        project_root=root,
        run_id=summary["run_id"],
    )

    parent_dir = (root / OUTPUT_PARENT_REL).resolve()
    _assert_no_symlinks_before_resolve(parent_dir)

    return _publish_n3_friction_receipt_for_lifecycle_test(summary, parent_dir=parent_dir)


# ---------------------------------------------------------------------------
# Public Entrypoint: run_diagnostic
# ---------------------------------------------------------------------------

def run_diagnostic(run_id: str) -> Dict[str, Any]:
    """Public diagnostic entrypoint."""
    root = _get_project_root().resolve()
    bundle_dir = get_canonical_execution_authority_bundle_path()

    # 1. Authority guards
    verify_execution_authority(bundle_dir=bundle_dir, project_root=root)
    verify_local_receipt_generation_authority(bundle_dir=bundle_dir, project_root=root, run_id=run_id)

    # 2. Frozen modules verification
    verify_frozen_upstream_contract(project_root=root)

    # 3. Re-admission and reducer
    admitted_sources = admit_frozen_n3_source_inputs(project_root=root)
    summary = derive_n3_friction_summary(admitted_sources, run_id=run_id)

    # 4. Publication
    receipt_dir = publish_n3_friction_receipt(summary)

    return {
        "summary": summary,
        "receipt_dir": receipt_dir,
    }
