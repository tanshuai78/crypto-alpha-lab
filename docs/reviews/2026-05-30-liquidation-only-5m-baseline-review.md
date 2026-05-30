# Liquidation-Only 5m Baseline Research Review Report

## 1. 决策概要 (Decision Summary)

- **最终决策 (Final Decision)**: `RETIRE_LIQUIDATION_ONLY_5M_BASELINE`
- **数据跨度 (Data Span)**: `10.00 天` (物理连续 5m bars 数量: `14397`)
- **触发事件总数 (Total Event Count)**: `54` 个 (每 30 天均值: `162.00` 次)
- **决策原因 (Decision Reasons)**:
  - No hypothesis passed all performance gates on a cost-adjusted basis. Hypothesis continuation failed performance gates across horizons (passed only on []); Hypothesis mean_reversion failed performance gates across horizons (passed only on [])

---

## 2. 假设表现分析 (Hypothesis Performance)

### A. Continuation Hypothesis (顺势假设)
衡量大额清算后，价格在未来 `1 / 2 / 3` 个 5m bar 是否继续顺着清算压力方向移动（即 short 爆仓进多，long 爆仓进空）。

| Horizon (Hold) | Event Count | Median (Gross) | Median (Cost-Adj) | Win Rate (Cost-Adj) | Worst Trade (Cost-Adj) |
|---|---|---|---|---|---|
| +1 bar (5m) | 54 | -0.29 bps | -16.29 bps | 22.2% | -93.76 bps |
| +2 bars (10m) | 54 | 3.07 bps | -12.93 bps | 24.1% | -145.47 bps |
| +3 bars (15m) | 54 | 2.83 bps | -13.17 bps | 33.3% | -100.26 bps |

### B. Mean Reversion Hypothesis (反转假设)
衡量大额清算后，清算压力耗尽导致价格迅速反转（即 short 爆仓进空，long 爆仓进多）。

| Horizon (Hold) | Event Count | Median (Gross) | Median (Cost-Adj) | Win Rate (Cost-Adj) | Worst Trade (Cost-Adj) |
|---|---|---|---|---|---|
| +1 bar (5m) | 54 | 0.29 bps | -15.71 bps | 22.2% | -104.41 bps |
| +2 bars (10m) | 54 | -3.07 bps | -19.07 bps | 22.2% | -91.54 bps |
| +3 bars (15m) | 54 | -2.83 bps | -18.83 bps | 29.6% | -107.49 bps |

---

## 3. 统计质量控制与反拟合审查 (Anti-Snooping Audit)

### A. 币种集中度 (Symbol Concentration)
清算特征是否集中在单一币种，导致策略其实只对单个币种生效？
- **BTC/USDT**: 11 次事件 (占比 20.4%)
- **DOGE/USDT**: 9 次事件 (占比 16.7%)
- **ETH/USDT**: 12 次事件 (占比 22.2%)
- **SOL/USDT**: 9 次事件 (占比 16.7%)
- **XRP/USDT**: 13 次事件 (占比 24.1%)

### B. 时间分片样本一致性 (By-Period Consistency)
将事件按时间先后对半切分，检验两段独立子样本的表现是否具有符号一致性：
- **第一半段 (First Half Median Cost-Adj)**: -20.94 bps
- **第二半段 (Second Half Median Cost-Adj)**: -4.71 bps
- **符号一致性 (Consistent Sign)**: `PASS`

---

## 4. 交易层解读与下一步计划 (Trading Interpretation)

1. **资金利用率与密度**:
   5分钟周期的纯清算事件密度对实盘的资金效率提出了极高要求。在 lookback 期间内探测到的合格事件数为 `54`。
2. **Hypothesis 结论**:
   - `continuation` 在扣除最小 `16.0` bps 的摩擦成本后，主要持仓周期的表现是否具有统计显著性？
   - `mean_reversion` 表现如何？是否在爆仓后的情绪性逆转期表现更好？
3. **下一步执行计划**:
   - 如果决策为 `CONTINUE_TO_PHASE2_ENHANCEMENTS`：进入 Phase 2，包括引入 OI 二级确认与订单簿深度的执行模拟。
   - 如果决策为 `RETIRE`：归档该研究方向，将资金和算力倾斜回 carry 和 multi-day basisdesk。
