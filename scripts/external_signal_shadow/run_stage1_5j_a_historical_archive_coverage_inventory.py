"""CLI runner for Stage 1.5J-A Historical Archive Coverage Inventory.

Enforces:
- Strict argparse validation: only the 5 approved CLI flags are accepted
- Strict literal validation against compiled Design/Plan paths and SHAs
- Strict RUN_ID regex grammar validation
- Delegation only to production run_inventory(run_id)
- Zero socket or network imports
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Sequence

from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
    APPROVED_DESIGN_REL_PATH,
    APPROVED_DESIGN_SHA256,
    APPROVED_PLAN_REL_PATH,
    APPROVED_PLAN_SHA256,
    Stage1_5JADiagnosticError,
    run_inventory,
)

RUN_ID_REGEX = re.compile(r"^stage1_5j_a_historical_archive_coverage_inventory_\d{8}T\d{6}Z$")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 1.5J-A Historical Archive Coverage Inventory CLI",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--approved-design-path",
        required=True,
        help="Relative path to approved Design document",
    )
    parser.add_argument(
        "--approved-design-sha256",
        required=True,
        help="SHA-256 of approved Design document",
    )
    parser.add_argument(
        "--approved-plan-path",
        required=True,
        help="Relative path to approved Plan document",
    )
    parser.add_argument(
        "--approved-plan-sha256",
        required=True,
        help="SHA-256 of approved Plan document",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Authorized run ID (UTC format)",
    )

    args = parser.parse_args(argv)

    # Validate literals
    if args.approved_design_path != APPROVED_DESIGN_REL_PATH:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_cli_authority_mismatch:design_path:{args.approved_design_path}"
        )
    if args.approved_design_sha256 != APPROVED_DESIGN_SHA256:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_cli_authority_mismatch:design_sha:{args.approved_design_sha256}"
        )
    if args.approved_plan_path != APPROVED_PLAN_REL_PATH:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_cli_authority_mismatch:plan_path:{args.approved_plan_path}"
        )
    if args.approved_plan_sha256 != APPROVED_PLAN_SHA256:
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_cli_authority_mismatch:plan_sha:{args.approved_plan_sha256}"
        )
    if not RUN_ID_REGEX.match(args.run_id):
        raise Stage1_5JADiagnosticError(
            f"STOP=stage1_5j_a_cli_run_id_invalid:{args.run_id}"
        )

    return args


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        result = run_inventory(run_id=args.run_id)
        print(f"Stage 1.5J-A inventory complete: {result.get('decision')}")
        return 0
    except Stage1_5JADiagnosticError as e:
        print(f"Diagnostic Error: {e}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    sys.exit(main())
