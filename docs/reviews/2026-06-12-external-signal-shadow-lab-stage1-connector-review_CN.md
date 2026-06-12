# External Signal Shadow Lab Stage 1 Connector 审查报告

## 1. 结论
- **决策**: `external_signal_connector_stage1_passed`
- **失效类型**: `connector_completed`
- **主阻塞项**: `None`

## 2. 范围与下一步
本轮不是 alpha 通过；不是 paper/live 准入；不允许下单；不允许接钱包。
Stage 0 replay handoff 必须使用 `available_at_ms`，不能使用原始 `event_time_ms`，否则会把外部信号延迟误当成可交易历史。

- **下一步**: `choose_one_real_read_only_source_for_manual_payload_dry_run`

## 3. 统计摘要
- Raw payload 数量: 11
- 输出事件数量: 2
- 去重数量: 1
- 隔离数量: 5
- 拒绝数量: 3
- 统计守恒是否通过: True
- Source: `fixture`
- Connector Version: `stage1_v0`
- Schema Version: `external_signal_event_v1`

## 4. Reject / Quarantine 明细
### Reject 明细
- available_before_event: 1
- forbidden_executable_payload: 1
- unsupported_event_type: 1

### Quarantine 明细
- missing_asset: 1
- missing_chain: 1
- price_mapping_unavailable: 2
- stale_latency: 1

## 5. 延迟语义
- P50 延迟（ms）: 60000
- P95 延迟（ms）: 60000
- 延迟口径: `available_at_ms - original_event_time_ms`

## 6. 安全边界
- Live Trading Enabled: `False`
- Exchange Paper Trading: `False`
- Execution Engine: `False`
- Research Shadow Replay: `True`
- Wallet Required: `False`

## 7. 不能推出的结论
这仍然**不能**证明外部 skills 有 alpha，也不能证明任何信号可进入 paper/live。它只能说明：file-backed connector 基础设施已经能把手动导出的只读 payload 安全、可审计地接入 research shadow pipeline。
