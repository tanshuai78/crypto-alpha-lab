# Binance Liquidation Snapshot Event Study — Phase 1 Review

**Generated:** 2026-05-31T15:17:41Z

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

Two implementation corrections were applied before finalizing this review:

- **Gap-reset lookback protection**: shock detection is now run on contiguous per-symbol
  segments only, so a failed or missing middle month cannot leak stale rows into a later
  month's `24h` reference window.
- **Reduced-universe downgrade**: a positive directional-bias result is no longer sufficient
  for confirmation when required symbol-month coverage is incomplete.

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

## Universe Integrity

**Universe integrity pass:** `false`

- Required symbol-months: 15
- Passed symbol-months: 8
- Missing or failed symbol-months:
  - `SOLUSDT / 2024-02`
  - `XRPUSDT / 2024-01`
  - `XRPUSDT / 2024-02`
  - `XRPUSDT / 2024-03`
  - `DOGEUSDT / 2024-01`
  - `DOGEUSDT / 2024-02`
  - `DOGEUSDT / 2024-03`

Interpretation:

- This branch no longer qualifies as the originally planned 5-symbol Binance-only replacement
  study.
- The effective research universe is a **reduced proxy universe** dominated by
  `BTCUSDT / ETHUSDT / SOLUSDT`, with `SOLUSDT` itself missing one of the three target months.
- Therefore, even if event density is high, this study cannot be upgraded to a confirmed
  Q1 2024 structure result.

---

## Event Density Summary

**Total shock events (deduplicated):** 4391

### By Month

| Month | Events |
| ----- | ------ |
| 2024-01 | 1460 |
| 2024-02 | 1147 |
| 2024-03 | 1784 |

### By Symbol

| Symbol | Events |
| ------ | ------ |
| BTCUSDT | 2206 |
| ETHUSDT | 1657 |
| SOLUSDT | 528 |

### By Side

| Side | Events |
| ---- | ------ |
| long | 2389 |
| short | 2002 |

---

## Directional Bias (Response Map)

| Horizon (min) | N | Positive | Directional Ratio |
| ------------- | - | -------- | ----------------- |
| 5 | 4390 | 1913 | 0.436 |
| 10 | 4390 | 1860 | 0.424 |
| 15 | 4390 | 1884 | 0.429 |

---

## Final Decision

**`binance_snapshot_structure_not_confirmed`**

> Decision: `binance_snapshot_structure_not_confirmed`. See density and continuity tables above for root cause.
> Reduced-universe / failed-symbol-month scope prevented a confirmed result.

More specifically:

- The branch **does not fail on raw event density**. There are enough events to study.
- The branch **does fail as a full-scope replacement validation**, because required
  symbol-month integrity is incomplete.
- After the gap-reset correction, the remaining directional-bias result is still weak:
  - `5m = 0.436`
  - `10m = 0.424`
  - `15m = 0.429`
- So the current evidence supports:
  - `Q1 2024 Binance snapshot proxy data does not confirm the original 5-symbol 1m shock structure`
  - rather than:
  - `liquidation alpha is globally disproven`
