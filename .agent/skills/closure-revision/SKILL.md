---
name: closure-revision
description: Use when revising a high-risk Design or Implementation Plan after Closure Audit or Closure Confirmation findings, especially with a frozen proof graph, multiple P0/P1 blockers, prior incomplete fixes, or risk of revision-introduced contradictions.
---

# Closure Revision — crypto-alpha-lab

## Overview

Closure Revision is the **author-side repair workflow** for a Design or Implementation Plan that has already been reviewed with Closure Audit / Closure Confirmation.

Core principle:

> **Do not patch reviewer comments one-by-one. Repair the smallest coherent part of the frozen proof system, verify sibling states and cross-fix interactions, then submit one closed revision.**

Target:

```text
one finding set
→ one coherent revision
→ author-side mini Closure Confirmation
→ reviewer Closure Confirmation
→ approval
```

Quality targets:

```text
previous_p0_closed = N/N
previous_required_p1_closed = N/N
partial_closure_count = 0
revision_introduced_p0_count = 0
no_touch_violation_count = 0
scope_expanded = false
```

---

## 0. Authority Boundary

This skill is for the **revision author**, not the reviewer.

It may:

```text
inspect the current candidate and review record
inspect current workspace/authorities when needed
build a blocker ledger and impact cones
edit the unapproved candidate
run self-consistency and mechanical closure checks
produce a revision delta report and candidate SHA
```

It may not:

```text
approve its own Design/Plan
set implementation_allowed=true
set deployment_allowed=true
set runtime_action_allowed=true
enable paper/live/execution permissions
change RISK_LIVE_TRADING_ENABLED=True
silently edit already-approved authority bytes
expand frozen scope/TCB without rerouting
```

If an already-approved authority must materially change:

```text
STOP = approved_authority_change_required
```

Route through a new explicit delta/review authority.

---

## 1. When To Use

Mandatory when any is true:

- Closure Audit produced P0/P1 findings.
- Closure Confirmation produced remaining/partial/new findings.
- proof graph / trust boundary / scope is frozen.
- multiple findings may touch one reducer, artifact chain, authority gate, or state machine.
- a prior revision partially closed a blocker.
- a prior revision introduced a contradiction.
- reviewer provided a “modify only X; do not reopen Y” boundary.
- the document involves evidence lineage, PIT, persistent state, restart/crash, runtime/deployment identity, shared storage, sealed artifacts, execution permissions, or risk invariants.

Do not use ordinary `receiving-code-review` as the primary method for these documents. Closure findings are coupled proof-system changes, not independent code-review comments.

---

## 2. Bind The Revision Authority Packet Before Editing

Collect exact inputs:

```text
revision_target_path
revision_target_current_sha256
revision_target_status

review_record
review_mode
final_claim
proof_graph_frozen
trust_boundary_frozen
scope_frozen
frozen_proof_graph_edges
frozen_trust_boundary
frozen_scope/non_goals
previous_blockers
reviewer_no_touch_instructions
closure_escape_count

approved_upstream_authorities + SHA256
current workspace/baseline identity when relevant
implementation_allowed
deployment_allowed
runtime_action_allowed
```

Workspace facts override memory.

### Review Findings Are Investigation Inputs, Not Absolute Authority

A review finding must be investigated, but it must not mechanically override a
real frozen source contract or parent invariant.

Revision authority order:

```text
1. approved parent/frozen source contracts and their invariants (including bound SHA256 bytes)
2. current workspace source, artifact, and lifecycle-owner evidence that proves those contracts
3. applicable project safety and authority rules
4. reviewer finding
```

Before adopting a finding that changes a lifecycle owner, state machine,
artifact grammar, authority boundary, or invariant, trace the real
producer/consumer topology and verify compatibility with the higher-authority
contracts. Adopt only the compatible portion.

If a finding conflicts with a higher-authority contract:

```text
do not implement it mechanically
→ record the conflict and supporting evidence in the blocker ledger
→ retain the frozen contract, or STOP = approved_authority_change_required
  when that contract itself must change
```

Project source priority:

```text
1. configs/base.py
2. current project/workspace state
3. current document index / approved hashes
4. affected src/scripts/tests
5. relevant runtime artifacts
6. roadmap/history
```

If a required authority, SHA, frozen edge, or scope boundary cannot be resolved:

```text
STOP = revision_authority_incomplete
```

Do not guess.

---

## 3. Determine Revision Mode

### Pre-freeze

If:

```text
proof_graph_frozen = false
```

repair all first-audit blockers and missing proof obligations/matrices needed for valid freeze.

### Post-freeze

If:

```text
proof_graph_frozen = true
trust_boundary_frozen = true
scope_frozen = true
```

then:

```text
review_mode = closure_confirmation
```

and the revision is strictly bounded:

```text
no new subsystem
no permission expansion
no threat-model expansion
no TCB descent
no speculative hardening outside blocker impact cones
```

If a correct fix requires material expansion:

```text
STOP = material_scope_expansion_required
```

Return to reviewer/user for rerouting.

---

## 4. Build One Blocker Ledger — Before Any Edit

Read **all findings first**.

For each blocker record:

| Field | Required value |
|---|---|
| ID | reviewer blocker ID |
| Severity | P0/P1 |
| Origin | A/B/C/D |
| Proof edge | frozen PG edge(s) |
| Failure mode | exact unsafe/incomplete condition |
| Required invariant | exact condition to restore |
| Closure evidence | test/hash/gate/artifact required |
| Dependencies | other blockers/edges touched |

Origin classification:

```text
A = earlier_closure_audit_miss
B = revision_introduced
C = previous_blocker_not_fully_closed
D = non-blocking_new_P1_inside_frozen_graph
```

Preserve reviewer classification when given.

### Closure criteria must be deterministic

Bad:

```text
clarify failure handling
```

Good:

```text
all blocked/failed/complete terminal intents produce the exact four-state summary vector before terminal persistence; not-probed profiles use observation_id=null
```

If closure criterion is ambiguous:

```text
STOP = blocker_closure_criterion_ambiguous
```

---

## 5. Freeze Mutable Set And No-Touch Set

Before editing, declare:

```text
MUTABLE SET
NO-TOUCH SET
```

Mutable Set contains only sections/contracts/files required by the blocker ledger.

No-Touch Set contains already-closed/frozen areas, for example:

```text
endpoints
ProfileCore values
thresholds
approved SHA authorities
scope split
permission flags
TCB
unaffected schemas/artifacts
```

After revision, any unplanned No-Touch change is a defect.

If a synchronized reference must change, explicitly add it to Mutable Set **before** editing and include it in the impact cone.

No opportunistic cleanup/refactor during Closure Revision.

---

## 6. Compute The Impact Cone For Every Blocker

For each blocker record:

```text
primary_changed_contract
changed_proof_edges
dependent_frozen_proof_edges
affected_state_artifact_rows
affected_transition_failure_rows
affected_authority_rows
affected_invariant_evidence_rows
affected_persistent_artifacts
affected_tests/completion_gates
```

Common cones:

### Reducer / terminal

```text
reducer
→ observation
→ summary
→ terminal
→ manifest/seal
→ failure precedence
→ restart/no-resume
→ tests
```

### Artifact producer

```text
producer
→ identity/hash
→ consumer/validator
→ terminal
→ manifest
→ closed-tree verifier
```

### Config gate

```text
configs/base.py
→ preflight/baseline
→ model tests
→ runtime imports
→ AST/diff completion gate
→ safety flag checks
```

### Runtime identity

```text
environment projection
→ authorization
→ root timing
→ attestation
→ network gate
→ terminal evidence
```

### Lock/storage

```text
lock primitive
→ runner lifecycle
→ shared-process interoperability
→ reserve algebra
→ crash/restart
→ control artifact/manifest
```

Rule:

> Fix the whole affected frozen edge, but do not expand beyond dependent frozen edges.

---

## 7. Reconstruct The Affected Matrix Rows

Use Closure Audit v2 matrices for all affected edges:

```text
A. State × Artifact
B. Transition × Failure
C. Authority
D. Invariant × Mechanical Evidence
```

Read `references/design-plan-checklists.md` for the detailed sibling-state prompts.

### Sibling-state rule

If one state changes, inspect siblings on the same proof obligation.

Typical siblings:

```text
success
blocked
failed
not_probed
raw_write_fail
observation_write_fail
summary_write_fail
terminal_write_fail
manifest_write_fail
same-ID collision
restart/stale revision
```

Do not submit a success-only fix when the frozen contract covers failure states.

---

## 8. Plan One Coherent Patch Before Editing

Create a Revision Patch Plan:

| Blocker | Exact change | Required sync changes | Mechanical closure evidence | No-touch risk |
|---|---|---|---|---|

Then check every pair of fixes:

```text
Can A invalidate B?
Can A create a state B does not model?
Can A change an enum/schema/hash B assumes?
Can B weaken failure precedence established by A?
Can either change authority or permissions?
```

Resolve interactions **before editing**.

### Minimal coherent patch

Do not redesign unrelated architecture, rename unrelated fields, add registries/factories, or broaden future scope unless explicitly required.

Smallest patch is not always best; use the **smallest patch that fully closes the coupled proof edge**.

---

## 9. Snapshot Before Revision

Record:

```text
pre_revision_candidate_sha256
review_record identity
upstream authority SHAs
workspace/baseline identity when relevant
Mutable Set
No-Touch Set
blocker ledger
```

Preserve exact pre-revision bytes or a baseline diff.

This is the authority for the final no-touch check.

---

## 10. Apply The Revision

Apply all planned changes as one coherent revision.

Rules:

1. Preserve frozen terminology exactly.
2. Preserve enum/field names unless blocker explicitly changes them.
3. Preserve threshold values unless authorized Design change says otherwise.
4. Preserve approved upstream SHA authorities.
5. Preserve permission flags.
6. No hidden retry/resume where Design says fail/no-resume.
7. No compatibility alias unless authorized.
8. Do not change normative semantics under the label “clarification.”
9. Keep tests/gates synchronized with normative text.
10. Do not claim approval in the candidate.

### Synchronize duplicated contract statements

For every changed rule search/update all applicable copies:

```text
normative definition
example
matrix row
pseudocode
implementation task
verification/test requirement
self-review checklist
```

A stale example contradicting the normative rule is a revision defect.

---

## 11. Run The Cross-Fix Contradiction Pass

After all edits, ignore the original reviewer wording and inspect the combined patch.

Mandatory questions:

```text
1. two fixes assign different meanings to one field/state?
2. simultaneous failures still have one verdict?
3. every changed/new state has an artifact row?
4. every required artifact has a producer for all required sibling states?
5. every producer has consumer/validator?
6. manifest/seal matches actual produced artifacts?
7. restart/reuse/collision still matches fresh/no-resume policy?
8. static gate accidentally rejects an approved literal/contract?
9. test verifies the exact invariant, not a weaker proxy?
10. authority/permissions unchanged?
11. failure-path fix accidentally grants success authority?
12. local durability supersession still follows frozen precedence?
```

If any is ambiguous:

```text
revision_self_check = failed
```

Do not submit.

Read `references/revision-failure-patterns.md` for known bad-revision patterns from this project.

---

## 12. Verify Mechanical Closure — Match The Exact Invariant

For every blocker, verify the exact closure evidence requested:

```text
SHA comparison
AST/diff comparison
state-artifact row
negative test
pytest command
closed-tree verifier
static scope gate
permission assertion
```

Do not substitute weaker evidence.

Examples:

```text
required: exact additive AST delta
wrong: only assert live_trading=False

required: summary on every terminal path
wrong: test P4 success only

required: fresh-root no-reuse
wrong: test advisory lock blocking only
```

---

## 13. Author-Side Mini Closure Confirmation

Before handing the revision back to the reviewer, simulate Closure Confirmation **inside the frozen graph**.

Required result:

```text
self_review_mode = closure_confirmation
final_claim = <same frozen claim>
proof_graph_frozen = true
trust_boundary_frozen = true
scope_frozen = true
scope_expanded = false

previous_p0_closed = X/X
previous_required_p1_closed = Y/Y
remaining_previous_p0 = 0
remaining_required_p1 = 0

revision_introduced_p0 = 0
partial_closure_count = 0
no_touch_violation_count = 0
authority_promotion_detected = false
TCB_expanded = false
```

For each blocker mark:

```text
CLOSED | PARTIAL | NOT_CLOSED
```

Only `CLOSED` is acceptable for submission.

For every changed proof edge record:

```text
sibling_rows_checked = true
cross_fix_contradiction = false
```

### Submission gate

Submit only if:

```text
all previous P0 closed
all required P1 closed or explicitly accepted
revision_introduced_p0 = 0
partial_closure_count = 0
scope_expanded = false
no_touch_violation_count = 0
authority_promotion_detected = false
```

Otherwise fix locally before spending another reviewer round.

---

## 14. Produce The Revision Delta Report

Every reviewer handoff must include:

| Blocker | Changed sections | Exact closure mechanism | Mechanical evidence | Other frozen areas touched |
|---|---|---|---|---|

And:

```text
previous_candidate_sha256
revised_candidate_sha256
review_record identity
changed_proof_edges
affected_matrix_rows_checked
no_touch_areas_verified
scope_expanded = false
permissions_changed = false
candidate_approval = false
```

Use the template in `references/revision-control-packet.md`.

---

## 15. STOP Conditions

Stop and escalate instead of improvising when:

```text
correct fix requires material scope expansion
correct fix requires TCB change/descent
correct fix requires mutating approved authority bytes in place
two blocker criteria conflict
review finding conflicts with frozen final claim
required authority/SHA cannot be verified
workspace contradicts Plan/Design assumptions
fix requires enabling paper/live/execution permissions
new design-level P0 appears outside impact cone
no deterministic safe behavior exists inside current Design authority
```

Report:

```text
STOP_REASON
affected_proof_edge
why_revision_authority_is_insufficient
minimum_reroute = new_closure_audit | design_delta | user_decision | workspace_reinspection
```

---

## 16. Design Revision Rules

For Design revisions additionally verify:

```text
final claim unchanged unless explicitly re-audited
scope/non-goals unchanged
source-of-truth relationships unchanged
enums/field names exact
identity/hash projection exact
failure precedence deterministic
success/blocked/failed/not-probed coverage complete
artifact producer coverage complete
crash/restart/no-resume semantics complete
PIT/anti-hindsight unchanged or correctly fixed
producer-consumer transport complete
manifest/seal authority exact
permission boundary unchanged
TCB unchanged
examples/matrices match normative text
```

---

## 17. Implementation Plan Revision Rules

For Implementation Plan revisions additionally verify:

```text
every Design invariant has implementation owner
every required artifact has producer task
every failure state has test/verification
RED -> implementation -> GREEN preserved
configs/base.py delta exactly authorized
no existing risk invariant silently changes
changed-path allowlist exact
baseline/provenance gate executable
Design SHA / Plan SHA rebind correct
raw/persistence/parse ordering correct
lock primitive != runner lifecycle
shared-resource algebra reads current SSOT
summary/terminal/manifest chain covers all terminal states
same-ID/root collision matches fresh/no-resume
static gates do not reject approved literals
final code review covers post-fix final diff
completion audit occurs after final verification
implementation authorization remains separate
deployment/runtime authorization remains separate
```

---

## 18. Relationship To Superpowers

Recommended routing:

```text
brainstorming
→ Design
→ spec/document review
→ Closure Audit
→ closure-revision if findings
→ Closure Confirmation

writing-plans
→ Implementation Plan
→ plan review
→ Closure Audit
→ closure-revision if findings
→ Closure Confirmation

approved Plan + explicit implementation authorization
→ test-driven-development / executing-plans
→ requesting-code-review
→ receiving-code-review
→ verification/completion audit
```

Closure Revision differs from ordinary review feedback handling:

```text
understand ALL findings first
→ compute shared impact cones
→ plan one patch
→ apply one patch
→ cross-fix confirmation
```

Do not use a sequential “fix item 1, then item 2” loop for a frozen proof system.

---

## 19. Prohibited Revision Behavior

Never:

```text
patch findings one-by-one before building blocker ledger
edit only reviewer-named sentence without impact analysis
clean up unrelated frozen sections
rename approved fields to dodge validation
weaken gate to make tests pass
hardcode historical values where current SSOT is required
add fallback where preflight must STOP
turn no-resume into wait-and-reuse
turn fail-closed into retry for convenience
produce summary/terminal/manifest only on happy path when siblings require them
use serializer existence as proof of artifact producer
use verifier existence as proof of producer
claim blocker closed from prose only
silently change final_claim / review mode / TCB
reset closure_escape_count
mark candidate approved
enable implementation/deployment/runtime authority
```

---

## 20. Definition Of Done

A Closure Revision is complete only when:

```text
[ ] exact authorities bound
[ ] all findings in one blocker ledger
[ ] deterministic closure criterion for every blocker
[ ] Mutable Set declared
[ ] No-Touch Set declared
[ ] impact cone calculated for every blocker
[ ] sibling matrix rows reconstructed
[ ] cross-blocker interactions planned before editing
[ ] one coherent patch applied
[ ] duplicated statements synchronized
[ ] cross-fix contradiction pass complete
[ ] exact mechanical evidence matches every closure criterion
[ ] author-side mini Closure Confirmation passes
[ ] no-touch diff passes
[ ] scope/permissions/TCB unchanged
[ ] revision delta report generated
[ ] revised candidate SHA recorded
[ ] candidate remains explicitly unapproved pending reviewer
```

Only then submit for reviewer Closure Confirmation.

---

## Final Rule

> Closure Revision is not “apply comments.” It is **controlled repair of a frozen proof system**.
>
> Read every finding first. Calculate shared impact. Freeze what must not move. Repair the smallest coherent contract set. Check sibling states and cross-fix contradictions. Prove every blocker closed with the exact requested evidence. Only then consume another review round.
