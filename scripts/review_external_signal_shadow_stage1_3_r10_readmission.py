#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from research.external_signal_shadow.stage1_3_r10_readmission import (
    APPROVED_DESIGN_PATH,
    APPROVED_DESIGN_SHA256,
    APPROVED_PLAN_PATH,
    APPROVED_PLAN_SHA256,
    DEFAULT_PARENT_DIR,
    build_r10_receipt_dict,
    parse_event_ledger,
    publish_r10_receipt,
    read_historical_manifest_from_git,
    read_structural_bars,
    reduce_r10_readmission,
    verify_authorities,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage 1.3 R10 historical evidence preflight admission check",
        allow_abbrev=False,
    )
    parser.add_argument("--bars-jsonl", required=True, help="Path to raw 15m bars JSONL")
    parser.add_argument(
        "--historical-manifest-git-commit",
        default=None,
        help="Git commit full 40-hex OID for historical evidence manifest",
    )
    parser.add_argument(
        "--historical-manifest-git-path",
        default=None,
        help="Git repo-relative path for historical evidence manifest",
    )
    parser.add_argument(
        "--event-ledger-jsonl",
        default=None,
        help="Path to candidate event ledger JSONL",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Custom run ID matching stage1_3_r10_readmission_YYYYMMDDTHHMMSSZ",
    )
    parser.add_argument(
        "--approved-design-path",
        default=APPROVED_DESIGN_PATH,
        help="Approved design relative path",
    )
    parser.add_argument(
        "--approved-design-sha256",
        default=APPROVED_DESIGN_SHA256,
        help="Approved design SHA-256",
    )
    parser.add_argument(
        "--approved-plan-path",
        default=APPROVED_PLAN_PATH,
        help="Approved plan relative path",
    )
    parser.add_argument(
        "--approved-plan-sha256",
        default=APPROVED_PLAN_SHA256,
        help="Approved plan SHA-256",
    )
    return parser


_GIT_DIR: Path | None = None
_BOUNDARY_COMMIT: str | None = None
_TEST_PARENT_DIR: Path | None = None


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    git_dir = _GIT_DIR or repo_root
    boundary = _BOUNDARY_COMMIT or "b122dc0700446990b43cc6fe9f613bf76bc8025c"
    canonical_parent = _TEST_PARENT_DIR or (repo_root / DEFAULT_PARENT_DIR)

    try:
        # 1. Authority validation
        verify_authorities(
            approved_design_path=args.approved_design_path,
            approved_design_sha256=args.approved_design_sha256,
            approved_plan_path=args.approved_plan_path,
            approved_plan_sha256=args.approved_plan_sha256,
            check_git=True,
            repo_root=repo_root,
            git_dir=git_dir,
            boundary_commit=boundary,
        )

        # 2. Structural bars parsing (args.bars_jsonl opened here only)
        bars_snapshot = read_structural_bars(args.bars_jsonl)

        # 3. Historical manifest admission
        manifest_snapshot = read_historical_manifest_from_git(
            commit_oid=args.historical_manifest_git_commit,
            manifest_path=args.historical_manifest_git_path,
            boundary_commit=boundary,
            repo_root=git_dir,
        )

        # 4. Event ledger parsing
        ledger_snapshot = parse_event_ledger(args.event_ledger_jsonl, bars_snapshot)

        # 5. Reducer
        reduction = reduce_r10_readmission(bars_snapshot, manifest_snapshot, ledger_snapshot)

        # 6. Run ID and Receipt publication
        run_id = args.run_id or f"stage1_3_r10_readmission_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        receipt_dict = build_r10_receipt_dict(run_id, reduction)
        pub_path = publish_r10_receipt(run_id, receipt_dict, parent_dir=canonical_parent)

        print(f"STATUS={reduction.readmission_status}")
        print(f"RUN_ID={run_id}")
        print(f"RECEIPT_PATH={pub_path}")
        return 0

    except Exception as exc:
        msg = str(exc)
        if "STOP=" not in msg:
            msg = f"STOP=stage1_3_r10_readmission_error:{msg}"
        print(msg, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
