# Superseded Plan

This draft is superseded by `docs/plans/2026-05-24-extreme-funding-phase1-watchlist-implementation-plan.md`.

The new plan follows the `superpowers:writing-plans` format and should be used for implementation review/execution.

---

# Implementation Plan: Extreme Funding Phase 1 Watchlist / Candidate / Shadow

## 0. Decision

This plan replaces the earlier draft `docs/plans/extreme_funding_scanner_impl.md` as the next executable plan.

The Extreme Funding module must not start as a tradable signal scanner. It starts as an event observer, then becomes a candidate builder, and only then becomes a shadow trade simulator.

Current execution scope: **Phase 1A only**.

Phase 1B and Phase 1C are included here to freeze interfaces and avoid building Phase 1A in a direction that cannot be extended.

## 1. Development Stage Check

The project process remains:

1. SSOT and data contract definition.
2. TDD component development.
3. Shadow simulation and cost/latency calibration.
4. Gated capital scaling.

Current project state:

- Day 1-3 setup is complete enough to proceed: `make test` and `make smoke` pass.
- `docs/roadmap.md` is the project-level roadmap and decision log.
- `docs/roadmap_CN.md` is the Chinese mirror for reading convenience.
- `configs/base.py` is the only configuration source of truth.
- `src/strategies/base.py` defines the current `SignalCandidate` contract.

SSOT is complete at roadmap level, but not yet complete at Extreme Funding implementation level. Phase 1A must first add missing config constants and freeze the watch event contract before production code.

## 2. Scope Boundary

### In Scope For Phase 1A

- Add Extreme Funding watchlist config constants to `configs/base.py`.
- Add a lightweight watch event dataclass in `src/strategies/extreme_funding/scanner.py`.
- Implement premium-derived watchlist detection.
- Implement micro-persistence calculation.
- Implement OI confirmation as a watchlist level input.
- Implement reject reason taxonomy for observation.
- Add unit tests for watchlist behavior.
- Add an observation daemon script that prints heartbeat and optionally writes low-frequency structured evidence.

### Not In Scope For Phase 1A

- No real trading.
- No execution layer calls.
- No `TradeIntent` creation.
- No private API keys.
- No account balance reads.
- No `SignalCandidate` output unless Phase 1B is explicitly started.
- No basis absorption decision unless spot/perp basis fields are available.
- No high-frequency raw data persistence.

## 3. Required Config Additions

Add these constants to `configs/base.py` before writing scanner logic:

```python
EXTREME_FUNDING_WATCH_SYMBOLS = ("XRP/USDT", "DOGE/USDT", "ADA/USDT", "ETH/USDT", "SOL/USDT", "BTC/USDT")

EXTREME_FUNDING_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT = 30.0
EXTREME_FUNDING_STRONG_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT = 50.0
EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT = 100.0

EXTREME_FUNDING_MICRO_PERSISTENCE_WINDOW_MIN = 30
EXTREME_FUNDING_MICRO_PERSISTENCE_MIN = 0.70
EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_WEAK = 0.50

EXTREME_FUNDING_OI_CONFIRMATION_MIN_CHANGE_1H_PCT = 0.0
EXTREME_FUNDING_OI_STRONG_CONFIRMATION_MIN_CHANGE_1H_PCT = 3.0

EXTREME_FUNDING_MARK_DATA_POLL_INTERVAL_SEC = 10
EXTREME_FUNDING_OI_POLL_INTERVAL_SEC = 60
EXTREME_FUNDING_KLINE_REFRESH_INTERVAL_SEC = 3600
EXTREME_FUNDING_HEARTBEAT_INTERVAL_SEC = 300

EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC = 30
EXTREME_FUNDING_MAX_OI_DATA_AGE_SEC = 180
```

Keep the existing roadmap constants:

- `EXTREME_FUNDING_ANNUALIZED_THRESHOLD_PCT`
- `EXTREME_FUNDING_MIN_PERSISTENCE`
- `EXTREME_FUNDING_MAX_HOLDING_HOURS`

Do not remove them in Phase 1A. They remain roadmap-level names until Phase 1B decides whether to rename or map them.

## 4. Phase 1A: Watchlist Scanner

### 4.1 Goal

Detect symbols showing early signs of an extreme funding event.

This phase answers:

- Is there a persistent premium-derived funding anomaly?
- Is OI expanding enough to confirm crowded positioning?
- Are API fields fresh enough to trust the observation?
- If no event appears, why exactly was each symbol rejected?

It does not answer:

- Is this trade profitable after basis and cost?
- Should the system open a position?
- How much capital should be used?

### 4.2 Input Snapshot Contract

`ExtremeFundingStrategy.scan()` receives one symbol snapshot per call:

```python
{
    "symbol": "DOGE/USDT",
    "exchange": "binance",
    "timestamp_ms": 1780000000000,
    "mark_price": 0.25,
    "index_price": 0.249,
    "premium_index": 0.0012,
    "estimated_funding_rate": 0.0008,
    "next_funding_time_ms": 1780003600000,
    "open_interest": 12345678.0,
    "oi_change_1h_pct": 4.2,
    "volume_24h_usdt": 150000000.0,
    "mark_data_age_sec": 5.0,
    "oi_data_age_sec": 30.0,
}
```

The daemon is responsible for iterating multiple symbols. The strategy class stays single-snapshot and deterministic.

### 4.3 Output Contract

Phase 1A returns watch events, not `SignalCandidate`.

Create:

```python
@dataclass(frozen=True)
class ExtremeFundingWatchEvent:
    strategy_type: str
    symbol: str
    exchange: str
    level: str
    premium_annualized_estimate_pct: float
    micro_persistence: float
    oi_change_1h_pct: float | None
    reason: str
    reject_reason: str | None
    executable: bool
    metadata: dict[str, Any]
```

Rules:

- `strategy_type = "extreme_funding"`
- `executable = False` always in Phase 1A.
- `level` must be one of: `none`, `watch_level_1`, `watch_level_2`, `watch_level_3`.
- If no watch event is emitted, internal classification must still produce a reject reason for observability.

### 4.4 Watch Level Rules

Premium-derived annualized estimate is a pre-signal only. It must not be treated as final settled funding.

Watch levels:

```text
watch_level_1:
    premium_annualized_estimate_pct >= 30
    micro_persistence >= 0.50

watch_level_2:
    premium_annualized_estimate_pct >= 50
    micro_persistence >= 0.70
    oi_change_1h_pct > 0

watch_level_3:
    premium_annualized_estimate_pct >= 100
    micro_persistence >= 0.70
    oi_change_1h_pct > 3
```

The estimate may use premium index and estimated funding rate, but the implementation must name the field `premium_annualized_estimate_pct` to prevent confusing it with settled funding.

### 4.5 Reject Reason Taxonomy

Implement these stable reason codes:

- `premium_below_threshold`
- `micro_persistence_below_threshold`
- `oi_not_confirmed`
- `missing_premium`
- `missing_oi`
- `missing_symbol`
- `missing_timestamp`
- `api_stale`
- `symbol_not_in_watchlist`
- `volume_below_min`
- `invalid_numeric_field`

Phase 1A must record reason counts in tests and daemon heartbeat output.

### 4.6 Tests

Create `tests/strategies/test_extreme_funding_scanner.py`.

Required cases:

1. Missing premium returns no event and `missing_premium`.
2. Premium spike with insufficient persistence returns no event and `micro_persistence_below_threshold`.
3. Premium persists with weak OI returns `watch_level_1`.
4. Premium persists with OI expansion returns `watch_level_2`.
5. Strong premium persists with OI > 3% returns `watch_level_3`.
6. Stale mark data returns no event and `api_stale`.
7. Symbol outside watchlist returns no event and `symbol_not_in_watchlist`.
8. `RISK_LIVE_TRADING_ENABLED=False` does not suppress watch events; watch events still return with `executable=False`.

### 4.7 Daemon Script

Create `scripts/run_extreme_funding_watchlist.py`.

Responsibilities:

- Fetch Binance public mark / premium data.
- Fetch OI no more frequently than the OI interval.
- Fetch 1h kline baseline no more frequently than hourly, if needed for heartbeat context.
- Maintain in-memory premium windows per symbol.
- Call `ExtremeFundingStrategy.scan()` once per symbol snapshot.
- Print heartbeat every 5 minutes.
- Print watch events immediately.
- Track API error and missing field counts.

Forbidden:

- No private API keys.
- No account balance reads.
- No order placement.
- No execution layer imports.

### 4.8 Persistence Policy

Do not write raw 10-second data.

Do write low-frequency evidence if a storage layer is available:

- `watch_event`
- `reject_reason_summary`
- `heartbeat_5m_snapshot`
- `api_error_summary`
- `data_staleness_summary`

If SQLite store is not ready, Phase 1A may start with structured logs, but the daemon must keep reason counts in memory and print them in heartbeat output.

## 5. Phase 1B: Candidate Builder

Phase 1B starts only after Phase 1A tests pass and the watchlist daemon can run stably.

### 5.1 Goal

Convert watch events into observation-only `SignalCandidate` objects when basis and cost confirm that the event still has edge.

### 5.2 Additional Required Fields

Phase 1B cannot start without these fields:

- `spot_mid_price`
- `perp_mid_price`
- `spot_bid_ask_spread_bps`
- `perp_bid_ask_spread_bps`
- `spot_depth_500usdt_bps`
- `perp_depth_500usdt_bps`
- `fee_bps`
- `slippage_estimate_bps`
- `basis_bps`
- `basis_rolling_median_bps`
- `basis_rolling_std_bps`

### 5.3 Candidate Conditions

```text
micro_persistence >= 0.70
expected_funding_income_bps >= 50
basis_absorption_ratio <= 0.50
net_edge_bps >= 30
depth_capacity >= 2 * planned_position_size
estimated_slippage_bps <= 10
```

### 5.4 SignalCandidate Mapping

Do not add new top-level fields to `SignalCandidate` in Phase 1B unless a separate contract change is approved.

Mapping:

- `strategy_type = "extreme_funding"`
- `direction = "neutral"`
- `confidence = 0.0-1.0`
- `expected_edge_bps = net_edge_bps`
- `entry_exchange = spot exchange`
- `hedge_exchange = perp exchange`
- `trigger_reason = "extreme_funding_candidate"`
- `invalidation_reason = "funding_decay_or_basis_absorption"`
- `max_holding_hours = EXTREME_FUNDING_MAX_HOLDING_HOURS`
- `stop_loss_pct = 0.0` until a basis-drawdown stop is modeled as percent.
- `suggested_notional_usdt <= RISK_MAX_SINGLE_POSITION_USDT`
- `metadata` carries basis, funding, cost, mode, executable, reject reason, and all diagnostics.

`metadata["mode"] = "observation"` and `metadata["executable"] = False` remain mandatory until pre-live approval.

## 6. Phase 1C: Shadow Trade Simulator

Phase 1C starts only after Phase 1B produces explainable candidates in historical replay.

### 6.1 Goal

Validate whether a real long spot / short perp position would have made money across 1-3 funding intervals.

### 6.2 Shadow Position

The simulator creates a shadow position with:

- entry time
- spot entry price
- perp entry price
- notional
- expected holding intervals
- entry basis bps
- accumulated funding income bps
- basis PnL bps
- fees
- slippage
- net PnL bps

### 6.3 Exit Rules

Exit rules must be fixed:

- Funding annualized estimate < 15%.
- Reached next funding settlement and net edge no longer positive.
- Max holding time = 24h.
- Basis loss > cumulative funding income * 0.5.
- Funding flips negative.

### 6.4 Historical Validation Gate

Use 2021-2026 settled Binance funding data and prioritize:

- DOGE
- XRP
- ADA
- ETH
- SOL
- BTC

Required historical pass conditions before real-time shadow:

- candidate_count >= 30
- median_net_pnl_bps > 20
- mean_net_pnl_bps > 30
- win_rate > 55%
- max_single_trade_loss_bps is bounded and explained
- losses mostly come from basis expansion, not fee drag

## 7. Phase 1A Completion Criteria

Phase 1A is complete when:

- `configs/base.py` contains all Phase 1A constants.
- `tests/strategies/test_extreme_funding_scanner.py` passes.
- `ExtremeFundingStrategy` can classify watch levels and reject reasons deterministically.
- The daemon can run without private keys or execution imports.
- Heartbeat output includes per-symbol watch level, premium estimate, micro persistence, OI change, stale status, and reject reason counts.
- `make test` and `make smoke` pass.

## 8. Stop / Continue Rules

After 7-10 days of Phase 1A observation:

- If no watch events appear: do historical replay; do not tune thresholds blindly.
- If watch events appear but are all weak: continue watchlist only.
- If watch events cluster in altcoins: prioritize DOGE/XRP/ADA data completeness.
- If API missing/stale rate is high: fix data fetching before strategy logic.
- If watch events are frequent and clean: start Phase 1B plan review.

## 9. Immediate Next Step

Review this plan. After approval, implement Phase 1A only, using TDD:

1. Add config constants.
2. Add tests for watch event and reject reason behavior.
3. Implement scanner.
4. Add daemon script.
5. Run `make test` and `make smoke`.
