import argparse
import json
import sys
from pathlib import Path

from src.research.external_signal_shadow.stage1_5b_event_table_loader import (
    assert_stage1_5a_audit_passed,
    load_high_confidence_candidate_rows,
)
from src.research.external_signal_shadow.stage1_5b_event_table_normalizer import (
    build_article_event_rows,
    dataclass_to_json_dict,
    expand_symbol_event_rows,
)
from src.research.external_signal_shadow.stage1_5b_event_table_summary import (
    build_event_table_summary,
)


def main():
    parser = argparse.ArgumentParser(
        description="Run Stage 1.5B Minimal Historical Event Table Builder"
    )
    parser.add_argument(
        "--input-jsonl", required=True, help="Path to high-confidence candidate JSONL"
    )
    parser.add_argument(
        "--stage1-5a-summary", required=True, help="Path to Stage 1.5A summary JSON"
    )
    parser.add_argument(
        "--output-raw-jsonl", required=True, help="Path to output raw article JSONL"
    )
    parser.add_argument(
        "--output-normalized-jsonl", required=True, help="Path to output normalized symbol JSONL"
    )
    parser.add_argument("--output-summary", required=True, help="Path to output summary JSON")

    args = parser.parse_args()

    # Create directories if they do not exist
    Path(args.output_raw_jsonl).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_normalized_jsonl).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_summary).parent.mkdir(parents=True, exist_ok=True)

    # 1. Assert Stage 1.5A passed
    try:
        allowed_event_types = assert_stage1_5a_audit_passed(args.stage1_5a_summary)
        source_audit_passed = True
    except Exception as exc:
        allowed_event_types = set()
        source_audit_passed = False
        print(f"Stage 1.5A audit validation failed: {exc}", file=sys.stderr)

    # 2. Load input rows
    load_failed = False
    load_error_msg = None
    build_failed = False
    build_error_msg = None
    rows = []
    try:
        rows = load_high_confidence_candidate_rows(args.input_jsonl)
    except Exception as exc:
        load_failed = True
        load_error_msg = str(exc)
        print(f"Error loading candidate rows: {exc}", file=sys.stderr)

    # 3. Read audit decisions
    source_audit_decisions = {}
    if source_audit_passed:
        try:
            with open(args.stage1_5a_summary, "r", encoding="utf-8") as f:
                s_data = json.load(f)
                source_audit_decisions = s_data.get("event_type_decisions", {})
        except Exception as exc:
            print(f"Error reading 1.5A summary decisions: {exc}", file=sys.stderr)

    # 4. Normalize and expand
    article_rows = []
    symbol_rows = []
    if not load_failed and source_audit_passed:
        try:
            article_rows = build_article_event_rows(rows, allowed_event_types)
            symbol_rows = expand_symbol_event_rows(article_rows, source_audit_decisions)
        except Exception as exc:
            build_failed = True
            build_error_msg = str(exc)
            print(f"Error building Stage 1.5B event table: {exc}", file=sys.stderr)

    # 5. Build summary
    summary = build_event_table_summary(article_rows, symbol_rows, source_audit_passed)
    if load_failed:
        summary["decision"] = "stage1_5b_event_table_failed"
        summary["blockers"].append("load_failed")
        if load_error_msg:
            summary["blockers"].append(load_error_msg)
    if build_failed:
        summary["decision"] = "stage1_5b_event_table_failed"
        summary["blockers"].append("build_failed")
        if build_error_msg:
            summary["blockers"].append(build_error_msg)

    # 6. Write output files
    # Write raw article JSONL
    with open(args.output_raw_jsonl, "w", encoding="utf-8") as f:
        for r in article_rows:
            f.write(json.dumps(dataclass_to_json_dict(r), ensure_ascii=False) + "\n")

    # Write normalized symbol JSONL
    with open(args.output_normalized_jsonl, "w", encoding="utf-8") as f:
        for r in symbol_rows:
            f.write(json.dumps(dataclass_to_json_dict(r), ensure_ascii=False) + "\n")

    # Write summary JSON
    with open(args.output_summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Stage 1.5B finished. Decision: {summary['decision']}")
    print(f"Article rows written: {len(article_rows)}")
    print(f"Symbol-expanded rows written: {len(symbol_rows)}")
    if summary["decision"] == "stage1_5b_event_table_failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
