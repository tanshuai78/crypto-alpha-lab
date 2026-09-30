import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.research.external_signal_shadow.safety import canonical_json_dumps

# In Task 1 RED phase, importing the new core module will fail with ModuleNotFoundError
from src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission import (
    EXPECTED_13_FALSE_FLAGS,
    FROZEN_INPUT_RECORDS,
    FROZEN_UPSTREAM_CONTRACT,
    Stage1_5GCrossRootAdmissionError,
    admit_frozen_cross_root_inputs,
    build_cross_root_summary,
    classify_receipt_state,
    compare_admitted_projection,
    load_verified_cross_root_receipt,
    publish_cross_root_receipt,
    render_review,
    verify_execution_authority,
    verify_frozen_upstream_contract,
)


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_real_root_cross_root_admission_positive_contract():
    """Step 1: Real-root integration test first."""
    project_root = _get_project_root()
    admitted_inputs = admit_frozen_cross_root_inputs(project_root=project_root)

    assert len(admitted_inputs) == 2
    assert [item["input_key"] for item in admitted_inputs] == ["moonshot", "batch7"]

    # Verify build_cross_root_summary produces the exact required facts
    result = build_cross_root_summary(admitted_inputs, run_id="stage1_5g_cross_root_admission_20260930T120000Z")

    assert result["formal_symbol_count"] == 8
    assert result["distinct_source_article_count"] == 2
    assert result["independent_parent_event_count"] == 2
    assert result["cross_root_evidence_count_status"] == "sufficient"
    assert result["stage1_5g_gate3_complete"] is False
    assert result["authority_flags"] == EXPECTED_13_FALSE_FLAGS
    assert [item["input_key"] for item in result["input_records"]] == ["moonshot", "batch7"]

    # Assert exact parent IDs and child sequences
    parent_ledger = result["parent_ledger"]
    assert len(parent_ledger) == 2
    p1, p2 = parent_ledger[0], parent_ledger[1]

    assert p1["parent_article_id"] == "7379b99aa0f349a49c3b3feca1b4bbd6"
    assert p1["parent_event_id"] == "e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5"
    assert p1["child_symbols"] == ["MOONSHOTUSDT"]

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


def test_production_loader_called_once_per_root_via_profile():
    """In an isolated subprocess, use sys.setprofile to prove load_stage1_5g_inputs and

    build_stage1_5g_review_summary run once per fixed root without pre-import/patching.
    """
    code = """
import sys
from pathlib import Path
from src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission import admit_frozen_cross_root_inputs

calls = {"load_stage1_5g_inputs": 0, "build_stage1_5g_review_summary": 0}

def profiler(frame, event, arg):
    if event == "call":
        name = frame.f_code.co_name
        if name in calls:
            calls[name] += 1

sys.setprofile(profiler)
admitted = admit_frozen_cross_root_inputs()
sys.setprofile(None)

assert calls["load_stage1_5g_inputs"] == 2, f"load calls: {calls['load_stage1_5g_inputs']}"
assert calls["build_stage1_5g_review_summary"] == 2, f"build calls: {calls['build_stage1_5g_review_summary']}"
print("PROFILE_OK")
"""
    cmd = [sys.executable, "-c", code]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_get_project_root()))
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert "PROFILE_OK" in res.stdout


# Step 2: Negative authority tests (one read/hash fault at a time)


def test_negative_upstream_contract_file_drift(tmp_path):
    """Upstream contract file missing or modified raises STOP=stage1_5g_cross_root_upstream_contract_drift."""
    project_root = _get_project_root()
    # We can test verify_frozen_upstream_contract directly with an invalid root or corrupted file
    fake_root = tmp_path / "corrupt_proj"
    fake_root.mkdir()
    for rel_path in FROZEN_UPSTREAM_CONTRACT:
        target = fake_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        # copy real file
        real = project_root / rel_path
        target.write_bytes(real.read_bytes())

    # Corrupt one upstream contract file
    first_path = list(FROZEN_UPSTREAM_CONTRACT.keys())[0]
    (fake_root / first_path).write_bytes(b"# corrupted\n")

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        verify_frozen_upstream_contract(project_root=fake_root)
    assert "STOP=stage1_5g_cross_root_upstream_contract_drift" in str(exc_info.value)


def test_negative_stored_summary_byte_corruption(tmp_path):
    """Stored summary byte mismatch raises STOP=stage1_5g_cross_root_input_authority_mismatch."""
    project_root = _get_project_root()
    corrupt_summary = tmp_path / "corrupt_summary.json"
    corrupt_summary.write_bytes(b'{"corrupted": true}')
    rel_p = os.path.relpath(corrupt_summary, project_root)

    mutated_record = copy.deepcopy(FROZEN_INPUT_RECORDS[0])
    mutated_record["stored_summary_path"] = rel_p

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        admit_frozen_cross_root_inputs(
            input_records_override=[mutated_record, FROZEN_INPUT_RECORDS[1]],
            project_root=project_root,
        )
    assert "STOP=stage1_5g_cross_root_input_authority_mismatch" in str(exc_info.value)


def test_negative_missing_source_root():
    """Missing source root directory raises STOP=stage1_5g_cross_root_input_authority_mismatch."""
    mutated_record = copy.deepcopy(FROZEN_INPUT_RECORDS[0])
    mutated_record["source_root_path"] = "data/external_signal_shadow/local_evidence/missing_root_dir"

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        admit_frozen_cross_root_inputs(
            input_records_override=[mutated_record, FROZEN_INPUT_RECORDS[1]],
            project_root=_get_project_root(),
        )
    assert "STOP=stage1_5g_cross_root_input_authority_mismatch" in str(exc_info.value)


def test_negative_source_sha256sums_digest_corruption(tmp_path):
    """Corrupted source SHA256SUMS raises STOP=stage1_5g_cross_root_input_authority_mismatch."""
    project_root = _get_project_root()
    fake_source = tmp_path / "fake_source"
    fake_source.mkdir()
    real_source = project_root / FROZEN_INPUT_RECORDS[0]["source_root_path"]
    for f in real_source.iterdir():
        if f.is_file():
            (fake_source / f.name).write_bytes(f.read_bytes())
    # corrupt SHA256SUMS
    (fake_source / "SHA256SUMS").write_bytes(b"corrupted\n")

    rel_source = os.path.relpath(fake_source, project_root)
    mutated_record = copy.deepcopy(FROZEN_INPUT_RECORDS[0])
    mutated_record["source_root_path"] = rel_source

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        admit_frozen_cross_root_inputs(
            input_records_override=[mutated_record, FROZEN_INPUT_RECORDS[1]],
            project_root=project_root,
        )
    assert "STOP=stage1_5g_cross_root_input_authority_mismatch" in str(exc_info.value)


# Step 2: Reducer / Comparator negative tests
# Obtain actual verified in-memory admitted projection from real-root positive fixture,
# then make single local copy and invoke the owned pure function directly.


@pytest.fixture(scope="module")
def admitted_positive_projection():
    project_root = _get_project_root()
    return admit_frozen_cross_root_inputs(project_root=project_root)


def test_compare_admitted_projection_mismatch(admitted_positive_projection):
    """Difference between stored and recomputed projection raises STOP=stage1_5g_cross_root_input_authority_mismatch."""
    record = copy.deepcopy(admitted_positive_projection[0])
    stored_proj = copy.deepcopy(record["recomputed_formal_projection"])
    recomputed_proj = copy.deepcopy(record["recomputed_formal_projection"])
    # Mutate recomputed projection decision
    recomputed_proj["decision"] = "stage1_5g_depth_evidence_quarantined_pass"

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        compare_admitted_projection(stored_proj, recomputed_proj)
    assert "STOP=stage1_5g_cross_root_input_authority_mismatch" in str(exc_info.value)


def test_reducer_duplicate_source_article(admitted_positive_projection):
    """Duplicate source article across roots raises STOP=stage1_5g_cross_root_parent_independence_mismatch."""
    records = copy.deepcopy(admitted_positive_projection)
    # Give record 1 the same source_article_id as record 0 in children
    art_id = records[0]["recomputed_formal_projection"]["formal_children"][0]["source_article_id"]
    for child in records[1]["recomputed_formal_projection"]["formal_children"]:
        child["source_article_id"] = art_id

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        build_cross_root_summary(records, run_id="stage1_5g_cross_root_admission_20260930T120000Z")
    assert "STOP=stage1_5g_cross_root_parent_independence_mismatch" in str(exc_info.value)


def test_reducer_duplicate_event_id(admitted_positive_projection):
    """Duplicate parent event_id across roots raises STOP=stage1_5g_cross_root_parent_independence_mismatch."""
    records = copy.deepcopy(admitted_positive_projection)
    event_id = records[0]["recomputed_formal_projection"]["formal_children"][0]["event_id"]
    for child in records[1]["recomputed_formal_projection"]["formal_children"]:
        child["event_id"] = event_id

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        build_cross_root_summary(records, run_id="stage1_5g_cross_root_admission_20260930T120000Z")
    assert "STOP=stage1_5g_cross_root_parent_independence_mismatch" in str(exc_info.value)


def test_reducer_duplicate_event_symbol_id(admitted_positive_projection):
    """Duplicate event_symbol_id collision raises STOP=stage1_5g_cross_root_child_identity_collision."""
    records = copy.deepcopy(admitted_positive_projection)
    es_id = records[0]["recomputed_formal_projection"]["formal_children"][0]["event_symbol_id"]
    records[1]["recomputed_formal_projection"]["formal_children"][0]["event_symbol_id"] = es_id

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        build_cross_root_summary(records, run_id="stage1_5g_cross_root_admission_20260930T120000Z")
    assert "STOP=stage1_5g_cross_root_child_identity_collision" in str(exc_info.value)


def test_reducer_duplicate_symbol(admitted_positive_projection):
    """Duplicate symbol collision across roots raises STOP=stage1_5g_cross_root_child_identity_collision."""
    records = copy.deepcopy(admitted_positive_projection)
    sym = records[0]["recomputed_formal_projection"]["formal_children"][0]["symbol"]
    records[1]["recomputed_formal_projection"]["formal_children"][0]["symbol"] = sym

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        build_cross_root_summary(records, run_id="stage1_5g_cross_root_admission_20260930T120000Z")
    assert "STOP=stage1_5g_cross_root_child_identity_collision" in str(exc_info.value)


def test_reducer_missing_child(admitted_positive_projection):
    """Missing expected child symbol raises STOP=stage1_5g_cross_root_child_identity_collision."""
    records = copy.deepcopy(admitted_positive_projection)
    # Pop one child from batch7
    records[1]["recomputed_formal_projection"]["formal_children"].pop()

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        build_cross_root_summary(records, run_id="stage1_5g_cross_root_admission_20260930T120000Z")
    assert "STOP=stage1_5g_cross_root_child_identity_collision" in str(exc_info.value)


def test_reducer_config_threshold_not_met(admitted_positive_projection):
    """Config threshold not exactly 3/2 or count not met raises STOP=stage1_5g_cross_root_threshold_not_met."""
    records = copy.deepcopy(admitted_positive_projection)

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        build_cross_root_summary(
            records,
            run_id="stage1_5g_cross_root_admission_20260930T120000Z",
            config_thresholds_override={"min_symbols": 99, "min_articles": 2},
        )
    assert "STOP=stage1_5g_cross_root_threshold_not_met" in str(exc_info.value)


def test_isolated_subprocess_origin_and_chdir_independence(tmp_path):
    """Step 4: Run real-root admission in isolated subprocess after chdir(tmp_path);

    assert module __file__/__spec__.origin match expected project-root paths.
    """
    code = f"""
import os, sys
from pathlib import Path

os.chdir({repr(str(tmp_path))})
from src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission import (
    admit_frozen_cross_root_inputs,
    _import_verified_upstream,
    _project_root_from_core_file,
)

root = _project_root_from_core_file()
modules = _import_verified_upstream()
for name, mod in modules.items():
    p_file = Path(mod.__file__).resolve()
    p_spec = Path(mod.__spec__.origin).resolve()
    assert str(p_file).startswith(str(root)), f"file outside root: {{p_file}}"
    assert str(p_spec).startswith(str(root)), f"spec outside root: {{p_spec}}"

admitted = admit_frozen_cross_root_inputs()
assert len(admitted) == 2
print("SUBPROCESS_CHDIR_OK")
"""
    cmd = [sys.executable, "-c", code]
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": f"{_get_project_root()}/src:{_get_project_root()}"},
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert "SUBPROCESS_CHDIR_OK" in res.stdout


def test_injected_shadow_module_origin_mismatch(tmp_path):
    """Preloaded shadow module causes STOP=stage1_5g_cross_root_upstream_module_origin_mismatch."""
    code = """
import sys, types
from pathlib import Path

# Inject a shadow module into sys.modules
fake_mod = types.ModuleType("configs.base")
fake_mod.__file__ = "/tmp/fake_configs_base.py"
fake_spec = types.SimpleNamespace(origin="/tmp/fake_configs_base.py")
fake_mod.__spec__ = fake_spec
sys.modules["configs.base"] = fake_mod

from src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission import (
    admit_frozen_cross_root_inputs,
    Stage1_5GCrossRootAdmissionError,
)

try:
    admit_frozen_cross_root_inputs()
    print("UNEXPECTED_SUCCESS")
    sys.exit(1)
except Stage1_5GCrossRootAdmissionError as e:
    assert "STOP=stage1_5g_cross_root_upstream_module_origin_mismatch" in str(e), f"Unexpected: {e}"
    print("SHADOW_INJECTION_REJECTED")
"""
    cmd = [sys.executable, "-c", code]
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(_get_project_root()),
        env={**os.environ, "PYTHONPATH": f"{_get_project_root()}/src:{_get_project_root()}"},
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert "SHADOW_INJECTION_REJECTED" in res.stdout


def test_verify_execution_authority():
    """Verify execution authority with baseline directory."""
    baseline_env = Path("/tmp/stage1_5g_cross_root_admission_env.sh")
    if not baseline_env.is_file():
        pytest.skip("No baseline env found in /tmp")

    env_lines = baseline_env.read_text().splitlines()
    baseline_dir = None
    for line in env_lines:
        if line.startswith("EXECUTION_BASELINE_DIR="):
            baseline_dir = line.split("=", 1)[1].strip()
    if not baseline_dir:
        pytest.skip("No EXECUTION_BASELINE_DIR in env")

    supplied = {
        "approved_design_path": "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md",
        "approved_design_sha256": "51a25377537dade47c7a234f93802aa445db75348f7e10b4e9c354888d4cefc7",
        "approved_plan_path": "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md",
        "approved_plan_sha256": "8bb2a6ff906d54e209d8bca6c0885211c101664b87af65e2bee0b17483369c73",
    }
    auth = verify_execution_authority(baseline_dir, supplied, project_root=_get_project_root())
    assert auth["approved_plan_sha256"] == "8bb2a6ff906d54e209d8bca6c0885211c101664b87af65e2bee0b17483369c73"

    # Mismatched binding raises STOP=approved_authority_mismatch
    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        verify_execution_authority(
            baseline_dir,
            {**supplied, "approved_plan_sha256": "0000000000000000000000000000000000000000000000000000000000000000"},
            project_root=_get_project_root(),
        )
    assert "STOP=approved_authority_mismatch" in str(exc_info.value)


def _make_mutated_baseline_dir(tmp_path: Path, mutator_fn) -> Path:
    baseline_env = Path("/tmp/stage1_5g_cross_root_admission_env.sh")
    if not baseline_env.is_file():
        pytest.skip("No baseline env found in /tmp")

    env_lines = baseline_env.read_text().splitlines()
    baseline_dir = None
    for line in env_lines:
        if line.startswith("EXECUTION_BASELINE_DIR="):
            baseline_dir = Path(line.split("=", 1)[1].strip())
    if not baseline_dir or not baseline_dir.is_dir():
        pytest.skip("No EXECUTION_BASELINE_DIR in env")

    target_dir = tmp_path / "mutated_baseline"
    target_dir.mkdir(parents=True, exist_ok=True)
    for f in baseline_dir.iterdir():
        if f.is_file():
            (target_dir / f.name).write_bytes(f.read_bytes())

    auth_p = target_dir / "execution_authority.json"
    auth_data = json.loads(auth_p.read_text(encoding="utf-8"))
    mutator_fn(auth_data)
    auth_bytes = json.dumps(auth_data, indent=2).encode("utf-8")
    auth_p.write_bytes(auth_bytes)
    (target_dir / "execution_authority.sha256").write_text(
        hashlib.sha256(auth_bytes).hexdigest() + "\n", encoding="utf-8"
    )
    return target_dir


def test_verify_execution_authority_rejects_wrong_project_root(tmp_path):
    """P0-1: verify_execution_authority rejects authority packet with forged project root."""
    target_dir = _make_mutated_baseline_dir(
        tmp_path, lambda data: data.update({"project_root": "/deliberately/wrong/project/root"})
    )
    supplied = {
        "approved_design_path": "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md",
        "approved_design_sha256": "51a25377537dade47c7a234f93802aa445db75348f7e10b4e9c354888d4cefc7",
        "approved_plan_path": "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md",
        "approved_plan_sha256": "8bb2a6ff906d54e209d8bca6c0885211c101664b87af65e2bee0b17483369c73",
    }
    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        verify_execution_authority(target_dir, supplied, project_root=_get_project_root())
    assert "STOP=approved_authority_mismatch:project_root_mismatch" in str(exc_info.value)


def test_verify_execution_authority_rejects_wrong_design_path(tmp_path):
    """P0-1: verify_execution_authority rejects authority packet with non-fixed design path."""
    target_dir = _make_mutated_baseline_dir(
        tmp_path, lambda data: data.update({"approved_design_path": "docs/designs/wrong_design.md"})
    )
    supplied = {
        "approved_design_path": "docs/designs/wrong_design.md",
        "approved_design_sha256": "51a25377537dade47c7a234f93802aa445db75348f7e10b4e9c354888d4cefc7",
        "approved_plan_path": "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md",
        "approved_plan_sha256": "8bb2a6ff906d54e209d8bca6c0885211c101664b87af65e2bee0b17483369c73",
    }
    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        verify_execution_authority(target_dir, supplied, project_root=_get_project_root())
    assert "STOP=approved_authority_mismatch:design_path_mismatch" in str(exc_info.value)


def test_verify_execution_authority_rejects_wrong_plan_path(tmp_path):
    """P0-1: verify_execution_authority rejects authority packet with non-fixed plan path."""
    target_dir = _make_mutated_baseline_dir(
        tmp_path, lambda data: data.update({"approved_plan_path": "docs/plans/wrong_plan.md"})
    )
    supplied = {
        "approved_design_path": "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md",
        "approved_design_sha256": "51a25377537dade47c7a234f93802aa445db75348f7e10b4e9c354888d4cefc7",
        "approved_plan_path": "docs/plans/wrong_plan.md",
        "approved_plan_sha256": "8bb2a6ff906d54e209d8bca6c0885211c101664b87af65e2bee0b17483369c73",
    }
    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        verify_execution_authority(target_dir, supplied, project_root=_get_project_root())
    assert "STOP=approved_authority_mismatch:plan_path_mismatch" in str(exc_info.value)


def test_verify_execution_authority_rejects_current_plan_sha_mismatch(tmp_path):
    """P0-1: verify_execution_authority rejects current_plan_sha256 != approved_plan_sha256."""
    target_dir = _make_mutated_baseline_dir(
        tmp_path, lambda data: data.update({"current_plan_sha256": "f" * 64})
    )
    supplied = {
        "approved_design_path": "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md",
        "approved_design_sha256": "51a25377537dade47c7a234f93802aa445db75348f7e10b4e9c354888d4cefc7",
        "approved_plan_path": "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md",
        "approved_plan_sha256": "8bb2a6ff906d54e209d8bca6c0885211c101664b87af65e2bee0b17483369c73",
    }
    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        verify_execution_authority(target_dir, supplied, project_root=_get_project_root())
    assert "STOP=approved_authority_mismatch:plan_sha_mismatch" in str(exc_info.value)


def test_verify_execution_authority_rejects_base_sha_mismatch(tmp_path):
    """P0-1: verify_execution_authority rejects base_sha != git HEAD."""
    target_dir = _make_mutated_baseline_dir(
        tmp_path, lambda data: data.update({"base_sha": "0" * 40})
    )
    supplied = {
        "approved_design_path": "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md",
        "approved_design_sha256": "51a25377537dade47c7a234f93802aa445db75348f7e10b4e9c354888d4cefc7",
        "approved_plan_path": "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md",
        "approved_plan_sha256": "8bb2a6ff906d54e209d8bca6c0885211c101664b87af65e2bee0b17483369c73",
    }
    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        verify_execution_authority(target_dir, supplied, project_root=_get_project_root())
    assert "STOP=approved_authority_mismatch:head_sha_mismatch" in str(exc_info.value)


# Task 3: Schema, Projection, Single-point Mutations, and Strict Loader tests


def test_render_review_matches_literal_template(admitted_positive_projection):
    """Rendered review Markdown must strictly match §5.3 literal template."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    md = render_review(summary)
    assert md.startswith("# Stage 1.5G Cross-Root Admission Receipt\n\n")
    assert "- `run_id`: `stage1_5g_cross_root_admission_20260930T120000Z`\n" in md
    assert "- `decision`: `stage1_5g_cross_root_event_family_admission_pass`\n" in md
    assert "- `cross_root_evidence_count_status`: `sufficient`\n" in md
    assert "- `stage1_5g_gate3_complete`: `false`\n" in md
    assert "- `formal_symbol_count`: `8`\n" in md
    assert "- `distinct_source_article_count`: `2`\n" in md
    assert "- `independent_parent_event_count`: `2`\n" in md
    assert "## Parent Ledger\n" in md
    assert "## Frozen Inputs\n" in md
    assert "## Authority Flags\n" in md
    assert md.endswith("\n")
    # Verify exact line endings LF
    assert "\r" not in md


def test_publish_and_load_verified_cross_root_receipt(admitted_positive_projection, tmp_path):
    """Publish to monkeypatched tmp parent and reload strictly."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    assert final_root == tmp_path / run_id
    assert final_root.is_dir()

    loaded = load_verified_cross_root_receipt(final_root)
    assert loaded["summary"]["run_id"] == run_id
    assert loaded["summary"]["decision"] == "stage1_5g_cross_root_event_family_admission_pass"
    assert loaded["manifest"]["run_id"] == run_id


def test_single_mutation_summary_extra_key(admitted_positive_projection, tmp_path):
    """Extra key in summary raises STOP."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    sum_p = final_root / "stage1_5g_cross_root_admission_summary.json"
    data = json.loads(sum_p.read_text(encoding="utf-8"))
    data["extra_unexpected_key"] = "forbidden"
    sum_p.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        load_verified_cross_root_receipt(final_root)
    assert "STOP=" in str(exc_info.value)


def test_single_mutation_summary_wrong_authority_flag(admitted_positive_projection, tmp_path):
    """Authority flag set to True raises STOP."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    sum_p = final_root / "stage1_5g_cross_root_admission_summary.json"
    data = json.loads(sum_p.read_text(encoding="utf-8"))
    data["authority_flags"]["live_trading_allowed"] = True
    sum_p.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        load_verified_cross_root_receipt(final_root)
    assert "STOP=" in str(exc_info.value)


def test_single_mutation_manifest_missing_artifact(admitted_positive_projection, tmp_path):
    """Missing artifact in manifest raises STOP."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    man_p = final_root / "stage1_5g_cross_root_admission_manifest.json"
    data = json.loads(man_p.read_text(encoding="utf-8"))
    del data["artifacts"]["review"]
    man_p.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        load_verified_cross_root_receipt(final_root)
    assert "STOP=" in str(exc_info.value)


def test_single_mutation_manifest_hash_mismatch(admitted_positive_projection, tmp_path):
    """Manifest hash mismatch raises STOP."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    man_p = final_root / "stage1_5g_cross_root_admission_manifest.json"
    data = json.loads(man_p.read_text(encoding="utf-8"))
    data["artifacts"]["summary"]["sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
    man_p.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        load_verified_cross_root_receipt(final_root)
    assert "STOP=" in str(exc_info.value)


def test_single_mutation_injected_markdown(admitted_positive_projection, tmp_path):
    """Injected text into Markdown projection raises STOP=stage1_5g_cross_root_review_projection_mismatch."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    rev_p = final_root / "stage1_5g_cross_root_admission_review_CN.md"
    rev_p.write_text(rev_p.read_text(encoding="utf-8") + "\nInjected claim\n", encoding="utf-8")

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        load_verified_cross_root_receipt(final_root)
    assert "STOP=" in str(exc_info.value)


def test_single_mutation_unlisted_file(admitted_positive_projection, tmp_path):
    """Unlisted file in receipt directory raises STOP."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    (final_root / "extra_file.txt").write_text("rogue")

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        load_verified_cross_root_receipt(final_root)
    assert "STOP=stage1_5g_cross_root_publication_integrity_failure" in str(exc_info.value)


def test_single_mutation_symlink_artifact(admitted_positive_projection, tmp_path):
    """Symlink artifact raises STOP."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    rev_p = final_root / "stage1_5g_cross_root_admission_review_CN.md"
    target = tmp_path / "somewhere.md"
    target.write_text(rev_p.read_text(encoding="utf-8"), encoding="utf-8")
    rev_p.unlink()
    rev_p.symlink_to(target)

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        load_verified_cross_root_receipt(final_root)
    assert "STOP=stage1_5g_cross_root_publication_integrity_failure" in str(exc_info.value)


def test_loader_rejects_forged_parent_identity(admitted_positive_projection, tmp_path):
    """P0-2: Strict loader rejects self-consistent but forged parent identity (e.g. 64 zeroes)."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    # Re-forge summary with parent_event_id set to 64 zeroes
    sum_file = final_root / "stage1_5g_cross_root_admission_summary.json"
    forged_summary = json.loads(sum_file.read_text(encoding="utf-8"))
    forged_summary["parent_ledger"][0]["parent_event_id"] = "0" * 64

    # Re-generate markdown, manifest, and SHA256SUMS so the directory is internally self-consistent
    forged_md = render_review(forged_summary)
    (final_root / "stage1_5g_cross_root_admission_review_CN.md").write_text(forged_md, encoding="utf-8")

    sum_bytes = canonical_json_dumps(forged_summary).encode("utf-8")
    sum_file.write_bytes(sum_bytes)

    rev_bytes = forged_md.encode("utf-8")
    man_file = final_root / "stage1_5g_cross_root_admission_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    man_data["artifacts"]["summary"]["sha256"] = hashlib.sha256(sum_bytes).hexdigest()
    man_data["artifacts"]["summary"]["byte_count"] = len(sum_bytes)
    man_data["artifacts"]["review"]["sha256"] = hashlib.sha256(rev_bytes).hexdigest()
    man_data["artifacts"]["review"]["byte_count"] = len(rev_bytes)

    man_bytes = canonical_json_dumps(man_data).encode("utf-8")
    man_file.write_bytes(man_bytes)

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        load_verified_cross_root_receipt(final_root)
    assert "STOP=stage1_5g_cross_root_publication_integrity_failure" in str(exc_info.value)


def test_loader_rejects_forged_child_event_symbol_id(admitted_positive_projection, tmp_path):
    """P0-2 residual: Strict loader rejects forged child event_symbol_id (e.g. 64 'f's) even if internally consistent."""
    summary = build_cross_root_summary(
        admitted_positive_projection,
        run_id="stage1_5g_cross_root_admission_20260930T120000Z",
    )
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    final_root = publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    # Re-forge summary with first child event_symbol_id set to 64 'f' characters
    sum_file = final_root / "stage1_5g_cross_root_admission_summary.json"
    forged_summary = json.loads(sum_file.read_text(encoding="utf-8"))
    forged_child_id = "f" * 64
    forged_summary["input_records"][0]["recomputed_formal_projection"]["formal_children"][0]["event_symbol_id"] = (
        forged_child_id
    )
    forged_summary["input_records"][0]["recomputed_formal_projection"][
        "formal_completed_event_symbol_ids_sha256"
    ] = hashlib.sha256(canonical_json_dumps([forged_child_id]).encode("utf-8")).hexdigest()
    forged_summary["parent_ledger"][0]["child_event_symbol_ids"][0] = forged_child_id

    # Re-generate markdown and manifest
    forged_md = render_review(forged_summary)
    (final_root / "stage1_5g_cross_root_admission_review_CN.md").write_text(forged_md, encoding="utf-8")

    sum_bytes = canonical_json_dumps(forged_summary).encode("utf-8")
    sum_file.write_bytes(sum_bytes)

    rev_bytes = forged_md.encode("utf-8")
    man_file = final_root / "stage1_5g_cross_root_admission_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    man_data["frozen_input_records"] = forged_summary["input_records"]
    man_data["artifacts"]["summary"]["sha256"] = hashlib.sha256(sum_bytes).hexdigest()
    man_data["artifacts"]["summary"]["byte_count"] = len(sum_bytes)
    man_data["artifacts"]["review"]["sha256"] = hashlib.sha256(rev_bytes).hexdigest()
    man_data["artifacts"]["review"]["byte_count"] = len(rev_bytes)

    man_bytes = canonical_json_dumps(man_data).encode("utf-8")
    man_file.write_bytes(man_bytes)

    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        load_verified_cross_root_receipt(final_root)
    assert "STOP=stage1_5g_cross_root_publication_integrity_failure" in str(exc_info.value)


def test_classify_receipt_state(admitted_positive_projection, tmp_path):
    """classify_receipt_state returns unpublished, staging_only, receipt_published, corrupt_or_unknown."""
    run_id = "stage1_5g_cross_root_admission_20260930T120000Z"
    assert classify_receipt_state(tmp_path, run_id) == "unpublished"

    # Create staging dir
    staging_dir = tmp_path / f".{run_id}.staging.12345"
    staging_dir.mkdir()
    assert classify_receipt_state(tmp_path, run_id) == "staging_only"

    # Publish properly
    summary = build_cross_root_summary(admitted_positive_projection, run_id=run_id)
    # staging_dir preexists for pid 12345, but publish will use os.getpid()
    publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)
    assert classify_receipt_state(tmp_path, run_id) == "receipt_published"

    # Corrupt final root
    (tmp_path / run_id / "corrupt.txt").write_text("junk")
    assert classify_receipt_state(tmp_path, run_id) == "corrupt_or_unknown"


# Task 4: Crash, Collision, Durability, and Restart Recovery tests


@pytest.mark.parametrize(
    "fault_pos",
    [
        "after_summary_write",
        "after_summary_fsync",
        "after_review_write",
        "after_review_fsync",
        "after_manifest_write",
        "after_manifest_fsync",
        "after_staging_fsync",
        "before_rename",
    ],
)
def test_lifecycle_pre_rename_failpoints(admitted_positive_projection, tmp_path, fault_pos):
    """Pre-rename failpoint leaves final root absent and staging_only state."""
    import src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission as core_mod

    def failpoint(pos: str):
        if pos == fault_pos:
            raise RuntimeError(f"SIMULATED_CRASH:{pos}")

    core_mod._FAILPOINT_HOOK = failpoint
    run_id = f"stage1_5g_cross_root_admission_20260930T1200{hash(fault_pos) % 100:02d}Z"
    summary = build_cross_root_summary(admitted_positive_projection, run_id=run_id)

    try:
        with pytest.raises(RuntimeError) as exc_info:
            publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)
        assert f"SIMULATED_CRASH:{fault_pos}" in str(exc_info.value)
    finally:
        core_mod._FAILPOINT_HOOK = None

    # Assert final root absent
    final_root = tmp_path / run_id
    assert not final_root.exists()

    # Assert classify is staging_only
    assert classify_receipt_state(tmp_path, run_id) == "staging_only"

    # Attempting to re-publish same run_id must fail (staging preexists)
    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)
    assert "STOP=stage1_5g_cross_root_publication_integrity_failure:staging_preexists" in str(exc_info.value)

    # Fresh run_id must succeed
    fresh_id = "stage1_5g_cross_root_admission_20260930T130000Z"
    fresh_summary = build_cross_root_summary(admitted_positive_projection, run_id=fresh_id)
    published = publish_cross_root_receipt(fresh_summary, run_id=fresh_id, parent_dir_override=tmp_path)
    assert published.is_dir()
    assert classify_receipt_state(tmp_path, fresh_id) == "receipt_published"


def test_lifecycle_post_rename_durability_failure(admitted_positive_projection, tmp_path):
    """After rename, failure in parent fsync raises POST_RENAME_DURABILITY_FAILURE without deleting final root."""
    import src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission as core_mod

    def failpoint(pos: str):
        if pos == "after_parent_fsync":
            raise OSError("simulated_parent_fsync_io_error")

    core_mod._FAILPOINT_HOOK = failpoint
    run_id = "stage1_5g_cross_root_admission_20260930T140000Z"
    summary = build_cross_root_summary(admitted_positive_projection, run_id=run_id)

    try:
        with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
            publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)
        assert "STOP=POST_RENAME_DURABILITY_FAILURE" in str(exc_info.value)
    finally:
        core_mod._FAILPOINT_HOOK = None

    # Final root exists and was NOT deleted
    final_root = tmp_path / run_id
    assert final_root.is_dir()

    # Byte-authoritative classifier determines receipt_published
    assert classify_receipt_state(tmp_path, run_id) == "receipt_published"


def test_lifecycle_final_root_collision_rejected(admitted_positive_projection, tmp_path):
    """Publishing to an already existing final root raises collision STOP without overwrite."""
    run_id = "stage1_5g_cross_root_admission_20260930T150000Z"
    summary = build_cross_root_summary(admitted_positive_projection, run_id=run_id)
    publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)

    # Calling publish again with same run_id must raise collision STOP
    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)
    assert "STOP=stage1_5g_cross_root_publication_integrity_failure:final_root_preexists" in str(exc_info.value)


def test_lifecycle_corrupt_final_root_not_overwritten(tmp_path):
    """Corrupt final root is classified corrupt_or_unknown and never overwritten."""
    run_id = "stage1_5g_cross_root_admission_20260930T160000Z"
    corrupt_root = tmp_path / run_id
    corrupt_root.mkdir()
    (corrupt_root / "garbage.bin").write_bytes(b"\x00\x01\x02")

    assert classify_receipt_state(tmp_path, run_id) == "corrupt_or_unknown"

    # Attempting to publish to this run_id raises collision STOP
    summary = {"run_id": run_id}
    with pytest.raises(Stage1_5GCrossRootAdmissionError) as exc_info:
        publish_cross_root_receipt(summary, run_id=run_id, parent_dir_override=tmp_path)
    assert "STOP=stage1_5g_cross_root_publication_integrity_failure:final_root_preexists" in str(exc_info.value)

    # Corrupt root file preserved
    assert (corrupt_root / "garbage.bin").read_bytes() == b"\x00\x01\x02"
