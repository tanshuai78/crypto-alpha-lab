# External Signal Shadow Lab：新热点事件源研究路线说明（个人投资者可执行版）

**日期:** 2026-07-08  
**用途:** 供后续编写 design / implementation plan / source audit 文件使用  
**状态:** research_route_guide / not_a_strategy / no_paper_live  

---

## 0. 一句话结论

本文件整理的是除 P1-P4 外，当前值得关注的新一批外部事件源候选：

```text
P5: market sentiment / narrative attention spike
P6: prediction market probability shift
P7: stablecoin / exchange flow shock
P8: ETF / institutional flow shock
P9: security incident / exploit / depeg events
P10: governance / protocol / tokenomics event
```

这些方向都有一定研究依据和市场关注度，但都不能直接解释为 alpha。

本项目的正确处理方式仍然是：

```text
source audit
-> schema audit
-> available_at_ms
-> historical replay
-> random / price / regime baseline
-> cost stress
-> live source observation
-> live depth / liquidity evidence
-> evidence review
-> decide continue / stop
```

不允许直接进入：

```text
paper trading
live trading
execution engine
TradeIntent
position sizing
copy trading
wallet / private key / API key
```

---

## 1. 总体判断：这些热点事件源为什么值得看？

P1-P4 主要围绕交易所公告、上市/下线、杠杆开放、解锁等外部催化事件。

本文件的 P5-P10 更偏向：

```text
情绪
叙事
概率市场
资金流
链上行为
制度性资金
安全事故
治理与代币经济变化
```

这些事件源的共同特点：

```text
1. 它们不是单纯价格/OHLCV 派生信号。
2. 它们可能代表外部信息进入市场。
3. 它们可能改变预期、风险偏好、流动性、供给压力或仓位结构。
4. 它们通常比纯 price-volume 信号信息密度更高。
```

但它们也有共同风险：

```text
1. 数据源噪音高。
2. bot / spam / manipulation 污染严重。
3. available_at_ms 难定义。
4. 历史数据容易有 hindsight bias。
5. 很多事件的第一波反应太快，不适合个人投资者。
6. 结果容易被单币、单日、单一极端事件支撑。
```

因此，本文件只定义“值得进一步审计的事件源路线”，不定义交易策略。

---

## 2. 个人投资者适配原则

本项目只保留个人投资者可能执行或研究的低频结构，不研究毫秒级抢跑。

### 2.1 必须排除的方向

```text
秒级 KOL/news 抢跑
新币首分钟狙击
prediction market 直接搬砖套利
需要交易所 VIP 费率或专线
需要私钥 / 钱包签名 / swap payload
需要账户 API key 的自动执行
需要真实借币库存作为第一版核心假设
MEV / 链上抢跑
跨所秒级套利
```

### 2.2 可保留的方向

```text
1h / 4h / 12h / 24h 反应
日频资金流
多日情绪极端状态
公告后低频二阶反应
流动性恶化 / 恢复
风险状态切换
供给压力慢变量
宏观概率变化对 crypto 波动的影响
```

### 2.3 通用硬规则

后续任何 design 建议默认写入：

```text
first_hour_no_trade_veto = true
minimum_actionable_latency_bucket = ">=1h"
personal_investor_feasibility_required = true
execution_feasibility_claim_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
```

含义：

```text
第一小时只观察，不当作可交易入场窗口。
只研究 1 小时以上的结构反应。
任何 positive replay 都只能进入后续 observation / shadow design，不能直接交易。
```

---

## 3. 推荐优先级总表

| 优先级 | 事件源 | 研究价值 | 个人投资者适配 | 数据难度 | 第一版建议 |
|---|---|---:|---:|---:|---|
| P5 | sentiment / narrative attention spike | 高 | 中 | 高 | source selection + bot/noise audit |
| P6 | prediction market probability shift | 高 | 中高 | 中高 | source/schema/settlement audit |
| P7 | stablecoin / exchange flow shock | 高 | 中高 | 高 | address-label source audit |
| P8 | ETF / institutional flow shock | 中高 | 高 | 中 | daily event table + BTC/ETH regime replay |
| P9 | security / exploit / depeg events | 高 | 中 | 高 | incident source audit + risk-veto schema |
| P10 | governance / protocol / tokenomics events | 中高 | 中高 | 高 | source audit + event severity schema |

当前建议排序：

```text
第一批轻量设计：
  P5 sentiment_extreme_and_narrative_attention_source_selection_design
  P6 prediction_market_probability_shift_source_schema_design

第二批：
  P7 stablecoin_exchange_flow_source_audit_design
  P8 ETF_institutional_flow_event_table_design

第三批：
  P9 security_incident_risk_event_source_audit_design
  P10 governance_tokenomics_event_source_audit_design
```

---

# P5. Market Sentiment / Narrative Attention Spike

## 5.1 它是什么？

`market sentiment / narrative attention` 指市场情绪、叙事热度、社交讨论强度、社区情绪突然变化。

来源可能包括：

```text
X / Twitter
Reddit
Discord
Telegram
TikTok
YouTube
Kaito-like mindshare data
LunarCrush-like social metrics
Google Trends
news sentiment feeds
```

事件例子：

```text
某 token 社交提及量 4h 暴增
某 narrative，例如 AI agent / RWA / DePIN / memecoin，mindshare 快速上升
Discord 社区情绪由负转正
Twitter 正面情绪极端化
TikTok 视频情绪突然转强
```

## 5.2 为什么可能成为 alpha？

核心机制不是“大家说好就买”，而是：

```text
注意力迁移 -> 资金流入 / 交易量上升 / 波动扩大 / 做市商调参 / 价格二阶反应
```

情绪事件可能有三类价值：

### A. Attention shock（注意力冲击）

市场注意力集中到某个资产或 narrative，可能带来：

```text
成交量放大
资金追逐
散户参与度提高
短期趋势延续
```

### B. Sentiment regime（情绪状态）

极端恐惧或极端贪婪可能对应：

```text
更高波动
更差流动性
更宽 spread
更高滑点
更强反转风险
```

此时 sentiment 也可以作为风险标签，而不是方向信号。

### C. Cross-platform divergence（跨平台分歧）

例如：

```text
X 已经开始热，但 Discord 未跟随
TikTok retail attention 暴增，但专业 crypto Twitter 没反应
Reddit 负面情绪上升，但价格还未动
```

分歧本身可能有研究价值。

## 5.3 个人投资者是否适合？

```text
research_fit = medium_high
execution_fit = medium
latency_dependency = medium
main_risk = bot/noise/manipulation
```

适合研究：

```text
1h / 4h / 12h attention drift
情绪极端后的 volatility / liquidity regime
narrative rotation
跨平台 attention divergence
```

不适合：

```text
看到 KOL 发帖立刻追
秒级新闻机器人
Telegram 群喊单跟随
meme coin 首分钟 FOMO
```

## 5.4 最小 schema

```json
{
  "event_type": "sentiment_attention_spike",
  "source": "x|reddit|discord|telegram|tiktok|vendor",
  "source_window_start_ms": 0,
  "source_window_end_ms": 0,
  "available_at_ms": 0,
  "symbol": "XYZUSDT",
  "base_asset": "XYZ",
  "narrative_tag": "ai_agent|rwa|depin|meme|l1|defi|other",
  "mention_count": 0,
  "mention_count_zscore": 0.0,
  "sentiment_score": 0.0,
  "sentiment_score_delta": 0.0,
  "unique_author_count": 0,
  "bot_suspected_ratio": 0.0,
  "source_confidence": "high|medium|low",
  "raw_payload_hash": "..."
}
```

## 5.5 Source audit 重点

```text
1. 数据源是否有历史？
2. 是否能拿到原始 timestamp？
3. 是否能区分真实用户和 bot？
4. 是否能稳定映射 token symbol？
5. 是否存在大量 ticker ambiguity？
6. 是否能构建 available_at_ms？
7. 是否有删除、编辑、补录导致的 hindsight risk？
```

## 5.6 Replay 方案

建议分组：

```text
G1: sentiment_score extreme positive
G2: sentiment_score extreme negative
G3: mention_count_zscore spike
G4: narrative_attention spike
G5: cross-platform confirmation
G6: cross-platform divergence
```

窗口：

```text
T+1h
T+4h
T+12h
T+24h
```

主要指标：

```text
forward_return
realized_volatility
volume_expansion
spread_bps
top_depth
MFE / MAE
left_tail_p05
baseline_excess_net_bps
```

基线：

```text
same-symbol random baseline
same-day random baseline
BTC regime baseline
price-momentum baseline
volume-spike baseline
```

## 5.7 停止条件

```text
bot_suspected_ratio 无法估计
symbol mapping 污染严重
event_count < 100 且不可扩展
跨平台确认没有增量
不优于 price/volume baseline
收益全靠少数 meme 极端样本
成本后中位收益为负
```

---

# P6. Prediction Market Probability Shift

## 6.1 它是什么？

`prediction market probability shift` 指预测市场中的事件概率发生显著变化。

来源可能包括：

```text
Polymarket
Kalshi
其他 prediction market / event contract 平台
```

事件例子：

```text
BTC 年底超过某价格的概率 4h 内从 35% 升到 48%
Fed 降息概率突然上升
美国大选候选人胜率变化
ETF approval 概率变化
recession probability 上升
某 crypto regulatory event 概率变化
```

## 6.2 为什么可能成为 alpha？

预测市场把市场对某个事件的概率用价格表达。

它可能影响 crypto 的路径包括：

```text
宏观事件概率变化 -> BTC/ETH risk appetite
监管事件概率变化 -> 相关 token 重估
ETF / policy 概率变化 -> institutional flow 预期
prediction market 与 options / futures 市场信息传递不同步 -> 短期 pricing gap
```

这里的关键不是直接套利 prediction market，而是把概率变化当作外部状态变量。

## 6.3 个人投资者是否适合？

```text
research_fit = high
execution_fit = medium
latency_dependency = low_to_medium
main_risk = settlement_rule / market manipulation / liquidity
```

适合研究：

```text
4h / 12h / 24h probability shock
macro probability repricing 对 BTC/ETH realized volatility 的影响
prediction probability 与 crypto options-implied probability gap
```

不适合：

```text
直接 prediction market 搬砖套利
依赖平台提现/充值速度
依赖合约结算条款漏洞
```

## 6.4 最小 schema

```json
{
  "event_type": "prediction_market_probability_shift",
  "platform": "polymarket|kalshi|other",
  "contract_id": "...",
  "contract_title": "...",
  "underlying_event_category": "macro|crypto_price|regulation|politics|etf|other",
  "source_url": "...",
  "probability_before": 0.35,
  "probability_after": 0.48,
  "probability_delta": 0.13,
  "window_ms": 14400000,
  "market_liquidity_usd": 0.0,
  "volume_usd": 0.0,
  "available_at_ms": 0,
  "settlement_rule_hash": "...",
  "raw_payload_hash": "..."
}
```

## 6.5 Source audit 重点

```text
1. 平台 API 是否稳定？
2. 历史 probability 是否可回放？
3. 合约 settlement rule 是否明确？
4. 合约是否有足够成交量/流动性？
5. 是否存在被单一大户操纵的风险？
6. contract title 是否能稳定分类？
7. probability 是否是 mid price、last price 还是 best bid/ask implied？
```

## 6.6 Replay 方案

分组：

```text
G1: macro probability shock
G2: crypto price threshold probability shock
G3: regulatory event probability shock
G4: ETF / institutional event probability shock
G5: prediction probability vs options-implied probability gap
```

观察资产：

```text
BTCUSDT
ETHUSDT
SOLUSDT
sector baskets if relevant
```

窗口：

```text
T+1h
T+4h
T+12h
T+24h
T+3d
```

指标：

```text
forward_return
realized_volatility
range expansion
volume expansion
options IV if available
funding / OI change
```

## 6.7 停止条件

```text
contract liquidity too low
settlement rule ambiguous
probability history unavailable
probability moves mostly manipulation/noise
no improvement over macro calendar baseline
no relation to crypto realized volatility or return
```

---

# P7. Stablecoin / Exchange Flow Shock

## 7.1 它是什么？

`stablecoin / exchange flow shock` 指链上资金进入或离开交易所，尤其是稳定币或主流资产的流向异常。

事件例子：

```text
USDT 大额净流入交易所
USDC 大额净流入交易所
BTC 大额净流入交易所
ETH 大额净流入交易所
某 whale deposit 到 Binance/OKX
stablecoin supply expansion
exchange reserve rapid change
```

## 7.2 为什么可能成为 alpha？

不同资产流入交易所含义不同：

```text
stablecoin 流入交易所:
  可能代表潜在买盘。

BTC/ETH/token 流入交易所:
  可能代表潜在卖压。

stablecoin 流出交易所:
  可能代表风险偏好下降或资金撤出。

BTC/ETH 流出交易所:
  可能代表长期持有或冷钱包迁移。
```

核心机制：

```text
链上资金流 -> 交易所可用购买力 / 潜在卖压 -> 市场状态变化
```

## 7.3 个人投资者是否适合？

```text
research_fit = high
execution_fit = medium_high
latency_dependency = medium
main_risk = address-label quality
```

这条线适合个人，因为不一定要秒级。  
但它严重依赖地址标签质量。

## 7.4 最小 schema

```json
{
  "event_type": "exchange_flow_shock",
  "chain": "ethereum|tron|solana|bitcoin|other",
  "asset": "USDT|USDC|BTC|ETH|other",
  "direction": "inflow|outflow",
  "exchange": "binance|okx|coinbase|bybit|unknown",
  "amount_token": 0.0,
  "amount_usd": 0.0,
  "flow_zscore": 0.0,
  "window_ms": 3600000,
  "tx_count": 0,
  "unique_sender_count": 0,
  "address_label_source": "...",
  "label_confidence": "high|medium|low",
  "available_at_ms": 0,
  "raw_payload_hash": "..."
}
```

## 7.5 Source audit 重点

```text
1. 交易所地址标签来源是否可信？
2. 是否能区分热钱包、冷钱包、内部转账？
3. 是否能排除交易所内部整理？
4. 多链 USDT/USDC 是否统一？
5. available_at_ms 是 block time 还是 indexer seen time？
6. 大额单笔是否会污染统计？
7. 是否能复现历史 flow？
```

## 7.6 Replay 方案

分组：

```text
G1: stablecoin exchange inflow spike
G2: stablecoin exchange outflow spike
G3: BTC/ETH exchange inflow spike
G4: token-specific exchange inflow spike
G5: whale deposit event
G6: multi-exchange synchronized flow
```

窗口：

```text
T+1h
T+4h
T+12h
T+24h
```

观察：

```text
BTC/ETH/SOL forward return
sector token return
realized volatility
volume expansion
funding/OI change
liquidation imbalance
```

## 7.7 停止条件

```text
address labels 不可信
内部转账无法剔除
历史数据不可复现
flow_zscore 只是大户单笔噪音
不优于 volume baseline
方向不稳定且无法用 context label 分层
```

---

# P8. ETF / Institutional Flow Shock

## 8.1 它是什么？

`ETF / institutional flow shock` 指传统资金流进入或离开 crypto 相关资产。

来源可能包括：

```text
BTC spot ETF daily flow
ETH spot ETF daily flow
大型基金持仓披露
corporate treasury BTC/ETH purchase/sale
institutional custody flow
public fund flow report
```

事件例子：

```text
BTC ETF 单日净流入超过 5 日均值 3 倍
BTC ETF 连续 5 日净流出
ETH ETF 流入转正
某上市公司宣布买入 BTC
某基金大幅减仓 crypto exposure
```

## 8.2 为什么可能成为 alpha？

这类事件影响的是传统资金的 crypto risk appetite。

可能路径：

```text
ETF 净流入 -> 现货购买压力 / risk appetite 上升
ETF 净流出 -> 赎回压力 / risk appetite 下降
连续流入 -> 趋势确认
连续流出 -> 风险偏好恶化
机构买入公告 -> narrative support
机构卖出公告 -> confidence shock
```

这类事件通常是日频，不是毫秒级，适合个人研究。

## 8.3 个人投资者是否适合？

```text
research_fit = high
execution_fit = medium_high
latency_dependency = low
main_risk = publication delay / already priced
```

适合研究：

```text
daily ETF flow extremes
multi-day inflow/outflow streak
flow reversal
BTC/ETH regime label
```

不适合：

```text
把每日流入直接当买入信号
忽略公布延迟
忽略宏观市场同步影响
```

## 8.4 最小 schema

```json
{
  "event_type": "etf_institutional_flow_shock",
  "asset": "BTC|ETH",
  "flow_source": "etf_daily_report|issuer|fund_disclosure|corporate_treasury",
  "flow_date": "YYYY-MM-DD",
  "published_at_ms": 0,
  "available_at_ms": 0,
  "net_flow_usd": 0.0,
  "aum_usd": 0.0,
  "flow_to_aum_pct": 0.0,
  "flow_zscore": 0.0,
  "flow_streak_days": 0,
  "direction": "inflow|outflow",
  "raw_payload_hash": "..."
}
```

## 8.5 Source audit 重点

```text
1. flow 数据发布时间是否稳定？
2. 是否有修正值？
3. 是否覆盖所有主要 ETF？
4. 不同来源是否一致？
5. available_at_ms 如何保守构建？
6. 是否能区分交易日和自然日？
7. 是否能和 BTC/ETH price bar 对齐？
```

## 8.6 Replay 方案

分组：

```text
G1: large single-day inflow
G2: large single-day outflow
G3: inflow streak
G4: outflow streak
G5: flow reversal
G6: ETF flow + BTC regime context
```

窗口：

```text
T+1d
T+3d
T+7d
```

指标：

```text
BTC/ETH forward return
realized volatility
drawdown
volume
funding/OI context
ETF flow continuation
```

## 8.7 停止条件

```text
flow data publication delay too high
flow signal does not outperform BTC regime baseline
flow effect fully explained by price momentum
single ETF dominates result
event count too low
```

---

# P9. Security Incident / Exploit / Depeg Events

## 9.1 它是什么？

这类事件包括：

```text
protocol exploit
bridge hack
oracle failure
stablecoin depeg
chain halt
major governance attack
exchange security incident
custodian failure
```

事件例子：

```text
某 DeFi 协议被盗
某 bridge 发生 exploit
某 stablecoin 脱锚
某 L1 停机
某 oracle 报价异常
```

## 9.2 为什么可能成为 alpha？

安全事故会触发：

```text
协议风险重估
流动性逃离
TVL 下降
相关生态 token 下跌
稳定币 depeg contagion
桥资产折价
链上拥堵和提现风险
```

但这类事件风险极高。  
第一版更适合做：

```text
risk veto
contagion diagnostic
avoidance signal
```

而不是做空或接飞刀。

## 9.3 个人投资者是否适合？

```text
research_fit = medium_high
execution_fit = low_to_medium
latency_dependency = high_for_first_reaction / medium_for_contagion
main_risk = extreme_gap_and_false_reports
```

适合：

```text
风险规避标签
不参与高风险生态
contagion 观察
stablecoin depeg monitoring
```

不适合：

```text
第一时间追空
接飞刀
链上抢跑撤流动性
依赖私钥/钱包执行
```

## 9.4 最小 schema

```json
{
  "event_type": "security_incident",
  "incident_type": "exploit|bridge_hack|oracle_failure|depeg|chain_halt|governance_attack",
  "source": "official|security_firm|chain_monitor|news|social",
  "source_url": "...",
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "affected_protocol": "...",
  "affected_chain": "...",
  "affected_assets": ["XYZ"],
  "estimated_loss_usd": 0.0,
  "severity": "critical|high|medium|low",
  "confirmed_status": "confirmed|unconfirmed|false_alarm",
  "contagion_scope": "single_protocol|ecosystem|cross_chain|stablecoin",
  "raw_payload_hash": "..."
}
```

## 9.5 Source audit 重点

```text
1. source 是否官方或安全公司？
2. false alarm 率如何？
3. 是否能区分 confirmed / unconfirmed？
4. 估算损失是否经常修正？
5. affected_assets 是否稳定解析？
6. available_at_ms 是否可靠？
7. 是否涉及私钥、钱包、交易 payload？如有必须 reject。
```

## 9.6 Replay 方案

分组：

```text
G1: confirmed critical exploit
G2: bridge hack
G3: stablecoin depeg
G4: chain halt
G5: oracle failure
G6: unconfirmed alert diagnostic only
```

窗口：

```text
T+1h
T+4h
T+12h
T+24h
T+7d
```

观察：

```text
affected token return
related ecosystem basket return
stablecoin deviation
DEX/CEX spread
liquidity withdrawal
volatility expansion
```

## 9.7 停止条件

```text
false alarm too high
source latency too slow
事件太少
affected_assets mapping 不稳定
第一反应全部在秒级完成且后续无结构
风险过高，只能作为 veto
```

---

# P10. Governance / Protocol / Tokenomics Events

## 10.1 它是什么？

这类事件包括：

```text
major protocol upgrade
fee switch proposal
tokenomics vote
emission reduction
staking unlock change
treasury sale proposal
DAO governance vote
protocol revenue distribution
L2 upgrade / hard fork
validator reward change
```

事件例子：

```text
某协议提案开启 fee switch
某 DAO 投票释放 treasury
某 L1 准备 major upgrade
某 tokenomics 改为减排
某 staking 解锁规则改变
```

## 10.2 为什么可能成为 alpha？

这类事件改变的是资产长期现金流、供给、治理风险或使用价值。

可能机制：

```text
fee switch -> token value capture 预期变化
emission reduction -> 未来供应压力下降
treasury sale -> 潜在卖压
staking unlock -> 流通供应变化
major upgrade -> 使用体验 / TVL / developer activity 改变
governance attack -> 风险重估
```

这类事件通常低频，更适合个人投资者研究。

## 10.3 个人投资者是否适合？

```text
research_fit = medium_high
execution_fit = medium
latency_dependency = low_to_medium
main_risk = semantic complexity
```

适合：

```text
日频 / 多日 replay
治理前后窗口
tokenomics change audit
```

不适合：

```text
读不懂 proposal 就交易
只看标题不看执行条件
忽略投票是否通过
忽略实际执行时间
```

## 10.4 最小 schema

```json
{
  "event_type": "governance_tokenomics_event",
  "event_subtype": "fee_switch|emission_change|treasury_sale|staking_change|protocol_upgrade|governance_vote",
  "protocol": "...",
  "chain": "...",
  "symbol": "XYZUSDT",
  "source_url": "...",
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "vote_start_ms": 0,
  "vote_end_ms": 0,
  "execution_time_ms": 0,
  "proposal_status": "draft|active|passed|failed|executed",
  "economic_direction": "supply_positive|supply_negative|cashflow_positive|risk_negative|unknown",
  "severity": "high|medium|low",
  "raw_payload_hash": "..."
}
```

## 10.5 Source audit 重点

```text
1. governance source 是否官方？
2. proposal 状态是否可追踪？
3. vote_end 和 execution_time 是否明确？
4. 事件语义是否能稳定分类？
5. proposal 是否后续修改？
6. 是否有链上执行 transaction？
7. token symbol mapping 是否稳定？
```

## 10.6 Replay 方案

锚点：

```text
available_at_ms
vote_start_ms
vote_end_ms
execution_time_ms
```

分组：

```text
G1: fee switch passed
G2: emission reduction
G3: treasury sale
G4: staking unlock change
G5: major protocol upgrade
G6: governance attack / failure
```

窗口：

```text
T+1d
T+3d
T+7d
T+14d
```

指标：

```text
forward_return
TVL change if available
volume
drawdown
volatility
relative performance vs sector basket
```

## 10.7 停止条件

```text
proposal status 无法追踪
事件语义无法稳定分类
execution_time 不明确
样本过少
结果由单协议贡献
不优于 sector baseline
```

---

# 11. 统一 Source Audit 模板

后续每个新热点事件源都应先写 source audit，不要直接 replay。

## 11.1 必须审计字段

```text
source_name
source_type
historical_data_available
timestamp_quality
available_at_policy_defined
raw_payload_storable
schema_stability
symbol_mapping_pass_rate
event_type_classification_pass_rate
forbidden_payload_count
hindsight_risk_level
sample_count
event_days
symbols_with_events
source_integrity_pass_rate
```

## 11.2 Source audit 通过门槛建议

```text
historical_events_found >= 30
event_days >= 10
symbols_with_events >= 3
source_integrity_pass_rate >= 0.95
symbol_mapping_pass_rate >= 0.95
available_at_policy_defined = true
forbidden_payload_count = 0
hindsight_risk_level != high
```

如果样本达不到：

```text
decision = source_audit_degraded_or_failed
replay_allowed = false
next_action = stop_or_collect_more_history
```

---

# 12. 统一 Replay 模板

## 12.1 Replay 前置条件

```text
source audit passed
minimal event table completed
available_at_ms defined
event_type not mixed
symbol mapping passed
hindsight risk controlled
forbidden payload count = 0
```

## 12.2 通用时间窗口

```text
T+1h
T+4h
T+12h
T+24h
T+3d
T+7d
```

日频事件可用：

```text
T+1d
T+3d
T+7d
T+14d
```

## 12.3 通用成本压力

```text
30 bps
50 bps
80 bps
```

## 12.4 通用 baseline

```text
same-symbol random baseline
same-day random baseline
BTC regime baseline
price momentum baseline
volume spike baseline
sector basket baseline
```

## 12.5 通用通过门槛

```text
event_count >= 30
event_days >= 10
symbols_with_events >= 3
median_net_return_after_50bps > 0
baseline_excess_net_bps > 0
price_or_sector_baseline_excess_net_bps > 0
left_tail_p05 not worse than random baseline
top_5_positive_events_gross_profit_share <= 0.40
max_single_day_event_share <= 0.30
max_single_symbol_event_share <= 0.60
```

---

# 13. 防止白忙活的 Kill Criteria

任何热点事件源只要满足以下任一条，直接停止或降级 observation-only：

```text
source 无法审计
available_at_ms 无法保守构建
historical data 不可复现
event_count < 30 且无法扩展
symbol mapping pass rate < 95%
hindsight risk high
bot/noise 无法控制
收益不优于 random baseline
收益不优于 price/sector baseline
成本后中位收益 <= 0
收益由单日/单币/top 5 极端事件贡献
live source latency 过高
盘口证据失败
需要 wallet / private key / API key / borrow inventory / VIP execution
```

---

# 14. 当前推荐下一步

在 Stage 1.5F 等待 futures launch 新事件的同时，可以并行准备新热点事件源路线。

建议两条轻量设计线：

```text
Stage 1.6B:
  sentiment_extreme_and_narrative_attention_source_selection_design

Stage 1.6C:
  prediction_market_probability_shift_source_schema_settlement_design
```

仍建议保留 P1 delisting 作为最务实的事件源扩展：

```text
Stage 1.6A:
  exchange_delisting_notice_source_schema_effective_time_design
```

推荐顺序：

```text
1. Stage 1.6A exchange_delisting_notice_source_schema_effective_time_design
2. Stage 1.6B sentiment_extreme_and_narrative_attention_source_selection_design
3. Stage 1.6C prediction_market_probability_shift_source_schema_settlement_design
4. Stage 1.6D stablecoin_exchange_flow_address_label_source_audit_design
5. Stage 1.6E ETF_institutional_flow_event_table_design
```

---

# 15. 最终边界

本文件列出的所有事件源都只能作为研究候选。

不允许输出：

```text
alpha_confirmed
trade_signal
paper_ready
live_ready
execution_feasibility_proven
```

最多允许输出：

```text
source_audit_passed
minimal_event_table_ready
historical_replay_completed
promising_cell_for_further_research
live_source_observation_allowed
live_depth_evidence_required
write_shadow_execution_simulator_design
```

一句话：

```text
这些热点事件源不是捷径。
它们只是比纯 OHLCV / funding / OI 更高信息密度的外部观察对象。
真正的边，必须由 source audit、replay、baseline、cost stress、live evidence 一步步证伪出来。
```
