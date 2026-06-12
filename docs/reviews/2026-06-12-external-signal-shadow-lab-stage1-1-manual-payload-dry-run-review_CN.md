# Stage 1.1 Manual Payload Dry Run 评审报告

---

## 结论

> ✅ Stage 0 observation-only 交接就绪；directional replay 不就绪

**本评审结论不构成任何 alpha、paper trading 或 live trading 许可。**

---

## 数据源身份

| 字段 | 值 |
|------|----|
| `source` | `gate_marketanalysis_manual_export` |
| `source_vendor` | `gate` |
| `source_surface` | `gate_big_data_dashboard` |
| `source_capture_method` | `manual_export` |
| `connector_version` | `stage1_v0` |
| `schema_version` | `external_signal_event_v1` |

---

## 数量统计（Accounting）

| 项目 | 数量 |
|------|------|
| 原始 payload 总数 | 21 |
| 已发出事件数 | 16 |
| 去重数 | 2 |
| 隔离数 | 2 |
| 拒绝数 | 1 |
| 统计守恒 | ✅ |

---

## 质量指标

| 指标 | 数值 |
|------|------|
| `event_time_fallback_ratio` | 6.2% |
| `duplicate_ratio` | 9.5% |
| `price_mapping_unavailable_ratio` | 0.0% |
| `rejected_payload_ratio` | 4.8% |
| `unknown_event_type_ratio` | 4.8% |
| `missing_required_field_ratio` | 4.8% |
| `single_symbol_dominance_ratio` | 25.0% |
| `single_time_bucket_dominance_ratio` | 6.2% |
| `unique_symbol_count` | 5 |
| `unique_event_time_bucket_count` | 16 |
| `latency_p50_ms` | 1000 |
| `latency_p95_ms` | 1000 |

---

## Stage 0 交接门禁

| 项目 | 状态 |
|------|------|
| `decision` | `external_signal_connector_stage1_passed` |
| `failure_type` | `connector_completed` |
| `primary_blocker` | `None` |
| `minimal_connector_pass` | `True` |
| `stage0_handoff_ready` | `True` |
| `stage0_handoff_mode` | `observation_only` |
| `stage0_directional_replay_ready` | `False` |
| `stage0_observation_handoff_ready` | `True` |

---

## 拒绝 / 隔离原因明细

**拒绝原因：**

- `unsupported_event_type`: 1

**隔离原因：**

- `missing_asset`: 1
- `unsupported_stage1_1_symbol`: 1

---

## 安全边界声明

- 本次 Dry Run 输出仅供研究观察，所有事件均标记 `shadow_only = true`。
- `notional_usd = 0.0`，不涉及任何名义持仓。
- `live_trading_enabled = false`，`execution_engine_allowed = false`。
- **禁止基于本报告推出 alpha 判断、paper trading 或 live trading 操作。**
