# Cross-Sectional Factor Lab Stage A v1 策略回测评审报告

**日期**：2026-06-08  
**阶段**：`Stage A: Exchange-only Fast Track`  
**数据源**：`Binance Spot` (540天，包含 warmup 实际拉取约 575 天)  
**审计决策 (Decision)**：`stageA_v1_failed` (策略回测未通过决策闸门)  
**声明**：本报告的所有回测与分析结果均标注为 `survivorship_bias_not_controlled` (未控制幸存者偏差)。
**复跑说明**：2026-06-08 已完成最小修补并复跑：补入 BTC/ETH benchmark gate，live 拉取改用 Binance spot raw kline 的 `quote asset volume`，不再用 `base_volume * close` 估算 `quote_volume`。复跑后结论仍为 `stageA_v1_failed`。

---

## 1. 核心结论
经过对 Binance 现货市场符合流动性门槛的代币进行 30d 动量（跳过 1d）周频调仓回测，**最终判定该策略未通过 Stage A 闸门**。
策略表现与等权基准几乎完全一致，未能展现出显著的超额收益，且在压力成本场景下录得深度负收益。同时，收益高度集中于个别月份，不满足稳健性要求。因此，**禁止将本策略推向实盘或 Paper Shadow 模拟**。

---

## 2. 数据与偏差 (Data & Bias)
*   **回测时间窗口**：约从 2025-01 到 2026-06 (共 540 天)
*   **偏差合同 (Bias Contract)**：
    *   `universe_scope`: `current_tradable_universe_only`
    *   `survivorship_bias_control`: `not_controlled`
    *   由于未包含已退市币种，回测的实际表现可能比本报告中呈现的更为糟糕（幸存者偏差未控制）。
*   **缺失值前向填充次数**：`ffill_count = 0`。数据源完整度极高，未发生因缺失价格导致的前向填充。

---

## 3. 主组合结果：top10_equal_weight
*   **调仓策略**：每周一 00:00 UTC 调仓，选择动量因子 `momentum_30d_skip_1d` 排名最高的 Top 10 代币等权配置。
*   **基准成本场景 (30 bps round-trip)**：
    *   **策略总收益率**：`-84.05%`
    *   **策略最大回撤**：`84.44%`
*   **调仓质量**：
    *   `rebalance_count`: `77` (满足最小 50 次调仓的统计要求)
    *   `insufficient_universe_ratio`: `0.0` (没有出现合格币种不足 10 个的情况)
    *   `median_turnover`: `0.6` (周换手率中位数为 60.0%)

---

## 4. 成本场景：30 / 50 / 80 bps (Cost Scenarios)
随着交易摩擦的增加，策略表现单调衰减：
*   **基础场景 (30 bps)**：总收益 `-84.05%`
*   **压力场景 (50 bps)**：总收益 `-84.86%` (录得深度负收益，直接触发 `stageA_v1_failed` 闸门限制)
*   **崩溃场景 (80 bps)**：总收益 `-85.99%`

---

## 5. Benchmark 对比
策略在 30 bps 基础摩擦下，与各项基准的对比情况如下：

| 组合/资产 | 总收益率 (Total Return) | 最大回撤 (Max Drawdown) | 策略超额收益 (Excess Return vs. EW) |
|---|---|---|---|
| **本策略 (Top 10 EW)** | `-84.05%` | `84.44%` | **+0.55%** |
| **全市场等权基准 (Universe EW)** | `-84.61%` | `84.61%` | - |
| **BTC Buy & Hold (Net)** | `-39.67%` | - | - |
| **ETH Buy & Hold (Net)** | `-57.60%` | - | - |

> [!NOTE]
> 策略收益率（-84.05%）虽然在数学上微弱战胜了等权基准（-84.61%），但超额收益仅为 **+0.55%**，不足以覆盖幸存者偏差、实盘滑点和交易可得性误差。并且策略严重跑输了 BTC 和 ETH 的持有收益。这表明单纯的 30d 现货动量因子在该时间段内无法形成可用的进攻型 alpha。

---

## 6. 集中度审计 (Concentration Audit)
*   **单代币最大正收益占比** (`max_single_symbol_positive_pnl_share`)：`18.28%` (低于 35% 门槛，合格)
*   **单代币最大绝对收益占比** (`max_single_symbol_abs_pnl_share`)：`4.20%`
*   **单月份最大正收益占比** (`max_single_month_positive_pnl_share`)：`40.52%`
    *   > [!WARNING]
        > **超标警告**：单月最大正收益占比高达 **40.52%**，大幅超过了配置中规定的 **30%** 限制上限 (`FACTOR_LAB_STAGEA_MAX_SINGLE_MONTH_PNL_CONTRIBUTION_SHARE = 0.30`)。这说明策略的少量盈利高度依赖特定月份的单边行情，缺乏时间跨度上的稳健性。
*   **单月份最大绝对收益占比** (`max_single_month_abs_pnl_share`)：`14.41%`

---

## 7. 诊断组合：top5_equal_weight
为了深入观察，我们运行了集中度更高的 Top 5 诊断组合（不参与主决策门槛）：
*   **总收益率 (30 bps)**：`-89.66%`
*   **最大回撤 (30 bps)**：`89.97%`
*   这表明将持仓进一步集中到极少数动量最高的币种，不仅没有改善业绩，反而使损失和回撤恶化到超过 `-90%` 的水平。

---

## 8. 失败类型与根本原因
策略未能通过闸门，主要归结于以下两个硬性限制失败：
1.  **压力测试失败**：在 50 bps 成本下录得 `-84.86%` 的严重负收益（硬性限制要求压力测试收益不得小于 0）。
2.  **BTC/ETH benchmark 失败**：策略 `-84.05%` 明显跑输 BTC `-39.67%` 与 ETH `-57.60%`，不满足 Stage A v1 的核心进攻型策略门槛。
3.  **时间集中度超标**：单月份正收益占比达 40.52%（硬性限制要求不得超过 30%）。
4.  **无有效 alpha 贡献**：策略仅小幅跑赢 Universe 等权约 0.55%，但该差异无法抵消幸存者偏差和实盘摩擦。

---

## 9. 下一步动作
由于本阶段判定为 `stageA_v1_failed`，按照指南规定：
1.  **停止对当前分支调参的意图**。禁止通过调小滑点、调大 Top N 或缩短历史窗口来宣布通过。
2.  **冻结 Stage A v1 失败结论**。后续以 `docs/reviews/2026-06-09-cross-sectional-factor-lab-stageA1-closure-review_CN.md` 作为 Stage A1 closure 与 Stage A2 路线图的主索引。
3.  **转入 Stage A2 失败诊断计划**。Round 1 只允许 `regime_cash_fallback_only`：对照 `regime_none`、`btc_ma20_cash`、`alt_universe_20d_return_cash`。`3d_rebalance_diagnostic`、`14d momentum`、`volume confirmation`、`funding/OI` 与 `on-chain` 全部后置，避免多重比较和解释污染。
