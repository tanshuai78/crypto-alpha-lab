# Stage 1.6F Historical Evidence Package Expansion Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: use `executing-plans` to implement this Plan task-by-task after external Plan approval.

**Goal:** 在不改变现有 Stage 1.6F REEF-only reader、B/C 根或交易权限的前提下，实现一次性、公开只读的历史候选证据包采集器和独立严格校验器。

**Architecture:** 新增一个脚本模块作为唯一 collector/validator 边界。它只通过既有 C 严格加载器和冻结的 `reconstruct_denominator` 推导 cohort，只向 coverage matrix 中的精确 URL 发出每 physical object 一次的无重定向 GET，并以 manifest-last 写入不可变 candidate root。独立 validator 只能读取 completed root 与外部批准记录，不能使用 collector 内存状态；现有 F reader 继续拒绝新 manifest identity。

**Tech Stack:** Python 标准库 `argparse`, `csv`, `hashlib`, `json`, `os`, `pathlib`, `tempfile`, `time`, `urllib`, `zipfile`; pytest; ruff; project anti-shortcut scanner.

---

## Governance And Design Authority

**Approved Design:** `docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md`
**Approved Design SHA-256:** `1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4`

This Plan implements only that Design. Plan review and Plan approval do not authorize implementation. A separate explicit user implementation authorization bound to this Plan's exact SHA is required before any code or test file is created or modified. Neither authority authorizes a network request, data collection, F admission, commit, push, deployment, SSH, replay, paper trading, or live trading.

The following frozen workspace authorities are rechecked by Task 0:

| Authority | Path | SHA-256 |
| --- | --- | --- |
| Parent F Design | `docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md` | `87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c` |
| F evidence-to-schema Delta | `docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md` | `8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628` |
| Approved F Plan | `docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md` | `6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f` |
| REEF evidence manifest | `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json` | `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f` |
| Coverage matrix | `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json` | `b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8` |
| C completion manifest | `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json` | `226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0` |
| C source receipt | `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/source_export_receipt.json` | `07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e` |
| B sealed manifest | `data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090/sealed_export_manifest.json` | `1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be` |
| F denominator module | `src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py` | `84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3` |
| F source verifier | `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py` | `00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f` |
| C registered test-fixture factory | `tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py` | `e7ff8ae12594e52a33a0c31721dba0296e5e5e2e911ac9862eca823fd0c3e1fc` |
| Timeout and user-agent SSOT | `configs/base.py` | `09ab3e787f49da6001050c5f2c6894f3665c8ffb766b6d4f0b2718dea08044f6` |
| Anti-shortcut scanner | `.agent/tools/anti_shortcut_scan.py` | `11f99b60a1b3e3d342e82f5113979129e0a9d5c90617ddc44fded3d972b50748` |

Before implementation, the executor needs an explicit user statement bound to this exact Plan SHA:

```text
I authorize implementation of Plan: <path> (SHA-256: <exact approved Plan SHA>).
Implementation only; no commit, push, deployment, SSH, runtime action, or network collection.
```

Before any real collection, the collector additionally needs these external inputs:

```text
approved Design path + SHA-256
approved Plan path + SHA-256
one-run network authorization JSON
external expected SHA-256 of that exact authorization file
```

The authorization file is exact UTF-8 JSON with no extra keys:

```json
{
  "run_id": "<collector run id>",
  "approved_design_sha256": "<64 lowercase hex>",
  "approved_plan_sha256": "<64 lowercase hex>"
}
```

The external user supplies the expected authorization-file SHA independently, for example in a one-run authorization statement. The collector accepts both `--network-authorization-file` and `--network-authorization-sha256`; before creating a root or opening a network connection it requires `SHA256(file bytes) == --network-authorization-sha256`, then records that verified value as `network_collection_authorization.authorization_record_sha256`. The collector/executor must never derive the expected SHA from the file it is checking. Design approval, Plan approval, and implementation authorization alone never authorize a request.

## Invariant Map

| Invariant | Implementation | Proof | Fail-closed result |
| --- | --- | --- | --- |
| INV-EP01 | CLI authority gate | authority mutations before fetch | `approved_authority_mismatch`, zero fetches/root |
| INV-EP02 | C loader + denominator/cohort | real C/matrix plus raw-C shortcut mutation | `candidate_cohort_authority_mismatch`, zero fetches |
| INV-EP03 | no-redirect single fetch | local 3xx/timeout/429 call counters | terminal status, one request |
| INV-EP04 | logical/physical enumerator | ID vectors, 705/664, duplicate mutations | `candidate_root_invalid` |
| INV-EP05 | ZIP/CSV and family reducer | unsafe ZIP, header, symbol, time, ladder mutations | `archive_invalid` or `csv_invalid/not_proven` |
| INV-EP06 | separate completed-root validator | manifest/byte/key/record/state mutations | `candidate_root_invalid` |
| INV-EP07 | exclusive root and atomic persistence | collision and local-write failure | run-fatal, no final manifest |
| INV-EP08 | existing F compatibility | current reader receives candidate manifest | candidate identity rejected |
| INV-EP09 | output schema/AST | forbidden domain/output assertions | test failure |
| INV-EP10 | permission mapping | true/non-bool flag mutations | validator rejection |

## Allowed Change Scope

Allowed implementation paths:
- `scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py`

Allowed verification paths:
- `tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py`

Allowed documentation paths:
- none

Allowed generated/runtime artifacts:
- `data/external_signal_shadow/stage1_6f/evidence_candidates/<run_id>/**` - generated only, ignored, never committed
- `graphify-out/**` - generated graph output, ignored, never committed
- `$(git rev-parse --git-path "plan-execution/<run_id>")/**` - executor baseline evidence in Git metadata only, never committed

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py`
  - source SHA remains `84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3`; collector uses only `reconstruct_denominator`.
- `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py`
  - source SHA remains `00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f`; `verify_c_input` remains the retained-byte C boundary and `verify_market_evidence` continues to reject candidate identity.
- `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py`
  - `verify_c_input` continues to reach canonical `load_completed_adapter_audit`; no B/C artifact is written.
- `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/**`
  - `gap02_evidence_manifest.json` remains `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f`.
- `configs/base.py`
  - source SHA remains `09ab3e787f49da6001050c5f2c6894f3665c8ffb766b6d4f0b2718dea08044f6`; `EXCHANGE_TIMEOUT_MS == 10000` and `EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT == "crypto-alpha-lab-research-readonly/0.1"`; capacity checks use the exact bytes of each atomic write and `statvfs`, not a new threshold.
- `tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py`
  - source SHA remains `e7ff8ae12594e52a33a0c31721dba0296e5e5e2e911ac9862eca823fd0c3e1fc`; it remains the only registered canonical C positive-fixture factory.

Forbidden:
- Any mutation outside the allowed paths.
- Any change to the approved Design, Parent/Delta Design, approved F Plan, current F code/tests, B/C roots, REEF package, or `configs/base.py`.
- Real collection during tests; retry, redirect follow, private/authenticated endpoint, VPS/SSH action, scheduler, daemon, queue, database, generic exchange adapter, F admission, control selection, alpha/PnL/replay/paper/live-trading action.
- Unrelated formatting, `ruff check --fix .`, `git clean`, staging, commit, push, or deployment.

## Task 0: Freeze Baseline And Authority Packet

**Invariant:** INV-EP01, INV-EP08, INV-EP10.
**Files:** Append Plan-specific evidence to the canonical `$(git rev-parse --git-path "plan-execution/<run_id>")/**`; never create or replace that baseline.

**Precondition: separate implementation authority.**

The executor must receive the exact user implementation-authorization statement defined above, verify that its path and SHA equal this independently approved Plan, and record its literal bytes in the execution report. Plan review/approval without that statement is `STOP=implementation_authorization_missing`; do not create or modify the script/test file. This precondition grants implementation only, never a network request.

**Step 1: Bind, do not recreate, the canonical execution baseline.**

`execute-approved-plan` Step 1 is the only owner that creates `BASE_SHA`, `EXECUTION_RUN_ID`, `EXECUTION_BASELINE_DIR`, `status.txt`, `worktree.patch`, `index.patch`, `untracked-paths.txt`, and `untracked-sha256.txt`. It must also create the following derived files in that same Step 1, before Task 0 and before any Plan file is modified:

```bash
set -euo pipefail
git diff --name-only "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/tracked-worktree-paths.txt"
git diff --cached --name-only "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/tracked-index-paths.txt"
cat "$EXECUTION_BASELINE_DIR/tracked-worktree-paths.txt" \
    "$EXECUTION_BASELINE_DIR/tracked-index-paths.txt" \
    "$EXECUTION_BASELINE_DIR/untracked-paths.txt" | LC_ALL=C sort -u \
    > "$EXECUTION_BASELINE_DIR/preexisting-paths.txt"
git ls-files -s -z | shasum -a 256 | awk '{print $1}' > "$EXECUTION_BASELINE_DIR/index.sha256"
printf '%s\n' "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/base_sha.txt"
```

Task 0 only binds and validates that pre-existing snapshot:

```bash
set -euo pipefail
: "${BASE_SHA:?STOP=execution_baseline_missing}"
: "${EXECUTION_RUN_ID:?STOP=execution_baseline_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=execution_baseline_missing}"
test -d "$EXECUTION_BASELINE_DIR" || { echo 'STOP=execution_baseline_missing' >&2; exit 1; }
test "$(cat "$EXECUTION_BASELINE_DIR/base_sha.txt")" = "$BASE_SHA" || { echo 'STOP=execution_baseline_mismatch' >&2; exit 1; }
test "$(git rev-parse HEAD)" = "$BASE_SHA" || { echo 'STOP=execution_baseline_mismatch' >&2; exit 1; }
for file in status.txt worktree.patch index.patch untracked-paths.txt untracked-sha256.txt \
  tracked-worktree-paths.txt tracked-index-paths.txt preexisting-paths.txt index.sha256; do
  test -f "$EXECUTION_BASELINE_DIR/$file" || { echo "STOP=execution_baseline_missing:$file" >&2; exit 1; }
done
```

Expected: one workflow-owned pre-execution baseline is present, unchanged, and reusable by executor and blind-first auditor. Nothing is reverted, staged, or re-baselined by Task 0.

**Step 2: Fingerprint immutable upstream evidence trees.**

Fingerprint exactly the C completed audit root, the B sealed-export root referenced by it, and the frozen REEF evidence root before any code/test action. A fingerprint entry contains `relative_path`, `file_type`, `mode`, `byte_length`, and `sha256`; regular-file bytes and symlink target bytes are hashed without following symlinks.

```bash
set -euo pipefail
cat > "$EXECUTION_BASELINE_DIR/fingerprint_upstream.py" <<'PY'
import hashlib, json, os, pathlib, stat, sys

def entry(root, path):
    st = path.lstat()
    rel = "." if path == root else path.relative_to(root).as_posix()
    if stat.S_ISREG(st.st_mode): raw, kind = path.read_bytes(), "file"
    elif stat.S_ISLNK(st.st_mode): raw, kind = os.fsencode(os.readlink(path)), "symlink"
    elif stat.S_ISDIR(st.st_mode): raw, kind = b"", "directory"
    else: raise SystemExit(f"STOP=unsupported_upstream_file_type:{path}")
    return {"relative_path": rel, "file_type": kind, "mode": stat.S_IMODE(st.st_mode),
            "byte_length": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

fingerprints = {}
for raw in sys.argv[2:]:
    label, raw_path = raw.split(":", 1)
    root = pathlib.Path(raw_path)
    if not root.is_dir() or root.is_symlink(): raise SystemExit(f"STOP=upstream_root_invalid:{root}")
    fingerprints[label] = [entry(root, root)] + [entry(root, path) for path in sorted(root.rglob("*"))]
pathlib.Path(sys.argv[1]).write_text(json.dumps(fingerprints, sort_keys=True, separators=(",", ":")), encoding="utf-8")
PY
python3 "$EXECUTION_BASELINE_DIR/fingerprint_upstream.py" \
  "$EXECUTION_BASELINE_DIR/upstream-tree-fingerprints.json" \
  "C:data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z" \
  "B:data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090" \
  "REEF:tests/fixtures/external_signal_shadow/stage1_6f/evidence_package"
```

Expected: one deterministic, non-following fingerprint per immutable tree. A missing root, unsupported type, or later byte/mode/path change is `STOP=upstream_evidence_mutated`.

**Step 3: Recompute all frozen bytes and tool policy.**

Verify the approved Design SHA above and every exact path/SHA pair in the authority table. Verify by literal source parsing that `configs/base.py` still declares `EXCHANGE_TIMEOUT_MS = 10_000` and `EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT = "crypto-alpha-lab-research-readonly/0.1"`; config hash/value drift is Rule-12 `STOP=BLOCKED_SPEC_DRIFT`, never a silently adopted transport policy.

```bash
set -euo pipefail
check_sha() { test "$(shasum -a 256 "$1" | awk '{print $1}')" = "$2"; }
while IFS=' ' read -r expected target_path; do
  check_sha "$target_path" "$expected" || { echo "STOP=approved_authority_mismatch:$target_path" >&2; exit 1; }
done <<'EOF'
87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md
8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628 docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md
1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4 docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md
6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md
9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json
b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8 tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json
226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0 data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json
07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/source_export_receipt.json
1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090/sealed_export_manifest.json
84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3 src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py
00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py
e7ff8ae12594e52a33a0c31721dba0296e5e5e2e911ac9862eca823fd0c3e1fc tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py
09ab3e787f49da6001050c5f2c6894f3665c8ffb766b6d4f0b2718dea08044f6 configs/base.py
11f99b60a1b3e3d342e82f5113979129e0a9d5c90617ddc44fded3d972b50748 .agent/tools/anti_shortcut_scan.py
EOF
python3 - <<'PY'
import ast
tree = ast.parse(open("configs/base.py", encoding="utf-8").read())
targets = {"EXCHANGE_TIMEOUT_MS", "EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT"}
values = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
          if isinstance(node, ast.Assign) and len(node.targets) == 1
          and isinstance(node.targets[0], ast.Name) and node.targets[0].id in targets}
assert values["EXCHANGE_TIMEOUT_MS"] == 10_000
assert values["EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT"] == "crypto-alpha-lab-research-readonly/0.1"
PY
command -v graphify >/dev/null || { echo 'STOP=graphify_workflow_contract_unavailable' >&2; exit 1; }
graphify --help >/dev/null || { echo 'STOP=graphify_workflow_contract_unavailable' >&2; exit 1; }
git check-ignore -v graphify-out/.stage1_6f_expansion_probe >/dev/null || { echo 'STOP=graphify_output_not_ignored' >&2; exit 1; }
echo CHECK_OK=authorities_frozen
```

Expected: `CHECK_OK=authorities_frozen`. Any mismatch is `STOP=approved_authority_mismatch`.

**Step 4: Freeze Rule-12 routing.**

Every later step records intended change, command, and expected result. Do not advance after a failed gate. An approved local repair inside this whitelist is `BLOCKED_IMPLEMENTATION_DEFECT`; a necessary unlisted file is `BLOCKED_SCOPE_DRIFT`; a contradiction with frozen B/C/F/Design is `BLOCKED_SPEC_DRIFT`. Stop in all cases. Do not invent a fallback, URL, data row, hash, approval, or permission.

## Task 1: Add Authority, Cohort, And Canonical-ID RED Tests

**Invariant:** INV-EP01, INV-EP02, INV-EP04, INV-EP10.
**Files:** Create `tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py`.

**Step 1: Write failing tests.**

The tests must:
- obtain positive C bytes only through `verify_c_input(...)` and the registered canonical C fixture factory; never handcraft a completion manifest, receipt, contract JSONL, or positive C hash;
- parse the real frozen matrix, verify its SHA, and invoke the prefetch authority/cohort phase against actual C/B roots to prove the exact sorted 41 symbols and 705 logical / 664 physical record sets;
- construct temporary one-run authorization bytes only from actual Design/Plan bytes and test `run_id`, but pass the expected authorization SHA as a separate harness authority input; a collector helper must never calculate its own expected hash from the file under test. Mutate every authority field, module SHA, authorization field, expected hash, or extra key and assert `STOP=approved_authority_mismatch`, zero fetch calls, and no root;
- assert the two Design Section 5.2 canonical JSON vectors exactly; altered tuple order, whitespace, separator, projection, or full-row hash must reject;
- assert `authority_flags == EXACT_EXPECTED_13_FALSE_MAPPING`; reject a missing approved key, an extra false key, an extra true key, `True`, `0`, and `"false"`.

Use a local callable fetch double with a call counter. It receives original matrix URLs only; it opens no public network connection.

**Step 2: Run RED.**

```bash
.venv/bin/pytest -q tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py
```

Expected: FAIL because the collector module does not exist.

**Step 3: Add the smallest script skeleton.**

Create `scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py` with required CLI arguments:

```text
--project-root --source-export --completed-root --coverage-matrix --output-root
--run-id --approved-design-path --approved-design-sha256
--approved-plan-path --approved-plan-sha256
--network-authorization-file --network-authorization-sha256
```

Add pure helpers for canonical JSON hashing, exact object-key checks, authority file hashes, logical/physical enumeration, and a prefetch gate. The gate verifies frozen bytes, user approvals, and the externally supplied expected authorization-file SHA before it creates a root, accepts a fetch callable, or opens a socket; it then verifies `verify_c_input(...)` and `reconstruct_denominator(verified_c)`. Tests may inject a fetch callable only through an internal Python function; `main()` always uses the real no-redirect standard-library opener.

Do not add a new `src` package, config constant, registry, class hierarchy, or generic archive client.

**Step 4: Run GREEN.** Re-run Step 2. Expected: PASS with zero public requests.

## Task 2: Add One-Request Fetch, ZIP/CSV Validation, And Coverage Reducers

**Invariant:** INV-EP03, INV-EP04, INV-EP05.
**Files:** Modify the new script and test module only.

**Step 1: Add RED terminal-path tests.**

Use only a local test server or injected fixture double. Assert:
- 404 -> `archive_not_found_404/unavailable`;
- first 3xx -> `redirect_refused/not_proven`, no redirect request;
- timeout, TLS-style `URLError`, 429, malformed response -> `transport_inconclusive/not_proven`, exactly one request each;
- corrupt ZIP, multiple member, directory, encrypted flag, symlink-like mode, traversal, duplicate or unexpected member -> `archive_invalid/not_proven`;
- header/type/timestamp/duplicate/BookDepth ladder -> `csv_invalid/not_proven`;
- one wrong case-sensitive `metrics_5m.symbol` -> `csv_invalid/not_proven`, with no row contributing to `metric_window_coverages`;
- valid grid gap -> `fetched_verified/window_incomplete`; valid funding, BookDepth, and agg-trades return only their approved non-grid outcomes.
- resolve the exact REEF raw files through `gap02_evidence_manifest.json`, verify each selected entry's hash/length, then pass the real archived ZIP/CSV bytes through the same new ZIP validator, CSV parser, and family reducer for `klines_1h`, `metrics_5m` (with `REEFUSDT` identity), `funding_rate`, `book_depth`, and `agg_trades`. These five tests are canonical parser positives, not synthetic fixtures.

**Step 2: Run RED.**

```bash
.venv/bin/pytest -q tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py -k 'fetch or zip or csv or coverage'
```

Expected: FAIL because fetch/parser/reducer logic is absent.

**Step 3: Implement minimal stdlib transport and parser.**

Implement directly in the script:
- `urllib.request` GET with redirect refusal, `ProxyHandler({})`, sequential execution, `base.EXCHANGE_TIMEOUT_MS / 1000.0` timeout, and `base.EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT`; the script reads but never changes either existing SSOT value;
- exactly one GET per deduplicated physical URL: no HEAD, retry, guessed URL, alternate host, credential, or private endpoint;
- retain ZIP bytes before `ZipFile.testzip()` and the exact single-member safety contract; never call `extract()` or `extractall()`;
- strict known-header parsing without coercion/default/row repair;
- Section 5.4 family reducers, validating every `metrics_5m.symbol` before coverage, invalidating its entire CSV on mismatch, and only then evaluating the 5-minute grid;
- physical terminal state copied exactly to every referenced logical record.

Synthetic ZIP/CSV bytes may be used only for one-point negative parser mutations and transport orchestration. They must not be the positive proof for a real Binance Vision family parser.

Before every atomic file write, require `os.statvfs(root).f_bavail * f_frsize >= 2 * len(serialized_bytes)`. The factor covers temporary and final files during `os.replace`; no global capacity threshold/config is added. A capacity, write, rename, read-back, or hash failure is run-fatal `candidate_root_invalid`.

**Step 4: Run GREEN.** Re-run Step 2. Expected: PASS; each fixture proves one request only.

## Task 3: Add Manifest-Last Persistence And Independent Validator

**Invariant:** INV-EP04, INV-EP06, INV-EP07, INV-EP09, INV-EP10.
**Files:** Modify the new script and test module only.

**Step 1: Add RED root-integrity tests.**

The separate validator must reject: reused root/run ID, missing manifest, stale temporary file, crash before manifest, local write failure, extra file, symlink, path escape, changed ZIP/CSV byte, wrong SHA/length, duplicate physical ID/path, missing/extra key or record, changed projection/full-row hash, non-terminal state, wrong root state, absent/mismatched post-collection authority, and any `authority_flags` mapping other than `EXACT_EXPECTED_13_FALSE_MAPPING`. Assert existing `verify_market_evidence(...)` rejects candidate identity.

Inject each durable-transition failure independently, with lifecycle-specific assertions:

- **Before final manifest publication:** ZIP temporary write, ZIP `os.replace`, ZIP read-back/hash, CSV temporary write, CSV `os.replace`, CSV read-back/hash, manifest temporary write, and manifest `os.replace`. Each must leave no final manifest, no consumable completed root, no resume/repair command, an unusable `run_id`, and require a fresh `run_id` for the next attempt.
- **After final manifest publication:** manifest post-write read-back failure and independent-validator rejection. Each must leave an immutable final manifest/root on disk but classify it `candidate_root_invalid` and non-consumable; the final manifest must not be deleted or rewritten. No resume/repair command is permitted, the same `run_id` remains unusable, and the next attempt requires a fresh `run_id`.

**Step 2: Run RED.**

```bash
.venv/bin/pytest -q tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py -k 'validator or manifest or root or permission'
```

Expected: FAIL before writer/validator implementation.

**Step 3: Implement root writer and reader.**

- Create `data/external_signal_shadow/stage1_6f/evidence_candidates/<run_id>` exclusively; an existing path is `STOP=candidate_run_id_collision`.
- Keep physical/logical/coverage staging in memory only.
- Atomically write collector-generated ID-based ZIP/CSV paths; read back and hash/length-check all files; derive root state; write exact-key manifest last.
- Add `validate_completed_candidate_root(...)`, which receives only completed root plus the three external inputs, rereads bytes from disk, recomputes authority/cohort/logical/physical/coverage/root state, and never consumes collector memory.
- Output only collection facts and `authority_flags == EXACT_EXPECTED_13_FALSE_MAPPING`; the reader rejects missing, extra, true, or non-bool entries.
- If post-publication read-back or the independent validator fails, retain the final manifest/root as immutable forensic evidence, mark it `candidate_root_invalid`, and never delete, repair, resume, or reuse it.

No F reader switch, compatibility alias, admission, report, or repair command.

**Step 4: Run GREEN.** Re-run Step 2. Expected: PASS; every corrupted root is non-consumable.

## Task 4: Add Full Frozen-Authority Integration And Regression Tests

**Invariant:** INV-EP01 through INV-EP10.
**Files:** Modify the new test module; modify script only if a test reveals an approved-contract defect.

**Step 1: Add canonical positive integration.**

Use the actual frozen C completed root, source export, B manifest, and coverage matrix from the approved Design; recompute their hashes first. Use the script's internal fetch seam only to prove URL routing and one-call physical-object orchestration. Its parser-positive payloads must be the real REEF ZIP/CSV bytes already verified in Task 2, never metric-appropriate minimal ZIP/CSV substitutes. Prove:

- canonical C plus `reconstruct_denominator` yields exactly 41 symbols, not 48 raw `source_audit_eligible` rows;
- 705 logical records map to 664 physical objects with 41 lawful shared URL references;
- every physical ID fetches once, root validates, remains candidate-only, and cannot enter current F;
- existing REEF package and both F module hashes remain unchanged.

The fixture double is only a transport-byte seam. It must not substitute C/B/matrix authority bytes or invent a C result. If those local authorities are absent or hash-mismatched, fail as authority failure rather than inserting synthetic positive evidence.

**Step 2: Add no-scope/no-permission assertions.**

AST/output checks reject imports of `requests`, `boto3`, exchange SDKs, SSH/process clients, F market reducers, F runner/writer/reviewer/control matcher, execution modules, and calls to `ZipFile.extract`/`extractall`. Candidate output must contain no control selection, alpha, PnL, execution, replay, or admission fields.

**Step 3: Run the new test module.**

```bash
.venv/bin/pytest -q tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py
```

Expected: PASS; no public request and no existing-input mutation.

**Step 4: Run F regressions.**

```bash
.venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6f_*.py tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py
```

Expected: PASS. Any F source/package change or candidate-reader acceptance is `STOP=BLOCKED_SCOPE_DRIFT` or `STOP=BLOCKED_SPEC_DRIFT`.

## Task 5: Final Scope, Scanner, And Completion Audit

**Invariant:** all.
**Files:** modify none.

**Step 1: Run limited static check.**

```bash
.venv/bin/ruff check \
  scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py
```

Expected: exit `0`; do not autofix.

**Step 2: Capture actual scanner return code for both changed Python files.**

```bash
set -euo pipefail
test "$(shasum -a 256 .agent/tools/anti_shortcut_scan.py | awk '{print $1}')" = \
  "11f99b60a1b3e3d342e82f5113979129e0a9d5c90617ddc44fded3d972b50748" || { echo 'STOP=scanner_authority_changed' >&2; exit 1; }
SCANNER_OUT="$EXECUTION_BASELINE_DIR/anti_shortcut_scan.txt"
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" --all-lines \
  scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py \
  >"$SCANNER_OUT" 2>&1; then SCANNER_RC=0; else SCANNER_RC=$?; fi
cat "$SCANNER_OUT"
printf '%s\n' "$SCANNER_RC" > "$EXECUTION_BASELINE_DIR/anti_shortcut_scan.exitcode"
test "$SCANNER_RC" -eq 0 || { echo 'STOP=anti_shortcut_scan_nonzero' >&2; exit 1; }
```

Expected: actual process exit code `0`. Every warning requires a source-level disposition in completion-audit evidence; any ERROR/nonzero blocks completion.

**Step 3: Prove index/worktree scope.**

```bash
set -euo pipefail
test "$(git ls-files -s -z | shasum -a 256 | awk '{print $1}')" = "$(cat "$EXECUTION_BASELINE_DIR/index.sha256")" || { echo 'STOP=git_index_changed' >&2; exit 1; }
git diff --check -- scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py
git diff --binary > "$EXECUTION_BASELINE_DIR/final_worktree.patch"
git diff --cached --binary > "$EXECUTION_BASELINE_DIR/final_index.patch"
cmp "$EXECUTION_BASELINE_DIR/worktree.patch" "$EXECUTION_BASELINE_DIR/final_worktree.patch" || { echo 'STOP=preexisting_worktree_changed' >&2; exit 1; }
cmp "$EXECUTION_BASELINE_DIR/index.patch" "$EXECUTION_BASELINE_DIR/final_index.patch" || { echo 'STOP=preexisting_index_changed' >&2; exit 1; }
python3 - "$EXECUTION_BASELINE_DIR/untracked-sha256.txt" <<'PY'
import hashlib, pathlib, sys
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    expected, path = line.split("  ", 1)
    actual = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    assert actual == expected, f"STOP=preexisting_untracked_changed:{path}"
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
  scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_evidence_package_expansion.py \
  | LC_ALL=C sort > "$EXECUTION_BASELINE_DIR/allowed-implementation-delta.txt"
diff -u "$EXECUTION_BASELINE_DIR/allowed-implementation-delta.txt" \
  "$EXECUTION_BASELINE_DIR/implementation-delta.txt" \
  || { echo 'STOP=implementation_delta_scope_violation' >&2; exit 1; }
```

Expected: `implementation_delta` is exactly the two whitelisted source/test paths; existing dirty/untracked bytes remain baseline-identical; ignored runtime output is never committed. A new untracked debug file therefore fails rather than merely appearing in `git status`.

**Step 4: Re-fingerprint upstream evidence and rerun the canonical C loader.**

Re-run the Task 0 fingerprint script against the same roots, writing `upstream-tree-fingerprints-final.json`, then require byte-for-byte equality with `upstream-tree-fingerprints.json`. Rerun the canonical strict loader over the same roots:

```bash
set -euo pipefail
python3 "$EXECUTION_BASELINE_DIR/fingerprint_upstream.py" \
  "$EXECUTION_BASELINE_DIR/upstream-tree-fingerprints-final.json" \
  "C:data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z" \
  "B:data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090" \
  "REEF:tests/fixtures/external_signal_shadow/stage1_6f/evidence_package"
cmp "$EXECUTION_BASELINE_DIR/upstream-tree-fingerprints.json" \
    "$EXECUTION_BASELINE_DIR/upstream-tree-fingerprints-final.json" \
    || { echo 'STOP=upstream_evidence_mutated' >&2; exit 1; }
.venv/bin/python - <<'PY'
from pathlib import Path
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import verify_c_input
verify_c_input(
    project_root=Path('.').resolve(),
    completed_root=Path('data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z'),
    source_export=Path('data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090'),
)
PY
```

Expected: exact fingerprints and canonical loader success. Any change, missing root, or loader failure is `STOP=upstream_evidence_mutated`.

**Step 5: Graph update, self-verification, review, and independent completion audit.**

After all code and tests pass, run exactly once through the project Graphify CLI required by `AGENTS.md`:

```bash
graphify update .
```

Then re-run Step 3 after the ignored `graphify-out/**` update. If the project Graphify CLI is unavailable, stop with `STOP=graphify_workflow_contract_unavailable` before implementation; do not skip the graph update.

Before handoff, the executor must invoke `verification-before-completion` and run all Task 4/5 commands. Because this is a significant new collector/validator boundary, it must also invoke `requesting-code-review` and resolve any required finding before audit.

The final auditor must be an independent Subagent, independent session, or the user; the executor must not audit its own completion. Use `.agent/skills/audit-plan-completion/SKILL.md` with an initial blind-first handoff containing only: approved Plan path/SHA, approved Design path/SHA, `BASE_SHA`, `EXECUTION_BASELINE_DIR`, the exact allowed implementation paths, and known unresolved blockers. Do not provide task-completion claims, self-authored success summaries, scanner summaries, or test summaries. The independent audit checks code, tests, scanner actual RC, index/worktree scope, B/C/matrix authority, upstream tree fingerprints, and real producer/consumer paths. `COMPLETE` does not authorize commit, push, deployment, or collection.

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

Independent Plan review plus user Plan approval of this exact SHA sets only `implementation_plan_approved = true`; `implementation_allowed` remains `false`. Only a separate explicit user implementation authorization bound to the same exact Plan SHA sets `implementation_authorization_present = true` and permits code/test implementation. A separate one-run authorization file plus an externally approved expected file SHA remains mandatory before any public archive request. Completion never grants commit, push, deployment, SSH, runtime, replay, paper-trading, or live-trading authority.
