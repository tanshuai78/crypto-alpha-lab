# Extreme Funding 参数敏感性审计复检（Pre-Orderbook）

## 1. 核心结论

本轮结论：**不进入 `orderbook-aware replay`**。

原因不是数据链路问题，而是硬门未达标：
- 在 `conservative_1_interval`（保守假设）下，DOGE/XRP 的候选数都为 0。
- 有候选只出现在 `optimistic_2_intervals` + 放宽参数组合下。
- 即使个别组合出现正 `median_net_pnl_bps`，样本量也只有 1-2 笔，不具备统计可信度。

这意味着当前策略对“必须收 2 期 funding 且门槛放宽”的依赖过强，不满足进入下一阶段的稳健性要求。

## 2. 审计输入与覆盖

```json
{
  "doge_input_row_count": 230,
  "xrp_input_row_count": 275,
  "param_set_count": 162,
  "coverage_quality": "historical_basis_proxy_not_depth_aware",
  "depth_aware": false
}
```

说明：本轮仍是历史 proxy replay，不是深度感知回放，不可用于 live 放行。

## 3. 候选侧（Candidate Sensitivity）

```json
{
  "DOGE": {
    "nonzero_candidate_sets": 81,
    "conservative_nonzero_sets": 0,
    "best_candidate_count": 2,
    "best_candidate_param": {
      "annualized_threshold_pct": 80.0,
      "assumption_level": "optimistic_2_intervals",
      "basis_absorption_max_ratio": 0.3,
      "expected_holding_intervals": 2,
      "max_slippage_bps": 8.0,
      "min_expected_funding_income_bps": 30.0
    },
    "top_reject_reasons": [
      "annualized_funding_below_trade_threshold",
      "expected_funding_income_below_min"
    ]
  },
  "XRP": {
    "nonzero_candidate_sets": 54,
    "conservative_nonzero_sets": 0,
    "best_candidate_count": 1,
    "best_candidate_param": {
      "annualized_threshold_pct": 80.0,
      "assumption_level": "optimistic_2_intervals",
      "basis_absorption_max_ratio": 0.3,
      "expected_holding_intervals": 2,
      "max_slippage_bps": 8.0,
      "min_expected_funding_income_bps": 30.0
    },
    "top_reject_reasons": [
      "annualized_funding_below_trade_threshold",
      "expected_funding_income_below_min"
    ]
  }
}
```

解读：当前主阻塞仍是 funding 强度门槛，不是 `basis_absorbed` 主导。

## 4. 影子侧（Shadow Sensitivity）

```json
{
  "DOGE_best_shadow": {
    "median_net_pnl_bps": 4.1818151852,
    "win_rate": 1.0,
    "candidate_count": 1,
    "shadow_trade_count": 1,
    "param": {
      "annualized_threshold_pct": 80.0,
      "assumption_level": "optimistic_2_intervals",
      "basis_absorption_max_ratio": 0.3,
      "expected_holding_intervals": 2,
      "max_slippage_bps": 8.0,
      "min_expected_funding_income_bps": 70.0
    }
  },
  "XRP_best_shadow": {
    "median_net_pnl_bps": 39.7351849295,
    "win_rate": 1.0,
    "candidate_count": 1,
    "shadow_trade_count": 1,
    "param": {
      "annualized_threshold_pct": 80.0,
      "assumption_level": "optimistic_2_intervals",
      "basis_absorption_max_ratio": 0.3,
      "expected_holding_intervals": 2,
      "max_slippage_bps": 8.0,
      "min_expected_funding_income_bps": 30.0
    }
  }
}
```

解读：
- `shadow_trade_count == candidate_count`，链路一致性通过。
- 但最佳结果依赖乐观假设，且样本过少，不具备决策稳健性。

## 5. 硬决策门结果

本轮采用的进入 `orderbook-aware replay` 最低条件：
1. `conservative_1_interval` 下 `candidate_count > 0`
2. `median_net_pnl_bps > 20`
3. `win_rate > 55%`
4. 结果不依赖极端放宽组合

结果：**失败**。

```json
{
  "DOGE_decision_gate_snapshot": {
    "any_candidate": true,
    "conservative_has_candidate": false,
    "best_median_net_pnl_bps": 4.1818151852
  },
  "XRP_decision_gate_snapshot": {
    "any_candidate": true,
    "conservative_has_candidate": false,
    "best_median_net_pnl_bps": 39.7351849295
  },
  "decision": "do_not_enter_orderbook_aware_replay"
}
```

## 6. 下一步动作

- 不进入 `orderbook-aware replay`。
- 回到策略定义层，优先处理：
  1. `expected_holding_intervals` 假设依赖过强（只能 2 interval 才有候选）
  2. funding 强度门槛与样本稀疏问题（`annualized_threshold` / `min_expected_income`）
  3. 形成“保守口径可触发”的新候选定义，再重跑本审计。

在没有保守口径候选前，不推进 execution 相关工作。
