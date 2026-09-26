# Stage 1.6F-W2-0 Exploratory Terminal-Basis Diagnostic Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: use `executing-plans` task-by-task only after this exact Plan receives user implementation approval.

**Goal:** Build a local, read-only W2-0 diagnostic that consumes the exact verified W2 candidate root and emits an immutable exploratory terminal-basis bundle without any network, replay, execution, or Alpha-promotion authority.

**Architecture:** The CLI first admits exact authorities and calls `load_verified_w2_evidence(...)`. The new W2-0 source then performs a read-only verified-row materialization: it reuses the returned manifest bindings and the existing production `validate_w2_zip_and_csv(...)` helper to obtain validated `parsed_rows`, before the reducer computes the two Design-defined endpoint basis descriptors. The reducer preserves every contract/parent denominator row including incomplete states. A separate minimal storage module performs create-exclusive manifest-last publication and strict read-back. The CLI never imports collector or transport code.

**Tech Stack:** Python 3 standard library (`dataclasses`, `hashlib`, `json`, `math`, `os`, `pathlib`, `statistics`); existing W2 strict reader; pytest; ruff; `.agent/tools/anti_shortcut_scan.py`; Graphify.

---

## Authority Packet

| Authority | Exact path | SHA-256 |
| --- | --- | --- |
| Approved W2-0 Design | `docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-design_CN.md` | `58f4cf8638b05a1c268578ace0ed8d4c6b8b794daa4d94107e2af349d22862c4` |
| W2 collection Design | `docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md` | `11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303` |
| W2 collection Plan | `docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md` | `183689a6b786ccd3dce9f74f5d1fc2e9ccc1741d80f243f5724dd3b7de149229` |
| W2 network authorization | `configs/authorizations/network_auth_w2_candidate_run_20260925_001.json` | `0189fd4a922c87811e25793b62d12d6ba76ad92e60a95236a3fe54f024fa5dbf` |
| W2 candidate manifest | `data/external_signal_shadow/stage1_6f/w2_evidence_candidates/w2_candidate_run_20260925_001/candidate_manifest.json` | `1bd45df8d27e85b40d30500148575780740c6d089b5700e43c1cbfc22a4a0cea` |
| External completion audit | `/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_completion_audit_review.md` | `1c3051315711b5fb0f80086d7f7dab3639a8ba438a74ab4ec4558ce3180d76f2` |
| Historical blind receipt | `/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_preanalysis_blind_receipt.json` | `5f6f1087888e73a0304f91b07d3a8b6ebaf7ca9b7701e4ab4de714dc158e0e25` |

The executor must supply the separately approved W2-0 Plan path/SHA at Task 0. It is not known until this Plan is reviewed and approved; it must never be guessed or substituted.

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py`
- `src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_storage.py`
- `scripts/external_signal_shadow/run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/stage1_6f_w2_0_test_support.py`
- `tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py`
- `tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_storage.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py`

Allowed documentation paths:
- `docs/plans/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-implementation-plan_CN.md` (this Plan only; no implementation task may edit it)

Allowed generated/runtime artifacts:
- `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/<run_id>/**` (only after separate runtime authorization; generated only, never committed)
- `${TMPDIR:-/tmp}/stage1_6f_w2_0_*` (test mirrors and execution baselines only; never committed)

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py`
  - compatibility evidence: existing W2 strict-reader tests plus W2-0 canonical integration test call `load_verified_w2_evidence(...)` without modifying the source.
- `scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py`
  - compatibility evidence: existing collector CLI tests remain green; W2-0 CLI must not import it.
- `configs/authorizations/network_auth_w2_candidate_run_20260925_001.json`
  - compatibility evidence: Task 0 and W2-0 admission recompute its SHA and its 13-field false vector remains validated by the existing strict reader.
- `data/external_signal_shadow/stage1_6f/w2_evidence_candidates/w2_candidate_run_20260925_001/**`
  - compatibility evidence: canonical fixture is link-or-copy only; tests must hash-check source bytes before and after mutation cases.
- W1/REEF source, storage, CLI, tests, Design/Plan, external audit, and receipt
  - compatibility evidence: no W2-0 import may target W1/REEF or collector modules; scope proof confirms no byte changes.

Forbidden:
- Any mutation outside the allowed paths.
- Any edit to the approved Design, W2 collection authorities, candidate root, external audit, historical receipt, `configs/base.py`, or existing W2/W1/REEF code.
- Network, socket, HTTP, public/private API, replay, execution, paper/live trading, deployment, SSH, commit, push, or runtime invocation against the production candidate root.
- New threshold, cost model, entry/exit rule, holding horizon, filter, benchmark, promotion criterion, kill criterion, compatibility alias, collector, or audit/receipt publisher.
- Full-repository autofix/formatting, `ruff check --fix .`, `git clean -fdx`, destructive cleanup, or reverting pre-existing user changes.

## Frozen Semantics and Task Routing

| Design edge / invariant | Production owner | Mechanical proof / fail-closed result |
| --- | --- | --- |
| §4.1, `INV-W20-01` exact authority before raw rows | CLI admission then `load_verified_w2_evidence(...)` | Wrong Design/Plan/auth/manifest/audit/receipt path, SHA, run ID, audit verdict, or required binding -> `STOP=w2_0_admission_invalid`, no output root. |
| §1, §7, `INV-W20-02` | Reducer | `outcome_inspection_status=outcome_seen`; only §1 reducer may emit `exploratory_only` or `evidence_insufficient`; all other status combinations reject. |
| §2.2, §4.3-4.4, `INV-W20-03/06` | Reducer and serialized ledgers | 41 contracts and 27 parents conserved; incomplete identities remain exact rows, 29 contracts are never treated as IID. |
| §4.2, `INV-W20-04` | Read-only materializer then reducer | Only after strict admission, revalidate each manifest-bound ZIP/CSV with `validate_w2_zip_and_csv(...)` and map `logical_archive_records -> physical_source_object_id + metric -> parsed_rows`. Path/URL/hash, physical-ID/metric mapping, or validator rejection is `STOP=w2_0_candidate_row_materialization_invalid` before output-root creation. The reducer, not the materializer, performs `C[0]`/`C[-1]`, alignment, finite, and positive-index checks: any valid-admitted contract failure becomes its exact retained `diagnostic_incomplete:<reason>` row. No fill or omission. |
| §4.3, `INV-W20-05` | Reducer and output schema | Only permitted endpoint basis descriptors; raw OHLC, direction, return, funding, cost, PnL, signal, and execution fields reject. |
| §6, `INV-W20-07` | Storage writer and strict bundle loader | Create-exclusive, manifest-last, fsync/read-back; collision, symlink, partial write, stale temp, unexpected file, or hash mismatch -> no consumable sealed bundle. |
| §11, `INV-W20-08` | Storage manifest/loader and CLI | Exact 20-key bool-false vector. Missing, extra, non-bool, or true -> strict rejection; no collector/network/execution imports. |

## Implementation Closure Matrices

### State x Artifact

| State | Artifact state | Producer / consumer | Required proof |
| --- | --- | --- | --- |
| Authority admission invalid | No W2-0 output root | CLI stops before strict reader | Task 1 mutation -> `STOP=w2_0_admission_invalid` |
| Candidate root strict-valid | `VerifiedW2Evidence` in memory only | Existing strict reader -> materializer | Task 1 canonical fixture calls production loader |
| Rows materialized | In-memory `(physical_source_object_id, metric) -> parsed_rows` map only | W2-0 materializer -> reducer | Task 2 interior-endpoint integration and validator-failure mutation |
| Valid admitted but endpoint/value-incomplete contract | Contract/parent ledger rows marked exact `diagnostic_incomplete` | Reducer -> storage | Task 2 removes one materialized `C[0]`/`C[-1]` and preserves all 41 contract rows |
| Valid non-observed coverage | Contract/parent ledger rows marked `diagnostic_incomplete` | Reducer -> storage | Task 2 temporal/no-complete-bar tests preserve denominator rows |
| Reducer success | In-memory ledgers and summary only | Reducer -> writer | Task 2 41/27 and classification tests |
| Writer failure/collision | Temporary or incomplete files; no manifest | Storage writer | Task 3 short-write/exception/collision tests |
| Sealed bundle | Exactly five regular files, manifest last | Storage writer -> strict loader | Task 3 read-back/hash/file-set tests |
| Strict bundle rejection | No consumable consumer input | Strict loader | Task 3 mutation tests reject before consumption |

### Transition x Failure

| Transition | Failure | Required fail-closed result | Task / proof |
| --- | --- | --- | --- |
| Authority admission -> strict reader | Path, SHA, run, audit, receipt, or verdict mismatch | `STOP=w2_0_admission_invalid`; no root | Task 1 authority mutations |
| Strict reader -> row materializer | Candidate ZIP/CSV validation or manifest path/URL/hash mismatch | `STOP=w2_0_candidate_row_materialization_invalid`; no root | Task 2 validator failure mutation |
| Row materializer -> reducer | Missing physical ID, unexpected metric, path/URL/hash mismatch, or production validator rejection | `STOP=w2_0_candidate_row_materialization_invalid`; no root | Task 2 mapping/validator tests |
| Reducer -> ledgers | Missing `C[0]`/`C[-1]`, alignment, nonfinite, or nonpositive index | Retain the exact contract/parent incomplete row; never fill or globally STOP | Task 2 production-path endpoint/value mutations |
| Writer -> seal | Symlink, collision, short write, exception, stale temp, or hash mismatch | No manifest and no resumptive overwrite | Task 3 crash/recovery tests |
| Seal -> strict loader | File-set, JSON, authority, flag, or classification mismatch | Strict loader rejects | Task 3 mutation tests |
| Final verification -> review/audit | Scope/index/provenance or P0/P1 review finding | STOP or remediation plus re-verification/re-review; no Completion Audit | Task 5 Steps 3-5 |

### Authority x Owner x Proof

| Frozen authority / invariant | Producer or consumer | Task and mechanical proof | Fail-closed result |
| --- | --- | --- | --- |
| W2-0 Design SHA `58f4...62c4`, collection Design/Plan, auth, candidate manifest | Task 0 / CLI admission | Task 0 SHA loop; Task 1 mutations | `STOP=approved_authority_mismatch` or `STOP=w2_0_admission_invalid` |
| External completion audit SHA and historical receipt SHA | CLI admission | Task 1 audit/receipt bindings and mutations | `STOP=w2_0_admission_invalid` |
| Candidate root -> strict loader -> production validator rows | Existing reader / W2-0 materializer | Task 2 canonical interior-endpoint integration | `STOP=w2_0_candidate_row_materialization_invalid` |
| 41 contracts, 27 parents, coverage states | Reducer / storage loader | Task 2 conservation tests; Task 3 read-back | Reject conservation or ledger mismatch |
| Exact 20-field false vector | Reducer / storage / CLI | Task 2, 3, and 4 key-set mutations | Missing/extra/non-bool/true rejects |
| Pre-existing worktree and index provenance | Task 0 / Task 5 scope gate | Per-path `XY`, kind, bytes, index entries, and tombstone comparison | `STOP=preexisting_whitelist_overlap` or `STOP=preexisting_provenance_mutated` |

### Action x Authority Level

| Action | Design approved | Plan reviewed | Explicit implementation authorization | Separate runtime/deployment authorization |
| --- | --- | --- | --- | --- |
| Modify the whitelist `src/**` and `tests/**` paths | Insufficient | Insufficient | Required | N/A |
| Run local canonical tests, lint, scanner, and static scope checks | Insufficient | Insufficient | Required | N/A |
| Create a production W2-0 output root from the production candidate root | Insufficient | Insufficient | Insufficient | Required |
| Make any public/private network request, replay, or collector invocation | Forbidden | Forbidden | Forbidden | Forbidden in this Plan |
| Commit or push | Insufficient | Insufficient | Insufficient | Separate explicit authorization |
| Deploy, SSH, paper trade, live trade, or use authenticated/order APIs | Forbidden | Forbidden | Forbidden | Forbidden |
| Consume a sealed W2-0 bundle as exploratory evidence | Insufficient | Insufficient | Implementation completion is insufficient | Separate approved analysis run and later review |
| Promote to phenomenon, Alpha, execution, PnL, or trading claim | Forbidden | Forbidden | Forbidden | Forbidden |

### Invariant x Mechanical Evidence

| Invariant | Implementation owner | Positive / negative evidence | Final gate |
| --- | --- | --- | --- |
| `INV-W20-01` authority before rows | CLI and strict reader | Canonical root; one authority mutation per test | Task 5 authority SHA loop |
| `INV-W20-02` forced `outcome_seen`, reducer-only classification | Admission and reducer | Valid two classifications; invalid pairing rejection | Strict bundle loader check |
| `INV-W20-03` denominator conservation | Reducer and storage | 41 contract / 27 parent canonical result; missing row mutation | Task 5 regression |
| `INV-W20-04` exact complete-bar endpoints | Materializer and reducer | Interior `C[0]`/`C[-1]` production validator path; mapping/endpoint mutations | Task 5 regression and code review |
| `INV-W20-05` descriptive-only schema | Reducer and strict loader | Allowed descriptor output; prohibited raw-price/PnL/execution field mutation | Task 3 strict loader |
| `INV-W20-06` non-IID parent aggregation | Reducer | Parent median and correlated-row tests | Task 5 regression |
| `INV-W20-07` immutable manifest-last bundle | Storage writer/loader | Create/read-back; crash, symlink, partial-write mutations | Task 3 strict loader |
| `INV-W20-08` 20-field deny vector/no runtime authority | Reducer/storage/CLI | Exact key-set/value tests and socket/HTTP traps | Task 5 scanner, scope, and review |

## Task 0: Execution Baseline, Authority Gate, Scope and Graphify

**Design coverage:** §2.1, §4.1, §9 `INV-W20-01`, §10, §11.

**Files:**
- Create: none in the repository.
- Modify: none.
- Evidence output: `${TMPDIR:-/tmp}/stage1_6f_w2_0_baseline.<timestamp>/` only.

**Step 1: Bind the user-approved Plan before code changes.**

Run only after an implementation approval sentence provides both variables:

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${APPROVED_PLAN_PATH:?STOP=APPROVED_PLAN_PATH_missing}"
: "${APPROVED_PLAN_SHA256:?STOP=APPROVED_PLAN_SHA256_missing}"
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
cd "$PROJECT_ROOT"

DESIGN_PATH='docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-design_CN.md'
DESIGN_SHA='58f4cf8638b05a1c268578ace0ed8d4c6b8b794daa4d94107e2af349d22862c4'
test "$(shasum -a 256 "$DESIGN_PATH" | awk '{print $1}')" = "$DESIGN_SHA" || {
  echo 'STOP=design_authority_mismatch' >&2; exit 1;
}
test "$(shasum -a 256 "$APPROVED_PLAN_PATH" | awk '{print $1}')" = "$APPROVED_PLAN_SHA256" || {
  echo 'STOP=approved_authority_mismatch' >&2; exit 1;
}
printf 'CHECK_OK=approved_design_and_plan_bound\n'
```

Expected: exit `0`. Any mismatch stops before tests or file edits.

**Step 2: Capture the full pre-existing worktree/index provenance and frozen authority hashes.**

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
cd "$PROJECT_ROOT"
EXECUTION_BASELINE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/stage1_6f_w2_0_baseline.XXXXXX")"
export EXECUTION_BASELINE_DIR

git rev-parse HEAD > "$EXECUTION_BASELINE_DIR/BASE_SHA"
git status --short --untracked-files=all > "$EXECUTION_BASELINE_DIR/status.before"
git diff --binary > "$EXECUTION_BASELINE_DIR/worktree.before.patch"
git diff --cached --binary > "$EXECUTION_BASELINE_DIR/index.before.patch"

cat > "$EXECUTION_BASELINE_DIR/allowed_paths.txt" <<'EOF_ALLOWED'
src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py
src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_storage.py
scripts/external_signal_shadow/run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py
tests/research/external_signal_shadow/stage1_6f_w2_0_test_support.py
tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py
tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_storage.py
tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py
EOF_ALLOWED

python3 - "$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")" \
  "$EXECUTION_BASELINE_DIR/preexisting_path_states.jsonl" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

base_sha, output_name = sys.argv[1:]

def git_names(*args):
    return set(subprocess.check_output(['git', *args], text=True).splitlines())

def porcelain_xy():
    records = subprocess.check_output(
        ['git', 'status', '--porcelain=v1', '-z', '--untracked-files=all']
    ).split(b'\0')
    result = {}
    i = 0
    while i < len(records):
        record = records[i]
        if not record:
            i += 1
            continue
        xy = record[:2].decode('ascii')
        path = record[3:].decode('utf-8', 'surrogateescape')
        result[path] = xy
        if 'R' in xy or 'C' in xy:
            i += 1
            result[records[i].decode('utf-8', 'surrogateescape')] = xy
        i += 1
    return result

def index_entries(relative_name):
    raw = subprocess.check_output(['git', 'ls-files', '-s', '-z', '--', relative_name])
    entries = []
    for record in raw.split(b'\0'):
        if not record:
            continue
        meta, _ = record.split(b'\t', 1)
        mode, blob_sha256, stage = meta.decode('ascii').split()
        entries.append({'mode': mode, 'blob_sha256': blob_sha256, 'stage': stage})
    return entries

def snapshot(relative_name, tracked_dirty, staged, untracked, xy):
    path = Path(relative_name)
    kinds = sorted(kind for kind, present in (
        ('tracked_dirty', relative_name in tracked_dirty),
        ('staged', relative_name in staged),
        ('untracked', relative_name in untracked),
    ) if present)
    if path.is_symlink():
        state, sha256 = 'symlink', hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    elif path.is_file():
        state, sha256 = 'file', hashlib.sha256(path.read_bytes()).hexdigest()
    elif path.exists():
        raise SystemExit(f'STOP=unsupported_preexisting_path_state:{relative_name}')
    else:
        state, sha256 = 'tombstone', None
    return {
        'path': relative_name,
        'xy': xy.get(relative_name, '--'),
        'kinds': kinds,
        'worktree_state': state,
        'worktree_sha256': sha256,
        'index_entries': index_entries(relative_name),
    }

tracked_dirty = git_names('diff', '--name-only', base_sha)
staged = git_names('diff', '--cached', '--name-only', base_sha)
untracked = git_names('ls-files', '--others', '--exclude-standard')
xy = porcelain_xy()
paths = sorted(tracked_dirty | staged | untracked)
with Path(output_name).open('w', encoding='utf-8') as out:
    for relative_name in paths:
        out.write(json.dumps(snapshot(relative_name, tracked_dirty, staged, untracked, xy), sort_keys=True) + '\n')
PY

cat > "$EXECUTION_BASELINE_DIR/authority.sha256" <<'EOF_AUTH'
58f4cf8638b05a1c268578ace0ed8d4c6b8b794daa4d94107e2af349d22862c4 docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-design_CN.md
11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303 docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md
183689a6b786ccd3dce9f74f5d1fc2e9ccc1741d80f243f5724dd3b7de149229 docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md
0189fd4a922c87811e25793b62d12d6ba76ad92e60a95236a3fe54f024fa5dbf configs/authorizations/network_auth_w2_candidate_run_20260925_001.json
1bd45df8d27e85b40d30500148575780740c6d089b5700e43c1cbfc22a4a0cea data/external_signal_shadow/stage1_6f/w2_evidence_candidates/w2_candidate_run_20260925_001/candidate_manifest.json
1c3051315711b5fb0f80086d7f7dab3639a8ba438a74ab4ec4558ce3180d76f2 /Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_completion_audit_review.md
5f6f1087888e73a0304f91b07d3a8b6ebaf7ca9b7701e4ab4de714dc158e0e25 /Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_candidate_run_20260925_001_preanalysis_blind_receipt.json
EOF_AUTH
while read -r expected path; do
  actual="$(shasum -a 256 "$path" | awk '{print $1}')"
  test "$actual" = "$expected" || { echo "STOP=approved_authority_mismatch:$path" >&2; exit 1; }
done < "$EXECUTION_BASELINE_DIR/authority.sha256"

python3 - <<'PY'
from configs.base import RISK_LIVE_TRADING_ENABLED
assert RISK_LIVE_TRADING_ENABLED is False, 'STOP=live_trading_not_disabled'
print('CHECK_OK=live_trading_disabled')
PY
printf 'EXECUTION_BASELINE_DIR=%s\n' "$EXECUTION_BASELINE_DIR"
printf 'BASE_SHA=%s\n' "$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")"
```

Expected: exit `0`. `preexisting_path_states.jsonl` is the authoritative provenance ledger: every pre-existing path records exact porcelain `XY`, tracked/staged/untracked kinds, worktree file/symlink/tombstone state and SHA, plus every index mode/blob/stage entry (empty list is the explicit index tombstone). Existing dirty/untracked paths are never an implementation exception: do not delete, stage, revert, overwrite, or attribute them to W2-0.

**Step 3: Verify the actual shared-helper impact cone.**

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
cd "$PROJECT_ROOT"
command -v graphify >/dev/null || { echo 'STOP=graphify_workflow_contract_unavailable' >&2; exit 1; }
test -f graphify-out/graph.json || { echo 'STOP=graphify_workflow_contract_unavailable' >&2; exit 1; }
graphify affected 'load_verified_w2_evidence' --depth 3 | tee "$EXECUTION_BASELINE_DIR/graphify_affected.txt"
rg -n 'load_verified_w2_evidence|stage1_6f_w2_evidence_source' \
  src scripts tests > "$EXECUTION_BASELINE_DIR/w2_reader_consumers.txt"
```

Expected: `graphify` identifies the existing W2 collector and its tests; direct source inspection confirms no existing W2-0 consumer. Treat Graphify as advisory: if a newly found real consumer needs modification, stop with `STOP=BLOCKED_SCOPE_DRIFT`; otherwise keep it under “Affected but unchanged.”

**Step 4: Reject an implementation-whitelist overlap immediately before RED.**

```bash
set -euo pipefail
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
python3 - "$EXECUTION_BASELINE_DIR/preexisting_path_states.jsonl" \
  "$EXECUTION_BASELINE_DIR/allowed_paths.txt" <<'PY'
import json
import sys
from pathlib import Path

baseline_paths = {
    json.loads(line)['path']
    for line in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines()
    if line
}
allowed = {
    line for line in Path(sys.argv[2]).read_text(encoding='utf-8').splitlines() if line
}
overlap = sorted(baseline_paths & allowed)
if overlap:
    raise SystemExit(f'STOP=preexisting_whitelist_overlap:{overlap}')
print('CHECK_OK=preexisting_whitelist_disjoint')
PY
```

Expected: exit `0` immediately before Task 1 RED. The allowed implementation/verification list deliberately excludes this Plan and all authority documents because no implementation task may modify them. Any overlap is `STOP=preexisting_whitelist_overlap`; an allowlist is never permission to overwrite a pre-existing path.

## Task 1: Canonical W2-0 Fixture Support and Admission Tests (RED)

**Design coverage:** §2.1-2.3, §4.1, §10; `INV-W20-01`, Rule 15 canonical-positive integrity.

**Files:**
- Create: `tests/research/external_signal_shadow/stage1_6f_w2_0_test_support.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py`
- Modify: none.

**Step 1: Create canonical mirror support without synthetic authority bytes.**

Implement `create_canonical_w2_0_mirror(tmp_path, project_root=...)` by reusing the W2 fixture’s verified root/authority derivation pattern. It must link-or-copy the current W2 candidate root and all in-workspace exact authority bytes, then SHA-check every copied authority. The canonical-positive admission reads external audit and receipt from their exact immutable absolute paths. A declared negative audit/receipt mutation may first hard-link-or-copy those exact bytes into the test mirror, then `unlink()` the mirror file before its one mutation; it must never modify the external source artifact.

`_link_or_copy` must use `os.link`; on `OSError` it must use `shutil.copy2`. `mutate_mirror_file` must `unlink()` first so a negative mutation cannot alter a hard-linked authority or candidate file.

**Step 2: Write failing admission tests.**

Create a canonical-positive admission case that requires all of:

```python
verified = load_verified_w2_evidence(...)
assert verified.run_id == 'w2_candidate_run_20260925_001'
assert admission.outcome_inspection_status == 'outcome_seen'
assert admission.audit_verdict == 'complete'
```

Add one declared mutation per test: Design SHA, future approved Plan SHA, W2 network authorization SHA, candidate manifest SHA, external audit SHA, external audit `Final Verdict: complete` token, receipt SHA, receipt candidate run/manifest/audit binding, receipt issued `not_seen` state, and forbidden receipt schema/key. Each must fail before W2 parsed rows are consumed and before any output-root creation.

Run:

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  -k 'admission or authority or receipt'
```

Expected before Task 2 implementation: fail only because W2-0 module/admission API is absent.

**Step 3: Keep the fixture boundary minimal.**

Do not create a second W2 parser, fake `VerifiedW2Evidence`, fake external audit, fake receipt, mock network transport, or W2 data copy in the repository. Pure arithmetic unit inputs are allowed only inside Task 2 and cannot serve as a cross-boundary positive fixture.

## Task 2: Implement the W2-0 Reducer and Complete Ledgers (RED -> GREEN)

**Design coverage:** §1, §2.2, §4.2-4.4, §7-8; `INV-W20-02` through `INV-W20-06`.

**Files:**
- Create: `src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py`
- Modify: `tests/research/external_signal_shadow/stage1_6f_w2_0_test_support.py`

**Step 1: Add RED tests for the verified-row materializer and exact reducer contract.**

Tests must prove:

1. The canonical root yields exactly 41 contract ledger rows and 27 parent ledger rows; 31/21 window-defined and 29/19 complete counts remain explicit.
2. Every parent appears exactly once. `temporal_unproven` and `no_complete_bars` parents remain `diagnostic_incomplete`, rather than being removed or counted as zero basis.
3. The canonical integration first calls `load_verified_w2_evidence(...)`, then `materialize_verified_w2_rows(...)`. It dynamically selects at least one canonical observed identity whose `C[0]` and `C[-1]` are both interior rows of their validated daily physical objects, asserts such an identity exists, and proves each endpoint came from the materialized production-validator row map rather than the physical object's manifest `first_row` or `last_row`.
4. For every observed identity, `C` comes only from `compute_w2_grid_points(window_start_ms, window_end_ms)`, `t_first=C[0]`, `t_last=C[-1]`, and all three families must contain both timestamps.
5. A declared negative mutation of the in-memory manifest-bound logical `physical_source_object_id` or metric causes `STOP=w2_0_candidate_row_materialization_invalid`. A declared monkeypatch that makes the W2-0 module's imported production `validate_w2_zip_and_csv(...)` reject after strict admission also causes that STOP before reducer or output creation. These are structural/trust failure proofs only; no fake positive `VerifiedW2Evidence` is allowed.
6. A separate production-path endpoint mutation starts from successful canonical strict load and successful materialization, removes exactly one `C[0]` or `C[-1]` row from `W20VerifiedRows`, then passes that object to the production reducer. It must produce `diagnostic_incomplete:endpoint_coverage_gap`, preserve all 41 contract rows and 27 parent rows, and create no global STOP or dropped identity.
7. The pure arithmetic fixture computes `10_000 * (perp_or_mark - index) / index` and `abs(last) - abs(first)` exactly, while serializable records exclude raw OHLC, open/high/low, return, direction, funding, cost, PnL, signal, order, and execution fields.
8. Missing endpoint, duplicate timestamp, nonfinite input, and `index_close <= 0` create the Design exact `diagnostic_incomplete:<reason>` row, retain the identity, and do not use fill/retry/fallback.
9. Parent descriptor is the deterministic median of qualified child descriptors; the 29 contract rows are marked correlated diagnostics, never independent observations.
10. `outcome_inspection_status` is always `outcome_seen`; either metric with a descriptor yields root `exploratory_only`; both zero yields root `evidence_insufficient`; any other classification or status pairing is rejected.

Run:

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py
```

Expected before implementation: failing tests identify the absent reducer API only.

**Step 2: Implement the smallest reducer API.**

Use frozen dataclasses for admitted authority, materialized verified rows, contract rows, parent rows, and result summary. Provide only:

```python
def admit_w2_0_inputs(...) -> W20Admission: ...
def materialize_verified_w2_rows(
    *, verified_w2: VerifiedW2Evidence
) -> W20VerifiedRows: ...
def compute_w2_0_exploratory_terminal_basis(
    *, verified_w2: VerifiedW2Evidence, verified_rows: W20VerifiedRows,
    admission: W20Admission
) -> W20DiagnosticResult: ...
def reduce_research_classification(...) -> str: ...
```

Requirements:
- `admit_w2_0_inputs` SHA-checks every authority before returning and validates the audit’s exact `complete` verdict plus required W2 Design/Plan/auth/manifest/run/root bindings. It strictly parses the receipt JSON, verifies its own audit/manifest/run/root bindings and historical `not_seen`, then returns the current forced `outcome_seen` classification. It does not mutate the receipt.
- `materialize_verified_w2_rows` runs only after successful `load_verified_w2_evidence(...)`. It uses the returned `verified_w2.manifest` `physical_source_objects` and `logical_archive_records`, plus `verified_w2.completed_root`; for every required verified physical object it re-calls the existing production `validate_w2_zip_and_csv(zip_path, csv_path, exact_source_url)`. It SHA/length-checks the returned result against the manifest and builds an immutable `(physical_source_object_id, metric) -> parsed_rows` map only after every logical record maps to the exact object and metric. It must neither open CSV files directly nor define a second CSV/ZIP parser; it must never read manifest `first_row`/`last_row` as endpoint data. Validator rejection and path/URL/hash/physical-ID/metric mapping failures raise `STOP=w2_0_candidate_row_materialization_invalid` before the reducer can run. It does not inspect or decide grid endpoint availability.
- The reducer consumes `VerifiedW2Evidence` and `W20VerifiedRows` only; it does not import a script, collector, transport, socket, HTTP library, execution layer, W1/REEF code, or `configs/base.py` thresholds. It alone computes `C` and decides endpoint/alignment/value eligibility. A missing `C[0]`/`C[-1]`, alignment failure, nonfinite value, or nonpositive index produces that contract's exact retained `diagnostic_incomplete:<reason>` row; valid non-observed `metric_window_coverages` likewise produce their Design-defined incomplete row. It cannot convert any missing materialized row into zero or a filled endpoint.
- Use `math.isfinite`, `sorted`, and direct list arithmetic. Do not add a registry, factory, generic metric engine, defaulting helper, config setting, new threshold, or compatibility alias.
- The exact W2-0 20-field false mapping is a source constant. Validate `set(keys)` equality and `type(value) is bool and value is False`; do not use `.get(..., False)`.
- The only emitted numeric descriptors are the Design-permitted basis values and their parent distribution summaries. The reducer must never serialize raw price rows.

**Step 3: Run GREEN and upstream-reader regression.**

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py
```

Expected: exit `0`. Allow at least 1,200 seconds for this real-root suite; do not treat a 30-second process timeout as a test failure diagnosis. The canonical integration must demonstrate the full `strict loader -> materializer -> reducer` route, not only pure arithmetic.

## Task 3: Immutable W2-0 Bundle Writer and Strict Loader (RED -> GREEN)

**Design coverage:** §5-6, §7, §9 `INV-W20-07/08`.

**Files:**
- Create: `src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_storage.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_storage.py`
- Modify: `tests/research/external_signal_shadow/stage1_6f_w2_0_test_support.py`

**Step 1: Write RED storage tests.**

Use the canonical reducer result from Task 2. Require exactly these five regular files and no others:

```text
stage1_6f_w2_0_denominator.jsonl
stage1_6f_w2_0_contract_metrics.jsonl
stage1_6f_w2_0_parent_metrics.jsonl
stage1_6f_w2_0_summary.json
stage1_6f_w2_0_bundle_manifest.json
```

Tests must cover positive write/read-back and one mutation each for: collision, symlink root/file, stale temporary file, unexpected extra file, duplicate JSON key, nonfinite JSON literal, short/zero write, exception before manifest, post-seal byte hash mutation, manifest key mismatch, authority path/SHA mismatch, missing/extra/non-bool/true 20-field flag, invalid `outcome_seen`/reducer classification pairing, and forbidden raw-price/PnL/execution field.

Run:

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_storage.py
```

Expected before storage implementation: failing tests identify the missing W2-0 storage module only.

**Step 2: Implement manifest-last, create-exclusive storage.**

Follow the existing W1 storage’s verified pattern only where it satisfies this Design: stdlib temp sibling files, `flush`, `os.fsync`, read-back SHA/length verification, `os.replace`, and directory `fsync`. The target root must be new, non-symlink, and under exactly:

```text
data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/<run_id>
```

The manifest is the last write and contains only exact artifact metadata, exact authority bindings, conserved counts, root/metric classifications, and exact 20-field false `authority_flags`. The loader independently validates JSON duplicate/nonfinite rejection, filename set, symlink/temp rejection, file hashes/lengths, no prohibited fields, the 20-field set, and the §1 classification reducer. On any failure, raise a W2-0 storage error; do not clean, overwrite, append, reuse the run ID, or publish a manifest.

**Step 3: Run GREEN plus W1 compatibility regression.**

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_storage.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py
```

Expected: exit `0`; W1 storage has no W2-0 dependency and remains unchanged.

## Task 4: Offline CLI Admission, Routing and No-Network Proof (RED -> GREEN)

**Design coverage:** §4.1, §5, §6-7, §9 `INV-W20-01/07/08`.

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py`
- Create: `tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py`
- Modify: `tests/research/external_signal_shadow/stage1_6f_w2_0_test_support.py`

**Step 1: Write RED CLI integration tests.**

The positive CLI invocation must pass project root, exact W2 candidate root, external audit path/SHA, receipt path/SHA, user-approved W2-0 Plan path/SHA, and a new relative W2-0 output root. It must prove the call order:

```text
exact authorities
-> external audit and receipt binding
-> load_verified_w2_evidence(...)
-> materialize_verified_w2_rows(...)
-> reducer
-> create-exclusive write
-> strict read-back
```

Negative tests must reject before output-root creation: absolute/`..`/wrong-parent/symlink output root, invalid run ID, collision, wrong W2-0 Design or approved Plan, wrong audit/receipt binding, strict-reader error, row-materializer validation/mapping error (`STOP=w2_0_candidate_row_materialization_invalid`), output writer error, and strict read-back error. Trap `socket.socket`, `socket.create_connection`, `urllib.request.urlopen`, `http.client.HTTPConnection`, and `http.client.HTTPSConnection`; any call fails the test.

Run:

```bash
.venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py
```

Expected before CLI implementation: fail solely because the runner is absent.

**Step 2: Implement the thin CLI adapter.**

The CLI owns path normalization and returns `1` after writing an exact `STOP=<reason>` to stderr for every rejection. It must:

- Verify the approved W2-0 Design at its frozen path/SHA and the supplied approved W2-0 Plan path/SHA before opening raw CSV through the strict reader.
- Use the Task 2 admission function for external audit/receipt semantics; do not add an audit writer, receipt writer, publisher, network switch, or parser fallback.
- Call only the new reducer and storage modules plus `load_verified_w2_evidence(...)` and `materialize_verified_w2_rows(...)`; call the latter only after strict-reader success and before reducer invocation.
- Permit no input that could result in an output outside the exact W2-0 parent directory.
- Print only bundle identity/status/count metadata. Never print raw price, OHLC, basis values, descriptors, return, PnL, signal, or execution data.

**Step 3: Run GREEN with no-network, upstream and W1 regressions.**

```bash
.venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_storage.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py
```

Expected: exit `0`; no network occurs; existing W2/W1 paths remain compatible.

## Task 5: Final Static Verification, Provenance/Scope Proof, Code Review and Independent Audit Routing

**Design coverage:** all invariants; §10-11.

**Files:**
- Create/modify: none beyond Tasks 1-4.
- Evidence output: `$EXECUTION_BASELINE_DIR` only.

**Step 1: Run bounded lint and full targeted regression.**

```bash
set -euo pipefail
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_storage.py \
  scripts/external_signal_shadow/run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  tests/research/external_signal_shadow/stage1_6f_w2_0_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py

.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py
```

Expected: both commands exit `0`. Do not use an external timeout below 1,200 seconds for the suite; it validates real archived bytes.

**Step 2: Capture the anti-shortcut scanner’s actual process exit code.**

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
BASE_SHA="$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")"
export BASE_SHA
SCANNER_OUT="$EXECUTION_BASELINE_DIR/anti_shortcut_scan.txt"
if python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" --all-lines \
  src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_storage.py \
  scripts/external_signal_shadow/run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  tests/research/external_signal_shadow/stage1_6f_w2_0_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_0_exploratory_terminal_basis_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  >"$SCANNER_OUT" 2>&1; then SCANNER_RC=0; else SCANNER_RC=$?; fi
cat "$SCANNER_OUT"
printf '%s\n' "$SCANNER_RC" > "$EXECUTION_BASELINE_DIR/anti_shortcut_scan.exitcode"
test "$SCANNER_RC" -eq 0 || { echo 'STOP=anti_shortcut_scan_nonzero' >&2; exit 1; }
```

Expected: actual `SCANNER_RC=0`. Every warning requires a specific completion-audit disposition; scanner zero is not proof of the no-network or authority invariants.

**Step 3: Prove Task-0-relative provenance, exact scope/index delta, and frozen authority immutability.**

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
cd "$PROJECT_ROOT"
BASE_SHA="$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")"
export BASE_SHA

allowed_paths=()
while IFS= read -r path; do allowed_paths+=("$path"); done < "$EXECUTION_BASELINE_DIR/allowed_paths.txt"
git diff --check -- "${allowed_paths[@]}"
git diff --cached --check -- "${allowed_paths[@]}"
git diff --name-only "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/final-worktree-paths.txt"
git diff --cached --name-only "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/final-index-paths.txt"
git status --short --untracked-files=all > "$EXECUTION_BASELINE_DIR/status.after"
while read -r expected path; do
  actual="$(shasum -a 256 "$path" | awk '{print $1}')"
  test "$actual" = "$expected" || { echo "STOP=frozen_authority_mutated:$path" >&2; exit 1; }
done < "$EXECUTION_BASELINE_DIR/authority.sha256"

python3 - "$BASE_SHA" "$EXECUTION_BASELINE_DIR" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
base_sha, baseline_name = sys.argv[1:]
baseline_dir = Path(baseline_name)
allowed = {
    line for line in (baseline_dir / 'allowed_paths.txt').read_text(encoding='utf-8').splitlines()
    if line
}

def git_names(*args):
    return set(subprocess.check_output(['git', *args], text=True).splitlines())

def porcelain_xy():
    records = subprocess.check_output(
        ['git', 'status', '--porcelain=v1', '-z', '--untracked-files=all']
    ).split(b'\0')
    result = {}
    i = 0
    while i < len(records):
        record = records[i]
        if not record:
            i += 1
            continue
        xy = record[:2].decode('ascii')
        path = record[3:].decode('utf-8', 'surrogateescape')
        result[path] = xy
        if 'R' in xy or 'C' in xy:
            i += 1
            result[records[i].decode('utf-8', 'surrogateescape')] = xy
        i += 1
    return result

def index_entries(relative_name):
    raw = subprocess.check_output(['git', 'ls-files', '-s', '-z', '--', relative_name])
    entries = []
    for record in raw.split(b'\0'):
        if not record:
            continue
        meta, _ = record.split(b'\t', 1)
        mode, blob_sha256, stage = meta.decode('ascii').split()
        entries.append({'mode': mode, 'blob_sha256': blob_sha256, 'stage': stage})
    return entries

def snapshot(relative_name, tracked_dirty, staged, untracked, xy):
    path = Path(relative_name)
    kinds = sorted(kind for kind, present in (
        ('tracked_dirty', relative_name in tracked_dirty),
        ('staged', relative_name in staged),
        ('untracked', relative_name in untracked),
    ) if present)
    if path.is_symlink():
        state, sha256 = 'symlink', hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    elif path.is_file():
        state, sha256 = 'file', hashlib.sha256(path.read_bytes()).hexdigest()
    elif path.exists():
        raise SystemExit(f'STOP=unsupported_preexisting_path_state:{relative_name}')
    else:
        state, sha256 = 'tombstone', None
    return {
        'path': relative_name,
        'xy': xy.get(relative_name, '--'),
        'kinds': kinds,
        'worktree_state': state,
        'worktree_sha256': sha256,
        'index_entries': index_entries(relative_name),
    }

tracked_dirty = git_names('diff', '--name-only', base_sha)
staged = git_names('diff', '--cached', '--name-only', base_sha)
untracked = git_names('ls-files', '--others', '--exclude-standard')
xy = porcelain_xy()
current_paths = tracked_dirty | staged | untracked
baseline_records = [
    json.loads(line)
    for line in (baseline_dir / 'preexisting_path_states.jsonl').read_text(encoding='utf-8').splitlines()
    if line
]
baseline_paths = {record['path'] for record in baseline_records}
overlap = sorted(baseline_paths & allowed)
assert not overlap, f'STOP=preexisting_whitelist_overlap:{overlap}'

after_records = []
for expected in baseline_records:
    actual = snapshot(expected['path'], tracked_dirty, staged, untracked, xy)
    after_records.append(actual)
    assert actual == expected, (
        f"STOP=preexisting_provenance_mutated:{expected['path']}:"
        f"expected={expected}:actual={actual}"
    )
(baseline_dir / 'preexisting_path_states.after.jsonl').write_text(
    ''.join(json.dumps(record, sort_keys=True) + '\n' for record in after_records),
    encoding='utf-8',
)

worktree_delta = git_names('diff', '--name-only', base_sha)
index_delta = git_names('diff', '--cached', '--name-only', base_sha)
new_paths = current_paths - baseline_paths
unexpected = sorted((worktree_delta | index_delta | new_paths) - baseline_paths - allowed)
assert not unexpected, f'STOP=scope_violation:{unexpected}'
new_index_delta = index_delta - baseline_paths
assert new_index_delta <= allowed, f'STOP=index_delta_outside_whitelist:{sorted(new_index_delta - allowed)}'
print(f'CHECK_OK=preexisting_provenance_unchanged:{len(baseline_records)}')
print(f'CHECK_OK=scope_paths_allowed:{len(new_paths)}')
print(f'CHECK_OK=index_delta_paths:{len(new_index_delta)}')
PY
```

Expected: all checks exit `0`. `git diff --check` examines only the new implementation whitelist, so unrelated pre-existing dirty bytes cannot create a false STOP. Every pre-existing path's `XY`, kind, worktree bytes/state, and index mode/blob/stage entries must be exact Task-0 matches; a matching allowed pathname never excuses a mutation. New worktree/index paths must be whitelisted relative to the Task-0 ledger. A changed generated `data/**` root remains uncommitted and is not evidence of runtime authorization.

**Step 4: Request independent code review before Completion Audit.**

Use `.agent/skills/requesting-code-review/SKILL.md` after Steps 1-3 pass and before Completion Audit. It is not replaced by Completion Audit.

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
cd "$PROJECT_ROOT"
BASE_SHA="$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")"
REVIEW_HEAD_SHA="$(git rev-parse HEAD)"
test "$REVIEW_HEAD_SHA" = "$BASE_SHA" || {
  echo "STOP=unexpected_commit_before_review:base=$BASE_SHA head=$REVIEW_HEAD_SHA" >&2
  exit 1
}
git diff --binary "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/review-worktree.patch"
git diff --cached --binary "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/review-index.patch"
git ls-files --others --exclude-standard | LC_ALL=C sort -u > "$EXECUTION_BASELINE_DIR/review-untracked-paths.txt"
printf 'CHECK_OK=code_review_scope:base=%s:head=%s\n' "$BASE_SHA" "$REVIEW_HEAD_SHA"
```

The independent reviewer receives the approved Design/Plan path and SHA, frozen authorities/no-touch boundary, `BASE_SHA`, final worktree/index diffs, new allowed untracked paths, `$EXECUTION_BASELINE_DIR`, Task-0/final provenance ledgers, exact test/lint/scanner commands with actual exit codes, scanner warning dispositions, production materializer endpoint proof, negative mutations, and crash/recovery proof. The review must inspect production call paths, row materialization, authority/permission preservation, scope/index provenance, and absence of audit/publisher/network code. A P0/P1 or scope/authority finding blocks Completion Audit. Remediate only within this approved scope, rerun affected RED/GREEN and regressions plus Steps 1-3, then request a fresh code review. Any repair requiring Design, lifecycle-owner, request-set, or whitelist change is `STOP=BLOCKED_SPEC_DRIFT` or `STOP=BLOCKED_SCOPE_DRIFT`.

**Step 5: Route to independent read-only Completion Audit only after code-review clearance.**

Do not write a completion artifact in the audited worktree and do not declare completion. Route the independent read-only auditor through `.agent/skills/audit-plan-completion/SKILL.md`, supplying only: approved Plan path/SHA, approved Design path/SHA, `BASE_SHA`, `$EXECUTION_BASELINE_DIR`, exact whitelist, known pre-existing provenance, code-review clearance, and factual verification evidence. The auditor independently inspects actual source routing, strict reader/materializer, tests, scanner RC, index/worktree, and issues `COMPLETE`, `INCOMPLETE`, or a classified `BLOCKED_*` verdict.

## Execution Gates

1. This document is not implementation authority. Execution requires a separate user approval sentence that binds this exact Plan SHA.
2. Any missing authority, stale external artifact, changed Design, invalid receipt/audit binding, Graphify-discovered required consumer outside scope, or frozen-source mismatch is `STOP=BLOCKED_SPEC_DRIFT` or `STOP=BLOCKED_SCOPE_DRIFT`; do not invent a fallback.
3. Tests use the canonical W2 root only through strict-loader-derived fixtures; no handcrafted cross-boundary positive, mock authority, or fabricated audit/receipt is allowed.
4. The implementation can prove an immutable, exploratory descriptive bundle derived from the verified historical root. It cannot prove a phenomenon, Alpha, PnL, trade direction, execution feasibility, replay validity, paper/live safety, or any permission to trade.
5. No task authorizes commit, push, deployment, SSH, runtime collection, replay, paper trading, live trading, private/authenticated/order APIs, or network access.
