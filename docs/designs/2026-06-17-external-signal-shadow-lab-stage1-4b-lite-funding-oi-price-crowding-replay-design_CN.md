# External Signal Shadow Lab Stage 1.4B-Lite Funding/OI/Price Crowding Replay Design

日期：2026-06-17

## 1. 设计结论

Stage 1.4B-Lite 的目标不是替代 full composite，也不是重新包装旧的 funding/OI 调参路线。

它只回答一个更窄的问题：

```text
在不使用 liquidation 条件的前提下，
funding / OI / futures price 这组 crowding label
是否仍然具备最小可重复结构，
足以作为 derivatives stress 方向的低成本 precheck？
```

推荐结论：

```text
decision = proceed_to_stage1_4b_lite_funding_oi_price_crowding_replay_design
scope = funding_oi_price_crowding_replay_only
liquidation_used = false
full_derivatives_stress_composite_claim_allowed = false
stage1_4b_full_composite_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

Stage 1.4B-Lite 的正确定位是：

```text
cheap crowding precheck
```

而不是：

```text
full derivatives stress pass
liquidation substitute
paper/live handoff
```

---

## 2. 为什么需要 B-Lite

当前 Stage 1.4 的现实状态是：

```text
LQ30 local forceOrder snapshot diagnostic 已经给出 promising，
说明 liquidation 这条本地代理腿值得继续累积历史；
但 >=90d local liquidation 仍未完成，
vendor-grade liquidation sample 仍未稳定取得。
```

如果这时完全停住等待 liquidation 历史继续累积，会产生两个问题：

1. 研究节奏停滞  
2. 无法尽快回答一个更便宜但重要的问题：

```text
即使暂时去掉 liquidation，
funding / OI / futures price 这组 crowded-state label，
是否还能形成任何最小结构？
```

这里必须强调：

```text
B-Lite 不是用来证明 liquidation 不重要；
B-Lite 只是用来判断 crowding-only 这条便宜支线是否完全没有增量。
```

如果 B-Lite 完全失败，而 LQ30 同时偏弱，那么免费 derivatives stress alpha 路线就更接近应当停止。  
如果 B-Lite 完全失败，但 LQ30 依旧 promising，则更可能说明：

```text
liquidation 不是装饰，而是关键缺失腿。
```

因此 B-Lite 必须被设计成：

```text
secondary track
```

而不是主线替代品。

---

## 3. 本阶段要回答的问题

Stage 1.4B-Lite 只回答以下 4 个问题：

### 3.1 funding / OI / price 是否仍能定义稳定事件

```text
在预注册的 4h detection window 上，
funding / OI / futures price 是否能够定义出事件数足够、跨日足够、跨币足够的 crowding event？
```

### 3.2 这些事件是否优于简单 price baseline

```text
crowding event 的 forward performance，
是否至少优于简单 price_move_1h baseline？
```

### 3.3 这些事件是否优于 matched random baseline

```text
在 symbol / hour matched random baseline 下，
crowding event 是否仍然保留正 excess 结构？
```

### 3.4 如果失败，失败是结构性失败还是“缺 liquidation 条件”

```text
如果 B-Lite 失败，
它只能说明 crowding-only 路线弱，
不能自动推导 full composite 也失败。
```

---

## 4. 不回答的问题

Stage 1.4B-Lite 明确不回答：

```text
liquidation 是否已经不重要
full composite 是否通过
paper/live 是否可进入
final alpha 是否成立
```

本阶段不允许输出：

```text
full derivatives stress composite pass
liquidation unnecessary
paper/live approved
strategy candidate approved
```

---

## 5. 数据范围与输入

### 5.1 funding

来源：

```text
Stage 1.4A.1 已验证的 Binance settled funding history
```

要求：

```text
funding rows must be settled rows
no future funding value may be used before its known time
```

### 5.2 OI

来源：

```text
Stage 1.4A.1 已验证的 Binance Vision / local archive OI history
```

要求：

```text
OI rows must include timestamped historical values
OI change must be computed using only rows available before event entry
```

### 5.3 price

来源：

```text
Binance futures klines preferred
spot proxy only if futures bars unavailable
```

要求：

```text
event definition and replay entry must use futures price if available
```

### 5.4 liquidation

本阶段固定：

```text
liquidation_used = false
```

并且 summary 必须写出：

```json
{
  "liquidation_used": false,
  "full_derivatives_stress_composite_claim_allowed": false,
  "stage1_4b_full_composite_allowed": false
}
```

---

## 6. 候选事件族与预注册定义

Stage 1.4B-Lite 第一版只允许 3 个候选族，不允许无限扩展：

### 6.1 `oi_expansion_trend_confirmation`

目标：

```text
验证 “price trend + OI expansion” 是否比纯 price move 更像杠杆趋势确认。
```

第一版硬定义：

```text
event_detection_window = 4h
entry_timeframe = 15m
primary_forward_window = 4h
secondary_forward_windows = 1h / 12h (report-only)
entry_delay_bars = 1

event_time_ms = 4h 检测窗口结束时点
event_available_at_ms = event_time_ms + configured_entry_delay
entry_bar = event_available_at_ms 之后第一根可交易 15m bar

price_4h_return_pct =
  (price_asof_event - price_asof_event_minus_4h) / price_asof_event_minus_4h

oi_4h_change_pct =
  (OI_asof_event - OI_asof_event_minus_4h) / OI_asof_event_minus_4h

funding_state_at_event =
  latest funding record where funding_time_ms <= event_available_at_ms - funding_publish_lag_ms

long trigger:
  price_4h_return_pct >= +1.5%
  oi_4h_change_pct >= +2.0%
  abs(funding_percentile) < 90th percentile

short diagnostic trigger:
  price_4h_return_pct <= -1.5%
  oi_4h_change_pct >= +2.0%
  abs(funding_percentile) < 90th percentile

exclusions:
  oi_asof_event stale beyond max_oi_staleness_ms
  oi history points below min_oi_history_points
  funding row unavailable under as-of rule
  futures price row unavailable

signed_replay_only = true
execution_intent_allowed = false
```

### 6.2 `funding_oi_crowding_unwind`

目标：

```text
验证 “极端 funding 拥挤 + OI contraction” 是否对应 crowded unwind 状态切换。
```

第一版硬定义：

```text
event_detection_window = 4h
entry_timeframe = 15m
primary_forward_window = 4h
secondary_forward_windows = 1h / 12h (report-only)
entry_delay_bars = 1

positive funding extreme = long crowded
negative funding extreme = short crowded

long crowded unwind trigger:
  funding_percentile >= 90th percentile
  oi_4h_change_pct <= -2.0%
  price_4h_return_pct <= -1.0%
  signed direction = short / avoid-long diagnostic

short crowded unwind trigger:
  funding_percentile <= 10th percentile
  oi_4h_change_pct <= -2.0%
  price_4h_return_pct >= +1.0%
  signed direction = long

event_time_ms / event_available_at_ms / entry_bar:
  与 candidate_1 相同

exclusions:
  future funding row usage forbidden
  stale OI forbidden
  missing futures price forbidden

signed_replay_only = true
execution_intent_allowed = false
```

### 6.3 `oi_contraction_after_price_flush`

目标：

```text
验证 “price flush + OI contraction” 作为去杠杆近似状态，是否保留最小结构。
```

第一版硬定义：

```text
event_detection_window = 4h
entry_timeframe = 15m
primary_forward_window = 4h
secondary_forward_windows = 1h / 12h (report-only)
entry_delay_bars = 1

down flush trigger:
  price_4h_return_pct <= -2.0%
  oi_4h_change_pct <= -2.0%
  signed direction = rebound long diagnostic

up squeeze trigger:
  price_4h_return_pct >= +2.0%
  oi_4h_change_pct <= -2.0%
  signed direction = reversal short diagnostic

liquidation_observed = false
deleveraging_proxy_only = true
signed_replay_only = true
execution_intent_allowed = false
```

### 6.4 baseline-only 对照

必须保留：

```text
price_move_1h baseline
random baseline (symbol/hour matched)
```

这样才能回答：

```text
crowding label 是否真的比纯价格冲击多提供了一点结构。
```

---

## 7. 事件定义原则与 as-of 对齐

Stage 1.4B-Lite 第一版必须预注册单一参数组，避免参数搜索。

第一版固定：

```text
event_detection_window = 4h
entry_timeframe = 15m
primary_forward_window = 4h
secondary_forward_windows = 1h / 12h (report-only)
```

不允许：

```text
不停尝试 15m / 1h / 2h / 3h / 6h / 8h / 24h
不停改 percentile / threshold / return gate
事后挑选表现最好的一组窗口
```

所有候选必须满足：

```text
entry_delay_bars >= 1
available_at_ms anchored
no future funding record
no future OI row
no future price bar
```

funding as-of 规则必须固定为：

```text
funding_state_at_event =
  latest funding record where funding_time_ms <= event_available_at_ms - funding_publish_lag_ms
```

OI as-of 规则必须固定为：

```text
OI_asof_event =
  latest OI row <= event_available_at_ms

OI_asof_event_minus_4h =
  latest OI row <= event_available_at_ms - 4h

OI_4h_change_pct =
  (OI_asof_event - OI_asof_event_minus_4h) / OI_asof_event_minus_4h
```

同时必须受以下约束：

```text
max_oi_staleness_ms
min_oi_history_points
```

price 方向语义必须固定为：

```text
price_4h_return_pct > 0 代表上行趋势/上冲
price_4h_return_pct < 0 代表下行趋势/下砸
```

---

## 8. 评价方法

Stage 1.4B-Lite 允许做 replay 和 baseline，但仍然是 research-only。

### 8.1 主评价方法

主评价指标固定为：

```text
primary_metric = terminal_return_4h_net_bps_after_50bps_median
```

主 baseline 固定为：

```text
symbol_and_hour_of_day_matched_random_baseline
```

额外 baseline：

```text
price_move_1h baseline
```

### 8.2 成本模型

必须至少评估：

```text
cost_scenarios_bps = 30 / 50 / 80
```

第一版 gate 以 `50bps` 为主。

### 8.3 随机基准

必须运行：

```text
random_baseline_trials >= 500
```

要求：

```text
event_count 完全匹配
symbol distribution 完全匹配
hour-of-day 尽量精确匹配，无法匹配时允许 ±1h
排除 candidate timestamp
forward window 必须完整
random_seed 固定
baseline_sampling_failure_count 必须输出
baseline_sampling_insufficient 必须输出
```

---

## 9. 通过门槛

Stage 1.4B-Lite 只有通过以下门槛，才允许写成 “crowding-only structure present”：

```text
event_count >= 100
event_days >= 20
symbols_with_events >= 3
median_net_return_after_50bps > 0
baseline_excess_net_bps > 0
left_tail_vs_baseline >= 0
top_5_positive_events_gross_profit_share <= 0.30
must beat price_move_1h baseline
must beat symbol/hour matched random baseline
```

建议再加两个集中度约束：

```text
max_single_symbol_event_share <= 0.50
max_single_day_event_share <= 0.20
top_5_abs_pnl_share reported
```

这些门槛只用于：

```text
判断 crowding-only 是否保留最小结构
```

而不是：

```text
允许进入 paper/live
```

---

## 10. 与 LQ30 的组合决策矩阵

Stage 1.4B-Lite 不应单独决定整条路线生死，必须和 LQ30 联合解释。

### 10.1 `B-Lite fail + LQ30 weak`

解释：

```text
crowding-only 路线弱；
local liquidation diagnostic 也弱；
免费 derivatives stress alpha 路线接近应停止。
```

动作：

```text
stop_free_derivatives_stress_alpha_route
keep_live_liquidation_collector_as_data_asset
```

### 10.2 `B-Lite fail + LQ30 promising`

解释：

```text
crowding-only 不够，
但 liquidation 可能是关键缺失腿。
```

动作：

```text
continue_accumulating_exact_history
or prioritize_vendor_liquidation_sample
```

### 10.3 `B-Lite pass + LQ30 weak`

解释：

```text
crowding-only 有一定结构，
但当前 liquidation local source 暂时没显示出足够增量价值。
```

动作：

```text
continue_crowding_replay_refinement
do_not_upgrade_to_full_composite_yet
```

### 10.4 `B-Lite pass + LQ30 promising`

解释：

```text
crowding-only 有最小结构，
local liquidation 也显示值得继续等。
```

动作：

```text
prepare_stage1_4c_joint_decision_review
continue_accumulating_exact_history_or_vendor_sample
do_not_upgrade_to_full_composite_before_90d_or_vendor_grade_liquidation
```

---

## 11. 失败路径

### 11.1 旧问题重演

最大风险是：

```text
B-Lite 滑回 funding / OI 老问题重跑一遍
```

防法：

```text
固定候选数 = 3
固定 baseline
固定 primary metric
固定 review gate
```

### 11.2 误把 B-Lite fail 当成 full composite fail

这是最危险的解释错误。

必须明确：

```text
B-Lite fail != liquidation+funding+OI+price full composite fail
```

review 与 summary 必须硬写：

```json
{
  "b_lite_failure_interpretation": "crowding_only_failed_not_full_composite_failed",
  "liquidation_missing_leg_remains_unresolved": true
}
```

### 11.3 误把 B-Lite pass 当成可交易

也必须明确：

```text
B-Lite pass != strategy ready
```

---

## 12. 顶层输出

Stage 1.4B-Lite 顶层 summary 至少应包含：

```json
{
  "decision": "crowding_lite_promising|crowding_lite_weak|crowding_lite_failed",
  "next_action": "...",
  "liquidation_used": false,
  "full_derivatives_stress_composite_claim_allowed": false,
  "stage1_4b_full_composite_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "signed_replay_only": true,
  "execution_intent_allowed": false,
  "b_lite_failure_interpretation": "crowding_only_failed_not_full_composite_failed",
  "liquidation_missing_leg_remains_unresolved": true
}
```

review 必须明确写出：

```text
这只是 funding/OI/price crowding replay；
它不能替代 liquidation composite；
它只能作为 crowding precheck。
```

---

## 13. 配置要求

所有阈值必须进入 `configs/base.py`，不得写死在 `src/`。

至少包括：

```text
EXTERNAL_SIGNAL_STAGE1_4B_LITE_EVENT_DETECTION_WINDOW_HOURS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_ENTRY_DELAY_BARS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_EXTREME_PERCENTILE
EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_EXPANSION_4H_PCT
EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT
EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_RETURN_4H_PCT
EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_PUBLISH_LAG_MS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_OI_STALENESS_MS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_OI_HISTORY_POINTS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_RANDOM_BASELINE_TRIALS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_COST_SCENARIOS_BPS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_COUNT
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_EVENT_DAYS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_SYMBOLS_WITH_EVENTS
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_SYMBOL_EVENT_SHARE
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_SINGLE_DAY_EVENT_SHARE
EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_TOP5_POSITIVE_GROSS_PROFIT_SHARE
```

---

## 14. 本阶段后的正确决策

当前正确的推进顺序应为：

```text
1. 完成 Stage 1.4B-Lite crowding replay 设计与实现
2. 将 B-Lite 结果与 LQ30 real diagnostic 联合解释
3. 决定是否继续等待 >=90d local liquidation history
4. 若两条线都支持，再考虑进入更完整 composite 定义
```

不正确的推进顺序是：

```text
把 B-Lite 直接当成 mainline alpha
把 B-Lite fail 当成 liquidation 无意义
把 B-Lite pass 当成 full composite 通过
```
