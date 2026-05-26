# Extreme Funding Admission Definition Revision Review (2026-05-26)

## 1. 核心结论

本轮“入选定义修订”已生效并跑通 DOGE/XRP 全量参数审计，但结论仍然是：

- Layer A（anchor event）与 Layer B（research shadow case）可以稳定产出样本；
- Layer C（trade candidate）在 `expected_holding_intervals=1` 下仍为 0；
- 因此当前策略不满足进入 orderbook-aware replay 的门槛。

**最终决策：`watchlist_only`**。

---

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

---

## 3. Layer A / B / C 结果

### DOGE

```json
{
  "anchor_event_count": 143,
  "research_shadow_admitted_count": 23,
  "trade_candidate_count": 0,
  "admission_layer_counts": {
    "no_anchor": 87,
    "anchor_only": 120,
    "research_shadow": 23
  }
}
```

### XRP

```json
{
  "anchor_event_count": 175,
  "research_shadow_admitted_count": 29,
  "trade_candidate_count": 0,
  "admission_layer_counts": {
    "no_anchor": 100,
    "anchor_only": 146,
    "research_shadow": 29
  }
}
```

解释：修订后不再“全灭”，但样本主要停留在研究层（Layer B），尚未进入交易候选层（Layer C）。

---

## 4. 拒绝主因与桥接阻塞

两条资产在 conservative 设定（`expected_holding_intervals=1`）下，Layer B -> Layer C 的主要阻塞一致：

- `expected_funding_income_below_min`
- 次要为 `basis_absorbed` / `net_edge_below_min`

同时，全量 top reject 仍包含：

- `anchor_threshold_not_met`
- `trade_requires_conservative_one_interval`

说明当前定义下，资金费强度与净边际仍不足以支撑交易层入选。

---

## 5. Shadow 结果（conservative 1 interval）

### DOGE（最佳 conservative 参数组）

```json
{
  "median_net_pnl_bps": -19.2450451919,
  "win_rate": 0.2608695652173913,
  "research_shadow_admitted_count": 23,
  "shadow_trade_count": 23
}
```

### XRP（最佳 conservative 参数组）

```json
{
  "median_net_pnl_bps": 9.4056730177,
  "win_rate": 0.5517241379310345,
  "research_shadow_admitted_count": 29,
  "shadow_trade_count": 29
}
```

与决策门对比：

- 需要 `median_shadow_net_pnl_bps > 20`，当前未达标；
- XRP 的 `win_rate` 约 55.17% 勉强达线，但 `median` 明显不达标；
- DOGE 的 `median` 和 `win_rate` 都不达标。

---

## 6. `expected_holding_intervals=2` 依赖判断

```json
{
  "strategy_depends_on_funding_persistence": false,
  "conservative_has_candidate": true,
  "conservative_has_trade_candidate": false
}
```

解释：当前不是“只靠 2 interval 才有研究样本”，而是“1 interval 也有研究样本，但仍不能形成 trade candidate”。

---

## 7. 决策

三选一决策输出：

- `watchlist_only` ✅
- `funding_persistence_study_required` ❌
- `enter_orderbook_aware_replay` ❌

原因：

1. `trade_candidate_count` 在 conservative 设定下仍为 0；
2. best conservative shadow 的 `median_net_pnl_bps` 未超过 20；
3. 主要阻塞仍是 funding income 与净边际不足，不是仅靠换深度模型就能解决。

---

## 8. 下一步建议（非本次实现范围）

1. 在策略定义层继续收敛 Layer C 触发语义（不是放宽到可交易，而是明确哪些研究样本永远不应升级）。
2. 保持 watchlist 与 research replay 并行，等待更强 funding regime 样本再复检。
3. 不进入 orderbook-aware replay，不进入 live。
