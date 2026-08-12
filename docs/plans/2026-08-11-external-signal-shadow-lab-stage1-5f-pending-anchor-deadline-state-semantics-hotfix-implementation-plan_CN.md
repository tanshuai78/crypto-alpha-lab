# Stage 1.5F Pending Anchor Deadline State Semantics Hotfix Implementation Plan

```text
status = plan_draft
source_design = docs/designs/2026-08-11-external-signal-shadow-lab-stage1-5f-pending-anchor-deadline-state-semantics-hotfix-design_CN.md
implementation_allowed = false
schedule_revision_producer_enablement_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` or `executing-plans` task-by-task only after this Plan is independently reviewed, receives verdict `Approve`, and the user explicitly approves execution. Do not create per-task commits unless the user explicitly requests them.

**Goal:** Prevent valid long-lead formal launch anchors from being terminally rejected by the 6-hour unresolved-anchor deadline, while preserving fail-closed unresolved paths and preventing stale anchors or cancelled schedules from becoming active observations.

**Architecture:** Reuse the current `EventSymbolState` fields and the existing 5-minute pending re-resolution clock. State construction and loader re-resolution classify current anchor state before applying an unresolved deadline. The existing runner consumes schedule revisions before pending re-evaluation, promotes only explicit admission statuses, and filters the pending summary input so `pending_cancelled` is not reported as an observation still waiting to launch.

**Tech stack:** Python 3.11, dataclasses, existing JSONL state storage, pytest, Ruff. No dependency, schema version, configuration, network endpoint, or background worker is added.

## Global Constraints

- Retain `EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS = 6h`; do not relax it.
- Retain `EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS = 14d`, the existing retry interval, and all depth collection thresholds.
- Use existing `anchor_resolution_started_at_ms`, `anchor_resolution_deadline_ms`, `next_anchor_resolution_at_ms`, and `applied_schedule_revision_ids`; do not add state fields or raise `observer_state_schema_version`.
- Reuse `select_latest_applicable_official_schedule()` for point-in-time schedule selection. Do not infer latest revision from JSONL order.
- For formal revision v2, preserve the current identity contract: `revision_id == revision_semantic_id == revision_application_id` and each is non-empty. `revision_payload_version_id` and `revision_observation_id` remain distinct provenance identities.
- `revision_application_id` is a revision-row application/idempotency identity, not an `EventSymbolState` field. State uses existing durable `applied_schedule_revision_ids` to suppress duplicate application and to distinguish a new application from a retry/replay.
- `pending_cancelled` is a non-admissible durable sink, not a terminal historical rewrite:
  `status = pending_cancelled`, `pending_reason = official_schedule_cancelled`, `pending_terminal_reason = ""`.
- `pending_cancelled` has no anchor, admission check, or re-resolution schedule; it is not re-resolved, promoted, or included in `pending_launch_observation_count`.
- Do not change Stage 1.5D, schedule-revision producer/registry contracts, Git ancestry attestation, 1.5G decision logic, or any trading permission.
- Do not run `ruff check --fix .`, repository-wide formatter/autofix, `git clean`, or a destructive cleanup command.

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- `tests/fixtures/external_signal_shadow/stage1_5f/pending_anchor_deadline_state_semantics/`

Additional read-only verification paths (may be executed, never modified by this Plan):
- `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py`
- `tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`

Allowed documentation paths:
- `docs/reviews/2026-08-11-external-signal-shadow-lab-stage1-5f-pending-anchor-deadline-state-semantics-hotfix-deployment-checklist_CN.md`

Allowed generated/runtime artifacts:
- none; runtime roots under `data/` may be generated during deployment but must not be committed.

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
  - compatibility evidence: state reload tests in `test_stage1_5f_live_depth_observer_state.py` prove nullable existing fields remain readable.
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
  - compatibility evidence: runner passes only retryable/admission-capable pending states; existing summary schema and direct counter logic remain unchanged.
- `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`
  - compatibility evidence: loader tests exercise existing `select_latest_applicable_official_schedule()` point-in-time semantics and Task 5 runs its unchanged contract regression file read-only; no contract shape changes.
- `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py`
  - compatibility evidence: runner revision idempotency tests and Task 5's unchanged registry regression file remain green; no registry storage or status changes.
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
  - compatibility evidence: Task 5 runs its unchanged integrity regression file read-only; no review taxonomy or decision code changes.
- `configs/base.py`
  - compatibility evidence: targeted tests assert existing 6h/14d/retry/guard values are consumed without modification.

Forbidden:
- Any code, test, fixture, documentation, generated artifact, or formatting mutation outside the paths above.
- Any Stage 1.5D parser, formal event contract, schedule-revision producer, registry, Git ancestry attestation, 1.5G, trading, execution, or config change.
- Producer enablement, `RISK_LIVE_TRADING_ENABLED` changes, paper/live trading, alpha interpretation, or execution-engine changes.
- Full-repository autofix/formatting and unscoped destructive cleanup.

## Preconditions And Baseline

Record these values before Task 1. They anchor the completion audit and prove that no unrelated dirty state was claimed by this Plan:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export BASE_SHA="$(git rev-parse HEAD)"
export PLAN_PATH="docs/plans/2026-08-11-external-signal-shadow-lab-stage1-5f-pending-anchor-deadline-state-semantics-hotfix-implementation-plan_CN.md"
export PLAN_SHA256="$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}')"
printf 'BASE_SHA=%s\nPLAN_SHA256=%s\n' "$BASE_SHA" "$PLAN_SHA256"
git status --short --untracked-files=all
```

Expected: `BASE_SHA` and `PLAN_SHA256` are non-empty. Preserve any pre-existing dirty/untracked path with its own patch or SHA-256 provenance; do not revert, overwrite, or attribute it to this Plan.

Topology was verified against source and advisory Graphify queries for `create_pending_observation_state`, `apply_anchor_contract_revision_to_state`, `re_resolve_pending_anchor`, and `process_schedule_revision_event`. Their verified direct production consumers are the three allowed implementation paths; their verified regression consumers are the three allowed test paths. No omitted schema or transport consumer requires migration.

### Task 0: Lock Current Workspace, Interfaces, And Incident Evidence

**Files:**
- Read only: `configs/base.py`, the three allowed implementation files, `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`, `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`, and `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py`.
- Read only: locally retained `data/` or `_project_context/` evidence, if any.

**Design invariants:** precondition for every `INV-*`; no repository mutation.

**Interfaces:**
- Consumes: the current checked-out workspace and any local evidence for article `45c2f20d589b420e80063ab75feb41f2`.
- Produces: terminal-visible preflight evidence and the provenance values consumed by Task 1. It creates no runtime root and no committed artifact.

- [ ] **Step 1: Freeze initial workspace provenance**

Run:

```bash
export INITIAL_STATUS_FILE="/tmp/stage1_5f_pending_anchor_initial_status.txt"
git status --short --untracked-files=all | tee "$INITIAL_STATUS_FILE"
shasum -a 256 "$INITIAL_STATUS_FILE"
```

Expected: every pre-existing dirty/untracked path is recorded. This does not authorize deletion, staging, overwrite, or attribution of those paths to this Plan.

- [ ] **Step 2: Assert configuration and durable-state prerequisites**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from configs import base
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import EventSymbolState

assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS == 6 * 60 * 60 * 1000
assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS == 14 * 24 * 60 * 60 * 1000
assert isinstance(base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS, int)
assert base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS >= 0
assert base.RISK_LIVE_TRADING_ENABLED is False
for name in (
    "anchor_resolution_started_at_ms", "anchor_resolution_deadline_ms",
    "next_anchor_resolution_at_ms", "pending_reason",
    "pending_terminal_reason", "applied_schedule_revision_ids",
):
    assert name in EventSymbolState.__dataclass_fields__, name
print("stage1_5f_preflight_state_and_config=ok")
PY
```

Expected: `stage1_5f_preflight_state_and_config=ok`. Any failure stops execution; do not add fallback fields, thresholds, or configuration.

- [ ] **Step 3: Assert revision identity, registry, and selector prerequisites**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from research.external_signal_shadow.stage1_5_launch_anchor_contract import build_formal_schedule_revision_row, select_latest_applicable_official_schedule
from research.external_signal_shadow.stage1_5f_schedule_revision_registry import compute_revision_application_id

row = build_formal_schedule_revision_row(
    source_article_id="revision-source", supersedes_source_article_id="launch-source",
    symbol="TESTUSDT", revised_anchor_ms=2_000,
    revision_id="revision-1", revision_semantic_id="revision-1",
    revision_application_id="revision-1", revision_payload_version_id="payload-v1",
    revision_observation_id="observation-1", revision_payload_hash="a" * 64,
    revision_available_at_ms=1_000,
)
assert row["revision_id"] == row["revision_semantic_id"] == row["revision_application_id"]
assert compute_revision_application_id(stable_schedule_identity="identity", revision_id="revision-1", revision_payload_hash="a" * 64)
result = select_latest_applicable_official_schedule(
    "TESTUSDT", [{"symbol": "TESTUSDT", "status": "rescheduled", "anchor_ms": 2_000, "revision_id": "revision-1", "available_at_ms": 1_000}], 1_000,
)
assert result["status"] == "selected" and result["effective_official_anchor_ms"] == 2_000
assert select_latest_applicable_official_schedule("TESTUSDT", [], 1_000)["status"] == "missing"
print("stage1_5f_preflight_revision_contract=ok")
PY
rg -n 'def process_schedule_revision_event|revision_application_id|applied_schedule_revision_ids|def select_latest_applicable_official_schedule|available_at_ms.*as_of_ms' \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py \
  src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py
```

Expected: formal revision identity equality, registry idempotency, and selector `available_at_ms <= as_of_ms` behavior exist. If any referenced identity field or selector status is absent, stop; do not expand the revision schema in this hotfix.

- [ ] **Step 4: Locate incident evidence or explicitly downgrade fixture scope**

Run:

```bash
export INCIDENT_ARTICLE_ID="45c2f20d589b420e80063ab75feb41f2"
find data _project_context -type f \( -name '*.json' -o -name '*.jsonl' \) \
  -exec rg -l "$INCIDENT_ARTICLE_ID" {} + 2>/dev/null || true
```

For each hit, record its path and `shasum -a 256` output, then verify it contains the article, all four Symbols, original durable deadline, official anchors, and actual timeout states. If there is no complete retained event/state artifact, Task 1 `metadata.json` must contain:

```json
{
  "incident_runtime_artifacts_independently_verified": false,
  "fixture_scope": "mechanism_regression_only"
}
```

Missing incident artifacts do not block a generic state-machine regression. They prohibit describing the fixture as a fully independently verified incident replay.

## Invariant-To-Task Mapping

| Design invariant | Implementation evidence |
| --- | --- |
| Current interface/evidence preconditions | Task 0: config, state field, revision identity, selector, registry, and incident-evidence lock. |
| `INV-01`, `INV-03`, `INV-09`, `INV-15` | Tasks 1-2: future state normalization, per-Symbol schedule, audit-field assertions. |
| `INV-02`, `INV-04`, `INV-05`, `INV-06`, `INV-08`, `INV-10`, `INV-12` | Task 2: resolve-before-timeout reducer, deterministic unresolved episodes, restart tests. |
| `INV-07`, `INV-13`, `INV-14`, `INV-15` | Task 4: three-phase poll ordering, explicit promotion, cancelled sink. |
| `INV-11` | Task 5: hard safety assertions and no-config-change verification. |
| Deployment observability and P1 summary correctness | Tasks 3-4: pending-cancelled summary exclusion and checklist assertions. |

### Task 1: Freeze Server Evidence In A Minimal Deterministic Fixture

**Files:**
- Create: `tests/fixtures/external_signal_shadow/stage1_5f/pending_anchor_deadline_state_semantics/launch_event.json`
- Create: `tests/fixtures/external_signal_shadow/stage1_5f/pending_anchor_deadline_state_semantics/revisions.json`
- Create: `tests/fixtures/external_signal_shadow/stage1_5f/pending_anchor_deadline_state_semantics/metadata.json`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Design invariants:** `INV-01`, `INV-02`, `INV-09`, `INV-13`.

**Interfaces:**
- Consumes: the confirmed server event/state facts for article `45c2f20d589b420e80063ab75feb41f2`.
- Produces: small, deterministic formal-v2 and revision rows reused by Tasks 2-3; no raw BAPI payload claim.

- [ ] **Step 1: Write fixture metadata and rows**

Create `metadata.json` exactly with the provenance boundary:

```json
{
  "fixture_provenance": "synthetic_offline_fixture_derived_from_server_evidence",
  "source_article_id": "45c2f20d589b420e80063ab75feb41f2",
  "raw_bapi_payload_available": false,
  "incident_runtime_artifacts_independently_verified": false,
  "fixture_scope": "mechanism_regression_only",
  "purpose": "pending-anchor deadline state semantics only"
}
```

Replace the two incident fields only if Task 0 found and semantically verified complete event/state evidence; then record the exact artifact paths and SHA-256 values in the metadata. `raw_bapi_payload_available` remains `false` unless an actual raw BAPI payload was found and independently verified, which is not required by this Plan.

`launch_event.json` must contain one normalized `formal_v2_valid` multi-Symbol launch row for `KUAISHOUUSDT`, `MEITUANUSDT`, `CSOPSKHYNIX2LUSDT`, and `CSOPSAMSUNG2LUSDT`, with four staggered valid anchors, `first_seen_at_ms`, and a test clock more than six hours before the first anchor.

`revisions.json` must contain only minimal valid schedule revision rows covering postpone, advance, cancelled, and equal-time conflict. Every row must carry all current identity layers:

```text
revision_id = official schedule selector identity
revision_semantic_id = same current v2 semantic identity
revision_application_id = same current v2 consumer application/idempotency identity
revision_payload_version_id = payload provenance identity; may differ
revision_observation_id = observation provenance identity; may differ
revision_payload_hash = payload integrity evidence; may differ without changing application identity in replay fixture
```

The fixture must assert the current v2 equality `revision_id == revision_semantic_id == revision_application_id`; it must never derive one identity by silently assigning another. `available_at_ms` remains the selector's point-in-time ordering key.

- [ ] **Step 2: Add fixture provenance checks**

Add one test helper in each affected test file that loads this exact fixture directory and asserts:

```python
assert metadata["fixture_provenance"] == "synthetic_offline_fixture_derived_from_server_evidence"
assert metadata["raw_bapi_payload_available"] is False
assert launch["source_contract_status"] == "formal_v2_valid"
assert set(launch["symbols"]) == {
    "KUAISHOUUSDT", "MEITUANUSDT", "CSOPSKHYNIX2LUSDT", "CSOPSAMSUNG2LUSDT",
}
```

- [ ] **Step 3: Run fixture checks**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k 'pending_anchor_deadline_state_semantics_fixture' -q
```

Expected: PASS after the fixture and checks exist. No production code changes occur in this task.

### Task 2: Make State Construction And Revision Application Write Unambiguous Pending Semantics

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py:252-320`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py:367-445`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

**Design invariants:** `INV-01`, `INV-03`, `INV-09`, `INV-12`, `INV-13`, `INV-15`.

**Interfaces:**
- Consumes: `create_pending_observation_state(event_symbol_row, status, diagnostics, now_ms)` and `apply_anchor_contract_revision_to_state(state, revision, now_ms)`.
- Produces: existing `EventSymbolState` with no new field, with state-specific schedule/deadline values and audit fields.

- [ ] **Step 1: Write RED state tests**

Add tests with exact behavioral assertions:

```python
def test_formal_future_anchor_has_no_resolution_deadline_but_keeps_refresh_schedule():
    state = create_pending_observation_state(
        event_symbol_row=formal_v2_row("KUAISHOUUSDT"),
        status="pending_launch_time_in_future",
        diagnostics={"observation_anchor_ms": 2_000_000},
        now_ms=1_000_000,
    )
    assert state.status == "pending_launch_time_in_future"
    assert state.anchor_resolution_started_at_ms is None
    assert state.anchor_resolution_deadline_ms is None
    assert state.next_anchor_resolution_at_ms > 1_000_000
    assert state.next_admission_check_at_ms == 2_000_000 + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS
    assert state.pending_terminal_reason == ""


def test_cancelled_revision_is_non_admissible_sink_with_clean_audit_fields():
    updated = apply_anchor_contract_revision_to_state(pending_future_state(), cancelled_revision(), now_ms=1_100_000)
    assert updated.status == "pending_cancelled"
    assert updated.pending_reason == "official_schedule_cancelled"
    assert updated.pending_terminal_reason == ""
    assert updated.observation_anchor_ms is None
    assert updated.next_admission_check_at_ms is None
    assert updated.next_anchor_resolution_at_ms is None
    assert updated.anchor_resolution_started_at_ms is None
    assert updated.anchor_resolution_deadline_ms is None
```

Add two further tests: a valid-to-unresolved revision starts exactly one deadline episode only when its `revision_application_id` is absent from the existing `applied_schedule_revision_ids`; replay of the same application ID after reload does not extend that deadline; a later distinct application ID may start one new episode only after a valid anchor had cleared the prior one. Include a payload-formatting/payload-version variant with the same application ID and assert it does not apply a second semantic revision or reset the deadline.

- [ ] **Step 2: Run RED tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  -k 'formal_future_anchor_has_no_resolution_deadline or cancelled_revision_is_non_admissible_sink or unresolved_episode' -q
```

Expected: FAIL on the current implementation because it assigns the 6h deadline to all pending states, sets the future admission check to the anchor without guard, and leaves cancelled schedules/audit fields stale.

- [ ] **Step 3: Implement the minimal state reducer changes**

In `create_pending_observation_state()`, branch by the incoming `status` before assigning default deadline values. The future branch must preserve the existing refresh interval but explicitly null only resolution-only fields:

```python
if status == "pending_launch_time_in_future" and anchor_ms is not None:
    deadline_ms = None
    resolution_started_ms = None
    next_check = anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS
    next_res = now_ms + retry_interval_ms
else:
    # Preserve current missing/conflict/legacy initialization semantics.
```

Pass `resolution_started_ms` into the existing dataclass field. Preserve an existing unresolved episode from diagnostics rather than computing a new deadline on every rebuild.

In `apply_anchor_contract_revision_to_state()`:

```python
if is_cancelled:
    d.update({
        "status": "pending_cancelled",
        "pending_reason": "official_schedule_cancelled",
        "pending_terminal_reason": "",
        "observation_anchor_ms": None,
        "next_admission_check_at_ms": None,
        "next_anchor_resolution_at_ms": None,
        "anchor_resolution_started_at_ms": None,
        "anchor_resolution_deadline_ms": None,
    })
```

For an official conflict, write `status = "pending_anchor_conflict"`, clear the stale anchor/admission schedule, clear `pending_terminal_reason`, and create or preserve one unresolved episode. For `postponed_without_anchor` or malformed applicable schedule, write `status = "pending_launch_anchor_missing"` with the same stale-anchor cleanup and episode rule. Determine new application from the existing durable list, not from a new state field:

```python
application_id = str(revision.get("revision_application_id") or "")
is_new_application = bool(application_id) and application_id not in state.applied_schedule_revision_ids
```

Create a deadline only when `is_new_application` changed a previously valid state to unresolved; append the application ID through the existing reducer path and do not reset the deadline during later retry, reload, or same-ID replay.

For a revised valid anchor, clear both episode fields, set `pending_launch_time_in_future`, keep the refresh schedule, and set admission time to `revised_anchor + guard`. Do not change active/completed contamination semantics beyond clearing stale pending-only schedules.

- [ ] **Step 4: Run state tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py -q
```

Expected: PASS. The test suite proves initial state, revision application, reload compatibility, cancellation audit precedence, and no sliding deadline.

### Task 3: Resolve First, Then Enforce Only The Applicable Deadline

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py:586-710`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

**Design invariants:** `INV-02`, `INV-04`, `INV-05`, `INV-06`, `INV-08`, `INV-10`, `INV-12`, `INV-13`, `INV-15`.

**Interfaces:**
- Consumes: `re_resolve_pending_anchor(pending_state, event_revisions, exchangeinfo_state, now_ms)`.
- Produces: an existing `EventSymbolState`, either normalized future/ready, retryable unresolved, a valid terminal reject, or unchanged `pending_cancelled`.

- [ ] **Step 1: Write RED loader tests**

Add focused tests:

```python
def test_future_formal_anchor_survives_expired_stale_resolution_deadline():
    state = future_state_with_stale_deadline(deadline_ms=1_100_000)
    updated = re_resolve_pending_anchor(state, [formal_v2_launch_row()], exchangeinfo_state={}, now_ms=1_100_001)
    assert updated.status == "pending_launch_time_in_future"
    assert updated.anchor_resolution_deadline_ms is None
    assert updated.anchor_resolution_started_at_ms is None
    assert updated.next_anchor_resolution_at_ms > 1_100_001
    assert updated.pending_terminal_reason == ""


def test_pending_cancelled_is_not_reresolved():
    state = cancelled_pending_state_with_stale_anchor()
    assert re_resolve_pending_anchor(state, [formal_v2_launch_row()], {}, now_ms=9_999_999) == state
```

Add an idempotence test for a valid future anchor: two due 5-minute re-resolution calls with unchanged current evidence must produce the same status, anchor, `next_admission_check_at_ms`, null resolution episode fields, and a newly advanced refresh timestamp only. It must never terminally reject or start a deadline.

Add tests that prove missing anchor and conflict still terminal precisely at their stored deadline, legacy source still uses its legacy deadline, restart preserves one unresolved episode deadline, a distinct new revision may start a new episode, and out-of-order rows select the result of `select_latest_applicable_official_schedule(symbol, revisions, as_of_ms=now_ms)` rather than the final input row.

- [ ] **Step 2: Run RED loader tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -k 'future_formal_anchor_survives_expired_stale_resolution_deadline or pending_cancelled_is_not_reresolved or unresolved_episode or latest_applicable_schedule' -q
```

Expected: FAIL because the current reducer checks the old deadline before resolution, takes the final matching row by input order, and re-resolves all `pending_*` statuses.

- [ ] **Step 3: Implement the minimal loader reorder**

Make `pending_cancelled` an immediate no-op before the generic `pending_` guard. Resolve matching evidence and current point-in-time schedule first. Reuse `select_latest_applicable_official_schedule()` and its `available_at_ms <= now_ms` conflict behavior; do not sort or select a last JSONL row locally. Project each matching formal revision event to the selector's existing input shape only at the call site:

```python
{
    "symbol": pending_state.symbol,
    "status": revision["symbol_official_schedule_statuses"][pending_state.symbol],
    "anchor_ms": revision["symbol_revised_anchor_ms"].get(pending_state.symbol),
    "revision_id": revision["revision_id"],
    "available_at_ms": revision["available_at_ms"],
    "supersedes_revision_id": revision.get("supersedes_revision_id"),
}
```

This is a local data projection for the existing SSOT selector, not a new selector/helper or a contract-module change. Map selector results exactly: `selected` to the formal anchor path, `cancelled` to the existing cancelled sink, `official_schedule_conflict` to `pending_anchor_conflict`, and `postponed_without_anchor`/`missing`/`malformed` to `pending_launch_anchor_missing`.

Use this reducer order:

```text
cancelled sink -> unchanged
current point-in-time schedule + formal source + valid future anchor -> normalize future; clear episode
current point-in-time schedule + formal source + valid due anchor -> pending_ready_for_admission; clear episode
current missing/conflict -> preserve or create one unresolved episode; only then enforce its deadline
legacy/unvalidated -> preserve existing legacy deadline behavior
```

For every non-terminal output, set `pending_reason` to the output state meaning and clear `pending_terminal_reason`. Set `next_anchor_resolution_at_ms = now_ms + retry_interval_ms` for retryable/future states only; do not reassign a fresh deadline during ordinary retry. For `pending_launch_time_in_future`, this recurring schedule is the approved point-in-time evidence refresh: it is deliberately non-null, must be idempotent apart from the next refresh timestamp, and must neither terminally reject nor create/extend an unresolved deadline.

- [ ] **Step 4: Run loader tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py -q
```

Expected: PASS. A formal 16-hour lead survives beyond six hours; missing/conflict/legacy defenses remain fail-closed.

### Task 4: Enforce Runner Ordering, Explicit Admission, And Accurate Pending Summary

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py:1215-1535`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py:1730-1740`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Design invariants:** `INV-07`, `INV-09`, `INV-13`, `INV-14`, `INV-15`; reviewer P1-1 and P1-2.

**Interfaces:**
- Consumes: existing `process_schedule_revision_event()` and `re_resolve_pending_anchor()`.
- Produces: the same JSONL state and summary schema; only scheduling order and which states enter existing counters change.

- [ ] **Step 1: Write RED runner tests**

Add five deterministic one-poll tests. Each test runs both input orders (`launch, revision` and `revision, launch`) and asserts identical final state:

```text
same poll launch + postpone -> pending_launch_anchor_missing; no active state or depth request
same poll launch + advance with new anchor still future -> pending_launch_time_in_future; no active state or depth request
same poll launch + advance with new anchor already due -> explicit admission path, not forced pending
same poll launch + cancel -> pending_cancelled; no active state or depth request
same poll equal-available_at conflict -> pending_anchor_conflict; no active state or depth request
```

For the advance-to-due case, add four gate assertions rather than asserting a universal no-depth result:

```python
assert state_after_capacity_failure.status == "pending_observation_capacity"
assert state_after_runtime_gate_failure.status != "active"
assert state_after_exchange_safety_failure.status != "active"
assert state_when_all_existing_gates_pass.status == "active"
```

Add replay coverage using the same launch/revision rows after state and registry reload. The result must not append a second semantic revision application, reset an unresolved deadline, or create an extra accepted row.

Add an explicit stale-anchor parameterized test for `pending_anchor_conflict`, `pending_source_event_unvalidated`, `pending_cancelled`, and malformed pending states:

```python
assert updated_state.status != "active"
assert updated_state.observation_started_at_ms is None
```

Add the required observability regression:

```python
summary = read_summary_after_one_poll(...pending_cancelled_state...)
assert summary["pending_launch_observation_count"] == 0
assert summary["active_observation_count"] == 0
assert re_resolve_call_count == 0
```

- [ ] **Step 2: Run RED runner tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k 'same_poll_postpone or same_poll_advance or same_poll_cancel or same_poll_equal_available_at_conflict or revision_replay or stale_anchor_never_promotes or pending_cancelled_not_counted' -q
```

Expected: FAIL because pending states are currently processed before schedule revisions, the runner has a generic anchor-time promotion branch, and all `pending_*` states are passed into summary.

- [ ] **Step 3: Implement the minimal runner changes**

Partition the already-loaded `events` list once and execute this deterministic three-phase poll. Do not add a runner class, worker, registry, or CLI option:

```text
Phase A - launch registration only
  Register or upsert every current-poll launch EventSymbolState using existing identity,
  watermark, batch, and formal-contract checks.
  For an otherwise eligible new launch, persist pending_ready_for_admission instead of
  promoting it here. Do not append accepted rows or send depth requests in this phase.

Phase B - revision application
  Every matching launch state now exists. Feed every valid formal revision row through the
  existing process_schedule_revision_event() path, preserving its current registry and
  revision_application_id idempotency behavior. This phase may update provisional state,
  but it may not admit or request depth.

Phase C - re-resolution and admission
  Run pending re-resolution for both pre-existing and Phase-A states. It receives the full
  current-poll revision set and uses select_latest_applicable_official_schedule(...,
  as_of_ms=now_ms) as the authoritative final schedule decision. Equal-time semantic
  disagreement becomes pending_anchor_conflict, never an input-order winner. Then allow
  only explicit reducer-authorized statuses through existing capacity, runtime-gate,
  exchange-safety, batch, accepted-row, and depth-request paths.
```

Defer any existing batch completion/acceptance update that depends on admission until Phase C. Preserve current candidate-set all-or-none emission and batch registry behavior; this change only prevents a Phase-A launch from being admitted before its same-poll revision is applied.

Replace the promotion predicate with only reducer-authorized statuses:

```python
admissible = {"pending_ready_for_admission", "eligible_clean_start", "eligible_recovery_only"}
if updated_pending.status in admissible:
    # Keep the existing capacity, runtime-gate, and promotion code unchanged.
```

Do not use `updated_pending.observation_anchor_ms` as a promotion condition.

Before calling `build_live_depth_observer_summary()`, pass only retryable/admission-capable pending states:

```python
summary_pending_states = [
    state for state in states.values()
    if state.status.startswith("pending_") and state.status != "pending_cancelled"
]
```

This is intentionally a runner-side filter. Do not change `LiveDepthObserverSummary` schema or `stage1_5f_live_depth_observer_summary.py`.

- [ ] **Step 4: Run runner tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected: PASS. Revisions are visible before due pending states are considered, only explicit reducer output can promote, and cancelled sink states do not inflate launch-pending metrics.

### Task 5: End-To-End Matrix, Deployment Checklist, And Completion Gate

**Files:**
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Create: `docs/reviews/2026-08-11-external-signal-shadow-lab-stage1-5f-pending-anchor-deadline-state-semantics-hotfix-deployment-checklist_CN.md`

**Design invariants:** `INV-01` through `INV-15`, especially `INV-11`.

**Interfaces:**
- Consumes: Tasks 1-4 and the fixture.
- Produces: repeatable test evidence, a new-root-only read-only deployment checklist, and a completion-audit input boundary.

- [ ] **Step 1: Add the four-Symbol integration regression**

Using the Task 1 fixture, assert each Symbol remains `pending_launch_time_in_future` at `first_seen + 6h + 1ms` while still before its own anchor, then only its own Symbol becomes eligible at its own `anchor + guard`. Assert no sibling is terminally rejected or promoted early.

The test must also assert a cancelled symbol remains absent from `pending_launch_observation_count` without changing the count for the remaining retryable future symbols.

- [ ] **Step 2: Write the deployment checklist**

The checklist must be concise and read-only. It must require:

```text
1. Start only a new 1.5F output root; do not alter an old root/state file.
2. Verify Stage 1.5D runtime gate is ready, events glob expands to real `events/*.jsonl` files, and the same root is bound three ways: `dirname(events_glob)` root == runtime gate `source_root` == intended Stage 1.5D root. If Git-attestation is deployed too, also satisfy its stronger root-contract check.
3. For a future formal event, inspect one state per Symbol:
   status = pending_launch_time_in_future
   anchor_resolution_deadline_ms = null
   next_anchor_resolution_at_ms is non-null
   next_admission_check_at_ms = observation_anchor_ms + guard
4. For a cancelled revision:
   status = pending_cancelled
   pending_reason = official_schedule_cancelled
   pending_terminal_reason = ""
   observation_anchor_ms, next_admission_check_at_ms, next_anchor_resolution_at_ms are null
   pending_launch_observation_count excludes that Symbol.
5. Stop new admission and retain artifacts if a formal future event reaches a timeout terminal before its anchor.
```

Do not include producer enablement, restart/config mutation, trading, execution, or deletion commands.

- [ ] **Step 3: Run the complete scoped test suite**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py -q
```

Expected: PASS. The first three files are mutable verification paths. The final three are read-only compatible-consumer regressions; if one fails and requires its own code/test modification, stop rather than widening this Plan. This proves state creation/reload, unresolved fail-closed behavior, schedule revision ordering, explicit promotion, four-Symbol isolation, cancelled summary exclusion, selector/registry compatibility, and 1.5G state-read compatibility.

- [ ] **Step 4: Run scoped quality and safety checks**

Run:

```bash
.venv/bin/python -m ruff check \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py

git diff --check "$BASE_SHA"
git diff --name-only "$BASE_SHA"
git status --short --untracked-files=all

PYTHONPATH=src:. .venv/bin/python - <<'PY'
from configs import base

assert base.RISK_LIVE_TRADING_ENABLED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is False
print("stage1_5f_safety_flags=ok")
PY

export FINAL_STATUS_FILE="/tmp/stage1_5f_pending_anchor_final_status.txt"
git status --short --untracked-files=all | tee "$FINAL_STATUS_FILE"
PYTHONPATH=src:. .venv/bin/python - <<'PY'
import os
import subprocess
from pathlib import Path

initial = set(Path("/tmp/stage1_5f_pending_anchor_initial_status.txt").read_text().splitlines())
final = set(Path("/tmp/stage1_5f_pending_anchor_final_status.txt").read_text().splitlines())
diff_paths = set(subprocess.check_output(["git", "diff", "--name-only", os.environ["BASE_SHA"]], text=True).splitlines())
new_status_paths = {line[3:] for line in final - initial if len(line) > 3}
paths = diff_paths | new_status_paths
allowed = {
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py",
    "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py",
    "docs/reviews/2026-08-11-external-signal-shadow-lab-stage1-5f-pending-anchor-deadline-state-semantics-hotfix-deployment-checklist_CN.md",
}
assert all(path in allowed or path.startswith("tests/fixtures/external_signal_shadow/stage1_5f/pending_anchor_deadline_state_semantics/") for path in paths), sorted(paths - allowed)
print("stage1_5f_scope_gate=ok")
PY

if git diff "$BASE_SHA" -- \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  | rg -n -i 'RISK_LIVE_TRADING_ENABLED\s*=\s*True|SCHEDULE_REVISION_PRODUCER_ENABLED\s*=\s*True|live_trading_allowed.*true|execution_engine_allowed.*true'; then
  echo "ERROR: forbidden safety permission change in scoped diff" >&2
  exit 1
fi
```

Expected: Ruff and whitespace checks pass; `stage1_5f_safety_flags=ok` and `stage1_5f_scope_gate=ok` are printed; changed and newly untracked paths are a subset of `Allowed Change Scope`; no forbidden permission appears in the scoped diff.

- [ ] **Step 5: Run completion audit before any commit or deployment claim**

Run `.agent/skills/audit-plan-completion/SKILL.md` against this Plan using the recorded `BASE_SHA`, `PLAN_SHA256`, initial/final status provenance, final diff, fixture provenance, and command outputs. The audit must return `complete`.

If the audit is `incomplete` or `blocked`, stop. Use `.agent/workflows/remediate-completion-audit.md`; do not expand this Plan's scope, enable the producer, or deploy around the finding.

## Stop Conditions

Stop execution and return to Design review if any condition occurs:

1. Correct point-in-time schedule selection requires a Stage 1.5D, registry-contract, schema, configuration, or 1.5G code change.
2. A valid formal future anchor still needs a deadline change rather than state-specific semantics.
3. A revision needs a new state field, storage format, background process, endpoint, or configuration flag.
4. Any existing missing/conflict/legacy timeout regression fails after the reducer changes.
5. The code attempts to promote a state not in the explicit admissible set, or `pending_cancelled` can re-enter re-resolution/admission.
6. The summary exclusion requires a schema change rather than filtering the runner input list.
7. A read-only compatible-consumer regression fails due to this change and requires a modification outside `Allowed Change Scope`, or an allowed test requires a modification outside `Allowed Change Scope`.
8. Safety flags, producer default-disabled state, or read-only boundaries differ from the global constraints.

## Completion Boundary

This Plan can prove that the Stage 1.5F state machine preserves valid long-lead formal anchors, stays fail-closed for unresolved anchors, applies schedule revisions before admission, and reports cancelled sinks accurately.

It cannot recover the already missed `45c2...` L2 snapshots, prove market alpha, enable schedule-revision production, authorize execution, or prove a new live root until a future real event is observed under the deployment checklist.

No implementation, commit, producer enablement, or deployment is authorized until this Plan receives independent `Approve` review and explicit user approval.
