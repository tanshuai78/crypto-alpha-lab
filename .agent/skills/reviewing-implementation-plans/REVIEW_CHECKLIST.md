# Plan Review Checklist

Use this as a fast pre-flight checklist.

## Scope

- [ ] State-mutating Plan has a bounded `Allowed Change Scope`.
- [ ] Applicable implementation, verification, documentation, and runtime artifact paths are listed; if the full template is retained, inapplicable categories say `none`.
- [ ] Compatible consumers that require no edits are listed under `Affected but unchanged` with verification evidence.
- [ ] No unscoped mutating command such as `ruff check --fix .`, repository-wide auto-format, or `git clean -fdx`.
- [ ] Title matches actual evidence and output.
- [ ] Goal, tasks, outputs, and Done Definition agree.
- [ ] Plan states what it proves and what it does not prove.
- [ ] Research/proxy/shadow/live labels are accurate.
- [ ] Next allowed decision is explicit.

## Minimality

- [ ] Each Task is necessary for an approved requirement, safety invariant, compatibility obligation, or verification gate.
- [ ] Existing helpers and stdlib/native capabilities are reused where suitable.
- [ ] No speculative registry, one-product factory, or new one-implementation interface without an approved boundary reason.
- [ ] Ponytail does not remove validation, failure handling, restart recovery, idempotency, required SSOT config, or existing layer interfaces.

## Topology and Contract Impact

- [ ] Shared SSOT/public helper/contract changes use targeted Graphify query/path checks when the graph is current.
- [ ] Graphify clues are verified at actual source lines; inferred/ambiguous edges are not blockers alone.
- [ ] Changed JSON keys, schema fields, event types, CLI flags, and file paths are searched with `rg`.
- [ ] Verified consumers requiring edits appear in `Allowed implementation paths` and Tasks.
- [ ] Verified compatible consumers appear in `Affected but unchanged` with regression/integration tests.
- [ ] A clean or stale Graphify result is not treated as proof that no consumers exist.

## Safety

- [ ] No private API / secrets / balance access in research code.
- [ ] No `src.execution` import unless explicitly intended and reviewed.
- [ ] No `TradeIntent` from observation/research paths.
- [ ] Live switches remain unchanged and default false.
- [ ] Observation outputs are `executable=false`.
- [ ] Risk thresholds live in SSOT.

## Layer Semantics

- [ ] Watch events are not called trade candidates.
- [ ] Research cases are not emitted as `SignalCandidate` unless Layer C/trade gate passes.
- [ ] Shadow/replay outputs cannot be mistaken for live approval.
- [ ] Proxy-only data is not labeled `execution_ready`, `live_ready`, or `orderbook_aware`.

## Data Lineage

- [ ] Source data and transformations are explicit.
- [ ] Source quality is declared: full / partial / sampled / proxy / delayed.
- [ ] No future data leakage.
- [ ] No cross-symbol path contamination.
- [ ] Empty/missing data emits explicit status.
- [ ] Optional inputs degrade gracefully.
- [ ] Coverage duration and coverage ratio are reported.

## Market Data Evidence Semantics

- [ ] Exchange streams that are partial/sampled are labeled as such.
- [ ] Binance `forceOrder` is treated as partial lower-bound proxy, not full liquidation tape.
- [ ] Kline close is treated as price proxy, not executable price.
- [ ] Mark price is treated as reference/risk price, not fill price.
- [ ] Partial-source metrics are not used alone for live/phase escalation.
- [ ] Full-data thresholds are not compared to proxy data without warning.

## Directional Evidence

- [ ] Long/short features preserve direction.
- [ ] Liquidation raw data includes `side` and normalized `liquidation_side`.
- [ ] Aggregation separates long and short liquidation notional.
- [ ] Directional strategy summaries split long vs short.

## Tests

- [ ] Happy path.
- [ ] Reject/failure branches.
- [ ] Boundary thresholds.
- [ ] Empty input.
- [ ] Missing fields.
- [ ] Missing optional file.
- [ ] No future data.
- [ ] No cross-symbol path.
- [ ] Source-quality metadata.
- [ ] Safety grep.
- [ ] Report placeholder check.

## Parameters

- [ ] Personal-investor cost assumptions are conservative.
- [ ] Stress cost scenario exists where relevant.
- [ ] Holding windows are justified.
- [ ] Thresholds are not relaxed only to create signals.
- [ ] Long/short, regime type, and symbol tier are split in reports.
- [ ] Aggregate performance is not used as sole evidence.

## Reports and Artifacts

- [ ] Summary JSON contains required fields, not just console print.
- [ ] Review document includes real values, not placeholders.
- [ ] Runtime `data/*.jsonl` is not committed unless converted to a small fixture.
- [ ] Reports go under `reports/` and decisions under `docs/reviews/`.

## Decision Gate

- [ ] Decision is one of: approve, conditional approve, block, defer.
- [ ] Required fixes are concrete and testable.
- [ ] Stop conditions are explicit.
- [ ] The plan cannot accidentally progress to live/execution.
