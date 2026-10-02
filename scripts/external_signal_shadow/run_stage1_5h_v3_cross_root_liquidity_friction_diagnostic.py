from __future__ import annotations

import argparse
import sys

from src.research.external_signal_shadow.stage1_5h_v3_cross_root_liquidity_friction_diagnostic import (
    Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError,
    run_diagnostic,
    verify_execution_authority,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage 1.5H V3 cross-root liquidity friction diagnostic runner.",
    )
    parser.add_argument("--approved-design-path", required=True, help="Path to approved design")
    parser.add_argument("--approved-design-sha256", required=True, help="SHA256 of approved design")
    parser.add_argument("--approved-plan-path", required=True, help="Path to approved plan")
    parser.add_argument("--approved-plan-sha256", required=True, help="SHA256 of approved plan")
    parser.add_argument("--execution-baseline-dir", required=True, help="Path to execution baseline dir")
    parser.add_argument("--run-id", required=True, help="Run ID")

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    try:
        authority_packet = {
            "execution_baseline_dir": args.execution_baseline_dir,
            "approved_design_path": args.approved_design_path,
            "approved_design_sha256": args.approved_design_sha256,
            "approved_plan_path": args.approved_plan_path,
            "approved_plan_sha256": args.approved_plan_sha256,
        }

        # 1. Authority validation
        verify_execution_authority(
            execution_baseline_dir=args.execution_baseline_dir,
            supplied_approval_bindings={
                "approved_design_path": args.approved_design_path,
                "approved_design_sha256": args.approved_design_sha256,
                "approved_plan_path": args.approved_plan_path,
                "approved_plan_sha256": args.approved_plan_sha256,
            },
        )

        # 2. Run diagnostic
        result = run_diagnostic(run_id=args.run_id, authority_packet=authority_packet)
        summary = result["summary"]
        print(f"DIAGNOSTIC_GENERATED: run_id={summary['run_id']} decision={summary['decision']}")
        return 0

    except Stage1_5HV3CrossRootLiquidityFrictionDiagnosticError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
