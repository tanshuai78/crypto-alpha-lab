# Stage 1.5J-B Replacement Receipt Rebind Implementation Plan

> **For executor:** Execute task-by-task under `.agent/workflows/execute-approved-plan.md`. Use TDD (`RED -> minimal implementation -> GREEN`) for every behavior change. This Plan is not implementation authority until independently reviewed and explicitly approved by the user.

**Goal:** Implement Stage 1.5J-B as a local, read-only historical `aggTrades` descriptive receipt producer/strict loader whose sole J-A input is the verified 20261010 replacement receipt, v2 governance-closure evidence, and rebound coverage projection.

**Architecture:** A new J-B core first validates immutable upstream authority, closure evidence, strict-loads J-A, and verifies every rebound projection before opening an archive ZIP. It streams one verified CSV member at a time, computes the frozen J-B descriptive rows, and publishes only an atomically staged, flock-protected local receipt after a separate offline receipt-generation authorization. Its strict loader independently replays the same input, schema, reduction, render, and tree contract. `scripts/governance/verify_artifact_schema.py` remains an independent audit CLI and is never imported by J-B `src/` code.

**Tech stack:** Python standard library (`csv`, `decimal`, `fcntl`, `hashlib`, `json`, `pathlib`, `zipfile`), existing J-A public strict loader, pytest, Ruff, project anti-shortcut scanner.

**Approved Design chain:**

```text
Parent J-B Design
docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md
SHA-256 ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b

Approved Rebind Delta
docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md
SHA-256 0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c
```

**Planning baseline:** `d15ca4e0da75a61553ca1d5983249d85a4512bb5`.

---

## 1. Scope And Immutable Inputs

### 1.1 Allowed implementation paths

Only these paths may be task-induced after Task 0:

```text
configs/base.py
src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py
scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py
tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py
tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py
.git/plan-execution/stage1_5j_b/<APPROVED_PLAN_SHA256>/**
```

### 1.2 Read-only upstream inputs

The executor must not alter, copy, rebind, manifest-rehash, or use a fallback for any of these:

```text
data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z/**
.git/plan-execution/governance_artifact_schema/ba362f2480c7872d39eede9254744d6e99216aa73134777658f9f81f05ba7881/evidence/v2_receipt_closure_evidence.json
.git/plan-execution/governance_artifact_schema/ba362f2480c7872d39eede9254744d6e99216aa73134777658f9f81f05ba7881/evidence/v2_receipt_closure_evidence.json.sha256
scripts/governance/verify_artifact_schema.py
src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py
```

The J-A root identity is exactly:

```text
run_id: stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
manifest: b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf
summary: 722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b
review: 1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152
request_journal: b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa
```

### 1.3 Explicit prohibitions

Do not modify any Design/Plan, J-A code/tests/CLI, governance verifier/tests, raw J-A root, project roadmap, or other existing receipt. Do not issue network authorization, make a network request, run production J-B receipt generation, authorize J-B consumption, create a signal/replay, calculate PnL/cost/fees/slippage/funding, or change `RISK_LIVE_TRADING_ENABLED` from `False`.

If an execution step needs another path, a changed upstream contract, a generated replacement fixture, or an implementation fallback not specified here, stop under L1 Rule 16 as `BLOCKED_SCOPE_DRIFT` or `BLOCKED_SPEC_DRIFT` rather than expanding this Plan.

---

## 2. Invariant-To-Task Map

| Invariant | Production boundary | Task and mechanical proof | Fail-closed result |
| --- | --- | --- | --- |
| `INV-JB-RB-01` | J-A replacement root identity | Tasks 0-2 bind run/root/four hashes/J-A core and reject legacy or hash drift before package reads. | `STOP=stage1_5j_b_upstream_authority_mismatch` |
| `INV-JB-RB-02` | Rule 17 v2 closure evidence | Tasks 0-2 parse exact canonical evidence plus sidecar and verify profile/version/verifier/status/RC literals; Task 6 independently invokes verifier CLI. | `STOP=stage1_5j_b_upstream_governance_evidence_invalid` |
| `INV-JB-RB-03` | J-A summary projection | Tasks 1-2 assert all nine literals `335/131/125/120/11/281/280/1/5`, state and decision before ZIP reads. | `STOP=stage1_5j_b_upstream_projection_mismatch` |
| `INV-JB-RB-04` | Persisted J-B `j_a_input` | Tasks 3-4 produce and strict-load exactly 16 rebound keys; each single key/value mutation reaches the J-B loader. | `STOP=stage1_5j_b_j_a_input_mismatch` |
| `INV-JB-RB-05` | Exploratory data reducer | Tasks 1-3 retain the frozen 131/281/843/393 ledgers and three fixed horizons without changing anchor/order/gap rules. | structural/reduction STOP; never omit a gap row |
| `INV-JB-RB-06` | Authority and safety boundary | Tasks 0, 4, 6-8 prove false flags, no network/import layering, no production run, scope/index cleanliness, and actual scanner RC. | `STOP=stage1_5j_b_scope_or_authority_violation` |

---

## 3. Task 0: Freeze Authority, Baseline, Scope, And Canonical Evidence

**Intent:** Create no source, output receipt, or network artifact before proving the exact approved Plan, Design chain, current baseline, and immutable inputs.

**Files:**

- Create only after every preflight check passes: `.git/plan-execution/stage1_5j_b/<APPROVED_PLAN_SHA256>/{base_sha,implementation_authorization.txt,implementation_authorization.sha256,execution_authority.json,execution_authority.sha256,evidence/**}`.
- Read-only: both J-B Design files, J-A replacement root, v2 closure evidence and sidecar, v2 verifier source, J-A core, `configs/base.py`.

### Step 1: Parse and validate the user approval before any write

The executor parses only the literal two-line user approval. It recomputes this Plan SHA and requires equality with `<APPROVED_PLAN_SHA256>`, then verifies both Design hashes and `HEAD`.

```bash
set -euo pipefail
test "$(git rev-parse HEAD)" = "d15ca4e0da75a61553ca1d5983249d85a4512bb5"
git diff --cached --quiet
shasum -a 256 \
  docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md \
  docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md \
  docs/plans/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-implementation-plan_CN.md
```

Expected: the first two values equal §0 and Plan SHA equals the approval. Any mismatch, dirty index, or changed HEAD is `STOP=approved_authority_mismatch`; do not rebaseline, edit an approval, or create evidence.

### Step 2: Create an immutable ownership ledger in memory

Capture `git status --short --untracked-files=all`, `git diff --name-only`, and `git diff --cached --name-only`. Record path/type/byte-count/SHA-256 for every pre-existing dirty or untracked path and all §1.2 inputs. The two J-B Design files must match their frozen bytes; later task work may not change them. Record recursively sorted root inventory and all four top-level hashes for the replacement receipt.

Expected: a complete pre-execution ledger. Any later changed pre-existing byte, modified root, unexpected staging/final J-B root, or undeclared path is `STOP=stage1_5j_b_scope_or_authority_violation`.

### Step 3: Prove upstream source topology before implementation

Inspect all callers/importers of J-A public loader and the verifier. J-B source may import only the public J-A loader; it may not import a script, test-only helper, private J-A function, or verifier implementation. The independent verifier is CLI-only evidence for Task 6/audit.

```bash
rg -n "load_verified_stage1_5j_a_historical_archive_coverage_root|verify_artifact_schema" \
  src scripts tests
```

Expected: no pre-existing J-B consumer path. If a hidden J-B producer/consumer is discovered, stop `BLOCKED_SCOPE_DRIFT`; do not create competing output semantics.

### Step 4: Validate canonical J-A admission evidence without writing

Run public J-A loader and exact independent verifier on the immutable root. Save only their stdout/stderr/RC and before/after root inventory in memory until Step 5 succeeds.

```bash
python3 - <<'PY'
from pathlib import Path
from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
    load_verified_stage1_5j_a_historical_archive_coverage_root,
)
root = Path("data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z")
summary = load_verified_stage1_5j_a_historical_archive_coverage_root(root)
assert summary["run_id"] == root.name
print(summary["decision"])
PY
python3 scripts/governance/verify_artifact_schema.py \
  --profile stage1_5j_a_receipt_v2 \
  --artifact-root data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
```

Expected: both RC `0`. A failure is `STOP=stage1_5j_b_upstream_governance_evidence_invalid` or `STOP=stage1_5j_b_upstream_authority_mismatch`; never replace it with an in-process verifier clone.

### Step 5: Create the authority directory exactly once

Only after Steps 1-4 pass, require the authority directory absent, write the exact user approval, canonical `execution_authority.json`, sidecars, `base_sha`, and the immutable ledger. The execution authority binds: Plan/Design paths and SHA, baseline SHA, replacement root/run/four hashes, J-A core path/SHA, v2 evidence path/SHA, profile/version, verifier path/SHA, and the allowed path list in §1.1. It explicitly sets every J-B permission and `RISK_LIVE_TRADING_ENABLED` expectation to `false`.

Expected: each sidecar is `<sha256><two spaces><filename>\n`; the directory has no authorization for network or receipt generation. Existing directory, malformed record, or sidecar mismatch is `STOP=approved_authority_mismatch`.

---

## 4. Task 1: RED Tests For Rebound Admission And Frozen Measurement

**Files:**

- Create: `tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py`
- Read-only positive source: full replacement J-A root and J-A public loader.

### Step 1: Add canonical-root admission tests

Write tests that begin by public strict-loading the real replacement root, then derive all J-B positive inputs from returned summary/manifest bytes. Assert all nine §2.1 values, J-A state/decision, exact root/run/four hashes, J-A core identity, v2 evidence canonical hash/sidecar/profile/version/verifier SHA/status/positive flag. Do not handwrite an upstream receipt dictionary, raw CSV, parent record, or authority packet.

Run:

```bash
pytest -q tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py -k upstream_admission
```

Expected before implementation: RED due to missing J-B module/API, not a skipped test.

### Step 2: Add single-mutation upstream negative tests

Using a disposable copy or reflink of the root plus canonical sidecars, mutate exactly one declared input per test: old RUN_ID; one top-level hash; evidence profile/version/verifier SHA/status/positive flag/sidecar; and each projection value `120 -> 118`, `11 -> 13`, `280 -> 278`, `1 -> 3`, `5 -> 0`. Rebuild only the immediately necessary manifest entry when the named semantic gate requires it. Each test must reach and assert the exact STOP in §2.

Expected before implementation: RED. The real root inventory/hashes must be identical before and after each test.

### Step 3: Add frozen pure measurement tests

Use local rows only for internal pure functions, never as upstream fixture substitutes. Cover physical ordering across date boundaries, equal timestamp last-physical-row selection, finite positive `Decimal` parsing, fixed-point serialization, anchor-delay gap, required-date gap, missing-horizon-trade gap, three-horizon arithmetic, equal-child parent median, nearest-rank distribution, and zero absolute-return denominator. Each expected value derives directly from parent Design §3.

Expected before implementation: RED; tests assert no `float`, no raw archive retention, and no PnL/trading fields.

---

## 5. Task 2: Implement Read-Only J-A Admission And Streaming Reducer

**Files:**

- Create: `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py`
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py`

### Step 1: Add only the nine frozen J-B config constants

Add exactly the parent Design §3.1 constants to `configs/base.py`: `MAX_ANCHOR_DELAY_MS=300_000`, horizons `(300_000, 3_600_000, 14_400_000)`, lookback `60_000`, J-A-equivalent ZIP/CSV/ratio caps, `STREAM_CHUNK_BYTES=65_536`, root cap `67_108_864`, and minimum-free-bytes `1_073_741_824`. No existing threshold changes.

Run:

```bash
pytest -q tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py -k config
```

Expected: GREEN; `RISK_LIVE_TRADING_ENABLED is False` remains asserted.

### Step 2: Implement the exact upstream admission gate

Define literal J-B constants for every §1.1/§1.2 and §2.1 value. Implement one private admission function that, in the exact §4 order, verifies containment/no symlinks, canonical v2 evidence/sidecar bytes, `profile_id=stage1_5j_a_receipt_v2`, contract version `2`, verifier path/SHA, `evidence_status=receipt_closure_audited_positive`, `governance_rule17_v2_positive is True`, J-A core disk SHA, public J-A strict loader result, four top-level hashes, J-A state/decision, and all nine projections. It returns only strict-loaded summary plus immutable input identity. It must not import `scripts.governance`, invoke network APIs, use `.get(..., default)`, or accept caller-supplied project roots in the public path.

Run the Task 1 admission/negative tests. Expected: GREEN with the exact three STOP families in §2.

### Step 3: Implement bounded stream and descriptive reducer

Implement exact header validation; bounded `ZipFile.open()` plus `TextIOWrapper`/`csv` iteration; ZIP member/size/ratio caps; `Decimal` finite-positive conversion; global physical order; anchor/required-date/target-row selection; child and parent outcomes; distributions; canonical decimal strings. Retain only per-child anchor/selectors/extrema/counts. Prohibit `ZipFile.read`, `extract`, whole-file CSV materialization, raw trade retention, or concurrent package reads.

Run:

```bash
pytest -q tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py -k 'measurement or stream or reducer'
```

Expected: GREEN. Any source/root mismatch fails before opening a ZIP; any unavailable J-A package remains an explicit evidence gap, never a network request.

---

## 6. Task 3: RED Then Implement J-B Receipt, Strict Loader, And Recovery

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py`

### Step 1: Write receipt/loader RED tests from canonical upstream input

Derive one temporary J-B test receipt only through the Task 2 production reducer with the full strict-loaded replacement root. Assert `j_a_input` is exactly this 16-key set, with no missing or extra key:

```text
j_a_core_path,
j_a_core_sha256,
j_a_governance_closure_evidence_relative_path,
j_a_governance_closure_evidence_sha256,
j_a_governance_evidence_status,
j_a_governance_profile_contract_version,
j_a_governance_profile_id,
j_a_governance_rule17_v2_positive,
j_a_governance_verifier_relative_path,
j_a_governance_verifier_sha256,
j_a_journal_sha256,
j_a_manifest_sha256,
j_a_root_relative_path,
j_a_review_sha256,
j_a_run_id,
j_a_summary_sha256
```

Assert every persisted literal, 131/281/843/393 ledgers, coverage counts `120/11/131`, authority/research flags false, canonical summary/manifest/review bytes, and byte-for-byte review re-rendering. Do not use a handcrafted summary as a positive fixture.

Add isolated mutation tests for each persisted `j_a_input` key/value, an extra final-root file, a symlink, missing manifest entry, changed rendered review, reducer count mismatch, and each collision state (`staging_only`, `final_only`, `final_plus_staging`).

Expected before implementation: RED.

### Step 2: Implement exact schema and strict loader

Implement canonical JSON, deterministic Markdown renderer, manifest, exact-key validators, receipt tree classifier, manifest/hash checks, loader recomputation/re-rendering, and the §4.4 fail order. The loader must independently run the upstream admission gate before accepting persisted `j_a_input`; it may share pure exact validators but must not trust producer output.

`analysis_state=exploratory_response_described` only if all **120** J-A complete parents are complete at every horizon. Otherwise emit the frozen evidence-gap state/decision. Keep all 11 J-A parent gaps explicit and do not convert a coverage gap into a negative outcome.

### Step 3: Implement atomic local publication only behind receipt authority

Implement a public zero-injection production entry that first verifies an exact future offline `receipt_generation_authorization` bundle, then uses one `fcntl.flock(LOCK_EX)` across collision check, staging creation, file fsync, directory fsync, atomic rename, and parent fsync. No authorization exists in this Plan; therefore the public producer test must prove it fails closed before output creation.

Private test helpers may write only beneath `tmp_path` and only from the canonical strict-loaded replacement root. They must never write under `data/`.

Run:

```bash
pytest -q tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py
```

Expected: GREEN. All temporary roots are cleaned and source root hashes remain unchanged.

---

## 7. Task 4: CLI, Authority Boundary, And Production Wiring Proof

**Files:**

- Create: `scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py`
- Create: `tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py`
- Modify only if required by Task 0 scope: J-B core/test paths already allowed above.

### Step 1: Write CLI RED tests

Require strict `argparse` literals for approved J-B Design/Plan path/SHA and a run ID. Import the immutable J-B core constants; do not duplicate them. Test wrong design/plan/run ID, unknown argument, and absent authorization. AST-check that CLI imports no socket/network client and only delegates to the public production core entry.

Expected before CLI implementation: RED.

### Step 2: Implement the minimal CLI

Implement parser validation and delegation only. It performs no direct file walking, raw ZIP read, network action, output write, or authorization construction. The core remains the single receipt-authority boundary.

Run:

```bash
pytest -q tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py
```

Expected: GREEN. Public CLI run without an exact future receipt authorization is a deterministic STOP and leaves no J-B root.

### Step 3: Production wiring and crash/recovery tests

In temporary output parents only, prove one shared parent `flock` rejects concurrent writers; simulated failures before rename leave only `staging_only`; failures after rename leave `final_only`; restart rejects every non-`absent` state; and no overwrite/resume/cleanup occurs. Confirm fsync ordering through injected test seams, not by weakening public code with path injection.

Expected: all states and failures have the parent Design's exact collision semantics.

---

## 8. Task 5: End-To-End Canonical Fixture, Independent Verifier, And Safety Gates

**Files:** read-only verification of all allowed paths; evidence only under `.git/plan-execution/stage1_5j_b/<APPROVED_PLAN_SHA256>/evidence/`.

### Step 1: Run canonical upstream-derived integration test

Run the full J-B research test suite that begins with the real replacement root, public J-A strict loader, v2 evidence verification, and a temporary J-B receipt. Record root hashes before/after. Its positive assertion is structural and descriptive only; it must not assert a positive/negative market outcome, rank an opportunity, or infer Alpha.

```bash
pytest -q tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py
```

Expected: `rc=0`, replacement root unchanged, temporary output cleaned, and no `data/external_signal_shadow/stage1_5j_b/` final root exists.

### Step 2: Independently invoke the Rule 17 verifier

This is not a J-B source import. Run and record the actual process RC, profile/version, verifier SHA, replacement-root identity, and four root artifact hashes:

```bash
python3 scripts/governance/verify_artifact_schema.py \
  --profile stage1_5j_a_receipt_v2 \
  --artifact-root data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z
```

Expected: `rc=0`. Any failure is `STOP=stage1_5j_b_upstream_governance_evidence_invalid`; do not make J-B accept the root by changing its own checks.

### Step 3: Static safety, scope, and index gates

```bash
ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py \
  scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py
git diff --check
git diff --cached --check
python3 .agent/tools/anti_shortcut_scan.py --base-sha d15ca4e0da75a61553ca1d5983249d85a4512bb5
scanner_rc=$?
printf 'scanner_rc=%s\n' "$scanner_rc"
test "$scanner_rc" -eq 0
python3 - <<'PY'
from configs.base import RISK_LIVE_TRADING_ENABLED
assert RISK_LIVE_TRADING_ENABLED is False
PY
git diff --cached --quiet
```

Expected: every command RC `0`, including actual `scanner_rc=0`. Rehash all Task 0 pre-existing paths and assert exact equality; only §1.1 source/test/config/evidence paths may be task-induced. An index change, unexpected path, root mutation, network import/call, production J-B root, or nonzero scanner is `STOP=stage1_5j_b_scope_or_authority_violation`.

---

## 9. Task 6: Independent Review And Completion Audit Routing

### Step 1: Independent code review

Provide the reviewer the approved Design/Delta/Plan SHA, Task 0 authority ledger, allowed-path diff, all target test output, independent v2 verifier transcript/RC/SHA, replacement-root before/after hashes, canonical-fixture provenance, mutation results, scope/index proof, and scanner actual RC. Reviewer must confirm each invariant in §2 and reject an executor-provided summary as evidence.

Open P0/P1 is `STOP=stage1_5j_b_code_review_open_findings` and routes to remediation. No one may create a J-B authorization or output root while review is open.

### Step 2: Fresh Completion Audit

Only after closed code review, invoke `.agent/skills/audit-plan-completion/SKILL.md`. The auditor independently verifies Plan/Design bytes, baseline and ownership ledger, J-A strict-loader result, v2 verifier command/actual RC/source SHA, exact 16-key `j_a_input`, `120/11/280/1/5` projection, canonical fixture provenance, mutation gate reachability, atomic recovery, scope/index, and scanner actual RC.

Strongest permitted result is `COMPLETE_PRE_RECEIPT_AUTHORIZATION`. It does not authorize commit, push, deployment, SSH, network, receipt generation, J-B consumption, Alpha/replay/signal/paper/live trading, or execution.

---

## 10. Stop And Escalation Matrix

| Condition | Required route |
| --- | --- |
| Plan/Design/baseline/approval/immutable input mismatch | `BLOCKED_SPEC_DRIFT`; return to Design/authority review. |
| Hidden J-B topology, needed non-whitelisted file, or changed pre-existing root/document | `BLOCKED_SCOPE_DRIFT`; preserve ledger and request a new Plan. |
| Code violates a frozen contract inside allowed paths | `BLOCKED_IMPLEMENTATION_DEFECT`; repair only through RED evidence. |
| Real replacement root write, network access, J-B output under `data/`, receipt authorization generation, or a non-false permission | stop immediately as safety/scope violation. |
| Independent verifier unavailable/nonzero or its bytes differ from the v2 evidence tuple | `STOP=stage1_5j_b_upstream_governance_evidence_invalid`; do not emulate it in J-B source. |

## 11. Explicit Non-Authorization

This Plan is documentation until independently reviewed and explicitly approved by the user. A future implementation approval may permit only the bounded local source/test/config/evidence work above. It cannot authorize commit, push, deployment, SSH, network, receipt generation, downstream J-B consumption, Alpha claims, replay, signal generation, paper trading, live trading, or execution.
