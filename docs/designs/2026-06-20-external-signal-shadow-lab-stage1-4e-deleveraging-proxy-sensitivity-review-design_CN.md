# External Signal Shadow Lab Stage 1.4E Deleveraging Proxy Sensitivity Review Design

日期：2026-06-20

## 1. 目标

Stage 1.4E 是一个 **Deleveraging Proxy Sensitivity Review（去杠杆代理信号敏感性评审）**。

它的出现原因很明确：

```text
Stage 1.4D Fuller Composite Readiness Review 要求更长 liquidation history，
但当前本地 forceOrder / liquidation history 仍未达到 design readiness 门槛。
```

因此 Stage 1.4E 只回答一个更窄的问题：

```text
在不使用 forceOrder、不使用 vendor liquidation、不等待 45d+ 本地 liquidation history 的前提下，
OI drop + price flush 能否构造出一个低成本 deleveraging stress proxy，
并在历史 replay 中显示出足够事件密度、分散性和 baseline excess？
```

本阶段的正确定位是：

```text
low-cost deleveraging proxy sensitivity review
```

不是：

```text
liquidation substitute
full composite replay
paper/live handoff
strategy pass
```

本阶段顶层必须写死：

```json
{
  "decision": "deleveraging_proxy_failed|deleveraging_proxy_inconclusive|deleveraging_proxy_survives_sensitivity_review",
  "secondary_status": "none|inconclusive_promising_sparse",
  "deleveraging_proxy_only": true,
  "liquidation_used": false,
  "force_order_used": false,
  "vendor_data_used": false,
  "liquidation_claim_allowed": false,
  "full_composite_claim_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "not_b_lite_restart": true,
  "previous_b_lite_crowding_only_branch_stopped": true,
  "stage1_5_allowed_only_as_filter": true
}
```

---

## 2. 为什么需要 Stage 1.4E

Stage 1.4C 已经正式收敛：

```text
B-Lite crowding-only branch = stopped
LQ30 local forceOrder snapshot = promising but still accumulating
full composite design = not ready yet
```

Stage 1.4D 进一步指出，进入 fuller composite design 至少需要更成熟的 liquidation 数据腿。

现实问题是：

```text
liquidation_history_days >= 45
```

当前无法马上满足。

因此 Stage 1.4E 允许做一次低成本历史代理验证：

- 如果失败：停止用 OI/price proxy 代替 liquidation 的想法，liquidation 只继续作为长期数据资产。
- 如果有结构：只能进入 `Stage 1.4F Deleveraging Proxy + External Catalyst Filter`，不能直接进入 live 或 full composite。

这一步的价值不是“证明 liquidation 可被替代”，而是快速回答：

```text
OI drop + price flush 这个代理信号，是否至少值得进入下一层外部催化过滤？
```

它还必须明确：

```text
this is not B-Lite restart
this is a two-parameter proxy sensitivity review
purpose = test_whether_oi_price_proxy_can_survive_as_filter
```

B-Lite 已经正式停止的是 `funding / OI / price crowding-only` 支线；
Stage 1.4E 只测试更窄的 `OI drop + price flush` 去杠杆代理，不重新打开 B-Lite 调参。

---

## 3. 数据输入

Stage 1.4E 只允许以下输入。

### 3.1 OI history

来源优先级：

```text
1. local Binance Vision / UM daily metrics OI archive
2. Binance public data metrics archive built by project scripts
```

字段要求：

```text
symbol
timestamp_ms
sumOpenInterest
sumOpenInterestValue
source
source_file
```

触发条件必须优先使用：

```text
sumOpenInterest
```

原因：

```text
sumOpenInterestValue 会被价格变化本身影响，
不能作为 OI drop trigger 的主字段。
```

`sumOpenInterestValue` 只允许用于：

```text
notional diagnostic
concentration diagnostic
source quality report
```

### 3.2 Futures price history

来源：

```text
Binance USD-M futures klines
```

字段要求：

```text
symbol
bar_start_ms
open
high
low
close
volume / quote_volume
```

必须使用 futures price。Spot price 只能作为缺失诊断，不允许作为 primary trigger。

### 3.3 Funding context

Funding 只作为 context，不参与 Stage 1.4E 的 proxy trigger。

允许输出：

```text
funding_state_at_event
funding_percentile_at_event
funding_extreme_share
```

禁止输出：

```text
funding confirms liquidation
funding makes proxy research-grade
```

### 3.4 禁止输入

Stage 1.4E 明确不使用：

```text
forceOrder raw archive
vendor liquidation data
manual liquidation labels
paper/live order data
```

---

## 4. 预注册候选参数

本阶段只允许两组参数。

不允许新增第三组，不允许事后调参续命。

### 4.1 Candidate A: `deleveraging_proxy_15m`

Down flush:

```text
price_return_15m <= -2.0%
oi_change_15m <= -3.0%
signed_direction = +1
event_label = down_flush_deleveraging_proxy
```

Up squeeze:

```text
price_return_15m >= +2.0%
oi_change_15m <= -3.0%
signed_direction = -1
event_label = up_squeeze_deleveraging_proxy
```

### 4.2 Candidate B: `deleveraging_proxy_1h`

Down flush:

```text
price_return_1h <= -3.0%
oi_change_1h <= -5.0%
signed_direction = +1
event_label = down_flush_deleveraging_proxy
```

Up squeeze:

```text
price_return_1h >= +3.0%
oi_change_1h <= -5.0%
signed_direction = -1
event_label = up_squeeze_deleveraging_proxy
```

### 4.3 Direction semantics

Stage 1.4E 使用 signed replay，但不表达 live execution intent。

```text
down flush + OI drop -> rebound-long diagnostic
up squeeze + OI drop -> reversal-short diagnostic
```

Review 必须输出：

```json
{
  "signed_replay_only": true,
  "short_execution_intent_allowed": false,
  "borrow_or_margin_feasibility_checked": false
}
```

---

## 5. Window 与 timestamp 规则

### 5.1 15m proxy

```text
price_return_15m = close_t / open_t - 1
oi_change_15m = OI_asof_bucket_end / OI_asof_bucket_start - 1
event_time_ms = bucket_end_ms
event_available_at_ms = bucket_end_ms + configured_data_lag_ms
entry_bar = first 15m futures bar after event_available_at_ms
```

### 5.2 1h proxy

```text
price_return_1h = close_t / open_t - 1
oi_change_1h = OI_asof_bucket_end / OI_asof_bucket_start - 1
event_time_ms = bucket_end_ms
event_available_at_ms = bucket_end_ms + configured_data_lag_ms
entry_bar = first 15m futures bar after event_available_at_ms
```

`configured_data_lag_ms` 必须进入 `configs/base.py`：

```text
EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_CONFIGURED_DATA_LAG_MS = 300_000
```

默认使用 5 分钟，避免 Binance Vision metrics / 本地归档生成延迟被错误当成即时可用数据。

### 5.3 OI alignment policy

OI rows must be aligned by as-of lookup:

```text
OI_asof_bucket_start = latest OI row <= bucket_start_ms
OI_asof_bucket_end = latest OI row <= bucket_end_ms
```

Hard requirements:

```text
max_oi_staleness_ms must be configured
oi_interval_coverage must be reported
missing_oi_bucket_count must be reported
```

### 5.4 OI interval support gate

Stage 1.4E 必须先判断 OI 数据频率是否支持候选窗口。

Summary 必须输出：

```text
oi_median_interval_ms
oi_p95_interval_ms
candidate_window_supported
```

15m proxy 的准入条件：

```text
oi_median_interval_ms <= 15m
oi_p95_interval_ms <= 30m
```

1h proxy 的准入条件：

```text
oi_median_interval_ms <= 1h
oi_p95_interval_ms <= 2h
```

如果不满足，candidate 必须输出：

```text
candidate_status = data_unsupported
```

并且不得继续 replay。否则 15m / 1h proxy 会把旧 OI 数据误当成当前窗口变化。

### 5.5 Event cooldown

同一波去杠杆不能被连续 bucket 重复计数。

cooldown key：

```text
symbol + candidate_name + event_label + signed_direction
```

配置：

```text
EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_COOLDOWN_MS = 3_600_000
EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_COOLDOWN_MS = 14_400_000
```

规则：

```text
15m candidate: same cooldown key within 1h only keeps first event
1h candidate: same cooldown key within 4h only keeps first event
```

---

## 6. Evaluation

每个 candidate 必须评估：

```text
forward_windows = 1h / 4h / 12h
cost_scenarios_bps = 30 / 50 / 80
primary_cost_bps = 50
random_baseline_trials >= 500
```

必须包含两个 baseline：

```text
symbol/hour matched random baseline
price_move baseline
```

Random baseline 要求：

- event count 与 candidate 完全一致
- symbol distribution 匹配
- hour-of-day 匹配，必要时允许 ±1h
- 排除 candidate timestamps
- forward window 必须完整
- random seed 固定
- 输出 sampling failure count

Price baseline 要求：

```text
15m candidate 对比 simple 15m price_move baseline
1h candidate 对比 simple 1h price_move baseline
```

Price baseline 的方向和匹配规则必须固定：

```text
down flush baseline:
  price_return <= same negative threshold
  signed_direction = +1

up squeeze baseline:
  price_return >= same positive threshold
  signed_direction = -1
```

Price baseline 必须使用：

```text
same symbol universe
same event window
same replay cost
same forward windows
same cooldown rule
```

否则 price baseline 与 proxy candidate 不可比。

---

## 7. Required Metrics

Summary 必须输出以下指标。

### 7.1 Event density

```text
event_count
event_days
symbols_with_events
down_flush_event_count
up_squeeze_event_count
```

### 7.2 Concentration

```text
max_single_day_event_share
max_single_symbol_event_share
top_5_positive_events_gross_profit_share
top_5_abs_pnl_share
```

### 7.3 Replay performance

```text
median_net_return_bps_after_50bps
mean_net_return_bps_after_50bps
left_tail_bps_after_50bps
baseline_excess_net_bps
price_baseline_excess_net_bps
```

`left_tail_bps_after_50bps` 固定使用 p05：

```text
EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_LEFT_TAIL_PERCENTILE = 5
```

不允许在 review 阶段临时改成 p01 / p10。接飞刀类 proxy 最需要固定左尾口径。

### 7.4 Source quality

```text
oi_history_days
price_history_days
oi_interval_coverage
price_interval_coverage
missing_oi_bucket_count
missing_price_bucket_count
stale_oi_bucket_count
stale_price_bucket_count
max_oi_staleness_ms_observed
max_price_gap_ms_observed
symbol_coverage
source_file_count
checksum_or_archive_validation_available
```

---

## 8. Decision Rules

Stage 1.4E 顶层只允许三种结论。

### 8.1 `deleveraging_proxy_failed`

含义：

```text
OI drop + price flush proxy 不足以作为 liquidation substitute。
```

后续动作：

```text
stop_oi_price_deleveraging_proxy_as_liquidation_substitute
continue_local_liquidation_as_long_term_data_asset
move_next_primary_research_to_external_catalyst
```

### 8.2 `deleveraging_proxy_inconclusive`

含义：

```text
数据质量、事件密度或 baseline sampling 不足，无法形成稳定判断。
```

后续动作：

```text
do_not_tune_parameters
fix_data_or_stop_proxy_branch
```

### 8.2.1 `secondary_status = inconclusive_promising_sparse`

如果 proxy 表现方向较好，但样本量仍不足以通过正式门槛，顶层 `decision` 仍必须是：

```text
deleveraging_proxy_inconclusive
```

同时允许设置：

```text
secondary_status = inconclusive_promising_sparse
```

建议条件：

```text
event_count >= 30
event_days >= 10
symbols_with_events >= 3
median_net_return_bps_after_50bps > 0
baseline_excess_net_bps > 0
price_baseline_excess_net_bps > 0
concentration not out of control
```

这个状态只能说明 proxy 值得作为弱候选进入后续过滤讨论。
它不允许输出 alpha、paper/live、full composite pass，也不允许事后调参续命。

### 8.3 `deleveraging_proxy_survives_sensitivity_review`

含义：

```text
代理信号有足够事件密度、分散性和 baseline excess，
值得进入 external catalyst filter。
```

后续动作：

```text
next_stage = Stage 1.4F Deleveraging Proxy + External Catalyst Filter
live_allowed = false
full_composite_allowed = false
```

---

## 9. Pass Gates

Stage 1.4E 不使用 B-Lite 的 crowding-only 解释，但仍保留研究级防自欺门槛。

建议通过门槛：

```text
event_count >= 100
event_days >= 20
symbols_with_events >= 3
median_net_return_bps_after_50bps > 0
baseline_excess_net_bps > 0
price_baseline_excess_net_bps > 0
left_tail_bps_after_50bps >= random_baseline_left_tail_bps
top_5_positive_events_gross_profit_share <= 0.30
max_single_day_event_share <= 0.25
max_single_symbol_event_share <= 0.60
```

如果事件低于门槛但表现很好，结论最多只能是：

```text
deleveraging_proxy_inconclusive
secondary_status = inconclusive_promising_sparse
```

不能写成 pass。

---

## 10. Failure Interpretation

如果 Stage 1.4E 失败，只能说明：

```text
OI drop + price flush 不能作为低成本 liquidation proxy 替代。
```

不能说明：

```text
真实 liquidation 没有价值
local forceOrder archive 没有继续积累价值
external catalyst 方向失败
```

如果 Stage 1.4E 通过，也只能说明：

```text
deleveraging proxy 值得进入 external catalyst filter。
```

不能说明：

```text
liquidation alpha confirmed
full composite confirmed
paper/live allowed
```

---

## 11. Implementation Notes

Implementation plan 必须把所有阈值写入 `configs/base.py`，不要写死在 `src/`。

建议配置前缀：

```text
EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_...
```

必须新增或复用：

- OI / futures kline loader
- 15m / 1h proxy event detector
- signed replay evaluator
- random baseline evaluator
- price baseline evaluator
- source quality report
- Chinese review generator

允许复用 Stage 1.4B-Lite 的 replay / baseline 框架，但必须保持 Stage 1.4E 的语义独立。

Implementation plan 必须覆盖以下测试：

```text
test_15m_candidate_rejected_when_oi_interval_too_sparse
test_1h_candidate_supported_when_oi_interval_within_limit
test_uses_sum_open_interest_not_sum_open_interest_value_for_trigger
test_down_flush_proxy_signed_long
test_up_squeeze_proxy_signed_short_but_no_short_execution_intent
test_configured_data_lag_applied_to_available_at
test_event_cooldown_deduplicates_cluster
test_price_baseline_uses_same_direction_and_cooldown
test_left_tail_uses_p05
test_sparse_positive_result_is_inconclusive_not_pass
test_failed_result_does_not_invalidate_real_liquidation_or_external_catalyst
```

---

## 12. 与 Stage 1.4D 的关系

Stage 1.4E 不是绕过 Stage 1.4D。

它只是因为 Stage 1.4D 当前被 liquidation history length 卡住，所以增加一个低成本分支：

```text
Can OI/price deleveraging proxy provide enough signal
to justify an external catalyst filter?
```

如果 1.4E 失败：

```text
1.4D 继续等待 local liquidation history 或 vendor sample；
1.4E proxy branch 停止。
```

如果 1.4E 通过：

```text
进入 1.4F proxy + external catalyst filter；
仍不进入 full composite 或 live。
```
