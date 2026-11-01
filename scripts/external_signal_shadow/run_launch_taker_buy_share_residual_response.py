#!/usr/bin/env python3
"""CLI entrypoint for offline exploratory analysis of launch taker buy share and 15m residual response.

Enforces single-run explicit authorization check and strict output directory collision/symlink
guards BEFORE invoking any upstream strict loader or opening raw archive packages.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

from research.external_signal_shadow.launch_taker_buy_share_residual_response import (
    APPROVED_DESIGN_SHA256,
    APPROVED_PLAN_SHA256,
    J_A_ROOT_RELATIVE_PATH,
    J_A_RUN_ID,
    J_B_ROOT_RELATIVE_PATH,
    J_B_RUN_ID,
    LEDGER_RELATIVE_PATH,
    LEDGER_SHA256,
    ChildResidualResponseResult,
    ExploratoryProtocol,
    TakerBuyShareResearchError,
    build_admitted_ja_context,
    resolve_project_root,
    stream_and_evaluate_admitted_child,
    validate_exploratory_protocol,
    verify_frozen_upstream_identities,
    verify_safe_new_output_dir,
    verify_single_run_authorization,
    verify_v2_ledger_and_select_universe,
    write_exploratory_outputs,
)

FIXED_EXPLORATORY_PROTOCOL = ExploratoryProtocol(
    feature_window_ms=60_000,
    latency_ms=3_000,
    entry_max_wait_ms=1_000,
    hold_horizon_ms=900_000,
    endpoint_max_age_ms=1_000,
)


def _parse_cli_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run single-authorized offline exploratory analysis of launch taker buy share and 15m residual response."
    )
    parser.add_argument(
        "--auth-file",
        required=True,
        help="Path to explicit single-run authorization JSON.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Path to non-existent new output directory outside protected roots.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(
    argv: Sequence[str] | None = None,
    *,
    project_root: Path | None = None,
    ja_loader: Callable[[Path], dict[str, Any]] | None = None,
    jb_loader: Callable[[Path], dict[str, Any]] | None = None,
    extra_protected_paths: Sequence[Path] | None = None,
) -> int:
    try:
        ns = _parse_cli_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        return code if code != 0 else 1

    proj = project_root if project_root is not None else resolve_project_root()
    auth_path = Path(ns.auth_file)
    output_dir = Path(ns.output_dir)
    protected = list(extra_protected_paths) if extra_protected_paths is not None else []

    try:
        validate_exploratory_protocol(FIXED_EXPLORATORY_PROTOCOL)
        # Gate 1 & 2: Verify single-run authorization and safe new output directory BEFORE any loader call
        verify_single_run_authorization(
            auth_file=auth_path,
            expected_output_dir=output_dir,
            project_root=proj,
        )
        verify_safe_new_output_dir(
            output_dir=output_dir,
            protected_paths=protected,
            project_root=proj,
        )

        # Gate 3: Verify frozen upstream file hashes
        verify_frozen_upstream_identities(project_root=proj)

        # Gate 4: Lazy import and invoke public strict loaders
        if ja_loader is None:
            from research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
                load_verified_stage1_5j_a_historical_archive_coverage_root,
            )

            actual_ja_loader = load_verified_stage1_5j_a_historical_archive_coverage_root
        else:
            actual_ja_loader = ja_loader

        if jb_loader is None:
            from research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
                load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
            )

            actual_jb_loader = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root
        else:
            actual_jb_loader = jb_loader

        ja_root = proj / J_A_ROOT_RELATIVE_PATH
        jb_root = proj / J_B_ROOT_RELATIVE_PATH
        ledger_path = proj / LEDGER_RELATIVE_PATH

        ja_summary = actual_ja_loader(ja_root)
        jb_summary = actual_jb_loader(jb_root)

        _universe_rows, selected_rows = verify_v2_ledger_and_select_universe(
            ledger_path=ledger_path,
            jb_child_rows=jb_summary["child_rows"],
            ja_root=ja_root,
            project_root=proj,
        )
        admitted_ctx = build_admitted_ja_context(ja_root, ja_summary)
        jb_by_key = {
            (str(r["source_article_id"]), str(r["symbol"])): r
            for r in jb_summary["child_rows"]
        }

        child_results: list[ChildResidualResponseResult] = []
        for s_row in sorted(
            selected_rows, key=lambda r: (str(r["parent_article_id"]), str(r["symbol"]))
        ):
            pid = str(s_row["parent_article_id"])
            sym = str(s_row["symbol"])
            reg = str(s_row["listing_regime"])
            child_results.append(
                stream_and_evaluate_admitted_child(
                    admitted_ja_context=admitted_ctx,
                    parent_article_id=pid,
                    symbol=sym,
                    listing_regime=reg,
                    jb_child_row=jb_by_key[(pid, sym)],
                    protocol=FIXED_EXPLORATORY_PROTOCOL,
                )
            )

        write_exploratory_outputs(
            output_dir=output_dir,
            protected_paths=protected,
            protocol=FIXED_EXPLORATORY_PROTOCOL,
            child_results=child_results,
            design_sha256=APPROVED_DESIGN_SHA256,
            plan_sha256=APPROVED_PLAN_SHA256,
            ja_run_id=J_A_RUN_ID,
            jb_run_id=J_B_RUN_ID,
            ledger_sha256=LEDGER_SHA256,
            project_root=proj,
        )
    except TakerBuyShareResearchError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"STOP=unexpected_error:{exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
