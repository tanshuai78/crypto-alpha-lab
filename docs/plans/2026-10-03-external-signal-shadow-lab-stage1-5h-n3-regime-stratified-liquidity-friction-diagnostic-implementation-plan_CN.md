# Stage 1.5H N=3 产品机制分层流动性摩擦诊断 Implementation Plan

## 1. Authority 与执行边界

本 Plan 仅实施已批准 Design 的确定性、只读、描述性 Stage 1.5H N=3 diagnostic。它不授权生成 production receipt、网络、SSH、replay、Alpha、信号、execution、paper/live、commit、push 或 deployment。

| authority | 固定值 |
| --- | --- |
| Approved Design | `docs/designs/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-design_CN.md` |
| Approved Design SHA-256 | `edc2dd3348fbf86f233ae4d236ed8202e69fc659a80d4a2b4376a0f7931d86a2` |
| Reviewed planning base SHA | `9484dd3eedbc10a2edd4a2ded46a1ecc2ab54e91` |
| Frozen N=3 receipt root | `data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z` |
| N=3 manifest / summary / review SHA-256 | `f3b4c76683fe7e1e4a7f28f30437f289f036f6ffc6126f8e9693faad62789adf` / `c92686b4834ee41165850aba99b1b68254b05a4afaf37d5e2789747db60ca941` / `df6e12df8b1d105c62dd8cb01baeb0f858aa008c42488f699999a3b9ba51f2dc` |

实施者在 Task 0 从用户的 Plan 实施批准语句取得 `<APPROVED_PLAN_SHA256>`；该值随后是唯一合法 attempt bundle locator：

```text
.git/plan-execution/stage1_5h_n3_regime/<APPROVED_PLAN_SHA256>/
```

Task 0 必须要求 `git rev-parse HEAD` 精确等于 reviewed planning base SHA；`BASE_SHA` 只能写入该字面值，不能以执行开始时的任意 HEAD 替代。任何 Design/Plan 字节、审批文本、bundle sidecar、`HEAD`、基线 ledger 或 scope 不匹配均为 `STOP=approved_authority_mismatch`。不得重建、替换或 rebaseline Task 0 证据。

实施 authority bundle 是 create-once 的固定 contract；已存在的 bundle、任一必需文件缺失、symlink、非 regular file 或 byte 不符均 STOP，不得覆盖。它只包含以下 authority files，其他 Task evidence 可在 create-once 成功后附加：

```text
implementation_authorization.txt
implementation_authorization.sha256
execution_authority.json
execution_authority.sha256
base_sha
```

`implementation_authorization.txt` 必须是下列 exact two-line UTF-8 bytes，末尾恰好一个 LF：

```text
我批准实施 Plan：<APPROVED_PLAN_REL_PATH>（SHA-256: <APPROVED_PLAN_SHA256>）。
允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。
```

其 sidecar 必须恰为 `<SHA256>  implementation_authorization.txt\n`。`execution_authority.json` 必须是 `canonical_json_dumps` 的 UTF-8 bytes，且 key set 恰为 `approved_design_path`、`approved_design_sha256`、`approved_plan_path`、`approved_plan_sha256`、`base_sha`、`current_plan_sha256`、`project_root`；值必须绑定本 Design、本 Plan、`base_sha == reviewed planning base SHA`、`current_plan_sha256 == APPROVED_PLAN_SHA256` 与 `project_root == resolved project root`。其 sidecar 恰为 `<SHA256>  execution_authority.json\n`；`base_sha` 是 40 个 ASCII lowercase hex bytes、无额外字节。

本 Plan 的实施成功只表示代码和测试可移交独立审计；不表示 `COMPLETE`，更不表示生成 receipt 或研究/交易权限。

## Allowed Change Scope

Allowed implementation paths:

```text
src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
scripts/external_signal_shadow/run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
```

Allowed verification paths:

```text
tests/research/external_signal_shadow/test_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
tests/scripts/external_signal_shadow/test_run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
```

Allowed documentation paths: `none`. The approved Design and approved Plan are immutable authorities, not execution targets.

Allowed generated/runtime artifacts:

```text
.git/plan-execution/stage1_5h_n3_regime/<APPROVED_PLAN_SHA256>/**
```

This bundle is implementation evidence only. It must not contain a local generation authority and must not create any receipt or `data/` runtime artifact.

Affected but unchanged / immutable authorities:

```text
docs/designs/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-design_CN.md
docs/plans/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-implementation-plan_CN.md
src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
src/research/external_signal_shadow/safety.py
configs/base.py
src/research/external_signal_shadow/stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py
scripts/external_signal_shadow/run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py
data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/
data/external_signal_shadow/local_evidence/
data/external_signal_shadow/stage1_5g/reviews/
```

Forbidden:

```text
data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/**
graphify-out/**
receipt_generation_authorization.txt and its sidecar
all mutation outside the paths above, unrelated formatter/refactor, commit, push, deployment, SSH, network, replay, execution, paper or live action
```

The immutable baseline, not this Plan, determines whether each authority is tracked, untracked or dirty. Every authority byte must match its approved hash and remain byte-identical.

## No-Touch Set

The following list duplicates the affected-but-unchanged authority boundary for Task execution:

```text
src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
src/research/external_signal_shadow/safety.py
configs/base.py
src/research/external_signal_shadow/stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py
scripts/external_signal_shadow/run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py
data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/
data/external_signal_shadow/local_evidence/
data/external_signal_shadow/stage1_5g/reviews/
docs/designs/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-design_CN.md
docs/plans/2026-10-03-external-signal-shadow-lab-stage1-5h-n3-regime-stratified-liquidity-friction-diagnostic-implementation-plan_CN.md
```

不得创建 `data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/`，不得创建 `receipt_generation_authorization.txt` 或其 sidecar。若正确实现需要触碰 No-Touch set 或需要真实 receipt，停止并路由 `STOP=BLOCKED_SCOPE_DRIFT`；若 frozen upstream 与 Design 不可调和，停止并提交 Rule-12 Evidence Packet，路由 `STOP=BLOCKED_SPEC_DRIFT`。

## Frozen Producer/Consumer Topology

新 core 必须只消费以下 verified producers：

```text
N=3 receipt strict loader:
  stage1_5g_n3_regime_stratified_admission.load_verified_n3_receipt(default behavior)

Stage 1.5G source re-admission:
  stage1_5g_live_depth_evidence_review.load_stage1_5g_inputs()
  stage1_5g_live_depth_evidence_review.build_stage1_5g_review_summary()

Canonical serializer:
  safety.canonical_json_dumps()
```

The new H module is the only reducer/writer/loader. There is no downstream consumer. It must not import the old N=2/H V3 diagnostic as data source, call a script from `src`, parse BAPI payloads, read raw events/depth JSONL, glob roots, or create a generic consumer/registry/configuration extension point.

The four runtime bindings are rechecked by path, `__file__`, `__spec__.origin`, resolved project containment and SHA-256 both before and after import:

```text
src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission
src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review
src.research.external_signal_shadow.safety
configs.base
```

Expected source bytes are, respectively:

```text
e64abe50b97d5cea303552c59f8f8f98168297ab0cabadfb554de9c1340c0c3d
596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d
1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d
414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4
```

## 3. Invariant-to-task map

| Design edge | Implementation owner | Mechanical proof | Fail-closed result |
| --- | --- | --- | --- |
| Approved Design/Plan and generation authority are separate | core + CLI | exact approval text/sidecar and five-line generation record mutations | `STOP=approved_authority_mismatch` or `STOP=local_receipt_generation_not_authorized` before import/source/staging |
| Fixed N=3 lineage | core re-admission | strict N=3 loader plus frozen receipt hash mutation | input/receipt integrity STOP |
| Source root provenance and exact stored/recomputed projections | core comparator | canonical upstream fixture; one-field stored/recomputed mutation | source authority mismatch STOP |
| CT-only projection and Batch7 duplicate identity | core reducer | CT missing/ninth/non-CT selection/duplicate mutation | identity mismatch STOP |
| Regime separation | reducer + strict loader | extra pooled key, wrong parent membership, wrong anchor hash | summary/lineage integrity STOP |
| Exact summary/manifest/Markdown | serializer + strict loader | canonical-byte, key-set, byte-count, hash, Markdown mutation | publication integrity STOP |
| Symlink-free atomic lifecycle | private lifecycle helper/state classifier | root/ancestor/artifact symlink, foreign staging, crash failpoint, collision tests | `corrupt_or_unknown` or publication STOP; never success |
| Permission isolation | CLI + AST/open spy tests | forbidden flag/import/open/source/output override tests | argument parse error or authority STOP |

## 4. Task 0: Immutable Baseline and Authority Capture

**Files:** only the Plan execution bundle. No source, test or data output is created.

1. Verify the approved Design path/SHA and require `git rev-parse HEAD == 9484dd3eedbc10a2edd4a2ded46a1ecc2ab54e91` before inspecting inputs. Write exactly that value to `base_sha`; every later Task starts and ends with `HEAD == base_sha`. Any different HEAD is `STOP=approved_authority_mismatch`, not a new baseline.
2. Create the canonical bundle with non-overwriting creation only. Before source/test work, require the exact authority files and byte grammars from §1: implementation approval text/sidecar, canonical authority JSON/sidecar and literal `base_sha`. The implementation validator must reject alternate sidecar names, extra/missing JSON keys, parent/leaf symlink, wrong resolved project root, wrong Design/Plan path/SHA, or a pre-existing bundle. It must not accept a self-defined variant of this contract.
3. Preserve complete pre-existing state: `git status --short --untracked-files=all`, `git diff --binary`, `git diff --cached --binary`, `git ls-files -s`, tracked/untracked path ledger and SHA-256 inventory. Record each approved Design/Plan's actual `tracked`/`untracked`/`dirty` state without assuming one. Empty output is recorded as an observed empty result, never silently interpreted as success.
4. Capture exact SHA-256 for the approved Design, N=3 receipt three artifacts, four frozen modules, three source `SHA256SUMS`, and three stored Stage 1.5G summaries. Strict-load the N=3 receipt using the actual frozen loader before any future test fixture refers to it.
5. Run targeted topology discovery and persist both output and exact `rg` return code. Only `0` and `1` are valid; `>1` stops:

```bash
set +e
rg -n 'stage1_5h_n3_regime|n3_regime_stratified|stage1_5h_v3|stage1_5g_n3_regime|load_verified_n3_receipt' \
  src scripts tests docs data >"$EXECUTION_BASELINE_DIR/topology_discovery.txt"
rg_rc=$?
set -e
printf '%s\n' "$rg_rc" >"$EXECUTION_BASELINE_DIR/topology_discovery.rc"
case "$rg_rc" in
  0|1) ;;
  *) echo 'STOP=stage1_5h_n3_topology_discovery_failed' >&2; exit 1 ;;
esac
```

Classify each hit as `compatible_unchanged`, `BLOCKED_SCOPE_DRIFT`, or `BLOCKED_SPEC_DRIFT`. Discovery is advisory; actual source contract prevails.

**Verification:** record commands, stdout/stderr and actual RC. Revalidate authority/baseline ledger on every task boundary. `git diff --cached` remains empty. Any changed pre-existing path, new non-whitelist path, Plan/Design byte change or base SHA drift stops before the next task. Graphify is explicitly excluded by the approved Design: do not install it and do not create or update `graphify-out/**`.

## 5. Task 1: RED Tests and Canonical Positive Fixture

**Files:** create only the two allowed test files. Write RED tests before creating the core or CLI.

1. Create one canonical fixture that invokes the actual N=3 strict loader at the fixed N=3 root, then invokes frozen `load_stage1_5g_inputs()` and `build_stage1_5g_review_summary()` exactly once for each fixed source root in order: `moonshot`, `batch7`, `ct_projection`. It verifies each stored summary hash, each `SHA256SUMS` hash, schema `2`, clean decision, clean pass true, quarantine pass false, no blockers and exact identity/quality projection. No handcrafted cross-boundary summary, event, hash or metric dictionary is allowed.
2. Define RED cases for source/receipt trust boundaries: frozen module/config byte drift, preloaded wrong-origin module, receipt artifact hash mutation, stored-summary hash mutation, manifest hash mutation, wrong/missing identity field, one changed quality field, missing quality/context field, CT missing/non-CT/ninth child, one changed Batch7 duplicate, duplicate parent/article/event/symbol/event-symbol ID and wrong source-anchor hash.
3. Define RED cases for exact reducer/schema: incorrect product regime, cross-parent or cross-regime aggregate key, wrong parent median, wrong 13-false flag vector, extra/missing/type-invalid summary or manifest field, malformed run id, NaN/infinite/bool-as-number, wrong Markdown literal/terminal LF, manifest byte-count/hash/relative-path mutation and unlisted file.
4. Define lifecycle RED cases through a private test-only lifecycle helper with `tmp_path`: final/root/ancestor/artifact symlink, malformed or foreign staging sibling, collision, valid-final-plus-staging, corrupt final, pre-rename crash and post-rename durability failure. Positive receipt bytes must derive from the canonical fixture's real reducer output; only the output parent is test-local.
5. Define authority/CLI RED cases: missing/tampered implementation record; missing/tampered five-line generation record and sidecar; alternate run id; current core/CLI hash drift; unexpected CLI flag; attempt at input/output/root/bundle/receipt/resume/replay/network/consumer override; and `future_consumer_allowed=True`. The public core/CLI must stop before source import/read/staging when generation authority is absent. The production authority locator itself is never monkeypatched: tests first require its exact canonical result, then may redirect only private post-locator file-content reads to a `tmp_path` bundle. They retain the actual project root and frozen source roots, and never write under the real `data/` tree.
6. Add AST/import/open-spy RED tests. They reject direct raw event/depth reader/glob/parser, BAPI payload open, network/exchange/SSH/process/deployment/execution/paper/live/replay imports, old H V3 import, and script-to-source inversion. The open spy proves raw source files are opened only by the verified Stage 1.5G producer.

Before executing any RED node, create `task1_red_ledger.json` in the canonical bundle. For every required negative probe it contains exactly: `test_node_id`, `canonical_positive_fixture`, `required_preconditions_before_gate`, `single_mutation`, `target_gate`, `expected_exact_stop`, and `expected_pre_green_failure`. Identity/quality nodes must declare these preconditions in order: strict N=3 receipt load, exact source/stored hash validation, real source-root re-admission, stored/recomputed projection creation, then one in-memory projection-field mutation. They must call the named comparator directly; mutating a frozen artifact and failing an earlier SHA gate is not comparator evidence.

**Verification:** collect the two test modules with zero collection errors. Then run every ledger node individually and preserve node-id, stderr and RC. Before its target implementation exists, each node must fail only with its ledgered `expected_pre_green_failure`; an unexpected pass, XFAIL, collection error or unrelated failure is `STOP=BLOCKED_SPEC_DRIFT`. Task 2 reruns the same ledger node after the named gate exists: each test must pass only by observing its `expected_exact_stop`, with all listed preconditions asserted before mutation. A suite-level nonzero RC is never sufficient RED evidence.

```bash
set +e
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py \
  >"$EXECUTION_BASELINE_DIR/task1_red.log" 2>&1
red_rc=$?
set -e
printf '%s\n' "$red_rc" >"$EXECUTION_BASELINE_DIR/task1_red.rc"
test "$red_rc" -ne 0 || { echo 'STOP=stage1_5h_n3_expected_red_not_observed' >&2; exit 1; }
```

The aggregate log is diagnostic only; a small runner must compare every individual result to `task1_red_ledger.json` and write `task1_red_ledger_result.json`. It exits nonzero on any omitted node, unexpected result, or precondition failure.

## 6. Task 2: Minimal Verified Re-admission and Reducer

**Files:** create only `src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py` and update its test file.

1. Add exact constants for approved Design/Plan paths and hashes, N=3 root/artifact hashes, three ordered source records, four frozen runtime bindings, output grammar, 13 false flags and the three allowed product-regime ids. Derive the project root only from the core module's own file. No registry, callback, discovery, optional root, environment override or source-selection argument.
2. Implement execution-authority validation using exactly the create-once authority bundle contract in §1 and Task 0. Implement a separate `verify_local_receipt_generation_authority()` for the Design's exact five-line receipt-generation grammar, sidecar bytes, Plan/Design binding, authorized run id and current future core/CLI hashes. The public entry calls both guards before any import, read or staging operation; this Plan deliberately supplies no valid generation record.
3. Implement verified imports for all four frozen modules. Before and after import, bind exactly one expected relative path, reject preloaded/shadowed `sys.modules` entries, then verify `__file__`, `__spec__.origin`, resolved containment and SHA. Import `configs.base` as a runtime binding, not a disk-only digest.
4. Strict-load the fixed N=3 receipt with default arguments only. Independently require its exact three artifact hashes. Re-admit the three fixed roots in canonical order through the verified Stage 1.5G producer, build stored/recomputed identity projections, compare every declared key/type/value/order, and compare the exact 15-field quality projection for only nine emitted children. Do not use `.get`, default, coercion, tolerance or a raw-row fallback.
5. Emit exactly nine per-symbol rows and three parent rows. Emit `CTUSDT` alone from CT; require the other seven CT children to exactly equal Batch7 identities. Compute only each parent-local unweighted `statistics.median` and `buy_p95 + sell_p95` marginal sum. Reject any cohort/regime summary, range, rank, winner, pooled statistic, fee/PnL/cost-floor/execution/Alpha conclusion or current/future consumer path.

**Verification:** all Task 1 source/projection/reducer tests become GREEN. The canonical fixture must still demonstrate actual upstream loading, not merely direct local reducer input. Replay every `task1_red_ledger.json` node individually; every comparator mutation must reach the declared comparator and raise exactly the declared STOP after all preconditions have passed.

## 7. Task 3: Strict Artifact Contract and Lifecycle

**Files:** modify only the new core and core test file.

1. Serialize summary and manifest only with `canonical_json_dumps`. Implement the exact fixed Markdown projection from the validated summary, including literal title, disclaimer, code fence, canonical JSON and terminal LF. The summary, manifest and Markdown must have exactly the Design key sets and no free-form output facts.
2. Implement a strict local loader. Before every `resolve`, reject a symlinked root, ancestor or artifact; require output project containment, exact final file set, canonical JSON bytes, exact types/key sets, manifest metadata, artifact length/hash and fixed N=3 lineage. Re-render and byte-compare Markdown. A valid local load returns only the validated descriptive projection and still grants no consumer authority.
3. Implement the state classifier exactly as `unpublished`, `staging_only`, `receipt_published`, `corrupt_or_unknown`. It must inspect matching staging siblings before resolving and classify final-plus-staging, malformed sibling, symlink or invalid final as `corrupt_or_unknown`.
4. Implement the private lifecycle helper for tests and the public writer separately. The private helper accepts a temporary parent solely for lifecycle tests; it is not exposed through CLI, public core API, environment or configuration. Under one `fcntl.flock(LOCK_EX)` it performs fresh-state check, own staging creation, summary then review then manifest-last write/fsync, strict staging load, staging fsync, foreign-sibling recheck, atomic rename, parent fsync, strict final reload and state reclassification. No overwrite, resume, delete or same-run recovery.
5. A pre-rename failure leaves `staging_only` and is non-success. A failure after rename or parent fsync raises `STOP=POST_RENAME_DURABILITY_FAILURE`; later state is derived from current strict bytes only. The public writer derives the one Design output parent but remains unusable without a future separate generation authorization.

**Verification:** all serialization, loader, negative mutation, symlink, collision, two-writer and crash/recovery tests pass. The test suite must prove its `tmp_path` lifecycle helper never creates the production H N=3 output parent. The public writer is also exercised through the Task 4 valid-authority route, but its final private lifecycle sink is replaced only by a test-private spy after the public writer has derived and asserted the fixed production-relative parent; this proves public delegation without producing real data.

## 8. Task 4: Narrow CLI and Permission Isolation

**Files:** create only `scripts/external_signal_shadow/run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py` and update its test file.

1. Expose only `--approved-design-path`, `--approved-design-sha256`, `--approved-plan-path`, `--approved-plan-sha256` and `--run-id`. CLI derives its project root from its own file, verifies exact flag equality to the immutable execution authority, then invokes public core wiring. It accepts no input root, output root, receipt root, project root, bundle, URL, resume, consumer, network, replay or runtime override.
2. Public `run_diagnostic()` independently derives authority paths, calls implementation and generation authority guards, then only reaches source/import/publication code if both pass. Production calls have no caller-controlled root or output parameter. Its locator must be a direct, deterministic construction from the resolved project root, literal `.git/plan-execution/stage1_5h_n3_regime`, and compiled `APPROVED_PLAN_SHA256`; it must not read environment/CLI/caller input, inspect `latest`, glob, discover or normalize an alternate bundle.
3. Add one non-monkeypatch production-locator wiring test. It calls the real locator read-only and requires exact equality to `<resolved_project_root>/.git/plan-execution/stage1_5h_n3_regime/<APPROVED_PLAN_SHA256>`. It proves an injected environment value cannot alter the returned path and that a bundle-like CLI flag is parser-rejected before locator use. An AST check on the real locator rejects environment reads, caller parameters, `glob`, directory iteration/discovery and the literal `latest`; no test creates siblings under the real `.git` tree. This test runs before every valid-authority integration path.
4. Add one valid-authority public integration test. It creates a private `tmp_path` bundle with the exact implementation authority contract and exact five-line generation capability bound to the test's current core/CLI bytes and one authorized valid run id. The test retains the actual project root, invokes public `run_diagnostic()`, and replaces only a private post-locator content reader after the real locator's exact canonical path has been asserted; the actual authority parser still validates the redirected bytes. It replaces only the final private lifecycle sink with a spy. It must prove the real N=3 strict loader and all three actual frozen source roots are invoked, the reducer reaches exactly nine child rows and three parent rows, the run id equals `AUTHORIZED_RUN_ID`, and public writer delegation selects exactly `data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction` as the project-relative output parent. The spies prevent production data publication and test-only content redirection is neither exported nor selectable by CLI, caller argument, environment or config.
5. Add one CLI positive wiring test in-process: supply the five exact parser arguments, use the same post-locator valid-authority content redirection, and spy only at the public-core boundary. It must prove the exact Design/Plan bindings and authorized run id reach `run_diagnostic()`. It must not substitute a resolver, reducer, writer, source root or output path. Separate CLI-negative tests continue to prove absent/tampered generation authority stops before source/staging.
6. Preserve `RISK_LIVE_TRADING_ENABLED is False`. AST tests must prove no network, SSH, subprocess, commit, push, deployment, execution, paper/live, replay, old H V3 or future consumer wiring. CLI invalid/extra arguments must be rejected by parser before any work.

**Verification:** the non-monkeypatch production-locator test proves the canonical authority locator before any redirected content is used. Valid-authority tests then prove public core and CLI wiring through real source re-admission to final writer delegation; absent-authority tests prove `STOP=local_receipt_generation_not_authorized` before importing/re-admitting sources or creating staging. No test may publish a real receipt.

## 9. Task 5: Final Gates, Independent Review and Completion-Audit Handoff

**Files:** no additional repository paths. Evidence only in canonical Plan bundle.

1. Re-run Task 0 authority/baseline/scope checks. Compare full status, tracked diff, cached diff, index, untracked ledger and allowed paths. The only new repository paths may be the four new implementation/test files; approved Design/Plan are immutable pre-existing authorities. `git diff --cached` must remain empty. Existing Design/Plan bytes must remain exactly as ledgered.
2. Run focused tests and lint:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py

.venv/bin/python -m ruff check \
  src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py \
  scripts/external_signal_shadow/run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py

python3 -c "from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False"
```

3. Run anti-shortcut scanner and preserve its actual process RC, not a paraphrase:

```bash
set +e
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$(cat \"$EXECUTION_BASELINE_DIR/base_sha\")" \
  >"$EXECUTION_BASELINE_DIR/anti_shortcut_scan.log" 2>&1
scanner_rc=$?
set -e
printf '%s\n' "$scanner_rc" >"$EXECUTION_BASELINE_DIR/anti_shortcut_scan.rc"
test "$scanner_rc" -eq 0 || { echo 'STOP=BLOCKED_IMPLEMENTATION_DEFECT:anti_shortcut_scan' >&2; exit 1; }
```

4. Do not run, install or update Graphify, and do not create `graphify-out/**`: the approved Design freezes Graphify as unavailable. Re-run the exact Task 0 targeted `rg` query, preserve `topology_discovery_task5.txt` and actual `rg` RC, and save a unified before/after diff. A small path classifier must prove every new topology hit is one of the four allowed implementation/test paths; all pre-existing source hits must retain their Task 0 classification or STOP with `BLOCKED_SCOPE_DRIFT` / `BLOCKED_SPEC_DRIFT`. The `rg` RC is valid only when `0` or `1`; `>1` is `STOP=stage1_5h_n3_topology_discovery_failed`.
5. Before requesting independent Task 5 code review, create `review_input_snapshot.json` using canonical JSON and its exact SHA-256 sidecar. It contains exactly: `base_sha`, `allowed_file_sha256` (the four allowed file path/SHA-256 pairs), `status_sha256`, `tracked_diff_sha256`, `cached_diff_sha256`, and `untracked_ledger_sha256`. The review request and its receipt must bind the snapshot SHA, exact `BASE_SHA`, Design/Plan identities, RED-ledger results, focused test/lint/scanner RC, topology diff/classification, no-real-receipt proof and No-Touch scope proof.
6. The independent reviewer must inspect actual producer-to-loader wiring, canonical fixture provenance, individual one-mutation reachability, valid and invalid public writer/CLI routes, source/output open-spy, state/recovery, permission isolation and scope/index records. Persist its exact verdict/receipt and SHA in the Plan bundle. An OPEN review finding routes only through Rule-12 remediation and requires rerunning affected gates.
7. Immediately before Completion Audit handoff, recompute an identically shaped `completion_handoff_snapshot.json` and require byte-for-byte equality to `review_input_snapshot.json`; save its SHA-256 sidecar. Any difference means `STOP=code_review_snapshot_drift` and requires a new independent code review before audit. Only then hand the workspace and exact bundle to a fresh independent Completion Audit. The auditor independently reruns real loaders, selected mutation probes, focused gates, scanner RC and scope/index inspection; it does not trust executor summaries.

## 10. Completion and Post-Plan Routing

Implementation is eligible only for independent Completion Audit after every Task 0-5 gate passes. Any failed test, integrity mismatch, authority error, scope expansion, receipt creation, or output under the real H N=3 namespace routes to the corresponding STOP; it is not repaired by deleting evidence, rerunning Task 0 or silently changing a fixture.

If Completion Audit returns `COMPLETE`, the next separate operation is not automatic receipt generation. A user must first provide the exact five-line local receipt-generation authorization bound to the audited Plan SHA, one chosen valid `RUN_ID`, and the audited core/CLI hashes. That later authorization permits only one local receipt publication and still grants no downstream consumer, Alpha, execution, paper/live or deployment authority.
