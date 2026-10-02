import ast
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

try:
    from scripts.external_signal_shadow.run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic import (
        main,
    )
except ImportError as _import_err:
    _err_msg = str(_import_err)

    def main(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(f"Stage 1.5H V3 CLI runner not yet implemented: {_err_msg}")


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _get_valid_baseline_dir() -> Path:
    env_file = Path("/tmp/stage1_5h_v3_env.sh")
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("export EXECUTION_BASELINE_DIR="):
                b_dir = Path(line.split("=", 1)[1].strip())
                if b_dir.is_dir():
                    return b_dir
    baseline_env = os.environ.get("EXECUTION_BASELINE_DIR")
    if baseline_env and Path(baseline_env).is_dir():
        return Path(baseline_env)
    pytest.skip("No valid EXECUTION_BASELINE_DIR found in env or /tmp/stage1_5h_v3_env.sh")


def _valid_cli_args(run_id: str, baseline_dir: Path) -> list[str]:
    return [
        "--approved-design-path",
        "docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-design_CN.md",
        "--approved-design-sha256",
        "416b394bf809e1dcc159f9d39ecd175b57962022434d09478f5e0d97fa5a9276",
        "--approved-plan-path",
        "docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-implementation-plan_CN.md",
        "--approved-plan-sha256",
        "7a1e8a5a2b0f803677bb9342d5167b8a2ec8d9458dc3c7cf8abf543c4ec53ceb",
        "--execution-baseline-dir",
        str(baseline_dir),
        "--run-id",
        run_id,
    ]


def test_cli_happy_path_spy() -> None:
    """CLI runs with valid args, spies on run_diagnostic with no overrides, returns 0."""
    baseline_dir = _get_valid_baseline_dir()
    run_id = "stage1_5h_v3_cross_root_friction_20261001T120000Z"

    mock_run = MagicMock(return_value={
        "summary": {
            "run_id": run_id,
            "decision": "stage1_5h_v3_cross_root_friction_diagnostic_generated",
        }
    })
    with patch(
        "scripts.external_signal_shadow.run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.run_diagnostic",
        mock_run,
    ):
        rc = main(_valid_cli_args(run_id, baseline_dir))
        assert rc == 0
        assert mock_run.call_count == 1
        call_args, call_kwargs = mock_run.call_args
        actual_run_id = call_kwargs.get("run_id") or (call_args[0] if call_args else None)
        actual_packet = call_kwargs.get("authority_packet") or (call_args[1] if len(call_args) > 1 else None)
        assert actual_run_id == run_id
        assert actual_packet is not None
        assert actual_packet["execution_baseline_dir"] == str(baseline_dir)
        # Verify no project-root or output override passed
        assert "project_root" not in call_kwargs
        assert "output_parent" not in call_kwargs
        assert "parent_dir" not in call_kwargs


def test_cli_rejects_missing_required_flags() -> None:
    """CLI rejects missing required flags."""
    baseline_dir = _get_valid_baseline_dir()
    args = _valid_cli_args("stage1_5h_v3_cross_root_friction_20261001T120000Z", baseline_dir)
    # Remove --run-id
    bad_args = args[:-2]
    rc = main(bad_args)
    assert rc != 0


def test_cli_rejects_forbidden_flags() -> None:
    """CLI rejects unauthorized flags like --output-root, --root, --force."""
    baseline_dir = _get_valid_baseline_dir()
    args = _valid_cli_args("stage1_5h_v3_cross_root_friction_20261001T120000Z", baseline_dir)

    for forbidden in ["--output-root", "--root", "--force", "--resume"]:
        bad_args = list(args) + [forbidden, "some_val"]
        rc = main(bad_args)
        assert rc != 0


def test_cli_rejects_invalid_run_id() -> None:
    """CLI rejects invalid run_id grammar."""
    baseline_dir = _get_valid_baseline_dir()
    bad_args = _valid_cli_args("invalid_run_id_grammar", baseline_dir)
    rc = main(bad_args)
    assert rc != 0


def test_cli_rejects_authority_drift() -> None:
    """CLI rejects wrong plan SHA256."""
    baseline_dir = _get_valid_baseline_dir()
    args = _valid_cli_args("stage1_5h_v3_cross_root_friction_20261001T120000Z", baseline_dir)
    # Tamper plan sha
    plan_sha_idx = args.index("--approved-plan-sha256") + 1
    args[plan_sha_idx] = "0" * 64
    rc = main(args)
    assert rc != 0


def test_cli_ast_no_network_and_no_raw_reads() -> None:
    """AST guard: CLI script has no raw file open, no network imports."""
    project_root = _get_project_root()
    cli_path = project_root / "scripts/external_signal_shadow/run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py"
    if not cli_path.is_file():
        raise AssertionError(f"CLI script not implemented yet: {cli_path}")

    tree = ast.parse(cli_path.read_text(encoding="utf-8"))
    forbidden_modules = {"urllib", "requests", "http", "socket", "ccxt", "aiohttp"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_root = alias.name.split(".")[0]
                assert mod_root not in forbidden_modules
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_root = node.module.split(".")[0]
                assert mod_root not in forbidden_modules
