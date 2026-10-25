# Stage 1.5J-C 收据闭环生命周期修复实施计划

> **For Codex:** 实施时必须逐 Task 执行；先写 RED 测试，再写最小实现，再运行该 Task 的验证。不得跳过任何 STOP 条件。

**状态：** `plan_candidate`。本文件不是实施、录入 payload、生成 closure report 或重新运行 J-C validation 的授权。

**Goal：** 在不改变既有 J-C validation、receipt profile、研究语义或权限的前提下，新增一个只会记录已批准 `AuditDecisionPayload` 的单用途 Evidence Recorder，并为其授权绑定、拒绝行为、崩溃恢复和最终只读复核建立可审计实施路径。

**Architecture：** 新的 `scripts/governance/record_stage1_5j_c_receipt_closure_audit.py` 是独立 stdlib 脚本，只接受一个仓库外 payload regular-file 路径。它从 payload 中得出既有 J-C RUN_ID，并只读验证 validation chain、recording chain、validation triplet 与 producer lifecycle evidence；只有全部匹配时，才以 directory-FD `flock`、同目录 staging、`os.link` 和 directory `fsync` 写入既定 closure report 与 sidecar。它不 import、调用或替代 J-C core、CLI、domain loader、Rule 17 verifier 或 Auditor。

**Tech Stack：** Python 3 stdlib (`argparse`, `fcntl`, `hashlib`, `json`, `os`, `pathlib`, `stat`); `pytest`; `ruff`; project anti-shortcut scanner。

---

## 1. Authority、冻结语义与前置条件

| Authority | Path | SHA-256 | 本 Plan 的约束 |
| --- | --- | --- | --- |
| Parent Design | `docs/designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md` | `32d5130806489c0848748060835a7c0fb8f1715a3f9fb6b479c2f02cff5d4e45` | 保持 J-C protocol、validation-only、profile、raw-to-output 证据要求不变。 |
| Parent R1 Plan | `docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md` | `827d1bbcabdd02f1d9d566752f1185e2e7aef49bb2a236660c8fc6a621d0ebe3` | 不重跑/重写既有 validation root；其 Task 5/6 closure writer 矛盾仅由获批 Delta 替换 owner。 |
| Approved Delta | `docs/designs/2026-10-25-external-signal-shadow-lab-stage1-5j-c-receipt-closure-lifecycle-design-delta_CN.md` | `da901f94fd441f3070c744cacf6337dd1d181e8ecae5f2076c62e1e8c76b584d` | `INV-13` 至 `INV-17`、两条 authority chain 与 S0-S4 是不可自行改写的 contract。 |

本 Plan 只实现 Delta 的治理生命周期，不改变任何研究参数、样本、60s/3s/15m protocol、成本假设、趋势结论或 claim level。L2 的研究项为 `N/A`；所有结果仍为 `hypothesis_only` / `validation_only`，不产生 Alpha、signal、consumer promotion、paper/live/execution 或可交易性结论。

### 1.1 已知验证对象，不是本轮可重写输入

```text
validation_plan_sha256 = 827d1bbcabdd02f1d9d566752f1185e2e7aef49bb2a236660c8fc6a621d0ebe3
validation_run_id = stage1_5j_c_launch_time_path_feasibility_20261024T102858Z
validation_authority_dir = .git/plan-execution/stage1_5j_c/827d1bbcabdd02f1d9d566752f1185e2e7aef49bb2a236660c8fc6a621d0ebe3/stage1_5j_c_launch_time_path_feasibility_20261024T102858Z
validation_root = /private/tmp/stage1_5j_c_launch_time_path_feasibility_20261024T102858Z
validation_source_bundle_sha256 = 86b78078a2e8dde75c14464e917ef2af2f4e7ffc63095ea0df371f6bbc3f3b35
manifest_sha256 = d9b91fd5544e0c7299b06b0e9f7fba152d001c6b8224443d8b0cbe6ec0c8f2ab
summary_sha256 = c48f4a40f82e6c6f9ff5f8f4a59fbd5861458c2bf4c656ce5cce6674f4aa2e3b
review_sha256 = 4e372da9b9390028f066c0e0af77891d79f5a9ad10652ddfb0c2483b6ce4c469
```

上述值仅是 Task 0 的读后重算比对目标。任何 bytes、seal、source bundle、authority tuple 或 triplet 与此不符，均不得重新基线、覆盖、删除或归因；按第 9 节路由。

## 2. Allowed Change Scope

### Allowed implementation paths
- `scripts/governance/record_stage1_5j_c_receipt_closure_audit.py` (new, stage-specific Recorder only)

### Allowed verification paths
- `tests/scripts/governance/test_record_stage1_5j_c_receipt_closure_audit.py` (new)
- `tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py` (only the Delta-required `P-AD-01` production-admission integration proof)

### Allowed documentation paths
- `docs/plans/2026-10-25-external-signal-shadow-lab-stage1-5j-c-receipt-closure-lifecycle-implementation-plan_CN.md`

### Allowed generated/runtime artifacts
- `.git/plan-execution/stage1_5j_c_delta/<APPROVED_DELTA_PLAN_SHA256>/evidence/resumption_inventory.json` and its `.sha256` sidecar, generated only by Task 0 after future Plan implementation approval; never committed.
- `.git/plan-execution/stage1_5j_c_delta/<APPROVED_DELTA_PLAN_SHA256>/evidence/physical_lifecycle_matrix.json` and its `.sha256` sidecar, generated only by the executor in Task 5 after the pre-recording readiness review. It records only disposable-root process probes, their actual RCs and hashes; it is not an Auditor report or an `AuditDecisionPayload`.
- Isolated `tmp_path` and system temporary directories used by tests and auditor-owned negative probes.
- After separate payload-specific user/Custodian authorization only: the four recording authority files in the existing `validation_authority_dir`, and only `evidence/receipt_closure_audit_report.md` plus `evidence/receipt_closure_audit_report.md.sha256` in that same existing directory.

### Affected but unchanged
- `src/research/external_signal_shadow/stage1_5j_c_launch_time_path_feasibility.py`
  - Compatibility evidence: source bundle SHA must remain `86b78078a2e8dde75c14464e917ef2af2f4e7ffc63095ea0df371f6bbc3f3b35`; targeted J-C core tests and no-import AST proof.
- `scripts/external_signal_shadow/run_stage1_5j_c_launch_time_path_feasibility.py`
  - Compatibility evidence: existing CLI authority and lifecycle tests retain their current actual process behavior; Recorder must not import it.
- `scripts/governance/verify_stage1_5j_c_receipt_schema.py`
  - Compatibility evidence: standalone verifier remains profile `stage1_5j_c_time_path_v1`; Recorder does not import/call it and report remains outside sealed receipt tree.
- Existing validation authority directory and `/private/tmp/stage1_5j_c_launch_time_path_feasibility_20261024T102858Z`
  - Compatibility evidence: Task 0 and Task 5 rehash all pre-existing files; no receipt/root/validation authority bytes may change.
- J-A/J-B producers, strict loaders, verifiers, receipts, configs and Rule 17 common verifier
  - Compatibility evidence: current source/input seals and their existing suites; no implementation whitelist authority.

### Forbidden
- Any change outside the paths above.
- Any change to `configs/base.py`, J-A/J-B/J-C core, J-C CLI, J-C standalone verifier, J-C protocol, source bundle, receipt/profile/schema, raw ZIP/CSV inputs, validation triplet, existing validation authority bytes, research semantics, or risk thresholds.
- Network/API calls, credential/account reads, signal/order/position generation, paper/live trading, consumer promotion, commit, push, deployment or SSH.
- `os.replace` in Recorder publication, broad framework/factory/registry additions, direct report overwrite, unscoped cleanup, `git clean`, `git reset`, `git checkout`, or formatter/autofix commands such as `ruff check --fix .`.
- Treating a Recorder unit test as validation, domain replay, Rule 17, Oracle, or receipt-closure evidence.

## 3. Invariant-to-Task Matrix

| Delta invariant | Runtime/mechanical owner | Task | Required proof | Fail-closed condition |
| --- | --- | --- | --- | --- |
| `INV-13` | Recorder serializes only payload `report_utf8`; Auditor remains read-only | 1-2, 5 | exact payload/report byte identity, pre-payload readiness review, and AST absence of Auditor write path | `STOP=stage1_5j_c_audit_recording_payload_mismatch` |
| `INV-14` | Recorder single positional payload input; fixed path identities; no J-C imports | 1-2, 4-5 | `--help`, import/read guard, static AST proof, write-set tests and physical process matrix | `STOP=stage1_5j_c_audit_recording_authority_mismatch` |
| `INV-15` | Recorder checks both authority chains, physical root, triplet, lifecycle evidence, source seal | 0-2, 4-5 | approved-Plan identity gate, canonical fixture, one-field mutations and exact FileSeal comparisons | `STOP=..._payload_mismatch`, `..._authority_mismatch`, or `..._triplet_mismatch` |
| `INV-16` | directory-FD lock; S0-S4; staging + link + fsync state transitions | 1-2, 5 | unit tests plus a fresh actual-process S0-S4, contention, collision and injected `fsync` fault matrix | `STOP=..._target_exists_mismatch`, `..._lock_unavailable`, or `..._persistence_failure` |
| `INV-17` | Existing parser/admission tests and later physical lifecycle matrix remain separate | 3-5 | canonical J-A admission proof, complete fresh matrix ledger and explicit deferred authority gate | `BLOCKED_SCOPE_DRIFT` or `receipt_closure_incomplete`; never substitute unit GREEN |

## 4. Task 0: Immutable Baseline and Resumption Inventory

**Invariants:** all, especially `INV-15` and `INV-17`.

**Files:**
- Create only after Plan approval: `.git/plan-execution/stage1_5j_c_delta/<APPROVED_DELTA_PLAN_SHA256>/evidence/resumption_inventory.json` and sidecar.
- Read only: every pre-existing J-C source/test/doc path, existing validation authority directory, validation root, parent Design/R1 Plan/Delta, and Git index/worktree state.

1. **Approval-identity gate, before any `.git` evidence write:** obtain the exact user Plan-implementation approval sentence as input, extract `APPROVED_DELTA_PLAN_RELATIVE_PATH` and `APPROVED_DELTA_PLAN_SHA256`, and require the path to equal this Plan's path. Recompute the current Plan bytes and require exact SHA equality. Do not derive either value from this file, `HEAD`, or an executor variable. A mismatch is `STOP=approved_authority_mismatch` before creating the inventory or any other new artifact.
2. After step 1 succeeds, capture `BASE_SHA=$(git rev-parse HEAD)`, `git status --short --untracked-files=all`, `git diff --check`, `git diff --cached --check`, staged state, and SHA-256/size for every pre-existing untracked J-C path. Record that their provenance is inherited and `scope_provenance_uncertain=true`; do not claim prior GREEN or ownership.
3. Recompute the three authority document seals, 11-file validation source bundle, nine validation input seals, all validation authority file/sidecar seals, lifecycle evidence/sidecar seal, and physical validation root triplet. Record the exact expected values in §1.1, the exact approval sentence (and its SHA-256), actual Plan SHA, `BASE_SHA`, index/worktree snapshot, and presence/absence of recording files and closure report. Use a canonical JSON object plus one LF and a two-space SHA sidecar for the inventory itself.
4. **First-start state only:** verify every ancestor from repository root through the authority evidence directory and every ancestor of `validation_root` with `lstat`; record any symlink. Confirm `evidence/` contains exactly the lifecycle two-file pair, no Recorder staging file, no report or report sidecar, and record `recorder_attempt_kind=first_start`, `required_initial_state=S0`. This gate is never rerun merely to resume a prior Recorder call.
5. STOP without changing any existing file if the approved Plan identity or baseline seal differs, validation root/evidence shape is unexpected, `HEAD != BASE_SHA`, a pre-existing changed path overlaps this Plan but cannot be preserved, or any evidence source is inaccessible. Classify under §10 instead of rebaselining.

**Verification commands:**

```bash
test "$APPROVED_DELTA_PLAN_RELATIVE_PATH" = \
  "docs/plans/2026-10-25-external-signal-shadow-lab-stage1-5j-c-receipt-closure-lifecycle-implementation-plan_CN.md"
actual_plan_sha=$(shasum -a 256 "$APPROVED_DELTA_PLAN_RELATIVE_PATH" | awk '{print $1}')
test "$actual_plan_sha" = "$APPROVED_DELTA_PLAN_SHA256"
BASE_SHA=$(git rev-parse HEAD)
git status --short --untracked-files=all
git diff --check && git diff --cached --check && git diff --cached --quiet
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from research.external_signal_shadow import stage1_5j_c_launch_time_path_feasibility as jc
seals, bundle = jc.compute_source_bundle_seals_and_sha256()
assert bundle == "86b78078a2e8dde75c14464e917ef2af2f4e7ffc63095ea0df371f6bbc3f3b35"
assert len(seals) == 11
PY
```

**Expected:** all pre-existing bytes and exact approved Plan identity match; inventory exists only in the Delta-owned runtime path; no closure report, recording authorization, raw read, CLI/replay/verifier invocation, or production write occurs. A later retry retains this inventory and proceeds only through Task 5's S1/S2/S4 recovery rule with the same approved Plan, validation tuple, payload SHA, Recorder source seal and second authority chain; S3 always stops.

## 5. Task 1: Recorder Contract Tests (RED)

**Invariants:** `INV-13` through `INV-16`.

**Files:**
- Create: `tests/scripts/governance/test_record_stage1_5j_c_receipt_closure_audit.py`
- Do not modify production code in this task.

1. Add a test-local *literal* serializer for the new Recorder-owned payload and recording-chain grammar. It must use fixed literals from the approved Delta for exact key sets, ordered 15-line approval grammar, enum values, sidecar grammar and S0-S4 filenames. It must not import private Recorder helpers or reuse its serializer/validator as its oracle.
2. For the validation chain portion, derive seals by parsing/copying the existing validation artifacts through their canonical upstream boundary: call the public J-C authority parser/strict validator where its API permits, and independently rehash copied regular files. The unit fixture must be labelled `tier=recorder_contract_unit_only`; it proves no raw/provenance/domain/verifier claim. If no existing public, strict, no-write upstream path can construct/validate that portion without a J-A/J-B/J-C change, STOP=`BLOCKED_SCOPE_DRIFT`; do not use a hand-built upstream authority dictionary.
3. Write failing tests for: one positional payload only; payload regular-file/no-symlink, UTF-8, canonical JSON, no duplicate key and exact key set; exact primitive types; SHA/path/run-id grammar; `validation_only`; verdict enum; report first-line projection and single `closure_verdict=` line; all FileSeal comparisons; fixed Recorder identity; all eight recording permission literals false; source plan/Delta mismatch; triplet/lifecycle mismatch; symlink/ancestor escape; additional CLI option rejection; and no raw/CLI/verifier/oracle imports or reads.
4. Write failing lifecycle tests for S0 first write, S1 sidecar completion, S2 idempotency preserving final inode/mtime, S3 rejection without deletion, each permitted S4 stale-staging cleanup then reclassification, malformed staging rejection, lock contention, final-inode collision, and injected file/directory `fsync` failure. Assert exact STOP families and no write outside `tmp_path` test authority/evidence roots.

**Verification command:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/governance/test_record_stage1_5j_c_receipt_closure_audit.py
```

**Expected before implementation:** RED due solely to missing recorder module/entrypoint. A failing test that instead needs an upstream contract/schema change is `BLOCKED_SCOPE_DRIFT`.

## 6. Task 2: Implement the Minimal Stage-Specific Recorder (GREEN)

**Invariants:** `INV-13` through `INV-16`.

**Files:**
- Create: `scripts/governance/record_stage1_5j_c_receipt_closure_audit.py`
- Test: `tests/scripts/governance/test_record_stage1_5j_c_receipt_closure_audit.py`

1. Implement a stdlib-only executable with exactly one positional `payload_path`; no project-root, run-id, receipt-root, profile, permission, plan or verdict override flag. `--help` must perform no artifact/raw/authority write.
2. Freeze the parent J-C Design path/SHA, R1 validation Plan path/SHA, Delta Design path/SHA, report relative path, profile/version, operation literal, payload exact keys, recording-release exact keys, permission key set and allowed final/staging filenames as module constants. The Recorder Delta Plan path is fixed as this Plan path; its physical SHA must be recomputed at invocation and matched to payload/release, not accepted from a CLI parameter.
3. Resolve the authority directory only from validated fixed validation-plan identity plus payload `run_id`; `lstat` each ancestor and every controlled regular file. Parse canonical JSON with duplicate-key rejection, reject non-canonical bytes, and compute FileSeals independently with `hashlib`; never use `dict.get` fallback for authority values.
4. Verify, field-for-field, payload against the immutable validation chain, 15-line recording approval and sidecar, recording release and sidecar, existing validation root triplet, and lifecycle two-file pair. Recompute this script's own source SHA with no-symlink identity check. The only success precondition is exact agreement and eight `false` permission values.
5. Open the pre-existing evidence directory by file descriptor, acquire `fcntl.flock(LOCK_EX | LOCK_NB)`, classify S0-S4 before creating a staging file, and use only a same-directory regular staging file, file `fsync`, `os.link(staging, final)`, directory `fsync`, `unlink(staging)`, directory `fsync`. Do not use `os.replace`, overwrite an existing final, change producer lifecycle evidence, or create a persistent lock file.
6. Return `0` only after S2 semantics are verified. Every exception must return nonzero and print one of the Delta STOP families without generating a different report, changing a verdict, invoking J-C, reading raw packages, or mutating validation root/authority inputs.

**Verification commands:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/governance/test_record_stage1_5j_c_receipt_closure_audit.py
python scripts/governance/record_stage1_5j_c_receipt_closure_audit.py --help
```

**Expected:** targeted tests `RC=0`; help `RC=0` and no file write. Any need for a generic framework, a Recorder import of J-C components, or a contract mutation is STOP=`BLOCKED_SCOPE_DRIFT`.

## 7. Task 3: Preserve Real J-C Package Admission Proof (`P-AD-01`)

**Invariants:** `INV-17`.

**Files:**
- Modify only if required: `tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py`
- Affected but unchanged: all J-A/J-B/J-C production sources.

1. Locate an existing J-A canonical strict-loader-compatible fixture/factory that can create an isolated physical root and yield actual `archive_package_records`. Use the canonical loader first; only after admission, mutate exactly one admitted ZIP/CHECKSUM/package-identity byte in its disposable root.
2. Call the actual J-C package-admission/reducer entry path with that loader-derived record. Assert the Design-assigned J-C admission owner returns nonzero/fail-closed before a result can be reduced. The positive control must process an unmodified canonical package through the same entry path.
3. Do not use a J-C helper mock, manually assembled package record, loose fake loader, or a copy of upstream attestations as a substitute. Do not alter the real J-A receipt, raw archive, checksum or J-C validation root.

**Verification command:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py \
  -k 'package_admission or production_admission'
```

**Expected:** canonical positive control and exactly-one-mutation negative path pass. If no reusable canonical fixture/factory exists in the whitelist, STOP=`BLOCKED_SCOPE_DRIFT`; do not add J-A source/test fixture machinery under this Plan.

## 8. Task 4: Local Regression, Scanner and Scope Gate

**Invariants:** all; local proof only, not Task 5 positive validation.

**Files:** no product changes beyond §2 whitelist.

1. Run the recorder suite, existing J-C core/CLI/verifier suites, and the focused P-AD-01 proof. Confirm protocol hash is unchanged before and after all test runs.
2. Run scoped Ruff over only the new recorder and the two allowed J-C test files. Run anti-shortcut scanner with immutable Task-0 `BASE_SHA`; record scanner source SHA, actual exit code and a per-warning disposition. A nonzero scanner is never called clean.
3. Record no-network/no-execution proof through AST/import checks: Recorder must not import `research.external_signal_shadow`, `scripts.external_signal_shadow`, `verify_stage1_5j_c_receipt_schema`, `zipfile`, `csv`, networking libraries or execution layers. Directly assert `RISK_LIVE_TRADING_ENABLED is False`.
4. Recheck `HEAD == BASE_SHA`, the current Plan byte SHA against Task 0's independently supplied `APPROVED_DELTA_PLAN_SHA256`, and index/worktree/untracked ownership against Task 0. Only the whitelist, the Delta-owned runtime inventory and permitted `tmp_path` data may be attributed to this Plan. Do not reformat, clean or alter pre-existing untracked J-C paths or create a replacement baseline.

**Verification commands:**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_c_launch_time_path_feasibility.py \
  tests/scripts/governance/test_verify_stage1_5j_c_receipt_schema.py \
  tests/scripts/governance/test_record_stage1_5j_c_receipt_closure_audit.py
.venv/bin/ruff check \
  scripts/governance/record_stage1_5j_c_receipt_closure_audit.py \
  tests/scripts/governance/test_record_stage1_5j_c_receipt_closure_audit.py \
  tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"; scanner_rc=$?
printf 'scanner_rc=%s\n' "$scanner_rc"
test "$scanner_rc" -eq 0
git diff --check && git diff --cached --check && git diff --cached --quiet
test "$(git rev-parse HEAD)" = "$BASE_SHA"
test "$(shasum -a 256 "$APPROVED_DELTA_PLAN_RELATIVE_PATH" | awk '{print $1}')" = "$APPROVED_DELTA_PLAN_SHA256"
PYTHONPATH=src:. .venv/bin/python -c 'from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False'
```

**Expected:** each process `RC=0`; scanner warnings have an explicit ledger disposition; no validation/recording authority or receipt/report write is performed by tests.

## 9. Task 5: Pre-Recording Review and Separately Authorized Physical Evidence

**Invariants:** `INV-13` through `INV-17`.

This task has two authority boundaries. Plan implementation approval permits neither an `AuditDecisionPayload` nor a persistent closure report. It has exactly the following frozen order; no later step may be advanced when an earlier proof is absent.

1. **Pre-recording independent readiness review, no final payload:** invoke `.agent/skills/audit-plan-completion/SKILL.md` in read-only mode over Tasks 0-4. It must verify the exact approved Plan identity, `HEAD == BASE_SHA`, current root/authority tuple, Task-4 local proofs and that no raw validation or closure claim has been substituted. Its only allowed result is implementation readiness or a fail-closed finding; it must not emit `AuditDecisionPayload`, `receipt_closure_audited`, recording authorization, or a closure report.
2. **Complete physical evidence before an audit decision:** verify `P-AD-01`, the existing canonical validation chain, and fresh actual-process evidence for every `P-LC-01` through `P-LC-06`. The executor writes the bounded `physical_lifecycle_matrix.json` ledger and sidecar, but an Auditor remains read-only. Each row must record `case_id`, single mutation/fault, actual command, actual process RC, expected RC/STOP, before/after physical directory listing, relevant SHA-256 plus inode/mtime where finals exist, and a proof that no file outside its disposable root changed. The ledger also records the Recorder source SHA, approved Delta Plan SHA, `BASE_SHA`, and payload fixture SHA. Unit-test output may be cited as supplementary evidence only.

   **Runtime-authorization classification:** `P-LC-01`, `P-LC-02` and `P-LC-03` are limited to disposable pre-loader or standalone structural-verifier probes and may run only when their recorded process proof shows no upstream loader/raw-package read or publication. `P-LC-04` and `P-LC-05` may consume controlled raw copies or invoke a J-C producer only after the executor independently verifies that a parent-Design user/Custodian raw/validation authorization explicitly covers the exact source bundle, operation, disposable root and process being invoked. Plan implementation approval, this Delta Plan, a readiness review, or a disposable directory do not substitute for that authorization. If the covering authority is absent or mismatched, record `STOP=stage1_5j_c_independent_approval_release_unavailable`, do not run `P-LC-04`/`P-LC-05`, leave their matrix rows incomplete, and do not emit a positive `AuditDecisionPayload`. `P-LC-06` is Recorder-only and must never read raw ZIP/CSV or invoke J-C CLI/core/loader/verifier/oracle.

   | Physical case | Required disposable-root actual process proof |
   | --- | --- |
   | `P-LC-01` missing Custodian release | In a disposable validation-authority copy, execute the real J-C CLI preflight with an otherwise self-consistent approval/sidecar/derived authorization that lacks the Custodian release. Require pre-loader nonzero RC and its frozen authority STOP; prove no raw/package read and no output publication. |
   | `P-LC-02` mismatched `output_root` | In a disposable copy, bind external release/derived authorization to a root different from the receipt root. Require the real J-C CLI preflight nonzero RC and frozen authority STOP; if the mutation is post-publication, require the independent tuple comparison to fail too. |
   | `P-LC-03` sealed-tree mutation | In a disposable receipt-root copy, mutate exactly one root/path/symlink or extra/missing artifact condition. Run the standalone Rule 17 verifier as its real process, require nonzero RC and its frozen structural STOP, and prove the copied final artifacts are not overwritten. |
   | `P-LC-04` semantic raw/receipt forgery | In an isolated disposable raw/receipt copy, make raw and receipt locally self-consistent while forging child/Parent/group/prose semantics. Run the J-C domain replay/independent oracle owner process, require nonzero RC and its frozen semantic STOP, and prove no canonical raw/receipt/root was read for mutation or written. |
   | `P-LC-05` producer directory `fsync` fault | Inject a parent-directory `fsync` fault only into an isolated producer subprocess environment. Require producer nonzero RC and missing lifecycle evidence, then require the closure predicate to remain false; record the directory state and prove no canonical output/authority byte changed. |
   | `P-LC-06a` second-chain mismatch | One mutation per subprocess for payload SHA, Delta Plan seal and Recorder source seal mismatch; each must return nonzero with the frozen authority/payload STOP and leave report targets absent. |
   | `P-LC-06b` S0 | A real Recorder subprocess performs the normal disposable publication and reaches S2; record the exact report/sidecar bytes and post-state. |
   | `P-LC-06c` S1 and S2 | Use an actual interrupted/faulted Recorder subprocess to leave legal S1, then run the unmodified Recorder process to complete sidecar publication. Re-run from S2 and prove RC=0 with final inode and mtime unchanged. |
   | `P-LC-06d` S3 and S4 | Construct only the Delta-permitted malformed/sidecar-only/unknown S3 cases and prove nonzero/no deletion. For each permitted stale-staging S4 variant, create it through the controlled disposable process, then prove cleanup and reclassification by a fresh unmodified Recorder subprocess. |
   | `P-LC-06e` directory `fsync` fault | Inject the fault only through an isolated disposable subprocess environment (for example a test-only `sitecustomize` on `PYTHONPATH`); run the real Recorder entrypoint, require the frozen persistence STOP/nonzero RC, and prove no successful final publication. No production flag, source hook or canonical directory mutation is allowed. |
   | `P-LC-06f` lock contention and final collision | Hold the disposable evidence-directory lock in a separate process and require the lock STOP/nonzero RC. Separately pre-create a wrong final inode, require the collision STOP/nonzero RC, and prove its bytes, inode and mtime are unchanged. |

   All `P-LC-06` commands invoke the real Recorder executable as a separate process against a disposable project/authority/evidence tree containing byte-identical approved inputs. They must not read J-C raw ZIP/CSV data, invoke the J-C CLI/core/strict loader/verifier/oracle, mutate the canonical validation root or existing authority directory, or create a durable production receipt/report. If any matrix row, external-write proof, sidecar, or required actual RC is absent, stop at `receipt_closure_incomplete`; do not issue a payload.
3. **Independent final-decision payload:** only after steps 1-2 are complete, a fresh independent read-only Auditor rehashes the validation tuple; runs `scripts/governance/verify_artifact_schema.py` for the J-A root, J-B standalone verifier for the J-B root, and J-C standalone verifier for the existing absolute validation root; records profile, verifier source SHA and J-A/J-B/J-C artifact hashes; and may emit the canonical `AuditDecisionPayload`. The payload is a user-transferred, repository-external regular file, not a Recorder command generated by the executor. No positive verdict is allowed if the complete physical matrix is unavailable.
4. **Second user/Custodian chain:** only after the exact payload SHA exists, the user may provide exact 15-line `user_audit_recording_approval.txt`; Custodian may write its sidecar and `audit_recording_release.json` plus sidecar. All four new files must bind this approved Delta, this approved Delta Plan, this Recorder's source seal, payload SHA, existing run/root and report path. They may not modify validation approval/release/run authorization.
5. **Authorized persistent Recorder call and retry rule:** the first authorized call must begin from the Task-0 recorded S0 state and may write only the two report files through S0/S1 to S2. A retry uses the same run ID, approved Plan, validation tuple, payload SHA, Recorder source seal and second authority chain. It must enter only the frozen legal S1/S2/S4 recovery paths; S3 remains a STOP. It must not create a replacement RUN_ID, rerun CLI, regenerate the J-C receipt, manually write a report, write a new resumption inventory, or establish a new baseline.
6. **Final read-only closure audit:** a new or same independent read-only Auditor validates S2 membership, report/sidecar/payload identity, both chains, triplet, Recorder source seal, complete physical-matrix ledger and all parent Design §9 predicates. It also proves Recorder did not run raw/domain/verifier code.

**Separate authorization STOPs:** missing/changed payload, recording approval/release, source seal, validation tuple, complete physical matrix, approved-Plan identity, `HEAD == BASE_SHA`, or independent audit means stop at `receipt_closure_incomplete`. Never create a replacement RUN_ID, rerun CLI, regenerate the J-C receipt, manually write the report, or treat Plan approval as Recorder release authority.

## 10. Rule-12 Routing and Done Definition

| Condition | Mandatory route |
| --- | --- |
| A repair fits §2, preserves all fixed contracts and needs only Recorder/test correction | `BLOCKED_IMPLEMENTATION_DEFECT`; return to RED/GREEN within this Plan. |
| P-AD-01 needs J-A/J-B source, fixture factory, profile, validation source bundle, config or core/CLI/verifier change | `BLOCKED_SCOPE_DRIFT`; stop and return to Design/Plan revision. |
| Approved Delta contradicts current validation tuple, root layout, upstream strict-loader capability or audit read-only invariant | `BLOCKED_SPEC_DRIFT`; return invariant, source evidence and contradiction packet to Design. |
| Approved Delta Plan path/SHA mismatch, `HEAD != BASE_SHA`, or an attempt to write Task-0 inventory before those checks | `approved_authority_mismatch`; perform no new evidence write and obtain correct approved authority. |
| Validation/recording authority, payload or physical lifecycle evidence absent | `receipt_closure_incomplete`; do not manufacture substitute evidence. |
| `P-LC-04` or `P-LC-05` lacks a parent-Design authority covering its raw/producer process, source bundle, operation and disposable root | `STOP=stage1_5j_c_independent_approval_release_unavailable`; do not invoke that process, leave the matrix incomplete and do not emit a positive payload. |
| A source/bundle/input/validation root byte changed after its original validation | invalidate recorder-only eligibility; a new parent-Design-authorized validation RUN_ID is required. |
| Recorder code or this Delta Plan changes after recording release | invalidate the recording release; require a new payload-bound recording authorization/release. |

**Implementation done (Tasks 0-4 only):** exact approved Plan identity was verified before Task-0 inventory creation; Recorder and tests exist within §2; all local RCs are zero; `HEAD` still equals Task-0 `BASE_SHA`; J-C validation source bundle, root, triplet and existing validation authority are unchanged; no raw validation is claimed; all permissions remain false.

**Receipt closure done (Task 5, separate):** the pre-recording readiness review and complete P-LC-01 through P-LC-06 actual-process matrix preceded the exact canonical payload; every raw/producer `P-LC-04`/`P-LC-05` process was covered by its independently verified parent-Design authorization; user/Custodian has made a matching second authority chain; Recorder has written only report + sidecar through S0-S2 or a legal same-identity S1/S2/S4 retry; final independent read-only audit rechecks both chains, physical bytes, matrix ledger and parent §9 predicates. This does not authorize commit, deployment, network, consumer promotion, paper/live trading, execution or Alpha claims.

## 11. Plan Self-Review Checklist

- Every `INV-13` to `INV-17` maps to an implementation owner, a mechanical test, an actual-process proof where required, and a fail-closed result in §3.
- Scope adds one script and two bounded tests only; it introduces no registry, service, signer, database, generic audit framework, config or J-C production-code refactor.
- Targeted Graphify queries for `producer_lifecycle_evidence`, `run_stage1_5j_c_launch_time_path_feasibility`, and `verify_stage1_5j_c_receipt_schema` returned no nodes in the current graph; `rg` direct source inspection is the authoritative compatibility evidence and found no consumer of the new closure report.
- Task 0 consumes an independently supplied user approval before its first write; it does not self-authorize from current Plan bytes. Task 5 emits a final payload only after the readiness review and complete physical matrix; no unit GREEN is treated as a closure decision.
- This Plan can prove Recorder contract/lifecycle behavior and preserve existing validation evidence. It cannot prove an Alpha, actual market execution, a new J-C raw validation, or receipt closure until the distinct Task 5 authority sequence completes.
- No task contains `commit`, `push`, `deploy`, `SSH`, `git clean`, `git reset`, `git checkout`, runtime collector control or a full-repository auto-fix.
