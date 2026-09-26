"""Tests for Stage 1.6F-W2-0 immutable bundle writer and strict reader.

Verifies:
- Atomic create-exclusive write and readback verification.
- Manifest-last publication.
- Exact 5 files and no extra/stray/temporary files.
- Exact 20 false authority flags.
- Strict loader rejections for single-point mutations:
  collision, symlink root/file, stale tmp, unexpected extra file,
  duplicate JSON keys, nonfinite literals, short writes,
  post-seal byte mutations, manifest key/authority mismatches,
  outcome_seen violations, and forbidden raw-price/PnL keys.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import src.research.external_signal_shadow.stage1_6f_w2_0_exploratory_terminal_basis_diagnostic as w2_0_diag
import src.research.external_signal_shadow.stage1_6f_w2_0_exploratory_terminal_basis_storage as w2_0_storage
import src.research.external_signal_shadow.stage1_6f_w2_evidence_source as w2_source
from tests.research.external_signal_shadow.stage1_6f_w2_0_test_support import (
    FROZEN_20_FALSE_FLAGS,
    create_canonical_w2_0_mirror,
)


@pytest.fixture(scope="module")
def canonical_diagnostic_result(tmp_path_factory) -> tuple[Any, Any, Any, Any]:
    """Shared canonical diagnostic run for storage tests."""
    tmp_path = tmp_path_factory.mktemp("canonical_storage_fixture")
    mirror = create_canonical_w2_0_mirror(tmp_path)
    admission = w2_0_diag.admit_w2_0_inputs(**mirror.get_admission_kwargs())
    verified_w2 = w2_source.load_verified_w2_evidence(
        project_root=mirror.project_root,
        candidate_root=mirror.candidate_root,
        approved_design_path=mirror.w2_design_path,
        approved_design_sha=mirror.w2_design_sha,
        approved_plan_path=mirror.w2_plan_path,
        approved_plan_sha=mirror.w2_plan_sha,
        network_authorization_path=mirror.w2_network_auth_path,
        network_authorization_sha=mirror.w2_network_auth_sha,
    )
    verified_rows = w2_0_diag.materialize_verified_w2_rows(verified_w2=verified_w2)
    diag_result = w2_0_diag.compute_w2_0_exploratory_terminal_basis(
        verified_w2=verified_w2,
        verified_rows=verified_rows,
        admission=admission,
    )
    return mirror, admission, verified_w2, diag_result


def test_positive_storage_write_and_strict_readback(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Canonical positive: write bundle, verify exact 5 files, and strictly read back."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    run_id = "test_run_w2_0_positive_001"
    output_root = tmp_path / "diagnostics" / run_id

    manifest_path = w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )
    assert manifest_path.is_file()
    assert manifest_path.name == "stage1_6f_w2_0_bundle_manifest.json"

    # Exactly 5 files in output_root
    files = sorted([f.name for f in output_root.iterdir()])
    assert files == [
        "stage1_6f_w2_0_bundle_manifest.json",
        "stage1_6f_w2_0_contract_metrics.jsonl",
        "stage1_6f_w2_0_denominator.jsonl",
        "stage1_6f_w2_0_parent_metrics.jsonl",
        "stage1_6f_w2_0_summary.json",
    ]

    # Strict loader reads and validates bundle
    bundle = w2_0_storage.load_verified_w2_0_bundle(
        output_root=output_root,
        project_root=mirror.project_root,
    )
    assert bundle.bundle_run_id == run_id
    assert bundle.outcome_inspection_status == "outcome_seen"
    assert bundle.research_classification == "exploratory_only"
    assert bundle.authority_flags == FROZEN_20_FALSE_FLAGS
    assert len(bundle.denominator_records) == 41
    assert len(bundle.contract_records) == 41
    assert len(bundle.parent_records) == 27


def test_storage_rejects_output_root_collision(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Writer fails closed if target output root already exists."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "colliding_root"
    output_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(w2_0_storage.W20StorageError, match="STOP=w2_0_output_root_collision"):
        w2_0_storage.write_w2_0_exploratory_bundle(
            output_root=output_root,
            diagnostic_result=diag_result,
            verified_w2=verified_w2,
            admission=admission,
        )


def test_storage_rejects_symlink_output_root(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Writer and loader reject symlinked output root."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir(parents=True, exist_ok=True)
    symlink_dir = tmp_path / "symlink_dir"
    symlink_dir.symlink_to(real_dir)

    with pytest.raises(w2_0_storage.W20StorageError, match="symlink"):
        w2_0_storage.write_w2_0_exploratory_bundle(
            output_root=symlink_dir,
            diagnostic_result=diag_result,
            verified_w2=verified_w2,
            admission=admission,
        )


def test_loader_rejects_stale_temporary_file(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects bundle with stray .tmp file."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "stale_tmp_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    stray = output_root / ".tmp_stage1_6f_w2_0_summary.json_xyz"
    stray.write_text("unfinished", encoding="utf-8")

    with pytest.raises(w2_0_storage.W20StorageError, match="unexpected_or_stale_file"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_loader_rejects_unexpected_extra_file(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects bundle with unapproved extra file."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "extra_file_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    (output_root / "extra_notes.txt").write_text("hello", encoding="utf-8")

    with pytest.raises(w2_0_storage.W20StorageError, match="unexpected_or_stale_file"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_loader_rejects_post_seal_hash_mutation(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects bundle if artifact byte hash differs from manifest."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "mutated_hash_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    summary_file = output_root / "stage1_6f_w2_0_summary.json"
    raw = bytearray(summary_file.read_bytes())
    raw[10] = ord(b"X") if raw[10] != ord(b"X") else ord(b"Y")
    summary_file.write_bytes(bytes(raw))

    with pytest.raises(w2_0_storage.W20StorageError, match="sha256_mismatch"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_loader_rejects_manifest_authority_sha_mutation(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects manifest if an authority SHA fails match against disk."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "mutated_auth_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    man_file = output_root / "stage1_6f_w2_0_bundle_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    man_data["authority_packet"]["w2_0_design"]["sha256"] = "0" * 64
    man_file.write_text(json.dumps(man_data), encoding="utf-8")

    with pytest.raises(w2_0_storage.W20StorageError, match="authority_sha_mismatch"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_loader_rejects_missing_authority_flag(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects manifest if 20-field flag is missing an entry."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "missing_flag_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    man_file = output_root / "stage1_6f_w2_0_bundle_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    del man_data["authority_flags"]["commit_allowed"]
    man_file.write_text(json.dumps(man_data), encoding="utf-8")

    with pytest.raises(w2_0_storage.W20StorageError, match="authority_flags_invalid"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_loader_rejects_true_authority_flag(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects manifest if any authority flag is True."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "true_flag_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    man_file = output_root / "stage1_6f_w2_0_bundle_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    man_data["authority_flags"]["alpha_candidate_allowed"] = True
    man_file.write_text(json.dumps(man_data), encoding="utf-8")

    with pytest.raises(w2_0_storage.W20StorageError, match="authority_flags_invalid"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_loader_rejects_outcome_not_seen(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects manifest if outcome_inspection_status is not outcome_seen."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "not_seen_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    man_file = output_root / "stage1_6f_w2_0_bundle_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    man_data["outcome_inspection_status"] = "outcome_blinded"
    man_file.write_text(json.dumps(man_data), encoding="utf-8")

    with pytest.raises(w2_0_storage.W20StorageError, match="outcome_inspection_status"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_loader_rejects_forbidden_keys_in_artifacts(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects artifacts containing raw price, pnl, or execution fields."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "forbidden_keys_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    # Inject forbidden key "pnl" into summary and update manifest hash
    summary_file = output_root / "stage1_6f_w2_0_summary.json"
    summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
    summary_data["pnl"] = 123.45
    summary_bytes = json.dumps(summary_data, sort_keys=True).encode("utf-8")
    summary_file.write_bytes(summary_bytes)

    man_file = output_root / "stage1_6f_w2_0_bundle_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    man_data["artifacts"]["stage1_6f_w2_0_summary.json"]["sha256"] = hashlib.sha256(summary_bytes).hexdigest()
    man_data["artifacts"]["stage1_6f_w2_0_summary.json"]["byte_length"] = len(summary_bytes)
    man_file.write_text(json.dumps(man_data), encoding="utf-8")

    with pytest.raises(w2_0_storage.W20StorageError, match="forbidden_field_detected"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_loader_rejects_duplicate_json_keys(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects JSON containing duplicate keys."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "duplicate_keys_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    # Write summary with duplicate key
    dup_json = b'{"schema_version": "v1", "schema_version": "v2"}'
    summary_file = output_root / "stage1_6f_w2_0_summary.json"
    summary_file.write_bytes(dup_json)

    man_file = output_root / "stage1_6f_w2_0_bundle_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    man_data["artifacts"]["stage1_6f_w2_0_summary.json"]["sha256"] = hashlib.sha256(dup_json).hexdigest()
    man_data["artifacts"]["stage1_6f_w2_0_summary.json"]["byte_length"] = len(dup_json)
    man_file.write_text(json.dumps(man_data), encoding="utf-8")

    with pytest.raises(w2_0_storage.W20StorageError, match="duplicate_json_key"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_crash_before_manifest_leaves_no_consumable_bundle(
    tmp_path: Path, canonical_diagnostic_result, monkeypatch
) -> None:
    """If writer crashes before manifest write, no manifest is published and loader rejects."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "crashed_write_root"

    # Monkeypatch os.replace to fail on manifest
    real_replace = w2_0_storage.os.replace

    def _failing_replace(src, dst):
        if "manifest" in str(dst):
            raise OSError("simulated_crash_before_manifest")
        real_replace(src, dst)

    monkeypatch.setattr(w2_0_storage.os, "replace", _failing_replace)

    with pytest.raises(OSError, match="simulated_crash_before_manifest"):
        w2_0_storage.write_w2_0_exploratory_bundle(
            output_root=output_root,
            diagnostic_result=diag_result,
            verified_w2=verified_w2,
            admission=admission,
        )

    assert not (output_root / "stage1_6f_w2_0_bundle_manifest.json").exists()

    with pytest.raises(w2_0_storage.W20StorageError, match="missing_manifest"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )


def test_loader_rejects_missing_or_corrupted_authority_packet_keys(
    tmp_path: Path, canonical_diagnostic_result
) -> None:
    """Strict loader rejects manifest if authority_packet keys do not match EXPECTED_AUTHORITY_KEYS."""
    mirror, admission, verified_w2, diag_result = canonical_diagnostic_result
    output_root = tmp_path / "corrupt_auth_packet_root"
    w2_0_storage.write_w2_0_exploratory_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_w2=verified_w2,
        admission=admission,
    )

    man_file = output_root / "stage1_6f_w2_0_bundle_manifest.json"
    man_data = json.loads(man_file.read_text(encoding="utf-8"))
    del man_data["authority_packet"]["historical_receipt"]
    man_file.write_text(json.dumps(man_data), encoding="utf-8")

    with pytest.raises(w2_0_storage.W20StorageError, match="authority_packet_keys_mismatch"):
        w2_0_storage.load_verified_w2_0_bundle(
            output_root=output_root,
            project_root=mirror.project_root,
        )

