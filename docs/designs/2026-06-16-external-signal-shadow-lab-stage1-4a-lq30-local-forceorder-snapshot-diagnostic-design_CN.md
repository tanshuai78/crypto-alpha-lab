# External Signal Shadow Lab Stage 1.4A-LQ30 Local ForceOrder Snapshot Diagnostic Design

日期：2026-06-16

## 1. 设计结论

Stage 1.4A-LQ30 的目标不是证明 alpha，也不是替代 full composite replay。

它只回答一个更窄的问题：

```text
当前已经积累的 15-30d 本地 forceOrder snapshot archive，
是否已经显示出足够事件密度、时间重叠度、集中度与 source quality，
值得继续等待 >=90d local forceOrder history，或继续争取 vendor-grade liquidation sample？
```

本阶段推荐结论：

```text
decision = proceed_to_stage1_4a_lq30_local_forceorder_snapshot_diagnostic
scope = local_force_order_snapshot_liquidation_diagnostic_only
primary_source = local_force_order_archive
price_source = binance_futures_1m_or_15m_bars
funding_source = existing_stage1_4a1_funding_history
oi_source = existing_stage1_4a1_oi_history
full_composite_claim_allowed = false
complete_liquidation_tape_claim_allowed = false
liquidation_source_truth_level = local_force_order_snapshot_rows_not_complete_tape
alpha_interpretation_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

Stage 1.4A-LQ30 的正确定位是：

```text
local forceOrder snapshot utility diagnostic
```

而不是：

```text
strategy pass
full derivatives stress composite pass
paper/live handoff
```

---

## 2. 为什么需要 LQ30

当前 Stage 1.4 的现实状态是：

```text
funding / OI / futures price 历史已基本可得；
local forceOrder snapshot archive 正在持续积累；
但 local forceOrder history 当前只有约 12-14d；
vendor liquidation sample 仍未取得；
CM liquidation proxy 只能做 partial diagnostic，不能当主证据。
```

因此当前主风险不是“完全没有 liquidation 数据”，而是：

```text
不知道这条 local forceOrder snapshot 线本身是否值得继续等到 90d。
```

如果直接等待 90d，可能花费较长时间后才发现：

```text
event density 太低
symbol coverage 太差
single-day concentration 太高
和 funding / OI / price 的重叠窗口太少
source quality 不稳定
```

Stage 1.4A-LQ30 的目的，就是在不误报 alpha 的前提下，先用 15-30d 已有 local forceOrder snapshot 历史做一次中间层诊断，尽早回答：

```text
这条线值得继续积累吗？
如果值得，最缺的是时间长度、vendor 数据，还是聚合/回放定义？
```

---

## 3. 本阶段要回答的问题

Stage 1.4A-LQ30 只回答以下 5 个问题：

### 3.1 事件密度是否足够

```text
15-30d 内，BTC / ETH / SOL / XRP / DOGE 的 local forceOrder liquidation 事件，
在 15m / 1h 聚合后是否足以形成有意义的 diagnostic window？
```

### 3.2 与 funding / OI / price 是否能对齐

```text
liquidation 窗口与现有 funding / OI / futures price 数据，
在时间上是否有足够 overlap 以支撑后续 composite 定义？
```

### 3.3 long / short imbalance 是否只是噪声

```text
多头强平与空头强平的分布，是否表现为完全均匀随机，
还是已经出现可识别的集中、偏斜或 regime clustering？
```

### 3.4 单日/单币集中度是否过高

```text
当前 liquidation diagnostic 是否严重依赖少数 symbol、少数日期或少数高 notional 窗口？
```

### 3.5 source quality 是否足够稳定

```text
本地 forceOrder archive 是否存在明显字段缺失、解析不稳定、
异常集中或解析不稳定，导致继续等待 90d 没有意义？
```

---

## 4. 不回答的问题

Stage 1.4A-LQ30 明确不回答：

```text
是否存在可执行 alpha
是否可以进入 paper trading
是否可以进入 live trading
是否已经证明 full composite 通过
是否已经证明 liquidation 一定优于 funding/OI/price
```

本阶段不允许输出：

```text
alpha pass
paper/live
Stage 1.4B full composite pass
strategy candidate approved
```

---

## 5. 数据范围与输入

### 5.1 liquidation

主输入：

```text
data/trend_regime_force_orders_raw.jsonl
或轮转后的 backup raw archive 片段集合
```

要求：

```text
source_quality = force_order_archive
liquidation_notional_semantics = partial_snapshot_lower_bound
complete_liquidation_tape_claim_allowed = false
symbol scope = BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT / DOGEUSDT
history target = 15-30d
```

这里的 `local forceOrder snapshot` 指：

```text
本地自采 forceOrder archive rows
```

不是指：

```text
full exchange liquidation tape truth
```

也就是说，LQ30 的语义是：

```text
local forceOrder snapshot rows
```

而不是：

```text
complete liquidation tape truth
```

### 5.1.1 forceOrder row schema 兼容范围

implementation plan 必须明确支持至少两类输入 schema：

```text
flat:
  symbol, side, price, origQty, time

nested Binance forceOrder:
  o.s / o.S / o.p / o.q / o.T
```

并且必须输出：

```text
parsed_row_count
unknown_schema_count
missing_required_field_count
parse_error_count
```

不能假设本地 archive 永远只有单一 JSON 结构。

### 5.1.2 side 与 notional 语义

Stage 1.4A-LQ30 必须把 liquidation side 映射写死：

```text
SELL = long_liquidation = 多头被强制卖出
BUY  = short_liquidation = 空头被强制买回
```

并且第一版 notional 必须保守定义为：

```text
notional_usd = price * quantity
notional_conversion_quality = estimated_from_price_qty
notional_is_lower_bound = true
```

也就是说，本阶段可以使用 estimated notional，但不能把它写成完整真实 liquidation notional。

### 5.2 funding / OI / price

辅助输入：

```text
Stage 1.4A.1 已确认可用的 funding history
Stage 1.4A.1 已确认可用的 OI history
Stage 1.4A.1 已确认可用的 futures price history
```

这些数据在本阶段的角色不是直接做 alpha replay，而是用于：

```text
时间对齐检查
alignment overlap 统计
stress overlap preview 统计
future composite feasibility diagnostics
```

---

## 6. 核心输出

Stage 1.4A-LQ30 应输出以下 5 类 diagnostic artifact：

```text
liquidation_event_density_report
liquidation_funding_oi_overlap_report
long_short_imbalance_distribution
single_day_concentration_report
source_quality_report
```

### 6.1 liquidation_event_density_report

至少包含：

```text
event_count_by_symbol
nonzero_15m_window_count_by_symbol
nonzero_1h_window_count_by_symbol
event_days
symbols_with_events
max_single_symbol_event_share
max_single_day_event_share
```

### 6.2 liquidation_funding_oi_overlap_report

至少包含：

```text
data_alignment_overlap_window_count_15m
data_alignment_overlap_window_count_1h
data_alignment_overlap_event_days
symbols_with_alignment_overlap
windows_with_liquidation_and_funding_data
windows_with_liquidation_and_oi_data
windows_with_liquidation_and_price_data
windows_with_liquidation_and_funding_oi_price_data

stress_condition_overlap_window_count_15m
stress_condition_overlap_window_count_1h
stress_condition_overlap_event_days
windows_with_liquidation_and_funding_crowding
windows_with_liquidation_and_oi_change
windows_with_liquidation_and_price_move
windows_with_liquidation_and_funding_oi_price_stress
```

必须明确区分：

```text
data alignment overlap = 数据在同一 bucket 可对齐
stress condition overlap = liquidation 与 crowding 状态预定义 preview 条件同时出现
```

否则 overlap count 容易因为 funding / OI / price 本身几乎全时段存在，而失去诊断价值。

### 6.3 long_short_imbalance_distribution

至少包含：

```text
long_liquidation_notional_share_distribution
short_liquidation_notional_share_distribution
dominance_ratio_percentiles
imbalance_window_count_above_threshold
regime_cluster_examples
```

### 6.4 single_day_concentration_report

至少包含：

```text
top_1_day_event_share
top_3_days_event_share
top_1_symbol_event_share
top_3_symbols_event_share
max_single_day_notional_share
max_single_symbol_notional_share
top_1_day_notional_share
top_3_days_notional_share
top_1_symbol_notional_share
```

### 6.5 source_quality_report

至少包含：

```text
raw_row_count
raw_history_days
raw_recent_event_count_24h
duplicate_event_count
invalid_json_line_count
invalid_json_line_ratio
missing_timestamp_count
expected_symbol_coverage
actual_symbol_coverage
rotation_fragment_count
archive_gap_observations
collector_gap_verifiable
event_silence_gap_count
collector_observed_gap_count
quarantined_invalid_row_count
```

这里必须特别强调：

```text
forceOrder 是稀疏事件流；
没有事件，不等于 collector 掉线。
```

因此 `archive_gap_observations` 需要拆成两类：

```text
event_silence_gap = 没有 liquidation 事件，无法据此判断 uptime
collector_observed_gap = 有 heartbeat / process log / reconnect log 支持的采集断点
```

如果没有 heartbeat 或 collector status log 证据，则只能输出：

```text
collector_gap_verifiable = false
archive_gap_observations = event_sparse_stream_cannot_prove_uptime
```

---

## 7. 关键判定门槛

本阶段不是 alpha gate，但需要最小 diagnostic gate。

建议门槛：

```text
liquidation_history_days >= 15
symbols_with_events >= 3
event_days >= 10
data_alignment_overlap_event_days >= 10
max_single_symbol_event_share <= 0.60
max_single_day_event_share <= 0.35
top_1_day_notional_share <= 0.50
top_3_days_notional_share <= 0.70
top_1_symbol_notional_share <= 0.70
invalid_json_line_count = 0 preferred
invalid_json_line_ratio <= 0.001 acceptable if quarantined
duplicate_event_count should be explainable and low
```

解释：

- `liquidation_history_days >= 15`：低于 15d 时，只能说明 collector 在跑，不能说明这条线值得继续。
- `symbols_with_events >= 3`：至少跨 3 个币，避免完全是单币局部现象。
- `event_days >= 10`：至少跨多个自然日，避免只靠 1-2 次单边行情。
- `data_alignment_overlap_event_days >= 10`：如果和 funding / OI / price 连对齐都不够，就没必要继续谈 composite。
- `max_single_symbol_event_share <= 0.60` 与 `max_single_day_event_share <= 0.35`：防止 LQ30 结果被单币或单日完全主导。
- `top_1_day_notional_share <= 0.50`、`top_3_days_notional_share <= 0.70`、`top_1_symbol_notional_share <= 0.70`：防止事件数很多，但 notional 其实全靠某一天 BTC 暴跌撑起来。
- `invalid_json_line_ratio <= 0.001 acceptable if quarantined`：真实 collector 环境可能存在极少量损坏行，但必须 quarantine，不能静默吞掉。

如果这些最小 diagnostic gate 都不满足，则默认结论应为：

```text
stop_waiting_for_90d_until_source_quality_or_density_improves
```

---

## 8. 允许的结论与禁止的结论

### 8.1 顶层 decision / next_action

建议 summary 顶层固定枚举：

```text
decision:
  liquidation_diagnostic_promising
  liquidation_diagnostic_weak
  liquidation_diagnostic_unusable

next_action:
  continue_accumulating_exact_history
  continue_accumulating_but_do_not_wait_for_90d
  prioritize_vendor_sample
  stop_waiting_for_90d_until_source_quality_or_density_improves
```

### 8.2 允许的结论

```text
liquidation_diagnostic_promising
liquidation_diagnostic_weak
liquidation_diagnostic_unusable
liquidation_overlap_sufficient
liquidation_overlap_insufficient
continue_accumulating_exact_history
exact_history_not_yet_worth_waiting_for
vendor_sample_still_desirable
```

### 8.3 禁止的结论

```text
alpha_pass
strategy_pass
paper_trading_allowed
live_trading_allowed
stage1_4_full_composite_pass
liquidation_alone_is_profitable
```

---

## 9. 与 Stage 1.4B-Lite 的关系

Stage 1.4A-LQ30 不是 `B-Lite` 的替代品。

两者关系应为：

```text
LQ30 = liquidation utility diagnostic
B-Lite = crowding label replay precheck
```

最终决策应看组合结果，而不是单条线：

```text
B-Lite fail + LQ30 weak
-> 停止免费 derivatives stress alpha 路线，只保留 live liquidation collector 作为长期数据资产

B-Lite fail + LQ30 promising
-> liquidation 可能真的是关键缺失腿；不做 alpha 通过结论，但值得继续积累 exact history 或争取 vendor sample

B-Lite pass + LQ30 weak
-> crowding label 可能有一些结构，但 liquidation 暂未显示明显增量；可继续低成本 crowding replay，不急于扩大 liquidation 成本投入

B-Lite pass + LQ30 promising
-> 最值得继续进入更长历史 local forceOrder replay 或 vendor-grade full composite
```

---

## 10. 为什么不是直接等待 90d

直接等待 90d 的问题在于：

```text
时间成本高
如果 source quality 或 overlap 先天不足，会把坏方向拖很久
如果事件高度集中于单币或单日，90d 也未必能自然修复
```

LQ30 的价值是提前回答：

```text
这条 liquidation 线值不值得继续积累？
如果值得，最缺的是时间长度，还是 source 质量 / vendor 支持？
```

因此它是一个：

```text
early go/no-go diagnostic
```

而不是：

```text
mini backtest
```

---

## 11. 对 implementation plan 的硬要求

下一份 implementation plan 必须明确：

```text
所有 LQ30 阈值进入 configs/base.py
不在 src/ 中写死 magic number
```

最低需要集中配置的常量包括：

```text
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_HISTORY_DAYS = 15
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_SYMBOLS_WITH_EVENTS = 3
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_EVENT_DAYS = 10
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ALIGNMENT_OVERLAP_EVENT_DAYS = 10
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_SYMBOL_EVENT_SHARE = 0.60
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_DAY_EVENT_SHARE = 0.35
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_DAY_NOTIONAL_SHARE = 0.50
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP3_DAYS_NOTIONAL_SHARE = 0.70
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_SYMBOL_NOTIONAL_SHARE = 0.70
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_INVALID_JSON_LINE_RATIO = 0.001
```

同时必须写死聚合窗口定义：

```text
15m bucket = floor(timestamp_ms / 15m) * 15m
1h bucket  = floor(timestamp_ms / 1h) * 1h
bucket_end_ms = bucket_start_ms + interval_ms
available_at_ms = bucket_end_ms + configured_lag_ms
```

LQ30 虽然不做收益 replay，但 overlap 统计也必须按固定 UTC bucket，不允许临时滑窗调参。

## 12. 当前推荐决策

```text
decision = proceed_to_stage1_4a_lq30_local_forceorder_snapshot_diagnostic_design
primary_goal = determine_whether_waiting_for_90d_local_forceorder_history_is_worth_it
parallel_secondary_track = stage1_4b_lite_funding_oi_price_crowding_replay
alpha_interpretation_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
full_composite_claim_allowed = false
complete_liquidation_tape_claim_allowed = false
```

一句话总结：

```text
Stage 1.4A-LQ30 的任务不是证明 liquidation 有 alpha，
而是尽快判断“local forceOrder snapshot 这条腿是否值得继续投入时间与数据成本”。
```
