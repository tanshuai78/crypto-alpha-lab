# Stage 1.5D Schedule Revision Producer and Stage 1.5F Formal Lineage Closure Corrective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` or `superpowers:executing-plans` task-by-task after this plan receives an `Approve` review verdict and explicit user authorization.

**Goal:** 修复 completion audit 发现的 formal v2 lineage、schedule revision producer、1.5F revision idempotency 与 readonly salvage 的未接线/非严格实现；建立可由真实 Stage 1.5D poll 调用、可在 1.5F/1.5G 验证的 fail-closed 闭环。任何失败均不得改变交易权限或阻止正常 launch collection。

**Architecture:** Part A 通过现有 state/accepted/reconcile writer 完成 source -> state -> accepted -> latest/completed 的严格 v2 hash lineage，并提供只读、真实输入驱动的 salvage audit。Part B 不新增 loop：在既有 Stage 1.5D `main()` poll 内将 listing pre-classifier 接入 detail retry scheduler；trusted detail 的 revision 只从已 durable 的 current-root index 或显式 manifest snapshot 做 L1/L2/L3 linking，并经现有 JSONL transport 传给 1.5F。1.5F 对新 contract 原样使用 producer semantic application id；1.5G 用同一 v2 lineage predicate 决定 blocker 与 formal count。

**Tech Stack:** Python 3、现有 `json` / `hashlib` / `pathlib`、pytest、Graphify、existing append-only JSONL storage。不得新增依赖、数据库或 generic framework。

## Global Constraints

- `RISK_LIVE_TRADING_ENABLED = False`；所有 trade/paper/live/execution/alpha 权限保持 `false`。
- 不增加私有 API、订单、余额、仓位、`src/execution` 或策略依赖。
- `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False` 是默认值；只有 `effective_producer_enabled` 的所有 prerequisite 都成立才可 formal emit。
- normal formal v2 launch row 不得因 revision candidate、snapshot 缺失、index failure 或 producer health 而停止写入。
- revision uncertainty、L4、orphan、ambiguous、invalid snapshot、collision、missing attestation 全部 diagnostic/blocked；绝不 formal emit。
- 不修改既有 server/local 1.5D/1.5F root。offline salvage 只读已有 JSONL，输出独立 audit report；不提交运行时数据。
- 禁止 `ruff check --fix .`、全库 formatter、`git clean`、`git reset`、`git checkout --`、未限定删除、隐式扫描任意 `data/` root。
- 本计划不能证明所有 Binance revision 文案都可识别；只证明本设计规定的 transport/consumer fail-closed 行为。
- 本文件替代先前未通过 completion audit 的执行结果；所有 Task 必须重新执行 RED-GREEN 与 production-wiring verification，既有 helper、fixture、测试或 summary 字段不得作为完成证据。
- `schedule_revision_producer_supported` 仅表示 build capability。它不得由 import 或 helper existence 推导为 runtime health；只有 actual poll integration、consumer attestation 与 prerequisite 全部为真时才可 `effective_enabled`。
- 当前未跟踪的 `docs/reviews/2026-08-07-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md` 不属于本计划范围，不得提交或作为测试输出。测试必须使用 `tmp_path`；该既有路径由用户另行决定保留或删除。

## Allowed Change Scope

### Allowed Implementation Paths

- `configs/base.py`
- `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`
- `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
- `src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py` (new)
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py`
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`

### Allowed Verification Paths

- `tests/fixtures/external_signal_shadow/stage1_5d/schedule_revision_producer/**` (new, bounded fixtures only)
- `tests/fixtures/external_signal_shadow/stage1_5f/ko_rddt_formal_v2_lineage/**` (new, bounded fixtures only)
- `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py`
- `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`
- `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- `tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py` (new)
- `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- `tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py`

### Allowed Documentation Paths

- `docs/designs/2026-08-04-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-rules-design_CN.md`
- `docs/plans/2026-08-07-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-and-1-5f-lineage-closure-implementation-plan_CN.md`
- `docs/reviews/2026-08-07-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-deployment-checklist_CN.md` (new)

### Allowed Generated Or Runtime Paths

- `data/external_signal_shadow/stage1_5g/reviews/ko_rddt_lineage_salvage_*/**` (generated, never committed)
- `data/external_signal_shadow/stage1_5d/*_schedule_revision_producer_hotfix/**` (generated, never committed)
- `data/external_signal_shadow/stage1_5f/*_schedule_revision_producer_hotfix/**` (generated, never committed)
- `graphify-out/**` only after one final `graphify update . --code-only`; keep generated changes unstaged unless explicit project policy requires otherwise.

### Affected But Unchanged

- `src/research/external_signal_shadow/stage1_5_launch_event_contract.py`: shared exports remain compatible; test existing v1/v2 paths.
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py`: existing append-only writer remains the single 1.5F writer.
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`: summary continues deriving from persisted state; no separate summary schema is introduced for salvage.

### Forbidden

- Any path outside this whitelist.
- Route C1, liquidation, extreme funding, strategy, risk-limit, execution, and unrelated historical scripts.
- Runtime artifact commits, old-root rewrite, accepted/state/snapshot/watermark mutation, broad autofix, destructive cleanup, implicit cross-root scanning, or new threshold outside `configs/base.py`.

## Invariant Mapping

| ID | Required behavior | Tasks |
| --- | --- | --- |
| `INV-C1` | formal v2 hash lineage stays consistent from source through 1.5G | 2-4 |
| `INV-C2` | salvage is readonly/nonproduction and cannot upgrade evidence | 5 |
| `INV-P1` | only mandatory-detail L1/L2/L3 revisions emit | 6-9 |
| `INV-P2` | same-poll launch is linkable only after event/index durability | 8-9 |
| `INV-P3` | cross-root index is explicit, manifest-verified, point-in-time safe | 7 |
| `INV-P4` | payload-version first-observed time is durable across restart | 6 |
| `INV-P5` | revision semantic/application/id equality and conflict transport | 6, 10 |
| `INV-P6` | valid late equal-time conflict is transported and fail-closed by 1.5F | 9, 10 |
| `INV-P7` | new v2 revision transport is strict; only v1 artifact may use legacy id fallback | 6, 10 |
| `INV-S1` | prerequisite attestation gates effective enablement | 11 |
| `INV-W1` | producer helper is called by the real 1.5D poll and produces either durable formal rows or durable diagnostics | 7-9, 11 |

---

## Part A: Consumer Prerequisite Closure

### Task 1: Freeze bounded evidence fixtures and baseline provenance

**Files:** Create only the two fixture directories in Allowed Change Scope.

- [ ] Record `BASE_SHA`, pre-existing dirty/untracked paths and their ownership. Never revert them.
- [ ] Add a minimal KO/RDDT extract from article `307687ad279e42e6909ee1be8c472b50`, retaining event id, both symbols, source article, v2 contract fields, per-symbol source hash and official anchor fields. Metadata must record source root id, source-row SHA-256, fixture SHA-256 and `data_quality = server_observed_formal_v2_event_row`.
- [ ] Add AIA article `a9f0566c85b54e30a63f1092e45d61f7` metadata. Add its raw BAPI fixture only if the original raw payload is available; otherwise declare `missing_real_fixture` and `producer_enablement_blocker = true`. Synthetic fixture never clears this blocker.
- [ ] Add small synthetic fixtures for L1/L2/L3/L4, cancelled, all-symbol failure, in-place edit, restart replay, late equal-time conflict, snapshot collision and pre-classifier false positives.
- [ ] Add metadata hash tests. Do not add a runtime root or broad server export to Git.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py -q
```

### Task 2: Preserve complete v2 lineage and schema version in 1.5F state

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

- [ ] Write failing tests that create a KO state from the frozen v2 event, move it pending -> active -> completed, serialize/reload, then assert these exact fields survive: `source_article_id`, `source_detail_url_normalized`, `source_published_at_ms`, `formal_event_contract_version`, `formal_event_consumable_by_stage1_5f`, `source_contract_status`, `symbol_identity_validation_status`, `launch_anchor_evidence_level`, `latest_anchor_evidence_level`, `effective_observation_anchor_source`, `launch_anchor_validation_status`, `source_anchor_contract_hash`, `admission_anchor_contract_hash`, `latest_anchor_contract_hash`, `anchor_contract_version`, `anchor_precedence_policy`, `admission_max_evidence_class`, `latest_max_evidence_class`, and `observation_anchor_revision_contaminated`.
- [ ] Write controls: a same-symbol/different-article re-resolution cannot overwrite lineage; a legacy pre-version state still loads; a new v2 state declared with missing required lineage is recognized as incomplete.
- [ ] Add only defaulted scalar fields plus `observer_state_schema_version`; retain existing `from_dict()` unknown-field filtering. Copy event immutable fields at pending creation and refresh only from exact matching event identity during re-resolution.
- [ ] Do not create a new state class, migration framework, observation window or snapshot policy.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py -q
```

### Task 3: Preserve identical lineage in accepted and crash-reconcile rows

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

- [ ] Write failing tests for `build_accepted_row_from_state()` asserting every Task 2 lineage field is emitted.
- [ ] Write a crash test: persist state, simulate failure before accepted append, restart through existing `reconcile_missing_accepted_rows()`, and assert reconstructed accepted row is byte-equivalent on lineage fields to normal admission.
- [ ] Make the existing shared accepted-row builder the only place that maps state lineage to accepted rows; both normal and reconcile paths must call it.
- [ ] Do not modify event identity, watermark rules, evidence-label selection or snapshots.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py -k 'lineage or reconcile' -q
```

### Task 4: Make 1.5G formal recognition a strict v2 lineage gate

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

- [ ] Write parameterized RED cases that remove or mismatch exactly one of: accepted v2 version, latest v2 anchor version, shared `official_schedule_priority_v1` policy, source hash, admission hash, official source/evidence fields, latest evidence class, non-contamination, and completed/latest hash. Each case must assert blocker `formal_v2_lineage_incomplete_or_mismatch` and formal count `0`.
- [ ] Extract one private predicate used by both blocker creation and formal counting. Its inputs are accepted row, latest state, optional completed state; it returns `(valid: bool, reason: str | None)`. It must reject an empty hash as well as unequal hashes. It must not use any legacy fallback once either input declares v2.
- [ ] Preserve existing legacy behavior only when neither accepted nor state declares v2. Add a KO/RDDT completed-snapshot regression that proves no fixture or reviewer code changes its original evidence label.
- [ ] Do not implement producer attestation in this task; Task 11 is its sole owner.

**Verification gate:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py -q
```

If this suite fails, stop. Keep effective producer emission false and do not proceed to Part B runtime enablement.

### Task 5: Add an explicit readonly KO/RDDT offline salvage audit procedure

**Files:**
- Modify: `docs/reviews/2026-08-07-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-deployment-checklist_CN.md`
- Generated only: `data/external_signal_shadow/stage1_5g/reviews/ko_rddt_lineage_salvage_*/**`

- [ ] Document one bounded local-only `PYTHONPATH=src:. .venv/bin/python - <<'PY'` command taking three explicit environment variables: `STAGE1_5D_EVENTS_GLOB`, `STAGE1_5F_ACCEPTED_GLOB`, and `STAGE1_5F_STATE_GLOB`. It must fail before writing output if any variable is empty, glob has zero files, or an input is outside the operator-selected local root.
- [ ] The command reads JSONL, selects only article `307687ad279e42e6909ee1be8c472b50` and KOUSDT/RDDTUSDT, and requires exactly one 1.5D source row, one accepted row and one latest state per `(event_id, symbol)`. It validates source contract, article id, formal version, policy and source/admission hashes. Duplicate, missing or unequal inputs are `failed`, never pass.
- [ ] It writes only `formal_lineage_salvage_manifest.json` and a short audit report under `ko_rddt_lineage_salvage_*`; record every input file SHA-256, each selected row canonical SHA-256, path, line number, timestamp, `salvage_mode = readonly_lineage_reconciliation`, and `nonproduction_audit_only = true`.
- [ ] It must never copy or modify a 1.5F root, produce an overlay, call the 1.5G production reviewer on modified input, change labels/counts/clean pass, or claim a production formal result.
- [ ] Its only decisions are `stage1_5g_formal_lineage_salvage_audit_pass` and `stage1_5g_formal_lineage_salvage_audit_failed`.

**Verification:** use a tmp-path fixture with matching rows and one each of missing state, duplicate accepted row and mismatched hash. `shasum -a 256` each source input before and after; hashes must match exactly. A command which does not read all three real input classes is a failure.

---

## Part B: Schedule Revision Producer

### Task 6: Make revision contract identity, payload time and config explicit

**Files:**
- Modify: `configs/base.py`
- Modify: `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

- [ ] Add RED contract tests proving the producer emits `formal_schedule_revision_contract_version = 2`; reject missing or unequal `revision_id`, `revision_semantic_id`, and `revision_application_id`; reject missing `revision_payload_version_id` or `revision_observation_id`, placeholder/default payload hash, and invalid status/anchor combinations; cover an in-place payload edit after restart.
- [ ] Add `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_LOOKBACK_DAYS = 14`, default disabled producer flag, prerequisite commit SHA, prerequisite suite-passed flag and real-fixture-verified flag. No `getattr(..., default)` or hidden runtime fallback is allowed.
- [ ] Make `build_formal_schedule_revision_row()` emit only version 2 and require all producer-confirmed identity fields as non-default keyword-only arguments. It must reject `link_status != linked`, reject unsupported intent/status, and never synthesize an id or substitute `default_hash`. `validate_schedule_revision_contract()` must enforce the v2 contract at the transport boundary while preserving a bounded read-only validator path for version 1 legacy artifacts.
- [ ] Update the 1.5D runtime contract and 1.5F observer-root contract to declare supported/allowed schedule-revision versions `[1, 2]`. This is compatibility metadata only; producer output is v2 exclusively.
- [ ] Add an append-only current-root payload-version registry keyed by `(source_article_id, raw_payload_sha256)`, with `payload_version_first_observed_at_ms`. Restart loads the first value unchanged; `revision_available_at_ms` is exactly that value, never publication time or current time.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -k 'schedule_revision or payload_version' -q
```

### Task 7: Add pre-detail scheduling and curated cross-root identity snapshots

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

- [ ] Write runner-level RED tests: a bounded AIA-style listing cue creates an existing scheduler work item with `detail_work_type = launch_schedule_revision_detail`; plain launch, API maintenance and funding/settlement delays create none; this scheduling step writes neither a revision event nor a revision formal row.
- [ ] Wire the pre-classifier into `run_stage1_5d_live_event_source_smoke_collector.py:main()` at listing ingestion, before `select_detail_retry_attempts()`. Reuse the existing detail retry state and per-article retry ceiling; do not add a second queue or poll loop.
- [ ] At trusted BAPI detail completion in the same `main()` path, invoke detail classification, payload-version lookup and linking. The runner, not a standalone test, must call `emit_schedule_revision_batch()` and pass every returned row to `append_formal_schedule_revision()`; non-linked/ambiguous/invalid results must use `append_stage1_5d_diagnostic()`.
- [ ] Add formal launch index rows only after `record_formal_futures_launch_event()` has appended the launch row. Populate actual append completion time as `formal_row_durable_at_ms`; never substitute publication time. Add the full v2 index schema fields from Design Section 8.1.
- [ ] Add `--formal-launch-identity-index-snapshot <path>` as the sole cross-root input. Verify manifest schema, content SHA, source roots and commit SHAs before merging with current-root rows; never scan historical roots automatically.
- [ ] Detect the three specified identity collisions. Any collision emits `index_collision`, blocks revision emission and records health/counter but normal launch continues. Link only L1/L2/L3 and require both observed and durable index times no later than `revision_available_at_ms`.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py -q
```

### Task 8: Enforce durable poll ordering and rebuild missing index state

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

- [ ] Write runner-level RED tests: revision cannot link a same-poll launch before both stream writes complete; crash before launch append emits no dependent revision; crash after launch append/before index append rebuilds the index on restart; and actual `events/*.jsonl` contains launch before dependent revision.
- [ ] Make `record_formal_futures_launch_event()` return only after launch event append and every corresponding index append succeeds. If index append fails after launch append, leave a recoverable gap diagnostic and do not expose the launch in the producer index until restart rebuild verifies it.
- [ ] At poll start, rebuild only missing current-root identity rows from validator-approved persisted launch events, then merge an explicit valid snapshot. Do not expose validated-only in-memory candidates or scheduler state to the linker. Application durability means successful append and close, not a power-loss guarantee.
- [ ] Add a test with no producer helper monkeypatch: run the real poll fixture through listing, detail, launch/index persistence and revision processing, then assert the formal revision transport row or its expected durable diagnostic.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -k 'revision and (durable or crash or same_poll)' -q
```

### Task 9: Implement batch emission and late-conflict transport

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

- [ ] Add runner-level RED tests for exact-all-symbol statement failure: simulate one invalid/unlinked symbol, read the actual stream written by the runner, and assert zero formal revision rows for that batch plus one terminal diagnostic. Do not assert an in-memory variable only.
- [ ] Add restart test: after one per-symbol row is durably appended, restart rebuilds emitted semantic ids from the event stream and appends only missing rows.
- [ ] Add late-conflict test: A is emitted, B is independently valid/linked/point-in-time valid but same identity/time with different status/anchor; the real 1.5D runner must append B and a late-conflict diagnostic/counter, not suppress it.
- [ ] Persist only batch identity, expected/link result sets, emitted semantic/observation IDs and status. Rebuild from event stream after crash. Counters must be sample-capped for candidate/detail pending/link emit/diagnostics/payload variant/collision/late conflict. A blocked producer changes no normal launch result.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -k 'revision and (batch or conflict or gate or restart)' -q
```

### Task 10: Make 1.5F apply semantic revisions and fail closed on cancellation/conflict

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

- [ ] Write failing tests: v2 contract consumes the exact transport `revision_application_id` rather than recomputing from payload hash; same semantics/payload variant is no-op; malformed v2 is blocked; v1 legacy artifact still uses legacy fallback; cancelled maps pending to `pending_cancelled`; active/completed become contaminated; late equal-time B reaches `pending_official_schedule_conflict` or contaminated state.
- [ ] Branch on `formal_schedule_revision_contract_version`: v2 must validate and use producer `revision_application_id` verbatim; v1 is the only legacy fallback path. Update the observer-root revision-version allow-list to `[1, 2]`. A declared v2 row lacking an id is blocked, not downgraded.
- [ ] Reuse `apply_anchor_contract_revision_to_state()` to implement status-specific transitions. Active collection remains read-only to its original window end; it is not stopped or reopened.
- [ ] Verify registry/state restart preserves conflict and contamination outcome.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -k 'revision or cancelled or conflict or contaminated' -q
```

### Task 11: Runtime attestation, deployment checklist and completion audit

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `docs/reviews/2026-08-07-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-deployment-checklist_CN.md`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

- [ ] Write runner-level RED tests proving runtime-gate context is computed from actual integration results: `supported` means the producer path is present, `configured enabled` means the config flag, `consumer prerequisites verified` requires current commit match + recorded Part A suite evidence + verified real AIA fixture, and `effective enabled` additionally requires current-poll producer integration health `ready`. Missing context may only result in `false`/`blocked`, never an optimistic default.
- [ ] Implement one pure attestation helper called by the Stage 1.5D runner before `build_stage1_5d_runtime_gate()`. Pass its explicit result into the gate context. `stage1_5d_runtime_gate.py` remains a serializer and must not invent attestation from `ctx.get()` defaults.
- [ ] Write the checklist: deploy with producer configured false; use unescaped `events/*.jsonl`; require explicit snapshot manifest for cross-root coverage; inspect health/effective enablement; prohibit enablement by tests alone. The checklist must state that normal launch collection continues when producer health is blocked.
- [ ] Verify the 1.5D runtime summary and 1.5F observer-root contract both expose schedule-revision versions `[1, 2]`, while the 1.5D producer reports v2 only when it emits a row.
- [ ] Replace the existing placeholder salvage block with the Task 5 command. It must require the three explicit input globs and print input/row hashes plus `nonproduction_audit_only = true`; do not hard-code a pass decision.
- [ ] Run the complete bounded suite:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py -q

git diff --check "$BASE_SHA"
git diff --cached --check "$BASE_SHA"
git diff --check
```

- [ ] Run exactly one post-code topology refresh and targeted query:

```bash
.venv/bin/python -m graphify update . --code-only
.venv/bin/python -m graphify query "build_formal_schedule_revision_row"
.venv/bin/python -m graphify query "validate_schedule_revision_contract"
.venv/bin/python -m graphify query "build_accepted_row_from_state"
.venv/bin/python -m graphify query "process_schedule_revision_event"
.venv/bin/python -m graphify path "process_schedule_revision_event" "apply_anchor_contract_revision_to_state"
rg -n "revision_application_id|revision_available_at_ms|payload_version_first_observed_at_ms|source_anchor_contract_hash|formal_v2_lineage_incomplete_or_mismatch" \
  src/research/external_signal_shadow scripts/external_signal_shadow tests/research/external_signal_shadow tests/scripts/external_signal_shadow
```

- [ ] Run `git diff --name-status "$BASE_SHA"`, `git diff --cached --name-status "$BASE_SHA"`, `git status --short --untracked-files=all`, and `git ls-files --others --exclude-standard`. The known out-of-scope generated 1.5G review must not be committed; preserve it until the user decides its disposition.
- [ ] Hand off an execution report to an independent `.agent/skills/audit-plan-completion` run. Required verdict: `complete` before any deployment/completion claim.

## Plan Self-Review

- All completion-audit P0 findings map to a runtime-tested task: strict lineage (2-4), real readonly salvage (5), complete IDs/payload time (6), actual scheduler/runner producer wiring and snapshot (7), durable ordering (8), stream-backed batch/late conflict transport (9), semantic 1.5F consumption (10), and computed attestation (11).
- Ponytail: reuse existing state, JSONL, contract validator, registry and runner paths. One new producer module is justified because parsing/linking/index semantics are a distinct producer concern. No dependency, DB, interface/factory or generic framework is introduced.
- Graphify: use existing graph only as advisory during planning; post-code update is AST-only/code-only and paths are in generated scope.
- A missing real AIA payload is an enablement blocker, not a reason to fabricate fixture proof or block normal launch collection.

## Execution Handoff

This plan requires independent `reviewing-implementation-plans` approval and explicit user authorization before source changes. Execution then follows `.agent/workflows/execute-approved-plan.md` with a frozen plan SHA and scope baseline.
