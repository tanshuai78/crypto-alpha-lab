import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary",
        type=str,
        default="data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json",
    )
    parser.add_argument(
        "--output-review",
        type=str,
        default="docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md",
    )

    args = parser.parse_args()

    summary_path = Path(args.summary)
    review_path = Path(args.output_review)

    if not summary_path.exists():
        print(f"Error: summary file not found: {summary_path}")
        return 1

    with open(summary_path, "r", encoding="utf-8") as f:
        s = json.load(f)

    decision = s.get("decision", "unknown")
    event_detection_validated = s.get("event_detection_validated", False)
    research_result_valid = s.get("research_result_valid", False)
    blockers = s.get("blockers", [])
    poll_count = s.get("poll_count", 0)
    observation_hours = s.get("observation_hours", 0.0)
    fixture_run = s.get("fixture_run", False)
    debug_short_run = s.get("debug_short_run", False)
    new_futures_launch_event_count = s.get("new_futures_launch_event_count", 0)
    raw_futures_launch_article_count = s.get("raw_futures_launch_article_count", new_futures_launch_event_count)
    symbol_parsed_event_count = s.get("symbol_parsed_event_count", new_futures_launch_event_count)
    symbol_parse_failed_count = s.get("symbol_parse_failed_count", 0)
    deduped_new_event_count = s.get("deduped_new_event_count", new_futures_launch_event_count)
    paper_trading_allowed = s.get("paper_trading_allowed", False)
    live_trading_allowed = s.get("live_trading_allowed", False)
    execution_engine_allowed = s.get("execution_engine_allowed", False)
    alpha_interpretation_allowed = s.get("alpha_interpretation_allowed", False)

    upstream_passed = "通过"
    if "upstream_evidence_missing_or_invalid" in blockers or not s.get(
        "decision"
    ) != "stage1_5d_smoke_invalid":
        # Check if decision is invalid or has upstream evidence blocker
        if (
            "upstream_evidence_missing_or_invalid" in blockers
            or decision == "stage1_5d_smoke_invalid"
        ):
            upstream_passed = "未通过"

    next_action_str = "继续保持 shadow 观察或排查 polling/upstream 错误"
    if (
        decision == "stage1_5d_event_detection_passed"
        or decision == "stage1_5d_operational_pass_event_detection_unvalidated"
    ):
        next_action_str = "允许进入 Stage 2 或下一阶段评估"

    md_content = f"""# Stage 1.5D Live Event-Source Smoke Collector Review

## Decision
- 决策: {decision}
- 是否成功验证事件检测 (event_detection_validated): {event_detection_validated}
- 是否符合研究结论 (research_result_valid): {research_result_valid}

## Upstream Evidence Gate
- 上游证据验证结果: {upstream_passed}
- 异常阻碍器 (blockers): {blockers}

## Polling Health
- 轮询次数 (poll_count): {poll_count}
- 运行小时数 (observation_hours): {observation_hours:.4f}h
- 是否为 Fixture 运行 (fixture_run): {fixture_run}
- 是否为 Short Debug 运行 (debug_short_run): {debug_short_run}

## Event Detection
- 检测到新的合约上线事件数量: {new_futures_launch_event_count}
- 原始 futures launch 文章计数 (raw_futures_launch_article_count): {raw_futures_launch_article_count}
- 成功解析 symbol 的事件计数 (symbol_parsed_event_count): {symbol_parsed_event_count}
- symbol 解析失败事件计数 (symbol_parse_failed_count): {symbol_parse_failed_count}
- 跨 poll 去重后的新事件计数 (deduped_new_event_count): {deduped_new_event_count}

## First Futures Bar Observation
- 对首个期货 K 线 (first futures bar) 的观察状态记录: {"已观察到首个 K 线" if decision == "stage1_5d_event_detection_passed" else "观察进行中或尚未检测到事件"}

## Safety Boundaries
- 是否允许模拟交易 (paper_trading_allowed): {paper_trading_allowed}
- 是否允许实盘交易 (live_trading_allowed): {live_trading_allowed}
- 是否允许执行引擎启动 (execution_engine_allowed): {execution_engine_allowed}
- 是否允许 Alpha 解释 (alpha_interpretation_allowed): {alpha_interpretation_allowed}

## Allowed Next Action
- 下一步允许动作: {next_action_str}
"""

    review_path.parent.mkdir(parents=True, exist_ok=True)
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(md_content.strip() + "\n")

    print(f"Review written to {review_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
