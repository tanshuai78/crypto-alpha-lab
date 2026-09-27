# Stage 1.6F 终局基差结论边界下游文档维护 Implementation Plan

> **For Codex:** 仅在本 Plan 经独立审核且用户给出 exact implementation approval 后，使用 `executing-plans` 逐 Task 执行。

**Goal:** 将 `roadmap.md` 与项目状态矩阵中超出 Stage 1.6F-W2-0 `outcome_seen/exploratory_only` 证据边界的断言，收敛为已批准 Delta 所允许的事实性表述。

**Architecture:** 这是纯 Markdown 文档维护。执行器先验证外部批准的 Delta、全部冻结 authority、external Completion Audit 和 production strict W2-0 bundle admission；仅从 strict loader 返回的 `parent_records` 重算统计。随后只改两份下游文档，移除数值阈值、强制退出、`falsified`、Alpha 和“下架 consumer -> Stage 1.6R”叙述。不创建策略、风险模块、代码或运行时 artifact。

**Tech Stack:** Bash、Python 3 标准库、现有 `load_verified_w2_0_bundle(...)`、`shasum`、Git、`.agent/tools/anti_shortcut_scan.py`。

---

## Authority Packet

| Authority | Exact path | SHA-256 |
| --- | --- | --- |
| Approved conclusion-closure Delta Design | `docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-terminal-basis-conclusion-closure-delta-design_CN.md` | `133b3ff90bc2ff204a15282441cde386753c2e729be442ca8a5040f411d65a13` |
| W2 evidence Design | `docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md` | `11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303` |
| W2 evidence Plan | `docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md` | `183689a6b786ccd3dce9f74f5d1fc2e9ccc1741d80f243f5724dd3b7de149229` |
| W2 network authorization | `configs/authorizations/network_auth_w2_candidate_run_20260925_001.json` | `0189fd4a922c87811e25793b62d12d6ba76ad92e60a95236a3fe54f024fa5dbf` |
| W2 candidate manifest | `data/external_signal_shadow/stage1_6f/w2_evidence_candidates/w2_candidate_run_20260925_001/candidate_manifest.json` | `1bd45df8d27e85b40d30500148575780740c6d089b5700e43c1cbfc22a4a0cea` |
| W2-0 Design | `docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-design_CN.md` | `58f4cf8638b05a1c268578ace0ed8d4c6b8b794daa4d94107e2af349d22862c4` |
| W2-0 Plan | `docs/plans/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-implementation-plan_CN.md` | `17dc74ee85e66f490460e745e97aa2ec6628baccf9039f69d9e78ed49b0666fe` |
| W2-0 external Completion Audit | `/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_0_exploratory_diagnostic_completion_audit_review.md` | `1c034753b3d2ec41b53122967e2282d5ed0f1ded8d4100b1935064a3ad73271e` |
| W2-0 sealed manifest | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json` | `74ce94ac0f21125b97590228664f11ed836a0ed7836e2b75ed1ac35d555a317f` |
| W2-0 summary | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_summary.json` | `4af9aa1bad656d096f0eaffe5bd17d3e98bbc553329949dd6319507420da26b3` |

## Reviewed Target Baseline

These are the exact target-document bytes reviewed with this Plan candidate. They are not regenerated at implementation time.

| Target | Reviewed SHA-256 |
| --- | --- |
| `docs/roadmap.md` | `e12c623878de2304e82c3ebd1aef96ed4f56e226fa0d7dc9748283e96b56dfe6` |
| `docs/project-status/current-project-state_CN.md` | `8d2d8b9a3cadbfe3081e2002365c85ec69b6527156ec043cecfdbb6e386dce96` |

## Allowed Change Scope

Allowed implementation paths:
- none

Allowed verification paths:
- none

Allowed documentation paths:
- `docs/roadmap.md`
- `docs/project-status/current-project-state_CN.md`

Allowed generated/runtime artifacts:
- `/tmp/stage1_6f_conclusion_closure_baseline.*` (baseline evidence only; never committed)

Affected but unchanged:
- `docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-terminal-basis-conclusion-closure-delta-design_CN.md`
  - compatibility evidence: Task 0 verifies external approval path/SHA before any write.
- `src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_storage.py`
  - compatibility evidence: Task 0 calls production `load_verified_w2_0_bundle(...)`; no source edit is allowed.
- `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/**`
  - compatibility evidence: Task 0 strict-loader admission and post-write SHA comparison prove read-only consumption.
- `configs/base.py`, all collectors, W1/W2/W2-0 code/tests, external audits and historical receipts
  - compatibility evidence: Task 3 scope/index proof and live-safety check prove no mutation.

Forbidden:
- Any mutation outside the two allowed documentation paths.
- Any edit to this Plan, the approved Delta, authority files, source, tests, `configs/`, `data/`, scripts, external audit, receipt, Git index, or runtime artifacts.
- Network, replay, private/authenticated/order API, execution, paper/live trading, deployment, SSH, commit or push.
- Any new threshold, entry/exit/stop rule, holding horizon, strategy claim, cost model, Alpha claim, collector, consumer, Stage 1.6R module, or separate stage identity.
- Whole-repository formatting/autofix, `ruff check --fix .`, `git clean -fdx`, `git reset`, `git checkout --`, or reverting pre-existing user changes.

## Invariant Routing

| Delta invariant | Task and proof | Fail-closed result |
| --- | --- | --- |
| INV-S16C-01, 08 | Task 0 validates approved Delta bytes, every authority, external audit binding, then strict loader | `STOP=stage1_6_conclusion_authority_mismatch` |
| INV-S16C-02 | Task 0 computes from `parent_records`; Tasks 1-2 retain 41/27 and distinguish 29/19 | reject a 29-contract or 19-parent full-denominator claim |
| INV-S16C-03 | Tasks 1-2 allow only the exact `outcome_seen/exploratory_only` templates; Task 3 requires normalized template equality | `STOP=stage1_6_roadmap_template_mismatch` or `STOP=stage1_6_project_state_template_mismatch` |
| INV-S16C-04 | Task 1 removes threshold/mandatory exit/Stage 1.6R links; Task 3 requires the affected conclusion, blocker and gate ranges to equal their closed templates | `STOP=stage1_6_roadmap_template_mismatch` |
| INV-S16C-05 | Task 1 removes W1 direction/Carry/cost/causal/execution elevation; Task 3 seals all fact-bearing ranges to templates | `STOP=stage1_6_roadmap_template_mismatch` |
| INV-S16C-06, 07 | Task 3 docs-only scope, safety assertion and scanner actual RC | `STOP=stage1_6_scope_or_permission_violation` |

### State x Artifact

| State | Artifact | Required proof |
| --- | --- | --- |
| reviewed target | two reviewed Markdown byte streams | reviewed SHA match before Task 0 snapshot |
| execution baseline | `EXECUTION_BASELINE_DIR` byte copies and provenance ledger | exact copies plus path/index/worktree content and mode facts |
| document edit | only declared Stage 1.6 blocks/rows | baseline-derived final document equals the target byte-for-byte |
| final candidate | two Markdown files | separate semantic validators pass |

### Transition x Failure

| Transition | Failure | Required result |
| --- | --- | --- |
| review -> baseline | reviewed SHA mismatch | `STOP=reviewed_document_baseline_changed` and re-review |
| baseline -> edit | target changed before its task | `STOP=preexisting_document_baseline_changed` |
| edit -> final | editor failure/interruption | restore exact Task 0 backup only; no Git reset/checkout |
| final -> audit | semantic/provenance/review failure | stop, remediate, rerun all final gates |

### Authority Matrix

| Action | Required authority | Prohibited shortcut |
| --- | --- | --- |
| read sealed W2-0 facts | Delta authority packet plus strict loader PASS | direct `parent_metrics.jsonl` read |
| edit target documents | reviewed/approved Plan plus exact reviewed target baseline | accepting a newer target as a new baseline |
| preserve worktree/index | Task 0 provenance ledger | pathname-only comparison |
| Completion Audit | independent review after code review | executor self-certification |

### Invariant x Mechanical Evidence

| Invariant | Mechanical evidence |
| --- | --- |
| reviewed target identity | hardcoded reviewed SHA test before baseline copy |
| unrelated byte preservation | baseline-derived final-document equality and exact pre-existing path/index ledger equality |
| per-document conclusion boundary | independent validators require exact normalized templates for every fact-bearing mutable range; empty deleted ranges must be whitespace only |
| no Git-index mutation | full mode/blob/stage index-entry equality for every pre-existing path |

## Task 0: Baseline, Approval and Strict-Admission Gate

**Files:** Create/modify: none in repository. Evidence: `/tmp/stage1_6f_conclusion_closure_baseline.*` only.

**Step 1: Bind the externally approved Delta and this exact Plan.**

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${APPROVED_DELTA_DESIGN_PATH:?STOP=APPROVED_DELTA_DESIGN_PATH_missing}"
: "${APPROVED_DELTA_DESIGN_SHA256:?STOP=APPROVED_DELTA_DESIGN_SHA256_missing}"
: "${APPROVED_PLAN_PATH:?STOP=APPROVED_PLAN_PATH_missing}"
: "${APPROVED_PLAN_SHA256:?STOP=APPROVED_PLAN_SHA256_missing}"
cd "$PROJECT_ROOT"
DELTA='docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-terminal-basis-conclusion-closure-delta-design_CN.md'
PLAN='docs/plans/2026-09-27-external-signal-shadow-lab-stage1-6f-terminal-basis-conclusion-closure-implementation-plan_CN.md'
test "$APPROVED_DELTA_DESIGN_PATH" = "$DELTA" || { echo 'STOP=stage1_6_conclusion_authority_mismatch:delta_path' >&2; exit 1; }
test "$APPROVED_DELTA_DESIGN_SHA256" = '133b3ff90bc2ff204a15282441cde386753c2e729be442ca8a5040f411d65a13' || { echo 'STOP=stage1_6_conclusion_authority_mismatch:delta_approval_sha' >&2; exit 1; }
test "$(shasum -a 256 "$DELTA" | awk '{print $1}')" = "$APPROVED_DELTA_DESIGN_SHA256" || { echo 'STOP=stage1_6_conclusion_authority_mismatch:delta_bytes' >&2; exit 1; }
test "$APPROVED_PLAN_PATH" = "$PLAN" || { echo 'STOP=approved_authority_mismatch:plan_path' >&2; exit 1; }
test "$(shasum -a 256 "$PLAN" | awk '{print $1}')" = "$APPROVED_PLAN_SHA256" || { echo 'STOP=approved_authority_mismatch:plan_bytes' >&2; exit 1; }
test "$(shasum -a 256 docs/roadmap.md | awk '{print $1}')" = 'e12c623878de2304e82c3ebd1aef96ed4f56e226fa0d7dc9748283e96b56dfe6' || { echo 'STOP=reviewed_document_baseline_changed:roadmap' >&2; exit 1; }
test "$(shasum -a 256 docs/project-status/current-project-state_CN.md | awk '{print $1}')" = '8d2d8b9a3cadbfe3081e2002365c85ec69b6527156ec043cecfdbb6e386dce96' || { echo 'STOP=reviewed_document_baseline_changed:project_state' >&2; exit 1; }
echo 'CHECK_OK=approved_delta_and_plan_bound'
```

Expected: exit `0`; otherwise stop before any write.

**Step 2: Capture user-owned baseline without reverting it.**

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
cd "$PROJECT_ROOT"
test -z "${EXECUTION_BASELINE_DIR:-}" || { echo 'STOP=execution_baseline_dir_must_be_unset' >&2; exit 1; }
export EXECUTION_BASELINE_DIR="$(mktemp -d /tmp/stage1_6f_conclusion_closure_baseline.XXXXXX)"
printf '%s\n' docs/roadmap.md docs/project-status/current-project-state_CN.md > "$EXECUTION_BASELINE_DIR/allowed_docs.txt"
for target_and_backup_and_sha in \
  'docs/roadmap.md|roadmap.before|e12c623878de2304e82c3ebd1aef96ed4f56e226fa0d7dc9748283e96b56dfe6' \
  'docs/project-status/current-project-state_CN.md|current-project-state.before|8d2d8b9a3cadbfe3081e2002365c85ec69b6527156ec043cecfdbb6e386dce96'; do
  IFS='|' read -r target backup expected <<< "$target_and_backup_and_sha"
  test -f "$target" && test ! -L "$target" || { echo "STOP=reviewed_document_baseline_changed:not_regular:$target" >&2; exit 1; }
  cp "$target" "$EXECUTION_BASELINE_DIR/$backup"
  test -f "$EXECUTION_BASELINE_DIR/$backup" && test ! -L "$EXECUTION_BASELINE_DIR/$backup" || { echo "STOP=reviewed_document_baseline_changed:backup_not_regular:$target" >&2; exit 1; }
  test "$(shasum -a 256 "$EXECUTION_BASELINE_DIR/$backup" | awk '{print $1}')" = "$expected" || { echo "STOP=reviewed_document_baseline_changed:backup_sha:$target" >&2; exit 1; }
  cmp -s "$target" "$EXECUTION_BASELINE_DIR/$backup" || { echo "STOP=reviewed_document_baseline_changed:copy_race:$target" >&2; exit 1; }
done
git rev-parse HEAD > "$EXECUTION_BASELINE_DIR/BASE_SHA"
git status --short --untracked-files=all > "$EXECUTION_BASELINE_DIR/status.before"
git diff --binary > "$EXECUTION_BASELINE_DIR/worktree.before.patch"
git diff --cached --binary > "$EXECUTION_BASELINE_DIR/index.before.patch"
python3 - "$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")" "$EXECUTION_BASELINE_DIR/preexisting_path_states.jsonl" <<'PY'
import hashlib, json, os, stat, subprocess, sys
from pathlib import Path

base_sha, output_name = sys.argv[1:]

def git_names(*args):
    return set(subprocess.check_output(['git', *args], text=True).splitlines())

def porcelain_xy():
    records = subprocess.check_output(['git', 'status', '--porcelain=v1', '-z', '--untracked-files=all']).split(b'\0')
    result, i = {}, 0
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
        if record:
            meta, _ = record.split(b'\t', 1)
            mode, blob_sha, stage = meta.decode('ascii').split()
            entries.append({'mode': mode, 'blob_sha': blob_sha, 'stage': stage})
    return entries

def snapshot(relative_name, tracked_dirty, staged, untracked, xy):
    path = Path(relative_name)
    kinds = sorted(kind for kind, present in (
        ('tracked_dirty', relative_name in tracked_dirty),
        ('staged', relative_name in staged),
        ('untracked', relative_name in untracked),
    ) if present)
    if path.is_symlink():
        worktree_state = 'symlink'
        worktree_sha256 = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
        worktree_mode = stat.S_IMODE(path.lstat().st_mode)
    elif path.is_file():
        worktree_state = 'file'
        worktree_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        worktree_mode = stat.S_IMODE(path.lstat().st_mode)
    elif path.exists():
        raise SystemExit(f'STOP=unsupported_preexisting_path_state:{relative_name}')
    else:
        worktree_state, worktree_sha256, worktree_mode = 'tombstone', None, None
    return {'path': relative_name, 'xy': xy.get(relative_name, '--'), 'kinds': kinds,
            'worktree_state': worktree_state, 'worktree_sha256': worktree_sha256, 'worktree_mode': worktree_mode,
            'index_entries': index_entries(relative_name)}

tracked_dirty = git_names('diff', '--name-only', base_sha)
staged = git_names('diff', '--cached', '--name-only', base_sha)
untracked = git_names('ls-files', '--others', '--exclude-standard')
xy = porcelain_xy()
with Path(output_name).open('w', encoding='utf-8') as out:
    targets = {'docs/roadmap.md', 'docs/project-status/current-project-state_CN.md'}
    for relative_name in sorted(tracked_dirty | staged | untracked | targets):
        out.write(json.dumps(snapshot(relative_name, tracked_dirty, staged, untracked, xy), sort_keys=True) + '\n')
PY
printf 'EXECUTION_BASELINE_DIR=%s\n' "$EXECUTION_BASELINE_DIR"
echo 'CHECK_OK=baseline_captured'
```

Expected: exit `0`. In every later shell, the executor must first run `export EXECUTION_BASELINE_DIR=<printed-path>` and require `: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"`. The exact target bytes are copied and their backup SHA/copy equivalence are revalidated before snapshotting; every pre-existing path records `XY`, worktree kind/content SHA/mode or symlink target/tombstone, and index mode/blob/stage. Never reset or silently merge user input.

**Step 3: Verify exact authorities, audit binding and live safety.**

Create and verify the exact authority list, then require the external audit to contain `Final Verdict.*COMPLETE` plus its W2-0 Design, Plan, manifest and audited-source-commit bindings:

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
cd "$PROJECT_ROOT"
test "$(git rev-parse HEAD)" = "$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")" || { echo 'STOP=git_head_mutated' >&2; exit 1; }
cat > "$EXECUTION_BASELINE_DIR/authority.sha256" <<'EOF_AUTH'
11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303 docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md
183689a6b786ccd3dce9f74f5d1fc2e9ccc1741d80f243f5724dd3b7de149229 docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md
0189fd4a922c87811e25793b62d12d6ba76ad92e60a95236a3fe54f024fa5dbf configs/authorizations/network_auth_w2_candidate_run_20260925_001.json
1bd45df8d27e85b40d30500148575780740c6d089b5700e43c1cbfc22a4a0cea data/external_signal_shadow/stage1_6f/w2_evidence_candidates/w2_candidate_run_20260925_001/candidate_manifest.json
58f4cf8638b05a1c268578ace0ed8d4c6b8b794daa4d94107e2af349d22862c4 docs/designs/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-design_CN.md
17dc74ee85e66f490460e745e97aa2ec6628baccf9039f69d9e78ed49b0666fe docs/plans/2026-09-26-external-signal-shadow-lab-stage1-6f-w2-0-exploratory-terminal-basis-diagnostic-implementation-plan_CN.md
1c034753b3d2ec41b53122967e2282d5ed0f1ded8d4100b1935064a3ad73271e /Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_0_exploratory_diagnostic_completion_audit_review.md
74ce94ac0f21125b97590228664f11ed836a0ed7836e2b75ed1ac35d555a317f data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json
4af9aa1bad656d096f0eaffe5bd17d3e98bbc553329949dd6319507420da26b3 data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_summary.json
EOF_AUTH
while read -r expected path; do
  actual="$(shasum -a 256 "$path" | awk '{print $1}')"
  test "$actual" = "$expected" || { echo "STOP=stage1_6_conclusion_authority_mismatch:$path" >&2; exit 1; }
done < "$EXECUTION_BASELINE_DIR/authority.sha256"
AUDIT=/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/stage1_6f_w2_0_exploratory_diagnostic_completion_audit_review.md
rg -q 'Final Verdict.*COMPLETE' "$AUDIT" || { echo 'STOP=stage1_6_conclusion_authority_mismatch:audit_verdict' >&2; exit 1; }
for sha in 58f4cf8638b05a1c268578ace0ed8d4c6b8b794daa4d94107e2af349d22862c4 17dc74ee85e66f490460e745e97aa2ec6628baccf9039f69d9e78ed49b0666fe 74ce94ac0f21125b97590228664f11ed836a0ed7836e2b75ed1ac35d555a317f; do
  rg -q "$sha" "$AUDIT" || { echo "STOP=stage1_6_conclusion_authority_mismatch:audit_binding:$sha" >&2; exit 1; }
done
AUDITED_W2_0_COMMIT='bd5d7f3b34b7e42e883e9bbb8410fdf688982793'
rg -q "${AUDITED_W2_0_COMMIT:0:7} feat\\(stage1_6f\\): implement W2-0 exploratory terminal basis diagnostic runner, storage, and tests" "$AUDIT" || { echo 'STOP=stage1_6_conclusion_authority_mismatch:audit_source_commit' >&2; exit 1; }
git cat-file -e "$AUDITED_W2_0_COMMIT^{commit}" || { echo 'STOP=stage1_6_conclusion_authority_mismatch:audited_commit_missing' >&2; exit 1; }
for source in \
  src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_storage.py \
  scripts/external_signal_shadow/run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py; do
  test -f "$source" && test ! -L "$source" || { echo "STOP=stage1_6_conclusion_authority_mismatch:audited_source_not_regular:$source" >&2; exit 1; }
  test "$(git hash-object "$source")" = "$(git rev-parse "$AUDITED_W2_0_COMMIT:$source")" || { echo "STOP=stage1_6_conclusion_authority_mismatch:audited_source_blob:$source" >&2; exit 1; }
done
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

def stop(detail):
    raise SystemExit(f'STOP=stage1_6_conclusion_authority_mismatch:{detail}')

root = Path('data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z')
manifest_path = root / 'stage1_6f_w2_0_bundle_manifest.json'
artifact_names = {
    'stage1_6f_w2_0_contract_metrics.jsonl',
    'stage1_6f_w2_0_denominator.jsonl',
    'stage1_6f_w2_0_parent_metrics.jsonl',
    'stage1_6f_w2_0_summary.json',
}
flag_names = {
    'RISK_LIVE_TRADING_ENABLED', 'alpha_candidate_allowed', 'alpha_interpretation_allowed',
    'alpha_validated_allowed', 'authenticated_api_allowed', 'commit_allowed', 'deployment_allowed',
    'execution_engine_allowed', 'execution_feasibility_claim_allowed', 'live_trading_allowed',
    'net_cost_or_profit_claim_allowed', 'network_collection_allowed', 'order_api_allowed',
    'paper_trading_allowed', 'point_in_time_directional_replay_allowed', 'private_api_allowed',
    'push_allowed', 'replay_allowed', 'ssh_allowed', 'trade_signal_allowed',
}
if not root.is_dir() or root.is_symlink():
    stop('bundle_root_not_regular_directory')
if {path.name for path in root.iterdir()} != artifact_names | {manifest_path.name}:
    stop('bundle_file_set_mismatch')
if not manifest_path.is_file() or manifest_path.is_symlink():
    stop('manifest_not_regular')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
if set(manifest.get('artifacts', {})) != artifact_names:
    stop('manifest_artifact_set_mismatch')
for name in artifact_names:
    path = root / name
    item = manifest['artifacts'][name]
    if not path.is_file() or path.is_symlink() or item.get('relative_path') != name:
        stop(f'artifact_not_regular_or_bound:{name}')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != item.get('byte_length') or digest != item.get('sha256'):
        stop(f'artifact_length_or_sha_mismatch:{name}')
flags = manifest.get('authority_flags')
if set(flags or {}) != flag_names or any(value is not False for value in flags.values()):
    stop('authority_flags_not_exact_false_vector')
print('CHECK_OK=independent_w2_0_manifest_file_and_flag_verification')
PY
python3 - <<'PY'
from configs.base import RISK_LIVE_TRADING_ENABLED
assert RISK_LIVE_TRADING_ENABLED is False, 'STOP=live_trading_not_disabled'
print('CHECK_OK=live_trading_disabled')
PY
```

Expected: all checks exit `0`; missing byte, hash, verdict or binding is `STOP=stage1_6_conclusion_authority_mismatch`.

**Step 4: Admit, then recompute from the production strict-loader result.**

```bash
set -euo pipefail
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
cd "$PROJECT_ROOT"
python3 - <<'PY'
from pathlib import Path
from src.research.external_signal_shadow.stage1_6f_w2_0_exploratory_terminal_basis_diagnostic import compute_median, compute_nearest_rank_quantile
from src.research.external_signal_shadow.stage1_6f_w2_0_exploratory_terminal_basis_storage import load_verified_w2_0_bundle
bundle = load_verified_w2_0_bundle(
    output_root=Path('data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z'),
    project_root=Path.cwd(),
)
assert bundle.bundle_run_id == 'w2_0_exploratory_20260926T071500Z'
assert bundle.outcome_inspection_status == 'outcome_seen'
assert bundle.research_classification == 'exploratory_only'
assert len(bundle.parent_records) == 27
rows = [row for row in bundle.parent_records if row['status'] == 'exploratory_described']
assert len(rows) == 19
expected = {
  'median_delta_abs_perp_basis_bps': (12.407940689016186, 102.55655569154337, 446.66861842102907),
  'median_delta_abs_mark_basis_bps': (4.015736373189862, 41.71871219723057, 283.01068213762466),
}
for field, target in expected.items():
    values = [row[field] for row in rows]
    assert (compute_nearest_rank_quantile(values, .25), compute_median(values), compute_nearest_rank_quantile(values, .75)) == target
    assert sum(v < 0 for v in values) == 3
    assert sum(v > 0 for v in values) == 16
print('CHECK_OK=strict_bundle_admission_and_descriptive_recompute')
PY
```

Expected: exit `0`. Never open `parent_metrics.jsonl` directly. Any loader/schema/length/SHA/20-field authority-vector/statistic mismatch stops with `STOP=stage1_6_conclusion_authority_mismatch`.

**Step 5: Record graph and permission routing.**

`graphify` is N/A: no source-module producer/consumer topology changes. Record `CHECK_OK=graphify_not_applicable:docs_only_no_source_topology_change`. Only local Markdown editing is pending authorization; network, replay, execution, paper/live trading, SSH, deployment, commit and push remain forbidden.

## Task 1: Correct `docs/roadmap.md`

**Files:** Modify `docs/roadmap.md` only. No code or test files.

**Step 1: Recheck baseline.**

```bash
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
cd "$PROJECT_ROOT"
cmp -s docs/roadmap.md "$EXECUTION_BASELINE_DIR/roadmap.before" || { echo 'STOP=preexisting_document_baseline_changed:docs/roadmap.md' >&2; exit 1; }
```

**Step 2: Make only these textual corrections.**

Replace each named mutable range with the following exact normalized text. Do not add free prose, quantiles, alternate count relationships, states, strategies, thresholds, exits, causal stories, Stage 1.6R, or other assertions inside these ranges.

````markdown
* **Stage 1.6F Historical Research State**:
  * **Stage 1.6F-W2 Evidence Expansion**: `w2_candidate_run_20260925_001`; 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined.
  * **Stage 1.6F-W2-0 Terminal Basis Diagnostic**: `w2_0_exploratory_20260926T071500Z`; 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive.

| **Stage 1.6F (Historical Matched Control & Evidence Expansion)** | `completed` | `w2_candidate_run_20260925_001` | 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined. | conclusion closure only | checksum mismatch. |
| **Stage 1.6F-W2-0 (Exploratory Terminal Basis Diagnostic)** | `completed` | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json` | 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive. | `none_from_current_evidence` | no further gate from current evidence. |

### 4.2 Stage 1.6 Delisting Research & Diagnostic Chain

```text
Stage 1.6F W1/W2 evidence
  -> 180 physical source objects
  -> 41 contracts / 27 parents; 31 contracts / 21 parents window-defined
Stage 1.6F-W2-0 exploratory diagnostic
  -> 29 contracts / 19 parents exploratory_described
  -> outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]
  -> 3/19 negative; 16/19 positive
  -> conclusion closure only
```

* **2026-09-25**: Stage 1.6F-W2 evidence expansion completed for `w2_candidate_run_20260925_001`: 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined.
* **2026-09-26**: Stage 1.6F-W2-0 exploratory diagnostic completed for `w2_0_exploratory_20260926T071500Z`: 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive.
````

The removed Stage 1.6F-W2-0 item in `Completed and Falsified Work`, the Stage 1.6 blocker range before the Stage 1.5G P3 blocker, and the Next Gates range before Gate 3 must each be whitespace only. Preserve the complete Routes C1, Stage 1.4B and Cross-Sectional Factor Lab entries, Stage 1.5G, and all other unowned bytes exactly.

**Step 3: Recovery rule.** If the editor/write fails, run only the following, then stop; never use `git checkout`, `git restore`, reset, or unscoped editor recovery on the user-owned dirty baseline.

```bash
cp "$EXECUTION_BASELINE_DIR/roadmap.before" docs/roadmap.md
cmp -s docs/roadmap.md "$EXECUTION_BASELINE_DIR/roadmap.before" || { echo 'STOP=roadmap_recovery_copy_failed' >&2; exit 1; }
```

## Task 2: Correct `docs/project-status/current-project-state_CN.md`

**Files:** Modify `docs/project-status/current-project-state_CN.md` only. No code or test files.

**Step 1: Recheck baseline.**

```bash
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
cd "$PROJECT_ROOT"
cmp -s docs/project-status/current-project-state_CN.md "$EXECUTION_BASELINE_DIR/current-project-state.before" || { echo 'STOP=preexisting_document_baseline_changed:current-project-state' >&2; exit 1; }
```

**Step 2: Apply the minimal matrix correction.**

- Remove the stale aggregate `Stage 1.6A - 1.6R` row; do not reconstruct broader Stage 1.6A/1.6R history from sources outside this Delta authority packet.
- Replace the Stage 1.6F row with this exact normalized row; no other Stage 1.6 row is allowed:

```markdown
| **Stage 1.6F** | W1/W2/W2-0 descriptive conclusion closure | `implemented_locally`, `evidence_collected`, `reviewed` | `Yes` | Offline Tool | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json` | `w2_0_exploratory_20260926T071500Z`; 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined; 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive. | `none_from_current_evidence` |
```

The literal `[-24h, 0h]` in that row is the frozen observation window, not an exit, holding, stop or threshold rule. Do not add a Stage 1.6R row, future delisting consumer, quantile or new matrix vocabulary. `hypothesis_only` and `evidence_insufficient` are research-state terms, not matrix statuses.

If its editor/write fails, run only the following, then stop:

```bash
cp "$EXECUTION_BASELINE_DIR/current-project-state.before" docs/project-status/current-project-state_CN.md
cmp -s docs/project-status/current-project-state_CN.md "$EXECUTION_BASELINE_DIR/current-project-state.before" || { echo 'STOP=project_state_recovery_copy_failed' >&2; exit 1; }
```

## Task 3: Independent Document, Scope and Safety Gates

**Files:** Modify none.

**Step 1: Independently validate each complete baseline-derived document.**

````bash
set -euo pipefail
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
cd "$PROJECT_ROOT"
for target in docs/roadmap.md docs/project-status/current-project-state_CN.md; do
  test -f "$target" && test ! -L "$target" || { echo "STOP=target_not_regular:$target" >&2; exit 1; }
done
python3 - "$EXECUTION_BASELINE_DIR" <<'PY'
import sys
from pathlib import Path
from textwrap import dedent

baseline = Path(sys.argv[1])

def stop(message):
    raise SystemExit(f'STOP={message}')

def span(text, start, end):
    try:
        left = text.index(start)
        right = text.index(end, left) if end else len(text)
    except ValueError:
        stop(f'stage1_6_owned_range_anchor_missing:{start}')
    return left, right

def line_span(text, start):
    try:
        left = text.index(start)
    except ValueError:
        stop(f'stage1_6_owned_range_anchor_missing:{start}')
    right = text.find('\n', left)
    return left, len(text) if right == -1 else right + 1

def replace_ranges(text, patches):
    for left, right, replacement in sorted(patches, reverse=True):
        text = text[:left] + replacement + text[right:]
    return text

ROADMAP_HISTORICAL = dedent("""\
* **Stage 1.6F Historical Research State**:
  * **Stage 1.6F-W2 Evidence Expansion**: `w2_candidate_run_20260925_001`; 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined.
  * **Stage 1.6F-W2-0 Terminal Basis Diagnostic**: `w2_0_exploratory_20260926T071500Z`; 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive.
""").strip()

ROADMAP_MATRIX = dedent("""\
| **Stage 1.6F (Historical Matched Control & Evidence Expansion)** | `completed` | `w2_candidate_run_20260925_001` | 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined. | conclusion closure only | checksum mismatch. |
| **Stage 1.6F-W2-0 (Exploratory Terminal Basis Diagnostic)** | `completed` | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json` | 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive. | `none_from_current_evidence` | no further gate from current evidence. |
""").strip()

ROADMAP_CHAIN = dedent("""\
### 4.2 Stage 1.6 Delisting Research & Diagnostic Chain

```text
Stage 1.6F W1/W2 evidence
  -> 180 physical source objects
  -> 41 contracts / 27 parents; 31 contracts / 21 parents window-defined
Stage 1.6F-W2-0 exploratory diagnostic
  -> 29 contracts / 19 parents exploratory_described
  -> outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]
  -> 3/19 negative; 16/19 positive
  -> conclusion closure only
```
""").strip()

ROADMAP_W2_LOG = '* **2026-09-25**: Stage 1.6F-W2 evidence expansion completed for `w2_candidate_run_20260925_001`: 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined.'
ROADMAP_W20_LOG = '* **2026-09-26**: Stage 1.6F-W2-0 exploratory diagnostic completed for `w2_0_exploratory_20260926T071500Z`: 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive.'

PROJECT_STATE_ROW = '| **Stage 1.6F** | W1/W2/W2-0 descriptive conclusion closure | `implemented_locally`, `evidence_collected`, `reviewed` | `Yes` | Offline Tool | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json` | `w2_0_exploratory_20260926T071500Z`; 180 physical source objects; 41 contracts / 27 parents; 31 contracts / 21 parents window-defined; 29 contracts / 19 parents exploratory_described; outcome_seen/exploratory_only 19-parent subset does not support usual natural terminal convergence in [-24h, 0h]; 3/19 negative; 16/19 positive. | `none_from_current_evidence` |'

def require_identical(label, actual, expected):
    if actual != expected:
        stop(f'{label}_template_mismatch')

def validate_roadmap(before, after):
    expected = replace_ranges(before, (
        (*span(before, '* **Stage 1.6F Historical Research State**:', '\n---\n\n## 3. Research Track Matrix'), ROADMAP_HISTORICAL),
        (*span(before, '| **Stage 1.6F (Historical Matched Control & Evidence Expansion)**', '\n---\n\n## 4. Current Active Chain'), ROADMAP_MATRIX),
        (*span(before, '### 4.2 Stage 1.6 Delisting Research & Diagnostic Chain', '\n---\n\n## 5. Completed and Falsified Work'), ROADMAP_CHAIN),
        (*span(before, '4. **Stage 1.6F-W2-0 Delisting Terminal Basis Convergence Hypothesis (Final 24h Window)**:', '\n---\n\n## 6. Current Blockers'), ''),
        (*span(before, '* **Risk Control / Circuit-Breaker Blocker (P1 - Stage 1.6R)**:', '* **Data / Verification Blocker (P3 - Stage 1.5G Live Depth)**:'), ''),
        (*span(before, '### Gate 1: Stage 1.6R Risk-Veto & Circuit-Breaker Specification', '### Gate 3: Stage 1.5G Event-Family Evidence Sufficiency'), ''),
        (*line_span(before, '* **2026-09-25**:'), ROADMAP_W2_LOG + '\n'),
        (*line_span(before, '* **2026-09-26**:'), ROADMAP_W20_LOG + '\n'),
    ))
    require_identical('stage1_6_roadmap_final_document', after, expected)
    for historical in ('Route C1 Price-Only Proxy 7-Day Live Smoke Test', 'Stage 1.4B-Lite Crowding-Only Replay', 'Cross-Sectional Factor Lab Stage A2 (CMOM Factor)'):
        if historical not in after:
            stop(f'historical_falsification_missing:{historical}')
    print('CHECK_OK=roadmap_semantics_and_owned_bytes')

def validate_current_project_state(before, after):
    transition_start = line_span(before, '| **Stage 1.6A - 1.6R**')[0]
    transition_end = line_span(before, '| **Stage 1.6F**')[1]
    expected = before[:transition_start] + PROJECT_STATE_ROW + '\n' + before[transition_end:]
    require_identical('stage1_6_project_state_final_document', after, expected)
    print('CHECK_OK=current_project_state_semantics_and_owned_bytes')

validate_roadmap((baseline / 'roadmap.before').read_text(encoding='utf-8'), Path('docs/roadmap.md').read_text(encoding='utf-8'))
validate_current_project_state((baseline / 'current-project-state.before').read_text(encoding='utf-8'), Path('docs/project-status/current-project-state_CN.md').read_text(encoding='utf-8'))
PY
````

Expected: exit `0`. Each validator independently derives the only allowed complete target document from its reviewed baseline. This preserves every unowned byte and rejects renamed stale sections, alternate counts/states, causal stories, thresholds, exits and any additional prose.

**Step 2: Compare full pre-existing worktree and index provenance.**

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=EXECUTION_BASELINE_DIR_missing}"
cd "$PROJECT_ROOT"
test "$(git rev-parse HEAD)" = "$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")" || { echo 'STOP=git_head_mutated' >&2; exit 1; }
git diff --check -- docs/roadmap.md docs/project-status/current-project-state_CN.md
python3 - "$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")" "$EXECUTION_BASELINE_DIR/preexisting_path_states.jsonl" <<'PY'
import hashlib, json, os, stat, subprocess, sys
from pathlib import Path

base_sha, ledger_name = sys.argv[1:]
targets = {'docs/roadmap.md', 'docs/project-status/current-project-state_CN.md'}

def git_names(*args):
    return set(subprocess.check_output(['git', *args], text=True).splitlines())

def porcelain_xy():
    records = subprocess.check_output(['git', 'status', '--porcelain=v1', '-z', '--untracked-files=all']).split(b'\0')
    result, i = {}, 0
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
    return [dict(zip(('mode', 'blob_sha', 'stage'), record.split(b'\t', 1)[0].decode('ascii').split()))
            for record in raw.split(b'\0') if record]

def snapshot(relative_name, tracked_dirty, staged, untracked, xy):
    path = Path(relative_name)
    kinds = sorted(kind for kind, present in (('tracked_dirty', relative_name in tracked_dirty), ('staged', relative_name in staged), ('untracked', relative_name in untracked)) if present)
    if path.is_symlink():
        worktree_state, worktree_sha256 = 'symlink', hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
        worktree_mode = stat.S_IMODE(path.lstat().st_mode)
    elif path.is_file():
        worktree_state, worktree_sha256 = 'file', hashlib.sha256(path.read_bytes()).hexdigest()
        worktree_mode = stat.S_IMODE(path.lstat().st_mode)
    elif path.exists():
        raise SystemExit(f'STOP=unsupported_preexisting_path_state:{relative_name}')
    else:
        worktree_state, worktree_sha256, worktree_mode = 'tombstone', None, None
    return {'path': relative_name, 'xy': xy.get(relative_name, '--'), 'kinds': kinds, 'worktree_state': worktree_state, 'worktree_sha256': worktree_sha256, 'worktree_mode': worktree_mode, 'index_entries': index_entries(relative_name)}

before = {entry['path']: entry for entry in (json.loads(line) for line in Path(ledger_name).read_text(encoding='utf-8').splitlines() if line)}
tracked_dirty = git_names('diff', '--name-only', base_sha)
staged = git_names('diff', '--cached', '--name-only', base_sha)
untracked = git_names('ls-files', '--others', '--exclude-standard')
xy = porcelain_xy()
after_names = tracked_dirty | staged | untracked | targets
new_paths = after_names - set(before)
if new_paths:
    raise SystemExit(f'STOP=stage1_6_scope_or_permission_violation:new_preexisting_path:{sorted(new_paths)}')
for name, expected in before.items():
    actual = snapshot(name, tracked_dirty, staged, untracked, xy)
    if name in targets:
        if actual['worktree_state'] != 'file':
            raise SystemExit(f'STOP=target_not_regular:{name}')
        if actual['worktree_mode'] != expected['worktree_mode']:
            raise SystemExit(f'STOP=target_worktree_mode_mutated:{name}')
        if actual['index_entries'] != expected['index_entries']:
            raise SystemExit(f'STOP=stage1_6_scope_or_permission_violation:index_mutated:{name}')
    elif actual != expected:
        raise SystemExit(f'STOP=preexisting_provenance_mutated:{name}')
print('CHECK_OK=preexisting_worktree_and_index_exact')
PY
while read -r expected path; do
  actual="$(shasum -a 256 "$path" | awk '{print $1}')"
  test "$actual" = "$expected" || { echo "STOP=stage1_6_conclusion_authority_mismatch:$path" >&2; exit 1; }
done < "$EXECUTION_BASELINE_DIR/authority.sha256"
echo 'CHECK_OK=scope_and_authority_unchanged'
```

Expected: exit `0`; every non-target pre-existing path must retain exact `XY`, kinds, worktree state/SHA/mode and index mode/blob/stage. Both target paths must remain regular non-symlink files with their baseline worktree mode, may change only in content bytes, and must retain exact index entries.

**Step 3: Safety and scanner actual RC.**

```bash
set -euo pipefail
: "${PROJECT_ROOT:?STOP=PROJECT_ROOT_missing}"
cd "$PROJECT_ROOT"
python3 - <<'PY'
from configs.base import RISK_LIVE_TRADING_ENABLED
assert RISK_LIVE_TRADING_ENABLED is False, 'STOP=live_trading_not_disabled'
print('CHECK_OK=live_trading_disabled')
PY
set +e
python3 .agent/tools/anti_shortcut_scan.py \
  src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py \
  src/research/external_signal_shadow/stage1_6f_w2_0_exploratory_terminal_basis_storage.py \
  scripts/external_signal_shadow/run_stage1_6f_w2_0_exploratory_terminal_basis_diagnostic.py
scanner_rc=$?
set -e
printf 'SCANNER_RC=%s\n' "$scanner_rc"
test "$scanner_rc" -eq 0 || { echo 'STOP=anti_shortcut_scan_failed' >&2; exit "$scanner_rc"; }
```

Expected: `SCANNER_RC=0`. The scanner cannot authorize source edits.

**Step 4: Independent code review, then Completion Audit.** Use `requesting-code-review` after Steps 1-3 pass. Its exact scope is the baseline-to-final diffs of the two target documents, both independent semantic outputs, the baseline-derived whole-document equality result, full provenance ledger comparison, `HEAD == BASE_SHA`, audited-source blob binding, independent manifest file/flag verification and scanner RC. If review has any open finding, stop, remediate only within this Plan, and rerun all Task 3 gates. Immediately before handing off to Completion Audit, recheck `test "$(git rev-parse HEAD)" = "$(cat "$EXECUTION_BASELINE_DIR/BASE_SHA")" || STOP=git_head_mutated`. Only a clean code review routes to a fresh independent Completion Audit. Do not commit, push, deploy or run a strategy.

## Plan Self-Review

- Every Delta authority edge maps to a Task 0/Task 3 proof and fail-closed STOP.
- The only writes are the two Delta-whitelisted Markdown files; user-owned pre-existing changes are snapshotted and never reset.
- Strict bundle admission precedes all parent-statistic use; no direct artifact read is authorized.
- Each target is validated separately; only predeclared Stage 1.6 ranges may differ from its reviewed byte copy, while every fact-bearing range must equal its exact normalized template and all pre-existing index entries and target worktree modes remain mechanically bound.
- The Plan removes unsupported claims rather than inventing a strategy, risk-veto, consumer or stage.
- No network, replay, execution, trading, SSH, deployment, commit or push authority is granted.
- Final semantic/scope gates require independent code review before a fresh Completion Audit; a fresh Model B plan review is required before implementation approval.
