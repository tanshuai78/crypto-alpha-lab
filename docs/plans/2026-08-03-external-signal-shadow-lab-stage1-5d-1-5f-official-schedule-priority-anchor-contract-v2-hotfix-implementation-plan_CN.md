# Stage 1.5D / 1.5F Official Schedule Priority Anchor Contract V2 Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Stage 1.5D / 1.5F / 1.5G 的 launch anchor evidence contract 升级为 `formal_event_contract_version = 2`，修复 GIGADEV 暴露的 exchangeInfo onboardDate 覆盖 official schedule anchor、后视 revision clean、fallback clean 污染、v1/v2 混用和跨阶段 lineage 缺失问题。

**Architecture:** 使用唯一共享模块 `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py` 作为 1.5D builder/writer、1.5F validator/admission、1.5G reviewer 的 anchor contract source of truth；旧 `stage1_5_launch_event_contract.py` 只能 re-export，不保留独立规则。1.5D 只写 fail-closed v2 consumable rows 和独立 schedule revision rows；1.5F 用 root-level immutable mode contract、point-in-time v2 validation、append-only schedule revision registry 和 state schema v3 维护 admission lineage；1.5G 读取 accepted/state/completed 最新 lineage，对 fallback、contamination、malformed、mismatch 一律 invalid。部署使用新 dated runbook 和新 root suffix；旧 v1 root 只读，v1 compatibility 默认关闭且只能进入 diagnostic-only root。

**Tech Stack:** Python 3, pytest, append-only JSON/JSONL artifacts, Binance official BAPI/exchangeInfo frozen fixtures, Stage 1.5D/1.5F runners, Stage 1.5G offline reviewer, read-only production deployment.

---

## 0. Non-Negotiable Rules

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
RISK_LIVE_TRADING_ENABLED = false
```

Execution rules:

```text
1. TDD first: write failing tests before implementation code.
2. Do not mutate, delete, or rewrite old production roots.
3. Do not backfill GIGADEV as clean/recovery evidence.
4. v2 production roots must not silently accept v1 rows.
5. exchangeInfo fallback can never produce clean evidence in this version.
6. exchangeinfo_fallback_clean_allowed = false is a hard invariant across 1.5D, 1.5F, and 1.5G.
7. Point-in-time schedule selection is mandatory; future revisions cannot rewrite past admission truth.
8. Revision ID lexical ordering must never resolve semantic conflicts.
9. Once observation starts, max_evidence_class can only stay same or decrease.
10. Quarantine is only for orderbook quality after anchor contract is valid; anchor lineage failures are invalid.
11. Use imports from research.external_signal_shadow..., not src.research.external_signal_shadow..., in new production code and tests.
12. Use PYTHONPATH=src:. .venv/bin/python for all tests and scripts.
```

## 0.1 Required Config Constants

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py`

Add only if missing:

```python
EXTERNAL_SIGNAL_STAGE1_5F_ALLOW_FORMAL_V1_COMPATIBILITY = False
EXTERNAL_SIGNAL_STAGE1_5_ANCHOR_PRECEDENCE_POLICY = "official_schedule_priority_v1"
EXTERNAL_SIGNAL_STAGE1_5_FORMAL_EVENT_CONTRACT_VERSION = 2
EXTERNAL_SIGNAL_STAGE1_5_FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION = 1
EXTERNAL_SIGNAL_STAGE1_5_OBSERVER_STATE_SCHEMA_VERSION = 3
EXTERNAL_SIGNAL_STAGE1_5_ANCHOR_CONTRACT_HASH_SCHEMA_VERSION = 1
```

Expected behavior:

```text
v1 compatibility default = false
v2 contract version is the only production consumable version
schedule revision contract version = 1
observer state schema version = 3
anchor hash schema version = 1
```

Verification:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py -q
```

---

## Task 1: Preflight and Current-State Inventory

**Files:**
- Read: `configs/base.py`
- Read: `src/research/external_signal_shadow/stage1_5_launch_event_contract.py`
- Read: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Read: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py`
- Read: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Read: `docs/designs/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-launch-time-priority-anchor-precedence-hotfix-design_CN.md`

**Step 1: Locate current v1 scalar anchor contract**

```bash
rg -n "FORMAL_CONTRACT_VERSION|formal_event_contract_version|launch_anchor_evidence_level|launch_anchor_comparison_status|launch_anchor_disagreement_ms|launch_anchor_validation_status" \
  src/research/external_signal_shadow/stage1_5_launch_event_contract.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests -g '*.py'
```

Expected:

```text
All v1 scalar producer/consumer/test sites are identified before edits.
```

**Step 2: Locate all import surfaces and eliminate double-module risk**

```bash
rg -n "stage1_5_launch_event_contract|stage1_5_launch_anchor_contract|src\.research\.external_signal_shadow|research\.external_signal_shadow" \
  src scripts tests -g '*.py'
```

Expected:

```text
Existing legacy imports are known.
New code will use research.external_signal_shadow.stage1_5_launch_anchor_contract only.
stage1_5_launch_event_contract.py will be reduced to compatibility re-export if still imported.
```

**Step 3: Locate Stage 1.5F state and active selectors**

```bash
rg -n "EventSymbolState|observer_state_schema_version|events_accepted|observer_state|completed|to_dict|from_dict|build_accepted_row_from_state|status == ['\"]active|active_observation|capacity" \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
```

Expected:

```text
All surfaces that must preserve contaminated active depth collection are known.
```

**Step 4: Locate 1.5G accepted/state/completed loaders and reducers**

```bash
rg -n "events_accepted|observer_state|completed|latest|event_symbol_id|clean_depth_evidence_pass|quarantined_depth_evidence_pass|blockers|decision" \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_*.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
```

Expected:

```text
All 1.5G evidence input paths and latest-state reducer behavior are known before Task 12.
```

---

## Task 2: Freeze GIGADEV V2 Regression Fixtures With Hash Provenance

**Files:**
- Add: `tests/fixtures/external_signal_shadow/stage1_5d/gigadev_anchor_contract_v2/gigadev_bapi_article_detail_real_frozen_fixture.json`
- Add: `tests/fixtures/external_signal_shadow/stage1_5d/gigadev_anchor_contract_v2/gigadev_fixture_metadata.json`
- Add: `tests/fixtures/external_signal_shadow/stage1_5d/gigadev_anchor_contract_v2/gigadev_exchangeinfo_onboard_earlier.json`
- Add: `tests/fixtures/external_signal_shadow/stage1_5d/gigadev_anchor_contract_v2/gigadev_legacy_v1_bad_event.json`
- Add: `tests/fixtures/external_signal_shadow/stage1_5f/gigadev_anchor_contract_v2/gigadev_pending_anchor_conflict_state_from_old_root.json`
- Test: `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py`

**Step 1: Write failing fixture metadata load and hash test**

Add:

```python
def test_gigadev_anchor_contract_v2_fixture_metadata_loads_and_hashes_match():
    import hashlib
    import json
    from pathlib import Path

    root = Path("tests/fixtures/external_signal_shadow/stage1_5d/gigadev_anchor_contract_v2")
    meta = json.loads((root / "gigadev_fixture_metadata.json").read_text())
    payload_bytes = (root / "gigadev_bapi_article_detail_real_frozen_fixture.json").read_bytes()

    assert meta["article_id"] == "e8bfd0c5adaf4d8a880bb1b7327107ef"
    assert meta["symbol"] == "GIGADEVUSDT"
    assert meta["official_schedule_anchor_ms"] == 1785735000000
    assert meta["exchangeinfo_onboardDate_ms"] == 1785722400000
    assert meta["expected_contract_version"] == 2
    assert meta["expected_primary_anchor_source"] == "official_schedule_anchor"
    assert meta["expected_clean_evidence_for_historical_incident"] is False
    assert hashlib.sha256(payload_bytes).hexdigest() == meta["payload_sha256"]
    assert meta["payload_sha256"] == meta["manifest_payload_sha256"]
    assert meta["fixture_sha256"]
    assert meta["request_url_sha256"]
    assert meta["payload_trusted"] is True
    assert meta["http_status"] == 200
    assert meta["parser_version"] == "stage1_5d_symbol_extraction_v3"
```

**Step 2: Run and confirm fail before fixtures exist**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py::test_gigadev_anchor_contract_v2_fixture_metadata_loads_and_hashes_match -q
```

Expected:

```text
FAIL because fixture files do not exist or metadata hashes are incomplete.
```

**Step 3: Create fixtures from synced production evidence**

Use local synced evidence if present. If missing, pull only the minimal server files before fixture creation; do not pull full `data/`.

Required metadata shape:

```json
{
  "article_id": "e8bfd0c5adaf4d8a880bb1b7327107ef",
  "symbol": "GIGADEVUSDT",
  "official_schedule_anchor_ms": 1785735000000,
  "exchangeinfo_onboardDate_ms": 1785722400000,
  "disagreement_ms": 12600000,
  "disagreement_direction": "exchangeinfo_earlier",
  "incident_class": "exchangeinfo_onboarddate_earlier_than_official_schedule",
  "expected_contract_version": 2,
  "expected_primary_anchor_source": "official_schedule_anchor",
  "expected_no_anchor_conflict": true,
  "expected_clean_evidence_for_historical_incident": false,
  "not_clean_evidence_reason": "missed_recovery_window_due_to_prior_deployment_and_anchor_precedence_bugs",
  "request_id": "...",
  "fetched_at_ms": 1785740141440,
  "http_status": 200,
  "request_url_sha256": "...",
  "manifest_payload_sha256": "...",
  "payload_sha256": "...",
  "fixture_sha256": "...",
  "payload_trusted": true,
  "request_manifest_path": "...",
  "parser_version": "stage1_5d_symbol_extraction_v3",
  "point_in_time_status": "post_incident_regression_fixture"
}
```

**Step 4: Verify fixture smoke test passes**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py::test_gigadev_anchor_contract_v2_fixture_metadata_loads_and_hashes_match -q
```

Expected:

```text
PASS
```

---

## Task 3: Choose and Lock the Single Shared Anchor Contract Module

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`
- Modify: `src/research/external_signal_shadow/stage1_5_launch_event_contract.py`
- Modify: all new/changed imports in `src/`, `scripts/`, `tests/`
- Test: `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py`

**Step 1: Write failing import-source test**

Add:

```python
def test_anchor_contract_single_source_of_truth_imports():
    from research.external_signal_shadow import stage1_5_launch_anchor_contract as anchor_contract
    from research.external_signal_shadow import stage1_5_launch_event_contract as legacy_contract

    assert legacy_contract.validate_launch_anchor_contract is anchor_contract.validate_launch_anchor_contract
    assert legacy_contract.build_symbol_anchor_contract is anchor_contract.build_symbol_anchor_contract
```

**Step 2: Write static namespace guard test**

Add a test that scans new hotfix test files and asserts they do not import from `src.research.external_signal_shadow`.

```python
def test_new_anchor_contract_tests_do_not_import_via_src_namespace():
    from pathlib import Path

    paths = [Path("tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py")]
    for path in paths:
        assert "from src.research.external_signal_shadow" not in path.read_text()
```

**Step 3: Implement compatibility re-export only**

`stage1_5_launch_event_contract.py` must not contain independent v2 business rules. It should either remain legacy v1-only or re-export v2 functions from `stage1_5_launch_anchor_contract.py` with a short compatibility comment.

Required import style in new code:

```python
from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
    build_formal_event_anchor_contract_row,
    build_symbol_anchor_contract,
    validate_launch_anchor_contract,
)
```

**Step 4: Run import-source tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py::test_anchor_contract_single_source_of_truth_imports \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py::test_new_anchor_contract_tests_do_not_import_via_src_namespace -q
```

Expected:

```text
PASS. There is only one v2 anchor contract implementation module.
```

---

## Task 4: Add Anchor Contract V2 Selector, Builder, Validator, and Hash Tests

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py`
- Modify: `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`

**Step 1: Write failing return-type tests**

```python
def test_symbol_builder_returns_symbol_contract_not_event_row():
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import build_symbol_anchor_contract

    contract = build_symbol_anchor_contract(
        symbol="GIGADEVUSDT",
        official_schedule_anchor_ms=1785735000000,
        exchangeinfo_onboard_date_ms=1785722400000,
        anchor_contract_decision_at_ms=1785726000000,
        official_schedule_revision_id="gigadev_rev_1",
        official_schedule_available_at_ms=1785724209135,
        mapping_confidence="exact_single_symbol",
        provenance={"payload_sha256": "sha", "parser_version": "test", "raw_time_text": "2026-08-03 05:30 (UTC)", "timezone_text": "UTC", "node_path": "body[0]", "logical_block_id": "block-1", "schedule_text_context": "Launch Time"},
    )

    assert contract["symbol"] == "GIGADEVUSDT"
    assert "formal_event_contract_version" not in contract
    assert contract["effective_observation_anchor_ms"] == 1785735000000


def test_event_row_builder_wraps_symbol_contracts_and_validator_accepts_row():
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_event_anchor_contract_row,
        build_symbol_anchor_contract,
        validate_launch_anchor_contract,
    )

    symbol_contract = build_symbol_anchor_contract(
        symbol="GIGADEVUSDT",
        official_schedule_anchor_ms=1785735000000,
        exchangeinfo_onboard_date_ms=1785722400000,
        anchor_contract_decision_at_ms=1785726000000,
        official_schedule_revision_id="gigadev_rev_1",
        official_schedule_available_at_ms=1785724209135,
        mapping_confidence="exact_single_symbol",
        provenance={"payload_sha256": "sha", "parser_version": "test", "raw_time_text": "2026-08-03 05:30 (UTC)", "timezone_text": "UTC", "node_path": "body[0]", "logical_block_id": "block-1", "schedule_text_context": "Launch Time"},
    )
    row = build_formal_event_anchor_contract_row(
        base_event={"event_type": "futures_contract_launch", "source_article_id": "e8bfd0c5adaf4d8a880bb1b7327107ef", "symbols": ["GIGADEVUSDT"]},
        symbol_contracts={"GIGADEVUSDT": symbol_contract},
    )

    res = validate_launch_anchor_contract(row, "GIGADEVUSDT", compatibility_mode=False)
    assert row["formal_event_contract_version"] == 2
    assert res["valid"] is True
    assert res["effective_observation_anchor_ms"] == 1785735000000
```

**Step 2: Write failing selector status-machine tests**

```python
def test_latest_cancelled_revision_blocks_old_schedule():
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import select_latest_applicable_official_schedule

    revisions = [
        {"revision_id": "r1", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
        {"revision_id": "r2", "symbol": "ABCUSDT", "available_at_ms": 4000, "anchor_ms": None, "status": "cancelled", "supersedes_revision_id": "r1"},
    ]
    selected = select_latest_applicable_official_schedule("ABCUSDT", revisions, as_of_ms=4500)
    assert selected["status"] == "cancelled"
    assert selected["effective_official_anchor_ms"] is None
    assert selected["consumable"] is False


def test_latest_postponed_revision_without_new_anchor_is_pending():
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import select_latest_applicable_official_schedule

    revisions = [
        {"revision_id": "r1", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
        {"revision_id": "r2", "symbol": "ABCUSDT", "available_at_ms": 4000, "anchor_ms": None, "status": "postponed", "supersedes_revision_id": "r1"},
    ]
    selected = select_latest_applicable_official_schedule("ABCUSDT", revisions, as_of_ms=4500)
    assert selected["status"] == "postponed_without_anchor"
    assert selected["pending_reason"] == "pending_schedule_revision"


def test_equal_available_at_conflicting_revisions_fail_closed():
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import select_latest_applicable_official_schedule

    revisions = [
        {"revision_id": "r1", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
        {"revision_id": "r2", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 9000, "status": "scheduled"},
    ]
    selected = select_latest_applicable_official_schedule("ABCUSDT", revisions, as_of_ms=1000)
    assert selected["status"] == "official_schedule_conflict"
    assert selected["consumable"] is False


def test_revision_id_is_not_used_to_resolve_semantic_conflict():
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import select_latest_applicable_official_schedule

    revisions = [
        {"revision_id": "z", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
        {"revision_id": "a", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 9000, "status": "scheduled"},
    ]
    assert select_latest_applicable_official_schedule("ABCUSDT", revisions, as_of_ms=1000)["status"] == "official_schedule_conflict"
```

**Step 3: Write failing provenance and hash tests**

Required tests:

```text
test_official_anchor_requires_full_mapping_provenance
test_source_admission_latest_hashes_have_distinct_contracts
test_hash_changes_when_revision_status_changes
test_hash_changes_when_mapping_provenance_changes
test_hash_is_stable_across_dict_order
test_latest_hash_links_previous_hash_and_revision
```

**Step 4: Implement constants and enum allowlists**

`stage1_5_launch_anchor_contract.py` must define:

```python
FORMAL_EVENT_CONTRACT_VERSION_V2 = 2
FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION = 1
ANCHOR_CONTRACT_HASH_SCHEMA_VERSION = 1
ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE = "official_schedule_priority_v1"

REVISION_SELECTOR_STATUSES = {
    "selected",
    "cancelled",
    "postponed_without_anchor",
    "official_schedule_conflict",
    "missing",
    "malformed",
}
ANCHOR_SOURCES = {"official_schedule_anchor", "exchangeinfo_onboard_date", "none"}
ANCHOR_EVIDENCE_LEVELS = {"official_schedule", "exchangeinfo_fallback", "missing", "official_conflict", "malformed"}
MAX_EVIDENCE_CLASSES = {"clean_or_recovery", "recovery_validation_only", "diagnostic_only", "none"}
MAPPING_CONFIDENCE_VALUES = {"exact_single_symbol", "exact_per_symbol_row", "exact_all_symbols_statement", "ambiguous"}
REQUIRED_OFFICIAL_PROVENANCE_FIELDS = {
    "raw_time_text",
    "timezone_text",
    "node_path",
    "logical_block_id",
    "schedule_text_context",
    "payload_sha256",
    "parser_version",
    "mapping_method",
}
```

**Step 5: Implement `select_latest_applicable_official_schedule`**

Function contract:

```python
def select_latest_applicable_official_schedule(symbol: str, revisions: list[dict], as_of_ms: int) -> dict:
    """Return structured point-in-time selection result for revisions with available_at_ms <= as_of_ms."""
```

Rules:

```text
Filter out revisions with available_at_ms > as_of_ms.
Filter out revisions not applying to symbol.
Validate namespace, symbol applicability, status, available_at_ms, anchor presence, supersedes relation where present.
If none remain -> status missing.
If latest applicable revisions share same available_at_ms but disagree on status/anchor/supersedes -> status official_schedule_conflict.
If latest status is cancelled -> status cancelled, no effective official anchor.
If latest status is postponed/rescheduled without replacement anchor -> status postponed_without_anchor, pending_schedule_revision.
If latest status is scheduled/rescheduled and has valid anchor -> status selected.
Never resolve semantic conflict by revision_id ordering.
```

**Step 6: Implement symbol and event builders**

Function contracts:

```python
def build_symbol_anchor_contract(...) -> dict:
    """Return one per-symbol anchor contract. Does not include event-level formal_event_contract_version."""


def build_formal_event_anchor_contract_row(*, base_event: dict, symbol_contracts: dict[str, dict]) -> dict:
    """Return complete formal v2 event row with per-symbol maps and event aggregate fields."""
```

Rules:

```text
Official schedule anchor wins over exchangeInfo onboardDate.
exchangeInfo fallback is only allowed when no valid official anchor exists.
exchangeInfo fallback max_evidence_class = recovery_validation_only.
exchangeinfo_fallback_clean_allowed = false.
Cancelled/postponed/conflict/malformed selected schedule -> non-consumable event aggregate.
Event aggregate fields are derived from all symbol contracts, not copied from first symbol.
```

**Step 7: Implement validator and canonical hashes**

Function contracts:

```python
def validate_launch_anchor_contract(row: dict, symbol: str, *, compatibility_mode: bool = False) -> dict:
    ...


def compute_source_anchor_contract_hash(row: dict, symbol: str) -> str:
    ...


def compute_admission_anchor_contract_hash(*, source_anchor_contract_hash: str, admission_snapshot: dict) -> str:
    ...


def compute_latest_anchor_contract_hash(*, previous_latest_anchor_contract_hash: str, revision_application_id: str, latest_contract: dict) -> str:
    ...
```

Canonical JSON serialization:

```text
json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
sha256 UTF-8 bytes
```

Source hash must include:

```text
hash_schema_version
symbol
source_article_id
formal_event_contract_version
anchor_precedence_policy
anchor_contract_decision_at_ms
official_schedule_selection_as_of_ms
selected_official_schedule_revision_id
selected_official_schedule_status
selected_official_schedule_available_at_ms
official_schedule_anchor_ms
exchangeinfo_onboard_date_ms
effective_observation_anchor_ms
effective_observation_anchor_source
anchor_evidence_level
max_evidence_class
mapping_method
mapping_confidence
payload_sha256
parser_version
logical_block_id
node_path
raw_time_text
timezone_text
```

Admission hash must include:

```text
source_anchor_contract_hash
admission_at_ms
observation_anchor_ms
evidence_start_class
admission_max_evidence_class
```

Latest hash must include:

```text
previous_latest_anchor_contract_hash
revision_application_id
latest source contract canonical payload
```

**Step 8: Run contract tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py -q
```

Expected:

```text
PASS all contract tests. Legacy v1 tests either use explicit compatibility mode or expect fail-closed.
```

---

## Task 5: Add Stage 1.5D Formal V2 Builder and Batch Writer Tests

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing GIGADEV builder test**

Assertions:

```python
assert row["formal_event_contract_version"] == 2
assert row["anchor_precedence_policy"] == "official_schedule_priority_v1"
assert row["symbol_official_schedule_anchor_ms"]["GIGADEVUSDT"] == 1785735000000
assert row["symbol_exchangeinfo_onboard_date_ms"]["GIGADEVUSDT"] == 1785722400000
assert row["symbol_effective_observation_anchor_ms"]["GIGADEVUSDT"] == 1785735000000
assert row["symbol_effective_observation_anchor_sources"]["GIGADEVUSDT"] == "official_schedule_anchor"
assert row["symbol_anchor_comparison_statuses"]["GIGADEVUSDT"] == "exchangeinfo_disagrees_with_official_schedule"
assert row["symbol_max_evidence_classes"]["GIGADEVUSDT"] == "clean_or_recovery"
assert row["symbol_source_anchor_contract_hashes"]["GIGADEVUSDT"]
assert row["event_all_symbols_consumable_by_stage1_5f"] is True
assert row["event_all_symbols_clean_eligible"] is True
```

**Step 2: Write failing formal writer batch validation tests**

Required tests:

```text
test_formal_writer_validates_every_symbol
test_second_symbol_malformed_blocks_entire_batch
test_event_aggregate_is_derived_from_all_symbol_contracts
```

Expected behavior:

```text
For multi-symbol rows, writer validates every emitted symbol.
If any sibling is missing/conflict/malformed/non-consumable, no formal event row is appended.
A sample-capped diagnostic/non-consumable artifact is emitted instead.
```

**Step 3: Write failing all-or-none mixed symbol test**

Scenario:

```text
PYPLUSDT official valid
GSUSDT official valid
SMHUSDT missing official and no strict fallback
```

Expected:

```text
No consumable formal event append for the batch.
Diagnostic/non-consumable artifact only.
```

**Step 4: Run tests and confirm fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected:

```text
FAIL due missing v2 fields / old exchangeInfo effective anchor behavior / incomplete batch validation.
```

---

## Task 6: Implement Stage 1.5D Formal V2 Writer, Revision Writer, and Runtime Gate Capability

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`

**Step 1: Route all consumable launch event writes through formal v2 writer**

Implementation sketch:

```python
def append_formal_futures_launch_event(...):
    row = build_formal_event_anchor_contract_row(...)
    validations = [validate_launch_anchor_contract(row, symbol) for symbol in row.get("symbols", [])]
    if not validations or any(not val["valid"] for val in validations):
        append_non_consumable_diagnostic(...)
        return None
    if not row.get("event_all_symbols_consumable_by_stage1_5f"):
        append_non_consumable_diagnostic(...)
        return None
    append_jsonl(events_path, row)
    return row
```

Requirements:

```text
No direct append_jsonl(stream_paths["events"], norm_event) for consumable futures_contract_launch rows.
Title symbol remains candidate only until full formal v2 contract is built.
Official schedule anchor must be chosen before exchangeInfo fallback.
Legacy aliases must derive from v2 fields, not vice versa.
All new schedule/revision metadata must be included in explicit retry scheduler serializer/deserializer fields.
Single-article detail retry cap must still obey EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES.
```

**Step 2: Add point-in-time decision fields to every v2 row**

Every v2 row must include:

```text
anchor_contract_decision_at_ms
official_schedule_selection_as_of_ms
latest_known_revision_id_at_decision
symbol_official_schedule_revision_ids
symbol_official_schedule_revision_statuses
symbol_official_schedule_revision_available_at_ms
symbol_selected_official_schedule_revision_ids
symbol_source_anchor_contract_hashes
```

**Step 3: Add fail-closed formal schedule revision writer**

Implement:

```python
def append_formal_schedule_revision(...):
    revision_row = build_formal_schedule_revision_row(...)
    validation = validate_schedule_revision_contract(revision_row)
    if not validation["valid"]:
        append_revision_diagnostic(...)
        return None
    append_jsonl(events_path, revision_row)
    return revision_row
```

Revision row cannot be appended by arbitrary branches.

**Step 4: Add runtime gate capability fields**

`live_safety_gate_summary.json` must include:

```json
{
  "formal_event_contract_versions_supported": [2],
  "anchor_precedence_policy": "official_schedule_priority_v1",
  "shared_anchor_validator_enabled": true,
  "formal_schedule_revision_contract_versions_supported": [1]
}
```

**Step 5: Run Stage 1.5D tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected:

```text
PASS. Existing v1 expectations updated only where they conflict with v2 production semantics.
```

---

## Task 7: Add Schedule Revision Registry, Orphan, Ambiguity, and Crash Tests

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py`

**Step 1: Write failing revision row contract tests**

Required tests:

```text
test_schedule_revision_event_is_not_admitted_as_new_launch
test_schedule_revision_writer_fail_closed_on_missing_provenance
test_revision_replay_is_idempotent
test_multisymbol_revision_updates_only_target_sibling
```

**Step 2: Write failing selector/revision link tests**

Required tests:

```text
test_revision_arriving_before_launch_is_durably_held
test_ambiguous_revision_does_not_mutate_state
test_revision_without_supersedes_article_and_ambiguous_symbol_is_diagnostic_only
test_same_symbol_multiple_launches_requires_stable_schedule_identity
test_multisymbol_revision_only_modifies_target_sibling
```

Required behavior:

```text
If revision cannot be linked to a unique stable_schedule_identity, set revision_link_status = ambiguous.
Ambiguous revision is diagnostic only and must not mutate pending/active/completed state.
Revision arriving before launch event is persisted as orphan and later applied only if stable identity becomes unique.
```

**Step 3: Write failing crash consistency tests**

Required tests:

```text
test_crash_after_state_write_before_registry_commit_is_idempotent
test_crash_after_registry_receive_before_state_apply_recovers
test_crash_after_registry_apply_before_state_write_recovers_without_duplicate_revision_count
test_restart_replays_orphan_registry_without_duplicate_application
```

**Step 4: Run and confirm fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected:

```text
FAIL because revision registry/orphan/crash contract does not exist.
```

---

## Task 8: Implement Durable Schedule Revision Transport and Registry

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Create/Modify: `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py`

**Step 1: Define revision row shape**

Required row:

```json
{
  "event_type": "futures_contract_launch_schedule_revision",
  "formal_schedule_revision_contract_version": 1,
  "source_article_id": "...",
  "supersedes_source_article_id": "...",
  "stable_schedule_identity": "binance|futures_contract_launch|original_article|SYMBOL",
  "symbols": ["SYMBOL"],
  "symbol_official_schedule_statuses": {"SYMBOL": "rescheduled"},
  "symbol_revised_anchor_ms": {"SYMBOL": 1785735000000},
  "symbol_official_schedule_revision_ids": {"SYMBOL": "..."},
  "symbol_official_schedule_revision_available_at_ms": {"SYMBOL": 1785724209135},
  "symbol_superseded_anchor_ms": {"SYMBOL": 1785722400000},
  "revision_id": "...",
  "revision_payload_hash": "...",
  "revision_reason": "rescheduled",
  "revision_link_status": "linked"
}
```

**Step 2: Create append-only registry**

Use independent file, not `watermark.json`:

```text
schedule_revision_registry.jsonl
```

Registry states:

```text
revision_received
revision_linked
revision_applied
revision_blocked
revision_orphaned
revision_ambiguous
```

Idempotency key:

```text
revision_application_id = sha256(stable_schedule_identity | revision_id | revision_payload_hash)
```

**Step 3: Route revisions in 1.5F before launch admission**

Pseudo-flow:

```python
for event in events:
    if event.get("event_type") == "futures_contract_launch_schedule_revision":
        receive_schedule_revision(event)
        reconcile_schedule_revision_registry()
        continue
    process_launch_event(event)
    reconcile_schedule_revision_registry()
```

**Step 4: Implement crash-safe replay**

Startup must rebuild applied IDs from `schedule_revision_registry.jsonl` and latest observer state. Replay must be idempotent for all crash windows:

```text
registry receive written, state not updated
state updated, registry applied row not written
registry applied row written, state update repeated on restart
orphan written before launch state exists
ambiguous revision replayed repeatedly
```

**Step 5: Run revision registry tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected:

```text
Revision tests pass; launch event tests still pass; watermark schema remains event-admission focused.
```

---

## Task 8A: Explicitly Defer Automatic Schedule Revision Producer Rules

**Status:** follow-up required, not part of this implementation commit.

**Why this task is separate:**

Task 8 implements the schedule revision row contract, fail-closed writer, durable registry, replay/idempotency, and Stage 1.5F consumer behavior. It does not fully implement the Stage 1.5D automatic classifier that decides which live Binance announcements should become `futures_contract_launch_schedule_revision` rows.

This separation is intentional. A producer classifier that guesses `supersedes_source_article_id` incorrectly can mutate a pending/active observation with the wrong official schedule. That is a data lineage error, not a cosmetic parser issue.

**Current implementation boundary:**

```text
implemented_now:
  - build_formal_schedule_revision_row(...)
  - validate_schedule_revision_contract(...)
  - append_formal_schedule_revision(...) fail-closed writer
  - Stage 1.5F routing by event_type before launch admission
  - schedule_revision_registry.jsonl append-only registry
  - orphan / ambiguous / applied / replay idempotency behavior

not_implemented_now:
  - broad automatic Binance announcement revision classifier
  - automatic supersedes_source_article_id inference from real live announcement text
  - full historical fixture pack for postpone/reschedule/cancel launch announcement shapes
```

**Required follow-up design/plan before producer implementation:**

```text
Stage 1.5D schedule revision producer rules
```

The follow-up must define:

```text
1. Which official Binance title/body patterns qualify as futures_contract_launch_schedule_revision.
2. Which similar announcement shapes are explicitly excluded.
3. How supersedes_source_article_id is linked:
   - direct articleCode/source_article_id reference
   - official link to original launch announcement
   - unique point-in-time symbol + original official launch anchor match
4. When producer output must be revision_link_status = orphaned.
5. When producer output must be revision_link_status = ambiguous.
6. Why symbol-only matching is forbidden when multiple launch candidates exist.
7. Real official fixtures for postpone/reschedule/cancel launch announcements.
```

**Commit boundary requirement:**

This v2 hotfix commit may claim:

```text
schedule_revision_transport_and_consumer_ready = true
automatic_schedule_revision_producer_ready = false
```

It must not claim that Stage 1.5D can already auto-detect every live schedule revision announcement.

---

## Task 9: Add Stage 1.5F Root Contract, Bootstrap, and V1/V2 Isolation Tests

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing root contract tests**

Required tests:

```text
test_v2_root_writes_observer_root_contract_before_watermark
test_v2_root_rejects_any_v1_row
test_v1_compatibility_root_rejects_v2_mix
test_bootstrap_does_not_write_watermark_on_mixed_versions
test_restart_cli_mode_must_match_root_contract
test_normal_runtime_blocks_new_admission_on_contract_version_mix
```

**Step 2: Define root contract artifact**

`observer_root_contract.json` shape:

```json
{
  "root_contract_schema_version": 1,
  "root_mode": "v2_production",
  "formal_event_contract_versions_allowed": [2],
  "formal_schedule_revision_contract_versions_allowed": [1],
  "anchor_precedence_policy": "official_schedule_priority_v1",
  "created_at_ms": 0,
  "reason": "",
  "source_stage1_5d_root_id": "...",
  "source_stage1_5d_runtime_gate_path": "..."
}
```

Allowed modes:

```text
v2_production
v1_compatibility_diagnostic_only
```

**Step 3: Write failing bootstrap behavior tests**

Expected:

```text
Bootstrap scans event rows before writing watermark.
If any disallowed contract version exists, bootstrap fails and watermark.json is not written.
If CLI mode conflicts with existing observer_root_contract.json, startup fails closed.
```

**Step 4: Run and confirm fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected:

```text
FAIL because root contract isolation is not implemented.
```

---

## Task 10: Implement Stage 1.5F Root Contract, Runtime Gate Capability, and V1 Compatibility Isolation

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Modify: `configs/base.py`

**Step 1: Add CLI gates**

Add:

```text
--allow-formal-v1-compatibility
--formal-v1-compatibility-reason <non-empty>
```

Rules:

```text
Default false.
If true, output root suffix must contain _v1_compatibility_diagnostic_only.
If false, v1 row cannot become active/accepted.
Compatibility root cannot mix v1 and v2 rows.
Production v2 root cannot mix v1 rows.
```

**Step 2: Write and validate `observer_root_contract.json`**

Bootstrap order:

```text
1. Determine root_mode from CLI.
2. Scan event rows and runtime gate capability.
3. If scan fails, do not write watermark.
4. Write observer_root_contract.json.
5. Write bootstrap watermark only after root contract exists and is valid.
```

Restart order:

```text
1. Read observer_root_contract.json if exists.
2. Verify CLI mode matches root_mode.
3. Verify new event rows match allowed versions.
4. If mismatch, block_new_event_admission = true and emit contract_version_mix diagnostic.
```

**Step 3: Validate runtime gate capability**

1.5F startup/runtime gate validation must require:

```text
formal_event_contract_versions_supported includes 2
formal_schedule_revision_contract_versions_supported includes 1
anchor_precedence_policy == official_schedule_priority_v1
shared_anchor_validator_enabled == true
```

If missing:

```text
block_new_event_admission = true
runtime_gate_invalid_count += 1
```

**Step 4: Run isolation tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected:

```text
PASS v1/v2 root isolation, bootstrap no-watermark-on-failure, and runtime gate capability tests.
```

---

## Task 11: Add Stage 1.5F State Schema V3 and V2 Admission Tests

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing official disagreement admission test**

```python
def test_gigadev_v2_official_schedule_disagreement_does_not_enter_anchor_conflict(tmp_path):
    # row official anchor 05:30, exchangeInfo 02:00
    # now before 05:30 -> pending_launch_time_in_future with observation_anchor_ms 05:30
```

Expected assertions:

```python
assert state.status == "pending_launch_time_in_future"
assert state.observation_anchor_ms == 1785735000000
assert state.pending_reason == "pending_launch_time_in_future"
```

**Step 2: Write failing fallback clean lock test**

```python
def test_exchangeinfo_fallback_inside_clean_window_is_recovery_only(tmp_path):
    # fallback anchor, now within 2m clean window
    # must not eligible_clean_start
```

Expected:

```python
assert accepted_row["evidence_start_class"] == "recovery_start"
assert accepted_row["admission_max_evidence_class"] == "recovery_validation_only"
assert accepted_row["clean_start_forbidden_reason"] == "exchangeinfo_fallback_anchor"
```

**Step 3: Write failing state schema migration and round-trip tests**

Required tests:

```text
test_v2_state_migrates_to_v3
test_all_lineage_fields_survive_roundtrip
test_unknown_state_fields_are_ignored
test_missing_lineage_fields_default_safely
```

**Step 4: Run and confirm fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected:

```text
FAIL because v2 admission/state v3 behavior is not implemented.
```

---

## Task 12: Implement Stage 1.5F V2 Admission and State Schema V3

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`

**Step 1: Replace scalar anchor conflict logic with v2 validation**

Flow:

```python
contract = validate_launch_anchor_contract(flat_event, symbol, compatibility_mode=args.allow_formal_v1_compatibility)
if not contract["valid"]:
    pending/diagnostic source contract path
else:
    use contract["effective_observation_anchor_ms"] and contract["max_evidence_class"]
```

**Step 2: Add state schema v3 fields with safe defaults**

Add to `EventSymbolState`:

```text
observer_state_schema_version: int = 3
source_anchor_contract_hash: str = ""
admission_anchor_contract_hash: str = ""
latest_anchor_contract_hash: str = ""
anchor_contract_version: int | None = None
anchor_precedence_policy: str = ""
anchor_contract_decision_at_ms: int | None = None
admission_anchor_evidence_level: str = ""
latest_anchor_evidence_level: str = ""
admission_max_evidence_class: str = ""
latest_max_evidence_class: str = ""
anchor_contract_revision_count: int = 0
observation_anchor_revision_contaminated: bool = False
anchor_revision_contamination_reason: str = ""
source_contract_status: str = ""
pending_reason: str = ""
```

`from_dict()` must keep the dataclass field filter pattern:

```python
cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
```

**Step 3: Persist v2 lineage fields in state and accepted rows**

Accepted and state rows must include:

```text
source_anchor_contract_hash
admission_anchor_contract_hash
latest_anchor_contract_hash
anchor_contract_version
anchor_precedence_policy
anchor_contract_decision_at_ms
admission_anchor_evidence_level
latest_anchor_evidence_level
admission_max_evidence_class
latest_max_evidence_class
```

**Step 4: Implement fallback class lock**

If `symbol_max_evidence_classes[symbol] == recovery_validation_only`:

```text
clean_start forbidden even inside clean window
eligible result must be recovery-only or diagnostic-only
```

**Step 5: Run Stage 1.5F tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected:

```text
PASS, including v2 admission, fallback clean lock, root isolation, and state v3 round-trip.
```

---

## Task 13: Add Contaminated Active Lifecycle Tests

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`

**Step 1: Write failing contaminated active tests**

Required tests:

```text
test_contaminated_active_continues_depth_polling
test_contaminated_active_counts_against_capacity
test_contaminated_active_completes_at_original_window_end
test_restart_preserves_contamination_and_window
test_contaminated_window_start_never_moves
test_completed_contaminated_state_is_stage1_5g_invalid_ready
```

Expected behavior:

```text
active_anchor_revision_contaminated continues depth collection.
It counts against observation capacity.
It does not move observation_started_at_ms or observation_window_end_ms.
It finalizes as completed_anchor_revision_contaminated or completed with contamination flag.
It remains invalid for 1.5G evidence claims.
```

**Step 2: Run and confirm fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected:

```text
FAIL before contaminated active status is included in active selectors.
```

---

## Task 14: Implement Contaminated Active Lifecycle

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`

**Step 1: Add status helper**

Implement:

```python
def is_depth_collection_active_status(status: str) -> bool:
    return status in {"active", "active_anchor_revision_contaminated"}
```

Use this helper everywhere depth polling, capacity accounting, expected snapshot count, completion finalization, restart recovery, and summary active count currently check `status == "active"`.

**Step 2: Add revision application state transition helper**

Implement:

```python
def apply_anchor_contract_revision_to_state(state: EventSymbolState, revision: dict, now_ms: int) -> EventSymbolState:
    ...
```

Rules:

```text
pending fallback + official revision -> update anchor if not started.
active fallback + differing official revision -> active_anchor_revision_contaminated.
completed fallback + differing official revision -> completed_anchor_revision_contaminated or completed with contamination flags.
matching post-start official revision -> later confirmed, no clean upgrade.
max_evidence_class can only stay same or decrease.
```

**Step 3: Preserve append-only state lineage**

Every mutation must append `observer_state.jsonl`; do not mutate prior rows.

**Step 4: Add summary counters**

Add defaulted summary fields:

```text
active_anchor_revision_contaminated_count
completed_anchor_revision_contaminated_count
anchor_contract_revision_count
anchor_contract_lineage_mismatch_count
schedule_revision_registry_orphan_count
schedule_revision_registry_ambiguous_count
```

**Step 5: Run contamination tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected:

```text
PASS contamination lifecycle tests.
```

---

## Task 15: Add Stage 1.5G Latest-State, Lineage, and Fallback Invalid Tests

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`
- Modify: `tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py`
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`

**Step 1: Write failing latest-state reducer tests**

Required tests:

```text
test_stage1_5g_uses_latest_state_for_anchor_contamination
test_latest_state_reducer_handles_out_of_order_jsonl_rows
test_latest_state_reducer_handles_duplicate_completed_rows
test_latest_state_reducer_matches_compacted_state
```

Expected:

```text
1.5G builds latest state by event_symbol_id before evaluating lineage.
It must not treat all historical observer_state rows as current state.
```

**Step 2: Write failing lineage invalid tests**

Required tests:

```text
test_anchor_contract_hash_mismatch_is_invalid
test_malformed_anchor_contract_is_invalid_not_quarantine
test_anchor_revision_contaminated_is_invalid_not_quarantine
test_missing_state_lineage_for_accepted_row_is_invalid
```

Expected:

```python
assert summary["decision"] == "stage1_5g_depth_evidence_invalid"
assert summary["clean_depth_evidence_pass"] is False
assert summary["quarantined_depth_evidence_pass"] is False
```

**Step 3: Write failing fallback final-decision tests**

Required tests:

```text
test_healthy_fallback_observation_is_not_clean
test_healthy_fallback_observation_is_not_quarantined_pass
test_healthy_fallback_observation_is_stage1_5g_invalid
test_fallback_decision_has_explicit_allowed_next_action
```

Expected:

```text
exchangeInfo fallback is invalid for Stage 1.5G research evidence, even if depth snapshots are healthy.
allowed_next_action = collect_official_anchor_evidence_or_wait_for_next_event
```

**Step 4: Run and confirm fail**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py -q
```

Expected:

```text
FAIL before Stage 1.5G lineage/latest-state/fallback invalid implementation.
```

---

## Task 16: Implement Stage 1.5G Latest-State and Anchor Lineage Validation

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`

**Step 1: Define explicit 1.5G input paths**

1.5G must read from configured 1.5F output root:

```text
events_accepted/*.jsonl
observer_state.jsonl or observer_state/*.jsonl if current implementation uses directory fanout
completed/*.jsonl or terminal observer_state rows if current implementation has no completed directory
```

The implementation must document the actual code path found in Task 1 before adding lineage checks.

**Step 2: Build latest state by `event_symbol_id`**

Reducer rules:

```text
Group state rows by event_symbol_id.
Choose latest by updated_at_ms / state_written_at_ms / monotonic file order, matching current schema fields.
Completed/terminal state beats older active state for same event_symbol_id.
Duplicate completed rows must be idempotent.
```

**Step 3: Validate lineage fields**

Checks:

```text
accepted.admission_anchor_contract_hash == latest_state.admission_anchor_contract_hash
latest_state.latest_anchor_contract_hash exists
completed.latest_anchor_contract_hash == latest_state.latest_anchor_contract_hash when completed exists
latest_state.observation_anchor_revision_contaminated false for any pass evidence
latest_state.latest_max_evidence_class permits requested evidence class
fallback max evidence class never allows clean/quarantine pass
```

**Step 4: Hard invalid blockers**

Set invalid if any:

```text
anchor_revision_contaminated
malformed_anchor_contract
anchor_contract_lineage_mismatch
exchangeinfo_fallback_anchor
exchangeinfo_fallback_clean_claim
anchor_contract_lineage_state_missing
```

Never quarantine these blockers.

**Step 5: Run Stage 1.5G tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py -q
```

Expected:

```text
PASS with clean/quarantine threshold tests unchanged except anchor blocker semantics.
```

---

## Task 17: Add Deployment Glob Regression and Dated Runbook Tests

**Files:**
- Add: `docs/reviews/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-schedule-priority-v2-deployment-checklist_CN.md`
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md` only to point to the dated runbook, not to host the full new deployment flow
- Add/Modify: `tests/scripts/external_signal_shadow/test_stage1_5f_deployment_checklist.py`

**Step 1: Write failing checklist static test**

```python
def test_stage1_5f_deployment_events_glob_contains_no_literal_backslash():
    from pathlib import Path
    paths = [
        Path("docs/reviews/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-schedule-priority-v2-deployment-checklist_CN.md"),
        Path("docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md"),
    ]
    for path in paths:
        text = path.read_text()
        assert "events/\\*.jsonl" not in text
    assert "events/*.jsonl" in paths[0].read_text()
```

**Step 2: Write glob hit smoke test**

Use a temp root with `events/2026-08-03.jsonl` and assert Python `glob.glob(f"{root}/events/*.jsonl")` hits it, while no documented startup command passes literal `\*.jsonl`.

**Step 3: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_stage1_5f_deployment_checklist.py -q
```

Expected:

```text
PASS and protects against the GIGADEV deployment glob regression.
```

---

## Task 18: End-to-End Runner Tests

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Modify: `tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py`

**Step 1: Add GIGADEV e2e production-shape test**

Scenario:

```text
1. 1.5D emits GIGADEV v2 row with official anchor 05:30 and exchangeInfo onboard 02:00.
2. 1.5F consumes before 05:30.
3. 1.5F writes pending_launch_time_in_future, not pending_anchor_conflict.
4. At 05:30 within clean window, 1.5F accepts active observation with official anchor.
5. 1.5G can only evaluate clean if no lineage blocker and no fallback/contamination exists.
```

**Step 2: Add fallback e2e invalid test**

Scenario:

```text
1. 1.5D emits fallback-only v2 row.
2. 1.5F consumes inside clean window.
3. accepted row is recovery_validation_only, not clean_start.
4. 1.5G decision is stage1_5g_depth_evidence_invalid.
```

**Step 3: Add contaminated e2e test**

Scenario:

```text
1. fallback active observation starts.
2. later official revision differs.
3. state becomes active_anchor_revision_contaminated and continues depth polling.
4. completed state invalidates 1.5G.
```

**Step 4: Add mixed-version e2e test**

Scenario:

```text
1. Bootstrap v2 production root.
2. v1 row appears in event stream.
3. 1.5F sets block_new_event_admission true and writes contract_version_mix diagnostic.
4. No watermark advance admits the bad row.
```

**Step 5: Run focused e2e tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py -q
```

Expected:

```text
PASS all focused e2e tests.
```

---

## Task 19: Full Verification Gate

Run focused suite first:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  tests/scripts/external_signal_shadow/test_stage1_5f_deployment_checklist.py -q
```

Then run broader Stage 1.5 set:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py -q
```

Run project checks:

```bash
make lint
make check
git diff --check
```

Expected:

```text
All tests pass.
No trade/paper/live/execution flags become true.
No old production root files are modified.
```

Run static safety grep on production paths only:

```bash
rg -n "trade_signal_allowed.*true|paper_trading_allowed.*true|live_trading_allowed.*true|execution_engine_allowed.*true|alpha_interpretation_allowed.*true|execution_feasibility_claim_allowed.*true|RISK_LIVE_TRADING_ENABLED.*true" \
  configs src scripts || true
```

Expected:

```text
No unsafe allowance in production paths. Tests/docs are excluded to avoid intentional negative fixtures.
```

Run v1/v2 safety grep:

```bash
rg -n "formal_event_contract_version.*1|launch_anchor_evidence_level|launch_anchor_comparison_status|launch_anchor_disagreement_ms" \
  src/research/external_signal_shadow scripts/external_signal_shadow tests -g '*.py'
```

Expected:

```text
Remaining v1/scalar references are either legacy compatibility tests, historical fixture tests, migration/reporting, or explicit fail-closed paths.
No v1 scalar path can emit clean/active production evidence.
```

---

## Task 20: Dated Server Deployment Runbook

**Files:**
- Add: `docs/reviews/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-schedule-priority-v2-deployment-checklist_CN.md`
- Modify: `docs/project-status/current-project-state_CN.md` only if user requests state update

Do not deploy until Task 19 passes locally.

Deployment root suffix:

```text
7d_official_schedule_anchor_contract_v2_hotfix
```

Required command-level sequence:

```text
1. Confirm local clean worktree and record commit SHA.
2. Scoped source sync only; exclude data, .git, .venv, caches.
3. Server per-file SHA256 compare for configs/base.py, shared anchor contract, 1.5D runner, 1.5F runner, 1.5G reviewer.
4. Confirm server disk free space >= 5G.
5. Confirm old active 1.5F observations; if active, mark old root drain-only unless user approves stop.
6. Start new Stage 1.5D v2 root.
7. Wait for live_safety_gate_summary decision = stage1_5d_runtime_gate_ready.
8. Verify runtime gate capability contains contract version 2, schedule revision version 1, official_schedule_priority_v1, shared validator true.
9. Create new Stage 1.5F root contract.
10. Run --bootstrap-watermark for new 1.5F root.
11. Bootstrap must verify same-root v2 capability and event stream glob hit count.
12. Bootstrap failure must not write watermark.json.
13. Start normal 1.5F with events/*.jsonl, not events/\\*.jsonl.
14. Keep old root read-only/drain-only until new root proves stable.
15. Stage 1.5G only runs offline against completed v2 root after collection completes.
```

First server check must verify:

```text
1. 1.5D live_safety_gate_summary decision = stage1_5d_runtime_gate_ready.
2. formal_event_contract_versions_supported contains 2.
3. formal_schedule_revision_contract_versions_supported contains 1.
4. anchor_precedence_policy = official_schedule_priority_v1.
5. shared_anchor_validator_enabled = true.
6. 1.5F observer_root_contract.root_mode = v2_production.
7. 1.5F stage1_5d_runtime_gate_decision = stage1_5d_runtime_gate_ready.
8. cross_root_upstream_summary_dependency = false.
9. block_new_event_admission = false.
10. events/*.jsonl glob matches >= 1 file and process argv contains no \\*.jsonl.
```

GIGADEV expectation after deployment:

```text
Do not backfill as clean evidence.
If replayed, it may be diagnostic/expired/invalid depending current time and old event fields.
The production acceptance target is the next new comparable live event.
```

---

## Task 21: Commit Plan for Implementation Work

Suggested commit boundaries during implementation:

```text
1. test: freeze GIGADEV anchor contract v2 fixtures
2. feat: add shared anchor contract v2 selector and canonical hashes
3. feat: emit Stage 1.5D formal v2 anchor rows and revision rows
4. feat: add durable schedule revision registry
5. feat: enforce Stage 1.5F root contract and v1/v2 isolation
6. feat: persist Stage 1.5F state schema v3 lineage
7. feat: preserve contaminated active depth lifecycle
8. feat: enforce Stage 1.5G latest-state lineage invalid blockers
9. docs: add official schedule v2 deployment checklist
```

Do not squash evidence-bearing fixture commits unless user explicitly requests it.

---

## Execution Notes

Implementation should proceed in a dedicated execution session or isolated worktree. The highest-risk dependencies are:

```text
1. The single shared contract module must land before 1.5D/1.5F/1.5G code changes.
2. The selector status machine must fail closed for cancelled/postponed/conflict/malformed revisions.
3. The formal writer must validate every symbol in a multi-symbol batch before append.
4. 1.5F cannot consume v2 rows safely until root contract and runtime gate capability validation exist.
5. Revision replay cannot be safe without append-only schedule_revision_registry.jsonl.
6. 1.5F state schema v3 must preserve contaminated active depth collection.
7. 1.5G cannot make clean or quarantine claims until latest-state lineage validation exists.
8. v1 compatibility must remain default-off throughout implementation.
```

If any focused test fails after more than three fix attempts, stop and re-check the contract design before continuing.
