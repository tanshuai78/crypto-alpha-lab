# crypto-alpha-lab — Project Roadmap & Decision Log

**Created:** 2026-05-23  
**Conversation:** ID `1833b66a-1d4e-455c-aedd-1d6b8cb9b9ea`  
**AI Agent reading this:** Read this file first before any session. It is the context bridge.

---

## Background: Why We Left the Old System

The predecessor project (`my-bitcoin-project`) was technically sound but strategically blocked.
Key evidence from the last observation window:

| Signal | Value | Meaning |
|---|---|---|
| `carry_builder_total` | 1030 | Builder had data to work with |
| `carry_engine_reject` | 1000 (97%) | **Term structure slope = 0.000** on all candidates |
| `mr_builder_reject` | 1030 (100%) | All rejected: `history_insufficient` |
| `medium_conviction_mr_total` | 0 | Completely empty |

**Root cause:**
- **carry_core**: BTC perpetual market entered a low-carry regime (flat term structure). The filter was *correct*, not broken. No amount of engineering fixes a market that isn't paying.
- **mr_core**: OKX spot fetch timeouts prevented the minimum 60-sample history from accumulating. The system required too much data continuity from an unreliable endpoint.

**Decision**: Stop engineering around dead alpha. The old system is excellent at *explaining why not to trade*. A new system must start from *better alpha hypotheses*.

---

## New Project Mission

**Not** an arbitrage system.  
**Not** a yield machine.  
**Is**: A personal alpha verification lab with a safe execution base.

Capital scale assumption: **5,000 – 50,000 USDT**.  
Phase 1 (30-day sprint): **Observation and shadow simulation only. No live trading.**

---

## Architecture Decisions

### Execution Layer: Verbatim Migration

`src/execution/` was migrated *verbatim* (only import paths changed) from the old project.

**Why**: The 355-line `order_executor.py` handles 7 failure paths:
1. Maker timeout → `UNKNOWN_REMOTE_STATE` recovery via `client_order_id`
2. Net edge ≤ 0 after fill → immediate rollback
3. Hedge leg exception → rollback maker leg
4. Hedge partial fill above dust threshold → conditional rollback
5. `abort_on_partial_fill` → rollback and `FAILED_SAFE`
6. Duplicate `intent_id` → rejected without replay
7. `FORCE_DELEVERAGING` lock → only `reduce_only` intents allowed

Any simplification of this code will re-create bugs that were already fixed in the old project.
**Do not simplify the execution layer.**

### Strategy Interface: `SignalCandidate`

All strategies must return `SignalCandidate` objects (defined in `src/strategies/base.py`).  
No strategy may produce raw dicts or call the execution layer directly.

### Configuration: Single Source of Truth

All thresholds live in `configs/base.py`. No magic numbers in `src/`.  
Changing a threshold requires changing one file and is immediately auditable.

### Open-Source References

| Project | What to Reference | What NOT to do |
|---|---|---|
| Freqtrade | Strategy lifecycle (entry+exit+stop as atomic unit) | Do not integrate as a dependency |
| Jesse | Clean strategy code style | Half-hour read, not a framework |
| Hummingbot | Connector concepts (already implemented in our execution layer) | Do not replace our execution layer |
| NautilusTrader | Event-driven architecture concepts | Do not use as a dependency in Phase 1 |

---

## Strategy Specifications

### 1. Extreme Funding Event Scanner (Priority 1)

**Hypothesis**: When annualized funding rate exceeds ~30%, collecting carry over 1–3 settlements has positive expected value even accounting for basis movement.

| Parameter | Value | Source |
|---|---|---|
| Min annualized rate | 30% | `EXTREME_FUNDING_ANNUALIZED_THRESHOLD_PCT` |
| Min funding persistence | 0.70 | `EXTREME_FUNDING_MIN_PERSISTENCE` |
| Max holding period | 24 hours | `EXTREME_FUNDING_MAX_HOLDING_HOURS` |
| Max position size | 500 USDT | `RISK_MAX_SINGLE_POSITION_USDT` |
| Max concurrent positions | 2 | `RISK_MAX_CONCURRENT_POSITIONS` |

**Trigger condition**: Annualized funding > 30% AND persistence > 0.70 AND basis has NOT already absorbed the excess funding (basis absorption check required).

**Invalidation condition**: Funding drops below 15% annualized OR basis expands by more than cumulative funding income collected.

**Exit**: At next funding settlement if rate decays below threshold, or at max holding boundary.

**Shadow validation target (Day 1–10)**: At least 1 qualifying signal per 7 days over a 30-day window.

---

### 2. Trend / Liquidation Regime Scanner (Priority 2)

**Hypothesis**: After vol breakout or liquidation cascade, directional momentum has positive short-term expectancy. Unlike carry, this is explicitly directional — not market neutral.

| Parameter | Value | Source |
|---|---|---|
| Vol breakout multiplier | 2.0× vs 30d baseline | `TREND_REGIME_VOL_BREAKOUT_MULTIPLIER` |
| Max holding period | 48 hours | `TREND_REGIME_MAX_HOLDING_HOURS` |
| Stop loss | 2.0% from entry | `TREND_REGIME_STOP_LOSS_PCT` |
| Max position size | 500 USDT | `RISK_MAX_SINGLE_POSITION_USDT` |

**Trigger condition**: 1h vol > 2× 30d baseline, with OI movement confirming direction (OI expanding = momentum, OI dropping = liquidation cascade).

**Invalidation condition**: Stop loss hit OR price reverses through entry zone OR holding period exceeded.

**Exit**: Stop loss OR time limit. Trailing stop optional in Phase 2.

**Shadow validation target (Day 11–20)**: Simulated net edge > 0 after 20 bps round-trip cost across ≥5 signals.

---

### 3. Long-Horizon Funding Basis Desk (Priority 3)

**Hypothesis**: When funding rates are in a stable "mid-carry" regime (10–25% annualized, persistence > 0.6), holding a delta-neutral position for 3–7 days collects enough funding to absorb normal basis fluctuation.

**Key distinction from carry_core**: This does NOT require positive term structure slope. It requires stable cumulative funding over the holding period.

| Parameter | Value | Source |
|---|---|---|
| Max holding period | 7 days | `BASIS_DESK_MAX_HOLDING_DAYS` |
| Basis drawdown halt | 50% of cumulative funding | `BASIS_DESK_BASIS_DRAWDOWN_HALT_RATIO` |
| Min funding persistence | 0.60 | `BASIS_DESK_MIN_FUNDING_PERSISTENCE` |
| Min Maker fill rate | 70% (shadow monitored) | `BASIS_DESK_MIN_MAKER_FILL_RATE` |
| Max position size | 500 USDT | `RISK_MAX_SINGLE_POSITION_USDT` |

**Critical risk: Basis expansion in trend regimes**. If BTC moves +10% in a day, perpetual premium (basis) expands. Multi-day holders absorb this as unrealized loss. The basis drawdown check at every 8h settlement is non-negotiable.

**Critical risk: Funding Flip**. If funding turns negative mid-hold, you pay instead of collect. Exit immediately on Funding Flip detection.

**Trigger condition**: Annualized funding in 10–25% range AND persistence > 0.60 AND Basis σ (30-day) < 0.3%.

**Invalidation / exit conditions** (checked every 8 hours):
- Cumulative basis loss > 50% of cumulative funding income → exit
- Funding rate flips negative → exit
- Holding period > 7 days → force exit or explicit renewal decision

**Shadow validation target (Day 21–30)**:
- Day 21–25: Data modeling only. Build Basis history DB, implement 8h Funding Flip detector.
- Day 26–30: Shadow simulation only if persistence > 0.6 in observation window.
- Must verify: Maker fill rate > 70% in shadow execution.

---

## 30-Day Sprint Plan

| Days | Phase | Deliverable | Gate to next phase |
|---|---|---|---|
| 1–3 | Setup | `make test` passes 100%. `make smoke` passes. | All tests green |
| 4–10 | Extreme Funding (observe) | Scanner producing logs. No execution. | ≥1 qualifying signal/7 days |
| 11–20 | Trend Regime (shadow sim) | Shadow simulation running. Cost-corrected expectancy > 0. | ≥5 signals, positive expectancy |
| 21–25 | Basis Desk (data) | Basis history DB populated. Funding Flip detector tested. | DB clean, detector firing correctly |
| 26–30 | Basis Desk (shadow) | Shadow position simulation. Maker fill rate monitored. | Fill rate > 70% |
| 31+ | Pre-live review | 8-point checklist (see below). | All 8 points satisfied |

---

## Pre-Live 8-Point Checklist

Before any strategy touches real money, ALL 8 must be satisfied:

- [ ] Signal frequency ≥ 1 per week (enough statistical sample)
- [ ] Net edge > 30 bps after realistic costs (not theoretical)
- [ ] Max execution capacity ≥ 2× planned position size (depth verified)
- [ ] Max adverse slippage ≤ 10 bps (measured, not estimated)
- [ ] Max holding period has hard upper bound (no "wait and see")
- [ ] Simulated max drawdown ≤ 5% of capital
- [ ] Withdrawal/deposit channels NORMAL status at signal time (cross-venue strategies)
- [ ] `InventoryGuard` and `RiskLimits` trigger correctly in edge-case simulation

---

## What Was Deliberately NOT Migrated

| Component | Reason |
|---|---|
| `carry_core` / `tactical_carry` engine | Blocked by flat term structure — market structure issue, not code |
| `mr_core` / `medium_conviction_mr` | Blocked by data pipeline fragility (OKX timeouts) |
| `nextgen_paper_runtime/` | Diagnostic wrapper, not alpha-generating |
| `screening/`, `router/`, `buckets/` | Governance surface built for a different design philosophy |
| `shadow_mode/` | Replaced by new strategy-level shadow simulation |
| Phase 4.5, bucket allocator, carry builder | Historical complexity with no forward value |
