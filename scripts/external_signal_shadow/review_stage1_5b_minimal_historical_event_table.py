import argparse
import json
import sys
from pathlib import Path


def generate_review_content(summary: dict) -> str:
    decision = summary.get("decision", "unknown")
    source_audit_passed = summary.get("source_audit_passed", False)
    article_count = summary.get("article_level_row_count", 0)
    symbol_count = summary.get("normalized_symbol_event_count", 0)
    unique_days = summary.get("unique_event_days", 0)
    unique_symbols = summary.get("symbols_with_events", 0)
    blockers = summary.get("blockers", [])
    next_action = summary.get("next_action", "unknown")

    article_counts = summary.get("event_type_counts_article_level", {})
    symbol_counts = summary.get("event_type_counts_symbol_level", {})

    blockers_str = "\n".join(f"- {b}" for b in blockers) if blockers else "无"

    article_types_str = "\n".join(f"  - `{k}`: {v}" for k, v in article_counts.items())
    symbol_types_str = "\n".join(f"  - `{k}`: {v}" for k, v in symbol_counts.items())
    if decision == "stage1_5b_event_table_ready":
        article_coverage_text = (
            f"- 包含公告级别记录 {article_count} 条，达到了首期目标的范围要求（门槛值为不少于 30 条）。"
        )
        symbol_coverage_text = (
            f"- 扩展后的事件共有 {symbol_count} 条，覆盖了 {unique_symbols} 个交易对，"
            f"具有合理的时间分布密度（共有 {unique_days} 个 UTC 日包含事件，门槛值为 20 天）。"
        )
        next_action_text = (
            "如果为 `write_stage1_5c_external_catalyst_replay_implementation_plan`，"
            "则可进入 Stage 1.5C 的设计与规划阶段。"
        )
    elif decision == "stage1_5b_event_table_sparse_inconclusive":
        article_coverage_text = (
            f"- 样本仍为 sparse/inconclusive：公告级别记录 {article_count} 条，"
            "尚未满足 Stage 1.5B ready 所需的完整密度门槛。"
        )
        symbol_coverage_text = (
            f"- 扩展后的事件共有 {symbol_count} 条，覆盖 {unique_symbols} 个交易对、"
            f"{unique_days} 个 UTC 日；当前只能作为稀疏诊断，不能进入 replay plan。"
        )
        next_action_text = "当前应继续补充高可信事件或新增 OKX source audit，不应进入 Stage 1.5C。"
    else:
        article_coverage_text = (
            f"- 未达到 Stage 1.5B 事件表 ready 门槛：公告级别记录 {article_count} 条，"
            "存在 hard blocker 或上游审计失败。"
        )
        symbol_coverage_text = (
            f"- 扩展后的事件共有 {symbol_count} 条，覆盖 {unique_symbols} 个交易对、"
            f"{unique_days} 个 UTC 日；由于当前 decision 为 failed，不能解释为有效研究表。"
        )
        next_action_text = "当前必须先修复 event table 输入或上游 source audit，再重新生成 Stage 1.5B。"

    content = f"""# External Signal Shadow Lab Stage 1.5B Minimal Historical Event Table Review

## 1. 结论
当前 Stage 1.5B minimal historical event table 的状态为：`{decision}`。

## 2. Input / Output Evidence
- **上游审计状态 (source_audit_passed)**: {source_audit_passed}
- **Article 级别公告事件数 (article_level_row_count)**: {article_count}
- **Symbol 扩展后的事件数 (normalized_symbol_event_count)**: {symbol_count}
- **唯一事件天数 (unique_event_days)**: {unique_days}
- **包含事件的 Symbol 数 (symbols_with_events)**: {unique_symbols}

## 3. Article-level Coverage
{article_coverage_text}

## 4. Symbol-expanded Coverage
{symbol_coverage_text}

## 5. Event Type Counts
- **Article 级别事件类型计数**：
{article_types_str or "  无"}
- **Symbol 级别事件类型计数**：
{symbol_types_str or "  无"}

## 6. Safety Boundaries (安全边界约束)
> [!IMPORTANT]
> - **Stage 1.5B 准备就绪不代表 alpha 存在，不设定 replay_allowed 为 true**。
> - **Stage 1.5B 准备就绪不允许进行 paper_trading_allowed 或 live_trading_allowed**。
> - **Stage 1.5B 准备就绪不决定任何事件是否符合 Stage 1.5C stage1_5c_replay_candidate_allowed 准入条件**。
> - **Stage 1.5B 仅允许编写 Stage 1.5C replay 实施计划**。
> - 所有归一化生成的 `BASEUSDT` 交易对均为**研究假设**，实际交易所的 `market pair` 是否存在、价格历史覆盖范围 (`price_history_coverage_verified`)、可交易性 (`tradability_verified`)、深度和流动性均**未在 Stage 1.5B 中验证**，必须由 Stage 1.5C 执行检查。
> - 方向性假设 (`directional_hypothesis`) 统一为 `"undefined"`，方向标志 `signed_direction` 为 `null`，禁止任何 long/short 交易意图。
> - 在本阶段中**不输出** funding/OI/liquidation/BTC regime 等 context labels (即 context_label_join_allowed 为 false)。

## 7. Blockers (阻碍因素)
{blockers_str}

## 8. Allowed Next Action (允许的下一步行动)
允许的下一步行动为：`{next_action}`。
{next_action_text}
"""
    return content


def main():
    parser = argparse.ArgumentParser(description="Generate Stage 1.5B Chinese Review Markdown")
    parser.add_argument("--summary", required=True, help="Path to normalization_summary.json")
    parser.add_argument("--output-review", required=True, help="Path to output markdown review")

    args = parser.parse_args()

    # Load summary
    try:
        with open(args.summary, "r", encoding="utf-8") as f:
            summary = json.load(f)
    except Exception as exc:
        print(f"Error reading summary file: {exc}", file=sys.stderr)
        sys.exit(1)

    # Generate review content
    review_content = generate_review_content(summary)

    # Create output directory
    Path(args.output_review).parent.mkdir(parents=True, exist_ok=True)

    # Write review content
    with open(args.output_review, "w", encoding="utf-8") as f:
        f.write(review_content)

    print(f"Stage 1.5B Chinese review generated at: {args.output_review}")


if __name__ == "__main__":
    main()
