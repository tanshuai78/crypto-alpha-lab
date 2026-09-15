"""Tests for Stage 1.6F read-only bundle reviewer script."""

import ast
from pathlib import Path

import pytest

from scripts.external_signal_shadow import (
    review_stage1_6f_historical_mechanism_diagnostic as reviewer,
)
from scripts.external_signal_shadow import run_stage1_6f_historical_mechanism_diagnostic as runner
from tests.research.external_signal_shadow.stage1_6f_historical_diagnostic_test_support import (
    build_valid_completed_c_root,
    copy_market_evidence_package,
)


def _generate_test_bundle(tmp_path: Path) -> Path:
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    pkg_dir = copy_market_evidence_package(tmp_path)
    output_root = tmp_path / "f_bundle_for_review"

    exit_code = runner.main([
        "--project-root", str(project_root),
        "--source-export", str(source_export),
        "--completed-root", str(completed_root),
        "--market-evidence-root", str(pkg_dir),
        "--output-root", str(output_root),
    ])
    assert exit_code == 0
    return output_root


def test_reviewer_cli_argument_contract(tmp_path: Path):
    with pytest.raises(SystemExit) as exc_info:
        reviewer.main([])
    assert exc_info.value.code == 2


def test_reviewer_reports_bundle_successfully(tmp_path: Path, capsys: pytest.CaptureFixture):
    bundle_root = _generate_test_bundle(tmp_path)

    exit_code = reviewer.main(["--bundle-root", str(bundle_root)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "=== STAGE 1.6F HISTORICAL MECHANISM DIAGNOSTIC REVIEW ===" in captured.out
    assert "Bundle State:" in captured.out
    assert "Authority Flags: ALL_STRICTLY_FALSE" in captured.out
    assert "=== REVIEW PASSED ===" in captured.out


def test_reviewer_rejects_corrupted_bundle(tmp_path: Path):
    bundle_root = _generate_test_bundle(tmp_path)

    # Corrupt an artifact: tamper with summary bytes
    summary_path = bundle_root / "stage1_6f_diagnostic_summary.json"
    summary_path.write_bytes(summary_path.read_bytes() + b"TAMPER")

    with pytest.raises(SystemExit) as exc_info:
        reviewer.main(["--bundle-root", str(bundle_root)])
    assert exc_info.value.code == 1


def test_reviewer_ast_and_forbidden_calls():
    reviewer_path = Path("scripts/external_signal_shadow/review_stage1_6f_historical_mechanism_diagnostic.py")
    tree = ast.parse(reviewer_path.read_text(encoding="utf-8"))

    forbidden_modules = {
        "socket",
        "urllib",
        "http",
        "requests",
        "subprocess",
        "ssh",
        "paramiko",
        "src.execution",
        "src.strategy",
        "src.risk",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import: {alias.name}"
                assert alias.name not in forbidden_modules, f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import from: {node.module}"
                assert node.module not in forbidden_modules, f"Forbidden import from: {node.module}"
