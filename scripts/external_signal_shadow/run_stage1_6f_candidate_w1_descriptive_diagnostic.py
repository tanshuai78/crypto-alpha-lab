"""Offline runner for Stage 1.6F candidate admission and W1 descriptive diagnostics.

Invariants: INV-CA01 through INV-CA12.
Zero-permission boundary: RISK_LIVE_TRADING_ENABLED = False.
Strict local path resolution, offline execution, authority verification,
create-exclusive atomic bundle publication, and immediate strict read-back verification.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import (
    bind_candidate_publication_authority,
    bind_verified_candidate_c_authority,
    compute_file_sha256,
    load_verified_candidate_evidence,
)
from src.research.external_signal_shadow.stage1_6f_candidate_w1_descriptive_diagnostic import (
    compute_candidate_w1_descriptive_diagnostic,
)
from src.research.external_signal_shadow.stage1_6f_candidate_w1_diagnostic_storage import (
    load_candidate_w1_bundle,
    write_candidate_w1_bundle,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    verify_c_input,
)

FROZEN_EXPANSION_DESIGN_PATH = (
    "docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md"
)
FROZEN_EXPANSION_DESIGN_SHA = (
    "1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4"
)

FROZEN_EXPANSION_PLAN_PATH = (
    "docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md"
)
FROZEN_EXPANSION_PLAN_SHA = (
    "fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d"
)

FROZEN_ADMISSION_DESIGN_PATH = (
    "docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md"
)
FROZEN_ADMISSION_DESIGN_SHA = (
    "dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097"
)

FROZEN_NETWORK_AUTH_PATH = (
    "configs/authorizations/network_auth_expansion_run_20260917_002.json"
)
FROZEN_NETWORK_AUTH_SHA = (
    "8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6"
)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage 1.6F Candidate Admission & W1 Descriptive Diagnostic Runner",
        add_help=False,
    )
    parser.add_argument("--project-root", required=True, help="Path to project root")
    parser.add_argument("--source-export", required=True, help="Path to source export receipt directory")
    parser.add_argument("--completed-root", required=True, help="Path to completed C audit root directory")
    parser.add_argument("--candidate-root", required=True, help="Path to candidate evidence package root")
    parser.add_argument("--output-root", required=True, help="Relative path to destination W1 diagnostic directory")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        sys.exit(2)

    project_root = Path(args.project_root).resolve()
    source_export = Path(args.source_export).resolve()
    completed_root = Path(args.completed_root).resolve()
    candidate_root = Path(args.candidate_root).resolve()

    raw_output_root = args.output_root
    output_path = Path(raw_output_root)

    # Validate output_root: must be relative, no '..', non-symlink parent, exact parent path
    if output_path.is_absolute():
        sys.stderr.write(f"STOP=candidate_w1_output_root_invalid:absolute_path:{raw_output_root}\n")
        return 1
    if ".." in output_path.parts or "." in output_path.parts:
        sys.stderr.write(f"STOP=candidate_w1_output_root_invalid:dot_dot_alias:{raw_output_root}\n")
        return 1

    expected_rel_parent = Path("data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics")
    if output_path.parent != expected_rel_parent:
        sys.stderr.write(
            f"STOP=candidate_w1_output_root_invalid:parent_mismatch:{output_path.parent}!={expected_rel_parent}\n"
        )
        return 1

    # Check that no component of the expected parent under project_root is a symlink
    curr_component = project_root
    for part in expected_rel_parent.parts:
        curr_component = curr_component / part
        if curr_component.is_symlink() or os.path.islink(curr_component):
            sys.stderr.write(f"STOP=candidate_w1_output_root_invalid:symlink_detected:{curr_component}\n")
            return 1

    run_id = output_path.name
    if not run_id:
        sys.stderr.write("STOP=candidate_w1_output_root_invalid:empty_run_id\n")
        return 1

    raw_output_target = project_root / output_path
    if raw_output_target.is_symlink() or os.path.islink(raw_output_target):
        sys.stderr.write(f"STOP=candidate_w1_output_root_invalid:symlink_detected:{raw_output_target}\n")
        return 1

    expected_parent = (project_root / expected_rel_parent).resolve()
    resolved_output_root = raw_output_target.resolve()

    if resolved_output_root.parent != expected_parent:
        sys.stderr.write(
            f"STOP=candidate_w1_output_root_invalid:parent_mismatch:{resolved_output_root.parent}!={expected_parent}\n"
        )
        return 1

    if raw_output_target.exists() or resolved_output_root.exists():
        sys.stderr.write(f"STOP=candidate_w1_output_run_id_collision:{resolved_output_root}\n")
        return 1

    # 1. Authority recomputation before opening candidate root
    admission_design_p = project_root / FROZEN_ADMISSION_DESIGN_PATH
    if not admission_design_p.is_file():
        sys.stderr.write(f"STOP=approved_authority_mismatch:missing_design:{admission_design_p}\n")
        return 1
    actual_design_sha = compute_file_sha256(admission_design_p)
    if actual_design_sha != FROZEN_ADMISSION_DESIGN_SHA:
        sys.stderr.write(
            f"STOP=approved_authority_mismatch:design_sha_mismatch:{actual_design_sha}!={FROZEN_ADMISSION_DESIGN_SHA}\n"
        )
        return 1

    # 2. Exact-002 candidate evidence admission
    try:
        verified_candidate = load_verified_candidate_evidence(
            project_root=project_root,
            candidate_root=candidate_root,
            approved_design_path=project_root / FROZEN_EXPANSION_DESIGN_PATH,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=project_root / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=project_root / FROZEN_NETWORK_AUTH_PATH,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )
    except Exception as exc:
        sys.stderr.write(f"STOP=candidate_admission_invalid:{exc}\n")
        return 1

    # 3. Upstream C input verification
    try:
        verified_c = verify_c_input(
            project_root=project_root,
            completed_root=completed_root,
            source_export=source_export,
        )
    except Exception as exc:
        sys.stderr.write(f"STOP=upstream_denominator_authority_invalid:{exc}\n")
        return 1

    # 4. Bind candidate C authority
    try:
        c_authority = bind_verified_candidate_c_authority(
            verified_candidate=verified_candidate,
            verified_c=verified_c,
            completed_root=completed_root,
            source_export=source_export,
        )
    except Exception as exc:
        sys.stderr.write(f"STOP=upstream_denominator_authority_invalid:{exc}\n")
        return 1

    # 5. Bind candidate publication authority
    try:
        pub_authority = bind_candidate_publication_authority(
            verified_candidate=verified_candidate,
            verified_c=verified_c,
        )
    except Exception as exc:
        sys.stderr.write(f"STOP=upstream_denominator_authority_invalid:{exc}\n")
        return 1

    # 6. Compute candidate W1 descriptive diagnostic
    try:
        diagnostic_result = compute_candidate_w1_descriptive_diagnostic(
            verified_candidate=verified_candidate,
            verified_c=verified_c,
            c_authority=c_authority,
            publication_authority=pub_authority,
        )
    except Exception as exc:
        sys.stderr.write(f"STOP=candidate_w1_diagnostic_failed:{exc}\n")
        return 1

    # 7. Write candidate W1 bundle atomically
    try:
        manifest_path = write_candidate_w1_bundle(
            output_root=resolved_output_root,
            diagnostic_result=diagnostic_result,
            verified_candidate=verified_candidate,
            verified_c=verified_c,
            approved_design_path=admission_design_p,
            approved_design_sha=FROZEN_ADMISSION_DESIGN_SHA,
        )
    except Exception as exc:
        sys.stderr.write(f"STOP=candidate_w1_storage_failed:{exc}\n")
        return 1

    # 8. Strict read-back verification
    try:
        load_candidate_w1_bundle(output_root=resolved_output_root)
    except Exception as exc:
        sys.stderr.write(f"STOP=candidate_w1_bundle_invalid:{exc}\n")
        return 1

    sys.stdout.write(f"SUCCESS: candidate W1 descriptive diagnostic sealed at {manifest_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
