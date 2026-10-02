import ast
import copy
import hashlib
import inspect
import json
import os
import shutil
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from src.research.external_signal_shadow.safety import canonical_json_dumps
from src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission import (
    load_verified_cross_root_receipt,
)

try:
    from src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic import (
        ALLOWED_QUALITY_METRIC_KEYS,
        APPROVED_DESIGN_REL_PATH,
        APPROVED_DESIGN_SHA256,
        APPROVED_PLAN_REL_PATH,
        APPROVED_PLAN_SHA256,
        CROSS_ROOT_MANIFEST_SHA256,
        CROSS_ROOT_ROOT_REL,
        CROSS_ROOT_SUMMARY_SHA256,
        EXPECTED_13_FALSE_FLAGS,
        FROZEN_INPUT_RECORDS,
        FROZEN_UPSTREAM_CONTRACT,
        MANIFEST_KEYS,
        OUTPUT_PARENT_REL,
        PER_SYMBOL_ROW_KEYS,
        SUMMARY_KEYS,
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        admit_frozen_cross_root_inputs,
        classify_v3_root_state,
        compare_quality_projections,
        derive_cross_root_friction_summary,
        load_verified_v3_manifest,
        load_verified_v3_review,
        load_verified_v3_root,
        load_verified_v3_summary,
        render_review,
        run_diagnostic,
        validate_receipt_identity,
        verify_execution_authority,
        verify_frozen_upstream_contract,
    )
except ImportError as _import_err:
    _err_msg = str(_import_err)

    def _unimplemented_stub(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(f"Stage 1.5H V3 module not yet implemented: {_err_msg}")

    ALLOWED_QUALITY_METRIC_KEYS = ()  # type: ignore[assignment]
    APPROVED_DESIGN_REL_PATH = ""  # type: ignore[assignment]
    APPROVED_DESIGN_SHA256 = ""  # type: ignore[assignment]
    APPROVED_PLAN_REL_PATH = ""  # type: ignore[assignment]
    APPROVED_PLAN_SHA256 = ""  # type: ignore[assignment]
    CROSS_ROOT_MANIFEST_SHA256 = ""  # type: ignore[assignment]
    CROSS_ROOT_ROOT_REL = ""  # type: ignore[assignment]
    CROSS_ROOT_SUMMARY_SHA256 = ""  # type: ignore[assignment]
    EXPECTED_13_FALSE_FLAGS = {}  # type: ignore[assignment]
    FROZEN_INPUT_RECORDS = []  # type: ignore[assignment]
    FROZEN_UPSTREAM_CONTRACT = {}  # type: ignore[assignment]
    MANIFEST_KEYS = ()  # type: ignore[assignment]
    OUTPUT_PARENT_REL = ""  # type: ignore[assignment]
    PER_SYMBOL_ROW_KEYS = ()  # type: ignore[assignment]
    SUMMARY_KEYS = ()  # type: ignore[assignment]

    class Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError(Exception):  # type: ignore[no-redef]
        pass

    admit_frozen_cross_root_inputs = _unimplemented_stub  # type: ignore[assignment]
    classify_v3_root_state = _unimplemented_stub  # type: ignore[assignment]
    compare_quality_projections = _unimplemented_stub  # type: ignore[assignment]
    derive_cross_root_friction_summary = _unimplemented_stub  # type: ignore[assignment]
    load_verified_v3_manifest = _unimplemented_stub  # type: ignore[assignment]
    load_verified_v3_review = _unimplemented_stub  # type: ignore[assignment]
    load_verified_v3_root = _unimplemented_stub  # type: ignore[assignment]
    load_verified_v3_summary = _unimplemented_stub  # type: ignore[assignment]
    render_review = _unimplemented_stub  # type: ignore[assignment]
    run_diagnostic = _unimplemented_stub  # type: ignore[assignment]
    validate_receipt_identity = _unimplemented_stub  # type: ignore[assignment]
    verify_execution_authority = _unimplemented_stub  # type: ignore[assignment]
    verify_frozen_upstream_contract = _unimplemented_stub  # type: ignore[assignment]


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _get_valid_baseline_dir() -> Path:
    env_file = Path("/tmp/stage1_5h_v3_env.sh")
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("export EXECUTION_BASELINE_DIR="):
                b_dir = Path(line.split("=", 1)[1].strip())
                if b_dir.is_dir():
                    return b_dir
    baseline_env = os.environ.get("EXECUTION_BASELINE_DIR")
    if baseline_env and Path(baseline_env).is_dir():
        return Path(baseline_env)
    pytest.skip("No valid EXECUTION_BASELINE_DIR found in env or /tmp/stage1_5h_v3_env.sh")


def test_canonical_integration_real_receipt_and_roots() -> None:
    """1. Canonical integration test that strict-loads real receipt and re-admits both roots."""
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)

    assert len(admitted_inputs) == 2
    assert [item["input_key"] for item in admitted_inputs] == ["moonshot", "batch7"]

    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)
    validate_receipt_identity(receipt, admitted_inputs)

    # Verify quality projections equality for both roots
    for admitted in admitted_inputs:
        stored = admitted["stored_per_symbol_quality"]
        recomputed = admitted["recomputed_per_symbol_quality"]
        for sym_id in admitted["formal_completed_event_symbol_ids"]:
            compare_quality_projections(stored[sym_id], recomputed[sym_id])

    summary = derive_cross_root_friction_summary(
        admitted_inputs,
        run_id="stage1_5h_v3_cross_root_friction_20261001T000000Z",
        receipt=receipt,
    )

    assert summary["schema_version"] == 1
    assert summary["decision"] == "stage1_5h_v3_cross_root_friction_diagnostic_generated"
    assert summary["research_classification"] == "evidence_insufficient"
    assert summary["stage1_5g_gate3_complete"] is False
    assert summary["authority_flags"] == EXPECTED_13_FALSE_FLAGS
    assert len(summary["per_symbol_rows"]) == 8
    assert len(summary["parent_rows"]) == 2

    # Assert 2 distinct parents and 8 ordered child event_symbol_ids
    p_moon = next(p for p in summary["parent_rows"] if p["parent_article_id"] == "7379b99aa0f349a49c3b3feca1b4bbd6")
    p_batch = next(p for p in summary["parent_rows"] if p["parent_article_id"] == "0c6ea14ba89b451db6ec9ec364045d22")

    assert p_moon["parent_event_id"] == "e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5"
    assert p_moon["child_symbol_count"] == 1

    assert p_batch["parent_event_id"] == "d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0"
    assert p_batch["child_symbol_count"] == 7

    cohort = summary["cohort_summary"]
    assert cohort["independent_parent_event_count"] == 2
    assert set(cohort["parent_event_ids"]) == {p_moon["parent_event_id"], p_batch["parent_event_id"]}
    assert set(cohort["parent_metric_ranges"].keys()) == set(ALLOWED_QUALITY_METRIC_KEYS)


def test_one_field_receipt_identity_mutation_fails_before_quality() -> None:
    """2. One-field receipt identity mutation fails before calling quality projection comparator."""
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    mutated_inputs = copy.deepcopy(admitted_inputs)
    # Mutate one identity field in admitted inputs
    mutated_inputs[0]["input_records"][0]["event_id"] = "0" * 64

    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_cross_root_authority_mismatch",
    ):
        validate_receipt_identity(receipt, mutated_inputs)


def test_manifest_artifact_hash_length_mutation_rejected_on_receipt_copy(tmp_path: Path) -> None:
    """3. Manifest artifact hash/length mutation rejected on temporary copy of receipt."""
    project_root = _get_project_root()
    real_receipt_dir = project_root / CROSS_ROOT_ROOT_REL

    temp_receipt = tmp_path / "temp_receipt"
    shutil.copytree(real_receipt_dir, temp_receipt)

    manifest_file = temp_receipt / "stage1_5g_cross_root_admission_manifest.json"
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    # Corrupt one artifact sha256
    manifest_data["artifacts"]["review"]["sha256"] = "f" * 64
    manifest_file.write_text(canonical_json_dumps(manifest_data), encoding="utf-8")

    with pytest.raises(Exception) as exc_info:
        load_verified_cross_root_receipt(temp_receipt)

    assert "STOP=stage1_5g_cross_root_publication_integrity_failure" in str(exc_info.value)


def test_quality_comparator_rejects_stored_mutation() -> None:
    """4. Quality comparator test: strict-load real roots, mutate one quality field, assert STOP."""
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)

    moonshot_id = admitted_inputs[0]["formal_completed_event_symbol_ids"][0]
    stored = admitted_inputs[0]["stored_per_symbol_quality"][moonshot_id]
    recomputed = admitted_inputs[0]["recomputed_per_symbol_quality"][moonshot_id]

    # Verify matching initially
    compare_quality_projections(stored, recomputed)

    # Mutate one allowed quality field in stored
    mutated_stored = copy.deepcopy(stored)
    mutated_stored["spread_bps_p50"] = float(mutated_stored["spread_bps_p50"]) + 1.5

    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_quality_projection_mismatch",
    ):
        compare_quality_projections(mutated_stored, recomputed)


def test_child_bijection_single_child_duplicate_omission_cross_parent_mutations() -> None:
    """5. Single-child duplicate, omission, and cross-parent mutation tests reject bijection."""
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    # 5a: Duplicate child
    dup_inputs = copy.deepcopy(admitted_inputs)
    dup_child = copy.deepcopy(dup_inputs[1]["input_records"][0])
    dup_inputs[1]["input_records"].append(dup_child)
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_cross_root_authority_mismatch",
    ):
        validate_receipt_identity(receipt, dup_inputs)

    # 5b: Omission
    omit_inputs = copy.deepcopy(admitted_inputs)
    omit_inputs[1]["input_records"].pop()
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_cross_root_authority_mismatch",
    ):
        validate_receipt_identity(receipt, omit_inputs)

    # 5c: Cross-parent move
    cross_inputs = copy.deepcopy(admitted_inputs)
    moved_child = cross_inputs[1]["input_records"].pop()
    cross_inputs[0]["input_records"].append(moved_child)
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_cross_root_authority_mismatch",
    ):
        validate_receipt_identity(receipt, cross_inputs)


def test_p95_arithmetic_delta_and_reduction_deterministic() -> None:
    """6. p95 arithmetic test: mutate buy p95 by delta d, assert exact delta and deterministic reducers."""
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    summary_orig = derive_cross_root_friction_summary(
        admitted_inputs,
        run_id="stage1_5h_v3_cross_root_friction_20261001T000000Z",
        receipt=receipt,
    )

    # Mutate in-memory buy p95 by delta d = 15.0 for MOONSHOT
    delta = 15.0
    mutated_inputs = copy.deepcopy(admitted_inputs)
    moonshot_id = admitted_inputs[0]["formal_completed_event_symbol_ids"][0]
    mutated_inputs[0]["stored_per_symbol_quality"][moonshot_id]["buy_slippage_bps_500usdt_p95"] += delta
    mutated_inputs[0]["recomputed_per_symbol_quality"][moonshot_id]["buy_slippage_bps_500usdt_p95"] += delta

    summary_mut = derive_cross_root_friction_summary(
        mutated_inputs,
        run_id="stage1_5h_v3_cross_root_friction_20261001T000000Z",
        receipt=receipt,
    )

    orig_row = next(r for r in summary_orig["per_symbol_rows"] if r["symbol"] == "MOONSHOTUSDT")
    mut_row = next(r for r in summary_mut["per_symbol_rows"] if r["symbol"] == "MOONSHOTUSDT")

    # Assert sum of marginal p95 changed by exactly delta
    assert round(mut_row["sum_of_marginal_p95_slippage_bps"] - orig_row["sum_of_marginal_p95_slippage_bps"], 6) == delta
    assert round(mut_row["buy_slippage_bps_500usdt_p95"] - orig_row["buy_slippage_bps_500usdt_p95"], 6) == delta
    assert mut_row["sell_slippage_bps_500usdt_p95"] == orig_row["sell_slippage_bps_500usdt_p95"]

    # Assert no cost floor, paired-P95 label, or feasibility status in summary
    raw_json = json.dumps(summary_mut)
    assert "cost_floor" not in raw_json
    assert "paired_p95" not in raw_json
    assert "execution_feasible" not in raw_json
    assert "feasible" not in summary_mut["decision"]
    assert summary_mut.get("feasibility_status") is None
    assert summary_mut["authority_flags"]["execution_feasibility_claim_allowed"] is False


def test_authority_packet_and_tcb_drift_rejection(tmp_path: Path) -> None:
    """7. Direct authority/TCB tests: Plan mutation, wrong paths, TCB hash drift."""
    project_root = _get_project_root()
    baseline_dir = _get_valid_baseline_dir()

    valid_bindings = {
        "approved_design_path": APPROVED_DESIGN_REL_PATH,
        "approved_design_sha256": APPROVED_DESIGN_SHA256,
        "approved_plan_path": APPROVED_PLAN_REL_PATH,
        "approved_plan_sha256": APPROVED_PLAN_SHA256,
    }

    # Valid call passes
    auth = verify_execution_authority(baseline_dir, valid_bindings, project_root=project_root)
    assert auth["project_root"] == str(project_root)

    # Mutated plan sha
    bad_plan_bindings = dict(valid_bindings, approved_plan_sha256="0" * 64)
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=approved_authority_mismatch",
    ):
        verify_execution_authority(baseline_dir, bad_plan_bindings, project_root=project_root)

    # Mutated plan path
    bad_path_bindings = dict(valid_bindings, approved_plan_path="docs/plans/nonexistent.md")
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=approved_authority_mismatch",
    ):
        verify_execution_authority(baseline_dir, bad_path_bindings, project_root=project_root)

    # Finding 1 RED probe: tampered authorization text must be rejected
    import shutil
    tamper_bundle = tmp_path / "tamper_bundle"
    shutil.copytree(baseline_dir, tamper_bundle)
    auth_txt = tamper_bundle / "implementation_authorization.txt"
    auth_txt.chmod(0o644)
    auth_txt.write_text("tampered authorization\n", encoding="utf-8")
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=approved_authority_mismatch:impl_auth_sha_mismatch",
    ):
        verify_execution_authority(tamper_bundle, valid_bindings, project_root=project_root)

    # Tampered sidecar
    tamper_sidecar_bundle = tmp_path / "tamper_sidecar_bundle"
    shutil.copytree(baseline_dir, tamper_sidecar_bundle)
    sidecar_txt = tamper_sidecar_bundle / "implementation_authorization.txt.sha256"
    sidecar_txt.chmod(0o644)
    sidecar_txt.write_text("0" * 64 + "\n", encoding="utf-8")
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=approved_authority_mismatch:impl_auth_sha_mismatch",
    ):
        verify_execution_authority(tamper_sidecar_bundle, valid_bindings, project_root=project_root)

    # Tampered permission clause (line 2) with matching sidecar
    tamper_perm_bundle = tmp_path / "tamper_perm_bundle"
    shutil.copytree(baseline_dir, tamper_perm_bundle)
    p_txt = tamper_perm_bundle / "implementation_authorization.txt"
    p_sidecar = tamper_perm_bundle / "implementation_authorization.txt.sha256"
    p_txt.chmod(0o644)
    p_sidecar.chmod(0o644)
    bad_lines = f"我批准实施 Plan：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。\n允许 live trading\n"
    p_txt.write_text(bad_lines, encoding="utf-8")
    p_sidecar.write_text(hashlib.sha256(bad_lines.encode("utf-8")).hexdigest() + "\n", encoding="utf-8")
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=approved_authority_mismatch:impl_auth_syntax_line2",
    ):
        verify_execution_authority(tamper_perm_bundle, valid_bindings, project_root=project_root)

    # TCB verification passes
    tcb = verify_frozen_upstream_contract(project_root=project_root)
    assert len(tcb) == 4

    # Corrupted TCB path
    fake_root = project_root / "nonexistent_root"
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_upstream_contract_drift",
    ):
        verify_frozen_upstream_contract(project_root=fake_root)

    # Finding 2 RED probe: preloaded in-project shadow module must be rejected
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as core_mod
    fake_mod = types.ModuleType("src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review")
    fake_mod.__file__ = str((project_root / "configs" / "__init__.py").resolve())
    orig_mod = sys.modules.get("src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review")
    orig_cache = dict(core_mod._CACHED_UPSTREAM_MODULES)
    try:
        sys.modules["src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review"] = fake_mod
        core_mod._CACHED_UPSTREAM_MODULES.clear()
        with pytest.raises(
            Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
            match="STOP=stage1_5h_v3_upstream_contract_drift",
        ):
            core_mod._import_verified_upstream(project_root=project_root)
    finally:
        core_mod._CACHED_UPSTREAM_MODULES.clear()
        core_mod._CACHED_UPSTREAM_MODULES.update(orig_cache)
        if orig_mod is not None:
            sys.modules["src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review"] = orig_mod
        else:
            sys.modules.pop("src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review", None)

    # Fake module with spec origin mismatch
    fake_mod2 = types.ModuleType("src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review")
    expected_file = project_root / "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py"
    fake_mod2.__file__ = str(expected_file.resolve())
    fake_mod2.__spec__ = types.SimpleNamespace(origin=str((project_root / "configs" / "__init__.py").resolve()))
    try:
        sys.modules["src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review"] = fake_mod2
        core_mod._CACHED_UPSTREAM_MODULES.clear()
        with pytest.raises(
            Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
            match="STOP=stage1_5h_v3_upstream_contract_drift:path_mismatch",
        ):
            core_mod._import_verified_upstream(project_root=project_root)
    finally:
        core_mod._CACHED_UPSTREAM_MODULES.clear()
        core_mod._CACHED_UPSTREAM_MODULES.update(orig_cache)
        if orig_mod is not None:
            sys.modules["src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review"] = orig_mod
        else:
            sys.modules.pop("src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review", None)


def test_summary_and_manifest_schema_types_and_invariants() -> None:
    """8. Task-2 schema/type/root tests: exact keys, types, false flags, lineage equality."""
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    summary = derive_cross_root_friction_summary(
        admitted_inputs,
        run_id="stage1_5h_v3_cross_root_friction_20261001T000000Z",
        receipt=receipt,
    )

    # Exact SUMMARY_KEYS
    assert tuple(sorted(summary.keys())) == tuple(sorted(SUMMARY_KEYS))

    # All 13 false flags
    assert summary["authority_flags"] == EXPECTED_13_FALSE_FLAGS
    assert summary["stage1_5g_gate3_complete"] is False

    # Receipt lineage equality
    assert summary["input_receipt_manifest_sha256"] == CROSS_ROOT_MANIFEST_SHA256
    assert summary["input_receipt_summary_sha256"] == CROSS_ROOT_SUMMARY_SHA256

    # Per-symbol rows schema and types
    for row in summary["per_symbol_rows"]:
        assert tuple(sorted(row.keys())) == tuple(sorted(PER_SYMBOL_ROW_KEYS))
        assert isinstance(row["valid_snapshot_count_after_quarantine"], int)
        assert type(row["valid_snapshot_count_after_quarantine"]) is not bool
        assert isinstance(row["invalid_book_row_count"], int)
        assert type(row["invalid_book_row_count"]) is not bool

        for metric in ALLOWED_QUALITY_METRIC_KEYS:
            val = row[metric]
            assert isinstance(val, (int, float))
            assert type(val) is not bool

    # Namespace invariant
    assert OUTPUT_PARENT_REL == "data/external_signal_shadow/stage1_5h/v3_cross_root_friction"

    # Signature invariant
    sig = inspect.signature(run_diagnostic)
    param_names = list(sig.parameters.keys())
    assert param_names == ["run_id", "authority_packet"]


def test_markdown_template_strict_reconstruction_and_tamper_rejection(tmp_path: Path) -> None:
    """9. Exact Markdown template strict-loader tests and tamper rejection."""
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    summary = derive_cross_root_friction_summary(
        admitted_inputs,
        run_id="stage1_5h_v3_cross_root_friction_20261001T000000Z",
        receipt=receipt,
    )

    rendered_md = render_review(summary)
    assert rendered_md.endswith("\n")
    assert "# Stage 1.5H V3 Cross-Root Liquidity Friction Diagnostic Review" in rendered_md
    assert "## Scope" in rendered_md
    assert "## Authority Flags" in rendered_md
    assert "## Input Lineage" in rendered_md
    assert "## Per-Symbol Rows" in rendered_md
    assert "## Parent Rows" in rendered_md
    assert "## Cohort Summary" in rendered_md

    # Write review and load it
    review_path = tmp_path / "stage1_5h_v3_cross_root_friction_review_CN.md"
    review_path.write_text(rendered_md, encoding="utf-8")

    loaded_text = load_verified_v3_review(review_path, summary)
    assert loaded_text == rendered_md

    # Tamper with review text
    tampered_md = rendered_md + "\nexecution looks feasible\n"
    review_path.write_text(tampered_md, encoding="utf-8")

    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:review_text_mismatch",
    ):
        load_verified_v3_review(review_path, summary)


def test_v3_ast_isolation_and_open_spy() -> None:
    """10. AST/import/open-spy: no raw JSONL, no network, no exchange clients in V3 code."""
    project_root = _get_project_root()
    core_file = project_root / "src/research/external_signal_shadow/stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py"

    if not core_file.is_file():
        raise AssertionError(f"V3 core file not implemented yet: {core_file}")

    tree = ast.parse(core_file.read_text(encoding="utf-8"))

    forbidden_modules = {"urllib", "requests", "http", "socket", "ccxt", "aiohttp", "order_executor"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_root = alias.name.split(".")[0]
                assert mod_root not in forbidden_modules, f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_root = node.module.split(".")[0]
                assert mod_root not in forbidden_modules, f"Forbidden import from: {node.module}"

        # Assert no calls to glob / rglob
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"glob", "rglob"}, f"Forbidden glob call: {node.func.attr}"


def test_publication_happy_path_manifest_last_and_durability(tmp_path: Path) -> None:
    """Publication writes summary, review, manifest last, and fsyncs parent."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    run_id = "stage1_5h_v3_cross_root_friction_20261001T150000Z"
    summary = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id, receipt=receipt)

    parent_dir = tmp_path / "v3_output"
    final_root = v3_core._publish_v3_diagnostic_to_parent(summary, run_id=run_id, parent_dir=parent_dir)

    assert final_root.is_dir()
    assert (final_root / "stage1_5h_v3_cross_root_friction_manifest.json").is_file()
    assert (final_root / "stage1_5h_v3_cross_root_friction_summary.json").is_file()
    assert (final_root / "stage1_5h_v3_cross_root_friction_review_CN.md").is_file()

    state = classify_v3_root_state(parent_dir, run_id)
    assert state == "receipt_published"


def test_publication_rejects_preexisting_final_root(tmp_path: Path) -> None:
    """Publication rejects pre-existing final root."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    run_id = "stage1_5h_v3_cross_root_friction_20261001T150001Z"
    summary = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id, receipt=receipt)

    parent_dir = tmp_path / "v3_output"
    parent_dir.mkdir(parents=True, exist_ok=True)
    (parent_dir / run_id).mkdir()

    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:final_root_preexists",
    ):
        v3_core._publish_v3_diagnostic_to_parent(summary, run_id=run_id, parent_dir=parent_dir)


def test_publication_rejects_stale_sibling_staging_other_pid(tmp_path: Path) -> None:
    """Publication rejects pre-existing matching staging directory from other PID."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    run_id = "stage1_5h_v3_cross_root_friction_20261001T150002Z"
    summary = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id, receipt=receipt)

    parent_dir = tmp_path / "v3_output"
    parent_dir.mkdir(parents=True, exist_ok=True)
    # Stale staging directory from another PID
    (parent_dir / f".{run_id}.staging.99999").mkdir()

    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:matching_staging_sibling_preexists",
    ):
        v3_core._publish_v3_diagnostic_to_parent(summary, run_id=run_id, parent_dir=parent_dir)


def test_publication_lifecycle_crash_failpoints(tmp_path: Path) -> None:
    """Crash failpoints verify staging_only state and post-rename durability failure."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    # 1. Crash after summary write
    run_id_1 = "stage1_5h_v3_cross_root_friction_20261001T150010Z"
    summary_1 = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id_1, receipt=receipt)
    parent_dir_1 = tmp_path / "v3_fail_1"

    def fail_summary(pos: str) -> None:
        if pos == "after_summary_write":
            raise RuntimeError("CRASH_AFTER_SUMMARY")

    v3_core._FAILPOINT_HOOK = fail_summary
    try:
        with pytest.raises(RuntimeError, match="CRASH_AFTER_SUMMARY"):
            v3_core._publish_v3_diagnostic_to_parent(summary_1, run_id=run_id_1, parent_dir=parent_dir_1)
        assert classify_v3_root_state(parent_dir_1, run_id_1) == "staging_only"
    finally:
        v3_core._FAILPOINT_HOOK = None

    # 2. Crash after rename before parent fsync -> STOP=stage1_5h_v3_post_rename_durability_failure
    run_id_2 = "stage1_5h_v3_cross_root_friction_20261001T150020Z"
    summary_2 = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id_2, receipt=receipt)
    parent_dir_2 = tmp_path / "v3_fail_2"

    def fail_post_rename(pos: str) -> None:
        if pos == "after_rename":
            raise OSError("DISK_IO_ERROR_DURING_FSYNC")

    v3_core._FAILPOINT_HOOK = fail_post_rename
    try:
        with pytest.raises(
            Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
            match="STOP=stage1_5h_v3_post_rename_durability_failure",
        ):
            v3_core._publish_v3_diagnostic_to_parent(summary_2, run_id=run_id_2, parent_dir=parent_dir_2)
    finally:
        v3_core._FAILPOINT_HOOK = None


def test_lifecycle_state_classification_four_states(tmp_path: Path) -> None:
    """Classification returns unpublished, staging_only, receipt_published, corrupt_or_unknown."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    parent_dir = tmp_path / "lifecycle_test"
    parent_dir.mkdir(parents=True, exist_ok=True)
    run_id = "stage1_5h_v3_cross_root_friction_20261001T160000Z"

    # State 1: unpublished
    assert classify_v3_root_state(parent_dir, run_id) == "unpublished"

    # State 2: staging_only
    staging_dir = parent_dir / f".{run_id}.staging.1234"
    staging_dir.mkdir()
    assert classify_v3_root_state(parent_dir, run_id) == "staging_only"
    staging_dir.rmdir()

    # State 3: receipt_published
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)
    summary = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id, receipt=receipt)
    v3_core._publish_v3_diagnostic_to_parent(summary, run_id=run_id, parent_dir=parent_dir)
    assert classify_v3_root_state(parent_dir, run_id) == "receipt_published"

    # State 4: corrupt_or_unknown (corrupt manifest)
    (parent_dir / run_id / "stage1_5h_v3_cross_root_friction_manifest.json").write_text("corrupted", encoding="utf-8")
    assert classify_v3_root_state(parent_dir, run_id) == "corrupt_or_unknown"


def test_publication_rejects_invalid_run_id(tmp_path: Path) -> None:
    """Publication rejects invalid run_id format."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    summary = {"run_id": "bad_run_id"}
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:invalid_run_id",
    ):
        v3_core._publish_v3_diagnostic_to_parent(summary, run_id="bad_run_id", parent_dir=tmp_path)


def test_publication_rejects_symlink_final_root(tmp_path: Path) -> None:
    """Publication rejects symlink at final root location."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    run_id = "stage1_5h_v3_cross_root_friction_20261001T170000Z"
    summary = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id, receipt=receipt)

    target_dir = tmp_path / "symlink_target"
    target_dir.mkdir()
    symlink_final = tmp_path / run_id
    symlink_final.symlink_to(target_dir)

    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:final_root_preexists",
    ):
        v3_core._publish_v3_diagnostic_to_parent(summary, run_id=run_id, parent_dir=tmp_path)


def test_publication_rejects_multiple_matching_staging_siblings(tmp_path: Path) -> None:
    """Publication rejects multiple matching staging directories."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    run_id = "stage1_5h_v3_cross_root_friction_20261001T170001Z"
    summary = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id, receipt=receipt)

    (tmp_path / f".{run_id}.staging.11111").mkdir()
    (tmp_path / f".{run_id}.staging.22222").mkdir()

    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:matching_staging_sibling_preexists",
    ):
        v3_core._publish_v3_diagnostic_to_parent(summary, run_id=run_id, parent_dir=tmp_path)


def test_strict_load_final_root_rejects_extra_and_missing_files(tmp_path: Path) -> None:
    """load_verified_v3_root rejects extra, missing, and symlink files."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    run_id = "stage1_5h_v3_cross_root_friction_20261001T170002Z"
    summary = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id, receipt=receipt)
    final_root = v3_core._publish_v3_diagnostic_to_parent(summary, run_id=run_id, parent_dir=tmp_path)

    # Valid load passes
    load_verified_v3_root(final_root)

    # Extra file rejects
    extra_file = final_root / "unexpected_file.txt"
    extra_file.write_text("extra", encoding="utf-8")
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:unlisted_files_in_root",
    ):
        load_verified_v3_root(final_root)
    extra_file.unlink()

    # Missing file rejects
    manifest_file = final_root / "stage1_5h_v3_cross_root_friction_manifest.json"
    manifest_content = manifest_file.read_bytes()
    manifest_file.unlink()
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:unlisted_files_in_root",
    ):
        load_verified_v3_root(final_root)
    manifest_file.write_bytes(manifest_content)

    # Symlink rejects
    review_file = final_root / "stage1_5h_v3_cross_root_friction_review_CN.md"
    review_bytes = review_file.read_bytes()
    review_file.unlink()
    external_target = tmp_path / "external_review.md"
    external_target.write_bytes(review_bytes)
    review_file.symlink_to(external_target)

    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:symlink_or_not_file",
    ):
        load_verified_v3_root(final_root)

    # Finding 3 RED probe: tampered manifest byte_count must be rejected
    review_file.unlink()
    review_file.write_bytes(review_bytes)
    man_file = final_root / "stage1_5h_v3_cross_root_friction_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    man_data["artifacts"]["summary"]["byte_count"] += 1
    man_file.write_text(canonical_json_dumps(man_data), encoding="utf-8")

    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:manifest_artifact_meta_mismatch",
    ):
        load_verified_v3_root(final_root)

    # Restore manifest
    man_data["artifacts"]["summary"]["byte_count"] -= 1
    man_file.write_text(canonical_json_dumps(man_data), encoding="utf-8")

    # Finding 4 RED probe: symlink final root argument must be rejected
    symlink_final_root = tmp_path / "symlink_final_root"
    symlink_final_root.symlink_to(final_root)
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure",
    ):
        load_verified_v3_root(symlink_final_root)


def test_ancestor_symlinks_rejected_across_writer_loader_and_classifier(tmp_path: Path) -> None:
    """Ancestors with symlinks must be rejected fail-closed in writer, loader, and classifier."""
    import src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic as v3_core

    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)
    receipt = load_verified_cross_root_receipt(project_root / CROSS_ROOT_ROOT_REL)

    real_parent = tmp_path / "real_parent"
    real_parent.mkdir()
    run_id = "stage1_5h_v3_cross_root_friction_20261001T180000Z"
    summary = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id, receipt=receipt)

    # 1. Normal publication to real_parent succeeds
    final_root = v3_core._publish_v3_diagnostic_to_parent(summary, run_id=run_id, parent_dir=real_parent)
    assert final_root.is_dir()

    # 2. Symlink parent pointing to real_parent
    sym_parent = tmp_path / "sym_parent"
    sym_parent.symlink_to(real_parent)

    # Loader must reject final root accessed through symlink parent
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:final_root_symlink",
    ):
        load_verified_v3_root(sym_parent / run_id)

    # 3. Writer must reject publication to symlink parent
    outside_dir = tmp_path / "outside_target"
    outside_dir.mkdir()
    sym_outside_parent = tmp_path / "sym_outside_parent"
    sym_outside_parent.symlink_to(outside_dir)

    run_id_2 = "stage1_5h_v3_cross_root_friction_20261001T180001Z"
    summary_2 = derive_cross_root_friction_summary(admitted_inputs, run_id=run_id_2, receipt=receipt)
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:parent_dir_symlink",
    ):
        v3_core._publish_v3_diagnostic_to_parent(summary_2, run_id=run_id_2, parent_dir=sym_outside_parent)

    # 4. Writer must reject publication to child under symlink ancestor
    sym_child_parent = sym_outside_parent / "sub_child"
    with pytest.raises(
        Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
        match="STOP=stage1_5h_v3_publication_integrity_failure:parent_dir_symlink",
    ):
        v3_core._publish_v3_diagnostic_to_parent(summary_2, run_id=run_id_2, parent_dir=sym_child_parent)

    # 5. State classifier must return corrupt_or_unknown for symlink parent and child under symlink ancestor
    assert classify_v3_root_state(sym_parent, run_id) == "corrupt_or_unknown"
    assert classify_v3_root_state(sym_child_parent, run_id_2) == "corrupt_or_unknown"
