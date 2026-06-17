from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LQ30 Local ForceOrder Snapshot Diagnostic Review Generator")
    parser.add_argument("--summary", required=True, help="Path to summary JSON file")
    parser.add_argument("--output-review", required=True, help="Path to write MD review output")

    args = parser.parse_args(argv)

    if not os.path.exists(args.summary):
        print(f"Error: Summary file {args.summary} does not exist.")
        return 1

    with open(args.summary, "r", encoding="utf-8") as f:
        summary = json.load(f)

    decision = summary.get("decision", "unknown")
    next_action = summary.get("next_action", "unknown")
    truth_level = summary.get("liquidation_source_truth_level", "unknown")
    complete_tape_allowed = summary.get("complete_liquidation_tape_claim_allowed", False)
    full_composite_allowed = summary.get("full_composite_claim_allowed", False)
    alpha_allowed = summary.get("alpha_interpretation_allowed", False)
    paper_allowed = summary.get("paper_trading_allowed", False)
    live_allowed = summary.get("live_trading_allowed", False)

    density = summary.get("density_report", {})
    overlap = summary.get("overlap_report", {})
    imbalance = summary.get("imbalance_distribution", {})
    source_quality = summary.get("source_quality_report", {})

    # Start formatting review in Chinese markdown
    lines = [
        "# External Signal Shadow Lab Stage 1.4A-LQ30 Local ForceOrder Snapshot Diagnostic Review",
        "",
        "## 0. 重要安全与审计边界声明",
        "",
        "> [!IMPORTANT]",
        f"- **数据真实性水平 (truth level)**: `{truth_level}`",
        f"- **是否允许宣称完整清算 tape (complete_liquidation_tape_claim_allowed)**: `{str(complete_tape_allowed).lower()}`",
        f"- **是否允许进行 composite signal 判定 (full_composite_claim_allowed)**: `{str(full_composite_allowed).lower()}`",
        f"- **是否允许进行 alpha 解释 (alpha_interpretation_allowed)**: `{str(alpha_allowed).lower()}`",
        f"- **是否允许 paper trading (paper_trading_allowed)**: `{str(paper_allowed).lower()}`",
        f"- **是否允许 live trading (live_trading_allowed)**: `{str(live_allowed).lower()}`",
        "",
        "根据设计边界，本轮评估属于 **diagnostic-only** 阶段。本地 forceOrder snapshot 仅为清算代理，并非完整的清算流水 tape (not complete tape)，因此不代表真实世界的完整成交清算。",
        "所有清算金额估算使用 `notional = price * quantity` 规则，被明确标记为 lower-bound estimate（保守估计值）。",
        "在分析中，清算方向映射定义如下：`SELL = long liquidation`（多头爆仓），`BUY = short liquidation`（空头爆仓）。",
        "",
        "## 1. 顶层诊断结论",
        "",
        f"- **诊断结论 (Decision)**: `{decision}`",
        f"- **下一步行动 (Next Action)**: `{next_action}`",
        "",
        "## 2. 数据密度与集中度报告 (Density & Concentration)",
        "",
        f"- **清算数据覆盖天数 (liquidation_history_days)**: `{density.get('liquidation_history_days', 0.0)}` 天",
        f"- **有清算事件的币种数量 (symbols_with_events)**: `{density.get('symbols_with_events', 0)}`",
        f"- **有清算事件的独立天数 (event_days)**: `{density.get('event_days', 0)}` 天",
        f"- **单币种最大事件占比 (max_single_symbol_event_share)**: `{density.get('max_single_symbol_event_share', 0.0):.2%}`",
        f"- **单日最大事件占比 (max_single_day_event_share)**: `{density.get('max_single_day_event_share', 0.0):.2%}`",
        f"- **Top 1 日名义价值占比 (top_1_day_notional_share)**: `{density.get('top_1_day_notional_share', 0.0):.2%}`",
        f"- **Top 3 日名义价值占比 (top_3_days_notional_share)**: `{density.get('top_3_days_notional_share', 0.0):.2%}`",
        f"- **Top 1 币种名义价值占比 (top_1_symbol_notional_share)**: `{density.get('top_1_symbol_notional_share', 0.0):.2%}`",
        "",
        "## 3. 多空失衡分布报告 (Imbalance Distribution)",
        "",
        f"- **多头爆仓总金额 (long_liquidation_notional_total)**: `${imbalance.get('long_liquidation_notional_total', 0.0):,.2f}`",
        f"- **空头爆仓总金额 (short_liquidation_notional_total)**: `${imbalance.get('short_liquidation_notional_total', 0.0):,.2f}`",
        f"- **15m 多空比例**: Long `{imbalance.get('long_short_imbalance_distribution_15m', {}).get('long_ratio', 0.5):.2%}` / Short `{imbalance.get('long_short_imbalance_distribution_15m', {}).get('short_ratio', 0.5):.2%}`",
        f"- **1h 多空比例**: Long `{imbalance.get('long_short_imbalance_distribution_1h', {}).get('long_ratio', 0.5):.2%}` / Short `{imbalance.get('long_short_imbalance_distribution_1h', {}).get('short_ratio', 0.5):.2%}`",
        "",
        "## 4. 对齐重叠报告 (Alignment Overlap)",
        "",
    ]

    if overlap.get("alignment_overlap_available"):
        lines.extend([
            "- **对齐是否可用 (alignment_overlap_available)**: `true`",
            f"- **15m 级别对齐窗口数 (data_alignment_overlap_window_count_15m)**: `{overlap.get('data_alignment_overlap_window_count_15m', 0)}`",
            f"- **15m 级别压力条件重叠数 (stress_condition_overlap_window_count_15m)**: `{overlap.get('stress_condition_overlap_window_count_15m', 0)}`",
            f"- **对齐覆盖天数 (data_alignment_overlap_event_days)**: `{overlap.get('data_alignment_overlap_event_days', 0)}` 天",
            f"- **满足压力条件的天数 (stress_condition_overlap_event_days)**: `{overlap.get('stress_condition_overlap_event_days', 0)}` 天",
            f"- **有对齐重叠的币种数量 (symbols_with_alignment_overlap)**: `{overlap.get('symbols_with_alignment_overlap', 0)}`",
            "",
            "### 对齐策略声明 (Alignment Policy)",
            "",
            f"- **Funding rate 对齐方式**: `{overlap.get('alignment_policy', {}).get('funding')}`",
            f"- **Open Interest 对齐方式**: `{overlap.get('alignment_policy', {}).get('oi')}`",
            f"- **Price 对齐方式**: `{overlap.get('alignment_policy', {}).get('price')}`",
        ])
    else:
        lines.extend([
            "- **对齐是否可用 (alignment_overlap_available)**: `false` (alignment unavailable in this run)",
            "- **对齐信息提示**: 此运行为仅清算数据诊断，未传入 funding/OI/price 归档数据，无法校验重叠对齐情况。",
        ])

    lines.extend([
        "",
        "## 5. 采集源质量报告 (source_quality_report)",
        "",
        f"- **原始行数 (raw_row_count)**: `{source_quality.get('raw_row_count', 0)}`",
        f"- **数据覆盖天数 (raw_history_days)**: `{source_quality.get('raw_history_days', 0.0)}` 天",
        f"- **最近24小时事件数 (raw_recent_event_count_24h)**: `{source_quality.get('raw_recent_event_count_24h', 0)}`",
        f"- **去重移除事件数 (duplicate_event_count)**: `{source_quality.get('duplicate_event_count', 0)}`",
        f"- **无效 JSON 行数 (invalid_json_line_count)**: `{source_quality.get('invalid_json_line_count', 0)}`",
        f"- **无效 JSON 行占比 (invalid_json_line_ratio)**: `{source_quality.get('invalid_json_line_ratio', 0.0):.4%}`",
        f"- **预期监测币种数 (expected_symbol_coverage)**: `{source_quality.get('expected_symbol_coverage', 0)}`",
        f"- **实际清算币种数 (actual_symbol_coverage)**: `{source_quality.get('actual_symbol_coverage', 0)}`",
        f"- **断线与重置次数 (rotation_fragment_count)**: `{source_quality.get('rotation_fragment_count', 0)}`",
        f"- **采集器断线时间段是否可校验 (collector_gap_verifiable)**: `{str(source_quality.get('collector_gap_verifiable', False)).lower()}`",
        f"- **Gap 观测备忘 (archive_gap_observations)**: `{source_quality.get('archive_gap_observations')}`",
        "",
        "---",
        "*Report generated by Antigravity diagnostic pipeline.*",
    ])

    os.makedirs(os.path.dirname(os.path.abspath(args.output_review)), exist_ok=True)
    with open(args.output_review, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
