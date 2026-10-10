"""Tests for scripts/governance/verify_artifact_schema.py.

Strictly verifies:
1. CLI argument validation (rc=2)
2. AST strict standard-library isolation & zero forbidden imports/calls
3. stage1_5j_a_receipt_v1 minimal valid conformant fixture (rc=0)
4. Comprehensive single-mutation negative probe matrix (rc=1)
5. Immutable Section 1 negative reference root invocation (rc=1, exact diagnostic)
"""

import ast
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

# Target CLI entrypoint to verify
from scripts.governance.verify_artifact_schema import (
    main,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
NEGATIVE_REF_ROOT = (
    "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/"
    "stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z"
)


# -----------------------------------------------------------------------------
# 1. CLI Argument Validation (rc=2)
# -----------------------------------------------------------------------------


def test_cli_argument_validation(tmp_path, capsys):
    """Assert invalid CLI arguments and paths exit with rc=2."""
    script_copy = tmp_path / "scripts" / "governance" / "verify_artifact_schema.py"
    script_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        PROJECT_ROOT / "scripts" / "governance" / "verify_artifact_schema.py",
        script_copy,
    )

    # Missing arguments
    assert main([]) == 2

    # Unsupported profile
    assert (
        main(["--profile", "invalid_profile", "--artifact-root", "data/foo/bar"])
        == 2
    )

    # Absolute path
    assert (
        main(
            [
                "--profile",
                "stage1_5j_a_receipt_v1",
                "--artifact-root",
                str(tmp_path.resolve()),
            ]
        )
        == 2
    )

    # Parent directory traversal
    assert (
        main(
            [
                "--profile",
                "stage1_5j_a_receipt_v1",
                "--artifact-root",
                "../outside",
            ]
        )
        == 2
    )

    # Non-existent path
    assert (
        main(
            [
                "--profile",
                "stage1_5j_a_receipt_v1",
                "--artifact-root",
                "data/external_signal_shadow/nonexistent",
            ]
        )
        == 2
    )

    # Empty path component
    assert (
        main(
            [
                "--profile",
                "stage1_5j_a_receipt_v1",
                "--artifact-root",
                "data//external_signal_shadow",
            ]
        )
        == 2
    )

    # Dot path component
    assert (
        main(
            [
                "--profile",
                "stage1_5j_a_receipt_v1",
                "--artifact-root",
                ".",
            ]
        )
        == 2
    )


# -----------------------------------------------------------------------------
# 2. AST Strict Stdlib Isolation & Zero Dynamic/Subprocess Execution
# -----------------------------------------------------------------------------


def test_ast_strict_stdlib_isolation():
    """Verify scripts/governance/verify_artifact_schema.py uses stdlib only, no subprocess, no dynamic code."""
    script_path = (
        PROJECT_ROOT / "scripts" / "governance" / "verify_artifact_schema.py"
    )
    assert script_path.exists(), "Verifier script must exist"

    tree = ast.parse(script_path.read_text(encoding="utf-8"), filename=str(script_path))

    allowed_stdlib_modules = {
        "sys",
        "os",
        "json",
        "pathlib",
        "re",
        "argparse",
        "hashlib",
    }

    for node in ast.walk(tree):

        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                assert (
                    root_mod in allowed_stdlib_modules
                ), f"Forbidden import {alias.name}"
                assert not alias.name.startswith(
                    ("src", "configs", "tests")
                ), f"Target repo import {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_mod = node.module.split(".")[0]
                assert (
                    root_mod in allowed_stdlib_modules
                ), f"Forbidden import from {node.module}"
                assert not node.module.startswith(
                    ("src", "configs", "tests")
                ), f"Target repo import from {node.module}"

        # Check calls
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in {
                    "subprocess",
                    "system",
                    "popen",
                    "importlib",
                    "runpy",
                    "exec",
                    "eval",
                    "compile",
                    "__import__",
                }, f"Forbidden call {func.id}()"
            elif isinstance(func, ast.Attribute):
                assert func.attr not in {
                    "system",
                    "popen",
                    "spawn",
                }, f"Forbidden method call {func.attr}()"

        # Check no .git access in string literals
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert ".git" not in node.value, "Verifier source must not reference .git"


# -----------------------------------------------------------------------------
# Fixture Generator for stage1_5j_a_receipt_v1 Minimal Valid Receipt
# -----------------------------------------------------------------------------


def _canonical_json(obj: dict) -> bytes:
    """Encode object to canonical UTF-8 bytes without BOM, sorted keys, no trailing whitespace, newline at end."""
    return (
        json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")



def _build_minimal_valid_receipt(root_dir: Path, run_id: str, rel_root: str):
    """Build a minimal conformant sealed receipt in root_dir satisfying all contracts."""
    root_dir.mkdir(parents=True, exist_ok=True)

    # 1. Raw payload files
    raw_detail_dir = root_dir / "raw" / "article_details"
    raw_detail_dir.mkdir(parents=True, exist_ok=True)
    detail_file = raw_detail_dir / f"{'a' * 32}.json"
    detail_bytes = b'{"code":"000000","data":{"articles":[{"id":1}]}}\n'
    detail_file.write_bytes(detail_bytes)
    detail_sha = hashlib.sha256(detail_bytes).hexdigest()

    raw_archive_dir = root_dir / "raw" / "archive" / "BTCUSDT"
    raw_archive_dir.mkdir(parents=True, exist_ok=True)
    zip_file = raw_archive_dir / "BTCUSDT-aggTrades-2026-10-10.zip"
    zip_bytes = b"PK\x05\x06" + b"\x00" * 18  # minimal empty zip
    zip_file.write_bytes(zip_bytes)
    zip_sha = hashlib.sha256(zip_bytes).hexdigest()

    checksum_file = raw_archive_dir / "BTCUSDT-aggTrades-2026-10-10.zip.CHECKSUM"
    checksum_bytes = f"{zip_sha}  BTCUSDT-aggTrades-2026-10-10.zip\n".encode("utf-8")
    checksum_file.write_bytes(checksum_bytes)
    checksum_sha = hashlib.sha256(checksum_bytes).hexdigest()

    # 2. Review markdown
    review_file = root_dir / "review_CN.md"
    review_bytes = b"# Stage 1.5J-A Coverage Inventory Review\n"
    review_file.write_bytes(review_bytes)
    review_sha = hashlib.sha256(review_bytes).hexdigest()

    # 3. Request journal
    journal_file = root_dir / "request_journal.jsonl"
    journal_records = [
        # Request 1: Detail
        {
            "event": "request_intent",
            "parent_article_id": "a" * 32,
            "request_id": 1,
            "request_kind": "detail",
            "request_state": "admitted_pending",
            "symbol": None,
            "url": "https://example.com/detail",
            "utc_date": None,
        },
        {
            "event": "request_terminal",
            "http_status": 200,
            "request_id": 1,
            "request_state": "response_persisted",
            "response_bytes": len(detail_bytes),
            "response_relative_path": f"{rel_root}/raw/article_details/{'a' * 32}.json",
            "response_sha256": detail_sha,
            "transport_error": None,
        },
        # Request 2: Archive zip
        {
            "event": "request_intent",
            "parent_article_id": "a" * 32,
            "request_id": 2,
            "request_kind": "archive",
            "request_state": "admitted_pending",
            "symbol": "BTCUSDT",
            "url": "https://example.com/archive.zip",
            "utc_date": "2026-10-10",
        },
        {
            "event": "request_terminal",
            "http_status": 200,
            "request_id": 2,
            "request_state": "response_persisted",
            "response_bytes": len(zip_bytes),
            "response_relative_path": f"{rel_root}/raw/archive/BTCUSDT/BTCUSDT-aggTrades-2026-10-10.zip",
            "response_sha256": zip_sha,
            "transport_error": None,
        },
        # Request 3: Archive checksum
        {
            "event": "request_intent",
            "parent_article_id": "a" * 32,
            "request_id": 3,
            "request_kind": "checksum",
            "request_state": "admitted_pending",
            "symbol": "BTCUSDT",
            "url": "https://example.com/archive.zip.CHECKSUM",
            "utc_date": "2026-10-10",
        },
        {
            "event": "request_terminal",
            "http_status": 200,
            "request_id": 3,
            "request_state": "response_persisted",
            "response_bytes": len(checksum_bytes),
            "response_relative_path": f"{rel_root}/raw/archive/BTCUSDT/BTCUSDT-aggTrades-2026-10-10.zip.CHECKSUM",
            "response_sha256": checksum_sha,
            "transport_error": None,
        },
    ]
    journal_bytes = (
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in journal_records)
    ).encode("utf-8")
    journal_file.write_bytes(journal_bytes)
    journal_sha = hashlib.sha256(journal_bytes).hexdigest()

    # 4. Summary JSON
    summary_obj = {
        "analysis_state": "coverage_inventory_complete",
        "archive_package_records": [
            {
                "checksum_request_id": 3,
                "child_state": "archive_verified_with_post_launch_rows",
                "first_post_launch_trade_delay_ms": 100,
                "first_post_launch_trade_time_ms": 1700000000100,
                "last_post_launch_trade_time_ms": 1700000000200,
                "logical_archive_identity": {
                    "market": "futures_um",
                    "metric": "aggTrades",
                    "parent_article_id": "a" * 32,
                    "symbol": "BTCUSDT",
                    "utc_date": "2026-10-10",
                },
                "parent_article_id": "a" * 32,
                "post_launch_row_count": 10,
                "symbol": "BTCUSDT",
                "utc_date": "2026-10-10",
                "zip_request_id": 2,
            }
        ],
        "authority_flags": {
            "alpha_claim_allowed": False,
            "alpha_interpretation_allowed": False,
            "commit_allowed": False,
            "deployment_allowed": False,
            "execution_allowed": False,
            "live_trading_allowed": False,
            "network_allowed_after_run": False,
            "paper_trading_allowed": False,
            "pnl_calculation_allowed": False,
            "price_response_calculation_allowed": False,
            "receipt_generation_allowed_without_authorization": False,
            "replay_allowed": False,
            "signal_generation_allowed": False,
        },
        "authority_packet": {
            "approved_design": {
                "relative_path": "docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md",
                "sha256": "b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a",
            },
            "approved_plan": {
                "relative_path": "docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan-r1_CN.md",
                "sha256": "b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82",
            },
            "audited_cli": {
                "relative_path": "scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py",
                "sha256": "ed4d1d9f8d4efe916186a4e64c0cb94188115e67d8251679811d2a02c133c417",
            },
            "audited_config": {
                "relative_path": "configs/base.py",
                "sha256": "473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc",
            },
            "audited_core": {
                "relative_path": "src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py",
                "sha256": "250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18",
            },
            "frozen_parser": {
                "relative_path": "src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py",
                "sha256": "7e0e696647acf158facbdd8d3d39351bbc68c33b039871f26f4a38bc75ad56e5",
            },
            "network_authorization": {
                "authorized_run_id": run_id,
                "network_profile_id": "stage1_5j_a_public_archive_inventory_v1",
                "relative_path": ".git/plan-execution/stage1_5j_a/b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82/network_authorization.txt",
                "sha256": "1" * 64,
            },

        },
        "catalog_denominator_records": [
            {
                "candidate_status": "resolved_target_parent",
                "detail_request_id": 1,
                "release_date_ms": 1700000000000,
                "source_article_id": "a" * 32,
                "title": "Binance Will List BTC",
            }
        ],
        "catalog_scan": {
            "page_limit_per_pass": 10,
            "scan_a_page_count": 1,
            "scan_b_page_count": 1,
            "sentinel_page_no": 1,
            "stable_tuple_sha256": "0" * 64,
        },
        "coverage_inventory": {
            "catalog_denominator_count": 1,
            "child_coverage_complete_count": 1,
            "child_coverage_gap_count": 0,
            "in_scope_usdt_child_count": 1,
            "out_of_scope_child_count": 0,
            "parent_coverage_complete_count": 1,
            "parent_coverage_gap_count": 0,
            "resolved_parent_count": 1,
            "target_parent_count": 1,
        },
        "decision": "stage1_5j_a_historical_archive_coverage_inventory_published",
        "parent_records": [
            {
                "children": [
                    {
                        "child_scope": "in_scope_usdt",
                        "symbol": "BTCUSDT",
                        "symbol_launch_time_ms": 1700000000000,
                    }
                ],
                "detail_payload_sha256": "2" * 64,
                "detail_request_id": 1,
                "detail_status": "validated_target_detail",
                "parent_state": "coverage_complete",
                "source_article_id": "a" * 32,
            }
        ],
        "request_records": [
            {
                "http_status_or_transport_error": 200,
                "request_id": 1,
                "request_kind": "detail",
                "request_state": "response_persisted",
                "response_bytes": len(detail_bytes),
                "response_relative_path": f"{rel_root}/raw/article_details/{'a' * 32}.json",
                "response_sha256": detail_sha,
                "url": "https://example.com/detail",
            },
            {
                "http_status_or_transport_error": 200,
                "request_id": 2,
                "request_kind": "archive",
                "request_state": "response_persisted",
                "response_bytes": len(zip_bytes),
                "response_relative_path": f"{rel_root}/raw/archive/BTCUSDT/BTCUSDT-aggTrades-2026-10-10.zip",
                "response_sha256": zip_sha,
                "url": "https://example.com/archive.zip",
            },
            {
                "http_status_or_transport_error": 200,
                "request_id": 3,
                "request_kind": "checksum",
                "request_state": "response_persisted",
                "response_bytes": len(checksum_bytes),
                "response_relative_path": f"{rel_root}/raw/archive/BTCUSDT/BTCUSDT-aggTrades-2026-10-10.zip.CHECKSUM",
                "response_sha256": checksum_sha,
                "url": "https://example.com/archive.zip.CHECKSUM",
            },
        ],
        "run_id": run_id,
        "schema_version": "stage1_5j_a_historical_archive_coverage_inventory_v1",
        "universe_window": {
            "end_exclusive_ms": 1700086400000,
            "start_ms": 1700000000000,
        },
    }
    summary_file = root_dir / "summary.json"
    summary_bytes = _canonical_json(summary_obj)
    summary_file.write_bytes(summary_bytes)
    summary_sha = hashlib.sha256(summary_bytes).hexdigest()

    # 5. Manifest JSON
    artifacts = [
        {
            "byte_count": len(zip_bytes),
            "relative_path": "raw/archive/BTCUSDT/BTCUSDT-aggTrades-2026-10-10.zip",
            "sha256": zip_sha,
        },
        {
            "byte_count": len(checksum_bytes),
            "relative_path": "raw/archive/BTCUSDT/BTCUSDT-aggTrades-2026-10-10.zip.CHECKSUM",
            "sha256": checksum_sha,
        },
        {
            "byte_count": len(detail_bytes),
            "relative_path": f"raw/article_details/{'a' * 32}.json",
            "sha256": detail_sha,
        },
        {
            "byte_count": len(journal_bytes),
            "relative_path": "request_journal.jsonl",
            "sha256": journal_sha,
        },
        {
            "byte_count": len(review_bytes),
            "relative_path": "review_CN.md",
            "sha256": review_sha,
        },
        {
            "byte_count": len(summary_bytes),
            "relative_path": "summary.json",
            "sha256": summary_sha,
        },
    ]
    # Ensure artifacts are sorted by relative_path
    artifacts.sort(key=lambda x: x["relative_path"])

    manifest_obj = {
        "artifacts": artifacts,
        "root_relative_path": rel_root,
        "run_id": run_id,
        "schema_version": "stage1_5j_a_historical_archive_coverage_inventory_manifest_v1",
    }
    manifest_file = root_dir / "manifest.json"
    manifest_bytes = _canonical_json(manifest_obj)
    manifest_file.write_bytes(manifest_bytes)

    return root_dir


# -----------------------------------------------------------------------------
# 3. Minimal Valid Fixture Test (rc=0)
# -----------------------------------------------------------------------------


def test_stage1_5j_a_receipt_v1_minimal_valid_fixture(tmp_path):
    """Verify minimal valid conformant receipt returns rc=0."""
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261010T120000Z"
    rel_root = f"data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/{run_id}"

    # Setup mock project root
    mock_proj = tmp_path
    script_copy = mock_proj / "scripts" / "governance" / "verify_artifact_schema.py"
    script_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        PROJECT_ROOT / "scripts" / "governance" / "verify_artifact_schema.py",
        script_copy,
    )

    receipt_dir = mock_proj / Path(rel_root)
    _build_minimal_valid_receipt(receipt_dir, run_id, rel_root)

    # Execute main from script_copy location
    # Note: verifier derives project root from Path(__file__).resolve().parents[2]
    import importlib.util

    spec = importlib.util.spec_from_file_location("verifier", str(script_copy))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rc = mod.main(["--profile", "stage1_5j_a_receipt_v1", "--artifact-root", rel_root])
    assert rc == 0


# -----------------------------------------------------------------------------
# 4. Single Mutation Negatives (rc=1)
# -----------------------------------------------------------------------------


MUTATION_CASES = [
    # (mutation_id, contract_class, expected_diag_keyword)
    # 1. Canonical JSON
    ("manifest_bom", "canonical_json", "BOM"),
    ("manifest_missing_newline", "canonical_json", "terminal newline"),
    ("manifest_unsorted_keys", "canonical_json", "sorted keys"),
    ("manifest_noncanonical_separators", "canonical_json", "separators"),
    ("summary_bom", "canonical_json", "BOM"),
    ("summary_missing_newline", "canonical_json", "terminal newline"),
    ("summary_unsorted_keys", "canonical_json", "sorted keys"),
    ("summary_noncanonical_separators", "canonical_json", "separators"),
    # 2. Manifest Identity and Entries
    ("manifest_schema_mismatch", "manifest_identity", "schema_version"),
    ("manifest_run_mismatch", "manifest_identity", "run_id"),
    ("manifest_root_mismatch", "manifest_identity", "root_relative_path"),
    ("manifest_unknown_key", "manifest_identity", "unexpected"),
    ("manifest_artifact_unknown_key", "manifest_identity", "unexpected"),
    ("manifest_bool_byte_count", "manifest_identity", "byte_count"),
    ("manifest_negative_byte_count", "manifest_identity", "byte_count"),
    ("manifest_invalid_sha", "manifest_identity", "sha256"),
    ("manifest_duplicate_entry", "manifest_identity", "duplicate"),
    ("manifest_unsorted_entry", "manifest_identity", "unsorted"),
    ("manifest_traversal_alias", "manifest_identity", "relative path"),
    ("manifest_missing_file", "manifest_identity", "missing"),
    ("manifest_unapproved_raw_filename", "manifest_identity", "pattern"),
    ("extra_unlisted_file", "manifest_identity", "unlisted"),
    ("unexpected_directory", "manifest_identity", "unimplied"),
    ("unimplied_archive_symbol_directory", "manifest_identity", "unimplied"),
    ("file_sha_mismatch", "manifest_identity", "sha256 mismatch"),
    ("file_byte_count_mismatch", "manifest_identity", "byte count mismatch"),
    # 3. Tree Traversal
    ("root_symlink", "tree_traversal", "symlink"),
    ("ancestor_symlink", "tree_traversal", "symlink"),
    ("descendant_directory_symlink", "tree_traversal", "symlink"),
    ("descendant_file_symlink", "tree_traversal", "symlink"),
    # 4. Summary Envelope
    ("summary_missing_key", "summary_envelope", "missing"),
    ("summary_unknown_key", "summary_envelope", "unexpected"),
    ("summary_schema_mismatch", "summary_envelope", "schema_version"),
    ("summary_run_mismatch", "summary_envelope", "run_id"),
    # 4a. All 13 Authority Flags Independently True
    (
        "summary_authority_flag_alpha_claim_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_alpha_interpretation_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_commit_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_deployment_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_execution_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_live_trading_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_network_allowed_after_run_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_paper_trading_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_pnl_calculation_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_price_response_calculation_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_receipt_generation_allowed_without_authorization_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_replay_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    (
        "summary_authority_flag_signal_generation_allowed_true",
        "summary_envelope",
        "authority_flags",
    ),
    # 4b. Summary Envelope Objects & Authority Packet
    ("universe_window_invalid", "summary_envelope", "universe_window"),
    ("catalog_scan_invalid", "summary_envelope", "catalog_scan"),
    ("authority_packet_invalid", "summary_envelope", "authority_packet"),
    (
        "authority_packet_approved_design_path_mismatch",
        "summary_envelope",
        "approved_design",
    ),
    (
        "authority_packet_approved_design_sha_mismatch",
        "summary_envelope",
        "approved_design",
    ),
    (
        "authority_packet_audited_core_path_mismatch",
        "summary_envelope",
        "audited_core",
    ),
    (
        "authority_packet_network_profile_id_mismatch",
        "summary_envelope",
        "network_profile_id",
    ),
    # 5. Denominator and Parent Rows
    ("denominator_ordering_fault", "denominator_and_parent", "sort"),
    (
        "denominator_detail_id_mismatch",
        "denominator_and_parent",
        "detail_request_id",
    ),
    ("parent_ordering_fault", "denominator_and_parent", "sort"),
    (
        "parent_detail_status_incoherent",
        "denominator_and_parent",
        "detail_nonpersisted",
    ),
    ("child_unknown_key", "denominator_and_parent", "child"),
    (
        "nonvalidated_parent_nonempty_children",
        "denominator_and_parent",
        "children",
    ),
    # 6. Archive Rows
    ("archive_ordering_fault", "archive_rows", "sorted"),
    (
        "archive_post_launch_row_count_non_null_for_nonpersisted",
        "archive_rows",
        "post_launch_row_count",
    ),
    (
        "archive_first_post_launch_trade_delay_ms_non_null_for_nonpersisted",
        "archive_rows",
        "trade_delay",
    ),
    (
        "archive_first_post_launch_trade_time_ms_non_null_for_nonpersisted",
        "archive_rows",
        "trade_time",
    ),
    (
        "archive_last_post_launch_trade_time_ms_non_null_for_nonpersisted",
        "archive_rows",
        "trade_time",
    ),
    (
        "logical_archive_identity_mismatch",
        "archive_rows",
        "logical_archive_identity",
    ),
    # 7. Coverage and Decision
    ("coverage_inventory_bool", "coverage_and_decision", "coverage_inventory"),
    (
        "coverage_inventory_negative",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    (
        "coverage_inventory_catalog_denominator_count_non_integer",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    (
        "coverage_inventory_child_coverage_complete_count_non_integer",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    (
        "coverage_inventory_child_coverage_gap_count_non_integer",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    (
        "coverage_inventory_in_scope_usdt_child_count_non_integer",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    (
        "coverage_inventory_out_of_scope_child_count_non_integer",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    (
        "coverage_inventory_parent_coverage_complete_count_non_integer",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    (
        "coverage_inventory_parent_coverage_gap_count_non_integer",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    (
        "coverage_inventory_resolved_parent_count_non_integer",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    (
        "coverage_inventory_target_parent_count_non_integer",
        "coverage_and_decision",
        "coverage_inventory",
    ),
    ("invalid_decision_pair", "coverage_and_decision", "decision"),
    # 8. Journal State Machine
    ("journal_intent_unknown_key", "journal_state_machine", "unexpected"),
    ("journal_created_at_utc", "journal_state_machine", "created_at_utc"),
    ("journal_context_invalid_catalog", "journal_state_machine", "catalog"),
    ("journal_context_invalid_detail", "journal_state_machine", "detail"),
    ("journal_context_invalid_archive", "journal_state_machine", "archive"),
    ("journal_context_invalid_checksum", "journal_state_machine", "checksum"),
    ("journal_duplicate_request_id", "journal_state_machine", "duplicate"),
    (
        "journal_non_contiguous_request_id",
        "journal_state_machine",
        "non-contiguous",
    ),
    ("journal_nonpositive_request_id", "journal_state_machine", "request_id"),
    ("journal_terminal_before_intent", "journal_state_machine", "before intent"),
    (
        "journal_duplicate_terminal",
        "journal_state_machine",
        "duplicate terminal",
    ),
    ("journal_dangling_intent", "journal_state_machine", "dangling"),
    (
        "journal_incoherent_terminal_fields",
        "journal_state_machine",
        "fields mismatch",
    ),
    (
        "journal_terminal_404_with_wrong_state",
        "journal_state_machine",
        "response_persisted",
    ),
    (
        "journal_terminal_200_with_rejected_state",
        "journal_state_machine",
        "fields mismatch",
    ),
    # 9. Completed Projection (all 8 projection fields)
    (
        "projection_request_id_mismatch",
        "completed_projection",
        "projection mismatch",
    ),
    (
        "projection_request_kind_mismatch",
        "completed_projection",
        "projection mismatch",
    ),
    (
        "projection_url_mismatch",
        "completed_projection",
        "projection mismatch",
    ),
    (
        "projection_request_state_mismatch",
        "completed_projection",
        "projection mismatch",
    ),
    (
        "projection_http_status_or_transport_error_mismatch",
        "completed_projection",
        "projection mismatch",
    ),
    (
        "projection_response_bytes_mismatch",
        "completed_projection",
        "projection mismatch",
    ),
    (
        "projection_response_relative_path_mismatch",
        "completed_projection",
        "projection mismatch",
    ),
    (
        "projection_response_sha256_mismatch",
        "completed_projection",
        "projection mismatch",
    ),
]


@pytest.mark.parametrize("mutation_id,contract_class,expected_keyword", MUTATION_CASES)
def test_stage1_5j_a_receipt_v1_single_mutation_negatives(
    tmp_path, capsys, mutation_id, contract_class, expected_keyword
):
    """Test that applying a single semantic mutation results in rc=1 and diagnostic."""
    run_id = "stage1_5j_a_historical_archive_coverage_inventory_20261010T120000Z"

    rel_root = f"data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/{run_id}"

    mock_proj = tmp_path
    script_copy = mock_proj / "scripts" / "governance" / "verify_artifact_schema.py"
    script_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        PROJECT_ROOT / "scripts" / "governance" / "verify_artifact_schema.py",
        script_copy,
    )

    receipt_dir = mock_proj / Path(rel_root)
    _build_minimal_valid_receipt(receipt_dir, run_id, rel_root)

    # Apply mutation
    _apply_mutation(receipt_dir, rel_root, run_id, mutation_id)

    import importlib.util

    spec = importlib.util.spec_from_file_location("verifier", str(script_copy))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rc = mod.main(["--profile", "stage1_5j_a_receipt_v1", "--artifact-root", rel_root])
    assert rc == 1, f"Mutation {mutation_id} expected rc=1, got {rc}"
    captured = capsys.readouterr()
    diag = captured.err + captured.out
    assert expected_keyword.lower() in diag.lower(), (
        f"Mutation {mutation_id} expected diagnostic containing '{expected_keyword}', got: {diag}"
    )


def _apply_mutation(receipt_dir: Path, rel_root: str, run_id: str, mutation_id: str):
    """Mutate exactly one aspect of the receipt."""
    manifest_path = receipt_dir / "manifest.json"
    summary_path = receipt_dir / "summary.json"
    journal_path = receipt_dir / "request_journal.jsonl"

    if mutation_id == "manifest_bom":
        manifest_path.write_bytes(b"\xef\xbb\xbf" + manifest_path.read_bytes())
    elif mutation_id == "manifest_missing_newline":
        manifest_path.write_bytes(manifest_path.read_bytes().rstrip(b"\n"))
    elif mutation_id == "manifest_unsorted_keys":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        reversed_obj = {k: obj[k] for k in reversed(list(obj.keys()))}
        manifest_path.write_text(json.dumps(reversed_obj, sort_keys=False, separators=(",", ":")) + "\n", encoding="utf-8")
    elif mutation_id == "manifest_noncanonical_separators":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_path.write_text(
            json.dumps(obj, sort_keys=True, separators=(", ", ": ")) + "\n",
            encoding="utf-8",
        )
    elif mutation_id == "summary_bom":
        summary_path.write_bytes(b"\xef\xbb\xbf" + summary_path.read_bytes())
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "summary_missing_newline":
        summary_path.write_bytes(summary_path.read_bytes().rstrip(b"\n"))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "summary_unsorted_keys":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        reversed_obj = {k: obj[k] for k in reversed(list(obj.keys()))}
        summary_path.write_text(json.dumps(reversed_obj, sort_keys=False, separators=(",", ":")) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "summary_noncanonical_separators":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        summary_path.write_text(
            json.dumps(obj, sort_keys=True, separators=(", ", ": ")) + "\n",
            encoding="utf-8",
        )
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "manifest_schema_mismatch":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["schema_version"] = "wrong_version"
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_run_mismatch":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["run_id"] = "invalid_run_id_regex"
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_root_mismatch":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["root_relative_path"] = "data/other/root"
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_unknown_key":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["extra_key"] = "forbidden"
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_artifact_unknown_key":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"][0]["extra"] = True
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_bool_byte_count":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"][0]["byte_count"] = True
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_negative_byte_count":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"][0]["byte_count"] = -1
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_invalid_sha":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"][0]["sha256"] = "invalid_not_hex"
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_duplicate_entry":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"].append(dict(obj["artifacts"][0]))
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_unsorted_entry":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"].reverse()
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_traversal_alias":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"][0]["relative_path"] = "./" + obj["artifacts"][0]["relative_path"]
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "manifest_missing_file":
        (receipt_dir / "review_CN.md").unlink()
    elif mutation_id == "manifest_unapproved_raw_filename":
        forbidden_file = receipt_dir / "raw" / "catalog_scan_a" / "not-a-page.txt"
        forbidden_file.parent.mkdir(parents=True, exist_ok=True)
        forbidden_file.write_text("not a page", encoding="utf-8")
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"].append(
            {
                "byte_count": len("not a page"),
                "relative_path": "raw/catalog_scan_a/not-a-page.txt",
                "sha256": hashlib.sha256(b"not a page").hexdigest(),
            }
        )
        obj["artifacts"].sort(key=lambda x: x["relative_path"])
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "extra_unlisted_file":
        (receipt_dir / "extra_file.txt").write_text("extra", encoding="utf-8")
    elif mutation_id == "unexpected_directory":
        (receipt_dir / "unexpected_dir").mkdir()
    elif mutation_id == "unimplied_archive_symbol_directory":
        empty_dir = receipt_dir / "raw" / "archive" / "ETHUSDT"
        empty_dir.mkdir(parents=True, exist_ok=True)
    elif mutation_id == "file_sha_mismatch":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"][0]["sha256"] = "0" * 64
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "file_byte_count_mismatch":
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
        obj["artifacts"][0]["byte_count"] += 1
        manifest_path.write_bytes(_canonical_json(obj))
    elif mutation_id == "root_symlink":
        real_target = receipt_dir.parent / f"{receipt_dir.name}_real"
        receipt_dir.rename(real_target)
        os.symlink(real_target.name, receipt_dir)
    elif mutation_id == "ancestor_symlink":
        ancestor = receipt_dir.parent
        ancestor_real = ancestor.parent / f"{ancestor.name}_real"
        ancestor.rename(ancestor_real)
        os.symlink(ancestor_real.name, ancestor)
    elif mutation_id == "descendant_directory_symlink":
        target = receipt_dir / "raw" / "article_details"
        real_target = receipt_dir / "raw" / "article_details_real"
        target.rename(real_target)
        os.symlink("article_details_real", target)
    elif mutation_id == "descendant_file_symlink":
        target = receipt_dir / "review_CN.md"
        target.unlink()
        os.symlink("summary.json", str(target))
    elif mutation_id == "summary_missing_key":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        del obj["analysis_state"]
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "summary_unknown_key":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["forbidden_extra"] = 123
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "summary_schema_mismatch":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["schema_version"] = "wrong"
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "summary_run_mismatch":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["run_id"] = "stage1_5j_a_historical_archive_coverage_inventory_20261010T999999Z"
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id.startswith("summary_authority_flag_") and mutation_id.endswith("_true"):
        flag = mutation_id[len("summary_authority_flag_") : -len("_true")]
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["authority_flags"][flag] = True
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "universe_window_invalid":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["universe_window"]["start_ms"] = True  # bool forbidden
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "catalog_scan_invalid":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        del obj["catalog_scan"]["stable_tuple_sha256"]
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "authority_packet_invalid":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        del obj["authority_packet"]["approved_design"]
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "authority_packet_approved_design_path_mismatch":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["authority_packet"]["approved_design"]["relative_path"] = "docs/designs/unapproved_design.md"
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "authority_packet_approved_design_sha_mismatch":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["authority_packet"]["approved_design"]["sha256"] = "f" * 64
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "authority_packet_audited_core_path_mismatch":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["authority_packet"]["audited_core"]["relative_path"] = "src/other_core.py"
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "authority_packet_network_profile_id_mismatch":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["authority_packet"]["network_authorization"]["network_profile_id"] = "wrong_network_profile"
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "denominator_ordering_fault":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["catalog_denominator_records"].append(
            {
                "candidate_status": "not_target_event_type",
                "detail_request_id": None,
                "release_date_ms": 1600000000000,  # earlier release date -> unsorted
                "source_article_id": "0" * 32,
                "title": "Old Article",
            }
        )
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "denominator_detail_id_mismatch":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["catalog_denominator_records"][0]["detail_request_id"] = None
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "parent_ordering_fault":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["parent_records"].append(
            {
                "children": [],
                "detail_payload_sha256": None,
                "detail_request_id": 2,
                "detail_status": "detail_nonpersisted",
                "parent_state": "coverage_evidence_gap_detail",
                "source_article_id": "0" * 32,
            }
        )
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "parent_detail_status_incoherent":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["parent_records"][0]["detail_status"] = "detail_nonpersisted"
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "child_unknown_key":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["parent_records"][0]["children"][0]["extra"] = True
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "nonvalidated_parent_nonempty_children":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["parent_records"][0]["detail_status"] = "detail_parser_unresolved"
        obj["parent_records"][0]["detail_payload_sha256"] = "3" * 64
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "archive_ordering_fault":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        rec = dict(obj["archive_package_records"][0])
        rec["parent_article_id"] = "0" * 32
        rec["logical_archive_identity"] = dict(rec["logical_archive_identity"])
        rec["logical_archive_identity"]["parent_article_id"] = "0" * 32
        obj["archive_package_records"].append(rec)
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "archive_post_launch_row_count_non_null_for_nonpersisted":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        rec = obj["archive_package_records"][0]
        rec["child_state"] = "archive_request_nonpersisted"
        rec["first_post_launch_trade_delay_ms"] = None
        rec["first_post_launch_trade_time_ms"] = None
        rec["last_post_launch_trade_time_ms"] = None
        rec["post_launch_row_count"] = 0
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "archive_first_post_launch_trade_delay_ms_non_null_for_nonpersisted":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        rec = obj["archive_package_records"][0]
        rec["child_state"] = "archive_request_nonpersisted"
        rec["post_launch_row_count"] = None
        rec["first_post_launch_trade_time_ms"] = None
        rec["last_post_launch_trade_time_ms"] = None
        rec["first_post_launch_trade_delay_ms"] = 100
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "archive_first_post_launch_trade_time_ms_non_null_for_nonpersisted":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        rec = obj["archive_package_records"][0]
        rec["child_state"] = "archive_request_nonpersisted"
        rec["post_launch_row_count"] = None
        rec["first_post_launch_trade_delay_ms"] = None
        rec["last_post_launch_trade_time_ms"] = None
        rec["first_post_launch_trade_time_ms"] = 1700000000000
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "archive_last_post_launch_trade_time_ms_non_null_for_nonpersisted":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        rec = obj["archive_package_records"][0]
        rec["child_state"] = "archive_request_nonpersisted"
        rec["post_launch_row_count"] = None
        rec["first_post_launch_trade_delay_ms"] = None
        rec["first_post_launch_trade_time_ms"] = None
        rec["last_post_launch_trade_time_ms"] = 1700000000000
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "logical_archive_identity_mismatch":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["archive_package_records"][0]["logical_archive_identity"]["symbol"] = "ETHUSDT"
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "coverage_inventory_bool":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["coverage_inventory"]["target_parent_count"] = True
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "coverage_inventory_negative":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["coverage_inventory"]["target_parent_count"] = -1
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id.startswith("coverage_inventory_") and mutation_id.endswith("_non_integer"):
        field = mutation_id[len("coverage_inventory_") : -len("_non_integer")]
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["coverage_inventory"][field] = 1.5
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "invalid_decision_pair":
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        obj["decision"] = "invalid_decision"
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)
    elif mutation_id == "journal_intent_unknown_key":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["extra_key"] = "forbidden"
        lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_created_at_utc":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["created_at_utc"] = "2026-10-10T12:00:00Z"
        lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_context_invalid_catalog":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["request_kind"] = "catalog"
        first["parent_article_id"] = "a" * 32
        lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_context_invalid_detail":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["request_kind"] = "detail"
        first["parent_article_id"] = "invalid_not_hex_32"
        lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_context_invalid_archive":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        intent = json.loads(lines[2])
        intent["symbol"] = "lower_case_sym"
        lines[2] = json.dumps(intent, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_context_invalid_checksum":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            rec = json.loads(line)
            if rec.get("event") == "request_intent" and rec.get("request_kind") == "checksum":
                rec["symbol"] = None
                lines[i] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
                break
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_duplicate_request_id":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        lines.append(lines[0])
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_non_contiguous_request_id":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        intent = json.loads(lines[2])
        intent["request_id"] = 10
        lines[2] = json.dumps(intent, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_nonpositive_request_id":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        intent = json.loads(lines[0])
        intent["request_id"] = 0
        lines[0] = json.dumps(intent, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_terminal_before_intent":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        lines[0], lines[1] = lines[1], lines[0]
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_duplicate_terminal":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        lines.append(lines[1])
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_dangling_intent":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        lines.pop()
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_incoherent_terminal_fields":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        term = json.loads(lines[1])
        term["request_state"] = "http_not_found"
        lines[1] = json.dumps(term, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_terminal_404_with_wrong_state":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        term = json.loads(lines[1])
        term["http_status"] = 404
        term["request_state"] = "response_persisted"
        lines[1] = json.dumps(term, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id == "journal_terminal_200_with_rejected_state":
        lines = journal_path.read_text(encoding="utf-8").splitlines()
        term = json.loads(lines[1])
        term["http_status"] = 200
        term["request_state"] = "response_rejected"
        lines[1] = json.dumps(term, sort_keys=True, separators=(",", ":"))
        journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _update_manifest_entry(manifest_path, "request_journal.jsonl", journal_path)
    elif mutation_id.startswith("projection_") and mutation_id.endswith("_mismatch"):
        field = mutation_id[len("projection_") : -len("_mismatch")]
        obj = json.loads(summary_path.read_text(encoding="utf-8"))
        rec = obj["request_records"][0]
        if field == "request_id":
            rec["request_id"] = 999
        elif field == "request_kind":
            rec["request_kind"] = "other_kind"
        elif field == "url":
            rec["url"] = "https://example.com/other"
        elif field == "request_state":
            rec["request_state"] = "http_not_found"
        elif field == "http_status_or_transport_error":
            rec["http_status_or_transport_error"] = 500
        elif field == "response_bytes":
            rec["response_bytes"] = 99999
        elif field == "response_relative_path":
            rec["response_relative_path"] = "data/other.bin"
        elif field == "response_sha256":
            rec["response_sha256"] = "f" * 64
        summary_path.write_bytes(_canonical_json(obj))
        _update_manifest_entry(manifest_path, "summary.json", summary_path)


def _update_manifest_entry(manifest_path: Path, rel_path: str, file_path: Path):
    """Regenerate only the derived manifest entry / canonical manifest needed for witness preparation."""
    manifest_obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    content = file_path.read_bytes()
    for art in manifest_obj["artifacts"]:
        if art["relative_path"] == rel_path:
            art["byte_count"] = len(content)
            art["sha256"] = hashlib.sha256(content).hexdigest()
            break
    manifest_path.write_bytes(_canonical_json(manifest_obj))


# -----------------------------------------------------------------------------
# 5. Immutable Section 1 Negative Reference Root
# -----------------------------------------------------------------------------


def test_immutable_section_1_negative_reference_root(capsys):
    """Verify that calling the verifier on real negative reference root fails closed with rc=1 and exact diagnostic."""
    root_path = PROJECT_ROOT / Path(NEGATIVE_REF_ROOT)
    assert root_path.exists(), f"Negative reference root must exist: {root_path}"

    rc = main(
        [
            "--profile",
            "stage1_5j_a_receipt_v1",
            "--artifact-root",
            NEGATIVE_REF_ROOT,
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1, f"Expected rc=1, got {rc}"
    diag = captured.err + captured.out
    assert "post_launch_row_count" in diag
    assert "null" in diag
    assert "0" in diag
