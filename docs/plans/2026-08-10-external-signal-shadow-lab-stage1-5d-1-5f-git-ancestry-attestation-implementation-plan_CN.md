# Stage 1.5D/1.5F Git Ancestry Attestation Implementation Plan

**日期：** 2026-08-10
**状态：** draft，待 implementation-plan review 与用户批准
**关联 Design：** [2026-08-10 Stage 1.5D Schedule Revision Producer Git Ancestry Attestation Design](../designs/2026-08-10-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-git-ancestry-attestation-design_CN.md)

> **For Codex:** 执行时使用 `.agent/workflows/execute-approved-plan.md`。本计划未获用户明确批准前，不得修改生产代码、配置或部署环境。

**Goal：** 用 Git ancestry、受保护代码/config proof、同一 Stage 1.5D root 绑定和运行期 sticky latch 替代 self-referential SHA equality gate，同时保持 schedule revision producer 默认关闭。

**Architecture：** Stage 1.5D runner 在启动时冻结完整静态证明，在每个 poll 的 formal revision emission 前做有 1 秒总预算的轻量 drift 检查；任何本地 runtime failure 都 sticky disable。Stage 1.5F 使用既有 root contract 和 summary 发布自身 startup/runtime proof，并证明其 events glob 与 runtime gate 都来自当前 Stage 1.5D output root；Stage 1.5D 仅在读取到同 root、同 commit、同 consumer process 的 fresh proof 时允许 future enablement。

**Tech Stack：** Python standard library `ast` / `hashlib` / `json` / `pathlib` / `subprocess` / `uuid`、Git CLI、pytest、Graphify（只作拓扑发现）。

---

## Allowed Change Scope

Allowed implementation paths:
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`

Allowed verification paths:
- `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- `tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`
- `tests/scripts/external_signal_shadow/test_stage1_5f_deployment_checklist.py`

Allowed documentation paths:
- `docs/reviews/2026-08-10-external-signal-shadow-lab-stage1-5d-1-5f-git-ancestry-attestation-deployment-checklist_CN.md`
- `docs/roadmap.md`

Allowed generated/runtime artifacts:
- `graphify-out/**` generated only by `graphify update . --code-only`; inspect but do not commit unless the user explicitly asks.
- `data/external_signal_shadow/**` generated only during a later read-only deployment; never commit as part of this plan.

Affected but unchanged:
- `configs/base.py`
  - compatibility evidence: producer flag remains `False`; no threshold or operator config key changes in this plan.
- `src/risk/limits.py`
  - compatibility evidence: `RiskLimits.live_trading_enabled` remains false and is checked by the new proof.
- `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`
  - compatibility evidence: Task 1 asserts current producer revision contract is v2; no transport schema change.
- `src/research/external_signal_shadow/stage1_5_launch_event_contract.py`
  - compatibility evidence: formal launch-event schema is unchanged; runner regressions remain green.
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
  - compatibility evidence: offline 1.5G code is protected by the manifest only and receives no schema change.
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py`
  - compatibility evidence: do not change generic `write_json`; use a runner-local atomic summary writer.
- `docs/reviews/2026-08-07-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-deployment-checklist_CN.md`
  - compatibility evidence: retain as historical operational record; the new checklist supersedes its attestation section without rewriting history.

Forbidden:
- Any mutation outside the allowed paths.
- Any change to `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED`, Part A flags, real-fixture flags, lookback, retry/fairness/anchor thresholds, or `RISK_LIVE_TRADING_ENABLED`.
- Any change to revision classifier/linking/index, formal revision JSONL schema, Stage 1.5G logic, snapshot collection semantics, or trading permissions.
- Full-repository autofix/formatting such as `ruff check --fix .`, `ruff format .`, or equivalent.
- Unscoped destructive cleanup such as `git clean -fdx`, `rm -rf data/`, reset, checkout, or reversion of pre-existing user changes.
- Runtime data commit, producer enablement, server deployment, or new external dependency.

---

## Preconditions And Execution Baseline

1. This plan implements Design invariants `INV-A1` through `INV-A15`; it does **not** prove a real Binance postponement/revision sample and it does **not** authorize producer enablement.
2. Before code changes, record the immutable execution baseline. Preserve every pre-existing dirty/untracked item as external provenance; never overwrite or revert it.

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export BASE_SHA="$(git rev-parse HEAD)"
export PLAN_PATH="docs/plans/2026-08-10-external-signal-shadow-lab-stage1-5d-1-5f-git-ancestry-attestation-implementation-plan_CN.md"
export PLAN_SHA256="$(python3 - <<'PY'
import hashlib
from pathlib import Path
print(hashlib.sha256(Path('docs/plans/2026-08-10-external-signal-shadow-lab-stage1-5d-1-5f-git-ancestry-attestation-implementation-plan_CN.md').read_bytes()).hexdigest())
PY
)"
printf 'BASE_SHA=%s\nPLAN_SHA256=%s\n' "$BASE_SHA" "$PLAN_SHA256"
git status --short --untracked-files=all
```

Expected: `BASE_SHA` and `PLAN_SHA256` are recorded. Pre-existing provenance may include the approved Design, this approved Implementation Plan, `_project_context/`, and explicitly recorded user files. Any pre-existing path overlapping a mutable Allowed Change Scope path requires explicit provenance review before implementation; do not assume this Plan is the only untracked artifact.

3. Run targeted topology confirmation before editing. The current direct callers are the two runners and their named tests; re-run and compare against source before changing signatures or JSON fields.

```bash
graphify query 'build_schedule_revision_producer_attestation'
graphify query 'write_observer_root_contract_atomically'
graphify query 'validate_stage1_5d_runtime_gate'
graphify query 'derive_stage1_5d_root_from_events_glob'
graphify query 'build_stage1_5d_runtime_gate'
rg -n 'schedule_revision_producer_|consumer_root_contract_sha256|consumer_runtime_manifest_sha256|stage1_5d_output_root_id|source_stage1_5d_' \
  scripts/external_signal_shadow src/research/external_signal_shadow tests
```

Expected: no additional verified consumer is omitted. If a source consumer of a changed field/function is discovered, add it to scope and return to plan review before implementation.

---

## Invariant To Task Mapping

| Design invariant | Implementation task | Primary evidence |
|---|---|---|
| `INV-A1`–`INV-A7` (including `INV-A2`) | Tasks 2–3 | runner-derived startup identity; temporary SHA-1 repositories; literal-only AST delta tests |
| `INV-A6`–`INV-A7` | Tasks 2–3 | dirty/untracked/ignored Python, static closure, module-path tests |
| `INV-A8`, `INV-A14`, `INV-A15` | Tasks 4–6 | root/summary source-root binding and canonical hash integration tests |
| `INV-A9` | Tasks 3 and 5 | D/F sticky-latch restart tests |
| `INV-A10`–`INV-A13` | Tasks 1, 3, 6, 8 | disabled default, revision-only fail-closed, no execution permission regression |

---

## Task 1: Lock Current Contract And Safety Baseline

**Design invariants:** `INV-A10`–`INV-A13`
**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Affected but unchanged: `configs/base.py`, `src/risk/limits.py`, `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`

1. Before changing production source, add and run a narrow **pre-change baseline** assertion that imports the current contracts and asserts:
   - `FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION == 2`.
   - `build_formal_schedule_revision_row(...)` emits version `2`.
   - the baseline `write_observer_root_contract_atomically(output_root: str, root_mode: str, reason: str = "")` signature has exactly those three parameters and advertises formal event version `2` and revision compatibility `[1, 2]`.
   - `base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is False` and `RiskLimits.live_trading_enabled is False`.
2. Run the pre-change assertion first; it must pass against the current code. Task 4 must replace this baseline-only exact-count assertion with the final compatibility regression: the first three positional parameters and defaults are unchanged; every added parameter is keyword-only and defaulted; no variadic parameter is accepted. A baseline failure means the Design's current-code premise is wrong: stop rather than adapting production behavior.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k 'revision_contract_version or root_contract or producer_attestation' -q
```

Expected: all selected tests pass; this task changes no production source.

## Task 2: Implement Stage 1.5D Startup Static Git/Config Proof

**Design invariants:** `INV-A1`–`INV-A7`, `INV-A13`
**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Affected but unchanged: `configs/base.py`, `src/risk/limits.py`

1. Write failing tests using a temporary local SHA-1 Git repository. Cover:
   - valid proof commit `A` plus config-only descendant `B` that changes only the four approved literal RHS values;
   - invalid/missing/non-ancestor SHA, SHA-256 repository, shallow repository, wrong worktree root, missing/non-blob manifest path. Build shallow fixtures only with `file://` local clones; test SHA-256 rejection through the runner-local Git-command adapter, and additionally use a real `git init --object-format=sha256` fixture only when the installed Git supports it;
   - `configs/base.py` AST changes: `bool("false")`, `os.getenv`, name/call/attribute/subscript, duplicate, deleted, added, moved, annotated, multi-target, tuple-target and unrelated threshold/risk changes;
   - final tree semantics: a protected file changed then restored to exactly `A` passes, while a final content difference fails;
   - static local import closure missing a manifest item, relative import omission, or any non-allowlisted dynamic import construct fails.
2. Add runner-local, standard-library-only helpers. Do not create a new `src/` attestation module or a factory/interface:
   - derive repository root from the runner path only;
   - invoke Git with `shell=False`, bounded timeout, `cwd=repo_root`, and `GIT_NO_REPLACE_OBJECTS=1`. Apply one shared `time.monotonic()` deadline across the whole 10-second startup proof rather than giving each subprocess an independent full timeout;
   - verify normal SHA-1 non-shallow repository, commit objects, `merge-base --is-ancestor`, manifest blobs at `A`/`B`, and final `git diff --quiet A B -- manifest`;
   - parse historical `configs/base.py` with `ast`; find exactly one top-level `ast.Assign` at the same `body` index for each approved field; require literal type/value domain; normalize only the four RHS nodes and compare the complete normalized module AST;
   - define the Design-approved `PROTECTED_TREE_MANIFEST` for A-to-B equivalence, the separate `CONSUMER_RUNTIME_MANIFEST` expected from F, and the D producer critical-module path map. The D gate publishes the protected-tree hash; D compares the consumer-manifest hash only with F's consumer-manifest hash. In tests, independently derive the static local import closure and assert that each runtime closure is manifest-complete; reject dynamic import constructs unless the explicit allowlist is empty. Do not build an import graph at runtime and do not create a manual subset that escapes the closure test.
3. Capture `startup_head_sha`, `startup_static_proof_verified`, `stage1_5d_output_root_id`, imported critical-module paths, and startup worktree result once in `main()`. The static proof value must never be recomputed within that process.
4. Run targeted RED/GREEN verification.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'attestation or ancestry or config_delta or manifest or dynamic_import or protected_tree' -q
```

Expected: temporary-repo edge cases pass; no network, fetch/deepen, config mutation, or producer enablement occurs.

## Task 3: Add Stage 1.5D Runtime Latch, Consumer Reader And Gate Metadata

**Design invariants:** `INV-A6`–`INV-A11`, `INV-A14`
**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`

1. Write failing tests for the reducer lifecycle:
   - `configured_enabled=False` always remains `DISABLED` and normal launch processing continues;
   - `configured_enabled=False` does not open, parse, stat, or otherwise read either supplied F artifact path;
   - no consumer paths before first arm is `BOOTSTRAP_WAITING_FOR_CONSUMER`, not compromised; exactly one supplied consumer artifact path is `prerequisites_unmet`; both paths are required and fully valid before first arm;
   - after arm, `HEAD B -> C -> B`, dirty-to-clean, ignored/untracked `.py` deletion, module-path repair or one timeout remains disabled until a process restart;
   - after arm, stale/missing/mismatched/restarted consumer proof sets the same sticky latch;
   - no code path searches `data/`, globs a Stage 1.5F root, selects by mtime, or falls back to another F summary; switching either explicit artifact path after arm sticky-compromises;
   - failed producer prerequisites emit only revision diagnostics while normal launch rows remain writable.
2. Add exactly two D CLI arguments: `--stage1-5f-consumer-root-contract` and `--stage1-5f-consumer-summary`, both defaulting to `""`. When producer configuration is false, never read either path. When configured and unarmed, both empty means `BOOTSTRAP_WAITING_FOR_CONSUMER`; one empty is invalid; both explicit paths are read only as the single candidate. Once armed, retain the exact resolved artifact paths and consumer root/process identities in memory; never auto-discover or replace them.
3. Implement process-local lifecycle state with monotonic semantics: `startup_head_sha` and `startup_static_proof_verified` are immutable; `producer_armed_once` and `runtime_attestation_compromised` may only change `False -> True`; `expected_consumer_root_id`, `expected_consumer_process_instance_id`, `expected_consumer_root_contract_path`, and `expected_consumer_summary_path` change only from `None` to their first successfully armed value and are never replaced in the same process. Do not persist this state to JSONL, a watermark, or config.
4. Before formal revision emission only, run lightweight checks under one shared 1-second aggregate `time.monotonic()` deadline: current HEAD equals startup HEAD; protected tracked worktree is clean; no normal or ignored untracked `.py` under the four Design directories; critical module files still resolve to expected repo paths. On any failure, latch false for the remainder of the process, write a diagnostic, and continue normal announcement/list/detail/launch handling.
5. Extend `build_stage1_5d_runtime_gate()` with the non-control `stage1_5d_output_root_id`, derived solely from resolved `output_root`. Preserve all existing gate fields and decision semantics.
6. Extend the D-side consumer reader to accept only the two explicit artifact paths and reject unreadable/corrupt root contract or summary, stale summary, root-contract hash mismatch, cross-artifact `consumer_root_id`, `consumer_startup_commit_sha`, or `consumer_runtime_manifest_sha256` mismatch, startup commit/manifest/capability mismatch, non-false admission blocker, missing/changed source Stage 1.5D root IDs, and post-arm consumer root/process/path identity changes. Add direct RED tests for each of those three cross-artifact equality failures. Freeze expected F root/process/paths only on the first successful arm.
7. Run targeted verification.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'runtime_gate or attestation or sticky or bootstrap or consumer or normal_launch' -q
```

Expected: runtime-gate remains READY for normal collection when producer prerequisites are unmet; no path can auto-re-arm after an in-process runtime failure.

## Task 4: Bind Stage 1.5F To Its Actual Stage 1.5D Input Root

**Design invariants:** `INV-A8`, `INV-A14`
**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py`

1. Write failing tests for:
   - events glob and runtime-gate `source_root` from different Stage 1.5D roots;
   - a gate file located outside `source_root/live_safety_gate_summary.json`;
   - same-root events/gate inputs producing three equal source-root IDs;
   - a healthy F root contract bound to D-B being rejected by D-A;
   - an E2 D restart at the same resolved output root preserving source-root binding.
2. Reuse `derive_stage1_5d_root_from_events_glob()` and `validate_stage1_5d_runtime_gate()`; extend their return data only as needed to expose the already validated resolved gate root and gate file. Do not add a new source module.
3. Add identical small runner-local canonical root-ID helpers in D/F using `Path(...).resolve()` and `hashlib.sha256(...encode("utf-8"))`. Cross-runner tests must prove equal resolved roots generate equal IDs; no operator-provided root ID is accepted.
4. Change `write_observer_root_contract_atomically()` through one explicit keyword-only, defaulted source-binding argument so the Task 1 positional signature remains compatible. Replace the Task 1 baseline-only exact-count assertion with a final regression asserting the first three positional parameters and defaults are unchanged and the new source-binding parameter is keyword-only and defaulted. It must write the three source Stage 1.5D root IDs and set `consumer_static_attestation_verified=False` if the binding/static proof is unavailable. This metadata failure must not add a new F admission block; it only blocks future producer arm. Preserve the existing `runtime_gate_root_mismatch` behavior, which already blocks new admission when F's actual events root and D runtime-gate root differ.
5. During E1 runtime startup, validate the explicit events glob and runtime-gate before publishing a `consumer_static_attestation_verified=True` contract. Do not rely on the old `os.path.dirname(events_glob)` fallback for producer arm.
6. Run targeted verification.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k 'runtime_gate_root or source_root or observer_root_contract or consumer_static' -q
```

Expected: a root mismatch remains blocked by the existing F runtime gate; an otherwise valid F run with incomplete attestation metadata has no newly introduced block but writes false static attestation. D cannot use either case to arm producer.

## Task 5: Publish Stage 1.5F Static/Runtime Proof Atomically

**Design invariants:** `INV-A8`, `INV-A9`, `INV-A15`
**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`

1. Write failing tests for both distinct canonical hashes:
   - protected-tree and consumer-runtime manifest hashes each change only with policy/path/newline content; D's expected consumer hash equals F's consumer hash, while the protected-tree hash is not substituted for it;
   - root-contract hash is insensitive to JSON key order/pretty print but changes when any attestation field changes;
   - root contract cannot contain its own hash; summary hash from another root is rejected;
   - D and F independently compute the same canonical root-contract hash from the same contract mapping, and D recomputes it rather than trusting the summary claim;
   - `consumer_process_started_at_ms > 0`, is no later than heartbeat, and heartbeat is at most 1 second in the future;
   - startup static proof requires F startup HEAD, clean protected consumer worktree, no untracked or ignored `.py`, complete consumer critical-module paths, and `RISK_LIVE_TRADING_ENABLED=False`;
   - before every heartbeat/poll summary, one shared 1-second `time.monotonic()` runtime deadline rechecks current HEAD equals startup HEAD, protected tracked worktree cleanliness, untracked/ignored `.py`, and consumer module paths. `HEAD B -> C -> B`, dirty-to-clean, normal/ignored Python add-then-remove, module-path mismatch-then-repair, or timeout all make `consumer_runtime_attestation_compromised=True` and `consumer_runtime_attestation_verified=False` until process restart;
   - fresh process restart generates a new UUID and can reverify after correction; an F runtime attestation failure does not block normal depth observation;
   - a reader never observes malformed/partial summary during a simulated atomic replacement.
2. In the existing F runner only, add standard-library helpers for the consumer-runtime manifest, canonical root-contract JSON, a UUID generated once per process, startup static proof, shared-deadline runtime revalidation, sticky latch, and a F-local atomic summary writer (`temp`, flush, close, `os.replace`; use `os.fsync` where supported). F does not repeat D's A-to-B ancestry/config-delta proof. Do not change generic `stage1_5f_live_depth_observer_storage.write_json`.
3. Add defaulted fields to `LiveDepthObserverSummary` and populate them through `build_live_depth_observer_summary()` so historical summaries remain readable via `from_dict()`:
   - consumer root/process/startup identity;
   - consumer manifest and root-contract hashes;
   - static/runtime proof and compromised latch;
   - existing heartbeat/admission/blocker values remain authoritative.
4. Update every F summary exit path and normal poll write to run the runtime revalidation then use the same atomic writer and immutable startup metadata. Root contract must omit its own hash and all mutable summary fields; summary carries `consumer_root_contract_sha256`. A failed F attestation updates proof fields/latch only and does not introduce a new F observation/admission block.
5. Run targeted verification.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py -q
```

Expected: old summary dictionaries deserialize, new roots expose complete proof metadata, F runtime compromise is sticky but leaves ordinary observation intact, and no summary write changes observation/trading decisions.

## Task 6: Wire E0/E1/E2 Consumer Proof Into Stage 1.5D Effective Enablement

**Design invariants:** `INV-A8`–`INV-A12`, `INV-A14`–`INV-A15`
**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

1. Add end-to-end temporary-root tests for the three-stage lifecycle:
   - E0: configured true, static D proof valid, both explicit F artifact paths absent -> `BOOTSTRAP_WAITING_FOR_CONSUMER`, `effective_enabled=False`, normal launch still works; only one path is invalid and no path is auto-discovered;
   - E1: F starts on the same commit and same D root -> root contract/summary are fresh, atomically readable and internally consistent;
   - E2: D restarts on the same output root -> only a complete matching F proof can arm it;
   - after E2: F process restart, root-contract/manifest/startup commit mismatch, source-root mismatch, stale heartbeat, admission block, or blocker -> sticky D compromise and revision-only fail-closed;
   - producer config false -> D does not require/read F proof and preserves present deployment behavior.
2. Wire the two explicit D CLI artifact paths and D reader into the existing `build_schedule_revision_producer_attestation()` call path without changing `process_trusted_schedule_revision_detail()` or formal revision row fields. Recompute only the allowed lightweight runtime proof at poll time; never re-run the complete startup proof.
3. Assert the runtime gate emits attestation policy, protected manifest hash and self output-root ID; F root contract/summary expose the matching source/consumer proof fields. Existing 1.5F JSONL input/output schemas and 1.5G inputs remain unchanged.
4. Run the cross-runner suite.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py -q
```

Expected: proof failure never prevents normal launch collection or F's observation loop; it only prevents formal revision emission.

## Task 7: Add Deployment Evidence And Historical Version Decision

**Design invariants:** `INV-A10`–`INV-A15`
**Files:**
- Create: `docs/reviews/2026-08-10-external-signal-shadow-lab-stage1-5d-1-5f-git-ancestry-attestation-deployment-checklist_CN.md`
- Modify: `docs/roadmap.md`
- Modify: `tests/scripts/external_signal_shadow/test_stage1_5f_deployment_checklist.py`

1. Create a compact deployment checklist with two explicitly separated sections:
   - **Section A: current disabled deployment.** Producer configuration stays false, no F consumer proof requirement, and all runnable commands are non-mutating checks only (`git status`, `git rev-parse`, targeted JSON reads, `ps`, `tmux`, `find`/`test`).
   - **Section B: future enablement reference.** Describe the required E0/E1/E2 ordering, the same-root fields to verify, the required explicit `--stage1-5f-consumer-root-contract` and `--stage1-5f-consumer-summary` inputs in E2, and stop conditions. Do not include runnable start, restart, config-enable, or producer-enable commands; those belong only to a future separately approved enablement plan.
2. Do not include `exit` in shell snippets and do not instruct deletion, rsync, force reset, producer enablement, or live trading.
3. Add a roadmap decision-log entry: current schedule revision producer emits v2; v1 is historical compatibility; consumer accepts `[1, 2]`; this hotfix remains producer-disabled until a separate real-fixture enablement decision.
4. Extend the deployment-checklist regression to check the new document exists, uses unescaped `events/*.jsonl`, contains E0/E1/E2 and source-root checks, keeps runnable commands in the disabled section only, and has no literal `exit` command.
5. Validate docs and narrow tests.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_stage1_5f_deployment_checklist.py -q
rg -n 'TODO|TBD|placeholder|events/\\\*\.jsonl|^exit$' \
  docs/reviews/2026-08-10-external-signal-shadow-lab-stage1-5d-1-5f-git-ancestry-attestation-deployment-checklist_CN.md
```

Expected: tests pass and `rg` returns no prohibited deployment-command content.

## Task 8: Bounded Verification, Topology Refresh And Completion Audit

**Design invariants:** all
**Files:** no production or documentation edits unless a failing scoped test proves one is necessary.

1. Re-check the exact Allowed Change Scope and inspect the diff against the recorded baseline. Stop if any out-of-scope code/config/runtime artifact changed.

```bash
git diff --name-only "$BASE_SHA"
git status --short --untracked-files=all
git diff --check "$BASE_SHA"
```

2. Run the complete targeted suite:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/scripts/external_signal_shadow/test_stage1_5f_deployment_checklist.py -q

.venv/bin/ruff check \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5d_runtime_gate.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py
```

Expected: all pass. A 1.5G integrity pass proves only backward-compatible parsing/lineage handling, not producer enablement or alpha.

3. Run narrow static safety checks and refresh topology using the code-only mode. Do not use an autofix command.

```bash
rg -n 'RISK_LIVE_TRADING_ENABLED\s*=\s*True|live_trading_allowed\s*=\s*True|paper_trading_allowed\s*=\s*True|execution_engine_allowed\s*=\s*True' \
  scripts/external_signal_shadow src/research/external_signal_shadow configs/base.py
graphify update . --code-only
graphify query 'build_schedule_revision_producer_attestation'
graphify query 'write_observer_root_contract_atomically'
```

Expected: the safety grep returns no new true assignment in the scoped code; Graphify direct callers match the plan scope. `graphify-out/**` is generated evidence only and remains uncommitted unless explicitly approved.

4. Invoke `.agent/skills/audit-plan-completion/SKILL.md` with `BASE_SHA`, this Plan SHA-256, the Allowed Change Scope, task-to-invariant mapping and actual command output. Completion requires verdict `complete`; `incomplete` or `blocked` must enter `.agent/workflows/remediate-completion-audit.md`.

---

## Stop Conditions

Stop implementation and return to Design review if any of the following occurs:

1. A required manifest/critical module is dynamically imported or an actual consumer requires a schema/semantic change outside this plan.
2. D/F cannot publish/consume the required proof without changing formal revision JSONL, 1.5G semantics, observation timing, or a risk/trading permission.
3. A static proof cannot be completed within the 10-second startup budget, or the lightweight poll checks cannot stay within the 1-second aggregate budget in local tests.
4. Any test reveals that normal launch collection is blocked by producer proof failure.
5. The workspace contains a pre-existing modified path that overlaps an Allowed Change Scope path and its provenance cannot be separated safely.

## Completion Boundary

This plan can prove that a future configured producer has a bounded, fail-closed Git/config/runtime/consumer proof path and that default D/F observation remains safe. It cannot prove a real revision event's linkage correctness, a producer enablement approval, live/paper trading safety, alpha, or execution feasibility. The only allowed next decision after a complete implementation audit is **deploy with producer still disabled and collect real revision evidence**.
