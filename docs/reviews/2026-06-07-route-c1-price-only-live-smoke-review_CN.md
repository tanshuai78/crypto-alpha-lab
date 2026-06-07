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
| events detected | 603 |
| matched events | 89 |
| baseline match rate | 0.148 |
| sample_days | 8 |

## Price Risk Ratios (Event / Baseline Median)

| Metric | Value | Gate |
|---|---|---|
| post_event_vol_ratio_median | 1.480 | >= 1.5 |
| post_event_range_ratio_median | 1.604 | >= 1.4 |
| post_event_abs_excursion_p90_ratio | 3.458 | >= 1.3 |

## Proxy Kill-Switch

- `proxy_kill_switch_weak`: `false`
  - vol_ratio < 1.2: False
  - range_ratio < 1.2: False
  - excursion_p90_ratio < 1.1: False

## Event Distribution

### By Symbol

- `BTCUSDT`: 13
- `DOGEUSDT`: 38
- `ETHUSDT`: 14
- `SOLUSDT`: 15
- `XRPUSDT`: 9

### By Month

- `2026-05`: 55
- `2026-06`: 34

## Decision

```
decision: route_c1_baseline_match_failed
```

## Next Path

- Ratios below gate thresholds. Continue 7d live overlap collection.
- Run `audit_route_c1_data_overlap.py --mode live_overlap` after 7 days.

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
