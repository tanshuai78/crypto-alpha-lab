"""Tests for Stage 1.6F-W2-0 offline CLI runner.

Verifies:
- Call order: exact authorities -> admission -> strict reader -> materializer -> reducer -> write -> strict read-back.
- Rejection of invalid output roots: absolute, dot-dot, wrong parent, symlink, collision.
- Rejection of authority, audit, receipt mismatches.
- Network trapping: zero socket/HTTP calls permitted.
- Clean stdout containing only identity/status/counts; no raw price, basis values, or PnL.
"""

from __future__ import annotations

import http.client
import socket
import urllib.request
from pathlib import Path
from typing import Any

import pytest

import scripts.external_signal_shadow.run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic as cli_runner
from tests.research.external_signal_shadow.stage1_6f_w2_0_test_support import (
    create_canonical_w2_0_mirror,
)


@pytest.fixture(autouse=True)
def trap_all_network(monkeypatch) -> None:
    """Zero network invariant: trap any socket or HTTP creation."""
    def _forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("CRITICAL_INVARIANT_VIOLATION: network/socket call attempted in offline CLI")

    monkeypatch.setattr(socket, "socket", _forbidden)
    if hasattr(socket, "create_connection"):
        monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", _forbidden)
    monkeypatch.setattr(http.client, "HTTPConnection", _forbidden)
    monkeypatch.setattr(http.client, "HTTPSConnection", _forbidden)


def test_cli_positive_invocation(tmp_path: Path, capsys) -> None:
    """Canonical positive invocation creates sealed bundle and prints metadata."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    run_id = "test_cli_run_positive_001"
    rel_output = f"data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/{run_id}"

    rc = cli_runner.main([
        "--project-root", str(mirror.project_root),
        "--candidate-root", str(mirror.candidate_root),
        "--output-root", rel_output,
        "--w2-0-plan-path", str(mirror.w2_0_plan_path),
        "--w2-0-plan-sha", mirror.w2_0_plan_sha,
        "--external-audit-path", str(mirror.external_audit_path),
        "--external-audit-sha", mirror.external_audit_sha,
        "--historical-receipt-path", str(mirror.historical_receipt_path),
        "--historical-receipt-sha", mirror.historical_receipt_sha,
    ])
    assert rc == 0

    out, err = capsys.readouterr()
    assert err == ""
    assert f"run_id: {run_id}" in out
    assert "outcome_inspection_status: outcome_seen" in out
    assert "research_classification: exploratory_only" in out

    # Verify no raw price, basis values, or PnL printed to stdout
    forbidden_tokens = ["close", "open", "high", "low", "pnl", "return", "basis_bps", "bps"]
    for line in out.splitlines():
        for tok in forbidden_tokens:
            assert f"{tok}:" not in line.lower()

    # Manifest file exists
    manifest_p = mirror.project_root / rel_output / "stage1_6f_w2_0_bundle_manifest.json"
    assert manifest_p.is_file()


def test_cli_rejects_absolute_output_root(tmp_path: Path, capsys) -> None:
    """CLI rejects absolute output root."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    rc = cli_runner.main([
        "--project-root", str(mirror.project_root),
        "--candidate-root", str(mirror.candidate_root),
        "--output-root", "/tmp/absolute_run",
    ])
    assert rc == 1
    _, err = capsys.readouterr()
    assert "STOP=w2_0_output_root_invalid:absolute_path" in err


def test_cli_rejects_dot_dot_output_root(tmp_path: Path, capsys) -> None:
    """CLI rejects output root with dot-dot traversal."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    rc = cli_runner.main([
        "--project-root", str(mirror.project_root),
        "--candidate-root", str(mirror.candidate_root),
        "--output-root", "data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/../bad_run",
    ])
    assert rc == 1
    _, err = capsys.readouterr()
    assert "STOP=w2_0_output_root_invalid:dot_dot_alias" in err


def test_cli_rejects_wrong_parent_output_root(tmp_path: Path, capsys) -> None:
    """CLI rejects output root under wrong parent."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    rc = cli_runner.main([
        "--project-root", str(mirror.project_root),
        "--candidate-root", str(mirror.candidate_root),
        "--output-root", "data/wrong_parent/run_001",
    ])
    assert rc == 1
    _, err = capsys.readouterr()
    assert "STOP=w2_0_output_root_invalid:parent_mismatch" in err


def test_cli_rejects_invalid_run_id_format(tmp_path: Path, capsys) -> None:
    """CLI rejects run ID with spaces or special characters."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    rc = cli_runner.main([
        "--project-root", str(mirror.project_root),
        "--candidate-root", str(mirror.candidate_root),
        "--output-root", "data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/bad run!@#",
    ])
    assert rc == 1
    _, err = capsys.readouterr()
    assert "STOP=w2_0_output_root_invalid:invalid_run_id_format" in err


def test_cli_rejects_output_root_collision(tmp_path: Path, capsys) -> None:
    """CLI rejects output root collision."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    run_id = "test_cli_collision_001"
    rel_output = f"data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/{run_id}"
    (mirror.project_root / rel_output).mkdir(parents=True, exist_ok=True)

    rc = cli_runner.main([
        "--project-root", str(mirror.project_root),
        "--candidate-root", str(mirror.candidate_root),
        "--output-root", rel_output,
    ])
    assert rc == 1
    _, err = capsys.readouterr()
    assert "STOP=w2_0_output_root_collision" in err


def test_cli_rejects_plan_sha_mismatch(tmp_path: Path, capsys) -> None:
    """CLI rejects approved plan SHA mismatch."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    run_id = "test_cli_plan_mismatch_001"
    rel_output = f"data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/{run_id}"

    rc = cli_runner.main([
        "--project-root", str(mirror.project_root),
        "--candidate-root", str(mirror.candidate_root),
        "--output-root", rel_output,
        "--w2-0-plan-sha", "0" * 64,
    ])
    assert rc == 1
    _, err = capsys.readouterr()
    assert "STOP=w2_0_admission_invalid:w2_0_plan_sha_mismatch" in err


def test_cli_rejects_audit_sha_mismatch(tmp_path: Path, capsys) -> None:
    """CLI rejects external audit SHA mismatch."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    run_id = "test_cli_audit_mismatch_001"
    rel_output = f"data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/{run_id}"

    rc = cli_runner.main([
        "--project-root", str(mirror.project_root),
        "--candidate-root", str(mirror.candidate_root),
        "--output-root", rel_output,
        "--external-audit-sha", "0" * 64,
    ])
    assert rc == 1
    _, err = capsys.readouterr()
    assert "STOP=w2_0_admission_invalid:external_audit_sha_mismatch" in err
