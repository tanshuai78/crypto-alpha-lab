"""CLI entrypoint for Stage 1.5J-C Launch Time and Path Feasibility Diagnostic."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from configs.base import RISK_LIVE_TRADING_ENABLED
from research.external_signal_shadow import (
    stage1_5j_c_launch_time_path_feasibility as jc,
)


class _StrictArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises ValueError on usage errors so main() returns RC=2."""

    def error(self, message: str) -> None:
        raise ValueError(message)


def _produce_summary_for_authorized_run(
    *,
    run_id: str,
    artifact_kind: str,
    authority_obj: dict[str, Any],
    protocol_obj: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Load canonical J-A/J-B roots via public strict loaders and compute J-C summary."""
    ja_root, ja_summary, jb_child_rows, exp_univ, exp_sel = (
        jc._load_upstream_ja_and_jb_for_replay(project_root)
    )
    ledger_path = project_root / jc.LEDGER_RELATIVE_PATH
    return jc.compute_stage1_5j_c_summary_from_admitted_inputs(
        run_id=run_id,
        artifact_kind=artifact_kind,
        authority_obj=authority_obj,
        protocol_obj=protocol_obj,
        ja_root=ja_root,
        ja_summary=ja_summary,
        jb_child_rows=jb_child_rows,
        ledger_path=ledger_path,
        project_root=project_root,
        expected_universe_count=exp_univ,
        expected_selected_count=exp_sel,
    )


def _write_and_verify_lifecycle_evidence(
    *,
    auth_dir: Path,
    pub_res: jc.PublishResult,
    authority_obj: dict[str, Any],
) -> None:
    """Write producer_lifecycle_evidence.json and .sha256 sidecar ONLY after PublishResult."""
    if (
        pub_res.publish_terminal != "parent_directory_fsynced"
        or pub_res.producer_returned_success is not True
    ):
        raise jc.Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_lifecycle_evidence_terminal_invalid"
        )

    final_root_path = Path(pub_res.final_root)
    actual_manifest_sha = jc._sha256_file(final_root_path / "manifest.json")
    actual_summary_sha = jc._sha256_file(final_root_path / "summary.json")
    actual_review_sha = jc._sha256_file(final_root_path / "review_CN.md")
    if (
        actual_manifest_sha != pub_res.manifest_sha256
        or actual_summary_sha != pub_res.summary_sha256
        or actual_review_sha != pub_res.review_sha256
    ):
        raise jc.Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_lifecycle_evidence_hash_mismatch"
        )

    ev_dir = auth_dir / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    ev_file = ev_dir / "producer_lifecycle_evidence.json"
    ev_sidecar = ev_dir / "producer_lifecycle_evidence.json.sha256"
    if ev_file.exists() or ev_sidecar.exists():
        raise jc.Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_lifecycle_evidence_already_exists:{ev_file}"
        )

    evidence_obj: dict[str, Any] = {
        "artifact_kind": pub_res.artifact_kind,
        "authorization_release": authority_obj["authorization_release"],
        "design": authority_obj["design"],
        "evidence_schema_version": 1,
        "final_root": pub_res.final_root,
        "manifest_sha256": actual_manifest_sha,
        "operation": pub_res.operation,
        "plan": authority_obj["plan"],
        "producer_returned_success": True,
        "publish_terminal": "parent_directory_fsynced",
        "review_sha256": actual_review_sha,
        "run_authorization": authority_obj["run_authorization"],
        "run_id": pub_res.run_id,
        "summary_sha256": actual_summary_sha,
        "user_receipt_generation_approval": authority_obj[
            "user_receipt_generation_approval"
        ],
    }
    ev_bytes = jc._dump_canonical_json_bytes(evidence_obj)
    ev_sha = jc._sha256_bytes(ev_bytes)
    ev_file.write_bytes(ev_bytes)
    ev_sidecar.write_bytes(
        f"{ev_sha}  producer_lifecycle_evidence.json\n".encode("ascii")
    )
    jc._verify_two_space_sidecar(ev_file, ev_sidecar)


def main(
    argv: list[str] | None = None,
    *,
    _test_authority_root: Path | None = None,
    _test_project_root: Path | None = None,
) -> int:
    """Execute Stage 1.5J-C CLI with strict Custodian release preflight and atomic publication."""
    parser = _StrictArgumentParser(
        prog="run_stage1_5j_c_launch_time_path_feasibility.py",
        description="Run Stage 1.5J-C launch time and path feasibility diagnostic.",
    )
    parser.add_argument(
        "--operation",
        required=True,
        help="Authorized single-use operation name.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Authorized run_id matching stage1_5j_c_launch_time_path_feasibility_YYYYMMDDTHHMMSSZ.",
    )

    try:
        args = parser.parse_args(argv)
    except ValueError as exc:
        sys.stderr.write(f"CLI usage error: {exc}\n")
        return 2

    if RISK_LIVE_TRADING_ENABLED is not False:
        sys.stderr.write("STOP=configs_risk_live_trading_enabled_must_be_false\n")
        return 1

    operation = str(args.operation)
    run_id = str(args.run_id)
    proj = (
        _test_project_root
        if _test_project_root is not None
        else jc.resolve_project_root()
    )

    try:
        plan_seal = jc._make_file_seal(proj, jc.APPROVED_PLAN_RELATIVE_PATH)
        plan_sha = str(plan_seal["sha256"])
        auth_dir = (
            (_test_authority_root / run_id)
            if _test_authority_root is not None
            else (
                proj
                / ".git"
                / "plan-execution"
                / "stage1_5j_c"
                / plan_sha
                / run_id
            )
        )

        # 1. Preflight: verify external user approval + Custodian release and derive run_authorization.json
        derived_auth = jc.verify_and_derive_run_authorization(
            operation=operation,
            run_id=run_id,
            project_root=proj,
            authority_dir=auth_dir,
        )

        artifact_kind = jc.ALLOWED_OPERATIONS[operation]
        output_root_str = str(derived_auth["output_root"])
        output_root = (
            (proj / output_root_str)
            if operation == "offline_time_path_diagnostic_once"
            else Path(output_root_str)
        )

        derived_file = auth_dir / "run_authorization.json"
        derived_bytes = derived_file.read_bytes()
        rel_prefix = f".git/plan-execution/stage1_5j_c/{plan_sha}/{run_id}"
        run_auth_seal = {
            "relative_path": f"{rel_prefix}/run_authorization.json",
            "sha256": jc._sha256_bytes(derived_bytes),
            "size_bytes": len(derived_bytes),
        }

        authority_obj: dict[str, Any] = {
            "authorization_release": derived_auth["authorization_release"],
            "design": derived_auth["design"],
            "input_files": derived_auth["input_files"],
            "plan": derived_auth["plan"],
            "run_authorization": run_auth_seal,
            "source_files": derived_auth["source_files"],
            "user_receipt_generation_approval": derived_auth[
                "user_receipt_generation_approval"
            ],
        }

        protocol_obj = jc.load_and_verify_protocol(
            proj / jc.PROTOCOL_RELATIVE_PATH
        )

        # 2. Produce summary via upstream strict loaders and bounded stream reduction
        summary_obj = _produce_summary_for_authorized_run(
            run_id=run_id,
            artifact_kind=artifact_kind,
            authority_obj=authority_obj,
            protocol_obj=protocol_obj,
            project_root=proj,
        )

        review_str = jc.render_stage1_5j_c_review(summary_obj)
        summary_bytes = jc._dump_canonical_json_bytes(summary_obj)
        review_bytes = review_str.encode("utf-8")
        manifest_obj = jc.build_stage1_5j_c_manifest(
            run_id=run_id,
            artifact_kind=artifact_kind,
            summary_bytes=summary_bytes,
            review_bytes=review_bytes,
        )
        manifest_bytes = jc._dump_canonical_json_bytes(manifest_obj)

        def _pre_publish_drift_check() -> None:
            re_source, re_bundle = jc.compute_source_bundle_seals_and_sha256(proj)
            re_input = jc.compute_input_file_seals(proj)
            if (
                re_source != derived_auth["source_files"]
                or re_bundle != derived_auth["authorized_source_bundle_sha256"]
                or re_input != derived_auth["input_files"]
            ):
                raise jc.Stage1_5JCDiagnosticError(
                    "STOP=stage1_5j_c_authority_mismatch:pre_publish_drift"
                )

        # 3. Atomic publication (PublishResult returned ONLY after parent directory fsync)
        pub_res = jc.publish_stage1_5j_c_receipt_root(
            output_root=output_root,
            run_id=run_id,
            artifact_kind=artifact_kind,
            operation=operation,
            manifest_bytes=manifest_bytes,
            summary_bytes=summary_bytes,
            review_bytes=review_bytes,
            pre_publish_verify_callback=_pre_publish_drift_check,
        )

        # 4. Write producer_lifecycle_evidence.json + sidecar ONLY after PublishResult
        _write_and_verify_lifecycle_evidence(
            auth_dir=auth_dir,
            pub_res=pub_res,
            authority_obj=authority_obj,
        )
        return 0
    except (jc.Stage1_5JCDiagnosticError, Exception) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
