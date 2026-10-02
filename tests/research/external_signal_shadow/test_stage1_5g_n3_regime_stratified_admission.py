import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.research.external_signal_shadow.safety import canonical_json_dumps
from src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission import (
    APPROVED_DESIGN_SHA256,
    APPROVED_PLAN_SHA256,
    EXPECTED_13_FALSE_FLAGS,
    FROZEN_INPUT_RECORDS,
    FROZEN_PRODUCT_REGIME_DECLARATIONS,
    FROZEN_UPSTREAM_CONTRACT,
    Stage1_5GN3RegimeAdmissionError,
    _publish_n3_receipt_for_lifecycle_test,
    admit_frozen_n3_inputs,
    build_n3_summary,
    classify_receipt_state,
    load_verified_n3_receipt,
    publish_n3_receipt,
    render_review,
    verify_execution_authority,
    verify_frozen_upstream_contract,
)


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_real_root_n3_admission_positive_contract():
    """Step 1: Real-root integration test first for all 3 roots."""
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_n3_inputs(project_root=project_root)

    assert len(admitted_inputs) == 3
    assert [item["input_key"] for item in admitted_inputs] == ["moonshot", "batch7", "ct_projection"]

    # Verify build_n3_summary produces the exact required facts
    result = build_n3_summary(admitted_inputs, run_id="stage1_5g_n3_regime_stratified_admission_20261002T120000Z")

    assert result["schema_version"] == 1
    assert result["decision"] == "stage1_5g_n3_regime_stratified_admission_pass"
    assert result["cross_root_evidence_count_status"] == "sufficient"
    assert result["formal_symbol_count"] == 9
    assert result["distinct_source_article_count"] == 3
    assert result["independent_parent_event_count"] == 3
    assert result["stage1_5g_gate3_complete"] is False
    assert result["authority_flags"] == EXPECTED_13_FALSE_FLAGS
    assert [item["input_key"] for item in result["input_records"]] == ["moonshot", "batch7", "ct_projection"]

    # Assert exact parent IDs and child sequences
    parent_ledger = result["parent_ledger"]
    assert len(parent_ledger) == 3
    p1, p2, p3 = parent_ledger[0], parent_ledger[1], parent_ledger[2]

    assert p1["parent_article_id"] == "7379b99aa0f349a49c3b3feca1b4bbd6"
    assert p1["parent_event_id"] == "e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5"
    assert p1["child_symbols"] == ["MOONSHOTUSDT"]
    assert p1["product_regime_id"] == "pre_ipo_equity_perpetual"

    assert p2["parent_article_id"] == "0c6ea14ba89b451db6ec9ec364045d22"
    assert p2["parent_event_id"] == "d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0"
    assert set(p2["child_symbols"]) == {
        "ACNUSDT",
        "BWETUSDT",
        "CRMLUSDT",
        "MPUSDT",
        "NKEUSDT",
        "SECZUSDT",
        "UNHUSDT",
    }
    assert p2["product_regime_id"] == "tradfi_equity_or_etf_perpetual_batch"

    assert p3["parent_article_id"] == "6bd26adeb6f742fe88eb72faca183566"
    assert p3["parent_event_id"] == "374345c5e4527ca0f061155796909acb385fbd084172f175bd8accb00cdbd963"
    assert p3["child_symbols"] == ["CTUSDT"]
    assert p3["product_regime_id"] == "crypto_standard_perpetual"

    # Assert product_regime_ledger
    regime_ledger = result["product_regime_ledger"]
    assert len(regime_ledger) == 3
    r1, r2, r3 = regime_ledger[0], regime_ledger[1], regime_ledger[2]

    assert r1["parent_article_id"] == "7379b99aa0f349a49c3b3feca1b4bbd6"
    assert r1["product_regime_id"] == "pre_ipo_equity_perpetual"
    assert r1["classification_status"] == "classified"
    assert r1["underlying_economic_type"] == "equity"
    assert r1["lifecycle_regime"] == "pre_ipo"
    assert r1["reference_market_availability"] == "unavailable_pre_ipo"
    assert r1["mark_price_regime"] == "exchange_trade_derived"
    assert r1["source_detail_url_normalized"] == "https://www.binance.com/en/support/announcement/7379b99aa0f349a49c3b3feca1b4bbd6"
    assert r1["source_anchor_contract_hashes"] == ["d9130cb1df6af342cb7f68642a91f33f7eb36dd86ff434cd355e33a98ef30900"]

    assert r2["parent_article_id"] == "0c6ea14ba89b451db6ec9ec364045d22"
    assert r2["product_regime_id"] == "tradfi_equity_or_etf_perpetual_batch"
    assert r2["classification_status"] == "classified"
    assert r2["underlying_economic_type"] == "tradfi_equity_or_etf"
    assert r2["lifecycle_regime"] == "standard"
    assert r2["reference_market_availability"] == "not_asserted"
    assert r2["mark_price_regime"] == "not_asserted"
    assert r2["source_detail_url_normalized"] == "https://www.binance.com/en/support/announcement/0c6ea14ba89b451db6ec9ec364045d22"
    assert len(r2["source_anchor_contract_hashes"]) == 7

    assert r3["parent_article_id"] == "6bd26adeb6f742fe88eb72faca183566"
    assert r3["product_regime_id"] == "crypto_standard_perpetual"
    assert r3["classification_status"] == "classified"
    assert r3["underlying_economic_type"] == "crypto_token"
    assert r3["lifecycle_regime"] == "standard"
    assert r3["reference_market_availability"] == "not_asserted"
    assert r3["mark_price_regime"] == "not_asserted"
    assert r3["source_detail_url_normalized"] == "https://www.binance.com/en/support/announcement/6bd26adeb6f742fe88eb72faca183566"
    assert r3["source_anchor_contract_hashes"] == ["198fd0c8b50433f8d9c36d974d792b521ad1e08fc09035b16028eba318e1cf12"]


def test_production_loader_called_once_per_root_via_profile():
    """In an isolated subprocess, use sys.setprofile to prove load_stage1_5g_inputs and
    build_stage1_5g_review_summary run exactly once per fixed root (3 times total).
    """
    code = """
import sys
from pathlib import Path
from src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission import admit_frozen_n3_inputs

calls = {"load_stage1_5g_inputs": 0, "build_stage1_5g_review_summary": 0}

def profiler(frame, event, arg):
    if event == "call":
        name = frame.f_code.co_name
        if name in calls:
            calls[name] += 1

sys.setprofile(profiler)
admitted = admit_frozen_n3_inputs()
sys.setprofile(None)

assert calls["load_stage1_5g_inputs"] == 3, f"load calls: {calls['load_stage1_5g_inputs']}"
assert calls["build_stage1_5g_review_summary"] == 3, f"build calls: {calls['build_stage1_5g_review_summary']}"
print("PROFILE_OK")
"""
    cmd = [sys.executable, "-c", code]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_get_project_root()))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert "PROFILE_OK" in res.stdout


def test_admit_frozen_n3_inputs_rejects_missing_record():
    records = copy.deepcopy(FROZEN_INPUT_RECORDS)[:2]
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        admit_frozen_n3_inputs(input_records_override=records)
    assert "STOP=stage1_5g_n3_regime_input_authority_mismatch" in str(exc_info.value)


def test_admit_frozen_n3_inputs_rejects_tampered_stored_summary_hash():
    records = copy.deepcopy(FROZEN_INPUT_RECORDS)
    records[0]["stored_summary_sha256"] = "0" * 64
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        admit_frozen_n3_inputs(input_records_override=records)
    assert "STOP=stage1_5g_n3_regime_input_authority_mismatch" in str(exc_info.value)


def test_admit_frozen_n3_inputs_rejects_tampered_source_manifest_hash():
    records = copy.deepcopy(FROZEN_INPUT_RECORDS)
    records[0]["source_manifest_sha256"] = "0" * 64
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        admit_frozen_n3_inputs(input_records_override=records)
    assert "STOP=stage1_5g_n3_regime_input_authority_mismatch" in str(exc_info.value)


def test_ct_projection_rejects_missing_ct_child():
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    # Tamper ct_projection formal_children to omit CTUSDT
    admitted_tampered = copy.deepcopy(admitted)
    admitted_tampered[2]["recomputed_formal_projection"]["formal_children"] = [
        c for c in admitted_tampered[2]["recomputed_formal_projection"]["formal_children"] if c["symbol"] != "CTUSDT"
    ]
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        build_n3_summary(admitted_tampered, run_id="stage1_5g_n3_regime_stratified_admission_20261002T120000Z")
    assert "STOP=stage1_5g_n3_regime_ct_projection_mismatch" in str(exc_info.value)


def test_ct_projection_rejects_changed_batch7_duplicate_child():
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    admitted_tampered = copy.deepcopy(admitted)
    # Modify one of the 7 duplicate Batch 7 children inside CT projection
    admitted_tampered[2]["recomputed_formal_projection"]["formal_children"][0]["event_symbol_id"] = "f" * 64
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        build_n3_summary(admitted_tampered, run_id="stage1_5g_n3_regime_stratified_admission_20261002T120000Z")
    assert "STOP=stage1_5g_n3_regime_ct_projection_mismatch" in str(exc_info.value)


def test_ct_projection_rejects_ninth_child():
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    admitted_tampered = copy.deepcopy(admitted)
    extra_child = copy.deepcopy(admitted_tampered[2]["recomputed_formal_projection"]["formal_children"][-1])
    extra_child["symbol"] = "EXTRAUSDT"
    extra_child["event_symbol_id"] = "e" * 64
    admitted_tampered[2]["recomputed_formal_projection"]["formal_children"].append(extra_child)
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        build_n3_summary(admitted_tampered, run_id="stage1_5g_n3_regime_stratified_admission_20261002T120000Z")
    assert "STOP=stage1_5g_n3_regime_ct_projection_mismatch" in str(exc_info.value)


def test_build_n3_summary_rejects_duplicate_parent_article():
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    admitted_tampered = copy.deepcopy(admitted)
    moonshot_article = admitted_tampered[0]["recomputed_formal_projection"]["formal_children"][0]["source_article_id"]
    # Make Batch 7 have same article as Moonshot in both Batch 7 input and CT projection duplicates
    for c in admitted_tampered[1]["recomputed_formal_projection"]["formal_children"]:
        c["source_article_id"] = moonshot_article
    for c in admitted_tampered[2]["recomputed_formal_projection"]["formal_children"]:
        if c["symbol"] != "CTUSDT":
            c["source_article_id"] = moonshot_article
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        build_n3_summary(admitted_tampered, run_id="stage1_5g_n3_regime_stratified_admission_20261002T120000Z")
    assert "STOP=stage1_5g_n3_regime_parent_identity_mismatch" in str(exc_info.value)


def test_build_n3_summary_rejects_regime_field_mutation():
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    # Mutate a regime field in declarations
    decls_tampered = copy.deepcopy(FROZEN_PRODUCT_REGIME_DECLARATIONS)
    decls_tampered["crypto_standard_perpetual"]["underlying_economic_type"] = "equity"
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        build_n3_summary(admitted, run_id="stage1_5g_n3_regime_stratified_admission_20261002T120000Z", declarations_override=decls_tampered)
    assert "STOP=stage1_5g_n3_regime_classification_mismatch" in str(exc_info.value)


def test_build_n3_summary_rejects_wrong_url_in_declaration():
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    decls_tampered = copy.deepcopy(FROZEN_PRODUCT_REGIME_DECLARATIONS)
    decls_tampered["crypto_standard_perpetual"]["official_url"] = "https://example.com"
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        build_n3_summary(admitted, run_id="stage1_5g_n3_regime_stratified_admission_20261002T120000Z", declarations_override=decls_tampered)
    assert "STOP=stage1_5g_n3_regime_classification_mismatch" in str(exc_info.value)


def test_publish_and_load_verified_n3_receipt(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T120000Z"
    summary = build_n3_summary(admitted, run_id=run_id)

    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)
    assert final_root.is_dir()
    assert (final_root / "stage1_5g_n3_regime_stratified_admission_summary.json").is_file()
    assert (final_root / "stage1_5g_n3_regime_stratified_admission_review_CN.md").is_file()
    assert (final_root / "stage1_5g_n3_regime_stratified_admission_manifest.json").is_file()

    # Load and verify
    loaded = load_verified_n3_receipt(final_root, project_root=project_root)
    assert loaded["run_id"] == run_id
    assert loaded["decision"] == "stage1_5g_n3_regime_stratified_admission_pass"
    assert loaded["formal_symbol_count"] == 9
    assert loaded["stage1_5g_gate3_complete"] is False


def test_loader_rejects_tampered_manifest(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T120000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    manifest_p = final_root / "stage1_5g_n3_regime_stratified_admission_manifest.json"
    manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_summary.json"]["sha256"] = "0" * 64
    manifest_p.write_text(canonical_json_dumps(manifest_data), encoding="utf-8")

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(final_root, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure" in str(exc_info.value)


def test_loader_rejects_markdown_projection_mismatch(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T120000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    review_p = final_root / "stage1_5g_n3_regime_stratified_admission_review_CN.md"
    review_p.write_text(review_p.read_text(encoding="utf-8") + "\n# Extra Alpha wording\n", encoding="utf-8")

    # Update manifest to match hash so hash check passes but projection check fails
    manifest_p = final_root / "stage1_5g_n3_regime_stratified_admission_manifest.json"
    manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
    new_sha = hashlib.sha256(review_p.read_bytes()).hexdigest()
    manifest_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_review_CN.md"]["sha256"] = new_sha
    manifest_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_review_CN.md"]["byte_count"] = review_p.stat().st_size
    manifest_p.write_text(canonical_json_dumps(manifest_data), encoding="utf-8")

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(final_root, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure:review_projection_mismatch" in str(exc_info.value)


def test_future_consumer_attempt_raises_fatal_stop(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T120000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(final_root, project_root=project_root, future_consumer_allowed=True)
    assert "STOP=stage1_5g_n3_regime_future_consumer_not_authorized" in str(exc_info.value)


def test_ast_rejects_forbidden_imports():
    """Verify that stage1_5g_n3_regime_stratified_admission.py does not import forbidden modules."""
    import ast

    core_file = _get_project_root() / "src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py"
    if not core_file.exists():
        pytest.fail("core file does not exist yet")

    tree = ast.parse(core_file.read_text(encoding="utf-8"), filename=str(core_file))
    forbidden_modules = {
        "socket", "requests", "urllib", "http", "ccxt",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_base = alias.name.split(".")[0]
                assert mod_base not in forbidden_modules, f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_base = node.module.split(".")[0]
                assert mod_base not in forbidden_modules, f"Forbidden from-import: {node.module}"


def test_classify_receipt_state_matrix(tmp_path):
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T120000Z"
    parent = tmp_path / "admissions"
    parent.mkdir()

    # 1. Fresh (unpublished)
    assert classify_receipt_state(parent, run_id) == "unpublished"

    # 2. Staging only
    staging = parent / f".{run_id}.staging.12345"
    staging.mkdir()
    assert classify_receipt_state(parent, run_id) == "staging_only"

    # 3. Malformed sibling
    malformed = parent / f".{run_id}.staging.abc"
    malformed.mkdir()
    assert classify_receipt_state(parent, run_id) == "corrupt_or_unknown"


def test_verify_execution_authority_happy_path():
    project_root = _get_project_root()
    auth = verify_execution_authority(project_root=project_root)
    assert auth["approved_plan_sha256"] == APPROVED_PLAN_SHA256
    assert auth["approved_design_sha256"] == APPROVED_DESIGN_SHA256
    assert auth["project_root"] == str(project_root)


def test_verify_execution_authority_rejects_head_drift(monkeypatch):
    import subprocess
    project_root = _get_project_root()
    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            class FakeRes:
                returncode = 0
                stdout = "0" * 40
                stderr = ""
            return FakeRes()
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        verify_execution_authority(project_root=project_root)
    assert "STOP=approved_authority_mismatch:head_sha_mismatch" in str(exc_info.value)


def test_verify_frozen_upstream_contract_happy_path():
    project_root = _get_project_root()
    verify_frozen_upstream_contract(project_root=project_root)
    assert len(FROZEN_UPSTREAM_CONTRACT) == 3


def test_render_review_content():
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T120000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    md = render_review(summary)
    assert "# Stage 1.5G N=3 Regime-Stratified Admission Receipt" in md
    assert "## Admitted Inputs" in md
    assert "## Parent Ledger" in md
    assert "## Product Regime Ledger" in md
    assert "## Authority Vector" in md


@pytest.mark.parametrize(
    "fault_pos",
    [
        "before_summary_write",
        "after_summary_write",
        "before_review_write",
        "after_review_write",
        "before_manifest_write",
        "after_manifest_write",
        "before_rename",
    ],
)
def test_lifecycle_pre_rename_failpoints(tmp_path, fault_pos):
    import src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission as core_mod

    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = f"stage1_5g_n3_regime_stratified_admission_20261002T12{abs(hash(fault_pos)) % 100:02d}00Z"
    summary = build_n3_summary(admitted, run_id=run_id)

    def hook(pos: str):
        if pos == fault_pos:
            raise RuntimeError(f"SIMULATED_CRASH:{pos}")

    core_mod._FAILPOINT_HOOK = hook
    try:
        with pytest.raises(RuntimeError) as exc_info:
            _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)
        assert f"SIMULATED_CRASH:{fault_pos}" in str(exc_info.value)
    finally:
        core_mod._FAILPOINT_HOOK = None

    final_root = tmp_path / run_id
    assert not final_root.exists()
    assert classify_receipt_state(tmp_path, run_id) == "staging_only"


def test_lifecycle_post_rename_durability_failure(tmp_path):
    import src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission as core_mod

    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T140000Z"
    summary = build_n3_summary(admitted, run_id=run_id)

    def hook(pos: str):
        if pos == "after_parent_fsync":
            raise OSError("POST_RENAME_DURABILITY_FAILURE:simulated_io_error")

    core_mod._FAILPOINT_HOOK = hook
    try:
        with pytest.raises(core_mod.Stage1_5GN3PostRenameDurabilityFailure) as exc_info:
            _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)
        assert "POST_RENAME_DURABILITY_FAILURE" in str(exc_info.value)
    finally:
        core_mod._FAILPOINT_HOOK = None

    final_root = tmp_path / run_id
    assert final_root.is_dir()
    assert classify_receipt_state(tmp_path, run_id) == "receipt_published"


def test_final_root_collision_rejected(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T150000Z"
    summary = build_n3_summary(admitted, run_id=run_id)

    _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    # Calling again with same run_id must raise collision STOP
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure:not_fresh" in str(exc_info.value)


def test_summary_extra_key_rejected(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T160000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    sum_p = final_root / "stage1_5g_n3_regime_stratified_admission_summary.json"
    data = json.loads(sum_p.read_text(encoding="utf-8"))
    data["extra_forbidden_key"] = "bad"
    sum_p.write_text(canonical_json_dumps(data), encoding="utf-8")

    # Update manifest to match hash so loader checks summary keys
    man_p = final_root / "stage1_5g_n3_regime_stratified_admission_manifest.json"
    man_data = json.loads(man_p.read_text(encoding="utf-8"))
    man_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_summary.json"]["sha256"] = hashlib.sha256(sum_p.read_bytes()).hexdigest()
    man_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_summary.json"]["byte_count"] = sum_p.stat().st_size
    man_p.write_text(canonical_json_dumps(man_data), encoding="utf-8")

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(final_root, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure:summary_keys" in str(exc_info.value)


def test_summary_authority_flag_true_rejected(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T170000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    sum_p = final_root / "stage1_5g_n3_regime_stratified_admission_summary.json"
    data = json.loads(sum_p.read_text(encoding="utf-8"))
    data["authority_flags"]["live_trading_allowed"] = True
    sum_p.write_text(canonical_json_dumps(data), encoding="utf-8")

    man_p = final_root / "stage1_5g_n3_regime_stratified_admission_manifest.json"
    man_data = json.loads(man_p.read_text(encoding="utf-8"))
    man_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_summary.json"]["sha256"] = hashlib.sha256(sum_p.read_bytes()).hexdigest()
    man_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_summary.json"]["byte_count"] = sum_p.stat().st_size
    man_p.write_text(canonical_json_dumps(man_data), encoding="utf-8")

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(final_root, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure:authority_flags" in str(exc_info.value)


def test_unlisted_file_in_final_root_rejected(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T180000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    (final_root / "rogue_file.txt").write_text("evil")

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(final_root, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure" in str(exc_info.value)


def test_loader_rejects_symlink_final_root(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T181000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path / "real", project_root=project_root)

    symlink_root = tmp_path / "symlink_root"
    symlink_root.symlink_to(final_root)

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(symlink_root, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure" in str(exc_info.value)
    assert "symlink" in str(exc_info.value).lower()


def test_loader_rejects_noncanonical_manifest(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T182000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    man_p = final_root / "stage1_5g_n3_regime_stratified_admission_manifest.json"
    man_data = json.loads(man_p.read_text(encoding="utf-8"))
    # Write non-canonical JSON with extra indentation and space
    man_p.write_bytes(json.dumps(man_data, indent=4).encode("utf-8") + b"\n")

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(final_root, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure:manifest_not_canonical" in str(exc_info.value)


def test_loader_rejects_forged_product_regime_ledger(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T183000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    sum_p = final_root / "stage1_5g_n3_regime_stratified_admission_summary.json"
    sum_data = json.loads(sum_p.read_text(encoding="utf-8"))
    sum_data["product_regime_ledger"][0]["underlying_economic_type"] = "forged_type"
    sum_bytes = canonical_json_dumps(sum_data).encode("utf-8")
    sum_p.write_bytes(sum_bytes)

    # Update manifest so hashes match
    man_p = final_root / "stage1_5g_n3_regime_stratified_admission_manifest.json"
    man_data = json.loads(man_p.read_text(encoding="utf-8"))
    man_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_summary.json"]["sha256"] = hashlib.sha256(sum_bytes).hexdigest()
    man_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_summary.json"]["byte_count"] = len(sum_bytes)
    man_p.write_bytes(canonical_json_dumps(man_data).encode("utf-8"))

    # Also update review markdown so review matches summary
    rev_p = final_root / "stage1_5g_n3_regime_stratified_admission_review_CN.md"
    rev_bytes = render_review(sum_data).encode("utf-8")
    rev_p.write_bytes(rev_bytes)
    man_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_review_CN.md"]["sha256"] = hashlib.sha256(rev_bytes).hexdigest()
    man_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_review_CN.md"]["byte_count"] = len(rev_bytes)
    man_p.write_bytes(canonical_json_dumps(man_data).encode("utf-8"))

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(final_root, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure:product_regime_ledger" in str(exc_info.value)


def test_loader_rejects_forged_manifest_relative_path(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T184000Z"
    summary = build_n3_summary(admitted, run_id=run_id)
    final_root = _publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)

    man_p = final_root / "stage1_5g_n3_regime_stratified_admission_manifest.json"
    man_data = json.loads(man_p.read_text(encoding="utf-8"))
    man_data["artifacts"]["stage1_5g_n3_regime_stratified_admission_summary.json"]["relative_path"] = "forged.json"
    man_p.write_bytes(canonical_json_dumps(man_data).encode("utf-8"))

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        load_verified_n3_receipt(final_root, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure" in str(exc_info.value)


def test_public_writer_rejects_without_receipt_generation_authority(tmp_path, monkeypatch):
    import src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission as core_mod

    # Isolate the generation-authority gate from the real project bundle.
    monkeypatch.setattr(core_mod, "verify_execution_authority", lambda **_kwargs: {})

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        core_mod.publish_n3_receipt({"run_id": "unused"}, project_root=tmp_path)
    assert "STOP=local_receipt_generation_not_authorized" in str(exc_info.value)
    assert not (tmp_path / core_mod.DEFAULT_ADMISSION_PARENT).exists()


def test_writer_rejects_ancestor_symlink_output_parent(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T193000Z"
    summary = build_n3_summary(admitted, run_id=run_id)

    real_parent = tmp_path / "real_admissions"
    real_parent.mkdir()
    sym_parent = tmp_path / "sym_admissions"
    sym_parent.symlink_to(real_parent)

    # 1. Direct symlink parent
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        _publish_n3_receipt_for_lifecycle_test(summary, output_parent=sym_parent, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure:parent_dir_symlink" in str(exc_info.value)
    assert not (real_parent / run_id).exists()

    # 2. Ancestor symlink parent
    target_nested = sym_parent / "nested"
    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info_nested:
        _publish_n3_receipt_for_lifecycle_test(summary, output_parent=target_nested, project_root=project_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure:parent_dir_symlink" in str(exc_info_nested.value)
    assert not (real_parent / "nested").exists()


def test_public_writer_rejects_symlink_root(tmp_path):
    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T194000Z"
    summary = build_n3_summary(admitted, run_id=run_id)

    sym_root = tmp_path / "sym_root"
    sym_root.symlink_to(project_root)

    with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
        publish_n3_receipt(summary, project_root=sym_root)
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure:project_root_symlink" in str(exc_info.value)


def test_lifecycle_pre_rename_foreign_sibling_fails_closed(tmp_path):
    import src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission as core_mod

    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T191000Z"
    summary = build_n3_summary(admitted, run_id=run_id)

    def hook(pos: str):
        if pos == "before_rename":
            # Inject a foreign staging sibling
            foreign_staging = tmp_path / f".{run_id}.staging.99999"
            foreign_staging.mkdir()

    core_mod._FAILPOINT_HOOK = hook
    try:
        with pytest.raises(Stage1_5GN3RegimeAdmissionError) as exc_info:
            core_mod._publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)
        assert "STOP=stage1_5g_n3_regime_publication_integrity_failure" in str(exc_info.value)
    finally:
        core_mod._FAILPOINT_HOOK = None


def test_lifecycle_after_rename_raises_post_rename_durability_failure(tmp_path):
    import src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission as core_mod

    project_root = _get_project_root()
    admitted = admit_frozen_n3_inputs(project_root=project_root)
    run_id = "stage1_5g_n3_regime_stratified_admission_20261002T192000Z"
    summary = build_n3_summary(admitted, run_id=run_id)

    def hook(pos: str):
        if pos == "after_rename":
            raise RuntimeError("CRASH_AFTER_RENAME")

    core_mod._FAILPOINT_HOOK = hook
    try:
        with pytest.raises(core_mod.Stage1_5GN3PostRenameDurabilityFailure) as exc_info:
            core_mod._publish_n3_receipt_for_lifecycle_test(summary, output_parent=tmp_path, project_root=project_root)
        assert "STOP=POST_RENAME_DURABILITY_FAILURE" in str(exc_info.value)
    finally:
        core_mod._FAILPOINT_HOOK = None
