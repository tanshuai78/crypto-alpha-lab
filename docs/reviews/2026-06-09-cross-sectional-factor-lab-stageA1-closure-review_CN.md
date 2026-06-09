# Cross-Sectional Factor Lab Stage A1 Closure Review

**日期**：2026-06-09  
**阶段**：`Stage A1 Closure`  
**对象**：`Stage A v1 Binance Spot 30d momentum weekly top10`  
**最终决策**：`stageA_v1_failed_frozen`  
**下一步决策**：`proceed_to_stageA2_diagnostic_design`  
**Stage A2 Round 1 范围**：`regime_cash_fallback_only`  
**实盘状态**：`live_usage = not_allowed`  
**偏差标签**：`survivorship_bias_not_controlled`  

---

## 1. Closure 结论

Stage A v1 失败结论正式冻结：

```text
Binance spot current-tradable high-liquidity universe 中，
每周买入 momentum_30d_skip_1d 排名前 10 的币，
long-only 等权持仓，
在 30/50/80 bps round-trip 成本约束下，
没有形成可用进攻型 alpha。
```

该结论来自复跑后的 Stage A v1 summary：

```text
strategy_30bps_total_return_pct      = -84.05
universe_equal_weight_total_return   = -84.61
excess_vs_universe_equal_weight      = +0.55
btc_buy_and_hold_net                 = -39.67
eth_buy_and_hold_net                 = -57.60
top5_diagnostic_total_return         = -89.66
max_single_month_positive_pnl_share  = 40.52%
decision                             = stageA_v1_failed
```

核心含义：

- 策略几乎和全市场 alt 等权一起崩，只比等权多 `+0.55%`；
- 策略明显跑输 BTC 和 ETH；
- top5 更集中动量组合更差，说明“更集中追强势币”没有救；
- 成本不是主因，主因是 `long-only alt beta` 和裸 30d 动量缺乏有效横截面 alpha；
- 当前 universe 未控制退市币，真实历史表现可能更差。

---

## 2. 冻结规则

以下动作被明确禁止：

1. 不允许继续调低交易成本来拯救 v1。
2. 不允许把 `top10` 改成 `top5/top20/topN` 后宣布 v1 通过。
3. 不允许缩短历史窗口，只挑有利月份重新定义 v1。
4. 不允许把 diagnostic 结果当作正式通过结果。
5. 不允许进入 paper shadow、live scanner 或真实下单。
6. 不允许在未写 A2 plan 前加入 LightGBM、on-chain、funding/OI 或复杂组合因子。
7. 不允许一次性并行实现 `3d + 14d + volume + vol-adjusted + funding/OI + on-chain`，防止多重比较和解释污染。

允许保留的内容：

1. Stage A v1 代码作为 baseline backtest harness。
2. Stage A v1 summary 作为失败证据。
3. Stage A v1 review 作为 A2 的对照基准。
4. `top5_equal_weight` 只作为 concentration diagnostic，不参与通过判定。

---

## 3. 已经证伪的命题

已经证伪：

```text
裸 30d price momentum + weekly rebalance + top10 equal-weight + long-only spot alt
可以在 Binance spot 高流动性 universe 中形成可用进攻型 alpha。
```

证伪原因：

1. `momentum_30d_skip_1d` 只让等权亏损从 `-84.61%` 变为 `-84.05%`，提升幅度不足以覆盖交易误差和幸存者偏差。
2. 策略跑输 BTC/ETH，说明复杂轮动不如持有核心资产。
3. top5 更差，说明失败不是因为 top10 过度分散。
4. 单月正收益贡献过高，说明盈利窗口不可重复。

---

## 4. 尚未证伪但暂不进入 Round 1 的命题

以下命题仍有研究价值，但不能进入 Stage A2 Round 1 implementation：

1. `3d rebalance` 是否能解决周频过慢问题；
2. `momentum_14d_skip_1d` 是否比 30d momentum 更适合 crypto；
3. `volume confirmation` 是否能过滤无资金确认的假动量；
4. `volatility-adjusted momentum` 是否能避免高噪声追涨；
5. `funding/OI crowding veto` 是否能过滤杠杆拥挤；
6. `Active Addresses / NVT` 是否能提供非价格维度 alpha；
7. `regime-aware BTC/ETH core + alt satellite` 是否能形成更完整的组合框架。

后置原因：

```text
如果 Round 1 连“什么时候不该持有 alt”都回答不了，
后面的 3d、14d、volume、funding/OI、on-chain 都容易变成新一轮过拟合搜索。
```

---

## 5. Stage A2 Round 1 核心问题

Stage A2 Round 1 只回答一个问题：

```text
这个策略是否应该经常空仓？
```

不是先回答：

```text
该用 14d 还是 30d？
该用 weekly 还是 3d？
该用什么 volume threshold？
是否应该加入 funding/OI 或 on-chain？
```

原因：

```text
Stage A v1 最大失败不是手续费，也不是 topN，
而是 long-only alt beta 在该窗口极差。
因此第一优先级必须是判断什么时候不该持有 alt。
```

---

## 6. Stage A2 Round 1 设计边界

Stage A2 Round 1 只允许三组对照：

```text
regime_none:
  原始 Stage A v1，对照组。

btc_ma20_cash:
  BTC close[t-1] > BTC MA20[t-1] 才持 alt；
  否则持 USDT cash。

alt_universe_20d_return_cash:
  universe_equal_weight_return_20d[t-1] > 0 才持 alt；
  否则持 USDT cash。
```

不得加入：

```text
3d rebalance pass/fail；
14d/30d lookback 对比；
volume confirmation；
volatility-adjusted momentum；
funding/OI veto；
on-chain factor；
LightGBM；
core-satellite portfolio construction。
```

---

## 7. Stage A2 Round 1 必须输出的审计字段

每个 regime 版本必须输出：

```json
{
  "regime_filter": {
    "filtered_rebalance_share": 0.0,
    "cash_days_share": 0.0,
    "alt_exposure_days_share": 0.0,
    "strategy_return_when_exposed": 0.0,
    "strategy_return_when_cash": 0.0
  },
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
    "max_single_month_positive_pnl_share": 0.0
  }
}
```

解释规则：

- 如果回撤下降只是因为 80% 时间持现金，而收益仍跑输 BTC/ETH，则不是 alpha；
- 如果 cash fallback 让亏损减少但无法跑赢 BTC/ETH，结论应是 `regime_filter_reduces_damage_but_no_alpha`；
- 如果 cash_days_share 超过 60%，必须标记为 `mostly_cash_strategy`，不能视为进攻型策略通过。

---

## 8. Stage A2 Round 1 继续/停止标准

Round 1 只有在同时满足以下条件时，才允许进入 A2.2/A2.3：

```text
max_drawdown_vs_v1_reduction >= 30%；
base_30bps 下相对 universe EW 有明确正超额；
不再严重跑输 BTC/ETH；
cash_days_share <= 60%；
turnover 没有因 regime filter 异常升高。
```

如果只把 `-84%` 改成 `-60%`，但仍大幅跑输 BTC/ETH，则停止进攻型 Stage A 路线，不能转入 B-lite on-chain。

---

## 9. 后续路线图，仅在 Round 1 通过后解锁

### A2.2 3d rebalance diagnostic

目标：判断 weekly rebalance 是否太慢。只能作为 diagnostic，不能作为独立 pass/fail 主策略。

### A2.3 14d momentum vs 30d momentum

目标：验证 crypto 是否更适合较短周期动量。只允许 `14d vs 30d`，不能做大量 lookback search。

### A2.4 volume confirmation

目标：过滤没有成交量确认的价格动量。第一版只能作为 veto，不作为新 alpha。

### A2.5 volatility-adjusted momentum

目标：避免买入“涨很多但乱跳”的高噪声币。必须证明改善稳定性，而不是仅降低暴露。

### A2.6 funding/OI veto

后置。它属于 perp/funding 维度，只有 price/volume/regime 诊断有生命力后才值得加。

### Stage B-lite on-chain factor

后置。只有 A2 证明 exchange-only 框架仍有生命力，才进入 Active Addresses / NVT / MVRV。

### Regime-aware BTC/ETH core + alt satellite

后置。它是组合结构升级，不是 Round 1 诊断项。只有 regime/cash fallback 证明“少持有 alt”有效后，才值得设计核心-卫星组合。

---

## 10. 当前推荐下一步

下一步不是继续修改 Stage A v1，而是写 Stage A2 diagnostic design。

Stage A2 design 必须固定：

```text
round = A2 Round 1
scope = regime_cash_fallback_only
variants = [regime_none, btc_ma20_cash, alt_universe_20d_return_cash]
paper_shadow_allowed = false
live_safe = false
```

---

## 11. Final Decision

```text
decision = stageA_v1_failed_frozen
can_tune_stageA_v1 = false
can_enter_stageA2_diagnostics = true
stageA2_round1_scope = regime_cash_fallback_only
stageA2_round1_variants = regime_none | btc_ma20_cash | alt_universe_20d_return_cash
not_allowed_now = 3d_as_pass_fail | 14d_search | volume_filter | vol_adjusted | funding_oi | onchain | lightgbm | core_satellite
live_safe = false
paper_shadow_allowed = false
```
