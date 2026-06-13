#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Stage 1.2 Chinese review.")
    parser.add_argument("--collector-summary", type=str, required=True, help="Path to collector summary JSON.")
    parser.add_argument("--connector-summary", type=str, help="Path to connector summary JSON.")
    parser.add_argument("--output", type=str, required=True, help="Path to write review_CN.md report.")

    args = parser.parse_args(argv)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load collector summary
    collector_path = Path(args.collector_summary)
    if not collector_path.exists():
        sys.stderr.write(f"Collector summary missing: {args.collector_summary}\n")
        return 1

    try:
        with open(collector_path, "r", encoding="utf-8") as f:
            coll = json.load(f)
    except Exception as e:
        sys.stderr.write(f"Failed to parse collector summary: {e}\n")
        return 1

    # 2. Check if connector summary is provided and exists
    conn = None
    if args.connector_summary:
        connector_path = Path(args.connector_summary)
        if connector_path.exists():
            try:
                with open(connector_path, "r", encoding="utf-8") as f:
                    conn = json.load(f)
            except Exception as e:
                sys.stderr.write(f"Failed to parse connector summary: {e}\n")

    if conn is None:
        # Generate error review
        content = (
            "# External Signal Shadow Lab Stage 1.2 Gate Public Read-Only Collector Review\n\n"
            "## 1. 结论\n"
            "**结果：不通过 (REJECTED)**\n\n"
            "## 2. 失败原因\n"
            "- **connector_summary_missing**: 缺失 Stage 1 connector summary 文件或解析失败。\n"
            "无法评估端到端 normalized 数据的正确性。\n\n"
            "## 3. 指标状态\n"
            "- collector_minimal_pass: false\n"
            "- connector_minimal_pass: false\n"
            "- stage0_observation_handoff_ready: false\n"
            "- stage0_directional_replay_ready: false\n"
        )
        output_path.write_text(content, encoding="utf-8")
        return 1

    # 3. Analyze both summaries
    coll_pass = coll.get("collector_minimal_pass") is True
    conn_pass = (conn.get("minimal_connector_pass") is True or conn.get("connector_minimal_pass") is True)
    handoff_ready = (
        coll_pass
        and conn_pass
        and coll.get("decision") == "external_signal_collector_stage1_2_passed"
        and conn.get("decision") == "external_signal_connector_stage1_passed"
        and conn.get("stage0_observation_handoff_ready") is True
    )

    status_str = "通过 (PASSED)" if handoff_ready else "不通过 (FAILED)"

    content = f"""# External Signal Shadow Lab Stage 1.2 Gate Public Read-Only Collector Review

## 1. 结论
**最终评估结果：{status_str}**

## 2. 核心指标说明
- **Source Identity**: gate_public_market_snapshot_collector (Gate 公开只读行情快照)
- **Collector Minimal Pass**: {coll_pass} (成功率: {coll.get("http_success_count", 0)}/{coll.get("http_success_count", 0) + coll.get("http_failure_count", 0)})
- **Connector Minimal Pass**: {conn_pass} (Emitted Count: {conn.get("emitted_event_count", 0)})
- **Stage 0 Observation Handoff Ready**: {handoff_ready} (观测通道是否就绪)
- **Stage 0 Directional Replay Ready**: False (仅用于观测，不构成 alpha，directional replay 不允许)
- **Event Density Alpha Valid**: False (事件密度不包含 alpha)

## 3. 安全防护审计 (Safety Boundary Guard)
- **API Key Used**: {coll.get("api_key_used", False)} (必须为 False，不读取或使用任何 CEX 密钥)
- **Private Endpoint Used**: {coll.get("private_endpoint_used", False)} (必须为 False，严禁使用任何需要账户权限的私有接口)
- **Forbidden Executable Payload Count**: {coll.get("forbidden_payload_count", 0)} (必须为 0，严禁含有交易指令/提币指令/签名交易等敏感内容)

## 4. 运行警告与边界约束
> [!IMPORTANT]
> `cex_market_snapshot` 是由 collector 定时触发的公开市场行情快照观测数据，不是外部系统主动推送的 alpha 异常事件。
>
> 1. 本通道**不产生任何 alpha 判断**。
> 2. 该事件**严禁用于任何 paper_trading 或 live_trading 实盘策略**。
> 3. 该事件**严禁触发三重屏障 directional order**，仅能在研究模块用于时间轴对齐或纯数据质量评估。
"""

    output_path.write_text(content, encoding="utf-8")
    if not handoff_ready:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
