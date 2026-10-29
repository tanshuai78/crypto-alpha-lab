# Closure Revision Checklists (Consequence-Driven)

Use only the checklist sections that match the actual contracts present in the Design or Implementation Plan being revised. Reference [`.agent/rules/L1_Engineering_Process.md`](../../../rules/L1_Engineering_Process.md) for rule authority.

## 1. Core Document Synchronization Checklist (All Revisions)

- [ ] Final claim, scope, and non-goals remain unchanged (unless a scope change was explicitly requested and routed).
- [ ] All code identifiers, config names (`configs/base.py`), file paths, and enum literals match workspace reality and retain exact English names.
- [ ] Normative definitions, tables, examples, and task verification steps agree with each other (no stale example contradicting updated text).
- [ ] `No-Touch Set` sections remain untouched.
- [ ] Authority boundaries remain strictly preserved:
  - Design approval != Plan approval
  - Plan approval != implementation authorization
  - Implementation completion != commit / deployment / runtime / trading authorization (`RISK_LIVE_TRADING_ENABLED = False`)

## 2. Implementation Plan Specific Checklist (When Revising a Plan)

- [ ] Every Design invariant (`INV-*`) maps to at least one Task and verification command.
- [ ] `Allowed Change Scope` accurately covers all implementation, verification, documentation, runtime, and `Affected but unchanged` paths.
- [ ] If files were added to `Allowed Change Scope` (`BLOCKED_SCOPE_DRIFT`), identity/source-bundle/authorization/`RUN_ID`/evidence dependencies were checked per `L1` §3.2.
- [ ] Behavioral/logic tasks specify public-interface `RED → GREEN → REFACTOR` TDD with independently derived expected values (`L1` §2 Rule 4) and `L1 Rule 15` fixture grading.
- [ ] Documentation/static/read-only tasks specify matching structural/reference/conservation checks without fake TDD.

## 3. Conditional Multi-State / Persistence / `Rule 17` Prompts (Only When Applicable)

Apply the prompts below **only** when the target Design/Plan actually defines persistent state machines, crash/restart recovery, lock lifecycles, or `L1 Rule 17` cross-boundary formal artifacts:

- **State & Sibling Paths (when the contract defines multiple terminal states)**:
  - Are required outputs and failure precedence defined across all applicable sibling states (e.g., `success`, `blocked`, `failed`, `not_probed`) rather than only the happy path?
- **Persistence, Crash & Lock Boundaries (when the contract writes durable state or coordinates processes)**:
  - Are partial-write failure, read-back verification, lock lifecycle vs. runner lifecycle, and restart/no-resume rules consistent across the updated sections?
- **High-Impact / Authority Artifacts (`L1 Rule 17`, when the artifact grants operational authority, controls trading/capital admission, underpins irreversible migration, or reuses an existing frozen Rule 17 profile)**:
  - Do producer tasks, domain strict loader checks, sealed-tree rules, and independent verifier invocations (`scripts/governance/verify_artifact_schema.py`) match the frozen schema and receipt hash bindings?
