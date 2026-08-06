---
name: reviewing-implementation-plans
description: Use when reviewing implementation, refactor, bugfix, replay/research, deployment, migration, data-pipeline, or strategy plans before coding, especially when safety, tests, evidence semantics, market-data quality, thresholds, execution risk, scope boundaries, Allowed Change Scope, or Graphify topology collisions may be unclear
---

# Reviewing Implementation Plans (Enhanced V3)

## Overview

Plan review is pre-flight risk control. The goal is not to make a plan sound better; it is to decide whether it is safe, testable, bounded, minimally complex, and worth executing.

A good review answers one of four decisions:

- **Approve**: safe, well-scoped, YAGNI-compliant, and fully bounded with an explicit `Allowed Change Scope`.
- **Approve with required fixes**: direction is right, but specified fixes (e.g. missing verified impact coverage, missing path whitelist, weak tests) are mandatory before execution.
- **Block**: plan would create unsafe, misleading, untestable, over-engineered, or incorrectly scoped work.
- **Defer / request missing inputs**: current evidence or design inputs are insufficient to review honestly.

The review must identify hidden scope creep, weak evidence, unsafe assumptions, missing tests, ambiguous contracts, bad thresholds, misleading completion criteria, un-scoped formatter commands, YAGNI violations, and Graphify topology collisions.

## When to Use

Use this skill for plans that change or create:

- implementation logic;
- refactors;
- bug fixes;
- trading strategy logic;
- research/replay pipelines;
- market-data collection;
- report generation;
- configs and thresholds;
- tests;
- deployment scripts;
- risk gates;
- operational workflows.

Do not use for casual brainstorming or explanation-only requests unless the user explicitly asks for plan review.

## Review Output Format

Use this structure unless the user requests a different format:

```text
结论：通过 / 条件通过 / 不建议执行 / 阻塞。

1. 总体判定
2. 做得对的地方
3. 必须修正的问题 (P0 Blocker / P1 Warning)
4. Allowed Change Scope 包含性审核
5. Ponytail YAGNI 防过度工程审核
6. Graphify 拓扑依赖碰撞审核
7. 参数 / 阈值 / 证据边界审核
8. 建议执行顺序
9. 最终意见
```

For high-risk trading/replay/data plans, add:

```text
10. 数据证据语义风险
11. 本轮能证明什么 / 不能证明什么
12. 禁止从本轮结果推出什么结论
```

Multi-Agent Review Findings (if participating in multi-agent review):
Every finding MUST report: `finding_id | severity (P0/P1/P2) | artifact_section | code_evidence | problem | required_change | verification`.

## Core Review Flow

### 1. Scope Truthfulness & Allowed Change Scope Gate (Mandatory)

Do not trust the title. Compare title, stated goal, tasks, outputs, and Done Definition.

**Mandatory Header Audit**:
Every Implementation Plan that mutates repository or runtime state MUST declare an explicit **`Allowed Change Scope`** block near its top. Use exact paths where known and bounded globs only for a defined file family. Include every applicable category; when retaining the full template, write `none` for an inapplicable category.

```markdown
## Allowed Change Scope

Allowed implementation paths:
- src/.../contract.py
- src/.../loader.py
- configs/base.py

Allowed verification paths:
- tests/.../test_contract.py
- tests/.../test_loader.py

Allowed documentation paths:
- docs/...

Allowed generated/runtime artifacts:
- data/...  # generated only; not committed

Affected but unchanged:
- src/.../consumer.py
  - compatibility evidence: tests/.../test_consumer.py

Forbidden:
- unrelated formatter changes
- full-repository autofix (e.g. ruff check --fix .)
- unscoped destructive cleanup (e.g. git clean -fdx)
- threshold changes outside SSOT
```

**Gate Rules**:
- Require Fix if `Allowed Change Scope` is missing, uses unbounded directory claims, or omits applicable implementation/verification/documentation/runtime categories. Legacy labels such as `Allowed source files` and `Allowed tests` are acceptable when their meaning is unambiguous.
- Block if the Plan allows unscoped mutating commands (e.g. `ruff check --fix .`, `git clean -fdx`, or repository-wide auto-formatters). A repository-wide non-mutating check may remain a verification step, but it does not authorize fixing unrelated findings.
- Do not force an affected compatible consumer into the modification whitelist. Record it under `Affected but unchanged` with concrete compatibility evidence.
- Flag if title says “complete validation” but data only supports a skeleton or proxy;
- Flag if plan says “fix bug” but also changes thresholds or strategy semantics.

### 2. Ponytail YAGNI & Anti-Overengineering Audit (Mandatory)

Audit every Task against the Ponytail Decision Ladder:

1. **Does this need to exist at all? (YAGNI)**: Require removal of speculative tasks, "for later" abstractions, or generic registries nobody requested.
2. **Already in this codebase?**: Flag tasks that attempt to re-implement existing helpers, state loaders, or validators.
3. **Stdlib / Native does it?**: Flag hand-rolled algorithms when Python stdlib (`datetime`, `hashlib`, `pathlib`, `json`, `math`) already provides them.
4. **Single-implementation interface / factory?**: Flag newly introduced interfaces with one implementation or factories with one product only when no approved contract boundary or existing architecture requires them.
5. **Shortest working diff**: Require each task to specify the minimal code change rather than monolithic refactors.

Block or require fixes if the Plan introduces bloat, boilerplate, or unrequested extensibility.

Apply this precedence before raising a Ponytail finding:

```text
L0 safety and data-loss prevention
→ approved Design invariants
→ existing project architecture and compatibility
→ required SSOT/config boundaries
→ Ponytail minimality
```

Ponytail must not remove trust-boundary validation, crash/restart recovery, idempotency, explicit failure handling, required calibration/threshold configuration, or an existing producer/consumer interface. It removes speculative complexity after those requirements are satisfied.

### 3. Targeted Graphify Topology Collision Check (Mandatory)

Graphify is an impact-discovery tool, not correctness proof. Run this check when a Plan changes a shared SSOT function, public helper, contract, schema, CLI, or transport boundary. Skip it for documentation-only changes with no runtime semantics.

DO NOT run broad or vague Graphify queries (e.g. `graphify query "整个流程"`). Instead, execute targeted checks for modified SSOT functions, contracts, and helpers:

**Step 1: Identify SSOT / Public Helper Targets**:
Extract all modified core functions or classes declared in the Plan (e.g., `build_formal_schedule_revision_row`).

**Step 2: Execute Targeted Graphify Queries**:
- Confirm `graphify-out/graph.json` represents the source baseline being reviewed. If it is stale, refresh it or treat its output as advisory only.
- For single function/class: `graphify query "<exact_function_name>"`
- For a known cross-module relationship: `graphify path "<Source>" "<Target>"`
- If Graphify is unavailable or stale, continue with `rg` and direct source inspection; do not skip impact analysis.

**Step 3: Verify Topology Clues Against Source**:
- Inspect relevant `calls`, `imports`, `references`, and data-sharing edges. `INFERRED` and `AMBIGUOUS` edges are leads, never blockers by themselves.
- Verify each candidate consumer at actual code lines. For JSON/schema/JSONL/CLI/file-path changes, also use `rg` on changed field names, flags, event types, and paths because these dependencies may have no function-call edge.
- A clean Graphify result does not prove that no consumer exists.

**Step 4: Classify Verified Impact**:

| Verified result | Required Plan treatment |
|---|---|
| Consumer requires code change | Add it to `Allowed implementation paths` and a Task. Missing coverage is P0. |
| Consumer remains compatible without edits | Add it to `Affected but unchanged` with a regression/integration test. Do not expand the modification whitelist. |
| Candidate edge is irrelevant or unverified | Record as advisory or discard after source inspection. No P0. |
| Transport/schema consumer is omitted and compatibility is unproven | P0 until compatibility or migration coverage is planned. |

**P0 requires verified source evidence**, not Graphify output alone.

### 4. Safety Boundary

For trading or high-risk systems, check:

- no private API usage in research paths;
- no account balance or secret read;
- no `src/execution` import unless explicitly intended and safe;
- no `TradeIntent` or order object from observation/research layers;
- live switch remains default false (`RiskLimits.live_trading_enabled = False`);
- observation/shadow outputs have `executable=false` or equivalent;
- config changes are in the designated SSOT (`configs/base.py`);
- no implicit increase in net exposure uncertainty.

Block if research code can accidentally route to execution.

### 5. Layer Semantics

Preserve naming boundaries:

- **watch event**: observation only;
- **research case**: useful for replay/shadow only;
- **SignalCandidate**: candidate for strategy review, not execution;
- **TradeIntent**: intent to execute;
- **Order**: exchange action.

Red flags:

- research-only item named “candidate” without hard guard;
- funding-only or proxy-only replay outputs `net_pnl` / `win_rate` as if complete;
- proxy dataset labeled `live_ready`, `execution_ready`, or `orderbook_aware`;
- Layer B/research layer generating `SignalCandidate` when Layer C/trade gate should be required.

### 6. Data Lineage and Evidence Semantics

Trace the chain:

```text
source data → filtering → alignment → feature construction → classification → replay/shadow → report → decision
```

Check:

- no future data leakage;
- no cross-symbol path contamination;
- no empty data silently producing “success”;
- missing data produces explicit status;
- source quality is declared;
- proxy fields cannot be mistaken for executable or complete data;
- coverage duration and coverage ratio are reported;
- runtime artifacts are not committed as evidence unless they are converted into audit reports or tiny fixtures.

### 7. Market Data Evidence Semantics

This is mandatory for crypto market-data plans.

Every external data source must state whether it is:

- full;
- sampled;
- partial;
- delayed;
- proxy;
- exchange-estimated;
- locally collected;
- third-party reconstructed.

Examples:

- `forceOrder` stream is a **partial liquidation proxy**, not full liquidation tape.
- kline close is a **price proxy**, not executable price.
- mark price is a **risk/reference price**, not fill price.
- funding-only rows cannot prove basis-aware PnL.
- static depth proxy is not orderbook depth.

If source is partial/proxy, require fields such as:

```json
{
  "source": "binance_forceorder_ws",
  "source_quality": "self_collected_partial_history",
  "semantics": "partial_snapshot_lower_bound",
  "coverage_quality": "historical_proxy_not_execution_aware"
}
```

Block or require fixes if proxy data is compared to full-data thresholds without warning.

### 8. Directional Evidence Must Preserve Direction

If a feature affects long/short classification, raw data must preserve direction.

For liquidation data, require:

- raw `side`;
- normalized `liquidation_side`;
- long liquidation notional;
- short liquidation notional;
- event count by side;
- source quality;
- hour bucket or timestamp semantics.

Do not approve a long/short liquidation-cascade plan that only stores total liquidation notional without side.

### 9. Coverage Duration Requirement

Any replay or live-collected historical dataset must report:

```text
start time
end time
duration hours/days
row count
symbol count
coverage by symbol
missing coverage
source quality
```

Decision guidance:

- under 72h: link test / pipeline smoke only;
- under 30d: weak strategy evidence for event regimes;
- no rare-event coverage: cannot conclude strategy invalid;
- partial-source coverage: may support diagnostics but not phase escalation alone.

### 10. Runtime Data Commit Policy

Do not commit runtime data artifacts directly unless explicitly intended as small fixtures.

Default rule:

```text
data/*.jsonl                → do not commit
reports/**                 → commit if audit artifact
docs/reviews/**            → commit if decision artifact
tests/fixtures/**          → commit only small deterministic samples
```

Flag any plan that commits large runtime JSONL files to git.

### 11. Tests and Verification

Require tests for:

- happy path;
- reject/failure branches;
- boundary thresholds;
- empty input;
- missing fields;
- no future leakage;
- no cross-symbol path contamination;
- optional file missing behavior;
- source-quality metadata;
- safety grep;
- report artifact placeholder check.

For replay/shadow logic, require:

- symbol grouping;
- time ordering;
- no use of future data for entry features;
- `insufficient_*` status when path is missing;
- summary fields included in JSON, not only printed.

### 12. Parameter and Threshold Review

For personal-investor crypto strategies, default to conservative review:

- fewer high-quality signals are better than many noisy signals;
- use high-liquidity universes;
- include base cost and stress cost;
- keep holding windows short until evidence supports longer exposure;
- long/short must be split;
- regime types must be split;
- BTC/ETH and altcoins must be split;
- aggregate averages are insufficient.

Do not approve threshold relaxation merely to create signals.

### 13. Done Definition Quality

A good Done Definition says:

- what was built;
- what evidence exists;
- what the evidence proves;
- what it does **not** prove;
- what decision is allowed next;
- what remains prohibited.

Red flags:

- “tests pass” is the only done criterion;
- report exists but can contain placeholders;
- no explicit decision gate;
- no status for empty/no-data outcomes;
- proxy result is treated as live-ready;
- missing `Allowed Change Scope` whitelist.

## High-Risk Red Lines

Block or require fixes if any appear:

1. A state-mutating Plan lacks a bounded `Allowed Change Scope` or allows unscoped mutating commands (`ruff check --fix .`, `git clean -fdx`).
2. Source verification proves a consumer requires code or migration work, but the Plan omits that work; or a transport/schema consumer is omitted with no compatibility evidence.
3. Plan violates Ponytail YAGNI after safety, approved Design invariants, existing architecture, compatibility, and SSOT requirements are satisfied.
4. Research/shadow code imports execution or can generate live order intent.
5. Private API or balance reads appear in observation/research plans.
6. Proxy/partial data is labeled as complete or execution-ready.
7. Partial liquidation stream is used as full liquidation volume.
8. Long/short directional claims are made without directional raw fields.
9. Replay uses future close/price for entry features.
10. Replay path crosses symbols.
11. Funding-only data outputs full PnL/win-rate claims.
12. Runtime data files are committed as final evidence.
13. Empty or missing data produces an “ok” strategy conclusion.
14. Thresholds are relaxed to make signals appear without replay evidence.
15. The plan changes risk invariants outside the approved SSOT (`configs/base.py`).
16. Review report can be generated with TODO/TBD/placeholders.
17. Candidate/shadow counts are mixed across regimes, directions, or symbol tiers without subgroup analysis.

## Anti-Rationalization Table

| Claim in plan | Required challenge |
|---|---|
| “No signals means threshold too strict” | Could be market state; prove with historical replay before changing thresholds. |
| “Historical proxy PnL is positive” | Is it orderbook-aware? Are costs realistic? Is source complete? |
| “Liquidation notional is available” | Is it full tape or partial forceOrder proxy? Does it preserve side? |
| “Candidate count increased after relaxing parameters” | Did edge survive conservative assumptions? Or only optimistic assumptions? |
| “Data pipeline works” | Does it prove strategy edge or only link health? |
| "Plan doesn't need file whitelist" | Every state-mutating Plan requires bounded `Allowed Change Scope`; when using the full template, mark inapplicable categories `none`. |
| "Graphify found it, so it must be edited" | Verify source impact. Compatible consumers belong in `Affected but unchanged` with tests, not the modification whitelist. |
| "Graphify found nothing, so there are no consumers" | Search changed schema fields, JSON keys, CLI flags, event types, and file paths with `rg`; call graphs miss transport coupling. |
| "Ponytail says one implementation means delete the interface" | Retain interfaces required by safety, approved Design, compatibility, SSOT, or existing architecture. |
| “Report generated successfully” | Does it contain real JSON values and decision gates? |
| “Optional input missing should fail” | Optional means graceful fallback with explicit status. |
| “Runtime JSONL should be committed for reproducibility” | Prefer reports/reviews; use small fixtures for tests. |

## Required Review Language

Be explicit:

```text
This plan can prove X.
This plan cannot prove Y.
It must not be used to decide Z.
```

For trading plans, always identify the next allowed decision:

```text
watchlist_only
continue_data_collection
continue_partial_source_collection
funding_persistence_study_required
orderbook_aware_replay_only
eligible_for_phase1b_review
blocked_due_to_insufficient_evidence
```

## Examples of Good Review Findings

- **Scope Gate**: “Block: this state-mutating Plan lacks `Allowed Change Scope` and proposes `ruff check --fix .`, which can rewrite unrelated files.”
- **Verified Topology Gap**: “Block: Graphify suggested `consumer.py`; source inspection confirms it reads the changed JSON key, but the Plan provides neither a compatible producer shape nor a consumer migration/integration test.”
- **Compatible Consumer**: “No scope expansion: `consumer.py` remains API-compatible. Record it under `Affected but unchanged` and keep the targeted regression test.”
- **Ponytail YAGNI**: “Require Fix: Task 3 creates a generic `RevisionRegistryFactory` for a single registry implementation. Prune factory and use direct instantiation.”
- “Direction is correct, but `forceOrder` must be marked partial lower-bound proxy and cannot drive liquidation threshold decisions alone.”
- “The replay must group by symbol before building future paths; otherwise DOGE entry can use XRP path.”
- “The plan says optional liquidation file, but missing file currently crashes. Add graceful fallback and explicit `liquidation_coverage_ratio=0`.”
