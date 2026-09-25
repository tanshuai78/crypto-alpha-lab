# Stage 1.6F-W2 历史价格证据最小补采 Implementation Plan

> For Codex: 仅在独立 Plan review 为 RECOMMEND_APPROVE、且用户另行对本 Plan 精确 SHA 签发 implementation 授权后，使用 executing-plans、test-driven-development 和 execute-approved-plan workflow 逐 Task 实施。本 Plan 不授权网络、运行时、提交或部署。

**目标：** 对冻结的 41 个候选身份实现独立 W2 candidate root 的本地 strict reader 与单次公共归档 collector。它只产生原始字节、Class A 本地重算事实及 Class B producer-attested observation，绝不产生价格 outcome、W2-0 分析、Alpha、PnL 或交易权限。

**架构：** 新 src 模块是唯一 W2 authority/time/request-set/coverage/strict-root validation owner，且无网络、无 scripts import。新前台 CLI 是唯一网络/root writer owner：先通过 W2 authority 与一次性授权门禁，复制 9 个 verified 002 对象，再对冻结的 171 URL 单线程、无重试、无重定向 GET，最后 manifest-last 发布。Completion Audit 是外部严格只读裁判；collector、executor 与 reader 均不写 collection_attestation.json、audit receipt 或 publisher artifact。

**技术栈：** Python stdlib csv, dataclasses, hashlib, json, math, os, pathlib, shutil, tempfile, time, urllib, zipfile；pytest；ruff；anti_shortcut_scan.py；PATH graphify CLI。

---

## Governance And Design Authority

Approved Design:
docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md

Approved Design SHA-256:
11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303

本 Plan 只实现上述 Design。Plan review、Plan approval 和 implementation approval 均不等于 public GET 授权。执行前必须收到独立用户语句：

~~~text
我批准实施 Plan：docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md（SHA-256: <exact-plan-sha>）。
允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。
~~~

即使收到该语句，也不得联网、创建真实 W2 root、执行 --live-public-readonly、提交、推送、部署、SSH/VPS 操作、启动常驻进程、replay、paper/live trading、信号或 outcome/Alpha 解释。真实 GET 还需要与最终 Design/Plan SHA、run ID、171 URL hash 绑定的独立一次性网络授权。

### Frozen Authority Packet

Task 0 在任何 code/test edit 前重算 raw-byte SHA。缺文件、hash 不符、Design 不符或 C/002 authority 不可严格加载均为 STOP=approved_authority_mismatch；不得使用 HEAD、别名 root、复制 manifest 或 synthetic hash 替代。

| Authority | Path | SHA-256 |
| --- | --- | --- |
| Approved W2 Design | docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md | 11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303 |
| Expansion Design | docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md | 1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4 |
| Expansion Plan | docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md | fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d |
| W1 admission Design | docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md | dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097 |
| Parent-cardinality Delta | docs/designs/2026-09-20-external-signal-shadow-lab-stage1-6f-candidate-w1-parent-article-cardinality-correction-delta-design_CN.md | 02945b5aa9989e48b50381876601ff72f7080878e4e5eb7cc6cdc6eaaf8617f9 |
| Canonical 002 manifest | data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002/candidate_manifest.json | b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67 |
| Canonical 002 network record | configs/authorizations/network_auth_expansion_run_20260917_002.json | 8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6 |
| Coverage matrix | tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json | b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8 |
| Shared W1 candidate source | src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py | 81dca38c323a1632e7e1302b8016a40603c970cb16da58ea13108b5a2ae23f3b |
| Existing expansion collector | scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py | 32c8b06e3167b9d2c5010f5efc95e777748f1a53b552731cdf4f192a8262c4dc |

旧 expansion Design 的传递 authority 也必须逐项重算：Parent F Design 87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c；F evidence-to-schema Delta 8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628；F implementation Plan 6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f；REEF manifest 9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f；C completion manifest 226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0；C source-export receipt 07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e；B sealed-export manifest 1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be；F denominator module 84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3；F source module 00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f。Task 0 还必须调用 canonical verify_c_input(...) 和 exact-002 load_verified_candidate_evidence(...)；它们是 upstream 行为证据，不得新建第二个 C/002 parser。

### Rule-12 Routing

| Condition during execution | Required route |
| --- | --- |
| 已有 approved helper 已提供行为但执行者先前遗漏 | BLOCKED_IMPLEMENTATION_DEFECT；仅在白名单内最小修复，并加共享 owner 回归。 |
| 正确行为需要白名单外文件、schema、consumer 或 authorization artifact | BLOCKED_SCOPE_DRIFT；保留证据并停止。 |
| frozen C/002/matrix bytes、shared parser、approved Design 或一次性授权与 Plan 矛盾 | BLOCKED_SPEC_DRIFT；报告 invariant、SSOT path/line、精确 bytes/值及所需 Design/Plan delta。 |

禁止以 get default 隐藏 required authority field、synthetic hash、alternate URL/root、retry/resume/redirect/fallback、src-to-scripts import、同 schema 第二 validator、collection_attestation.json、audit publisher、workspace audit serializer、scheduler、database、observer、W2-0 reducer、replay 或 outcome display 作为 workaround。

## Invariant Map

| Design invariant | Production owner | Mechanical proof / negative mutation | Fail-closed outcome |
| --- | --- | --- | --- |
| INV-W2E01 | W2 source preflight + CLI authority gate | wrong Design/Plan/auth SHA, wrong run ID, false permission, FETCH hash mutation; transport call count remains zero | STOP=approved_authority_mismatch or STOP=w2_network_authorization_invalid |
| INV-W2E02 | W2 temporal derivation | canonical C/002; remove unproven identity or mutate Tsettle<=Tpub | STOP=w2_temporal_authority_invalid |
| INV-W2E03 | W2 request-set derivation | 41/27, 31/21, 10 unproven, 180/9/171 and URL hashes; URL/date/host mutation | STOP=w2_request_set_mismatch |
| INV-W2E04 | CLI copy path + reader | copy nine real objects; source hash/status/symlink mutation; mutate copied inode without changing source | root rejected; zero fallback GET |
| INV-W2E05 | CLI transport adapter | injected 3xx/404/429/timeout/short-body/oversize and call count | terminal state or STOP=w2_resource_budget_exceeded |
| INV-W2E06 | parser wrapper + reader | multi-member/CRC/path/header-only/nonfinite/nonhourly/close-time/duplicate mutations | archive_invalid/csv_invalid; no coverage rows |
| INV-W2E07 | coverage reducer | AIA/PORT3 window, t=a/t=b, UTC crossing, missing hour, zero Index close | no interpolation; exact status |
| INV-W2E08 | atomic lifecycle | write/rename/fsync/free-space/cleanup fault injection | forensic root only; no final manifest |
| INV-W2E09 | strict reader | manifest key/type/status/count/HTTP/nullability/root-state mutation | root rejected; no GET claim |
| INV-W2E10/11 | source/CLI topology | old reader rejects W2; 13 false flags; no reverse import/duplicate validator | STOP=w2_production_wiring_invalid |
| INV-W2E12 | external audit handoff | factual handoff checklist + static absence of audit writer/publisher | no W2-0 admission without external complete artifact |
| INV-W2E13 | outcome boundary | no OHLC/basis/return/MAE/MFE output before later receipt | STOP=w2_outcome_boundary_violation |

## Allowed Change Scope

Allowed implementation paths:
- configs/base.py - only the five W2 resource constants.
- src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py - W2 no-network authority, derivation, coverage and strict reader.
- scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py - one-shot CLI, streaming transport, copy/write lifecycle, manifest-last owner.

Allowed verification paths:
- tests/research/external_signal_shadow/stage1_6f_w2_test_support.py - canonical mirrored C/002 fixture, independent copy and mutation helpers.
- tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py
- tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py

Allowed documentation paths:
- none

Allowed generated/runtime artifacts:
- data/external_signal_shadow/stage1_6f/w2_evidence_candidates/<run_id>/** - only after separate public-GET authorization; ignored, never committed.
- graphify-out/** - generated only, ignored, never committed.
- Git metadata plan-execution/<run_id> - baseline evidence only, never committed.

Affected but unchanged:
- src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py - reuse only parse_and_validate_csv(), compute_logical_archive_record_id(), compute_physical_source_object_id().
- src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py - reuse only reconstruct_denominator(...).
- src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py - reuse only verify_c_input(...), retained-fact readers and types.
- scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py - reference topology only; unmodified.
- existing W1/REEF readers/runners/storage/tests/root - incompatible W2 schema remains deliberate.
- all parent Design/Plan bytes, C/B roots, 002 root, matrix, old network authorization, runbooks, roadmap, Stage 1.5/1.6D/1.6E-B, risk/strategy/execution modules.

Forbidden:
- Any mutation outside listed paths, including Design/Plan bytes.
- Any real network request before separately approved authorization, credentials, proxy/cookie/netrc, SSH/VPS, daemon, deployment, commit or push.
- Any repository-wide format/autofix, git clean, git reset, automatic revert or destructive cleanup.
- Any W2-0 calculation, raw-price/outcome display, Alpha/PnL/cost/execution/replay/paper/live claim or change to RISK_LIVE_TRADING_ENABLED.
- Any audit artifact writer, collection attestation, audit publisher, post-audit serializer or Completion Auditor workspace mutation.

---

## Task 0: Freeze Execution Baseline, Authorities, Scope, And Blind Inputs

**Invariants:** all.

**Files:** modify none.

### Step 1: Require implementation authorization and record workflow-owned baseline

Run only after Plan review and exact user implementation approval. This is sole owner of BASE_SHA, EXECUTION_RUN_ID, EXECUTION_BASELINE_DIR, status/diff/index snapshots and pre-existing provenance.

~~~bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
test -n "$APPROVED_PLAN_SHA256" || { echo 'STOP=approved_plan_sha_missing' >&2; exit 1; }
APPROVED_PLAN_PATH=docs/plans/2026-09-25-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-implementation-plan_CN.md
test "$(shasum -a 256 "$APPROVED_PLAN_PATH" | awk '{print $1}')" = "$APPROVED_PLAN_SHA256" || {
  echo 'STOP=approved_authority_mismatch:plan' >&2
  exit 1
}
BASE_SHA=$(git rev-parse HEAD)
EXECUTION_RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
EXECUTION_BASELINE_DIR=$(git rev-parse --git-path "plan-execution/$EXECUTION_RUN_ID")
mkdir -p "$EXECUTION_BASELINE_DIR"
git status --short --untracked-files=all > "$EXECUTION_BASELINE_DIR/status.txt"
git diff --binary > "$EXECUTION_BASELINE_DIR/worktree.patch"
git diff --cached --binary > "$EXECUTION_BASELINE_DIR/index.patch"
git ls-files --others --exclude-standard > "$EXECUTION_BASELINE_DIR/untracked-paths.txt"
while IFS= read -r target_path; do
  test -z "$target_path" || shasum -a 256 "$target_path"
done < "$EXECUTION_BASELINE_DIR/untracked-paths.txt" > "$EXECUTION_BASELINE_DIR/untracked-sha256.txt"
git ls-files -s -z | shasum -a 256 | awk '{print $1}' > "$EXECUTION_BASELINE_DIR/index.sha256"
{
  git diff --name-only "$BASE_SHA"
  git diff --cached --name-only "$BASE_SHA"
  git ls-files --others --exclude-standard
} | LC_ALL=C sort -u > "$EXECUTION_BASELINE_DIR/preexisting-paths.txt"
python3 - "$BASE_SHA" \
  "$EXECUTION_BASELINE_DIR/preexisting-paths.txt" \
  "$EXECUTION_BASELINE_DIR/preexisting-path-states.jsonl" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

base_sha, paths_name, states_name = sys.argv[1:]

def git_names(*args):
    return set(subprocess.check_output(["git", *args], text=True).splitlines())

tracked_dirty = git_names("diff", "--name-only", base_sha)
staged = git_names("diff", "--cached", "--name-only", base_sha)
untracked = git_names("ls-files", "--others", "--exclude-standard")
paths = sorted(tracked_dirty | staged | untracked)
Path(paths_name).write_text("\n".join(paths) + ("\n" if paths else ""), encoding="utf-8")

with Path(states_name).open("w", encoding="utf-8") as out:
    for relative_name in paths:
        path = Path(relative_name)
        kinds = sorted(
            kind for kind, present in (
                ("tracked_dirty", relative_name in tracked_dirty),
                ("staged", relative_name in staged),
                ("untracked", relative_name in untracked),
            ) if present
        )
        if path.is_symlink():
            state = "symlink"
            sha256 = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
        elif path.is_file():
            state = "file"
            sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.exists():
            raise SystemExit(f"STOP=unsupported_preexisting_path_state:{relative_name}")
        else:
            state = "tombstone"
            sha256 = None
        out.write(json.dumps(
            {"path": relative_name, "kinds": kinds, "state": state, "sha256": sha256},
            sort_keys=True,
        ) + "\n")
PY
python3 - "$EXECUTION_BASELINE_DIR/preexisting-path-states.jsonl" <<'PY'
import json
import sys
from pathlib import Path

allowed = {
    "configs/base.py",
    "src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py",
    "scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py",
    "tests/research/external_signal_shadow/stage1_6f_w2_test_support.py",
    "tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py",
}
baseline_paths = {
    json.loads(line)["path"]
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    if line
}
overlap = sorted(baseline_paths & allowed)
if overlap:
    raise SystemExit(f"STOP=preexisting_whitelist_overlap:{overlap}")
print("CHECK_OK=preexisting_whitelist_disjoint")
PY
printf '%s\n' "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/base_sha.txt"
printf 'CHECK_OK=execution_baseline:%s\n' "$EXECUTION_BASELINE_DIR"
~~~

Expected: CHECK_OK preexisting whitelist disjoint, then CHECK_OK execution baseline. preexisting-path-states.jsonl is the authoritative pre-existing provenance ledger: every path has exact kinds (tracked_dirty/staged/untracked), state (file/symlink/tombstone) and byte/target SHA. Pre-existing untracked/dirty paths are evidence, never overwritten, staged, reverted or attributed to this Task. A pre-existing path overlapping the implementation whitelist is STOP=preexisting_whitelist_overlap before Task 1 RED, rather than a permission to mutate it. Task 5 repeats this check against final state.

### Step 2: Recompute authority and safe configuration facts

~~~bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
cat > "$EXECUTION_BASELINE_DIR/frozen-authority.tsv" <<'LEDGER'
11f5e9a253e2b721301e1c12aedd35bc6a01aaa7d6a05b5d6616c6e876eec303 docs/designs/2026-09-23-external-signal-shadow-lab-stage1-6f-w2-minimal-historical-evidence-expansion-design_CN.md
1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4 docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md
fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md
dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097 docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md
02945b5aa9989e48b50381876601ff72f7080878e4e5eb7cc6cdc6eaaf8617f9 docs/designs/2026-09-20-external-signal-shadow-lab-stage1-6f-candidate-w1-parent-article-cardinality-correction-delta-design_CN.md
b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67 data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002/candidate_manifest.json
8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6 configs/authorizations/network_auth_expansion_run_20260917_002.json
b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8 tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json
81dca38c323a1632e7e1302b8016a40603c970cb16da58ea13108b5a2ae23f3b src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py
32c8b06e3167b9d2c5010f5efc95e777748f1a53b552731cdf4f192a8262c4dc scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py
87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md
8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628 docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md
6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md
9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json
226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0 data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json
07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/source_export_receipt.json
1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090/sealed_export_manifest.json
84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3 src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py
00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py
LEDGER
while IFS=' ' read -r expected target_path; do
  actual=$(shasum -a 256 "$target_path" | awk '{print $1}')
  test "$actual" = "$expected" || { echo "STOP=approved_authority_mismatch:$target_path" >&2; exit 1; }
done < "$EXECUTION_BASELINE_DIR/frozen-authority.tsv"
python3 - <<'PY'
import ast
from pathlib import Path
targets = {'EXCHANGE_TIMEOUT_MS', 'EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT', 'RISK_LIVE_TRADING_ENABLED'}
tree = ast.parse(Path('configs/base.py').read_text(encoding='utf-8'))
values = {
    node.targets[0].id: ast.literal_eval(node.value)
    for node in tree.body
    if isinstance(node, ast.Assign) and len(node.targets) == 1
    and isinstance(node.targets[0], ast.Name) and node.targets[0].id in targets
}
assert values == {
    'EXCHANGE_TIMEOUT_MS': 10_000,
    'EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT': 'crypto-alpha-lab-research-readonly/0.1',
    'RISK_LIVE_TRADING_ENABLED': False,
}
print('CHECK_OK=authorities_and_safety_config_frozen')
PY
~~~

Expected: CHECK_OK authorities and config. Do not use path as the loop variable: zsh binds it to PATH.

### Step 3: Prove canonical positive inputs and non-network gates

~~~bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
command -v graphify >/dev/null || { echo 'STOP=graphify_workflow_contract_unavailable' >&2; exit 1; }
graphify --help >/dev/null || { echo 'STOP=graphify_workflow_contract_unavailable' >&2; exit 1; }
git check-ignore -v graphify-out/.stage1_6f_w2_plan_probe >/dev/null || { echo 'STOP=graphify_output_not_ignored' >&2; exit 1; }
git check-ignore -v data/external_signal_shadow/stage1_6f/w2_evidence_candidates/.stage1_6f_w2_plan_probe >/dev/null || { echo 'STOP=w2_runtime_root_not_ignored' >&2; exit 1; }
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from pathlib import Path
from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import load_verified_candidate_evidence
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import verify_c_input
p = Path.cwd()
c = p / 'data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z'
b = p / 'data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090'
r = p / 'data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002'
d = p / 'docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md'
plan = p / 'docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md'
a = p / 'configs/authorizations/network_auth_expansion_run_20260917_002.json'
assert verify_c_input(project_root=p, completed_root=c, source_export=b)
v = load_verified_candidate_evidence(project_root=p, candidate_root=r, approved_design_path=d,
    approved_design_sha='1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4',
    approved_plan_path=plan, approved_plan_sha='fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d',
    network_authorization_path=a, network_authorization_sha='8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6')
assert len(v.cohort) == 41
print('CHECK_OK=canonical_c_and_002_inputs')
PY
~~~

Expected: no network request and CHECK_OK canonical C/002. Do not print/inspect raw price values.

### Step 4: Record scope before RED

~~~bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
{
  git diff --name-only "$BASE_SHA"
  git diff --cached --name-only "$BASE_SHA"
  git ls-files --others --exclude-standard
} | LC_ALL=C sort -u > "$EXECUTION_BASELINE_DIR/pre-task-paths.txt"
printf 'CHECK_OK=task0_scope_recorded\n'
~~~

Expected: only pre-existing paths recorded. Required unlisted mutation triggers Rule-12 before RED.

---

## Task 1: Add W2 Authority, Temporal, Request-Set And Resource Contracts

**Invariants:** INV-W2E01, INV-W2E02, INV-W2E03, INV-W2E10, INV-W2E13.

**Files:**
- Create: src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py
- Create: tests/research/external_signal_shadow/stage1_6f_w2_test_support.py
- Create: tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py
- Modify: configs/base.py

**Interfaces:**
- Consumes: canonical verify_c_input(...), reconstruct_denominator(...), load_verified_candidate_evidence(...), matrix and shared pure parser/ID functions.
- Produces: W2EvidenceSourceError, W2AuthorityInputs, W2RequestSet, derive_w2_authority_inputs(...), derive_w2_request_set(...), validate_w2_network_authorization(...). No function returns, logs or formats price outcomes.

The test-support fixture canonical_w2_inputs returns an exact mapping with project_root, c_completed_root, b_source_export, canonical_002_root, coverage_matrix, approved_design_path/SHA, approved_plan_path/SHA and a temporary one-time authorization path/SHA. Its mirror is built only from the 19 frozen authority bytes and canonical C/B/002 directories.

### Step 1: Write RED tests with canonical mirror and single-point mutation

Fixture support links-or-copies real authority bytes. On os.link() OSError use shutil.copy2(). Before negative mutation unlink mirror file so it cannot alter authority inode.

~~~python
def test_w2_request_set_is_exact_and_outcome_blind(canonical_w2_inputs):
    authority = source.derive_w2_authority_inputs(**canonical_w2_inputs)
    request_set = source.derive_w2_request_set(authority)
    assert (len(authority.denominator_records), authority.distinct_parent_count) == (41, 27)
    assert (authority.window_defined_count, authority.window_parent_count) == (31, 21)
    assert authority.settlement_time_unproven_count == 10
    assert (len(request_set.logical_records), len(request_set.physical_records)) == (180, 180)
    assert (len(request_set.reuse_ids), len(request_set.fetch_ids)) == (9, 171)
    assert request_set.all_urls_sha256 == '3b9ab69a8c1236cab59f161636ae9e4136465ca599d735ef65e37fd2cc574a46'
    assert request_set.reuse_urls_sha256 == '9773f11e316ce480651b0debf6258fefbd39a1ee9bdc2d6bdd838484704ed405'
    assert request_set.fetch_urls_sha256 == '6eac006f8854a17a2d78b4306c03da6f28528aba58ffcfafd6b5f078d4ed7058'
    assert not hasattr(request_set, 'prices')


def test_w2_temporal_or_url_mutation_fails_closed(canonical_w2_inputs, mutate_mirror_file):
    matrix = canonical_w2_inputs['project_root'] / 'tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json'
    mutate_mirror_file(matrix, matrix.read_bytes().replace(b'indexPriceKlines', b'evilHostKlines', 1))
    with pytest.raises(source.W2EvidenceSourceError, match='STOP=w2_request_set_mismatch'):
        source.derive_w2_authority_inputs(**canonical_w2_inputs)
~~~

Also test one altered URL host/query/fragment, removed URL, removed unproven identity, Tsettle<=Tpub, invalid run ID, missing/false authorization field and exact 13-false mapping. No handcrafted C/002 dict is valid positive fixture.

### Step 2: Run RED

~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  -k 'request_set or temporal or authorization or outcome_blind'
~~~

Expected: FAIL because W2 module does not exist; no socket call and no output root.

### Step 3: Implement minimal config and source-only contract

Add only these constants to a dedicated Stage 1.6F-W2 block:

~~~python
EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES = 1_048_576
EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES = 4_194_304
EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES = 65_536
EXTERNAL_SIGNAL_STAGE1_6F_W2_MIN_FREE_BYTES = 4_294_967_296
EXTERNAL_SIGNAL_STAGE1_6F_W2_REQUEST_INTERVAL_SECONDS = 1
~~~

Implement:

~~~python
@dataclass(frozen=True)
class W2AuthorityInputs:
    project_root: Path
    verified_c: VerifiedCInput
    verified_002: VerifiedCandidateEvidence
    denominator_records: tuple[dict[str, object], ...]
    distinct_parent_count: int
    window_defined_count: int
    window_parent_count: int
    settlement_time_unproven_count: int
    coverage_matrix_path: Path


@dataclass(frozen=True)
class W2RequestSet:
    denominator_records: tuple[dict[str, object], ...]
    logical_records: tuple[dict[str, object], ...]
    physical_records: tuple[dict[str, object], ...]
    reuse_ids: frozenset[str]
    fetch_ids: frozenset[str]
    all_urls_sha256: str
    reuse_urls_sha256: str
    fetch_urls_sha256: str


def derive_w2_request_set(authority: W2AuthorityInputs) -> W2RequestSet:
    """Derive frozen W2 metadata only; never inspect/output price outcomes."""


def validate_w2_network_authorization(
    *, authorization_path: Path, authorization_sha256: str,
    design_path: Path, design_sha256: str, plan_path: Path,
    plan_sha256: str, run_id: str, request_set: W2RequestSet,
) -> dict[str, object]:
    """Require exact one-time W2 authorization; never create it."""
~~~

derive_w2_authority_inputs(...) uses canonical C/002 loaders, retains all 41 identities, derives Tpub/Tsettle only from retained facts, preserves 10 settlement_time_unproven, selects only w2_settlement_24h with klines_1h/index_price_1h/mark_price_1h, and requires 180 logical/physical, 31 temporal-valid, 21 parents and the three fixed URL hashes. Authorization requires exact Design 7.1 fields and all 13 false flags.

### Step 4: Run GREEN

~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  -k 'request_set or temporal or authorization or outcome_blind'
ruff check configs/base.py \
  src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py \
  tests/research/external_signal_shadow/stage1_6f_w2_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py
~~~

Expected: PASS and ruff RC 0, zero network calls. Authority count/hash drift is STOP=BLOCKED_SPEC_DRIFT, not a tuning reason.

### Step 5: Task scope and scanner gate

~~~bash
export GIT_CONFIG_GLOBAL=/dev/null
git diff --name-only "$BASE_SHA"
git diff --cached --name-only "$BASE_SHA"
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA" \
  src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py \
  tests/research/external_signal_shadow/stage1_6f_w2_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py
~~~

Expected: only Task 1 whitelist paths. Record scanner actual RC and every warning disposition; nonzero RC stops this Task.

---

## Task 2: Implement W2 Physical Schema, Coverage, And Strict Reader

**Invariants:** INV-W2E04, INV-W2E06, INV-W2E07, INV-W2E08, INV-W2E09, INV-W2E10, INV-W2E11.

**Files:**
- Modify: src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py
- Modify: tests/research/external_signal_shadow/stage1_6f_w2_test_support.py
- Modify: tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py

**Interfaces:**
- Consumes: Task 1 W2AuthorityInputs, W2RequestSet and shared parser/ID helpers.
- Produces: validate_w2_zip_and_csv(...), compute_w2_metric_coverages(...), validate_w2_candidate_root_core(...), load_verified_w2_evidence(...); only Class A local facts.

The test-support canonical_w2_root contains candidate_root, authority_kwargs and single_point_mutation(name). single_point_mutation must copy the root, unlink only its target before changing it, and support exactly extra_manifest_key, forged_url, http_bool, wrong_member, header_only_csv, duplicate_open_time and root_state_all_complete.

### Step 1: Write RED strict-reader and coverage tests

Use Task 1 mirror to independently copy nine real 002 ZIP/CSV bytes into W2 test root. Build manifest only via canonical test constructors. The 171 unknown objects are explicit transport_inconclusive fixture outcomes, not synthetic successful downloads.

~~~python
def test_strict_reader_accepts_canonical_w2_gaps_root(canonical_w2_root):
    verified = source.load_verified_w2_evidence(**canonical_w2_root.authority_kwargs)
    assert verified.candidate_root_state == 'collection_terminal_with_evidence_gaps'
    assert len(verified.denominator_records) == 41
    assert len(verified.logical_archive_records) == 180
    assert len(verified.physical_source_objects) == 180
    assert len(verified.metric_window_coverages) == 123


@pytest.mark.parametrize('mutation,stop', [
    ('extra_manifest_key', 'w2_root_invalid:manifest_keys'),
    ('forged_url', 'w2_root_invalid:physical_url'),
    ('http_bool', 'w2_root_invalid:http_status_type'),
    ('wrong_member', 'w2_root_invalid:zip_member_name'),
    ('header_only_csv', 'w2_root_invalid:csv_invalid'),
    ('duplicate_open_time', 'w2_root_invalid:hour_grid'),
    ('root_state_all_complete', 'w2_root_invalid:candidate_root_state'),
])
def test_strict_reader_rejects_single_point_mutations(canonical_w2_root, mutation, stop):
    mutated = canonical_w2_root.single_point_mutation(mutation)
    with pytest.raises(source.W2EvidenceSourceError, match=stop):
        source.load_verified_w2_evidence(**mutated.authority_kwargs)
~~~

Add coverage tests for AIA/PORT3 truncation, t=a, t=b, UTC crossing, missing point, empty complete-bar grid, zero Index close and referenced physical failure. Temporal-unproven coverage has null counts and temporal_unproven, never zero/observed.

### Step 2: Run RED

~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  -k 'strict_reader or coverage or zip or csv or copied'
~~~

Expected: FAIL because W2 schema/reader does not exist.

### Step 3: Implement a single strict schema/reader owner

~~~python
@dataclass(frozen=True)
class VerifiedW2Evidence:
    run_id: str
    completed_root: Path
    manifest: dict[str, object]
    denominator_records: tuple[dict[str, object], ...]
    logical_archive_records: tuple[dict[str, object], ...]
    physical_source_objects: tuple[dict[str, object], ...]
    metric_window_coverages: tuple[dict[str, object], ...]
    candidate_root_state: str


def load_verified_w2_evidence(
    *, project_root: Path, candidate_root: Path,
    approved_design_path: Path, approved_design_sha: str,
    approved_plan_path: Path, approved_plan_sha: str,
    network_authorization_path: Path, network_authorization_sha: str,
) -> VerifiedW2Evidence:
    """Recompute Class A only; never assert a remote GET occurred."""
~~~

Require canonical W2 root path with no symlink and only zips/csvs/manifest. Re-derive authority/denominator/time/request set before accepting every exact manifest key/type/state/path/hash/length. Require all 180 physical records and Design 9 nullability:

- copied_verified_002 has exact old source manifest/hash/ID, ordinary files, attempt 0 and null request/response.
- network_get has attempt 1 and exact state/HTTP/time relation; reader checks only local consistency, not remote proof.
- Reopen ZIP with ZipFile.open fixed chunks, CRC and caps; never extract/extractall/testzip/whole-member read.
- Reuse shared parser then W2 nonempty/hourly/date/close-time/monotonic/unique checks before slicing.
- Recompute G/C separately; never interpolate/fill/deduplicate. zero_index_close_count is only a count.

Return only IDs, paths, hashes, status/count metadata and validation-only rows. Do not print/export OHLC or derived values.

### Step 4: Run GREEN and unchanged-consumer regression

~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_evidence_source.py -v
~~~

Expected: PASS. The old exact-002 reader remains exact-002 only; W2 is not added to W1/REEF consumers.

### Step 5: Prove no reverse import, duplicate validator, or outcome output

~~~bash
set -euo pipefail
! rg -n 'from scripts\.|import scripts\.' src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py
! rg -n 'collection_attestation|audit_receipt_writer|audit.?publisher|W2-0|alpha_candidate|alpha_validated|MAE|MFE|basis|price_return|gross_return' \
  src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py
printf 'CHECK_OK=single_reader_and_outcome_boundary\n'
~~~

Expected: CHECK_OK single reader and outcome boundary. Any old consumer modification is STOP=BLOCKED_SCOPE_DRIFT.

---

## Task 3: Implement One-Shot Collector, Streaming Transport, And Manifest-Last Lifecycle

**Invariants:** INV-W2E01, INV-W2E04, INV-W2E05, INV-W2E06, INV-W2E08, INV-W2E09, INV-W2E11, INV-W2E13.

**Files:**
- Create: scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py
- Create: tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py
- Modify: tests/research/external_signal_shadow/stage1_6f_w2_test_support.py

**Interfaces:**
- Consumes: Task 1/2 source APIs and resource constants.
- Produces: execute_w2_collection_run(...), parse_args(...), main(...); CLI is sole network/root writer owner and never produces audit artifact.

The test-support module defines FakeResponse(status, body, headers), whose read(size) returns no more than size bytes and whose close() is a no-op; make_transport(event) returns that response or raises TimeoutError for timeout; expected_status_or_stop(status) is pytest.raises only when status begins with STOP= and contextlib.nullcontext otherwise. These are test-only transport doubles, never production evidence.

### Step 1: Write RED injected-transport, production-opener, copy, crash and CLI tests

Tests inject a callable/response object; no urllib opener reaches the network. Positive test copies nine canonical 002 objects and supplies exactly 171 lexicographically ordered explicit transport failures to form a legal gaps root.

~~~python
def test_offline_collector_writes_manifest_last_and_preserves_copy_source(canonical_w2_inputs, tmp_path):
    calls = []
    def transport(url):
        calls.append(url)
        return FakeResponse(status=404, body=b'', headers={})
    result = collector.execute_w2_collection_run(
        **canonical_w2_inputs,
        output_root=tmp_path / 'data/external_signal_shadow/stage1_6f/w2_evidence_candidates',
        run_id='w2_test_001', transport=transport,
    )
    assert len(calls) == 171
    assert result['candidate_root_state'] == 'collection_terminal_with_evidence_gaps'
    assert (result['candidate_root'] / 'candidate_manifest.json').is_file()
    assert canonical_w2_inputs['canonical_002_manifest_sha_before'] == canonical_w2_inputs['canonical_002_manifest_sha_after']()
~~~

The injected path proves collection lifecycle only. Add separate offline production-path tests that never contact a host:

~~~python
def test_public_archive_opener_refuses_proxy_redirect_cookie_and_auth():
    opener = collector.build_public_archive_opener()
    assert any(
        isinstance(handler, urllib.request.ProxyHandler) and handler.proxies == {}
        for handler in opener.handlers
    )
    assert any(isinstance(handler, collector.NoRedirectHandler) for handler in opener.handlers)
    redirect_handlers = [
        handler for handler in opener.handlers
        if isinstance(handler, urllib.request.HTTPRedirectHandler)
    ]
    assert len(redirect_handlers) == 1
    assert isinstance(redirect_handlers[0], collector.NoRedirectHandler)
    forbidden = (
        urllib.request.HTTPCookieProcessor,
        urllib.request.HTTPBasicAuthHandler,
        urllib.request.HTTPDigestAuthHandler,
        urllib.request.ProxyBasicAuthHandler,
        urllib.request.ProxyDigestAuthHandler,
    )
    assert not any(isinstance(handler, forbidden) for handler in opener.handlers)


def test_real_transport_builds_production_opener_and_attempts_exactly_once(monkeypatch):
    calls = []
    class SpyOpener:
        def open(self, request, *, timeout):
            calls.append((request, timeout))
            raise urllib.error.HTTPError(request.full_url, 302, "redirect", {}, None)
    monkeypatch.setattr(collector, "build_public_archive_opener", lambda: SpyOpener())
    with pytest.raises(urllib.error.HTTPError) as raised:
        collector.open_public_archive_get(EXACT_FETCH_URL)
    assert raised.value.code == 302
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.get_method() == "GET"
    assert request.full_url == EXACT_FETCH_URL
    assert request.get_header("User-agent") == EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT
    assert timeout == EXCHANGE_TIMEOUT_MS / 1000.0


def test_uninjected_collector_routes_fetches_to_production_transport(monkeypatch, canonical_w2_inputs, tmp_path):
    calls = []
    def production_transport(url):
        calls.append(url)
        return FakeResponse(status=404, body=b"", headers={})
    monkeypatch.setattr(collector, "open_public_archive_get", production_transport)
    collector.execute_w2_collection_run(
        **canonical_w2_inputs,
        output_root=tmp_path / "data/external_signal_shadow/stage1_6f/w2_evidence_candidates",
        run_id="w2_test_002",
        transport=None,
    )
    assert calls == canonical_w2_inputs["fetch_urls_lexicographic"]
~~~

The second test calls the real production helper with only its opener monkeypatched. The third proves the un-injected collector branch routes every FETCH URL through that helper. Together they prove the exact GET URL/method, frozen timeout/User-Agent, one request maximum and terminal 3xx behavior without a real GET.

Add isolated tests for 404, 429, timeout, short body, oversize, wrong auth before mkdir/transport, source copied hash/status/symlink failure with zero GET, <=171 calls, stream chunk/cap, archive-invalid retention, csv-invalid retention, atomic write/directory fsync/cleanup/free-space fault, collision, post-manifest reader failure and no resume/repair.

### Step 2: Run RED

~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py -v
~~~

Expected: FAIL because W2 CLI/collector does not exist; no project runtime root created.

### Step 3: Implement smallest dedicated stdlib collector

~~~python
def execute_w2_collection_run(
    *, project_root: Path, c_completed_root: Path, b_source_export: Path,
    canonical_002_root: Path, coverage_matrix: Path, output_root: Path,
    run_id: str, approved_design_path: Path, approved_design_sha: str,
    approved_plan_path: Path, approved_plan_sha: str,
    network_authorization_path: Path, network_authorization_sha: str,
    transport: Callable[[str], ResponseLike] | None = None,
) -> dict[str, object]:
    """One front-end run; caller supplies separately authorized transport."""


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def build_public_archive_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirectHandler(),
    )


def open_public_archive_get(url: str) -> ResponseLike:
    opener = build_public_archive_opener()
    request = urllib.request.Request(
        url,
        headers={"User-Agent": EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT},
        method="GET",
    )
    return opener.open(request, timeout=EXCHANGE_TIMEOUT_MS / 1000.0)


def main(argv: list[str] | None = None) -> int:
    """Require --live-public-readonly and exact authority arguments before transport."""
~~~

Fixed sequence:

1. Validate Design/Plan/auth raw bytes, exact fields, run ID, false permission flags and frozen request set before connection/root; invalid input has zero calls.
2. Check constants/free bytes; exclusively mkdir canonical W2 root with only zips and csvs.
3. Strict-load 002; copy nine IDs through .part, flush/fsync/rename/directory fsync, read back and prove source SHA unchanged. Record attempt 0 and null request/response.
4. Iterate 171 FETCH URLs lexicographically. When transport is None, real transport calls open_public_archive_get(), which constructs build_public_archive_opener() for each permitted attempt and issues one stdlib HTTPS GET with default TLS validation and frozen user agent/timeout. The opener must contain ProxyHandler({}) and NoRedirectHandler, and must contain no cookie/basic/digest/proxy-auth/netrc handler. No HEAD/retry/redirect/mirror/host substitution/authenticated proxy/cookie/netrc. Enforce one-second start-to-start.
5. Stream at most CHUNK_BYTES; one additional byte above cap fails. Preserve only Design-permitted bytes/status. Failed physical objects never contribute rows.
6. Aggregate 41/180/180/123; atomically publish manifest last. Reopen through load_verified_w2_evidence(...) before return. Fatal local I/O never publishes manifest.

Request fields are producer_attested_runtime_observation, not independent HTTP proof.

### Step 4: Run GREEN without network

~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py -v
ruff check scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py
~~~

Expected: PASS and ruff RC 0; collector-lifecycle tests use injected transport, while production transport tests monkeypatch only opener.open/build_public_archive_opener and make no real GET. Do not invoke live-public-readonly outside separately approved GET.

### Step 5: Prove transport/audit-writer absence

~~~bash
set -euo pipefail
! rg -n 'retry|urlopen\(|requests\.|httpx\.|extractall|\.extract\(|testzip\(|zf\.read\(' \
  scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py
! rg -n 'collection_attestation|audit_receipt|audit.?publisher|subprocess|tmux|ssh|socket\.create_connection' \
  scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py
rg -n 'def build_public_archive_opener|ProxyHandler\(\{\}\)|class NoRedirectHandler|def open_public_archive_get' \
  scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py
rg -n 'test_public_archive_opener_refuses_proxy_redirect_cookie_and_auth|test_real_transport_builds_production_opener_and_attempts_exactly_once|test_uninjected_collector_routes_fetches_to_production_transport' \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py
printf 'CHECK_OK=transport_and_audit_writer_absence\n'
~~~

Expected: CHECK_OK transport/audit-writer absence. The RED/GREEN opener tests, not this text check alone, prove proxy/redirect/auth/cookie isolation and one-attempt 3xx behavior. Need for retry/redirect/proxy/new family/more than 171 requests is STOP=BLOCKED_SPEC_DRIFT.

---

## Task 4: Complete CLI Gates, Production Wiring, And External-Audit Handoff

**Invariants:** INV-W2E09, INV-W2E10, INV-W2E11, INV-W2E12, INV-W2E13.

**Files:**
- Modify: scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py
- Modify: tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py
- Modify: tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py

### Step 1: Write RED CLI/audit separation tests

~~~python
def test_cli_requires_explicit_public_readonly_and_never_self_attests(monkeypatch, canonical_w2_inputs):
    def fail_if_called(*args, **kwargs):
        raise AssertionError('collector must not dispatch')
    monkeypatch.setattr(collector, 'execute_w2_collection_run', fail_if_called)
    assert collector.main(canonical_w2_inputs['argv_without_live_flag']) != 0
    assert collector.main(canonical_w2_inputs['argv_with_false_network_permission']) != 0
    text = Path(collector.__file__).read_text(encoding='utf-8')
    assert 'collection_attestation' not in text
    assert 'audit_receipt_writer' not in text
    assert 'audit publisher' not in text
~~~

Also test exact external SHA before dispatch, nonzero exit after reader failure, metadata-only CLI output, W1/REEF modules do not import W2 and W2 source never imports scripts.

### Step 2: Run RED

~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py \
  -k 'cli or self_attests or wiring or outcome'
~~~

Expected: FAIL until CLI gate/absence checks exist.

### Step 3: Implement CLI and factual handoff contract

Parser requires project root, C root, B root, canonical 002 root, matrix, output root, run ID, approved Design path/SHA, approved Plan path/SHA, network authorization path/SHA and --live-public-readonly.

Before dispatch require explicit flag, exact SHA and public_archive_get_allowed=true. Otherwise exit nonzero before root/transport. Output only run/root/manifest identifiers, root state, counts/statuses and explicit Class B producer-attested label; never raw CSV/OHLC/outcome.

The factual handoff to a future independent auditor is not a repository artifact and not a self-verdict. It includes Design/Plan/network auth path+SHA; BASE_SHA; baseline dir; run/root/manifest SHA; actual CLI argv; source allowlist SHA; configs/base.py SHA; Git HEAD; scanner command/actual RC; runtime/index/untracked scope evidence; producer-attested network_attempt_count=171, FETCH count=171 and no-retry/no-redirect assertion.

Do not serialize this handoff to workspace/root. A fresh Completion Auditor independently returns a read-only external complete/incomplete/blocked artifact. Only future W2-0 may bind its path+SHA.

### Step 4: Run GREEN and compatibility regressions

~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_evidence_source.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py -v
~~~

Expected: PASS without real GET; old 002/REEF behavior unchanged.

### Step 5: Targeted producer/consumer topology proof

~~~bash
set -euo pipefail
graphify query 'load_verified_w2_evidence' | tee "$EXECUTION_BASELINE_DIR/graphify-w2-reader-query.txt"
graphify query 'execute_w2_collection_run' | tee "$EXECUTION_BASELINE_DIR/graphify-w2-collector-query.txt"
rg -n 'load_verified_w2_evidence|execute_w2_collection_run|stage1_6f_w2_evidence_source' src scripts tests
printf 'CHECK_OK=w2_producer_consumer_topology\n'
~~~

Expected: only new CLI owns collection; tests are other callers. Graphify discovers candidates only; rg/regressions prove compatibility.

---

## Task 5: Final Offline Verification, Scope/Index Proof, Scanner, And Audit Route

**Invariants:** all.

**Files:** modify none, except ignored graphify-out output.

### Step 1: Run full focused regression with realistic timeout

Do not kill after 30 seconds: canonical root validation legitimately ZIP/CSV/hash-checks many authority files. Use at least 240 seconds for this aggregate command and report elapsed/slow tests.

~~~bash
PYTHONPATH=src:. .venv/bin/pytest -v -s --durations=20 \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_evidence_source.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py
~~~

Expected: all PASS. Duration output distinguishes slow full authority parse from deadlock.

### Step 2: Run lint and scanner; record actual RC

~~~bash
set -euo pipefail
ruff check configs/base.py \
  src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py \
  scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py \
  tests/research/external_signal_shadow/stage1_6f_w2_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py
set +e
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA" \
  src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py \
  scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py \
  tests/research/external_signal_shadow/stage1_6f_w2_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py
SCANNER_RC=$?
set -e
printf 'SCANNER_RC=%s\n' "$SCANNER_RC"
test "$SCANNER_RC" -eq 0
~~~

Expected: ruff RC 0, actual SCANNER_RC=0. Every warning needs execution-report path:line/rule/code/boundary justification/test. Scanner nonzero is a blocker.

### Step 3: One final graph update

~~~bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
command -v graphify >/dev/null || { echo 'STOP=graphify_workflow_contract_unavailable' >&2; exit 1; }
graphify update .
git check-ignore -v graphify-out/graph.json >/dev/null || { echo 'STOP=graphify_output_not_ignored' >&2; exit 1; }
printf 'CHECK_OK=graphify_updated_ignored\n'
~~~

Expected: CHECK_OK graphify updated; do not commit generated output.

### Step 4: Prove scope, index, No-Touch bytes and safety

~~~bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
git diff --check "$BASE_SHA"
git diff --cached --check "$BASE_SHA"
git diff --name-only "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/final-worktree-paths.txt"
git diff --cached --name-only "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/final-index-paths.txt"
git status --short --untracked-files=all > "$EXECUTION_BASELINE_DIR/final-status.txt"
git ls-files -s -z | shasum -a 256 | awk '{print $1}' > "$EXECUTION_BASELINE_DIR/final-index.sha256"
python3 - "$BASE_SHA" "$EXECUTION_BASELINE_DIR" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

allowed = {
    'configs/base.py',
    'src/research/external_signal_shadow/stage1_6f_w2_evidence_source.py',
    'scripts/external_signal_shadow/run_stage1_6f_w2_historical_evidence_expansion.py',
    'tests/research/external_signal_shadow/stage1_6f_w2_test_support.py',
    'tests/research/external_signal_shadow/test_stage1_6f_w2_evidence_source.py',
    'tests/scripts/external_signal_shadow/test_run_stage1_6f_w2_historical_evidence_expansion.py',
}
base_sha, baseline_name = sys.argv[1:]
baseline_dir = Path(baseline_name)

def git_names(*args):
    return set(subprocess.check_output(['git', *args], text=True).splitlines())

def snapshot(relative_name, tracked_dirty, staged, untracked):
    path = Path(relative_name)
    kinds = sorted(
        kind for kind, present in (
            ('tracked_dirty', relative_name in tracked_dirty),
            ('staged', relative_name in staged),
            ('untracked', relative_name in untracked),
        ) if present
    )
    if path.is_symlink():
        state = 'symlink'
        sha256 = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    elif path.is_file():
        state = 'file'
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    elif path.exists():
        raise SystemExit(f'STOP=unsupported_path_state:{relative_name}')
    else:
        state = 'tombstone'
        sha256 = None
    return {'path': relative_name, 'kinds': kinds, 'state': state, 'sha256': sha256}

tracked_dirty = git_names('diff', '--name-only', base_sha)
staged = git_names('diff', '--cached', '--name-only', base_sha)
untracked = git_names('ls-files', '--others', '--exclude-standard')
current_paths = tracked_dirty | staged | untracked
baseline_records = [
    json.loads(line)
    for line in (baseline_dir / 'preexisting-path-states.jsonl').read_text(encoding='utf-8').splitlines()
    if line
]
baseline_paths = {record['path'] for record in baseline_records}
assert not (baseline_paths & allowed), (
    f'STOP=preexisting_whitelist_overlap:{sorted(baseline_paths & allowed)}'
)

for expected in baseline_records:
    actual = snapshot(expected['path'], tracked_dirty, staged, untracked)
    assert actual == expected, (
        f"STOP=preexisting_provenance_mutated:{expected['path']}:"
        f"expected={expected}:actual={actual}"
    )

new_paths = current_paths - baseline_paths
unexpected = sorted(
    path for path in new_paths
    if path not in allowed and not path.startswith('graphify-out/')
)
assert not unexpected, f'STOP=scope_violation:{unexpected}'
new_staged = staged - baseline_paths
assert new_staged <= allowed, f'STOP=index_delta_outside_whitelist:{sorted(new_staged - allowed)}'

initial_index_sha = (baseline_dir / 'index.sha256').read_text(encoding='utf-8').strip()
final_index_sha = (baseline_dir / 'final-index.sha256').read_text(encoding='utf-8').strip()
index_state = 'unchanged' if initial_index_sha == final_index_sha else 'changed_only_in_allowed_scope'
print(f'CHECK_OK=preexisting_provenance_unchanged:{len(baseline_records)}')
print(f'CHECK_OK=scope_paths_allowed:{len(new_paths)}')
print(f'CHECK_OK=index_delta:{index_state}')
PY
PYTHONPATH=src:. .venv/bin/python - <<'PY'
import ast
from pathlib import Path
tree = ast.parse(Path('configs/base.py').read_text(encoding='utf-8'))
values = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
          if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
          and n.targets[0].id == 'RISK_LIVE_TRADING_ENABLED'}
assert values == {'RISK_LIVE_TRADING_ENABLED': False}
print('CHECK_OK=live_trading_disabled')
PY
~~~

Expected: all CHECK_OK. Every pre-existing path must retain its exact kinds, state and SHA/tombstone record; a matching pathname never excuses a mutation. New worktree/index paths must be whitelisted relative to BASE_SHA, and any index change must be only in allowed paths. Parent authority/W1/REEF/002/C/B/non-whitelist change is a blocker; preserve evidence, do not reset/delete it.

### Step 5: Request independent code review before Completion Audit

Use requesting-code-review after Step 4 passes and before any Completion Audit. This is a substantial cross-boundary change (authority gate, strict reader, production network runner and manifest lifecycle), so focused tests and a scanner alone are insufficient.

~~~bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
REVIEW_HEAD_SHA=$(git rev-parse HEAD)
test "$REVIEW_HEAD_SHA" = "$BASE_SHA" || {
  echo "STOP=unexpected_commit_before_review:base=$BASE_SHA head=$REVIEW_HEAD_SHA" >&2
  exit 1
}
git diff --binary "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/review-worktree.patch"
git diff --cached --binary "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/review-index.patch"
git ls-files --others --exclude-standard | LC_ALL=C sort -u > "$EXECUTION_BASELINE_DIR/review-untracked-paths.txt"
printf 'CHECK_OK=code_review_scope:base=%s:head=%s\n' "$BASE_SHA" "$REVIEW_HEAD_SHA"
~~~

The review packet must state that no implementation commit exists: BASE_SHA is the pre-execution commit and REVIEW_HEAD_SHA is only the unchanged repository commit, not a fabricated end-of-change SHA. Provide the reviewer all of:

- Approved Design/Plan path plus exact SHA, frozen authorities/request-set and no-touch boundary.
- BASE_SHA and REVIEW_HEAD_SHA; git diff --binary "$BASE_SHA"; git diff --cached --binary "$BASE_SHA"; git status --short --untracked-files=all; and the exact allowed-untracked path list.
- EXECUTION_BASELINE_DIR, preexisting-path-states.jsonl, final worktree/index/status snapshots and the Step 4 CHECK_OK output.
- The exact test/lint/scanner commands with actual exit codes and scanner-warning disposition ledger.
- The production-opener tests, negative mutations, crash/recovery tests and factual handoff boundary.

The reviewer must examine production call paths rather than only fake transport tests, confirm pre-existing baseline records did not change, verify no persistence/audit writer was introduced, and reject request-set/root/permission drift.

If the reviewer reports P0/P1 or scope/authority defect, do not route to Completion Audit. Apply only an approved-scope repair, rerun its RED/GREEN and affected regression, then rerun Task 5 Steps 1, 2 and 4 and request a new focused review. A reviewer finding requiring Design, request-set, lifecycle-owner or whitelist expansion is STOP=BLOCKED_SPEC_DRIFT or STOP=BLOCKED_SCOPE_DRIFT as applicable.

### Step 6: Route to independent read-only Completion Audit

Do not declare completion. Handoff only exact Plan/Design SHA, BASE_SHA, baseline dir, whitelist, factual run evidence and known blockers. Do not send a self-authored success verdict or write an audit artifact.

A fresh auditor follows audit-plan-completion SKILL, independently runs current scanner/strict reader and checks source, diff/index/untracked state. It returns external read-only complete/incomplete/blocked. Only later W2-0 may bind that artifact path+SHA with final manifest; no Plan component writes or consumes it.

---

## Plan Self-Review

- INV-W2E01-03 map to Tasks 0-1; INV-W2E04-09 to Tasks 2-3; INV-W2E10-11 to Tasks 2/4; INV-W2E12 to Task 4/5 read-only handoff; INV-W2E13 to Tasks 1-4 metadata-only boundary.
- No Task alters upstream parser, W1/REEF consumer, Design/Plan, candidate/C/B bytes, runbook, roadmap, risk setting or trading code.
- No Task authorizes public GET. Future collector execution still needs separate single-use authorization bound to final Plan SHA.
- No audit writer/publisher/attestation is introduced.
- Scanner warnings require a ledger and actual scanner RC=0; code review occurs after final scope/index proof and before read-only Completion Audit.
- Pre-existing worktree/index/untracked paths are provenance records with exact state/SHA comparison, never scope exemptions.

## Execution Gate

This is a Plan candidate only. It requires independent Model B review and separate user implementation approval bound to its final SHA before any Task. Even then, public archive GET needs separate exact authorization.
