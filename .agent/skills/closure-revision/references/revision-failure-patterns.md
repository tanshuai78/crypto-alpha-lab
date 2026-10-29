# Common Revision Failure Patterns

Use these patterns as a fast cross-fix self-check before handing a revised Design or Implementation Plan back for review.

## 1. Patching One Sentence While Leaving Examples or Tasks Stale

- **Failure**: Normative text is updated to fix a finding, but an example, table row, `Allowed Change Scope` entry, or Task verification command still reflects the old rule.
- **Prevention**: Search the target document for all occurrences of the modified field, path, or rule and synchronize them in the same revision pass.

## 2. Sequential Fix Collision

- **Failure**: Fixing Finding #3 changes a field name, enum literal, or file path that Finding #1's fix relied upon.
- **Prevention**: Build the full Blocker Ledger first, check pairwise interactions across all planned edits, and run a combined diff review after editing.

## 3. Over-Prescribing Ceremonial Gates onto Simple Tasks

- **Failure**: Adding 4-state crash matrices, `flock`/`fsync` durability protocols, or standalone `Rule 17` verifiers to a local internal fix or exploratory script just to make the document "look stricter."
- **Prevention**: Follow `.agent/rules/L1_Engineering_Process.md` §3—include persistence/verifier ceremonies only when the task's actual failure consequences trigger them.

## 4. Happy-Path-Only Fix on Multi-State Contracts

- **Failure**: When a contract genuinely defines multiple terminal states or failure branches, updating only the success path while leaving `blocked`/`failed` or rollback paths inconsistent.
- **Prevention**: When revising a state machine or reducer contract, verify all sibling branches declared by that contract.

## 5. Overly Broad Static Grep Gate

- **Failure**: Adding a verification grep that bans a generic word (e.g., `event_time` or `bugfix.md`) without accounting for legitimate approved identifiers or historical migration tables.
- **Prevention**: Scope static checks to exact forbidden calls/paths or explicitly classify legitimate historical references.

## 6. No-Touch Drift & Self-Approval Overclaim

- **Failure**: Opportunistically refactoring unrelated frozen sections, or claiming `100% CLOSED` / `Approved` when an open question still requires reviewer or user confirmation.
- **Prevention**: Enforce the `No-Touch Set`, keep `candidate_self_approved = false`, and mark any non-deterministic item as `PARTIALLY_CLOSED` / `OPEN` with clear notes for the reviewer.
