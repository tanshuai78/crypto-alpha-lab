import json
import shutil
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_6a_futures_delisting_audit import (
    process_capture_bundle,
)
from src.research.external_signal_shadow.stage1_6a_futures_delisting_storage import (
    COMPLETION_MANIFEST_FILENAME,
    SUMMARY_FILENAME,
    load_completed_audit,
    persist_audit_artifacts,
    validate_output_root_path,
)

REQUIRED_ARTIFACT_FILENAMES = (
    "capture_bundle.jsonl",
    "audit_candidate_manifest.json",
    "detail_revisions.jsonl",
    "semantic_extractions.jsonl",
    "delisting_notices.jsonl",
    "delisting_contracts.jsonl",
    "audit_diagnostics.jsonl",
    SUMMARY_FILENAME,
)


def test_validate_output_root_path_is_new_and_confined(tmp_path, monkeypatch):
    import src.research.external_signal_shadow.stage1_6a_futures_delisting_storage as storage

    output_parent = tmp_path / "data" / "external_signal_shadow" / "stage1_6a"
    output_parent.mkdir(parents=True)
    monkeypatch.setattr(storage, "STAGE1_6A_OUTPUT_PARENT", output_parent.resolve())

    validate_output_root_path(output_parent / "new_root")
    with pytest.raises(ValueError, match="output parent"):
        validate_output_root_path(tmp_path / "outside")
    with pytest.raises(ValueError, match="output parent"):
        validate_output_root_path(output_parent)

    existing = output_parent / "existing"
    existing.mkdir()
    with pytest.raises(ValueError, match="already exists"):
        validate_output_root_path(existing)


def test_persist_and_load_completed_audit(tmp_path, monkeypatch):
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    raw_bundle_bytes = fixture_path.read_bytes()
    records = [json.loads(line) for line in raw_bundle_bytes.decode("utf-8").splitlines() if line.strip()]

    audit_result = process_capture_bundle(records)
    summary_dict = {
        "run_id": "test_run_001",
        "implementation_scope": "fixture_historical_contract_only",
        "source_audit_passed": False,
    }

    import src.research.external_signal_shadow.stage1_6a_futures_delisting_storage as storage

    output_parent = tmp_path / "data" / "external_signal_shadow" / "stage1_6a"
    output_parent.mkdir(parents=True)
    out_dir = output_parent / "stage1_6a_out"
    monkeypatch.setattr(storage, "STAGE1_6A_OUTPUT_PARENT", output_parent.resolve())
    completion_path = persist_audit_artifacts(out_dir, audit_result, summary_dict, raw_bundle_bytes, run_id="test_run_001")

    assert completion_path.exists()
    assert (out_dir / COMPLETION_MANIFEST_FILENAME).exists()
    assert (out_dir / SUMMARY_FILENAME).exists()
    assert (out_dir / "audit_candidate_manifest.json").exists()
    assert (out_dir / "delisting_contracts.jsonl").exists()
    assert (out_dir / "capture_bundle.jsonl").read_bytes() == raw_bundle_bytes
    assert (out_dir / "audit_diagnostics.jsonl").exists()

    # Load successfully
    loaded = load_completed_audit(out_dir)
    assert loaded["completion_manifest"]["status"] == "complete"
    assert loaded["completion_manifest"]["run_id"] == "test_run_001"
    assert loaded["summary"]["audit_summary_state"] == "pre_completion"
    assert set(loaded["completion_manifest"]["artifact_hashes"]) == set(REQUIRED_ARTIFACT_FILENAMES)


def test_load_completed_audit_rejects_partial_or_tampered_root(tmp_path, monkeypatch):
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    raw_bundle_bytes = fixture_path.read_bytes()
    records = [json.loads(line) for line in raw_bundle_bytes.decode("utf-8").splitlines() if line.strip()]

    audit_result = process_capture_bundle(records)
    summary_dict = {"run_id": "test_run_002"}

    import src.research.external_signal_shadow.stage1_6a_futures_delisting_storage as storage

    output_parent = tmp_path / "data" / "external_signal_shadow" / "stage1_6a"
    output_parent.mkdir(parents=True)
    monkeypatch.setattr(storage, "STAGE1_6A_OUTPUT_PARENT", output_parent.resolve())
    out_dir = output_parent / "stage1_6a_partial"
    persist_audit_artifacts(out_dir, audit_result, summary_dict, raw_bundle_bytes)

    # 1. Simulate crash before completion_manifest by deleting it
    (out_dir / COMPLETION_MANIFEST_FILENAME).unlink()
    with pytest.raises(ValueError, match="Incomplete or unverified audit root"):
        load_completed_audit(out_dir)

    # Re-persist to a new root: same-root reuse is forbidden.
    complete_dir = output_parent / "stage1_6a_complete"
    persist_audit_artifacts(complete_dir, audit_result, summary_dict, raw_bundle_bytes)

    # 2. Simulate corrupted/tampered file
    contracts_file = complete_dir / "delisting_contracts.jsonl"
    contracts_file.write_text("tampered_content\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Hash mismatch"):
        load_completed_audit(complete_dir)


def test_load_completed_audit_rejects_manifest_with_missing_authoritative_hashes(tmp_path, monkeypatch):
    import src.research.external_signal_shadow.stage1_6a_futures_delisting_storage as storage

    output_parent = tmp_path / "data" / "external_signal_shadow" / "stage1_6a"
    output_parent.mkdir(parents=True)
    monkeypatch.setattr(storage, "STAGE1_6A_OUTPUT_PARENT", output_parent.resolve())
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    raw_bundle_bytes = fixture_path.read_bytes()
    records = [json.loads(line) for line in raw_bundle_bytes.decode("utf-8").splitlines() if line.strip()]
    audit_result = process_capture_bundle(records)
    out_dir = output_parent / "stage1_6a_missing_hash"
    persist_audit_artifacts(out_dir, audit_result, {"run_id": "test"}, raw_bundle_bytes)

    completion_path = out_dir / COMPLETION_MANIFEST_FILENAME
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["artifact_hashes"].pop("delisting_contracts.jsonl")
    completion_path.write_text(json.dumps(completion), encoding="utf-8")

    with pytest.raises(ValueError, match="artifact hash set"):
        load_completed_audit(out_dir)


def test_load_completed_audit_rejects_each_crash_phase_before_completion_manifest(tmp_path, monkeypatch):
    import src.research.external_signal_shadow.stage1_6a_futures_delisting_storage as storage

    output_parent = tmp_path / "data" / "external_signal_shadow" / "stage1_6a"
    output_parent.mkdir(parents=True)
    monkeypatch.setattr(storage, "STAGE1_6A_OUTPUT_PARENT", output_parent.resolve())
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    raw_bundle_bytes = fixture_path.read_bytes()
    records = [json.loads(line) for line in raw_bundle_bytes.decode("utf-8").splitlines() if line.strip()]
    audit_result = process_capture_bundle(records)
    complete_root = output_parent / "stage1_6a_complete_source"
    persist_audit_artifacts(complete_root, audit_result, {"run_id": "crash"}, raw_bundle_bytes)

    for phase, artifact_count in (("candidate", 2), ("revision", 3), ("children", 6), ("summary", 8)):
        partial_root = output_parent / f"stage1_6a_crash_after_{phase}"
        partial_root.mkdir()
        for filename in REQUIRED_ARTIFACT_FILENAMES[:artifact_count]:
            shutil.copyfile(complete_root / filename, partial_root / filename)
        with pytest.raises(ValueError, match="Incomplete or unverified"):
            load_completed_audit(partial_root)
        if phase == "summary":
            summary = json.loads((partial_root / SUMMARY_FILENAME).read_text(encoding="utf-8"))
            assert summary["audit_summary_state"] == "pre_completion"
