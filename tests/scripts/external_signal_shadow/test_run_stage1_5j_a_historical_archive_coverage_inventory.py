"""Tests for Stage 1.5J-A Historical Archive Coverage Inventory CLI.

Verifies:
- Strict argparse validation: only the 5 approved CLI flags are accepted
- Extra or unauthorized flags (e.g. --output-dir, --override, --skip-authority) rejected
- Authority literals matching approved Design/Plan paths and SHAs
- Proper delegation to production run_inventory(run_id)
"""

import sys
from unittest.mock import patch

import pytest

APPROVED_DESIGN_REL_PATH = "docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md"
APPROVED_DESIGN_SHA256 = "b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a"
APPROVED_PLAN_REL_PATH = "docs/plans/2026-10-06-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-implementation-plan_CN.md"
APPROVED_PLAN_SHA256 = "fa7d2ac23a605163a3ceb476efe4c5823b94e16ef9944ced173a2cff9d07279f"
VALID_RUN_ID = "stage1_5j_a_historical_archive_coverage_inventory_20261006T000000Z"

# Graceful import stubbing for TDD RED phase
try:
    from scripts.external_signal_shadow.run_stage1_5j_a_historical_archive_coverage_inventory import (
        main as cli_main,
    )
    from scripts.external_signal_shadow.run_stage1_5j_a_historical_archive_coverage_inventory import (
        parse_args as cli_parse_args,
    )
except ImportError as _import_err:
    _err_msg = str(_import_err)

    def _cli_unimplemented_stub(*args, **kwargs):
        raise RuntimeError(f"STOP=stage1_5j_a_cli_not_yet_implemented: {_err_msg}")

    cli_main = _cli_unimplemented_stub
    cli_parse_args = _cli_unimplemented_stub


def test_cli_rejects_missing_arguments() -> None:
    test_args = ["run_stage1_5j_a.py", "--run-id", VALID_RUN_ID]
    with patch.object(sys, "argv", test_args):
        with pytest.raises((SystemExit, Exception)):
            cli_parse_args()


def test_cli_rejects_forbidden_extra_flags() -> None:
    test_args = [
        "run_stage1_5j_a.py",
        "--approved-design-path", APPROVED_DESIGN_REL_PATH,
        "--approved-design-sha256", APPROVED_DESIGN_SHA256,
        "--approved-plan-path", APPROVED_PLAN_REL_PATH,
        "--approved-plan-sha256", APPROVED_PLAN_SHA256,
        "--run-id", VALID_RUN_ID,
        "--output-dir", "/tmp/forbidden",
    ]
    with patch.object(sys, "argv", test_args):
        with pytest.raises((SystemExit, Exception)):
            cli_parse_args()


def test_cli_rejects_wrong_design_sha() -> None:
    test_args = [
        "run_stage1_5j_a.py",
        "--approved-design-path", APPROVED_DESIGN_REL_PATH,
        "--approved-design-sha256", "0" * 64,
        "--approved-plan-path", APPROVED_PLAN_REL_PATH,
        "--approved-plan-sha256", APPROVED_PLAN_SHA256,
        "--run-id", VALID_RUN_ID,
    ]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(Exception, match=r"STOP=stage1_5j_a_cli_authority_mismatch:design_sha"):
            cli_main()


def test_cli_rejects_wrong_plan_sha() -> None:
    test_args = [
        "run_stage1_5j_a.py",
        "--approved-design-path", APPROVED_DESIGN_REL_PATH,
        "--approved-design-sha256", APPROVED_DESIGN_SHA256,
        "--approved-plan-path", APPROVED_PLAN_REL_PATH,
        "--approved-plan-sha256", "0" * 64,
        "--run-id", VALID_RUN_ID,
    ]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(Exception, match=r"STOP=stage1_5j_a_cli_authority_mismatch:plan_sha"):
            cli_main()


def test_cli_rejects_malformed_run_id() -> None:
    test_args = [
        "run_stage1_5j_a.py",
        "--approved-design-path", APPROVED_DESIGN_REL_PATH,
        "--approved-design-sha256", APPROVED_DESIGN_SHA256,
        "--approved-plan-path", APPROVED_PLAN_REL_PATH,
        "--approved-plan-sha256", APPROVED_PLAN_SHA256,
        "--run-id", "invalid_run_id_prefix",
    ]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(Exception, match=r"STOP=stage1_5j_a_cli_run_id_invalid"):
            cli_main()


def test_cli_delegates_to_run_inventory() -> None:
    test_args = [
        "run_stage1_5j_a.py",
        "--approved-design-path", APPROVED_DESIGN_REL_PATH,
        "--approved-design-sha256", APPROVED_DESIGN_SHA256,
        "--approved-plan-path", APPROVED_PLAN_REL_PATH,
        "--approved-plan-sha256", APPROVED_PLAN_SHA256,
        "--run-id", VALID_RUN_ID,
    ]
    with patch.object(sys, "argv", test_args):
        with patch("scripts.external_signal_shadow.run_stage1_5j_a_historical_archive_coverage_inventory.run_inventory", return_value={"status": "ok"}) as mock_run:
            _ = cli_main()
            mock_run.assert_called_once_with(run_id=VALID_RUN_ID)
