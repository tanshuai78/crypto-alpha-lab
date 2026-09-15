"""Tests for Stage 1.6F offline runner script and runner composition fail-closed matrix."""

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.external_signal_shadow import run_stage1_6f_historical_mechanism_diagnostic as runner
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    MarketEvidenceInvalidError,
    SourceInvalidError,
)
from tests.research.external_signal_shadow.stage1_6f_historical_diagnostic_test_support import (
    build_valid_completed_c_root,
    copy_market_evidence_package,
)


def test_runner_cli_argument_contract(tmp_path: Path):
    # Missing required argument must exit with code != 0
    with pytest.raises(SystemExit):
        runner.main(["--project-root", str(tmp_path)])


def test_runner_executes_successfully_and_produces_bundle(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    pkg_dir = copy_market_evidence_package(tmp_path)
    output_root = tmp_path / "f_bundle_out"

    exit_code = runner.main([
        "--project-root", str(project_root),
        "--source-export", str(source_export),
        "--completed-root", str(completed_root),
        "--market-evidence-root", str(pkg_dir),
        "--output-root", str(output_root),
    ])

    assert exit_code == 0
    manifest_p = output_root / "stage1_6f_diagnostic_bundle_manifest.json"
    assert manifest_p.is_file()

    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "stage1_6f_diagnostic_bundle_manifest_v1"
    assert manifest["bundle_state"] in ("diagnostic_incomplete", "protocol_executed_complete")


def test_runner_rejects_already_completed_output_root(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    pkg_dir = copy_market_evidence_package(tmp_path)
    output_root = tmp_path / "f_bundle_out_dup"

    exit_code = runner.main([
        "--project-root", str(project_root),
        "--source-export", str(source_export),
        "--completed-root", str(completed_root),
        "--market-evidence-root", str(pkg_dir),
        "--output-root", str(output_root),
    ])
    assert exit_code == 0

    # Running again against the same output root must fail closed
    with pytest.raises(SystemExit):
        runner.main([
            "--project-root", str(project_root),
            "--source-export", str(source_export),
            "--completed-root", str(completed_root),
            "--market-evidence-root", str(pkg_dir),
            "--output-root", str(output_root),
        ])


@pytest.mark.parametrize("mutation_case", [
    "c_loader_missing_manifest",
    "c_artifact_hash_mismatch",
    "c_post_loader_retained_byte_mismatch",
    "market_manifest_corrupted",
    "market_csv_hash_mismatch",
    "market_zip_hash_mismatch",
    "market_csv_header_corrupted",
    "market_unlisted_extra_file",
])
def test_runner_composition_fail_closed_matrix(tmp_path: Path, mutation_case: str):
    """
    Parent 4.1 & Delta INV-FD01/INV-FD02 fail-closed matrix:
    For any source or market boundary mutation:
    reconstruct_denominator, compute_descriptive_metrics, and write_diagnostic_bundle
    call counts on runner must be strictly 0, and no completed manifest may exist.
    """
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    pkg_dir = copy_market_evidence_package(tmp_path)
    output_root = tmp_path / f"f_out_{mutation_case}"

    loader_cm = None
    if mutation_case == "c_loader_missing_manifest":
        (completed_root / "completion_manifest.json").unlink()
    elif mutation_case == "c_artifact_hash_mismatch":
        target = completed_root / "parent_audit_outcomes.jsonl"
        target.write_bytes(target.read_bytes() + b"\nTAMPER\n")
    elif mutation_case == "c_post_loader_retained_byte_mismatch":
        from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter_storage import (
            load_completed_adapter_audit as real_loader,
        )
        def loader_with_tamper(*args, **kwargs):
            res = real_loader(*args, **kwargs)
            (completed_root / "parent_audit_outcomes.jsonl").write_bytes(b"\nPOST_LOADER_TAMPER\n")
            return res
        loader_cm = patch("src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source.load_completed_adapter_audit", side_effect=loader_with_tamper)
    elif mutation_case == "market_manifest_corrupted":
        m_p = pkg_dir / "gap02_evidence_manifest.json"
        m_p.write_bytes(m_p.read_bytes() + b"TAMPER")
    elif mutation_case == "market_csv_hash_mismatch":
        csv_files = sorted(pkg_dir.rglob("*.csv"))
        csv_files[0].write_bytes(csv_files[0].read_bytes() + b"\nTAMPER,1,2\n")
    elif mutation_case == "market_zip_hash_mismatch":
        zip_files = sorted(pkg_dir.rglob("*.zip"))
        zip_files[0].write_bytes(zip_files[0].read_bytes() + b"TAMPER")
    elif mutation_case == "market_csv_header_corrupted":
        csv_files = sorted(pkg_dir.rglob("*.csv"))
        lines = csv_files[0].read_text(encoding="utf-8").splitlines()
        lines[0] = "corrupted,header,line"
        csv_files[0].write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif mutation_case == "market_unlisted_extra_file":
        (pkg_dir / "unlisted_intruder.csv").write_text("intruder\n", encoding="utf-8")

    if loader_cm:
        loader_cm.start()
    try:
        with patch.object(runner, "reconstruct_denominator") as mock_denom, \
             patch.object(runner, "compute_descriptive_metrics") as mock_metric, \
             patch.object(runner, "write_diagnostic_bundle") as mock_writer:

            with pytest.raises((SourceInvalidError, MarketEvidenceInvalidError, SystemExit)):
                runner.main([
                    "--project-root", str(project_root),
                    "--source-export", str(source_export),
                    "--completed-root", str(completed_root),
                    "--market-evidence-root", str(pkg_dir),
                    "--output-root", str(output_root),
                ])

            assert mock_denom.call_count == 0, f"reconstruct_denominator called in {mutation_case}"
            assert mock_metric.call_count == 0, f"compute_descriptive_metrics called in {mutation_case}"
            assert mock_writer.call_count == 0, f"write_diagnostic_bundle called in {mutation_case}"
            assert not (output_root / "stage1_6f_diagnostic_bundle_manifest.json").exists()
    finally:
        if loader_cm:
            loader_cm.stop()


def test_runner_ast_and_forbidden_calls():
    runner_path = Path("scripts/external_signal_shadow/run_stage1_6f_historical_mechanism_diagnostic.py")
    tree = ast.parse(runner_path.read_text(encoding="utf-8"))

    forbidden_modules = {"socket", "urllib", "http", "requests", "subprocess", "ssh", "paramiko"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import from: {node.module}"
