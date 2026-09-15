# Stage 1.6F Evidence-to-Schema Delta Design

- Date: 2026-09-14
- Status: `draft_for_review`
- Parent Design: `docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md`
- Parent Design SHA-256: `87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c`
- Scope authority: user authorized this Design delta only; this is not Plan, implementation, commit, deployment, network collection, SSH, runtime, replay, paper-trading, live-trading, signal, or execution authority.

## 1. Delta Claim

The Parent Design correctly froze the research question, C-side retained-byte transaction, matching protocol, W1/W2 semantics, and zero-permission boundary. It deliberately deferred the exact historical market input, reducer, and output schema until real evidence existed. This Delta closes only that deferred implementation boundary using the verified local evidence package.

This Delta does not modify Parent Design bytes, B/C writers or loaders, the 1.6B historical range, matching thresholds, W1/W2 definitions, Stage 1.5/1.6E runtime paths, or any permission. It does not add a downloader, HTTP client, exchange API, background process, database, queue, alpha conclusion, PnL calculation, execution model, or terminal observer.

## 2. Confirmed Evidence And Authority

### 2.1 Parent C input remains the only event authority

F receives the exact `SOURCE_EXPORT` and `C_H2_COMPLETED_ROOT` supplied by the operator. It first calls the frozen C loader:

```python
load_completed_adapter_audit(project_root, completed_root, source_export)
```

The loader is authority for C completion, not a convenience summary. The call must return a complete manifest with `source_audit_passed is True`. The Parent Design Section 4.1 nine-artifact retained-byte transaction remains unchanged and mandatory. F never treats a root pathname, copied summary, fixture, or historical report as equivalent C authority.

The current Reality Snapshot used to establish this Delta is:

```text
SOURCE_EXPORT:
data/external_signal_shadow/stage1_6b/historical_backfill/
hist_20260913_072358_671ce365/sealed_exports/
4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090

C_H2_COMPLETED_ROOT:
data/external_signal_shadow/stage1_6a/sealed_export_source_audits/
stage1_6a_audit_4d1c5092c5ce_20260913T072500Z

completion_manifest.json SHA-256:
226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0

source_export_receipt.json SHA-256:
07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e
```

These values are a reviewed Reality Snapshot, not a hard-coded runtime allowlist. Each future run independently validates its supplied C inputs through the frozen loader and retained-byte transaction.

### 2.2 Frozen local market-evidence package

The first F implementation consumes one local, immutable `market_evidence_root`. Its root manifest is exactly:

```text
relative path: gap02_evidence_manifest.json
schema_version: stage1_6f_gap02_evidence_manifest_v1
current reviewed SHA-256: 9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f
```

The package has 148 ZIP artifacts and their decompressed CSV counterparts. The manifest records each relative ZIP/CSV path, SHA-256, byte length, CSV header, row count, and first/last row. The reader accepts only regular, non-symlink descendants of `market_evidence_root`; it verifies every listed ZIP and CSV byte length and SHA-256 before parsing any CSV. It rejects missing, duplicate, extra manifest paths, path escape, unreadable ZIP, hash mismatch, size mismatch, malformed CSV, or a header different from the exact applicable schema below.

The following auxiliary authority artifacts are exact manifest-bound inputs:

| Relative path | SHA-256 | Role |
| --- | --- | --- |
| `historical_universe_snapshot_20250115.json` | `63449f932636893a0b24466d04e79b2456553ad8d9502f677f8d6b66d197d5e8` | 878-prefix historical S3 census and 380/498 active partition |
| `historical_control_candidates_baseline_provenance_reef_20250115.json` | `e34da67918daa8be84a7dbc647918decc40bdd6a9fd4bf8a521ae9ce1f2b68ad` | 365-candidate 168-hour baseline provenance |
| `historical_control_universe_reef_20250115.json` | `b3042945036fe4825b7fc1e40150be438805a706b8dd1e5b80ac849a3808cdb0` | exclusion chain and deterministic top-three controls |
| `denominator_archive_coverage_matrix_all_intersecting.json` | `b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8` | archive availability only, including W2 truncation fields |
| `settlement_rule_mapping_37contracts.json` | `40b338651644d9d141f075f1dc78b8f219b435d52a8e9246eebbe33b3b4b7601` | event-to-settlement-rule mapping |
| `data_semantics_contract.json` | `5a096c50b194521ccc1402884ee15364783b1201a2c5fb0d289d64548cd38fd2` | price, funding, and BookDepth usage boundaries |

The package is a local read-only input. Its current files prove one REEF anchor and three selected controls, not complete raw-market coverage for every C denominator row. A C row without an exact matching evidence identity remains in the denominator with `diagnostic_incomplete`; it is not silently removed and does not make the package invalid.

## 3. Scope And Non-Goals

### 3.1 In scope

1. An offline F runner that consumes a C completed root, a source export, and one verified local market-evidence package.
2. A retained-byte C reader and market-evidence verifier, each fail-closed before any reducer or output writer.
3. Reconstruction of the complete C event/symbol denominator, per-row eligibility and exclusion reasons.
4. Parent Design Section 6 deterministic matching when an event has an exact verified control-universe artifact; otherwise `control_universe_unverified` or `unmatched`.
5. W1/W2 descriptive-only price, basis, funding, OI, visible-depth, and aggregate-trade diagnostics at the granularity actually present in verified bytes.
6. A new independent, atomic F diagnostic bundle and a read-only reviewer for it.

### 3.2 Explicit non-goals

1. Any download, retry, S3/HTTP/API request, credential, private endpoint, SSH, VPS action, daemon, queue, database, or modification of B/C/E roots.
2. Any use of the historical artifacts as point-in-time availability proof, replay permission, trade signal, execution feasibility, net-cost, PnL, Sharpe, win-rate, MAE/MFE, position, borrow, or liquidation attribution evidence.
3. L2 reconstruction, quoted spread, executable slippage, order-book replay, maker behavior, causal forced-flow conclusion, or terminal settlement-value reconstruction from 1-hour bars.
4. Changing Parent Design matching parameters or manufacturing controls when the exact historical control artifact is unavailable.

## 4. Exact Input Contract

### 4.1 Invocation and identity

The future offline CLI has exactly these required path arguments:

```text
--project-root
--source-export
--completed-root
--market-evidence-root
--output-root
```

It has no URL, API, retry, credential, network, live-root, or permissive fallback argument. `output_root` must not already contain a completed F bundle. The input identity stored in the output is:

```text
completion_manifest fields returned by the C loader:
  input_export_id
  input_manifest_sha256
  source_export_receipt_sha256
  authoritative_artifacts[] {relative_path, sha256, byte_length}

F-retained C bytes SHA-256 for each of the exact nine Parent Design paths
market_evidence_manifest_sha256
market_evidence_manifest_byte_length
auxiliary artifact relative paths, SHA-256, and byte lengths
```

`completed_root`, `source_export`, and `market_evidence_root` paths may be recorded for diagnostics but are not identity substitutes. F rejects a C identity mismatch, an auxiliary reference mismatch, a package schema mismatch, or a source/event identity conflict as `market_evidence_invalid` or `source_invalid`, before invoking matching or any market reducer.

### 4.2 CSV schemas and semantics

All CSV parsing is strict UTF-8 with one exact header and finite numeric values. Timestamp fields are exact UTC epoch milliseconds; no unit inference or timestamp-length heuristic is permitted.

| Family | Exact header | Permitted use |
| --- | --- | --- |
| `klines_1h`, `klines_1m`, `mark_price_1h`, `index_price_1h`, `premium_index_1h` | `open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore` | separate bar-aligned descriptive price series only |
| `metrics_5m` | `create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio` | OI value and reported ratio series only |
| `funding_rate` | `calc_time,funding_interval_hours,last_funding_rate` | actual discrete funding observations only |
| `book_depth` | `timestamp,percentage,depth,notional` | discrete visible cumulative depth ladder only |
| `agg_trades` | `agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker` | aggregate executed-trade descriptors only |

`klines_1h` is the only tradable price series. `index_price_1h` and `mark_price_1h` are non-tradable. `premium_index_1h` is never a direct basis. `book_depth` must preserve the signed percentage level and is a low-frequency visible-depth proxy, not BBO, L2, or slippage evidence. `is_buyer_maker` may be counted as the raw flag's two populations but must not be renamed to forced buying/selling. Funding is not borrow interest and does not permit carry PnL.

### 4.3 Temporal alignment and coverage

Parent windows remain exact:

```text
W1 = [Tpub, Tpub + 12h)
W2 nominal = [Tsettlement - 24h, Tsettlement)
W2 paired = [max(Tpub, Tsettlement - 24h), Tsettlement)
```

For each metric, F retains the original requested interval and computes an `observed_interval` only from raw timestamps that fall within the requested interval. It records `first_observed_at_ms`, `last_observed_at_ms`, `expected_interval_start_ms`, `expected_interval_end_ms`, duplicate/conflict counts, and gaps. A bar may be used only when its own timestamp is in the interval; F does not stretch a bar across a boundary, interpolate, forward-fill, or use a download timestamp. Therefore a non-hour-aligned `Tpub` can yield an observed bar-aligned subinterval; it is descriptive-only and never claimed to be exact 12-hour coverage.

For W2, the output must also retain `nominal_w2_start_ms`, `paired_w2_start_ms`, `paired_w2_end_ms`, `is_truncated_by_tpub`, and `truncation_reason`. `Tsettlement <= Tpub`, absent settlement, or a missing valid rule mapping prevents paired W2 calculation. A 1-hour index series is insufficient to verify the historical 1-second settlement average; `settlement_value_status=unavailable_insufficient_1s_index` is mandatory unless exact required 1-second inputs are a future separately approved input profile.

## 5. Reducer And Status Contract

### 5.1 Reducer order

```text
C loader complete verification
-> exact nine-artifact retained-byte transaction
-> market package manifest and all listed-byte verification
-> C denominator and per-row eligibility reconstruction
-> exact event/control evidence identity join
-> deterministic matching
-> per metric/window parse, time validation, and coverage accounting
-> descriptive reducers
-> atomic F bundle publication
```

No later stage runs after a global prior-stage failure. Per-event missing market evidence is not global corruption: it remains a denominator row with the exact incomplete status.

### 5.2 Descriptive reducers

All reducers emit raw quantities and preserve the observed interval. They are not return, PnL, execution, or causal reducers.

| Metric | Required verified series | Output when available | Required unavailable status |
| --- | --- | --- | --- |
| Perpetual price path | `klines_1h` for event and selected controls | first/last close, `10000 * (last_close / first_close - 1)`, and equal-weight event-minus-control bps only when all selected controls share the same observed timestamps | `price_path_unavailable` |
| Perp/index basis | aligned `klines_1h` and `index_price_1h` | per-timestamp `10000 * (perp_close / index_close - 1)` and first/last/median, separately for event and controls | `basis_unavailable` |
| Mark/index basis | aligned `mark_price_1h` and `index_price_1h` | `10000 * (mark_close / index_close - 1)` as non-tradable risk-price basis | `mark_basis_unavailable` |
| Funding | `funding_rate` observations in interval | ordered `(calc_time, funding_interval_hours, last_funding_rate)` and count; no summed carry PnL | `funding_unavailable` |
| OI | `metrics_5m` | ordered `sum_open_interest_value`, first/last/delta and raw reported ratios | `oi_unavailable` |
| Visible depth | `book_depth` | per signed percentage level: count, first/last/median `notional`; no spread/slippage | `visible_depth_unavailable` |
| Aggregate trades | `agg_trades` | count, total `price * quantity`, and counts/notional by raw `is_buyer_maker` value | `agg_trade_unavailable` |
| Settlement mechanism | exact event mapping plus 1-second index inputs for its rule | rule version, expected sample count, and verified rule-input result only | `settlement_value_unavailable_insufficient_1s_index` |

If an event has no exact historical control-universe artifact, all unpaired comparisons are unavailable. F may still produce event-only raw descriptions, explicitly labeled `unmatched_event_only_description`; it must not emit event-minus-control values. A selected control lacking an identical observed timestamp intersection censors that specific paired metric. F does not replace, reweight, or retrospectively select another control.

### 5.3 Statuses

`source_invalid` and `market_evidence_invalid` are global fail-closed errors: zero F bundle, zero reducer, zero writer. Valid inputs always produce a bundle, including zero eligible rows, but its completion state is determined by the exact rows:

| Status | Meaning |
| --- | --- |
| `diagnostic_incomplete` | at least one predeclared event/symbol/window/metric is unavailable, censored, unmatched, out of historical range, or truncated |
| `descriptive_only` | one specific metric/window has all required verified inputs and an explicit observed interval; no alpha or causal upgrade |
| `protocol_executed_complete` | every predeclared in-range eligible metric has valid full required input, no truncation/censor, and valid evaluation; this does not establish the mechanism, alpha, or feasibility |

Empty denominators, zero eligible rows, all unmatched rows, or all unavailable metrics are valid `diagnostic_incomplete` bundles, never a positive result.

## 6. Output, Crash, And Compatibility Contract

Each successful offline invocation writes a fresh independent directory with this exact layout:

```text
<output-root>/
  stage1_6f_input_receipt.json
  stage1_6f_event_denominator.jsonl
  stage1_6f_metric_diagnostics.jsonl
  stage1_6f_diagnostic_summary.json
  stage1_6f_diagnostic_bundle_manifest.json
```

Every output record contains `schema_version=stage1_6f_historical_mechanism_diagnostic_v1`, the input identity in Section 4.1, `parent_article_id`, `contract_id`, canonical symbol, original and observed intervals, controls or exclusion reasons, metric status, and all permission flags in Section 8. The summary contains counts by `source_invalid`/`market_evidence_invalid` only when no bundle exists; otherwise counts by denominator, eligibility, matching, metric availability, truncation, censor, and result status. It must not contain a trade recommendation, position, expected profit, or `alpha` verdict.

All files except the bundle manifest use atomic write-and-replace. The manifest is written last, after each listed output file is read back and its SHA-256 and byte length match its manifest entry. A reader accepts a bundle only when the manifest exists, has exact schema `stage1_6f_diagnostic_bundle_manifest_v1`, every listed artifact matches, and `bundle_state` is either `diagnostic_incomplete` or `protocol_executed_complete`. A stale temporary file, partial root, missing manifest, duplicate manifest entry, or changed artifact is not a bundle and cannot be read as one. Re-running with identical verified inputs may produce a new root with equivalent semantic rows, but must never overwrite a completed root.

No compatibility reader for legacy F output is needed because F has no prior writer. Legacy B/C/E artifacts remain immutable and are never upgraded to F input or output schemas.

## 7. Acceptance Invariants And Required Proofs

| ID | Invariant | Required proof |
| --- | --- | --- |
| INV-FD01 | C loader-validated bytes are F-consumed bytes | canonical C loader positive fixture; mutate one returned-manifest-listed artifact after loader return and prove zero market reducer/output writer |
| INV-FD02 | market evidence is manifest-bound and offline | canonical 148-artifact package positive fixture; mutate one CSV/ZIP/hash/header/path or add path escape and prove `market_evidence_invalid`, zero reducer/output |
| INV-FD03 | denominator survives missing evidence | C fixture with eligible, ineligible, out-of-range, unmatched, and no-evidence rows; output count and reasons preserve all rows |
| INV-FD04 | matching is historical, deterministic, and immutable | REEF universe/provenance fixture; verify 878/380/15/365/120/245 conservation, top AXL/AKT/REZ order; mutate post-Tpub data or candidate order and prove matching is unchanged/rejected |
| INV-FD05 | W1/W2 preserve original versus observed interval | exact boundary, non-hour Tpub, `Tsettlement <= Tpub`, AIA/PORT3 truncation, stop/missing data fixtures; no full-W2 claim on truncated rows |
| INV-FD06 | metric semantics cannot be upgraded | OHLCV-only, mark-only, premium-only, BookDepth-only, and funding-only fixtures each produce only their allowed descriptors and exact unavailable statuses for prohibited claims |
| INV-FD07 | settlement rule is not settlement value | V1/V2 mapping positives and wrong/missing mapping negatives; 1-hour index input must produce `settlement_value_unavailable_insufficient_1s_index` |
| INV-FD08 | manifest-last crash behavior | inject failure before manifest and mutate output after manifest; reader rejects both partial and hash-mismatched roots |
| INV-FD09 | no network, upstream mutation, or permissions | monkeypatch socket/HTTP and B/C write functions; assert zero calls, upstream hashes unchanged, and every authority flag is exact `False` |

## 8. Safety And Authority Boundary

All of the following are exact `False` in every valid output and are reject-on-non-bool/non-false input/output fields:

```text
RISK_LIVE_TRADING_ENABLED
trade_signal_allowed
paper_trading_allowed
live_trading_allowed
execution_engine_allowed
private_api_allowed
authenticated_api_allowed
order_api_allowed
alpha_interpretation_allowed
execution_feasibility_claim_allowed
net_cost_or_profit_claim_allowed
replay_allowed
point_in_time_directional_replay_allowed
```

The F implementation is a local read-only historical diagnostic. It does not authorize collection, deployment, VPS operation, strategy development, or any trade-related action.

## 9. Open Questions And Gate

No unresolved question changes the first implementation path: the first implementation receives only verified local C and market-evidence roots and reports unavailable data explicitly.

The following are deferred, non-blocking only because the first implementation must reject them rather than infer a fallback:

1. A new market package schema/version or an additional event's raw evidence requires a new evidence review and a Delta before the reader accepts it.
2. Exact 1-second index inputs for settlement-value validation require a separate source contract and Delta.
3. PIT availability, strategy, cost, execution, and terminal live observation require separate Designs.

Current authority after this candidate is reviewed: `design_review_allowed=true`; `implementation_plan_allowed=false`; `implementation_allowed=false`; `deployment_allowed=false`; `runtime_action_allowed=false`.
