# Stage 1.3 R10 历史证据再准入预核查 Implementation Plan

> **For Codex:** 只有本 Plan 经独立审核、用户给出绑定本文件 SHA-256 的实施批准语句后，才可按 `executing-plans` 逐 Task 实施。当前文档不授权实施、数据读取、receipt 生成、网络、replay、交易、commit、push、部署或 SSH。

**Goal:** 新增一个纯本地、只读的 Stage 1.3 R10 历史证据再准入预核查路径。它只验证调用方提供的 bars 与 event ledger 是否能由一个早于历史 review 的 Git manifest 逐字节锚定，并输出受限的本地 receipt 或 fail closed；它不重新计算任何结果、不重开 Stage 1.3 策略。

**Architecture:** 新核心模块仅复用 `HistoricalBar` 的既有完整性语义。生产 CLI 只能把 `--bars-jsonl` 传给一次性 structural reader；reader 返回不含 OHLCV 或 bars path 的 `StructuralBarsSnapshot`，下游 event reader/reducer/receipt writer 只能接收该 snapshot。它以固定的历史 boundary commit 验证 Git blob manifest，以严格 allowlist 验证 event ledger 的 PIT identity，并以 manifest-last 的 same-filesystem staging directory 原子发布两个文件的 candidate receipt root。旧 `stage1_3_orchestrator` 会读取 forward outcome、成本和随机基线，因此 R10 不得导入它或任何 replay/metrics/baseline 模块。当前不存在经批准的 future consumer/audit grammar，故 future-consumer gate 恒定 fail-closed；本 Plan 不实现 consumer、audit verifier 或研究分析。

**Tech Stack:** Python 3 标准库、现有 `HistoricalBar`/Stage 1.3 model helpers、Git CLI、pytest、ruff、`shasum`、`.agent/tools/anti_shortcut_scan.py`。不引入依赖、服务、配置项或网络客户端。

---

## 1. Approved Design Binding

| Item | Exact value |
| --- | --- |
| Approved Design | `docs/designs/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-design_CN.md` |
| Approved Design SHA-256 | `1b5088316f4f7dd28424ae37702f7b78d6c5e5b4fb3f873e73282f6137619446` |
| Design status at Plan authoring | approved by user sentence; implementation remains unapproved |
| Historical review boundary commit | `b122dc0700446990b43cc6fe9f613bf76bc8025c` |
| R10 final claim | local input admission only; never an Alpha, expectancy, replay, venue-parity or execution claim |

An implementation invocation must receive all four externally approved values before it reads bars, an event ledger, Git manifest, or output root:

```text
APPROVED_DESIGN_PATH
APPROVED_DESIGN_SHA256
APPROVED_PLAN_PATH
APPROVED_PLAN_SHA256
```

The future implementation approval sentence supplies the Plan pair. The process recomputes both file hashes first. A missing, non-regular, symlinked or mismatching authority is `STOP=approved_authority_mismatch`; a Design-specific mismatch is additionally reported as `STOP=stage1_3_r10_readmission_design_approval_mismatch`.

## 2. Allowed Scope, No-Touch Set And Permissions

### 2.1 Files an approved implementation may add or change

| Path | Purpose |
| --- | --- |
| `src/research/external_signal_shadow/stage1_3_r10_readmission.py` | strict R10 authority/input/receipt core |
| `scripts/review_external_signal_shadow_stage1_3_r10_readmission.py` | explicit local CLI only |
| `tests/research/external_signal_shadow/test_stage1_3_r10_readmission.py` | core unit, negative-mutation and crash tests |
| `tests/scripts/test_review_external_signal_shadow_stage1_3_r10_readmission.py` | CLI admission and output-boundary tests |

Test-only temporary Git repositories and output roots must use `pytest` `tmp_path`. No fixture is written into `data/`, `reports/`, `/tmp` as durable project evidence, or a caller-selected repository directory.

### 2.2 Generated runtime root, only after separate execution authorization

The production CLI has no output-root argument. It may write only:

```text
data/external_signal_shadow/stage1_3/r10_readmission_preflight/<RUN_ID>/
```

where `RUN_ID` exactly matches:

```text
^stage1_3_r10_readmission_[0-9]{8}T[0-9]{6}Z$
```

This Plan authorizes neither creation of this root nor a preflight invocation. Unit tests must redirect the fixed parent through an internal test seam to `tmp_path`; production code must never accept an output-root, input-root, directory, glob, URL, stdin or environment-default input.

### 2.3 No-touch set

Do not change or import as an R10 execution dependency:

- `src/research/external_signal_shadow/stage1_3_orchestrator.py`
- `src/research/external_signal_shadow/stage1_3_replay.py`
- `src/research/external_signal_shadow/stage1_3_metrics.py`
- `src/research/external_signal_shadow/stage1_3_baseline.py`
- `scripts/run_external_signal_shadow_stage1_3_candidate_discovery.py`
- `src/research/external_signal_shadow/stage1_3_candidates.py`
- `configs/`, existing Stage 1.3 summary/review, roadmap/status documents, all historical artifacts, all Stage 1.5/1.6 paths, VPS/runbook paths and Git index.

`src/research/external_signal_shadow/stage1_3_models.py` is read-only and may be imported only for its existing `HistoricalBar`, `find_duplicate_bar_starts`, and `compute_bar_coverage` semantics. R10 must not duplicate or alter those validations.

### 2.4 Permission isolation

The exact 19-field authority deny vector defined in Design §8.3 remains bool `false` in every receipt. `RISK_LIVE_TRADING_ENABLED` remains `False`. The implementation must not call network APIs, subprocess shell commands, old replay paths, price/outcome evaluators, trading APIs, paper/live execution, SSH, deployment, or write/commit/push in the project Git repository. The canonical pytest Git fixture may initialize and commit only inside its own `tmp_path` to construct the Design-required ancestor graph; it cannot write the project worktree, refs, index or remotes and is not historical authority.

Any need for a new historical source, archive/sealed-root admission mechanism, event reconstruction, cross-symbol clustering, outcome calculation, runtime route or changed Design authority is `STOP=BLOCKED_SPEC_DRIFT`. Any necessary file outside §2.1 is `STOP=BLOCKED_SCOPE_DRIFT`.

## 3. Authority Edge to Implementation Matrix

| Design authority / invariant | Implementation task and proof | Fail-closed result |
| --- | --- | --- |
| §2 approved authority packet, INV-R10-02 | Task 0 hashes every frozen current byte; Task 2 verifies boundary-tree review/summary blobs and strict ancestor relation before manifest read | `STOP=stage1_3_r10_readmission_authority_mismatch` or `...historical_anchor_invalid` |
| §6.2 missing vs malformed | Tasks 2-3 use exact presence reducer; only complete absence creates listed gap reason, malformed supplied bytes stop | `STOP=stage1_3_r10_readmission_input_invalid` |
| §6.3 Git manifest schema | Task 2 validates exact top-level keys/types/values plus bars/ledger SHA and length | `STOP=stage1_3_r10_readmission_historical_anchor_invalid` |
| §6.4 PIT ledger schema, INV-R10-05 | Task 3 parses exact JSONL allowlist, sorted identity and pre-event timestamps against structural time index | `STOP=stage1_3_r10_readmission_event_ledger_invalid` |
| §6.5 structural/outcome separation, INV-R10-03 | Task 1 enforces `CLI -> read_structural_bars(path) -> StructuralBarsSnapshot -> downstream` ownership; production signatures and open-spy/AST wiring tests prove bars are opened exactly once and never exposed downstream | `STOP=stage1_3_r10_readmission_outcome_path_detected` |
| §8.1/8.4 root lifecycle, INV-R10-08 | Task 4 validates canonical root grammar, tests pre/post-rename failure and classifies only exact final bytes/checksum | `STOP=stage1_3_r10_readmission_receipt_invalid` |
| §8.2/8.2.1 receipt schema, INV-R10-07 | Task 4 independently validates exact nested key sets, status and cross-field combinations before publication and in loader tests | `STOP=stage1_3_r10_readmission_receipt_invalid` |
| §8.3 deny vector, INV-R10-10 | Task 4 requires exact 19 false bool keys; one missing, extra or true mutation rejects | `STOP=stage1_3_r10_readmission_receipt_invalid` |
| §8.4 external audit boundary, INV-R10-09 | Task 4 implements local published-receipt validation only; every current future-consumer call fails closed because no approved audit grammar/verifier exists | `STOP=stage1_3_r10_readmission_future_consumer_binding_missing` |
| §9 exact reducer | Task 5 integration tests distinguish valid absences (`evidence_gap`) from any invalid supplied object (STOP) and verify eligible only with both anchored inputs | status mismatch stops before root publication |
| §10 every negative obligation | Tasks 1-5 contain one RED mutation per invariant row, followed by GREEN regression | relevant exact STOP |
| §12 review/audit route | Task 6 captures actual scanner RC, scope/index proof, code review then fresh read-only Completion Audit | `INCOMPLETE` until audit, no authority promotion |

## 4. Task 0: Fresh Baseline, Approval, Scope And Safety Gates

**Repository files:** none. **Test/runtime output:** none before all checks pass. This Task runs before source/test creation in an implementation session.

### Step 0.1: Bind approved Plan and Design bytes

The executor reads the future user approval sentence, exports the four exact authority values from §1, then runs:

```bash
set -euo pipefail
cd "$PROJECT_ROOT"
test -L "$APPROVED_DESIGN_PATH" && { echo 'STOP=approved_authority_mismatch'; exit 1; }
test -L "$APPROVED_PLAN_PATH" && { echo 'STOP=approved_authority_mismatch'; exit 1; }
test "$(shasum -a 256 "$APPROVED_DESIGN_PATH" | awk '{print $1}')" = "$APPROVED_DESIGN_SHA256" || {
  echo 'STOP=stage1_3_r10_readmission_design_approval_mismatch'; exit 1;
}
test "$(shasum -a 256 "$APPROVED_PLAN_PATH" | awk '{print $1}')" = "$APPROVED_PLAN_SHA256" || {
  echo 'STOP=approved_authority_mismatch'; exit 1;
}
```

Recompute the eight Design §2 authority hashes and validate `b122dc0700446990b43cc6fe9f613bf76bc8025c^{commit}` before touching any caller data. Validate `RISK_LIVE_TRADING_ENABLED is False` by import/read-only assertion. Any mismatch stops without creating a data root.

### Step 0.2: Create the one immutable per-attempt provenance bundle

Task 0 creates the only baseline exactly once, before source/test creation. An ambient bundle path is prohibited:

```bash
set -euo pipefail
test -z "${EXECUTION_BASELINE_DIR+x}" || {
  echo 'STOP=stage1_3_r10_readmission_ambient_baseline_dir_forbidden' >&2
  exit 1
}
EXECUTION_BASELINE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/stage1_3_r10_readmission.XXXXXX")"
chmod 700 "$EXECUTION_BASELINE_DIR"
export EXECUTION_BASELINE_DIR
BASE_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/base_sha"
printf '%s  %s\n' "$(shasum -a 256 "$EXECUTION_BASELINE_DIR/base_sha" | awk '{print $1}')" base_sha \
  > "$EXECUTION_BASELINE_DIR/base_sha.sha256"
```

The bundle records, each with a direct sibling SHA-256 record and length record: `base_sha`; the four approved authority values; initial porcelain-v1 `-z` status; tracked worktree binary diff; cached binary diff; full `git ls-files -s` index snapshot; and `preexisting_path_ledger.jsonl`. The ledger contains every pre-existing tracked, staged, dirty and untracked path with path, porcelain XY, type, mode, worktree SHA-256 for regular files (or symlink target), plus index mode/blob/stage when indexed. It is comparison evidence, not a clean-worktree requirement.

The task captures each value before later Tasks may modify a file. Existing user changes are never permission to alter/revert them. After implementation, only §2.1 paths may differ from this original ledger, and every Git index entry must equal this original snapshot. Missing, altered or unreadable bundle evidence is `STOP=stage1_3_r10_readmission_provenance_unavailable`; it is never regenerated or rebaselined.

Define one reusable gate and run it at the start and end of every implementation Task, immediately before publication, before code-review request, and in the Completion Audit handoff:

```bash
test "$(shasum -a 256 "$EXECUTION_BASELINE_DIR/base_sha" | awk '{print $1}')" = \
  "$(awk '{print $1}' "$EXECUTION_BASELINE_DIR/base_sha.sha256")" || {
  echo 'STOP=stage1_3_r10_readmission_provenance_unavailable' >&2; exit 1;
}
test "$(git rev-parse HEAD)" = "$(cat "$EXECUTION_BASELINE_DIR/base_sha")" || {
  echo 'STOP=stage1_3_r10_readmission_head_drift' >&2; exit 1;
}
```

The same gate verifies each named direct record and compares all no-touch paths against the original ledger. It must not use `git reset`, `git checkout`, `git restore`, `git clean`, recapture a baseline, or create a repository `.tmp` file.

### Step 0.3: Graph/topology fallback discovery

`graphify` remains advisory and unavailable in the current workspace. Before adding R10 source, run the following read-only collision discovery and record its exact output in the immutable bundle:

```bash
set +e
rg -n --hidden \
  --glob '!docs/designs/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-design_CN.md' \
  --glob '!docs/plans/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-implementation-plan_CN.md' \
  'stage1_3_r10_readmission|r10_readmission_preflight|eligible_for_exploratory_expectancy_design|historical-manifest-git-commit|event-ledger-jsonl|load_verified_r10_receipt' \
  . > "$EXECUTION_BASELINE_DIR/topology_discovery.txt"
rg_rc=$?
set -e
printf 'RG_RC=%s\n' "$rg_rc" > "$EXECUTION_BASELINE_DIR/topology_discovery.rc"
case "$rg_rc" in
  0|1) ;;
  *)
    echo 'STOP=stage1_3_r10_readmission_topology_discovery_failed' >&2
    exit 1
    ;;
esac
```

`topology_discovery.rc` is a direct immutable attempt record and receives its own SHA-256/length records with the other Task 0 evidence. `RG_RC=1` is the only no-match result and is classified `none`; `RG_RC=0` requires classification of every hit as exactly one of `compatible_unchanged`, `BLOCKED_SCOPE_DRIFT`, or `BLOCKED_SPEC_DRIFT`; any other RC stops and can never be classified as `none`. The current expected result is `RG_RC=1` / `none`; do not install Graphify or silently merge a discovered producer/consumer. After source creation, the same query may match only the four §2.1 paths; any other newly introduced hit is routed by that classification. Completion Audit independently reads both the output and recorded actual `RG_RC`.

### Step 0.4: Canonical fixture boundaries

The canonical positive fixture is a **test-only** temporary Git repository built by a fixture factory. It copies the actual current review and summary bytes from the frozen Design authorities, creates a manifest commit that strictly precedes a fixture boundary commit, and uses `HistoricalBar` to serialize valid five-symbol JSONL bars. The fixture boundary commit identity is injected only into the pure Git-proof helper; it does not replace the fixed production `b122...` authority.

This proves parser/ancestor mechanics, not that real Stage 1.3 evidence exists. The production integration fixture must separately prove that the current repository with no supplied historical manifest returns only `evidence_gap`, never eligibility.

### Step 0.5: Initial negative probes

Before implementation, add tests that fail because the module/CLI does not yet exist, then implement only enough behavior to make them green:

- Design SHA mutation returns approval mismatch before input opening.
- absent paired Git manifest flags becomes `historical_anchor_absent`; a single flag is a STOP.
- a fake filesystem sidecar is not accepted as a historical anchor.
- an event row with an outcome field is a STOP.
- an invalid `RUN_ID` and duplicated-prefix staging path are a STOP.

## 5. Task 1: Isolated Structural Reader and Import Boundary

**Repository files:** add the core module and core test file from §2.1. Do not alter Stage 1.3 models or runner.

### Step 1.1: Implement only structural bars parsing

In `stage1_3_r10_readmission.py`:

1. Define frozen candidate, symbol, interval, count, coverage, authority-hash and deny-vector constants directly from approved Design bytes.
2. Require `--bars-jsonl` to name an existing local regular non-symlink file. Resolve neither arbitrary roots nor symlink targets.
3. Define one frozen `StructuralBarsSnapshot` dataclass. Its only fields are bar byte SHA-256, positive byte length, count, per-symbol coverage, and the immutable `(symbol, bar_start_ms, bar_end_ms)` time index. It has no `Path`, `HistoricalBar`, OHLCV or arbitrary raw-row field.
4. Implement `read_structural_bars(bars_path: Path) -> StructuralBarsSnapshot` as the only function permitted to open the bars path. Stream JSONL once while calculating its hash; for each non-empty line construct existing `HistoricalBar` with the old runner's eight required field names. Never print, log or serialize OHLCV numeric values.
5. After constructor validation, retain only `(symbol, bar_start_ms, bar_end_ms)` in the snapshot. Reuse `find_duplicate_bar_starts` and `compute_bar_coverage`; require the exact five-symbol universe, no duplicate starts, each coverage ratio `>= 0.98`, total count `86400`, and a 180-day span under the Design contract.
6. The event reader accepts `(event_ledger_path, StructuralBarsSnapshot)` only. The reducer/receipt writer accepts structural facts and parsed event identities only. None of these functions accepts a bars path, `HistoricalBar`, raw JSON row or OHLCV value; none can reopen bars or perform an event-relative lookup.

The module may use `hashlib`, `json`, `os`, `pathlib`, `re`, `stat`, `subprocess`, `tempfile` and `datetime` from the standard library. It must not add a framework, datastore, config knob or cache.

### Step 1.2: Enforce no outcome call path

The core imports only from `research.external_signal_shadow.stage1_3_models`; the production core and CLI are both parsed by the same AST guard. It rejects imports/references to:

```text
stage1_3_orchestrator
stage1_3_replay
stage1_3_metrics
stage1_3_baseline
run_stage1_3_candidate_discovery
compute_forward_metrics_from_entry_index
run_random_baseline_trials
```

It rejects HTTP/socket client imports and direct bars-file reads outside `read_structural_bars`. The guard verifies the production CLI references `args.bars_jsonl` exactly once and passes it directly to `read_structural_bars`; its later calls may receive only `StructuralBarsSnapshot`. This ownership proof, rather than a variable-name blacklist, is the final blind/PIT wiring gate.

### Step 1.3: RED/GREEN tests

- **Positive:** bars generated through the actual `HistoricalBar` constructor parse into `StructuralBarsSnapshot`; downstream function signatures expose neither bars path nor `HistoricalBar`.
- **Negative:** wrong 15m duration, duplicate bar start, insufficient coverage, wrong symbol set, wrong count, symlink path and malformed JSON each STOP before root creation.
- **Production wiring proof:** an integration `open` spy proves the CLI opens the bars file exactly once, through `read_structural_bars`; parsing an event ledger cannot cause a second bars open.
- **Negative regression:** the same AST guard receives a one-line test source mutation that performs a second `open(args.bars_jsonl)` or passes a `HistoricalBar` to event processing. It must reject that mutation and the real core/CLI sources are checked by the same guard.

## 6. Task 2: Git-Anchored Manifest Admission

**Repository files:** core module and core tests only.

### Step 2.1: Verify production authority before manifest access

Implement a production entrypoint that first checks all Design §2 current-workspace file hashes, then invokes Git without a shell:

```text
git cat-file -e b122dc0700446990b43cc6fe9f613bf76bc8025c^{commit}
git show b122dc...:docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md
git show b122dc...:reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json
```

Hash the returned bytes and require the exact review/summary SHAs from Design §2. The working-tree copies are also validated but never substitute for boundary-tree bytes.

### Step 2.2: Implement the sole v1 anchor mechanism

Accept the Git manifest only when both paired flags are supplied. Before any `git show <commit>:<path>`, require `--historical-manifest-git-commit` to match `^[0-9a-f]{40}$`, resolve `git rev-parse --verify "<value>^{commit}"`, and require the resolved full object ID byte-for-byte equals the supplied value. Then require it differs from `b122...` and `git merge-base --is-ancestor <value> b122...` succeeds. Store that exact full object ID, never the original rev-parse input, in the receipt. Read exactly `git show <full-commit>:<path>` bytes, parse UTF-8 JSON, and enforce the exact §6.3 key set/value set.

Never open a filesystem manifest path, search Git history, accept a branch/tag/ref name, infer a manifest location, or fall back to a newly created sidecar. Hash/length-match the mandatory bars bytes only after the Git blob schema is valid. A fully absent pair yields `historical_anchor_absent`; partial or invalid supplied pair is `STOP=stage1_3_r10_readmission_historical_anchor_invalid`.

### Step 2.3: Git fixture and negative mutations

The test fixture factory creates:

```text
manifest commit -> fixture boundary commit containing exact copied review/summary bytes
```

The generic helper may accept this fixture’s boundary identity exclusively under test; the production entrypoint always supplies fixed `b122...` and no CLI flag can override it.

Required RED mutations:

1. boundary review or summary blob differs by one byte;
2. manifest commit equals boundary;
3. manifest commit is not an ancestor;
4. Git object/path is unreadable;
5. branch name, tag name, abbreviated SHA, `HEAD`, `HEAD~1`, mixed/uppercase hex and non-40-hex commit input each reject before `git show <commit>:<path>`;
6. manifest has an extra/missing/wrong-type key;
7. bars SHA or length differs from supplied bytes;
8. caller-created matching filesystem sidecar is presented without a Git pair.

Every mutation must STOP with the anchor-specific result and leave no final root.

## 7. Task 3: Event-Ledger PIT Identity and Exact Reducer

**Repository files:** core module and core tests only.

### Step 3.1: Parse the ledger as identity, never as outcome data

Implement a streaming JSONL reader that permits exactly:

```text
candidate_name, symbol, source_bar_start_ms, source_bar_end_ms, event_available_at_ms
```

Require candidate names exactly in the two-item R10 array, fixed symbol universe, and reject a `relative_strength_vs_btc` row for `BTCUSDT`. Require strict ordering and uniqueness by `(candidate_name, symbol, event_available_at_ms)`, `end - start == 900000`, `available == end + 60000`, and one matching bars time-index identity. Reject any price, volume, metadata, cluster, entry, exit, return, PnL, cost, MAE, MFE or unknown key.

When a valid manifest is anchored, require event-ledger SHA/length match its manifest values. When anchor is absent, preserve ledger SHA/length but set `matches_historical_manifest=false`; do not let compatible content establish history.

### Step 3.2: Implement exact absence reducer

The reducer has no best-effort branch:

| Manifest pair | Ledger | Result before publication |
| --- | --- | --- |
| absent | absent | `evidence_gap`, reasons exactly sorted `historical_anchor_absent`, `event_ledger_absent` |
| absent | valid supplied | `evidence_gap`, reason exactly `historical_anchor_absent` |
| anchored valid | absent | `evidence_gap`, reason exactly `event_ledger_absent` |
| anchored valid | valid and manifest-matching | `eligible_for_exploratory_expectancy_design`, reasons `[]` |
| partial/malformed/conflicting supplied object | any | STOP, no root |

The receipt always sets `independent_unit_status=deferred_to_future_exploratory_design`, `post_event_outcome_accessed=false`, and has no parent/cluster count. `eligible...` means only a future exploratory Design may be proposed; it is not `reconsider_under_expectancy_framework`, `phenomenon_supported`, Alpha or research execution authority.

### Step 3.3: Required negative proof

Test each presence-row and add individual mutations for extra ledger key, unsorted/duplicate identity, invalid candidate/symbol, BTC relative-strength row, timestamp mismatch, missing bar identity, anchored event hash mismatch and an attempted event-relative outcome field/access. All invalid supplied inputs STOP; only actual absence reaches an `evidence_gap` receipt.

## 8. Task 4: Receipt, Atomic Publication, Crash Classification and Strict Loading

**Repository files:** core/CLI/tests named in §2.1. No current receipt is generated outside test temporary roots.

### Step 4.1: Write and independently validate the exact receipt

Build a canonical JSON receipt only from validated facts. Before staging write, validate its exact top-level and nested keys, §8.2 status matrix, §8.2.1 input cross-field matrix, lexicographically sorted de-duplicated gap list and exact 19-key false deny vector.

Write exactly these two regular non-symlink files into the canonical staging root:

```text
r10_readmission_receipt.json
SHA256SUMS
```

`SHA256SUMS` covers the receipt with a named standard line. The writer fsyncs the receipt, checksum and staging directory, atomically renames the staging directory to final root on the same filesystem, then fsyncs the final parent. It creates the fixed parent only after all input gates pass. A preexisting/symlinked final root, invalid run ID, wrong parent, duplicate run ID, unexpected staging grammar or cross-device rename possibility stops; there is no resume writer and no overwrite/repair/rebaseline path.

### Step 4.2: State is determined by final bytes, not process state

Implement a local classifier with only Design §8.1 states. It validates exactly two final files and checksum before recognizing `receipt_published`; a `state.*` file, process exit code, stale staging directory or missing Completion Audit is irrelevant to publication state. A strict local receipt reader rejects missing/extra files, symlinks, broken checksum, schema mutations, false-vector mutation and any cross-field inconsistency.

Test both crash points by injected hooks, not actual process killing:

1. failure before `os.replace()` leaves no final root and requires a new run ID;
2. injected exception immediately after successful `os.replace()` leaves a valid final root classified as `receipt_published` if exact bytes/checksum validate;
3. corruption/missing/extra file after rename is `corrupt_or_unknown` and stops;
4. an existing final root prevents a second invocation even if its bytes are valid.

### Step 4.3: Future binding is intentionally unavailable in this Plan

Implement `load_local_published_r10_receipt(final_root)` only. It verifies the two-file final tree, internal checksum and exact local receipt schema, then returns local evidence facts with no consumer authority.

No `load_verified_r10_receipt`, caller-supplied callback, verifier protocol, audit parser or future consumer is implemented in this Plan. Since no approved future exploratory Design defines a Completion Audit artifact grammar or verifier identity, any current attempt to request `future_consumer_allowed` must unconditionally fail with `STOP=stage1_3_r10_readmission_future_consumer_binding_missing`, before it can consume receipt facts as research input. It must not accept an arbitrary audit path/SHA or callable verifier as a substitute.

Unit tests prove the local loader never returns consumer authorization and that a hypothetical call requesting future consumption rejects even when both receipt and checksum are self-consistent. Replacing both local receipt and checksum files cannot turn local publication into external authority. A later approved consumer Design must define the audit artifact grammar, verifier identity and exact binding contract in its own implementation scope.

## 9. Task 5: CLI, Integration Tests and Mechanical Gates

**Repository files:** add the CLI and CLI test from §2.1. The CLI is the only production writer entrypoint.

### Step 5.1: CLI contract

Expose exactly these data-source flags:

```text
--bars-jsonl PATH                         required
--historical-manifest-git-commit COMMIT   paired optional
--historical-manifest-git-path PATH       paired optional
--event-ledger-jsonl PATH                 optional
```

Expose only the non-data operational binding flags needed by the Design:

```text
--run-id RUN_ID
--approved-design-path PATH
--approved-design-sha256 SHA256
--approved-plan-path PATH
--approved-plan-sha256 SHA256
```

There is no `--output`, `--output-root`, `--input-root`, `--resume`, `--url`, `--glob`, `--directory`, `--stdin`, `--network`, `--replay`, `--fixture-run`, strategy, cost, horizon or permission override flag. The repository root is derived from the script location, not a user option. The CLI prints only status, stop code, run ID and output relative path; it never prints bars, prices, volumes, event outcomes or economic statistics.

### Step 5.2: Integration fixture and negative CLI matrix

With the canonical test Git factory, prove:

- full anchored bars/ledger produces exactly one two-file receipt with `eligible_for_exploratory_expectancy_design` only in `tmp_path`;
- missing manifest and/or ledger produces an exact `evidence_gap` receipt with only allowed reason names;
- no manifest supplied from the actual current repository cannot become eligible;
- partial flags, corrupted authority bytes, malformed paths, invalid root grammar, Git non-ancestor, ledger mutation and duplicate final root produce nonzero RC/no final root;
- CLI cannot accept prohibited flags and never creates a root outside its fixed parent test seam.

### Step 5.3: Scope/index and scanner gates

Run after all tests pass and record actual outputs/RCs in the implementation handoff:

```bash
pytest -q \
  tests/research/external_signal_shadow/test_stage1_3_r10_readmission.py \
  tests/scripts/test_review_external_signal_shadow_stage1_3_r10_readmission.py
ruff check \
  src/research/external_signal_shadow/stage1_3_r10_readmission.py \
  scripts/review_external_signal_shadow_stage1_3_r10_readmission.py \
  tests/research/external_signal_shadow/test_stage1_3_r10_readmission.py \
  tests/scripts/test_review_external_signal_shadow_stage1_3_r10_readmission.py
git diff --check -- \
  src/research/external_signal_shadow/stage1_3_r10_readmission.py \
  scripts/review_external_signal_shadow_stage1_3_r10_readmission.py \
  tests/research/external_signal_shadow/test_stage1_3_r10_readmission.py \
  tests/scripts/test_review_external_signal_shadow_stage1_3_r10_readmission.py
```

For each allowed path that is untracked relative to the original bundle, run `git diff --no-index --check /dev/null "$path"`, capture stderr/stdout, and require it is empty; Git RC `1` is expected for a new file, while any whitespace diagnostic is `STOP=stage1_3_r10_readmission_diff_check_failed`. Do not let an unrelated pre-existing worktree whitespace error block this Plan.

Capture the anti-shortcut scanner’s actual process RC, rather than trusting a summary:

```bash
set +e
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$(cat "$EXECUTION_BASELINE_DIR/base_sha")"
scanner_rc=$?
set -e
printf 'SCANNER_RC=%s\n' "$scanner_rc"
test "$scanner_rc" -eq 0 || { echo 'STOP=stage1_3_r10_readmission_scanner_failed' >&2; exit 1; }
```

Use `git diff --name-only "$(cat "$EXECUTION_BASELINE_DIR/base_sha")" --`, `git diff --cached --name-only`, and `git status --porcelain=v1 -z --untracked-files=all` with the original Task 0 index snapshot/full pre-existing-path ledger. Compare every pre-existing path to its original ledger and require every newly changed or newly untracked path is exactly one of the four §2.1 paths; require no index entry changed. `graphify` is advisory only: current `.venv/bin/python -m graphify` is unavailable (`No module named graphify`), so implementation records that fact but neither installs it nor treats its absence as a passing proof. The Task 0 topology discovery is rerun against the original bundle and must show no newly affected producer/consumer outside §2.1.

## 10. Task 6: Rule-12 Routing, Review and Completion Audit

1. Before an independent code review, rerun the immutable-bundle integrity/HEAD/no-touch comparison and every Task 1-5 gate against the same original `base_sha`. A test/scanner claim alone cannot replace direct source/diff inspection. Task 0 baseline capture itself never reruns.
2. Request `requesting-code-review` for the exact allowed paths, new module, CLI, tests and this Plan/Design bindings. The reviewer must verify all §3 edges, cross-boundary fixture limitation, outcome-import AST guard, each negative mutation, crash classification, strict loader fail-closed state, scope/index proof and 19 false flags.
3. Any review finding routes first through `receiving-code-review` and then exactly one Rule-12 class. An executor-local defect whose minimum correction stays inside §2.1 and preserves the approved Design/Plan is `STOP=BLOCKED_IMPLEMENTATION_DEFECT` until repaired; after repair, rerun all applicable RED/GREEN and final gates against the original immutable Task 0 bundle. A required file outside §2.1 is `STOP=BLOCKED_SCOPE_DRIFT`. A mismatch between approved Design/Plan and frozen upstream source/authority, including a needed historical admission, audit grammar, rule, data-root or permission change, is `STOP=BLOCKED_SPEC_DRIFT`. No class permits Task 0 re-capture, rebaseline, Git reset/checkout, or silent authority substitution.
4. After code review has zero open findings, request a fresh independent read-only Completion Audit. It must recompute approved Plan/Design hashes, inspect actual source/test diff/index/untracked state, run its own tests and `.agent/tools/anti_shortcut_scan.py`, and read the scanner’s actual RC. It must not create/repair a receipt root.
5. `COMPLETE` means only that the offline implementation meets this Plan. It does not authorize a preflight execution, historical evidence discovery, new Design, replay, Alpha claim, paper/live trading, network, commit, push, SSH or deployment.

## 11. Final Verification Checklist

- [ ] Approved Design and Plan bytes hash-match external user approvals before input read.
- [ ] One original immutable Task 0 bundle records authority bytes, `base_sha`, full worktree/index/untracked provenance and topology discovery; it is never recaptured after implementation starts.
- [ ] Every Task, publication, review and audit handoff proves current `HEAD` equals the recorded original `base_sha`.
- [ ] All eight frozen authorities and boundary-tree review/summary blobs are independently revalidated.
- [ ] Manifest input is a lowercase exact 40-hex commit OID that resolves to itself before any Git blob read; no ref/rev expression is accepted.
- [ ] Only existing `HistoricalBar` semantics parse bars; production wiring opens bars exactly once into `StructuralBarsSnapshot`, and no downstream path can receive bars/OHLCV or import old replay components.
- [ ] Git blob manifest is the only v1 history anchor; a fresh sidecar never establishes history.
- [ ] Missing evidence yields only the exact allowed `evidence_gap`; malformed supplied evidence stops with no final root.
- [ ] PIT ledger identity is exact, sorted, pre-event and contains no outcome/economic field.
- [ ] Receipt schemas, input matrix, run/root/staging grammar and 19 false flags reject every mutation.
- [ ] Pre-rename and post-rename crash cases are classified solely from final bytes/checksum; no resume writer exists.
- [ ] Future consumption is unconditionally fail-closed; no audit verifier, consumer or analysis is implemented before a new approved Design defines its authority.
- [ ] Targeted pytest/ruff, tracked/untracked path-scoped diff checks, original-ledger scope/index proof and scanner actual `RC=0` pass.
- [ ] Independent code review and fresh read-only Completion Audit complete before any separate user decision.
