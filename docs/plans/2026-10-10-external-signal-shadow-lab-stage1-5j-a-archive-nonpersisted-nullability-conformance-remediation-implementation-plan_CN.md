# Stage 1.5J-A Archive Nonpersisted Nullability Conformance Remediation Implementation Plan

> **For Codex:** 实施时必须逐任务执行；先完成对应 RED 测试与门禁，再写最小生产代码。未经 Plan Review 为 `RECOMMEND_APPROVE` 且用户明确批准本 Plan，不得执行任何任务。

**状态:** `draft_for_independent_review`

**Goal:** 在不改变 J-A archive universe、journal、date-set、parser、reducer、CLI 或权限边界的前提下，使 producer 与 strict loader 对 `archive_request_nonpersisted` 的四个 trade fields nullability 以及 declared-child launch-time admission 同时 fail-closed。

**Architecture:** 仅在既有 J-A core 中增加两个私有、确定性的结构检查路径：一个复用的 positive non-bool integer launch-time predicate，及一个仅检查 nonpersisted 四字段为 `None` 的 archive-record validator。producer 在任何 archive 身份或请求生成前执行 launch-time admission；strict loader 从原始详情重新投射后独立重放相同 admission，并在 raw-file replay 分支前调用同一 record validator。没有新 public API、schema framework、配置、网络测试接缝或兼容模式。

**Tech Stack:** Python 3 standard library、现有 J-A core、pytest、Ruff、Git、现有 anti-shortcut scanner。

---

## 1. Approved Design Binding

| Item | Exact value |
| --- | --- |
| Approved remediation Design | `docs/designs/2026-10-09-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-design-delta_CN.md` |
| Approved remediation Design SHA-256 | `f427df9435c8b9c8dd2b4b45c24bbbbd595df2c7e8d209f40f6fe2cd13b00f3c` |
| Parent J-A Design | `docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md` |
| Parent Design SHA-256 | `b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a` |
| Prior remediation Delta | `docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md` |
| Prior remediation Delta SHA-256 | `6063ed103d31fcf6c60ad8106eb13650f54b74272182c78bf8e81f9ba48a91ac` |
| Task 0 required baseline HEAD | `647fae2cf3ba09efc1971bb1a87a30e18b86dd5b` |
| Current audited core SHA-256 | `c2127ebd83734c6272fd85044e661a21419e6511d01037ca6dcd9be5b1a9a43e` |
| Current audited test SHA-256 | `94b9459d18cb4da628bea6b236c233f1d3b7465b3d5b9f71bf6099e95299848a` |
| Approved Plan identity | 仅在 Model B review 为 `RECOMMEND_APPROVE` 且用户提交 exact Plan approval sentence 后，由 Task 0 解析并重新计算本文件 SHA-256；当前候选 SHA 不构成实施授权。 |

The authority chain is additive and exact:

```text
parent J-A Design (b74c306e...fc15a)
+ prior remediation Delta (6063ed10...a91ac)
+ approved nullability Delta (f427df94...00f3c)
```

Task 0 must recompute all three files from disk. If any path, byte sequence, or hash differs, stop before editing with:

```text
STOP=stage1_5j_a_design_authority_chain_mismatch
```

This Plan is not an implementation, commit, push, deployment, SSH, network, receipt-generation, replay, J-B consumption, paper-trading, live-trading, execution, or Alpha authorization.

## 2. Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py`

Allowed documentation paths:
- none. The user-approved Plan, current Delta, parent Design, and prior Delta are immutable read-only authority during execution.

Allowed generated/runtime artifacts:
- `.git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>/{base_sha,execution_authority.json,execution_authority.sha256,implementation_authorization.txt,implementation_authorization.sha256}` created exactly once by Task 0 after the user's exact Plan approval; never committed.
- `.git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>/evidence/**` for the create-once Task 0 provenance ledger, Task 5 review evidence, and Task 6 audit evidence; never committed.
- `data/<exact-run-root>/**`: none. This Plan prohibits creating, copying, editing, deleting, manifest-rehashing, or rebinding any receipt.
- `graphify-out/<exact-generated-file>`: none.

Affected but unchanged:
- `scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py`
  - compatibility evidence: Task 0 proves through `rg`/AST inspection that it imports Core identity constants rather than hard-coding the Design/Plan identity, then its existing delegation test remains green.
- `configs/base.py`
  - compatibility evidence: `RISK_LIVE_TRADING_ENABLED is False`; no threshold or flag change.
- `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
  - compatibility evidence: its frozen SHA remains `7e0e696647acf158facbdd8d3d39351bbc68c33b039871f26f4a38bc75ad56e5`; parser output is consumed but not altered.
- `tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/**`
  - compatibility evidence: canonical GRVT component Proof B runs unchanged; it is not full-receipt positive evidence for this repair.
- `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z/**`
  - compatibility evidence: Task 0 and Task 5 compare its recorded hashes before/after; public loader fails closed under the new authority identity.
- `.agent/tools/anti_shortcut_scan.py`
  - compatibility evidence: scanner runs unmodified and actual process exit code is recorded.

Forbidden:
- Any mutation outside the allowed paths.
- `configs/base.py`, the frozen parser, J-A CLI, fixture bytes, parent Design, prior Delta, prior Plan, Governance Design/verifier, J-B, roadmap, project-status files, network profile, universe window, journal grammar, Decimal validation, UTC date-set logic, or coverage reducer changes.
- Any change to existing `data/` roots, including a copy, test cleanup, synthetic full receipt, rebind, fallback, manifest edit, or compatibility conversion.
- Network calls, network authorization creation, receipt generation, deployment, SSH, replay, signal generation, paper/live trading, execution, Alpha/economic/PIT/price-response claim.
- Unrelated formatting, full-repository autofix, `ruff check --fix .`, `git clean -fdx`, `git reset`, `git rebase`, or automatic commit.

## 3. Invariant-to-Task Map

| Invariant | Production boundary | Required task and proof | Fail-closed condition |
| --- | --- | --- | --- |
| `INV-15J-A-N-00` | producer detail admission and strict-loader detail replay | Tasks 1-3: six invalid launch-time values reduce to unresolved; loader accepts only unresolved representation and rejects forged validated representation | existing reduction mismatch STOP; no archive request/record may be emitted |
| `INV-15J-A-N-01` | producer valid nonpersisted record construction | Tasks 1-2: all four trade fields are `None`; production construction calls shared validator | exact nullability STOP |
| `INV-15J-A-N-02` | strict-loader archive-record replay before raw-branch selection | Tasks 1-2: loader invokes the same private validator before persisted/nonpersisted selection | exact nullability STOP before raw-file acceptance |
| `INV-15J-A-N-03` | shared validator | Task 1: four single-field mutations; required `post_launch_row_count: None -> 0` mutation reaches the validator | `STOP=stage1_5j_a_archive_package_record_invalid:archive_request_nonpersisted_trade_fields_must_be_null` |
| `INV-15J-A-N-04` | legacy receipt / public loader | Tasks 0 and 4: old root bytes unchanged and public loader rejects authority identity | no fallback, rebind, or schema relaxation |
| `INV-15J-A-N-05` | process boundary | Tasks 0, 4-6: no output root, no network authorization, all flags remain false | stop on scope or authority drift |

## 4. Task 0: Freeze Authority, Baseline, and Immutable Evidence

**Invariants:** all. This task writes no production code and makes no receipt change.

**Files:**
- Create only after the exact user Plan-approval sentence validates: `.git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>/{base_sha,execution_authority.json,execution_authority.sha256,implementation_authorization.txt,implementation_authorization.sha256,evidence/**}`.
- Read: all three authority Designs, this approved Plan, current core/test, CLI/config/parser, canonical fixture, and every existing J-A output root.

**Step 1: Parse the exact user Plan approval and validate all immutable authority bytes before any write.**

The executor must extract only the Plan path and SHA from the user's exact two-line approval sentence. It must recompute this Plan from disk and require equality. It must then recompute the three Design chain hashes, verify `HEAD == 647fae2cf3ba09efc1971bb1a87a30e18b86dd5b`, require an empty Git index, and require the current core/test hashes exactly equal the values in section 1. No authority directory or evidence file may exist or be written before all these checks pass.

Run:

```bash
set -euo pipefail
test "$(git rev-parse HEAD)" = "647fae2cf3ba09efc1971bb1a87a30e18b86dd5b"
git diff --cached --quiet
shasum -a 256 \
  docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md \
  docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md \
  docs/designs/2026-10-09-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-design-delta_CN.md \
  docs/plans/2026-10-10-external-signal-shadow-lab-stage1-5j-a-archive-nonpersisted-nullability-conformance-remediation-implementation-plan_CN.md \
  src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py
```

Expected: each SHA exactly matches its bound source or the parsed user approval. Any missing/mismatched Design chain is `STOP=stage1_5j_a_design_authority_chain_mismatch`; a Plan mismatch, stale core/test byte, nonempty index, or stale baseline is `STOP=approved_authority_mismatch`. None may be repaired by changing the Plan, baseline, or expected hash.

**Step 2: Build pre-execution immutable provenance in memory.**

Capture `git status --short --untracked-files=all`, `git diff --name-only`, and `git diff --cached --name-only`. For every pre-existing dirty/untracked path and every frozen authority/compatibility input, compute `path`, `type`, `byte_count`, and SHA-256. The frozen set must include the three Design-chain files, the approved Plan, core/test baseline, CLI, config, frozen parser, all five canonical fixture files, and all four top-level witness files in the legacy `20261008T160500Z` root.

Build a separate sorted output-parent ledger for every direct child directory of:

```text
data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/
```

Each row is `{relative_root_path, manifest_sha256}`. The expected current root set is the three dated roots present at Task 0; do not hard-code their count as a substitute for recording the actual rows. Any path that appears after this snapshot, any changed pre-existing byte, or any allowed core/test overlap before Task 1 is `STOP=stage1_5j_a_task0_baseline_mismatch`. Do not clean, revert, stage, overwrite, or rebaseline it.

**Step 3: Perform targeted topology and CLI compatibility discovery.**

Run these exact Graphify queries when Graphify is available and current:

```bash
graphify query "run_inventory"
graphify query "load_verified_stage1_5j_a_historical_archive_coverage_root"
graphify query "validate_archive_package"
graphify query "RequestManager"
```

If Graphify is unavailable or stale, record that fact and run equivalent `rg -n` searches over `src/`, `scripts/`, and `tests/`, followed by direct source inspection. Classify every result as `modified` or `compatible_unchanged`; record the classification in Task 0 evidence. The CLI check must prove whether the CLI imports Core Design/Plan constants dynamically. If it hard-codes either identity or a corresponding test has stale literal expectations, stop as `BLOCKED_SCOPE_DRIFT` before implementation because CLI/test changes are outside this Plan's whitelist.

**Step 4: Verify canonical fixture provenance for all planned positive component evidence.**

Require `git ls-files tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/` to return exactly the frozen five files. Record their hashes and the frozen parser SHA. Task 1's unmutated base projection must be obtained by passing the canonical article-detail bytes to the frozen parser and asserting the resulting production projection before a single `launch_time_ms` mutation. A hand-written positive parser projection is prohibited.

**Step 5: Create the canonical implementation-authority bundle exactly once.**

Only after Steps 1-4 pass, set:

```bash
AUTHORITY_DIR=".git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>"
test ! -e "$AUTHORITY_DIR"
```

If it already exists, stop with `STOP=approved_authority_mismatch`; never overwrite or reuse it. Create the directory once and write exactly these five top-level files plus `evidence/`, with no canonical `network_authorization.txt` pair:

```text
base_sha
execution_authority.json
execution_authority.sha256
implementation_authorization.txt
implementation_authorization.sha256
evidence/
```

- `base_sha` is exactly `647fae2cf3ba09efc1971bb1a87a30e18b86dd5b\n`.
- `implementation_authorization.txt` is the exact two user-provided approval lines, UTF-8 and LF-terminated; it has no substitutions except the already parsed exact Plan path/SHA.
- `execution_authority.json` is canonical JSON, LF-terminated, has exactly the existing verifier's required key set, binds the current Delta path/SHA, the exact user-approved Plan path/SHA in both Plan-SHA fields, `base_sha=647fae...dd5b`, and the resolved project root.
- Each sidecar is exactly `<lowercase-hex-sha256><two spaces><referenced filename>\n` over its sibling's exact disk bytes.

Then materialize the in-memory `pre_execution_frozen_bytes.json`, its checksum sidecar, and the sorted output-parent ledger in `evidence/` without changing their precomputed contents. At this point the current core still intentionally binds the previous Design/Plan constants, so Task 0 verifies the new bundle's exact top-level entry set, canonical JSON, LF rules, and sidecars directly; it must not claim public-verifier success against old constants. Task 2 Step 4 performs the first public `verify_execution_authority()` positive load after atomically updating the matching constants. Missing file, old Plan/Design/baseline, unexpected top-level entry, noncanonical JSON, or sidecar mismatch is `STOP=approved_authority_mismatch`.

## 5. Task 1: Write RED Tests for the Frozen Contract

**Invariants:** `INV-15J-A-N-00`, `N-01`, `N-02`, `N-03`.

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py`
- Read only: `tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/**`
- Do not modify: fixture bytes or any root.

**Step 1: Add the smallest pure-record tests.**

Import the eventual private production validator, not a test-only clone. Use a local in-module record object only for this pure structural unit test; it makes no cross-boundary receipt claim.

Write one positive test where `child_state="archive_request_nonpersisted"` and all four fields are `None`. Write a parameterized negative test that changes exactly one field at a time from `None` to a non-null value. Include the required named case:

```python
("post_launch_row_count", 0)
```

Each negative case must assert exactly:

```text
STOP=stage1_5j_a_archive_package_record_invalid:archive_request_nonpersisted_trade_fields_must_be_null
```

**Step 2: Add launch-time admission RED cases derived from canonical fixture bytes through the frozen parser.**

Start every case from the real canonical GRVT article-detail bytes in `canonical_input_v1`, pass them through the frozen parser, and assert the unmodified projection identity (`parser_status`, ordered symbols, and `symbol_launch_times_ms`) before copying it. For each exact invalid value below, mutate only the declared child's `launch_time_ms` in that parser-produced projection:

```python
None, True, 0, -1, 1.5, "123"
```

Assert the actual production admission/replay path yields:

```python
candidate_status == "catalog_detail_unresolved"
detail_status == "detail_parser_unresolved"
children == []
parent_state == "coverage_evidence_gap_detail"
```

Record the canonical fixture SHA and frozen parser SHA in the test assertion/evidence. Also assert zero archive identity, UTC date, archive record, and HTTP-request construction. Do not create a handcrafted positive projection/full receipt, mock a successful transport, or introduce a parallel test reducer.

**Step 3: Add strict-loader replay RED proof.**

Exercise the actual production loader replay helper/path with the same canonical-fixture-derived and singly mutated projection. It must accept only the unresolved parent representation above and reject the sibling forged representation:

```python
candidate_status == "resolved_target_parent"
detail_status == "validated_target_detail"
```

The forged form is one semantic state substitution; do not mutate raw files, authority packets, manifests, or unrelated summary fields. The positive part is a component/replay proof only, not a full-root positive claim.

**Step 4: Add production-wiring proof.**

Use AST inspection plus runtime symbol identity, following the existing Task 5 proof style, to show:

- `run_inventory` uses the production launch-time admission and invokes the private archive-record validator at the valid nonpersisted construction site before appending the row.
- `load_verified_stage1_5j_a_historical_archive_coverage_root` invokes that same validator before choosing the persisted/nonpersisted raw replay branch.

The test must fail if either call is removed or redirected to a test-only helper.

**Step 5: Run the focused tests before implementation.**

Run each new test node with `PYTHONPATH=src:. .venv/bin/python -m pytest -q <exact-nodeid>`. Expected: RED because the existing production code accepts at least `post_launch_row_count=0` and admits invalid launch-time representations. If a new negative test is green before the intended production path exists, stop with `STOP=stage1_5j_a_test_not_reaching_semantic_gate` and correct the test, not the Design.

## 6. Task 2: Implement the Minimal Shared Production Checks

**Invariants:** `INV-15J-A-N-00`, `N-01`, `N-02`, `N-03`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py`

**Step 1: Add the minimal private predicates in the existing core.**

Add only:

```python
def _is_positive_non_bool_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
```

and a private archive-package-record validator that, only when:

```python
record["child_state"] == "archive_request_nonpersisted"
```

requires the four frozen fields to be `None`, otherwise raises exactly the STOP in section 3. Do not add a public export, class hierarchy, registry, config switch, generic schema framework, new key-set rule, request-ID constraint, or fallback coercion.

**Step 2: Repair producer admission before archive work.**

At the existing parsed-detail branch in `run_inventory`, evaluate every declared child launch time with `_is_positive_non_bool_integer` before constructing children, dates, logical archive identities, request IDs, URLs, or package records. If any declared child fails, write the parent as:

```python
candidate_status = "catalog_detail_unresolved"
detail_status = "detail_parser_unresolved"
children = []
parent_state = "coverage_evidence_gap_detail"
```

and preserve only the already-required detail evidence. Continue without archive work for that parent. The former `utc_date="unknown"` nonpersisted row from a missing launch time must disappear because it is an invalid sibling state.

For the still-valid request-nonpersisted branch after a valid launch time and required date-set, construct all four trade fields as `None`, call the private validator, and only then append the record. Do not change transport behavior, journal entries, date calculation, checksum/ZIP request ordering, package validation, summary reduction, or authority flags.

**Step 3: Repair strict-loader independent replay.**

In `load_verified_stage1_5j_a_historical_archive_coverage_root`, after re-running the frozen parser on persisted detail bytes, independently apply `_is_positive_non_bool_integer` to every declared child. If any one is invalid, require the unresolved representation from Step 2 and require zero archive projection. Reject `validated_target_detail` for that parser projection through the existing reduction-mismatch failure path.

For every archive package record, call the private record validator before the raw archive persisted/nonpersisted branch. It must therefore reject an invalid `post_launch_row_count=0` before accepting missing raw files as a nonpersisted request. Do not make legacy roots compatible.

**Step 4: Update authority literals only after Task 0 validates the exact Plan approval.**

Update only the core's existing approved Design/Plan path/SHA constants and set `PLANNING_BASE_SHA = "647fae2cf3ba09efc1971bb1a87a30e18b86dd5b"`. The current Delta path/SHA, the exact parsed user-approved Plan path/SHA, and the canonical five-file bundle must all bind the same disk bytes. Add/retain a positive test that invokes public `verify_execution_authority()` against that canonical on-disk bundle, plus existing negative cases for a missing file, old Plan SHA, old Design SHA, stale base SHA, unexpected entry, and sidecar mismatch. Do not add a field to the authority packet or modify receipt schema. Any mismatch remains fail-closed under existing authority validation.

**Step 5: Run the RED-to-GREEN tests.**

Run the focused node IDs from Task 1. Expected: all pass; the required `None -> 0` mutation produces the exact nullability STOP; all six launch-time values produce the unresolved representation; valid canonical GRVT component behavior remains unchanged.

## 7. Task 3: Production-Path Regression and Scope Gates

**Invariants:** `INV-15J-A-N-00` through `N-03`.

**Files:**
- Modify: none beyond Tasks 1-2.
- Test: both existing J-A core and CLI test modules.

**Step 1: Run the J-A suite.**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
```

Expected: all collected tests pass, including all new semantic-gate tests. A changed count is acceptable only when the new named tests are present and every existing test passes; a count alone is not evidence.

**Step 2: Run canonical component proof without editing its fixture.**

Run the existing canonical GRVT fixture proof. Expected: the unchanged frozen parser projection and `validate_archive_package` result still pass. This proves compatibility with canonical component inputs only; it must not be reported as a replacement-receipt positive load.

**Step 3: Run bounded static and safety gates.**

```bash
set -euo pipefail
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py

git diff --check 647fae2cf3ba09efc1971bb1a87a30e18b86dd5b
git diff --cached --check 647fae2cf3ba09efc1971bb1a87a30e18b86dd5b
git diff --cached --quiet
python3 -c 'from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False'
set +e
python3 .agent/tools/anti_shortcut_scan.py --base-sha 647fae2cf3ba09efc1971bb1a87a30e18b86dd5b
scanner_rc=$?
set -e
printf 'anti_shortcut_rc=%s\n' "$scanner_rc"
test "$scanner_rc" -eq 0
```

Expected: Ruff and both whitespace checks exit `0`; index is empty; live-trading flag assertion exits `0`; scanner prints its actual `anti_shortcut_rc=0`. Do not accept a copied scanner summary. Any nonzero exit stops the task.

**Step 4: Prove exact scope.**

Compare `git diff --name-only`, untracked files, and the SHA-256/byte-count of every Task 0 pre-existing/frozen path with `pre_execution_frozen_bytes.json`. Expected task-induced source changes are only the two allowed implementation/test paths; the approved Plan is read-only and cannot be task-induced. Recompute the output-parent ledger and require byte-for-byte equality with Task 0. Pre-existing dirty/untracked paths remain unchanged and separately attributed. Any byte drift outside the two allowed source/test paths is `BLOCKED_SCOPE_DRIFT`; any new/missing/changed output root is `STOP=stage1_5j_a_output_parent_mutated` and must not be deleted to conceal the failure.

## 8. Task 4: Preserve Lifecycle, Legacy Immutability, and Permission Isolation

**Invariants:** `INV-15J-A-N-04`, `N-05`.

**Files:**
- Modify: none beyond Tasks 1-2.
- Read only: existing lifecycle tests and immutable legacy root.

**Step 1: Re-run existing lifecycle/crash-recovery coverage.**

Run the existing focused tests for parent `flock` exclusion, staging/final collision classification, and crash/no-resume behavior. Expected: they pass unchanged. This Plan deliberately adds no lifecycle branch; the new validation is before record acceptance/publication and cannot alter atomic staging, double `fsync`, atomic rename, or the four-state recovery model.

**Step 2: Re-check immutable root and output-parent bytes.**

Re-run the four `shasum` commands for the legacy root and recompute the complete sorted output-parent ledger from Task 0. Expected: exact byte-for-byte equality with Task 0. A legacy witness difference is `STOP=stage1_5j_a_legacy_root_mutated`; a root-set or manifest difference is `STOP=stage1_5j_a_output_parent_mutated`. Either requires immediate audit; do not delete or repair anything.

**Step 3: Verify public loader rejection without mutation.**

Invoke the public loader against `20261008T160500Z` exactly as it exists on disk. Expected: fail-closed at authority identity validation, matching:

```text
STOP=stage1_5j_a_authority_packet_invalid:rel_path_mismatch:approved_design
```

If disk ordering exposes `disk_sha_mismatch:audited_core` first, record it as the equivalent authority-identity rejection; no semantic state validator result may be claimed from this legacy root. A successful load, fallback, rebind, or changed root is a blocker.

**Step 4: Prove no runtime authority.**

The existing unauthorized-run test must still prove `run_inventory` fails before transport for an unauthorized `run_id`. Verify there is no new `network_authorization.txt`, no output parent/run root created by this execution, and all existing J-A authority flags remain false. No network CLI run is allowed by this Plan.

## 9. Task 5: Independent Code Review Gate

**Invariants:** all.

**Files:**
- Create only after implementation authorization: `.git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>/evidence/task5_code_review_request.md`
- Review scope: only the two allowlisted implementation/test paths, exact Design chain, Task 0 ledger, test/scan outputs.

**Step 1: Prepare exact review input.**

Provide the independent reviewer the final core/test diff, exact user approval sentence, recomputed final Plan/Design-chain hashes, canonical five-file authority bundle bytes/sidecars, Task 0 `pre_execution_frozen_bytes.json` and output-parent ledger, focused RED/GREEN proof outputs, canonical fixture/parser provenance, full J-A test output, Ruff output, scanner command plus actual return code, scope/index proof, legacy-root and complete output-parent before/after identities, and public-loader rejection evidence.

**Step 2: Require the following review questions.**

- Does `run_inventory` reject all six invalid launch-time types before archive identity/request/record creation?
- Does strict loader independently replay that admission and reject forged `validated_target_detail`?
- Is the nonpersisted validator shared by production producer and loader, and does it only constrain the four frozen fields?
- Does the required `None -> 0` mutation reach the semantic validator, rather than fail earlier on a hash/manifest/review issue?
- Does the canonical on-disk implementation-authority bundle bind the user-approved exact Plan, current Delta, and `base_sha=647fae...dd5b`, and does public `verify_execution_authority()` positive-load it while all existing malformed-bundle probes fail closed?
- Do the pre-existing/frozen-byte ledger and sorted output-parent ledger remain exactly unchanged outside the two allowed source/test files?
- Are all six launch-time mutations based on canonical GRVT detail bytes passed through the frozen parser before exactly one field is changed?
- Are the CLI, parser, config, fixture, data, journal, date-set, reducer, authority flags, lifecycle, and J-B/Governance paths truly unchanged?
- Did the executor avoid synthetic full-receipt positive evidence, network activity, receipt creation, and legacy-root mutation? The only permitted authority creation is the Task 0 create-once canonical implementation bundle.

**Step 3: Route review failures.**

A P0/P1, missing semantic proof, scope violation, or authority mismatch is `INCOMPLETE` or `BLOCKED` and returns to the smallest applicable Task. Do not progress to Completion Audit with an open finding. If correction needs Design changes or a new file outside section 2, stop as `BLOCKED_SCOPE_DRIFT` or `BLOCKED_SPEC_DRIFT` rather than expanding this Plan.

## 10. Task 6: Fresh Independent Completion Audit and Deferred Routing

**Invariants:** all.

**Files:**
- Create only after Task 5 is accepted: `.git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>/evidence/completion_audit_report.md` and its checksum sidecar if the existing workflow requires it.
- Modify: none.

**Step 1: Invoke the independent completion audit.**

The auditor must independently parse the user approval, recompute approved Plan/Design bytes, validate the canonical five-file authority bundle and its public positive load, inspect actual diff/index/untracked ownership, production/loader call paths, test source, canonical fixture provenance, immutable root hashes, complete output-parent ledger, and run the scanner itself with the actual exit code. Executor-generated summaries are inputs, not audit conclusions.

**Step 2: Required audit probes.**

- Invoke the shared private record validator with valid all-`None` data and each one-field mutation, including `post_launch_row_count: None -> 0`.
- Verify actual producer and loader call the same production validator.
- Probe all six invalid launch-time values through production admission and loader replay; test unresolved acceptance and forged-validated rejection.
- Confirm no archive request/record is produced for invalid launch times.
- Confirm every pre-existing/frozen path's byte count/SHA and every output-parent root/manifest entry matches Task 0; confirm legacy root bytes are unchanged and public loader rejects it under new authority.
- Confirm the public authority verifier accepts only the canonical Task 0 bundle and fails closed for a missing file, stale Design/Plan/base SHA, unexpected entry, malformed sidecar, or on-disk authority drift.
- Independently rerun targeted tests, Ruff, diff/index checks, live-trading flag check, and `anti_shortcut_scan.py --base-sha 647fae2cf3ba09efc1971bb1a87a30e18b86dd5b`; record real return codes.

**Step 3: Completion verdict and Rule-12 routing.**

`COMPLETE_PRE_NETWORK_IMPLEMENTATION` is possible only when every invariant and gate passes. It means code readiness only. It does not authorize a commit, push, deployment, SSH, network, receipt generation, Governance verifier implementation, J-B binding, replay, paper/live trading, execution, or Alpha claim.

If any prior step/gate fails, stop immediately and route exactly:

- Local code/test defect within the two allowlisted paths: `BLOCKED_IMPLEMENTATION_DEFECT`; repair only after a fresh review/audit path.
- Required new file, contract, authority schema, lifecycle, parser, CLI, fixture, data, journal, date-set, reducer, or scope change: `BLOCKED_SCOPE_DRIFT`.
- Contradiction between this Plan/Delta and frozen parent/prior authority: `BLOCKED_SPEC_DRIFT` with an evidence packet.

Only an independent `COMPLETE_PRE_NETWORK_IMPLEMENTATION` result routes to the separately approved Governance verifier Implementation Plan. A later J-A network run requires a new user-approved one-time network authorization, a new `RUN_ID`, newly audited Core/CLI/Config hashes, and a future Receipt Closure Audit. Only after strict-loader and Governance-verifier closure may a separate J-B Design Delta consider an upstream rebind.

## 11. Execution Prohibitions and Assumptions

- The sole material implementation assumption is that the frozen parser's existing projection can be represented in test as the same internal shape consumed by the existing production replay code. If that cannot be proven without a test-only parallel reducer or fixture modification, stop rather than fabricate a positive receipt.
- No financial, Alpha, strategy, price-response, replay, execution, paper-trading, or live-trading semantics are introduced. L2 research criteria are `N/A` because this is deterministic schema conformance only.
- `RISK_LIVE_TRADING_ENABLED` and every existing J-A authority flag remain `False`.
- No automatic Git commit is permitted. User decides whether and how to stage or commit only after the required independent review and completion audit.
