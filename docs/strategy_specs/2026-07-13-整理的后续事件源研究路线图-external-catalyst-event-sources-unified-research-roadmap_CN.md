# External Signal Shadow Lab：后续事件源统一研究路线总纲（个人投资者可执行版）

**日期：** 2026-07-13  
**用途：** 统一后续 external catalyst event source（外部催化事件源）的研究顺序、可行性判断、工程难度、证据门槛与停止条件。  
**适用分支：** External Signal Shadow Lab / External Catalyst Events + Filter  
**文档状态：** research_route_guide / not_a_strategy / no_paper_live  

---

## 0. 核心结论

后续事件源不应按“听起来最热门”排序，而应按以下顺序排序：

```text
1. 能否使用公开只读数据稳定获取；
2. available_at_ms 能否保守定义；
3. 历史样本能否快速积累并复现；
4. 是否适合个人投资者研究 1h 以上的二阶反应；
5. 是否能复用现有 Stage 1.5 的公告、symbol mapping、replay 与 live depth 管线；
6. 扣除成本、延迟和集中度后，是否有机会优于随机、价格和市场状态基线。
```

为了尽快发现值得继续研究的 alpha 候选，同时避免在高噪声数据上消耗过多时间，建议采用两条并行队列：

### Alpha discovery 主队列

```text
Stage 1.6A  Futures Delisting Notice
Stage 1.6B  ETF / Institutional Flow Regime Diagnostic（快速证伪线）
Stage 1.6C  Prediction Market Probability Shift
Stage 1.6D  Scheduled Token Unlock / Emission
Stage 1.6E  Margin / Borrow Enablement
Stage 1.6F  Stablecoin / Exchange Flow Shock
Stage 1.6G  Sentiment / Narrative Attention Spike
Stage 1.6H  Spot Pair Addition After-First-Hour
Stage 1.6I  Governance / Protocol / Tokenomics Events
```

### Risk-veto 旁路线

```text
Stage 1.6R  Security Incident / Exploit / Depeg / Chain Halt
```

`Stage 1.6R` 的第一目标不是寻找方向性收益，而是识别应回避的高风险状态、流动性中断和传染风险。只有后续数据证明存在稳定的低频二阶反应，才允许单独评估其 alpha 价值。

`Stage 1.6R` 的成功标准必须与 alpha 路线分离：

```text
risk_veto_route_success != alpha_success
directional_replay_failed does not invalidate risk_veto_value
primary_success_metric = confirmed_status + affected_assets + avoidance_window + false_alarm_rate
```

含义：即使 security / exploit / depeg 事件完全不适合方向性交易，只要能稳定识别需要回避的资产、窗口和传染范围，`Stage 1.6R` 仍可作为风险控制能力继续推进。

当前 `futures_contract_launch` 已由 Stage 1.5 主线研究，不应在新路线中重复建设。它继续作为 listing family 的既有实验线，仅保留 after-first-valid-book / after-first-hour 的低频研究口径。

---

## 1. 项目对 Alpha 的定义

本项目中的 `alpha` 不是“事件后价格涨过或跌过”，而是：

```text
某类外部信息，在使用保守 available_at_ms、合理 entry delay、真实手续费和滑点、
随机/价格/市场状态基线、集中度检查与 live depth 证据后，
仍然能产生稳定、可重复、不过度依赖单币或极端样本的增量信息。
```

因此：

```text
公告后上涨或下跌 ≠ alpha
close-price replay 为正 ≠ 可执行
单事件表现很好 ≠ 事件家族成立
低滑点 ≠ 有收益
高信息密度 ≠ 适合个人投资者
```

后续所有路线都必须遵守：

```text
source audit
-> schema audit
-> available_at_ms policy
-> minimal event table
-> historical replay
-> random / price / regime baseline
-> cost stress
-> live source observation
-> live depth / liquidity evidence
-> evidence review
-> continue / stop
```

---

## 2. 个人投资者统一硬边界

### 2.1 默认排除

```text
毫秒级公告抢跑
新币首分钟狙击
KOL / Telegram / news 秒级跟单
MEV 或链上交易排序竞争
跨交易所秒级套利
需要 VIP API、专线或做市商库存
需要账户 API key、私钥或钱包签名
需要即时借币库存才能成立的第一版策略
```

### 2.2 默认保留

```text
T+1h / T+4h / T+12h / T+24h 的二阶反应
日频或多日资金流
公告后风险重估、供给压力和流动性迁移
情绪或概率的状态切换
盘口恶化、恢复和不可执行窗口
可用 500 USDT 级别风险上限进行 depth/slippage 审计的场景
```

### 2.3 所有路线默认配置

```text
first_hour_no_trade_veto = true
minimum_actionable_latency_bucket = ">=1h"
personal_investor_feasibility_required = true
no_private_endpoint = true
no_api_key_required = true
no_wallet_required = true
no_vip_fee_assumption = true
no_borrow_inventory_dependency_for_first_version = true
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

`first_hour_no_trade_veto` 是默认规则，不代表所有事件都必须永久排除第一小时。只有在独立 live depth evidence 证明首小时稳定、可审计且不依赖低延迟竞争后，才允许另行评审。

---

## 3. 统一优先级与难度矩阵

| 顺序 | 事件源 | 找到候选 edge 的速度 | 数据可审计性 | 工程难度 | 个人投资者适配 | 最可能价值 | 第一动作 |
|---:|---|---|---|---|---|---|---|
| 1 | `futures_delisting_notice` | 中高 | 高 | 中 | 高 | 强制减仓流、流动性撤退、settlement timetable 压力 | futures-only source/schema/effective-time design |
| 2 | `ETF / institutional flow regime diagnostic` | 高 | 中高 | 低 | 高 | BTC/ETH 日频 risk appetite regime label | source/available-time quick screen + regime diagnostic |
| 3 | `prediction_market_probability_shift` | 中高 | 中高 | 中 | 中高 | 宏观/监管概率重定价 | source/schema/settlement audit |
| 4 | `scheduled_token_unlock / emission` | 中 | 中低 | 中高 | 高 | 供给 overhang、提前定价 | calendar source/version audit |
| 5 | `margin / borrow enablement` | 中 | 中高 | 中高 | 中 | shortability / leverage access shock | 单一产品族 source audit |
| 6 | `stablecoin / exchange flow shock` | 中 | 中 | 高 | 中高 | 潜在购买力/卖压、流量状态 | address-label audit |
| 7 | `sentiment / narrative attention spike` | 中 | 低中 | 高 | 中 | attention drift / volatility regime | source selection + bot/noise audit |
| 8 | `spot pair addition after first hour` | 中低 | 高 | 中 | 中低 | 流动性迁移、attention drift | event-type split source audit |
| 9 | `governance / protocol / tokenomics` | 低中 | 中 | 高 | 中高 | 供给/现金流/协议价值变化 | semantic/status source audit |
| R | `security / exploit / depeg` | 不按方向 alpha 排名 | 中 | 高 | 风险规避高 | risk veto / contagion diagnostic | confirmed incident source audit |

说明：

- “找到候选 edge 的速度”指完成一次可信 source audit 和初步 replay 的速度，不代表更容易最终盈利。
- ETF flow 排名靠前，是因为数据频率稳定、工程成本低，适合快速证伪；它的最终 alpha 上限未必高。
- Sentiment 和 stablecoin flow 可能有较高信息上限，但数据清洗和历史可复现难度大，不适合作为最先投入的路线。
- Security incident 信息冲击强，但执行和尾部风险极高，第一版应服务于 veto，而不是做空或接飞刀。

---

# 第一梯队：优先推进与快速证伪

## 4. Stage 1.6A：Futures Delisting Notice

### 4.1 为什么排第一

它是当前最务实的新事件源：

```text
官方公告源可复用 Stage 1.5 基础设施；
effective_time / delisting_time 通常有明确语义；
事件可能引发持续数小时至数日的风险重估和流动性迁移；
不要求个人投资者在公告首秒参与。
```

更高层判断：

```text
原始路线 = announcement_T_plus_1h_blind_short
decision = rejected
reason = liquidity_vacuum_short_squeeze_and_available_at_risk

重构路线 = futures_delisting_source_schema_effective_time_audit
decision = continue_as_source_audit_only
primary_mechanism = forced_position_reduction + liquidity_withdrawal + rule_based_settlement_timetable
```

含义：`Stage 1.6A` 不是“下架做空策略”，而是先验证 futures delisting 的公告源、时间锚点、产品族和下架规则是否可审计。只有 source/schema/effective-time 审计通过后，才允许单独讨论 `pre_settlement_forced_flow_diagnostic_replay_design`。

### 4.2 第一版范围

```text
source = Binance official announcements
product_scope = binance_futures_delisting_only
primary_route = futures_delisting_source_schema_effective_time_audit
secondary_route = pre_settlement_forced_flow_diagnostic
```

必须区分：

```text
spot_delisting
futures_delisting
margin_delisting
borrow_delisting
trading_pair_removal
```

第一版只接受：

```text
futures_delisting = in_scope
spot_delisting = excluded
margin_delisting = excluded
loan_delisting = excluded
convert_delisting = excluded
trading_pair_removal_without_futures_settlement = excluded
```

第一版不要混入所有市场类型，也不得把 spot/margin/loan 下架样本拿来补 futures delisting 样本数。

### 4.3 可能的 alpha 机制

```text
风险重估：资产质量、合规、流动性与交易通道风险被重新定价；
流动性迁移：做市商撤单、交易者迁移、跨所价差扩大；
强制处理：最后交易、自动结算和仓位关闭形成非自愿交易流；
时间锚点：公告时点与正式下线时点之间可能存在可研究的慢速结构。
```

必须反向记录的失败假设：

```text
forbidden_hypothesis = announcement_plus_1h_blind_short
forbidden_assumption = delisting_is_unidirectional_short_edge
forbidden_assumption = final_settlement_anchor_eliminates_intraperiod_risk
```

正确研究对象不是“下架必跌”，而是：

```text
forced_flow_diagnostic
liquidity_deterioration_diagnostic
mark_index_divergence_diagnostic
MAE_before_terminal_convergence
```

### 4.4 研究窗口

```text
after available_at_ms diagnostic: T+1h / T+4h / T+12h / T+24h
pre_settlement diagnostic: settlement_time - 24h -> settlement_time - 1h
post_settlement diagnostic: report-only / no execution interpretation
```

announcement、effective 和 settlement 三类 anchor 必须分开。

防泄漏规则：

```text
pre_effective_replay_start_ms = max(
  available_at_ms + entry_delay_ms,
  effective_time_ms - lookback_window_ms
)
pre_effective rows before available_at_ms are forbidden
```

含义：`before effective_time` 只能研究公告已经公开后的下线前窗口，不允许用公告发布前市场不可见的 `effective_time` 做事后锚定。

必须解析的时间锚点：

```text
available_at_ms
settlement_time_ms
non_reduce_only_start_time_ms
final_hour_start_time_ms
last_trading_time_ms
```

禁止窗口：

```text
announcement_first_hour = hard_veto_for_execution_research
final_hour_before_settlement = hard_veto_for_new_entry
after_non_reduce_only_start_for_new_entry = hard_veto
post_settlement = report_only
```

`T-24h -> T-1h` 只是候选 replay 窗口，不是交易授权。该窗口必须同时输出 MAE、wick risk、spread/depth/slippage、funding crossing、mark-index divergence 和 book availability。

### 4.5 第一份文档

```text
2026-07-xx-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md
```

第一阶段只回答：

```text
source 是否稳定？
market_scope 是否可拆？
effective_time 是否可解析？
available_at_ms 是否可保守构建？
settlement_time_ms / non_reduce_only_start_time_ms / final_hour_start_time_ms 是否可解析？
历史 futures market existence 是否可确认？
历史样本是否达到 replay 前置门槛？
```

不得直接写：

```text
delisting short strategy
delisting alpha replay plan
pre_settlement forced-flow implementation plan
paper/live execution plan
SignalCandidate / TradeIntent
```

默认允许动作：

```text
allowed_next_action = write_source_schema_effective_time_audit_plan
replay_allowed = false
implementation_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

### 4.6 Kill criteria

```text
历史样本不足且不可扩展；
spot/futures/margin scope 无法可靠区分；
effective_time 缺失率过高；
settlement_time / non_reduce_only_start_time / final_hour_start_time 缺失率过高；
无法确认历史 futures market existence；
公告前价格已完成全部反应，T+1h 后无增量；
盘口过薄，close-price edge 无 live execution research 价值；
T-24h -> T-1h 结构完全被 BTC regime / price momentum / liquidity bucket 解释；
short diagnostic 收益存在但 MAE、wick risk、spread 或 book unavailability 使其不可执行；
必须混入 spot/margin/loan delisting 才能得到正结果。
```

---

## 5. Stage 1.6B：ETF / Institutional Flow Regime Diagnostic

### 5.1 为什么作为快速证伪线

ETF 和机构资金流的优势不是“必然有方向性 alpha”，而是：

```text
日频、数据结构简单、发布时间相对稳定；
BTC/ETH symbol mapping 简单；
可以快速建立 event table、baseline 和 cost-stressed replay；
适合低成本验证外部资金流是否提供超过 price/regime 的日频状态信息。
```

工程成本低，适合与 1.6A 并行做一个小规模 quick screen（快速筛查）。

本路线的正确定位：

```text
route_type = quick_screen
primary_question = ETF flow 是否能作为 BTC/ETH risk_appetite_regime label
not_primary_question = 今天大流入 BTC 明天是否上涨
directional_alpha_allowed = false
regime_filter_diagnostic_allowed = true
```

含义：`Stage 1.6B` 不研究“ETF flow 买卖信号”，而是研究 ETF flow 是否能作为既有或后续策略的 regime filter。例如：在 `flow_expansion` / `flow_contraction` 状态下，BTC/ETH 的波动、range、funding、basis 或已有策略表现是否有稳定差异。

第一版如果不能证明 ETF flow 在 BTC/ETH momentum、BTC regime 和同日随机基线之外仍有增量，应立即停止，不允许调阈值救结果。

### 5.2 第一版范围

```text
asset = BTC / ETH
source = 可审计的 ETF daily flow 汇总或发行方/基金披露
frequency = daily
scope = source_audit + available_at_ms_policy + minimal_daily_event_table + regime_diagnostic
timebox = 2_to_4_working_days
```

事件类型：

```text
large_single_day_inflow
large_single_day_outflow
inflow_streak
outflow_streak
flow_reversal
```

第一版只允许极端 flow 事件：

```text
flow_zscore_extreme_only = true
non_extreme_event_mixing = forbidden
directional_trade_signal = forbidden
```

### 5.3 最小关键字段

```text
flow_date
published_at_ms
available_at_ms
net_flow_usd
aum_usd
flow_to_aum_pct
flow_zscore
flow_streak_days
source_revision_status
source_revision_count
source_name
source_priority
raw_payload_hash
point_in_time_snapshot_path
data_complete_at_ms
```

时间语义硬规则：

```text
flow_date is not tradable timestamp
entry anchor must be available_at_ms
same_day_replay_forbidden unless source timestamp proves same_day_public_availability
if exact published_at_ms unavailable:
  available_at_ms = conservative_next_day_available_time
```

若 `source_revision_status`、`available_at_ms` 或 `point_in_time_snapshot_path` 无法建立，第一版只能保留 source observation，不允许 historical replay claim。

### 5.4 Replay 窗口与基线

```text
T+1d / T+3d / T+7d
BTC/ETH price momentum baseline
BTC regime baseline
macro risk-asset baseline
same-day random baseline
```

第一版输出必须拆成两类：

```text
directional_replay = diagnostic_only
regime_filter_diagnostic = primary_output
```

`regime_filter_diagnostic` 至少回答：

```text
flow_expansion / flow_contraction 下 BTC/ETH realized_vol 是否不同；
flow_expansion / flow_contraction 下 BTC/ETH forward_range 是否不同；
flow state 是否改善已有 strategy family 的 Sharpe / left_tail / drawdown；
flow state 的增量是否高于 BTC price momentum / BTC regime baseline。
```

第一版不要求接入任何执行系统，也不要求启动 live daemon。

### 5.5 快速停止条件

```text
flow effect 完全被价格动量或 BTC regime 解释；
发布时间过晚，信息已经完全进入价格；
单一 ETF 或单一极端日期主导结果；
成本后中位 excess return <= 0；
多日 streak 没有比单日 flow 提供更多信息；
source_revision_status unavailable；
available_at_ms policy missing；
point_in_time_reconstruction impossible；
partial_correlation_after_BTC_regime_and_momentum < 0.1；
regime_filter_sharpe_uplift <= 0；
single_issuer_or_GBTC_dominance > 0.40；
threshold_tuning_needed_to_pass。
```

如果首次 replay 不优于 price/regime baseline，应快速停止，不要反复修改 flow z-score 阈值救结果。

### 5.6 允许与禁止

允许：

```text
source_audit
available_at_ms_policy_design
point_in_time_snapshot_policy
minimal_daily_event_table_BTC_ETH_only
flow_zscore_extreme_event_table
replay_vs_BTC_momentum_and_regime_baseline
regime_filter_diagnostic
```

禁止：

```text
directional_trade_signal
paper_trading
live_trading
execution_engine
ETF_flow_buy_sell_rule
threshold_tuning_to_rescue_results
mixing_non_extreme_events_to_inflate_sample
using_revised_historical_data_without_revision_flag
```

第一份 design 文件建议：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6b-etf-flow-regime-diagnostic-quick-screen-design_CN.md
```

---

## 6. Stage 1.6C：Prediction Market Probability Shift

### 6.1 排名理由

Prediction market（预测市场）把宏观、监管、ETF 或价格阈值预期压缩成概率。它比普通新闻标题更结构化，也比社交情绪更容易量化。

个人投资者不研究 prediction market 搬砖，只研究：

```text
概率在 4h / 12h / 24h 发生明显变化后，
BTC/ETH 的波动、区间和风险偏好是否出现二阶变化。
```

### 6.2 主要困难

```text
contract settlement rule（结算规则）可能复杂；
低流动性合约的 probability 可能被单一订单操纵；
概率定义可能来自 last/mid/bid/ask，不同口径不可混用；
历史 probability 是否可完整回放需要先验证。
```

### 6.3 第一版范围

优先只选择：

```text
macro probability shock
crypto regulatory probability shock
ETF / institutional event probability shock
```

暂不研究大量小众政治合约或直接价格门槛搬砖。

### 6.4 必要字段

```text
platform
contract_id
contract_title
underlying_event_category
probability_before / after / delta
window_ms
market_liquidity_usd
volume_usd
available_at_ms
settlement_rule_hash
price_definition
raw_payload_hash
```

### 6.5 第一份文档

```text
2026-07-xx-external-signal-shadow-lab-stage1-6c-prediction-market-probability-shift-source-schema-settlement-design_CN.md
```

### 6.6 Kill criteria

```text
历史 probability 不可复现；
settlement rule 无法稳定审计；
大部分事件由低流动性操纵产生；
不优于宏观日历、options IV 或 BTC regime baseline；
概率变化和 crypto 的关系只体现在同一时刻，无后续二阶结构。
```

---

# 第二梯队：机制较强，但 source audit 是主要风险

## 7. Stage 1.6D：Scheduled Token Unlock / Emission

### 7.1 排名理由

Token unlock 对个人投资者的时间尺度友好，通常提前排期，不需要低延迟。但它最大的风险不是执行，而是 hindsight bias（事后偏差）：今天看到的历史 calendar 可能已经被修改，不能证明当时市场可见相同内容。

### 7.2 Alpha 机制

```text
供给增加；
潜在卖压 overhang；
团队/投资人/生态接收方差异；
市场提前定价与利空落地；
低流动性资产对 unlock/volume/depth 比例更敏感。
```

必须明确：

```text
unlocked != immediately sold
```

### 7.3 第一阶段只做 source audit

```text
source_published_at_ms 是否存在；
历史 schedule 是否有版本记录；
unlock amount 是否可能事后修订；
available_at_ms 是否可保守构建；
recipient_type 是否可靠；
多来源是否一致；
是否可保存原始页面或 API payload hash。
```

### 7.4 关键强度指标

```text
unlock_float_pct
unlock_total_supply_pct
unlock_to_30d_volume_ratio
unlock_to_depth_ratio
recipient_type
schedule_confidence
hindsight_risk_level
```

### 7.5 Replay 窗口

```text
T-14d -> T-7d
T-7d -> T-1d
T-1d -> T+1d
T+1d -> T+7d
```

### 7.6 Kill criteria

```text
历史 schedule 无版本；
available_at_ms 只能使用今天看到的页面倒推；
第三方数据大量修订且无审计轨迹；
解锁结果完全被 price momentum 或 liquidity bucket 解释；
结果只由少数低流动性 token 贡献。
```

---

## 8. Stage 1.6E：Margin / Borrow Enablement

### 8.1 排名理由

这类事件的理论机制强，而且可以复用交易所官方公告，但产品字段分散、方向不稳定、真实借币库存不可见，因此排在 unlock 之后。

### 8.2 第一版只选一个产品族

建议优先：

```text
Binance margin base-asset borrow_enablement only
```

备选：

```text
Binance futures leverage_enablement only
```

禁止把 margin、borrow、collateral 和 futures leverage 混成一个 event type。

### 8.3 可能的结构变化

```text
base asset borrow enabled -> shortability shock
quote asset borrow enabled -> leverage-long access
both sides enabled -> volatility/liquidity diagnostic
leverage increase -> OI/liquidation-risk diagnostic
```

### 8.4 第一版不得假设

```text
borrow enabled 就一定有库存；
用户账户一定有权限；
VIP borrow rate 可获得；
公告后可以立即借币开空；
方向一定是下跌或上涨。
```

### 8.5 Kill criteria

```text
product_scope 无法稳定解析；
base/quote borrow side 无法区分；
effective_time 缺失；
方向在不同事件中完全不稳定；
只有真实 borrow inventory 才能成立；
4h/12h/24h 结构变化不优于普通 volume/OI baseline。
```

---

## 9. Stage 1.6F：Stablecoin / Exchange Flow Shock

### 9.1 研究价值

链上流向可能代表：

```text
stablecoin 流入交易所 -> 潜在购买力；
BTC/ETH/token 流入交易所 -> 潜在卖压；
多交易所同步流向 -> 更高可信度的资金状态变化。
```

这条线的信息上限高，但地址标签质量是核心风险。

### 9.2 第一阶段必须解决

```text
热钱包、冷钱包、内部转账如何区分；
交易所内部归集如何剔除；
多链 USDT/USDC 如何统一；
block_time 与 indexer_seen_time 哪个作为 available_at_ms；
单一 whale transaction 是否会污染 z-score；
历史地址标签是否可复现。
```

### 9.3 第一版范围

建议只做：

```text
USDT/USDC aggregate exchange inflow shock
BTC/ETH aggregate exchange inflow shock
```

不要第一版就扩展到所有 token 和所有链。

### 9.4 Kill criteria

```text
address-label source 不可审计；
内部转账无法稳定排除；
历史 flow 无法复现；
flow shock 不优于 volume/price baseline；
结果只来自单笔 whale deposit；
需要昂贵 vendor 才能维持最小历史覆盖。
```

---

# 第三梯队：信息上限高，但噪声、语义或样本效率较差

## 10. Stage 1.6G：Sentiment / Narrative Attention Spike

### 10.1 为什么不应过早投入

情绪和叙事看起来最接近“热点 alpha”，但实际最容易出现：

```text
bot/spam 污染；
ticker 歧义；
帖子删除或编辑；
历史 API 覆盖不足；
供应商分数不可解释；
meme 极端事件主导收益；
价格和成交量已经包含同样信息。
```

如果 source audit 不强，后续所有统计都可能是伪信号。

### 10.2 第一版建议

不要同时接 X、Reddit、Telegram、Discord 和 TikTok。先选择一个可保存历史、可定义 available_at_ms、可估计独立作者数的平台或 vendor。

建议研究对象：

```text
mention_count_zscore spike
sentiment extreme
narrative attention rotation
cross-platform confirmation（仅在单源通过后）
```

### 10.3 必须加入

```text
unique_author_count
bot_suspected_ratio
source_confidence
ticker_ambiguity_status
narrative_tag
raw_payload_hash
```

### 10.4 Alpha 验证必须击败

```text
price momentum baseline
volume spike baseline
same-symbol random baseline
BTC regime baseline
```

如果不能击败 price/volume baseline，就没有必要继续扩大平台数量。

### 10.5 Kill criteria

```text
bot_suspected_ratio 无法估计；
symbol mapping pass rate < 95%；
历史数据大量缺失或不可复现；
事件数虽多但独立作者极少；
收益由少数 meme 币贡献；
跨平台确认没有增量。
```

---

## 11. Stage 1.6H：Spot Pair Addition After-First-Hour

### 11.1 当前定位

Listing family 已由 Stage 1.5 的 `futures_contract_launch` 主线部分覆盖。新路线不应重复建设 futures listing，而应只考虑：

```text
spot_listing
spot_pair_addition
margin_pair_addition
```

### 11.2 为什么优先级较低

```text
首小时机器人竞争最强；
盘口尚未稳定；
公告可能提前泄露；
不同 listing 类型机制差异巨大；
新币营销和做市安排容易主导结果。
```

个人投资者只保留：

```text
after-first-hour attention drift
新增 quote pair 后的流动性迁移
已有 futures 市场时的 spot listing 二阶反应
```

### 11.3 Hard veto

```text
first_hour_no_trade_veto
listing_family_missing_veto
trading_start_time_missing_veto
available_at_veto
asset_quality_veto
liquidity_depth_veto
```

### 11.4 Kill criteria

```text
T+1h 后无稳定结构；
表现完全由开盘跳空贡献；
不同 listing family 必须混合后才有结果；
收益集中在单一 meme/launchpad 样本；
live depth 无法支持 500 USDT proxy。
```

---

## 12. Stage 1.6I：Governance / Protocol / Tokenomics Events

### 12.1 研究价值

这类事件可能改变：

```text
token cash-flow/value-capture 预期；
emission 与未来供应；
treasury sell pressure；
staking 解锁和流通供应；
协议升级、TVL 和开发者活动；
治理失败或攻击风险。
```

它适合日频或多日研究，但语义复杂、事件低频、协议差异大。

### 12.2 第一版范围

只选一个 subtype，例如：

```text
fee_switch_passed
或
emission_reduction_executed
```

不要把 proposal draft、投票通过和链上执行混成同一事件。

### 12.3 必须区分的锚点

```text
available_at_ms
vote_start_ms
vote_end_ms
execution_time_ms
```

### 12.4 Kill criteria

```text
proposal status 无法追踪；
execution_time 不明确；
语义分类准确率不足；
样本数太少；
结果由单一协议贡献；
不优于 sector basket baseline。
```

---

# 风险旁路线：不以方向性收益为第一目标

## 13. Stage 1.6R：Security Incident / Exploit / Depeg

### 13.1 正确定位

```text
primary_use = risk veto / contagion diagnostic / avoid-list
secondary_use = low-frequency post-incident research
not_primary_use = first-reaction short / catching falling knives
```

事件包括：

```text
protocol exploit
bridge hack
oracle failure
stablecoin depeg
chain halt
exchange/custodian incident
governance attack
```

### 13.2 为什么不放入 Alpha 主队列

```text
第一反应通常过快；
价格跳空和流动性真空明显；
false alarm 和损失金额修订频繁；
提现、链上拥堵和交易通道可能失效；
尾部风险高，不符合资本保全优先。
```

### 13.3 第一版输出

```text
confirmed_status
severity
contagion_scope
affected_assets
source_confidence
avoidance_window
risk_veto_active
```

不得输出：

```text
short instruction
buy-the-dip instruction
position size
execution feasibility
```

### 13.4 Kill / downgrade criteria

如果第一波反应全部在秒级完成，或 source false-alarm rate 过高，则保留为 veto，不再研究方向性 alpha。

---

## 14. 统一 Source Audit 门槛

任何路线进入 minimal event table 前，必须至少满足：

```text
historical_events_found >= 30
event_days >= 10
symbols_with_events >= 3
source_integrity_pass_rate >= 0.95
symbol_mapping_pass_rate >= 0.95
event_type_classification_pass_rate >= 0.95
available_at_policy_defined = true
forbidden_payload_count = 0
hindsight_risk_level != high
```

对单一宏观资产事件，例如 ETF flow / prediction market，`symbols_with_events >= 3` 可能不适用。此时必须在 design 中显式声明：

```text
asset_scope = BTC/ETH macro event
cross_symbol_requirement_degraded = true
更严格的 event_days / regime / baseline 要求替代 symbols 门槛
```

不得静默取消样本要求。

对低频但高质量事件，例如 confirmed security incident、governance executed event、futures delisting effective event，可以在 design review 明确批准后使用降级样本规则：

```text
low_frequency_event_family_allowed = true
min_event_count_degraded = 10
subtype_mixing_for_sample_size = forbidden
stronger_manual_audit_required = true
stronger_baseline_required = true
alpha_claim_allowed = false
paper_live_allowed = false
```

降级样本规则只允许继续做 source audit / diagnostic replay，不允许得出 event-family alpha 结论。

---

## 15. 统一 Replay 规范

### 15.1 前置条件

```text
source audit passed
minimal event table completed
available_at_ms defined
event_type not mixed
symbol mapping passed
hindsight risk controlled
forbidden payload count = 0
```

### 15.2 时间窗口

低频事件默认：

```text
entry delay: 1h / 4h / 12h
holding horizon: 1h / 4h / 12h / 24h
```

日频或慢变量事件：

```text
T+1d / T+3d / T+7d / T+14d
```

禁止第一版使用：

```text
0s / 10s / 1min / 5min
```

### 15.3 成本压力

```text
30 bps
50 bps
80 bps
```

### 15.4 Baseline

至少选择与事件机制匹配的基线：

```text
same-symbol random baseline
same-day random baseline
BTC regime baseline
price momentum baseline
volume spike baseline
sector basket baseline
macro calendar baseline
```

### 15.5 最低 replay pass 门槛

```text
event_count >= 30
event_days >= 10
median_net_return_after_50bps >= 30
baseline_excess_net_bps >= 20
price_or_sector_baseline_excess_net_bps >= 20
stress_80bps_median_net_bps >= 0
bootstrap_ci_lower_net_bps > 0
hit_rate_vs_baseline > 0.55
left_tail_p05 not worse than random baseline
top_5_positive_events_gross_profit_share <= 0.40
max_single_day_event_share <= 0.30
max_single_symbol_event_share <= 0.60
```

说明：`median_net_return_after_50bps > 0` 只能作为 early diagnostic，不足以作为 replay pass。正式 replay pass 必须证明在 50 bps 成本底线、80 bps stress cost、baseline 和左尾风险下仍有可复核优势。

建议额外输出：

```text
forward_return by horizon
MFE / MAE
median / trimmed mean
left_tail_p05
hit rate vs baseline
bootstrap confidence interval
sample concentration by day/symbol/source subtype
```

---

## 16. 快速发现 Alpha 的执行策略

“快速”应指快速完成证伪，不是快速进入交易。

建议采用以下工作节奏：

### 16.1 主线 + quick screen 并行

```text
主线：Stage 1.6A futures delisting，复用官方公告管线，建立 futures-only 高质量事件源。
quick screen：Stage 1.6B ETF flow，用低工程成本快速验证外部资金流是否能作为 BTC/ETH risk appetite regime label。
```

### 16.2 每条路线只允许一个最小问题

例如：

```text
futures delisting：source/schema/effective-time/settlement-time/non-reduce-only-time 是否可审计？
ETF flow：极端 flow/streak 是否优于 BTC regime + momentum baseline？
prediction market：高流动性宏观 probability shock 是否预测后续波动？
unlock：历史 schedule 是否能避免 hindsight bias？
```

不得一开始同时做多个产品族、多个平台和多个方向假设。

### 16.3 先用 cheap kill criteria

在大量工程投入前，先检查：

```text
样本数量和时间跨度；
available_at_ms；
source revision / hindsight risk；
是否明显只在首小时有效；
是否已经被 price/volume baseline 解释；
是否依赖个人无法获得的执行条件。
```

### 16.4 不救失败结果

如果事件源不通过，应执行：

```text
stop_this_event_source
observation_only
risk_veto_only
或缩窄 event subtype 后重新 source audit
```

禁止：

```text
无限调阈值；
混入更多 event type 稀释失败；
删除不利样本；
把 close-price replay 包装成 execution feasibility；
用单一极端事件证明策略成立。
```

---

## 17. 推荐阶段路线图

```text
Stage 1.6A
  Futures Delisting Notice Source / Schema / Effective-Time Audit

Stage 1.6B
  ETF Flow Regime Diagnostic Quick Screen

Stage 1.6C
  Prediction Market Probability Shift Source / Schema / Settlement Audit

Stage 1.6D
  Token Unlock Calendar Source / Version / Available-Time Audit

Stage 1.6E
  Margin Base-Asset Borrow Enablement Source Audit

Stage 1.6F
  Stablecoin / Exchange Flow Address-Label Source Audit

Stage 1.6G
  Sentiment / Narrative Source Selection And Bot/Noise Audit

Stage 1.6H
  Spot Pair Addition After-First-Hour Source Audit

Stage 1.6I
  Governance / Tokenomics Single-Subtype Source Audit

Stage 1.6R
  Security Incident Confirmed-Event Risk-Veto Source Audit
```

每个 Stage 都必须单独经过：

```text
design review
-> implementation plan review
-> implementation
-> hard verification
```

默认允许动作：

```text
allowed_next_action = write_source_schema_design_only
implementation_plan_allowed = false
implementation_allowed = false
replay_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

只有当对应 Stage 的 source/schema/available_at review 明确通过后，才允许进入 replay implementation plan。路线总纲本身不授权任何实现。

---

## 18. 当前立即建议

最优先编写：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md
```

同时可以启动一个严格限时的 quick screen design：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6b-etf-flow-regime-diagnostic-quick-screen-design_CN.md
```

1.6B 的目标不是建立长期系统，而是在最小工程投入下回答：

```text
ETF / institutional flow 是否能作为 BTC/ETH risk_appetite_regime label，
并提供超出 BTC/ETH momentum、BTC regime 和同日随机基线的增量信息？
```

若答案为否，应立即停止 1.6B，将资源集中到 1.6A 和 1.6C。

---

## 19. 最终边界

本路线总纲不能被解释为：

```text
alpha 已成立
某事件可以交易
可以 paper trading
可以 live trading
可以连接 execution engine
可以生成 SignalCandidate / TradeIntent
可以根据事件直接推荐买卖或仓位
```

本路线最多支持：

```text
选择下一个事件源
编写 source audit design
定义 minimal schema 与 available_at_ms
执行 historical replay 与基线比较
决定 continue / stop / observation-only / risk-veto-only
```

最终原则：

```text
优先寻找可审计、可证伪、适合个人投资者的慢速信息优势；
先快速淘汰伪 alpha，再把工程资源集中到真正具有增量证据的事件源。
```
