# External Signal Shadow Lab 研究说明文档

日期：2026-06-13

## 1. 一句话结论

External Signal Shadow Lab 不是一个交易策略，也不是一个自动交易系统。它是一个“外部情报接入、标准化、隔离、回放、证伪”的研究框架。

它要解决的问题是：

```text
当我们从交易所 skills、公开 API、链上工具、排行榜、异动监控、smart money 标签等外部来源拿到信息时，如何判断这些信息是否有资格进入 alpha 研究，而不是直接变成交易冲动？
```

当前阶段的目标不是赚钱，而是建立一条安全、可审计、可回放、可快速否定的外部信号研究链路：

```text
外部数据源
-> raw payload
-> connector 标准化
-> Risk Guard / 安全隔离
-> observation / candidate event
-> 历史 replay / shadow replay
-> 统计 review
-> 决定是否继续、转向、或停止
```

最终目标是发现可验证的 alpha 候选，但 Stage 0 / Stage 1 本身不产生 alpha，也不允许 paper/live。

---

## 2. 为什么需要这个 Lab

本项目此前已经尝试过多条进攻型或半进攻型研究线：

```text
funding 极端
basis 扩大
liquidation shock
orderbook 变薄
price-only momentum
14d CMOM
BTC regime / cash fallback
```

多数结果显示：单独依赖 CEX 价格、funding、basis、liquidation、orderbook 等本地构造信号，很难形成稳定可用的进攻型 alpha。

这说明两个问题：

1. 继续只在本地 OHLCV / funding / liquidation / orderbook 上调参，边际价值下降。
2. 如果要提高研究成功率，需要引入外部信息维度，但必须防止外部信息直接污染交易系统。

External Signal Shadow Lab 的定位就是：

```text
把外部信息变成可研究事件，而不是把外部信息变成交易命令。
```

它吸收了 Gate / Binance / OKX / BofAI / AI-Trader 等外部 skills 或工具体系的启发，但不直接采纳它们的交易执行能力。

我们要采纳的是：

```text
只读数据能力
市场情报标签
链上风险标签
候选事件生成思路
shadow replay 流程
```

明确禁止采纳的是：

```text
钱包登录
私钥/签名
swap payload
真实订单
copy trade
paper account 自动下单
跟单执行
```

---

## 3. Lab 的核心边界

External Signal Shadow Lab 必须遵守以下边界：

```text
live_trading_enabled = false
exchange_paper_trading_allowed = false
execution_engine_allowed = false
wallet_required = false
api_key_required = false
alpha_interpretation_allowed = false，除非后续某个候选通过独立 review 明确提升
```

任何外部 payload 中出现以下字段，必须 reject：

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

Stage 0 / Stage 1 / Stage 1.2 当前只允许：

```text
research_shadow_replay_allowed = true
```

这里的 shadow replay 是本地研究记录，不是交易所 paper trading，也不是模拟撮合账户。

---

## 4. 已完成阶段总览

### 4.1 Stage 0：Shadow Replay 基础设施

Stage 0 建立的是“事件后评估引擎”。

它回答的问题：

```text
如果有一条外部事件，我们如何安全地评估事件之后的价格表现？
```

已完成能力：

```text
ExternalSignalEvent 标准事件结构
Risk Guard 过滤
CUSUM confirmation
Triple Barrier replay
no-CUSUM baseline branch
CUSUM-confirmed branch
fixture-only summary / review
```

Stage 0 review 结论：

```text
decision = external_signal_shadow_stage0_passed
failure_type = stage0_completed
```

但 Stage 0 明确不能推出：

```text
外部信号有效
CUSUM 可作为买入信号
三重屏障参数可用于实盘
paper/live 可以启用
```

### 4.2 Stage 1.0：File-backed Connector

Stage 1.0 建立的是“外部 raw payload 标准化入口”。

它回答的问题：

```text
外部来源的数据格式不统一，如何安全转换成项目内部标准事件？
```

已完成能力：

```text
读取 raw JSONL
source mismatch 检查
forbidden payload 递归检查
semantic dedup
raw_payload_hash
price mapping
available_at_ms
source latency
summary accounting
normalized events 输出
```

Stage 1.0 的核心价值：

```text
所有外部来源先变成文件和审计记录，而不是直接进入策略或执行引擎。
```

### 4.3 Stage 1.1：Manual Payload Dry Run

Stage 1.1 原本用于验证“真实手动整理外部 payload 能否接入 connector”。

执行后发现：

```text
手动写 JSONL 对用户不可持续
人工转换不可复现
真实 manual raw 与 fixture 容易混淆
```

因此 Stage 1.1 的价值主要是工程验证，不再作为长期主线。

保留结论：

```text
file-backed connector 可以处理 Gate-like payload
但不应要求用户长期手动整理 JSONL
```

### 4.4 Stage 1.2：Gate Public Read-Only Collector

Stage 1.2 用脚本替代手动 payload。

它回答的问题：

```text
我们能否稳定、无登录、无 API key、无交易权限地把 Gate 公开市场快照采集成可审计 raw payload？
```

已完成能力：

```text
逐 symbol 请求 Gate public REST ticker endpoint
只采 BTC_USDT / ETH_USDT / SOL_USDT / XRP_USDT / DOGE_USDT
生成 raw JSONL
保存 api_response_hash / endpoint / query / status / latency / response field names
保留 numeric raw strings 与 parse 状态
显式 --live-public-readonly 才能联网
mock/fixture 测试默认不联网
connector normalize
review 输出 observation-only 结论
```

Stage 1.2 review 结论：

```text
collector_minimal_pass = true
connector_minimal_pass = true
stage0_observation_handoff_ready = true
stage0_directional_replay_ready = false
event_density_alpha_valid = false
```

Stage 1.2 的关键边界：

```text
cex_market_snapshot 是定时市场快照
不是 alpha event
不是买入信号
不是卖出信号
不能进入 directional triple-barrier order
只能 observation-only
```

必须特别强调：

```text
Stage 1.2 只证明 external data ingestion 可行。
Stage 1.2 不证明 external signal 已经存在。
Gate ticker snapshot 只是低成本初筛材料，不是高信息密度 alpha 来源。
```

### 4.5 Stage 1.3：Candidate Signal Discovery

Stage 1.3 已完成真实历史 replay。

它回答的问题：

```text
能否从 Gate ticker snapshot / Binance proxy OHLCV 这种低维公开市场数据中，派生出值得进入 live smoke 的候选事件？
```

执行口径：

```text
historical_venue = binance_proxy
venue_proxy_used = true
symbols = BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT / DOGEUSDT
history = 180 days
bar_interval = 15m
bar_count = 86,400
random_baseline_trials = 500
primary_metric = 4h terminal return after 50bps round-trip cost
```

测试候选：

```text
volume_spike_1h
relative_strength_vs_btc
volume_confirmed_relative_strength
price_move_15m baseline
cross_symbol_rotation diagnostic
```

真实 replay 结论：

```text
decision = stage1_3_candidate_signal_discovery_completed
next_action = stop_gate_ticker_direction
research_result_valid = true
```

主要结果：

```text
volume_spike_1h: excess +4.23 bps，但 50bps 后中位收益 -48.96 bps
relative_strength_vs_btc: excess +1.01 bps，但 50bps 后中位收益 -52.29 bps
volume_confirmed_relative_strength: excess -8.59 bps，失败
price_move_15m: excess -0.40 bps，失败
cross_symbol_rotation: event_count = 0，未形成有效诊断
```

解释：

```text
低维 ticker / OHLCV 派生事件最多表现为“比匹配随机时刻少亏一点”，没有形成成本后中位正收益。
因此它们不能进入 Stage 1.4 live smoke，也不应继续调阈值续命。
```

Stage 1.3 的意义不是“找到了 alpha”，而是完成了一次低成本证伪：

```text
Gate ticker snapshot / Binance proxy OHLCV 的短周期 price-volume 派生方向，应停止扩展。
External Signal Shadow Lab 若继续，必须转向更高信息密度 source。
```

---

## 5. 当前到底收集了什么外部信号

严格说，当前还没有收集真正的 alpha signal。

当前收集的是：

```text
cex_market_snapshot
```

来源：

```text
Gate public REST spot ticker endpoint
```

采集对象：

```text
BTC_USDT
ETH_USDT
SOL_USDT
XRP_USDT
DOGE_USDT
```

每条 `cex_market_snapshot` 表示：

```text
在某个 available_at_ms 时刻，我们从 Gate 公开 API 看到某个 symbol 的市场快照。
```

它携带的主要信息包括：

```text
last price raw string
base volume raw string
quote volume raw string
change percentage raw string
parse status
api response hash
api endpoint / query
api latency
source URL
available_at_ms
```

它不表示：

```text
买入
卖出
动量信号
突破信号
资金费率套利信号
清算信号
orderbook 信号
```

它只是后续候选信号发现的原始观察材料。

---

## 6. 每类信号的意义与目的

### 6.1 当前已落地信号：cex_market_snapshot

含义：

```text
公开市场快照。
```

目的：

```text
验证外部公开数据是否能安全进入项目。
为后续构造 volume shock、relative strength、cross-symbol rotation 等候选事件提供基础数据。
```

当前状态：

```text
observation-only
不允许 directional replay
不允许 alpha interpretation
```

### 6.2 第一优先候选：volume_spike_1h

含义：

```text
某个 symbol 最近 1h quote volume 显著高于过去同类窗口。
```

可能市场假设：

```text
突然放量可能代表新信息进入市场，后续短周期可能有延续或反转结构。
```

风险：

```text
放量可能只是出货、清算、噪音或新闻已充分定价。
```

目的：

```text
判断成交量异常是否比纯价格动量更有信息含量。
```

### 6.3 第一优先候选：relative_strength_vs_btc

含义：

```text
某个 alt 在短周期内明显强于 BTC。
```

可能市场假设：

```text
资金可能从 BTC 轮动到某个 alt，短期相对强势可能延续。
```

风险：

```text
alt beta 很弱时，相对强势仍可能绝对亏损。
```

目的：

```text
避免只看单币涨幅，转而判断是否存在横截面资金轮动。
```

### 6.4 第一优先候选：volume_confirmed_relative_strength

含义：

```text
某个 alt 同时出现相对 BTC 强势，并伴随成交额异常放大。
```

可能市场假设：

```text
单纯涨幅可能是噪音，单纯放量可能是出货；相对强势 + 放量确认的组合信息密度更高。
```

风险：

```text
两个弱信号叠加不一定变成强信号；也可能只是更严格地筛选出少数追高事件。
```

目的：

```text
判断 Gate ticker 这种低维数据是否还能派生出比纯价格、纯成交量更强的组合事件。
```

### 6.5 降级为 baseline：price_move_15m

含义：

```text
某个 symbol 15 分钟价格变化超过预注册阈值。
```

降级原因：

```text
它本质上仍是短周期 price-only momentum / reversal。项目此前已经在 30d momentum、14d CMOM 等价格动量方向上看到明显不足，因此 price_move_15m 不应作为主候选。
```

用途：

```text
只作为 baseline，用来判断 volume_spike_1h 和 volume_confirmed_relative_strength 是否真的提供了额外信息。
```

### 6.6 降级为 diagnostic：cross_symbol_rotation

含义：

```text
多个主流币之间的成交额或相对强弱排名发生变化。
```

降级原因：

```text
当前 universe 只有 BTC/ETH/SOL/XRP/DOGE，横截面太小；BTC/ETH/SOL 高相关，DOGE/XRP 又常受事件驱动，独立统计力不足。
```

用途：

```text
只作为辅助诊断：当 volume_spike 或 relative_strength 触发时，观察是否存在轮动确认。
```

### 6.7 后续应转向的高信息密度 source

Stage 1.3 已经证伪低维 ticker / OHLCV 派生方向。后续不应继续围绕 `price / volume / change percentage` 调阈值，而应只考虑信息密度更高、且个人投资者仍可低频执行的外部 source。

优先级建议：

```text
P1: liquidation cluster / liquidation imbalance
P2: funding + OI crowding
P3: orderbook depth / imbalance snapshot
P4: listing / delisting / unlock / event calendar
P5: cross-exchange divergence
P6: on-chain smart money / whale flow
```

简要注释：

- `liquidation cluster`：清算集中爆发。比如某个时间窗口内多空爆仓额突然放大，可能代表杠杆仓位被强制出清。它比普通成交量更有信息量，因为清算不是自愿交易，常伴随短期流动性缺口。
- `liquidation imbalance`：多头清算和空头清算的不平衡。若多头清算远大于空头清算，可能表示下跌过程中杠杆多头被挤出；后续可能出现继续下跌或短线反弹，需要用 replay 判定。
- `funding + OI crowding`：资金费率和未平仓量共同显示仓位拥挤。`funding` 是永续合约多空之间支付的费率，`OI` 是 open interest，即未平仓合约规模。高 funding + 高 OI 往往表示多头拥挤，低/负 funding + 高 OI 可能表示空头拥挤。
- `orderbook depth / imbalance`：订单簿深度和买卖盘不平衡。`depth` 表示盘口附近有多少挂单能承接交易，`imbalance` 表示买盘/卖盘哪一边更厚。盘口变薄或单边失衡可能预示短期冲击更容易放大。
- `listing / delisting / unlock / event calendar`：交易所上线、下线、代币解锁、重大项目事件日历。它们是离散事件，不是连续价格噪声，通常比普通 ticker 更接近“外部信息”。
- `cross-exchange divergence`：不同交易所之间价格、成交量、盘口或 funding 出现差异。若某交易所先动，另一个交易所滞后，可能形成低频观察机会。但需要警惕手续费、提现/转账不可用、盘口深度和同步延迟。
- `on-chain smart money / whale flow`：链上大额钱包、标记聪明钱、交易所流入流出等行为。它信息量可能高，但也更依赖地址标签质量、链上延迟和 token 安全过滤。

仍然需要排除的方向：

```text
MEV / 抢跑
meme 新币首分钟狙击
需要钱包签名或 swap payload 的链上自动交易
秒级 orderbook 做市
跨所搬砖依赖快速充提
KOL/news 秒级抢跑
```

原因：这些方向即使有 alpha，也大概率需要低延迟、私钥、复杂执行或个人不可控的基础设施，不符合本项目的 L0 安全边界。

所有高信息密度 source 都不应直接交易，仍必须先进 External Signal Shadow Lab：

```text
raw payload -> connector -> available_at_ms -> safety checks -> historical replay -> review -> 决定是否 live smoke
```

---

## 7. 为什么不直接用 Gate/Binance/OKX skills 交易

Gate / Binance / OKX / BofAI 这些 skills 的价值在于：

```text
数据源
分析模板
风险标签
外部情报雷达
```

它们的风险在于：

```text
可能混有交易、钱包、swap、账户、签名、执行能力
输出可能是自然语言解释，不是稳定结构化数据
source latency 和 available_at_ms 未必清楚
同一 signal 的语义可能随产品变化
```

所以本项目的原则是：

```text
只采纳只读数据和研究思想
不采纳执行能力
不允许外部 skill 直接进入交易系统
```

外部来源必须经过：

```text
raw JSONL
connector normalize
forbidden payload check
available_at_ms
price mapping
summary accounting
review
```

---

## 8. 为什么 available_at_ms 很重要

任何外部事件都有两个时间：

```text
event_time_ms：事件声称发生的时间
available_at_ms：我们实际拿到这条信息的时间
```

如果事件发生在 10:00，但我们 10:18 才看到，回测用 10:00 入场就是未来函数。

因此 External Signal Shadow Lab 的原则是：

```text
所有 replay 必须以 available_at_ms 为信息可得时间锚点。
```

这不是运维洁癖，而是防止策略回测偷看未来。

不过，available_at_ms 的真实稳定性不需要一开始等 30 天。它可以通过短期 live smoke 验证。

---

## 9. 30d shadow replay 的定位

30d shadow replay 不应该作为所有候选的默认前置门槛。

它真正要防的是：

```text
历史过拟合
样本只在少数几天有效
信号未来不再出现
真实采集延迟破坏信号
真实 API 字段和历史模拟不同
单币/单日贡献过高
```

但以下问题不需要 30 天才能发现：

```text
API 字段是否存在
429 是否频繁
脚本是否能跑
available_at_ms 是否写入
网络失败是否 safe fail
```

这些用 1 天 live smoke，甚至几小时 smoke，就能发现大部分。

因此建议采用分层验证：

```text
历史 replay：快速筛掉垃圾方向
24h live smoke：验证真实采集链路
7d shadow：验证样本密度和短期稳定性
30d shadow：只给历史 replay 和 7d shadow 都有希望的候选
```

---

## 10. 为什么下一步重点不是继续 ticker 采集，而是 source 升维

当前最大的风险不是“没有 collector”，而是：

```text
没有高质量候选信号。
```

Stage 0 / Stage 1 / Stage 1.2 都是基础设施。它们让我们能安全研究外部数据，但它们不决定研究方向是否有价值。

Stage 1.3 已经回答了第一批低维候选问题：

```text
Gate ticker snapshot / Binance proxy OHLCV 派生的 volume_spike、relative_strength、volume_confirmed_relative_strength，没有形成可进入 live smoke 的成本后正收益结构。
```

因此下一阶段真正应该回答的问题变成：

```text
哪一类更高信息密度 source 最值得接入？
它代表什么市场假设？
是否可用公开只读或低权限数据获取？
是否能在个人投资者可执行的 15m / 1h / 4h 时间尺度上验证？
如果失败，是否能快速停止而不是继续搭管线？
```

因此下一步建议不是：

```text
继续实时采集 7 天
```

而是：

```text
Stage 1.4 不应直接 live smoke。
下一步应先写 High-Information Source Selection / Stage 1.4 Design。
```

它的目标不是新增一堆 collector，而是选择一个最值得研究的高信息密度 source，并定义最小可证伪 replay。

---

## 11. 下一阶段建议：高信息密度 source selection

建议正式名称：

```text
External Signal Shadow Lab Stage 1.4 High-Information Source Selection Design
```

核心目标：

```text
在停止 Gate ticker snapshot 派生方向后，选择一个更高信息密度 source，定义最小接入、最小 replay、最小停止条件。
```

推荐第一优先 source：

```text
liquidation cluster / liquidation imbalance
```

理由：

```text
清算是强制交易，不是普通成交量。
它通常发生在杠杆拥挤和流动性断层附近。
项目已有 liquidation 相关历史研究和脚本资产，复用成本低。
可以用 15m / 1h / 4h 低频 replay 验证，不必进入秒级执行竞赛。
```

备选 source：

```text
funding + OI crowding
orderbook depth / imbalance snapshot
listing / unlock / event calendar
```

下一阶段不应做：

```text
继续调整 volume_spike 阈值
继续扩大 ticker symbol universe
直接进入 24h live smoke
一次性接入多个 source
接入需要私钥、钱包、swap payload 或交易权限的工具
```

---

## 12. 后续高信息密度 source 必须回答的问题

每个新 source 和候选信号必须回答：

```text
它代表什么市场假设？
触发条件是什么？
需要哪些字段？
是否只依赖未来数据？
事件样本数是否足够？
是否覆盖多个 symbol？
是否覆盖多个日期？
与随机 baseline 相比是否有改善？
扣 30/50/80 bps 后是否仍有空间？
是否只靠单个 symbol 或单日贡献？
是否只靠 top 5 极端事件贡献？
MFE / MAE / left tail 是否可接受？
失败后是否停止？
```

不能接受的研究方式：

```text
跑很多参数，然后挑最好的
失败后不断改阈值救结果
只报告收益，不报告样本数和集中度
把 observation-only 事件解释成交易信号
```

---

## 13. 后续候选信号通过门槛建议

第一版建议硬门槛：

```text
event_count >= 100
symbols_with_events >= 3
event_days >= 20
max_single_symbol_event_share <= 0.50
max_single_day_event_share <= 0.20
top_5_events_pnl_share <= 0.30
random_baseline_trials >= 500
entry_delay_bars >= 1
baseline_comparison_required = true
cost_scenarios_bps = 30 / 50 / 80
alpha_interpretation_allowed = false until review approved
```

候选信号要进入下一阶段，至少需要：

```text
相对随机 baseline 有明确改善
不是单币/单日/top 5 极端事件贡献
成本后仍有空间
回撤或尾部亏损没有明显恶化
结果可由固定预注册规则复现
```

后续 source-specific replay review 至少要输出：

```text
forward_return_15m
forward_return_1h
forward_return_4h
MFE
MAE
median_return
trimmed_mean_return
left_tail_p05
hit_rate_vs_random_baseline
top_5_events_pnl_share
max_single_day_contribution
```

如果候选只是“少亏一点”，但仍远差于 BTC/ETH 或 universe baseline，不能晋级。

固定 30/50/80 bps 成本只是最低摩擦测试。对短周期冲击类信号，还应报告更保守的 gap/slippage stress，但 stress 结果不应被用来事后调参。

---

## 14. 如果候选信号都失败怎么办

这条线不能无限续命。

需要区分三种失败：

### 14.1 信号无效

表现：

```text
样本足够
回放完整
但所有候选都没有超额结构
```

决策：

```text
停止 Gate ticker snapshot 派生信号方向。
```

### 14.2 数据维度太弱

表现：

```text
ticker / volume / change percentage 信息不足
无法形成更强候选
```

决策：

```text
转向更高信息密度数据源。
```

候选高信息密度来源：

```text
liquidation aggregate
funding / OI crowding
orderbook depth / imbalance
listing / unlock / event calendar
cross-exchange divergence
on-chain smart money
holder concentration
token audit
news/social propagation
```

### 14.3 框架不适合个人执行

表现：

```text
信号可能存在，但需要低延迟、抢跑、MEV、复杂跨所执行、大额盘口深度。
```

决策：

```text
停止，不做个人不可执行的 alpha。
```

---

## 15. 路线图

当前建议路线：

```text
Stage 0: Shadow Replay Engine
状态：完成
作用：评估事件后续表现

Stage 1.0: File-backed Connector
状态：完成
作用：把外部 raw payload 标准化

Stage 1.1: Manual Payload Dry Run
状态：完成，但不作为长期路线
作用：验证 connector 能处理 Gate-like payload

Stage 1.2: Gate Public Read-Only Collector
状态：完成
作用：脚本自动采集公开只读快照

Stage 1.3: Candidate Signal Discovery
状态：完成
作用：验证 Gate ticker snapshot / Binance proxy OHLCV 是否能派生短周期候选 alpha
结论：低维 price-volume 派生方向未通过；停止 Gate ticker snapshot 派生扩展

Stage 1.4: High-Information Source Selection
状态：下一步建议
作用：在 liquidation / funding+OI / orderbook / event calendar 等 source 中选择一个最小可证伪方向
边界：一次只选一个 source，不扩多个 collector，不接执行能力

Stage 1.5: Source-specific Connector / Historical Replay
状态：后置
作用：对 Stage 1.4 选中的 source 建立只读 connector 和历史 replay

Stage 2: 7d / 30d Shadow Validation
状态：只对通过 source-specific historical replay 和 24h live smoke 的候选开放
作用：验证未来真实环境下是否仍有结构

Stage 3: Strategy Candidate Design
状态：极少数候选才允许进入
作用：定义 entry/exit/stop/sizing/risk，不直接 live
```

---

## 16. 需要其他 AI agent 审核的问题

请其他 reviewer 重点判断以下问题：

1. 这条研究线的逻辑是否自洽？
2. Stage 0 / Stage 1 / Stage 1.2 是否只是基础设施，而没有被误读为 alpha？
3. `cex_market_snapshot` 是否应保持 observation-only？
4. Stage 1.3 是否足以停止 Gate ticker snapshot 派生方向？
5. 下一步是否应该优先选择 `liquidation cluster / liquidation imbalance`？
6. `funding + OI crowding`、`orderbook imbalance`、`event calendar` 哪个更适合作为备选？
7. 高信息密度 source 的历史 replay 应如何定义 baseline？
8. 通过门槛是否仍沿用 event_count / event_days / symbol coverage / random baseline / cost stress？
9. 30d shadow replay 是否仍应后置到 historical replay 和 24h smoke 之后？
10. 哪些外部 source 最适合个人投资者继续研究，哪些应直接排除？

---

## 17. 当前判断

External Signal Shadow Lab 值得继续，但 Gate ticker snapshot / Binance proxy OHLCV 的低维短周期 price-volume 派生方向应停止。

它的下一步重点必须从：

```text
继续调 ticker / volume 阈值
```

转向：

```text
选择一个高信息密度 source，并用最小 replay 快速证伪
```

Stage 1.3 已经给出停止 Gate ticker snapshot 派生方向的证据：候选事件样本足够、覆盖多币和多日，但成本后中位收益仍为负，组合候选也未跑赢匹配随机基准。

当前推荐决策：

```text
decision = proceed_to_stage1_4_high_information_source_selection_design
preferred_first_source = liquidation_cluster_or_liquidation_imbalance
collector_expansion_allowed = false
live_shadow_required_now = false
historical_replay_first = true
alpha_interpretation_allowed = false
```

更高层判断：

```text
这条线有希望的地方在于引入外部信息维度。
这条线最大的风险在于外部信息本身信息量不足，或个人投资者无法执行。
```

因此，External Signal Shadow Lab 的正确价值不是“直接给交易信号”，而是：

```text
快速发现哪些外部信息值得研究，哪些应该尽早淘汰。
```
