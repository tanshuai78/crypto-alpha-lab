# External Signal Shadow Lab Stage 1.5G Runtime Attestation Evidence Gate Hotfix Design

**日期:** 2026-09-08  
**状态:** `draft_for_review`  
**Revision mode:** `closure_revision`  
**适用阶段:** Stage 1.5F source-root attestation completion；Stage 1.5G offline live-depth evidence review；Stage 1.5H v2 read-only bundle admission；Stage 1.5D/1.5F VPS deployment operations  
**实现计划许可:** `false`  
**代码实施许可:** `false`  
**部署许可:** `false`  
**任何 trade / paper / live / execution permission:** `false`

---

## 1. 一句话结论

Stage 1.5G 目前只验证 Stage 1.5F root 的 closed-tree 文件集合与盘口数据，未验证该 root 的 runtime attestation 是否属于同一个 Stage 1.5F process/root-contract，也没有把该验证结果持久化给 Stage 1.5H。因此已被 1.5F 标记为 compromised 的 root 仍可能得到 `stage1_5g_depth_evidence_quarantined_pass`，旧的无 runtime-proof 1.5G bundle 也可能被 1.5H 接受。

本 Hotfix 建立一条最小闭环：

```text
manifest-valid Stage 1.5F source tree
-> root-contract / summary semantic binding
-> exact runtime-attestation predicate
-> Stage 1.5G source-authority gate
-> sealed positive gate proof in a v3 1.5G review manifest
-> Stage 1.5H requires that proof before report generation
```

任一边失败均为 `stage1_5g_depth_evidence_invalid` 或 Stage 1.5H input rejection；不得 promotion、不得计入 event family、不得生成新的 1.5H report。盘口采集、quarantine 算法、阈值与所有执行权限不变。

---

## 2. Revision Authority Packet

本修订只以以下冻结 bytes 为 authority；引用名称不能替代 SHA-256。

| Authority | Path | SHA-256 | 本 Hotfix 继承的约束 |
|---|---|---|---|
| Stage 1.5F runtime-attestation Design | `docs/designs/2026-08-10-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-git-ancestry-attestation-design_CN.md` | `28cd9e55540a3eccfd24cca3598acdb7959d02407ff54edf1045765cba5b2f36` | root contract/summary binding、exact attestation、sticky compromise、E0/E1/E2 |
| Stage 1.5F runtime-attestation Plan | `docs/plans/2026-08-10-external-signal-shadow-lab-stage1-5d-1-5f-git-ancestry-attestation-implementation-plan_CN.md` | `65a47168af6f1e9ba11f8003cace93962a5986fafae53577996db360d4defe7e` | 不改变普通 launch collection，producer 默认 disabled |
| Stage 1.5G multi-symbol Design Delta | `docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-design-delta_CN.md` | `3528d4b5f90ee8b7bd142773b1c35a1a51b2ea09242224eaed2ab10df69c5c8b` | per-symbol Layer A、aggregate Layer B、无 family/alpha promotion |
| Stage 1.5G multi-symbol Plan | `docs/plans/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-implementation-plan_CN.md` | `47f9728b8a17e815e836fae837c038a0bc8ae06c6593d9ae0280741997b6da67` | 1.5G v2 existing reducer/metrics contract |
| Stage 1.5H v2 Design Delta | `docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-design-delta_CN.md` | `ec936020cba1ca26a2709f02996ad70bcf05d9457bb1e741ac6d40685269f812` | v2 summary/quarantine semantics、per-symbol read-only reports |
| Stage 1.5H v2 governance approval | `docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md` | `7bf59a14a230da4071bde7acafc0b2022de52c313f47f389eadd293b162dacc4` | read-only only；no cross-symbol aggregation, alpha, signal or execution |

`review finding` 不是 authority。其关于 `consumer_process_started_at_ms` 的要求与上表中的 Stage 1.5F Design/Plan 一致，但当前 workspace 的 `Stage1_5FLiveDepthObserverSummary` 尚未持久化此字段。故本 Design 不把它假装成既有事实：将其作为 Section 6 的最小 producer-contract completion；未完成前不允许 1.5G pass。

### 2.1 已确认事实

1. `data/external_signal_shadow/local_evidence/20260902T105158Z_stage1_5f` 的 `SHA256SUMS` 通过项目 `verify_source_evidence_manifest()`。manifest 自身的全零占位项由此 verifier 显式跳过；通用 `shasum -c` 的 self-entry 失败不能替代项目契约。
2. 该 root 的 summary 记录 `consumer_static_attestation_verified=true`、`consumer_runtime_attestation_verified=false`、`consumer_runtime_attestation_compromised=true`；当前 1.5G 仍可重算为 `stage1_5g_depth_evidence_quarantined_pass`。
3. 该 root 的 summary `consumer_root_contract_sha256` 等于 root contract 的 canonical JSON SHA-256。父级 Plan 规定的 cross-artifact identity 为 `consumer_root_id`、`consumer_startup_commit_sha`、`consumer_runtime_manifest_sha256`，以及两边的 static-attestation value。
4. source root 可以经 `rsync` 被离线复制到不同的本地绝对路径。因此 `consumer_root_id` 只能用于 contract/summary cross-artifact equality，**不得**与 reviewer 当前文件系统路径重新计算的 root ID 比较。
5. `consumer_process_started_at_ms` 在批准的 Stage 1.5F runtime Design 中属于 summary identity/freshness contract，但在当前 writer/model artifact 中缺失。这是已确认的已批准 contract implementation defect，不是可由 1.5G defaulting 绕过的 legacy case。
6. 1.5F 的 runtime proof 与 sticky compromised latch 本身正确：每轮检查 runtime proof；同一 process 一旦失败，`consumer_runtime_attestation_compromised` 不得恢复为 false。
7. 当前 1.5G review manifest 为 v2，只封存 summary、quarantine summary、invalid rows、quality rows；Stage 1.5H 只要求该 v2 closed bundle，因而无法区分经过本 Hotfix gate 的新 bundle 与历史 bundle。
8. 全链路 observation-only。`RISK_LIVE_TRADING_ENABLED = false`；1.5G/1.5H 的 trade、paper、live、execution 和 execution-feasibility permission 均为 false。
9. 当前 workspace 的 1.5F writer 已有额外把 `consumer_process_instance_id` 与 `consumer_runtime_attestation_compromised` 镜像进 root contract 的行为；它与父级 Plan "Root contract must omit ... mutable summary fields" 相冲突。该 pre-existing implementation drift 不构成此 Hotfix 的新 authority，且本 Hotfix 不扩展为 root-contract cleanup；1.5G 不得依赖这些额外 bytes。

---

## 3. Blocker Ledger、Mutable Set 与 No-Touch Set

| ID | Severity | Origin | Proof edge | 失败模式 | 闭合条件 |
|---|---|---|---|---|---|
| P0-1 | P0 | C | parent authority -> Hotfix | 父级仅以名称引用 | Section 2 exact path + SHA verified before Plan |
| P0-2 | P0 | C | 1.5F root -> 1.5G | summary-only boolean 可与另一 contract/root 混配，且 parent-required start field 未落地 | Sections 5-6 的 manifest -> binding -> exact predicate 全部通过 |
| P0-3 | P0 | C | 1.5G pass -> 1.5H admission | old/new pass 无 durable distinction | Sections 7-8 的 gate proof + manifest v3 + 1.5H required verification |
| P1-1 | P1 | C | source failure -> audit diagnosis | malformed `compromised` 被误写成 confirmed compromise | Section 5.4 exact taxonomy |
| P1-2 | P1 | C | historical immutability -> regression evidence | non-goal 与 diagnostic rerun 混淆 | Section 9.2 explicitly separates them |
| P1-3 | P1 | C | writer stop -> checkout | zero-writer gate is not mechanically defined | Section 10.1 exact `/proc` predicate, bounded poll and STOP |
| P1-4 | P1 | C | ordinary deployment -> producer enablement | ordinary path silently supersedes E0/E1/E2 | Section 10.2 preserves configured-true handshake |

**Mutable set:**

```text
Stage 1.5F summary model/writer and runner startup context: only consumer_process_started_at_ms
Stage 1.5G source-root authority validator, invalid reducer, positive gate-proof writer,
  review manifest verifier/writer and its CLI artifact sequence
Stage 1.5H Stage 1.5G input admission/manifest verification only
Stage 1.5G/1.5H focused tests
docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md
```

**No-touch set:**

```text
Stage 1.5F runtime-proof algorithm, protected path set, sticky-latch semantics
Stage 1.5D collector/revision producer policy and E0/E1/E2 state machine
all Stage 1.5G coverage/quarantine thresholds and existing metric formulas
Stage 1.5G summary/quarantine schema_version=2 and review-id formula
Stage 1.5H report/bundle schema and static-proxy metrics
configs/base.py, network endpoints, storage budgets, existing historical bytes
all trade/paper/live/execution permissions and RISK_LIVE_TRADING_ENABLED
```

---

## 4. Scope and Explicit Non-Goals

### 4.1 Scope

1. Complete the already-approved Stage 1.5F summary field `consumer_process_started_at_ms`, set exactly once per observer process, and serialize it atomically with each summary.
2. Make 1.5G validate Stage 1.5F source runtime authority only after source manifest validation and before every evidence-quality reducer.
3. Persist a positive-only runtime-attestation gate proof, then seal it inside a newly versioned 1.5G review manifest.
4. Require that proof in the post-hotfix Stage 1.5H input path; reject old/no-proof bundles.
5. Put an exact zero-writer-before-checkout procedure in the existing VPS runbook.

### 4.2 Non-Goals

1. Do not change 1.5F proof rules, protected paths, Git checks, sticky-latch behavior, source APIs, collection scheduling, root ownership, or status recovery semantics.
2. Do not alter `configs/base.py`, any coverage/quarantine/static-proxy threshold, Stage 1.5G summary/quarantine v2 schema, existing 1.5G review-id formula, or Stage 1.5H output bundle schema.
3. Do not modify, overwrite, delete, re-sign, migrate, re-promote, or merge `20260902T105158Z_stage1_5f` or any historical 1.5G/1.5H artifact.
4. Do not use a current Git checkout, file mtime, operator declaration or copied root path as a substitute for historical runtime evidence.
5. Do not enable any trade, paper, live, execution, private API, API-key or order endpoint capability.

---

## 5. Stage 1.5G Source Runtime Authority Gate

### 5.1 Ordered authority evaluation

`load_stage1_5g_inputs()` continues to load the same source-root bytes. Before `build_stage1_5g_review_summary()` reaches watermark, event, coverage, raw-integrity or quarantine reducers, it must evaluate exactly:

```text
A. verify_source_evidence_manifest(source_root) == valid
B. parse observer_root_contract.json and live_depth_observer_summary.json once
C. validate their semantic binding
D. validate exact static/runtime/compromised predicate
E. only then run the existing 1.5G quality reducers
```

Failure in A keeps the existing `source_evidence_manifest_missing_or_unreadable` path. B-D failures are source-authority loader blockers. The loader must neither mutate source bytes nor rerun a Git proof.

### 5.2 Contract/summary semantic binding

Both files must parse to JSON objects. The validator uses the existing canonical JSON encoding (`sort_keys=true`, separators `(',', ':')`, `ensure_ascii=false`) for the root-contract hash. Field ownership is fixed by the parent Design/Plan, not by current extra writer bytes: root contract is the startup-static/source-binding artifact; process identity and all runtime state are summary-only authority.

It requires all of the following. Every boolean check uses `type(value) is bool`; no truthiness, `.get(..., default)`, `str()` or `bool()` coercion is permitted.

```text
root_contract.root_contract_schema_version == 1
root_contract.root_mode == "v2_production"

summary.consumer_root_contract_sha256
  == SHA256(canonical JSON bytes of root_contract)

for each field in:
  consumer_root_id
  consumer_startup_commit_sha
  consumer_runtime_manifest_sha256
summary[field] == root_contract[field]

for the shared static boolean field:
  consumer_static_attestation_verified
both summary[field] and root_contract[field] have type(value) is bool
and summary[field] is root_contract[field]

summary.consumer_process_instance_id is a lowercase canonical UUID string:
  ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$
consumer_root_id and consumer_runtime_manifest_sha256 are lowercase SHA-256 hex strings
consumer_startup_commit_sha is lowercase 40-hex Git SHA

root_contract.source_stage1_5d_output_root_id
  == root_contract.source_stage1_5d_events_root_id
  == root_contract.source_stage1_5d_runtime_gate_root_id
  and each is a lowercase SHA-256 hex string

summary.consumer_process_started_at_ms is an int but not bool, > 0
summary.last_heartbeat_at_ms is an int but not bool, > 0
summary.consumer_process_started_at_ms <= summary.last_heartbeat_at_ms

summary.consumer_runtime_attestation_verified is an exact bool
summary.consumer_runtime_attestation_compromised is an exact bool
```

The final time relation is an internal process-order check only. It deliberately does **not** require freshness relative to the offline 1.5G review wall clock, because a valid finished root is expected to be reviewed after its process has stopped.

### 5.3 Exact attestation predicate

After Section 5.2 succeeds, the source authority passes only if:

```text
root_contract.consumer_static_attestation_verified is True
summary.consumer_static_attestation_verified is True
summary.consumer_runtime_attestation_verified is True
summary.consumer_runtime_attestation_compromised is False
```

The static value is cross-artifact bound. `consumer_runtime_attestation_verified` and `consumer_runtime_attestation_compromised` are fresh runtime state and authoritative only in summary; 1.5G must not read same-named root-contract extra bytes when present.

### 5.4 Fail-closed taxonomy

All blockers are stable, sorted and deduplicated. A root may emit more than one.

```text
source_runtime_attestation_root_contract_missing_or_unreadable
  observer_root_contract.json missing, unreadable, non-object or invalid JSON

source_runtime_attestation_contract_summary_binding_invalid
  any Section 5.2 identity/hash/cross-artifact/source-root/time/UUID
  relation or format fails, except attestation-boolean type/value cases
  assigned to the dedicated blockers below

source_static_attestation_field_invalid
  root-contract or summary static field is not an exact bool

source_static_attestation_unverified
  shared static field is exactly false

source_runtime_attestation_verified_field_invalid
  summary consumer_runtime_attestation_verified is not an exact bool

source_runtime_attestation_unverified
  summary consumer_runtime_attestation_verified is exactly false

source_runtime_attestation_compromised_field_invalid
  summary consumer_runtime_attestation_compromised is not an exact bool

source_runtime_attestation_compromised
  summary consumer_runtime_attestation_compromised is exactly true
```

Boolean blocker precedence is exclusive and deterministic:

```text
static field non-bool
  -> source_static_attestation_field_invalid only

both static fields exact bool and equal false
  -> source_static_attestation_unverified only

both static fields exact bool but unequal
  -> source_runtime_attestation_contract_summary_binding_invalid only

runtime_verified non-bool
  -> source_runtime_attestation_verified_field_invalid only

runtime_verified exact false
  -> source_runtime_attestation_unverified only

runtime_compromised non-bool
  -> source_runtime_attestation_compromised_field_invalid only

runtime_compromised exact true
  -> source_runtime_attestation_compromised only
```

The validator must not coerce a malformed boolean or infer a positive compromise from a non-bool value. Any source-authority blocker forces:

```text
decision = stage1_5g_depth_evidence_invalid
allowed_next_action = continue_observation
evidence_scope = none
event_family_conclusion_allowed = false
all emitted trading/execution/alpha permissions = false
```

No clean/quarantined pass and no consumer-eligible closed bundle may be emitted.

---

## 6. Minimal Stage 1.5F Contract Completion

The parent runtime-attestation Design requires a process-start field but current implementation does not serialize it. The smallest compatible repair is:

```text
consumer_process_started_at_ms
  = one UTC epoch-millisecond integer captured once when the observer process starts
  = immutable for that process
  = passed through existing runtime_gate_context
  = written by the existing atomic live_depth_observer_summary writer
```

It is a new required **summary** field for post-hotfix roots only. It is not added to root contract, runtime proof input, state JSONL, watermark, 1.5D event schema, config, or any historical root. The existing root-contract fields and 1.5F sticky-latch semantics remain unchanged.

A newly started root lacking this field is invalid for 1.5G promotion; a historical root is diagnostic-only and also invalid. This is intentionally fail-closed rather than a backward-compatible default.

---

## 7. Durable Downstream Proof and Versioned Artifact Grammar

### 7.1 Positive-only runtime-gate proof

When and only when Sections 5-6 pass **and** the unchanged 1.5G reducer has reached a consumer-eligible `stage1_5g_depth_evidence_quarantined_pass`, 1.5G writes:

```text
stage1_5g_runtime_attestation_gate.json
```

Its exact top-level keys are:

```text
schema_version
source_runtime_attestation_gate_verified
stage1_5g_review_id
source_evidence_manifest_sha256
consumer_process_instance_id
consumer_root_id
consumer_process_started_at_ms
consumer_startup_commit_sha
consumer_root_contract_sha256
consumer_runtime_manifest_sha256
consumer_static_attestation_verified
consumer_runtime_attestation_verified
consumer_runtime_attestation_compromised
source_runtime_attestation_authority_sha256
```

Required values:

```text
schema_version == 1
source_runtime_attestation_gate_verified is True
the three attestation values are exactly True, True, False
all copied identity/attestation values equal the Section 5 validated summary projection
stage1_5g_review_id and source_evidence_manifest_sha256 equal the emitted 1.5G summary
source_runtime_attestation_authority_sha256
  == SHA256(canonical JSON of this object with only that hash key omitted)
```

The proof is not written for source-authority failure, quality failure, clean-only output, or partial output. It creates no new permission.

### 7.2 Stage 1.5G review manifest v3

The existing summary/quarantine artifacts remain `schema_version=2` and retain their current `stage1_5g_review_id` formula. Rather than silently adding fields to those frozen schemas, only the sealed review-manifest contract is versioned:

```text
stage1_5g_review_manifest.json.schema_version = 3
```

The v3 manifest retains its existing identity keys and must contain exactly these five artifact entries:

```text
summary
quarantine_summary
quarantined_invalid_book_rows
depth_quality_input_rows
runtime_attestation_gate
```

Every entry retains the existing `relative_path`, `sha256`, `byte_count` grammar. The proof artifact must be written before the manifest; the manifest is written last. A partial output with no valid v3 manifest is not a closed promotion bundle.

`verify_stage1_5g_review_manifest()` on the post-hotfix 1.5H consumer path must require v3, exact five-entry artifact membership, all existing artifact hash/linkage checks, and Section 7.1 proof verification. It must reject manifest v2, missing proof, unexpected proof keys, hash mismatch, proof-summary linkage mismatch or authority-hash mismatch with:

```text
stage1_5h_runtime_attestation_gate_missing_or_invalid
```

### 7.3 Historical revocation boundary

Already-written v2 Stage 1.5G/1.5H artifacts are immutable diagnostic history. They are not overwritten or retrospectively reclassified. However, after this Hotfix, the 1.5H input loader must not generate a new report from a v2 manifest because it lacks the required runtime gate proof. Consequently, old bundles cannot be counted in the post-hotfix Stage 1.5 evidence ledger.

This is admission revocation for future consumption, not historical mutation.

### 7.4 Legacy Stage 1.5H compatibility matrix

The Hotfix changes only the post-hotfix v2 event-bundle admission path. It does not rewrite or broaden the legacy Stage 1.5H CLI.

| Input path | Post-hotfix behavior | Evidence-ledger status |
|---|---|---|
| Pre-hotfix Stage 1.5G v2 manifest | The post-hotfix v2 event-bundle loader rejects it: no sealed runtime-gate proof | historical diagnostic only; excluded |
| New Stage 1.5G v3 manifest plus valid proof | Enters the unchanged v2 per-symbol checks | eligible only if all existing checks pass |
| v3 manifest with missing, malformed or unlinked proof | Reject with `stage1_5h_runtime_attestation_gate_missing_or_invalid` | excluded |
| Historical Stage 1.5H v1 / N=1 legacy CLI path | Legacy CLI behavior and artifact grammar remain unchanged; it may render only a legacy/historical read-only report | never runtime-attested, never post-hotfix promotion, never counted in the post-hotfix Stage 1.5 evidence ledger |

No new legacy CLI admission is introduced. If a future requirement is to revoke the legacy CLI itself, that is a separate parent-contract change and is outside this Hotfix.

---

## 8. Stage 1.5H Admission Contract

Stage 1.5H keeps its v2 per-symbol report/bundle schema and static-proxy computations. Before its existing v2 source-of-truth checks, it must require the closed 1.5G v3 manifest and verify the runtime gate proof described in Section 7.

```text
valid v3 1.5G manifest
AND valid sealed gate proof
AND proof.stage1_5g_review_id == summary.stage1_5g_review_id
AND proof.source_evidence_manifest_sha256 == summary.source_evidence_manifest_sha256
AND proof exact positive predicate
-> existing Stage 1.5H v2 per-symbol validation
```

Otherwise:

```text
decision = stage1_5h_v2_event_bundle_input_rejected
report_generation_allowed = false
all safety flags remain false
```

No new 1.5H output field, metric, threshold or permission is introduced. The changed input admission is required solely to make the 1.5G source-authority result durable and consumer-verifiable.

---

## 9. State, Failure, Crash and Idempotency

### 9.1 Reducer and write ordering

```text
source manifest validation
-> contract/summary binding
-> exact attestation gate
-> existing 1.5G reducers
-> existing quarantine artifacts and JSON/Markdown summary
-> positive runtime-gate proof (only for eligible quarantined pass)
-> v3 manifest written last
```

1.5G remains offline and read-only with respect to its source root. A crash before the final manifest leaves no consumable bundle. Re-running the same immutable source to a **new** review output root is idempotent: valid source authority and unchanged reducer inputs yield the same review decision; an invalid source authority continues to yield invalid.

### 9.2 Historical immutability versus allowed diagnostic rerun

Forbidden:

```text
modify a source root
overwrite an old 1.5G/1.5H artifact
treat a diagnostic rerun as historical artifact migration or promotion
```

Allowed:

```text
pytest fixture roots or an explicitly disposable local diagnostic review root
perform a read-only rerun against frozen source bytes
```

The known compromised `20260902T105158Z_stage1_5f` root must be tested only through the allowed diagnostic path and must remain invalid.

---

## 10. VPS Deployment Ordering

### 10.1 Exact zero-writer gate

For target `PROJECT_ROOT=/root/crypto-alpha-lab`, a relevant writer is a live process for which all are true:

```text
its /proc/<pid>/cwd resolves to PROJECT_ROOT
its NUL-delimited argv contains a path which, resolved against that cwd when relative,
equals either:
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
```

The runbook must use a small inline Python standard-library inspector over `/proc`, not an unscoped `grep`, to print matching PID/cwd/argv and return its count. `tmux kill-session` is only a requested-stop mechanism, never zero-writer proof.

Deployment is one fail-closed shell sequence:

```text
request stop for D and F tmux sessions
-> inspect exact writer set once per second for at most 30 seconds
-> count == 0
-> git fetch / checkout DEPLOY_COMMIT
```

If the count remains nonzero, terminate the sequence with:

```text
STOP=stage1_5d_1_5f_writer_still_running
```

The process probe must return nonzero on inspection error; it must not be followed by `|| true`. `git checkout` appears only after a successful zero result in the same `set -euo pipefail` shell block, so checkout is unreachable when the stop proof fails. After checkout, require exact `HEAD == DEPLOY_COMMIT`, clean protected worktree, a fresh `RUN_ID`, and a fresh root before ordinary restart.

### 10.2 Producer-disabled versus configured-true deployment

The current ordinary deployment retains:

```text
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False
```

For that mode, Section 10.1 is followed by fresh 1.5D then fresh 1.5F startup and initial verified/uncompromised summary check.

If a future, separately authorized deployment sets `configured_enabled=true`, this Hotfix supplies only the zero-writer/checkout/fresh-root boundary. It does **not** replace the parent authority's E0/E1/E2 handshake:

```text
E0: start a newly created post-checkout 1.5D root in BOOTSTRAP_WAITING_FOR_CONSUMER
E1: start same-commit 1.5F against that root and wait for valid contract/summary
E2: restart 1.5D at the same commit and same newly created D root with explicit F paths, then arm
```

E2's same-root restart is an explicit parent-contract exception to the ordinary fresh-root-after-checkout rule. No pre-checkout historical root may be reused.

---

## 11. Acceptance Invariants and Proof Matrix

| Invariant | Mechanical proof | Fail-closed result |
|---|---|---|
| INV-01 Parent authority | SHA-256 checks for all Section 2 bytes before Plan | `STOP=revision_authority_incomplete` |
| INV-02 1.5F completion | canonical 1.5F runner/serializer emits immutable positive integer start time; missing/zero/bool/after-heartbeat mutations reject | no 1.5G promotion |
| INV-03 source binding | canonical valid root; one declared mutation each for contract hash, process UUID malformed, root ID, commit, manifest SHA, source-D triple or root mode | `source_runtime_attestation_contract_summary_binding_invalid` |
| INV-04 exact booleans | canonical root plus, for each triad field, its canonical valid boolean and every non-canonical boolean, missing or malformed value; also a valid-but-unequal static pair | canonical values yield no blocker; every invalid mutation yields exactly one Section 5.4 blocker selected by the precedence matrix, and an unequal static pair yields binding-invalid only; no coercion |
| INV-05 known compromised root | read-only rerun of `20260902T105158Z_stage1_5f` to a disposable output root | invalid with runtime-unverified and compromised blockers; historical bytes unchanged |
| INV-06 valid existing reducer | canonical post-hotfix source root with valid binding/triad and existing multi-symbol fixture | unchanged v2 summary/quarantine metrics and decision |
| INV-07 durable proof | valid eligible pass emits exact v1 proof and sealed v3 manifest; mutate proof hash, ID linkage, field key, artifact hash or delete proof | 1.5H rejects with `stage1_5h_runtime_attestation_gate_missing_or_invalid` |
| INV-08 legacy rejection | a pre-hotfix v2 manifest with otherwise valid v2 artifacts | updated 1.5H rejects; no new report |
| INV-09 crash closure | interrupt after any artifact before final manifest | no closed consumer-eligible bundle; rerun to new output root only |
| INV-10 zero writer | `/proc` fixture/static proof for both writer scripts, wrong cwd, residual writer and inspector error | checkout unreachable unless exact count is zero |
| INV-11 E0/E1/E2 preservation | runbook static proof shows configured-true branch delegates to parent E0/E1/E2 | no simplified D->F replacement |
| INV-12 safety | import `configs.base` and inspect 1.5G/1.5H outputs | all execution-related flags false |

Positive cross-boundary fixtures must call canonical 1.5F constructor/serializer and strict 1.5G/1.5H loaders. Negative fixtures may make exactly one declared mutation after canonical artifact generation, then regenerate the disposable source manifest where the test is intended to reach a later gate.

---

## 12. Rollout, Rollback and Open Questions

1. Only after Design approval, approved Plan, implementation and independent completion audit may the Section 10 runbook be used.
2. Do not resume or deploy over the compromised root. Start a fresh post-checkout root; its initial summary must pass Sections 5-6 before it can later be promoted by 1.5G.
3. If initial runtime attestation fails, preserve the fresh failed root as diagnostic evidence and stop. Do not override the latch or backfill fields.
4. Rollback means return code to the prior approved commit **after** the same zero-writer gate, then create another fresh root. It never means restoring or rewriting historical root bytes.

Open question, non-blocking: the old compromised root does not persist the precise runtime-proof failure reason. This Hotfix intentionally does not add it; a future observability Design may do so without changing the truth value of this gate.

---

## 13. Author-Side Mini Closure Confirmation

```text
P0-1 closed: exact parent paths/SHA-256 are bound in Section 2.
P0-2 closed: Section 5 uses source manifest plus root-contract/summary semantic binding;
               it restores parent field ownership, validates canonical process UUID only in summary,
               and Section 6 closes the parent-required missing process-start field without path-based rejection.
P0-3 closed: Sections 7-8 create a separately versioned durable proof and require it in 1.5H.
P1-1 closed: malformed fields have distinct invalid-field blockers and are not asserted compromised.
P1-2 closed: Section 9.2 separates immutable history from disposable diagnostic reruns.
P1-3 closed: Section 10.1 freezes the /proc predicate, bounded poll, STOP and checkout reachability.
P1-4 closed: Section 10.2 explicitly preserves parent E0/E1/E2 for configured-enabled mode.
NEW-P1-01 closed: Section 7.4 freezes legacy v1/N=1 as historical-only and excludes it from post-hotfix evidence.

no_touch_violation_count = 0
scope_expanded_beyond_blocker_impact_cone = false
implementation_allowed = false
deployment_allowed = false
runtime_action_allowed = false
```

This author-side check is not approval. External closure confirmation remains required.
