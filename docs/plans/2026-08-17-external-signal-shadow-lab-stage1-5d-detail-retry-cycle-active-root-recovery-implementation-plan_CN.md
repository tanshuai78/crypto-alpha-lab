# Stage 1.5D Detail Retry Cycle Durability 与 Active-Root Recovery Hotfix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `.agent/workflows/execute-approved-plan.md` after this Plan has review approval and explicit user authorization. Track each task with the checkboxes below.

**Goal:** 修复 1.5D 将物理 HTTP 请求数误作逻辑 retry 上限而导致的 detail retry starvation；在一次受控 active-root recovery 中，以显式、持久的 D→F provenance 将恢复事件降级为 `recovery_validation_only`，且不改变 formal identity。

**Architecture:** 继续使用现有 `detail_retry_cycle_count` 作为逻辑 retry cycle。1.5D 在任何 HTTP 前持久化 cycle reservation；HTTP telemetry 只保留给 manifest 审计。恢复 provenance 仅由 1.5D runner 的精确 one-shot article authority 写入 event JSONL，1.5F loader 仅从该 marker 降级证据，不从 `T1 - T0` 推断。StorageGuard 使用 output-root 数据平面派生的绝对共享 lock，支持在工作树 C 上重启并继续写入 active root B。

**Tech Stack:** Python 3.11、stdlib (`argparse`, `json`, `pathlib`, `re`)、pytest、ruff、Graphify；不新增依赖、数据库、配置项或 formal contract version。

## Global Constraints

- Design authority: `docs/designs/2026-08-17-external-signal-shadow-lab-stage1-5d-detail-retry-cycle-current-root-recovery-hotfix-design_CN.md`.
- Safety mode remains public-read-only. `RISK_LIVE_TRADING_ENABLED`, paper/live/execution/alpha permissions and schedule-revision producer enablement remain `False`.
- `detail_http_request_count` is transport telemetry only; it must not participate in selector eligibility or logical retry cap.
- Existing config values, retry thresholds, contract versions, parser behavior, raw-payload trust validation and transient max age must not change. This Plan makes no `configs/base.py` change.
- `detail_recovery_provenance` is exactly `active_root_retry_cycle_recovery_v1`; it is additive metadata, not a formal contract or identity input.
- The recovery CLI accepts exactly one 32-lowercase-hex `source_article_id` and the one allowed provenance enum. No wildcard, list, prefix, all-pending mode, bootstrap, synthetic row, root mutation or manual state edit is allowed.
- If current source rejects additive event metadata, if marker changes formal identity, or if the preflight target is terminal/already emitted, STOP. Do not bump a contract version or broaden scope.
- Stage 1.5G remains local/offline only. This Plan does not authorize deployment or active-root cutover; it produces the code, tests, and future runbook gate only.

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- `src/research/external_signal_shadow/stage1_5_storage_guard.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- `tests/research/external_signal_shadow/test_stage1_5_storage_guard.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- `tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py` (read-only compatibility)
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py` (read-only compatibility)

Allowed documentation paths:
- `docs/plans/2026-08-17-external-signal-shadow-lab-stage1-5d-detail-retry-cycle-active-root-recovery-implementation-plan_CN.md`
- `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md` (future active-root recovery preflight/runbook only)

Allowed generated/runtime artifacts:
- none. The active-root recovery ledger is an operator-local artifact outside the repository and must not be committed.

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`
  - compatibility evidence: marker/no-marker runner regression validates `validate_launch_anchor_contract()` and equal anchor hashes/version.
- `src/research/external_signal_shadow/stage1_5_launch_event_contract.py`
  - compatibility evidence: marker/no-marker runner regression validates equal event identity and no version change.
- `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
  - compatibility evidence: runner integration keeps guarded formal event append and exactly-once restart behavior.
- `src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py`
  - compatibility evidence: marker/no-marker runner regression asserts official schedule revision IDs and source-anchor hashes are unchanged.
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
  - compatibility evidence: loader and runner tests prove stored `evidence_start_class` produces recovery-only accepted evidence without runner edits.
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
  - compatibility evidence: existing integrity regression proves `recovery_validation_only` contributes zero to `formal_announcement_and_launch_count`.

Forbidden:
- Any mutation outside the paths above.
- Formal event/schedule-revision contract version or schema change.
- New retry thresholds, config values, feature flags, dependencies, generic recovery framework, database, queue, factory or interface.
- Any `configs/base.py` modification.
- `--mark-recovery-all`, wildcard/list/prefix authority, implicit recovery by timestamp, or a recovery marker on a non-exact article.
- Live-root hand edits, new root/bootstrap, VPS 1.5G review, producer enablement, paper/live/execution/alpha enablement.
- `ruff check --fix .`, global formatter/autofix, `git clean`, `git reset --hard`, `rsync --delete`, or destructive cleanup.

## Invariant-to-Task Mapping

| Design invariant | Task | Mechanical evidence |
|---|---|---|
| INV-01 | 0 | BASE/Design hashes, source/runtime evidence checklist, stop predicates |
| INV-02, INV-04, INV-05 | 1 | selector RED/GREEN matrix; existing bounds regression |
| INV-03, INV-06 | 2 | pre-HTTP durable reservation, failure/crash tests |
| INV-07, INV-08, INV-11 | 3, 5 | marker transport, F same-root/no-bootstrap resume, and cutover lifecycle tests |
| INV-09 | 2, 3 | append-before-cleanup restart regression and marker replay regression |
| INV-10 | 4 | output-root-derived shared flock tests |
| INV-11, INV-12 | 5 | runbook gates and no historical-root mutation commands |
| INV-13 | 6 | safety grep plus read-only compatibility suite |

## Task 0: Freeze Baseline, Incident Predicate, and Topology

**Files:**
- Modify: none.
- Verify: all allowed verification paths.
- Document: this Plan only if a review-required clarification is needed.

**Purpose:** Keep the incident-specific recovery authority separate from general retry code. The Design's reference to "Section 14" means the preflight facts listed in Design §10.1; do not infer a nonexistent Design section.

- [ ] **Step 1: Freeze immutable execution inputs before any code edit.**

```bash
export BASE_SHA="$(git rev-parse HEAD)"
export DESIGN_PATH="docs/designs/2026-08-17-external-signal-shadow-lab-stage1-5d-detail-retry-cycle-current-root-recovery-hotfix-design_CN.md"
export DESIGN_SHA256="$(shasum -a 256 "$DESIGN_PATH" | awk '{print $1}')"
export PLAN_PATH="docs/plans/2026-08-17-external-signal-shadow-lab-stage1-5d-detail-retry-cycle-active-root-recovery-implementation-plan_CN.md"
export PLAN_SHA256="$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}')"
export STATUS_BASELINE="/tmp/stage1_5d_active_root_recovery_status_${BASE_SHA}.porcelain"
export UNTRACKED_BASELINE="/tmp/stage1_5d_active_root_recovery_untracked_${BASE_SHA}.nul"
git status --porcelain=v1 -z > "$STATUS_BASELINE"
git ls-files --others --exclude-standard -z > "$UNTRACKED_BASELINE"
printf 'BASE_SHA=%s\nDESIGN_SHA256=%s\nPLAN_SHA256=%s\nSTATUS_BASELINE=%s\nUNTRACKED_BASELINE=%s\n' \
  "$BASE_SHA" "$DESIGN_SHA256" "$PLAN_SHA256" "$STATUS_BASELINE" "$UNTRACKED_BASELINE"
git status --short --untracked-files=all
git diff --exit-code -- configs/base.py
git diff --exit-code -- \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  src/research/external_signal_shadow/stage1_5_storage_guard.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
```

Expected: record all output in the execution ledger. All mutable implementation and test paths must be tracked-clean at Task 0. Existing dirty/untracked paths outside this Plan are provenance only; do not revert, delete, or claim them.

- [ ] **Step 2: Freeze only the current-B incident predicate before code edits.**

The operator-local ledger must contain the current B commit, exact article `0872245db74c4daaabd4f11984ba52c1`, current D/F absolute roots, target scheduler row hash, `detail_http_request_count=4`, `detail_retry_cycle_count=2`, nonterminal `pending_detail_retry`, overdue retry timestamp, current event/manifest evidence, current watermark/root-contract hashes and current D/F health. This is premise evidence only: do not record a target C commit, future no-event proof, or future `active_observation_count` as if they were immutable. Any mismatch, missing state, or malformed evidence stops implementation authority.

- [ ] **Step 3: Record targeted topology evidence; do not rebuild Graphify.**

```bash
graphify query 'select_detail_retry_attempts'
graphify query 'write_detail_retry_scheduler_state'
graphify query 'record_formal_futures_launch_event'
graphify query 'classify_event_symbol_eligibility_with_diagnostics'
graphify query 'classify_live_depth_evidence_basis'
graphify query 'StorageGuard'
```

Verify the returned direct consumers against source with:

```bash
rg -n 'select_detail_retry_attempts|write_detail_retry_scheduler_state|record_formal_futures_launch_event' \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
rg -n 'classify_event_symbol_eligibility_with_diagnostics|classify_live_depth_evidence_basis' \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
```

Expected: only the four implementation paths require edits. If a verified consumer needs a code change outside the whitelist, STOP for Design/Plan delta.

## Task 1: Remove HTTP-Count Selector Starvation

**Design invariants:** INV-02, INV-04, INV-05.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

**Interfaces:**
- Preserve `select_detail_retry_attempts(...) -> list[str]` signature.
- Logical attempted/never-attempted classification uses durable `detail_retry_cycle_count`, falling back only to legacy `detail_fetch_attempt_count` when that field is absent.
- `detail_http_request_count` remains available in state but is never read by selector eligibility/cap logic.

- [ ] **Step 1: Add RED tests for the incident shape and retained bounds.**

```python
state = {
    ARTICLE: {
        "detail_http_request_count": 4,
        "detail_retry_cycle_count": 2,
        "detail_fetch_attempt_count": 2,
        "detail_retryable": True,
        "last_detail_failure_class": "http_202_empty",
        "next_detail_retry_at_ms": NOW - 1,
        "last_retry_at_ms": NOW - 60_000,
        "first_detected_at_ms": NOW - 120_000,
        "terminal_state": False,
    }
}
assert select_detail_retry_attempts(..., detail_retry_state=state, now_ms=NOW, detail_budget_per_poll=1, endpoint_degraded_until_ms=0, overdue_attempted_retry_budget_per_poll=1) == [ARTICLE]
```

Also assert the same row is not selected if terminal, non-retryable, not due, below the minimum interval, or excluded by the existing degraded-cycle cap. Include a legacy row without `detail_retry_cycle_count` to prove the fallback is limited to `detail_fetch_attempt_count`.

- [ ] **Step 2: Run the focused RED suite.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py -q
```

Expected: the incident-shape test fails before implementation because HTTP count `4` reaches the old `max_retries=3` selector branch.

- [ ] **Step 3: Make the minimal selector change.**

Remove the `max_retries`/`detail_http_request_count` eligibility branch from `select_detail_retry_attempts()`. Select never/attempted rows from `detail_retry_cycle_count` (legacy fallback only), preserving all existing due-time, degraded-window, per-poll budget, overdue-slot, minimum-interval and terminal predicates. Do not modify `configs/base.py`.

- [ ] **Step 4: Run GREEN and guard against accidental config changes.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py -q
git diff --exit-code "$BASE_SHA" -- configs/base.py
```

Expected: all scheduler tests pass; `configs/base.py` has no diff.

## Task 2: Persist Logical Cycle Reservation Before HTTP

**Design invariants:** INV-03, INV-06, INV-09.

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Interfaces:**
- Keep `write_detail_retry_scheduler_state(output_root, scheduler_state, ..., storage_guard=...)` as the only scheduler checkpoint writer.
- Add only runner-local state fields: `inflight_cycle = {"cycle": int, "reserved_at_ms": int}`.
- Selected cycles are reserved for the full selected batch, state is persisted once, and only then may the first HTTP call occur.

- [ ] **Step 1: Add RED runner tests for reservation ordering and crash semantics.**

Use the existing fixture runner with monkeypatched detail fetch functions and a `write_detail_retry_scheduler_state` failure injection.

```python
assert fetch_call_count == 0  # reservation checkpoint raises
assert persisted_article["inflight_cycle"] == {"cycle": 3, "reserved_at_ms": NOW}

# Restart after a persisted reservation and simulated pre-HTTP crash.
assert resumed_state[ARTICLE]["detail_retry_cycle_count"] == 3
assert next_completed_attempt_cycle == 4
assert "request_manifest_persistence_unknown" in diagnostic_types
```

Add three restart subcases: (a) clear checkpoint failure after the diagnostic yields zero HTTP and preserves the reserved cycle; (b) crash after diagnostic but before clear permits a duplicate diagnostic on the next restart but never reuses the cycle; (c) successful clear permits only `previous_cycle + 1` as the next completed logical cycle. These are at-least-once diagnostic assertions, not exactly-once assertions.

Add a post-event-append/pre-scheduler-cleanup crash fixture. After restart and replay of the same trusted payload, assert exactly one event row for the article/event identity and no second `record_formal_futures_launch_event()` append.

- [ ] **Step 2: Run the targeted RED tests.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'reservation or inflight_cycle or crash_after_event_append_before_state_write' -q
```

Expected: at least the new ordering test fails because current code increments the cycle and waits until end-of-poll to write scheduler state.

- [ ] **Step 3: Implement the smallest runner-local reservation reducer.**

Immediately after selection/budget allocation and before any BAPI, primary or fallback fetch:

```python
for article_id in attempt_codes:
    state = detail_retry_state[article_id]
    cycle = int(state.get("detail_retry_cycle_count") or 0) + 1
    state["detail_retry_cycle_count"] = cycle
    state["last_retry_at_ms"] = now_ms
    state["inflight_cycle"] = {"cycle": cycle, "reserved_at_ms": now_ms}

scheduler_state["articles"] = serialize_retry_articles(detail_retry_state)
write_detail_retry_scheduler_state(output_root, scheduler_state, ..., storage_guard=storage_guard)
```

On restart, an existing `inflight_cycle` is an at-least-once persistence-unknown diagnostic: emit the diagnostic, clear `inflight_cycle` in memory, then perform a guarded scheduler checkpoint. Only after that clear checkpoint succeeds may the selector grant a new cycle. If diagnostic emission crashes before the clear checkpoint, a later restart may emit the same diagnostic again; it must never reuse the reserved cycle. If the clear checkpoint fails, issue zero HTTP requests and grant no new cycle. After normal attempt recording, clear `inflight_cycle` only through its normal guarded scheduler checkpoint. Do not create a second persistence system, request journal, or counter.

- [ ] **Step 4: Run GREEN regression coverage.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py -q
```

Expected: reservation failure produces no network side effect; restart cannot reuse a reserved cycle; normal transient/retry behavior remains bounded.

## Task 3: Add Exact One-Shot Recovery Provenance and Prove F Same-Root Resume

**Design invariants:** INV-07, INV-08, INV-09, INV-11.

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Verify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`

**Interfaces:**
- D CLI pair: `--active-root-recovery-source-article-id` and `--active-root-recovery-provenance`.
- The only accepted provenance value is `active_root_retry_cycle_recovery_v1`.
- Both arguments are absent in normal mode, or both are present; any other combination exits before polling.
- D marker field: `detail_recovery_provenance` on the durable formal launch event row only.
- F loader reads exactly that field; it writes its existing state-owned `evidence_start_class="recovery_start"` only for the accepted marker.
- Marker absent retains normal behavior. A present empty, non-string, unknown, or future marker is malformed provenance and must fail closed without clean evidence.
- Same-root F recovery has no F runner code change: test the existing CLI/runtime path against a seeded root and no `--bootstrap-watermark` argument.

- [ ] **Step 1: Add RED D runner tests for strict authority and identity preservation.**

Cover parser/startup validation:

```python
# Exact one-shot matching only.
authority = (ARTICLE_A, "active_root_retry_cycle_recovery_v1")
assert emitted_for(ARTICLE_A)["detail_recovery_provenance"] == authority[1]
assert "detail_recovery_provenance" not in emitted_for(ARTICLE_B)

# Reject wildcard, comma-list, prefix, missing paired option, unknown enum,
# terminal target, and target whose durable event stream already contains ARTICLE_A.
with pytest.raises(SystemExit): run_args("--active-root-recovery-source-article-id", "*")
```

Cover formal identity with the identical base formal payload emitted once with no authority and once with authority. Assert equality for `event_id`, `stable_event_key`, `stable_event_symbol_key` when present, `formal_event_contract_version`, `source_anchor_contract_hash`/`symbol_source_anchor_contract_hashes`, `symbol_official_schedule_revision_ids`, and every existing schedule-revision identity field. Assert only `detail_recovery_provenance` differs. The test must call the existing v2 validator; if it rejects the additive field, STOP rather than modifying a contract/version.

Add a startup-order test: the exact pair is parsed and validated before any poll or network fetch; a generic invocation without both arguments is normal mode but is **not** a valid continuation of a stopped recovery procedure. The test must prove no marker is emitted in normal mode and no fetch/poll occurs when recovery arguments are malformed.

- [ ] **Step 2: Add RED F loader contrast tests.**

```python
normal = formal_bapi_detail_row(detected_at_ms=T0, detail_fetched_at_ms=T1)
recovered = {**normal, "detail_recovery_provenance": "active_root_retry_cycle_recovery_v1"}

assert classify_event_symbol_eligibility_with_diagnostics(normal, ...)[2]["evidence_start_class"] == "clean_start"
assert classify_event_symbol_eligibility_with_diagnostics(recovered, ...)[2]["evidence_start_class"] == "recovery_start"
assert classify_live_depth_evidence_basis(recovered_state, watermark)["live_depth_evidence_basis"] == "recovery_validation_only"
assert classify_live_depth_evidence_basis(recovered_state, watermark)["announcement_time_capture_evidence_allowed"] is False
```

Persist and reload the recovered accepted/state row through the existing F runner fixture. Re-run classification after replay and assert it remains recovery-only. Add no timestamp heuristic test: normal BAPI detail with the same `T0/T1` shape and no marker remains normal.

Add invalid-marker cases for `""`, `"future_v2"`, and `123`: classification must be diagnostic-only/rejected/blocked, must not produce `clean_start`, and must not produce `announcement_and_launch_time` evidence.

- [ ] **Step 3: Add a RED same-root/no-bootstrap F resume fixture.**

Seed one existing F output root with watermark `W`, canonical root ID `R`, readable latest state `S`, root contract, summary source-D-root identity `D`, and a valid old process identity. Start the existing F runner test harness as simulated process C using the **same** `--output-root`, no `--bootstrap-watermark`, and a C runtime-attestation fixture.

```python
assert loaded_watermark_bytes == seeded_watermark_bytes
assert loaded_watermark_hash == seeded_watermark_hash
assert observer_root_contract["consumer_root_id"] == R
assert latest_state[event_symbol_id] == S
assert summary["consumer_process_instance_id"] != old_process_instance_id
assert summary["consumer_startup_commit_sha"] == COMMIT_C
assert summary["consumer_runtime_attestation_verified"] is True
assert summary["consumer_runtime_attestation_compromised"] is False
assert observer_root_contract["source_stage1_5d_output_root_id"] == D
assert observer_root_contract["source_stage1_5d_events_root_id"] == D
assert observer_root_contract["source_stage1_5d_runtime_gate_root_id"] == D
assert summary["block_new_event_admission"] is False
```

Add negative fixtures: a recovery procedure that requests `--bootstrap-watermark` is invalid and must not launch F; source-D-root mismatch fails closed; runtime attestation mismatch blocks admission. The bootstrap prohibition is an operator/runbook gate, not a new F runner feature. These tests modify no F runner production source.

- [ ] **Step 4: Run the focused RED tests.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k 'active_root_recovery or recovery_provenance or recovery_validation_only or bapi_detail' -q
```

Expected: no strict recovery CLI exists, no durable marker is emitted, unknown marker behavior is not fail-closed, and no same-root C-resume proof exists.

- [ ] **Step 5: Implement only the required transport boundary.**

1. Add the two CLI arguments. Validate article ID with `re.fullmatch(r"[0-9a-f]{32}", value)` and provenance with an `argparse` one-value choice. Reject one-sided input before polling.
2. At startup, when authority is supplied, load the exact scheduler row and scan durable event rows for exact `source_article_id`. Reject missing, terminal, already-emitted, malformed, or non-retryable targets. Do not scan or alter any other article.
3. Store the validated authority in runner-local `stream_paths`. In `record_formal_futures_launch_event()`, copy the row, add the marker only when `row["source_article_id"] == authority_article`, then call the existing validator and guarded append. Never include the marker in any event/anchor/schedule-revision identity calculation.
4. In F eligibility classification, distinguish three cases: absent marker follows existing behavior; exact marker forces `evidence_start_class="recovery_start"`, recovery-only basis and false announcement capture eligibility once anchor/admission checks otherwise permit observation; any present-but-invalid marker is diagnostic-only/rejected and never reaches a clean path. In `classify_live_depth_evidence_basis()`, treat persisted `recovery_start` as recovery-only and malformed provenance as non-clean. Do not inspect `detail_fetched_at_ms`, `symbol_resolved_at_ms`, delay duration, or wall clock for recovery provenance.

- [ ] **Step 6: Run GREEN plus read-only F/G compatibility.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py -q
```

Expected: the existing G regression reports `formal_announcement_and_launch_count == 0` for recovery-only evidence. No 1.5G source/test modification is allowed.

## Task 4: Derive the Shared StorageGuard Lock from the Data Plane

**Design invariants:** INV-10.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5_storage_guard.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5_storage_guard.py`

**Interfaces:**
- Keep `StorageGuard(output_root, stage, ...)` signature unchanged.
- `lock_file_path` is derived from the resolved `data/external_signal_shadow` ancestor of `output_root`, never from CWD.

- [ ] **Step 1: Add RED lock identity tests.**

Create D and F roots below one temporary absolute `B/data/external_signal_shadow/...` tree. Change CWD between constructor calls and assert both guards have the same absolute `.stage1_5_storage_guard.lock` path and serialize concurrent `reserve_and_write()` callbacks. Also assert `StorageGuard(active_root_under_B).lock_file_path == B/data/external_signal_shadow/.stage1_5_storage_guard.lock`, the exact pre-patch B-worktree lock location. Assert a root without that ancestor fails closed; it must not fall back to `Path.cwd()`. Update existing StorageGuard test fixture helpers to create their roots below this same path shape; do not weaken the production fail-closed requirement merely to preserve arbitrary `tmp_path/root` fixtures.

- [ ] **Step 2: Run RED test.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py -q
```

Expected: current implementation derives the lock from CWD, so cross-worktree identity test fails.

- [ ] **Step 3: Implement the narrow path derivation.**

Resolve `output_root`, walk its ancestors, select the ancestor whose path suffix is exactly `data/external_signal_shadow`, and create/use only `<that-ancestor>/.stage1_5_storage_guard.lock`. Raise `ValueError("output_root_missing_external_signal_shadow_ancestor")` if absent. Keep the existing local-filesystem `flock` assumption and all reservation arithmetic unchanged.

- [ ] **Step 4: Run GREEN regression.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py -q
```

Expected: D/F roots share one host-data-plane lock independently of worktree/CWD; existing storage budget tests still pass.

## Task 5: Document the Future Active-Root Recovery Gate

**Design invariants:** INV-11, INV-12.

**Files:**
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

- [ ] **Step 1: Add a concise, non-executable-by-default recovery subsection.**

Document the following two distinct evidence times and deterministic lifecycle. This Plan does not authorize actually running the cutover; implementation completion and a separate deployment decision are required first.

```text
Task 0 / current-B premise evidence, before code edits:
  freeze B commit, current roots, current scheduler/event/manifest facts,
  current watermark/root contract and health only.

Deployment preflight, after implementation/completion:
  freeze exact approved C commit and fresh target/root facts again:
  article is one 32-hex value, pending/retryable/nonterminal/not emitted/in max age;
  prove no systemd/supervisord/cron/container restart policy will recreate B or generic C D/F
    (record tmux ls, ps -ef, and verify no auto-supervisor/cron recreates processes);
  D/F gates and host storage are ready; no concurrent writer; F active_observation_count=0;
  current watermark/state/root contract and B lock path are readable; C lock equals B lock.

Cutover:
  1. stop B D and B F; prove both exited; do not checkout or restart B.
  2. start D(C) exactly once, against original absolute D root, with both exact flags:
       --active-root-recovery-source-article-id=<article>
       --active-root-recovery-provenance=active_root_retry_cycle_recovery_v1
  3. record PID, started_at, full command line, C commit, article and enum in the local ledger;
     prove the running command contains both flags before accepting D READY.
  4. verify D READY, same B lock, and target continuity.
  5. start F(C) once against original absolute F root, without --bootstrap-watermark;
     verify same watermark/root/state, C process/commit, healthy attestation and unchanged D-root bindings.
  6. only then allow recovery to continue; verify any emitted target row carries the marker and F evidence is recovery-only.

If D(C) exits before the target becomes terminal or formal:
  stop; no automatic generic restart is a valid continuation; fresh deployment preflight is required;
  any new recovery invocation must repeat the exact authority pair.

Partial-cutover failure matrix:
  C D fails before root write -> stop C processes; preserve roots/ledger; do not restart B; new decision.
  C D writes scheduler state then fails -> stop C processes; preserve roots/ledger; fresh preflight.
  C D emits marked event and C F fails -> stop C D; preserve event/roots; never start old B F.
  C F starts with unhealthy attestation/binding -> stop both C processes; preserve roots/ledger; new decision.
  C pair healthy -> recovery may continue.

Always forbidden:
  bootstrap/new root, automatic B resume, marker stripping, manual state/watermark/event edits,
  manual/offline compaction before recovery, or VPS 1.5G review.
  Existing guarded automatic F startup compaction remains allowed lifecycle behavior.
```

- [ ] **Step 2: Verify documentation stays narrow.**

```bash
rg -n -- '--active-root-recovery-source-article-id|active_root_retry_cycle_recovery_v1|bootstrap|mark-recovery-all|manual' \
  docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

Expected: only one D(C) start path exists; the authority pair, no-bootstrap F resume, no automatic restart/B resume, partial-cutover matrix, process supervisor proof, and compaction distinction are present. No wildcard/all-pending or manual-file-edit instruction appears.

## Task 6: Full Verification and Completion Audit

**Design invariants:** INV-13 and cross-task proof closure.

**Files:**
- Modify: none except failed-test repairs within the approved paths.
- Verify: all allowed verification paths.

- [ ] **Step 1: Run the complete scoped suite.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py -q
```

Expected: all pass. A failure in an affected-but-unchanged contract/consumer is a STOP unless its code is already in the implementation whitelist.

- [ ] **Step 2: Run scoped static and safety checks without autofix.**

```bash
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  src/research/external_signal_shadow/stage1_5_storage_guard.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
git diff --check "$BASE_SHA"
git diff --exit-code "$BASE_SHA" -- configs/base.py
git diff --exit-code "$BASE_SHA" -- \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py
if rg -n 'RISK_LIVE_TRADING_ENABLED\s*=\s*True|EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED\s*=\s*True' configs src scripts; then
  echo 'STOP: safety switch enabled' >&2
  exit 1
fi
if rg -n 'detail_http_request_count.*max_retries|max_retries.*detail_http_request_count' \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py; then
  echo 'STOP: HTTP telemetry still gates retry selection' >&2
  exit 1
fi
```

Expected: no Ruff or whitespace errors; no enabled safety switch; no HTTP-count selector cap; read-only compatibility tests 100% unchanged.

- [ ] **Step 3: Verify exact scope and obtain independent completion audit.**

```bash
git merge-base --is-ancestor "$BASE_SHA" HEAD
python3 - "$BASE_SHA" "$UNTRACKED_BASELINE" <<'PY'
import pathlib
import subprocess
import sys

base_sha, baseline_path = sys.argv[1:]
allowed = {
    "src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py",
    "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py",
    "src/research/external_signal_shadow/stage1_5_storage_guard.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py",
    "tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py",
    "tests/research/external_signal_shadow/test_stage1_5_storage_guard.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py",
    "docs/plans/2026-08-17-external-signal-shadow-lab-stage1-5d-detail-retry-cycle-active-root-recovery-implementation-plan_CN.md",
    "docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md",
}

def nul_paths(raw: bytes) -> set[str]:
    return {part.decode() for part in raw.split(b"\0") if part}

tracked = nul_paths(subprocess.check_output(["git", "diff", "--name-only", "-z", base_sha]))
before = nul_paths(pathlib.Path(baseline_path).read_bytes())
now = nul_paths(subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"]))
changed = tracked | (now - before)
unexpected = sorted(changed - allowed)
assert not unexpected, f"STOP: changed paths outside Allowed Change Scope: {unexpected}"
print({"scope_checked_paths": sorted(changed), "scope_status": "ok"})
PY
git status --short --untracked-files=all
```

Compare changed paths with this Plan's `Allowed Change Scope`, then run `.agent/skills/audit-plan-completion/SKILL.md` from an independent agent/session. Completion requires verdict `complete`; otherwise use `.agent/workflows/remediate-completion-audit.md` for only the reported findings.

## Stop Conditions

Stop and return to Design/Plan review if any condition occurs:

1. The Task 0 runtime predicate differs from the confirmed incident, the article is terminal/emitted, or required active-root health evidence is unavailable.
2. The marker cannot remain additive while preserving formal event, anchor, or schedule-revision identity.
3. A needed direct consumer requires a code edit outside the allowed implementation paths.
4. The patch weakens trusted-payload rejection, existing bounds, 24-hour max age, storage protection, attestation, watermark preservation, or any safety flag.
5. A scoped repair introduces failures in an unrelated module, or any full-repository tool proposes mutations outside scope.
6. A deployment attempt would require F bootstrap, a new root, manual live-file edits, a concurrent writer, 1.5G execution on VPS, generic recovery-D restart without the exact authority pair, or B-process resume after any C cutover attempt.

## Completion Boundary

This Plan proves a bounded liveness and provenance correction. It does **not** prove Binance will expose a trusted detail payload, that the Aug-17/Aug-18 article can still be captured, that any recovery evidence is clean/formal announcement evidence, or that there is alpha/tradability. Deployment and the one-shot active-root recovery require a separate user-approved decision after completion audit.
