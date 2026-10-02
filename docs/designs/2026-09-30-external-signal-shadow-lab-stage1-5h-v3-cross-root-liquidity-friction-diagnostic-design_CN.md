# Stage 1.5H V3 Cross-Root Liquidity Friction Diagnostic Design

**状态：** Design candidate，未批准实施。  
**日期：** 2026-09-30  
**范围：** 仅本地、只读、冻结 Stage 1.5G cross-root evidence 的描述性流动性摩擦诊断。  
**不授权：** Alpha、交易信号、execution feasibility、replay/backtest、paper/live trading、网络、SSH、commit、push、deployment 或 runtime action。

## 1. 已确认事实

1. 已 sealed 的 Stage 1.5G cross-root receipt 位于：`data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z/`。
2. 其真实 summary 文件是 `stage1_5g_cross_root_admission_summary.json`，SHA-256 为 `9f45b4c184f4cb3d76944eb3e5bef51af3cd7a3277028196e0fb84eb293516c0`；strict loader 要求 summary、review 和 manifest 三个文件精确存在且完整性通过。
3. receipt 的唯一合法结论是：`cross_root_evidence_count_status=sufficient`、`stage1_5g_gate3_complete=false`、2 篇 parent article、2 个 independent parent event、8 个 formal child symbol。
4. 两个输入根均已通过 Stage 1.5G clean-depth review：`20260923T025100Z_stage1_5f_moonshot` 与 `20260930T021507Z_stage1_5f_batch7`。它们的 per-symbol quality 字段已包含静态 `spread_bps`、500 USDT buy/sell slippage、top bid/ask depth、availability 及 invalid-book 计数。
5. 8 个 child symbol 不是 8 个独立事件：`MOONSHOTUSDT` 属于一个 parent event，另 7 个 symbol 共享另一个 parent event。
6. Stage 1.5G receipt 的 13 个 authority flags 必须全部为 `false`，其中包括 `event_family_conclusion_allowed`、`alpha_interpretation_allowed` 和 `execution_feasibility_claim_allowed`。
7. 已有 Stage 1.5H / V2 是特定 input authority 下的 static read-only report；它不能自动消费本 receipt。

## 2. 核心问题与决策

### 2.1 核心问题

当前已有跨 root 的冻结样本数量准入，但没有被授权的 consumer 来机械展示：在这两个 parent event 的已捕获 L2 快照中，各 symbol 和 parent 的静态 spread、深度、slippage 与摩擦分布是什么。

`stage1_5g_gate3_complete=false` 不是本 Design 要修复的 defect。它表示本地 receipt 不能证明 VPS 上 Stage 1.5D/1.5F 的持续运行状态；本 Design 不依赖、也不改变该状态。

### 2.2 决策

新增一个最小 consumer：**Stage 1.5H V3 Cross-Root Liquidity Friction Diagnostic**。它严格重验 receipt 和两个 frozen root，再从 upstream 已验证的 per-symbol quality metrics 投影出：

- 8 个 child symbol 的描述性静态质量行；
- 2 个 parent event 的 cluster summary；
- 不跨 parent 作显著性、胜率、EV、可执行性或策略结论的 cohort summary。

V3 自身不解析、glob 或直接打开 raw depth row；它只调用 §4.1 冻结的 Stage 1.5G production loader/reducer。该上游 loader 为重新准入而在其自身边界内读取 frozen `depth_snapshots/**/*.jsonl` 和 frozen local heartbeat/request-manifest artifacts；V3 只接收其 recomputed summary。V3 不读取价格 outcome、forward return、成交、订单或 P/L，避免把静态 depth 快照伪装成 fill model。

## 3. 范围与非目标

### 3.1 In scope

- 仅读取本 Design §4 指定的本地 frozen receipt、两个 stored review summary 及其 source root；
- 通过 §4.1 冻结的 upstream production loader/reducer 重新准入；该上游边界内的 raw-row / local heartbeat 读取仅用于验证 frozen source-root integrity，而非 V3 自有分析输入；
- 为 8 个 receipt-member 生成 deterministic per-symbol / per-parent / cohort descriptive metrics；
- 写入单一 fresh output root，并采用 manifest-last sealing。

### 3.2 Explicit non-goals

- 不将 `stage1_5g_gate3_complete` 变为 `true`，不读取当前 VPS heartbeat，也不做 runtime health attestation；冻结 source root 内被 upstream re-admission 所需的历史 heartbeat 不构成当前 runtime claim；
- 不作 price outcome、收益、expectancy、PnL、strategy、entry、exit、holding、sizing、threshold、risk-veto 或 Alpha claim；
- 不作 order simulation、fill model、queue position、latency model、replay 或 backtest；
- 不访问网络、private API、authenticated API、order API，也不读写 exchange state；
- 不修改或停止 Stage 1.5D/1.5F，亦不改变 `configs/base.py` 的任何阈值；
- 不对 2 个 parent event 做总体推广，不把 8 个 child symbol 当成 iid sample。

## 4. Authority 与输入契约

### 4.1 Frozen authority packet

Future implementation 的 Task 0 必须在任何导入、读取、写入前验证：

```text
APPROVED_DESIGN_PATH = this file
APPROVED_DESIGN_SHA256 = user-approved final SHA-256
APPROVED_PLAN_PATH = future approved Plan
APPROVED_PLAN_SHA256 = user-approved final SHA-256
CROSS_ROOT_ROOT = data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z
CROSS_ROOT_MANIFEST_SHA256 = a3b9a45d3c4fbed9ed1136add956a0d0266236298f9be4b754d11134feb65467
CROSS_ROOT_SUMMARY_SHA256 = 9f45b4c184f4cb3d76944eb3e5bef51af3cd7a3277028196e0fb84eb293516c0
```

The exact Reviewed Upstream Contract Packet is:

```text
src/research/external_signal_shadow/stage1_5g_cross_root_event_family_admission.py
  = b6a1c9f1348985a7407d41b67b240656faac84cb0e362e7191a2731a2f098570
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
  = 596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d
configs/base.py
  = 414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4
src/research/external_signal_shadow/safety.py
  = 1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d
```

Task 0 verifies every file byte hash and verifies each imported module's `__file__` and `__spec__.origin` resolve under the project root to the exact frozen file before import/call. `load_verified_cross_root_receipt(CROSS_ROOT_ROOT)` must then pass first. Any TCB, manifest, review projection, summary, source-root re-admission, hash, type, schema, parent-ledger, membership or false-vector failure is:

```text
STOP=stage1_5h_v3_upstream_contract_drift
or STOP=stage1_5h_v3_cross_root_authority_mismatch
```

The receipt is an input identity, not a producer-execution proof and not a Gate-3 runtime completion proof.

### 4.2 Exact input membership

The only accepted receipt identity is the following exact frozen set:

| input_key | source root | source manifest SHA-256 | parent event | symbols |
| --- | --- | --- | --- | --- |
| `moonshot` | `data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot` | `611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db` | `e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5` | `MOONSHOTUSDT` |
| `batch7` | `data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7` | `0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280` | `d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0` | `CRMLUSDT`, `BWETUSDT`, `ACNUSDT`, `MPUSDT`, `SECZUSDT`, `UNHUSDT`, `NKEUSDT` |

**Receipt identity check.** `input_records` and `parent_ledger` are identity/count authority only. V3 compares them only against the independently re-admitted source-root identity projection: `input_key`, stored summary path/SHA, source root path/manifest SHA, `event_symbol_id`, `event_id`, `symbol`, `source_article_id`, `evidence_label`, `state_status` and `formal_completed`.

Quality fields MUST NOT be read from, inferred from, or compared against `cross_root receipt.input_records` or `parent_ledger`.

**Quality evidence check.** For each receipt-authorized source root, V3 calls the frozen production `load_stage1_5g_inputs(source_root)` followed by frozen production `build_stage1_5g_review_summary(...)`. The loader may internally open frozen raw source artifacts; V3 itself may not. It then validates that the stored review summary and recomputed summary have equal per-symbol quality projections for exactly the receipt-authorized child identities, and validates that each exact recomputed review summary is:

```text
schema_version = 2
decision = stage1_5g_depth_evidence_clean_pass
clean_depth_evidence_pass = true
quarantined_depth_evidence_pass = false
blockers = []
```

The quality projection is exactly the §5.1 metric object plus `valid_snapshot_count_after_quarantine`, `invalid_book_row_count`, and `book_availability_ratio`, taken from `quarantine.per_symbol_quarantine_metrics[event_symbol_id]`. The stored/recomputed field keys, types and values must be equal. Missing, duplicate, substituted, additional or cross-parent child rows reject the entire invocation; partial output is forbidden.

### 4.3 Upstream raw-row ownership

Only the frozen `stage1_5g_live_depth_evidence_review.py` production loader/reducer may read frozen raw `depth_snapshots/**/*.jsonl`, local historical heartbeat or request-manifest artifacts during source-root re-admission. V3-owned code must not implement a second raw reader, glob, parser, percentile recomputation or direct `open()` to those artifacts. Its sole analysis input is the stored/recomputed per-symbol quality projection after equality validation.

### 4.4 Required all-false authority vector

The exact output `authority_flags` key set is:

```text
alpha_interpretation_allowed
commit_allowed
deployment_allowed
event_family_conclusion_allowed
execution_engine_allowed
execution_feasibility_claim_allowed
live_trading_allowed
network_collection_allowed
paper_trading_allowed
push_allowed
replay_allowed
ssh_allowed
trade_signal_allowed
```

Every value must be boolean `false`. Missing is not false; extra keys are not permitted.

## 5. Data, Time and Statistical Contract

### 5.1 Allowed source fields

For each exact child, the sole metric source is:

```text
review_summary.quarantine.per_symbol_quarantine_metrics[event_symbol_id]
  .quarantined_depth_quality
```

The allowed fields are:

```text
spread_bps_p50
spread_bps_p95
buy_slippage_bps_500usdt_p50
buy_slippage_bps_500usdt_p95
sell_slippage_bps_500usdt_p50
sell_slippage_bps_500usdt_p95
top_bid_depth_usdt_p05
top_bid_depth_usdt_p50
top_ask_depth_usdt_p05
top_ask_depth_usdt_p50
healthy_window_ratio
depth_capacity_ratio_to_risk_cap_p50
```

The projection also preserves `event_symbol_id`, `symbol`, `event_id`, `source_article_id`, `valid_snapshot_count_after_quarantine`, `invalid_book_row_count`, and `book_availability_ratio` as provenance/context, without recomputing quality percentiles from raw rows.

### 5.2 Derived descriptive metric

For each child `s`, the only new arithmetic metric is:

```text
sum_of_marginal_p95_slippage_bps[s] =
  buy_slippage_bps_500usdt_p95[s] + sell_slippage_bps_500usdt_p95[s]
```

This is a sum of two marginal p95 values, not a percentile of a paired two-sided distribution. The buy and sell p95 observations need not have occurred in the same snapshot. It is not total trading cost, expected loss, fill estimate, capacity certification, or an executable threshold.

No configured cost floor is applied and no threshold comparison is emitted in V3. Existing Stage 1.5H blocker logic is not imported, because applying it would turn this diagnostic into an execution-feasibility classifier.

### 5.3 Independent sampling and aggregation

```text
child-symbol observations = 8
independent parent events = 2
```

Child rows are descriptive within-parent observations only. The parent summary for each metric is the unweighted arithmetic median over that parent's child values, with its `child_symbol_count` reported. The cohort summary consists only of the two parent summaries and reports:

```text
independent_parent_event_count = 2
parent_median_min
parent_median_max
```

No pooled child percentile, pooled child mean, p-value, confidence interval, win rate, expected value, ranking, pass/fail score, or generalization is allowed. With two parent events, `research_classification` is exactly `evidence_insufficient` for every economic/Alpha/execution interpretation.

### 5.4 Point-in-time and outcome boundary

Input is limited to the already captured Stage 1.5F snapshot-derived quality metrics associated with formal completed event-symbol identities. The diagnostic must not read any price series, later orderbook state, outcome or future artifact. It therefore has no forward-outcome statistic and cannot support or reject an economic mechanism.

## 6. Output and Persistent State Contract

### 6.1 Root grammar

```text
RUN_ID = ^stage1_5h_v3_cross_root_friction_[0-9]{8}T[0-9]{6}Z$
FINAL_ROOT = data/external_signal_shadow/stage1_5h/v3_cross_root_friction/<RUN_ID>/
STAGING_ROOT = data/external_signal_shadow/stage1_5h/v3_cross_root_friction/.<RUN_ID>.staging.<pid>/
```

`FINAL_ROOT` and `STAGING_ROOT` must be absent before work. Existing final, staging collision, symlink, non-directory parent, path escape or nonconforming `RUN_ID` is fatal. The writer may create only `STAGING_ROOT` and then atomically rename it to `FINAL_ROOT`; it must never modify an existing root.

### 6.2 Exact sealed files

The final root contains exactly:

```text
stage1_5h_v3_cross_root_friction_summary.json
stage1_5h_v3_cross_root_friction_review_CN.md
stage1_5h_v3_cross_root_friction_manifest.json
```

The JSON summary top-level key set is exactly:

```text
authority_flags
cohort_summary
decision
input_receipt_manifest_sha256
input_receipt_summary_sha256
input_source_roots
parent_rows
per_symbol_rows
research_classification
run_id
schema_version
stage1_5g_gate3_complete
```

Its fixed scalar values are:

```text
schema_version = 1
decision = stage1_5h_v3_cross_root_friction_diagnostic_generated
research_classification = evidence_insufficient
stage1_5g_gate3_complete = false
```

`input_source_roots` has exactly two rows, ordered by `input_key`, with exact keys:

```text
input_key
source_manifest_sha256
source_root_path
stored_summary_path
stored_summary_sha256
```

Persistent lineage equality is mandatory, not merely a type check:

```text
summary.input_receipt_manifest_sha256 == CROSS_ROOT_MANIFEST_SHA256
summary.input_receipt_summary_sha256  == CROSS_ROOT_SUMMARY_SHA256

manifest.input_receipt_manifest_sha256 == summary.input_receipt_manifest_sha256
                                      == CROSS_ROOT_MANIFEST_SHA256
manifest.input_receipt_summary_sha256  == summary.input_receipt_summary_sha256
                                      == CROSS_ROOT_SUMMARY_SHA256

summary.input_source_roots == receipt.input_records projected to
  (input_key, source_root_path, source_manifest_sha256,
   stored_summary_path, stored_summary_sha256)
```

The `input_source_roots` projection must contain exactly the two §4.2 rows in canonical `input_key` order. A valid-format but different hash, path, row, order or summary/manifest disagreement is a strict-loader failure.

`per_symbol_rows` has exactly eight rows in canonical `event_symbol_id` order. Each row has exactly:

```text
book_availability_ratio
buy_slippage_bps_500usdt_p50
buy_slippage_bps_500usdt_p95
depth_capacity_ratio_to_risk_cap_p50
event_id
event_symbol_id
healthy_window_ratio
input_key
invalid_book_row_count
sum_of_marginal_p95_slippage_bps
sell_slippage_bps_500usdt_p50
sell_slippage_bps_500usdt_p95
source_article_id
spread_bps_p50
spread_bps_p95
symbol
top_ask_depth_usdt_p05
top_ask_depth_usdt_p50
top_bid_depth_usdt_p05
top_bid_depth_usdt_p50
valid_snapshot_count_after_quarantine
```

`parent_rows` has exactly two rows ordered by `parent_event_id`. Each row has exactly `parent_article_id`, `parent_event_id`, `child_event_symbol_ids`, `child_symbol_count`, and `median_metrics`. `child_event_symbol_ids` is in canonical child `event_symbol_id` order. `median_metrics` and `parent_metric_ranges` have exactly these 13 metric keys:

```text
buy_slippage_bps_500usdt_p50
buy_slippage_bps_500usdt_p95
depth_capacity_ratio_to_risk_cap_p50
healthy_window_ratio
sum_of_marginal_p95_slippage_bps
sell_slippage_bps_500usdt_p50
sell_slippage_bps_500usdt_p95
spread_bps_p50
spread_bps_p95
top_ask_depth_usdt_p05
top_ask_depth_usdt_p50
top_bid_depth_usdt_p05
top_bid_depth_usdt_p50
```

`cohort_summary` has exactly `independent_parent_event_count`, `parent_event_ids`, and `parent_metric_ranges`. Its event count is integer `2`; IDs are the two ordered `parent_event_id` values. `parent_metric_ranges` contains exactly the same 13 metric keys as `median_metrics`, and each value has exactly `parent_median_min` and `parent_median_max`. It reports a range across two parent medians, never a cohort mean, percentile or test statistic.

### 6.3 Exact human review projection

The Markdown review is a sealed human projection, not free-form commentary. The renderer may emit only the following literal template, with the five `<canonical_json(...)>` placeholders replaced by `canonical_json_dumps` output and no added/omitted line, row, heading or paragraph:

````text
# Stage 1.5H V3 Cross-Root Liquidity Friction Diagnostic Review

## Scope

- `run_id`: `<run_id>`
- `decision`: `stage1_5h_v3_cross_root_friction_diagnostic_generated`
- `research_classification`: `evidence_insufficient`
- `stage1_5g_gate3_complete`: `false`
- 本报告仅为冻结 L2 quality metrics 的描述性投影；不构成 phenomenon、Alpha、strategy 或 execution-feasibility evidence。

## Authority Flags

```json
<canonical_json(authority_flags)>
```

## Input Lineage

```json
<canonical_json(input_lineage)>
```

## Per-Symbol Rows

```json
<canonical_json(per_symbol_rows)>
```

## Parent Rows

```json
<canonical_json(parent_rows)>
```

## Cohort Summary

```json
<canonical_json(cohort_summary)>
```
````

Here `input_lineage` is exactly the object with keys `input_receipt_manifest_sha256`, `input_receipt_summary_sha256`, and `input_source_roots`, populated from those same summary fields and no others. `<run_id>` is the raw validated `run_id` string; all other dynamic values use their exact canonical JSON bytes. The renderer appends exactly one final `\n`. The V3 strict loader reconstructs this template independently from strict-loaded summary bytes and requires byte-for-byte equality. It rejects any additional prose, including a claim that execution is feasible.

### 6.4 Types, canonical bytes and deterministic arithmetic

Before serialization, V3 validates every value. It then serializes summary and manifest exclusively with the frozen `canonical_json_dumps(payload).encode("utf-8")` from §4.1. JSON parsed bytes must canonicalize back to the identical bytes; missing/extra keys, whitespace-only hashes, non-canonical bytes, `NaN`, `Infinity` and `-Infinity` reject.

```text
run_id                 = valid §6.1 string
event_symbol_id        = lowercase 64-character hexadecimal string
parent_event_id        = lowercase 64-character hexadecimal string
parent_article_id      = lowercase 32-character hexadecimal string
source_article_id      = lowercase 32-character hexadecimal string
input_key              = moonshot | batch7
paths                  = exact §4.2 relative strings; no absolute, .. or symlink resolution
sha256                 = lowercase 64-character hexadecimal string
counts                 = non-negative integer; bool is not an integer
metric/range values    = finite JSON number; bool is not a number
authority values       = boolean false only
```

The parent median uses `statistics.median` over exactly that parent's receipt-member child metric values. The cohort range uses `min` and `max` over exactly the two finite parent medians. Any type, membership, finite-number or ordering failure rejects before writing.

### 6.5 Manifest-last publication and recovery

Writer sequence:

```text
validate authority and both roots
-> derive summary/review entirely in memory
-> write and fsync summary
-> write and fsync deterministic review
-> write, fsync and validate manifest
-> strict-load staging root
-> fsync STAGING_ROOT directory
-> atomic os.replace(STAGING_ROOT, FINAL_ROOT)
-> fsync FINAL_ROOT parent directory
-> strict-load FINAL_ROOT
```

The manifest key set is exactly `artifacts`, `input_receipt_manifest_sha256`, `input_receipt_summary_sha256`, `run_id`, and `schema_version`. `artifacts` has exactly `review` and `summary`; each artifact metadata object has exactly `byte_count`, `relative_path`, and `sha256`. Its receipt SHA fields must satisfy the §6.2 persistent-lineage equality before any artifact hash is trusted. The manifest is written last. A final root is authoritative only if the V3 strict loader passes.

Canonical physical states are:

```text
unpublished          = final root absent; staging absent
staging_only         = matching staging root exists; final root absent
receipt_published    = final root exists and V3 strict loader passes
corrupt_or_unknown   = any other final/staging condition or strict-load failure
```

`staging_only` and `corrupt_or_unknown` are never consumable and are never resumed, deleted or overwritten by this Design. A rerun uses a new `RUN_ID`. If `os.replace()` succeeds but parent-directory `fsync` fails, the process returns non-zero `STOP=stage1_5h_v3_post_rename_durability_failure`, never reports generated, and never deletes or overwrites `FINAL_ROOT`. Restart classification is determined solely by final bytes using the state table above.

## 7. Reducer and Failure Semantics

The reducer has only two outcomes:

```text
all authority, receipt, source-root, membership, schema, false-vector,
projection, path and persistence checks pass
  -> stage1_5h_v3_cross_root_friction_diagnostic_generated

otherwise
  -> STOP=stage1_5h_v3_cross_root_authority_mismatch
     or a more specific fail-closed STOP code
```

There is no partial `generated_with_warnings`, no fallback to receipt self-report, no `.get(..., default)` for required contract fields, and no path supplied by ambient environment variable.

`stage1_5g_gate3_complete=false` is accepted exactly as false; `true`, missing, non-bool or any attempt to promote it is a contract mismatch.

## 8. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| `INV-H3-01` | Exact §4.1 TCB bytes and imported module origins validate before any receipt/source import or read. |
| `INV-H3-02` | Receipt identity/count authority is checked only against receipt identity fields; quality is independently re-admitted under §4.2; every sealed output lineage field equals the exact §4.1/§4.2 authority. |
| `INV-H3-03` | Exactly 8 child rows map bijectively to exactly 2 parent rows; child symbols never count as independent events. |
| `INV-H3-04` | Frozen upstream Stage 1.5G loader/reducer alone may open frozen source artifacts for re-admission; V3 owns no raw-row reader and consumes only equality-validated quality projections. |
| `INV-H3-05` | `sum_of_marginal_p95_slippage_bps` is exactly buy p95 plus sell p95 and is never represented as paired round-trip p95, cost, PnL, threshold or pass/fail classification. |
| `INV-H3-06` | Every economic, Alpha and execution interpretation is `evidence_insufficient`; output cannot emit phenomenon, strategy or feasibility status. |
| `INV-H3-07` | Output false-vector key set exactly equals §4.4 and all values are boolean false. |
| `INV-H3-08` | Canonical JSON/type validation, exact human-template projection, manifest-last sealing, both directory fsyncs and four-state restart classification prevent a partial, non-durable or semantically promoted root from being consumable. |
| `INV-H3-09` | `stage1_5g_gate3_complete` stays false; V3 neither verifies nor changes current Stage 1.5D/1.5F runtime state. |
| `INV-H3-10` | No network, replay, exchange API, paper/live trading, execution, commit, push, deployment or SSH path is reachable. |

## 9. Contract Impact Matrix

| Role | Owner / artifact | Allowed effect | Forbidden effect |
| --- | --- | --- | --- |
| Producer | New V3 local diagnostic module and CLI | Read exact locally sealed evidence and write one sealed local output | Network, VPS, API, order, direct raw-row reader or outcome access |
| Upstream loader | Frozen `load_verified_cross_root_receipt`, `load_stage1_5g_inputs` and `build_stage1_5g_review_summary` | Strictly verify receipt identity and independently re-admit both source roots | Trust receipt/self-reported quality without revalidation |
| Writer | V3 manifest-last writer | Fresh root only, deterministic summary/review/manifest | Append, overwrite, partial publication |
| Consumer | N/A under this Design | Human read-only review of sealed V3 output | Existing Stage 1.5H, strategy, simulator, replay or execution consumption |
| Reviewer | Future independent Completion Audit | Recompute projection from strict-loaded upstream bytes | Treat test fixtures or executor report as proof |

## 10. Validation Strategy

Future Plan must bind every invariant to a real implementation owner, canonical upstream positive fixture, one declared negative mutation, test and final gate.

Mandatory cases:

1. Canonical positive fixture must strict-load the real frozen receipt and re-admit real frozen root bytes through the frozen production loader/reducer, not a hand-written dict.
2. Mutate only one receipt identity field (summary SHA or child identity), then require failure before quality projection use.
3. Mutate one manifest artifact hash/length, then require strict receipt-load failure.
4. Quality-comparator negative: strict-load the real receipt and fully re-admit both real roots; mutate exactly one field only in the admitted in-memory stored-quality projection; directly invoke the quality comparator and require `STOP=stage1_5h_v3_quality_projection_mismatch`. Do not mutate frozen stored-summary bytes, because that would correctly stop earlier at the stored-summary SHA authority gate.
5. Duplicate, omit or move one child between parent ledgers, then require bijection failure.
6. Arithmetic unit: mutate exactly one admitted in-memory buy/sell p95 input and assert `sum_of_marginal_p95_slippage_bps` changes by exactly that delta. Integration reducer: use the same single admitted in-memory mutation and assert all legitimately dependent per-symbol, parent median and cohort range fields recompute deterministically; assert no configured cost floor, threshold, paired-P95 label or feasibility status appears.
7. Use AST/import/open spies to prove V3-owned code has no raw JSONL glob/open, price/outcome, network or exchange-client access, while proving the frozen upstream loader is the sole production caller allowed to open frozen source rows.
8. Test invalid `RUN_ID`, final/staging collision, symlink traversal, crash before manifest, crash after manifest, crash after staging-directory fsync, and post-rename parent-fsync failure. Assert the four canonical states and final-root strict reload behavior.
9. Append the deterministic but unauthorized prose `execution looks feasible` to an otherwise valid review and require byte-for-byte template rejection. Also assert exact key sets, ordering, finite metric types, non-negative integer counts, canonical JSON byte equality, persistent-lineage equality, false-vector key equality and false values.
10. Independently run `.agent/tools/anti_shortcut_scan.py` and record its actual process exit code; a zero exit code is necessary but not sufficient.

## 11. L2 Research Classification

### Mechanism hypothesis

This Design has no market-mechanism or economic-edge hypothesis. It asks only what static L2 quality metrics were recorded in two frozen parent events.

### Cost and capacity boundary

`sum_of_marginal_p95_slippage_bps` is a descriptive sum of marginal quantiles, not a joint round-trip percentile. It does not include fees, fill uncertainty, queue position, latency, adverse selection, price movement, funding, basis, holding risk or margin. It therefore cannot establish Gate D economic/executable edge.

### Promotion / kill / evidence-gap semantics

```text
valid sealed diagnostic -> descriptive artifact generated
invalid input/persistence/authority -> evidence_gap / STOP
all Alpha, execution and strategy propositions -> evidence_insufficient
```

No result of this Design promotes, kills or reopens a strategy. A later economic or simulator Design would need independently approved hypotheses, PIT outcome data, parent-aware sample rules, cost model, loss/tail analysis and separate authority.

## 12. Compatibility, Rollback and Open Questions

- Existing Stage 1.5G receipt, Stage 1.5H/V2 code and Stage 1.5D/1.5F runtime are No-Touch.
- V3 writes a new root only. Rollback is deleting an unconsumed V3 root under a separately authorized maintenance operation; this Design itself does not delete anything.
- Graphify is unavailable in the current virtual environment (`No module named graphify`); source and test topology were verified using direct source inspection and `rg`. Future implementation may use Graphify only if its current graph/tooling is independently verified.

There are no blocking open questions for this Design: the exact frozen receipt, roots, sample hierarchy, allowed metrics and authority boundary are already fixed. Whether a later consumer needs current runtime proof is explicitly deferred and cannot be inferred from V3.

## 13. Design Self-Review

- No placeholders, thresholds or implementation-only magic numbers were introduced.
- `stage1_5g_gate3_complete=false` is preserved rather than treated as a defect.
- The 8 child symbols are never promoted to 8 independent events.
- The Design adds one bounded local consumer, no registry, callback, plugin, generic root-union framework or execution abstraction.
- Implementation remains prohibited until independent Design review and explicit user approval.
