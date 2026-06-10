# Cross-Sectional Factor Lab Stage A2 Regime/Cash Fallback Review

**日期**：2026-06-10  
**阶段**：Stage A2 Round 1  
**范围**：regime_cash_fallback_only  
**输入报告**：reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json  
**实盘状态**：live_usage = not_allowed；paper_shadow_allowed = False  

## 1. 结论

- `decision`: `stageA2_round1_completed`
- `winner_variant`: `None`
- `can_enter_stageA2_round2`: `False`
- `failure_type`: `structure_failure`
- `failure_reason`: `btc_ma20_cash:drawdown_reduction_insufficient|still_underperforms_btc_by_more_than_10pct|positive_pnl_month_concentration_above_30pct, alt_universe_20d_return_cash:still_underperforms_btc_by_more_than_10pct|mostly_cash|positive_pnl_month_concentration_above_30pct`

## 2. 三组变体结果

| variant | decision | rebalances | 30bps return | max DD | DD reduction | cash days | vs BTC | vs ETH | vs EW | max month +PnL share |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| regime_none | regime_filter_failed | 77 | -84.05% | 84.44% | 0.00% | 0.00% | -44.38% | -26.45% | 0.55% | 40.52% |
| btc_ma20_cash | regime_filter_failed | 77 | -61.08% | 64.77% | 23.30% | 53.25% | -21.41% | -3.48% | 23.53% | 52.74% |
| alt_universe_20d_return_cash | regime_filter_reduces_damage_but_no_alpha | 77 | -53.54% | 57.48% | 31.93% | 61.04% | -13.87% | 4.06% | 31.06% | 65.55% |

## 3. 失效类型与归因

- `data_failure`: 数据不足、有效 rebalance 数不足、诊断未完成。
- `density_failure`: 本轮不适用；Stage A2 不是事件密度研究。
- `structure_failure`: regime filter 未能同时降低回撤、保持相对 benchmark 表现、避免 mostly-cash，并且收益不应集中在单一月份。
- `execution_cost_failure`: 若 30/50/80 bps 成本场景下改善只在低成本成立，应归入该类。
- `confirmed_next_action`: 只有 `can_enter_stageA2_round2 = true` 时成立。

本次归类：`structure_failure`，原因：`btc_ma20_cash:drawdown_reduction_insufficient|still_underperforms_btc_by_more_than_10pct|positive_pnl_month_concentration_above_30pct, alt_universe_20d_return_cash:still_underperforms_btc_by_more_than_10pct|mostly_cash|positive_pnl_month_concentration_above_30pct`。

## 4. 口径说明

- benchmark 使用 `first_rebalance_open_to_last_valid_exit_open`。
- Stage A2 Round 1 是 weekly equal-length period，因此 `cash_rebalance_period_share` 与 `cash_days_share` 等价。
- 当前 universe 仍是 current tradable universe，存在 survivorship bias。
- 结果不能进入实盘，不能作为 paper shadow 准入依据。

## 5. 下一步

A2.1 的事实结论已经冻结：regime/cash fallback 能减亏，但没有形成进攻型 alpha。下一步不应直接扩大到多分支调参，也不应默认转向 B-lite。

当前推荐进入：

```text
Stage A2.2 = 14d CMOM vs 30d momentum diagnostic
```

理由：论文中的 crypto momentum 更接近 `past two-week return / CMOM`，而 Stage A v1 使用的是 `30d momentum`。因此在关闭 price-only momentum 路线前，需要先判断失败是否来自动量窗口口径偏离。

A2.2 只允许回答一个问题：

```text
14d CMOM 是否明显优于当前 30d momentum？
```

后续路线：

1. 如果 14d CMOM 明显优于 30d，进入 `regime-gated CMOM` 设计；
2. 如果 14d CMOM 有改善但仍路径很差，再做 `3d rebalance failure diagnostic`；
3. 如果 14d CMOM 仍接近 universe equal-weight 或显著跑输 BTC，停止 price-only momentum，转入 B-lite 非价格因子可行性讨论。

`3d rebalance` 不再作为 A2.2 第一优先，因为它回答的是调仓频率问题；当前更基础的问题是：Stage A v1 是否用了错误的动量窗口。
