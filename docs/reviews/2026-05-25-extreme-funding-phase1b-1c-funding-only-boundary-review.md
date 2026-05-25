# Extreme Funding Phase 1B / 1C funding-only 边界验证结论

## 1. 结论

本轮没有证明 `Extreme Funding` 已具备可交易盈利能力。

本轮只证明：

- Phase 1B `candidate_builder` contract 可运行。
- Phase 1C `shadow_simulator` skeleton 可运行。
- funding-only historical replay 不会被误判为 basis-aware candidate。
- funding-only shadow 只输出 `funding_minus_cost` diagnostic，不输出完整 `net_pnl_bps` / `win_rate`。

## 2. Candidate Replay Summary

```json
{
  "candidate_count": 0,
  "coverage_quality": "funding_only_insufficient_for_basis",
  "has_threshold_segments": true,
  "input_file_count": 6,
  "reject_reason_counts": {
    "missing_basis": 245
  },
  "segments_seen": 245,
  "status": "ok",
  "threshold_pct": 100.0
}
```

## 3. Shadow Diagnostic Summary

```json
{
  "coverage_quality": "funding_only_insufficient_for_basis",
  "mean_funding_minus_cost_bps": 1.2631053971624486,
  "median_funding_minus_cost_bps": -2.1632999999999996,
  "notes": [
    "funding_only_replay_does_not_validate_basis_absorption",
    "funding_only_replay_does_not_validate_net_pnl"
  ],
  "positive_funding_minus_cost_rate": 0.46530612244897956,
  "shadow_trade_count": 245
}
```

## 4. 下一步

下一份计划应是 `Historical Basis-Aware Replay Plan`，至少补齐：

- historical `spot_mid_price`
- historical `perp_mid_price`
- `basis_bps`
- funding time alignment
- entry / holding period basis path
- depth / slippage proxy
- `historical_basis_aware` observation row
- basis-aware candidate replay
- basis-aware shadow PnL summary
