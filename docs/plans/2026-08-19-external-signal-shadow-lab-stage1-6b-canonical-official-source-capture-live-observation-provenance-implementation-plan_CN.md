# Stage 1.6B Canonical Official Source Capture And Live-Observation Provenance Implementation Plan

**Plan status:** `draft_for_review`
**Approved Design:** `docs/designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md`
**Approved Design SHA-256:** `83aaa473a9ddb287ee916eae4da327966daa7b0afd5c465f7cc883a06e4f6bc0`
**Planning HEAD:** `5a6f3b476225809bc5b4cc171ed558df8b99f30d`
**Safety mode:** `research_shadow_mode`; source audit, PIT validation, market coverage, replay, risk veto, paper trading, live trading and execution remain `false`.

> **Execution authority:** After this Plan is approved, both this file and the Design above are immutable implementation inputs. Task 0 records their hashes in an execution-local log outside the repository; Task 9 must revalidate the same hashes. A Plan cannot contain its own final hash without changing it, so the approved Plan SHA-256 is recorded externally at Task 0, never written back into this file.

**Goal:** Implement isolated local historical capture and low-frequency VPS live observation with durable official-source provenance, bounded storage, fail-closed completion, and sealed-export validation. It must not alter Stage 1.5D/F, Stage 1.6A authority, market-data collection, or any trading permission.

**Architecture:** New Stage 1.6B modules own a fixed public-web profile, capture identities, candidate discovery, retry state, guarded persistence, bounded restart reconciliation, and sealed-export validation. The storage guard is implemented locally with the standard library, but test code proves it uses the exact lock path and lock protocol already used by Stage 1.5. Historical and live outputs are separate, strictly confined root families.

**Tech stack:** Python 3.11 stdlib only: `dataclasses`, `hashlib`, `json`, `pathlib`, `unicodedata`, `urllib.parse`, `urllib.request`, `fcntl`, `os`, `time`, `shutil`, `tempfile`; pytest and Ruff already installed.

---

## Allowed Change Scope

### Allowed implementation paths

- `configs/base.py`
- `src/research/external_signal_shadow/stage1_6b_canonical_source_models.py`
- `src/research/external_signal_shadow/stage1_6b_canonical_source_client.py`
- `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`
- `src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py`
- `scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py`
- `scripts/external_signal_shadow/run_stage1_6b_historical_backfill.py`
- `scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py`

### Allowed verification paths

- `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py`
- `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py`
- `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py`
- `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py`
- `tests/fixtures/external_signal_shadow/stage1_6b/**`
- `tests/research/external_signal_shadow/test_stage1_5_storage_guard.py` (read-only regression)
- `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py` (read-only regression)
- `tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py` (read-only regression)
- `tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py` (read-only regression)

### Allowed documentation paths

- `docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md`

### Allowed generated/runtime artifacts

- `data/external_signal_shadow/stage1_6b/source_profile_attestations/**` (generated only; not committed)
- `data/external_signal_shadow/stage1_6b/historical_backfill/**` (generated only; not committed)
- `data/external_signal_shadow/stage1_6b/live_observation/**` (generated only; not committed)
- `none` for `graphify-out/**`

### Affected but unchanged

- `docs/designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md`
  - immutable implementation authority; Task 0/9 SHA-256 equality is required.
- `docs/plans/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-implementation-plan_CN.md`
  - immutable implementation authority; Task 0/9 SHA-256 equality is required.
- `src/research/external_signal_shadow/stage1_5_storage_guard.py`
  - compatibility evidence: read-only test imports it solely to prove exact shared-lock equivalence; `git diff --exit-code "$BASE_SHA"` must remain clean.
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py`
- `src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py`
- `scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py`
  - compatibility evidence: read-only regression tests and zero diff; 1.6B copies the frozen candidate predicate rather than importing 1.6A production code.
- All Stage 1.5D/F scripts, roots, processes, watermarks and deployment runbooks.
  - compatibility evidence: static import/path tests plus exact zero-diff checks.

### Forbidden

- Any mutation outside the listed paths, including either approved Design or this approved Plan.
- Any Stage 1.5D/F root, process, watermark, state, config or deployment mutation.
- Any Stage 1.6A source-audit verdict enablement or modification of Stage 1.6A production/read-only verification paths.
- Any market-data, L2, funding, OI, fee, account, order, Cookie, Authorization, replay, risk-veto or trading implementation.
- Any Stage 1.6B production import of a Stage 1.5D/F or Stage 1.6A module.
- Worker pools, async fan-out, daemonized historical backfill, root-wide periodic scans, automatic cleanup/deletion.
- `ruff check --fix .`, `git clean`, `rsync --delete`, broad formatter/refactor changes, or Graphify updates.

## Preconditions And Stop Conditions

1. Implementation starts only after Plan approval and explicit user approval. Task 0 records `BASE_SHA`, `DESIGN_SHA256`, `PLAN_SHA256`, `git status --short --untracked-files=all`, and SHA-256 for every pre-existing dirty/untracked path in an execution-local directory outside the repository.
2. Task 0 copies `configs/base.py` to an execution-local `CONFIG_BASELINE_PATH`. It verifies the current Stage 1.5 host/storage SSOT assignments exist before any source change; historical documents are not configuration evidence.
3. Stop if the Design/Plan hash changes, a pre-existing dirty/untracked path changes unexpectedly, a Stage 1.5/1.6A consumer needs modification, a new source endpoint/profile is required, or any `INV-*` cannot be preserved. Do not edit authority documents to resolve a stop.
4. No unit test may make a real network request. All network-capable commands require exact `--live-public-readonly`; absent permission must fail before client construction, DNS/HTTP, or any output mutation.
5. Graphify is advisory only. Do not run `graphify update`; verify relations with `rg` and source.

## Topology Preflight

Run before code changes:

```bash
.venv/bin/python -m graphify query 'compute_list_capture_id'
.venv/bin/python -m graphify query 'persist_audit_artifacts'
.venv/bin/python -m graphify query 'load_completed_audit'
.venv/bin/python -m graphify query 'StorageGuard'
rg -n 'compute_list_capture_id|persist_audit_artifacts|load_completed_audit|StorageGuard|CANDIDATE_DISCOVERY_RULE_VERSION' \
  src/research/external_signal_shadow scripts/external_signal_shadow tests/research/external_signal_shadow tests/scripts/external_signal_shadow
```

Expected classification: Stage 1.6A identities/storage are read-only compatibility surfaces. Stage 1.5 guard has live downstream callers and stays unchanged. Test-only imports may compare its lock path and contention behavior; Stage 1.6B production code may not import it.

## Invariant-To-Task Mapping

| Design invariant | Tasks | Mechanical evidence |
|---|---|---|
| INV-01, INV-02, INV-17, INV-18 | 0, 1, 7, 9 | immutable hashes, AST authority check, strict roots, zero Stage 1.5/1.6A diff |
| INV-03--INV-07 | 1, 3, 4, 5 | identity, candidate-rule parity, historical null-time and profile tests |
| INV-08--INV-10 | 4, 5, 7 | deterministic scheduler, bounded epoch, retry and terminal tests |
| INV-11--INV-13 | 1, 2, 3, 4, 6, 7 | all-write guard inventory, shared lock, quota and crash/restart tests |
| INV-14, INV-19 | 1, 3, 5, 7 | profile/hash binding, exact readonly permission, attestation tests |
| INV-15--INV-16 | 5, 6 | two-sweep, completion and independent consumer acceptance tests |
| INV-20 | 8 | read-only deployment checklist review; no VPS action |

## Task 0: Immutable Provenance And Baselines

**Design invariants:** INV-01, INV-17, INV-18.

**Files:** no repository file changes.

1. Create an execution-local directory outside the repository. Record `BASE_SHA`, status, `DESIGN_SHA256`, `PLAN_SHA256`, and per-path SHA-256 provenance for all pre-existing dirty/untracked paths.
2. Copy current `configs/base.py` to `$CONFIG_BASELINE_PATH`; record its hash. Parse the current file and fail unless all existing Stage 1.5 host reserve, D terminal peak and F terminal peak assignments are present exactly once.
3. Verify the approved Design hash equals `83aaa473a9ddb287ee916eae4da327966daa7b0afd5c465f7cc883a06e4f6bc0`. Do not create, modify or normalize either authority document.
4. Run the topology preflight. Stop rather than widening scope if source evidence disagrees with the Plan.
5. Expected: no repository diff exists after Task 0; execution log and config baseline exist only outside the repository.

## Task 1: Models, Config SSOT And RED Contract Tests

**Design invariants:** INV-03--INV-07, INV-11--INV-12, INV-14, INV-17--INV-19.

**Files:**
- Modify: `configs/base.py`
- Create: `src/research/external_signal_shadow/stage1_6b_canonical_source_models.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py`
- Create: `tests/fixtures/external_signal_shadow/stage1_6b/candidate_discovery_rule_v1_cases.json`

1. Write RED identity tests for `list_payload_id`, unique `request_observation_id`, distinct page/request `list_capture_id`, `detail_revision_id`, sorted artifact tuples, and historical/live `SealedExportManifest` nullable fields.
2. Write RED **Design semantic parity** tests using the shared fixture: Unicode NFKC normalization, `casefold`, title contains both `binance futures` and `delist`, and exact rule version `candidate_discovery_rule_v1`. These tests prove the 1.6B reducer equals the frozen Design rule, without importing or changing a Stage 1.6A production helper. Detail success/failure must not alter membership; the candidate set freezes before detail work. Separately, existing read-only Stage 1.6A regressions plus Task 9 zero-diff prove current Stage 1.6A code compatibility.
3. Write RED assertions that historical values retain null PIT fields, source-profile headers exclude Cookie/Authorization, and every authority/trading output flag is false.
4. Add exactly the Design-approved `EXTERNAL_SIGNAL_STAGE1_6B_*` assignments, including the single terminal-peak authority `EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES = 256 * 1024`: live poll interval, live root max/reserves, raw payload cap, HTTP timeout, epoch max, historical page/request bounds, pending candidate cap, and retry bounds. Do not add aliases, a second terminal threshold, hidden constants, or change any existing Stage 1.5 assignment.
5. Add a RED config algebra test that reads current config values and requires `EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES >= EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES + EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES + EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES`, without hardcoding historical values.
6. Implement frozen dataclasses/enums and stdlib hash/normalization helpers. Use `urllib.parse`; do not add a custom URL parser or dependency.
7. Run the model suite and read-only Stage 1.6A parity regression. Expected: pass with no Stage 1.6A diff.

## Task 2: Strict Roots, Guarded Writes And Recovery Accounting

**Design invariants:** INV-02, INV-07, INV-11--INV-13, INV-16, INV-19.

**Files:**
- Create: `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py`

1. Write RED path-validation tests before implementation. After `resolve()`, only permit:
   - probe: `data/external_signal_shadow/stage1_6b/source_profile_attestations/<profile-sha256>/source_profile_probe_attestation.json`;
   - historical: `data/external_signal_shadow/stage1_6b/historical_backfill/<new-run-id>/`;
   - live: `data/external_signal_shadow/stage1_6b/live_observation/<new-run-id>/`.
   Reject `..`, symlink escape, non-local/special paths, Stage 1.5 roots, Stage 1.6A roots, and wrong historical/live family. This pre-lock phase performs only immutable path-level checks; it must not inspect or mutate checkpoint/state artifacts. For `fresh_live`, the exact live run root must not exist, then creation and lifetime writer-lock acquisition are atomic. For `resume_live`, the exact canonical live run root must already exist; acquire `<run-root>/.stage1_6b_writer.lock` before inspecting any mutable root artifact. While holding that lock, require `terminal_status.json` absent, no valid sealed export, valid run contract/attestation/checkpoint and valid bounded-tail reconciliation; atomically write the reconciliation checkpoint before network admission. Reject resume of terminal-complete and terminal-failure roots.
2. Write RED cross-implementation lock tests. Test code may import Stage 1.5 `StorageGuard`; production code may not. Construct sibling 1.5D, 1.5F and 1.6B roots and assert both helpers derive exactly `data/external_signal_shadow/.stage1_5_storage_guard.lock`. In both directions, holding one implementation lock must block a writer of the other; shared host lock must release after each guarded write.
3. Write RED guarded-write inventory tests for **every** persistent artifact: raw bytes, JSONL/request records, checkpoint, terminal status, export temp/rename, probe attestation, `capture_run_contract.json`, and copied root attestation. Each operation declares normal/ordinary/terminal class and exact `persistent_delta_bytes` plus `transient_peak_bytes`.
4. Define one narrow storage guard API, used by all persistent writers while holding the derived shared lock. It enforces the Design normal/ordinary/terminal formulas, 256 KiB terminal cap, existing host startup/reserve values, and 1.5D + 1.5F + 1.6B emergency peak sufficiency. Probe artifacts have no storage-admission bypass.
5. Add checkpoint accounting and resume-ownership RED tests. A checkpoint stores `accounted_root_bytes`, committed stream offsets/last hashes, and known content-addressed raw sizes. On restart, **while holding the lifetime writer lock**: recheck terminal/sealed-export/run-contract facts, verify committed prefixes, read only bounded tails/known targets, apply exact deltas, write a reconciliation checkpoint, then permit client construction/network. Test that process B cannot inspect/reconcile/write a checkpoint as owner, or call its opener, while process A holds the same root lock; after A dies B acquires the released flock, reconciles and writes before its opener may run; and a terminal state created after pre-lock path validation but before B obtains the lock is rejected by the post-lock check. Never root-scan.
6. Add crash matrix tests after raw rename, JSONL append, checkpoint temp write, terminal write, and export temp write. Retain raw orphan as non-authoritative; reject malformed committed prefix and malformed/partial final JSONL tail deterministically. In every bounded synthetic case, reconciled `accounted_root_bytes` equals expected actual bytes.
7. Implement content-addressed raw write, append, atomic JSON, checkpoint/reconciliation, SHA helpers, root writer lock helpers, and streaming export primitives only through this API. `transient_peak_bytes >= max(0, persistent_delta_bytes)` is asserted at the guard boundary.
8. Run storage tests plus read-only Stage 1.5 storage tests. Expected: cross-implementation contention, strict confinement, accounting recovery and guarded probe artifacts all pass.

## Task 3: Attested Public-Web Client And Probe Runner

**Design invariants:** INV-05, INV-11, INV-14, INV-19.

**Files:**
- Create: `src/research/external_signal_shadow/stage1_6b_canonical_source_client.py`
- Create: `scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py`
- Create: `tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py`
- Create: `tests/fixtures/external_signal_shadow/stage1_6b/profile_probe_*.json`

1. Write RED client tests with injected opener: exact HTTPS host/path/query/header validation, timeout/response-size cap, bad redirect, WAF/empty/wrong-locale/malformed rejection, and request-class recording.
2. Write RED probe-runner tests: exact 32-hex article ID, exact `--live-public-readonly`, one index and one detail request, strict probe root validation, and guarded atomic attestation persistence. Missing flag must call neither opener nor storage writer and must not create output.
3. Write RED startup validation tests for run contract/copy: exact source-profile attestation root, current profile/header hashes, `probe_attested_at_ms <= run_started_at_ms`, guarded `capture_run_contract.json`, and guarded copied attestation before any run network request.
4. Implement GET-only `urllib.request` client. Allow `urllib.parse`; statically forbid `urllib.request` bypasses, `requests`, `httpx`, `aiohttp`, `socket`, auth and cookies.
5. Run client/probe tests. Expected: fake-network tests pass; no real URL is reached.

## Task 4: Candidate Reducer, Scheduling And Restart Semantics

**Design invariants:** INV-04, INV-08--INV-10, INV-13.

**Files:**
- Create: `src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py`
- Create: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py`

1. Write RED reducer tests for `T_list_receive -> T_article_discovered -> T_detail_receive -> T_detail_trusted`, immutable earliest live values, null historical PIT fields, and candidate rule version persisted on every discovery.
2. Write RED scheduling tests: one index plus at most one detail request per 300-second poll, no intra-poll retry, Lane A precedence, Lane B exponential retry, max cycle/age terminal state, and first-attempt SLA terminal failure.
3. Write RED restart tests asserting the reconciled checkpoint is durably written before any opener call; root recovery preserves content identities and first-observed values.
4. Implement only a process-local reducer; it restores via Task 2 reconciliation and delegates all writes to Task 2. Do not add a registry, worker pool or periodic scan.
5. Run observer/storage suites. Expected: deterministic clock/opener behavior with no I/O outside temporary Stage 1.6B roots.

## Task 5: Historical Backfill, Stable Sweeps And Producer Completion

**Design invariants:** INV-03, INV-05, INV-10, INV-15--INV-16, INV-19.

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_6b_historical_backfill.py`
- Create: `tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py`
- Modify: `src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`

1. Write RED CLI tests requiring exact `--live-public-readonly`; absent flag rejects before client construction, DNS/HTTP or output mutation. Validate strict fresh historical root and 730-day maximum.
2. Write RED sweep tests for sequential A/B equality, repeated page, duplicate, insertion, ordering inversion, 429/5xx, and exact 100-page boundaries: reaching `from_ms` first on page 100 may complete; still not reaching it is incomplete and must never request page 101.
3. Write RED tests proving candidate discovery happens from persisted list captures before details; detail success/failure cannot change frozen membership. Pending/unattempted candidates or invalid final checkpoint make `historical_completion_precondition` false.
4. Implement local one-shot historical orchestration: two sweeps, frozen candidate set, one detail selection per cycle, no retry of failed index page in the same run, and fresh run ID for every retry.
5. Implement producer lifecycle exactly: stop admission, final checkpoint, evaluate producer-only `historical_completion_precondition`, then either write failure terminal/no export or write `status=complete, reason=historical_backfill_complete`, prove no active writer, and seal through Task 6.
6. Run historical tests. Expected: no incomplete condition creates an export or claims completion.

## Task 6: Sealed Export And Independent Consumer Acceptance

**Design invariants:** INV-06--INV-08, INV-11--INV-12, INV-15--INV-16, INV-19.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py`

1. Write RED tests for active/incomplete root refusal and last-written `SealedExportManifest`.
2. Write a RED quota test: source files fit but guarded export temp peak exceeds reserve. Preserve terminal collection state, create no sealed export, and never relax root/host reserve.
3. Write RED consumer tests: incomplete `HistoricalCoverage`, A/B mismatch, one pending candidate, missing terminal reason, invalid artifact hash, or non-null live historical fields all reject. Fully complete historical export accepts; live export accepts only with null historical fields.
4. Implement streaming guarded copy: each source file has guarded temp write and guarded rename. No `copytree`, unguarded `copy2`, whole-bundle read or unguarded manifest/copy artifact is permitted.
5. Implement `load_sealed_export()` to independently evaluate generic and historical acceptance predicates; never trust a producer boolean. Persist and verify `request_headers_profile_sha256` directly in the manifest.
6. Run storage suite. Expected: guarded export refusal preserves safety, and consumer rejection does not rely on producer claims.

## Task 7: Live Runner, Lifetime Writer Ownership And Static Closure

**Design invariants:** INV-01, INV-08--INV-14, INV-17--INV-20.

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py`
- Create: `tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py`

1. Write RED CLI tests requiring exact `--live-public-readonly`, strict fresh/resume live root rules, exact attestation path, and 300-second interval. Missing permission must cause zero opener calls and zero output writes.
2. Write RED epoch tests: `--max-seconds` is only an optional shorter bound; a value above `EXTERNAL_SIGNAL_STAGE1_6B_LIVE_EPOCH_MAX_SECONDS` rejects. Define `poll_bound_seconds = max_polls * EXTERNAL_SIGNAL_STAGE1_6B_LIVE_POLL_INTERVAL_SEC` and `effective_stop = min(config_epoch_deadline, optional_max_seconds_deadline, optional_poll_bound_deadline)`. `--max-polls` may only shorten; when its bound is not shorter the configured deadline remains authoritative. Test/operational early stop records `test_bound`/`operator_stop`; reaching the configured seven-day limit records `epoch_complete`.
3. Write RED lifetime root-lock tests. `<run-root>/.stage1_6b_writer.lock` is held for the full process lifetime: a second observer on the same root rejects before network, a restart after simulated process death succeeds, different Stage 1.6B roots may run, and the shared host lock is still released between individual writes.
4. Write one AST/source inventory test covering every persistent writer in all new Stage 1.6B modules/scripts, including probe attestation, run contract and copied attestation. It fails if a persistent write reaches `open`, `Path.write_*`, `Path.replace`, `os.replace`, `shutil.copy*` or append primitive without Task 2 guarded storage. No persistent writer may bypass Task 2 guarded storage.
5. Implement a thin single-process runner: validate, acquire lifetime root lock, invoke one poll at a time, and stop/seal only through observer lifecycle. No thread, process, async task, Stage 1.5 call or implicit network mode.
6. Run live/storage suites. Expected: no same-root dual writer, no unbounded epoch and no unguarded persistent writer.

## Task 8: Read-Only Deployment Checklist

**Design invariants:** INV-01, INV-17--INV-20.

**Files:**
- Create: `docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md`

1. Write a read-only checklist only. It requires the Design Section 11 Stage 1.5D/F health predicate, exact shared lock path, host 8 GiB threshold, no active Stage 1.5F observation/cutover, and completed local UNITREE Stage 1.5G review.
2. Require a probe executed for the exact intended run: the exact resulting probe attestation SHA must equal `capture_run_contract.source_profile_attestation_sha256`. Do not introduce an arbitrary freshness TTL.
3. State explicitly that this Plan authorizes neither VPS deployment nor source execution. Include no start/restart, probe URL, collector, cleanup, or configuration-enable command.
4. Run a documentation static check. Expected: no mutating command or enabled authority occurs.

## Task 9: Full Verification, Scope And Completion Audit

**Design invariants:** INV-01--INV-20.

1. Recompute Design and Plan hashes and require equality with Task 0 execution-log values before every final test. A changed authority document is a stop condition.
2. Run the full Stage 1.6B suite plus all read-only compatibility regressions:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_historical_backfill.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_5_storage_guard.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py \
  tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py \
  -q
```

3. Run bounded static checks:

```bash
.venv/bin/ruff check configs/base.py src/research/external_signal_shadow/stage1_6b_*.py scripts/external_signal_shadow/run_stage1_6b_*.py tests/research/external_signal_shadow/test_stage1_6b_*.py tests/scripts/external_signal_shadow/test_run_stage1_6b_*.py
git diff --check "$BASE_SHA"
git diff --exit-code "$BASE_SHA" -- src/research/external_signal_shadow/stage1_5_storage_guard.py src/research/external_signal_shadow/stage1_5d_*.py src/research/external_signal_shadow/stage1_5f_*.py scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py src/research/external_signal_shadow/stage1_6a_*.py scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py tests/research/external_signal_shadow/test_stage1_5_storage_guard.py tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_models.py tests/research/external_signal_shadow/test_stage1_6a_futures_delisting_storage.py tests/scripts/external_signal_shadow/test_run_stage1_6a_futures_delisting_source_audit.py
```

4. Run one repository-local Python verification script against `$BASE_SHA`, `$CONFIG_BASELINE_PATH`, and an explicit list of all Allowed implementation, verification and documentation paths. It must fail on any changed/added path outside that list; it must compare config ASTs and allow exactly one top-level single-target assignment for each approved `EXTERNAL_SIGNAL_STAGE1_6B_*` constant, with every baseline AST node unchanged and no duplicate authority. It must also compare this complete name-to-literal-value map to the frozen Design: `LIVE_POLL_INTERVAL_SEC=300`; `LIVE_ROOT_MAX_BYTES=256*1024*1024`; `LIVE_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES=4*1024*1024`; `LIVE_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES=1*1024*1024`; `LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES=256*1024`; `MAX_RAW_PAYLOAD_BYTES=2_000_000`; `HTTP_TIMEOUT_SEC=10.0`; `LIVE_EPOCH_MAX_SECONDS=7*24*60*60`; `HISTORICAL_MAX_INDEX_PAGES=100`; `HISTORICAL_REQUEST_INTERVAL_SEC=1.0`; `MAX_PENDING_DETAIL_CANDIDATES=500`; `DETAIL_FIRST_ATTEMPT_MAX_POLLS=2`; `DETAIL_RETRY_MIN_INTERVAL_SEC=300`; `DETAIL_RETRY_MAX_INTERVAL_SEC=3600`; `DETAIL_RETRY_MAX_CYCLES=12`; `DETAIL_RETRY_MAX_AGE_SEC=24*60*60`.
5. The same script must parse `configs/base.py` and new Stage 1.6B source/script ASTs, failing if any of these are assigned/called with a truthy literal: `RISK_LIVE_TRADING_ENABLED`, `trade_signal_allowed`, `paper_trading_allowed`, `live_trading_allowed`, `execution_engine_allowed`, `alpha_interpretation_allowed`, `source_audit_passed`, `point_in_time_source_validated`, `market_data_coverage_passed`, `replay_allowed`, `risk_veto_candidate`, or risk-veto enforcement. It must also enforce the static guarded-write inventory from Task 7.
6. Run `.agent/skills/audit-plan-completion` against `BASE_SHA`, this immutable Plan and the final diff. Required verdict: `complete` before any commit, deployment decision or source run.

## Completion Boundary

This Plan completes an isolated Stage 1.6B capture implementation and its test/documentation contract. It does **not** authorize a real historical backfill, source-profile probe, VPS deployment, Stage 1.6A real-source consumer, source-audit pass, market-data collection, replay, risk veto or any trading behavior.
