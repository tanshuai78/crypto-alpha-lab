# Route C1 Price-Only Proxy Precheck Review

> **IMPORTANT:** This proxy cannot promote to live filter (`can_promote_live_filter: false`).  
> Generalization allowed: `false`.  
> Data semantics: `snapshot_proxy_not_complete_liquidation_tape`.

## Status

- This review reflects the repaired Route C1 proxy implementation as of `2026-06-03`.
- The proxy result was re-run after tightening the statistical contract:
  - same-symbol same-side event scoring
  - same-month baseline matching
  - complete first post-event 5m response window checks
  - required kline high/low merge
- Current interpretation: the price-only proxy is promising, but it still cannot promote to live filter without `7d` live overlap and smoke validation.
- Current live-overlap status has advanced beyond the earlier local blocker:
  - `liquidation_input_exists = true`
  - `price_input_exists = true`
  - `orderbook_dir_exists = true`
  - `decision = route_c1_overlap_ready_for_orderbook_aware`
- Current residual limitation is no longer missing liquidation input or incomplete orderbook symbol coverage. The actual limitation is overlap length: the current live overlap is ~`72h`, still below the intended `7d / 168h` live-smoke gate.

## Live Overlap Status

Latest overlap audit summary:

```json
{
  "decision": "route_c1_overlap_ready_for_orderbook_aware",
  "ready_for_price_only": true,
  "ready_for_orderbook_aware": true,
  "liquidation_1m_zero_fill_coverage_24h": 1.0,
  "price_1m_coverage_24h": 1.0,
  "orderbook_snapshot_coverage_24h": 1.0,
  "overlap_hours_by_symbol": {
    "BTCUSDT": 72.55,
    "ETHUSDT": 72.53333333333333,
    "SOLUSDT": 72.0,
    "XRPUSDT": 72.1,
    "DOGEUSDT": 72.08333333333333
  }
}
```

Interpretation:

- The live liquidation archive, live 1m price dataset, and orderbook archive now form a valid overlap chain for the price-only Route C1 path.
- The live liquidation archive, live 1m price dataset, and orderbook archive now form a valid overlap chain for both the price-only path and the orderbook-aware input gate.
- This is enough to keep Route C1 alive and continue collecting overlap toward the `7d` live-smoke gate.
- This is still not enough to claim a live-ready filter, because the overlap length is only about `72h`, not `168h`.

## Root Cause Of Earlier Partial Overlap

- `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `XRPUSDT`, and `DOGEUSDT` orderbook files are now all updated through `2026-06-03`, so all five symbols have positive live overlap.
- The earlier `ETHUSDT/SOLUSDT/XRPUSDT = 0.0h` state was caused by incomplete local synchronization rather than unsupported collection logic.
- Earlier `0.0h` overlap across all symbols was caused by using the historical Q1 2024 proxy price dataset as the `price-1m` input. That issue is now fixed by building a live 1m price dataset aligned to the synchronized liquidation window.

## Run Mode

- `run_mode`: `proxy_snapshot`
- `data_source`: `binance_vision_liquidation_snapshot`

## Data Coverage

| Field | Value |
|---|---|
| events detected | 2958 |
| matched events | 2950 |
| unmatched events | 8 |
| baseline match rate | 0.997 |
| sample_days | 90 |

## Price Risk Ratios (Event / Baseline Median)

| Metric | Value | Gate |
|---|---|---|
| post_event_vol_ratio_median | 1.725 | >= 1.5 |
| post_event_range_ratio_median | 1.829 | >= 1.4 |
| post_event_abs_excursion_p90_ratio | 4.536 | >= 1.3 |

## Proxy Kill-Switch

- `proxy_kill_switch_weak`: `false`
  - vol_ratio < 1.2: False
  - range_ratio < 1.2: False
  - excursion_p90_ratio < 1.1: False

## Event Distribution

### By Symbol

- `BTCUSDT`: 1372
- `ETHUSDT`: 1145
- `SOLUSDT`: 433

### By Month

- `2024-01`: 1032
- `2024-02`: 770
- `2024-03`: 1148

## Decision

```
decision: route_c1_price_risk_proxy_promising_wait_for_live_overlap
```

## Interpretation

- The repaired proxy still passes the Route C1 price-only gate.
- This is materially stronger evidence than the earlier ad hoc run because the repaired version now enforces the intended anti-leakage and baseline constraints.
- This is still only a proxy result from Binance snapshot semantics, not a live-ready execution filter proof.

## Next Path

- `continue_collect_7d_overlap`
- `stop_after_7d_if_live_smoke_weak`
- `continue_to_30d_only_if_live_smoke_promising`

Concrete next actions:

- Keep syncing live liquidation 1m and orderbook archives from the server.
- Re-run overlap audit periodically; `7d` smoke should only start once overlap hours approach `168` for the required symbols.
- Treat the current state as `input ready, time not ready`.

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
