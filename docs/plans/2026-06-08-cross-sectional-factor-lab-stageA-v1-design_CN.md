# Cross-Sectional Factor Lab Stage A v1 Design

日期：2026-06-08  
策略线：`cross_sectional_factor_lab`  
阶段：`Stage A v1: exchange-only price + volume Fast Track`  
状态：设计稿  
前置依据：
- `docs/strategy_specs/cross_sectional_factor_lab_implementation_guide_CN_v3.md`
- `docs/reviews/2026-06-07-cross-sectional-factor-lab-stage0-data-coverage-review_CN.md`
- `reports/cross_sectional_factor_lab/factor_lab_data_coverage_summary.json`

---

## 1. 核心结论

Stage 0 已允许进入 Stage A，但允许范围必须精确限定为：

```text
market = Binance spot
mode = price_volume_fast_track
direction = long-only
data_scope = current_tradable_universe_only
bias_label = survivorship_bias_not_controlled
```

Stage A v1 的目标不是证明正式 alpha，而是快速验证一个最小、可证伪的问题：

```text
每周买入 Binance spot 高流动性 USDT 现货中，过去 30 天动量最强的 top 10，
扣除交易成本后，是否能跑赢 BTC、ETH 和 universe equal-weight 基准？
```

如果 v1 不能在这个最简单版本中表现出基本生命力，后续不应继续叠加 `LightGBM`、链上数据、C1 filter 或复杂多因子。

---

## 2. 已锁定决策

| 项目 | 决策 |
|---|---|
| `market` | `Binance spot` |
| `universe` | Stage 0 通过的高流动性 USDT spot |
| `history` | 最近 540 个完整 UTC 日 |
| `rebalance` | 每周一 00:00 UTC |
| `factor` | `momentum_30d_skip_1d` |
| `primary_portfolio` | top 10 equal-weight |
| `diagnostic_portfolio` | top 5 equal-weight，仅用于集中度诊断 |
| `direction` | long-only |
| `cost_scenarios_round_trip_bps` | base 30 / stress 50 / crash 80 |
| `optimistic_cost_diagnostic` | 10 bps per traded leg，仅诊断，不作为主结论 |
| `benchmarks` | BTC buy-and-hold、ETH buy-and-hold、universe equal-weight |
| `bias_label` | `survivorship_bias_not_controlled` |
| `live_usage` | 禁止，仅研究回测 |

---

## 3. 明确不做什么

Stage A v1 禁止扩大范围：

```text
不做 USDT perpetual；
不做 funding veto；
不做 OI veto；
不做 C1 entry block，只允许后续诊断字段；
不做 Active Addresses / NVT；
不做 market cap / size；
不做 LightGBM；
不做 long-short；
不做 paper trading；
不接 live scanner；
不做参数搜索。
```

这些禁令的目的不是保守，而是保护结论可解释性。v1 只回答 `30d momentum` 这一个问题。

---

## 4. 数据输入

Stage A v1 使用 Binance public spot daily OHLCV。

最低字段：

```text
symbol
date_utc
open
high
low
close
base_volume
quote_volume
```

时间口径：

```text
daily bar = UTC day
end_date = latest complete UTC day
history_days = 540
exclude_incomplete_today = true
```

数据质量要求：

```text
daily OHLCV coverage >= 0.95
quote_volume 可用；
close_price > 0；
rebalance 日之前必须有足够 lookback；
不能使用 rebalance 日之后的数据计算信号。
```

---

## 5. Warm-up 规则

Stage A v1 不能从 540 天样本的第一天直接开始调仓。

原因：

```text
momentum_30d_skip_1d 需要 31 个已完成 UTC daily bars；
rolling_30d_median_quote_volume_usdt 需要 30 个已完成 UTC daily bars；
两者都满足后，才允许出现 first_eligible_rebalance_date。
```

实现口径：

```text
warmup_days = max(31, 30)
first_eligible_rebalance_date = 第一个满足 warmup 且落在 Monday 00:00 UTC 的 rebalance_date
no positions before warmup complete
```

implementation plan 必须测试：

```text
test_first_rebalance_after_momentum_and_liquidity_warmup；
test_no_positions_before_warmup_complete。
```

---

## 6. Universe 规则

Stage A v1 的 universe 从 Stage 0 spot 可用结果派生。

静态排除：

```text
stablecoin base assets；
leveraged tokens；
wrapped / synthetic tokens if configured；
非 USDT quote；
被 Binance API 标记为不可交易或无足够 daily OHLCV 的 symbol。
```

流动性规则：

Stage 0 的当前 30d median quote volume 只用于筛选第一版候选池，不能作为历史回测中的 point-in-time 交易性证据。

Stage A v1 必须在每个 rebalance date 上重新计算：

```text
rolling_30d_median_quote_volume_usdt
```

并在当日只允许流动性通过的 symbol 进入 rank。

第一版阈值沿用 Stage 0：

```text
rolling_30d_median_quote_volume_usdt >= 20,000,000
```

该阈值后续 implementation plan 必须放入 `configs/base.py`，不得写死在 `src/`。

---

## 7. 因子定义

Stage A v1 只使用一个 alpha 因子：

```text
momentum_30d_skip_1d = close[t-1] / close[t-31] - 1
```

解释：

```text
rebalance 在 t 日 00:00 UTC 发生；
不能使用 t 日 close；
跳过最近 1 天，是为了降低短期反转和当日未完成数据污染；
信号窗口覆盖 t-31 到 t-1。
```

索引口径：

```text
rebalance_date = t；
signal_asof_date = rebalance_date - 1 day；
lookback_start_date = rebalance_date - 31 days；
momentum_30d_skip_1d = close[signal_asof_date] / close[lookback_start_date] - 1。
```

implementation plan 必须用测试锁定这个口径：

```text
test_momentum_30d_skip_1d_uses_t_minus_1_and_t_minus_31；
test_momentum_does_not_use_rebalance_day_close；
test_momentum_requires_31_prior_daily_bars。
```

排序规则：

```text
同一 rebalance date；
在可交易 universe 内按 momentum_30d_skip_1d 从高到低排序；
选择 top 10；
若不足 top 10，则该 rebalance 标记为 insufficient_universe，不强行建仓。
```

---

## 8. 组合构造

主组合规则：

```text
primary_portfolio = top10_equal_weight
target_count = 10
weighting = equal_weight
target_weight_each = 1 / selected_count
cash_weight = 0 if selected_count == 10 else residual cash
```

选择 top 10 的原因：

```text
降低单币偶然性；
降低 survivorship-bias 下由少数幸存小币制造的虚假结果；
更接近个人 spot long-only 组合的可执行分散度；
避免在 v1 中比较 top3/top5/top10 后挑最好结果。
```

top 10 的代价也必须承认：

```text
momentum 信号会被第 8-10 名稀释；
当 eligible universe 不足时，组合质量会下降；
若 top 10 通过但 top 5 崩溃，需要在 review 中标记信号集中度风险。
```

诊断组合：

```text
diagnostic_portfolio = top5_equal_weight
usage = concentration_diagnostic_only
```

`top5_equal_weight` 不参与主通过判定，不能用于参数搜索后宣布策略通过。它只用于判断失败或通过是否来自过度分散、过度集中或单币贡献。

第一版不做波动率缩放、不做 sector cap、不做单币手动 cap。原因：v1 是最小可证伪版本，先验证最基础动量结构是否存在。

仓位方向：

```text
long-only spot
no leverage
no margin
no short
```

---

## 9. 回测与成本

调仓规则：

```text
每周一 00:00 UTC 调仓；
用调仓日前已完成 daily bar 计算信号；
用调仓日 open 作为近似成交价格；
持有到下一次周一 00:00 UTC。
```

主成本规则：

```text
cost_scenarios_round_trip_bps = [30, 50, 80]
one_way_cost_bps = round_trip_cost_bps / 2
rebalance turnover = sum(abs(target_weight - previous_weight))
cost = turnover * one_way_cost_bps
```

说明：

```text
如果从 100% 现金买入 10 个币，turnover = 1.0；
在 30 bps round-trip 场景下，one_way_cost = 15 bps，首次建仓成本 = 15 bps；
如果从一组币完整换到另一组币，turnover 接近 2.0；
在 30 bps round-trip 场景下，完整换仓成本接近 30 bps；
现金不产生收益。
```

成本场景解释：

```text
base = 30 bps round-trip，主通过场景；
stress = 50 bps round-trip，稳健性场景；
crash = 80 bps round-trip，风险披露场景，不作为硬通过但必须报告。
```

可选诊断：

```text
optimistic_maker_like_diagnostic_only = 10 bps per traded leg
```

该诊断不能作为主结论，也不能替代 `30 / 50 / 80 bps` 主报告。

---

## 10. Benchmark

必须同时输出三个基准：

```text
BTC buy-and-hold
ETH buy-and-hold
universe equal-weight weekly rebalance
```

`universe equal-weight` 定义：

```text
每个 rebalance date；
使用同一可交易 universe；
所有通过流动性与数据质量门槛的 symbol 等权；
同样使用 30 / 50 / 80 bps round-trip cost_scenarios。
```

这样可以区分：

```text
策略收益来自整体 altcoin beta；
还是来自 momentum rank 的横截面选择能力。
```

成本公平性要求：

```text
BTC / ETH buy-and-hold 必须输出 net_with_entry_exit_cost；
初始买入扣 one_way_cost；
期末退出扣 one_way_cost；
universe equal-weight 使用与策略相同的 cost_scenario；
universe equal-weight 使用同一 rebalance date 上的 point-in-time eligible universe。
```

implementation plan 必须测试：

```text
test_universe_equal_weight_uses_same_point_in_time_eligible_universe；
test_universe_equal_weight_applies_same_cost_scenario；
test_btc_eth_buy_and_hold_applies_entry_exit_cost。
```

---

## 11. 输出报告

Stage A v1 summary 建议输出到：

```text
reports/cross_sectional_factor_lab/stageA_v1_momentum_summary.json
```

最低字段：

```json
{
  "run_mode": "stageA_v1_momentum_backtest",
  "market": "binance_spot",
  "strategy": "momentum_30d_skip_1d_top10_weekly",
  "bias_label": "survivorship_bias_not_controlled",
  "live_usage": "not_allowed",
  "history_days": 540,
  "rebalance": "weekly_monday_0000_utc",
  "cost_scenarios_round_trip_bps": [30.0, 50.0, 80.0],
  "optimistic_maker_like_diagnostic_per_leg_bps": 10.0,
  "primary_cost_scenario": "base_30_bps_round_trip",
  "portfolio_variants": ["top5_equal_weight", "top10_equal_weight"],
  "primary_portfolio": "top10_equal_weight",
  "portfolio": {
    "target_count": 10,
    "weighting": "equal_weight"
  },
  "warmup": {
    "momentum_lookback_days_required": 31,
    "liquidity_lookback_days_required": 30,
    "first_eligible_rebalance_date": "YYYY-MM-DD",
    "effective_rebalance_count": 0
  },
  "performance": {
    "by_cost_scenario": {
      "base_30_bps_round_trip": {
        "strategy_total_return_pct": 0.0,
        "strategy_max_drawdown_pct": 0.0,
        "strategy_annualized_return_pct": 0.0,
        "strategy_sharpe_proxy": 0.0,
        "turnover_sum": 0.0,
        "cost_paid_bps": 0.0
      }
    }
  },
  "benchmarks": {
    "btc_buy_and_hold_net_with_entry_exit_cost_pct": 0.0,
    "eth_buy_and_hold_net_with_entry_exit_cost_pct": 0.0,
    "universe_equal_weight_total_return_pct": 0.0
  },
  "excess_performance": {
    "vs_btc_total_return_pct": 0.0,
    "vs_eth_total_return_pct": 0.0,
    "vs_universe_equal_weight_total_return_pct": 0.0
  },
  "concentration": {
    "max_single_symbol_positive_pnl_share": 0.0,
    "max_single_symbol_abs_pnl_share": 0.0,
    "max_single_month_positive_pnl_share": 0.0,
    "max_single_month_abs_pnl_share": 0.0,
    "top_3_symbol_positive_pnl_share": 0.0,
    "pnl_contribution_denominator": "positive_pnl|absolute_pnl"
  },
  "rebalance_quality": {
    "rebalance_count": 0,
    "insufficient_universe_count": 0,
    "median_selected_symbol_count": 0,
    "average_turnover": 0.0
  },
  "decision": "stageA_v1_passed|stageA_v1_failed|stageA_v1_data_unavailable"
}
```

Review 文档建议输出到：

```text
docs/reviews/YYYY-MM-DD-cross-sectional-factor-lab-stageA-v1-review_CN.md
```

---

## 12. 通过与停止标准

Stage A v1 通过条件必须同时满足：

```text
base_30_bps_round_trip 下，strategy_total_return > BTC net total_return；
base_30_bps_round_trip 下，strategy_total_return > ETH net total_return；
base_30_bps_round_trip 下，strategy_total_return > universe_equal_weight total_return；
stress_50_bps_round_trip 下，strategy_total_return 不显著失效；
crash_80_bps_round_trip 必须报告，但不作为硬通过；
base_30_bps_round_trip 下，strategy_max_drawdown <= universe_equal_weight max_drawdown * 1.25；
base_30_bps_round_trip 下，net result after cost remains positive；
rebalance_count >= 50；
median_selected_symbol_count >= 10；
max_single_symbol_weight <= 0.10 at rebalance；
max_single_symbol_positive_pnl_share <= 0.35；
max_single_symbol_abs_pnl_share 必须报告，若极端集中则 fail；
max_single_month_positive_pnl_share <= 0.30；
max_single_month_abs_pnl_share 必须报告，若极端集中则 fail；
insufficient_universe_count / rebalance_count <= 0.10。
```

停止条件：

```text
费用后跑不赢 universe equal-weight；
回撤显著高于 universe equal-weight；
结果只靠 1-2 个 symbol 贡献；
rebalance 日大量 insufficient_universe；
数据缺失导致样本不可解释；
回测结果对单一月份或单一币高度集中。
```

若失败，不允许直接进入 `LightGBM` 或更多因子调参。下一步只能写 failure review，判断是：

```text
data failure；
momentum structure failure；
cost failure；
concentration failure；
benchmark failure。
```

---

## 13. 后续扩展条件

只有 Stage A v1 通过后，才允许讨论 Stage A v2。

可选扩展：

```text
3d_rebalance_diagnostic，Stage A2 第一优先项；
momentum_14d / momentum_60d robustness；
volume acceleration；
volatility filter；
drawdown-aware rank；
walk-forward split；
C1 entry block diagnostic overlay；
OKX spot coverage audit。
```

Stage A v1 implementation plan 可以保留以下 diagnostic-only robustness：

```text
momentum_14d_skip_1d_top10_weekly；
momentum_30d_skip_1d_top5_weekly。
```

这些诊断只用于解释失败或集中度风险，不能替代主测试，也不能用于调参后宣布通过。

仍不允许直接进入：

```text
live trading；
paper shadow；
LightGBM；
on-chain factor；
perp long-short。
```

---

## 14. 当前设计结论

```text
decision = proceed_to_stageA_v1_implementation_plan
required_fixes_status = applied_to_design
scope = binance_spot_momentum_30d_skip_1d_top10_weekly
evidence_level = hypothesis_screening_only
live_safe = false
```

下一步应编写：

```text
docs/plans/2026-06-08-cross-sectional-factor-lab-stageA-v1-implementation-plan_CN.md
```

该 implementation plan 必须采用 TDD，先写 pure-function tests，再实现数据 panel、factor、portfolio、cost、benchmark 和 summary。
