# Stage 1.5H V3 Cross-Root Liquidity Friction Diagnostic Implementation Plan

> 本 Plan 仅定义实现与验证合同。只有本文件经独立审核并由用户以本文件的 exact SHA-256 发出实施批准语句后，才允许按 Task 实施。它不授权数据生成、network、VPS/SSH、replay、交易、commit、push、deployment 或任何 runtime action。

**目标：** 增加一个严格本地的 Stage 1.5H V3 diagnostic producer。它只重读已冻结的 Stage 1.5G cross-root receipt，并通过被冻结的 production loader/reducer 重准入两个根，写入一个新的 manifest-last sealed root。结果只能描述 2 个 parent event 内的 8 个 child-symbol L2 quality metric 投影；任何 Alpha、成本、可执行性或策略结论固定为 `evidence_insufficient`。

**最小架构：** 一个 V3 core、一个窄 CLI、两份测试文件。V3 不实现 raw-row reader、glob、parser、percentile 计算、consumer 或 extension point；它仅调用现有严格 receipt reader 与现有 1.5G production loader/reducer，并复用 `canonical_json_dumps`。不修改现有 1.5G、1.5H/V2、配置、collector 或下游 consumer。

**技术栈：** Python 标准库、现有 Stage 1.5G 生产模块、`canonical_json_dumps`、pytest、ruff、Git、`shasum`、`.agent/tools/anti_shortcut_scan.py`。不新增依赖或服务。

## 1. Approved Design Binding

| 项目 | 冻结值 |
| --- | --- |
| Approved Design | `docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-design_CN.md` |
| Approved Design SHA-256 | `416b394bf809e1dcc159f9d39ecd175b57962022434d09478f5e0d97fa5a9276` |
| 本 Plan 路径 | `docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-implementation-plan_CN.md` |
| Plan authority | 实施时必须逐字保存并解析用户的实施批准语句；`APPROVED_PLAN_PATH` 与 `APPROVED_PLAN_SHA256` 只能是该语句的解析结果，绝不可由 CLI、环境或当前 Plan bytes 自证 |
| 1.5G receipt root | `data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z` |
| receipt manifest SHA-256 | `a3b9a45d3c4fbed9ed1136add956a0d0266236298f9be4b754d11134feb65467` |
| receipt summary SHA-256 | `9f45b4c184f4cb3d76944eb3e5bef51af3cd7a3277028196e0fb84eb293516c0` |

Task 0 的外部 authority 是用户逐字提供的两行实施批准语句，而不是 executor 选择的环境值。它必须恰好匹配：

```text
我批准实施 Plan：<expected-plan-path>（SHA-256: <lowercase-64-hex>）。
允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。
```

Task 0 将原始 UTF-8 bytes 写入 attempt bundle 的 `implementation_authorization.txt`，保存独立 SHA-256 并设为只读。它只从这份 bytes 提取 path/SHA；传入的 `APPROVED_PLAN_PATH`/`APPROVED_PLAN_SHA256` 必须逐字等于提取结果，且 current Plan bytes 必须等于该 SHA。Task 0 再生成唯一、sorted compact JSON 的 `execution_authority.json`，其 key set **恰好**为：

```text
project_root
base_sha
approved_design_path
approved_design_sha256
approved_plan_path
approved_plan_sha256
current_plan_sha256
```

`approved_plan_path`/`approved_plan_sha256` 是上述用户语句解析值；`current_plan_sha256 == approved_plan_sha256` 是强制 equality，不能作为新的 authority。`approved_design_path`/`approved_design_sha256` 必须等于本节冻结值。每个 Task 的开始和结束、CLI core entry 及 publication 前都必须重新验证：当前 Plan regular-file bytes == `execution_authority.approved_plan_sha256` == immutable user-statement parsed SHA，路径 == 预期相对路径 == immutable parsed path。随后才可读取 receipt、导入 upstream 或创建 staging root。

任何读取、导入、输出目录创建之前，Task 0 和 CLI/core 都必须重新验证 approved Design/Plan 的 regular-file 路径和字节，以及下列 TCB 的 exact bytes：

| 路径 | SHA-256 |
| --- | --- |
| `src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py` | `b6a1c9f1348985a7407d41b67b240656faac84cb0e362e7191a2731a2f098570` |
| `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py` | `596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d` |
| `configs/base.py` | `414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4` |
| `src/research/external_signal_shadow/safety.py` | `1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d` |

模块在 import 后还必须验证 `__file__`、`__spec__.origin` 和再哈希均绑定到 project root 内的同一冻结路径。TCB/import drift 为 `STOP=stage1_5h_v3_upstream_contract_drift`；批准、receipt、root、membership、schema 或 projection drift 为 `STOP=stage1_5h_v3_cross_root_authority_mismatch`。

## 2. Allowed Change Scope

### 允许实现路径

- `src/research/external_signal_shadow/stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py`
- `scripts/external_signal_shadow/run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py`

### 允许验证路径

- `tests/research/external_signal_shadow/test_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py`

### 允许文档与生成物

- 本 Plan 本身；实施不得改变其它文档。
- 仅在另一条明确本地执行授权下，`data/external_signal_shadow/stage1_5h/v3_cross_root_friction/<RUN_ID>/**`。
- pytest 的 `tmp_path` 下临时输出；不得成为项目 evidence。

### 已知受影响但必须保持不变

- 1.5G receipt producer、1.5G review loader/reducer、`safety.py`、`configs/base.py`、现有 1.5H/V2。
- Stage 1.5D/1.5F、所有 VPS/runbook、roadmap/status、data 根、consumer、Graphify、Git metadata。

禁止 network、VPS、SSH、任何下载或第三根发现、价格/结果/PnL/expectancy/replay/backtest、raw orderbook 重算、execution/paper/live、commit/push/deploy。需要白名单外文件为 `STOP=BLOCKED_SCOPE_DRIFT`；冻结 Design 与当前 source API 无法兼容为 `STOP=BLOCKED_SPEC_DRIFT`，不得改 hash、改解释或造 fallback。

## 3. Canonical Positive Fixture And Output Contract

唯一跨边界 positive fixture 是项目内的 exact receipt 和下面两个 exact local source roots；测试必须调用 upstream strict reader/loader/reducer，不得以手写字典替代：

| input key | root | source manifest SHA-256 | parent event | symbols |
| --- | --- | --- | --- | --- |
| `moonshot` | `data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot` | `611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db` | `e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5` | `MOONSHOTUSDT` |
| `batch7` | `data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7` | `0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280` | `d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0` | `CRMLUSDT`, `BWETUSDT`, `ACNUSDT`, `MPUSDT`, `SECZUSDT`, `UNHUSDT`, `NKEUSDT` |

Fixture proof requires:

1. `load_verified_cross_root_receipt()` passes on the exact root.
2. For both receipt-authorized roots, `load_stage1_5g_inputs()` then `build_stage1_5g_review_summary()` pass.
3. Receipt identity/count fields are compared only to source identity fields; V3 never takes quality values from receipt `input_records` or `parent_ledger`.
4. Stored and recomputed per-symbol quality projections are exact equal; both source summaries remain schema `2`, decision `stage1_5g_depth_evidence_clean_pass`, `clean_depth_evidence_pass=true`, `quarantined_depth_evidence_pass=false`, `blockers=[]`.

V3 has fixed `RUN_ID` grammar `^stage1_5h_v3_cross_root_friction_[0-9]{8}T[0-9]{6}Z$`, final root `data/external_signal_shadow/stage1_5h/v3_cross_root_friction/<RUN_ID>/`, staging root `.<RUN_ID>.staging.<pid>/`, and exactly these final files:

```text
stage1_5h_v3_cross_root_friction_summary.json
stage1_5h_v3_cross_root_friction_review_CN.md
stage1_5h_v3_cross_root_friction_manifest.json
```

Summary/review/manifest schema, canonical ordering, all 13 false authority flags, persistent receipt lineage equality, 8 child rows/2 parent rows, 13 allowed metrics, `statistics.median`, `min/max` ranges, exact human Markdown template and `evidence_insufficient` must match Design sections 5-6 byte-for-byte. `sum_of_marginal_p95_slippage_bps` is only `buy_p95 + sell_p95`; it must never be labelled paired round-trip percentile, cost, threshold, feasibility or pass/fail.

## 4. Design-to-Implementation Matrix

| Design invariant / authority edge | Owner | RED proof and canonical GREEN proof | Fail-closed outcome |
| --- | --- | --- | --- |
| INV-H3-01 exact authority/TCB/import origin | Task 0 user-statement packet and Task 2 V3 core | self-derived Plan hash, wrong path, post-Task-0 Plan edit, wrong TCB or preloaded shadow module fails before receipt call; canonical immutable statement/bytes/import origin pass | `...upstream_contract_drift` / `...cross_root_authority_mismatch` / `STOP=approved_authority_mismatch` |
| INV-H3-02 receipt identity separated from quality | Task 1 integration tests, Task 2 comparator | mutate one identity field then fail before quality; canonical fixture strict-loads receipt and independently re-admits both roots | `STOP=stage1_5h_v3_cross_root_authority_mismatch` |
| INV-H3-03 8 children to 2 parents | Task 1 reducer tests | duplicate, omit, or move exactly one child fails; canonical ordered 8/2 fixture passes | `STOP=stage1_5h_v3_cross_root_authority_mismatch` |
| INV-H3-04 upstream-only raw access | Task 1 AST/open-spy and Task 2 core | V3 raw JSONL/glob/open/import violation fails before core implementation; actual production loader is the sole raw-row caller | `STOP=stage1_5h_v3_upstream_contract_drift` |
| INV-H3-05 arithmetic semantics | Task 1 pure reducer and integration mutation | alter one in-memory buy/sell p95 and assert exact delta plus only legitimate parent/range updates | `STOP=stage1_5h_v3_quality_projection_mismatch` |
| INV-H3-06/07/09 economic isolation, 13 false flags, Gate3 false | Task 1 schema/template RED tests and Task 2 validators | missing/true/extra flag, Gate3 true, forbidden promotion prose or status fails before implementation; fixed literal output passes after Task 2 | `STOP=stage1_5h_v3_cross_root_authority_mismatch` |
| INV-H3-08 exact bytes and lifecycle | Task 3 fixed-root writer/loader and Task-3-owned lifecycle RED tests | one artifact hash/length, type, template, symlink, current-PID or stale-other-PID matching staging collision, or failpoint mutation fails; staging and final strict-load only in valid states | `STOP=stage1_5h_v3_publication_integrity_failure` |
| INV-H3-10 no unsafe reachability | Task 1 source isolation, Task 3 CLI RED and Task 5 scanner | Task 1 AST/import/open spy rejects Task-2 unsafe code before implementation; Task 3 CLI tests reject URLs, arbitrary roots/outputs and environment substitution | `STOP=stage1_5h_v3_unsafe_action_not_authorized` |
| Scope/provenance and Rule-12 | Task 0 and Task 5 | baseline ledger, index/worktree comparison and actual scanner RC; independent review then Completion Audit | `BLOCKED_SCOPE_DRIFT`, `BLOCKED_SPEC_DRIFT`, `BLOCKED_IMPLEMENTATION_DEFECT`, or `INCOMPLETE` |

## 5. Task 0: Immutable Baseline And Authority Admission

**Files:** create a single attempt bundle outside the repository; read approved Design/Plan, frozen TCB, receipt and source metadata only. Do not import V3/upstream code, modify source, create V3 output, or invoke a runtime producer.

1. Require `EXECUTION_BASELINE_DIR` initially unset. Create it once with `mktemp -d "${TMPDIR:-/tmp}/stage1_5h_v3_cross_root_friction.XXXXXX"`; never accept a caller-selected directory and never recapture/rebaseline it.
2. Require a user-supplied, verbatim `IMPLEMENTATION_AUTHORIZATION_TEXT` containing exactly the two lines in Section 1. Persist it before parsing as `implementation_authorization.txt` plus `implementation_authorization.sha256`; reject malformed grammar, altered permission clause, wrong relative path, uppercase/non-hex SHA, symlinked record or hash mismatch. Parse its Plan path/SHA once. Require external `APPROVED_PLAN_PATH`/`APPROVED_PLAN_SHA256` to exactly equal the parsed values, and require current non-symlink regular Plan bytes to equal that SHA. Verify the frozen Design bytes before any source/test changes.
3. Capture `base_sha`, full `git status --short --untracked-files=all`, binary worktree/index patches, tracked changed path set, index snapshot, and sorted untracked set. Capture a sorted JSONL pre-existing ledger for the union of tracked dirty, staged, untracked and missing paths with type/size/SHA or literal symlink target. The currently pre-existing approved Design is ledgered and must remain byte-identical.
4. Refuse pre-existing dirty/untracked files in the four allowed implementation/test paths. Write only the exact Section 1 schema for `execution_authority.json`; write its SHA separately. Make the authorization statement/sidecar, authority JSON/sidecar and ledger/sidecar read-only. Every later task verifies all six record hashes, re-parses the immutable user statement, verifies the three-way Plan path/SHA equality and `HEAD == base_sha`.
5. Hash all TCB/receipt/source-manifest/stored-summary bytes; verify exact receipt files and roots exist as non-symlink regular/directory objects. This task does not parse raw snapshot rows.
6. Run direct `rg` topology discovery for V3 symbol collisions. Capture `rg_rc`: only `0` or `1` is valid; `>1` is `STOP=stage1_5h_v3_topology_discovery_failed`. Record a classification of `none`, `compatible_unchanged`, `BLOCKED_SCOPE_DRIFT`, or `BLOCKED_SPEC_DRIFT`; do not add registry/consumer fallback.

Required persistent attempt records are `implementation_authorization.txt`, `implementation_authorization.sha256`, `execution_authority.json`, `execution_authority.sha256`, `preexisting_path_ledger.jsonl`, `preexisting_path_ledger.sha256`, baseline Git files, TCB hash output, topology result, and actual `rg_rc`. Any absent/replaced/read-only-record mismatch is `STOP=approved_authority_mismatch`. The Plan itself becomes a No-Touch authority after Task 0; no task, test, formatter or review remediation may change it in place.

## 6. Task 1: RED Tests For Receipt, Re-admission And Reducer

**Files:** create the two allowed test files first. No production code before the relevant RED test exists.

Before Task 2 creates the core, execute and preserve the TDD evidence below. `red.log` and `red_rc` are attempt-bundle records, never source-controlled output:

```bash
set +e
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py \
  >"$EXECUTION_BASELINE_DIR/task1_red.log" 2>&1
red_rc=$?
set -e
printf '%s\n' "$red_rc" > "$EXECUTION_BASELINE_DIR/task1_red_rc"
test "$red_rc" -ne 0 || { echo 'STOP=stage1_5h_v3_expected_red_not_observed' >&2; exit 1; }
```

The log must show only the declared missing/unimplemented V3 RED cases, recorded in `task1_red_expected_cases.txt`; an unrelated collection, upstream or authority failure is `STOP=BLOCKED_SPEC_DRIFT`, not valid RED evidence. Task 2 reruns this exact command after the minimum implementation, saves `task2_green.log`/`task2_green_rc`, and requires actual RC `0`.

1. Add canonical integration test that strict-loads the real receipt and re-admits both real source roots through the actual frozen production loader/reducer. Assert exact two input keys, two distinct parent IDs, eight ordered `event_symbol_id`s and stored/recomputed quality equality.
2. Add a one-field receipt identity mutation test. Invoke the V3 identity validator directly with only a mutated admitted in-memory identity field, and prove failure occurs before calling the quality projection comparator.
3. Add one manifest artifact hash/length mutation to a temporary copy of the strict receipt; `load_verified_cross_root_receipt` must reject it. Never mutate the frozen workspace receipt.
4. Add quality comparator test: strict-load real receipt and real roots, mutate one allowed quality field only in the admitted in-memory stored projection, then require `STOP=stage1_5h_v3_quality_projection_mismatch`.
5. Add single-child duplicate/omission/cross-parent mutation tests against the V3-owned identity/reducer boundary. Each must reject bijection; the canonical fixture must still show children are not independent events.
6. Add p95 arithmetic test: mutate one admitted in-memory buy or sell p95 by delta `d`; assert the per-symbol sum changes by exactly `d`, and the only dependent parent median/cohort min-max values are deterministically recomputed. Assert no cost floor, paired-P95 label, feasibility/pass status or selection appears.
7. Add direct authority/TCB tests for the Task 2 core: modified Plan plus self-calculated SHA against the immutable user statement, same bytes at wrong path, Plan mutation after Task 0, TCB hash drift and preloaded shadow module. Each must fail before receipt/re-admission use.
8. Add Task-2 schema/type/root tests: exact canonical summary/manifest key sets and bytes, finite values, identifier/path grammar, non-bool count checks, receipt lineage equality, exact 13 false keys/values, `stage1_5g_gate3_complete=false`, `OUTPUT_PARENT_REL` equality with the Design namespace, and public `run_diagnostic` signature with no root/output override.
9. Add exact Markdown strict-loader tests before renderer implementation: the literal template must rebuild byte-for-byte and appended `execution looks feasible` must reject. These tests are Task 2 RED, not a later Task 4 addition.
10. Add AST/import/open-spy tests before Task 2 code exists: V3-owned code must have no raw JSONL glob/open, raw parser, price/outcome, network or exchange-client access; frozen upstream re-admission is the only permitted source-artifact reader. A missing V3 module is the declared initial RED condition, not a reason to omit the test.

The Task 1 RED suite is the complete test owner for every Task 2 contract in items 1-10; Task 2 may not add a first test for those behaviors. Synthetic local structures are allowed only for V3 pure reducer/lifecycle unit tests after the real-root integration test is present. They cannot be used as a positive upstream boundary fixture.

## 7. Task 2: GREEN Minimal V3 Core

**File:** `src/research/external_signal_shadow/stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py`

Implement only these responsibilities:

1. Resolve project root from the module's own `__file__`; define fixed Design/receipt/TCB/input constants and strict hash/path/type helpers. Do not permit root registry, glob discovery, user output path, callback, plugin or consumer API.
2. Verify Design/Plan authority packet and TCB bytes before lazy importing the frozen upstream modules. Reject preloaded shadow modules; then check imported `__file__`, `__spec__.origin` and bytes again.
3. Call `load_verified_cross_root_receipt` for identity/count only. Call frozen `load_stage1_5g_inputs` then `build_stage1_5g_review_summary` once per fixed root. Compare only independently derived identity fields to receipt identity, and only stored versus recomputed quality projections to each other.
4. Build exactly the Design schemas: sorted 8 per-symbol rows, two parent medians via `statistics.median`, two-parent min/max metric ranges, fixed decision/classification/Gate3 false and exact 13-key false vector. Validate all finite numeric, non-bool count, identity, path/order/key-set and lineage rules before serialization.
5. Serialize only with frozen `canonical_json_dumps`. Render the Design §6.3 Markdown literal template in one function with exactly one trailing newline. Implement strict summary/review/manifest loaders that independently rebuild the Markdown and require canonical byte equality.
6. Expose public runtime functions only for authority verification, identity validation, quality projection comparison, summary derivation, render/strict-load, state classification and `run_diagnostic(run_id, authority_packet)`. `run_diagnostic` derives project root from its own `__file__` and resolves the sole output parent from fixed `OUTPUT_PARENT_REL = "data/external_signal_shadow/stage1_5h/v3_cross_root_friction"`; it accepts no project-root, parent-dir or output override. A private lifecycle-only writer helper may accept a temporary already-validated parent solely for `tmp_path` crash tests; CLI and public runtime entrypoints never import, expose or call it with caller-supplied paths.

No V3 code may open/glob raw snapshot JSONL, read prices/outcomes, construct an exchange/network client, import a script, or calculate any statistic other than the specified sum/medians/min-max.

## 8. Task 3: Manifest-Last Writer, Strict Reader And Narrow CLI

**Files:** V3 core and `scripts/external_signal_shadow/run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py`.

Before adding publication/CLI behavior, add only the Task-3-owned manifest-last, stale-sibling, crash-state and CLI parser/wiring cases to the two test files and run this focused RED command. It must be nonzero because writer/CLI behavior is not yet implemented; save both actual output and RC:

```bash
set +e
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  -k 'publication or lifecycle or staging or cli' \
  tests/research/external_signal_shadow/test_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5h_v3_cross_root_liquidity_friction_diagnostic.py \
  >"$EXECUTION_BASELINE_DIR/task3_red.log" 2>&1
task3_red_rc=$?
set -e
printf '%s\n' "$task3_red_rc" > "$EXECUTION_BASELINE_DIR/task3_red_rc"
test "$task3_red_rc" -ne 0 || { echo 'STOP=stage1_5h_v3_expected_task3_red_not_observed' >&2; exit 1; }
```

The executor records the exact declared cases in `task3_red_expected_cases.txt`; unrelated failure is Rule-12 drift, not RED evidence. After the minimum writer/CLI implementation, rerun the same command into `task3_green.log`/`task3_green_rc` and require actual RC `0`. Task 4 introduces no first test for Task 0/Task 2/Task 3 behavior; any later logic correction repeats this RED -> minimum fix -> focused GREEN sequence.

Core writer sequence is fixed:

```text
validate authority and both roots
-> derive summary/review in memory
-> write+fsync summary
-> write+fsync review
-> write+fsync manifest last
-> strict-load staging root
-> fsync staging directory
-> os.replace(staging, final)
-> fsync final parent directory
-> strict-load final root
```

The public writer resolves only `project_root_from_core_file() / OUTPUT_PARENT_REL`, which must equal the Design final-parent path exactly; no public/core/CLI parameter can substitute it. It accepts only a conforming `RUN_ID`, non-symlink project-contained ancestor, absent final root, and **zero** sibling entries matching exactly `re.compile(rf"^\\.{re.escape(run_id)}\\.staging\\.[1-9][0-9]*$")`. The matcher covers every PID, not merely `os.getpid()`. It never overwrites, deletes, resumes or repairs final/staging roots, and creates no state file. Classify only `unpublished`, `staging_only`, `receipt_published`, `corrupt_or_unknown` from actual filesystem bytes and strict load.

If rename succeeded but parent directory fsync fails, raise nonzero `STOP=stage1_5h_v3_post_rename_durability_failure`; never report generated or alter the final root. All other writer/schema/strict-load failures are `STOP=stage1_5h_v3_publication_integrity_failure`.

CLI accepts exactly:

```text
--approved-design-path --approved-design-sha256
--approved-plan-path --approved-plan-sha256
--execution-baseline-dir --run-id
```

It revalidates the immutable Task 0 statement/authority records and the Section 1 three-way external Plan binding. It has no `--root`, `--output-root`, URL, stdin, glob, resume, force, environment-default or consumer mode. It returns nonzero and emits the specific STOP on failure. CLI positive proof is a spy asserting `CLI -> run_diagnostic` with no project-root/output override; it never invokes a producer against either a temporary or project runtime root.

## 9. Task 4: Regression, Integration And Negative-Test Completion

**Files:** both allowed test files.

1. Introduce no first test for Task 0/Task 2/Task 3 behavior. Rerun the complete Task 1 authority/TCB/re-admission/reducer/schema/template/isolation suite and the Task 3 publication/lifecycle/CLI suite; both recorded GREEN commands must return `0`.
2. Confirm the Task 3 lifecycle suite covers invalid `RUN_ID`, pre-existing final, symlink traversal, extra/missing files, stale matching staging for a different PID, multiple matching staging siblings and fresh zero-sibling start. Every reuse/collision case rejects without overwrite, delete, resume or cleanup.
3. Confirm the Task 3 lifecycle suite uses writer failpoints for crash before manifest, after manifest, after staging-directory fsync, and after rename before parent fsync; assert exact four-state classification, never-consumable partial state, and strict final reload only when publication genuinely completed.
4. Confirm the Task 1 suite exercises exact canonical JSON/type/false-vector/Gate3/lineage/template behavior, the three authority negatives and V3 raw/open/import isolation. Confirm the Task 3 CLI suite rejects arbitrary root/output/URL/resume/force/unknown arguments and bad bindings, while its only positive is the no-override `CLI -> public run_diagnostic` spy.

Each negative mutates one declared edge only, except lifecycle states which require the stated compound filesystem state. After every RED mutation, rerun the canonical real-root positive fixture. Task 4 is regression/integration completion, not deferred test authoring for already-implemented core behavior.

## 10. Task 5: Full Gates, Scope/Index Proof And Rule-12 Routing

Before and after this task, verify immutable authority/ledger hashes and `HEAD == base_sha`. Compare current worktree/index/untracked paths against Task 0 records:

1. New changes may appear only in the four whitelisted source/test paths. The pre-existing approved Design and all ledgered unrelated paths must retain their recorded identity; no staged changes are allowed.
2. Run `git diff --check`, `git diff --no-index --check /dev/null <each-new-whitelisted-file>` with its expected difference RC handled explicitly, targeted `ruff check` on the two implementation files, and targeted pytest for the two V3 test files. Record full commands and real return codes in the attempt bundle. The focused pytest command must produce actual RC `0` at Task 2 and again after Tasks 3/4; record each GREEN log/RC separately.
3. Run `PYTHONPATH=src:. .venv/bin/python .agent/tools/anti_shortcut_scan.py --base-sha "$(cat "$EXECUTION_BASELINE_DIR/base_sha")"` without `|| true`; save `scanner_rc`. Only actual RC `0` passes. Scanner success is necessary, not sufficient.
4. Run direct `rg` topology/safety checks and store actual RC as in Task 0. Graphify is advisory only because the current environment lacks the module; it cannot substitute direct source/AST/CLI evidence or block solely due to absence.

Rule-12 routing is mandatory and stops the current task immediately:

| Evidence | Route |
| --- | --- |
| local code misunderstood approved Design or existing API, fixable in the four paths | `BLOCKED_IMPLEMENTATION_DEFECT`; reproduce the changed logic as RED, apply minimum fix, record focused GREEN, then rerun Tasks 1-5 |
| required source/test/doc/config/consumer change outside whitelist | `BLOCKED_SCOPE_DRIFT`; no workaround or hidden compatibility layer |
| frozen receipt/TCB/API conflicts with approved Design/Plan | `BLOCKED_SPEC_DRIFT`; produce invariant, SSOT path, contradiction and proposed Design delta |
| authority/ledger/hash/index/scanner failure | specific STOP; no rebaseline, reset, checkout or substitution |

After all local gates pass, create an immutable `code_review_round_<n>/` directory inside the attempt bundle. It must contain: `base_sha`, fresh status/index snapshots, a sorted exact four-path manifest with relative path/byte count/SHA-256, exact copies of the four current non-symlink untracked files, one `git diff --no-index /dev/null <path>` patch per path, a lexicographically concatenated `combined.patch`, and SHA-256 sidecars for every copied file and combined patch. Each `git diff --no-index` must return exactly `1`; any other RC stops. Make the bundle read-only after hashing. The reviewer receives `base_sha + exact bundle bytes/patches`, never an empty `git diff BASE_SHA...HEAD`; staging or commit is forbidden.

Invoke `requesting-code-review` against that exact review bundle. If it changes logic, use the Rule-12 RED -> minimum fix -> focused GREEN sequence, rerun all Task 5 gates, generate a new immutable `code_review_round_<n+1>` from the new four-file bytes, and request a new review. Only then hand the untouched workspace and final review bundle to a fresh independent `audit-plan-completion` auditor. Code review and Completion Audit are mandatory, independent, and occur in that order. Neither grants commit, runtime execution, network, deployment, paper/live or trading authority.

## 11. Completion Checklist

Completion Audit may return `COMPLETE` only when all of the following are independently reproducible:

1. immutable user implementation statement, exact authority-record schema, three-way approved Plan bytes/path equality, frozen Design/receipt/TCB hashes, imported origins and Task 0 ledger are exact.
2. canonical positive test uses the real receipt and both real roots through the production loader/reducer; all specified single-point negatives fail closed.
3. V3 owns no raw reader, no public arbitrary-root/output selection, no consumer, and no unsafe import/path; public output resolution equals the frozen Design namespace and the CLI calls it without override.
4. output schema/template/lineage/false vector/Gate3 false and 8-child/2-parent arithmetic are strictly loaded from sealed bytes.
5. manifest-last staging, every-PID sibling collision matcher, both directory fsyncs, crash classification and post-rename durability failure obey the contract.
6. declared RED log/actual nonzero RC, each focused GREEN log/actual zero RC, ruff, diff/scope/index checks and anti-shortcut scanner actual RC are green and recorded.
7. immutable untracked four-file code-review bundle and fresh Completion Audit have no OPEN required finding.

`COMPLETE` only means this local implementation contract is met. It does not authorize a runtime diagnostic execution, strategy, Alpha claim, simulator/consumer wiring, network, replay, paper/live trading, commit, push, deployment or SSH.
