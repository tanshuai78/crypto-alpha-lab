#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import (
    load_stage1_5h_inputs,
    write_stage1_5h_v2_event_bundle_reports,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 1.5H v2 event-bundle per-symbol read-only report generator"
    )
    parser.add_argument("--stage1-5g-summary", required=True)
    parser.add_argument("--stage1-5g-quarantine-summary", required=True)
    parser.add_argument("--depth-quality-input-rows", required=True)
    parser.add_argument("--quarantined-invalid-book-rows", required=True)
    parser.add_argument("--governance-review", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=args.stage1_5g_summary,
        quarantine_summary_path=args.stage1_5g_quarantine_summary,
        depth_quality_input_rows_path=args.depth_quality_input_rows,
        quarantined_invalid_book_rows_path=args.quarantined_invalid_book_rows,
        governance_review_path=args.governance_review,
    )
    if bundle.loader_blockers:
        print(f"Stage 1.5H v2 loader blockers: {bundle.loader_blockers}", file=sys.stderr)
        return 1

    result = write_stage1_5h_v2_event_bundle_reports(
        bundle=bundle,
        output_root=args.output_root,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("decision") != "stage1_5h_v2_event_bundle_reports_sealed":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
