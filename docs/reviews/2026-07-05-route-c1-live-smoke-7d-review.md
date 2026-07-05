# Route C1 Price-Only Proxy Precheck Review

> **IMPORTANT:** This proxy cannot promote to live filter (`can_promote_live_filter: false`).  
> Generalization allowed: `false`.  
> Data semantics: `snapshot_proxy_not_complete_liquidation_tape`.

## Run Mode

- `run_mode`: `live_smoke_7d`
- `data_source`: `binance_vision_liquidation_snapshot`

## Data Coverage

| Field | Value |
|---|---|
| events detected | 1536 |
| matched events | 904 |
| baseline match rate | 0.589 |
| sample_days | 23 |

## Price Risk Ratios (Event / Baseline Median)

| Metric | Value | Gate |
|---|---|---|
| post_event_vol_ratio_median | 1.551 | >= 1.5 |
| post_event_range_ratio_median | 1.693 | >= 1.4 |
| post_event_abs_excursion_p90_ratio | 3.806 | >= 1.3 |

## Proxy Kill-Switch

- `proxy_kill_switch_weak`: `false`
  - vol_ratio < 1.2: False
  - range_ratio < 1.2: False
  - excursion_p90_ratio < 1.1: False

## Event Distribution

### By Symbol

- `BTCUSDT`: 305
- `ETHUSDT`: 291
- `SOLUSDT`: 308

### By Month

- `2026-05`: 42
- `2026-06`: 852
- `2026-07`: 10

## Decision

```
decision: route_c1_baseline_match_failed
```

## Next Path

- 当前不是信号强度不够，而是 baseline 对照覆盖率没过门槛。
- 正式 `baseline_match_rate >= 0.70` 门槛先不改。
- 最低成本的提升方式不是放宽正式规则，而是继续采集更长时间的 live 数据，让样本在 `month/day` 维度更分散。
- 这次样本的主要问题是 `2026-06` 过度集中；如果后续新增数据仍然主要落在同一 regime，`baseline_match_rate` 不一定会明显改善。
- 如果后面只是做诊断，可以临时开一个分析版 matcher，把 `hour` 放宽到 `±2h`、把 `vol bucket` 放宽到 `±3`，但这只能用于观察敏感性，不要升级成正式 smoke 标准。

## Baseline 对照怎么选

- `live event` 是被脚本识别出来的事件样本，代表某个 liquidation 冲击后的市场反应窗口。
- `baseline` 不是另一条 liquidation 事件，而是“相似的正常对照窗口”。
- 这里的“相似”不是指也发生了 liquidation，而是指：
  - 同一个 symbol
  - 同一个 month
  - 有完整的未来 5 分钟价格窗口
  - candidate 前后 30 分钟没有 liquidation 污染
  - pre30_vol 落在相近分位桶
  - 时间上尽量接近同一小时段
- 之所以要求 baseline 不能被 liquidation 污染，是为了让对照组尽量代表“没有这次事件时的正常波动”。如果 baseline 自己也被 liquidation 影响了，对照就失真了，price-risk ratio 会被冲淡。
- 所以这里找的不是“另一个 liquidation 事件”，而是“足够像、但没有被事件污染的正常市场片段”。这也是为什么 baseline_match_rate 会受约束比较多。

## Anti-Leakage Contract

- Entry price = `first_response_row[open_price]` (first complete 5m response bar).
- Response window excludes the shock bar and any partial 5m bar containing it.
- Baseline matched windows must have zero liquidation in candidate + ±30m guard + future 5m.

## Algorithm Parameters

```json
{
  "ROUTE_C1_EVENT_PERCENTILE_THRESHOLD": 0.995,
  "ROUTE_C1_REQUIRED_REFERENCE_BARS": 1440,
  "ROUTE_C1_DOMINANCE_RATIO_MIN": 0.65,
  "ROUTE_C1_DEDUP_BUCKET_MINUTES": 5,
  "ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT": 50000.0,
  "ROUTE_C1_ALT_ABS_THRESHOLD_USDT": 10000.0,
  "ROUTE_C1_BASELINE_MATCH_COUNT": 20,
  "ROUTE_C1_BASELINE_MATCH_RATE_MIN": 0.7,
  "ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX": 1.2,
  "ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX": 1.2,
  "ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX": 1.1
}
```
