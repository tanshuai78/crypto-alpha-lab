# Cross-Sectional Factor Lab 指南可行性评估

日期：2026-06-07  
评估对象：`/Users/tanshuai/Downloads/cross_sectional_factor_lab_implementation_guide_CN_v3.md`  
目标项目：`crypto-alpha-lab`  
结论级别：可以推进，但只能按研究线推进，不能直接升级为实盘策略或 AI 组合策略。

---

## 1. 核心结论

这份 `cross_sectional_factor_lab` 指南适合放进 `crypto-alpha-lab`，而且是当前项目里比 liquidation 方向更接近“进攻型收益”的研究线。

但它必须被严格定位为：

```text
低频横截面选币研究线
不是高频交易系统
不是 AI 自动基金
不是立即可实盘策略
不是对论文结论的直接复刻
```

推荐推进方式：

1. 先做 `Stage 0: Data Coverage + Bias Audit`。
2. 再做 `Stage A: Exchange-only Fast Track`。
3. 暂时不做 on-chain、LightGBM、AIMM 迁移、long-short、实盘执行。
4. 所有结论必须扣除 `30 / 50 / 80 bps` round-trip 成本。
5. 如果只使用当前交易所仍挂牌币种，所有结果必须标注 `survivorship_bias_not_controlled`。

一句话判断：

> 这条线值得做，但要把它当成“低频选币因子实验室”，不是“马上能赚钱的 AI 对冲基金”。

---

## 2. 为什么这条线比当前 C1 更适合作为进攻型策略

C1 的定位是防守型风控过滤器：

```text
liquidation 后是否更危险？
是否应该暂停入场、降低仓位、提高滑点保护？
```

它即使成立，也主要回答“什么时候不要交易”，不能直接回答“买什么更赚钱”。

`cross_sectional_factor_lab` 回答的是另一个问题：

```text
在同一时间点，哪些币未来一段时间更可能跑赢？
```

这更像真正的进攻型策略，因为它有明确的组合选择动作：

```text
每周或每 3 天：
  对可交易币种打分；
  买入前 3–5 个；
  避开过热、拥挤、流动性差或 C1 风险窗口中的币；
  下一次调仓再重新排序。
```

这个方向和个人投资者更匹配：

- 不依赖毫秒级延迟；
- 不需要复杂做市库存管理；
- 交易频率低，成本更可控；
- 更适合用历史数据验证；
- 可以先 paper/shadow，再小仓试运行。

---

## 3. 指南中最合理的部分

### 3.1 强制 Stage A long-only 是正确的

指南要求 Stage A 第一版必须 `long-only`，不允许把无摩擦 `long-short` 作为主结果。

这是正确的。

原因很简单：

```text
个人投资者做空小币的真实成本很难稳定建模：
  funding；
  借币成本；
  合约深度；
  强平风险；
  交易所临时风控；
  小币插针。
```

如果第一版就做 long-short，很容易得到一个“论文里很好看、实盘里根本吃不到”的结果。

Stage A 应只回答：

```text
只买强币、不做空弱币，扣成本后能不能跑赢 BTC / ETH / 等权基准？
```

这个问题干净、可执行、也更适合个人账户。

### 3.2 成本场景 30 / 50 / 80 bps 是必要的

指南把 round-trip 成本设为：

```text
base   = 30 bps
stress = 50 bps
crash  = 80 bps
```

这个比很多“学术回测”诚实得多。

低频选币策略看起来换手不高，但真实摩擦包含：

- 手续费；
- bid/ask spread；
- 小币冲击成本；
- 调仓时段拥挤；
- 流动性突然变薄；
- 部分成交后被迫追价。

如果一个策略在 `30 bps` 下才刚刚盈利，在 `50 / 80 bps` 下立刻崩掉，那它不应该进入 shadow。

### 3.3 明确标注幸存者偏差是硬要求

如果只用当前仍在 Binance/OKX 上交易的币回测，会天然漏掉：

- 已退市币；
- 归零币；
- 改名迁移币；
- 历史上流动性消失的币；
- 曾经进入组合但后来不可交易的币。

这会让回测结果偏乐观。

所以指南要求输出：

```json
{
  "universe_scope": "current_tradable_universe_only",
  "survivorship_bias_control": "not_controlled",
  "delisted_symbols_included": false,
  "result_usage": "hypothesis_screening_only_not_final_evidence"
}
```

这是必须保留的规则，不能删。

### 3.4 Active Addresses / NVT 不作为 Stage A 起手式是正确的

Active Addresses 和 NVT 在论文里很诱人，但实操上很脏：

- 地址数可以被空投刷量污染；
- 交易所归集会扭曲链上转账；
- L2、meme、平台币、治理币的链上含义不同；
- 不同链的数据口径不统一；
- 免费数据源质量不稳定。

所以指南把 Stage A 限定为 `exchange-only` 是正确的：

```text
先用价格、成交量、funding、OI 证明低频横截面框架是否有边际价值；
再决定是否值得引入链上数据。
```

这避免了开局就陷入“昂贵数据 + 复杂清洗 + 无法判断到底是谁贡献收益”的泥潭。

### 3.5 C1 只做入场拦截，不做强制平仓

指南要求：

```text
C1 risk window active 只阻止新买入；
不因为分钟级 C1 风险临时平掉 weekly / 3d 仓位。
```

这是正确的。

原因：

- C1 是分钟级风险状态；
- 横截面选币是日级/周级策略；
- 如果用分钟级噪声强制退出低频仓位，会把策略切碎；
- 调仓成本会暴增；
- 可能把一个慢周期 alpha 变成过度交易。

但需要注意：

当前 C1 live smoke 的结论仍是 `baseline_match_failed`，不是正式通过。因此在 Factor Lab 的 Stage A 中，C1 最多先作为 diagnostic 字段或可选 veto 版本，不应作为主回测的强制条件。

---

## 4. 最大现实风险

### 4.1 当前项目还没有“宽 universe 日频面板”

`crypto-alpha-lab` 目前已有：

- funding 方向研究；
- trend/liquidation 方向研究；
- Binance liquidation snapshot 研究；
- C1 live overlap / smoke；
- 局部 Binance REST 拉取脚本；
- 1h trend regime rows。

但还没有 Factor Lab 需要的核心数据结构：

```text
多币种 × 多日期 × 多字段 的 daily panel
```

至少需要：

```text
date
exchange
symbol
open
high
low
close
volume
quote_volume
funding_rate
open_interest
tradable_flag
listing_status
```

没有这个面板，就不能做严肃的横截面排序、分组回测和 walk-forward。

### 4.2 当前 `asset master` 不存在

指南里的正式版需要：

```text
canonical_asset_id
exchange_symbol
listing_date
delisting_date
alias_history
migration_policy
delist_exit_policy
```

当前项目还没有这个模块。

这意味着第一版只能做：

```text
current_tradable_universe_only
survivorship_bias_not_controlled
hypothesis_screening_only
```

不能把 Stage A 的正结果解释成最终可实盘 edge。

### 4.3 当前依赖不支持成熟因子研究栈

当前 `pyproject.toml` 依赖主要是：

```text
ccxt
loguru
aiosqlite
numpy
```

没有：

```text
pandas
scipy
statsmodels
lightgbm
```

Stage 0 如果只做 coverage audit，可以用纯 Python / numpy 做，避免为了一个审计脚本过早扩依赖。

但从 Stage A 开始，一旦要构建 daily panel，就应默认引入 `pandas`。原因是横截面因子研究会大量使用：

```text
groupby symbol
cross-sectional rank
rolling window
missing coverage audit
rebalance date slicing
walk-forward split
```

这些用纯 Python 长期硬写，代码会更脆，也更难审计。第一阶段可以只新增 `pandas`，不要同时引入 `statsmodels`、`scipy` 全家桶或 `LightGBM`。

不建议现在引入 `LightGBM`。

原因：

```text
如果单因子和简单组合都没有站住，
机器学习只会更快地过拟合。
```

### 4.4 论文结论不能直接迁移到本项目

论文里的强因子不等于个人账户可交易收益。

主要差异：

- 论文 universe 可能更宽；
- 论文可能用高质量商业数据；
- 学术组合可能允许做空；
- 回测成本可能偏低；
- 论文统计显著不等于实盘收益稳定；
- crypto 资产生命周期短，退市和迁移很多；
- 小币 alpha 可能被流动性和滑点吃掉。

因此本项目必须坚持：

```text
先验证 exchange-only long-only 净收益；
再考虑 size / on-chain；
最后才考虑 AI 融合。
```

---

## 5. 当前项目中可以复用的模块

### 5.1 `configs/base.py`

用途：

- 放置 Factor Lab 的所有阈值；
- 避免策略阈值散落在脚本里；
- 保持项目 “no magic numbers in src” 的规则。

建议未来新增类似：

```python
FACTOR_LAB_MIN_DAILY_QUOTE_VOLUME_USDT = ...
FACTOR_LAB_COST_SCENARIO_BPS = (30.0, 50.0, 80.0)
FACTOR_LAB_TOP_K = (3, 5)
FACTOR_LAB_REBALANCE_DAYS = (3, 7)
FACTOR_LAB_MIN_HISTORY_DAYS = ...
FACTOR_LAB_SURVIVORSHIP_BIAS_REQUIRED_FLAG = True
```

### 5.2 `src/research/cost_model.py`

当前 cost model 偏 funding 策略，但可以复用其思想：

```text
所有收益必须扣成本；
成本用 bps；
不允许只看 gross return。
```

Factor Lab 需要新增 cross-sectional 专用成本模型：

```text
rebalance turnover × round_trip_cost_bps
```

建议保留 `30 / 50 / 80 bps` 三档，而不是只用单一成本。

### 5.3 `scripts/build_trend_regime_market_rows.py`

可复用的部分：

- Binance REST URL 构造；
- symbol 规范化；
- JSONL rows 输出；
- OI / funding / kline 组合拉取模式；
- timestamp 排序写入。

不能直接复用的部分：

- 它是 1h trend regime 数据；
- universe 太窄；
- 不是 daily panel；
- 不处理 listing/delisting；
- 不适合直接作为 cross-sectional 回测数据源。

### 5.4 `src/exchange/market_data.py`

可复用：

- ccxt fetch 结构；
- retry / error classification；
- spot tickers；
- Binance funding data；
- volume 过滤思想。

适用阶段：

```text
Stage D Paper Shadow
Stage F Tiny Live Pilot
```

不适合直接承担 Stage A historical panel，因为它主要是 live fetch 层，不是历史数据构建器。

### 5.5 `src/strategies/base.py`

可用于后续把 Factor Lab 接入统一策略接口。

但 Stage 0/A 不建议先写 `BaseStrategy` 实盘策略类。

原因：

```text
Stage A 是研究，不是交易系统；
如果过早接入 strategy/execution，容易把未验证假设包装成可交易策略。
```

正确顺序：

```text
Stage 0/A: src/research/cross_sectional_factor_lab/
Stage D: shadow scanner
Stage F: BaseStrategy + SignalCandidate
```

### 5.6 `src/risk/limits.py`

用于 Stage F 小仓试运行：

- live trading 默认关闭；
- 单笔最大名义本金；
- 最大并发仓位；
- drawdown halt。

Stage A 不需要接这个模块，但最终上线前必须经过它。

### 5.7 C1 相关产物

C1 可以作为未来入场风控 overlay：

```text
如果调仓时某个 symbol 正处于 C1 risk window，则跳过新买入。
```

但当前 C1 live smoke 仍是：

```text
route_c1_baseline_match_failed
```

这表示 C1 尚未完成正式统计确认。

所以 Factor Lab 第一版应这样处理：

```text
主结果：不使用 C1；
附加诊断：记录如果启用 C1 entry block，会影响多少调仓；
正式启用：等待 C1 30d forward 或 orderbook-aware 通过后再说。
```

---

## 6. 不建议直接复用或迁移的部分

### 6.1 不建议直接迁移 AIMM

外部 AIMM 项目可以参考架构概念，但不建议直接迁移。

原因：

- 当前项目已经有清晰的研究 / 风控 / 执行边界；
- AIMM 可能引入大量未知抽象和依赖；
- agentic 系统容易把未验证信号包装成复杂流程；
- 对个人账户来说，简单可审计比“像基金公司”更重要。

建议：

```text
不迁移 AIMM；
只借鉴 desk 分层思想：
  market scan
  factor scoring
  risk guard
  paper shadow
```

### 6.2 不建议一开始使用 LightGBM

LightGBM 应放在 Stage G，而不是 Stage A。

启动条件至少应包括：

- 2 个以上单因子在 walk-forward 中稳定；
- 数据长度足够；
- universe 足够宽；
- 成本后仍有净收益；
- 有严格 train/test 时间切分；
- 有特征泄漏测试；
- 有换手和容量约束。

否则 LightGBM 只会把噪声拟合得更漂亮。

### 6.3 不建议直接复活 extreme funding 作为主策略

项目之前已经证明 extreme funding / basis-aware replay 的收益结构不足以支撑独立策略。

它可以作为 Factor Lab 的一个风险或拥挤度字段：

```text
funding too positive = crowded long risk
funding too negative = short crowding / stress
```

但不建议把它重新升级为主盈利策略。

### 6.4 不建议直接使用 execution 层

Stage A 是 research。

不应接：

- order executor；
- preflight；
- inventory guard；
- live order state machine。

这些应该等到：

```text
Stage D paper shadow 通过；
Stage F tiny live pilot 被单独审批。
```

---

## 7. 推荐的最小推进路径

### 7.1 第一小步：只做 Stage 0

目标：

```text
判断当前免费交易所数据是否足够支持 Fast Track。
```

这里的“只做 Stage 0”只表示**下一步只做数据覆盖与偏差审计**，不是未来几周一直停在 Stage 0。Stage 0 是闸门，不是终点。

不做：

- 因子回测；
- 策略结论；
- AI；
- on-chain；
- 实盘。

建议输出：

```text
reports/cross_sectional_factor_lab/factor_lab_data_coverage_summary.json
docs/reviews/YYYY-MM-DD-cross-sectional-factor-lab-data-coverage-review_CN.md
```

最低审计字段：

```json
{
  "universe_scope": "current_tradable_universe_only",
  "survivorship_bias_control": "not_controlled",
  "symbols_total": 0,
  "symbols_passing_liquidity": 0,
  "history_days_available": 0,
  "daily_ohlcv_coverage_ratio": 0.0,
  "funding_coverage_ratio": 0.0,
  "open_interest_coverage_ratio": 0.0,
  "listing_metadata_available": false,
  "decision": "factor_lab_data_unavailable|factor_lab_data_ready_with_bias"
}
```

建议通过线：

```text
symbols_passing_liquidity >= 30
history_days_available >= 540
daily_ohlcv_coverage_ratio >= 0.95
funding_coverage_ratio >= 0.90 for perp universe
open_interest_coverage_ratio >= 0.90 for perp universe
survivorship_bias_control explicitly labeled
```

如果达不到，不进入 Stage A。

如果输出：

```text
decision = factor_lab_data_ready_with_bias
```

则应立即进入下一步：

```text
编写 Stage A exchange-only Fast Track implementation plan
```

不要在 Stage 0 后反复讨论而不进入回测。这里要避免两个相反错误：

```text
错误 1：跳过 Stage 0，直接写完整策略；
错误 2：Stage 0 通过后，迟迟不进入 Stage A。
```

### 7.2 第二小步：Stage A exchange-only Fast Track

只有 Stage 0 通过后再做。

第一版因子：

```text
cmom_14d = close / close.shift(14) - 1
volume_expansion = quote_volume_7d_avg / quote_volume_30d_avg - 1
funding_veto = funding too positive / too negative
oi_veto = OI expansion too extreme
liquidity_veto = volume / spread / depth proxy too weak
```

第一版组合：

```text
long-only
top 3
top 5
weekly rebalance
3d rebalance
```

必须比较：

```text
BTC buy-and-hold
ETH buy-and-hold
50/50 BTC/ETH
equal-weight eligible universe
```

必须扣成本：

```text
30 bps
50 bps
80 bps
```

最低继续标准：

```text
成本后跑赢 BTC/ETH/等权中的至少 2 个基准；
结果不是由单一月份或单一币种贡献；
stress 50 bps 后仍不崩；
walk-forward 不反转；
最大回撤可接受；
换手不过高。
```

### 7.3 第三小步：Stage A2 walk-forward

禁止全样本调参后再宣称有效。

应使用：

```text
train window -> 固定参数 -> test window
rolling / expanding walk-forward
```

需要输出：

```text
by-period return
by-period turnover
by-period max drawdown
by-period benchmark excess return
```

### 7.4 后续阶段

只有 Stage A/A2 通过后：

```text
Stage B-lite: 小样本 Active Addresses / NVT feasibility
Stage C: market cap / size extension
Stage D: paper shadow
Stage E: production-grade on-chain
Stage F: tiny live pilot
Stage G: LightGBM / AI factor fusion
```

不要跳级。

---

## 8. 建议的模块结构

指南建议的结构基本合理。

推荐落地为：

```text
src/research/cross_sectional_factor_lab/
  __init__.py
  universe.py
  asset_master.py
  panel_builder.py
  factors.py
  scoring.py
  portfolio_simulator.py
  gates.py
  experiment_trace.py

scripts/
  audit_factor_lab_data_coverage.py
  build_factor_lab_daily_panel.py
  review_factor_lab_baseline.py

configs/
  asset_aliases.json

reports/cross_sectional_factor_lab/
  factor_lab_data_coverage_summary.json
  factor_lab_stage_a_baseline_summary.json

docs/reviews/
  YYYY-MM-DD-cross-sectional-factor-lab-*.md
```

但建议先只实现：

```text
audit_factor_lab_data_coverage.py
src/research/cross_sectional_factor_lab/universe.py
src/research/cross_sectional_factor_lab/asset_master.py
```

不要一次性铺满所有文件。

---

## 9. 是否适合在 crypto-alpha-lab 推进

适合。

理由：

1. 项目当前定位就是 alpha verification lab。
2. 这条线有明确可证伪问题。
3. 低频横截面更适合个人投资者。
4. 它不依赖服务器低延迟。
5. 它能复用已有 config、research、risk、report 流程。
6. 它和 C1 防守线互补：一个负责进攻选币，一个负责风险窗口过滤。

但推进边界必须写死：

```text
不直接实盘；
不先 AI；
不先 on-chain；
不先 long-short；
不忽略幸存者偏差；
不使用 gross return 讲故事；
不因为论文结论好看就默认可交易。
```

---

## 10. 推荐决策

当前建议：

```text
decision = proceed_with_stage0_data_coverage_audit_only
```

这条 decision 的含义是：

```text
下一步只执行 Stage 0；
Stage 0 若 data_ready_with_bias，则立刻进入 Stage A plan；
Stage 0 若 data_unavailable，则停止 Fast Track 或更换数据源。
```

不建议：

```text
decision = build_full_factor_lab_now
decision = migrate_to_AIMM
decision = start_lightgbm_factor_model
decision = start_onchain_active_address_pipeline
decision = paper_trade_immediately
```

下一步最合适的任务：

```text
编写 Stage 0 implementation plan：
  1. 数据源选择；
  2. universe 定义；
  3. coverage audit 字段；
  4. bias contract；
  5. 输出 summary；
  6. 通过/停止标准；
  7. 不进入回测的边界条件。
```

---

## 11. 最终评价

这份指南的方向是合理的，尤其是它没有犯三个常见错误：

```text
直接 AI；
直接实盘；
直接把论文收益当可交易收益。
```

它真正有价值的地方不是“选了 CMOM / Active Addresses / NVT 这些漂亮因子”，而是把研究推进顺序写得比较克制：

```text
先证明数据能用；
再证明 exchange-only 因子有净收益；
再证明 walk-forward 稳定；
再考虑链上；
最后才考虑 AI 融合和小仓实盘。
```

我的判断：

```text
可以推进；
优先级高于继续挖 liquidation directionality；
与 C1 风控线互补；
第一阶段只做 Stage 0；
不要急着写完整策略。
```
