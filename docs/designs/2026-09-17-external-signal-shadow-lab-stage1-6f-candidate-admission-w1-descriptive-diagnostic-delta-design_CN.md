# Stage 1.6F Candidate Evidence Admission and Multi-Symbol W1 Descriptive Diagnostic Delta Design

**日期：** 2026-09-17  
**状态：** `draft_for_review`  
**类型：** 离线只读 Design Delta；不是 Plan、implementation、commit、push、deployment、SSH、network collection、replay、paper-trading、signal、execution 或 live-trading authority。

## 1. 核心问题、结论与最小方案

`expansion_candidate_run_20260917_002` 已完成并通过独立候选根验根，但其 manifest schema 是 `stage1_6f_historical_evidence_expansion_candidate_manifest_v1`，不是旧 F REEF package 的 `stage1_6f_gap02_evidence_manifest_v1`。现有 `verify_market_evidence(...)` 因而正确拒绝此根；不得以扩展 allowlist 或放宽 `REVIEWED_MARKET_EVIDENCE_MANIFEST_SHA256` 的方式绕过该边界。

本 Delta 的唯一目标是建立一个**独立、严格、只读**的 candidate admission consumer，并由其产生 41 个冻结事件的 1h、4h、12h W1 原始描述性诊断。它不改变 REEF 链路，不选择控制组，不计算 event-minus-control、收益、胜率、显著性、alpha、PnL 或任何执行可行性。

最小方案是新增一个共享的 candidate strict loader 和一个独立 W1-only consumer。将现有 collector 内的严格验根逻辑迁入共享 loader，collector 与新 consumer 都调用它；不得从 `src/` 导入 `scripts/`，不得复制第二套验根器。现有 REEF `verify_market_evidence(...)`、REEF runner、REEF bundle 及其输出语义保持不变。

## 2. 已确认事实

### 2.1 冻结 authority packet

| Authority | 路径 | SHA-256 |
| --- | --- | --- |
| Parent F Design | `docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md` | `87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c` |
| F evidence-to-schema Delta | `docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md` | `8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628` |
| Existing F implementation Plan | `docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md` | `6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f` |
| Approved expansion Design | `docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md` | `1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4` |
| Approved expansion Plan | `docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md` | `fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d` |
| Canonical candidate root | `data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002/` | root basename: `expansion_candidate_run_20260917_002` |
| Canonical candidate manifest | `data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002/candidate_manifest.json` | `b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67` |
| One-run network authorization | `configs/authorizations/network_auth_expansion_run_20260917_002.json` | `8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6` |
| Existing REEF evidence manifest | `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json` | `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f` |
| Current candidate collector and strict validator baseline | `scripts/external_signal_shadow/run_stage1_6f_historical_evidence_package_expansion.py` | `200279f3d25e69d06e8bdff238b2894da4c27cfb70e214a10dedf7e072f77a08` |
| Current F source baseline | `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py` | `00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f` |
| Current F diagnostic baseline | `src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py` | `84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3` |

The candidate manifest itself binds the approved expansion Design/Plan, the existing F Design/Plan, C/B roots, coverage-matrix authority and one-run network authorization. This Delta adds no network authority. A future Plan must bind this Delta's approved SHA-256 and must recompute every listed file hash before changing code.

### 2.2 Candidate-root facts

- `candidate_root_state = collection_terminal_with_gaps_or_unproven_data`; this is a truthful terminal state, not a failed collection root.
- The canonical root has exactly 664 ZIP files, 664 CSV files and one final manifest. Independent hash/length recomputation found zero retained-file mismatches.
- The physical ledger is exactly 650 `fetched_verified` and 14 `csv_invalid`; the logical ledger is exactly 691 `fetched_verified` and 14 `csv_invalid`.
- The 41-symbol cohort is exact. Its 369 coverage records are 241 `window_observed`, 114 `rows_observed_continuity_not_proven`, 3 `window_incomplete`, 10 `not_proven`, and 1 `no_rows_observed`.
- `index_price_1h`, `mark_price_1h`, `premium_index_1h`, and both baseline/W1 `klines_1h` records are `window_observed` for every cohort symbol. `metrics_5m` is fully observed for 36 symbols, incomplete for 3 and not proven for 2. `book_depth` is descriptively available but continuity-not-proven for 33 symbols and not proven for 8. Funding has 40 discrete rows-observed records and one no-row record. Aggregate trades have 41 rows-observed-continuity-not-proven records.
- The 14 invalid objects are evidence, not repair candidates: 12 BookDepth ladder-schema changes and two `metrics_5m` files with a missing required source field. They remain in the denominator and never supply a descriptor.
- The older root `data/external_signal_shadow/stage1_6f/candidate_evidence_packages/expansion_candidate_run_20260917_001/` is a forensic-only non-canonical artifact. It is forbidden input even if its bytes can be read.
- All 38 retained C parents have exact-equal `parent_audit_outcomes.source_published_at_ms` and `delisting_notices.source_published_at_ms`. For all 41 candidate W1 `klines_1h` coverage rows, `requested_interval_start_ms` equals that parent value and `requested_interval_end_ms = start + 12h`.
- In the frozen Stage 1.6A producer, `parent_audit_outcomes.source_published_at_ms` is emitted only after the selected trusted detail's BAPI `data.publishDate` is a non-bool integer in the accepted epoch-millisecond range and equals the first-list catalog `releaseDate`. `releaseDate` corroborates this fact; it is not a replacement publication authority. The retained C values `system_available_at_ms=null`, `fact_available_at_ms=null`, and `capture_time_status=historical_unknown` remain unchanged.

### 2.3 Existing consumer boundary

- `verify_market_evidence(...)` accepts only the exact REEF manifest SHA `9e44...`; pointing it at the candidate root yields `market_evidence_invalid: manifest_missing`.
- Current `compute_descriptive_metrics(...)` includes the REEF-only `event_minus_control_bps` field and emits a W2 settlement-mechanism placeholder. It is therefore not an admissible consumer for this Delta's 41-symbol W1-only output.
- The collector currently owns `validate_completed_candidate_root(...)` inside a script. A production `src/` consumer cannot import a script under the project's layering rules; the validator must be promoted once into a shared read-only source module, with collector behavior preserved by delegation.

## 3. Assumptions, Decisions, and Open Questions

### 3.1 Explicit assumptions

1. Candidate archive bytes are historical ex-post observations. `point_in_time_source_validated=false` remains true and prohibits historical directional replay or causal availability claims.
2. A strict candidate-root validation is sufficient to admit bytes into a descriptive consumer only when the root exactly equals the path and manifest identity in Section 2.1. It does not establish market-data continuity beyond each family-specific coverage result.
3. `is_buyer_maker` remains an exchange field label only. It cannot be relabeled as aggressive buy/sell pressure.

### 3.2 Decisions

1. **One exact root, one new consumer.** This Delta admits only `expansion_candidate_run_20260917_002` with the exact manifest SHA. A future collection requires a new admission Delta; no glob, latest-run selection, fallback root or manifest allowlist is permitted.
2. **Shared loader, no duplicated trust boundary.** Move the existing strict root-validation behavior to one `src/` candidate loader; collector and W1 consumer call it. The move is mechanical: its accepted/rejected roots and failure keys must remain equivalent to the baseline validator.
3. **One publication authority and W1 only.** `Tpub` is exactly the verified parent's `parent_audit_outcomes.source_published_at_ms`; the corresponding retained notice field must be equal. It is neither `releaseDate`, download time, `system_available_at_ms`, nor `fact_available_at_ms`. Each event may have separate raw descriptors for `H1=[Tpub,Tpub+1h)`, `H4=[Tpub,Tpub+4h)`, and `H12=[Tpub,Tpub+12h)`. No W2, W3, 24h horizon or settlement interval is created.
4. **Metric-specific inclusion, denominator preservation.** Every one of 41 event rows remains in the output denominator. A metric may emit raw descriptors only if its required family coverage is proven for that event and horizon. Otherwise it emits exactly one `diagnostic_incomplete` record with the immutable candidate coverage status/reason; it is not deleted, filled, imputed or substituted.
5. **Raw descriptive output, not a strategy result.** Cross-event summaries may state `n_denominator`, `n_descriptive`, `n_diagnostic_incomplete`, parent-article count, and the exact Section 6.5 scalar projection. They must not state win rate, expected strategy return, control-adjusted/excess return, signal direction, statistical significance, alpha, economic PnL, cost, borrow, slippage or tradability. `bar_close_change_bps` remains a permitted raw path descriptor only; it is not a strategy return or PnL.
6. **Separate output bundle and exact serialized grammar.** Candidate W1 output uses a new schema and root, never `write_diagnostic_bundle(...)`, never the old REEF filenames and never an overwrite of a prior F bundle. Its strict loader rejects every unknown, missing or type-invalid key recursively; a required-key-only reader is insufficient.

### 3.3 Open questions

| Question | Blocking | Owner / disposition |
| --- | --- | --- |
| Whether a later study should construct point-in-time controls or test W2 terminal convergence | Yes, for that later study only | Separate Design with source-specific point-in-time and 1-second-index evidence; explicitly out of scope here |
| Whether newly collected future roots should join this cohort | Yes, for any new root | A new evidence-to-admission Delta must bind its exact manifest bytes and coverage ledger |
| Whether distributional observations survive a preregistered independent-sample or cost-aware alpha test | Not relevant to this Delta | Deferred; this Design makes no such claim |

No open question changes this Delta's implementation path: the input root, allowed metrics, horizons, exclusions, output schema and fail-closed behavior are fixed.

## 4. Scope and No-Touch Set

### 4.1 Allowed future implementation scope

The future Plan may modify only the minimum files needed to:

- move the existing candidate strict validator to one new `src/research/external_signal_shadow/` module and make the collector delegate to it without semantic drift;
- add one W1-only candidate reader/reducer module, one storage module and one CLI entry point under existing Stage 1.6F paths;
- add focused tests for loader equivalence, candidate admission, raw W1 descriptors, negative mutations and output loading;
- write a fresh, immutable output root under `data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/<run_id>/` only during an approved later implementation run.

Exact filenames are Plan decisions. The Plan must not introduce a database, daemon, queue, scheduler, generic exchange adapter, network client, runtime configuration switch or additional dependency.

### 4.2 Explicit non-goals / No-Touch

- Do not change `REVIEWED_MARKET_EVIDENCE_MANIFEST_SHA256`, `verify_market_evidence(...)`, the current REEF runner/reviewer, REEF fixture, B/C roots, the candidate root, its manifest, the 14 invalid retained bytes, `configs/base.py`, Stage 1.5 or Stage 1.6E.
- Do not call a public/private network endpoint, use credentials, use SSH/VPS, collect a new archive, deploy, commit, push, run a daemon, replay, paper trade or trade.
- Do not select controls, calculate `event_minus_control_bps`, calculate a strategy return, control-adjusted/excess return or economic PnL, use baseline `klines_1h` to make a relative-return claim, emit W2/W3/24h, reconstruct settlement, or produce alpha/cost/execution/tradability conclusions. A Section 6.4 `bar_close_change_bps` raw path descriptor is not prohibited by this boundary.
- Do not delete, rehash, edit, repair or relocate any prior root, including the forensic `001` root.

Any required No-Touch modification is `STOP=BLOCKED_SCOPE_DRIFT`. Any mismatch between this Delta and a frozen parent authority is `STOP=BLOCKED_SPEC_DRIFT`.

## 5. Producer, Loader, Consumer, and Reviewer Contract

| Role | Input / output | Required responsibility |
| --- | --- | --- |
| Existing expansion collector | canonical candidate root | Produces immutable historical candidate bytes and final manifest; no change in collection semantics |
| Shared candidate strict loader | completed root plus exact Design/Plan/network authority arguments | Recomputes and validates all candidate authority, record, ZIP/CSV, coverage and root-state facts; no network and no writer |
| New W1 candidate consumer | one `VerifiedCandidateEvidence` from the shared loader plus verified C input | Reconstructs all 41 denominator rows and emits metric-specific W1 raw descriptions or explicit incompleteness |
| New candidate W1 bundle writer/loader | diagnostic records | Atomically writes and strictly reloads only the new bundle schema |
| Existing REEF F consumer | REEF evidence package only | Unchanged and continues to reject candidate input |
| Future reviewer | completed candidate W1 bundle | Reads, verifies and describes outputs only; never converts them to strategy, execution or alpha authority |

The shared loader returns immutable retained metadata and parsed series keyed by `(parent_article_id, contract_id, canonical_symbol, metric)`. It must preserve `physical_source_object_id`, logical-record identity, `fetch_status`, `coverage_status`, coverage reason, byte hashes and original file paths for every consumed record. It must not return a bare `symbol -> rows` map because that loses event identity when one symbol has more than one contract/event relation. It also returns a per-parent `PublicationAuthority` only when both retained C records carry the same exact `source_published_at_ms`; it never selects the first non-null representation.

## 6. Admission and W1 Data Contract

### 6.1 Candidate admission gate

Admission executes before any denominator reconstruction, reducer, output-directory creation or writer call. It requires all conditions below:

```text
root path == data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002
root basename == manifest.run_id == expansion_candidate_run_20260917_002
SHA256(candidate_manifest bytes) == b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67
schema_version == stage1_6f_historical_evidence_expansion_candidate_manifest_v1
candidate_root_state == collection_terminal_with_gaps_or_unproven_data
canonical strict loader recomputation succeeds
```

Any path alias, symlink, extra/missing file, authority mismatch, changed byte, changed record, root-state mismatch, unknown key, duplicate identity, non-terminal record, unlisted file, malformed ZIP/CSV, coverage mismatch, non-canonical parent or old `001` root is `candidate_admission_invalid`. It produces no W1 bundle.

`collection_terminal_with_gaps_or_unproven_data` is admissible only because this Delta preserves failures at metric level. It must never be relabeled as `full_grid_coverage`, `complete_market_evidence`, or a successful all-metric sample.

### 6.2 Canonical publication-time gate

For every candidate event identity, the consumer derives one `Tpub` before constructing any horizon. It requires all of the following:

```text
parent_audit_outcomes.source_published_at_ms is type int, not bool,
    and 1_000_000_000_000 <= value < 10_000_000_000_000
parent_audit_outcomes.publication_time_status == "present"
delisting_notices.source_published_at_ms is the same exact int
all candidate records selected by window == "w1_shock_12h" for that identity
    have requested/window start == Tpub and requested/window end == Tpub + 12h
```

`Tpub` is recorded with `publication_time_authority = parent_audit_outcomes.source_published_at_ms_selected_trusted_bapi_publishDate`. `metric_window_coverages` use their exact `window == "w1_shock_12h"` selector; `logical_archive_records` use the same exact `window` value. `baseline_168h` records are provenance-only and must not enter this equality gate. Any missing/non-int/bool/out-of-range/conflicting C value, a selected-W1 logical-window mismatch, or a selected-W1 coverage-window mismatch is `STOP=upstream_denominator_authority_invalid`, before output-directory creation. `releaseDate` may be checked only as the retained upstream corroboration already embodied in the verified parent outcome; it cannot be used as a fallback. `Tpub`, download time and manifest request time must never populate an availability field.

### 6.3 Event denominator and metric ledger

The consumer calls the existing frozen `verify_c_input(...)` and `reconstruct_denominator(...)`, then requires its in-range, eligible, non-REEF projection to equal the candidate manifest's exact sorted 41-symbol cohort and full `(parent_article_id, contract_id, canonical_symbol)` identity set. A C row cannot be replaced by a manifest-only row.

For each denominator event and each allowed metric/horizon tuple below, the output creates exactly one metric record. `required coverage` is a necessary condition, not a fallback preference. The allowed tuple count is exactly 19 per event, hence `41 * 19 = 779` metric records. For every allowed tuple, `descriptive_only_count + diagnostic_incomplete_count == 41`; a missing, duplicate or unpermitted tuple is bundle-invalid.

| Output metric and permitted horizon | Required candidate metric coverage | Descriptor condition | If condition fails |
| --- | --- | --- | --- |
| `hourly_bar_observation` / `H1` | `klines_1h/W1 = window_observed` | At least one valid hourly bar whose `open_time` is in H1; this is a row-level observation, not a price return or an H1 endpoint | `diagnostic_incomplete` |
| `price_path` / `H4`, `H12` | `klines_1h/W1 = window_observed` | At least two complete post-Tpub bars with `open_time >= ceil_to_step(Tpub, 1h)` and `close_time < end_ms`, exact grid, no duplicate/conflict/gap | `diagnostic_incomplete` |
| `perp_index_basis`, `mark_index_basis` / `H4`, `H12` | Their two required 1h families are each `window_observed` | At least one complete post-Tpub aligned bar with `open_time >= ceil_to_step(Tpub, 1h)`, `close_time < end_ms`, exact grid and positive Index close | `diagnostic_incomplete` |
| `funding_observations` / `H1`, `H4`, `H12` | `funding_rate/W1 = rows_observed_continuity_not_proven` | At least one finite row whose `calc_time` is in the horizon | `diagnostic_incomplete` |
| `open_interest` / `H1`, `H4`, `H12` | `metrics_5m/W1 = window_observed` | Exact 5m horizon grid has no duplicate/conflict/gap | `diagnostic_incomplete` |
| `visible_depth_proxy` / `H1`, `H4`, `H12` | `book_depth/W1 = rows_observed_continuity_not_proven` | At least one complete valid source ladder snapshot in horizon | `diagnostic_incomplete` |
| `agg_trade_observations` / `H1`, `H4`, `H12` | `agg_trades/W1 = rows_observed_continuity_not_proven` | At least one finite trade row in horizon | `diagnostic_incomplete` |

`premium_index_1h` stays verified provenance-only in this Delta. It cannot be transformed into basis, funding PnL or a carry indicator. Baseline `klines_1h` stays provenance-only and cannot participate in event-relative, matched-control or excess-return output.

### 6.4 Source timestamp authority and exact time rules

For each `H in {1h, 4h, 12h}`:

```text
start_ms = Tpub
end_ms = Tpub + H
include a raw row iff start_ms <= row_timestamp_ms < end_ms
```

The timestamp authority matrix is fixed below. No family may use another field, a file timestamp, archive date, download time, `close_time` as membership, or an inferred timestamp.

| Family | Retained CSV horizon-membership field | Grid field / step | Complete-bar field rule |
| --- | --- | --- | --- |
| `klines_1h`, `index_price_1h`, `mark_price_1h`, `premium_index_1h` | `open_time` | `open_time` / 3,600,000 ms | only for H4/H12 price/basis: `close_time == open_time + 3,600,000 - 1` and `open_time + 3,600,000 <= end_ms` |
| `metrics_5m` | `create_time` | `create_time` / 300,000 ms | N/A |
| `funding_rate` | `calc_time` | no grid | N/A |
| `book_depth` | `timestamp` | no grid | N/A |
| `agg_trades` | `transact_time` | no grid | N/A |

`ceil_to_step(t, step_ms) = ((t + step_ms - 1) // step_ms) * step_ms`. The **observation-open grid** is every grid timestamp `t` with `ceil_to_step(start_ms, step_ms) <= t < end_ms`; it applies only to `hourly_bar_observation` and `metrics_5m`. The **complete-hourly-bar grid** is every 1h open `t` with `ceil_to_step(Tpub, 3,600,000) <= t` and `t + 3,600,000 <= end_ms`; it applies only to H4/H12 `price_path`, `perp_index_basis`, and `mark_index_basis`. Thus a non-integral H4 event has exactly three possible complete hourly bars, an integral H4 event has four, a non-integral H12 event has eleven, and an integral H12 event has twelve. The consumer records the selected source-family audit facts in Section 6.5, not an ambiguous single metric-level coverage value.

The H1 hourly metric deliberately has no `price_change_bps`, `return_bps`, first/last endpoint pair or basis descriptor. A 1-hour half-open interval contains at most one hourly grid open, so a two-close price change would be unreachable. For H4/H12, `price_path` is explicitly `coarse_complete_post_publication_bar_close_proxy`, not an exact publication-time return: only bars fully after `Tpub` and closed before `end_ms` participate. No pre-publication bar, partially post-publication bar or close after `end_ms` may enter a H4/H12 descriptor.

Permitted descriptors are exact raw transformations only:

- `hourly_bar_observation`: the first and last raw OHLC observations whose `open_time` lies in H1, with their exact open/close timestamps, and no price-change field;
- `price_path`: first/last complete bar close, `10000 * (last_close / first_close - 1)`, and the explicit coarse-proxy note; no control-related field;
- `perp_index_basis`: first, last and median of `10000 * (perp_close / index_close - 1)` on aligned timestamps;
- `mark_index_basis`: first, last and median of `10000 * (mark_close / index_close - 1)`, explicitly `non_tradable_reference_only`;
- `funding_observations`: original `(calc_time, funding_interval_hours, last_funding_rate)` tuples and count only; no cumulative carry, PnL or annualization;
- `open_interest`: first/last `sum_open_interest_value`, raw delta and latest `sum_toptrader_long_short_ratio`; no causal interpretation;
- `visible_depth_proxy`: per source percentage level count, first, last and median `notional`, explicitly `visible_discrete_depth_proxy_only_no_slippage`;
- `agg_trade_observations`: original-field partitions by `is_buyer_maker`, count and `price * quantity` notional only, explicitly `exchange_label_only_not_aggressor_inference`.

All numeric inputs and derived values must be finite. No rounding is permitted before storage. The writer uses `json.dumps(..., allow_nan=False)` and the strict loader rejects JSON `NaN`, `Infinity`, `-Infinity`, booleans in every numeric slot, and any non-finite numeric value recursively. For `price_path`, `first_complete_bar_close == 0` is a zero denominator and makes that metric `diagnostic_incomplete`, with `descriptors={}` and no synthetic value. A non-finite value, missing required column, invalid row identity or impossible interval has the same metric-terminal state. Its exact gate reason is emitted through `gate_failures`, not fabricated from a candidate coverage reason.

### 6.5 Exact serialized output grammar

All JSON/JSONL records use UTF-8, canonical sorted-key serialization and the following exact key sets. Unknown, missing, duplicate or type-invalid keys are rejected recursively by the strict bundle loader.

```text
denominator JSONL key set =
schema_version, parent_article_id, contract_id, canonical_symbol,
eligibility_passed, ineligibility_reasons, publication_time_authority,
t_pub_ms, point_in_time_source_validated, capture_time_status,
system_available_at_ms, fact_available_at_ms, candidate_root_relative_path,
candidate_manifest_sha256, authority_flags

metric JSONL key set =
schema_version, parent_article_id, contract_id, canonical_symbol,
metric_name, horizon, requested_interval, publication_time_authority,
t_pub_ms, point_in_time_source_validated, capture_time_status,
system_available_at_ms, fact_available_at_ms, source_family_audits,
source_logical_archive_record_ids, gate_failures, status,
descriptors, authority_flags

summary JSON key set =
schema_version, candidate_root_relative_path, candidate_manifest_sha256,
candidate_run_id, candidate_root_state, publication_time_authority,
point_in_time_source_validated, capture_time_status,
system_available_at_ms, fact_available_at_ms, n_denominator,
n_unique_parent_article_ids, metric_horizon_groups, authority_flags,
non_independence_notice

manifest JSON key set =
schema_version, bundle_run_id, bundle_state_at_write, design_authority,
candidate_input_authority, c_input_authority, point_in_time_authority,
output_artifacts, denominator_count, metric_status_counts,
authority_flags
```

`schema_version` is respectively `stage1_6f_candidate_w1_denominator_v1`, `stage1_6f_candidate_w1_metric_v1`, `stage1_6f_candidate_w1_summary_v1`, and `stage1_6f_candidate_w1_descriptive_bundle_v1`. `metric_name` is exactly one of `hourly_bar_observation`, `price_path`, `perp_index_basis`, `mark_index_basis`, `funding_observations`, `open_interest`, `visible_depth_proxy`, or `agg_trade_observations`. `horizon` is exactly `H1`, `H4`, or `H12` and must satisfy the Section 6.3 matrix. `status` is exactly `descriptive_only` or `diagnostic_incomplete`; the latter has `descriptors={}` only.

`publication_time_authority` is exactly `parent_audit_outcomes.source_published_at_ms_selected_trusted_bapi_publishDate`; `point_in_time_source_validated` is exactly `false`; `capture_time_status` is exactly `historical_unknown`; `system_available_at_ms` and `fact_available_at_ms` are exactly `null`. The strict writer and loader compare these five PIT values to the verified C/candidate inputs on every denominator record, metric record, summary and manifest. No later admission or reviewer may upgrade them in place; a future PIT source requires a new Design and bundle identity.

Every identity/path/schema/note/status field is a non-empty string, each SHA-256 is 64 lowercase hexadecimal characters, `t_pub_ms`, interval bounds, counts and timestamps are exact non-bool integers, and `eligibility_passed` is exactly `true`. `requested_interval` has the exact key set `start_ms`, `end_ms`, with `end_ms - start_ms` equal to the named horizon. `ineligibility_reasons` is an exact JSON array of strings and is empty for every admitted event. `candidate_root_state` is exactly `collection_terminal_with_gaps_or_unproven_data`, `bundle_state_at_write` is exactly `sealed_valid_at_write`, and `authority_flags` has exactly the 13 keys in Section 7.3 with every value boolean `false`. JSON decoding rejects duplicate object keys through `object_pairs_hook` before any ordinary object construction.

`source_family_audits` is a non-empty array sorted lexicographically by `family_name`. Every item has exactly this key set:

```text
family_name, coverage_status, coverage_reason, logical_record_ids,
timestamp_field, first_observed_ms, last_observed_ms, row_count,
duplicate_count, conflict_count, gap_count
```

`family_name` is exactly one of `klines_1h`, `index_price_1h`, `mark_price_1h`, `funding_rate`, `metrics_5m`, `book_depth`, or `agg_trades`; only families needed by the metric may occur. `coverage_status` is exactly one of the five frozen `002` values `window_observed`, `rows_observed_continuity_not_proven`, `window_incomplete`, `not_proven`, or `no_rows_observed`; `coverage_reason` exactly equals the selected `metric_window_coverages` W1 row's `reason` for that event/family. `logical_record_ids` is the sorted unique exact set of selected-W1 logical record IDs used by that family. `timestamp_field` is the exact Section 6.4 field for the family. `row_count`, `duplicate_count`, `conflict_count`, and `gap_count` are non-bool integers greater than or equal to zero. `first_observed_ms` and `last_observed_ms` are exact non-bool integers when `row_count > 0`, otherwise both are `null`; when present they satisfy `first_observed_ms <= last_observed_ms`. The horizon-selected row audit, including boundary exclusion and complete-bar counts, supplies these values; a candidate coverage row alone is insufficient.

`source_logical_archive_record_ids` is the sorted unique union of every `source_family_audits[].logical_record_ids`. `gate_failures` is an exact JSON array of sorted unique strings. It is `[]` if and only if `status=descriptive_only`; for `status=diagnostic_incomplete`, it is non-empty and contains only `candidate_coverage_not_admissible`, `horizon_grid_incomplete`, `horizon_duplicate_or_conflict`, `insufficient_complete_post_publication_bars`, `missing_aligned_complete_bars`, `missing_positive_index_close`, `no_horizon_funding_observation`, `no_complete_horizon_depth_ladder`, `no_horizon_agg_trade_observation`, `zero_price_path_denominator`, `missing_required_reducer_field`, or `non_finite_reducer_value`. For `metric_name=price_path`, `first_complete_bar_close == 0` must add `zero_price_path_denominator`; when it is the sole failed gate, `gate_failures` is exactly `["zero_price_path_denominator"]`. Candidate collection reasons remain in each family audit; they are not silently collapsed into a single metric-level reason.

The manifest's nested objects are equally closed:

```text
design_authority = path, sha256
candidate_input_authority = root_relative_path, manifest_sha256, run_id, root_state
c_input_authority = completion_manifest_sha256, source_export_receipt_sha256
point_in_time_authority = publication_time_authority,
    point_in_time_source_validated, capture_time_status,
    system_available_at_ms, fact_available_at_ms
output_artifacts[] = relative_path, byte_length, sha256
metric_status_counts[] = metric_name, horizon, status, count
```

All five nested mappings and every array item have exactly the listed keys, types and enum values. `output_artifacts` contains exactly the three non-manifest output files in Section 6.6, sorted by `relative_path`; its hashes and byte lengths are recomputed by the strict loader. `metric_status_counts` contains exactly 38 rows: every allowed Section 6.3 `(metric_name, horizon)` tuple crossed with both statuses, including zero counts, sorted lexicographically by `(metric_name, horizon, status)`. For every allowed tuple its two status counts sum to exactly 41, and all 38 counts sum to exactly 779.

The only permitted descriptor key sets are fixed by `metric_name`:

```text
hourly_bar_observation:
first_open_time_ms, first_close_time_ms, first_open, first_high, first_low,
first_close, last_open_time_ms, last_close_time_ms, last_open, last_high,
last_low, last_close, row_count, note

price_path:
first_close_time_ms, last_close_time_ms, first_complete_bar_close,
last_complete_bar_close, bar_close_change_bps, bar_count, note

perp_index_basis:
first_basis_bps, last_basis_bps, median_basis_bps, bar_count, note

mark_index_basis:
first_mark_basis_bps, last_mark_basis_bps, median_mark_basis_bps,
bar_count, note

funding_observations:
observations, count, note
where every observations item is exactly:
calc_time, funding_interval_hours, last_funding_rate

open_interest:
first_oi_value, last_oi_value, delta_oi_value,
latest_toptrader_long_short_ratio, bar_count, note

visible_depth_proxy:
pct_neg_5, pct_neg_4, pct_neg_3, pct_neg_2, pct_neg_1,
pct_pos_1, pct_pos_2, pct_pos_3, pct_pos_4, pct_pos_5, note
where every percentage object is exactly:
count, first_notional, last_notional, median_notional

agg_trade_observations:
total_trades, total_notional, buyer_maker_true_count,
buyer_maker_true_notional, buyer_maker_false_count,
buyer_maker_false_notional, note
```

The only permitted note values are respectively `hourly_bar_open_time_in_window_observation_only`, `coarse_complete_post_publication_bar_close_proxy`, `perp_index_reference_basis_only`, `non_tradable_reference_only`, `discrete_observations_only_no_carry_pnl`, `raw_open_interest_observation_only`, `visible_discrete_depth_proxy_only_no_slippage`, and `exchange_label_only_not_aggressor_inference`. Every listed descriptor numeric slot is a finite non-bool number; `row_count`, `bar_count`, `count` and trade counts are non-bool integers. No descriptor key may be null unless its exact descriptor grammar explicitly says so; this version has no such nullable descriptor field.

`source_logical_archive_record_ids` cannot be empty, shortened to one family for a multi-family metric, or padded with an unrelated logical record. It is mechanically recomputed as the exact Section 6.5 audit-ID union and therefore cannot diverge from the individual family facts.

Every `metric_horizon_groups` item has the exact key set `metric_name`, `horizon`, `descriptor_name`, `depth_percentage`, `n_denominator`, `n_descriptive`, `n_diagnostic_incomplete`, `n_unique_parent_article_ids`, `minimum`, `median`, `maximum`. The summary contains exactly these 45 groups and no other scalar descriptor projection:

```text
price_path: H4/H12 x bar_close_change_bps
perp_index_basis: H4/H12 x median_basis_bps
mark_index_basis: H4/H12 x median_mark_basis_bps
funding_observations: H1/H4/H12 x count
open_interest: H1/H4/H12 x delta_oi_value
visible_depth_proxy: H1/H4/H12 x median_notional x depth_percentage in
  {-5,-4,-3,-2,-1,1,2,3,4,5}
agg_trade_observations: H1/H4/H12 x total_notional
```

The groups are sorted by `(metric_name, horizon, descriptor_name, depth_percentage)`. Each group has `n_denominator=41`, `n_descriptive + n_diagnostic_incomplete = 41`, and `n_unique_parent_article_ids` equal to the distinct parent IDs among its `descriptive_only` source records. `depth_percentage` is `null` outside `visible_depth_proxy` and otherwise is exactly one listed non-bool integer. `minimum`, `median`, and `maximum` are all `null` if and only if `n_descriptive=0`; otherwise each is finite. Median is deterministic: sort the finite scalar values ascending; take the central value for odd count, or the arithmetic mean of positions `n/2-1` and `n/2` for even count, without rounding. No group mixes metrics, horizons, descriptor names or depth levels.

The summary has `n_denominator=41`, `n_unique_parent_article_ids=38`, and `non_independence_notice=historical_ex_post_descriptive_rows_may_share_parent_articles_and_are_not_independent_samples`. It must not calculate, serialize or imply a win rate, significance test, alpha, return, PnL, control adjustment or economic interpretation.

### 6.6 New output bundle

Each approved execution writes a fresh, create-exclusive root:

```text
data/external_signal_shadow/stage1_6f/candidate_w1_diagnostics/<run_id>/
```

It contains exactly:

```text
stage1_6f_candidate_w1_denominator.jsonl
stage1_6f_candidate_w1_metrics.jsonl
stage1_6f_candidate_w1_summary.json
stage1_6f_candidate_w1_bundle_manifest.json
```

`stage1_6f_candidate_w1_bundle_manifest.json` is written last and declares schema `stage1_6f_candidate_w1_descriptive_bundle_v1`. It has `bundle_state_at_write=sealed_valid_at_write` and binds:

- `bundle_run_id` exactly equal to the create-exclusive output-root basename `<run_id>`;
- this Delta's future approved SHA-256;
- the exact candidate root relative path, manifest SHA-256, run ID and root state;
- C completion manifest/source-export receipt identities and the exact PIT values in Section 6.5;
- every output relative path, byte length and SHA-256;
- full 41-row denominator counts; per metric/horizon status counts; and all 13 exact-false authority flags.

Every metric JSONL record follows the Section 6.5 grammar, has no control field, and preserves PIT facts without inference. A summary may aggregate only the raw descriptor fields allowed in Section 6.4 and must preserve the Section 6.5 group counts and non-independence notice.

## 7. Failure, Persistence, Compatibility, and Safety Semantics

### 7.1 Failure reducer sequence

```text
validate approved authority packet
  -> validate canonical candidate root exactly once
  -> verify C retained bytes exactly once
  -> reconstruct all 41 denominator rows
  -> derive and cross-bind canonical Tpub under Section 6.2
  -> for every allowed event x horizon x metric tuple, apply the Section 6.3 gate
  -> serialize each artifact with canonical JSON bytes
  -> write each artifact to a same-directory temporary file, flush and fsync
  -> read back and verify output hashes/lengths
  -> atomically rename the three verified non-manifest artifacts
  -> write, flush, fsync and read-back-verify the temporary manifest
  -> atomically rename the manifest last
```

Canonical JSON bytes use `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`. JSON files have no trailing newline; each JSONL record uses those canonical object bytes followed by exactly one `\n`, with no blank line. Temporary files are created in the output root and are never accepted by the strict loader. `os.replace()` of the verified manifest temporary file to `stage1_6f_candidate_w1_bundle_manifest.json` is the sole seal/publication event. No later repair, append, overwrite, reuse or deletion is permitted.

- Failure before candidate admission completes: `STOP=candidate_admission_invalid`, zero output files.
- Failure in C verification or cohort equality: `STOP=upstream_denominator_authority_invalid`, zero output files.
- Per-metric source absence/incompleteness: normal terminal `diagnostic_incomplete` record, not process failure and not sample deletion.
- **Pre-seal failure:** a local write/read-back/rename/serialization/manifest-write failure before manifest publication is run-fatal `candidate_w1_bundle_invalid`; no final manifest exists, no file is repaired or reused, and a later attempt needs a new output `run_id`.
- **Post-seal validation failure:** after the manifest is published, any strict-loader rejection for a missing/extra file, temporary file, symlink, hash/length mismatch, unknown schema/key, invalid finite number, authority mismatch or record mutation leaves the root intact as an immutable invalid forensic root. It is non-consumable, no file may be deleted or rewritten, and the `run_id` is burned.
- Manifest presence is never proof of consumability. `load_candidate_w1_bundle(...)` passing strict recomputation is the sole completed-bundle admission gate. Existing or reused output root is `STOP=candidate_w1_output_run_id_collision`.

### 7.2 Compatibility and migration

The REEF package and its strict reader are unchanged. Existing REEF commands must still reject candidate roots, while the new candidate W1 CLI must reject the REEF package and every candidate root except `002`. This is intentional asymmetric compatibility, not a migration gap.

The old `001` root remains forensic-only. It must be rejected before C verification and cannot be repaired, copied, merged or used as an alternate fixture.

### 7.3 Safety and authority boundary

All input, intermediate and output authority flags are exact booleans `False`:

```text
RISK_LIVE_TRADING_ENABLED, trade_signal_allowed, paper_trading_allowed,
live_trading_allowed, execution_engine_allowed, private_api_allowed,
authenticated_api_allowed, order_api_allowed, alpha_interpretation_allowed,
execution_feasibility_claim_allowed, net_cost_or_profit_claim_allowed,
replay_allowed, point_in_time_directional_replay_allowed
```

This Delta authorizes neither a network action nor an execution action. Its outputs are diagnostic evidence only and cannot be routed to `SignalCandidate`, `TradeIntent`, a strategy, an order API, paper trading, live trading, a deployment target or VPS runtime.

## 8. Acceptance Invariants and Verification Strategy

| ID | Invariant | Required future proof |
| --- | --- | --- |
| INV-CA01 | Only the exact canonical `002` root and manifest SHA are admissible. | Canonical root positive; path alias, old `001`, copied root, manifest-byte mutation and unlisted-file mutations fail before writer creation. |
| INV-CA02 | One shared strict loader is the only candidate trust boundary. | Collector and new W1 consumer positives derive from the canonical strict loader; equivalent valid/invalid root tests prove no `src -> scripts` import or duplicated validator. |
| INV-CA03 | Existing REEF consumer behavior and input identity do not drift. | Existing REEF tests pass; `verify_market_evidence(candidate_root)` still fails; candidate CLI rejects REEF root. |
| INV-CA04 | All 41 event identities, canonical publication facts and PIT facts survive every output boundary. | Compare full `(parent_article_id, contract_id, canonical_symbol)` set, `Tpub`, two retained `source_published_at_ms` values, exact candidate W1 window and five PIT fields from verified C/candidate through denominator, metric, summary and manifest. |
| INV-CA05 | Source timestamp identity is checked before coverage and uses separate observation-open and complete-bar grids. | Mutate each family timestamp field, an hourly partial bar, an after-end bar, a duplicate and a gap; verify `csv_invalid/not_proven` for identity failure and exact H4/H12 complete-bar exclusion otherwise. |
| INV-CA06 | Every metric carries exact per-family audit facts and a metric-specific failure ledger. | Assert the 41-row denominator, 19-tuple ledger and 779 metric records; multi-family audit omission/addition/reordering, wrong coverage reason, stale row audit and empty/non-empty `gate_failures` mutations fail. A single `price_path.first_complete_bar_close=0` mutation yields `diagnostic_incomplete`, `descriptors={}`, and exactly `["zero_price_path_denominator"]` when no other gate is changed. |
| INV-CA07 | Serialized schema is exact and cannot carry W2, control, excess-return, alpha, PnL, fee, cost, execution or signal data. | Recursive key-set/type/enum loader tests, forbidden-field injection for top-level, family-audit and descriptor fields, plus source/CLI scanner. |
| INV-CA08 | Every scalar serialized numeric is finite and every source logical ID is exact. | `NaN`, infinity and bool-as-number mutations fail; a finite zero `price_path` denominator mutation must fail closed at metric level rather than divide or serialize a synthetic value; multi-family and multi-archive provenance omissions/additions/reordering fail. |
| INV-CA09 | Output is atomic, reloadable and bound to candidate/C authority. | Crash before every rename proves absent manifest/no-resume; output-root basename/bundle-run-ID mismatch fails; post-seal mutation preserves immutable forensic bytes and strict loader rejects missing/extra/symlink/hash/length/schema/authority failures. |
| INV-CA10 | Cross-event summaries use an exhaustive fixed allowlist and deterministic statistics. | Assert exactly 45 sorted groups and 38 sorted status-count rows; group insertion/removal, H1/H4/H12, metric, descriptor and depth-level mixing, zero-count handling and even/odd median mutations fail. |
| INV-CA11 | All 13 authority flags are exact `False`. | Positive output checks plus one boolean mutation per flag fails closed. |
| INV-CA12 | No network, runtime or deployment activity occurs. | Tests use canonical local bytes only; audit proves zero network calls and no runtime/deployment command. |

The future Plan must define a canonical positive fixture by running the strict candidate loader against the exact `002` root, not by handcrafted manifest dictionaries. Negative cases use one declared mutation per invariant. It must run the focused suite, the existing Stage 1.6F regression suite, `ruff`, `anti_shortcut_scan.py` with its actual process exit code, `git diff --check`, index/worktree scope proof and a blind-first completion audit.

## 9. Rollout, Rollback, and Design Gate

There is no runtime rollout, deployment or VPS action. The only future operational action is an offline local invocation after a separately reviewed and user-approved Plan. Rollback is a safe no-op: do not delete or alter roots; refuse the new candidate W1 path and leave existing REEF behavior unchanged.

```text
design_status = draft_for_review
implementation_plan_allowed = false
implementation_allowed = false
network_collection_allowed = false
commit_allowed = false
deployment_allowed = false
runtime_action_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

This Design requires an independent Design review and explicit user approval before an Implementation Plan may be written.
