# Stage 1.5G Raw Snapshot Quarantine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. For every code task, use TDD: write the failing test, verify it fails, then implement the minimal code. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Stage 1.5G from a binary `invalid_book` hard gate into a quarantine-aware depth evidence reviewer that distinguishes clean pass, quarantined pass, and invalid evidence while preserving all trading/execution safety bans.

**Architecture:** Keep Stage 1.5G as an offline review module. Add explicit configuration in `configs/base.py`, pure quarantine classification helpers in `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`, then wire the result into `build_stage1_5g_review_summary()` and the CLI artifact writer. Raw Stage 1.5F snapshots remain immutable; quarantine outputs are derived Stage 1.5G artifacts.

**Tech Stack:** Python stdlib, dataclasses, JSON/JSONL artifacts, existing Stage 1.5G reviewer, pytest.

---

## 0. Safety Boundary

This implementation must preserve:

```text
stage1_5h_implementation_allowed = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
old_stage1_5f_artifact_rewrite_allowed = false
```

Quarantine means:

```text
invalid book rows are retained and explicitly counted as unavailable book evidence.
invalid book rows are excluded from spread/slippage/top-depth percentile calculations only.
invalid book rows are included in availability and stability gates.
```

Quarantine does not mean:

```text
remove invalid rows and pretend the 12h evidence was fully executable.
```

---

## 1. Current Code Map

Modify:

```text
configs/base.py
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py
```

Tests:

```text
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py
tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
```

Documentation after code passes:

```text
docs/reviews/2026-07-11-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md
```

No new dependency is allowed.

---

## 2. Data Field Assumptions

Stage 1.5G must resolve launch warmup anchor from existing Stage 1.5F fields in this order:

```text
1. accepted_event["symbol_effective_launch_times_ms"][symbol]
2. accepted_event["symbol_onboard_times_ms"][symbol]
3. accepted_event["observation_age_base_ms"] only when accepted_event["observation_age_basis"] in {
     "symbol_effective_launch_time",
     "symbol_onboard_time"
   }
4. state["observation_age_base_ms"] only when state["observation_age_basis"] in {
     "symbol_effective_launch_time",
     "symbol_onboard_time"
   }
5. fallback to observation_start_ms and label as observation_initial, not launch_warmup
```

Observation start should be resolved per `event_symbol_id` using:

```text
state["observation_started_at_ms"]
state["accepted_at_ms"]
accepted_event["accepted_at_ms"]
first snapshot fetched_at_ms
```

If no launch anchor exists, use observation initial fallback and emit:

```text
launch_time_missing_warmup_anchor_degraded
```

---

## 3. Task 1: Add Quarantine Config Constants

**Files:**

```text
Modify: configs/base.py
Modify test: tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py
```

- [ ] **Step 1: Write failing config test**

Append this test:

```python
def test_stage1_5g_quarantine_config_constants_exist_and_are_safe():
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_INVALID_BOOK_RATIO == 0.02
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_LAUNCH_WARMUP_WINDOW_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_LAUNCH_WARMUP_INVALID_ROW_COUNT == 15
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_LAUNCH_WARMUP_INVALID_MINUTE_BUCKET_COUNT == 12
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_MIDRUN_INVALID_BOOK_RATIO == 0.002
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_MIDRUN_INVALID_BOOK_COUNT == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_CONSECUTIVE_INVALID_AFTER_WARMUP == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_VALID_SNAPSHOTS_AFTER_QUARANTINE == 684
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_BOOK_AVAILABILITY_RATIO == 0.98
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_FIRST_VALID_BOOK_LATENCY_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_CROSSED_OR_NEGATIVE_BOOK_ALLOWED is False
```

- [ ] **Step 2: Run failing test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py::test_stage1_5g_quarantine_config_constants_exist_and_are_safe \
  -q
```

Expected: FAIL with missing `EXTERNAL_SIGNAL_STAGE1_5G_MAX_INVALID_BOOK_RATIO`.

- [ ] **Step 3: Add constants to `configs/base.py`**

Append under the Stage 1.5G config block:

```python
EXTERNAL_SIGNAL_STAGE1_5G_MAX_INVALID_BOOK_RATIO = 0.02
# Maximum invalid book row ratio allowed for quarantined evidence. 0.02 = 2%.

EXTERNAL_SIGNAL_STAGE1_5G_LAUNCH_WARMUP_WINDOW_MS = 15 * 60 * 1000
# Window after effective launch time where empty book can be classified as launch warmup.

EXTERNAL_SIGNAL_STAGE1_5G_MAX_LAUNCH_WARMUP_INVALID_ROW_COUNT = 15
# Maximum invalid snapshot rows allowed inside launch warmup.

EXTERNAL_SIGNAL_STAGE1_5G_MAX_LAUNCH_WARMUP_INVALID_MINUTE_BUCKET_COUNT = 12
# Maximum invalid UTC minute buckets allowed inside launch warmup.
# 12 is intentionally lower than the 15-minute warmup window: warmup may be mostly unavailable,
# but a full 15/15 minute unavailable launch window is not accepted in first quarantine version.

EXTERNAL_SIGNAL_STAGE1_5G_MAX_MIDRUN_INVALID_BOOK_RATIO = 0.002
# Maximum invalid book ratio after warmup. 0.002 = 0.2%.

EXTERNAL_SIGNAL_STAGE1_5G_MAX_MIDRUN_INVALID_BOOK_COUNT = 1
# Maximum invalid book rows allowed after warmup in first quarantine version.
# SKHYUSDT had exactly one midrun invalid row; count=1 is the boundary pass case.

EXTERNAL_SIGNAL_STAGE1_5G_MAX_CONSECUTIVE_INVALID_AFTER_WARMUP = 1
# Maximum consecutive invalid rows allowed after warmup.

EXTERNAL_SIGNAL_STAGE1_5G_MIN_VALID_SNAPSHOTS_AFTER_QUARANTINE = 684
# Minimum valid book rows after excluding quarantined invalid rows.

EXTERNAL_SIGNAL_STAGE1_5G_MIN_BOOK_AVAILABILITY_RATIO = 0.98
# Minimum valid_book_count / expected_snapshot_count for quarantined evidence.
# This is an AND condition with MIN_VALID_SNAPSHOTS_AFTER_QUARANTINE.
# 684/720 satisfies coverage but not availability; availability prevents over-accepting sparse valid books.

EXTERNAL_SIGNAL_STAGE1_5G_MAX_FIRST_VALID_BOOK_LATENCY_MS = 15 * 60 * 1000
# Maximum latency from launch/warmup anchor to first valid book.

EXTERNAL_SIGNAL_STAGE1_5G_CROSSED_OR_NEGATIVE_BOOK_ALLOWED = False
# Crossed or negative books are hard blockers in first quarantine version.
```

- [ ] **Step 4: Run config tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add configs/base.py tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py
git commit -m "feat: add stage1 5g quarantine config"
```

---

## 4. Task 2: Add Pure Quarantine Classification Helpers

**Files:**

```text
Modify: src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
Create: tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py
```

- [ ] **Step 1: Write helper tests for launch-time anchor and observation fallback**

Create the new test file with:

```python
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    compute_raw_snapshot_quarantine_metrics,
)


def _valid_snapshot(i: int, *, event_symbol_id="es1", symbol="SKHYUSDT", fetched_at_ms=None):
    t = i * 60_000 if fetched_at_ms is None else fetched_at_ms
    return {
        "event_symbol_id": event_symbol_id,
        "symbol": symbol,
        "fetched_at_ms": t,
        "best_bid": 100.0,
        "best_ask": 100.1,
        "mid_price": 100.05,
        "spread_bps": 10.0,
        "buy_slippage_bps": 5.0,
        "sell_slippage_bps": 5.0,
        "top_bid_depth_usdt": 1000.0,
        "top_ask_depth_usdt": 1000.0,
    }


def _empty_snapshot(i: int, *, event_symbol_id="es1", symbol="SKHYUSDT", fetched_at_ms=None):
    row = _valid_snapshot(i, event_symbol_id=event_symbol_id, symbol=symbol, fetched_at_ms=fetched_at_ms)
    row.update({
        "best_bid": None,
        "best_ask": None,
        "mid_price": None,
        "spread_bps": None,
        "depth_status": "invalid",
        "slippage_status": "invalid_depth",
        "top_bid_depth_usdt": 0.0,
        "top_ask_depth_usdt": 0.0,
        "buy_slippage_bps": None,
        "sell_slippage_bps": None,
    })
    return row


def test_warmup_phase_uses_launch_time_not_observation_start_when_available():
    launch_ms = 1_000_000
    observation_start_ms = launch_ms + 30 * 60_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=observation_start_ms),
        _valid_snapshot(1, fetched_at_ms=observation_start_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": observation_start_ms}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_by_reason["midrun_empty_book"] == 1
    assert result.invalid_book_by_reason["launch_warmup_empty_book"] == 0
    assert "launch_time_missing_warmup_anchor_degraded" not in result.warnings


def test_missing_launch_time_uses_observation_initial_label_with_warning():
    observation_start_ms = 2_000_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=observation_start_ms),
        _valid_snapshot(1, fetched_at_ms=observation_start_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": observation_start_ms}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_by_reason["observation_initial_empty_book"] == 1
    assert result.invalid_book_by_phase["observation_initial"] == 1
    assert "launch_time_missing_warmup_anchor_degraded" in result.warnings


def test_invalid_book_reason_classification_precedence():
    snapshots = [
        {"event_symbol_id": None, "symbol": "SKHYUSDT", "fetched_at_ms": 0, "best_bid": None, "best_ask": -1, "spread_bps": -5},
        {"event_symbol_id": "es1", "symbol": "SKHYUSDT", "fetched_at_ms": 60_000, "best_bid": 101.0, "best_ask": 100.0, "spread_bps": -1},
        _empty_snapshot(2, fetched_at_ms=120_000),
        _valid_snapshot(3, fetched_at_ms=180_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.schema_invalid_count == 1
    assert result.crossed_or_negative_book_count == 1
    assert result.invalid_book_by_reason["observation_initial_empty_book"] == 1
```

- [ ] **Step 2: Run tests to verify failure**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  -q
```

Expected: FAIL with `ImportError: cannot import name 'compute_raw_snapshot_quarantine_metrics'`.

- [ ] **Step 3: Add dataclasses and helper skeleton**

Add near `RawSnapshotIntegrityResult`:

```python
@dataclass(frozen=True)
class RawSnapshotQuarantineResult:
    blockers: list[str]
    warnings: list[str]
    clean_depth_evidence_pass: bool
    quarantined_depth_evidence_pass: bool
    quarantine_candidate: bool
    observed_snapshot_count: int
    expected_snapshot_count: int
    invalid_book_row_count: int
    invalid_book_minute_bucket_count: int
    invalid_book_ratio: float
    invalid_book_ratio_observed: float
    valid_snapshot_count_after_quarantine: int
    book_availability_ratio: float
    book_unavailable_ratio: float
    invalid_book_by_phase: dict[str, int]
    invalid_book_by_reason: dict[str, int]
    launch_warmup_invalid_row_count: int
    launch_warmup_invalid_minute_bucket_count: int
    midrun_invalid_book_count: int
    midrun_invalid_minute_bucket_count: int
    crossed_or_negative_book_count: int
    schema_invalid_count: int
    max_consecutive_invalid: int
    max_consecutive_invalid_after_warmup: int
    first_valid_book_latency_ms: int | None
    depth_quality_input_rows: list[dict]
    quarantined_invalid_book_rows: list[dict]
```

Add these pure helpers:

```python
def _minute_bucket_ms(ts_ms: int) -> int:
    return int(ts_ms) // 60000 * 60000


def _is_schema_invalid_snapshot(row: dict) -> bool:
    return not row.get("event_symbol_id") or not row.get("symbol") or row.get("fetched_at_ms") is None


def _is_empty_book_snapshot(row: dict) -> bool:
    return row.get("best_bid") is None or row.get("best_ask") is None or row.get("spread_bps") is None


def _is_crossed_or_negative_book(row: dict) -> bool:
    bid = row.get("best_bid")
    ask = row.get("best_ask")
    spread = row.get("spread_bps")
    if bid is None or ask is None:
        return False
    try:
        bid_f = float(bid)
        ask_f = float(ask)
        spread_f = None if spread is None else float(spread)
    except (TypeError, ValueError):
        return True
    return bid_f <= 0 or ask_f <= 0 or bid_f >= ask_f or (spread_f is not None and spread_f < 0)
```

Classification precedence must be fixed:

```text
1. schema_invalid: missing event_symbol_id / symbol / fetched_at_ms
2. crossed_or_negative_book: bid/ask parseable and bid<=0, ask<=0, bid>=ask, or spread<0
3. empty_book: bid/ask/spread missing
4. valid
```

This means a row with missing `event_symbol_id` and malformed bid/ask is `schema_invalid`, not empty book.

- [ ] **Step 4: Implement launch anchor resolution**

Add:

```python
def _resolve_event_launch_time_ms(event: dict, state: dict | None = None) -> int | None:
    symbol = event.get("symbol") or (state or {}).get("symbol")
    for field in ("symbol_effective_launch_times_ms", "symbol_onboard_times_ms"):
        mapping = event.get(field) or (state or {}).get(field) or {}
        if symbol and isinstance(mapping, dict) and mapping.get(symbol) is not None:
            return int(mapping[symbol])
    for obj in (event, state or {}):
        basis = obj.get("observation_age_basis")
        if basis in {"symbol_effective_launch_time", "symbol_onboard_time"} and obj.get("observation_age_base_ms") is not None:
            return int(obj["observation_age_base_ms"])
    return None


def _resolve_observation_start_ms(event_symbol_id: str, snapshots: list[dict], event: dict, state: dict | None = None) -> int | None:
    for obj in (state or {}, event):
        for field in ("observation_started_at_ms", "accepted_at_ms"):
            if obj.get(field) is not None:
                return int(obj[field])
    times = [int(s["fetched_at_ms"]) for s in snapshots if s.get("event_symbol_id") == event_symbol_id and s.get("fetched_at_ms") is not None]
    return min(times) if times else None
```

- [ ] **Step 5: Implement minimal `compute_raw_snapshot_quarantine_metrics()`**

Add the function and make the two tests pass. It must:

```text
- group accepted_events by event_symbol_id
- group states by event_symbol_id
- classify invalid rows as launch_warmup_empty_book, observation_initial_empty_book, midrun_empty_book, crossed_or_negative_book, or schema_invalid
- build depth_quality_input_rows from valid rows only
- build quarantined_invalid_book_rows with reason and phase
- compute row counts and minute bucket counts
- compute `max_consecutive_invalid` and `max_consecutive_invalid_after_warmup` after sorting by `(event_symbol_id, fetched_at_ms)`, not JSONL file order
- compute first_valid_book_latency_ms from launch_time_ms when available, otherwise observation_start_ms
```

- [ ] **Step 6: Run quarantine tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  -q
```

Expected: PASS for the two initial tests.

- [ ] **Step 7: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py
git commit -m "feat: classify stage1 5g invalid book quarantine rows"
```

---

## 5. Task 3: Add Quarantine Gates And Availability Metrics

**Files:**

```text
Modify: src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
Modify: tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py
```

- [ ] **Step 1: Add tests for row/minute bucket and availability**

Append:

```python
def test_invalid_rows_and_minute_buckets_are_counted_separately():
    launch_ms = 1_000_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=launch_ms),
        _empty_snapshot(1, fetched_at_ms=launch_ms + 10_000),
        _valid_snapshot(2, fetched_at_ms=launch_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_row_count == 2
    assert result.invalid_book_minute_bucket_count == 1
    assert result.launch_warmup_invalid_row_count == 2
    assert result.launch_warmup_invalid_minute_bucket_count == 1


def test_book_availability_ratio_uses_expected_snapshot_count():
    snapshots = [_valid_snapshot(i) for i in range(706)] + [_empty_snapshot(706 + i) for i in range(12)]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.valid_snapshot_count_after_quarantine == 706
    assert round(result.book_availability_ratio, 4) == round(706 / 720, 4)
    assert round(result.book_unavailable_ratio, 4) == round(12 / 720, 4)


def test_invalid_book_ratio_uses_observed_snapshot_count_not_expected_count():
    snapshots = [_valid_snapshot(i) for i in range(706)] + [_empty_snapshot(706 + i) for i in range(12)]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.observed_snapshot_count == 718
    assert result.expected_snapshot_count == 720
    assert round(result.invalid_book_ratio, 4) == round(12 / 718, 4)
    assert round(result.invalid_book_ratio_observed, 4) == round(12 / 718, 4)
    assert round(result.book_availability_ratio, 4) == round(706 / 720, 4)
```

- [ ] **Step 2: Add tests for first valid latency and midrun gates**

Append:

```python
def test_first_valid_book_latency_above_threshold_blocks_quarantined_pass():
    launch_ms = 1_000_000
    snapshots = [_empty_snapshot(i, fetched_at_ms=launch_ms + i * 60_000) for i in range(16)]
    snapshots.extend(_valid_snapshot(16 + i, fetched_at_ms=launch_ms + (16 + i) * 60_000) for i in range(700))

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert "first_valid_book_latency_too_high" in result.blockers
    assert result.quarantined_depth_evidence_pass is False


def test_midrun_invalid_count_two_blocks_quarantined_pass():
    launch_ms = 1_000_000
    snapshots = [_valid_snapshot(i, fetched_at_ms=launch_ms + i * 60_000) for i in range(718)]
    snapshots[30] = _empty_snapshot(30, fetched_at_ms=launch_ms + 30 * 60_000)
    snapshots[60] = _empty_snapshot(60, fetched_at_ms=launch_ms + 60 * 60_000)

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.midrun_invalid_book_count == 2
    assert "midrun_invalid_book_count_exceeded" in result.blockers
    assert result.quarantined_depth_evidence_pass is False


def test_max_consecutive_invalid_uses_fetched_at_ms_order_not_jsonl_order():
    launch_ms = 1_000_000
    snapshots = [
        _empty_snapshot(2, fetched_at_ms=launch_ms + 2 * 60_000),
        _valid_snapshot(0, fetched_at_ms=launch_ms),
        _empty_snapshot(3, fetched_at_ms=launch_ms + 3 * 60_000),
        _valid_snapshot(1, fetched_at_ms=launch_ms + 1 * 60_000),
        _empty_snapshot(4, fetched_at_ms=launch_ms + 4 * 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.max_consecutive_invalid == 3
```

- [ ] **Step 3: Run tests to verify failure**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  -q
```

Expected: FAIL until gate blockers and ratios are implemented.

- [ ] **Step 4: Implement gate logic in `compute_raw_snapshot_quarantine_metrics()`**

Gate blockers must use these exact keys:

```text
invalid_book_ratio_above_threshold
book_availability_ratio_below_threshold
first_valid_book_latency_too_high
launch_warmup_invalid_row_count_exceeded
launch_warmup_invalid_minute_bucket_count_exceeded
midrun_invalid_book_ratio_exceeded
midrun_invalid_book_count_exceeded
max_consecutive_invalid_after_warmup_exceeded
valid_snapshot_count_after_quarantine_below_threshold
crossed_or_negative_book
schema_invalid
expected_snapshot_count_missing
```

Result booleans:

```text
clean_depth_evidence_pass = invalid_book_row_count == 0 and no blockers
quarantine_candidate = invalid_book_row_count > 0 and crossed_or_negative_book_count == 0 and schema_invalid_count == 0
quarantined_depth_evidence_pass = quarantine_candidate and no blockers
```

Ratio semantics:

```text
observed_snapshot_count = len(snapshots)
expected_snapshot_count = coverage_result["expected_snapshot_count"] in production path
invalid_book_ratio = invalid_book_row_count / observed_snapshot_count
invalid_book_ratio_observed = invalid_book_ratio
book_availability_ratio = valid_snapshot_count_after_quarantine / expected_snapshot_count
book_unavailable_ratio = invalid_book_row_count / expected_snapshot_count
```

Production implementation rule:

```text
build_stage1_5g_review_summary() must not pass magic 720.
It must pass expected_snapshot_count from coverage_result["expected_snapshot_count"].
If coverage_result lacks a positive expected_snapshot_count, quarantine is unavailable and blocker expected_snapshot_count_missing is emitted.
Do not fallback to len(snapshots) as expected count, because that hides missed collection.
```

Formal evidence rule:

```text
compute_raw_snapshot_quarantine_metrics() may be used for diagnostics on any snapshot set.
build_stage1_5g_review_summary() may emit stage1_5g_depth_evidence_quarantined_pass only when:
  formal_announcement_and_launch_count >= 1
  and formal_completed_event_symbol_ids is non-empty.

Observation-only, launch_time_only, and recovery_validation_only samples may report quarantine diagnostics,
but must not be promoted to quarantined_pass.
```

- [ ] **Step 5: Run quarantine tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py
git commit -m "feat: add stage1 5g quarantine gates"
```

---

## 6. Task 4: Integrate Quarantine Into 1.5G Decision Flow

**Files:**

```text
Modify: src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
Modify: tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py
```

- [ ] **Step 1: Add decision tests**

Append tests:

```python
def make_skhy_quarantine_fixture():
    launch_ms = 1_000_000
    snapshots = make_depth_snapshots(event_symbol_id="es1", symbol="SKHYUSDT", count=718)
    for i in range(11):
        snapshots[i].update({
            "fetched_at_ms": launch_ms + i * 60_000,
            "best_bid": None,
            "best_ask": None,
            "mid_price": None,
            "spread_bps": None,
            "depth_status": "invalid",
            "slippage_status": "invalid_depth",
            "top_bid_depth_usdt": 0.0,
            "top_ask_depth_usdt": 0.0,
            "buy_slippage_bps": None,
            "sell_slippage_bps": None,
        })
    snapshots[320].update({
        "fetched_at_ms": launch_ms + 320 * 60_000,
        "best_bid": None,
        "best_ask": None,
        "mid_price": None,
        "spread_bps": None,
        "depth_status": "invalid",
        "slippage_status": "invalid_depth",
        "top_bid_depth_usdt": 0.0,
        "top_ask_depth_usdt": 0.0,
        "buy_slippage_bps": None,
        "sell_slippage_bps": None,
    })
    return launch_ms, snapshots


def test_skhyusdt_quarantine_candidate_allows_design_only_not_execution():
    launch_ms, snapshots = make_skhy_quarantine_fixture()
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "status": "completed",
            "depth_snapshot_count": 718,
            "max_gap_ms": 60_000,
            "observation_started_at_ms": launch_ms,
        }],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        snapshots=snapshots,
        request_manifest_rows=[{
            "request_type": "depth_snapshot",
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "http_status": 200,
        } for _ in range(718)],
    )

    assert result["decision"] == "stage1_5g_depth_evidence_quarantined_pass"
    assert result["allowed_next_action"] == "write_stage1_5h_design_only"
    assert result["clean_depth_evidence_pass"] is False
    assert result["quarantined_depth_evidence_pass"] is True
    assert result["execution_feasibility_claim_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False
    assert result["raw_integrity"]["invalid_book_count"] == 12
    assert result["quarantine"]["observed_snapshot_count"] == 718
    assert result["quarantine"]["expected_snapshot_count"] == 720
    assert result["quarantine"]["expected_snapshot_count"] == result["coverage_metrics"]["expected_snapshot_count"]
    assert result["quarantine"]["invalid_book_ratio_observed"] == result["quarantine"]["invalid_book_ratio"]
    assert result["quarantine"]["book_availability_ratio"] >= 0.98
    assert result["quarantine"]["midrun_invalid_book_count"] == 1


def test_two_midrun_invalid_books_keep_depth_evidence_invalid():
    launch_ms, snapshots = make_skhy_quarantine_fixture()
    snapshots[400].update(snapshots[320])
    snapshots[400]["fetched_at_ms"] = launch_ms + 400 * 60_000

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "status": "completed", "depth_snapshot_count": 718, "max_gap_ms": 60_000}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        snapshots=snapshots,
        request_manifest_rows=[{"request_type": "depth_snapshot", "event_symbol_id": "es1", "symbol": "SKHYUSDT", "http_status": 200} for _ in range(718)],
    )

    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "midrun_invalid_book_count_exceeded" in result["blockers"]


def test_quarantine_cannot_promote_observation_only_evidence_to_quarantined_pass():
    launch_ms, snapshots = make_skhy_quarantine_fixture()
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "status": "completed", "depth_snapshot_count": 718, "max_gap_ms": 60_000}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "evidence_label": "launch_time_only",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        snapshots=snapshots,
        request_manifest_rows=[{"request_type": "depth_snapshot", "event_symbol_id": "es1", "symbol": "SKHYUSDT", "http_status": 200} for _ in range(718)],
    )

    assert result["decision"] != "stage1_5g_depth_evidence_quarantined_pass"
    assert result["formal_announcement_and_launch_count"] == 0
    assert result.get("quarantined_depth_evidence_pass") is not True


def test_quarantine_expected_snapshot_count_missing_does_not_fallback_to_observed_rows(monkeypatch):
    from configs import base

    monkeypatch.delattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS", raising=False)
    monkeypatch.delattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC", raising=False)
    launch_ms, snapshots = make_skhy_quarantine_fixture()

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "status": "completed", "depth_snapshot_count": 718, "max_gap_ms": 60_000}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        snapshots=snapshots,
        request_manifest_rows=[{"request_type": "depth_snapshot", "event_symbol_id": "es1", "symbol": "SKHYUSDT", "http_status": 200} for _ in range(718)],
    )

    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "missing_stage1_5f_observation_config" in result["blockers"] or "expected_snapshot_count_missing" in result["blockers"]
    assert result.get("quarantined_depth_evidence_pass") is not True
```

- [ ] **Step 2: Run tests to verify failure**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py::test_skhyusdt_quarantine_candidate_allows_design_only_not_execution \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py::test_two_midrun_invalid_books_keep_depth_evidence_invalid \
  -q
```

Expected: FAIL. Current code returns `stage1_5g_depth_evidence_invalid` on any `invalid_book`.

- [ ] **Step 3: Integrate quarantine after coverage and before raw hard fail**

Implementation rule:

```text
1. compute coverage_result first.
2. compute raw_integrity_result for legacy metrics.
3. compute quarantine_result using expected_snapshot_count from coverage_result.
4. If raw_integrity has blockers other than invalid_book, keep invalid.
5. If invalid_book exists and quarantine_result.quarantined_depth_evidence_pass is true, continue to quarantined depth quality using valid rows.
6. If invalid_book exists and quarantine_result has blockers, return invalid with those blockers.
7. If no invalid_book, keep clean path.
8. If formal_announcement_and_launch_count == 0, never emit quarantined_pass even if quarantine_result passes.
9. If coverage_result["expected_snapshot_count"] is missing or <= 0, emit expected_snapshot_count_missing and do not compute availability from len(snapshots).
```

Use explicit decision strings:

```text
stage1_5g_depth_evidence_clean_pass
stage1_5g_depth_evidence_quarantined_pass
stage1_5g_depth_evidence_invalid
```

For backward compatibility, the previous sufficient decision may be retained as an alias only in documentation, not as the new primary clean decision.

- [ ] **Step 4: Ensure safety flags and summary fields**

Every pass result must include:

```python
"stage1_5h_implementation_allowed": False,
"execution_feasibility_claim_allowed": False,
"trade_signal_allowed": False,
"paper_trading_allowed": False,
"live_trading_allowed": False,
"execution_engine_allowed": False,
"alpha_interpretation_allowed": False,
```

Quarantined pass must include:

```python
"allowed_next_action": "write_stage1_5h_design_only",
"clean_depth_evidence_pass": False,
"quarantined_depth_evidence_pass": True,
"quarantine_candidate": True,
```

Clean pass must include:

```python
"allowed_next_action": "write_stage1_5h_design_or_shadow_simulator_design",
"clean_depth_evidence_pass": True,
"quarantined_depth_evidence_pass": False,
"quarantine_candidate": False,
```

- [ ] **Step 5: Run decision tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  -q
```

Expected: PASS. If older tests assert `stage1_5g_depth_evidence_sufficient_for_stage1_5h_plan`, update them to the new clean decision and allowed action only where the evidence is clean.

- [ ] **Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py
git commit -m "feat: add stage1 5g quarantine-aware decisions"
```

---

## 7. Task 5: Split Depth Quality From Book Availability Quality

**Files:**

```text
Modify: src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
Modify: tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py
```

- [ ] **Step 1: Write metric test**

Append:

```python
def test_quarantined_depth_quality_excludes_invalid_rows_but_reports_availability():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        compute_quarantined_depth_quality,
        compute_raw_snapshot_quarantine_metrics,
    )

    snapshots = make_healthy_snapshots(event_symbol_id="es1", symbol="SKHYUSDT", count=20)
    snapshots[0].update({
        "best_bid": None,
        "best_ask": None,
        "mid_price": None,
        "spread_bps": None,
        "depth_status": "invalid",
        "slippage_status": "invalid_depth",
        "top_bid_depth_usdt": 0.0,
        "top_ask_depth_usdt": 0.0,
        "buy_slippage_bps": None,
        "sell_slippage_bps": None,
    })
    quarantine = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "symbol_effective_launch_times_ms": {"SKHYUSDT": 0}}],
        expected_snapshot_count=20,
    )

    result = compute_quarantined_depth_quality(quarantine)

    assert result["depth_quality_clean_mode_available"] is False
    assert result["depth_quality_quarantined_mode_available"] is True
    assert result["quarantined_depth_quality"]["input_valid_rows"] == 19
    assert result["quarantined_depth_quality"]["excluded_invalid_rows"] == 1
    assert result["book_availability_quality"]["availability_ratio"] == 19 / 20
    assert result["depth_quality_input_mode"] == "quarantined_valid_rows"
```

- [ ] **Step 2: Run failing test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py::test_quarantined_depth_quality_excludes_invalid_rows_but_reports_availability \
  -q
```

Expected: FAIL with missing `compute_quarantined_depth_quality`.

- [ ] **Step 3: Implement wrapper**

Add:

```python
def compute_quarantined_depth_quality(quarantine_result: RawSnapshotQuarantineResult) -> dict:
    quality = compute_depth_quality_metrics(quarantine_result.depth_quality_input_rows)
    return {
        "depth_quality_clean_mode_available": False,
        "depth_quality_quarantined_mode_available": True,
        "quarantined_depth_quality": {
            **quality,
            "input_valid_rows": quarantine_result.valid_snapshot_count_after_quarantine,
            "excluded_invalid_rows": quarantine_result.invalid_book_row_count,
        },
        "book_availability_quality": {
            "availability_ratio": quarantine_result.book_availability_ratio,
            "unavailable_ratio": quarantine_result.book_unavailable_ratio,
            "max_consecutive_invalid": quarantine_result.max_consecutive_invalid,
            "max_consecutive_invalid_after_warmup": quarantine_result.max_consecutive_invalid_after_warmup,
            "first_valid_book_latency_ms": quarantine_result.first_valid_book_latency_ms,
        },
        "depth_quality_input_mode": "quarantined_valid_rows",
        "depth_quality_input_row_count": quarantine_result.valid_snapshot_count_after_quarantine,
        "excluded_invalid_book_row_count": quarantine_result.invalid_book_row_count,
        "blockers": quality.get("blockers", []),
        "warnings": quality.get("warnings", []),
    }
```

For clean evidence, continue using `compute_depth_quality_metrics(snapshots)` but wrap summary fields:

```python
"depth_quality_input_mode": "clean_all_rows"
```

- [ ] **Step 4: Wire into summary**

In quarantined pass path:

```text
- call compute_quarantined_depth_quality(quarantine_result)
- if returned blockers is non-empty, return invalid with depth_quality blockers
- otherwise attach as depth_quality and quarantine fields
```

In clean pass path:

```text
- call compute_depth_quality_metrics(snapshots)
- if blockers, existing observation_only/invalid behavior remains conservative
```

- [ ] **Step 5: Run metric and decision tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py
git commit -m "feat: split stage1 5g quarantine quality metrics"
```

---

## 8. Task 6: Write Derived Quarantine Artifacts From CLI

**Files:**

```text
Modify: src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
Modify: scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py
Modify: tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
```

- [ ] **Step 0: Preserve path parameter semantics**

Existing `build_stage1_5g_review_summary(output_root=...)` means Stage 1.5F input root and populates:

```text
summary["stage1_5f_output_root"]
```

Do not reuse it for Stage 1.5G review output artifacts.

Add a new keyword-only parameter:

```python
review_output_root: str | Path | None = None
```

Semantics:

```text
output_root = Stage 1.5F source artifact root, read-only audit provenance.
review_output_root = Stage 1.5G review output root, where derived quarantine artifacts may be written.
```

Docstring must state this distinction.

- [ ] **Step 1: Write CLI artifact test**

Append:

```python
def test_cli_writes_quarantine_derived_artifacts(tmp_path, monkeypatch):
    from tests.research.external_signal_shadow.test_stage1_5g_live_depth_evidence_review_loader import make_stage1_5f_fixture_root

    root = make_stage1_5f_fixture_root(tmp_path)
    output_root = tmp_path / "review_out"

    # Force one invalid row in the fixture snapshot file.
    snapshot_file = next((root / "depth_snapshots").glob("**/*.jsonl"))
    rows = [json.loads(line) for line in snapshot_file.read_text().splitlines() if line.strip()]
    rows[0].update({
        "best_bid": None,
        "best_ask": None,
        "mid_price": None,
        "spread_bps": None,
        "depth_status": "invalid",
        "slippage_status": "invalid_depth",
        "top_bid_depth_usdt": 0.0,
        "top_ask_depth_usdt": 0.0,
        "buy_slippage_bps": None,
        "sell_slippage_bps": None,
    })
    snapshot_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "review_stage1_5g_live_depth_evidence.py",
        "--stage1-5f-output-root", str(root),
        "--output-root", str(output_root),
    ])

    assert main() == 0
    assert (output_root / "stage1_5g_live_depth_evidence_review_summary.json").exists()
    assert (output_root / "quarantined_invalid_book_rows.jsonl").exists()
    assert (output_root / "depth_quality_input_rows.jsonl").exists()
    assert (output_root / "stage1_5g_quarantine_summary.json").exists()
```

Fixture note:

```text
`make_stage1_5f_fixture_root` already exists in
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py.
Reuse it. Do not create a duplicate fixture helper unless that existing helper is removed.
```

- [ ] **Step 2: Run failing CLI test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py::test_cli_writes_quarantine_derived_artifacts \
  -q
```

Expected: FAIL because derived files do not exist.

- [ ] **Step 3: Add artifact writer**

Add function:

```python
def write_stage1_5g_quarantine_artifacts(review_output_root: Path, quarantine_result: RawSnapshotQuarantineResult) -> dict[str, str]:
    review_output_root.mkdir(parents=True, exist_ok=True)
    invalid_path = review_output_root / "quarantined_invalid_book_rows.jsonl"
    valid_path = review_output_root / "depth_quality_input_rows.jsonl"
    summary_path = review_output_root / "stage1_5g_quarantine_summary.json"

    with invalid_path.open("w", encoding="utf-8") as fh:
        for row in quarantine_result.quarantined_invalid_book_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    with valid_path.open("w", encoding="utf-8") as fh:
        for row in quarantine_result.depth_quality_input_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump({
            "invalid_book_row_count": quarantine_result.invalid_book_row_count,
            "valid_snapshot_count_after_quarantine": quarantine_result.valid_snapshot_count_after_quarantine,
            "book_availability_ratio": quarantine_result.book_availability_ratio,
            "blockers": quarantine_result.blockers,
            "warnings": quarantine_result.warnings,
        }, fh, indent=2, ensure_ascii=False)

    return {
        "quarantined_rows_path": str(invalid_path),
        "depth_quality_input_rows_path": str(valid_path),
        "quarantine_summary_path": str(summary_path),
    }
```

- [ ] **Step 4: Pass `review_output_root` through CLI**

Change CLI order:

```text
1. resolve out_root before building summary
2. load bundle
3. build summary with review_output_root=out_root
4. write summary JSON and markdown
```

Add optional kwarg to `build_stage1_5g_review_summary()`:

```python
review_output_root: str | Path | None = None,
```

When quarantine_result exists and `review_output_root is not None`, write artifacts and attach returned paths to `summary["quarantine"]`.

Artifact write condition:

```text
Only write quarantine artifacts when quarantine_result.invalid_book_row_count > 0.
Clean pass must not write empty quarantine files unless a future plan explicitly adds
quarantine_artifacts_written=true with clear semantics.
```

Add an additional CLI test:

```python
def test_cli_does_not_write_quarantine_artifacts_for_clean_pass(tmp_path, monkeypatch):
    from tests.research.external_signal_shadow.test_stage1_5g_live_depth_evidence_review_loader import make_stage1_5f_fixture_root

    root = make_stage1_5f_fixture_root(tmp_path)
    output_root = tmp_path / "review_out"
    monkeypatch.setattr("sys.argv", [
        "review_stage1_5g_live_depth_evidence.py",
        "--stage1-5f-output-root", str(root),
        "--output-root", str(output_root),
    ])

    assert main() == 0
    assert not (output_root / "quarantined_invalid_book_rows.jsonl").exists()
    assert not (output_root / "depth_quality_input_rows.jsonl").exists()
    assert not (output_root / "stage1_5g_quarantine_summary.json").exists()
```

- [ ] **Step 5: Run CLI tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
git commit -m "feat: write stage1 5g quarantine artifacts"
```

---

## 9. Task 7: Update Chinese Review Output

**Files:**

```text
Modify: src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
Modify: tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py
```

- [ ] **Step 1: Write markdown content test**

Append:

```python
def test_chinese_review_includes_quarantine_section_for_quarantined_pass():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import generate_stage1_5g_chinese_review

    markdown = generate_stage1_5g_chinese_review({
        "decision": "stage1_5g_depth_evidence_quarantined_pass",
        "allowed_next_action": "write_stage1_5h_design_only",
        "evidence_scope": "single_event",
        "event_family_conclusion_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "execution_feasibility_claim_allowed": False,
        "blockers": [],
        "warnings": ["not_clean_depth_evidence"],
        "formal_announcement_and_launch_count": 1,
        "evidence_label_counts": {"announcement_and_launch_time": 1},
        "coverage_metrics": {},
        "raw_integrity": {"invalid_book_count": 12},
        "depth_quality": {},
        "quarantine": {
            "invalid_book_row_count": 12,
            "book_availability_ratio": 0.9806,
            "first_valid_book_latency_ms": 660000,
            "max_consecutive_invalid": 11,
            "max_consecutive_invalid_after_warmup": 1,
            "execution_availability_claim": "partial_not_clean",
        },
    })

    assert "Quarantine" in markdown or "隔离" in markdown
    assert "partial_not_clean" in markdown
    assert "write_stage1_5h_design_only" in markdown
```

- [ ] **Step 2: Run failing test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py::test_chinese_review_includes_quarantine_section_for_quarantined_pass \
  -q
```

Expected: FAIL because review lacks quarantine section.

- [ ] **Step 3: Add markdown section**

In `generate_stage1_5g_chinese_review()`, after raw integrity section add:

```text
## 6. Quarantine 审计
```

Include these fields when `summary.get("quarantine")` exists:

```text
invalid_book_row_count
invalid_book_minute_bucket_count
book_availability_ratio
book_unavailable_ratio
first_valid_book_latency_ms
max_consecutive_invalid
max_consecutive_invalid_after_warmup
execution_availability_claim
quarantined_rows_path
depth_quality_input_rows_path
```

State explicitly:

```text
quarantined pass 只能支持 1.5H design，不允许 execution feasibility claim / paper / live。
```

- [ ] **Step 4: Run markdown test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py::test_chinese_review_includes_quarantine_section_for_quarantined_pass \
  -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py
git commit -m "docs: report stage1 5g quarantine review fields"
```

---

## 10. Task 8: Update SKHYUSDT Review Document

**Files:**

```text
Modify: docs/reviews/2026-07-11-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md
```

- [ ] **Step 1: Update conclusion text**

Add a section:

```markdown
## Quarantine Design Follow-up

当前 SKHYUSDT 在旧 hard gate 下仍保持 `stage1_5g_depth_evidence_invalid` 结论，原因是存在 `invalid_book`。

根据 `docs/designs/2026-07-11-external-signal-shadow-lab-stage1-5g-raw-snapshot-quarantine-design_CN.md`，该样本将作为 quarantine-aware 1.5G 的 regression fixture：

- `invalid_book_row_count = 12`
- `valid_snapshot_count_after_quarantine = 706`
- `book_availability_ratio ~= 0.9806`
- `first_valid_book_latency_ms ~= 660000`
- `max_consecutive_invalid = 11`
- `max_consecutive_invalid_after_warmup = 1`
- 预期新规则下为 `stage1_5g_depth_evidence_quarantined_pass`
- `allowed_next_action = write_stage1_5h_design_only`
- `execution_feasibility_claim_allowed = false`

该结论不得被解释为 clean pass，不得进入 1.5H implementation，不得用于 paper/live。
```

- [ ] **Step 2: Run doc format check**

```bash
git diff --check -- docs/reviews/2026-07-11-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add docs/reviews/2026-07-11-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md
git commit -m "docs: record stage1 5g quarantine follow-up"
```

---

## 11. Task 9: Verification Gate

Run targeted tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q
```

Expected: PASS.

Run whitespace check:

```bash
git diff --check
```

Expected: no output.

Run safety grep:

```bash
rg -n "paper_trading_allowed\": true|live_trading_allowed\": true|execution_engine_allowed\": true|trade_signal_allowed\": true|execution_feasibility_claim_allowed\": true" \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_*.py
```

Expected: no output.

Manual server rerun after deployment:

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export STAGE1_5G_OUT="data/external_signal_shadow/stage1_5g/reviews/${RUN_ID}"

python scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  --stage1-5f-output-root "$STAGE1_5F_OUT" \
  --output-root "$STAGE1_5G_OUT" \
  --output-summary "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review_summary.json" \
  --output-review "docs/reviews/$(date -u +%Y-%m-%d)-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_SKHYUSDT_CN.md"
```

Expected for SKHYUSDT after implementation:

```text
Decision: stage1_5g_depth_evidence_quarantined_pass
Allowed next action: write_stage1_5h_design_only
```

Then inspect:

```bash
python - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ["STAGE1_5G_OUT"]) / "stage1_5g_live_depth_evidence_review_summary.json"
s = json.loads(p.read_text())
for k in [
    "decision",
    "allowed_next_action",
    "clean_depth_evidence_pass",
    "quarantined_depth_evidence_pass",
    "execution_feasibility_claim_allowed",
    "quarantine",
]:
    print(f"\n=== {k} ===")
    print(json.dumps(s.get(k), indent=2, ensure_ascii=False))
PY

wc -l "$STAGE1_5G_OUT/quarantined_invalid_book_rows.jsonl"
wc -l "$STAGE1_5G_OUT/depth_quality_input_rows.jsonl"
cat "$STAGE1_5G_OUT/stage1_5g_quarantine_summary.json" | python -m json.tool
```

Expected:

```text
quarantined_invalid_book_rows.jsonl line count = 12
depth_quality_input_rows.jsonl line count = 706
execution_feasibility_claim_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

---

## 12. Final Commit

After all tests pass:

```bash
git status --short
git add configs/base.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  docs/reviews/2026-07-11-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md

git commit -m "feat: add stage1 5g raw snapshot quarantine review"
```

If any verification fails, do not commit final batch. Keep the smallest passing commit set and report the failing gate.

---

## 13. Scope Guard

This plan does not implement Stage 1.5H.

This plan does not modify Stage 1.5F collection, request cadence, or depth snapshot generation.

This plan does not convert quarantined evidence into execution feasibility.
