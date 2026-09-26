"""Stage 1.6F-W2-0 offline CLI runner for exploratory terminal basis diagnostics.

Invariants:
- INV-W20-01 through INV-W20-08.
- Zero network / offline local execution.
- Call order: exact authorities -> admission -> strict reader -> materializer -> reducer -> write -> strict read-back.
- Strictly forbidden to print raw price, OHLC, basis values, returns, or PnL to stdout.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

from src.research.external_signal_shadow.stage1_6f_w2_0_exploratory_terminal_basis_diagnostic import (
    W20AdmissionError,
    W20MaterializationError,
    admit_w2_0_inputs,
    compute_w2_0_exploratory_terminal_basis,
    materialize_verified_w2_rows,
)
from src.research.external_signal_shadow.stage1_6f_w2_0_exploratory_terminal_basis_storage import (
    W20StorageError,
    load_verified_w2_0_bundle,
    write_w2_0_exploratory_bundle,
)
from src.research.external_signal_shadow.stage1_6f_w2_evidence_source import (
    W2EvidenceSourceError,
    load_verified_w2_evidence,
)

# Exact frozen defaults
DEFAULT_W2_0_DESIGN_PATH = "docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-design_CN.md"
DEFAULT_W2_0_DESIGN_SHA = "58f4cf8638b05a1c268578ace0ed8d4c6b8b794daa4d94107e2af349d22862c4"

DEFAULT_W2_0_PLAN_PATH = "docs/plans/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-implementation-plan_CN.md"
DEFAULT_W2_0_PLAN_SHA = "17dc74ee85e66f490460e745e97aa2ec6628baccf9039f69d9e78ed49b0666fe"

DEFAULT_W2_DESIGN_PATH = "docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md"
DEFAULT_W2_DESIGN_SHA = "11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303"

DEFAULT_W2_PLAN_PATH = "docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md"
DEFAULT_W2_PLAN_SHA = "183689a6b786ccd3dce9f74f5d1fc2e9ccc1741d80f243f5724dd3b7de149229"

DEFAULT_W2_NETWORK_AUTH_PATH = "configs/authorizations/network_auth_w2_candidate_run_20260925_001.json"
DEFAULT_W2_NETWORK_AUTH_SHA = "0189fd4a922c87811e25793b62d12d6ba76ad92e60a95236a3fe54f024fa5dbf"

DEFAULT_W2_CANDIDATE_ROOT_PATH = "data/external_signal_shadow/stage1_6f/w2_evidence_candidates/w2_candidate_run_20260925_001"
DEFAULT_W2_CANDIDATE_MANIFEST_SHA = "1bd45df8d27e85b40d30500148575780740c6d089b5700e43c1cbfc22a4a0cea"

DEFAULT_EXTERNAL_AUDIT_PATH = "/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_completion_audit_review.md"
DEFAULT_EXTERNAL_AUDIT_SHA = "1c3051315711b5fb0f80086d7f7dab3639a8ba438a74ab4ec4558ce3180d76f2"

DEFAULT_HISTORICAL_RECEIPT_PATH = "/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_preanalysis_blind_receipt.json"
DEFAULT_HISTORICAL_RECEIPT_SHA = "5f6f1087888e73a0304f91b07d3a8b6ebaf7ca9b7701e4ab4de714dc158e0e25"

EXPECTED_OUTPUT_PARENT_REL = Path("data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage 1.6F-W2-0 Offline Exploratory Terminal Basis Diagnostic Runner",
        add_help=False,
    )
    parser.add_argument("--project-root", default=".", help="Path to project root")
    parser.add_argument("--candidate-root", default=DEFAULT_W2_CANDIDATE_ROOT_PATH, help="Path to W2 candidate root")
    parser.add_argument("--output-root", required=True, help="Relative path to destination W2-0 diagnostic directory")

    parser.add_argument("--w2-0-design-path", default=DEFAULT_W2_0_DESIGN_PATH)
    parser.add_argument("--w2-0-design-sha", default=DEFAULT_W2_0_DESIGN_SHA)
    parser.add_argument("--w2-0-plan-path", default=DEFAULT_W2_0_PLAN_PATH)
    parser.add_argument("--w2-0-plan-sha", default=DEFAULT_W2_0_PLAN_SHA)

    parser.add_argument("--w2-design-path", default=DEFAULT_W2_DESIGN_PATH)
    parser.add_argument("--w2-design-sha", default=DEFAULT_W2_DESIGN_SHA)
    parser.add_argument("--w2-plan-path", default=DEFAULT_W2_PLAN_PATH)
    parser.add_argument("--w2-plan-sha", default=DEFAULT_W2_PLAN_SHA)

    parser.add_argument("--w2-network-auth-path", default=DEFAULT_W2_NETWORK_AUTH_PATH)
    parser.add_argument("--w2-network-auth-sha", default=DEFAULT_W2_NETWORK_AUTH_SHA)

    parser.add_argument("--candidate-manifest-sha", default=DEFAULT_W2_CANDIDATE_MANIFEST_SHA)
    parser.add_argument("--external-audit-path", default=DEFAULT_EXTERNAL_AUDIT_PATH)
    parser.add_argument("--external-audit-sha", default=DEFAULT_EXTERNAL_AUDIT_SHA)
    parser.add_argument("--historical-receipt-path", default=DEFAULT_HISTORICAL_RECEIPT_PATH)
    parser.add_argument("--historical-receipt-sha", default=DEFAULT_HISTORICAL_RECEIPT_SHA)

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    project_root = Path(args.project_root).resolve()
    candidate_root = Path(args.candidate_root)
    if not candidate_root.is_absolute():
        candidate_root = project_root / candidate_root
    candidate_root = candidate_root.resolve()

    raw_output_root = args.output_root
    output_path = Path(raw_output_root)

    # 1. Output root path validation: relative, no dot-dot, exact parent, regex run_id
    if output_path.is_absolute():
        sys.stderr.write(f"STOP=w2_0_output_root_invalid:absolute_path:{raw_output_root}\n")
        return 1
    if ".." in output_path.parts or "." in output_path.parts:
        sys.stderr.write(f"STOP=w2_0_output_root_invalid:dot_dot_alias:{raw_output_root}\n")
        return 1
    if output_path.parent != EXPECTED_OUTPUT_PARENT_REL:
        sys.stderr.write(
            f"STOP=w2_0_output_root_invalid:parent_mismatch:{output_path.parent}!={EXPECTED_OUTPUT_PARENT_REL}\n"
        )
        return 1

    run_id = output_path.name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id):
        sys.stderr.write(f"STOP=w2_0_output_root_invalid:invalid_run_id_format:{run_id}\n")
        return 1

    # Check symlinks along parent components
    curr_component = project_root
    for part in EXPECTED_OUTPUT_PARENT_REL.parts:
        curr_component = curr_component / part
        if curr_component.is_symlink() or os.path.islink(curr_component):
            sys.stderr.write(f"STOP=w2_0_output_root_invalid:symlink_detected:{curr_component}\n")
            return 1

    target_output_root = project_root / output_path
    if target_output_root.is_symlink() or os.path.islink(target_output_root):
        sys.stderr.write(f"STOP=w2_0_output_root_invalid:symlink_detected:{target_output_root}\n")
        return 1
    if target_output_root.exists():
        sys.stderr.write(f"STOP=w2_0_output_root_collision:{target_output_root}\n")
        return 1

    # 2. Path normalization for authority files
    w2_0_design_p = Path(args.w2_0_design_path)
    if not w2_0_design_p.is_absolute():
        w2_0_design_p = project_root / w2_0_design_p

    w2_0_plan_p = Path(args.w2_0_plan_path)
    if not w2_0_plan_p.is_absolute():
        w2_0_plan_p = project_root / w2_0_plan_p

    w2_design_p = Path(args.w2_design_path)
    if not w2_design_p.is_absolute():
        w2_design_p = project_root / w2_design_p

    w2_plan_p = Path(args.w2_plan_path)
    if not w2_plan_p.is_absolute():
        w2_plan_p = project_root / w2_plan_p

    w2_net_auth_p = Path(args.w2_network_auth_path)
    if not w2_net_auth_p.is_absolute():
        w2_net_auth_p = project_root / w2_net_auth_p

    ext_audit_p = Path(args.external_audit_path)
    if not ext_audit_p.is_absolute():
        ext_audit_p = project_root / ext_audit_p

    hist_receipt_p = Path(args.historical_receipt_path)
    if not hist_receipt_p.is_absolute():
        hist_receipt_p = project_root / hist_receipt_p

    # 3. Task 2 Admission gate
    try:
        admission = admit_w2_0_inputs(
            project_root=project_root,
            candidate_root=candidate_root,
            w2_0_design_path=w2_0_design_p,
            w2_0_design_sha=args.w2_0_design_sha,
            w2_0_plan_path=w2_0_plan_p,
            w2_0_plan_sha=args.w2_0_plan_sha,
            w2_design_path=w2_design_p,
            w2_design_sha=args.w2_design_sha,
            w2_plan_path=w2_plan_p,
            w2_plan_sha=args.w2_plan_sha,
            w2_network_auth_path=w2_net_auth_p,
            w2_network_auth_sha=args.w2_network_auth_sha,
            candidate_manifest_sha=args.candidate_manifest_sha,
            external_audit_path=ext_audit_p,
            external_audit_sha=args.external_audit_sha,
            historical_receipt_path=hist_receipt_p,
            historical_receipt_sha=args.historical_receipt_sha,
        )
    except W20AdmissionError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"STOP=w2_0_admission_invalid:{exc}\n")
        return 1

    # 4. Strict reader: load verified W2 candidate evidence
    try:
        verified_w2 = load_verified_w2_evidence(
            project_root=project_root,
            candidate_root=candidate_root,
            approved_design_path=w2_design_p,
            approved_design_sha=args.w2_design_sha,
            approved_plan_path=w2_plan_p,
            approved_plan_sha=args.w2_plan_sha,
            network_authorization_path=w2_net_auth_p,
            network_authorization_sha=args.w2_network_auth_sha,
        )
    except W2EvidenceSourceError as exc:
        sys.stderr.write(f"STOP=w2_0_candidate_root_invalid:{exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"STOP=w2_0_candidate_root_invalid:unexpected:{exc}\n")
        return 1

    # 5. Materialize verified parsed rows
    try:
        verified_rows = materialize_verified_w2_rows(verified_w2=verified_w2)
    except W20MaterializationError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"STOP=w2_0_candidate_row_materialization_invalid:{exc}\n")
        return 1

    # 6. Compute diagnostic result (reducer)
    try:
        diag_result = compute_w2_0_exploratory_terminal_basis(
            verified_w2=verified_w2,
            verified_rows=verified_rows,
            admission=admission,
        )
    except Exception as exc:
        sys.stderr.write(f"STOP=w2_0_diagnostic_computation_failed:{exc}\n")
        return 1

    # 7. Create-exclusive atomic bundle write
    try:
        manifest_path = write_w2_0_exploratory_bundle(
            output_root=target_output_root,
            diagnostic_result=diag_result,
            verified_w2=verified_w2,
            admission=admission,
        )
    except W20StorageError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"STOP=w2_0_bundle_invalid:{exc}\n")
        return 1

    # 8. Strict read-back verification
    try:
        bundle = load_verified_w2_0_bundle(
            output_root=target_output_root,
            project_root=project_root,
        )
    except W20StorageError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"STOP=w2_0_bundle_invalid:strict_readback_failed:{exc}\n")
        return 1

    # 9. Print clean identity/status/counts metadata (strictly no raw price/basis/PnL)
    print(f"run_id: {bundle.bundle_run_id}")
    print(f"outcome_inspection_status: {bundle.outcome_inspection_status}")
    print(f"research_classification: {bundle.research_classification}")
    print("metric_evidence_status:")
    for k, v in sorted(bundle.metric_evidence_status.items()):
        print(f"  {k}: {v}")
    print("conserved_counts:")
    for k, v in sorted(bundle.conserved_counts.items()):
        print(f"  {k}: {v}")
    print(f"manifest_path: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
