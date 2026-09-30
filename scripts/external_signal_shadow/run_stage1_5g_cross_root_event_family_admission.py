from __future__ import annotations

import argparse
import sys

from src.research.external_signal_shadow.stage1_5g_cross_root_event_family_admission import (
    Stage1_5GCrossRootAdmissionError,
    admit_frozen_cross_root_inputs,
    build_cross_root_summary,
    load_verified_cross_root_receipt,
    publish_cross_root_receipt,
    verify_execution_authority,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage 1.5G cross-root event-family admission runner.",
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
        approval_bindings = {
            "approved_design_path": args.approved_design_path,
            "approved_design_sha256": args.approved_design_sha256,
            "approved_plan_path": args.approved_plan_path,
            "approved_plan_sha256": args.approved_plan_sha256,
        }

        # 1. Verify execution authority from baseline dir
        verify_execution_authority(
            execution_baseline_dir=args.execution_baseline_dir,
            supplied_approval_bindings=approval_bindings,
        )

        # 2. Admit frozen inputs
        admitted = admit_frozen_cross_root_inputs()

        # 3. Build summary
        summary = build_cross_root_summary(admitted, run_id=args.run_id)

        # 4. Atomically publish receipt
        final_root = publish_cross_root_receipt(summary, run_id=args.run_id)

        # 5. Strict local reload
        loaded = load_verified_cross_root_receipt(final_root)

        print(f"RECEIPT_PUBLISHED: run_id={loaded['summary']['run_id']} decision={loaded['summary']['decision']}")
        print(f"RECEIPT_ROOT: {final_root}")
        return 0

    except Stage1_5GCrossRootAdmissionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
