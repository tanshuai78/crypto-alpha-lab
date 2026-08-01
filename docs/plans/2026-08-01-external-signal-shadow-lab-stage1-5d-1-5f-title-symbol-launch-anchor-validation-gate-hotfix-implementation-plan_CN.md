# Stage 1.5D / 1.5F Title-Symbol Launch-Anchor Validation Gate Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 2026-07-31 `GRVTUSDT` title-symbol prelaunch hard reject 事故：1.5F 先阻断 `symbol_not_in_exchangeinfo` 早期 terminal reject，1.5D 再阻断 title-only unanchored formal emit，使 single-symbol 与 multi-symbol launch event 都必须满足 formal launch-anchor contract 后才可供 1.5F admission。

**Architecture:** 分 Phase A/B/C。Phase A 在 1.5F 增加 source contract triage、anchor-first admission、exchangeInfo visibility pending/timeout、capacity pending 与 durable pending recovery。Phase B 在 1.5D 将 title symbol 改为 candidate，统一进入 detail/BAPI + exchangeInfo validation，新增 formal v1 event contract 与唯一 formal event writer。Phase C 固化 GRVT/A827/93b5 回归 fixture、部署 runbook 与生产验收。

**Tech Stack:** Python, pytest, JSON/JSONL append-only artifacts, Binance BAPI/exchangeInfo frozen fixtures, Stage 1.5D/1.5F offline runner tests, read-only production deployment.

---

## 0. Non-Negotiable Rules

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

Execution rules:

```text
1. TDD first: every behavior change starts with a failing test.
2. Phase A can be deployed independently as defensive hotfix; Phase B must follow to remove source contamination.
3. Do not mutate or delete old production roots.
4. Do not convert GRVT missed observation into clean evidence.
5. Fail closed on source contract, anchor, exchangeInfo, identity, or capacity ambiguity.
6. Pending is safe; false clean evidence and irreversible terminal reject are unsafe.
7. Use PYTHONPATH=src:. .venv/bin/python for all verification.
```

## 0.1 External Review Mandatory Revisions

The following implementation constraints are mandatory and override any ambiguous task wording below:

```text
1. 1.5D builder, 1.5D writer, and 1.5F validator must share one contract module.
2. append_formal_futures_launch_event() must validate and fail closed; it cannot be a thin append wrapper.
3. legacy_unvalidated_recoverable events may persist identity and enrichment diagnostics, but must never active, accepted, or create clean/recovery evidence without a formal_v1_valid revision.
4. legacy source revision wait deadline must be distinct from formal anchor resolution deadline.
5. observation_anchor_ms = None must use anchor_resolution_deadline_ms, not symbol_visibility_deadline_ms.
6. EventSymbolState and 1.5D scheduler state schema changes must round-trip across restart with safe defaults.
7. detail scheduler lanes must have deterministic quotas/cursors and must still enforce EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES = 3 per article.
8. Phase A and Phase B deployment flows must be separate, with independent roots, bootstrap watermarks, SHA256 checks, and drain/stop rules.
```

---

## Task 1: Preflight and Evidence Inventory

**Files:**
- Read: `configs/base.py`
- Read: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Read: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Read: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Read: `_project_context/server_evidence/20260801_grvt_title_gate/`

**Step 1: Confirm config boundaries**

```bash
rg -n "EXTERNAL_SIGNAL_STAGE1_5F_(LAUNCH_START_GUARD_MS|MAX_CLEAN_START_DELAY_MS|MAX_RECOVERY_START_DELAY_MS|MAX_ANCHOR_RESOLUTION_AGE_MS|MAX_ANCHOR_DISAGREEMENT_MS)|EXTERNAL_SIGNAL_STAGE1_5D_DETAIL" configs/base.py
```

Expected baseline:

```text
EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS = 0
EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS = 120_000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS = 900_000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS = 21_600_000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS = 60_000
```

Also confirm:

```text
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES = 3
```

If a distinct legacy wait timeout does not exist, add it later in Task 5:

```text
EXTERNAL_SIGNAL_STAGE1_5F_LEGACY_SOURCE_REVISION_WAIT_MS
```

**Step 2: Locate unsafe 1.5F hard reject paths**

```bash
rg -n "symbol_not_in_exchangeinfo|budget_exceeded|pending_exchangeinfo|pending_observation_capacity|classify_event_symbol_eligibility" \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests -g '*.py'
```

Expected:

```text
All current production sites that can emit symbol_not_in_exchangeinfo or budget_exceeded are identified before edits.
```

**Step 3: Locate unsafe 1.5D formal append paths**

```bash
rg -n "append_jsonl\(stream_paths\[\"events\"\]|detail_fetch_status.*not_needed|symbol_extraction_source.*title|normalize_live_event" \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py \
  tests -g '*.py'
```

Expected:

```text
Every direct events/*.jsonl append path is known.
Title-symbol immediate emit path is known.
```

**Step 4: Confirm GRVT incident evidence availability**

```bash
find _project_context/server_evidence/20260801_grvt_title_gate -maxdepth 5 -type f | sort
```

Required evidence categories:

```text
1. Stage 1.5D GRVT unanchored event row.
2. Stage 1.5F GRVT rejected row with legacy reason symbol_not_in_exchangeinfo.
3. exchangeInfo after launch showing GRVTUSDT TRADING and onboardDate.
4. Optional: raw BAPI/detail payload or post-incident official BAPI payload.
```

---

## Task 2: Freeze GRVT Regression Fixtures

**Files:**
- Add: `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_grvt_real_frozen_fixture.json`
- Add: `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_grvt_real_frozen_fixture_metadata.json`
- Add: `tests/fixtures/external_signal_shadow/stage1_5f/grvt_title_gate/grvt_stage1_5d_unanchored_event.json`
- Add: `tests/fixtures/external_signal_shadow/stage1_5f/grvt_title_gate/grvt_stage1_5f_legacy_rejected_event.json`
- Add: `tests/fixtures/external_signal_shadow/stage1_5f/grvt_title_gate/grvt_exchangeinfo_after_launch.json`
- Optional Add: `tests/fixtures/external_signal_shadow/stage1_5f/grvt_title_gate/grvt_exchangeinfo_before_launch.json`

**Step 1: Copy incident rows from server evidence**

Create fixtures from the synced files under `_project_context/server_evidence/20260801_grvt_title_gate/`. Preserve original JSON fields. Do not normalize away missing fields, because the legacy unanchored shape is the regression target.

Required metadata:

```json
{
  "article_id": "20536b05b2a34b87a3bae99c45d0dc91",
  "symbol": "GRVTUSDT",
  "incident_class": "title_symbol_prelaunch_hard_reject",
  "expected_legacy_rejected_reason": "symbol_not_in_exchangeinfo",
  "expected_onboardDate": 1785501900000,
  "expected_onboard_utc": "2026-07-31T12:45:00+00:00"
}
```

**Step 2: Freeze official BAPI payload**

If already synced, use the existing raw payload. If not, fetch a post-incident official payload for parser capability only:

```bash
python3 - <<'PY'
import json, urllib.request
from pathlib import Path
article = "20536b05b2a34b87a3bae99c45d0dc91"
out = Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_grvt_real_frozen_fixture.json")
out.parent.mkdir(parents=True, exist_ok=True)
url = f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode={article}"
with urllib.request.urlopen(url, timeout=20) as r:
    payload = json.loads(r.read())
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(out)
PY
```

Metadata must state:

```text
data_quality = post_incident_official_bapi_frozen_payload
not_point_in_time_incident_payload = true
```

Metadata must also include:

```text
fetched_at_ms
request_url
http_status
raw_sha256
fixture_sha256
parser_version_at_capture
source_transport
content_provenance
```

Tests must not fetch network. The network command above is a one-time fixture capture step only.

**Step 3: Add fixture smoke tests**

Add tests that only assert fixture loadability and expected incident fields before changing implementation:

```text
test_grvt_incident_unanchored_stage1_5d_fixture_loads
test_grvt_incident_legacy_rejected_stage1_5f_fixture_loads
test_grvt_bapi_fixture_extracts_symbol_and_launch_time_if_payload_contains_body
```

---

## Task 3: Shared Formal Launch Event Contract Module

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5_launch_event_contract.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5_launch_event_contract.py`
- Modify later: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify later: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`

**Step 1: Write failing shared-contract tests**

Add tests:

```text
test_validate_formal_launch_event_requires_full_v1_contract
test_exchangeinfo_fallback_requires_auditable_detail_attempt
test_consumer_rejects_invalid_evidence_level_field_combination
test_disagreement_and_comparison_status_must_be_consistent
test_builder_and_loader_use_same_contract_validator
test_all_formal_v1_fixtures_roundtrip_producer_to_consumer
```

**Step 2: Implement shared module skeleton**

The module must be the single source of truth for formal launch event contract semantics:

```python
def classify_anchor_evidence(row: dict, symbol: str) -> dict:
    """Classify per-symbol launch anchor evidence and consistency."""


def validate_formal_launch_event(row: dict, symbol: str | None = None) -> dict:
    """Return {valid, status, blockers, diagnostics}; never raise for data quality failures."""


def build_formal_launch_event(*, raw_event: dict, symbol_rows: list[dict], diagnostics: dict) -> dict:
    """Build a formal v1 event row and validate before returning it."""
```

Required validator coverage:

```text
formal_event_contract_version
formal_event_consumable_by_stage1_5f
source_contract_status
symbol_identity_validation_status
symbol_effective_launch_times_ms
symbol_onboard_times_ms
symbol_launch_time_candidates_ms
symbol_effective_launch_time_sources
launch_anchor_validation_status
launch_anchor_disagreement_ms
launch_anchor_comparison_status
launch_anchor_evidence_level
detail_fetch_attempted
detail_fetch_status
detail_fetch_variant
detail_confirmation_missing
source_article_id
stable_event_key
event_id
parser_version
symbol_extraction_version
```

**Step 3: Define evidence-level consistency matrix**

```text
detail_confirmed:
  detail_fetch_attempted = true
  detail_confirmation_missing = false
  bapi/support detail anchor exists
  exchangeInfo identity validation exists

detail_exchangeinfo_consensus:
  detail anchor exists
  exchangeInfo onboardDate exists
  disagreement_ms is integer <= tolerance
  comparison_status = consensus

exchangeinfo_fallback:
  exchangeInfo onboardDate exists
  detail_fetch_attempted = true
  detail request is auditable
  detail anchor absent or transient unavailable
  detail_confirmation_missing = true
  comparison_status = single_source_exchangeinfo

conflict/missing/malformed:
  valid = false
  no formal emit
```

**Step 4: Enforce shared usage**

Later tasks must call this shared module:

```text
1. 1.5D builder calls build_formal_launch_event() / validate_formal_launch_event().
2. 1.5D append_formal_futures_launch_event() calls validate_formal_launch_event() before append.
3. 1.5F classify_stage1_5d_source_contract() calls validate_formal_launch_event() for formal_v1 rows.
```

No implementation may duplicate a partial subset of the formal contract rules.

---

## Task 4: 1.5F Source Contract Triage

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

**Step 1: Write failing tests**

Add tests:

```text
test_legacy_unversioned_post_watermark_event_becomes_pending_not_rejected
test_legacy_unversioned_pre_watermark_event_is_ignored_not_pending
test_explicit_non_consumable_event_never_enters_observation_pending
test_formal_contract_check_cannot_terminal_reject_recoverable_legacy_event
test_formal_v1_requires_exchangeinfo_identity_and_per_symbol_anchor_fields
```

**Step 2: Implement helper**

Add a pure helper:

```python
def classify_stage1_5d_source_contract(row: dict, symbol: str) -> dict:
    """Classify whether a Stage 1.5D event row is consumable by Stage 1.5F."""
```

This helper must call the shared validator:

```python
from src.research.external_signal_shadow.stage1_5_launch_event_contract import (
    validate_formal_launch_event,
)
```

It must not reimplement a weaker duplicate of the formal contract rules.

Return fields:

```text
source_contract_status:
  formal_v1_valid
  legacy_unvalidated_recoverable
  explicit_non_consumable
  malformed
pending_source_event_unvalidated: bool
required_source_revision: str | None
source_contract_blocker: str | None
```

Formal v1 valid requires:

```text
formal_event_contract_version == 1
formal_event_consumable_by_stage1_5f is true
symbol_identity_validation_status == validated_by_exchangeinfo
symbol_effective_launch_times_ms contains symbol
symbol_launch_time_candidates_ms contains symbol
symbol_effective_launch_time_sources contains symbol
launch_anchor_comparison_status contains symbol
launch_anchor_validation_status is valid for evidence level
launch_anchor_evidence_level is valid
detail_fetch_attempted/detail_fetch_status/detail_confirmation_missing combination is valid
exchangeinfo_fallback has auditable detail attempt
disagreement_ms and comparison_status are internally consistent
```

Legacy recoverable includes GRVT-like rows:

```text
formal fields missing
source_article_id present
stable_event_key/event_id recoverable
symbol present
```

Terminal/diagnostic contract:

```text
explicit_non_consumable:
  write diagnostic only
  no observation pending
  no events_accepted
  no events_rejected evidence row

malformed:
  write diagnostic with raw row hash/path where possible
  preserve raw row
  no observation pending
  no clean/recovery evidence
```

**Step 3: Keep historical ignore before pending creation**

Admission order must be:

```text
identity/event_type
bootstrap/pre-watermark/historical classification
source contract triage
pending/eligible/rejected classification
```

A pre-bootstrap unversioned row must be ignored, not persisted as pending.

**Step 4: Enforce legacy no-promotion boundary**

Legacy/unvalidated source events may be preserved, enriched, and later upserted by a formal revision, but must never become active from exchangeInfo alone:

```text
source_contract_status != formal_v1_valid
=> active forbidden
=> accepted row forbidden
=> clean/recovery evidence forbidden
```

Add tests:

```text
test_legacy_event_with_exchangeinfo_onboard_date_remains_pending
test_legacy_event_with_symbol_trading_remains_pending_without_formal_revision
test_legacy_event_never_writes_accepted_row
test_formal_revision_then_allows_normal_admission
```

---

## Task 5: 1.5F ExchangeInfo Visibility State Machine

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing tests for GRVT class**

Add tests:

```text
test_grvt_legacy_unanchored_event_returns_pending_launch_anchor_missing_not_symbol_missing_reject
test_exchangeinfo_symbol_missing_before_future_anchor_returns_pending_launch_time_in_future
test_symbol_missing_at_anchor_stays_pending_within_recovery_window
test_symbol_appears_five_minutes_after_anchor_promotes_recovery
test_symbol_missing_after_recovery_deadline_becomes_terminal
test_anchor_missing_matrix_never_returns_exchangeinfo_missing_terminal_reason
test_legacy_unanchored_event_not_terminal_after_six_hours
test_legacy_revision_wait_deadline_is_distinct_from_anchor_resolution_deadline
```

**Step 2: Reorder eligibility classifier**

Required order:

```text
1. normalize identity
2. event_type == futures_contract_launch
3. resolve anchor candidates for diagnostics
4. historical/pre-watermark classification
5. source contract triage
6. anchor conflict -> pending_anchor_conflict
7. anchor missing -> pending_launch_anchor_missing
8. anchor future -> pending_launch_time_in_future
9. exchangeInfo unavailable -> pending_exchangeinfo_unavailable
10. exchangeInfo symbol/product validation
11. symbol missing within recovery window -> pending_exchangeinfo_symbol_not_visible_after_anchor
12. symbol missing after recovery deadline -> rejected_launch_symbol_not_visible_timeout
13. clean/recovery age eligibility
14. capacity check
15. accept/start observation
```

**Step 3: Replace deprecated terminal reason**

New production code must never return:

```python
return "rejected", "symbol_not_in_exchangeinfo", ...
```

New terminal reason is only:

```text
rejected_launch_symbol_not_visible_timeout
```

It requires all conditions:

```text
observation_anchor_ms is not None
source_contract_status == formal_v1_valid
exchangeInfo request succeeded
symbol absent
now_ms > observation_anchor_ms + launch_start_guard_ms + max_recovery_start_delay_ms
```

For `observation_anchor_ms is None`:

```text
symbol_visibility_deadline_ms must stay null
terminal symbol visibility reason is impossible
timeout logic must use anchor_resolution_deadline_ms or legacy_source_revision_wait_deadline_ms depending on source_contract_status
```

**Step 4: Add static regression test**

Add a test that scans production Stage 1.5F source files and fails if this exact production pattern exists:

```text
return "rejected", "symbol_not_in_exchangeinfo"
```

Allow legacy string occurrences only in:

```text
fixtures
migration/reporting compatibility
historical audit text
```

---

## Task 6: 1.5F Durable Pending Models and Recovery Loop

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Add backward-compatible model fields**

Add defaults for all new fields:

```text
state_schema_version: int = 3
source_contract_status: str | None = None
pending_source_event_unvalidated: bool = False
required_source_revision: str | None = None
pending_reason: str | None = None
anchor_resolution_started_at_ms: int | None = None
anchor_resolution_deadline_ms: int | None = None
anchor_resolution_retry_count: int = 0
anchor_resolution_last_attempt_at_ms: int | None = None
legacy_source_revision_wait_started_at_ms: int | None = None
legacy_source_revision_wait_deadline_ms: int | None = None
symbol_visibility_deadline_ms: int | None = None
capacity_defer_count: int = 0
capacity_deferred_at_ms: int | None = None
next_capacity_check_at_ms: int | None = None
latest_source_event_id: str | None = None
latest_event_payload_hash: str | None = None
revision_seen_count: int = 0
```

Do not break old `observer_state.jsonl` deserialization. The loader must keep the dataclass field filter pattern:

```python
cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
```

All new fields must have `None` / `False` / `0` defaults so Stage 1.5G and legacy state readers can parse both old and new roots.

**Step 2: Pending allowlist**

Ensure restart loader and pending selector include:

```text
pending_anchor_conflict
pending_launch_anchor_missing
pending_launch_time_in_future
pending_exchangeinfo_unavailable
pending_exchangeinfo_symbol_not_visible_after_anchor
pending_observation_capacity
```

**Step 3: Pending deadlines**

Define:

```text
anchor_resolution_started_at_ms = first durable registration time
anchor_resolution_deadline_ms = anchor_resolution_started_at_ms + EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS
admission_open_ms = observation_anchor_ms + EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS
symbol_visibility_deadline_ms = admission_open_ms + EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS
```

When `observation_anchor_ms is None`:

```text
admission_open_ms = null
symbol_visibility_deadline_ms = null
timeout fallback = anchor_resolution_deadline_ms for formal_v1 anchor damage
timeout fallback = legacy_source_revision_wait_deadline_ms for legacy_unvalidated_recoverable
```

Add config if absent:

```text
EXTERNAL_SIGNAL_STAGE1_5F_LEGACY_SOURCE_REVISION_WAIT_MS
```

First version policy:

```text
legacy_unvalidated_recoverable waits longer than 6h for formal revision.
legacy timeout becomes diagnostic_non_consumable / rejected_launch_anchor_unavailable_timeout only after the legacy wait deadline.
legacy timeout must not use exchangeInfo-missing terminal reason.
```

Revision must not reset `first_seen_at_ms`, `anchor_resolution_started_at_ms`, or `legacy_source_revision_wait_started_at_ms`.

**Step 4: Tests**

Add tests:

```text
test_pending_exchangeinfo_symbol_not_visible_is_rechecked
test_pending_exchangeinfo_symbol_appears_then_promotes
test_pending_exchangeinfo_state_survives_restart
test_pending_exchangeinfo_state_times_out_only_after_deadline
test_pending_unvalidated_event_recovers_from_validated_revision
test_pending_revision_upserts_existing_state_without_new_event_symbol_id
test_active_completed_revision_records_diagnostic_without_reopening_observation
test_all_new_pending_fields_roundtrip
test_anchor_resolution_started_at_survives_restart
test_capacity_pending_anchor_does_not_move_after_restart
test_legacy_observer_state_loads_with_safe_defaults
test_legacy_revision_wait_deadline_is_distinct_from_anchor_resolution_deadline
test_revision_does_not_reset_original_wait_started_at
```

**Step 5: 1.5D scheduler schema migration**

In the same commit or an adjacent schema commit, upgrade 1.5D retry scheduler serialization for title candidate state:

```text
detail_retry_scheduler_schema_version
candidate_symbols
symbol_validation_status = pending_detail_launch_anchor
detail_fetch_status = pending_detail_required
scheduler_lane
first_attempt_due_at_ms
lane_defer_count
last_served_lane
anchor provenance fields
detail attempt metadata
```

Add tests:

```text
test_title_candidate_scheduler_state_survives_restart
test_scheduler_lane_and_attempt_metadata_survive_restart
test_unknown_scheduler_status_loads_fail_safe
```

---

## Task 7: 1.5F Capacity Pending Instead of Terminal Budget Rejection

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing tests**

Add tests:

```text
test_budget_exceeded_defers_to_pending_capacity_not_terminal_rejected
test_capacity_pending_rechecks_without_moving_anchor
test_capacity_pending_after_recovery_deadline_rejects_anchor_age_exceeded_not_budget_exceeded
```

**Step 2: Move capacity check to the end**

Capacity/budget check may run only after:

```text
source_contract_status == formal_v1_valid
anchor resolved and due
exchangeInfo symbol/product validation passed
clean/recovery age eligibility classified
```

If capacity unavailable:

```text
status = pending_observation_capacity
reason = pending_observation_capacity
capacity_defer_count += 1
capacity_deferred_at_ms = now_ms
next_capacity_check_at_ms = now_ms + poll_interval_ms
```

It must not write `events_rejected` with `budget_exceeded`.

---

## Task 8: 1.5F Summary, Diagnostics, and Runtime Gate Output

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Add summary counters with defaults**

Add counters:

```text
pending_exchangeinfo_symbol_not_visible_after_anchor_count
pending_source_event_unvalidated_count
rejected_launch_symbol_not_visible_timeout_count
deprecated_symbol_not_in_exchangeinfo_emitted_count
pending_observation_capacity_count
```

Existing counters must continue to deserialize from old summary files.

**Step 2: Add sample-capped diagnostics**

Add diagnostics for:

```text
legacy_unvalidated_recoverable_pending
pending_exchangeinfo_symbol_not_visible_after_anchor
rejected_launch_symbol_not_visible_timeout
capacity_deferred
```

Cap samples by existing diagnostic cap style. Diagnostics must not create formal accepted rows.

**Step 3: Summary invariants**

New root expectations:

```text
deprecated_symbol_not_in_exchangeinfo_emitted_count = 0
block_new_event_admission = false unless runtime gate/source collision/fatal blocker exists
pending counters reflect durable state, not transient in-memory only state
```

---

## Task 9: 1.5D Formal Event Contract Builder and Validator

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5_launch_event_contract.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5_launch_event_contract.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Write failing contract tests**

Add tests:

```text
test_formal_event_contract_requires_version_consumable_identity_and_anchor
test_formal_event_contract_rejects_title_exact_without_exchangeinfo_validation
test_formal_event_contract_accepts_detail_confirmed_anchor
test_formal_event_contract_accepts_exchangeinfo_fallback_anchor_with_detail_attempt
test_formal_event_contract_rejects_anchor_conflict_over_tolerance
test_formal_event_contract_does_not_max_null_disagreement
test_builder_output_is_validated_by_shared_validator
test_all_formal_v1_fixtures_roundtrip_producer_to_consumer
```

**Step 2: Implement builder**

Implement builder in the shared module, not as a private 1.5D-only rule set:

```python
def build_formal_launch_event(...):
    """Return a formal v1 event row only after validate_formal_launch_event() passes."""
```

If existing naming requires a local adapter, it must delegate:

```python
def build_formal_futures_launch_event_contract(...):
    return build_formal_launch_event(...)
```

Required output fields:

```text
formal_event_contract_version
formal_event_consumable_by_stage1_5f
source_contract_status
symbol_identity_validation_status
symbol_effective_launch_times_ms
symbol_onboard_times_ms
symbol_launch_time_candidates_ms
symbol_effective_launch_time_sources
launch_anchor_validation_status
launch_anchor_disagreement_ms
launch_anchor_comparison_status
launch_anchor_evidence_level
detail_fetch_attempted
detail_fetch_status
detail_fetch_variant
detail_confirmation_missing
source_article_id
stable_event_key
event_id
parser_version
symbol_extraction_version
```

**Step 3: Anchor provenance levels**

Implement:

```text
detail_confirmed
detail_exchangeinfo_consensus
exchangeinfo_fallback
conflict
missing
```

Rules:

```text
single source anchor -> disagreement null, not 0
both sources and abs(diff) <= tolerance -> consensus
both sources and abs(diff) > tolerance -> conflict, no formal emit
```

Do not duplicate anchor evidence logic outside `classify_anchor_evidence(...)`.

---

## Task 10: 1.5D Unique Formal Event Writer

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Add wrappers**

Add:

```python
def append_formal_futures_launch_event(stream_paths: dict, row: dict) -> None:
    validation = validate_formal_launch_event(row)
    if not validation["valid"]:
        append_stage1_5d_diagnostic(stream_paths, {
            "diagnostic_type": "formal_event_contract_invalid",
            "blockers": validation["blockers"],
            "source_article_id": row.get("source_article_id"),
            "symbols": row.get("symbols"),
        })
        return
    append_jsonl(stream_paths["events"], row)


def append_stage1_5d_diagnostic(stream_paths: dict, row: dict) -> None:
    append_jsonl(stream_paths["diagnostics"], row)
```

Adjust names if existing diagnostic stream uses another path, but keep formal writer unique. The writer must be fail-closed even when called directly by a future code path.

**Step 2: Replace direct appends**

Replace every direct:

```python
append_jsonl(stream_paths["events"], ...)
```

with the formal writer. Legacy fallback paths must call diagnostic writer or keep scheduler pending, not formal writer.

**Step 3: Static tests**

Add tests:

```text
test_only_formal_event_writer_can_append_events_stream
test_all_legacy_fallback_paths_emit_diagnostic_not_formal_event
test_all_event_append_paths_reject_unanchored_futures_launch_formal_emit
test_writer_rejects_unvalidated_row_even_when_called_directly
```

Static rule:

```text
Only append_formal_futures_launch_event contains append_jsonl(stream_paths["events"], ...)
```

The static test should inspect every `append_jsonl(...)` call site, preferably with AST. A simple string grep is acceptable only as a supplemental check because it can miss aliases such as `events_path = stream_paths["events"]`.

---

## Task 11: 1.5D Title-Symbol Path Enters Detail/Validation Flow

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing GRVT tests**

Add tests:

```text
test_title_symbol_launch_article_enters_detail_required_pending_not_immediate_emit
test_grvt_title_symbol_requires_launch_anchor_before_formal_emit
test_single_symbol_title_bapi_body_extracts_launch_time_and_emits_validated_event
test_detail_retry_max_age_without_anchor_writes_non_consumable_diagnostic_not_event
```

**Step 2: Change title-symbol behavior**

Old behavior:

```text
ev.get("symbols") -> normalize_live_event -> events/*.jsonl
```

New behavior:

```text
ev.get("symbols") -> detail_retry_state[article_id]
candidate_symbols = title symbols
symbol_extraction_source = title
symbol_validation_status = pending_detail_launch_anchor
detail_fetch_attempted = false
detail_fetch_status = pending_detail_required
next_detail_retry_at_ms = now_ms
no formal event append yet
```

**Step 3: Formal emit only after validation**

Emit only when:

```text
candidate_symbols non-empty
per-symbol launch anchor available or allowed exchangeInfo fallback available
symbol_identity_validation_status == validated_by_exchangeinfo
formal contract builder returns formal_v1_valid
```

---

## Task 12: 1.5D Detail Scheduler Lane/Fairness

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py` if present/appropriate
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Add tests**

Add tests:

```text
test_title_known_and_generic_title_both_receive_first_detail_attempt
test_title_known_burst_does_not_starve_generic_title
test_old_202_backlog_does_not_starve_grvt_like_article
test_detail_attempt_manifest_count_matches_scheduler_attempt_count
test_budget_one_round_robins_title_and_generic_fresh_lanes
test_scheduler_cursor_survives_restart
test_old_backlog_eventually_receives_service
test_no_lane_can_monopolize_all_budget
test_first_attempt_sla_breach_is_reported
test_lane_scheduler_still_enforces_per_article_max_retries
```

**Step 2: Implement lane selector**

Lanes:

```text
Lane 1: title-known, anchor-missing fresh articles
Lane 2: generic-title, symbol-missing fresh articles
Lane 3: recent transient retries
Lane 4: old transient backlog
```

Minimum contract:

```text
Lane 1 gets first-attempt budget.
Lane 2 gets first-attempt budget.
Old HTTP 202 backlog cannot consume the whole per-poll budget.
Every actual HTTP request writes one request_manifest row and increments attempt_count once.
```

Deterministic algorithm:

```text
Priority 1:
  overdue first-attempt articles from Lane 1 or Lane 2 where attempt_count = 0

Priority 2:
  Lane 1 and Lane 2 persistent round-robin

Priority 3:
  Lane 3 recent transient retries

Priority 4:
  Lane 4 old transient backlog
```

When total per-poll budget is 1:

```text
poll N     -> Lane 1
poll N + 1 -> Lane 2
```

When total per-poll budget is >= 2:

```text
reserve at least 1 slot for Lane 1 if due
reserve at least 1 slot for Lane 2 if due
remaining slots can serve Lane 3/4 by age and retry_due_at
```

Persist across restart:

```text
scheduler_lane_cursor
last_served_lane
lane_defer_count
first_attempt_due_at_ms
```

Config additions if absent:

```text
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FIRST_ATTEMPT_SLA_SEC
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_LANE1_MIN_SLOTS_PER_POLL
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_LANE2_MIN_SLOTS_PER_POLL
```

Hard cap:

```text
Every lane must enforce EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES = 3 per article.
Lane priority cannot reset attempt_count or create infinite retry loops.
```

Do not silently increase request budgets unless a config change and tests justify it.

---

## Task 13: 1.5D Postponement/Revision Guard

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Add tests**

Add tests:

```text
test_postponement_notice_not_treated_as_new_launch
test_pending_launch_receives_postponement_revision_and_does_not_promote_old_anchor
test_usd1_usdc_title_symbols_still_follow_formal_anchor_contract
```

**Step 2: Parser classification**

Postpone/delayed/rescheduled notices:

```text
not futures_contract_launch
write launch_schedule_revision diagnostic
no new formal event row
no automatic active observation mutation
```

If a pending event with same stable identity exists, mark revision conflict/pending diagnostic only.

---

## Task 14: 1.5F Formal Revision Upsert

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Add tests**

Add tests:

```text
test_pending_unvalidated_event_recovers_from_formal_v1_revision
test_pending_revision_preserves_event_symbol_id_and_first_seen
test_pending_revision_updates_anchor_candidates_and_latest_payload_hash
test_completed_revision_does_not_reopen_observation
```

**Step 2: Immutable vs updatable fields**

Immutable:

```text
event_symbol_id
stable_event_symbol_key
source_article_id
symbol
first_seen_at_ms
```

Updatable:

```text
latest_source_event_id
latest_payload_hash
revision_seen_count
anchor candidates
resolved anchor
source validation fields
```

Same stable key + pending:

```text
upsert existing pending state
no second accepted row
no duplicate observation state
```

Active/completed:

```text
record diagnostic
no window mutation
no reopen
```

---

## Task 15: Integration Tests for GRVT, A827, 93b5, POPMART

**Files:**
- Modify/Add tests under `tests/research/external_signal_shadow/`
- Modify/Add tests under `tests/scripts/external_signal_shadow/`

**Step 1: Add regression cases**

Required coverage:

```text
GRVT title-only prelaunch event cannot be terminal rejected by 1.5F.
GRVT title-only article cannot be immediate formal emitted by 1.5D.
A827 BAPI table parser still extracts TMF/TBT/BITO launch times.
93b5 multi-symbol all-or-none still emits all siblings exactly once.
POPMART launch-time gated observer still blocks prelaunch depth rows.
Historical anchor hygiene still suppresses old pre-bootstrap anchors.
```

**Step 2: Full targeted pytest**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_a827_boundary_regression.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Stage 1.5G compatibility is mandatory because formal event/state schemas change:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py -q
```

If runtime permits, run the broader stage suites:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow \
  tests/scripts/external_signal_shadow -q

make lint
make check
```

---

## Task 16: Static Hygiene and Backward Compatibility Checks

**Files:**
- All modified files

**Step 1: Static source checks**

Run:

```bash
rg -n 'return "rejected", "symbol_not_in_exchangeinfo"|return "rejected", "budget_exceeded"' \
  src/research/external_signal_shadow \
  scripts/external_signal_shadow || true

rg -n 'append_jsonl\(stream_paths\["events"\]' \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
```

Expected:

```text
No production return of deprecated symbol_not_in_exchangeinfo.
No production terminal budget_exceeded for capacity.
Only formal writer contains events stream append.
```

**Step 2: Syntax and diff checks**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m compileall \
  scripts/external_signal_shadow \
  src/research/external_signal_shadow

git diff --check
```

**Step 3: Fixture integrity**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
for p in Path('tests/fixtures/external_signal_shadow').rglob('*.json'):
    json.loads(p.read_text(encoding='utf-8'))
for p in Path('tests/fixtures/external_signal_shadow').rglob('*.jsonl'):
    for i, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
        if line.strip():
            json.loads(line)
print('fixture_json_ok')
PY
```

---

## Task 17: Deployment Review Document

**Files:**
- Add: `docs/reviews/2026-08-01-stage1-5d-1-5f-title-anchor-gate-hotfix-deployment-review_CN.md`
- Optional Update: `docs/project-status/current-project-state_CN.md`
- Optional Update: `_project_context/source_upload` generation logic if source pack is regenerated

**Step 1: Create a new deployment checklist**

Do not use `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md` as the primary checklist for this hotfix. It can remain as historical reference only.

Checklist must be split into two deployment phases.

Phase A defensive 1.5F deployment:

```text
1. Verify local clean/expected worktree and record commit SHA.
2. Scoped sync only the Phase A files unless a full sync is explicitly justified.
3. SHA256 compare every synced source/test/config file on server.
4. Run server targeted Phase A pytest.
5. Confirm current/old 1.5D runtime gate is fresh/ready.
6. Check old 1.5F active/pending observations grouped by source_article_id.
7. If old 1.5F has active observation, leave it drain-only and start a new Phase A 1.5F root.
8. Bootstrap new Phase A 1.5F watermark against the 1.5D events root it will consume.
9. Start Phase A 1.5F with --stage1-5d-runtime-gate, not old --stage1-5d-summary.
10. Verify legacy unversioned GRVT-like rows become pending only: no active, no accepted, no deprecated symbol_not_in_exchangeinfo.
```

Phase B strict 1.5D + 1.5F deployment:

```text
1. Deploy Phase B commit after Phase A is passing.
2. Scoped sync Phase B files and SHA256 compare.
3. Run server full targeted 1.5D/1.5F/1.5G pytest.
4. Start new 1.5D root with suffix 7d_title_anchor_validation_gate_hotfix.
5. Wait until same-root live_safety_gate_summary is READY.
6. Bootstrap a new Phase B 1.5F watermark against the new 1.5D events root.
7. Start new Phase B 1.5F root using the new 1.5D runtime gate.
8. Verify formal_v1 producer/consumer roundtrip using any new formal event row.
9. Stop or archive Phase A compatibility root only after Phase B root is healthy and no active observation is being killed.
10. Record final commit SHA, server SHA256 evidence, root IDs, and rollback commands.
```

Do not use full project sync as the default hotfix deployment method. Default is scoped sync + SHA256 compare. Full sync is allowed only when explicitly recorded with rationale and excludes.

**Step 2: Production checks must include these greps**

```bash
cat "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" | python3 -m json.tool | grep -E \
'"decision"|"consumable_by_stage1_5f"|"successful_poll_count"|"failed_poll_count"|"fatal_blockers"|"multi_symbol_candidate_set_emission_enabled"'

cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" | python3 -m json.tool | grep -E \
'"decision"|"stage1_5d_gate_mode"|"stage1_5d_runtime_gate_decision"|"stage1_5d_runtime_gate_stale"|"block_new_event_admission"|"pending_source_event_unvalidated_count"|"pending_exchangeinfo_symbol_not_visible_after_anchor_count"|"deprecated_symbol_not_in_exchangeinfo_emitted_count"|"blocker"'
```

Expected:

```text
stage1_5d_runtime_gate_ready
stage1_5d_runtime_gate_stale = false
block_new_event_admission = false
deprecated_symbol_not_in_exchangeinfo_emitted_count = 0
```

**Step 3: Commit boundaries**

The runbook must preserve deployable commit boundaries:

```text
Commit A:
  1.5F defensive compatibility only
  shared validator read path allowed only if complete and tested

Commit B:
  1.5D shared formal contract builder + validating writer
  1.5F validator wired to shared module

Commit C:
  scheduler fairness + fixtures + deployment runbook/source upload updates
```

Phase A deployment must not include partial Phase B code that changes 1.5D formal emission but has not passed Phase B tests.

---

## Task 18: Production Acceptance Criteria

A deployment is acceptable only if all local and server checks pass.

**Phase A acceptance:**

```text
1. GRVT legacy unanchored event fixture returns pending_launch_anchor_missing or pending_source_event_unvalidated, not rejected.
2. Future-anchor symbol missing returns pending_launch_time_in_future.
3. Anchor reached but within recovery window returns pending_exchangeinfo_symbol_not_visible_after_anchor.
4. Symbol missing after recovery deadline returns rejected_launch_symbol_not_visible_timeout.
5. Capacity unavailable returns pending_observation_capacity.
6. New production code emits no symbol_not_in_exchangeinfo terminal reason.
```

**Phase B acceptance:**

```text
1. 1.5D title-symbol article no longer immediate-emits formal row.
2. 1.5D writes request_manifest detail attempt for title-symbol article.
3. Formal event row has formal_event_contract_version = 1.
4. Formal event row has formal_event_consumable_by_stage1_5f = true.
5. Formal event row has validated_by_exchangeinfo identity.
6. Formal event row has per-symbol launch anchor candidates, source, disagreement, comparison status, and evidence level.
7. Missing anchor timeout writes diagnostic only, not formal events/*.jsonl.
8. Direct events append static check passes.
```

**Live root acceptance:**

```text
1. 1.5D and 1.5F tmux sessions both alive.
2. 1.5D live_safety_gate_summary is ready and consumable.
3. 1.5F reads runtime gate from current 1.5D root.
4. cross_root_upstream_summary_dependency = false.
5. request_success_rate stays healthy.
6. no active observation unless a valid launch event exists.
7. no deprecated symbol_not_in_exchangeinfo emission in new root.
```

---

## Task 19: Rollback and Incident Handling

If Phase A deployment fails:

```text
stop new 1.5F root
restart previous observer only in no-new-admission safe mode if available
keep 1.5D running for raw evidence capture
never restore prelaunch symbol_not_in_exchangeinfo hard reject as acceptable clean path
```

If Phase B deployment starves event emission:

```text
keep raw_payloads/request_manifest/detail_retry_scheduler_state
pause 1.5F new admission
fix scheduler/detail retry lane logic
never re-enable title-only formal emit shortcut
```

If a live new event appears during deployment:

```text
prefer safe pending over restart churn
if 1.5F already has active observation, do not kill it without preserving output root and state
if no active/pending observation, restart with new suffix after SHA256 verification
```

---

## Verification Command Summary

Run locally before deployment:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_a827_boundary_regression.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q

PYTHONPATH=src:. .venv/bin/python -m compileall \
  scripts/external_signal_shadow \
  src/research/external_signal_shadow

git diff --check
```

Run static guards:

```bash
rg -n 'return "rejected", "symbol_not_in_exchangeinfo"|return "rejected", "budget_exceeded"' \
  src/research/external_signal_shadow \
  scripts/external_signal_shadow || true

rg -n 'append_jsonl\(stream_paths\["events"\]' \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
```

---

## Final Notes

This plan intentionally accepts a possible short-term coverage sacrifice: Phase B may delay formal emit until detail/BAPI or exchangeInfo anchor evidence is available. That is preferable to false formal evidence or irreversible prelaunch rejection. The success criterion is not “capture every event early”; it is “never admit or reject a launch event without a defensible launch-anchor contract.”
