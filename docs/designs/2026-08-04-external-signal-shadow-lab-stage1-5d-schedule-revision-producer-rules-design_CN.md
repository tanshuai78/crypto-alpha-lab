# Stage 1.5D Schedule Revision Producer Rules Design

**日期:** 2026-08-04
**关联主设计:** `docs/designs/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-launch-time-priority-anchor-precedence-hotfix-design_CN.md`
**关联实现计划:** `docs/plans/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-schedule-priority-anchor-contract-v2-hotfix-implementation-plan_CN.md`
**范围:** Stage 1.5D schedule revision producer classifier / linker / formal row emission rules
**状态:** design revised after P0 review

---

## 1. 当前结论

```text
decision = stage1_5d_schedule_revision_producer_rules_ready_for_implementation_plan_after_prerequisite_check
scope = stage1_5d_revision_detection_linking_identity_and_formal_row_emission
producer_policy_version = linked_only_formal_v1
schedule_revision_consumer_prerequisites_verified = required_before_enablement
schedule_revision_producer_supported = design_defined
schedule_revision_producer_enabled = false_until_consumer_prerequisites_verified
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

本设计只定义 Stage 1.5D 自动 producer。它不假设 consumer 能力已经被事实验证。实施计划开始前必须先用代码、测试和 commit SHA 验证 1.5F / 1.5G 已能安全消费 schedule revision row。

---

## 2. Review 采纳结论

```text
partner1_p0 = all_adopted
partner2_p0 = all_adopted
partner1_p1 = adopted
partner2_p1 = adopted_except_active_cancel_stop_snapshots
implementation_plan_allowed = only_after_this_design_revision
implementation_allowed = false
```

唯一不完全采纳项：`cancelled revision` 到达时，active observation 不立即停止 snapshot collection。原因是 Stage 1.5F 当前是 read-only evidence collector，停止会制造部分证据窗口；更安全的默认是继续只读采集到原窗口结束，同时将 lineage 标记为 contaminated，让 Stage 1.5G 判 invalid。

---

## 3. Consumer Prerequisite Gate

Stage 1.5D 只有在以下硬证据齐全时，才允许设置：

```text
schedule_revision_consumer_prerequisites_verified = true
schedule_revision_producer_enabled = true
```

必须验证的证据：

```text
1. 1.5F schedule revision contract validator 文件和函数存在。
2. 1.5F durable schedule revision registry 存在，并覆盖 replay/idempotency。
3. 1.5F orphan/replay/crash recovery tests 存在且通过。
4. 1.5F pending/active/completed lineage contamination tests 存在且通过。
5. 1.5G latest observer_state lineage invalidation tests 存在且通过。
6. 上述能力对应 commit SHA 已记录在 deployment checklist。
```

Runtime gate 必须区分 capability 与 health：

```text
schedule_revision_producer_supported = true
schedule_revision_producer_enabled = false | true
schedule_revision_producer_health = ready | degraded | blocked
schedule_revision_consumer_prerequisites_verified = false | true
```

如果 revision index 损坏、schema 不兼容、detail endpoint 退化，必须暂停 revision formal emission，但 normal v2 launch collection 可以继续运行。

---

## 4. 非目标

```text
1. 不启用 paper/live/execution/alpha。
2. 不把 spot/margin/earn/options/delisting/settlement/API maintenance 纳入 revision producer。
3. 不允许 symbol-only supersedes inference。
4. 不让 scheduler candidate 作为 formal linking evidence。
5. 不要求本轮实现人工审核 UI。
6. 不回写或改写旧 root。
```

---

## 5. Revision Intent Classifier

### 5.1 结构化输出

Classifier 不能使用 full-article keyword hit 直接判定。输出必须是结构化 intent：

```text
revision_intent =
  rescheduled_with_new_anchor
  postponed_without_anchor
  cancelled
  not_revision
  ambiguous_revision_intent
```

成为 formal candidate 的最低条件：

```text
revision action phrase
+ futures contract launch lifecycle context
+ symbol mapping
+ same logical_block_id
+ mandatory detail payload parsed
```

`will launch at` 本身不是 revision 证据。它只有在同一 logical block 内同时出现 replacement/reschedule/postpone 语义，或明确指向旧 schedule，才可进入 revision intent。

### 5.2 分类优先级

同一 logical block 内按以下优先级分类：

```text
cancelled
> rescheduled_with_new_anchor
> postponed_without_anchor
> ordinary_new_launch
> out_of_scope
```

无法区分 postpone 与 cancel 时：

```text
revision_intent = ambiguous_revision_intent
formal_emit_allowed = false
```

### 5.3 必须覆盖的反例

```text
ordinary "will launch SYMBOL at TIME" -> ordinary_new_launch, not revision
"API maintenance delayed" -> out_of_scope
"funding settlement delayed" -> out_of_scope
same article postpone + new time -> rescheduled_with_new_anchor
ambiguous postpone/cancel language -> ambiguous_revision_intent, diagnostic only
```

---

## 6. Mandatory Detail-Fetch Lifecycle

Revision candidate 必须进入 detail/BAPI pipeline。Title-only 信息只能生成 candidate，不能 formal emit。

```text
list/title possible revision
-> revision_candidate_pending_detail
-> detail_work_type = launch_schedule_revision_detail
-> BAPI/detail fetch
-> detail parsed into intent/link/anchor evidence
-> formal launch identity index lookup
-> linked-only formal row or diagnostic
```

Detail 状态规则：

```text
detail not attempted -> no formal revision
detail HTTP 202 / timeout / empty -> pending revision detail retry
detail max age exceeded -> terminal_non_consumable revision diagnostic
detail parsed but intent/link ambiguous -> diagnostic only
detail parsed and linked -> eligible for formal contract validation
```

Scheduler 必须保留单文章 retry 上限，并避免 fresh revision 被旧 HTTP 202 backlog 饿死。

---

## 7. Formal Launch Identity Index

### 7.1 唯一 formal linking source

Producer formal linking 只能查询版本化 identity index：

```text
stage1_5d_formal_launch_identity_index.jsonl
```

该 index 只能由通过共享 validator 的 formal v2 launch rows 构建。Scheduler state 只能用于 diagnostics，不得生成 `supersedes_source_article_id` 或 `stable_schedule_identity`。

Index row 最少字段：

```text
index_schema_version
source_root_id
source_root_commit_sha
source_article_id
symbol
normalized_source_namespace
source_transport
formal_event_contract_version
source_anchor_contract_hash
official_schedule_anchor_ms
source_published_at_ms
first_observed_at_ms
event_id
payload_sha256
```

### 7.2 Index 有效性

```text
index missing -> schedule_revision_producer_health = blocked
index schema invalid -> schedule_revision_producer_health = blocked
index hash invalid -> schedule_revision_producer_health = blocked
explicit L1/L2 reference not found in index -> orphaned
explicit L1/L2 reference resolves multiple rows -> ambiguous
```

配置必须显式存在：

```text
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_LOOKBACK_DAYS = 14
```

不允许在代码中用 silent fallback 掩盖该常量缺失。

---

## 8. Poll 内查询时序

Producer 的查询窗口必须是 point-in-time safe：

```text
state_query_window = prior polls durable formal launch identity index
                   + current poll in-memory formal launch index built before revision processing
```

同一 poll 中的处理顺序：

```text
1. parse launch rows
2. validate launch rows against formal v2 contract
3. add valid launch rows to in-memory formal launch index
4. parse revision candidates
5. link revision candidates against durable index + current in-memory index
6. append launch rows, revision rows, diagnostics, and batch state durably
```

如果实现无法保证该两阶段顺序，则同 poll 的 launch + revision 组合必须 diagnostic-only，不能 formal emit。

---

## 9. Linking Evidence Rules

每个 revision candidate 的每个 symbol 必须得到一个状态：

```text
linked
orphaned
ambiguous
out_of_scope
```

第一版 automatic formal linking 只允许 L1/L2/L3：

```text
L1 explicit_source_article_id:
  revision body 明确引用原始 articleCode/source_article_id，且 index 中唯一命中。

L2 explicit_original_title_or_url:
  revision body 明确包含原始公告 URL/title/canonical slug，且 index 中唯一命中。

L3 unique_symbol_original_schedule_match:
  revision body 给出 symbol + superseded_anchor_ms / old launch time，且 index 中唯一 formal v2 launch row 同时满足：
    same symbol
    same product family
    same settlement asset
    same contract type
    same normalized_source_namespace
    official_schedule_anchor_ms == superseded_anchor_ms
    original_source_published_at_ms <= revision_available_at_ms
    revision_available_at_ms - original_source_published_at_ms <= lookback_days
```

L4 禁用 automatic formal linking：

```text
L4 unique_symbol_pending_match_without_old_anchor = diagnostic_only
formal_emit_allowed = false
```

原因：L4 本质是 symbol + lookback uniqueness，没有独立 supersession 证据，会把不同 lifecycle 错误关联。

---

## 10. Formal Row Emission Contract

### 10.1 Builder 输入必须显式

`revision_link_status` 必须由 Producer 显式传入，builder 不得从 `stable_identity` 自行推导。

```python
build_formal_schedule_revision_row(
    *,
    source_article_id: str,
    supersedes_source_article_id: str,
    symbol: str,
    revision_intent: Literal[
        "rescheduled_with_new_anchor",
        "postponed_without_anchor",
        "cancelled",
    ],
    link_status: Literal["linked"],
    revised_anchor_ms: int | None,
    superseded_anchor_ms: int | None,
    revision_semantic_id: str,
    revision_payload_version_id: str,
    revision_observation_id: str,
    revision_payload_hash: str,
    raw_payload_sha256: str,
    revision_available_at_ms: int,
    producer_decision_at_ms: int,
    linking_index_as_of_ms: int,
    provenance: dict,
) -> dict
```

Required guard：

```python
assert link_status == "linked", "only linked revisions may build formal rows"
```

如果 `link_status != linked`，Producer 不得调用 builder，必须写 diagnostic。

### 10.2 Intent 到 status 映射

```text
revision_intent = rescheduled_with_new_anchor:
  symbol_official_schedule_statuses[symbol] = rescheduled
  symbol_revised_anchor_ms[symbol] = parsed new anchor

revision_intent = postponed_without_anchor:
  symbol_official_schedule_statuses[symbol] = postponed_without_anchor
  symbol_revised_anchor_ms[symbol] = null

revision_intent = cancelled:
  symbol_official_schedule_statuses[symbol] = cancelled
  symbol_revised_anchor_ms[symbol] = null
```

Validator 必须校验：

```text
symbol_official_schedule_statuses[symbol] in {rescheduled, postponed_without_anchor, cancelled}
rescheduled requires revised_anchor_ms not null
postponed_without_anchor requires revised_anchor_ms null
cancelled requires revised_anchor_ms null
revision_link_status == linked
```

---

## 11. Time Semantics

必须区分发布时间、首次观测时间和 payload 版本首次观测时间：

```text
revision_source_published_at_ms
revision_first_observed_at_ms
revision_payload_first_observed_at_ms
revision_available_at_ms
producer_decision_at_ms
linking_index_as_of_ms
```

计算规则：

```text
new revision article:
  revision_available_at_ms = max(revision_source_published_at_ms, revision_first_observed_at_ms)

existing article payload changed:
  revision_available_at_ms = revision_payload_first_observed_at_ms
```

所有 linking、ordering、point-in-time selection 和 lookback 计算必须使用 `revision_available_at_ms`。不得用原始 article publish time 替代，以避免 in-place edit 时间穿越。

Lookback 基准：

```text
revision_available_at_ms - original_source_published_at_ms <= EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_LOOKBACK_DAYS
```

超过 lookback 是 coverage loss，不是 parser failure。

---

## 12. Revision Identity Model

不要把 semantic identity 与 payload version 混在一个 ID 内。

```text
revision_semantic_id = sha256(
  source_article_id
  | symbol
  | revision_intent
  | revised_anchor_ms
  | supersedes_source_article_id
)

revision_payload_hash = sha256(canonical_revision_evidence_dict)
raw_payload_sha256 = sha256(raw_bapi_article_detail_response_bytes)

revision_payload_version_id = sha256(source_article_id | raw_payload_sha256)
revision_observation_id = sha256(revision_semantic_id | revision_payload_version_id | revision_first_observed_at_ms)
revision_application_id = revision_semantic_id
```

Consumer 应按 `revision_application_id` 做语义应用，避免 HTML formatting 变化重复污染 state。

规则：

```text
same semantic_id + different raw_payload_sha256 + same parsed semantics -> payload_variant_diagnostic, do not reapply
same source_article_id + changed semantic fields -> new semantic revision
same raw_payload_sha256 replay -> exact duplicate
```

---

## 13. Multi-Symbol Batch Contract

multi-symbol revision article 使用 per-symbol formal rows，但 producer 必须维护 batch crash consistency。

Batch state 字段：

```text
revision_article_batch_id
expected_revision_symbols
linked_symbols
orphaned_symbols
ambiguous_symbols
out_of_scope_symbols
emitted_revision_semantic_ids
emitted_revision_observation_ids
batch_status
```

允许状态：

```text
candidate_parsed
linking_complete
partially_emitted
all_emit_actions_durable
terminal_diagnostic
```

文本结构规则：

```text
exact_per_symbol_row:
  linked symbols 可独立 formal emit；其他 symbols diagnostic。

exact_all_symbols_statement:
  必须知道 original complete symbol set，且所有目标 symbols linking 完成、状态一致、anchor 规则一致；否则整组 diagnostic-only。

partial_revision:
  只影响文本明确 revision 的 symbols。
```

Crash recovery 必须保证：

```text
crash after first row append -> restart emits only missing rows
crash before batch terminal state write -> restart reconciles emitted rows from events stream
exact_all_symbols_statement -> never partially mutates subset
```

---

## 14. Late Conflict Handling

Append-only 环境不能撤回已写 revision。策略如下：

```text
1. 每条 independent official linked revision row 可以 formal emit。
2. Stage 1.5F point-in-time selector 遇到同 stable_schedule_identity + same revision_available_at_ms + conflicting revised_anchor/status 时 fail closed。
3. 对应 event_symbol_id 进入 pending_official_schedule_conflict 或 contaminated lineage，不得静默继续使用 first revision。
```

第一版不新增单独 `futures_contract_launch_schedule_revision_conflict` artifact。只有当 fail-closed counter 在 live 中出现，才考虑新增 conflict transport row。

---

## 15. Diagnostics And Summary

每条 orphaned / ambiguous / out_of_scope / payload_variant diagnostic 至少记录：

```text
diagnostic_type
source_article_id
symbol
revision_intent
candidate_original_article_ids
link_evidence_levels
matched_symbols
matched_old_anchors
lookback_calculations
linking_index_hash
producer_policy_version
revision_available_at_ms
producer_decision_at_ms
raw_payload_sha256
revision_payload_hash
```

Summary/runtime gate 记录 sample-capped counters：

```text
schedule_revision_candidate_count
schedule_revision_linked_emit_count
schedule_revision_orphaned_diagnostic_count
schedule_revision_ambiguous_diagnostic_count
schedule_revision_out_of_scope_count
schedule_revision_payload_variant_count
schedule_revision_late_conflict_count
schedule_revision_detail_pending_count
schedule_revision_detail_terminal_non_consumable_count
schedule_revision_coverage_loss_outside_lookback_count
```

---

## 16. Cancellation Semantics In 1.5F/1.5G

```text
pending observation not started:
  mark pending_cancelled / no promotion to active

active observation:
  continue read-only snapshot collection to original window end
  mark schedule_lineage_contaminated = true
  record revision_id / revision_semantic_id / revision_available_at_ms

completed observation:
  do not reopen
  Stage 1.5G marks evidence invalid lineage if cancellation was point-in-time applicable
```

该策略保留证据，不产生交易行为，不扩大风险面。

---

## 17. Fixtures And Tests Required Before Plan Completion

Required fixtures：

```text
1. Real/frozen AIA postponement fixture with full provenance。
2. Synthetic explicit L1 source_article_id reschedule fixture。
3. Synthetic L2 original URL/title fixture。
4. Synthetic L3 symbol + old official anchor exact match fixture。
5. Synthetic L4 symbol-only unique pending fixture that must remain diagnostic-only。
6. Synthetic cancelled fixture。
7. Multi-symbol exact_per_symbol_row fixture。
8. Multi-symbol exact_all_symbols_statement fixture。
9. In-place payload edit fixture with later revision_payload_first_observed_at_ms。
10. Late same-time conflict fixture。
```

Fixture metadata 必须包含：

```text
request_id
fetched_at_ms
http_status
payload_sha256
fixture_sha256
request_manifest_path
parser_version
point_in_time_status
raw_payload_sha256
revision_payload_hash
```

Required tests：

```text
test_consumer_prerequisite_gate_blocks_producer_enablement_without_verified_evidence
test_plain_will_launch_at_is_not_revision
test_api_maintenance_delayed_is_out_of_scope
test_funding_settlement_delayed_is_out_of_scope
test_title_only_revision_candidate_never_formal_emits
test_l4_symbol_only_unique_match_is_diagnostic_only
test_explicit_article_reference_requires_index_unique_hit
test_l3_requires_old_official_anchor_exact_match
test_builder_rejects_non_linked_revision_link_status
test_cancelled_revision_maps_cancelled_status_and_null_anchor
test_validator_rejects_unknown_schedule_status
test_revision_available_at_uses_payload_first_observed_for_in_place_edit
test_same_semantic_different_payload_variant_does_not_reapply
test_multi_symbol_batch_restart_emits_only_missing_rows
test_exact_all_symbols_statement_never_partially_emits
test_late_same_time_conflict_reaches_1_5f_fail_closed_selector
test_runtime_gate_reports_supported_enabled_health_separately
test_schedule_revision_lookback_config_required
```

---

## 18. Resolved Design Questions

```text
Q1: current root or historical index?
A1: versioned formal launch identity index only. Current root rows may enter the index after formal v2 validation; scheduler state cannot.

Q2: diagnostics only or counters?
A2: both. JSONL stores evidence; runtime gate/summary stores bounded counters and samples.

Q3: cancelled revision handling?
A3: pending stops before activation; active continues read-only but contaminated; completed is invalidated by 1.5G lineage review.
```

---

## 19. Safety Invariants

```text
1. Producer uncertainty never creates formal revision row.
2. Non-linked revision never calls formal row builder.
3. L4 symbol-only inference is diagnostic-only.
4. Scheduler state is never formal linking evidence.
5. Revision available time is payload-version point-in-time safe.
6. Normal formal v2 launch collection continues even if revision producer is blocked.
7. All paper/live/execution/alpha flags remain false.
```
