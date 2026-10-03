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

try:
    from src.research.external_signal_shadow.stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic import (
        ALLOWED_CONTEXT_METRIC_KEYS,
        ALLOWED_DERIVED_METRIC_KEYS,
        ALLOWED_QUALITY_METRIC_KEYS,
        APPROVED_DESIGN_REL_PATH,
        APPROVED_DESIGN_SHA256,
        APPROVED_PLAN_REL_PATH,
        APPROVED_PLAN_SHA256,
        EXPECTED_13_FALSE_FLAGS,
        FROZEN_PRODUCT_REGIME_IDS,
        FROZEN_SOURCE_ROOT_RECORDS,
        FROZEN_UPSTREAM_MODULES,
        INPUT_RECEIPT_KEYS,
        INPUT_SOURCE_ROOTS_KEYS,
        MANIFEST_ARTIFACT_KEYS,
        MANIFEST_KEYS,
        N3_MANIFEST_SHA256,
        N3_RECEIPT_REL_PATH,
        N3_REVIEW_SHA256,
        N3_SUMMARY_SHA256,
        OUTPUT_PARENT_REL,
        PARENT_ROW_KEYS,
        PER_SYMBOL_ROW_KEYS,
        REVIEWED_PLANNING_BASE_SHA,
        SUMMARY_KEYS,
        Stage1_5HN3PostRenameDurabilityFailure,
        Stage1_5HN3RegimeFrictionError,
        _classify_n3_friction_root_state_for_test,
        _import_verified_upstream,
        _load_verified_n3_friction_root_for_test,
        _publish_n3_friction_receipt_for_lifecycle_test,
        admit_frozen_n3_source_inputs,
        classify_n3_friction_root_state,
        compare_source_identity_and_quality,
        derive_n3_friction_summary,
        get_canonical_execution_authority_bundle_path,
        load_verified_n3_friction_manifest,
        load_verified_n3_friction_review,
        load_verified_n3_friction_root,
        load_verified_n3_friction_summary,
        publish_n3_friction_receipt,
        render_review,
        run_diagnostic,
        verify_execution_authority,
        verify_frozen_upstream_contract,
        verify_local_receipt_generation_authority,
    )
except ImportError as _import_err:
    _err_msg = str(_import_err)

    def _unimplemented_stub(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(f"Stage 1.5H N=3 module not yet implemented: {_err_msg}")

    ALLOWED_CONTEXT_METRIC_KEYS = ()  # type: ignore[assignment]
    ALLOWED_DERIVED_METRIC_KEYS = ()  # type: ignore[assignment]
    ALLOWED_QUALITY_METRIC_KEYS = ()  # type: ignore[assignment]
    APPROVED_DESIGN_REL_PATH = ""  # type: ignore[assignment]
    APPROVED_DESIGN_SHA256 = ""  # type: ignore[assignment]
    APPROVED_PLAN_REL_PATH = ""  # type: ignore[assignment]
    APPROVED_PLAN_SHA256 = ""  # type: ignore[assignment]
    EXPECTED_13_FALSE_FLAGS = {}  # type: ignore[assignment]
    FROZEN_PRODUCT_REGIME_IDS = ()  # type: ignore[assignment]
    FROZEN_SOURCE_ROOT_RECORDS = []  # type: ignore[assignment]
    FROZEN_UPSTREAM_MODULES = {}  # type: ignore[assignment]
    INPUT_RECEIPT_KEYS = ()  # type: ignore[assignment]
    INPUT_SOURCE_ROOTS_KEYS = ()  # type: ignore[assignment]
    MANIFEST_ARTIFACT_KEYS = ()  # type: ignore[assignment]
    MANIFEST_KEYS = ()  # type: ignore[assignment]
    N3_MANIFEST_SHA256 = ""  # type: ignore[assignment]
    N3_RECEIPT_REL_PATH = ""  # type: ignore[assignment]
    N3_REVIEW_SHA256 = ""  # type: ignore[assignment]
    N3_SUMMARY_SHA256 = ""  # type: ignore[assignment]
    OUTPUT_PARENT_REL = ""  # type: ignore[assignment]
    PARENT_ROW_KEYS = ()  # type: ignore[assignment]
    PER_SYMBOL_ROW_KEYS = ()  # type: ignore[assignment]
    REVIEWED_PLANNING_BASE_SHA = ""  # type: ignore[assignment]
    SUMMARY_KEYS = ()  # type: ignore[assignment]

    class Stage1_5HN3RegimeFrictionError(Exception):  # type: ignore[no-redef]
        pass

    class Stage1_5HN3PostRenameDurabilityFailure(Stage1_5HN3RegimeFrictionError):  # type: ignore[no-redef]
        pass

    _import_verified_upstream = _unimplemented_stub  # type: ignore[assignment]
    _classify_n3_friction_root_state_for_test = _unimplemented_stub  # type: ignore[assignment]
    _load_verified_n3_friction_root_for_test = _unimplemented_stub  # type: ignore[assignment]
    _publish_n3_friction_receipt_for_lifecycle_test = _unimplemented_stub  # type: ignore[assignment]
    admit_frozen_n3_source_inputs = _unimplemented_stub  # type: ignore[assignment]
    classify_n3_friction_root_state = _unimplemented_stub  # type: ignore[assignment]
    compare_source_identity_and_quality = _unimplemented_stub  # type: ignore[assignment]
    derive_n3_friction_summary = _unimplemented_stub  # type: ignore[assignment]
    get_canonical_execution_authority_bundle_path = _unimplemented_stub  # type: ignore[assignment]
    load_verified_n3_friction_manifest = _unimplemented_stub  # type: ignore[assignment]
    load_verified_n3_friction_review = _unimplemented_stub  # type: ignore[assignment]
    load_verified_n3_friction_root = _unimplemented_stub  # type: ignore[assignment]
    load_verified_n3_friction_summary = _unimplemented_stub  # type: ignore[assignment]
    publish_n3_friction_receipt = _unimplemented_stub  # type: ignore[assignment]
    render_review = _unimplemented_stub  # type: ignore[assignment]
    run_diagnostic = _unimplemented_stub  # type: ignore[assignment]
    verify_execution_authority = _unimplemented_stub  # type: ignore[assignment]
    verify_frozen_upstream_contract = _unimplemented_stub  # type: ignore[assignment]
    verify_local_receipt_generation_authority = _unimplemented_stub  # type: ignore[assignment]


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _get_task0_bundle_dir() -> Path:
    plan_sha = "9d9ebe80fa0560d9ae60df412d32fec3b5e839ec3073e93b4be9a661a5fded42"
    bundle_dir = _get_project_root() / f".git/plan-execution/stage1_5h_n3_regime/{plan_sha}"
    if not bundle_dir.is_dir():
        pytest.skip(f"Task 0 bundle directory not found: {bundle_dir}")
    return bundle_dir


# ---------------------------------------------------------------------------
# Task 1 Canonical Fixture & Positive Cross-Boundary Test
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def canonical_admitted_sources():
    """Canonical upstream fixture: loads N=3 receipt and re-admits all 3 frozen source roots."""
    project_root = _get_project_root()
    return admit_frozen_n3_source_inputs(project_root=project_root)


def test_canonical_positive_fixture_and_real_root_re_admission(canonical_admitted_sources):
    """Proves canonical fixture loads N=3 receipt and re-admits all 3 roots without error."""
    sources = canonical_admitted_sources
    assert len(sources) == 3
    assert [s["input_key"] for s in sources] == ["moonshot", "batch7", "ct_projection"]

    summary = derive_n3_friction_summary(
        sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )

    assert summary["schema_version"] == 1
    assert summary["decision"] == "stage1_5h_n3_regime_stratified_friction_diagnostic_generated"
    assert summary["research_classification"] == "evidence_insufficient"
    assert summary["independent_parent_event_count"] == 3
    assert summary["stage1_5g_gate3_complete"] is False
    assert summary["authority_flags"] == EXPECTED_13_FALSE_FLAGS

    # Verify per_symbol_rows: exactly 9 rows
    per_symbol_rows = summary["per_symbol_rows"]
    assert len(per_symbol_rows) == 9

    expected_symbols = [
        "MOONSHOTUSDT",
        "ACNUSDT",
        "BWETUSDT",
        "CRMLUSDT",
        "MPUSDT",
        "NKEUSDT",
        "SECZUSDT",
        "UNHUSDT",
        "CTUSDT",
    ]
    actual_symbols = [r["symbol"] for r in per_symbol_rows]
    assert set(actual_symbols) == set(expected_symbols)

    # Verify parent_rows: exactly 3 rows
    parent_rows = summary["parent_rows"]
    assert len(parent_rows) == 3
    assert [p["child_symbol_count"] for p in parent_rows] == [1, 7, 1]

    # Verify CT child duplicate proof: only CTUSDT emitted from ct_projection
    ct_row = next(r for r in per_symbol_rows if r["symbol"] == "CTUSDT")
    assert ct_row["product_regime_id"] == "crypto_standard_perpetual"


# ---------------------------------------------------------------------------
# Task 1 Negative Probes: Authority & Upstream Contracts
# ---------------------------------------------------------------------------

def test_verify_execution_authority_success():
    """Task 0 canonical bundle must pass execution authority verification."""
    bundle_dir = _get_task0_bundle_dir()
    authority = verify_execution_authority(bundle_dir=bundle_dir, project_root=_get_project_root())
    assert authority["approved_plan_sha256"] == "9d9ebe80fa0560d9ae60df412d32fec3b5e839ec3073e93b4be9a661a5fded42"
    assert authority["base_sha"] == "9484dd3eedbc10a2edd4a2ded46a1ecc2ab54e91"


def test_verify_execution_authority_rejects_tampered_sidecar(tmp_path):
    """Mutating execution_authority.sha256 sidecar triggers fail-closed STOP."""
    bundle_dir = _get_task0_bundle_dir()
    test_bundle = tmp_path / "bundle"
    shutil.copytree(bundle_dir, test_bundle)

    # Mutate execution_authority.sha256
    sidecar_path = test_bundle / "execution_authority.sha256"
    sidecar_path.write_text("0" * 64 + "  execution_authority.json\n", encoding="utf-8")

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        verify_execution_authority(bundle_dir=test_bundle, project_root=_get_project_root())
    assert "authority_sidecar_mismatch" in str(exc_info.value)


def test_verify_execution_authority_rejects_plan_sha_mismatch(tmp_path):
    """Mutating approved_plan_sha256 inside execution_authority.json triggers STOP."""
    bundle_dir = _get_task0_bundle_dir()
    test_bundle = tmp_path / "bundle"
    shutil.copytree(bundle_dir, test_bundle)

    auth_json = test_bundle / "execution_authority.json"
    data = json.loads(auth_json.read_bytes())
    data["approved_plan_sha256"] = "f" * 64
    new_bytes = canonical_json_dumps(data).encode("utf-8")
    auth_json.write_bytes(new_bytes)
    (test_bundle / "execution_authority.sha256").write_text(
        f"{hashlib.sha256(new_bytes).hexdigest()}  execution_authority.json\n",
        encoding="utf-8",
    )

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        verify_execution_authority(bundle_dir=test_bundle, project_root=_get_project_root())
    assert "plan_sha256_mismatch" in str(exc_info.value)


def test_verify_execution_authority_rejects_base_sha_mismatch(tmp_path):
    """Mutating base_sha triggers fail-closed STOP."""
    bundle_dir = _get_task0_bundle_dir()
    test_bundle = tmp_path / "bundle"
    shutil.copytree(bundle_dir, test_bundle)

    (test_bundle / "base_sha").write_bytes(b"e" * 40)

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        verify_execution_authority(bundle_dir=test_bundle, project_root=_get_project_root())
    assert "base_sha_mismatch" in str(exc_info.value)


def test_verify_execution_authority_rejects_implementation_auth_text_substitution(tmp_path):
    """Substituted implementation authorization text with valid sidecar is rejected."""
    bundle_dir = _get_task0_bundle_dir()
    test_bundle = tmp_path / "bundle"
    shutil.copytree(bundle_dir, test_bundle)

    fake_text = "我批准实施 Plan：fake_plan.md（SHA-256: 0000000000000000000000000000000000000000000000000000000000000000）。\n允许 implementation；不允许 commit。"
    auth_txt = test_bundle / "implementation_authorization.txt"
    auth_txt.write_text(fake_text, encoding="utf-8")
    new_sha = hashlib.sha256(fake_text.encode("utf-8")).hexdigest()
    (test_bundle / "implementation_authorization.sha256").write_text(
        f"{new_sha}  implementation_authorization.txt\n", encoding="utf-8"
    )

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        verify_execution_authority(bundle_dir=test_bundle, project_root=_get_project_root())
    assert "implementation_auth" in str(exc_info.value)


def test_verify_execution_authority_rejects_implementation_auth_symlink(tmp_path):
    """Symlinked implementation_authorization.txt is rejected before read."""
    bundle_dir = _get_task0_bundle_dir()
    test_bundle = tmp_path / "bundle"
    shutil.copytree(bundle_dir, test_bundle)

    auth_txt = test_bundle / "implementation_authorization.txt"
    real_file = tmp_path / "real_auth.txt"
    real_file.write_bytes(auth_txt.read_bytes())
    auth_txt.unlink()
    auth_txt.symlink_to(real_file)

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        verify_execution_authority(bundle_dir=test_bundle, project_root=_get_project_root())
    assert "implementation_auth_symlink" in str(exc_info.value)


def test_verify_frozen_upstream_contract_rejects_module_byte_drift(monkeypatch):
    """Drift in frozen module SHA256 triggers fail-closed STOP."""
    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        verify_frozen_upstream_contract(
            project_root=_get_project_root(),
            expected_override={
                "src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py": "0" * 64
            },
        )
    assert "frozen_module_hash_mismatch" in str(exc_info.value)


def test_import_verified_upstream_rejects_preloaded_wrong_spec_origin():
    """Preloaded upstream module with wrong __spec__.origin is rejected fail-closed."""
    dummy_mod = types.ModuleType("configs.base")
    dummy_mod.__file__ = str((_get_project_root() / "configs/base.py").resolve())
    dummy_spec = types.SimpleNamespace(origin="/tmp/shadow/configs/base.py")
    dummy_mod.__spec__ = dummy_spec  # type: ignore[assignment]

    old_mod = sys.modules.get("configs.base")
    try:
        sys.modules["configs.base"] = dummy_mod
        with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
            _import_verified_upstream("configs.base", project_root=_get_project_root())
        assert "preloaded_shadow_module_origin" in str(exc_info.value)
    finally:
        if old_mod is not None:
            sys.modules["configs.base"] = old_mod
        else:
            sys.modules.pop("configs.base", None)


def test_verify_local_receipt_generation_authority_rejects_absent_generation_authority():
    """Absent receipt_generation_authorization.txt triggers fail-closed STOP."""
    bundle_dir = _get_task0_bundle_dir()
    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        verify_local_receipt_generation_authority(
            bundle_dir=bundle_dir,
            project_root=_get_project_root(),
            run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
        )
    assert "generation_authorization_missing" in str(exc_info.value)


def test_verify_local_receipt_generation_authority_rejects_forged_five_line_content(tmp_path):
    """Forged five-line generation authority with matching sidecar is rejected."""
    bundle_dir = _get_task0_bundle_dir()
    test_bundle = tmp_path / "bundle"
    shutil.copytree(bundle_dir, test_bundle)

    run_id = "stage1_5h_n3_regime_stratified_friction_20261003T120000Z"
    forged_text = (
        f"我批准本地生成 Stage 1.5H N=3 diagnostic receipt：{APPROVED_PLAN_REL_PATH}（SHA-256: {APPROVED_PLAN_SHA256}）。\n"
        f"RUN_ID: stage1_5h_n3_regime_stratified_friction_99999999T999999Z\n"
        "H_CORE_SHA256: 0000000000000000000000000000000000000000000000000000000000000000\n"
        "H_CLI_SHA256: 0000000000000000000000000000000000000000000000000000000000000000\n"
        "允许仅本地生成 Stage 1.5H N=3 diagnostic receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。\n"
    )
    gen_file = test_bundle / "receipt_generation_authorization.txt"
    gen_file.write_text(forged_text, encoding="utf-8")
    gen_sha = hashlib.sha256(forged_text.encode("utf-8")).hexdigest()
    (test_bundle / "receipt_generation_authorization.sha256").write_text(
        f"{gen_sha}  receipt_generation_authorization.txt\n", encoding="utf-8"
    )

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        verify_local_receipt_generation_authority(
            bundle_dir=test_bundle,
            project_root=_get_project_root(),
            run_id=run_id,
        )
    assert "generation_authorization" in str(exc_info.value)


def test_verify_local_receipt_generation_authority_rejects_generation_auth_symlink(tmp_path):
    """Symlinked receipt_generation_authorization.txt is rejected before read."""
    bundle_dir = _get_task0_bundle_dir()
    test_bundle = tmp_path / "bundle"
    shutil.copytree(bundle_dir, test_bundle)

    run_id = "stage1_5h_n3_regime_stratified_friction_20261003T120000Z"
    real_file = tmp_path / "real_gen.txt"
    real_file.write_text("some content\n", encoding="utf-8")
    gen_file = test_bundle / "receipt_generation_authorization.txt"
    gen_file.symlink_to(real_file)
    (test_bundle / "receipt_generation_authorization.sha256").write_text(
        "0" * 64 + "  receipt_generation_authorization.txt\n", encoding="utf-8"
    )

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        verify_local_receipt_generation_authority(
            bundle_dir=test_bundle,
            project_root=_get_project_root(),
            run_id=run_id,
        )
    assert "generation_auth_symlink" in str(exc_info.value)


def test_run_diagnostic_signature_accepts_only_run_id():
    """Public run_diagnostic entrypoint must accept only run_id parameter."""
    sig = inspect.signature(run_diagnostic)
    params = list(sig.parameters.keys())
    assert params == ["run_id"]


# ---------------------------------------------------------------------------
# Task 1 Negative Probes: Source Re-admission & Quality Comparator
# ---------------------------------------------------------------------------

def test_compare_source_identity_and_quality_rejects_tampered_quality_metric(canonical_admitted_sources):
    """Mutating buy_slippage_bps_500usdt_p95 triggers metric projection mismatch STOP."""
    sources = copy.deepcopy(canonical_admitted_sources)
    moonshot = next(s for s in sources if s["input_key"] == "moonshot")
    child_id = next(iter(moonshot["quality_projection"]))
    # Preconditions verified: sources is real admitted source
    # Single mutation:
    moonshot["quality_projection"][child_id]["quarantined_depth_quality"]["buy_slippage_bps_500usdt_p95"] += 999.0

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        compare_source_identity_and_quality(sources)
    assert "metric_projection_mismatch" in str(exc_info.value)


def test_compare_source_identity_and_quality_rejects_wrong_contract_hash(canonical_admitted_sources):
    """Tampering source_anchor_contract_hash triggers source authority mismatch STOP."""
    sources = copy.deepcopy(canonical_admitted_sources)
    moonshot = next(s for s in sources if s["input_key"] == "moonshot")
    child_id = next(iter(moonshot["quality_projection"]))
    moonshot["contract_hashes"][child_id] = "0" * 64

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        compare_source_identity_and_quality(sources)
    assert "contract_hash_mismatch" in str(exc_info.value)


def test_admit_frozen_n3_source_inputs_rejects_ct_duplicate_deviation(canonical_admitted_sources):
    """Deviating non-CT child in ct_projection root triggers ct_duplicate_mismatch STOP."""
    sources = copy.deepcopy(canonical_admitted_sources)
    ct_source = next(s for s in sources if s["input_key"] == "ct_projection")
    # Mutate one of the 7 duplicate child identities
    non_ct_child = next(c for c in ct_source["all_child_identities"] if c["symbol"] != "CTUSDT")
    non_ct_child["parent_article_id"] = "f" * 32

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        compare_source_identity_and_quality(sources)
    assert "ct_duplicate_mismatch" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Task 1 Negative Probes: Reducer & Schema Validation
# ---------------------------------------------------------------------------

def test_derive_n3_friction_summary_rejects_extra_pooled_key(canonical_admitted_sources):
    """Injecting extra pooled/cohort summary key is rejected under fail-closed scope check."""
    sources = copy.deepcopy(canonical_admitted_sources)
    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        derive_n3_friction_summary(
            sources,
            run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
            extra_test_injection={"pooled_summary": {"mean_spread": 10.0}},
        )
    assert "forbidden_aggregate_key" in str(exc_info.value)


def test_derive_n3_friction_summary_rejects_nan_metric(canonical_admitted_sources):
    """NaN or non-finite metric in input triggers metric projection mismatch STOP."""
    sources = copy.deepcopy(canonical_admitted_sources)
    moonshot = next(s for s in sources if s["input_key"] == "moonshot")
    child_id = next(iter(moonshot["quality_projection"]))
    moonshot["quality_projection"][child_id]["quarantined_depth_quality"]["spread_bps_p50"] = float("nan")

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        derive_n3_friction_summary(
            sources,
            run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
        )
    assert "metric_projection_mismatch" in str(exc_info.value) or "non_finite" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Task 1 Negative Probes: Serialization & Strict Loader
# ---------------------------------------------------------------------------

def test_render_review_matches_template_exact_bytes(canonical_admitted_sources):
    """render_review produces exact deterministic markdown containing required disclaimer."""
    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )
    md = render_review(summary)
    assert "本报告仅描述三个冻结 parent event 的静态 L2 quality metrics；不同 product regime 不作池化、比较、成本地板、执行可行性、Alpha 或交易结论。" in md
    assert md.endswith("\n")


def test_strict_loader_rejects_ancestor_symlink(tmp_path, canonical_admitted_sources):
    """Strict loader rejects any ancestor symlink in path before resolve."""
    # Create real directory tree, then symlink parent
    real_parent = tmp_path / "real_parent"
    real_parent.mkdir()
    symlink_parent = tmp_path / "symlink_parent"
    os.symlink(real_parent, symlink_parent)

    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )
    receipt_dir = _publish_n3_friction_receipt_for_lifecycle_test(summary, parent_dir=real_parent)

    # Attempt to load through symlinked ancestor
    aliased_receipt_dir = symlink_parent / receipt_dir.name
    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        load_verified_n3_friction_root(aliased_receipt_dir)
    assert "parent_dir_symlink" in str(exc_info.value) or "symlink" in str(exc_info.value)


def test_strict_loader_rejects_tampered_manifest_sha(tmp_path, canonical_admitted_sources):
    """Mutating summary SHA256 in manifest.json triggers publication integrity failure STOP."""
    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )
    receipt_dir = _publish_n3_friction_receipt_for_lifecycle_test(summary, parent_dir=tmp_path)

    manifest_p = receipt_dir / "stage1_5h_n3_regime_stratified_friction_manifest.json"
    manifest_data = json.loads(manifest_p.read_bytes())
    manifest_data["artifacts"]["stage1_5h_n3_regime_stratified_friction_summary.json"]["sha256"] = "0" * 64
    manifest_p.write_bytes(canonical_json_dumps(manifest_data).encode("utf-8"))

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        load_verified_n3_friction_manifest(manifest_p)
    assert "manifest_hash_mismatch" in str(exc_info.value)


def test_strict_loader_rejects_noncanonical_output_parent(tmp_path, canonical_admitted_sources):
    """load_verified_n3_friction_root rejects final_root outside canonical output parent."""
    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )
    published_dir = _publish_n3_friction_receipt_for_lifecycle_test(summary, parent_dir=tmp_path)

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        load_verified_n3_friction_root(published_dir)
    assert "noncanonical_output_parent" in str(exc_info.value)


def test_strict_loader_rejects_forged_input_receipt_lineage(tmp_path, canonical_admitted_sources):
    """load_verified_n3_friction_summary rejects forged N=3 input receipt hashes."""
    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )
    summary["input_receipt"]["manifest_sha256"] = "0" * 64
    sum_bytes = canonical_json_dumps(summary).encode("utf-8")
    sum_path = tmp_path / "stage1_5h_n3_regime_stratified_friction_summary.json"
    sum_path.write_bytes(sum_bytes)

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        load_verified_n3_friction_summary(sum_path)
    assert "input_receipt" in str(exc_info.value)


def test_strict_loader_rejects_extra_foreign_artifact(tmp_path, canonical_admitted_sources):
    """load_verified_n3_friction_root rejects unexpected sibling files in final_root."""
    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )
    published_dir = _publish_n3_friction_receipt_for_lifecycle_test(summary, parent_dir=tmp_path)

    (published_dir / "foreign.txt").write_text("evil", encoding="utf-8")

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        _load_verified_n3_friction_root_for_test(published_dir, allowed_parent=tmp_path)
    assert "foreign_artifact" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Task 1 Negative Probes: Lifecycle & Durability
# ---------------------------------------------------------------------------

def test_lifecycle_helper_rejects_foreign_staging_sibling(tmp_path, canonical_admitted_sources):
    """Pre-existing foreign staging sibling triggers fail-closed STOP."""
    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )
    # Create foreign staging sibling: .stage1_5h_n3_regime_stratified_friction_20261003T120000Z.staging.99999
    staging_sibling = tmp_path / ".stage1_5h_n3_regime_stratified_friction_20261003T120000Z.staging.99999"
    staging_sibling.mkdir()

    with pytest.raises(Stage1_5HN3RegimeFrictionError) as exc_info:
        _publish_n3_friction_receipt_for_lifecycle_test(summary, parent_dir=tmp_path)
    assert "foreign_staging_sibling" in str(exc_info.value)


def test_lifecycle_helper_pre_rename_failure_leaves_staging_only(tmp_path, canonical_admitted_sources):
    """Crash before rename leaves state as staging_only without creating final root."""
    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )

    with pytest.raises(RuntimeError, match="simulated_pre_rename_crash"):
        _publish_n3_friction_receipt_for_lifecycle_test(
            summary,
            parent_dir=tmp_path,
            _failpoint="before_rename",
        )

    state = _classify_n3_friction_root_state_for_test(
        tmp_path / "stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
        allowed_parent=tmp_path,
    )
    assert state == "staging_only"


def test_lifecycle_helper_post_rename_durability_failure_raises_specific_error(tmp_path, canonical_admitted_sources):
    """Failure after atomic rename wraps in Stage1_5HN3PostRenameDurabilityFailure."""
    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )

    with pytest.raises(Stage1_5HN3PostRenameDurabilityFailure):
        _publish_n3_friction_receipt_for_lifecycle_test(
            summary,
            parent_dir=tmp_path,
            _failpoint="after_rename_before_fsync",
        )


def test_strict_loader_and_classifier_have_no_test_bypass_parameters(tmp_path):
    """Ensure public strict loader and classifier have no test bypass or project_root parameters."""
    loader_params = list(inspect.signature(load_verified_n3_friction_root).parameters.keys())
    assert loader_params == ["final_root"], f"Expected ['final_root'], got {loader_params}"

    classifier_params = list(inspect.signature(classify_n3_friction_root_state).parameters.keys())
    assert classifier_params == ["final_root"], f"Expected ['final_root'], got {classifier_params}"

    with pytest.raises(Stage1_5HN3RegimeFrictionError, match="noncanonical_output_parent"):
        load_verified_n3_friction_root(tmp_path / "stage1_5h_n3_regime_stratified_friction_test")


def test_publish_n3_friction_receipt_signature_has_no_project_root():
    """Ensure public writer accepts strictly summary and derives production paths internally."""
    writer_params = list(inspect.signature(publish_n3_friction_receipt).parameters.keys())
    assert writer_params == ["summary"], f"Expected ['summary'], got {writer_params}"


def test_generated_bytes_schema_conforms_to_design(tmp_path, canonical_admitted_sources):
    """Ensure published manifest and summary match Design schemas exactly."""
    summary = derive_n3_friction_summary(
        canonical_admitted_sources,
        run_id="stage1_5h_n3_regime_stratified_friction_20261003T120000Z",
    )
    final_root = _publish_n3_friction_receipt_for_lifecycle_test(summary, parent_dir=tmp_path)

    # 1. Manifest schema check
    manifest_bytes = (final_root / "stage1_5h_n3_regime_stratified_friction_manifest.json").read_bytes()
    manifest_data = json.loads(manifest_bytes.decode("utf-8"))
    assert set(manifest_data.keys()) == set(MANIFEST_KEYS)
    assert manifest_data["schema_version"] == 1
    assert manifest_data["input_receipt_manifest_sha256"] == N3_MANIFEST_SHA256
    assert manifest_data["input_receipt_review_sha256"] == N3_REVIEW_SHA256
    assert manifest_data["input_receipt_summary_sha256"] == N3_SUMMARY_SHA256
    assert manifest_data["run_id"] == summary["run_id"]
    assert set(manifest_data["artifacts"].keys()) == {
        "stage1_5h_n3_regime_stratified_friction_summary.json",
        "stage1_5h_n3_regime_stratified_friction_review_CN.md",
    }

    # 2. Summary schema check
    summary_bytes = (final_root / "stage1_5h_n3_regime_stratified_friction_summary.json").read_bytes()
    summary_data = json.loads(summary_bytes.decode("utf-8"))
    assert set(summary_data.keys()) == set(SUMMARY_KEYS)
    assert "root_relative_path" in summary_data["input_receipt"]
    assert "receipt_relative_path" not in summary_data["input_receipt"]
    assert set(summary_data["input_receipt"].keys()) == set(INPUT_RECEIPT_KEYS)
    assert summary_data["input_receipt"]["root_relative_path"] == N3_RECEIPT_REL_PATH


def test_canonical_execution_authority_bundle_path_has_no_parameters():
    """Ensure get_canonical_execution_authority_bundle_path accepts zero parameters and rejects caller input."""
    sig = inspect.signature(get_canonical_execution_authority_bundle_path)
    assert len(sig.parameters) == 0, f"Expected 0 parameters, got {list(sig.parameters.keys())}"

    with pytest.raises(TypeError):
        get_canonical_execution_authority_bundle_path(Path("/tmp"))  # type: ignore[call-arg]

    bundle_path = get_canonical_execution_authority_bundle_path()
    expected = _get_project_root().resolve() / f".git/plan-execution/stage1_5h_n3_regime/{APPROVED_PLAN_SHA256}"
    assert bundle_path == expected
