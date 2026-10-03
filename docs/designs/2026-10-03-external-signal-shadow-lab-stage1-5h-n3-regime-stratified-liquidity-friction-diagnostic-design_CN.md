# Stage 1.5H N=3 产品机制分层流动性摩擦诊断 Design

## 1. 已确认事实

1. 已 sealed 的 N=3 准入 receipt 位于 `data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z/`；其三个 authoritative artifacts 的 SHA-256 分别为：

   ```text
   stage1_5g_n3_regime_stratified_admission_manifest.json = f3b4c76683fe7e1e4a7f28f30437f289f036f6ffc6126f8e9693faad62789adf
   stage1_5g_n3_regime_stratified_admission_summary.json  = c92686b4834ee41165850aba99b1b68254b05a4afaf37d5e2789747db60ca941
   stage1_5g_n3_regime_stratified_admission_review_CN.md  = df6e12df8b1d105c62dd8cb01baeb0f858aa008c42488f699999a3b9ba51f2dc
   ```

   receipt 的唯一可接受状态是 `decision=stage1_5g_n3_regime_stratified_admission_pass`、`3` 个 source article、`3` 个 independent parent event、`9` 个 formal child symbol，且 `stage1_5g_gate3_complete=false`。
2. N=3 receipt 的 parent ledger 已按三种机制冻结：

   | `product_regime_id` | parent article | parent event | child symbols |
   | --- | --- | --- | --- |
   | `pre_ipo_equity_perpetual` | `7379b99aa0f349a49c3b3feca1b4bbd6` | `e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5` | `MOONSHOTUSDT` |
   | `tradfi_equity_or_etf_perpetual_batch` | `0c6ea14ba89b451db6ec9ec364045d22` | `d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0` | `CRMLUSDT`, `BWETUSDT`, `ACNUSDT`, `MPUSDT`, `SECZUSDT`, `UNHUSDT`, `NKEUSDT` |
   | `crypto_standard_perpetual` | `6bd26adeb6f742fe88eb72faca183566` | `374345c5e4527ca0f061155796909acb385fbd084172f175bd8accb00cdbd963` | `CTUSDT` |

   一个 parent 下的 child symbol 不是独立事件。每个 regime 在此 receipt 中恰有一个 parent，不能形成 regime 内分布或推断样本。
3. 已冻结的旧 Stage 1.5H V3 仅绑定旧 N=2 receipt、两个 parent、八个 child；其 source、CLI、tests 和 historical artifacts 是本次 No-Touch，不能被原地扩展或重解释为 N=3。
4. 旧 H V3 已定义的静态 quality metric 命名、类型和 `sum_of_marginal_p95_slippage_bps` 的算术含义可原样复用；但其两-parent `parent_metric_ranges` 与任何 N=2 cohort projection 不可复用。
5. 本地 N=3 producer 已冻结的 upstream contract bytes 为：

   | Path | SHA-256 |
   | --- | --- |
   | `src/research/external_signal_shadow/stage1_5g_n3_regime_stratified_admission.py` | `e64abe50b97d5cea303552c59f8f8f98168297ab0cabadfb554de9c1340c0c3d` |
   | `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py` | `596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d` |
   | `src/research/external_signal_shadow/safety.py` | `1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d` |
   | `configs/base.py` | `414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4` |

6. `configs/base.py` 保持 `RISK_LIVE_TRADING_ENABLED=False`。N=3 receipt 的十三个 authority flags 均为 boolean `false`，其中包括 `alpha_interpretation_allowed`、`execution_feasibility_claim_allowed`、`replay_allowed`、`paper_trading_allowed` 与 `live_trading_allowed`。
7. 当前虚拟环境没有可用的 Graphify module（`No module named graphify`）。本 Design 的拓扑依据为真实 source、tests 和定向 `rg`；不得为了本 Design 更新或生成 `graphify-out/`。

## 2. 核心问题、方案比较与决策

### 2.1 核心问题

N=3 receipt 已证明三个历史 parent 的 local structural admission 和机制隔离，但没有一个被授权的 consumer 将九个 member 的已捕获静态 L2 quality metrics 做成同样隔离的只读诊断。直接修改旧 H V3 会改变已冻结 N=2 input identity 和统计 contract；将九个 child 或三个 parent 跨机制池化，又会把不相同的标记价格、参考市场与 underlying 语义伪装成共同的流动性样本。

### 2.2 方案比较

| 方案 | 结论 | 理由 |
| --- | --- | --- |
| 修改旧 H V3 为 N=3 | 拒绝 | V3 的 N=2 receipt identity、两-parent range 和历史 sealed output 已冻结。 |
| 构建可扩展多-regime analytics framework | 拒绝 | 当前只有三个明确 parent；泛化 registry、plugin 或 future consumer callback 没有已批准需求。 |
| 新增固定 N=3、分层的只读 diagnostic | 采用 | 最小新增 consumer，精确绑定现有 receipt/roots/metrics，输出可审计描述性投影但不做跨机制结论。 |

### 2.3 决定

新增独立的 **Stage 1.5H N=3 Regime-Stratified Liquidity Friction Diagnostic**。它严格验证 N=3 receipt，再通过冻结的 Stage 1.5G production loader/reducer 重验三条 source root，仅投影已验证的静态 depth-quality metrics。

输出可逐 symbol 展示九条 metric row，并按 receipt 既有 `product_regime_id` 和 parent lineage 分区。唯一允许的 parent summary 是**该 parent 自身 child rows 的未加权中位数**，且必须带 `child_symbol_count`。不得生成跨 regime cohort row、regime distribution、cross-regime range、共同 cost floor、门槛、ranking、pass/fail 或 execution conclusion。

## 3. 范围与显式非目标

### 3.1 In scope

- 创建一个新的 H N=3 core module、CLI、测试与独立 output namespace；
- strict-load §4 的 exact N=3 receipt，保持其 `stage1_5g_gate3_complete=false`；
- 重验三条 frozen source root 并与 receipt identity、parent ledger、product-regime ledger 和 per-symbol quality projection 做逐字段一致性检查；
- 为 receipt 的九个 children 写入 deterministic JSON summary、完全由 summary 渲染的 Markdown review，以及 manifest；
- 分层展示 per-symbol rows 与 three parent-local median rows。

### 3.2 Explicit non-goals

- 不修改旧 N=2 Stage 1.5G、旧 H V3、其 source/CLI/tests、historical outputs 或统计含义；
- 不读取 raw depth JSONL、价格序列、后续盘口、forward outcome、成交、订单、P/L、funding、手续费、保证金或仓位；
- 不形成跨 mechanism/regime 的 pooled metric、共同市场结论、cost floor、容量阈值、执行可行性或交易候选结论；
- 不做 replay、backtest、仿真、fill/queue/latency model、strategy、entry/exit/holding/sizing/risk-veto；
- 不访问网络、BAPI、authenticated/private/order API、VPS、SSH 或 exchange state；
- 不将 `stage1_5g_gate3_complete` 改为 `true`，不验证当前 Stage 1.5D/1.5F 运行状态；
- 不为第四 parent、未知 regime 或未来 consumer 提供 discovery、fallback、registry、callback 或配置扩展点。

## 4. Authority、输入与拓扑契约

### 4.1 Frozen authority packet

```text
APPROVED_DESIGN_PATH   = this exact Design after independent review and explicit user approval
APPROVED_PLAN_PATH     = future approved Plan only
N3_RECEIPT_ROOT        = data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z
N3_MANIFEST_SHA256     = f3b4c76683fe7e1e4a7f28f30437f289f036f6ffc6126f8e9693faad62789adf
N3_SUMMARY_SHA256      = c92686b4834ee41165850aba99b1b68254b05a4afaf37d5e2789747db60ca941
N3_REVIEW_SHA256       = df6e12df8b1d105c62dd8cb01baeb0f858aa008c42488f699999a3b9ba51f2dc
```

Before importing or reading a source root, the new H module must hash and require the exact four §1.5 module/config bytes. For each of these runtime modules it must, both before and after import, verify expected project-contained path, `__file__`, `__spec__.origin`, resolved path and current file SHA-256:

```text
src.research.external_signal_shadow.stage1_5g_n3_regime_stratified_admission
src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review
src.research.external_signal_shadow.safety
configs.base
```

A preloaded, shadowed, missing or post-import-drifted module is fatal. `configs.base` is an imported runtime dependency of the production Stage 1.5G reducer, not merely a disk file whose SHA may be checked without validating its import identity.

The N=3 loader call is `load_verified_n3_receipt(N3_RECEIPT_ROOT)` with its default local validation behavior. The new diagnostic must never request `future_consumer_allowed=True`, must not alter N=3 loader source, and must itself independently bind the exact receipt hashes above. This Design is the only proposed consumer authorization; it creates no reusable future-consumer mechanism.

### 4.2 Separate local receipt-generation authority

Implementation authority is not local receipt-generation authority. The public CLI and public `run_diagnostic()` must call both the ordinary approved Design/Plan execution-authority validator and the following generation validator **before importing a source module, reading a source root, creating a staging directory, or invoking a writer**. Missing or invalid generation authority must return exactly:

```text
STOP=local_receipt_generation_not_authorized
```

The only accepted locator is derived from the project root and the compiled approved Plan SHA; neither CLI arguments nor environment variables may select it:

```text
.git/plan-execution/stage1_5h_n3_regime/<APPROVED_PLAN_SHA256>/
  receipt_generation_authorization.txt
  receipt_generation_authorization.sha256
```

Both files and every locator ancestor must be regular, project-contained, non-symlink filesystem objects. The sidecar must have exactly these ASCII bytes, where `<AUTH_SHA256>` is the SHA-256 of the authorization text bytes:

```text
<AUTH_SHA256>  receipt_generation_authorization.txt\n
```

The authorization text must be UTF-8 and have exactly these five lines plus one final LF, with no leading/trailing/extra whitespace. `<AUTHORIZED_RUN_ID>` must satisfy §5.5 grammar; `<APPROVED_H_CORE_SHA256>` and `<APPROVED_H_CLI_SHA256>` are the exact post-Code-Review and fresh-Completion-Audit SHA-256 values for the two future output paths named below:

```text
我批准本地生成 Stage 1.5H N=3 diagnostic receipt：<APPROVED_PLAN_REL_PATH>（SHA-256: <APPROVED_PLAN_SHA256>）。
RUN_ID: <AUTHORIZED_RUN_ID>
H_CORE_SHA256: <APPROVED_H_CORE_SHA256>
H_CLI_SHA256: <APPROVED_H_CLI_SHA256>
允许仅本地生成 Stage 1.5H N=3 diagnostic receipt；不允许 commit、push、deployment、SSH、network、replay、execution、paper 或 live action。
```

The bound paths are exactly:

```text
src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
scripts/external_signal_shadow/run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
```

The validator must independently verify text SHA, sidecar bytes, exact five-line grammar, Plan path/SHA equality, `run_id == AUTHORIZED_RUN_ID`, both current code bytes, and the Plan/Design binding already captured by execution authority. The public CLI may accept a `RUN_ID` argument only when it exactly equals `AUTHORIZED_RUN_ID`; it must not generate, default, discover or substitute one. A capability can publish at most this one final root. Any distinct `RUN_ID` requires a new user-signed authorization with a distinct `AUTHORIZED_RUN_ID` and fresh audited code hashes; same-root crash/restart behavior remains exclusively subject to §5.5 no-resume state rules. Unit-level pure reducers may be tested in a temporary directory, but no public writer or CLI route may bypass this gate.

### 4.3 Exact source-root re-admission

The new H module must use the verified Stage 1.5G module's `load_stage1_5g_inputs()` and `build_stage1_5g_review_summary()` for exactly these input records, in this canonical order:

| input key | source root | source `SHA256SUMS` SHA-256 | stored Stage 1.5G summary / SHA-256 |
| --- | --- | --- | --- |
| `moonshot` | `data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot` | `611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db` | `data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json` / `849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082` |
| `batch7` | `data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7` | `0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280` | `data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json` / `28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37` |
| `ct_projection` | `data/external_signal_shadow/local_evidence/20261001T074500Z_stage1_5f_ctusdt` | `f69efe25ea2efd03054372c41f882e2deb10e9842b890d71f60c19ce9b44f7db` | `data/external_signal_shadow/stage1_5g/reviews/20261002T010000Z_ctusdt_review/stage1_5g_live_depth_evidence_review_summary.json` / `9f6a1e9797dbc42af3ce103ed231689adb0422ef1ab23768ca398eb8ec153c1c` |

For each input, H must build two explicit, independent comparators. It must not compare the whole Stage 1.5G summary, and in particular must not compare presentation/provenance-only `stage1_5f_output_root`, whose absolute-vs-relative representation is not a stable source-evidence claim.

**Identity projection.** Stored summary, recomputed summary and N=3 receipt must agree on the exact projection below. The three path/SHA fields originate in the exact §4.3 record; the remaining values originate from the frozen summaries and receipt.

```text
input_key
stored_summary_path
stored_summary_sha256
source_root_path
source_manifest_sha256
schema_version = 2
decision = stage1_5g_depth_evidence_clean_pass
clean_depth_evidence_pass = true
quarantined_depth_evidence_pass = false
blockers = []
source_evidence_manifest_sha256
formal_completed_event_symbol_ids_sha256
formal_children[] ordered by event_symbol_id, each with exactly:
  event_symbol_id
  event_id
  symbol
  source_article_id
  evidence_label
  state_status
  formal_completed
```

Every projected key, type, value and child ordering must match exactly. The N=3 receipt's `input_records` and `parent_ledger` must also match their appropriate identity fields. For `ct_projection`, all eight children must pass this comparator; only exact `CTUSDT` may be emitted, and each of the other seven child identities must exactly match the independently admitted Batch 7 child with the same `event_symbol_id`.

**Quality projection.** For exactly the nine emitted children, H extracts the fifteen §4.4 fields from the stored Stage 1.5G summary and recomputed Stage 1.5G summary. The extracted projection must have exactly twelve `quarantined_depth_quality` keys plus exactly three parent-object context keys; every key, type and value must be equal. No `.get`, float coercion, tolerance, default, partial comparison or alternate source is permitted.

Only after both comparators pass may H use the recomputed values for output. Any direct raw-row reader, glob, handcrafted summary/metric dict, root discovery, omitted child, or fallback is forbidden.

### 4.4 Sole allowed metric projection

For each exact receipt-member `event_symbol_id`, `per_symbol_quarantine_metrics[event_symbol_id]` is the authoritative parent object. It has two non-interchangeable projections:

```text
recomputed_review_summary
  .quarantine.per_symbol_quarantine_metrics[event_symbol_id]
  .quarantined_depth_quality.<quality field>
```

The following twelve quality fields are copied only from `quarantined_depth_quality`, never recomputed from raw rows:

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
depth_capacity_ratio_to_risk_cap_p50
healthy_window_ratio
```

The following three context fields are copied only from the parent object, never from `quarantined_depth_quality` and never from a fallback/default:

```text
recomputed_review_summary
  .quarantine.per_symbol_quarantine_metrics[event_symbol_id]
  .valid_snapshot_count_after_quarantine
  .invalid_book_row_count
  .book_availability_ratio
```

```text
valid_snapshot_count_after_quarantine
invalid_book_row_count
book_availability_ratio
```

Each copied field must be present in both the stored and recomputed quality projections, have the exact §5.2 type, and be exact-equal. The output additionally derives exactly one arithmetic field:

```text
sum_of_marginal_p95_slippage_bps
= buy_slippage_bps_500usdt_p95 + sell_slippage_bps_500usdt_p95
```

It is only a sum of two marginal static percentiles. It is not a paired round-trip percentile, fill estimate, all-in transaction cost, fee-inclusive cost, P/L, threshold, score or execution-feasibility claim.

### 4.5 Trust boundary and TCB

**Protected.** The Design protects against accidental or unprivileged local byte/config drift, preloaded module shadowing, static path/symlink escape, wrong receipt/source identity, authority substitution, stale/partial/collision publication, and concurrent invocations that honor the defined output-directory lock.

**Trusted computing base.** CPython, `hashlib`, `json`, `statistics`, `pathlib`, `os`, `fcntl.flock`, local filesystem completed-syscall/rename/`fsync` semantics, the checked project root, and a non-malicious privileged local operator are trusted. The new H module itself verifies origin and hash, both before and after import, for N=3, Stage 1.5G review, `safety.py` and imported runtime module `configs.base`. It does not delegate those checks to the N=3 loader.

**Out of scope.** A compromised kernel/interpreter/filesystem, a malicious privileged actor that coherently rewrites code and evidence after checks, a SHA-256 collision, and non-cooperating processes that ignore the advisory `flock` are outside this Design. The Design must not claim that a `lstat`/`resolve` sequence prevents those adversaries' post-check path swaps. The lock only serializes cooperating local writers; strict reload and the state machine still prevent their stale/partial roots from becoming success states.

### 4.6 Producer / writer / loader / consumer / reviewer matrix

| Role | Owner/artifact | Must do | Must not do |
| --- | --- | --- | --- |
| Receipt producer/loader | Frozen N=3 module | Validate N=3 receipt structure and local integrity | Grant generic future-consumer authority |
| Source re-admission producer | Frozen Stage 1.5G review module | Validate frozen root and derive quality projection | Expose a new H raw-row API |
| New H reducer | New H N=3 core | Match receipt to independent source projections and build partitioned descriptive rows | Infer labels, substitute values or pool regimes |
| New H writer/loader | New H N=3 core | Validate exact schema, canonical bytes, lineage, manifest and state | Tolerate missing fields, symlinks, partial state or legacy roots |
| Consumer | No downstream consumer in this Design | N/A | Treat generated diagnostic as Alpha, cost floor or execution permission |
| Reviewer | Design/Plan/Completion Audit | Independently invoke real loaders and compare artifacts | Trust Markdown or producer self-report alone |

## 5. Data, state and output contract

### 5.1 Canonical membership and partitioning

`per_symbol_rows` contains exactly nine rows, sorted by `(product_regime_id, parent_event_id, event_symbol_id)`. Each row must contain exactly:

```text
event_symbol_id
symbol
parent_article_id
parent_event_id
product_regime_id
source_anchor_contract_hash
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
depth_capacity_ratio_to_risk_cap_p50
healthy_window_ratio
valid_snapshot_count_after_quarantine
invalid_book_row_count
book_availability_ratio
sum_of_marginal_p95_slippage_bps
```

`parent_rows` contains exactly three rows, sorted by `parent_event_id`. Every row has exactly:

```text
product_regime_id
parent_article_id
parent_event_id
child_event_symbol_ids
child_symbol_count
median_metrics
```

`median_metrics` contains exactly the twelve static quality fields plus `sum_of_marginal_p95_slippage_bps`; it is the unweighted `statistics.median` over exactly that row's children. The one-child MOONSHOT and CT rows therefore equal their individual child values. Batch 7's row is a within-parent seven-child description, not seven independent event observations.

There is intentionally no `cohort_summary`, `regime_summary`, `parent_metric_ranges`, pooled metric, rank, winner, common baseline or comparison verdict. A valid implementation must reject any extra output key that creates one.

Every `per_symbol_rows` row's `source_anchor_contract_hash` must equal both the matching re-admitted canonical accepted-event child's hash and the matching N=3 receipt parent `product_regime_ledger.source_anchor_contract_hashes` item in that parent's canonical `child_event_symbol_ids` order. Writer-selected, parent-only, set-based or unmatched hashes are fatal.

### 5.2 Summary schema and immutable claims

The JSON summary has exactly these top-level keys:

```text
authority_flags
decision
input_receipt
input_source_roots
independent_parent_event_count
parent_rows
per_symbol_rows
research_classification
run_id
schema_version
stage1_5g_gate3_complete
```

Required scalar values:

```text
schema_version                  = 1
decision                        = stage1_5h_n3_regime_stratified_friction_diagnostic_generated
research_classification         = evidence_insufficient
independent_parent_event_count  = 3
stage1_5g_gate3_complete        = false
```

`input_receipt` has exactly these keys and literal values:

```text
manifest_sha256      = f3b4c76683fe7e1e4a7f28f30437f289f036f6ffc6126f8e9693faad62789adf
review_sha256        = df6e12df8b1d105c62dd8cb01baeb0f858aa008c42488f699999a3b9ba51f2dc
root_relative_path   = data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z
run_id               = stage1_5g_n3_regime_stratified_admission_20261002T110403Z
summary_sha256       = c92686b4834ee41165850aba99b1b68254b05a4afaf37d5e2789747db60ca941
```

`input_source_roots` is a three-element list in §4.3 order. Every row has exactly `input_key`, `source_root_path`, `source_manifest_sha256`, `stored_summary_path`, and `stored_summary_sha256`; every value must equal its §4.3 literal. `authority_flags` has exactly the N=3 thirteen-key vector and every value is boolean `false`; missing, extra, truthy or non-bool value is fatal.

Type grammar is exact:

```text
run_id                          = Stage 1.5H RUN_ID grammar below
parent_article_id               = lowercase [0-9a-f]{32}
event_symbol_id/event_id/hash   = lowercase [0-9a-f]{64}
SHA-256                         = lowercase [0-9a-f]{64}
symbol                          = exact receipt-member symbol for its event_symbol_id; no free string or normalization
product_regime_id               = exactly one of the three §1 frozen literals and equal to its receipt parent
path                            = exact declared project-relative literal; no absolute path, dot component or separator normalization
count                           = type(x) is int and x >= 0
ratio                           = finite non-bool JSON number in [0, 1]
quality/median/derived metric   = finite non-bool JSON number
authority flag                  = type(x) is bool and x is False
```

`valid_snapshot_count_after_quarantine` and `invalid_book_row_count` are counts; `book_availability_ratio` and `healthy_window_ratio` are ratios. All other quality, median and derived values use the metric grammar. `child_symbol_count` is the exact length of a duplicate-free `child_event_symbol_ids` list and must equal the corresponding receipt parent membership.

### 5.3 Exact manifest schema

Manifest has exactly these top-level keys:

```text
artifacts
input_receipt_manifest_sha256
input_receipt_review_sha256
input_receipt_summary_sha256
run_id
schema_version
```

Required literal values are `schema_version=1`, the summary's `run_id`, and the three exact N=3 receipt artifact hashes from §4.1. `artifacts` has exactly these keys:

```text
stage1_5h_n3_regime_stratified_friction_review_CN.md
stage1_5h_n3_regime_stratified_friction_summary.json
```

Each artifact entry has exactly `relative_path`, `byte_count`, and `sha256`; `relative_path` equals its artifact key, `byte_count` is a positive non-bool integer equal to actual bytes, and `sha256` is the actual lowercase SHA-256. The strict loader compares all manifest lineage fields to summary `input_receipt`, does not accept a producer-defined alternate lineage layout, and rejects any extra key or file.

### 5.4 Exact Markdown projection

The Markdown artifact is a deterministic rendering of the validated summary, with no free-form facts. It has exactly these UTF-8 lines, including the terminal LF. `<CANONICAL_SUMMARY_JSON>` is the UTF-8 decode of `canonical_json_dumps(summary)` and no pretty-printer, sorting pass or secondary serializer is permitted:

````text
# Stage 1.5H N=3 Regime-Stratified Liquidity Friction Diagnostic Receipt

本报告仅描述三个冻结 parent event 的静态 L2 quality metrics；不同 product regime 不作池化、比较、成本地板、执行可行性、Alpha 或交易结论。

## Canonical Summary

```json
<CANONICAL_SUMMARY_JSON>
```
````

`render_review(summary)` must reproduce the stored Markdown byte-for-byte. Any changed literal, unrendered prose, alternate ordering, output metric, cross-regime language, code-fence variation or changed terminal LF rejects strict loading.

### 5.5 Run grammar, publication and recovery

```text
RUN_ID       = ^stage1_5h_n3_regime_stratified_friction_[0-9]{8}T[0-9]{6}Z$
FINAL_ROOT   = data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/<RUN_ID>/
STAGING_ROOT = data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/.<RUN_ID>.staging.<pid>/
```

Final root has exactly:

```text
stage1_5h_n3_regime_stratified_friction_summary.json
stage1_5h_n3_regime_stratified_friction_review_CN.md
stage1_5h_n3_regime_stratified_friction_manifest.json
```

Manifest is written last and lists only summary/review with exact relative path, non-bool positive integer byte count and lowercase SHA-256. All JSON uses frozen `canonical_json_dumps(...).encode("utf-8")`; parsed JSON must canonicalize to identical bytes. `NaN`, infinities, bool-as-number, non-finite metric, noncanonical bytes, unexpected file/key or weak type is fatal.

Before every `resolve()`, writer, classifier and loaders reject final/staging paths, artifacts and every ancestor symlink; after resolve every path must remain inside its declared project namespace. State classification is exactly:

| Pre-write state | Required action |
| --- | --- |
| final absent; no matching staging sibling | A fresh attempt may create one staging root. |
| final absent; one or more matching staging siblings | `staging_only`; STOP, no resume/delete/overwrite/reuse. |
| final present; no matching staging sibling | Strict valid tree is `receipt_published`; invalid tree is `corrupt_or_unknown`; neither is overwritten. |
| final present; one or more matching staging siblings | `corrupt_or_unknown`; STOP, no consumption or mutation. |

The writer opens the project-contained output-parent directory and holds one `fcntl.flock(LOCK_EX)` on its directory file descriptor from the first classification until final strict-load succeeds or the invocation fails. It must create the parent, open the descriptor and acquire this lock before first state classification. Under that same lock it must classify every matching staging sibling, require `unpublished`, and create only its own staging root.

Write sequence under the same lock: fully validate both authorities and all data in memory; write+flush+file-`fsync` summary; write+flush+file-`fsync` review; write+flush+file-`fsync` manifest last; strict-load staging; `fsync` staging directory; reclassify all matching siblings; require final absent, exactly the writer's own staging root and zero foreign staging roots; atomically rename to an absent final root; `fsync` final parent; reclassify and require `receipt_published` with zero matching staging roots; strict-load final root; only then return success and release the lock.

A failure before rename leaves only `staging_only`; a failure after rename but before parent `fsync` is non-zero `POST_RENAME_DURABILITY_FAILURE`. Neither path has resume, cleanup or overwrite authority. A second cooperating writer with the same `RUN_ID` blocks on the lock, then observes non-`unpublished` state and stops; it must never return success.

## 6. Fail-closed reducer sequence

```text
verify approved Design/Plan execution authority
-> verify separate local receipt-generation authority
-> verify frozen source/config/module bytes and module origins
-> strict-load exact N=3 receipt
-> require receipt decision/counts/false vector/gate3=false/product ledger
-> independently re-admit the three exact source roots
-> compare stored/recomputed identity projection and stored/recomputed 15-field quality projection
-> compare validated identity against receipt membership
-> derive nine rows and three parent-local rows in memory
-> reject any pooled/regime-summary schema or non-finite/type/order violation
-> canonicalize, render and strict-validate staged artifacts
-> manifest-last atomic publication and strict final reload
```

| Condition | Required result |
| --- | --- |
| Generation authority missing, malformed, wrong run id, wrong core/CLI hash, or reused for a different root | `STOP=local_receipt_generation_not_authorized` |
| Approved authority, module byte/origin, imported `configs.base`, or canonical serializer drift | `STOP=stage1_5h_n3_regime_upstream_contract_drift` |
| N=3 root/hash/manifest/summary/review/flag/gate/count/product ledger mismatch | `STOP=stage1_5h_n3_regime_receipt_authority_mismatch` |
| Source root, explicit stored/recomputed identity projection, CT duplicate edge, or receipt-membership mismatch | `STOP=stage1_5h_n3_regime_source_authority_mismatch` |
| Missing, extra, duplicate or cross-parent/regime row | `STOP=stage1_5h_n3_regime_membership_mismatch` |
| Metric key/type/finiteness/equality/arithmetic mismatch | `STOP=stage1_5h_n3_regime_metric_projection_mismatch` |
| Pooled/cohort/regime aggregate, cost-floor, feasibility, Alpha or execution field/prose | `STOP=stage1_5h_n3_regime_scope_violation` |
| Collision, staging, symlink, manifest, projection, canonical-byte or durability failure | `STOP=stage1_5h_n3_regime_publication_integrity_failure` |
| Any downstream consumption request | `STOP=stage1_5h_n3_regime_future_consumer_not_authorized` |

No `.get(..., default)`, substituted source, partial `generated_with_warnings`, tolerant legacy branch or ambient environment path is allowed for required contract data.

## 7. Acceptance invariants

| ID | Invariant |
| --- | --- |
| `INV-HN3-01` | Exact Design/Plan execution authority and the separate §4.2 single-operation receipt-generation capability, including one `AUTHORIZED_RUN_ID` and audited core/CLI bytes, validate before any source read, staging creation or public writer invocation. |
| `INV-HN3-02` | The exact N=3 receipt artifacts, thirteen false flags, `3/3/9` identity and `stage1_5g_gate3_complete=false` validate before source re-admission or output creation. |
| `INV-HN3-03` | Only the §4.3 roots and frozen Stage 1.5G loader/reducer may establish source identity and quality projection; stored/recomputed identity and fifteen-field quality comparators must pass before output. H owns no raw reader or discovery path. |
| `INV-HN3-04` | Exactly nine rows map bijectively to exactly three receipt parent rows; CT emits only `CTUSDT`, while the other seven CT-root children prove duplicate equality with Batch 7 and are not emitted twice. |
| `INV-HN3-05` | Every symbol/parent row carries the exact parent lineage and `product_regime_id` supplied by N=3 receipt; no Design/CLI/user input may relabel it. |
| `INV-HN3-06` | Metrics are exact re-admitted projections; the only new arithmetic is the defined sum of marginal p95 values, without economic or execution interpretation. |
| `INV-HN3-07` | A parent-local median is permitted only within one parent; no cohort/regime/cross-regime aggregate, comparison, cost floor, threshold, score or conclusion is emitted. |
| `INV-HN3-08` | Summary, Markdown and manifest have exact schemas, canonical bytes, deterministic rendering, exact source-anchor binding and a thirteen-key boolean-false vector. |
| `INV-HN3-09` | Directory `flock`, under-lock pre/post classification, symlink rejection, manifest-last publication, atomic rename and both directory fsyncs prevent a cooperating same-RUN-ID writer, partial or non-durable output from being consumable. |
| `INV-HN3-10` | Old N=2 Stage 1.5G/H V3 contracts and artifacts remain immutable and cannot be loaded or reinterpreted by this path. |
| `INV-HN3-11` | This stage grants no Alpha, strategy, replay, simulation, network, paper/live, execution, commit, push, deployment or SSH authority; future consumption requires a distinct approved Design. |

## 8. Verification and fixture provenance

The future Plan may whitelist only:

```text
src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
scripts/external_signal_shadow/run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
tests/research/external_signal_shadow/test_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
tests/scripts/external_signal_shadow/test_run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py
data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/<authorized RUN_ID>/
```

Required mechanical proof:

1. Task 0 captures a unique immutable baseline before changes: exact `HEAD`, full status, tracked/cached diff, index, untracked ledger, Plan/Design hashes and the four allowed source paths. Any baseline drift stops; Task 0 is never rerun or rebased.
2. The canonical positive fixture strict-loads the exact N=3 receipt and re-admits all three actual §4.3 roots through the production loader/reducer. It proves three parent rows, nine unique emitted children, the CT duplicate exclusion, exact product ledger and false flags.
3. One-mutation RED tests reject missing/malformed/tampered §4.2 authorization text or sidecar, mismatched `RUN_ID`, and changed core/CLI bytes before any source root read or staging creation. They then reject altered receipt hash, receipt flag, `gate3`, parent ledger, product regime, source-root manifest, stored/recomputed identity projection, clean-pass scalar, CT identity, Batch7 duplicate identity and each of the two §4.4 metric projections.
4. A single in-memory mutation of either p95 marginal slippage must change only the allowed derived sum and legitimately dependent local parent median; it must not create a pooled result. Tests must assert the absence of every forbidden cohort/regime aggregate and cost/execution/Alpha field.
5. AST/import/open-spy tests prove new H code does not import old H V3/N=2 admission, open/glob raw JSONL, access price/outcome/network/exchange clients, or invoke N=3 `future_consumer_allowed=True`; only the verified upstream Stage 1.5G boundary may open source evidence. A preloaded shadow `configs.base` probe must return `STOP=stage1_5h_n3_regime_upstream_contract_drift` before source-root read or staging creation.
6. Strict-loader tests reject malformed/noncanonical JSON, unexpected key/file, wrong metadata key/length/hash, altered Markdown projection, summary/review/manifest symlink and ancestor symlink, and final root outside project namespace.
7. Crash tests cover before each artifact, after manifest, after staging-directory `fsync`, after rename and before final-parent `fsync`; restart tests cover valid final, corrupt final, stale/malformed sibling, mixed final/staging, collision and a distinct fresh `RUN_ID`. A two-worker same-`RUN_ID` barrier test and a foreign-staging-before-rename test prove that at most one cooperating writer succeeds and success has zero staging siblings.
8. Independently run `.agent/tools/anti_shortcut_scan.py` and record its actual process exit code. Also verify `RISK_LIVE_TRADING_ENABLED=False`, focused pytest, `ruff check`, scope/index proof, independent code review and fresh Completion Audit in that order.

## 9. L2 research boundary

| Required L2 item | Boundary for this Design |
| --- | --- |
| Alpha/economic mechanism hypothesis | N/A. This stage measures no market outcome or strategy rule. |
| Permitted claim | Static, frozen L2 quality description only; `research_classification=evidence_insufficient`. |
| Independent unit / cluster | Parent article/event. Child rows are descriptive; Batch 7's seven symbols remain one cluster. Each regime has only one parent. |
| PIT / anti-hindsight | Only frozen source-root snapshots and historical admission lineage; no subsequent market state or forward outcome. |
| Preregistration | The fixed receipt, roots, memberships, fields, arithmetic and no-pooling rule are frozen before implementation. |
| Outcome distribution, PnL, fees, funding, capacity, MAE, tail loss, outlier, conditional Alpha | N/A. No price outcome, trade or economic result is read. |
| Promotion / kill | N/A for Alpha. Valid diagnostic remains `evidence_insufficient`; invalid evidence causes a contract STOP, not negative expectancy. |
| Deferred claims | Any cross-exchange comparison, temporal microstructure analysis, cost model, simulation, replay, execution feasibility, Alpha, paper/shadow/live claim requires a separate Design and authority. |

## 10. Compatibility, rollout and rollback

- Compatibility: no legacy parsing or migration. Old N=2 receipts/H V3 are rejected as inputs by identity.
- Rollout: N/A. This is an offline local receipt producer with no service, collector, deployment or runtime integration.
- Rollback: N/A. No existing behavior changes. A failed new output remains non-consumable under §5.5; no automatic deletion is authorized.

## 11. Open questions and self-review

There are no blocking open questions. The only potentially useful future question, whether to conduct a cross-exchange or temporal microstructure study, is deliberately deferred because its input authority, independent unit, PIT boundary and allowed claim differ from this static diagnostic.

Mutable set: this candidate Design only.

No-Touch set: `configs/base.py`; Stage 1.5D/1.5F collectors; old N=2 Stage 1.5G and H V3 sources/CLIs/tests/receipts; N=3 Stage 1.5G producer and receipt; all deployment/runtime artifacts.

Required route:

```text
independent Design review
-> explicit user approval of exact Design bytes
-> Implementation Plan and independent Plan review
-> explicit implementation approval
-> implementation, code review and fresh Completion Audit
```

This candidate grants no implementation, local receipt generation, runtime, network, execution, paper, live, deployment, commit, push or SSH authority.
