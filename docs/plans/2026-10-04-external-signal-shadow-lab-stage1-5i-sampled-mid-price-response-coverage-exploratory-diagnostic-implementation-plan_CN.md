# Stage 1.5I N=3 采样中间价响应覆盖与探索性诊断 Implementation Plan

> **For implementation agent:** 仅在本 Plan 获独立 review 通过并取得用户 Plan implementation approval 后，按 Task 顺序执行；不得跳过 Task 0 或生成真实 receipt。

**Goal:** 新增一个只读、N=3 固定样本的 Stage 1.5I consumer，输出完整 `coverage_inventory` 或完整的描述性 `complete_n3_exploratory_analysis`，绝不产生 Alpha、PnL、执行或交易结论。

**Architecture:** I core 自身定位 project root，先验证实施 authority、冻结 G/H source bytes 与两个 sealed receipt，再以真实 G reducer 重验三个 source root。它仅从每个 owned child 的 manifest-verified JSONL 读取采样盘口，严格生成九个 child row、三个 parent-local row 与可验证的本地 receipt；CLI 只能传入冻结 authority 与 `run_id`。所有 production 入口均无 caller-controlled root、source、bundle、output 或 consumer 参数。

**Tech Stack:** Python 3 standard library (`hashlib`, `json`, `math`, `pathlib`, `fcntl`, `os`, `importlib`), existing G/H strict loaders, `pytest`, `ruff`。

---

## 1. Authority 与执行边界

本 Plan 仅落实以下已批准 Design 的确定性、只读、描述性 contract：

| authority | fixed value |
| --- | --- |
| Approved Design | `docs/designs/2026-10-04-external-signal-shadow-lab-stage1-5i-sampled-mid-price-response-coverage-exploratory-diagnostic-design_CN.md` |
| Approved Design SHA-256 | `9b9e2c51927c521844e8121e60ae1aa6b7bbe9acd175e05dfadad4c1a034efc8` |
| Planning `BASE_SHA` | `96257f6f55788e9b7791bb9bb6c8bd6489300f14` |
| Frozen G N=3 receipt | `data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z` |
| G artifacts SHA-256 | `f3b4c76683fe7e1e4a7f28f30437f289f036f6ffc6126f8e9693faad62789adf` / `c92686b4834ee41165850aba99b1b68254b05a4afaf37d5e2789747db60ca941` / `df6e12df8b1d105c62dd8cb01baeb0f858aa008c42488f699999a3b9ba51f2dc` |
| Frozen H receipt | `data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/stage1_5h_n3_regime_stratified_friction_20261003T070500Z` |
| H artifacts SHA-256 | `c9034ae8c079e066b1de5a8c092bad00a054170aa22a28392df2f24dd0487bcc` / `1dba9853878d24da8cd3d7ae99f0ec899bfc3d1a90ddcc1399e999659e498b11` / `ea774319e905de0ed4e8a62c44238cc33d4e0ac5994188198ee356c4220082b3` |

`<APPROVED_I_PLAN_SHA256>` is obtained only from the later user approval sentence. Task 0 requires the exact current Plan bytes to equal that value and `git rev-parse HEAD` to equal `BASE_SHA`; any mismatch is `STOP=approved_authority_mismatch`. It must not rewrite a baseline or use a later HEAD as a substitute.

The Plan does not authorize receipt generation, network, VPS, SSH, replay, simulation, Alpha, signal generation, execution, paper/live action, commit, push or deployment. Success means only that implementation is ready for independent Completion Audit.

### 1.1 Local authority bundle

Task 0 uses one create-once, non-symlink, project-contained bundle:

```text
.git/plan-execution/stage1_5i_n3_sampled_mid_price_response/<APPROVED_I_PLAN_SHA256>/
```

Before code/test work, it must contain regular files `implementation_authorization.txt`, `implementation_authorization.sha256`, `execution_authority.json`, `execution_authority.sha256`, and `base_sha`. The text must be exactly the user approval's two UTF-8 lines with one final LF; its sidecar is `<SHA256>  implementation_authorization.txt\n`. The canonical JSON key set is exactly `approved_design_path`, `approved_design_sha256`, `approved_plan_path`, `approved_plan_sha256`, `base_sha`, `current_plan_sha256`, `project_root`; its values bind the approved Design/Plan bytes, fixed `BASE_SHA`, and derived root. A missing/extra key, non-regular file, any symlink ancestor, malformed sidecar, substitution, or pre-existing bundle is fatal.

No `receipt_generation_authorization.txt` or sidecar is created during this Plan. Future local receipt generation is a separate authorization with a specific `RUN_ID` and then-current I core/CLI hashes.

## Allowed Change Scope

Allowed implementation paths:

```text
src/research/external_signal_shadow/stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py
scripts/external_signal_shadow/run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py
```

Allowed verification paths:

```text
tests/research/external_signal_shadow/test_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py
tests/scripts/external_signal_shadow/test_run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py
```

Allowed documentation paths: `none`. The approved Design and this approved Plan become immutable authorities during execution.

Allowed generated/runtime artifacts:

```text
.git/plan-execution/stage1_5i_n3_sampled_mid_price_response/<APPROVED_I_PLAN_SHA256>/**
```

This evidence bundle is not a receipt and must not be committed.

Affected but unchanged:

```text
src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
src/research/external_signal_shadow/safety.py
configs/base.py
data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z/**
data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/stage1_5h_n3_regime_stratified_friction_20261003T070500Z/**
data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot/**
data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7/**
data/external_signal_shadow/local_evidence/20261001T074500Z_stage1_5f_ctusdt/**
```

Compatibility evidence: the core tests call the real G/H strict loaders and the exact G re-admission APIs; the CLI test verifies the public I entrypoint only. No existing consumer imports an I symbol at planning baseline (`rg` discovery in Task 0).

Forbidden:

```text
data/external_signal_shadow/stage1_5i/**
receipt_generation_authorization.txt and receipt_generation_authorization.sha256
graphify-out/**
all mutation outside the four implementation/test paths and the execution bundle
unrelated formatter/refactor, ruff --fix, git clean, commit, push, deployment, SSH, network,
replay, simulator, signal, execution, paper trading or live trading
```

Any need to change a frozen producer/receipt/root/configuration, create a real I receipt, or expand the whitelist is `STOP=BLOCKED_SCOPE_DRIFT`. Any contradiction between this Plan and a frozen upstream contract is `STOP=BLOCKED_SPEC_DRIFT` with Rule-12 evidence packet: failed invariant, exact source contract, reproduction, and proposed Design delta.

## 2. Frozen topology and invariant map

The I core verifies, before and after import, each module's expected relative path, non-symlink ancestry, `__file__`, `__spec__.origin`, resolved project containment, and SHA-256:

```text
src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission
src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review
src.research.external_signal_shadow.stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic
configs.base
```

It uses `load_verified_n3_receipt()`, `load_verified_n3_friction_root()`, `load_stage1_5g_inputs()`, and `build_stage1_5g_review_summary()` directly. It must not import a script into `src`, old N=2/H V3, collector code, network/exchange client, execution code, or a generic registry.

| Design invariant / authority edge | implementation task | mechanical proof | fail-closed result |
| --- | --- | --- | --- |
| INV-15I-01 membership/receipt identity | 1, 2 | real G strict load plus one artifact or lineage mutation | receipt/source integrity STOP |
| INV-15I-02 owned-file bridge | 1, 2 | real bundle projection vs one JSONL; second/unowned/CT Batch7 selection mutation | `STOP=stage1_5i_source_file_bundle_mismatch` or ownership STOP |
| INV-15I-03 no silent attrition | 2 | nine fixed rows with one child horizon/price mutation | only `coverage_inventory`, never child deletion |
| INV-15I-04 time authority | 1, 2 | one accepted/state anchor mismatch or malformed timestamp | `STOP=stage1_5i_anchor_authority_mismatch` |
| INV-15I-05 sampled-only claim | 2 | sampled-return/extrema field and forbidden-claim mutation | no interpolation, full-path, PnL or executable-price output |
| INV-15I-06 fixed exploratory rule | 2 | 15m/1h/4h locator plus invalid-intermediate, invalid-first and all-invalid mutations | exact gap reason/null grammar; no tuned horizon or fallback |
| INV-15I-07 cluster/regime separation | 2, 3 | parent/regime membership mutation and forbidden pooled-key mutation | strict loader STOP |
| INV-15I-08 friction separation | 2, 3 | H context mutation and derived-cost/rank key mutation | strict loader STOP; no cost verdict |
| INV-15I-09 artifact/lifecycle integrity | 3 | byte/key/hash/symlink/staging/collision/crash mutations | integrity STOP or non-success state |
| INV-15I-10 authority isolation | 1, 4 | text/sidecar/run-id/core/CLI hash/CLI flag/AST mutation | authority STOP before source/output |

## 3. Task 0: Immutable baseline, scope and authority capture

**Files:** only the allowed execution bundle. No source, tests, receipt, data output, or generation authority.

1. Verify approved Design bytes, current approved Plan bytes, approval sentence grammar, and `HEAD == 96257f6f55788e9b7791bb9bb6c8bd6489300f14`. Write that literal base to `base_sha`; each later task begins and ends by checking `HEAD == base_sha`.
2. Record `git status --short --untracked-files=all`, `git diff --binary`, `git diff --cached --binary`, `git ls-files -s`, an untracked/tracked SHA-256 ledger, and index state. The pre-existing approved Design/Plan state is provenance, not output from this Plan. `git diff --cached` must remain empty.
3. Create the bundle only if absent, then validate the exact ordinary authority contract in Section 1.1. Capture SHA-256 for Design/Plan, G/H receipt artifacts, three `SHA256SUMS`, three stored G summaries, and four frozen modules. Strict-load G/H receipts and require `RISK_LIVE_TRADING_ENABLED is False`.
4. Run the targeted discovery below; preserve stdout and actual return code. Only `0`/`1` are valid. Classify existing H references as `compatible_unchanged`; any pre-existing I reference outside this Design/Plan is `BLOCKED_SCOPE_DRIFT` until understood.

```bash
set +e
rg -n 'stage1_5i|sampled_mid_price|coverage_inventory|complete_n3_exploratory_analysis|stage1_5h_n3_regime' \
  src scripts tests docs data >"$EXECUTION_BASELINE_DIR/topology_discovery.txt"
rg_rc=$?
set -e
printf '%s\n' "$rg_rc" >"$EXECUTION_BASELINE_DIR/topology_discovery.rc"
case "$rg_rc" in 0|1) ;; *) echo 'STOP=stage1_5i_topology_discovery_failed' >&2; exit 1;; esac
```

**Verify:** all captured commands have saved stdout/stderr and actual RC; no real I output namespace exists or is created. If scope/index/baseline differs at any task boundary, stop before proceeding.

## 4. Task 1: RED fixtures and trust-boundary tests

**Files:** create the two allowed test files only. Do not create the I core/CLI until all listed RED nodes are collected and individually fail for their declared pre-GREEN reason. Until the core/CLI exists, each test module may define only a test-local import fallback that raises `I_CORE_NOT_IMPLEMENTED`; it is never installed, exported, or used as a positive fixture.

1. Build one canonical positive fixture from the real G and H strict loaders at the fixed receipt roots. For each fixed root in `moonshot`, `batch7`, `ct_projection` order, call real `load_stage1_5g_inputs()` and `build_stage1_5g_review_summary()` with every named argument from the approved Design. Assert manifest, stored-summary, source-root, N=3 membership, parent ledger, regime ledger, accepted-event, completed-state and no-blocker projections before any mutation. No handcrafted receipt, hash, membership, source row, event or H context fixture is allowed.
2. Add RED authority/import tests: substituted implementation text, malformed sidecar, wrong Plan/Design bytes, wrong base SHA, forged five-line generation record, wrong authorized run id/core/CLI hash, symlink file, byte-drift module and preloaded wrong `__spec__.origin`. Each must fail before import, root read, staging or output.
3. Add RED re-admission/ownership tests: G/H artifact hash drift, source `SHA256SUMS` mismatch, stored-vs-recomputed summary field mismatch, missing/duplicate/wrong owned JSONL, selected CT-root Batch7 duplicate, JSONL/bundle row mismatch, accepted/state identity mismatch, and anchor mismatch. Mutate exactly one field after canonical fixture preconditions pass.
4. Add RED sampled-row tests from a real validated owned projection: missing 4h interval; invalid intermediate bid/ask with valid anchor/horizons; invalid first bid/ask with later valid anchor; all invalid prices; malformed/non-monotonic timestamp. Require the exact `coverage_gap` reason/null grammar or exact STOP; no test may suppress a child.
5. In the test module, implement one test-only **independent oracle** over the canonical owned snapshot projection. It must not call an I reducer, locator, return/extrema helper, serializer, or loader under test. Its local loop selects the first valid anchor at/after `observation_window_start_ms`, the first valid horizon in each closed `[anchor+h, anchor+h+120000ms]` interval, and calculates `10000 * (mid_h / anchor_mid - 1)`, max/min sampled return and sample count through the selected 4h row. Compare every emitted child value to this oracle. Add one-mutation boundary cases for first-valid anchor selection, left/right closed-interval endpoints, and rows outside the selected 4h interval; a shared producer/loader calculation is never an oracle.
6. Add RED schema/lifecycle/permission tests: incorrect 19-false flag map, unknown/omitted/typed-wrong schema field, `NaN`/infinity/bool numeric, Markdown mismatch, manifest byte/hash/path mismatch, root/ancestor/artifact symlink, foreign staging, collision, pre-rename failure, post-rename parent-`fsync` failure, extra CLI flag, and forbidden imports/opens. Under a `tmp_path` output parent, start two independently spawned processes for the same valid `RUN_ID` behind a synchronization barrier. Exactly one may publish; the other, after acquiring the same parent lock, must STOP on existing final/staging and neither may overwrite. AST/open-spy assertions reject raw root scanning, BAPI/network/SSH/subprocess/execution/replay/paper/live imports and prove no source file is opened before the frozen producer gates.
7. Store `task1_red_ledger.json` in the execution bundle. Each test node records canonical fixture, prior gates, exactly one mutation, target gate, expected exact STOP or expected `coverage_inventory`, and expected pre-GREEN failure. Run every node independently; unexpected pass, collection error, XFAIL, omitted precondition, or unrelated failure is `STOP=BLOCKED_SPEC_DRIFT`.

**Verify:** `pytest --collect-only` succeeds. Each ledger node fails before implementation for its recorded pre-GREEN reason; aggregate suite RC is non-zero by design and is not accepted as evidence on its own.

## 5. Task 2: Minimal I core, verified re-admission and reducer

**Files:** create `src/research/external_signal_shadow/stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py`; update the core test file.

1. Add fixed constants only for approved Design/Plan identities, base SHA, G/H roots/artifact hashes, the three ordered owned source records, exact nine owner/path records, four frozen modules, three regimes, `15m`/`1h`/`4h`, 120000ms locator, 19 false flags, output grammar, and run-id regex. Derive root solely from the core file. No environment override, glob/discovery, factory, registry, optional root, source selector, threshold, or configuration extension.
2. Implement ordinary implementation-authority and separate five-line local generation-authority validators. The public route invokes both before frozen import, source read, staging or write. Tests may redirect only private post-locator content reads after canonical locator assertion; no test seam is public or CLI-selectable.
3. Implement pre/post-import freeze verification and strict-load fixed G/H receipts with default consumer behavior. Re-admit all three roots via real G API and exact call signature; compare stored and recomputed identity, parent/regime, membership, source-manifest and clean-quality projections without `.get`, defaults, coercion, tolerance or fallback.
4. Locate exactly one manifest-listed, regular, non-symlink JSONL for each owned child. Parse it in append order and exact-compare it to the matching `bundle.snapshots` projection. Emit the fixed nine child records in `(parent_article_id, event_symbol_id)` order; CT only emits `CTUSDT` while known CT-root Batch7 duplicate files are excluded before selection.
5. Resolve exactly one accepted event and one completed state per child, requiring matching identity and `observation_window_start_ms`. For structurally valid rows, form `valid_price_rows`; locate anchor and horizons only from valid prices. Enforce the exact iff gap rules: invalid intermediate retains concrete anchor/horizons but nulls `sampled_path`; invalid first uses later valid anchor; all-invalid adds `invalid_price_row` plus `missing_anchor` and nulls anchor/horizons/path. Compute each return exactly as `10000 * (mid_h / anchor_mid - 1)` and extrema/sample count only from valid rows from anchor through the selected 4h row, inclusive. Only all-nine-complete produces `complete_n3_exploratory_analysis`; otherwise publish all nine in `coverage_inventory`.
6. Copy same-parent H `friction_context` only as descriptive context. Produce no pooled/regime aggregate, rank, direction, cost verdict, full-path claim, MAE/MFE tail bound, PnL, fee/funding, signal or Alpha field.

**Verify:** replay every Task 1 RED node after its target gate exists; each becomes GREEN only by observing the ledgered STOP/state after all preconditions. The independent oracle must match every concrete anchor, horizon, return, sampled extrema and sample count; all endpoint/out-of-window fixtures must reach their declared selection rule. The canonical positive fixture must show nine children, three parents, fixed horizons, 19 boolean-false flags and no cross-regime/child independence upgrade.

## 6. Task 3: Exact artifact grammar, strict loader and crash-safe lifecycle

**Files:** modify the new I core and core test file only.

1. Implement canonical UTF-8 JSON summary/manifest and deterministic Markdown render exactly per Design Section 5.3-5.4: two possible `analysis_state`/`decision` pairs, exact G/H bindings, three fixed source-root bindings, nine child grammar, three parent-local context rows, and exact 19-false flags.
2. Implement strict summary/manifest/review loaders and `load_verified_n3_sampled_mid_price_response_root()`. Before every resolve/read, reject leaf or ancestor symlink; require canonical final parent, exact artifact set, exact keys/types, finite numbers, matching byte counts/hashes, exact G/H lineage and byte-identical Markdown re-render.
3. Implement `classify_n3_sampled_mid_price_response_root_state()` with only `unpublished`, `staging_only`, `receipt_published`, `corrupt_or_unknown`. A foreign/malformed staging sibling, final-plus-staging, symlink, invalid final, collision, or unknown file is not success.
4. Implement one private lifecycle helper for `tmp_path` tests and one private production publication helper. There is no public writer: only `run_diagnostic(run_id)` may invoke the production helper after both authority guards. After creating and symlink-checking the fixed output parent, open that **parent directory itself** and hold its single `fcntl.flock(LOCK_EX)` FD from final/staging existence checks through staging write/strict-load, rename, parent `fsync`, reclassification and strict final load. The test helper uses the same protocol over its `tmp_path` parent; it must not lock a staging directory, final root, per-run file, or any path below the output parent. Write summary then review then manifest-last with file `fsync`, directory `fsync`, and atomically rename only into an absent final. No overwrite, resume, cleanup or retry. Pre-rename crash is `staging_only`; failure after rename/parent `fsync` raises `POST_RENAME_DURABILITY_FAILURE` and never success.

**Verify:** lifecycle tests run only under `tmp_path`; they prove no real `data/external_signal_shadow/stage1_5i/` path exists or is written. The synchronized two-process same-`RUN_ID` test proves both processes contend for the same parent directory lock, exactly one publishes, and the loser exits non-success after lock acquisition without overwrite. Strict loader probes for all single-field/schema/artifact/symlink mutations STOP; crash probes leave the required non-success state.

## 7. Task 4: Narrow CLI and public permission wiring

**Files:** create `scripts/external_signal_shadow/run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py`; update the CLI test file.

1. Expose only `--approved-design-path`, `--approved-design-sha256`, `--approved-plan-path`, `--approved-plan-sha256`, and `--run-id`. Validate literals against compiled constants and reject malformed/extra arguments before core work. There is no root, source, output, receipt, bundle, URL, resume, consumer, network, replay or runtime override.
2. `run_diagnostic(run_id)` accepts only `run_id`; it derives root and canonical authority-bundle path directly from module location, literal I bundle directory and compiled Plan SHA. It validates both authority layers before all source/import/staging operations and delegates only to private I reducer/publication helpers. It is the sole public production publication route; no public `publish*`/`write*` function may exist or be imported by the CLI.
3. Add a non-monkeypatch locator and public-surface test proving the exact canonical bundle path, proving environment variables or parser input cannot influence it, and proving `run_diagnostic(run_id)` is the only public production publication route. AST/import checks reject exported `publish*`/`write*` lifecycle functions and any CLI import/call path that bypasses `run_diagnostic`; they also reject env reads, caller-selected paths, glob/iteration discovery, `latest`, old H V3, network, SSH, subprocess, commit/push/deployment, execution, paper/live, replay and future-consumer wiring.
4. Add public core/CLI integration tests that retain actual project root and actual G/H/root re-admission, but redirect only private post-locator authority content to a `tmp_path` bundle and replace only the final private lifecycle sink with a spy after fixed output-parent validation. They prove the public route reaches nine child/three parent reduction and canonical I output-parent delegation without real receipt publication. Absent/tampered generation authority proves STOP before import/source/staging.

**Verify:** CLI/core positive wiring reaches only the test-private sink; all absent/tampered authority and parser-negative tests stop before re-admission or output. `RISK_LIVE_TRADING_ENABLED is False` remains asserted.

## 8. Task 5: Final gates, scope/index proof and independent-audit handoff

**Files:** no additional repository file. Evidence only in the canonical execution bundle.

1. Repeat Task 0 authority, `BASE_SHA`, Design/Plan bytes, full status/diff/index/untracked ledger, No-Touch hash and allowed-path checks. The only new repository paths are the four whitelisted I core/CLI/test files; Design/Plan retain their captured bytes and `git diff --cached` is empty.
2. Run focused tests, scoped lint, live-risk assertion, and scanner. Persist complete output and actual process return code; do not paraphrase scanner results.

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py

.venv/bin/python -m ruff check \
  src/research/external_signal_shadow/stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py \
  scripts/external_signal_shadow/run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5i_sampled_mid_price_response_coverage_exploratory_diagnostic.py

python3 -c "from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False"

set +e
scanner_base_sha="$(cat "$EXECUTION_BASELINE_DIR/base_sha")" || { echo 'STOP=approved_authority_mismatch:scanner_base_sha_read' >&2; exit 1; }
test "$scanner_base_sha" = "96257f6f55788e9b7791bb9bb6c8bd6489300f14" \
  || { echo 'STOP=approved_authority_mismatch:scanner_base_sha_value' >&2; exit 1; }
printf '%s\n' "--base-sha=$scanner_base_sha" >"$EXECUTION_BASELINE_DIR/anti_shortcut_scan.argv"
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$scanner_base_sha" \
  >"$EXECUTION_BASELINE_DIR/anti_shortcut_scan.log" 2>&1
scanner_rc=$?
set -e
printf '%s\n' "$scanner_rc" >"$EXECUTION_BASELINE_DIR/anti_shortcut_scan.rc"
test "$scanner_rc" -eq 0 || { echo 'STOP=BLOCKED_IMPLEMENTATION_DEFECT:anti_shortcut_scan' >&2; exit 1; }
```

3. Re-run Task 0 `rg` discovery and preserve actual RC. Compare it with the baseline classification: every new hit must be one of the four whitelisted implementation/test paths; any new consumer/reference requires `BLOCKED_SCOPE_DRIFT` or `BLOCKED_SPEC_DRIFT`. Do not install/run/update Graphify or create `graphify-out/**`; the approved Design establishes it as unavailable.
4. Write canonical `review_input_snapshot.json` plus sidecar in the bundle with exactly `base_sha`, `allowed_file_sha256`, `status_sha256`, `tracked_diff_sha256`, `cached_diff_sha256`, `untracked_ledger_sha256`, `red_ledger_sha256`, `focused_test_rc`, `ruff_rc`, `scanner_rc`, `topology_rc`, and `no_real_receipt_proof_sha256`. Independent review binds this snapshot, all exact artifacts, actual producer-to-loader route, one-mutation tests, lifecycle state, authority isolation, scope/index evidence and the no-receipt proof.
5. Before fresh Completion Audit, regenerate `completion_handoff_snapshot.json` with the same shape and require byte equality with `review_input_snapshot.json`. Difference is `STOP=code_review_snapshot_drift`; obtain a new independent review. Completion Audit independently reruns loaders/probes/gates/scanner and does not accept executor summaries.

## 9. Completion routing and proof limits

This Plan can prove a deterministic sampled-mid descriptive consumer preserves fixed N=3 lineage, exact coverage states, artifact integrity, recovery behavior and permission isolation. It cannot prove announcement-time response, complete price path, full MAE/MFE, expected return, cost coverage, capacity, Alpha, strategy direction, execution feasibility or any trade permission.

If independent Completion Audit is `COMPLETE`, the only next optional operation is a separate user-signed five-line local receipt-generation authority for one exact `RUN_ID` and audited I core/CLI hashes. It still grants no downstream consumer, Alpha, execution, paper/live, network, deployment or commit authority.
