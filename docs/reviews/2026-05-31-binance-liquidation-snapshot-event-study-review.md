# Binance Liquidation Snapshot Event Study — Phase 1 Review

**Generated:** 2026-05-31T14:13:00Z

---

## Data Source Semantics

| Field | Value |
| ----- | ----- |
| `data_source` | `binance_vision_liquidation_snapshot` |
| `liquidation_data_semantics` | `binance_forceorder_largest_order_snapshot_per_symbol_per_1000ms` |
| `not_complete_liquidation_tape` | `true` |
| `notional_interpretation` | `snapshot_notional_proxy_not_total_market_liquidation` |
| `sample_window` | `2024-01_to_2024-03` |
| `known_window_bias` | `Q1_2024_trending_crypto_market` |
| `generalization_allowed` | `false` |

---

## Purpose

This is a **data-source replacement validation study**, not a live strategy promotion decision.
It evaluates whether Binance Vision historical `liquidationSnapshot` data can replace
Coinalyze 1m liquidation data for the purposes of the existing shock event-study pipeline,
within the Q1 2024 sample window only.

---

## Continuity Gate

| Symbol | Month | Price Coverage | Max Gap (min) | Liq File Coverage | PASS/FAIL |
| ------ | ----- | -------------- | ------------- | ----------------- | --------- |
| BTCUSDT | 2024-01 | 1.0000 | 0 | 1.0000 | ✅ PASS |
| BTCUSDT | 2024-02 | 1.0000 | 0 | 1.0000 | ✅ PASS |
| BTCUSDT | 2024-03 | 1.0000 | 0 | 1.0000 | ✅ PASS |
| ETHUSDT | 2024-01 | 1.0000 | 0 | 1.0000 | ✅ PASS |
| ETHUSDT | 2024-02 | 1.0000 | 0 | 1.0000 | ✅ PASS |
| ETHUSDT | 2024-03 | 1.0000 | 0 | 1.0000 | ✅ PASS |
| SOLUSDT | 2024-01 | 1.0000 | 0 | 1.0000 | ✅ PASS |
| SOLUSDT | 2024-02 | 1.0000 | 0 | 0.9655 | ❌ FAIL |
| SOLUSDT | 2024-03 | 1.0000 | 0 | 1.0000 | ✅ PASS |
| XRPUSDT | 2024-01 | 1.0000 | 0 | 0.0000 | ❌ FAIL |
| XRPUSDT | 2024-02 | 1.0000 | 0 | 0.0000 | ❌ FAIL |
| XRPUSDT | 2024-03 | 1.0000 | 0 | 0.0000 | ❌ FAIL |
| DOGEUSDT | 2024-01 | 1.0000 | 0 | 0.0000 | ❌ FAIL |
| DOGEUSDT | 2024-02 | 1.0000 | 0 | 0.0000 | ❌ FAIL |
| DOGEUSDT | 2024-03 | 1.0000 | 0 | 0.0000 | ❌ FAIL |

---

## Event Density Summary

**Total shock events (deduplicated):** 4398

### By Month

| Month | Events |
| ----- | ------ |
| 2024-01 | 1460 |
| 2024-02 | 1147 |
| 2024-03 | 1791 |

### By Symbol

| Symbol | Events |
| ------ | ------ |
| BTCUSDT | 2206 |
| ETHUSDT | 1657 |
| SOLUSDT | 535 |

### By Side

| Side | Events |
| ---- | ------ |
| long | 2395 |
| short | 2003 |

---

## Directional Bias (Response Map)

| Horizon (min) | N | Positive | Directional Ratio |
| ------------- | - | -------- | ----------------- |
| 5 | 4397 | 1914 | 0.435 |
| 10 | 4397 | 1861 | 0.423 |
| 15 | 4397 | 1884 | 0.428 |

---

## Final Decision

**`binance_snapshot_structure_not_confirmed`**

> Decision: `binance_snapshot_structure_not_confirmed`. See density and continuity tables above for root cause.
