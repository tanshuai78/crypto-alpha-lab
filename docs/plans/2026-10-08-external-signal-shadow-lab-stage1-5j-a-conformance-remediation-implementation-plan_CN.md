# Stage 1.5J-A Conformance Remediation Implementation Plan

> **For implementer:** 必须按 Task 顺序执行；每个 Gate 失败即停止。仅在用户逐字批准本 Plan 的 exact SHA-256 后，才可实施 Task 0--6。不得使用本 Plan 作为 network、receipt、commit、push、deployment、SSH、replay、signal、paper 或 live trading 授权。

**Goal:** 以最小变更修复 Stage 1.5J-A 的 journal exact grammar、presence-window UTC-date set 和 finite-positive `Decimal` CSV 校验，使未来 replacement receipt 可在独立授权后按父级 J-A Design 与 approved Delta 重新产生和审计。

**Architecture:** 只修改既有 J-A core producer/strict loader 及其研究测试。`RequestManager` 在 transport 前持久化 exact intent，并以同一 grammar 写入 terminal；archive logical identity 由纯 UTC-date helper 生成；CSV validator 使用标准库 `Decimal`。strict loader 从 raw journal、logical records、package bytes 和 reducer 独立重放，不兼容 legacy root。

**Tech Stack:** Python 3 标准库（`datetime`、`decimal.Decimal`、`json`、`zipfile`、`fcntl`）、pytest、Ruff、现有 `anti_shortcut_scan.py`。

---

## 1. Authority Binding And Fixed Inputs

| item | exact value |
| --- | --- |
| approved Delta | `docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md` |
| approved Delta SHA-256 | `6063ed103d31fcf6c60ad8106eb13650f54b74272182c78bf8e81f9ba48a91ac` |
| parent J-A Design | `docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md` |
| parent J-A Design SHA-256 | `b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a` |
| original J-A Plan | `docs/plans/2026-10-06-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-implementation-plan_CN.md` |
| original J-A Plan SHA-256 | `fa7d2ac23a605163a3ceb476efe4c5823b94e16ef9944ced173a2cff9d07279f` |
| immutable execution baseline | `23708b840384b56d11b17b8d63c131e9ce72f2d3` |
| immutable legacy root | `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261007T091336Z/` |
| canonical positive component fixture | `tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/` |

`APPROVED_PLAN_*` is intentionally not supplied here: it is the SHA-256/path of this Plan after independent review and the user's later implementation-approval sentence. Task 0 must parse that sentence, recompute this document's bytes, and STOP unless both values agree. It must then use that exact Plan identity in the new core authority constants and `.git/plan-execution/stage1_5j_a/<APPROVED_REMEDIATION_PLAN_SHA256>/` bundle.

The approved Delta is a deterministic provenance repair only. This Plan must not create or modify any alpha rule, price response, net PnL, cost model, parent aggregation, J-B measurement, trade signal, execution path, network profile, resource limit, or risk threshold.

## 2. Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py`

Allowed documentation paths:
- none -- this Plan, the approved Delta, parent Design, and original J-A Plan are immutable read-only authority during execution.

Allowed generated/runtime artifacts:
- `.git/plan-execution/stage1_5j_a/<APPROVED_REMEDIATION_PLAN_SHA256>/{base_sha,execution_authority.json,execution_authority.sha256,implementation_authorization.txt,implementation_authorization.sha256}` -- create once in Task 0 after the separate user implementation-approval sentence; never committed.
- `.git/plan-execution/stage1_5j_a/<APPROVED_REMEDIATION_PLAN_SHA256>/evidence/**` -- create-once Task 0 ledger, Task 5 review snapshot/receipt, and Task 6 completion-audit snapshot only; never committed.

Affected but unchanged:
- `scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py`
  - compatibility evidence: it imports the Core identity constants rather than duplicating them; an updated CLI test and AST/runtime assertion prove its sole production delegation remains `run_inventory(run_id)`.
- `configs/base.py`
  - compatibility evidence: existing `EXTERNAL_SIGNAL_STAGE1_5J_A_*` caps and `PRESENCE_WINDOW_MS` are reused verbatim; no new threshold is necessary.
- `docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md`
  - approved immutable authority input.
- `docs/plans/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-implementation-plan_CN.md`
  - immutable authority input after its independent review and user implementation-approval sentence; Task 0/5/6 verify its exact bytes.
- parent J-A Design, original J-A Plan, frozen parser, all 1.5D/F/G/H/I files, J-B Design, execution/risk code, VPS state, and the immutable legacy root.
  - compatibility evidence: read-only identity/hash checks and targeted tests only.

Forbidden:
- Any mutation outside the paths above, including `configs/base.py`, CLI code, J-B, the parent J-A Design/Plan, legacy receipt/raw bytes/manifest/journal, or existing project-state documents.
- Any runtime output under `data/external_signal_shadow/stage1_5j_a/**` during implementation.
- Network I/O, DNS, receipt generation, replay, signal generation, paper/live trading, execution, commit, push, deployment, SSH, `git reset`, `git rebase`, `git clean`, or full-repository autofix/formatting. Creating canonical runtime `network_authorization.txt` / `network_authorization.sha256` under `.git/plan-execution/stage1_5j_a/<APPROVED_REMEDIATION_PLAN_SHA256>/` is forbidden; isolated `tmp_path` network-authorization bytes used only by the existing private test verifier are permitted and grant no runtime authority.
- `ruff check --fix`, permissive legacy parsing, fallback identity aliases, handcrafted upstream-success packets, and changing a threshold or network profile.

## 3. Contract Map And Stop Rules

| Delta invariant | implementation owner | mechanical proof | fail-closed STOP / route |
| --- | --- | --- | --- |
| `INV-15J-A-R-01` | `RequestManager`, private journal grammar/reducer component validator, strict loader | pre-network component exact-key/enum/field-combination mutations; post-network public-root mutation replay | malformed or legacy journal -> component/loader STOP; no compatibility branch |
| `INV-15J-A-R-02` | `RequestManager`, private journal grammar/reducer component validator, strict loader | component one-intent/one-terminal, durable-before-transport and controlled-404 tests; post-network public-root replay | missing/duplicate terminal or `http_non_200` -> component/loader STOP; no compatibility branch |
| `INV-15J-A-R-03` | pure required-date helper and archive loop/records | midnight/non-midnight fixture-derived tests, logical identity replay | missing/duplicate/out-of-window date -> reduction STOP |
| `INV-15J-A-R-04` | `validate_archive_package` and strict loader replay | canonical GRVT ZIP pass; one CSV-token mutation plus derived matching checksum reaches numeric STOP | package numeric STOP, never `checksum_mismatch` or `float()` coercion |
| `INV-15J-A-R-05` | authority constants and execution verifier | create-once exact authority bundle, Delta/Plan/disk SHA and byte-ledger rechecks | identity/sidecar/ledger mismatch -> authority STOP before transport |
| `INV-15J-A-R-06` | public strict loader | direct read-only legacy-root load rejects | `disk_sha_mismatch` or journal grammar STOP; no rebinding |
| `INV-15J-A-R-07` | existing reducer | fixture-derived parent/child omission test | coverage gap remains explicit; no deletion/filtering |
| `INV-15J-A-R-08` | existing atomic publisher | existing same-`RUN_ID`, crash-state and sealed-tree tests rerun | collision/recovery failure -> STOP; do not alter lifecycle design |
| `INV-15J-A-R-09` | later receipt-closure route | post-network only: positive replacement load before one-at-a-time `/tmp` mutations | absence of a replacement root is `DEFERRED_TO_RECEIPT_CLOSURE_AUDIT`, not GREEN |
| `INV-15J-A-R-10` | all tasks | AST/import/flag checks and no-network probes | any authority elevation -> stop and return `BLOCKED_SCOPE_DRIFT` |

## 4. Task 0: Freeze Baseline, Authority, Fixture, And Scope

**Invariants:** all, especially `R-05`, `R-06`, `R-10`.

**Files:**
- Create at execution only: `.git/plan-execution/stage1_5j_a/<APPROVED_REMEDIATION_PLAN_SHA256>/**`
- Read only: all paths in Sections 1-2.

1. Before creating or mutating `AUTHORITY_DIR`, parse the user implementation-approval sentence for this exact Plan path/SHA; recompute Delta and Plan SHA-256; verify `HEAD == 23708b840384b56d11b17b8d63c131e9ce72f2d3`; verify the index is clean; and define `AUTHORITY_DIR=.git/plan-execution/stage1_5j_a/<APPROVED_REMEDIATION_PLAN_SHA256>`. Any failure in steps 1--3 must create no authority directory.
2. Before authority initialization, derive and validate in memory the canonical bytes for a future `evidence/pre_execution_frozen_bytes.json` plus exact SHA-256 sidecar; do not create any file yet. The payload must record `git status --short --untracked-files=all`, `git diff --name-only`, `git diff --cached --name-only`, and path/byte-count/SHA-256 for every frozen or pre-existing path. It must include the Delta, this remediation Plan, parent J-A Design, original J-A Plan, canonical fixture manifest, immutable legacy-root top-level artifacts, and every pre-existing dirty/untracked path. Derive and validate in memory a sorted, relative-path plus manifest-SHA ledger of every existing directory immediately below `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/`; this is the pre-network output baseline. At authoring time the expected pre-existing paths are:
   - `docs/project-status/current-document-index_CN.md`
   - `docs/project-status/current-project-state_CN.md`
   - `docs/roadmap.md`
   - `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md`
   - `docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md`
   - this Plan, if it remains untracked when authorization is issued.
   Any other pre-existing path, or any newly appearing path outside the exact three implementation/verification paths in Task 5 and the future bundle's `evidence/`, is not attributable to this task. STOP=`BLOCKED_SCOPE_DRIFT`; never clean, revert, stage, overwrite, or rehash the ledger after Task 0.
3. Verify `git ls-files tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/` yields exactly the canonical five files; verify its `fixture_manifest.json` identities and obtain fixture values only through the real catalog/detail/ZIP/CHECKSUM bytes and existing frozen parser/validator. Run targeted impact discovery: `graphify query "RequestManager"`, `graphify query "validate_archive_package"`, `graphify query "load_verified_stage1_5j_a_historical_archive_coverage_root"`, and `graphify query "run_inventory"`. If Graphify is unavailable/stale, record that fact and run equivalent `rg` searches over `src/`, `scripts/`, and `tests/`. Classify every verified consumer as modified or compatible-unchanged. A newly required file is scope drift, not permission to edit it.
4. Only after steps 1--3 pass, verify `AUTHORITY_DIR` is absent. If it exists, STOP=`approved_authority_mismatch` without mutation. No action before successful step 4 may create the directory.
5. Only after step 4 passes, create `AUTHORITY_DIR` once, then atomically write exactly the following five authority files and no canonical `network_authorization.txt` / `network_authorization.sha256` pair: `base_sha`, `execution_authority.json`, `execution_authority.sha256`, `implementation_authorization.txt`, and `implementation_authorization.sha256`. Materialize the precomputed baseline bytes unchanged as `AUTHORITY_DIR/evidence/pre_execution_frozen_bytes.json` plus its exact sidecar and output-root ledger. The top-level directory may additionally contain only `evidence/`.
   - `base_sha` is exactly `23708b840384b56d11b17b8d63c131e9ce72f2d3\n`.
   - `implementation_authorization.txt` is exactly two UTF-8 lines, each LF-terminated:
     ```text
     我批准实施 Plan：docs/plans/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-implementation-plan_CN.md（SHA-256: <APPROVED_REMEDIATION_PLAN_SHA256>）。
     允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action.
     ```
   - each `.sha256` sidecar is exactly `<lowercase-hex-sha256><two spaces><referenced filename>\n` over its sibling's exact bytes.
   - `execution_authority.json` is UTF-8 canonical JSON (`sort_keys=True`, separators `(',', ':')`, `ensure_ascii=False`, final LF) with exactly `approved_design_path`, `approved_design_sha256`, `approved_plan_path`, `approved_plan_sha256`, `base_sha`, `current_plan_sha256`, and `project_root`. Its Design fields bind the approved Delta; both Plan SHA fields bind this approved remediation Plan; `base_sha` binds the value above; `project_root` resolves to the canonical workspace root.
   STOP=`approved_authority_mismatch` if any authority byte/key/sidecar differs, the bundle contains any other entry, or either approved source file's on-disk SHA differs. A failure after creation preserves the failed attempt for audit and prohibits overwrite, reuse, or rebaseline.

**Verification commands:**
```bash
git rev-parse HEAD
git diff --cached --quiet
git status --short --untracked-files=all
AUTHORITY_DIR=".git/plan-execution/stage1_5j_a/<APPROVED_REMEDIATION_PLAN_SHA256>"
shasum -a 256 docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md \
  docs/plans/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-implementation-plan_CN.md
git ls-files tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/
find data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory \
  -mindepth 1 -maxdepth 1 -type d -print | sort
# All commands above must pass before this irreversible create-once check.
test ! -e "$AUTHORITY_DIR"
```

**Expected result:** baseline/approved bytes match; index is clean; all preconditions completed while the authority directory remained absent; it is then sealed with exactly five required files plus `evidence/`. No canonical network sidecar, code/data mutation, or socket exists. Otherwise stop.

## 5. Task 1: Write Focused RED Tests From the Frozen Contract

**Invariants:** `R-01` through `R-08`, `R-10`.

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py`
- Read only: core, canonical fixture, legacy root, CLI test.

1. Add failing pre-network component tests for exact journal grammar. Use production `RequestManager` in a temporary staging directory and a controlled standard-library HTTP response to produce canonical positive journal bytes; then invoke the private journal grammar/reducer component validator that the strict loader will reuse. Assert exact key sets for intent and terminal, exact `admitted_pending`, and a controlled 404 mapping to `http_not_found`. Apply exactly one field mutation per probe: omit `request_state`; add `created_at_utc`; set `http_non_200`; or make a 404 terminal carry response bytes. Each probe must reach the component grammar gate and assert its exact journal STOP. It must not call the public strict loader or claim a complete-root semantic proof.
2. Add pure helper RED tests for the interval endpoints: non-crossing interval produces one sorted date; interval crossing UTC midnight produces exactly two sorted dates; all returned logical identities retain `(parent_article_id, symbol, utc_date, "aggTrades", "futures_um")`; no duplicate physical download is asserted without changing current network behavior.
3. Add fixture-derived archive validator RED tests. The real GRVT ZIP/CHECKSUM must first pass unchanged. For each negative probe, create a temporary ZIP at the canonical basename, changing exactly one CSV `price` or `quantity` token to `NaN`, `sNaN`, `Infinity`, `-Infinity`, `0`, or a negative decimal; then generate the temporary `.CHECKSUM` from that mutated ZIP's SHA and same basename. This is one semantic token mutation plus the required dependent integrity-sidecar update, so `validate_archive_package()` reaches the Decimal gate. Assert the exact numeric CSV STOP and explicitly assert it is not `checksum_mismatch`, ZIP, header, or other earlier gate.
4. Add public-loader pre-network structural tests only: directly read the immutable legacy root in place and assert rejection; separately give the public loader only incomplete/malformed temporary roots and assert fail-closed structural STOP. Do not copy/change the legacy root, create a synthetic complete root, change an authority packet, or claim public-loader journal semantic mutation coverage. Retain existing collision, crash/recovery, sealed-tree, no-socket, governance-flag and CLI-delegation tests.
5. Run only these new tests and demonstrate RED against the pre-fix core. If any expected test is already green, inspect whether it is testing a different contract; do not weaken it to manufacture RED.

**Verification command:**
```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  -k 'journal_exact or http_not_found or required_utc_date or finite_decimal or legacy_root'
```

**Expected result:** failure proves the current missing fields/legacy enum/date/numeric behavior at their actual component gates. No public-loader positive root, HTTP connection outside the controlled component transport, or `data/` output is permitted.

## 6. Task 2: Implement Exact Journal Producer And Strict-Loader Grammar

**Invariants:** `R-01`, `R-02`, `R-05`, `R-06`, `R-08`, `R-10`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py`

1. Before altering production code, retain Task 1 RED failures and inspect every `RequestManager.request` caller. Extend the existing call contract minimally so each request supplies or derives only `parent_article_id`, `symbol`, and `utc_date`, using `null` for non-applicable kinds. Do not introduce a new transport interface, registry, timestamp field, or configurable journal schema.
2. Emit and fsync intent before any `HTTPSConnection` with exactly these keys and no others: `event`, `request_id`, `request_kind`, `request_state`, `url`, `parent_article_id`, `symbol`, `utc_date`. Set `event="request_intent"` and `request_state="admitted_pending"`.
3. Emit exactly one fsynced terminal with precisely `event`, `request_id`, `request_state`, `http_status`, `transport_error`, `response_relative_path`, `response_sha256`, `response_bytes`. Map 404 only to `http_not_found`; map other non-200/non-404 status only to `response_rejected`; preserve parent Design combinations for persisted and transport-inconclusive outcomes. Remove acceptance/production of `http_non_200` and all time metadata.
4. Extract the minimum private journal grammar/reducer component validator from the strict loader, then have the strict loader call that same validator. It joins terminals to intents, requires contiguous IDs, exactly one terminal per intent, exact keys, allowed state combinations and correct request context. It must reject the legacy journal rather than normalize it. Preserve raw response path/hash/size verification and all existing sealed-tree checks; do not export a new public API.
5. Change `APPROVED_DESIGN_REL_PATH/SHA256` to the Delta; change Plan constants only after Task 0 has supplied the exact approved Plan identity. Keep the replacement `authority_packet` key set unchanged. Update the local identity expectations in both research and CLI tests. The CLI implementation imports these Core constants and therefore remains unchanged; source inspection plus its updated test must prove that its sole production delegation remains `run_inventory(run_id)`.
6. Change `PLANNING_BASE_SHA` only to the frozen Task 0 value `23708b840384b56d11b17b8d63c131e9ce72f2d3`; the canonical `base_sha` file, `execution_authority.json.base_sha`, core constant, authority tests, and Task 5 snapshot must agree exactly. No other baseline is admissible.

**Verification commands:**
```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  -k 'journal_exact or http_not_found or legacy_root or authority'
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
```

**Expected result:** Task 1 contract tests turn GREEN; CLI remains a compatible unchanged consumer. Any second public writer, permissive legacy branch, identity mismatch, or socket during an authority failure is STOP.

## 7. Task 3: Implement Date-Set and Finite Decimal Repair

**Invariants:** `R-03`, `R-04`, `R-07`, `R-08`, `R-10`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py`

1. Implement one private, deterministic helper using integer milliseconds and UTC calendar conversion. It returns every calendar date that intersects the closed interval `[launch_time_ms, launch_time_ms + EXTERNAL_SIGNAL_STAGE1_5J_A_PRESENCE_WINDOW_MS]`, sorted and deduplicated. Reuse the existing archive path/record code; do not add configuration or a date service.
2. Replace the single launch-date archive request with one logical record per required date. Deduplicate only physical fetches with the already-required `(symbol, utc_date, kind/provider)` identity; preserve every parent-scoped logical record. A missing response for any date remains an explicit child/parent coverage gap.
3. Parse raw CSV price and quantity tokens directly as `Decimal`. Reject parsing errors, non-finite values, zero and negative values before any aggregate is accepted. For the Task 1 dependent-checksum probes, assert the numeric CSV STOP is reached only after checksum validation succeeds. Retain all existing ZIP, header, ordering, ID, maker, SHA and resource-limit validation; no float-based admissibility predicate may remain.
4. Extend strict-loader replay to recompute the required date set and compare exact logical identities/date membership, then rerun the finite-positive package validator on raw ZIP bytes. Do not change coverage-state precedence, universe selectors, frozen parser, resource caps, network profile or flags.

**Verification commands:**
```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  -k 'required_utc_date or archive_package or finite_decimal or coverage_gap'
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
```

**Expected result:** real GRVT component evidence passes; every single bad numeric token and date-set mismatch fails closed; all focused tests pass with zero network I/O. A date computation that needs an unavailable upstream field is `BLOCKED_SPEC_DRIFT`, not a guessed default.

## 8. Task 4: Preserve Production Wiring, Lifecycle, And No-Authority Boundary

**Invariants:** `R-05`, `R-06`, `R-08`, `R-09`, `R-10`.

**Files:**
- Modify only if Task 2/3 requires it: core and research test paths already whitelisted.
- Read only: CLI/script test, `configs/base.py`, legacy root, parent Design/Delta.

1. Prove from AST and runtime inspection that the unchanged CLI delegates only to `run_inventory(run_id)` and exposes no alternative writer, project-root override, skip-authority argument, or transport injection. Its approved path/SHA literals must be checked against the replacement Core's identity expectation; incompatible literal wiring is scope drift, not a local edit permission.
2. Rerun existing same-`RUN_ID` dual-process locking, crash-after-staging, final-only, final-plus-staging, no-resume, manifest sealed-tree, and no-socket failure tests. The remediation must not refactor flock/fsync/rename/recovery code merely because it is adjacent.
3. Verify implementation authority separately: the public zero-argument `verify_execution_authority()` validates only the canonical Task 0 five-file bundle. It must fail before transport for a missing or malformed implementation bundle, unexpected entry, changed Delta/Plan byte, base-SHA mismatch, malformed sidecar, project-root mismatch, or `RISK_LIVE_TRADING_ENABLED is not False`. It MUST NOT bind Core/CLI/Config/frozen-parser SHA values, a network packet, or `AUTHORIZED_RUN_ID`. Test its positive path only from canonical on-disk Task 0 bytes; no handcrafted success dictionary or copied attestation.
4. Verify network authority separately, using only `_verify_network_authorization_for_test(run_id, bundle_dir, project_root)` with an isolated `tmp_path` packet during implementation. Test absent packet, malformed grammar or sidecar, wrong run ID, wrong Delta/Plan/Core/CLI/Config/frozen-parser SHA, and wrong network profile or request-cap values. The public `verify_network_authorization(run_id)` may only be checked to fail closed for an absent canonical packet; neither test may create the canonical runtime pair under `.git/plan-execution/**`, call transport, or grant runtime authority.
5. Assert `RISK_LIVE_TRADING_ENABLED is False` and every J-A governance flag is false. Confirm no import/call edge reaches execution, order, replay, paper, or signal generation.

**Verification commands:**
```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
python3 -c 'from configs.base import RISK_LIVE_TRADING_ENABLED; assert RISK_LIVE_TRADING_ENABLED is False'
# Compare this sorted path + manifest-SHA output with Task 0's immutable ledger.
find data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory \
  -mindepth 1 -maxdepth 1 -type d -print | sort
```

**Expected result:** pre-network component/structural verification is GREEN; the Task 4 output-root ledger is identical to Task 0's ledger, no receipt is generated, and no public strict-loader positive-load claim is made. Lack of replacement root is expected and must be recorded as `deferred_to_receipt_closure_audit=true`.

## 9. Task 5: Scope, Static Gates, And Independent Review Handoff

**Invariants:** all; gate before Completion Audit.

**Files:**
- Read only: allowed paths, authority evidence, baseline ledger, Delta, parent Design, original Plan.
- Create at execution only: `.git/plan-execution/stage1_5j_a/<APPROVED_REMEDIATION_PLAN_SHA256>/evidence/**`.

1. Run only targeted non-mutating checks. Capture each command's actual process return code in evidence; a textual scanner report without `RC=0` is not a pass.
2. Prove scope/index: `git diff --name-only BASE_SHA`, `git diff --cached --name-only`, `git status --short --untracked-files=all`, and Task 0 ledger must show that the exact implementation-attributable changed-path set is:
   ```text
   src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py
   tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py
   tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
   ```
   Every Task 0 frozen/pre-existing path, including this Plan and the approved Delta, must still exist with the identical byte count and SHA-256 recorded in `pre_execution_frozen_bytes.json`; `.git` evidence is allowed only at the exact bundle path. Any extra attributable path, staged path, ledger mismatch, or output-root ledger mismatch is STOP=`BLOCKED_SCOPE_DRIFT`.
3. Create canonical `evidence/review_input_snapshot.json` plus exact `.sha256` sidecar, without timestamps or nondeterministic fields. It must bind: `BASE_SHA`; current `HEAD`; approved Delta path/SHA; approved remediation Plan path/SHA; parent Design SHA; Task 0 frozen-ledger SHA; output-root-ledger SHA; exact three changed-path SHA-256 values; SHA-256 of the binary diff from `BASE_SHA`; canonical fixture-manifest SHA; sorted authority-bundle file-hash map; pytest/Ruff/scanner exact argv and RC; `RISK_LIVE_TRADING_ENABLED=false`; and no-network/no-receipt facts. The independent Task 5 review receipt must name this snapshot SHA-256 and reject any review of different bytes.
4. Prepare the independent Task 5 code-review packet from that snapshot: exact diff; baseline/HEAD; canonical fixture provenance; RED command/output; GREEN command/output; actual scanner RC; authority/no-network proof; graph impact classification; and explicit deferred post-network items. The reviewer must inspect production core/CLI call paths, not merely test summaries.
5. Do not self-approve. If review identifies a defect within whitelist, remediate only after re-running RED/GREEN and repeat Task 5 with a new snapshot. If it requires another file or changes a frozen contract, route under L1 Rule 16.

**Verification commands:**
```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
python3 .agent/tools/anti_shortcut_scan.py --base-sha 23708b840384b56d11b17b8d63c131e9ce72f2d3; scanner_rc=$?; printf 'scanner_rc=%s\n' "$scanner_rc"; test "$scanner_rc" -eq 0
git diff --check 23708b840384b56d11b17b8d63c131e9ce72f2d3
git diff --cached --check 23708b840384b56d11b17b8d63c131e9ce72f2d3
```

**Expected result:** all gates return `0`; no staged changes, no runtime data, no network; the reviewer receipt binds exactly the recorded snapshot SHA. Failure of scanner, scope, index, byte-ledger equality, fixture provenance, snapshot binding, or reviewer approval stops the task.

## 10. Task 6: Completion Audit, Then Explicitly Deferred Runtime Route

**Invariants:** all, especially `R-09` and `R-10`.

**Files:**
- Read only: current workspace and Task 5 evidence.
- No new source/data/document mutation in this task.

1. Before auditing, regenerate `evidence/completion_audit_input_snapshot.json` with the exact deterministic schema from Task 5 and generate its sidecar. Require byte-for-byte equality, and therefore equal SHA-256, with `review_input_snapshot.json`; otherwise the Task 5 receipt is stale and the workflow returns to Task 5 without a completion verdict. A fresh independent completion auditor must verify the approved Plan bytes/authority, current diff/index/untracked state, both production and loader paths, canonical fixture lineage, exact journal/date/numeric negative probes, actual scanner exit code, byte-ledger equality, and safety flags. It must independently classify no replacement root as a correctly deferred post-network obligation, not as a missed pre-network positive test.
2. The only valid pre-network outcome is `COMPLETE_PRE_NETWORK_IMPLEMENTATION` (or equivalent completion-audit wording) with these frozen facts:
   ```text
   replacement_receipt_generated = false
   replacement_root_positive_load_verified = false
   replacement_semantic_mutation_suite_verified = false
   deferred_to_receipt_closure_audit = true
   network_authorization_present = false
   RISK_LIVE_TRADING_ENABLED = false
   ```
   It is not a receipt closure verdict and grants no runtime authority.
3. Stop after the completion audit. A later separate user authorization must bind a new, single-use `AUTHORIZED_RUN_ID`, the approved Delta/Plan, audited Core/CLI/Config/frozen parser bytes, and the frozen network profile. Only then may the canonical CLI make network requests and publish a new replacement root.
4. After that separate run, a fresh Receipt Closure Audit must first public-positive-load the exact replacement root, then copy it byte-identically to `/tmp` and apply one mutation per probe: journal key/enum/field-combination, date membership, numeric token, summary/review/count, duplicate terminal, authority packet, and manifest artifact. It must never mutate the legacy or production replacement root. J-B stays blocked until its own approved identity plus projection/cardinality rebind confirmation.

**Expected result:** no implicit transition from code completion to network/receipt/J-B authority. Any attempt to run network before a new authorization is STOP=`stage1_5j_a_network_authorization_absent`.

## 11. Rule-12 / Rule-16 Routing

Every implementation step states its change, command and expected result above. Apply these routes without improvisation:

| condition | required route |
| --- | --- |
| targeted test, fixture identity, authority, scanner, scope, index, or safety gate fails | stop at current Task; diagnose/reproduce within its approved files only |
| fix requires CLI/script test/config or any other path not explicitly whitelisted | `STOP=BLOCKED_SCOPE_DRIFT`; revise Plan first |
| frozen parent J-A Design, Delta, actual canonical fixture, or source topology conflicts | `STOP=BLOCKED_SPEC_DRIFT`; produce failed invariant, SSOT reference, contradiction, and proposed Delta |
| implementation misunderstood an approved local behavior and core/test-only fix is sufficient | `STOP=BLOCKED_IMPLEMENTATION_DEFECT`; RED -> minimum fix -> GREEN -> Task 5 again |
| all pre-network gates pass | independent Completion Audit only; do not run network, generate receipt, commit, push, deploy, SSH, replay, paper, live, or execution |

## 12. Explicit Non-Claims

This remediation can prove only J-A conformance readiness. It cannot prove historical price response, market phenomenon, statistical edge, economic edge, capacity, executability, alpha, strategy promotion/falsification, paper trading, live safety, or J-B admissibility. The safe action before later authorizations is no-op.
