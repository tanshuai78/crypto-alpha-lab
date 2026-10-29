---
name: closure-revision
description: Use when revising a high-risk Design or Implementation Plan after Closure Audit or Closure Confirmation findings, especially with a frozen proof graph, multiple P0/P1 blockers, prior incomplete fixes, or risk of revision-introduced contradictions.
---

# Closure Revision — Controlled Design & Plan Revision

## Overview

`closure-revision` is the **author-side controlled revision workflow** for repairing an unapproved Design or Implementation Plan after review findings (such as `REVISION_REQUIRED` or `Approve with required fixes`).

Core principle:

> **Do not patch reviewer comments one-by-one in isolation, and do not re-audit unrelated frozen sections. Build one complete blocker ledger for all `OPEN` findings, trace their shared impact cone on directly affected contracts, apply one coherent revision, and report honest closure status for independent review.**

Reference [`.agent/rules/L1_Engineering_Process.md`](../../rules/L1_Engineering_Process.md) (§2 Closure Revision Discipline & §3) as the authoritative engineering process rule.

---

## 1. Authority Boundary

This skill applies to the **revision author**, never the independent reviewer or user approver.

- **Permitted**:
  - Inspect the target Design/Plan, review findings, upstream authority documents, and current workspace facts (`configs/base.py`, source, tests);
  - Build the blocker ledger, `Mutable Set` / `No-Touch Set`, and impact cones;
  - Edit the target unapproved Design or Plan within the `Mutable Set`;
  - Run author-side consistency checks and produce a concise Revision Delta Report with pre/post SHA-256 hashes.
- **Prohibited**:
  - Self-approving the revised Design or Plan;
  - Enabling implementation, commit, deployment, runtime, paper-trading, or live-trading authority (`RISK_LIVE_TRADING_ENABLED` must remain `False`);
  - Silently mutating already-approved upstream authority files in place;
  - Expanding frozen scope or changing upstream contracts without flagging `STOP = approved_authority_change_required` or `STOP = material_scope_expansion_required`.

---

## 2. Priority of Facts & Review Findings

Workspace reality and higher-level safety/authority contracts take precedence over mechanical compliance with a reviewer suggestion:

1. `L0` Financial Safety & `configs/base.py` invariants;
2. Approved upstream authority contracts (bound by SHA-256) and verified workspace source code;
3. `.agent/rules/L1_Engineering_Process.md` and (for research) `.agent/rules/L2_Alpha_Research_Methodology.md`;
4. Reviewer findings.

If a reviewer finding contradicts an upstream frozen contract or workspace fact, do **not** implement the contradiction blindly—document the objective source/hash evidence in the blocker ledger and either retain the compatible contract or escalate (`STOP`) if the upstream contract itself must change.

---

## 3. Step-by-Step Revision Workflow

### Step 1: Record Pre-Revision Baseline & Build the Blocker Ledger

Before editing, record the target file's current `pre_revision_sha256` and list all `OPEN` P0/P1 findings in one ledger:

| Blocker ID | Severity | Affected Section / Contract | Root Problem | Required Fix & Closure Criterion | Coupled Blockers |
|---|---|---|---|---|---|

### Step 2: Freeze `Mutable Set` & `No-Touch Set`

- **`Mutable Set`**: Only the sections, contracts, examples, and task entries directly required to close the blocker ledger and keep internal references consistent.
- **`No-Touch Set`**: All unaffected sections, closed contracts, approved thresholds, permission boundaries, and non-goals. Do not perform opportunistic rewrites outside the `Mutable Set`.

### Step 3: Trace Impact Cones (Proportional to Actual Contract Type)

For each blocker, identify all coupled places inside the document that must stay synchronized (normative rule, table/matrix row, example, Task description, `Allowed Change Scope`, verification command).

**Consequence-Driven Matrix Rule**:
- Inspect complex state machines (`success / blocked / failed / not_probed`), `flock`/`fsync` crash/restart windows, or `Rule 17` sealed-tree/verifier bindings **only when the target Design/Plan actually defines or modifies those contracts** (see [`references/design-plan-checklists.md`](references/design-plan-checklists.md)).
- Do **not** force multi-state crash matrices or standalone `Rule 17` verifiers into local, documentation, or exploratory tasks that do not have those obligations under `L1` §3.

### Step 4: Apply One Coherent Patch & Run Cross-Fix Check

Apply all planned edits in one coherent pass, then verify across fixes (see [`references/revision-failure-patterns.md`](references/revision-failure-patterns.md)):
1. Did Fix B invalidate Fix A or introduce a conflicting field/enum/path name?
2. Are normative sections, examples, `Allowed Change Scope`, and Task verification commands 100% synchronized?
3. Are safety and permission flags unchanged (`candidate_approval = false`, `implementation_allowed = false`, `RISK_LIVE_TRADING_ENABLED = False`)?
4. Were all `No-Touch Set` sections preserved without drift?

### Step 5: Author-Side Mini Closure Check & Honest Status Reporting

Evaluate each blocker after editing and report its status honestly (using [`references/revision-control-packet.md`](references/revision-control-packet.md)):

- **`CLOSED`**: The finding and its coupled references inside the document are deterministically resolved and verified.
- **`PARTIALLY_CLOSED` / `OPEN`**: A full resolution depends on an external decision, missing input, or independent reviewer judgement that the author cannot self-certify. State the exact remaining point requiring reviewer/user confirmation rather than fabricating a false `100% CLOSED` claim.

Next reviewers should perform **focused Closure Confirmation** on the `OPEN` / `PARTIALLY_CLOSED` items, directly affected contract edges, and any revision-introduced diffs—without re-running an unconstrained full-document audit on untouched sections.
