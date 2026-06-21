import argparse
import json
import os
import sys
from typing import Sequence, Optional


def main(args: Optional[Sequence[str]] = None) -> None:
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Stage 1.4E Deleveraging Proxy Review Generator")
    parser.add_argument("--summary", required=True, help="Path to summary JSON")
    parser.add_argument("--output-review", required=True, help="Path to output markdown review")

    parsed = parser.parse_args(args)

    with open(parsed.summary, "r", encoding="utf-8") as f:
        summary_data = json.load(f)

    # Compile the review report in Chinese markdown
    md = []

    # 1. Title & Header
    md.append("# Stage 1.4E Deleveraging Proxy Sensitivity Review Report")
    md.append("\n> **注意：** 本次运行为 Deleveraging Proxy Sensitivity Review（去杠杆代理信号敏感性审查），旨在评估 `OI Drop + Price Flush` 作为外生事件过滤器的可行性。")
    md.append("> **本项工作绝非 B-Lite 阶段重启 (not B-Lite restart)，不涉及任何实盘或模拟盘交易决策许可。**")

    # Get overall decisions
    c15m = summary_data.get("deleveraging_proxy_15m", {})
    c1h = summary_data.get("deleveraging_proxy_1h", {})

    candidate_summaries = (c15m, c1h)
    valid_candidates = [c for c in candidate_summaries if c.get("research_result_valid", False)]
    invalid_notes = sorted({
        note
        for c in candidate_summaries
        for note in c.get("research_result_notes", [])
    })

    # Determine report top-level conclusion
    overall_conclusion = "未通过"
    if not valid_candidates:
        overall_conclusion = "无有效研究结论 (research_result_valid=false)"
    elif any(c.get("decision") == "deleveraging_proxy_survives_sensitivity_review" for c in valid_candidates):
        overall_conclusion = "通过 (survives)"
    elif any(c.get("decision") == "deleveraging_proxy_inconclusive" for c in valid_candidates):
        overall_conclusion = "条件通过 / 尚无定论 (inconclusive)"

    md.append(f"\n## 最终判定：{overall_conclusion}\n")

    # Render table of results
    md.append("| 候选信号 | 事件总数 | 活跃天数 | 4h Replay Median Bps | 4h Random Baseline Bps | 4h Price Baseline Bps | 审查判定 |")
    md.append("|---|---|---|---|---|---|---|")
    for name, sum_info in (("deleveraging_proxy_15m", c15m), ("deleveraging_proxy_1h", c1h)):
        md.append(
            f"| `{name}` "
            f"| {sum_info.get('events_detected_count', 0)} "
            f"| {sum_info.get('distinct_days_count', 0)} "
            f"| {sum_info.get('replayed_median_bps_4h', 0.0):.2f} "
            f"| {sum_info.get('random_baseline_4h_median_bps', 0.0):.2f} "
            f"| {sum_info.get('price_baseline_4h_median_bps', 0.0):.2f} "
            f"| `{sum_info.get('decision', 'unknown')}` |"
        )

    if invalid_notes:
        md.append("\n### 0. 有效性限制")
        md.append("- `research_result_valid=false`")
        md.append(f"- invalidation_notes: `{', '.join(invalid_notes)}`")
        md.append("- 本轮只能说明真实运行路径闭环，不能作为 Deleveraging Proxy 是否有效的研究结论。")

    # 1. 总体判定
    md.append("\n### 1. 总体判定")
    md.append("评估代理信号（去杠杆代理）在历史中的统计表现。本审查判定该代理信号是否能通过密度门槛及超额表现门槛，从而存活进入 Stage 1.5 外生事件源的过滤器。")

    # 2. 做得对的地方
    md.append("\n### 2. 做得对的地方")
    md.append("- 实现了纯代理信号（`OI drop + price flush`）的隔离评测。")
    md.append("- 严格隔离了 execution / liquidation / vendor 数据，没有任何真实爆仓数据泄露或主观参数调优。")
    md.append("- 运用了 `symbol-hour matched random baseline` 与 `price-only baseline` 双重基准进行检验。")

    # 3. 必须修正的问题
    md.append("\n### 3. 必须修正的问题")
    md.append("本轮为敏感性审查，若存在 `debug_baseline_override_used`（即 trials 未达到 500 次）或 `insufficient_history_duration`（数据历史少于 30 天）或 `data_unsupported`，则 `research_result_valid` 强制设为 `false`。")

    # 4. 参数 / 阈值 / 证据边界审核
    md.append("\n### 4. 参数 / 阈值 / 证据边界审核")
    md.append("- 15m 价格波动阀值: 2% / OI 下降阀值: -3%")
    md.append("- 1h 价格波动阀值: 3% / OI 下降阀值: -5%")
    md.append("- Cooldown: 15m 候选为 1小时; 1h 候选为 4小时")

    # 5. 建议执行顺序
    md.append("\n### 5. 建议执行顺序")
    if valid_candidates:
        md.append("若存在 `research_result_valid = true` 且 `decision = deleveraging_proxy_survives_sensitivity_review` 的候选，才允许把对应代理参数作为 Stage 1.5 外生事件源过滤器继续检验。")
    else:
        md.append("本轮 `research_result_valid=false`，不允许把 `deleveraging_proxy_15m` 或 `deleveraging_proxy_1h` 带入 Stage 1.5；下一步应先补足历史覆盖或改用外生事件主线。")

    # 6. 最终意见
    md.append("\n### 6. 最终意见")
    md.append("仅在 `research_result_valid = true` 且判定为 `deleveraging_proxy_survives_sensitivity_review` 时，该参数组才被允许在 Stage 1.5 中作为过滤条件。")

    # 7. 数据证据语义风险
    md.append("\n### 7. 数据证据语义风险")
    md.append("- 本项工作**没有使用 (liquidation_used=false)** 真实爆仓流 (forceOrder) 或 vendor 年包数据。")
    md.append("- **Price close** 是价格代理，并非实盘可执行价格 (close_price_proxy_not_fill_price)。")
    md.append("- **OI 数据** 为交易所每5分钟或1小时更新的快照，存在时间对齐误差。")

    # 8. 本轮能证明什么 / 不能证明什么
    md.append("\n### 8. 本轮能证明什么 / 不能证明什么")
    md.append("- **能证明**：在控制了日内时间效应与单纯价格波动后，去杠杆发生后的短时间内（4h内）是否存在统计学上的价格漂移。")
    md.append("- **不能证明**：真实清算爆仓发生后的阿尔法表现。")

    # 9. 禁止从本轮结果推出什么结论
    md.append("\n### 9. 禁止从本轮结果推出什么结论")
    md.append("- **禁止**将 `up_squeeze_deleveraging_proxy` (signed_direction = -1) 误读为具备做空执行意图 (up squeeze signed replay is diagnostic only and not short execution intent)。")
    md.append("- **禁止**因为通过敏感性审查就略过 Stage 1.5 外生事件源筛选而直接设计交易策略。")
    md.append("- **禁止**声称获得了可实盘交易的复合 Alpha (full_composite_claim_allowed=false)。")
    md.append("- **survives** 判定仅允许将其作为 Stage 1.5 外生事件源的过滤器 (survives only permits use as Stage 1.5 external catalyst filter, not a primary signal)。")

    # Write review
    os.makedirs(os.path.dirname(parsed.output_review), exist_ok=True)
    with open(parsed.output_review, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Written Markdown review report to {parsed.output_review}")

if __name__ == "__main__":
    main()
