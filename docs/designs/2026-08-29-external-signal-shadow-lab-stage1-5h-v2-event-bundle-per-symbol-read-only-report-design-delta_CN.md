# External Signal Shadow Lab Stage 1.5H V2 Event-Bundle Per-Symbol Read-Only Report Design Delta

**日期:** 2026-08-29
**状态:** design_approved
**Review Mode:** closure_confirmation
**适用阶段:** Stage 1.5H local-only read-only reporting for a Stage 1.5G v2 quarantined event bundle
**父级设计:** `docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-static-execution-proxy-design_CN.md`
**上游 Delta:** `docs/designs/2026-08-29-external-signal-shadow-lab-stage1-5g-multi-symbol-quarantine-denominator-design-delta_CN.md`
**现有治理 review:** `docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md`
**新 v2 governance review:** `docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md`
**实现计划许可:** `true`
**代码实施许可:** `false`
**部署许可:** `false`

---

## 1. 根因与结论

现有 Stage 1.5H 的已批准治理范围是 `single_event_fixture_bound_report_generator`。它对 v2 `formal_count > 1` 写入 `stage1_5h_multi_symbol_input_not_authorized` 并拒绝；该旧入口及其历史解释保持不变。

2026-08-29 的 Stage 1.5G v2 quarantined closed bundle 包含五个 formal completed event-symbol。新路径不是把五个 orderbook 合成为一个 proxy，而是只在完整上游 evidence 已验证后，为 `S` 中每个 event-symbol 写一份独立、不可交易的 static-proxy 报告和一个非聚合 directory。

```text
complete Stage 1.5G v2 quarantined bundle
-> validate governance and immutable upstream bundle
-> validate formal identity map and JSONL partitions
-> reuse existing Stage 1.5H per-symbol static-proxy semantics
-> exactly one report per member of S
-> non-aggregating event directory
-> manifest-last sealed local bundle
-> no execution, alpha, paper or live authority
```

本 Delta 仅定义该路径的技术 contract。它不复用旧 single-event governance 来授权新路径；新的 governance review 是 Implementation Plan 的前置条件。

---

## 2. 已确认事实与冻结 runtime evidence

本 Design 的真实回归 evidence 仅限下列本地 Stage 1.5G v2 root；这些值是 implementation preflight 和 golden regression 的输入，不是交易或 execution evidence：

```text
review_root =
data/external_signal_shadow/stage1_5g/reviews/
20260829T024637Z_local_recheck_551b1fa19ce6

stage1_5g_review_id =
0b059ce27b67a6221374602552a3f423bd4c07222e976526aadfe9b5f9ddfa50

source_evidence_manifest_sha256 =
46dacc457ed292b40d317ab340319447912d4de23967c2ed7cf638719d714918

formal_completed_event_symbol_ids_sha256 =
40a7584e5bd4a0ec88f7f3e7dbd24ae2249c2d002c426cbb47f688af52eda4aa

stage1_5g_review_manifest.json =
35a1ce9dc0ad02738ab26e97c9fd36ef860d3533dc8626c2f527e7ff1f4ecdf0

stage1_5g_live_depth_evidence_review_summary.json =
0fde86685162b74d08751098075fd5ce74197176408da0a033d214270de2a425

stage1_5g_quarantine_summary.json =
9f783c90015b068499a175061df20e12211469ff559a208ddffd3b12340c41d2

depth_quality_input_rows.jsonl =
1af7418009c5c09375d3c0315b47fb87ff9192b92a0d6cf03248aff0747aec85

quarantined_invalid_book_rows.jsonl =
44ac1a602787507e6178d2b05599e7b8b1f848c82eed2361f5fcb4c04a770bf3
```

该 bundle 的冻结输入状态是：

```text
schema_version = 2
decision = stage1_5g_depth_evidence_quarantined_pass
clean_depth_evidence_pass = false
quarantined_depth_evidence_pass = true
formal_completed_symbol_count = 5
total_expected_snapshot_count = 3600
aggregate_observed_snapshot_count = 3546
aggregate_valid_snapshot_count_after_quarantine = 3543
aggregate_invalid_book_row_count = 3
```

其中三个 event-symbol 是 per-symbol clean，两个是 per-symbol quarantined。它们仅支持 local read-only reporting；不支持 event-family、cross-event 或任何 execution 结论。

---

## 3. 新治理授权与兼容性

### 3.1 New governance authority

旧治理 review 只继续约束 legacy path：

```text
scope = single_event_fixture_bound_report_generator
multi_event_aggregation_allowed = false
event_family_conclusion_allowed = false
```

新 v2 event-bundle path 在 Implementation Plan 之前必须新增、批准并引用一份独立 governance review，且该 review 必须冻结：

```text
scope = v2_event_bundle_per_symbol_read_only_report_generator
multi_symbol_per_symbol_reporting_allowed = true
cross_symbol_metric_aggregation_allowed = false
event_family_conclusion_allowed = false
cross_event_generalization_allowed = false
implementation_plan_allowed = true
implementation_allowed = false
deployment_allowed = false
```

新的 governance review 必须引用本 Delta、上游 Stage 1.5G v2 Delta 和 legacy governance review，并且只授权该 v2 local-only path。`docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md` 已获得 explicit human approval，因此 `PG-H2-01 authority_instantiated = true`；Implementation Plan 现可编写，但代码实施与部署仍未授权。

### 3.2 Compatibility matrix

| 输入 | Legacy Stage 1.5H path | New v2 event-bundle path |
| --- | --- | --- |
| v1, N=1, historical quarantined | 保持既有行为 | 拒绝，不迁移 |
| v1, N>1 | 保持拒绝 | 拒绝 |
| v2, N=1, valid quarantined closed bundle | 保持既有 single-symbol path | 允许；必须与 legacy static-proxy 语义相同 |
| v2, N>1, valid quarantined closed bundle | 保持 `stage1_5h_multi_symbol_input_not_authorized` | 允许；逐 symbol 独立报告 |
| v2, overall clean | 保持当前边界 | 拒绝：`stage1_5h_v2_clean_bundle_not_authorized` |
| v2 invalid, incomplete, manifest mismatch | 拒绝 | 全局拒绝 |
| unknown schema | 拒绝 | 拒绝 |

新路径不改变 v1、historical artifact、legacy Stage 1.5H output 或既有 multi-symbol reject。

---

## 4. Scope、非目标与安全边界

### 4.1 Scope

```text
new local-only v2 closed-bundle validator
one read-only JSON and Markdown report per member of S
one non-aggregating event directory
one manifest-last sealed output bundle
current frozen five-symbol bundle regression
```

### 4.2 Non-goals

```text
Stage 1.5D/F collection changes
Stage 1.5G writer, schema or duplicate-row semantics changes
v1 migration or clean-v2 input path
cross-symbol metric aggregate, average, ranking or synthetic proxy
cross-event/event-family conclusion
order simulation, fill model, replay/PIT, alpha or execution feasibility
paper/live trading, exchange access, private API, API key or VPS deployment
```

### 4.3 Safety fields

每份 JSON report、event directory 和 final manifest 必须固定：

```text
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
private_endpoint_allowed = false
api_key_allowed = false
order_endpoint_allowed = false
```

禁止写入 `SignalCandidate`、`TradeIntent`、buy/sell instruction、entry/exit recommendation、position sizing、`tradeable`、`profitable` 或 readiness claim。

---

## 5. 上游 closed-bundle 合同

### 5.1 Artifact admission

新路径只接收以下完整且 manifest-bound 的 artifact set：

```text
stage1_5g_live_depth_evidence_review_summary.json
stage1_5g_quarantine_summary.json
depth_quality_input_rows.jsonl
quarantined_invalid_book_rows.jsonl
stage1_5g_review_manifest.json
```

验证顺序固定：

```text
validate new governance authority
-> validate manifest schema, relative paths and SHA-256 of all four artifacts
-> validate v2 quarantined admission fields and shared review/source/formal-id identity
-> validate canonical_json_dumps(main_summary.quarantine) == canonical_json_dumps(stage1_5g_quarantine_summary)
-> derive S from main_summary.quarantine.eligible_event_symbol_ids only
-> validate identity map, per-symbol metrics and JSONL total/disjoint partitions
-> generate output only after every upstream invariant succeeds
```

禁止 normalize、sort 或 deduplicate upstream artifact。令：

```text
raw_ids = main_summary.quarantine.eligible_event_symbol_ids
```

准入要求：

```text
raw_ids is a non-empty list[str]
raw_ids == sorted(raw_ids)
len(raw_ids) == len(set(raw_ids))
every raw_id matches ^[0-9a-f]{64}$
S = raw_ids
```

`S` 是唯一 report-set authority；它在验证后保留 producer 给出的 canonical order。必须继续满足：

```text
S hash == formal_completed_event_symbol_ids_sha256
len(S) == quarantine_summary.formal_completed_symbol_count
set(per_symbol_quarantine_metrics) == set(S)
```

`S hash` 必须严格为：

```text
formal_completed_event_symbol_ids_sha256 =
SHA-256(UTF-8(canonical_json_dumps(S)))

hashlib.sha256(canonical_json_dumps(S).encode("utf-8")).hexdigest()
```

embedded/standalone quarantine projection 的任何差异、ID 未排序、重复 ID 或任何其他失败均为 global bundle reject，不得生成部分 authoritative output。

### 5.2 Formal identity authority

`main_summary.event_level_decisions` 是唯一的 `event_symbol_id -> identity` authority。对每个 `s in S` 必须恰有一条 row：

```text
event_symbol_id == s
formal_completed == true
symbol is a nonempty string
source_article_id is a nonempty string
```

此外：

```text
set(event_symbol_id for formal_completed rows) == set(S)
no duplicate event_symbol_id in formal_completed rows
no extra formal_completed row outside S
```

Stage 1.5H 不得从 JSONL、filename、symbol text 或 metrics key 推断 identity。JSONL 仅可 cross-check：每一行的 `event_symbol_id` 和 `symbol` 必须分别等于该 authoritative identity row 的值。

### 5.3 JSONL membership and partition contract

对 valid 和 invalid JSONL 分别执行：

```text
all row.event_symbol_id belong to S
all row.event_symbol_id match ^[0-9a-f]{64}$
row.symbol == identity_map[row.event_symbol_id].symbol
```

令：

```text
valid_rows_s = valid JSONL rows whose event_symbol_id == s
invalid_rows_s = invalid JSONL rows whose event_symbol_id == s
metrics_s = per_symbol_quarantine_metrics[s]
```

每个 `s in S` 必须满足：

```text
len(valid_rows_s) == metrics_s.valid_snapshot_count_after_quarantine
len(invalid_rows_s) == metrics_s.invalid_book_row_count
```

valid 和 invalid 各自均必须是由 `S` 完全覆盖的 disjoint partition：

```text
sum_s len(valid_rows_s) == total valid JSONL rows
sum_s len(invalid_rows_s) == total invalid JSONL rows
```

foreign row、identity mismatch、count mismatch、缺少 metrics、nonempty upstream blocker、invalid-count/phase/reason inconsistency 或任何本节违反均表示上游语义矛盾：

```text
stage1_5h_input_rejected
-> no report
-> no event directory
-> no final manifest
```

Stage 1.5H 不新增 raw-row duplicate quality gate，也不重新解释 Stage 1.5G 已拥有的 duplicate semantics。

---

## 6. 逐标的 static-proxy 语义

### 6.1 Existing semantic reuse

数字质量的唯一来源是：

```text
per_symbol_quarantine_metrics[s].quarantined_depth_quality
```

JSONL 只用于第五章的 provenance、membership 和 count validation；新路径不得从 JSONL 重算 p50、p95、slippage、depth 或 quality gates。

对每个 `s`，新路径必须复用既有 Stage 1.5H static-proxy formula 和阈值：

```text
observed_static_depth_friction_bps_p95 =
  buy_slippage_bps_500usdt_p95 + sell_slippage_bps_500usdt_p95

configured_conservative_round_trip_cost_bps =
  EXTERNAL_SIGNAL_STAGE1_5H_CONSERVATIVE_ROUND_TRIP_COST_BPS

effective_friction_floor_bps =
  max(observed_static_depth_friction_bps_p95,
      configured_conservative_round_trip_cost_bps)
```

禁止将 observed friction 与 configured cost 相加。`spread_bps_p95`、buy/sell slippage p95、top bid/ask depth p05、book availability 和 first-valid latency 的 existing Stage 1.5H blockers 必须原样复用。

同一份 v2 `N=1` quarantined bundle 经 legacy path 和 new path 生成时，以下字段必须完全相同；仅 wrapper、provenance 和 output-path 字段可不同：

```text
static proxy inputs
spread/slippage/depth metrics
availability discount
effective friction floor
Stage 1.5H static-proxy blockers
required_next_evidence
```

### 6.2 Report statuses

每份成功生成的 report 必须区分，且不得混写：

```text
upstream_stage1_5g_status = clean | quarantined
report_generation_status = generated
stage1_5h_static_proxy_status = within_limits | blocked
stage1_5h_static_proxy_blockers = [...]
required_next_evidence = ...
```

`upstream_stage1_5g_status` 只能按下列 authoritative formula 推导，不得从 warning、aggregate decision 或 JSONL 自行猜测：

```text
metrics_s = per_symbol_quarantine_metrics[s]

require metrics_s.blockers == []
require metrics_s.invalid_book_row_count is an integer >= 0

if metrics_s.invalid_book_row_count == 0:
    upstream_stage1_5g_status = clean

elif metrics_s.invalid_book_row_count > 0:
    upstream_stage1_5g_status = quarantined

else:
    global bundle reject
```

`invalid_book_row_count` 必须为 non-negative integer。clean report 必须有零条 invalid JSONL row，且 invalid phase/reason totals 均为零；quarantined report 必须有恰好 `invalid_book_row_count > 0` 条 invalid JSONL row，且 phase/reason totals 均等于该 count。任何不一致均为 global bundle reject。

`stage1_5h_static_proxy_blockers` 是合法 report 的 read-only result，不是 upstream evidence rejection。例如 spread 高、depth 低或 friction 高可以产生 `blocked` report，但永远不能产生 trading recommendation。

不支持“4 个 authoritative report + 1 个 upstream rejected report”的 partial bundle。任一 upstream semantic contradiction 使整个 root non-authoritative。

---

## 7. 输出合同、path safety 与 lifecycle

### 7.1 Root and paths

输出必须是 fresh local-only root，且不在 Stage 1.5F source root 或 Stage 1.5G review root 内：

```text
data/external_signal_shadow/stage1_5h/reports/<fresh-run-id>/
  reports/<event_symbol_id>.json
  reports/<event_symbol_id>.md
  event_directory.json
  stage1_5h_event_bundle_manifest.json
```

`event_symbol_id` 必须是 64 位 lowercase hexadecimal。每个 report path resolve 后必须是 `<root>/reports/` 的 direct non-symlink child；禁止 absolute path、`..`、nested segment、symlink traversal 和 filename collision。

### 7.2 Semantic authority

```text
JSON report = sole machine-readable semantic authority
Markdown report = deterministic human-readable projection of its JSON report
event directory = provenance and status directory only
```

Markdown 不得新增 JSON 没有的 blocker、metric、recommendation、结论或更强表述。event directory 不得包含 aggregate spread、slippage、depth、availability、score、rank、trade recommendation 或 synthetic event-level proxy。

### 7.3 Final manifest exact schema and identity

`stage1_5h_event_bundle_manifest.json` 是唯一 completion/seal authority，必须包含精确的顶层 schema：

```text
schema_version = "stage1_5h_v2_event_bundle_manifest_v1"
bundle_status = "sealed_read_only_bundle"
upstream:
  stage1_5g_review_id
  source_evidence_manifest_sha256
  formal_completed_event_symbol_ids_sha256
  stage1_5g_review_manifest_sha256
event_symbol_ids = sorted(S)
event_directory:
  relative_path
  sha256
reports:
  event_symbol_id ->
    json_relative_path
    json_sha256
    md_relative_path
    md_sha256
    upstream_stage1_5g_status
    stage1_5h_static_proxy_status
all safety fields from Section 4.3
```

`reports` 的 keys 必须精确等于 `S`，每个 stored path 只能出现一次。output bundle identity 是 exact stored manifest raw bytes 的 SHA-256；manifest 不自引用该 digest。

### 7.4 Crash and restart lifecycle

```text
A. root absent
   -> eligible for a new generation

B. root exists and final manifest absent
   -> incomplete_non_authoritative
   -> preserve for diagnostics
   -> never resume, append, repair or seal in place

C. final manifest exists but schema/member/path/hash validation fails
   -> invalid_non_authoritative
   -> no report is reusable

D. final manifest validates and covers exactly S
   -> sealed_read_only_bundle
   -> read-only; no append or mutation
```

Writer sequence is fixed:

```text
validate complete upstream bundle
-> write all JSON/Markdown reports
-> write event_directory.json
-> hash exact stored report/directory bytes
-> write manifest to a temporary file
-> atomically replace final manifest path
```

The directory or N report files never establish success. On rerun after B or C, create a different fresh root.

---

## 8. Acceptance invariants and verification

| ID | Invariant |
| --- | --- |
| INV-H2-01 | New v2 path has an approved new governance authority; legacy governance is not silently reused. |
| INV-H2-02 | Only complete manifest-bound v2 quarantined bundles enter the new path. |
| INV-H2-03 | `event_level_decisions` provides a unique formal identity map exactly matching `S`. |
| INV-H2-04 | Valid/invalid JSONL membership, identity and per-symbol counts form total/disjoint partitions of `S`. |
| INV-H2-05 | Quality metrics and static-proxy semantics are reused from existing Stage 1.5H; JSONL does not recalculate them. |
| INV-H2-06 | Any upstream contradiction globally rejects; static-proxy blockers remain report-level only. |
| INV-H2-07 | Exactly one JSON and Markdown report exists for every member of `S`; no cross-symbol aggregate appears. |
| INV-H2-08 | Event-symbol IDs and resolved report paths are root-confined and path-safe. |
| INV-H2-09 | Only a valid final manifest seals an output root; incomplete or invalid roots are non-authoritative. |
| INV-H2-10 | JSON is semantic authority and Markdown is a deterministic non-expanding projection. |
| INV-H2-11 | Legacy Stage 1.5H remains unchanged; v2 N=1 semantic fields are equivalent across legacy and new paths. |
| INV-H2-12 | All output permissions remain false. |

Implementation verification must prove at minimum:

1. The frozen five-symbol bundle, after full hash preflight, generates exactly five reports, one directory and one valid sealed manifest.
2. Altering any upstream manifest hash, artifact byte, embedded/standalone quarantine projection, review/source/formal-id identity, raw-ID order/uniqueness, formal identity row, JSONL membership, JSONL symbol or per-symbol count globally rejects with no final manifest.
3. A foreign JSONL row globally rejects; no new duplicate-row quality rule is introduced.
4. Missing per-symbol metrics, nonempty upstream blocker, non-integer/negative invalid count, or invalid JSONL/phase/reason count inconsistency globally rejects.
5. Static proxy formula uses `max(observed, configured)`, never addition; existing Stage 1.5H blocker thresholds are preserved.
6. A v2 N=1 quarantined fixture yields equivalent legacy/new static-proxy fields, blockers and `required_next_evidence`.
7. A clean per-symbol and a quarantined per-symbol retain their respective availability and invalid-row facts without metric borrowing.
8. Unsafe event-symbol IDs, traversal paths, symlinks, collisions and root overlap reject before write.
9. Crash states B/C never resume or become sealed; only an atomic valid final manifest produces state D.
10. Markdown is deterministic from JSON and adds no metric, blocker or recommendation.
11. Existing v1 and legacy Stage 1.5H tests remain behavior-compatible.
12. Regression revalidates every frozen runtime SHA-256 in Section 2 before generating the five reports.

---

## 9. Contract impact matrix

| Component | Change | Compatibility requirement |
| --- | --- | --- |
| Stage 1.5D/F producer | None | No collection, API, VPS or writer change. |
| Stage 1.5G producer/reviewer | None | Existing v2 manifest, identity and duplicate semantics remain authoritative. |
| Legacy Stage 1.5H loader/report | None | v1 and v2 N=1 legacy behavior remains unchanged. |
| New Stage 1.5H v2 local path | New after governance approval | Reads only the closed bundle; writes only fresh local output roots. |
| Downstream consumer | N/A | No new execution, alpha or deployment consumer is authorized. |

---

## 10. Approval gates

Before an Implementation Plan may be written, closure confirmation must establish:

1. a new governance review explicitly authorizes only `v2_event_bundle_per_symbol_read_only_report_generator`;
2. all `INV-H2-01` through `INV-H2-12` are unambiguous and fail closed;
3. current frozen evidence is treated only as local read-only regression input;
4. legacy Stage 1.5H remains unmodified in scope and authority;
5. every execution, alpha and trading permission remains false.

Closure confirmation and the independent governance review have passed:

```text
implementation_plan_allowed = true
implementation_allowed = false
deployment_allowed = false
```
