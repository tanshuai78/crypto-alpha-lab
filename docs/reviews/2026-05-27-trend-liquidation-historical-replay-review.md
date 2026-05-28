# Trend / Liquidation Historical Replay Review

**Date:** 2026-05-27  
**Replay file:** `reports/trend_regime/2026-05-27_historical_replay_dual_cost_summary.json`  
**Input file:** `data/trend_regime_historical_rows.jsonl`

本轮 historical replay 只解决“历史推进能力”和“主 blocker 诊断”问题，不等于 live-ready，不等于 execution-ready。

---

## 1. Input Coverage

| Metric | Value |
|---|---|
| `input_row_count` | 2994 |
| `symbol_count` | 6 |
| `symbols` | ADA/USDT, BTC/USDT, DOGE/USDT, ETH/USDT, SOL/USDT, XRP/USDT |
| `start_timestamp_ms` | 1778090399999 |
| `end_timestamp_ms` | 1779883199999 |
| `time_span_hours` | 498.0 |
| 30-day gate (`>= 720h`) | **NOT MET** (smoke replay only) |

说明：
- 当前 `time_span_hours` 只有 498h，未达 30 天门槛。
- 根因是 Binance `openInterestHist` 单次返回上限约 500 条 1h 记录，历史跨度被限制到约 20.8 天。

---

## 2. Historical Freshness Normalization

| Metric | Value |
|---|---|
| `historical_mode` | `true` |
| `historical_freshness_normalized_count` | 2994 |
| `rows_originally_api_stale_count` | 2988 |

说明：
- replay 中统一把 `data_age_sec` 归一化为 `0.0`，是为了绕过 live `api_stale` 门控，专注回放逻辑。
- `rows_originally_api_stale_count` 保留了“若按 live 语义会被 stale 拦截”的原始规模。

---

## 3. Classification Diagnostics

### 3.1 全局拒绝结构（base / stress 一致）

| Reject reason | Count | Share |
|---|---:|---:|
| `vol_breakout_below_threshold` | 2298 | 76.8% |
| `symbol_not_in_watchlist` | 499 | 16.7% |
| `return_below_min` | 160 | 5.3% |
| `volume_below_min` | 30 | 1.0% |
| `oi_confirmation_below_min` | 7 | 0.2% |

### 3.2 入场事件结构

- `entry_event_count = 0`
- `entry_event_count_by_symbol = {}`
- `entry_event_count_by_regime = {}`

### 3.3 `reject_counts_by_symbol` 关键观察

- `ADA/USDT` 的 499 行全部被 `symbol_not_in_watchlist` 拦截。
- 这是“采集 universe 与策略 watchlist 不一致”造成的结构性噪声，不是行情问题。

---

## 4. Liquidation Coverage

| Metric | Value |
|---|---:|
| `rows_with_liquidation_notional_count` | 0 |
| `rows_missing_liquidation_notional_count` | 2994 |
| `liquidation_coverage_ratio` | 0.0 |

结论：
- 当前历史 rows 数据中，`liquidation_notional_1h_usdt` 完全缺失。
- 在该数据面下，`liquidation_cascade` 路径结构性不可达，只能评估 `vol_breakout` 路径。

---

## 5. Shadow Replay Outcome

### Base cost (`30 bps`)

| Metric | Value |
|---|---:|
| `shadow_trade_count` | 0 |
| `mean_net_pnl_bps` | 0.0 |
| `median_net_pnl_bps` | 0.0 |
| `win_rate` | 0.0 |
| `worst_trade_net_pnl_bps` | 0.0 |

### Stress cost (`50 bps`)

| Metric | Value |
|---|---:|
| `shadow_trade_count` | 0 |
| `mean_net_pnl_bps` | 0.0 |
| `median_net_pnl_bps` | 0.0 |
| `win_rate` | 0.0 |
| `worst_trade_net_pnl_bps` | 0.0 |

---

## 6. Gate Assessment

当前结果无法进入 `eligible_for_phase1b_review`，原因：

1. `time_span_hours < 720`，只到 smoke replay 级别。  
2. `entry_event_count = 0`，后续 PnL gate 无法有效评估。  
3. 没有任何 `regime × direction × symbol_tier` 子类形成稳定可评估样本。  
4. `liquidation_coverage_ratio = 0.0`，`liquidation_cascade` 分支无法验证。

---

## 7. Decision

**Decision: `keep_observation_only`**

核心原因：
- 主 blocker 仍是 `vol_breakout_below_threshold`（76.8%）。
- 次级 blocker 是 `return_below_min`（在通过 `vol` 的 in-watchlist 样本里占绝大多数）。
- 历史回放数据结构目前不支持 liquidation 路径验证。

---

## 8. Next Actions

1. 对齐 universe：historical rows 构建默认 symbol 与 `TREND_REGIME_WATCH_SYMBOLS` 对齐，先移除 `ADA/USDT` 噪声。  
2. 补 liquidation 历史覆盖：把 `collect_trend_regime_force_orders.py` 的可用历史信息接入 replay 数据面（或明确声明无历史覆盖时不评估该分支）。  
3. 继续保守门槛不动，先扩数据窗口到可审计覆盖（`>= 720h`）再重跑。  
4. 仅当出现可评估样本后，再判断是否需要做阈值重构，而不是先调低门槛换信号数量。

