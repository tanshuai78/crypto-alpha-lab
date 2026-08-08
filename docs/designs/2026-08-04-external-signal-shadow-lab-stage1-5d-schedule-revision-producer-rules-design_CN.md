# Stage 1.5D Schedule Revision Producer Rules Design

**日期:** 2026-08-04，2026-08-07 修订，2026-08-08 completion-audit 修订
**关联主设计:** `docs/designs/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-launch-time-priority-anchor-precedence-hotfix-design_CN.md`
**关联实现计划:** `docs/plans/2026-08-07-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-and-1-5f-lineage-closure-implementation-plan_CN.md`
**范围:** Stage 1.5D schedule revision producer、Stage 1.5F/1.5G formal v2 lineage prerequisite、只读离线 salvage audit
**状态:** completion audit found producer/lineage wiring incomplete; corrective plan must be approved before implementation resumes

---

## 1. Current Decision

```text
decision = stage1_5d_schedule_revision_producer_rules_revised_pending_plan_approval
producer_policy_version = linked_only_formal_v2
schedule_revision_producer_supported = design_defined
schedule_revision_producer_enabled = false
schedule_revision_consumer_prerequisites_verified = required_before_enablement
offline_salvage_mode = readonly_nonproduction_audit_only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

本设计先关闭 KOUSDT/RDDTUSDT 暴露的 formal v2 lineage drop，再实现自动 revision producer。任何一部分的不确定性都只能阻断 revision formal emission，不能阻断正常 formal v2 launch collection。

---

## 2. Confirmed Facts And Root Cause

1. 2026-08-06 的 KOUSDT/RDDTUSDT Stage 1.5D event 已是 `formal_event_contract_version = 2`、`source_contract_status = formal_v2_valid`、official-schedule anchor valid。
2. Stage 1.5F 的 `flatten_event_symbols()` 保留原 event row，但 pending/active state 与 accepted-row builder 未完整持久化 source/anchor lineage，导致 1.5G 只能得到 `launch_time_only`。
3. v2 anchor contract 已有 `source_anchor_contract_hash`、`admission_anchor_contract_hash`、`latest_anchor_contract_hash`、contract version、precedence policy、evidence class 与 contamination 字段；1.5G formal recognition 必须使用它们，而不是只检查若干 provenance 字符串。
4. 现有 revision builder/consumer 仍混合 semantic identity 与 payload identity，且 current-poll in-memory linking、root-local index、in-place edit time 和 late-conflict transport 均未形成完整 contract。
5. completion audit 确认：helper 可独立通过单元测试，但若 Stage 1.5D poll runner 未在 listing -> detail -> durable launch/index -> revision emission 的实际路径调用它，则 producer 未实现；runtime gate 不得仅因模块存在而宣称 producer supported/healthy。
6. completion audit 确认：readonly salvage 若未读取并校验指定 source event、accepted row 与 latest state 的真实 JSONL 输入，就不得输出 pass；静态 manifest 不是 audit evidence。

---

## 3. Scope And Non-Goals

### 3.1 In Scope

- formal v2 launch lineage 在 1.5F state、accepted/reconcile artifact 与 1.5G review 中的端到端一致性。
- Stage 1.5D listing pre-classifier、mandatory detail lifecycle、payload-version time registry、curated formal launch identity snapshot、linked-only revision transport。
- Stage 1.5F semantic idempotency、cancellation/late-conflict fail-closed handling。
- KO/RDDT 只读离线 lineage salvage audit。

### 3.2 Explicit Non-Goals

- 不启用 paper/live/execution/alpha，不读取私有 API，不增加订单、仓位或账户依赖。
- 不回写旧 root，不修改现有 accepted/state/snapshot JSONL，不以 salvage 制造 clean/formal evidence。
- 不接受 title-only revision、L4 symbol-only linking、scheduler state、模糊语义匹配或任意 historical data scan 作为 formal linking evidence。
- 不新增数据库、通用 migration framework、generic revision engine、人工审核 UI 或 conflict transport event type。

---

## 4. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| `INV-C1` | 一个 v2 source contract 必须在 1.5F admission、accepted、latest/completed state 与 1.5G formal recognition 中保持可验证的一致谱系。 |
| `INV-C2` | Offline salvage 是非生产只读 audit；它不得改变 production formal count、clean pass、evidence label 或原 artifact。 |
| `INV-P1` | 只有 detail-confirmed、L1/L2/L3 uniquely linked、contract-valid、point-in-time valid 的 revision 可 formal emit。 |
| `INV-P2` | 同 poll launch 只有 event row 与 formal identity index 均已应用层持久化后才 linkable。 |
| `INV-P3` | 跨 root linking 只使用 operator-explicit、版本化、带 manifest 的 curated identity snapshot；不得隐式扫描 `data/`。 |
| `INV-P4` | `revision_available_at_ms` 永远等于该 raw payload version 的首次观测时间，并在 restart 后不变。 |
| `INV-P5` | 新 revision contract row 必须令 `revision_id == revision_semantic_id == revision_application_id`。 |
| `INV-P6` | 合法 late equal-time conflict 必须 transport 到 1.5F；1.5F 不得静默采用先到 revision。 |
| `INV-P7` | 新 producer 只发 `formal_schedule_revision_contract_version = 2`；只有 version 1 artifact 可使用 legacy application-id fallback。 |
| `INV-S1` | producer effective enablement 需要可验证的 consumer prerequisite attestation；缺失时 fail closed。 |
| `INV-W1` | revision producer 必须由 Stage 1.5D production poll 的真实 listing/detail 生命周期调用；孤立 helper、fixture 或 summary 字段均不构成实现证据。 |

---

## 5. Formal V2 Consumer Prerequisite Gate

### 5.1 Strict Production Lineage Gate

当 accepted event 或 latest state 声明 `formal_event_contract_version = 2` 或 `anchor_contract_version = 2` 时，1.5G 只能在以下条件全部满足时将其计入 `formal_announcement_and_launch_count`：

```text
accepted.formal_event_contract_version == 2
latest.anchor_contract_version == 2
accepted.anchor_precedence_policy == latest.anchor_precedence_policy
  == official_schedule_priority_v1
accepted.source_contract_status == formal_v2_valid
accepted.launch_anchor_evidence_level == official_schedule
latest.latest_anchor_evidence_level == official_schedule
accepted.effective_observation_anchor_source == official_schedule_anchor
accepted.source_article_id is non-empty
accepted.source_anchor_contract_hash is non-empty
accepted.source_anchor_contract_hash == latest.source_anchor_contract_hash
accepted.admission_anchor_contract_hash == latest.admission_anchor_contract_hash
latest.observation_anchor_revision_contaminated is false
latest.latest_max_evidence_class == clean_or_recovery
```

若存在单独 completed state，则还必须满足：

```text
latest.latest_anchor_contract_hash == completed.latest_anchor_contract_hash
```

任一缺失或不一致：

```text
formal_announcement_and_launch_count += 0
blocker = formal_v2_lineage_incomplete_or_mismatch
```

旧 schema / legacy root 没有 v2 declaration 时维持现有兼容逻辑；新 schema 写出的 v2 state 缺字段则是 corruption，不得按 legacy 降级。

### 5.2 State Schema Boundary

`EventSymbolState` 增加显式 schema version。旧 state 缺 version/字段可按旧 schema 默认值读取；新 schema 的 v2 state 必须持久化完整 contract 字段。`from_dict()` 仍过滤未知字段，保证前后兼容而不掩盖新 schema 的缺失 lineage。

### 5.3 Effective Producer Enablement

```text
configured_producer_enabled = config flag
effective_producer_enabled = configured_producer_enabled
  AND prerequisite_commit_sha == running_commit_sha
  AND prerequisite_suite_passed == true
  AND real_aia_fixture_verified == true
```

任何 prerequisite metadata 缺失、commit 不一致或 fixture 未验证时，`effective_producer_enabled = false`，runtime health 为 `blocked`；正常 launch collection 继续。

---

## 6. Offline Evidence Salvage Boundary

KO/RDDT salvage 是一个独立 audit，不是 1.5G production review 的输入覆盖层。

```text
input = immutable local 1.5D event JSONL + immutable local 1.5F accepted/state JSONL
operation = exact (event_id, symbol) lineage comparison
output = formal_lineage_salvage_manifest.json + nonproduction audit report
salvage_mode = readonly_lineage_reconciliation
```

允许证明：指定 1.5D event、每个 `(event_id, symbol)` accepted row 与 latest state 在 source event identity、article id、formal version、anchor policy、source/admission hash 上一致，或明确输出哪个输入/字段缺失或不一致。

每次 audit 必须：

```text
1. 显式接收本地 1.5D event glob、1.5F accepted glob、1.5F observer-state glob；不得猜测或扫描其他 root。
2. 仅选择 article 307687ad279e42e6909ee1be8c472b50 与 KOUSDT/RDDTUSDT。
3. 对每个实际读取的文件和每个匹配 JSONL row 记录 SHA-256、路径、行号与解析结果。
4. 对两 symbol 全部成功才输出 pass；无匹配、重复匹配、缺 state 或任一不一致必须输出 failed。
5. 写 manifest 与 Markdown report 前后再次比较输入文件 SHA-256，证明没有写入输入。
```

不允许：

```text
- 改写 accepted/state/snapshot/watermark 或创建派生 state overlay
- 改变 evidence_label
- 改变 formal_announcement_and_launch_count
- 将 clean_depth_evidence_pass 从 false 改为 true
- 将 launch_time_only 解释为 announcement_and_launch_time
```

结果仅能是：

```text
stage1_5g_formal_lineage_salvage_audit_pass
stage1_5g_formal_lineage_salvage_audit_failed
```

其报告必须明确 `nonproduction_audit_only = true`。该任务不需要复制整 root，也不需要 `cp -al`。

---

## 7. Revision Candidate And Mandatory Detail Lifecycle

### 7.1 Listing Pre-Classifier

增加只具有 scheduling authority 的函数：

```python
classify_schedule_revision_detail_candidate_from_listing(
    title: str,
    source_category: str,
    source_article_id: str,
) -> bool
```

它只允许在 futures-launch context 下，以 `postpone`、`reschedule`、`delay`、`cancel`、`not proceed`、`instead of` 等 bounded cue 进入：

```text
detail_work_type = launch_schedule_revision_detail
```

它不得决定 intent、supersedes、anchor 或 formal emission。plain launch、API maintenance、funding/settlement delay 必须不入队。

### 7.2 Detail Classifier

只有可信 BAPI detail 才能产生：

```text
revision_intent =
  rescheduled_with_new_anchor
  postponed_without_anchor
  cancelled
  not_revision
  ambiguous_revision_intent
```

detail HTTP failure/empty/202 是 pending retry；max-age exceeded 是 terminal diagnostic；ambiguous 是 diagnostic-only。

### 7.3 Production Poll Integration Boundary

producer 不是一个可选的 post-processing helper。配置的 producer effective enablement 为 true 时，Stage 1.5D 的**同一个 poll** 必须按以下实际调用顺序执行；任一边界未执行则 `producer_health = blocked`，不得 formal emit：

```text
listing row
  -> bounded pre-classifier
  -> existing detail-retry scheduler work item (detail_work_type = launch_schedule_revision_detail)
  -> trusted BAPI detail result
  -> detail classifier / symbol and supersedes extraction
  -> load only current durable index + explicit snapshot
  -> point-in-time linker
  -> all-or-none batch validation
  -> append formal schedule revision rows or diagnostic JSONL
  -> persist/rebuild restart state and counters
```

launch rows and revision rows share the existing `events/*.jsonl` transport, distinguished by `event_type`; no second runtime loop or polling process is introduced. `append_formal_schedule_revision()` is the only revision writer. The runner must pass the producer-supplied `revision_application_id` unchanged to Stage 1.5F through that transport.

---

## 8. Formal Launch Identity Index And Cross-Root Snapshot

### 8.1 Index Rows

唯一 formal linking source 是 validator-approved formal v2 launch identity row。每条 row 至少包括：

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
identity_first_observed_at_ms
formal_row_durable_at_ms
event_id
payload_sha256
```

不得把 scheduler state 转化为 index identity。

### 8.2 Curated Snapshot Contract

新 root 如需 14-day lookback，必须由 operator 显式提供：

```text
--formal-launch-identity-index-snapshot <approved-path>
```

snapshot manifest 必须有：

```text
index_schema_version
index_built_at_ms
index_content_sha256
source_root_ids
source_root_commit_shas
source_index_paths
```

snapshot 只含已验证 source root 的 immutable index rows。无 snapshot 时，producer 可以只使用当前 root 已持久化 index；跨 root link 不可用并写 `orphaned`/coverage diagnostic。禁止递归或通配扫描任意 `data/` root。

### 8.3 Index Validity And Collision

```text
index missing/schema/hash invalid -> producer health = blocked
same source_article_id + symbol with different source_anchor_contract_hash -> collision
same stable launch identity with multiple event_ids -> collision
same index identity with different official anchor -> collision
any collision -> `index_collision`; producer health = blocked; revision formal emission disabled; normal launch unaffected
```

---

## 9. Durable Poll Ordering And Crash Recovery

`current_poll_launch_valid` 不等于 `current_poll_launch_linkable`。同 poll 的安全顺序是：

```text
1. parse and validate candidate launch rows
2. append/close formal launch event rows
3. append/close formal launch identity index rows
4. rebuild/verify index from durable streams if prior crash left a gap
5. expose only durable identities to revision linker
6. classify detail-confirmed revision candidates
7. emit validated revision rows and diagnostics
8. persist/reconcile batch state
```

若 crash：

```text
before launch append -> dependent revision must never emit
after launch append before index append -> restart rebuilds missing index, then may link later
after first multi-symbol revision append -> restart emits only missing semantic rows
```

应用层 durable 定义为 append operation 成功并关闭文件；本设计不声明电源故障级 storage guarantee。

---

## 10. Linking And Point-in-Time Rules

允许 formal linking 的 L1/L2/L3：

```text
L1: explicit original source_article_id, unique index hit
L2: explicit original URL/title/canonical slug, unique index hit
L3: symbol + explicit superseded official anchor, unique matching formal v2 identity
```

每一 index hit 必须同时满足：

```text
original.identity_first_observed_at_ms <= revision_available_at_ms
original.formal_row_durable_at_ms <= revision_available_at_ms
revision_available_at_ms - original.identity_first_observed_at_ms <= lookback_days
```

`source_published_at_ms` 只保留为 provenance，不是 linking 的 point-in-time proof。

L4 symbol-only uniqueness、缺 index、multiple index hit、outside lookback、invalid index 均不得 formal emit。

---

## 11. Payload-Version Time And Identity

持久化 payload-version registry：

```text
source_article_id
raw_payload_sha256
payload_version_first_observed_at_ms
source_published_at_ms
last_observed_at_ms
```

规则：

```text
first observation of (source_article_id, raw_payload_sha256):
  payload_version_first_observed_at_ms = detected_at_ms
same pair after restart:
  retain first-observed time
revision_available_at_ms = payload_version_first_observed_at_ms
```

原始 publish time 永远不得回填或 backdate later payload edit。registry 必须是 current root 的 append-only JSONL/state artifact；restart 从该 artifact 重建，不能以默认 hash、当前时间或 source publication time 代替缺失 version record。

```text
revision_semantic_id = sha256(
  source_article_id | symbol | revision_intent | revised_anchor_ms | supersedes_source_article_id
)
revision_payload_hash = sha256(canonical_revision_evidence_dict)
revision_payload_version_id = sha256(source_article_id | raw_payload_sha256)
revision_observation_id = sha256(
  revision_semantic_id | revision_payload_version_id | revision_available_at_ms
)
revision_id = revision_semantic_id
revision_application_id = revision_semantic_id
formal_schedule_revision_contract_version = 2
```

新 contract row 缺少其中任一 required identity 或三者不相等时 validator 必须失败。v2 是 strict semantic transport；仅 `formal_schedule_revision_contract_version = 1` 的既有 artifact 可走 legacy application-id fallback。1.5F v2 production root 必须显式允许 `[1, 2]`，并在收到 v2 row 时拒绝缺失 strict 字段的 row，而不是回退。

---

## 12. Formal Revision Row, Batch And Late Conflict

### 12.1 Explicit Builder Inputs

builder 只接受 Producer 已确认的：

```text
revision_intent
link_status = linked
revision_semantic_id
revision_application_id
revision_id
revision_payload_version_id
revision_observation_id
revision_available_at_ms
```

`link_status != linked` 不得调用 builder。status 映射：

```text
rescheduled_with_new_anchor -> rescheduled + non-null anchor
postponed_without_anchor -> postponed_without_anchor + null anchor
cancelled -> cancelled + null anchor
```

### 12.2 Multi-Symbol Batch

exact-per-symbol statement 可按已明确的 symbol 独立 emit。exact-all-symbols statement 必须所有目标 symbol 均完成同一规则的 valid link；否则一个 formal row 也不写。

### 12.3 Late Equal-Time Conflict Transport

若 revision B 自身仍为 official、linked、contract-valid、point-in-time-valid，即使与已 emit revision A 同 stable identity、同 `revision_available_at_ms`、不同 status/anchor，也必须写 formal B row，并标记 producer late-conflict diagnostic/counter。

1.5F 收到 v2 row 后必须原样读取 transport row 的 `revision_application_id`；只有 `formal_schedule_revision_contract_version = 1` 的 legacy artifact 才能调用旧的 payload-hash application-id 算法。收到两者后必须进入：

```text
pending_official_schedule_conflict
active_anchor_revision_contaminated
completed_anchor_revision_contaminated
```

不得因 B 是 late conflict 而在 1.5D suppress transport。

---

## 13. 1.5F Cancellation And 1.5G Review Semantics

```text
pending + cancelled -> pending_cancelled; no promotion
active + cancelled -> keep read-only snapshot collection to original end; contaminate lineage
completed + cancelled -> do not reopen; contaminate/invalid lineage
```

1.5G 对 v2 evidence 必须使用 Section 5 的 strict lineage gate。conflict、contamination、missing state 或 hash mismatch 都不能得到 formal count。

---

## 14. Diagnostics, Runtime And Safety

诊断至少记录 source article、symbol、intent、link evidence、index manifest/hash、payload/version time、durable/index time、producer decision 与 collision/conflict reason。summary/runtime gate 至少记录：

```text
schedule_revision_candidate_count
schedule_revision_detail_pending_count
schedule_revision_linked_emit_count
schedule_revision_orphaned_diagnostic_count
schedule_revision_ambiguous_diagnostic_count
schedule_revision_out_of_scope_count
schedule_revision_payload_variant_count
schedule_revision_late_conflict_count
schedule_revision_index_collision_count
schedule_revision_producer_supported
schedule_revision_producer_enabled
schedule_revision_producer_effective_enabled
schedule_revision_consumer_prerequisites_verified
schedule_revision_producer_health
```

`health = blocked` 只禁止 revision formal emission，不改变 normal 1.5D runtime READY 或交易权限。

`schedule_revision_producer_supported = true` 只表示当前 build 含有实现；`schedule_revision_producer_effective_enabled = true` 还必须证明 Section 5.3 prerequisite 已通过且 Section 7.3 的 runner integration health 为 `ready`。任何字段不得由默认 `ctx.get(..., false)` 伪造为已验证。

---

## 15. Required Evidence And Tests

Fixtures:

```text
- KO/RDDT real observed formal-v2 event-row extract with provenance
- real frozen AIA postponement BAPI fixture; absence remains producer-enable blocker
- L1/L2/L3/L4, cancellation, exact-per-symbol, exact-all-symbols
- in-place payload edit, restart payload replay, late equal-time conflict
- cross-root curated identity snapshot and collision fixture
```

Required regressions include:

```text
test_formal_v2_lineage_requires_hash_state_and_contamination_consistency
test_new_v2_state_missing_lineage_is_blocked_but_legacy_state_is_compatible
test_accepted_reconcile_after_crash_preserves_normal_lineage
test_salvage_audit_never_changes_production_formal_count_or_clean_pass
test_aia_title_enters_revision_detail_queue
test_preclassifier_never_formal_emits
test_revision_cannot_link_to_non_durable_same_poll_launch
test_crash_after_launch_append_before_index_append_rebuilds_index
test_crash_before_launch_append_never_emits_dependent_revision
test_cross_root_snapshot_requires_manifest_and_is_point_in_time_safe
test_index_collision_blocks_revision_not_normal_launch
test_in_place_edit_available_at_is_payload_version_first_seen
test_restart_does_not_reset_payload_version_first_seen
test_new_revision_row_requires_revision_application_id
test_payload_variant_does_not_change_application_id
test_late_equal_time_conflict_is_emitted_and_reaches_1_5f
test_exact_all_symbols_statement_writes_zero_formal_rows_when_one_symbol_fails
test_runner_preclassifier_enqueues_revision_detail_and_emits_linked_revision
test_runner_keeps_normal_launch_when_revision_producer_is_blocked
test_salvage_audit_fails_without_real_matching_input_rows
test_v2_formal_count_rejects_missing_or_mismatched_policy_or_hash
```

---

## 16. Rollout And Rollback

```text
1. Deploy with configured_producer_enabled = false.
2. Verify consumer gate, real AIA fixture, current commit attestation and runtime fields.
3. Configure an explicit curated identity snapshot before any cross-root coverage claim.
4. Enable only through a separately approved config change.
5. If health becomes blocked/degraded, set effective producer emission to false; retain normal launch collection and diagnostics.
6. Rollback is a new disabled root; never rewrite old roots.
```

---

## 17. Resolved Questions

```text
Q1: Can same-poll in-memory launch identity link a revision?
A1: No. It becomes linkable only after launch event and index row are durably written.

Q2: Can salvage turn KO/RDDT into production formal evidence?
A2: No. It is a separate readonly audit with a separate decision namespace.

Q3: How does a new root see a prior-root launch?
A3: Only through an operator-explicit, manifest-verified curated identity snapshot.

Q4: What is revision availability for a later article edit?
A4: The first observation time of that exact raw payload version, persisted across restart.
```
