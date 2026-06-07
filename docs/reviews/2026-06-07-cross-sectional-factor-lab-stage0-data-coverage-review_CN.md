# Cross-Sectional Factor Lab Stage 0 数据审计报告

日期：2026-06-07  
审计阶段：`Stage 0: Data Coverage + Bias Audit`  
数据源：`Binance public API`  
策略规格：`docs/strategy_specs/cross_sectional_factor_lab_implementation_guide_CN_v3.md`

---

## 1. 核心结论

本次 Stage 0 审计结论：

```text
decision = factor_lab_data_ready_with_bias
allowed_next_stage = stage_a_exchange_only_fast_track
primary_blocker = null
```

但这个通过结论必须精确理解为：

```text
Binance spot 数据足够支持 Stage A price + volume Fast Track；
Binance USDT perpetual 数据暂不支持 Stage A price + volume Fast Track；
funding / OI veto 暂不能作为 Stage A 主回测硬过滤；
所有 Stage A 结果必须标注 survivorship_bias_not_controlled。
```

当前允许的 Stage A 模式：

```json
{
  "price_volume_fast_track": true,
  "funding_veto": false,
  "oi_veto": false,
  "long_only_only": true,
  "c1_entry_block": "diagnostic_only",
  "survivorship_bias_label_required": true
}
```

按市场拆分：

```json
{
  "spot": {
    "price_volume_fast_track": true,
    "funding_veto": false,
    "oi_veto": false
  },
  "usdt_perp": {
    "price_volume_fast_track": false,
    "funding_veto": false,
    "oi_veto": false
  }
}
```

---

## 2. Bias Contract

本次审计只使用当前 Binance 仍挂牌交易对，因此幸存者偏差未被控制。

```json
{
  "universe_scope": "current_tradable_universe_only",
  "survivorship_bias_control": "not_controlled",
  "delisted_symbols_included": false,
  "result_usage": "hypothesis_screening_only_not_final_evidence"
}
```

这意味着：

```text
Stage A 可以用于快速杀假设；
Stage A 不能作为 formal alpha 证明；
Stage A 不能直接进入 paper shadow 或 live pilot。
```

---

## 3. 审计结果

Summary 文件：`reports/cross_sectional_factor_lab/factor_lab_data_coverage_summary.json`

顶层结果：

| 字段 | 结果 |
|---|---:|
| `symbols_total` | 1650 |
| `symbols_after_static_exclusions` | 1138 |
| `symbols_passing_liquidity` | 108 |
| `history_days_required` | 540 |
| `history_days_available_median` | 540.0 |
| `daily_ohlcv_coverage_ratio_median` | 1.0 |
| `api_errors_count` | 1 |
| `rate_limited_count` | 0 |
| `historical_liquidity_gate_ready` | false |

说明：顶层 `daily_ohlcv_coverage_ratio_median = 1.0` 来自当前允许进入 Stage A 的 spot market。perp market 单独分账，不能被顶层结果代表。

---

## 4. Spot 审计

```json
{
  "symbols_total": 1040,
  "symbols_after_static_exclusions": 597,
  "symbols_passing_liquidity": 56,
  "daily_ohlcv_coverage_ratio_median": 1.0,
  "history_days_available_median": 540.0,
  "decision": "factor_lab_data_ready_with_bias",
  "primary_blocker": null
}
```

结论：

```text
Binance spot 当前足够支持 Stage A price + volume Fast Track。
```

但流动性口径只是当前 30d median quote volume screening：

```text
usage = stage0_screening_only_not_historical_tradability
```

Stage A 必须重新实现 point-in-time rolling 30d quote volume，不能用当前流动性过滤历史。

---

## 5. USDT Perpetual 审计

```json
{
  "symbols_total": 610,
  "symbols_after_static_exclusions": 541,
  "symbols_passing_liquidity": 52,
  "daily_ohlcv_coverage_ratio_median": 0.0,
  "history_days_available_median": 0.0,
  "decision": "factor_lab_data_unavailable",
  "primary_blocker": "insufficient_ohlcv_coverage",
  "funding_oi_veto_readiness": "degraded",
  "open_interest_history_mode": "recent_only"
}
```

结论：

```text
Binance USDT perpetual 暂不允许进入 Stage A 主回测。
```

原因：

```text
大量当前可交易 perp 在 540 天前尚未上市；
当前 O(1) 历史可用性探测下，perp 的 540d daily OHLCV 中位覆盖不足；
OI 只能做 recent-only readiness，不能作为 540d coverage 硬门槛。
```

---

## 6. API 异常

本次 live audit 记录：

```text
api_errors_count = 1
rate_limited_count = 0
```

已观察到 Binance public API 对个别 symbol 返回 invalid symbol，例如 `BSVUSDT`。该错误没有阻断 Stage 0，因为 spot market 已满足 Stage A price/volume Fast Track 的最低数据闸门。

后续 Stage A 不应使用这些 API error symbol，必须从 Stage 0 summary 的可用 market/universe 重新构建候选集。

---

## 7. 下一步

允许进入：

```text
Stage A exchange-only Fast Track implementation plan
```

Stage A 第一版必须限制为：

```text
Binance spot only
long-only
price + volume factors only
no funding veto
no OI veto
C1 diagnostic_only
survivorship_bias_not_controlled
30 / 50 / 80 bps cost scenarios
```

不允许：

```text
perp 主回测
funding/OI veto 主结论
on-chain
LightGBM
paper shadow
live pilot
```

