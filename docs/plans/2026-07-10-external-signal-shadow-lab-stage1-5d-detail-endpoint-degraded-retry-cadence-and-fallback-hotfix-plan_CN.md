# Stage 1.5D Detail Endpoint Degraded Retry Cadence And Fallback Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. For every code task, use TDD: write the failing test, verify it fails, then implement the minimal fix.

**Goal:** Improve Stage 1.5D behavior when Binance announcement detail endpoint returns repeated HTTP 202 / empty payload: new announcement articles must retry at a bounded cadence, old transient articles must remain throttled, and `detail_http_request_count` must match auditable HTTP request manifest rows while `detail_retry_cycle_count` tracks scheduler selections separately.

**Architecture:** Keep the existing Stage 1.5D scheduler helper, but split retry policy into two tracks: recently detected articles get a protected degraded retry cadence; old transient articles continue using endpoint-level degraded backoff. Add a small detail-fetch fallback path for alternate public Binance announcement detail URL forms only after the primary URL returns transient 202/empty. Do not change Stage 1.5F watermark, age gate, depth collection, or any trading safety flags.

**Tech Stack:** Python stdlib, `configs/base.py`, existing Stage 1.5D scheduler helper, JSONL artifacts, pytest.

---

## 0. Safety Boundary

```text
private_api_allowed = false
order_endpoint_allowed = false
api_key_allowed = false
stage1_5f_watermark_change_allowed = false
stage1_5f_age_gate_change_allowed = false
old_artifact_rewrite_allowed = false
symbol_guessing_allowed = false
exchangeinfo_only_symbol_binding_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
```

This hotfix must not make `d083...` a formal Stage 1.5F evidence event. That article remains recovery validation because its `source_published_at_ms` is before the new Stage 1.5F watermark.

---

## 1. Observed Failure To Preserve

Observed on the 2026-07-10 `d0833e4ae9b542be90dbf3fe1c960c53` announcement:

```text
raw payload: found
announcement_detail manifest rows: 2
HTTP status: 202
payload_trusted: false
event_hits: 0
scheduler state: still present
endpoint_health: transient error rate 1.0, degraded window repeatedly extended
retry cadence: 09:08 -> 11:12, too slow for a new announcement
detail_fetch_attempt_count: 4
manifest_rows: 2
required_after_fix: detail_http_request_count == manifest_rows, detail_retry_cycle_count tracks scheduler selections
```

Interpretation:

```text
1. The previous starvation hotfix worked: the new article received detail attempts and was not terminal-failed.
2. The new issue is retry cadence under endpoint degraded state: new articles retry too slowly.
3. Audit semantics are also weak: detail_fetch_attempt_count currently mixes logical cycles and HTTP request rows; this hotfix must introduce explicit HTTP request and retry cycle counters.
```

---

## 2.1 Review Fixes Absorbed

The external review raised valid blocking issues. This implementation plan adopts these requirements before code execution:

```text
1. Split HTTP request count from logical retry cycle count.
2. Fallback URL requests must count against a total per-poll HTTP request budget.
3. Fallback is allowed only for HTTP 202 empty / HTTP 200 empty-untrusted payload, not 429, 5xx, network timeout, TLS error, or URL validation failure.
4. Endpoint degraded health must be tracked by URL variant so primary 202 does not mark the detail-path fallback variant degraded.
5. Retry cadence config semantics must be explicit: protected recent retry max counts logical cycles, not HTTP requests.
6. Fallback success must preserve payload trust checks, payload hash, URL provenance, and symbol extraction provenance.
7. New scheduler kwargs must be keyword-only, added after `endpoint_degraded_until_ms`, and all `select_detail_retry_attempts(` call sites must be grepped and reviewed.
8. The duplicate `detail_fetch_attempt_count` increment in the transient branch must be removed as one line only; `retry_count`, `last_retry_at_ms`, and `next_detail_retry_at_ms` updates must remain.
9. Summary fields require failing tests first, and mismatch counters must have explicit source logic.
```

Terminology used below:

```text
detail_http_request_count:
  Number of actual public announcement detail HTTP requests.
  Must equal the number of announcement_detail manifest rows for the article.

detail_retry_cycle_count:
  Number of times scheduler selected the article for a logical retry cycle.
  One cycle may include primary URL and one or more fallback URL HTTP requests.

protected recent retry max cycles:
  Limits logical cycles, not HTTP requests.
```

## 2. Design Decision

Use a bounded two-lane retry policy:

```text
Lane A: protected recent transient articles
  - Recently detected no-symbol futures articles that already had at least one transient detail failure.
  - They may retry during endpoint_degraded, but with a small protected budget and minimum retry interval.
  - Purpose: avoid missing the first useful detail payload when Binance detail recovers.

Lane B: old transient articles
  - Older repeated HTTP 202/empty articles.
  - They remain suppressed while endpoint_degraded is active.
  - Purpose: old bad URLs cannot consume all detail budget.
```

Do not disable endpoint degraded globally. The degraded circuit breaker is still useful. This hotfix only adds a protected retry allowance for recent articles.

---

## 3. Files

Modify:

```text
configs/base.py
src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

Tests:

```text
tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py
tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py
tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py
tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
```

---

## 4. Task 1: Add Retry Cadence Config

**Files:**
- Modify: `configs/base.py`
- Modify test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`

**Step 1: Write failing config test**

Add:

```python
def test_stage1_5d_detail_degraded_recent_retry_config_present():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_ARTICLE_WINDOW_SEC == 3 * 60 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_INTERVAL_SEC == 10 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_BUDGET_PER_POLL == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_MAX_CYCLES == 6
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FALLBACK_MAX_URLS_PER_ARTICLE == 2
```

Parameter semantics:

```text
DEGRADED_RECENT_ARTICLE_WINDOW_SEC = 3h:
  Article can be classified as recent for up to 3h.

DEGRADED_RECENT_RETRY_INTERVAL_SEC = 10min:
  Minimum time between protected retry cycles for a recent article.

DEGRADED_RECENT_RETRY_MAX_CYCLES = 6:
  First-hour burst protection: at 10min interval this protects about 60min of retry cycles.
  After 6 cycles the article falls back to old transient backlog treatment even if still inside the 3h recent window.

DETAIL_HTTP_REQUEST_BUDGET_PER_POLL:
  Hard cap for announcement detail HTTP requests per poll, including fallback URLs.

DETAIL_FALLBACK_MAX_URLS_PER_ARTICLE:
  Hard cap for URL variants attempted in one logical retry cycle.
```


**Step 2: Run failing test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py::test_stage1_5d_detail_degraded_recent_retry_config_present \
  -q
```

Expected: FAIL because constants do not exist.

**Step 3: Add constants**

Add near the existing Stage 1.5D detail config block:

```python
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_ARTICLE_WINDOW_SEC = 3 * 60 * 60
# Articles detected within this window are considered recent enough for protected degraded retry cadence.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_INTERVAL_SEC = 10 * 60
# Minimum retry interval for recent transient articles even while endpoint degraded is active.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_BUDGET_PER_POLL = 1
# Maximum protected recent transient retries per poll during endpoint degraded state.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_MAX_CYCLES = 6
# Maximum protected recent transient logical retry cycles before the article is treated like old transient backlog.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL = 4
# Hard cap for actual announcement detail HTTP requests per poll, including fallback URL attempts.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FALLBACK_MAX_URLS_PER_ARTICLE = 2
# Maximum detail URL variants attempted for one article in one logical retry cycle.
```


**Step 4: Re-run test**

Expected: PASS.

---

## 5. Task 2: Extend Scheduler Selection For Protected Recent Retries

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Modify test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

**Step 1: Write failing scheduler tests**

Add tests:

```python
def test_endpoint_degraded_allows_recent_transient_retry_with_protected_budget():
    now_ms = 4 * 60 * 60 * 1000
    state = {
        "recent": {
            "source_article_id": "recent",
            "first_detected_at_ms": now_ms - 30 * 60 * 1000,
            "detail_http_request_count": 2,
            "detail_retry_cycle_count": 2,
            "transient_detail_error_count": 2,
            "next_detail_retry_at_ms": now_ms - 1,
            "last_retry_at_ms": now_ms - 11 * 60 * 1000,
        },
        "old": {
            "source_article_id": "old",
            "first_detected_at_ms": now_ms - 12 * 60 * 60 * 1000,
            "detail_http_request_count": 8,
            "detail_retry_cycle_count": 8,
            "transient_detail_error_count": 8,
            "next_detail_retry_at_ms": now_ms - 1,
            "last_retry_at_ms": now_ms - 11 * 60 * 1000,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms + 60_000,
        degraded_recent_article_window_ms=3 * 60 * 60 * 1000,
        degraded_recent_retry_interval_ms=10 * 60 * 1000,
        degraded_recent_retry_budget_per_poll=1,
        degraded_recent_retry_max_cycles=6,
    )

    assert selected == ["recent"]


def test_endpoint_degraded_recent_retry_respects_interval_and_attempt_cap():
    now_ms = 4 * 60 * 60 * 1000
    state = {
        "too_soon": {
            "source_article_id": "too_soon",
            "first_detected_at_ms": now_ms - 30 * 60 * 1000,
            "detail_http_request_count": 2,
            "detail_retry_cycle_count": 2,
            "transient_detail_error_count": 2,
            "next_detail_retry_at_ms": now_ms - 1,
            "last_retry_at_ms": now_ms - 2 * 60 * 1000,
        },
        "too_many": {
            "source_article_id": "too_many",
            "first_detected_at_ms": now_ms - 30 * 60 * 1000,
            "detail_http_request_count": 6,
            "detail_retry_cycle_count": 6,
            "transient_detail_error_count": 6,
            "next_detail_retry_at_ms": now_ms - 1,
            "last_retry_at_ms": now_ms - 11 * 60 * 1000,
        },
    }

    selected = select_detail_retry_attempts(
        detail_retry_state=state,
        now_ms=now_ms,
        detail_budget_per_poll=3,
        endpoint_degraded_until_ms=now_ms + 60_000,
        degraded_recent_article_window_ms=3 * 60 * 60 * 1000,
        degraded_recent_retry_interval_ms=10 * 60 * 1000,
        degraded_recent_retry_budget_per_poll=1,
        degraded_recent_retry_max_cycles=6,
    )

    assert selected == []
```

**Step 2: Run failing tests**

Expected: FAIL due missing kwargs/behavior.

**Step 3: Implement scheduler logic**

Update `select_detail_retry_attempts` signature. The new parameters must remain keyword-only and must be added after `endpoint_degraded_until_ms`:

```python
def select_detail_retry_attempts(
    *,
    detail_retry_state: dict[str, dict],
    now_ms: int,
    detail_budget_per_poll: int,
    endpoint_degraded_until_ms: int,
    degraded_recent_article_window_ms: int | None = None,
    degraded_recent_retry_interval_ms: int | None = None,
    degraded_recent_retry_budget_per_poll: int = 0,
    degraded_recent_retry_max_cycles: int | None = None,
    max_first_attempt_delay_polls: int | None = None,
    max_first_attempt_delay_ms: int | None = None,
) -> list[str]:
```

Before implementation, run:

```bash
grep -R "select_detail_retry_attempts(" -n src scripts tests
```

Every call site must be reviewed. Existing tests may rely on defaults; runner must pass the new config values explicitly.

Behavior:

```text
1. never_attempted queue remains first priority and still capped by detail_budget_per_poll.
2. If endpoint is not degraded, attempted queue behavior remains unchanged.
3. If endpoint is degraded:
   - old attempted queue stays suppressed.
   - recent attempted transient queue may be selected only if:
     a. first_detected age <= degraded_recent_article_window_ms
     b. detail_retry_cycle_count < degraded_recent_retry_max_cycles
     c. now_ms - last_retry_at_ms >= degraded_recent_retry_interval_ms
     d. now_ms >= next_detail_retry_at_ms
   - protected recent retries are capped by min(remaining_budget, degraded_recent_retry_budget_per_poll).
```

**Step 4: Re-run scheduler tests**

Expected: PASS.

---

## 5.5 Task 2.5: Add Explicit HTTP Request And Retry Cycle Counters

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- Modify test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing tests**

Add tests asserting serialized scheduler state contains explicit defaults:

```python
def test_serialize_retry_articles_fills_http_request_and_retry_cycle_counts():
    serialized = serialize_retry_articles({"a": {"source_article_id": "a"}})
    assert serialized["a"]["detail_http_request_count"] == 0
    assert serialized["a"]["detail_retry_cycle_count"] == 0
```

Add a runner test where one logical cycle performs primary + fallback HTTP requests. Assert:

```python
assert state_article["detail_retry_cycle_count"] == 1
assert state_article["detail_http_request_count"] == 2
assert len(announcement_detail_manifest_rows_for_article) == 2
```

**Step 2: Run failing tests**

Expected: FAIL because fields are absent.

**Step 3: Implement counter semantics**

Rules:

```text
detail_retry_cycle_count:
  Increment exactly once when scheduler selects an article and the runner starts a logical detail retry cycle.

detail_http_request_count:
  Increment exactly once for each actual public HTTP detail request.
  Must equal announcement_detail manifest rows for the article.

detail_fetch_attempt_count:
  Keep for backward compatibility during this hotfix, but set it equal to detail_http_request_count when serializing state.
  Do not use it for protected retry cycle caps.
```

**Step 4: Re-run tests**

Expected: PASS.

---

## 6. Task 3: Fix Attempt Counter Semantics

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Problem:** Current runner increments `detail_fetch_attempt_count` before fetch and increments it again in the transient failure branch. This causes legacy `attempt_count > manifest_rows`. After Task 2.5, `detail_http_request_count` must equal manifest rows and legacy `detail_fetch_attempt_count` must mirror the HTTP request count for backward compatibility.

**Step 1: Write failing test**

Add an integration test with repeated HTTP 202 and zero backoff. Assert:

```python
assert state_article["detail_http_request_count"] == len(detail_manifest_rows_for_article)
assert state_article["detail_fetch_attempt_count"] == state_article["detail_http_request_count"]
```

Test outline:

```python
def test_detail_fetch_attempt_count_matches_announcement_detail_manifest_rows_for_transient_202(tmp_path):
    # one list article requiring detail
    # fetch_public_payload always returns HTTP 202 empty
    # max_polls=3, poll_interval=0
    # backoff base/max patched to 0
    # detail budget patched to 1
    # assert scheduler state detail_http_request_count == manifest rows for source_article_id
    # assert legacy detail_fetch_attempt_count mirrors detail_http_request_count
```

**Step 2: Run failing test**

Expected: FAIL with attempt_count greater than manifest rows.

**Step 3: Implement minimal fix**

Rules:

```text
1. Increment `detail_retry_cycle_count` exactly once when the article is selected and a logical retry cycle starts.
2. Increment `detail_http_request_count` exactly once per actual HTTP detail fetch path.
3. Keep legacy `detail_fetch_attempt_count` equal to `detail_http_request_count`.
4. Do not increment HTTP request counters for scheduler selection, defer, URL validation failure before HTTP, or candidate validation.
5. Remove only the duplicate line `state["detail_fetch_attempt_count"] = int(state.get("detail_fetch_attempt_count") or 0) + 1` in the transient failure branch.
6. Preserve `transient_detail_error_count`, `retry_count`, `last_retry_at_ms`, and `next_detail_retry_at_ms` updates unchanged.
```

Careful: fixture path that simulates detail payload should count as a detail fetch only if it writes an `announcement_detail` or `fixture_detail` manifest row.

**Step 4: Re-run test**

Expected: PASS.

---

## 7. Task 4: Wire Protected Retry Config Into Runner

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing integration test**

Add a test where:

```text
1. Endpoint health is degraded after repeated HTTP 202.
2. A recent article has previous transient failures and next_retry_at_ms is due.
3. Old transient articles also exist.
4. Runner should retry the recent article during degraded state but not old backlog.
```

If full runner setup is too heavy, validate through `select_detail_retry_attempts` in Task 2 and add one runner smoke test asserting config kwargs are wired by observing recent article receives a second manifest row while old articles do not.

**Step 2: Implement runner wiring**

Pass these args into `select_detail_retry_attempts`:

```python
degraded_recent_article_window_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_ARTICLE_WINDOW_SEC * 1000,
degraded_recent_retry_interval_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_INTERVAL_SEC * 1000,
degraded_recent_retry_budget_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_BUDGET_PER_POLL,
degraded_recent_retry_max_cycles=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_MAX_CYCLES,
```

**Step 3: Re-run runner tests**

Expected: PASS.

---

## 8. Task 5: Add Detail Fetch Fallback URL Builder

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py`

**Step 1: Write failing tests**

Add:

```python
def test_build_announcement_detail_fallback_urls_returns_allowlisted_detail_variants():
    urls = build_announcement_detail_fallback_urls(
        "https://www.binance.com/en/support/announcement/d0833e4ae9b542be90dbf3fe1c960c53"
    )
    assert "https://www.binance.com/en/support/announcement/detail/d0833e4ae9b542be90dbf3fe1c960c53" in urls
    assert urls[0].endswith("/announcement/d0833e4ae9b542be90dbf3fe1c960c53")
    assert len(urls) == len(set(urls))
    for url in urls:
        validate_announcement_detail_url(url)
```

**Step 2: Implement helper**

Add:

```python
def build_announcement_detail_fallback_urls(url: str) -> list[str]:
    validate_announcement_detail_url(url)
    parsed = urllib.parse.urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    code = parts[-1]
    candidates = [
        url,
        f"https://www.binance.com/en/support/announcement/detail/{code}",
        f"https://www.binance.com/en/support/announcement/{code}",
    ]
    unique = []
    for candidate in candidates:
        if candidate not in unique:
            validate_announcement_detail_url(candidate)
            unique.append(candidate)
    return unique
```

Do not add non-Binance domains. Do not add private/auth endpoints.

**Step 3: Re-run client tests**

Expected: PASS.

---

## 9. Task 6: Use Fallback URLs Only For Transient Detail Failures

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing tests**

Add tests:

```python
def test_detail_fetch_fallback_detail_url_used_after_primary_http_202(tmp_path):
    # primary /announcement/<code> returns HTTP 202 empty
    # fallback /announcement/detail/<code> returns 200 with trusted payload containing ETHUSD1
    # assert manifest has primary failed row and fallback success row
    # assert event parsed symbols includes ETHUSD1
    # assert event/manifest records detail_fetch_variant and detail_payload_hash


def test_detail_fallback_requests_respect_total_http_request_budget_per_poll(tmp_path):
    # detail_http_request_budget_per_poll=1
    # primary returns HTTP 202
    # assert fallback is not attempted in the same poll


def test_detail_fallback_not_used_after_http_429(tmp_path):
    # primary returns 429
    # assert only one manifest row, no fallback URL request


def test_detail_fallback_not_used_after_network_timeout(tmp_path):
    # primary raises timeout/network error
    # assert no fallback URL request


def test_fallback_200_untrusted_payload_does_not_emit_parsed_event(tmp_path):
    # primary returns 202
    # fallback returns 200 with empty/untrusted payload
    # assert no parsed event


def test_fallback_success_event_records_fetch_variant_and_payload_hash(tmp_path):
    # fallback success must record detail_fetch_variant, detail_fetch_url_used, detail_payload_hash, detail_payload_trusted
```

**Step 2: Implement fallback loop**

Instead of one `fetch_public_payload(detail_url)`, build fallback URLs and try in order:

```text
1. Try primary URL.
2. Fallback is allowed only for:
   - http_202_empty
   - http_200_empty_untrusted_payload / empty_detail_payload
3. Fallback is not allowed for:
   - http_429
   - http_5xx
   - network_timeout / network_error
   - TLS error
   - URL validation failure
   - redirect host validation failure
4. Fallback request counts against EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL.
5. Per article URL attempts in one cycle are capped by EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FALLBACK_MAX_URLS_PER_ARTICLE.
6. Append one manifest row per actual HTTP request with `detail_fetch_variant` = primary / detail_path_fallback.
7. Stop on first `ok=True` trusted payload.
```

Important: Each actual HTTP request must increment `detail_http_request_count` exactly once, mirror legacy `detail_fetch_attempt_count`, and write exactly one request manifest row.

**Step 2.5: Preserve trust and provenance**

A fallback `200` response must pass the same trusted payload checks as the primary response. Parsed events from fallback success must include:

```text
detail_fetch_variant
detail_fetch_url_used
detail_payload_hash
detail_payload_trusted = true
symbol_extraction_source = detail_path_fallback or detail_payload_fallback
```

Do not parse untrusted fallback payloads.

**Step 3: Re-run test**

Expected: PASS.

---

## 9.5 Task 6.5: Track Endpoint Health By URL Variant

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Modify test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

**Step 1: Write failing test**

Add:

```python
def test_primary_202_does_not_mark_detail_path_fallback_degraded_when_fallback_succeeds():
    health = {}
    now_ms = 100_000
    for i in range(5):
        health = update_detail_endpoint_health_by_variant(
            health,
            now_ms=now_ms + i,
            variant="primary",
            result_code="http_202_empty",
            degraded_rate_threshold=0.80,
            degraded_min_sample=5,
            degraded_backoff_sec=900,
        )
    health = update_detail_endpoint_health_by_variant(
        health,
        now_ms=now_ms + 10,
        variant="detail_path_fallback",
        result_code="success",
        degraded_rate_threshold=0.80,
        degraded_min_sample=5,
        degraded_backoff_sec=900,
    )

    assert health["by_variant"]["primary"]["detail_endpoint_transient_error_rate"] == 1.0
    assert health["by_variant"]["primary"]["detail_endpoint_degraded_until_ms"] > now_ms
    assert health["by_variant"]["detail_path_fallback"].get("detail_endpoint_degraded_until_ms", 0) == 0
```

**Step 2: Implement variant health helper**

Add `update_detail_endpoint_health_by_variant(...)`. Keep aggregate `update_detail_endpoint_health(...)` for backward compatibility and summary fields, but scheduler/fallback decisions should prefer variant-specific health when available.

State shape:

```json
{
  "by_variant": {
    "primary": {
      "recent_detail_attempt_results": [],
      "detail_endpoint_transient_error_rate": 1.0,
      "detail_endpoint_degraded_until_ms": 0
    },
    "detail_path_fallback": {
      "recent_detail_attempt_results": [],
      "detail_endpoint_transient_error_rate": 0.0,
      "detail_endpoint_degraded_until_ms": 0
    }
  }
}
```

**Step 3: Re-run tests**

Expected: PASS.

---

## 10. Task 7: Summary Counters And Review Diagnostics

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

**Step 1: Write failing summary test**

Add or extend a summary test so `build_smoke_summary` / runner summary output includes:

```text
detail_degraded_recent_retry_count
detail_fetch_fallback_attempt_count
detail_fetch_fallback_success_count
detail_fetch_attempt_manifest_mismatch_count
```

Expected initial result: FAIL because fields are absent.

**Step 2: Define counter sources in runner**

```text
detail_degraded_recent_retry_count:
  Increment when an attempted article is selected by protected recent degraded retry lane.

detail_fetch_fallback_attempt_count:
  Increment for each fallback URL HTTP request attempted.

detail_fetch_fallback_success_count:
  Increment when fallback URL returns trusted payload and parsing proceeds from it.

detail_fetch_attempt_manifest_mismatch_count:
  Increment when, at end of poll, an article has detail_http_request_count different from counted announcement_detail manifest rows for that source_article_id in the current state/root.
  Expected value is 0. Non-zero is an audit warning.
```

**Step 3: Implement summary fields**

Add fields in `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py` and runner summary dict.

**Step 4: Update review doc**

Review doc should explain:

```text
1. `detail_degraded_recent_retry_count > 0` is expected when Binance detail endpoint is degraded but recent articles are protected.
2. `detail_fetch_attempt_manifest_mismatch_count` must be 0 for formal audit cleanliness.
3. Fallback success can validate parser recovery but does not override watermark evidence labels.
4. `DETAIL_DEGRADED_RECENT_RETRY_MAX_CYCLES=6` is a first-hour burst protection, not a 3h retry guarantee.
```

---

## 11. Task 8: Verification

Before tests, verify all scheduler call sites were reviewed:

```bash
grep -R "select_detail_retry_attempts(" -n src scripts tests
```

Run targeted tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Run downstream compatibility tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_*.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q
```

Run static checks:

```bash
git diff --check

grep -R "paper_trading_allowed.*true\|live_trading_allowed.*true\|trade_signal_allowed.*true\|execution_engine_allowed.*true\|alpha_interpretation_allowed.*true" \
  configs scripts src tests \
  --exclude-dir=.venv --exclude-dir=.git --exclude-dir=__pycache__ --exclude='*.pyc' || true
```

Expected:

```text
All tests pass.
git diff --check has no output.
safety grep has no output.
```

---

## 12. Deployment Note

After implementation, deploy with a new Stage 1.5D output root and new Stage 1.5F root. Do not reuse the current `7d_detail_retry_scheduler_starvation_hotfix` root for formal evidence after this new hotfix, because scheduler semantics and manifest audit semantics changed.

Suggested new root suffix:

```text
7d_detail_degraded_retry_cadence_fallback_hotfix
```

The 2026-07-10 `d083...` event remains recovery-validation only.
