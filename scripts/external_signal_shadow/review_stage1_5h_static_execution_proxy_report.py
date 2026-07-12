#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import (
    build_stage1_5h_report_summary,
    generate_stage1_5h_chinese_report,
    load_stage1_5h_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1.5H read-only static execution proxy report generator")
    parser.add_argument("--stage1-5g-summary", required=True)
    parser.add_argument("--stage1-5g-quarantine-summary", required=True)
    parser.add_argument("--depth-quality-input-rows", required=True)
    parser.add_argument("--quarantined-invalid-book-rows", required=True)
    parser.add_argument("--governance-review", required=True)
    parser.add_argument("--output-root")
    parser.add_argument("--output-summary")
    parser.add_argument("--output-review")
    args = parser.parse_args()

    utc_now = datetime.now(timezone.utc)
    run_id = utc_now.strftime("%Y%m%dT%H%M%SZ")
    today = utc_now.strftime("%Y-%m-%d")
    out_root = Path(args.output_root) if args.output_root else Path(f"data/external_signal_shadow/stage1_5h/reports/{run_id}")
    summary_path = Path(args.output_summary) if args.output_summary else out_root / "stage1_5h_static_execution_proxy_report_summary.json"
    review_path = Path(args.output_review) if args.output_review else Path(f"docs/reviews/{today}-external-signal-shadow-lab-stage1-5h-static-execution-proxy-report_CN.md")

    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=args.stage1_5g_summary,
        quarantine_summary_path=args.stage1_5g_quarantine_summary,
        depth_quality_input_rows_path=args.depth_quality_input_rows,
        quarantined_invalid_book_rows_path=args.quarantined_invalid_book_rows,
        governance_review_path=args.governance_review,
    )
    if bundle.loader_blockers:
        print(f"Stage 1.5H loader blockers: {bundle.loader_blockers}", file=sys.stderr)
        return 1

    report_summary = build_stage1_5h_report_summary(bundle)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(report_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    if report_summary.get("blockers"):
        print(f"Stage 1.5H report blockers: {report_summary['blockers']}", file=sys.stderr)
        return 1

    if report_summary.get("decision") == "stage1_5h_input_rejected":
        # Governance failed or some validation blocker, do not write the Markdown report
        return 1

    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(generate_stage1_5h_chinese_report(report_summary) + "\n", encoding="utf-8")

    print(f"Stage 1.5H report summary written to: {summary_path}")
    print(f"Stage 1.5H markdown report written to: {review_path}")
    print(f"Decision: {report_summary['decision']}")
    print(f"Allowed next action: {report_summary['allowed_next_action']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
