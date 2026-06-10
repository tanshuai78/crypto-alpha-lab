# Cross-Sectional Factor Lab Stage A2.2 CMOM Diagnostic Design

**日期**：2026-06-10  
**阶段**：Stage A2.2  
**范围**：`cmom_14d_vs_momentum_30d_diagnostic_only`  
**前置结论**：Stage A1 证伪裸 30d momentum；Stage A2.1 证明 regime/cash fallback 能减亏但不能形成 alpha。  
**实盘状态**：`live_safe = false`；`paper_shadow_allowed = false`。

---

## 1. 核心问题

Stage A v1 失败后，不能直接判定“动量因子无效”。原因是论文中的 crypto momentum 更接近 `CMOM = past two-week return`，而 Stage A v1 使用的是：

```text
momentum_30d_skip_1d = close[t-1] / close[t-31] - 1
```

这两个口径不等价。Crypto 轮动速度快，30 天动量可能已经从“强者恒强”变成“追高接盘”。因此 Stage A2.2 只回答一个窄问题：

```text
14d CMOM 是否比当前 30d momentum 更适合 Binance spot 横截面轮动？
```

本阶段是 failure diagnostic，不是重新宣布 Stage A 有效，也不是进入实盘或 paper shadow 的依据。

---

## 2. 为什么 A2.2 先做 CMOM，而不是 3d rebalance

`3d rebalance` 回答的是：

```text
weekly rebalance 是否太慢？
```

但如果动量信号本身选错窗口，先加快调仓只会让错误信号交易得更频繁，并放大成本敏感性。

因此当前优先级调整为：

```text
A2.2: 14d CMOM vs 30d momentum
A2.3: 若 CMOM 有生命力，再做 regime-gated CMOM
A2.4: 若 regime-gated CMOM 有生命力，再做 volume confirmation
A2.x: 3d rebalance 作为后续 execution cadence diagnostic，不作为当前第一诊断项
```

---

## 3. 测试对象

### 3.1 对照组：30d momentum

沿用 Stage A v1：

```text
factor_name = momentum_30d_skip_1d
rebalance_date = t
signal_asof_date = t - 1 day
lookback_start_date = t - 31 days
factor_value = close[t-1] / close[t-31] - 1
```

### 3.2 候选组：14d CMOM

新增论文口径近似版本：

```text
factor_name = cmom_14d_skip_1d
rebalance_date = t
signal_asof_date = t - 1 day
lookback_start_date = t - 15 days
factor_value = close[t-1] / close[t-15] - 1
```

注意：这里的 `14d` 指使用过去 14 个完整 UTC 日的收益，不使用 rebalance 当日价格。

---

## 4. 固定不变的回测框架

为避免解释污染，A2.2 不改变以下条件：

```text
market = Binance spot
universe = Stage 0/Stage A 已审计的 current tradable high-liquidity universe
portfolio = top10 equal-weight
rebalance = weekly, Monday 00:00 UTC
cost_scenarios_round_trip_bps = [30, 50, 80]
liquidity_gate = point-in-time rolling 30d median quote volume
benchmark = BTC buy-and-hold, ETH buy-and-hold, universe equal-weight
```

允许保留：

```text
top5_equal_weight = concentration diagnostic only
```

禁止加入：

```text
3d rebalance
BTC/alt regime filter
volume confirmation
volatility-adjusted momentum
funding/OI veto
on-chain factors
LightGBM
core-satellite portfolio
```

---

## 5. 输出 Summary Schema

A2.2 summary 至少输出：

```json
{
  "stage": "stageA2_cmom_diagnostic",
  "decision": "cmom_diagnostic_completed",
  "live_usage": "not_allowed",
  "paper_shadow_allowed": false,
  "factor_variants": {
    "momentum_30d_skip_1d": {},
    "cmom_14d_skip_1d": {}
  },
  "primary_comparison": {
    "cmom_vs_30d_return_diff_pct": 0.0,
    "cmom_vs_30d_drawdown_diff_pct": 0.0,
    "cmom_vs_30d_vs_universe_ew_diff_pct": 0.0,
    "cmom_beats_30d_after_30bps": false,
    "cmom_top5_not_worse_than_top10": false
  },
  "next_action": "stop_price_only_momentum|proceed_to_regime_gated_cmom_design|run_3d_failure_diagnostic"
}
```

每个 factor variant 必须包含：

```json
{
  "performance": {
    "base_30bps_total_return_pct": 0.0,
    "stress_50bps_total_return_pct": 0.0,
    "crash_80bps_total_return_pct": 0.0,
    "max_drawdown_pct": 0.0,
    "turnover_median": 0.0
  },
  "benchmarks": {
    "vs_btc_total_return_pct": 0.0,
    "vs_eth_total_return_pct": 0.0,
    "vs_universe_equal_weight_total_return_pct": 0.0
  },
  "concentration": {
    "max_single_symbol_positive_pnl_share": 0.0,
    "max_single_symbol_abs_pnl_share": 0.0,
    "max_single_month_positive_pnl_share": 0.0,
    "max_single_month_abs_pnl_share": 0.0
  },
  "rebalance_quality": {
    "rebalance_count": 0,
    "insufficient_universe_ratio": 0.0,
    "median_selected_symbol_count": 0
  }
}
```

---

## 6. 判断标准

A2.2 不允许直接输出 `strategy_confirmed`。它只能输出诊断结论。

### 6.1 `proceed_to_regime_gated_cmom_design`

只有同时满足以下条件，才允许进入 regime-gated CMOM：

```text
cmom_14d 30bps total return 优于 30d momentum >= 10 percentage points；
cmom_14d max drawdown 不高于 30d momentum；
cmom_14d vs universe equal-weight 明确为正；
cmom_14d 不严重跑输 BTC，vs BTC >= -10 percentage points；
cmom_14d top5 diagnostic 不显著差于 top10；
max_single_month_positive_pnl_share <= 30%。
```

### 6.2 `run_3d_failure_diagnostic`

如果 CMOM 明显优于 30d，但仍然收益/回撤路径差，则允许后续做 3d diagnostic：

```text
CMOM improves ranking quality, but weekly cadence may be too slow.
```

### 6.3 `stop_price_only_momentum`

如果 CMOM 与 30d 一样接近 universe equal-weight，或仍显著跑输 BTC/ETH，则停止 price-only momentum 路线：

```text
price-only cross-sectional momentum does not provide enough alpha under current constraints.
```

---

## 7. 必须测试的实现口径

Implementation plan 必须覆盖：

1. `cmom_14d_skip_1d` 使用 `t-1` 和 `t-15`，不使用 rebalance 当日 close。
2. late-listed symbol 在没有完整 15 日 lookback 前不得进入 ranking。
3. 14d 和 30d 使用同一 universe、同一 rebalance calendar、同一 cost model。
4. top5 只作为 diagnostic，不参与主 decision。
5. summary 不允许给出 live-safe 或 paper-shadow 结论。
6. 空数据、rebalance 数不足、universe 不足必须输出 data unavailable，而不是策略失败。

---

## 8. 本设计的非目标

本阶段不解决：

```text
是否 3d 更好；
是否加 volume confirmation；
是否加 funding/OI；
是否使用 active addresses / NVT；
是否改成 BTC/ETH core + alt satellite；
是否做 LightGBM 多因子融合。
```

这些问题只有在 CMOM 至少显示出比 30d momentum 更强的基础生命力后，才值得继续。

---

## 9. Final Decision

```text
decision = proceed_to_stageA2_cmom_diagnostic_implementation_plan
scope = 14d_cmom_vs_30d_momentum_only
live_safe = false
paper_shadow_allowed = false
can_promote_strategy = false
```
