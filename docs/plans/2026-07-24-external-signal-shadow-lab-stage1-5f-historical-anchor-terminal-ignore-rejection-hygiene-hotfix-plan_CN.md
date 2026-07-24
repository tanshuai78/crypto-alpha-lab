# Stage 1.5F Historical-Anchor Terminal Ignore / Rejection Hygiene Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Stage 1.5F so historical/pre-bootstrap launch anchors become idempotent terminal ignored states outside normal `events_rejected`, while genuine post-bootstrap rejected rows get complete identity/reason audit fields.

**Architecture:** Add a root-level immutable bootstrap watermark, stable terminal hygiene IDs, terminal ignored/rejected state persistence, and bounded diagnostics. Admission must classify source identity and historical anchors before anchor-conflict logic, suppress duplicate terminal artifacts across polls/restarts, and preserve 1.5G compatibility by keeping historical/malformed diagnostics out of normal `events_rejected`.

**Tech Stack:** Python 3, dataclasses, JSON/JSONL append-only artifacts, pytest, existing Stage 1.5F runner/loader/state/storage/summary modules.

---

## Source Design

Implement against:

```text
docs/designs/2026-07-24-external-signal-shadow-lab-stage1-5f-historical-anchor-rejection-hygiene-hotfix-design_CN.md
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

No task may introduce private exchange APIs, order endpoints, trading decisions, sizing, execution actions, or any exchange state mutation. Network use remains public read-only and guarded by existing `--live-public-readonly` / mock fixtures.

## Key Decisions Locked By Design Review

```text
historical/pre-bootstrap anchor:
  status = ignored_historical_anchor_pre_bootstrap
  normal events_rejected = forbidden
  consumable_by_stage1_5g = false

normal rejected:
  only post-bootstrap candidate that entered admission and terminally failed
  normal events_rejected = allowed
  must have identity + rejected_reason

bootstrap cutoff:
  root-level immutable bootstrap_max_seen_detected_at_ms only
  moving watermark / admission_watermark_at_first_seen_ms forbidden for historical classification

revision reopen:
  first version does not reopen ignored historical states on payload hash changes
  count terminal_ignored_revision_seen_count instead

required plan fixes from review:
  bootstrap watermark missing must be diagnostic-only safe no-op
  delayed-launch exception must use immutable bootstrap cutoff
  terminal idempotency must index by stable_event_symbol_key, not event_symbol_id
  malformed identity must route to capped diagnostics only
  anchor epoch bounds must live in configs/base.py
  terminal_hygiene_id must include bootstrap_root_id
  diagnostic cap must survive restart and not conflict with reconciliation
  reconciliation must handle state-missing/artifact-present as well as artifact-missing/state-present
  terminal state must persist canonical audit payload for reconstruction
  durable totals must come from durable state or be omitted
  production deployment must use a new 1.5F root suffix
```

---

### Task 0: Root-Cause Preflight and Baseline

**Files:**
- Inspect only: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Inspect only: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Inspect only: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Inspect only: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Inspect only: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Inspect only: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: List all normal `events_rejected` writers**

Run:

```bash
grep -R "events_rejected\|rejection_reason\|rejected_reason" -n \
  scripts/external_signal_shadow \
  src/research/external_signal_shadow \
  tests | head -n 200
```

Expected: enumerate every writer/loader path. Record whether only the runner rejected branch writes `events_rejected`.

**Step 2: Confirm runner CLI arguments**

Run:

```bash
grep -n "add_argument" scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
```

Expected: confirm `--fixture-events-jsonl`, `--bootstrap-watermark`, `--stage1-5d-summary`, `--stage1-5e-summary`, and `--output-root` exist. If `--fixture-events-jsonl` is missing or renamed, all runner fixture tests in this plan must use the actual argparse name before implementation proceeds.

**Step 3: Inspect current rejected writer**

Run:

```bash
sed -n '520,630p' scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
```

Expected: confirm whether `flat_event` identity is directly included and whether the canonical field is currently `rejection_reason`.

**Step 4: Capture local raw rejected fixture from production sample**

Create a minimal local fixture file for tests:

```bash
mkdir -p tests/fixtures/external_signal_shadow/stage1_5f/rejected_hygiene
cat > tests/fixtures/external_signal_shadow/stage1_5f/rejected_hygiene/malformed_historical_rejected_rows.jsonl <<'JSONL'
{"symbol":"GLWUSDT","event_id":null,"source_article_id":null,"rejected_reason":null,"status":null,"detected_at_ms":null,"observation_anchor_ms":1781170200000,"event_age_ms":3685540115,"watermark_max_seen_detected_at_ms":1784822376255}
JSONL
```

Expected: fixture preserves the observed malformed production shape; do not use it as a valid output target. Add adjacent metadata in the test docstring or fixture-loading test: `fixture_type = minimized_observed_shape`, `not_formal_evidence = true`, and the observed production root ID.

**Step 5: Run baseline tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: baseline passes or known failures are recorded before edits.

**Step 6: Commit preflight fixture if created**

```bash
git add tests/fixtures/external_signal_shadow/stage1_5f/rejected_hygiene/malformed_historical_rejected_rows.jsonl
git commit -m "test: capture malformed stage1 5f rejected fixture"
```

Skip commit if repository workflow prefers batching, but keep fixture in the later code commit.

---

### Task 1: Add Config and Immutable Bootstrap Watermark Schema

**Files:**
- Modify: `configs/base.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py` if watermark helpers live there
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

**Step 1: Write failing config/model tests**

Add tests:

```python
def test_watermark_schema_v2_has_immutable_bootstrap_fields():
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=2000,
        updated_at_ms=3000,
        bootstrap_max_seen_detected_at_ms=1000,
        bootstrap_created_at_ms=1500,
        bootstrap_source_root="stage1_5d/root",
        watermark_schema_version=2,
    )
    d = w.to_dict()
    assert d["watermark_schema_version"] == 2
    assert d["bootstrap_max_seen_detected_at_ms"] == 1000
    assert d["bootstrap_created_at_ms"] == 1500
    assert d["bootstrap_source_root"] == "stage1_5d/root"


def test_legacy_watermark_defaults_do_not_enable_historical_classification():
    w = Watermark.from_dict({
        "watermark_version": 1,
        "max_seen_detected_at_ms": 2000,
        "updated_at_ms": 3000,
    })
    assert getattr(w, "watermark_schema_version", 1) == 1
    assert getattr(w, "bootstrap_max_seen_detected_at_ms", None) is None
```

Add loader-level test:

```python
def test_historical_classification_requires_immutable_bootstrap_watermark():
    assert historical_anchor_classification_allowed(Watermark(max_seen_detected_at_ms=1000)) is False
    assert historical_anchor_classification_allowed(Watermark(
        max_seen_detected_at_ms=2000,
        watermark_schema_version=2,
        bootstrap_max_seen_detected_at_ms=1000,
        bootstrap_created_at_ms=900,
    )) is True
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -q
```

Expected: FAIL because bootstrap fields/helpers do not exist.

**Step 3: Add config and model fields**

In `configs/base.py` add:

```python
EXTERNAL_SIGNAL_STAGE1_5F_MAX_REJECTION_HYGIENE_DIAGNOSTIC_SAMPLES_PER_TYPE = 10
EXTERNAL_SIGNAL_STAGE1_5F_MIN_VALID_ANCHOR_EPOCH_MS = 1_500_000_000_000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_VALID_ANCHOR_EPOCH_MS = 4_200_000_000_000
```

In `Watermark` dataclass add defaults:

```python
watermark_schema_version: int = 1
bootstrap_max_seen_detected_at_ms: int | None = None
bootstrap_created_at_ms: int | None = None
bootstrap_source_root: str = ""
bootstrap_root_id: str = ""
```

Ensure `from_dict()` remains tolerant of missing legacy fields.

**Step 4: Add loader helpers**

Add:

```python
def historical_anchor_classification_allowed(watermark) -> bool:
    return (
        getattr(watermark, "watermark_schema_version", 1) >= 2
        and getattr(watermark, "bootstrap_max_seen_detected_at_ms", None) is not None
    )


def get_immutable_bootstrap_watermark_ms(watermark) -> int | None:
    if not historical_anchor_classification_allowed(watermark):
        return None
    return int(watermark.bootstrap_max_seen_detected_at_ms)
```

No fallback to moving watermark or `admission_watermark_at_first_seen_ms`.

**Step 5: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add configs/base.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
git commit -m "feat: add immutable stage1 5f bootstrap watermark schema"
```

---

### Task 2: Write Bootstrap Watermark V2 on New Root Bootstrap

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing bootstrap CLI test**

Add test:

```python
def test_bootstrap_watermark_writes_schema_v2_immutable_bootstrap_fields(tmp_path, monkeypatch):
    import sys, time, json
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps({
        "event_id": "old-event",
        "event_type": "futures_contract_launch",
        "source_article_id": "old-article",
        "stable_event_key": "binance_old",
        "detected_at_ms": 1000,
        "symbols": ["OLDUSDT"],
    }) + "\n")
    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({"decision": "stage1_5d_event_detection_passed", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({"decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    output_root = tmp_path / "out"
    monkeypatch.setattr(time, "time", lambda: 2000 / 1000.0)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main
    argv = [
        "run_stage1_5f_live_depth_observer.py",
        "--fixture-events-jsonl", str(event_file),
        "--stage1-5d-summary", str(summary_d),
        "--stage1-5e-summary", str(summary_e),
        "--output-root", str(output_root),
        "--bootstrap-watermark",
    ]
    old = sys.argv
    try:
        sys.argv = argv
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = old

    w = json.loads((output_root / "watermark.json").read_text())
    assert w["watermark_schema_version"] == 2
    assert w["bootstrap_max_seen_detected_at_ms"] == 1000
    assert w["bootstrap_created_at_ms"] == 2000
    assert w["bootstrap_source_root"]
    assert w["bootstrap_root_id"]
```

**Step 2: Run failing test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_bootstrap_watermark_writes_schema_v2_immutable_bootstrap_fields \
  -q
```

Expected: FAIL because v2 fields are missing.

**Step 3: Implement bootstrap writer**

In bootstrap path, when creating `Watermark`, set:

```python
watermark_schema_version=2,
bootstrap_max_seen_detected_at_ms=max_seen_detected_at_ms,
bootstrap_created_at_ms=now_ms,
bootstrap_source_root=args.stage1_5d_events_glob or args.fixture_events_jsonl or "",
bootstrap_root_id=sha256(f"{os.path.abspath(output_root)}|{now_ms}|{args.stage1_5d_events_glob or args.fixture_events_jsonl}|{max_seen_detected_at_ms}".encode("utf-8")).hexdigest(),
```

Do not mutate these fields during normal watermark updates.

**Step 4: Add non-mutation regression test**

Add test asserting `update_watermark_with_event()` or normal accepted path does not overwrite `bootstrap_max_seen_detected_at_ms`.

**Step 5: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_bootstrap_watermark_writes_schema_v2_immutable_bootstrap_fields \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
git commit -m "fix: freeze stage1 5f bootstrap watermark on root bootstrap"
```

---

### Task 3: Add Terminal Hygiene State Model and Stable ID

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py`

**Step 1: Write failing state tests**

Add:

```python
def test_make_terminal_hygiene_id_uses_stable_key_not_event_symbol_id():
    a = make_terminal_hygiene_id(
        stable_event_symbol_key="article|futures_contract_launch|EBAYUSDT",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        normalized_anchor_class="all_pre_bootstrap",
        bootstrap_root_id="root-id",
    )
    b = make_terminal_hygiene_id(
        stable_event_symbol_key="article|futures_contract_launch|EBAYUSDT",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        normalized_anchor_class="all_pre_bootstrap",
        bootstrap_root_id="root-id",
    )
    assert a == b
    assert len(a) == 64


def test_terminal_ignored_state_roundtrip_defaults():
    state = EventSymbolState(
        event_symbol_id="volatile-id",
        event_id="event-1",
        source_article_id="article-1",
        symbol="EBAYUSDT",
        detected_at_ms=1784822376255,
        stable_event_symbol_key="article-1|futures_contract_launch|EBAYUSDT",
        status="ignored_historical_anchor_pre_bootstrap",
        terminal_hygiene_id="abc",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_at_ms=1784850000000,
        consumable_by_stage1_5g=False,
    )
    loaded = EventSymbolState.from_dict(state.to_dict())
    assert loaded.status == "ignored_historical_anchor_pre_bootstrap"
    assert loaded.terminal_hygiene_id == "abc"
    assert loaded.consumable_by_stage1_5g is False
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  -q
```

Expected: FAIL because fields/helper are missing.

**Step 3: Add model fields with defaults**

In `EventSymbolState`, add:

```python
terminal_hygiene_id: str = ""
terminal_status: str = ""
terminal_reason: str = ""
terminal_at_ms: int | None = None
consumable_by_stage1_5g: bool | None = None
source_event_payload_hash: str = ""
latest_event_payload_hash: str = ""
terminal_ignored_revision_seen_count: int = 0
duplicate_suppressed_count: int = 0
last_duplicate_seen_at_ms: int | None = None
diagnostic_sample_reserved: bool = False
diagnostic_expected: bool = False
diagnostic_emitted: bool = False
terminal_audit_type: str = ""
terminal_audit_row: dict | None = None
```

Add `terminal_at_ms` to nullable timestamp coercion.

**Step 4: Add ID helper**

In state module:

```python
def make_terminal_hygiene_id(
    stable_event_symbol_key: str,
    terminal_status: str,
    normalized_anchor_class: str,
    bootstrap_root_id: str,
) -> str:
    payload = f"{stable_event_symbol_key}|{terminal_status}|{normalized_anchor_class}|{bootstrap_root_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

**Step 5: Run tests**

Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py
git commit -m "feat: add stage1 5f terminal hygiene state"
```

---

### Task 4: Implement Anchor Candidate Normalization and Historical Ignore Classification

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

**Step 1: Write failing tests**

Add tests:

```python
def test_invalid_zero_anchor_is_not_counted_as_historical_candidate():
    candidates = normalize_anchor_candidates({
        "symbol_effective_launch_time": 0,
        "exchangeinfo_current_onboard_time": 1781170800000,
    })
    assert "symbol_effective_launch_time" not in candidates
    assert candidates["exchangeinfo_current_onboard_time"] == 1781170800000


def test_all_valid_anchors_pre_bootstrap_short_circuits_conflict():
    watermark = Watermark(
        watermark_schema_version=2,
        bootstrap_max_seen_detected_at_ms=1784822376255,
        bootstrap_created_at_ms=1784822584716,
        max_seen_detected_at_ms=1784822376255,
    )
    row = {
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
        "detected_at_ms": 1784822376255,
        "symbol": "EBAYUSDT",
        "symbols": ["EBAYUSDT"],
        "stable_event_key": "binance_f598_MULTI",
        "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
    }
    exchangeinfo_state = {
        "available": True,
        "symbols": {"EBAYUSDT"},
        "symbol_rows": {"EBAYUSDT": {"symbol": "EBAYUSDT", "status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1780996800000}},
    }
    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        row=row,
        symbol="EBAYUSDT",
        now_ms=1784850000000,
        watermark=watermark,
        exchangeinfo_state=exchangeinfo_state,
        budget_state={},
    )
    assert status == "ignored"
    assert reason == "ignored_historical_anchor_pre_bootstrap"
    assert diag["terminal_status"] == "ignored_historical_anchor_pre_bootstrap"


def test_missing_bootstrap_watermark_does_not_fall_through_to_conflict():
    watermark = Watermark(max_seen_detected_at_ms=1784822376255)
    row = {
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
        "detected_at_ms": 1784822376255,
        "symbol": "EBAYUSDT",
        "symbols": ["EBAYUSDT"],
        "stable_event_key": "binance_f598_MULTI",
        "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
    }
    exchangeinfo_state = {
        "available": True,
        "symbols": {"EBAYUSDT"},
        "symbol_rows": {"EBAYUSDT": {"symbol": "EBAYUSDT", "status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1780996800000}},
    }
    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        row=row,
        symbol="EBAYUSDT",
        now_ms=1784850000000,
        watermark=watermark,
        exchangeinfo_state=exchangeinfo_state,
        budget_state={},
    )
    assert status == "diagnostic_only"
    assert reason == "historical_classification_bootstrap_watermark_missing"
    assert diag["bootstrap_watermark_missing"] is True


def test_delayed_launch_exception_uses_immutable_bootstrap_cutoff():
    row = {
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1784820000000,
        "symbols": ["FUTUREUSDT"],
        "symbol_effective_launch_times_ms": {"FUTUREUSDT": 1784900000000},
    }
    assert delayed_launch_event_symbol_is_post_bootstrap_watermark(
        row,
        "FUTUREUSDT",
        bootstrap_watermark_ms=1784810000000,
    ) is True
    assert delayed_launch_event_symbol_is_post_bootstrap_watermark(
        row,
        "FUTUREUSDT",
        bootstrap_watermark_ms=1784910000000,
    ) is False


def test_one_post_bootstrap_anchor_prevents_historical_ignore():
    watermark = Watermark(
        watermark_schema_version=2,
        bootstrap_max_seen_detected_at_ms=1784822376255,
        bootstrap_created_at_ms=1784822584716,
        bootstrap_root_id="root-id",
        max_seen_detected_at_ms=1784822376255,
    )
    row = {
        "event_id": "event-mixed",
        "event_type": "futures_contract_launch",
        "source_article_id": "article-mixed",
        "detected_at_ms": 1784822376255,
        "symbol": "MIXEDUSDT",
        "symbols": ["MIXEDUSDT"],
        "stable_event_key": "binance_mixed_MULTI",
        "symbol_effective_launch_times_ms": {"MIXEDUSDT": 1780995600000},
    }
    exchangeinfo_state = {
        "available": True,
        "symbols": {"MIXEDUSDT"},
        "symbol_rows": {"MIXEDUSDT": {"symbol": "MIXEDUSDT", "status": "PENDING_TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1784825976255}},
    }
    status, reason, diag = classify_event_symbol_eligibility_with_diagnostics(
        row=row,
        symbol="MIXEDUSDT",
        now_ms=1784823000000,
        watermark=watermark,
        exchangeinfo_state=exchangeinfo_state,
        budget_state={},
    )
    assert status != "ignored"
    assert reason != "ignored_historical_anchor_pre_bootstrap"
```

**Step 2: Run failing loader tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -q
```

Expected: FAIL because helpers/status do not exist.

**Step 3: Implement helpers**

Add:

```python
def normalize_anchor_candidates(anchor_candidates: dict) -> dict:
    out = {}
    for key, value in (anchor_candidates or {}).items():
        try:
            v = int(value)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        if v < base.EXTERNAL_SIGNAL_STAGE1_5F_MIN_VALID_ANCHOR_EPOCH_MS or v > base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_VALID_ANCHOR_EPOCH_MS:
            continue
        out[key] = v
    return out
```

Add historical classifier that runs before conflict check:

```python
def classify_historical_anchor_pre_bootstrap(row, symbol, anchor_diag, watermark) -> tuple[bool, dict]:
    boot = get_immutable_bootstrap_watermark_ms(watermark)
    if boot is None:
        return False, {"historical_anchor_classification_allowed": False, "bootstrap_watermark_missing": True}
    normalized = normalize_anchor_candidates(anchor_diag.get("observation_anchor_candidates", {}))
    if not normalized:
        return False, {"normalized_anchor_candidates": normalized}
    if delayed_launch_event_symbol_is_post_bootstrap_watermark(row, symbol, boot):
        return False, {"normalized_anchor_candidates": normalized, "delayed_launch_exception_active": True}
    if all(v <= boot for v in normalized.values()):
        return True, {
            "terminal_status": "ignored_historical_anchor_pre_bootstrap",
            "terminal_reason": "historical_anchor_pre_bootstrap",
            "normalized_anchor_candidates": normalized,
            "bootstrap_watermark_max_seen_detected_at_ms": boot,
            "normalized_anchor_class": "all_pre_bootstrap",
        }
    return False, {"normalized_anchor_candidates": normalized}
```

In `classify_event_symbol_eligibility_with_diagnostics()`, after anchor resolution and before conflict check:

```python
is_hist, hist_diag = classify_historical_anchor_pre_bootstrap(row, symbol, anchor_diag, watermark)
diag.update(hist_diag)
if is_hist:
    return "ignored", "ignored_historical_anchor_pre_bootstrap", diag
```

**Step 4: Run tests**

Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
git commit -m "fix: classify historical stage1 5f anchors as terminal ignored"
```

---

### Task 4.5: Add Stable Identity Normalization and Malformed Diagnostic Route

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing tests**

Add:

```python
def test_malformed_production_fixture_routes_to_diagnostic_only(tmp_path):
    # Load tests/fixtures/external_signal_shadow/stage1_5f/rejected_hygiene/malformed_historical_rejected_rows.jsonl.
    # Assert normalize_event_symbol_identity returns identity_valid=False.
    # Runner-level companion test must assert no events_rejected and no normal terminal ignored state.


def test_missing_source_article_id_never_enters_normal_terminal_state():
    # Missing source_article_id and event_id => diagnostic_only only.


def test_malformed_diagnostic_is_idempotent_across_restarts():
    # Same malformed input across two runner invocations writes at most one diagnostic sample per terminal_hygiene_id/fallback diagnostic id.
```

**Step 2: Implement helper**

Add:

```python
def normalize_event_symbol_identity(flat_event: dict, symbol: str) -> dict:
    # Output identity_valid, event_symbol_id, stable_event_symbol_key,
    # source_article_id, event_id, detected_at_ms, identity_errors.
```

Malformed path:

```text
identity_valid = false
-> diagnostic_only
-> no events_rejected
-> no normal ignored state
-> consumable_by_stage1_5g = false
```

**Step 3: Run tests and commit**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest   tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py   tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py   -q
```

### Task 5: Build Terminal Ignored State and Diagnostic Rows

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py` if needed
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

**Step 1: Write failing tests**

Add:

```python
def test_build_terminal_ignored_state_preserves_identity_and_is_not_1_5g_consumable():
    flat_event = {
        "event_symbol_id": "volatile-id",
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "article-ebay",
        "stable_event_key": "binance_article_MULTI",
        "stable_event_symbol_key": "article-ebay|futures_contract_launch|EBAYUSDT",
        "symbol": "EBAYUSDT",
        "detected_at_ms": 1784822376255,
    }
    state = build_terminal_ignored_state(
        flat_event=flat_event,
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        now_ms=1784850000000,
        diagnostics={
            "normalized_anchor_class": "all_pre_bootstrap",
            "bootstrap_watermark_max_seen_detected_at_ms": 1784822376255,
        },
    )
    assert state.status == "ignored_historical_anchor_pre_bootstrap"
    assert state.terminal_hygiene_id
    assert state.source_article_id == "article-ebay"
    assert state.detected_at_ms == 1784822376255
    assert state.consumable_by_stage1_5g is False
```

Add diagnostic row test:

```python
def test_build_historical_anchor_diagnostic_is_not_1_5g_consumable():
    row = build_historical_anchor_hygiene_diagnostic(state, diagnostic_at_ms=1784850000000)
    assert row["diagnostic_type"] == "historical_anchor_pre_bootstrap_ignored"
    assert row["consumable_by_stage1_5g"] is False
    assert row["terminal_hygiene_id"] == state.terminal_hygiene_id


def test_build_terminal_ignored_state_allows_event_id_when_source_article_id_missing():
    flat_event = {
        "event_symbol_id": "volatile-id",
        "event_id": "event-only-id",
        "event_type": "futures_contract_launch",
        "stable_event_symbol_key": "event-only-id|futures_contract_launch|EBAYUSDT",
        "symbol": "EBAYUSDT",
        "detected_at_ms": 1784822376255,
    }
    state = build_terminal_ignored_state(
        flat_event=flat_event,
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        now_ms=1784850000000,
        diagnostics={
            "normalized_anchor_class": "all_pre_bootstrap",
            "bootstrap_watermark_max_seen_detected_at_ms": 1784822376255,
            "bootstrap_root_id": "root-id",
        },
    )
    assert state.event_id == "event-only-id"
    assert state.source_article_id == ""
    assert state.status == "ignored_historical_anchor_pre_bootstrap"
```

**Step 2: Run failing tests**

Expected: FAIL because builders do not exist.

**Step 3: Implement builders**

Add `build_terminal_ignored_state()` and `build_historical_anchor_hygiene_diagnostic()` in state module.

Builder must validate:

```python
if (not flat_event.get("source_article_id") and not flat_event.get("event_id")) or not flat_event.get("symbol") or not flat_event.get("detected_at_ms"):
    raise ValueError("terminal ignored state requires source_article_id, symbol, detected_at_ms")
```

**Step 4: Run tests**

Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py
git commit -m "feat: add stage1 5f terminal ignored state builders"
```

---

### Task 6: Add Normal Rejected Row Builder With Identity Contract

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

**Step 1: Write failing tests**

Add:

```python
def test_build_rejected_event_symbol_row_contains_identity_and_reason_alias():
    flat_event = {
        "event_symbol_id": "event-symbol-id",
        "event_id": "event-1",
        "event_type": "futures_contract_launch",
        "source_article_id": "article-1",
        "stable_event_key": "binance_article_SYMBOL",
        "stable_event_symbol_key": "article-1|futures_contract_launch|XYZUSDT",
        "symbol": "XYZUSDT",
        "symbols": ["XYZUSDT"],
        "title": "Binance Futures Will Launch XYZUSDT",
        "detected_at_ms": 1784820000000,
        "available_at_ms": 1784820000000,
    }
    row = build_rejected_event_symbol_row(
        flat_event=flat_event,
        terminal_hygiene_id="abc",
        rejected_reason="rejected_launch_anchor_age_exceeded",
        now_ms=1784850000000,
        watermark_max_seen_detected_at_ms=1784822376255,
        watermark_version=1,
        eligibility_diag={"observation_anchor_ms": 1780995600000, "selected_anchor_age_ms": 3854400000},
        basis_diag={"live_depth_evidence_basis": "recovery_validation_only"},
    )
    assert row["rejected_reason"] == "rejected_launch_anchor_age_exceeded"
    assert row["rejection_reason"] == row["rejected_reason"]
    assert row["event_id"] == "event-1"
    assert row["source_article_id"] == "article-1"
    assert row["detected_at_ms"] == 1784820000000
    assert row["consumable_by_stage1_5g"] is True


def test_build_rejected_event_symbol_row_rejects_missing_identity():
    with pytest.raises(ValueError):
        build_rejected_event_symbol_row(
            flat_event={"symbol": "XYZUSDT"},
            terminal_hygiene_id="abc",
            rejected_reason="bad",
            now_ms=1,
            watermark_max_seen_detected_at_ms=0,
            watermark_version=1,
            eligibility_diag={},
            basis_diag={},
        )
```

**Step 2: Run failing tests**

Expected: FAIL because builder missing.

**Step 3: Implement builder**

Implement with canonical `rejected_reason` and compatibility alias `rejection_reason`. Set `event_age_ms` as compatibility alias for `selected_anchor_age_ms` only.

**Step 4: Run tests**

Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py
git commit -m "feat: add stage1 5f rejected row contract"
```

---

### Task 7: Wire Runner Terminal Ignored and Rejected Paths

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing runner tests**

Add:

```python
def test_historical_anchor_pre_bootstrap_writes_terminal_ignored_state_not_events_rejected(tmp_path, monkeypatch):
    # Build fixture with EBAY-style old anchors before immutable bootstrap watermark.
    # Run max-polls=1.
    # Assert observer_state has status ignored_historical_anchor_pre_bootstrap.
    # Assert no events_rejected files exist.
    # Assert historical_anchor_hygiene_diagnostics has one non-1.5G-consumable row.
```

Add concrete fixture:

```python
event = {
    "event_id": "event-ebay",
    "event_type": "futures_contract_launch",
    "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
    "stable_event_key": "binance_f598_MULTI",
    "detected_at_ms": 1784822376255,
    "symbols": ["EBAYUSDT"],
    "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
    "symbol_onboard_times_ms": {"EBAYUSDT": 1780995600000},
}
exchangeinfo = {"symbols": [{"symbol": "EBAYUSDT", "status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1780996800000}]}
watermark = {
    "watermark_version": 1,
    "watermark_schema_version": 2,
    "max_seen_detected_at_ms": 1784822376255,
    "bootstrap_max_seen_detected_at_ms": 1784822376255,
    "bootstrap_created_at_ms": 1784822584716,
    "seen_event_ids": [],
    "seen_source_article_ids": [],
    "seen_stable_event_keys": [],
    "updated_at_ms": 1784822584716,
}
```

Add idempotency test:

```python
def test_historical_anchor_pre_bootstrap_is_idempotent_across_polls(tmp_path, monkeypatch):
    # Run same fixture for max-polls=2 or call runner twice on same output root.
    # Assert exactly one terminal state in latest states and diagnostic rows <= 1 for that terminal_hygiene_id.
    # Assert events_rejected remains empty.


def test_changed_event_symbol_id_same_stable_key_remains_terminal_ignored(tmp_path, monkeypatch):
    # First poll writes terminal ignored state.
    # Second poll uses same source_article_id/event_type/symbol but changed payload/event_symbol_id.
    # Assert stable key lookup suppresses reprocessing and events_rejected remains empty.


def test_historical_terminal_payload_revision_does_not_reopen(tmp_path, monkeypatch):
    # Same stable key, changed payload hash.
    # Assert terminal_ignored_revision_seen_count increments durably and status remains ignored_historical_anchor_pre_bootstrap.
```

Add normal rejected regression:

```python
def test_launch_anchor_age_exceeded_writes_one_rejected_row_with_identity(tmp_path, monkeypatch):
    # Use post-bootstrap anchor but now beyond recovery delay.
    # Assert one events_rejected row with rejected_reason + rejection_reason and identity.
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_historical_anchor_pre_bootstrap_writes_terminal_ignored_state_not_events_rejected \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_historical_anchor_pre_bootstrap_is_idempotent_across_polls \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py::test_launch_anchor_age_exceeded_writes_one_rejected_row_with_identity \
  -q
```

Expected: FAIL.

**Step 3: Wire `status == "ignored"` path**

In runner classify loop, before eligible/rejected handling:

```python
if status == "ignored" and reason == "ignored_historical_anchor_pre_bootstrap":
    terminal_state = build_terminal_ignored_state(flat_event, reason, reason, now_ms, eligibility_diag)
    states[event_symbol_id] = terminal_state
    terminal_states_by_stable_event_symbol_key[terminal_state.stable_event_symbol_key] = terminal_state
    terminal_states_by_terminal_hygiene_id[terminal_state.terminal_hygiene_id] = terminal_state
    append_jsonl(state_file, terminal_state.to_dict())
    diagnostic_path = build_daily_path(output_root, "historical_anchor_hygiene_diagnostics", now_ms)
    append_jsonl(diagnostic_path, build_historical_anchor_hygiene_diagnostic(terminal_state, now_ms))
    continue
```

Ensure diagnostics are sample-capped per type per root/poll using config.

**Step 4: Wire normal rejected builder**

Replace ad-hoc `events_rejected` dict with `build_rejected_event_symbol_row()` for non-pre-watermark, non-historical terminal rejection.

Also write terminal rejected state to `observer_state.jsonl` before/with audit row so subsequent polls hit `event_symbol_id in states`.

**Step 5: Run tests**

Expected: PASS.

**Step 6: Commit**

```bash
git add scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
git commit -m "fix: make stage1 5f terminal ignored and rejected paths idempotent"
```

---

### Task 8: Add Crash Reconciliation for Terminal Hygiene Artifacts

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py` if helper belongs there
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing crash recovery tests**

Add:

```python
def test_restart_after_terminal_state_write_repairs_missing_diagnostic_row(tmp_path, monkeypatch):
    # Precreate observer_state.jsonl with ignored_historical_anchor_pre_bootstrap terminal state.
    # Do not create historical_anchor_hygiene_diagnostics row.
    # Run max-polls=1 with same event fixture.
    # Assert diagnostic row is backfilled once.


def test_restart_after_diagnostic_write_does_not_duplicate_row(tmp_path, monkeypatch):
    # Precreate state and diagnostic row with same terminal_hygiene_id.
    # Run max-polls=1.
    # Assert diagnostic row count remains 1.


def test_restart_after_diagnostic_write_repairs_missing_terminal_state(tmp_path, monkeypatch):
    # Precreate diagnostic artifact but no observer_state terminal state.
    # Run max-polls=1.
    # Assert terminal ignored state is reconstructed and diagnostic is not duplicated.


def test_restart_after_rejected_audit_write_repairs_missing_rejected_state(tmp_path, monkeypatch):
    # Precreate events_rejected row with terminal_hygiene_id but no state.
    # Run max-polls=1.
    # Assert terminal rejected state is reconstructed and events_rejected is not duplicated.


def test_capped_terminal_state_does_not_trigger_diagnostic_backfill(tmp_path, monkeypatch):
    # Terminal state has diagnostic_expected=false due to cap.
    # Restart does not write missing diagnostic.
```

**Step 2: Run failing tests**

Expected: FAIL because reconciliation missing.

**Step 3: Implement reconciliation**

On startup after loading `states`, build all terminal indexes:

```python
states_by_event_symbol_id
terminal_states_by_stable_event_symbol_key
terminal_states_by_terminal_hygiene_id
existing_historical_diagnostic_ids
existing_rejected_audit_ids
```

Implement four-state reconciliation:

```text
state missing + artifact missing:
  normal first create

state exists + artifact missing:
  backfill only if state.terminal_audit_row exists and diagnostic_expected=true for diagnostics

state missing + artifact exists:
  reconstruct terminal state from canonical artifact row and append observer_state

state exists + artifact exists:
  no-op
```

For normal rejected state, backfill `events_rejected` only from persisted `terminal_audit_row`; do not reconstruct from current event/now. If `terminal_audit_row` is missing, write malformed diagnostic, not normal rejected.

Diagnostic sample cap must be durable: only states with `diagnostic_expected=true` are eligible for diagnostic backfill. Capped states set `diagnostic_sample_reserved=false`, `diagnostic_expected=false`, `diagnostic_emitted=false` and must not trigger reconciliation backfill.

**Step 4: Run tests**

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
git commit -m "fix: reconcile stage1 5f terminal hygiene artifacts on restart"
```

---

### Task 9: Add Summary Hygiene Metrics

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`

**Step 1: Write failing summary tests**

Add:

```python
def test_summary_counts_historical_ignored_latest_states_as_gauge():
    active = EventSymbolState(event_symbol_id="b", status="active")
    ignored = EventSymbolState(
        event_symbol_id="a",
        status="ignored_historical_anchor_pre_bootstrap",
        terminal_hygiene_id="id-a",
        stable_event_symbol_key="article|futures_contract_launch|AUSDT",
    )
    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_running_no_new_event",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="stage1_5d.json",
        stage1_5e_summary_path="stage1_5e.json",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=0,
        pre_watermark_events_ignored=0,
        post_watermark_events_accepted=0,
        active_states=[active],
        completed_states=[],
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[],
        heartbeat_rows=[],
        pending_states=[],
        terminal_states=[ignored],
    )
    assert summary.historical_anchor_ignored_count == 1


def test_summary_new_hygiene_fields_default_for_legacy_compatibility():
    summary = LiveDepthObserverSummary(
        decision="stage1_5f_observer_running_no_new_event",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="stage1_5d.json",
        stage1_5e_summary_path="stage1_5e.json",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=0,
        pre_watermark_events_ignored=0,
        post_watermark_events_accepted=0,
        active_observation_count=0,
        completed_observation_count=0,
        expired_observation_count=0,
        failed_observation_count=0,
        min_snapshot_count_required=576,
        total_snapshots_collected=0,
        request_success_rate=1.0,
        total_requests_made=0,
        failed_requests_count=0,
        consecutive_network_errors=0,
        max_consecutive_network_errors_seen=0,
        last_heartbeat_at_ms=0,
        heartbeat_count=0,
        execution_feasibility_claim_allowed=False,
        trade_signal_allowed=False,
        paper_trading_allowed=False,
        live_trading_allowed=False,
        execution_engine_allowed=False,
        alpha_interpretation_allowed=False,
        research_result_valid=False,
    )
    assert summary.historical_anchor_ignored_count == 0
    assert summary.rejected_missing_identity_count == 0
```

If current builder does not accept `terminal_states`, update expected plan to compute terminal gauges from all loaded `states.values()` passed by runner.

**Step 2: Run failing tests**

Expected: FAIL.

**Step 3: Add dataclass fields with defaults**

Add to summary model:

```python
historical_anchor_ignored_count: int = 0
rejected_event_symbol_count: int = 0
malformed_terminal_diagnostic_count: int = 0
historical_anchor_newly_ignored_this_poll: int = 0
terminal_state_hits_this_poll: int = 0
malformed_rows_seen_this_poll: int = 0
terminal_state_hits_this_poll: int = 0
historical_anchor_duplicate_suppressed_total: int = 0  # only if derived from durable state duplicate_suppressed_count
rejected_event_symbol_duplicate_suppressed_total: int = 0  # only if derived from durable state duplicate_suppressed_count
terminal_ignored_revision_seen_count: int = 0
rejected_missing_identity_count: int = 0
rejected_missing_reason_count: int = 0
rejection_hygiene_diagnostic_count: int = 0
bootstrap_watermark_missing_diagnostic_count: int = 0
```

**Step 4: Update builder**

Compute gauges from latest states, not raw append count.

**Step 5: Update runner summary call**

Pass terminal states or all latest states as needed.

**Step 6: Run tests**

Expected: PASS.

**Step 7: Commit**

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py
git commit -m "feat: expose stage1 5f terminal hygiene summary metrics"
```

---

### Task 10: Regression Suite for Existing Launch-Time Gate Behavior

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

**Step 1: Ensure regression tests exist or add them**

Required tests:

```text
test_future_launch_pending_still_does_not_write_rejected_row
test_anchor_conflict_for_post_bootstrap_future_event_still_pending
test_pre_watermark_ignored_does_not_write_events_rejected_row
test_clean_post_watermark_event_acceptance_unaffected
test_historical_ignored_diagnostic_sample_is_capped_per_type
```

For diagnostic cap, create > cap duplicate historical events and assert diagnostic rows per type <= config.

**Step 2: Run targeted regression**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: PASS.

**Step 3: Commit**

```bash
git add tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
git commit -m "test: cover stage1 5f terminal hygiene regressions"
```

---

### Task 11: Full Verification and Safety Grep

**Files:**
- No source edits unless verification reveals failures.

**Step 1: Run focused 1.5F suite**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: PASS.

**Step 2: Run 1.5G compatibility suite**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  -q
```

Expected: PASS.

**Step 3: Compile changed modules**

```bash
PYTHONPATH=src:. .venv/bin/python -m py_compile \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py
```

Expected: no output.

**Step 4: Safety grep**

```bash
grep -RInE 'paper_trading_allowed\s*[:=]\s*True|live_trading_allowed\s*[:=]\s*True|execution_engine_allowed\s*[:=]\s*True|trade_signal_allowed\s*[:=]\s*True|alpha_interpretation_allowed\s*[:=]\s*True' \
  configs src scripts \
  --exclude-dir='__pycache__' || true
```

Expected: no output. Tests may contain explicit unsafe-true negative fixtures; inspect those separately if this grep is expanded to `tests`.

**Step 5: Diff check**

```bash
git diff --check
```

Expected: no output.

**Step 6: Commit verification-only doc/test updates if any**

```bash
git status --short
```

Commit only if new files remain uncommitted.

---

### Task 12: Production Deployment Notes and Review Doc Update

**Files:**
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

**Step 1: Add short monitoring subsection**

Add a subsection under Stage 1.5F launch-time gated checks:

````markdown
### Stage 1.5F terminal hygiene 专项检查

```bash
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null | python -m json.tool | grep -E \
"historical_anchor_ignored_count|rejected_event_symbol_count|malformed_terminal_diagnostic_count|historical_anchor_duplicate_suppressed_total|rejected_missing_identity_count|rejected_missing_reason_count|rejection_hygiene_diagnostic_count|bootstrap_watermark_missing_diagnostic_count" || true

wc -l "$STAGE1_5F_OUT"/events_rejected/*.jsonl 2>/dev/null || true
sleep 120
wc -l "$STAGE1_5F_OUT"/events_rejected/*.jsonl 2>/dev/null || true

find "$STAGE1_5F_OUT" -maxdepth 2 -type f \
  \( -path '*/historical_anchor_hygiene_diagnostics/*' -o -path '*/rejection_hygiene_diagnostics/*' \) \
  -print -exec wc -l {} \; 2>/dev/null || true
```

判定：historical old anchors 不应持续增加 normal `events_rejected`；新 normal rejected rows 必须有 identity 和 reason。
````

**Step 2: Run markdown diff check**

```bash
git diff --check docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

Expected: no output.

**Step 3: Commit docs update**

```bash
git add docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
git commit -m "docs: add stage1 5f terminal hygiene checks"
```

---

## Production Acceptance Checklist

After deployment to a new root suffix `_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`, run:

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix' | sort | tail -n 1)"

cat "$STAGE1_5F_OUT/watermark.json" 2>/dev/null | python -m json.tool | grep -E \
"watermark_schema_version|bootstrap_root_id|bootstrap_max_seen_detected_at_ms|bootstrap_created_at_ms" || true

cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null | python -m json.tool | grep -E \
"historical_anchor_ignored_count|rejected_event_symbol_count|malformed_terminal_diagnostic_count|historical_anchor_duplicate_suppressed_total|rejected_missing_identity_count|rejected_missing_reason_count|pending_launch_observation_count|active_observation_count|total_snapshots_collected" || true

wc -l "$STAGE1_5F_OUT"/events_rejected/*.jsonl 2>/dev/null || true
sleep 120
wc -l "$STAGE1_5F_OUT"/events_rejected/*.jsonl 2>/dev/null || true
```

Pass criteria:

```text
active_observation_count = 0 implies total_snapshots_collected = 0
historical old anchors do not write normal events_rejected
normal events_rejected does not grow every poll without genuine post-bootstrap failures
rejected_missing_identity_count = 0
rejected_missing_reason_count = 0
pending_launch_observation_count is not held by historical old anchors
watermark_schema_version = 2
bootstrap_root_id present
bootstrap_max_seen_detected_at_ms present
```

## Final Safety Notes

```text
Do not patch production output roots in place.
Do not delete old events_rejected files.
Do not convert historical ignored rows into accepted or rejected evidence.
Do not run 1.5G clean/quarantine review against diagnostic streams.
Do not deploy during an active 12h clean observation unless explicitly preserving the old root for that event.
```
