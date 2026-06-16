#!/usr/bin/env python3
"""
scripts/external_signal_shadow/review_stage1_4a2_vendor_liquidation_data_feasibility.py
"""
import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 1.4A.2 Chinese Review Generator")
    parser.add_argument("--summary", required=True, help="Path to summary JSON")
    parser.add_argument("--output-review", required=True, help="Path to output markdown review")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    # Load summary
    try:
        with open(args.summary, "r", encoding="utf-8") as f:
            summary = json.load(f)
    except Exception as e:
        print(f"Error loading summary: {e}", file=sys.stderr)
        return 1

    # Check if docs-only
    decisions = summary.get("vendor_decisions", [])
    evidence_levels = []
    for d in decisions:
        if "evidence_level" in d:
            evidence_levels.append(d["evidence_level"])
    for a in summary.get("vendor_audits", []):
        if "evidence_level" in a:
            evidence_levels.append(a["evidence_level"])

    is_docs_only = len(evidence_levels) > 0 and all(el in {"marketing_page", "official_api_docs"} for el in evidence_levels)


    # Render parts
    decision_str = "可行 (Feasible)" if summary.get("decision") == "vendor_liquidation_source_feasible" else "不可行/降级 (Degraded)"

    # 1. Title & Conclusion
    markdown = []
    markdown.append("# External Signal Shadow Lab Stage 1.4A.2 Vendor Liquidation Data Feasibility Review\n")
    markdown.append("## 1. 结论")
    markdown.append(f"- **Feasibility Status**: {decision_str}")
    markdown.append(f"- **Primary Blocker**: {summary.get('primary_blocker')}")
    markdown.append(f"- **Best Vendor**: {summary.get('best_vendor')}")
    markdown.append(f"- **Lowest Cost Usable Vendor**: {summary.get('lowest_cost_usable_vendor')}")
    markdown.append(f"- **Highest Data Quality Vendor**: {summary.get('highest_data_quality_vendor')}\n")

    # 2. What it proves/does not prove
    markdown.append("## 2. 本轮能证明什么 / 不能证明什么")
    if is_docs_only:
        markdown.append("- **Important**: **this is docs-only feasibility smoke**")
        markdown.append("- **不能证明 vendor liquidation source 可用** (Docs-only verification is insufficient to prove data tape feasibility without inspecting raw rows).")
        markdown.append("- **Next Action**: request_sample_or_trial to secure sample exports.")
    else:
        markdown.append("- 本轮通过审计本地 vendor 提供的 sample 文件，验证了数据的 schema 兼容性、历史覆盖率及精度。")
        if summary.get("decision") == "vendor_liquidation_source_feasible":
            markdown.append("- **能证明**: 目标 vendor 已经通过 Stage 1.4A.2 的 sample-first 可行性审计，可以进入 `Stage 1.4A.3 vendor sample parser plan`。")
            markdown.append("- **不能推出**: 这不等于 Stage 1.4B composite replay 已开放，也不等于 liquidation alpha 已被验证。")
        else:
            markdown.append("- **不能证明**: 尚未找到在合规、成本和覆盖周期上完全满足 Stage 1.4B 的数据源。")
    markdown.append("")

    # 3. Per-Vendor Audit Table
    markdown.append("## 3. Per-Vendor Audit Table\n")
    markdown.append("| Vendor | Blocker | Decision | Next Action |")
    markdown.append("|---|---|---|---|")
    for d in decisions:
        vendor = d.get("vendor", "")
        blocker = d.get("primary_blocker", "None")
        dec = d.get("decision", "")
        act = d.get("next_action", "")
        markdown.append(f"| {vendor} | {blocker} | {dec} | {act} |")
    markdown.append("")

    # 4. Recommended Vendor Order
    markdown.append("## 4. Recommended Vendor Order (recommended_vendor_order)")
    order = summary.get("recommended_vendor_order", [])
    markdown.append("- 推荐的优先级排序如下 (recommended_vendor_order): " + " -> ".join(order))
    markdown.append("")

    # 5. Blockers And Next Actions
    markdown.append("## 5. Blockers And Next Actions")
    for d in decisions:
        if d.get("decision") == "vendor_liquidation_source_degraded":
            markdown.append(f"- **{d.get('vendor')}**: Blocker `{d.get('primary_blocker')}` -> `{d.get('next_action')}`")
    markdown.append("")

    # 6. Safety Boundaries
    markdown.append("## 6. Safety Boundaries")
    markdown.append("根据 L0 金融安全守则，以下执行权限严格禁止/处于锁定状态 (不允许推出)：")
    markdown.append("```text")
    markdown.append(f"purchase_allowed = {str(summary.get('purchase_allowed', False)).lower()}")
    markdown.append(f"paper_trading_allowed = {str(summary.get('paper_trading_allowed', False)).lower()}")
    markdown.append(f"live_trading_allowed = {str(summary.get('live_trading_allowed', False)).lower()}")
    markdown.append(f"alpha_interpretation_allowed = {str(summary.get('alpha_interpretation_allowed', False)).lower()}")
    markdown.append(f"stage1_4b_candidate_replay_allowed = {str(summary.get('stage1_4b_candidate_replay_allowed', False)).lower()}")
    markdown.append("```\n")

    # Write output
    output_review_path = Path(args.output_review)
    output_review_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_review_path, "w", encoding="utf-8") as f:
        f.write("\n".join(markdown))

    return 0


if __name__ == "__main__":
    sys.exit(main())
