# External Signal Shadow Lab Stage 1.5 External Catalyst Filter Matrix Design

日期：2026-06-22

## 0. 一句话结论

本文件只定义 Stage 1.5 的 **Filter Matrix（过滤矩阵）**。

它不是 Stage 1.5 总路线，不是 source audit implementation plan，也不是交易策略。

```json
{
  "stage": "external_signal_shadow_lab_stage1_5",
  "scope": "external_catalyst_filter_matrix_design_only",
  "architecture_design": "docs/designs/2026-06-21-external-signal-shadow-lab-stage1-5-external-catalyst-architecture-design_CN.md",
  "execution_engine_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "alpha_interpretation_allowed": false,
  "external_event_direct_entry_allowed": false,
  "short_execution_intent_allowed": false,
  "post_hoc_group_selection_allowed": false,
  "event_type_mixing_allowed_for_replay_pass": false
}
```

Filter Matrix 的目标是：

```text
把 external catalyst event 从“新闻/公告/日历”转换成可审计、可分组、可证伪的研究事件。
```

---

## 1. Filter Matrix 总体结构

Filter Matrix 分为四层：

```text
Layer A: Hard Veto Filters
Layer B: Eligibility Filters
Layer C: Context Label Filters
Layer D: Replay Group Matrix
```

核心原则：

```text
Hard veto = 一票否决；触发后 event 不进入 replay candidate。
Eligibility = 判断 event 是否有资格进入 replay 或只能 observation-only。
Context label = 只做分组变量，不做硬触发，不单独作为 entry rule。
Replay group = 固定分组，用来评估 filter 是否有增量信息。
```

所有 filter 必须满足：

```text
asof_safe = true
context_available_at_ms <= entry_candidate_time_ms
post_hoc_group_selection_allowed = false
```

---

## 2. Layer A — Hard Veto Filters

Hard Veto Filters 是一票否决。触发后 event 不进入 replay candidate。

### 2.1 Source Integrity Veto

| 字段 | 规则 |
|---|---|
| `source_url` | 必须存在 |
| `source_domain` | 必须存在，且属于 allowlist |
| `raw_payload_hash` | 必须存在 |
| `available_at_ms` | 必须存在或可保守推断 |
| `event_type` | 必须属于 allowed enum |
| `symbol_mapping` | 必须唯一 |

Veto reasons:

```text
missing_source_url
missing_source_domain
domain_allowlist_violation
missing_raw_payload_hash
missing_available_at_ms
ambiguous_symbol_mapping
unsupported_event_type
```

### 2.2 Forbidden Payload Veto

任何 raw payload 出现以下字段，直接 reject：

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

Veto reason:

```text
forbidden_payload_detected
```

### 2.3 Source Resource Safety Veto

`source_resource_safety_veto` 在 connector normalize 前生效，防止格式炸弹、重试风暴、source drift 或错误 symbol mapping 污染研究表。

必须定义：

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

Veto / quarantine reasons:

```text
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

触发后：

```text
replay_allowed = false
quarantine_or_observation_only = true
silent_fallback_allowed = false
auto_symbol_guess_allowed = false
```

### 2.4 Available-at / Hindsight Veto

规则：

```text
available_at_ms 必须来自 source_published_at_ms + conservative_delay_ms，
或来自 live smoke 阶段的 collector_received_at_ms。
```

第一版 delay scenarios:

```text
exchange_announcement_delay_scenarios = 5min / 15min / 60min
primary_delay = 15min
```

Historical replay 只允许：

```text
historical_available_at_confidence in [high, medium]
edited_page_risk = false
hindsight_risk = false
```

Veto / downgrade reasons:

```text
source_time_missing
timestamp_quality_low
edited_page_risk
hindsight_risk_detected
calendar_snapshot_missing
```

低可信事件只能：

```text
observation_only = true
replay_allowed = false
```

### 2.5 First-Hour Entry Delay Policy

这不是 event veto，而是 entry delay policy。

```text
entry_candidate_time_ms >= available_at_ms + 60min
```

用途：

```text
避开公告瞬间的低延迟竞争、盘口撤单、极端滑点、fake repricing 和薄盘插针。
```

首小时只允许记录 context：

```text
post_event_return_15m
post_event_return_1h
spread_change
depth_change
liquidation_context
```

禁止：

```text
first_minute_entry
announcement_instant_entry
market_order_chase
```

### 2.6 Asset Quality Veto

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
new_coin_listing
low_float_high_fdv_token
low_depth_memecoin
no_reliable_perp_market
contract_risk_asset
symbol_mapping_unresolved
```

Veto reasons:

```text
asset_not_in_allowed_tier
low_float_high_fdv
no_reliable_derivatives_market
low_liquidity_asset
contract_risk_asset
```

### 2.7 Liquidity / Depth / Spread Veto

第一版推荐硬门槛：

```text
min_24h_futures_quote_volume_usdt >= 50_000_000
max_spread_bps <= 20
min_top_1pct_depth_usdt >= 2 * planned_position_notional
max_slippage_estimate_bps_for_500usdt <= 50
```

如果没有 orderbook / depth 数据：

```text
close_price_replay_only = true
execution_feasibility_unknown = true
execution_relevance_claim_allowed = false
replay_allowed = true for research
live_or_shadow_upgrade_allowed = false
```

---

## 3. Layer B — Eligibility Filters

Eligibility Filters 判断 event 是否有资格进入不同研究分组。

### 3.1 Event Type Eligibility

| `event_type` | replay eligibility | 备注 |
|---|---|---|
| `exchange_delisting_notice` | eligible | 优先 |
| `futures_contract_launch` | eligible | 优先 |
| `margin_enablement` | eligible | 优先 |
| `trading_pair_removal` | eligible | 优先 |
| `trading_pair_addition_for_existing_liquid_asset` | eligible | 必须有事件前流动性 |
| `major_exchange_status_event` | eligible | 需冻结 replay mode |
| `major_unlock_event` | audit_first | 历史 schedule 风险 |
| `large_scheduled_token_emission` | audit_first | 历史 schedule 风险 |
| `spot_listing_existing_liquid_asset` | observation_only | 首小时风险高 |
| `new_coin_listing` | excluded | 第一版不碰 |
| `whale_deposit` | excluded | 第一版不碰 |
| `kol_tweet` | excluded | 第一版不碰 |

### 3.2 Event Magnitude Eligibility

每个 event type 必须有可解释强度。

Examples:

```text
delisting:
  notice_to_effective_hours
  affected_pair_count
  venue_tier

contract_launch:
  venue_tier
  trading_start_time_ms
  contract_type
  max_leverage

unlock:
  unlock_amount_usd
  unlock_pct_circulating_supply
  unlock_pct_30d_volume
```

缺少 magnitude：

```text
magnitude_unknown = true
replay_group = event_only_or_observation
```

### 3.3 Historical Availability Eligibility

Source audit preferred thresholds:

```text
historical_events_found >= 30
primary_event_type_events >= 20
unique_event_days >= 20
symbols_with_events >= 3
timestamp_quality_high_or_medium_ratio >= 95%
```

若不满足：

```text
source_status = sparse_inconclusive
replay_pass_allowed = false
```

---

## 4. Layer C — Context Label Filters

Context Label Filters 不做一票否决，只给事件打标签，用于分组 replay。

所有 context label 必须满足：

```text
context_available_at_ms <= entry_candidate_time_ms
```

如果 context 是事件后观测值，例如 `post_event_return_1h_bps`，则只能用于 `entry_delay >= 1h` 的 replay 分组，不能用于 0-1h forward return 判定。

### 4.1 Local ForceOrder Liquidation Context

来源：local forceOrder snapshot archive。

标签：

```json
{
  "local_liquidation_cluster_present_1h": false,
  "local_liquidation_cluster_present_4h": false,
  "long_liquidation_share_1h": null,
  "short_liquidation_share_1h": null,
  "liquidation_notional_zscore_4h": null,
  "complete_liquidation_tape_claim_allowed": false
}
```

解释：

```text
可以作为 context label。
不能 claim complete tape。
不能单独证明 liquidation alpha。
```

### 4.2 Deleveraging Proxy Diagnostic Context

由于 Stage 1.4E 未通过，OI drop + price flush 只能 diagnostic-only。

标签：

```json
{
  "deleveraging_proxy_15m_present": false,
  "deleveraging_proxy_1h_present": false,
  "deleveraging_proxy_hard_filter_allowed": false,
  "deleveraging_proxy_diagnostic_only": true
}
```

禁止：

```text
deleveraging_proxy_filter_pass
proxy_confirmed_liquidation
proxy_as_primary_signal
```

### 4.3 Funding Crowding Context

标签：

```json
{
  "funding_percentile_90d": null,
  "funding_positive_extreme": false,
  "funding_negative_extreme": false,
  "funding_flip_recent": false
}
```

用途：

```text
分组 replay：event + funding crowded vs event + funding neutral。
不能单独作为方向信号。
```

### 4.4 OI Crowding Context

标签：

```json
{
  "oi_percentile_30d": null,
  "oi_high_and_rising": false,
  "oi_high_and_falling": false,
  "oi_expansion_4h": null,
  "oi_contraction_4h": null
}
```

用途：

```text
判断 catalyst 前是否已经有杠杆拥挤。
事件后 OI drop 不作为硬入场触发。
```

### 4.5 Price Reaction Context

标签：

```json
{
  "post_event_return_1h_bps": null,
  "post_event_return_4h_bps": null,
  "post_event_volatility_4h": null,
  "first_hour_repriced": false,
  "price_flush_present": false,
  "price_squeeze_present": false
}
```

用途：

```text
判断事件后是否已经快速重定价。
只能在对应 context 已可得的 entry delay 分组中使用。
```

### 4.6 Orderbook / Execution Context

标签：

```json
{
  "spread_bps": null,
  "top_0_5pct_depth_usdt": null,
  "top_1pct_depth_usdt": null,
  "slippage_estimate_bps_for_500usdt": null,
  "depth_collapse_flag": false,
  "execution_feasibility_unknown": false
}
```

用途：

```text
判断 close-price replay 是否有执行意义。
没有 orderbook 时，不能输出 execution-ready 结论。
```

### 4.7 Market Regime Context

标签：

```json
{
  "btc_return_4h_bps": null,
  "btc_return_24h_bps": null,
  "btc_realized_vol_24h": null,
  "market_drawdown_24h": null,
  "systemic_risk_flag": false
}
```

用途：

```text
区分单币事件与系统性市场冲击。
```

---

## 5. Layer D — Replay Group Matrix

Stage 1.5 不是直接测试一个最终策略，而是测试 filter 是否增加信息量。

### 5.1 固定 replay groups

```text
Group 0: event_only
Group 1: event + first_hour_entry_delay_policy
Group 2: event + first_hour_entry_delay_policy + asset_quality_pass
Group 3: event + first_hour_entry_delay_policy + asset_quality_pass + liquidity_pass
Group 4: event + first_hour_entry_delay_policy + asset_quality_pass + liquidity_pass + local_liquidation_context_present
Group 5a: event + first_hour_entry_delay_policy + asset_quality_pass + liquidity_pass + funding_crowding_context
Group 5b: event + first_hour_entry_delay_policy + asset_quality_pass + liquidity_pass + oi_crowding_context
Group 5c: event + first_hour_entry_delay_policy + asset_quality_pass + liquidity_pass + funding_crowding_context + oi_crowding_context
Group 6: event + first_hour_entry_delay_policy + asset_quality_pass + liquidity_pass + market_regime_context
```

规则：

```text
Group 0-3 是基础安全分组。
Group 4-6 是上下文实验分组。
primary_replay_group 必须在 implementation plan 前预注册。
其他 group 默认 report-only。
任何 group 通过都不允许 paper/live。
```

### 5.2 不允许的 group

```text
event + deleveraging_proxy_hard_filter
event + whale_deposit_signal
event + first_minute_entry
event + new_coin_listing_long
event + post_hoc_best_context_group
```

---

## 6. Replay 解释边界

即使某个 replay group 通过，也只能说明：

```text
该 external catalyst + fixed filter group 在历史 replay 中值得进入下一阶段审计。
```

不能说明：

```text
external event alpha confirmed
paper/live approved
execution-ready
short execution feasible
liquidation composite solved
```

必须输出：

```json
{
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "alpha_interpretation_allowed": false,
  "short_execution_intent_allowed": false,
  "filter_matrix_is_trade_rule": false
}
```

---

## 7. Implementation Plan 继承要求

后续 Stage 1.5A implementation plan 必须只实现 source audit 相关部分：

```text
Layer A: source_integrity / forbidden_payload / source_resource_safety / available_at / hindsight
Layer B: event_type / magnitude / historical availability
```

Stage 1.5A 不得实现：

```text
Layer C context labels
Layer D replay groups
historical replay
live smoke collector
paper/live trading
```

Layer C / D 只能在 Stage 1.5B/1.5C 计划中实现，并且必须重新确认 data availability、as-of 语义和 replay group 预注册。
