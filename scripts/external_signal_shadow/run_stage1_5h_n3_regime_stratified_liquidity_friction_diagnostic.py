import argparse
import sys
from pathlib import Path
from typing import List, Optional

from src.research.external_signal_shadow.stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic import (
    APPROVED_DESIGN_REL_PATH,
    APPROVED_DESIGN_SHA256,
    APPROVED_PLAN_REL_PATH,
    APPROVED_PLAN_SHA256,
    RUN_ID_REGEX,
    Stage1_5HN3RegimeFrictionError,
    run_diagnostic,
)


def _get_project_root() -> Path:
    """Derives project root strictly from this script file location."""
    return Path(__file__).resolve().parents[2]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage 1.5H N=3 Product-Regime Stratified Liquidity Friction Diagnostic Runner"
    )
    parser.add_argument("--approved-design-path", required=True, help="Relative path to approved Design")
    parser.add_argument("--approved-design-sha256", required=True, help="Expected SHA256 of approved Design")
    parser.add_argument("--approved-plan-path", required=True, help="Relative path to approved Plan")
    parser.add_argument("--approved-plan-sha256", required=True, help="Expected SHA256 of approved Plan")
    parser.add_argument("--run-id", required=True, help="Exact run ID for this execution")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    # 1. Exact flag assertions
    if args.approved_design_path != APPROVED_DESIGN_REL_PATH:
        print(f"Error: approved_design_path mismatch: {args.approved_design_path} != {APPROVED_DESIGN_REL_PATH}", file=sys.stderr)
        return 1

    if args.approved_design_sha256 != APPROVED_DESIGN_SHA256:
        print(f"Error: approved_design_sha256 mismatch: {args.approved_design_sha256} != {APPROVED_DESIGN_SHA256}", file=sys.stderr)
        return 1

    if args.approved_plan_path != APPROVED_PLAN_REL_PATH:
        print(f"Error: approved_plan_path mismatch: {args.approved_plan_path} != {APPROVED_PLAN_REL_PATH}", file=sys.stderr)
        return 1

    if args.approved_plan_sha256 != APPROVED_PLAN_SHA256:
        print(f"Error: approved_plan_sha256 mismatch: {args.approved_plan_sha256} != {APPROVED_PLAN_SHA256}", file=sys.stderr)
        return 1

    if not RUN_ID_REGEX.match(args.run_id):
        print(f"Error: malformed run_id: {args.run_id}", file=sys.stderr)
        return 1

    try:
        res = run_diagnostic(run_id=args.run_id)
        print(f"Diagnostic generated successfully: run_id={res['summary']['run_id']}")
        return 0
    except Stage1_5HN3RegimeFrictionError as e:
        print(f"Diagnostic authority / validation error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
