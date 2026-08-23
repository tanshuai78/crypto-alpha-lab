"""Tests for Stage 1.6A sealed-export source-audit CLI script."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from tests.research.external_signal_shadow.stage1_6a_sealed_export_adapter_test_support import (
    build_valid_historical_sealed_export,
    trusted_article,
)


def test_cli_runs_synthetic_completed_export_to_separate_fresh_root(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    run_id = "cli_test_run_001"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id

    cmd = [
        sys.executable,
        "scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py",
        "--project-root",
        str(root),
        "--source-export",
        str(export),
        "--audit-run-id",
        run_id,
        "--output-root",
        str(out_root),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI failed: {res.stderr}"
    assert (out_root / "completion_manifest.json").is_file()


def test_cli_rejects_existing_or_mismatched_run_id_output_root_before_write(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    run_id = "cli_test_run_002"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / "wrong_id"

    cmd = [
        sys.executable,
        "scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py",
        "--project-root",
        str(root),
        "--source-export",
        str(export),
        "--audit-run-id",
        run_id,
        "--output-root",
        str(out_root),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert not out_root.exists()


def test_cli_rejects_output_root_outside_adapter_output_family_before_write(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    run_id = "cli_test_run_outside"
    out_root = tmp_path / "outside" / run_id

    res = subprocess.run([
        sys.executable,
        "scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py",
        "--project-root", str(root),
        "--source-export", str(export),
        "--audit-run-id", run_id,
        "--output-root", str(out_root),
    ], capture_output=True, text=True)

    assert res.returncode != 0
    assert not out_root.exists()


def test_cli_rejects_invalid_source_before_creating_output_root(tmp_path):
    root = tmp_path
    nonexistent_export = root / "data" / "external_signal_shadow" / "stage1_6b" / "historical_backfill" / "none" / "sealed_exports" / "none"
    run_id = "cli_test_run_003"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id

    cmd = [
        sys.executable,
        "scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py",
        "--project-root",
        str(root),
        "--source-export",
        str(nonexistent_export),
        "--audit-run-id",
        run_id,
        "--output-root",
        str(out_root),
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert not out_root.exists()


def test_cli_has_no_network_stage15_or_legacy_fixture_import_boundary():
    script_path = Path("scripts/external_signal_shadow/run_stage1_6a_sealed_export_source_audit.py")
    if not script_path.is_file():
        pytest.fail("CLI script does not exist yet")

    tree = ast.parse(script_path.read_text(encoding="utf-8"))
    forbidden_modules = {"requests", "urllib.request", "http", "websocket", "selenium", "aiohttp", "httpx"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in forbidden_modules
                assert "stage1_5" not in alias.name
                assert "strategies" not in alias.name
                assert "risk" not in alias.name
                assert "execution" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert node.module not in forbidden_modules
                assert "stage1_5" not in node.module
                assert "strategies" not in node.module
                assert "risk" not in node.module
                assert "execution" not in node.module
            for alias in node.names:
                assert alias.name not in ("process_capture_bundle", "persist_audit_artifacts")


def test_legacy_fixture_cli_remains_fixture_only_and_unmodified():
    legacy_script = Path("scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py")
    assert legacy_script.is_file()
    content = legacy_script.read_text(encoding="utf-8")
    assert "--fixture-run" in content
    assert "stage1_6a_sealed_export_adapter" not in content
