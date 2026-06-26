
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

因为没有 schema 和 filter 之前，收集 events 会带来四类污染：

```text
1. event_type 语义污染：listing / delisting / unlock / futures launch 被混成一个 signal。
2. available_at_ms 污染：历史发布时间被误当成真实可得时间。
3. hindsight bias：今天看到的过去 event calendar 未必是当时市场知道的信息。
4. filter 误用：已经失败的 OI/price proxy 被偷偷塞回硬过滤器。
```

因此必须先写 Stage 1.5 filter matrix design，再做 source audit。

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
available_at_veto
first_hour_no_trade_veto
asset_quality_veto
liquidity_depth_veto
hindsight_risk_veto
```

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

---

## 10. 当前进展与后续路线

本节用于同步 Stage 1.5 分支的最新状态。后续 agent / 人工 reviewer 只看本 brief 时，应优先读取本节，再打开对应 review 文档核对证据。

### 10.1 Stage 1.5A：Historical Event Source Audit（已完成）

目标：

```text
审计 external catalyst source 是否有足够历史、字段、时间戳和 source integrity。
```

已完成事项：

```text
1. 完成 fixture source audit，用于验证 forbidden payload、source integrity、timestamp quality、per-source / per-event-type decision 等框架能力。
2. 完成 Binance API candidate events smoke，证明可以从 Binance official announcements 半自动采集候选事件。
3. 完成人工复核与 high-confidence source audit，产出 Binance reviewed high-confidence event source。
```

关键结论：

```text
Binance official announcements 可以作为 Stage 1.5B 的第一批高可信事件源。
Fixture review 中出现 source_audit_failed 是安全测试预期，不代表真实 Binance source 失败。
Unknown / unsupported event type 必须 quarantine 或 observation-only，replay_allowed = false。
```

主要证据：

```text
docs/reviews/2026-06-22-external-signal-shadow-lab-stage1-5a-historical-event-source-audit-fixture-review_CN.md
docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-api-candidate-events-smoke-review_CN.md
docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-candidate-events-manual-review_CN.md
docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-reviewed-high-confidence-source-audit-review_CN.md
```

### 10.2 Stage 1.5B：Minimal Historical Event Table（已完成）

目标：

```text
把 Stage 1.5A 通过审计的 Binance high-confidence events 转换成最小历史事件表。
```

已完成事项：

```text
构建 article-level 与 symbol-level event table。
保留 source_url、source_published_at_ms、available_at_ms、raw_payload_hash、event_payload_hash。
保留 stage1_5a provenance，便于回溯 review / summary。
明确 symbol = BASEUSDT 只是 research normalization，不代表 market pair 已验证。
明确 directional_hypothesis = undefined，1.5B 不给 long / short 方向。
```

关键结论：

```text
Stage 1.5B 只是“事件表制造机”，不是 replay 或 signal generator。
stage1_5c_review_pending = true 只表示可以交给 1.5C 审核，不代表已经允许 replay。
price_join_allowed = false
forward_return_allowed = false
context_label_join_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

主要证据：

```text
docs/plans/2026-06-23-external-signal-shadow-lab-stage1-5b-minimal-historical-event-table-implementation-plan_CN.md
docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5b-minimal-historical-event-table-review_CN.md
```

### 10.3 Stage 1.5C：External Catalyst Historical Replay（已完成）

目标：

```text
按照 filter matrix 固定分组，评估 external catalyst event 后的 1h / 4h / 12h forward return。
```

已完成事项：

```text
实现 event_type + signed_mode + entry_delay + filter_group 的 cell-level replay。
禁止混合 futures_contract_launch 与 exchange_delisting_notice 形成 top-level pass claim。
使用 30 / 50 / 80 bps cost、500 trials random baseline、price baseline、集中度与左尾风险检查。
close-price replay only，不证明执行可行性。
```

关键结论：

```text
top_level_decision = stage1_5c_replay_completed
research_result_valid = true
promising_cells:
  futures_contract_launch | futures_launch_long_attention_diagnostic | 12h | G1_source_event_after_first_hour_delay
  futures_contract_launch | futures_launch_long_attention_diagnostic | 12h | G2_price_coverage_only
```

解释：

```text
Binance futures_contract_launch 事件，在 12h long_attention diagnostic close-price replay 上出现 promising cell。
1h / 4h long 方向失败，可能反映刚上线后价格仍处于剧烈重定价、插针、做市商调盘口阶段。
short_access diagnostic 方向不允许解释成可执行做空策略。
```

安全边界：

```text
Stage 1.5C promising 不允许 paper/live。
Stage 1.5C promising 不证明 alpha。
Stage 1.5C promising 不证明 execution feasibility。
Promising cell 只允许进入 live event-source smoke collector design，以及并行编写 execution feasibility data audit plan。
```

主要证据：

```text
docs/plans/2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-implementation-plan_CN.md
docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-review_CN.md
```

### 10.4 Stage 1.5C.1：Price Coverage Expansion（已完成）

目标：

```text
解决 Stage 1.5C 初始运行中的 no_price_history_coverage / futures price coverage 问题。
```

已完成事项：

```text
为 Stage 1.5B 的 Binance symbol events 扩展 futures kline coverage。
区分 current exchangeInfo 与 historical existence。
输出 futures coverage pass event table，供 Stage 1.5C clean rerun 使用。
明确 spot proxy report-only，不能影响 ready decision。
```

关键结论：

```text
decision = stage1_5c1_price_coverage_ready_for_1_5c_rerun
Stage 1.5B input events = 194
Futures coverage pass events = 63
Calendar days = 46
Symbols = 61
Not matured events = 1
```

解释：

```text
1.5C.1 修复的是数据覆盖问题，不是策略问题。
futures_contract_launch 可以用 post-launch futures coverage。
exchange_delisting_notice 仍需要 market_scope / historical futures existence / effective-time 进一步拆解。
```

主要证据：

```text
docs/plans/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-implementation-plan_CN.md
docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-review_CN.md
```

### 10.5 Stage 1.5D：Live Event-Source Smoke Collector（已实现，正式 24h 运行中）

目标：

```text
验证真实 Binance announcement source 的 latency、字段稳定性、schema drift、request health、heartbeat、first futures bar observation。
```

已完成事项：

```text
实现 public-readonly live source collector。
实现 upstream evidence gate。
实现 domain allowlist、redirect final host 校验、dedupe / watermark、request manifest、heartbeat、daily rotated storage。
实现 first futures bar observer，且不阻塞 announcement poll loop。
实现 fixture smoke 与 short live smoke。
完成服务器部署流程文档。
```

当前状态：

```text
short live smoke decision = stage1_5d_smoke_observation_in_progress
research_result_valid = false
event_detection_validated = false
poll_count = 3
deduped_new_event_count = 28
```

解释：

```text
短 smoke 只证明本地路径闭环，不是正式 24h operational pass。
正式 24h source smoke 必须是同一个 output-root 下连续运行 >= 24h。
多段中断运行不能拼接成正式 24h。
服务器已部署，当前应等待正式 24h 运行结束后取回 summary / JSONL / review。
```

正式 24h 后可能出现两种合格结果：

```text
stage1_5d_operational_pass_event_detection_unvalidated:
  24h 内 collector 稳定，但没有新 futures launch event。

stage1_5d_event_detection_passed:
  24h 内捕捉到新 futures launch event，并完成 first futures bar observation。
```

主要证据：

```text
docs/designs/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-design_CN.md
docs/plans/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-implementation-plan_CN.md
docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md
```

### 10.6 Stage 1.5E：Execution Feasibility Data Audit（下一步，建议并行编写）

目标：

```text
验证 Stage 1.5C 的 promising cell 是否具备执行意义。
```

它不是 replay，不是 trading，不是 signal generator。

需要审计的内容：

```text
futures launch 后 1h / 4h / 12h 的 spread_bps
top_0_5pct_depth_usdt
top_1pct_depth_usdt
slippage_estimate_bps_for_500usdt
mark / index divergence
24h quote volume
first 1h liquidity stabilization
orderbook snapshot availability
```

为什么必须做：

```text
Stage 1.5C 只使用 close price replay。
close price replay 无法证明真实盘口可以成交。
futures launch 初期常见薄盘口、宽点差、插针、做市商重新定价、深度塌陷。
如果执行可行性失败，Stage 1.5C promising 只能保留为研究现象，不能进入 shadow execution。
```

建议下一步文档：

```text
docs/plans/2026-06-25-external-signal-shadow-lab-stage1-5e-execution-feasibility-data-audit-implementation-plan_CN.md
```

安全边界：

```text
execution_engine_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
trade_signal_allowed = false
```

---

## 11. 成功与失败标准

### 11.1 Source audit 成功

```text
historical_events_found >= 30
source_integrity_pass_rate >= 95%
symbol_mapping_pass_rate >= 95%
available_at_policy_defined = true
forbidden_payload_count = 0
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
事件数不足且不可扩展
表现不优于 random baseline
成本后中位收益为负
收益由单日 / 单币 / Top 5 极端事件贡献
filter matrix 没有增量价值
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
decision = continue_stage1_5d_24h_live_source_smoke_and_write_stage1_5e_execution_feasibility_audit_plan
stage1_5a_source_audit_status = completed
stage1_5b_minimal_event_table_status = completed
stage1_5c_historical_replay_status = completed_with_promising_cells
stage1_5c1_price_coverage_status = completed_ready_for_1_5c_rerun
stage1_5d_live_source_smoke_status = implemented_and_formal_24h_run_pending_or_running
stage1_5e_execution_feasibility_audit_status = next_plan_to_write
primary_event_type_under_research = futures_contract_launch
primary_promising_cell = futures_contract_launch_long_attention_diagnostic_12h_close_price_replay_only
exchange_delisting_notice_status = insufficient_futures_replay_sample_pending_market_scope_and_effective_time_work
external_catalyst_events_collection_allowed = true
historical_replay_completed = true
live_event_source_smoke_allowed = true
execution_feasibility_audit_allowed = true
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

一句话：

```text
External Catalyst Events + Filter 已经从 source audit 推进到 historical replay 与 live source smoke；
当前唯一有希望的研究现象是 Binance futures_contract_launch 在 12h long_attention diagnostic close-price replay 上的 promising cell；
但它仍然不能解释成 alpha 或交易信号。
下一步必须同时完成 24h live event-source smoke 和 execution feasibility data audit，
确认 source 能稳定捕捉事件、盘口执行条件没有把 close-price replay 的收益吃掉。
```
