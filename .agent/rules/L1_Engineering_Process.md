---
trigger: always_on
---

---
type: rule
name: L1 – Superpowers Engineering Process Rules
---

# L1 – Superpowers Engineering Process Rules (Authoritative SSOT)

**Priority: HIGH (Level 1 — Subordinate only to L0 Financial Safety; authoritative full text for project engineering rules)**

`AGENTS.md`, `.agent/workflows/*`, project skills under `.agent/skills/*`, and `docs/production_artifacts/tri_agent_prompt_library_CN.md` reference this file as the single source of truth (SSOT) for engineering process discipline and must not introduce stricter hidden gates.

---

## 1. Task Sizing: Brief Plan vs. Formal Chain

1. **Brief Plan (简短方案)**: A task may use an inline brief plan (traceable goal, allowed scope, forbidden actions, and verification method in conversation or task notes, without standalone Design/Plan files) when **all** of the following hold:
   - The goal is clear, local, and reversible;
   - It does **not** alter L0 financial safety, authority boundaries, frozen research semantics, public contracts/schemas, persistence lifecycle, deployment, or cross-module runtime flow;
   - Verification can be completed within existing boundaries.
   - Simply touching a file under `src/` does not automatically mandate standalone Design/Plan documents; however, explicit user requests for a formal Design/Plan always govern.
   - A brief plan still requires explicit user scope authorization (a clear local modification request suffices; questions or drafting requests do not authorize implementation). Significant logic changes still require independent review; local low-impact edits may be verified directly by the executor without forcing a full three-model loop. Financial execution changes never bypass independent review or L0 shadow validation.
2. **Formal Chain (正式链)**: Required for non-trivial new capabilities, major refactors, or any change to the boundaries above (`Design → Independent B Review → User Design Approval → Implementation Plan → Independent B Review → User Plan Approval → Controlled Implementation → Independent Completion Audit`).
   - Do not downgrade a task merely because it is labeled "offline", nor impose full runtime/replay ceremony on a comment-only edit in a trading module.
3. **Selective Clarification (需求澄清)**:
   - Never ask the user facts that can be verified directly from the workspace (`configs/base.py`, `docs/roadmap.md`, source, tests, or git history).
   - When impact is unclear after workspace inspection, ask only narrow questions that change implementation path, scope, research semantics, allowed side effects, completion evidence, or result consumers (e.g., whether numbers are illustrative examples or frozen parameters).
   - Define task-critical terms inline in the active document; do not mandate standalone `GLOSSARY.md`, `ADR`, `spec`, or `ticket` files.
   - Generic template simplification never overrides `.agent/rules/L2_Alpha_Research_Methodology.md` (§15 remains mandatory for alpha/strategy research Designs, using explicit definitions or justified `N/A`).

---

## 2. Core Engineering & Verification Discipline

1. **Structured Flow (`§2.1`)**: Follow `inspect → plan → implement → verify`. Convert every non-trivial task into verifiable goals before coding:
   - **Bugfix**: Use `.agent/skills/systematic-debugging` to confirm root cause via logs or minimal reproduction first, then reproduce with a failing test before fixing.
   - **Refactor**: Capture and verify existing behavior with tests before restructuring, and prove behavior preservation after.
   - **Feature / Validation**: Define boundary and invalid-input checks before implementation.
2. **Skill Adaptation Boundary (`§2.2`)**: Before invoking third-party skills (`brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `requesting-code-review`, `receiving-code-review`, `verification-before-completion`, `ponytail`), project workflows supply path, approval, and non-commit constraints. If an upstream skill conflicts with project boundaries (e.g., auto-commit or unapproved scope expansion), pause the conflicting action and follow project rules without editing the upstream skill file.
3. **Syncing State (`§2.3`)**: Always sync from `docs/roadmap.md`, `configs/base.py`, and relevant source modules at session start. Never reference non-existent `src/main.py` or `src/config.py`.
4. **TDD & Independent Expected Values (`§2.4`)**:
   - Prioritize testing stable observable behavior boundaries; complex pure functions may be tested directly without inventing wrapper interfaces solely to "test through a public interface".
   - Expected values in assertions MUST come from hand calculation, known ground-truth vectors, or an independent specification—never by calling or copying the tested production algorithm to self-prove correctness.
   - Property/conservation checks complement but do not replace required integration checks.
5. **Defensive Review Reception (`§2.5`)**: When receiving review or audit feedback (`.agent/skills/receiving-code-review`), perform objective source/test verification and push back with evidence if a suggestion violates project invariants, YAGNI, or approved scope. Avoid performative agreement. Mandatory review findings must cite the requirement, concrete evidence, reachable failure or critical verification gap, and minimum fix; style preferences are advisory.
6. **Closure Revision Discipline (`§2.6`)**: When revising a Design or Implementation Plan after review findings, load `.agent/skills/closure-revision/SKILL.md`. Review only previous `OPEN` / `PARTIALLY_CLOSED` findings, directly affected proof edges, and revision-introduced defects; do not reopen closed areas without new evidence, and do not fabricate self-proving claims solely to force an "all CLOSED" label.
7. **Step Gate & Scope Control (`§2.7`)**: Every multi-step task must specify intended change, verification command, and expected result. Do not proceed past a failed gate without user approval.

---

## 3. Consequence-Driven Mechanisms & Rule Alias Mapping (Rules 15–17)

Historical documents may refer to these rules by either numbering convention; both resolve to the definitions below:
- **Rule 15 (alias: Legacy L1 Rule 11)** — *Test & Fixture Provenance Integrity*
- **Rule 16 (alias: Legacy L1 Rule 12)** — *Architectural Drift Classification & Repair Routing*
- **Rule 17** — *Cross-Boundary Artifact Contract & Risk-Proportionate Verification*

### Rule 15 (Legacy L1 Rule 11): Test & Fixture Provenance Integrity
- **Internal Pure-Logic & Fault Tests (Synthetic Allowed)**: Unit tests for pure calculation functions, time/window boundaries, streaming chunk boundaries, parser fault injection, and local failure branches may use minimal synthetic inputs or local test doubles, provided they do not claim real archive coverage, upstream provenance authenticity, or cross-module contract compatibility.
- **Cross-Boundary Positive Claims (Canonical Required)**: Any test or verification claiming compatibility with an upstream module, strict loader, or persisted stage artifact MUST derive positive inputs from canonical upstream constructors/serializers, upstream strict loaders, or verified upstream artifact bytes—never from handcrafted dictionaries or fabricated hashes/attestations that bypass upstream validation.
- **Negative Tests**: Negative/fail-closed tests must isolate the failure cause; single-point mutations are preferred when they isolate the invariant, while compound state mutations are permitted when the lifecycle/failure scenario requires them and the mutations are explicitly listed.

### Rule 16 (Legacy L1 Rule 12): Architectural Drift Classification & Repair Routing
Never mask a mismatch between implementation and upstream reality using silent fallbacks (e.g., permissive `.get(k, default)` for required contract fields, fake hashes, or layering violations). Route mismatches strictly by actual impact:

| Classification | Condition | Required Action & Approval Boundary |
|---|---|---|
| `BLOCKED_IMPLEMENTATION_DEFECT` (Local Fix) | Implementation or test deviates from approved requirements and can be fixed within `Allowed Change Scope` without altering Design contracts, permissions, or frozen research semantics | Fix locally within allowed paths and run targeted regression; do **not** rewrite Design/Plan or treat path allowance as permission to change semantics |
| `BLOCKED_SCOPE_DRIFT` (Bounded Plan Supplement) | Fix requires only adding an implementation/test/doc path or task without changing Design goals, contracts, permissions, or research semantics | Halt out-of-scope edits first; submit a bounded Plan supplement bound to the original Plan path/SHA for B review of the affected scope and explicit user approval (**no new Design required**). Check identity dependencies (`Plan SHA`, `source_bundle`, run authorization, `RUN_ID`, bound evidence): re-verify or re-authorize if frozen source bundle/authority is touched; adding an out-of-bundle test file alone does not automatically require full data replay or a new `RUN_ID` |
| `BLOCKED_SPEC_DRIFT` (Design & Plan Change) | Approved Design/Plan contradicts frozen upstream reality, or the change alters Design contracts, permissions, research semantics, or persistence lifecycle | Halt affected work and escalate with concrete contradiction evidence (`Failed Invariant`, `Upstream SSOT`, `Contradiction Proof`, `Proposed Delta`) for Design and Plan review/approval |

When an audit finding lacks evidence or contradicts frozen source contracts, investigate, request minimal missing evidence, or reject with source evidence (`rejected_with_evidence`) rather than blindly editing code.

### Rule 17: Cross-Boundary Artifact Contract & Risk-Proportionate Verification
*(Prospective governance contract update to `docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md` §3.2–3.3, SHA-256 `73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4`; historical files and existing J-A/J-B/J-C profiles/obligations remain unchanged and non-retroactive.)*

1. **Consequence-Driven Mechanism Selection**: Engineering mechanisms must be justified by concrete failure consequences in the active Design/task description (without creating a separate risk-ledger artifact):
   - **External calls / credentials / order placement / deployment**: Require explicit operational authorization, capability isolation, and defined failure behavior. Design/Plan approval never implies operational/deployment authorization.
   - **Irreplaceable data or shared mutable state**: Protect against overwrite; provide backup or recovery proportionate to loss impact. Do **not** mandate full multi-state crash recovery state machines for recomputable outputs.
   - **Multi-writer contention or concurrent consumer visibility**: Use single-writer constraints, completion markers, atomic rename, or locks when concurrent access actually exists. Do **not** mandate `flock` on every file or claim atomic rename alone proves power-loss durability.
   - **Post-fault durability requirements**: Define persistence/fsync checks only where the storage contract requires surviving a crash without recomputation. Do **not** mandate two-phase `fsync` by default for all tasks.
   - **Single-run recomputable outputs with no concurrent consumer**: Protect read-only inputs, fail with non-zero exit status on error, and prevent partial outputs from masquerading as success. Recomputability never excuses skipping mathematical, temporal (PIT), or sample-conservation verification.
2. **Stratified Cross-Boundary Artifact Verification**:
   - **Contract Obligation (All Cross-Boundary Artifacts)**: Every persistent artifact crossing producer/consumer, process, lifecycle, or stage boundaries must declare its structure, data semantics, provenance, failure states, and consumption conditions, and enforce them in its producer/consumer checks (hash matching alone is insufficient).
   - **High-Impact / Authority Artifacts (Full Profile & Standalone Verifier Required)**: When an artifact directly grants operational authority, controls trading/capital admission, or underpins an irreversible migration—or when a task reuses an existing frozen Rule 17 profile—it MUST satisfy the full immutable profile authority tuple, exact key sets, sealed-tree rules, audit identity binding, and a standalone verifier whose acceptance logic does not depend on the target producer/loader implementation.
   - **Recomputable / Exploratory Cross-Boundary Research Artifacts (Selective Verification)**: When a new research artifact does not trigger the high-impact or existing-profile conditions above, a dedicated standalone verifier script duplicating producer logic is **not** required by default. Instead, the Design/Plan must specify its actual consumers, structural checks, independent semantic evidence (hand-calculated oracle vectors, alternative calculation path, or consumer check not sharing the target bug; producer+loader sharing the same algorithm is insufficient), and uncovered limits for B review and user approval. Such verification must not be labeled as passing a legacy full Rule 17 profile. Promoting an exploratory output to formal downstream admission or trading authority requires completing the corresponding boundary review and verification before consumption.

---

## 4. Completion, Tooling Timing & Authority Isolation

1. **Completion Standard (`§4.1`)**: Completion requires verifiable evidence for the task's stated goal, allowed scope, target behavior, production wiring, and required checks—never a mechanical "tests green + matching SHA" shortcut.
2. **Audit Scope & Read-Only Delivery (`§4.2`)**: Reviews and completion audits inspect committed, staged, unstaged, and untracked changes against the recorded pre-execution baseline (`BASE_SHA` + status/patch snapshot); an empty `HEAD` diff never proves no work occurred, and missing baselines must be reported as provenance uncertainty without fabricating history or overwriting user files. Completion audits are read-only and delivered in the response by default; do **not** build dedicated audit Recorder scripts unless an approved contract explicitly requires automated consumption of the audit report.
3. **Conditional Tooling (`anti_shortcut_scan.py` & `graphify`, `§4.3`)**:
   - Run `python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"` during final verification for applicable Python changes (and earlier when touching critical boundaries); documentation-only tasks do not invent Python scan tasks, unless required by an active migration plan.
   - Use `graphify query / path / affected` as an advisory impact-discovery aid when modifying shared helpers, contracts, schemas, or CLI boundaries, and always verify against actual source lines and `rg`. Do not force `graphify update .` after every task.
4. **Authority Isolation (`§4.4`)**: A `complete` audit verdict means only that implementation within the declared scope is verified. It **never** authorizes `git commit`, `git push`, merge, deployment, SSH, runtime execution, paper trading, or live trading (`RISK_LIVE_TRADING_ENABLED` remains `False`).
