# Stage 1.6F Candidate Evidence Admission and W1 Descriptive Diagnostic Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: use `executing-plans` and `test-driven-development` to implement this Plan task-by-task after independent Plan review and separate user implementation authorization.

**Goal:** 对冻结的候选根 `expansion_candidate_run_20260917_002` 建立独立、严格、离线只读的 admission consumer，产出 41 个事件、779 条 W1 原始描述性指标及可严格重载的 sealed bundle，不改变 REEF 链路或任何交易权限。

**Architecture:** 将现有 expansion collector 内的 completed-root 验根逻辑一次性迁入一个 `src/` generic shared validation core；它保留 collector 的 Design/Plan/network authority 参数、accepted/rejected root 语义和 failure keys。collector 保留其 CLI、网络采集与既有错误边界，通过 thin adapter 委托该 core；独立 exact-`002` admission wrapper 以冻结 manifest SHA 与 collection authority packet 调用同一 core。新增 W1 reducer、bundle storage/strict loader 与离线 CLI，只消费该 wrapper、既有 `verify_c_input(...)` 和 candidate/C authority bind，并以 canonical JSON、manifest-last 和 `os.replace()` 生成独立输出根。现有 REEF reader/runner/storage 不修改且继续拒绝 candidate root。

**Tech Stack:** Python 标准库 `csv`, `dataclasses`, `hashlib`, `json`, `math`, `os`, `pathlib`, `tempfile`; pytest; ruff; project `anti_shortcut_scan.py`; project Graphify CLI.

---

## Governance And Design Authority

**Approved Design:** `docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md`
**Approved Design SHA-256:** `dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097`

This Plan implements only the approved Design above. Plan review and Plan approval do not authorize implementation. Before changing any code or test, the executor must receive a separate statement bound to this Plan's exact SHA:

```text
我批准实施 Plan：<path>（SHA-256: <exact approved Plan SHA>）。
允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。
```

That implementation authority permits neither a network request nor new collection. It never permits commit, push, deployment, SSH, VPS action, replay, paper trading, live trading, signal generation, execution or alpha interpretation.

### Frozen Authority Packet

Task 0 must recompute every file hash before a code/test edit. A mismatch is `STOP=approved_authority_mismatch`, except for the Rule-12 routes defined below.

| Authority | Path | SHA-256 |
| --- | --- | --- |
| Parent F Design | `docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md` | `87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c` |
| F evidence-to-schema Delta | `docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md` | `8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628` |
| Existing F implementation Plan | `docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md` | `6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f` |
| Expansion Design | `docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md` | `1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4` |
| Expansion implementation Plan | `docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md` | `fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d` |
| Candidate admission Design | `docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md` | `dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097` |
| Canonical candidate manifest | `data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002/candidate_manifest.json` | `b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67` |
| One-run network authorization | `configs/authorizations/network_auth_expansion_run_20260917_002.json` | `8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6` |
| Existing F source boundary | `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py` | `00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f` |
| Existing F denominator module | `src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py` | `84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3` |
| C completion manifest | `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json` | `226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0` |
| C source-export receipt | `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/source_export_receipt.json` | `07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e` |
| B sealed export manifest | `data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090/sealed_export_manifest.json` | `1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be` |
| Coverage matrix | `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json` | `b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8` |
| REEF manifest | `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json` | `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f` |

### Mutable Implementation Baseline

This is verified before code/test edits only. It is deliberately not an immutable authority: Task 1 must change it into the collector thin adapter. Task 5 instead proves its exact whitelisted delta plus delegation/equivalence regressions.

| Mutable baseline | Path | Pre-change SHA-256 |
| --- | --- | --- |
| Candidate collector | `scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py` | `200279f3d25e69d06e8bdff238b2894da4c27cfb70e214a10dedf7e072f77a08` |

### Rule-12 Routing

| Condition during execution | Required route |
| --- | --- |
| An existing helper/real producer already supplies the approved behavior, but the executor initially missed it | `BLOCKED_IMPLEMENTATION_DEFECT`; repair only inside this Plan's whitelist. |
| Correct behavior requires a file, schema or API outside the whitelist | `BLOCKED_SCOPE_DRIFT`; preserve evidence and stop. |
| Real C/candidate bytes, their strict loaders, or a frozen authority contradict this Design/Plan | `BLOCKED_SPEC_DRIFT`; stop with failed invariant, SSOT path, exact contradiction and proposed Design/Plan delta. |

No `.get(..., default)`, synthetic hash, copied attestation, alternate candidate root, legacy `001` root, handcrafted cross-boundary positive fixture, `src -> scripts` import, compatibility allowlist expansion or retry/resume path is permitted as a local workaround.

## Invariant Map

| Design invariant | Production owner | Mechanical proof | Fail-closed outcome |
| --- | --- | --- | --- |
| INV-CA01 | exact-`002` admission wrapper over shared validation core | exact root/manifest plus frozen collection Design/Plan/network packet; alias/`001`/manifest/extra-file mutations | `candidate_admission_invalid`, no output root |
| INV-CA02 | generic shared validation core and collector adapter | same authority/root mutation reaches the pre-migration failure key through collector adapter and shared core | no duplicate validator, no ignored authority argument and no `src -> scripts` import |
| INV-CA03 | unchanged REEF boundary and candidate CLI | REEF reader rejects candidate; candidate CLI rejects REEF | incompatible identity rejected |
| INV-CA04 | candidate W1 reducer | all 41 C/candidate identities, exact `Tpub` and five PIT facts cross-bound | `upstream_denominator_authority_invalid` |
| INV-CA05 | reducer time/family gates | family timestamp, partial-bar, duplicate, gap and after-end mutations | per-metric `diagnostic_incomplete` or candidate invalidity |
| INV-CA06 | metric ledger and storage | 19 tuples/event, 779 rows, family audit and gate-failure mutations | bundle loader rejects malformed ledger |
| INV-CA07/08 | candidate W1 storage strict loader | recursive key/type/finite/forbidden-field mutations | sealed bundle rejected |
| INV-CA09 | atomic writer and strict loader | write/rename crash, stale temp, collision and post-seal mutation | no final manifest or immutable invalid forensic root |
| INV-CA10 | summary reducer/loader | 45 groups, 38 status-count rows, zero/even/odd median mutations | summary rejected |
| INV-CA11/12 | candidate source, W1 reducer, W1 storage, CLI and tests | 13 false flags; four-module closed AST import/call policy plus socket runtime trap | fail closed; no network/runtime side effect |

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py` - new shared candidate strict loader and C/candidate publication binder
- `src/research/external_signal_shadow/stage1_6f_candidate_w1_descriptive_diagnostic.py` - new W1-only denominator/reducer contract
- `src/research/external_signal_shadow/stage1_6f_candidate_w1_diagnostic_storage.py` - new sealed-bundle writer and strict loader
- `scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py` - delegate completed-root validation to the shared module without changing collection semantics
- `scripts/external_signal_shadow/run_stage1_6f_candidate_w1_descriptive_diagnostic.py` - new offline local CLI

Allowed verification paths:
- `tests/research/external_signal_shadow/stage1_6f_candidate_w1_test_support.py` - new canonical-root fixture and single-mutation materializer
- `tests/research/external_signal_shadow/test_stage1_6f_candidate_evidence_source.py`
- `tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_descriptive_diagnostic.py`
- `tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6f_candidate_w1_descriptive_diagnostic.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py` - delegation/equivalence regression only

Allowed documentation paths:
- none

Allowed generated/runtime artifacts:
- `data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/<run_id>/**` - local generated output only, ignored, never committed
- `graphify-out/**` - generated, ignored, never committed
- `$(git rev-parse --git-path "plan-execution/<run_id>")/**` - execution baseline evidence only, never committed

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py` - reuse only `reconstruct_denominator(...)`; do not change REEF metric grammar or controls.
- `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py` - reuse only `verify_c_input(...)`; `verify_market_evidence(...)` remains REEF-only.
- `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_storage.py` - REEF bundle schema/loader unchanged.
- `scripts/external_signal_shadow/run_stage1_6f_historical_mechanism_diagnostic.py` and `scripts/external_signal_shadow/review_stage1_6f_historical_mechanism_diagnostic.py` - remain REEF-only.
- `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/**`, all B/C roots, `data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002/**`, legacy `001`, `configs/base.py`, Stage 1.5 and Stage 1.6E.

Forbidden:
- Any mutation outside the paths above.
- Any mutation of the approved Design, parent authorities, candidate bytes, B/C bytes or REEF fixture/package.
- Any network request, new collection, credentials, SSH/VPS action, daemon, replay, paper/live trading, signal, execution, alpha/PnL/control/W2/W3 feature.
- Any unrelated refactor, formatter/autofix, `ruff check --fix .`, repository-wide format, `git clean -fdx`, reset or automatic revert.

## Task 0: Freeze Execution Baseline, Authorities, And Real Inputs

**Invariants:** all.
**Files:** modify none.

### Step 1: Require implementation authority and create the workflow-owned baseline

Run only after separate user approval of this exact Plan. Follow `execute-approved-plan.md` Step 1 exactly; it is the sole owner of `BASE_SHA`, `EXECUTION_RUN_ID`, `EXECUTION_BASELINE_DIR`, `status.txt`, `worktree.patch`, `index.patch`, `untracked-paths.txt` and `untracked-sha256.txt`.

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
BASE_SHA=$(git rev-parse HEAD)
EXECUTION_RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
EXECUTION_BASELINE_DIR=$(git rev-parse --git-path "plan-execution/$EXECUTION_RUN_ID")
mkdir -p "$EXECUTION_BASELINE_DIR"
git status --short --untracked-files=all > "$EXECUTION_BASELINE_DIR/status.txt"
git diff --binary > "$EXECUTION_BASELINE_DIR/worktree.patch"
git diff --cached --binary > "$EXECUTION_BASELINE_DIR/index.patch"
git ls-files --others --exclude-standard > "$EXECUTION_BASELINE_DIR/untracked-paths.txt"
while IFS= read -r target_path; do shasum -a 256 "$target_path"; done \
  < "$EXECUTION_BASELINE_DIR/untracked-paths.txt" \
  > "$EXECUTION_BASELINE_DIR/untracked-sha256.txt"
git ls-files -s -z | shasum -a 256 | awk '{print $1}' > "$EXECUTION_BASELINE_DIR/index.sha256"
{
  git diff --name-only "$BASE_SHA"
  git diff --cached --name-only "$BASE_SHA"
  git ls-files --others --exclude-standard
} | LC_ALL=C sort -u > "$EXECUTION_BASELINE_DIR/preexisting-paths.txt"
python3 - "$EXECUTION_BASELINE_DIR/preexisting-paths.txt" \
  "$EXECUTION_BASELINE_DIR/preexisting-path-states.jsonl" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

paths_file, output_file = map(Path, sys.argv[1:])
records = []
for raw_path in paths_file.read_text(encoding="utf-8").splitlines():
    path = Path(raw_path)
    if path.is_symlink():
        payload = os.readlink(path).encode("utf-8")
        state = "symlink"
    elif path.is_file():
        payload = path.read_bytes()
        state = "file"
    elif not path.exists():
        payload = b""
        state = "missing"
    else:
        raise SystemExit(f"STOP=preexisting_path_unsupported:{raw_path}")
    records.append({
        "path": raw_path,
        "state": state,
        "sha256": hashlib.sha256(payload).hexdigest(),
    })
output_file.write_text(
    "".join(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n" for record in records),
    encoding="utf-8",
)
PY
printf '%s\n' "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/base_sha.txt"
```

Expected: one immutable pre-execution baseline. `preexisting-path-states.jsonl` is the byte/state authority for every pre-existing tracked dirty or untracked path; Task 5 must compare every path outside this Plan's implementation whitelist to it. Existing untracked Design/Plan candidates are recorded, never overwritten, staged, reverted or attributed to implementation.

### Step 2: Verify the authority packet and literal safe configuration facts

Use a target-only AST extractor; do not call `ast.literal_eval` over every assignment in `configs/base.py`.

```bash
set -euo pipefail
AUTHORITY_LEDGER="$EXECUTION_BASELINE_DIR/frozen-authority-ledger.tsv"
MUTABLE_BASELINE_LEDGER="$EXECUTION_BASELINE_DIR/mutable-implementation-baseline.tsv"
cat >"$AUTHORITY_LEDGER" <<'EOF'
87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md
8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628 docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md
6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md
1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4 docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md
fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md
dfa324ede1f0cb498a53660756aa408762220a667370a8409aa5bcb194cb4097 docs/designs/2026-09-17-external-signal-shadow-lab-stage1-6f-candidate-admission-w1-descriptive-diagnostic-delta-design_CN.md
b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67 data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002/candidate_manifest.json
8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6 configs/authorizations/network_auth_expansion_run_20260917_002.json
00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py
84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3 src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py
226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0 data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json
07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/source_export_receipt.json
1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090/sealed_export_manifest.json
b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8 tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json
9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json
EOF
cat >"$MUTABLE_BASELINE_LEDGER" <<'EOF'
200279f3d25e69d06e8bdff238b2894da4c27cfb70e214a10dedf7e072f77a08 scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py
EOF
check_sha_ledger() {
  ledger_path=$1
  while IFS=' ' read -r expected target_path; do
    actual=$(shasum -a 256 "$target_path" | awk '{print $1}') || {
      echo "STOP=approved_authority_missing:$target_path" >&2; return 1;
    }
    test "$actual" = "$expected" || {
      echo "STOP=approved_authority_mismatch:$target_path" >&2; return 1;
    }
  done < "$ledger_path"
}
check_sha_ledger "$AUTHORITY_LEDGER"
check_sha_ledger "$MUTABLE_BASELINE_LEDGER"
python3 - <<'PY'
import ast
from pathlib import Path
targets = {"EXCHANGE_TIMEOUT_MS", "EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT", "RISK_LIVE_TRADING_ENABLED"}
tree = ast.parse(Path("configs/base.py").read_text(encoding="utf-8"))
values = {
    node.targets[0].id: ast.literal_eval(node.value)
    for node in tree.body
    if isinstance(node, ast.Assign)
    and len(node.targets) == 1
    and isinstance(node.targets[0], ast.Name)
    and node.targets[0].id in targets
}
assert values == {
    "EXCHANGE_TIMEOUT_MS": 10_000,
    "EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT": "crypto-alpha-lab-research-readonly/0.1",
    "RISK_LIVE_TRADING_ENABLED": False,
}
PY
printf '%s\n' 'CHECK_OK=authorities_and_permissions_frozen'
```

Expected: `CHECK_OK=authorities_and_permissions_frozen`; `RISK_LIVE_TRADING_ENABLED = False` is an exact invariant. `frozen-authority-ledger.tsv` is the sole immutable authority list and must be re-used unchanged by Task 5. `mutable-implementation-baseline.tsv` is Task-0-only and must not be rehashed as immutable after Task 1. A config/source/candidate authority contradiction is `STOP=BLOCKED_SPEC_DRIFT`, not a locally adopted new value.

### Step 3: Fingerprint immutable roots and validate tool/output boundaries

Create a small standard-library fingerprint script only inside `$EXECUTION_BASELINE_DIR`; it is audit metadata, not repository code. It must enumerate sorted relative paths, file byte lengths, SHA-256, mode and symlink status for the exact C root, B root and canonical `002` candidate root. Record the resulting JSON before edits and compare it byte-for-byte after all Tasks.

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
command -v graphify >/dev/null || { echo 'STOP=graphify_workflow_contract_unavailable' >&2; exit 1; }
graphify --help >/dev/null || { echo 'STOP=graphify_workflow_contract_unavailable' >&2; exit 1; }
git check-ignore -v data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/plan_probe \
  >/dev/null || { echo 'STOP=candidate_w1_output_not_ignored' >&2; exit 1; }
test -d data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z \
  || { echo 'STOP=upstream_root_missing' >&2; exit 1; }
test -d data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090 \
  || { echo 'STOP=upstream_root_missing' >&2; exit 1; }
test -d data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002 \
  || { echo 'STOP=candidate_root_missing' >&2; exit 1; }
```

Expected: all checks pass. This Plan uses `graphify update .`, the canonical CLI named by `AGENTS.md`; it must not invent a Python-interpreter fallback. If that command is unavailable at execution time, stop with `STOP=graphify_workflow_contract_unavailable` before implementation.

## Task 1: Promote the Candidate Strict Loader Once and Preserve Collector Semantics

**Invariants:** INV-CA01, INV-CA02, INV-CA03, INV-CA11, INV-CA12.
**Files:**
- Create: `src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py`
- Modify: `scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py`
- Create: `tests/research/external_signal_shadow/stage1_6f_candidate_w1_test_support.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6f_candidate_evidence_source.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py`

### Step 1: Write RED tests using canonical upstream bytes

Create a test helper that:

- builds the sole canonical positive fixture: a temporary project mirror whose candidate/C/B roots and every frozen authority file are direct hard-link copies of the real repository bytes; use `try: os.link(...)` and on `OSError` use `shutil.copy2(...)` as the only fallback when a hard link is unavailable;
- verifies each mirrored file SHA-256, byte length, relative path and whole-root tree against its real authority source before every positive use; it never constructs a manifest, authority dictionary or C fixture by hand;
- invokes the existing `verify_c_input(...)` against the canonical-byte mirror for all positive C input;
- derives every negative fixture from that verified canonical positive mirror by one declared mutation; before changing any clone file, unlink the destination first, so a hard-linked clone can never mutate the real authority inode.

Write failing tests for:

1. `validate_candidate_root_core(...)` accepts the existing producer's complete `approved_design_path`, `approved_design_sha`, `approved_plan_path`, `approved_plan_sha`, `network_authorization_sha`, `project_root` and `completed_root` arguments. `load_verified_candidate_evidence(...)` is a separate exact-`002` wrapper: it checks the canonical relative root and manifest SHA, supplies the frozen expansion Design/Plan/network packet, then calls that same core.
2. The exact-`002` wrapper accepts only the verified canonical-byte mirror's real `002` bytes, 41 cohort, 705 logical records, 664 physical objects, 369 coverage records, 13 exact-false flags and final-root tree. It rejects an alias, legacy `001`, copied/extra file, symlink, altered manifest key, altered physical URL/ID, altered logical projection, CSV/ZIP hash mismatch and stale temp before a W1 writer is called.
3. Before extraction, freeze positive success projection and exact failure keys from the existing collector validator. After migration, execute the collector adapter and shared core against the same canonical positive plus one declared mutation for each of: approved Design SHA, approved Plan SHA, network-authorization SHA, manifest byte and candidate-root state. Assert the same accept/reject result and exact existing `candidate_root_invalid:*` failure key through the collector adapter, including `candidate_root_invalid:network_auth_record_sha_mismatch` and `candidate_root_invalid:root_state_mismatch:*`; assert its call to the core is exactly once with all authority arguments preserved.
4. Construct `VerifiedCInput` only through `verify_c_input(...)`. A declared mutation of the supplied C completion manifest SHA, source-export receipt SHA or B sealed-export manifest SHA must fail before denominator/Tpub reconstruction when compared to the candidate's frozen authority packet.
5. `verify_market_evidence(candidate_root)` remains rejected, and the candidate source module imports no script, network, execution or REEF writer/reader module.

Run:

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_evidence_source.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py \
  -k 'candidate or validator or delegation or canonical'
```

Expected: RED because no `src/` candidate source module exists.

### Step 2: Implement the shared source boundary

Move, do not reimplement, the completed-root validation dependencies currently used by `validate_completed_candidate_root(...)`: exact key sets/enums, canonical parent-path checks, file hashing, strict retained CSV parsing, coverage recomputation, cohort/request enumeration and independent retained-tree verification. The new module must expose only explicit functions/data classes required by both callers, including:

```python
def validate_candidate_root_core(
    *, completed_root: Path, approved_design_path: Path, approved_design_sha: str,
    approved_plan_path: Path, approved_plan_sha: str,
    network_authorization_sha: str, project_root: Path,
) -> VerifiedCandidateEvidence: ...

def load_verified_candidate_evidence(
    *, project_root: Path, candidate_root: Path,
    approved_design_path: Path, approved_design_sha: str,
    approved_plan_path: Path, approved_plan_sha: str,
    network_authorization_sha: str,
) -> VerifiedCandidateEvidence: ...

def bind_candidate_publication_authority(
    *, verified_candidate: VerifiedCandidateEvidence, verified_c: VerifiedCInput
) -> Mapping[CandidateIdentity, PublicationAuthority]: ...

def bind_verified_candidate_c_authority(
    *, verified_candidate: VerifiedCandidateEvidence, verified_c: VerifiedCInput,
    completed_root: Path, source_export: Path,
) -> None: ...
```

The generic core preserves the current collector validation semantics and failure keys for every accepted authority argument; it has no network, writer, collector-memory or fallback behavior. The exact-`002` wrapper admits only the canonical relative root plus manifest SHA and calls the generic core with the frozen expansion Design/Plan/network authority packet. It re-reads all retained candidate bytes and returns immutable metadata plus parsed rows keyed by `(parent_article_id, contract_id, canonical_symbol, metric)`.

`bind_verified_candidate_c_authority(...)` runs after `verify_c_input(...)` and before publication binding, denominator reconstruction or output-root creation. It requires `SHA256(completed_root/completion_manifest.json)`, `verified_c.source_export_receipt_sha256`, `SHA256(source_export/sealed_export_manifest.json)` and `verified_c.input_manifest_sha256` to each exact-match the corresponding C/receipt/B values in `VerifiedCandidateEvidence`'s frozen packet. Any difference is `STOP=upstream_denominator_authority_invalid`; compatible cohort/Tpub values never substitute for these byte bindings. `bind_candidate_publication_authority(...)` then accepts only equal exact `parent_audit_outcomes.source_published_at_ms` / `delisting_notices.source_published_at_ms` values; it never selects the first non-null field or falls back to `releaseDate`.

Keep the collector's public exception class and function signature. Its `validate_completed_candidate_root(...)` becomes a thin adapter over `validate_candidate_root_core(...)` and translates only the shared validation failure into the existing collector error shape. It must forward every existing authority argument exactly once and cannot call the exact-`002` wrapper. Do not move `validate_prefetch_authority(...)`, request dispatch, network authorization, ZIP download or collector CLI into `src/`.

### Step 3: Run GREEN and compatibility regressions

Run the command from Step 1, then:

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py
```

Expected: PASS. Existing collector validation behavior remains equivalent; current REEF strict-reader tests pass and no `src -> scripts` import exists.

## Task 2: Build the 41 x 19 W1 Denominator and Descriptive Reducer

**Invariants:** INV-CA04, INV-CA05, INV-CA06, INV-CA08, INV-CA11, INV-CA12.
**Files:**
- Create: `src/research/external_signal_shadow/stage1_6f_candidate_w1_descriptive_diagnostic.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_descriptive_diagnostic.py`
- Modify: `tests/research/external_signal_shadow/stage1_6f_candidate_w1_test_support.py`

### Step 1: Write RED contract tests

Use `load_verified_candidate_evidence(...)` with the frozen expansion Design/Plan/network packet, `verify_c_input(...)`, `bind_verified_candidate_c_authority(...)` and `reconstruct_denominator(...)` over the Task 1 verified canonical-byte mirror to construct the positive path. Assert:

- the eligible non-REEF C projection equals the candidate's full identity set and exact sorted 41-symbol cohort;
- both retained C publication fields are equal exact non-bool millisecond integers; every selected `window == "w1_shock_12h"` coverage/logical record begins at `Tpub` and ends at `Tpub + 12h`; `baseline_168h` does not enter this gate;
- the verified C completion-manifest, receipt and B sealed-export byte authorities are exact-equal to the candidate packet before any denominator or `Tpub` value is read;
- exactly 19 permitted `(metric_name, horizon)` tuples per event and exactly `41 * 19 = 779` records; each tuple has 41 records split only between `descriptive_only` and `diagnostic_incomplete`; dynamic metric discovery cannot replace this cardinality oracle;
- `H1` has only `hourly_bar_observation`; H4/H12 complete bars require `open_time >= ceil_to_step(Tpub, 3_600_000)`, `close_time == open_time + 3_600_000 - 1`, and `open_time + 3_600_000 <= end_ms`;
- family membership fields are exactly `open_time`, `create_time`, `calc_time`, `timestamp`, and `transact_time`; no archive date/download time is used;
- every result carries sorted `source_family_audits`, exact audit-ID union, and `gate_failures`; a multi-family basis record cannot collapse source provenance;
- a sole `price_path.first_complete_bar_close=0` mutation yields `diagnostic_incomplete`, `{}`, and exactly `["zero_price_path_denominator"]`; `NaN`, infinity, bool-as-number, gap, duplicate, partial bar, timestamp-field mismatch and missing positive index close cannot yield descriptors.

Run:

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_descriptive_diagnostic.py
```

Expected: RED because the new W1 reducer does not exist.

### Step 2: Implement the minimal W1-only reducer

Define closed data classes for candidate denominator rows and metric results. Reuse `reconstruct_denominator(...)` only for its frozen C projection; do not import or call REEF `compute_descriptive_metrics(...)`, control matching, W2 logic or REEF storage.

Implement an explicit 19-tuple table, not dynamic discovery. Generate exactly one record per denominator identity/tuple. Apply source coverage first, then the exact source-family timestamp/grid rule, then the descriptor reducer. On failure, preserve the denominator and produce `diagnostic_incomplete`, `descriptors={}`, required family audits and a sorted non-empty `gate_failures` array. Do not impute, delete, substitute baseline data or synthesize a numeric result.

Implement only the Design descriptors: H1 raw hourly observation; H4/H12 raw `bar_close_change_bps`; perp/index and mark/index reference basis; discrete funding observations; raw OI; visible depth proxy; and aggregate-trade labels/notional. Preserve raw descriptive status only: no control, excess return, win rate, alpha, PnL, execution, signal, cost, slippage, W2/W3/24h or settlement output.

### Step 3: Run GREEN and legacy reducer regression

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_golden_numerical_verification.py
```

Expected: PASS. Candidate W1 output meets the exact 41/19/779 contract; existing REEF reducer and golden numerical verification remain unchanged.

## Task 3: Add Candidate W1 Sealed Storage, Strict Reloading, And Fixed Summary Grammar

**Invariants:** INV-CA06 through INV-CA11.
**Files:**
- Create: `src/research/external_signal_shadow/stage1_6f_candidate_w1_diagnostic_storage.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py`
- Modify: `tests/research/external_signal_shadow/stage1_6f_candidate_w1_test_support.py`

### Step 1: Write RED storage/loader tests from canonical reducer outputs

Create the positive bundle only by passing Task 2 outputs derived from the Task 1 verified canonical-byte mirror plus canonical C loader into the new writer. Write one declared mutation per assertion:

1. Writer produces exactly denominator JSONL, metric JSONL, summary JSON and manifest; `bundle_run_id == output_root.name`; manifest is absent until the final rename.
2. Strict loader rejects an unknown/missing/duplicate JSON key, invalid type, non-finite number, changed candidate/C/PIT authority, invalid 13-false flag, forged family audit, wrong source audit union, invalid/empty gate failure, duplicate or missing metric tuple, forbidden W2/control/PnL/alpha field, unlisted extra file, symlink, stale temp, hash/length mismatch and output-root/run-ID mismatch.
3. Summary has exactly 45 sorted allowlisted groups, exactly 38 sorted `(metric_name, horizon, status)` count rows including zeroes, count conservation to 41/779, exact `n_unique_parent_article_ids`, null extrema only when no descriptive row, deterministic even/odd median and the exact non-independence notice.
4. Inject writer failures before each non-manifest rename and manifest rename. Assert no final manifest, no resume/repair, and a new run ID is required. Mutate a post-seal artifact and assert the root remains intact but strict loader rejects it.

Run:

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py
```

Expected: RED because candidate W1 storage/loader does not exist.

### Step 2: Implement minimal sealed-bundle storage

Implement only these public entry points:

```python
def write_candidate_w1_bundle(*, output_root: Path, ...) -> Path: ...
def load_candidate_w1_bundle(*, output_root: Path) -> VerifiedCandidateW1Bundle: ...
```

Require a create-exclusive output root. Serialize JSON with `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=True`, `allow_nan=False`, no trailing newline; serialize each JSONL record as canonical JSON plus exactly one newline. Write all artifacts to same-directory temp files, flush/fsync, read-back verify SHA-256/byte length, rename the three data artifacts, then temp-write/fsync/read-back/atomically `os.replace()` the manifest last. Never rewrite, append, repair, delete or reuse a root.

The strict loader uses duplicate-key rejection before object construction, closed key sets, finite-number recursion and full authority/hash/length recomputation. It verifies schema `stage1_6f_candidate_w1_descriptive_bundle_v1`, all candidate/C/PIT authority facts, 41 denominator rows, 779 metric records, all 45 summary groups, all 38 count rows, and 13 exact false flags.

### Step 3: Run GREEN and storage compatibility regression

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_storage.py
```

Expected: PASS. Candidate bundle is sealed/reloadable; REEF storage schema and tests remain unchanged.

## Task 4: Connect the Offline Candidate W1 CLI Without Network or Runtime Authority

**Invariants:** INV-CA01 through INV-CA12.
**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_6f_candidate_w1_descriptive_diagnostic.py`
- Create: `tests/scripts/external_signal_shadow/test_run_stage1_6f_candidate_w1_descriptive_diagnostic.py`

### Step 1: Write RED CLI and production-routing tests

Test `main(argv)` with exactly these local path arguments:

```text
--project-root
--source-export
--completed-root
--candidate-root
--output-root
```

Positive integration uses only the Task 1 verified canonical-byte temporary-project mirror: its `project_root`, candidate root, C/B roots and authority files are one already-verified fixture. It writes only that mirror's canonical relative output root at `data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/<run_id>/` and reloads it with `load_candidate_w1_bundle(...)`. It must prove the runner calls exact-`002` candidate admission, C verification, candidate/C authority binding, publication binding, W1 reduction and candidate storage exactly once in that order.

Negative tests assert no output directory/manifest on: REEF root, legacy `001`, alias candidate root, wrong collection Design/Plan/network authority argument, wrong current Design SHA/current Design byte, candidate/C authority mismatch, output collision, missing C path, an outside output parent, a `..` output alias, symlink output parent/root and basename/run-ID mismatch. The positive uses no arbitrary `/tmp` output root.

Add a dedicated no-network proof that is independent of `anti_shortcut_scan.py`: parse all four new production modules - candidate source, W1 reducer, W1 storage and candidate CLI - and reject imports rooted at `urllib`, `http`, `socket`, `requests`, `httpx`, `aiohttp`, `websockets`, `ftplib` or `subprocess`, and reject calls rooted at `os.system`, `os.popen`, `subprocess`, `socket`, `urllib`, `http`, `requests`, `httpx`, `aiohttp`, `websockets` or `ftplib`. In the runner integration test, trap `socket.socket`, `socket.create_connection`, `urllib.request.urlopen`, `http.client.HTTPConnection` and `http.client.HTTPSConnection` to raise. A scanner RC of zero is not evidence for this invariant.

Run:

```bash
.venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_candidate_w1_descriptive_diagnostic.py
```

Expected: RED because the CLI does not exist.

### Step 2: Implement the smallest offline runner

Resolve only the five explicit paths. Recompute the approved candidate-admission Design SHA before opening the candidate root; mismatch is `STOP=approved_authority_mismatch`. The runner supplies the frozen expansion Design/Plan/network authority packet to exact-`002` admission. Before writer creation it requires `--output-root` to be a non-symlink, `..`-free relative path whose resolved parent exactly equals `project_root/data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics`; its basename is the non-empty `run_id`. Reject any other parent, absolute path, symlink component, alias, existing root or basename/run-ID mismatch before any output file with `STOP=candidate_w1_output_root_invalid` (or existing-root `STOP=candidate_w1_output_run_id_collision`).

Invoke exact-`002` admission before any output-root creation, then `verify_c_input(...)`, `bind_verified_candidate_c_authority(...)`, publication binding, W1 reducer, writer and strict reload. The candidate/C authority bind must complete before denominator/Tpub reconstruction.

The runner imports no collector script, network-capable library, credentials, execution/strategy module, REEF market reader, REEF writer or REEF runner. It sets no permission flag and accepts no URL, run selection, `latest`, retry, fallback, control, W2, output overwrite or runtime option.

### Step 3: Run GREEN and cross-boundary regressions

```bash
.venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_*.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_*.py
```

Expected: PASS. Candidate CLI accepts only `002`; existing REEF runner remains independent and candidate-incompatible.

## Task 5: Final Scope, Scanner, Graph, And Independent Completion Audit

**Invariants:** all.
**Files:** modify none.

### Step 1: Run non-mutating static and focused verification

```bash
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py \
  src/research/external_signal_shadow/stage1_6f_candidate_w1_descriptive_diagnostic.py \
  src/research/external_signal_shadow/stage1_6f_candidate_w1_diagnostic_storage.py \
  scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py \
  scripts/external_signal_shadow/run_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/research/external_signal_shadow/stage1_6f_candidate_w1_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_evidence_source.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py

.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_*.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py
```

Expected: exit `0`; do not run any autofix or formatter.

### Step 2: Capture the actual scanner exit code

```bash
set -euo pipefail
SCANNER_OUT="$EXECUTION_BASELINE_DIR/anti_shortcut_scan.txt"
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" --all-lines \
  src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py \
  src/research/external_signal_shadow/stage1_6f_candidate_w1_descriptive_diagnostic.py \
  src/research/external_signal_shadow/stage1_6f_candidate_w1_diagnostic_storage.py \
  scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py \
  scripts/external_signal_shadow/run_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/research/external_signal_shadow/stage1_6f_candidate_w1_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_evidence_source.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py \
  >"$SCANNER_OUT" 2>&1; then SCANNER_RC=0; else SCANNER_RC=$?; fi
cat "$SCANNER_OUT"
printf '%s\n' "$SCANNER_RC" > "$EXECUTION_BASELINE_DIR/anti_shortcut_scan.exitcode"
test "$SCANNER_RC" -eq 0 || { echo 'STOP=anti_shortcut_scan_nonzero' >&2; exit 1; }
```

Expected: actual scanner RC is `0`. Every scanner warning needs an explicit completion-audit disposition; any error/nonzero blocks completion.

### Step 3: Prove scope, authority and upstream immutability

Re-run Task 0 root fingerprint and require byte-for-byte equality. Re-run the same Task-0 authority ledger and safe-config AST check, then run exact-`002` admission, `verify_c_input(...)` and `bind_verified_candidate_c_authority(...)` over real roots. Then prove changed paths are limited to the Plan whitelist, the Git index remains baseline-identical and every pre-existing path outside the implementation whitelist is byte/state-identical to Task 0.

```bash
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null
git diff --check "$BASE_SHA"
git diff --cached --check "$BASE_SHA"
git diff --name-only "$BASE_SHA"
git diff --cached --name-only "$BASE_SHA"
git status --short --untracked-files=all
test "$(git ls-files -s -z | shasum -a 256 | awk '{print $1}')" = \
  "$(cat "$EXECUTION_BASELINE_DIR/index.sha256")" \
  || { echo 'STOP=git_index_changed' >&2; exit 1; }
while IFS=' ' read -r expected target_path; do
  actual=$(shasum -a 256 "$target_path" | awk '{print $1}') || {
    echo "STOP=approved_authority_missing:$target_path" >&2; exit 1;
  }
  test "$actual" = "$expected" || {
    echo "STOP=approved_authority_mismatch:$target_path" >&2; exit 1;
  }
done < "$EXECUTION_BASELINE_DIR/frozen-authority-ledger.tsv"
python3 - <<'PY'
import ast
from pathlib import Path

targets = {"EXCHANGE_TIMEOUT_MS", "EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT", "RISK_LIVE_TRADING_ENABLED"}
tree = ast.parse(Path("configs/base.py").read_text(encoding="utf-8"))
values = {
    node.targets[0].id: ast.literal_eval(node.value)
    for node in tree.body
    if isinstance(node, ast.Assign)
    and len(node.targets) == 1
    and isinstance(node.targets[0], ast.Name)
    and node.targets[0].id in targets
}
assert values == {
    "EXCHANGE_TIMEOUT_MS": 10_000,
    "EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT": "crypto-alpha-lab-research-readonly/0.1",
    "RISK_LIVE_TRADING_ENABLED": False,
}
PY
{
  git diff --name-only "$BASE_SHA"
  git diff --cached --name-only "$BASE_SHA"
  git ls-files --others --exclude-standard
} | LC_ALL=C sort -u > "$EXECUTION_BASELINE_DIR/current-changed-paths.txt"
comm -23 "$EXECUTION_BASELINE_DIR/current-changed-paths.txt" \
  "$EXECUTION_BASELINE_DIR/preexisting-paths.txt" \
  > "$EXECUTION_BASELINE_DIR/implementation-delta.txt"
printf '%s\n' \
  src/research/external_signal_shadow/stage1_6f_candidate_evidence_source.py \
  src/research/external_signal_shadow/stage1_6f_candidate_w1_descriptive_diagnostic.py \
  src/research/external_signal_shadow/stage1_6f_candidate_w1_diagnostic_storage.py \
  scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py \
  scripts/external_signal_shadow/run_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/research/external_signal_shadow/stage1_6f_candidate_w1_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_evidence_source.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_candidate_w1_diagnostic_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_candidate_w1_descriptive_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py \
  | LC_ALL=C sort > "$EXECUTION_BASELINE_DIR/allowed-implementation-delta.txt"
comm -23 "$EXECUTION_BASELINE_DIR/preexisting-paths.txt" \
  "$EXECUTION_BASELINE_DIR/allowed-implementation-delta.txt" \
  > "$EXECUTION_BASELINE_DIR/preexisting-no-touch-paths.txt"
python3 - \
  "$EXECUTION_BASELINE_DIR/preexisting-path-states.jsonl" \
  "$EXECUTION_BASELINE_DIR/preexisting-no-touch-paths.txt" \
  "$EXECUTION_BASELINE_DIR/preexisting-no-touch-states.final.jsonl" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

baseline_file, no_touch_file, output_file = map(Path, sys.argv[1:])
expected = {
    item["path"]: item
    for item in (json.loads(line) for line in baseline_file.read_text(encoding="utf-8").splitlines())
}
actual = []
for raw_path in no_touch_file.read_text(encoding="utf-8").splitlines():
    path = Path(raw_path)
    if path.is_symlink():
        payload, state = os.readlink(path).encode("utf-8"), "symlink"
    elif path.is_file():
        payload, state = path.read_bytes(), "file"
    elif not path.exists():
        payload, state = b"", "missing"
    else:
        raise SystemExit(f"STOP=preexisting_path_unsupported:{raw_path}")
    item = {"path": raw_path, "state": state, "sha256": hashlib.sha256(payload).hexdigest()}
    if item != expected[raw_path]:
        raise SystemExit(f"STOP=preexisting_no_touch_changed:{raw_path}")
    actual.append(item)
output_file.write_text(
    "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in actual),
    encoding="utf-8",
)
PY
diff -u "$EXECUTION_BASELINE_DIR/allowed-implementation-delta.txt" \
  "$EXECUTION_BASELINE_DIR/implementation-delta.txt" \
  || { echo 'STOP=implementation_delta_scope_violation' >&2; exit 1; }
grep -Fx 'scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py' \
  "$EXECUTION_BASELINE_DIR/implementation-delta.txt" >/dev/null \
  || { echo 'STOP=collector_adapter_delta_missing' >&2; exit 1; }
```

Expected: no whitelist escape, no immutable authority/config/root mutation, no changed pre-existing No-Touch byte/state and no staged/index drift. The mutable collector is present in the approved implementation delta from its Task-0 baseline; Task 1's delegation/equivalence regressions, run again in Task 5, prove that its changed bytes are the required thin adapter rather than an unrelated change. Preserve any unrelated dirty file; do not reset or delete it.

### Step 4: Update graph once and hand off a Blind-first audit

After all code/tests pass, run exactly once:

```bash
graphify update .
```

Re-run Step 3 after the ignored `graphify-out/**` change. Then invoke `verification-before-completion` and `requesting-code-review`. Required findings must be repaired before audit.

The independent completion auditor receives only: approved Plan path/SHA, approved Design path/SHA, `BASE_SHA`, `EXECUTION_BASELINE_DIR`, exact allowed implementation paths and known unresolved blockers. Do not give it executor-authored success claims, test summaries or scanner summaries. It must independently run `.agent/skills/audit-plan-completion/SKILL.md`, inspect actual producer/consumer routing, verify scanner RC and issue `COMPLETE`, `INCOMPLETE` or `BLOCKED`.

## Execution Gates

```text
plan_status = draft_for_review
implementation_plan_approved = false
implementation_authorization_present = false
implementation_allowed = false
network_collection_allowed = false
commit_allowed = false
push_allowed = false
deployment_allowed = false
ssh_allowed = false
runtime_action_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

This document does not authorize its own execution. Independent Plan review plus explicit user approval of this exact Plan SHA may set only `implementation_plan_approved=true`. A separate user implementation authorization bound to the unchanged Plan SHA is still required before code/test work. Completion never grants commit, push, deployment, SSH, runtime action, network collection, replay, paper trading or live trading.
