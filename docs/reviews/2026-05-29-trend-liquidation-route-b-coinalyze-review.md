# Trend Liquidation Route-B Coinalyze Review Report

> 范围说明  
> 本报告只审查 `liquidation_cascade` 子策略在 **Route B-only** 条件下的历史可行性。  
> Route A 当前仍处于 `route_a_old_artifact_only` 状态，因此本报告不使用 Route C overlap 作为主判断门槛。

---

## 1. 核心结论

- **Route B 数据链已打通**；
- **Route B-only replay 没有给出继续保留当前版 `liquidation_cascade` 的正证据**；
- **当前最合理的策略结论是：`retire_liquidation_cascade_branch`**。

这不是因为“拿不到 liquidation 历史数据”，而是因为：

1. baseline 阈值下没有任何入场事件；
2. 适度放宽阈值后才出现极少量事件，但成本后仍为负；
3. 再激进放宽时事件数上升，但仍为负，且尾部更差。

---

## 2. Route B Data Status

本轮 Route B-only 审计使用 Coinalyze 第三方历史 liquidation 数据，结果如下：

- **数据源**：`coinalyze_liquidation_history`
- **数据状态**：`api_ok_non_empty_rows`
- **Route B joined_count**：`2393`
- **Route B 覆盖时长**：`1499.0h`
- **Route A joined_count**：`0`
- **Route C overlap**：`0`

对应产物：

- `reports/trend_regime/2026-05-30_liquidation_cascade_route_b_only_data_source_comparison.json`
- `reports/trend_regime/2026-05-30_liquidation_cascade_route_b_only_viability_summary.json`
- `reports/trend_regime/2026-05-30_liquidation_cascade_route_b_only_sensitivity.json`

解释：

- Route B 数据接线已经不是 blocker；
- Route A 当前仍未形成可用 overlap，不影响本轮 Route B-only 结论；
- 本轮的主判断只依赖 Route B historical replay。

---

## 3. Event Density And Reject Pattern

### Baseline 结果

- **input_row_count**：`2495`
- **entry_event_count**：`0`
- **events_per_30d**：`0.0`
- **capital_utilization_label**：`too_sparse`

### 主拦截项

- `vol_breakout_below_threshold`: `2184`
- `return_below_min`: `172`
- `missing_liquidation_fields`: `101`
- `oi_confirmation_below_min`: `8`
- `volume_below_min`: `30`

这说明当前定义下，`liquidation_cascade` 仍然主要被：

1. 波动突破门槛
2. 价格变动门槛
3. OI 确认门槛

拦在上游，而不是被 Route B 历史数据缺失拦住。

换句话说：

- **数据问题已经被基本排除**
- **当前更像是策略定义本身不过关**

---

## 4. Continuation / Mean Reversion Replay

在 baseline current 条件下：

- `continuation`: 所有持有周期 `4h / 8h / 12h / 24h` 下 `entry_event_count = 0`
- `mean_reversion`: 所有持有周期 `4h / 8h / 12h / 24h` 下 `entry_event_count = 0`

因此：

- baseline 没有任何可交易样本；
- 当前无法从 baseline replay 中证明 continuation 或 mean-reversion 任一方向存在可用 edge。

---

## 5. Sensitivity Result

### baseline_current

- `entry_event_count = 0`
- `mean_net_pnl_bps = 0.0`

### moderately_relaxed

- `entry_event_count = 1`
- `mean_net_pnl_bps = -80.8969`
- `median_net_pnl_bps = -80.8969`
- `win_rate = 0.0`

### aggressive_relaxed

- `entry_event_count = 5`
- `mean_net_pnl_bps = -71.7107`
- `median_net_pnl_bps = -80.8969`
- `win_rate = 0.2`
- `worst_trade_net_pnl_bps = -214.2846`
- `eligible_for_redefinition = false`

解释：

1. baseline 根本不出事件；
2. moderate 才勉强出 1 笔，但直接亏损；
3. aggressive 是噪音边界诊断，不具备重定义资格，而且结果仍然为负。

所以 sensitivity 给出的信号非常一致：

- **不是“阈值再微调一下就能救活”**
- 更像是 **这条策略在当前定义下本身就没有可保留性**

---

## 6. Trading Interpretation

从交易逻辑上看，这条策略想做的是：

1. 价格在 1 小时内已有明显方向移动；
2. OI 出现支持性的变化；
3. 再叠加 liquidation imbalance，判断是否继续顺势或做反转。

问题在于，本轮回放已经说明：

- 真正满足这三层条件的样本几乎没有；
- 就算通过放宽阈值“挤出”样本，成本后仍然不能转正；
- 对个人投资者而言，事件密度太低，资本利用效率非常差；
- 对研究流程而言，再继续堆数据工程已经不是当前主矛盾。

---

## 7. Final Decision

本轮 Route B-only 审计建议的最终决策为：

- **`retire_liquidation_cascade_branch`**

原因：

1. Route B 历史数据已接通，不再能把问题归因于“缺少 liquidation 数据”；
2. baseline 没有事件；
3. moderate / aggressive 放宽后仍为负；
4. 事件密度与资本利用效率都不支持继续投入。

---

## 8. Recommended Next Step

当前最稳的下一步不是继续磨这条策略，而是二选一：

1. 归档 `liquidation_cascade`，停止作为候选策略推进；
2. 如果仍想研究 liquidation 主题，则另起一条 **全新策略定义**，例如：
   - 更短周期；
   - 更纯粹的 liquidation-only signal；
   - 不再绑定当前这套 1h trend/return/OI 门槛结构。

本报告建议优先选择：

- **归档当前版 `liquidation_cascade`**
