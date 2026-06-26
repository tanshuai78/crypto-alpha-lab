import argparse
import json
import sys
from pathlib import Path

from loguru import logger


def parse_args():
    parser = argparse.ArgumentParser(description="Stage 1.5E Review Generator")
    parser.add_argument("--summary", required=True, help="Path to execution_feasibility_audit_summary.json")
    parser.add_argument("--output-review", required=True, help="Path to write the Chinese review markdown")
    return parser.parse_args()


def generate_chinese_review(summary: dict) -> str:
    decision = summary.get("decision", "unknown")
    proven = summary.get("execution_feasibility_proven", False)
    hist_depth_avail = summary.get("historical_orderbook_depth_available", False)
    live_depth_avail = summary.get("live_depth_snapshot_available", False)
    source_status = summary.get("source_smoke_dependency_status", "pending")
    total_events = summary.get("top_level_unique_symbol_event_count", 0)
    depth_coverage = summary.get("historical_depth_coverage", {}) or {}
    mark_index_status = summary.get("mark_index_divergence_status", "not_audited")

    cell_summaries = summary.get("cell_summaries", {})
    blockers = summary.get("blockers", [])
    allowed_action = summary.get("allowed_next_action", "none")

    # Format blockers
    blockers_text = "\n".join([f"- `{b}`" for b in blockers]) if blockers else "无"

    # Format cell summaries
    cells_markdown = ""
    for cell_key, metrics in cell_summaries.items():
        cells_markdown += f"""
### Cell: `{cell_key}`
- **Cell Status:** `{metrics.get('cell_status', 'unknown')}`
- **事件数量 (cell_event_count):** {metrics.get('cell_event_count', 0)}
- **Entry 15m Bar Range (BPS):** Median {metrics.get('median_entry_bar_range_bps')}, P95 {metrics.get('p95_entry_bar_range_bps')}
- **Entry 1h Range (BPS):** Median {metrics.get('median_entry_1h_range_bps')}
- **Entry 4h Range (BPS):** Median {metrics.get('median_entry_4h_range_bps')}
- **Pre-Entry 24h Volume (USDT):** Median {metrics.get('median_pre_entry_24h_quote_volume_usdt')}, P05 {metrics.get('p05_pre_entry_24h_quote_volume_usdt')}
- **Quote Volume Pass Rate:** {metrics.get('quote_volume_pass_rate')}
- **Live Spread (BPS):** Median {metrics.get('median_spread_bps_if_live_depth_available') or 'N/A'}
- **Live Slippage (BPS for 500 USDT buy):** Median {metrics.get('median_slippage_bps_for_500usdt_buy_if_live_depth_available') or 'N/A'}
"""

    review_content = f"""# External Signal Shadow Lab Stage 1.5E Execution Feasibility Data Audit Review

## 1. Decision (决策)
- **Top-Level Decision:** `{decision}`
- **execution_feasibility_proven:** `{proven}`
- **Allowed Next Action:** `{allowed_action}`

## 2. Upstream Evidence (上游证据)
- **总唯一事件数量 (top_level_unique_symbol_event_count):** {total_events}
- **候选事件天数 (candidate_event_days):** {summary.get('candidate_event_days', 0)}
- **包含事件的标的数量 (symbols_with_events):** {summary.get('symbols_with_events', 0)}
- **Blockers (阻碍项):**
{blockers_text}

## 3. Cell-Level Historical Proxy Audit (单元格级历史代理审计)
{cells_markdown}

## 4. Historical Orderbook / Depth Evidence (历史订单簿/深度证据)
- **historical_orderbook_depth_available:** `{hist_depth_avail}`
- **historical_depth_file_count:** `{depth_coverage.get('historical_depth_file_count', 0)}`
- **candidate_symbol_overlap_count:** `{depth_coverage.get('candidate_symbol_overlap_count', 0)}`
- **matched_snapshot_count:** `{depth_coverage.get('matched_snapshot_count', 0)}`
- **matched_candidate_event_count:** `{depth_coverage.get('matched_candidate_event_count', 0)}`
- **coverage_reject_reason:** `{depth_coverage.get('coverage_reject_reason', 'none')}`
- **审计结论:** {'历史订单簿深度归档不可用，无法进行历史回测层面的盘口真实成交价核验。' if not hist_depth_avail else '历史订单簿归档可用，已成功完成历史盘口深度审计。'}

## 5. Live Depth Snapshot Evidence (实时深度快照证据)
- **live_depth_snapshot_available:** `{live_depth_avail}`
- **Source Smoke Dependency Status:** `{source_status}`
- **审计结论:** {'未采集到任何实时盘口快照数据。' if not live_depth_avail else '已采集到实时盘口快照数据，成功计算了实时盘口价差与 500 USDT Buy/Sell 估计滑点。'}

## 5.1 Mark / Index Proxy Evidence
- **mark_index_proxy_available:** `{summary.get('mark_index_proxy_available', False)}`
- **mark_index_divergence_status:** `{mark_index_status}`
- **审计结论:** 当前版本未接入历史 `markPriceKlines` / `indexPriceKlines` / `premiumIndexKlines`，不得声称已完成 mark/index divergence 审计。

## 6. Why close-price replay is still not execution proof (为什么收盘价回放仍然不能证明可执行性)
即使历史 Kline 代理指标与交易量通过审计，收盘价 (close price) 仍然不能作为真实市场成交价的证明。这是因为：
1. **盘口变薄与瞬间重定价风险:** 新币上线或极端事件触发时，盘口买卖价差 (bid/ask spread) 可能极度变宽，单笔 500 USDT 的市价订单就可能产生超过 100 bps 的滑点。
2. **缺乏限价单撮合时间证据:** 真实执行多为 Maker-first，收盘价回放假定可以在 Close Price 瞬间以 100% 填充率成交，忽略了单腿敞口时间和撤单退回逻辑。

## 7. Safety Boundaries (安全边界约束)
- **paper_trading_allowed:** `{summary.get('paper_trading_allowed', False)}`
- **live_trading_allowed:** `{summary.get('live_trading_allowed', False)}`
- **execution_engine_allowed:** `{summary.get('execution_engine_allowed', False)}`
- **alpha_interpretation_allowed:** `{summary.get('alpha_interpretation_allowed', False)}`

## 8. Allowed Next Action (允许的下一步行动)
- **当前决策:** `{decision}`
- **允许行动:** `{allowed_action}`
- **说明:** {'由于决策为 ready_for_live_depth_observer，下一步被允许设计并实现 Stage 1.5F 实时盘口深度采集模块，以持续收集 live events 数据。' if decision == 'stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer' else '当前尚未满足进入 Stage 1.5F 的条件。请检查并修复相关 Blockers。'}
"""
    return review_content


def main() -> int:
    args = parse_args()
    summary_path = Path(args.summary)
    review_path = Path(args.output_review)

    if not summary_path.exists():
        logger.error(f"Summary file not found: {summary_path}")
        return 1

    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to parse summary file: {e}")
        return 1

    review_text = generate_chinese_review(summary_data)

    # Write output
    review_path.parent.mkdir(parents=True, exist_ok=True)
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(review_text)

    logger.info(f"Generated review at {review_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
