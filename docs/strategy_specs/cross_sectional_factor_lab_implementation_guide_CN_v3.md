# Cross-Sectional Factor Lab 进攻型策略实施指南 V3

**项目**：`crypto-alpha-lab`  
**策略线**：`cross_sectional_factor_lab`  
**版本**：V3  
**项目内修订日期**：2026-06-07  
**定位**：进攻型低频横截面选币研究线。  
**核心原则**：Fast Track 快速杀假设；正式版必须控制幸存者偏差、成本低估、做空成本、Token Migration、C1 频率冲突与链上数据污染。
**文档定位**：本文件是 `strategy_specs` 级别的策略指导文件；具体落地时仍需另写 `docs/plans/` 下的 implementation plan。

---

## 0. V3 相比 V2 的关键修正

1. **Fast Track 不是最终证据**  
   Fast Track 只用于快速筛选方向，不能作为 live 策略证明。

2. **Stage A 第一阶段强制 long-only**  
   禁止把无摩擦 long-short 作为主结果。做空成本、funding、借币利息未建模前，不允许模拟完美做空。

3. **成本场景上调**  
   原 `10 / 25 / 50 bps` 偏乐观。V3 改为：
   - base：`30 bps round-trip`
   - stress：`50 bps round-trip`
   - crash：`80 bps round-trip`

4. **幸存者偏差必须显式标注**  
   若只用当前仍挂牌交易对回测，必须标注 `survivorship_bias_not_controlled`。正式版必须引入退市币、listing/delisting 和 asset master。

5. **C1 只做入场拦截，不强制平仓**  
   `C1 risk window active` 只在调仓日阻止新买入；不因为分钟级 C1 风险临时平掉 weekly / 3d 仓位。

6. **Token Migration / Symbol Alias 必须处理**  
   例如 `MATIC -> POL`、`AGIX/OCEAN -> FET`。MVP 可用 static alias；正式版必须使用 effective-date asset master。

7. **Active Addresses / NVT 是核心战略因子，但不是 Stage A 起手式**  
   Stage A 保持 exchange-only；Stage B-lite 做小样本链上可行性；Stage E 才做生产级 on-chain integration。

8. **Stage 0 是闸门，不是终点**  
   下一步只做 Stage 0 data coverage audit；如果输出 `factor_lab_data_ready_with_bias`，必须立即进入 Stage A implementation plan，不能长期停留在数据审计讨论。

9. **Stage A daily panel 默认引入 pandas**  
   Stage 0 coverage audit 可用纯 Python / numpy；但 Stage A 一旦构建 daily panel，默认使用 `pandas` 处理 rank、groupby、rolling、缺失率和 walk-forward 切分。第一阶段不引入 `LightGBM`、`statsmodels` 或 `scipy` 全家桶。

10. **C1 entry block 必须区分正式启用与诊断启用**  
    在 C1 尚未通过 30d forward 或 orderbook-aware 验证前，Factor Lab 主回测不得强制启用 C1 veto；只能记录 `c1_would_block` 作为诊断字段。C1 正式通过后，才允许加入 entry block 版本。

11. **AIMM / Agentic OS 不作为本项目迁移目标**  
    可以借鉴“market scan / alpha / risk guard / shadow”的分层思想，但不迁移外部 AIMM 项目，不引入无法审计的 agentic live decision loop。

---

## 1. 策略核心问题

本策略要回答：

> 在 Binance / OKX 高流动性币种中，是否存在一组低频横截面因子，可以每周或每 3 天选出未来相对更强的 3–5 个币，并在扣除真实交易摩擦后跑赢 BTC、ETH 和等权基准？

这不是高频交易，不是盘口做市，也不是单币方向预测。

核心思想：

```text
在同一时间点比较所有可交易币，
买入：趋势强 + 放量 + 不拥挤 + 可执行 + 非 C1 风险窗口的标的；
避开：funding 过热、OI 失控、波动极端、流动性不足、链上/交易所数据异常的标的。
```

---

## 2. 学术背景与项目解释

### 2.1 CMOM

`CMOM` = Crypto Momentum = **2 周动量**。

项目实现：

```text
cmom_14d = close / close.shift(14) - 1
```

含义：今天价格相对 14 天前的涨幅。

### 2.2 NVT

`NVT = Network Value / Transaction Volume`

解释：

```text
NVT 低 = 链上“物有所值”
类似股票里的低市盈率。
```

交易方向：

```text
NVT 越低越好；
NVT beta 预期为负；
可使用 inverse_nvt = transaction_volume / network_value，越高越好。
```

### 2.3 Active Addresses

`Active Addresses` 是链上真实用户采用度代理。  
UCM 论文结论显示，动态 Active Addresses 单因子具有很强横截面解释力；动态 NVT 也具有强定价解释力和组合表现。

项目解释：

```text
CMOM：资金趋势；
Active Addresses：真实采用增长；
NVT：网络价值效率；
三者是最终形态的核心 alpha 候选。
```

### 2.4 防过度解读

论文结论不能直接等于本项目可交易收益。原因：

- 论文 universe 不等于 Binance/OKX 可交易 universe；
- 学术多空组合不等于个人投资者 long-only；
- 学术数据可能来自深度清洗后的供应商；
- 实盘有手续费、滑点、盘口深度、交易所风控；
- Active Addresses 容易被空投刷量、MEV、交易所归集污染；
- NVT 对 meme、L2 governance token、平台币的解释力不稳定。

---

## 3. 总体推进路线

| Stage | 名称 | 目标 | 数据 | 是否可 live |
|---|---|---|---|---|
| Stage 0 | Data Coverage + Bias Audit | 判断免费交易所数据是否足够 | Binance/OKX daily | 否 |
| Stage A | Exchange-only Fast Track | 快速验证 CMOM/volume/funding/OI | 免费交易所数据 | 否 |
| Stage A2 | Walk-forward + Robustness | 防过拟合 | 同上 | 否 |
| Stage B-lite | On-chain Small Sample | 小样本验证 Active/NVT 是否有增量 | 免费/低成本链上 | 否 |
| Stage C | Market Cap / Size Extension | 测试 liquidity-adjusted size | CoinGecko/CMC | 否 |
| Stage D | Paper Shadow | 验证真实数据链路 | live API | 否 |
| Stage E | Production-grade On-chain | 生产级 Active/NVT | 清洗后链上数据 | 否 |
| Stage F | Tiny Live Pilot | 极小仓摩擦验证 | live exchange | 极小仓 |
| Stage G | Composite / AI / LightGBM | 因子融合 | 完整数据 | 单独审批 |

当前推荐推进状态：

```text
next_action = Stage 0 implementation plan
not_allowed_yet = Stage A backtest / on-chain / LightGBM / paper shadow / live pilot
```

---

## 4. Stage 0：Data Coverage + Bias Audit

### 4.1 目的

确认免费交易所数据能否支持 Fast Track，并显式标注偏差。

### 4.2 数据源

优先：

```text
Binance USDT perpetuals / spot
```

后续：

```text
OKX swaps
```

字段：

```text
daily OHLCV
quote volume
funding rate
open interest
mark price / index price
listing / tradability metadata
```

### 4.3 Bias Contract

如果只使用当前挂牌币种，必须输出：

```json
{
  "universe_scope": "current_tradable_universe_only",
  "survivorship_bias_control": "not_controlled",
  "delisted_symbols_included": false,
  "result_usage": "hypothesis_screening_only_not_final_evidence"
}
```

### 4.4 正式版 Asset Master

正式回测必须构建：

```text
canonical_asset_id
exchange
exchange_symbol
listing_date
delisting_date
tradable_start
tradable_end
alias_history
migration_policy
delist_exit_policy
```

### 4.5 退市处理

必须至少支持：

```text
delist_at_last_trade_price
delist_to_zero
delist_with_forced_exit_slippage
```

推荐默认：

```text
delist_with_forced_exit_slippage
```

压力测试：

```text
delist_to_zero
```

### 4.6 通过标准

Fast Track 最低标准：

```text
月均 universe >= 30
daily OHLCV coverage >= 95%
至少 18 个月历史
funding/OI 覆盖可用
```

### 4.7 输出文件

建议输出：

```text
reports/cross_sectional_factor_lab/factor_lab_data_coverage_summary.json
docs/reviews/YYYY-MM-DD-cross-sectional-factor-lab-data-coverage-review_CN.md
```

### 4.8 决策分支

```text
factor_lab_data_unavailable:
    不进入 Stage A；更换数据源或缩小 universe 后重跑 Stage 0。

factor_lab_data_ready_with_bias:
    允许立即编写 Stage A implementation plan；
    所有 Stage A 结果必须标注 survivorship_bias_not_controlled。

factor_lab_data_ready_formal:
    允许进入正式版回测；
    需要包含 asset master、listing/delisting、alias history。
```

Stage 0 不能被当作长期研究终点。它只回答：

```text
免费交易所数据是否足够支持 Fast Track？
```

如果回答是“足够但有偏差”，下一步就是 Stage A plan，不应反复停在数据审计阶段。

---

## 5. Stage A：Exchange-only Fast Track

### 5.1 目的

快速验证：

```text
CMOM + volume expansion + funding/OI veto
```

是否存在基础 edge。

### 5.1.1 依赖策略

Stage A 一旦构建 daily panel，默认引入 `pandas`。

原因：

```text
横截面 rank
groupby symbol
rolling window
缺失率审计
rebalance date slicing
walk-forward split
```

这些逻辑用纯 Python 长期维护风险更高。Stage A 只新增 `pandas`；不引入 `LightGBM`、`statsmodels`、`scipy` 全家桶。

### 5.2 Universe

```text
Binance 高流动性 USDT perpetuals / spot
30d median quote volume >= 20M 或 50M USDT
剔除 stablecoin / leveraged token / wrapped token
```

### 5.3 强制 Long-only

主结果只允许：

```text
long-only top 3
long-only top 5
cash fallback
```

禁止：

```text
long-short main result
frictionless short
borrow-cost-free short
funding-free short
```

如果做 long-short，只能作为 diagnostic：

```json
{
  "long_short_result_usage": "diagnostic_only",
  "short_cost_model": "missing|funding_deducted|borrow_cost_deducted"
}
```

### 5.4 因子定义

```text
cmom_14d = close / close.shift(14) - 1
momentum_7d = close / close.shift(7) - 1
momentum_30d = close / close.shift(30) - 1
volume_ratio_7d_30d = mean(volume_quote, 7d) / median(volume_quote, 30d)
realized_vol_14d = std(daily_return, 14d)
funding_annualized_7d = mean(funding_rate_8h, 7d) * 3 * 365
oi_change_7d = open_interest / open_interest.shift(7) - 1
```

### 5.5 Score 设计

第一版 score 是 heuristic，不是论文证明的最优参数。

必须同时测试：

#### A. 单因子

```text
cmom_14d
volume_ratio_7d_30d
oi_change_7d
realized_vol_14d
funding_annualized_7d
```

#### B. 等权 score

```text
score_equal =
  rank(cmom_14d)
+ rank(volume_ratio_7d_30d)
+ rank(oi_change_7d)
- rank(realized_vol_14d)
```

#### C. 启发式权重 score

```text
score_heuristic =
  0.45 * rank(cmom_14d)
+ 0.25 * rank(volume_ratio_7d_30d)
+ 0.15 * rank(oi_change_7d)
- 0.15 * rank(realized_vol_14d)
```

必须输出：

```json
{
  "score_weight_source": "heuristic_not_paper_proven"
}
```

### 5.6 Veto

```text
exclude if funding_annualized_7d > 0.80
exclude if volume_quote_30d_median < threshold
exclude if realized_vol_14d in top 5% of universe
```

C1 口径必须分两层：

```text
主回测：
    默认不强制启用 C1。

诊断回测：
    记录 c1_would_block；
    输出如果启用 C1 会影响多少调仓、多少收益、多少回撤。

C1 正式版本：
    只有 C1 通过 30d forward 或 orderbook-aware 验证后，
    才允许 exclude if C1 entry block active on rebalance day。
```

### 5.7 Rebalance Frequency

必须同时测试：

```text
weekly rebalance / hold 7d
3d rebalance / hold 3d
daily scan with min_hold >= 3d and turnover cap
```

禁止：

```text
1h 或更低频率高频调仓
```

### 5.8 Cost Scenarios

V3 成本：

```text
base: 30 bps round-trip
stress: 50 bps round-trip
crash: 80 bps round-trip
```

`10 bps` 只允许作为 maker diagnostic：

```text
仅当 maker_fill_rate >= 70%
且未成交处理逻辑已建模
且不追价
才允许报告 10 bps optimistic result。
```

### 5.9 Benchmark

```text
BTC buy-and-hold
ETH buy-and-hold
BTC/ETH 50-50
equal-weight tradable universe
```

### 5.10 通过标准

```text
30 bps 后跑赢 BTC/ETH 50-50 或 equal-weight
50 bps 下不崩
80 bps crash 结果可接受
top3/top5 方向一致
weekly/3d 至少一个频率明显有效
收益不是单币贡献
收益不是单月贡献
最大回撤不超过 benchmark 的 1.5 倍
```

### 5.11 停止条件

```text
30 bps 后不如 benchmark
50 bps 下收益消失
80 bps 下严重崩盘
收益来自单币/单月
turnover 过高
C1 entry block 后信号稀疏
```

---

## 6. Stage A2：Walk-forward + Robustness

### 6.1 目的

防止 Fast Track 只是过拟合。

### 6.2 检查项

```text
按年份切分
按牛/熊/震荡切分
单币贡献
单月贡献
top3 vs top5
weekly vs 3d
30/50/80 bps 成本敏感性
参数敏感性
```

### 6.3 通过标准

```text
不是只靠一个 market regime
不是只靠单一币种
不是只靠单一月份
成本压力下仍保留部分 edge
```

---

## 7. C1 Entry Block 逻辑

### 7.1 定位

C1 是：

```text
Entry Block
```

不是：

```text
Forced Exit
```

### 7.1.1 启用状态

Factor Lab 中的 C1 必须带启用状态：

```json
{
  "c1_entry_block_mode": "disabled|diagnostic_only|formal_veto",
  "c1_evidence_source": "none|price_only_proxy|live_smoke|30d_forward|orderbook_aware",
  "c1_can_affect_main_result": false
}
```

默认：

```text
c1_entry_block_mode = diagnostic_only
c1_can_affect_main_result = false
```

只有当 C1 通过 `30d_forward` 或 `orderbook_aware` 验证后，才允许：

```text
c1_entry_block_mode = formal_veto
c1_can_affect_main_result = true
```

### 7.2 调仓日逻辑

```text
for candidate in ranked_list:
    if c1_risk_window_active(candidate, rebalance_time):
        record c1_would_block = true
        if c1_entry_block_mode == "formal_veto":
            record c1_entry_blocked = true
            skip candidate
            continue to next ranked asset
        else:
            record c1_entry_blocked = false
            allow candidate
    else:
        allow candidate
```

### 7.3 持仓期间逻辑

```text
如果 C1 在持仓期间触发：
    不强制平仓；
    只记录 c1_risk_during_holding；
    后续分析该事件是否解释 drawdown。
```

### 7.4 全局风控例外

只有以下情况可触发强制退出：

```text
exchange incident
withdrawal/deposit halt
symbol delisting
extreme market halt
global risk halt
manual emergency stop
```

---

## 8. Asset Master 与 Token Migration

### 8.1 MVP

Fast Track 可用 static alias mapping：

```text
MATIC -> POL
AGIX/OCEAN -> FET
```

必须标注：

```json
{
  "alias_mapping_mode": "static_mvp",
  "alias_mapping_complete": false
}
```

### 8.2 正式版

正式版必须使用 effective-date asset master：

```json
{
  "canonical_asset_id": "polygon",
  "aliases": [
    {
      "symbol": "MATICUSDT",
      "start": "2020-01-01",
      "end": "2024-09-XX"
    },
    {
      "symbol": "POLUSDT",
      "start": "2024-09-XX",
      "end": null
    }
  ],
  "migration_type": "token_migration",
  "continuity_policy": "continuous_adjusted"
}
```

### 8.3 测试

```text
test_matic_pol_alias_continuity
test_alias_mapping_is_effective_date_aware
test_unknown_symbol_is_reported_not_silently_merged
```

---

## 9. Stage B-lite：On-chain Small Sample Feasibility

### 9.1 目的

在不购买昂贵数据、不重构系统的前提下，小样本验证 Active Addresses / NVT 是否有增量。

### 9.2 启动条件

只有 Stage A 和 A2 通过后启动。

### 9.3 样本范围

优先链上含义清晰的标的：

```text
BTC
ETH
SOL
LINK
AAVE
UNI
少数 DeFi / L1 标的
```

暂不纳入：

```text
meme
L2 governance token
exchange token
wrapped token
synthetic asset
```

### 9.4 数据源

优先尝试：

```text
DefiLlama
Dune
CoinMetrics community data（如可用）
CoinGecko 衍生数据
```

暂不购买：

```text
Glassnode professional API
CryptoQuant institutional API
Token Terminal paid plan
```

### 9.5 因子

```text
active_address_growth_14d
active_address_growth_30d
active_addresses_zscore_90d
nvt_ratio
inverse_nvt = transaction_volume / network_value
nvt_percentile
```

### 9.6 污染检查

必须记录：

```text
sybil_risk
exchange_sweeping_risk
bot_activity_risk
missing_data_ratio
data_lag_hours
token_category_suitability
```

### 9.7 通过标准

```text
Active/NVT 对 OOS 排名有增量
不是简单重复 CMOM
缺失率可控
数据滞后不影响周频/3d 调仓
小样本结果足够强，值得 Stage E 正式化
```

---

## 10. Stage C：Market Cap / Size Extension

### 10.1 启动条件

Stage A 通过后可启动，但优先级低于 B-lite。

### 10.2 目标

测试：

```text
liquidity-adjusted size
small-but-liquid momentum
volume growth × size
```

### 10.3 数据源

```text
CoinGecko
CoinMarketCap
```

### 10.4 难点

```text
coin_id mapping
historical market cap missing
circulating supply changes
token migration
delisted symbols
```

### 10.5 通过标准

```text
market_cap coverage >= 90%
加入 size 后 OOS 改善
drawdown 不恶化
不是买入不可执行小币
```

---

## 11. Stage D：Paper Shadow

### 11.1 启动条件

```text
Stage A 通过
A2 robustness 通过
数据链路稳定
RiskLimits 不变
```

C1 entry block 不是 Stage D 的硬前提。若 C1 尚未正式通过，则 Stage D 必须使用：

```text
c1_entry_block_mode = diagnostic_only
```

只有 C1 已通过 30d forward 或 orderbook-aware 验证，才允许 Stage D 使用：

```text
c1_entry_block_mode = formal_veto
```

### 11.2 分层 shadow

```text
2 周 smoke shadow:
    验证数据链路和信号生成。

4 周 paper shadow:
    验证 rebalance 可执行性。

8–12 周 pre-live shadow:
    仅在准备 live pilot 前需要。
```

### 11.3 验证内容

```text
信号是否准时生成
symbol mapping 是否正确
所选币是否真实可交易
funding/OI 是否延迟
C1 entry block 是否正常
paper next-open 模拟是否稳定
报告是否可审计
```

---

## 12. Stage E：Production-grade On-chain Extension

### 12.1 启动条件

只有 B-lite 通过后启动。

### 12.2 目标

正式集成：

```text
Active Addresses
NVT
MVRV（可选）
TVL / fees / revenue（DeFi 子集）
```

### 12.3 必须解决

```text
Sybil filtering
exchange address filtering
multi-chain normalization
data lag audit
token category eligibility
vendor cost-benefit analysis
```

### 12.4 付费数据规则

购买前必须回答：

```text
预计 edge 提升是否覆盖订阅成本？
样本量是否足够？
免费小样本是否已显示增量？
是否能按周频稳定更新？
```

---

## 13. Stage F：Tiny Live Pilot

### 13.1 定位

Tiny live pilot 不是正式上线，而是：

```text
真实摩擦实验
```

### 13.2 验证

```text
真实手续费
真实滑点
盘口可成交性
API 稳定性
订单拒绝路径
C1 entry block 与 rebalance 冲突
```

### 13.3 启动条件

必须全部满足：

```text
Stage A/A2 通过
至少 2–4 周 paper shadow 稳定
选币真实可交易
成本模型保守
C1 entry block formal_veto 可选；若未通过，只能 diagnostic_only
RiskLimits 未改变
用户明确批准
live_trading_enabled 单独审批
```

### 13.4 仓位限制

```text
单币 notional <= 100–200 USDT
总持仓 <= 500 USDT
只做 spot 或 1x perp proxy
不允许杠杆
不允许自动扩大仓位
不允许补仓摊低
必须一键停机
```

---

## 14. Stage G：Composite / AI Recipe / LightGBM

### 14.1 启动条件

```text
多个单因子有效
Stage A/C/E 至少两个阶段有增量
walk-forward 稳定
样本足够
成本后仍有效
```

### 14.2 LLM 只能生成 factor recipe

允许：

```json
{
  "factor_name": "cmom_active_nvt_composite",
  "hypothesis": "...",
  "inputs": ["cmom_14d", "active_address_growth_30d", "inverse_nvt"],
  "recipe": "rank(cmom_14d) + rank(active_address_growth_30d) + rank(inverse_nvt)",
  "expected_direction": "higher_score_outperforms"
}
```

禁止：

```text
LLM 直接改 execution
LLM 改 configs/base.py
LLM 根据 OOS 调参
LLM 写任意 strategy class
LLM 改成本模型
```

### 14.3 LightGBM 启动条件

```text
有效因子 >= 8
训练集 >= 24 个月
validation >= 6 个月
OOS >= 6 个月
walk-forward 可跑
缺失率可控
```

---

## 15. 推荐文件结构

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

configs/
  asset_aliases.json

scripts/
  audit_factor_lab_data_coverage.py
  build_factor_lab_daily_panel.py
  review_factor_lab_baseline.py
  review_factor_lab_robustness.py
  review_factor_lab_onchain_b_lite.py

tests/research/
  test_cross_sectional_asset_master.py
  test_cross_sectional_panel_builder.py
  test_cross_sectional_factors.py
  test_cross_sectional_portfolio_simulator.py

tests/scripts/
  test_audit_factor_lab_data_coverage.py
  test_build_factor_lab_daily_panel.py
  test_review_factor_lab_baseline.py

reports/factor_lab/
docs/reviews/
```

项目内推荐使用更明确的报告目录名：

```text
reports/cross_sectional_factor_lab/
```

如果历史上已生成 `reports/factor_lab/`，应迁移或在 review 中说明别名关系，避免报告目录漂移。

---

## 16. 决策标签

### Data

```text
factor_lab_data_unavailable
factor_lab_data_ready_with_bias
factor_lab_data_ready_formal
```

### Baseline

```text
factor_lab_baseline_failed
factor_lab_baseline_promising_continue_to_shadow
factor_lab_baseline_promising_continue_to_b_lite
```

### On-chain

```text
factor_lab_onchain_b_lite_failed
factor_lab_onchain_b_lite_promising_continue_to_stage_e
factor_lab_onchain_data_quality_failed
```

### Live

```text
factor_lab_paper_shadow_failed
factor_lab_paper_shadow_ready_for_tiny_pilot
factor_lab_tiny_pilot_failed
factor_lab_tiny_pilot_continue_observe
```

---

## 17. 执行纪律

1. Stage A 只做 long-only。
2. 成本用 `30 / 50 / 80 bps`。
3. Fast Track 必须标注幸存者偏差。
4. C1 只做 entry block。
5. 不做无成本做空。
6. 不买 on-chain 数据前先做 B-lite。
7. Active/NVT 是核心候选，但不是起手式。
8. 每个因子必须证明增量价值。
9. 每个失败实验必须写入 trace。
10. 任何 tiny live pilot 必须单独审批。
11. Stage 0 通过后必须进入 Stage A plan，不能把数据审计当成无限期研究。
12. Stage A daily panel 默认使用 pandas；不得用手写复杂循环替代可审计的 groupby/rank/rolling。
13. C1 在未正式通过前只能 diagnostic_only，不得影响主回测结论。
14. 不迁移 AIMM；只借鉴分层思想，不引入 agentic live decision loop。

---

## 18. 一句话总结

V3 的核心原则：

> 用 Fast Track 快速杀假设，用严格成本和偏差标注防止假回测；用 B-lite 小样本验证 Active Addresses / NVT 的战略价值；用 C1 做入场拦截；最终只把经过增量验证的因子推进到 shadow 和极小仓 pilot。
