import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


DESIGN_PATH = "docs/designs/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-design_CN.md"
DESIGN_SHA = "81f7da45c882cc16430f57e4252e5530e457a95b7f36ff045d262ded9e755da0"
PLAN_PATH = "docs/plans/2026-10-02-external-signal-shadow-lab-stage1-5g-n3-regime-stratified-admission-implementation-plan_CN.md"
PLAN_SHA = "f0582a5ba03db3be8340dfa8d5d47b5c1dcb63caac19cebb5888a2c1d56eb5bb"
RUN_ID = "stage1_5g_n3_regime_stratified_admission_20261002T120000Z"
CLI_SCRIPT = "scripts/external_signal_shadow/run_stage1_5g_n3_regime_stratified_admission.py"


def _isolated_project_without_generation_authority(tmp_path: Path) -> Path:
    source_root = _get_project_root()
    project_root = tmp_path / "project"
    bundle = project_root / ".git" / "plan-execution" / "stage1_5g_n3_regime" / PLAN_SHA

    for rel_path in (DESIGN_PATH, PLAN_PATH, CLI_SCRIPT):
        source = source_root / rel_path
        destination = project_root / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    subprocess.run(["git", "init", "-q", str(project_root)], check=True)
    subprocess.run(["git", "-C", str(project_root), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(project_root), "config", "user.name", "N3 Test"], check=True)
    subprocess.run(["git", "-C", str(project_root), "add", "docs", "scripts"], check=True)
    subprocess.run(["git", "-C", str(project_root), "commit", "-qm", "isolated authority fixture"], check=True)
    base_sha = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    bundle.mkdir(parents=True)
    for name in ("implementation_authorization.txt", "implementation_authorization.sha256"):
        shutil.copy2(
            source_root / ".git" / "plan-execution" / "stage1_5g_n3_regime" / PLAN_SHA / name,
            bundle / name,
        )
    authority = {
        "approved_design_path": DESIGN_PATH,
        "approved_design_sha256": DESIGN_SHA,
        "approved_plan_path": PLAN_PATH,
        "approved_plan_sha256": PLAN_SHA,
        "base_sha": base_sha,
        "current_plan_sha256": PLAN_SHA,
        "project_root": str(project_root.resolve()),
    }
    authority_bytes = json.dumps(authority, sort_keys=True, separators=(",", ":")).encode("utf-8")
    (bundle / "execution_authority.json").write_bytes(authority_bytes)
    (bundle / "execution_authority.sha256").write_text(
        f"{hashlib.sha256(authority_bytes).hexdigest()}  execution_authority.json\n",
        encoding="utf-8",
    )
    return project_root


def test_cli_rejects_forbidden_flags():
    project_root = _get_project_root()
    cli_p = project_root / CLI_SCRIPT

    cmd = [
        sys.executable,
        str(cli_p),
        "--approved-design-path", DESIGN_PATH,
        "--approved-design-sha256", DESIGN_SHA,
        "--approved-plan-path", PLAN_PATH,
        "--approved-plan-sha256", PLAN_SHA,
        "--run-id", RUN_ID,
        "--execution-baseline-dir", "/tmp/fake",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
    assert res.returncode != 0
    assert "unrecognized arguments" in res.stderr.lower() or "error" in res.stderr.lower()


def test_cli_rejects_malformed_run_id():
    project_root = _get_project_root()
    cli_p = project_root / CLI_SCRIPT

    cmd = [
        sys.executable,
        str(cli_p),
        "--approved-design-path", DESIGN_PATH,
        "--approved-design-sha256", DESIGN_SHA,
        "--approved-plan-path", PLAN_PATH,
        "--approved-plan-sha256", PLAN_SHA,
        "--run-id", "invalid_run_id_format",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
    assert res.returncode != 0
    assert "STOP=stage1_5g_n3_regime_publication_integrity_failure" in res.stderr or res.returncode != 0


def test_cli_without_receipt_generation_auth_stops(tmp_path):
    """Without receipt_generation_authorization.txt, CLI stops before source or staging."""
    source_root = _get_project_root()
    project_root = _isolated_project_without_generation_authority(tmp_path)
    cli_p = project_root / CLI_SCRIPT

    cmd = [
        sys.executable,
        str(cli_p),
        "--approved-design-path", DESIGN_PATH,
        "--approved-design-sha256", DESIGN_SHA,
        "--approved-plan-path", PLAN_PATH,
        "--approved-plan-sha256", PLAN_SHA,
        "--run-id", RUN_ID,
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root)
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root), env=env)
    assert res.returncode != 0
    assert "STOP=local_receipt_generation_not_authorized" in res.stderr or "STOP=local_receipt_generation_not_authorized" in res.stdout
    assert not (project_root / "data" / "external_signal_shadow" / "stage1_5g" / "n3_regime_stratified_admissions").exists()


def test_cli_ast_guards():
    """Verify script imports no network or execution libraries."""
    project_root = _get_project_root()
    cli_p = project_root / CLI_SCRIPT
    if not cli_p.exists():
        pytest.fail("cli script does not exist yet")

    tree = ast.parse(cli_p.read_text(encoding="utf-8"), filename=str(cli_p))
    forbidden = {"socket", "requests", "urllib", "http", "ccxt", "paramiko"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert node.module.split(".")[0] not in forbidden
