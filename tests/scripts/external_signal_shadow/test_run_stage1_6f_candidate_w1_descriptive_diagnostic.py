"""Tests for offline candidate W1 descriptive diagnostic runner script.

Invariants: INV-CA01 through INV-CA12.
Validates CLI argument parsing, strict canonical routing, fail-closed gates,
network isolation (AST and runtime traps), and sealed bundle generation.
"""

from __future__ import annotations

import ast
import http.client
import shutil
import socket
import urllib.request
from pathlib import Path

import pytest

from scripts.external_signal_shadow import (
    run_stage1_6f_candidate_w1_descriptive_diagnostic as runner,
)
from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import (
    CANONICAL_CANDIDATE_RELATIVE_PATH,
)
from src.research.external_signal_shadow.stage1_6f_candidate_w1_diagnostic_storage import (
    load_candidate_w1_bundle,
)
from tests.research.external_signal_shadow.stage1_6f_candidate_w1_test_support import (
    B_SOURCE_EXPORT_RELATIVE,
    C_COMPLETED_ROOT_RELATIVE,
    create_canonical_project_mirror,
)


@pytest.fixture(scope="module")
def canonical_mirror(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("canonical_cli_mirror")
    return create_canonical_project_mirror(base)


def test_ast_no_network_and_no_subprocesses():
    """Independent AST proof: 4 production modules contain zero network/subprocess calls."""
    repo_root = Path(__file__).resolve().parents[3]
    target_files = [
        repo_root / "src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py",
        repo_root / "src/research/external_signal_shadow/stage1_6f_candidate_w1_descriptive_diagnostic.py",
        repo_root / "src/research/external_signal_shadow/stage1_6f_candidate_w1_diagnostic_storage.py",
        repo_root / "scripts/external_signal_shadow/run_stage1_6f_candidate_w1_descriptive_diagnostic.py",
    ]

    forbidden_modules = {
        "urllib",
        "http",
        "socket",
        "requests",
        "httpx",
        "aiohttp",
        "websockets",
        "ftplib",
        "subprocess",
    }

    for target in target_files:
        assert target.is_file(), f"target file missing: {target}"
        tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    assert root_mod not in forbidden_modules, f"Forbidden import {alias.name} in {target}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_mod = node.module.split(".")[0]
                    assert root_mod not in forbidden_modules, f"Forbidden importFrom {node.module} in {target}"
            elif isinstance(node, ast.Call):
                # Check for os.system, os.popen
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        assert node.func.attr not in ("system", "popen"), f"Forbidden os call {node.func.attr} in {target}"


def test_positive_offline_runner_execution(
    canonical_mirror: Path,
    monkeypatch,
):
    """Run runner.main with runtime network traps and verify sealed bundle generation."""
    def _trap_network(*args, **kwargs):
        raise RuntimeError("NETWORK_ACCESS_FORBIDDEN_AT_RUNTIME")

    monkeypatch.setattr(socket, "socket", _trap_network)
    monkeypatch.setattr(socket, "create_connection", _trap_network)
    monkeypatch.setattr(urllib.request, "urlopen", _trap_network)
    monkeypatch.setattr(http.client, "HTTPConnection", _trap_network)
    monkeypatch.setattr(http.client, "HTTPSConnection", _trap_network)

    run_id = "cli_test_run_001"
    output_rel = f"data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/{run_id}"
    output_abs = canonical_mirror / output_rel

    exit_code = runner.main([
        "--project-root", str(canonical_mirror),
        "--source-export", str(canonical_mirror / B_SOURCE_EXPORT_RELATIVE),
        "--completed-root", str(canonical_mirror / C_COMPLETED_ROOT_RELATIVE),
        "--candidate-root", str(canonical_mirror / CANONICAL_CANDIDATE_RELATIVE_PATH),
        "--output-root", output_rel,
    ])

    assert exit_code == 0
    assert output_abs.is_dir()

    # Verify reload
    bundle = load_candidate_w1_bundle(output_root=output_abs)
    assert bundle.manifest["bundle_run_id"] == run_id
    assert bundle.manifest["denominator_count"] == 41
    assert len(bundle.metric_records) == 779
    assert bundle.summary["n_unique_parent_article_ids"] == 27


def test_runner_rejects_missing_arguments():
    with pytest.raises(SystemExit):
        runner.main(["--project-root", "/some/path"])


def test_runner_rejects_output_root_invalid_parent(canonical_mirror: Path):
    exit_code = runner.main([
        "--project-root", str(canonical_mirror),
        "--source-export", str(canonical_mirror / B_SOURCE_EXPORT_RELATIVE),
        "--completed-root", str(canonical_mirror / C_COMPLETED_ROOT_RELATIVE),
        "--candidate-root", str(canonical_mirror / CANONICAL_CANDIDATE_RELATIVE_PATH),
        "--output-root", "invalid_parent/run_001",
    ])
    assert exit_code != 0


def test_runner_rejects_output_root_absolute(canonical_mirror: Path):
    abs_out = canonical_mirror / "data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/abs_run"
    exit_code = runner.main([
        "--project-root", str(canonical_mirror),
        "--source-export", str(canonical_mirror / B_SOURCE_EXPORT_RELATIVE),
        "--completed-root", str(canonical_mirror / C_COMPLETED_ROOT_RELATIVE),
        "--candidate-root", str(canonical_mirror / CANONICAL_CANDIDATE_RELATIVE_PATH),
        "--output-root", str(abs_out),
    ])
    assert exit_code != 0


def test_runner_rejects_output_root_collision(canonical_mirror: Path):
    run_id = "collision_run_001"
    output_rel = f"data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/{run_id}"
    existing_dir = canonical_mirror / output_rel
    existing_dir.mkdir(parents=True, exist_ok=True)

    exit_code = runner.main([
        "--project-root", str(canonical_mirror),
        "--source-export", str(canonical_mirror / B_SOURCE_EXPORT_RELATIVE),
        "--completed-root", str(canonical_mirror / C_COMPLETED_ROOT_RELATIVE),
        "--candidate-root", str(canonical_mirror / CANONICAL_CANDIDATE_RELATIVE_PATH),
        "--output-root", output_rel,
    ])
    assert exit_code != 0


def test_runner_rejects_output_parent_symlink(canonical_mirror: Path, tmp_path: Path, capsys):
    """Test that runner rejects symlinked output parent directory and writes no files to external target."""
    mirror = create_canonical_project_mirror(tmp_path / "symlink_parent_mirror")
    parent_dir = mirror / "data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics"
    if parent_dir.exists():
        if parent_dir.is_dir() and not parent_dir.is_symlink():
            shutil.rmtree(parent_dir)
        else:
            parent_dir.unlink()

    outside_target = tmp_path / "outside_target"
    outside_target.mkdir(parents=True, exist_ok=True)
    parent_dir.symlink_to(outside_target)

    run_id = "symlink_parent_run"
    output_rel = f"data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/{run_id}"

    exit_code = runner.main([
        "--project-root", str(mirror),
        "--source-export", str(mirror / B_SOURCE_EXPORT_RELATIVE),
        "--completed-root", str(mirror / C_COMPLETED_ROOT_RELATIVE),
        "--candidate-root", str(mirror / CANONICAL_CANDIDATE_RELATIVE_PATH),
        "--output-root", output_rel,
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "STOP=candidate_w1_output_root_invalid" in captured.err
    # Assert external target has no files, no directory, and no manifest
    assert not (outside_target / run_id).exists()
    assert not (outside_target / run_id / "manifest.json").exists()


def test_runner_rejects_output_root_symlink(canonical_mirror: Path, tmp_path: Path, capsys):
    """Test that runner rejects symlinked output root directly and writes no files to external target."""
    mirror = create_canonical_project_mirror(tmp_path / "symlink_root_mirror")
    parent_dir = mirror / "data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics"
    parent_dir.mkdir(parents=True, exist_ok=True)

    run_id = "symlink_root_run"
    target_link = parent_dir / run_id
    outside_run_target = tmp_path / "outside_run_target"
    target_link.symlink_to(outside_run_target)

    output_rel = f"data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/{run_id}"

    exit_code = runner.main([
        "--project-root", str(mirror),
        "--source-export", str(mirror / B_SOURCE_EXPORT_RELATIVE),
        "--completed-root", str(mirror / C_COMPLETED_ROOT_RELATIVE),
        "--candidate-root", str(mirror / CANONICAL_CANDIDATE_RELATIVE_PATH),
        "--output-root", output_rel,
    ])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "STOP=candidate_w1_output_root_invalid" in captured.err
    assert not outside_run_target.exists()

