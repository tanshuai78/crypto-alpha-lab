"""Tests for candidate W1 sealed diagnostic storage and strict loader.

Invariants: INV-CA06 through INV-CA11.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import (
    CANONICAL_CANDIDATE_RELATIVE_PATH,
    bind_candidate_publication_authority,
    bind_verified_candidate_c_authority,
    load_verified_candidate_evidence,
)
from src.research.external_signal_shadow.stage1_6f_candidate_w1_descriptive_diagnostic import (
    compute_candidate_w1_descriptive_diagnostic,
)
from src.research.external_signal_shadow.stage1_6f_candidate_w1_diagnostic_storage import (
    CandidateW1StorageError,
    VerifiedCandidateW1Bundle,
    load_candidate_w1_bundle,
    write_candidate_w1_bundle,
)
from tests.research.external_signal_shadow.stage1_6f_candidate_w1_test_support import (
    B_SOURCE_EXPORT_RELATIVE,
    C_COMPLETED_ROOT_RELATIVE,
    FROZEN_ADMISSION_DESIGN_PATH,
    FROZEN_ADMISSION_DESIGN_SHA,
    FROZEN_EXPANSION_DESIGN_PATH,
    FROZEN_EXPANSION_DESIGN_SHA,
    FROZEN_EXPANSION_PLAN_PATH,
    FROZEN_EXPANSION_PLAN_SHA,
    FROZEN_NETWORK_AUTH_PATH,
    FROZEN_NETWORK_AUTH_SHA,
    create_canonical_project_mirror,
    load_canonical_verified_c_input,
)


@pytest.fixture(scope="module")
def canonical_mirror(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("canonical_mirror_storage")
    return create_canonical_project_mirror(base)


@pytest.fixture(scope="module")
def candidate_w1_result(canonical_mirror: Path):
    verified_candidate = load_verified_candidate_evidence(
        project_root=canonical_mirror,
        candidate_root=canonical_mirror / CANONICAL_CANDIDATE_RELATIVE_PATH,
        approved_design_path=canonical_mirror / FROZEN_EXPANSION_DESIGN_PATH,
        approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
        approved_plan_path=canonical_mirror / FROZEN_EXPANSION_PLAN_PATH,
        approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
        network_authorization_path=canonical_mirror / FROZEN_NETWORK_AUTH_PATH,
        network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
    )
    verified_c = load_canonical_verified_c_input(canonical_mirror)
    c_auth = bind_verified_candidate_c_authority(
        verified_candidate=verified_candidate,
        verified_c=verified_c,
        completed_root=canonical_mirror / C_COMPLETED_ROOT_RELATIVE,
        source_export=canonical_mirror / B_SOURCE_EXPORT_RELATIVE,
    )
    pub_auth = bind_candidate_publication_authority(
        verified_candidate=verified_candidate,
        verified_c=verified_c,
    )
    res = compute_candidate_w1_descriptive_diagnostic(
        verified_candidate=verified_candidate,
        verified_c=verified_c,
        c_authority=c_auth,
        publication_authority=pub_auth,
    )
    return verified_candidate, verified_c, res


def test_write_and_load_candidate_w1_bundle_positive(
    candidate_w1_result,
    canonical_mirror: Path,
    tmp_path: Path,
):
    """Verify sealed write and strict read-back of positive bundle."""
    verified_candidate, verified_c, diag_result = candidate_w1_result
    run_id = "test_bundle_run_001"
    output_root = tmp_path / "diagnostics" / run_id

    # 1. Write bundle
    manifest_path = write_candidate_w1_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_candidate=verified_candidate,
        verified_c=verified_c,
        approved_design_path=canonical_mirror / FROZEN_ADMISSION_DESIGN_PATH,
        approved_design_sha=FROZEN_ADMISSION_DESIGN_SHA,
    )
    assert manifest_path.is_file()
    assert manifest_path.name == "stage1_6f_candidate_w1_bundle_manifest.json"

    # Exactly 4 artifacts
    artifacts = sorted([p.name for p in output_root.iterdir() if not p.name.startswith(".")])
    assert artifacts == [
        "stage1_6f_candidate_w1_bundle_manifest.json",
        "stage1_6f_candidate_w1_denominator.jsonl",
        "stage1_6f_candidate_w1_metrics.jsonl",
        "stage1_6f_candidate_w1_summary.json",
    ]

    # 2. Load bundle strictly
    bundle: VerifiedCandidateW1Bundle = load_candidate_w1_bundle(output_root=output_root)
    assert bundle.manifest["schema_version"] == "stage1_6f_candidate_w1_descriptive_bundle_v1"
    assert bundle.manifest["bundle_run_id"] == run_id
    assert bundle.manifest["bundle_state_at_write"] == "sealed_valid_at_write"
    assert bundle.manifest["denominator_count"] == 41
    assert len(bundle.denominator_rows) == 41
    assert len(bundle.metric_records) == 779
    assert len(bundle.summary["metric_horizon_groups"]) == 45
    assert len(bundle.manifest["metric_status_counts"]) == 38
    assert bundle.summary["n_denominator"] == 41
    assert bundle.summary["n_unique_parent_article_ids"] == 27


def test_storage_rejects_output_collision(
    candidate_w1_result,
    canonical_mirror: Path,
    tmp_path: Path,
):
    """Verify write_candidate_w1_bundle rejects existing output directory."""
    verified_candidate, verified_c, diag_result = candidate_w1_result
    run_id = "test_bundle_collision"
    output_root = tmp_path / run_id
    output_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(CandidateW1StorageError, match="collision|already_exists"):
        write_candidate_w1_bundle(
            output_root=output_root,
            diagnostic_result=diag_result,
            verified_candidate=verified_candidate,
            verified_c=verified_c,
            approved_design_path=canonical_mirror / FROZEN_ADMISSION_DESIGN_PATH,
            approved_design_sha=FROZEN_ADMISSION_DESIGN_SHA,
        )


def test_strict_loader_rejects_tampered_metric_bytes(
    candidate_w1_result,
    canonical_mirror: Path,
    tmp_path: Path,
):
    """Verify loader rejects artifact SHA mismatch when a byte is altered."""
    verified_candidate, verified_c, diag_result = candidate_w1_result
    run_id = "test_bundle_tamper"
    output_root = tmp_path / run_id

    write_candidate_w1_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_candidate=verified_candidate,
        verified_c=verified_c,
        approved_design_path=canonical_mirror / FROZEN_ADMISSION_DESIGN_PATH,
        approved_design_sha=FROZEN_ADMISSION_DESIGN_SHA,
    )

    metrics_file = output_root / "stage1_6f_candidate_w1_metrics.jsonl"
    data = metrics_file.read_bytes()
    metrics_file.write_bytes(data + b"\n")

    with pytest.raises(CandidateW1StorageError, match="sha|length|mismatch"):
        load_candidate_w1_bundle(output_root=output_root)


def test_strict_loader_rejects_extra_file_or_symlink(
    candidate_w1_result,
    canonical_mirror: Path,
    tmp_path: Path,
):
    """Verify loader rejects undeclared files, stale temp files, and symlinks."""
    verified_candidate, verified_c, diag_result = candidate_w1_result
    run_id = "test_bundle_extra"
    output_root = tmp_path / run_id

    write_candidate_w1_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_candidate=verified_candidate,
        verified_c=verified_c,
        approved_design_path=canonical_mirror / FROZEN_ADMISSION_DESIGN_PATH,
        approved_design_sha=FROZEN_ADMISSION_DESIGN_SHA,
    )

    extra_file = output_root / "unexpected.txt"
    extra_file.write_text("rogue", encoding="utf-8")
    with pytest.raises(CandidateW1StorageError, match="unexpected_file|unlisted"):
        load_candidate_w1_bundle(output_root=output_root)
    extra_file.unlink()

    # Symlink
    symlink_file = output_root / "link_manifest"
    symlink_file.symlink_to(output_root / "stage1_6f_candidate_w1_bundle_manifest.json")
    with pytest.raises(CandidateW1StorageError, match="symlink"):
        load_candidate_w1_bundle(output_root=output_root)


def test_strict_loader_rejects_flag_flip(
    candidate_w1_result,
    canonical_mirror: Path,
    tmp_path: Path,
):
    """Verify loader rejects any authority flag flipped to True."""
    verified_candidate, verified_c, diag_result = candidate_w1_result
    run_id = "test_bundle_flag_flip"
    output_root = tmp_path / run_id

    write_candidate_w1_bundle(
        output_root=output_root,
        diagnostic_result=diag_result,
        verified_candidate=verified_candidate,
        verified_c=verified_c,
        approved_design_path=canonical_mirror / FROZEN_ADMISSION_DESIGN_PATH,
        approved_design_sha=FROZEN_ADMISSION_DESIGN_SHA,
    )

    manifest_file = output_root / "stage1_6f_candidate_w1_bundle_manifest.json"
    m = json.loads(manifest_file.read_text(encoding="utf-8"))
    m["authority_flags"]["RISK_LIVE_TRADING_ENABLED"] = True
    manifest_file.write_text(json.dumps(m, indent=2), encoding="utf-8")

    with pytest.raises(CandidateW1StorageError, match="authority_flag|not_false"):
        load_candidate_w1_bundle(output_root=output_root)
