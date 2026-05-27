# Trend / Liquidation Regime — Historical Replay Review

**Date:** 2026-05-27  
**Replay file:** `reports/trend_regime/2026-05-27_historical_replay_dual_cost_summary.json`  
**Input:** `data/trend_regime_historical_rows.jsonl`  
**Reviewer:** Automated subagent (crypto-alpha-lab)

---

This historical replay only resolves historical-advancement capability and primary-blocker diagnosis. It does not imply live-ready or execution-ready status.

---

## 1. Input Coverage

| Metric | Value |
|---|---|
| Row count | 2994 |
| Symbols fetched | ADA/USDT, BTC/USDT, DOGE/USDT, ETH/USDT, SOL/USDT, XRP/USDT |
| Rows per symbol | 499 |
| First timestamp | 2026-05-06 17:59 UTC |
| Last timestamp | 2026-05-27 11:59 UTC |
| Time span | 498.0 hours (~20.75 days) |
| Minimum span gate (720h) | **NOT MET** — this is a smoke replay only |
| OI endpoint cap | Binance `openInterestHist` max limit = 500 rows; `--oi-limit 1500` was silently capped to 500. This caps effective history to ≈498h per symbol. |

> **Note:** The 720h (30-day) span gate was not met because Binance's `openInterestHist` endpoint caps at 500 hourly rows (~20.8 days). This is a data coverage constraint, not a strategy defect. The replay covers 498h, classifying this as a **smoke replay**, not a full Phase 1A historical validation.

---

## 2. Stale Row Normalization

| Metric | Value |
|---|---|
| Rows normalized (data_age_sec set to 0.0) | 2988 / 2994 |
| Rows already fresh (age = 0.0) | 6 |

Historical rows have non-zero `data_age_sec` by construction (they are fetched at a point in time and their age increases). The replay script normalizes all stale rows to `data_age_sec = 0.0` to bypass the live-freshness gate. This is expected behavior for historical replay mode.

---

## 3. Classification Reject Counts

These counts apply identically to both base (30 bps) and stress (50 bps) scenarios, since classification is independent of cost assumption.

| Reject Reason | Count | % of Total Rows |
|---|---|---|
| `vol_breakout_below_threshold` | 2298 | 76.8% |
| `symbol_not_in_watchlist` | 499 | 16.7% |
| `return_below_min` | 160 | 5.3% |
| `volume_below_min` | 30 | 1.0% |
| `oi_confirmation_below_min` | 7 | 0.2% |
| **Entry events** | **0** | **0.0%** |

### Primary Blocker Identification

**PRIMARY BLOCKER: `vol_breakout_below_threshold` (2298 rows, 76.8%)**

The scanner requires `vol_1h_pct / vol_baseline_30d_pct >= 2.5` (`TREND_REGIME_VOL_BREAKOUT_MULTIPLIER`). Distribution across the 2994 rows:

| Percentile | Vol Breakout Ratio |
|---|---|
| p50 | 0.649 |
| p75 | 1.226 |
| p90 | 2.070 |
| p95 | 2.774 |
| p99 | 5.187 |
| Max | 9.883 |

Only 6.6% of all rows (198 rows) crossed the 2.5x threshold. Of those 198 rows, ADA/USDT (not in watchlist) accounts for 31. The remaining **167 in-watchlist rows that passed vol_breakout** still produced **zero entries**:

| Post-Vol-Breakout Reject Reason | Count |
|---|---|
| `return_below_min` | 160 |
| `oi_confirmation_below_min` | 7 |

**Per-symbol reject cascade (all rows, normalized):**

| Symbol | In Watchlist | vol_breakout_below_threshold | return_below_min | oi_confirmation_below_min | volume_below_min | Entry |
|---|---|---|---|---|---|---|
| ADA/USDT | No | — | — | — | — | 0 (all 499 → symbol_not_in_watchlist) |
| BTC/USDT | Yes | 471 | 27 | 1 | 0 | 0 |
| DOGE/USDT | Yes | 442 | 25 | 2 | 30 | 0 |
| ETH/USDT | Yes | 468 | 28 | 3 | 0 | 0 |
| SOL/USDT | Yes | 452 | 47 | 0 | 0 | 0 |
| XRP/USDT | Yes | 465 | 33 | 1 | 0 | 0 |

**SECONDARY BLOCKER: `return_below_min` (160 / 167 in-watchlist vol-pass rows)**  
The scanner requires `|return_1h_pct| >= 2.0%` for majors and `>= 2.5%` for large alts. Even among rows where volatility was elevated (vol_ratio >= 2.5), the 1h directional move was insufficient to pass the return gate in 95.8% of cases.

**TERTIARY BLOCKER: `oi_confirmation_below_min` (7 / 7 remaining rows)**  
The 7 rows that passed both vol_breakout and return gates were then rejected because OI change did not meet the minimum confirmation threshold.

**FOURTH GATE (never reached): Liquidation confirmation**  
Because 0 rows passed all three entry gates (vol, return, OI), the liquidation_cascade regime was never triggered. Had entries occurred with positive OI, they would route to `vol_breakout_{direction}`. Had OI been non-positive and liquidation_notional insufficient, they would be rejected as `liquidation_not_confirmed`.

---

## 4. Liquidation Coverage

| Metric | Value |
|---|---|
| Rows with `liquidation_notional_1h_usdt` data | 0 |
| Rows missing `liquidation_notional_1h_usdt` | 2994 |
| Liquidation coverage ratio | 0.000 (0%) |

`liquidation_notional_1h_usdt` is always `null` in the output of `build_trend_regime_market_rows.py`. The script does not fetch force-order (liquidation) data — that is the responsibility of `collect_trend_regime_force_orders.py`. This means the `liquidation_cascade` regime path in the scanner is **structurally unreachable** from this data pipeline until force-order data is merged.

**Implication:** The scanner can still produce entries via the `vol_breakout_{direction}` regime path (when OI confirms positively), which does NOT require liquidation data. The missing liquidation data only blocks the `liquidation_cascade` regime arm.

---

## 5. Entry Events by Symbol and Regime

**Entry event count: 0 (base), 0 (stress)**

No per-symbol or per-regime entry statistics can be computed because zero entries were generated. The vol_breakout + return + OI gate cascade eliminated all 2995 candidate rows.

**Stop-loss exit rate:** N/A (no trades to compute)  
**Liquidation coverage ratio (as gate metric):** 0.000  
**Trade count:** 0 (base), 0 (stress)

---

## 6. Base Cost Replay (30 bps) — Stats vs Phase 1A Gates

| Metric | Value | Phase 1A Gate | Pass/Fail |
|---|---|---|---|
| `entry_event_count` | 0 | >= 20 | **FAIL** |
| `trade_count` | 0 | — | — |
| `mean_net_pnl_bps` | 0.0 | > 40 bps | **FAIL** |
| `median_net_pnl_bps` | 0.0 | > 30 bps | **FAIL** |
| `win_rate` | 0.0 (0%) | > 55% | **FAIL** |
| `worst_trade_net_pnl_bps` | 0.0 | > -200 bps | N/A (no trades) |
| `stop_loss_exit_rate` | N/A | < 35% | N/A (no trades) |

*All Phase 1A gates fail due to zero entry events. PnL metrics are zero by construction (empty trade list).*

---

## 7. Stress Cost Replay (50 bps) — Stats vs Phase 1A Gates

| Metric | Value | Phase 1A Gate | Pass/Fail |
|---|---|---|---|
| `entry_event_count` | 0 | — | — |
| `trade_count` | 0 | — | — |
| `mean_net_pnl_bps` | 0.0 | — | — |
| `median_net_pnl_bps` | 0.0 | > 0 bps | **FAIL** |
| `win_rate` | 0.0 (0%) | — | — |
| `worst_trade_net_pnl_bps` | 0.0 | > -200 bps | N/A |
| `stop_loss_exit_rate` | N/A | < 35% | N/A |

*Same root cause: zero entries. Cost assumption is irrelevant with no trades.*

---

## 8. Exit Reason Breakdown

No trades were simulated. Exit reason breakdown is empty for both base and stress scenarios.

| Exit Reason | Count (Base) | Count (Stress) |
|---|---|---|
| (no trades) | 0 | 0 |

---

## 9. Review Gate Answers (7 Questions)

**Q1: Did the replay generate >= 20 signal entries?**  
No. Entry event count = 0. Primary blocker is `vol_breakout_below_threshold` (76.8% of rows). Even during a 498h window spanning multiple market regimes (BTC oscillating ~71k–82k), the volatility breakout threshold was not met in 93.4% of hourly rows.

**Q2: Does median_net_pnl_bps (base) exceed the 30 bps Phase 1A gate?**  
No. Median = 0.0 bps (no trades). Gate: > 30 bps. **FAIL.**

**Q3: Does mean_net_pnl_bps (base) exceed 40 bps?**  
No. Mean = 0.0 bps. Gate: > 40 bps. **FAIL.**

**Q4: Does win_rate exceed 55%?**  
No. Win rate = 0.0% (no trades). Gate: > 55%. **FAIL.**

**Q5: Does stress median_net_pnl_bps exceed 0?**  
No. Stress median = 0.0 bps. Gate: > 0 bps. **FAIL.**

**Q6: Is worst_trade_net_pnl_bps > -200 bps?**  
Not assessable — no trades. The stop-loss design (1.5% per `TREND_REGIME_STOP_LOSS_PCT`) translates to approximately -300 bps gross worst case before cost, so worst-case net with 30 bps cost ≈ -330 bps. This must be verified with actual trades.

**Q7: Is stop_loss_exit_rate < 35%?**  
Not assessable — no trades.

---

## 10. Conclusion

**Decision: `keep_observation_only`**

**Rationale:**

1. **Zero entries is the hard blocker.** All Phase 1A quantitative gates (signal_count, PnL, win_rate) fail by definition when no trades are generated. This is not a market edge problem — it is a classification gate calibration problem.

2. **Root cause is multi-layered, not a single threshold miss:**
   - Layer 1: `vol_breakout_below_threshold` is the dominant filter (76.8% of all rows). During a moderate-volatility 20-day window, only 6.6% of hourly rows exceeded 2.5x the 30-day baseline. This ratio is tuned for regime-change moments; normal market hours will always produce sparse signals.
   - Layer 2: `return_below_min` eliminates 95.8% of vol-pass rows. Even when vol spikes, the directional 1h return often does not meet the 2.0% (major) / 2.5% (large alt) absolute threshold.
   - Layer 3: `oi_confirmation_below_min` eliminates the remaining 7 rows.
   - Liquidation gate: unreachable without force-order data and only used for one regime arm.

3. **Data pipeline gap:** `liquidation_notional_1h_usdt` is structurally null (0% coverage). The `liquidation_cascade` regime arm of the scanner cannot fire from current data. This must be resolved before any entry count can include liquidation-driven signals.

4. **The smoke replay (498h vs 720h target) is not the binding constraint.** Even with 30 days of data, the vol_breakout rate in a normal market regime would produce similar sparse counts. Phase 1B cannot proceed until at least one of the following is addressed:
   - Threshold recalibration (lower `TREND_REGIME_VOL_BREAKOUT_MULTIPLIER` or `TREND_REGIME_MIN_1H_ABS_RETURN_PCT_*`)
   - Force-order data integration to enable the liquidation regime arm
   - Replay over a higher-volatility historical window (March 2024, November 2024, January 2025)

**Required before Phase 1B eligibility review:**
- [ ] Resolve liquidation data pipeline gap (integrate `collect_trend_regime_force_orders.py` output)
- [ ] Decide threshold recalibration scope with explicit risk justification
- [ ] Re-run replay over a >= 720h window that includes at least one known high-volatility regime period
- [ ] Achieve signal_count >= 20 with non-zero PnL before re-evaluating Phase 1A gates
