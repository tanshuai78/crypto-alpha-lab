import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    summary_path = Path(args.summary)
    if not summary_path.exists():
        return 1

    summary = json.loads(summary_path.read_text())

    rejects = "\n".join(f"- {k}: {v}" for k, v in summary.get("reject_reason_counts", {}).items())
    quarantines = "\n".join(f"- {k}: {v}" for k, v in summary.get("quarantine_reason_counts", {}).items())

    markdown = f"""# External Signal Shadow Lab Stage 1 Connector 审查报告

## 1. 结论
- **决策**: `{summary.get("decision")}`
- **失效类型**: `{summary.get("failure_type")}`
- **主阻塞项**: `{summary.get("primary_blocker")}`

## 2. 范围与下一步
本轮不是 alpha 通过；不是 paper/live 准入；不允许下单；不允许接钱包。
Stage 0 replay handoff 必须使用 `available_at_ms`，不能使用原始 `event_time_ms`，否则会把外部信号延迟误当成可交易历史。

- **下一步**: `choose_one_real_read_only_source_for_manual_payload_dry_run`

## 3. 统计摘要
- Raw payload 数量: {summary.get("raw_payload_count")}
- 输出事件数量: {summary.get("emitted_event_count")}
- 去重数量: {summary.get("deduped_payload_count")}
- 隔离数量: {summary.get("quarantined_payload_count")}
- 拒绝数量: {summary.get("rejected_payload_count")}
- 统计守恒是否通过: {summary.get("summary_accounting_ok")}
- Source: `{summary.get("source")}`
- Connector Version: `{summary.get("connector_version")}`
- Schema Version: `{summary.get("schema_version")}`

## 4. Reject / Quarantine 明细
### Reject 明细
{rejects if rejects else "- None"}

### Quarantine 明细
{quarantines if quarantines else "- None"}

## 5. 延迟语义
- P50 延迟（ms）: {summary.get("latency_p50_ms", "N/A")}
- P95 延迟（ms）: {summary.get("latency_p95_ms", "N/A")}
- 延迟口径: `available_at_ms - original_event_time_ms`

## 6. 安全边界
- Live Trading Enabled: `{summary.get("live_trading_enabled")}`
- Exchange Paper Trading: `{summary.get("exchange_paper_trading_allowed")}`
- Execution Engine: `{summary.get("execution_engine_allowed")}`
- Research Shadow Replay: `{summary.get("research_shadow_replay_allowed")}`
- Wallet Required: `{summary.get("wallet_required")}`

## 7. 不能推出的结论
这仍然**不能**证明外部 skills 有 alpha，也不能证明任何信号可进入 paper/live。它只能说明：file-backed connector 基础设施已经能把手动导出的只读 payload 安全、可审计地接入 research shadow pipeline。
"""

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown)
    print(f"Written: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
