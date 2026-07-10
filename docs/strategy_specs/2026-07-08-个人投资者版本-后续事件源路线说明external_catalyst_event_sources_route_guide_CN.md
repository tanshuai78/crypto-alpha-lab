# External Catalyst Events 后续事件源路线说明

**日期:** 2026-07-07  
**用途:** 作为后续编写 `design` / `implementation plan` / `review` 文件的事件源路线参考。  
**适用分支:** External Signal Shadow Lab / External Catalyst Events + Filter  
**当前状态:** 研究说明文档，不是策略设计，不是交易计划。

---

## 0. 一句话结论

在 Stage 1.5F 等待新的 post-watermark futures launch event 期间，可以并行准备其他 external catalyst event source 的 source/schema/effective-time design。

当前建议优先级：

```text
P1: exchange_delisting_notice
  最优先。事件语义硬、官方数据相对可得、effective_time 可定义，适合作为下一条事件源支线。

P2: margin_enablement / borrow_enablement / leverage_enablement
  第二优先。理论基础强，但产品字段分散，schema 难度高。

P3: trading_pair_addition / spot listing / futures listing family
  第三优先。attention shock 和流动性迁移机制存在，但必须强拆 event_type，不能混成 listing。

P4: scheduled token unlock / emission
  第四优先。供给压力原理强，但第三方 calendar hindsight risk 最大，必须先做 source audit。
```

本文件只用于研究路线规划。所有路线均不允许直接输出：

```text
trade_signal
paper_trading_allowed = true
live_trading_allowed = true
execution_engine_allowed = true
alpha_interpretation_allowed = true
execution_feasibility_claim_allowed = true
```

---

## 1. 基础概念

### 1.1 Alpha 是什么

在本项目里，`alpha` 不是“事件后价格涨跌过”。

更严格地说：

```text
alpha = 某类信息或规则，在扣除手续费、滑点、延迟、错误样本、盘口容量限制后，仍然能稳定跑赢随机基线或价格基线。
```

因此：

```text
公告后涨了 ≠ alpha
历史 close price 看起来有收益 ≠ execution feasibility
单个样本表现好 ≠ 事件类型成立
```

### 1.2 External Catalyst Event 是什么

`External Catalyst Event` 指来自市场价格之外的外部催化事件，例如：

```text
交易所公告
合约 / 杠杆功能开通
交易对增加或移除
下线公告
重大解锁或释放计划
交易所状态变化
```

它们不同于：

```text
price
volume
funding
OI
liquidation
orderbook depth
```

后者是市场内部状态变量；前者是外部事件源。

核心研究假设是：

```text
external catalyst -> 预期变化 / 杠杆可得性变化 / 供给变化 / 流动性迁移 -> 市场状态切换
```

### 1.3 Replay 是什么

`replay` 可以理解成“历史事件体检”。

它不是模拟下单，而是：

```text
把历史 external catalyst event 按统一 available_at_ms、entry delay、cost、baseline、filter group 重跑，检查这类事件过去是否真的比随机时间点或普通价格基线更有信息量。
```

Replay 回答的是：

```text
这类事件过去值不值得继续研究？
```

不是：

```text
今天能不能立刻交易？
```

### 1.4 available_at_ms 为什么关键

每个外部事件至少有两个时间：

```text
event_time_ms:
  事件声称发生的时间。

available_at_ms:
  我们的系统或市场可以保守认为最早拿到这条信息的时间。
```

如果公告 10:00 发布，但系统 10:08 才抓到，replay 用 10:00 入场就是未来函数。

统一规则：

```text
所有 replay 必须以 available_at_ms 或更保守的时间作为信息可得锚点。
```

### 1.5 统一流程

所有后续事件源都应使用同一条研究管线：

```text
raw payload
-> source audit
-> normalize
-> available_at_ms policy
-> hard veto filter
-> context label filter
-> historical replay
-> review
-> live source observation
-> live depth observation
-> evidence review
-> decide continue / stop
```

---

## 2. 四条路线横向对比

| 路线 | Alpha 原理强度 | 数据可得性 | Schema 难度 | 执行证据审计难度 | 当前优先级 |
|---|---:|---:|---:|---:|---:|
| `exchange_delisting_notice` | 高 | 中高 | 中 | 中 | P1 |
| `margin/borrow/leverage enablement` | 高 | 中 | 高 | 高 | P2 |
| `trading_pair_addition / listing family` | 中高 | 高 | 高 | 高 | P3 |
| `scheduled token unlock / emission` | 高 | 中低 | 高 | 中高 | P4 |

推荐推进顺序：

```text
1. 先做 exchange_delisting_notice source/schema/effective-time design。
2. 再做 margin / borrow / leverage enablement source audit。
3. listing 家族必须拆 event_type 后再做。
4. unlock / emission 先做 source audit，不直接 replay。
```

---

## 3. P1：exchange_delisting_notice

### 3.1 定义

`exchange_delisting_notice` 是交易所宣布某个资产、交易对、合约或产品功能即将下线的公告。

必须拆分 market scope：

```text
spot_delisting:
  现货交易对或现货资产下线。

futures_delisting:
  永续 / 交割合约下线或自动结算。

margin_delisting:
  杠杆交易功能下线。

borrow_delisting:
  借币功能下线。

trading_pair_removal:
  某个交易对移除，但资产本身未必完全下线。
```

不能把它们混成一个 event_type。

### 3.2 可能成为 alpha 的原理

#### 原理 A：风险重估

交易所下线代表市场需要重新评估资产风险：

```text
资产质量风险
合规风险
流动性风险
运营风险
交易通道风险
```

潜在市场反应：

```text
风险厌恶资金卖出
做市商降低库存
散户恐慌迁移
借贷平台降低抵押价值
跨交易所价格分化
```

研究假设：

```text
delisting_notice 后，受影响资产可能出现负向漂移、波动升高、盘口变薄或跨所价差扩大。
```

#### 原理 B：流动性迁移

交易对即将下线时，用户和做市商会迁移交易位置：

```text
卖出
转到其他交易所
切换 quote pair
关闭挂单
关闭 basis / hedge 仓位
```

可能造成：

```text
原交易所深度下降
价差扩大
冲击成本升高
跨所价差扩大
```

#### 原理 C：强制平仓 / 强制结算

如果是 futures delisting，交易所通常会设置：

```text
最后交易时间
自动结算时间
资金费率停止时间
仓位关闭要求
```

这会迫使部分市场参与者关闭仓位，可能产生非自愿交易流。

#### 原理 D：shortability 改变

如果 delisting 同时影响 futures / borrow / margin，做空路径也会变化。

研究上必须区分：

```text
价格下跌可观察 ≠ 当时可做空
```

第一版只能做 observation / replay，不能把 short path 解释成 execution claim。

### 3.3 最小可实现方案

第一版建议限定：

```text
source = Binance official announcements
scope = futures-related delisting / trading-pair-removal only
```

原因：

```text
1. Binance 公告源已在 Stage 1.5A / 1.5D 路线中验证过。
2. futures market 有统一 exchangeInfo / kline / depth endpoint。
3. 与当前 futures_contract_launch 管线复用度最高。
```

### 3.4 最小 schema

```json
{
  "event_type": "exchange_delisting_notice",
  "source": "binance_announcement",
  "source_article_id": "...",
  "source_url": "...",
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "market_scope": "futures|spot|margin|borrow",
  "symbol": "XYZUSDT",
  "base_asset": "XYZ",
  "quote_asset": "USDT",
  "effective_time_ms": 0,
  "delisting_time_ms": 0,
  "settlement_time_ms": 0,
  "futures_historical_existence": true,
  "shortability_status": "futures_exists|borrow_exists|unknown",
  "raw_payload_hash": "...",
  "event_payload_hash": "..."
}
```

### 3.5 必要字段

缺任意关键字段时，不能进入 replay：

```text
market_scope
available_at_ms
effective_time_ms 或 delisting_time_ms
futures_historical_existence
source_url / source_article_id
raw_payload_hash
```

### 3.6 Replay anchor

同一事件至少分三种 anchor：

```text
announcement_anchor:
  从 available_at_ms 开始。
  用于研究公告冲击。

effective_anchor:
  从 effective_time_ms 前后开始。
  用于研究正式生效前后的流动性迁移。

settlement_anchor:
  如果 futures 自动结算，从 settlement_time_ms 开始。
  用于研究强制结算前后行为。
```

三种 anchor 不能混用。

### 3.7 第一版 filter matrix

Hard veto：

```text
source_integrity_veto
available_at_veto
market_scope_missing_veto
effective_time_missing_veto
futures_historical_existence_veto
forbidden_payload_veto
```

Context label：

```text
pre_event_liquidity_bucket
pre_event_market_cap_bucket
pre_event_volume_bucket
btc_regime_context
funding_crowding_context
oi_crowding_context
orderbook_execution_context
```

### 3.8 最可能失败原因

```text
历史样本太少。
spot / futures / margin scope 混乱。
公告前已经跌完。
无法确认当时 futures 是否存在。
无法确认可做空路径。
盘口太薄，close-price paper edge 不可执行。
```

### 3.9 当前建议

```text
decision = write_stage1_6a_exchange_delisting_notice_source_schema_effective_time_design
```

不要直接写：

```text
delisting_alpha_replay_plan
```

第一阶段只解决：

```text
source 是否可靠？
schema 是否可抽？
effective_time 是否可定义？
样本是否够？
```

---

## 4. P2：margin_enablement / borrow_enablement / leverage_enablement

### 4.1 定义

这类事件表示交易所开放或改变某个资产的杠杆、借币、保证金或 leverage 参数。

必须拆开：

```text
margin_enablement:
  允许保证金交易。

borrow_enablement:
  允许借入 base asset 或 quote asset。

leverage_enablement:
  提高或开放 futures leverage。

collateral_enablement:
  允许某资产作为抵押物。
```

### 4.2 可能成为 alpha 的原理

#### 原理 A：做空能力突然出现

如果 base asset 可以被借出，悲观资金可以借币卖出。

研究假设：

```text
base borrow enabled -> shortability shock -> 价格发现加速 / 卖压上升 / 波动升高
```

但注意：

```text
可借功能开放 ≠ 可借库存充足
```

#### 原理 B：做多杠杆能力增强

如果 quote asset 可以借，或 margin long 开放，看多资金可以更容易放大仓位。

研究假设：

```text
quote borrow enabled -> leverage-long access -> attention / buy pressure / OI increase
```

#### 原理 C：参与者结构改变

开放 margin/leverage 后，参与者从普通现货交易者扩展为：

```text
杠杆多头
杠杆空头
套利者
做市商
清算猎手
资金费率交易者
```

市场结构可能发生变化。

#### 原理 D：流动性和波动同时变化

杠杆产品可能：

```text
增加交易量
改善盘口深度
提高短期波动
增加清算风险
```

方向不一定稳定，因此第一版更适合做 `market_structure_change_diagnostic`，不是 long/short 策略。

### 4.3 最小可实现方案

第一版只能限定单一产品族。

可选：

```text
方案 A: Binance margin borrow_enablement only
方案 B: Binance futures leverage change only
```

不要同时研究 margin、borrow、futures leverage。

### 4.4 最小 schema

```json
{
  "event_type": "borrow_enablement",
  "source": "binance_announcement",
  "source_article_id": "...",
  "source_url": "...",
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "effective_time_ms": 0,
  "product_scope": "margin|borrow|futures_leverage|collateral",
  "symbol": "XYZUSDT",
  "base_asset": "XYZ",
  "quote_asset": "USDT",
  "borrow_asset": "XYZ|USDT|unknown",
  "long_enabled": true,
  "short_enabled": true,
  "leverage_before": null,
  "leverage_after": null,
  "borrow_data_available": false,
  "raw_payload_hash": "..."
}
```

### 4.5 分组方式

```text
G1: base asset borrow enabled
  偏 shortability shock。

G2: quote asset borrow enabled
  偏 leverage-long shock。

G3: both base and quote borrow enabled
  方向不确定，只做 volatility / liquidity diagnostic。

G4: futures leverage increase
  偏 OI / liquidation-risk diagnostic。
```

### 4.6 观察指标

```text
forward_return_1h / 4h / 12h / 24h
realized_volatility
OI change
funding change
liquidation imbalance
spread_bps
top depth
slippage proxy
borrow rate / borrow utilization，若可得
```

### 4.7 最可能失败原因

```text
公告字段分散。
产品线命名不统一。
borrow enabled 不代表有可借库存。
borrow utilization 数据可能拿不到。
方向不稳定，既可能多，也可能空，也可能只是波动变大。
不同交易所规则差异大。
```

### 4.8 当前建议

P2 理论强，但不要作为下一条首选。更适合在 P1 delisting source/schema 做完后，选一个窄产品族做 source audit。

---

## 5. P3：trading_pair_addition / spot listing / futures listing family

### 5.1 定义

这类事件都是“新增交易入口”，但机制差异极大。

必须拆分：

```text
spot_listing:
  某资产第一次上线现货。

spot_pair_addition:
  已有资产新增一个现货交易对，例如 XYZ/FDUSD。

futures_contract_launch:
  新增永续或交割合约。

margin_pair_addition:
  新增杠杆交易对。

launchpool_or_launchpad_listing:
  带发行、营销、挖矿或空投属性的 listing。
```

不能把它们合并成 `listing`。

### 5.2 可能成为 alpha 的原理

#### 原理 A：Attention shock

listing 会带来注意力：

```text
更多用户看到该资产。
更多机器人和做市商接入。
行情网站和聚合器更新。
社群和媒体传播。
```

可能导致：

```text
成交量暴增
短期价格跳变
盘口重构
波动升高
```

#### 原理 B：流动性迁移

新增交易对会改变交易流向。

例子：

```text
XYZ/USDT 已存在，新增 XYZ/FDUSD。
```

可能发生：

```text
部分成交迁移到新 pair。
旧 pair 深度下降或总深度增加。
跨 pair 套利增强。
价差和盘口结构变化。
```

#### 原理 C：用户入口变化

新增 fiat/stable pair 可能改变区域或资金入口：

```text
TRY pair -> 土耳其用户入口
EUR pair -> 欧元区入口
USDC pair -> 合规稳定币入口
FDUSD pair -> 特定交易所生态入口
```

#### 原理 D：futures listing 改变多空结构

futures listing 不只是新增交易对，还引入：

```text
杠杆多头
杠杆空头
funding
OI
清算
basis trade
做市 hedge
```

当前项目已经在 Stage 1.5 主线研究 `futures_contract_launch`，不要重复造轮子。

### 5.3 最小可实现方案

如果要扩展 P3，不建议先做 futures listing，因为它已经是 Stage 1.5 主线。

建议后续选择：

```text
spot_pair_addition_or_spot_listing_source_audit
```

但必须先拆 event_type。

### 5.4 最小 schema

```json
{
  "event_type": "spot_listing",
  "listing_family": "spot|spot_pair_addition|futures|margin|launchpool",
  "market_scope": "spot|futures|margin",
  "source_article_id": "...",
  "source_url": "...",
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "trading_start_time_ms": 0,
  "symbol": "XYZUSDT",
  "base_asset": "XYZ",
  "quote_asset": "USDT",
  "is_first_major_exchange_listing": false,
  "is_new_pair_for_existing_asset": true,
  "existing_spot_market_elsewhere": true,
  "existing_futures_market": true,
  "raw_payload_hash": "..."
}
```

### 5.5 Replay 分组

```text
G1: first major exchange spot listing
G2: new quote pair for existing listed asset
G3: spot listing with existing futures market
G4: spot listing without existing futures market
G5: futures listing after spot market exists
G6: launchpool / launchpad listing
```

### 5.6 Hard veto

```text
listing_family_missing_veto
trading_start_time_missing_veto
available_at_veto
first_hour_no_trade_veto
asset_quality_veto
liquidity_depth_veto
source_integrity_veto
```

### 5.7 最可能失败原因

```text
第一小时不可成交或滑点极高。
公告前已经泄露。
不同 listing 类型混杂。
价格表现依赖单个币营销。
做市商控制初期盘口。
市场过度拥挤。
```

### 5.8 当前建议

P3 可以作为后续路线，但必须先拆：

```text
spot_listing
spot_pair_addition
futures_contract_launch
margin_pair_addition
```

当前不要再扩展 futures listing，除非 1.5F/1.5G 盘口证据开始形成。

---

## 6. P4：scheduled token unlock / emission

### 6.1 定义

`scheduled token unlock` 是原本锁定的代币按计划释放。

常见类型：

```text
team unlock
investor unlock
ecosystem unlock
community incentive unlock
staking reward emission
mining emission
linear vesting
cliff unlock
```

`emission` 是新供应进入市场。

### 6.2 可能成为 alpha 的原理

#### 原理 A：供给压力

最基本逻辑：

```text
需求不变，供给增加，价格承压。
```

但必须注意：

```text
unlocked != immediately sold
```

解锁只是“可以卖”，不是“一定卖”。

#### 原理 B：Overhang 风险

`overhang` 是潜在卖压。

即使接收方没有马上卖，市场也会担心：

```text
这些代币未来随时可能进入市场。
```

影响强度取决于：

```text
unlock_amount / circulating_float
unlock_amount / 30d_volume
recipient_type
liquidity_depth
market regime
是否 OTC 消化
```

#### 原理 C：预期提前反映

unlock schedule 通常提前公开。市场可能在事件前就卖出。

所以真正可研究的窗口不是只有当天：

```text
T-14d to T-7d
T-7d to T-1d
T-1d to T+1d
T+1d to T+7d
```

事件当天可能反而出现“利空落地”反弹。

#### 原理 D：低流动性资产更敏感

同样 1000 万美元 unlock：

```text
日成交 5 亿美元的币：影响可能有限。
日成交 1000 万美元的币：可能是巨大冲击。
```

所以核心不是绝对解锁额，而是比例：

```text
unlock_float_pct
unlock_to_30d_volume_ratio
unlock_to_depth_ratio
```

### 6.3 最小可实现方案

P4 第一阶段必须是：

```text
unlock_calendar_source_audit
```

不要直接 replay。

原因：

```text
第三方 calendar 可能事后修改。
历史 schedule 未必带当时可得时间。
今天查到的 unlock 数据，不代表当时市场知道。
```

### 6.4 最小 schema

```json
{
  "event_type": "scheduled_token_unlock",
  "source": "unlock_calendar_vendor",
  "source_url": "...",
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "event_time_ms": 0,
  "symbol": "XYZUSDT",
  "base_asset": "XYZ",
  "unlock_amount_tokens": 0,
  "unlock_amount_usd": 0,
  "unlock_float_pct": 0.0,
  "unlock_total_supply_pct": 0.0,
  "unlock_to_30d_volume_ratio": 0.0,
  "recipient_type": "team|investor|ecosystem|community|unknown",
  "schedule_confidence": "high|medium|low",
  "hindsight_risk_level": "low|medium|high",
  "raw_payload_hash": "..."
}
```

### 6.5 Source audit 必问问题

```text
这个 calendar 当时是否已经公开？
历史记录是否会被事后修改？
有没有原始发布时间？
有没有 API response hash / page snapshot？
不同来源是否一致？
unlock amount 是否会被更新？
recipient_type 是否可靠？
```

只要这些问题无法解决，就不能 replay。

### 6.6 Replay 分组

```text
G1: unlock_float_pct >= 2%
G2: unlock_to_30d_volume_ratio >= 0.5
G3: investor/team unlock
G4: ecosystem/community unlock
G5: low-liquidity unlock
G6: high-liquidity unlock
```

### 6.7 必须加的 veto

```text
hindsight_risk_veto
calendar_source_integrity_veto
available_at_veto
asset_quality_veto
liquidity_depth_veto
```

### 6.8 最可能失败原因

```text
calendar hindsight risk。
解锁不等于卖出。
OTC 消化。
市场提前定价。
第三方数据历史不可复核。
低流动性 token 无法执行。
```

### 6.9 当前建议

P4 经济学原理强，但第一步只能做 source audit：

```text
scheduled_token_unlock_source_audit_design
```

不要直接写：

```text
unlock_short_replay_plan
```

---

## 7. 统一 Source Audit 成功标准

所有事件源都应先过 source audit。

最低通过标准：

```text
historical_events_found >= 30
source_integrity_pass_rate >= 95%
symbol_mapping_pass_rate >= 95%
available_at_policy_defined = true
forbidden_payload_count = 0
```

解释：

```text
historical_events_found >= 30:
  样本太少时，无法判断是否有结构。

source_integrity_pass_rate >= 95%:
  大部分样本必须能稳定抽到关键字段。

symbol_mapping_pass_rate >= 95%:
  公告里的资产必须能正确映射成研究 symbol。

available_at_policy_defined = true:
  没有可得时间策略，replay 会出现未来函数。

forbidden_payload_count = 0:
  一旦出现 api_key、private_key、order_request 等敏感字段，必须 reject。
```

---

## 8. 统一 Replay 成功标准

只有 source audit 通过后，才允许写 replay plan。

最低 replay pass 标准：

```text
event_count >= 30
event_days >= 10
symbols_with_events >= 3
median_net_return_after_50bps > 0
baseline_excess_net_bps > 0
price_baseline_excess_net_bps > 0
left_tail_p05 not worse than random baseline
top_5_positive_events_gross_profit_share <= 0.40
max_single_day_event_share <= 0.30
max_single_symbol_event_share <= 0.60
```

Replay 必须输出：

```text
forward_return_1h
forward_return_4h
forward_return_12h
forward_return_24h
MFE
MAE
median_return
trimmed_mean_return
left_tail_p05
hit_rate_vs_random_baseline
top_5_events_pnl_share
max_single_day_contribution
max_single_symbol_contribution
```

---

## 9. 统一失败条件

如果出现以下任一情况，应停止或降级：

```text
source 无法审计
available_at_ms 无法保守构建
事件数不足且不可扩展
表现不优于 random baseline
表现不优于 price baseline
成本后中位收益为负
收益由单日 / 单币 / Top 5 极端事件贡献
filter matrix 没有增量价值
盘口深度不足以支持后续 execution research
```

失败后的正确动作：

```text
stop_this_event_source
或
observation_only
或
design_next_narrower_source_audit
```

错误动作：

```text
继续调阈值救结果
混入更多 event_type 稀释失败
直接进入 paper/live
把 close-price replay 包装成 execution feasibility
```

---

## 10. Design / Plan 文件命名建议

### 10.1 P1 delisting

```text
2026-07-xx-external-signal-shadow-lab-stage1-6a-exchange-delisting-notice-source-schema-effective-time-design_CN.md
2026-07-xx-external-signal-shadow-lab-stage1-6a-exchange-delisting-notice-source-schema-effective-time-implementation-plan_CN.md
```

### 10.2 P2 margin / borrow / leverage

```text
2026-07-xx-external-signal-shadow-lab-stage1-6b-margin-borrow-leverage-enablement-source-audit-design_CN.md
2026-07-xx-external-signal-shadow-lab-stage1-6b-margin-borrow-leverage-enablement-source-audit-implementation-plan_CN.md
```

### 10.3 P3 listing family

```text
2026-07-xx-external-signal-shadow-lab-stage1-6c-listing-family-event-type-split-source-audit-design_CN.md
2026-07-xx-external-signal-shadow-lab-stage1-6c-listing-family-event-type-split-source-audit-implementation-plan_CN.md
```

### 10.4 P4 unlock / emission

```text
2026-07-xx-external-signal-shadow-lab-stage1-6d-token-unlock-emission-source-audit-design_CN.md
2026-07-xx-external-signal-shadow-lab-stage1-6d-token-unlock-emission-source-audit-implementation-plan_CN.md
```

---

## 11. 推荐下一步

当前 1.5D / 1.5F 不应暂停。

等待新的 futures launch live depth evidence 时，优先推进：

```text
Stage 1.6A exchange_delisting_notice source/schema/effective-time design
```

第一版目标：

```text
只做 source/schema/effective-time audit。
不做 alpha replay。
不做 live source collector。
不做 paper/live。
```

最小问题清单：

```text
1. Binance official announcements 中是否能稳定抽到 delisting notices？
2. 是否能区分 spot / futures / margin / borrow scope？
3. 是否能抽到 effective_time_ms / delisting_time_ms / settlement_time_ms？
4. 是否能确认当时 futures market 存在？
5. 是否有 >=30 historical events、>=10 event days、>=3 symbols？
6. 是否能保守定义 available_at_ms？
7. 是否能保存 raw_payload_hash / event_payload_hash？
8. 是否有 forbidden payload 风险？
```

---

## 12. 最终边界

本文件不能被解释为：

```text
alpha 已成立
下一步可以交易
可以 paper trading
可以 live trading
可以连接 execution engine
可以生成 TradeIntent
```

本文件只支持：

```text
后续事件源路线选择
source audit design 编写
schema design 编写
implementation plan 前置参考
review checklist 编写
```

最终原则：

```text
外部事件先变成证据，不是先变成交易冲动。
```
