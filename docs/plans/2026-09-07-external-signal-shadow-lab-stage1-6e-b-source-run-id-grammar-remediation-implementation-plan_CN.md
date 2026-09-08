# Stage 1.6E-B Source Run-ID Grammar Remediation Implementation Plan

> **For implementation agents:** Execute only after an `Approve` Plan-review verdict, explicit user implementation authorization, and external exact-byte Plan SHA-256 approval. Use the project `execute-approved-plan` workflow task by task. This Plan is not VPS deployment authorization.

**Goal:** Repair the E-B runner's source-run-ID lexical gate so it accepts the deployed Stage 1.6D identifier and rejects undocumented variants, without changing source linkage, E-A authority, semantic parsing, storage, network behavior, or permissions.

**Architecture:** This is a bounded implementation-defect remediation. The Parent Design requires one authorized existing 1.6D source root and exact equality among the CLI argument, `capture_run_contract.json`, and `observer_checkpoint.json`. The 1.6D runbook freezes the real identifier syntax. The remediation changes only the early runner regex and replaces the old synthetic runner test fixture with the real syntax.

**Tech stack:** Python standard library `re`, existing `pytest`, and `ruff`.

## Plan Status And Authority

- Date: 2026-09-07
- Plan status: `draft_for_review`
- Parent E-B Design SHA-256: `752aecff8735f22513483e6bf65ae991386f46ff2ae953da44cd1fe9c5898583`
- Parent E-B Plan SHA-256: `279f729645c9e3691797a92059cab3d212e7b62c0ffbdb49a49947bb712b4da6`
- Pre-remediation deployment baseline: `5b168caad9e2e6553e95bb1a7429196be0892ab3`
- Unapproved candidate commit: `62edd04a5746b101b939da7ab8802aeb0337dcf3`
- Required candidate relation: `62edd04a^ == 5b168caad9e2e6553e95bb1a7429196be0892ab3`
- 1.6D lexical-source runbook: `docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md`
- Frozen lexical-source runbook SHA-256: `81a449e90b34b8284c2fafe0153d665d7dcb6a6257fa0956cf4804e3fc534383`
- Frozen lexical-source runbook Git blob at the documentation baseline: `7b5182c3399661511e3b43718f421b8a299ef267`
- Agent-error-log commit: `070caec007b459c8dd8da61348fd187dc31bf2c0`
- Documentation baseline commit: `bb9260dd0ee3e3022e53c78ea8ace10f4e61c71b`
- Required documentation chain: `070caec007b459c8dd8da61348fd187dc31bf2c0^ == 62edd04a5746b101b939da7ab8802aeb0337dcf3` and `bb9260dd0ee3e3022e53c78ea8ace10f4e61c71b^ == 070caec007b459c8dd8da61348fd187dc31bf2c0`; these two commits contain only the user-owned agent-error log and E-B VPS runbook, respectively.
- `implementation_allowed=false`
- `deployment_allowed=false`
- `runtime_action_allowed=false`

Before execution, an external approval record must provide `EXPECTED_APPROVED_SOURCE_RUN_ID_REMEDIATION_PLAN_SHA256`. The executor must hash these exact Plan bytes; mismatch is `STOP=source_run_id_remediation_plan_bytes_not_authorized`. Do not change `draft_for_review` to `approved`, because approval must not modify frozen Plan bytes.

The candidate commit is not deployment authority. This Plan does not authorize `git push`, VPS synchronization, checkout, session action, root creation, source read, public request, or network test.

## Frozen Source Authority

The only grammar admitted by the E-B production CLI after remediation is:

```python
r"^stage1_6d_live_[0-9]{8}T[0-9]{6}Z$"
```

Authority:

- `docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md:155` defines `RUN_ID="stage1_6d_live_$(date -u +%Y%m%dT%H%M%SZ)"`.
- The lexical-source runbook is an independent frozen authority: its current worktree SHA-256 and Git blob must both equal the values in `Plan Status And Authority` before RED and at final handoff. A later runbook edit is not execution authority for this Plan.
- Parent Design Section 7.2 requires one deployment-authorized run ID naming an existing 1.6D live root.
- Existing `Stage16EBSourceConsumer` remains unchanged and requires `capture_run_contract.run_id == observer_checkpoint.run_id == authorized_run_id`, followed by existing live-mode, profile, and raw-linkage checks.

The following must reject with `invalid_source_run_id_format` before Step-A, source construction, root creation, raw copy, projection, admission, client construction, or network:

```text
stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef
stage1_6b_live_20260904T120000Z
stage1_6b_live_20260904T120000Z_0123456789abcdef0123456789abcdef
stage1_6d_live_source_20260904T120000Z
stage1_6d_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef
stage1_6d_live_20260904T120000Z_ABCDEF
stage1_6d_live_20260904T120000Z/../../x
```

## Allowed Scope

Production code:

- Modify only `scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py`

Tests:

- Modify only `tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py`

Affected but unchanged:

- Parent Design and Parent Plan above.
- 1.6D runbook and all 1.6D writer code.
- `src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_source.py`.
- Every `src/**` path, `configs/base.py`, E-A code, runbooks, deployment authorization records, and `data/**` roots.

Forbidden:

- A second accepted grammar, compatibility adapter, alias, source-root discovery, path parsing, source consumer change, source schema change, E-A change, new configuration, or any permission/risk change.
- VPS access, live/public network test, process/session action, `git push`, `git commit --amend`, destructive Git command, or `ruff --fix`.

## Mandatory STOP Conditions

Stop and return to review if any condition holds:

- Parent Design/Plan bytes differ from their bound SHA-256 values.
- The candidate commit is absent, has a different parent, or modifies a path other than the runner script.
- Correct behavior requires accepting a second grammar, changing 1.6D writer/runbook, changing `Stage16EBSourceConsumer`, or changing the Parent Design.
- A negative fixture reaches Step-A, source construction, root creation, client construction, or network.
- Any test/lint fails, any L0 permission becomes true, any out-of-scope path changes, or the pre-existing user-owned E-B runbook changes.

## Task 0: Freeze Authority And Candidate Baseline

**Files:** none.

1. Freeze Parent bytes, the independent 1.6D lexical source authority, candidate ancestry/content, and the exact implementation worktree/index baseline. The E-B VPS runbook is pre-existing user-owned **tracked** documentation and must remain byte-identical. This Task does not require, create, amend, or authorize a commit.

```bash
set -euo pipefail
BASE_COMMIT=5b168caad9e2e6553e95bb1a7429196be0892ab3
CANDIDATE_COMMIT=62edd04a5746b101b939da7ab8802aeb0337dcf3
DOCUMENTATION_BASELINE_COMMIT=bb9260dd0ee3e3022e53c78ea8ace10f4e61c71b
AGENT_ERROR_LOG_COMMIT=070caec007b459c8dd8da61348fd187dc31bf2c0
PARENT_DESIGN=docs/designs/2026-09-03-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-design_CN.md
PARENT_PLAN=docs/plans/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-implementation-plan_CN.md
USER_OWNED_RUNBOOK=docs/ops/2026-09-06-external-signal-shadow-lab-stage1-6e-b-vps-deployment-and-operations-runbook_CN.md
SOURCE_RUNBOOK=docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md
THIS_PLAN=docs/plans/2026-09-07-external-signal-shadow-lab-stage1-6e-b-source-run-id-grammar-remediation-implementation-plan_CN.md
EXPECTED_SOURCE_RUNBOOK_SHA256=81a449e90b34b8284c2fafe0153d665d7dcb6a6257fa0956cf4804e3fc534383
EXPECTED_SOURCE_RUNBOOK_BLOB=7b5182c3399661511e3b43718f421b8a299ef267
EXPECTED_CANDIDATE_PATCH_SHA256=0f64995f91a19f48f89bfdd5e0cfe95a7d52d20e8ecf144e614b62d70597a8dd
EXECUTION_BASELINE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/stage1_6e_b_source_run_id.XXXXXX")"

test "$(git rev-parse "$CANDIDATE_COMMIT^")" = "$BASE_COMMIT" || { echo 'STOP=candidate_parent_mismatch' >&2; exit 1; }
test "$(git rev-parse "$AGENT_ERROR_LOG_COMMIT^")" = "$CANDIDATE_COMMIT" || { echo 'STOP=agent_error_log_chain_mismatch' >&2; exit 1; }
test "$(git rev-parse "$DOCUMENTATION_BASELINE_COMMIT^")" = "$AGENT_ERROR_LOG_COMMIT" || { echo 'STOP=runbook_chain_mismatch' >&2; exit 1; }
git merge-base --is-ancestor "$DOCUMENTATION_BASELINE_COMMIT" HEAD || { echo 'STOP=documentation_baseline_not_ancestor' >&2; exit 1; }
test "$(shasum -a 256 "$PARENT_DESIGN" | awk '{print $1}')" = 752aecff8735f22513483e6bf65ae991386f46ff2ae953da44cd1fe9c5898583 || { echo 'STOP=parent_design_bytes_mismatch' >&2; exit 1; }
test "$(shasum -a 256 "$PARENT_PLAN" | awk '{print $1}')" = 279f729645c9e3691797a92059cab3d212e7b62c0ffbdb49a49947bb712b4da6 || { echo 'STOP=parent_plan_bytes_mismatch' >&2; exit 1; }
test "$(shasum -a 256 "$SOURCE_RUNBOOK" | awk '{print $1}')" = "$EXPECTED_SOURCE_RUNBOOK_SHA256" || { echo 'STOP=source_runbook_bytes_mismatch' >&2; exit 1; }
test "$(git rev-parse "$DOCUMENTATION_BASELINE_COMMIT:$SOURCE_RUNBOOK")" = "$EXPECTED_SOURCE_RUNBOOK_BLOB" || { echo 'STOP=source_runbook_baseline_blob_mismatch' >&2; exit 1; }
test "$(git hash-object "$SOURCE_RUNBOOK")" = "$EXPECTED_SOURCE_RUNBOOK_BLOB" || { echo 'STOP=source_runbook_worktree_blob_mismatch' >&2; exit 1; }
test "$(git diff --name-only "$BASE_COMMIT" "$CANDIDATE_COMMIT")" = scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py || { echo 'STOP=candidate_scope_mismatch' >&2; exit 1; }
test "$(git diff --name-only "$CANDIDATE_COMMIT" "$DOCUMENTATION_BASELINE_COMMIT")" = $'AGENT_ERROR_LOG_CN.md\ndocs/ops/2026-09-06-external-signal-shadow-lab-stage1-6e-b-vps-deployment-and-operations-runbook_CN.md' || { echo 'STOP=documentation_baseline_scope_mismatch' >&2; exit 1; }
git diff --binary "$BASE_COMMIT" "$CANDIDATE_COMMIT" -- scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py > "$EXECUTION_BASELINE_DIR/candidate.patch"
test "$(shasum -a 256 "$EXECUTION_BASELINE_DIR/candidate.patch" | awk '{print $1}')" = "$EXPECTED_CANDIDATE_PATCH_SHA256" || { echo 'STOP=candidate_contains_unreviewed_runner_change' >&2; exit 1; }
git diff --check "$BASE_COMMIT" "$CANDIDATE_COMMIT"
git diff --quiet || { echo 'STOP=tracked_worktree_not_clean_before_implementation' >&2; exit 1; }
git diff --cached --quiet || { echo 'STOP=git_index_not_clean_before_implementation' >&2; exit 1; }
git ls-files --others --exclude-standard -z > "$EXECUTION_BASELINE_DIR/untracked.z"
python3 - "$EXECUTION_BASELINE_DIR/untracked.z" "$THIS_PLAN" <<'PY'
from pathlib import Path
import sys

paths = [item.decode() for item in Path(sys.argv[1]).read_bytes().split(b"\0") if item]
assert paths in ([], [sys.argv[2]]), {"unexpected_untracked_paths": paths}
PY
git ls-files -s -z | shasum -a 256 > "$EXECUTION_BASELINE_DIR/index.sha256"
git rev-parse HEAD > "$EXECUTION_BASELINE_DIR/implementation_base_sha"
test -f "$USER_OWNED_RUNBOOK" || { echo 'STOP=user_owned_runbook_missing' >&2; exit 1; }
shasum -a 256 "$THIS_PLAN" "$SOURCE_RUNBOOK" "$USER_OWNED_RUNBOOK" > "$EXECUTION_BASELINE_DIR/frozen_worktree_authorities.sha256"
export EXECUTION_BASELINE_DIR
printf '%s\n' "$EXECUTION_BASELINE_DIR"
```

2. Perform the required pre-RED Contract Reality Check before writing a test. Inspect the frozen source runbook, the current runner validation order, and the existing runner test harness. If a discovered fact differs from this Plan, classify it through Rule-12 as `BLOCKED_IMPLEMENTATION_DEFECT`, `BLOCKED_SCOPE_DRIFT`, or `BLOCKED_SPEC_DRIFT`; do not create a local compatibility workaround.

```bash
nl -ba "$SOURCE_RUNBOOK" | sed -n '150,158p'
nl -ba scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py | sed -n '103,180p'
rg -n "_runner_args|test_cli_arg_parsing|run_observer" \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py
```

**Expected:** bound authority matches; candidate is exactly the known one-hunk regex change; the two later commits are documentation-only; the implementation baseline has no tracked or staged changes and at most this frozen Plan as untracked; no runtime command occurs.

**STOP:** any assertion failure, unexpected untracked path, or Contract Reality mismatch. Do not repair baseline, clean the worktree, infer approval, or proceed to RED.

## Task 1: RED Test For Exact 1.6D Grammar

**Files:**

- Modify `tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py`
- Read the 1.6D runbook authority at line 155.

**Consumes:** existing runner `_SOURCE_RUN_ID_RE`; existing `run_observer()` validates the run ID before Step-A and source construction.

**Produces:** lexical and production-call-order proof that each rejected identifier fails with the exact reason before Step-A, E-A gate, storage/supervisor construction, source construction, event-root creation, public-client construction, or network-capable operation.

1. Replace every valid E-B runner fixture ID with this one constant:

```python
CANONICAL_STAGE1_6D_RUN_ID = "stage1_6d_live_20260907T123941Z"
REJECTED_SOURCE_RUN_IDS = (
    "stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef",
    "stage1_6b_live_20260904T120000Z",
    "stage1_6b_live_20260904T120000Z_0123456789abcdef0123456789abcdef",
    "stage1_6d_live_source_20260904T120000Z",
    "stage1_6d_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef",
    "stage1_6d_live_20260904T120000Z_ABCDEF",
    "stage1_6d_live_20260904T120000Z/../../x",
)
```

No E-B runner test may retain `stage1_6b_live_source_...` as a valid argument.

2. Keep a direct lexical test and add this parameterized runner-level negative test beside `test_cli_arg_parsing_and_validations`. Reuse the existing `_runner_args()` helper with absolute placeholder paths and a valid 40-hex deployment commit. Do not create an E-A root, source root, event root, client, or network fixture for this rejection test.

```python
import socket
import urllib.request


def test_source_run_id_grammar_lexical_contract() -> None:
    assert runner_module._SOURCE_RUN_ID_RE.fullmatch(CANONICAL_STAGE1_6D_RUN_ID)
    assert all(
        runner_module._SOURCE_RUN_ID_RE.fullmatch(run_id) is None
        for run_id in REJECTED_SOURCE_RUN_IDS
    )


@pytest.mark.parametrize(
    "run_id",
    REJECTED_SOURCE_RUN_IDS,
)
def test_invalid_source_run_id_fails_before_runtime_side_effects(
    run_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def forbidden(name: str):
        def _forbidden(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"forbidden runtime side effect: {name}")
        return _forbidden

    monkeypatch.setattr(runner_module, "get_vps_step_a_projection", forbidden("step_a"))
    monkeypatch.setattr(runner_module, "validate_e_a_runtime_gate", forbidden("e_a_gate"))
    monkeypatch.setattr(runner_module, "Stage16EBStorageGuard", forbidden("storage_guard"))
    monkeypatch.setattr(runner_module, "Stage16EBSupervisor", forbidden("supervisor_or_root"))
    monkeypatch.setattr(runner_module, "Stage16EBSourceConsumer", forbidden("source_consumer"))
    monkeypatch.setattr(runner_module, "Stage16EBPublicClient", forbidden("public_client"))
    monkeypatch.setattr(socket, "create_connection", forbidden("network_socket"))
    monkeypatch.setattr(urllib.request, "urlopen", forbidden("network_urlopen"))

    args = _runner_args(
        e_a_root=Path("/tmp/e_a"),
        source_root=Path("/tmp/source"),
        source_run_id=run_id,
        supervisor_root=Path("/tmp/supervisor"),
        events_root=Path("/tmp/events"),
        shared_lock=Path("/tmp/shared.lock"),
    )
    with pytest.raises(ValueError) as exc_info:
        run_observer(args)
    assert str(exc_info.value) == f"invalid_source_run_id_format: {run_id}"
    assert calls == []
```

3. Run before production change:

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py::test_source_run_id_grammar_lexical_contract \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py::test_invalid_source_run_id_fails_before_runtime_side_effects
```

**Expected RED:** fail because `62edd04a` accepts at least one undocumented variant. For an admitted bad value, the production-call-order test must fail by reaching a `forbidden(...)` trap instead of returning the exact `invalid_source_run_id_format` error.

4. Run the per-task scope and scanner gate after RED test creation. The scanner process exit code is authoritative; do not hide it behind a pipeline. Any warning must be recorded in the Task Execution Report's Scanner Disposition Ledger before Task 2.

```bash
BASE_SHA="$(cat "$EXECUTION_BASELINE_DIR/implementation_base_sha")"
test "$(git ls-files -s -z | shasum -a 256 | awk '{print $1}')" = "$(awk '{print $1}' "$EXECUTION_BASELINE_DIR/index.sha256")" || { echo 'STOP=task1_git_index_changed' >&2; exit 1; }
python3 - "$BASE_SHA" <<'PY'
import subprocess
import sys

changed = set(subprocess.check_output(
    ["git", "diff", "--name-only", sys.argv[1]], text=True
).splitlines())
assert changed == {
    "tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py",
}, {"unexpected_or_missing_paths": sorted(changed ^ {
    "tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py",
})}
PY
git diff --cached --name-only "$BASE_SHA"
git status --short --untracked-files=all
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/task1-scanner.txt" 2>&1; then
  SCANNER_RC=0
else
  SCANNER_RC=$?
fi
cat "$EXECUTION_BASELINE_DIR/task1-scanner.txt"
test "$SCANNER_RC" -eq 0 || { echo 'STOP=task1_anti_shortcut_scan_nonzero' >&2; exit 1; }
```

**STOP:** the lexical or runner test needs a source root, Step-A, client, root, or network fixture; any rejected ID reaches a trap; scanner returns nonzero; or a changed path is outside the runner test file.

## Task 2: Minimal Runner Grammar Correction

**Files:**

- Modify `scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py:37-39`
- Modify `tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py`

**Consumes:** Task 1 fixture; unchanged Parent exact source equality checks.

**Produces:** a CLI gate accepting only the runbook-defined 1.6D identifier before Step-A/source/client operation.

1. Replace the candidate regex with exactly:

```python
_SOURCE_RUN_ID_RE = re.compile(r"^stage1_6d_live_[0-9]{8}T[0-9]{6}Z$")
```

Do not add helper functions, aliases, optional groups, 1.6B compatibility, suffixes, calendar parsing, or changes to `run_observer()` ordering.

2. Run the Task 1 test again.

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py::test_source_run_id_grammar_lexical_contract \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py::test_invalid_source_run_id_fails_before_runtime_side_effects
```

**Expected GREEN:** `8 passed`.

3. Prove the unchanged downstream equality/profile/raw-linkage boundary.

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py
```

**Expected:** all tests pass; existing contract/checkpoint mismatch, profile, capture-mode, and raw-linkage rejection tests remain unchanged.

4. Run the per-task scope and scanner gate after the production correction. The only task-induced changed paths may now be the runner and its test file.

```bash
BASE_SHA="$(cat "$EXECUTION_BASELINE_DIR/implementation_base_sha")"
test "$(git ls-files -s -z | shasum -a 256 | awk '{print $1}')" = "$(awk '{print $1}' "$EXECUTION_BASELINE_DIR/index.sha256")" || { echo 'STOP=task2_git_index_changed' >&2; exit 1; }
python3 - "$BASE_SHA" <<'PY'
import subprocess
import sys

allowed = {
    "scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py",
}
changed = set(subprocess.check_output(
    ["git", "diff", "--name-only", sys.argv[1]], text=True
).splitlines())
assert changed == allowed, {"unexpected_or_missing_paths": sorted(changed ^ allowed)}
PY
if GIT_CONFIG_GLOBAL=/dev/null python3 .agent/tools/anti_shortcut_scan.py \
  --base-sha "$BASE_SHA" > "$EXECUTION_BASELINE_DIR/task2-scanner.txt" 2>&1; then
  SCANNER_RC=0
else
  SCANNER_RC=$?
fi
cat "$EXECUTION_BASELINE_DIR/task2-scanner.txt"
test "$SCANNER_RC" -eq 0 || { echo 'STOP=task2_anti_shortcut_scan_nonzero' >&2; exit 1; }
```

Record every Task 2 scanner warning in the Task Execution Report's Scanner Disposition Ledger before Task 3.

**STOP:** any requirement to modify `Stage16EBSourceConsumer`, source artifacts, source profile, raw linkage, or Parent authority documents; any scanner nonzero result; any index mutation; or an out-of-scope changed path.

## Task 3: Scope, Safety, And Handoff Proof

**Files:** none beyond Tasks 1-2.

1. Run E-B regression, lint, and L0 proof:

```bash
PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py \
  tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py
.venv/bin/ruff check \
  scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from configs import base
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import stage1_6e_b_permissions
assert base.RISK_LIVE_TRADING_ENABLED is False
assert all(value is False for value in stage1_6e_b_permissions().values())
print("stage1_6e_b_source_run_id_remediation_l0=PASS")
PY
```

**Expected:** every test and lint check passes; L0 proof prints `PASS`.

2. Verify the final **working-tree and index** scope, then re-verify every frozen authority. Do not create, amend, stage, or require a commit for this proof. `IMPLEMENTATION_BASE_SHA` is the exact `HEAD` recorded in Task 0; the Plan, source runbook, and user-owned E-B runbook are pre-existing authority inputs, not task-induced implementation paths.

```bash
set -euo pipefail
: "${EXECUTION_BASELINE_DIR:?STOP=execution_baseline_dir_missing}"
IMPLEMENTATION_BASE_SHA="$(cat "$EXECUTION_BASELINE_DIR/implementation_base_sha")"
THIS_PLAN=docs/plans/2026-09-07-external-signal-shadow-lab-stage1-6e-b-source-run-id-grammar-remediation-implementation-plan_CN.md
SOURCE_RUNBOOK=docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md
USER_OWNED_RUNBOOK=docs/ops/2026-09-06-external-signal-shadow-lab-stage1-6e-b-vps-deployment-and-operations-runbook_CN.md
EXPECTED_SOURCE_RUNBOOK_SHA256=81a449e90b34b8284c2fafe0153d665d7dcb6a6257fa0956cf4804e3fc534383
EXPECTED_SOURCE_RUNBOOK_BLOB=7b5182c3399661511e3b43718f421b8a299ef267

git diff --check "$IMPLEMENTATION_BASE_SHA"
git diff --cached --check "$IMPLEMENTATION_BASE_SHA"
test "$(git ls-files -s -z | shasum -a 256 | awk '{print $1}')" = "$(awk '{print $1}' "$EXECUTION_BASELINE_DIR/index.sha256")" || { echo 'STOP=git_index_changed' >&2; exit 1; }
python3 - "$IMPLEMENTATION_BASE_SHA" "$EXECUTION_BASELINE_DIR/untracked.z" <<'PY'
import subprocess
import sys
from pathlib import Path

allowed = {
    "scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py",
    "tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py",
}
changed = set(subprocess.check_output(
    ["git", "diff", "--name-only", sys.argv[1]], text=True
).splitlines())
assert changed == allowed, {"unexpected_or_missing_paths": sorted(changed ^ allowed)}
baseline_untracked = Path(sys.argv[2]).read_bytes()
current_untracked = subprocess.check_output(
    ["git", "ls-files", "--others", "--exclude-standard", "-z"]
)
assert current_untracked == baseline_untracked, "untracked_paths_changed"
print("stage1_6e_b_source_run_id_remediation_scope=PASS")
PY
shasum -a 256 -c "$EXECUTION_BASELINE_DIR/frozen_worktree_authorities.sha256"
test "$(shasum -a 256 "$SOURCE_RUNBOOK" | awk '{print $1}')" = "$EXPECTED_SOURCE_RUNBOOK_SHA256" || { echo 'STOP=source_runbook_bytes_changed' >&2; exit 1; }
test "$(git hash-object "$SOURCE_RUNBOOK")" = "$EXPECTED_SOURCE_RUNBOOK_BLOB" || { echo 'STOP=source_runbook_blob_changed' >&2; exit 1; }
```

**Expected:** scope proof prints `PASS`; the index snapshot, untracked baseline, Plan bytes, source-runbook bytes/blob, and user-owned E-B runbook hash match their Task 0 baseline.

**STOP:** a task-induced path is not exactly one of the two allowed files; the index or untracked baseline changes; an authority hash/blob differs; L0 fails; or test/lint fails.

3. Hand off to a different session, subagent, or user for a Blind-First independent read-only completion audit. Provide only: this Plan's external approval SHA, Parent Design/Plan/source-runbook SHA values, `IMPLEMENTATION_BASE_SHA`, `EXECUTION_BASELINE_DIR`, the two-file implementation whitelist, and any known unresolved blocker. Do not provide a self-certifying completion summary. The auditor must independently verify the final grammar, all seven runner-level negative fixtures, source-linkage regressions, index/worktree scope, and absence of VPS/runtime action.

A separate VPS deployment authorization must bind the final reviewed commit and preserve the already-running 1.6D session/check-out boundary. No deployment may occur from this Plan.

## Completion Matrix

| Requirement | Task | Mechanical proof | STOP |
|---|---:|---|---|
| Parent authority unchanged | 0 | exact SHA-256 | authority bytes mismatch |
| Frozen lexical authority unchanged | 0, 3 | source runbook SHA-256 + Git blob | source-runbook mismatch |
| Candidate is only known defect | 0 | parent, one-file, exact-patch SHA | candidate scope/content mismatch |
| Real 1.6D ID accepted | 1-2 | canonical lexical fixture | valid ID rejected |
| Expanded/legacy IDs rejected before side effects | 1-2 | lexical test plus seven `run_observer()` traps | any variant accepted or any trap reached |
| Exact source linkage retained | 2 | existing source regressions | contract/checkpoint/linkage failure |
| Anti-shortcut compliance | 1-2 | scanner RC=0; warning ledger | scanner nonzero or undispositioned warning |
| L0 unchanged | 3 | direct assertions | any true permission/risk |
| Scope and index closed | 3 | exact two-file worktree diff, index hash, untracked baseline, authority hashes | extra path/index/untracked/authority mutation |
| No runtime action | 0-3 | no VPS/network command | runtime/deployment action |

## Self-Review

- This Plan changes one production lexical gate and one existing runner test file only.
- It does not redesign Parent E-B, alter 1.6D, accept a compatibility grammar, or change source equality.
- Every authority edge maps to a task, mechanical proof, and fail-closed STOP condition.
- Plan approval, implementation approval, completion audit, and VPS deployment authorization remain separate.
