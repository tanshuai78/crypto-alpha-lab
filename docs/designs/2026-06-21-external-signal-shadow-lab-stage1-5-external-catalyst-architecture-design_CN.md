# External Signal Shadow Lab Stage 1.5 External Catalyst Architecture Design

日期：2026-06-21

## 0. 一句话结论

Stage 1.5 的目标不是把外部公告、解锁、上线、下线、合约开通等事件直接变成交易信号。

Stage 1.5 的目标是建立一套 **External Catalyst Architecture（外生催化事件研究架构）**，用来回答：

```text
外部事件本身是否含有可研究的信息量？
不同硬过滤器与上下文标签是否能提高事件后的 forward return 结构？
哪些 event type 值得进入历史 replay / live smoke / shadow observation？
```

本阶段仍然是 **research-only / diagnostic-only**。

```json
{
  "stage": "external_signal_shadow_lab_stage1_5",
  "scope": "external_catalyst_architecture_design_only",
  "execution_engine_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "alpha_interpretation_allowed": false,
  "external_event_is_trade_signal": false,
  "filter_matrix_is_trade_rule": false,
  "active_research_track": "external_catalyst_events_filter_matrix",
  "liquidation_collection_continues_as_data_asset": true,
  "full_composite_track_deferred": true,
  "event_source_mixing_allowed_for_replay_pass": false,
  "post_hoc_group_selection_allowed": false,
  "short_execution_intent_allowed": false,
  "external_event_direct_entry_allowed": false,
  "source_resource_safety_required": true
}
```

---

## 1. 背景与收敛结论

前置阶段已经形成明确证据：

```text
Stage 1.3:
  low-dimensional ticker / OHLCV 派生方向失败。

Stage 1.4B-Lite:
  funding / OI / futures price crowding-only 分支失败。

Stage 1.4E:
  OI drop + price flush deleveraging proxy 未通过，不能作为 liquidation 的低成本替代过滤器。

Stage 1.4A-LQ30:
  local forceOrder snapshot 值得继续积累，但仍不是 complete liquidation tape，也不能支持 full composite / alpha / paper/live 结论。
```

因此当前正式判断是：

```text
CEX 内生状态变量不能继续作为 primary alpha source。
下一步应转向 external catalyst events。
但 external catalyst 也不能直接交易，必须先进入 filter matrix 和 replay。
```

这里的“转向”不是否定 Stage 1.4C 的 `continue_liquidation_primary_track`，而是重新分工：

```text
active_research_track = external_catalyst_events_filter_matrix
long_term_data_asset_track = continue_local_forceorder_liquidation_collection
full_composite_track = deferred_until_liquidation_history_or_vendor_quality_improves
```

也就是说，Stage 1.5 负责主动寻找新的外生事件 source；本地 forceOrder 继续采集，但只作为长期 liquidation 数据资产，不作为当前 Stage 1.5 的 primary trigger。

Stage 1.5 是这一范式切换的第一份设计文档。

---

## 2. Stage 1.5 要回答的问题

Stage 1.5 只回答以下问题：

### 2.1 外生事件是否可标准化

```text
能否把不同来源的 external catalyst event 转换成统一 schema？
是否能保留 source、available_at_ms、raw_payload_hash、event magnitude 等审计字段？
```

### 2.2 哪些事件类型值得第一版研究

```text
哪些事件源足够外生、低频、可审计、可回放？
哪些事件源噪音太大或延迟太不可控，应降级为 observation-only？
```

### 2.3 哪些过滤器是 hard veto，哪些只是 context label

```text
source integrity / forbidden payload / available_at / liquidity / asset quality 属于 hard veto。
first-hour 规则属于 entry delay policy，不删除事件，只禁止首小时入场。
funding / OI / liquidation / price reaction / BTC regime 属于 context label。
```

### 2.4 Filter matrix 是否提高事件后结构

```text
external catalyst only 是否有结构？
加入 hard veto 后是否改善？
加入 context labels 分组后是否出现更高质量的子集？
```

---

## 3. Stage 1.5 不回答的问题

本阶段明确不回答：

```text
是否可以实盘交易
是否可以 paper trading
某个公告是否应立即买入/卖出
某个 filter 是否已经是交易规则
某个 external catalyst 是否已经确认 alpha
```

禁止输出：

```text
strategy approved
paper/live approved
external event alpha confirmed
listing alpha confirmed
unlock short alpha confirmed
liquidation rebound alpha confirmed
```

---

## 4. 第一版允许研究的 event type

第一版不做全量事件采集，只做高可信、低频、可审计事件。

### 4.1 P1：正式允许进入 Stage 1.5A source audit 的事件

```text
exchange_delisting_notice
futures_contract_launch
margin_enablement
trading_pair_removal
trading_pair_addition_for_existing_liquid_asset
major_exchange_status_event
```

说明：

- `exchange_delisting_notice`：交易所下线公告。事件语义较硬，source 通常来自官方公告。
- `futures_contract_launch`：合约开通。可能改变杠杆可得性、做空通道与资金流结构。
- `margin_enablement`：杠杆/保证金功能开放。可能改变融资做多/做空行为。
- `trading_pair_removal`：交易对移除。可能导致流动性收缩与迁移。
- `trading_pair_addition_for_existing_liquid_asset`：仅限已有高流动性资产的新交易对，不含新币首发追涨。
- `major_exchange_status_event`：充值/提现暂停、恢复、重大维护等。

必须拆分 listing 语义：

```text
new_coin_spot_listing = forbidden_or_observation_only
new_perp_for_existing_spot_asset = allowed_if_pre_event_liquidity_pass
new_pair_for_existing_liquid_asset = allowed
```

`existing_liquid_asset` 的资格只能用事件前数据判定，不能用事件后成交量、价格历史或交易热度反推。

### 4.2 P2：只允许 observation-only source audit 的事件

```text
major_unlock_event
large_scheduled_token_emission
protocol_upgrade
scheduled_airdrop_claim
```

说明：

- 解锁和释放事件具有外生性，但历史 schedule 容易存在 hindsight risk（事后可见风险）。
- 第一版只审计 source 与字段质量，不直接进入 directional replay。

### 4.3 第一版禁止作为主研究对象

```text
new_coin_spot_listing_chase
single_whale_deposit
kol_tweet
partnership_announcement
meme_trend
rumor_based_news
unverified_social_signal
```

原因：

```text
延迟不可控
欺骗性高
source 语义不稳定
容易引发追涨/追空
无法可靠构建 available_at_ms
```

---

## 5. External catalyst event schema

### 5.1 通用字段

所有 event 必须包含：

```json
{
  "event_id": "string",
  "event_type": "string",
  "symbol": "BTCUSDT",
  "base_asset": "BTC",
  "quote_asset": "USDT",
  "venue": "binance|okx|coinbase|other",
  "source_name": "string",
  "source_domain": "string",
  "source_url": "string",
  "source_published_at_ms": 0,
  "event_time_ms": 0,
  "available_at_ms": 0,
  "collector_received_at_ms": 0,
  "raw_payload_hash": "sha256",
  "raw_payload_size_bytes": 0,
  "schema_version": "stage1_5_v1",
  "source_timestamp_quality": "official_api_published_at|html_page_time|inferred_from_url|missing",
  "historical_available_at_confidence": "high|medium|low",
  "edited_page_risk": false,
  "hindsight_risk": false,
  "metadata": {}
}
```

字段语义：

- `source_published_at_ms`：source 声称发布该事件的时间。
- `event_time_ms`：事件实际生效或发生时间。
- `available_at_ms`：本项目可以合法使用该信息的时间锚点。
- `collector_received_at_ms`：collector 实际收到 payload 的本地时间。
- `source_domain`：归一化后的 source domain，用于 allowlist 与 source drift 审计。
- `raw_payload_size_bytes`：原始 payload 大小，用于防止超大 payload 污染。
- `source_timestamp_quality`：历史发布时间的证据质量。
- `historical_available_at_confidence`：historical replay 中该事件可得时间的可信等级。
- `edited_page_risk`：公告页是否可能被编辑、覆盖或回填。
- `hindsight_risk`：该事件是否存在事后才知道的时间/内容风险。

### 5.2 delisting_notice schema

```json
{
  "event_type": "exchange_delisting_notice",
  "symbol": "XYZUSDT",
  "venue": "binance",
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "delisting_effective_time_ms": 0,
  "affected_pairs": ["XYZUSDT"],
  "notice_to_effective_hours": 0.0,
  "metadata": {
    "delisting_reason": "low_liquidity|compliance|project_issue|unknown"
  }
}
```

### 5.3 contract_launch / margin_enablement schema

```json
{
  "event_type": "futures_contract_launch",
  "symbol": "XYZUSDT",
  "venue": "binance",
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "trading_start_time_ms": 0,
  "contract_type": "usdt_perp|coin_margin|margin_pair",
  "metadata": {
    "max_leverage": null,
    "margin_mode": "cross|isolated|unknown"
  }
}
```

### 5.4 unlock event schema

```json
{
  "event_type": "major_unlock_event",
  "symbol": "XYZUSDT",
  "source_name": "defillama|tokenomist|other",
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "unlock_time_ms": 0,
  "unlock_amount_usd": 0.0,
  "unlock_pct_float": 0.0,
  "unlock_pct_30d_volume": 0.0,
  "hindsight_risk": true,
  "metadata": {
    "allocation_type": "team|investor|ecosystem|foundation|unknown"
  }
}
```

---

## 6. available_at_ms policy

### 6.1 官方交易所公告

第一版 historical replay 使用保守可得时间：

```text
available_at_ms = source_published_at_ms + conservative_delay_ms
```

建议 sensitivity：

```text
exchange_announcement_delay_scenarios = 5min / 15min / 60min
```

主报告使用：

```text
primary_delay = 15min
```

`source_published_at_ms` 必须带 timestamp quality：

```text
official_api_published_at -> high
html_page_time -> medium
inferred_from_url -> low
missing -> unavailable
```

Historical replay 只允许：

```text
historical_available_at_confidence in [high, medium]
edited_page_risk = false
```

否则：

```text
historical_available_at_confidence = low
-> observation-only
-> replay_allowed = false
```

如果没有可信 `source_published_at_ms`：

```text
source_time_missing -> hard veto 或 observation-only
```

### 6.2 unlock calendar

如果有历史 calendar snapshot：

```text
available_at_ms = calendar_snapshot_available_at_ms
```

如果只有当前看到的过去 schedule：

```text
hindsight_risk = true
replay_allowed = false in first version
observation_only = true
```

### 6.3 live smoke

live smoke 阶段才允许使用：

```text
available_at_ms = collector_received_at_ms
```

在 historical replay 阶段不得伪造实时可得时间。

---

## 7. Filter matrix 总览

Stage 1.5 filter 分为四类：

```text
A. Hard Veto Filter
B. Eligibility Filter
C. Context Label Filter
D. Experimental Replay Group
```

### 7.1 A 类：Hard Veto Filter

Hard veto 是一票否决。触发后事件不得进入 candidate replay。

| Filter | 作用 | 触发后动作 |
|---|---|---|
| `source_integrity_veto` | source / raw / timestamp 不完整 | reject |
| `forbidden_payload_veto` | 出现私钥、API key、swap、订单字段 | reject |
| `source_resource_safety_veto` | 外部源超限、格式炸弹、重试风暴、source drift | reject / quarantine |
| `available_at_veto` | 缺失或不可审计 available_at_ms | reject / observation-only |
| `first_hour_entry_delay_policy` | available_at 后 60m 内禁止 entry | 延迟 replay，不允许首小时入场 |
| `asset_quality_veto` | 资产不符合质量门槛 | reject |
| `liquidity_depth_veto` | 深度、spread、volume 不足 | reject / execution_unknown |
| `hindsight_risk_veto` | 历史事件明显事后可见 | observation-only |

### 7.2 B 类：Eligibility Filter

Eligibility filter 判断事件是否有资格进入 replay。

| Filter | 要求 |
|---|---|
| `event_type_allowed` | event_type 在 P1/P2 列表中 |
| `event_magnitude_available` | unlock amount / effective time / launch time 等关键字段存在 |
| `symbol_mapping_resolved` | 能映射到项目内 symbol |
| `price_history_available` | 事件前后价格数据完整 |
| `price_data_available` | 事件前后 futures kline 数据完整 |
| `context_missingness_report_required` | funding / OI / liquidation / orderbook 缺失必须报告，但默认不做 hard veto |

### 7.3 C 类：Context Label Filter

Context label 不做硬过滤，只做分组 replay 与风险解释。

| Label | 来源 | 用途 |
|---|---|---|
| `local_liquidation_context` | local forceOrder snapshot | 标注事件后是否有清算 cluster / imbalance |
| `deleveraging_proxy_context` | OI drop + price flush | 1.4E 失败后仅 diagnostic-only |
| `funding_crowding_context` | funding history | 标注多空资金费拥挤 |
| `oi_crowding_context` | OI history | 标注杠杆堆积或收缩 |
| `price_reaction_context` | futures kline | 标注公告后价格冲击 |
| `orderbook_execution_context` | orderbook snapshots | 标注可执行深度 / spread / slippage |
| `btc_regime_context` | BTC/ETH price/vol | 标注系统性行情背景 |

### 7.4 D 类：Experimental Replay Group

固定分组，不允许事后挑选：

```text
Group 0: external catalyst only
Group 1: event + first_hour_delay
Group 2: event + first_hour_delay + asset_quality_pass
Group 3: event + first_hour_delay + asset_quality_pass + liquidity_pass
Group 4: event + first_hour_delay + asset_quality_pass + liquidity_pass + local_liquidation_context_present
Group 5: event + first_hour_delay + asset_quality_pass + liquidity_pass + funding_oi_context_labels
```

注意：

```text
Group 4 / Group 5 是研究分组，不是交易规则。
primary_replay_group = Group 2 或 Group 3，在 implementation plan 前必须预注册。
其他 group 默认 report-only。
post_hoc_group_selection_allowed = false。
```

---

## 8. Filter 细则

### 8.1 Source Integrity Veto

必须存在：

```text
source_name
source_url or source_id
raw_payload_hash
event_type
symbol mapping
available_at_ms
schema_version
```

缺失处理：

```text
critical field missing -> reject
non-critical field missing -> observation-only
```

### 8.2 Forbidden Payload Veto

递归检查 raw payload。出现以下字段直接 reject：

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

### 8.3 Source Resource Safety Veto

`source_resource_safety_veto` 必须在 connector normalize 前生效，避免外部源投毒、格式炸弹或 source drift 污染研究表。

第一版必须定义：

```text
domain_allowlist
max_payload_bytes
max_json_depth
request_timeout_sec
retry_with_backoff
retry_budget
max_events_per_page
schema_quarantine
raw_payload_hash_required
collector_circuit_breaker
```

触发条件至少包括：

```text
domain_allowlist_violation
payload_too_large
json_depth_exceeded
request_timeout
retry_budget_exhausted
events_per_page_exceeded
schema_parse_error
symbol_mapping_ambiguous
source_format_drift
raw_payload_hash_missing
```

处理规则：

```text
触发后不得 silent fallback
不得自动猜 symbol
不得进入 replay
只能进入 quarantine / observation-only 统计
```

这些规则不代表本分支存在资金漏洞；本阶段不接 API key、钱包或 execution layer。它们只用于保护研究数据质量和 collector 稳定性。

### 8.4 First-Hour Entry Delay Policy

```text
entry_candidate_time_ms >= available_at_ms + 60min
```

第一小时只允许记录：

```text
post_event_return_15m
post_event_return_1h
spread_change
depth_change
liquidation_context
```

### 8.5 Asset Quality Veto

第一版允许：

```text
Tier 1: BTC / ETH / SOL
Tier 2: XRP / DOGE / BNB / ADA / LTC
```

临时允许条件：

```text
must_have_usdt_perp = true
min_24h_futures_quote_volume_usdt >= 50_000_000
min_price_history_days >= 90
```

禁止：

```text
low_float_high_fdv_new_listing
illiquid_meme
no_perp_market
contract_risk_asset
symbol_mapping_unresolved
```

### 8.6 Liquidity / Depth / Spread Veto

如果有 orderbook：

```text
spread_bps <= 20
slippage_estimate_bps_for_500usdt <= 30
visible_depth_1pct_usdt >= 1000
```

如果没有 orderbook：

```text
execution_feasibility_unknown = true
不能输出 execution-ready 结论
```

### 8.7 Deleveraging Proxy Context

由于 Stage 1.4E 未通过：

```text
deleveraging_proxy_15m_present = diagnostic-only
deleveraging_proxy_1h_present = diagnostic-only
```

禁止：

```text
proxy_confirmed_liquidation = true
proxy_filter_pass = true
proxy_required_for_entry = true
```

### 8.8 Local Liquidation Context

允许输出：

```text
local_forceorder_cluster_present
long_liquidation_notional
short_liquidation_notional
long_liquidation_share
short_liquidation_share
liquidation_event_count_1h
liquidation_event_count_4h
```

必须标记：

```text
local_forceorder_snapshot_not_complete_tape = true
```

### 8.9 Event Direction Semantics

Stage 1.5C implementation 前必须冻结每个 `event_type` 的 replay mode：

```text
exchange_delisting_notice = avoid_long_or_signed_short_diagnostic
futures_contract_launch = volatility_or_signed_directional_diagnostic
margin_enablement = signed_directional_diagnostic
trading_pair_removal = avoid_long_diagnostic
trading_pair_addition_for_existing_liquid_asset = long_only_or_volatility_diagnostic
major_exchange_status_event = event_type_specific_diagnostic
```

本设计阶段不直接选择最终方向，只规定：

```text
evaluation_mode_required = true
short_execution_intent_allowed = false
borrow_or_margin_feasibility_checked = false
volatility_only_events_must_not_be_reported_as_directional_alpha = true
```

---

## 9. Replay 设计

### 9.1 Entry windows

第一版只允许延迟 entry：

```text
entry_delay_from_available_at = 1h / 4h / 12h
```

禁止：

```text
0m entry
announcement-instant entry
market-order chase
```

### 9.2 Forward windows

```text
forward_windows = 1h / 4h / 12h / 24h
```

### 9.3 成本模型

```text
cost_scenarios_bps = 30 / 50 / 80
primary_cost_bps = 50
```

### 9.4 Baseline

必须包含：

```text
symbol-hour matched random baseline
price-move baseline
event-type matched baseline
BTC regime matched baseline
```

Baseline 采样规则必须固定：

```text
random_baseline_trials >= 500
match event_count
match symbol distribution
match event_type distribution
match hour-of-day
match weekday if possible
exclude candidate timestamp
require complete forward windows
fixed random_seed
output baseline_sampling_failure_count
```

### 9.5 必须输出的 replay metrics

```text
event_count
event_days
symbols_with_events
event_type_count
primary_event_type
median_net_return_after_50bps
mean_net_return_after_50bps
trimmed_mean_net_return_after_50bps
left_tail_p05_after_50bps
baseline_excess_net_bps
price_baseline_excess_net_bps
hit_rate_vs_random
top_5_positive_events_gross_profit_share
top_5_abs_pnl_share
max_single_day_event_share
max_single_symbol_event_share
baseline_sampling_failure_count
context_missingness_report
```

---

## 10. Pass / Stop Criteria

### 10.1 Source audit pass

```text
historical_events_found >= 30
source_integrity_pass_rate >= 95%
symbol_mapping_pass_rate >= 95%
available_at_policy_defined = true
forbidden_payload_count = 0
source_resource_safety_policy_defined = true
schema_quarantine_count is reported
payload_too_large_count is reported
json_depth_exceeded_count is reported
request_timeout_count is reported
retry_budget_exhausted_count is reported
symbol_mapping_ambiguous_count = 0 for replay rows
source_format_drift_count is reported
primary_event_type_events >= 20
timestamp_quality_high_or_medium_ratio >= 95%
```

### 10.2 Replay candidate pass

第一版 research pass 需要：

```text
event_count >= 30
event_days >= 10
symbols_with_events >= 3
primary_event_type_events >= 20
event_type_mixing_allowed_for_replay_pass = false
median_net_return_after_50bps > 0
baseline_excess_net_bps > 0
price_baseline_excess_net_bps > 0
left_tail_p05_after_50bps >= random_baseline_left_tail_p05
top_5_positive_events_gross_profit_share <= 0.40
max_single_day_event_share <= 0.30
max_single_symbol_event_share <= 0.60
```

注意：

```text
通过 Stage 1.5 replay 也不允许 paper/live。
只能进入 24h live smoke collector。
```

### 10.3 Stop criteria

任一情况触发 stop：

```text
source integrity 不可审计
available_at_ms 无法保守构建
source_resource_safety_policy 无法定义
schema parse / symbol mapping 错误被 silent ignore
事件数不足且不可扩展
replay 表现不优于 random baseline
收益只靠单日 / 单币 / top 5 事件
成本后中位收益为负
context filter 没有任何增量
任一 event type 的 replay 样本不足但被强行混合成通过
事后挑选表现最好的 group 作为主结论
```

---

## 11. Recommended Stage 1.5 子阶段

### Stage 1.5A：Historical Event Source Audit

目标：

```text
审计 Binance / OKX 官方公告、unlock calendars、event calendars 的历史可得性、字段质量、时间戳质量和 connector resource safety。
```

输出：

```text
source_audit_summary.json
source_audit_review_CN.md
```

`source_audit_summary.json` 必须包含：

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
timestamp_source_disagreement_count
timestamp_quality_distribution
available_at_delay_sensitivity_required
```

### Stage 1.5B：Minimal Historical Event Table

目标：

```text
构建 30-100 条高可信 external catalyst event JSONL。
```

输出：

```text
external_catalyst_events_raw.jsonl
external_catalyst_events_normalized.jsonl
normalization_summary.json
```

### Stage 1.5C：External Catalyst Replay

目标：

```text
按 filter matrix 固定分组做 delayed replay。
```

输出：

```text
stage1_5_external_catalyst_replay_summary.json
stage1_5_external_catalyst_replay_review_CN.md
```

### Stage 1.5D：24h / 7d Live Smoke Collector

只有历史 replay 有希望才允许。

目标：

```text
验证真实 source latency、字段稳定性、429、available_at_ms 与 safe fail。
```

不允许交易。

---

## 12. 最终决策

```text
decision = proceed_to_stage1_5a_historical_event_source_audit
collector_expansion_allowed = false_until_source_audit_pass
historical_replay_allowed_after_minimal_event_table = true
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
liquidation_collection_continues_as_data_asset = true
full_composite_track_deferred = true
post_hoc_group_selection_allowed = false
short_execution_intent_allowed = false
```

一句话：

```text
Stage 1.5 不是追公告，而是建立一套 external catalyst 的审计、过滤、分组 replay 机制。
只有当事件源、时间戳、资产质量、流动性、baseline 与集中度都通过后，才允许进入 live smoke。
```
