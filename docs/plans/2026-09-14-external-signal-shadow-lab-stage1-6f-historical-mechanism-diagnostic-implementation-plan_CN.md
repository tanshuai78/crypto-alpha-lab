# Stage 1.6F Historical Mechanism Diagnostic Implementation Plan

> **For executor:** Execute only after this Plan receives independent review and explicit user approval. Use `.agent/workflows/execute-approved-plan.md`, `.agent/skills/test-driven-development`, `.agent/skills/systematic-debugging` for failures, and `.agent/skills/audit-plan-completion` before any completion claim.

**Status:** `draft_for_review`

`implementation_allowed=false`; `deployment_allowed=false`; `runtime_action_allowed=false`; every trading, replay, paper-trading, signal, and execution permission remains `false`.

**Goal:** Implement a local, read-only Stage 1.6F diagnostic that consumes verified C retained bytes and a verified local market-evidence package, preserves every denominator row, emits only descriptive diagnostics, and publishes an atomic independent bundle.

**Architecture:** `stage1_6f_historical_diagnostic_source.py` owns the two trust-boundary reads: canonical C loader plus retained-byte transaction, then evidence-manifest and raw-file verification. `stage1_6f_historical_diagnostic.py` contains deterministic denominator, matching, window, and descriptive reducers over already verified in-memory bytes. `stage1_6f_historical_diagnostic_storage.py` atomically writes and re-verifies a new F bundle and loads it read-only. Two thin scripts compose these modules; neither performs network I/O.

**Tech stack:** Python standard library only: `csv`, `hashlib`, `json`, `pathlib`, `statistics`, `zipfile`, `tempfile`, and existing Stage 1.6A loader.

---

## 1. Governance And Authority

This Plan is constrained by both externally approved Design authorities. The executor must recalculate both file hashes before changing code:

```text
APPROVED_STAGE1_6F_PARENT_DESIGN_PATH=
docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md
APPROVED_STAGE1_6F_PARENT_DESIGN_SHA256=
87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c

APPROVED_STAGE1_6F_EVIDENCE_TO_SCHEMA_DELTA_DESIGN_PATH=
docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md
APPROVED_STAGE1_6F_EVIDENCE_TO_SCHEMA_DELTA_DESIGN_SHA256=
8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628
```

This Plan has no self-embedded approval SHA. The user/reviewer must freeze the exact Plan bytes externally after review. Plan approval is not implementation, commit, deployment, network, VPS, replay, paper-trading, live-trading, signal, or execution authority.

### 1.1 Non-negotiable constraints

1. `RISK_LIVE_TRADING_ENABLED` and every F authority flag remain exact `False`; non-bool or true is rejected.
2. F has no network, URL, credential, private API, downloader, retry, daemon, queue, database, strategy, risk, or execution import.
3. F consumes C only through `load_completed_adapter_audit(project_root, completed_root, source_export)`, then performs the Parent Design exact nine-artifact retained-byte transaction. It never trusts a root path or copied summary.
4. The first F implementation consumes market data only from the passed local `market_evidence_root` whose exact `gap02_evidence_manifest.json` bytes SHA-256 is `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f`, whose schema is exact `stage1_6f_gap02_evidence_manifest_v1`, and whose six auxiliary artifact path/SHA/byte-length tuples equal Delta Section 2.2. A merely self-consistent replacement package is rejected as `market_evidence_invalid` with `unapproved_market_evidence_identity`. No absolute development-machine path is permitted in production code or tests.
5. Missing evidence, unmatched controls, truncation, censor, out-of-range rows, and unavailable metrics remain explicit `diagnostic_incomplete`; no row deletion, interpolation, fallback, synthetic positive summary, or outcome-driven control replacement is allowed.
6. The implementation must not alter either approved Design, B/C writers/loaders, 1.5/1.6E code, `configs/base.py`, evidence-package bytes, or any upstream runtime root.

## 2. Allowed Change Scope

### Allowed implementation paths

- `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py`
- `src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py`
- `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_storage.py`
- `scripts/external_signal_shadow/run_stage1_6f_historical_mechanism_diagnostic.py`
- `scripts/external_signal_shadow/review_stage1_6f_historical_mechanism_diagnostic.py`

### Allowed verification paths

- `tests/research/external_signal_shadow/stage1_6f_historical_diagnostic_test_support.py`
- `tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py`
- `tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic.py`
- `tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_storage.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_6f_historical_mechanism_diagnostic.py`

### Allowed documentation paths

- `docs/reviews/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-completion-audit_CN.md` only when generated by the independent completion-audit workflow.

### Allowed generated/runtime artifacts

- `data/external_signal_shadow/stage1_6f/**` generated only; never committed by this Plan.
- `/tmp/stage1_6f_*` test-only temporary output; remove only paths created by the current test process.

### Affected but unchanged

- `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter.py`
- `src/research/external_signal_shadow/stage1_6a_sealed_export_adapter_storage.py`
  - Compatibility evidence: canonical loader tests in `tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py` plus F `INV-FD01` tests.
- `tests/research/external_signal_shadow/stage1_6a_sealed_export_adapter_test_support.py`
  - Compatibility evidence: F positive C inputs must be produced by its registered `build_valid_historical_sealed_export` factory and `persist_adapter_audit`, not by handcrafted F dictionaries.
- `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/**`
  - Compatibility evidence: copy to a test temp root and verify manifest hashes; never mutate the source package.
- Both approved Design files, all B/C roots, `configs/base.py`, all Stage 1.5 and 1.6E code, and all trading/risk/execution modules.

### Forbidden

- Any mutation outside the paths above.
- Any change to approved Design or this approved Plan after approval.
- `ruff check --fix .`, full-repository formatting, `git clean`, destructive cleanup, unscoped search/replace, staging, commit, push, deployment, SSH, runtime action, or data download.
- Any fallback for absent C fields, absent market artifacts, missing coverage, missing 1-second settlement input, or absolute fixture paths.

## 3. Invariant-To-Task Map

| Design authority edge | Task | Mechanical proof | Fail-closed STOP |
| --- | --- | --- | --- |
| Parent 4.1 / Delta INV-FD01 C retained bytes | 1, 5 | canonical C factory -> persisted C root -> loader -> post-loader artifact mutation -> real runner composition | `source_invalid`; zero market/reducer/writer |
| Delta 4.2 / INV-FD02 manifest-bound market bytes | 2, 5 | real package copy; mutate CSV, ZIP, header, path, hash, size, or coherent package identity -> real runner composition | `market_evidence_invalid`; zero reducer/writer |
| Parent `INV-F02` historical is not PIT | 3 | null historical availability projection plus attempted `Tpub`/download-time substitution | reject substitution; no output with fabricated availability |
| Parent 5 / Delta INV-FD03 denominator preservation | 3 | mixed eligible/ineligible/unmatched/out-of-range/no-evidence fixture | every row and reason emitted; no deletion |
| Parent 6 / Delta INV-FD04 deterministic historical controls | 3 | actual REEF universe/provenance values; 878/380/15/365/120/245 and AXL/AKT/REZ checks | `control_universe_unverified` or `unmatched`; no replacement |
| Parent 5.2 / Delta INV-FD05 W1/W2 time boundary | 3 | exact boundaries, non-hour `Tpub`, AIA/PORT3, `Tsettlement <= Tpub` | incomplete metric; no full-window claim |
| Parent `INV-F08` / Delta INV-FD07 settlement association | 3 | V1/V2 boundary, missing/wrong mapping, then valid mapping with only 1-hour index | no last-price fallback; exact insufficient-1s status only after valid mapping |
| Parent `INV-F09` announcement grouping | 3 | one article/three contracts versus three articles/one contract and repeated revision | announcement and contract-row counts remain distinct |
| Parent 7 / Delta INV-FD06 semantic limits | 3 | OHLCV-only, mark/premium/depth/funding-only fixtures | exact `*_unavailable`; no upgraded metric |
| Delta Section 6 output provenance / INV-FD08 bundle integrity | 4 | record-contract mutation, fail before manifest, and mutate published artifact | reader rejects incomplete, untraceable, or mutated root |
| Parent `INV-F12` / Delta INV-FD09 zero side effect and permission | 5, 6 | AST/import guard, socket/HTTP and B/C-writer monkeypatches, plus real-root before/after fingerprint | `permission_or_side_effect_violation` or `upstream_evidence_mutated`; no output |

## 4. Task 0: Freeze Baseline, Authority, Scope, And Fixture Provenance

**Files:**
- Create: none.
- Modify: none.
- Read: both approved Designs, current workspace, evidence package, C loader, and all paths in Allowed Change Scope.

**Design edges:** all. Task 0 runs exactly once after `.agent/workflows/execute-approved-plan.md` Step 1 creates `EXECUTION_BASELINE_DIR`, and before any implementation or test mutation. Tasks 1-5 run their own Contract Reality, RED/GREEN, scope, and scanner gates; they do not recreate a baseline.

1. Reuse the workflow's one immutable execution baseline; do not invent an ad hoc directory or rerun this task later:

```bash
: "${BASE_SHA:?STOP=execution_baseline_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=execution_baseline_missing}"
BASELINE_DIR="$EXECUTION_BASELINE_DIR"
FINAL_DIR="$BASELINE_DIR/final"
test -d "$BASELINE_DIR" || { echo 'STOP=execution_baseline_missing' >&2; exit 1; }
test ! -e "$FINAL_DIR" || { echo 'STOP=execution_final_directory_exists' >&2; exit 1; }
mkdir "$FINAL_DIR"
```

The executor must preserve the workflow's `status.txt`, `worktree.patch`, `index.patch`, `untracked-paths.txt`, and `untracked-sha256.txt`; Task 0 adds the F-specific checks below.
2. Recalculate both approved Design SHA-256 values in Section 1. Any mismatch is `STOP=design_authority_mismatch`.
3. Record SHA-256 for every pre-existing dirty/untracked file under `docs/designs/`, `docs/reviews/`, and `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/`. These bytes are evidence inputs, not implementation output.
4. Freeze the entire Git index, without staging anything:

```bash
git ls-files -s -z | shasum -a 256 > "$BASELINE_DIR/index.sha256"
```

5. Save the current package manifest SHA and verify that it is `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f`. Verify all 148 ZIP/CSV pairs and the six Delta Section 2.2 auxiliary path/SHA/byte-length tuples before tests use the package.
6. Run scanner with actual process exit code captured outside a pipeline:

```bash
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" > "$BASELINE_DIR/scanner-baseline.txt" 2>&1; then
  scanner_rc=0
else
  scanner_rc=$?
fi
cat "$BASELINE_DIR/scanner-baseline.txt"
printf '%s\n' "$scanner_rc" > "$BASELINE_DIR/scanner-baseline.exitcode"
test "$scanner_rc" -eq 0 || { echo 'STOP=scanner_baseline_nonzero' >&2; exit 1; }
```

7. Inspect source topology with `rg`; Graphify is advisory only if its graph is stale or unavailable. Confirm no existing Stage 1.6F production module exists before creating the three permitted modules. This check is Task-0-only; its expected truth value must not be evaluated again after Task 1 creates those modules.

**Expected result:** approved bytes, evidence package, index, and scanner baseline are recorded; no repository file changes occur.

**STOP conditions:** `execution_baseline_missing`, `execution_final_directory_exists`, `design_authority_mismatch`, `evidence_fixture_hash_mismatch`, `scanner_baseline_nonzero`, `preexisting_workspace_provenance_missing`, `unexpected_existing_stage1_6f_production_module`.

## 5. Task 1: Implement C Retained-Byte Input Authority

**Files:**
- Create: `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py`
- Create: `tests/research/external_signal_shadow/stage1_6f_historical_diagnostic_test_support.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py`
- Modify: none.

**Design edges:** Parent Section 4.1, Parent `INV-F01`, `INV-F02`, `INV-F03`, `INV-F11`, Delta `INV-FD01`.

1. Add a failing test that creates a positive historical C source only through `build_valid_historical_sealed_export(...)`, then creates its completed C root through the existing `persist_adapter_audit(...)`. The F test helper may call those upstream APIs but may not write a C completion manifest, C summary, authoritative-artifact metadata, or derived C JSONL by hand.
2. Add failing tests for: loader exception; `source_audit_passed is not True`; missing/duplicate/extra/path-escaping nine authoritative artifacts; SHA/length mismatch; malformed retained JSON/JSONL; and a post-loader mutation of one artifact before F's one-time read.
3. Implement `verify_c_input(...)` in `stage1_6f_historical_diagnostic_source.py`:
   - calls `load_completed_adapter_audit` exactly once;
   - validates the exact required nine relative paths, no aliases or extras;
   - reads each listed regular non-symlink file once, immediately validates exact SHA-256 and byte length against the returned in-memory manifest, and returns only an immutable in-memory byte mapping plus the C identity fields;
   - parses all later C JSON/JSONL only from that mapping;
   - never reopens a retained C path after successful verification.
4. Run the focused tests red then green:

```bash
pytest -q tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py
```

**Expected result:** all source-boundary unit tests pass. They prove C verification and retained-byte behavior only; the required production proof that invalid C input reaches zero matching/metric reducer and writer calls is owned by Task 5's real runner-composition matrix.

**STOP conditions:** `source_invalid`; any need to modify the Stage 1.6A loader/schema/test factory is `BLOCKED_SCOPE_DRIFT`; any mismatch between frozen loader reality and Parent/Delta is `BLOCKED_SPEC_DRIFT` with failed invariant and source evidence.

## 6. Task 2: Implement Offline Market-Evidence Verification And Strict Parsers

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py`
- Modify: `tests/research/external_signal_shadow/stage1_6f_historical_diagnostic_test_support.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py`

**Design edges:** Delta Sections 2.2, 4.1, 4.2 and `INV-FD02`.

1. Add a failing positive test that copies the existing repo-relative evidence package to `tmp_path`, passes that copied root explicitly, and validates the real `gap02_evidence_manifest.json` and all listed ZIP/CSV bytes. Tests must derive the package source from a repo-relative path; a development-machine absolute path must never be hardcoded.
2. Add one-mutation negative tests for one CSV hash, one ZIP hash, byte count, header, missing file, duplicate manifest path, unlisted extra path, path traversal, symlink, invalid UTF-8, non-finite numeric value, and corrupt ZIP. Add a coherent-package mutation that adds or changes an evidence artifact, correctly recomputes all internal file hashes/sizes/row metadata, and rebuilds a self-consistent v1 manifest. It must still reject specifically as `market_evidence_invalid` with `unapproved_market_evidence_identity`, not as an internal file-hash failure.
3. Implement `verify_market_evidence(...)` and strict parsers for the exact CSV headers frozen by Delta Section 4.2. Before parsing any CSV, require all of: exact manifest SHA-256 `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f`; exact manifest schema; every listed file's hash/size; and exact Delta Section 2.2 path/SHA/byte-length equality for all six auxiliary artifacts. Return only parsed in-memory rows and verified identity metadata. A future market package is not accepted by schema compatibility alone.
4. Do not use `dict.get(..., default)` for authority, identity, hashes, timestamps, headers, or permission fields. Do not accept headers by subset, reordered columns, extension inference, globbing, or fallback path.
5. Run focused tests:

```bash
pytest -q tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py
```

**Expected result:** the unchanged copied package is accepted; every one-point mutation raises `market_evidence_invalid`. Unit tests do not substitute for Task 5's composition proof of zero reducer and writer calls.

**STOP conditions:** `market_evidence_invalid`; an evidence schema/manifest ambiguity not resolved by Delta is `BLOCKED_SPEC_DRIFT`.

## 7. Task 3: Implement Denominator, Matching, Windows, And Descriptive Reducers

**Files:**
- Create: `src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic.py`
- Modify: `tests/research/external_signal_shadow/stage1_6f_historical_diagnostic_test_support.py`

**Design edges:** Parent Sections 5-8 and `INV-F02` through `INV-F10`; Delta Sections 4.3, 5 and `INV-FD03` through `INV-FD07`.

1. Write failing tests that rebuild the full C denominator from retained C bytes, preserving parent failures, ineligible child rows, missing times, out-of-range rows, duplicate/revision lifecycle ambiguity, `control_universe_unverified`, unmatched, and no-evidence rows. Assert that no input row disappears.
2. Add the Parent `INV-F02` projection matrix using actual F projection functions, not a final-flag-only assertion: canonical C rows with `system_available_at_ms=None`, `fact_available_at_ms=None`, and `capture_time_status=historical_unknown` must preserve all three values unchanged in the F record. An attempted projection substitution of either `Tpub` or a market-download timestamp for a null availability field must be rejected before an F record is emitted. In every accepted projection, every Section 8 replay/PIT permission field must be exact boolean `False`.
3. Write failing tests against the actual verified REEF auxiliary bytes for exact conservation `878 = 380 + 498`, `380 - 15 = 365`, and `365 = 120 + 245`; assert deterministic selected controls `AXLUSDT`, `AKTUSDT`, `REZUSDT`. Add an explicit pure-matcher boundary matrix over already verified in-memory matcher inputs, not by corrupting manifest-bound package files: zero candidates -> `unmatched`; one -> one control with weight `1`; three -> three equal weights; four -> only the top three; ratios exactly `0.5` and `2.0` accepted and values just outside rejected; equal distances ordered by canonical symbol; one missing baseline bar, zero volatility, or zero median quote volume rejected; candidate input permutation unchanged. Test post-`Tpub` mutation cannot alter the frozen matching result and cannot cause replacement or reweighting.
4. Add independent settlement-association tests over the already verified in-memory rule mapping before the one-second-input gate: an event before the rule-effective boundary selects V1; an event after it selects V2; missing or wrong event mapping is rejected or explicitly unavailable without selecting a fallback or using last price. Only after a valid V1/V2 mapping is established may a 1-hour-only index input produce `settlement_value_unavailable_insufficient_1s_index`.
5. Add the Parent `INV-F09` grouping fixture: one `parent_article_id` with three distinct `contract_id` values has independent-announcement count `1` and contract-row count `3`; three distinct `parent_article_id` values with one contract each have independent-announcement count `3`; replaying the same revision does not increase either count. Assert matched/unmatched counts are emitted at the frozen announcement and contract-row layers rather than treating `len(contract_rows)` as shock count.
6. Implement pure functions, receiving verified in-memory rows only, to:
   - reconstruct C event/symbol denominator and exact eligibility;
   - join a market package only on exact event/symbol/time identity;
   - apply Parent Section 6 matching with its fixed ratio bounds, distance, canonical tie break, 1-3 equal weights, no substitute controls;
   - retain requested and observed W1/W2 intervals, including AIA/PORT3 truncation fields, `Tsettlement <= Tpub`, duplicates, gaps, and censor;
   - produce only the Delta Section 5.2 allowed descriptors and exact unavailable status names.
7. Add red/green semantic-boundary tests: OHLCV cannot emit depth/slippage; mark/index cannot be tradable; premium cannot be direct basis; funding cannot emit carry PnL; `is_buyer_maker` remains a raw-flag grouping; no settlement descriptor may use last price.
8. Run focused tests:

```bash
pytest -q tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic.py
```

**Expected result:** deterministic rows preserve denominator and input provenance. Available metrics are `descriptive_only`; any unavailable/truncated/censored metric remains exact `diagnostic_incomplete`; no alpha, PnL, executable-price, causal, or settlement-value claim exists.

**STOP conditions:** unexpected C schema requires `BLOCKED_SPEC_DRIFT`; any request to alter matching thresholds, replace controls, infer availability, interpolate, or add a market downloader is `BLOCKED_SCOPE_DRIFT`.

## 8. Task 4: Implement Atomic F Bundle Writer And Read-Only Reviewer Core

**Files:**
- Create: `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_storage.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_storage.py`

**Design edges:** Parent Sections 8-9, `INV-F10`, Delta Section 6 and `INV-FD08`.

1. Add failing tests for valid fresh-root output, pre-manifest crash, missing manifest, malformed/extra/duplicate manifest entry, altered artifact after manifest, existing completed root, and repeat run with a distinct output root.
2. Implement atomic write/read-back helpers for exactly:

```text
stage1_6f_input_receipt.json
stage1_6f_event_denominator.jsonl
stage1_6f_metric_diagnostics.jsonl
stage1_6f_diagnostic_summary.json
stage1_6f_diagnostic_bundle_manifest.json
```

3. Add failing record-contract tests before storage implementation. For `stage1_6f_event_denominator.jsonl` and `stage1_6f_metric_diagnostics.jsonl`, require every row to contain exact `schema_version`, verified Section 4.1 input identity, `parent_article_id`, `contract_id`, canonical symbol, requested/original and observed intervals, controls or exclusion reasons, metric status, and every Section 8 permission flag as exact `False`; each identity/linkage value must equal the verified in-memory source record. For `stage1_6f_input_receipt.json` and `stage1_6f_diagnostic_summary.json`, require their applicable aggregate identity, authority flags, and frozen count/status fields without inventing row-level IDs for aggregate artifacts. Remove or alter one required applicable provenance/identity field and prove the read-only bundle reader rejects the completed root.
4. Write all non-manifest files atomically, read back and hash them, then write `stage1_6f_diagnostic_bundle_manifest.json` last. The manifest schema is exact `stage1_6f_diagnostic_bundle_manifest_v1`; it includes relative path, SHA-256, byte length, and `bundle_state`. The reader accepts only a complete exact manifest and matching listed bytes plus the required record-level provenance contract.
5. Reject unknown bundle state and any non-exact `False` authority flag. Do not repair, overwrite, append to, or migrate any existing output root.
6. Run focused tests:

```bash
pytest -q tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_storage.py
```

**Expected result:** incomplete is a valid completed bundle only when its manifest-last proof is intact; partial/mutated roots are rejected as unreadable.

**STOP conditions:** `output_root_already_completed`, `bundle_manifest_invalid`, `bundle_artifact_hash_mismatch`, or `permission_or_side_effect_violation`.

## 9. Task 5: Add Thin Offline Runner, Read-Only Reviewer, And Isolation Tests

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_6f_historical_mechanism_diagnostic.py`
- Create: `scripts/external_signal_shadow/review_stage1_6f_historical_mechanism_diagnostic.py`
- Create: `tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py`
- Create: `tests/scripts/external_signal_shadow/test_review_stage1_6f_historical_mechanism_diagnostic.py`

**Design edges:** Parent Section 4.1 and `INV-F01`/`INV-F12`; Delta Sections 3, 4.1, 6, 8 and `INV-FD01`/`INV-FD02`/`INV-FD09`.

1. Add failing CLI tests for missing each required path argument, relative/absolute path acceptance only after resolve-and-confine checks, existing completed output root, and an input that yields a `diagnostic_incomplete` bundle.
2. Implement a runner with exactly the five path arguments from Delta Section 4.1. It composes source verification, reducers, and storage. It has no `--url`, `--download`, `--retry`, `--network`, `--credential`, `--fixture-run`, or permissive fallback argument.
3. Implement a reviewer whose only input is a completed F bundle root. It uses the storage loader, recomputes listed artifact hashes, reports per-status denominator/metric counts, and does not read source export, market evidence, network, or runtime roots.
4. Add a real runner-composition fail-closed matrix with canonical valid C input and a copied valid market package. For each single-point mutation -- C loader failure, C artifact hash failure, post-loader retained-byte mismatch, market manifest identity failure, market CSV/hash/path/schema failure -- invoke the actual runner/composition entry point and spy on matching reducer, metric reducer, and storage writer. Assert each call count is `0` and no completed F bundle exists. This matrix, rather than isolated verifier unit tests, proves Parent 4.1 and Delta global `source_invalid`/`market_evidence_invalid` ordering.
5. Add AST/import tests and monkeypatch `socket`, `urllib`, `http.client`, `subprocess`, B/C writer entry points, and all strategy/risk/execution imports. Assert no call/import is reachable from either F script or source modules. Assert every emitted authority flag is exact `False`.
6. Run focused script tests:

```bash
pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py \
  tests/scripts/external_signal_shadow/test_review_stage1_6f_historical_mechanism_diagnostic.py
```

**Expected result:** runner is local-only; reviewer is bundle-only; an invalid C or market boundary reaches zero matching reducer, metric reducer, and writer calls and cannot create a completed bundle.

**STOP conditions:** `network_or_subprocess_import_forbidden`, `upstream_write_attempt`, `permission_or_side_effect_violation`, or `runner_argument_contract_invalid`.

## 10. Task 6: Integrated Verification, Scope Proof, And Completion-Audit Handoff

**Files:**
- Create: none, except the explicitly allowed completion audit only if independently generated.
- Modify: none.

1. Run the full F suite and required upstream compatibility suite:

```bash
pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py \
  tests/scripts/external_signal_shadow/test_review_stage1_6f_historical_mechanism_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter_storage.py
```

2. Run a read-only real-root production preflight using the Delta Section 2.1 repo-relative Reality Snapshot, not a synthetic factory. Before the runner, compute deterministic fingerprints for both `SOURCE_EXPORT` and `C_H2_COMPLETED_ROOT`: sorted relative path, file type, mode, byte length, and SHA-256 for every regular file; record directories by path/type/mode; reject any symlink or other non-regular entry. Save both fingerprints under `$FINAL_DIR`. Verify `completion_manifest.json` is `226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0` and `source_export_receipt.json` is `07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e`; then run the actual F runner with that `SOURCE_EXPORT`, `C_H2_COMPLETED_ROOT`, and a copied unchanged evidence package into a fresh `/tmp/stage1_6f_*` output root. Run the actual read-only reviewer against that output. Recompute the two fingerprints and require byte-for-byte equality with their before snapshots; any difference is `STOP=upstream_evidence_mutated`. Assert the C loader, retained-byte transaction, denominator reconstruction, bundle manifest, reviewer, and upstream-read-only proof all succeed. This is verification-only and records the root paths as diagnostics; it must not turn the C snapshot into a production allowlist.
3. Run targeted static checks only on changed implementation/test paths. Do not use automatic fixing.

```bash
ruff check \
  src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py \
  src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py \
  src/research/external_signal_shadow/stage1_6f_historical_diagnostic_storage.py \
  scripts/external_signal_shadow/run_stage1_6f_historical_mechanism_diagnostic.py \
  scripts/external_signal_shadow/review_stage1_6f_historical_mechanism_diagnostic.py \
  tests/research/external_signal_shadow/stage1_6f_historical_diagnostic_test_support.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py \
  tests/scripts/external_signal_shadow/test_review_stage1_6f_historical_mechanism_diagnostic.py
```

4. Run the scanner again, capture its actual process return code exactly as in Task 0, require `0`, require no ERROR, and require no new normalized warning identity beyond the Task 0 baseline. Any warning in a changed F path requires a written technical disposition in the completion audit.
5. Verify both Design hashes and the externally approved Plan SHA before completion audit. A mismatch is `STOP=approved_authority_mismatch`.
6. Rebind the Task 0 baseline variables without recreating a baseline, then verify scope and index without staging:

```bash
BASELINE_DIR="${EXECUTION_BASELINE_DIR:?STOP=execution_baseline_missing}"
FINAL_DIR="$BASELINE_DIR/final"
test -d "$FINAL_DIR" || { echo 'STOP=execution_final_directory_missing' >&2; exit 1; }
git ls-files -s -z | shasum -a 256 > "$FINAL_DIR/index.sha256"
test "$(awk '{print $1}' "$FINAL_DIR/index.sha256")" = \
  "$(awk '{print $1}' "$BASELINE_DIR/index.sha256")" || {
  echo 'STOP=git_index_changed' >&2; exit 1;
}
```

Compare changed-after-baseline paths against this exact implementation/test/document whitelist. Verify every pre-existing dirty/untracked path recorded by Task 0 has unchanged bytes. The generated `data/external_signal_shadow/stage1_6f/**` output is excluded only when it is newly generated and remains untracked.

7. Invoke `.agent/skills/audit-plan-completion` for an independent audit. Do not claim complete, stage, commit, push, deploy, or run on a VPS unless the audit verdict is `complete` and the user separately authorizes the next lifecycle action.

**Expected result:** all tests, targeted lint, scanner process RC, authority hashes, real-root before/after fingerprints, scope proof, index proof, and independent completion audit pass.

**STOP conditions:** `upstream_evidence_mutated`, `approved_authority_mismatch`, `git_index_changed`, `execution_baseline_missing`, `execution_final_directory_missing`, scanner nonzero, any scope-whitelist violation, or an independent audit verdict other than `complete`.

## 11. Rule-12 Failure Routing

| Observation during execution | Required classification | Required action |
| --- | --- | --- |
| F code misunderstands an already frozen source/manifest contract, and repair stays in the whitelist | `BLOCKED_IMPLEMENTATION_DEFECT` | preserve RED evidence, make the smallest local repair, rerun affected and regression tests |
| Correct repair needs a file outside Allowed Change Scope, a config change, C/B/E mutation, downloader, network permission, or fixture evidence mutation | `BLOCKED_SCOPE_DRIFT` | stop; provide affected path, failed invariant, and minimum Plan/Design change request |
| Frozen Parent/Delta contradicts actual canonical C loader, verified evidence schema, CSV semantics, or required implementation behavior | `BLOCKED_SPEC_DRIFT` | stop; provide failed invariant, exact source bytes/path, contradiction proof, and proposed Design delta; do not add fallback |

## 12. Plan Self-Review

- Every Parent/Delta authority edge maps to a task, mechanical proof, and fail-closed STOP in Section 3.
- The Plan creates only the minimum local reader/reducer/storage/script path required by the Delta. It does not create an adapter framework, registry, downloader, service, database, config, or future extension point.
- Positive cross-boundary C inputs use the canonical upstream test factory and persistence path. Real market bytes are copied from the repo-relative evidence package; synthetic helpers are only for local pure-logic negatives and are explicitly marked synthetic.
- Current evidence and approved Design files are pre-existing untracked artifacts. Task 0 preserves their bytes; this Plan does not claim ownership or authorize their alteration.
- Plan review is still required. This document itself grants no implementation authority.
