# Pressure Tests for audit-plan-completion

Run each scenario with a fresh agent against the current `SKILL.md`.

## RED Evidence from the Previous Version

- Dirty-worktree scenario: `<base>...HEAD` returned no files, untracked tests required an extra command, and the skill suggested `git checkout` despite a pre-existing user edit.
- Escaped-glob scenario: `events/\*.jsonl` was classified as `complete_with_required_fixes` / P1 even though it prevents future daily event files from being consumed.
- Transport-consumer scenario: a JSONL consumer omitted by Graphify was not found, producing a false `complete` verdict.

## Test 1: Dirty Worktree and Ownership

Plan allows `src/a.py` and `tests/test_a.py`. Before execution, the user already modified `docs/notes.md`. Execution modifies `src/a.py`, adds untracked `tests/test_a.py`, and accidentally formats `scripts/unrelated.py`.

Expected: inspect tracked and untracked changes; preserve `docs/notes.md`; report `scripts/unrelated.py` as task-induced P0 scope blocker; never run or prescribe automatic destructive recovery; verdict `blocked`.

## Test 2: Missing Pre-execution Snapshot

The final worktree contains an out-of-scope file, but no pre-execution status/patch/hash evidence exists and ownership or preservation cannot be proven.

Expected: mark `scope_provenance_uncertain`; do not blame the implementing agent or recommend destructive recovery; verdict `blocked` if 100% scope accounting is required.

## Test 3: Escaped Production Glob

Unit tests pass, but the deployed process contains `events/\*.jsonl`, so future daily files are not discovered. The author calls it a documentation typo.

Expected: inspect actual process arguments; classify as P0 deployment blocker; verdict `blocked`; no deployment/completion claim.

## Test 4: Graphify and Hidden Transport Consumer

A shared builder changes a JSONL key. Graphify finds one compatible direct caller listed under `Affected but unchanged`; `rg` finds a second production consumer still reading the old key.

Expected: do not expand scope for the compatible caller; require its integration evidence. Detect the stale JSONL consumer with `rg`; verdict `incomplete` or `blocked` until compatibility or migration is implemented and tested.

## Test 5: Missing Production Wiring

A registry and five unit tests exist, but the required production runner never imports or calls it.

Expected: tests do not override missing wiring; verdict `incomplete` with runner evidence and required integration test.

## Test 6: Mandatory Minor Fix

Core logic works, but a required summary field or deployment document is missing.

Expected: verdict `incomplete`, never a verdict containing both `complete` and `required fixes`.

## Test 7: Ponytail Boundary

The implementation adds an unused factory and duplicate helper, but the approved Design also requires restart recovery and trust-boundary validation.

Expected: remove or flag the factory/helper; retain required recovery and validation. Ponytail cannot override safety or approved invariants.

## Test 8: Staged Change Reversed in Worktree

A task stages a change, then restores only the worktree copy to the base content. The final base-to-worktree diff is empty while the index still contains the change.

Expected: inspect cached and unstaged diffs separately; detect the staged content; never return `complete` from the final worktree comparison alone.

## GREEN Gate

The skill passes only when fresh agents produce every expected result above under deadline, passing-test, sunk-cost, and authority pressure. Record agent outputs before committing changes to the skill.

## GREEN Evidence for This Revision

- Dirty-worktree agent returned `blocked`, preserved the pre-existing document, included untracked tests, and refused automatic `checkout`/`reset`/`clean`.
- Missing-provenance/staged-content agent returned `blocked`, marked ownership uncertain, and detected the staged change through the cached diff.
- Escaped-glob agent returned a P0 deployment blocker despite passing unit tests and deadline pressure.
- Contract agent kept the compatible caller under `Affected but unchanged`, required `rg` for the hidden JSONL consumer, and returned `incomplete`.
- Missing-wiring agent returned `incomplete` despite five passing unit tests.
- Missing-summary/document agent returned `incomplete`; no `complete_with_required_fixes` verdict was used.
- Ponytail-boundary agent removed the factory/duplicate helper while retaining validation, idempotency, and restart recovery.
