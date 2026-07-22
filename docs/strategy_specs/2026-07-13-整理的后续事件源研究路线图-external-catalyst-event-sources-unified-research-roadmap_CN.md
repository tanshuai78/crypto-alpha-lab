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
Stage 1.6D  Scheduled Unlock / Emission Source-Version Diagnostic（audit-first reserve）
Stage 1.6E  Margin / Borrow Enablement Auxiliary Diagnostic（delayed）
Stage 1.6F  Daily Exchange Flow Regime Diagnostic
Stage 1.6G  Sentiment / Narrative Regime Journal（F&G + Google Trends only）
Stage 1.6H  Listing Event Optional Observation / Discipline Track
Stage 1.6I  Governance / Tokenomics Fundamental Reading Track
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
| 4 | `scheduled_unlock / emission source-version diagnostic` | 中低 | 中低 | 中高 | 中 | point-in-time calendar 可验证性、recipient/onchain supply overhang 诊断 | source/version/available-time/recipient-contract audit |
| 5 | `margin / borrow enablement auxiliary diagnostic` | 低中 | 中高 | 中高 | 中 | leverage shock veto、funding/OI regime 诊断 | 仅在 Extreme Funding 稳定运行后做 base_borrow_enablement schema audit |
| 6 | `daily exchange flow regime diagnostic` | 中 | 中低 | 中高 | 中 | BTC exchange net position、日频资金状态 regime label | BTC exchange net position source/label audit |
| 7 | `sentiment / narrative regime journal` | 低中 | 中 | 低 | 高 | F&G vol regime、自我情绪校准、Google Trends 叙事冷热标签 | F&G + Google Trends low-cost journal design |
| 8 | `listing event optional observation / discipline track` | 低 | 高 | 低中 | 低中 | first_hour_no_trade discipline、少量 basis/volume split 观察 | optional listing classification / discipline checklist |
| 9 | `governance / tokenomics fundamental reading track` | 低 | 中 | 低 | 中 | 协议机制理解、治理风险认知、token value-capture 背景 | quarterly blue-chip protocol governance reading |
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

## 7. Stage 1.6D：Scheduled Unlock / Emission Source-Version Diagnostic

### 7.1 排名理由

Token unlock / emission 对个人投资者的时间尺度友好，通常提前排期，不需要低延迟。但它不应被理解为“解锁前做空”的 alpha 路线。

本路线当前定位调整为：

```text
route_type = audit_first_reserve
primary_goal = source_version_available_time_recipient_contract_audit
secondary_goal = supply_overhang_regime_diagnostic
directional_short_alpha_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

调整理由：

```text
unlocked tokens != tokens sold
scheduled unlock is widely known and often priced before the visible event window
recipient behavior is heterogeneous and cannot be inferred from calendar size alone
calendar history may be revised, delayed, cancelled, or backfilled
small-cap unlocks that show visible impact are often not executable after realistic liquidity/friction checks
```

因此，Stage 1.6D 的第一目标不是证明“解锁会跌”，而是先证明：

```text
1. 当时市场是否真的能看到这条 unlock/emission 信息；
2. 这条信息在历史中是否可 point-in-time 复现；
3. 解锁接收方和链上合约是否可审计；
4. 解锁后是否真的产生 transfer_to_exchange / sell-pressure proxy；
5. 该 supply overhang 是否能作为其他策略的 regime filter。
```

如果上述 source audit 失败，本路线应立即停止，不进入 replay。

### 7.2 机制假设与不可成立的原始路线

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
unlock calendar visible today != unlock calendar visible at historical decision time
calendar-only replay != valid alpha evidence
directional_short_on_unlock_day = forbidden
```

原始路线不成立：

```text
解锁日前一周做空；
解锁当天或解锁后固定窗口平仓；
使用今天看到的 TokenUnlocks / Cryptorank / Messari 历史 calendar 直接回测；
混合 VC / team / ecosystem / farmer emission 事件；
把少数小市值低流动性 token 的下跌当成事件家族证据。
```

原因：

```text
VC/team 可以提前 OTC、hedge、延期或分散卖出；
项目方可以用延期、回购、销毁、做市激励对抗空头；
真实冲击大的 token 往往 liquidity/depth 太差，close-price replay 不可执行；
历史 calendar 缺少版本记录时，回测 anchor 可能是事后修订时间。
```

### 7.3 第一阶段只做 source audit

```text
source_published_at_ms 是否存在；
历史 schedule 是否有版本记录；
unlock amount 是否可能事后修订；
available_at_ms 是否可保守构建；
recipient_type 是否可靠；
vesting_contract_address 是否可链上验证；
recipient_address / beneficiary_address 是否可审计；
unlock_cancelled_or_delayed 是否有 revision trail；
多来源是否一致；
是否可保存原始页面或 API payload hash。
```

第一阶段允许：

```text
point_in_time_calendar_audit；
source_version_history_audit；
available_at_ms_policy_design；
vesting_contract_address_verification；
recipient_type_classification；
onchain_transfer_to_exchange_diagnostic_design；
supply_overhang_regime_label_design。
```

第一阶段禁止：

```text
pre_unlock_short_replay；
unlock_day_short_signal；
calendar_only_backtest；
CT_tweet_driven_target_selection；
small_cap_altcoin_replay；
paper_trading / live_trading / execution_engine。
```

### 7.4 关键强度指标

```text
unlock_float_pct
unlock_total_supply_pct
unlock_to_30d_volume_ratio
unlock_to_depth_ratio
recipient_type
recipient_type_confidence
vesting_contract_address_verified
vesting_contract_address_coverage_ratio
transfer_to_exchange_amount
transfer_to_exchange_ratio
recipient_to_exchange_latency_ms
source_version_history_available
calendar_revision_count
calendar_revision_status
schedule_confidence
hindsight_risk_level
```

### 7.5 Replay 前置条件与窗口

```text
replay_allowed only if source audit passed
point_in_time_calendar_verified = true
available_at_ms_policy_defined = true
recipient_type_classification_available = true
vesting_contract_address_coverage_ratio >= 0.80
valid_audited_event_count >= 30
calendar_revision_trail_preserved = true
```

通过前置条件后，replay 也只能做 diagnostic，不做交易信号：

```text
T-14d -> T-7d：提前定价诊断
T-7d -> T-1d：pre-event supply overhang / liquidity diagnostic
T-1d -> T+1d：event-window chain transfer / exchange inflow diagnostic
T+1d -> T+7d：post-event absorption / reversal diagnostic
```

Replay 输出必须同时对比：

```text
BTC/ETH regime baseline
price_momentum baseline
liquidity_bucket baseline
market_cap_bucket baseline
recipient_type bucket
```

禁止把 replay 正收益解释为 execution feasibility 或独立 alpha。

### 7.6 第一版范围

```text
scope = audit_only_until_source_version_passes
preferred_assets = high_liquidity_major_ecosystem_tokens_only
min_float_market_cap_usd = 200_000_000
small_cap_altcoin_replay_allowed = false
recipient_type_mixing_allowed = false
directional_price_claim_allowed = false
```

不建议第一版写成 “BTC/ETH ecosystem only” 的原因：

```text
BTC 没有传统 token unlock；
ETH staking/emission 和 VC/team unlock 不是同一机制；
过窄范围可能样本不足，过宽范围又会混入低质量山寨事件。
```

更稳妥的第一版是：

```text
只筛选高流动性、vesting contract 可验证、recipient_type 可分类、calendar point-in-time 可复现的事件。
```

### 7.7 Kill criteria

```text
主数据源没有 point-in-time 历史版本；
available_at_ms 只能使用今天看到的页面倒推；
第三方数据大量修订且无审计轨迹；
vesting_contract_address_coverage_ratio < 0.80；
recipient_type_unknown_ratio > 0.30；
valid_audited_event_count < 30；
无法区分 team / VC / ecosystem / farmer emission；
无法审计 transfer_to_exchange 行为；
解锁结果完全被 BTC/ETH regime、price momentum、liquidity bucket 或 market_cap bucket 解释；
结果只由少数低流动性 token 贡献；
需要参考 CT/KOL 解锁预警才能找到目标。
```

### 7.8 客观结论

```text
stage1_6d_status = conditional_research_candidate
priority = behind_stage1_6a_and_stage1_6b
budget = small_timeboxed_source_audit_only
expected_value = medium_if_source_audit_passes_else_zero
independent_alpha_expectation = low
regime_filter_value = possible_but_unproven
```

具体建议：

```text
先投入 2-3 天做 source/version/available-time audit；
如果 calendar point-in-time 无法复现，立即停止；
如果 audit 通过，再写 Stage 1.6D design；
不得直接进入 price replay；
不得把 unlock calendar 当成做空清单。
```

第一份文档建议：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6d-scheduled-unlock-source-version-recipient-contract-audit-design_CN.md
```

---

## 8. Stage 1.6E：Margin / Borrow Enablement Auxiliary Diagnostic

### 8.1 排名理由

这类事件可以复用交易所官方公告，数据可获得性高，但不适合作为独立 alpha 路线。它的真实价值只在于辅助已有策略识别 leverage access shock，尤其是给 `Extreme Funding` 策略提供 veto / regime filter。

当前定位：

```text
route_type = delayed_auxiliary_diagnostic
independent_alpha_expectation = very_low
primary_value = extreme_funding_leverage_shock_veto
secondary_value = OI_funding_spread_volume_regime_diagnostic
actual_borrow_short_execution_allowed = false
directional_trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

调整理由：

```text
margin / borrow enablement is a two-sided access shock, not a one-direction signal
base asset borrow enabled may increase shortability
quote asset borrow enabled may increase leverage-long access
margin pair addition does not imply borrow inventory availability
borrow inventory / utilization / historical borrow rate are not publicly auditable
first-hour reaction belongs to latency competition and remains blocked by first_hour_no_trade_veto
```

因此，如果 `Extreme Funding` 策略没有稳定运行，1.6E 暂时没有足够研究价值；它不应抢占 1.6A、1.6B 或 Stage 1.5 live evidence 的资源。

### 8.2 不成立的原始路线

禁止把 1.6E 理解为：

```text
新增 margin / borrow -> 立刻买入；
base borrow enabled -> 立刻做空；
quote borrow enabled -> 立刻做多；
公告后首小时追单；
用合约做空替代真实 borrow 并声称验证了 borrow alpha；
把所有 margin / borrow / leverage 公告混合 replay。
```

原因：

```text
机构和 API 用户在公告后首分钟内完成主要反应；
散户可见窗口通常已经是二阶残余；
真实 borrow availability 不可见，历史 replay 会系统性低估借币成本；
borrow rate 可能在有价值事件中快速跳升，最需要做空时反而最借不到；
不同产品类型的方向机制相反，混合后统计结论不可解释。
```

### 8.3 第一版只选一个产品族

建议优先：

```text
Binance margin base-asset borrow_enablement only
```

备选：

```text
Binance futures leverage_enablement only
```

禁止把 margin、borrow、collateral 和 futures leverage 混成一个 event type。

第一版只有在下列条件满足时才启动：

```text
extreme_funding_strategy_active = true
event_type_classification_schema_reviewed = true
base_quote_borrow_side_separable = true
effective_time_policy_defined = true
diagnostic_only = true
```

### 8.4 可能的结构变化

```text
base asset borrow enabled -> shortability shock
quote asset borrow enabled -> leverage-long access
both sides enabled -> volatility/liquidity diagnostic
leverage increase -> OI/liquidation-risk diagnostic
```

这些结构变化只能作为 diagnostic，不允许直接转成方向信号。

### 8.5 第一版不得假设

```text
borrow enabled 就一定有库存；
用户账户一定有权限；
VIP borrow rate 可获得；
公告后可以立即借币开空；
方向一定是下跌或上涨。
```

还必须明确：

```text
borrow_inventory_visible = false
historical_borrow_utilization_available = false
borrow_rate_replay_trusted = false unless source_audit_proves_otherwise
actual_borrow_execution_claim_allowed = false
```

### 8.6 允许的诊断输出

```text
T+4h OI change
T+12h OI change
T+24h OI change
T+4h funding_rate change
T+12h funding_rate change
T+24h funding_rate change
spread_bps change
volume change
depth change
leverage_shock_veto_candidate
funding_persistence_degradation_candidate
```

窗口从 `T+4h` 起步，原因是：

```text
首小时属于速度竞争区；
T+1h~T+4h 仍可能是做市商库存重定价；
本项目第一版不研究首小时执行；
1.6E 的目标是 regime diagnostic，不是公告瞬时交易。
```

### 8.7 必要 schema 字段

```text
event_type
affected_asset
affected_quote
borrow_side
margin_mode
effective_time_ms
available_at_ms
source_article_id
source_detail_url_normalized
announcement_language
raw_payload_hash
classification_confidence
manual_review_required
```

`event_type` 第一版只允许：

```text
base_borrow_enablement
```

其他类型必须记录但不进入 replay：

```text
margin_pair_addition
quote_borrow_enablement
leverage_adjustment
cross_margin_support
isolated_margin_support
borrow_suspension
margin_delisting
```

### 8.8 Kill criteria

```text
product_scope 无法稳定解析；
base/quote borrow side 无法区分；
effective_time 缺失；
event_type_classification_accuracy < 0.90；
base_borrow_enablement top_liquidity_assets 历史样本 < 15；
T+4h / T+12h OI 或 funding 变化不优于 baseline；
结果完全被 BTC regime、spot volume 或 market-wide volatility baseline 解释；
只有真实 borrow inventory 才能成立；
方向在不同事件中完全不稳定；
任何结论需要假设散户可以稳定借到币。
```

### 8.9 客观结论

```text
stage1_6e_status = delayed_auxiliary_diagnostic
priority = after_extreme_funding_strategy_has_stable_observation
independent_alpha_expectation = very_low
strategy_support_value = possible
first_action = margin_borrow_event_type_schema_design
implementation_allowed = false
```

具体建议：

```text
不要现在投入大工程；
等 Extreme Funding 重新进入稳定观察或有足够 funding/OI 数据后再启动；
第一份设计只写 base_borrow_enablement schema / source audit；
不得写 borrow execution plan；
不得写 directional replay plan。
```

第一份文档建议：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6e-margin-borrow-enablement-schema-source-audit-design_CN.md
```

---

## 9. Stage 1.6F：Daily Exchange Flow Regime Diagnostic

### 9.1 研究价值

链上资金流数据的信息上限高，但个人投资者能可靠触达的上限很低。本路线不应被理解为“USDT 流入交易所就买 BTC”或“BTC 流入交易所就卖”的实时信号，而应降级为日频资金状态诊断。

当前定位：

```text
route_type = daily_regime_diagnostic
primary_goal = BTC_exchange_net_position_daily_source_audit
secondary_goal = USDT_USDC_aggregate_exchange_inflow_zscore_after_source_audit
frequency = daily
directional_trade_signal_allowed = false
real_time_whale_alert_trigger_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

调整理由：

```text
stablecoin exchange inflow != confirmed buy demand
BTC exchange outflow != guaranteed bullish holding signal
onchain raw transfers are true, but address labels and intent interpretation can be wrong
public data has 30-120min delay, so real-time following is stale for personal investors
single whale transfers and internal exchange movements can dominate short-window z-scores
multi-chain stablecoin flow requires address-label and available_at_ms policy that is hard to audit
```

因此，1.6F 的第一目标不是预测方向，而是回答：

```text
BTC 交易所净仓量持续下降/上升时，
是否能作为 T+14d / T+30d 的 supply regime label；
这个 label 是否能帮助 long-horizon basis / funding 策略过滤风险。
```

### 9.2 不成立的原始路线

禁止把 1.6F 理解为：

```text
USDT / USDC 流入交易所 -> 立刻做多 BTC；
BTC 流入交易所 -> 立刻做空 BTC；
BTC 流出交易所 -> 立刻做多 BTC；
Whale Alert 推送 -> 立即操作；
追踪单一 smart money / whale address；
用单链 USDT 流量代表全市场购买力；
用平台今日标签直接回测历史并声称 point-in-time 有效。
```

原因：

```text
交易所入金可能是补保证金、内部归集、跨所转账、OTC 结算或量化 margin 管理；
最大机构买盘可能通过 OTC 完成，不经过可见稳定币入金路径；
地址标签会滞后、误标、回填和修订；
FTX 等极端事件说明 exchange outflow 可能是 solvency risk，不是利好；
实时链上推送会制造 FOMO，但散户看到时通常已经是旧数据。
```

### 9.3 第一阶段必须解决

```text
热钱包、冷钱包、内部转账如何区分；
交易所内部归集如何剔除；
多链 USDT/USDC 如何统一；
block_time 与 indexer_seen_time 哪个作为 available_at_ms；
单一 whale transaction 是否会污染 z-score；
历史地址标签是否可复现。
```

第一阶段必须显式输出：

```text
address_label_source
address_label_revision_risk
point_in_time_label_available
internal_transfer_filter_available
exchange_solvency_risk_flag_policy
available_at_ms_policy
data_missing_ratio
single_whale_dominance_ratio
```

如果无法审计 point-in-time 标签，第一版仍可继续做 degraded research，但必须写明：

```text
label_quality_assumption = accept_platform_labels
evidence_level = degraded_public_api_regime_diagnostic
directional_claim_allowed = false
```

### 9.4 第一版范围

优先只做：

```text
BTC_exchange_net_position_daily
```

原因：

```text
BTC exchange address labels are usually more stable than multi-chain stablecoin labels
BTC exchange net position is a medium-term supply metric, not a real-time trigger
single-chain / multi-chain USDT coverage risk can be deferred
engineering scope is smaller and failure exits cleaner
```

第二步才允许评估：

```text
USDT_USDC_aggregate_exchange_inflow_zscore_daily
```

但前提是：

```text
multi_chain_available_at_ms_policy_defined = true
address_label_revision_risk_reported = true
internal_transfer_filter_available = true
coverage_limitation_documented = true
```

### 9.5 Replay / diagnostic 窗口

```text
frequency = daily
available_at_ms = platform_published_at_ms + 2h_buffer
windows = T+7d / T+14d / T+30d
T+1d / T+3d short_window_allowed = false
```

输出只能是 regime diagnostic：

```text
exchange_supply_regime_label
stablecoin_liquidity_regime_label
realized_vol_distribution
return_distribution_vs_baseline
funding_or_basis_filter_candidate
```

必须对比：

```text
BTC price momentum baseline
BTC realized volatility baseline
market-wide risk regime baseline
ETF flow regime baseline
```

### 9.6 明确禁止

```text
real_time_whale_alert_trigger
single_whale_address_tracking
smart_money_address_following
directional_trade_signal
treating_inflow_as_confirmed_buy_demand
treating_outflow_as_confirmed_holding
paper_trading / live_trading / execution_engine
```

### 9.7 Kill criteria

```text
historical_missing_ratio > 0.20；
address_label_revision_known_bad_ratio > 0.15；
内部转账无法稳定排除且显著影响主指标；
BTC_exchange_net_position 被 BTC price momentum 完全解释；
T+14d / T+30d distribution 无显著差异；
结果由单笔 whale transfer 主导；
无法定义保守 available_at_ms；
必须依赖昂贵 vendor 或自建多链地址标签系统才能成立；
研究结果诱导 real-time whale alert 操作。
```

### 9.8 客观结论

```text
stage1_6f_status = conditional_high_information_ceiling_regime_diagnostic
priority = after_stage1_6a_and_stage1_6b_source_audit
first_action = BTC_exchange_net_position_daily_source_label_audit
information_ceiling = high
personal_investor_reachable_ceiling = low_to_medium
implementation_allowed = false
```

具体建议：

```text
第一步只做 BTC exchange net position 日频 source audit；
不要先做多链 stablecoin flow；
不要订阅 Whale Alert 作为研究触发器；
如果 BTC exchange net position 对 T+14d / T+30d 没有增量，停止；
只有低成本版本有效后，才考虑 USDT/USDC aggregate flow。
```

第一份文档建议：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6f-btc-exchange-net-position-daily-source-label-audit-design_CN.md
```

---

# 第三梯队：信息上限高，但噪声、语义或样本效率较差

## 10. Stage 1.6G：Sentiment / Narrative Regime Journal

### 10.1 为什么不应过早投入

完整版情绪路线看起来最接近“热点 alpha”，但实际是散户最容易被对手盘设计收割的路线。`Social Volume spike -> buy` 和 `Fear & Greed < 20 -> buy` 都不能作为方向交易信号。

当前定位：

```text
route_type = low_cost_regime_journal
primary_goal = Fear_and_Greed_volatility_regime_diagnostic
secondary_goal = Google_Trends_narrative_rotation_label
asset_scope = BTC_ETH_only
directional_trade_signal_allowed = false
social_volume_direct_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

调整理由：

```text
Social Volume is often price-driven, not price-leading
sentiment spike can be manufactured by KOL / bot / incentive campaigns
Fear & Greed includes price / volatility / momentum components and is naturally lagged
altcoin ticker mapping and bot filtering are not reliable enough for first-version replay
Twitter/X algorithm changes create structural breaks in historical social time series
researcher is also part of the emotional crowd being studied
```

因此，Stage 1.6G 的第一版不是情绪交易，也不是 social alpha，而是：

```text
用 Fear & Greed 记录 BTC/ETH 情绪极值；
用 Google Trends 记录叙事冷热；
验证这些低成本指标是否对 realized vol、MAE、OI/volume regime 有辅助解释力；
同时把它作为个人研究者的情绪校准日志。
```

### 10.2 不成立的原始路线

禁止把 1.6G 理解为：

```text
Social Volume spike -> 立刻买入；
Fear & Greed < 20 -> 立刻抄底；
Fear & Greed > 85 -> 立刻做空；
LunarCrush trending asset -> 买入；
Santiment social metric -> 方向信号；
情绪 spike 后反向做空；
KOL / Telegram / Discord 热度 -> 交易触发器。
```

原因：

```text
情绪 spike 可能只是价格上涨后的反应；
真实领先叙事、价格滞后情绪、操纵情绪在实时中很难区分；
Social Volume 的有效反应窗口通常在量化/机器人区域；
山寨币情绪 spike 常伴随低流动性与做庄出货；
反向做空情绪 spike 也可能成为对手盘设计的一部分；
F&G 极度恐惧在 LUNA / FTX 类事件中可能持续数周，不是自动底部。
```

### 10.3 第一版范围

```text
allowed_sources:
  Fear_and_Greed_Index（daily, alternative.me）
  Google_Trends（weekly, narrative keyword relative interest）

forbidden_sources_first_version:
  LunarCrush_Social_Volume
  Santiment_social_metrics
  X/Twitter raw posts
  Reddit / Telegram / Discord / TikTok
  KOL ranking / trending asset lists
```

第一版研究对象：

```text
F&G < 15 / F&G > 85 extreme zones
F&G extreme duration_days
BTC_ETH_realized_vol_T+7d / T+14d
existing_strategy_MAE_under_FG_extreme
Google_Trends narrative_rotation_label
Google_Trends weekly trend change
OI / volume change for representative BTC/ETH-related assets
```

### 10.4 允许的诊断输出

```text
volatility_regime_label
narrative_rotation_label
MAE_risk_context
position_sizing_context_for_existing_strategies
combined_regime_context_with_1_6B_and_1_6F
researcher_emotion_journal_reference
```

这些输出只能作为 regime/context，不允许转成买卖建议。

### 10.5 必须对比的 baseline

```text
BTC price momentum baseline
BTC realized volatility baseline
same-calendar-date random baseline
ETF flow regime baseline
exchange flow regime baseline
existing_strategy_MAE_baseline
```

如果 F&G / Google Trends 不能提供增量解释，不扩大到社交平台。

### 10.6 研究纪律规则

```text
no_same_day_trade_due_to_FG = true
no_same_week_trade_due_to_Google_Trends = true
no_push_notification_source = true
no_trending_asset_page = true
output_has_no_buy_sell_column = true
researcher_action_log_required = true
```

如果出现“因为 F&G 或 Trends 数据直接下单”的记录，本路线必须重置为 observation-only journal，不再做 alpha 解释。

### 10.7 Kill criteria

```text
F&G 极值后 T+7d / T+14d realized vol 分布无统计差异；
F&G 对 existing_strategy_MAE 无增量；
Google Trends narrative_rotation_label 与 OI / volume change 的 partial correlation < 0.10；
结论完全被 BTC price momentum 或 realized volatility baseline 解释；
必须接入 LunarCrush / Santiment 才能成立；
需要 altcoin sentiment tracking 才能看到效果；
研究者因 F&G / Trends 直接下单；
研究输出开始包含 buy/sell 建议。
```

### 10.8 客观结论

```text
stage1_6g_status = low_cost_parallel_regime_journal
full_social_volume_route_status = killed
priority = parallel_low_cost_maintenance
first_action = Fear_and_Greed_Google_Trends_journal_design
independent_alpha_expectation = very_low
self_calibration_value = high
implementation_allowed = false
```

具体建议：

```text
保留 F&G 每日记录；
保留 Google Trends 周频叙事热度记录；
不注册或接入 LunarCrush / Santiment；
不追踪 altcoin social spike；
不写 sentiment trade signal；
把第一版产物定义成 CSV + 统计摘要 + 情绪校准日志。
```

第一份文档建议：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6g-fear-greed-google-trends-regime-journal-design_CN.md
```

---

## 11. Stage 1.6H：Listing Event Optional Observation / Discipline Track

### 11.1 当前定位

Listing family 已由 Stage 1.5 的 `futures_contract_launch` 主线覆盖。1.6H 不应重复建设 listing alpha，也不应主动推进为新 alpha 研究线。

当前定位：

```text
stage1_6h_status = optional_observation_track
active_research_allowed = false
independent_alpha_expectation = near_zero
primary_value = execution_discipline_training
secondary_value = listing_type_classification_reference
directional_trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

调整理由：

```text
first-hour listing reaction is dominated by market makers, bots, and latency competition
cross-exchange announcement positioning is usually arbitraged before retail can act
new token first listing and Launchpad / Launchpool have severe sell-pressure and FOMO traps
after constraints, remaining valid subtypes have very small sample counts and low strategy contribution
Stage 1.5 already covers futures_contract_launch, so 1.6H would duplicate listing-family effort
```

因此，1.6H 的主要用途不是找 alpha，而是把“上新冲动”转化为执行纪律训练。

### 11.2 不成立的原始路线

禁止把 1.6H 理解为：

```text
开盘第一秒买入；
首小时内抢交易；
公告后去其他交易所提前买入；
Binance 上线后卖出套利；
Launchpad / Launchpool 上线后接盘；
新币首发 after-first-hour 做方向；
小市值 listing 追涨；
根据 CT/KOL listing 热度选币。
```

原因：

```text
首小时机器人竞争最强；
盘口尚未稳定；
公告可能提前泄露；
不同 listing 类型机制差异巨大；
新币营销和做市安排容易主导结果。
开盘价往往由做市商和项目方库存安排主导；
跨所溢价通常在公告后 5-30 分钟被套利消除；
Launchpad / Launchpool 可能形成集中配额卖压；
小市值 listing 的 close-price replay 无法代表真实 500 USDT execution。
```

### 11.3 仅保留的观察范围

只有两个极窄子类允许作为 optional observation：

```text
already_has_futures_spot_addition
  condition: mature_asset_and_market_cap_gt_1B
  output: basis_convergence_diagnostic
  window: T+1h -> T+4h

new_quote_pair_for_major_asset
  examples: BTC/USDC, ETH/USDC
  output: volume_split_and_spread_diagnostic
  window: T+1h -> T+24h
```

这些观察只能服务于：

```text
listing_type_classification_reference
depth_stabilization_observation
basis_convergence_context
volume_split_context
first_hour_no_trade_discipline_log
```

不能服务于方向交易。

### 11.4 Hard veto

```text
first_hour_no_trade_veto
listing_family_missing_veto
trading_start_time_missing_veto
available_at_veto
asset_quality_veto
liquidity_depth_veto
launchpad_launchpool_veto
new_token_first_listing_veto
market_cap_below_200m_veto
cross_exchange_announcement_arbitrage_veto
```

### 11.5 研究纪律规则

```text
48h_cooling_period_after_listing_announcement = true
no_exception_to_first_hour_no_trade_veto = true
launchpad_launchpool_marked_as_forbidden_zone = true
new_token_first_listing_marked_as_forbidden_zone = true
output_has_no_buy_sell_column = true
listing_impulse_journal_required = true
```

看到任何新币上线公告后的默认动作：

```text
do_not_trade
classify_listing_type
record_why_first_hour_is_forbidden
wait_48h_before_any_research_note
```

### 11.6 Kill criteria

```text
已有 futures 的 spot 新增事件（市值 > $1B）2 年内 < 10 个；
T+1h -> T+4h basis convergence 无统计规律；
主流 quote pair volume split 方差过大；
必须混入 Launchpad / Launchpool / new_token_first_listing 才有结果；
表现完全由开盘跳空贡献；
live depth 无法支持 500 USDT proxy；
任何人为“这次例外”破坏 first_hour_no_trade_veto；
研究输出开始包含 buy/sell 建议。
```

### 11.7 客观结论

```text
stage1_6h_status = optional_observation_track
active_research_priority = none
recommended_action = keep_as_discipline_checklist_not_alpha_route
independent_alpha_expectation = near_zero
implementation_allowed = false
```

具体建议：

```text
不主动写 1.6H implementation plan；
不与 1.6A / 1.6B / 1.6F 抢资源；
如果未来确实要写，只写 listing observation + discipline design；
把每次 listing FOMO 转化为 first_hour_no_trade 纪律记录。
```

第一份文档建议：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6h-listing-event-optional-observation-and-discipline-design_CN.md
```

---

## 12. Stage 1.6I：Governance / Tokenomics Fundamental Reading Track

### 12.1 当前定位

Governance / protocol / tokenomics 事件不适合作为主动量化 alpha 路线。它的价值主要是长期理解协议经济机制、治理风险和 token value-capture，而不是从 `vote_passed` 或 `proposal_executed` 里生成交易信号。

```text
stage1_6i_status = downgraded_fundamental_context_track
active_quant_research_allowed = false
event_replay_allowed = false
independent_alpha_expectation = near_zero
primary_value = protocol_mechanism_understanding
secondary_value = governance_risk_awareness
directional_trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

调整理由：

```text
governance information is layered, and retail usually sees the last layer
proposal_passed is often sell-the-fact, not a fresh buy signal
proposal semantics require protocol-specific manual reading
same event type can have opposite effects under different protocol states
effective value change may already be reflected in ETH beta, sector basket, or options IV
valid event count after filtering is too small for robust replay
manual review cost per event is the highest among Stage 1.6 routes
governance attacks can invert "proposal passed" into catastrophic risk
```

因此，1.6I 的合理用途是：

```text
每季度阅读 1-2 个主流协议治理论坛；
记录 tokenomics / fee switch / emission / treasury / risk parameter 变化；
积累 protocol value-capture 和 governance attack 的判断框架；
作为未来基本面背景，不作为可交易事件源。
```

### 12.2 不成立的原始路线

禁止把 1.6I 理解为：

```text
proposal_passed -> buy
governance_active -> bullish
fee_switch_passed -> immediate long
buyback_burn_execution -> repeated alpha
protocol_upgrade_confirmed -> automatic bullish
automated_LLM_governance_signal
small_DAO_governance_replay
post_vote_entry
paper_trading / live_trading / execution_engine
```

原因：

```text
核心开发者、whale voter 和活跃社区通常在散户前数周看到信息；
提案通过时，不确定性已经大幅消除，容易出现获利了结；
protocol value != token value；
治理通过 != 链上安全执行；
buyback / burn 第 N 次执行通常已被第一次公告定价；
治理攻击、恶意升级、timelock 出货窗口是真实尾部风险。
```

### 12.3 允许的背景阅读范围

```text
ETH ecosystem major upgrades
blue_chip_DeFi_protocols_only
  examples: Uniswap, Aave, Compound, MakerDAO, Curve

manual_notes_only:
  fee_switch_discussion
  buyback_burn_design
  emission_change
  treasury_allocation
  risk_parameter_change
  major_protocol_upgrade
  governance_attack_case_review
```

阅读频率：

```text
frequency = quarterly
budget = 2_to_4_hours_per_quarter
protocol_count = 1_to_2_per_quarter
output = qualitative_notes_only
```

### 12.4 如果未来强行做最小量化版

不建议当前启动。但如果未来资源充足，只允许极窄版本：

```text
scope = ETH_ecosystem_plus_blue_chip_DeFi_only
event_type = fee_switch | buyback_burn | major_protocol_upgrade
minimum_sample_per_type = 10
valid_event_count >= 20
manual_semantic_review_required = true
research_window = forum_post_date -> vote_end_date
no_post_vote_entry = true
small_DAO_excluded = true
market_cap_below_500m_excluded = true
```

必须区分时间锚点：

```text
forum_post_available_at_ms
proposal_published_at_ms
vote_start_ms
vote_end_ms
timelock_start_ms
execution_time_ms
```

但这只能是 diagnostic，不允许输出交易信号。

### 12.5 Kill criteria

```text
manual_semantic_review_cost_per_event > 1h；
valid_event_count < 20；
sample_per_event_type < 10；
proposal direction cannot be classified with confidence；
result explained by ETH beta / sector basket / options IV；
requires small DAO events to show effect；
governance_attack_risk cannot be screened；
any output says vote_passed_buy；
researcher treats forum reading as investment conviction。
```

### 12.6 客观结论

```text
stage1_6i_status = downgraded_fundamental_context_track
active_research_priority = none
recommended_action = quarterly_reading_not_quant_replay
independent_alpha_expectation = near_zero
fundamental_context_value = medium
implementation_allowed = false
```

具体建议：

```text
不写 1.6I implementation plan；
不做治理事件 replay；
不把 governance forum 阅读包装成 alpha research；
每季度选择 1-2 个主流协议，写 tokenomics / governance risk 读书笔记；
如果未来重启量化评估，必须先写单独 design 并通过 review。
```

第一份文档建议：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6i-governance-tokenomics-quarterly-fundamental-reading-guide_CN.md
```

---

# 风险旁路线：不以方向性收益为第一目标

## 13. Stage 1.6R：Confirmed Security Incident Risk-Veto / Contagion Diagnostic

### 13.1 正确定位

```text
route_type = capital_preservation_side_route
primary_use = confirmed incident risk veto / contagion diagnostic / avoid-list
secondary_use = spread-depth recovery and avoidance-window research
not_primary_use = first-reaction short / catching falling knives / exploit momentum trade
independent_alpha_expectation = near_zero
implementation_allowed = false
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

本路线的核心判断：

```text
risk_veto_route_success != alpha_success
directional_replay_failed does not invalidate risk_veto_value
primary_success_metric = confirmed_status + affected_assets + avoidance_window + false_alarm_rate
```

含义：即使 exploit / depeg / chain halt 事件不适合方向性交易，只要能稳定识别需要回避的资产、链、交易所、抵押品和时间窗口，`Stage 1.6R` 就有独立的风控价值。

### 13.2 为什么不放入 Alpha 主队列

```text
第一反应通常过快；
价格跳空和流动性真空明显；
false alarm 和损失金额修订频繁；
提现、链上拥堵和交易通道可能失效；
尾部风险高，不符合资本保全优先。
```

更直接地说：事故发生后追空通常不是 alpha，而是在信息不完整、盘口断裂、资金费率畸变、交易所风控和协议救援反弹之间赌博。攻击者、巨鲸或救援方可能已经完成对冲，后手散户追空经常变成他们的退出流动性。

### 13.3 第一版允许范围

允许：

```text
confirmed_incident_source_audit
affected_assets_mapping
venue_chain_protocol_exposure_check
risk_veto_flag
contagion_scope_map
spread_depth_recovery_time_distribution
false_alarm_tracking
post_incident_research_log
```

禁止：

```text
first_reaction_short
catching_falling_knife
exploit_directional_trade_signal
depeg_momentum_trade
unconfirmed_rumor_trigger
whale_alert_only_trigger
paper_trading
live_trading
execution_engine
```

### 13.4 触发条件

```text
official_protocol_or_exchange_confirmation = true
or credible_incident_aggregator_confirmation = true
or stablecoin_depeg_abs_pct >= 2.0 and sustained_minutes >= 120
or spread_multiple_vs_baseline >= 5.0 with multi_venue_confirmation
or tvl_drawdown_with_official_confirmation = true
```

单一大额链上转账、单条社媒传闻、单个 Whale Alert、单一 DEX 价格偏离只能进入 watchlist，不能触发正式 risk veto。

### 13.5 第一版输出

```text
confirmed_status
confirmed_at_ms
incident_type
severity
source_confidence
affected_assets
affected_chains
affected_venues
affected_protocols
contagion_scope
avoidance_window
risk_veto_active
false_alarm_status
spread_peak_bps
depth_collapse_ratio
recovery_time_minutes
```

不得输出：

```text
short instruction
buy-the-dip instruction
position size
execution feasibility
entry/exit path
PnL expectation
```

### 13.6 执行纪律 SOP

触发后第一反应必须是 safe no-op，而不是交易：

```text
cooling_period_minutes = 60
new_position_allowed = false
directional_trade_allowed = false
only_current_exposure_check_allowed = true
protective_deleveraging_review_allowed = true
```

SOP：

```text
1. 进入 60 分钟 no-new-position cooling period；
2. 检查当前持仓、挂单、抵押品、相关链、相关交易所和相关协议暴露；
3. 如果已有直接暴露，允许进入保护性降风险 review；
4. 如果没有暴露，不允许因为事件本身新开方向仓；
5. 记录 confirmed_at_ms、affected_assets、spread/depth、恢复时间和 false_alarm_status。
```

### 13.7 Kill / downgrade criteria

```text
source_false_alarm_rate > 0.50；
affected_assets cannot be mapped；
confirmed_status cannot be established；
event source only provides rumors；
incident trigger encourages short/long output；
exposure mapping cannot be audited；
reviewer tries to use single extreme incident as profit proof。
```

如果第一波反应全部在秒级完成，或 source false-alarm rate 过高，则保留为人工 watchlist / veto context，不再研究方向性 alpha。

### 13.8 客观结论

```text
stage1_6r_status = retained_as_risk_veto_side_route
active_alpha_priority = none
capital_preservation_value = high
recommended_action = write_confirmed_incident_risk_veto_source_audit_design
directional_replay_allowed = false
paper_live_allowed = false
```

具体建议：

```text
不写 exploit short strategy；
不写 depeg momentum strategy；
不把事故后暴跌包装成可执行 alpha；
先写 confirmed incident source / schema / confirmation-time / affected-asset mapping design；
后续只验证 risk-veto 是否能减少暴露和误报，不验证追空收益。
```

第一份文档建议：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6r-confirmed-security-incident-risk-veto-source-audit-design_CN.md
```

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
  Scheduled Unlock Source / Version / Available-Time / Recipient-Contract Audit

Stage 1.6E
  Margin / Borrow Enablement Auxiliary Diagnostic Schema Source Audit

Stage 1.6F
  BTC Exchange Net Position Daily Source / Label Audit

Stage 1.6G
  Fear & Greed / Google Trends Regime Journal Design

Stage 1.6H
  Listing Event Optional Observation / Discipline Design

Stage 1.6I
  Governance / Tokenomics Quarterly Fundamental Reading Guide

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
