# Historical Research Decision Record Correction Implementation Plan

> **For Codex:** 仅在本 Plan 通过独立审核、用户给出 exact implementation approval 后，使用 `executing-plans` 逐 Task 执行。

**Goal:** 仅将 `docs/roadmap.md` 与 `docs/project-status/current-document-index_CN.md` 中关于 Route C1、Stage 1.4B-Lite crowding-only 与已测试 pure-price Factor Lab 的历史决策表述，收敛为经批准 Delta 定义的事实边界。

**Architecture:** 这是纯文档治理。执行器在 `/tmp` 创建单次、可核验的 provenance bundle；从冻结 baseline 依据 Design R1-R12 生成完整 expected documents，先完成独立字节、语义、scope 和 provenance 验证，再依序以 same-filesystem `os.replace()` 发布 `current-document-index_CN.md` 和 `roadmap.md`。候选文件始终位于 bundle 内；若 `/tmp` 与目标父目录不在同一设备，安全停止而非在仓库内创建临时路径。不创建仓库代码、manifest、schema、策略或运行时 artifact。

**Tech Stack:** Bash、Python 3 标准库、Git、`shasum`、`cmp`、`.agent/tools/anti_shortcut_scan.py`。

---

## 1. Approved Design Binding

| Item | Exact value |
| --- | --- |
| Approved Delta Design | `docs/designs/2026-09-28-historical-research-decision-record-correction-delta-design_CN.md` |
| Approved Delta SHA-256 | `37ff23045de7519b426ff1da71e04ec8d61ce371ccafe3fae96711802201583f` |
| Serial publication dependency | commit `d2ad662b6b10bc495fc07a23ad8a0aa0fd396f0d` |

### Immutable authorities

The approved Delta/Plan, L2, historical reviews/summaries, and serial Git dependency are immutable authorities. They remain exact throughout fresh start, publication, resume and completion.

### Mutable target identities

The following values are **input baseline identities**, not immutable post-publication authorities:

| Target | Reviewed baseline SHA-256 | Fresh-start condition | Resume/final condition |
| --- | --- | --- | --- |
| `docs/roadmap.md` | `217bb60180c4300ca03a5efe7335f00b7ae313c249216f3a1235e314a3531f32` | current target equals this baseline | original bundle baseline copy equals this baseline; current target equals original expected copy |
| `docs/project-status/current-document-index_CN.md` | `509589227b2c5518b4e43b08fe8ac12bd620ce448028b8b276e2a75d074c414e` | current target equals this baseline | original bundle baseline copy equals this baseline; current target equals original expected copy |

The implementation authorization must bind both this exact Plan and the exact Delta. Any mismatch before candidate generation, backup, or write is `STOP=approved_authority_mismatch` or `STOP=historical_decision_correction_design_approval_mismatch`.

## 2. Allowed Scope And Permission Isolation

**Only repository files that may be changed by an approved implementation:**

- `docs/roadmap.md`
- `docs/project-status/current-document-index_CN.md`

**Generated evidence:** a unique `/tmp/historical_decision_correction.<attempt_id>/` provenance directory is the only recovery authority for its own attempt. Its `candidates/` children are regular non-symlink files. Candidate identity, SHA-256, length and mode are recorded in an attempt-local direct integrity record. A candidate is consumed by `os.replace()` or retained only for same-attempt resume. If a candidate does not share `st_dev` with the final target parent, stop with `STOP=historical_decision_correction_cross_filesystem_publish`; never create a temporary repository path as fallback.

**No-touch:** every other repository path, including the Delta, this Plan, original reviews/summaries/reports, `src/`, `scripts/`, `tests/`, `configs/`, `data/`, runtime roots, VPS runbooks, external artifacts, and Git index.

**All permissions remain false:** `RISK_LIVE_TRADING_ENABLED`, network collection, replay, private/authenticated/order API, strategy/execution, paper/live trading, deployment, SSH, commit and push. No network request, collection, backtest, remote command, deployment, commit or push belongs to this Plan.

If a required change falls outside the two target paths or R1-R12, stop with `STOP=historical_decision_correction_scope_drift` and start a new Design.

## 3. Authority And Invariant Routing

| Delta authority edge / invariant | Implementation task and mechanical proof | Fail-closed result |
| --- | --- | --- |
| §2 immutable authority packet and approved Delta bytes, INV-HDRC-01 | Task 0 recomputes immutable SHA-256 values, validates approved path/SHA variables and Git dependency before creating a bundle | `STOP=historical_decision_correction_authority_mismatch` |
| §2.1 post-Stage-1.6 serial dependency | Task 0 validates commit existence, ancestry and historical roadmap blob SHA | `STOP=historical_decision_correction_stage1_6_publication_dependency_mismatch` |
| §5 R1-R12 exact transformation, INV-HDRC-02 | Task 1 derives expected files only from frozen baselines and exact Design templates; Task 4 uses byte-for-byte equality | `STOP=historical_decision_correction_expected_document_mismatch` |
| C1, B-Lite and Factor semantic limits, INV-HDRC-03..05 | Task 1 requires each owned range to equal one exact template and Task 4 rejects any extra owned-range assertion | `STOP=historical_decision_correction_semantic_mismatch` |
| No promotion or runtime authority, INV-HDRC-06 | Task 4 runs owned-range promotion gate, safety AST check and actual scanner RC | `STOP=historical_decision_correction_permission_violation` |
| User worktree/index preservation, INV-HDRC-07 | Task 0 snapshots full pre-existing path/index ledger; Task 4 compares it exactly except the two approved targets | `STOP=historical_decision_correction_provenance_mismatch` |
| Atomic two-document publication and recovery, INV-HDRC-08 | Tasks 2-3 use only durable same-device candidates, `os.replace`, parent-directory fsync and state recognition | `STOP=historical_decision_correction_publication_state_corrupt` |

## 4. Revision Closure Ledger

This is the first Plan Closure Audit continuation. The revised Plan changes only its own execution contract; the approved Design, R1-R12 prose, historical conclusion semantics, target-document bytes, authority SHA values, permissions and lifecycle owner remain frozen.

| ID | Severity | Proof edge and reachable failure | Revision closure criterion | Impact cone |
| --- | --- | --- | --- | --- |
| P0-1 | P0 | Published targets were rechecked as input baselines, so a correct publication could never reach Task 4 | Immutable authorities are distinct from target input baselines; final targets are checked only against bundle expected bytes | §§1, 3, 5; Tasks 0, 3, 4; State/transition/invariant rows |
| P0-2 | P0 | Candidate in a target parent could leave a new untracked repository path after a crash | Candidates exist only under the repo-external bundle; unequal devices stop | §§2, 5; Tasks 1-3; state and scope rows |
| P0-3 | P0 | `os.replace()` adopts candidate mode and can silently change a target to `0600` | Original target modes are captured, candidate modes must match, and post-publish/final modes must equal originals | Tasks 0-4; provenance and invariant rows |
| P0-4 | P0 | An unauthorized commit can change `HEAD` while target bytes/index still pass | `base_sha` is created as a direct integrity record and exact `HEAD` is required at every transition, resume, review and audit handoff | Tasks 0-5; state/authority/invariant rows |
| P0-5 | P0 | Generator and validator could share a hand-copied incorrect R template | Separate generator/validator extract each R1-R12 fenced block directly from verified Design bytes | Task 1 positive fixture; semantic final gate |
| P0-6 | P0 | A crash after `os.replace()` can precede a state marker, and consumed candidates have different lifecycle requirements | Target bytes determine state; state-aware candidate checks follow state determination | §5 State x Artifact, Tasks 1-3 and recovery proof |
| P1-1 | P1 | Existing tables did not bind artifact consumers to all state transitions | Add complete State x Artifact, Transition x Failure, Authority, Invariant x Evidence matrices | §5 and all tasks |
| P1-2 | P1 | An open-ended self-referential central integrity listing could become a new subsystem | Use only state-specific, non-self-referential attempt-local integrity records | Tasks 0-4 and recovery rows |
| P1-3 | P1 | Global `git diff --check` can reject preserved unrelated user whitespace | Diff check is restricted to the two target paths; non-target state uses ledger equality | Task 4 |
| P1-4 | P1 | Code-review remediation was routed through Completion-Audit remediation despite `both_published` having no mutation transition | Code review first follows `receiving-code-review`; Completion Audit OPEN findings alone use remediation workflow, with Rule-12 classification | Task 5 |

### Mutable Set

- This Plan only: §§1-5, Tasks 0-5, and Final Scope Checklist.

### No-Touch Set

- `docs/designs/2026-09-28-historical-research-decision-record-correction-delta-design_CN.md` and every frozen SHA/claim in it.
- R1-R12 canonical text, Route C1/B-Lite/Factor Lab historical conclusions, all authority files, source/config/test/data/runtime paths, target documents, Git index, network and trading permissions.
- Publication order `current-document-index_CN.md -> roadmap.md`, `os.replace()` primitive, no-rollback/no-rebaseline rule, and the external-lifecycle ownership of code review/Completion Audit.

## 5. Closure Matrices

### 5.1 State x Artifact

| State | targets | bundle-required records | candidates | Git/provenance state | permitted action |
| --- | --- | --- | --- | --- | --- |
| `before` | both exact input baselines, original modes | none, or incomplete non-resume attempt only | absent | no snapshot consumer | fresh-start preflight only |
| `staged` | both exact input baselines, original modes | `attempt_record.json`, `base_sha`, `authority.sha256`, baseline/expected/template copies with named `.sha256` and `.length`, `target_index_snapshot.json`, `preexisting_path_ledger.jsonl`, `candidate_record.json` | both durable external candidates exist, match candidate record and frozen modes | `HEAD == base_sha`; target index equals snapshot | publish index only |
| `index_published` | index exact expected/mode; roadmap exact baseline/mode | same state-independent records as `staged` | index candidate is consumed/absent; roadmap candidate exists and matches candidate record/mode | `HEAD == base_sha`; index entries equal snapshot; non-target ledger exact | resume: publish roadmap only |
| `both_published` | both exact expected bytes and original modes | same state-independent records as `staged` | both candidates are consumed/absent | `HEAD == base_sha`; index entries/ledger exact | validation, review and audit only |
| any other state | any other bytes/mode/type | missing/corrupt required record | any | any | `STOP=historical_decision_correction_publication_state_corrupt` |

State is inferred only from exact target bytes plus original verified baseline/expected copies and provenance. No `state.*.json` is produced or consumed as state authority. Each listed `.sha256` covers exactly its named sibling file, never itself and never an open-ended directory. These records are attempt-local recovery evidence, not a publication manifest, sealed root or consumer-facing subsystem.

### 5.2 Transition x Failure

| Transition | Precondition | Failure handling | Required postcondition / resume route |
| --- | --- | --- | --- |
| `before -> staged` | immutable authorities, reviewed target baselines, original modes/index, `HEAD == base_sha` | any record/candidate/template/fsync failure stops before target write | targets remain exact baselines; incomplete bundle is not resume authority |
| `staged -> index_published` | all state-independent records valid; both candidates lifecycle-valid; index candidate same-device and original mode; `HEAD == base_sha` | pre-replace failure leaves `staged`; crash yields only baseline or expected index | valid `index_published` is inferred from target bytes and may resume only with original bundle |
| `index_published -> both_published` | original bundle valid; index candidate absent, roadmap candidate lifecycle-valid/same-device/original-mode; `HEAD == base_sha` | failure leaves `index_published`; do not rewrite index | `both_published` is inferred from target bytes; resume only publishes roadmap from original candidate |
| `both_published -> validation` | both target bytes/modes expected; `HEAD == base_sha` | validator/review/audit failure stops; no rollback/rebaseline | target mutation requires Rule-12 classification and a new approved route |

### 5.3 Authority Matrix

| Action | Owner / source of truth | Positive proof | Negative proof | Stop / forbidden shortcut |
| --- | --- | --- | --- | --- |
| Extract R1-R12 templates | verified approved Delta bytes | independent extractor finds each expected label and one fenced block | duplicate/missing label or block | `STOP=historical_decision_correction_template_authority_mismatch`; no copied constants |
| Create expected/candidates | baseline copies + extracted templates | expected/candidate equality and original mode | one-byte/template/mode mutation rejected | `STOP=historical_decision_correction_expected_document_mismatch` |
| Publish a target | original attempt bundle | same-device candidate, candidate mode, `HEAD`, index and authority gates | unequal device/mode/HEAD reject | no repository temp file, copy, truncate or manual edit |
| Resume | original attempt bundle only | exact state and direct integrity records | missing/corrupt record rejects | no new bundle or rebaseline |
| Review/audit handoff | reviewed final bytes plus immutable bundle evidence | `HEAD == base_sha`, target/ledger/scanner gates pass | any drift rejects | no executor self-certification |

### 5.4 Invariant x Mechanical Evidence

| Invariant | Owner task | Canonical positive fixture | Required negative mutation | Every-transition / final consumer |
| --- | --- | --- | --- | --- |
| INV-HDRC-01 | Task 0 | exact approved paths/SHA and immutable authority bytes | one authority-byte mismatch | all transitions and Task 4 recheck immutable items |
| INV-HDRC-02..05 | Task 1 | copied baseline plus separately extracted R1-R12 Design templates | one-byte and forbidden-semantic candidate mutation | Task 4 exact expected equality and independent extraction |
| INV-HDRC-06 | Task 4 | exact owned ranges with required limiting language | promotion-phrase mutation | target-scoped semantic/safety/scanner gates |
| INV-HDRC-07 | Task 0 | original target modes, `base_sha`, target index snapshot and full non-target ledger | wrong candidate mode and changed HEAD | every publish, resume, review/audit handoff and Task 4 |
| INV-HDRC-08 | Tasks 1-3 | durable external same-device candidates and ordered replace | unequal-device and missing-record mutations | state recognition, parent fsync and expected-byte/mode recheck |

## 6. Publication State Contract

| State | document-index | roadmap | valid next action |
| --- | --- | --- | --- |
| `before` | exact reviewed baseline | exact reviewed baseline | only fresh-start preflight |
| `staged` | exact reviewed baseline | exact reviewed baseline | only atomic document-index publish |
| `index_published` | exact expected bytes | exact reviewed baseline | resume only with the same valid provenance bundle; publish roadmap only |
| `both_published` | exact expected bytes | exact expected bytes | full verification, code review and fresh Completion Audit only |
| any other combination | anything else | anything else | `STOP=historical_decision_correction_publication_state_corrupt` |

Fresh start and resume are mutually exclusive.

- `fresh_start_preflight`: both targets are regular non-symlink files, exact reviewed baselines, unstaged, and their index entries are captured before any target write.
- `resume_preflight`: caller explicitly supplies the original bundle. Only `index_published` or `both_published` is valid. The bundle's baseline/expected copies, attempt identity, authority record and ledger must all pass their recorded hashes. Do not create a new bundle, rebaseline targets, or require a published target to equal the reviewed baseline.
- Missing, corrupt or `/tmp`-lost original bundle is `STOP=historical_decision_correction_resume_provenance_unavailable`.

## Task 0: Approval, Authority, Baseline And Provenance Gate

**Repository files:** none. **External evidence:** one fresh `/tmp/historical_decision_correction.<attempt_id>/` bundle only after every fresh-start gate passes.

### Step 0.1: Bind exact user approval before any write

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${APPROVED_DELTA_DESIGN_PATH:?STOP=APPROVED_DELTA_DESIGN_PATH_missing}"
: "${APPROVED_DELTA_DESIGN_SHA256:?STOP=APPROVED_DELTA_DESIGN_SHA256_missing}"
: "${APPROVED_PLAN_PATH:?STOP=APPROVED_PLAN_PATH_missing}"
: "${APPROVED_PLAN_SHA256:?STOP=APPROVED_PLAN_SHA256_missing}"
cd "$PROJECT_ROOT"

DELTA='docs/designs/2026-09-28-historical-research-decision-record-correction-delta-design_CN.md'
PLAN='docs/plans/2026-09-29-historical-research-decision-record-correction-implementation-plan_CN.md'
DELTA_SHA='37ff23045de7519b426ff1da71e04ec8d61ce371ccafe3fae96711802201583f'

test "$APPROVED_DELTA_DESIGN_PATH" = "$DELTA" || { echo 'STOP=historical_decision_correction_design_approval_mismatch:path' >&2; exit 1; }
test "$APPROVED_DELTA_DESIGN_SHA256" = "$DELTA_SHA" || { echo 'STOP=historical_decision_correction_design_approval_mismatch:sha' >&2; exit 1; }
test "$(shasum -a 256 "$DELTA" | awk '{print $1}')" = "$DELTA_SHA" || { echo 'STOP=historical_decision_correction_design_approval_mismatch:bytes' >&2; exit 1; }
test "$APPROVED_PLAN_PATH" = "$PLAN" || { echo 'STOP=approved_authority_mismatch:plan_path' >&2; exit 1; }
test "$(shasum -a 256 "$PLAN" | awk '{print $1}')" = "$APPROVED_PLAN_SHA256" || { echo 'STOP=approved_authority_mismatch:plan_bytes' >&2; exit 1; }
echo 'CHECK_OK=approved_delta_and_plan_bound'
```

Expected: `CHECK_OK`, exit `0`. Any failure stops before snapshots, candidates or target writes.

### Step 0.2: Validate immutable authority bytes and publication dependency

The executor must use this exact list, reporting one `CHECK_OK=authority:<path>` per item. Missing/non-regular/symlink paths or hash differences stop with `STOP=historical_decision_correction_authority_mismatch`.

```text
61ba2f7acb88b91db9f23a2f9f085bc493d52160d6ee411978573cb96d9f3ac4 docs/reviews/2026-09-27-historical-alpha-methodology-audit_CN.md
806314e860bbf94d0e4332377d8bf617471f31dfcb51ffab1b646220ba8aed27 .agent/rules/L2_Alpha_Research_Methodology.md
c6f4eef35c87c43348d2cccfd06e2980046806c056565afeac86ef02c30e85eb docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md
3314415f69539bc3370a19cc014a2637d250e9ccbd4e03649d2e627c3779aa55 reports/route_c1/route_c1_live_smoke_7d_summary.json
fee493979a97c4f3fe3a182988e9bd36f877197a4eb7f1606d089affe975824e docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md
7872b201559239e77ae7e109f4dc2b00a161494487267ee2396f0c41fb07ca55 reports/external_signal_shadow/stage1_4b_lite_funding_oi_price_crowding_replay_500trials_real_summary.json
720b7f36bd4084883ecbb1dec9c7588e516d8d1f7207e3f0ec0efb2934704cd1 docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md
b2429af21c9a7fb42ed919efa0c3542498346dcd2a1833ac1d7a8a2d396ca244 reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json
```

Also require:

```bash
git cat-file -e d2ad662b6b10bc495fc07a23ad8a0aa0fd396f0d^{commit} || exit 1
git merge-base --is-ancestor d2ad662b6b10bc495fc07a23ad8a0aa0fd396f0d HEAD || exit 1
test "$(git show d2ad662b6b10bc495fc07a23ad8a0aa0fd396f0d:docs/roadmap.md | shasum -a 256 | awk '{print $1}')" = \
  217bb60180c4300ca03a5efe7335f00b7ae313c249216f3a1235e314a3531f32 || exit 1
```

Any of the three Git checks failing is `STOP=historical_decision_correction_stage1_6_publication_dependency_mismatch`.

### Step 0.3: Fresh-start target-baseline and provenance capture

Require `EXECUTION_PROVENANCE_DIR` to be unset. Generate a unique attempt directory with `mktemp -d /tmp/historical_decision_correction.XXXXXX`. Do not use a caller-supplied path.

Before generation, validate the two current targets against the §1 mutable target input-baseline table, then capture into that directory:

- immutable `attempt_id`, UTC creation timestamp, approved Design/Plan paths/SHA values, and immutable authority hashes in `attempt_record.json` plus a direct sibling `attempt_record.json.sha256`;
- `base_sha` containing exactly `git rev-parse HEAD` plus `base_sha.sha256`; every later transition reads this exact path and must require current `HEAD` equality;
- byte copies of the two reviewed target baselines, each with direct named `.sha256` and `.length` records;
- `git status --porcelain=v1 -z --untracked-files=all`, `git diff --binary`, `git diff --cached --binary`, and target index entries (`mode`, `blob`, `stage`);
- a full pre-existing path ledger: path, porcelain XY, file type, mode, worktree SHA (or symlink target), and Git index mode/blob/stage, in `preexisting_path_ledger.jsonl` with its direct `.sha256` record;
- `target_index_snapshot.json` with direct `.sha256`, including original target worktree mode and index mode/blob/stage;
- `authority.sha256`, a fixed table of the eight immutable file authorities only; it does not contain target baselines, candidates, state records, itself or arbitrary later files.

The ledger must include pre-existing dirty, staged and untracked files. It is comparison evidence, not a clean-worktree requirement. Either target being symlinked, staged, non-regular or failing its reviewed baseline hash stops with `STOP=historical_decision_correction_fresh_start_preflight_failed`. Record each target's original `stat.S_IMODE(target.lstat().st_mode)` before generation; later candidate and published target modes must equal this frozen value.

The producer must create the HEAD record exactly once, before candidate generation:

```bash
git rev-parse HEAD > "$EXECUTION_PROVENANCE_DIR/base_sha"
printf '%s  %s\n' "$(shasum -a 256 "$EXECUTION_PROVENANCE_DIR/base_sha" | awk '{print $1}')" \
  base_sha > "$EXECUTION_PROVENANCE_DIR/base_sha.sha256"
test "$(git rev-parse HEAD)" = "$(cat "$EXECUTION_PROVENANCE_DIR/base_sha")" || {
  echo 'STOP=historical_decision_correction_head_drift' >&2
  exit 1
}
```

**Crash proof:** terminate the generator before candidate publication. Both targets must equal their copied baseline files; incomplete bundles cannot be resume authority. A new fresh start must recapture provenance after preflight passes.

## Task 1: Deterministically Build And Validate Complete Candidates

**Repository files:** none. **External evidence:** `<bundle>/expected/` and `<bundle>/candidates/` only. Candidates must remain outside the repository; failure of the same-device gate is a safe stop, not permission to relocate them.

### Step 1.1: Implement the one-off external generator

The implementation may be a Python 3 standard-library script stored only in the provenance bundle. It must not be added to `src/`, `scripts/` or any repository path. It writes candidates only to `<bundle>/candidates/`.

Inputs are only:

- the two bundle baseline copies;
- the verified approved Delta bytes;
- the verified approved Delta SHA for the single R9 placeholder;
- an extractor that parses the verified approved Design bytes.

The generator must:

1. Locate exactly one `### 5.2 Exact canonical text` heading and the next exact `## 6. Acceptance Invariants` heading in the verified Design bytes; reject a missing, duplicate or inverted boundary with `STOP=historical_decision_correction_template_authority_mismatch`. Extract only this bounded §5.2 byte slice. For every required label (`ROADMAP_FACTOR_MATRIX_ROW` through `INDEX_FACTOR_SECTION`), require exactly one label occurrence in that slice and exactly one immediately following `markdown` fenced block. Persist the extracted bytes as `<bundle>/templates/<label>.md` with direct `.sha256` and `.length` records. Missing, ambiguous, duplicate or malformed extraction is `STOP=historical_decision_correction_template_authority_mismatch`.
2. Parse neither free prose nor current target documents after baseline capture. Apply R1-R8 to the roadmap baseline and R9-R12 to the index baseline exactly once each, using frozen boundary anchors. A missing, ambiguous or duplicate anchor is `STOP=historical_decision_correction_template_anchor_mismatch`.
3. Replace `<APPROVED_DELTA_DESIGN_SHA256>` exactly once in R9; any remaining or extra placeholder is `STOP=historical_decision_correction_template_placeholder_mismatch`.
4. Write complete expected files first, then write named direct `.sha256` and `.length` records for each expected file. Write candidates only beneath `<bundle>/candidates/`; require `os.stat(candidate).st_dev == os.stat(target.parent).st_dev`. Otherwise stop with `STOP=historical_decision_correction_cross_filesystem_publish`.
5. After writing and before candidate validation, set each candidate's mode with `os.chmod(candidate, original_target_mode)`, flush and fsync its writable file descriptor, then require the candidate mode exactly equals the original mode. Record candidate path, direct SHA-256, length and mode in `candidate_record.json` plus `candidate_record.json.sha256`.

Use no editor, formatter, `sed -i`, `cp`, target `write_text`, target `open(..., "w")`, whole-document normalization or free-text replacement. The only target-adjacent output is an attempt-local candidate outside the repository.

### Step 1.2: Canonical positive fixture

From the exact copied baselines, generation must produce two complete expected files and candidates such that:

```bash
cmp -s "$EXECUTION_PROVENANCE_DIR/expected/current-document-index_CN.md" "$INDEX_CANDIDATE"
cmp -s "$EXECUTION_PROVENANCE_DIR/expected/roadmap.md" "$ROADMAP_CANDIDATE"
```

The validator must run as a separately invoked process and independently:

- independently locate the same unique §5.2 boundary and re-extract all twelve template blocks from the verified approved Design bytes rather than importing, reading or trusting generator template constants/records; prove all 12 ranges are replaced exactly once with those independently extracted §5.2 bytes;
- prove the R9 SHA equals `APPROVED_DELTA_DESIGN_SHA256`;
- prove bytes outside R1-R12 are unchanged relative to the copied baselines;
- reject an Alpha promotion, strategy reopen, positive/negative EV claim, win-rate falsification claim, full derivatives-stress conclusion or all-factor falsification inside owned ranges; the exact Design templates' limiting phrases such as `no-Alpha conclusion` and `no ... Alpha claim follows` remain required and allowed;
- prove candidates are regular non-symlink files, their `st_dev` equals the corresponding target parent `st_dev`, and their modes equal the original target modes from the target-index snapshot.

Any failure is `STOP=historical_decision_correction_expected_document_mismatch`.

### Step 1.3: Required negative mutation tests

Run before any target publication and record each non-zero expected exit:

1. Append one byte to a copy of any one R1-R12 candidate range. The independent validator must reject it with `STOP=historical_decision_correction_expected_document_mismatch`.
2. Pass an injected unequal `(candidate_dev, target_parent_dev)` pair to the same-filesystem predicate. It must reject with `STOP=historical_decision_correction_cross_filesystem_publish`; this is a pure helper test and must not use a target path.
3. Change a candidate copy to a mode that differs from the frozen target mode. The candidate validator must reject with `STOP=historical_decision_correction_target_mode_mismatch` without touching a target.
4. Remove or corrupt a direct required record such as `baseline/roadmap.md.sha256` and invoke `resume_preflight`. It must reject with `STOP=historical_decision_correction_resume_provenance_unavailable`.
5. Add a forbidden semantic phrase to an owned-range copy, such as `500 independent opportunities confirmed no Alpha`. The owned-range validator must reject with `STOP=historical_decision_correction_semantic_mismatch`.

The tests must operate only on bundle copies. Any mutation of a target or authority file is out of scope and a hard stop.

## Task 2: Publish In Monotonic Consumer Order

**Repository files:** the two allowed targets only. **Precondition:** Tasks 0-1 all pass, state is `staged`, every enumerated direct integrity record revalidates, and `git rev-parse HEAD` equals `<bundle>/base_sha`.

Implement a single publication primitive. It is the only target-writing path:

```python
def atomic_publish(candidate: Path, target: Path, expected: Path, original_mode: int, base_sha: str) -> None:
    require_regular_non_symlink(candidate)
    require_regular_non_symlink(target)
    require(git_head() == base_sha, 'STOP=historical_decision_correction_head_drift')
    require(os.stat(candidate).st_dev == os.stat(target.parent).st_dev,
            'STOP=historical_decision_correction_cross_filesystem_publish')
    require(stat.S_IMODE(candidate.lstat().st_mode) == original_mode,
            'STOP=historical_decision_correction_target_mode_mismatch')
    os.replace(candidate, target)
    directory_fd = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    require_exact_bytes(target, expected)
    require(stat.S_IMODE(target.lstat().st_mode) == original_mode,
            'STOP=historical_decision_correction_target_mode_mismatch')
```

The generator must flush and fsync the writable candidate descriptor after writing and after its `chmod`, before this publish primitive. `os.replace` must be called only after state, immutable authority, direct integrity record, candidate mode, `HEAD`, target-index and non-target provenance preconditions are revalidated.

Publish only in this order:

1. `docs/project-status/current-document-index_CN.md`
2. Revalidate state, immutable authorities, all explicitly enumerated direct integrity records, target modes/index entries, non-target ledger and `HEAD == base_sha`.
3. `docs/roadmap.md`

After index publication, retain expected copies and roadmap candidate, and do not regenerate anything. Do not write a target-state marker: state is determined only from exact target bytes on recovery. If the process dies before roadmap publish, it is a valid `index_published` state, not permission to roll back the index. Any failure before the second replace stops immediately.

**Forbidden recovery actions:** `git reset`, `git checkout --`, `git restore`, `git clean`, unscoped deletion, manual target editing, copying a candidate over a target, rebaselining, or overwriting the index document with old bytes.

## Task 3: Recovery And Resume Proof

**Repository files:** no new paths. **External evidence:** the original attempt bundle only.

The resume entrypoint must require `--resume-provenance-dir "$EXECUTION_PROVENANCE_DIR"`; it must not accept a fresh-start bundle path or create a replacement directory.

1. Validate state-independent direct integrity records: attempt identity, `base_sha`, immutable authority table, baseline/expected/template copies, target-index snapshot, pre-existing ledger and candidate record. A record is valid only if its named sibling SHA/length/type/mode checks pass; no central or self-hashing manifest exists.
2. Determine state solely from exact target bytes against the original bundle baseline/expected copies and original target modes. Do this before checking whether candidate paths exist.
3. Apply state-aware candidate lifecycle checks: `staged` requires both candidates present and matching `candidate_record`; `index_published` requires the consumed index candidate absent and the roadmap candidate present/matching; `both_published` requires both candidates absent. Any other lifecycle is `STOP=historical_decision_correction_publication_state_corrupt`.
4. Require `git rev-parse HEAD == <bundle>/base_sha`, target Git index entries equal to the original snapshot, and every non-target pre-existing path equal to its ledger entry.
5. In `index_published`, publish only the saved roadmap candidate via the Task 2 primitive.
6. In `both_published`, perform validation only; do not publish again.
7. In any other state, stop without writing.

**Recovery simulation:** terminate immediately after each `os.replace()` and before any subsequent bundle write. Invoke resume with the same bundle; it must infer `index_published` or `both_published` from target bytes, enforce the matching candidate lifecycle, and either publish only roadmap or validate only. Re-run every Task 4 gate from the beginning. A restart with a missing bundle must fail closed, not rebuild state.

## Task 4: Final Mechanical Verification

**Repository files:** no further changes. This Task determines only implementation completeness, never commit/deployment/runtime authority.

Run all gates after both documents are published and after any permitted attempt-local evidence remediation:

1. Recompute immutable §2 authority hashes and Git dependency. Validate each bundle baseline copy, not the published targets, against the §1 input-baseline SHA. Never compare a published target to its old baseline.
2. Require `git rev-parse HEAD == <bundle>/base_sha`; reject `STOP=historical_decision_correction_head_drift` before every final consumer.
3. Compare each actual target byte-for-byte with its original bundle expected copy and require each target's current mode equals its original snapshot mode.
4. Re-run the independently invoked R1-R12 validator, which independently re-extracts the canonical templates from verified Design bytes, and run the outside-owned-byte preservation check.
5. Compare target index entries and every non-target pre-existing ledger entry with the original snapshot; changed targets are allowed only at their exact expected worktree bytes, original modes and unstaged index state.
6. Run target-scoped `git diff --check -- docs/roadmap.md docs/project-status/current-document-index_CN.md`; do not scan unrelated pre-existing diffs or alter them to satisfy this gate.
7. Run the project safety check that proves `RISK_LIVE_TRADING_ENABLED=False` without changing configs.
8. Run the scanner independently and capture its actual process exit code, not a claimed summary:

```bash
set +e
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$(cat "$EXECUTION_PROVENANCE_DIR/base_sha")"
scanner_rc=$?
set -e
printf 'SCANNER_RC=%s\n' "$scanner_rc" | tee "$EXECUTION_PROVENANCE_DIR/scanner_rc.txt"
test "$scanner_rc" -eq 0 || { echo 'STOP=historical_decision_correction_scanner_failed' >&2; exit 1; }
```

9. Record `git status --short --untracked-files=all`, `git diff --binary`, `git diff --cached --binary` and proof that only the two allowed target paths changed in the worktree, no index entry changed, no repository candidate exists and `HEAD == base_sha`. `scanner_rc.txt` and review/audit handoff notes are post-publication validation observations, not resume-state artifacts: every later consumer reruns or independently verifies them rather than trusting a bundle hash record.

Any unexpected path, staged entry, authority change, semantic mismatch or scanner non-zero result is a stop. Do not use a passing scanner as a substitute for exact document equality.

## Task 5: Review And Completion Routing

1. Run `requesting-code-review` on the exact two-target diff plus the external generator/provenance evidence. The handoff must include `base_sha`, and reviewer start/end must require `HEAD == base_sha`. The reviewer checks scope, R1-R12 equality, independent template extraction, state/recovery, mode/HEAD preservation and no permission elevation.
2. A code-review finding first routes through `receiving-code-review` for objective verification. In `both_published`, a finding requiring target/source/scope mutation has no allowed state transition: classify it as `BLOCKED_IMPLEMENTATION_DEFECT`, `BLOCKED_SCOPE_DRIFT` or `BLOCKED_SPEC_DRIFT`, stop, and obtain the required new approved route. A finding limited to attempt-local evidence may be corrected only if it preserves state and then requires all applicable Task 4 gates again.
3. Request a fresh independent read-only Completion Audit only after code review has no OPEN finding. An OPEN implementation finding from that Completion Audit routes through `remediate-completion-audit`, subject to the same Rule-12 classification and no unauthorized target mutation.
4. `COMPLETE` means only this docs-only implementation meets the Plan. It does not authorize commit, push, network, replay, SSH, deployment, research reopening, strategy execution, paper trading or live trading.

## Final Scope Checklist

- [ ] All authority and approved bytes match before any write.
- [ ] Fresh start captured user-owned worktree/index provenance without requiring cleanliness.
- [ ] Only exact R1-R12 templates produced complete expected documents.
- [ ] Negative one-byte, forbidden-semantic, cross-device and missing-provenance tests fail closed.
- [ ] Publication followed `document-index -> roadmap` using only durable same-filesystem `os.replace`.
- [ ] Resume requires the original valid bundle and cannot rebaseline or rollback.
- [ ] Final target bytes equal expected copies; bytes outside the mutable set and non-target provenance remain unchanged.
- [ ] `git diff --check`, safety check and scanner actual `RC=0` pass.
- [ ] Independent code review and fresh Completion Audit are requested before any separate integration decision.
