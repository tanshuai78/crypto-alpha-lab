# Stage 1.5D / 1.5F / 1.5G Storage Lifecycle and Resource Guard Hotfix Implementation Plan

```text
status = draft_for_plan_review
scope = stage1_5d_1_5f_1_5g_storage_lifecycle_resource_guard_hotfix
base_sha_at_plan_authoring = 34d337d520004e57c07f8e46fec3a2fada55382b
approved_design = docs/designs/2026-08-13-external-signal-shadow-lab-stage1-5d-1-5f-1-5g-storage-lifecycle-resource-guard-hotfix-design_CN.md
stage1_5g_execution_location = local_only
schedule_revision_producer_effective_enabled = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
implementation_allowed = false
plan_review_verdict = pending
```

> **For Codex:** 执行本计划前必须使用 `.agent/workflows/execute-approved-plan.md`，逐 Task 执行 TDD；在独立 Plan Review verdict 为 `Approve` 且用户明确批准前，不得修改生产代码、启动新 root、提交或部署。

**Goal:** 为新的 Stage 1.5D/1.5F 生产 root 建立可证明的存储预算、三层 reservation、checkpoint 收敛和本地流式 1.5G state review，使 30GB VPS 可以连续运行 7 天而不会因为无限 checkpoint/raw payload 增长、重启 compaction 或 VPS 上的 1.5G review 失联。

**Architecture:** 新增一个最小、stdlib-only 的 `stage1_5_storage_guard.py` 作为 D/F 共用写前 reservation、`flock` 和 root accounting 边界。D/F 所有新 root persistent write 按 `normal data`、`ordinary control plane`、`terminal control plane` 三类通过该边界；F checkpoint 改为 physical-last two-pass compaction，G 仅在本地对 state 进行流式 physical-last 归约。

**Tech Stack:** Python 3.11 stdlib (`fcntl`, `os`, `pathlib`, `shutil`, `json`, `hashlib`)、现有 `pytest`、`loguru`、Git、Graphify（只读 `query`/`path`）。不新增第三方依赖、数据库、队列、对象存储、factory 或 backend abstraction。

---

## 1. 输入、事实与执行前门禁

### 1.1 已冻结输入

1. 已批准 Design：`docs/designs/2026-08-13-external-signal-shadow-lab-stage1-5d-1-5f-1-5g-storage-lifecycle-resource-guard-hotfix-design_CN.md`。
2. 计划编写基线：`34d337d520004e57c07f8e46fec3a2fada55382b`；Plan 作者工作区只有上述 Design 为 untracked。执行人不得删除、覆盖、反向归因或重置它。
3. DOSUSDT local-only incident archive：`data/external_signal_shadow/evidence_archive/2026-08-13_dosusdt_lineage_incident/`，有 `ARCHIVE_MANIFEST.json` 与 `SHA256SUMS`。该 archive 不是 Git fixture、不是 formal evidence，不允许修改。
4. 已确认根因：F state/registry replay append、启动全量 compaction + `.bak`、D raw timestamp 路径重复写、D raw budget 接线到错误日 JSONL、G state 全量 list 加载。

### 1.2 执行开始前必须记录的 provenance

执行人先运行，记录原样输出到 repair/execution ledger；任何不通过均停止，不得以本计划修复：

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export BASE_SHA="$(git rev-parse HEAD)"
export PLAN_PATH="docs/plans/2026-08-13-external-signal-shadow-lab-stage1-5d-1-5f-1-5g-storage-lifecycle-resource-guard-hotfix-implementation-plan_CN.md"
export DESIGN_PATH="docs/designs/2026-08-13-external-signal-shadow-lab-stage1-5d-1-5f-1-5g-storage-lifecycle-resource-guard-hotfix-design_CN.md"
printf 'BASE_SHA=%s\n' "$BASE_SHA"
shasum -a 256 "$PLAN_PATH" "$DESIGN_PATH"
git status --short --untracked-files=all
git diff --check "$BASE_SHA"
```

Expected: `BASE_SHA` is explicitly recorded; existing untracked Design/Plan are preserved; no pre-existing dirty path may be silently modified. If `BASE_SHA` differs from the Plan header, record why and require a reviewer to confirm the diff still represents the approved Design before implementation.

### 1.3 Hard stop conditions

Stop the current batch and report instead of expanding scope when any condition occurs:

1. A required writer/consumer is outside `Allowed Change Scope`, or a formal/anchor/admission/watermark semantic change is required.
2. The DOS archive checksum, manifest or described source facts disagree; archive facts win and require a Design delta if they change a safety threshold.
3. A terminal write-set bound cannot be expressed with bounded fields, or `host_emergency_blocker_reserve_bytes < D terminal peak + F terminal peak`.
4. A test needs real Binance/network access, changes a poll/depth/authority threshold, starts a live root, or runs 1.5G on the VPS.
5. Any unrelated test that previously passed fails after a Task and the cause is outside that Task's root cause.
6. Any proposed optimization requires a second storage backend, global formatter/autofix, automatic root deletion, or mutation of an old root/archive.

## 2. Resolved Scope-Delta Evidence

The initial Plan Review found three verified persistent writers omitted from the original Design Scope Gate. The approved Design has now received the following narrow scope delta; no business semantic or safety authority changed:

| Omitted persistent writer | Verified source evidence | Why it blocks this Plan |
| --- | --- | --- |
| `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py` | `write_detail_retry_scheduler_state()` uses `tmp_path.write_text()` and `os.replace()`; D runner calls it at `run_stage1_5d_live_event_source_smoke_collector.py:3699`. | It persists a D new-root checkpoint. Leaving it unguarded contradicts the Design's “all persistent writes” rule and makes static closure false. |
| `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py` | `append_jsonl()` and `write_json()` use direct `open(..., "a"/"w")`; F runner imports them at multiple production write callsites. | It is the concrete F stream writer. Guarding only runner call syntax would be a bypassable façade, not a storage boundary. |
| `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py` | `ScheduleRevisionRegistry.record_revision()` directly appends JSONL; F runner's `process_schedule_revision_event()` calls it for `schedule_revision_registry.jsonl`. | The Design classifies revision registry as normal data. Treating it as unchanged leaves a live normal-data writer unguarded. |

The Design now permits guard-only wiring for the three modules and their tests. They are included below and in Tasks 6/7. This resolves the earlier P0 scope collision; Plan Review is again required before implementation. The delta does not authorize changes to retry scheduling, revision linkage/application, event/admission semantics, checkpoint identity, schedule-revision producer enablement, watermark identity, or authority flags.

## 3. Allowed Change Scope

This scope constrains future implementation only. It does not authorize changes to the approved Design or this Plan. A new file, caller or schema outside the list is a Design/Plan stop condition.

### Allowed implementation paths

- `configs/base.py`
- `src/research/external_signal_shadow/stage1_5_storage_guard.py` (new)
- `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py` (guard-only scheduler checkpoint persistence)
- `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- `src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py` (approved remediation scope-delta: guard-only identity-index rebuild persistence)
- `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py` (only semantic fingerprint/replay classifier)
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py` (guard-only stream persistence)
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py`
- `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py` (guard-only revision registry persistence)
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`

### Allowed verification paths

- `tests/research/external_signal_shadow/test_stage1_5_storage_guard.py` (new)
- `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py` (read-only compatibility regression)
- `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py` (read-only compatibility regression)
- `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py`
- `tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py` (approved remediation scope-delta: identity-index rebuild guard propagation)
- `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py`
- `tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py`
- `tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py` (read-only compatibility regression)
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- `tests/fixtures/external_signal_shadow/stage1_5d/storage_lifecycle/**` (new synthetic fixtures only)
- `tests/fixtures/external_signal_shadow/stage1_5f/storage_lifecycle/**` (new synthetic fixtures only)

### Allowed documentation paths

- `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`
  - Required because this is the operator's canonical D/F deployment and inspection runbook. It must replace any VPS 1.5G execution path with minimal-root sync plus local-only 1.5G review, add non-destructive storage preflight/guard health checks, and preserve Git exact-commit/new-root deployment. It must not add commands that enable the schedule-revision producer or mutate/delete evidence.

### Allowed generated/runtime artifacts

- `none`.

Synthetic fixtures above are committed test source, not generated/runtime artifacts. New production roots, local review outputs, `data/external_signal_shadow/evidence_archive/**`, `.pytest_cache/**`, `__pycache__/**` and `graphify-out/**` are not implementation outputs and must not be committed by this Plan.

### Affected but unchanged

- `docs/designs/2026-08-13-external-signal-shadow-lab-stage1-5d-1-5f-1-5g-storage-lifecycle-resource-guard-hotfix-design_CN.md`
  - Evidence: approved Design is input only; execution must not rewrite accepted decisions.
- `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`
  - Compatibility evidence: `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py` is run read-only in Task 9; no import/caller modification is allowed.
- `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
  - Compatibility evidence: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py` and the D runner suite are run read-only in Task 9; no parser edits are allowed.
- `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
  - Evidence: runner routes its already-built output through the guard; summary business builder/schema is not changed.
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_requests.py`
  - Compatibility evidence: F runner manifest/request regressions and `test_stage1_5f_runtime_gate_validator.py` run read-only in Task 9; no endpoint, timeout, poll cadence or depth limit edits are allowed.
- `scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py`
  - Evidence: CLI interface and local-only operator policy remain; only the reviewer state loader/reducer changes.
- `configs/base.py` authority and request constants outside this Plan's named storage constants.
  - Evidence: final AST/grep lock proves no change to `RISK_LIVE_TRADING_ENABLED`, producer enablement, poll/depth parameters, formal versions or authority flags.

### Forbidden

- Any mutation outside the explicit allowed paths.
- Formal event/schedule revision/anchor contracts, anchor/admission reducer behavior outside the named replay classifier, watermark schema version or watermark identity semantics.
- Poll interval, depth limit, authority flags, `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED`, live/paper/execution/alpha permissions.
- Database, queue, object storage, third-party dependency, generic backend, interface or factory.
- `ruff check --fix .`, `ruff format .`, `git clean`, `git reset --hard`, `rsync --delete`, `rm -rf`, or automatic evidence/root cleanup.
- Altering an old root, DOSUSDT archive, historical raw payload, historical manifest, snapshot or local 1.5G output.
- Starting 1.5D/1.5F production roots, performing a VPS 1.5G review, or changing server state during implementation tests.

### Approved remediation scope-delta (2026-08-14)

The completion audit found that `rebuild_missing_formal_launch_identity_index()` is a production persistent writer through `append_jsonl()`. It is called only by the already-allowed D runner, but its producer module and dedicated test were omitted from the original writer inventory. The user approved the two paths added above solely to make `storage_guard` required and propagate the runner's existing guard into this startup identity-index rebuild. This delta does not change schedule-revision classification, linkage, enablement, contracts, or emitted rows.

## 4. Topology Preflight and Compatibility Classification

Before Task 1, rerun these read-only checks. `graphify-out` is not updated by this Plan; Graphify is advisory and source `rg` is the authority for exact callsites.

```bash
for symbol in \
  write_detail_payload_append_only \
  build_detail_payload_path \
  enforce_payload_budget \
  write_detail_retry_scheduler_state \
  compact_observer_state_jsonl \
  update_batch_registry_status \
  write_watermark_atomic \
  ScheduleRevisionRegistry \
  classify_event_symbol_revision_admission \
  reduce_latest_states_by_event_symbol_id; do
  graphify query "$symbol" --budget 1200
done

rg -n "\\b(write_detail_payload_append_only|enforce_payload_budget|write_detail_retry_scheduler_state|compact_observer_state_jsonl|update_batch_registry_status|write_watermark_atomic|record_revision|classify_event_symbol_revision_admission|reduce_latest_states_by_event_symbol_id)\\s*\\(" src scripts tests
```

Expected direct consumer classification:

| Symbol | Direct production consumer | Required treatment |
| --- | --- | --- |
| `write_detail_payload_append_only`, `build_detail_payload_path`, `enforce_payload_budget`, `write_detail_retry_scheduler_state` | D runner | modify in Task 2/6. Task 0 records the pre-change helper names; Task 2 may replace `write_detail_payload_append_only` with a content-addressed writer, and Task 9 verifies the post-change guarded writer rather than preserving this name. |
| `compact_observer_state_jsonl`, `update_batch_registry_status`, `write_watermark_atomic`, `ScheduleRevisionRegistry`, `classify_event_symbol_revision_admission` | F runner | modify in Task 3/4/5/7 |
| `reduce_latest_states_by_event_symbol_id` | 1.5G integrity reducer | modify in Task 8 |
| existing D/F test modules | verification consumers | modify only under allowed verification paths |
| formal contract, parser, request transport, schedule revision linkage/application semantics | compatible but unchanged | retain read-only tests/grep evidence; do not edit |

If source confirms another persistent writer producing a new D/F root outside the two runners and allowed storage/state/watermark modules, classify it as P0 and stop. Do not patch it opportunistically.

## 5. Invariant-to-Task Mapping

| Design invariant | Production entry/persistence/consumer | Task and mechanical evidence |
| --- | --- | --- |
| `INV-01` | D/F runner startup before stream writes | Task 1/6/7: mocked free-space startup RED tests; non-zero/blocker assertions |
| `INV-02` | guard reservation, D gate, F terminal summary | Task 1/5/6/7: normal/ordinary denial, terminal write-set and fail-closed tests |
| `INV-03` | `stage1_5_storage_guard.py`, all D/F writes | Task 1/3/5/6/7/9: exact config, lock, peak math, write-surface static test |
| `INV-04` | F state/batch checkpoint files | Task 3/7: physical-last two-pass compaction, no `.bak` |
| `INV-05` | F checkpoint temp/replace/restart | Task 3/5/7: crash-before/after replace and candidate reservation tests |
| `INV-06` | replay classifier, batch registry, watermark recovery reducer | Task 3/4/5/7: no-op replay plus complete crash matrix |
| `INV-07` | D raw payload writer | Task 2/6: `article + variant + raw SHA256` `.bin` reuse test |
| `INV-08` | D actual raw payload directory budget | Task 2/6: directory budget and blocked-request manifest test |
| `INV-09` | D payload path and manifest provenance | Task 2/6: content/variant split and manifest relation tests |
| `INV-10` | F loader/state/compaction and G state review | Task 3/4/7/8: physical-last equivalence and out-of-order fixtures |
| `INV-11` | F checkpoint loader/compaction and G parse error | Task 3/7/8: malformed non-empty row preserves file and fails closed |
| `INV-12` | deployment review runbook | Task 9: no VPS 1.5G command; local read-only workflow validation |
| `INV-13` | all boundaries | Task 0/9: AST/grep and full regression prove no contract/request/authority drift |
| `INV-14` | `configs/base.py`, D/F output flags | Task 2/9: safety literal/summary regression grep; all flags remain false |

## 6. Guarded Write-Surface Matrix

This execution matrix intentionally refines Design section 8.3's two-column table. The third column prevents an implementer from accidentally allowing routine runtime-gate/summary/watermark writes to consume the reserved final-blocker space.

| Stage | Normal Data | Ordinary Control Plane | Terminal Control Plane |
| --- | --- | --- | --- |
| 1.5D | events; raw-payload JSONL; request manifest; heartbeat; detail retry scheduler state/diagnostics; parse results; formal launch identity index; revision payload versions; raw BAPI detail payload | READY runtime gate; normal smoke summary | FAILED runtime gate; final bounded storage summary; bounded final storage diagnostic; optional failed-payload terminal manifest |
| 1.5F | observer state; batch/revision registry; accepted/rejected/pending/diagnostic rows; request manifest; depth snapshots; heartbeat | observer root contract at startup; normal summary; authorized watermark transaction commit | final bounded storage summary; bounded final storage diagnostic; terminal blocker used to set `block_new_event_admission=true` before exit |

Required class invariants:

```text
normal data:
  preserve root ordinary + root emergency and host ordinary + host emergency
ordinary control plane:
  preserve root emergency and host emergency
terminal control plane:
  may consume only configured emergency reserve, then process exits
```

No task may reclassify a normal artifact as ordinary/terminal merely to bypass a failed reservation. The terminal write set is only the bounded set in the table and Design section 5.1.

## 7. Tasks

### Task 0: Read-only provenance, storage facts and writer inventory

**Design invariants:** `INV-01` through `INV-14` (preflight evidence only).

**Files:**
- Read: approved Design, `docs/roadmap.md`, `configs/base.py`, all allowed implementation/test paths, DOS archive.
- Create/modify: none.

**Step 0: Capture external, read-only execution baselines.**

The repository remains read-only in Task 0. A temporary provenance file outside the repository is allowed only to make the final scope/config comparison reproducible:

```bash
export CONFIG_BASELINE_PATH="$(mktemp "${TMPDIR:-/tmp}/stage1_5_storage_config_baseline.XXXXXX.py")"
export PREEXISTING_UNTRACKED_PATHS="$(mktemp "${TMPDIR:-/tmp}/stage1_5_storage_preexisting_untracked.XXXXXX.txt")"
cp configs/base.py "$CONFIG_BASELINE_PATH"
git ls-files --others --exclude-standard | sort > "$PREEXISTING_UNTRACKED_PATHS"
shasum -a 256 "$CONFIG_BASELINE_PATH" "$PLAN_PATH" "$DESIGN_PATH"
printf 'CONFIG_BASELINE_PATH=%s\nPREEXISTING_UNTRACKED_PATHS=%s\n' \
  "$CONFIG_BASELINE_PATH" "$PREEXISTING_UNTRACKED_PATHS"
```

Expected: only external `/tmp` provenance snapshots are created; no workspace file is created or modified. Keep both paths for Task 9.

**Step 0.5: Confirm read-only compatibility regressions exist before implementation.**

```bash
test -f tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py
test -f tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py
test -f tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py
```

Expected: all three files exist and are retained as read-only verification inputs for Task 9. If any is absent, or if its Task 9 execution fails and would require a production contract/parser/runtime-gate change outside this Plan, stop for Plan review; do not widen the scope merely to make the regression pass.

**Step 1: Verify local DOSUSDT archive without reading all JSONL into memory.**

```bash
ARCHIVE="data/external_signal_shadow/evidence_archive/2026-08-13_dosusdt_lineage_incident"
test -d "$ARCHIVE"
test -f "$ARCHIVE/ARCHIVE_MANIFEST.json"
test -f "$ARCHIVE/SHA256SUMS"
(cd "$ARCHIVE" && shasum -a 256 -c SHA256SUMS)
du -sh "$ARCHIVE"
wc -l "$ARCHIVE"/stage1_5f/observer_state_dosusdt_latest.json \
      "$ARCHIVE"/stage1_5d/event_dosusdt.jsonl \
      "$ARCHIVE"/stage1_5d/request_manifest_dosusdt.jsonl
find "$ARCHIVE/stage1_5d" -type f -name '*.bin' -o -path '*/raw_payloads/*' | head -n 40
```

Expected: all checksum rows pass; provenance is recorded as local-only incident evidence; no archive file changes. If current manifest facts differ from Design's historical counts, record the actual result and stop for Design review only if a limit or safety decision would change.

**Step 2: Record static writer inventory before changing production code.**

```bash
rg -n "\\b(append_jsonl|open|Path\\.write_text|Path\\.replace|write_text|json\\.dump|os\\.replace|write_watermark_atomic)\\b" \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py \
  src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py \
  src/research/external_signal_shadow/stage1_5d_runtime_gate.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py \
  src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py
```

Expected: an explicit pre-change list of every root persistent writer, including D scheduler/summary/gate/raw and F stream storage/revision registry/contract/state/batch/watermark/summary/manifest/snapshot writers. This list is the input to Task 9's static closure test; no implementation yet.

**Out of scope:** no profile run against a full root, no server access, no archive mutation, no production-root scan.

### Task 1: Add storage constants and the minimal guard TCB first

**Design invariants:** `INV-01`, `INV-02`, `INV-03`, `INV-13`, `INV-14`.

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5_storage_guard.py`
- Create: `tests/research/external_signal_shadow/test_stage1_5_storage_guard.py`
- Modify: `configs/base.py`

**Step 1: Write RED tests for configuration and reservation algebra.**

Test, using injected `disk_usage` and temporary roots only. The only permitted new `configs/base.py` assignments are exactly these storage constants; all existing assignments and every other AST node must remain byte-for-byte/AST-equivalent to the Task 0 external baseline:

```text
EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES
EXTERNAL_SIGNAL_STAGE1_5_HOST_RUNTIME_PROTECTED_RESERVE_BYTES
EXTERNAL_SIGNAL_STAGE1_5_HOST_ORDINARY_CONTROL_PLANE_RESERVE_BYTES
EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES
EXTERNAL_SIGNAL_STAGE1_5D_ROOT_MAX_BYTES
EXTERNAL_SIGNAL_STAGE1_5D_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES
EXTERNAL_SIGNAL_STAGE1_5D_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES
EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
EXTERNAL_SIGNAL_STAGE1_5D_RAW_PAYLOAD_ROOT_MAX_BYTES
EXTERNAL_SIGNAL_STAGE1_5F_ROOT_MAX_BYTES
EXTERNAL_SIGNAL_STAGE1_5F_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES
EXTERNAL_SIGNAL_STAGE1_5F_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES
EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
EXTERNAL_SIGNAL_STAGE1_5_ROOT_RECONCILIATION_SCAN_INTERVAL_SEC
EXTERNAL_SIGNAL_STAGE1_5F_CHECKPOINT_COMPACT_INTERVAL_SEC
EXTERNAL_SIGNAL_STAGE1_5F_CHECKPOINT_COMPACT_THRESHOLD_BYTES
```

Their required values are, in the same order: `8*MiB*1024`, `4*MiB*1024`, `52*MiB`, `12*MiB`, `1*GiB`, `12*MiB`, `4*MiB`, `2*MiB`, `768*MiB`, `2*GiB`, `28*MiB`, `4*MiB`, `2*MiB`, `300`, `900`, `256*MiB`, where `MiB=1024*1024` and `GiB=1024*1024*1024`. The implementation may use readable integer arithmetic, but no environment fallback or derived runtime override.

Do not reuse or modify the existing `validate_configs_base_ast_delta()` production attestation helper: it protects a different prior allowlist. This Task adds a test-only baseline-versus-final AST comparator that removes none of these nodes before comparison; it permits only the exact additions above and rejects a replacement, deletion or movement of any pre-existing assignment.

Tests:

1. exact Design constants and names: `EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES=8GiB`, `EXTERNAL_SIGNAL_STAGE1_5_HOST_RUNTIME_PROTECTED_RESERVE_BYTES=4GiB`, host ordinary `52MiB`, host emergency `12MiB`, D `1GiB/12MiB/4MiB/2MiB/768MiB`, F `2GiB/28MiB/4MiB/2MiB`, scan `300s`, compact `900s`, threshold `256MiB`. The test enumerates every newly allowed assignment by exact name and value.
2. `normal` write is denied if it would consume any ordinary or emergency reserve.
3. `ordinary_control_plane` write is denied if it would consume emergency reserve.
4. `terminal_control_plane` may consume emergency reserve but never the `4GiB` protected reserve.
5. `transient_peak_bytes >= max(0, persistent_delta_bytes)` is required; direct append, atomic replacement and compaction use the exact Design formulas.
6. generic startup validation rejects a supplied D/F terminal write-set byte bound above its configured cap, and rejects host emergency smaller than the supplied D+F terminal peaks. Actual artifact serialization is tested only in Tasks 6 and 7.
7. two concurrent processes on the project lock cannot both approve a near-reserve write based on the same stale free-space value.

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py -q
```

Expected before implementation: failure due to the missing module/constants.

**Step 2: Implement the smallest shared guard.**

In `configs/base.py`, add only named storage constants from Design section 5.1. Do not modify any existing threshold or authority constant.

In `stage1_5_storage_guard.py`, use only stdlib and provide one narrow, concrete API for D/F:

1. build/open fixed project lock `data/external_signal_shadow/.stage1_5_storage_guard.lock` with `fcntl.flock`;
2. recursively scan one output root and retain `accounted_root_bytes` plus last scan time;
3. validate startup free/root/write-set bounds;
4. reserve one serialized direct append or one exact atomic candidate, under the lock, with explicit artifact class;
5. invoke a caller-provided low-level write only after approval, reconcile actual persistent delta under the same lock, and return a structured `ready`/blocked result;
6. expose the bounded status fields required by Design section 8.1 and a safe owned-temp cleanup predicate.

Every production persistence API added or changed by this Plan receives a mandatory keyword-only `storage_guard` argument with no default. `None`, optional typing, a direct-write fallback and a compatibility bypass are forbidden. Missing the argument must fail before any filesystem write (`TypeError` is acceptable). The callers named in Tasks 2, 3, 5, 6 and 7 must always pass the guard and artifact class; Task 9 statically rejects an optional guard or a guardless fallback.

Use a single small process-local guard state only if necessary to carry root accounting; no base class, factory, registry, storage backend, CLI/env override, global background thread or implicit fallback. Document the deliberate global lock ceiling in one `# ponytail: flock assumes local filesystem; NFS/SMB not supported; use per-root locks only if measured throughput requires them` comment.

**Step 3: Add generic terminal-budget self-validation before runners use it.**

The guard owns only generic byte accounting: each caller supplies bounded serialized-byte length, persistent delta and transient peak. It must not construct synthetic runtime-gate, summary, diagnostic or manifest payloads as evidence for the real D/F write sets. Verify the ordered terminal peak formula:

```text
max_k(sum(previous persistent_delta_bytes) + current transient_peak_bytes)
```

The concrete D/F terminal artifact builders remain in their existing runner/gate/summary modules. Tasks 6 and 7 serialize their real maximum field shapes, verify every field has a bounded limit, and pass the resulting real write-set peaks to this generic validator.

**Step 4: Run focused tests.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py -q
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py -q
```

Expected: all pass; no gate/summary business contract regression.

**Out of scope:** runner wiring, raw path changes, state compaction, deployment commands.

### Task 2: Make D raw payload persistence content-addressed and budget the real directory

**Design invariants:** `INV-02`, `INV-03`, `INV-07`, `INV-08`, `INV-09`, `INV-13`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py`
- Optionally create synthetic D fixture under `tests/fixtures/external_signal_shadow/stage1_5d/storage_lifecycle/` only if it makes a multi-row provenance test clearer.

**Fixture rule:** if a synthetic fixture is needed, create it in this Task with a one-line README stating its generated identities and that it contains no real raw BAPI bytes. Task 0 creates no workspace fixture.

**Step 1: Write RED tests for the exact raw identity.**

Add tests that assert:

1. `build_detail_payload_path` accepts only the canonical `source_article_id`, `detail_fetch_variant`, `raw_payload_sha256` identity and produces `raw_payloads/announcement_detail/<article>/<variant>.<full_sha256>.bin`.
2. The old `timestamp_ms`/suffix interface and suffix validation are removed; `.bin` is the only persisted suffix. `content_type` remains manifest metadata and cannot change the path for identical bytes.
3. same article + variant + bytes across retries writes one final file and returns identical path/hash; manifest callers may still append separate request rows.
4. changed bytes or variant produces a distinct file; identical bytes for another article stays under that other article path.
5. actual recursive `raw_payloads/announcement_detail/` usage, not a daily JSONL file size, enforces `EXTERNAL_SIGNAL_STAGE1_5D_RAW_PAYLOAD_ROOT_MAX_BYTES`.
6. a reservation denial returns `raw_payload_persisted=false`, `payload_path=null`, hash if available, a bounded storage blocker, and never refers to temp/nonexistent files.
7. the content-addressed writer rejects a missing `storage_guard` before it opens or creates any payload/temp path.

Name the last regression `test_content_addressed_writer_requires_guard` so the mandatory-boundary proof is directly discoverable.

Run the test module and confirm RED failures.

**Step 2: Implement only the content-addressed writer and real raw root accounting.**

Replace the old timestamp-addressed `write_detail_payload_append_only` implementation with the content-addressed writer. Task 0 inventory intentionally records the old name; Task 9 checks the resulting writer callsite rather than requiring the old symbol to survive. Route raw temporary/final write through a mandatory keyword-only `storage_guard` with `normal_data`. The writer must reserve the exact candidate temp peak, atomically create the final `.bin` only if absent, and return current manifest-compatible fields. Keep original per-day config and semantics untouched; use the new raw-root constant solely for the real raw directory.

Do not dedupe across article ids, delete prior versions, change BAPI parser behavior, alter manifest identity fields, or write a raw file after a denied reservation.

**Step 3: Verify focused D behavior.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py -q
```

Expected: all old provenance tests adapted to the new canonical `.bin` path and all new identity/budget tests pass.

**Out of scope:** D runner's other persistent streams and runtime gate wiring (Task 6).

### Task 3: Make F checkpoint load/compaction fail-closed and bounded

**Design invariants:** `INV-03`, `INV-04`, `INV-05`, `INV-10`, `INV-11`, `INV-13`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Optionally create synthetic F fixtures under `tests/fixtures/external_signal_shadow/stage1_5f/storage_lifecycle/`.

**Fixture rule:** any synthetic fixture is created here only after its RED assertion is defined; it records only generated state/batch identities and cannot claim real exchange payload provenance.

**Step 1: Write RED state compatibility and malformed-checkpoint tests.**

Add tests for:

1. historical `EventSymbolState` row without `latest_source_semantic_fingerprint` loads with `""`; a new row round-trips it; `observer_state_schema_version` remains `3`.
2. `load_latest_state_by_event_symbol_id` and batch registry loader select the last successfully parsed physical row, independent of timestamp order/equality/missing timestamp.
3. any malformed non-empty state or registry row is returned as integrity failure, never silently skipped; startup/compaction caller can fail closed.
4. compaction never replaces an authoritative malformed source; original bytes remain; it produces only a bounded integrity diagnostic input/result, no full `.bak`.
5. crash before replace leaves original; crash after replace leaves complete compacted physical-last stream; owned `.<target>.compact.<pid>.tmp` cleanup is safe and `.compacted.tmp` legacy broad cleanup is not used.
6. two-pass compact candidate is emitted line-by-line and counted incrementally, never built as one giant JSONL string; candidate peak, rather than prior source size, controls reservation.
7. a large append stream with a small latest map can compact when its candidate fits; candidate that cannot reserve exits without temp/replace.
8. compaction/registry persistence rejects a missing `storage_guard` before a temporary or authoritative checkpoint write.

Name this regression `test_checkpoint_writer_requires_guard`.

Run the state module and confirm RED failures.

**Step 2: Implement physical-last loader and compaction.**

1. Extend `EventSymbolState` with `latest_source_semantic_fingerprint: str = ""` and preserve the existing filtered `from_dict` compatibility behavior.
2. Replace warning-and-continue malformed handling for checkpoint streams with a typed/structured integrity result that the runner can turn into a fail-closed blocker. Do not drop a malformed non-empty row.
3. Generalize the existing state compaction logic, not a new persistence framework, so state and batch registry each compact with the same physical-last comparator.
4. Use exactly three phases: (A) scan the authoritative stream into the physical-last map and stop on malformed non-empty input; (B) serialize canonical JSONL line-by-line to an in-memory byte counter only, without any filesystem mutation; (C) reserve the exact candidate bytes with the mandatory `storage_guard`, then reserialize line-by-line to the owned temp, fsync, `os.replace`, fsync the parent directory and reconcile account. The second pass must not construct a giant JSONL string.
5. Do not create any `.bak`, do not retain transition history in checkpoint streams, and do not modify accepted/rejected/snapshot/manifest evidence streams.
6. Make `update_batch_registry_status` the sole monotonic transition boundary: reject final regressions and suppress equal `(status, durable_keys, reason)` writes without appending.
7. The owned-temp cleanup predicate must require both the exact target basename and this process-instance-id. It is called exactly once at startup, never in periodic compaction cycles.

**Step 3: Verify state module.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py -q
```

Expected: all compaction, malformed, crash, physical-last, compatibility and monotonicity tests pass.

**Out of scope:** source semantic classification and runner recovery order (Tasks 4/7); no observer-state schema version bump.

### Task 4: Add semantic replay fingerprint without changing admission semantics

**Design invariants:** `INV-06`, `INV-10`, `INV-13`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py` only if Task 3 did not already add the field.

**Step 1: Write RED fingerprint property tests.**

For one uppercase symbol, assert canonical JSON (`sort_keys=True`, compact separators, UTF-8) and SHA256 projection behavior:

1. every Design-listed included field changes fingerprint;
2. each excluded operational field (`now_ms`, request id, manifest timestamp/path, local filename, HTTP fetch time, raw payload path) does not;
3. per-symbol map fields are selected by uppercase symbol and maps are sorted;
4. same semantic fingerprint plus same durable state returns no business mutation for exact, active/completed and terminal replay paths;
5. a changed included field yields one legal pending revision/update, then a repeated identical input yields no second durable business update.

Run focused loader tests and confirm RED failures.

**Step 2: Implement only the frozen projection and classifier comparison.**

Add a local deterministic helper in the existing loader module. It must not reuse or redefine `latest_event_payload_hash`: raw payload hash remains provenance. Persist/use `latest_source_semantic_fingerprint` solely in `classify_event_symbol_revision_admission` and the existing pending upsert path. Do not change stable ids, formal contract validation, launch anchor selection, schedule revision processing, pending deadlines or admission decision branches.

**Step 3: Verify loader compatibility.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py -q
```

Expected: all existing contract/anchor tests and new fingerprint properties pass; no API consumer outside allowed runner/tests needs editing.

**Out of scope:** durable append suppression and missing transaction recovery wiring are runner responsibilities in Task 7.

### Task 5: Guard atomic watermark writes without altering watermark meaning

**Design invariants:** `INV-02`, `INV-03`, `INV-05`, `INV-06`, `INV-13`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py`

**Step 1: Write RED tests.**

Assert that:

1. the existing watermark JSON content/version/identity is byte-for-byte logically unchanged after a successful guarded atomic write;
2. its candidate temporary bytes and old-target delta are supplied to `ordinary_control_plane` reservation;
3. ordinary denial preserves the target and reports a storage result that lets the runner terminalize; no partial temp is referenced;
4. crash-before-replace keeps original and owned tmp cleanup never touches arbitrary `.tmp` paths.
5. `write_watermark_atomic` without its mandatory keyword-only `storage_guard` raises before creating a temp or mutating the target.

Name this regression `test_watermark_writer_requires_guard`.

**Step 2: Implement a narrow mandatory guard handoff.**

Keep `write_watermark_atomic` as the only watermark writer and route its existing same-directory atomic procedure through the mandatory keyword-only `storage_guard` using `ordinary_control_plane`. Preserve its public identity semantics, schema and atomic replace/fsync behavior. Do not add a new watermark format, change its stable keys, or add recovery policy here.

**Step 3: Verify.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py -q
```

Expected: atomic behavior remains green and new denial/crash assertions pass.

**Out of scope:** runner decides whether a missing watermark edge is authorized (Task 7).

### Task 6: Route the complete 1.5D write surface and fail through its existing runtime gate

**Design invariants:** `INV-01`, `INV-02`, `INV-03`, `INV-07`, `INV-08`, `INV-09`, `INV-13`, `INV-14`.

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`

**Step 1: Write RED runner/gate tests.**

Cover:

1. startup below `8GiB` or D root at/over own budget writes no normal streams, exposes `storage_start_*` blocker if terminal evidence fits, and returns non-zero;
2. normal D paths in the matrix are passed to normal reservation before bytes are written;
3. READY gate and normal summary are ordinary control-plane; they cannot consume emergency reserve;
4. runtime normal/ordinary reservation failure appends bounded `fatal_blockers`, produces `decision=stage1_5d_runtime_gate_failed`, `consumable_by_stage1_5f=false`, final bounded summary/diagnostic and exit;
5. raw storage failure after HTTP response produces a terminal manifest row only if it can be written, with `raw_payload_persisted=false`, null path and storage blocker; if it cannot, `request_manifest_persistence_unknown=true` is represented in terminal summary/gate;
6. parser/event/formal contract behavior, producer default-disabled, authority flags and original request budgets remain unchanged.
7. the real maximum serialized D FAILED runtime gate, final smoke summary, final storage diagnostic and optional failed-payload terminal manifest each obey their bounded field limits; their ordered real write-set peak is at or below `EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES`.
8. `write_detail_retry_scheduler_state` without its mandatory keyword-only `storage_guard` fails before `Path.write_text`/`Path.replace`; the runner has no direct guardless persistent writer.

Name the scheduler regression `test_detail_retry_scheduler_writer_requires_guard`; name the real-artifact tests `test_d_actual_max_failed_gate_fits_terminal_cap`, `test_d_actual_terminal_set_fits_terminal_cap`, `test_actual_terminal_field_length_is_bounded` and `test_oversized_actual_d_terminal_shape_blocks_startup`.

**Step 2: Wire D runner only through the guard boundary.**

1. Construct/validate D guard before normal stream directory/write activity.
2. Route every D root write recorded in Task 0 through the guard with the class in section 6. This includes events, raw payload JSONL, manifest, heartbeat, scheduler state/diagnostics, parse/audit rows, formal identity index, raw detail payload, runtime gate and output summary. `write_detail_retry_scheduler_state()` receives the mandatory guard only to use it; its scheduler state schema and retry selection semantics remain unchanged.
3. On a guard failure, stop normal polling; use only the actual bounded terminal class write set and the existing gate's `fatal_blockers` mapping. Do not introduce a parallel F-only storage signal or synthetic terminal evidence.
4. Reconcile actual root size at startup and configured cadence under the shared lock. A reconciliation breach follows the same terminal path.

**Step 3: Verify D.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: all pass, including existing parser/formal-v2/producer-disabled regression cases.

**Out of scope:** parser/formal contract/producer implementation and any change to 1.5F non-ready runtime-gate interpretation.

### Task 7: Route the complete 1.5F surface, run recovery exactly once, and summarize storage health

**Design invariants:** `INV-01`, `INV-02`, `INV-03`, `INV-04`, `INV-05`, `INV-06`, `INV-10`, `INV-11`, `INV-13`, `INV-14`.

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`

**Step 1: Write RED runner tests for the recovery matrix.**

Add deterministic no-network tests for:

1. F startup below free/root threshold refuses normal writes; malformed state/batch checkpoint produces `blocked_checkpoint_integrity`, `block_new_event_admission=true`, bounded terminal summary/diagnostic and non-zero exit.
2. repeated `active_or_completed_duplicate_revision` and `terminal_revision_seen` leave state/registry/watermark file row counts unchanged; duplicate counts are process telemetry only.
3. `unknown -> batch_started`; `batch_started -> siblings_partially_durable | siblings_all_durable | batch_blocked`; final statuses never regress; equal registry tuple does not append.
4. each crash window: after first sibling, last sibling, all durable before watermark, watermark before final registry. Replay performs exactly one missing durable edge and never recreates a business-state row.
5. `watermark_committed` with missing watermark identity is corruption and fails closed; `watermark_committed`/`batch_blocked` replay writes no new registry/watermark row.
6. runtime reservation/reconciliation failure stops new admission/snapshot/normal append, sets `block_new_event_admission=true`, writes only terminal summary/diagnostic and exits.
7. summary includes every Design 8.1 storage field with truthful `ready`/blocked values, current account/root budget/last scan, terminal peak/emergency reserve and `storage_blocker`; all trade/paper/live/execution/alpha fields remain false.
8. startup compacts both state and batch registry; runtime compacts each independently only after interval plus threshold; it never compacts an old root in place.
9. the real maximum F final observer summary, final storage diagnostic and terminal admission blocker each obey their bounded field limits; their ordered real write-set peak is at or below `EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES`.
10. `append_jsonl`, `write_json` and `ScheduleRevisionRegistry.record_revision` each reject a missing mandatory keyword-only `storage_guard` before any persistent write; owned-temp cleanup is invoked once at startup and never by an ordinary compaction cycle.

Name the boundary regressions `test_production_append_jsonl_requires_guard`, `test_write_json_requires_guard` and `test_schedule_revision_registry_writer_requires_guard`; name the real-artifact tests `test_f_actual_max_final_summary_fits_terminal_cap`, `test_f_actual_terminal_set_fits_terminal_cap` and `test_oversized_actual_f_terminal_shape_blocks_startup`.

**Step 2: Implement F runner in the prescribed order.**

1. Construct/validate F guard before creating normal streams; safely remove only owned temporary files inside its new output root once at startup, using both process-instance-id and target basename.
2. Startup load/compaction: convert checkpoint integrity result into a terminal fail-closed path before regular polling.
3. Before each launch replay, load latest state/batch maps. Use Task 4 semantic classifier; do not append state for semantic no-op active/completed/terminal paths.
4. Run the six-step Design recovery reducer even for a semantic no-op. `update_batch_registry_status` remains the only registry transition boundary, and `write_watermark_atomic` is called only at its authorized edge.
5. Route every F root write in section 6 through the mandatory guard: root contract, state/batch/revision checkpoint/evidence rows, manifests, snapshots, heartbeats, diagnostics, watermark and summaries. Update `stage1_5f_live_depth_observer_storage.py` and `ScheduleRevisionRegistry.record_revision()` only to use the guard; preserve stream row content, revision identity/status transitions and all request/admission/snapshot behavior. No writer may accept `guard=None` or direct-write as a compatibility fallback.
6. At configured cadence, reconcile and independently compact state/batch checkpoints. A failed reservation or reconciliation enters terminal-only write set then exits. Never continue polling or retry an `ENOSPC` loop.
7. Extend existing summary data/model additively with the Design section 8.1 fields; do not change summary decision, root contract, watermark schema or identity semantics.

**Step 3: Verify F.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

Expected: all existing launch/admission/runtime-gate tests remain green; new no-op/crash/terminal/compaction tests pass without network access.

**Out of scope:** changing anchor deadlines, schedule-revision application, depth request limit, exchange HTTP semantics, event admission semantics or watermark identity.

### Task 8: Stream 1.5G state physical-last reduction locally

**Design invariants:** `INV-10`, `INV-11`, `INV-12`, `INV-13`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- Use synthetic F fixture only if necessary.

**Step 1: Write RED integrity tests.**

Assert that:

1. a state JSONL stream with out-of-order/equal/missing timestamps uses the last successfully parsed physical line for every `event_symbol_id`, matching F loader and compaction.
2. a parse error remains the existing `jsonl_parse_error`/integrity blocker; review cannot pass because a malformed row was skipped or compacted away.
3. state review uses an iterator/stream map and does not call a generic full-list state loader; accepted/rejected/snapshot/manifest existing loaders remain unchanged.
4. old append-only and compacted physical-last state inputs yield equivalent latest-map/evidence decisions.

**Step 2: Implement the smallest state-only streaming path.**

Create a local state stream iterator/reducer in the existing reviewer module. It reads one line at a time, records parse diagnostics, overwrites the map entry on each valid physical row, then passes only that map to the unchanged integrity reducer. Remove timestamp+sequence ordering from the state latest decision. Do not broadly refactor other JSONL consumers, change decision policy or add VPS host detection.

**Step 3: Verify locally.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py -q
```

Expected: physical-last/reviewer parse blocker tests pass; no production server command is run.

**Out of scope:** streaming accepted/snapshot/manifest streams, 1.5G decision criteria, output schema, or automated server refusal.

### Task 9: Prove write-surface closure, update the local-only runbook, and run complete verification

**Design invariants:** `INV-01` through `INV-14`.

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5_storage_guard.py`
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

**Step 1: Add the static scope test before editing the runbook.**

Add an AST/source-level test that inventories the exact D/F new-root persistent writer callsites in:

```text
run_stage1_5d_live_event_source_smoke_collector.py
run_stage1_5f_live_depth_observer.py
stage1_5d_live_event_source_storage.py
stage1_5d_detail_retry_scheduler.py
stage1_5d_runtime_gate.py
stage1_5f_live_depth_observer_state.py
stage1_5f_live_depth_observer_storage.py
stage1_5f_live_depth_observer_watermark.py
stage1_5f_schedule_revision_registry.py
```

The test must fail when a runner directly reaches an unguarded `append_jsonl`, `open(..., write mode)`, `Path.write_text`, `Path.replace`, `json.dump` or `os.replace` persistent path. It must also fail when any production persistence function in this matrix declares `storage_guard=None`, an `Optional` guard, a defaulted guard or a branch that writes when guard is absent. Low-level filesystem primitives may exist only inside the guard's named write implementation or a named helper whose signature requires `storage_guard` before finalization; direct runner bypasses are forbidden. The test must map every callsite to exactly one of the three table classes and reject an unknown/missing class. It must not inspect or reformat unrelated repository files.

Name the closure regressions `test_runner_has_no_guardless_persistent_writer_callsite` and `test_no_storage_helper_contains_guard_none_direct_write_fallback`.

**Step 2: Update only the affected runbook sections.**

In the D/F deployment/check documentation:

1. retain Git exact-commit checkout, new-root isolation, no `rsync --delete`/destructive cleanup;
2. add startup preflight: host free space at least `8GiB`, no old root reuse, expected D/F root caps and guard fields;
3. add concise checks for `storage_guard_status`, `storage_free_bytes`, `storage_root_bytes`, `storage_root_max_bytes`, `storage_blocker`, `storage_root_scanned_at_ms`, terminal peak and emergency reserve;
4. specify stop conditions: any non-`ready` status, non-ready D runtime gate, `block_new_event_admission=true`, root cap breach, malformed checkpoint blocker or missing terminal evidence;
5. remove VPS 1.5G execution commands. Provide only non-mutating minimal-root `rsync`/checksum verification to the local workstation, followed by local-only 1.5G command. The local review must not write to D/F root;
6. do not provide producer enablement, live-trading, root deletion or server-side 1.5G commands.

Add a focused static negative test that extracts the VPS/server/tmux sections and rejects `review_stage1_5g_live_depth_evidence.py` there, while requiring that command only in the clearly marked local-workstation/read-only section. Validate shell snippets with `bash -n` using an extracted temporary script or a focused existing deployment-checklist test; never execute mutating server operations during this Task.

**Step 3: Run the bounded complete verification suite.**

Before the suite, fail if Task 0's `CONFIG_BASELINE_PATH` or `PREEXISTING_UNTRACKED_PATHS` is unavailable. They are execution provenance, not repository artifacts. Extend the storage-guard test with `test_host_emergency_reserve_covers_actual_d_plus_f_peaks`, using the byte lengths generated by the real D and F maximum terminal artifact builders from Tasks 6 and 7: the `12MiB` host emergency reserve must cover their two ordered actual peaks, not synthetic surrogate rows.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q

ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5_storage_guard.py \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py \
  src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py \
  src/research/external_signal_shadow/stage1_5d_runtime_gate.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py \
  src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py

git diff --check "$BASE_SHA"
python3 - "$CONFIG_BASELINE_PATH" configs/base.py <<'PY'
import ast
from collections import Counter
import pathlib
import sys

baseline = ast.parse(pathlib.Path(sys.argv[1]).read_text())
current = ast.parse(pathlib.Path(sys.argv[2]).read_text())
allowed = {
    "EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5_HOST_RUNTIME_PROTECTED_RESERVE_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5_HOST_ORDINARY_CONTROL_PLANE_RESERVE_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5D_ROOT_MAX_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5D_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5D_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5D_RAW_PAYLOAD_ROOT_MAX_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5F_ROOT_MAX_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5F_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5F_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES",
    "EXTERNAL_SIGNAL_STAGE1_5_ROOT_RECONCILIATION_SCAN_INTERVAL_SEC",
    "EXTERNAL_SIGNAL_STAGE1_5F_CHECKPOINT_COMPACT_INTERVAL_SEC",
    "EXTERNAL_SIGNAL_STAGE1_5F_CHECKPOINT_COMPACT_THRESHOLD_BYTES",
}
def target(node):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None
extra = [node for node in current.body if target(node) in allowed]
stripped = [node for node in current.body if target(node) not in allowed]
assert ast.dump(ast.Module(body=baseline.body, type_ignores=[]), include_attributes=False) == ast.dump(ast.Module(body=stripped, type_ignores=[]), include_attributes=False)
counts = Counter(target(node) for node in extra)
assert counts == Counter({name: 1 for name in allowed}), counts
PY
python3 - "$PREEXISTING_UNTRACKED_PATHS" <<'PY'
import subprocess
import sys

before = set(open(sys.argv[1]).read().splitlines())
after = set(subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], text=True).splitlines())
allowed_new_files = {
    "src/research/external_signal_shadow/stage1_5_storage_guard.py",
    "tests/research/external_signal_shadow/test_stage1_5_storage_guard.py",
    "docs/designs/2026-08-13-external-signal-shadow-lab-stage1-5d-1-5f-1-5g-storage-lifecycle-resource-guard-hotfix-design_CN.md",
    "docs/plans/2026-08-13-external-signal-shadow-lab-stage1-5d-1-5f-1-5g-storage-lifecycle-resource-guard-hotfix-implementation-plan_CN.md",
}
allowed_fixture_prefixes = (
    "tests/fixtures/external_signal_shadow/stage1_5d/storage_lifecycle/",
    "tests/fixtures/external_signal_shadow/stage1_5f/storage_lifecycle/",
)
unexpected = {
    path for path in after - before
    if path not in allowed_new_files and not path.startswith(allowed_fixture_prefixes)
}
assert not unexpected, sorted(unexpected)
PY
python3 - "$BASE_SHA" <<'PY'
import subprocess
import sys

allowed = {
    "configs/base.py",
    "src/research/external_signal_shadow/stage1_5_storage_guard.py",
    "src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py",
    "src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py",
    "src/research/external_signal_shadow/stage1_5d_runtime_gate.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py",
    "src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py",
    "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py",
    "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py",
    "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py",
    "tests/research/external_signal_shadow/test_stage1_5_storage_guard.py",
    "tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py",
    "tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py",
    "tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py",
    "tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py",
    "docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md",
}
prefixes = (
    "tests/fixtures/external_signal_shadow/stage1_5d/storage_lifecycle/",
    "tests/fixtures/external_signal_shadow/stage1_5f/storage_lifecycle/",
)
changed = set(subprocess.check_output(["git", "diff", "--name-only", sys.argv[1]], text=True).splitlines())
unexpected = {path for path in changed if path not in allowed and not path.startswith(prefixes)}
assert not unexpected, sorted(unexpected)
print("scoped_changed_paths=OK", len(changed))
PY
git diff --name-only "$BASE_SHA"
rg -n "RISK_LIVE_TRADING_ENABLED\s*=\s*True|EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED\s*=\s*True" configs/base.py
```

Expected: all listed tests, including the three read-only formal/parser/runtime-gate compatibility regressions, and scoped Ruff pass. The AST comparator proves that only the named new storage constants were added exactly once, the untracked comparison attributes no pre-existing untracked path to this work, `git diff --name-only` is a subset of this Plan's exact allowed paths, and final grep has no output. A failure in a read-only compatibility regression is a stop condition, not permission to alter its unchanged production contract. Do not run `ruff --fix`.

**Step 4: Completion audit gate.**

Before any completion claim, commit or deployment recommendation, run `.agent/skills/audit-plan-completion` against:

```text
BASE_SHA
Plan SHA-256 recorded in section 1.2
the approved Design SHA-256 recorded in section 1.2
the exact Allowed Change Scope above
all invariant-to-task evidence and verification output
```

Only an independent `complete` verdict permits a user decision about commit/deployment. `incomplete` or `blocked` must use `.agent/workflows/remediate-completion-audit.md`; no direct opportunistic fix.

**Out of scope:** deployment execution, server process restart, retention cleanup, evidence archive management and schedule-revision producer enablement.

## 8. Task Order and Non-Overlapping Batches

1. `Task 0` is read-only and establishes evidence/inventory.
2. `Task 1` creates `stage1_5_storage_guard.py` before any production code imports it, satisfying the new-module prerequisite.
3. `Task 2` changes D raw persistence in isolation.
4. `Task 3` changes checkpoint persistence/malformed handling before the runner consumes its result.
5. `Task 4` changes only source semantic replay classification; `Task 5` changes only watermark write plumbing.
6. `Task 6` wires D complete write surface; `Task 7` wires F/recovery/summary after its primitives are tested.
7. `Task 8` changes local reviewer state reduction after F's physical-last comparator is fixed.
8. `Task 9` proves closure, updates the only approved operational document, and performs final bounded verification.

Tasks 2 and 3 may be implemented in separate isolated worktrees after Task 1 is green, but they must not be merged or combined with Task 6/7 until their focused tests pass. No task has a per-task commit instruction; user controls commits.

## 9. Explicit Non-Goals and Acceptance Boundary

This Plan is complete only when a new root would start fail-closed below the configured storage thresholds, all named persistent writers are guarded, checkpoint/raw replay no longer grows proportionally to poll count, local 1.5G reads state stream physical-last without full list materialization, and the full bounded suite passes.

It does **not** prove a 7-day production capacity result, alpha, execution feasibility, live/paper trading safety, a Clean 1.5G evidence pass, or schedule-revision producer enablement. Production deployment remains a separate user-approved operation after the completion audit.

## 10. Plan Review Checklist

```text
[ ] Allowed Change Scope contains only Design-approved files and every category.
[ ] Every INV-01..INV-14 maps to a concrete task and executable evidence.
[ ] The write-surface matrix has Normal / Ordinary Control Plane / Terminal Control Plane columns.
[ ] Task 1 creates the guard module before any runner wiring.
[ ] Static writer-closure test covers all new-root persistent D/F writer callsites.
[ ] Checkpoint malformed rows fail closed and cannot be erased by compaction.
[ ] Compaction second pass is incremental and reserves exact candidate bytes.
[ ] D path uses only full-SHA `.bin`, and actual raw directory has independent root budget.
[ ] F fingerprint inclusion/exclusion property tests and full batch/watermark crash matrix are present.
[ ] 1.5G physical-last stream is local-only; no VPS execution command survives in runbook.
[ ] No task enables producer/trading, mutates old evidence, uses destructive cleanup, or invokes full-repo autofix.
[ ] Implementation is blocked until plan review `Approve` and explicit user approval.
```
