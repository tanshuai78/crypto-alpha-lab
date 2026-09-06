# Stage 1.6E-B Completion Remediation Implementation Plan

> **For implementation agents:** Execute only after an `Approve` Plan-review verdict, explicit user implementation authorization, and exact external Plan-byte authorization. Use the project `execute-approved-plan` workflow task by task.

**Goal:** Repair only the approved Stage 1.6E-B completion-audit authority and recovery defects while preserving the Parent E-B Design behavior and all public-read-only safety boundaries.

**Architecture:** Reuse the existing 1.6D committed checkpoint grammar, frozen E-A Step-A helper, E-A complete-bundle verifier, and Parent E-B persistence model. The remediation adds no schema, transport, policy, or runtime capability: it makes the existing source lineage, per-root gate, verified ProfileCore, and C5/C6/C8/C9 paths fail closed as already approved.

**Tech stack:** Python standard library, existing project serializers/verifiers, `pytest`, and `ruff`.

## Plan Status And Authority

- 日期: 2026-09-05
- Plan status: `draft_for_review`
- Parent Design SHA-256: `752aecff8735f22513483e6bf65ae991386f46ff2ae953da44cd1fe9c5898583`
- Parent Plan SHA-256: `279f729645c9e3691797a92059cab3d212e7b62c0ffbdb49a49947bb712b4da6`
- Approved Remediation Delta Design SHA-256: `145bbb7d84e4d7ae4fc9e901b293b8520b3b825d1377f96d02bff8b8dc67ee44`
- Completion-audit input: `docs/reviews/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-completion-audit_CN.md`
- `implementation_allowed=false`
- `deployment_allowed=false`
- `runtime_action_allowed=false`

本 Plan 只修复 Parent Design/Plan 已要求且 Approved Remediation Delta 明确列出的 completion defects。它不重新设计 Parent E-B，不修改三份已绑定 authority 文档，也不构成实现、部署、root 创建、source read 或网络请求授权。

执行开始前，外部审批记录必须提供 `EXPECTED_APPROVED_REMEDIATION_PLAN_SHA256`。执行者计算本文件 exact bytes SHA-256；不相等即 `STOP = remediation_plan_bytes_not_authorized`。该值不得由本 Plan 自行填写或推断。

## Remediation Boundary

```text
validated E-A complete bundle
-> fresh Step-A projection for each fresh-root gate
-> exact 1.6D committed revision-observation-raw linkage
-> E-B durable projection/admission
-> deterministic event-root recovery
-> existing Parent E-B slot/terminal/manifest lifecycle
```

不改变 12 小时 window、三 symbol 上限、single-active-event policy、G2 parsing、E-A profile schema、1.6D writer/checkpoint grammar、public REST client 或任何 permissions。所有 E-B permissions 与 `RISK_LIVE_TRADING_ENABLED` 保持 `False`。

## Allowed Change Scope

Allowed implementation paths:
- `configs/base.py`
  - 仅删除当前 E-B config block 后导致 `git diff --check` 失败的 EOF 空白行；22 个既批准 assignment、AST、值和既有 schedule-revision allowlist 不得变化。
- `scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py`
- `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_source.py`
- `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_storage.py`
- `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py`
- `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py`
- `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py`

Allowed documentation paths:
- `none`
  - independent `audit-plan-completion` verdict is external read-only evidence for this Plan; it must not be created or changed after audit within the audited worktree.

Allowed generated/runtime artifacts:
- `pytest` `tmp_path` only; never committed.
- `none` for deployment/runtime roots. This Plan does not authorize `data/external_signal_shadow/stage1_6e_b/**` creation.

Affected but unchanged:
- `docs/designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md`
  - SHA-256 equality against bound Parent Design value.
- `docs/plans/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-implementation-plan_CN.md`
  - SHA-256 equality against bound Parent Plan value.
- `docs/designs/2026-09-04-external-signal-shadow-lab-stage1-6e-b-completion-remediation-delta-design_CN.md`
  - SHA-256 equality against bound Delta value.
- `scripts/external_signal_shadow/run_stage1_6e_a_market_data_capability_audit.py`
  - E-B runner calls only its existing `get_vps_step_a_projection`; E-B `src/` must not import this runner.
- `src/research/external_signal_shadow/stage1_6e_a_market_data_capability_{models,storage,client}.py`
  - exact E-A complete-bundle/profile fixtures and upstream regression pass.
- `src/research/external_signal_shadow/stage1_6b_canonical_source_{models,storage,observer,client}.py`
  - canonical 1.6D test producer and upstream regression pass; no writer mutation.
- `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py`
  - G2 regression pass; no grammar change.
- `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_{models,client}.py`
  - exact existing schema/client regression passes; no model or transport extension.
- `src/research/external_signal_shadow/stage1_5_storage_guard.py`
  - shared guard regression passes; no shared storage policy change.

Forbidden:
- Any mutation outside the allowed paths.
- Parent Design/Plan/Delta mutation, E-A/1.6D/G2/Stage 1.5 source mutation, schema-version change, migration, repair-in-place, adapter, fallback, replay/backfill, retry, queue, concurrency, second window or capacity-policy change.
- New configuration threshold, renamed assignment, schedule-revision allowlist mutation, broad formatter/refactor or `ruff check --fix`.
- Private/authenticated/account/order API, trade signal, alpha/PnL/cost claim, paper/live trading, execution engine, runtime session, VPS synchronization or real network test.
- `git clean`, `git reset --hard`, destructive checkout, or overwriting pre-existing dirty/untracked files.

## Preflight Contract And Impact Map

| Delta invariant | Production entry point | Persistent/consumer edge | Task | Mechanical proof | Fail-closed STOP |
|---|---|---|---:|---|---|
| `INV-R01` exact 1.6D linkage | `Stage16EBSourceConsumer` and `Stage16EBSupervisor.step_source_stream` | complete checkpoint map -> exact daily observation stream -> revision -> physical raw | 1, 2 | canonical 1.6D producer fixture; every committed-stream boundary plus exact raw path/hash and zero/multiple linkage tests | `source_checkpoint_invalid` or `source_structural_failure/orphan_or_ambiguous_live_revision` |
| `INV-R02` bootstrap | `step_source_stream` | current committed boundary -> E-B consumer checkpoint | 2 | nonzero boundary yields only read-back checkpoint | bootstrap replay or any raw/projection/admission/request |
| `INV-R03` fresh-root environment | E-B runner + storage gate | exact E-A Manifest -> gate-local Step-A -> root device | 3 | supervisor and C5 event-root pre/post mismatch tests | `environment_attestation_failed` before root; partial/non-consumable root after root |
| `INV-R04` independent E-B attestation | runner + storage + supervisor | exact E-A manifest/attestation + Step-A/root state -> E-B attestation -> exact receipt | 3 | field-provenance/read-back SHA/receipt-schema tests; copied E-A bytes reject | copied E-A bytes, unauthorized commit, manifest/receipt mismatch |
| `INV-R05` C5/C6 ownership | runner -> supervisor recovery | durable admission -> gate-local root initialization or controlled resume -> active checkpoint | 3, 4 | exact runner handoff, deterministic root, controlled-resume and checkpoint-only recovery fixtures | `global_active_supervisor_state_invalid` |
| `INV-R06` terminal capacity | supervisor recovery + storage lock | terminal/manifest/existing immutable writer lock -> active checkpoint | 5 | C8/C9 and failed-terminal writer-held/released/missing-lock fixtures | retained active fields, zero admission/root/HTTP |
| `INV-R07` immutable event time | C5/C6 recovery | projection -> event contract | 4, 5 | restart exact `semantic_projected_at_ms`/window equality | recomputed time or new event branch |
| `INV-R08` safety | runner + scope proof | config/permissions -> all E-B paths | 0, 6 | false-permission/risk static assertions | any true permission or execution import |
| `INV-R09` E-A profile authority | storage -> supervisor event initialization | verified E-A files -> derived event ProfileCore | 3, 4 | canonical E-A bundle fixture and mutation/fake-SHA tests | missing/mutated/wrong binding/static fallback |

Graphify is unavailable in this workspace (`.venv/bin/python -m graphify` has no module; available `graphify` output is unrelated/stale). Task 0 records this as advisory unavailable. The verified source impact set is therefore established by direct imports/calls and `rg`: E-B runner calls `validate_e_a_runtime_gate`, E-B storage calls `verify_complete_bundle`, E-B source calls `compute_live_v3_checkpoint_id`, and supervisor currently owns projection/admission/event-root creation. No unverified consumer may be modified.

## Mandatory Execution Governance Gates

### Pre-RED Contract Reality Gate

Before writing RED tests for any cross-boundary consumption in Tasks 1, 3, or 4, the executor must perform `execute-approved-plan` Step 3.0 against the real upstream SSOT: authoritative model/dataclass, canonical serializer, strict loader/verifier, canonical producer/generator, exact field names/types/enums/null behavior, path grammar, and hash/identity semantics. Record externally that the check was performed, inspected surfaces, and observed field/type result.

If the approved expectation and frozen upstream contract differ, do not invent fields, aliases, `.get()` defaults, hashes, fixtures, copied bytes, or compatibility fallback. Classify exactly once:

- `BLOCKED_IMPLEMENTATION_DEFECT`: the approved Design/Plan and upstream contract agree; current implementation is wrong and may be corrected within this approved scope.
- `BLOCKED_SCOPE_DRIFT`: the correct implementation requires a path outside Allowed Change Scope; stop and request a scope/Plan revision.
- `BLOCKED_SPEC_DRIFT`: the approved Design/Plan structurally contradicts the frozen upstream contract; stop and return to Design/Plan delta review.

### Per-Task Anti-Shortcut Gate

Each implementation Task 1-5 is additionally subject to the `execute-approved-plan` mandatory AST differential scanner gate. A Task is not GREEN until:

```bash
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
```

returns exit code `0`, scanner SHA-256/version and command are recorded, `ERROR` count is zero, and every `WARNING` has an explicit external Scanner Disposition Ledger entry showing why it does not weaken a strict contract. An undispositioned warning makes the Task incomplete even when the scanner exits `0`.

### Blind-First Independent Completion Audit

The implementation executor must not audit its own completion. After the final worktree is frozen, the executor gives an independent read-only auditor only a factual handover packet: bound Parent/Delta/Plan paths and SHA-256 values, `BASE_SHA`, pre-execution dirty-worktree evidence, Allowed Change Scope, known unresolved blockers if any, and verification commands. The initial handover must not assert completion, test success, invariant satisfaction, merge readiness, or an absence of findings.

The auditor may be an independent subagent, independent session, user, or other independent reviewer; this Plan does not bind a specific IDE/tool implementation. The auditor independently inspects the worktree/index/untracked files, upstream bytes, production call paths, test and scanner evidence, and negative probes before reading any executor explanation. The auditor is read-only: it must not fix code/tests, repair the worktree, or generate favorable evidence. `incomplete` or `blocked` returns to a separate remediation flow. Record auditor identity/session, read-only boundary, final-worktree freeze, factual handover packet, and verdict as external completion evidence; do not mutate the audited worktree after verdict.

## Task 0: Authority, Baseline, And Dirty-Worktree Preflight

**Invariants:** all; especially `INV-R08`.

**Files:** none.

1. Record `BASE_SHA=$(git rev-parse HEAD)`, exact `git status --short --untracked-files=all`, and SHA-256 of every pre-existing dirty/untracked file. Preserve the existing E-B implementation and its parent artifacts as provenance; do not revert, delete, stage, or overwrite unrelated bytes.
2. Compute and require exact equality for the three bound SHA-256 values and the externally supplied `EXPECTED_APPROVED_REMEDIATION_PLAN_SHA256`.
3. Record targeted source evidence for `get_vps_step_a_projection`, `verify_complete_bundle`, `compute_live_v3_checkpoint_id`, `Stage16EBSupervisor.step_source_stream`, `initialize_event_root`, and `RootWriterLock`. Graphify unavailability is recorded, not bypassed.
4. Parse `configs/base.py` AST against the Task-0 snapshot. The only permitted semantic E-B config delta remains exactly the pre-existing 22 assignment block from Parent Plan Task 1. Record the current EOF-whitespace finding as the sole authorized textual cleanup.
5. Confirm all permissions are false and record no root/session/client construction occurred.

**Verification:**

```bash
BASE_SHA="$(git rev-parse HEAD)"
git status --short --untracked-files=all
shasum -a 256 \
  docs/designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md \
  docs/plans/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-implementation-plan_CN.md \
  docs/designs/2026-09-04-external-signal-shadow-lab-stage1-6e-b-completion-remediation-delta-design_CN.md \
  docs/plans/2026-09-05-external-signal-shadow-lab-stage1-6e-b-completion-remediation-implementation-plan_CN.md
```

**Expected:** all four authority checks match their approved/external values; pre-existing dirty paths are recorded; no process/runtime artifact is created.

**STOP:** missing external Plan SHA; parent/Delta hash mismatch; unrecorded dirty path; required upstream modification; Plan needs a new artifact/schema/permission/threshold.

**Out of scope:** implementation, config semantic changes, test relaxation, deployment.

## Task 1: Exact Committed 1.6D Linkage

**Invariants:** `INV-R01`.

**Files:**
- Modify `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_source.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py`

**RED:** first complete the Pre-RED Contract Reality Gate. Then create positive fixtures only by running the canonical 1.6D observer/serializer in `tmp_path` with an injected local opener; do not handcraft cross-boundary checkpoint, revision, observation, raw or profile-attestation dictionaries. Mutate exactly one generated fact for each negative case: an unrelated checkpoint-declared committed stream missing/corrupt, selected stream map/boundary/hash failure, raw file missing, raw symlink, or raw-byte SHA mismatch.

**Implementation:**

1. Before reading any revision, validate the current complete V3 checkpoint with 1.6D's existing checkpoint-ID computation and validate **every** declared stream in its exact `stream_offsets`/`stream_last_hashes` maps. The maps must have the upstream-recognized exact relative-path grammar and mutually consistent keys. For every positive offset: resolve only under the authorized source root; require an existing regular non-symlink file; require an exact line-boundary offset; hash the final committed line below that offset; and equal the declared last hash. For a zero offset, enforce the upstream zero-boundary grammar and never invent a file/hash. Parse no bytes until the full map passes.
2. Derive exactly one observation stream key with `datetime.fromtimestamp(revision.captured_at_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")`; require that exact key in both already-validated maps with a positive offset. Parse only its committed `[0, offset)` bytes. Do not glob, enumerate directory roots, prefix-match, infer another date, read an uncommitted tail or fall back to another stream.
3. Filter the committed daily stream to trusted linkage candidates matching live mode, exact 1.6D source profile, exact BAPI detail request variant, authorized run ID, article ID, raw SHA and raw relative path. If candidate cardinality is zero or multiple, fail as `source_structural_failure/orphan_or_ambiguous_live_revision` before resolving, selecting or inspecting any physical raw path. If it is exactly one, obtain request observation ID only from that observation and trusted time only from the revision.
4. Only for the unique trusted observation, resolve its exact normalized root-relative raw path under the authorized source root. Require an existing regular non-symlink raw file, read its exact bytes, and require `SHA256(bytes) == revision.detail_raw_sha256 == observation.raw_payload_sha256` before accepting linkage, raw copy, projection, admission or checkpoint advance. A missing/symlink/path/hash contradiction of this uniquely linked raw is `source_raw_path_hash_or_profile_mismatch`.
5. Any complete-map/path/boundary/hash failure or invalid run/mode/profile/variant is `source_checkpoint_invalid`. The zero/multiple and uniquely linked raw-failure taxonomies above are distinct Parent source structural failures. Every failure classification performs zero raw copy/projection/admission/event/request and does not advance the E-B checkpoint.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py
```

**Expected:** every checkpoint-declared positive stream is verified before any revision is read; an unrelated missing/corrupt declared stream, selected wrong day/zero offset/hash/tail, and invalid profile/variant/run fail closed with zero consumer advance. A fully valid map reaches linkage cardinality first: zero/multiple candidates inspect no raw and use `source_structural_failure/orphan_or_ambiguous_live_revision`; only exactly-one linkage reaches physical raw validation, whose missing/symlink/path/hash contradiction uses `source_raw_path_hash_or_profile_mismatch`.

**STOP:** need to modify 1.6D schema/writer/checkpoint, use synthetic upstream positive bytes, or add a fallback/scan/replay path.

**Out of scope:** G2 parsing, root recovery, E-A environment checks.

## Task 2: Bootstrap And Source-to-Supervisor Handoff

**Invariants:** `INV-R01`, `INV-R02`.

**Files:**
- Modify `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py`

**RED:** use the Task-1 canonical 1.6D fixture to prove fresh bootstrap begins at the current durable `detail_revisions` boundary, including a nonzero offset and last-line hash/sequence.

**Implementation:**

1. Make first consumer checkpoint creation durable/read-back at the exact current 1.6D committed boundary, then return. It must not call raw read/copy, reducer/G2, projection/admission/event-root creation or public client construction.
2. On an existing valid E-B consumer checkpoint, consume only its verified suffix and pass validated revision-observation-raw linkage to the existing reducer.
3. Remove all fabricated provenance/default paths, including synthetic request/revision IDs, fake raw paths/hashes, alias `detail_revisions`, or source-root scans. `step_source_stream` may persist verified projections/admissions but must not create an event root or read E-A ProfileCore bytes.
4. Preserve Parent source-degraded behavior: no new admission while degraded; an already active event remains independently observable under Parent lifecycle rules.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py
```

**Expected:** bootstrap writes exactly one read-back consumer checkpoint and no other E-B artifact; suffix processing cannot fabricate provenance; no event root is created before Task 3 gate.

**STOP:** any historical replay, direct raw-to-client path, new durable artifact/schema, or need to alter G2/1.6D.

**Out of scope:** fresh-root environment validation and C5/C6 recovery.

## Task 3: Per-Root E-A Environment Gate And Profile Authority

**Invariants:** `INV-R03`, `INV-R04`, `INV-R09`.

**Files:**
- Modify `scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py`
- Modify `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_storage.py`
- Modify `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py`
- Modify `tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py`

**RED:** first complete the Pre-RED Contract Reality Gate. Then make E-A positive fixtures by invoking the canonical E-A audit/serializer with an injected local opener in `tmp_path`, then verify with the E-A complete-bundle verifier. Negative tests mutate exactly one verified file/field after construction.

**Implementation:**

1. The E-B runner derives `canonical_project_root = Path(__file__).resolve().parents[2]`, requires it to be a real project root, and requires `Path.cwd().resolve(strict=True) == canonical_project_root` when the process relies on its working directory. Only that composition root may import/call frozen `get_vps_step_a_projection(canonical_project_root)`. E-B `src/` modules must not import the E-A runner, invoke subprocess, copy its formula, or create a shared adapter. If that direct call is not side-effect-free, stop rather than relocate/copy it.
2. For supervisor fresh root and separately for every C5 deterministic fresh event root, call Step-A again. A supervisor projection must never authorize event-root creation.
3. Before each fresh root: run `verify_complete_bundle`, require exact E-A Manifest ID `e918b344b6781bbdb0cd005b3744acf3bb0d370e98ddd5c2973312dc974874b3`, read back the exact manifest bytes and require their SHA-256 to equal the verified manifest SHA, then validate the exact E-A environment attestation. Enforce pre-root host/project-root/netns/proxy/clean-worktree equality and parent/shared-lock device equality. Any pre-root failure creates no corresponding E-B root and does no source/client work.
4. Create the exact root only after pre-root success, acquire its writer lock, then enforce post-root device equality. A post-root mismatch leaves the root partial/non-consumable, writes neither E-B attestation nor receipt, performs no source/client work, and does not write a new `environment_attestation_failed` terminal reason.
5. Build/read-back E-B same-schema attestation from the gate-local projection plus current root state and separately authorized E-B deployment commit. Build/read-back `environment_authority_receipt.json` with the Parent's exact keys: `schema_version`, `root_kind`, `e_a_manifest_id`, `e_a_manifest_sha256`, `e_a_environment_attestation_sha256`, `e_b_execution_environment_attestation_sha256`, `permissions`, and `receipt_id`. Recompute `receipt_id` from canonical JSON with only `receipt_id` omitted; all three SHA-256 fields must hash their exact read-back files. Reject copied E-A bytes as E-B provenance; byte inequality itself is not an authority condition.
6. After successful `verify_complete_bundle`, load the four exact E-A profile and profile-attestation files from that E-A root. Validate their bytes/hashes against the verified manifest/attestations and pass them to event initialization. Do not use `PROFILE_CORES` static fallback, `SHA256(profile_id)`, a partial map or unverified manifest values.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py \
  tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_models.py \
  tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_a_market_data_capability_audit.py
```

**Expected:** supervisor and C5 both recompute Step-A. A different but internally valid E-A bundle, wrong E-A manifest ID/SHA, receipt missing manifest binding, or receipt with correct attestation SHA but wrong manifest SHA rejects before root/source/client authority. The negative sequence `supervisor P0 valid -> environment changes -> C5 P1 mismatch` yields zero event-root creation and zero event HTTP. Missing/mutated profile attestation, wrong binding, `SHA256(profile_id)` fake and absent E-A profile file with attempted static fallback all reject.

**STOP:** E-A code change, script import from E-B `src/`, copied projection formula, new schema/artifact, terminal vocabulary change, or any source/client operation before the applicable gate.

**Out of scope:** client transport changes, E-A profile contract changes, deployment authorization.

## Task 4: C5/C6 Deterministic Recovery And Event Provenance

**Invariants:** `INV-R05`, `INV-R07`, `INV-R09`.

**Files:**
- Modify `scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py`
- Modify `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py`
- Modify `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_storage.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py`
- Modify `tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py`

**RED:** first complete the Pre-RED Contract Reality Gate. Then start from a canonical durable admission/projection and canonical E-A authority fixture. Exercise both legal C5 sources: startup recovery before source polling from an existing durable admission, and current source processing after a newly durable admission. They must produce the same in-memory work item and runner path. Inject only the exact C5 or C6 persisted state; do not construct foreign profile/attestation bytes manually.

**Implementation:**

1. Freeze one in-memory `C5WorkItem` contract containing the exact durable projection, exact durable admission and deterministic event-root path; it creates no durable handoff artifact. There are exactly two producers: startup recovery before source polling finds an existing exact durable admission with missing root and null active fields; current source processing writes an exact new admission with missing root and null active fields. `step_source_stream(...)` only produces the latter; the supervisor recovery path only produces the former. Both return the same `C5WorkItem` to the runner. No callback, adapter, E-A-runner import in `src/`, or second C5 path is permitted.
2. The runner is the single C5 orchestration owner. For either `C5WorkItem`, it recomputes fresh Step-A, verifies exact E-A authority, performs PRE-ROOT equality, then invokes one dedicated supervisor root-creation operation as the only `mkdir(exist_ok=False)` owner. That operation creates the deterministic root exactly once and acquires/retains the event writer lock; it returns only the locked root for POST-ROOT equality. After POST-ROOT passes, the supervisor writes/read-backs E-B attestation, authority receipt, event contract, derived ProfileCores and initial event checkpoint, then atomically writes matching active fields. No slot/request authority exists earlier. The existing `initialize_event_root` must be refactored to one of these two single-owner phases; it must not perform a second root creation.
3. C5 accepts only one exact admitted row, deterministic missing event root, `active_notice_event_key == null`, and `active_event_id == null`. C6 accepts only one exact owned valid nonterminal deterministic root, `active_notice_event_key == null`, and `active_event_id == null`.
4. Before C6 checkpoint-only active recovery, perform the Parent controlled-resume validation: existing E-B environment attestation and authority receipt, current environment/network revalidation, global and event-writer-lock ownership, exact event contract, derived ProfileCore hashes, event checkpoint, source raw hashes, and terminal/manifest absence. Then set the same active fields checkpoint-only and do not recreate the root.
5. Preserve `event_window_started_at_ms == projection.semantic_projected_at_ms` exactly. No restart wall-clock input may change it.
6. Non-null active fields, wrong event ID, multiple roots, malformed/foreign root, invalid attestation/receipt, failed current environment/lock ownership, present terminal/manifest, or contract/projection mismatch preserves bytes and is `global_active_supervisor_state_invalid`, with zero HTTP.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py
```

**Expected:** startup-persisted C5 and new-admission C5 both return the same in-memory work item to the same runner gate; each performs `PRE -> root exactly once -> retained writer lock -> POST -> attestation/receipt -> contract/ProfileCore/checkpoint -> active IDs`. The runner is the only C5 orchestration owner. C6 completes Parent controlled-resume checks then writes only the active checkpoint. Non-null active fields, wrong attestation/receipt, changed environment, global/writer-lock failure, or terminal/manifest presence preserve root/admission/checkpoint bytes and make zero request.

**STOP:** duplicate root/admission, inferred root selection, time recomputation, root repair/migration, static ProfileCore fallback, or non-parent recovery state.

**Out of scope:** C8/C9 terminal decisions and slot WAL changes.

## Task 5: C8/C9 Capacity And Failed-Terminal Writer Ownership

**Invariants:** `INV-R06`, `INV-R07`.

**Files:**
- Modify `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py`
- Modify `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_storage.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py`
- Modify `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py`

**RED:** use existing terminal/manifest serializers and `RootWriterLock` only to create canonical event roots; inject exactly the C8, C9, valid-failed-writer-held and valid-failed-writer-stopped states. Add one mutation for a missing, symlink, or nonzero-byte event writer lock. A held-writer fixture must hold the same event lock in a separate descriptor/process-safe test arrangement.

**Implementation:**

1. Before capacity release, classify terminals using existing Parent schema only. C8 means terminal write/read-back failure, terminal absent because persistence failed, or malformed/invalid terminal; C9 means valid complete terminal with absent/invalid manifest. Both retain root and active fields.
2. Before a valid-failed terminal's stopped-writer probe, require the exact existing `.stage1_6e_b_event_writer.lock` to be a regular non-symlink zero-byte artifact within the event root. Add one storage-local non-creating probe helper only if needed: it must open that existing file without `O_CREAT`, `O_TRUNC`, replace, chmod, rename or write; verify the opened descriptor remains regular/zero-byte; take `LOCK_EX | LOCK_NB`; then unlock/close. It must never reuse `RootWriterLock.acquire()` for this probe because that method may create a missing file.
3. A valid failed terminal releases active fields only when manifest is absent and the non-creating exact event-writer probe succeeds after terminal validation. Release the probe lock without changing the lock artifact bytes or metadata.
4. A valid complete terminal releases only after closed-manifest validation. No path rewrites/reseals a manifest or resumes/reobserves a terminal root.
5. All other terminal/root ambiguity remains a global blocker. Do not add an environment terminal reason or alter Parent terminal enums.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py
```

**Expected:** C8/C9, held failed writer, and missing/symlink/nonzero writer-lock roots retain active capacity with zero new admission/root/HTTP and no lock repair. Only stopped valid-failed writer and complete+valid manifest release exactly once; lock bytes remain unchanged and the probe performs no create/replace/truncate/chmod/rename/write operation.

**STOP:** capacity release with held/missing/symlink/nonzero writer lock; probe implementation that can create or repair an artifact; manifest retry/reseal; terminal enum change; or any reissued event request.

**Out of scope:** event-slot retry/WAL redesign and new terminal states.

## Task 6: Scope Closure, Regression, And Independent Completion Audit

**Invariants:** `INV-R08` plus all previous proof edges.

**Files:**
- Modify `configs/base.py` only as permitted by Allowed Change Scope.

1. Remove only the known trailing EOF blank line from `configs/base.py`. Use a Python AST comparator against Task-0 snapshot to prove the 22 approved E-B assignments and all other AST nodes are unchanged. Never modify the pre-existing schedule-revision production attestation helper/allowlist.
2. Run focused E-B tests, unchanged 1.6D/E-A/G2/shared-guard regression tests, `ruff` only on allowed paths, `git diff --check`, and the mandatory anti-shortcut scanner with `--base-sha "$BASE_SHA"`. Record external scanner command, scanner SHA-256/version, exit code, ERROR count, WARNING count, and a per-warning Scanner Disposition Ledger. Nonzero scanner exit, any ERROR, or an undispositioned WARNING is `STOP` and prohibits completion.
3. Enforce scope proof: actual task-induced modified paths must be a subset of Allowed Change Scope; every actual changed path must be fully attributed/accounted, and every Plan-required deliverable that genuinely needs a change must exist. Record all pre-existing dirty/untracked path SHA-256 values before/after and never create a no-op diff merely to use an allowed path.
4. Static-check E-B allowed implementation paths for prohibited imports/tokens: E-A runner import outside the E-B runner, `PROFILE_CORES` fallback, `sha256_hex(profile_id.encode())`, fabricated `req_1`/`rev_1`, raw default/alias fallback, 1.6D writer mutation, async/thread/executor, retry/backoff, proxy/cookie/auth/account/order/execution/trading/replay/alpha/signal.
5. Freeze the final worktree, apply the Blind-First Independent Completion Audit handover, and invoke `.agent/skills/audit-plan-completion` through an independent read-only auditor. Record its identity/session, factual handover packet and verdict externally. Its independent read-only verdict is external evidence and must not be followed by a Plan-generated worktree mutation. A `complete` verdict still does not authorize commit, deployment or runtime.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py \
  tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_models.py \
  tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_storage.py \
  tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_client.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_a_market_data_capability_audit.py \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py
.venv/bin/ruff check \
  configs/base.py \
  scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py \
  src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py \
  src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_source.py \
  src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_storage.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py
git diff --check
shasum -a 256 .agent/tools/anti_shortcut_scan.py
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
```

**Expected:** all tests/static checks pass, config AST is unchanged except no EOF whitespace when that already-authorized textual cleanup is performed, actual task-induced paths are an attributed whitelist subset, no source mutation exists outside whitelist, scanner ERROR count is zero with every WARNING dispositioned, and independent audit is `complete` for the final worktree.

**STOP:** any test/regression/scope/AST/scanner/audit failure; any scanner WARNING without an explicit disposition; any new config semantic delta; an attempt to update Parent authority; any inference of VPS/deployment/runtime permission.

**Out of scope:** commit, push, deployment, VPS sync, tmux/session management, public request or live observation.

## Mandatory Completion Matrix

| Proof edge | Task | Required hard evidence |
|---|---:|---|
| Bound Parent Design, Parent Plan and Delta bytes | 0, 6 | three SHA checks before code and final audit |
| Bound approved remediation Plan bytes | 0, 6 | externally supplied expected SHA equals exact Plan bytes |
| `INV-R01` daily committed linkage | 1 | canonical 1.6D fixture; every declared committed stream boundary passes before revision read; exact daily key; physical source raw regular/non-symlink/hash; both failure taxonomies |
| `INV-R02` bootstrap no replay | 2 | nonzero boundary checkpoint-only fixture |
| `INV-R03` per-root Step-A | 3, 4 | exact E-A manifest ID/read-back SHA; independent supervisor/C5 pre/post-root gates; canonical project-root and changed-environment negatives |
| `INV-R04` E-B own attestation | 3 | field provenance, exact receipt schema/read-back SHA/receipt ID, copied-byte and manifest-binding rejection |
| `INV-R05` C5/C6 | 3, 4 | runner-only handoff, deterministic root/checkpoint-only controlled-resume matrix and immutable bytes |
| `INV-R06` C8/C9/failed writer | 5 | active retention, flock held/stopped/missing/symlink/nonzero, manifest rules, zero lock repair |
| `INV-R07` time immutability | 4, 5 | exact durable projection time/window after restart |
| `INV-R08` safety | 0, 6 | all flags false; prohibited-import scan |
| `INV-R09` verified ProfileCore | 3, 4 | canonical E-A bundle, exact profile SHA binding, mutation/fake rejection |
| Parent compatibility | 6 | 1.6D/E-A/G2/shared-guard regression and no upstream diff |
| Pre-RED Contract Reality Gate | 1, 3, 4 | real upstream SSOT/serializer/verifier inspection; external Rule-12 no-mismatch record or blocking classification |
| Anti-shortcut governance gate | 1-6, final audit | scanner command/base SHA/scanner SHA/exit code; ERROR count `0`; every WARNING dispositioned |
| Blind-First independent audit handover | 6 | frozen final worktree; factual-only packet; independent auditor identity/session and read-only verdict |
| Completion claim | 6 | independent read-only `audit-plan-completion` `complete` verdict for final worktree |

## Plan Review Checklist

- [ ] All nine Delta invariants have Task, exact production entry point, proof and STOP condition.
- [ ] Parent Design, Parent Plan and approved Delta SHA-256 are bound; approved remediation Plan bytes require an external expected SHA.
- [ ] Positive upstream boundary fixtures are generated by canonical 1.6D/E-A production constructors/serializers with injected local openers, never handwritten foreign artifacts.
- [ ] Before any revision is read, every current checkpoint-declared committed stream passes exact path, boundary and final-line-hash validation; accepted raw bytes are regular, non-symlink and hash-bound.
- [ ] E-B `src/` never imports the E-A runner; only the E-B composition root calls the exact existing Step-A helper.
- [ ] E-A authority requires the exact approved Manifest ID/read-back SHA and the Parent exact receipt schema; C5 has runner-only fresh-root orchestration and C6 has Parent controlled-resume revalidation.
- [ ] Failed-terminal capacity release uses a non-creating probe of an existing regular zero-byte writer lock; it never repairs a root.
- [ ] Tasks 1/3/4 complete the Pre-RED Contract Reality Gate, use Rule-12 routing for any mismatch, and never fabricate an upstream contract or fixture.
- [ ] Tasks 1-6 pass the anti-shortcut scanner with zero ERROR and an explicit external disposition for every WARNING.
- [ ] Final completion audit uses the Blind-First factual handover and an independent read-only auditor; no audited-worktree mutation follows its verdict.
- [ ] No schema version, artifact family, threshold, endpoint, retry, queue, parallelism or permission expansion is allowed.
- [ ] `configs/base.py` change is only EOF whitespace removal with AST identity proof.
- [ ] Actual task-induced paths are an attributed subset of Allowed Change Scope; Plan approval and implementation completion do not authorize commit, deployment, runtime or network action.
