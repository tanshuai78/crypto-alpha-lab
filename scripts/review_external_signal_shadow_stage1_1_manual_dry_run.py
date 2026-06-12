"""
Stage 1.1 Review Script – 生成中文评审报告

Usage:
    PYTHONPATH=. uv run python scripts/review_external_signal_shadow_stage1_1_manual_dry_run.py \
        --summary reports/external_signal_shadow/connectors/stage1_1_gate_marketanalysis_manual_summary.json \
        --output docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-1-manual-payload-dry-run-review_CN.md
"""

import argparse
import json
import sys
from pathlib import Path


def _fmt_pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:.1%}"


def _fmt_int(val: int | None) -> str:
    if val is None:
        return "N/A"
    return str(val)


def generate_review(summary: dict) -> str:
    decision = summary.get("decision", "unknown")
    failure_type = summary.get("failure_type", "unknown")
    primary_blocker = summary.get("primary_blocker")
    handoff_ready = summary.get("stage0_handoff_ready", False)
    handoff_mode = summary.get("stage0_handoff_mode", "blocked")
    minimal_pass = summary.get("minimal_connector_pass", False)
    blockers = summary.get("stage0_handoff_blockers", [])

    # Conclusion banner
    if handoff_ready and handoff_mode == "directional_replay":
        conclusion = "✅ Stage 0 directional replay 交接就绪"
    elif handoff_ready and handoff_mode == "observation_only":
        conclusion = "✅ Stage 0 observation-only 交接就绪；directional replay 不就绪"
    elif handoff_ready:
        conclusion = f"✅ Stage 0 交接就绪；handoff_mode = `{handoff_mode}`"
    elif minimal_pass:
        conclusion = "⚠️ Connector 通过，但 Stage 0 交接尚未就绪（存在阻断项）"
    else:
        conclusion = "❌ Connector 未通过（不是 alpha 通过，不可进行 Stage 0 交接）"

    lines = [
        "# Stage 1.1 Manual Payload Dry Run 评审报告",
        "",
        "---",
        "",
        "## 结论",
        "",
        f"> {conclusion}",
        "",
        "**本评审结论不构成任何 alpha、paper trading 或 live trading 许可。**",
        "",
        "---",
        "",
        "## 数据源身份",
        "",
        "| 字段 | 值 |",
        "|------|----|",
        f"| `source` | `{summary.get('source')}` |",
        f"| `source_vendor` | `{summary.get('source_vendor')}` |",
        f"| `source_surface` | `{summary.get('source_surface')}` |",
        f"| `source_capture_method` | `{summary.get('source_capture_method')}` |",
        f"| `connector_version` | `{summary.get('connector_version')}` |",
        f"| `schema_version` | `{summary.get('schema_version')}` |",
        "",
        "---",
        "",
        "## 数量统计（Accounting）",
        "",
        "| 项目 | 数量 |",
        "|------|------|",
        f"| 原始 payload 总数 | {_fmt_int(summary.get('raw_payload_count'))} |",
        f"| 已发出事件数 | {_fmt_int(summary.get('emitted_event_count'))} |",
        f"| 去重数 | {_fmt_int(summary.get('deduped_payload_count'))} |",
        f"| 隔离数 | {_fmt_int(summary.get('quarantined_payload_count'))} |",
        f"| 拒绝数 | {_fmt_int(summary.get('rejected_payload_count'))} |",
        f"| 统计守恒 | {'✅' if summary.get('summary_accounting_ok') else '❌'} |",
        "",
        "---",
        "",
        "## 质量指标",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| `event_time_fallback_ratio` | {_fmt_pct(summary.get('event_time_fallback_ratio'))} |",
        f"| `duplicate_ratio` | {_fmt_pct(summary.get('duplicate_ratio'))} |",
        f"| `price_mapping_unavailable_ratio` | {_fmt_pct(summary.get('price_mapping_unavailable_ratio'))} |",
        f"| `rejected_payload_ratio` | {_fmt_pct(summary.get('rejected_payload_ratio'))} |",
        f"| `unknown_event_type_ratio` | {_fmt_pct(summary.get('unknown_event_type_ratio'))} |",
        f"| `missing_required_field_ratio` | {_fmt_pct(summary.get('missing_required_field_ratio'))} |",
        f"| `single_symbol_dominance_ratio` | {_fmt_pct(summary.get('single_symbol_dominance_ratio'))} |",
        f"| `single_time_bucket_dominance_ratio` | {_fmt_pct(summary.get('single_time_bucket_dominance_ratio'))} |",
        f"| `unique_symbol_count` | {_fmt_int(summary.get('unique_symbol_count'))} |",
        f"| `unique_event_time_bucket_count` | {_fmt_int(summary.get('unique_event_time_bucket_count'))} |",
        f"| `latency_p50_ms` | {_fmt_int(summary.get('latency_p50_ms'))} |",
        f"| `latency_p95_ms` | {_fmt_int(summary.get('latency_p95_ms'))} |",
        "",
        "---",
        "",
        "## Stage 0 交接门禁",
        "",
        "| 项目 | 状态 |",
        "|------|------|",
        f"| `decision` | `{decision}` |",
        f"| `failure_type` | `{failure_type}` |",
        f"| `primary_blocker` | `{primary_blocker}` |",
        f"| `minimal_connector_pass` | `{minimal_pass}` |",
        f"| `stage0_handoff_ready` | `{handoff_ready}` |",
        f"| `stage0_handoff_mode` | `{handoff_mode}` |",
        f"| `stage0_directional_replay_ready` | `{summary.get('stage0_directional_replay_ready')}` |",
        f"| `stage0_observation_handoff_ready` | `{summary.get('stage0_observation_handoff_ready')}` |",
        "",
    ]

    if blockers:
        lines += [
            "### 交接阻断项（stage0_handoff_blockers）",
            "",
        ]
        for b in blockers:
            lines.append(f"- `{b}`")
        lines.append("")

    lines += [
        "---",
        "",
        "## 拒绝 / 隔离原因明细",
        "",
    ]

    reject_counts = summary.get("reject_reason_counts", {})
    quarantine_counts = summary.get("quarantine_reason_counts", {})

    if reject_counts:
        lines.append("**拒绝原因：**")
        lines.append("")
        for k, v in sorted(reject_counts.items()):
            lines.append(f"- `{k}`: {v}")
        lines.append("")

    if quarantine_counts:
        lines.append("**隔离原因：**")
        lines.append("")
        for k, v in sorted(quarantine_counts.items()):
            lines.append(f"- `{k}`: {v}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 安全边界声明",
        "",
        "- 本次 Dry Run 输出仅供研究观察，所有事件均标记 `shadow_only = true`。",
        "- `notional_usd = 0.0`，不涉及任何名义持仓。",
        "- `live_trading_enabled = false`，`execution_engine_allowed = false`。",
        "- **禁止基于本报告推出 alpha 判断、paper trading 或 live trading 操作。**",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 1.1 中文评审报告生成器"
    )
    parser.add_argument("--summary", required=True, help="输入：JSON summary 文件路径")
    parser.add_argument("--output", required=True, help="输出：Markdown 评审报告路径")

    args = parser.parse_args()

    summary_path = Path(args.summary)
    if not summary_path.exists():
        print(f"ERROR: Summary file not found: {summary_path}", file=sys.stderr)
        sys.exit(1)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    review_text = generate_review(summary)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(review_text, encoding="utf-8")

    print(f"评审报告已写入: {out_path}")


if __name__ == "__main__":
    main()
