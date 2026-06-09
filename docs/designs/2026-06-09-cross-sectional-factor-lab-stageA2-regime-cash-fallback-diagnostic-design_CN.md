# Cross-Sectional Factor Lab Stage A2 Regime/Cash Fallback Diagnostic Design

**日期**：2026-06-09  
**阶段**：`Stage A2 Round 1`  
**设计类型**：`diagnostic_design`  
**范围**：`regime_cash_fallback_only`  
**上游依据**：`docs/reviews/2026-06-09-cross-sectional-factor-lab-stageA1-closure-review_CN.md`  
**实盘状态**：`live_safe = false`，`paper_shadow_allowed = false`  

---

## 1. 背景

Stage A v1 已冻结失败结论：

```text
strategy_30bps_total_return_pct      = -84.05
universe_equal_weight_total_return   = -84.61
excess_vs_universe_equal_weight      = +0.55
btc_buy_and_hold_net                 = -39.67
eth_buy_and_hold_net                 = -57.60
top5_diagnostic_total_return         = -89.66
decision                             = stageA_v1_failed
```

失败主因不是手续费，也不是 topN，而是：

```text
long-only alt beta 在该窗口极差；
裸 30d momentum 没有提供有效横截面 alpha；
策略没有判断什么时候不该持有 alt。
```

因此 Stage A2 Round 1 不做参数搜索，只做 regime/cash fallback 诊断。

---

## 2. 核心研究问题

Stage A2 Round 1 只回答一个问题：

```text
这个 long-only alt rotation 策略是否应该经常空仓？
```

换成交易语言：

```text
如果大盘或 alt universe 处于弱势，
把仓位切回 USDT cash，
能否显著降低回撤，
同时不把策略变成长期空仓的伪安全系统？
```

不回答的问题：

```text
是否应该用 3d rebalance？
是否应该用 14d momentum？
是否应该加入 volume confirmation？
是否应该加入 funding/OI？
是否应该加入 on-chain？
是否应该做 BTC/ETH core + alt satellite？
```

这些全部后置。

---

## 3. 诊断变体

Stage A2 Round 1 只允许三组对照。

### 3.1 `regime_none`

原始 Stage A v1 对照组。

```text
signal = momentum_30d_skip_1d
portfolio = top10_equal_weight
rebalance = weekly Monday UTC
regime_filter = none
fallback = none
```

用途：提供 v1 baseline。

### 3.2 `btc_ma20_cash`

BTC 趋势过滤。

```text
if BTC close[t-1] > BTC MA20[t-1]:
    hold top10 alt portfolio
else:
    hold USDT cash
```

设计理由：BTC 是 crypto 市场风险总开关。若 BTC 自身弱势，alt rotation 的 long-only beta 通常更危险。

风险：BTC 强不等于 alt 强，因此该过滤可能仍无法避免 alt universe 独立走弱。

### 3.3 `alt_universe_20d_return_cash`

Alt universe 自身趋势过滤。

```text
if universe_equal_weight_return_20d[t-1] > 0:
    hold top10 alt portfolio
else:
    hold USDT cash
```

设计理由：Stage A v1 的主要亏损来自 alt universe 本身崩盘，因此直接看 alt universe 状态可能比 BTC MA20 更贴近问题根因。

风险：universe equal-weight 是由当前可交易 universe 构成，仍带有幸存者偏差。

---

## 4. 信号与时间口径

所有 regime 规则必须使用 `t-1` 及更早数据。

```text
rebalance_date = t
signal_asof_date = t - 1 day
BTC MA20 window = [t-20, t-1]
universe_return_20d = universe_equal_weight_close[t-1] / universe_equal_weight_close[t-21] - 1
```

禁止：

```text
使用 rebalance_date 当天 close；
使用未来收益判断是否空仓；
使用 response period 里的价格反推 regime；
```

---

## 5. Cash Fallback 语义

`cash fallback` 表示持有 USDT，不赚取收益，也不承担 alt 风险。

```text
cash_return = 0.0
cash_turnover = previous_alt_weight_to_zero_cost + next_alt_entry_cost
cash_days_counted = true
```

必须计算从 alt 切到 cash、从 cash 切回 alt 的 turnover cost。否则 cash fallback 会被高估。

---

## 6. 必须输出的 Summary Schema

每个 regime variant 必须输出以下字段：

```json
{
  "variant": "regime_none|btc_ma20_cash|alt_universe_20d_return_cash",
  "regime_filter": {
    "filtered_rebalance_share": 0.0,
    "cash_days_share": 0.0,
    "alt_exposure_days_share": 0.0,
    "strategy_return_when_exposed": 0.0,
    "strategy_return_when_cash": 0.0,
    "mostly_cash_strategy": false
  },
  "performance": {
    "base_30bps_total_return_pct": 0.0,
    "stress_50bps_total_return_pct": 0.0,
    "crash_80bps_total_return_pct": 0.0,
    "max_drawdown_pct": 0.0,
    "max_drawdown_vs_v1_reduction_pct": 0.0,
    "turnover_median": 0.0
  },
  "benchmarks": {
    "btc_buy_and_hold_net_pct": 0.0,
    "eth_buy_and_hold_net_pct": 0.0,
    "universe_equal_weight_pct": 0.0,
    "vs_btc_total_return_pct": 0.0,
    "vs_eth_total_return_pct": 0.0,
    "vs_universe_equal_weight_total_return_pct": 0.0
  },
  "concentration": {
    "max_single_symbol_positive_pnl_share": 0.0,
    "max_single_month_positive_pnl_share": 0.0
  },
  "decision": "regime_filter_promising|regime_filter_reduces_damage_but_no_alpha|regime_filter_failed"
}
```

顶层 summary 必须包含：

```json
{
  "run_mode": "stageA2_regime_cash_fallback_diagnostic",
  "scope": "regime_cash_fallback_only",
  "variants": [],
  "winner_variant": null,
  "can_enter_stageA2_round2": false,
  "live_usage": "not_allowed",
  "paper_shadow_allowed": false,
  "bias_label": "survivorship_bias_not_controlled"
}
```

---

## 7. 判断标准

Round 1 只有在某个 regime variant 同时满足以下条件时，才允许进入 Stage A2 Round 2：

```text
max_drawdown_vs_v1_reduction >= 30%；
base_30bps 下相对 universe EW 有明确正超额；
不再严重跑输 BTC/ETH；
cash_days_share <= 60%；
turnover_median 不因 regime filter 异常升高；
max_single_month_positive_pnl_share <= 30%。
```

解释：

- 如果只是把 `-84%` 改成 `-60%`，但仍严重跑输 BTC/ETH，结论是 `regime_filter_reduces_damage_but_no_alpha`；
- 如果 cash_days_share 超过 60%，标记 `mostly_cash_strategy = true`，不能视为进攻型策略；
- 如果回撤下降但收益完全来自少数月份，不能进入 Round 2；
- 如果 `btc_ma20_cash` 与 `alt_universe_20d_return_cash` 都失败，则暂停 Stage A 进攻型路线。

---

## 8. 后续解锁规则

只有 Round 1 通过，才允许进入：

```text
A2.2 3d rebalance diagnostic
A2.3 14d momentum vs 30d momentum
A2.4 volume confirmation
A2.5 volatility-adjusted momentum
```

仍然后置：

```text
funding/OI veto
on-chain Active Addresses / NVT
LightGBM
regime-aware BTC/ETH core + alt satellite
```

原因：这些会引入新数据源、新参数或组合结构升级，不能用来掩盖 Round 1 失败。

---

## 9. 不变量与安全边界

1. 研究输出不得接入 live scanner。
2. 研究输出不得接入 paper shadow。
3. 不允许改变全局交易风控开关。
4. 不允许改变 Stage A v1 summary 作为 baseline 的语义。
5. 不允许把 diagnostic result 当作 strategy pass。
6. 所有参数必须进入 `configs/base.py`，不能散落在脚本里。
7. 所有新行为必须先写测试，再实现。

---

## 10. 设计结论

```text
decision = proceed_to_stageA2_regime_cash_fallback_implementation_plan
scope = regime_cash_fallback_only
variants = regime_none | btc_ma20_cash | alt_universe_20d_return_cash
not_allowed_now = 3d_as_pass_fail | 14d_search | volume_filter | vol_adjusted | funding_oi | onchain | lightgbm | core_satellite
live_safe = false
paper_shadow_allowed = false
```
