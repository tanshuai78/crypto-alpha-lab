# Stage 1.5D Detail Retry Overdue Starvation Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. For every code task, use TDD: write the failing test, verify it fails, then implement the minimal fix.

**Goal:** Fix Stage 1.5D detail retry overdue starvation where a futures launch article with prior HTTP 202 / empty detail attempts has `next_detail_retry_at_ms <= now_ms` and expired endpoint-degraded window, but does not re-enter the retry queue and therefore never emits event rows for Stage 1.5F.

**Architecture:** Keep Stage 1.5D public-readonly collection, existing detail fallback URLs, and Stage 1.5F watermark semantics unchanged. Add explicit scheduler fairness for overdue attempted transient articles, add auditable overdue diagnostics to summary/state, and preserve Binance detail endpoint HTTP 202 as transient/pending rather than parser evidence. Do not hardcode any article or symbol.

**Tech Stack:** Python stdlib, `configs/base.py`, `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`, `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`, JSONL artifacts, pytest.

---

## 0. Safety Boundary

```text
scope = stage1_5d_detail_retry_overdue_starvation_hotfix
live_public_readonly_only = true
private_api_allowed = false
order_endpoint_allowed = false
api_key_allowed = false
stage1_5f_watermark_change_allowed = false
stage1_5f_age_gate_change_allowed = false
stage1_5g_decision_override_allowed = false
old_artifact_rewrite_allowed = false
manual_event_backfill_allowed = false
manual_symbol_injection_allowed = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

This hotfix must not turn the missed 2026-07-21 `f43403ef11974998bc0f46420826577a` event into formal Stage 1.5F evidence. That event is only valid as a missed-event regression case because the launch window has already passed.

---

## 1. Observed Failure To Preserve

Observed on the running server after SPCXUSD1 clean pass:

```text
source_article_id = f43403ef11974998bc0f46420826577a
title = Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)
first_detected_at_ms = 1784619996988
first_detected_utc = 2026-07-21T07:46:36.988Z
candidate_symbols = null
pending_reason = title_symbol_missing
detail_http_request_count = 2
detail_fetch_attempt_count = 2
detail_retry_cycle_count = 1
transient_detail_error_count = 1
defer_count = 1
next_detail_retry_at_ms = 1784620117651
next_detail_retry_utc = 2026-07-21T07:48:37.651Z
now_utc = 2026-07-22T03:32:30.293Z
next_retry_due = true
next_retry_overdue_ms ~= 71,032,642
endpoint_degraded_until_utc = 2026-07-21T16:46:47.839Z
degraded_expired = true
degraded_overdue_ms ~= 38,742,454
1.5D event rows for article = 0
1.5F accepted rows for article = 0
1.5F rejected rows for article = 0
```

Manual detail URL probe still returned HTTP 202 empty for all tested URL variants:

```text
/en/support/announcement/<article_id> -> 202 empty
/en/support/announcement/detail/<article_id> -> 202 empty
/zh-CN/support/announcement/detail/<article_id> -> 202 empty
```

Interpretation:

```text
external_condition = Binance detail endpoint remains unavailable for this article
internal_failure = overdue pending article is not continuously retried or visibly diagnosed
result = missed formal 1.5F evidence for 2026-07-21 Multiple TradFi launch
```

This observation does not prove that a successful retry would have recovered `f434` symbols, because all manual detail URL variants still returned HTTP 202 empty. It proves a narrower production failure: the scheduler did not provide bounded retry service or explicit defer diagnostics for an overdue pending article when the endpoint might later recover.

The hotfix must distinguish these cases:

```text
A. endpoint still returns 202 empty -> keep article pending/transient, retry at bounded cadence, expose overdue diagnostics
B. endpoint recovers -> extract symbols, validate against exchangeInfo, emit event rows
C. article exceeds max transient age -> terminal scheduler diagnostic as detail_unavailable_timeout, not Stage 1.5F-consumable parser evidence
```

---

## 2. Working Hypotheses To Verify

Do not assume a single root cause before tests. The plan must verify these hypotheses:

```text
H1: Attempted transient rows whose next_detail_retry_at_ms is overdue can be starved by higher-priority never-attempted backlog.
H2: Endpoint-degraded state can be expired in persisted state, but scheduler output lacks explicit overdue attempted diagnostics, making starvation silent.
H3: The runner does not expose per-poll selected attempt codes / overdue pending counts, so production cannot distinguish "still 202 but retried" from "not retried".
H4: Multiple TradFi rows with repeated HTTP 202 must remain pending/transient until timeout, not terminal parser failure.
```

A fix is only valid if it creates auditable behavior:

```text
if next_detail_retry_at_ms <= now_ms and endpoint_degraded expired:
  article must either receive a retry cycle in bounded time
  or summary must expose why it was deferred and how overdue it is
```

### 2.1 Required Review Fixes Absorbed

This plan revision incorporates the following mandatory constraints before implementation:

```text
1. Overdue attempted reserved slots must never consume the last first-attempt slot.
2. Overdue eligibility must use effective_retry_due_at_ms = max(next_retry_at_ms, last_retry_at_ms + min_interval).
3. attempted rows with missing/zero next_detail_retry_at_ms require diagnostics, not automatic oldest-overdue selection.
4. title_symbol_missing alone is not retry permission; retryability must come from explicit transient failure class / retryable flag.
5. Overdue logical retry cycles must still respect total detail HTTP request budget, including fallback URL requests.
6. Diagnostics must explain why overdue rows were not selected, not only count overdue rows.
7. detail_http_request_count is the attempted source of truth; detail_fetch_attempt_count fallback must be explicit legacy warning only.
8. detail_unavailable_timeout must not be emitted as a Stage 1.5F-consumable event row.
9. Overdue pending fields are gauges; selected/deferred/retry-cycle fields are cumulative counters.
10. Restart and bounded service tests are required because this failure depends on persisted scheduler state.
11. Safety grep must be production-code focused and not match plan/test safety declarations.
12. Deployment must use new *_7d_detail_retry_overdue_starvation_hotfix roots, not old fallback roots.
```

---

## 3. Files

Modify:

```text
configs/base.py
src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py
src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

Tests:

```text
tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py
tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py
tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py
tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
```

Do not modify:

```text
src/research/external_signal_shadow/stage1_5f_live_depth_observer_*.py
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py
```

Unless a test proves a downstream audit field is incorrectly interpreting Stage 1.5D scheduler diagnostics.

---

## 4. Task 1: Add Overdue Retry Config

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`

### Step 1: Write failing config test

Add:

```python
def test_stage1_5d_detail_overdue_retry_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_RETRY_BUDGET_PER_POLL == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_MIN_INTERVAL_SEC == 10 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_WARN_SEC == 30 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_HARD_WARN_SEC == 2 * 60 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_RETRY_BUDGET_PER_POLL > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL >= 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_HARD_WARN_SEC > base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_WARN_SEC
```

### Step 2: Run failing test

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py::test_stage1_5d_detail_overdue_retry_config_present \
  -q
```

Expected: FAIL because constants do not exist.

### Step 3: Add config constants

Add near Stage 1.5D detail scheduler config:

```python
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_RETRY_BUDGET_PER_POLL = 1
# Bounded fairness slot for already-attempted transient rows whose next_detail_retry_at_ms is overdue.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_MIN_INTERVAL_SEC = 10 * 60
# Minimum interval between retry cycles for an overdue attempted transient article.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL = 1
# The overdue attempted reserved slot must never consume the final first-attempt slot.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_WARN_SEC = 30 * 60
# Summary warning threshold for overdue pending detail retries.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_HARD_WARN_SEC = 2 * 60 * 60
# Summary hard warning threshold for severely overdue pending detail retries.
```

### Step 4: Re-run config test

Expected: PASS.

---

## 5. Task 2: Add Scheduler Tests For Overdue Attempted Rows

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`

### Step 1: Write failing scheduler test for degraded-expired overdue attempted row

Add:

```python
def test_overdue_attempted_transient_selected_after_endpoint_degraded_expires():
    now_ms = 10_000_000
    article = {
        "first_detected_at_ms": now_ms - 90 * 60 * 1000,
        "detail_http_request_count": 2,
        "detail_fetch_attempt_count": 2,
        "detail_retry_cycle_count": 1,
        "transient_detail_error_count": 1,
        "last_detail_failure_class": "http_202_empty",
        "detail_retryable": True,
        "last_retry_at_ms": now_ms - 80 * 60 * 1000,
        "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
        "defer_count": 1,
        "pending_reason": "title_symbol_missing",
    }

    selected = select_detail_retry_attempts(
        detail_retry_state={"f434": article},
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == ["f434"]
```

### Step 2: Write failing fairness test for never-attempted backlog

This test captures the likely production failure mode: an overdue attempted transient article must not be hidden forever behind never-attempted backlog.

```python
def test_overdue_attempted_transient_gets_bounded_slot_even_with_never_attempted_backlog():
    now_ms = 10_000_000
    state = {
        "fresh1": {
            "first_detected_at_ms": now_ms - 3 * 60 * 1000,
            "detail_http_request_count": 0,
            "detail_fetch_attempt_count": 0,
            "next_detail_retry_at_ms": 0,
        },
        "fresh2": {
            "first_detected_at_ms": now_ms - 4 * 60 * 1000,
            "detail_http_request_count": 0,
            "detail_fetch_attempt_count": 0,
            "next_detail_retry_at_ms": 0,
        },
        "fresh3": {
            "first_detected_at_ms": now_ms - 5 * 60 * 1000,
            "detail_http_request_count": 0,
            "detail_fetch_attempt_count": 0,
            "next_detail_retry_at_ms": 0,
        },
        "f434": {
            "first_detected_at_ms": now_ms - 90 * 60 * 1000,
            "detail_http_request_count": 2,
            "detail_fetch_attempt_count": 2,
            "detail_retry_cycle_count": 1,
            "transient_detail_error_count": 1,
            "last_detail_failure_class": "http_202_empty",
            "detail_retryable": True,
            "last_retry_at_ms": now_ms - 80 * 60 * 1000,
            "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            "defer_count": 1,
            "pending_reason": "title_symbol_missing",
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert "f434" in selected
    assert len(selected) <= 3
    assert len(selected) == len(set(selected))
```

### Step 2.1: Write budget invariant tests

The overdue slot is reserved inside `detail_budget_per_poll`; it is not additive.

```python
def test_overdue_slot_is_within_total_budget_not_additive():
    now_ms = 10_000_000
    state = {
        f"fresh{i}": {
            "first_detected_at_ms": now_ms - i * 60_000,
            "detail_http_request_count": 0,
            "detail_fetch_attempt_count": 0,
            "next_detail_retry_at_ms": 0,
        }
        for i in range(1, 5)
    }
    state["f434"] = {
        "first_detected_at_ms": now_ms - 90 * 60 * 1000,
        "detail_http_request_count": 2,
        "detail_fetch_attempt_count": 2,
        "detail_retry_cycle_count": 1,
        "transient_detail_error_count": 1,
        "last_detail_failure_class": "http_202_empty",
        "detail_retryable": True,
        "last_retry_at_ms": now_ms - 80 * 60 * 1000,
        "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert len(selected) <= 3


def test_overdue_reserved_slot_never_consumes_last_first_attempt_slot():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "fresh": {
                "first_detected_at_ms": now_ms - 60_000,
                "detail_http_request_count": 0,
                "detail_fetch_attempt_count": 0,
                "next_detail_retry_at_ms": 0,
            },
            "f434": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            },
        },
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == ["fresh"]
```

For `detail_budget_per_poll == 1`, the design intentionally protects first attempts and relies on cross-poll rotation for overdue attempted rows. It must not claim both categories can be serviced in every poll with a single slot.

### Step 2.2: Write eligibility edge-case tests

```python
def test_overdue_attempted_respects_minimum_retry_interval():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "f434": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 5 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == []


def test_attempted_state_with_missing_next_retry_is_diagnosed_not_selected():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "bad": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": 0,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == []


def test_title_symbol_missing_alone_does_not_make_hard_failure_retryable():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "hard": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "pending_reason": "title_symbol_missing",
                "last_detail_failure_class": "http_404",
                "detail_retryable": False,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == []


def test_http_202_empty_attempted_row_is_retryable():
    now_ms = 10_000_000
    selected = select_detail_retry_attempts(
        detail_retry_state={
            "f434": {
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            }
        },
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms - 10 * 60 * 1000,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
        min_never_attempted_slots_per_poll=1,
    )

    assert selected == ["f434"]
```

### Step 3: Write failing test for active degraded state

Overdue attempted retry during active degraded state is allowed only through bounded degraded-recent policy already present. This hotfix must not disable degraded circuit breaker globally.

```python
def test_overdue_attempted_transient_not_selected_when_degraded_active_and_not_recent_allowed():
    now_ms = 10_000_000
    article = {
        "first_detected_at_ms": now_ms - 10 * 60 * 60 * 1000,
        "detail_http_request_count": 2,
        "detail_fetch_attempt_count": 2,
        "detail_retry_cycle_count": 10,
        "transient_detail_error_count": 8,
        "last_retry_at_ms": now_ms - 4 * 60 * 60 * 1000,
        "next_detail_retry_at_ms": now_ms - 3 * 60 * 60 * 1000,
    }

    selected = select_detail_retry_attempts(
        detail_retry_state={"old": article},
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms + 10 * 60 * 1000,
        degraded_recent_article_window_ms=3 * 60 * 60 * 1000,
        degraded_recent_retry_interval_ms=10 * 60 * 1000,
        degraded_recent_retry_budget_per_poll=1,
        degraded_recent_retry_max_cycles=6,
        overdue_attempted_retry_budget_per_poll=1,
        overdue_attempted_min_interval_ms=10 * 60 * 1000,
    )

    assert selected == []
```

### Step 4: Run failing tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  -q
```

Expected: at least the new tests fail before implementation.

### Step 5: Implement minimal scheduler change

Extend `select_detail_retry_attempts` signature with keyword-only optional args:

```python
overdue_attempted_retry_budget_per_poll: int = 0,
overdue_attempted_min_interval_ms: int | None = None,
min_never_attempted_slots_per_poll: int = 1,
```

Implementation approach:

```text
1. Keep existing never_attempted priority for first attempts.
2. Build attempted_due rows where:
   - detail_http_request_count > 0
   - terminal_state is false
   - detail_retryable is true
   - last_detail_failure_class in {"http_202_empty", "http_200_empty_untrusted_payload"}
   - next_detail_retry_at_ms > 0
   - effective_retry_due_at_ms = max(next_detail_retry_at_ms, last_retry_at_ms + overdue_attempted_min_interval_ms)
   - effective_retry_due_at_ms <= now_ms
   - terminal_state is false
3. When endpoint_degraded is not active, reserve overdue slots inside detail_budget_per_poll:
   overdue_slots = min(
       overdue_attempted_retry_budget_per_poll,
       max(0, detail_budget_per_poll - min_never_attempted_slots_per_poll),
   )
4. Select oldest/most-overdue attempted_due rows into reserved slots.
5. Fill remaining slots with existing never_attempted and attempted ordering.
6. Do not reserve this slot when endpoint_degraded is active; active degraded must still use degraded_recent_* policy only.
7. Deduplicate selected codes while preserving order.
8. Missing next_detail_retry_at_ms must be diagnosed as missing_next_retry_at, not selected as oldest overdue.
```

Sorting for overdue attempted rows:

```python
key = (
    int(state.get("next_detail_retry_at_ms") or 0),
    int(state.get("last_retry_at_ms") or 0),
    -int(state.get("transient_detail_error_count") or 0),
    int(state.get("first_detected_at_ms") or 0),
    code,
)
```

### Step 6: Re-run scheduler tests

Expected: PASS.

---

## 6. Task 3: Add Overdue Diagnostics Helper

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Modify test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

### Step 1: Write failing helper test

Add a helper named `summarize_detail_retry_overdue_state`.

```python
def test_summarize_detail_retry_overdue_state_reports_attempted_overdue_rows():
    now_ms = 10_000_000
    result = summarize_detail_retry_overdue_state(
        {
            "f434": {
                "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "transient_detail_error_count": 1,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "terminal_state": False,
            },
            "future": {
                "detail_http_request_count": 1,
                "next_detail_retry_at_ms": now_ms + 10_000,
                "terminal_state": False,
            },
        },
        now_ms=now_ms,
        warn_ms=30 * 60 * 1000,
        hard_warn_ms=2 * 60 * 60 * 1000,
    )

    assert result["detail_retry_overdue_pending_count"] == 1
    assert result["detail_retry_overdue_attempted_count"] == 1
    assert result["detail_retry_oldest_overdue_ms"] == 70 * 60 * 1000
    assert result["detail_retry_overdue_warn_active"] is True
    assert result["detail_retry_overdue_hard_warn_active"] is False
    assert result["detail_retry_overdue_articles"][0]["source_article_id"] == "f434"
```

Add edge-case tests:

```python
def test_summarize_overdue_skips_attempted_row_with_zero_next_retry():
    now_ms = 10_000_000
    result = summarize_detail_retry_overdue_state(
        {
            "attempted_missing_next": {
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "next_detail_retry_at_ms": 0,
                "terminal_state": False,
            }
        },
        now_ms=now_ms,
        warn_ms=30 * 60 * 1000,
        hard_warn_ms=2 * 60 * 60 * 1000,
    )

    assert result["detail_retry_overdue_attempted_count"] == 0
    assert result["detail_retry_due_timestamp_missing_count"] == 1


def test_overdue_diagnostics_do_not_hide_http_attempt_counter_mismatch():
    now_ms = 10_000_000
    result = summarize_detail_retry_overdue_state(
        {
            "legacy_mismatch": {
                "detail_http_request_count": 0,
                "detail_fetch_attempt_count": 2,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
                "terminal_state": False,
            }
        },
        now_ms=now_ms,
        warn_ms=30 * 60 * 1000,
        hard_warn_ms=2 * 60 * 60 * 1000,
    )

    assert result["detail_retry_overdue_attempted_count"] == 0
    assert result["detail_attempt_manifest_mismatch_count"] == 1
    assert result["legacy_attempt_count_fallback_used"] is False
```

### Step 2: Run failing test

Expected: FAIL because helper does not exist.

### Step 3: Implement helper

Add:

```python
def summarize_detail_retry_overdue_state(
    detail_retry_state: dict[str, dict],
    *,
    now_ms: int,
    warn_ms: int,
    hard_warn_ms: int,
    max_articles: int = 10,
) -> dict:
    overdue = []
    due_timestamp_missing_count = 0
    attempt_manifest_mismatch_count = 0
    for code, state in detail_retry_state.items():
        if state.get("terminal_state"):
            continue
        next_retry = int(state.get("next_detail_retry_at_ms") or 0)
        http_count = int(state.get("detail_http_request_count") or 0)
        fetch_count = int(state.get("detail_fetch_attempt_count") or 0)
        if next_retry <= 0:
            if http_count > 0:
                due_timestamp_missing_count += 1
            if http_count == 0 and fetch_count > 0:
                attempt_manifest_mismatch_count += 1
            continue
        if now_ms < next_retry:
            continue
        overdue_ms = now_ms - next_retry
        attempt_manifest_mismatch = http_count == 0 and fetch_count > 0
        row = {
            "source_article_id": code,
            "title": state.get("title"),
            "overdue_ms": overdue_ms,
            "attempted": http_count > 0,
            "detail_http_request_count": http_count,
            "detail_fetch_attempt_count": fetch_count,
            "detail_attempt_manifest_mismatch": attempt_manifest_mismatch,
            "transient_detail_error_count": int(state.get("transient_detail_error_count") or 0),
            "next_detail_retry_at_ms": next_retry,
            "pending_reason": state.get("pending_reason"),
            "candidate_symbols": state.get("candidate_symbols"),
        }
        overdue.append(row)

    overdue.sort(key=lambda r: (-r["overdue_ms"], r["source_article_id"]))
    oldest = overdue[0]["overdue_ms"] if overdue else 0
    return {
        "detail_retry_overdue_pending_count": len(overdue),
        "detail_retry_overdue_attempted_count": sum(1 for r in overdue if r["attempted"]),
        "detail_retry_overdue_never_attempted_count": sum(1 for r in overdue if not r["attempted"]),
        "detail_retry_due_timestamp_missing_count": due_timestamp_missing_count,
        "detail_attempt_manifest_mismatch_count": attempt_manifest_mismatch_count + sum(1 for r in overdue if r["detail_attempt_manifest_mismatch"]),
        "legacy_attempt_count_fallback_used": False,
        "detail_retry_oldest_overdue_ms": oldest,
        "detail_retry_overdue_warn_active": oldest >= warn_ms if oldest else False,
        "detail_retry_overdue_hard_warn_active": oldest >= hard_warn_ms if oldest else False,
        "detail_retry_overdue_articles": overdue[:max_articles],
    }
```

### Step 4: Re-run scheduler helper tests

Expected: PASS.

---

## 7. Task 4: Wire Scheduler Config And Overdue Diagnostics Into Runner

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

### Step 0: Inspect existing runner test fixture pattern

Before writing tests, inspect current assertions and fixture helpers:

```bash
grep -n "request_manifest\|detail_retry_scheduler_state\|fixture_json\|output_root" \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py | head -n 120
```

Use the existing pattern for reading request manifest JSONL rows. If no helper exists for initial scheduler state, write `detail_retry_scheduler_state.json` directly into the temp output root before invoking the runner.

### Step 1: Write failing runner test for bounded overdue retry selection

Minimum assertion set:

```python
def test_overdue_attempted_detail_retry_gets_bounded_retry_slot(tmp_path):
    # Arrange: output_root contains persisted f434-like scheduler state.
    # - f434 detail_http_request_count=2
    # - transient_detail_error_count=1
    # - last_detail_failure_class="http_202_empty"
    # - detail_retryable=True
    # - next_detail_retry_at_ms is overdue
    # - endpoint degraded_until is expired
    # - catalog contains enough never-attempted no-symbol rows to consume old budget

    # Act: run one Stage 1.5D poll with fixture detail response still HTTP 202 empty.

    manifest_rows = load_request_manifest_rows(output_root)
    article_rows = [r for r in manifest_rows if r.get("source_article_id") == "f43403ef11974998bc0f46420826577a"]
    assert any(r.get("request_type") == "announcement_detail" for r in article_rows)
    assert any(r.get("http_status") == 202 for r in article_rows)
    assert len(selected_codes_from_scheduler_diagnostics(output_root)) <= base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL

    state = load_scheduler_state(output_root)["articles"]["f43403ef11974998bc0f46420826577a"]
    assert state["detail_retry_cycle_count"] >= 2
    assert state["detail_http_request_count"] >= 3
    assert state["terminal_failure_type"] is None
```

Also add:

```python
def test_overdue_retry_cycle_respects_total_detail_http_request_budget(tmp_path):
    # Arrange one overdue article whose retry cycle can attempt primary + fallback URLs.
    # Set EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL = 1 via monkeypatch.
    # Assert actual announcement_detail manifest rows written in the poll <= 1.
```

```python
def test_overdue_fallback_requests_each_increment_http_request_count_and_manifest_rows(tmp_path):
    # Arrange HTTP budget >= 2 and one overdue article with primary + fallback transient responses.
    # Assert detail_http_request_count increases by number of actual manifest announcement_detail rows.
    # Assert detail_retry_cycle_count increases by exactly 1.
```

### Step 2: Add scheduler selected/deferred diagnostics

The runner must emit auditable per-poll bounded diagnostics, preferably as capped JSONL rows in request manifest or a dedicated scheduler diagnostics JSONL. Required fields:

```text
request_type = detail_retry_scheduler_diagnostic
selected_overdue_article_ids = capped list
deferred_overdue_reason_counts = dict
logical_retry_budget = detail_budget_per_poll
http_request_budget = detail_http_requests_remaining at poll start
endpoint_degraded_active = bool
```

Required defer reasons:

```text
endpoint_degraded_active
minimum_interval_not_elapsed
http_request_budget_exhausted
logical_retry_budget_exhausted
never_attempted_slot_protection
state_not_retryable
missing_next_retry_at
```

Add tests:

```python
def test_active_degraded_overdue_row_reports_endpoint_degraded_defer_reason(tmp_path): ...

def test_selected_overdue_row_is_auditable_in_scheduler_diagnostics(tmp_path): ...
```

### Step 3: Wire new scheduler args

In the `select_detail_retry_attempts(...)` call, pass:

```python
overdue_attempted_retry_budget_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_RETRY_BUDGET_PER_POLL,
overdue_attempted_min_interval_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_MIN_INTERVAL_SEC * 1000,
min_never_attempted_slots_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL,
```

When `classify_detail_attempt_result(...)` returns transient classes, persist explicit retry fields on state:

```python
state["last_detail_failure_class"] = attempt_result
state["detail_retryable"] = attempt_result in {"http_202_empty", "http_200_empty_untrusted_payload"}
```

Do not use `pending_reason == title_symbol_missing` as retry permission.

### Step 4: Ensure HTTP budget is still authoritative

A selected overdue logical retry cycle may attempt multiple URL variants. Each actual HTTP request must decrement `detail_http_requests_remaining`, append one `announcement_detail` manifest row, and increment `detail_http_request_count`. No selected overdue slot may bypass `EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL`.

### Step 5: Re-run runner tests

Expected: PASS.

---

## 8. Task 5: Add Summary Fields As Gauges And Counters

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py`

### Step 1: Write failing summary tests

Add gauge test:

```python
def test_overdue_pending_summary_is_current_gauge_not_cumulative_counter():
    summary1 = build_stage1_5d_summary(..., counters={"detail_retry_overdue_pending_count": 1})
    summary2 = build_stage1_5d_summary(..., counters={"detail_retry_overdue_pending_count": 1})
    assert summary1["detail_retry_overdue_pending_count"] == 1
    assert summary2["detail_retry_overdue_pending_count"] == 1
```

Add fields test:

```python
def test_summary_includes_detail_retry_overdue_diagnostics():
    summary = build_stage1_5d_summary(
        ...,
        counters={
            "detail_retry_overdue_pending_count": 1,
            "detail_retry_overdue_attempted_count": 1,
            "detail_retry_overdue_never_attempted_count": 0,
            "detail_retry_due_timestamp_missing_count": 0,
            "detail_attempt_manifest_mismatch_count": 0,
            "detail_retry_oldest_overdue_ms": 70 * 60 * 1000,
            "detail_retry_overdue_warn_active": True,
            "detail_retry_overdue_hard_warn_active": False,
            "detail_retry_overdue_selected_total": 1,
            "detail_retry_overdue_deferred_total": 2,
            "detail_retry_overdue_retry_cycle_total": 1,
        },
    )
    assert summary["detail_retry_overdue_pending_count"] == 1
    assert summary["detail_retry_overdue_selected_total"] == 1
```

### Step 2: Add gauge fields

These fields must be recomputed from current scheduler state after mutation and then overwritten in summary; do not `+=` them per poll:

```text
detail_retry_overdue_pending_count
detail_retry_overdue_attempted_count
detail_retry_overdue_never_attempted_count
detail_retry_due_timestamp_missing_count
detail_attempt_manifest_mismatch_count
detail_retry_oldest_overdue_ms
detail_retry_overdue_warn_active
detail_retry_overdue_hard_warn_active
```

### Step 3: Add cumulative counter fields

These may accumulate per process/root:

```text
detail_retry_overdue_selected_total
detail_retry_overdue_deferred_total
detail_retry_overdue_retry_cycle_total
```

Expected: summary tests pass.

---

## 9. Task 6: Regression Test Multiple TradFi 202 Empty Does Not Terminal Fail Prematurely Or Emit Consumable Timeout Events

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify if needed: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`

### Step 0: Run guard test early

Run this guard before broad runner integration work to establish current behavior:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k "202_empty or transient_detail" \
  -q
```

### Step 1: Add pending-before-timeout test

Expected after a short run with f434-style article and HTTP 202 empty detail responses:

```text
article remains in detail_retry_scheduler_state.json
candidate_symbols is null
pending_reason = title_symbol_missing
transient_detail_error_count >= 1
terminal_failure_type is null
events/*.jsonl has no terminal parser failure row for this article
request_manifest has announcement_detail rows for this article
```

### Step 2: Add timeout diagnostic non-consumable test

If transient max age is exceeded:

```text
scheduler state or detail_retry_terminal_diagnostics.jsonl records detail_unavailable_timeout
detail_retry_terminal_diagnostics row has consumable_by_stage1_5f = false
normal events/*.jsonl does not receive symbols=[] consumable event row for this article
1.5F accepted/rejected cannot consume this terminal diagnostic as an event-symbol
```

Add explicit tests:

```python
def test_http_202_remains_pending_before_transient_max_age(tmp_path): ...

def test_detail_unavailable_timeout_does_not_emit_stage1_5f_consumable_event(tmp_path): ...
```

Reuse existing transient max-age config; do not hardcode timeout inside the runner.

---

## 10. Task 7: Restart And Bounded Service Regression Tests

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

Add restart test:

```python
def test_overdue_attempted_row_survives_restart_and_is_selected_after_degraded_expiry(tmp_path):
    # poll 1: persisted f434-like state, endpoint degraded active, article deferred
    # restart runner / reload persisted detail_retry_scheduler_state.json
    # poll 2: degraded_until expired, never-attempted backlog exists
    # assert f434 obtains overdue reserved slot and manifest retry row
```

Add bounded service test:

```python
def test_overdue_attempted_queue_has_bounded_round_robin_service():
    # N overdue attempted rows, overdue budget = 1, no active degraded.
    # Simulate N eligible polls with transient retry result preserved.
    # Assert every row is selected at least once within N eligible polls.
```

These tests prove starvation is removed rather than only proving one `f434` row can be selected once.

---

## 11. Task 8: Update Review / Ops Documentation

**Files:**
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

Add a subsection under the historical issue index or Stage 1.5D hotfix section:

```text
2026-07-21 f434 Multiple TradFi missed-event diagnostic:
  article list capture succeeded
  detail endpoint returned repeated 202 empty
  candidate_symbols remained null
  next_detail_retry overdue ~= 19.7h
  endpoint degraded window expired ~= 10.8h
  1.5D event not emitted
  1.5F accepted/rejected absent
  result = missed formal 1.5F evidence
  required action = Stage 1.5D detail retry overdue starvation hotfix
```

Add evidence boundary:

```text
This missed event must not be manually backfilled into formal Stage 1.5F evidence.
It may only be used as regression/recovery validation for the overdue starvation hotfix.
```

Add post-deploy checks for:

```text
exact article request_manifest rows
scheduler overdue diagnostics
summary overdue fields
1.5D events rows
1.5F accepted/rejected rows
new root suffix = _7d_detail_retry_overdue_starvation_hotfix
```

---

## 12. Task 9: Verification Commands

Run focused tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Run existing Stage 1.5D/1.5F/1.5G safety regression subset:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q
```

Production safety grep:

```bash
! grep -RInE 'paper_trading_allowed\s*[:=]\s*True|live_trading_allowed\s*[:=]\s*True|execution_engine_allowed\s*[:=]\s*True|trade_signal_allowed\s*[:=]\s*True' \
  configs src scripts
```

Private/order path grep, production code only:

```bash
! grep -RInE '\bplace_order\b|\bcreate_order\b|\border_endpoint\b|\border_intent\b|\bOrderIntent\b|apiKey|secret' \
  configs src scripts
```

Expected:

```text
all focused tests pass
existing Stage 1.5D/F/G regression subset passes
production safety grep has no violations
```

---

## 13. Deployment Notes After Implementation

After code is merged/deployed, do not reuse the missed f434 event as formal evidence. Start new Stage 1.5D / 1.5F roots with a new suffix:

```text
1.5D root suffix = _7d_detail_retry_overdue_starvation_hotfix
1.5F root suffix = _7d_detail_retry_overdue_starvation_hotfix
old fallback root remains read-only
SPCXUSD1 clean evidence root remains read-only
f434 remains regression-only / missed-event diagnostic
```

Post-deploy checks:

```text
1. New 1.5D root heartbeat grows.
2. New 1.5F root heartbeat grows.
3. Root suffix matches overdue hotfix.
4. detail_retry_overdue_pending_count is present in summary.
5. pending articles with next_detail_retry_at_ms <= now appear in manifest retries or explicit overdue diagnostics.
6. 1.5F continues using the new root and accepts only emitted event rows.
7. old root remains read-only.
```

Server check skeleton:

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export ARTICLE_ID="f43403ef11974998bc0f46420826577a"
export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_detail_retry_overdue_starvation_hotfix' | sort | tail -n 1)"

echo "$STAGE1_5D_EVENTS_OUT"
echo "$STAGE1_5F_OUT"

cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" | python -m json.tool | grep -E \
"detail_retry_overdue_pending_count|detail_retry_overdue_attempted_count|detail_retry_due_timestamp_missing_count|detail_attempt_manifest_mismatch_count|detail_retry_oldest_overdue_ms|detail_retry_overdue_warn_active|detail_retry_overdue_hard_warn_active|detail_retry_overdue_selected_total|detail_retry_overdue_deferred_total|detail_scheduler_pending_count|detail_scheduler_backoff_count|detail_degraded_recent_retry_count" || true

find "$STAGE1_5D_EVENTS_OUT/request_manifest" -type f 2>/dev/null \
  -exec grep -HIn "\"source_article_id\": \"$ARTICLE_ID\"" {} \; || true
```

---

## 14. Commit Guidance

Recommended commits:

```text
1. test: cover stage1 5d overdue detail retry starvation
2. fix: give overdue attempted detail retries bounded scheduler slot
3. feat: report stage1 5d detail retry overdue diagnostics
4. docs: record f434 missed event and overdue retry hotfix plan
```

Do not squash with unrelated Stage 1.5H or roadmap work.
