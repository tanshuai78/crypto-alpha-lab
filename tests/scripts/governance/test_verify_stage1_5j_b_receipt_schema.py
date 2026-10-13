"""Tests for scripts/governance/verify_stage1_5j_b_receipt_schema.py.

Strictly verifies:
1. CLI argument validation (rc=2 for missing, unsupported profile, non-relative or non-descendant path).
2. AST strict standard-library isolation & zero forbidden imports/calls.
3. Profile authority literal constants: profile_id='stage1_5j_b_receipt_v1', version=1, four Design hashes.
4. Minimal valid synthetic J-B receipt fixture (rc=0).
5. Comprehensive single-mutation negative probe matrix (rc=1).
"""

import ast
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

# Target CLI entrypoint to verify
from scripts.governance.verify_stage1_5j_b_receipt_schema import (
    GOVERNANCE_PARENT_DESIGN_PATH,
    GOVERNANCE_PARENT_DESIGN_SHA256,
    J_B_PARENT_DESIGN_PATH,
    J_B_PARENT_DESIGN_SHA256,
    J_B_PROFILE_DESIGN_DELTA_PATH,
    J_B_REBIND_DELTA_PATH,
    J_B_REBIND_DELTA_SHA256,
    J_B_RECEIPT_SCHEMA_AUTHORITY_PATH,
    J_B_RECEIPT_SCHEMA_AUTHORITY_SHA256,
    LATEST_J_B_DOMAIN_DESIGN_PATH,
    LATEST_J_B_DOMAIN_DESIGN_SHA256,
    OUTPUT_PARENT,
    PROFILE_AUDITED_CONFIG_RELATIVE_PATH,
    PROFILE_AUDITED_CONFIG_SHA256,
    PROFILE_CONTRACT_VERSION,
    PROFILE_CONTRACT_VERSION_V2,
    PROFILE_ID,
    PROFILE_ID_V2,
    PROFILE_V2_DESIGN_PATH,
    PROFILE_V2_DESIGN_SHA256,
    RUN_ID_REGEX,
    SCHEMA_VERSION,
    main,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


# -----------------------------------------------------------------------------
# 1. Profile Authority Literals and Constants
# -----------------------------------------------------------------------------


def test_profile_authority_literals() -> None:
    """Assert frozen profile authority literal constants."""
    assert PROFILE_ID == "stage1_5j_b_receipt_v1"
    assert PROFILE_CONTRACT_VERSION == 1
    assert OUTPUT_PARENT == "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response"
    assert RUN_ID_REGEX == r"^stage1_5j_b_historical_aggtrades_launch_response_[0-9]{8}T[0-9]{6}Z$"
    assert SCHEMA_VERSION == "stage1_5j_b_historical_aggtrades_launch_response_v1"

    assert J_B_PARENT_DESIGN_PATH == "docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md"
    assert J_B_PARENT_DESIGN_SHA256 == "ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b"

    assert J_B_REBIND_DELTA_PATH == "docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md"
    assert J_B_REBIND_DELTA_SHA256 == "0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c"

    assert J_B_RECEIPT_SCHEMA_AUTHORITY_PATH == "docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md"
    assert J_B_RECEIPT_SCHEMA_AUTHORITY_SHA256 == "f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25"

    assert J_B_PROFILE_DESIGN_DELTA_PATH == "docs/designs/2026-10-11-governance-stage1-5j-b-receipt-rule17-profile-design-delta_CN.md"

    assert GOVERNANCE_PARENT_DESIGN_PATH == "docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md"
    assert GOVERNANCE_PARENT_DESIGN_SHA256 == "73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4"


# -----------------------------------------------------------------------------
# 2. AST Isolation and Standard-Library Purity
# -----------------------------------------------------------------------------


def test_ast_standard_library_isolation() -> None:
    """Assert verifier script imports strictly standard library and no forbidden modules."""
    script_path = PROJECT_ROOT / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py"
    assert script_path.is_file()

    tree = ast.parse(script_path.read_text(encoding="utf-8"), filename=str(script_path))

    allowed_modules = {
        "sys", "os", "json", "pathlib", "re", "argparse", "hashlib", "decimal"
    }

    forbidden_names = {
        "subprocess", "socket", "urllib", "requests", "http", "importlib",
        "runpy", "pickle", "ctypes", "builtins", "pytest"
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert root_pkg in allowed_modules, f"Forbidden import: {alias.name}"
                assert root_pkg not in forbidden_names, f"Directly forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg in allowed_modules, f"Forbidden import from: {node.module}"
                assert root_pkg not in forbidden_names, f"Directly forbidden import from: {node.module}"
                assert not root_pkg.startswith("src"), f"Forbidden src import: {node.module}"
                assert not root_pkg.startswith("configs"), f"Forbidden configs import: {node.module}"


# -----------------------------------------------------------------------------
# 3. CLI Argument Validation (rc=2)
# -----------------------------------------------------------------------------


def test_cli_argument_validation(tmp_path: Path) -> None:
    """Assert invalid CLI arguments and paths exit with rc=2."""
    assert main([]) == 2
    assert main(["--profile", "stage1_5j_b_receipt_v2", "--artifact-root", "data/foo"]) == 2
    assert main(["--profile", "stage1_5j_b_receipt_v1", "--artifact-root", "/absolute/path"]) == 2
    assert main(["--profile", "stage1_5j_b_receipt_v1", "--artifact-root", "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/../escape"]) == 2
    assert main(["--profile", "stage1_5j_b_receipt_v1", "--artifact-root", "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/non_existent_20261011T120000Z"]) == 2


# -----------------------------------------------------------------------------
# 4. Helper for Building Minimal Valid Synthetic Sealed Receipt Tree
# -----------------------------------------------------------------------------


def _build_minimal_valid_receipt(root: Path, run_id: str = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z") -> dict:
    root.mkdir(parents=True, exist_ok=True)

    summary_obj = {
        "analysis_state": "historical_aggtrades_launch_response_complete",
        "authority_flags": {
            "alpha_claim_allowed": False,
            "broker_routing_allowed": False,
            "capital_commitment_allowed": False,
            "discretionary_override_allowed": False,
            "execution_engine_allowed": False,
            "execution_feasibility_claim_allowed": False,
            "live_trading_allowed": False,
            "network_access_allowed": False,
            "paper_trading_allowed": False,
            "position_sizing_allowed": False,
            "realtime_telemetry_allowed": False,
            "trade_intent_allowed": False
        },
        "authority_packet": {
            "approved_j_b_design": {
                "relative_path": J_B_RECEIPT_SCHEMA_AUTHORITY_PATH,
                "sha256": J_B_RECEIPT_SCHEMA_AUTHORITY_SHA256
            }
        },
        "child_horizon_rows": [],
        "child_rows": [],
        "decision": "stage1_5j_b_historical_aggtrades_launch_response_published",
        "j_a_input": {
            "catalog_denominator_count": 335,
            "child_coverage_complete_count": 280,
            "child_coverage_gap_count": 1,
            "in_scope_usdt_child_count": 281,
            "j_a_core_path": "src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py",
            "j_a_core_sha256": "250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18",
            "j_a_manifest_sha256": "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf",
            "j_a_request_journal_sha256": "b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa",
            "j_a_review_sha256": "1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152",
            "j_a_root_relative_path": "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z",
            "j_a_run_id": "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z",
            "j_a_summary_sha256": "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b",
            "out_of_scope_child_count": 5,
            "parent_coverage_complete_count": 120,
            "parent_coverage_gap_count": 11,
            "resolved_parent_count": 125,
            "target_parent_count": 131
        },
        "parent_horizon_rows": [],
        "parent_rows": [],
        "research_status": {
            "alpha_evidence_status": "evidence_insufficient",
            "capital_survival_claim": "not_evaluated",
            "economic_edge_claim": "not_evaluated",
            "execution_feasibility_claim": "not_evaluated",
            "live_permission_claim": False,
            "phenomenon_claim": "not_evaluated",
            "research_mode": "exploratory_descriptive_only",
            "statistical_edge_claim": "not_evaluated"
        },
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
        "summary_projections": {
            "canonical_horizons_ms": [300000, 3600000, 14400000],
            "child_horizon_rows_count": 0,
            "child_rows_count": 0,
            "parent_horizon_rows_count": 0,
            "parent_rows_count": 0
        }
    }

    # Summary json
    summary_bytes = (json.dumps(summary_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    (root / "summary.json").write_bytes(summary_bytes)

    # Review markdown
    review_bytes = b"# Stage 1.5J-B Review\n\nDescriptive exploratory reduction.\n"
    (root / "review_CN.md").write_bytes(review_bytes)

    # Manifest json
    manifest_obj = {
        "artifacts": [
            {
                "byte_count": len(review_bytes),
                "path": "review_CN.md",
                "sha256": hashlib.sha256(review_bytes).hexdigest()
            },
            {
                "byte_count": len(summary_bytes),
                "path": "summary.json",
                "sha256": hashlib.sha256(summary_bytes).hexdigest()
            }
        ],
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION
    }
    manifest_bytes = (json.dumps(manifest_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    (root / "manifest.json").write_bytes(manifest_bytes)

    return summary_obj


# -----------------------------------------------------------------------------
# 5. Minimal Valid Fixture Validation (rc=0)
# -----------------------------------------------------------------------------


def test_minimal_valid_fixture(tmp_path: Path) -> None:
    """Assert minimal conformant fixture passes verifier with rc=0."""
    fake_proj = tmp_path / "mock_project"
    fake_proj.mkdir(parents=True, exist_ok=True)

    rel_root = f"{OUTPUT_PARENT}/stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = fake_proj / rel_root
    _build_minimal_valid_receipt(target_root)

    # Copy verifier script into fake project to run directly
    script_dst = fake_proj / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py"
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJECT_ROOT / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py", script_dst)

    cwd = os.getcwd()
    try:
        os.chdir(fake_proj)
        rc = main(["--profile", PROFILE_ID, "--artifact-root", rel_root])
        assert rc == 0
    finally:
        os.chdir(cwd)


# -----------------------------------------------------------------------------
# 6. Single-Mutation Negative Probe Matrix (rc=1)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation_key,mutator",
    [
        ("manifest_hash_tamper", lambda root, s: (root / "summary.json").write_bytes(b"tampered\n")),
        ("unexpected_file", lambda root, s: (root / "extra.txt").write_bytes(b"unexpected\n")),
        ("missing_manifest", lambda root, s: (root / "manifest.json").unlink()),
        ("authority_flag_true", lambda root, s: _mutate_summary(root, s, lambda o: o["authority_flags"].__setitem__("live_trading_allowed", True))),
        ("invalid_approved_design", lambda root, s: _mutate_summary(root, s, lambda o: o["authority_packet"]["approved_j_b_design"].__setitem__("sha256", "0" * 64))),
        ("invalid_rebind_projection", lambda root, s: _mutate_summary(root, s, lambda o: o["j_a_input"].__setitem__("parent_coverage_complete_count", 999))),
        ("invalid_schema_version", lambda root, s: _mutate_summary(root, s, lambda o: o.__setitem__("schema_version", "invalid_v9"))),
        ("research_status_claim_true", lambda root, s: _mutate_summary(root, s, lambda o: o["research_status"].__setitem__("live_permission_claim", True))),
    ],
)
def test_single_mutation_matrix(tmp_path: Path, mutation_key: str, mutator) -> None:
    """Assert each single mutation fails closed with rc=1."""
    fake_proj = tmp_path / f"mock_project_{mutation_key}"
    fake_proj.mkdir(parents=True, exist_ok=True)

    rel_root = f"{OUTPUT_PARENT}/stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = fake_proj / rel_root
    summary_obj = _build_minimal_valid_receipt(target_root)

    mutator(target_root, summary_obj)

    script_dst = fake_proj / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py"
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJECT_ROOT / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py", script_dst)

    cwd = os.getcwd()
    try:
        os.chdir(fake_proj)
        rc = main(["--profile", PROFILE_ID, "--artifact-root", rel_root])
        assert rc == 1, f"Mutation '{mutation_key}' expected rc=1, got rc={rc}"
    finally:
        os.chdir(cwd)


def _mutate_summary(root: Path, summary_obj: dict, mutate_fn) -> None:
    mutate_fn(summary_obj)
    raw = (json.dumps(summary_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    (root / "summary.json").write_bytes(raw)
    # Also update manifest so we test semantic/schema gate, not manifest hash mismatch
    review_bytes = (root / "review_CN.md").read_bytes()
    manifest_obj = {
        "artifacts": [
            {
                "byte_count": len(review_bytes),
                "path": "review_CN.md",
                "sha256": hashlib.sha256(review_bytes).hexdigest()
            },
            {
                "byte_count": len(raw),
                "path": "summary.json",
                "sha256": hashlib.sha256(raw).hexdigest()
            }
        ],
        "run_id": summary_obj["run_id"],
        "schema_version": SCHEMA_VERSION
    }
    m_bytes = (json.dumps(manifest_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    (root / "manifest.json").write_bytes(m_bytes)


# -----------------------------------------------------------------------------
# 7. Profile v2 Authority Literals and Constants
# -----------------------------------------------------------------------------


def test_profile_authority_literals_v2() -> None:
    """Assert frozen v2 profile authority literal constants."""
    assert PROFILE_ID_V2 == "stage1_5j_b_receipt_v2"
    assert PROFILE_CONTRACT_VERSION_V2 == 2

    assert LATEST_J_B_DOMAIN_DESIGN_PATH == "docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md"
    assert LATEST_J_B_DOMAIN_DESIGN_SHA256 == "66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f"

    assert PROFILE_AUDITED_CONFIG_RELATIVE_PATH == "configs/stage1_5j_b_historical_aggtrades_launch_response.py"
    assert PROFILE_AUDITED_CONFIG_SHA256 == "771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4"

    assert PROFILE_V2_DESIGN_PATH == "docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md"
    assert PROFILE_V2_DESIGN_SHA256 == "8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454"


# -----------------------------------------------------------------------------
# 8. Helper for Building Minimal Valid Synthetic Sealed Receipt Tree v2
# -----------------------------------------------------------------------------


def _build_minimal_valid_receipt_v2(root: Path, run_id: str = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z") -> dict:
    root.mkdir(parents=True, exist_ok=True)

    child_rows = []
    for i in range(281):
        p_idx = i % 131
        is_gap_parent = p_idx >= 120
        child_rows.append({
            "anchor_delay_ms": None,
            "anchor_price": None,
            "anchor_state": "anchor_unavailable_inherited_j_a_parent_gap" if is_gap_parent else "evidence_gap",
            "anchor_time_ms": None,
            "j_a_child_state": "j_a_child_coverage_complete",
            "j_a_parent_state": "coverage_evidence_gap_archive" if is_gap_parent else "coverage_complete",
            "required_archive_dates_by_horizon": {
                "300000": [],
                "3600000": [],
                "14400000": [],
            },
            "source_article_id": f"{p_idx:032x}",
            "symbol": f"SYM{i}USDT",
            "symbol_launch_time_ms": 1700000000000 + i,
        })

    child_horizon_rows = []
    for i in range(281):
        p_idx = i % 131
        is_gap_parent = p_idx >= 120
        for h_ms in (300000, 3600000, 14400000):
            child_horizon_rows.append({
                "child_horizon_state": "child_horizon_evidence_gap",
                "gross_return_bps": None,
                "horizon_ms": h_ms,
                "horizon_offset_ms": None,
                "horizon_price": None,
                "horizon_selected_time_ms": None,
                "horizon_target_time_ms": 1700000000000 + i + h_ms,
                "missing_reason": "inherited_j_a_parent_gap" if is_gap_parent else "evidence_gap_missing_horizon_trade",
                "sampled_max_excursion_bps": None,
                "sampled_min_excursion_bps": None,
                "source_article_id": f"{p_idx:032x}",
                "symbol": f"SYM{i}USDT",
                "trade_count": None,
            })

    parent_horizon_rows = []
    for i in range(131):
        is_gap_parent = i >= 120
        for h_ms in (300000, 3600000, 14400000):
            parent_horizon_rows.append({
                "failed_child_reasons": [{"missing_reason": "inherited_j_a_parent_gap" if is_gap_parent else "evidence_gap_missing_horizon_trade", "symbol": f"SYM{i}USDT"}],
                "horizon_ms": h_ms,
                "parent_gross_return_bps": None,
                "parent_horizon_state": "parent_horizon_evidence_gap",
                "parent_sampled_max_excursion_bps": None,
                "parent_sampled_min_excursion_bps": None,
                "source_article_id": f"{i:032x}",
                "source_parent_state": "coverage_evidence_gap_archive" if is_gap_parent else "coverage_complete",
            })

    cov_counts = {
        "j_a_parent_coverage_complete_count": 120,
        "j_a_parent_coverage_gap_count": 11,
        "j_a_target_parent_count": 131,
        "n_child_horizon_complete_by_horizon": {"300000": 0, "3600000": 0, "14400000": 0},
        "n_child_horizon_gap_by_horizon": {"300000": 281, "3600000": 281, "14400000": 281},
        "n_parent_horizon_complete_by_horizon": {"300000": 0, "3600000": 0, "14400000": 0},
        "n_parent_horizon_gap_by_horizon": {"300000": 131, "3600000": 131, "14400000": 131},
        "n_parent_total": 131,
        "n_parent_with_j_a_gap": 11,
        "parent_distribution_by_horizon": {
            h_str: {
                "max": None,
                "mean": None,
                "median": None,
                "min": None,
                "n_complete_parent": 0,
                "p10": None,
                "p25": None,
                "p50": None,
                "p75": None,
                "p90": None,
                "top_1_abs_return_contribution": "0",
                "top_1_parent_ids": [],
                "top_3_abs_return_contribution": "0",
                "top_3_parent_ids": [],
            }
            for h_str in ("300000", "3600000", "14400000")
        },
    }

    summary_obj = {
        "analysis_state": "launch_response_evidence_gap",
        "authority_flags": {
            "alpha_claim_allowed": False,
            "broker_routing_allowed": False,
            "capital_commitment_allowed": False,
            "discretionary_override_allowed": False,
            "execution_engine_allowed": False,
            "execution_feasibility_claim_allowed": False,
            "live_trading_allowed": False,
            "network_access_allowed": False,
            "paper_trading_allowed": False,
            "position_sizing_allowed": False,
            "realtime_telemetry_allowed": False,
            "trade_intent_allowed": False,
        },
        "authority_packet": {
            "approved_j_b_design": {
                "relative_path": LATEST_J_B_DOMAIN_DESIGN_PATH,
                "sha256": LATEST_J_B_DOMAIN_DESIGN_SHA256,
            },
            "audited_config": {
                "relative_path": PROFILE_AUDITED_CONFIG_RELATIVE_PATH,
                "sha256": PROFILE_AUDITED_CONFIG_SHA256,
            },
        },
        "child_horizon_rows": child_horizon_rows,
        "child_rows": child_rows,
        "coverage_counts": cov_counts,
        "decision": "stage1_5j_b_historical_aggtrades_launch_response_evidence_gap_published",
        "j_a_input": {
            "catalog_denominator_count": 335,
            "child_coverage_complete_count": 280,
            "child_coverage_gap_count": 1,
            "in_scope_usdt_child_count": 281,
            "j_a_core_path": "src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py",
            "j_a_core_sha256": "250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18",
            "j_a_manifest_sha256": "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf",
            "j_a_request_journal_sha256": "b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa",
            "j_a_review_sha256": "1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152",
            "j_a_root_relative_path": "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z",
            "j_a_run_id": "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z",
            "j_a_summary_sha256": "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b",
            "out_of_scope_child_count": 5,
            "parent_coverage_complete_count": 120,
            "parent_coverage_gap_count": 11,
            "resolved_parent_count": 125,
            "target_parent_count": 131,
        },
        "parent_horizon_rows": parent_horizon_rows,
        "research_status": {
            "alpha_evidence_status": "evidence_insufficient",
            "capital_survival_claim": "not_evaluated",
            "economic_edge_claim": "not_evaluated",
            "execution_feasibility_claim": "not_evaluated",
            "live_permission_claim": False,
            "phenomenon_claim": "not_evaluated",
            "research_mode": "exploratory_descriptive_only",
            "statistical_edge_claim": "not_evaluated",
        },
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
    }

    summary_bytes = (json.dumps(summary_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    (root / "summary.json").write_bytes(summary_bytes)

    review_bytes = b"# Stage 1.5J-B Review\n\nDescriptive exploratory reduction.\n"
    (root / "review_CN.md").write_bytes(review_bytes)

    manifest_obj = {
        "artifacts": [
            {
                "byte_count": len(review_bytes),
                "path": "review_CN.md",
                "sha256": hashlib.sha256(review_bytes).hexdigest(),
            },
            {
                "byte_count": len(summary_bytes),
                "path": "summary.json",
                "sha256": hashlib.sha256(summary_bytes).hexdigest(),
            },
        ],
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
    }
    manifest_bytes = (json.dumps(manifest_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    (root / "manifest.json").write_bytes(manifest_bytes)

    return summary_obj


# -----------------------------------------------------------------------------
# 9. Minimal Valid Fixture Validation v2 (rc=0)
# -----------------------------------------------------------------------------


def test_minimal_valid_fixture_v2(tmp_path: Path) -> None:
    """Assert minimal conformant v2 fixture passes verifier with rc=0."""
    fake_proj = tmp_path / "mock_project_v2"
    fake_proj.mkdir(parents=True, exist_ok=True)

    rel_root = f"{OUTPUT_PARENT}/stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = fake_proj / rel_root
    _build_minimal_valid_receipt_v2(target_root)

    script_dst = fake_proj / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py"
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJECT_ROOT / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py", script_dst)

    cwd = os.getcwd()
    try:
        os.chdir(fake_proj)
        rc = main(["--profile", PROFILE_ID_V2, "--artifact-root", rel_root])
        assert rc == 0
    finally:
        os.chdir(cwd)


# -----------------------------------------------------------------------------
# 10. Single-Mutation Negative Probe Matrix v2 (rc=1)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation_key,mutator",
    [
        ("v2_legacy_config_path", lambda root, s: _mutate_summary(root, s, lambda o: o["authority_packet"]["audited_config"].__setitem__("relative_path", "configs/base.py"))),
        ("v2_config_sha_mismatch", lambda root, s: _mutate_summary(root, s, lambda o: o["authority_packet"]["audited_config"].__setitem__("sha256", "0" * 64))),
        ("v2_missing_audited_config", lambda root, s: _mutate_summary(root, s, lambda o: o["authority_packet"].pop("audited_config", None))),
        ("v2_prior_domain_design", lambda root, s: _mutate_summary(root, s, lambda o: o["authority_packet"]["approved_j_b_design"].__setitem__("sha256", "f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25"))),
        ("v2_manifest_hash_tamper", lambda root, s: (root / "summary.json").write_bytes(b"tampered\n")),
        ("v2_forged_anchor_state", lambda root, s: _mutate_summary(root, s, lambda o: o["child_rows"][0].__setitem__("anchor_state", "forged_semantic_state"))),
        ("v2_child_rows_cardinality_tamper", lambda root, s: _mutate_summary(root, s, lambda o: o["child_rows"].pop())),
        ("v2_child_horizon_rows_cardinality_tamper", lambda root, s: _mutate_summary(root, s, lambda o: o["child_horizon_rows"].pop())),
        ("v2_parent_horizon_rows_cardinality_tamper", lambda root, s: _mutate_summary(root, s, lambda o: o["parent_horizon_rows"].pop())),
        ("v2_forged_child_horizon_state", lambda root, s: _mutate_summary(root, s, lambda o: o["child_horizon_rows"][0].__setitem__("child_horizon_state", "forged_state"))),
        ("v2_forged_parent_horizon_state", lambda root, s: _mutate_summary(root, s, lambda o: o["parent_horizon_rows"][0].__setitem__("parent_horizon_state", "forged_state"))),
        ("v2_coverage_counts_keys_tamper", lambda root, s: _mutate_summary(root, s, lambda o: o["coverage_counts"].pop("n_parent_total"))),
        ("v2_child_row_parent_state_contradiction", lambda root, s: _mutate_summary(root, s, lambda o: o["child_rows"][0].__setitem__("j_a_parent_state", "coverage_evidence_gap_archive"))),
        ("v2_gap_parent_wrong_anchor_state", lambda root, s: _mutate_summary(root, s, lambda o: o["child_rows"][120].__setitem__("anchor_state", "evidence_gap"))),
        ("v2_complete_parent_wrong_anchor_state", lambda root, s: _mutate_summary(root, s, lambda o: o["child_rows"][0].__setitem__("anchor_state", "anchor_unavailable_inherited_j_a_parent_gap"))),
    ],
)
def test_single_mutation_matrix_v2(tmp_path: Path, mutation_key: str, mutator) -> None:
    """Assert each single v2 mutation fails closed with rc=1."""
    fake_proj = tmp_path / f"mock_project_v2_{mutation_key}"
    fake_proj.mkdir(parents=True, exist_ok=True)

    rel_root = f"{OUTPUT_PARENT}/stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = fake_proj / rel_root
    summary_obj = _build_minimal_valid_receipt_v2(target_root)

    mutator(target_root, summary_obj)

    script_dst = fake_proj / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py"
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJECT_ROOT / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py", script_dst)

    cwd = os.getcwd()
    try:
        os.chdir(fake_proj)
        rc = main(["--profile", PROFILE_ID_V2, "--artifact-root", rel_root])
        assert rc == 1, f"Mutation '{mutation_key}' expected rc=1, got rc={rc}"
    finally:
        os.chdir(cwd)


# -----------------------------------------------------------------------------
# 11. Profile Sibling Rejection (v1 fixture rejected by v2 profile)
# -----------------------------------------------------------------------------


def test_v1_as_v2_rejection(tmp_path: Path) -> None:
    """Assert v1 receipt verified with v2 profile fails closed with rc=1."""
    fake_proj = tmp_path / "mock_project_v1_as_v2"
    fake_proj.mkdir(parents=True, exist_ok=True)

    rel_root = f"{OUTPUT_PARENT}/stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = fake_proj / rel_root
    _build_minimal_valid_receipt(target_root)  # v1 fixture

    script_dst = fake_proj / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py"
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJECT_ROOT / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py", script_dst)

    cwd = os.getcwd()
    try:
        os.chdir(fake_proj)
        rc = main(["--profile", PROFILE_ID_V2, "--artifact-root", rel_root])
        assert rc == 1
    finally:
        os.chdir(cwd)

