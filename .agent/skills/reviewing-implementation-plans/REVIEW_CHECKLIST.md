# Plan Review Checklist

Use this pre-flight checklist to audit an Implementation Plan against [`.agent/rules/L1_Engineering_Process.md`](../../rules/L1_Engineering_Process.md) and the approved Design.

## 1. Scope & Authority (`Allowed Change Scope`)

- [ ] State-mutating Plan includes an explicit `Allowed Change Scope` block (`Allowed implementation paths`, `Allowed verification paths`, `Allowed documentation paths`, `Allowed generated/runtime artifacts`, `Affected but unchanged`, `Forbidden`; inapplicable categories marked `none`).
- [ ] Compatible consumers requiring no code edits are listed under `Affected but unchanged` with compatibility verification.
- [ ] No unscoped mutating command (`ruff check --fix .`, repo-wide auto-format, `git clean -fdx`) or automatic per-task `git commit`.
- [ ] Plan does not alter `configs/base.py` thresholds, research semantics, or authority boundaries without explicit Design approval.
- [ ] Execution baseline capture (`BASE_SHA`, pre-execution `git status`) and independent completion audit (`audit-plan-completion`) are specified for formal Plans.

## 2. Vertical Slicing, Dependencies & Minimality (Ponytail)

- [ ] Tasks are broken into independently verifiable vertical slices with explicit `Dependencies`, exact file paths, verification commands, and expected outputs (no external ticket files required).
- [ ] Existing helpers and Python stdlib are reused; no speculative registries, single-product factories, or unrequested refactors.
- [ ] Minimality does not remove required safety gates, Fail-Closed checks, restart/idempotency logic, or approved contract boundaries.

## 3. Topology & Consumer Compatibility (When Shared Boundaries Change)

- [ ] Changed shared functions, schemas, JSON/JSONL keys, CLI flags, and file paths are checked against actual source consumers via `rg` (and targeted Graphify queries when applicable).
- [ ] Graphify `INFERRED`/stale results are verified against source before raising a blocker.
- [ ] Verified consumers needing edits are in `Allowed implementation paths`; compatible consumers are in `Affected but unchanged`.

## 4. Consequence-Driven Verification & Fixture Grading (`L1` §2–§3)

- [ ] Core logic, bugfixes, and contract changes use public-interface `RED → GREEN → REFACTOR` TDD with **independently calculated expected values**.
- [ ] Single-module internal pure logic and fault-injection tests are permitted to use minimal local synthetic inputs (`L1 Rule 15`).
- [ ] Cross-module/cross-boundary positive contract tests derive from canonical upstream constructors/serializers or strict loaders (`L1 Rule 15`).
- [ ] Pure documentation, static rules, or read-only diagnostic scripts use matching structural/reference/conservation verification rather than fake TDD unit tests.
- [ ] `Rule 17` independent Verifier and full sealed-tree profile requirements are included **only** when the artifact directly grants operational authority, controls trading/capital admission, underpins an irreversible migration, or reuses an existing frozen Rule 17 profile (`L1` §3.3). Recomputable cross-stage research outputs declare consumer contracts and independent semantic evidence without forcing a standalone duplicate verifier.

## 5. Safety & Alpha Research Semantics (When Applicable)

- [ ] No private API, secret/balance access, `src/execution` import, or `TradeIntent` generation in research/shadow paths; `RISK_LIVE_TRADING_ENABLED` remains `False`.
- [ ] For `L2` Alpha/replay tasks: independent sampling unit, PIT anti-hindsight alignment, symbol-grouped replay paths, outcome distribution metrics, cost/capacity boundaries, and explicit `phenomenon_supported / evidence_insufficient / alpha_candidate / falsified` status semantics match the approved Design.
- [ ] Partial/proxy market-data sources (e.g., `forceOrder`, kline close, mark price) and directional fields (`side`) are accurately labeled and never overclaimed as live-executable proof.
- [ ] Runtime `data/*.jsonl` outputs remain uncommitted unless converted into small deterministic test fixtures.
