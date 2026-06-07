# Cross-Sectional Factor Lab Stage 0 数据审计报告

**日期**：2026-06-07  
**审计阶段**：`Stage 0: Data Coverage + Bias Audit`  
**数据源**：`Binance` (Spot & USDT perpetuals)  
**审计时间戳**：2026-06-07T15:14:03.243419+00:00 (UTC)  
**策略规格**：`docs/strategy_specs/cross_sectional_factor_lab_implementation_guide_CN_v3.md`

---

## 1. 审计核心结论与决策

根据 Stage 0 的数据闸门决策逻辑，本阶段审计结论如下：

* **最终决策 (Decision)**：`factor_lab_data_ready_with_bias`
* **后续允许进入阶段 (Allowed Next Stage)**：`stage_a_exchange_only_fast_track` (允许进入 Stage A 编写计划与回测)
* **主拦截器 (Primary Blocker)**：无 (Null)
* **Stage A 允许运行的模式 (Allowed Modes)**：
  * **价格/成交量回测 (price_volume_fast_track)**：`True` (允许进行价格和成交量因子的 Fast Track)
  * **资金费率拦截 (funding_veto)**：`False` (由于历史资金费率数据在此样本范围表现处于 degraded 降级状态，暂不作为硬性 veto)
  * **未平仓合约拦截 (oi_veto)**：`False` (币安免费接口仅提供最新 30 天的历史 OI，不支持 540d 完整回测拦截)
  * **方向限制 (long_only_only)**：`True` (由于做空成本和借币利息未建模，Stage A 必须且只能跑 Long-only 多头回测)
  * **C1 拦截器 (c1_entry_block)**：`diagnostic_only` (C1 仅用于记录诊断数据，不影响主回测收益)
  * **偏差标签强制要求 (survivorship_bias_label_required)**：`True`

---

## 2. 幸存者偏差状态 (Bias Contract)

根据 Stage 0 偏差合同规范，本次数据审计声明如下：

```json
{
  "universe_scope": "current_tradable_universe_only",
  "survivorship_bias_control": "not_controlled",
  "delisted_symbols_included": false,
  "result_usage": "hypothesis_screening_only_not_final_evidence"
}
```

> [!WARNING]
> **幸存者偏差警告**：
> 本策略由于仅提取了当前 Binance 挂牌交易的币种历史，漏掉了历史上已被下架（De-listed）的代币，因此存在**未受控的幸存者偏差**。
> Stage A Fast Track 的所有回测结果只能用于“过滤不靠谱的策略假说（Hypothesis Screening）”，**绝对不能**作为该策略正式上线的收益凭证。

---

## 3. 交易版图与覆盖率数据审计 (Universe & Coverage Audit)

本次审计涵盖了 Binance 的所有主流 USDT 交易对，并应用了静态排除（去除了稳定币、杠杆代币以及 wrapped 桥接代币）：

### 3.1 总体统计 (Aggregate Statistics)

* **全市场初始交易对总数 (symbols_total)**：1,650 个
* **静态排除后剩余交易对 (symbols_after_static_exclusions)**：1,462 个
* **通过流动性门槛的交易对 (symbols_passing_liquidity)**：202 个 (当前 30d 中位数日成交额 $\ge 20,000,000\text{ USDT}$)
* **要求的历史天数 (history_days_required)**：540 天 (约 18 个月)
* **可用历史天数中位数 (history_days_available_median)**：540.0 天
* **日 OHLCV 覆盖率中位数 (daily_ohlcv_coverage_ratio_median)**：1.00 (100% 覆盖)
* **资金费率覆盖率中位数 (funding_coverage_ratio_median)**：1.00
* **近期未平仓合约覆盖率中位数 (open_interest_coverage_ratio_median)**：0.00 (OI 数据降级)

---

### 3.2 现货与永续合约分账审计结果 (Market Breakdown)

#### A. 现货市场 (Spot)
* **现货交易对总数**：1,040 个
* **静态排除后剩余**：921 个
* **满足流动性的交易对数**：110 个
* **日 OHLCV 覆盖率中位数**：1.00 (100% 覆盖)
* **可用历史天数中位数**：540.0 天

#### B. 永续合约市场 (USDT Swap)
* **永续合约交易对总数**：610 个
* **静态排除后剩余**：541 个
* **满足流动性的交易对数**：92 个
* **日 OHLCV 覆盖率中位数**：0.00 (由于大部分小市值永续合约在 540 天前尚未上市，拉长到 540 天中位数为 0.0)
* **可用历史天数中位数**：0.0 天
* **资金费率历史覆盖率中位数**：1.00 (在已上市期间)
* **未平仓合约历史覆盖率中位数**：0.00 (免费接口仅保存最新 30 天，长周期覆盖率为 0.0)

---

## 4. 特殊声明

* **流动性门槛仅用于当前筛选 (Current Liquidity Screening Only)**：
  报告中的 `symbols_passing_liquidity = 202` 仅代表当前 30 天的成交量满足条件。它并不代表这些标的在 540 天前的历史成交量也满足门槛。在 Stage A 的正式回测中，必须实现 point-in-time rolling 30d quote volume（历史时点滚动滚动成交量筛选）来防止未来信息泄露。

---

## 5. 下一步行动计划 (Next Steps)

由于 Stage 0 数据审计结果明确为 `factor_lab_data_ready_with_bias`，表示免费交易所数据在**静态排除且标注偏差**的前提下足够支持我们进行 Fast Track 假说验证。

我们将采取以下行动：
1. **结束 Stage 0 阶段**，将所有代码和审计产物提交至分支。
2. **编写 Stage A: Exchange-only Fast Track 实施计划书**，主要基于 pandas 实现 `Daily Panel Builder`、`Baseline Factors`（包含 `cmom_14d`、`volume_ratio_7d_30d` 等）以及 `Portfolio Simulator`，且回测必须严格限制为 **Long-only** 模式。
