# Cross-Sectional Factor Lab Stage A2.2 CMOM Diagnostic Review

**日期**：2026-06-10  
**阶段**：Stage A2.2  
**输入报告**：reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json  
**实盘状态**：live_usage = not_allowed；paper_shadow_allowed = false  

---

## 1. 结论

- **decision**：`cmom_diagnostic_completed`
- **next_action**：`stop_price_only_momentum`
- **can_promote_strategy**：False

---

## 2. 30d momentum vs 14d CMOM 对比数据

在 77 次周频调仓（约 540 天回测窗口）下，两种因子变体在 30 bps 基础交易成本及压力测试下的业绩对比：

| factor | 30bps return | max DD | vs BTC | vs ETH | vs EW | top5 return | max month +PnL share | max month abs PnL share |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **momentum_30d_skip_1d** | -84.05% | 84.44% | -44.38% | -26.45% | +0.55% | -89.66% | 40.52% | 14.41% |
| **cmom_14d_skip_1d** | -75.32% | 75.32% | -35.65% | -17.72% | +9.28% | -78.06% | 38.01% | 13.84% |

**主要差值指标：**
- `cmom_vs_30d_return_diff_pct`：+8.73%（未达到 `configs/base.py` 中 `FACTOR_LAB_STAGEA2_CMOM_MIN_RETURN_DIFF_PCT = 10.0%` 的判定阈值）。
- `cmom_vs_30d_drawdown_diff_pct`：-9.12%（回撤表现有所改善）。
- `cmom_vs_30d_vs_universe_ew_diff_pct`：+8.73%（相比等权重跑赢幅度增加）。

---

## 3. 诊断解释

从数据来看，14d lookback 价格动量（`cmom_14d_skip_1d`）相比 30d 价格动量（`momentum_30d_skip_1d`）在收益和回撤控制上表现出了**方向性改善**（收益提升 8.73%，回撤降低 9.12%）。但由于其绝对表现依然极其糟糕（收益率为 -75.32%），且严重跑输 BTC（-39.67%）和 ETH（-57.60%）基准，同时收益提升幅度（8.73%）未能突破 10.0% 的统计显著性改善门槛线，这表明单纯缩短回溯窗口并不能克服价格动量因子在交易摩擦下的固有损耗。

---

## 4. 失效类型与归因

- **失效类型**：`structure_failure`（结构性失效）
- **详细归因**：
  在控制交易手续费和滑点摩擦（30 bps）的前提下，基于价格的纯截面动量因子（无论是 30d 还是 14d lookback）在加密 spot token 市场上都存在严重的路径依赖和高周转损耗（CMOM 的 `turnover_median` 接近 1.0）。回撤和超额收益改善无法弥补频繁调仓带来的摩擦成本，纯价格动量因子不具备独立的统计学优势。

---

## 5. 下一步

根据计划定义的 Expected Final Interpretation Rules，由于 `next_action == stop_price_only_momentum`，我们将采取以下行动：
1. **停止（Pause）**基于纯价格周频旋转的截面动量（price-only cross-sectional momentum）策略研究。
2. **决策转换**：本轮结论要求停止纯价格动量路线，而不是直接终止整个 Factor Lab。Factor Lab 不应继续通过调参挽救 14d/30d price-only momentum；下一步只允许进入非价格因子可行性研究，例如 funding/OI 拥挤度限制、成交量结构确认、链上活跃地址或 NVT 等。如果这些非价格因子也无法提供可验证的数据质量与结构优势，再考虑终止 Factor Lab。

---

## 6. 证据边界声明
- K线 OHLCV 数据为**价格代理（price proxy）**，不代表实际滑点。
- 30 bps 基础费率与 50/80 bps 压力费率是完全覆盖滑点、手续费与执行摩擦的静态上限代理。
- 此结论禁止用于解锁实盘交易（`live_trading_enabled`）或任何沙盒影子模拟（`paper_shadow_allowed`）。
