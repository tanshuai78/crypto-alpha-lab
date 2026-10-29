# Closure Revision Control Packet Templates

Use this lightweight template when preparing and handing off a controlled Design or Implementation Plan revision.

## 1. Pre-Revision Authority & Baseline

```text
revision_target_path = ...
pre_revision_sha256 = ...
review_record_reference = ...
upstream_authority_paths_and_sha256 = ...
scope_frozen = true | false
implementation_allowed = false
deployment_allowed = false
runtime_action_allowed = false
```

## 2. Blocker Ledger & Sets

| Blocker ID | Severity | Affected Section / Contract | Root Problem | Planned Change & Closure Criterion | Coupled Blockers |
|---|---|---|---|---|---|
| P0-01 | P0 | ... | ... | ... | ... |

```text
MUTABLE SET:
- ...

NO-TOUCH SET:
- ...
```

## 3. Author-Side Closure Summary & Handoff Delta

| Blocker ID | Changed Sections | Closure Mechanism & Synced References | Author Status (`CLOSED` / `PARTIALLY_CLOSED` / `OPEN`) | Notes for Independent Reviewer |
|---|---|---|---|---|
| P0-01 | ... | ... | CLOSED | ... |

```text
pre_revision_sha256 = ...
post_revision_sha256 = ...
no_touch_set_preserved = true | false
cross_fix_contradiction_check = passed | failed
scope_expanded = false
permissions_changed = false
candidate_self_approved = false
```

> **Note**: If any item requires external user judgment or cannot be deterministically self-proven by the author, mark it `PARTIALLY_CLOSED` or `OPEN` and state the exact verification point for the independent reviewer.
