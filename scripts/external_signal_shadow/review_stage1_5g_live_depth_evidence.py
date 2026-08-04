#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    build_stage1_5g_review_summary,
    generate_stage1_5g_chinese_review,
    load_stage1_5g_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1.5G Live Depth Evidence Reviewer")
    parser.add_argument(
        "--stage1-5f-output-root",
        required=True,
        help="Path to Stage 1.5F output directory",
    )
    parser.add_argument(
        "--output-root",
        help="Directory to write review outputs (default: data/external_signal_shadow/stage1_5g/reviews/<UTC_RUN_ID>/)",
    )
    parser.add_argument(
        "--output-summary",
        help="Explicit path to output JSON summary file",
    )
    parser.add_argument(
        "--output-review",
        help="Explicit path to output markdown review file",
    )

    args = parser.parse_args()

    stage1_5f_root = Path(args.stage1_5f_output_root)
    if not stage1_5f_root.is_dir():
        print(f"Error: Stage 1.5F output root directory not found: {stage1_5f_root}", file=sys.stderr)
        return 1

    # Determine outputs
    utc_now = datetime.now(timezone.utc)
    run_id = utc_now.strftime("%Y%m%dT%H%M%SZ")
    today_str = utc_now.strftime("%Y-%m-%d")

    if args.output_root:
        out_root = Path(args.output_root)
    else:
        out_root = Path(f"data/external_signal_shadow/stage1_5g/reviews/{run_id}")

    if args.output_summary:
        summary_path = Path(args.output_summary)
    else:
        summary_path = out_root / "stage1_5g_live_depth_evidence_review_summary.json"

    if args.output_review:
        review_path = Path(args.output_review)
    else:
        review_path = Path(f"docs/reviews/{today_str}-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md")

    # Load bundle
    bundle = load_stage1_5g_inputs(stage1_5f_root)

    # Build review summary
    summary = build_stage1_5g_review_summary(
        summary=bundle.summary,
        watermark=bundle.watermark,
        states=bundle.states,
        accepted_events=bundle.accepted_events,
        snapshots=bundle.snapshots,
        request_manifest_rows=bundle.request_manifest_rows,
        output_root=stage1_5f_root,
        loader_blockers=bundle.loader_blockers,
        review_output_root=out_root,
    )

    # Add parse errors and line counts if loaded
    summary["parse_error_count"] = bundle.parse_error_count
    summary["total_jsonl_line_count"] = bundle.total_jsonl_line_count

    # Create directories
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON summary
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    # Write Markdown review
    review_content = generate_stage1_5g_chinese_review(summary)
    with open(review_path, "w", encoding="utf-8") as fh:
        fh.write(review_content + "\n")


    print(f"Stage 1.5G review summary written to: {summary_path}")
    print(f"Stage 1.5G markdown review written to: {review_path}")
    print(f"Decision: {summary['decision']}")
    print(f"Allowed next action: {summary['allowed_next_action']}")

    # If missing summary or critical loader blocks exist, exit with code 1
    if "missing_or_unreadable_summary" in summary.get("blockers", []):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
