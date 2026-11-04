#!/usr/bin/env python3
"""CLI entrypoint for offline exploratory analysis of launch open interest and basis.

Enforces single-run explicit authorization check and strict output directory collision/symlink
guards BEFORE invoking any upstream loader or opening raw archive packages.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
    J_A_ROOT_RELATIVE_PATH,
    J_B_ROOT_RELATIVE_PATH,
    LEDGER_RELATIVE_PATH,
    AggTradeRecord,
    KlineBar,
    LaunchOiResearchError,
    OiMetricRecord,
    execute_exploratory_pipeline,
    verify_safe_new_output_dir,
    verify_single_run_authorization,
    verify_v2_ledger_and_select_universe,
)


def _resolve_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _parse_cli_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run single-authorized offline exploratory analysis of launch open interest and basis."
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
    extra_protected_paths: Sequence[Path] | None = None,
    ja_loader: Any | None = None,
    jb_loader: Any | None = None,
    metrics_by_symbol: dict[str, list[OiMetricRecord]] | None = None,
    aggtrades_by_symbol: dict[str, list[AggTradeRecord]] | None = None,
    klines_by_symbol: dict[str, tuple[list[KlineBar], list[KlineBar], str | None]] | None = None,
) -> int:
    try:
        ns = _parse_cli_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        return code if code != 0 else 1

    proj = project_root if project_root is not None else _resolve_project_root()
    auth_path = Path(ns.auth_file)
    output_dir = Path(ns.output_dir)
    protected = list(extra_protected_paths) if extra_protected_paths is not None else []

    try:
        # Gate 1: Authorization check
        auth_data = verify_single_run_authorization(
            auth_file=auth_path,
            expected_output_dir=output_dir,
            project_root=proj,
        )

        # Gate 2: Safe new output directory check (ancestor symlinks & collisions)
        verify_safe_new_output_dir(
            output_dir=output_dir,
            protected_paths=protected,
            project_root=proj,
        )

        # Gate 3: Ledger verification and universe selection
        ledger_path = proj / LEDGER_RELATIVE_PATH
        if not ledger_path.is_file():
            raise LaunchOiResearchError(f"ledger_file_not_found: {ledger_path}")
        selected_children = verify_v2_ledger_and_select_universe(ledger_path)

        # Gate 4: Upstream admission, reduction, and report generation
        ja_root = proj / J_A_ROOT_RELATIVE_PATH
        jb_root = proj / J_B_ROOT_RELATIVE_PATH
        authorized_sources: list[Path] = []
        for key in ["oi_source_relative_path", "kline_source_relative_path"]:
            rel = auth_data.get(key)
            if rel:
                source_p = proj / rel
                if source_p not in authorized_sources:
                    authorized_sources.append(source_p)
        auth_files = auth_data.get("authorized_input_files") or auth_data.get("authorized_files")

        res = execute_exploratory_pipeline(
            selected_children=selected_children,
            ja_root=ja_root,
            jb_root=jb_root,
            output_dir=output_dir,
            project_root=proj,
            ja_loader=ja_loader,
            jb_loader=jb_loader,
            metrics_by_symbol=metrics_by_symbol,
            aggtrades_by_symbol=aggtrades_by_symbol,
            klines_by_symbol=klines_by_symbol,
            sources_dirs=authorized_sources,
            authorized_input_files=auth_files,
        )

        if res.child_complete_count == 0:
            sys.stderr.write(
                "LaunchOiResearchError: research_data_not_connected: 0 complete children reduced from historical archives\n"
            )
            return 1

        return 0
    except LaunchOiResearchError as exc:
        sys.stderr.write(f"LaunchOiResearchError: {exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"UnexpectedError: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
