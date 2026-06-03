# Route C：爆仓后风险过滤研究设计

**日期：** 2026-06-02

## 1. 核心定位

Route C 不是对前面失败的“爆仓方向策略”的简单延续。

前一轮研究问的是一个很窄的方向问题：

> 1m 爆仓冲击之后，能不能预测接下来 5/10/15 分钟的价格方向？

这个问题没有被当前数据确认。失败原因既包括数据源限制，也包括方向响应结构本身不强。

Route C 要换一个问题：

> 爆仓压力出现之后，市场是否变得更危险、更不适合正常交易？

这是一个更低阶、也更贴近实盘的问题。它不要求预测上涨或下跌，只要求证明：爆仓后的窗口比普通匹配窗口有更差的执行环境和更高的风险。

如果验证成立，Route C 第一阶段应该先成为 **风险过滤器 / 执行保护层**，而不是独立 alpha 策略。

潜在实盘用途：

- 爆仓冲击后暂停新开仓；
- 市场不稳定时降低下单 notional；
- 提高滑点预留；
- 盘口不稳定时禁用 maker entry；
- 禁止在强制波动之后追单；
- 触发临时 risk-off；
- 将 liquidation context 接入后续 regime 或 alpha 模型。

这与当前系统的资金保护逻辑一致：Route C 可以先提升交易质量，而不是增加新的方向暴露。

---

## 2. 为什么 Route A/B 失败后仍然需要 Route C

### 2.1 前面失败了什么

原始 liquidation 策略线试图验证：

- 1m liquidation shock event；
- 固定 5/10/15m response；
- 方向延续或反转；
- 5 个币种 universe：BTC、ETH、SOL、XRP、DOGE。

关键失败点：

- Coinalyze 路线缺少可靠的 1m 连续性；
- Binance Vision snapshot 不是完整逐笔爆仓 tape；
- Binance snapshot 路线没有通过完整 5-symbol universe integrity；
- 缩窄后的 proxy sample 也没有确认方向结构；
- Route A complete-quarter screening 在 2023-Q1 到 2024-Q1 没有找到干净的 BTC/ETH/SOL 完整季度。

正确结论不是：

> liquidation 数据没有用。

更准确的结论是：

> liquidation 数据尚未证明自己可以作为简单固定窗口方向 alpha。

Route C 是对这个结果的纪律化响应。

### 2.2 为什么风险过滤比方向预测更合理

爆仓事件是强制成交。它通常伴随：

- 波动率扩大；
- 快速价格跳动；
- spread 扩大；
- 盘口深度临时撤退；
- market order impact 上升；
- 止损级联；
- maker adverse selection；
- 后续延续/反转不稳定。

这些现象即使在方向不可预测时也可能存在。

通俗讲：

- 市场可能没有告诉我们它接下来往哪走；
- 但它可能告诉我们：现在不是正常入场的好时机。

这正是 Route C 要验证的问题。

---

## 3. Route C 的三个阶段

Route C 有三个阶段。它们不是三个并列的独立策略。

推荐解释：

1. **C1：Post-Liquidation Volatility / Liquidity Filter**
   - 风险模块；
   - 第一优先级；
   - 最贴近实盘用途。

2. **C2：Episode Pressure**
   - 事件定义升级；
   - 把单分钟弱 shock 改造成多分钟压力 episode。

3. **C3：Context-Conditioned Directionality**
   - alpha 验证层；
   - 过拟合风险最高；
   - 只有在 C1/C2 产生稳定事件标签之后才应该做。

## 4. C1：爆仓后波动率 / 流动性过滤器

### 4.1 目的

C1 问的是：

> liquidation event 之后，波动率、不利波动、spread、depth 或 impact cost 是否显著恶化？

C1 不问：

> 能不能预测价格方向？

### 4.2 为什么 C1 要先做

C1 是最实用的分支，因为它可以在不引入新 alpha 依赖的情况下改进当前系统。

如果 liquidation pressure 能稳定预示更差的执行环境，系统就可以用它阻断或降级高风险交易。

这直接对应当前系统已有约束：

- slippage tolerance；
- impact cost filter；
- liquidity monitor；
- entry cooldown；
- risk-off controls；
- net exposure protection；
- orderbook-aware execution。

### 4.3 事件定义

初始事件：

- symbol 属于 BTC/USDT、ETH/USDT、SOL/USDT、XRP/USDT、DOGE/USDT；
- 1m liquidation notional 超过滚动阈值；
- 阈值基于 trailing 24h 或 30d 分布；
- 保留方向字段：`long_liquidation` / `short_liquidation`；
- event timestamp 对齐到 1m bucket。

注意：C1 不把 event side 当成交易方向。

### 4.4 后续窗口指标

价格指标：

- `realized_vol_5m`；
- `realized_vol_10m`；
- `realized_vol_15m`；
- `realized_vol_30m`；
- `high_low_range_5m_bps`；
- `high_low_range_15m_bps`；
- `max_adverse_excursion_5m_bps`；
- `max_adverse_excursion_15m_bps`；
- `jump_return_abs_bps`；
- `stop_loss_overrun_proxy_bps`。

Orderbook 指标：

- `bid_ask_spread_bps`；
- `top1_depth_usdt`；
- `top5_depth_usdt`；
- `depth_within_5bps_usdt`；
- `depth_within_10bps_usdt`；
- `depth_within_20bps_usdt`；
- `orderbook_imbalance`；
- `estimated_impact_cost_500usdt_bps`；
- `estimated_impact_cost_1000usdt_bps`；
- `estimated_impact_cost_2000usdt_bps`；
- `maker_adverse_selection_proxy`。

由这些指标派生出的执行风险动作：

- `pause_entry`；
- `reduce_notional`；
- `increase_slippage_reserve`；
- `disable_maker_first`；
- `force_taker_only_with_small_size`；
- `risk_off_cooldown`。

### 4.5 Baseline 比较方式

C1 不能把 liquidation 窗口和所有随机分钟粗暴比较。

必须使用 matched baseline：

- 同 symbol；
- 同 exchange；
- 同 month；
- 尽量同 time-of-day bucket；
- 相似的 pre-event 30m volatility percentile；
- baseline lookback window 内没有 liquidation shock。

这样可以避免错误结论：liquidation event 看起来危险，只是因为它本来就发生在高波动时段。

### 4.6 Continue / Stop 标准

继续 C1 的条件：

- post-event realized volatility median >= matched baseline median * 1.5；
- post-event P75/P90 adverse excursion 明显高于 baseline；
- event 后 spread 或 impact cost 恶化；
- BTC/ETH/SOL 至少 2 个 symbol 成立；
- by-month 不崩；
- orderbook 恶化能在 event 后 1/5/10/15m 内观察到。

停止或降级 C1 的条件：

- post-event volatility 与 matched baseline 没有显著差异；
- 只在单个 symbol 成立；
- 只在单个月份成立；
- orderbook 指标没有恶化；
- 排除本来就高波动的 baseline window 后效果消失。

### 4.7 预期输出

C1 的第一版输出应该是 risk-filter summary，不是 PnL 回测。

必要字段：

```json
{
  "decision": "continue_route_c1|stop_route_c1|needs_more_forward_data",
  "data_window": "...",
  "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
  "event_count": 0,
  "matched_baseline_count": 0,
  "post_event_vol_ratio_median": 0.0,
  "post_event_mae_p90_bps": 0.0,
  "baseline_mae_p90_bps": 0.0,
  "spread_deterioration_ratio_median": 0.0,
  "impact_cost_deterioration_ratio_median": 0.0,
  "symbols_passing": [],
  "months_passing": [],
  "recommended_live_action": "observe_only|pause_entry|reduce_notional|risk_off"
}
```

---

## 5. C2：Episode Pressure

### 5.1 目的

C2 问的是：

> 多分钟 liquidation pressure episode 是否比单个 1m shock 更有信息量？

单分钟 shock 可能只是噪音。真正的 liquidation cascade 往往是一个过程，而不是一根 K 线。

### 5.2 为什么 C2 在 C1 之后

C2 会增加复杂度。只有当 C1 证明 liquidation pressure 有风险过滤价值之后，才值得做 C2。

如果 C1 失败，就没有太大必要继续工程化更复杂的 episode。

如果 C1 成功，C2 可以提高事件质量：

- 减少孤立 false positive；
- 提供更好的 pressure duration 信号；
- 更好地连接执行恶化；
- 给后续方向研究提供更干净的标签。

### 5.3 Episode 定义

初始 episode 规则：

- rolling window：3 到 10 分钟；
- 至少 N 个 liquidation-positive minutes；
- same-side pressure ratio >= 阈值；
- total liquidation notional 高于 percentile 阈值；
- 允许 1 分钟短 gap；
- pressure 衰减到阈值以下后 episode 结束。

候选字段：

- `episode_start_ms`；
- `episode_end_ms`；
- `episode_duration_min`；
- `dominant_side`；
- `same_side_ratio`；
- `episode_total_notional_usdt`；
- `peak_1m_notional_usdt`；
- `pressure_decay_rate`；
- `price_displacement_during_episode_bps`；
- `post_episode_vol_15m`；
- `post_episode_mae_15m_bps`；
- `post_episode_spread_deterioration`。

### 5.4 C2 的用途

C2 服务两个方向：

1. 改进 C1 风险过滤器：
   - 更长 pressure episode 可能需要更长 cooldown；
   - 更强 same-side pressure 可能需要更激进的 notional reduction。

2. 为 C3 方向测试做准备：
   - 如果 episode 比单分钟 shock 更干净，方向测试应该使用 episode。

### 5.5 Continue / Stop 标准

继续 C2 的条件：

- episode 比 1m shock 减少 false positive；
- post-episode risk metrics 强于 post-single-shock metrics；
- event density 仍然可用；
- 至少 2 个 symbol 有足够 episode；
- by-month 稳定性可接受。

停止 C2 的条件：

- episode 规则过于稀疏；
- 参数选择很脆弱；
- 只有激进调参后才出现效果；
- episode label 没有改善 C1 风险信号。

---

## 6. C3：条件化方向性验证

### 6.1 目的

C3 问的是：

> liquidation pressure 是否只在某些预先锁定的市场上下文里有方向价值？

这是 Route C 中最接近 alpha 的部分。

它不应该第一步就做，因为过拟合风险最高。

### 6.2 为什么 C3 风险高

前面的方向分支已经在简单固定窗口定义下失败。

如果我们马上开始按以下条件切样本：

- trend；
- funding；
- OI；
- volatility；
- symbol；
- side；
- time of day；
- episode strength；

很容易只是挖出一个碰巧为正的小 bucket。

所以 C3 必须使用预先锁定的 contexts，并做 walk-forward evaluation。

### 6.3 允许使用的 Context

只能使用分析前已经定义好的 context：

- previous 30m return direction；
- previous 30m realized volatility percentile；
- funding positive / negative / extreme；
- OI expanding / contracting；
- price above / below short moving average；
- orderbook imbalance regime；
- spread-normal / spread-wide regime。

看到结果之后新增的 context，只能标记为 exploratory，不能用于最终确认。

### 6.4 C3 输出

C3 应输出：

- directional ratio by context；
- 扣除 fees 和 slippage 后的 PnL proxy；
- event count by bucket；
- month split；
- symbol split；
- walk-forward stability；
- 被拒绝 context 及原因。

要升级为策略，必须满足：

- 每个 bucket 有足够事件；
- out-of-sample 稳定；
- 扣除执行成本后仍有净 edge；
- 不隐含增加 net exposure；
- live 前经过 shadow-mode 验证。

---

## 7. 已有数据资产

## 7.1 Live Liquidation Collector

服务器上的 collector 已经开始接收真实 Binance forceOrder 事件。

这条数据链仍然有用，应该继续运行。

最低采集周期：

- 7 天：只能验证 collector 稳定性；
- 30 天：可做第一版 forward Route C1 risk study；
- 90 天：可以做更强的 regime-aware Route C study；
- 更长：如果存储和运维允许，长期不停更好。

不要停止 collector，除非它正在写坏数据或阻塞更高优先级基础设施。

必要 live liquidation 文件：

- raw append-only liquidation events；
- 1m zero-filled aggregate；
- 5m aggregate；
- 1h compatibility aggregate；
- health summary。

## 7.2 Binance Vision Historical Snapshot Data

这份数据仍然有用，但只能作为 proxy。

已知限制：

- Binance liquidation snapshot 不是完整逐笔 liquidation tape；
- 它更接近每个 symbol 每秒最大 force-order snapshot；
- 不能解释为市场真实 total liquidation notional。

适合用于：

- 探索性 Route C1 price-risk study；
- event density 估算；
- pressure-label 原型。

不适合用于：

- 最终 full-market liquidation-volume 结论；
- 强 live alpha 声明；
- total liquidation notional 解释。

## 7.3 Historical Orderbook Data

Orderbook 数据位于：

```text
/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook
```

已观察到的覆盖：

- Binance 和 OKX；
- BTCUSDT、ETHUSDT、SOLUSDT、XRPUSDT、DOGEUSDT、ADAUSDT；
- 同时存在 funding 文件；
- 每个 exchange-symbol 大约 74 个 daily files；
- BTC/ETH/SOL 覆盖大约为 2026-02-10 到 2026-05-08。

这对 Route C 有价值，但必须先做 time-overlap audit。

潜在用途：

1. 如果 orderbook 日期与 liquidation events 重叠：
   - 直接做 post-liquidation liquidity deterioration study。

2. 如果 orderbook 日期与 liquidation events 不重叠：
   - 构建正常 liquidity baseline；
   - 定义 spread/depth/impact metrics；
   - 估计 execution-risk 阈值；
   - 等待 forward liquidation + orderbook 产生重叠。

重要归一化问题：

- Binance 样本通常更深，现有文件里常见约 20 档；
- OKX 样本可能档位更少；
- 所以应比较 depth within bps 和 impact cost，不应直接比较 raw level count。

---

## 8. 从失败分支复用的经验

## 8.1 来自 Extreme Funding

可复用经验：

- 信号强度不够，必须经过 funding、basis、fees、execution friction 检验；
- `depth_aware=false` 是重大研究限制；
- reject-reason distribution 很有用，应继续保留；
- funding 更适合作为 context，而不是强行作为独立 trigger；
- shadow result 必须区分 proxy research 和 live-executable evidence。

Route C 复用方式：

- 把 funding 作为 C3 context，而不是 C1 trigger；
- 用 orderbook depth 让 C1 execution-aware；
- 输出 blocker distribution：
  - event density 不足；
  - 没有 matched baseline；
  - 没有 orderbook overlap；
  - spread effect absent；
  - impact effect absent；
  - symbol instability；
  - month instability。

## 8.2 来自 Vol-Breakout

可复用经验：

- 高波动即使不能盈利，也可能代表危险；
- 小时级退出会隐藏 sub-hour jump 和 stop-loss overrun；
- 稀疏事件密度让独立 alpha 不具吸引力；
- 放宽阈值制造交易通常会恶化尾部风险。

Route C 复用方式：

- 聚焦 MAE、jump risk、adverse excursion；
- 用 1m/5m 粒度衡量风险窗口，而不是只看小时收盘；
- 把高波动窗口作为 no-trade zone 候选；
- 不要只因为 median 可接受就升级信号，必须检查 P75/P90/P95 尾部。

---

## 9. Route C 所需数据

## 9.1 C1 Price-Only Study 最小数据

必要数据：

- 1m price bars；
- 1m liquidation aggregates；
- symbol；
- timestamp；
- liquidation side；
- liquidation notional proxy；
- zero-filled non-event minutes；
- matched baseline windows。

没有 orderbook 也能跑，但结论更弱。

## 9.2 C1 Execution-Risk Study 推荐数据

必要数据：

- 所有 C1 最小数据；
- orderbook snapshots；
- top-of-book bid/ask；
- depth levels；
- exchange；
- timestamp；
- funding rate optional；
- mark price optional。

Orderbook 采样目标：

- 第一版 Route C 研究中，每秒 1 个 snapshot 足够；
- 100ms feed 可以下采样到 1s 后分析；
- 如果存储允许，应保留 raw daily files。

## 9.3 C2 所需数据

必要数据：

- C1 liquidation aggregate；
- side-aware pressure；
- per-minute notional；
- episode 期间 price displacement；
- post-episode price 和 liquidity metrics。

推荐数据：

- event-level raw liquidation archive，用于 dedup 和 side validation。

## 9.4 C3 所需数据

必要数据：

- C2 episode labels；
- funding context；
- OI context，如果可用；
- pre-event return context；
- pre-event volatility context；
- orderbook imbalance context，如果可用。

推荐数据：

- by-month walk-forward split；
- out-of-sample validation windows。

---

## 10. 服务器数据采集决策

## 10.1 Liquidation Collector 是否继续运行

是，继续运行。

Liquidation collector 现在正在产生我们最干净的 forward liquidation archive。

运维目标：

- 持续运行；
- 监控 raw row count；
- 监控 invalid JSON lines；
- 监控 1m aggregate coverage；
- 监控 24h research readiness；
- 把 raw 数据作为 append-only evidence 保存。

最低有效周期：

- 30 天：第一版 forward Route C1 study；
- 90 天：更强 regime study。

## 10.2 Orderbook Collector 是否重启

是，但不要盲目重启。

重启前必须修正或确认 retention policy。

当前项目配置显示：

```text
COLLECTOR_DATA_RETENTION_DAYS = 14
```

这对研究太短。如果直接以该设置长期运行，旧 orderbook 文件会在日期轮转时被删除，不适合 Route C。

建议重启前改造：

- retention 至少设为 90 天；或
- 禁用自动删除，把清理改成人工归档策略；或
- 写入按日期归档目录并补 checksum。

推荐 orderbook 采集范围：

- Binance USDT perp：BTCUSDT、ETHUSDT、SOLUSDT、XRPUSDT、DOGEUSDT；
- OKX swaps：如果带宽允许，采同样 symbols；
- 第一版 Route C 用 1s write interval 足够；
- funding collection 保持开启；
- ADA 只有为了旧系统连续性才需要，不是 Route C core。

## 10.3 还需要采集什么

第一优先级：

- live forceOrder raw events；
- 1m/5m zero-filled liquidation aggregates；
- 同 symbols 的 Binance orderbook snapshots；
- 同 symbols 的 1m price bars。

第二优先级：

- OKX orderbook snapshots，用于 cross-exchange liquidity stress comparison；
- funding rate；
- mark price。

第三优先级：

- open interest；
- taker buy/sell volume；
- long/short account ratio，如果有可靠 vendor。

在确认 C1 数据重叠之前，不要让服务器同时接太多新数据源。

---

## 11. 研究执行顺序

### Batch 0：Data Overlap Audit

目标：

- 验证 liquidation events 和 orderbook snapshots 是否有时间重叠。

检查项：

- liquidation raw earliest/latest timestamp；
- 1m aggregate earliest/latest timestamp；
- orderbook earliest/latest timestamp by exchange-symbol；
- overlap hours by symbol；
- missing orderbook days；
- missing liquidation days。

决策：

- overlap >= 7 天：启动 C1 paired study；
- overlap < 7 天：继续采集器，只构建 metric adapters/baselines。

### Batch 1：C1 Price-Only Baseline

目标：

- 测试 liquidation events 是否提高 realized volatility、range 和 MAE。

为什么先做：

- 不需要足够 orderbook overlap 也能跑；
- 可以验证 Route C 是否有基础风险信号。

### Batch 2：C1 Orderbook-Aware Study

目标：

- 测试 liquidation events 后 spread、depth、impact cost 是否恶化。

这是 Route C1 的核心证明。

### Batch 3：C2 Episode Pressure

目标：

- 用多分钟 pressure labels 替代孤立 1m shock。

只有 C1 显示风险过滤价值后才做。

### Batch 4：C3 Context-Conditioned Directionality

目标：

- 在预先锁定的 context 下测试方向结构。

只有 C1/C2 提供稳定事件标签和足够样本后才做。

---

## 12. 升级规则

Route C 不能直接进入 live trading。

升级路径：

1. Research summary 通过 C1 risk criteria。
2. 加入 shadow-only filter。
3. 系统记录哪些交易本应被暂停/降级。
4. 对比 blocked trades 与 allowed trades。
5. 至少经过一个 scan cycle 的 shadow mode 后，才考虑 live gating。

最保守的 live-safe 初始动作：

- observe-only；
- 然后 pause new entries；
- 然后 reduce notional；
- 最后才考虑修改 execution mode。

Route C 初次接入 live 时绝不能增加 position size 或 net exposure。

---

## 13. 最终建议

按以下顺序推进 Route C：

1. 保持 liquidation collector 运行。
2. 只有在 retention/archive policy 变成 research-safe 后，才重启 orderbook collector。
3. 运行 data-overlap audit。
4. 构建 C1 price-only risk study。
5. 一旦有足够 overlap，再加入 orderbook-aware C1。
6. 之后再考虑 C2 episode labels。
7. 把 C3 视为后续 alpha 分支，不是当前立即推进的下一步。

近期最高价值交付物不是新的交易入口。

近期最高价值交付物是：

> 一个经过验证的 liquidation-aware execution risk filter，用来告诉系统什么时候不要按正常方式交易。

---

## 14. C1 硬化补充规则

外部 review 指出的最大问题成立：

> C1 的方向是对的，但统计定义还不够硬。

本节锁死第一版实现范围。后续变体必须作为独立研究分支，不允许悄悄混进 Phase 1。

### 14.1 第一版事件算法

第一版不要同时支持 24h 和 30d 阈值。

C1 第一版事件定义：

- `event_score = same-symbol same-side trailing 24h percentile rank`；
- `reference_window = previous 1440 1m bars`；
- reference window 排除当前 bar；
- `event_threshold = percentile_rank >= 0.995`；
- 必须使用 side-aware notional；
- 要求 `dominance_ratio >= 0.65`；
- `min_abs_notional` 按 symbol tier 设置：
  - BTC/ETH：使用项目配置或研究配置里的 major threshold；
  - SOL/XRP/DOGE：使用项目配置或研究配置里的 alt threshold；
- dedup by `symbol + side + 5m bucket`；
- 同一 dedup bucket 只保留 notional 最大的 event。

在第一版 C1 没有跑出干净结果前，不加入 30d 阈值、多 percentile 阈值或 episode 变体。

### 14.2 Post-Event Window 防偷看规则

C1 衡量的是 liquidation event **之后**的风险，不能包含 event minute，也不能包含 event 所在的 5m bar。

定义：

- 如果 `shock_bar_start = 12:03:00`；
- 则 `shock_bar_end = 12:03:59`；
- `first_post_1m_window = 12:04:00`；
- `first_complete_5m_response_bar = 12:05:00-12:09:59`。

所有 response metrics 都必须从 event 完成后开始计算：

- 1m 指标从下一分钟开始；
- 5m bar 指标从下一个完整 5m bar 开始；
- realized volatility、range、MAE、MFE、orderbook deterioration 都不能包含 event bar。

这样可以避免把事件发生过程中的价格冲击误标成“未来 post-event risk”。

### 14.3 Direction-Agnostic 与 Strategy-Conditioned 风险拆分

C1 不预测方向，所以 adverse excursion 必须拆成两类指标。

方向无关风险：

- `max_abs_excursion_bps`；
- `high_low_range_bps`；
- `realized_vol_bps`；
- `jump_return_abs_bps`。

策略方向条件化不利波动：

- `mae_if_long_bps = min(low / entry_price - 1, 0) * 10000`；
- `mae_if_short_bps = min(entry_price / high - 1, 0) * 10000`。

必要 summary 字段：

```json
{
  "max_abs_excursion_p90_bps": 0.0,
  "mae_if_long_p90_bps": 0.0,
  "mae_if_short_p90_bps": 0.0
}
```

这样 C1 既能支持通用 no-trade risk，也能服务现有策略的 side-aware protection。

### 14.4 Matched Baseline 合约

每个 event 尝试匹配 `K = 20` 个 baseline windows。

主匹配条件：

1. same symbol；
2. same month；
3. same hour-of-day bucket，允许 `+-1h`；
4. pre-event 30m realized volatility percentile 位于同一个 10% 分位桶；
5. baseline window 前 30m 和后 30m 内没有 liquidation shock；
6. 不与其他 event response window 重叠。

Fallback 规则：

1. 如果匹配不到，先放宽 time-of-day；
2. 再把 volatility percentile 放宽到 `+-20%`；
3. 仍匹配不到，则标记为 `no_matched_baseline`；
4. unmatched event 不进入主统计。

必要 summary 字段：

```json
{
  "event_count": 100,
  "matched_event_count": 82,
  "unmatched_event_count": 18,
  "matched_baseline_count": 1640,
  "baseline_match_rate": 0.82
}
```

如果 `baseline_match_rate < 0.70`，C1 不能通过。

### 14.5 硬性通过 / 失败标准

C1 price-only 第一阶段 gate：

- `event_count >= 100`；
- `matched_event_count >= 70`；
- `baseline_match_rate >= 0.70`；
- `post_event_vol_ratio_median >= 1.5`；
- `post_event_range_ratio_median >= 1.4`；
- `post_event_abs_excursion_p90 / baseline_abs_excursion_p90 >= 1.3`；
- `symbols_passing >= 2` among BTC/ETH/SOL；
- `months_passing >= 2`；
- `max_single_symbol_event_share <= 0.60`；
- `max_single_month_event_share <= 0.60`。

C1 orderbook-aware gate：

- `spread_deterioration_ratio_median >= 1.2`；
- `impact_cost_500usdt_ratio_median >= 1.2`；
- `depth_within_10bps_ratio_median <= 0.8`；
- orderbook effect 在 1/5/10m 内出现。

如果 price-only 通过但 orderbook-aware 失败，结果最多只能是：

```text
volatility_warning
```

不能升级为 execution filter。

### 14.6 Live Action 映射规则

第一版不能依赖人工解释指标。

推荐动作映射：

- `observe_only`：
  - price-only risk 通过；
  - orderbook-aware 证据尚不可用或未通过。

- `pause_entry`：
  - price-only risk 通过；
  - spread 或 impact cost deterioration 通过。

- `reduce_notional`：
  - `impact_cost_500usdt_ratio >= 1.2`；或
  - `depth_within_10bps_ratio <= 0.8`。

- `risk_off`：
  - `post_event_abs_excursion_p90 >= baseline * 2.0`；
  - `spread_deterioration_ratio >= 1.5`；
  - 至少 2 个 symbol/month 组成立。

第一版 live-safe action 只能是：

```text
observe_only -> shadow pause_entry
```

不要从 `force_taker_only_with_small_size` 开始。流动性恶化时强制 taker，可能等于在最差时刻主动吃单。

### 14.7 机会成本与 False Positive 检查

风险过滤器可能通过阻止好交易来破坏收益。

Shadow 分析必须回答：

- 有多少现有 scanner signal 会被过滤；
- 被阻止的 signal 后来表现如何；
- 未被阻止的 signal 后来表现如何；
- signal frequency 下降多少；
- 是否错过主要盈利交易。

必要 proxy 字段：

```json
{
  "filtered_time_share": 0.0,
  "filtered_signal_share_if_applied_to_existing_scanner": 0.0,
  "blocked_trade_proxy_count": 0,
  "allowed_trade_proxy_count": 0
}
```

如果 `filtered_time_share > 0.20`，在机会成本分析证明有效前，必须把该 filter 视为高风险。

### 14.8 Orderbook 采集硬约束

当前服务器资源必须进入设计约束：

- 2 核 CPU；
- 2GB RAM；
- 约 30GB 根磁盘；
- 不计划扩容；
- 已选择每周本地归档和服务器清理模式。

因此，在不扩盘模式下，不要求服务器保存 90 天。

不扩盘运维模式：

- 服务器只保留短期缓存；
- 本地 Mac archive 保存长期研究数据；
- `COLLECTOR_DATA_RETENTION_DAYS = 14`；
- 每周 rsync + checksum + server cleanup；
- 每日 disk usage check；
- 磁盘 70% 告警；
- 磁盘 85% 强制人工干预。

如果资源压力出现，按以下顺序缩减采集：

1. 先停 ADA；
2. 再停 OKX orderbook；
3. 保留 Binance USDT perp BTC/ETH/SOL；
4. 保留 1s write interval；
5. 保留足以计算 5/10/20bps depth 和 impact cost 的深度。

分阶段 rollout：

- Stage 1：只采 Binance BTC/ETH/SOL；
- Stage 2：磁盘和 IO 安全后加入 XRP/DOGE；
- Stage 3：只有需要 cross-exchange liquidity comparison 时才加入 OKX。

### 14.9 Historical Binance Vision Snapshot 边界

Binance Vision snapshot + kline 只能验证 post-event **price risk**。

它不能验证：

- spread deterioration；
- depth withdrawal；
- impact-cost deterioration；
- 最终 live execution-risk filter 行为。

原因：

- snapshot 数据有 liquidation proxy 和 price bars；
- 但没有同步 orderbook state。

因此：

- Binance Vision proxy 可用于 C1 price-only exploration；
- 最终 execution-filter 证据必须来自 liquidation archive 与 orderbook archive 的 live overlap。

### 14.10 C2 与 C3 启动 Gate

C2 start gate：

- C1 price-only 通过；
- `event_count >= 100`；
- 至少 2 个 symbol 通过；
- `baseline_match_rate >= 0.70`。

C3 start gate：

- C1 orderbook-aware 通过；或
- C2 让 C1 metrics 提升至少 20%；
- 每个 context bucket 至少 50 个 events；
- 有 walk-forward split；
- 扣除成本后的 estimated net edge 为正。

这些 gate 未满足前，不启动 C2/C3。否则 Route C 会变成另一个 data-mining 分支。

### 14.11 修订后的开发顺序

不要同时开发 C1/C2/C3。

Batch 0：data overlap audit

必要输出：

```json
{
  "liquidation_1m_zero_fill_coverage_24h": 0.0,
  "orderbook_snapshot_coverage_24h": 0.0,
  "price_1m_coverage_24h": 0.0,
  "overlap_hours_by_symbol": {},
  "ready_for_price_only": true,
  "ready_for_orderbook_aware": false
}
```

Batch 1：C1 price-only baseline

- event detection；
- matched baseline；
- realized volatility；
- range；
- max absolute excursion；
- MAE if long / MAE if short；
- month/symbol stability。

Batch 2：C1 orderbook-aware

- spread；
- depth within 5/10/20bps；
- impact cost 500/1000/2000 USDT；
- maker adverse-selection proxy。

Batch 3：shadow-only filter simulation

- `would_pause_entry`；
- `would_reduce_notional`；
- `would_increase_slippage_reserve`；
- compare blocked versus allowed posterior risk。

这会把 Route C 控制成一个小型 research sprint，而不是一次策略重写。
