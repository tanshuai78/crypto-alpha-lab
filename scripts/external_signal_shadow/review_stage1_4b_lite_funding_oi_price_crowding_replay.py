from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 1.4B-Lite Crowding-Only Replay Review Generator")
    parser.add_argument("--summary", required=True, help="Path to summary JSON file")
    parser.add_argument("--output-review", required=True, help="Path to write MD review output")

    args = parser.parse_args(argv)

    if not os.path.exists(args.summary):
        print(f"Error: Summary file {args.summary} does not exist.", file=sys.stderr)
        return 1

    try:
        with open(args.summary, "r", encoding="utf-8") as f:
            summary = json.load(f)
    except Exception as e:
        print(f"Error parsing summary file: {e}", file=sys.stderr)
        return 1

    decision = summary.get("decision", "unknown")
    next_action = summary.get("next_action", "unknown")
    liquidation_used = summary.get("liquidation_used", False)
    signed_replay_only = summary.get("signed_replay_only", True)
    liquidation_missing_leg_remains_unresolved = summary.get("liquidation_missing_leg_remains_unresolved", True)
    paper_trading_allowed = summary.get("paper_trading_allowed", False)
    live_trading_allowed = summary.get("live_trading_allowed", False)
    execution_intent_allowed = summary.get("execution_intent_allowed", False)

    candidates = summary.get("candidates", {})

    lines = [
        "# External Signal Shadow Lab Stage 1.4B-Lite Crowding-Only Replay Review",
        "",
        "## 0. 重要安全与审计边界声明",
        "",
        "> [!IMPORTANT]",
        f"- **是否使用清算触发条件 (liquidation_used)**: `{str(liquidation_used).lower()}`",
        f"- **是否属于仅 signed replay (signed_replay_only)**: `{str(signed_replay_only).lower()}`",
        f"- **清算缺失腿是否仍未解决 (liquidation_missing_leg_remains_unresolved)**: `{str(liquidation_missing_leg_remains_unresolved).lower()}`",
        f"- **是否允许进行 composite signal 判定 (stage1_4b_full_composite_allowed)**: `{str(summary.get('stage1_4b_full_composite_allowed', False)).lower()}`",
        f"- **是否允许执行意图 (execution_intent_allowed)**: `{str(execution_intent_allowed).lower()}`",
        f"- **是否允许 paper trading (paper_trading_allowed)**: `{str(paper_trading_allowed).lower()}`",
        f"- **是否允许 live trading (live_trading_allowed)**: `{str(live_trading_allowed).lower()}`",
        "",
        "根据 L0 资金安全规则及 L1 工程流程，本模块被严格定义为 **diagnostic-only** 仅诊断分支。以下为核心审计结论与边界约束：",
        "1. **B-Lite 失败不代表复合条件失败 (B-Lite fail != full composite fail)**：由于本分支不包含清算(liquidation)过滤，事件的信噪比较低。如果本分支评估为 `failed` 或 `weak`，仅表示纯拥挤因子(crowding-only)无独立超额收益，不代表未来加入清算过滤后的 `full composite` 分支也必定失败。",
        "2. **B-Lite 成功不代表策略可上线 (B-Lite pass != strategy ready)**：本分支仅做 diagnostic signed replay。即使表现为 `promising`，也绝不意味着策略可用于实盘交易。",
        "3. **signed short replay 不代表空头策略执行意图**：针对空头(short)事件的 signed replay 仅为了数据诊断和参数对称性校验，在未经过借贷可行性与保证金风控审计前，严禁开启任何实盘空头交易 (`short_execution_intent_allowed = false`)。",
        "",
        "## 1. 顶层决策与行动建议",
        "",
        f"- **诊断结论 (Decision)**: `{decision}`",
        f"- **下一步行动 (Next Action)**: `{next_action}`",
        f"- **是否为 Fixture Smoketest Run**: `{str(summary.get('fixture_run', False)).lower()}`",
        f"- **研究结论是否真实有效 (research_result_valid)**: `{str(summary.get('research_result_valid', False)).lower()}`",
        "",
    ]

    if summary.get("fixture_run", False):
        lines.extend([
            "> [!WARNING]",
            "> 当前报告来自 fixture smoke run，仅证明 B-Lite 管线可运行。",
            "> 它不能证明 funding / OI / price crowding 方向真实失败，也不能作为研究级证据。",
            "",
        ])

    lines.extend([
        "## 2. 候选事件统计与 Replay 表现 (Per Candidate Family)",
        "",
    ])

    for name, cand in candidates.items():
        median_net_return = cand.get("median_net_return_bps", 0.0)
        random_baseline = cand.get("random_baseline_median_bps", 0.0)
        price_move_baseline = cand.get("price_move_baseline_median_bps", 0.0)
        excess_vs_random = median_net_return - random_baseline

        lines.extend([
            f"### 候选类别: `{name}`",
            "",
            f"- **事件总数 (event_count)**: `{cand.get('event_count', 0)}`",
            f"- **覆盖天数 (event_days)**: `{cand.get('event_days', 0)}` 天",
            f"- **涉及币种数量 (symbols_count)**: `{cand.get('symbols_count', 0)}`",
            f"- **Replay 中位数净收益 (median_net_return_bps)**: `{median_net_return:+.2f} bps` (扣除 50bps 摩擦)",
            f"- **Symbol-Hour 匹配随机基准中位数 (random_baseline_median_bps)**: `{random_baseline:+.2f} bps`",
            f"- **1h 价格波动基准中位数 (price_move_baseline_median_bps)**: `{price_move_baseline:+.2f} bps`",
            f"- **相比随机基准超额收益 (excess_vs_random)**: `{excess_vs_random:+.2f} bps`",
            f"- **集中度/Top 5 正收益事件毛利占比 (top_5_positive_events_gross_profit_share)**: `{cand.get('top_5_positive_events_gross_profit_share', 0.0):.2%}`",
            f"- **单币种最大事件占比 (max_single_symbol_event_share)**: `{cand.get('max_single_symbol_event_share', 0.0):.2%}`",
            f"- **单日最大事件占比 (max_single_day_event_share)**: `{cand.get('max_single_day_event_share', 0.0):.2%}`",
            f"- **诊断决策 (decision)**: `{cand.get('decision', 'unknown')}`",
            f"- **当前阻碍项 (blocker)**: `{cand.get('blocker') or 'None'}`",
            "",
        ])

    lines.extend([
        "## 3. 全局统计与拥挤度集中度审查",
        "",
        f"- **全局事件总数 (total_events)**: `{summary.get('total_events', 0)}`",
        f"- **全局覆盖天数 (total_days)**: `{summary.get('total_days', 0)}` 天",
        f"- **全局涉及币种数 (total_symbols)**: `{summary.get('total_symbols', 0)}`",
        f"- **全局单币种最大事件占比 (max_single_symbol_event_share)**: `{summary.get('max_single_symbol_event_share', 0.0):.2%}`",
        f"- **全局单日最大事件占比 (max_single_day_event_share)**: `{summary.get('max_single_day_event_share', 0.0):.2%}`",
        f"- **全局 Top 5 正利润事件占比 (top_5_positive_events_gross_profit_share)**: `{summary.get('top_5_positive_events_gross_profit_share', 0.0):.2%}`",
        f"- **全局 Top 5 绝对盈亏占比 (top_5_abs_pnl_share)**: `{summary.get('top_5_abs_pnl_share', 0.0):.2%}`",
        "",
        "---",
        "*Report generated by Antigravity Stage 1.4B-Lite Replay Pipeline.*",
    ])

    os.makedirs(os.path.dirname(os.path.abspath(args.output_review)), exist_ok=True)
    with open(args.output_review, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Review successfully written to {args.output_review}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
