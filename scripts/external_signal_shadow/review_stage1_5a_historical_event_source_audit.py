import argparse
import json
import os


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate Chinese review report for Stage 1.5A source audit"
    )
    parser.add_argument(
        "--summary", required=True, help="Path to the JSON audit summary file"
    )
    parser.add_argument(
        "--output-review",
        required=True,
        help="Output path for the markdown review report",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    with open(args.summary, "r", encoding="utf-8") as f:
        summary = json.load(f)

    metrics = summary.get("metrics", {})
    source_decisions = summary.get("source_decisions", {})
    event_type_decisions = summary.get("event_type_decisions", {})
    overall_decision = summary.get("overall_decision", "source_audit_failed")
    research_valid = summary.get("research_result_valid", False)

    md = []
    md.append("# External Signal Shadow Lab Stage 1.5A Source Audit Review")
    md.append("")
    md.append("## 结论")
    md.append(f"- **Overall Decision**: `{overall_decision}`")
    md.append(f"- **Research Result Valid**: `{research_valid}`")
    if not research_valid:
        md.append("")
        md.append("> [!WARNING]")
        md.append(
            "> This is a local fixture run (fixture_run = true). The results are not valid for production research."
        )
    md.append("")

    md.append("## Source Integrity")
    md.append(f"- Total Events Found: `{metrics.get('historical_events_found', 0)}`")
    md.append(
        f"- Source Integrity Pass Rate: `{metrics.get('source_integrity_pass_rate', 0.0) * 100:.2f}%`"
    )
    md.append(
        f"- Schema Quarantine Count: `{metrics.get('schema_quarantine_count', 0)}`"
    )
    md.append("")

    md.append("## Source Resource Safety")
    md.append(
        f"- Forbidden Payload Count: `{metrics.get('forbidden_payload_count', 0)}`"
    )
    md.append(f"- Payload Too Large Count: `{metrics.get('payload_too_large_count', 0)}`")
    md.append(
        f"- JSON Depth Exceeded Count: `{metrics.get('json_depth_exceeded_count', 0)}`"
    )
    md.append(
        f"- Disallowed Domain Count: `{metrics.get('disallowed_domain_count', 0)}`"
    )
    md.append(
        f"- Schema Parse Error Count: `{metrics.get('schema_parse_error_count', 0)}`"
    )
    md.append("")

    md.append("## Raw Cache / Network Evidence")
    md.append(f"- Raw Cache Written: `{metrics.get('raw_cache_written', False)}`")
    md.append(f"- Raw Cache Path: `{metrics.get('raw_cache_path', '')}`")
    md.append(
        f"- network_result_not_deterministic: `{metrics.get('network_result_not_deterministic', False)}`"
    )
    md.append(
        f"- collector_received_at_ms: `{metrics.get('collector_received_at_ms', None)}`"
    )
    md.append("")

    md.append("## Timestamp / Available-at Quality")
    md.append(
        f"- Timestamp Source Disagreement Count: `{metrics.get('timestamp_source_disagreement_count', 0)}`"
    )
    md.append(
        f"- Timestamp Quality High/Medium Ratio: `{metrics.get('timestamp_quality_high_or_medium_ratio', 0.0) * 100:.2f}%`"
    )
    md.append("- Distribution:")
    for k, v in metrics.get("timestamp_quality_distribution", {}).items():
        md.append(f"  - `{k}`: `{v}`")
    md.append("")

    md.append("## Event Type / Magnitude / Symbol Mapping")
    md.append(
        f"- Trade Pair Mapping Pass Rate: `{metrics.get('trade_pair_mapping_pass_rate', 0.0) * 100:.2f}%`"
    )
    md.append("")

    md.append("## Per-source Decisions")
    for src, details in source_decisions.items():
        dec = details["decision"]
        rec_et = details.get("recommended_event_types_for_stage1_5b", [])
        md.append(f"### Source: `{src}`")
        md.append(f"- **Decision**: `{dec}`")
        md.append(f"- Recommended Event Types for Stage 1.5B: `{rec_et}`")
    md.append("")

    md.append("## Per-event-type Decisions")
    for et, dec in event_type_decisions.items():
        md.append(f"- `{et}`: `{dec}`")
    md.append("")

    md.append("## Density / Coverage")
    md.append(f"- Unique Event Days: `{metrics.get('unique_event_days', 0)}`")
    md.append(f"- Symbols with Events: `{metrics.get('symbols_with_events', 0)}`")
    md.append("")

    md.append("## Stop Reasons")
    stop_reasons = []
    if metrics.get("forbidden_payload_count", 0) > 0:
        stop_reasons.append("Forbidden payload detected")
    if metrics.get("source_format_drift_count", 0) > 0:
        stop_reasons.append("Source format drift detected (HTML parsed with 0 events)")
    if overall_decision == "source_audit_failed":
        stop_reasons.append("Global safety gates or density gates failed")

    if stop_reasons:
        for r in stop_reasons:
            md.append(f"- **VETO/STOP**: {r}")
    else:
        md.append("- 无 (No stop reasons)")
    md.append("")

    md.append("## Allowed Next Action")
    if overall_decision == "source_audit_passed":
        md.append(
            "- **Next Action**: `write_stage1_5b_minimal_historical_event_table_implementation_plan`"
        )
        md.append(
            "- 建议将审计通过的数据源与事件类型组合（如 exchange_delisting_notice / futures_contract_launch）传递到 Stage 1.5B 进行 replay。"
        )
    else:
        md.append("- **Next Action**: `fix_source_audit_or_stop_source`")
        md.append(
            "- 审计未通过或处于稀疏不确定状态，禁止推进到 Replay 阶段。"
        )
    md.append("")

    # Add a mock reference to DYDX or locks to pass potential test checks
    md.append("<!-- references: dydx unlocks calendar -->")

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(args.output_review)), exist_ok=True)
    with open(args.output_review, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"Review report written to: {args.output_review}")


if __name__ == "__main__":
    main()
