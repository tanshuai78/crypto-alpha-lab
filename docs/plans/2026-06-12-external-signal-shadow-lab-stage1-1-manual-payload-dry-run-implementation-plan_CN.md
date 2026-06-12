# External Signal Shadow Lab Stage 1.1 Manual Payload Dry Run Implementation Plan

> **For Codex / Claude:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. For code changes use `test-driven-development`. Do **not** commit automatically unless the user explicitly asks.

**Goal:** Add a manual-export dry run for one real read-only source profile, `gate_marketanalysis_manual_export`, and distinguish `connector-valid` from `stage0_handoff_ready` using strict source-quality gates.

**Architecture:** Reuse the existing Stage 1 file-backed connector. Add source-profile metadata, manual-export provenance validation, Stage 1.1 CEX symbol whitelist, source-quality metrics, handoff mode, and a stricter `stage0_handoff_ready` gate. Fixture data is only for tests; the Stage 1.1 review artifact must be generated from a real manual raw file under `data/external_signal_shadow/raw/`.

**Tech Stack:** Python stdlib, existing `configs/base.py`, `src/research/external_signal_shadow/*`, pytest, ruff.

---

## 0. Preconditions, Runtime Data Safety, And Non-Negotiable Boundaries

Run all commands from:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/.worktrees/external-signal-shadow-stage1
```

Before implementation, check:

```bash
git status --short --branch
PYTHONPATH=. uv run pytest tests/research/test_external_signal_shadow_stage1_*.py tests/scripts/test_*external_signal_shadow_stage1*.py -q
```

Expected:

- Current branch is `feature/external-signal-shadow-stage1`.
- Existing Stage 1 tests pass.
- If unrelated dirty files appear, stop and ask.
- Do not connect to external websites or APIs.
- Do not add exchange API keys, wallet fields, paper trading, or execution paths.
- Do not commit automatically.

### Task 0.1: Verify `.gitignore` Covers Runtime Raw And Normalized Data

**Files:**

- Modify if needed: `.gitignore`
- Test/verify: shell commands only

**Step 1: Check current ignore rules**

Run:

```bash
grep -n "data/external_signal_shadow/raw/" .gitignore || true
grep -n "data/external_signal_shadow/normalized/" .gitignore || true
```

**Step 2: Add missing ignore rules**

If missing, append:

```gitignore
data/external_signal_shadow/raw/
data/external_signal_shadow/normalized/
```

**Step 3: Verify ignore behavior**

Run:

```bash
mkdir -p data/external_signal_shadow/raw/gate_marketanalysis_manual_export data/external_signal_shadow/normalized
touch data/external_signal_shadow/raw/gate_marketanalysis_manual_export/2026-06-12.jsonl
touch data/external_signal_shadow/normalized/stage1_1_gate_marketanalysis_manual_events.jsonl
git check-ignore data/external_signal_shadow/raw/gate_marketanalysis_manual_export/2026-06-12.jsonl
git check-ignore data/external_signal_shadow/normalized/stage1_1_gate_marketanalysis_manual_events.jsonl
```

Expected: both paths are printed by `git check-ignore`.

---

## Task 1: Add Stage 1.1 Config Constants With Audit Comments

**Files:**

- Modify: `configs/base.py`
- Modify tests: `tests/research/test_external_signal_shadow_stage1_connector.py`

**Step 1: Write failing config test**

Add near `test_external_signal_stage1_connector_config_constants_exist`:

```python
def test_external_signal_stage1_1_manual_dry_run_config_constants_exist():
    from configs import base

    assert base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE == "gate_marketanalysis_manual_export"
    assert base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_VENDOR == "gate"
    assert base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SURFACE == "gate_big_data_dashboard"
    assert base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_CAPTURE_METHOD == "manual_export"
    assert base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SKILL == "gate_exchange_marketanalysis"
    assert base.EXTERNAL_SIGNAL_STAGE1_1_ALLOWED_SYMBOLS == (
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MIN_RAW_PAYLOADS == 10
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MIN_EMITTED_EVENTS == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_RAW_PAYLOADS == 20
    assert base.EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_EMITTED_EVENTS == 5
    assert base.EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_UNIQUE_SYMBOLS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_UNIQUE_TIME_BUCKETS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MAX_EVENT_TIME_FALLBACK_RATIO == 0.50
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MAX_PRICE_MAPPING_UNAVAILABLE_RATIO == 0.30
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MAX_REJECTED_PAYLOAD_RATIO == 0.30
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_SYMBOL_DOMINANCE_RATIO == 0.70
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_TIME_BUCKET_DOMINANCE_RATIO == 0.70
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MAX_DUPLICATE_RATIO == 0.50
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MAX_UNKNOWN_EVENT_TYPE_RATIO == 0.30
    assert base.EXTERNAL_SIGNAL_STAGE1_1_MAX_MISSING_REQUIRED_FIELD_RATIO == 0.30
```

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=. uv run pytest tests/research/test_external_signal_shadow_stage1_connector.py::test_external_signal_stage1_1_manual_dry_run_config_constants_exist -q
```

Expected: FAIL because constants do not exist.

**Step 3: Implement constants with comments**

Append to the external signal connector section of `configs/base.py`. Every constant must include a short comment. Use this exact style:

```python
EXTERNAL_SIGNAL_STAGE1_1_SOURCE = "gate_marketanalysis_manual_export"
# Internal source id for Stage 1.1 manual-export dry run. Not a vendor API name.

EXTERNAL_SIGNAL_STAGE1_1_SOURCE_VENDOR = "gate"
# External vendor label used for source attribution in summaries and reviews.

EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SURFACE = "gate_big_data_dashboard"
# Human-readable surface where manual observations are collected.

EXTERNAL_SIGNAL_STAGE1_1_SOURCE_CAPTURE_METHOD = "manual_export"
# Capture method for Stage 1.1. HTTP/API collection remains explicitly out of scope.

EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SKILL = "gate_exchange_marketanalysis"
# Internal source_skill label used when normalizing manually captured market-analysis payloads.

EXTERNAL_SIGNAL_STAGE1_1_ALLOWED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
# CEX majors whitelist for Stage 1.1. Prevents a manual Gate dashboard dry run from drifting into small-cap discovery.

EXTERNAL_SIGNAL_STAGE1_1_MIN_RAW_PAYLOADS = 10
# Minimum raw manual-export payload count for connector-valid status. Below this, data density is insufficient even for dry run.

EXTERNAL_SIGNAL_STAGE1_1_MIN_EMITTED_EVENTS = 1
# Minimum normalized event count for connector-valid status. This is not enough for Stage 0 handoff.

EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_RAW_PAYLOADS = 20
# Minimum raw manual-export payload count before Stage 0 handoff can be considered. Safe range: 20-100 for manual dry run.

EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_EMITTED_EVENTS = 5
# Minimum emitted event count before Stage 0 handoff can be considered.

EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_UNIQUE_SYMBOLS = 3
# Minimum distinct emitted symbols for handoff. Prevents single-symbol dashboard refreshes from looking like broad signal coverage.

EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_UNIQUE_TIME_BUCKETS = 3
# Minimum distinct event-time buckets for handoff. Prevents one-time clustered samples from passing as source coverage.

EXTERNAL_SIGNAL_STAGE1_1_MAX_EVENT_TIME_FALLBACK_RATIO = 0.50
# Maximum fraction of emitted events whose event_time_ms was derived from available_at_ms. Above this, event timing is not replay-trustworthy.

EXTERNAL_SIGNAL_STAGE1_1_MAX_PRICE_MAPPING_UNAVAILABLE_RATIO = 0.30
# Maximum fraction of raw payloads quarantined because no local price series exists. Above this, source does not fit current lab coverage.

EXTERNAL_SIGNAL_STAGE1_1_MAX_REJECTED_PAYLOAD_RATIO = 0.30
# Maximum rejected/raw ratio for handoff readiness. High rejection means schema/source quality is unstable.

EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_SYMBOL_DOMINANCE_RATIO = 0.70
# Maximum emitted-event concentration in one symbol before source quality is considered too concentrated.

EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_TIME_BUCKET_DOMINANCE_RATIO = 0.70
# Maximum emitted-event concentration in one time bucket before source quality is considered too clustered.

EXTERNAL_SIGNAL_STAGE1_1_MAX_DUPLICATE_RATIO = 0.50
# Maximum deduped/raw ratio before source quality is considered dominated by repeated dashboard refreshes.

EXTERNAL_SIGNAL_STAGE1_1_MAX_UNKNOWN_EVENT_TYPE_RATIO = 0.30
# Maximum unsupported-event/raw ratio before source event taxonomy is considered too unstable.

EXTERNAL_SIGNAL_STAGE1_1_MAX_MISSING_REQUIRED_FIELD_RATIO = 0.30
# Maximum missing-required-field/raw ratio before manual payload quality is considered insufficient.
```

**Step 4: Verify GREEN**

Run the same pytest command. Expected: PASS.

---

## Task 2: Add Source Profile And Strict Manual Provenance Schema

**Files:**

- Create: `src/research/external_signal_shadow/source_profiles.py`
- Modify: `src/research/external_signal_shadow/schemas.py`
- Test: `tests/research/test_external_signal_shadow_stage1_1_manual_dry_run.py`

**Step 1: Write failing tests**

Create `tests/research/test_external_signal_shadow_stage1_1_manual_dry_run.py`:

```python
import pytest


def _manual_payload(**overrides):
    payload = {
        "source": "gate_marketanalysis_manual_export",
        "source_vendor": "gate",
        "source_surface": "gate_big_data_dashboard",
        "source_capture_method": "manual_export",
        "source_skill": "gate_exchange_marketanalysis",
        "data_quality": "manual_export",
        "capture_id": "gate_big_data_20260612_001",
        "captured_by": "manual",
        "source_observed_at_ms": 1781165880000,
        "fetched_at_ms": 1781165880000,
        "available_at_ms": 1781165880000,
        "manual_transform_version": "stage1_1_v0",
        "field_confidence": {
            "event_time_ms": "source_provided",
            "symbol": "source_provided",
            "score": "source_native",
        },
        "raw_payload": {
            "event_type": "cex_market_tape_anomaly",
            "chain": "cex",
            "symbol": "SOLUSDT",
            "event_time_ms": 1781165400000,
            "score": 78.0,
            "score_scale": "source_native",
            "score_interpretation_allowed": False,
            "metadata": {"event_time_policy": "source_provided"},
        },
    }
    payload.update(overrides)
    return payload


def test_gate_manual_source_profile_uses_internal_source_id():
    from src.research.external_signal_shadow.source_profiles import get_source_profile

    profile = get_source_profile("gate_marketanalysis_manual_export")

    assert profile.source == "gate_marketanalysis_manual_export"
    assert profile.source_vendor == "gate"
    assert profile.source_surface == "gate_big_data_dashboard"
    assert profile.source_capture_method == "manual_export"
    assert profile.source_skill == "gate_exchange_marketanalysis"
    assert "BTCUSDT" in profile.allowed_symbols


def test_raw_skill_payload_accepts_complete_manual_provenance_fields():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = RawSkillPayload.from_dict(_manual_payload())

    assert payload.source_vendor == "gate"
    assert payload.source_surface == "gate_big_data_dashboard"
    assert payload.source_capture_method == "manual_export"
    assert payload.capture_id == "gate_big_data_20260612_001"
    assert payload.field_confidence["event_time_ms"] == "source_provided"


def test_manual_export_rejects_missing_capture_id():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = _manual_payload()
    payload.pop("capture_id")

    with pytest.raises(ValueError, match="capture_id"):
        RawSkillPayload.from_dict(payload)


def test_manual_export_source_profile_mismatch_rejected():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    with pytest.raises(ValueError, match="source profile"):
        RawSkillPayload.from_dict(_manual_payload(source_vendor="binance"))


def test_field_confidence_value_must_be_allowed():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = _manual_payload()
    payload["field_confidence"]["event_time_ms"] = "manual_guess"

    with pytest.raises(ValueError, match="field_confidence"):
        RawSkillPayload.from_dict(payload)


def test_available_at_fallback_requires_event_time_equals_available_at():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = _manual_payload()
    payload["field_confidence"]["event_time_ms"] = "available_at_fallback"
    payload["raw_payload"]["metadata"]["event_time_policy"] = "available_at_fallback"
    payload["raw_payload"]["event_time_ms"] = payload["available_at_ms"] - 60_000

    with pytest.raises(ValueError, match="available_at_fallback"):
        RawSkillPayload.from_dict(payload)


def test_score_interpretation_allowed_must_be_false_for_manual_source():
    from src.research.external_signal_shadow.schemas import RawSkillPayload

    payload = _manual_payload()
    payload["raw_payload"]["score_interpretation_allowed"] = True

    with pytest.raises(ValueError, match="score_interpretation_allowed"):
        RawSkillPayload.from_dict(payload)
```

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=. uv run pytest tests/research/test_external_signal_shadow_stage1_1_manual_dry_run.py -q
```

Expected: FAIL because source profile and strict schema validation do not exist.

**Step 3: Implement source profile**

Create `src/research/external_signal_shadow/source_profiles.py` with a `SourceProfile` dataclass and `get_source_profile(source)` using `configs/base.py` Stage 1.1 constants.

**Step 4: Extend RawSkillPayload**

Modify `src/research/external_signal_shadow/schemas.py`:

- Add fields: `source_vendor`, `source_surface`, `source_capture_method`, `capture_id`, `captured_by`, `source_observed_at_ms`, `manual_transform_version`, `field_confidence`.
- If `data_quality == "manual_export"`, require all fields above.
- Validate source profile matches `configs/base.py` constants.
- Validate allowed field confidence values:

```python
FIELD_CONFIDENCE_ALLOWED = {
    "event_time_ms": {"source_provided", "available_at_fallback"},
    "symbol": {"source_provided", "normalized", "missing"},
    "score": {"source_native", "manual_scaled", "missing"},
}
```

- Validate consistency:
  - `event_time_policy == "available_at_fallback"` requires `field_confidence["event_time_ms"] == "available_at_fallback"` and `raw_payload["event_time_ms"] == available_at_ms`.
  - `event_time_policy == "source_provided"` requires `field_confidence["event_time_ms"] == "source_provided"`.
  - `score_interpretation_allowed` must be `False` for manual source when present.

**Step 5: Verify GREEN**

Run the Stage 1.1 schema tests. Expected: PASS.

---

## Task 3: Add Fixture Payloads, Real Manual Raw Placeholder, And Price Map Coverage

**Files:**

- Create: `tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl`
- Create runtime local file, ignored by git: `data/external_signal_shadow/raw/gate_marketanalysis_manual_export/2026-06-12.jsonl`
- Modify: `tests/fixtures/external_signal_shadow/stage1_price_map.json`
- Modify: `configs/external_signal_shadow_price_map.json`
- Test: `tests/research/test_external_signal_shadow_stage1_1_manual_dry_run.py`

**Step 1: Write fixture tests**

Add:

```python
import json
from pathlib import Path


def _load_jsonl(path: str):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def test_stage1_1_fixture_has_minimum_manual_payload_shape():
    rows = _load_jsonl("tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl")

    assert len(rows) >= 20
    assert {row["source"] for row in rows} == {"gate_marketanalysis_manual_export"}
    assert all(row["source_vendor"] == "gate" for row in rows)
    assert all(row["source_surface"] == "gate_big_data_dashboard" for row in rows)
    assert all(row["source_capture_method"] == "manual_export" for row in rows)
    assert all(row["data_quality"] == "manual_export" for row in rows)
    assert all("capture_id" in row for row in rows)
    assert all("field_confidence" in row for row in rows)


def test_stage1_1_fixture_contains_quality_edge_cases():
    rows = _load_jsonl("tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl")
    symbols = {row["raw_payload"].get("symbol") for row in rows}
    policies = {row["raw_payload"].get("metadata", {}).get("event_time_policy") for row in rows}

    assert {"BTCUSDT", "ETHUSDT", "SOLUSDT"}.issubset(symbols)
    assert "available_at_fallback" in policies
    assert any(row["raw_payload"].get("symbol") == "PEPEUSDT" for row in rows)
```

**Step 2: Verify RED**

Run the two fixture tests. Expected: FAIL because fixture does not exist.

**Step 3: Create fixture**

Create at least 20 JSONL rows. Requirements:

- At least 5 valid emitted candidates.
- Valid rows cover at least 3 allowed symbols.
- Valid rows cover at least 3 event-time buckets.
- Include at least one `available_at_fallback` row.
- Include one unsupported symbol like `PEPEUSDT`.
- Include one missing symbol.
- Include one duplicate semantic event.
- Include one unsupported event type.
- Include one row where `score_interpretation_allowed = false`.

**Step 4: Create ignored real manual raw file**

Create:

```text
data/external_signal_shadow/raw/gate_marketanalysis_manual_export/2026-06-12.jsonl
```

For now, copy the fixture content into this ignored raw file only if the user has not yet provided real Gate manual payload. Mark all rows with `data_quality = manual_export` and `source_capture_method = manual_export`. This file must not be committed.

Important: Task 8 review artifact must use this `data/.../raw/.../2026-06-12.jsonl` path, not the fixture path.

**Step 5: Extend price maps**

Ensure both price map files include direct CEX mappings for:

```text
BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT
```

Files:

- `tests/fixtures/external_signal_shadow/stage1_price_map.json`
- `configs/external_signal_shadow_price_map.json`

**Step 6: Verify GREEN**

Run the fixture tests. Expected: PASS.

---

## Task 4: Enforce Stage 1.1 Symbol Whitelist And Event-Time Policy

**Files:**

- Modify: `src/research/external_signal_shadow/file_backed_connector.py`
- Test: `tests/research/test_external_signal_shadow_stage1_1_manual_dry_run.py`

**Step 1: Write failing behavior tests**

Add:

```python
def test_stage1_1_quarantines_symbol_outside_allowed_universe(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="gate_marketanalysis_manual_export",
    )

    assert summary["quarantine_reason_counts"]["unsupported_stage1_1_symbol"] >= 1


def test_stage1_1_available_at_fallback_not_counted_in_latency_percentiles(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="gate_marketanalysis_manual_export",
    )

    assert summary["event_time_fallback_count"] >= 1
    assert summary["event_time_fallback_ratio"] > 0.0
    assert summary["latency_sample_count"] < summary["emitted_event_count"]
```

**Step 2: Verify RED**

Run these tests. Expected: FAIL because whitelist and fallback-aware latency are not implemented.

**Step 3: Implement whitelist**

In connector processing:

- Normalize CEX symbols using existing logic.
- If `source == base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE` and normalized symbol not in `base.EXTERNAL_SIGNAL_STAGE1_1_ALLOWED_SYMBOLS`, return quarantine `unsupported_stage1_1_symbol` before price mapping.
- Do not apply this whitelist to Stage 1.0 fixture source.

**Step 4: Implement event-time policy**

In emitted metadata:

- Read `event_time_policy = raw.metadata.event_time_policy`.
- If absent, default to `source_provided`.
- Store it in metadata.
- If `event_time_policy == "available_at_fallback"`, do not add its latency to percentile samples.
- Count it in `event_time_fallback_count` and `event_time_fallback_ratio`.

**Step 5: Verify GREEN**

Run the tests. Expected: PASS.

---

## Task 5: Add Quality Metrics With Fixed Denominators And Zero-Division Safety

**Files:**

- Modify: `src/research/external_signal_shadow/file_backed_connector.py`
- Modify: `src/research/external_signal_shadow/connector_summary.py`
- Test: `tests/research/test_external_signal_shadow_stage1_1_manual_dry_run.py`

**Fixed ratio denominators:**

```text
event_time_fallback_ratio = event_time_fallback_count / emitted_event_count
duplicate_ratio = deduped_payload_count / raw_payload_count
price_mapping_unavailable_ratio = quarantine_reason_counts["price_mapping_unavailable"] / raw_payload_count
rejected_payload_ratio = rejected_payload_count / raw_payload_count
unknown_event_type_ratio = reject_reason_counts["unsupported_event_type"] / raw_payload_count
missing_required_field_ratio = missing_required_field_count / raw_payload_count
single_symbol_dominance_ratio = max(emitted_symbol_count) / emitted_event_count
single_time_bucket_dominance_ratio = max(emitted_time_bucket_count) / emitted_event_count
```

If denominator is zero, return `0.0`; other gates such as `emitted_event_count == 0` will classify the run as schema/data failure.

**Step 1: Write failing summary tests**

Add:

```python
def test_stage1_1_summary_reports_quality_and_handoff_metrics(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="gate_marketanalysis_manual_export",
    )

    assert summary["source_vendor"] == "gate"
    assert summary["source_surface"] == "gate_big_data_dashboard"
    assert summary["source_capture_method"] == "manual_export"
    assert summary["unique_symbol_count"] >= 3
    assert summary["unique_event_time_bucket_count"] >= 3
    assert 0.0 <= summary["duplicate_ratio"] <= 1.0
    assert 0.0 <= summary["price_mapping_unavailable_ratio"] <= 1.0
    assert 0.0 <= summary["rejected_payload_ratio"] <= 1.0
    assert 0.0 <= summary["unknown_event_type_ratio"] <= 1.0
    assert 0.0 <= summary["missing_required_field_ratio"] <= 1.0
    assert 0.0 <= summary["single_symbol_dominance_ratio"] <= 1.0
    assert 0.0 <= summary["single_time_bucket_dominance_ratio"] <= 1.0
    assert "minimal_connector_pass" in summary
    assert "stage0_handoff_ready" in summary
    assert "stage0_handoff_blockers" in summary


def test_stage1_1_quality_ratios_handle_zero_denominators():
    from src.research.external_signal_shadow.connector_summary import _safe_ratio

    assert _safe_ratio(1, 0) == 0.0
    assert _safe_ratio(0, 0) == 0.0
    assert _safe_ratio(1, 4) == 0.25


def test_stage1_1_summary_reports_unknown_and_missing_required_field_ratios(tmp_path):
    from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector

    output = tmp_path / "events.jsonl"
    summary = run_file_backed_connector(
        input_files=["tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl"],
        price_map_path="tests/fixtures/external_signal_shadow/stage1_price_map.json",
        output_path=str(output),
        source="gate_marketanalysis_manual_export",
    )

    assert "unknown_event_type_ratio" in summary
    assert "missing_required_field_ratio" in summary
    assert summary["unknown_event_type_ratio"] > 0.0
```

**Step 2: Verify RED**

Run these tests. Expected: FAIL.

**Step 3: Implement metrics**

Collect:

- `unique_symbol_count`
- `unique_event_time_bucket_count`
- `event_time_fallback_count`
- `latency_sample_count`
- `duplicate_ratio`
- `price_mapping_unavailable_ratio`
- `rejected_payload_ratio`
- `unknown_event_type_ratio`
- `missing_required_field_count`
- `missing_required_field_ratio`
- `single_symbol_dominance_ratio`
- `single_time_bucket_dominance_ratio`
- `stage0_replay_eligible_event_count`
- `stage0_observation_only_event_count`
- `directionless_event_count`
- `avoid_event_count`

For missing required fields, classify payloads missing core raw fields (`event_type`, `chain`, `symbol/token_address`, `event_time_ms`) with a reject/quarantine reason that increments `missing_required_field_count`.

**Step 4: Implement `_safe_ratio`**

Add `_safe_ratio(numerator, denominator) -> float` in `connector_summary.py` or a small helper module. Keep it importable for tests.

**Step 5: Verify GREEN**

Run the tests. Expected: PASS.

---

## Task 6: Add Handoff Gate, Handoff Mode, And Failure Classification

**Files:**

- Modify: `src/research/external_signal_shadow/connector_summary.py`
- Test: `tests/research/test_external_signal_shadow_stage1_1_manual_dry_run.py`

**Step 1: Write failing tests**

Add:

```python
def test_stage1_1_handoff_ready_requires_density_not_just_one_event():
    from src.research.external_signal_shadow.connector_summary import decide_stage1_connector_summary

    summary = _base_stage1_1_summary(
        raw_payload_count=10,
        emitted_event_count=1,
        unique_symbol_count=1,
        unique_event_time_bucket_count=1,
        single_symbol_dominance_ratio=1.0,
        single_time_bucket_dominance_ratio=1.0,
    )

    result = decide_stage1_connector_summary(summary)

    assert result["minimal_connector_pass"] is True
    assert result["stage0_handoff_ready"] is False
    assert "insufficient_emitted_events" in result["stage0_handoff_blockers"]


def test_price_mapping_failure_when_unavailable_ratio_high():
    from src.research.external_signal_shadow.connector_summary import decide_stage1_connector_summary

    result = decide_stage1_connector_summary(
        _base_stage1_1_summary(price_mapping_unavailable_ratio=0.60)
    )

    assert result["decision"] == "external_signal_connector_stage1_failed"
    assert result["failure_type"] == "price_mapping_failure"
    assert result["primary_blocker"] == "price_mapping_unavailable_high"


def test_stage1_1_source_quality_failure_when_event_time_unreliable():
    from src.research.external_signal_shadow.connector_summary import decide_stage1_connector_summary

    result = decide_stage1_connector_summary(
        _base_stage1_1_summary(event_time_fallback_ratio=0.80)
    )

    assert result["decision"] == "external_signal_connector_stage1_failed"
    assert result["failure_type"] == "source_quality_failure"
    assert result["primary_blocker"] == "event_time_unreliable"


def test_stage0_handoff_mode_is_observation_only_for_unknown_events():
    from src.research.external_signal_shadow.connector_summary import decide_stage1_connector_summary

    result = decide_stage1_connector_summary(
        _base_stage1_1_summary(
            stage0_replay_eligible_event_count=0,
            stage0_observation_only_event_count=5,
            directionless_event_count=5,
            avoid_event_count=0,
        )
    )

    assert result["stage0_handoff_mode"] == "observation_only"
    assert result["stage0_directional_replay_ready"] is False
    assert result["stage0_observation_handoff_ready"] is True
```

Define `_base_stage1_1_summary` in the test module with sane defaults:

```python
def _base_stage1_1_summary(**overrides):
    payload = {
        "source": "gate_marketanalysis_manual_export",
        "raw_payload_count": 20,
        "emitted_event_count": 5,
        "deduped_payload_count": 0,
        "quarantined_payload_count": 15,
        "rejected_payload_count": 0,
        "summary_accounting_ok": True,
        "output_file": "events.jsonl",
        "output_file_sha256": "abc",
        "live_trading_enabled": False,
        "exchange_paper_trading_allowed": False,
        "execution_engine_allowed": False,
        "research_shadow_replay_allowed": True,
        "wallet_required": False,
        "unique_symbol_count": 3,
        "unique_event_time_bucket_count": 3,
        "event_time_fallback_ratio": 0.0,
        "duplicate_ratio": 0.0,
        "price_mapping_unavailable_ratio": 0.0,
        "rejected_payload_ratio": 0.0,
        "unknown_event_type_ratio": 0.0,
        "missing_required_field_ratio": 0.0,
        "single_symbol_dominance_ratio": 0.50,
        "single_time_bucket_dominance_ratio": 0.50,
        "stage0_replay_eligible_event_count": 0,
        "stage0_observation_only_event_count": 5,
        "directionless_event_count": 5,
        "avoid_event_count": 0,
    }
    payload.update(overrides)
    return payload
```

**Step 2: Verify RED**

Run these tests. Expected: FAIL.

**Step 3: Implement gate and classification**

In `connector_summary.py`:

- Preserve existing Stage 1.0 behavior for fixture source.
- For Stage 1.1 source, compute:
  - `minimal_connector_pass`
  - `stage0_handoff_ready`
  - `stage0_handoff_blockers`
  - `stage0_handoff_mode`: `blocked|observation_only|directional_replay`
  - `stage0_directional_replay_ready`
  - `stage0_observation_handoff_ready`
- Classification:
  - `price_mapping_unavailable_ratio > 0.30` -> `price_mapping_failure`.
  - `event_time_fallback_ratio > 0.50` -> `source_quality_failure`, blocker `event_time_unreliable`.
  - `duplicate_ratio > 0.50` -> `source_quality_failure`.
  - `unknown_event_type_ratio > 0.30` -> `source_quality_failure`.
  - `missing_required_field_ratio > 0.30` -> `source_quality_failure`.
  - dominance ratios > 0.70 -> `source_quality_failure`.
- Do not let a non-ready handoff fail the connector by itself unless a failure threshold is breached.

**Step 4: Verify GREEN**

Run the tests. Expected: PASS.

---

## Task 7: Add Stage 1.1 CLI And Chinese Review Output

**Files:**

- Create: `scripts/run_external_signal_shadow_stage1_1_manual_dry_run.py`
- Create: `scripts/review_external_signal_shadow_stage1_1_manual_dry_run.py`
- Test: `tests/scripts/test_run_external_signal_shadow_stage1_1_manual_dry_run.py`
- Test: `tests/scripts/test_review_external_signal_shadow_stage1_1_manual_dry_run.py`

**Step 1: Write failing CLI tests**

Create script tests for:

- CLI writes events and summary.
- CLI rejects `--external-api` with exit code 1.
- Review writes Chinese markdown and contains `stage0_handoff_ready`, `stage0_handoff_mode`, and “不是 alpha 通过”.
- Review does not contain English headings like `Conclusion`.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=. uv run pytest tests/scripts/test_run_external_signal_shadow_stage1_1_manual_dry_run.py tests/scripts/test_review_external_signal_shadow_stage1_1_manual_dry_run.py -q
```

Expected: FAIL because scripts do not exist.

**Step 3: Implement CLI script**

`run_external_signal_shadow_stage1_1_manual_dry_run.py` should:

- Hardcode source from `base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE`.
- Reject `--external-api` with exit code 1.
- Call `run_file_backed_connector(...)`.
- Write sorted JSON summary.
- Print decision, failure type, `minimal_connector_pass`, `stage0_handoff_ready`, `stage0_handoff_mode`.

**Step 4: Implement review script**

Review must be Chinese and include:

- 结论。
- Source identity。
- Accounting。
- Quality metrics。
- Handoff gate and handoff mode。
- Reject/quarantine breakdown。
- 禁止推出 alpha/paper/live。

**Step 5: Verify GREEN**

Run script tests. Expected: PASS.

---

## Task 8: Run Fixture Test Dry Run And Actual Manual Raw Dry Run

Fixture is only for tests. The official Stage 1.1 artifact must use a real manual raw file path under `data/external_signal_shadow/raw/`.

### 8A. Fixture test dry run

Run:

```bash
PYTHONPATH=. uv run python scripts/run_external_signal_shadow_stage1_1_manual_dry_run.py \
  --input tests/fixtures/external_signal_shadow/stage1_1_gate_manual_payloads.jsonl \
  --price-map tests/fixtures/external_signal_shadow/stage1_price_map.json \
  --output-events /tmp/stage1_1_fixture_events.jsonl \
  --output-summary /tmp/stage1_1_fixture_summary.json
```

Expected: exit 0. This output is not the review artifact.

### 8B. Actual manual raw dry run

Run this command for the official artifact:

```bash
PYTHONPATH=. uv run python scripts/run_external_signal_shadow_stage1_1_manual_dry_run.py \
  --input data/external_signal_shadow/raw/gate_marketanalysis_manual_export/2026-06-12.jsonl \
  --price-map configs/external_signal_shadow_price_map.json \
  --output-events data/external_signal_shadow/normalized/stage1_1_gate_marketanalysis_manual_events.jsonl \
  --output-summary reports/external_signal_shadow/connectors/stage1_1_gate_marketanalysis_manual_summary.json
```

Expected:

- If actual raw file is missing, output must be `data_failure`; do not use fixture to fake Stage 1.1 success.
- If raw file exists, summary must reflect actual manual raw payload.
- Events file remains ignored by git.

### 8C. Generate review from actual summary

Run:

```bash
PYTHONPATH=. uv run python scripts/review_external_signal_shadow_stage1_1_manual_dry_run.py \
  --summary reports/external_signal_shadow/connectors/stage1_1_gate_marketanalysis_manual_summary.json \
  --output docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-1-manual-payload-dry-run-review_CN.md
```

Expected:

- Review exists.
- Review is Chinese.
- Review states whether this run is only connector-valid or also `stage0_handoff_ready`.
- Review states no alpha/paper/live conclusion.

---

## Task 9: Regression, Lint, And Safety Verification

**Step 1: Run focused tests**

```bash
PYTHONPATH=. uv run pytest \
  tests/research/test_external_signal_shadow_stage1_*.py \
  tests/scripts/test_*external_signal_shadow_stage1*.py \
  -q
```

Expected: PASS.

**Step 2: Run external signal shadow tests**

```bash
PYTHONPATH=. uv run pytest \
  tests/research/test_external_signal_shadow_*.py \
  tests/scripts/test_*external_signal_shadow*.py \
  -q
```

Expected: PASS.

**Step 3: Run scoped ruff**

Use scoped ruff to avoid unrelated historical script lint issues:

```bash
uv run ruff check \
  src/research/external_signal_shadow \
  scripts/run_external_signal_shadow_stage1_connector.py \
  scripts/review_external_signal_shadow_stage1_connector.py \
  scripts/run_external_signal_shadow_stage1_1_manual_dry_run.py \
  scripts/review_external_signal_shadow_stage1_1_manual_dry_run.py \
  tests/research/test_external_signal_shadow_stage1_connector.py \
  tests/research/test_external_signal_shadow_stage1_1_manual_dry_run.py \
  tests/scripts/test_review_external_signal_shadow_stage1_connector.py \
  tests/scripts/test_run_external_signal_shadow_stage1_1_manual_dry_run.py \
  tests/scripts/test_review_external_signal_shadow_stage1_1_manual_dry_run.py
```

Expected: `All checks passed!`

**Step 4: Run full pytest**

```bash
PYTHONPATH=. uv run pytest -q
```

Expected: PASS.

**Step 5: Check git status**

```bash
git status --short --branch
git check-ignore data/external_signal_shadow/raw/gate_marketanalysis_manual_export/2026-06-12.jsonl
git check-ignore data/external_signal_shadow/normalized/stage1_1_gate_marketanalysis_manual_events.jsonl
```

Expected:

- Runtime raw and normalized files are ignored.
- Source, tests, docs, fixture, summary/review artifacts visible for user review.
- Do not commit unless user explicitly requests.

---

## Completion Criteria

Stage 1.1 implementation is complete only if all are true:

- Stage 1.0 tests still pass.
- Stage 1.1 fixture has >=20 manual payloads and provenance fields.
- Actual Stage 1.1 review artifact is generated from `data/external_signal_shadow/raw/gate_marketanalysis_manual_export/2026-06-12.jsonl`, not from fixture.
- Connector preserves safety boundaries: no wallet/order/swap/API key, `shadow_only = true`, `notional_usd = 0.0`.
- Summary includes `minimal_connector_pass`, `stage0_handoff_ready`, and `stage0_handoff_mode`.
- `available_at_fallback` samples do not enter latency percentile calculations.
- Stage 0 replay is blocked unless `stage0_handoff_ready = true`.
- High price mapping unavailable ratio is classified as `price_mapping_failure`.
- Review is Chinese and states no alpha/paper/live conclusion.
- Scoped ruff passes.
- Full pytest passes.
- No automatic commit.
