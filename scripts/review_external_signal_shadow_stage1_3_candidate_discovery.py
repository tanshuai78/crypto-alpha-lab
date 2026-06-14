from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


def _candidate_table(summary: dict) -> str:
    rows = []
    for item in summary.get("candidate_results", []):
        rows.append(
            "| {name} | {count} | {decision} | {blocker} | {symbols} | {days} | {excess} | {median} | {tail} | {top5} |".format(
                name=item.get("candidate_name"),
                count=item.get("event_count"),
                decision=item.get("candidate_decision"),
                blocker=item.get("primary_blocker"),
                symbols=item.get("symbols_with_events"),
                days=item.get("event_days"),
                excess=item.get("baseline_excess_net_bps"),
                median=item.get("median_net_return_after_50bps"),
                tail=item.get("left_tail_p05_after_50bps_vs_baseline_bps"),
                top5=item.get("top_5_positive_events_gross_profit_share"),
            )
        )
    if not rows:
        return "无候选结果。"
    header = "| candidate | events | decision | blocker | symbols | days | excess_bps | median_50bps | left_tail_vs_baseline | top5_profit_share |"
    sep = "|---|---:|---|---|---:|---:|---:|---:|---:|---:|"
    return "\n".join([header, sep, *rows])


def _render(summary: dict) -> str:
    next_action = summary.get("next_action")
    if next_action == "stop_gate_ticker_direction":
        action_cn = "停止 Gate ticker snapshot 派生方向"
    elif next_action == "proceed_to_24h_live_smoke_design":
        action_cn = "只允许写 24h live smoke design，不允许 paper/live"
    elif next_action == "run_real_historical_bars_replay":
        action_cn = "运行真实历史 bars replay"
    else:
        action_cn = "仅允许一次性修订候选定义或停止"
    fixture_note = "本 review 基于 fixture 数据，不能推出信号有效性结论，只证明 pipeline 可运行。" if summary.get("fixture_run") else "本 review 基于历史 bars 输入；是否 research-valid 取决于 coverage/history_days。"
    return f"""# External Signal Shadow Lab Stage 1.3 Candidate Signal Discovery Review

## 1. 结论

- decision: `{summary.get('decision')}`
- next_action: `{next_action}`
- 中文动作：{action_cn}
- fixture_run: `{summary.get('fixture_run')}`
- research_result_valid: `{summary.get('research_result_valid')}`

{fixture_note}

## 2. 安全边界

- 不允许 alpha interpretation: `{summary.get('alpha_interpretation_allowed') is False}`
- 不允许扩 collector: `{summary.get('collector_expansion_allowed') is False}`
- 不要求立即 live shadow: `{summary.get('live_shadow_required_now') is False}`

## 3. 数据 venue

- historical_venue: `{summary.get('historical_venue')}`
- venue_proxy_used: `{summary.get('venue_proxy_used')}`

## 4. 候选结果

{_candidate_table(summary)}

## 5. 解释边界

本 review 不能推出任何实盘、paper trading 或自动交易结论。Stage 1.3 只判断预注册候选事件是否值得进入下一阶段研究。
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Stage 1.3 candidate discovery review")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    summary = json.loads(Path(args.summary).read_text())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
