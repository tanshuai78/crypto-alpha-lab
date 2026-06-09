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
- `failure_reason`: `btc_ma20_cash:drawdown_reduction_insufficient, alt_universe_20d_return_cash:mostly_cash`

## 2. 三组变体结果

| variant | decision | rebalances | 30bps return | max DD | DD reduction | cash days | vs BTC | vs ETH | vs EW |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| regime_none | regime_filter_failed | 77 | -84.05% | 84.44% | 0.00% | 0.00% | -44.38% | -26.45% | 0.55% |
| btc_ma20_cash | regime_filter_failed | 77 | -61.08% | 64.77% | 23.30% | 53.25% | -21.41% | -3.48% | 23.53% |
| alt_universe_20d_return_cash | regime_filter_reduces_damage_but_no_alpha | 77 | -53.54% | 57.48% | 31.93% | 61.04% | -13.87% | 4.06% | 31.06% |

## 3. 失效类型与归因

- `data_failure`: 数据不足、有效 rebalance 数不足、诊断未完成。
- `density_failure`: 本轮不适用；Stage A2 不是事件密度研究。
- `structure_failure`: regime filter 未能同时降低回撤、保持相对 benchmark 表现、避免 mostly-cash。
- `execution_cost_failure`: 若 30/50/80 bps 成本场景下改善只在低成本成立，应归入该类。
- `confirmed_next_action`: 只有 `can_enter_stageA2_round2 = true` 时成立。

本次归类：`structure_failure`，原因：`btc_ma20_cash:drawdown_reduction_insufficient, alt_universe_20d_return_cash:mostly_cash`。

## 4. 口径说明

- benchmark 使用 `first_rebalance_open_to_last_valid_exit_open`。
- Stage A2 Round 1 是 weekly equal-length period，因此 `cash_rebalance_period_share` 与 `cash_days_share` 等价。
- 当前 universe 仍是 current tradable universe，存在 survivorship bias。
- 结果不能进入实盘，不能作为 paper shadow 准入依据。

## 5. 下一步

暂停 Stage A exchange-only momentum line 的扩展；先做 closure decision：1. 是否执行 A2.2 3d diagnostic；2. 是否转向 B-lite 非价格因子可行性；3. 是否关闭当前 Factor Lab 路线。
