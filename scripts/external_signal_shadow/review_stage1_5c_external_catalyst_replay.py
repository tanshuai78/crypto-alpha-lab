import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Generate Stage 1.5C Review Document")
    parser.add_argument("--summary", required=True, help="Path to summary JSON file")
    parser.add_argument("--output-review", required=True, help="Path to write markdown review")

    args = parser.parse_args()

    with open(args.summary, "r", encoding="utf-8") as f:
        s = json.load(f)

    # Compile cell summaries
    cell_rows_md = []
    cells = s.get("cell_summaries", {})
    for k, v in cells.items():
        blockers_str = ", ".join(v.get("blockers", [])) or "None"
        cell_rows_md.append(
            f"| {k} | {v.get('cell_decision')} | {v.get('event_count')} | "
            f"{v.get('median_net_return_after_50bps_4h')} | {v.get('baseline_excess_net_bps_4h')} | {blockers_str} |"
        )
    cells_table = "\n".join(cell_rows_md)

    funnel = s.get("coverage_attrition_funnel", {})
    funnel_md = ""
    if funnel:
        funnel_md = f"""
### Coverage Attrition Funnel (价格与流动性过滤漏斗)
- **输入 Stage 1.5B 原始事件数 (Symbol-Events):** {funnel.get("stage1_5b_symbol_events")}
- **允许的事件类型数 (Allowed Event Type Events):** {funnel.get("allowed_event_type_events")}
- **CEX 存在性校验通过数 (Market Pair Existence Verified):** {funnel.get("market_pair_existence_verified_count")}
- **价格覆盖校验通过数 (Price History Coverage Pass):** {funnel.get("price_history_coverage_pass_count")}
- **流动性代理校验通过数 (Liquidity Proxy Pass):** {funnel.get("liquidity_proxy_pass_count")}
- **去重与冷却后候选事件数 (Candidate Count After Cooldown):** {funnel.get("candidate_count_after_cooldown")}
- **参与 Replay 评估的 Primary 样本行数:** {funnel.get("replay_result_primary_rows")}
- **拒绝原因统计 (Reject Reason Counts):** {json.dumps(funnel.get("coverage_reject_reason_counts", {}))}
"""

    top_blockers = ", ".join(s.get("blockers", [])) or "None"

    review_content = f"""# External Signal Shadow Lab Stage 1.5C External Catalyst Replay Review

## 1. 结论与顶层状态 (Conclusion & Top-Level Decision)
- **Top-Level Decision:** `{s.get("top_level_decision")}`
- **Research Result Valid (研究结论有效性):** `{s.get("research_result_valid")}`
- **Baseline Trials Override Used (是否使用了调试次数覆盖):** `{s.get("baseline_trials_override_used", False)}`
- **Promising Cells (有希望的实验组):** {s.get("promising_cells", [])}
- **Top-Level Blockers (全局阻塞原因):** `{top_blockers}`

---

## 2. 价格与流动性过滤漏斗 (Price and Liquidity Funnel)
{funnel_md}

---

## 3. Cell-Level Replay Results (各实验组 Replay 明细)
| Cell Key | Decision | Event Count | Median Net Return (4h, 50bps) | Baseline Excess Bps | Blockers |
|---|---|---|---|---|---|
{cells_table}

---

## 4. 历史基准对比 (Baseline Comparison)
- **Random Baseline Trials (随机基准模拟次数):** {s.get("random_baseline_trials")}
- **Random Baseline Median Net Return (4h, 50bps):** {s.get("random_baseline_median_net_bps_after_50bps_4h")} bps
- **Price Move Baseline Median Net Return (4h, 50bps):** {s.get("price_baseline_median_net_bps_after_50bps_4h")} bps
- **Random Baseline Left Tail (5th percentile):** {s.get("random_baseline_left_tail_p05_after_50bps_4h")} bps

---

## 5. 安全红线与合规披露 (Safety Boundaries & Disclosures)
> [!IMPORTANT]
> **Stage 1.5C research-only constraints:**
> 1. **Stage 1.5C promising does not permit paper/live.** 即使有实验组被判定为 promising，也不允许直接上线实盘 (live) 或模拟盘 (paper)。
> 2. **Stage 1.5C failed does not invalidate external catalyst source audit.** 单个实验组回测失败不代表上游数据源审计结论失效，仅代表当前的被动执行参数在该子组下无法获得正期望。
> 3. **Signed short replay is diagnostic only.** 做空方向的 Replay 纯属诊断性质，不代表实际上有借币、保证金或执行通路。
> 4. **No execution feasibility was proven without orderbook/depth.** 没有配套的订单簿/深度归档数据，任何基于 Close 价格的 Replay 都不算通过执行可行性论证。
> 5. **Delisting replay uses notice_time_available_at; effective_time replay is not implemented.** 退市公告回测仅基于 notice_time_available_at 锚定，尚未实现 effective_time 退市生效日期的回测。
> 6. **A promising cell only allows live event-source smoke collector design, not execution/shadow readiness.** 一个 promising cell 仅允许我们进入 Stage 1.5D 活体事件源收集器设计，不代表任何执行系统已经就绪。

- **paper_trading_allowed:** `{s.get("paper_trading_allowed", False)}`
- **live_trading_allowed:** `{s.get("live_trading_allowed", False)}`
- **alpha_interpretation_allowed:** `{s.get("alpha_interpretation_allowed", False)}`
- **execution_engine_allowed:** `{s.get("execution_engine_allowed", False)}`

---

## 6. 后续行动指南 (Allowed Next Action)
- **Replay Invalid:** 修复数据覆盖、Symbol 映射或价格归档。
- **Replay Completed (No Promising Cells):** 增加更多高可信事件源，或扩大回测价格覆盖面。若全部 cell 回测失败，应考虑停止当前分支或在重试前引入 OKX 数据源。
- **Replay Completed (With Promising Cells):** 允许编写 Stage 1.5D 活体事件源收集器设计方案 (write_stage1_5d_live_event_source_smoke_collector_design)。如果考虑部署 Shadow 观察模式，必须首先编写执行可行性数据审计方案 (write_execution_feasibility_data_audit_plan)。
"""

    Path(args.output_review).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_review, "w", encoding="utf-8") as f:
        f.write(review_content)


if __name__ == "__main__":
    main()
