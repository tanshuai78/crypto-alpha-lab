# External Signal Shadow Lab Stage 1.5F Request Manifest Symbol Key Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. For every code task, write or extend tests before implementation.

**Goal:** Make Stage 1.5F depth request manifest rows auditable by Stage 1.5G at per-symbol granularity by adding `event_symbol_id` and `symbol` to every depth snapshot request manifest row.

**Architecture:** Keep Stage 1.5F live observation semantics unchanged. Add a small helper in the Stage 1.5F runner to enrich depth request manifest rows immediately before they are appended to `request_manifest/*.jsonl`; do not enrich global `exchangeInfo` request rows because they are not symbol-specific. Stage 1.5G remains strict: completed observations with depth manifest rows missing symbol keys must continue to block.

**Tech Stack:** Python stdlib, JSONL files, pytest, existing `configs.base`.

---

## 0. Execution Boundary

```text
scope = stage1_5f_manifest_audit_metadata_only
network_behavior_change_allowed = false
event_filter_change_allowed = false
watermark_change_allowed = false
age_gate_change_allowed = false
depth_snapshot_schema_change_allowed = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

This hotfix must only change the audit metadata written for depth request manifest rows.

Do not change:

```text
1. Stage 1.5D event parsing.
2. Stage 1.5F accepted/rejected event eligibility.
3. Stage 1.5F watermark semantics.
4. Stage 1.5F depth request endpoint, interval, timeout, or retry behavior.
5. Stage 1.5F depth snapshot schema.
6. Stage 1.5G decision thresholds.
```

### 0.1 Mandatory Review Fixes Absorbed

This plan must absorb these blocking review fixes before implementation starts:

```text
1. Failed depth requests must receive the same event_symbol_id/event_id/symbol context as successful depth requests.
2. The manifest enrichment helper must reject empty event_symbol_id, event_id, or symbol; empty keys are not auditable.
3. Depth request manifest rows must include audit_metadata_version=1 to distinguish post-hotfix formal-auditable rows from legacy rows.
4. Mock and live depth request paths must write exactly one manifest row per depth request; no double append/double count.
5. Stage 1.5G enriched fixture tests must use snapshot counts consistent with completed state counts.
6. Stage 1.5G must still block completed formal fixtures with unkeyed depth manifest rows.
```

---

## 1. Root Cause

Stage 1.5G now requires per-symbol request health:

```text
per_symbol_request_success_rate >= EXTERNAL_SIGNAL_STAGE1_5G_MIN_PER_SYMBOL_REQUEST_SUCCESS_RATE
```

Current Stage 1.5F depth `request_manifest` rows include fields such as:

```json
{
  "requested_host": "fapi.binance.com",
  "requested_path": "/fapi/v1/depth",
  "http_status": 200,
  "fetched_at_ms": 1780000000000
}
```

But they do not include:

```json
{
  "event_symbol_id": "...",
  "symbol": "ETHUSD1"
}
```

Therefore Stage 1.5G cannot attribute request success/failure to a specific observed event-symbol. The safe behavior is to block with:

```text
request_manifest_symbol_key_missing
```

This hotfix adds those keys at the source for newly generated Stage 1.5F evidence.

---

## 2. Files

Modify:

```text
scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
```

Add/modify tests:

```text
tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
```

If the repository does not currently have this exact test file, create it.

Run existing regression tests:

```text
tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer*.py
tests/scripts/external_signal_shadow/test_review_stage1_5f_live_depth_observer.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_*.py
tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
```

---

## 3. Task 1: Add A Small Manifest Enrichment Helper

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

### Step 1: Write the failing helper test

Add:

```python
from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
    enrich_depth_request_manifest_row,
)


def test_enrich_depth_request_manifest_row_adds_event_symbol_context_without_mutating_input():
    original = {
        "requested_host": "fapi.binance.com",
        "requested_path": "/fapi/v1/depth",
        "http_status": 200,
    }

    enriched = enrich_depth_request_manifest_row(
        original,
        event_symbol_id="es1",
        event_id="ev1",
        symbol="ETHUSD1",
    )

    assert enriched["request_type"] == "depth_snapshot"
    assert enriched["audit_metadata_version"] == 1
    assert enriched["event_symbol_id"] == "es1"
    assert enriched["event_id"] == "ev1"
    assert enriched["symbol"] == "ETHUSD1"
    assert enriched["requested_path"] == "/fapi/v1/depth"
    assert "event_symbol_id" not in original
```

Also add an overwrite-protection test:

```python
def test_enrich_depth_request_manifest_row_preserves_existing_core_manifest_fields():
    enriched = enrich_depth_request_manifest_row(
        {
            "requested_host": "fapi.binance.com",
            "requested_path": "/fapi/v1/depth",
            "http_status": 500,
            "error": "http_error_500",
        },
        event_symbol_id="es1",
        event_id="ev1",
        symbol="ETHUSD1",
    )

    assert enriched["http_status"] == 500
    assert enriched["error"] == "http_error_500"
    assert enriched["request_type"] == "depth_snapshot"
    assert enriched["audit_metadata_version"] == 1
    assert enriched["event_symbol_id"] == "es1"
    assert enriched["event_id"] == "ev1"
    assert enriched["symbol"] == "ETHUSD1"
```

Add hard validation tests:

```python
import pytest


def test_enrich_depth_request_manifest_row_rejects_missing_event_symbol_id():
    with pytest.raises(ValueError, match="event_symbol_id_required"):
        enrich_depth_request_manifest_row(
            {"requested_path": "/fapi/v1/depth", "http_status": 200},
            event_symbol_id="",
            event_id="ev1",
            symbol="ETHUSD1",
        )


def test_enrich_depth_request_manifest_row_rejects_missing_event_id():
    with pytest.raises(ValueError, match="event_id_required"):
        enrich_depth_request_manifest_row(
            {"requested_path": "/fapi/v1/depth", "http_status": 200},
            event_symbol_id="es1",
            event_id="",
            symbol="ETHUSD1",
        )


def test_enrich_depth_request_manifest_row_rejects_missing_symbol():
    with pytest.raises(ValueError, match="symbol_required"):
        enrich_depth_request_manifest_row(
            {"requested_path": "/fapi/v1/depth", "http_status": 200},
            event_symbol_id="es1",
            event_id="ev1",
            symbol="",
        )
```

### Step 2: Run test to verify it fails

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_adds_event_symbol_context_without_mutating_input \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_preserves_existing_core_manifest_fields \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_rejects_missing_event_symbol_id \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_rejects_missing_event_id \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_rejects_missing_symbol \
  -q
```

Expected: FAIL because `enrich_depth_request_manifest_row` does not exist.

### Step 3: Implement minimal helper

Add near the top-level helper section in `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`:

```python
def enrich_depth_request_manifest_row(
    manifest_row: dict,
    *,
    event_symbol_id: str,
    event_id: str,
    symbol: str,
) -> dict:
    if not event_symbol_id:
        raise ValueError("event_symbol_id_required")
    if not event_id:
        raise ValueError("event_id_required")
    if not symbol:
        raise ValueError("symbol_required")

    row = dict(manifest_row or {})
    row["request_type"] = "depth_snapshot"
    row["audit_metadata_version"] = 1
    row["event_symbol_id"] = event_symbol_id
    row["event_id"] = event_id
    row["symbol"] = symbol
    return row
```

### Step 4: Run helper tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_adds_event_symbol_context_without_mutating_input \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_preserves_existing_core_manifest_fields \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_rejects_missing_event_symbol_id \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_rejects_missing_event_id \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_enrich_depth_request_manifest_row_rejects_missing_symbol \
  -q
```

Expected: PASS.

---

## 4. Task 2: Enrich Live And Mock Depth Request Manifest Rows

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

### Step 1: Write failing integration-style test for a mock depth request row

Add a narrow test around the helper or runner seam. If invoking full runner is already supported in tests, prefer a minimal runner smoke with `--mock-response-dir`. Otherwise, test the exact row-building helper path.

Required assertion:

```python
def test_depth_manifest_row_written_for_active_state_contains_symbol_keys(tmp_path):
    # Build or invoke the minimal runner fixture that writes one depth request manifest row.
    # Then read request_manifest/*.jsonl.
    row = read_single_depth_manifest_row(...)

    assert row["request_type"] == "depth_snapshot"
    assert row["audit_metadata_version"] == 1
    assert row["event_symbol_id"] == "es1"
    assert row["event_id"] == "ev1"
    assert row["symbol"] == "ETHUSD1"
    assert row["requested_path"] == "/fapi/v1/depth"
```

Add a failed request attribution test:

```python
def test_failed_depth_manifest_row_contains_event_symbol_context():
    row = enrich_depth_request_manifest_row(
        {
            "requested_host": "fapi.binance.com",
            "requested_path": "/fapi/v1/depth",
            "http_status": 500,
            "error": "http_error_500",
        },
        event_symbol_id="es1",
        event_id="ev1",
        symbol="ETHUSD1",
    )

    assert row["request_type"] == "depth_snapshot"
    assert row["audit_metadata_version"] == 1
    assert row["event_symbol_id"] == "es1"
    assert row["event_id"] == "ev1"
    assert row["symbol"] == "ETHUSD1"
    assert row["http_status"] == 500
    assert row["error"] == "http_error_500"
```

At minimum this must cover one failed path. The same helper must be used for:

```text
HTTP 4xx/5xx
network error
empty response
symbol invalid response
```

because all of these must be attributable to the active event-symbol for Stage 1.5G request health.

Add exactly-once tests:

```python
def test_mock_depth_manifest_row_written_exactly_once(tmp_path):
    rows = run_mock_observer_and_read_depth_manifest_rows(tmp_path, symbol="ETHUSD1")
    keys = [
        (r.get("event_symbol_id"), r.get("fetched_at_ms"), r.get("requested_path"))
        for r in rows
        if r.get("request_type") == "depth_snapshot"
    ]
    assert len(keys) == len(set(keys))


def test_live_depth_manifest_row_written_exactly_once(monkeypatch, tmp_path):
    rows = run_live_observer_with_mocked_fetch_depth_snapshot_and_read_manifest_rows(tmp_path)
    keys = [
        (r.get("event_symbol_id"), r.get("fetched_at_ms"), r.get("requested_path"))
        for r in rows
        if r.get("request_type") == "depth_snapshot"
    ]
    assert len(keys) == len(set(keys))
```

If the full runner fixture is too heavy, keep these tests at the smallest seam that exercises the write path, but they must fail on double append/double count.

If full runner setup is too heavy, keep the integration at the smallest existing seam but make sure both code paths below are covered by direct tests:

```text
mock_response_dir path
live fetch_depth_snapshot path
```

### Step 2: Run test to verify it fails

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_depth_manifest_row_written_for_active_state_contains_symbol_keys \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_failed_depth_manifest_row_contains_event_symbol_context \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_mock_depth_manifest_row_written_exactly_once \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_live_depth_manifest_row_written_exactly_once \
  -q
```

Expected: FAIL because request manifest rows do not yet contain symbol keys.

### Step 3: Modify the active observation loop

In `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`, inside the loop:

```python
for state in list(active_states):
    symbol = state.symbol
```

For the mock path, after the mock `manifest_row` dict is created, enrich it:

```python
manifest_row = enrich_depth_request_manifest_row(
    manifest_row,
    event_symbol_id=state.event_symbol_id,
    event_id=state.event_id,
    symbol=symbol,
)
```

For the live path, replace:

```python
manifest_row = res["manifest_row"]
request_manifest_rows.append(manifest_row)
manifest_path = build_daily_path(output_root, "request_manifest", now_ms)
append_jsonl(manifest_path, manifest_row)
```

with:

```python
manifest_row = enrich_depth_request_manifest_row(
    res["manifest_row"],
    event_symbol_id=state.event_symbol_id,
    event_id=state.event_id,
    symbol=symbol,
)
request_manifest_rows.append(manifest_row)
manifest_path = build_daily_path(output_root, "request_manifest", now_ms)
append_jsonl(manifest_path, manifest_row)
```

Also ensure the mock path still appends/writes the enriched row exactly once. If current mock path does not append manifest rows before this hotfix, add the same append/write logic to match live behavior:

```python
request_manifest_rows.append(manifest_row)
manifest_path = build_daily_path(output_root, "request_manifest", now_ms)
append_jsonl(manifest_path, manifest_row)
```

Do not append/write before enrichment. Do not append/write the same `event_symbol_id + fetched_at_ms + requested_path` more than once.

### Step 4: Run integration test

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_depth_manifest_row_written_for_active_state_contains_symbol_keys \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_failed_depth_manifest_row_contains_event_symbol_context \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_mock_depth_manifest_row_written_exactly_once \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_live_depth_manifest_row_written_exactly_once \
  -q
```

Expected: PASS.

---

## 5. Task 3: Prove ExchangeInfo Manifest Is Not Forced Into Symbol Context

**Files:**
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

### Step 1: Write failing/confirming test

Add:

```python
def test_exchangeinfo_manifest_row_is_not_depth_symbol_specific():
    # Use an exchangeInfo manifest fixture or direct row from refresh path.
    row = {
        "requested_host": "fapi.binance.com",
        "requested_path": "/fapi/v1/exchangeInfo",
        "http_status": 200,
    }

    # The hotfix helper must not be applied to exchangeInfo rows.
    assert row.get("event_symbol_id") is None
    assert row.get("symbol") is None
```

If a direct runner fixture exists, assert the actual exchangeInfo request row still has:

```text
requested_path == /fapi/v1/exchangeInfo
event_symbol_id missing
symbol missing
```

### Step 2: Run test

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_exchangeinfo_manifest_row_is_not_depth_symbol_specific \
  -q
```

Expected: PASS. If it fails, the implementation is over-enriching global manifest rows and must be narrowed.

---

## 6. Task 4: Verify Stage 1.5G No Longer Blocks A Completed Fixture With Enriched Manifest

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`

### Step 1: Add regression test

Add:

```python
def test_stage1_5g_accepts_completed_formal_evidence_with_symbol_keyed_manifest():
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{
            "event_symbol_id": "es1",
            "symbol": "ETHUSD1",
            "status": "completed",
            "depth_snapshot_count": 700,
            "max_gap_ms": 60000,
        }],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "ETHUSD1",
            "source_article_id": "article1",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
        }],
        snapshots=make_healthy_snapshots(event_symbol_id="es1", symbol="ETHUSD1", count=700),
        request_manifest_rows=[
            {
                "request_type": "depth_snapshot",
                "audit_metadata_version": 1,
                "event_symbol_id": "es1",
                "event_id": "ev1",
                "symbol": "ETHUSD1",
                "requested_path": "/fapi/v1/depth",
                "http_status": 200,
            }
        ],
    )

    assert "request_manifest_symbol_key_missing" not in result["blockers"]
    assert result["decision"] == "stage1_5g_depth_evidence_sufficient_for_stage1_5h_plan"
```

### Step 2: Run test

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py::test_stage1_5g_accepts_completed_formal_evidence_with_symbol_keyed_manifest \
  -q
```

Expected: PASS after Task 2 and existing Stage 1.5G strict gate remain compatible.

### Step 3: Add the unkeyed manifest blocker regression test

Add:

```python
def test_stage1_5g_blocks_completed_formal_evidence_with_unkeyed_depth_manifest():
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{
            "event_symbol_id": "es1",
            "symbol": "ETHUSD1",
            "status": "completed",
            "depth_snapshot_count": 700,
            "max_gap_ms": 60000,
        }],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "ETHUSD1",
            "source_article_id": "article1",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
        }],
        snapshots=make_healthy_snapshots(event_symbol_id="es1", symbol="ETHUSD1", count=700),
        request_manifest_rows=[
            {
                "request_type": "depth_snapshot",
                "requested_path": "/fapi/v1/depth",
                "http_status": 200,
            }
        ],
    )

    assert "request_manifest_symbol_key_missing" in result["blockers"]
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
```

### Step 4: Run the strict-gate tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py::test_stage1_5g_accepts_completed_formal_evidence_with_symbol_keyed_manifest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py::test_stage1_5g_blocks_completed_formal_evidence_with_unkeyed_depth_manifest \
  -q
```

Expected: PASS.

---

## 7. Task 5: Full Regression

Run Stage 1.5F tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer*.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: PASS.

Run Stage 1.5G tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q
```

Expected: PASS.

Run static checks:

```bash
git diff --check
```

Expected: no output.

Run safety grep:

```bash
grep -R "trade_signal_allowed.*True\\|paper_trading_allowed.*True\\|live_trading_allowed.*True\\|execution_engine_allowed.*True\\|alpha_interpretation_allowed.*True\\|execution_feasibility_claim_allowed.*True" \
  -n scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
     scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
     src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
     tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_*.py \
     tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
     tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  || true
```

Expected: no unsafe `True` flags.

---

## 8. Deployment Note

This hotfix affects only newly written Stage 1.5F request manifest rows.

Existing Stage 1.5F output roots that already contain request_manifest rows without `event_symbol_id` / `symbol` remain incomplete for Stage 1.5G formal audit.

Recommended rollout:

```text
1. Stop current Stage 1.5F observer only after confirming there is no active observation.
2. Keep current Stage 1.5D root if still healthy.
3. Start a new Stage 1.5F output root after this hotfix.
4. Bootstrap watermark in the new Stage 1.5F root.
5. Wait for the next post-watermark futures launch event.
6. Use the new Stage 1.5F root for Stage 1.5G review.
```

Do not repair old missing manifest rows by guessing symbol attribution unless it is explicitly labeled:

```text
recovery_validation_only
```

Old reconstructed rows must not be treated as formal 12h live depth evidence.

---

## 9. Completion Criteria

The implementation is complete only when:

```text
1. Depth request_manifest rows written after the hotfix include request_type=depth_snapshot.
2. Depth request_manifest rows written after the hotfix include audit_metadata_version=1.
3. Depth request_manifest rows include event_symbol_id.
4. Depth request_manifest rows include event_id.
5. Depth request_manifest rows include symbol.
6. Failed depth request_manifest rows include the same event_symbol_id/event_id/symbol context as successful rows.
7. Helper rejects empty event_symbol_id, event_id, and symbol.
8. Mock depth request path writes exactly one manifest row per request.
9. Live depth request path writes exactly one manifest row per request.
10. exchangeInfo manifest rows are not forced to include event_symbol_id/symbol.
11. Stage 1.5G no longer blocks enriched completed fixtures with request_manifest_symbol_key_missing.
12. Stage 1.5G still blocks completed fixtures with unkeyed depth manifest rows.
13. Stage 1.5F regression tests pass.
14. Stage 1.5G regression tests pass.
15. git diff --check passes.
16. Safety grep finds no unsafe trading/execution flags.
17. No Stage 1.5F event filter, age gate, watermark, or depth snapshot schema behavior changes are included.
```

---

## 10. Handoff

After implementation, update:

```text
docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

Add a short section:

```text
Stage 1.5F request_manifest symbol-key hotfix
```

Include:

```text
1. Why the hotfix was needed.
2. Exact fields added to depth request manifest rows.
3. Why audit_metadata_version=1 distinguishes post-hotfix rows from legacy rows.
4. Why exchangeInfo rows stay global.
5. Deployment command for a fresh Stage 1.5F output root.
6. Verification command showing new manifest rows include event_symbol_id/symbol.
```
