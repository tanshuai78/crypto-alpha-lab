# External Signal Shadow Lab Stage 1.4A.2 Vendor Liquidation Data Feasibility Design

日期：2026-06-15

## 1. 设计结论

Stage 1.4A.1 已经证明：`funding`、`OI`、`USD-M futures price` 三类数据具备 `>=90d` 可用历史，但 `liquidation` 数据仍是完整 derivatives stress composite 的唯一硬阻塞项。

当前 mixed audit 结果：

```text
funding_history_days ~= 179.67d
OI_history_days ~= 178.00d
price_history_days ~= 179.99d
local_force_order_liquidation_history_days ~= 12.31d - 14.27d
outcome = stage1_4_data_degraded
primary_blocker = liquidation_history_insufficient
stage1_4b_candidate_replay_allowed = false
composite_replay_allowed = false
```

因此 Stage 1.4A.2 的目标不是继续开发策略，也不是购买数据，而是做一个更窄的 vendor 数据可行性审计：

```text
是否存在适合本项目的 >=90d liquidation history vendor source？
```

推荐进入 Stage 1.4A.2：

```text
decision = proceed_to_stage1_4a2_vendor_liquidation_data_feasibility_design
scope = vendor_liquidation_data_feasibility_audit_only
primary_blocker_from_stage1_4a1 = liquidation_history_insufficient
purchase_allowed = false_by_default
sample_or_trial_only = true
stage1_4b_candidate_replay_allowed = false_by_default
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
```

Stage 1.4A.2 只允许输出三类结论：

```text
vendor_liquidation_source_feasible
vendor_liquidation_source_degraded
vendor_liquidation_source_unavailable
```

不允许输出：

```text
liquidation 有 alpha
可以进入 paper/live
可以交易 derivatives stress event
Stage 1.4B full composite 已通过
```

---

## 2. 为什么需要 Stage 1.4A.2

Stage 1.4A.1 的核心发现不是 derivatives stress 方向失败，而是数据拼图缺一块。

已通过的数据：

```text
funding: Binance public settled funding history, >=90d
OI: Binance Vision daily metrics converted local archive, >=90d
price: Binance USD-M futures 15m klines, >=90d
```

未通过的数据：

```text
liquidation: 本地 forceOrder archive 只有约 12-14d
```

Liquidation 是 Stage 1.4 composite 的核心，不是可选装饰。没有 `>=90d` liquidation history，就无法判断：

- liquidation cluster 的真实事件密度；
- long / short liquidation imbalance 是否跨 regime 稳定；
- liquidation 与 OI contraction / funding crowding 是否有足够 overlap；
- 是否只是靠一两天极端行情产生伪结构；
- random baseline / time-of-day baseline 是否有足够采样空间。

继续等待 90 天 live forceOrder 是最干净的长期方案，但会拖慢研究。Stage 1.4A.2 的作用是在不等待、不采购的前提下，先判断是否有可用 vendor source，减少盲等成本。

---

## 3. 本阶段不做什么

Stage 1.4A.2 不是数据采购计划。

禁止：

```text
直接购买年度订阅
上传 API key 到仓库
读取 .env / secrets
接入 vendor private account endpoint
下载大规模付费数据
做收益回放
做 Stage 1.4B candidate replay
生成交易信号
```

允许：

```text
阅读官方 docs / pricing / sample schema
申请 trial / sample file
下载公开 sample
手工记录 vendor 字段能力
对 sample 做 schema compatibility audit
估算成本和 license 风险
```

如果 vendor 需要 API key 才能访问 sample，第一版也不把 key 写进代码。只能由用户手动导出 sample 到本地 ignored path，再由本项目读取本地 sample 文件做 audit。

---

## 4. 候选 vendor source

第一版只审计 5 个候选 source，不继续扩散：

```text
P1: Tardis.dev
P2: Coinalyze
P3: CoinGlass
P4: Coin Metrics Pro
P5: Laevitas
```

### 4.1 `Tardis.dev`

官方资料显示 Tardis.dev 提供历史 tick-level crypto market data，覆盖 order books、trades、funding、open interest、liquidations 等，并支持 API / downloadable CSV。其文档也把 `liquidation` 定义为来自 exchange-native liquidation feeds 的事件类型，例如 Binance `forceOrder`、Bybit `allLiquidation`、OKX `liquidation-orders`。

对本项目的价值：

```text
最可能提供 tick-level liquidation history
字段语义更接近 exchange-native feed
可能支持 Binance / Bybit / OKX 等多 exchange
```

主要风险：

```text
成本未知或偏高
历史数据量较大
需要确认 Binance USD-M liquidation 覆盖起止日期
需要确认 sample 可导出为 CSV/NDJSON
```

初始评级：

```text
priority = P1
expected_fit = high
purchase_now = false
```

### 4.2 `Coinalyze`

Coinalyze 页面显示其覆盖 aggregated futures market data，包括 open interest、funding rate、liquidations、basis 等。API 文档显示需要 API key。

对本项目的价值：

```text
可能提供 aggregated liquidation history
与 funding / OI / basis 数据族一致
适合低频 15m / 1h composite，不一定需要 tick-level
```

主要风险：

```text
可能是 aggregated 而非逐笔 liquidation
license / API limit 需要确认
字段是否含 long/short side 和 notional USD 需要 sample 验证
```

初始评级：

```text
priority = P2
expected_fit = medium_high
purchase_now = false
```

### 4.3 `CoinGlass`

CoinGlass API 文档显示有 pair liquidation history 与 aggregated liquidation history endpoint；其 liquidation order endpoint 只提供近 7 天订单数据，而 liquidation history endpoint 面向历史 long/short liquidation 数据。CoinGlass 页面也显示有 90d / all 的 liquidation history 图表能力。

对本项目的价值：

```text
可能直接提供 long / short liquidation history
可能区分 exchange / pair
上手成本可能低于 tick-level vendor
```

主要风险：

```text
历史 endpoint 的 plan 限制、时间范围、粒度需要确认
aggregated history 不一定有逐笔 timestamp
免费层或普通层可能不足以导出 >=90d sample
```

初始评级：

```text
priority = P3
expected_fit = medium
purchase_now = false
```

### 4.4 `Coin Metrics Pro`

Coin Metrics 文档显示 community API 只提供最近 24h liquidation data，而 professional API 提供完整 liquidations data 与更高 rate limit。

对本项目的价值：

```text
数据供应商可信度高
字段和 market metadata 可能较规范
适合机构级研究审计
```

主要风险：

```text
专业 API 成本可能较高
community API 明确不够 >=90d
需要商务/试用流程
```

初始评级：

```text
priority = P4
expected_fit = high_but_cost_sensitive
purchase_now = false
```

### 4.5 `Laevitas`

Laevitas 公开资料显示其是 derivatives analytics / data 平台，覆盖 futures、options、order book、funding、liquidations 等。其历史 API 文档更容易确认 OI / volume 等 derivatives history；liquidation 历史字段需要进一步以 API docs 或 sample 核实。

对本项目的价值：

```text
衍生品数据平台定位匹配
可能适合 derivatives stress research
```

主要风险：

```text
liquidation history endpoint 和字段需要进一步确认
可能更偏 analytics dashboard，不一定方便 raw sample export
```

初始评级：

```text
priority = P5
expected_fit = unknown_medium
purchase_now = false
```

---

## 5. Vendor sample 审计 schema

每个 vendor 需要输出一条 `vendor_liquidation_source_audit` 记录。

建议 schema：

```json
{
  "vendor": "tardis_dev",
  "source_surface": "official_docs|trial_sample|manual_sales_reply|public_sample",
  "audit_time_ms": 1781452800000,
  "purchase_required_for_sample": false,
  "sample_file_available": true,
  "license_allows_local_research": true,
  "history_days_claimed": 180,
  "history_days_verified_from_sample": 0,
  "symbols_claimed": ["BTCUSDT", "ETHUSDT"],
  "symbols_verified": ["BTCUSDT"],
  "exchange_scope": "binance_usdm|multi_exchange|aggregated_unknown",
  "timestamp_resolution_ms": 1000,
  "side_available": true,
  "side_semantics": "long_short|buy_sell|unknown",
  "notional_usd_available": true,
  "price_available": true,
  "quantity_available": true,
  "exchange_field_available": true,
  "symbol_field_available": true,
  "timestamp_field_available": true,
  "download_or_export_format": "csv|jsonl|parquet|api_json|unknown",
  "available_at_policy_defined": true,
  "field_mapping_status": "compatible|needs_transform|incompatible|unknown",
  "stage1_4a1_alignment_status": "compatible|degraded|incompatible|unknown",
  "estimated_cost_usd_per_month": null,
  "manual_notes": []
}
```

其中 `available_at_policy_defined` 的意思是：

```text
历史 vendor 数据没有真实实时 arrival time 时，回放必须使用保守 timestamp policy。
```

默认 policy：

```text
event_time_ms = liquidation event timestamp from vendor
available_at_ms = event_time_ms + configured_vendor_data_lag_ms
configured_vendor_data_lag_ms >= 60_000
```

如果 vendor 数据是 aggregated 1m bar：

```text
available_at_ms = bucket_end_ms + configured_vendor_data_lag_ms
```

不能用 bucket start 当 replay anchor。

---

## 6. 通过门槛

Vendor 只有满足以下条件，才允许进入下一步 sample parser implementation plan：

```text
history_days_claimed >= 90
sample_file_available = true
license_allows_local_research = true
symbols_with_usable_data >= 3
side_available = true
notional_usd_available = true
symbol_field_available = true
timestamp_field_available = true
exchange_scope != aggregated_unknown
timestamp_resolution_ms <= 60_000
field_mapping_status in {compatible, needs_transform}
stage1_4a1_alignment_status in {compatible, degraded}
purchase_required_for_sample = false OR explicit_user_approval_for_trial = true
```

Hard reject：

```text
license disallows local research
only dashboard screenshots, no export
no side / long-short field
no timestamp field
no symbol field
no notional / price / quantity sufficient to compute notional
only real-time < 7d data
requires private trading account permission
requires API key in repo or .env automation
```

如果只有 aggregated liquidation data，但包含：

```text
long_liquidation_usd
short_liquidation_usd
symbol
exchange
timestamp/bucket_end
```

则可标记为：

```text
field_mapping_status = compatible
source_granularity = aggregated_window
```

不要求 tick-level。Stage 1.4 的候选事件本来就是 `15m / 1h` 聚合级别，不做秒级交易。

---

## 7. 与现有 Stage 1.4A.1 数据如何对齐

Vendor liquidation sample 必须能对齐现有三类已通过数据：

```text
funding: Binance /fapi/v1/fundingRate, 8h settlement
OI: Binance Vision daily metrics archive, inferred interval, ~=5m in current sample
price: Binance USD-M futures 15m klines
```

对齐规则：

```text
symbol normalized to BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT / DOGEUSDT
liquidation event timestamp -> 15m and 1h UTC buckets
long liquidation = forced SELL pressure
short liquidation = forced BUY pressure
notional_usd = vendor provided OR price * quantity with explicit semantics
exchange must be Binance USD-M or clearly marked multi-exchange aggregate
```

如果 vendor 只有 multi-exchange aggregate：

```text
exchange_scope = multi_exchange
stage1_4a1_alignment_status = degraded
binance_usdm_exact = false
```

这种数据可以做 partial diagnostic，但不能直接声称 Binance USD-M composite 已满足。

---

## 8. 成本与授权边界

Stage 1.4A.2 不做采购，只做以下动作：

```text
read official docs
record pricing page visibility
request trial/sample if no payment required
manual export sample if user approves
local sample audit
```

如果 vendor 要求付费，输出：

```text
purchase_required = true
estimated_cost_usd_per_month = known_or_unknown
next_action = user_cost_decision_required
```

此时停止，不允许 agent 自动继续。

如果 vendor 要求 API key：

```text
api_key_required = true
```

第一版 implementation 不读取 `.env`，不接 secret manager，不把 key 写进 repo。用户可以手动导出 sample 到：

```text
data/external_signal_shadow/vendor_liquidation_samples/{vendor}/
```

该目录必须被 `.gitignore` 忽略。

---

## 9. 输出 artifacts

Stage 1.4A.2 应输出：

```text
reports/external_signal_shadow/stage1_4a2_vendor_liquidation_data_feasibility_summary.json
docs/reviews/2026-06-15-external-signal-shadow-lab-stage1-4a2-vendor-liquidation-data-feasibility-review_CN.md
```

Summary 顶层字段：

```json
{
  "decision": "vendor_liquidation_source_feasible|vendor_liquidation_source_degraded|vendor_liquidation_source_unavailable",
  "primary_blocker": "...",
  "candidate_vendor_count": 5,
  "feasible_vendor_count": 0,
  "purchase_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "alpha_interpretation_allowed": false,
  "stage1_4b_candidate_replay_allowed": false,
  "vendor_audits": []
}
```

Review 必须包含表格：

```text
vendor | sample_available | history_days | symbols | side | notional_usd | timestamp_resolution | exchange_scope | license_ok | cost_known | decision | blocker
```

---

## 10. 决策树

```text
if feasible_vendor_count >= 1:
    next_action = write_stage1_4a3_vendor_sample_parser_plan
elif at_least_one_vendor_requires_paid_trial_but_fields_look_promising:
    next_action = user_cost_decision_required
elif no vendor has sample/export/license clarity:
    next_action = fallback_to_stage1_4b_lite_or_continue_live_collection
else:
    next_action = stop_vendor_liquidation_path
```

`Stage 1.4B full composite replay` 仍保持 blocked，直到：

```text
vendor sample parser proves usable rows >=90d
or local forceOrder archive reaches >=90d
```

---

## 11. 与其他路径的关系

### 路径 B：`Stage 1.4B-Lite`

可以作为备选，但不应先于 Stage 1.4A.2。

原因：B-Lite 不使用 liquidation，只能回答：

```text
funding + OI + price crowding 是否有结构？
```

不能回答：

```text
full derivatives stress composite 是否有结构？
```

### 路径 C：`CM liquidation proxy diagnostic`

可做 parser 演练，但优先级低。

它只能支持：

```text
partial proxy diagnostic
```

不能支持：

```text
USD-M full composite replay
```

### 路径 D：继续 live forceOrder collection

必须继续，但不阻塞 Stage 1.4A.2。

建议后台检查节奏：

```text
每 7 天输出 live liquidation density report
30d: density sanity check
60d: preliminary structure check
90d: full replay eligibility check
```

---

## 12. 最终建议

进入 Stage 1.4A.2：

```text
decision = proceed_to_stage1_4a2_vendor_liquidation_data_feasibility_design
implementation_scope = docs_and_sample_audit_only
first_action = write_stage1_4a2_vendor_liquidation_data_feasibility_implementation_plan
purchase_allowed = false
stage1_4b_candidate_replay_allowed = false
live_safe = false
```

一句话：

```text
先审 vendor liquidation 数据是否存在、字段是否够、license 是否允许、sample 是否能导出；不买数据、不回测、不宣称 alpha。
```

---

## 13. Sources

- Tardis.dev: historical tick-level market data covering liquidations, funding, OI, order books and downloadable/API access.
- Tardis.dev docs: `liquidation` data type sourced from exchange-native liquidation feeds such as Binance `forceOrder`.
- Coin Metrics docs: community liquidation data limited to recent 24h; full liquidation data is professional API.
- Coinalyze: derivatives market data includes OI, funding, liquidations, basis.
- CoinGlass API docs: pair and aggregated liquidation history endpoints, plus real-time liquidation order endpoint with shorter range.
- Laevitas docs/pages: derivatives analytics/data platform; historical derivatives endpoints visible, liquidation history details require sample/API verification.
