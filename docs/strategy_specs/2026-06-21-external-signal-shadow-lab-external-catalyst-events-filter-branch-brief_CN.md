# External Signal Shadow Lab 分支说明：External Catalyst Events + Filter

日期：2026-06-21

## 1. 一句话结论

`External Catalyst Events + Filter` 是 External Signal Shadow Lab 在 Stage 1.4 之后的新分支。

它不是一个交易策略，也不是公告追涨系统。

它的目标是：

```text
把外部催化事件转换成可审计、可回放、可证伪的研究事件，
再用分层 filter matrix 判断哪些事件类型、哪些状态上下文可能具备进一步研究价值。
```

最终目标仍然是发现 alpha 候选，但本分支当前阶段不允许输出 alpha pass，也不允许 paper/live。

---

## 2. 为什么需要这个分支

前置研究已经连续证伪了多条低维或内生状态变量方向：

```text
Gate ticker / Binance proxy OHLCV 派生方向：失败。
Funding / OI / price crowding-only：失败。
OI drop + price flush deleveraging proxy：失败。
Local forceOrder snapshot：值得继续积累，但不是完整 liquidation tape，不能支持 full composite / alpha 结论。
```

这些结果共同说明：

```text
继续只在 CEX 内生状态变量中调阈值，边际价值下降。
```

因此下一步必须从：

```text
market state predicts market state
```

转向：

```text
external catalyst triggers market state transition
```

也就是：

```text
外生事件 -> 标准化 -> 安全审计 -> filter matrix -> 历史 replay -> review -> 决定继续或停止
```

这里的“转向”不是放弃本地 liquidation 数据资产，而是把当前主动研究重心从继续调 CEX 内生变量，转移到 external catalyst。

正式路线应写成双轨：

```text
active_research_track = external_catalyst_events_filter_matrix
long_term_data_asset_track = continue_local_forceorder_liquidation_collection
full_composite_track = deferred_until_liquidation_history_or_vendor_quality_improves
```

也就是说：

```text
Stage 1.5 负责寻找新的高信息密度外生 source；
local forceOrder collector 继续作为长期 liquidation 数据资产积累；
二者不是互相替代关系。
```

---

## 3. external catalyst events 是什么

External catalyst events 指来自市场价格以外的外部事件。

第一版关注：

```text
交易所公告
合约 / 杠杆功能开通
交易对增加或移除
下线公告
重大解锁或释放计划
交易所状态变化
```

它们与前面 `cex_market_snapshot`、funding、OI、price、liquidation snapshot 的区别是：

```text
前者是外生催化事件；
后者是市场内部状态变量。
```

前面的 CEX 内生变量回答：

```text
市场已经发生了什么？
```

External catalyst events 要回答：

```text
是否有一个外部事件可能引发未来的仓位重估、流动性迁移或强制出清？
```

---

## 4. 它和 External Signal Shadow Lab 的关系

这是同一个 Lab 的新数据源分支，不是新项目。

External Signal Shadow Lab 的核心方法不变：

```text
raw payload
-> connector normalize
-> forbidden payload check
-> available_at_ms
-> risk / safety guard
-> replay
-> review
-> continue / stop
```

区别只在于输入源升级：

```text
Stage 1.2 输入：Gate public ticker snapshot
Stage 1.3 输入：OHLCV / ticker 派生事件
Stage 1.4 输入：funding / OI / price / forceOrder snapshot
Stage 1.5 输入：external catalyst events
```

---

## 5. 这个分支不是什么

它不是：

```text
公告追涨系统
新币 listing 抢跑系统
whale deposit 开空系统
链上 smart money 自动跟单系统
KOL/news 秒级抢跑系统
liquidation 接飞刀实盘系统
```

它也不允许：

```text
api_key
secret
private_key
wallet_seed
mnemonic
authorization
bearer
access_token
refresh_token
cookie
session
csrf
password
passphrase
signed_tx
raw_tx
order_request
swap_request
transfer_request
wallet_private_key
tx_payload
```

任何外部 payload 出现上述字段，必须 reject。

---

## 6. 核心研究假设

本分支的核心假设不是：

```text
外部公告一出就上涨或下跌。
```

而是：

```text
某些外部事件会改变市场参与者的预期、杠杆可得性、供给压力或流动性结构；
这些变化可能在事件后 1h / 4h / 12h / 24h 内形成可观测的状态切换；
合适的 filter matrix 可能帮助区分噪音事件和高信息密度事件。
```

简化为：

```text
external catalyst = 压力源
filter matrix = 风险与状态识别器
replay = 证伪器
```

---

## 7. 为什么不能直接收集所有 events

因为没有 schema 和 filter 之前，收集 events 会带来五类污染：

```text
1. event_type 语义污染：listing / delisting / unlock / futures launch 被混成一个 signal。
2. available_at_ms 污染：历史发布时间被误当成真实可得时间。
3. hindsight bias：今天看到的过去 event calendar 未必是当时市场知道的信息。
4. filter 误用：已经失败的 OI/price proxy 被偷偷塞回硬过滤器。
5. connector / payload 污染：外部源格式变化、超大 payload、深层嵌套或错误 symbol mapping 污染研究表。
```

因此必须先写 Stage 1.5 filter matrix design，再做 source audit。

Stage 1.5A 之前不允许写“全量采集器”。第一版只允许做 bounded source audit：

```text
source_domain_allowlist_required = true
max_payload_bytes_required = true
max_json_depth_required = true
request_timeout_required = true
retry_with_backoff_required = true
schema_quarantine_required = true
raw_payload_hash_required = true
collector_circuit_breaker_required = true
```

这些规则的目的不是防资金被盗，因为本分支不接 API key / 钱包 / execution layer；它们的目的是防止脏数据、格式炸弹、重试风暴或 source drift 污染研究结论。

---

## 8. 推荐事件源

### 8.1 第一优先：官方交易所公告

适合研究：

```text
delisting_notice
futures_contract_launch
margin_enablement
trading_pair_addition
trading_pair_removal
exchange_status_event
```

优势：

```text
source 可信
事件语义较硬
适合 historical replay
```

风险：

```text
结构化差
分页 / 反爬 / 多语言页面可能造成字段不稳定
available_at_ms 需要保守估计
```

第一版需要进一步拆分 listing 语义，避免滑回“新币追涨”：

```text
new_coin_spot_listing = forbidden_or_observation_only
new_perp_for_existing_spot_asset = allowed_if_pre_event_liquidity_pass
new_pair_for_existing_liquid_asset = allowed
```

其中 `existing_liquid_asset` 必须在事件前已经有足够价格历史、成交量和可映射 symbol；不能用事件后流动性反推事件前资格。

### 8.2 第二优先：Token unlock calendars

适合研究：

```text
major_unlock_event
large_scheduled_token_emission
```

优势：

```text
事件强度字段较清晰
可计算 unlock amount / float percentage / volume ratio
```

风险：

```text
历史 schedule 存在 hindsight risk
很多 token 不符合资产质量门槛
不适合第一版直接 directional replay
```

### 8.3 第三优先：Crypto event calendars

适合：

```text
source discovery
observation-only
辅助补充
```

不适合第一版主线，因为噪音高、事件类型泛化、历史数据可能受限。

---

## 9. Filter 的角色

Filter 不是一个神奇入场条件。

Filter 分为四类：

```text
Hard Veto Filter：不满足就拒绝。
Eligibility Filter：判断能不能进入 replay。
Context Label Filter：只打标签，不直接决定入场。
Experimental Replay Group：用于固定分组对比。
```

### 9.1 Hard Veto Filter

包括：

```text
source_integrity_veto
forbidden_payload_veto
source_resource_safety_veto
available_at_veto
first_hour_entry_delay_policy
asset_quality_veto
liquidity_depth_veto
hindsight_risk_veto
```

注意：

```text
first_hour_entry_delay_policy 不删除事件，只禁止 available_at 后首小时入场，避免公告瞬时追涨/追空。
```

`source_resource_safety_veto` 必须在 connector normalize 前生效。至少覆盖：

```text
domain_allowlist_violation
payload_too_large
json_depth_exceeded
request_timeout
retry_budget_exhausted
schema_parse_error
symbol_mapping_ambiguous
source_format_drift
```

触发后不得 silent fallback，不得自动猜 symbol，不得进入 replay；只能进入 quarantine / observation-only 统计。

### 9.2 Context Label Filter

包括：

```text
local_liquidation_context
funding_crowding_context
oi_crowding_context
price_reaction_context
orderbook_execution_context
btc_regime_context
deleveraging_proxy_context
```

注意：

```text
deleveraging_proxy_context 在 Stage 1.4E 失败后只能 diagnostic-only，不能作为 hard filter。
```

其他 CEX 内生变量也只能作为 context label，不允许重新变成 primary alpha source：

```text
funding_crowding_context != entry rule
oi_crowding_context != entry rule
price_reaction_context != entry rule
local_liquidation_context != complete tape truth
```

---

## 10. 后续步骤

### Stage 1.5A：Historical Event Source Audit

目标：

```text
审计 external catalyst source 是否有足够历史、字段、时间戳和 source integrity。
```

推荐审计对象：

```text
Binance official announcements
OKX official announcements
DefiLlama unlocks
Tokenomist unlocks
CoinMarketCal / CoinMarketCap events calendar
```

输出：

```text
source_audit_summary.json
source_audit_review_CN.md
```

Source audit summary 必须包含 connector 安全与 source drift 字段：

```text
source_domain_allowlist_pass_rate
payload_too_large_count
json_depth_exceeded_count
request_timeout_count
retry_budget_exhausted_count
schema_parse_error_count
schema_quarantine_count
symbol_mapping_ambiguous_count
source_format_drift_count
raw_payload_hash_missing_count
```

如果官方公告页面存在 CDN / 多语言 / HTML 更新时间不一致，必须在 review 中单独输出：

```text
timestamp_source_disagreement_count
timestamp_quality_distribution
available_at_delay_sensitivity_required = true
```

### Stage 1.5B：Minimal Historical Event Table

目标：

```text
收集 30-100 条高可信 external catalyst events。
```

要求：

```text
source_url
source_published_at_ms
available_at_ms policy
raw_payload_hash
symbol mapping
event_type
event magnitude
hindsight_risk flag
timestamp_quality
event_type_replay_group
```

### Stage 1.5C：External Catalyst Historical Replay

目标：

```text
按照 filter matrix 固定分组，评估事件后 1h / 4h / 12h / 24h forward return。
```

必须包含：

```text
30 / 50 / 80 bps cost
symbol-hour matched random baseline
price baseline
event-type baseline
BTC regime baseline
concentration checks
```

Replay 不允许混合 event type 后直接宣称通过。必须按 event type 输出独立结果：

```text
event_type_mixing_allowed_for_source_audit = true
event_type_mixing_allowed_for_replay_pass = false
post_hoc_group_selection_allowed = false
```

### Stage 1.5D：Live Smoke Collector

只有 Stage 1.5C 有希望，才允许。

目标：

```text
验证真实 source latency、字段稳定性、429、available_at_ms 与 safe fail。
```

不允许 paper/live。

---

## 11. 成功与失败标准

### 11.1 Source audit 成功

```text
historical_events_found >= 30
source_integrity_pass_rate >= 95%
symbol_mapping_pass_rate >= 95%
available_at_policy_defined = true
forbidden_payload_count = 0
source_resource_safety_policy_defined = true
schema_quarantine_count is reported
payload_too_large_count is reported
request_timeout_count is reported
symbol_mapping_ambiguous_count = 0 for replay rows
primary_event_type_events >= 20
timestamp_quality_high_or_medium_ratio >= 95%
```

### 11.2 Replay research pass

```text
event_count >= 30
event_days >= 10
symbols_with_events >= 3
median_net_return_after_50bps > 0
baseline_excess_net_bps > 0
price_baseline_excess_net_bps > 0
left_tail_p05 不差于 random baseline
top_5_positive_events_gross_profit_share <= 0.40
max_single_day_event_share <= 0.30
max_single_symbol_event_share <= 0.60
```

### 11.3 停止条件

```text
source 无法审计
available_at_ms 无法保守构建
connector resource safety 无法定义
schema parse / symbol mapping 错误被 silent ignore
事件数不足且不可扩展
表现不优于 random baseline
成本后中位收益为负
收益由单日 / 单币 / Top 5 极端事件贡献
filter matrix 没有增量价值
任一 event type 的 replay 样本不足但被强行混合成通过
事后挑选表现最好的 group 作为主结论
```

---

## 12. 与资金安全规则的关系

本分支不触碰 execution layer，不生成 TradeIntent，不连接交易所账户，不使用 API key，不使用钱包。

即使历史 replay 通过，也只允许进入：

```text
24h live smoke collector
7d shadow observation
30d shadow observation
```

不允许直接进入：

```text
paper trading
live trading
maker-first execution
position sizing
```

任何策略设计必须另起 Stage 2 / Stage 3，并满足项目 pre-live checklist。

---

## 13. 当前正式建议

```text
decision = proceed_to_stage1_5a_historical_event_source_audit
primary_source_priority = official_exchange_announcements
secondary_source_priority = unlock_calendars_source_audit_only
active_research_track = external_catalyst_events_filter_matrix
liquidation_collection_continues_as_data_asset = true
full_composite_track_deferred = true
external_catalyst_events_collection_allowed_after_filter_matrix_design = true
historical_replay_allowed_after_minimal_event_table = true
live_smoke_allowed_only_after_historical_replay_promising = true
paper_trading_allowed = false
live_trading_allowed = false
short_execution_intent_allowed = false
post_hoc_group_selection_allowed = false
```

一句话：

```text
External Catalyst Events + Filter 是 External Signal Shadow Lab 的下一条高信息密度 source 分支；
它的价值在于用外部事件替代低维内生状态变量作为研究起点，
但所有事件都必须经过 schema、available_at_ms、hard veto、context label、baseline replay 和 review，
不能被直接解释成交易信号。
```
