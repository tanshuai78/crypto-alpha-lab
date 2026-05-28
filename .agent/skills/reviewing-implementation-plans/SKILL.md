---
name: reviewing-implementation-plans
description: Use when reviewing implementation, refactor, bugfix, replay/research, deployment, migration, data-pipeline, or strategy plans before coding, especially when safety, tests, evidence semantics, market-data quality, thresholds, execution risk, or scope boundaries may be unclear
---

# Reviewing Implementation Plans

## Overview

Plan review is pre-flight risk control. The goal is not to make a plan sound better; it is to decide whether it is safe, testable, bounded, and worth executing.

A good review answers one of four decisions:

- **Approve**: safe and well-scoped.
- **Approve with required fixes**: direction is right, but specified fixes are mandatory before execution.
- **Block**: plan would create unsafe, misleading, untestable, or incorrectly scoped work.
- **Defer / request missing inputs**: current evidence is insufficient to review honestly.

The review must identify hidden scope creep, weak evidence, unsafe assumptions, missing tests, ambiguous contracts, bad thresholds, misleading completion criteria, and market-data semantics that could produce false confidence.

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
3. 必须修正的问题
4. 参数 / 阈值 / 证据边界审核
5. 建议执行顺序
6. 最终意见
```

For high-risk trading/replay/data plans, add:

```text
7. 数据证据语义风险
8. 本轮能证明什么 / 不能证明什么
9. 禁止从本轮结果推出什么结论
```

## Core Review Flow

### 1. Scope Truthfulness

Do not trust the title. Compare title, stated goal, tasks, outputs, and Done Definition.

Flag if:

- title says “complete validation” but data only supports a skeleton or proxy;
- plan says “trade candidate” but produces only research cases;
- plan says “basis-aware” but has no basis path;
- plan says “live-ready” but uses historical/proxy/shadow evidence only;
- plan says “fix bug” but also changes thresholds or strategy semantics.

The review must state the true scope in plain language.

### 2. Safety Boundary

For trading or high-risk systems, check:

- no private API usage in research paths;
- no account balance or secret read;
- no `src/execution` import unless explicitly intended and safe;
- no `TradeIntent` or order object from observation/research layers;
- live switch remains default false;
- observation/shadow outputs have `executable=false` or equivalent;
- config changes are in the designated SSOT;
- no implicit increase in net exposure uncertainty.

Block if research code can accidentally route to execution.

### 3. Layer Semantics

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

### 4. Data Lineage and Evidence Semantics

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

### 5. Market Data Evidence Semantics

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

### 6. Directional Evidence Must Preserve Direction

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

### 7. Coverage Duration Requirement

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

### 8. Runtime Data Commit Policy

Do not commit runtime data artifacts directly unless explicitly intended as small fixtures.

Default rule:

```text
data/*.jsonl                → do not commit
reports/**                 → commit if audit artifact
docs/reviews/**            → commit if decision artifact
tests/fixtures/**          → commit only small deterministic samples
```

Flag any plan that commits large runtime JSONL files to git.

### 9. Tests and Verification

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

### 10. Parameter and Threshold Review

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

### 11. Done Definition Quality

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
- proxy result is treated as live-ready.

## High-Risk Red Lines

Block or require fixes if any appear:

1. Research/shadow code imports execution or can generate live order intent.
2. Private API or balance reads appear in observation/research plans.
3. Proxy/partial data is labeled as complete or execution-ready.
4. Partial liquidation stream is used as full liquidation volume.
5. Long/short directional claims are made without directional raw fields.
6. Replay uses future close/price for entry features.
7. Replay path crosses symbols.
8. Funding-only data outputs full PnL/win-rate claims.
9. Runtime data files are committed as final evidence.
10. Empty or missing data produces an “ok” strategy conclusion.
11. Thresholds are relaxed to make signals appear without replay evidence.
12. The plan changes risk invariants outside the approved SSOT.
13. Review report can be generated with TODO/TBD/placeholders.
14. Candidate/shadow counts are mixed across regimes, directions, or symbol tiers without subgroup analysis.

## Anti-Rationalization Table

| Claim in plan | Required challenge |
|---|---|
| “No signals means threshold too strict” | Could be market state; prove with historical replay before changing thresholds. |
| “Historical proxy PnL is positive” | Is it orderbook-aware? Are costs realistic? Is source complete? |
| “Liquidation notional is available” | Is it full tape or partial forceOrder proxy? Does it preserve side? |
| “Candidate count increased after relaxing parameters” | Did edge survive conservative assumptions? Or only optimistic assumptions? |
| “Data pipeline works” | Does it prove strategy edge or only link health? |
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

- “Direction is correct, but `forceOrder` must be marked partial lower-bound proxy and cannot drive liquidation threshold decisions alone.”
- “The replay must group by symbol before building future paths; otherwise DOGE entry can use XRP path.”
- “The plan says optional liquidation file, but missing file currently crashes. Add graceful fallback and explicit `liquidation_coverage_ratio=0`.”
- “The report should not commit `data/*.jsonl`; commit `reports/` and `docs/reviews/`, or small fixtures only.”
- “Layer B should be named research case, not candidate, to avoid confusion with `SignalCandidate`.”
