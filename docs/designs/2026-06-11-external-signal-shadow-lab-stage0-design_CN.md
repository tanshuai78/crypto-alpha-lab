# External Signal Shadow Lab Stage 0 Design

日期：2026-06-11

## 1. 设计结论

External Signal Shadow Lab 的目标不是立刻寻找一个可上线交易策略，而是建立一条更快的外部机会验证管线：

```text
外部只读情报事件 -> 本地风险过滤 -> CUSUM 事件确认 -> 三重屏障 shadow order -> 30 天 forward shadow replay -> 决定是否进入正式策略研究
```

本阶段只允许产生研究标签和影子订单，不允许产生真实订单。

关键边界：

- 不接钱包；
- 不签名；
- 不下单；
- 不 swap；
- 不 copy trade；
- 不把外部 skill 的输出直接解释为交易指令；
- 不把 CUSUM / 三重屏障结果解释为策略通过。

本设计采纳 Springer 论文《Algorithmic crypto trading using information-driven bars, triple barrier labeling and deep learning》的两个方法论思想：

1. 使用信息驱动采样，避免机械地只按固定时间点交易；
2. 使用三重屏障法，将交易结果定义为“止盈 / 止损 / 最大持仓时间”中谁先触发，而不是简单预测下一根 K 线。

但是本项目不会直接复刻论文中的深度学习模型。Stage 0 只做事件采集、事件确认和 shadow label 基础设施。

参考论文链接：

https://link.springer.com/article/10.1186/s40854-025-00866-w

## 2. 为什么需要这个模块

过去的研究模式大致是：

```text
提出策略假设 -> 写下载器 -> 写回测 -> 跑历史结果 -> 证伪
```

这个流程严谨，但成本高。每条策略线都需要大量工程投入，最后经常发现：

- 信号没有超额；
- 收益被成本吃掉；
- 结果依赖单一月份；
- 结果只是 beta 暴露；
- 样本或数据源不可用；
- 外部可交易性不成立。

External Signal Shadow Lab 试图改变研究顺序：

```text
先收集大量外部候选事件；
先做轻量 shadow 后验评估；
只有出现稳定结构，再写正式策略。
```

它的核心价值是提高研究淘汰速度，而不是直接提高收益。

## 3. 外部信号的定义

外部信号不是交易指令。它只是一个候选事件。

候选来源包括：

- Gate marketanalysis 类市场结构信号；
- Binance Skills Hub 的 smart money、market rank、token audit、meme rush；
- OKX OnchainOS 的 dex signal、dex token、dex trenches、security；
- BofAI / TRON 生态的只读链上数据；
- 未来其他只读研究源。

候选事件统一为：

```json
{
  "event_id": "string",
  "source": "gate|binance_web3|okx_onchainos|bofai|internal",
  "source_skill": "string",
  "event_type": "smart_money_inflow|token_audit_pass|meme_migrated|liquidity_expansion|market_tape_anomaly",
  "chain": "ethereum|solana|bsc|base|tron|cex",
  "symbol": "BTCUSDT",
  "token_address": "string|null",
  "event_time_utc": "2026-06-11T00:00:00Z",
  "direction_hint": "long|short|avoid|unknown",
  "raw_score": 0.0,
  "notional_usd": 0.0,
  "liquidity_usd": 0.0,
  "risk_flags": [],
  "data_quality": "ok|degraded|unavailable",
  "shadow_only": true
}
```

`direction_hint` 不能直接变成订单方向。它只能进入后续确认流程。

## 4. Stage 0 范围

Stage 0 只做五件事：

1. 定义外部事件统一 schema；
2. 定义本地 Risk Guard 初筛；
3. 设计 CUSUM confirmation gate；
4. 设计三重屏障 shadow order；
5. 设计 30 天 shadow replay 的记录和判定。

Stage 0 不做：

- 真实交易；
- 深度学习；
- LightGBM；
- 钱包接入；
- 自动跟单；
- 自动生成实盘信号；
- 外部 skills 全量安装；
- on-chain execution。

## 5. 本地 Risk Guard 初筛

所有外部事件先经过本地 Risk Guard。

第一版硬 veto：

```text
token_audit_honeypot = true -> reject
rug_pull_risk = high -> reject
sell_tax_pct > 5% -> reject
liquidity_usd < 500_000 -> reject
top10_holder_share > 35% -> reject
smart_money_exit_rate > 70% -> reject
data_quality != ok -> reject_or_quarantine
```

对 CEX 大币事件，第一版 hard veto：

```text
spread_bps > 10 -> reject_or_reduce
depth_10bps_usd < 100_000 -> reject_or_reduce
recent_orderbook_coverage < 0.95 -> reject
price_coverage < 0.99 -> reject
```

Risk Guard 输出：

```json
{
  "event_id": "string",
  "risk_decision": "accept_for_shadow|reject|quarantine",
  "reject_reasons": [],
  "allowed_shadow_direction": "long|short|both|observe_only"
}
```

## 6. CUSUM Confirmation Gate

### 6.1 用途

CUSUM 不是 alpha。它是事件确认器。

外部情报源可能很吵：

- smart money 事件可能太早；
- social hype 可能是假热度；
- meme launch 可能没有真实买盘；
- liquidity expansion 可能只是短时刷量；
- CEX market anomaly 可能只是噪声。

CUSUM 用来回答：

```text
外部事件之后，价格是否真的发生了足够大的信息驱动变化？
```

如果没有触发 CUSUM，事件只记录，不生成 shadow order。

### 6.2 第一版定义

输入：

- event_time；
- symbol 或 token address；
- price series；
- direction_hint；
- volatility estimate；
- CUSUM threshold。

第一版采用对数收益：

```text
r_t = log(price_t / price_{t-1})
```

双边 CUSUM：

```text
s_pos_t = max(0, s_pos_{t-1} + r_t)
s_neg_t = min(0, s_neg_{t-1} + r_t)

if s_pos_t > threshold:
    trigger = positive_move

if s_neg_t < -threshold:
    trigger = negative_move
```

阈值第一版不调参搜索：

```text
threshold = max(
  fixed_threshold_bps,
  k * rolling_volatility
)
```

建议默认：

```text
fixed_threshold_bps = 30
k = 1.5
rolling_volatility_window = 60 minutes
confirmation_window = 30 minutes
```

如果 event_time 后 30 分钟内未触发 CUSUM：

```text
cusum_decision = no_confirm
```

如果触发：

```text
cusum_decision = confirmed
cusum_trigger_time = ...
cusum_direction = positive_move|negative_move
```

### 6.3 方向规则

如果外部事件是 long-biased：

```text
只接受 positive_move 触发；
negative_move 触发记为 adverse_confirm，不生成 long shadow order。
```

如果外部事件是 short-biased：

```text
只接受 negative_move 触发。
```

如果外部事件方向未知：

```text
只生成 observe_only label，不生成方向性 shadow order。
```

## 7. 三重屏障 Shadow Order

### 7.1 用途

三重屏障不是下单系统。它是 shadow 结果评估方法。

每个通过 Risk Guard 和 CUSUM confirmation 的事件，生成一个影子订单对象：

```text
entry_time = CUSUM trigger time 后的下一根可成交 bar
direction = long|short
take_profit = 上方收益屏障
stop_loss = 下方亏损屏障
vertical_barrier = 最大持仓时间
```

之后观察谁先发生：

```text
先触发 take_profit -> label = win
先触发 stop_loss -> label = loss
先到 max holding time -> label = timeout
```

### 7.2 第一版参数

第一版不做参数搜索，只做固定基准：

```text
take_profit_bps = 150
stop_loss_bps = 100
max_holding_minutes = 240
entry_delay_bars = 1
cost_round_trip_bps = 50
```

对 meme / low-liquidity token，参数要更保守：

```text
take_profit_bps = 300
stop_loss_bps = 150
max_holding_minutes = 120
min_liquidity_usd = 500_000
```

但 Stage 0 只定义 schema，不做参数优化。

### 7.3 Shadow Order Schema

```json
{
  "shadow_order_id": "string",
  "event_id": "string",
  "symbol": "BTCUSDT",
  "token_address": "string|null",
  "direction": "long|short",
  "entry_time_utc": "2026-06-11T00:05:00Z",
  "entry_price": 0.0,
  "take_profit_price": 0.0,
  "stop_loss_price": 0.0,
  "vertical_barrier_time_utc": "2026-06-11T04:05:00Z",
  "cost_round_trip_bps": 50.0,
  "status": "open|closed",
  "exit_time_utc": null,
  "exit_price": null,
  "exit_reason": "take_profit|stop_loss|vertical_barrier|null",
  "gross_return_bps": null,
  "net_return_bps": null,
  "max_adverse_excursion_bps": null,
  "max_favorable_excursion_bps": null
}
```

## 8. 30 天 Shadow Replay 的定义

### 8.1 是否必须实时数据 replay

不必须。

Shadow replay 有两种：

### A. Historical replay

使用历史事件和历史价格数据模拟 shadow order。

优点：

- 快；
- 可以立刻检查代码逻辑；
- 可以快速排除明显无效的事件类型。

缺点：

- 很多 skills 没有完整历史事件接口；
- 外部榜单可能存在幸存者偏差；
- 历史 hot token / smart money ranking 很难完整复原；
- API 当前返回的数据可能不是当时真实可见的数据；
- 容易产生 lookahead bias。

用途：

```text
用于工程验证和 sanity check，不能作为最终通过证据。
```

### B. Forward shadow replay

从今天开始，按固定频率采集外部事件，未来 30 天只记录不交易。

优点：

- 最接近真实使用环境；
- 不存在事后知道榜单的问题；
- 能观察 API 稳定性、限频、字段漂移；
- 能发现信号是否迟到。

缺点：

- 慢；
- 需要稳定采集；
- 30 天样本可能仍不足。

用途：

```text
作为是否进入正式策略研究的最低证据。
```

### 8.2 本项目采用的结论

Stage 0 允许 historical replay，但只作为开发验证。

真正判断一个外部事件源是否有研究价值，必须至少经过：

```text
30 天 forward shadow replay
```

或者：

```text
可证明 point-in-time 的历史事件数据 + 完整历史价格/流动性数据
```

如果外部事件源不能提供 point-in-time 历史数据，就不能用历史回测宣称有效。

## 9. Stage 0 输出文件

建议输出：

```text
data/external_signal_shadow/raw/events/YYYY-MM-DD.jsonl
data/external_signal_shadow/processed/confirmed_events.jsonl
data/external_signal_shadow/processed/shadow_orders.jsonl
reports/external_signal_shadow/stage0_data_coverage_summary.json
reports/external_signal_shadow/stage0_shadow_replay_summary.json
docs/reviews/YYYY-MM-DD-external-signal-shadow-lab-stage0-review_CN.md
```

Git 只提交：

```text
reports/*summary.json
docs/reviews/*.md
docs/designs/*.md
tests/*
src/*
```

不提交：

```text
data/**/*.jsonl
raw API payload
wallet data
API keys
```

## 10. Stage 0 数据源优先级

第一批只接只读源。

### P0：内部已有数据

- CEX price；
- orderbook；
- liquidation；
- funding；
- basis；
- route C1 live data。

用途：

验证 CUSUM / 三重屏障基础设施。

### P1：Gate marketanalysis 思路

不直接绑定 Gate。

先把它拆成内部指标：

- liquidity anomaly；
- slippage risk；
- basis dislocation；
- funding crowding；
- liquidation stress。

用途：

作为 market tape event。

### P2：Binance Web3

优先：

- `query-token-audit`
- `query-token-info`
- `crypto-market-rank`
- `trading-signal`
- `meme-rush`

用途：

生成链上候选事件。

### P3：OKX OnchainOS

优先：

- `okx-dex-token`
- `okx-dex-signal`
- `okx-dex-trenches`
- `okx-security`
- `okx-dex-market`

用途：

链上 token、holder、smart money、meme、security 事件。

## 11. Stage 0 成功标准

Stage 0 不要求策略赚钱。

成功标准：

```text
至少 2 类外部事件源可稳定采集；
事件 schema 可统一；
Risk Guard 可以过滤明显垃圾事件；
CUSUM confirmation 可以稳定生成 confirmed/no_confirm；
三重屏障 shadow order 可以复现 TP/SL/timeout；
historical replay 可跑通；
forward shadow 采集流程可运行；
没有任何真实交易路径。
```

Stage 0 失败标准：

```text
外部 API 不稳定；
字段不可复现；
事件无法 point-in-time；
无法映射到价格序列；
Risk Guard 缺关键字段；
CUSUM/三重屏障无法稳定落盘；
需要钱包或交易权限才能获得关键数据。
```

## 12. Stage 1 才允许回答的问题

Stage 1 在至少 30 天 forward shadow 后回答：

```text
哪些事件类型有正向后效？
哪些事件只是噪声？
哪些事件触发后风险更高？
Risk Guard 是否真的减少尾部亏损？
CUSUM confirmation 是否提高信号质量？
三重屏障下 TP/SL/timeout 的分布是否有结构？
```

如果没有事件类型通过 Stage 1，则停止 external signal 方向。

如果有事件类型通过，才进入：

```text
Stage 2 strategy candidate design
```

## 13. 对论文方法的采纳边界

论文支持了一个重要方向：

```text
信息驱动采样 + 三重屏障标签，比固定时间采样 + next-bar label 更贴近真实交易。
```

但不能从论文直接推出：

```text
我们的外部 skills 信号一定有效；
CUSUM + 三重屏障本身就是 alpha；
任何 token 都可以套同一套参数；
可以直接生成真实订单；
```

原因：

- 论文重点样本是 BTC/ETH；
- 使用 tick-level data；
- 样本区间是 2018-01 到 2023-06；
- 模型训练和参数敏感性是研究核心；
- 论文结果不能自动迁移到小市值 token、meme、DEX 低流动性资产；
- 我们当前目标是 shadow evaluation，不是 ML prediction。

因此，本项目只采纳两个工程思想：

```text
CUSUM = 事件确认器；
Triple Barrier = shadow 结果评估器。
```

## 14. 下一步建议

下一步应写：

```text
External Signal Shadow Lab Stage 0 Implementation Plan
```

第一版实现只做内部基础设施：

1. `src/research/external_signal_shadow/events.py`
2. `src/research/external_signal_shadow/risk_guard.py`
3. `src/research/external_signal_shadow/cusum.py`
4. `src/research/external_signal_shadow/triple_barrier.py`
5. `src/research/external_signal_shadow/replay.py`
6. `scripts/run_external_signal_shadow_stage0.py`

第一版 fixture 不调用真实外部 API。

等基础设施通过测试后，再单独写外部 skills connector plan。

最终原则：

```text
先证明管线正确；
再接外部数据；
最后才判断是否存在 alpha。
```
