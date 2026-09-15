# Stage 1.6F Current Numerical Snapshot Regression Test-Only Implementation Plan

> **For implementers:** This is a test-only plan. Do not modify production code, evidence bytes, Designs, the parent Stage 1.6F Plan, configuration, permissions, deployment state, or VPS state.

**Status:** `draft_for_review`
**Plan type:** local test-only regression guard; this document is not implementation, commit, deployment, runtime, replay, paper-trading, signal, execution, or live-trading authority.
**Goal:** Permanently detect a change from the current REEFUSDT W1 descriptive reducer snapshot, using the frozen local evidence package and one deterministic pytest.
**Architecture:** The test copies the existing repo-relative evidence package to `tmp_path`, validates it through the production strict reader, then calls the production `compute_descriptive_metrics(...)` with the frozen REEFUSDT event identity and three frozen controls. It compares literal current-snapshot values with `math.isclose`; it does not implement a second CSV parser or a second reducer.
**Tech stack:** Python 3.11 standard library (`hashlib`, `math`), existing `pytest`, existing Stage 1.6F test helper and production reader/reducer.

---

## 1. Governance And Exact Authority

### 1.1 Bound authorities

| Authority | Path | SHA-256 |
| --- | --- | --- |
| Parent Design | `docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md` | `87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c` |
| Evidence-to-schema Delta Design | `docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md` | `8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628` |
| Parent implementation Plan | `docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md` | `6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f` |
| Frozen market-evidence manifest | `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json` | `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f` |

`parent_completion_audit_available = false`; no Stage 1.6F parent completion-audit artifact is used as authority or evidence by this Plan. The exact parent Plan bytes are authority only. Task 0 independently requires the current pre-existing Stage 1.6F suite to pass before a snapshot-regression test may be added. This Plan does not reopen the Parent or Delta Design, nor does it change their status text.

### 1.2 Scope decision

The literal values in this Plan are a current implementation snapshot, not a provenance-bound independent numerical oracle. The test proves that future code continues to emit this reviewed current behavior under the frozen evidence package; it does not independently prove that the current reducer formulas are numerically correct. A full cleanroom parser in CI is explicitly out of scope because it would create and maintain a second implementation of the same reducers. A future request for an independent numerical-correctness oracle requires a separately reviewed evidence record that names its source bytes, SHA-256, method, and no-production-reducer constraint.

This Plan protects calculation regression only. It does not prove Alpha, causal forced-flow, trading feasibility, settlement value, PnL, carry PnL, slippage, replay readiness, or a deployment result.

### 1.3 Authority and permission invariant

The authoritative Stage 1.6F permission vocabulary is the exact current key set of `ALL_PERMISSION_FLAGS_FALSE`; no local alias or hand-maintained subset is permitted. Every value must be the singleton boolean `False`. This Plan has no network, URL, S3, HTTP, credential, SSH, VPS, downloader, process, database, writer, or output-root authority.

## 2. Mutable And No-Touch Sets

### 2.1 Allowed implementation scope

| Category | Allowed path or action |
| --- | --- |
| Implementation | none |
| Verification | Create `tests/research/external_signal_shadow/test_stage1_6f_golden_numerical_verification.py` only |
| Documentation | none; this candidate Plan is pre-existing execution input and must remain byte-identical |
| Generated/runtime | canonical `.git/plan-execution/<UTC_RUN_ID>/**` baseline evidence only; it is Git metadata and is never committed |
| Affected-but-unchanged | Parent/Delta/parent Plan, all existing Stage 1.6F sources/tests, `configs/base.py`, and the full evidence package |
| Forbidden | all other paths, commits, remotes, VPS, deployment, and runtime actions |

The executor may update this Plan's execution evidence only in an external audit record. It must not alter this Plan's approved bytes after user approval.

### 2.2 No-Touch set

- `src/**`, `configs/**`, `scripts/**`, and all production source imports.
- Both Stage 1.6F Design files and the completed parent Plan listed in Section 1.1.
- `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/**`, including the manifest and every ZIP/CSV/HTML/JSON byte.
- Existing Stage 1.6F tests and test-support helper.
- `data/external_signal_shadow/**`, `.gitignore`, Git index, commits, remotes, VPS, and runtime processes.

Any need to modify a No-Touch path is `STOP=BLOCKED_SCOPE_DRIFT`. A mismatch between the frozen golden results and an unchanged, verified evidence package is a potential reducer defect, not permission to change the fixture or golden constants.

## 3. Frozen Current-Snapshot Contract

### 3.1 Canonical input

The sole positive fixture is copied by the registered helper `copy_market_evidence_package(tmp_path)` from the repo-relative evidence root. The test must call `verify_market_evidence(copied_root)` before reducer invocation. It must not hardcode a workstation absolute path, construct market records by hand, glob files, or download data.

Call exactly:

```python
compute_descriptive_metrics(
    symbol="REEFUSDT",
    t_pub_ms=1736928006723,
    t_settle_ms=1737536400000,
    selected_controls=["AXLUSDT", "AKTUSDT", "REZUSDT"],
    verified_market=verified_market,
)
```

The W1 requested interval is exactly `[1736928006723, 1736971206723)`. The expected observed 1-hour bars are 12, from `1736931600000` through `1736971200000`; this is bar-aligned descriptive observation, not a claim of exact 12-hour tradeability.

### 3.2 Required outputs

The test must assert that the only eight metric names are `price_path`, `basis`, `mark_basis`, `funding`, `open_interest`, `visible_depth`, `agg_trades`, and `settlement_mechanism`; map by metric name only after asserting uniqueness.

All W1 available metrics have `status == "descriptive_only"`. `settlement_mechanism` has exactly `status == "settlement_value_unavailable_insufficient_1s_index"`; the test must not calculate or assert a settlement value.

For every result, every authority flag in `ALL_PERMISSION_FLAGS_FALSE` is the singleton `False` (`value is False`).

### 3.3 Current snapshot literal values

Use `math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)` for every floating-point descriptor. Exact integers, strings, booleans, tuple ordering, dict keys, and counts use exact equality.

| Metric | Required golden assertions |
| --- | --- |
| `price_path` | `first_close=0.000828`; `last_close=0.001018`; `price_change_bps=2294.6859903381655`; `event_minus_control_bps=1441.6271512850253`; `paired_diff_censored is False`; `bar_count=12`; exact requested and observed times from Section 3.1. |
| `basis` | `bar_count=12`; `first_basis_bps=-119.331742243437`; `last_basis_bps=0.0`; `median_basis_bps=0.0`. |
| `mark_basis` | `bar_count=12`; `first_mark_basis_bps=-37.82816229117025`; `last_mark_basis_bps=9.823182711197198`; `median_mark_basis_bps=0.0`; exact note `non_tradable_risk_price_basis_only`. |
| `funding` | `observation_count=3`; ordered observations exactly `[(1736942400000, 4, -0.00464199), (1736956800000, 4, -0.0006037), (1736971200000, 4, 0.00005)]`; `count=3`. |
| `open_interest` | `bar_count=144`; `first_oi_value=5880098.4449056`; `last_oi_value=5687841.42686945`; `delta_oi_value=-192257.01803614944`; `latest_toptrader_long_short_ratio=0.918348`. |
| `visible_depth` | `snapshot_count=14400`; exact ten keys `pct_-5` through `pct_-1` and `pct_1` through `pct_5`; each `count=1440`; each `first_notional`, `last_notional`, and `median_notional` matches the literal table in Task 1; exact note `visible_discrete_depth_ladder_proxy_only_no_slippage`. |
| `agg_trades` | `trade_count=121749`; `total_trades=121749`; `total_notional=78177015.7525911`; true population `66022 / 39228553.41463927`; false population `55727 / 38948462.33794786`. |
| `settlement_mechanism` | `sample_count=0`; `rule_version="V2"`; `expected_sample_count=3600`; `sample_interval_seconds=1`; `sample_window_minutes=60`; exact unavailable note. |

## 4. Implementation Tasks

### Task 0: Freeze execution baseline and authority

**Files:**
- Create only through the canonical execution workflow: `.git/plan-execution/<UTC_RUN_ID>/**`
- Read only: every authority and fixture in Section 1.1.

1. The execution authorization must supply this Plan's repo-relative path and exact approved SHA-256. Compute this Plan's SHA-256 first and require equality with that external approval token; otherwise stop before any test file is created.

2. Confirm all Section 1.1 SHA-256 values from exact current bytes:

```bash
for path in \
  docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md \
  docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md \
  docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md \
  tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json
do
  shasum -a 256 "$path"
done
```

**Expected result:** all four digests exactly match Section 1.1.
**STOP:** `approved_authority_mismatch`.

3. Reuse the canonical execution-workflow baseline. Do not create a second baseline owner. The execution workflow must already have supplied `BASE_SHA` and `EXECUTION_BASELINE_DIR` and created `status.txt`, `worktree.patch`, `index.patch`, `untracked-paths.txt`, and `untracked-sha256.txt` before this Plan's tasks start:

```bash
: "${BASE_SHA:?STOP=execution_baseline_missing}"
: "${EXECUTION_BASELINE_DIR:?STOP=execution_baseline_missing}"
BASELINE_DIR="$EXECUTION_BASELINE_DIR"
for evidence in status.txt worktree.patch index.patch untracked-paths.txt untracked-sha256.txt; do
  test -f "$BASELINE_DIR/$evidence" || {
    echo "STOP=execution_baseline_missing:$evidence" >&2
    exit 1
  }
done
test ! -e tests/research/external_signal_shadow/test_stage1_6f_golden_numerical_verification.py || {
  echo 'STOP=authorized_test_path_preexists' >&2
  exit 1
}
```

4. Capture the scanner's actual process exit code without a pipeline:

```bash
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" > "$BASELINE_DIR/scanner-before.txt" 2>&1
then
  scanner_rc=0
else
  scanner_rc=$?
fi
cat "$BASELINE_DIR/scanner-before.txt"
printf '%s\n' "$scanner_rc" > "$BASELINE_DIR/scanner-before.exitcode"
test "$scanner_rc" -eq 0 || { echo 'STOP=scanner_baseline_nonzero' >&2; exit 1; }
```

5. Before the new test is created, run the existing Stage 1.6F suite as a pre-existing implementation baseline:

```bash
if .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py \
  tests/scripts/external_signal_shadow/test_review_stage1_6f_historical_mechanism_diagnostic.py \
  > "$BASELINE_DIR/stage1_6f-preexisting-suite.txt" 2>&1
then
  preexisting_suite_rc=0
else
  preexisting_suite_rc=$?
fi
cat "$BASELINE_DIR/stage1_6f-preexisting-suite.txt"
printf '%s\n' "$preexisting_suite_rc" > "$BASELINE_DIR/stage1_6f-preexisting-suite.exitcode"
test "$preexisting_suite_rc" -eq 0 || {
  echo 'STOP=preexisting_stage1_6f_baseline_not_green' >&2
  exit 1
}
```

6. Confirm `configs/base.py` still contains `RISK_LIVE_TRADING_ENABLED = False`, and read the existing fixture helper and reducer API. No edit occurs in Task 0.

7. Rule-12 routing is fixed: a failure confined to the allowed new test path is `BLOCKED_IMPLEMENTATION_DEFECT`; any required change to a No-Touch path is `BLOCKED_SCOPE_DRIFT`; a contradiction between this Plan and frozen Parent/Delta contracts is `BLOCKED_SPEC_DRIFT`. Do not add a fallback, alter fixture bytes, or modify production code to route around any case.

**STOP conditions:** `approved_authority_mismatch`, `execution_baseline_missing`, `authorized_test_path_preexists`, `scanner_baseline_nonzero`, `preexisting_stage1_6f_baseline_not_green`, or any request for a new fixture/version/schema is `BLOCKED_SPEC_DRIFT`.

### Task 1: Add the one golden numerical regression test

**Files:**
- Create: `tests/research/external_signal_shadow/test_stage1_6f_golden_numerical_verification.py`
- Read only: `tests/research/external_signal_shadow/stage1_6f_historical_diagnostic_test_support.py`; `src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py`; `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py`.

1. Create one test named `test_reef_w1_descriptive_metrics_match_current_snapshot_values`.
2. Import only `hashlib`, `math`, `Path`, the existing `copy_market_evidence_package` helper, `verify_market_evidence`, `compute_descriptive_metrics`, and `ALL_PERMISSION_FLAGS_FALSE`. Do not import scripts, storage writers, network libraries, or test output bundles.
3. Copy the fixture to `tmp_path`; hash the copied manifest using `hashlib.sha256(...).hexdigest()` and assert the Section 1.1 manifest digest. Then call `verify_market_evidence` and assert its returned manifest identity is the same digest.
4. Call the reducer with exactly the Section 3.1 inputs. Build a metric map only after verifying the eight-name set and no duplicate names.
5. Encode the Section 3.3 snapshot values as local literal constants. A tiny local `assert_close(actual, expected)` wrapper around `math.isclose(..., rel_tol=0.0, abs_tol=1e-12)` is permitted only to keep numeric assertions readable; it must fail with the field name, actual value, and expected value. Do not describe these literals as independently verified or as numerical-correctness proof.
6. For `visible_depth`, use one literal mapping with all ten percentage keys and the exact `first_notional`, `last_notional`, `median_notional`, and `count` values below. Iterate over that literal mapping; do not calculate a second depth reducer.

```python
EXPECTED_DEPTH = {
    "pct_-5": (1440, 283079.160823, 333617.024617, 385648.745531),
    "pct_-4": (1440, 217558.967351, 291654.601869, 335300.052711),
    "pct_-3": (1440, 160876.386087, 243766.42073, 282177.560653),
    "pct_-2": (1440, 131484.899513, 170901.85691, 221390.282449),
    "pct_-1": (1440, 44193.649303, 90257.400987, 106993.138865),
    "pct_1": (1440, 37278.942028, 89126.22403, 93751.537525),
    "pct_2": (1440, 147053.596677, 154025.329339, 184400.194495),
    "pct_3": (1440, 199796.067384, 186170.381003, 220761.744244),
    "pct_4": (1440, 234731.576448, 192858.088739, 243415.06369),
    "pct_5": (1440, 245215.602344, 222972.328403, 262599.015962),
}
```

7. Assert `result.authority_flags == ALL_PERMISSION_FLAGS_FALSE` for every result, then assert each exact key's value `is False`; this rejects missing, renamed, and extra authority fields without inventing a local permission vocabulary. Assert no descriptor contains `alpha`, `pnl`, `carry_pnl`, `slippage`, or `tradable_price` except the existing permitted `price_path` boundary, matching the existing semantic-boundary test.
8. Run the new test:

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_golden_numerical_verification.py
```

**Expected result:** `1 passed`. The test must read no network resource, create no F bundle, and alter only its temporary directory.

**Crash/recovery boundary:** not applicable. This Plan creates no persistent F output root, manifest, process, or lifecycle state; adding crash/recovery machinery is forbidden scope expansion.

**Deliberate TDD note:** This is a regression-test-only task over a pre-existing GREEN implementation baseline; no production change is authorized and no intentional source regression may be introduced merely to manufacture a RED phase. The mechanical proof is a focused GREEN snapshot comparison. It is not an independent numerical-correctness oracle.

**STOP conditions:** fixture digest mismatch or strict market-reader failure is `market_evidence_invalid`; any reducer mismatch is `BLOCKED_IMPLEMENTATION_DEFECT`; any required production/fixture/Design modification is `BLOCKED_SCOPE_DRIFT`.

### Task 2: Regression, safety, scanner, and scope proof

**Files:**
- Read only: all existing Stage 1.6F test files, `configs/base.py`, and Task 0 baseline files.

1. Run the full existing Stage 1.6F test surface plus the new test:

```bash
.venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_source.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_historical_diagnostic_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6f_historical_mechanism_diagnostic.py \
  tests/scripts/external_signal_shadow/test_review_stage1_6f_historical_mechanism_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_6f_golden_numerical_verification.py
```

**Expected result:** all tests pass.

2. Run lint only over the added test:

```bash
.venv/bin/ruff check \
  tests/research/external_signal_shadow/test_stage1_6f_golden_numerical_verification.py
```

**Expected result:** exit code `0`.

3. Capture the broad final scanner process exit code explicitly:

```bash
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" > "$BASELINE_DIR/scanner-after.txt" 2>&1
then
  scanner_rc=0
else
  scanner_rc=$?
fi
cat "$BASELINE_DIR/scanner-after.txt"
printf '%s\n' "$scanner_rc" > "$BASELINE_DIR/scanner-after.exitcode"
test "$scanner_rc" -eq 0 || { echo 'STOP=scanner_final_nonzero' >&2; exit 1; }
```

4. Scan the only newly authorized `tests/**` Python file explicitly. The broad differential scanner intentionally defaults to changed `src/**` and `scripts/**` paths when no positional file is supplied, so it is not proof for this test-only change:

```bash
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --all-lines \
  tests/research/external_signal_shadow/test_stage1_6f_golden_numerical_verification.py \
  > "$BASELINE_DIR/golden-test-scanner.txt" 2>&1
then
  golden_test_scanner_rc=0
else
  golden_test_scanner_rc=$?
fi
cat "$BASELINE_DIR/golden-test-scanner.txt"
printf '%s\n' "$golden_test_scanner_rc" > "$BASELINE_DIR/golden-test-scanner.exitcode"
test "$golden_test_scanner_rc" -eq 0 || {
  echo 'STOP=golden_test_scanner_nonzero' >&2
  exit 1
}
```

5. Prove scope and Git index preservation against the canonical execution baseline:

```bash
git diff --binary > "$BASELINE_DIR/worktree-after.patch"
cmp -s "$BASELINE_DIR/worktree.patch" "$BASELINE_DIR/worktree-after.patch" || {
  echo 'STOP=preexisting_tracked_worktree_bytes_changed' >&2
  exit 1
}

git diff --cached --binary > "$BASELINE_DIR/index-after.patch"
cmp -s "$BASELINE_DIR/index.patch" "$BASELINE_DIR/index-after.patch" || {
  echo 'STOP=git_index_changed' >&2
  exit 1
}

shasum -a 256 -c "$BASELINE_DIR/untracked-sha256.txt" || {
  echo 'STOP=preexisting_untracked_bytes_changed' >&2
  exit 1
}

git ls-files --others --exclude-standard | LC_ALL=C sort > "$BASELINE_DIR/untracked-paths-after.txt"
{
  cat "$BASELINE_DIR/untracked-paths.txt"
  printf '%s\n' tests/research/external_signal_shadow/test_stage1_6f_golden_numerical_verification.py
} | LC_ALL=C sort -u > "$BASELINE_DIR/expected-untracked-paths.txt"
cmp -s "$BASELINE_DIR/expected-untracked-paths.txt" "$BASELINE_DIR/untracked-paths-after.txt" || {
  echo 'STOP=scope_violation' >&2
  exit 1
}

shasum -a 256 \
  docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md \
  docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md \
  docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md \
  tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json
```

The final four hashes must equal Section 1.1.

6. Do not stage, commit, push, deploy, SSH, run a VPS process, or create a generated diagnostic bundle. Request an independent completion audit after all prior gates pass.

**STOP conditions:** any failing test/lint/scanner, `golden_test_scanner_nonzero`, `preexisting_tracked_worktree_bytes_changed`, `preexisting_untracked_bytes_changed`, `git_index_changed`, `scope_violation`, authority hash drift, non-false permission, or audit verdict other than `COMPLETE`.

## 5. Authority-Edge Proof Matrix

| Authority edge / invariant | Implementation task | Mechanical proof | Fail-closed STOP |
| --- | --- | --- | --- |
| Frozen Parent/Delta/parent-Plan bytes | Task 0 | exact SHA-256 recomputation before test creation | `approved_authority_mismatch` |
| Frozen reviewed market package | Task 1 | explicit manifest SHA plus `verify_market_evidence` | `market_evidence_invalid` |
| REEF W1 time boundary and control identity | Task 1 | exact literal call, interval assertions, ordered controls | `BLOCKED_IMPLEMENTATION_DEFECT` |
| Current numerical snapshot compatibility | Task 1 | seven W1 descriptor groups and unavailable settlement assertion | `BLOCKED_IMPLEMENTATION_DEFECT` |
| No unauthorized semantic upgrade | Task 1 | exact status/note/no-forbidden-descriptor assertions | `BLOCKED_IMPLEMENTATION_DEFECT` |
| Zero permission expansion | Tasks 0-2 | exact authority-flag mapping equals `ALL_PERMISSION_FLAGS_FALSE`; every value is `False` | `permission_invariant_violation` |
| No source/fixture/design drift | Task 2 | canonical baseline patches, untracked SHA verification, path-set proof, and authority hashes | `BLOCKED_SCOPE_DRIFT` |
| No shortcut bypass | Tasks 0 and 2 | broad scanner and explicit all-lines test scanner actual process RCs equal `0` | `scanner_baseline_nonzero` / `scanner_final_nonzero` / `golden_test_scanner_nonzero` |

## 6. Completion Boundary

Completion means only that the new local pytest detects a change from the frozen REEFUSDT W1 current snapshot under the reviewed evidence package. It does not independently establish numerical correctness and does not approve a commit, deployment, VPS run, new market package, historical replay, strategy change, alpha conclusion, or any trade-related action.

Plan approval is required before Task 0. After independent completion audit returns `COMPLETE`, commit/push or any later operational step still needs separate user instruction.
