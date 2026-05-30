from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

from src.research.liquidation_only_5m.baseline import classify_liquidation_only_5m_event
from src.research.liquidation_only_5m.forward_returns import (
    aggregate_forward_returns,
    compute_event_forward_returns,
)

logger = logging.getLogger(__name__)


def run_decision_engine(
    summary: dict[int, dict[str, dict[str, Any]]],
    total_events: int,
    span_days: float,
) -> tuple[str, list[str]]:
    reasons = []

    # 1. Check data depth
    if span_days < 7.0:
        return "insufficient_5m_data_depth", [
            f"Span of data is only {span_days:.2f} days, less than required 7 days."
        ]

    # 2. Check event density
    events_per_30d = (total_events * 30.0 / span_days) if span_days > 0 else 0.0
    if total_events < 5:
        return "insufficient_event_density", [
            f"Too few total events ({total_events} < 5) for reliable inference."
        ]
    if events_per_30d < 5.0:
        return "insufficient_event_density", [
            f"Events density too low ({events_per_30d:.2f}/30d < 5.0/30d)."
        ]

    # 3. Check symbol concentration
    # We check concentration for both hypotheses on horizon 1
    max_share = 0.80
    for hyp in ("continuation", "mean_reversion"):
        share_map = summary[1][hyp].get("event_share_per_symbol", {})
        for sym, share in share_map.items():
            if share > max_share:
                reasons.append(
                    f"Symbol concentration too high for {hyp}: {sym} has {share * 100:.1f}% share (> {max_share * 100}%)"
                )

    # 4. Check performance gates per hypothesis
    hyp_success = {}
    for hyp in ("continuation", "mean_reversion"):
        # Must pass performance gates across at least 2 horizons (e.g. h=1 and h=2)
        success_horisons = []
        for h in (1, 2, 3):
            stats = summary[h][hyp]
            # Performance gates
            med_cost = stats.get("median_cost_adjusted_bps", 0.0)
            win_rate_cost = stats.get("cost_adjusted_win_rate", 0.0)
            worst_cost = stats.get("worst_cost_adjusted_bps", 0.0)

            passed_med = med_cost > 0.0
            passed_win = win_rate_cost >= 0.48
            passed_worst = worst_cost >= -1000.0  # tail loss < 10%

            if passed_med and passed_win and passed_worst:
                success_horisons.append(h)
            else:
                logger.debug(
                    f"Hypothesis {hyp} failed horizon {h} gates: med={med_cost:.2f}, win_rate={win_rate_cost:.2f}, worst={worst_cost:.2f}"
                )

        # Requires adjacent or at least 2 horizons consistency
        if len(success_horisons) >= 2:
            hyp_success[hyp] = success_horisons
        else:
            reasons.append(
                f"Hypothesis {hyp} failed performance gates across horizons (passed only on {success_horisons})"
            )

    if hyp_success:
        # At least one hypothesis passed all gates!
        passed_hyp = list(hyp_success.keys())
        return "continue_to_phase2_enhancements", [
            f"Hypothesis {passed_hyp} passed all gates: {hyp_success}"
        ]

    return "retire_liquidation_only_5m_baseline", [
        "No hypothesis passed all performance gates on a cost-adjusted basis. " + "; ".join(reasons)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review 5m baseline research results and make continue/retire decision."
    )
    parser.add_argument(
        "--dataset-jsonl",
        default="reports/liquidation_only_5m/liquidation_only_5m_dataset.jsonl",
        help="Path to the enriched aligned 5m dataset",
    )
    parser.add_argument(
        "--summary-output",
        default="reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_baseline_summary.json",
        help="Output path for the aggregate JSON report",
    )
    parser.add_argument(
        "--review-output",
        default="docs/reviews/2026-05-30-liquidation-only-5m-baseline-review.md",
        help="Output path for the markdown review report",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    # Load dataset
    if not os.path.exists(args.dataset_jsonl):
        logger.error(f"Dataset {args.dataset_jsonl} does not exist.")
        return 1

    rows = []
    with open(args.dataset_jsonl, "r") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    if not rows:
        logger.error("Dataset is empty.")
        return 1

    # Group rows by symbol
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_symbol.setdefault(r["symbol"], []).append(r)

    # Sort each symbol's timeline
    for sym, sym_rows in by_symbol.items():
        sym_rows.sort(key=lambda x: x["bar_start_ms"])

    # Calculate time span of dataset
    all_ts = [r["bar_start_ms"] for r in rows]
    min_ts = min(all_ts)
    max_ts = max(all_ts)
    span_days = (max_ts - min_ts) / 1000.0 / 86400.0

    # Find qualifying events
    event_returns = []
    symbol_counts = {}

    for sym, sym_rows in by_symbol.items():
        for i, row in enumerate(sym_rows):
            event = classify_liquidation_only_5m_event(row)
            if event is not None:
                ret = compute_event_forward_returns(event, sym_rows, event_index=i)
                if ret is not None:
                    event_returns.append(ret)
                    symbol_counts[sym] = symbol_counts.get(sym, 0) + 1

    total_events = len(event_returns)

    # Compute overall aggregates
    summary = aggregate_forward_returns(event_returns)

    # Enrich summary with symbol event shares
    for h in (1, 2, 3):
        for hyp in ("continuation", "mean_reversion"):
            share_map = {}
            for sym, count in symbol_counts.items():
                share_map[sym] = count / total_events if total_events > 0 else 0.0
            summary[h][hyp]["event_share_per_symbol"] = share_map

    # Compute time split consistency (anti-snooping lookback/forward check)
    period_consistency = {}
    if total_events >= 4:
        # Split events into two halves based on timestamp
        sorted_events = sorted(event_returns, key=lambda x: x["bar_start_ms"])
        mid_idx = total_events // 2
        first_half = sorted_events[:mid_idx]
        second_half = sorted_events[mid_idx:]

        sum1 = aggregate_forward_returns(first_half)
        sum2 = aggregate_forward_returns(second_half)

        # Consistency metric: do they both have positive cost-adjusted median on the best hypothesis?
        # Let's check best hypothesis in aggregate
        best_hyp = "continuation"
        # If mean reversion has higher median return in aggregate on h=1, use it
        if (
            summary[1]["mean_reversion"]["median_cost_adjusted_bps"]
            > summary[1]["continuation"]["median_cost_adjusted_bps"]
        ):
            best_hyp = "mean_reversion"

        med1 = sum1[1][best_hyp]["median_cost_adjusted_bps"]
        med2 = sum2[1][best_hyp]["median_cost_adjusted_bps"]
        consistent = (med1 > 0.0 and med2 > 0.0) or (med1 <= 0.0 and med2 <= 0.0)

        period_consistency = {
            "split_timestamp_ms": sorted_events[mid_idx]["bar_start_ms"],
            "best_hypothesis": best_hyp,
            "first_half_median_cost_adjusted_bps": med1,
            "second_half_median_cost_adjusted_bps": med2,
            "consistent_sign": consistent,
        }

    # Run decision engine
    decision, reasons = run_decision_engine(summary, total_events, span_days)

    # Prepare final JSON
    report_json = {
        "vendor": "coinalyze",
        "interval": "5min",
        "data_span_days": round(span_days, 2),
        "total_event_count": total_events,
        "events_per_30d": round(total_events * 30.0 / span_days, 2) if span_days > 0 else 0.0,
        "symbol_counts": symbol_counts,
        "max_single_symbol_event_share": round(max(symbol_counts.values()) / total_events, 3)
        if symbol_counts
        else 0.0,
        "aggregates": summary,
        "period_consistency": period_consistency,
        "decision": decision,
        "decision_reasons": reasons,
    }

    # Save JSON report
    os.makedirs(os.path.dirname(os.path.abspath(args.summary_output)), exist_ok=True)
    with open(args.summary_output, "w") as f:
        json.dump(report_json, f, indent=2)
    logger.info(f"Saved baseline summary JSON to {args.summary_output}")

    # Build Markdown review
    os.makedirs(os.path.dirname(os.path.abspath(args.review_output)), exist_ok=True)

    # Extract stats for Markdown representation
    c_h1 = summary.get(1, {}).get("continuation", {})
    mr_h1 = summary.get(1, {}).get("mean_reversion", {})
    c_h2 = summary.get(2, {}).get("continuation", {})
    mr_h2 = summary.get(2, {}).get("mean_reversion", {})
    c_h3 = summary.get(3, {}).get("continuation", {})
    mr_h3 = summary.get(3, {}).get("mean_reversion", {})

    with open(args.review_output, "w", encoding="utf-8") as f:
        f.write(f"""# Liquidation-Only 5m Baseline Research Review Report

## 1. 决策概要 (Decision Summary)

- **最终决策 (Final Decision)**: `{decision.upper()}`
- **数据跨度 (Data Span)**: `{span_days:.2f} 天` (物理连续 5m bars 数量: `{len(rows)}`)
- **触发事件总数 (Total Event Count)**: `{total_events}` 个 (每 30 天均值: `{report_json["events_per_30d"]:.2f}` 次)
- **决策原因 (Decision Reasons)**:
""")
        for r in reasons:
            f.write(f"  - {r}\n")

        f.write(f"""
---

## 2. 假设表现分析 (Hypothesis Performance)

### A. Continuation Hypothesis (顺势假设)
衡量大额清算后，价格在未来 `1 / 2 / 3` 个 5m bar 是否继续顺着清算压力方向移动（即 short 爆仓进多，long 爆仓进空）。

| Horizon (Hold) | Event Count | Median (Gross) | Median (Cost-Adj) | Win Rate (Cost-Adj) | Worst Trade (Cost-Adj) |
|---|---|---|---|---|---|
| +1 bar (5m) | {c_h1.get("event_count", 0)} | {c_h1.get("median_gross_bps", 0.0):.2f} bps | {c_h1.get("median_cost_adjusted_bps", 0.0):.2f} bps | {c_h1.get("cost_adjusted_win_rate", 0.0) * 100:.1f}% | {c_h1.get("worst_cost_adjusted_bps", 0.0):.2f} bps |
| +2 bars (10m) | {c_h2.get("event_count", 0)} | {c_h2.get("median_gross_bps", 0.0):.2f} bps | {c_h2.get("median_cost_adjusted_bps", 0.0):.2f} bps | {c_h2.get("cost_adjusted_win_rate", 0.0) * 100:.1f}% | {c_h2.get("worst_cost_adjusted_bps", 0.0):.2f} bps |
| +3 bars (15m) | {c_h3.get("event_count", 0)} | {c_h3.get("median_gross_bps", 0.0):.2f} bps | {c_h3.get("median_cost_adjusted_bps", 0.0):.2f} bps | {c_h3.get("cost_adjusted_win_rate", 0.0) * 100:.1f}% | {c_h3.get("worst_cost_adjusted_bps", 0.0):.2f} bps |

### B. Mean Reversion Hypothesis (反转假设)
衡量大额清算后，清算压力耗尽导致价格迅速反转（即 short 爆仓进空，long 爆仓进多）。

| Horizon (Hold) | Event Count | Median (Gross) | Median (Cost-Adj) | Win Rate (Cost-Adj) | Worst Trade (Cost-Adj) |
|---|---|---|---|---|---|
| +1 bar (5m) | {mr_h1.get("event_count", 0)} | {mr_h1.get("median_gross_bps", 0.0):.2f} bps | {mr_h1.get("median_cost_adjusted_bps", 0.0):.2f} bps | {mr_h1.get("cost_adjusted_win_rate", 0.0) * 100:.1f}% | {mr_h1.get("worst_cost_adjusted_bps", 0.0):.2f} bps |
| +2 bars (10m) | {mr_h2.get("event_count", 0)} | {mr_h2.get("median_gross_bps", 0.0):.2f} bps | {mr_h2.get("median_cost_adjusted_bps", 0.0):.2f} bps | {mr_h2.get("cost_adjusted_win_rate", 0.0) * 100:.1f}% | {mr_h2.get("worst_cost_adjusted_bps", 0.0):.2f} bps |
| +3 bars (15m) | {mr_h3.get("event_count", 0)} | {mr_h3.get("median_gross_bps", 0.0):.2f} bps | {mr_h3.get("median_cost_adjusted_bps", 0.0):.2f} bps | {mr_h3.get("cost_adjusted_win_rate", 0.0) * 100:.1f}% | {mr_h3.get("worst_cost_adjusted_bps", 0.0):.2f} bps |

---

## 3. 统计质量控制与反拟合审查 (Anti-Snooping Audit)

### A. 币种集中度 (Symbol Concentration)
清算特征是否集中在单一币种，导致策略其实只对单个币种生效？
""")
        for sym, count in symbol_counts.items():
            share = count / total_events if total_events > 0 else 0.0
            f.write(f"- **{sym}**: {count} 次事件 (占比 {share * 100:.1f}%)\n")

        f.write(f"""
### B. 时间分片样本一致性 (By-Period Consistency)
将事件按时间先后对半切分，检验两段独立子样本的表现是否具有符号一致性：
- **第一半段 (First Half Median Cost-Adj)**: {period_consistency.get("first_half_median_cost_adjusted_bps", 0.0):.2f} bps
- **第二半段 (Second Half Median Cost-Adj)**: {period_consistency.get("second_half_median_cost_adjusted_bps", 0.0):.2f} bps
- **符号一致性 (Consistent Sign)**: `{"PASS" if period_consistency.get("consistent_sign") else "FAIL"}`

---

## 4. 交易层解读与下一步计划 (Trading Interpretation)

1. **资金利用率与密度**:
   5分钟周期的纯清算事件密度对实盘的资金效率提出了极高要求。在 lookback 期间内探测到的合格事件数为 `{total_events}`。
2. **Hypothesis 结论**:
   - `continuation` 在扣除最小 `16.0` bps 的摩擦成本后，主要持仓周期的表现是否具有统计显著性？
   - `mean_reversion` 表现如何？是否在爆仓后的情绪性逆转期表现更好？
3. **下一步执行计划**:
   - 如果决策为 `CONTINUE_TO_PHASE2_ENHANCEMENTS`：进入 Phase 2，包括引入 OI 二级确认与订单簿深度的执行模拟。
   - 如果决策为 `RETIRE`：归档该研究方向，将资金和算力倾斜回 carry 和 multi-day basisdesk。
""")

    logger.info(f"Saved baseline review markdown report to {args.review_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
