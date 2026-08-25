# Stage 1.6D VPS Live Source Observation Runbook Governance Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task only after plan review and explicit user approval.

**Goal:** 将已批准的 Stage 1.6D 部署授权契约落为唯一当前 runbook 与导航链接，不启动 VPS、不修改生产代码，也不改变任何交易或研究权限。

**Architecture:** 新 runbook 只把既有 runner、storage guard 和 source-profile probe 的已实现门禁组织为 target-local、fail-closed 的操作顺序。旧 2026-08-19 checklist 保留为历史证据；路线地图和 current document index 只导航到新 runbook，避免把 UNITREE/1.5G 历史条目重新用作当前部署 gate。

**Tech Stack:** Markdown、zsh/bash、Python 3、现有 `.venv`、pytest、tmux；无新增依赖、无代码变更。

**Plan Status:** `draft_for_review`  
**Approved Design:** `docs/designs/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md`  
**Planning Baseline:** `c98801bb99e7e0d9d472b9684db97a12f442bdb6`  
**Deployment Authorization:** `false`  
**Live/Paper/Execution Authorization:** `false`

---

## Allowed Change Scope

Allowed implementation paths:
- none

Allowed verification paths:
- none

Allowed documentation paths:
- `docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md` (create)
- `docs/project-status/2026-08-24-stage1-6-futures-delisting-route-map_CN.md` (modify navigation only)
- `docs/project-status/current-document-index_CN.md` (modify Stage 1.6 authority entry and generated date only)
- `docs/plans/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook-governance-implementation-plan_CN.md` (this plan; review-status metadata only)

Allowed generated/runtime artifacts:
- none; target preflight transcripts, probe attestations, live roots and tmux sessions are explicitly out of scope for this docs-only execution

Affected but unchanged:
- `docs/designs/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md`
  - compatibility evidence: this Plan maps INV-01--INV-11 without changing the approved Design bytes
- `docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md`
  - compatibility evidence: retain it as historical preflight evidence; new runbook links to it but does not inherit UNITREE/1.5G as gates
- `scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py`
- `scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py`
- `src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py`
- `configs/base.py`
- `tests/research/external_signal_shadow/test_stage1_6b_canonical_source_{client,models,observer,storage}.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_6b_{source_profile_probe,live_source_observer}.py`
  - compatibility evidence: the runbook invokes existing CLI/config/test behavior only; no implementation or test changes are allowed

Forbidden:
- Any mutation outside the allowed documentation paths
- Any mutation of `src/`, `scripts/`, `configs/`, tests, existing data roots or the historical checklist
- VPS SSH, `tmux`, probe, runner, `--resume`, data deletion, syncing, deployment or process control during this Plan
- Any trade, paper, replay, market-data, alpha or execution authorization change
- Full-repository formatting/autofix, destructive cleanup, or unscoped `git` recovery commands

## Preconditions and Provenance Gate

Before editing documentation, run from the repository root:

```bash
set -euo pipefail
export BASE_SHA="$(git rev-parse HEAD)"
test "$BASE_SHA" = "c98801bb99e7e0d9d472b9684db97a12f442bdb6"
git status --short --untracked-files=all
shasum -a 256 docs/designs/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md
```

Expected:

```text
BASE_SHA=c98801bb99e7e0d9d472b9684db97a12f442bdb6
```

The approved Design may be pre-existing untracked work before this Plan is executed. Record its SHA-256 and do not change it. Any different `BASE_SHA`, unexpected code/config/script/test mutation, or Design SHA change is a STOP condition.

For this reviewed draft, the approved Design SHA-256 is:

```text
5070644d57e789ebf9c422e5a9022c58c8a606c1074cab7b849abc22f61bf202
```

## Invariant Map

| Design invariant | Plan task | Verification evidence |
|---|---|---|
| INV-01 commit/environment binding | Task 1 | target-local interpreter/import and six-file Stage 1.6B test gate in runbook |
| INV-02 fresh target attestation | Task 1 | dynamic selected-catalog `code` extraction, same-probe membership check, target-local SHA/path gate |
| INV-03 root/writer exclusivity | Task 1 | fresh-root/session/writer check plus separately scoped resume procedure |
| INV-04 shared-host safety | Task 1 | 8 GiB, lock, root family and active/absent 1.5D/F branches |
| INV-05 log-output hygiene | Task 1 | no stdout/stderr redirection into live root |
| INV-06 read-only authority | Task 1 | explicit flag and target master-switch assertion |
| INV-07 bounded runtime | Task 1 | 300-second/7-day command contract; test bounds prohibited for production |
| INV-08 terminal/sealing | Task 1 | complete/failure terminal and seal inspection branches |
| INV-09 no cross-epoch write | Task 1 | new root per epoch and no-resume terminal/sealed rules |
| INV-10 no research overclaim | Task 1 | zero-authority assertion and post-epoch limitations |
| INV-11 fail closed | Tasks 1 and 3 | every non-PASS branch is STOP/no-start; static runbook contract check |

### Task 1: Create The Current Stage 1.6D Runbook

**Design invariants:** INV-01 through INV-11  
**Files:**
- Create: `docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md`
- Read only: all affected-but-unchanged code/config/test files listed in Allowed Change Scope
- Do not modify: legacy checklist, source, scripts, configs, tests, data or VPS

**Step 1: Write the runbook header and explicit authority boundary.**

Include exact metadata:

```text
status = current_runbook_draft
scope = Stage 1.6D VPS live source observation only
code_change = false
deployment_authorization = false
RISK_LIVE_TRADING_ENABLED = false
```

Link the approved 1.6D Design, route map, legacy checklist, live runner and probe runner. State that this runbook is not a start authorization: a named target transcript and separate user authorization are still mandatory.

**Step 2: Add target preflight commands in mandatory order.**

The runbook must provide copyable commands, each wrapped in `set -euo pipefail`, for:

1. target `DEPLOY_COMMIT` identity, clean worktree and target `.venv` import/master-switch assertion;
2. only these six Stage 1.6B test files:

```text
tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py
tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py
tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py
tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py
tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py
tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py
```

3. target-local current selected-catalog `code` extraction; it must fail if the selected Delisting catalog is absent/empty or the resulting ID is not 32 hex;
4. probe invocation with the dynamically captured ID, then attestation schema/profile/catalog/header/SHA/path/timestamp checks;
5. active-or-absent Stage 1.5D/F co-tenancy branch, host free space >= 8 GiB, shared-lock usability, no active 1.6D writer, and fresh root/session absence.

Do not add a command that fetches live market data other than the existing source profile probe. Do not use a historic hardcoded article ID, reuse a local attestation, delete any lock file, or use a broad test glob.

**Step 3: Add the only permitted production start contract.**

Specify one target command shape that:

- invokes `.venv/bin/python scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py`;
- passes the target-local attestation path, `--live-public-readonly`, a fresh `--run-id` and `--project-root "$PWD"`;
- starts inside an explicitly named tmux session;
- does not pass `--resume`, `--max-polls`, or a short `--max-seconds` for the first production epoch;
- does not redirect stdout/stderr into `data/external_signal_shadow/stage1_6b/live_observation/<run_id>`.

The command must remain a documented post-authorization action, not be executed while implementing this Plan. State that the default runner epoch is bounded by existing configuration at 7 days and uses the existing 300-second sequential poll interval.

**Step 4: Add health, terminal, seal, interruption and resume branches.**

Include copyable inspection commands and exact STOP actions for:

- healthy running state: one live runner, matching root/session/run ID, fresh checkpoint/summary, no storage/blocker failure;
- complete epoch: exact `status=complete`, `terminal_reason=epoch_complete`, then a sealed export;
- failure terminal: preserve root, verify no sealed export, do not retry with aliases;
- interruption: terminal and sealed artifacts absent; preserve evidence; no fabricated terminal;
- resume: only same root, same attestation SHA, no terminal/seal, and reconciliation before client/network; this remains a separately authorized recovery action;
- any failed gate: no start/no resume/no delete, record transcript and stop.

State explicitly that an observation/sealed export does not set PIT, market-data, replay, signal, paper, live, execution or alpha permissions to true.

**Step 5: Run a static runbook contract check.**

Run a local non-network Python assertion that verifies the runbook contains all required command and safety literals. Example shape:

```bash
python3 - docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text(encoding="utf-8")
required = (
    "--live-public-readonly",
    "stage1_6d_target_environment=PASS",
    "test_run_stage1_6b_source_profile_probe.py",
    "test_run_stage1_6b_live_source_observer.py",
    "binance_public_web_bapi_en_delisting_catalog_v2",
    "8 GiB",
    ".stage1_5_storage_guard.lock",
    ".stage1_6b_writer.lock",
    "terminal_reason=epoch_complete",
    "RISK_LIVE_TRADING_ENABLED is False",
    "不得重定向至 live root",
    "不得硬编码历史公告 ID",
)
missing = [item for item in required if item not in text]
assert not missing, missing
for forbidden in ("deployment_authorization = true", "live_trading_allowed = true"):
    assert forbidden not in text, forbidden
print({"stage1_6d_runbook_contract": "PASS"})
PY
```

Expected: `{'stage1_6d_runbook_contract': 'PASS'}`. This validates documentation only; it must not connect to the VPS or public endpoints.

### Task 2: Update Current Navigation Without Rewriting Historical Evidence

**Design invariants:** INV-08, INV-09, INV-10  
**Files:**
- Modify: `docs/project-status/2026-08-24-stage1-6-futures-delisting-route-map_CN.md`
- Modify: `docs/project-status/current-document-index_CN.md`
- Do not modify: `docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md`

**Step 1: Update the route map's 1.6D authority chain.**

Add the approved Design and new current runbook to the Stage 1.6D navigation. Retain the old checklist as `historical_preflight_reference`, not as the active deployment procedure. Keep 1.6D status `not_deployed` and preserve the statement that actual deployment needs target transcript plus explicit user authorization.

**Step 2: Update the current document index minimally.**

Change only the Stage 1.6 Futures Delisting current authority row and its Stage 1.6 chain description to link:

```text
1.6D deployment authorization Design -> 1.6D current runbook -> target preflight transcript -> explicit user deployment authorization
```

Update the index generated date to 2026-08-25. Do not rewrite stale historical runtime snapshots, Stage 1.5 deployment statements, document counts, or unrelated route statuses.

**Step 3: Verify navigation targets and preservation.**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
paths = {
    "docs/project-status/2026-08-24-stage1-6-futures-delisting-route-map_CN.md": (
        "2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md",
        "2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md",
        "historical_preflight_reference",
        "not_deployed",
    ),
    "docs/project-status/current-document-index_CN.md": (
        "2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md",
        "2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md",
        "target preflight transcript",
        "explicit user deployment authorization",
    ),
    "docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md": (
        "UNITREE 观测已完成",
        "Stage 1.5G 复核完毕",
    ),
}
for name, expected in paths.items():
    text = Path(name).read_text(encoding="utf-8")
    missing = [item for item in expected if item not in text]
    assert not missing, {name: missing}
print({"stage1_6d_navigation_and_history": "PASS"})
PY
```

Expected: `{'stage1_6d_navigation_and_history': 'PASS'}`.

### Task 3: Scope, Safety and Documentation Completion Gate

**Design invariants:** INV-01, INV-05, INV-06, INV-10, INV-11  
**Files:**
- Verify only: all paths in Allowed Change Scope

**Step 1: Confirm no deployment command was run by this docs-only execution.**

Inspect the shell transcript and git diff. There must be no new `data/external_signal_shadow/stage1_6b/live_observation/` root, no new attestation, no tmux session, no remote command, and no changes outside the three documentation deliverables plus this Plan.

**Step 2: Check file scope and whitespace.**

Run:

```bash
git diff --check
python3 - <<'PY'
import subprocess
allowed = {
    "docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md",
    "docs/project-status/2026-08-24-stage1-6-futures-delisting-route-map_CN.md",
    "docs/project-status/current-document-index_CN.md",
    "docs/plans/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook-governance-implementation-plan_CN.md",
}
protected_preexisting = {
    "docs/designs/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md":
        "5070644d57e789ebf9c422e5a9022c58c8a606c1074cab7b849abc22f61bf202",
}
changed = set(filter(None, subprocess.check_output(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"], text=True
).replace("\x00", "").splitlines()))
paths = {line[3:] for line in changed if len(line) >= 4}
for path, expected_sha256 in protected_preexisting.items():
    actual_sha256 = __import__("hashlib").sha256(open(path, "rb").read()).hexdigest()
    assert actual_sha256 == expected_sha256, {"protected_path_changed": path}
assert paths <= allowed | set(protected_preexisting), {"unexpected_paths": sorted(paths - allowed - set(protected_preexisting))}
print({"stage1_6d_docs_scope": "PASS", "paths": sorted(paths)})
PY
```

Expected: `stage1_6d_docs_scope=PASS` and only allowed documentation paths plus the SHA-256-verified pre-existing Design. The Design is never an implementation allowlist path; do not edit it during execution.

**Step 3: Request completion audit before any commit or VPS action.**

Invoke `.agent/skills/audit-plan-completion` against the approved Design, this Plan and documentation diff. Required verdict: `complete`. A `complete` docs audit does not authorize target preflight or deployment.

## Completion Criteria

- New runbook contains all INV-01--INV-11 command contracts and STOP paths.
- Route map and document index point to the new runbook while preserving the historical checklist unchanged.
- No code/config/test/data/VPS mutation occurred.
- Static checks and `git diff --check` pass.
- Completion audit verdict is `complete`.
- User separately decides whether and when to commit the documentation change; deployment remains unauthorized.
