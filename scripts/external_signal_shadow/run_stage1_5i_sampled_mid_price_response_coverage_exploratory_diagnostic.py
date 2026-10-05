#!/usr/bin/env python3
"""CLI runner for Stage 1.5I N=3 Sampled Mid-Price Response Coverage and Exploratory Diagnostic."""

from __future__ import annotations

import argparse
import sys

from src.research.external_signal_shadow.stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic import (
    APPROVED_DESIGN_REL_PATH,
    APPROVED_DESIGN_SHA256,
    APPROVED_PLAN_REL_PATH,
    APPROVED_PLAN_SHA256,
    run_diagnostic,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Stage 1.5I N=3 Sampled Mid-Price Response Diagnostic",
        allow_abbrev=False,
    )
    parser.add_argument("--approved-design-path", required=True, help="Path to approved Design")
    parser.add_argument("--approved-design-sha256", required=True, help="SHA256 of approved Design")
    parser.add_argument("--approved-plan-path", required=True, help="Path to approved Plan")
    parser.add_argument("--approved-plan-sha256", required=True, help="SHA256 of approved Plan")
    parser.add_argument("--run-id", required=True, help="Authoritative Run ID")

    args = parser.parse_args(argv)

    if args.approved_design_path != APPROVED_DESIGN_REL_PATH:
        parser.error(f"Invalid --approved-design-path: {args.approved_design_path}")
    if args.approved_design_sha256 != APPROVED_DESIGN_SHA256:
        parser.error(f"Invalid --approved-design-sha256: {args.approved_design_sha256}")
    if args.approved_plan_path != APPROVED_PLAN_REL_PATH:
        parser.error(f"Invalid --approved-plan-path: {args.approved_plan_path}")
    if args.approved_plan_sha256 != APPROVED_PLAN_SHA256:
        parser.error(f"Invalid --approved-plan-sha256: {args.approved_plan_sha256}")

    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        summary = run_diagnostic(run_id=args.run_id)
        print(f"STAGE1_5I_SUCCESS: run_id={summary['run_id']} decision={summary['decision']}")
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:
        print(f"STAGE1_5I_FAILURE: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
