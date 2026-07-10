# External Catalyst Events 后续事件源路线说明（个人投资者可执行版）

**日期:** 2026-07-07  
**用途:** 作为后续编写 `design` / `implementation plan` / `review` 文件的路线参考。  
**适用分支:** External Signal Shadow Lab / External Catalyst Events + Filter  
**当前状态:** 研究说明文档，不是策略设计，不是交易计划。  

---

## 0. 一句话结论

后续事件源不是都适合个人投资者。

适合个人投资者的不是“事件本身”，而是事件后的低频、可审计、可回放、可用小资金验证的结构变化。

本项目应明确排除：

```text
毫秒级抢公告
新币上市首分钟狙击
KOL / news 秒级抢跑
需要私钥或钱包签名的链上自动交易
需要 VIP API、专线、做市商库存的盘口抢跑
需要即时借币库存的做空策略
```

本项目可以保留：

```text
delisting 后的慢速风险重估
unlock 前后的低频供给压力
margin / borrow / leverage enablement 后的市场结构变化
listing / futures launch 跳过首小时后的流动性稳定与 attention drift
```

核心原则：

```text
个人投资者不和机器人比快。
个人投资者只研究 1h / 4h / 12h / 24h 级别的二阶反应。
```

所有路线仍保持：

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

---

## 1. 个人投资者可行性判断标准

一条 external catalyst event source 只有同时满足下面大部分条件，才值得进入后续 design。

```text
1. 反应窗口 >= 15 分钟，最好 >= 1 小时。
2. 不依赖公告首秒 / 首分钟抢反应。
3. 数据能通过公开只读接口或静态网页获得。
4. 不需要私钥、钱包、API key、交易权限。
5. 不依赖真实借币库存、VIP 费率或高速专线。
6. 能定义 available_at_ms，避免 hindsight bias。
7. 能积累足够历史样本。
8. 能通过 live depth evidence 验证盘口容量。
9. 能在 500 USDT 级别小资金假设下审计深度和滑点。
10. 失败后可以明确停止，而不是无限调参。
```

如果一条路线的收益主要来自：

```text
公告后 0–5 秒
listing 开盘第一根撮合
别人还没看到公告之前
链上交易排序或 MEV
跨交易所秒级价差
```

则默认不适合个人投资者。

---

## 2. 最终推荐优先级

| 优先级 | 事件源 | 个人投资者适配度 | 推荐动作 |
|---|---|---:|---|
| P1 | `exchange_delisting_notice` | 高 | 下一条主线，先写 source/schema/effective-time design |
| P2 | `scheduled_token_unlock / emission` | 高，但 source audit 难 | 做 source audit，不直接 replay |
| P3 | `margin_enablement / borrow_enablement / leverage_enablement` | 中等 | 只选单一产品族做 source audit |
| P4 | `trading_pair_addition / spot listing / futures listing family` | 中等偏低，首小时高危 | 只研究跳过首小时后的二阶反应 |

注意：P2 在“个人投资者时间尺度”上比 listing 更友好，但因为 source audit 难，所以工程优先级可排在 delisting 后面。

---

## 3. 统一硬规则

后续所有事件源 design 都应默认包含以下 hard rules。

### 3.1 First-hour no-trade veto

```text
first_hour_no_trade_veto = true
```

含义：

```text
公告 / listing / launch 后第一小时只观察，不把它当成 replay 入场窗口。
```

原因：首小时通常存在：

```text
跳空
插针
盘口极薄
价差极大
API 限频
做市商重新定价
机器人竞争最激烈
```

除非后续单独证明某事件源不需要这个 veto，否则默认启用。

### 3.2 Minimum actionable latency bucket

```text
minimum_actionable_latency_bucket = ">=1h"
```

含义：

```text
只研究 1h 以上的二阶反应，不研究秒级/分钟级抢跑。
```

### 3.3 Personal investor feasibility required

```text
personal_investor_feasibility_required = true
```

最低要求：

```text
no_private_endpoint
no_api_key_required
no_wallet_required
no_sub_minute_entry
no_vip_fee_assumption
no_borrow_inventory_dependency_for_first_version
live_depth_evidence_required_before_execution_sim
```

### 3.4 Evidence boundary

即使 historical replay 通过，也只能进入：

```text
source audit
minimal event table
historical replay
live source observation
live depth observation
shadow execution simulator design
```

不能直接进入：

```text
paper trading
live trading
execution engine
position sizing
TradeIntent
```

---

## 4. P1: exchange_delisting_notice

### 4.1 适配结论

```text
research_fit = high
execution_fit = medium
latency_dependency = low_to_medium
first_minute_competition = avoid
recommended = yes, first next branch
```

`exchange_delisting_notice` 是最适合下一步推进的事件源。

它适合个人投资者的原因不是“公告一出可以马上开空”，而是：

```text
下线公告通常引发的是慢速风险重估、流动性迁移、做市商撤流动性、合约结算压力。
这些变化可能持续数小时到数天，不完全依赖首秒速度。
```

### 4.2 Alpha 原理

#### 原理 A：风险重估

交易所宣布下线，相当于告诉市场：

```text
这个资产或交易对不再满足某些上市、流动性、合规或运营要求。
```

市场可能重新定价风险：

```text
风险厌恶资金卖出
做市商降低库存
借贷平台降低抵押价值
散户迁移到其它交易所
套利资金关闭相关路径
```

可能表现为：

```text
短期负向 drift
盘口变薄
价差扩大
跨交易所价差扩大
波动升高
```

#### 原理 B：流动性迁移

交易对下线后，原交易所的流动性会迁移或消失：

```text
挂单撤出
交易者转去其它交易所
做市商撤单
跨所价格联动变差
```

这类变化不一定在一秒内完成，更适合 1h / 4h / 12h / effective-time 前后研究。

#### 原理 C：强制结算 / 强制迁移

如果是 futures delisting，可能存在：

```text
最后交易时间
自动结算时间
仓位必须关闭时间
资金费率停止时间
```

这会迫使仓位提前平仓或迁移。

### 4.3 不适合个人的部分

```text
公告首分钟抢空
没有 futures / borrow 路径却假设可以做空
盘口极薄时追空
用历史已经跌完的样本反推公告入场
```

### 4.4 推荐研究窗口

```text
T+1h
T+4h
T+12h
T+24h
effective_time - 24h
effective_time - 4h
effective_time + 1h
```

### 4.5 第一版 scope

```text
scope = Binance futures-related delisting notice
```

不要第一版就覆盖所有交易所、所有 spot/margin/futures delisting。

### 4.6 最小事件 schema

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
  "futures_historical_existence": true,
  "shortability_status": "futures_exists|borrow_exists|unknown",
  "raw_payload_hash": "...",
  "event_payload_hash": "..."
}
```

### 4.7 必须先解决的 blockers

| blocker | 含义 | 最小解决路径 |
|---|---|---|
| `sample` | 历史样本是否足够 | 先清点 `event_count / event_days / symbols_with_events` |
| `market_scope` | 影响的是 spot / futures / margin / borrow 哪个市场 | schema 强制拆出 `market_scope` |
| `effective_time` | 公告时间与真正下线时间不同 | 同时保存 `available_at_ms / effective_time_ms` |
| `futures_historical_existence` | 当时是否有可研究 futures 市场 | 做 historical exchangeInfo / symbol existence audit |
| `shortability` | 是否真的有可做空路径 | 第一版只做 observation/replay，不做 execution claim |

### 4.8 推荐下一步文档

```text
2026-07-xx-external-signal-shadow-lab-stage1-6a-exchange-delisting-notice-source-schema-effective-time-design_CN.md
```

目标只写：

```text
source/schema/effective-time audit
```

不要直接写：

```text
delisting alpha replay
```

---

## 5. P2: scheduled token unlock / emission

### 5.1 适配结论

```text
research_fit = high
execution_fit = medium
latency_dependency = low
main_blocker = source_audit_and_hindsight_risk
recommended = yes, but source audit first
```

Token unlock / emission 是最适合个人投资者时间尺度的事件之一，因为它通常是提前排期事件，不需要毫秒级抢跑。

真正的问题不是速度，而是：

```text
历史 schedule 是否当时就可见？
第三方 calendar 是否事后修改？
unlock amount 是否可复核？
解锁是否真的形成卖压？
```

### 5.2 Alpha 原理

#### 原理 A：供给压力

简化理解：

```text
需求不变，供给增加，价格承压。
```

但必须注意：

```text
unlocked != immediately sold
```

解锁只是“可以卖”，不是“一定卖”。

#### 原理 B：Overhang 潜在卖压

即使解锁后没有立刻卖，市场也会担心：

```text
这些代币随时可能进入市场。
```

影响大小取决于：

```text
unlock_amount / circulating_float
unlock_amount / 30d_volume
unlock_amount / orderbook_depth
recipient_type
market regime
```

#### 原理 C：提前定价与利空落地

因为 unlock 通常提前公开，市场可能提前反应。

所以研究窗口不应只看 unlock 当天：

```text
T-14d -> T-7d
T-7d -> T-1d
T-1d -> T+1d
T+1d -> T+7d
```

### 5.3 不适合个人的部分

```text
看到明天解锁就直接开空
不区分 team / investor / ecosystem unlock
不看 unlock_to_volume_ratio
不看盘口深度
用今天可见的完整 calendar 回测两年前事件
```

### 5.4 第一版 scope

第一版不做 replay，先做：

```text
unlock_calendar_source_audit
```

需要回答：

```text
source_published_at_ms 是否存在
available_at_ms 是否可保守构建
历史 schedule 是否有版本记录
unlock amount 是否会被事后修改
symbol mapping 是否稳定
```

### 5.5 最小事件 schema

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

### 5.6 必须先解决的 blockers

```text
hindsight_risk
source_versioning
available_at_policy
schedule_confidence
recipient_type_quality
symbol_mapping_quality
```

### 5.7 推荐下一步文档

```text
2026-07-xx-external-signal-shadow-lab-stage1-6b-token-unlock-calendar-source-audit-design_CN.md
```

---

## 6. P3: margin_enablement / borrow_enablement / leverage_enablement

### 6.1 适配结论

```text
research_fit = medium_high
execution_fit = medium_low
latency_dependency = medium
main_blocker = borrow_inventory_and_product_scope
recommended = after delisting / unlock source audit
```

这类事件理论上很强，但执行路径复杂。

对个人投资者，第一版只能研究：

```text
杠杆可得性变化后，市场结构是否发生 4h / 12h / 24h 级别变化。
```

不能直接研究：

```text
公告后马上借币做空
依赖真实 borrow 库存
依赖 VIP margin rate
```

### 6.2 Alpha 原理

#### 原理 A：做空能力突然出现

如果某个币以前不能 borrow，现在可以 borrow，则悲观资金可以表达看空观点。

可能结果：

```text
卖压增加
价格发现加快
高估值回落
funding / OI / borrow demand 改变
```

#### 原理 B：杠杆做多能力增强

如果 quote borrow 或 leverage long 能力增强，则看多资金可以用更少本金控制更大仓位。

可能结果：

```text
短期买压
OI 上升
funding 变正
后续拥挤清算风险增加
```

#### 原理 C：参与者结构变化

开放 margin / borrow / leverage 后，市场参与者从现货买卖扩展为：

```text
杠杆多头
杠杆空头
资金费率套利者
做市商
清算猎手
```

这可能改变价格、波动、深度和 liquidation profile。

### 6.3 不适合个人的部分

```text
实时抢借币库存
依赖账户权限
依赖 VIP 费率
假设公告支持就一定借得到
假设 borrow enabled 就能稳定做空
```

### 6.4 第一版 scope

必须只选一个产品族。

推荐二选一：

```text
scope = Binance margin borrow_enablement only
```

或：

```text
scope = Binance futures leverage_enablement only
```

不要把 margin / borrow / futures leverage 混成一个 event_type。

### 6.5 最小事件 schema

```json
{
  "event_type": "borrow_enablement",
  "market_scope": "margin",
  "source_article_id": "...",
  "symbol": "XYZUSDT",
  "base_asset": "XYZ",
  "quote_asset": "USDT",
  "borrow_asset": "XYZ",
  "borrow_side_enabled": true,
  "margin_long_enabled": true,
  "margin_short_enabled": true,
  "effective_time_ms": 0,
  "available_at_ms": 0,
  "source_published_at_ms": 0,
  "raw_payload_hash": "..."
}
```

### 6.6 replay 分组

```text
G1: base asset borrow enabled
  含义：可以借 XYZ 卖出，偏 shortability shock。

G2: quote asset borrow enabled
  含义：可以借 USDT 买 XYZ，偏 leverage-long shock。

G3: both base and quote borrow enabled
  含义：多空杠杆同时开放，方向不确定，只做 volatility / liquidity diagnostic。
```

### 6.7 推荐下一步文档

```text
2026-07-xx-external-signal-shadow-lab-stage1-6c-margin-borrow-enable-source-audit-design_CN.md
```

---

## 7. P4: trading_pair_addition / spot listing / futures listing family

### 7.1 适配结论

```text
research_fit = medium
execution_fit = low_to_medium
latency_dependency = high_for_first_hour / medium_after_1h
main_blocker = first_hour_microstructure
recommended = only with first_hour_no_trade_veto
```

listing 家族最容易被误用。

它不是不能研究，而是不能研究首波抢跑。

### 7.2 Alpha 原理

#### 原理 A：Attention shock

交易所 listing 会带来注意力：

```text
更多用户看到
更多机器人接入
更多做市商报价
更多行情网站更新
```

可能导致：

```text
成交量暴增
价格跳变
高波动
盘口剧烈变动
```

#### 原理 B：流动性迁移

新增交易对可能改变原有交易对的深度和成交分布。

例如：

```text
XYZ/USDT 已存在
新增 XYZ/FDUSD
一部分流动性从 USDT pair 迁移到 FDUSD pair
```

#### 原理 C：Futures listing 改变多空结构

futures listing 会引入：

```text
杠杆多头
杠杆空头
funding
OI
清算
basis trade
做市库存 hedge
```

这也是当前 Stage 1.5 futures_contract_launch 主线的理论基础。

### 7.3 不适合个人的部分

```text
spot listing 首秒
futures listing 开盘首秒
新币首分钟追涨
盘口未稳定时市价单
launchpad/meme 首分钟狙击
```

### 7.4 适合个人的部分

```text
跳过首小时后的 futures launch 12h attention / liquidity drift
新增 quote pair 后的流动性迁移
spot listing 后盘口稳定后的二阶反应
```

### 7.5 必须拆分 event_type

不要写：

```text
event_type = listing
```

必须拆：

```text
event_type = spot_listing
event_type = spot_pair_addition
event_type = futures_contract_launch
event_type = margin_pair_addition
```

### 7.6 最小事件 schema

```json
{
  "event_type": "spot_listing",
  "listing_family": "spot",
  "market_scope": "spot",
  "source_article_id": "...",
  "symbol": "XYZUSDT",
  "base_asset": "XYZ",
  "quote_asset": "USDT",
  "is_first_major_exchange_listing": false,
  "is_new_pair_for_existing_asset": true,
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "trading_start_time_ms": 0,
  "existing_futures_market": true,
  "existing_spot_market_elsewhere": true,
  "raw_payload_hash": "..."
}
```

### 7.7 推荐下一步文档

```text
2026-07-xx-external-signal-shadow-lab-stage1-6d-spot-pair-addition-after-first-hour-source-audit-design_CN.md
```

注意：当前 futures_contract_launch 已经在 Stage 1.5 主线，不要重复造轮子。

---

## 8. 统一 replay 方法

### 8.1 时间锚点

每个事件源至少区分两个 anchor：

```text
anchor_1 = available_at_ms
anchor_2 = effective_time_ms / trading_start_time_ms / unlock_time_ms
```

可选 replay 模式：

```text
after_available_at
after_first_hour_delay
before_effective_time
after_effective_time
```

### 8.2 Entry delay

默认：

```text
1h
4h
12h
```

禁止第一版使用：

```text
0s
10s
1min
5min
```

### 8.3 Holding horizon

```text
1h
4h
12h
24h
7d for unlock only
```

### 8.4 Cost stress

```text
30 bps
50 bps
80 bps
```

### 8.5 Baseline

至少包括：

```text
random time baseline
same-symbol random baseline
same-day random baseline
price momentum baseline
BTC regime baseline
```

### 8.6 Replay pass 最低门槛

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

### 8.7 停止条件

```text
source 无法审计
available_at_ms 无法保守构建
事件数不足且不可扩展
表现不优于 random baseline
成本后中位收益为负
收益由单日 / 单币 / Top 5 极端事件贡献
filter matrix 没有增量价值
需要个人不可控的低延迟或执行资源
```

---

## 9. 个人投资者版路线图

### Stage 1.6A: Exchange Delisting Notice Source / Schema / Effective-Time Audit

目标：

```text
确认 delisting notice 是否有足够样本、稳定字段、明确 effective_time 和 market_scope。
```

第一版只做 Binance futures-related delisting。

通过后才允许写 minimal event table plan。

### Stage 1.6B: Token Unlock Calendar Source Audit

目标：

```text
确认第三方 unlock calendar 是否存在可审计历史、版本记录和可靠 available_at_ms。
```

第一版不做 directional replay。

### Stage 1.6C: Margin / Borrow Enablement Source Audit

目标：

```text
确认 margin / borrow enablement 公告是否能稳定解析 product_scope、borrow_side、effective_time。
```

第一版不做 borrow execution claim。

### Stage 1.6D: Spot Pair Addition After-First-Hour Source Audit

目标：

```text
只研究跳过首小时后的流动性迁移，不研究 listing 抢跑。
```

---

## 10. 推荐立即推进的下一份 design

最推荐：

```text
2026-07-xx-external-signal-shadow-lab-stage1-6a-exchange-delisting-notice-source-schema-effective-time-design_CN.md
```

Design 目标：

```text
source audit
schema audit
effective_time policy
market_scope policy
futures historical existence audit
shortability diagnostic only
```

Design 禁止目标：

```text
delisting alpha claim
short strategy
paper/live
execution simulator
position sizing
```

建议一句话结论：

```text
Stage 1.6A 只回答 Binance futures-related delisting notice 是否具备进入历史事件表和 replay 的数据条件；不回答 delisting 是否可交易。
```

---

## 11. 总结

适合个人投资者的 external catalyst event 研究，应满足：

```text
低频
只读
可审计
可回放
可等待盘口稳定
可用 500 USDT 级别小资金假设验证
不依赖首秒速度
不依赖私有执行资源
```

当前最合适的下一条路线是：

```text
exchange_delisting_notice
```

第二条值得准备的是：

```text
token_unlock_calendar_source_audit
```

但无论哪条路线，当前都只能作为 External Signal Shadow Lab 的研究输入，不能成为交易信号。

最终边界保持：

```text
把外部信息变成可研究事件，
而不是把外部信息变成交易命令。
```
