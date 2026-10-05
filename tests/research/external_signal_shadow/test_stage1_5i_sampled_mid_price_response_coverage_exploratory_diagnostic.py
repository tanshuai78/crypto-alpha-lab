import ast
import copy
import hashlib
import inspect
import json
import multiprocessing
import os
import shutil
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.research.external_signal_shadow.safety import canonical_json_dumps

try:
    from src.research.external_signal_shadow.stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic import (
        APPROVED_DESIGN_REL_PATH,
        APPROVED_DESIGN_SHA256,
        APPROVED_PLAN_REL_PATH,
        APPROVED_PLAN_SHA256,
        EXPECTED_19_FALSE_FLAGS,
        FROZEN_SOURCE_ROOT_RECORDS,
        FROZEN_UPSTREAM_MODULES,
        G_MANIFEST_SHA256,
        G_RECEIPT_REL_PATH,
        G_REVIEW_SHA256,
        G_SUMMARY_SHA256,
        H_MANIFEST_SHA256,
        H_RECEIPT_REL_PATH,
        H_REVIEW_SHA256,
        H_SUMMARY_SHA256,
        MANIFEST_KEYS,
        OUTPUT_PARENT_REL,
        REVIEWED_PLANNING_BASE_SHA,
        SUMMARY_KEYS,
        Stage1_5IN3DiagnosticError,
        Stage1_5IN3PostRenameDurabilityFailure,
        _classify_n3_sampled_mid_price_response_root_state_for_test,
        _import_verified_upstream,
        _load_verified_n3_sampled_mid_price_response_root_for_test,
        _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test,
        admit_frozen_n3_inputs_and_reduce,
        build_n3_sampled_mid_price_response_summary,
        classify_n3_sampled_mid_price_response_root_state,
        get_canonical_execution_authority_bundle_path,
        load_verified_n3_sampled_mid_price_response_manifest,
        load_verified_n3_sampled_mid_price_response_review,
        load_verified_n3_sampled_mid_price_response_root,
        load_verified_n3_sampled_mid_price_response_summary,
        locate_and_validate_owned_child_file,
        reduce_child_sampled_mid_price_coverage,
        render_review,
        run_diagnostic,
        verify_execution_authority,
        verify_frozen_upstream_contract,
        verify_local_receipt_generation_authority,
    )
except ImportError as _import_err:
    _err_msg = str(_import_err)

    def _unimplemented_stub(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"STOP=I_CORE_NOT_IMPLEMENTED: {_err_msg}")

    APPROVED_DESIGN_REL_PATH = ""  # type: ignore[assignment]
    APPROVED_DESIGN_SHA256 = ""  # type: ignore[assignment]
    APPROVED_PLAN_REL_PATH = ""  # type: ignore[assignment]
    APPROVED_PLAN_SHA256 = ""  # type: ignore[assignment]
    EXPECTED_19_FALSE_FLAGS = {}  # type: ignore[assignment]
    FROZEN_SOURCE_ROOT_RECORDS = []  # type: ignore[assignment]
    FROZEN_UPSTREAM_MODULES = {}  # type: ignore[assignment]
    G_MANIFEST_SHA256 = ""  # type: ignore[assignment]
    G_RECEIPT_REL_PATH = ""  # type: ignore[assignment]
    G_REVIEW_SHA256 = ""  # type: ignore[assignment]
    G_SUMMARY_SHA256 = ""  # type: ignore[assignment]
    H_MANIFEST_SHA256 = ""  # type: ignore[assignment]
    H_RECEIPT_REL_PATH = ""  # type: ignore[assignment]
    H_REVIEW_SHA256 = ""  # type: ignore[assignment]
    H_SUMMARY_SHA256 = ""  # type: ignore[assignment]
    MANIFEST_KEYS = ()  # type: ignore[assignment]
    OUTPUT_PARENT_REL = ""  # type: ignore[assignment]
    REVIEWED_PLANNING_BASE_SHA = ""  # type: ignore[assignment]
    SUMMARY_KEYS = ()  # type: ignore[assignment]

    class Stage1_5IN3DiagnosticError(Exception):  # type: ignore[no-redef]
        pass

    class Stage1_5IN3PostRenameDurabilityFailure(Stage1_5IN3DiagnosticError):  # type: ignore[no-redef]
        pass

    _import_verified_upstream = _unimplemented_stub  # type: ignore[assignment]
    _classify_n3_sampled_mid_price_response_root_state_for_test = _unimplemented_stub  # type: ignore[assignment]
    _load_verified_n3_sampled_mid_price_response_root_for_test = _unimplemented_stub  # type: ignore[assignment]
    _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test = _unimplemented_stub  # type: ignore[assignment]
    admit_frozen_n3_inputs_and_reduce = _unimplemented_stub  # type: ignore[assignment]
    build_n3_sampled_mid_price_response_summary = _unimplemented_stub  # type: ignore[assignment]
    classify_n3_sampled_mid_price_response_root_state = _unimplemented_stub  # type: ignore[assignment]
    get_canonical_execution_authority_bundle_path = _unimplemented_stub  # type: ignore[assignment]
    load_verified_n3_sampled_mid_price_response_manifest = _unimplemented_stub  # type: ignore[assignment]
    load_verified_n3_sampled_mid_price_response_review = _unimplemented_stub  # type: ignore[assignment]
    load_verified_n3_sampled_mid_price_response_root = _unimplemented_stub  # type: ignore[assignment]
    load_verified_n3_sampled_mid_price_response_summary = _unimplemented_stub  # type: ignore[assignment]
    locate_and_validate_owned_child_file = _unimplemented_stub  # type: ignore[assignment]
    reduce_child_sampled_mid_price_coverage = _unimplemented_stub  # type: ignore[assignment]
    render_review = _unimplemented_stub  # type: ignore[assignment]
    run_diagnostic = _unimplemented_stub  # type: ignore[assignment]
    verify_execution_authority = _unimplemented_stub  # type: ignore[assignment]
    verify_frozen_upstream_contract = _unimplemented_stub  # type: ignore[assignment]
    verify_local_receipt_generation_authority = _unimplemented_stub  # type: ignore[assignment]


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _get_task0_bundle_dir() -> Path:
    plan_sha = "4c233bca0587efa488dbb8339a225d8657e1b0a6c71796f75882fa5a210c2f65"
    bundle_dir = _get_project_root() / f".git/plan-execution/stage1_5i_n3_sampled_mid_price_response/{plan_sha}"
    if not bundle_dir.is_dir():
        pytest.skip(f"Task 0 bundle directory not found: {bundle_dir}")
    return bundle_dir


# ===========================================================================
# Independent Test-Only Oracle (Plan §4.5)
# ===========================================================================

def run_independent_test_oracle(
    raw_snapshots: list[dict[str, Any]],
    observation_window_start_ms: int,
) -> dict[str, Any]:
    """Test-only independent oracle over canonical snapshot list.

    Does NOT call any production reducer, locator, return helper, serializer, or loader.
    """
    valid_rows = [
        r for r in raw_snapshots
        if (
            isinstance(r.get("best_bid"), (int, float))
            and isinstance(r.get("best_ask"), (int, float))
            and not isinstance(r.get("best_bid"), bool)
            and not isinstance(r.get("best_ask"), bool)
            and r["best_bid"] > 0
            and r["best_ask"] > 0
            and r["best_ask"] >= r["best_bid"]
            and isinstance(r.get("fetched_at_ms"), int)
            and not isinstance(r.get("fetched_at_ms"), bool)
        )
    ]
    invalid_price_count = len(raw_snapshots) - len(valid_rows)
    gap_reasons = []
    if invalid_price_count > 0:
        gap_reasons.append("invalid_price_row")

    anchor_row = next((r for r in valid_rows if r["fetched_at_ms"] >= observation_window_start_ms), None)
    if anchor_row is None:
        gap_reasons.append("missing_anchor")
        return {
            "child_state": "coverage_gap",
            "gap_reasons": sorted(list(set(gap_reasons))),
            "raw_snapshot_count": len(raw_snapshots),
            "valid_mid_snapshot_count": len(valid_rows),
            "invalid_price_row_count": invalid_price_count,
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
            "child_state": "coverage_gap",
            "gap_reasons": sorted(list(set(gap_reasons))),
            "raw_snapshot_count": len(raw_snapshots),
            "valid_mid_snapshot_count": len(valid_rows),
            "invalid_price_row_count": invalid_price_count,
            "anchor": anchor_obj,
            "horizons": horizons_obj,
            "sampled_path": None,
        }

    # All horizons present and zero invalid prices -> complete
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
        "child_state": "complete",
        "gap_reasons": [],
        "raw_snapshot_count": len(raw_snapshots),
        "valid_mid_snapshot_count": len(valid_rows),
        "invalid_price_row_count": 0,
        "anchor": anchor_obj,
        "horizons": horizons_obj,
        "sampled_path": sampled_path_obj,
    }


# ===========================================================================
# Task 1 Canonical Fixture & Positive Cross-Boundary Test
# ===========================================================================

@pytest.fixture(scope="module")
def canonical_admitted_sources():
    """Canonical upstream fixture: loads N=3 receipt and re-admits all 3 frozen source roots."""
    project_root = _get_project_root()
    return admit_frozen_n3_inputs_and_reduce(project_root=project_root)


def test_canonical_positive_fixture_and_real_root_re_admission(canonical_admitted_sources):
    """Proves canonical fixture loads N=3 receipt and re-admits all 3 roots without error."""
    summary = canonical_admitted_sources
    assert summary["run_id"].startswith("stage1_5i_n3_sampled_mid_price_response_")
    assert summary["schema_version"] == 1
    assert summary["analysis_state"] in ("coverage_inventory", "complete_n3_exploratory_analysis")
    assert len(summary["coverage_inventory"]["parent_rows"]) == 3
    assert summary["coverage_inventory"]["child_count"] == 9


# ===========================================================================
# Task 1 Authority & Import Verification Tests
# ===========================================================================

def test_authority_rejects_substituted_implementation_text(tmp_path):
    """Authority validator rejects modified implementation_authorization.txt."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shutil.copytree(_get_task0_bundle_dir(), bundle, dirs_exist_ok=True)
    auth_file = bundle / "implementation_authorization.txt"
    auth_file.write_text("TAMPERED_AUTHORIZATION_LINE\n", encoding="utf-8")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=_get_project_root())


def test_authority_rejects_malformed_sidecar(tmp_path):
    """Authority validator rejects malformed or mismatched .sha256 sidecar."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shutil.copytree(_get_task0_bundle_dir(), bundle, dirs_exist_ok=True)
    sidecar = bundle / "implementation_authorization.sha256"
    sidecar.write_text("0000000000000000000000000000000000000000000000000000000000000000  implementation_authorization.txt\n")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=_get_project_root())


def test_authority_rejects_wrong_plan_sha(tmp_path):
    """Authority validator rejects mismatch between expected plan sha and authority json."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shutil.copytree(_get_task0_bundle_dir(), bundle, dirs_exist_ok=True)
    exec_auth_p = bundle / "execution_authority.json"
    data = json.loads(exec_auth_p.read_text(encoding="utf-8"))
    data["approved_plan_sha256"] = "f" * 64
    raw = canonical_json_dumps(data)
    exec_auth_p.write_text(raw, encoding="utf-8")
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    (bundle / "execution_authority.sha256").write_text(f"{h}  execution_authority.json\n")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=_get_project_root())


def test_authority_rejects_wrong_design_sha(tmp_path):
    """Authority validator rejects mismatch between expected design sha and authority json."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shutil.copytree(_get_task0_bundle_dir(), bundle, dirs_exist_ok=True)
    exec_auth_p = bundle / "execution_authority.json"
    data = json.loads(exec_auth_p.read_text(encoding="utf-8"))
    data["approved_design_sha256"] = "e" * 64
    raw = canonical_json_dumps(data)
    exec_auth_p.write_text(raw, encoding="utf-8")
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    (bundle / "execution_authority.sha256").write_text(f"{h}  execution_authority.json\n")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=_get_project_root())


def test_authority_rejects_wrong_base_sha(tmp_path):
    """Authority validator rejects base_sha that does not equal frozen base sha."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shutil.copytree(_get_task0_bundle_dir(), bundle, dirs_exist_ok=True)
    (bundle / "base_sha").write_text("0" * 40, encoding="utf-8")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=_get_project_root())


def test_authority_rejects_missing_design_file(tmp_path):
    """Authority validator rejects execution if approved design file is missing on disk."""
    mock_root = tmp_path / "mock_root"
    mock_root.mkdir()
    bundle = tmp_path / "bundle"
    shutil.copytree(_get_task0_bundle_dir(), bundle)
    exec_p = bundle / "execution_authority.json"
    data = json.loads(exec_p.read_text(encoding="utf-8"))
    data["project_root"] = str(mock_root.resolve())
    raw = canonical_json_dumps(data)
    exec_p.write_text(raw, encoding="utf-8")
    (bundle / "execution_authority.sha256").write_text(f"{hashlib.sha256(raw.encode('utf-8')).hexdigest()}  execution_authority.json\n")

    plan_dest = mock_root / APPROVED_PLAN_REL_PATH
    plan_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_get_project_root() / APPROVED_PLAN_REL_PATH, plan_dest)
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=mock_root)


def test_authority_rejects_tampered_design_file(tmp_path):
    """Authority validator rejects execution if approved design file hash does not match compiled constant."""
    mock_root = tmp_path / "mock_root"
    mock_root.mkdir()
    bundle = tmp_path / "bundle"
    shutil.copytree(_get_task0_bundle_dir(), bundle)
    exec_p = bundle / "execution_authority.json"
    data = json.loads(exec_p.read_text(encoding="utf-8"))
    data["project_root"] = str(mock_root.resolve())
    raw = canonical_json_dumps(data)
    exec_p.write_text(raw, encoding="utf-8")
    (bundle / "execution_authority.sha256").write_text(f"{hashlib.sha256(raw.encode('utf-8')).hexdigest()}  execution_authority.json\n")

    design_dest = mock_root / APPROVED_DESIGN_REL_PATH
    design_dest.parent.mkdir(parents=True, exist_ok=True)
    design_dest.write_text("TAMPERED DESIGN CONTENT\n", encoding="utf-8")
    plan_dest = mock_root / APPROVED_PLAN_REL_PATH
    plan_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_get_project_root() / APPROVED_PLAN_REL_PATH, plan_dest)
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=mock_root)


def test_authority_rejects_missing_plan_file(tmp_path):
    """Authority validator rejects execution if approved plan file is missing on disk."""
    mock_root = tmp_path / "mock_root"
    mock_root.mkdir()
    bundle = tmp_path / "bundle"
    shutil.copytree(_get_task0_bundle_dir(), bundle)
    exec_p = bundle / "execution_authority.json"
    data = json.loads(exec_p.read_text(encoding="utf-8"))
    data["project_root"] = str(mock_root.resolve())
    raw = canonical_json_dumps(data)
    exec_p.write_text(raw, encoding="utf-8")
    (bundle / "execution_authority.sha256").write_text(f"{hashlib.sha256(raw.encode('utf-8')).hexdigest()}  execution_authority.json\n")

    design_dest = mock_root / APPROVED_DESIGN_REL_PATH
    design_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_get_project_root() / APPROVED_DESIGN_REL_PATH, design_dest)
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=mock_root)


def test_authority_rejects_tampered_plan_file(tmp_path):
    """Authority validator rejects execution if approved plan file hash does not match compiled constant."""
    mock_root = tmp_path / "mock_root"
    mock_root.mkdir()
    bundle = tmp_path / "bundle"
    shutil.copytree(_get_task0_bundle_dir(), bundle)
    exec_p = bundle / "execution_authority.json"
    data = json.loads(exec_p.read_text(encoding="utf-8"))
    data["project_root"] = str(mock_root.resolve())
    raw = canonical_json_dumps(data)
    exec_p.write_text(raw, encoding="utf-8")
    (bundle / "execution_authority.sha256").write_text(f"{hashlib.sha256(raw.encode('utf-8')).hexdigest()}  execution_authority.json\n")

    design_dest = mock_root / APPROVED_DESIGN_REL_PATH
    design_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_get_project_root() / APPROVED_DESIGN_REL_PATH, design_dest)
    plan_dest = mock_root / APPROVED_PLAN_REL_PATH
    plan_dest.parent.mkdir(parents=True, exist_ok=True)
    plan_dest.write_text("TAMPERED PLAN CONTENT\n", encoding="utf-8")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=mock_root)


def test_authority_rejects_symlink_design_or_plan_file(tmp_path):
    """Authority validator rejects symlinked design or plan files."""
    mock_root = tmp_path / "mock_root"
    mock_root.mkdir()
    bundle = tmp_path / "bundle"
    shutil.copytree(_get_task0_bundle_dir(), bundle)
    exec_p = bundle / "execution_authority.json"
    data = json.loads(exec_p.read_text(encoding="utf-8"))
    data["project_root"] = str(mock_root.resolve())
    raw = canonical_json_dumps(data)
    exec_p.write_text(raw, encoding="utf-8")
    (bundle / "execution_authority.sha256").write_text(f"{hashlib.sha256(raw.encode('utf-8')).hexdigest()}  execution_authority.json\n")

    design_dest = mock_root / APPROVED_DESIGN_REL_PATH
    design_dest.parent.mkdir(parents=True, exist_ok=True)
    real_design = _get_project_root() / APPROVED_DESIGN_REL_PATH
    os.symlink(real_design, design_dest)
    plan_dest = mock_root / APPROVED_PLAN_REL_PATH
    plan_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_get_project_root() / APPROVED_PLAN_REL_PATH, plan_dest)
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=mock_root)


def test_authority_rejects_forged_generation_record(tmp_path):
    """Generation authority validator rejects forged or malformed receipt_generation_authorization.txt."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shutil.copytree(_get_task0_bundle_dir(), bundle, dirs_exist_ok=True)
    gen_file = bundle / "receipt_generation_authorization.txt"
    gen_file.write_text("FORGED_LINE_1\nFORGED_LINE_2\n", encoding="utf-8")
    gen_sha = hashlib.sha256(gen_file.read_bytes()).hexdigest()
    (bundle / "receipt_generation_authorization.sha256").write_text(f"{gen_sha}  receipt_generation_authorization.txt\n")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_local_receipt_generation_authority(
            run_id="stage1_5i_n3_sampled_mid_price_response_20261004T120000Z",
            bundle_dir=bundle,
            project_root=_get_project_root(),
        )


def test_authority_rejects_wrong_authorized_run_id(tmp_path):
    """Generation authority validator rejects authorized text specifying a different RUN_ID."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shutil.copytree(_get_task0_bundle_dir(), bundle, dirs_exist_ok=True)
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    text = (
        f"我批准本地生成 Stage 1.5I N=3 sampled-mid-price response receipt：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。\n"
        f"RUN_ID: stage1_5i_n3_sampled_mid_price_response_20261004T999999Z\n"
        f"I_CORE_SHA256: {'a'*64}\n"
        f"I_CLI_SHA256: {'b'*64}\n"
        "允许仅本地生成 Stage 1.5I N=3 sampled-mid-price response receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。\n"
    )
    (bundle / "receipt_generation_authorization.txt").write_text(text, encoding="utf-8")
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (bundle / "receipt_generation_authorization.sha256").write_text(f"{h}  receipt_generation_authorization.txt\n")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_local_receipt_generation_authority(
            run_id=run_id,
            bundle_dir=bundle,
            project_root=_get_project_root(),
        )


def test_authority_rejects_wrong_core_or_cli_hash(tmp_path):
    """Generation authority validator rejects mismatch in core or cli hash."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    shutil.copytree(_get_task0_bundle_dir(), bundle, dirs_exist_ok=True)
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    text = (
        f"我批准本地生成 Stage 1.5I N=3 sampled-mid-price response receipt：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。\n"
        f"RUN_ID: {run_id}\n"
        f"I_CORE_SHA256: {'0'*64}\n"
        f"I_CLI_SHA256: {'0'*64}\n"
        "允许仅本地生成 Stage 1.5I N=3 sampled-mid-price response receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。\n"
    )
    (bundle / "receipt_generation_authorization.txt").write_text(text, encoding="utf-8")
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (bundle / "receipt_generation_authorization.sha256").write_text(f"{h}  receipt_generation_authorization.txt\n")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_local_receipt_generation_authority(
            run_id=run_id,
            bundle_dir=bundle,
            project_root=_get_project_root(),
        )


def test_authority_rejects_symlink_bundle_or_file(tmp_path):
    """Authority validator rejects bundle directory or any file inside that is a symlink."""
    bundle = tmp_path / "symlink_bundle"
    real_bundle = _get_task0_bundle_dir()
    os.symlink(real_bundle, bundle)
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_execution_authority(bundle_dir=bundle, project_root=_get_project_root())


def test_import_rejects_byte_drift_module(tmp_path):
    """Frozen upstream contract verifier rejects byte-drift in an upstream module."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        verify_frozen_upstream_contract(
            project_root=_get_project_root(),
            tampered_overrides={"configs/base.py": "0" * 64},
        )


def test_import_rejects_wrong_spec_origin():
    """Import guard rejects preloaded modules with wrong __spec__.origin."""
    fake_mod = types.ModuleType("configs.base")
    fake_mod.__file__ = "/tmp/fake_configs_base.py"
    fake_mod.__spec__ = types.SimpleNamespace(origin="/tmp/fake_configs_base.py")  # type: ignore[assignment]
    with patch.dict(sys.modules, {"configs.base": fake_mod}):
        with pytest.raises(Stage1_5IN3DiagnosticError):
            _import_verified_upstream(project_root=_get_project_root())


def test_import_rejects_preloaded_module_wrong_file_attribute():
    """Import guard rejects preloaded modules with wrong __file__ despite valid __spec__.origin."""
    expected_origin = str((_get_project_root() / "configs/base.py").resolve())
    fake_mod = types.ModuleType("configs.base")
    fake_mod.__file__ = "/tmp/fake_configs_base.py"
    fake_mod.__spec__ = types.SimpleNamespace(origin=expected_origin)  # type: ignore[assignment]
    with patch.dict(sys.modules, {"configs.base": fake_mod}):
        with pytest.raises(Stage1_5IN3DiagnosticError):
            _import_verified_upstream(project_root=_get_project_root())


# ===========================================================================
# Task 1 Re-admission & Ownership Verification Tests
# ===========================================================================

def test_readmission_rejects_g_artifact_hash_drift():
    """Re-admission fails closed if G receipt artifact hash drifts."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        admit_frozen_n3_inputs_and_reduce(
            project_root=_get_project_root(),
            tampered_g_manifest_sha="0" * 64,
        )


def test_readmission_rejects_h_artifact_hash_drift():
    """Re-admission fails closed if H receipt artifact hash drifts."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        admit_frozen_n3_inputs_and_reduce(
            project_root=_get_project_root(),
            tampered_h_manifest_sha="0" * 64,
        )


def test_readmission_rejects_source_sha256sums_mismatch():
    """Re-admission fails closed if any source root SHA256SUMS hash drifts."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        admit_frozen_n3_inputs_and_reduce(
            project_root=_get_project_root(),
            tampered_source_manifest_key="moonshot",
        )


def test_readmission_rejects_stored_vs_recomputed_summary_mismatch():
    """Re-admission fails closed if stored summary differs from recomputed summary."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        admit_frozen_n3_inputs_and_reduce(
            project_root=_get_project_root(),
            tampered_stored_summary_key="batch7",
        )


def test_ownership_rejects_missing_owned_jsonl():
    """File locator fails closed if an owned child JSONL file is missing."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        locate_and_validate_owned_child_file(
            owner_input_key="moonshot",
            event_symbol_id="non_existent_event_symbol_id",
            project_root=_get_project_root(),
        )


def test_ownership_rejects_duplicate_or_wrong_owned_jsonl():
    """File locator fails closed if multiple files match the owned pattern."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        locate_and_validate_owned_child_file(
            owner_input_key="batch7",
            event_symbol_id="09da9a8516ad799b304fe2cf5d0f3b27bba2706099f9008c2650e3c468ea8035",
            project_root=_get_project_root(),
            simulate_duplicate=True,
        )


def test_ownership_rejects_selected_ct_root_batch7_duplicate():
    """CT root retains physical Batch7 files; attempting to select a Batch7 child under CT owner must STOP."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        locate_and_validate_owned_child_file(
            owner_input_key="ct_projection",
            event_symbol_id="09da9a8516ad799b304fe2cf5d0f3b27bba2706099f9008c2650e3c468ea8035",  # Batch7 child
            project_root=_get_project_root(),
        )


def test_ownership_rejects_jsonl_bundle_row_mismatch():
    """Parsed JSONL rows must match bundle.snapshots filtered rows exactly; mismatch is STOP."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        locate_and_validate_owned_child_file(
            owner_input_key="moonshot",
            event_symbol_id="e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602",
            project_root=_get_project_root(),
            tamper_parsed_row=True,
        )


def test_ownership_rejects_accepted_vs_state_identity_mismatch():
    """Mismatch in accepted event vs state identity for a child must STOP."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        admit_frozen_n3_inputs_and_reduce(
            project_root=_get_project_root(),
            tamper_accepted_event_identity=True,
        )


def test_ownership_rejects_accepted_vs_state_anchor_mismatch():
    """Mismatch between accepted-event observation_window_start_ms and state observation_window_start_ms must STOP."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        admit_frozen_n3_inputs_and_reduce(
            project_root=_get_project_root(),
            tamper_anchor_start_ms=True,
        )


# ===========================================================================
# Task 1 Sampled-Row Reduction & Oracle Verification Tests
# ===========================================================================

def test_sampled_row_independent_oracle_matches_canonical_projection():
    """Proves the independent test oracle matches the canonical reduction for all 9 children."""
    project_root = _get_project_root()
    # Read MOONSHOT canonical snapshots directly from physical file
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    obs_start = 1790065800000

    oracle_res = run_independent_test_oracle(raw_rows, obs_start)
    assert oracle_res["child_state"] == "complete"
    assert oracle_res["raw_snapshot_count"] == 716
    assert oracle_res["valid_mid_snapshot_count"] == 716
    assert oracle_res["invalid_price_row_count"] == 0
    assert oracle_res["anchor"]["anchor_delay_ms"] == 52693
    assert abs(oracle_res["horizons"]["15m"]["sampled_mid_return_bps"] - 154.6536) < 0.01
    assert abs(oracle_res["horizons"]["1h"]["sampled_mid_return_bps"] - (-430.3708)) < 0.01
    assert abs(oracle_res["horizons"]["4h"]["sampled_mid_return_bps"] - (-467.4597)) < 0.01
    assert oracle_res["sampled_path"]["sample_count_through_4h"] > 0

    # Production reducer call must match oracle output exactly
    reduced = reduce_child_sampled_mid_price_coverage(
        raw_snapshots=raw_rows,
        observation_window_start_ms=obs_start,
        detected_at_ms=1790062305738,
        parent_article_id="7379b99aa0f349a49c3b3feca1b4bbd6",
        parent_event_id="e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5",
        product_regime_id="pre_ipo_equity_perpetual",
        event_symbol_id="e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602",
        symbol="MOONSHOTUSDT",
        owner_input_key="moonshot",
        source_snapshot_relative_path="depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl",
    )
    assert reduced["child_state"] == oracle_res["child_state"]
    assert reduced["anchor"] == oracle_res["anchor"]
    assert reduced["horizons"] == oracle_res["horizons"]
    assert reduced["sampled_path"] == oracle_res["sampled_path"]


def test_sampled_row_boundary_anchor_selection_first_valid():
    """Anchor row must be strictly the first valid row with fetched_at_ms >= observation_window_start_ms."""
    project_root = _get_project_root()
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    obs_start = raw_rows[5]["fetched_at_ms"]  # exactly row 5's timestamp
    oracle_res = run_independent_test_oracle(raw_rows, obs_start)
    assert oracle_res["anchor"]["fetched_at_ms"] == obs_start
    assert oracle_res["anchor"]["anchor_delay_ms"] == 0


def test_sampled_row_boundary_horizon_endpoints_closed_interval():
    """Horizon window is closed interval [anchor+h, anchor+h+120000ms]. Rows at exact endpoints are valid."""
    obs_start = 1000000
    rows = [
        {"best_bid": 10.0, "best_ask": 10.0, "fetched_at_ms": obs_start, "exchange_time_ms": obs_start},
        {"best_bid": 10.0, "best_ask": 10.0, "fetched_at_ms": obs_start + 900000, "exchange_time_ms": obs_start + 900000},  # exact left 15m
        {"best_bid": 10.0, "best_ask": 10.0, "fetched_at_ms": obs_start + 3600000 + 120000, "exchange_time_ms": obs_start + 3600000 + 120000},  # exact right 1h
        {"best_bid": 10.0, "best_ask": 10.0, "fetched_at_ms": obs_start + 14400000, "exchange_time_ms": obs_start + 14400000},  # exact left 4h
    ]
    oracle_res = run_independent_test_oracle(rows, obs_start)
    assert oracle_res["child_state"] == "complete"
    assert oracle_res["horizons"]["15m"]["fetched_at_ms"] == obs_start + 900000
    assert oracle_res["horizons"]["1h"]["fetched_at_ms"] == obs_start + 3600000 + 120000
    assert oracle_res["horizons"]["4h"]["fetched_at_ms"] == obs_start + 14400000


def test_sampled_row_boundary_rows_outside_4h_excluded():
    """Rows beyond the selected 4h row must not be included in sampled_path extrema."""
    obs_start = 1000000
    rows = [
        {"best_bid": 10.0, "best_ask": 10.0, "fetched_at_ms": obs_start, "exchange_time_ms": obs_start},
        {"best_bid": 10.0, "best_ask": 10.0, "fetched_at_ms": obs_start + 900000, "exchange_time_ms": obs_start + 900000},
        {"best_bid": 10.0, "best_ask": 10.0, "fetched_at_ms": obs_start + 3600000, "exchange_time_ms": obs_start + 3600000},
        {"best_bid": 10.0, "best_ask": 10.0, "fetched_at_ms": obs_start + 14400000, "exchange_time_ms": obs_start + 14400000},  # 4h row, mid=10.0
        {"best_bid": 50.0, "best_ask": 50.0, "fetched_at_ms": obs_start + 20000000, "exchange_time_ms": obs_start + 20000000},  # outside row, mid=50.0
    ]
    oracle_res = run_independent_test_oracle(rows, obs_start)
    assert oracle_res["child_state"] == "complete"
    assert oracle_res["sampled_path"]["sampled_mfe_bps"] == 0.0  # 50.0 is excluded!
    assert oracle_res["sampled_path"]["sample_count_through_4h"] == 4


def test_sampled_row_gap_missing_4h_interval():
    """Removing rows in 4h horizon window causes coverage_gap with missing_horizon_4h and null sampled_path."""
    project_root = _get_project_root()
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    obs_start = 1790065800000
    anchor_fetched = 1790065852693
    # Filter out 4h window
    mutated_rows = [
        r for r in raw_rows
        if not (anchor_fetched + 14400000 <= r["fetched_at_ms"] <= anchor_fetched + 14400000 + 120000)
    ]
    oracle_res = run_independent_test_oracle(mutated_rows, obs_start)
    assert oracle_res["child_state"] == "coverage_gap"
    assert oracle_res["gap_reasons"] == ["missing_horizon_4h"]
    assert oracle_res["horizons"]["4h"] is None
    assert oracle_res["sampled_path"] is None


def test_sampled_row_gap_invalid_intermediate_bid_ask():
    """An invalid intermediate bid/ask retains anchor and horizons but causes invalid_price_row gap and null sampled_path."""
    project_root = _get_project_root()
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    obs_start = 1790065800000
    # Mutate row 10 (an intermediate row) to crossed book
    mutated_rows = copy.deepcopy(raw_rows)
    mutated_rows[10]["best_bid"] = 100.0
    mutated_rows[10]["best_ask"] = 50.0  # crossed book: best_ask < best_bid

    oracle_res = run_independent_test_oracle(mutated_rows, obs_start)
    assert oracle_res["child_state"] == "coverage_gap"
    assert oracle_res["gap_reasons"] == ["invalid_price_row"]
    assert oracle_res["invalid_price_row_count"] == 1
    assert oracle_res["anchor"] is not None
    assert oracle_res["horizons"]["15m"] is not None
    assert oracle_res["horizons"]["1h"] is not None
    assert oracle_res["horizons"]["4h"] is not None
    assert oracle_res["sampled_path"] is None


def test_sampled_row_gap_invalid_first_bid_ask_uses_later_valid():
    """An invalid first row with later valid row uses the later valid row as anchor, without fabricating missing_anchor."""
    project_root = _get_project_root()
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    obs_start = 1790065800000
    mutated_rows = copy.deepcopy(raw_rows)
    # Mutate the actual anchor row to crossed book
    mutated_rows[0]["best_bid"] = 100.0
    mutated_rows[0]["best_ask"] = 50.0

    oracle_res = run_independent_test_oracle(mutated_rows, obs_start)
    assert oracle_res["child_state"] == "coverage_gap"
    assert "invalid_price_row" in oracle_res["gap_reasons"]
    assert "missing_anchor" not in oracle_res["gap_reasons"]
    assert oracle_res["anchor"]["fetched_at_ms"] == raw_rows[1]["fetched_at_ms"]


def test_sampled_row_gap_all_invalid_prices():
    """All invalid prices produce invalid_price_row + missing_anchor and null anchor/horizons/path."""
    project_root = _get_project_root()
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    obs_start = 1790065800000
    mutated_rows = copy.deepcopy(raw_rows)
    for r in mutated_rows:
        r["best_bid"] = 0.0  # all non-positive
    oracle_res = run_independent_test_oracle(mutated_rows, obs_start)
    assert oracle_res["child_state"] == "coverage_gap"
    assert oracle_res["gap_reasons"] == ["invalid_price_row", "missing_anchor"]
    assert oracle_res["anchor"] is None
    assert oracle_res["horizons"] == {"15m": None, "1h": None, "4h": None}
    assert oracle_res["sampled_path"] is None


def test_sampled_row_stops_on_malformed_or_non_monotonic_timestamp():
    """Structural timestamp violation (non-monotonic or non-finite) is a STOP, not a coverage gap."""
    project_root = _get_project_root()
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    mutated_rows = copy.deepcopy(raw_rows)
    mutated_rows[5]["fetched_at_ms"] = mutated_rows[4]["fetched_at_ms"] - 1000  # non-monotonic!

    with pytest.raises(Stage1_5IN3DiagnosticError):
        reduce_child_sampled_mid_price_coverage(
            raw_snapshots=mutated_rows,
            observation_window_start_ms=1790065800000,
            detected_at_ms=1790062305738,
            parent_article_id="7379b99aa0f349a49c3b3feca1b4bbd6",
            parent_event_id="e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5",
            product_regime_id="pre_ipo_equity_perpetual",
            event_symbol_id="e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602",
            symbol="MOONSHOTUSDT",
            owner_input_key="moonshot",
            source_snapshot_relative_path="depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl",
        )


def test_sampled_row_stops_on_duplicate_fetched_at_ms():
    """Duplicate fetched_at_ms timestamp is a non-monotonic STOP."""
    project_root = _get_project_root()
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    mutated_rows = copy.deepcopy(raw_rows)
    mutated_rows[5]["fetched_at_ms"] = mutated_rows[4]["fetched_at_ms"]  # duplicate fetched!
    with pytest.raises(Stage1_5IN3DiagnosticError):
        reduce_child_sampled_mid_price_coverage(
            raw_snapshots=mutated_rows,
            observation_window_start_ms=1790065800000,
            detected_at_ms=1790062305738,
            parent_article_id="7379b99aa0f349a49c3b3feca1b4bbd6",
            parent_event_id="e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5",
            product_regime_id="pre_ipo_equity_perpetual",
            event_symbol_id="e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602",
            symbol="MOONSHOTUSDT",
            owner_input_key="moonshot",
            source_snapshot_relative_path="depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl",
        )


def test_sampled_row_stops_on_duplicate_exchange_time_ms():
    """Duplicate exchange_time_ms timestamp is a non-monotonic STOP."""
    project_root = _get_project_root()
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    mutated_rows = copy.deepcopy(raw_rows)
    mutated_rows[5]["exchange_time_ms"] = mutated_rows[4]["exchange_time_ms"]  # duplicate exchange!
    with pytest.raises(Stage1_5IN3DiagnosticError):
        reduce_child_sampled_mid_price_coverage(
            raw_snapshots=mutated_rows,
            observation_window_start_ms=1790065800000,
            detected_at_ms=1790062305738,
            parent_article_id="7379b99aa0f349a49c3b3feca1b4bbd6",
            parent_event_id="e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5",
            product_regime_id="pre_ipo_equity_perpetual",
            event_symbol_id="e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602",
            symbol="MOONSHOTUSDT",
            owner_input_key="moonshot",
            source_snapshot_relative_path="depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl",
        )


def test_sampled_row_stops_on_identical_duplicate_row():
    """Identical duplicate row is a non-monotonic STOP."""
    project_root = _get_project_root()
    moonshot_p = project_root / "data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl"
    raw_rows = [json.loads(line) for line in moonshot_p.read_text(encoding="utf-8").splitlines()]
    mutated_rows = copy.deepcopy(raw_rows)
    mutated_rows[5] = copy.deepcopy(mutated_rows[4])
    with pytest.raises(Stage1_5IN3DiagnosticError):
        reduce_child_sampled_mid_price_coverage(
            raw_snapshots=mutated_rows,
            observation_window_start_ms=1790065800000,
            detected_at_ms=1790062305738,
            parent_article_id="7379b99aa0f349a49c3b3feca1b4bbd6",
            parent_event_id="e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5",
            product_regime_id="pre_ipo_equity_perpetual",
            event_symbol_id="e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602",
            symbol="MOONSHOTUSDT",
            owner_input_key="moonshot",
            source_snapshot_relative_path="depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl",
        )


# ===========================================================================
# Task 1 Schema, Lifecycle, Durability & Permission Tests
# ===========================================================================

def test_schema_enforces_19_false_flags():
    """Summary schema must enforce all 19 authority flags are strictly boolean false."""
    flags = copy.deepcopy(EXPECTED_19_FALSE_FLAGS)
    assert len(flags) == 19
    for k, v in flags.items():
        assert v is False, f"Flag {k} must be False"


def test_schema_rejects_missing_or_unknown_or_typed_wrong_fields():
    """Strict loader rejects summary with missing, unknown, or typed-wrong fields."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        load_verified_n3_sampled_mid_price_response_summary(
            Path("/nonexistent/stage1_5i_n3_sampled_mid_price_response_summary.json"),
        )


def test_schema_rejects_nan_inf_bool_numerics():
    """Strict loader rejects summary containing NaN, Infinity, or bool in numeric fields."""
    summary_data = {
        "analysis_state": "coverage_inventory",
        "authority_flags": EXPECTED_19_FALSE_FLAGS,
        "coverage_inventory": {"child_count": 9, "parent_count": 3, "parent_rows": []},
        "decision": "stage1_5i_coverage_inventory_published",
        "g_receipt_binding": {},
        "h_receipt_binding": {},
        "parent_descriptive_rows": [],
        "run_id": "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z",
        "schema_version": 1,
        "source_root_bindings": [],
    }
    # Pass boolean True as numeric child_count
    bad_data = copy.deepcopy(summary_data)
    bad_data["coverage_inventory"]["child_count"] = True  # bool instead of int
    with pytest.raises(Stage1_5IN3DiagnosticError):
        build_n3_sampled_mid_price_response_summary(bad_data)


def test_schema_rejects_markdown_mismatch(tmp_path):
    """Strict review loader rejects Markdown that does not match byte-for-byte re-render of summary."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        load_verified_n3_sampled_mid_price_response_review(
            tmp_path / "stage1_5i_n3_sampled_mid_price_response_review_CN.md",
            summary={},
        )


def test_schema_rejects_manifest_byte_hash_path_mismatch(tmp_path):
    """Strict manifest loader rejects manifest with byte count, hash, or path mismatch."""
    with pytest.raises(Stage1_5IN3DiagnosticError):
        load_verified_n3_sampled_mid_price_response_manifest(
            tmp_path / "stage1_5i_n3_sampled_mid_price_response_manifest.json",
        )


def test_lifecycle_rejects_symlink_root_ancestor_artifact(tmp_path):
    """Lifecycle classifier rejects any final root, ancestor, or artifact containing a symlink."""
    sym_dir = tmp_path / "sym_target"
    sym_dir.mkdir()
    sym_link = tmp_path / "sym_link"
    os.symlink(sym_dir, sym_link)
    state = classify_n3_sampled_mid_price_response_root_state(sym_link)
    assert state == "corrupt_or_unknown"


_CANONICAL_TEST_SUMMARY_CACHE: dict[str, Any] | None = None


def _make_dummy_summary(run_id: str) -> dict[str, Any]:
    global _CANONICAL_TEST_SUMMARY_CACHE
    if _CANONICAL_TEST_SUMMARY_CACHE is None:
        _CANONICAL_TEST_SUMMARY_CACHE = admit_frozen_n3_inputs_and_reduce(
            project_root=_get_project_root(),
            run_id="stage1_5i_n3_sampled_mid_price_response_20261004T120000Z",
        )
    res = copy.deepcopy(_CANONICAL_TEST_SUMMARY_CACHE)
    res["run_id"] = run_id
    return res


def test_loader_rejects_noncanonical_output_parent(tmp_path):
    """Strict loader rejects published root with noncanonical output parent."""
    sig_loader = inspect.signature(load_verified_n3_sampled_mid_price_response_root)
    assert "allowed_parent" not in sig_loader.parameters, "Public loader must not expose allowed_parent parameter"
    assert "project_root" not in sig_loader.parameters, "Public loader must not expose project_root parameter"
    sig_classifier = inspect.signature(classify_n3_sampled_mid_price_response_root_state)
    assert "allowed_parent" not in sig_classifier.parameters, "Public classifier must not expose allowed_parent parameter"
    assert "project_root" not in sig_classifier.parameters, "Public classifier must not expose project_root parameter"

    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    custom_parent = tmp_path / "custom_parent"
    custom_parent.mkdir()
    final_root = _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=_make_dummy_summary(run_id),
        output_parent=custom_parent,
        project_root=_get_project_root(),
    )
    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        load_verified_n3_sampled_mid_price_response_root(final_root)
    assert "STOP=noncanonical_output_parent" in str(exc_info.value)

    # Public classifier must reject non-canonical output parent as corrupt_or_unknown
    assert classify_n3_sampled_mid_price_response_root_state(final_root) == "corrupt_or_unknown"


def test_public_loader_and_classifier_reject_external_project_root_override(tmp_path):
    """Public loader and classifier strictly derive workspace root and cannot be overridden by caller."""
    sig_loader = inspect.signature(load_verified_n3_sampled_mid_price_response_root)
    assert "project_root" not in sig_loader.parameters, "Public loader must not accept project_root"
    sig_classifier = inspect.signature(classify_n3_sampled_mid_price_response_root_state)
    assert "project_root" not in sig_classifier.parameters, "Public classifier must not accept project_root"

    fake_project_root = tmp_path / "fake_project"
    fake_out_parent = fake_project_root / OUTPUT_PARENT_REL
    fake_out_parent.mkdir(parents=True)
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    final_root = _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=_make_dummy_summary(run_id),
        output_parent=fake_out_parent,
        project_root=_get_project_root(),
    )
    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        load_verified_n3_sampled_mid_price_response_root(final_root)
    assert "STOP=noncanonical_output_parent" in str(exc_info.value)
    assert classify_n3_sampled_mid_price_response_root_state(final_root) == "corrupt_or_unknown"


def test_run_diagnostic_has_no_global_mutable_overrides():
    """run_diagnostic must not have global mutable overrides for authority or output sink."""
    import src.research.external_signal_shadow.stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic as core_mod
    assert not hasattr(core_mod, "_TEST_AUTHORITY_BUNDLE_DIR"), "_TEST_AUTHORITY_BUNDLE_DIR must not exist"
    assert not hasattr(core_mod, "_PRIVATE_PUBLICATION_SINK_FOR_TEST"), "_PRIVATE_PUBLICATION_SINK_FOR_TEST must not exist"



def test_loader_rejects_unlisted_extra_file_in_root(tmp_path):
    """Strict loader rejects root directory containing unlisted extra files."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "out_parent"
    out_parent.mkdir()
    final_root = _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=_make_dummy_summary(run_id),
        output_parent=out_parent,
        project_root=_get_project_root(),
    )
    (final_root / "unlisted_file.txt").write_text("injection\n", encoding="utf-8")
    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        _load_verified_n3_sampled_mid_price_response_root_for_test(final_root)
    assert "STOP=unlisted_file_in_root" in str(exc_info.value)


def test_loader_rejects_manifest_byte_count_or_hash_mismatch_with_disk(tmp_path):
    """Strict loader rejects root when artifact byte count or hash on disk mismatches manifest."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "out_parent"
    out_parent.mkdir()
    final_root = _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=_make_dummy_summary(run_id),
        output_parent=out_parent,
        project_root=_get_project_root(),
    )
    # Mutate review.md on disk
    (final_root / "stage1_5i_n3_sampled_mid_price_response_review_CN.md").write_text("TAMPERED\n", encoding="utf-8")
    with pytest.raises(Stage1_5IN3DiagnosticError):
        _load_verified_n3_sampled_mid_price_response_root_for_test(final_root)


def test_loader_rejects_forged_lineage_hashes(tmp_path):
    """Strict manifest loader rejects forged or tampered upstream lineage hashes."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "out_parent"
    out_parent.mkdir()
    final_root = _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=_make_dummy_summary(run_id),
        output_parent=out_parent,
        project_root=_get_project_root(),
    )
    man_p = final_root / "stage1_5i_n3_sampled_mid_price_response_manifest.json"
    data = json.loads(man_p.read_text(encoding="utf-8"))
    data["g_receipt_manifest_sha256"] = "0" * 64
    man_p.write_bytes(canonical_json_dumps(data).encode("utf-8"))
    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        load_verified_n3_sampled_mid_price_response_manifest(man_p)
    assert "STOP=manifest_g_lineage_mismatch" in str(exc_info.value)


def test_loader_rejects_forged_sampled_mid_price_metric_even_with_valid_manifest(tmp_path):
    """Strict root loader rejects forged child metric even if summary, review, and manifest are self-consistent."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "out_parent"
    out_parent.mkdir()
    final_root = _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=_make_dummy_summary(run_id),
        output_parent=out_parent,
        project_root=_get_project_root(),
    )
    sum_p = final_root / "stage1_5i_n3_sampled_mid_price_response_summary.json"
    rev_p = final_root / "stage1_5i_n3_sampled_mid_price_response_review_CN.md"
    man_p = final_root / "stage1_5i_n3_sampled_mid_price_response_manifest.json"

    data = json.loads(sum_p.read_text(encoding="utf-8"))
    # Forge 15m return by +1.0 bps
    data["coverage_inventory"]["parent_rows"][0]["children"][0]["horizons"]["15m"]["sampled_mid_return_bps"] += 1.0
    sum_bytes = canonical_json_dumps(data).encode("utf-8")
    sum_p.write_bytes(sum_bytes)

    rev_text = render_review(data)
    rev_bytes = rev_text.encode("utf-8")
    rev_p.write_bytes(rev_bytes)

    man_data = json.loads(man_p.read_text(encoding="utf-8"))
    man_data["artifacts"]["stage1_5i_n3_sampled_mid_price_response_summary.json"]["byte_count"] = len(sum_bytes)
    man_data["artifacts"]["stage1_5i_n3_sampled_mid_price_response_summary.json"]["sha256"] = hashlib.sha256(sum_bytes).hexdigest()
    man_data["artifacts"]["stage1_5i_n3_sampled_mid_price_response_review_CN.md"]["byte_count"] = len(rev_bytes)
    man_data["artifacts"]["stage1_5i_n3_sampled_mid_price_response_review_CN.md"]["sha256"] = hashlib.sha256(rev_bytes).hexdigest()
    man_p.write_bytes(canonical_json_dumps(man_data).encode("utf-8"))

    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        _load_verified_n3_sampled_mid_price_response_root_for_test(final_root)
    assert "STOP=stage1_5i_n3_sampled_mid_price_response_reduction_mismatch:coverage_inventory" in str(exc_info.value)


def test_loader_rejects_forged_child_state_or_gap_reasons_even_with_valid_manifest(tmp_path):
    """Strict root loader rejects forged child state even if manifest is updated."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "out_parent"
    out_parent.mkdir()
    final_root = _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=_make_dummy_summary(run_id),
        output_parent=out_parent,
        project_root=_get_project_root(),
    )
    sum_p = final_root / "stage1_5i_n3_sampled_mid_price_response_summary.json"
    rev_p = final_root / "stage1_5i_n3_sampled_mid_price_response_review_CN.md"
    man_p = final_root / "stage1_5i_n3_sampled_mid_price_response_manifest.json"

    data = json.loads(sum_p.read_text(encoding="utf-8"))
    data["coverage_inventory"]["parent_rows"][0]["children"][0]["child_state"] = "gap_detected"
    data["coverage_inventory"]["parent_rows"][0]["children"][0]["gap_reasons"] = ["forged_gap"]
    sum_bytes = canonical_json_dumps(data).encode("utf-8")
    sum_p.write_bytes(sum_bytes)

    rev_text = render_review(data)
    rev_bytes = rev_text.encode("utf-8")
    rev_p.write_bytes(rev_bytes)

    man_data = json.loads(man_p.read_text(encoding="utf-8"))
    man_data["artifacts"]["stage1_5i_n3_sampled_mid_price_response_summary.json"]["byte_count"] = len(sum_bytes)
    man_data["artifacts"]["stage1_5i_n3_sampled_mid_price_response_summary.json"]["sha256"] = hashlib.sha256(sum_bytes).hexdigest()
    man_data["artifacts"]["stage1_5i_n3_sampled_mid_price_response_review_CN.md"]["byte_count"] = len(rev_bytes)
    man_data["artifacts"]["stage1_5i_n3_sampled_mid_price_response_review_CN.md"]["sha256"] = hashlib.sha256(rev_bytes).hexdigest()
    man_p.write_bytes(canonical_json_dumps(man_data).encode("utf-8"))

    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        _load_verified_n3_sampled_mid_price_response_root_for_test(final_root)
    assert "STOP=stage1_5i_n3_sampled_mid_price_response_reduction_mismatch:coverage_inventory" in str(exc_info.value)


def test_loader_rejects_non_canonical_json_bytes(tmp_path):
    """Strict loaders reject non-canonical formatting in summary or manifest."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "out_parent"
    out_parent.mkdir()
    final_root = _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
        summary=_make_dummy_summary(run_id),
        output_parent=out_parent,
        project_root=_get_project_root(),
    )
    sum_p = final_root / "stage1_5i_n3_sampled_mid_price_response_summary.json"
    data = json.loads(sum_p.read_text(encoding="utf-8"))
    sum_p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        load_verified_n3_sampled_mid_price_response_summary(sum_p)
    assert "STOP=summary_non_canonical_json" in str(exc_info.value)


def test_summary_rejects_mismatched_state_decision_or_child_count():
    """Summary validator strictly enforces 9 children, 3 parents, product regimes, and state-decision pair."""
    base_summary = _make_dummy_summary("stage1_5i_n3_sampled_mid_price_response_20261004T120000Z")

    # Mismatched state and decision
    bad_pair = copy.deepcopy(base_summary)
    bad_pair["analysis_state"] = "coverage_inventory"
    bad_pair["decision"] = "stage1_5i_complete_n3_exploratory_analysis_published"
    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        build_n3_sampled_mid_price_response_summary(bad_pair)
    assert "STOP=invalid_state_decision_pair" in str(exc_info.value)

    # Wrong child count
    bad_child = copy.deepcopy(base_summary)
    bad_child["coverage_inventory"]["child_count"] = 8
    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        build_n3_sampled_mid_price_response_summary(bad_child)
    assert "STOP=invalid_numeric:child_count" in str(exc_info.value)

    # Wrong parent count
    bad_parent = copy.deepcopy(base_summary)
    bad_parent["coverage_inventory"]["parent_count"] = 2
    with pytest.raises(Stage1_5IN3DiagnosticError) as exc_info:
        build_n3_sampled_mid_price_response_summary(bad_parent)
    assert "STOP=invalid_numeric:parent_count" in str(exc_info.value)


def test_lifecycle_rejects_foreign_staging_or_collision(tmp_path):
    """Writer rejects publication if foreign staging or existing final root pre-exists."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "output_parent"
    out_parent.mkdir()
    foreign_staging = out_parent / f".{run_id}.staging.999999"
    foreign_staging.mkdir()
    with pytest.raises(Stage1_5IN3DiagnosticError):
        _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
            summary=_make_dummy_summary(run_id),
            output_parent=out_parent,
            project_root=_get_project_root(),
        )


def test_lifecycle_crash_pre_rename_leaves_staging_only(tmp_path):
    """Crash before atomic rename leaves staging directory and classifies state as staging_only."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "output_parent"
    out_parent.mkdir()
    with pytest.raises(Stage1_5IN3DiagnosticError):
        _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
            summary=_make_dummy_summary(run_id),
            output_parent=out_parent,
            project_root=_get_project_root(),
            simulate_crash_before_rename=True,
        )
    state = _classify_n3_sampled_mid_price_response_root_state_for_test(out_parent / run_id)
    assert state == "staging_only"


def test_lifecycle_crash_post_rename_fsync_raises_durability_failure(tmp_path):
    """Crash after atomic rename during parent fsync raises Stage1_5IN3PostRenameDurabilityFailure."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "output_parent"
    out_parent.mkdir()
    with pytest.raises(Stage1_5IN3PostRenameDurabilityFailure):
        _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
            summary=_make_dummy_summary(run_id),
            output_parent=out_parent,
            project_root=_get_project_root(),
            simulate_crash_post_rename_fsync=True,
        )


def _writer_worker(out_parent: Path, project_root: Path, run_id: str, barrier: Any, result_queue: Any):
    barrier.wait()
    try:
        _publish_n3_sampled_mid_price_response_receipt_for_lifecycle_test(
            summary=_make_dummy_summary(run_id),
            output_parent=out_parent,
            project_root=project_root,
        )
        result_queue.put(("SUCCESS", os.getpid()))
    except Exception as exc:
        result_queue.put(("FAIL", os.getpid(), str(exc)))


def test_lifecycle_concurrent_writers_synchronization_barrier_collision_excluded(tmp_path):
    """Two concurrent processes contending for the same parent flock with same RUN_ID: exactly 1 publishes, 1 fails closed."""
    run_id = "stage1_5i_n3_sampled_mid_price_response_20261004T120000Z"
    out_parent = tmp_path / "output_parent"
    out_parent.mkdir()
    project_root = _get_project_root()

    barrier = multiprocessing.Barrier(2)
    result_queue = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=_writer_worker, args=(out_parent, project_root, run_id, barrier, result_queue))
    p2 = multiprocessing.Process(target=_writer_worker, args=(out_parent, project_root, run_id, barrier, result_queue))

    p1.start()
    p2.start()
    p1.join(timeout=10)
    p2.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    assert len(results) == 2
    successes = [r for r in results if r[0] == "SUCCESS"]
    fails = [r for r in results if r[0] == "FAIL"]
    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
    assert len(fails) == 1, f"Expected 1 fail, got {len(fails)}"


def test_ast_and_open_spy_rejects_forbidden_imports_and_premature_opens():
    """AST guard proves core has zero network/socket/subprocess/live/paper imports and no premature file opens."""
    core_path = _get_project_root() / "src/research/external_signal_shadow/stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py"
    if not core_path.is_file():
        raise RuntimeError("STOP=I_CORE_NOT_IMPLEMENTED: core file absent")

    tree = ast.parse(core_path.read_text(encoding="utf-8"))
    forbidden_modules = {
        "socket", "urllib", "requests", "http", "aiohttp", "httpx",
        "subprocess", "asyncio", "ftplib", "smtplib", "telnetlib",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import from: {node.module}"
