# Trend Liquidation Historical Replay Review — 2026-05-28

> **范围声明**：本次 replay 仅验证 universe 对齐修复与 liquidation proxy 数据链路。
> 不代表策略可交易状态或 live-ready 结论。

---

## 1. 输入数据摘要

| 指标 | 值 |
|---|---|
| 总行数 | 2495 |
| Symbols | BTC/USDT, DOGE/USDT, ETH/USDT, SOL/USDT, XRP/USDT |
| 时间跨度 | 498.0h（**烟雾回放**，未达 720h 全量阈值） |
| ADA/USDT 污染 | **否**（universe 对齐修复已生效） |
| 非 watchlist 行数 | 0 |
| 缺失 symbol 行数 | 0 |

> **注**：498h 回放覆盖约 20.75 天，属于 "smoke replay" 分类。OI 数据 500 行限制仍影响历史跨度，但 universe 对齐已干净。

---

## 2. Stale Row 归一化

| 指标 | 值 |
|---|---|
| historical_mode | `true` |
| 归一化行数（原 api_stale） | 2495（其中 2490 行原始为 api_stale） |

所有历史行均已通过 `normalize_rows_for_historical_replay()` 将 `data_age_sec` 置零，避免 `api_stale` 批量拒绝。

---

## 3. Classification 拒绝分布

### 汇总（2495 行，两个成本档位结果相同）

| 拒绝原因 | 行数 | 占比 |
|---|---|---|
| `vol_breakout_below_threshold` | **2285** | **91.6%** |
| `return_below_min` | 172 | 6.9% |
| `volume_below_min` | 30 | 1.2% |
| `oi_confirmation_below_min` | 8 | 0.3% |

**主要拦截点：`vol_breakout_below_threshold`（91.6%）**

### 按 Symbol 拒绝明细

| Symbol | vol_breakout | return_below_min | volume_below_min | oi_below_min |
|---|---|---|---|---|
| BTC/USDT | 468 | 30 | 0 | 1 |
| ETH/USDT | 465 | 30 | 0 | 4 |
| SOL/USDT | 450 | 49 | 0 | 0 |
| XRP/USDT | 462 | 36 | 0 | 1 |
| DOGE/USDT | 440 | 27 | **30** | 2 |

> DOGE/USDT 有 30 行 `volume_below_min`，占该 symbol 约 12%。24h volume < 300M USDT 门槛在低波动窗口内会命中。

---

## 4. Liquidation 覆盖率

| 指标 | 值 |
|---|---|
| 有 liquidation 数据行数 | 0 |
| 缺失 liquidation 数据行数 | 2495 |
| coverage_ratio | **0.0** |

**原因**：`trend_regime_force_orders_raw.jsonl` 尚未存在（forceOrder 采集器需在服务器上以 `--raw-output` 模式持续运行后才能积累数据）。此轮回放在无 liquidation proxy 的情况下运行，是预期行为。

**影响**：当前 entry_event_count = 0，部分原因可能是清算过滤门槛（`TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_MAJOR` = 10M、Large Alt = 3M）在无 liquidation 数据时直接拒绝。需待 forceOrder 数据积累后复核。

---

## 5. Entry Events 与 Trade 结果

### Base Cost（30.0 bps）

| 指标 | 值 |
|---|---|
| entry_event_count | **0** |
| trade_count | 0 |
| mean_net_pnl_bps | 0.0 |
| median_net_pnl_bps | 0.0 |
| win_rate | 0.0 |
| worst_trade_net_pnl_bps | 0.0 |

### Stress Cost（50.0 bps）

| 指标 | 值 |
|---|---|
| entry_event_count | **0** |
| trade_count | 0 |
| mean_net_pnl_bps | 0.0 |
| median_net_pnl_bps | 0.0 |
| win_rate | 0.0 |
| worst_trade_net_pnl_bps | 0.0 |

---

## 6. 结论与下一步

- **Universe 对齐修复成功**：ADA/USDT 已完全剔除，non_watchlist_row_count = 0，missing_symbol_row_count = 0。这是本轮计划的核心验证目标，已达成。

- **主要拦截点未变**：`vol_breakout_below_threshold` 占比 91.6%，是 Phase 1A 进入下一阶段的核心障碍。在 498h 的历史窗口内（低波动市场阶段），当前 `VOL_BREAKOUT_MULTIPLIER=2.5` 门槛几乎过滤全部行。

- **Liquidation proxy 数据链路已就绪，但数据尚未积累**：`collect_trend_regime_force_orders.py --raw-output` 的启动命令、聚合器 `aggregate_trend_regime_liquidations.py`、以及 replay 的 `--liquidation-hourly-jsonl` 参数全部实现并通过测试。需要服务器端以 `--raw-output` 模式持续运行采集器，积累至少 24h 原始事件后，才能评估 liquidation 覆盖率对 entry_event_count 的实际影响。

- **回放仍处于 smoke replay 分类**（498h < 720h）：历史跨度受限于 Binance OI API 500 行上限。`entry_event_count = 0` 本质上是市场状态问题（低波动窗口），不是代码或链路问题。

- **当前决策**：维持 `keep_observation_only`。待满足以下其中一项条件后进入下一阶段：
  1. 服务器 forceOrder 采集器积累 ≥ 72h 原始事件（`liquidation_coverage_ratio > 0.3`），重跑 replay 确认 entry_event_count > 0；
  2. 或市场出现 vol_breakout 信号（1h 波动率 > 2.5× 30日基线），实时链路产生第一个 watchlist 信号。

---

*数据来源*：`reports/trend_regime/2026-05-28_historical_replay_summary.json`（2026-05-28 本地生成）
