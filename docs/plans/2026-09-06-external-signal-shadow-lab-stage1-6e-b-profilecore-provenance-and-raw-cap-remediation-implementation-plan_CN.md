# Stage 1.6E-B ProfileCore Provenance And Raw-Cap Remediation Implementation Plan

> **For implementation agents:** Execute only after independent Plan review returns `Approve`, the user explicitly authorizes implementation, and an external approval record supplies the exact SHA-256 of these Plan bytes. Execute with `.agent/workflows/execute-approved-plan.md`, task by task. This Plan authorizes neither deployment nor any runtime session.

**Goal:** Close only the two residual Stage 1.6E-B implementation defects: bind every derived Event ProfileCore to the verified E-A profile-attestation hash at construction, and make the E-B client enforce the Design-required inner `max_raw_response_bytes` without a default.

**Architecture:** The Parent Design already specifies both behaviors. The model remains the single producer of Event ProfileCore, the public client remains the single raw-body bound enforcer, and the observer becomes a direct consumer with no downstream attestation or capacity patch. No serialized schema, network behavior, capacity policy, or permission changes.

**Tech stack:** Existing Python standard-library implementation, existing E-A canonical profile-attestation helper, `pytest`, `ruff`, existing anti-shortcut scanner.

## Governance And Bound Authority

- Date: 2026-09-06
- Plan status: `draft_for_review`
- Parent E-B Design SHA-256: `752aecff8735f22513483e6bf65ae991386f46ff2ae953da44cd1fe9c5898583`
- Parent E-B Plan SHA-256: `279f729645c9e3691797a92059cab3d212e7b62c0ffbdb49a49947bb712b4da6`
- Approved completion-remediation Delta Design SHA-256: `145bbb7d84e4d7ae4fc9e901b293b8520b3b825d1377f96d02bff8b8dc67ee44`
- Parent completion-remediation Plan SHA-256: `acb2e5b88d68b633f1b0ad81d2d62d687d07ee4dd0f6c2a6cbed8ed1552dc479`
- Completion-audit finding input: `docs/reviews/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-completion-audit_CN.md`
- `implementation_allowed=false`
- `deployment_allowed=false`
- `runtime_action_allowed=false`

Before execution, an external approval record must provide `EXPECTED_APPROVED_PROFILECORE_REMEDIATION_PLAN_SHA256`. The executor computes this file's exact-byte SHA-256 and requires equality; otherwise `STOP=profilecore_remediation_plan_bytes_not_authorized`. This Plan must never fill in or infer that value itself.

This is an implementation-scope amendment, not a Design change. Parent Design Section 9.2 already requires the exact `base_e_a_profile_attestation_sha256` and requires the transformed inner `http_profile_core.max_raw_response_bytes`. Delta `INV-R09` already requires the derived profile to bind the verified E-A attestation. The implementation must not introduce an `event_max_raw_response_bytes` key inside `http_profile_core`; that would violate the frozen ProfileCore grammar.

## Mandatory Governance Gates

Before RED in Tasks 1-3, execute `execute-approved-plan` Step 3.0 against the actual upstream E-A helper, E-B model/client signatures, serializers, verified-bundle factory, and every direct caller. If reality differs, do not add a fallback, copied authority, alias, or local adapter. Classify exactly once under `AGENTS.md` L1.16: `BLOCKED_IMPLEMENTATION_DEFECT`, `BLOCKED_SCOPE_DRIFT`, or `BLOCKED_SPEC_DRIFT`.

After each of Tasks 1-3 reaches GREEN, run the anti-shortcut scanner against `BASE_SHA`: zero `ERROR` is mandatory and every `WARNING` must be recorded in an external Scanner Disposition Ledger. A warning is not implicitly accepted because the scanner exits zero.

Final completion uses a Blind-First handover: the executor supplies an independent read-only `audit-plan-completion` auditor only the authority paths/SHAs, `BASE_SHA`, baseline provenance, Allowed Change Scope, and commands. The executor must not self-audit, and the audited worktree must not change after handover.

## Invariants, Entry Points, And STOP Conditions

| Invariant | Production owner | Required implementation evidence | Fail-closed STOP |
|---|---|---|---|
| Parent Design 9.2 exact derived ProfileCore | `derive_event_profile_core()` | exact verified E-A attestation hash is an explicit constructor input and is present in the signed output | `missing_or_invalid_base_e_a_profile_attestation_sha256` |
| Parent Design 9.2 raw-body transform | `derive_event_profile_core()` | copied inner ProfileCore has exact E-B `max_raw_response_bytes` of 262144 or 32768 | `profile_core_raw_response_bound_invalid` |
| Parent Design 10 network bound | `Stage16EBPublicClient.fetch()` | raw reader strictly requires inner `max_raw_response_bytes` and rejects missing/non-positive/non-integer values before opening a request | `profile_core_raw_response_bound_invalid` |
| Delta `INV-R09` trusted provenance | event-root producer in `Stage16EBSupervisor` | verified E-A map value flows directly to model constructor; no `dataclasses.replace` post-processing | `missing_e_a_profile_attestation` |
| Parent/Delta safety | all changed paths | all permissions remain false; no private/order/execution import or runtime artifact | `safety_invariant_violation` |

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_models.py`
- `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_client.py`
- `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py`
- `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py`
- `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py`

Allowed documentation paths:
- `none`

Allowed generated/runtime artifacts:
- `pytest` `tmp_path` only; never committed.
- `none` for `data/external_signal_shadow/**`; this Plan does not authorize a runtime root, source read, or network request.

Affected but unchanged:
- `configs/base.py`
  - Existing E-B raw-cap assignments remain exact; AST and values must not change.
- `scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py`
  - Existing runner constructs the same public client and remains API-compatible; runner regression passes.
- `src/research/external_signal_shadow/stage1_6e_a_market_data_capability_models.py`
  - Its existing `PROFILE_CORES` and `compute_profile_attestation_sha256()` are read-only canonical upstream authority; E-A regression passes.
- `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_{source,storage}.py`
  - No source-linkage, storage, environment, C5/C6/C8/C9, or artifact grammar change; focused remediation regressions pass.
- All Parent/Delta/previous-Plan documents listed above
  - Their exact SHA-256 values must remain equal to the bound values.

Forbidden:
- Any mutation outside the paths above.
- Parent/Delta/previous-Plan mutations, config/threshold changes, E-A or 1.6D changes, schema version changes, migrations, compatibility aliases, fallback defaults, adapter layers, queue/retry/concurrency changes, or broad refactoring.
- Private/authenticated/account/order API, trade signal, alpha/PnL/cost claim, paper/live trading, execution engine, VPS synchronization, runtime root creation, or real network testing.
- `ruff check --fix`, any repository-wide formatter, `git clean`, `git reset --hard`, destructive checkout, or modifications to pre-existing dirty/untracked files outside this whitelist.

## Task 0: Authority And Baseline Gate

**Invariants:** all.

**Files:** none.

- [ ] Record `BASE_SHA=$(git rev-parse HEAD)` and `git status --short --untracked-files=all`; preserve every pre-existing dirty/untracked file and record SHA-256 provenance before editing.
- [ ] Require equality of the four bound Parent/Delta/Plan SHA-256 values above and `EXPECTED_APPROVED_PROFILECORE_REMEDIATION_PLAN_SHA256` before any code or test mutation.
- [ ] Inspect `derive_event_profile_core`, `Stage16EBPublicClient.fetch`, the event-root producer, all direct callers, and the E-A canonical `compute_profile_attestation_sha256` helper. Confirm `initialize_event_root` is absent, as required by the already-closed prior remediation; its absence is expected evidence, not an exception. `graphify` output is advisory because its `.fetch()` symbol is ambiguous; direct `rg` caller results are authoritative for this Plan.
- [ ] Confirm the existing E-B Design field is inner `max_raw_response_bytes`, not a new inner `event_max_raw_response_bytes` alias.
- [ ] Record the whole Git index snapshot SHA-256 from `git ls-files -s -z`, then record `SCANNER_SHA256`, exact scanner command, scanner exit code, and normalized baseline warning identities (`rule`, `path`, and source expression) under `$PROFILECORE_REMEDIATION_BASELINE_DIR`. This Plan has no staging authority: any index change is a STOP. The baseline must show the raw-cap fallback warning before this remediation; it is not a permissible final warning.

**Verification:**

```bash
BASE_SHA="$(git rev-parse HEAD)"
export PROFILECORE_REMEDIATION_BASELINE_DIR="$(mktemp -d)"
git status --short --untracked-files=all
python3 - "$PROFILECORE_REMEDIATION_BASELINE_DIR" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

out = Path(sys.argv[1])
raw = subprocess.check_output(
    ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
    text=False,
)
baseline = {}
for record in raw.split(b"\0"):
    if not record:
        continue
    if b"R" in record[:2] or b"C" in record[:2]:
        raise SystemExit("STOP=baseline_rename_or_copy_not_supported")
    path = record[3:].decode("utf-8")
    p = Path(path)
    baseline[path] = {
        "status": record[:2].decode("ascii"),
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None,
    }
(out / "dirty-baseline.json").write_text(
    json.dumps(baseline, sort_keys=True, separators=(",", ":")), encoding="utf-8"
)
print({"baseline_dirty_path_count": len(baseline)})
PY
git ls-files -s -z | shasum -a 256 | awk '{print $1}' \
  > "$PROFILECORE_REMEDIATION_BASELINE_DIR/index.sha256"
shasum -a 256 \
  docs/designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md \
  docs/plans/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-implementation-plan_CN.md \
  docs/designs/2026-09-04-external-signal-shadow-lab-stage1-6e-b-completion-remediation-delta-design_CN.md \
  docs/plans/2026-09-05-external-signal-shadow-lab-stage1-6e-b-completion-remediation-implementation-plan_CN.md \
  docs/plans/2026-09-06-external-signal-shadow-lab-stage1-6e-b-profilecore-provenance-and-raw-cap-remediation-implementation-plan_CN.md
assert_sha() {
  test "$(shasum -a 256 "$2" | awk '{print $1}')" = "$1" || {
    echo "STOP=authority_sha_mismatch:$2" >&2
    exit 1
  }
}
assert_sha 752aecff8735f22513483e6bf65ae991386f46ff2ae953da44cd1fe9c5898583 \
  docs/designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md
assert_sha 279f729645c9e3691797a92059cab3d212e7b62c0ffbdb49a49947bb712b4da6 \
  docs/plans/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-implementation-plan_CN.md
assert_sha 145bbb7d84e4d7ae4fc9e901b293b8520b3b825d1377f96d02bff8b8dc67ee44 \
  docs/designs/2026-09-04-external-signal-shadow-lab-stage1-6e-b-completion-remediation-delta-design_CN.md
assert_sha acb2e5b88d68b633f1b0ad81d2d62d687d07ee4dd0f6c2a6cbed8ed1552dc479 \
  docs/plans/2026-09-05-external-signal-shadow-lab-stage1-6e-b-completion-remediation-implementation-plan_CN.md
: "${EXPECTED_APPROVED_PROFILECORE_REMEDIATION_PLAN_SHA256:?STOP=profilecore_remediation_plan_bytes_not_authorized}"
assert_sha "$EXPECTED_APPROVED_PROFILECORE_REMEDIATION_PLAN_SHA256" \
  docs/plans/2026-09-06-external-signal-shadow-lab-stage1-6e-b-profilecore-provenance-and-raw-cap-remediation-implementation-plan_CN.md
rg -n 'derive_event_profile_core\(|client\.fetch\(' src scripts tests
if rg -n 'def initialize_event_root|initialize_event_root\(' \
  src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py; then
  echo 'STOP=legacy_initialize_event_root_still_present' >&2
  exit 1
fi
SCANNER_SHA256="$(shasum -a 256 .agent/tools/anti_shortcut_scan.py | awk '{print $1}')"
printf '%s\n' "$SCANNER_SHA256" > "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner.sha256"
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" \
  > "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-baseline.txt" 2>&1; then
  SCANNER_BASELINE_RC=0
else
  SCANNER_BASELINE_RC=$?
fi
cat "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-baseline.txt"
printf '%s\n' "$SCANNER_BASELINE_RC" \
  > "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-baseline.exitcode"
test "$SCANNER_BASELINE_RC" -eq 0 || {
  echo 'STOP=scanner_baseline_nonzero' >&2
  exit 1
}
python3 - "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-baseline.txt" \
  "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-warning-identities.json" <<'PY'
import json
import re
import sys
from pathlib import Path

lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
identities = sorted(
    re.sub(r":\d+:\d+ - ", ":<location> - ", line)
    for line in lines
    if line.startswith("[WARN]")
)
Path(sys.argv[2]).write_text(json.dumps(identities), encoding="utf-8")
print({"baseline_warning_count": len(identities), "warnings": identities})
assert any("event_max_raw_response_bytes" in line for line in identities), (
    "STOP=raw_cap_fallback_not_in_baseline"
)
PY
```

**Expected:** the four parent hashes equal their bound values; this Plan equals the external approval value; `initialize_event_root` is absent; exactly one production `client.fetch` call and one production model-constructor call exist in E-B; index snapshot, scanner version/zero exit/output, and all baseline warnings are preserved externally; no runtime action occurs.

**STOP:** any authority hash mismatch, unknown caller, required file outside whitelist, Design field mismatch, or pre-existing worktree change is unrecorded.

## Task 1: Make Event ProfileCore The Single Provenance And Cap Producer

**Invariants:** Parent Design 9.2; Delta `INV-R09`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_models.py:682-748`
- Modify: `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py:182-218`

**Interface:**

```python
def derive_event_profile_core(
    *,
    event_id: str,
    source_article_id: str,
    source_detail_revision_id: str,
    canonical_symbol: str,
    base_e_a_manifest_id: str,
    base_e_a_profile_id: str,
    base_e_a_profile_attestation_sha256: str,
    base_e_a_profile_core: dict[str, Any],
) -> EventProfileCore: ...
```

The caller supplies the value only after E-A bundle verification. The function calls the existing `validate_sha256()` on both manifest and attestation inputs, copies the supplied ProfileCore, applies only Parent Design transforms, assigns `http_core["max_raw_response_bytes"] = event_max_bytes`, and calculates `profile_attestation_sha256` from the exact output object excluding only that field. It must not calculate an attestation hash from `base_e_a_profile_core`.

- [ ] **Step 1: Add RED model assertions.** Update the four-profile exact-transform test to derive its positive attestation input through the canonical upstream `compute_profile_attestation_sha256(E_A_PROFILE_CORES[base_pid])`; assert the output's `base_e_a_profile_attestation_sha256` equals that supplied value, the output inner `max_raw_response_bytes` equals its outer `event_max_raw_response_bytes`, and all other unchanged E-A keys retain their original values. Add one invalid attestation test asserting `ValueError("sha256_invalid")`.

  Add a separate pure-model dependency mutation test, not a cross-boundary positive fixture: invoke `derive_event_profile_core()` twice with the same canonical E-A ProfileCore and all other inputs equal but with two distinct syntactically valid 64-hex sentinel values `A` and `B`, each deliberately different from `compute_profile_attestation_sha256(base_core)`. Assert the corresponding output base-attestation fields equal `A` and `B` exactly, and the two canonical output objects and `profile_attestation_sha256` values differ. This test proves supplied-input dataflow; it must not claim either sentinel is an accepted E-A bundle attestation.
- [ ] **Step 2: Run the narrow RED test.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py::test_derived_profile_cores_exact_transforms
```

**Expected:** failure because the constructor lacks the attestation argument and the inner E-B raw cap remains the E-A two-MiB value.

- [ ] **Step 3: Implement the minimal producer correction.** Add exactly the required input; validate it; use it for `base_e_a_profile_attestation_sha256`; replace the inner copied E-A `max_raw_response_bytes` with the already selected E-B bound. Do not add a dataclass field, serializer key, configuration value, default, or new helper.
- [ ] **Step 4: Run model tests.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py
```

**Expected:** all model tests pass; the positive fixture derives the attestation only through the canonical E-A helper, while the isolated dependency mutation proves the producer does not substitute a locally recomputed core hash.

**STOP:** a field/schema change, a supplied attestation not bound in the signed result, noncanonical E-A fixture, or need to change E-A source.

## Task 2: Enforce The Approved Inner Raw-Cap At The Client Boundary

**Invariants:** Parent Design 9.2 and 10; Delta `INV-R09`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_client.py:388-395`
- Modify: `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py:157-256`

**Interface:** `Stage16EBPublicClient.fetch(http_profile_core)` consumes the exact inner ProfileCore generated in Task 1. It must not consume outer Event ProfileCore fields or a compatibility alias.

- [ ] **Step 1: Add RED client tests.** Build each client core by calling the Task-1 model constructor with the canonical E-A attestation helper, then pass only `.http_profile_core` to `fetch()`.

  Use `b"{}"` plus ASCII whitespace as raw-reader-only padding and prove the exact differential matrix without schema adapters: a 32768-byte body is `response_verified` under a 32768-byte premium ProfileCore and a 32769-byte body is `raw_size_exceeded`; a 262144-byte body is `response_verified` under a 262144-byte depth ProfileCore and a 262145-byte body is `raw_size_exceeded`. The two accepted cases must retain the exact returned raw bytes. This rules out a hard-coded 32768-byte reader.

  Delete `max_raw_response_bytes`, then replace it with `True`, `"32768"`, `0`, and `-1`; each case must raise `ValueError("profile_core_raw_response_bound_invalid")` before the mock opener receives a request. There is no raw `KeyError` contract.
- [ ] **Step 2: Run the narrow RED test.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py
```

**Expected:** failure because client tests currently supply a non-Design alias, `fetch()` silently defaults when the canonical key is absent, and no differential 32768/262144 bound proof exists.

- [ ] **Step 3: Implement the strict boundary check.** Read exactly `http_profile_core["max_raw_response_bytes"]`; translate only a missing key to `ValueError("profile_core_raw_response_bound_invalid")`, and require `type(value) is int and value > 0` with that same error otherwise. Use that exact `value` as the raw reader limit. Keep every existing request, redirect, content-encoding, response-validation, and raw-read behavior unchanged.
- [ ] **Step 4: Run client tests.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py
```

**Expected:** all client tests pass; a direct client caller cannot fall back to 262144 bytes, dispatch with an invalid/missing cap, or replace an approved 262144-byte limit with a hard-coded 32768-byte limit.

**STOP:** any attempted new inner alias, numeric coercion/default, client transport expansion, or change to E-A client code.

## Task 3: Remove Observer-Level Workarounds And Prove End-To-End Binding

**Invariants:** Parent Design 9.2; Delta `INV-R09`; all safety boundaries.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py:587-614,1383-1387`
- Modify: `tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py:480-650`

**Interface:** the verified `e_a_profile_attestation_sha256_by_id[base_pid]` is supplied directly to `derive_event_profile_core()`. `Stage16EBEventObserver.step_slot()` passes the persisted derived `profile.http_profile_core` directly to the client.

- [ ] **Step 1: Add RED integration assertions.** Using the existing verified E-A bundle/root test factory, inspect each persisted `profile_attestations/<symbol>.<profile>.json`: its base attestation equals the verified E-A gate map entry, its inner and outer cap are equal, and its profile attestation hash equals canonical bytes of the object with that field omitted. Retain the existing 32769-byte premium observation test but require its result through the direct inner ProfileCore path.
- [ ] **Step 2: Run the narrow RED test.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py
```

**Expected:** failure because the observer currently repairs provenance and cap after model construction rather than consuming the model output directly.

- [ ] **Step 3: Implement the direct consumer path.** Pass the verified map value into the model constructor. Delete only the `profile_data`/`dataclasses.replace` provenance repair. Replace the copied-core/event-alias client call with `self.client.fetch(profile.http_profile_core)`. Do not alter event-root ordering, receipts, contracts, slots, network policy, locks, C5/C6/C8/C9 recovery, or terminal behavior.
- [ ] **Step 4: Run observer tests.**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py
```

**Expected:** all observer tests pass; persisted artifacts prove exact verified E-A provenance and the client receives only the Design-correct inner ProfileCore.

**STOP:** test fixture cannot obtain E-A authority from its existing verified-bundle factory, any need for a static E-A fallback, or any change to event artifact grammar.

## Task 4: Scope, Safety, And Independent Completion Audit Gate

**Invariants:** all.

**Files:** none.

- [ ] Before editing in Task 0, save a NUL-safe dirty-worktree baseline under `$PROFILECORE_REMEDIATION_BASELINE_DIR`: every initially dirty/untracked path, its status record, and its SHA-256 or an explicit `missing` marker. Also save the whole Git index snapshot hash. At final verification, compare both baselines with final state. An initially dirty path outside this Plan's implementation/verification whitelist must still exist with identical bytes and porcelain status; the Git index hash must be exactly unchanged. Every new path or any byte change after the baseline must be in the exact implementation or verification whitelist and must be attributed to Tasks 1-3.
- [ ] Recompute the four bound Parent/Delta/previous-Plan SHA-256 values and this Plan's externally authorized SHA-256. A changed authority byte is a STOP, not an attributed Plan change.
- [ ] Run the three changed test modules, then the Parent remediation focused suite, required upstream E-A regression, runner regression, formatting, diff, mechanical scope proof, scanner, and safety checks.
- [ ] Require the scanner program SHA-256 to equal the Task-0 value. Require zero final `ERROR`, no raw-cap fallback warning, no new normalized warning identity relative to Task 0, and an external disposition for every remaining unchanged baseline warning. The prior raw-cap fallback warning must be absent; the two known warning expressions may remain only if they were present in the saved Task-0 baseline.
- [ ] Provide a factual, read-only handover to an independent `audit-plan-completion` auditor. The packet must contain only authority paths/SHAs, `BASE_SHA`, pre-existing dirty baseline, final scope-proof output, scanner baseline/final output, Allowed Change Scope, and commands. Do not change the audited worktree after handover. `incomplete` or `blocked` returns to a new remediation flow.

**Verification:**

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py \
  tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_models.py \
  tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_storage.py
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_models.py \
  src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_client.py \
  src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py
GIT_CONFIG_GLOBAL=/dev/null git diff --check
python3 - "$PROFILECORE_REMEDIATION_BASELINE_DIR" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

baseline_dir = Path(sys.argv[1])
allowed = {
    "src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_models.py",
    "src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_client.py",
    "src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py",
    "tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py",
    "tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py",
    "tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py",
}

def current_dirty_statuses():
    raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        text=False,
    )
    statuses = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        if record[:1] in {b"R", b"C"} or record[1:2] in {b"R", b"C"}:
            raise SystemExit("STOP=scope_proof_rename_or_copy_not_supported")
        statuses[record[3:].decode("utf-8")] = record[:2].decode("ascii")
    return statuses

def digest(path):
    p = Path(path)
    return None if not p.is_file() else hashlib.sha256(p.read_bytes()).hexdigest()

baseline = json.loads((baseline_dir / "dirty-baseline.json").read_text())
baseline_paths = set(baseline)
final_statuses = current_dirty_statuses()
final_paths = set(final_statuses)
changed_after_baseline = {
    path for path in baseline_paths if digest(path) != baseline[path]["sha256"]
} | (final_paths - baseline_paths)
unexpected = changed_after_baseline - allowed
assert not unexpected, {"STOP": "scope_path_outside_allowlist", "paths": sorted(unexpected)}
for path in baseline_paths - allowed:
    assert digest(path) == baseline[path]["sha256"], {"STOP": "preexisting_dirty_bytes_changed", "path": path}
    assert final_statuses.get(path) == baseline[path]["status"], {"STOP": "preexisting_dirty_status_changed", "path": path}
print({"task_induced_paths": sorted(changed_after_baseline), "preexisting_preserved": True})
PY
test "$(git ls-files -s -z | shasum -a 256 | awk '{print $1}')" \
  = "$(cat "$PROFILECORE_REMEDIATION_BASELINE_DIR/index.sha256")" || {
  echo 'STOP=git_index_changed' >&2
  exit 1
}
shasum -a 256 \
  docs/designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md \
  docs/plans/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-implementation-plan_CN.md \
  docs/designs/2026-09-04-external-signal-shadow-lab-stage1-6e-b-completion-remediation-delta-design_CN.md \
  docs/plans/2026-09-05-external-signal-shadow-lab-stage1-6e-b-completion-remediation-implementation-plan_CN.md \
  docs/plans/2026-09-06-external-signal-shadow-lab-stage1-6e-b-profilecore-provenance-and-raw-cap-remediation-implementation-plan_CN.md
assert_sha() {
  test "$(shasum -a 256 "$2" | awk '{print $1}')" = "$1" || {
    echo "STOP=authority_sha_mismatch:$2" >&2
    exit 1
  }
}
assert_sha 752aecff8735f22513483e6bf65ae991386f46ff2ae953da44cd1fe9c5898583 \
  docs/designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md
assert_sha 279f729645c9e3691797a92059cab3d212e7b62c0ffbdb49a49947bb712b4da6 \
  docs/plans/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-implementation-plan_CN.md
assert_sha 145bbb7d84e4d7ae4fc9e901b293b8520b3b825d1377f96d02bff8b8dc67ee44 \
  docs/designs/2026-09-04-external-signal-shadow-lab-stage1-6e-b-completion-remediation-delta-design_CN.md
assert_sha acb2e5b88d68b633f1b0ad81d2d62d687d07ee4dd0f6c2a6cbed8ed1552dc479 \
  docs/plans/2026-09-05-external-signal-shadow-lab-stage1-6e-b-completion-remediation-implementation-plan_CN.md
: "${EXPECTED_APPROVED_PROFILECORE_REMEDIATION_PLAN_SHA256:?STOP=profilecore_remediation_plan_bytes_not_authorized}"
assert_sha "$EXPECTED_APPROVED_PROFILECORE_REMEDIATION_PLAN_SHA256" \
  docs/plans/2026-09-06-external-signal-shadow-lab-stage1-6e-b-profilecore-provenance-and-raw-cap-remediation-implementation-plan_CN.md
test "$(shasum -a 256 .agent/tools/anti_shortcut_scan.py | awk '{print $1}')" \
  = "$(cat "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner.sha256")"
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" \
  > "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-final.txt" 2>&1; then
  SCANNER_FINAL_RC=0
else
  SCANNER_FINAL_RC=$?
fi
cat "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-final.txt"
printf '%s\n' "$SCANNER_FINAL_RC" \
  > "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-final.exitcode"
test "$SCANNER_FINAL_RC" -eq 0 || {
  echo 'STOP=scanner_final_nonzero' >&2
  exit 1
}
python3 - "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-warning-identities.json" \
  "$PROFILECORE_REMEDIATION_BASELINE_DIR/scanner-final.txt" <<'PY'
import json
import re
import sys
from pathlib import Path

baseline = set(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
final_lines = Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
assert not any(line.startswith("[ERROR]") for line in final_lines), "STOP=scanner_error"
final = {
    re.sub(r":\d+:\d+ - ", ":<location> - ", line)
    for line in final_lines
    if line.startswith("[WARN]")
}
assert not any("event_max_raw_response_bytes" in line for line in final), (
    "STOP=raw_cap_fallback_warning_present"
)
assert not (final - baseline), {"STOP": "new_scanner_warning", "warnings": sorted(final - baseline)}
print({"final_warning_count": len(final), "warning_identities": sorted(final)})
PY
python3 - <<'PY'
from configs import base
from src.risk.limits import RiskLimits
assert base.RISK_LIVE_TRADING_ENABLED is False
assert RiskLimits().live_trading_enabled is False
PY
```

**Expected:** all tests and `ruff` pass, `git diff --check` is clean, the scope proof reports only the six whitelisted code/test paths (or a strict subset) while preserving all other baseline dirty bytes/statuses and the exact initial index snapshot, all bound authority bytes remain exact, scanner has a recorded zero process exit/no errors/no raw-cap fallback/no new warning identity and only separately dispositioned baseline warnings, and both live-trading controls are false.

**STOP:** any test failure, scanner error or residual raw-cap warning, changed path outside whitelist, new runtime artifact, safety failure, or independent-audit verdict other than `complete`.

## Author Self-Review

| Requirement | Task | Verification |
|---|---:|---|
| exact verified E-A attestation enters derived ProfileCore | 1, 3 | canonical upstream helper plus persisted event profile assertions |
| inner raw cap is exactly the approved 262144/32768 transform | 1, 2, 3 | four-profile model test, direct-client 32769-byte rejection, observer slot regression |
| no default/alias at transport boundary | 2 | missing/bool/string/zero cap tests before opener dispatch |
| no observer provenance/cap patch | 3 | direct constructor and direct inner-core call only |
| no scope/safety/runtime expansion | 0, 4 | exact whitelist, scanner, static false-permission assertions, independent audit |

This Plan can prove that E-B produces and consumes the approved Event ProfileCore provenance and raw-cap contract without fallback. It cannot prove alpha, cost, execution feasibility, replay quality, paper/live trading readiness, or VPS runtime correctness. The only permitted subsequent decision after an independent `complete` audit is whether to seek a separate deployment authorization; all trading and execution authority remains false.
