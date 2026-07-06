# External Signal Shadow Lab Stage 1.5G Live Depth Evidence Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. For every code task, write or extend tests before implementation.

**Date:** 2026-07-06
**Status:** implementation_plan_draft
**Design:** `docs/designs/2026-07-06-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review-design_CN.md`
**Goal:** Build an offline Stage 1.5G reviewer that audits Stage 1.5F 12h live depth evidence and decides whether the evidence is invalid, observation-only, or sufficient only for writing a Stage 1.5H shadow execution simulator design.

**Architecture:** Add a new research module under `src/research/external_signal_shadow/` that loads a Stage 1.5F output root, validates watermark/evidence-label integrity, recomputes coverage and per-symbol health, validates raw snapshots, computes depth quality distributions, and writes a JSON summary plus Chinese markdown review. Keep Stage 1.5G separate from the existing Stage 1.5F collector and review generator.

**Tech Stack:** Python stdlib, dataclasses, JSON/JSONL files, existing `configs.base`, pytest.

---

## 0. Execution Boundary

```text
scope = offline_evidence_review_only
input_stage = stage1_5f_live_depth_observer_output_root
public_readonly = true
new_network_requests_allowed = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

Stage 1.5G can output:

```text
stage1_5g_not_ready_no_completed_observation
stage1_5g_depth_evidence_invalid
stage1_5g_depth_evidence_observation_only
stage1_5g_depth_evidence_sufficient_for_stage1_5h_plan
```

Stage 1.5G cannot output:

```text
execution_feasibility_proven
alpha_confirmed
paper_ready
live_ready
```

Implementation must not modify Stage 1.5F live collection semantics.

### 0.1 Mandatory Review Fixes Absorbed

This plan must absorb these blocking review fixes before implementation starts:

```text
1. Loader must treat JSONL parse errors as evidence-chain blockers, not silent skips.
2. Missing or unreadable watermark.json must produce stage1_5g_depth_evidence_invalid, not not_ready.
3. Accepted event-symbols with no physical depth snapshot file must not crash loader; they remain in the bundle and fail coverage via depth_snapshot_count = 0.
4. coverage expected count must come from 1.5F config snapshot if present, then configs/base.py; no hardcoded 720/60s.
5. summary, observer_state, accepted events, snapshots, and request_manifest must be cross-validated.
6. sufficient_for_stage1_5h_plan requires completed formal evidence, not merely accepted evidence.
7. completed observations without request_manifest are invalid because request health cannot be audited.
8. CLI must treat Stage 1.5F output root as read-only input; default 1.5G outputs go under data/external_signal_shadow/stage1_5g/reviews/<run_id>/.
9. 1-minute static depth/slippage is a sampled lower-bound proxy, not realized execution capacity.
```

---

## 1. Files And Modules

Create:

```text
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py
tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
```

Modify:

```text
configs/base.py
```

Do not modify:

```text
scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_*.py
```

unless a test proves a Stage 1.5F output field contract is missing. If that happens, stop and write a separate hotfix plan.

---

## 2. Task 1: Add Stage 1.5G Config Constants

**Files:**
- Modify: `configs/base.py`
- Create: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py`

**Step 1: Write failing config tests**

Add tests:

```python
from configs import base


def test_stage1_5g_config_constants_exist_and_are_observation_only():
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_REQUEST_SUCCESS_RATE == 0.98
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_PER_SYMBOL_REQUEST_SUCCESS_RATE == 0.98
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_SNAPSHOT_COVERAGE_RATIO == 0.95
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_SLIPPAGE_TEST_NOTIONAL_USDT == 500.0
    assert base.RISK_LIVE_TRADING_ENABLED is False


def test_stage1_5g_thresholds_are_safe_ranges():
    assert 0.0 < base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_HEALTHY_WINDOW_RATIO <= 1.0
    assert 0.0 <= base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_NULL_RATIO < 0.05
    assert 0.0 <= base.EXTERNAL_SIGNAL_STAGE1_5G_MAX_DUPLICATE_SNAPSHOT_RATIO < 0.10
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_EVENT_FAMILY_SAMPLE_REQUIRED >= 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5G_MIN_SOURCE_ARTICLES_REQUIRED >= 2
```

**Step 2: Run test and verify it fails**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  -q
```

Expected: FAIL because constants do not exist.

**Step 3: Add constants**

Add a new section after Stage 1.5F constants:

```python
# ─── External Signal Shadow Lab Stage 1.5G: Live Depth Evidence Review ───

EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION = 1
EXTERNAL_SIGNAL_STAGE1_5G_MIN_REQUEST_SUCCESS_RATE = 0.98
EXTERNAL_SIGNAL_STAGE1_5G_MIN_PER_SYMBOL_REQUEST_SUCCESS_RATE = 0.98
EXTERNAL_SIGNAL_STAGE1_5G_MIN_SNAPSHOT_COVERAGE_RATIO = 0.95
EXTERNAL_SIGNAL_STAGE1_5G_MAX_SNAPSHOT_GAP_MULTIPLIER = 5
EXTERNAL_SIGNAL_STAGE1_5G_MAX_SNAPSHOT_GAP_FLOOR_MS = 10 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5G_SLIPPAGE_TEST_NOTIONAL_USDT = 500.0
EXTERNAL_SIGNAL_STAGE1_5G_MAX_SPREAD_BPS_P50 = 30.0
EXTERNAL_SIGNAL_STAGE1_5G_MAX_SPREAD_BPS_P95 = 100.0
EXTERNAL_SIGNAL_STAGE1_5G_MAX_BUY_SLIPPAGE_BPS_P50 = 50.0
EXTERNAL_SIGNAL_STAGE1_5G_MAX_SELL_SLIPPAGE_BPS_P50 = 50.0
EXTERNAL_SIGNAL_STAGE1_5G_MAX_BUY_SLIPPAGE_BPS_P95 = 150.0
EXTERNAL_SIGNAL_STAGE1_5G_MAX_SELL_SLIPPAGE_BPS_P95 = 150.0
EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_BID_DEPTH_USDT_P50 = 500.0
EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_ASK_DEPTH_USDT_P50 = 500.0
EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_BID_DEPTH_USDT_P05 = 250.0
EXTERNAL_SIGNAL_STAGE1_5G_MIN_TOP_ASK_DEPTH_USDT_P05 = 250.0
EXTERNAL_SIGNAL_STAGE1_5G_MIN_HEALTHY_WINDOW_RATIO = 0.90
EXTERNAL_SIGNAL_STAGE1_5G_MAX_NULL_RATIO = 0.01
EXTERNAL_SIGNAL_STAGE1_5G_MAX_DUPLICATE_SNAPSHOT_RATIO = 0.05
EXTERNAL_SIGNAL_STAGE1_5G_MIN_EVENT_FAMILY_SAMPLE_REQUIRED = 3
EXTERNAL_SIGNAL_STAGE1_5G_MIN_SOURCE_ARTICLES_REQUIRED = 2
```

**Step 4: Run test and verify it passes**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  -q
```

Expected: PASS.

---

## 3. Task 2: Create Loader And Fixture Helpers

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Create: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py`

**Step 1: Write failing loader tests**

Test should create a temp Stage 1.5F root with:

```text
live_depth_observer_summary.json
watermark.json
observer_state.jsonl
events_accepted/20260706.jsonl
events_rejected/20260706.jsonl
depth_snapshots/20260706/{event_symbol_id}.jsonl
request_manifest/20260706.jsonl
heartbeat/20260706.jsonl
```

Assertions:

```python
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import load_stage1_5g_inputs


def test_load_stage1_5g_inputs_reads_stage1_5f_output_root(tmp_path):
    root = make_stage1_5f_fixture_root(tmp_path)
    bundle = load_stage1_5g_inputs(root)

    assert bundle.summary["decision"] == "stage1_5f_observer_depth_evidence_collected"
    assert bundle.watermark["watermark_version"] == 1
    assert len(bundle.accepted_events) == 1
    assert len(bundle.snapshots) == 3
    assert len(bundle.states) == 1
    assert len(bundle.request_manifest_rows) == 3
```

Also test missing optional dirs:

```python
def test_load_stage1_5g_inputs_tolerates_missing_rejected_and_manifest_dirs(tmp_path):
    root = make_minimal_stage1_5f_fixture_root(tmp_path)
    bundle = load_stage1_5g_inputs(root)
    assert bundle.rejected_events == []
    assert bundle.request_manifest_rows == []
```

Add tests for mandatory edge cases:

```python
def test_loader_missing_snapshot_file_keeps_state_and_empty_snapshots(tmp_path):
    root = make_stage1_5f_fixture_root_without_snapshot_file(tmp_path)
    bundle = load_stage1_5g_inputs(root)

    assert len(bundle.accepted_events) == 1
    assert len(bundle.states) == 1
    assert bundle.states[0]["event_symbol_id"] == "es1"
    assert bundle.states[0]["depth_snapshot_count"] == 0
    assert bundle.snapshots == []


def test_loader_jsonl_parse_error_blocks_review(tmp_path):
    root = make_stage1_5f_fixture_root_with_corrupt_snapshot_jsonl(tmp_path)
    bundle = load_stage1_5g_inputs(root)

    assert bundle.loader_blockers == ["jsonl_parse_error"]
    assert bundle.parse_error_count == 1
    assert bundle.total_jsonl_line_count > 0


def test_loader_missing_watermark_records_blocker_not_not_ready(tmp_path):
    root = make_stage1_5f_fixture_root(tmp_path)
    (root / "watermark.json").unlink()

    bundle = load_stage1_5g_inputs(root)

    assert bundle.watermark == {}
    assert "missing_or_unreadable_watermark" in bundle.loader_blockers
```

**Step 2: Run tests and verify they fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  -q
```

Expected: FAIL because module/function does not exist.

**Step 3: Implement minimal loader**

Create dataclass:

```python
@dataclass(frozen=True)
class Stage1_5GInputBundle:
    output_root: Path
    summary: dict
    watermark: dict
    states: list[dict]
    accepted_events: list[dict]
    rejected_events: list[dict]
    snapshots: list[dict]
    request_manifest_rows: list[dict]
    heartbeat_rows: list[dict]
    loader_blockers: list[str]
    loader_warnings: list[str]
    parse_error_count: int
    total_jsonl_line_count: int
```

Implement:

```python
def load_json(path: Path) -> dict
def load_jsonl_glob(pattern: str) -> list[dict]
def load_stage1_5g_inputs(output_root: str | Path) -> Stage1_5GInputBundle
```

Required behavior:

```text
summary is required. Missing summary should record missing_or_unreadable_summary and cause CLI failure.
watermark is required for valid review. Missing watermark should record missing_or_unreadable_watermark and later decision invalid.
JSONL parse errors must record jsonl_parse_error in loader_blockers; they cannot be silent skips.
Corrupt lines may be omitted from parsed rows, but parse_error_count and total_jsonl_line_count must be preserved for decision/integrity.
Missing optional dirs return empty lists.
Accepted/state event-symbols with no matching snapshot file must remain represented and fail later by coverage count 0.
No network calls.
```

**Step 4: Run tests and verify they pass**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  -q
```

Expected: PASS.

---

## 4. Task 3: Evidence Label And Watermark Integrity Validator

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Create: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`

**Step 1: Write failing tests**

Required tests:

```python
def test_validator_accepts_announcement_and_launch_time_post_watermark():
    event = {
        "event_symbol_id": "es1",
        "symbol": "DATAIPUSDT",
        "source_article_id": "a1",
        "evidence_label": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
    }
    result = validate_evidence_integrity([event], watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1})
    assert result.blockers == []
    assert result.evidence_label_counts["announcement_and_launch_time"] == 1


def test_validator_blocks_missing_evidence_label():
    event = {"event_symbol_id": "es1", "watermark_max_seen_detected_at_ms": 1000, "watermark_version": 1}
    result = validate_evidence_integrity([event], watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1})
    assert "missing_evidence_label" in result.blockers


def test_recovery_validation_only_cannot_count_as_formal_evidence():
    event = {
        "event_symbol_id": "es1",
        "symbol": "ETHUSD1",
        "evidence_label": "recovery_validation_only",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
    }
    result = validate_evidence_integrity([event], watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1})
    assert result.formal_announcement_and_launch_count == 0
    assert result.evidence_label_counts["recovery_validation_only"] == 1
```

Also test watermark mismatch:

```python
def test_validator_blocks_watermark_mismatch():
    event = {"event_symbol_id": "es1", "evidence_label": "announcement_and_launch_time", "watermark_max_seen_detected_at_ms": 999, "watermark_version": 1}
    result = validate_evidence_integrity([event], watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1})
    assert "watermark_max_seen_detected_at_ms_mismatch" in result.blockers
```

Add cross-validation tests:

```python
def test_validator_blocks_missing_watermark():
    result = validate_evidence_integrity(
        accepted_events=[{"event_symbol_id": "es1", "evidence_label": "announcement_and_launch_time"}],
        watermark={},
        states=[],
        snapshots=[],
    )
    assert "missing_or_unreadable_watermark" in result.blockers


def test_validator_blocks_summary_state_count_mismatch():
    result = validate_evidence_integrity(
        accepted_events=[{"event_symbol_id": "es1", "evidence_label": "announcement_and_launch_time", "watermark_max_seen_detected_at_ms": 1000, "watermark_version": 1}],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "active"}],
        snapshots=[],
        summary={"completed_observation_count": 1},
    )
    assert "summary_state_count_mismatch" in result.blockers


def test_validator_blocks_completed_state_without_snapshots():
    result = validate_evidence_integrity(
        accepted_events=[{"event_symbol_id": "es1", "evidence_label": "announcement_and_launch_time", "watermark_max_seen_detected_at_ms": 1000, "watermark_version": 1}],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        snapshots=[],
        summary={"completed_observation_count": 1},
    )
    assert "completed_state_without_snapshots" in result.blockers
```

**Step 2: Run tests and verify they fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  -q
```

Expected: FAIL.

**Step 3: Implement integrity validator**

Add:

```python
VALID_EVIDENCE_LABELS = {
    "announcement_and_launch_time",
    "launch_time_only",
    "recovery_validation_only",
}

@dataclass(frozen=True)
class EvidenceIntegrityResult:
    blockers: list[str]
    warnings: list[str]
    evidence_label_counts: dict[str, int]
    formal_announcement_and_launch_count: int
    formal_completed_event_symbol_ids: set[str]
```

Function:

```python
def validate_evidence_integrity(
    accepted_events: list[dict],
    watermark: dict,
    states: list[dict] | None = None,
    snapshots: list[dict] | None = None,
    summary: dict | None = None,
) -> EvidenceIntegrityResult
```

Rules:

```text
missing watermark -> blocker missing_or_unreadable_watermark
missing evidence_label -> blocker
unknown evidence_label -> blocker
accepted event watermark_version mismatch -> blocker
accepted event watermark_max_seen_detected_at_ms mismatch -> blocker
recovery_validation_only and launch_time_only count as non-formal evidence
summary.completed_observation_count must equal count(state.status == completed)
accepted event_symbol_id must join to observer_state event_symbol_id before formal evidence can count
completed state must have at least one matching snapshot row
formal_announcement_and_launch_count only includes event-symbols with:
  accepted evidence_label == announcement_and_launch_time
  AND state.status == completed
  AND matching snapshots exist
```

**Step 4: Run tests and verify they pass**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  -q
```

Expected: PASS.

---

## 5. Task 4: Coverage And Per-Symbol Request Health Metrics

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Create: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py`

**Step 1: Write failing coverage tests**

Tests:

```python
def test_compute_expected_snapshot_count_from_summary_config_snapshot():
    summary = {
        "observation_window_ms": 3_600_000,
        "snapshot_interval_ms": 30_000,
        "min_snapshot_coverage_ratio": 0.90,
    }
    metrics = compute_coverage_metrics(
        states=[{"event_symbol_id": "es1", "depth_snapshot_count": 108, "max_gap_ms": 120000}],
        request_manifest_rows=[],
        summary=summary,
    )
    assert metrics["expected_snapshot_count"] == 120
    assert metrics["min_snapshot_count_required"] == 108
    assert metrics["snapshot_interval_ms"] == 30000


def test_coverage_blocks_when_observation_config_missing(monkeypatch):
    monkeypatch.delattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS", raising=False)
    monkeypatch.delattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC", raising=False)

    metrics = compute_coverage_metrics(states=[], request_manifest_rows=[], summary={})
    assert "missing_stage1_5f_observation_config" in metrics["blockers"]


def test_coverage_fails_when_per_symbol_request_success_rate_is_low():
    rows = [
        {"event_symbol_id": "es1", "symbol": "A", "http_status": 200},
        {"event_symbol_id": "es1", "symbol": "A", "http_status": 500},
    ]
    metrics = compute_coverage_metrics(
        states=[{"event_symbol_id": "es1", "depth_snapshot_count": 684, "max_gap_ms": 300000}],
        request_manifest_rows=rows,
        summary={"observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
    )
    assert metrics["per_symbol_request_success_rate_min"] == 0.5
    assert "per_symbol_request_success_rate_below_threshold" in metrics["blockers"]
```

**Step 2: Run tests and verify they fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py::test_compute_expected_snapshot_count_from_stage1_5f_config \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py::test_coverage_fails_when_per_symbol_request_success_rate_is_low \
  -q
```

Expected: FAIL.

**Step 3: Implement coverage metrics**

Function:

```python
def resolve_observation_config(summary: dict, states: list[dict]) -> tuple[dict, list[str]]
def compute_coverage_metrics(states: list[dict], request_manifest_rows: list[dict], summary: dict | None = None) -> dict
```

Required:

```text
Observation config source priority:
  1. summary config snapshot fields: observation_window_ms, snapshot_interval_ms, min_snapshot_coverage_ratio
  2. observer_state config snapshot fields, if present
  3. configs/base.py EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS and EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC
  4. otherwise blocker = missing_stage1_5f_observation_config
expected_snapshot_count = floor(observation_window_ms / snapshot_interval_ms)
min_snapshot_count_required = floor(expected * 1.5G coverage ratio)
computed_max_gap_ms = max(1.5G gap multiplier * interval, 1.5G gap floor)
coverage_ratio per state = depth_snapshot_count / expected
per-symbol request success computed using event_symbol_id when available, otherwise symbol
global request success computed separately
blockers emitted for count/gap/per-symbol/global failures
Do not hardcode 720 or 60000 in implementation.
```

**Step 4: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  -q
```

Expected: PASS for coverage tests; later tests may still fail as they are added.

---

## 6. Task 5: Raw Snapshot Integrity Validator

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`

**Step 1: Write failing raw integrity tests**

Required tests:

```python
def test_raw_snapshot_integrity_blocks_crossed_book():
    snapshots = [{"event_symbol_id": "es1", "symbol": "A", "fetched_at_ms": 1, "best_bid": 101, "best_ask": 100, "mid_price": 100.5, "spread_bps": -1}]
    result = validate_raw_snapshot_integrity(snapshots)
    assert "invalid_book" in result.blockers


def test_raw_snapshot_integrity_blocks_non_monotonic_time_per_event_symbol():
    snapshots = [
        {"event_symbol_id": "es1", "symbol": "A", "fetched_at_ms": 2, "best_bid": 100, "best_ask": 101, "mid_price": 100.5, "spread_bps": 100},
        {"event_symbol_id": "es1", "symbol": "A", "fetched_at_ms": 1, "best_bid": 100, "best_ask": 101, "mid_price": 100.5, "spread_bps": 100},
    ]
    result = validate_raw_snapshot_integrity(snapshots)
    assert "non_monotonic_timestamp" in result.blockers


def test_raw_snapshot_integrity_blocks_symbol_event_symbol_mapping_conflict():
    snapshots = [
        {"event_symbol_id": "es1", "symbol": "A", "fetched_at_ms": 1, "best_bid": 100, "best_ask": 101, "mid_price": 100.5, "spread_bps": 100},
        {"event_symbol_id": "es1", "symbol": "B", "fetched_at_ms": 2, "best_bid": 100, "best_ask": 101, "mid_price": 100.5, "spread_bps": 100},
    ]
    result = validate_raw_snapshot_integrity(snapshots)
    assert "symbol_event_symbol_id_mapping_conflict" in result.blockers


def test_raw_snapshot_integrity_blocks_jsonl_parse_error_from_loader():
    result = validate_raw_snapshot_integrity(
        snapshots=[],
        parse_error_count=1,
        total_jsonl_line_count=100,
    )
    assert "jsonl_parse_error" in result.blockers
    assert result.jsonl_parse_error_ratio == 0.01
```

**Step 2: Run tests and verify they fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  -q
```

Expected: FAIL.

**Step 3: Implement raw integrity validation**

Add:

```python
@dataclass(frozen=True)
class RawSnapshotIntegrityResult:
    blockers: list[str]
    warnings: list[str]
    null_ratio_max: float
    jsonl_parse_error_ratio: float
    jsonl_parse_error_count: int
    duplicate_snapshot_ratio_max: float
    non_monotonic_timestamp_count: int
    invalid_book_count: int
```

Function:

```python
def validate_raw_snapshot_integrity(
    snapshots: list[dict],
    parse_error_count: int = 0,
    total_jsonl_line_count: int = 0,
) -> RawSnapshotIntegrityResult
```

Rules:

```text
best_bid <= 0 -> invalid_book
best_ask <= 0 -> invalid_book
best_bid >= best_ask -> invalid_book
mid_price <= 0 -> invalid_book
spread_bps < 0 -> invalid_book
fetched_at_ms per event_symbol_id must be monotonic increasing
same event_symbol_id cannot map to multiple symbols
null ratio across required fields must be <= config max
duplicate ratio by (event_symbol_id, fetched_at_ms, best_bid, best_ask) must be <= config max
any JSONL parse error from loader must add blocker jsonl_parse_error
jsonl_parse_error_ratio must be reported for audit
```

**Step 4: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  -q
```

Expected: PASS.

---

## 7. Task 6: Depth Quality Metrics

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py`

**Step 1: Write failing depth quality tests**

Tests:

```python
def test_depth_quality_computes_p05_p50_p95_and_capacity_ratio():
    snapshots = make_healthy_snapshots(event_symbol_id="es1", symbol="A", count=20)
    result = compute_depth_quality_metrics(snapshots)

    assert result["spread_bps_p50"] is not None
    assert result["spread_bps_p95"] is not None
    assert result["top_bid_depth_usdt_p05"] is not None
    assert result["top_ask_depth_usdt_p05"] is not None
    assert result["depth_capacity_ratio_to_risk_cap_p50"] is not None


def test_depth_quality_fails_on_low_healthy_window_ratio():
    snapshots = make_mixed_quality_snapshots(healthy=5, unhealthy=95)
    result = compute_depth_quality_metrics(snapshots)
    assert result["healthy_window_ratio"] == 0.05
    assert "healthy_window_ratio_below_threshold" in result["blockers"]
```

**Step 2: Run tests and verify they fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  -q
```

Expected: FAIL.

**Step 3: Implement metrics**

Functions:

```python
def percentile(values: list[float], pct: float) -> float | None
def compute_depth_quality_metrics(snapshots: list[dict]) -> dict
```

Metrics:

```text
spread_bps_p50 / p95
buy_slippage_bps_500usdt_p50 / p95
sell_slippage_bps_500usdt_p50 / p95
top_bid_depth_usdt_p05 / p50
top_ask_depth_usdt_p05 / p50
healthy_window_ratio
depth_capacity_ratio_to_risk_cap_p50
```

Healthy snapshot definition:

```text
spread_bps <= MAX_SPREAD_BPS_P95 threshold can be evaluated per row using MAX_SPREAD_BPS_P95
buy_slippage_bps <= MAX_BUY_SLIPPAGE_BPS_P95
sell_slippage_bps <= MAX_SELL_SLIPPAGE_BPS_P95
top_bid_depth_usdt >= MIN_TOP_BID_DEPTH_USDT_P05
top_ask_depth_usdt >= MIN_TOP_ASK_DEPTH_USDT_P05
```

**Step 4: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  -q
```

Expected: PASS.

---

## 8. Task 7: Decision Engine

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Create: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`

**Step 1: Write failing decision tests**

Required tests:

```python
def test_decision_not_ready_without_completed_observation():
    summary = {"completed_observation_count": 0, "post_watermark_events_accepted": 0}
    result = build_stage1_5g_review_summary(summary=summary, watermark={"watermark_version": 1, "max_seen_detected_at_ms": 0}, states=[], accepted_events=[], snapshots=[], request_manifest_rows=[])
    assert result["decision"] == "stage1_5g_not_ready_no_completed_observation"
    assert result["allowed_next_action"] == "continue_observation"


def test_missing_watermark_is_invalid_not_not_ready():
    summary = {"completed_observation_count": 0, "post_watermark_events_accepted": 0}
    result = build_stage1_5g_review_summary(summary=summary, watermark={}, states=[], accepted_events=[], snapshots=[], request_manifest_rows=[])
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "missing_or_unreadable_watermark" in result["blockers"]


def test_loader_parse_error_is_invalid():
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 0},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 0},
        states=[],
        accepted_events=[],
        snapshots=[],
        request_manifest_rows=[],
        loader_blockers=["jsonl_parse_error"],
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "jsonl_parse_error" in result["blockers"]


def test_launch_time_only_is_observation_only_even_with_good_depth():
    result = build_fixture_review_summary(evidence_label="launch_time_only", good_depth=True)
    assert result["decision"] == "stage1_5g_depth_evidence_observation_only"
    assert result["allowed_next_action"] == "continue_observation"


def test_recovery_validation_only_is_excluded_from_formal_evidence():
    result = build_fixture_review_summary(evidence_label="recovery_validation_only", good_depth=True)
    assert result["decision"] == "stage1_5g_depth_evidence_observation_only"
    assert result["evidence_labels"]["recovery_validation_only"] == 1
    assert result["valid_evidence_event_symbol_count"] == 0


def test_valid_single_announcement_and_launch_time_allows_only_stage1_5h_design():
    result = build_fixture_review_summary(evidence_label="announcement_and_launch_time", good_depth=True)
    assert result["decision"] == "stage1_5g_depth_evidence_sufficient_for_stage1_5h_plan"
    assert result["allowed_next_action"] == "write_stage1_5h_shadow_execution_simulator_design"
    assert result["evidence_scope"] == "single_event"
    assert result["event_family_conclusion_allowed"] is False
    assert result["trade_signal_allowed"] is False


def test_accepted_but_active_announcement_and_launch_time_does_not_trigger_sufficient():
    result = build_fixture_review_summary(
        evidence_label="announcement_and_launch_time",
        state_status="active",
        good_depth=True,
    )
    assert result["decision"] != "stage1_5g_depth_evidence_sufficient_for_stage1_5h_plan"


def test_completed_observation_without_request_manifest_is_invalid():
    result = build_fixture_review_summary(
        evidence_label="announcement_and_launch_time",
        state_status="completed",
        good_depth=True,
        request_manifest_rows=[],
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "missing_request_manifest_for_completed_observation" in result["blockers"]
```

Also test event-family scope:

```python
def test_event_family_scope_requires_three_symbols_and_two_articles():
    result = build_fixture_review_summary_with_events(
        labels=["announcement_and_launch_time", "announcement_and_launch_time", "announcement_and_launch_time"],
        source_article_ids=["a1", "a1", "a2"],
        good_depth=True,
    )
    assert result["event_family_conclusion_allowed"] is True
```

**Step 2: Run tests and verify they fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  -q
```

Expected: FAIL.

**Step 3: Implement decision engine**

Main function:

```python
def build_stage1_5g_review_summary(
    summary: dict,
    watermark: dict,
    states: list[dict],
    accepted_events: list[dict],
    snapshots: list[dict],
    request_manifest_rows: list[dict],
    output_root: str | Path | None = None,
    loader_blockers: list[str] | None = None,
) -> dict
```

Decision order:

```text
1. loader_blockers present -> invalid
2. missing/unreadable watermark -> invalid
3. evidence integrity blockers -> invalid
4. summary/state/accepted/snapshot join blockers -> invalid
5. completed observation exists but request_manifest_rows empty -> invalid
6. completed_observation_count == 0 -> not_ready
7. coverage blockers -> invalid
8. raw snapshot integrity blockers -> invalid
9. no completed formal announcement_and_launch_time evidence -> observation_only
10. depth quality blockers -> observation_only
11. otherwise -> sufficient_for_stage1_5h_plan
```

Safety flags must always be false:

```text
execution_feasibility_claim_allowed
trade_signal_allowed
paper_trading_allowed
live_trading_allowed
execution_engine_allowed
alpha_interpretation_allowed
```

**Step 4: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  -q
```

Expected: PASS.

---

## 9. Task 8: CLI And Report Writer

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py`
- Create: `tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py`
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`

**Step 1: Write failing CLI tests**

Test CLI:

```python
from scripts.external_signal_shadow.review_stage1_5g_live_depth_evidence import main


def test_stage1_5g_cli_writes_summary_and_review(tmp_path, monkeypatch):
    root = make_stage1_5f_fixture_root(tmp_path)
    summary_out = tmp_path / "stage1_5g_summary.json"
    review_out = tmp_path / "stage1_5g_review.md"

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5g_live_depth_evidence.py",
        "--stage1-5f-output-root", str(root),
        "--output-summary", str(summary_out),
        "--output-review", str(review_out),
    ])

    assert main() == 0
    data = json.loads(summary_out.read_text())
    assert "schema_version" in data
    assert data["trade_signal_allowed"] is False
    assert review_out.exists()
    assert "Stage 1.5G" in review_out.read_text(encoding="utf-8")
```

Add default output isolation test:

```python
def test_cli_does_not_write_inside_stage1_5f_output_root_by_default(tmp_path, monkeypatch):
    root = make_stage1_5f_fixture_root(tmp_path / "stage1_5f_root")
    output_root = tmp_path / "stage1_5g" / "reviews" / "run1"

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5g_live_depth_evidence.py",
        "--stage1-5f-output-root", str(root),
        "--output-root", str(output_root),
    ])

    assert main() == 0
    assert (output_root / "stage1_5g_live_depth_evidence_review_summary.json").exists()
    assert not (root / "stage1_5g_live_depth_evidence_review_summary.json").exists()
```

Also test missing input:

```python
def test_stage1_5g_cli_returns_nonzero_for_missing_output_root(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", [...])
    assert main() == 1
```

**Step 2: Run tests and verify they fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q
```

Expected: FAIL.

**Step 3: Implement CLI and markdown writer**

CLI args:

```text
--stage1-5f-output-root
--output-root optional; default data/external_signal_shadow/stage1_5g/reviews/<UTC_RUN_ID>/
--output-summary optional explicit override
--output-review optional explicit override
```

Functions:

```python
def generate_stage1_5g_chinese_review(summary: dict) -> str
def write_json(path: Path, data: dict) -> None
def main() -> int
```

Markdown must include:

```text
Decision
Safety Boundaries
Watermark Audit
Reviewed Event-Symbols
Coverage Review
Request Health Review
Raw Snapshot Integrity Review
Depth Quality Review
Evidence Label Review
Event-Family Scope Review
Why paper/live is still forbidden
Next Action
```

Output rules:

```text
Stage 1.5F output root is read-only input.
Default JSON summary path:
  data/external_signal_shadow/stage1_5g/reviews/<run_id>/stage1_5g_live_depth_evidence_review_summary.json
Default markdown review path:
  docs/reviews/YYYY-MM-DD-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md
Explicit --output-summary / --output-review may override these paths, but tests must ensure default mode does not write inside Stage 1.5F root.
```

**Step 4: Run CLI tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q
```

Expected: PASS.

---

## 10. Task 9: Integration Fixture For Representative Outcomes

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`

**Step 1: Add fixture scenarios**

Required scenarios:

```text
1. no completed observation -> not_ready
2. valid announcement_and_launch_time with good depth -> sufficient_for_stage1_5h_plan
3. valid launch_time_only with good depth -> observation_only
4. recovery_validation_only with good depth -> observation_only and excluded
5. coverage failure -> invalid
6. raw snapshot invalid -> invalid
7. thin book / high slippage -> observation_only
8. per-symbol request success failure -> invalid
9. JSONL parse error -> invalid
10. missing watermark.json -> invalid
11. summary.completed_observation_count != completed state count -> invalid
12. completed state without snapshots -> invalid
13. completed observation without request_manifest -> invalid
14. accepted announcement_and_launch_time but state still active -> not sufficient
```

**Step 2: Run all Stage 1.5G tests**

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

---

## 11. Task 10: Backward Compatibility And Safety Regression

**Files:**
- Existing Stage 1.5F tests only.

**Step 1: Run Stage 1.5F regression tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: PASS.

**Step 2: Safety grep**

```bash
grep -RniE "api[_-]?key|secret|private[_-]?key|order_request|TradeIntent|SignalCandidate|paper_trading_allowed.*true|live_trading_allowed.*true|execution_engine_allowed.*true" \
  src/research/external_signal_shadow \
  scripts/external_signal_shadow \
  tests/research/external_signal_shadow \
  tests/scripts/external_signal_shadow \
  | grep -v "__pycache__" || true
```

Expected:

```text
No new unsafe private endpoint, order, signal, paper/live permission path.
```

---

## 12. Manual Run Command

After implementation, run locally against a Stage 1.5F output root:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5F_OUT="data/external_signal_shadow/stage1_5f/live_depth_observer_7d_delayed_launch_age_gate_hotfix"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
export STAGE1_5G_OUT="data/external_signal_shadow/stage1_5g/reviews/${RUN_ID}"

PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  --stage1-5f-output-root "$STAGE1_5F_OUT" \
  --output-root "$STAGE1_5G_OUT" \
  --output-review "docs/reviews/$(date +%Y-%m-%d)-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md"
```

Do not write default Stage 1.5G artifacts inside `$STAGE1_5F_OUT`; Stage 1.5F root is read-only evidence input.

Expected before a completed 12h observation:

```text
decision = stage1_5g_not_ready_no_completed_observation
allowed_next_action = continue_observation
paper/live/execution/alpha flags all false
```

---

## 13. Completion Criteria

Implementation is complete only if all are true:

```text
1. All EXTERNAL_SIGNAL_STAGE1_5G_* constants exist in configs/base.py and have config tests.
2. Stage 1.5G loader reads Stage 1.5F output root without network calls.
3. Missing summary/watermark fails safely.
4. JSONL parse errors become blockers and can never be silently skipped into a sufficient decision.
5. Accepted event-symbols with no snapshot file do not crash loader; they fail via coverage count 0.
6. Missing watermark.json is stage1_5g_depth_evidence_invalid, not not_ready.
7. Evidence labels support announcement_and_launch_time, launch_time_only, recovery_validation_only.
8. recovery_validation_only never counts as formal 12h live depth evidence.
9. launch_time_only never triggers write_stage1_5h_shadow_execution_simulator_design.
10. Formal evidence requires accepted event, completed state, passing coverage, passing raw integrity, passing depth quality, and matching snapshots.
11. summary completed count, observer_state, accepted events, snapshots, and request_manifest are cross-validated.
12. Completed observation without request_manifest is invalid.
13. coverage is recomputed from 1.5F config snapshot or configs/base.py; implementation does not hardcode 720 or 60000.
14. per-symbol request success can fail a symbol even when global success is high.
15. raw snapshot integrity gate catches crossed books, invalid prices, non-monotonic timestamps, duplicate overload, null overload, JSONL parse errors, and symbol/id conflicts.
16. depth quality reports p05/p50/p95, healthy_window_ratio, and depth_capacity_ratio_to_risk_cap.
17. single event-symbol can allow only 1.5H design/plan, not event-family conclusion.
18. event-family conclusion discussion requires >=3 event-symbols and >=2 source_article_id.
19. summary contains schema_version, config_version, blockers[], warnings[], event_level_decisions[].
20. CLI default output goes under data/external_signal_shadow/stage1_5g/reviews/<run_id>/ and does not write into Stage 1.5F root.
21. all safety flags remain false in every decision branch.
22. CLI writes both JSON summary and Chinese review markdown.
23. Stage 1.5F regression tests still pass.
24. safety grep finds no private endpoint, API key, order, TradeIntent, SignalCandidate, paper/live enablement path.
```

---

## 14. Verification Commands

Run before handoff:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q

git diff --check
```

---

## 15. Handoff Notes

Do not use Stage 1.5G output as:

```text
alpha evidence
paper trading approval
live trading approval
execution feasibility proof
```

Interpret depth/slippage conservatively:

```text
1-minute REST depth snapshots are sampled static lower-bound friction estimates.
They are not realized execution slippage.
Crossed books, empty books, and startup market-maker instability must be treated as invalid or observation-only evidence.
500 USDT static slippage aligns with the current risk cap only as a review notional; it is not execution capacity.
```

The only positive next step allowed by this plan is:

```text
write_stage1_5h_shadow_execution_simulator_design
```

That next step is still design/plan only.
