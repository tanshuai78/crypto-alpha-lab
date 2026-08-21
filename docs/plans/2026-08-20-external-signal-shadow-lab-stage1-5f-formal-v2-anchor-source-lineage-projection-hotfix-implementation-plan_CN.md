# Stage 1.5F Formal-V2 Anchor Source Lineage Projection Hotfix Implementation Plan

**状态：** Draft for independent review; not implementation authority
**日期：** 2026-08-20
**实现 diff 基线：** execution-time `BASE_SHA`（Task 0 冻结）
**冻结 v1 replay authority：** `FROZEN_V1_BASE_SHA=9e397059ebe869b6535465451e392affd936da87`
**Design authority：** [2026-08-20 Design Delta 1](../designs/2026-08-20-external-signal-shadow-lab-stage1-5f-formal-v2-anchor-source-lineage-projection-hotfix-design_CN.md)
**Design SHA-256 at planning：** `0b074f1d823b7205420de7535644c3242160649cb11254140673e16a8c8e6bd8`
**Replaces:** the prior unapproved Plan draft at this same path. It must not be used.

> **For Codex:** Implementation must use the approved-plan execution workflow and execute Task 0 through Task 5 in order. Every behavior change is RED -> minimal GREEN -> scoped regression. Do not implement, commit, deploy, restart a VPS process, or create a root until this Plan receives review verdict `Approve` and the user explicitly approves execution.

**Goal:** Preserve frozen `source_semantic_fingerprint_v1` exactly while allowing only newly-created **formal-v2** states to use a strict v2 source-aware replay identity; project the official anchor source through F and require 1.5G to verify the complete accepted/state lineage, including recovery after `revision_applied` precedes the adapter state write.

**Architecture:** Keep `compute_event_semantic_fingerprint()` as the unmodified v1 algorithm. Add loader-local v2 computation and strict prefix parsing; pass a prefixed v2 value through existing eligibility diagnostics into the existing state field, with no schema/model/runner change. Pending schedule revisions are selected only by a validated loader-local adapter, while the existing runner continues to reload the full D stream and invoke re-resolution; direct pending v2 reducer application becomes a no-op so the adapter is the sole pending-state selection writer.

**Tech Stack:** Python 3.11, stdlib `dataclasses`/`hashlib`/`json`/`re`, existing Stage 1.5 contract helpers, pytest, Ruff.

**Material assumptions frozen for execution:**

1. The approved Design Delta is the authority for v1/v2 compatibility. The Plan must not modify either the Design or this Plan during implementation.
2. `run_stage1_5f_live_depth_observer.py` reloads all D event rows each poll, processes revision registry records, then invokes `re_resolve_pending_anchor()` with full `current_poll_events` whenever revision rows exist. This is read-only compatibility evidence, not authorization to modify the runner.
3. `EventSymbolState.latest_source_semantic_fingerprint` exists and `from_dict()` preserves it without a length assertion. `observer_state_schema_version` remains `3`; no migration or new state field is authorized.
4. An invalid or unknown explicit v2 prefix must use the runner's existing safe batch-blocked path and must not mutate state, accepted rows or the watermark. If Task 0 proves this cannot be expressed through existing allowed loader behavior, STOP rather than modify the runner.
5. Legacy roots are read-only historical evidence under the hotfixed deployment. Attaching the hotfixed runtime only to a newly-created F root is a separate rollout-review prerequisite, not a fact this code-only Plan can prove. This Plan authorizes no rollout.

---

## Allowed Change Scope

Allowed implementation paths:
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`

Allowed verification paths:
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- `tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py` (read-only compatibility regression)
- `tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py` (read-only compatibility regression)

Allowed documentation paths:
- `none` during implementation. The Design and this Plan are immutable authority after approval.

Allowed generated/runtime artifacts:
- Execution-local provenance only at `$EXECUTION_EVIDENCE_DIR` outside the repository. Do not create or commit `data/**`, `graphify-out/**`, `/tmp` evidence snapshots, or VPS output.

Affected but unchanged:
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
  - Evidence: Task 0 verifies `latest_source_semantic_fingerprint` round-trips through `EventSymbolState.to_dict()`/`from_dict()` with no length/hex constraint; schema version remains `3`.
- `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
  - Evidence: Task 0 records ordering of full event load -> registry processing -> re-resolution. Task 4 proves its existing batch-blocked, registry and watermark behavior with no diff.
- `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py`
  - Evidence: Task 4 proves one existing `revision_applied` row remains one row during restart recovery; registry test remains zero-diff.
- `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`
  - Evidence: Task 2 reuses `validate_schedule_revision_contract()`, `select_latest_applicable_official_schedule()` and `compute_latest_anchor_contract_hash()` unchanged; run read-only contract regressions.
- `src/research/external_signal_shadow/stage1_5_storage_guard.py` and all storage writers
  - Evidence: all new behavior is reducer value selection; Task 5 confirms no write-surface or storage-guard diff.
- `configs/base.py`
  - Evidence: zero diff; `RISK_LIVE_TRADING_ENABLED` and `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED` remain `False`.
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
  - Evidence: source maps remain D-owned read-only authority; zero diff.
- `docs/designs/2026-08-20-external-signal-shadow-lab-stage1-5f-formal-v2-anchor-source-lineage-projection-hotfix-design_CN.md`
- `docs/plans/2026-08-20-external-signal-shadow-lab-stage1-5f-formal-v2-anchor-source-lineage-projection-hotfix-implementation-plan_CN.md`
- `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`
  - Evidence: no deployment/runbook change is authorized.

Forbidden:
- Any mutation outside the Allowed implementation and verification paths.
- Any modification to `configs/base.py`, model schema, runner, schedule registry, launch/revision contract, D producer, storage guard, execution/risk/strategy/order modules, or existing `data/external_signal_shadow/**` artifacts.
- Any online migration, old-root resume, JSONL rewrite, accepted-row rewrite, watermark bootstrap, VPS deployment/restart, root deletion, `git clean`, `git reset`, or `ruff check --fix .`.
- Any top-level formal-v2 source fallback, raw-revision source fabrication, G-side inference, v1 hash-input alteration, formal contract/version change, config threshold change, or permission expansion.

## Invariant-to-Task Mapping

| Design invariant | Task(s) | Mechanical evidence |
|---|---|---|
| `INV-01` | 0, 2 | Source-map inventory; resolver diagnostics and spoofed top-level source RED/GREEN tests. |
| `INV-02` | 2 | Formal-v2 resolver returns equal official basis and source. |
| `INV-03` | 2, 4 | Raw revision validation before reduction; selected adapter only; runner recovery test. |
| `INV-04` | 2, 4 | Pending atomic update; active/completed no-reopen and accepted-row immutability. |
| `INV-05` | 3 | G rejects null/mismatched accepted/latest source and basis. |
| `INV-06` | 3 | Basis/hash never supplies a missing source. |
| `INV-07` | 1, 2, 5 | Frozen v1 exact digest, formal-v1 and existing conflict/fallback/revision regressions. |
| `INV-08` | 0, 3 | UNITREE structural negative shape remains rejected; no artifact mutation. |
| `INV-09` | 0, 5 | Config/model/runner/contract/guard zero-diff gates. |
| `INV-10` | 1, 2, 4 | v2 source-only exactly once; selected revision restart idempotence. |
| `INV-11` | 0, 5 | No existing root/artifact mutation; deployment excluded. |
| `INV-12` | 0, 5 | Safety flags false; no execution/risk diff. |
| `INV-13` algorithmic fingerprint part | 0, 1, 5 | v1 digest frozen; v2 prefix only for newly-created formal-v2 state; old/empty values never upgraded. |
| `INV-13` new-root provenance part | Deferred to rollout review | The hotfixed runtime must attach only to a newly-created F root. This Plan does not claim code-level proof because no root-mode authority is in scope. |
| `INV-14` | 1, 4 | Same-anchor/source-only v2 pending update once; active/completed no reopen. |
| `INV-15` | 2, 4 | `revision_applied` crash fixture proves one full validated lineage tuple and no duplicate durable effects. |
| `INV-16` | 0, 1, 5 | All explicit malformed/unknown prefixes fail closed, never downgrade to v1. |
| `INV-17` | 0, 5 | No old-root runtime operation; no runner/root/deployment modification. Operational enforcement remains deferred to rollout review. |

## Task 0: Execution Authority, Consumer Inventory And STOP Gates

**Design invariants:** `INV-01`, `INV-07`-`INV-13`, `INV-16`, `INV-17`.

**Files:**
- Modify: none.
- Read: Design, this Plan, all Allowed and Affected-but-unchanged paths.

### Step 1: Freeze provenance before any edit

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
export FROZEN_V1_BASE_SHA="9e397059ebe869b6535465451e392affd936da87"
export BASE_SHA="$(git rev-parse HEAD)"
export DESIGN_PATH="docs/designs/2026-08-20-external-signal-shadow-lab-stage1-5f-formal-v2-anchor-source-lineage-projection-hotfix-design_CN.md"
export PLAN_PATH="docs/plans/2026-08-20-external-signal-shadow-lab-stage1-5f-formal-v2-anchor-source-lineage-projection-hotfix-implementation-plan_CN.md"
export DESIGN_SHA256="$(shasum -a 256 "$DESIGN_PATH" | awk '{print $1}')"
export PLAN_SHA256="$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}')"
export EXECUTION_EVIDENCE_DIR="${CODEX_HOME:-$HOME/.codex}/execution-evidence/stage1_5f_formal_v2_lineage_${BASE_SHA}"
export EXECUTION_LOG="$EXECUTION_EVIDENCE_DIR/execution.log"
mkdir -p "$EXECUTION_EVIDENCE_DIR"
chmod 700 "$EXECUTION_EVIDENCE_DIR"
test "$FROZEN_V1_BASE_SHA" = "9e397059ebe869b6535465451e392affd936da87"
git cat-file -e "${FROZEN_V1_BASE_SHA}^{commit}"
git merge-base --is-ancestor "$FROZEN_V1_BASE_SHA" "$BASE_SHA"
printf 'FROZEN_V1_BASE_SHA=%s\nBASE_SHA=%s\nDESIGN_SHA256=%s\nPLAN_SHA256=%s\nEXECUTION_LOG=%s\n' \
  "$FROZEN_V1_BASE_SHA" "$BASE_SHA" "$DESIGN_SHA256" "$PLAN_SHA256" "$EXECUTION_LOG" | tee -a "$EXECUTION_LOG"
git status --short --untracked-files=all | tee -a "$EXECUTION_LOG"
```

Expected: `FROZEN_V1_BASE_SHA` is exactly `9e397059ebe869b6535465451e392affd936da87` and is an ancestor of execution-time `BASE_SHA`. `FROZEN_V1_BASE_SHA` is the only v1 replay-identity authority; `BASE_SHA` is only the implementation diff/scope authority. Design SHA equals `0b074f1d823b7205420de7535644c3242160649cb11254140673e16a8c8e6bd8`; existing untracked Design/Plan are recorded as pre-existing documentation, not attributed to implementation. All Task 0 evidence is appended to `$EXECUTION_LOG` outside the repository and is never committed.

STOP if the frozen commit is unavailable, is not an ancestor of `BASE_SHA`, the Design SHA differs, the user has not approved this exact Plan, or a pre-existing dirty code path overlaps an Allowed path without an independently recorded patch/SHA.

### Step 2: Record exact topology and runner order

Run and retain output in the execution log:

```bash
.venv/bin/python -m graphify query 'compute_event_semantic_fingerprint'
.venv/bin/python -m graphify query 're_resolve_pending_anchor'
rg -n -C 5 'compute_event_semantic_fingerprint|classify_event_symbol_revision_admission|upsert_pending_state_with_event_revision|re_resolve_pending_anchor' \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py
rg -n -C 6 'load_all_events|process_schedule_revision_event|re_resolve_pending_anchor|current_poll_events' \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
sed -n '160,240p' src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py
```

Expected ordering is `load_all_events -> process_schedule_revision_event -> re_resolve_pending_anchor(current_poll_events)`. Record exact locations for the inventory; Graphify is advisory and source output is authoritative.

### Step 3: Complete the required source-map and fingerprint-consumer inventory

Run:

```bash
rg -n -C 3 'symbol_effective_observation_anchor_sources|symbol_official_schedule_anchor_ms|symbol_anchor_evidence_levels|symbol_max_evidence_classes' \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py
rg -n -C 3 'latest_source_semantic_fingerprint|compute_event_semantic_fingerprint' \
  src/research/external_signal_shadow scripts/external_signal_shadow \
  tests/research/external_signal_shadow tests/scripts/external_signal_shadow
rg -n -i 'fingerprint.*(len|length|hex|sha|64)|len\([^\n]*fingerprint|fullmatch\([^\n]*fingerprint' \
  src scripts tests || true
```

Write an execution table with exactly these columns:

```text
consumer or per-symbol field | current call-site | v1/v2 or projection behavior | needs edit? | allowed path? | result
```

The table must enumerate, at minimum:

```text
compute helper
classifier
pending upsert
new-state diagnostics/builder
EventSymbolState.to_dict/from_dict
state compaction and restart loader
runner wiring tests
any fingerprint length/hex-format assertion
symbol_effective_observation_anchor_sources
symbol_official_schedule_anchor_ms
symbol_anchor_evidence_levels
symbol_max_evidence_classes
```

Record the source-only probe explicitly: same event/payload/anchor with changed source must leave current v1 unchanged and be suppressed before this hotfix.

Write a second source-only pending-transition table to `$EXECUTION_LOG` before
writing Task 1 tests. It must use one same-anchor formal-v2 old/incoming pair
and exactly these columns:

```text
field | old pending value | incoming validated value | required action | authority / reason
```

The required actions are frozen as follows:

| Field | Required action for valid same-anchor formal-v2 source-only upsert |
|---|---|
| `latest_source_semantic_fingerprint` | Update to the exact prefixed v2 value. |
| `effective_observation_anchor_source` | Update from validated resolver diagnostics only. |
| `observation_anchor_basis` | Update to the same validated source. |
| `observation_anchor_ms` | Must equal the old pending anchor; otherwise this narrow upsert is forbidden. |
| `source_anchor_contract_hash` | Update to the incoming validated resolver hash, because its canonical contract includes effective source. |
| `admission_anchor_contract_hash` | Remain byte-for-byte unchanged: pending state has not been admitted. |
| `latest_anchor_contract_hash` | Remain byte-for-byte unchanged: no schedule-revision application/admission transition occurred. |
| `source_contract_status` | Must remain or become the incoming `formal_v2_valid` value. |
| `launch_anchor_evidence_level` | Update only from the incoming validated formal-v2 row; expected official schedule value. |
| `anchor_precedence_policy` | Must equal the incoming approved policy and the old value; mismatch is not a source-only upsert. |

STOP if the actual source inventory contradicts any table row or requires a
field outside the allowed loader/state paths. Do not substitute a hash, basis,
or title for the authoritative source map.

STOP if:
- a source map other than the known source field is not projected or cannot be proved invariant-equivalent;
- any fingerprint consumer needs modification outside the three Allowed implementation files or four editable test files;
- a consumer assumes every fingerprint is 64 characters and cannot accept a prefixed v2 value without modifying an unapproved path;
- the existing runner cannot map malformed explicit v2 prefix to its existing safe batch-blocked behavior without a runner change.

Report the exact call-site, impact, required path and proposed separate Design/Plan. Do not expand this scope.

### Step 4: Freeze v1 against the immutable historical authority and record safety boundary

Before changing the helper, prove the `BASE_SHA` pre-hotfix source equals the
same fixed fixture evaluated from `FROZEN_V1_BASE_SHA`; do not bless a
descendant or the current workspace result as the v1 authority. This command
executes both committed sources in memory only and does not create a repository
or `/tmp` artifact.

```bash
PYTHONPATH=src:. .venv/bin/python - "$FROZEN_V1_BASE_SHA" "$BASE_SHA" <<'PY' | tee -a "$EXECUTION_LOG"
import json
import subprocess
import sys

frozen_v1_base, pre_hotfix_head = sys.argv[1:]

def load_v1_at(ref):
    source = subprocess.check_output(
        ["git", "show", f"{ref}:src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py"],
        text=True,
    )
    namespace = {"__name__": f"_v1_loader_{ref[:12]}", "__file__": f"{ref}_loader.py"}
    exec(compile(source, f"{ref}_loader.py", "exec"), namespace)
    return namespace["compute_event_semantic_fingerprint"]

frozen_v1 = load_v1_at(frozen_v1_base)
pre_hotfix_v1 = load_v1_at(pre_hotfix_head)
fixture = {
    "source_article_id": "art1",
    "event_type": "futures_contract_launch",
    "symbol": "ABCUSDT",
    "symbols": ["ABCUSDT"],
    "title": "Binance Launch ABCUSDT",
    "source_published_at_ms": 1_000_000,
    "symbol_official_schedule_anchor_ms": {"ABCUSDT": 2_000_000},
    "symbol_onboard_times_ms": {"ABCUSDT": 1_900_000},
    "symbol_effective_launch_times_ms": {"ABCUSDT": 2_000_000},
}
frozen_digest = frozen_v1(fixture, "ABCUSDT")
pre_hotfix_head_digest = pre_hotfix_v1(fixture, "ABCUSDT")
assert frozen_digest == pre_hotfix_head_digest, (frozen_digest, pre_hotfix_head_digest)
print(json.dumps({
    "frozen_9e39705_v1_digest": frozen_digest,
    "pre_hotfix_HEAD_v1_digest": pre_hotfix_head_digest,
    "fixture": fixture,
}, sort_keys=True))
PY

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py::test_compute_event_semantic_fingerprint_included_and_excluded_fields -q | tee -a "$EXECUTION_LOG"
rg -n 'RISK_LIVE_TRADING_ENABLED|EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED' configs/base.py | tee -a "$EXECUTION_LOG"
```

Expected: `frozen_9e39705_v1_digest == pre_hotfix_HEAD_v1_digest`.
Copy that frozen digest, not a newly invented value, into Task 1's RED test as
`FROZEN_V1_REFERENCE_DIGEST`. The post-hotfix completion gate must prove
`frozen_9e39705_v1_digest == pre_hotfix_HEAD_v1_digest == post_hotfix_v1_digest`.
Both safety flags remain `False`.

## Task 1: Version-Aware Replay Identity Without Changing Frozen v1

**Design invariants:** `INV-07`, `INV-09`, `INV-10`, `INV-13`, `INV-14`, `INV-16`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

### Step 1: Write RED tests before code

Add minimal synthetic formal-v2 rows only, plus one explicit formal-v1
compatibility row. No live root, raw payload or network fixture is permitted.
Tests must prove:

```python
# v1 is a digest frozen at 9e397059..., not merely "same as before".
assert compute_event_semantic_fingerprint(v1_fixture, "ABCUSDT") == FROZEN_V1_REFERENCE_DIGEST

# Same row except the source map: v1 is identical, v2 is distinct and exact.
assert compute_event_semantic_fingerprint(old_source, symbol) == compute_event_semantic_fingerprint(new_source, symbol)
assert compute_event_semantic_fingerprint_v2(old_source, symbol) != compute_event_semantic_fingerprint_v2(new_source, symbol)
assert re.fullmatch(r"source_semantic_fingerprint_v2:[0-9a-f]{64}", v2_value)

# New state receives the v2 value from eligibility diagnostics and survives to_dict/from_dict.
state = create_pending_observation_state(new_source, status, v2_diagnostics, now_ms)
assert state.latest_source_semantic_fingerprint == v2_value
assert EventSymbolState.from_dict(state.to_dict()).latest_source_semantic_fingerprint == v2_value

# New formal-v1 state never receives a v2 seed and retains current replay behavior.
formal_v1_state = create_pending_observation_state(formal_v1_row, v1_status, v1_diagnostics, now_ms)
assert not formal_v1_state.latest_source_semantic_fingerprint.startswith("source_semantic_fingerprint_v2:")
assert classify_event_symbol_revision_admission(formal_v1_row, {id: formal_v1_state}, {})[0] == V1_EXPECTED_REPLAY_ACTION

# Existing bare v1 and empty values remain legacy; a source-only correction does not upgrade them.
assert classify_event_symbol_revision_admission(new_source, {id: v1_state}, {})[0] == "exact_replay_noop"
assert classify_event_symbol_revision_admission(new_source, {id: empty_legacy_state}, {})[0] == "exact_replay_noop"

# Existing v2 recognises a same-anchor/source-only difference as a pending revision.
# Task 2 owns the resolver-backed atomic state transition itself.
assert classify_event_symbol_revision_admission(new_source, {id: v2_pending}, {})[0] == "pending_revision_upsert"

# Explicit malformed/unknown version never becomes legacy replay.
for bad in ("source_semantic_fingerprint_v2:", "source_semantic_fingerprint_v2:xyz", "source_semantic_fingerprint_v3:" + "0" * 64, "unexpected:abc"):
    action, _state, diag = classify_event_symbol_revision_admission(new_source, {id: state_with(bad)}, {})
    assert action == "identity_collision_blocked"
    assert diag["reason"] == "malformed_versioned_source_semantic_fingerprint"
```

The malformed-prefix assertion deliberately uses the existing `identity_collision_blocked` runner action: it blocks the batch before state/accepted/watermark mutation and needs no runner change. Its diagnostic reason is exactly `malformed_versioned_source_semantic_fingerprint`, distinct from the real stable-key collision reason; do not collapse these causes in loader diagnostics.

### Step 2: Run RED tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  -k 'semantic_fingerprint or fingerprint_version or source_only' -q
```

Expected: FAIL because v1 is currently the sole unprefixed algorithm, new states do not seed fingerprints, and malformed prefixes have no classification.

### Step 3: Implement the smallest version dispatcher

In `stage1_5f_live_depth_observer_loader.py`:

1. Preserve `compute_event_semantic_fingerprint()` byte-for-byte as v1 behavior. Do not add the source map to its dict. Its post-hotfix output for Task 0's fixed fixture must equal `frozen_9e39705_v1_digest`.
2. Add one loader-local v2 helper that uses the exact v1 projection plus `symbol_effective_observation_anchor_sources[symbol]`, canonicalizes with the same sorted/compact JSON rules, hashes it, and returns exactly `source_semantic_fingerprint_v2:<64 lowercase hex>`.
3. Add a narrow parser/dispatcher:
   - prefixed valid v2 -> compare only v2;
   - bare non-empty v1 -> compare only frozen v1 and retain current v1 payload fallback;
   - empty -> retain current legacy payload fallback;
   - explicit malformed/unknown prefix -> return existing `identity_collision_blocked` with a fingerprint-integrity diagnostic.
4. Put the v2 value in eligibility diagnostics **only for a newly-created formal-v2 state**. A new formal-v1 state retains existing v1/legacy behavior and never receives a prefixed v2 value. Pending source-only transition is deliberately deferred to Task 2, because it requires the newly-projected resolver source diagnostics.
5. For a v2 stored value, a same event/payload hash is not an exact replay when v2 differs. For v1/empty states, preserve the current replay rule exactly. Task 2 owns the resolver-backed upsert; it must not combine an anchor/policy/contract change into the narrow source-only transition.

In `stage1_5f_live_depth_observer_state.py`, persist only the diagnostics-provided fingerprint into the existing field when constructing a new state. Do not import loader code, add fields, alter `from_dict`, change schema version, or compute a second fingerprint in state code.

### Step 4: Run GREEN and v1 compatibility regressions

Run the Task 1 command again, then:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  -k 'formal_v1 or exchangeinfo or anchor_conflict or semantic_fingerprint' -q
```

Expected: formal-v1 receives no v2 seed; v2 detects a source-only pending revision; no legacy/empty value is upgraded; malformed explicit versions are blocked. Task 2 proves the atomic source-only state transition; Task 5 proves the three-way v1 digest equality.

## Task 2: Formal-V2 Source Projection And Validated Pending Revision Adapter

**Design invariants:** `INV-01`-`INV-04`, `INV-07`, `INV-10`, `INV-14`, `INV-15`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

### Step 1: Write RED tests for source authority and complete selection

Add tests for all of the following:

```python
# Initial formal-v2 source is projected only from the validated per-symbol map.
diag = resolve_depth_observation_anchor_ms(formal_v2_row, symbol, exchangeinfo, now_ms)
assert diag["observation_anchor_basis"] == "official_schedule_anchor"
assert diag["effective_observation_anchor_source"] == "official_schedule_anchor"

# Top-level source cannot spoof a missing formal-v2 map.
state = create_pending_observation_state(
    {**formal_v2_without_source_map, "effective_observation_anchor_source": "official_schedule_anchor"},
    "pending_launch_anchor_missing", {}, now_ms,
)
assert state.effective_observation_anchor_source in (None, "")

# Same anchor + changed validated source updates one complete pending lineage tuple.
assert classify_event_symbol_revision_admission(incoming_v2, {id: v2_pending}, {})[0] == "pending_revision_upsert"
updated = upsert_pending_state_with_event_revision(v2_pending, incoming_v2, symbol)
assert updated.latest_source_semantic_fingerprint == incoming_v2_fingerprint
assert updated.observation_anchor_basis == updated.effective_observation_anchor_source == "official_schedule_anchor"
assert updated.observation_anchor_ms == v2_pending.observation_anchor_ms
assert updated.source_anchor_contract_hash == validated_incoming_source_hash
assert updated.admission_anchor_contract_hash == v2_pending.admission_anchor_contract_hash
assert updated.latest_anchor_contract_hash == v2_pending.latest_anchor_contract_hash
assert updated.source_contract_status == "formal_v2_valid"
assert updated.launch_anchor_evidence_level == incoming_v2["launch_anchor_evidence_level"]
assert updated.anchor_precedence_policy == v2_pending.anchor_precedence_policy == incoming_v2["anchor_precedence_policy"]
assert classify_event_symbol_revision_admission(incoming_v2, {id: updated}, {})[0] == "exact_replay_noop"

# Raw invalid schedule revision is rejected before reduction/selection.
assert validated_schedule_selection(invalid_full_row, pending_state, now_ms) is None

# One selected revision returns one inseparable tuple.
selection = validated_schedule_selection(valid_full_row, pending_state, now_ms)
assert (selection.revision_id, selection.revision_application_id, selection.revised_anchor_ms,
        selection.effective_observation_anchor_source, selection.available_at_ms,
        selection.supersedes_source_article_id) == EXPECTED

# Pending formal-v2 direct revision reducer does not claim selection completion.
assert apply_anchor_contract_revision_to_state(pending_v2, valid_full_row, now_ms) == pending_v2

# Adapter transition owns all matching state lineage fields.
updated = re_resolve_pending_anchor(pending_v2, [valid_full_row], exchangeinfo, now_ms)
assert updated.observation_anchor_ms == selection.revised_anchor_ms
assert updated.observation_anchor_basis == updated.effective_observation_anchor_source == "official_schedule_anchor"
assert selection.revision_application_id in updated.applied_schedule_revision_ids
assert updated.anchor_contract_revision_count == pending_v2.anchor_contract_revision_count + 1
assert updated.latest_anchor_contract_hash == expected_hash_for_same_selection
```

Retain RED cases for supersedes mismatch, stable-key mismatch, unavailable future revision, same-timestamp conflict, cancellation and formal-v1 direct reducer behavior.

### Step 2: Run RED tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  -k 'formal_v2 and (effective_observation_anchor_source or schedule or revision)' -q
```

Expected: FAIL because source is absent from resolver diagnostics, state permits top-level fallback, raw revisions are reduced before validation, and direct pending revision handling can claim application before the adapter writes source lineage.

### Step 3: Implement only the validated adapter path

1. In `resolve_depth_observation_anchor_ms()`, formal-v2 validated branch must emit both:

```python
"observation_anchor_basis": effective_source,
"effective_observation_anchor_source": effective_source,
```

2. In `create_pending_observation_state()`, formal-v2 reads `effective_observation_anchor_source` from diagnostics only. Preserve current event-row fallback only for formal-v1.

3. In `upsert_pending_state_with_event_revision()`, handle only a stored valid-v2 state plus a valid same-anchor formal-v2 incoming row as the narrow source-only transition. Call the shared resolver without network input; require its anchor to equal the pending anchor and its source to be validated official. Atomically apply the Task 0 lineage table: update v2 fingerprint, source, basis, source contract hash, source contract status and launch evidence level; preserve pending admission/latest hashes and anchor. Do not set `next_anchor_resolution_at_ms = 0`. If any precondition fails, preserve existing anchor/revision handling rather than partially update the tuple.

4. In `re_resolve_pending_anchor()`, call `validate_schedule_revision_contract(row)` inside the raw `for row in event_revisions` loop **before** reading maps or appending any reduced `schedule_rows` entry. Invalid rows cannot enter selection.

5. Add one frozen loader-local `ValidatedScheduleSelection` result containing exactly:

```text
revision_id
revision_application_id
revised_anchor_ms
effective_observation_anchor_source
available_at_ms
supersedes_source_article_id
revision_payload_hash
anchor_precedence_policy
```

It is built only after validation, stable identity/supersedes match, point-in-time availability, and `select_latest_applicable_official_schedule()` select the same validated raw row. Do not reassemble anchor from one row and provenance from another.

6. For pending formal-v2, make `apply_anchor_contract_revision_to_state()` return the unchanged state before writing application ids, revision count or anchor hash. This preserves formal-v1 and active/completed contamination behavior. The registry's existing `revision_applied` record remains dispatch idempotency only.

7. Let loader-local re-resolution apply the complete `ValidatedScheduleSelection` atomically to the pending state's existing fields: anchor, basis, effective source, `applied_schedule_revision_ids`, `anchor_contract_revision_count`, `latest_anchor_contract_hash`, available/decision metadata and pending scheduling fields. Reuse the unchanged `compute_latest_anchor_contract_hash()` helper. If the same application id is already in state, return exact state unchanged.

Do not add a generic registry, new state field, runner branch, revision contract field, or config.

### Step 4: Run GREEN and compatibility regressions

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  -q
```

Expected: formal-v2 initial/revision source is authoritative and coherent; existing formal-v1/revision contract/registry behavior remains green.

## Task 3: 1.5G Strict Formal-V2 Consumer Predicate

**Design invariants:** `INV-05`, `INV-06`, `INV-08`.

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py`

### Step 1: Write RED consumer tests

Extend the existing formal-v2 integrity fixture by mutating one field per case. Assert blocker `formal_v2_lineage_incomplete_or_mismatch` for:

```python
latest_state["effective_observation_anchor_source"] = None
accepted_event["effective_observation_anchor_source"] = "official_schedule_anchor"
latest_state["effective_observation_anchor_source"] = "exchangeinfo_onboard_date"
accepted_event["effective_observation_anchor_source"] != latest_state["effective_observation_anchor_source"]
accepted_event["observation_anchor_basis"] != accepted_event["effective_observation_anchor_source"]
latest_state["observation_anchor_basis"] != latest_state["effective_observation_anchor_source"]
accepted_event["observation_anchor_basis"] != latest_state["observation_anchor_basis"]
```

Keep the UNITREE structural negative shape: otherwise-valid hashes/policy/basis with null source remains rejected. Add one all-equal official source/basis pass case.

### Step 2: Run RED tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  -k 'formal_v2 or lineage' -q
```

Expected: FAIL because the current predicate checks accepted source but not the latest state source or all basis/source equality relationships.

### Step 3: Implement the narrow predicate extension

In `_validate_formal_v2_lineage()` require all six Design relationships directly from durable accepted/latest values:

```text
accepted source == official_schedule_anchor
latest source == official_schedule_anchor
accepted source == latest source
accepted basis == accepted source
latest basis == latest source
accepted basis == latest basis
```

Do not infer a source from hashes, basis, event title, wall clock or fallback. Keep the existing v1 early return and blocker string unchanged.

### Step 4: Run GREEN tests

Run the Task 3 command again. Expected: only the complete durable formal-v2 chain passes; UNITREE remains invalid.

## Task 4: Runner-Level Exactly-Once And Registry-Before-Adapter Crash Recovery

**Design invariants:** `INV-04`, `INV-10`, `INV-14`, `INV-15`, `INV-17`.

**Files:**
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Read only: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Read only: `src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py`

### Step 1: Write RED runner tests without a live server

Use `tmp_path`, deterministic event JSONL, mock exchangeinfo, an existing watermark and a bounded `--max-polls` invocation. Do not use `data/**` or network. Add:

1. **v2 source-only lifecycle test:** seed a v2 pending state, send same event/payload/anchor with changed source, run one poll, then replay it. Assert exactly one new pending state row containing every Task 0 source-only lineage value: new fingerprint, official source/basis, incoming source hash/status/evidence level, unchanged anchor/admission/latest hashes and policy. Replay adds none. Seed active and completed variants and assert no reopen, no second accepted row, and no mutation of admission anchor/source or accepted row.
2. **registry-before-adapter crash recovery test:** seed a pending formal-v2 state that has no applied revision id, a valid raw revision event and a registry JSONL containing one durable `revision_received` plus one `revision_applied` for its `revision_application_id`. Do not pre-write the adapter transition. Save watermark bytes and accepted-row count, then run one bounded non-bootstrap poll.
3. **malformed-versioned-fingerprint no-write test:** seed a state with `source_semantic_fingerprint_v2:xyz`, save the exact state-file, accepted-row and watermark bytes, then run one bounded poll with the matching event. Assert the existing runner batch-blocks the event, state/accepted/watermark bytes are unchanged, no active observation begins, and the loader diagnostic reason is `malformed_versioned_source_semantic_fingerprint` rather than the real identity-collision reason.

The second test must assert after restart:

```text
exactly one revision_applied registry record
no new accepted row
watermark bytes unchanged
selected revision_id == expected raw revision revision_id
selected revision_application_id is present in applied_schedule_revision_ids
anchor_contract_revision_count increments exactly once
latest_anchor_contract_hash == hash for that same selected revision
observation_anchor_ms == selected revised anchor
observation_anchor_basis == effective_observation_anchor_source == official_schedule_anchor
second identical bounded poll adds no state transition or registry row
```

### Step 2: Run RED tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k 'source_only or revision_applied or restart or malformed' -q
```

Expected: FAIL before Task 1/2 changes because v2 state dispatch/adapter source lineage and recovery tuple are absent or incomplete.

### Step 3: Run GREEN runner tests

Run the Task 4 command again after Task 1-3 code is green.

Expected: existing runner full-stream re-resolution recovers the missing adapter transition under a registry-applied crash window; no runner source change is necessary. If this fails because a runner behavior change is required, STOP and create a new Design/Plan rather than modifying the runner.

## Task 5: Completion Gate, Scope Gate And Independent Completion Audit

**Design invariants:** all `INV-01` through `INV-17`.

**Files:**
- Modify: none.

### Step 1: Run the complete scoped suite

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py \
  tests/research/external_signal_shadow/test_stage1_5f_schedule_revision_registry.py \
  -q
```

Expected: all pass. A failure in an affected-but-unchanged test is a STOP; do not edit that path to force green.

### Step 2: Run static, safety and exact scope gates

```bash
.venv/bin/ruff check \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py

PYTHONPATH=src:. .venv/bin/python - "$FROZEN_V1_BASE_SHA" "$EXECUTION_LOG" <<'PY' | tee -a "$EXECUTION_LOG"
import json
import subprocess
import sys

from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
    compute_event_semantic_fingerprint as post_hotfix_v1,
)

frozen_v1_base, log_path = sys.argv[1:]
source = subprocess.check_output(
    ["git", "show", f"{frozen_v1_base}:src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py"],
    text=True,
)
namespace = {"__name__": "_baseline_stage1_5f_loader", "__file__": "baseline_loader.py"}
exec(compile(source, "baseline_loader.py", "exec"), namespace)
fixture = {
    "source_article_id": "art1",
    "event_type": "futures_contract_launch",
    "symbol": "ABCUSDT",
    "symbols": ["ABCUSDT"],
    "title": "Binance Launch ABCUSDT",
    "source_published_at_ms": 1_000_000,
    "symbol_official_schedule_anchor_ms": {"ABCUSDT": 2_000_000},
    "symbol_onboard_times_ms": {"ABCUSDT": 1_900_000},
    "symbol_effective_launch_times_ms": {"ABCUSDT": 2_000_000},
}
frozen_digest = namespace["compute_event_semantic_fingerprint"](fixture, "ABCUSDT")
post_digest = post_hotfix_v1(fixture, "ABCUSDT")
pre_records = [
    json.loads(line) for line in open(log_path, encoding="utf-8")
    if line.startswith('{') and "pre_hotfix_HEAD_v1_digest" in line
]
assert pre_records, "STOP: Task 0 frozen v1 record missing"
pre_digest = pre_records[-1]["pre_hotfix_HEAD_v1_digest"]
assert frozen_digest == pre_digest == post_digest, (frozen_digest, pre_digest, post_digest)
print(json.dumps({
    "frozen_9e39705_v1_digest": frozen_digest,
    "pre_hotfix_HEAD_v1_digest": pre_digest,
    "post_hotfix_v1_digest": post_digest,
}, sort_keys=True))
PY

git diff --check "$BASE_SHA"

test "$(shasum -a 256 "$DESIGN_PATH" | awk '{print $1}')" = "$DESIGN_SHA256"
test "$(shasum -a 256 "$PLAN_PATH" | awk '{print $1}')" = "$PLAN_SHA256"

test -z "$(git diff --name-only "$BASE_SHA" -- configs/base.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py \
  src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py \
  src/research/external_signal_shadow/stage1_5_storage_guard.py)"

python3 - <<'PY'
from pathlib import Path
import os
import subprocess

allowed = {
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py",
    "src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py",
    "src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py",
    "tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py",
    "tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py",
}
base = os.environ["BASE_SHA"]
changed = set(filter(None, subprocess.check_output(["git", "diff", "--name-only", base], text=True).splitlines()))
extra = changed - allowed
assert not extra, f"STOP: changed path outside approved scope: {sorted(extra)}"
print({"changed": sorted(changed), "scope": "OK"})
PY

python3 - <<'PY'
from configs import base
assert base.RISK_LIVE_TRADING_ENABLED is False
assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is False
print("safety_flags=OK")
PY
```

Expected: Ruff and whitespace clean; the Design/Plan hashes have not changed since Task 0; exact changed-path set is a subset of Allowed paths; both safety flags remain false.

### Step 3: Completion audit gate

Only after every prior command passes, invoke `.agent/skills/audit-plan-completion` against this exact Plan and `BASE_SHA`. Require verdict `complete` before any commit or separate deployment decision. A non-complete verdict returns to `.agent/workflows/remediate-completion-audit.md`; it does not authorize an out-of-scope fix.

## Explicit Completion Boundary

Completion means only that the local code and tests implement the approved formal-v2 source-lineage and v1/v2 replay contract. `INV-13` new-root provenance and `INV-17` operational old-root prohibition remain deployment-gated and are not implementation-complete claims. Completion does **not** authorize deployment, resuming a legacy root, creating a new F root, reclassifying UNITREE, calling a result clean evidence, alpha interpretation, paper trading, live trading, or execution.
