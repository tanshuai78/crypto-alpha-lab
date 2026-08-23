# Stage 1.6A Sealed-Export Adapter Derived Artifact Schema Delta

- **日期:** 2026-08-23
- **状态:** `design_approved`
- **Review Mode:** `closure_confirmation`
- **类型:** narrow derived-artifact contract delta
- **父契约:** `2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md`
- **不授权:** Stage 1.6B、旧 Stage 1.6A fixture runner/storage/fixture schema、network、PIT、replay、risk、execution 或 deployment change

---

## 1. Confirmed Facts / Assumptions / Root Cause

父 1.6A fixture reducer 的 `semantic_extractions`、`delisting_notices` 与 `DelistingContract.to_dict()` 是 conditional dictionaries：至少 `delisting_notices` 有多种合法 key set，且部分 rows 没有 `schema_version`。因此它们不是本 adapter 可直接声称复用的 exact serialized contract。

父 v2 Section 12.3 的“reuse approved parent exact schemas”表述会让 Plan 决定新的持久化 key set，违反 derived artifact -> completion manifest -> independent consumer 的单一 authority 要求。

**Assumptions**：父 v2 已冻结的 source snapshot、candidate/revision/semantic reducer、metric definition、historical temporal values 和 completion-manifest hash contract 均正确且不在本 delta 修改范围内。此 delta 只为四个 previously-undefined derived projection artifacts 定义序列化协议；不重新定义其 semantic reducer。

## 2. Decision And Scope

本 delta 取代父 v2 Section 12.3 中关于以下四个 artifact “复用 parent exact schema”的表述：

```text
audit_candidate_manifest.json
semantic_extractions.jsonl
delisting_notices.jsonl
delisting_contracts.jsonl
```

它们是 **new adapter projection artifacts**，只用于 `stage1_6a_sealed_export_source_audit_v2` root；不得改变旧 fixture runner、其输出或其 storage loader。四个 artifact 的 bytes 仍是 Section 12.6 `authoritative_artifacts` 的一部分。

所有 schema key set 均为 exact set；缺失、额外 key、未知 enum、错误 nullability 或 nested-object shape 均使 completed consumer reject root。`artifact_profile_version` 固定为 `stage1_6a_sealed_export_source_audit_v2`。

除非本节另有说明：`*_id`、`*_sha256`、`*_version`、`title`、enum 均为非空 string；`*_sha256` 为 64 个小写 hexadecimal characters；`*_ms` 为 `int`（禁止 bool）或明示的 `null`。所有 `source_article_id`、list-capture ID、revision ID、semantic extraction ID、raw hash、source profile fields 都必须和父 v2 reducer 已验证并保留的 authoritative input/value 完全相等，不得由 adapter 重新猜测、修复或别名化。

## 3. Exact Schemas

### 3.1 Candidate Manifest

`audit_candidate_manifest.json` exact top-level keys：

```text
schema_version
artifact_profile_version
capture_mode
input_export_id
input_manifest_sha256
candidate_discovery_rule_version
manifest_id
candidates
```

固定值：`schema_version=stage1_6a_adapter_candidate_manifest_v1`、`artifact_profile_version=stage1_6a_sealed_export_source_audit_v2`、`capture_mode=historical_backfill`、`candidate_discovery_rule_version=candidate_discovery_rule_v1`。`input_export_id`、`input_manifest_sha256` 必须与 `source_export_receipt.json` 相等。`manifest_id` 是 `sha256(input_export_id | candidate_discovery_rule_version | len(candidates))`，其中 `|` 是 UTF-8 literal delimiter；`candidates` 按 `source_article_id` 严格升序；每个 element exact keys：

```text
source_article_id
discovery_title
first_list_capture_id
source_catalog_id
source_catalog_name
notice_lineage_first_detected_at_ms
```

`discovery_title` 是对应 `ArticleDiscovery.title` 的 non-empty string；`source_catalog_id=161`、`source_catalog_name=Delisting`、`notice_lineage_first_detected_at_ms=null`。每一 ArticleDiscovery candidate 恰有一个 element；后续 outcome 不得改变该 array。

### 3.2 Semantic Extraction Projection

`semantic_extractions.jsonl` 每一行 exact keys：

```text
schema_version
artifact_profile_version
source_article_id
detail_revision_id
semantic_extraction_id
semantic_extractor_version
body_normalization_version
canonical_fact_fingerprint
normalized_body_sha256
semantic_extracted_at_ms
capture_mode
system_available_at_ms
fact_available_at_ms
capture_time_status
point_in_time_replay_eligible
risk_veto_candidate
```

固定 `schema_version=stage1_6a_adapter_semantic_extraction_v1`、`artifact_profile_version=stage1_6a_sealed_export_source_audit_v2`、`capture_mode=historical_backfill`、`system_available_at_ms=null`、`fact_available_at_ms=null`、`capture_time_status=historical_unknown`、`point_in_time_replay_eligible=false`、`risk_veto_candidate=false`。`semantic_extracted_at_ms` 是实际本地 extraction 的非负 epoch-ms int。只有 selected trusted revision 且 BAPI envelope/body 已建立 semantic authority 的 parent 才写一行；其它 parent 仍由 exact parent outcome row 留在 metric denominator。每行的 `detail_revision_id`、`semantic_extractor_version`、`body_normalization_version`、`canonical_fact_fingerprint` 与 `normalized_body_sha256` 必须是该 selected revision 的 reducer output；`semantic_extraction_id` 必须是父 v2 所冻结的 semantic ID。

### 3.3 Notice Projection

`delisting_notices.jsonl` 每个 frozen candidate 恰有一行，exact keys：

```text
schema_version
artifact_profile_version
source_article_id
detail_revision_id
semantic_extraction_id
source_detail_title
source_published_at_ms
publication_time_status
parent_declaration_status
source_audit_eligible
declared_child_count
eligible_child_count
capture_mode
semantic_extracted_at_ms
notice_lineage_first_detected_at_ms
system_available_at_ms
fact_available_at_ms
capture_time_status
point_in_time_replay_eligible
risk_veto_candidate
```

固定 `schema_version=stage1_6a_adapter_delisting_notice_v1`、`artifact_profile_version=stage1_6a_sealed_export_source_audit_v2`、`capture_mode=historical_backfill`、`notice_lineage_first_detected_at_ms=null`、`system_available_at_ms=null`、`fact_available_at_ms=null`、`capture_time_status=historical_unknown`、`point_in_time_replay_eligible=false`、`risk_veto_candidate=false`。`semantic_extracted_at_ms` 是 nonnegative int，或在未建立 semantic authority 时为 `null`。

没有 selected trusted revision 或无法建立 semantic authority 时：`detail_revision_id=null`、`semantic_extraction_id=null`、`source_detail_title=null`、`source_published_at_ms=null`、`semantic_extracted_at_ms=null`、`declared_child_count=0`、`eligible_child_count=0`、`source_audit_eligible=false`。否则 title 仅可来自 selected BAPI `data.title`，不得来自 discovery/list title；`source_published_at_ms` 是 V2 publication authority 的 valid epoch-ms 或 `null`；count fields are nonnegative ints；`source_audit_eligible` is bool。不得省略 key。

### 3.4 Contract Projection And Nested Schedule Facts

`delisting_contracts.jsonl` 每个 declared child 一行，exact keys：

```text
schema_version
artifact_profile_version
contract_id
parent_article_id
detail_revision_id
semantic_extraction_id
canonical_symbol
settlement_asset
quote_asset
margin_family
contract_type
underlying_family
is_in_scope
source_audit_eligible
settlement_time
order_restriction
last_trading_time
delisting_complete_time
capture_mode
semantic_extracted_at_ms
notice_lineage_first_detected_at_ms
system_available_at_ms
fact_available_at_ms
capture_time_status
point_in_time_replay_eligible
risk_veto_candidate
```

固定 `schema_version=stage1_6a_adapter_delisting_contract_v1`、`artifact_profile_version=stage1_6a_sealed_export_source_audit_v2`、`capture_mode=historical_backfill`、`notice_lineage_first_detected_at_ms=null`、`system_available_at_ms=null`、`fact_available_at_ms=null`、`capture_time_status=historical_unknown`、`point_in_time_replay_eligible=false`、`risk_veto_candidate=false`。`semantic_extracted_at_ms` 是对应 semantic projection 的 nonnegative int。`settlement_asset` 与 `quote_asset` 只能是 selected canonical-English BAPI semantic reducer 直接证明的 non-empty uppercase asset string，或 `null`；`null` 是唯一 unavailable representation，表示该 child 的 product declaration incomplete，故该 parent 不得产生 eligible child。不得由 canonical symbol、当前/未来 exchangeInfo、list title 或人工规则猜测/补齐资产。`source_audit_eligible` 只有在父 declaration complete 且 child 满足 USD-M crypto perpetual scope 时可为 true；其它 bool 值、child identity/classification 与 selected semantic authority 的 reducer output 必须一致。

四个 schedule field 都必须是 object，而非 optional/missing key；其 exact keys：

```text
fact_parse_status
capture_time_status
timestamp_ms
order_restriction_type
source_detail_revision_id
source_semantic_extraction_id
fact_available_at_ms
evidence
```

`evidence` 可为 `null`；非 null 时 exact keys：

```text
detail_revision_id
detail_raw_sha256
semantic_extraction_id
semantic_extractor_version
body_normalization_version
location_kind
location_value
normalized_body_utf8_byte_start
normalized_body_utf8_byte_end
excerpt
```

`fact_parse_status` 只允许 parent Stage 1.6A frozen enum：`present`、`not_stated`、`unparseable`、`conflicting`、`out_of_scope`。historical schedule `capture_time_status=historical_unknown`、`fact_available_at_ms=null`。`order_restriction_type` 只可用于 `order_restriction` 且为 approved order-restriction enum；其它三项必须为 `null`。`timestamp_ms` 只可用于三个 time fields，且为 valid epoch-ms 或 `null`；`order_restriction.timestamp_ms=null`。`source_detail_revision_id` 与 `source_semantic_extraction_id` 要么均为当前 row 的 selected IDs、要么均为 `null`；`evidence` 非 null 时必须引用同一 IDs 和同一 raw SHA。无事实时使用 explicit `not_stated` object：除 `fact_parse_status` 与 `capture_time_status` 外全部值为 `null`，不得省略 schedule field。

## 4. Writer / Consumer / Failure Contract

| Role | Required behavior | Forbidden behavior |
|---|---|---|
| adapter writer | Write the four exact schemas only after complete parent outcomes exist. | Borrow conditional fixture row shapes or omit null fields. |
| completed consumer | Verify stored bytes/hashes, then rebuild and exact-compare each semantic projection from the caller-supplied source export. | Trust persisted shape, hash or final verdict without rebuild. |
| fixture-only 1.6A writer/loader | Remain unchanged. | Read, migrate or accept an adapter root. |
| operator | Supply one exact completed source export and inspect a completed adapter root. | Repair rows, fill missing fields or mix roots. |

Writer 必须先生成完整 parent outcomes，再由相同 projection 生成这四个 artifact；不得从 success-only rows重新推导 candidate denominator。Completed consumer 必须先验证 persisted artifact bytes 对应 completion-manifest hashes，再 re-reduce exact source bytes。JSONL row order is part of the exact protocol and must be strictly ascending: `semantic_extractions.jsonl` by `(source_article_id, detail_revision_id, semantic_extraction_id)`; `delisting_notices.jsonl` by `source_article_id`; `delisting_contracts.jsonl` by `(parent_article_id, canonical_symbol, contract_id)`. Tied sort keys/duplicate logical rows are rejection. 重建比较使用 `deterministic_projection_view`：对每个 JSON object 仅删除 `semantic_extracted_at_ms`，按 JSON key lexical order 和上述 fixed row order 作 canonical JSON comparison；不得删除、归一化或忽略任何其它字段。该 timestamp 已受 persisted artifact hash 保护，但不属于 semantic identity，故不能要求独立 rerun 的墙钟值相同。

任何这四个 artifact 的 shape/hash/projection mismatch 都是 completed-root rejection；不得降级为 partial metric、schema fallback 或 legacy compatibility path。Structural source failure 仍发生在 output root 创建前；denominator-visible semantic failure 仍写 parent outcome 和 notice row，但可不写 semantic extraction/contract row。

本 delta 不增加 checkpoint/resume：crash before completion manifest leaves a non-consumable fresh root; rerun uses a new audit run ID under the parent v2 lifecycle.

## 5. Acceptance Invariants

| ID | Invariant |
|---|---|
| INV-D01 | The four listed artifacts have one adapter-owned exact schema; no fixture-only conditional row schema is reused. |
| INV-D02 | Every frozen candidate has exactly one candidate-manifest entry and one notice row, including denominator-visible failures. |
| INV-D03 | Semantic extraction and contract rows are emitted only from selected trusted canonical BAPI authority. |
| INV-D04 | Every contract persists settlement_asset and quote_asset from selected BAPI authority or explicit null; every schedule field and non-null evidence object has the exact nested schema defined in Section 3.4. |
| INV-D05 | Writer and completed consumer use the same deterministic projection; any shape, hash or rebuilt-projection mismatch rejects the completed root. |
| INV-D06 | This delta cannot grant PIT, replay, risk, paper, live or execution authority. |

## 6. Persistence / Compatibility / Safety / Verification / Rollback / Open Questions

输出 root、summary、completion-manifest-last、crash、fresh-rerun 和 no-resume 行为完全沿用父 v2；本 delta 不增加 checkpoint、recovery state 或 writer。旧 fixture-only outputs 不是 compatibility target，也不会被该 adapter reader 接受或迁移。所有 live/PIT/replay/risk/paper/execution authority 维持 false；本 delta 不引入网络或 source mutation。rollback 是停止 adapter invocation；已完成 root 保留只读，partial root 仍 non-consumable。

后续 Plan RED tests 至少覆盖：每个 candidate 一条 notice；missing/extra key、wrong nullability 或 unknown enum reject；settlement_asset/quote_asset source-proved versus null-incomplete and symbol/exchangeInfo inference reject；nontrusted parent 有 notice 但没有 semantic extraction/contract；BAPI title 而非 list title provenance；schedule absent 仍为 exact `not_stated` object；nested evidence key/ID mismatch reject；each JSONL sort order/duplicate rejection；completed consumer 重建四个 projection、只忽略 permitted local extraction timestamp、并拒绝任何其他 tampering。

Open Questions：`N/A`。此 delta 只冻结既有 adapter output protocol，不改变 semantic, metric 或 upstream collection authority。
