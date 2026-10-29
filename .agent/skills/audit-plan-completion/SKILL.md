---
name: audit-plan-completion
description: Use after executing an approved implementation plan, refactor, or bugfix and before declaring completion, committing, merging, or deploying.
---

# Audit Plan Completion

## Purpose

Verify with fresh, independent evidence that an approved Implementation Plan was implemented completely, verified honestly, and kept strictly within its `Allowed Change Scope`.

**REQUIRED SUB-SKILL:** Use `verification-before-completion` for fresh command output. Reference [`.agent/rules/L1_Engineering_Process.md`](../../rules/L1_Engineering_Process.md) as the single engineering process authority.

## Normative Requirements vs. Factual Evidence

Instead of a rigid multi-tier ceremony, the auditor evaluates two distinct dimensions:

1. **Normative Requirements (What Must Be True)**:
   - The approved Design, approved Implementation Plan, `Allowed Change Scope`, and explicit user authorization define the required behavior, invariants, scope, and permitted actions.
   - If workspace reality contradicts the approved Design/Plan contract, classify it per `L1 Rule 16` (alias `Old L1 Rule 12`) as `BLOCKED_SPEC_DRIFT` and return `blocked` rather than silently reinterpreting the contract.
2. **Factual Evidence (What Is Proven in the Workspace)**:
   - Actual source code, production runner wiring, real output bytes/hashes, independent negative/fail-closed checks, canonical upstream cross-boundary fixtures (`L1 Rule 15`), static AST diff scans (`anti_shortcut_scan.py`), and fresh verification command outputs.
   - Executor verbal claims, self-congratulatory summaries, or passing tests that bypass production call paths or use fabricated cross-boundary mocks are **never** sufficient evidence on their own.

## Auditor Read-Only & Delivery Invariant

- **Strictly Read-Only**: The auditor must **not** modify, stage, commit, checkout, reset, clean, or delete any repository file, fixture, runtime evidence root, or baseline record. Any negative probing by the auditor must run strictly in isolated temporary directories (`/tmp` or `mktemp -d`) without touching production roots or triggering unauthorized network/deployment actions.
- **Default Report Delivery**: Deliver the structured audit report directly in the audit reply (or to an existing path only if explicitly authorized in the approved Plan's `Allowed documentation paths`). Do **not** build a dedicated audit recorder subsystem or write unapproved files into the workspace.

## Verdicts & Authority Boundary

- **`complete`**: every Task, Design invariant (`INV-*`), compatibility obligation, and verification gate is satisfied with fresh factual evidence, and all changes fall within `Allowed Change Scope` (or pre-existing baseline).
- **`incomplete`**: required implementation, production wiring, test coverage, expected-value independence, or documentation is missing or partially done. (Never invent hybrid verdicts such as `complete_with_required_fixes`.)
- **`blocked`**: a `P0` safety or scope violation occurred, mandatory verification failed, `BLOCKED_SPEC_DRIFT` / `BLOCKED_SCOPE_DRIFT` is unresolved, or missing pre-execution provenance prevents honest scope accounting.

> **Authority Isolation (`L1` §4.4)**: A `complete` verdict proves **only** that the workspace implementation satisfies the currently approved Plan scope. It **never** automatically grants permission for `git commit`, `git push`, merge, deployment, SSH/remote execution, runtime service startup, paper trading, or live trading (`RISK_LIVE_TRADING_ENABLED` must remain `False`).

## Required Inputs

1. Approved Design and Implementation Plan (with SHA-256 and `Allowed Change Scope`).
2. Pre-execution `BASE_SHA` and baseline snapshot (`git status --short --untracked-files=all`, worktree/index patches, and untracked file SHA-256 list).
3. Current workspace state and objective execution notes.

If the pre-execution snapshot is missing and dirty/untracked files exist outside the Plan scope, mark ownership as `scope_provenance_uncertain` and return `blocked` (never auto-revert or guess ownership).

## Audit Flow

### 1. Capture the Full Change Set (Committed, Staged, Unstaged & Untracked)

Run and inspect all four views against `BASE_SHA`:

```bash
git merge-base --is-ancestor "$BASE_SHA" HEAD
git status --short --untracked-files=all
git diff --name-status "$BASE_SHA"
git diff --cached --name-status "$BASE_SHA"
git diff --name-status
git ls-files --others --exclude-standard
```

Inspect both index (`--cached`) and worktree diffs so a staged change reversed in the worktree cannot hide from review. Compare against the pre-execution baseline so pre-existing user edits are preserved and neither reverted nor misattributed.

### 2. Enforce `Allowed Change Scope` & Drift Rules (`L1 Rule 16`)

Classify every changed or newly untracked path against `Allowed implementation paths`, `Allowed verification paths`, `Allowed documentation paths`, `Allowed generated/runtime artifacts`, `Affected but unchanged`, and `Forbidden`:

- Any task-induced modification or new file outside `Allowed Change Scope` is a `P0` scope blocker (`blocked`).
- If a bounded scope supplement (`BLOCKED_SCOPE_DRIFT`) was approved during execution/remediation, verify both the user's explicit approval and the **Mandatory Identity & Evidence Check** (`L1` §3.2): confirm whether any source bundle hash, authorization binding, `RUN_ID`, or receipt depended on the prior file set/Plan hash, and verify that affected bindings were re-validated rather than reused stale.

### 3. Map Tasks & Invariants to Factual Evidence

Build an explicit verification matrix:

```text
Task / Invariant | Normative Requirement | Factual Workspace Evidence (file:line / hash / cmd) | Status
```

Check that each invariant is backed by the appropriate evidence class:
- **Code / Runtime behavior**: production `src/` or `scripts/` `file:line` plus runner wiring (a helper tested in isolation but never called by its target entry point is `incomplete`).
- **Config / Safety invariants**: exact `configs/base.py` constant and `RISK_LIVE_TRADING_ENABLED is False`.
- **Documentation / Governance deliverables**: exact file existence, normative consistency, and link/reference integrity (do not demand fake Python unit tests for pure documentation tasks).

### 4. Audit Test Quality, Fixture Provenance & Consequence-Driven `Rule 17`

Verify alignment with [`.agent/rules/L1_Engineering_Process.md`](../../rules/L1_Engineering_Process.md):

1. **Public Interface & Independent Expected Values (`L1` §2 Rule 4)**:
   - Confirm behavioral tests assert public interfaces using expected values derived independently from rules/formulas rather than copying implementation output into `assert`.
2. **Fixture Grading (`L1 Rule 15`, alias `Old L1 Rule 11`)**:
   - Single-module internal pure logic and fault-injection tests may legitimately use minimal local synthetic inputs (do **not** reject internal unit tests for using synthetic tuples/dicts).
   - Positive cross-module/cross-boundary tests must derive from canonical upstream constructors/serializers or artifact bytes validated by upstream strict loaders; hand-crafted cross-boundary mock dicts or copied foreign attestations have zero evidentiary value (`incomplete` or `blocked`).
3. **Consequence-Driven `Rule 17` Verification (`L1` §3.3)**:
   - Trigger independent artifact schema verifier checks (`scripts/governance/verify_artifact_schema.py --profile <profile_id> --artifact-root <relative_root>`) and receipt hash bindings **only** when required by `L1 Rule 17` and the current task's frozen contract: i.e., when the artifact directly grants operational authority, controls trading/capital admission, or underpins an irreversible migration—or when the task reuses an existing frozen Rule 17 profile.
   - For ordinary recomputable or exploratory cross-stage research outputs, verify that the declared structural checks and independent semantic evidence are satisfied without demanding a duplicate standalone verifier script; verify they are not mislabeled as passing a legacy full Rule 17 profile.
   - Do **not** demand a standalone `Rule 17` verifier for exploratory statistics, human-readable reports, or internal module changes that do not cross formal artifact boundaries.

### 5. Recheck Shared Topology & Run Fresh Verification

1. When shared functions, schemas, JSON/JSONL keys, or CLI flags changed, verify consumer compatibility with `rg` and source inspection (using `graphify query/path` when applicable).
2. Run the Plan's verification commands plus repository hygiene and safety checks:
   ```bash
   git diff --check "$BASE_SHA"
   git diff --cached --check "$BASE_SHA"
   python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
   PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -c 'from configs import base; assert base.RISK_LIVE_TRADING_ENABLED is False'
   ```
   - Any non-zero exit from `anti_shortcut_scan.py` is `blocked`; any `WARNING` must have a valid technical justification proving it does not mask a contract error.

## Output Format

1. **Verdict**: `complete` | `incomplete` | `blocked` (with explicit note that `complete` grants no commit/deploy/runtime/trading authority).
2. **Findings**: Ordered `P0` / `P1` / `P2` with exact `file:line` or command output evidence.
3. **Scope Accounting Table**: Allowed vs. Actual vs. Pre-existing vs. Unapproved / Uncertain.
4. **Task & Invariant Evidence Matrix**.
5. **Fresh Verification Log**: Commands run, exit codes (`RC`), and key output.
6. **Required Remediation or Residual Risks**.

See [`PRESSURE_TESTS.md`](PRESSURE_TESTS.md) for audit verification scenarios.
