# Extreme Funding Phase 1A Watchlist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1A Extreme Funding Watchlist Scanner that detects persistent premium-derived funding anomalies without producing executable trade signals.

**Architecture:** Phase 1A is an observation-only component. `ExtremeFundingWatchlistScanner` consumes one symbol snapshot at a time, maintains timestamp-windowed premium history, returns `ExtremeFundingWatchEvent` objects, and records deterministic reject reasons. `scripts/run_extreme_funding_watchlist.py` starts as a dry-run daemon skeleton plus public snapshot adapter; real Binance REST polling is deferred until scanner and adapter tests are green.

**Tech Stack:** Python 3.11, pytest, `configs/base.py` as SSOT, `src/strategies/base.py` as read-only Phase 1B strategy-contract reference, `loguru` for logs, public market-data snapshots only.

---

## Context

`docs/roadmap.md` defines Extreme Funding as the first Day 4-10 observation module. Historical analysis in `docs/roadmap_CN.md` shows that 30% annualized funding is useful as an observation threshold, while >100% historically had stronger trade-like edge in DOGE/XRP/ADA/ETH than BTC.

The earlier draft `docs/plans/extreme_funding_scanner_impl.md` treated premium spikes too close to executable signals. This plan replaces it for implementation purposes.

Implementation scope is **Phase 1A only**:

- Detect watchlist events.
- Classify reject reasons.
- Print and optionally persist low-frequency evidence.
- Never call execution.
- Never read private keys or balances.
- Never create `TradeIntent`.
- Never mark a signal executable.
- Do not subclass `BaseStrategy` in Phase 1A. `BaseStrategy.scan()` returns `list[SignalCandidate]`, while watch events are intentionally not candidates.

Phase 1B and Phase 1C remain future work:

- Phase 1B: Candidate Builder with basis absorption, cost, depth, slippage, and observation-only `SignalCandidate`.
- Phase 1C: Shadow Trade Simulator using historical and live shadow PnL.

---

### Task 1: Baseline Verification

**Files:**
- Read: `docs/roadmap.md`
- Read: `docs/roadmap_CN.md`
- Read: `configs/base.py`
- Read: `src/strategies/base.py`
- Read: `src/risk/limits.py`

- [ ] **Step 1: Confirm clean starting point**

Run:

```bash
git status --short
```

Expected: current research/docs changes may be present, but no untracked implementation files for this plan.

- [ ] **Step 2: Run current tests**

Run:

```bash
make test
```

Expected: PASS, currently `30 passed`.

- [ ] **Step 3: Run smoke checks**

Run:

```bash
make smoke
```

Expected: PASS, including `configs OK` and `risk gate OK`.

- [ ] **Step 4: Commit**

No commit for this task unless baseline files changed.

---

### Task 2: Add Extreme Funding SSOT Constants

**Files:**
- Modify: `configs/base.py`
- Create: `tests/test_extreme_funding_config.py`

- [ ] **Step 1: Write the failing config test**

Create `tests/test_extreme_funding_config.py`:

```python
from configs import base


def test_extreme_funding_phase1a_config_constants_exist():
    assert base.EXTREME_FUNDING_WATCH_SYMBOLS == (
        "XRP/USDT",
        "DOGE/USDT",
        "ADA/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BTC/USDT",
    )
    assert base.EXTREME_FUNDING_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT == 30.0
    assert base.EXTREME_FUNDING_STRONG_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT == 50.0
    assert base.EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT == 100.0
    assert base.EXTREME_FUNDING_MICRO_PERSISTENCE_WINDOW_MIN == 30
    assert base.EXTREME_FUNDING_MICRO_PERSISTENCE_MIN == 0.70
    assert base.EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_WEAK == 0.50
    assert base.EXTREME_FUNDING_OI_CONFIRMATION_MIN_CHANGE_1H_PCT == 0.0
    assert base.EXTREME_FUNDING_OI_STRONG_CONFIRMATION_MIN_CHANGE_1H_PCT == 3.0
    assert base.EXTREME_FUNDING_MARK_DATA_POLL_INTERVAL_SEC == 10
    assert base.EXTREME_FUNDING_OI_POLL_INTERVAL_SEC == 60
    assert base.EXTREME_FUNDING_KLINE_REFRESH_INTERVAL_SEC == 3600
    assert base.EXTREME_FUNDING_HEARTBEAT_INTERVAL_SEC == 300
    assert base.EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC == 30
    assert base.EXTREME_FUNDING_MAX_OI_DATA_AGE_SEC == 180
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py -v
```

Expected: FAIL with missing `EXTREME_FUNDING_*` constants.

- [ ] **Step 3: Add constants to `configs/base.py`**

Append to the existing `Strategy: Extreme Funding Event Scanner` section:

```python
EXTREME_FUNDING_WATCH_SYMBOLS = ("XRP/USDT", "DOGE/USDT", "ADA/USDT", "ETH/USDT", "SOL/USDT", "BTC/USDT")
# Symbols monitored by Phase 1A watchlist mode, ordered by historical priority.

EXTREME_FUNDING_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT = 30.0
# Observation-only threshold for premium-derived pre-signal alerts.

EXTREME_FUNDING_STRONG_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT = 50.0
# Stronger watchlist threshold requiring persistence and OI confirmation.

EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT = 100.0
# Historical trade-like threshold. Phase 1A must not produce executable trades from it.

EXTREME_FUNDING_MICRO_PERSISTENCE_WINDOW_MIN = 30
# Rolling micro window length for premium-derived observation persistence.

EXTREME_FUNDING_MICRO_PERSISTENCE_MIN = 0.70
# Strong micro persistence threshold.

EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_WEAK = 0.50
# Weak micro persistence threshold for watch_level_1.

EXTREME_FUNDING_OI_CONFIRMATION_MIN_CHANGE_1H_PCT = 0.0
# Minimum 1h OI change for watch_level_2.

EXTREME_FUNDING_OI_STRONG_CONFIRMATION_MIN_CHANGE_1H_PCT = 3.0
# Minimum 1h OI change for watch_level_3.

EXTREME_FUNDING_MARK_DATA_POLL_INTERVAL_SEC = 10
# Public mark/premium polling interval for observation daemon.

EXTREME_FUNDING_OI_POLL_INTERVAL_SEC = 60
# Open interest polling interval.

EXTREME_FUNDING_KLINE_REFRESH_INTERVAL_SEC = 3600
# Kline baseline refresh interval; do not fetch 720 candles every 10 seconds.

EXTREME_FUNDING_HEARTBEAT_INTERVAL_SEC = 300
# Heartbeat print interval for daemon status.

EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC = 30
# Maximum age for mark/premium data before classifying as stale.

EXTREME_FUNDING_MAX_OI_DATA_AGE_SEC = 180
# Maximum age for OI data before classifying as stale.
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add configs/base.py tests/test_extreme_funding_config.py
git commit -m "feat: add extreme funding watchlist config"
```

---

### Task 3: Add Watchlist Scanner Contract Tests

**Files:**
- Create: `tests/strategies/test_extreme_funding_scanner.py`
- Create: `src/strategies/extreme_funding/scanner.py`

- [ ] **Step 1: Write the failing import and dataclass test**

Create `tests/strategies/test_extreme_funding_scanner.py`:

```python
from strategies.extreme_funding.scanner import ExtremeFundingWatchEvent


def test_watch_event_contract_is_observation_only():
    event = ExtremeFundingWatchEvent(
        strategy_type="extreme_funding",
        symbol="DOGE/USDT",
        exchange="binance",
        level="watch_level_1",
        premium_annualized_estimate_pct=35.0,
        micro_persistence=0.55,
        oi_change_1h_pct=None,
        reason="premium_persistent",
        reject_reason=None,
        executable=False,
        metadata={
            "mode": "observation",
            "estimate_type": "naive_premium_annualization",
            "not_settled_funding": True,
        },
    )

    assert event.strategy_type == "extreme_funding"
    assert event.executable is False
    assert event.metadata["mode"] == "observation"
    assert event.metadata["estimate_type"] == "naive_premium_annualization"
    assert event.metadata["not_settled_funding"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py::test_watch_event_contract_is_observation_only -v
```

Expected: FAIL with missing module or missing `ExtremeFundingWatchEvent`.

- [ ] **Step 3: Write minimal dataclass implementation**

Create `src/strategies/extreme_funding/scanner.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py::test_watch_event_contract_is_observation_only -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/strategies/extreme_funding/scanner.py tests/strategies/test_extreme_funding_scanner.py
git commit -m "feat: add extreme funding watch event contract"
```

---

### Task 4: Implement Reject Reason Classification

**Files:**
- Modify: `tests/strategies/test_extreme_funding_scanner.py`
- Modify: `src/strategies/extreme_funding/scanner.py`

- [ ] **Step 1: Write failing reject reason tests**

Append:

```python
from strategies.extreme_funding.scanner import classify_extreme_funding_snapshot


def test_missing_premium_is_rejected():
    result = classify_extreme_funding_snapshot({"symbol": "DOGE/USDT", "timestamp_ms": 1})
    assert result.reject_reason == "missing_premium"
    assert result.event is None


def test_stale_mark_data_is_rejected():
    result = classify_extreme_funding_snapshot({
        "symbol": "DOGE/USDT",
        "timestamp_ms": 1,
        "premium_index": 0.001,
        "mark_data_age_sec": 31,
    })
    assert result.reject_reason == "api_stale"
    assert result.event is None


def test_symbol_outside_watchlist_is_rejected():
    result = classify_extreme_funding_snapshot({
        "symbol": "UNKNOWN/USDT",
        "timestamp_ms": 1,
        "premium_index": 0.001,
        "mark_data_age_sec": 1,
    })
    assert result.reject_reason == "symbol_not_in_watchlist"
    assert result.event is None

```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py -v
```

Expected: FAIL with missing `classify_extreme_funding_snapshot`.

- [ ] **Step 3: Add classification result and minimal classifier**

Add:

```python
@dataclass(frozen=True)
class ExtremeFundingClassification:
    event: ExtremeFundingWatchEvent | None
    reject_reason: str | None


def classify_extreme_funding_snapshot(snapshot: dict[str, Any]) -> ExtremeFundingClassification:
    symbol = snapshot.get("symbol")
    if not symbol:
        return ExtremeFundingClassification(None, "missing_symbol")
    if symbol not in EXTREME_FUNDING_WATCH_SYMBOLS:
        return ExtremeFundingClassification(None, "symbol_not_in_watchlist")
    if snapshot.get("timestamp_ms") is None:
        return ExtremeFundingClassification(None, "missing_timestamp")
    if snapshot.get("premium_index") is None:
        return ExtremeFundingClassification(None, "missing_premium")
    if float(snapshot.get("mark_data_age_sec", 0.0)) > EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC:
        return ExtremeFundingClassification(None, "api_stale")
    # OI missing/stale is not fatal in Phase 1A. It downgrades event level later.
    return ExtremeFundingClassification(None, "premium_below_threshold")
```

Import required config values from `configs.base`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/strategies/extreme_funding/scanner.py tests/strategies/test_extreme_funding_scanner.py
git commit -m "feat: classify extreme funding reject reasons"
```

---

### Task 5: Implement Timestamp-Window Micro Persistence

**Files:**
- Modify: `tests/strategies/test_extreme_funding_scanner.py`
- Modify: `src/strategies/extreme_funding/scanner.py`

- [ ] **Step 1: Write failing persistence tests**

Append:

```python
from strategies.extreme_funding.scanner import ExtremeFundingWatchlistScanner, compute_micro_persistence


def test_micro_persistence_counts_fraction_above_threshold():
    values = [10.0, 35.0, 40.0, 20.0]
    assert compute_micro_persistence(values, threshold_pct=30.0) == 0.5


def test_micro_persistence_empty_window_is_zero():
    assert compute_micro_persistence([], threshold_pct=30.0) == 0.0


def test_micro_persistence_uses_timestamp_window_not_sample_count():
    scanner = ExtremeFundingWatchlistScanner()
    scanner.append_observation("DOGE/USDT", timestamp_ms=0, annualized_pct=120.0)
    scanner.append_observation("DOGE/USDT", timestamp_ms=31 * 60_000, annualized_pct=10.0)

    values = scanner.get_window_values("DOGE/USDT", now_ms=31 * 60_000)

    assert values == [10.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py::test_micro_persistence_counts_fraction_above_threshold tests/strategies/test_extreme_funding_scanner.py::test_micro_persistence_empty_window_is_zero -v
```

Expected: FAIL with missing `compute_micro_persistence` or `ExtremeFundingWatchlistScanner`.

- [ ] **Step 3: Implement persistence helper**

Add:

```python
def compute_micro_persistence(values: list[float], *, threshold_pct: float) -> float:
    if not values:
        return 0.0
    above = sum(1 for value in values if value >= threshold_pct)
    return above / len(values)
```

Add timestamp-window storage:

```python
from collections import defaultdict, deque


class ExtremeFundingWatchlistScanner:
    def __init__(self) -> None:
        self._history = defaultdict(deque)

    def append_observation(self, symbol: str, *, timestamp_ms: int, annualized_pct: float) -> None:
        self._history[symbol].append((timestamp_ms, annualized_pct))
        self._prune_history(symbol, now_ms=timestamp_ms)

    def get_window_values(self, symbol: str, *, now_ms: int) -> list[float]:
        self._prune_history(symbol, now_ms=now_ms)
        return [value for _, value in self._history[symbol]]

    def _prune_history(self, symbol: str, *, now_ms: int) -> None:
        cutoff_ms = now_ms - EXTREME_FUNDING_MICRO_PERSISTENCE_WINDOW_MIN * 60_000
        while self._history[symbol] and self._history[symbol][0][0] < cutoff_ms:
            self._history[symbol].popleft()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/strategies/extreme_funding/scanner.py tests/strategies/test_extreme_funding_scanner.py
git commit -m "feat: add extreme funding micro persistence"
```

---

### Task 6: Implement Watch Level Detection

**Files:**
- Modify: `tests/strategies/test_extreme_funding_scanner.py`
- Modify: `src/strategies/extreme_funding/scanner.py`

- [ ] **Step 1: Write failing watch level tests**

Append:

```python
from strategies.extreme_funding.scanner import ExtremeFundingWatchlistScanner


def _snapshot(**overrides):
    base = {
        "symbol": "DOGE/USDT",
        "exchange": "binance",
        "timestamp_ms": 1,
        "premium_index": 0.001,
        "estimated_funding_rate": 0.0008,
        "open_interest": 1_000_000.0,
        "oi_change_1h_pct": 0.0,
        "volume_24h_usdt": 100_000_000.0,
        "mark_data_age_sec": 1.0,
        "oi_data_age_sec": 1.0,
    }
    base.update(overrides)
    return base


def test_premium_spike_without_persistence_is_rejected():
    scanner = ExtremeFundingWatchlistScanner()
    result = scanner.classify(_snapshot(premium_annualized_estimate_pct=80.0))
    assert result.event is None
    assert result.reject_reason == "micro_persistence_below_threshold"


def test_persistent_premium_with_weak_oi_returns_level_1():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(20):
        scanner.classify(_snapshot(timestamp_ms=minute * 60_000, premium_annualized_estimate_pct=35.0))
    result = scanner.classify(_snapshot(timestamp_ms=20 * 60_000, premium_annualized_estimate_pct=35.0))
    assert result.event is not None
    assert result.event.level == "watch_level_1"
    assert result.event.executable is False


def test_persistent_premium_with_oi_expansion_returns_level_2():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        scanner.classify(_snapshot(timestamp_ms=minute * 60_000, premium_annualized_estimate_pct=60.0, oi_change_1h_pct=1.0))
    result = scanner.classify(_snapshot(timestamp_ms=30 * 60_000, premium_annualized_estimate_pct=60.0, oi_change_1h_pct=1.0))
    assert result.event is not None
    assert result.event.level == "watch_level_2"


def test_strong_premium_with_strong_oi_returns_level_3():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        scanner.classify(_snapshot(timestamp_ms=minute * 60_000, premium_annualized_estimate_pct=120.0, oi_change_1h_pct=4.0))
    result = scanner.classify(_snapshot(timestamp_ms=30 * 60_000, premium_annualized_estimate_pct=120.0, oi_change_1h_pct=4.0))
    assert result.event is not None
    assert result.event.level == "watch_level_3"


def test_persistent_premium_with_missing_oi_returns_level_1_with_oi_missing_metadata():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        scanner.classify(_snapshot(timestamp_ms=minute * 60_000, premium_annualized_estimate_pct=60.0, oi_change_1h_pct=None))
    result = scanner.classify(_snapshot(timestamp_ms=30 * 60_000, premium_annualized_estimate_pct=60.0, oi_change_1h_pct=None))
    assert result.event is not None
    assert result.event.level == "watch_level_1"
    assert result.event.metadata["oi_status"] == "missing"
    assert result.reject_reason is None


def test_persistent_premium_with_stale_oi_returns_level_1_with_oi_stale_metadata():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        scanner.classify(_snapshot(timestamp_ms=minute * 60_000, premium_annualized_estimate_pct=60.0, oi_data_age_sec=181))
    result = scanner.classify(_snapshot(timestamp_ms=30 * 60_000, premium_annualized_estimate_pct=60.0, oi_data_age_sec=181))

    assert result.event is not None
    assert result.event.level == "watch_level_1"
    assert result.event.metadata["oi_status"] == "stale"
    assert result.reject_reason is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py -v
```

Expected: FAIL with missing `ExtremeFundingWatchlistScanner` behavior.

- [ ] **Step 3: Implement `ExtremeFundingWatchlistScanner.classify()`**

Implement:

- Per-symbol timestamp-windowed history of `premium_annualized_estimate_pct`.
- If snapshot includes `premium_annualized_estimate_pct`, use it directly.
- Otherwise derive annualized estimate from `premium_index`.
- Treat OI as level-confirmation metadata: missing/stale OI downgrades persistent premium events to `watch_level_1`; it must not suppress a premium anomaly.
- Classify `watch_level_1`, `watch_level_2`, `watch_level_3`.
- Return `ExtremeFundingClassification`.

Minimal derivation helper:

```python
def premium_to_naive_annualized_pct(premium_index: float, funding_intervals_per_day: int = 3) -> float:
    return premium_index * funding_intervals_per_day * 365 * 100
```

This field remains a naive pre-signal estimate, not settled funding. Every emitted event must include `metadata["estimate_type"] = "naive_premium_annualization"` and `metadata["not_settled_funding"] is True`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/strategies/extreme_funding/scanner.py tests/strategies/test_extreme_funding_scanner.py
git commit -m "feat: detect extreme funding watch levels"
```

---

### Task 7: Add Observation Scanner Async Wrapper

**Files:**
- Modify: `tests/strategies/test_extreme_funding_scanner.py`
- Modify: `src/strategies/extreme_funding/scanner.py`

- [ ] **Step 1: Write failing async scan test**

Append:

```python
import pytest


@pytest.mark.asyncio
async def test_scan_returns_watch_events_not_signal_candidates():
    scanner = ExtremeFundingWatchlistScanner()
    for minute in range(30):
        await scanner.scan(_snapshot(timestamp_ms=minute * 60_000, premium_annualized_estimate_pct=60.0, oi_change_1h_pct=1.0))

    events = await scanner.scan(_snapshot(timestamp_ms=30 * 60_000, premium_annualized_estimate_pct=60.0, oi_change_1h_pct=1.0))

    assert len(events) == 1
    assert isinstance(events[0], ExtremeFundingWatchEvent)
    assert events[0].executable is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py::test_scan_returns_watch_events_not_signal_candidates -v
```

Expected: FAIL if `scan()` is missing or returns wrong shape.

- [ ] **Step 3: Implement observation-only `scan()`**

`ExtremeFundingWatchlistScanner` must not subclass `BaseStrategy` in Phase 1A.

Implement:

```python
async def scan(self, market_data: dict[str, Any]) -> list[ExtremeFundingWatchEvent]:
    result = self.classify(market_data)
    return [result.event] if result.event is not None else []
```

Do not implement `should_exit()` or `risk_check()` in Phase 1A. Those are strategy/execution semantics and belong to Phase 1B or later.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/strategies/extreme_funding/scanner.py tests/strategies/test_extreme_funding_scanner.py
git commit -m "feat: add extreme funding watchlist scan wrapper"
```

---

### Task 8: Add Watchlist Daemon Skeleton

**Files:**
- Create: `scripts/run_extreme_funding_watchlist.py`
- Create: `tests/scripts/test_run_extreme_funding_watchlist.py`

- [ ] **Step 1: Write failing daemon unit tests**

Create `tests/scripts/test_run_extreme_funding_watchlist.py`:

```python
from scripts.run_extreme_funding_watchlist import should_poll, summarize_reject_counts


def test_should_poll_respects_interval():
    assert should_poll(last_poll_ts=0.0, now_ts=10.0, interval_sec=10) is True
    assert should_poll(last_poll_ts=5.0, now_ts=10.0, interval_sec=10) is False


def test_summarize_reject_counts_counts_reasons():
    summary = summarize_reject_counts(["premium_below_threshold", "api_stale", "api_stale"])
    assert summary == {"premium_below_threshold": 1, "api_stale": 2}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py -v
```

Expected: FAIL with missing script/module.

- [ ] **Step 3: Add minimal daemon helpers**

Create `scripts/run_extreme_funding_watchlist.py` with:

```python
from __future__ import annotations

from collections import Counter


def should_poll(*, last_poll_ts: float, now_ts: float, interval_sec: int) -> bool:
    return now_ts - last_poll_ts >= interval_sec


def summarize_reject_counts(reasons: list[str]) -> dict[str, int]:
    return dict(Counter(reasons))
```

Do not add live API polling in this task.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_extreme_funding_watchlist.py tests/scripts/test_run_extreme_funding_watchlist.py
git commit -m "feat: add extreme funding watchlist daemon skeleton"
```

---

### Task 9: Add Public Snapshot Adapter

**Files:**
- Modify: `scripts/run_extreme_funding_watchlist.py`
- Test: `tests/scripts/test_run_extreme_funding_watchlist.py`
- Read: `src/exchange/market_data.py`

- [ ] **Step 1: Write failing public snapshot adapter test**

Append:

```python
def test_build_snapshot_requires_no_private_fields():
    raw = {
        "symbol": "DOGE/USDT",
        "exchange": "binance",
        "timestamp_ms": 1,
        "mark_price": 0.25,
        "index_price": 0.249,
        "premium_index": 0.001,
        "estimated_funding_rate": 0.0008,
        "next_funding_time_ms": 100,
        "open_interest": 1000.0,
        "oi_change_1h_pct": 1.0,
        "volume_24h_usdt": 100000000.0,
        "mark_data_age_sec": 1.0,
        "oi_data_age_sec": 1.0,
        "apiKey": "must_drop",
        "secret": "must_drop",
    }

    snapshot = build_snapshot(raw)

    assert snapshot["symbol"] == "DOGE/USDT"
    assert "apiKey" not in snapshot
    assert "secret" not in snapshot
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py -v
```

Expected: FAIL with missing `build_snapshot`.

- [ ] **Step 3: Implement `build_snapshot()`**

Add a pure adapter that validates and copies only public fields:

```python
PUBLIC_SNAPSHOT_FIELDS = {
    "symbol",
    "exchange",
    "timestamp_ms",
    "mark_price",
    "index_price",
    "premium_index",
    "estimated_funding_rate",
    "next_funding_time_ms",
    "open_interest",
    "oi_change_1h_pct",
    "volume_24h_usdt",
    "mark_data_age_sec",
    "oi_data_age_sec",
}


def build_snapshot(raw: dict) -> dict:
    return {key: raw.get(key) for key in PUBLIC_SNAPSHOT_FIELDS}
```

Keep actual network polling behind `main()` and exclude it from unit tests.

Do not add Binance REST requests in this task. Real polling is a later daemon task after scanner and adapter tests are green.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_extreme_funding_watchlist.py tests/scripts/test_run_extreme_funding_watchlist.py
git commit -m "feat: add extreme funding public snapshot adapter"
```

---

### Task 10: Full Verification

**Files:**
- Verify: all changed files

- [ ] **Step 1: Run strategy tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py -v
```

Expected: PASS.

- [ ] **Step 2: Run script tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py -v
```

Expected: PASS.

- [ ] **Step 3: Run config test**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py -v
```

Expected: PASS.

- [ ] **Step 4: Run full test suite**

Run:

```bash
make test
```

Expected: PASS.

- [ ] **Step 5: Run smoke checks**

Run:

```bash
make smoke
```

Expected: PASS.

- [ ] **Step 6: Commit verification docs if updated**

If no docs changed, no commit.

If docs changed:

```bash
git add docs/plans/2026-05-24-extreme-funding-phase1-watchlist-implementation-plan.md
git commit -m "docs: add extreme funding phase 1a implementation plan"
```

---

## Phase 1A Done Definition

Phase 1A is done when:

- Config constants are in `configs/base.py`.
- Phase 1A class is named `ExtremeFundingWatchlistScanner` and does not subclass `BaseStrategy`.
- Watch event contract is tested.
- Reject reasons are deterministic and tested.
- Watch level detection is tested.
- Micro persistence is timestamp-window based, not sample-count based.
- Watch events mark `metadata["estimate_type"] = "naive_premium_annualization"` and `metadata["not_settled_funding"] is True`.
- OI missing/stale states are classified separately from premium failures.
- `RISK_LIVE_TRADING_ENABLED=False` does not suppress watch events.
- Daemon helpers are tested.
- Daemon imports no execution modules.
- No private API fields are required.
- Public snapshot adapter whitelists fields and drops private/unknown fields.
- No real network polling is added before scanner and adapter tests are green.
- `make test` passes.
- `make smoke` passes.

---

## Deferred Phase 1B Plan Notes

Phase 1B must not begin until Phase 1A is stable.

Required fields before Phase 1B:

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

Candidate conditions:

- `micro_persistence >= 0.70`
- `expected_funding_income_bps >= 50`
- `basis_absorption_ratio <= 0.50`
- `net_edge_bps >= 30`
- `depth_capacity >= 2 * planned_position_size`
- `estimated_slippage_bps <= 10`

Phase 1B emits observation-only `SignalCandidate` objects with `metadata["mode"] = "observation"` and `metadata["executable"] = False`.

---

## Deferred Phase 1C Plan Notes

Phase 1C validates shadow PnL over 1-3 funding intervals.

Historical pass gate:

- `candidate_count >= 30`
- `median_net_pnl_bps > 20`
- `mean_net_pnl_bps > 30`
- `win_rate > 55%`
- `max_single_trade_loss_bps` is bounded and explained
- losses mostly come from basis expansion, not fee drag

If historical high-funding windows fail these gates, Extreme Funding stays a dormant watchlist tool.

---

## Recommended Review Batches

Do not execute all tasks in one uninterrupted pass.

1. **Batch 1: Task 1-3** - confirm baseline, config constants, and watch event contract. Review that Phase 1A does not subclass `BaseStrategy`.
2. **Batch 2: Task 4-6** - confirm reject taxonomy, timestamp-window persistence, OI downgrade behavior, and watch level boundaries.
3. **Batch 3: Task 7-9** - confirm async observation wrapper, daemon skeleton, public snapshot adapter, and no execution/private config imports.
4. **Batch 4: Task 10** - run full verification and decide whether Phase 1A is ready for real public REST polling in a separate plan.

Review after each batch before continuing.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-24-extreme-funding-phase1-watchlist-implementation-plan.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Choose an execution approach before modifying `src/`.
