#!/usr/bin/env python3
"""
scripts/external_signal_shadow/run_stage1_5g_n3_regime_stratified_admission.py

Narrow CLI runner for Stage 1.5G N=3 Regime-Stratified Admission.
Accepts only the 5 approved authority and run-id flags.
Rejects any ambient override or unexpected arguments.
"""

import argparse
import sys
from pathlib import Path

from src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission import (
    Stage1_5GN3RegimeAdmissionError,
    run_admission,
    verify_execution_authority,
    verify_local_receipt_generation_authority,
)


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Stage 1.5G N=3 Regime-Stratified Admission."
    )
    parser.add_argument("--approved-design-path", required=True)
    parser.add_argument("--approved-design-sha256", required=True)
    parser.add_argument("--approved-plan-path", required=True)
    parser.add_argument("--approved-plan-sha256", required=True)
    parser.add_argument("--run-id", required=True)

    args = parser.parse_args()

    project_root = _get_project_root()

    try:
        # Check authority bindings first
        authority = verify_execution_authority(project_root=project_root)
        if (
            args.approved_design_path != authority["approved_design_path"]
            or args.approved_design_sha256 != authority["approved_design_sha256"]
            or args.approved_plan_path != authority["approved_plan_path"]
            or args.approved_plan_sha256 != authority["approved_plan_sha256"]
        ):
            sys.stderr.write("STOP=approved_authority_mismatch:cli_flag_mismatch\n")
            sys.exit(1)

        # Check local receipt generation authority
        verify_local_receipt_generation_authority(project_root=project_root)

        receipt = run_admission(run_id=args.run_id, project_root=project_root)
        print(f"RECEIPT_PUBLISHED: {receipt['run_id']}")
    except Stage1_5GN3RegimeAdmissionError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
