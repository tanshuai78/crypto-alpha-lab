# External Signal Shadow Lab Stage 1.3 Candidate Signal Discovery Design

日期：2026-06-13

## 1. 设计结论

Stage 1.3 的目标不是继续扩展 collector，也不是证明 Gate ticker snapshot 有 alpha。

Stage 1.3 只回答一个更窄、更关键的问题：

```text
在现有 Gate public ticker snapshot / 历史 OHLCV 能表达的信息范围内，是否能预注册出少数候选事件，并在历史 replay 中表现出高于随机 baseline 的后续结构？
```

最终建议：执行 Stage 1.3，但必须严格限定范围。

```text
decision = proceed_to_stage1_3_candidate_signal_discovery_design
scope = Gate ticker snapshot derived candidate signals only
collector_expansion_allowed = false
live_shadow_required_now = false
historical_replay_first = true
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false until review approved
```

这一步的价值不是赚钱，而是快速证伪或保留少数候选。

如果 Stage 1.3 失败，结论应是：停止 Gate ticker snapshot 派生信号方向，而不是增加阈值、增加币种、提高采样频率或继续写 collector。

---

## 2. 当前阶段定位

External Signal Shadow Lab 已完成：

```text
Stage 0: Shadow Replay Engine
Stage 1.0: File-backed Connector
Stage 1.1: Manual Payload Dry Run
Stage 1.2: Gate Public Read-Only Collector
```

这些阶段已经证明：

```text
外部 raw payload 可以被安全接入
connector 可以标准化事件
cex_market_snapshot 可以 observation-only 进入研究系统
collector 可以公开只读采集 Gate ticker
```

但它们没有证明：

```text
Gate ticker snapshot 有 alpha
短周期价格/成交量事件可交易
任何事件可以进入 paper/live
任何事件可以生成 directional order
```

因此 Stage 1.3 必须从“采集是否可行”切换到“候选信号是否有研究价值”。

---

## 3. 为什么不继续扩 collector

继续扩 collector 的诱惑很强，但当前不是瓶颈。

当前瓶颈是：

```text
没有被证实有信息含量的候选事件。
```

继续做以下事情都会拖慢研究速度：

```text
继续增加 Gate symbols
继续接 Binance / OKX collector
继续加网页 crawler
继续做长期 realtime collection
继续把所有字段都收进来
```

这些动作只会让数据更多，不会自动让信号更好。

Stage 1.3 的核心原则是：

```text
先证明当前低成本数据能不能派生出结构；
如果不能，停止该数据源方向；
只有证明字段不足但框架有希望时，才考虑更高信息密度 source。
```

---

## 4. Stage 1.3 的输入与输出

### 4.1 输入

第一版只允许使用：

```text
Gate Stage 1.2 public ticker snapshot 字段
历史 OHLCV / volume 数据
BTC baseline 数据
已存在的 Stage 0 replay 组件
```

允许字段类型：

```text
symbol
available_at-like timestamp
last / close
quote_volume
base_volume
change_percentage
historical rolling volume
historical rolling return
BTC return baseline
```

禁止输入：

```text
orderbook depth
funding
open interest
liquidation
on-chain
news/social
wallet / private endpoint
未来价格字段
事后挑选事件标签
```

这些不是永远禁止，而是 Stage 1.3 第一版禁止。原因是第一版要判断 Gate ticker / OHLCV 这类低维数据是否仍有初筛价值。

### 4.1.1 历史数据 venue 口径

Stage 1.3 必须明确历史 OHLCV venue。

优先方案：

```text
historical_venue = gate
```

原因：Stage 1.2 的真实 collector 来自 Gate public ticker，历史 replay 如果也使用 Gate OHLCV，venue 一致性最好。

允许降级方案：

```text
historical_venue = binance_proxy
venue_proxy_used = true
```

只有在本地暂时没有 Gate 历史 15m OHLCV 时，才允许用 Binance 15m OHLCV 作为 price/volume proxy。此时 summary 和 review 必须明确写：

```text
本轮只能证明 Binance proxy 历史数据下的候选结构，不能声称 Gate ticker 派生信号已经被验证。
```

必须输出：

```json
{
  "historical_venue": "gate|binance_proxy",
  "venue_proxy_used": false,
  "venue_proxy_risk": "none|gate_live_binance_history_mismatch"
}
```

### 4.2 输出

Stage 1.3 输出不是交易信号，而是候选事件研究报告。

必须输出：

```text
candidate_event_summary.json
candidate_signal_discovery_review_CN.md
每个候选的 baseline comparison
每个候选的 failure / proceed decision
```

输出不能包含：

```text
交易订单
paper order
live order
copy trade payload
wallet payload
position sizing instruction
```

---

## 5. 配置常量要求

Stage 1.3 implementation plan 必须把所有阈值放进 `configs/base.py`，并给每个 constant 写清楚用途、安全范围和不可用于实盘调参的说明。

禁止在 `src/` 或脚本里散落 magic number。

建议配置名：

```python
EXTERNAL_SIGNAL_STAGE1_3_VOLUME_SPIKE_THRESHOLD = 3.0
EXTERNAL_SIGNAL_STAGE1_3_REL_STRENGTH_Z_THRESHOLD = 1.5
EXTERNAL_SIGNAL_STAGE1_3_ROLLING_DAYS = 7
EXTERNAL_SIGNAL_STAGE1_3_SAME_HOUR_MIN_SAMPLES = 5
EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES = 48
EXTERNAL_SIGNAL_STAGE1_3_SNAPSHOT_INTERVAL_MINUTES = 15
EXTERNAL_SIGNAL_STAGE1_3_ONE_HOUR_BAR_COUNT = 4
EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_PREFERRED = 180
EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_MIN = 90
EXTERNAL_SIGNAL_STAGE1_3_CONFIGURED_DATA_LAG_MS = 60_000
EXTERNAL_SIGNAL_STAGE1_3_ENTRY_DELAY_BARS = 1
EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_COUNT = 100
EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_DAYS = 20
EXTERNAL_SIGNAL_STAGE1_3_MIN_SYMBOLS_WITH_EVENTS = 3
EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_SYMBOL_EVENT_SHARE = 0.50
EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_DAY_EVENT_SHARE = 0.20
EXTERNAL_SIGNAL_STAGE1_3_MAX_TOP5_POSITIVE_PNL_SHARE = 0.30
EXTERNAL_SIGNAL_STAGE1_3_RANDOM_BASELINE_TRIALS = 500
EXTERNAL_SIGNAL_STAGE1_3_RANDOM_SEED = 20260613
EXTERNAL_SIGNAL_STAGE1_3_COST_SCENARIOS_ROUND_TRIP_BPS = (30.0, 50.0, 80.0)
EXTERNAL_SIGNAL_STAGE1_3_MIN_BAR_COVERAGE_RATIO = 0.98
```

这些配置是研究协议的一部分，不是后续为了让结果变好而可以随意调的参数。

---

## 6. 候选事件定义

Stage 1.3 第一版只做三个主候选、一个 baseline、一个 diagnostic。

### 6.1 主候选 A：volume_spike_1h

假设：

```text
成交额异常放大可能代表新信息进入市场，后续短周期可能有可观测结构。
```

预注册触发逻辑建议：

```text
current_1h_quote_volume / rolling_7d_same_hour_median_quote_volume >= 3.0
```

必要约束：

```text
rolling baseline 不得包含当前 1h
rolling baseline 至少有 5 个可用历史同小时样本
事件时间锚点使用当前 1h bar close 后的 available_at-like timestamp
entry_delay_bars >= 1
```

主要风险：

```text
放量可能是出货或清算尾声
放量后可能反转而不是延续
低流动性时间段的 volume spike 容易误报
```

### 6.2 主候选 B：relative_strength_vs_btc

假设：

```text
某个 alt 明显强于 BTC，可能代表资金轮动或 idiosyncratic demand。
```

预注册触发逻辑建议：

```text
alt_1h_return - BTC_1h_return >= 1.5 * rolling_7d_std(alt_1h_return - BTC_1h_return)
```

必要约束：

```text
不允许使用未来 BTC return
rolling std 不得包含当前 1h
rolling std 至少有 48 个历史 1h 样本
只对 ETH/SOL/XRP/DOGE 计算；BTC 自身不触发该候选
entry_delay_bars >= 1
```

主要风险：

```text
alt 相对强但绝对仍下跌
BTC 横盘时小幅 alt 噪音可能被放大
DOGE/XRP 事件驱动会制造不稳定样本
```

### 6.3 主候选 C：volume_confirmed_relative_strength

假设：

```text
单纯放量可能是噪音，单纯相对强势可能是追高；放量 + 相对强势同时出现时信息密度更高。
```

预注册触发逻辑建议：

```text
volume_spike_1h is true
AND
relative_strength_vs_btc is true
```

必要约束：

```text
两个子条件必须在同一个 1h observation window 内成立
不得事后调整 volume threshold 或 relative strength threshold
事件样本数不足时输出 data_insufficient，不得放宽阈值救结果
entry_delay_bars >= 1
```

主要风险：

```text
两个弱信号叠加不一定变强
样本数可能不足
可能筛出更极端的追高事件
```

### 6.4 Baseline：price_move_15m

定位：baseline only。

假设：

```text
短周期价格快速移动后可能存在延续或反转。
```

预注册触发逻辑建议：

```text
abs(symbol_15m_return) >= rolling_7d_std(symbol_15m_return) * 1.5
```

方向处理：

```text
如果 15m return > 0，signed_forward_return = future_return
如果 15m return < 0，signed_forward_return = -future_return
```

这只是观察“冲击方向是否延续”，不是生成 long/short order。

降级原因：

```text
它本质上是短周期 price-only momentum / reversal，容易重复 Factor Lab price momentum 的失败路径。
```

用途：

```text
如果 volume_spike_1h 或 volume_confirmed_relative_strength 没有明显优于 price_move_15m，则说明成交量确认没有提供额外信息。
```

禁止：

```text
禁止把 price_move_15m 作为主候选晋级。
禁止用它单独进入 live smoke。
```

### 6.5 Diagnostic：cross_symbol_rotation

定位：diagnostic only。

假设：

```text
BTC/ETH/SOL/XRP/DOGE 之间可能存在短期资金轮动。
```

降级原因：

```text
当前 universe 只有 5 个币，横截面统计力不足。
```

用途：

```text
当主候选触发时，检查是否存在轮动确认；不单独决定候选晋级。
```

---

## 7. Historical Snapshot Replay 设计

Stage 1.3 使用 Historical Snapshot Replay，而不是先等 7d/30d live collection。

核心思想：

```text
用历史 OHLCV 模拟 Stage 1.2 的 snapshot 序列，生成候选事件，再用 Stage 0 replay 评估事件后续分布。
```

建议 replay 粒度：

```text
snapshot_interval = 15m
candidate_evaluation_window = 1h aggregation where needed
symbols = BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT
history_days >= 180 preferred
minimum_history_days >= 90
```

15m 到 1h 的聚合必须写死：

```text
1h window = 当前完整 4 根 15m bar
current_1h_quote_volume = sum(last 4 completed 15m quote_volume)
current_1h_return = close[t] / close[t-4] - 1
BTC_1h_return 使用同一个 close timestamp
candidate timestamp = 第 4 根 15m bar close + configured_data_lag_ms
entry_bar = 下一根完整 15m bar open，且满足 entry_delay_bars >= 1
```

禁止：

```text
使用未完成 15m bar
混用不同 timestamp 的 alt return 和 BTC return
用当前 1h window 参与 rolling baseline
```

时间锚点：

```text
historical_available_at_ms = bar_close_time_ms + configured_data_lag_ms
```

建议第一版：

```text
configured_data_lag_ms = 60_000
```

这不是证明真实 API 延迟，而是防止历史 replay 使用 bar 内未来信息。

真实 API 延迟、429、字段变化、维护窗口等问题，放到后续 24h live smoke 验证。Stage 1.3 先判断信号本身有没有结构。

---

## 8. Entry / Exit / Evaluation 口径

Stage 1.3 不设计真实交易策略，但必须用保守可复现的评估口径。

入场锚点：

```text
candidate_event_time = historical_available_at_ms
entry_bar = first complete bar after candidate_event_time
entry_delay_bars >= 1
entry_price = entry_bar.open
```

禁止：

```text
使用触发 bar close 作为成交价
使用触发 bar high/low 判断止盈止损
使用事件发生前已知不了的信息
```

评估窗口：

```text
forward_return_15m
forward_return_1h
forward_return_4h
MFE over 4h
MAE over 4h
terminal_return_4h
```

主评价指标必须固定，不能事后挑 horizon：

```text
primary_metric = terminal_return_4h_net_bps_after_50bps_median
primary_baseline = symbol_and_time_of_day_matched_random_baseline
baseline_excess_net_bps = candidate.primary_metric - baseline.primary_metric_median
```

`forward_return_15m`、`forward_return_1h`、MFE、MAE 只作为诊断指标，不作为主晋级指标。

成本场景：

```text
base_cost_round_trip_bps = 30
stress_cost_round_trip_bps = 50
crash_cost_round_trip_bps = 80
```

额外压力报告：

```text
gap_slippage_stress_bps = report only
```

注意：gap/slippage stress 只能报告，不能用于事后调参。

---

## 9. Baseline 与随机对照

每个候选必须和 baseline 比较。

必需 baseline：

```text
random_event_baseline
symbol_matched_random_baseline
time_of_day_matched_random_baseline
price_move_15m_baseline
BTC buy-and-hold over same evaluation windows
universe equal-weight over same evaluation windows
```

随机 baseline 要求：

```text
random_baseline_trials >= 500
每个 trial 的 event_count 必须等于 candidate event_count
symbol distribution 必须完全匹配
hour-of-day distribution 尽量精确匹配；无法精确时允许 ±1h bucket
random event time 必须来自可交易历史窗口
random event 不得落在 candidate event 同一 timestamp
random event 必须满足完整 forward window
fixed random_seed 必须写入 summary
不得跨未来采样
```

通过逻辑不能只看绝对收益。

必须同时检查：

```text
相对 random baseline 是否改善
相对 symbol/time matched baseline 是否改善
相对 BTC / universe baseline 是否改善
左尾是否恶化
结果是否集中在少数事件
```

---

## 10. Summary Schema 要求

Stage 1.3 summary 至少包含：

```json
{
  "decision": "stage1_3_candidate_signal_discovery_completed",
  "primary_blocker": null,
  "alpha_interpretation_allowed": false,
  "collector_expansion_allowed": false,
  "live_shadow_required_now": false,
  "historical_replay_first": true,
  "historical_venue": "gate|binance_proxy",
  "venue_proxy_used": false,
  "venue_proxy_risk": "none|gate_live_binance_history_mismatch",
  "bar_coverage_ratio_by_symbol": {},
  "excluded_event_reason_counts": {},
  "rolling_baseline_insufficient_count": 0,
  "forward_window_incomplete_count": 0,
  "candidate_results": {},
  "baseline_results": {},
  "next_action": "stop_gate_ticker_direction|proceed_to_24h_live_smoke_design|revise_candidate_definitions_once"
}
```

每个 candidate result 至少包含：

```json
{
  "candidate_name": "volume_spike_1h",
  "candidate_role": "primary|baseline|diagnostic",
  "event_count": 0,
  "symbols_with_events": 0,
  "event_days": 0,
  "max_single_symbol_event_share": 0.0,
  "max_single_day_event_share": 0.0,
  "top_5_positive_events_gross_profit_share": 0.0,
  "top_5_events_abs_pnl_share": 0.0,
  "forward_return_15m_net_bps_median": 0.0,
  "forward_return_1h_net_bps_median": 0.0,
  "forward_return_4h_net_bps_median": 0.0,
  "mfe_4h_bps_median": 0.0,
  "mae_4h_bps_median": 0.0,
  "left_tail_p05_net_bps": 0.0,
  "hit_rate_vs_random_baseline": 0.0,
  "primary_metric": "terminal_return_4h_net_bps_after_50bps_median",
  "primary_baseline": "symbol_and_time_of_day_matched_random_baseline",
  "baseline_excess_net_bps": 0.0,
  "cost_scenarios_round_trip_bps": [30, 50, 80],
  "candidate_decision": "candidate_failed|candidate_data_insufficient|candidate_diagnostic_promising|candidate_promising_for_live_smoke"
}
```

---

## 11. 通过、失败、停止规则

### 11.1 Data Sufficiency Gate

候选必须满足：

```text
event_count >= 100
symbols_with_events >= 3
event_days >= 20
max_single_symbol_event_share <= 0.50
max_single_day_event_share <= 0.20
```

不满足则：

```text
candidate_decision = candidate_data_insufficient
```

不得因为样本不足而放宽阈值。

### 11.2 Structure Gate

候选必须满足：

```text
random_baseline_trials >= 500
baseline_excess_net_bps > 0 after 50 bps stress
median_net_return_after_50bps > 0 或 left_tail 明显优于 baseline
left_tail_p05_after_50bps 不显著劣于 baseline
top_5_positive_events_gross_profit_share <= 0.30
```

这里的 `median_net_return_after_50bps > 0` 不是唯一通过条件。若中位数接近 0，但 left tail 明显改善且 random baseline 明显更差，可以标记为 candidate_diagnostic_promising。

`candidate_diagnostic_promising` 不允许进入 Stage 1.4 live smoke，只允许进入一次性候选定义修订或停止。

### 11.3 Stop Gate

出现以下任一情况，应停止 Gate ticker snapshot 派生方向：

```text
三个主候选全部失败
候选仅靠单日或少数事件贡献
候选不优于 price_move_15m baseline
候选不优于 random baseline
候选在 50 bps 后结构消失
候选需要 sub-minute latency 才成立
候选需要 orderbook / liquidation / funding 才能解释，但当前数据源无法支持
```

停止后允许写新的“高信息密度 source feasibility design”，但不能继续救 Gate ticker snapshot。

---

### 11.4 Data Availability Gate

历史 replay 必须先通过 bar 覆盖率检查。

最低门槛：

```text
min_bar_coverage_ratio >= 0.98
BTC baseline bars coverage >= 0.98
每个候选事件必须有完整 forward window
rolling baseline 不足时不生成事件，计入 rolling_baseline_insufficient_count
forward window 不完整时排除事件，计入 forward_window_incomplete_count
```

summary 必须输出：

```json
{
  "bar_coverage_ratio_by_symbol": {},
  "excluded_event_reason_counts": {},
  "rolling_baseline_insufficient_count": 0,
  "forward_window_incomplete_count": 0
}
```

---

## 12. 个人投资者可执行边界

Stage 1.3 必须显式排除个人投资者不可执行方向。

直接排除：

```text
MEV / DEX 抢跑
meme 新币首分钟狙击
链上 gas war
需要私钥签名的 wallet skill
copy trade
自动 swap payload
毫秒级 orderbook 做市
跨所搬砖依赖快速充提
新闻/KOL 秒级抢跑
```

可研究但必须降速：

```text
orderbook depth / imbalance
liquidation aggregate
funding / OI crowding
cross-exchange divergence
```

这些若后续进入研究，时间尺度应优先放在：

```text
15m / 1h / 4h
```

不做秒级策略。

---

## 13. 错误处理与偏差控制

Stage 1.3 必须控制以下偏差：

### 13.1 Look-ahead Bias

防线：

```text
使用 historical_available_at_ms
entry_delay_bars >= 1
不使用触发 bar 的 high/low/close 作为可成交证据
```

### 13.2 Parameter Search Bias

防线：

```text
候选阈值预注册
第一版不做网格搜索
失败后不得增加参数组救结果
```

### 13.3 Event Density Bias

防线：

```text
snapshot 频率不是市场信号频率
只有派生候选事件才进入统计
cex_market_snapshot 本身仍然 observation-only
```

### 13.4 Survivorship / Symbol Bias

防线：

```text
明确当前只研究 5 个 CEX majors
不把结果外推到所有 alt 或 meme
报告 symbol concentration
```

### 13.5 Tail Risk Bias

防线：

```text
报告 MAE / left_tail_p05
报告 top_5_positive_events_gross_profit_share / top_5_events_abs_pnl_share
报告 max_single_day_contribution
```

---

## 14. 测试要求

Stage 1.3 implementation plan 必须采用 TDD。

最低测试覆盖：

```text
test_historical_available_at_uses_bar_close_plus_lag
test_entry_uses_first_complete_bar_after_event_with_delay
test_volume_spike_excludes_current_bar_from_baseline
test_relative_strength_uses_btc_same_window_without_future_data
test_volume_confirmed_requires_both_conditions_same_window
test_price_move_15m_is_baseline_only
test_cross_symbol_rotation_is_diagnostic_only
test_price_move_15m_uses_signed_forward_return_not_order
test_random_baseline_trials_minimum_500
test_random_baseline_matches_event_count_symbol_and_hour_distribution
test_candidate_fails_when_event_count_below_100
test_candidate_fails_when_top_5_positive_events_concentration_too_high
test_bar_coverage_gate_requires_min_coverage_ratio
test_incomplete_forward_window_excludes_event
test_candidate_c_data_insufficient_does_not_relax_thresholds
test_stage1_3_summary_keeps_alpha_interpretation_false
test_stage1_3_does_not_require_live_shadow
test_stage1_3_does_not_expand_collector
```

---

## 15. 不在 Stage 1.3 范围内的事项

Stage 1.3 明确不做：

```text
新的 Gate collector
Binance / OKX collector
网页爬虫
on-chain connector
funding / OI / liquidation connector
orderbook replay
paper trading
live trading
strategy sizing
portfolio construction
LightGBM / ML fusion
大规模参数搜索
```

Candidate C 如果样本不足，必须输出 `candidate_data_insufficient`。禁止：

```text
降低 volume threshold
降低 relative strength z threshold
扩大 universe
把 AND 改成 OR
```

如果 Stage 1.3 成功，也只是允许进入：

```text
Stage 1.4 Short Live Smoke Design
```

不是进入策略实现，也不是进入 paper/live。

---

## 16. 预期结果解释

### 16.1 如果候选成功

成功只表示：

```text
在历史 replay 中，某个预注册候选事件相对随机 baseline 有可复现结构。
```

不能表示：

```text
未来一定有效
可以实盘
可以 paper trading
可以扩仓
可以复制到其他币种
```

下一步只能是：

```text
写 Stage 1.4 Short Live Smoke Design
验证真实 API 延迟、字段稳定、429、维护窗口、available_at_ms 真实可得性
```

### 16.2 如果候选失败

失败表示：

```text
Gate ticker snapshot 低维数据不足以派生出当前定义下的可研究结构。
```

下一步是：

```text
停止 Gate ticker snapshot 派生方向
```

而不是：

```text
继续调阈值
增加币种
提高采样频率
扩展 collector
```

### 16.3 如果结果不确定

不确定包括：

```text
样本数不足
symbol 过度集中
单日贡献过大
baseline 差异很小
left tail 恶化
```

下一步只能是一次性修订候选定义或停止。不得无限循环。

---

## 17. 最终建议

Stage 1.3 值得做，但必须“小而硬”。

最终建议：

```text
proceed_to_stage1_3_implementation_plan_after_design_review
```

前置条件：

```text
外部 reviewer 确认候选定义不属于过度调参
确认 baseline 和 stop gate 足够严格
确认不需要先做实时 7d / 30d shadow
确认不扩 collector
```

一句话：

```text
Stage 1.3 是 External Signal Shadow Lab 的第一次真正生死测试；它测试的是“能否从低维外部市场快照派生出候选结构”，而不是测试 collector 是否还能继续扩展。
```
