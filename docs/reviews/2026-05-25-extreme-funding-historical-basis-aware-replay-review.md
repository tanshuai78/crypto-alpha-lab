# Extreme Funding Historical Basis-Aware Replay 阶段性结论

## 1. 核心结论

本轮不是 live approval。

本轮结论是：

- 历史 basis-aware 数据链路已跑通，DOGE/XRP 都拿到了可用 `basis_row`。
- 在当前 Phase 1B 门槛下，DOGE/XRP 的 `candidate_count` 都是 0。
- 主拒绝原因不是 `basis_absorbed`，而是 `annualized_funding_below_trade_threshold` 与 `expected_funding_income_below_min`。
- 这意味着当前门槛下，历史样本更多是 funding 强度不够，而不是先被基差直接吃掉。

## 2. 数据覆盖

```json
{
  "DOGEUSDT_dataset_summary": {
    "alignment_miss_count": 0,
    "basis_row_count": 230,
    "coverage_quality": "historical_basis_proxy_not_depth_aware",
    "depth_aware": false,
    "depth_source": "static_min_capacity_proxy",
    "fetch_error_count": 0,
    "futures_empty_count": 0,
    "has_basis_rows": true,
    "max_price_time_diff_ms": 0,
    "missing_basis_count": 0,
    "parse_error_count": 0,
    "request_count": 460,
    "row_error_count": 0,
    "selected_funding_row_count": 230,
    "spot_empty_count": 0,
    "status": "ok",
    "symbols": [
      "DOGE/USDT"
    ]
  },
  "XRPUSDT_dataset_summary": {
    "alignment_miss_count": 0,
    "basis_row_count": 275,
    "coverage_quality": "historical_basis_proxy_not_depth_aware",
    "depth_aware": false,
    "depth_source": "static_min_capacity_proxy",
    "fetch_error_count": 0,
    "futures_empty_count": 0,
    "has_basis_rows": true,
    "max_price_time_diff_ms": 0,
    "missing_basis_count": 0,
    "parse_error_count": 0,
    "request_count": 550,
    "row_error_count": 0,
    "selected_funding_row_count": 275,
    "spot_empty_count": 0,
    "status": "ok",
    "symbols": [
      "XRP/USDT"
    ]
  }
}
```

## 3. Candidate Replay

```json
{
  "DOGEUSDT_candidate_summary": {
    "candidate_count": 0,
    "coverage_quality": "historical_basis_proxy_not_depth_aware",
    "depth_aware": false,
    "depth_source": "static_min_capacity_proxy",
    "input_row_count": 230,
    "reject_reason_counts": {
      "annualized_funding_below_trade_threshold": 87,
      "expected_funding_income_below_min": 143
    },
    "status": "ok"
  },
  "XRPUSDT_candidate_summary": {
    "candidate_count": 0,
    "coverage_quality": "historical_basis_proxy_not_depth_aware",
    "depth_aware": false,
    "depth_source": "static_min_capacity_proxy",
    "input_row_count": 275,
    "reject_reason_counts": {
      "annualized_funding_below_trade_threshold": 100,
      "expected_funding_income_below_min": 175
    },
    "status": "ok"
  }
}
```

解释：

- 这轮没有出现 `basis_absorbed` 主导拒绝，说明历史窗口里更核心的约束是 funding 强度门槛。
- 结论仍然只能用于研究判断，不可推导为可执行策略结论，因为 `depth_aware=false`。

## 4. Shadow Replay

```json
{
  "DOGEUSDT_shadow_summary": {
    "coverage_quality": "historical_basis_proxy_not_depth_aware",
    "depth_aware": false,
    "depth_source": "static_min_capacity_proxy",
    "exit_reason_counts": {
      "basis_loss_halt": 78,
      "funding_decay": 38,
      "funding_flip": 7,
      "max_holding_intervals_reached": 104,
      "path_exhausted": 2
    },
    "mean_net_pnl_bps": -2.5583678196855897,
    "median_net_pnl_bps": -6.1268314411,
    "shadow_trade_count": 229,
    "status": "ok",
    "symbols": [
      "DOGE/USDT"
    ],
    "win_rate": 0.4279475982532751
  },
  "XRPUSDT_shadow_summary": {
    "coverage_quality": "historical_basis_proxy_not_depth_aware",
    "depth_aware": false,
    "depth_source": "static_min_capacity_proxy",
    "exit_reason_counts": {
      "basis_loss_halt": 89,
      "funding_decay": 29,
      "max_holding_intervals_reached": 155,
      "path_exhausted": 1
    },
    "mean_net_pnl_bps": 0.47243197752846705,
    "median_net_pnl_bps": -1.11126283315,
    "shadow_trade_count": 274,
    "status": "ok",
    "symbols": [
      "XRP/USDT"
    ],
    "win_rate": 0.4781021897810219
  }
}
```

解释：

- shadow 是基于 basis proxy 的研究性模拟，不等价实盘回测。
- DOGE median 为负，XRP median 也为负，且 win rate 都低于 50%。
- 在当前参数和数据口径下，不支持进入 live，甚至不支持直接进入 pre-live checklist。

## 5. 决策

- 当前属于“结论 B”（策略历史上多数被门槛阻断，无法形成可交易候选）。
- `Extreme Funding` 保留为 watchlist + 研究方向，不进入 live。
- 下一步应进入 `orderbook-aware replay` 之前的参数敏感性审计，重点检查：
  - `EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT`
  - `EXTREME_FUNDING_MIN_EXPECTED_FUNDING_INCOME_BPS`
  - `EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS`
  - `EXTREME_FUNDING_MAX_SLIPPAGE_BPS`

