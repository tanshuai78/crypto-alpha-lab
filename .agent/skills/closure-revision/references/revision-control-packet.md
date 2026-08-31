# Closure Revision Control Packet Templates

Use this file when preparing or handing off a revision.

## A. Pre-Revision Authority Packet

```text
# Revision Authority
revision_target = ...
current_sha256 = ...
revision_target_status = revision_required
review_record = ...
review_record_sha256 = ...
review_mode = closure_confirmation

final_claim = ...
proof_graph_frozen = true
trust_boundary_frozen = true
scope_frozen = true
closure_escape_count = ...

approved_upstream_authorities = ...
approved_upstream_sha256s = ...
workspace_baseline = ...

implementation_allowed = false
deployment_allowed = false
runtime_action_allowed = false
```

## B. Blocker Ledger

| ID | Severity | Origin A/B/C/D | Proof Edge | Failure Mode | Required Invariant | Mechanical Closure Evidence | Dependencies |
|---|---|---|---|---|---|---|---|
| P0-1 | P0 | C | PG-X | ... | ... | ... | ... |

## C. Mutable / No-Touch Sets

```text
MUTABLE
- ...

NO-TOUCH
- ...
```

## D. Impact Cone

```text
blocker_id = ...
primary_changed_contract = ...
changed_proof_edges = ...
dependent_proof_edges = ...
affected_state_artifact_rows = ...
affected_transition_failure_rows = ...
affected_authority_rows = ...
affected_invariant_evidence_rows = ...
affected_artifacts = ...
affected_tests_completion_gates = ...
```

## E. One-Batch Patch Plan

| Blocker | Exact Change | Sync Changes | Mechanical Closure Test | No-Touch Risk |
|---|---|---|---|---|

## F. Author-Side Mini Closure Confirmation

```text
self_review_mode = closure_confirmation
final_claim = <unchanged>
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

changed_proof_edges = ...
affected_matrix_rows_checked = ...

candidate_status = ready_for_reviewer_closure_confirmation
candidate_approval = false
implementation_allowed = false
deployment_allowed = false
```

## G. Reviewer Handoff Delta

| Blocker | Changed Sections | Exact Closure Mechanism | Mechanical Evidence | Other Frozen Areas Touched |
|---|---|---|---|---|

```text
previous_candidate_sha256 = ...
revised_candidate_sha256 = ...
review_record = ...
changed_proof_edges = ...
affected_matrix_rows_checked = ...
no_touch_areas_verified = ...
scope_expanded = false
permissions_changed = false
candidate_approval = false
```
