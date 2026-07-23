# Stage 1.5F Launch-Time Gated Depth Observation Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Stage 1.5F so futures launch depth observation starts only at/after the launch/onboard anchor, persists and re-resolves pending launch observations across restarts, and prevents pre-launch or late/internal-capacity artifacts from becoming clean evidence.

**Architecture:** Replace detected-time admission with a launch-anchor state machine. Freeze bootstrap watermark evidence once at first seen, persist pending observations by stable event-symbol key, re-resolve missing/conflicting anchors on a bounded schedule, promote to accepted with an idempotent acceptance protocol, record first HTTP depth attempt separately from first healthy book, and compute 12h coverage by unique anchor-based time buckets. Stage 1.5G threshold changes are explicitly out of scope; 1.5F emits anchor-integrity fields for a later 1.5G audit update.

**Tech Stack:** Python 3, dataclasses, JSON/JSONL append-only artifacts, pytest, existing Stage 1.5F runner/loader/state/storage modules.

---

## Review Disposition

The latest audit is adopted with one bounded clarification:

```text
accepted:
  P0-1 anchor missing/conflict re-resolution and timeout
  P0-2 split pending timeout semantics
  P0-3 rewrite physically impossible capacity test/model
  P0-4 first depth HTTP request tracked outside parsed snapshot
  P0-5 frozen bootstrap watermark generation path
  P0-6 nullable anchor schema and legacy migration
  P0-7 coverage pass separated from clean-start eligibility
  P0-8 unique bucket coverage denominator
  P0-9 exchangeInfo medium-confidence clean conditions
  P0-10 event revision upsert by stable event-symbol key
  P0-11 idempotent accepted/state/watermark promotion recovery

clarified:
  CLOCK_SKEW_TOLERANCE_MS is retained only as a diagnostic/clock-audit field.
  It must never be used to permit depth requests before observation_anchor_ms.
```

## Safety Invariants

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

No task may introduce private exchange APIs, order endpoints, trading decisions, sizing, or execution actions. Network use remains public read-only and guarded by existing `--live-public-readonly` / mock fixtures.

## Source Design

Implement against:

```text
docs/designs/2026-07-23-external-signal-shadow-lab-stage1-5f-launch-time-gated-depth-observation-hotfix-design_CN.md
```

POPMARTUSDT legacy evidence is regression evidence only. It must not be converted to clean evidence by this implementation.

---

### Task 0: Preflight Current Code and Baseline Tests

**Files:**
- Inspect only: `configs/base.py`
- Inspect only: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Inspect only: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Inspect only: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Inspect only: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py`
- Inspect only: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py`
- Inspect only: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Inspect only: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py`
- Inspect only: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Inspect current state schema and frozen dataclass behavior**

Run:

```bash
grep -n "@dataclass\|class EventSymbolState\|frozen=True\|def __post_init__" \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py
```

Expected: confirm whether `EventSymbolState` is frozen. If frozen, any `__post_init__` mutation must use `object.__setattr__`.

**Step 2: Inspect current admission/start/finalize semantics**

Run:

```bash
grep -n "resolve_observation_age_base_ms\|classify_event_symbol_eligibility\|classify_live_depth_evidence_basis" \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py

grep -n "def start_observation\|def record_depth_snapshot\|def compute_snapshot_time_coverage\|def finalize_observation_if_due" \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py

grep -n "update_watermark_with_event\|events_accepted\|events_rejected\|record_depth_snapshot\|fetch_depth_snapshot" \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
```

Expected: confirm current `start_observation(now_ms)` and accepted/watermark ordering.

**Step 3: Inspect exchangeInfo cache schema**

Run:

```bash
grep -n "def parse_exchangeinfo\|def refresh_exchangeinfo_cache\|manifest_row\|symbols" \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py
```

Expected: confirm whether `symbol_rows`, payload hash, and raw payload path already exist.

**Step 4: Run baseline 1.5F tests before edits**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: current baseline known. If already failing, record failures before changing code.

**Step 5: Commit**

No commit for inspection-only task.

---

### Task 1: Split Stage 1.5F Launch-Gate Config Semantics

**Files:**
- Modify: `configs/base.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py`

**Step 1: Write failing config tests**

Append tests:

```python
def test_stage1_5f_launch_gate_config_constants_exist_and_are_safe():
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_CLOCK_SKEW_TOLERANCE_MS == 30_000
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS == 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS == 14 * 24 * 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS == 6 * 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS == 120_000
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS == 900_000
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_ANCHOR_RESOLUTION_RETRY_INTERVAL_SEC == 300
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS == 60_000


def test_stage1_5f_pending_timeouts_have_distinct_semantics():
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS < base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS < base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  -q
```

Expected: FAIL because new constants are missing.

**Step 3: Add constants**

In the Stage 1.5F config block in `configs/base.py`, add:

```python
EXTERNAL_SIGNAL_STAGE1_5F_CLOCK_SKEW_TOLERANCE_MS = 30 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS = 0
EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS = 14 * 24 * 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS = 6 * 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS = 2 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS = 15 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_ANCHOR_RESOLUTION_RETRY_INTERVAL_SEC = 5 * 60
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS = 60 * 1000
```

Keep `EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS` for backward compatibility until all call sites stop using it.

**Step 4: Run tests**

Run same command. Expected: PASS.

**Step 5: Commit**

```bash
git add configs/base.py tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py
git commit -m "test: add stage1 5f launch gate config contract"
```

---

### Task 2: Make Launch Anchor Schema Nullable and Legacy-Safe

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py`

**Step 1: Write failing nullable schema tests**

Append tests:

```python
def test_event_symbol_state_uses_nullable_launch_anchor_fields():
    state = EventSymbolState(
        event_symbol_id="es1",
        event_id="e1",
        symbol="ABCUSDT",
        detected_at_ms=1_000,
        status="pending_launch_anchor_missing",
        observation_anchor_ms=None,
        observation_started_at_ms=None,
        first_depth_request_at_ms=None,
        first_healthy_snapshot_at_ms=None,
        observer_state_schema_version=2,
    )

    row = state.to_dict()
    assert row["observation_anchor_ms"] is None
    assert row["observation_started_at_ms"] is None
    assert row["first_depth_request_at_ms"] is None
    assert row["observer_state_schema_version"] == 2


def test_legacy_zero_timestamps_migrate_to_none_for_new_semantic_fields():
    row = {
        "event_symbol_id": "es1",
        "event_id": "e1",
        "symbol": "ABCUSDT",
        "status": "pending_launch_anchor_missing",
        "observation_anchor_ms": 0,
        "first_depth_request_at_ms": 0,
        "first_healthy_snapshot_at_ms": 0,
    }

    state = EventSymbolState.from_dict(row)

    assert state.observation_anchor_ms is None
    assert state.first_depth_request_at_ms is None
    assert state.first_healthy_snapshot_at_ms is None
```

**Step 2: Run failing model tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  -q
```

Expected: FAIL because nullable fields and migration are missing.

**Step 3: Extend dataclass with nullable defaults**

Add fields with safe defaults. Use `None` for not-yet-happened timestamps:

```python
observer_state_schema_version: int = 2
observation_anchor_ms: int | None = None
observation_anchor_basis: str = ""
observation_anchor_confidence: str = ""
observation_anchor_candidates: dict | None = None
observation_anchor_disagreement_max_ms: int = 0
observation_anchor_conflict_active: bool = False
observation_admitted_at_ms: int | None = None
observation_started_at_ms: int | None = None
observation_window_start_ms: int | None = None
observation_window_end_ms: int | None = None
first_depth_request_at_ms: int | None = None
first_depth_request_latency_ms: int | None = None
first_healthy_snapshot_at_ms: int | None = None
first_valid_book_latency_ms: int | None = None
market_valid_book_latency_after_first_request_ms: int | None = None
evidence_start_class: str = ""
source_article_id: str = ""
stable_event_symbol_key: str = ""
stable_event_key: str = ""
latest_event_payload_hash: str = ""
acceptance_id: str = ""
acceptance_state: str = ""
first_seen_at_ms: int | None = None
announcement_capture_time_ms: int | None = None
next_admission_check_at_ms: int | None = None
next_anchor_resolution_at_ms: int | None = None
last_anchor_resolution_at_ms: int | None = None
anchor_resolution_started_at_ms: int | None = None
anchor_resolution_deadline_ms: int | None = None
last_anchor_resolution_sources: list[str] | None = None
bootstrap_watermark_max_seen_detected_at_ms: int | None = None
admission_watermark_at_first_seen_ms: int | None = None
announcement_capture_post_bootstrap_watermark: bool | None = None
launch_anchor_post_bootstrap_watermark: bool | None = None
capacity_defer_count: int = 0
anchor_resolution_attempt_count: int = 0
pending_terminal_reason: str = ""
expected_snapshot_count: int = 0
unique_snapshot_bucket_count: int = 0
duplicate_snapshot_row_count: int = 0
out_of_window_snapshot_row_count: int = 0
missing_snapshot_bucket_count: int = 0
pre_start_expected_snapshot_count: int = 0
pre_start_missing_snapshot_count: int = 0
coverage_ratio: float = 0.0
clean_start_sla_pass: bool = False
clean_evidence_start_allowed: bool = False
attempted_snapshot_count: int = 0
successful_http_snapshot_count: int = 0
valid_book_snapshot_count: int = 0
empty_book_snapshot_count: int = 0
invalid_book_snapshot_count: int = 0
```

If dataclass is frozen, `__post_init__` must use `object.__setattr__` to default dict/list fields and normalize legacy zeros.

**Step 4: Run model tests**

Run same command. Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py
git commit -m "feat: add nullable stage1 5f launch gate state schema"
```

---

### Task 3: Add Stable Event-Symbol Identity and Event Revision Upsert Helpers

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

**Step 1: Write failing identity/upsert tests**

Add tests:

```python
def test_stable_event_symbol_key_uses_article_symbol_and_event_type_not_revision_hash():
    row1 = {
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "event_id": "revision-a",
        "symbols": ["ABCUSDT"],
        "detail_payload_hash": "hash-a",
    }
    row2 = {
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "event_id": "revision-b",
        "symbols": ["ABCUSDT"],
        "detail_payload_hash": "hash-b",
    }

    assert make_stable_event_symbol_key(row1, "ABCUSDT") == make_stable_event_symbol_key(row2, "ABCUSDT")


def test_pending_state_upserts_new_event_revision_by_stable_key_preserving_first_seen_fields():
    pending = EventSymbolState(
        event_symbol_id="old-es",
        event_id="revision-a",
        symbol="ABCUSDT",
        status="pending_launch_anchor_missing",
        stable_event_symbol_key="futures_contract_launch|article1|ABCUSDT",
        first_seen_at_ms=1_000,
        bootstrap_watermark_max_seen_detected_at_ms=500,
        announcement_capture_post_bootstrap_watermark=True,
    )
    revision = {
        "event_id": "revision-b",
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "symbols": ["ABCUSDT"],
        "symbol_effective_launch_times_ms": {"ABCUSDT": 10_000},
        "detail_payload_hash": "hash-b",
    }

    updated = upsert_pending_state_with_event_revision(pending, revision, "ABCUSDT")

    assert updated.event_id == "revision-b"
    assert updated.latest_event_payload_hash == "hash-b"
    assert updated.first_seen_at_ms == 1_000
    assert updated.bootstrap_watermark_max_seen_detected_at_ms == 500
    assert updated.announcement_capture_post_bootstrap_watermark is True
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -q
```

Expected: FAIL because helpers are missing.

**Step 3: Implement helpers**

Add:

```python
def make_stable_event_symbol_key(row: dict, symbol: str) -> str:
    source_article_id = str(row.get("source_article_id") or "")
    event_type = str(row.get("event_type") or "")
    sym = symbol.strip().upper()
    if source_article_id:
        return f"{event_type}|{source_article_id}|{sym}"
    return f"{event_type}|{get_stable_event_key(row)}|{sym}"


def upsert_pending_state_with_event_revision(pending_state, event_row: dict, symbol: str):
    # Required behavior:
    # - return a new EventSymbolState
    # - preserve first_seen_at_ms and all frozen watermark fields
    # - update event_id and latest_event_payload_hash from event_row
    # - keep stable_event_symbol_key unchanged
    # - do not mutate active states
    raise NotImplementedError("implement in task")
```

The implementation must not rewrite `observation_anchor_ms` for an already `active` state. If an active observation receives a materially different anchor revision, write diagnostics later in runner and downgrade/mark recovery-only; do not silently mutate the active anchor.

**Step 4: Run loader tests**

Run same command. Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
git commit -m "feat: add stable stage1 5f event symbol revision identity"
```

---

### Task 4: Add Anchor Resolution, Conflict Detection, and ExchangeInfo Evidence

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py`

**Step 1: Write failing anchor tests**

Add tests:

```python
def test_resolve_depth_observation_anchor_prefers_effective_launch_time():
    row = {
        "symbol_effective_launch_times_ms": {"ABCUSDT": 10_000},
        "symbol_onboard_times_ms": {"ABCUSDT": 10_030},
    }
    exchangeinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    result = resolve_depth_observation_anchor_ms(row, "ABCUSDT", exchangeinfo, now_ms=9_000)

    assert result["observation_anchor_ms"] == 10_000
    assert result["observation_anchor_basis"] == "symbol_effective_launch_time"
    assert result["observation_anchor_confidence"] == "high"
    assert result["observation_anchor_conflict_active"] is False


def test_anchor_conflict_blocks_silent_priority_selection():
    row = {
        "symbol_effective_launch_times_ms": {"ABCUSDT": 10_000},
        "symbol_onboard_times_ms": {"ABCUSDT": 20_000},
    }
    exchangeinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    result = resolve_depth_observation_anchor_ms(row, "ABCUSDT", exchangeinfo, now_ms=9_000)

    assert result["observation_anchor_conflict_active"] is True
    assert result["observation_anchor_disagreement_max_ms"] == 10_000


def test_timely_exchangeinfo_anchor_can_be_medium_confidence_clean_start():
    row = {
        "event_type": "futures_contract_launch",
        "symbol_validation_status": "validated",
    }
    exchangeinfo = {
        "available": True,
        "symbols": {"ABCUSDT"},
        "symbol_rows": {
            "ABCUSDT": {
                "symbol": "ABCUSDT",
                "status": "PENDING_TRADING",
                "contractType": "PERPETUAL",
                "quoteAsset": "USDT",
                "marginAsset": "USDT",
                "onboardDate": 10_000,
            }
        },
        "fetched_at_ms": 9_000,
        "payload_sha256": "hash",
        "raw_payload_path": "raw/exchangeinfo.jsonl",
    }

    result = resolve_depth_observation_anchor_ms(row, "ABCUSDT", exchangeinfo, now_ms=9_000)

    assert result["observation_anchor_ms"] == 10_000
    assert result["observation_anchor_basis"] == "exchangeinfo_current_onboard_time"
    assert result["observation_anchor_confidence"] == "medium"
    assert result["exchangeinfo_anchor_clean_eligible"] is True


def test_exchangeinfo_anchor_without_payload_hash_is_recovery_only():
    row = {"event_type": "futures_contract_launch", "symbol_validation_status": "validated"}
    exchangeinfo = {
        "available": True,
        "symbols": {"ABCUSDT"},
        "symbol_rows": {"ABCUSDT": {"symbol": "ABCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 10_000}},
        "fetched_at_ms": 9_000,
        "payload_sha256": "",
        "raw_payload_path": "",
    }

    result = resolve_depth_observation_anchor_ms(row, "ABCUSDT", exchangeinfo, now_ms=9_000)

    assert result["observation_anchor_basis"] == "exchangeinfo_current_onboard_time"
    assert result["exchangeinfo_anchor_clean_eligible"] is False
```

**Step 2: Write failing exchangeInfo cache tests**

Add tests:

```python
def test_refresh_exchangeinfo_cache_exposes_symbol_rows_payload_hash_and_raw_path(tmp_path):
    payload = {"symbols": [{"symbol": "ABCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 20_000}]}

    cache = refresh_exchangeinfo_cache(
        now_ms=10_000,
        previous_cache=None,
        live_public_readonly=False,
        mock_exchangeinfo_payload=payload,
        raw_payload_root=str(tmp_path),
    )

    assert cache["symbol_rows"]["ABCUSDT"]["onboardDate"] == 20_000
    assert cache["payload_sha256"]
    assert cache["raw_payload_path"]
    assert (tmp_path / cache["raw_payload_path"]).exists() or cache["raw_payload_path"].endswith(".jsonl")
```

If `refresh_exchangeinfo_cache()` signature is too broad to change cleanly, implement a separate append-only raw writer and call it from runner. The test must still prove payload hash/path are available to anchor resolution.

**Step 3: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py \
  -q
```

Expected: FAIL because helpers and exchangeInfo evidence fields are missing.

**Step 4: Implement anchor resolver and exchangeInfo row cache**

Requirements:

```text
resolve_depth_observation_anchor_ms() returns diagnostics dict.
Candidate sources: symbol_effective_launch_times_ms, symbol_onboard_times_ms, validated exchangeInfo onboardDate.
ExchangeInfo status allowed: PENDING_TRADING, TRADING.
Product fields must be present and compatible with futures launch.
Anchor conflict if candidate disagreement > EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS.
No detected_at_ms fallback for clean futures launch observation.
ExchangeInfo clean eligibility requires payload_sha256 and timely fetched_at_ms.
```

**Step 5: Run tests**

Run same command. Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py
git commit -m "feat: resolve stage1 5f launch anchors with exchangeinfo evidence"
```

---

### Task 5: Freeze Bootstrap Watermark Evidence at First Seen

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

**Step 1: Write failing frozen watermark tests**

Add tests:

```python
def test_first_seen_computes_frozen_bootstrap_watermark_fields():
    event = {"event_id": "e1", "event_type": "futures_contract_launch", "detected_at_ms": 2_000, "symbols": ["ABCUSDT"]}
    diag = {"observation_anchor_ms": 10_000}
    watermark = Watermark(1, 5_000, [], [], [], 5_000)
    bootstrap_watermark_ms = 1_000

    frozen = build_first_seen_watermark_diagnostics(event, "ABCUSDT", diag, watermark, bootstrap_watermark_ms)

    assert frozen["bootstrap_watermark_max_seen_detected_at_ms"] == 1_000
    assert frozen["admission_watermark_at_first_seen_ms"] == 5_000
    assert frozen["announcement_capture_post_bootstrap_watermark"] is True
    assert frozen["launch_anchor_post_bootstrap_watermark"] is True


def test_pending_recheck_does_not_recompute_frozen_evidence_flags():
    existing = EventSymbolState(
        event_symbol_id="es1",
        status="pending_launch_time_in_future",
        bootstrap_watermark_max_seen_detected_at_ms=1_000,
        admission_watermark_at_first_seen_ms=5_000,
        announcement_capture_post_bootstrap_watermark=True,
        launch_anchor_post_bootstrap_watermark=True,
    )
    new_diag = {
        "bootstrap_watermark_max_seen_detected_at_ms": 9_000,
        "admission_watermark_at_first_seen_ms": 9_000,
        "announcement_capture_post_bootstrap_watermark": False,
        "launch_anchor_post_bootstrap_watermark": False,
    }

    merged = merge_first_seen_watermark_fields(existing, new_diag)

    assert merged["bootstrap_watermark_max_seen_detected_at_ms"] == 1_000
    assert merged["announcement_capture_post_bootstrap_watermark"] is True
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  -q
```

Expected: FAIL because frozen watermark helpers are missing.

**Step 3: Implement frozen evidence helpers**

Rules:

```text
First new event_symbol_id/stable_event_symbol_key:
  bootstrap_watermark_max_seen_detected_at_ms = root bootstrap value.
  admission_watermark_at_first_seen_ms = current moving watermark.
  announcement_capture_post_bootstrap_watermark = announcement_capture_time_ms > bootstrap watermark.
  launch_anchor_post_bootstrap_watermark = anchor_ms > bootstrap watermark when anchor exists.

Existing pending state:
  preserve all first-seen watermark fields.
  event revisions can update anchor candidates/hash but cannot rewrite announcement_capture_post_bootstrap_watermark.
```

The root bootstrap value can initially be `watermark.max_seen_detected_at_ms` loaded at process start. If `watermark.json` lacks a dedicated field, store it in runner-local `bootstrap_watermark_max_seen_detected_at_ms` at startup and write it into state rows.

**Step 4: Update `classify_live_depth_evidence_basis()`**

If frozen fields exist, use them. Moving watermark fallback is allowed only for legacy accepted rows without frozen fields.

**Step 5: Run tests**

Run same command. Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py
git commit -m "feat: freeze stage1 5f watermark evidence at first seen"
```

---

### Task 6: Implement Pending State Creation, Revision Upsert, and Anchor Re-Resolution Scheduler

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

**Step 1: Write failing pending creation/reload tests**

Add tests:

```python
def test_create_pending_launch_state_survives_state_reload(tmp_path):
    state_file = tmp_path / "observer_state.jsonl"
    event = {
        "event_symbol_id": "es1",
        "event_id": "e1",
        "source_article_id": "article1",
        "stable_event_symbol_key": "futures_contract_launch|article1|ABCUSDT",
        "symbol": "ABCUSDT",
        "detected_at_ms": 1_000,
    }
    diag = {
        "observation_anchor_ms": 10_000,
        "observation_anchor_basis": "symbol_effective_launch_time",
        "observation_anchor_confidence": "high",
        "next_admission_check_at_ms": 10_000,
        "bootstrap_watermark_max_seen_detected_at_ms": 500,
        "announcement_capture_post_bootstrap_watermark": True,
        "launch_anchor_post_bootstrap_watermark": True,
    }

    state = create_pending_observation_state(event, "pending_launch_time_in_future", diag, now_ms=2_000)
    state_file.write_text(json.dumps(state.to_dict()) + "\n")

    loaded = load_latest_state_by_event_symbol_id(str(state_file))["es1"]
    assert loaded.status == "pending_launch_time_in_future"
    assert loaded.observation_anchor_ms == 10_000
```

**Step 2: Write failing anchor re-resolution tests**

Add tests:

```python
def test_missing_anchor_rechecks_latest_event_revision():
    pending = EventSymbolState(
        event_symbol_id="es1",
        event_id="rev1",
        symbol="ABCUSDT",
        status="pending_launch_anchor_missing",
        stable_event_symbol_key="futures_contract_launch|article1|ABCUSDT",
        next_anchor_resolution_at_ms=10_000,
        anchor_resolution_deadline_ms=20_000,
    )
    revision = {
        "event_id": "rev2",
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "symbols": ["ABCUSDT"],
        "symbol_effective_launch_times_ms": {"ABCUSDT": 15_000},
    }

    result = re_resolve_pending_anchor(pending, [revision], {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}, now_ms=10_000)

    assert result.status == "pending_launch_time_in_future"
    assert result.event_id == "rev2"
    assert result.observation_anchor_ms == 15_000


def test_missing_anchor_timeout_returns_terminal_rejection_state():
    pending = EventSymbolState(
        event_symbol_id="es1",
        symbol="ABCUSDT",
        status="pending_launch_anchor_missing",
        next_anchor_resolution_at_ms=10_000,
        anchor_resolution_deadline_ms=9_999,
    )

    result = re_resolve_pending_anchor(pending, [], {"available": True, "symbols": set(), "symbol_rows": {}}, now_ms=10_000)

    assert result.status == "rejected_launch_anchor_unavailable_timeout"
    assert result.pending_terminal_reason == "rejected_launch_anchor_unavailable_timeout"


def test_anchor_conflict_can_resolve_after_event_revision():
    pending = EventSymbolState(
        event_symbol_id="es1",
        event_id="rev1",
        symbol="ABCUSDT",
        status="pending_anchor_conflict",
        stable_event_symbol_key="futures_contract_launch|article1|ABCUSDT",
        observation_anchor_candidates={"symbol_effective_launch_time": 10_000, "symbol_onboard_time": 20_000},
        anchor_resolution_deadline_ms=30_000,
        next_anchor_resolution_at_ms=10_000,
    )
    revision = {
        "event_id": "rev2",
        "event_type": "futures_contract_launch",
        "source_article_id": "article1",
        "symbols": ["ABCUSDT"],
        "symbol_effective_launch_times_ms": {"ABCUSDT": 15_000},
        "symbol_onboard_times_ms": {"ABCUSDT": 15_010},
    }

    result = re_resolve_pending_anchor(pending, [revision], {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}, now_ms=10_000)

    assert result.status == "pending_launch_time_in_future"
    assert result.observation_anchor_ms == 15_000
```

**Step 3: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -q
```

Expected: FAIL because pending helpers and re-resolution scheduler are missing.

**Step 4: Implement pending and re-resolution helpers**

Add:

```python
def create_pending_observation_state(event_symbol_row: dict, status: str, diagnostics: dict, now_ms: int) -> EventSymbolState:
    # Required behavior:
    # - create an EventSymbolState with status starting with pending_ or rejected_
    # - copy event identity from event_symbol_row
    # - copy anchor/watermark/retry diagnostics from diagnostics
    # - initialize anchor_resolution_started_at_ms/deadline when missing/conflict
    raise NotImplementedError("implement in task")


def re_resolve_pending_anchor(pending_state: EventSymbolState, latest_event_rows: list[dict], exchangeinfo_state: dict, now_ms: int) -> EventSymbolState:
    # Required behavior:
    # - preserve immutable first-seen watermark fields
    # - merge latest same stable_event_symbol_key event revision
    # - rerun anchor resolution with current exchangeInfo
    # - reschedule, promote to future/due, or terminally reject on deadline
    raise NotImplementedError("implement in task")
```

Rules:

```text
known future anchor:
  pending until anchor unless anchor - first_seen > MAX_FUTURE_LAUNCH_LEAD_MS.

missing/conflict anchor:
  recheck when now_ms >= next_anchor_resolution_at_ms.
  merge latest same stable_event_symbol_key revision.
  re-run resolve_depth_observation_anchor_ms().
  if resolved and future -> pending_launch_time_in_future.
  if resolved and due -> eligible in classifier/runner.
  if still missing/conflict and now < deadline -> reschedule.
  if now >= deadline -> terminal rejected_*_timeout state.

capacity pending:
  not handled here; runner capacity task handles it.
```

Add fields:

```text
last_anchor_resolution_at_ms
anchor_resolution_attempt_count
anchor_resolution_started_at_ms
anchor_resolution_deadline_ms
last_anchor_resolution_sources
pending_terminal_reason
```

**Step 5: Run tests**

Run same command. Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
git commit -m "feat: re-resolve stage1 5f pending launch anchors"
```

---

### Task 7: Replace Eligibility Classification with Launch-Gate Statuses

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

**Step 1: Write failing eligibility tests**

Add tests:

```python
def test_launch_time_in_future_is_pending_status_with_next_admission_time():
    now_ms = 1_000_000
    event = {"event_id": "e1", "event_type": "futures_contract_launch", "detected_at_ms": now_ms - 60_000, "symbols": ["ABCUSDT"], "symbol_effective_launch_times_ms": {"ABCUSDT": now_ms + 600_000}}
    w = Watermark(1, now_ms - 120_000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(event, "ABCUSDT", now_ms, w, exinfo, {})

    assert status == "pending"
    assert reason == "pending_launch_time_in_future"
    assert diag["observation_anchor_ms"] == now_ms + 600_000
    assert diag["next_admission_check_at_ms"] == now_ms + 600_000


def test_missing_launch_anchor_does_not_fallback_to_detected_time_for_clean_observation():
    now_ms = 1_000_000
    event = {"event_id": "e1", "event_type": "futures_contract_launch", "detected_at_ms": now_ms - 60_000, "symbols": ["ABCUSDT"]}
    w = Watermark(1, now_ms - 120_000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(event, "ABCUSDT", now_ms, w, exinfo, {})

    assert status == "pending"
    assert reason == "pending_launch_anchor_missing"
    assert diag["observation_anchor_ms"] is None
    assert diag["live_depth_evidence_basis"] == "recovery_validation_only"


def test_late_launch_start_is_recovery_only_not_clean():
    now_ms = 1_000_000
    launch_ms = now_ms - base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS - 1
    event = {"event_id": "e1", "event_type": "futures_contract_launch", "detected_at_ms": now_ms - 60_000, "symbols": ["ABCUSDT"], "symbol_effective_launch_times_ms": {"ABCUSDT": launch_ms}}
    w = Watermark(1, now_ms - 120_000, [], [], [], now_ms)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}, "symbol_rows": {}}

    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(event, "ABCUSDT", now_ms, w, exinfo, {})

    assert status == "eligible"
    assert reason == "eligible_recovery_only"
    assert diag["evidence_start_class"] == "recovery_start"
    assert diag["live_depth_evidence_basis"] == "recovery_validation_only"
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -q
```

Expected: FAIL until classifier uses anchor-based statuses.

**Step 3: Implement classifier changes**

Rules:

```text
wrong event type -> rejected wrong_event_type.
pre-watermark identity seen -> rejected pre_watermark.
anchor missing -> pending pending_launch_anchor_missing.
anchor conflict -> pending pending_anchor_conflict.
known future anchor beyond max lead -> rejected rejected_future_launch_lead_exceeded.
known future anchor not due -> pending pending_launch_time_in_future.
anchor due and now-anchor <= MAX_CLEAN_START_DELAY_MS -> eligible eligible_clean_start.
anchor due and clean delay exceeded but recovery delay not exceeded -> eligible eligible_recovery_only.
anchor due and recovery delay exceeded -> rejected rejected_launch_anchor_age_exceeded.
```

Never use `detected_at_ms` to accept a futures launch without anchor.

**Step 4: Update old tests**

Update old expected reason names for anchor-based tests. Keep backward compatibility only for legacy non-clean diagnostics where explicitly needed.

**Step 5: Run tests**

Run same command. Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
git commit -m "feat: classify stage1 5f events by launch anchor"
```

---

### Task 8: Idempotent Acceptance Protocol and Crash Reconciliation

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing stable acceptance tests**

Add tests:

```python
def test_acceptance_id_is_stable_across_restarts():
    state = EventSymbolState(event_symbol_id="es1", stable_event_symbol_key="futures_contract_launch|article1|ABCUSDT", observation_anchor_ms=10_000)

    a1 = make_acceptance_id(state)
    a2 = make_acceptance_id(state)

    assert a1 == a2
    assert len(a1) == 64


def test_promote_pending_to_active_sets_window_from_anchor_not_now_and_acceptance_id():
    pending = EventSymbolState(
        event_symbol_id="es1",
        event_id="e1",
        symbol="ABCUSDT",
        status="pending_launch_time_in_future",
        observation_anchor_ms=10_000,
        observation_anchor_basis="symbol_effective_launch_time",
        observation_anchor_confidence="high",
        stable_event_symbol_key="futures_contract_launch|article1|ABCUSDT",
        announcement_capture_post_bootstrap_watermark=True,
        launch_anchor_post_bootstrap_watermark=True,
    )

    active = promote_pending_to_active_observation(pending, now_ms=10_500, evidence_start_class="clean_start")

    assert active.status == "active"
    assert active.observation_started_at_ms == 10_500
    assert active.observation_window_start_ms == 10_000
    assert active.observation_window_end_ms == 10_000 + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS
    assert active.acceptance_id
```

**Step 2: Write failing runner reconciliation tests**

Add tests:

```python
def test_restart_after_accepted_write_does_not_duplicate_acceptance(tmp_path, monkeypatch):
    # Arrange output_root with an events_accepted row containing acceptance_id but no active state row.
    # Run one poll with same event at anchor.
    # Expected: exactly one accepted row remains and active state is repaired.
    accepted_rows = load_all_accepted_rows(output_root)
    assert len({row["acceptance_id"] for row in accepted_rows}) == 1
    assert len(accepted_rows) == 1
    assert latest_state.status == "active"


def test_restart_after_active_state_write_repairs_missing_accepted_row(tmp_path, monkeypatch):
    # Arrange observer_state has active state with acceptance_id but events_accepted is absent.
    # Run one poll.
    # Expected: accepted row is backfilled once with same acceptance_id.
    accepted_rows = load_all_accepted_rows(output_root)
    assert len(accepted_rows) == 1
    assert accepted_rows[0]["acceptance_id"] == active_state.acceptance_id
```

Use helper functions inside the test file to read accepted/state rows. Do not leave pseudocode in final tests.

**Step 3: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: FAIL because acceptance ids/reconciliation do not exist.

**Step 4: Implement idempotent promotion**

Minimum protocol:

```text
acceptance_id = sha256(stable_event_symbol_key | observation_anchor_ms)
accepted row includes acceptance_id.
active state includes acceptance_id.
runner startup/reconciliation builds accepted_id set from events_accepted.
if accepted exists but active state missing: repair active state from accepted row.
if active exists but accepted missing: backfill accepted row.
if both exist: do not duplicate.
watermark update is idempotent because seen lists are sets/list-deduped by update helper.
```

If full repair from accepted row lacks fields, include enough fields in accepted row to reconstruct active state: symbol, event_id, event_symbol_id, detected_at_ms, observation_anchor_ms, basis/confidence, window_start/end, evidence_start_class, frozen watermark fields.

**Step 5: Run tests**

Run same command. Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
git commit -m "feat: make stage1 5f acceptance promotion idempotent"
```

---

### Task 9: Runner Pending Integration and Capacity Timeout Model

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing future pending runner test**

Add/replace test:

```python
def test_runner_future_launch_writes_pending_state_no_accepted_no_depth_no_watermark(tmp_path, monkeypatch):
    # Fixture values:
    # now_ms = 1_783_069_200_000
    # launch_time_ms = now_ms + 10 * 60_000
    # detected_at_ms = now_ms - 60_000
    # watermark_time = now_ms - 120_000
    # event symbol ETHUSD1 with launch/onboard maps.
    # mock exchangeInfo includes ETHUSD1.
    run_poll(now_ms)

    assert list((output_root / "events_accepted").glob("**/*.jsonl")) == []
    assert list((output_root / "events_rejected").glob("**/*.jsonl")) == []
    assert list((output_root / "depth_snapshots").glob("**/*.jsonl")) == []

    states = load_state_rows(output_root)
    assert states[-1]["status"] == "pending_launch_time_in_future"
    assert states[-1]["observation_anchor_ms"] == launch_time_ms

    watermark = json.loads((output_root / "watermark.json").read_text())
    assert watermark["max_seen_detected_at_ms"] == watermark_time
```

**Step 2: Write failing restart/promotion test**

Add:

```python
def test_runner_pending_launch_survives_restart_and_promotes_once_at_anchor(tmp_path, monkeypatch):
    run_poll(launch_time_ms - 600_000)
    run_poll(launch_time_ms)
    run_poll(launch_time_ms + 60_000)

    accepted_rows = load_accepted_rows(output_root)
    assert len(accepted_rows) == 1
    assert accepted_rows[0]["observation_anchor_ms"] == launch_time_ms
    assert accepted_rows[0]["observation_window_start_ms"] == launch_time_ms

    state_rows = load_state_rows(output_root)
    assert state_rows[-1]["status"] == "active"
```

**Step 3: Write failing capacity tests**

Add:

```python
def test_capacity_pending_remains_pending_while_active_slot_occupied(tmp_path, monkeypatch):
    # monkeypatch MAX_ACTIVE_EVENT_SYMBOLS = 1.
    # One event row contains symbols AAAUSDT and BBBUSDT with same launch_time_ms.
    # First poll at launch admits one active symbol and capacity-defers the other.
    # Second poll shortly after still has active slot occupied.
    run_poll(launch_time_ms)
    run_poll(launch_time_ms + 60_000)

    latest_by_symbol = latest_state_by_symbol(output_root)
    assert latest_by_symbol["AAAUSDT"]["status"] == "active"
    assert latest_by_symbol["BBBUSDT"]["status"] == "pending_observation_capacity"


def test_capacity_pending_promotes_if_slot_frees_before_recovery_deadline(tmp_path, monkeypatch):
    # Same setup, but before second poll mark AAAUSDT completed in observer_state.
    # Second poll occurs before launch_time_ms + MAX_RECOVERY_START_DELAY_MS.
    run_poll(launch_time_ms)
    append_completed_state_for_symbol(output_root, "AAAUSDT")
    run_poll(launch_time_ms + 60_000)

    latest_by_symbol = latest_state_by_symbol(output_root)
    assert latest_by_symbol["BBBUSDT"]["status"] == "active"
    assert latest_by_symbol["BBBUSDT"]["evidence_start_class"] == "clean_start"


def test_capacity_pending_rejects_when_recovery_deadline_expires(tmp_path, monkeypatch):
    run_poll(launch_time_ms)
    run_poll(launch_time_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS + 1)

    latest_by_symbol = latest_state_by_symbol(output_root)
    assert latest_by_symbol["BBBUSDT"]["status"] == "rejected_observation_capacity_timeout"
    assert latest_by_symbol["BBBUSDT"]["pending_terminal_reason"] == "rejected_observation_capacity_timeout"
```

**Step 4: Run failing runner tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: FAIL until runner handles pending state and capacity timeouts.

**Step 5: Implement runner integration**

Requirements:

```text
Load states at startup, including pending states.
Index pending by stable_event_symbol_key and event_symbol_id.
For new event rows, upsert pending revisions rather than skipping by event_symbol_id alone.
For pending missing/conflict states due for re-resolution, call re_resolve_pending_anchor().
For pending future states, promote only when now_ms >= anchor_ms + LAUNCH_START_GUARD_MS.
For pending capacity, retry while active capacity may free; reject at anchor + MAX_RECOVERY_START_DELAY_MS.
Sort promotion candidates by (observation_anchor_ms, stable_event_symbol_key) for fairness.
Write accepted/state/watermark using idempotent acceptance protocol from Task 8.
```

**Step 6: Run runner tests**

Run same command. Expected: PASS.

**Step 7: Commit**

```bash
git add scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
git commit -m "feat: integrate stage1 5f pending launch state in runner"
```

---

### Task 10: Record First Depth HTTP Attempt Separately from Parsed Snapshot

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing state tests**

Add:

```python
def test_failed_first_depth_http_request_still_sets_first_request_latency():
    state = EventSymbolState(event_symbol_id="es1", event_id="e1", symbol="ABCUSDT", status="active", observation_anchor_ms=10_000)

    updated = record_depth_request_attempt(state, fetched_at_ms=10_600, http_status=500, request_manifest_id="m1")

    assert updated.first_depth_request_at_ms == 10_600
    assert updated.first_depth_request_latency_ms == 600
    assert updated.first_healthy_snapshot_at_ms is None


def test_second_healthy_snapshot_does_not_replace_first_request_timestamp():
    state = EventSymbolState(event_symbol_id="es1", event_id="e1", symbol="ABCUSDT", status="active", observation_anchor_ms=10_000)
    after_fail = record_depth_request_attempt(state, fetched_at_ms=10_600, http_status=500, request_manifest_id="m1")
    after_ok_req = record_depth_request_attempt(after_fail, fetched_at_ms=70_000, http_status=200, request_manifest_id="m2")
    snap = DepthSnapshot(event_symbol_id="es1", symbol="ABCUSDT", fetched_at_ms=70_000, best_bid=1.0, best_ask=2.0, depth_status="healthy")

    updated = record_depth_snapshot(after_ok_req, snap)

    assert updated.first_depth_request_at_ms == 10_600
    assert updated.first_depth_request_latency_ms == 600
    assert updated.first_healthy_snapshot_at_ms == 70_000
    assert updated.market_valid_book_latency_after_first_request_ms == 59_400
```

**Step 2: Write failing runner manifest/state test**

Add:

```python
def test_manifest_first_depth_request_matches_state_first_depth_request(tmp_path, monkeypatch):
    # Use mock or monkeypatch fetch_depth_snapshot to return first failure then success.
    # State first_depth_request_at_ms must equal first depth request manifest fetched_at_ms, not first healthy snapshot time.
    depth_rows = load_depth_manifest_rows(output_root)
    latest = latest_state_by_symbol(output_root)["ABCUSDT"]
    assert latest["first_depth_request_at_ms"] == depth_rows[0]["fetched_at_ms"]
```

**Step 3: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: FAIL because request attempt tracking is missing.

**Step 4: Implement `record_depth_request_attempt()` and runner call order**

Add:

```python
def record_depth_request_attempt(state: EventSymbolState, *, fetched_at_ms: int, http_status: int | None, request_manifest_id: str = "") -> EventSymbolState:
    # Required behavior:
    # - set first_depth_request_at_ms only if it is currently None
    # - set first_depth_request_latency_ms relative to observation_anchor_ms
    # - increment attempted/successful HTTP counters without requiring a parsed snapshot
    # - never overwrite first request timestamp with later healthy snapshots
    raise NotImplementedError("implement in task")
```

Runner order:

```text
perform depth HTTP/mock request
build/write manifest row
record_depth_request_attempt(state, fetched_at_ms=manifest_row["fetched_at_ms"], http_status=manifest_row.get("http_status"), request_manifest_id=manifest_row.get("request_id", ""))
if payload parsed into snapshot: record_depth_snapshot()
append updated state after request attempt and after parsed snapshot update
```

Hard guard remains:

```text
if state.observation_anchor_ms is not None and now_ms < state.observation_anchor_ms:
  skip depth request and log diagnostic; this should be unreachable.
```

**Step 5: Run tests**

Run same command. Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
git commit -m "feat: track first stage1 5f depth http attempt"
```

---

### Task 11: Compute Anchor-Based Unique-Bucket Coverage

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

**Step 1: Write failing unique bucket tests**

Add:

```python
def test_late_start_keeps_full_anchor_based_expected_snapshot_denominator_without_forcing_coverage_fail():
    anchor_ms = 10_000
    started_ms = anchor_ms + 5 * 60_000
    state = EventSymbolState(
        event_symbol_id="es1",
        event_id="e1",
        symbol="ABCUSDT",
        status="active",
        observation_anchor_ms=anchor_ms,
        observation_started_at_ms=started_ms,
        observation_window_start_ms=anchor_ms,
        observation_window_end_ms=anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS,
        evidence_start_class="recovery_start",
    )
    snapshots = [DepthSnapshot(event_symbol_id="es1", symbol="ABCUSDT", fetched_at_ms=started_ms + i * 60_000, best_bid=1, best_ask=2) for i in range(715)]

    cov = compute_snapshot_time_coverage(state, snapshots)

    assert cov["expected_snapshot_count"] == 720
    assert cov["pre_start_missing_snapshot_count"] == 5
    assert cov["coverage_ratio"] == 715 / 720
    assert cov["clean_evidence_start_allowed"] is False


def test_duplicate_snapshots_do_not_inflate_coverage():
    anchor_ms = 10_000
    state = EventSymbolState(event_symbol_id="es1", event_id="e1", symbol="ABCUSDT", status="active", observation_anchor_ms=anchor_ms, observation_started_at_ms=anchor_ms, observation_window_start_ms=anchor_ms, observation_window_end_ms=anchor_ms + 120_000)
    snapshots = [
        DepthSnapshot(event_symbol_id="es1", symbol="ABCUSDT", fetched_at_ms=anchor_ms + 1_000),
        DepthSnapshot(event_symbol_id="es1", symbol="ABCUSDT", fetched_at_ms=anchor_ms + 2_000),
    ]

    cov = compute_snapshot_time_coverage(state, snapshots)

    assert cov["unique_snapshot_bucket_count"] == 1
    assert cov["duplicate_snapshot_row_count"] == 1


def test_snapshot_just_before_anchor_is_out_of_window():
    anchor_ms = 10_000
    state = EventSymbolState(event_symbol_id="es1", event_id="e1", symbol="ABCUSDT", status="active", observation_anchor_ms=anchor_ms, observation_started_at_ms=anchor_ms, observation_window_start_ms=anchor_ms, observation_window_end_ms=anchor_ms + 120_000)
    snapshots = [DepthSnapshot(event_symbol_id="es1", symbol="ABCUSDT", fetched_at_ms=anchor_ms - 1)]

    cov = compute_snapshot_time_coverage(state, snapshots)

    assert cov["out_of_window_snapshot_row_count"] == 1
    assert cov["unique_snapshot_bucket_count"] == 0


def test_snapshot_at_window_end_is_out_of_window():
    anchor_ms = 10_000
    state = EventSymbolState(event_symbol_id="es1", event_id="e1", symbol="ABCUSDT", status="active", observation_anchor_ms=anchor_ms, observation_started_at_ms=anchor_ms, observation_window_start_ms=anchor_ms, observation_window_end_ms=anchor_ms + 120_000)
    snapshots = [DepthSnapshot(event_symbol_id="es1", symbol="ABCUSDT", fetched_at_ms=anchor_ms + 120_000)]

    cov = compute_snapshot_time_coverage(state, snapshots)

    assert cov["out_of_window_snapshot_row_count"] == 1
    assert cov["unique_snapshot_bucket_count"] == 0
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  -q
```

Expected: FAIL because current coverage uses raw row count and started-at boundaries.

**Step 3: Implement bucket coverage**

Rules:

```text
bucket_index = floor((fetched_at_ms - observation_window_start_ms) / poll_interval_ms)
valid bucket range = 0 <= bucket_index < expected_snapshot_count
unique_snapshot_bucket_count counts unique bucket indexes only
duplicate_snapshot_row_count counts extra in-window rows landing in already-counted bucket
out_of_window_snapshot_row_count counts fetched_at before anchor or >= window_end
missing_snapshot_bucket_count = expected - unique
coverage_ratio = unique / expected
coverage_ratio_pass only compares coverage_ratio against configured threshold
clean_start_sla_pass is separate from coverage_ratio_pass
clean_evidence_start_allowed = evidence_start_class == clean_start and clean_start_sla_pass
```

Do not materialize fake empty snapshots for missing pre-start buckets.

**Step 4: Update `finalize_observation_if_due()`**

Copy bucket metrics onto `EventSymbolState` and keep `research_result_valid` dependent on both coverage/gap and non-recovery clean rules only where appropriate. If legacy behavior needs backward compatibility, retain old fields but populate them from bucket metrics.

**Step 5: Run tests**

Run same command. Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py
git commit -m "feat: compute stage1 5f coverage by launch anchored buckets"
```

---

### Task 12: Summary Exposes Pending, Anchor, and Bucket Gauges

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`

**Step 1: Write failing summary test**

Add:

```python
def test_summary_includes_launch_gate_pending_and_bucket_gauges():
    active = EventSymbolState(event_symbol_id="active1", status="active", symbol="ABCUSDT", observation_anchor_ms=10_000, observation_started_at_ms=10_100, first_depth_request_latency_ms=100, unique_snapshot_bucket_count=1)
    pending = EventSymbolState(event_symbol_id="pending1", status="pending_launch_time_in_future", symbol="XYZUSDT", observation_anchor_ms=20_000)

    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_event_observation_in_progress",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="d.json",
        stage1_5e_summary_path="e.json",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1_000,
        pre_watermark_events_ignored=0,
        post_watermark_events_accepted=1,
        active_states=[active],
        completed_states=[],
        expired_states=[],
        failed_states=[],
        pending_states=[pending],
        request_manifest_rows=[],
        heartbeat_rows=[],
    ).to_dict()

    assert summary["pending_launch_observation_count"] == 1
    assert summary["pending_launch_time_in_future_count"] == 1
    assert summary["launch_gate_anchor_active_count"] == 1
    assert summary["unique_snapshot_bucket_count_total"] == 1
```

**Step 2: Run failing summary tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  -q
```

Expected: FAIL because summary signature/model lacks fields.

**Step 3: Add summary fields**

Add default fields:

```python
pending_launch_observation_count: int = 0
pending_launch_time_in_future_count: int = 0
pending_launch_anchor_missing_count: int = 0
pending_anchor_conflict_count: int = 0
pending_observation_capacity_count: int = 0
rejected_launch_anchor_unavailable_timeout_count: int = 0
rejected_anchor_conflict_timeout_count: int = 0
rejected_observation_capacity_timeout_count: int = 0
launch_gate_anchor_active_count: int = 0
observation_started_before_launch_anchor_count: int = 0
pre_start_missing_snapshot_count_total: int = 0
unique_snapshot_bucket_count_total: int = 0
duplicate_snapshot_row_count_total: int = 0
out_of_window_snapshot_row_count_total: int = 0
missing_snapshot_bucket_count_total: int = 0
```

Update builder to accept `pending_states: list | None = None` backward compatibly.

**Step 4: Update runner summary call**

Pass pending states from `states.values()` where `status.startswith("pending_")`.

**Step 5: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py
git commit -m "feat: summarize stage1 5f launch gate state"
```

---

### Task 13: POPMART Regression Fixture

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing POPMART regression test**

Add:

```python
def test_popmart_detected_before_onboard_does_not_start_prelaunch_depth(tmp_path, monkeypatch):
    detected_at_ms = 1784770354224
    accepted_bug_time_ms = 1784770461958
    onboard_ms = 1784773800000
    watermark_time = 1784705989499

    # Event row:
    # - event_type futures_contract_launch
    # - source_article_id fcdc949b45a644c78e341c88331a35ef
    # - detected_at_ms above
    # - symbols ["POPMARTUSDT"]
    # - no symbol_effective_launch_times_ms and no symbol_onboard_times_ms
    # Mock exchangeInfo payload:
    # {"symbols": [{"symbol": "POPMARTUSDT", "status": "TRADING",
    #   "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT",
    #   "marginAsset": "USDT", "onboardDate": onboard_ms}]}

    run_poll(accepted_bug_time_ms)

    assert list((output_root / "events_accepted").glob("**/*.jsonl")) == []
    assert list((output_root / "depth_snapshots").glob("**/*.jsonl")) == []

    states = load_state_rows(output_root)
    assert states[-1]["status"] == "pending_launch_time_in_future"
    assert states[-1]["observation_anchor_ms"] == onboard_ms

    run_poll(onboard_ms)

    accepted_rows = load_accepted_rows(output_root)
    assert len(accepted_rows) == 1
    accepted = accepted_rows[0]
    assert accepted["symbol"] == "POPMARTUSDT"
    assert accepted["observation_anchor_ms"] == onboard_ms
    assert accepted["observation_anchor_basis"] == "exchangeinfo_current_onboard_time"
    assert accepted["first_depth_request_at_ms"] is None or accepted["first_depth_request_at_ms"] >= onboard_ms
```

**Step 2: Run failing regression**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_popmart_detected_before_onboard_does_not_start_prelaunch_depth \
  -q
```

Expected: FAIL until exchangeInfo anchor fallback and pending promotion fully work.

**Step 3: Fix only regression gaps**

Do not broaden scope. Fix only paths required for:

```text
No accepted/depth before onboardDate.
Pending state persisted before onboardDate.
Promotion at onboardDate.
Accepted row has exchangeInfo medium-confidence anchor fields.
No clean evidence claim for legacy POPMART root.
```

**Step 4: Run full 1.5F suite**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py
git commit -m "test: add popmart launch anchor regression"
```

---

### Task 14: Documentation Update for Deployment Checks

**Files:**
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

**Step 1: Add short review note**

Add near existing Stage 1.5F hotfix/check sections:

```markdown
### Stage 1.5F launch-time gated observation hotfix note

POPMARTUSDT exposed that accepted-time depth observation can begin before futures onboardDate when 1.5F falls back to detected_at_ms. The new launch-time gate requires persisted pending state until symbol_effective_launch_times_ms / symbol_onboard_times_ms / validated exchangeInfo.onboardDate is reached. First depth request must be >= observation_anchor_ms. Coverage is computed by unique anchor-based buckets over the full anchor -> anchor+12h window.
```

**Step 2: Add compact check commands**

Add only short checks:

```bash
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null | python -m json.tool | grep -E \
"pending_launch_observation_count|observation_started_before_launch_anchor_count|pre_start_missing_snapshot_count_total|unique_snapshot_bucket_count_total|duplicate_snapshot_row_count_total|launch_gate_anchor_active_count" || true

find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null -exec grep -HIn \
"acceptance_id\|observation_anchor_ms\|observation_window_start_ms\|first_depth_request_latency_ms\|evidence_start_class" {} \; | tail -n 40
```

**Step 3: Verify docs only**

```bash
git diff --check -- docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

Expected: no whitespace errors.

**Step 4: Commit**

```bash
git add docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
git commit -m "docs: record stage1 5f launch-time gate checks"
```

---

### Task 15: Full Verification and Safety Grep

**Files:**
- No code changes unless verification fails.

**Step 1: Run targeted 1.5F tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: all pass.

**Step 2: Run adjacent 1.5D / 1.5G guard tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  -q
```

Expected: all pass. If 1.5G tests fail because new fields are unknown, keep 1.5G behavior backward compatible; do not change 1.5G thresholds in this hotfix.

**Step 3: Safety grep**

```bash
grep -RInE \
'paper_trading_allowed\s*[:=]\s*True|live_trading_allowed\s*[:=]\s*True|execution_engine_allowed\s*[:=]\s*True|trade_signal_allowed\s*[:=]\s*True|alpha_interpretation_allowed\s*[:=]\s*True|execution_feasibility_claim_allowed\s*[:=]\s*True' \
configs src scripts tests \
|| true
```

Expected: no production enabling of unsafe flags. If tests intentionally assert rejection of unsafe flags, verify they are test fixtures only.

**Step 4: Deployment root name check**

Plan deployment root suffixes must be new and must not reuse the POPMART legacy root:

```text
live_event_source_continuous_*_7d_bapi_detail_and_launch_time_gate_hotfix
live_depth_observer_*_7d_bapi_detail_and_launch_time_gate_hotfix
```

**Step 5: Final git status**

```bash
git status --short
```

Expected: only intentional files changed/staged.

---

## Done Definition

Implementation is complete only when:

```text
1. futures launch without anchor cannot start clean depth observation from detected_at_ms.
2. future launch persists pending state, survives restart, and promotes exactly once at anchor.
3. missing/conflicting anchors are re-resolved on a bounded schedule or terminally rejected.
4. capacity pending cannot outlive anchor + MAX_RECOVERY_START_DELAY_MS and never becomes market-liquidity failure.
5. evidence label uses frozen bootstrap/first-seen watermark fields, not moving watermark at acceptance.
6. accepted/state/watermark promotion is idempotent across crash windows.
7. first depth request fetched_at_ms is recorded from first HTTP attempt, independent of first healthy parsed book.
8. first depth request fetched_at_ms >= observation_anchor_ms.
9. observation window denominator is anchor_ms -> anchor_ms + 12h and coverage uses unique buckets.
10. duplicate/out-of-window snapshots cannot inflate coverage.
11. late/internal-capacity starts are recovery_validation_only, not clean.
12. exchangeInfo medium-confidence anchor has payload hash/path/status evidence or downgrades to recovery-only.
13. active observation anchor cannot be silently rewritten by later event revisions.
14. POPMART regression proves no pre-onboard depth starts.
15. BAPI 1.5D tests and 1.5F launch-gate tests pass together.
16. all safety flags remain false.
17. deployment uses new root suffix; old roots remain read-only evidence artifacts.
```
