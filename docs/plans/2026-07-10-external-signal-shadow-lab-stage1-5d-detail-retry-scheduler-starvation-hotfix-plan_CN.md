# Stage 1.5D Detail Retry Scheduler Starvation Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. For every code task, write or extend tests before implementation.

**Goal:** Fix Stage 1.5D announcement detail retry starvation so new no-symbol futures launch articles receive a bounded first detail fetch attempt and old transient HTTP 202 detail rows cannot monopolize the per-poll budget.

**Architecture:** Extract retry scheduling decisions from the Stage 1.5D runner into a small auditable scheduler helper with first-attempt SLA, transient backoff, endpoint degraded state, and persisted scheduler metadata. Keep Stage 1.5D event semantics, Stage 1.5F watermark semantics, and all trading safety flags unchanged. Treat never-attempted budget starvation as a collection failure, not parser evidence.

**Tech Stack:** Python stdlib, JSONL artifacts, `configs/base.py`, pytest, existing Stage 1.5D/1.5F/1.5G review modules.

---

## 0. Execution Boundary

```text
scope = stage1_5d_detail_retry_scheduler_hotfix
live_public_readonly_only = true
private_api_allowed = false
order_endpoint_allowed = false
stage1_5f_watermark_change_allowed = false
stage1_5f_age_gate_change_allowed = false
old_artifact_rewrite_allowed = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

Do not repair this by hardcoding the 2026-07-09 article. The fix must generalize to future no-symbol `futures_contract_launch` announcements whose detail payload is needed to resolve symbols.

Do not reuse or modify old output roots for formal evidence. The 2026-07-09 missed event is only valid as regression / recovery-validation evidence.

---

## 1. Root Cause To Preserve In Tests

The observed failure was:

```text
source_article_id = 84ad610bdd284699bc451b7baaa0ff7d
title = Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-09)
detected_at_ms = 1783592168202
symbol_resolved_at_ms = 1783595804449
symbols = []
symbol_parse_status = terminal_failed
detail_fetch_attempted = False
detail_fetched_at_ms = None
detail_fetch_status = max_age_exceeded
symbol_parse_failed_reason = detail_retry_max_age_exceeded
request_manifest rows for this source_article_id = 0
```

The old loop processed `detail_retry_state.items()` in insertion order while `EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL = 3`. Three older articles repeatedly returned HTTP 202 / empty detail and consumed all detail budget. The new article never received a first detail request and then expired.

The regression tests must prove:

```text
1. A never-attempted eligible article cannot be expired as parser/symbol-empty evidence.
2. Old transient HTTP 202 articles enter backoff and cannot monopolize all future budget.
3. If detail budget is positive, every eligible never-attempted article receives first attempt within SLA.
4. Restart does not reset old transient articles into budget-stealing fresh state.
5. Restart can continue fetching a pending article even after it disappears from the current catalog list.
```

---

## 1.1 Plan Review Fixes Absorbed

The plan must incorporate these additional review constraints before implementation starts:

```text
1. Persisted scheduler state must include enough minimal article metadata to fetch detail and emit diagnostics without relying on the current catalog list.
2. EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_NEVER_ATTEMPTED_MAX_DEFER_SEC must drive explicit SLA breach classification before max-age terminal handling.
3. request_manifest is an audit trail; detail_retry_scheduler_state.json is the latest scheduler state source of truth.
4. endpoint_degraded must not block first attempts, but selected attempts must still be capped by EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL.
5. Stage 1.5G depth request health must only consider request_type == "depth_snapshot"; Stage 1.5D scheduler diagnostics must not affect depth request success rates.
6. Runner integration must preserve the existing raw article object and must not introduce undefined local variables such as ev.
7. serialize_retry_articles must normalize every persisted article to the full scheduler schema, including defer_count and minimal article metadata.
8. The old terminal_fail_type = None max-age branch for never-attempted rows must be replaced explicitly.
9. classify_stage1_5d_terminal_failure must be added explicitly if Stage 1.5G needs to interpret Stage 1.5D terminal rows.
```

These are valid requirements. They close restart, audit, and downstream review gaps in the first draft plan.

---

## 2. Files

Modify:

```text
configs/base.py
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
```

Create:

```text
src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py
tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py
```

Modify or extend tests:

```text
tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py
tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py
```

If exact Stage 1.5G test filenames differ locally, use the nearest existing `test_stage1_5g_live_depth_evidence_review_*.py` files and keep the same assertions.

---

## 3. Task 1: Add Config Constants

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`

### Step 1: Write failing config tests

Add tests that assert the constants exist and have safe relationships:

```python
def test_stage1_5d_detail_scheduler_fairness_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS == 10 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS > 0


def test_stage1_5d_detail_scheduler_backoff_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC == 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC == 3600
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC >= base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_NEVER_ATTEMPTED_MAX_DEFER_SEC == 10 * 60


def test_stage1_5d_detail_endpoint_degraded_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD == 0.80
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE == 5
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC == 15 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEFERRED_MANIFEST_MIN_INTERVAL_SEC == 15 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION == 1
```

### Step 2: Run the failing tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  -q
```

Expected: FAIL because the new constants are missing.

### Step 3: Add constants in `configs/base.py`

Add below the existing Stage 1.5D detail config block:

```python
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS = 3
# Eligible never-attempted announcement detail rows must receive a first attempt within this many polls.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS = 10 * 60 * 1000
# Wall-clock SLA for first detail fallback attempt on newly detected no-symbol futures articles.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC = 60
# Initial backoff for transient announcement detail failures such as HTTP 202 empty body.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC = 3600
# Maximum per-article transient detail retry backoff.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_NEVER_ATTEMPTED_MAX_DEFER_SEC = 10 * 60
# Maximum tolerated scheduler defer time before classifying never-attempted detail rows as collection failure.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD = 0.80
# Endpoint degradation threshold for recent HTTP 202 / empty detail responses.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE = 5
# Minimum recent detail attempts required before endpoint degraded state can activate.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC = 15 * 60
# Endpoint-level backoff for old transient detail retries when Binance detail endpoint is degraded.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEFERRED_MANIFEST_MIN_INTERVAL_SEC = 15 * 60
# Per-article minimum interval for compacted announcement_detail_deferred diagnostic rows.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION = 1
# Audit metadata version for Stage 1.5D detail retry scheduler diagnostics.
```

### Step 4: Re-run config tests

Expected: PASS.

---

## 4. Task 2: Create Scheduler Helper With Bounded Fair Selection

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Create/modify test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

### Step 1: Write scheduler selection tests first

Add tests for the core queue behavior:

```python
def test_never_attempted_article_is_selected_before_old_transient_backlog():
    now_ms = 1_000_000
    state = {
        "old1": {
            "source_article_id": "old1",
            "first_detected_at_ms": now_ms - 60_000,
            "detail_fetch_attempt_count": 7,
            "transient_detail_error_count": 7,
            "next_detail_retry_at_ms": now_ms,
            "last_retry_at_ms": now_ms - 60_000,
        },
        "old2": {
            "source_article_id": "old2",
            "first_detected_at_ms": now_ms - 60_000,
            "detail_fetch_attempt_count": 7,
            "transient_detail_error_count": 7,
            "next_detail_retry_at_ms": now_ms,
            "last_retry_at_ms": now_ms - 60_000,
        },
        "new": {
            "source_article_id": "new",
            "first_detected_at_ms": now_ms - 1_000,
            "detail_fetch_attempt_count": 0,
            "transient_detail_error_count": 0,
            "next_detail_retry_at_ms": 0,
            "defer_count": 0,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    )

    assert selected == ["new"]
```

Add SLA/aging test:

```python
def test_older_never_attempted_article_cannot_be_starved_by_continuous_new_articles():
    now_ms = 1_000_000
    state = {
        "older": {
            "source_article_id": "older",
            "first_detected_at_ms": now_ms - 9 * 60 * 1000,
            "detail_fetch_attempt_count": 0,
            "defer_count": 8,
            "next_detail_retry_at_ms": 0,
            "last_retry_at_ms": 0,
        },
        "newer": {
            "source_article_id": "newer",
            "first_detected_at_ms": now_ms - 10_000,
            "detail_fetch_attempt_count": 0,
            "defer_count": 0,
            "next_detail_retry_at_ms": 0,
            "last_retry_at_ms": 0,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    )

    assert selected == ["older"]
```

Add transient backoff test:

```python
def test_attempted_transient_article_not_selected_before_next_retry_time():
    now_ms = 1_000_000
    state = {
        "old": {
            "source_article_id": "old",
            "first_detected_at_ms": now_ms - 60_000,
            "detail_fetch_attempt_count": 2,
            "transient_detail_error_count": 2,
            "next_detail_retry_at_ms": now_ms + 30_000,
            "last_retry_at_ms": now_ms - 30_000,
        }
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    )

    assert selected == []
```

Add schema normalization test:

```python
def test_serialize_retry_articles_fills_required_schema_defaults():
    raw_state = {
        "old": {
            "source_article_id": "old",
            "title": "Binance Futures Will Launch XUSDT Perpetual Contract",
            "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/old",
            "source_published_at_ms": 1000,
            "detected_at_ms": 2000,
            "event_type": "futures_contract_launch",
            "detail_fetch_attempt_count": 3,
        }
    }

    serialized = serialize_retry_articles(raw_state)

    article = serialized["old"]
    assert article["source_article_id"] == "old"
    assert article["defer_count"] == 0
    assert article["transient_detail_error_count"] == 0
    assert article["next_detail_retry_at_ms"] == 0
    assert article["title"]
    assert article["source_detail_url_normalized"]
    assert article["event_type"] == "futures_contract_launch"
```

Add never-attempted defer classification tests:

```python
def test_never_attempted_defer_sla_breach_counter_increments_before_max_age():
    result = classify_never_attempted_defer_state(
        detail_fetch_attempt_count=0,
        first_detected_at_ms=0,
        now_ms=11 * 60 * 1000,
        never_attempted_max_defer_sec=10 * 60,
        detail_fetch_max_age_sec=3600,
    )

    assert result["classification"] == "detail_first_attempt_sla_breach"
    assert result["terminal_failure_type"] is None


def test_never_attempted_max_age_becomes_budget_starved_not_parser_failure():
    result = classify_never_attempted_defer_state(
        detail_fetch_attempt_count=0,
        first_detected_at_ms=0,
        now_ms=3601 * 1000,
        never_attempted_max_defer_sec=10 * 60,
        detail_fetch_max_age_sec=3600,
    )

    assert result["classification"] == "detail_never_attempted_budget_starved"
    assert result["terminal_failure_type"] == "detail_never_attempted_budget_starved"
    assert result["detail_fetch_status"] == "budget_starved"
```

### Step 2: Implement minimal helper

Implement dict-based helpers to avoid a large refactor:

```python
def compute_detail_transient_backoff_ms(
    transient_detail_error_count: int,
    *,
    base_sec: int,
    max_sec: int,
) -> int:
    exponent = max(0, min(transient_detail_error_count - 1, 5))
    return min(max_sec, base_sec * (2 ** exponent)) * 1000


def select_detail_retry_attempts(
    *,
    detail_retry_state: dict[str, dict],
    now_ms: int,
    detail_budget_per_poll: int,
    endpoint_degraded_until_ms: int,
) -> list[str]:
    if detail_budget_per_poll <= 0:
        return []

    never_attempted = []
    attempted = []
    for code, state in detail_retry_state.items():
        if state.get("terminal_state"):
            continue
        if now_ms < int(state.get("next_detail_retry_at_ms") or 0):
            continue
        if int(state.get("detail_fetch_attempt_count") or 0) <= 0:
            never_attempted.append((code, state))
        else:
            attempted.append((code, state))

    never_attempted.sort(
        key=lambda item: (
            -int(item[1].get("defer_count") or 0),
            int(item[1].get("first_detected_at_ms") or 0),
            item[0],
        )
    )

    if now_ms < endpoint_degraded_until_ms:
        attempted = []
    else:
        attempted.sort(
            key=lambda item: (
                int(item[1].get("last_retry_at_ms") or 0),
                int(item[1].get("transient_detail_error_count") or 0),
                int(item[1].get("first_detected_at_ms") or 0),
                item[0],
            )
        )

    ordered = never_attempted + attempted
    return [code for code, _ in ordered[:detail_budget_per_poll]]
```

Note: with default `base_sec=60` and exponent cap `5`, the effective maximum from the exponential backoff formula is 1920 seconds. `max_sec=3600` remains a hard cap for future config changes and must still be applied.

Also implement:

```python
def classify_never_attempted_defer_state(
    *,
    detail_fetch_attempt_count: int,
    first_detected_at_ms: int,
    now_ms: int,
    never_attempted_max_defer_sec: int,
    detail_fetch_max_age_sec: int,
) -> dict:
    if detail_fetch_attempt_count > 0:
        return {"classification": "attempted", "terminal_failure_type": None}
    age_ms = max(0, now_ms - first_detected_at_ms)
    if age_ms >= detail_fetch_max_age_sec * 1000:
        return {
            "classification": "detail_never_attempted_budget_starved",
            "terminal_failure_type": "detail_never_attempted_budget_starved",
            "detail_fetch_status": "budget_starved",
        }
    if age_ms >= never_attempted_max_defer_sec * 1000:
        return {
            "classification": "detail_first_attempt_sla_breach",
            "terminal_failure_type": None,
            "detail_fetch_status": "budget_deferred",
        }
    return {"classification": "pending", "terminal_failure_type": None}
```

`serialize_retry_articles` must normalize every article to a complete scheduler schema. Missing keys must be filled with safe defaults rather than left absent after restart.

### Step 3: Run helper tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  -q
```

Expected: PASS.

---

## 5. Task 3: Add Scheduler State Persistence

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

Persisted scheduler state must contain enough minimal article metadata to fetch detail and emit/recover diagnostics without relying on the current catalog list. Required per-article fields:

```text
source_article_id
title
source_detail_url_normalized
source_parent_url
source_published_at_ms
detected_at_ms
first_detected_at_ms
event_type
catalog_id / catalog_title if available
symbol_extraction_source
symbol_parse_failed_reason / pending_reason
source_published_at_ms_confidence
detail_fetch_attempt_count
transient_detail_error_count
non_transient_detail_error_count
last_retry_at_ms
next_detail_retry_at_ms
first_deferred_at_ms
last_deferred_at_ms
last_deferred_manifest_at_ms
defer_count
terminal_state
terminal_failure_type
```

If the current catalog list no longer includes a pending article after restart, the runner must still be able to fetch `source_detail_url_normalized` from the persisted state and emit a correct diagnostic event row.

### Step 1: Write persistence tests

```python
def test_detail_retry_scheduler_state_round_trips(tmp_path):
    state = {
        "articles": {
            "old": {
                "source_article_id": "old",
                "title": "Binance Futures Will Launch XUSDT Perpetual Contract",
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/old",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": 900,
                "detected_at_ms": 1000,
                "event_type": "futures_contract_launch",
                "symbol_extraction_source": "none",
                "pending_reason": "title_symbol_missing",
                "first_detected_at_ms": 1000,
                "detail_fetch_attempt_count": 2,
                "transient_detail_error_count": 2,
                "last_retry_at_ms": 2000,
                "next_detail_retry_at_ms": 62000,
                "defer_count": 0,
            }
        },
        "endpoint_health": {
            "detail_endpoint_degraded_until_ms": 62000,
            "recent_detail_attempt_results": ["http_202_empty"],
        },
    }

    write_detail_retry_scheduler_state(tmp_path, state, metadata_version=1)
    loaded = load_detail_retry_scheduler_state(tmp_path)

    assert loaded["metadata_version"] == 1
    assert loaded["articles"]["old"]["next_detail_retry_at_ms"] == 62000
    assert loaded["endpoint_health"]["detail_endpoint_degraded_until_ms"] == 62000
```

```python
def test_old_202_backoff_survives_restart_and_new_article_gets_attempt(tmp_path):
    write_detail_retry_scheduler_state(
        tmp_path,
        {
            "articles": {
                "old": {
                    "source_article_id": "old",
                    "title": "Old article",
                    "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/old",
                    "source_parent_url": "https://www.binance.com/en/support/announcement",
                    "source_published_at_ms": 900,
                    "detected_at_ms": 1000,
                    "event_type": "futures_contract_launch",
                    "first_detected_at_ms": 1000,
                    "detail_fetch_attempt_count": 5,
                    "transient_detail_error_count": 5,
                    "next_detail_retry_at_ms": 999999,
                    "last_retry_at_ms": 5000,
                },
                "new": {
                    "source_article_id": "new",
                    "title": "New article",
                    "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/new",
                    "source_parent_url": "https://www.binance.com/en/support/announcement",
                    "source_published_at_ms": 7900,
                    "detected_at_ms": 8000,
                    "event_type": "futures_contract_launch",
                    "first_detected_at_ms": 8000,
                    "detail_fetch_attempt_count": 0,
                    "transient_detail_error_count": 0,
                    "next_detail_retry_at_ms": 0,
                    "defer_count": 0,
                },
            },
            "endpoint_health": {},
        },
        metadata_version=1,
    )

    loaded = load_detail_retry_scheduler_state(tmp_path)
    selected = select_detail_retry_attempts(
        detail_retry_state=loaded["articles"],
        now_ms=10_000,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    )

    assert selected == ["new"]
```

```python
def test_pending_detail_article_survives_restart_after_it_disappears_from_catalog_list(tmp_path):
    write_detail_retry_scheduler_state(
        tmp_path,
        {
            "articles": {
                "missing_from_catalog": {
                    "source_article_id": "missing_from_catalog",
                    "title": "Binance Futures Will Launch XUSDT Perpetual Contract",
                    "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/missing_from_catalog",
                    "source_parent_url": "https://www.binance.com/en/support/announcement",
                    "source_published_at_ms": 1000,
                    "detected_at_ms": 1100,
                    "event_type": "futures_contract_launch",
                    "symbol_extraction_source": "none",
                    "pending_reason": "title_symbol_missing",
                    "first_detected_at_ms": 1100,
                    "detail_fetch_attempt_count": 0,
                    "transient_detail_error_count": 0,
                    "next_detail_retry_at_ms": 0,
                    "defer_count": 0,
                }
            },
            "endpoint_health": {},
        },
        metadata_version=1,
    )

    loaded = load_detail_retry_scheduler_state(tmp_path)
    article = loaded["articles"]["missing_from_catalog"]

    assert article["source_detail_url_normalized"].endswith("/missing_from_catalog")
    assert article["title"]
    assert article["event_type"] == "futures_contract_launch"
    assert select_detail_retry_attempts(
        detail_retry_state=loaded["articles"],
        now_ms=1200,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=0,
    ) == ["missing_from_catalog"]
```

### Step 2: Implement persistence helpers

Use a compact JSON file, not one JSONL row per poll:

```python
DETAIL_RETRY_SCHEDULER_STATE_FILENAME = "detail_retry_scheduler_state.json"


def load_detail_retry_scheduler_state(output_root: Path) -> dict:
    path = output_root / DETAIL_RETRY_SCHEDULER_STATE_FILENAME
    if not path.exists():
        return {"metadata_version": 1, "articles": {}, "endpoint_health": {}}
    with path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    if not isinstance(loaded.get("articles"), dict):
        loaded["articles"] = {}
    if not isinstance(loaded.get("endpoint_health"), dict):
        loaded["endpoint_health"] = {}
    return loaded


def write_detail_retry_scheduler_state(output_root: Path, state: dict, *, metadata_version: int) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / DETAIL_RETRY_SCHEDULER_STATE_FILENAME
    tmp_path = path.with_suffix(".json.tmp")
    serializable = dict(state)
    serializable["metadata_version"] = metadata_version
    tmp_path.write_text(json.dumps(serializable, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)
```

`write_detail_retry_scheduler_state` must only write normalized output from `serialize_retry_articles`. The serialized state is the latest scheduler state source of truth. `request_manifest/*.jsonl` remains an append-only audit trail, not the authoritative latest deferred state.

### Step 3: Run persistence tests

Expected: PASS.

---

## 6. Task 4: Integrate Fair Scheduler Into Stage 1.5D Runner

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

### Step 1: Write starvation regression test

Add a runner-level test that creates three old transient articles plus one new no-symbol article, with budget = 3. The new article must receive a detail attempt within the same or bounded subsequent poll.

Test intent:

```python
def test_old_transient_detail_backlog_does_not_starve_new_article_first_attempt(...):
    # Arrange: list payload has old1/old2/old3/new.
    # old1/old2/old3 detail fetch returns HTTP 202 empty.
    # new detail fetch returns payload with valid symbols.
    # Act: run enough polls to exercise scheduler.
    # Assert: request_manifest contains announcement_detail row for new source_article_id.
    # Assert: events contain parsed symbols for new article, not terminal_failed symbols=[].
```

Concrete mock design:

```text
1. Reuse the existing Stage 1.5D runner test fixture that writes valid 1.5C / 1.5C1 upstream summaries.
2. Monkeypatch the runner's HTTP fetch helper or Binance client wrapper used by announcement list/detail calls.
3. First poll announcement list payload includes old1, old2, old3 and new_article_id.
4. Detail URL responses:
   - old1/old2/old3 return http_status=202, payload/body empty, error=detail_payload_http_status_202.
   - new_article_id returns a trusted detail payload/body containing a parseable contract symbol, for example ETHUSD1.
5. Run the collector with bounded max_seconds / poll interval under fake time or existing loop-count fixture used by current runner tests.
6. Read request_manifest rows from output_root/request_manifest/*.jsonl.
7. Read event rows from output_root/events/*.jsonl.
8. Assert new_article_id has an announcement_detail manifest row and no terminal_failed detail_fetch_attempted=false event row.
```

Minimum assertions:

```python
assert any(
    row.get("request_type") == "announcement_detail"
    and row.get("source_article_id") == "new_article_id"
    for row in request_manifest_rows
)
assert not any(
    row.get("source_article_id") == "new_article_id"
    and row.get("symbol_parse_status") == "terminal_failed"
    and row.get("detail_fetch_attempted") is False
    for row in event_rows
)
```

### Step 2: Write never-attempted protection test

```python
def test_never_attempted_detail_article_does_not_terminal_fail_as_symbol_empty(...):
    # Arrange: article enters detail_retry_state but budget is consumed / zero until age exceeds max age.
    # Act: run collector beyond EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC.
    # Assert: if terminal artifact is emitted, terminal_failure_type is detail_never_attempted_budget_starved.
    # Assert: summary symbol_empty_event_count and detail_symbol_parse_failed_count do not increment for this article.
```

Required assertions:

```python
assert event_row["terminal_failure_type"] == "detail_never_attempted_budget_starved"
assert event_row["detail_fetch_attempted"] is False
assert event_row["detail_fetch_status"] == "budget_starved"
assert event_row["symbol_parse_failed_reason"] == "detail_never_attempted_budget_starved"
assert summary["detail_budget_starved_count"] == 1
assert summary["detail_never_attempted_expired_count"] == 1
assert summary["symbol_empty_event_count"] == 0
assert summary["detail_symbol_parse_failed_count"] == 0
```

### Step 3: Replace direct dict-order retry loop

In the runner:

1. Load scheduler state once before the poll loop:

```python
scheduler_state = load_detail_retry_scheduler_state(output_root)
persisted_articles = scheduler_state.get("articles", {})
```

2. When adding an article to `detail_retry_state`, merge persisted scheduler metadata if present. Preserve the existing `raw_art` object when it is available from the current catalog. Do not reference an undefined `ev` variable; derive values from the current normalized event metadata already in scope or from persisted article metadata.

```python
persisted = persisted_articles.get(code, {})
detail_retry_state[code] = {
    "raw": raw_art,
    "source_article_id": code,
    "title": raw_art.get("title") or persisted.get("title"),
    "source_detail_url_normalized": persisted.get("source_detail_url_normalized") or build_detail_url(code),
    "source_parent_url": source_parent_url,
    "source_published_at_ms": raw_art.get("releaseDate") or persisted.get("source_published_at_ms"),
    "detected_at_ms": persisted.get("detected_at_ms", now_ms),
    "event_type": "futures_contract_launch",
    "first_detected_at_ms": persisted.get("first_detected_at_ms", now_ms),
    "detail_fetch_attempt_count": persisted.get("detail_fetch_attempt_count", 0),
    "transient_detail_error_count": persisted.get("transient_detail_error_count", 0),
    "non_transient_detail_error_count": persisted.get("non_transient_detail_error_count", 0),
    "last_retry_at_ms": persisted.get("last_retry_at_ms", 0),
    "next_detail_retry_at_ms": persisted.get("next_detail_retry_at_ms", 0),
    "first_deferred_at_ms": persisted.get("first_deferred_at_ms"),
    "last_deferred_at_ms": persisted.get("last_deferred_at_ms"),
    "last_deferred_manifest_at_ms": persisted.get("last_deferred_manifest_at_ms", 0),
    "defer_count": persisted.get("defer_count", 0),
    "source_published_at_ms_confidence": (
        current_event_metadata.get("source_published_at_ms_confidence")
        or persisted.get("source_published_at_ms_confidence")
        or "medium"
    ),
    "symbol_extraction_source": persisted.get("symbol_extraction_source", "none"),
    "pending_reason": persisted.get("pending_reason", "title_symbol_missing"),
}
```

For persisted articles that are not present in the current catalog after restart, reconstruct the in-memory state from persisted metadata and set `raw` to a minimal raw-like dict:

```python
raw = {
    "code": article["source_article_id"],
    "title": article["title"],
    "releaseDate": article.get("source_published_at_ms"),
}
```

3. Build `attempt_codes` using `select_detail_retry_attempts(...)`.

4. For states not selected because budget is exhausted, call `mark_detail_budget_deferred(...)` and increment `detail_budget_deferred_count`, but do not fetch.

5. Persist scheduler state at the end of each poll:

```python
scheduler_state["articles"] = serialize_retry_articles(detail_retry_state)
scheduler_state["endpoint_health"] = endpoint_health
write_detail_retry_scheduler_state(
    output_root,
    scheduler_state,
    metadata_version=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION,
)
```

### Step 4: Run targeted runner tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: existing tests still pass, new starvation tests pass.

---

## 7. Task 5: Add Transient Backoff And Endpoint Degraded Breaker

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

### Step 1: Write endpoint degraded tests

```python
def test_endpoint_degraded_after_recent_202_empty_rate_crosses_threshold():
    health = {"recent_detail_attempt_results": []}
    now_ms = 100_000
    for idx in range(5):
        health = update_detail_endpoint_health(
            health,
            now_ms=now_ms + idx,
            result_code="http_202_empty",
            degraded_rate_threshold=0.80,
            degraded_min_sample=5,
            degraded_backoff_sec=15 * 60,
        )

    assert health["detail_endpoint_degraded_until_ms"] == now_ms + 4 + 15 * 60 * 1000
    assert health["detail_endpoint_transient_error_rate"] == 1.0
```

```python
def test_endpoint_degraded_skips_old_transient_but_preserves_never_attempted_first_attempt():
    now_ms = 100_000
    state = {
        "old": {
            "source_article_id": "old",
            "detail_fetch_attempt_count": 4,
            "transient_detail_error_count": 4,
            "next_detail_retry_at_ms": now_ms,
            "last_retry_at_ms": now_ms - 60_000,
            "first_detected_at_ms": now_ms - 600_000,
        },
        "new": {
            "source_article_id": "new",
            "detail_fetch_attempt_count": 0,
            "transient_detail_error_count": 0,
            "next_detail_retry_at_ms": 0,
            "first_detected_at_ms": now_ms - 1_000,
            "defer_count": 0,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=1,
        endpoint_degraded_until_ms=now_ms + 60_000,
    )

    assert selected == ["new"]
```

```python
def test_endpoint_degraded_preserves_budget_cap_for_many_never_attempted_articles():
    now_ms = 100_000
    state = {
        f"new{i}": {
            "source_article_id": f"new{i}",
            "detail_fetch_attempt_count": 0,
            "transient_detail_error_count": 0,
            "next_detail_retry_at_ms": 0,
            "first_detected_at_ms": now_ms - i * 1000,
            "defer_count": 0,
        }
        for i in range(20)
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms + 60_000,
    )

    assert len(selected) == 3
    assert all(state[code]["detail_fetch_attempt_count"] == 0 for code in selected)
```

Endpoint degraded semantics:

```text
endpoint_degraded active:
  never_attempted_first_attempts <= EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL
  attempted_transient_attempts = 0
  selected_count <= EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL
```

### Step 2: Implement backoff update

After each transient detail fetch failure, update state:

```python
state["detail_fetch_attempt_count"] = int(state.get("detail_fetch_attempt_count") or 0) + 1
state["retry_count"] = int(state.get("retry_count") or 0) + 1
state["transient_detail_error_count"] = int(state.get("transient_detail_error_count") or 0) + 1
state["last_retry_at_ms"] = now_ms
state["next_detail_retry_at_ms"] = now_ms + compute_detail_transient_backoff_ms(
    state["transient_detail_error_count"],
    base_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC,
    max_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC,
)
```

### Step 3: Update endpoint health after every detail attempt

Classify attempt result as one of:

```text
success
http_202_empty
http_429
http_5xx
network_error
non_transient_error
```

Only `announcement_detail` real requests should update endpoint health. `announcement_detail_deferred` scheduler decisions must not.

### Step 4: Run tests

Expected: PASS.

---

## 8. Task 6: Add Manifest Schema Cleanup And Deferred Compaction

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

### Step 1: Write manifest tests

```python
def test_stage1_5d_manifest_rows_include_request_type_and_article_id(...):
    # Run collector through one announcement list poll and one detail attempt.
    # Assert request_manifest rows have request_type.
    assert any(row.get("request_type") == "announcement_list" for row in rows)
    assert any(
        row.get("request_type") == "announcement_detail"
        and row.get("source_article_id") == "article1"
        for row in rows
    )
    assert all(row.get("audit_metadata_version") == 1 for row in rows if row.get("request_type"))
```

```python
def test_deferred_manifest_is_compacted_not_written_every_poll(...):
    # Arrange an article deferred for multiple polls.
    # Assert at most one announcement_detail_deferred row is written within the configured interval.
    deferred = [row for row in rows if row.get("request_type") == "announcement_detail_deferred"]
    assert len(deferred) == 1
    assert deferred[0]["defer_count"] >= 1
    assert deferred[0]["latest_defer_reason"] == "detail_budget_exhausted"
```

```python
def test_scheduler_state_contains_latest_defer_count_even_when_manifest_deferred_rows_are_rate_limited(...):
    # Arrange one article deferred across multiple polls within the deferred manifest rate-limit interval.
    # request_manifest should not receive one row per poll.
    # detail_retry_scheduler_state.json must still contain the latest defer_count and last_deferred_at_ms.
    deferred_rows = [row for row in manifest_rows if row.get("request_type") == "announcement_detail_deferred"]
    assert len(deferred_rows) == 1

    state_article = scheduler_state["articles"]["article1"]
    assert state_article["defer_count"] >= 3
    assert state_article["last_deferred_at_ms"] >= state_article["first_deferred_at_ms"]
```

### Step 2: Add request types

All request manifest rows written by Stage 1.5D should now include:

```json
{
  "request_type": "announcement_list | announcement_detail | announcement_detail_deferred | exchange_info | first_futures_bar_klines",
  "audit_metadata_version": 1
}
```

For article detail rows include:

```json
{
  "request_type": "announcement_detail",
  "source_article_id": "...",
  "source_detail_url_normalized": "..."
}
```

For deferred diagnostics include compacted state:

```json
{
  "request_type": "announcement_detail_deferred",
  "source_article_id": "...",
  "first_deferred_at_ms": 0,
  "last_deferred_at_ms": 0,
  "defer_count": 17,
  "latest_defer_reason": "detail_budget_exhausted"
}
```

Do not write one deferred JSONL row per article per poll. Use `last_deferred_manifest_at_ms` and `EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEFERRED_MANIFEST_MIN_INTERVAL_SEC` to compact.

State ownership rule:

```text
request_manifest/*.jsonl:
  append-only audit trail for real requests and rate-limited scheduler diagnostics.

detail_retry_scheduler_state.json:
  authoritative latest scheduler state source of truth, including latest defer_count / first_deferred_at_ms / last_deferred_at_ms.
```

### Step 3: Run manifest tests

Expected: PASS.

---

## 9. Task 7: Fix Terminal Failure Taxonomy And Summary Counters

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

### Step 1: Write taxonomy tests

Add or extend runner tests to assert these failure classes:

```text
detail_never_attempted_budget_starved:
  detail_fetch_attempt_count == 0
  terminal_failure_type = detail_never_attempted_budget_starved
  increments detail_budget_starved_count and detail_never_attempted_expired_count
  does not increment symbol_empty_event_count / detail_symbol_parse_failed_count

detail_transient_timeout:
  detail_fetch_attempt_count > 0
  transient_detail_error_count > 0
  terminal_failure_type = detail_transient_timeout
  increments detail_transient_timeout_count
  does not increment symbol_empty_event_count / detail_success_symbols_empty_count

detail_success_symbols_empty:
  detail fetch succeeded and trusted payload has no symbol
  terminal_failure_type = detail_success_symbols_empty
  may increment symbol_empty_event_count and detail_success_symbols_empty_count

candidate_validation_rejected:
  candidate symbols extracted but exchangeInfo validation rejects them
  terminal_failure_type = candidate_validation_rejected
```

### Step 2: Add counters

Runner summary must include:

```text
detail_budget_deferred_count
detail_budget_starved_count
detail_never_attempted_expired_count
detail_first_attempt_sla_breach_count
detail_scheduler_pending_count
detail_scheduler_backoff_count
detail_endpoint_degraded_count
detail_endpoint_degraded_active
detail_success_symbols_empty_count
```

Rules:

```text
budget_starved must not increment:
  symbol_empty_event_count
  detail_symbol_parse_failed_count
  detail_success_symbols_empty_count

attempted transient timeout must not increment:
  symbol_empty_event_count
  detail_success_symbols_empty_count
```

### Step 3: Replace the old never-attempted max-age branch explicitly

The current runner has an old branch equivalent to:

```python
elif not has_candidate_symbols and not has_transient_detail_errors and age_sec >= max_age_limit:
    symbol_empty_event_count += 1
    symbol_parse_failed_count += 1
    detail_symbol_parse_failed_count += 1
    terminal_fail_type = None
```

This is the 2026-07-09 bug path. Replace it with explicit classification:

```python
if state.get("detail_fetch_attempt_count", 0) == 0:
    defer_classification = classify_never_attempted_defer_state(
        detail_fetch_attempt_count=0,
        first_detected_at_ms=state["first_detected_at_ms"],
        now_ms=now_ms,
        never_attempted_max_defer_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_NEVER_ATTEMPTED_MAX_DEFER_SEC,
        detail_fetch_max_age_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC,
    )

    if defer_classification["classification"] == "detail_first_attempt_sla_breach":
        detail_first_attempt_sla_breach_count += 1
        # Keep pending; do not emit terminal_failed yet.
        continue

    if defer_classification["classification"] == "detail_never_attempted_budget_starved":
        detail_budget_starved_count += 1
        detail_never_attempted_expired_count += 1
        detail_terminal_failed_count += 1
        fetch_status = "budget_starved"
        failed_reason = "detail_never_attempted_budget_starved"
        terminal_fail_type = "detail_never_attempted_budget_starved"
        # Do not increment symbol_empty_event_count or detail_symbol_parse_failed_count.
```

Only a successful trusted detail fetch with no extracted symbols may use `terminal_failure_type = detail_success_symbols_empty` and increment symbol-empty/content-parser counters.

### Step 4: Update summary builder

`src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py` must pass through the new counters and not derive parser failure from `terminal_failed` alone.

### Step 5: Run tests

Expected: PASS.

---

## 10. Task 8: Add Stage 1.5G / Review Compatibility Tests

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Modify tests:
  - `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py`
  - `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py`
  - `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`

### Step 1: Add explicit Stage 1.5D terminal failure classifier

Create a small pure helper in `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`:

```python
def classify_stage1_5d_terminal_failure(event: dict) -> str:
    terminal_failure_type = event.get("terminal_failure_type")
    if terminal_failure_type in {
        "detail_never_attempted_budget_starved",
        "detail_transient_timeout",
        "detail_unavailable_timeout",
    }:
        return "collection_failure"
    if terminal_failure_type == "detail_success_symbols_empty":
        return "content_or_parser_empty"
    if terminal_failure_type == "candidate_validation_rejected":
        return "validation_rejected"
    if event.get("symbol_parse_status") == "terminal_failed":
        return "unknown_terminal_failure"
    return "not_terminal_failure"
```

This helper is for review interpretation only. It must not turn a failed Stage 1.5D row into formal Stage 1.5G evidence.

### Step 2: Add tests proving scheduler diagnostics are not formal evidence

```python
def test_stage1_5g_depth_request_health_ignores_stage1_5d_announcement_detail_deferred_rows():
    rows = [
        {
            "request_type": "announcement_detail_deferred",
            "source_article_id": "article1",
            "defer_count": 4,
            "latest_defer_reason": "detail_budget_exhausted",
        }
    ]

    health = compute_depth_request_health(..., request_manifest_rows=rows, ...)

    assert health.depth_request_manifest_rows_count == 0
    assert health.scheduler_diagnostic_rows_count == 1
    assert health.per_symbol_request_success_rate_min is None
    assert "request_manifest_symbol_key_missing" not in health.blockers
```

```python
def test_budget_starved_terminal_failure_is_recovery_only_not_formal_evidence():
    event = {
        "event_type": "futures_contract_launch",
        "symbols": [],
        "symbol_parse_status": "terminal_failed",
        "terminal_failure_type": "detail_never_attempted_budget_starved",
    }

    assert classify_stage1_5d_terminal_failure(event) == "collection_failure"
```

Stage 1.5G manifest handling rule:

```text
request_type == "depth_snapshot":
  included in depth request health and must have event_symbol_id / symbol.

request_type != "depth_snapshot":
  ignored for depth request success-rate calculations.
  optionally counted as scheduler_diagnostic_rows_count or non_depth_manifest_rows_count for diagnostics.
  must not trigger request_manifest_symbol_key_missing.
  must not improve or degrade per-symbol request success rate.
```

This rule also preserves Stage 1.5F `enrich_depth_request_manifest_row` semantics: the helper should only be used for depth snapshot rows, not for Stage 1.5D `announcement_detail_deferred` rows.

If no `compute_depth_request_health` helper exists, create a small helper or adapt the existing coverage metric helper so the row filtering is explicit and directly unit-tested. Do not rely on incidental behavior from missing `event_symbol_id` fields.

### Step 3: Preserve strict old unkeyed depth manifest gate

Add or keep test:

```python
def test_unknown_or_unkeyed_depth_manifest_still_blocks_formal_audit():
    result = build_stage1_5g_review_summary(
        ...,
        request_manifest_rows=[
            {
                "request_type": "depth_snapshot",
                "requested_path": "/fapi/v1/depth",
                "http_status": 200,
            }
        ],
    )

    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "request_manifest_symbol_key_missing" in result["blockers"]
```

### Step 4: Run Stage 1.5G tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  -q
```

Expected: PASS. If exact files are absent, run the existing `test_stage1_5g_live_depth_evidence_review_*.py` set.

---

## 11. Task 9: Update Stage 1.5F Review Runbook Notes

**Files:**
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

### Step 1: Add a Chinese subsection for this hotfix

Add a section under the existing Stage 1.5D/1.5F troubleshooting area:

```text
Stage 1.5D detail retry scheduler starvation hotfix 检查
```

Include commands to check:

```bash
cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" | python -m json.tool | grep -E \
"detail_budget_deferred_count|detail_budget_starved_count|detail_never_attempted_expired_count|detail_first_attempt_sla_breach_count|detail_scheduler_pending_count|detail_scheduler_backoff_count|detail_endpoint_degraded"

python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
state_path = root / "detail_retry_scheduler_state.json"
print("scheduler_state_exists", state_path.exists())
if state_path.exists():
    state = json.loads(state_path.read_text())
    print("metadata_version", state.get("metadata_version"))
    print("pending_articles", len(state.get("articles", {})))
    print("endpoint_health", state.get("endpoint_health", {}))
PY
```

### Step 2: Document interpretation

Add clear criteria:

```text
正常：newly detected no-symbol futures article 有 announcement_detail request_manifest row，或仍在 scheduler_state pending/backoff/deferred 中。
异常：detail_fetch_attempted=false 的 article 被写成 terminal_failed + symbol_empty/parser_failed。
异常：announcement_detail_deferred 每分钟对同一 source_article_id 无限写行。
异常：request_type 全部为 unknown，无法区分 announcement_list / announcement_detail / exchange_info。
```

---

## 12. Task 10: Verification Commands

Run targeted tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Run Stage 1.5F regression:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer*.py \
  -q
```

Run Stage 1.5G compatibility/regression:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_*.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q
```

Run formatting and safety checks:

```bash
git diff --check

grep -R "paper_trading_allowed.*true\|live_trading_allowed.*true\|trade_signal_allowed.*true\|execution_engine_allowed.*true\|alpha_interpretation_allowed.*true" \
  configs scripts src tests docs \
  --exclude-dir=.venv \
  --exclude-dir=.git \
  --exclude='*.pyc' || true
```

Expected safety grep result:

```text
No newly introduced true safety flags in Stage 1.5D/1.5F/1.5G code paths.
```

If `test_stage1_5f_live_depth_observer.py` or the exact script review test is absent, do not skip regression entirely; run the nearest existing Stage 1.5F pytest files shown by:

```bash
find tests -type f -name '*stage1_5f*' | sort
```

---

## 13. Deployment Boundary After Implementation

After code passes tests, deploy with new roots only:

```text
new Stage 1.5D root:
  data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_detail_retry_scheduler_hotfix

new Stage 1.5F root:
  data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_hotfix_<RUN_ID>
```

Rules:

```text
1. Do not edit old events/*.jsonl.
2. Do not rewrite old terminal_failed rows to parsed rows.
3. Do not treat 2026-07-09 missed event as formal 12h live depth evidence.
4. New 1.5F root must bootstrap watermark from the new 1.5D root.
5. Old roots remain review artifacts only.
```

Operational check after deployment:

```bash
date -u
tmux ls
ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" 2>/dev/null | python -m json.tool || true
wc -l "$STAGE1_5D_EVENTS_OUT"/heartbeats/*.jsonl 2>/dev/null || true
wc -l "$STAGE1_5D_EVENTS_OUT"/events/*.jsonl 2>/dev/null || true
find "$STAGE1_5D_EVENTS_OUT/request_manifest" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
cat "$STAGE1_5D_EVENTS_OUT/detail_retry_scheduler_state.json" 2>/dev/null | python -m json.tool || true
```

Acceptance criteria after deployment:

```text
1. Stage 1.5D heartbeats continue every poll.
2. request_manifest rows have request_type, not all unknown.
3. scheduler_state exists and has metadata_version=1.
4. No newly detected no-symbol futures article is terminal_failed with detail_fetch_attempted=false and symbol_empty/parser failure counters.
5. If detail endpoint returns repeated HTTP 202, old articles move to backoff and endpoint_degraded diagnostics appear.
6. When a new no-symbol futures article appears, it receives announcement_detail request_manifest row within first-attempt SLA.
```

---

## 14. Completion Criteria

Implementation is complete only when all are true:

```text
1. Config constants exist in configs/base.py and tests cover them.
2. Scheduler helper tests prove bounded fairness, backoff, endpoint degraded behavior, and restart persistence.
3. Stage 1.5D runner no longer uses raw dict insertion order as the detail retry scheduler.
4. Never-attempted articles cannot become symbol-empty/parser-failed evidence.
5. Deferred diagnostics are compacted and auditable.
6. Summary counters distinguish collection failure from parser/content failure.
7. Stage 1.5G ignores scheduler diagnostics as depth request failures but still blocks unkeyed depth_snapshot rows.
8. Persisted scheduler state contains minimal article metadata and can fetch a pending article after it disappears from the current catalog list.
9. EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_NEVER_ATTEMPTED_MAX_DEFER_SEC is used by classify_never_attempted_defer_state and increments detail_first_attempt_sla_breach_count before max-age.
10. endpoint_degraded active state preserves first attempts but never selects more rows than DETAIL_FETCH_BUDGET_PER_POLL.
11. Stage 1.5G depth request health only considers request_type == depth_snapshot.
12. classify_stage1_5d_terminal_failure exists and classifies budget_starved / transient timeout as collection_failure.
13. Targeted Stage 1.5D tests pass.
14. Stage 1.5F regression tests pass.
15. Stage 1.5G compatibility tests pass.
16. `git diff --check` passes.
17. Review/runbook document includes the new checks and interpretation.
```
