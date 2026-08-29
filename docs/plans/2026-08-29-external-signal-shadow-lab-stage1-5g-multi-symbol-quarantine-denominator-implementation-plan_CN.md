# Stage 1.5G Multi-Symbol Quarantine Denominator Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. `src/`、`configs/`、`scripts/` 或 `tests/` 的任何修改，必须等待本 Plan 审核批准且用户明确授权。

**Goal:** 修复 Stage 1.5G 多标的 quarantine 将单标的 `720` 作为聚合分母的问题。新产生的 Stage 1.5G review 使用 v2：每个 formal completed symbol 保持既有 gate，聚合指标仅作正确算术审计；Stage 1.5H 只接受单标的 quarantined bundle，拒绝所有 multi-symbol 与 clean-v2 输入。

**Architecture:** 复用现有 Stage 1.5G loader、review builder、CLI 和 Stage 1.5H loader。Stage 1.5G 在同一 reducer 内按唯一 formal evidence set `S` 分组，生成每标的 authoritative metrics 与不可放宽的 overall reduction；CLI 只在 fresh output root 写入 closed v2 quarantine bundle 和 manifest。Stage 1.5H 不重算数据，只做 schema、cardinality、closed-bundle path/hash/provenance 的 fail-closed 验证后才进入既有单标的路径。

**Tech Stack:** Python 3 standard library (`dataclasses`, `hashlib`, `json`, `math`, `pathlib`)、pytest、ruff；不新增依赖、服务、数据库、网络请求、VPS 操作或并发模型。

---

## Plan Status

- **状态:** `draft_for_review`
- **Review Mode:** `closure_confirmation`
- **Implementation authorization:** `false`
- **Deployment authorization:** `false`
- **Runtime action:** 禁止。此 Plan 不得修改 Stage 1.5D/F 运行进程、VPS 数据、历史 v1 review 或 `20260829T024637Z_local`。

## Frozen Authority

| Authority | SHA-256 |
| --- | --- |
| Approved Stage 1.5G multi-symbol denominator Design Delta | `3528d4b5f90ee8b7bd142773b1c35a1a51b2ea09242224eaed2ab10df69c5c8b` |
| Parent Stage 1.5G raw-snapshot quarantine Design | `6478936ab3501fba6c79ffcb15383748c6ef561ac71465b856805a919edb7d30` |
| Stage 1.5H runtime governance review | `8058bf63eda822b6e93c65dc41afb29230e47551f0aa7e4a85bf53c19d51a3e8` |
| Planning baseline commit | `efe364eda28c3321b7c246876b03f88c01e951bf` |
| Frozen source evidence manifest bytes (`SHA256SUMS`) | `46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918` |

Implementation must stop if any Design/governance-review bytes or its SHA differ from the table. The exact approved Plan SHA is intentionally not set in this draft; after Plan approval, record it outside the repository as `APPROVED_PLAN_SHA` and re-check it before Task 1.

Known pre-existing worktree content that this Plan must neither edit nor revert:

- `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`
- `docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-design-delta_CN.md`

Task 0 records each path's Git status, file type and SHA-256 (or symlink target) outside the repository. Task 5 and the completion audit must prove the recorded paths are byte-identical and retain their original types. The Plan itself is governed separately by `APPROVED_PLAN_SHA`.

## Allowed Scope

**Allowed implementation paths:**

- `configs/base.py` only for `EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION: 1 -> 2`; all threshold values remain byte-equivalent.
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- `scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py`
- `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`

**Allowed verification paths:**

- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py`
- `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`

**Allowed generated artifacts, never committed:**

- pytest temporary roots.
- Fresh local re-review root `data/external_signal_shadow/stage1_5g/reviews/20260829T024637Z_local_v2/**`.
- External execution provenance record containing command output and hashes.

**Forbidden:**

- any Stage 1.5D/F code, configuration, output root, live collector or VPS mutation;
- threshold or decision-taxonomy change; source evidence rewrite; migration/overwrite/delete of historical v1 artifacts;
- any Stage 1.5H multi-symbol or clean-input report path, proxy-model change, consumer write-back, or report execution on the new multi-symbol bundle;
- Stage 1.6 code/docs, execution feasibility, alpha/PIT/replay conclusion, paper/live trading or execution enablement;
- new dependency, service, database, queue, generic framework, asynchronous worker, full-repository formatter or destructive cleanup.

## Invariant and Proof Coverage

| Design invariant | Plan evidence |
| --- | --- |
| INV-01 evidence-set authority | Tasks 1--2 derive `S` only from integrity result and exclude nonformal rows from ratios. |
| INV-02 per-symbol authority | Tasks 1--2 filter state/snapshot/event/request rows by the same formal identity and test coverage, gap, request health, quarantine and depth quality independently. |
| INV-03 aggregate cannot promote a failed symbol | Task 2 aggregate-camouflage negative fixtures. |
| INV-04 same-set arithmetic | Tasks 1--2 exact `N * 720`, nonpositive denominator and ratio checks. |
| INV-05 ratio bounds | Task 2 NaN/infinity/out-of-range fail-closed tests; no clamp. |
| INV-06 single-symbol preservation | Task 2 v1-equivalent arithmetic fixture for v2 `N=1`. |
| INV-07 artifact closure | Task 3 canonical projection, formal-ID hash golden vector, four-hash manifest and cross-review mix test. |
| INV-08 consumer safety | Task 4 v1/v2 cardinality and clean-v2 reject matrix. |
| INV-09 evidence immutability | Tasks 0 and 6 hash source, preserve v1 root, require a fresh v2 root. |
| INV-10 permissions false | Tasks 2, 4 and 6 assert every safety flag remains false. |

```text
approved Delta/parent/governance bytes + approved Plan bytes + clean protected baseline
    -> unique implementation authority
source manifest entries + preserved v1 root
    -> immutable offline evidence
formal completed evidence set S + same-ID state/snapshot/event/request rows
    -> per-symbol coverage/request-health/quarantine/depth-quality gates
    -> aggregate audit with N * per-symbol expected denominator
    -> v2 summary / JSONL / manifest closed bundle
    -> Stage 1.5H single-symbol quarantined-only rejection gate
    -> corrected local Stage 1.5G evidence, with no execution authority
```

## Task 0: Authority, Baseline and Historical-Evidence Gate

**Files:** no repository file changes.

**Step 1: Freeze approved authority and protected baseline.**

```bash
set -euo pipefail
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
DESIGN=docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-design-delta_CN.md
PARENT_DESIGN=docs/designs/2026-07-11-external-signal-shadow-lab-stage1-5g-raw-snapshot-quarantine-design_CN.md
GOVERNANCE_REVIEW=docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md
PLAN=docs/plans/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-implementation-plan_CN.md
git merge-base --is-ancestor efe364eda28c3321b7c246876b03f88c01e951bf HEAD
test -z "$(git diff --name-only efe364eda28c3321b7c246876b03f88c01e951bf..HEAD -- configs src scripts tests)" || {
  echo 'STOP: protected implementation path drift after planning baseline' >&2; exit 1;
}
test -z "$(git diff --name-only -- configs src scripts tests)" || {
  echo 'STOP: unstaged protected implementation path drift' >&2; exit 1;
}
test -z "$(git diff --cached --name-only -- configs src scripts tests)" || {
  echo 'STOP: staged protected implementation path drift' >&2; exit 1;
}
test -z "$(git ls-files --others --exclude-standard -- configs src scripts tests)" || {
  echo 'STOP: untracked protected implementation path' >&2; exit 1;
}
test "$(shasum -a 256 "$DESIGN" | awk '{print $1}')" = 3528d4b5f90ee8b7bd142773b1c35a1a51b2ea09242224eaed2ab10df69c5c8b
test "$(shasum -a 256 "$PARENT_DESIGN" | awk '{print $1}')" = 6478936ab3501fba6c79ffcb15383748c6ef561ac71465b856805a919edb7d30
test "$(shasum -a 256 "$GOVERNANCE_REVIEW" | awk '{print $1}')" = 8058bf63eda822b6e93c65dc41afb29230e47551f0aa7e4a85bf53c19d51a3e8
printf 'REVIEW_CANDIDATE_PLAN_SHA=%s\n' "$(shasum -a 256 "$PLAN" | awk '{print $1}')"
git status --short --untracked-files=all
```

Expected: baseline, Delta, parent Design and runtime governance SHA match; protected paths have neither committed/staged/unstaged drift nor untracked files. Record the printed candidate Plan SHA and complete worktree status outside the repository. Do not treat the candidate hash as implementation authority.

**Step 2: Freeze exact pre-existing worktree provenance outside the repository.**

Create an external provenance directory and store two distinct evidence classes:

1. `BASELINE_WORKTREE_SNAPSHOT`: raw `git status --porcelain=v1 -z`, `git diff`, and `git diff --cached`. This is retained only as a before-implementation provenance snapshot; it is not required to equal post-implementation worktree output.
2. `PREEXISTING_PATH_RECORDS`: for every dirty or untracked path that exists at Task 0, other than this Plan, record its repository-relative path, original porcelain status, `lstat` file type, SHA-256 for a regular file, or symlink target for a symlink. The records must include the known modified Stage 1.5F review document. The approved Design is checked by the Frozen Authority SHA above and is also included when dirty/untracked. Copy exact baseline `configs/base.py` bytes to this external directory and store `ast.dump(ast.parse(...), include_attributes=False)` beside it.

At Task 5 and Completion Gate, regenerate and require exact equality only for `PREEXISTING_PATH_RECORDS`. A path deletion, restoration, content change, type change, new pre-existing-path ambiguity, or symlink substitution is STOP; do not clean, stage, revert, or normalize those paths. New implementation changes are validated separately by the Task 5 allowed-scope/changed-path gate.

**Step 3: Require explicit approval rebind before implementation.**

The executor must supply externally recorded `APPROVED_PLAN_SHA`, assert it equals the current Plan hash, then repeat all three frozen document SHA checks. Any mismatch is STOP and requires review; do not modify code/tests to match changed authority bytes.

**Step 4: Verify every hash-frozen source-evidence byte and freeze the v1 root.**

```bash
set -euo pipefail
SOURCE=data/external_signal_shadow/local_evidence/20260829T024637Z_stage1_5f
V1=data/external_signal_shadow/stage1_5g/reviews/20260829T024637Z_local
test "$(shasum -a 256 "$SOURCE/SHA256SUMS" | awk '{print $1}')" = 46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918
test -d "$SOURCE" && test -d "$V1"
PYTHONPATH=src:. .venv/bin/python - "$SOURCE" "$V1" <<'PY'
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

source, v1 = (Path(arg).resolve() for arg in sys.argv[1:])
manifest = source / "SHA256SUMS"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def entry(path: Path) -> dict:
    st = path.lstat()
    if stat.S_ISREG(st.st_mode):
        return {"type": "regular", "sha256": sha256(path)}
    if stat.S_ISLNK(st.st_mode):
        return {"type": "symlink", "target": os.readlink(path)}
    raise AssertionError(f"STOP: unsupported evidence file type: {path}")

declared = {}
for line in manifest.read_text(encoding="utf-8").splitlines():
    digest, separator, raw_path = line.partition("  ")
    assert separator and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), line
    path = Path(raw_path).resolve()
    try:
        path.relative_to(source)
    except ValueError as exc:
        raise AssertionError(f"STOP: manifest path escapes source root: {path}") from exc
    assert path not in declared, f"STOP: duplicate manifest entry: {path}"
    declared[path] = digest

# The retained manifest intentionally has an e3b0 self-entry. Its own frozen
# bytes are verified by the shell SHA above; validate every non-self entry.
assert manifest in declared, "STOP: manifest self-entry missing"
for path, digest in declared.items():
    if path != manifest:
        assert path.is_file() and not path.is_symlink(), f"STOP: missing/non-regular manifest entry: {path}"
        assert sha256(path) == digest, f"STOP: manifest digest mismatch: {path}"

actual = {path.resolve() for path in source.rglob("*") if path.is_file() and not path.is_symlink()}
assert actual == set(declared), "STOP: source file set differs from frozen manifest"
assert not any(path.is_symlink() for path in source.rglob("*")), "STOP: source evidence symlink is forbidden"

v1_entries = {str(path.relative_to(v1)): entry(path) for path in sorted(v1.rglob("*")) if path.is_file() or path.is_symlink()}
assert v1_entries, "STOP: preserved v1 root is empty"
print(json.dumps({"v1_root": str(v1), "v1_entries": v1_entries}, sort_keys=True, ensure_ascii=False))
PY
```

Persist the exact verifier source and printed v1 inventory outside the repository. Task 6 and Completion Gate must execute that same verifier and require byte-for-byte inventory equality. The manifest self-entry is not verified against its stale `e3b0...` declaration because that would be recursive; its exact current bytes are independently frozen by the table SHA, while every declared evidence entry and the complete source file set are verified.

**Step 5: Enumerate historical unsafe Stage 1.5H descendants deterministically.**

Search only `data/external_signal_shadow/stage1_5h/reports/**/stage1_5h_static_execution_proxy_report_summary.json`, sorted by repository-relative path. Emit one deterministic JSON row per file with path, SHA-256, report decision, persisted upstream Stage 1.5G path/schema/cardinality, and classification. If a report does not persist sufficient upstream provenance, classify it `unattributable_legacy_1_5h_evidence`, `non_authoritative=true`, `reusable_as_stage1_5h_evidence=false`; never infer or fabricate a source path. If persisted provenance proves `schema_version=1` and `N>1`, classify it `preserved_defect_evidence` with the same non-authoritative flags. Count both classifications as unsafe and assert `unsafe_stage1_5h_descendant_count == 0` for this baseline. Persist the sorted JSON rows and count outside the repository; Task 5, Task 6 and Completion Gate must reproduce them exactly. Never delete, alter or reclassify a historical artifact in place.

**Step 6: Establish pre-change regression evidence.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
```

Expected: all baseline tests pass before test edits. No code/test/runtime changes in this task.

## Task 1: Define the v2 Reducer Contract with RED Fixtures

**Files:**

- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py`

**Step 1: Add focused failing tests before production edits.**

Add fixtures/assertions for:

1. v2 config only: `EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION == 2`; every existing Stage 1.5G threshold has the old value.
2. Single-symbol quarantined input: `N=1`, `per_symbol_expected_snapshot_count=720`, total expected `720`, and v2 per-symbol/aggregate arithmetic equals v1 arithmetic without retaining ambiguous v1 aggregate keys under `quarantine`.
3. Five-symbol golden arithmetic: `N=5`, expected `3600`, observed `3546`, valid `3543`, invalid `3`, availability `3543/3600`, unavailable `3/3600`, invalid-observed `3/3546`, each finite and inside `[0,1]`.
4. Aggregate camouflage: four symbols with `720` valid rows and one with `650`; aggregate availability may exceed threshold but the reducer returns `stage1_5g_depth_evidence_invalid` and includes `per_symbol_quarantine_gate_failed`.
5. Same aggregate counts with invalid rows concentrated in one symbol; decision follows that symbol's midrun/consecutive/latency gate, not aggregate counts.
6. One symbol whose quarantined depth-quality p95/top-depth/healthy-window gate fails while the aggregate-looking data is healthy; overall result is invalid.
7. A nonformal snapshot is counted only by `ignored_nonformal_snapshot_row_count`; it changes neither Layer A nor Layer B numerator/denominator. A structural raw-integrity fault in that row remains a global blocker.
8. `N=0`, missing/nonpositive per-symbol expected, nonpositive total expected, `NaN`, infinity and every ratio `<0` or `>1` fail closed with exact `quarantine_ratio_out_of_range` or applicable denominator blocker. Tests must explicitly reject clamping.
9. One symbol has insufficient snapshot coverage while all other symbols pass; aggregate evidence may look sufficient but the overall decision is invalid.
10. One symbol has `max_gap_ms` beyond the existing per-symbol limit while all other symbols pass; the overall decision is invalid.
11. One symbol's depth request-success rate is below the existing per-symbol threshold while global success remains above threshold; the fixture proves other symbols' request rows are excluded from that symbol's rate.

**Step 2: Run RED.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py
```

Expected: new tests fail for the current aggregate reducer; existing unrelated tests remain green.

## Task 2: Implement Per-Symbol Authority and Aggregate Audit

**Files:**

- Modify: `configs/base.py`
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Modify: the four Task 1 test files only as needed to complete fixtures.

**Step 1: Implement the smallest shared reducer change.**

1. Change only `EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION` from `1` to `2`; do not change any thresholds.
2. Derive `S = sorted(set(integrity_result.formal_completed_event_symbol_ids))` once in `build_stage1_5g_review_summary`. It is the only authority for eligible snapshots.
3. Extend the existing `RawSnapshotQuarantineResult`/quarantine computation rather than introducing a second reducer. For each `s in S`, construct `states_s`, `snapshots_s`, `accepted_events_s`, and `request_manifest_rows_s` only from the authoritative `event_symbol_id == s`. Request rows missing an authoritative identity remain structural blockers; they are never admitted to another symbol's rate.
4. Correct the shared root cause in `compute_depth_request_health`: accept the existing formal identity filter, apply it before calculating totals/rates, and have `compute_coverage_metrics` pass the same filter. Layer A calls `compute_coverage_metrics(..., event_symbol_ids={s}, request_manifest_rows=request_manifest_rows_s)`; it must never derive a symbol rate from full-root request rows.
5. For each `s`, run existing coverage/gap/request-health checks, existing quarantine checks, and `compute_depth_quality_metrics` only on that symbol's data. Retain exact parent threshold comparisons and blockers.
6. Build `per_symbol_quarantine_metrics[s]` with the exact Decision 2 metrics, per-symbol coverage/request-health results, `quarantined_depth_quality`, and sorted exact blockers. Any nonempty per-symbol blocker appends exactly `per_symbol_quarantine_gate_failed` to the overall result; aggregate metrics may not erase it.
7. Calculate Layer B only from eligible rows and `total_expected_snapshot_count = len(S) * coverage_metrics.expected_snapshot_count`. Validate denominators and `math.isfinite`/`0.0 <= ratio <= 1.0` before constructing output. Raise the frozen invalid blocker; never clamp or fall back to observed rows.
8. Retain full-root global request-health and raw-integrity checks as additional blockers only. They cannot prove an individual symbol passes. Keep all safety booleans false in every decision path.
9. Serialize v2 `quarantine` exactly as Design Decision 4: include per-symbol fields and `aggregate_` fields; omit the four ambiguous v1 keys and unprefixed aggregate ratio keys. `coverage_metrics.expected_snapshot_count` remains per-symbol.

**Step 2: Run the focused GREEN suite.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py
```

Expected: every parent per-symbol contract remains enforced; all new reducer tests pass.

## Task 3: Write a Closed v2 Artifact Bundle from a Fresh Root

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Modify: `scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py`
- Modify: `tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py`

**Step 1: Add RED bundle tests.**

Require a v2 quarantine bundle to prove:

1. summary embedded `quarantine` and standalone `stage1_5g_quarantine_summary.json` are canonically byte-equivalent projections;
2. review id is SHA-256 over exact canonical JSON `{schema_version: 2, source_evidence_manifest_sha256, formal_completed_event_symbol_ids: sorted(S)}`;
3. `formal_completed_event_symbol_ids_sha256` is exactly `SHA-256(UTF-8(safety.canonical_json_dumps(sorted(S))))`. Reuse that existing canonical helper; add no canonicalizer. Require the independent literal golden vector `sorted(S) == ["article-a", "article-b"]`, canonical bytes `b'["article-a","article-b"]'`, and digest `6db09e3b17ebe4d98e12c691c0e90a43b6444aefd7577e0d91863dbf8dfcdee3` without deriving the expected digest from the production helper.
4. main summary and standalone summary carry identical review id, source manifest hash and formal-id hash;
5. `stage1_5g_review_manifest.json` has relative exact paths and SHA-256 for the main summary, standalone summary and both existing JSONL outputs;
6. any mixed path, altered JSONL byte, altered summary byte, identity mismatch or missing manifest yields the frozen future-loader blocker `stage1_5g_quarantine_v2_artifact_mismatch`;
7. artifact matrix: structural/denominator failure writes only main invalid summary; clean writes only main summary; quarantined pass writes all four artifacts plus manifest; invalid quarantine analysis with invalid rows writes a diagnostic closed bundle but remains consumer-ineligible;
8. an existing output root is rejected before any output write.

**Step 2: Run RED.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
```

**Step 3: Move writing to the CLI finalization boundary.**

1. Keep the builder pure: it returns summary and exact in-memory quarantine projection/data rows; it must not write an artifact before final decision and summary fields are complete.
2. In the existing Stage 1.5G CLI, reject pre-existing `--output-root`, create only a fresh root, then deterministically write JSONL, standalone quarantine projection, final main summary, markdown and manifest. Compute each SHA from the exact stored UTF-8 bytes. The manifest is last so it cannot form a hash cycle.
3. Reuse existing JSON serialization conventions consistently. Do not add a second generic serialization framework. Canonical comparison uses sorted keys, UTF-8 and compact separators; human-readable on-disk summary formatting remains allowed because the manifest hashes the exact stored bytes.
4. Before assigning the v2 review identity, verify the frozen `SHA256SUMS` bytes, every non-self manifest entry and exact source file-set membership using the Task 0 verifier. The manifest's retained self-entry is deliberately excluded from entry digest comparison only because its exact manifest bytes are independently frozen. Missing/unreadable manifest, a mismatched entry, extra/missing source file, unsupported file type or symlink produces `source_evidence_manifest_missing_or_unreadable` and follows the pre-quarantine invalid write matrix.
5. Keep JSONL row schemas unchanged. No output may be written inside the Stage 1.5F source root or the preserved v1 review root.

**Step 4: Run GREEN.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py
```

## Task 4: Make Stage 1.5H a Strict Single-Symbol Consumer

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`

**Step 1: Add RED compatibility fixtures.**

Test the full frozen matrix:

1. v1 cardinality is exactly `formal_announcement_and_launch_count`; v1 `N=1` quarantined artifact set stays accepted through the existing legacy path.
2. v1 `N>1` rejects with `stage1_5g_v1_multi_symbol_denominator_unsafe`.
3. v2 cardinality is exactly `formal_completed_symbol_count`, requires positive `N == len(eligible_event_symbol_ids)`, and never derives `N` from JSONL rows.
4. v2 `N=1` quarantined pass plus complete valid manifest is accepted through the existing path.
5. v2 `N=1` clean pass remains rejected/no-path. Do not create a clean report fixture or loader interface.
6. v2 `N>1` rejects with `stage1_5h_multi_symbol_input_not_authorized`.
7. Unknown version rejects with `unsupported_stage1_5g_schema_version`.
8. For v2, missing/malformed manifest, non-root-relative path, supplied path mismatch, review/source/formal-id mismatch, non-equal embedded projection, or any of four hash mismatches rejects with `stage1_5g_quarantine_v2_artifact_mismatch`.
9. A semantically equivalent legacy v1 `N=1` fixture and v2 `N=1` fixture produce identical accepted quarantine inputs and static-proxy values. The v2 fixture proves valid count, invalid count, availability/unavailability, phase/reason diagnostics, consecutive-invalid values, first-valid latency and quarantined depth quality all originate from its sole `per_symbol_quarantine_metrics[sole_id]`, never Layer B aggregate fields.
10. Stage 1.5H remains read-only and all safety flags remain false on acceptance and rejection.

**Step 2: Run RED.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
```

**Step 3: Implement validation only at the existing loader boundary.**

1. Dispatch cardinality from the supplied Stage 1.5G main summary only: v1 uses `formal_announcement_and_launch_count`; v2 uses `formal_completed_symbol_count` and requires it exactly equals `len(eligible_event_symbol_ids)`. Do not infer cardinality from JSONL rows.
2. Preserve the v1 `N=1` legacy validation exactly. Add its multi-symbol reject before static proxy/report construction.
3. For v2, resolve the manifest only from the main summary's parent root. Recompute `formal_completed_event_symbol_ids_sha256` from `safety.canonical_json_dumps(sorted(eligible_event_symbol_ids))`, then verify all closed-bundle values and exact four supplied paths/hashes before calling existing source-of-truth and proxy logic.
4. For an already validated v2 `N=1` quarantined bundle only, create a private in-memory compatibility view. Set `sole_id = eligible_event_symbol_ids[0]`, take every old single-market field from `per_symbol_quarantine_metrics[sole_id]`, and supply that view to existing consistency, row-count, clean-missing-reason, static-proxy and report rendering logic. Map valid/invalid count, availability/unavailability, phase/reason diagnostics, consecutive-invalid values, first-valid latency, and quarantined depth quality from that sole entry. Never use Layer B aggregate metrics as a v1 substitute, never write the view back to Stage 1.5G, and do not recalculate any gate or alter the proxy model.
5. Reject clean v2 explicitly as outside this Delta. Do not add new input arguments, report fields, proxy calculations or write-back behavior.
6. Deduplicate blockers with existing `_append_once`; no consumer branch may repair, recalculate or mutate a source artifact.

**Step 4: Run GREEN.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
```

## Task 5: Full Regression and Scope Audit

**Files:** no production file changes beyond Tasks 2--4.

**Step 1: Run the full affected test matrix and static checks.**

```bash
set -euo pipefail
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
.venv/bin/ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from configs import base
assert base.EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION == 2
assert base.RISK_LIVE_TRADING_ENABLED is False
PY
```

**Step 2: Prove `configs/base.py` has the one authorized AST change.**

Using Task 0's external baseline copy, run a Python verifier that:

1. parses both files with `ast.parse` and requires baseline `EXTERNAL_SIGNAL_STAGE1_5G_SCHEMA_VERSION = 1` and current value `= 2`;
2. removes only that top-level assignment from each AST and requires `ast.dump(..., include_attributes=False)` equality;
3. requires every top-level assignment whose name starts `EXTERNAL_SIGNAL_STAGE1_5G_`, `EXTERNAL_SIGNAL_STAGE1_5H_`, or `RISK_` to have identical AST value before/after, except the single authorized schema assignment;
4. rejects a missing, duplicate or non-literal schema assignment.

The verifier must read the external baseline bytes, not a test fixture or mutable expected value. A source comment/format-only difference is not a configuration semantic change; every other AST difference is STOP.

**Step 3: Rebind all non-code provenance.**

Repeat Task 0 Step 1's three document SHA checks and approved-Plan SHA binding. Retain a new full-worktree snapshot for audit comparison, but do not compare it to `BASELINE_WORKTREE_SNAPSHOT` for equality. Regenerate only `PREEXISTING_PATH_RECORDS` and require exact equality with Task 0. Repeat Task 0 Step 4's full source-manifest/v1-root verifier, and repeat Task 0 Step 5's exact Stage 1.5H report-root enumeration. Require the v1 inventory, source evidence set and `unsafe_stage1_5h_descendant_count` to remain unchanged. Do not accept a changed hash merely because a file is ignored by Git.

**Step 4: Enforce the path allowlist.**

```bash
set -euo pipefail
git diff --name-only -- \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_config.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
```

Compare the union of committed changes since `efe364...951bf`, unstaged changes, staged changes and untracked files against the allowed implementation/verification paths plus this Plan. Separately compare all pre-existing dirty/untracked paths to Task 0's exact record. Any Stage 1.5D/F, Stage 1.6, historical artifact, VPS/runbook, threshold value, unrecorded dirty path or out-of-scope change is STOP. This is a scope test, not permission to edit the pre-existing files listed in Frozen Authority.

## Task 6: Fresh Local v2 Re-Review and Evidence Check

**Files:** generated local output only; never commit.

**Preconditions:** Tasks 0--5 green, approved Plan SHA bound, Task 0 Step 4's complete source-manifest/v1-root verifier passes again, Task 0 Step 5's descendant inventory remains zero, and the v2 output root is absent. No VPS command, SSH, live process restart or Stage 1.5H report invocation is permitted.

**Step 1: Run fresh offline review.**

```bash
set -euo pipefail
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
SOURCE=data/external_signal_shadow/local_evidence/20260829T024637Z_stage1_5f
OUT=data/external_signal_shadow/stage1_5g/reviews/20260829T024637Z_local_v2
test "$(shasum -a 256 "$SOURCE/SHA256SUMS" | awk '{print $1}')" = 46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918
# Re-run the exact Task 0 Step 4 verifier here: manifest bytes, every non-self
# declared source entry, complete source file set, no symlink, and v1 root inventory.
test ! -e "$OUT" || { echo "STOP: fresh v2 output root already exists: $OUT" >&2; exit 1; }
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  --stage1-5f-output-root "$SOURCE" \
  --output-root "$OUT"
```

**Step 2: Verify arithmetic, artifact closure and authority.**

```bash
PYTHONPATH=src:. .venv/bin/python - "$OUT" <<'PY'
import hashlib
import json
import math
import sys
from pathlib import Path

from src.research.external_signal_shadow.safety import canonical_json_dumps

root = Path(sys.argv[1])
summary_path = root / "stage1_5g_live_depth_evidence_review_summary.json"
quarantine_path = root / "stage1_5g_quarantine_summary.json"
manifest_path = root / "stage1_5g_review_manifest.json"
summary = json.loads(summary_path.read_text(encoding="utf-8"))
quarantine = json.loads(quarantine_path.read_text(encoding="utf-8"))
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert summary["schema_version"] == 2
assert summary["quarantine"] == quarantine
ids = sorted(quarantine["eligible_event_symbol_ids"])
assert summary["source_evidence_manifest_sha256"] == "46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918"
assert summary["formal_completed_event_symbol_ids_sha256"] == hashlib.sha256(
    canonical_json_dumps(ids).encode("utf-8")
).hexdigest()
assert summary["stage1_5g_review_id"] == quarantine["stage1_5g_review_id"] == manifest["stage1_5g_review_id"]
assert quarantine["formal_completed_symbol_count"] == 5
assert quarantine["total_expected_snapshot_count"] == 3600
assert quarantine["aggregate_observed_snapshot_count"] == 3546
assert quarantine["aggregate_valid_snapshot_count_after_quarantine"] == 3543
assert quarantine["aggregate_invalid_book_row_count"] == 3
assert quarantine["aggregate_book_availability_ratio"] == 3543 / 3600
assert quarantine["aggregate_book_unavailable_ratio"] == 3 / 3600
assert quarantine["aggregate_invalid_book_ratio"] == 3 / 3546
assert len(quarantine["per_symbol_quarantine_metrics"]) == 5
for key in ("expected_snapshot_count", "observed_snapshot_count", "valid_snapshot_count_after_quarantine", "invalid_book_row_count"):
    assert key not in quarantine, key
for symbol_id, metrics in quarantine["per_symbol_quarantine_metrics"].items():
    assert symbol_id in ids
    assert "coverage_metrics" in metrics and "request_health" in metrics
    assert "quarantined_depth_quality" in metrics and "blockers" in metrics
for key in ("aggregate_book_availability_ratio", "aggregate_book_unavailable_ratio", "aggregate_invalid_book_ratio"):
    assert math.isfinite(quarantine[key]) and 0.0 <= quarantine[key] <= 1.0
for name, meta in manifest["artifacts"].items():
    path = root / meta["relative_path"]
    assert path.is_file(), name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"], name
for key in ("execution_feasibility_claim_allowed", "trade_signal_allowed", "paper_trading_allowed", "live_trading_allowed", "execution_engine_allowed", "alpha_interpretation_allowed"):
    assert summary[key] is False, key
print({"decision": summary["decision"], "review_id": summary["stage1_5g_review_id"], "manifest": str(manifest_path)})
PY
```

Expected: only corrected Stage 1.5G evidence validity can be concluded. Whether the output is internally valid or invalid depends on the preserved per-symbol gates; either result must preserve safety flags. Never run Stage 1.5H on this `N=5` output.

## Completion Gate

Before claiming implementation complete:

1. run `audit-plan-completion` against this exact approved Plan and preserve its report;
2. repeat Task 5's document/Plan SHA rebind, `configs/base.py` schema-only AST proof, protected/untracked scope audit, pre-existing-worktree provenance comparison, source-manifest/v1-root verifier, and Stage 1.5H descendant inventory;
3. compare the final diff and runtime evidence against every allowed/forbidden path and invariant above;
4. record the local v2 output hash set and retain v1 `20260829T024637Z_local` unchanged;
5. require a separate user decision before any commit, VPS sync, deployment or subsequent Stage 1.5H design work.

This Plan itself performs no commit and grants no code/deployment authority until it is independently approved.
