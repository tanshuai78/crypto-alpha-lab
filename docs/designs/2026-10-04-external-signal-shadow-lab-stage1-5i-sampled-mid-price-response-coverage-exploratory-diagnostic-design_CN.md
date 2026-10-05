# Stage 1.5I N=3 采样中间价响应覆盖与探索性诊断 Design

## 1. 已确认事实与历史盘点声明

1. 本 Design 的唯一 N=3 membership authority 是 sealed receipt：

   ```text
   data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/
     stage1_5g_n3_regime_stratified_admission_20261002T110403Z/
   ```

   其 artifacts SHA-256 为：

   ```text
   manifest = f3b4c76683fe7e1e4a7f28f30437f289f036f6ffc6126f8e9693faad62789adf
   summary  = c92686b4834ee41165850aba99b1b68254b05a4afaf37d5e2789747db60ca941
   review   = df6e12df8b1d105c62dd8cb01baeb0f858aa008c42488f699999a3b9ba51f2dc
   ```

   `load_verified_n3_receipt()` 已验证该 receipt 为 `3` 个 parent、`9` 个 formal child、三种隔离的 `product_regime_id`，且 `stage1_5g_gate3_complete=false`。三个 parent 是本阶段的 cluster；Batch7 的七个 child 不是七个独立事件。
2. 唯一允许的 source-root ownership 已由 N=3 receipt 的固定 `input_records` 和 parent ledger 确定：

   | owner | source root | emitted members |
   | --- | --- | --- |
   | `moonshot` | `data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot` | `MOONSHOTUSDT` |
   | `batch7` | `data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7` | `CRMLUSDT`, `BWETUSDT`, `ACNUSDT`, `MPUSDT`, `SECZUSDT`, `UNHUSDT`, `NKEUSDT` |
   | `ct_projection` | `data/external_signal_shadow/local_evidence/20261001T074500Z_stage1_5f_ctusdt` | `CTUSDT` only |

   The CT root physically retains Batch7 snapshots. They are an upstream duplicate projection, not CT-owned I input. A global recursive scan across all roots would double-count Batch7 observations and is forbidden.
3. **Historical I-0 declaration, not Design authority.** A local inventory was reported at `/tmp/stage1_5i_inventory_output/stage1_5i_evidence_inventory.json` with SHA-256 `68c3441a73c70a88491a1facc2b99ebe6a9103af89f56066a0f6793e53ee31d7`, including `710-717` valid snapshots, approximately `60-61` second adjacent intervals and maximum `66.676` seconds. Its bytes and generating command/script were not supplied to the independent Design reviewer; these figures are historical provenance only and do not set an I rule, threshold, success state or authority. All implementation/review decisions must independently re-admit the current roots under Sections 4-5. An external reviewer may separately verify the old claim only from the exact JSON plus its original command/script bytes.
4. The observer's configured window is `12h` with nominal polling interval `60s`. **Historical timing declaration, not Design authority:** the unavailable original I-0 inventory reported first valid samples `36.375-55.001s` after `observation_window_start_ms` and `3494.262-17008.676s` after `detected_at_ms`. These unverified figures set no acceptance threshold or terminal state. Whether independently recomputed or not, `observation_window_start_ms` is only a configured/admitted observation-window anchor, not proof that an immediate post-announcement reaction was captured or that an executable entry was available.
5. Stage 1.5H's sealed receipt is a verified static friction-context input only:

   ```text
   data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/
     stage1_5h_n3_regime_stratified_friction_20261003T070500Z/
   manifest = c9034ae8c079e066b1de5a8c092bad00a054170aa22a28392df2f24dd0487bcc
   summary  = 1dba9853878d24da8cd3d7ae99f0ec899bfc3d1a90ddcc1399e999659e498b11
   review   = ea774319e905de0ed4e8a62c44238cc33d4e0ac5994188198ee356c4220082b3
   ```

   Its `sum_of_marginal_p95_slippage_bps` is not a paired round-trip percentile, fill estimate, fee-inclusive cost, cost floor, or net-PnL comparator.
6. The current G/H source contracts are frozen input dependencies, with current bytes:

   | path | SHA-256 |
   | --- | --- |
   | `src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py` | `e64abe50b97d5cea303552c59f8f8f98168297ab0cabadfb554de9c1340c0c3d` |
   | `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py` | `596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d` |
   | `src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py` | `2657e5550796ed772abf8acffc5b70b1de22f9c2a33cfb88c824df668655a1bf` |
   | `configs/base.py` | `414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4` |

   The project has no usable `graphify` module. Source and targeted tests, not `graphify-out/`, are authoritative for this Design.

## 2. Core issue, alternatives and decision

### 2.1 Core issue

The admitted N=3 cohort has trustworthy, regularly sampled L2 top-of-book snapshots, but no approved consumer describes the sampled mid-price path after the configured observation-window start. Treating static H friction as a net-cost model, treating children as independent parents, or merging duplicate root files would create an unsupported Alpha or price-path claim.

### 2.2 Alternatives

| alternative | decision | reason |
| --- | --- | --- |
| Wait for more events before any price research | reject | The existing frozen N=3 data is sufficient for a bounded descriptive case study; additional events remain necessary for any later independent validation. |
| Build an event backtester, simulator, or net-PnL model | reject | The inputs have no fees, funding, executable fills, entry/exit specification, or complete intraperiod path. |
| Extend Stage 1.5H in place | reject | H's frozen scope is static friction only and explicitly excludes raw depth/price paths. |
| Create a fixed N=3 sampled-mid coverage and descriptive diagnostic | adopt | A single new read-only consumer can expose coverage and observed sampled paths while preserving all upstream boundaries. |

### 2.3 Decision

Create an independent **Stage 1.5I N=3 Sampled Mid-Price Response Coverage and Exploratory Diagnostic**. It strict-loads the exact G and H receipts, re-admits the three exact roots using the frozen G reducer, then reads only the selected owned snapshot rows needed to form sampled mid-price observations.

The diagnostic has two distinct terminal publications:

```text
coverage_inventory
complete_n3_exploratory_analysis
```

`coverage_inventory` may report per-child gaps, missing horizons, and exact reasons. `complete_n3_exploratory_analysis` is permitted only when all 3 parents and all 9 owned children pass the exact completeness contract in Section 5. It remains an exploratory, descriptive result, never a strategy conclusion.

## 3. Scope and non-goals

### 3.1 In scope

- A new I core module, zero-argument production CLI, tests, and a separate output namespace under `data/external_signal_shadow/stage1_5i/`.
- Strict N=3 G receipt and H friction receipt verification before every source read.
- Exact source ownership, per-child sampled midpoint series, source timestamps, coverage inventory, and fixed-horizon sampled responses.
- Per-child sampled extrema relative to its anchor, explicitly labeled sampled rather than complete-path MAE/MFE.
- Three parent-local descriptive rows, each retaining regime and child count; no cross-parent/regime reduction.
- H's same-parent static friction fields as a visibly separate `friction_context` block.

### 3.2 Explicit non-goals

- No modification of G, H, D, F, prior tests, historical roots, prior receipts, or `configs/base.py`.
- No network, VPS, SSH, exchange/API call, collector/observer change, replay, simulator, fill model, order, signal, execution, paper trading, or live action.
- No announcement-immediate response, open-price, market-open, executable-price, full-path high/low, full MAE/MFE, forecast, direction, PnL, fee, funding, cost coverage, capacity, or Alpha claim.
- No regime pooling, child-to-parent independence upgrade, ranking, threshold optimization, parameter search, discovery of a fourth root, fallback root selection, or future extension registry.
- No reinterpretation of `stage1_5g_gate3_complete=false` or assertion about current collector liveness.

## 4. Authority, TCB and topology contract

### 4.1 Frozen upstream admission and TCB

The I core must verify the four Section 1.6 modules before and after import: expected project-contained path, non-symlink ancestors, `__file__`, `__spec__.origin`, resolved path and current SHA-256. Missing, shadowed, preloaded with a wrong origin, or changed-after-import module is fatal. It must strict-load the exact G/H roots with no caller-selected root or `future_consumer_allowed=True`, then compare their individual artifact bytes to Section 1.

**Protected:** accidental/local byte drift, wrong G/H receipt, source-root or source-file substitution, duplicate ownership, invalid receipt/manifest/schema, wrong time anchor, partial publication, symlink escape and cooperating same-`RUN_ID` writers.

**TCB:** CPython, `hashlib`, `json`, `math`, `statistics`, `pathlib`, `os`, `fcntl.flock`, completed local filesystem `rename`/`fsync` semantics, the checked project root, and a non-malicious privileged local operator. This Design does not claim protection from a malicious privileged operator, compromised kernel/interpreter/filesystem, SHA-256 collision, post-check path swaps, or processes that ignore advisory `flock`.

### 4.2 Exact re-admission, file locator and ownership

For each fixed input record, the real frozen G invocation is exactly:

```python
bundle = load_stage1_5g_inputs(EXACT_SOURCE_ROOT)
recomputed = build_stage1_5g_review_summary(
    summary=bundle.summary,
    watermark=bundle.watermark,
    states=bundle.states,
    accepted_events=bundle.accepted_events,
    snapshots=bundle.snapshots,
    request_manifest_rows=bundle.request_manifest_rows,
    output_root=EXACT_SOURCE_ROOT,
    loader_blockers=bundle.loader_blockers,
    source_evidence_manifest_sha256=bundle.source_evidence_manifest_sha256,
)
```

`bundle.loader_blockers` must be empty. The source manifest hash, stored/recomputed G identity projection, N=3 `input_records`, parent ledger, product-regime ledger and formal child identity must exact-match before I reads any source file.

For an owned child, I then locates **exactly one** file by the manifest-constrained literal pattern:

```text
<owned_source_root>/depth_snapshots/**/<event_symbol_id>.jsonl
```

The match must be one regular non-symlink file, project-contained and listed by the already-verified root `SHA256SUMS`. I parses that one JSONL file in append order. Its parsed row list must exact-equal, including order and all keys/values, the list obtained by filtering `bundle.snapshots` for that exact `event_symbol_id`; otherwise STOP=`stage1_5i_source_file_bundle_mismatch`. This is the sole bridge from the G aggregate bundle to the physical source path.

The fixed owner map is Moonshot -> Moonshot child, Batch7 -> its seven children, and `ct_projection` -> `CTUSDT` only. The seven Batch7 files physically retained below the CT root are not selected, emitted, counted, or treated as an error. A selected file for an unowned child, a second match, a no-match, or any child outside fixed membership is a STOP.

The accepted one-file matches are frozen to these relative paths; the locator is a verification of this table, not a discovery mechanism:

| owner | symbol | `source_snapshot_relative_path` |
| --- | --- | --- |
| `moonshot` | `MOONSHOTUSDT` | `depth_snapshots/20260922/e0b48e9ff025e75ca0e682b3e77a973e7170c9859bd84877bc3f50a27f28b602.jsonl` |
| `batch7` | `CRMLUSDT` | `depth_snapshots/20260929/09da9a8516ad799b304fe2cf5d0f3b27bba2706099f9008c2650e3c468ea8035.jsonl` |
| `batch7` | `BWETUSDT` | `depth_snapshots/20260929/f49cf85ef4e96d5ddfcd4f8c0e5ec507d2d031ebba6ec3dc0fd59b8ad66a09f9.jsonl` |
| `batch7` | `ACNUSDT` | `depth_snapshots/20260929/f66e0e5a56fdbfefc3292200a37a41ce1c2f07374aba4a117fafd72262a2a3f8.jsonl` |
| `batch7` | `MPUSDT` | `depth_snapshots/20260929/b8aee4aeddb1e22360a23912b748def6677fc4406155cb140597aea2b53a541e.jsonl` |
| `batch7` | `SECZUSDT` | `depth_snapshots/20260929/62a15b5bb8f3ad7afe704ed49514874faff1d2e01f58e9e5cb6f43b704f238e2.jsonl` |
| `batch7` | `UNHUSDT` | `depth_snapshots/20260929/c69d52018ff86725529c39327294809d7c23c7e9e9e119445c6f7fbf71575250.jsonl` |
| `batch7` | `NKEUSDT` | `depth_snapshots/20260929/2663af65922c547147e7a76d61453ddd9c4050a9c7abc0e5cfd089cd2b796650.jsonl` |
| `ct_projection` | `CTUSDT` | `depth_snapshots/20261001/88df6bae915fb096ea7fe92b4a92d22b3c5b7b268e999636ff062c3fd9989345.jsonl` |

### 4.3 Time-anchor authority

For each owned child, select exactly one accepted-event row and exactly one reduced completed-state row by matching `event_symbol_id`, `event_id`, `symbol`, parent article and parent event to the fixed membership. Both rows must contain a non-bool integer `observation_window_start_ms`, and their values must be exactly equal. Missing, duplicate, mismatched, or non-integer anchor values are `STOP=stage1_5i_anchor_authority_mismatch`.

`detected_at_ms` is read only from the accepted-event row as descriptive provenance; it never determines an anchor, completeness, horizon, or decision. `observation_started_at_ms` is not an alternative anchor.

### 4.4 Producer, writer, loader, consumer matrix

| role | owner/artifact | required behavior | prohibited behavior |
| --- | --- | --- | --- |
| G loader/reducer | frozen Stage 1.5G module | validate root provenance/formal identity and recompute the source review | new wrapper or altered G API |
| H loader | frozen Stage 1.5H module | validate static friction context | calculate price or economics |
| I file reader/reducer | new I core | bridge verified bundle to one verified owned JSONL and reduce coverage | root discovery, union glob, row fallback or source substitution |
| I writer/loader | new I core | strict schema, canonical artifacts and no-resume publication | accept partial/symlinked/foreign root |
| downstream consumer | none | N/A | treat I as Alpha, signal, PnL or execution authority |
| reviewer | Design/Plan/Completion Audit | real loaders plus declared reducer-only mutations | trust Markdown or producer self-report |

## 5. Data, time, state and output contract

### 5.1 Row classification and fixed observation rule

The selected physical-file rows must be valid JSON objects with exact owned `event_symbol_id`/`symbol`, non-bool integer `fetched_at_ms` and `exchange_time_ms`. Duplicate or non-increasing `fetched_at_ms`, duplicate row identity, non-increasing `exchange_time_ms`, malformed JSON, foreign identity, or non-finite timestamp is an upstream structural contradiction and STOPs the run.

A structurally valid row whose `best_bid`/`best_ask` is non-numeric, non-finite, non-positive or crossed is an `invalid_price_row`. It remains counted in the child coverage record and makes that child `coverage_gap`; it cannot be silently filtered into a complete result. This case is expected to be rejected by a clean G source before I in production, but is a valid I pure-reducer negative fixture.

For every structurally valid child, form `valid_price_rows` by excluding only `invalid_price_row` rows, retaining their count and their `invalid_price_row` reason in the same child record. Locate anchor and horizons exclusively from `valid_price_rows`:

```text
anchor_row = first valid row with fetched_at_ms >= authoritative observation_window_start_ms
anchor_mid = (best_bid + best_ask) / 2
anchor_delay_ms = anchor_row.fetched_at_ms - observation_window_start_ms
```

No anchor is a `coverage_gap`, not a STOP. A first-row invalid price with a later valid row therefore has that later valid anchor; an invalid intermediate row does not erase otherwise locatable horizon observations; an all-invalid child has `missing_anchor`. The anchor is a sampled post-window observation, not a market-open, announcement-time, executable-entry or point-in-time decision price.

The only horizons are `15m=900000ms`, `1h=3600000ms`, and `4h=14400000ms` after `anchor_row.fetched_at_ms`. For horizon `h`, select the first valid row with timestamp in closed interval `[anchor+h, anchor+h+120000ms]`. No candidate is a `missing_horizon_<h>` coverage gap. There is no interpolation, backward fill, forward extension, nearest neighbor, resampling, bar construction or 12-hour metric. `120000ms` is a two-poll coverage locator, not an economic parameter.

For a present horizon, `sampled_mid_return_bps = 10000 * (mid_h / anchor_mid - 1)`. `sampled_mfe_bps` and `sampled_mae_bps` are the maximum/minimum sampled-mid returns from anchor through the selected 4h row. They are not full-path extrema, stop outcomes or tail bounds.

### 5.2 State precedence and completeness

| condition | result | publication |
| --- | --- | --- |
| execution/generation authority, module, G/H receipt, source manifest, G re-admission, file ownership, JSON/identity/time-anchor structure failure | STOP | none |
| known CT-root Batch7 duplicate file | exclude before selection | no effect |
| structurally valid owned child has invalid price row, no valid anchor, or missing frozen horizon | `coverage_gap` child row with exact reason | only `coverage_inventory` |
| all nine child rows complete | `complete` child rows | `complete_n3_exploratory_analysis` |

Every reduction first creates exactly nine rows in fixed `(parent_article_id, event_symbol_id)` order. `complete_n3_exploratory_analysis` requires three exact parent rows, each child exactly once, one owned file per child, zero invalid-price rows, one anchor and all three horizons for every child. It is prohibited to drop a child or parent after detecting a gap.

### 5.3 Exact summary grammar

Canonical summary has exactly:

```text
analysis_state
authority_flags
coverage_inventory
decision
g_receipt_binding
h_receipt_binding
parent_descriptive_rows
run_id
schema_version
source_root_bindings
```

`schema_version=1`. `analysis_state` and `decision` are one of exactly:

```text
coverage_inventory                  / stage1_5i_coverage_inventory_published
complete_n3_exploratory_analysis    / stage1_5i_complete_n3_exploratory_analysis_published
```

`g_receipt_binding` and `h_receipt_binding` each have exactly `root_relative_path`, `run_id`, `manifest_sha256`, `summary_sha256`, `review_sha256`, equal to Section 1 literals. `source_root_bindings` is exactly the three fixed records in Section 1.2 order, each with `input_key`, `source_root_path`, `source_manifest_sha256`, `stored_summary_path`, `stored_summary_sha256`, `owned_event_symbol_ids` and `owned_snapshot_relative_paths`; the last two fields are fixed duplicate-free ordered lists derived from Section 4.2, never discovered at write time.

`coverage_inventory` has exactly `parent_count`, `child_count`, `parent_rows`; values are `3`, `9`, and exactly three rows in fixed parent order. A parent row has exactly `parent_article_id`, `parent_event_id`, `product_regime_id`, `child_event_symbol_ids`, `child_symbol_count`, `children`. `child_event_symbol_ids` and `children` have exact N=3 membership/order; `child_symbol_count` equals their length.

A child row has exactly:

```text
parent_article_id parent_event_id product_regime_id event_symbol_id symbol
owner_input_key source_snapshot_relative_path raw_snapshot_count
valid_mid_snapshot_count invalid_price_row_count child_state gap_reasons
detected_at_ms observation_window_start_ms anchor horizons sampled_path
```

`child_state` is exactly `complete` or `coverage_gap`; `gap_reasons` is a sorted duplicate-free list of only `invalid_price_row`, `missing_anchor`, `missing_horizon_15m`, `missing_horizon_1h`, `missing_horizon_4h`. A `complete` row has `gap_reasons=[]`; a `coverage_gap` row has a non-empty list. `invalid_price_row` appears if and only if `invalid_price_row_count > 0`; `missing_anchor` appears if and only if no valid row reaches the authoritative anchor; each `missing_horizon_*` appears if and only if an anchor exists but its exact forward interval has no valid row.

`anchor` is either `null` only for a `coverage_gap` with `missing_anchor`, or an object with exactly `fetched_at_ms`, `exchange_time_ms`, `mid_price`, `anchor_delay_ms`. `horizons` has exactly `15m`, `1h`, `4h`: if anchor is null, all three are null and no `missing_horizon_*` reason appears; otherwise each value is null if and only if its matching missing reason exists, or an object with exactly `fetched_at_ms`, `exchange_time_ms`, `mid_price`, `sampled_mid_return_bps`, `offset_from_anchor_ms`. `sampled_path` is null for every gap row, including a row whose only reason is `invalid_price_row`; it is an object with exactly `sampled_mae_bps`, `sampled_mfe_bps`, `sample_count_through_4h` only for a complete row.

All IDs/hashes/path/count/number values use the exact type grammar: lowercase fixed-length hexadecimal IDs/hashes; fixed project-relative paths without `..`; non-bool non-negative integers for timestamps/counts; finite non-bool JSON numbers for mids/returns; no `NaN`, infinity, coercion or default.

`parent_descriptive_rows` is exactly the same three parent identities/order, with exactly `parent_article_id`, `parent_event_id`, `product_regime_id`, `child_symbol_count`, `friction_context`. `friction_context` is an exact same-parent copy from H and has no derived cost verdict. It never contains a response, rank, pool, regime distribution or strategy conclusion.

`authority_flags` has exactly these nineteen boolean-false keys:

```text
alpha_claim_allowed
alpha_interpretation_allowed
commit_allowed
cost_coverage_claim_allowed
deployment_allowed
event_family_conclusion_allowed
execution_engine_allowed
execution_feasibility_claim_allowed
full_mae_mfe_claim_allowed
full_price_path_claim_allowed
live_trading_allowed
net_pnl_claim_allowed
network_collection_allowed
paper_trading_allowed
push_allowed
replay_allowed
ssh_allowed
strategy_direction_claim_allowed
trade_signal_allowed
```

### 5.4 Manifest, Markdown, publication and recovery

The fixed output grammar is:

```text
RUN_ID       = ^stage1_5i_n3_sampled_mid_price_response_[0-9]{8}T[0-9]{6}Z$
FINAL_ROOT   = data/external_signal_shadow/stage1_5i/n3_sampled_mid_price_response/<RUN_ID>/
STAGING_ROOT = data/external_signal_shadow/stage1_5i/n3_sampled_mid_price_response/.<RUN_ID>.staging.<pid>/
```

Final root contains exactly manifest, summary and review named `stage1_5i_n3_sampled_mid_price_response_{manifest.json,summary.json,review_CN.md}`. Manifest has exactly `schema_version`, `run_id`, `g_receipt_manifest_sha256`, `g_receipt_summary_sha256`, `g_receipt_review_sha256`, `h_receipt_manifest_sha256`, `h_receipt_summary_sha256`, `h_receipt_review_sha256`, `artifacts`; the summary/review entries have exactly `relative_path`, positive non-bool `byte_count`, and actual lowercase `sha256`.

All JSON is canonical UTF-8. Markdown is only the deterministic render of canonical summary and must strict-rerender byte-for-byte. Before any resolve/read/write, every project/output/staging/final/artifact ancestor is rejected if symlinked; resolved paths remain inside their declared namespace.

Under one output-parent directory `flock`, the writer verifies all authority and data in memory; writes+file-`fsync`s summary, review and manifest last; `fsync`s staging directory; strict-loads staging; atomically renames only into an absent final root; then `fsync`s the final parent directory; reclassifies and strict-loads final root. A failure before rename leaves `staging_only`; a failure after rename but before/at parent `fsync` is `POST_RENAME_DURABILITY_FAILURE`. Both are non-success, no-resume/no-cleanup/no-overwrite states. Existing final root or any matching staging sibling is a STOP.

### 5.5 Exact generation authority

There is one public production route: `run_diagnostic(run_id)`. It has no non-publication mode and accepts no root, bundle, source, output or hook parameter. Before importing a frozen source module, reading a source root, creating staging or writing any file, it verifies ordinary implementation authority **and** the following local generation authority.

The unique project-contained, non-symlink bundle is:

```text
.git/plan-execution/stage1_5i_n3_sampled_mid_price_response/<APPROVED_I_PLAN_SHA256>/
  receipt_generation_authorization.txt
  receipt_generation_authorization.sha256
```

The sidecar exact ASCII bytes are `<AUTH_SHA256>  receipt_generation_authorization.txt\n`, where hash covers the exact UTF-8 authorization bytes. The text has exactly five lines plus final LF:

```text
我批准本地生成 Stage 1.5I N=3 sampled-mid-price response receipt：<APPROVED_I_PLAN_REL_PATH>（SHA-256: <APPROVED_I_PLAN_SHA256>）。
RUN_ID: <AUTHORIZED_RUN_ID>
I_CORE_SHA256: <CURRENT_I_CORE_SHA256>
I_CLI_SHA256: <CURRENT_I_CLI_SHA256>
允许仅本地生成 Stage 1.5I N=3 sampled-mid-price response receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。
```

Validator requires exact Design/Plan disk hashes and paths from ordinary implementation authority, exact `RUN_ID`, exact current core/CLI hashes and exact permission line. Missing, malformed, stale, substituted or mismatched files return `STOP=local_receipt_generation_not_authorized` before side effects. Internal pure reducers may receive already-validated in-memory canonical fixtures in tests only; they are not public authority bypasses.

## 6. Fail-closed reducer sequence

1. Resolve project root from I core; reject caller-controlled roots and symlink ancestors.
2. Public route verifies ordinary implementation authority and exact local generation authority.
3. Verify/import/re-verify frozen G/H/config modules; strict-load exact G/H receipts and artifact hashes.
4. For each fixed root, execute the real G call in Section 4.2 and verify every lineage projection.
5. Locate/parse/compare exactly one owned source file per child; exclude known CT-root Batch7 duplicates before any row reduction.
6. Resolve matching accepted/state anchor pair. Structural identity/time errors STOP. Reduce all nine child coverage records under Section 5.1.
7. Select the sole allowed terminal analysis state under Section 5.2; no child omission or success fallback.
8. Canonicalize, render, stage, strict-load, rename, parent-`fsync`, reclassify and strict-load final root. Any failure is non-success.

## 7. Acceptance invariants

1. **INV-15I-01 N=3 identity:** only exact G receipt bytes define parent, child, ownership and regime membership.
2. **INV-15I-02 Root/file ownership:** each emitted child bridges to exactly one manifest-verified designated JSONL; CT-root Batch7 copies are excluded, not fatal.
3. **INV-15I-03 No silent attrition:** all nine children appear in every valid inventory; any child gap prevents complete N=3 state.
4. **INV-15I-04 Time authority:** accepted/state `observation_window_start_ms` exact-match; `detected_at_ms` is provenance only; no announcement-immediate claim exists.
5. **INV-15I-05 Sampled-only claim:** no interpolation, complete path, executable price, full MFE/MAE, PnL or economic assertion.
6. **INV-15I-06 Fixed exploratory rule:** only 15m/1h/4h and forward 120000ms locator; no outcome tuning.
7. **INV-15I-07 Cluster/regime separation:** parent is the only independent unit; no cross-parent/regime pool or conclusion.
8. **INV-15I-08 Friction separation:** H context is copied, never used to net/gate/rank response.
9. **INV-15I-09 Schema/lifecycle integrity:** nested schema, manifest, canonical bytes, post-rename parent `fsync`, strict load and no-resume behavior are exact.
10. **INV-15I-10 Authority isolation:** all nineteen flags are exactly boolean false; no path grants Alpha, network, commit, push, SSH, execution, paper or live authority.

## 8. Verification and fixture provenance

Positive boundary tests call real G/H strict loaders and derive membership/source rows from frozen canonical artifacts. Handcrafted positive G/H receipts, membership, manifest hash or source-lineage fixtures are forbidden. Reducer-only negative tests start from a real validated bundle/file projection, then make one explicit in-memory mutation after the upstream gate has passed.

| case | mutation/proof boundary | required result |
| --- | --- | --- |
| canonical complete coverage | real G/H roots and owned files | exactly nine owned rows and one complete state only when all horizons resolve |
| source-byte mutation | mutate one temporary source file without updating manifest | G manifest gate STOP; no inventory |
| CT duplicate isolation | attempt selection of CT-root Batch7 file | STOP before reducer |
| missing horizon | after real loader, remove all in-memory valid rows in selected `[anchor+4h, anchor+4h+120000ms]` interval | `coverage_inventory`, all nine rows retained |
| invalid intermediate row | after real loader, mutate one non-anchor/non-horizon in-memory owned bid/ask invalid | `invalid_price_row`, locatable anchor/horizons remain concrete, `sampled_path=null`, no complete state |
| invalid first row | after real loader, mutate the first in-memory owned bid/ask invalid while a later valid row remains | later valid anchor is concrete, `invalid_price_row`, no fabricated `missing_anchor` |
| all invalid rows | after real loader, mutate every in-memory owned bid/ask invalid | `invalid_price_row` plus `missing_anchor`, null anchor/horizons/path, no complete state |
| time/anchor conflict | one in-memory timestamp mutation or accepted/state anchor disagreement | STOP |
| receipt/source/H drift | one artifact/lineage/context mutation | STOP before publication |
| schema mutation | extra/missing key, null in complete row, wrong flag/horizon offset | strict loader STOP |
| authority mutation | one text/sidecar/path/SHA/run-id mutation | STOP before import/read/output |
| durability/restart | staged, same-ID final, foreign staging, and after-rename-before-parent-fsync failpoints | no resume/overwrite and no false success |

The Plan must run focused tests, `ruff check` only on I files, `anti_shortcut_scan.py` with actual RC, strict-load its output, independently traverse for symlinks, and assert `RISK_LIVE_TRADING_ENABLED is False`.

## 9. L2 research boundary

| L2 requirement | Stage 1.5I decision |
| --- | --- |
| hypothesis | A configured observation-window may have a descriptively measurable sampled mid-price path. No directional or economic mechanism is asserted. |
| claim level | `evidence_insufficient` unless and until a later approved stage evaluates a separately preregistered phenomenon claim. |
| independent unit | one `parent_article_id`; all Batch7 children remain within one parent cluster. |
| point-in-time boundary | frozen rows are historical sampled observations; they do not establish what an earlier decision system knew or a continuously observed path. |
| outcome metrics | fixed sampled 15m/1h/4h returns plus sampled extrema. No win rate, expectancy, confidence interval, significance, PnL or cost-adjusted return. |
| friction/capacity | H static fields are descriptive context only; fees, funding, fills, holding costs and capacity are unmeasured. |
| MAE/tail risk | sampled extrema are lower-resolution descriptive observations, not a survival or stop analysis. |
| promotion / kill | none. A weak or adverse current case can prioritize or pause research resources, but cannot falsify a product/event family. |
| evidence gap | invalid/missing roots STOP; valid but incomplete child horizons publish only `coverage_inventory`; valid complete data still does not establish Alpha. |
| deferred gates | candidate statistical edge, robustness, economic/executable edge, capital survival, shadow validation and all trading permissions. |

## 10. Compatibility, rollout and rollback

This is a new, isolated consumer. G/H source, output and loader contracts are No-Touch. No migration exists: legacy N=2 G/H roots, previous H V3 receipt, and any future G receipt are rejected rather than adapted. Rollback is simply not approving or not running the new I implementation; no existing receipt needs alteration.

## 11. Open questions and self-review

- **Non-blocking: future independent validation sample size.** This Design intentionally defines no numeric Alpha sample threshold because it makes no Alpha claim. A later strategy/validation Design must define independent parents, correlation exclusions, cost model and preregistered promotion/kill criteria from then-current evidence.
- **Non-blocking: additional horizons.** `12h` is excluded: all current observed sequences are slightly shorter than a full anchor-to-12h interval. Adding it requires a new Design rather than silently changing this fixed exploratory rule.
- **No unresolved implementation-path question.** The producer, inputs, ownership, state reduction, output contract, failure behavior, recovery rule, test provenance, claims and permissions are defined here. This Design does not authorize implementation, receipt generation, commit, deployment, network, replay, paper trading or live action.
