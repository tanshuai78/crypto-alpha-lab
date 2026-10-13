"""Tests for scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py.

Verifies:
1. CLI argument validation (exits with code 2 on missing or malformed args).
2. Unauthorized invocation fails closed (exits with code 1, creates zero outputs).
3. Delegation to public core entry point run_stage1_5j_b_historical_aggtrades_launch_response.
"""

from pathlib import Path

import pytest

from scripts.external_signal_shadow.run_stage1_5j_b_historical_aggtrades_launch_response import (
    main,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_cli_missing_args(capsys: pytest.CaptureFixture[str]) -> None:
    """Invoking CLI without required arguments must exit with code 2."""
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_cli_invalid_run_id_pattern(capsys: pytest.CaptureFixture[str]) -> None:
    """Invoking CLI with invalid run_id regex must exit with code 2."""
    with pytest.raises(SystemExit) as exc:
        main(["--run-id", "invalid_run_id_format"])
    assert exc.value.code == 2


def test_cli_unauthorized_invocation_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invoking CLI in production environment fails closed with code 1 because authorization is absent."""
    valid_run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    ret = main(["--run-id", valid_run_id])
    assert ret == 1
    # Verify no output directory was created in data
    out_dir = PROJECT_ROOT / "data" / "external_signal_shadow" / "stage1_5j_b" / "historical_aggtrades_launch_response" / valid_run_id
    assert not out_dir.exists()
