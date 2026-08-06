---
name: audit-plan-completion
description: Use after executing an approved implementation plan, refactor, or bugfix and before declaring completion, committing, merging, or deploying.
---

# Audit Plan Completion

## Purpose

Prove that the approved Plan was fully implemented, verified, and kept within its allowed scope. Passing tests alone is not completion.

**REQUIRED SUB-SKILL:** Use `verification-before-completion` for fresh command evidence. For significant code changes, use `requesting-code-review` before the final verdict.

## Verdicts

- **complete**: every Task, invariant, Done Definition item, compatibility obligation, and verification gate passes; scope is fully accounted for.
- **incomplete**: required implementation, wiring, serialization, tests, or documentation is missing. Any mandatory fix means incomplete.
- **blocked**: a P0 safety/scope failure exists, mandatory verification fails, or missing provenance/evidence prevents an honest audit.

Only `complete` permits a completion claim, commit, merge, or deployment.

## Required Inputs

1. Approved Design and Implementation Plan, including `Allowed Change Scope`.
2. `BASE_SHA` from immediately before execution.
3. Pre-execution `git status --short --untracked-files=all` snapshot, plus a patch or SHA-256 for every pre-existing dirty/untracked path that execution may overlap.
4. Current worktree and fresh verification results.

If the pre-execution snapshot is missing, label ownership as `scope_provenance_uncertain`. Do not attribute, revert, or overwrite an existing change. Return `blocked` when that uncertainty prevents full scope accounting.

## Audit Flow

### 1. Capture the Entire Change Set

Verify the base and inspect committed, staged, unstaged, and untracked files:

```bash
git merge-base --is-ancestor "$BASE_SHA" HEAD
git status --short --untracked-files=all
git diff --name-status "$BASE_SHA"
git diff --cached --name-status "$BASE_SHA"
git diff --name-status
git ls-files --others --exclude-standard
```

Inspect both index and worktree diffs. A staged change can be reversed only in the worktree, making the final file match `BASE_SHA` while the index still differs. Do not use `<base>...HEAD` as the only source; it misses current worktree and untracked changes.

Never run `git checkout`, `git reset`, `git clean`, or any other destructive remediation automatically. Report exact paths and ownership evidence; the user decides whether to preserve, split, or revert them.

### 2. Enforce Allowed Change Scope

Classify every changed path against:

- `Allowed implementation paths`
- `Allowed verification paths`
- `Allowed documentation paths`
- `Allowed generated/runtime artifacts`
- `Affected but unchanged`
- `Forbidden`

Bounded legacy labels are acceptable. An unchanged compatible consumer is not a scope violation; require its stated regression/integration evidence. Verify generated artifacts exist when required and remain ignored or uncommitted unless the Plan explicitly allows committing them.

A proven task-induced change outside allowed paths is a P0 scope blocker. A pre-existing user change is preserved and excluded from task attribution.

### 3. Map Plan to Implementation

Build a matrix before judging completion:

```text
Task / invariant | Required artifact | Implementation evidence | Production wiring evidence | Fresh verification | Status
```

Check every Task, design invariant, Done Definition item, serializer/state field, restart path, production entry point, deployment command, and documentation deliverable. A helper that exists only in `src/` and tests but is not called by the required production path is incomplete.

Inspect new tests to confirm they assert the planned behavior and failure branch; test count alone is not evidence.

### 4. Recheck Topology and Contracts

For changed shared helpers, SSOT functions, contracts, schemas, CLI flags, or transport fields:

1. Confirm `graphify-out/graph.json` matches the reviewed baseline; otherwise treat it as advisory.
2. Run targeted `graphify query "<exact_symbol>"` or `graphify path "<producer>" "<consumer>"`.
3. Verify every candidate edge at source lines.
4. Use `rg` for changed JSON keys, JSONL fields, event types, CLI flags, and paths because call graphs can miss transport consumers.

Graphify discovers impact; it does not prove correctness. A clean, stale, `INFERRED`, or `AMBIGUOUS` result never proves that no consumer exists.

### 5. Check Minimality and Side Effects

Apply Ponytail only inside the approved requirements: flag duplicate helpers, speculative abstractions, unnecessary dependencies, and unrelated formatting/refactors. Do not simplify away safety validation, idempotency, restart recovery, compatibility, SSOT boundaries, or approved Design invariants.

### 6. Run Fresh Verification

Run the exact targeted tests and non-mutating checks required by the Plan, then:

```bash
git diff --check "$BASE_SHA"
git diff --cached --check "$BASE_SHA"
git diff --check
```

Apply deployment and safety checks only to affected paths and invariants. Do not scan all historical docs and demand zero matches.

For this repository, always verify the master switch directly:

```bash
PYTHONPATH=src:. .venv/bin/python - <<'PY'
from configs import base
assert base.RISK_LIVE_TRADING_ENABLED is False
PY
```

If deployment files changed, inspect actual command/process arguments. An executable `events/\*.jsonl` argument that prevents future-file discovery is a P0 deployment blocker, not a documentation-only warning.

## Output

Report findings first, ordered P0/P1/P2, then:

1. Verdict: `complete`, `incomplete`, or `blocked`.
2. Scope matrix: allowed, actual, pre-existing, unapproved, provenance-uncertain.
3. Task/invariant matrix with file:line evidence.
4. Topology/contract evidence, including Graphify limits and `rg` results.
5. Fresh commands, exit codes, pass/fail counts.
6. Required actions and residual risks.

Do not claim 100% scope compliance when provenance is uncertain. Do not call work complete while required fixes remain.

See `PRESSURE_TESTS.md` for RED/GREEN validation scenarios.
