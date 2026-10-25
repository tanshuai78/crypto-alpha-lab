# Stage 1.5J-C 新合约上线时间与路径可行性诊断实施计划 R1

**日期：** 2026-10-24
**状态：** `implementation_plan_candidate_r1`，仅供评审；未授权实施、原始数据消费、收据生成或审计。
**绑定 Design：** [2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md](../designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md)
**Design SHA-256：** `32d5130806489c0848748060835a7c0fb8f1715a3f9fb6b479c2f02cff5d4e45`，已按用户批准语句重算一致。
**前序已批准 Plan（冻结不修改）：** [2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan_CN.md](2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan_CN.md)，SHA-256 `90b09dc847b90dad2ceffab74c2a4a019ea5807d62aaa4c24aacf02692f628a7`。
**规划基线：** `f7118978d6a446fe4bac156979053667ec51b2e7`；执行时必须重新记录 `BASE_SHA`，不得沿用本文基线。
**研究状态：** `hypothesis_only`；只允许历史离线描述，不能产生 alpha、信号、paper/live trading 或 execution 结论。

## 0. Authority And Preconditions

本 Plan 只落实已经批准的单一场景：`60s observation + 3s latency + 15m endpoint`、成本 `50/80/150 bps`、观察障碍 `200/3000 bps`、71 个选入 child、long/short 并列、Parent 统计。它不改变参数、分组、输入根、profile 或结论 reducer；任何此类要求均为 `STOP=BLOCKED_SPEC_DRIFT`。

Design 批准和未来 Plan 实施批准都不是 raw-data runtime 授权。以下仍须在实现审计通过后，由用户原文和独立 Authorization Custodian 的 release 另行授权：

- `offline_time_path_validation_once`：读取真实 JA/JB raw 输入并发布 `validation_only` 临时根；
- `offline_time_path_diagnostic_once`：发布正式 `production_diagnostic` J-C receipt；
- 写入任何 `.git/plan-execution/stage1_5j_c/<approved-plan-sha>/<run-id>/` 的运行授权、派生授权、lifecycle 或 closure evidence。

CLI、producer、test 和 auditor 都不是 Custodian，不得创建、改写、删除、批准或修复 `user_receipt_generation_approval.txt` 或 `authorization_release.json`。没有 Custodian release 时，入口必须在任何 upstream loader 前以 `STOP=stage1_5j_c_independent_approval_release_unavailable` 退出。

执行授权根是用户原样提供的 Plan 实施批准语句中的 path/SHA，而不是本文件中的自述、当前 Git HEAD 或执行者写入的证据。Task 0 必须先取得该外部批准记录的 `APPROVED_PLAN_SHA256`，重算本 Plan 物理字节并精确比较；不一致为 `STOP=approved_plan_identity_mismatch`。Plan SHA 不自嵌入本文，避免循环哈希。

### R1 Proof-Layer Repair

本 R1 只修复 P1-01 的证据顺序，不改变已批准 Design、研究参数、输入身份、producer/consumer、权限或 lifecycle owner。原 Plan 保持上述 SHA 所标识的字节不变。

- **Task 4 是独立 Rule 17 schema 单元验证。** 它可在 `tmp_path` 中建立一个仅满足 J-C literal profile 的局部三文件 fixture，以检验 verifier 的闭树、字段、条件关系、canonical JSON 和 renderer 规则。该 fixture 不读取 J-A/J-B root、raw ZIP、ledger、approval/release 或 `.git` authority state；不调用 producer、domain loader 或 CLI；不得称为 canonical upstream fixture、source-backed receipt 或 Tier-4 cross-boundary proof。其正向结果只证明 standalone verifier 的 schema 行为。
- **Task 5 是唯一的 Tier-4 正向跨边界证明。** 只有在外部 Custodian release 后，真实 CLI 从冻结 J-A/J-B 输入产生 `validation_only` root，且 J-C domain replay 与独立 Rule 17 verifier 都接受该物理 root，才可证明 raw-to-output/provenance 语义。Task 5 前该证据状态为 `not_yet_authorized`，不是可由 Task 4 synthetic fixture 关闭的 P1。
- Gate 4.5 只能评审 Task 0-4 的 pre-authorization 实现正确性和声明边界；它不得要求、暗示或伪造 Task-5-only 证据。Task 6 也不得以 Task 4 fixture 代替 Task 5 的真实结果。

### R1 Interrupted-Execution Resumption Repair

R1 不是假定从零开始的重建计划。开始时 J-C whitelist 内可能已存在原 Plan 的中断实现、测试或局部证据；这些内容在 Task 0 完成当前字节审计前均为 `present_unverified`，不能因文件存在、旧口头结论、旧 review、旧 test output 或旧 source bundle 而获得 GREEN、授权或 Task-5 资格。

- Task 0 必须在任何写入、测试或重新执行前形成 **resumption inventory**，逐项列出七个 implementation/verification/protocol path 的存在状态、SHA-256、Git tracked/staged/untracked 状态、最近可核验的 test/evidence 位置与状态：`absent`、`present_unverified`、`prior_failure_recorded` 或 `prior_evidence_verified`。该 inventory 只进入实施 handoff/review packet；不得由此创建 `.git/plan-execution`、runtime root 或新的 authority artifact。
- 缺少旧 Task-0 baseline、准确执行记录或可读取证据时，记录 `scope_provenance_uncertain=true`。这不允许重写历史、假定旧 Task 通过或把旧 GREEN 升级为 R1 evidence；执行者必须保留现有字节、记录它们为 `present_unverified`，并以当前实际 bytes 重新运行本 Plan 指定的 test/probe/quality gates。只有 current scope/index proof 与独立 Gate 4.5 才可决定 Tasks 0-4 是否重新取得 GREEN。
- 本 Plan 中的“create”只适用于 inventory 为 `absent` 的 whitelist path。对于任何已存在 path，只可在定位到的最小 defect 范围内修改；不得覆盖、删除、重新归因或为了制造 RED 而回退已有实现。若既有行为已使一个新测试为 GREEN，记录 `inherited_red_not_observable`，并以 test-local negative mutation、raising sentinel 或 fault injection 证明该断言的 fail-closed owner，而不是破坏当前产品行为。
- 旧 Plan 的 review、baseline、test transcript、source bundle、validation root 或 closure evidence 只能作为调查输入。它们永远不能替代 R1 approved bytes、R1 Task-0 inventory、当前 process RC、Gate 4.5 review 或 Task-5 authorized root/hash tuple。

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_5j_c_launch_time_path_feasibility.py`
- `scripts/external_signal_shadow/run_stage1_5j_c_launch_time_path_feasibility.py`
- `scripts/governance/verify_stage1_5j_c_receipt_schema.py`
- `docs/production_artifacts/stage1_5j_c_time_path_protocol_v1.json`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5j_c_launch_time_path_feasibility.py`
- `tests/scripts/governance/test_verify_stage1_5j_c_receipt_schema.py`

Allowed documentation paths:
- `docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md`

Allowed generated/runtime artifacts:
- `data/external_signal_shadow/stage1_5j_c/launch_time_path_feasibility/<authorized-run-id>/**` only after a separate `offline_time_path_diagnostic_once` authorization; never committed.
- `<authorized-absolute-temporary-root>/{manifest.json,summary.json,review_CN.md}` only after a separate `offline_time_path_validation_once` authorization; never in the repository or formal data root.
- `.git/plan-execution/stage1_5j_c/<approved-plan-sha>/<authorized-run-id>/**` only where the separately authorized contract requires it; never committed.

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`
  - compatibility evidence: J-C invokes its public strict loader unchanged only after authorization; J-A regression suite stays green.
- `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py`
  - compatibility evidence: J-C imports only its public strict loader and `validate_zip_archive_package`; AST test forbids private reader imports; J-B regression suite stays green.
- `configs/base.py`, `configs/stage1_5j_b_historical_aggtrades_launch_response.py`, `scripts/governance/verify_artifact_schema.py`, `scripts/governance/verify_stage1_5j_b_receipt_schema.py`
  - compatibility evidence: before/after SHA identity; no diff allowed.
- JA/JB roots, J-B v2 closure evidence, V2 exports/ledger, existing receipts and historical `.git/plan-execution` trees.
  - compatibility evidence: pre/post seals and strict loader/verifier checks; no regeneration, cleanup, movement or overwrite.

Forbidden:
- Any mutation outside this whitelist, including `AGENTS.md`, rules, roadmap, existing config, exporter, verifier or J-A/J-B code.
- Network transport, collector, service, scheduler, database, cache, registry, generic backtest/factor framework, new dependency, output-root override or parameter override.
- Importing/exposing J-B private `_open_verified_package_stream` / `_ChunkBoundedReader`, or adding an upstream wrapper.
- Any signal, consumer promotion, execution, paper/live trading, risk-limit, commit, push, deployment, SSH, VPS action, full-tree autofix/format or destructive cleanup.

## 1. Frozen Identity And Impact Map

Task 0 must compare these exact bytes before any edit. A mismatch is never a reason to rebaseline.

| Frozen item | Required identity |
| --- | --- |
| Design | path above; SHA `32d5130806489c0848748060835a7c0fb8f1715a3f9fb6b479c2f02cff5d4e45` |
| JA root | `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z`; manifest `b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf`; summary `722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b` |
| JB root | `data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z`; manifest `f0a8ac724925084161f6b9aa2dced5139b261707fda0f0f21ebd0eb6de3087fb`; summary `5ea0f1c87803114c4c6917cd0c3d24292948fa0e7066a80e0a2bce611e32546b`; review `17e9ffaa973923868621a8ee925dc811c15e12459924ee63897f9c21fcac317e` |
| Input ledger | `data/exports/stage1_5j_token_launch_classification_ledger_v2.csv`; SHA `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b` |
| Frozen code | `configs/base.py` `473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc`; J-B config `771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4`; J-A core `250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18`; J-B core `b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f` |
| Verifier/evidence | J-A verifier `7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473`; J-B v2 verifier `442c527fb7f49d78eff4e13fd68e5fabfff12ba1e74089cd5e5133977cde90f1`; J-B closure JSON `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/64e14726202b53727a7627139578369cb6af54f08d5a785d4df006009eb25a2d/evidence/receipt_closure_evidence.json`, SHA `8d535303d61b3860eaa69018eff3f76645f91b3e27af1af89e1e956b948f8b6d`, and its sidecar |
| New fixed protocol | `docs/production_artifacts/stage1_5j_c_time_path_protocol_v1.json`; SHA `4dd353751256191d75fc52388413d97e5a7b177e499bbee28e2dd2ff356e1cbe` |
| Execution authority, resolved only after Plan approval | external user approval record supplies `APPROVED_PLAN_RELATIVE_PATH` and `APPROVED_PLAN_SHA256`; Task 0 recomputes the current Plan bytes, records the exact approval text/SHA plus `BASE_SHA` and never replaces them from current workspace state |

| Component | Role | Change decision |
| --- | --- | --- |
| J-A strict loader | authentic `archive_package_records` admission | compatible, unchanged |
| J-B strict loader | anchor and child-set admission | compatible, unchanged |
| J-B public ZIP validator | resource precheck | compatible, unchanged |
| J-C core / CLI / Rule 17 verifier | consumer, producer and structural verifier | new |
| Existing J-A/J-B verifiers | upstream structural evidence only | unchanged; not a J-C fallback |

Graphify `affected` identifies only existing J-B core/CLI/test consumers of the J-B strict loader. `rg` and source inspection confirm that no J-C consumer exists. The persisted Graphify graph is advisory; exact imports and the unchanged J-A/J-B regression suites are the compatibility proof.

## 2. Invariant-To-Task Matrix

| Design invariant | Task(s) | Mechanical proof and failure owner |
| --- | --- | --- |
| INV-01 identity/no rebaseline | 0, 1, 2, 4, 6 | frozen SHA/import tests; `STOP=stage1_5j_c_authority_mismatch` |
| INV-02 Custodian release first | 1, 4, 5 | no-writer scan, write sentinel, missing-release loader sentinel; CLI preflight |
| INV-03 281 universe and 71 x 2 scope | 2, 3, 5 | duplicate/AIA/cross-parent tests; domain replay |
| INV-04 persisted package admission | 2, 5 | isolated package/path/checksum/symlink mutations; loader/admission |
| INV-05 exact timing/order | 1, 2 | 63/64, 899/900, same-ms ID, UTC and no-trade tests |
| INV-06 first-passage semantics | 1, 2 | order, jump, equality, neither and rounding tests |
| INV-07 gaps/nulls | 2, 3, 4 | state precedence, no-zero and Parent/group insufficient tests |
| INV-08 fixed scenario/no network | 1, 2, 4, 6 | protocol SHA, AST/import scan, 4 groups x 3 costs |
| INV-09 bounded resources | 2, 5 | observed `readinto`, ZIP/CSV/ratio/line/root/free-space and RSS evidence |
| INV-10 raw-to-output chain | 3, 5 | PRL gap oracle, lexicographic positive oracle, raising sentinel, replay |
| INV-11 crash/collision safety | 3, 4, 5 | four durability faults, collision matrix, lifecycle predicate |
| INV-12 scope/permission isolation | 0, 4, 6 | diff/index/untracked union, L0 assertion, scanner actual RC |

## 3. Task 0: Baseline, Authority, And No-Touch Ledger

**Invariants:** INV-01, INV-12.
**Files:** no product/test edits; record only the resumption inventory in the implementation handoff/review packet, and record execution evidence only under a later authorized evidence path.

1. Before the first test or `src/` edit, create the R1 resumption inventory required above. Read any discoverable original-Plan Task-0 baseline, task transcript, review finding and evidence path, but classify unavailable/unreadable material as `scope_provenance_uncertain`; do not fabricate a replacement historical baseline. Record each existing J-C whitelist file's physical SHA and Git state, then preserve it until a minimal defect is identified.
2. Read the user-provided R1 Plan implementation approval record. Extract `APPROVED_PLAN_RELATIVE_PATH` and `APPROVED_PLAN_SHA256`, require the approved path to be this Plan, recompute its physical SHA and require equality. Record the approval record, approved Plan SHA, `BASE_SHA=$(git rev-parse HEAD)`, resumption inventory, `git status --short --untracked-files=all`, tracked/staged diffs and the SHA ledger in the implementation handoff/review packet as immutable Task-0 evidence; do not materialize a `.git/plan-execution` or runtime artifact for this purpose. The scanner in Task 4.5 and the final audit in Task 6 must use this recorded `BASE_SHA`, not a freshly substituted HEAD.
3. Recompute the Design SHA and all frozen tuples. A mismatch stops as `STOP=design_authority_mismatch`, `STOP=approved_authority_mismatch` or `BLOCKED_SPEC_DRIFT`.
4. Assert `RISK_LIVE_TRADING_ENABLED is False`, require an empty index, and record the exact J-C whitelist. Preserve pre-existing dirty/untracked paths; do not reset, clean, delete or reattribute them. The current untracked Design and the Plans are authority/documentation bytes, not implementation output to overwrite.
5. Confirm the protocol file is absent or exactly matches the Design bytes/hash. If it exists but differs, stop rather than normalize it. An existing matching protocol remains `present_unverified` until current protocol tests pass.

```bash
BASE_SHA=$(git rev-parse HEAD)
git status --short --untracked-files=all
git diff --name-status "$BASE_SHA"
git diff --cached --name-status
git diff --cached --quiet
shasum -a 256 docs/designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md
shasum -a 256 docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md
PYTHONPATH=src:. .venv/bin/python -c 'from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False'
```

Expected: approved Design and externally approved Plan hashes both match, index is empty and safety assertion has `RC=0`. Otherwise do not start RED tests.

## 4. Task 1: Fixed Protocol And RED Semantic/Authority Tests

**Invariants:** INV-01, INV-02, INV-05, INV-06, INV-08.
**Files:** create missing protocol/test files, or narrowly revise existing protocol/test files only after Task-0 resumption inventory and a current defect finding.

1. If the protocol file is absent, write the sole canonical protocol JSON specified by the Design: UTF-8, sorted keys, compact separators, one LF and the fixed SHA. If it exists, first verify those exact bytes and only repair it after a recorded current defect finding; never overwrite a mismatched existing protocol during resumption. Test exact keyset/types/bytes and reject altered, missing or extra values. It is not a `configs/` setting and cannot be overridden by CLI/environment/test defaults.
2. Write RED tests first for pure stdlib semantics: UTC integer milliseconds; `T0 + 60000 + 3000`; first entry in its exact 1000ms window; last endpoint in its exact 1000ms window; aggregate-ID/physical row ordering; `Fraction` values; first passage. Cover 63/64 seconds, 899/900 seconds, one-millisecond exclusion, same time/different ID, threshold equality, risk jump, neither, cross-midnight, no entry and no endpoint.
3. Add RED tests for the exact 11-line ASCII/LF approval grammar, both two-space sidecar grammars, exact release keys/false flags, the sorted 11-file source bundle and derived authorization. A locally self-consistent approval/sidecar/derived JSON without release must stop before a monkeypatched upstream-loader sentinel.
4. Add AST/import tests forbidding network transport, `scripts` imports in core, J-B private helpers, whole-file ZIP/CSV reads, parameter-search loops and production test-writer capability.

**RED gate:** new remediation nodes must fail because J-C behavior is absent. Existing negative guards may remain green. Do not weaken them to create universal RED.

## 5. Task 2: Read-Only Admission And Bounded Stream Reducer

**Invariants:** INV-01, INV-03 through INV-09.
**Files:** create `src/research/external_signal_shadow/stage1_5j_c_launch_time_path_feasibility.py` only if absent; otherwise narrowly revise it and its domain test only after Task-0 resumption inventory and a current defect finding.

1. Create a minimal stdlib core only if absent; otherwise retain the current core and make only a recorded minimal defect repair. In either case it reads the protocol, validates frozen identity, then accepts only objects returned by public J-A/J-B strict loaders. It must never derive package records from filenames, hand-written dicts or the V2 wide table.
2. Parse the ledger's exact 12 columns; require a unique 281-key bijection with J-B child rows; independently check selected classification evidence against the J-A article. Preserve all 71 selected rows and produce 142 direction rows without treating directions as independent events.
3. Own J-C package admission and its local bounded reader: verify five-field identity, admitted state, manifest/request linkage, containment/no symlink, exact checksum/actual SHA, J-B public `validate_zip_archive_package`, frozen 65,536-byte cap, one member/header and every CSV field/order constraint. Never use J-B private helpers, extract a ZIP, persist raw rows or repair malformed input.
4. Stream every required package to EOF before accepting a child. Compute `TradeRef`, terminal/MFE/MAE, first touch and intertrade gap with exact rational values. Identity/syntax/resource faults stop; only already-admitted business gaps map to the exact `Child.state` and null behavior.
5. Turn RED nodes green using isolated synthetic and archive fixtures: invalid checksum/path/symlink/unadmitted dict/wrong Parent-date/header/Decimal/order/line/ZIP cap, duplicate ledger key and AIA cross-Parent borrowing. Observe actual underlying `readinto` requests through a test monkeypatch; do not add global production test state.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py
```
Expected: `RC=0`; raw integrity violations never downgrade to business gaps.

## 6. Task 3: Projection, Publication, Domain Replay, And Oracles

**Invariants:** INV-03, INV-06, INV-07, INV-10, INV-11.
**Files:** modify only the J-C core and domain test.

1. Implement exact child -> Parent -> four-group reduction. Parent requires every selected child complete; statistics recompute from rationals; all three cost rows are emitted; incomplete/empty groups remain `evidence_insufficient`; no best cost/direction selection.
2. Canonically serialize only `manifest.json`, `summary.json`, `review_CN.md` and implement a strict J-C domain loader with explicit expected `artifact_kind`. It must independently replay raw input and reject semantically forged but structurally self-consistent child/Parent/group/prose output.
3. Implement single-process atomic publication: exclusive sibling lock/staging, each file fsync, staging fsync, rename, parent fsync. `PublishResult` exists only after parent fsync. Existing root/lock/staging, stale state, run-id reuse or source drift fail closed without cleanup/overwrite.
4. Implement independent oracle code: fixed PRL gap oracle for Parent `0116dd83010043bd95c37626e2277bbe`, plus lexical `(parent_article_id,symbol)` first complete positive oracle. Neither calls production parser/reducer/stat helpers. Add AST dependency proof and a production-helper raising sentinel.
5. Test four durability faults; root/lock/staging collisions; lifecycle non-success; forged extrema/touch/projection; review mutation; PRL same-gap and positive-oracle parity. All mutations use `tmp_path` physical copies only.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py \
  -k 'publication or durability or oracle or domain_loader or projection'
```
Expected: `RC=0`; parent-fsync failure never satisfies completion.

## 7. Task 4: CLI, Custodian Boundary, Lifecycle Evidence, And Rule 17 Verifier

**Invariants:** INV-01, INV-02, INV-07, INV-08, INV-11, INV-12.
**Files:** create missing J-C CLI/verifier/test paths, or narrowly revise existing CLI/verifier/test paths only after Task-0 resumption inventory and a current defect finding.

1. CLI accepts only documented operation/run ID. It has no root/upstream/protocol/permission/skip-check override and enforces: readonly approval/release + sidecars -> grammar/release tuple -> physical Design/Plan/source/input identity -> derived authorization -> public upstream loaders. Contract failure is `RC=1`; CLI usage is `RC=2`.
2. Prove Custodian isolation statically and at runtime. No core/CLI code path writes, renames, unlinks or repairs approval/release. A write-sentinel fails on such attempt. Only valid external release permits derived `run_authorization.json`; only successful parent-fsync publication permits lifecycle evidence plus sidecar. Evidence-write failure makes CLI nonzero.
3. Build the standalone stdlib J-C Rule 17 verifier. It imports neither producer nor loader, owns literal profile/version/protocol/key/enum/closed-tree checks and validates only the supplied artifact root and artifact bytes. For `validation_only`, it requires an absolute supplied root, no symlink ancestor, `artifact_kind=validation_only`, the frozen run-id grammar and the sealed three-file tree; for `production_diagnostic`, it requires the canonical project-relative root form and `artifact_kind=production_diagnostic`. It must not silently coerce either root type. It must not read approval/release/derived-authorization files or `.git` authority state, invoke CLI authorization logic, or require a later audit record. CLI preflight owns the external approval/release/derived-authorization and output-root comparison, including the temporary root's absence and location outside the repository/formal data root; the independent auditor rechecks that cross-process tuple.
4. Implement and test the following complete independent-verifier matrix. The verifier checks structural/conditional relations from artifact bytes; Task 5 domain replay independently checks raw semantics, and Task 6 independently recomputes external file bytes. No layer may substitute for another. The Task-4 positive fixture is a test-local, `tmp_path`-only schema unit fixture built by an independent literal test serializer; it must not import/call the producer, domain loader or CLI, and its FileSeal strings are grammar values only, not assertions of an upstream source identity.

| Contract relation | Independent verifier requirement | Negative test reaching this verifier |
| --- | --- | --- |
| profile/root/tree | exact profile/version, `artifact_kind`, run-id grammar, root type, canonical JSON/no duplicate keys, only `manifest.json`, `summary.json`, `review_CN.md`, manifest seals | wrong kind/root pairing, absolute formal root, relative validation root, extra file, symlink, malformed JSON/duplicate key |
| receipt-local authority/protocol/permissions | exact embedded Authority and Permissions keysets; Design seal path/SHA; Plan/user/release/derived FileSeal grammar; exact fixed protocol; all eight permission booleans false. The verifier neither reads nor compares external approval/release/derived-authorization files. | wrong Design SHA/path, malformed embedded seal, altered protocol value, true permission |
| source/input identity sets | exactly 11 sorted unique `source_files` paths and exactly 9 sorted unique `input_files` paths, with Design-required path identities and SHA grammar; no duplicate/extra/omitted entry | missing/extra/reordered source or input, duplicate path, invalid SHA/size/path |
| universe/child conditional contract | 281 sorted unique Universe keys; selected 71 keys and exactly 142 sorted direction rows; allowed labels; every Child `state` has the Design-prescribed null/non-null `TradeRef`, metric, first-touch and `max_intertrade_gap_ms` combination | duplicate/missing key, wrong direction/regime, gap with fabricated metric, complete with null required field, invalid touch trade |
| Parent/Group projection contract | Parent identity/symbol membership/date ordering/count relations, complete/gap conditional fields, exact four `(listing_regime,direction)` Groups, child/Parent totals and cost rows `50/80/150`, touch count/fraction/concentration shape | wrong membership/count, incomplete Parent with metrics, missing group/cost, malformed fraction/concentration |
| review projection | `review_CN.md` exactly equals the independent literal renderer projection of summary and ends with the frozen non-authority sentence | review text/hash mismatch or semantic field omitted |

5. Confine CLI seams to `tmp_path`; they never materialize canonical `.git` authority files or select production roots. CLI tests own missing release, source-bundle mismatch, true permission, authority-file symlink, and a physically valid temporary root whose external release/derived `output_root` is mismatched: each must stop before the loader sentinel. Verifier tests own both root-kind mismatches, artifact-root symlink, sealed-tree/canonical-JSON failures and an import/read guard proving the verifier neither imports CLI/producer/loader nor reads `.git` authority state. The verifier-positive schema unit must be labelled `tier=schema_unit_only` in test evidence and must contain an assertion that it makes no source/provenance/semantic claim. Test collision, lifecycle predicate and actual process RC at their Design-assigned owner.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_c_launch_time_path_feasibility.py \
  tests/scripts/governance/test_verify_stage1_5j_c_receipt_schema.py
python scripts/governance/verify_stage1_5j_c_receipt_schema.py --help
```
Expected: `RC=0`; `--help` reads no raw input and starts no producer.

## 8. Gate 4.5: Independent Pre-Validation Code Review

**Invariants:** INV-01 through INV-12, before any real raw-input validation.
**Files:** no product changes; reviewer receives the exact diff and Task-0 baseline evidence.

1. After Tasks 0-4 are GREEN, run the complete local J-C suites, scoped Ruff, anti-shortcut scanner, L0 assertion, no-network/no-private-import AST tests and Task-0 scope/index proof. Record actual process RC, scanner source SHA and every warning disposition.
2. Submit the exact diff, approved Plan SHA comparison, recorded `BASE_SHA`, Task-0 tracked/staged/untracked ledger, authority boundary tests, Rule 17 matrix results, publication-fault matrix and affected-but-unchanged SHA ledger for independent code review.
3. Only an independent review with no P0/P1 in the completed **pre-authorization** Tasks 0-4 allows requesting the separate `offline_time_path_validation_once` approval/release. The review must record `tier4_real_positive_evidence=not_yet_authorized` rather than treating its absence as a Task-4 defect. The reviewer cannot replace that authorization, and a Task-4 schema unit fixture cannot stand in for it.
4. If review or a subsequent fix changes any of the 11 source files, CLI/verifier behavior, exact protocol or artifact contract, invalidate this Gate and Task 5 eligibility. Return to the appropriate RED task, repeat Gate 4.5, then obtain a newly bound source-bundle authorization and a new RUN_ID. Do not attach a prior validation root to changed source bytes.

**Expected result:** all local gates have actual `RC=0`, independent pre-validation review has no P0/P1 in its allowed scope, `tier4_real_positive_evidence=not_yet_authorized`, and no raw JA/JB consumer or runtime root has yet been invoked/created.

## 9. Task 5: Separately Authorized Canonical Validation And Negative Matrix

**Invariants:** all; primary owners INV-02, INV-04, INV-09 through INV-11.
**Files:** no code changes; only later authorized temporary/evidence paths.

This task is blocked until Gate 4.5 has no P0/P1 **and** a separate exact `offline_time_path_validation_once` authorization/release exists. Plan implementation approval alone is insufficient. Do not invent approval/release or replace raw input with a mock.

After authorization, run exactly one canonical validation to its authorized absent temporary root. This is the first and only Tier-4 positive cross-boundary proof: the root must be produced by the actual J-C CLI from the frozen J-A/J-B inputs, not by a fixture, hand-written receipt, mock loader or test serializer. Then independently run:

```bash
.venv/bin/python scripts/governance/verify_artifact_schema.py \
  --profile stage1_5j_a_receipt_v2 \
  --artifact-root data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
.venv/bin/python scripts/governance/verify_stage1_5j_b_receipt_schema.py \
  --profile stage1_5j_b_receipt_v2 \
  --artifact-root data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z
.venv/bin/python scripts/governance/verify_stage1_5j_c_receipt_schema.py \
  --profile stage1_5j_c_time_path_v1 \
  --artifact-root <authorized-absolute-validation-root>
```

`<authorized-absolute-validation-root>` is the exact absolute path in the user approval, Custodian release and derived authorization. CLI preflight independently compares that external tuple, requires the root to be absent before production, outside the repository and formal J-C data root, and rejects a project-relative validation root, a formal data root or a mismatched `artifact_kind` before any upstream loader. The producer and domain loader receive the resulting explicit root; the J-C verifier receives the invoked artifact root but checks only its literal-profile path form, sealed tree and artifact bytes, never external authority files. The independent auditor later compares the approval/release/derived tuple, producer, domain-loader and verifier invocation records with the final root. Each command must return actual `RC=0`; record its source SHA and stdout/stderr. The J-C verifier checks its independently frozen profile tuple, while the J-C domain replay below checks raw semantics. Neither substitutes for the other.

1. Run J-C domain replay with explicit `validation_only`, standalone J-C verifier, frozen J-A/J-B verifier commands and physical three-file hashes. Record the CLI invocation and actual `RC=0`, J-C domain replay `RC=0`, J-C Rule 17 verifier `RC=0`, and the common physical root/hash tuple. This four-way agreement is the sole positive evidence for raw-to-output/provenance compatibility.
2. Run PRL gap and lexical positive semantic oracles. Record the selected positive key before any outcome comparison. `positive_semantic_evidence_unavailable` is closure-incomplete, never a sample-switch invitation.
3. In `/tmp` isolated physical copies, mutate source/package/checksum/path/symlink; receipt-only structure; raw-vs-receipt self-consistent semantic data; locally self-consistent authorization with missing Custodian release; a structurally valid `validation_only` receipt with an external release/derived `output_root` mismatch; and parent fsync after rename. Root-kind, artifact-root symlink and sealed-tree mutations must reach the standalone verifier; the external root-tuple mutation must fail in CLI preflight before the loader and in the independent-auditor comparison if introduced after production. Each probe must fail at its Design-assigned owner and record actual RC.
4. Record actual readinto cap, ZIP/CSV/ratio/line/root/free-space checks, peak RSS and full EOF processing. Scanner warnings receive an individual disposition; nonzero scanner never becomes `clean`.

Any missing authorization, changed source bundle, unexpected raw write, nonzero CLI/verifier/replay/oracle or visible root after parent-fsync failure stops. A validation-only root is not a production receipt. Until this task completes, the only permitted status is `not_yet_authorized` or `incomplete`; a green Task-4 schema unit is never positive validation evidence.

## 10. Task 6: Final Regression, Source-Bundle Recheck, And Completion Handoff

**Invariants:** INV-01 through INV-12.
**Files:** no additional product changes.

1. Recompute and compare the external authority tuple before any final claim: Governance Rule 17 parent Design path/SHA `docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md` / `73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4` -> approved J-C Design path/SHA -> approved Plan path/SHA -> profile `stage1_5j_c_time_path_v1` / version `1` -> J-C verifier path/SHA -> user approval/Custodian release/derived authorization `run_id` and `output_root` -> producer, domain-loader and verifier invocation records -> final artifact run-id/root and physical manifest/summary/review seals. This is an external audit comparison, not a producer/verifier self-assertion. Recompute all 11 source and 9 input seals, then compare the source-bundle SHA to the user approval, release and derived authorization.
2. Run the new J-C suites and unchanged J-A/J-B regression suites:
```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_c_launch_time_path_feasibility.py \
  tests/scripts/governance/test_verify_stage1_5j_c_receipt_schema.py
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py
```
3. Record actual quality/safety gate RCs. Ruff is scoped to the six new J-C files; scanner source SHA, command, actual RC and every warning disposition are evidence. The scanner receives the immutable Task-0 `BASE_SHA`, not current HEAD.
```bash
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_5j_c_launch_time_path_feasibility.py \
  scripts/external_signal_shadow/run_stage1_5j_c_launch_time_path_feasibility.py \
  scripts/governance/verify_stage1_5j_c_receipt_schema.py \
  tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_c_launch_time_path_feasibility.py \
  tests/scripts/governance/test_verify_stage1_5j_c_receipt_schema.py
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"; scanner_rc=$?
printf 'scanner_rc=%s\n' "$scanner_rc"
test "$scanner_rc" -eq 0
git diff --check
git diff --cached --check
git diff --cached --quiet
PYTHONPATH=src:. .venv/bin/python -c 'from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False'
```
4. Prove `HEAD == BASE_SHA`, empty index and tracked/staged/untracked union matches Task-0 ownership ledger. Only the seven whitelist implementation/test/protocol paths, this Plan and explicitly pre-existing paths may differ. Recompute all affected-but-unchanged hashes. HEAD change is `STOP=commit_forbidden_head_changed`.
5. Confirm the Task 5 authorization/source bundle/RUN_ID remains bound to unchanged source bytes. If code changed after Gate 4.5 or Task 5, invalidate the old validation result and return to Gate 4.5 plus a new authorization/RUN_ID; do not use final review to bless mismatched evidence.
6. A fresh independent completion auditor uses `.agent/skills/audit-plan-completion/SKILL.md` and reads the Task-0 resumption inventory, pre-validation review and actual Task 5/6 evidence. The audit must distinguish inherited implementation bytes, R1 modifications and current re-execution evidence; it must reject any attempt to close an R1 requirement with an original-Plan review, old GREEN, old source bundle or old validation root. It must also reject any claim that a Task-4 schema unit fixture proves source provenance, raw semantics or Tier-4 positive acceptance; it must require the Task-5 actual CLI/domain-replay/verifier root/hash tuple. Executor summaries are not proof. No new final code review substitutes for Gate 4.5 unless code changed, in which case Gate 4.5 repeats.

## 11. Rule-12 Routing And Completion Boundary

| Condition | Required route |
| --- | --- |
| Approved Design/Plan/user bytes, frozen tuple or protocol hash differs | `STOP=approved_authority_mismatch` or `BLOCKED_SPEC_DRIFT`; never rebaseline |
| Repair stays within this whitelist and preserves fixed Design contract | `BLOCKED_IMPLEMENTATION_DEFECT`; RED -> minimal fix -> GREEN |
| Repair needs J-A/J-B/config/ledger/existing verifier/risk-rule change, dependency/data source or scenario change | `BLOCKED_SCOPE_DRIFT`; return to Design |
| Frozen source contract contradicts Design | `BLOCKED_SPEC_DRIFT` with invariant/source/contradiction packet |
| Original-Plan Task-0/task/evidence record is absent or unverifiable | record `scope_provenance_uncertain`; grant no inherited GREEN or Task-5 credit, preserve current bytes and re-establish evidence only through R1 Task 0/current process RC |
| Resumption inventory finds an existing path outside the whitelist, an unrecorded overwrite, or an inability to preserve existing bytes while repairing | `BLOCKED_SCOPE_DRIFT`; do not rebaseline, clean or reattribute work |
| Custodian release or runtime authorization is absent | stop at Task 5; no raw consumer invocation |
| A Task-4 synthetic/schema fixture is presented as a canonical upstream fixture, source-backed receipt or Tier-4 positive proof | `BLOCKED_SPEC_DRIFT`; reject the claim and retain `not_yet_authorized` until Task 5 |
| Closing the Task-4/Task-5 proof gap requires a new J-A/J-B fixture factory, serializer, source contract or upstream artifact | `BLOCKED_SCOPE_DRIFT`; return to Design rather than extending this Plan |
| Code, protocol, verifier or source bundle changes after Gate 4.5 or validation authorization | invalidate validation eligibility/result; repeat Gate 4.5 and obtain new source-bundle release plus RUN_ID |
| Scanner nonzero, scope/index fails, safety false, production-root test write or reachable network import | stop; `BLOCKED_SCOPE_DRIFT` unless a narrower approved-path defect is proven |

This R1 candidate is ready only for independent Plan review. A later R1 Plan approval would authorize implementation within `Allowed Change Scope`, not raw validation or formal J-C receipt generation. Completion also never authorizes consumer promotion, alpha/execution claims, paper/live trading, commit, push or deployment.
