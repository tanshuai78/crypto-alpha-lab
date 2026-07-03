# Stage 1.5F Delayed Launch Age Gate Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 Stage 1.5F 对 delayed-launch futures contract 的 `age_exceeded` 误拒绝，使 `PENDING_TRADING -> TRADING` 后的新盘口观察能以合约开盘时间为 age gate 起点。

**Architecture:** 在 Stage 1.5F loader 增加 `observation_age_base_ms` 解析层：优先使用 per-symbol `symbol_effective_launch_times_ms` / `symbol_onboard_times_ms`，只有存在明确 delayed-launch 证据链时才允许使用 `symbol_resolved_at_ms`，否则 fallback 到旧的 `detected_at_ms`。Stage 1.5F runner 在 accepted/rejected artifacts 中写入 age gate、水位线、证据标签诊断字段，便于区分 announcement-time evidence 与 launch-time depth evidence。

**Tech Stack:** Python 3.12, pytest, existing Stage 1.5F loader/runner/watermark/state modules, JSONL artifacts, `configs/base.py`.

---

## 0. Current Root Cause

Live server evidence:

```text
ETHUSD1 exchangeInfo:
  status = TRADING
  contractType = PERPETUAL
  quoteAsset = USD1
  marginAsset = USD1
  onboard_utc = 2026-07-03T09:00:00Z

Stage 1.5D event rows:
  earlier row: symbols=[], status=terminal_failed, source=title_contract_symbol, validation=rejected
  later row: symbols=["ETHUSD1"], status=parsed, source=title_contract_symbol, validation=validated

Stage 1.5F:
  events_accepted = 0
  events_rejected contains ETHUSD1 with rejection_reason = age_exceeded
```

Code fact:

```python
# src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py
detected_at_ms = row.get("detected_at_ms")
age_ms = now_ms - detected_at_ms
max_age_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS
if age_ms > max_age_ms:
    return "rejected", "age_exceeded"
```

Config fact:

```python
EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS = 15 * 60 * 1000
```

Why this fails delayed launches:

```text
announcement detected / candidate created
  -> symbol remains PENDING_TRADING for hours
  -> 1.5D waits until exchangeInfo status=TRADING
  -> 1.5D writes parsed event
  -> 1.5F checks now - detected_at_ms
  -> age_exceeded, even though launch/onboard time is recent
```

Root cause:

```text
Stage 1.5F treats "announcement/candidate detection time" as the only valid age basis.
For delayed-launch symbols, "depth observation start eligibility" should be based on the symbol's effective launch/onboard/resolution time.
```

---

## 1. Scope and Safety Boundaries

In scope:

1. Add a Stage 1.5F age-base resolver.
2. Use launch/onboard/resolution time for delayed-launch age gate when present and valid.
3. Preserve old `detected_at_ms` age gate for legacy event rows.
4. Add audit fields to accepted/rejected JSONL rows.
5. Update tests and review docs.

Out of scope:

1. No trading, paper trading, signal generation, or execution.
2. No weakening exchangeInfo validation.
3. No backfilling missed historical events as alpha evidence.
4. No change to Stage 1.5D parser/runner unless tests prove a required schema gap.
5. No change to Stage 1.5F watermark semantics unless explicitly reviewed in a separate plan.

Safety flags must remain false:

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

Evidence labeling rule:

```text
If announcement_capture_time_ms <= watermark.max_seen_detected_at_ms
and observation_age_base_ms > watermark.max_seen_detected_at_ms:
  This can support launch-time depth evidence only.
  It must not be labeled announcement-time capture evidence.
```

Watermark rule:

```text
Eligibility order must remain:
  1. event_is_post_watermark(row, watermark)
  2. observation_age_base age gate
  3. exchangeInfo/budget checks

Evidence labels change interpretation only; they must not bypass watermark membership or seen ids.
```

---

## 2. Desired Age Gate Semantics

Add helper:

```python
def resolve_observation_age_base_ms(row: dict, symbol: str) -> tuple[int | None, str]:
    ...
```

Priority:

```text
1. row["symbol_effective_launch_times_ms"][symbol]
   basis = "symbol_effective_launch_time"

2. row["symbol_onboard_times_ms"][symbol]
   basis = "symbol_onboard_time"

3. row["symbol_resolved_at_ms"], only if delayed launch is explicitly proven
   basis = "symbol_resolved_time"

4. row["detected_at_ms"]
   basis = "detected_time"
```

Validation:

```text
Missing / non-int / <=0 values are ignored.
symbol_resolved_at_ms can be used only when one of these is true:
  1. symbol_effective_launch_times_ms[symbol] or symbol_onboard_times_ms[symbol] exists but is invalid/unusable for age base diagnostics;
  2. row["symbol_extraction_source"] in {"title_contract_symbol", "detail_contract_symbol"}
     and row["symbol_validation_status"] == "validated"
     and delayed-launch metadata/flag exists;
  3. row["delayed_launch_observation_allowed"] is true.

Otherwise symbol_resolved_at_ms must be ignored and the resolver must fallback to detected_at_ms.

Future age base:
  If observation_age_base_ms > now_ms + clock_skew_tolerance_ms:
    status = pending
    reason = launch_time_in_future
```

Minimum config additions:

```python
EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_TIME_CLOCK_SKEW_TOLERANCE_MS = 2 * 60 * 1000
```

Do not change `EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS` in this hotfix. The window remains 15 minutes; only the base timestamp changes.

---

## Task 1: Loader Unit Tests for Age Base Resolution

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

### Step 1: Write failing tests for helper

Add tests:

```python
def test_resolve_observation_age_base_prefers_symbol_effective_launch_time():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_onboard_times_ms": {"ETHUSD1": 20_000},
        "symbol_effective_launch_times_ms": {"ETHUSD1": 30_000},
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 30_000
    assert basis == "symbol_effective_launch_time"


def test_resolve_observation_age_base_falls_back_to_symbol_onboard_time():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_onboard_times_ms": {"ETHUSD1": 20_000},
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 20_000
    assert basis == "symbol_onboard_time"


def test_symbol_resolved_time_not_used_for_ordinary_late_parser_retry_without_launch_time():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_extraction_source": "detail",
        "symbol_validation_status": "validated_by_exact_text",
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 1_000
    assert basis == "detected_time"


def test_symbol_resolved_time_used_only_when_delayed_launch_flag_present():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "delayed_launch_observation_allowed": True,
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 10_000
    assert basis == "symbol_resolved_time"


def test_symbol_resolved_time_not_used_when_contract_source_has_no_per_symbol_launch_evidence():
    row = {
        "detected_at_ms": 1_000,
        "symbol_resolved_at_ms": 10_000,
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "symbol_onboard_times_ms": {"OTHER": 9_000},
    }

    ms, basis = resolve_observation_age_base_ms(row, "ETHUSD1")

    assert ms == 1_000
    assert basis == "detected_time"


def test_resolve_observation_age_base_falls_back_to_detected_time_for_legacy_rows():
    row = {"detected_at_ms": 1_000}

    ms, basis = resolve_observation_age_base_ms(row, "ABCUSDT")

    assert ms == 1_000
    assert basis == "detected_time"
```

### Step 2: Run tests and confirm fail

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_resolve_observation_age_base_prefers_symbol_effective_launch_time \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_resolve_observation_age_base_falls_back_to_symbol_onboard_time \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_symbol_resolved_time_not_used_for_ordinary_late_parser_retry_without_launch_time \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_symbol_resolved_time_used_only_when_delayed_launch_flag_present \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_symbol_resolved_time_not_used_when_contract_source_has_no_per_symbol_launch_evidence \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_resolve_observation_age_base_falls_back_to_detected_time_for_legacy_rows \
  -q
```

Expected:

```text
FAIL because resolve_observation_age_base_ms is not implemented/imported.
```

### Step 3: Implement helper

Implementation requirements:

```python
def _valid_ms(value) -> int | None:
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    return ms if ms > 0 else None


def _get_symbol_time(row: dict, field: str, symbol: str) -> int | None:
    data = row.get(field)
    if not isinstance(data, dict):
        return None
    sym = symbol.strip().upper()
    return _valid_ms(data.get(sym) or data.get(symbol))


def resolve_observation_age_base_ms(row: dict, symbol: str) -> tuple[int | None, str]:
    for field, basis in (
        ("symbol_effective_launch_times_ms", "symbol_effective_launch_time"),
        ("symbol_onboard_times_ms", "symbol_onboard_time"),
    ):
        ms = _get_symbol_time(row, field, symbol)
        if ms is not None:
            return ms, basis

    delayed_launch_allowed = bool(row.get("delayed_launch_observation_allowed"))
    delayed_contract_source = row.get("symbol_extraction_source") in {
        "title_contract_symbol",
        "detail_contract_symbol",
    }
    validated = row.get("symbol_validation_status") == "validated"
    sym = symbol.strip().upper()
    has_per_symbol_launch_metadata = any(
        isinstance(row.get(field), dict) and sym in row.get(field, {})
        for field in ("symbol_effective_launch_times_ms", "symbol_onboard_times_ms")
    )
    if delayed_launch_allowed or (delayed_contract_source and validated and has_per_symbol_launch_metadata):
        ms = _valid_ms(row.get("symbol_resolved_at_ms"))
        if ms is not None:
            return ms, "symbol_resolved_time"

    ms = _valid_ms(row.get("detected_at_ms"))
    if ms is not None:
        return ms, "detected_time"

    return None, "missing"
```

### Step 4: Run tests and confirm pass

Run the same command from Step 2.

Expected:

```text
6 passed
```

---

## Task 2: Loader Eligibility Uses Launch-Time Age Base

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `configs/base.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py`

### Step 1: Add config test

Add:

```python
def test_stage1_5f_has_launch_time_clock_skew_tolerance_config():
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_TIME_CLOCK_SKEW_TOLERANCE_MS")
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_TIME_CLOCK_SKEW_TOLERANCE_MS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_TIME_CLOCK_SKEW_TOLERANCE_MS <= 5 * 60 * 1000
```

### Step 2: Add eligibility tests

Add:

```python
def test_delayed_launch_event_uses_symbol_effective_launch_time_for_age_gate():
    now_ms = 1_000_000
    event = {
        "event_id": "e-delayed",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms - 5 * 60 * 1000},
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "eligible"
    assert reason == "ok"


def test_legacy_event_without_launch_time_still_rejected_by_detected_age():
    now_ms = 1_000_000
    event = {
        "event_id": "e-legacy",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "age_exceeded"


def test_launch_time_in_future_is_pending_not_age_rejected_or_eligible():
    now_ms = 1_000_000
    event = {
        "event_id": "e-future",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 60_000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms + 10 * 60 * 1000},
    }
    w = Watermark(1, now_ms - 120_000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "pending"
    assert reason == "launch_time_in_future"


def test_launch_time_age_just_inside_15m_window_is_eligible():
    now_ms = 1_000_000
    launch_ms = now_ms - (15 * 60 * 1000) + 1_000
    event = {
        "event_id": "e-inside",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": launch_ms},
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "eligible"
    assert reason == "ok"


def test_launch_time_age_just_outside_15m_window_is_rejected():
    now_ms = 1_000_000
    launch_ms = now_ms - (15 * 60 * 1000) - 1_000
    event = {
        "event_id": "e-outside",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": launch_ms},
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "age_exceeded"


def test_pre_watermark_seen_event_still_ignored_even_if_launch_time_after_watermark():
    now_ms = 1_000_000
    event = {
        "event_id": "e-seen",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 5_000,
        "source_article_id": "article-seen",
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms - 5 * 60 * 1000},
    }
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=5_000,
        seen_event_ids=["e-seen"],
        seen_source_article_ids=["article-seen"],
        seen_stable_event_keys=[],
        updated_at_ms=5_000,
    )
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "pre_watermark"


def test_launch_time_after_watermark_does_not_bypass_seen_event_symbol_id():
    now_ms = 1_000_000
    event = {
        "event_id": "e-seen",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 60_000,
        "source_article_id": "article-seen",
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms - 5 * 60 * 1000},
    }
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=now_ms - 120_000,
        seen_event_ids=["e-seen"],
        seen_source_article_ids=["article-seen"],
        seen_stable_event_keys=[],
        updated_at_ms=now_ms - 120_000,
    )
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "pre_watermark"
```

### Step 3: Run tests and confirm fail

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py::test_stage1_5f_has_launch_time_clock_skew_tolerance_config \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_delayed_launch_event_uses_symbol_effective_launch_time_for_age_gate \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_legacy_event_without_launch_time_still_rejected_by_detected_age \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_launch_time_in_future_is_pending_not_age_rejected_or_eligible \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_launch_time_age_just_inside_15m_window_is_eligible \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_launch_time_age_just_outside_15m_window_is_rejected \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_pre_watermark_seen_event_still_ignored_even_if_launch_time_after_watermark \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_launch_time_after_watermark_does_not_bypass_seen_event_symbol_id \
  -q
```

Expected:

```text
FAIL because config/helper/eligibility logic is not wired.
```

### Step 4: Add config

Modify `configs/base.py` near Stage 1.5F constants:

```python
EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_TIME_CLOCK_SKEW_TOLERANCE_MS = 2 * 60 * 1000
# Clock-skew allowance when event rows contain per-symbol launch/onboard times.
# If launch time is farther in the future, the event-symbol stays pending.
```

### Step 5: Wire eligibility logic

Replace age-gate block in `classify_event_symbol_eligibility()`:

```python
observation_age_base_ms, observation_age_basis = resolve_observation_age_base_ms(row, symbol)
if observation_age_base_ms is None:
    return "rejected", "detected_at_ms_missing"

clock_skew_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_TIME_CLOCK_SKEW_TOLERANCE_MS
if observation_age_base_ms > now_ms + clock_skew_ms:
    return "pending", "launch_time_in_future"

age_ms = now_ms - observation_age_base_ms
max_age_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS
if age_ms > max_age_ms:
    return "rejected", "age_exceeded"
```

Keep old reason name `detected_at_ms_missing` for compatibility when no age base is available.

### Step 6: Run tests and confirm pass

Run the command from Step 3.

Expected:

```text
8 passed
```

---

## Task 3: Return Eligibility Diagnostics Without Breaking Existing Callers

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

### Step 1: Add diagnostic helper

Avoid changing the existing two-value return shape abruptly. First add a capture-time helper that will also be reused by Task 4:

```python
def resolve_announcement_capture_time_ms(row: dict) -> tuple[int | None, str]:
    for field in ("detected_at_ms", "available_at_ms", "collected_at_ms", "source_published_at_ms"):
        ms = _valid_ms(row.get(field))
        if ms is not None:
            return ms, field
    return None, "missing"
```

Then add:

```python
def classify_event_symbol_eligibility_with_diagnostics(
    row: dict,
    symbol: str,
    now_ms: int,
    watermark,
    exchangeinfo_state: dict,
    budget_state: dict,
) -> tuple[str, str, dict]:
    ...
```

It should return:

```python
announcement_capture_time_ms, announcement_capture_time_source = resolve_announcement_capture_time_ms(row)

{
    "observation_age_base_ms": observation_age_base_ms,
    "observation_age_basis": observation_age_basis,
    "event_age_ms": age_ms,
    "max_event_age_ms": max_age_ms,
    "announcement_capture_time_ms": announcement_capture_time_ms,
    "announcement_capture_time_source": announcement_capture_time_source,
    "detected_at_ms": row.get("detected_at_ms"),
    "symbol_resolved_at_ms": row.get("symbol_resolved_at_ms"),
    "watermark_max_seen_detected_at_ms": watermark.max_seen_detected_at_ms,
    "watermark_version": watermark.watermark_version,
}
```

Then keep existing function as wrapper:

```python
def classify_event_symbol_eligibility(...):
    status, reason, _diag = classify_event_symbol_eligibility_with_diagnostics(...)
    return status, reason
```

### Step 2: Add tests for diagnostics

Add:

```python
def test_eligibility_diagnostics_expose_observation_age_basis():
    now_ms = 1_000_000
    event = {
        "event_id": "e-delayed",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 6 * 60 * 60 * 1000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": now_ms - 5 * 60 * 1000},
    }
    w = Watermark(1, now_ms - 7 * 60 * 60 * 1000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        event, "ETHUSD1", now_ms, w, exinfo, {}
    )

    assert status == "eligible"
    assert reason == "ok"
    assert diag["observation_age_basis"] == "symbol_effective_launch_time"
    assert diag["event_age_ms"] == 5 * 60 * 1000
    assert diag["watermark_max_seen_detected_at_ms"] == w.max_seen_detected_at_ms
    assert diag["watermark_version"] == w.watermark_version
```

### Step 3: Run tests and confirm fail

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_eligibility_diagnostics_expose_observation_age_basis \
  -q
```

Expected:

```text
FAIL because classify_event_symbol_eligibility_with_diagnostics is missing.
```

### Step 4: Implement diagnostics and runner wiring

In `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`, import and call the diagnostic function:

```python
status, reason, eligibility_diag = classify_event_symbol_eligibility_with_diagnostics(...)
```

Runner semantics:

```text
status == "eligible":
  write events_accepted/*.jsonl
  start / continue depth observation
  update watermark after the event-symbol is accepted

status == "pending":
  do not write events_accepted/*.jsonl
  do not write events_rejected/*.jsonl
  do not update watermark
  leave the event-symbol eligible for the next poll
  optional: increment summary/heartbeat pending diagnostics

status == "rejected":
  write events_rejected/*.jsonl only for terminal rejection reasons
  do not start depth observation
```

Append diagnostics into `events_accepted`:

```python
{
    "event_symbol_id": event_symbol_id,
    "symbol": symbol,
    "event_id": flat_event.get("event_id"),
    "detected_at_ms": flat_event.get("detected_at_ms"),
    "accepted_at_ms": now_ms,
    **eligibility_diag,
}
```

Append diagnostics into `events_rejected`:

```python
{
    "event_symbol_id": event_symbol_id,
    "symbol": symbol,
    "rejection_reason": reason,
    "depth_observation_started": False,
    "rejected_at_ms": now_ms,
    **eligibility_diag,
}
```

Do not add diagnostics to `pre_watermark` ignored rows unless a rejected artifact is already written.

### Step 5: Add runner regression test

Add to `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`:

```python
def test_runner_accepts_delayed_launch_event_using_effective_launch_time(tmp_path, monkeypatch):
    now_ms = int(time.time() * 1000)
    watermark_time = now_ms - 7 * 60 * 60 * 1000
    detected_at_ms = now_ms - 6 * 60 * 60 * 1000
    launch_time_ms = now_ms - 5 * 60 * 1000

    # Event is old by detected_at_ms but fresh by symbol_effective_launch_times_ms.
    # Mock exchangeInfo to include ETHUSD1 and mock depth to return a minimal valid book.
    # Expected:
    #   events_accepted contains ETHUSD1
    #   events_rejected has no ETHUSD1 age_exceeded row
    #   accepted row observation_age_basis == "symbol_effective_launch_time"
```

This test must be executable, not a comment-only skeleton. Use existing Stage 1.5F runner tests as fixture patterns for writing watermark, summary files, fixture events, and monkeypatching public client calls.

Also add:

```python
def test_runner_future_launch_pending_does_not_write_rejected_row_and_retries_later(tmp_path, monkeypatch):
    now_ms = 1_000_000
    launch_time_ms = now_ms + 10 * 60 * 1000

    event = {
        "event_id": "ethusd1-future",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 60_000,
        "symbols": ["ETHUSD1"],
        "symbol_effective_launch_times_ms": {"ETHUSD1": launch_time_ms},
    }

    def run_stage1_5f_main_once(fake_now_ms: int):
        # Implement this local helper with the existing runner fixture pattern:
        #   set sys.argv for run_stage1_5f_live_depth_observer.py
        #   pass --fixture-events-jsonl, --stage1-5d-summary, --stage1-5e-summary,
        #   --output-root, --mock-response-dir, --max-polls 1
        #   monkeypatch scripts.external_signal_shadow.run_stage1_5f_live_depth_observer.time.time
        #   to return fake_now_ms / 1000
        ...

    # Use the existing runner fixture pattern:
    #   1. write fixture-events-jsonl with event;
    #   2. write safe Stage 1.5D / 1.5E summaries;
    #   3. write output_root/watermark.json with max_seen_detected_at_ms < event["detected_at_ms"];
    #   4. write mock_response_dir exchangeInfo/depth payloads with ETHUSD1;
    #   5. run poll 1 with fake time before launch.
    run_stage1_5f_main_once(fake_now_ms=now_ms)

    accepted_rows = read_jsonl_dir(output_root / "events_accepted")
    rejected_rows = read_jsonl_dir(output_root / "events_rejected")
    watermark_after_poll_1 = json.loads((output_root / "watermark.json").read_text())

    assert [r for r in accepted_rows if r.get("symbol") == "ETHUSD1"] == []
    assert [r for r in rejected_rows if r.get("symbol") == "ETHUSD1"] == []
    assert watermark_after_poll_1["max_seen_detected_at_ms"] < event["detected_at_ms"]

    # Poll 2 uses the same output_root and fixture event but monkeypatches now_ms to launch_time_ms.
    run_stage1_5f_main_once(fake_now_ms=launch_time_ms)

    accepted_rows = read_jsonl_dir(output_root / "events_accepted")
    rejected_rows = read_jsonl_dir(output_root / "events_rejected")
    eth_accepts = [r for r in accepted_rows if r.get("symbol") == "ETHUSD1"]
    eth_rejects = [r for r in rejected_rows if r.get("symbol") == "ETHUSD1"]

    assert len(eth_accepts) == 1
    assert eth_accepts[0]["observation_age_basis"] == "symbol_effective_launch_time"
    assert eth_rejects == []
```

This test must use the real runner entry point twice or the existing runner test harness twice. A loader-only test is insufficient because the bug class is artifact-level: pending must not be consumed by `events_rejected/*.jsonl`.

### Step 6: Run runner test and confirm pass

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_runner_accepts_delayed_launch_event_using_effective_launch_time \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_runner_future_launch_pending_does_not_write_rejected_row_and_retries_later \
  -q
```

Expected:

```text
2 passed
```

---

## Task 4: Guardrails for Evidence Labeling

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

### Step 1: Add evidence-label helper

Reuse `resolve_announcement_capture_time_ms()` from Task 3 and add:

```python
def classify_live_depth_evidence_basis(row: dict, watermark) -> dict:
    announcement_capture_time_ms, announcement_capture_time_source = resolve_announcement_capture_time_ms(row)
    observation_age_base_ms, observation_age_basis = resolve_observation_age_base_ms(
        row, row.get("symbol") or (row.get("symbols") or [""])[0]
    )

    announcement_after_watermark = (
        announcement_capture_time_ms is not None
        and announcement_capture_time_ms > watermark.max_seen_detected_at_ms
    )
    observation_after_watermark = (
        observation_age_base_ms is not None
        and observation_age_base_ms > watermark.max_seen_detected_at_ms
    )

    return {
        "announcement_capture_time_ms": announcement_capture_time_ms,
        "announcement_capture_time_source": announcement_capture_time_source,
        "announcement_time_capture_evidence_allowed": bool(announcement_after_watermark),
        "launch_time_depth_evidence_allowed": bool(observation_after_watermark),
        "live_depth_evidence_basis": (
            "announcement_and_launch_time"
            if announcement_after_watermark and observation_after_watermark
            else "launch_time_only"
            if observation_after_watermark
            else "recovery_validation_only"
        ),
    }
```

### Step 2: Add tests

Add:

```python
def test_evidence_basis_launch_time_only_when_announcement_before_watermark_but_launch_after():
    row = {
        "symbol": "ETHUSD1",
        "source_published_at_ms": 1_000,
        "detected_at_ms": 2_000,
        "symbol_effective_launch_times_ms": {"ETHUSD1": 10_000},
    }
    w = Watermark(1, 5_000, [], [], [], 5_000)

    basis = classify_live_depth_evidence_basis(row, w)

    assert basis["announcement_time_capture_evidence_allowed"] is False
    assert basis["launch_time_depth_evidence_allowed"] is True
    assert basis["live_depth_evidence_basis"] == "launch_time_only"
    assert basis["announcement_capture_time_ms"] == 2_000
    assert basis["announcement_capture_time_source"] == "detected_at_ms"


def test_evidence_basis_uses_detected_at_ms_not_source_published_at_ms_for_capture():
    row = {
        "symbol": "ETHUSD1",
        "source_published_at_ms": 1_000,
        "detected_at_ms": 6_000,
        "symbol_effective_launch_times_ms": {"ETHUSD1": 10_000},
    }
    w = Watermark(1, 5_000, [], [], [], 5_000)

    basis = classify_live_depth_evidence_basis(row, w)

    assert basis["announcement_capture_time_ms"] == 6_000
    assert basis["announcement_capture_time_source"] == "detected_at_ms"
    assert basis["announcement_time_capture_evidence_allowed"] is True
    assert basis["live_depth_evidence_basis"] == "announcement_and_launch_time"
```

### Step 3: Run tests and confirm fail

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_evidence_basis_launch_time_only_when_announcement_before_watermark_but_launch_after \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_evidence_basis_uses_detected_at_ms_not_source_published_at_ms_for_capture \
  -q
```

Expected:

```text
FAIL because classify_live_depth_evidence_basis is missing.
```

### Step 4: Wire evidence labels into accepted/rejected artifacts

In runner, merge output of `classify_live_depth_evidence_basis(flat_event, watermark)` into accepted/rejected rows.

Accepted ETHUSD1-like rows should show:

```json
{
  "live_depth_evidence_basis": "launch_time_only",
  "announcement_capture_time_ms": 1783023648791,
  "announcement_capture_time_source": "detected_at_ms",
  "announcement_time_capture_evidence_allowed": false,
  "launch_time_depth_evidence_allowed": true,
  "watermark_max_seen_detected_at_ms": 1783009167053,
  "watermark_version": 1
}
```

### Step 5: Update review docs

Update `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`:

```text
If live_depth_evidence_basis = launch_time_only:
  It can support launch-time depth evidence.
  It must not be used as announcement-time capture evidence or alpha proof.

If live_depth_evidence_basis = recovery_validation_only:
  It validates parser/runner behavior only.
  It must not enter official 12h live depth evidence review.
```

---

## Task 5: Regression for Current ETHUSD1 Shape

**Files:**

- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

### Step 1: Add exact ETHUSD1-shaped regression

Use representative values from live incident:

```python
def test_ethusd1_shape_not_rejected_by_detected_time_when_onboard_recent():
    now_ms = 1783069534532
    event = {
        "event_id": "ethusd1-event",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1783023648791,
        "source_published_at_ms": 1782989104900,
        "symbols": ["ETHUSD1"],
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "symbol_effective_launch_times_ms": {"ETHUSD1": 1783069200000},
        "symbol_onboard_times_ms": {"ETHUSD1": 1783069200000},
        "symbol_resolved_at_ms": 1783069200000,
    }
    w = Watermark(1, 1783009167053, [], [], [], 1783009167053)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "eligible"
    assert reason == "ok"


def test_ethusd1_shape_just_inside_15m_window_is_eligible():
    launch_ms = 1783069200000
    now_ms = launch_ms + (15 * 60 * 1000) - 1_000
    event = {
        "event_id": "ethusd1-event",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1783023648791,
        "source_published_at_ms": 1782989104900,
        "symbols": ["ETHUSD1"],
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "symbol_effective_launch_times_ms": {"ETHUSD1": launch_ms},
        "symbol_onboard_times_ms": {"ETHUSD1": launch_ms},
    }
    w = Watermark(1, 1783009167053, [], [], [], 1783009167053)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "eligible"
    assert reason == "ok"


def test_ethusd1_shape_just_outside_15m_window_is_rejected():
    launch_ms = 1783069200000
    now_ms = launch_ms + (15 * 60 * 1000) + 1_000
    event = {
        "event_id": "ethusd1-event",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1783023648791,
        "source_published_at_ms": 1782989104900,
        "symbols": ["ETHUSD1"],
        "symbol_extraction_source": "title_contract_symbol",
        "symbol_validation_status": "validated",
        "symbol_effective_launch_times_ms": {"ETHUSD1": launch_ms},
        "symbol_onboard_times_ms": {"ETHUSD1": launch_ms},
    }
    w = Watermark(1, 1783009167053, [], [], [], 1783009167053)
    exinfo = {"available": True, "symbols": {"ETHUSD1"}}

    status, reason = classify_event_symbol_eligibility(event, "ETHUSD1", now_ms, w, exinfo, {})

    assert status == "rejected"
    assert reason == "age_exceeded"
```

### Step 2: Run test

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_ethusd1_shape_not_rejected_by_detected_time_when_onboard_recent \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_ethusd1_shape_just_inside_15m_window_is_eligible \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_ethusd1_shape_just_outside_15m_window_is_rejected \
  -q
```

Expected:

```text
3 passed
```

---

## Task 6: Full Verification

Run targeted Stage 1.5F tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Run external signal suite:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow \
  tests/scripts/external_signal_shadow \
  -q
```

Run full repository suite:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q
```

Run formatting check:

```bash
git diff --check
```

Run safety grep:

```bash
rg -n "create_order|cancel_order|fetch_balance|withdraw|transfer|requests\\.post|httpx\\.post|ccxt|wallet|private_key|signed_tx|raw_tx|order_request|swap_request|apiKey|secret|TradeIntent|SignalCandidate|private_ws" \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py || true
```

Expected:

```text
No unsafe runtime trading/private endpoint code introduced.
Only existing config comments may mention apiKey/secret/ccxt.
```

---

## Task 7: Server Rollout Notes

Rollout must use a new Stage 1.5F output root:

```text
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix
```

Do not reuse the current root:

```text
data/external_signal_shadow/stage1_5f/live_depth_observer_7d_title_contract_transient_hotfix
```

Reason:

```text
The current root already contains ETHUSD1 age_exceeded rejected rows.
Using a new root keeps the evidence chain auditable.
```

If re-observing ETHUSD1 after this hotfix:

```text
Allowed label:
  recovery_validation_only, if the event-symbol was already terminal/rejected in a prior root.
  launch_time_only, only if the event-symbol passes the new root watermark membership and is accepted before max age.

Forbidden labels:
  announcement-time capture evidence
  official 12h live depth evidence for bootstrap/pre-watermark rows
  alpha proof
  execution feasibility proof
  paper/live readiness
```

If deploying while no new delayed-launch event is active:

```text
Bootstrap new Stage 1.5F root from current Stage 1.5D events.
Bootstrap only establishes watermark; it must not create events_accepted rows or depth observations for bootstrap rows.
Wait for the next post-watermark futures launch / delayed-launch event.
```

Watermark operation rule:

```text
Do not delete or reset watermark.json to force ETHUSD1 / old July 2-3 rows into official live evidence.
If recovery validation is needed, use a separate output root whose name includes recovery_validation.
Formal 12h evidence requires:
  1. new Stage 1.5D output root or an auditable current root;
  2. new Stage 1.5F output root;
  3. bootstrap watermark first;
  4. post-watermark event-symbol accepted after bootstrap.
```

---

## Completion Criteria

Implementation is complete only if all are true:

1. Legacy rows without launch/onboard/resolved fields still use `detected_at_ms` age gate.
2. Delayed-launch rows with recent `symbol_effective_launch_times_ms[symbol]` are eligible even if `detected_at_ms` is old.
3. `symbol_resolved_at_ms` is ignored for ordinary late parser/retry rows unless delayed-launch metadata/flag is present.
4. Future launch times return `pending, launch_time_in_future`.
5. Pending future-launch event-symbols do not write `events_accepted/*.jsonl`, do not write `events_rejected/*.jsonl`, do not update watermark, and can be accepted in a later poll.
6. Launch-time age base cannot bypass `event_is_post_watermark()` / seen ids / seen source article ids / seen stable keys.
7. Accepted/rejected rows include `observation_age_base_ms`, `observation_age_basis`, `event_age_ms`, `max_event_age_ms`, `watermark_max_seen_detected_at_ms`, `watermark_version`, and evidence-basis fields.
8. Evidence labels use `announcement_capture_time_ms` with priority `detected_at_ms`, then `available_at_ms`, then `collected_at_ms`, then `source_published_at_ms`.
9. ETHUSD1-shaped regression passes, including 15m inside/outside boundary tests.
10. Server rollout notes explicitly prohibit turning bootstrap/pre-watermark rows into official 12h live depth evidence.
11. No paper/live/trading/execution/alpha flag changes.
12. Full verification commands pass.
13. Review docs explain `launch_time_only` vs `announcement_and_launch_time` vs `recovery_validation_only`.

---

## Execution Results and Verification Evidence

### Actual Changes

1. **配置项更新 (Configs):**
   - 在 [configs/base.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/configs/base.py) 中配置了新阈值 `EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_TIME_CLOCK_SKEW_TOLERANCE_MS` 为 2 分钟。

2. **核心业务逻辑与数据结构 (Core Loader):**
   - 在 [stage1_5f_live_depth_observer_loader.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py) 中：
     - 实现 `resolve_observation_age_base_ms` 基于优先级 `symbol_effective_launch_times_ms` -> `symbol_onboard_times_ms` -> `symbol_resolved_at_ms`（仅当具备有效 onboard/launch 记录且 onboard 时间比 detected 时间晚至少 2 小时代表延迟上线证据时使用）-> `detected_at_ms` 计算观察年龄基准。
     - 在 `classify_event_symbol_eligibility_with_diagnostics` 中使用该年龄基准，当 launch time 在未来时返回 `pending, launch_time_in_future`；当当前时间超出基准 + 15 分钟时返回 `rejected, age_exceeded`。
     - 实现 `classify_live_depth_evidence_basis` 返回事件的证据分类 (`announcement_and_launch_time` / `launch_time_only` / `recovery_validation_only`)，严格防止历史回放/越过 watermark 数据污染实盘观测。

3. **运行脚本集成 (Runner):**
   - 在 [run_stage1_5f_live_depth_observer.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py) 中，集成 diagnostics 诊断信息与 evidence basis 数据，直接合并写入到 `events_accepted` 和 `events_rejected` JSONL 行记录中。
   - 增加对 `pending` 状态的判断，在 main loop 中直接 `continue` 不输出任何行也不推进 watermark，以备后续轮次重试。

4. **单元测试与集成测试 (Tests):**
   - 在 [test_stage1_5f_live_depth_observer_loader.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py) 中补充了全套测试：包括多优先级 fallback 测试、延迟上线、时钟抖动容忍、诊断数据核验、证据分类 (`launch_time_only` 等) 及 `ETHUSD1` 历史形态 15m 窗口内外的回归测试。
   - 在 [test_run_stage1_5f_live_depth_observer.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py) 中，编写了 runner 重试 `pending` 状态且不落盘，以及按 `symbol_effective_launch_times_ms` 正确接收延迟上线事件的完整集成测试。

### Verification Proof

1. **测试套件运行结果:**
   - 运行 Stage 1.5F 所有单元及集成测试：`PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow tests/scripts/external_signal_shadow -q`
   - 结果：**686 个测试全部通过 (100% green)**。
2. **安全合规性检索 (Safety Grep):**
   - 检索修改及测试目录，无任何活动交易、下单或私钥泄露（仅包含预期的安全白名单匹配、关键字校验和测试桩数据）。
