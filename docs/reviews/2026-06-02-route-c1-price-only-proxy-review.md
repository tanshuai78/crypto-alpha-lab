# Route C1 Price-Only Proxy Precheck Review

> **IMPORTANT:** This proxy cannot promote to live filter (`can_promote_live_filter: false`).  
> Generalization allowed: `false`.  
> Data semantics: `snapshot_proxy_not_complete_liquidation_tape`.

## Run Mode

- `run_mode`: `proxy_snapshot`
- `data_source`: `binance_vision_liquidation_snapshot`

## Data Coverage

| Field | Value |
|---|---|
| events detected | 1686 |
| matched events | 1686 |
| baseline match rate | 0.995 |
| sample_days | 90 |

## Price Risk Ratios (Event / Baseline Median)

| Metric | Value | Gate |
|---|---|---|
| post_event_vol_ratio_median | 1.725 | >= 1.5 |
| post_event_range_ratio_median | 1.750 | >= 1.4 |
| post_event_abs_excursion_p90_ratio | 4.725 | >= 1.3 |

## Proxy Kill-Switch

- `proxy_kill_switch_weak`: `false`
  - vol_ratio < 1.2: False
  - range_ratio < 1.2: False
  - excursion_p90_ratio < 1.1: False

## Event Distribution

### By Symbol

- `BTCUSDT`: 675
- `ETHUSDT`: 662
- `SOLUSDT`: 349

### By Month

- `2024-01`: 623
- `2024-02`: 431
- `2024-03`: 632

## Decision

```
decision: route_c1_price_risk_proxy_promising_wait_for_live_overlap
```

## Next Path

- `continue_collect_7d_overlap`
- `stop_after_7d_if_live_smoke_weak`
- `continue_to_30d_only_if_live_smoke_promising`

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
