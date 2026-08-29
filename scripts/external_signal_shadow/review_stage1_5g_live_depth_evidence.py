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
    write_stage1_5g_quarantine_artifacts,
    write_stage1_5g_review_manifest,
)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


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

    preserved_v1_root = Path(
        "data/external_signal_shadow/stage1_5g/reviews/20260829T024637Z_local"
    )
    if _is_within(out_root, stage1_5f_root) or _is_within(out_root, preserved_v1_root):
        print("Error: output root overlaps immutable source evidence", file=sys.stderr)
        return 1
    if out_root.exists():
        print(f"Error: output root already exists: {out_root}", file=sys.stderr)
        return 1

    if args.output_summary:
        summary_path = Path(args.output_summary)
    else:
        summary_path = out_root / "stage1_5g_live_depth_evidence_review_summary.json"

    if args.output_review:
        review_path = Path(args.output_review)
    else:
        review_path = out_root / f"{today_str}-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md"

    if not _is_within(summary_path, out_root) or not _is_within(review_path, out_root):
        print("Error: output paths must remain inside fresh output root", file=sys.stderr)
        return 1

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
    )

    # Add parse errors and line counts if loaded
    summary["parse_error_count"] = bundle.parse_error_count
    summary["total_jsonl_line_count"] = bundle.total_jsonl_line_count

    quarantine_result = summary.pop("_stage1_5g_quarantine_result", None)

    # Create directories
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)

    quarantine_summary_path = out_root / "stage1_5g_quarantine_summary.json"
    if quarantine_result is not None:
        write_stage1_5g_quarantine_artifacts(
            out_root,
            quarantine_result,
            summary["quarantine"],
        )

    # Write JSON summary
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)

    # Write Markdown review
    review_content = generate_stage1_5g_chinese_review(summary)
    with open(review_path, "w", encoding="utf-8") as fh:
        fh.write(review_content + "\n")

    # If quarantine artifacts exist, write review manifest
    if quarantine_summary_path.is_file() and (out_root / "quarantined_invalid_book_rows.jsonl").is_file() and (out_root / "depth_quality_input_rows.jsonl").is_file():
        artifact_paths = {
            "summary": summary_path,
            "quarantine_summary": quarantine_summary_path,
            "quarantined_invalid_book_rows": out_root / "quarantined_invalid_book_rows.jsonl",
            "depth_quality_input_rows": out_root / "depth_quality_input_rows.jsonl",
        }
        write_stage1_5g_review_manifest(out_root, summary, artifact_paths)

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
