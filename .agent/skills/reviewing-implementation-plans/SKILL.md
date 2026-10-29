---
name: reviewing-implementation-plans
description: Use when reviewing implementation, refactor, bugfix, replay/research, deployment, migration, data-pipeline, or strategy plans before coding, especially when safety, tests, evidence semantics, market-data quality, thresholds, execution risk, scope boundaries, Allowed Change Scope, or Graphify topology collisions may be unclear
---

# Reviewing Implementation Plans

## Overview

Plan review is pre-flight risk control before modifying repository or runtime state. Its goal is to verify that a Plan is bounded, minimally complex, dependency-ordered, and backed by executable verification aligned with [`.agent/rules/L1_Engineering_Process.md`](../../rules/L1_Engineering_Process.md) and (when applicable) [`.agent/rules/L2_Alpha_Research_Methodology.md`](../../rules/L2_Alpha_Research_Methodology.md).

A review must return one of four verdicts:

- **Approve**: safe, bounded with an explicit `Allowed Change Scope`, vertically sliced, and matched to consequence-driven verification.
- **Approve with required fixes**: direction is sound, but specific gaps (e.g., missing path in whitelist, unverified consumer compatibility, weak test assertion) must be fixed before execution.
- **Block**: Plan introduces unsafe behavior, scope creep, unapproved semantic/threshold changes, or untestable tasks.
- **Defer / request missing inputs**: required upstream Design, source context, or baseline facts are missing.

> **Web / Restricted Reviewer Rule**: When reviewing in an environment without full workspace access, request only the minimal missing source files or rule texts that carry key decisions; never demand proof-of-skill artifacts such as standalone `GLOSSARY`, `ADR`, external `spec`, or external `ticket` files.

## Review Output Format

Use this structure unless the user requests another format:

```text
结论：Approve | Approve with required fixes | Block | Defer / request missing inputs

1. 总体判定
2. 必改问题 (P0 Blocker / P1 Required Fix) — 含 finding_id | severity | section | evidence | problem | required_change | verification
3. Allowed Change Scope 与范围边界核查
4. 任务切片、前置依赖与最小化 (Ponytail) 核查
5. 跨模块拓扑与契约兼容性核查
6. 测试、证据语义与按后果附加门禁核查
7. 建议执行顺序与结论边界（本轮能证明什么 / 不能证明什么 / 禁止推出的结论）
```

## Core Review Checks

### 1. Scope & `Allowed Change Scope` Gate (Mandatory)

Compare the Plan title, goal, tasks, outputs, and Done Definition against the approved Design:

- Every Plan that mutates repository or runtime state must declare an explicit `Allowed Change Scope` block (`Allowed implementation paths`, `Allowed verification paths`, `Allowed documentation paths`, `Allowed generated/runtime artifacts`, `Affected but unchanged`, `Forbidden`), marking inapplicable categories `none`. Equivalent unambiguous headings are acceptable for documentation-only plans.
- **Block** any Plan containing unscoped mutating commands (`ruff check --fix .`, `git clean -fdx`, repo-wide auto-formatters). Non-mutating checks are allowed as verification only.
- Compatible consumers that need no edits belong in `Affected but unchanged` with regression/compatibility evidence, not in `Allowed implementation paths`.
- **Block** if a Plan silently changes `configs/base.py` thresholds, research assumptions, or strategy semantics without explicit Design approval.

### 2. Vertical Slicing, Dependencies & Ponytail Minimality (Mandatory)

Check against [`.agent/rules/L1_Engineering_Process.md`](../../rules/L1_Engineering_Process.md) and [`.agent/rules/ponytail.md`](../../rules/ponytail.md):

- Tasks must be organized as **independently verifiable vertical slices** with explicit dependencies (`Dependencies`), exact file paths, verification commands, and expected outputs—without requiring external ticket files.
- Apply Ponytail minimality below `L0` safety, approved Design invariants, compatibility, and `configs/base.py` SSOT: prune speculative registries, single-product factories, unrequested refactors, and single-implementation interfaces that lack an approved boundary justification.
- Never use Ponytail to strip required trust-boundary validation, Fail-Closed handling, restart/idempotency logic, or approved contract interfaces.

### 3. Targeted Topology & Consumer Compatibility Check (When Shared Boundaries Change)

Skip this check for pure documentation or single-file internal changes that do not alter shared interfaces. When a Plan modifies a shared SSOT function, public helper, contract, schema, CLI flag, or persistent field:

1. Use targeted Graphify queries (`graphify query "<exact_symbol>"` / `graphify path "<Source>" "<Target>"`) as discovery clues when `graphify-out/graph.json` is current; treat stale/inferred edges as advisory only.
2. Always verify candidate callers in actual source files and run `rg` on changed JSON/JSONL keys, CLI flags, event types, and file paths (call graphs miss dynamic file/transport consumers).
3. Classify verified consumers:
   - Needs code change → must be in `Allowed implementation paths` and covered by a Task (`P0` if omitted).
   - Remains compatible without edit → list in `Affected but unchanged` with a regression test.

### 4. Consequence-Driven Verification & Test Quality (Ref: `L1` §2–§3)

Verify that each Task's verification matches its actual risk and output type per [`.agent/rules/L1_Engineering_Process.md`](../../rules/L1_Engineering_Process.md):

- **Core logic, bugfixes, and contract changes**: require public-interface `RED → GREEN → REFACTOR` TDD with **independently derived expected values** (`L1` §2 Rule 4).
- **Fixture provenance (`L1 Rule 15`, alias `Old L1 Rule 11`)**: single-module pure logic and fault-injection tests may use minimal local synthetic inputs; cross-module/cross-boundary positive tests must use canonical upstream constructors/serializers or upstream strict loaders.
- **Pure documentation, static rules, and read-only diagnostic outputs**: require matching structural/existence/conservation/reference checks; do **not** require fake TDD unit tests.
- **Persistent artifact & `Rule 17` boundary (`L1` §3.3)**:
  - Require the full immutable profile authority tuple, sealed-tree rules, and independent Verifier execution (`scripts/governance/verify_artifact_schema.py`) **only** when the artifact directly grants operational authority, controls trading/capital admission, or underpins an irreversible migration—or when the task reuses an existing frozen Rule 17 profile.
  - For ordinary recomputable or exploratory cross-stage research outputs, require declared consumer contracts, structural checks, and independent semantic evidence (hand-calculated oracle vectors or bug-independent consumer checks), but do **not** mandate a duplicate standalone verifier script or full profile ceremony.
  - Do **not** impose `Rule 17` profile tuples, `flock`/`fsync` crash matrices, or standalone Verifiers on human-readable reports, exploratory one-off statistics, or single-module internal helpers.

### 5. Safety, Alpha Methodology & Market-Data Evidence Boundaries (When Applicable)

- **`L0` Safety**: Research/shadow code must never import `src/execution`, read private keys/balances, emit `TradeIntent`/live orders, or flip `RISK_LIVE_TRADING_ENABLED` (`False`).
- **`L2` Alpha & Replay Semantics** (when the Plan concerns strategy/event/replay/market-data research; see [`.agent/rules/L2_Alpha_Research_Methodology.md`](../../rules/L2_Alpha_Research_Methodology.md)):
  - Preserve naming boundaries (`watch event` vs `research_case` vs `SignalCandidate` vs `TradeIntent`).
  - Enforce point-in-time (PIT) alignment (no future look-ahead), symbol-grouped replay paths (no cross-symbol contamination), explicit empty/missing-data status, and runtime data commit policy (`data/*.jsonl` not committed; commit only reports/reviews or tiny deterministic fixtures).
  - Require explicit source-quality and direction preservation where relevant (for example, in crypto market-data tasks, labeling partial streams like Binance `forceOrder` as lower-bound proxies rather than full tape, preserving long/short liquidation `side`, and reporting dataset time span/coverage). Treat concrete window numbers (such as `<72h` smoke vs `<30d` regime coverage or specific return thresholds) as **scenario/stage-specific inputs** from the approved Design rather than universal rules for unrelated tasks.

See [`REVIEW_CHECKLIST.md`](REVIEW_CHECKLIST.md) for the rapid pre-flight checklist and [`PRESSURE_TESTS.md`](PRESSURE_TESTS.md) for benchmark review scenarios.
