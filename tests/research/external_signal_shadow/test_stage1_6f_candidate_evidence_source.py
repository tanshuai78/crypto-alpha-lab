"""Tests for stage1_6f_candidate_evidence_source.py.

Invariants: INV-CA01, INV-CA02, INV-CA03, INV-CA11, INV-CA12.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import (
    CandidateEvidenceSourceError,
    VerifiedCandidateEvidence,
    bind_candidate_publication_authority,
    bind_verified_candidate_c_authority,
    load_verified_candidate_evidence,
    validate_candidate_root_core,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    MarketEvidenceInvalidError,
    verify_market_evidence,
)
from tests.research.external_signal_shadow.stage1_6f_candidate_w1_test_support import (
    CANONICAL_CANDIDATE_RELATIVE_PATH,
    FROZEN_EXPANSION_DESIGN_PATH,
    FROZEN_EXPANSION_DESIGN_SHA,
    FROZEN_EXPANSION_PLAN_PATH,
    FROZEN_EXPANSION_PLAN_SHA,
    FROZEN_NETWORK_AUTH_PATH,
    FROZEN_NETWORK_AUTH_SHA,
    create_canonical_project_mirror,
    load_canonical_verified_c_input,
    mutate_mirror_file,
)


@pytest.fixture(scope="module")
def canonical_mirror(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("canonical_mirror")
    return create_canonical_project_mirror(base)


def test_validate_candidate_root_core_positive(canonical_mirror: Path):
    """Test shared validate_candidate_root_core against canonical mirror."""
    completed_root = canonical_mirror / CANONICAL_CANDIDATE_RELATIVE_PATH
    verified = validate_candidate_root_core(
        completed_root=completed_root,
        approved_design_path=canonical_mirror / FROZEN_EXPANSION_DESIGN_PATH,
        approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
        approved_plan_path=canonical_mirror / FROZEN_EXPANSION_PLAN_PATH,
        approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
        network_authorization_path=canonical_mirror / FROZEN_NETWORK_AUTH_PATH,
        network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        project_root=canonical_mirror,
    )
    assert isinstance(verified, VerifiedCandidateEvidence)
    assert len(verified.cohort) == 41
    assert len(verified.physical_source_objects) == 664
    assert len(verified.logical_archive_records) == 705
    assert len(verified.metric_window_coverages) == 369
    assert verified.candidate_root_state == "collection_terminal_with_gaps_or_unproven_data"
    for flag_name, flag_val in verified.authority_flags.items():
        assert flag_val is False, f"Flag {flag_name} is not False"


def test_load_verified_candidate_evidence_positive_and_rejections(canonical_mirror: Path, tmp_path: Path):
    """Test exact-002 admission wrapper requires exact canonical root and manifest."""
    # Positive
    verified = load_verified_candidate_evidence(
        project_root=canonical_mirror,
        candidate_root=canonical_mirror / CANONICAL_CANDIDATE_RELATIVE_PATH,
        approved_design_path=canonical_mirror / FROZEN_EXPANSION_DESIGN_PATH,
        approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
        approved_plan_path=canonical_mirror / FROZEN_EXPANSION_PLAN_PATH,
        approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
        network_authorization_path=canonical_mirror / FROZEN_NETWORK_AUTH_PATH,
        network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
    )
    assert verified.run_id == "expansion_candidate_run_20260917_002"

    # Rejection: alias / wrong root path
    wrong_root = tmp_path / "alias_root"
    wrong_root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(CandidateEvidenceSourceError, match="candidate_admission_invalid"):
        load_verified_candidate_evidence(
            project_root=canonical_mirror,
            candidate_root=wrong_root,
            approved_design_path=canonical_mirror / FROZEN_EXPANSION_DESIGN_PATH,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=canonical_mirror / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=canonical_mirror / FROZEN_NETWORK_AUTH_PATH,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )


def test_bind_verified_candidate_c_authority_positive_and_mutations(canonical_mirror: Path, tmp_path: Path):
    """Test candidate/C authority binding enforces exact hash matches."""
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

    completed_root = canonical_mirror / "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z"
    source_export = canonical_mirror / "data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090"

    # Positive binding
    bind_verified_candidate_c_authority(
        verified_candidate=verified_candidate,
        verified_c=verified_c,
        completed_root=completed_root,
        source_export=source_export,
    )

    # Publication authority binding positive
    pub_auth = bind_candidate_publication_authority(
        verified_candidate=verified_candidate,
        verified_c=verified_c,
    )
    assert len(pub_auth) == 41

    # Mutation test: mutate a copy of completion manifest
    mutated_mirror = create_canonical_project_mirror(tmp_path / "mutated_mirror")
    c_manifest = mutated_mirror / "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json"
    data = json.loads(c_manifest.read_text())
    data["audit_run_id"] = "tampered_run_id"
    mutate_mirror_file(c_manifest, json.dumps(data).encode("utf-8"))

    with pytest.raises(CandidateEvidenceSourceError, match="upstream_denominator_authority_invalid"):
        bind_verified_candidate_c_authority(
            verified_candidate=verified_candidate,
            verified_c=verified_c,
            completed_root=mutated_mirror / "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z",
            source_export=source_export,
        )


def test_asymmetric_compatibility_reef_rejects_candidate(canonical_mirror: Path):
    """Ensure verify_market_evidence strictly rejects candidate root."""
    candidate_root = canonical_mirror / CANONICAL_CANDIDATE_RELATIVE_PATH
    with pytest.raises(MarketEvidenceInvalidError):
        verify_market_evidence(market_evidence_root=candidate_root)


def test_source_module_imports_and_layering():
    """Ensure stage1_6f_candidate_evidence_source.py imports no scripts, networks, or execution."""
    src_file = Path("src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py")
    if not src_file.exists():
        pytest.fail("stage1_6f_candidate_evidence_source.py does not exist yet")

    tree = ast.parse(src_file.read_text(encoding="utf-8"))
    forbidden_modules = {
        "urllib", "http", "socket", "requests", "httpx", "aiohttp", "websockets",
        "ftplib", "subprocess", "scripts", "src.execution",
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
                if node.module.startswith("scripts"):
                    pytest.fail(f"Layering violation: import from scripts: {node.module}")
                if "execution" in node.module:
                    pytest.fail(f"Safety violation: import from execution: {node.module}")


def test_load_verified_candidate_evidence_rejects_expansion_authority_mutations(canonical_mirror: Path, tmp_path: Path):
    """Test that mutating expansion Design, Plan, or network auth file on disk is strictly rejected."""
    # 1. Mutate expansion design
    mirror1 = create_canonical_project_mirror(tmp_path / "mirror1")
    design_p = mirror1 / FROZEN_EXPANSION_DESIGN_PATH
    mutate_mirror_file(design_p, b"# tampered design\n")
    with pytest.raises(CandidateEvidenceSourceError, match="workspace_authority_mismatch"):
        load_verified_candidate_evidence(
            project_root=mirror1,
            candidate_root=mirror1 / CANONICAL_CANDIDATE_RELATIVE_PATH,
            approved_design_path=design_p,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=mirror1 / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=mirror1 / FROZEN_NETWORK_AUTH_PATH,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )

    # 2. Mutate expansion plan
    mirror2 = create_canonical_project_mirror(tmp_path / "mirror2")
    plan_p = mirror2 / FROZEN_EXPANSION_PLAN_PATH
    mutate_mirror_file(plan_p, b"# tampered plan\n")
    with pytest.raises(CandidateEvidenceSourceError, match="workspace_authority_mismatch"):
        load_verified_candidate_evidence(
            project_root=mirror2,
            candidate_root=mirror2 / CANONICAL_CANDIDATE_RELATIVE_PATH,
            approved_design_path=mirror2 / FROZEN_EXPANSION_DESIGN_PATH,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=plan_p,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=mirror2 / FROZEN_NETWORK_AUTH_PATH,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )

    # 3. Mutate network authorization file
    mirror3 = create_canonical_project_mirror(tmp_path / "mirror3")
    net_auth_p = mirror3 / FROZEN_NETWORK_AUTH_PATH
    mutate_mirror_file(net_auth_p, b'{"run_id": "tampered"}\n')
    with pytest.raises(CandidateEvidenceSourceError, match="(network_auth_sha_mismatch|workspace_authority_mismatch)"):
        load_verified_candidate_evidence(
            project_root=mirror3,
            candidate_root=mirror3 / CANONICAL_CANDIDATE_RELATIVE_PATH,
            approved_design_path=mirror3 / FROZEN_EXPANSION_DESIGN_PATH,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=mirror3 / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=net_auth_p,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )


def test_load_verified_candidate_evidence_rejects_authority_symlinks(canonical_mirror: Path, tmp_path: Path):
    """Test that symlinks for expansion Design, Plan, or network auth are rejected."""
    mirror = create_canonical_project_mirror(tmp_path / "symlink_mirror")

    # Symlink design
    design_p = mirror / FROZEN_EXPANSION_DESIGN_PATH
    real_design = tmp_path / "real_design.md"
    real_design.write_bytes(design_p.read_bytes())
    design_p.unlink()
    design_p.symlink_to(real_design)

    with pytest.raises(CandidateEvidenceSourceError, match="symlink_detected"):
        load_verified_candidate_evidence(
            project_root=mirror,
            candidate_root=mirror / CANONICAL_CANDIDATE_RELATIVE_PATH,
            approved_design_path=design_p,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=mirror / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=mirror / FROZEN_NETWORK_AUTH_PATH,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )

    # Symlink network auth
    mirror_net = create_canonical_project_mirror(tmp_path / "symlink_net_mirror")
    net_p = mirror_net / FROZEN_NETWORK_AUTH_PATH
    real_net = tmp_path / "real_net.json"
    real_net.write_bytes(net_p.read_bytes())
    net_p.unlink()
    net_p.symlink_to(real_net)

    with pytest.raises(CandidateEvidenceSourceError, match="symlink_detected"):
        load_verified_candidate_evidence(
            project_root=mirror_net,
            candidate_root=mirror_net / CANONICAL_CANDIDATE_RELATIVE_PATH,
            approved_design_path=mirror_net / FROZEN_EXPANSION_DESIGN_PATH,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=mirror_net / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=net_p,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )


def test_load_verified_candidate_evidence_rejects_missing_fixed_auth_with_alias_copy(
    canonical_mirror: Path, tmp_path: Path
):
    """Test that deleting fixed canonical network auth and placing an identical copy at an alias path strictly fails admission."""
    mirror = create_canonical_project_mirror(tmp_path / "alias_probe_mirror")
    fixed_auth_path = mirror / FROZEN_NETWORK_AUTH_PATH
    auth_bytes = fixed_auth_path.read_bytes()

    # Place identical copy at alias path under evidence_candidates/
    alias_auth_path = mirror / CANONICAL_CANDIDATE_RELATIVE_PATH / "network_auth_expansion_run_20260917_002.json"
    alias_auth_path.write_bytes(auth_bytes)

    # Delete fixed canonical auth file
    fixed_auth_path.unlink()

    # Probe 1: Passing alias path must be rejected as not canonical
    with pytest.raises(CandidateEvidenceSourceError, match="candidate_admission_invalid:network_auth_path_not_canonical"):
        load_verified_candidate_evidence(
            project_root=mirror,
            candidate_root=mirror / CANONICAL_CANDIDATE_RELATIVE_PATH,
            approved_design_path=mirror / FROZEN_EXPANSION_DESIGN_PATH,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=mirror / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=alias_auth_path,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )

    # Probe 2: Passing canonical path when file is missing must be rejected as missing
    with pytest.raises(CandidateEvidenceSourceError, match="candidate_admission_invalid:missing_network_authorization"):
        load_verified_candidate_evidence(
            project_root=mirror,
            candidate_root=mirror / CANONICAL_CANDIDATE_RELATIVE_PATH,
            approved_design_path=mirror / FROZEN_EXPANSION_DESIGN_PATH,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=mirror / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=fixed_auth_path,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )

    # Independent probe assertion verifying NETWORK_AUTH_ALIAS_ACCEPTED is False
    network_auth_alias_accepted = False
    try:
        load_verified_candidate_evidence(
            project_root=mirror,
            candidate_root=mirror / CANONICAL_CANDIDATE_RELATIVE_PATH,
            approved_design_path=mirror / FROZEN_EXPANSION_DESIGN_PATH,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=mirror / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=alias_auth_path,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )
        network_auth_alias_accepted = True
    except CandidateEvidenceSourceError:
        network_auth_alias_accepted = False

    assert network_auth_alias_accepted is False, "NETWORK_AUTH_ALIAS_ACCEPTED must be False"

