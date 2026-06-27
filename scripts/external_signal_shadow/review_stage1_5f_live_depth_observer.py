import argparse
import glob
import json
import os
import sys
from pathlib import Path

from loguru import logger


def parse_args():
    parser = argparse.ArgumentParser(description="Stage 1.5F Review Generator")
    parser.add_argument("--summary", required=True, help="Path to live_depth_observer_summary.json")
    parser.add_argument("--output-review", required=True, help="Path to write the Chinese review markdown")
    return parser.parse_args()


def percentile(lst, pct):
    if not lst:
        return None
    sorted_lst = sorted(lst)
    idx = (len(sorted_lst) - 1) * pct
    idx_floor = int(idx)
    idx_ceil = min(idx_floor + 1, len(sorted_lst) - 1)
    weight = idx - idx_floor
    return sorted_lst[idx_floor] * (1.0 - weight) + sorted_lst[idx_ceil] * weight


def format_pct_dist(lst):
    if not lst:
        return "N/A"
    p0 = percentile(lst, 0.0)
    p25 = percentile(lst, 0.25)
    p50 = percentile(lst, 0.50)
    p75 = percentile(lst, 0.75)
    p95 = percentile(lst, 0.95)
    p100 = percentile(lst, 1.0)
    return f"Min: {p0:.2f}, P25: {p25:.2f}, Median: {p50:.2f}, P75: {p75:.2f}, P95: {p95:.2f}, Max: {p100:.2f}"


def format_depth_dist(lst):
    if not lst:
        return "N/A"
    p0 = percentile(lst, 0.0)
    p25 = percentile(lst, 0.25)
    p50 = percentile(lst, 0.50)
    p75 = percentile(lst, 0.75)
    p95 = percentile(lst, 0.95)
    p100 = percentile(lst, 1.0)
    return f"Min: {p0:.2f} USDT, P25: {p25:.2f} USDT, Median: {p50:.2f} USDT, P75: {p75:.2f} USDT, P95: {p95:.2f} USDT, Max: {p100:.2f} USDT"


def load_all_snapshots(output_root: Path) -> list:
    snapshots = []
    pattern = os.path.join(output_root, "depth_snapshots", "**", "*.jsonl")
    for filepath in glob.glob(pattern, recursive=True):
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    snapshots.append(json.loads(line))
                except Exception:
                    pass
    return snapshots


def load_all_states(output_root: Path) -> dict:
    state_file = output_root / "observer_state.jsonl"
    states = {}
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    es_id = row.get("event_symbol_id")
                    if es_id:
                        states[es_id] = row
                except Exception:
                    pass
    return states


def generate_chinese_review(summary: dict, states: dict, snapshots: list) -> str:
    decision = summary.get("decision", "unknown")
    watermark_present = summary.get("watermark_present", False)
    watermark_version = summary.get("watermark_version")
    max_seen = summary.get("max_seen_detected_at_ms", 0)
    pre_watermark_ignored = summary.get("pre_watermark_events_ignored", 0)
    post_watermark_accepted = summary.get("post_watermark_events_accepted", 0)

    active_count = summary.get("active_observation_count", 0)
    completed_count = summary.get("completed_observation_count", 0)
    expired_count = summary.get("expired_observation_count", 0)
    failed_count = summary.get("failed_observation_count", 0)

    success_rate = summary.get("request_success_rate", 1.0)
    total_reqs = summary.get("total_requests_made", 0)
    failed_reqs = summary.get("failed_requests_count", 0)
    consec_errors = summary.get("consecutive_network_errors", 0)
    max_consec_seen = summary.get("max_consecutive_network_errors_seen", 0)

    # Calculate distributions
    spreads = [s["spread_bps"] for s in snapshots if s.get("spread_bps") is not None]
    buy_slippages = [s["buy_slippage_bps"] for s in snapshots if s.get("buy_slippage_bps") is not None]
    sell_slippages = [s["sell_slippage_bps"] for s in snapshots if s.get("sell_slippage_bps") is not None]
    top_bids = [s["top_bid_depth_usdt"] for s in snapshots if s.get("top_bid_depth_usdt") is not None]
    top_asks = [s["top_ask_depth_usdt"] for s in snapshots if s.get("top_ask_depth_usdt") is not None]

    # Calculate coverage statistics
    coverage_info = ""
    if states:
        coverage_info += "\n### 各事件标的观测详情 (Observation Details per Event-Symbol):\n"
        for es_id, st in states.items():
            coverage_info += f"- **{st.get('symbol')}** (ID: `{es_id[:8]}`):\n"
            coverage_info += f"  - 状态 (status): `{st.get('status')}`\n"
            coverage_info += f"  - 快照数量 (snapshots): {st.get('depth_snapshot_count')}\n"
            coverage_info += f"  - 最大间隔时间 (max_gap_ms): {st.get('max_gap_ms')} ms (通过: `{st.get('max_gap_pass')}`)\n"
            coverage_info += f"  - 覆盖率达标 (coverage_ratio_pass): `{st.get('coverage_ratio_pass')}`\n"
            coverage_info += f"  - 结果有效 (research_result_valid): `{st.get('research_result_valid')}`\n"
    else:
        coverage_info += "\n无已加载的 EventSymbolState 记录。\n"

    # Next action mapping
    allowed_action = "none"
    if decision == "stage1_5f_observer_depth_evidence_collected":
        allowed_action = "stage1_5g_write_depth_evidence_review_plan"
    elif decision == "stage1_5f_observer_event_observation_in_progress":
        allowed_action = "continue_server_observer"
    elif decision == "stage1_5f_observer_running_no_new_event":
        allowed_action = "continue_server_observer"
    elif decision == "stage1_5f_observer_failed":
        allowed_action = "debug_observer_failures"

    review_content = f"""# External Signal Shadow Lab Stage 1.5F Live Depth Observer Review

## 1. Decision (决策)
- **Top-Level Decision (顶层决策):** `{decision}`
- **research_result_valid (研究结果有效性):** `{summary.get('research_result_valid', False)}`
- **Allowed Next Action (允许的下一步行动):** `{allowed_action}`

## 2. Watermark / Bootstrap Status (水位线与初始化状态)
- **watermark_present (水位线文件存在):** `{watermark_present}`
- **watermark_version (水位线版本):** `{watermark_version}`
- **max_seen_detected_at_ms (最大观测事件时间戳):** `{max_seen}`
- **pre_watermark_events_ignored (水位线前忽略事件数):** `{pre_watermark_ignored}`
- **post_watermark_events_accepted (水位线后接受事件数):** `{post_watermark_accepted}`

## 3. Observation Status Statistics (观测状态统计)
- **活动中观测数 (active_observation_count):** `{active_count}`
- **已完成观测数 (completed_observation_count):** `{completed_count}`
- **已过期观测数 (expired_observation_count):** `{expired_count}`
- **已失败观测数 (failed_observation_count):** `{failed_count}`
- **要求的最小快照数 (min_snapshot_count_required):** `{summary.get('min_snapshot_count_required', 0)}`
- **收集的总快照数 (total_snapshots_collected):** `{len(snapshots)}`
{coverage_info}

## 4. Depth Snapshot Metrics Distributions (盘口快照指标分布)

### 4.1 Bid/Ask Spread (买卖价差 - BPS)
- **分布 (bps):** {format_pct_dist(spreads)}

### 4.2 Slippage Proxy (500 USDT 模拟滑点 - BPS)
- **买入滑点 (Buy Slippage bps):** {format_pct_dist(buy_slippages)}
- **卖出滑点 (Sell Slippage bps):** {format_pct_dist(sell_slippages)}

### 4.3 Bid/Ask Depth at Best Price (最优档挂单深度 - USDT)
- **买单挂单量 (Top Bid Depth):** {format_depth_dist(top_bids)}
- **卖单挂单量 (Top Ask Depth):** {format_depth_dist(top_asks)}

## 5. Request Health & Network Statistics (请求健康度与网络错误统计)
- **请求成功率 (request_success_rate):** `{success_rate:.4f}`
- **总请求数 (total_requests_made):** `{total_reqs}`
- **失败请求数 (failed_requests_count):** `{failed_reqs}`
- **当前连续错误数 (consecutive_network_errors):** `{consec_errors}`
- **历史最大连续错误数 (max_consecutive_network_errors_seen):** `{max_consec_seen}`
- **上游 Stage 1.5E summary 异常警告 (stage1_5e_context_suspicious):** `{summary.get('stage1_5e_context_suspicious', False)}`
- **阻碍项 (blocker):** `{summary.get('blocker')}`

## 6. Safety Boundaries (安全约束与合规控制)
- **execution_feasibility_claim_allowed (允许声明执行可行性证明):** `{summary.get('execution_feasibility_claim_allowed', False)}`
- **trade_signal_allowed (允许输出交易信号):** `{summary.get('trade_signal_allowed', False)}`
- **paper_trading_allowed (允许模拟盘交易):** `{summary.get('paper_trading_allowed', False)}`
- **live_trading_allowed (允许实盘交易):** `{summary.get('live_trading_allowed', False)}`
- **execution_engine_allowed (允许接入执行引擎):** `{summary.get('execution_engine_allowed', False)}`
- **alpha_interpretation_allowed (允许声称包含 alpha 边际):** `{summary.get('alpha_interpretation_allowed', False)}`

## 7. Why execution feasibility is still not proven (为什么执行可行性仍然未被证明)
即使本阶段收集了 12 小时的实时盘口深度快照（价差、最优档深度与 500 USDT 模拟滑点代理数据），执行可行性在当前阶段仍然未被证明。主要原因如下：
1. **被动观测 vs 主动撮合模拟:** 本阶段仅进行了被动盘口数据的定时快照拉取（REST API 代理），并未运行包含延迟模型、订单簿回放与主动撮合逻辑的仿真模拟。
2. **挂单 fill rate 与撤单逻辑未验证:** 实盘多采用 Maker-first 挂单模式，真实的挂单成交率、单腿暴露时间、远端 API 限频下的撤单退回与失败回滚，均未在 shadow 模式中进行验证。
3. **滑点与流动性深度的极端情况:** 单一的 500 USDT 滑点计算属于静态点估计，未考虑大额流动性瞬时枯竭、多并发订单竞争盘口以及订单薄更新延迟等实盘滑点漂移风险。
因此，必须在 Stage 1.5G 中进行多标的历史订单簿深度与 dual-leg 执行模拟后，才能对执行可行性做出最终科学判定。
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

    output_root = summary_path.parent
    states = load_all_states(output_root)
    snapshots = load_all_snapshots(output_root)

    review_text = generate_chinese_review(summary_data, states, snapshots)

    review_path.parent.mkdir(parents=True, exist_ok=True)
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(review_text)

    logger.info(f"Generated review at {review_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
