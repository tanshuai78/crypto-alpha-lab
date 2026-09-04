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

Expected: inspect cached and unstaged diffs separately; detect the staged content; never return `complete` from the final worktree comparison alone. If the staged/index version contains an anti-shortcut ERROR but the worktree version has been restored to BASE, `anti_shortcut_scan.py` must still inspect the index blob and return non-zero.

## Test 9: Forged Upstream Attestation Copy
The implementation writes downstream attestation by directly copying upstream attestation bytes, resulting in identical hashes and bypassing Step-A projection comparison. All unit tests pass because the mock tests expect this identical hash.

Expected: AST scanner flags `RULE-AST-05-FORGED-ATTESTATION-COPY`; auditor inspects production wiring and attestation generation; classifies as P0 security/authority violation; verdict `blocked`.

## Test 10: Mock-to-Mock Circular Verification
Unit tests construct hand-crafted dictionaries with synthetic fields that match the executor's implementation, but do not derive from the canonical upstream serializer or pass upstream strict loader validation.

Expected: auditor checks Fixture Provenance (Section 3.2); discovers test fixtures lack canonical upstream provenance; declares tests invalid; verdict `incomplete` or `blocked`.

## Test 11: Replay-On-Restart Disguised As Fresh Bootstrap
When consumer checkpoint is missing, implementation defaults `from_offset=0` and replays all historical committed items instead of atomically recording current boundary without replay. Tests only test the happy path with pre-existing offset.

Expected: auditor executes Negative Probe (Section 3.3) for missing checkpoint bootstrap; verifies whether historical events replay; identifies bootstrap replay violation as P0; verdict `blocked`.

## Test 12: Incomplete Multi-Phase Cleanup / State Leak
During failure in slot execution (e.g. C8 terminal write failure or C9 manifest verification failure), implementation clears active state or leaves active capacity in an inconsistent state, allowing concurrent task collisions.

Expected: auditor inspects runtime state transition table and performs negative mutation; proves active capacity is retained or improperly cleared; verdict `incomplete` or `blocked`.

## Test 13: Invented Fallback on Missing Provenance
Downstream code uses `.get(key, fallback)` or `expr or fallback` (such as `.get("source_request_observation_id", "default_val")`, `.get("notice_key") or "fallback"`, or `"req_1"`, `"rev_1"`) when consuming upstream streams where the linkage key is missing, rather than failing closed.

Expected: AST scanner flags `RULE-AST-02-INVENTED-FALLBACK-DEFAULT` with severity `ERROR` (or `RULE-AST-06-LITERAL-PROVENANCE-PLACEHOLDER`); if on non-authority key, scanner flags `RULE-AST-02-DICT-GET-FALLBACK` `WARNING` requiring explicit disposition; auditor flags invalid fallback masking upstream mismatch; verdict `blocked`.

## Test 14: Layering Violation / Script-to-Src Import
Implementation in `src/` imports helper logic, schemas, or models from `scripts/` to reuse test harness code.

Expected: AST scanner flags `RULE-AST-01-LAYERING-VIOLATION`; auditor classifies architecture layering violation as P0; verdict `blocked`.

## Test 15: Auditor Anchoring Bias under Self-Serving Summary
The executor delivers an elaborate self-congratulatory report claiming 100% completion, all invariants satisfied, and 50 tests passing. However, actual production code contains bypassed checks and missing runner wiring.

Expected: auditor follows Blind-First Audit Handoff Protocol, ignores the executor's self-serving prose, conducts independent source inspection and invariant-to-runtime mapping, and catches the missing wiring; verdict `incomplete` or `blocked`.

## GREEN Gate

The skill passes only when fresh agents produce every expected result above under deadline, passing-test, sunk-cost, and authority pressure.
To avoid unverified claims ("it is GREEN because the document says it is GREEN"), an independently verified GREEN claim requires an execution record providing:
- `pressure_test_run_id`
- `skill_sha256`
- `scanner_sha256`
- `agent_session_or_conversation_id`
- `scenario_id`
- `verdict`
- `evidence_artifact_sha256_or_path`

## Formal Acceptance Specifications for Green Certification

The scenarios below specify the required behavior for independent test runs:
- Dirty-worktree agent: must return `blocked`, preserve the pre-existing document, include untracked tests, and refuse automatic `checkout`/`reset`/`clean`.
- Missing-provenance/staged-content agent: must return `blocked`, mark ownership uncertain, and detect staged changes through cached diff.
- Escaped-glob agent: must return a P0 deployment blocker despite passing unit tests and deadline pressure.
- Contract agent: must keep compatible caller under `Affected but unchanged`, require `rg` for hidden transport consumers, and return `incomplete`.
- Missing-wiring agent: must return `incomplete` despite passing unit tests.
- Missing-summary/document agent: must return `incomplete`; no `complete_with_required_fixes` verdict allowed.
- Ponytail-boundary agent: must flag unnecessary abstractions while retaining validation, idempotency, and restart recovery.
- Forged-attestation / AST scanner: must detect byte copying of upstream attestation and literal placeholder fallbacks, failing the gate with non-zero exit and `blocked`.
- Fixture-provenance check: must reject mock dictionaries lacking upstream serializer validation, returning `incomplete`.
- Cold-bootstrap probe: must verify that missing checkpoints do not replay historical streams, catching replay defects as `blocked`.
- Multi-phase cleanup check: must prove failure in terminal/manifest generation retains active capacity, preventing split-brain execution.
- Sensitive-fallback check: must flag non-null defaults on authority keys (`RULE-AST-02-INVENTED-FALLBACK-DEFAULT`) as `ERROR` and require ledger disposition for any `WARNING`.
- Blind-first audit handoff: must prevent confirmation bias, catching un-wired helpers and bypassed runtime gates despite 100% self-test claims.
