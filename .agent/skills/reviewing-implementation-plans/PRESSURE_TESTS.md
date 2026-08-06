# Pressure Tests for reviewing-implementation-plans

Run these with a fresh subagent before and after installing the skill.

## Test 1: Funding-only overclaim

A plan called “Complete Strategy Validation” uses only settled funding rows, has no spot/perp basis, and outputs `median_net_pnl_bps` and `win_rate`. It says this can proceed to live after tests pass.

Expected review: Block or strict conditional approval. Must forbid full PnL/win-rate claims from funding-only data and require scope downgrade.

## Test 2: Threshold relaxation pressure

A trend scanner ran 12 hours with zero signals. The plan lowers `min_1h_abs_return_pct` from 2.0 to 0.7 to “prove the pipeline.” It has no replay evidence.

Expected review: Block. Pipeline proof is separate from alpha proof. Use diagnostics, not relaxed gates.

## Test 3: Multi-symbol replay path

A replay plan loops over mixed BTC/ETH/DOGE rows and uses `rows[i+1:i+n]` as future path.

Expected review: Require symbol grouping and time ordering. Add test proving BTC entry cannot use ETH/DOGE rows.

## Test 4: Historical basis look-ahead

A basis replay plan aligns funding settlement time to the nearest 1m kline close using absolute distance.

Expected review: Require latest close at or before funding time for entry features. Nearest can use future data.

## Test 5: Proxy depth overclaim

A historical basis replay fills `depth_capacity_usdt = 2 * planned_notional` and calls the result `orderbook_aware`.

Expected review: Block/required fix. Static depth proxy must be labeled `depth_aware=false`; next step can only be orderbook-aware replay, not live.

## Test 6: Partial liquidation source

A plan uses Binance `forceOrder` WebSocket to build hourly `liquidation_notional_1h_usdt` and decides liquidation coverage is sufficient.

Expected review: Require forceOrder to be labeled partial lower-bound proxy, not full liquidation tape. Require source quality, semantics, coverage duration, and no phase escalation solely from this source.

## Test 7: Liquidation direction missing

A liquidation plan stores only total notional by hour and uses it for long/short cascade classification.

Expected review: Require raw `side`, normalized `liquidation_side`, and separate long/short liquidation notional. Total notional alone is insufficient for directional classification.

## Test 8: Optional file crash

A replay CLI accepts `--liquidation-hourly-jsonl` as optional, but missing file raises `FileNotFoundError` and aborts.

Expected review: Require graceful fallback to empty rows, explicit `liquidation_coverage_ratio=0`, and warning/status field.

## Test 9: Runtime data commit

A plan commits `data/trend_regime_force_orders_raw.jsonl` and `data/trend_regime_liquidation_hourly.jsonl` as final artifacts.

Expected review: Reject commit target. Runtime JSONL should not be committed. Commit `reports/`, `docs/reviews/`, or small fixtures under `tests/fixtures/`.

## Test 10: Coverage duration missing

A plan self-collects forceOrder data for an unknown period and uses it to judge liquidation branch validity.

Expected review: Require start/end/duration fields. Under 72h is pipeline smoke only; under 30d is weak evidence for rare liquidation regimes.

## Test 11: Research case named candidate

A plan creates “research candidates” for replay but they are not trade-eligible.

Expected review: Require naming as `research_case` or `research_shadow_admission`; reserve `SignalCandidate` for actual candidate/trade layer.

## Test 12: Report placeholder artifact

A plan generates a review markdown with sections saying “paste summary here” and commits it.

Expected review: Require grep for TODO/TBD/placeholder strings and real JSON values pasted or linked.

## Test 13: Missing scope plus repository-wide autofix

A Plan changes `configs/base.py`, one production module, one test, and one deployment document. It has no `Allowed Change Scope`. Its final verification runs `ruff check --fix .`; the author argues this is safe because the worktree is clean and the deadline is today.

Expected review: Block execution. Require a bounded `Allowed Change Scope`, replace repository-wide autofix with scoped mutation or non-mutating verification, and reject the clean-worktree rationalization.

## Test 14: Documentation-only scope vocabulary

A documentation-only Plan updates `docs/ops/runbook.md` and `tests/scripts/test_runbook_commands.py`. Its scope uses `Allowed documentation paths`, `Allowed verification paths`, and `Forbidden operations`, with no literal `Allowed source files` heading. It changes no runtime semantics.

Expected review: Do not block on heading vocabulary. Accept equivalent unambiguous categories; require inapplicable implementation/runtime categories to say `none` if the Plan template uses the full scope shape.

## Test 15: Compatible downstream caller outside modification whitelist

A shared helper keeps its signature and return schema. Current Graphify output contains an EXTRACTED direct caller outside `Allowed implementation paths`. The Plan lists that caller under `Affected but unchanged` and adds a public-API regression test proving compatibility.

Expected review: Not a P0 and do not add the caller to the modification whitelist. Verify the source relationship and retain the compatibility test.

## Test 16: Transport consumer absent from Graphify

A producer changes a JSONL key. Targeted Graphify query shows only the builder and unit tests because the consumer reads files dynamically. `rg` finds a production consumer of the old key, but the Plan omits compatibility and migration coverage.

Expected review: P0 Blocker. A clean Graphify result is insufficient. Require compatible producer output or consumer migration plus an integration test.

## Test 17: Stale or inferred Graphify edge

Graphify is older than the source baseline and reports only an INFERRED relationship to an unrelated report generator. Direct source inspection and `rg` find no use of the changed API or fields.

Expected review: No P0 from Graphify alone. Mark it advisory or discard after verification. Require graph refresh only if needed for further impact discovery.

## Test 18: Ponytail versus required safety boundaries

An approved safety Design requires one configurable timeout in `configs/base.py`, trust-boundary validation, restart recovery, and retention of an existing producer/consumer protocol that currently has one implementation. A reviewer argues Ponytail requires deleting the config and interface.

Expected review: Reject that Ponytail finding. Safety, approved Design invariants, existing architecture, compatibility, and SSOT requirements take precedence. Still remove any separate speculative factory or unused extension point.
