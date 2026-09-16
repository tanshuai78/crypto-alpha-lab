# Stage 1.6F Historical Evidence Package Expansion Design

**日期：** 2026-09-16
**状态：** `draft_for_review`
**类型：** 只读公开历史归档的候选证据包采集 Design；不是 Plan、实现、提交、部署、VPS、回放、交易、paper-trading、signal 或 execution authority。

## 1. 问题与结论

当前 Stage 1.6F 的严格 reader 只接受 REEF 锚点 evidence package 的精确 manifest SHA-256。真实 C root 有 63 个 contract 行，其中 47 个 `eligibility_passed`；但当前 evidence package 只物理保存 REEF 的完整 W1 原始市场数据。因此以该包运行 F 时，除 REEF 外的 62 行均输出 unavailable 指标。

这不是“其他 62 个合约已被 Binance Vision 证明不存在历史数据”。当前 archive coverage matrix 对历史范围内所需的 1,187 个归档路径记录 1,187 个 HTTP 200；它只证明归档路径存在，不证明 ZIP/CSV 已下载、内容可解析、窗口连续或可被 F 使用。

本 Design 的唯一目标是将这条未闭合的证据边从“路径曾可用”升级为“附带精确原始 bytes、SHA-256、严格 CSV 校验和窗口覆盖结论的候选证据包”。首版只处理 W1 和控制组所需的公告前 event Kline；它不建立新的 matched-control 结论、不改变当前 F 受信任输入集，也不验证 W2 结算值。

## 2. 已确认事实

### 2.1 冻结 authority packet

| Authority | 路径 | SHA-256 |
| --- | --- | --- |
| Parent F Design | `docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md` | `87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c` |
| F evidence-to-schema Delta | `docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md` | `8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628` |
| Approved F implementation Plan | `docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md` | `6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f` |
| Existing REEF evidence manifest | `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json` | `9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f` |
| Archive coverage matrix | `tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json` | `b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8` |
| C completion manifest | `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json` | `226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0` |
| C source-export receipt | `data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/source_export_receipt.json` | `07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e` |
| B sealed export manifest | `data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090/sealed_export_manifest.json` | `1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be` |
| F denominator module | `src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py` | `84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3` |
| F source module | `src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py` | `00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f` |

The future execution packet has two further external authorities that cannot be self-embedded in this draft: the user-approved SHA-256 of this Design and of its future collection Plan. A future collector must receive those approval records and a separate, one-run network-collection authorization record. The latter binds exactly `run_id`, approved Design SHA-256, and approved Plan SHA-256; Design or Plan approval alone never authorizes a public network request.

### 2.2 Current evidence boundary

- The verified C input contains 63 contract rows and 38 independent parent announcements. Its raw contract field is `source_audit_eligible`; C has no `eligibility_passed` field.
- The frozen existing F function `reconstruct_denominator(verified_c)` derives `eligibility_passed` from the retained C bytes: parent integrity/trust/declaration/mapping/classification predicates, the USD-M perpetual quote/settlement/margin/type predicates, and `source_audit_eligible`. It yields 47 eligible and 16 ineligible rows. `source_audit_eligible=True` alone yields 48 rows, so it is not a substitute authority.
- Current REEF package matrix lists 48 market-symbol rows: 42 in the Parent historical range and six explicitly out of range. `IPUSDC` is in the market census and has `source_audit_eligible=True`, but fails the frozen F denominator predicate.
- The intersection of the 47 F-derived `eligibility_passed` rows and the matrix `in_range_historical_export` symbols is exactly 42, including `REEFUSDT`.
- This Design's first candidate cohort is therefore exactly 41 symbols: the 42-symbol intersection minus the already sealed `REEFUSDT` anchor.
- The five C-eligible out-of-range symbols are `AERGOUSDT`, `ANTUSDT`, `BLUEBIRDUSDT`, `CTKUSDT`, and `FOOTBALLUSDT`. They are not collection targets in this Design.
- Existing matrix availability is not a content proof: it explicitly declares `in_archive_continuous_bars_proven=false`.

### 2.3 Current source and consumer behavior

- `verify_market_evidence(...)` rejects every manifest identity other than `9e44...` before parsing market rows.
- The F runner only produces one matched REEF row from the currently sealed REEF control artifact. No other event gets an invented control set.
- Current F correctly labels absent market series `*_unavailable`; it must continue to do so until a separately approved input-admission delta accepts a new exact package identity.

## 3. Assumptions, Decisions, and Open Questions

### 3.1 Explicit assumptions

1. The archive coverage matrix URLs are a candidate public-source list, not a guarantee that a fresh GET will succeed or that bytes are internally complete.
2. A public archive fetch uses no credentials, private endpoint, account state, trading API, order API, SSH, VPS, or background process.
3. A future implementation may use standard-library HTTPS only after a separately approved Plan; this Design does not itself authorize any network activity.

### 3.2 Decisions

1. **Scope is W1-first.** Collect the event's `[Tpub, Tpub + 12h)` raw families and event baseline `[E-168h, E)` `klines_1h`. W2 is excluded because the current 1-hour Index evidence cannot establish a one-second settlement value; it needs a separate source-specific Design.
2. **No new control selection in this Design.** The event baseline is collected only as raw input for a future per-event historical-universe/control-proof Design. No selected control, event-minus-control metric, alpha result, or matched conclusion may be emitted for the 41 new symbols.
3. **New package remains candidate-only.** It has a new manifest identity and is rejected by the current F reader. A later input-admission Delta must bind its exact manifest SHA-256 and define reader compatibility; this Design never weakens the current `9e44...` check.
4. **No silent shortage.** An unavailable source, malformed archive, missing bar, or unreadable ZIP is a retained ledger fact, never an empty series, zero observation, substituted date, or fallback package.

### 3.3 Non-blocking open questions

| Question | Disposition | Owner / later gate |
| --- | --- | --- |
| Whether all 41 candidate archives can be fetched and parsed today | Not assumed; the candidate manifest records the outcome per artifact | Future implementation and evidence review |
| Whether an existing repository downloader can meet the exact package contract | Not a Design choice; future Plan must prove reuse is contract-compatible or use the smallest standard-library implementation | Plan author |
| Whether enough successful events remain for a cross-event mechanism study | Deferred until completed candidate package audit; no sample-size or alpha claim in this Design | Subsequent research Design |

No open question changes this Design's authority, schema, safety boundary, or fail-closed behavior. The 41-symbol candidate set and required artifact classes are frozen below.

## 4. Scope and No-Touch Set

### 4.1 Allowed future implementation scope

The later Plan may create only:

- one dedicated public read-only archive collection entry point under `scripts/external_signal_shadow/`;
- its focused tests under `tests/scripts/external_signal_shadow/` and/or `tests/research/external_signal_shadow/`;
- an immutable, run-ID-scoped candidate evidence root under `data/external_signal_shadow/stage1_6f/evidence_candidates/`;
- a candidate-package audit document under `docs/reviews/`.

The exact filenames and implementation paths remain Plan decisions, but must be minimal and must not create a daemon, queue, database, scheduler, retry service, or generic exchange adapter.

### 4.2 Explicit non-goals / No-Touch

- No modification of Parent/Delta Design bytes, the approved F Plan, current F source/tests, `configs/base.py`, existing REEF evidence package, B/C export roots, or Stage 1.5/1.6E collectors.
- No update to `REVIEWED_MARKET_EVIDENCE_MANIFEST_SHA256`, `verify_market_evidence(...)`, the F runner, or F reviewer. A candidate package is deliberately not F-consumable.
- No collection of the five out-of-range C-eligible symbols, `IPUSDC`, or a future/current exchange universe.
- No W2 archive collection, one-second Index collection, settlement-value reconstruction, control selection, event-minus-control calculation, significance test, alpha verdict, PnL, fee, borrow, slippage, execution, replay, paper-trading, or live-trading work.
- No deletion, overwrite, mutation, rehash, or repair of any prior B/C/evidence root.

Any requirement to touch a No-Touch path is `STOP=BLOCKED_SCOPE_DRIFT`. Any contradiction between this document and Parent/Delta authority is `STOP=BLOCKED_SPEC_DRIFT`.

## 5. Candidate Cohort and Input Contract

### 5.1 Exact cohort

The future collector must derive its target set mechanically from the frozen C root and frozen coverage matrix, then require:

```text
verified C root
    -> canonical C loader and retained verified C bytes
    -> existing frozen F `reconstruct_denominator(verified_c)` predicate
    -> F-derived `eligibility_passed`
    -> intersect matrix.range_category == in_range_historical_export
    -> minus {REEFUSDT}

count == 41
```

The expected sorted symbols are:

```text
1000XUSDT, AIAUSDT, AIUSDT, ALPHAUSDT, AUDIOUSDT, BAKEUSDT,
BDXNUSDT, BOBUSDT, BONDUSDT, BSWUSDT, CVXUSDT, DAMUSDT,
DEFIUSDT, EPTUSDT, HIFIUSDT, KDAUSDT, LEVERUSDT, LOOMUSDT,
MAVIAUSDT, MBLUSDT, MDTUSDT, MILKUSDT, NEIROETHUSDT, OBOLUSDT,
OMGUSDT, ORBSUSDT, PERPUSDT, PORT3USDT, PUFFERUSDT, QUICKUSDT,
RADUSDT, SLERFUSDT, SLPUSDT, STPTUSDT, SXPUSDT, TANSSIUSDT,
TOKENUSDT, UXLINKUSDT, VOXELUSDT, XEMUSDT, YALAUSDT
```

Any count or set mismatch is `STOP=candidate_cohort_authority_mismatch`; a collector must not silently use a current exchange list, a glob, a hand-edited subset, or C `source_audit_eligible` as a replacement predicate.

### 5.2 Logical archive records and physical source objects

The only permitted URLs are the exact `url` values in the frozen coverage matrix records whose symbol is in Section 5.1 and whose window is one of:

- `baseline_168h` with metric `klines_1h`;
- `w1_shock_12h` with metrics `klines_1h`, `index_price_1h`, `mark_price_1h`, `premium_index_1h`, `funding_rate`, `metrics_5m`, `book_depth`, and `agg_trades`.

No URL template may be reconstructed from a symbol or date. No redirect destination, alternate host, current API endpoint, archive index, or source fallback is permitted.

The coverage matrix is the logical-request authority. A logical archive record is the canonical JSON tuple:

```text
(parent_article_id, contract_id, canonical_symbol, window,
 nominal_window_start_utc, window_start_utc, window_end_utc,
 metric, archive_date_or_month, exact_source_url)
```

Canonical serialization is exactly `UTF-8(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True for objects only))`, with no trailing newline. The logical value is the JSON array in the displayed field order; the physical value is the JSON string `exact_source_url`. Its `logical_archive_record_id` and `physical_source_object_id` are respectively the SHA-256 of those bytes. The fixed test vectors are:

```text
["parent","contract","SYMBOL","w1_shock_12h","2025-01-01T00:00:00+00:00","2025-01-01T00:00:00+00:00","2025-01-01T12:00:00+00:00","metrics_5m","2025-01-01","https://example.test/object.zip"]
-> d49cdfa17433748ed194a323eb969632d23a2036d4bc5873bf1b80c25069a295
"https://example.test/object.zip"
-> 3c8db1814c8bfc8be6ef2f19ca9527cb313fece63616de1f6226a2321e8c18b1
```

A run must contain one logical record for every selected matrix row and one physical-source-object record for every distinct selected URL. It may make exactly one first request and retain at most one ZIP/CSV object set per `physical_source_object_id`; several logical records may reference that one physical object. In the frozen cohort this is not hypothetical: 705 logical records map to 664 distinct URLs, with 41 lawful shared URL references. Duplicate prohibition applies to a duplicate physical object ID or physical relative path, not to repeated logical references.

For each logical archive record, the candidate manifest must retain at least:

```text
logical_archive_record_id, parent_article_id, contract_id, canonical_symbol,
window, nominal_window_start_utc, window_start_utc, window_end_utc,
metric, archive_date_or_month, exact_source_url,
coverage_matrix_sha256, matrix_record_sha256,
physical_source_object_id, record_state, reason,
parsed_window_row_count, observed_first_timestamp_ms,
observed_last_timestamp_ms, duplicate_count, conflict_count, gap_count
```

Each physical-source-object record must retain:

```text
physical_source_object_id, exact_source_url, fetch_status,
http_status_or_transport_error, zip_relative_path, zip_byte_length,
zip_sha256, csv_relative_path, csv_byte_length, csv_sha256,
zip_member_name, csv_header, csv_row_count, first_row, last_row,
request_started_at_ms, response_observed_at_ms, reason
```

`funding_rate` uses its matrix-selected monthly archive. Every other listed metric uses its exact matrix-selected daily archive. A URL that is no longer fetchable is retained with its exact failure classification and does not become a substitute source request.

`matrix_record_projection_v1` is exactly the logical fields copied from the selected frozen matrix row: `parent_article_id`, `contract_id`, `symbol` renamed to `canonical_symbol`, `window`, `nominal_window_start_utc`, `window_start_utc`, `window_end_utc`, `metric`, `archive_date_or_month`, and `url` renamed to `exact_source_url`. `matrix_record_sha256` is the SHA-256 of the canonical serialization of the full source matrix object, including every unprojected field. The validator independently canonicalizes the matrix row, compares its full-row hash, then compares this exact projection. It does not require unprojected source fields to be duplicated in the logical record.

### 5.3 ZIP member safety

Before any CSV byte is read or persisted, the ZIP inventory must contain exactly one member. That member must be a non-directory, non-encrypted regular file with a nonempty `.csv` basename; its name may contain neither an absolute-path prefix, `..`, `/`, nor `\\`. A member is symlink-like exactly when `((ZipInfo.external_attr >> 16) & 0o170000) == 0o120000`; such a member is invalid. Duplicate member names and any extra member are invalid. `ZipFile.extract()` and `extractall()` are prohibited: the collector reads only that verified member directly in fixed-size chunks, verifies the exact declared member byte count, and writes its bytes to a collector-generated path derived from `physical_source_object_id`, never from the member path.

### 5.4 Family-specific coverage predicates

Every raw timestamp is included only when `window_start_ms <= timestamp < window_end_ms`. `ceil(t, step_ms)` is exactly `((t + step_ms - 1) // step_ms) * step_ms`. The candidate manifest records one `metric_window_coverage` result for every distinct `(parent_article_id, contract_id, canonical_symbol, window, metric)` after joining every referenced logical archive record. It must retain the timestamp key, requested interval, expected-grid step or `null`, observed count/range, duplicate/conflict/gap counts, and one status below. No family may borrow another family's predicate.

| Family | Timestamp identity and interval rule | Coverage predicate | Valid terminal coverage result |
| --- | --- | --- | --- |
| `klines_1h`, `index_price_1h`, `mark_price_1h`, `premium_index_1h` | `open_time`; one row per timestamp | Expected grid is every 3,600,000 ms boundary from `ceil(window_start_ms, 3,600,000)` through `< window_end_ms`. Any missing grid timestamp is a gap; any duplicate timestamp is a conflict. | `window_observed` only when every grid point is present exactly once; otherwise `window_incomplete`. |
| `metrics_5m` | `create_time`; every row's case-sensitive `symbol` equals the logical `canonical_symbol`; one row per timestamp | A symbol mismatch is an identity-validation failure, not a coverage conflict: the entire CSV is `csv_invalid` / `not_proven`, and none of its rows may contribute to `metric_window_coverage`. Only after that identity check passes, the expected grid is every 300,000 ms boundary from `ceil(window_start_ms, 300,000)` through `< window_end_ms`; a missing grid timestamp is a gap and a duplicate timestamp is a conflict. | `window_observed` only when the identity-valid CSV contains every grid point exactly once; otherwise `window_incomplete`. |
| `funding_rate` | `calc_time`; one row per timestamp | It is a discrete settlement observation, not a clock grid. Duplicate `calc_time` is a conflict. No expected interval or missing-gap count may be inferred from `funding_interval_hours`. | Nonempty valid rows: `rows_observed_continuity_not_proven`; no valid row: `no_rows_observed`. |
| `book_depth` | `(timestamp, percentage)`; required percentage set at every observed timestamp is `{-5,-4,-3,-2,-1,1,2,3,4,5}` | Snapshots are non-uniform; no time grid is permitted. A duplicate `(timestamp, percentage)`, a missing required percentage at an observed timestamp, or an unapproved percentage makes the CSV invalid. | Nonempty valid snapshots: `rows_observed_continuity_not_proven`; no valid snapshot: `no_rows_observed`. |
| `agg_trades` | `agg_trade_id`; `transact_time` selects the interval | Trades are event-driven; no time grid and no inactivity gap may be inferred. Duplicate `agg_trade_id` is a conflict. | Nonempty valid rows: `rows_observed_continuity_not_proven`; no valid row: `no_rows_observed`. |

`csv_invalid` / `not_proven` is mandatory for any header, type, timestamp, symbol-identity, duplicate, or ladder-conflict failure; no collector may deduplicate, interpolate, forward-fill, drop a bad row, or coerce a value. A grid-family `window_incomplete` is distinct from a non-grid family with observed rows but no continuity proof.

### 5.5 Candidate evidence schema and strict validator

The candidate root is a new immutable root with a unique run ID and final manifest schema:

```text
stage1_6f_historical_evidence_expansion_candidate_manifest_v1
```

The manifest's exact top-level key set is:

```text
schema_version, run_id, authority_packet, cohort,
physical_source_objects, logical_archive_records,
metric_window_coverages, candidate_root_state, capture_mode,
point_in_time_source_validated, authority_flags
```

`authority_packet` is an exact mapping whose keys are `parent_f_design`, `f_evidence_to_schema_delta`, `approved_f_implementation_plan`, `existing_reef_evidence_manifest`, `archive_coverage_matrix`, `c_completion_manifest`, `c_source_export_receipt`, `b_sealed_export_manifest`, `f_denominator_module`, `f_source_module`, `approved_historical_evidence_expansion_design`, `approved_expansion_implementation_plan`, and `network_collection_authorization`. The first ten values have exactly `path` and `sha256`, matching Section 2.1. The two approved-authority values have exactly `path` and `sha256`, and must equal the external user approval records supplied at execution. `network_collection_authorization` has exactly `run_id`, `approved_design_sha256`, `approved_plan_sha256`, and `authorization_record_sha256`; all four must equal the run and approved authority values. Its bytes are external authorization evidence, not an artifact that grants any trading, replay, paper, execution, or F-input authority.

`cohort` is the exact sorted 41-symbol list in Section 5.1. `logical_archive_records` must equal the derived selected matrix-record ID set; each entry must match `matrix_record_sha256` and `matrix_record_projection_v1` in Section 5.2. `physical_source_objects` must equal the deduplicated URL set referenced by that logical set. The physical object key set and logical record key set are exactly the fields in Section 5.2. The `metric_window_coverages` key set is exactly:

```text
parent_article_id, contract_id, canonical_symbol, window, metric,
timestamp_key, requested_interval_start_ms, requested_interval_end_ms,
expected_grid_step_ms, parsed_window_row_count,
observed_first_timestamp_ms, observed_last_timestamp_ms,
duplicate_count, conflict_count, gap_count, coverage_status, reason
```

The only physical `fetch_status` values are `fetched_verified`, `archive_not_found_404`, `redirect_refused`, `transport_inconclusive`, `archive_invalid`, and `csv_invalid`. Every logical `record_state` must be one of exactly those values and equal its referenced physical object's `fetch_status`. The only coverage values are `window_observed`, `window_incomplete`, `rows_observed_continuity_not_proven`, `no_rows_observed`, `unavailable`, and `not_proven`. `request_started_at_ms` is an exact UTC epoch-millisecond integer for the one permitted request; `response_observed_at_ms` is an exact UTC epoch-millisecond integer only when a response is received, otherwise null. The root additionally records `capture_mode=historical_ex_post_candidate` and `point_in_time_source_validated=false`; neither timestamp is a historical fact-availability value.

`archive_not_found_404`, `redirect_refused`, and `transport_inconclusive` have null ZIP/CSV fields. If an HTTP body was received, `archive_invalid` retains and binds that body as the ZIP path/length/SHA even when ZIP integrity fails; `csv_invalid` retains and binds the validated ZIP and extracted CSV bytes even when strict CSV parsing fails. A `fetched_verified` object has non-null regular-file ZIP/CSV paths, byte lengths, SHA-256, exact header, row count, first row, and last row.

`candidate_root_state` is derived, never chosen by the collector:

```text
collection_terminal_with_full_grid_coverage
    iff every physical object is fetched_verified,
        every grid metric-window is window_observed, and
        every non-grid metric-window is rows_observed_continuity_not_proven;
collection_terminal_with_gaps_or_unproven_data
    iff every expected logical record and physical object has a terminal
        status but the first condition is false.
```

A future Plan must implement a canonical, read-only candidate validator as a separate consumer path. It receives only a completed root and the three external execution authorities, then independently recomputes the authority packet, F-derived cohort, expected logical set, physical URL set, object hashes/lengths, ZIP-member contract, strict CSV and coverage outcomes, root-state reducer, and all path rules. It rejects missing/extra keys, missing/extra records, duplicate physical IDs/paths, path escape, symlink, unlisted regular file, changed byte, non-terminal state, source-module identity drift, absent/mismatched user authority, or an inconsistent root state. It must not consume collector in-memory state and is the only permitted input path for a future audit or admission Delta. This remains a collection/audit artifact only; it is not a `stage1_6f_gap02_evidence_manifest_v1` and must not claim F-reader compatibility.

## 6. Collection, Validation, and Failure Semantics

### 6.1 Required order

The future implementation must perform this exact order for each new run:

```text
verify frozen authority bytes
  -> verify C root through canonical C loader
  -> parse frozen coverage matrix
  -> derive F denominator through `reconstruct_denominator(verified_c)`
  -> derive and exact-check 41-symbol cohort
  -> enumerate exact logical records and deduplicated physical URLs
  -> make the one permitted exact-URL request per physical object without redirect following
  -> retain ZIP bytes
  -> verify ZIP integrity
  -> validate the Section 5.3 ZIP member inventory and read its one CSV member directly
  -> retain collector-named CSV bytes
  -> hash, parse strict known header, and apply the Section 5.4 family predicate
  -> append in-memory physical-object and logical-record staging records
  -> derive metric-window coverage and root state
  -> read back every retained ZIP/CSV output and verify assembled manifest metadata
  -> write candidate manifest last
  -> validate the completed root through the independent reader
```

The sole permitted F logic dependency is the pure `reconstruct_denominator(verified_c)` denominator reducer at the frozen module SHA. The collector must not call F market-data metric reducers, runner, writer, reviewer, control matcher, or any trade/execution component.

### 6.2 Required coverage classification

| Condition | Required `fetch_status` / `coverage_status` | Prohibited behavior |
| --- | --- | --- |
| HTTP 200, ZIP and CSV validation pass | `fetched_verified` / result from the exact Section 5.4 family predicate | Calling it matched, tradable, or alpha-positive |
| HTTP 404 for matrix URL | `archive_not_found_404` / `unavailable` | Trying a guessed URL, retry, or alternate source |
| First exact-URL response is 3xx | `redirect_refused` / `not_proven` | Following `Location`, requesting a redirect destination, or calling it source absence |
| timeout, TLS, non-404/non-3xx HTTP error, rate limit, malformed response | `transport_inconclusive` / `not_proven` | Recording source absence or retrying on the same or another host |
| ZIP hash/integrity/extraction failure | `archive_invalid` / `not_proven` | Parsing partial rows or retaining a valid status |
| CSV header/type/timestamp/symbol-identity failure | `csv_invalid` / `not_proven` | Coercion, default values, interpolation, deduplication, dropped-row repair, or treating a wrong-symbol CSV as an incomplete window |
| Valid grid-family CSV with a missing expected timestamp | `fetched_verified` / `window_incomplete` | Calling the window complete or filling the gap |
| Valid non-grid CSV with no in-window row | `fetched_verified` / `no_rows_observed` | Inferring a time gap, filling a missing event, or calling it continuous |
| Valid non-grid CSV with in-window rows | `fetched_verified` / `rows_observed_continuity_not_proven` | Inferring continuity, executable depth, or a trade-flow absence |

`book_depth` remains a low-frequency visible-depth proxy and `agg_trades.is_buyer_maker` remains a raw flag. Neither output permits executable slippage, L2 replay, maker behavior, forced-flow, liquidation, or trade-direction conclusions.

### 6.3 Persistence and crash behavior

- All files write atomically into a fresh, unique candidate root.
- `candidate_root = data/external_signal_shadow/stage1_6f/evidence_candidates/<run_id>`; creation is exclusive. An existing path or reused `run_id` is `STOP=candidate_run_id_collision`, and `manifest.run_id` must equal the root basename.
- There are no standalone durable ledger files. Physical/logical/coverage staging records exist only in memory until the final manifest embeds them.
- `max_network_attempts_per_physical_source_object = 1`. Any timeout, TLS failure, 429, or other non-404/non-3xx error is final `transport_inconclusive`; no same-URL or alternate-host retry is allowed.
- Any local ZIP/CSV write, atomic rename, read-back, hash/read, or manifest-write failure is run-fatal `candidate_root_invalid`, outranks a remote terminal status, stops the run, writes no final manifest, and requires a new `run_id` for any later attempt.
- The candidate manifest writes last only after every retained ZIP/CSV file is read back and its hash and byte length match. The independent candidate validator then reads the completed root; rejection makes that root invalid and non-consumable.
- A missing final manifest, stale temporary file, duplicate physical ID/path, path traversal, symlink, unexpected regular file, missing/extra manifest key or record, hash mismatch, or root-state mismatch means `candidate_root_invalid`.
- An interrupted root is never resumed or overwritten. A later attempt uses a new run ID and retains the interrupted root for forensic inspection.
- A completed candidate root is immutable. Its status may be reviewed but not altered to repair a failed archive.

## 7. Producer / Consumer / Authority Matrix

| Role | Artifact / boundary | Change in this Design |
| --- | --- | --- |
| Existing B/C | sealed export and completed audit root | Read-only exact authority; no producer or loader change |
| Coverage matrix | exact public archive URL list | Read-only authority for cohort and URLs |
| External user authorities | approved Design, approved collection Plan, one-run network authorization | Required future execution inputs; no self-approval or implicit network authority |
| New candidate collector | candidate root under `data/external_signal_shadow/stage1_6f/evidence_candidates/` | Future Plan only; public, read-only, single-run collector |
| Candidate manifest | new `...candidate_manifest_v1` | Future immutable collection/audit output; not an F input |
| Candidate validator | completed candidate root | Future Plan only; independent, read-only strict consumer required before audit or admission |
| Existing F reader/runner/reviewer | current `9e44...` REEF package contract | Affected but unchanged; must reject candidate identity |
| Future admission Delta | exact successful candidate manifest | Out of scope; sole path to make a new package F-consumable |

## 8. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| INV-EP01 | All B/C/matrix/F-module bytes and all three external user authorities match before any network request; a missing/mismatched Design, Plan, module, or run authorization stops with `approved_authority_mismatch`. |
| INV-EP02 | Candidate target set is exactly the 41-symbol cohort derived through canonical C loading and the frozen F denominator eligibility reducer; no raw C-field shortcut, current-universe, or hand-edited fallback. |
| INV-EP03 | Each physical object permits exactly one request to its coverage-matrix exact URL. A 3xx is terminal `redirect_refused`; every transport failure is terminal `transport_inconclusive`; no redirect destination or retry request is permitted. |
| INV-EP04 | Every expected logical archive record and every physical source object reaches exactly one explicit terminal state. The exact logical-to-physical mapping permits shared URL references but forbids duplicate physical objects; full matrix rows bind by canonical hash and fixed projection. |
| INV-EP05 | Downloaded ZIP and CSV bytes are retained, SHA-256/length bound, ZIP-member validated before direct reading, strictly parsed, symbol/time identity checked, and evaluated only by the matching Section 5.4 family predicate before a coverage result is emitted. |
| INV-EP06 | The independent strict candidate validator recomputes external/internal authority, cohort, matrix hashes/projections, logical/physical record sets, bytes, ZIP member, coverage, and root state. Manifest-last and immutable-root rules make a partial/corrupted root unreadable as completed evidence. |
| INV-EP07 | Root basename and manifest `run_id` are equal, create-exclusive, and never reused. Local durability/read-back failure is run-fatal and outranks remote archive classification. |
| INV-EP08 | Existing REEF package bytes and all existing F source/input identities remain unchanged; candidate output cannot enter current F. |
| INV-EP09 | No control selection, event-minus-control output, W2 settlement claim, alpha, PnL, replay, paper, execution, or trading permission appears in any candidate artifact. |
| INV-EP10 | All authority flags in collector status and candidate manifest are exact singleton booleans `False`: `RISK_LIVE_TRADING_ENABLED`, `trade_signal_allowed`, `paper_trading_allowed`, `live_trading_allowed`, `execution_engine_allowed`, `private_api_allowed`, `authenticated_api_allowed`, `order_api_allowed`, `alpha_interpretation_allowed`, `execution_feasibility_claim_allowed`, `net_cost_or_profit_claim_allowed`, `replay_allowed`, and `point_in_time_directional_replay_allowed`. |

## 9. Verification Strategy for a Future Plan

The future Plan must map every invariant to an implementation task, canonical fixture, negative mutation, mechanical proof, and fail-closed STOP. At minimum it must prove:

1. every authority mismatch, including Design/Plan/run authorization or either F module SHA, causes zero network calls and no candidate root;
2. the 41-symbol set is obtained only through `reconstruct_denominator(verified_c)`; a fixture that substitutes C `source_audit_eligible` alone must fail before range filtering, even when a later range filter could accidentally preserve the final 41 symbols;
3. candidate cohort cardinality/set mismatch causes zero network calls;
4. a non-matrix URL, credential/private endpoint, or current-universe path is rejected before a request; a local 3xx and a timeout/429 server each prove one initial exact-URL request, zero later requests, and the prescribed terminal status;
5. the canonical-ID test vectors in Section 5.2 reproduce their exact SHA-256 values; altered separators, whitespace, or tuple order fail;
6. the 705 logical-record / 664 physical-URL fixture proves one fetch and one retained object for a shared URL, lawful multiple logical references, exact full-row matrix hash/projection validation, and rejection of duplicate physical object IDs/paths;
7. one declared mutation each for 404, transport failure, corrupt ZIP, multiple/unsafe/encrypted ZIP member, CSV hash mismatch, invalid header, wrong `metrics_5m.symbol` (must yield `csv_invalid` / `not_proven` and contribute no rows to `metric_window_coverage`), grid timestamp gap, duplicate/conflict, incomplete BookDepth ladder, symlink, unexpected file, and post-write artifact mutation;
8. one fixture each proves the Section 5.4 results for every family: 1h grid, 5m grid, discrete funding, non-uniform complete ladder, and event-driven trades;
9. missing manifest, crash-before-manifest, extra key/record, changed authority/cohort/matrix projection, reused run ID/root, local durability failure, or inconsistent root state is rejected by the independent candidate validator;
10. existing `verify_market_evidence(...)` rejects the new candidate manifest identity;
11. existing REEF evidence package SHA-256 and current F regression suite remain unchanged; and
12. all network tests use a local test server or fixture double, never real public network in CI.

The Plan must also freeze storage capacity, sequential/concurrent request policy, timeout classification, exact user-agent policy if any, scanner actual process return code, baseline/index/worktree proof, and a disposition ledger for scanner warnings. No Plan may infer a successful candidate package before physical bytes exist.

## 10. Compatibility, Rollout, and Rollback

This Design has no runtime rollout: it creates no daemon, VPS process, deployment target, queue, database, or scheduled task. Existing F remains REEF-only and unchanged.

Rollback is a no-op for existing systems: do not delete a candidate root. If a candidate collection is invalid or incomplete, it remains non-consumable and a new run ID is required. The candidate package may be used only as review evidence until a future externally approved admission Delta binds its exact successful manifest bytes.

## 11. Design Gate

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

This Design is ready for independent review. Approval must freeze this file's exact SHA-256 externally; changing its status text after approval is forbidden because it would change the approved bytes.
