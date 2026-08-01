# Stage 1.5D / 1.5F Title-Symbol Launch-Anchor Validation Gate Hotfix Design

```text
status = design_revised_after_external_review
scope = stage1_5d_1_5f_title_symbol_launch_anchor_validation_gate_hotfix
trigger_incident = 2026-07-31_grvtusdt_title_symbol_prelaunch_hard_reject
implementation_allowed = false
implementation_plan_allowed = after_design_review_only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

## 0. 外部审核修订摘要

本版采纳 2026-08-01 design review 的 P0 反馈，并修正以下边界：

```text
1. `symbol_not_in_exchangeinfo` 不再作为跨阶段通用 terminal reason。
2. launch 后 recovery window 内 exchangeInfo 仍未出现 symbol 时，必须继续 pending，不得 hard reject。
3. capacity/budget check 必须在 event 已通过 source contract、anchor、exchangeInfo/product validation 与 clean/recovery age eligibility 后执行。
4. 1.5D formal event contract 改为 versioned、per-symbol、fail-closed。
5. 1.5D 所有 `events/*.jsonl` formal append 必须物理集中到唯一 writer。
6. title-known article 强制进入 detail/validation flow 后，scheduler 必须有 lane/fairness/first-attempt SLA，避免新 backlog/starvation。
7. source-ingestion watermark 与 accepted/admission counters 明确分离。
8. postpone / delayed / rescheduled notice 不得作为新的 launch event。
```

## 1. 背景

Stage 1.5D 负责从 Binance 官方公告中发现 futures contract launch event，解析 `symbols`、正文 detail、per-symbol launch/onboard anchor，并输出 `events/*.jsonl`。Stage 1.5F 消费这些 event rows，按 `event_symbol_id` / `stable_event_symbol_key` 做 live depth observation admission，并在 launch anchor 后采集 12h public depth snapshots。

2026-07-31 发生新的生产事故：

```text
article_id = 20536b05b2a34b87a3bae99c45d0dc91
symbol = GRVTUSDT
title = Binance Futures Will Launch USDⓈ-Margined GRVTUSDT Perpetual Contract (2026-07-31)
source_published_at_ms = 1785497411662
detected_at_ms = 1785497559218
exchangeinfo_onboardDate = 1785501900000
launch_utc = 2026-07-31T12:45:00Z
```

公告标题已包含 `GRVTUSDT`。Stage 1.5D 因 title parser 已解析出 symbol，直接走 `detail_fetch_status = not_needed` 快路径并写入 `events/*.jsonl`。该 event row 缺少：

```text
symbol_validation_status
symbol_effective_launch_times_ms
symbol_onboard_times_ms
launch_time_source
detail/BAPI payload provenance
```

Stage 1.5F 于 `2026-07-31T11:33:36Z` 消费该 event。此时距离真实上线 `12:45:00Z` 还有约 71 分钟，Binance `exchangeInfo` 尚未包含 `GRVTUSDT`。1.5F 当前 admission 顺序先判断 `symbol not in exchangeInfo`，再判断 anchor missing / anchor future，最终写入 terminal rejected：

```text
status = rejected
rejected_reason = symbol_not_in_exchangeinfo
```

当 `GRVTUSDT` 于 `12:45:00Z` 正式变为 `TRADING` 后，1.5F 已有 `status = rejected` terminal state，后续 revision/retry 被 `terminal_revision_seen` 抑制，无法恢复 observation。

本事故证明：上一轮 BAPI parser、多 symbol all-or-none、launch-time gated observation hotfix 仍未覆盖 single-symbol title 快路径。

## 2. 输入审计结论

本设计基于以下审计文件与服务器证据：

```text
docs/reviews/2026-08-01-binance-futures-announcement-shape-audit_CN.md
docs/reviews/2026-08-01-stage1-5d-evidence-contract-audit_CN.md
docs/reviews/2026-08-01-stage1-5d-1-5f-regression-fixture-audit_CN.md
docs/reviews/2026-08-01-stage1-5f-admission-defense-audit_CN.md
_project_context/server_evidence/20260801_grvt_title_gate/
```

审计确认的事实：

```text
1. Binance single-symbol title launch 公告普遍可能早于真实上线时间发布。
2. Stage 1.5D 当前 title-symbol path 可以无 detail、无 launch anchor、无 exchangeInfo validation 直接 emit。
3. Stage 1.5F 当前在 anchor missing/future 判断前先执行 exchangeInfo symbol presence hard reject。
4. Stage 1.5F terminal rejected state 会阻止后续 revision/recovery。
5. 临时 capacity/budget exceeded 不应作为 event terminal rejected。
6. 现有 regression fixture 缺少 GRVT 这类 single-symbol title prelaunch 事故样本。
```

## 3. 当前根因

### 3.1 Stage 1.5D title-symbol 快路径破坏 formal evidence contract

当前 collector 在公告列表 poll 后，如果 `ev.get("symbols")` 非空，会直接：

```text
normalize_live_event(...)
append_jsonl(stream_paths["events"], norm_event)
```

`normalize_live_event()` 的默认 metadata 是：

```text
symbol_extraction_source = title
detail_fetch_attempted = false
detail_fetch_status = not_needed
symbol_parse_status = parsed
```

这对历史 price-replay 阶段可接受，但对 Stage 1.5F formal live depth evidence 不再安全。原因是 `title has symbol` 只证明“候选 symbol 可见”，不能证明“合约已经上线”或“可开始 depth observation”。

### 3.2 Stage 1.5F admission 防御顺序错误

当前 1.5F admission 大致顺序是：

```text
identity/event_type/watermark
exchangeInfo available
symbol in exchangeInfo
budget
anchor conflict/missing/future
eligible
```

这会在 pre-launch 正常状态下误杀新币。正确顺序必须是：

```text
identity/event_type/watermark
resolve anchor and evidence contract
anchor conflict/missing/future -> pending
exchangeInfo available
symbol/product validation
clean/recovery age eligibility
capacity/budget check -> pending if deferred
start observation / timeout rejected
```

### 3.3 Terminal rejected 不可恢复

`symbol_not_in_exchangeinfo` 在 anchor missing/future 以及 launch 后 recovery window 内不是确定性非法事件，而是“可能太早或 exchangeInfo 尚未同步”。将其写入 `status = rejected` 会导致：

```text
existing.status == rejected
-> classify_event_symbol_revision_admission returns terminal_revision_seen
-> later valid exchangeInfo / 1.5D revision ignored
```

### 3.4 Capacity exceeded 被错误建模为事件非法

如果 `can_start_new_observation(...)` 返回 false，当前 runner 将 `status = rejected`、`reason = budget_exceeded`。这是系统资源暂时不足，不是 event-symbol 非法。应进入 capacity pending 队列。

### 3.5 Fixture 缺口导致只能等待真实事件暴露问题

已有 A827 / f434 / d0833 / 6cbb / 93b5 覆盖了 BAPI table、HTTP 202、degraded endpoint、USD1、multi-symbol all-or-none，但没有覆盖：

```text
single-symbol title contains symbol
announcement published before launch
1.5D emits unanchored event
1.5F sees symbol missing before onboardDate
```

GRVT 必须冻结为 regression。

## 4. 设计目标

必须实现：

```text
1. 1.5F 下游防御先落地：任何 unanchored/future-anchor/recovery-window 内 event 不得因为 exchangeInfo 缺失被 terminal rejected。
2. 1.5D 源头收口：futures_contract_launch 的 title symbol 只能作为 candidate，不得作为 formal emit 条件。
3. 所有 consumable 1.5D event 必须携带 launch/onboard anchor 或明确 non-consumable diagnostic。
4. 1.5D single-symbol 与 multi-symbol 共享同一 candidate -> detail/BAPI -> exchangeInfo validation -> emit contract。
5. 1.5F 的 exchangeInfo symbol missing 只允许在 launch anchor 已到、并超过 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS` 后 hard reject。
6. 1.5F 的 capacity/budget exceeded 必须 pending，不得 terminal reject。
7. GRVT 事故必须被 fixture 化，后续本地测试可复现，不再等待真实公告。
8. 旧污染 root 不补 clean evidence，不回写旧 observations。
```

非目标：

```text
不改变 Stage 1.5G clean/quarantine 阈值。
不补录 GRVT 为 clean evidence。
不修改 Stage 1.5E execution feasibility。
不改变 `RISK_LIVE_TRADING_ENABLED = False`。
不新增交易信号、paper trading、live trading 或 execution permission。
不做全量 Binance 公告历史 parser 重构。
```

## 5. 核心设计原则

### 5.1 Title symbol 是 candidate，不是 formal evidence

`symbol_extraction_source = title` 的含义调整为：

```text
title provided candidate symbol identity only
```

不得再隐含：

```text
detail_fetch_status = not_needed
launch_anchor_verified = true
exchangeInfo visibility verified = true
```

### 5.2 Launch anchor 优先于 exchangeInfo presence reject

对 futures launch observation，`exchangeInfo` 缺失至少有三种语义：

```text
1. launch anchor 之前：正常 pre-listing 状态，应 pending。
2. launch anchor 之后、recovery window 内：exchangeInfo 可能尚未同步，应 pending。
3. launch anchor 之后超过 recovery window：异常，应 timeout rejected/diagnostic。
```

因此 1.5F 必须先解析 `observation_anchor_ms`，再判断是否允许 hard reject。

### 5.3 Temporary system capacity is pending, not event invalidity

`budget_exceeded` / capacity exhausted 只说明当前 poll 无法启动新的 observation，不说明 event-symbol 不合法。应使用：

```text
pending_observation_capacity
```

并保留 retry cadence、defer count、next check time。

### 5.4 Formal event 与 diagnostic event 分离

1.5D `events/*.jsonl` 是 1.5F 的 formal input。缺少 anchor 的 title-only candidate 不应进入同一 formal stream，除非明确标记为 non-consumable 且 1.5F 硬拒绝消费。

第一版优先策略：

```text
缺少 anchor -> 留在 scheduler pending / diagnostics
不写 consumable events row
```

不优先引入新的 `events_candidates/*.jsonl`，避免扩大接口面。

## 6. Stage 1.5F 防御层设计（Phase A）

Phase A 目标是即使 1.5D 仍输出坏 event，1.5F 也不能永久误杀。

### 6.1 Source contract triage and admission decision order

Phase A 必须先于 Phase B 部署。部署 Phase A 时，上游 1.5D 仍可能产生旧格式 event：

```text
missing formal_event_contract_version
missing formal_event_consumable_by_stage1_5f
missing symbol_identity_validation_status
missing launch anchor
```

因此 Phase A 的 `formal source contract check` 不得实现成“旧格式直接 terminal reject”。必须先做三态/四态 source contract triage：

```text
source_contract_status = formal_v1_valid
  -> 可以进入完整 admission 流程

source_contract_status = legacy_unvalidated_recoverable
  -> 可以建立 durable pending state
  -> 不得 active
  -> 不得 accepted
  -> 不得 clean/recovery evidence
  -> 等待同 stable_event_symbol_key 的 formal v1 validated revision

source_contract_status = explicit_non_consumable
  -> diagnostic_only / terminal non-consumable
  -> 不进入 observation pending

source_contract_status = malformed
  -> diagnostic_only / terminal malformed
  -> 不进入 observation pending
```

推荐判定顺序：

```text
1. normalize_event_symbol_identity
2. event_type == futures_contract_launch
3. resolve_depth_observation_anchor_ms for diagnostics only
4. historical / pre-watermark classification
5. source contract triage
6. anchor conflict -> pending_anchor_conflict
7. anchor missing -> pending_launch_anchor_missing
8. anchor future -> pending_launch_time_in_future
9. exchangeInfo unavailable -> pending_exchangeinfo_unavailable
10. exchangeInfo symbol/product validation
11. symbol missing within recovery window -> pending_exchangeinfo_symbol_not_visible_after_anchor
12. symbol missing after recovery deadline -> rejected_launch_symbol_not_visible_timeout
13. clean/recovery age eligibility
14. capacity/budget check -> pending_observation_capacity
15. start observation
```

`source contract triage` 不得在 historical / pre-watermark classification 之前创建 pending state。否则旧 pre-bootstrap unversioned rows 可能被错误写入 pending，而不是 historical ignore。

`capacity/budget` 不得早于 exchangeInfo symbol/product validation。只有已经满足 observation eligibility 的 event-symbol，才允许因为系统容量不足进入 `pending_observation_capacity`。否则容量不足会掩盖非法 product/symbol，并长期污染 pending queue。

必需测试：

```text
test_legacy_unversioned_post_watermark_event_becomes_pending_not_rejected
test_legacy_unversioned_pre_watermark_event_is_ignored_not_pending
test_explicit_non_consumable_event_never_enters_observation_pending
test_formal_contract_check_cannot_terminal_reject_recoverable_legacy_event
```

### 6.2 ExchangeInfo symbol visibility invariant

INVARIANT:

```text
`symbol_not_in_exchangeinfo` is a deprecated legacy reason.
New Stage 1.5F roots must never emit it.
```

新代码唯一允许的 symbol-visibility terminal reason：

```text
rejected_launch_symbol_not_visible_timeout
```

且必须同时满足：

```text
observation_anchor_ms is not None
source_contract_status == formal_v1_valid
exchangeInfo request succeeded
symbol absent
now_ms > observation_anchor_ms + EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS + EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS
```

对于 unanchored event：

```text
symbol_not_in_exchangeinfo = impossible
rejected_launch_symbol_not_visible_timeout = impossible
```

不得继续使用模糊的 `symbol_not_in_exchangeinfo` 作为所有阶段共用的 terminal reason。必须按时间阶段区分：

```text
anchor missing
-> pending_launch_anchor_missing

now_ms < observation_anchor_ms + EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS
-> pending_launch_time_in_future

exchangeInfo request unavailable / failed
-> pending_exchangeinfo_unavailable

exchangeInfo success but symbol missing
AND now_ms <= observation_anchor_ms + EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS + EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS
-> pending_exchangeinfo_symbol_not_visible_after_anchor

exchangeInfo success but symbol missing
AND now_ms > observation_anchor_ms + EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS + EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS
-> rejected_launch_symbol_not_visible_timeout
```

当前配置边界：

```text
EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS = 0
EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS = 120_000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS = 900_000
```

必需测试：

```text
test_symbol_missing_at_anchor_stays_pending_within_recovery_window
test_symbol_appears_five_minutes_after_anchor_promotes_recovery
test_symbol_missing_after_recovery_deadline_becomes_terminal
test_anchor_missing_matrix_never_returns_exchangeinfo_missing_terminal_reason
test_stage1_5f_production_code_has_no_symbol_not_in_exchangeinfo_return
```

旧 reason 只能保留在：

```text
legacy artifact parser
migration/reporting
historical fixture
```

### 6.3 Legacy / unvalidated event handling

若 1.5D event 缺少 formal validation fields：

```text
formal_event_contract_version != 1
formal_event_consumable_by_stage1_5f is not true
symbol_identity_validation_status != validated_by_exchangeinfo
symbol_effective_launch_times_ms missing symbol
observation_anchor_ms unresolved
```

则：

```text
source_contract_status = legacy_unvalidated_recoverable
pending_source_event_unvalidated = true
required_source_revision = formal_v1_validated_launch_anchor
```

Phase A 对此类 event 的职责严格限定为：

```text
防止误杀
保存可恢复 durable pending state
记录 anchor candidates / exchangeInfo enrichment diagnostics
不创建新的 source validity
```

Legacy/unvalidated source event 即使后来从 exchangeInfo 看到 `symbol` 与 `onboardDate`，也只能 enrich pending state：

```text
legacy/unvalidated source event
+ exchangeInfo onboardDate
-> update anchor candidates
-> keep pending_source_event_unvalidated = true
-> do not active
-> do not accepted
-> do not clean/recovery evidence
```

只有收到同 `stable_event_symbol_key` 的 formal v1 validated revision 才能进入 eligible。第一版不提供 legacy compatibility override。若未来需要 override，必须单独设计，并且只能产生 `recovery_validation_only`，不得作为 1.5G clean/formal evidence。

如果达到 anchor resolution deadline 仍无 formal revision / anchor：

```text
status = rejected
reason = rejected_launch_anchor_unavailable_timeout
```

### 6.4 Pending state recovery allowlist

所有 pending 状态必须 restart-safe、可 recheck、可 timeout：

```text
pending_anchor_conflict
pending_launch_anchor_missing
pending_launch_time_in_future
pending_exchangeinfo_unavailable
pending_exchangeinfo_symbol_not_visible_after_anchor
pending_observation_capacity
```

每个状态必须定义：

```text
next_check_at_ms
deadline_ms
retry_count
promotion condition
terminal condition
restart behavior
```

特别是：

```text
pending_exchangeinfo_symbol_not_visible_after_anchor
-> must be selected by pending recheck loop
-> exchangeInfo symbol appears and source_contract_status == formal_v1_valid -> promote eligibility
-> timeout only after symbol_visibility_deadline_ms
```

必需测试：

```text
test_pending_exchangeinfo_symbol_not_visible_is_rechecked
test_pending_exchangeinfo_symbol_appears_then_promotes
test_pending_exchangeinfo_state_survives_restart
test_pending_exchangeinfo_state_times_out_only_after_deadline
```

### 6.5 Anchor-resolution and symbol-visibility deadlines

Anchor resolution deadline 与 clean/recovery start delay 是不同概念，不得复用 15 分钟 recovery window。

当前配置已有：

```text
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS = 6 * 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS = 2 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS = 15 * 60 * 1000
```

定义：

```text
anchor_resolution_started_at_ms = first durable registration time
anchor_resolution_deadline_ms = anchor_resolution_started_at_ms + EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS
```

正常 source revision：

```text
不重置 first_seen_at_ms
不重置 anchor_resolution_started_at_ms
不无限延长 anchor_resolution_deadline_ms
```

上游仍有 detail retry：

```text
source_retry_active = true 可记录
但不得隐式无限 pending
```

对已知 anchor 的 symbol visibility：

```text
admission_open_ms = observation_anchor_ms + EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS
symbol_visibility_deadline_ms = admission_open_ms + EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS
```

### 6.6 Capacity pending

当 observation capacity 不足时：

```text
status = pending_observation_capacity
reason = pending_observation_capacity
capacity_defer_count += 1
capacity_deferred_at_ms = now_ms
next_capacity_check_at_ms = now_ms + poll_interval_ms
```

只有当：

```text
now_ms - observation_anchor_ms > EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS
```

才允许转为 terminal diagnostic/rejected，且原因必须是 `rejected_launch_anchor_age_exceeded`，不是 `budget_exceeded`。

`capacity` pending 期间不得移动 `observation_anchor_ms` 或 `observation_window_start_ms`。

### 6.7 Summary, serializer and diagnostics

以下新增/强化状态不得只存在于内存：

```text
pending_exchangeinfo_symbol_not_visible_after_anchor
pending_source_event_unvalidated
pending_observation_capacity
```

必须进入：

```text
EventSymbolState serializer / deserializer
live_depth_observer_summary.json counters
events_pending/*.jsonl sample rows
sample-capped diagnostics
restart recovery loader
```

## 7. Stage 1.5D 源头合同设计（Phase B）

Phase B 目标是 1.5D 不再输出 unanchored formal event。

### 7.1 Versioned formal event contract

任何写入 `events/*.jsonl` 的 `futures_contract_launch` row，必须通过唯一 formal writer：

```text
append_formal_futures_launch_event(stream_paths, row_or_state, diagnostics)
```

该 writer 内部唯一调用：

```text
append_jsonl(stream_paths["events"], formal_row)
```

代码级不变量：

```text
run_stage1_5d_live_event_source_smoke_collector.py 中
append_jsonl(stream_paths["events"], ...)
只能存在于 `append_formal_futures_launch_event(...)` 一个 wrapper 内。
```

所有 scheduler / fetch / parser / max-age / cleanup 失败路径只能写 diagnostics：

```text
append_stage1_5d_diagnostic(...)
```

不得写 formal `events/*.jsonl`。必须迁移的 legacy fallback 类别包括：

```text
detail_never_attempted_budget_starved
detail_transient_timeout
detail_success_symbols_empty
max_age_exceeded
final_url_not_allowlisted
url_missing / url_not_allowlisted
```

formal event 必须 fail-closed，并带版本字段：

```text
formal_event_contract_version = 1
formal_event_consumable_by_stage1_5f = true
```

通用通过条件：

```text
symbols non-empty
source_article_id non-empty
stable_event_key non-empty
formal_event_contract_version == 1
formal_event_consumable_by_stage1_5f is true
symbol_identity_validation_status == validated_by_exchangeinfo
symbol_effective_launch_times_ms contains every emitted symbol
symbol_effective_launch_time_sources contains every emitted symbol
symbol_launch_time_candidates_ms contains every emitted symbol
launch_anchor_comparison_status contains every emitted symbol
```

anchor validation 必须按 `launch_anchor_evidence_level` 分支校验：

```text
launch_anchor_evidence_level = detail_confirmed
  detail anchor exists
  exchangeInfo identity valid
  exchangeInfo onboardDate may be absent
  launch_anchor_disagreement_ms[SYMBOL] = null if no second anchor
  launch_anchor_comparison_status[SYMBOL] = single_source_detail

launch_anchor_evidence_level = exchangeinfo_fallback
  exchangeInfo onboardDate exists
  detail attempt is auditable in request_manifest
  detail anchor absent
  detail_confirmation_missing = true
  launch_anchor_disagreement_ms[SYMBOL] = null
  launch_anchor_comparison_status[SYMBOL] = single_source_exchangeinfo

launch_anchor_evidence_level = detail_exchangeinfo_consensus
  both anchors exist
  launch_anchor_disagreement_ms[SYMBOL] is integer
  launch_anchor_disagreement_ms[SYMBOL] <= EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS
  launch_anchor_comparison_status[SYMBOL] = consensus

launch_anchor_evidence_level = conflict
  both anchors exist
  launch_anchor_disagreement_ms[SYMBOL] > EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS
  launch_anchor_comparison_status[SYMBOL] = conflict
  -> no formal emit
```

不得对 `null` disagreement 调用统一 `max()`；单源 anchor 不是“两来源完全一致”。

以下状态一律不得作为 formal allowlist：

```text
validated
parsed
title_exact
validated_by_exact_text
launch_time_unverified
explicit_trusted_source
unknown future status
```

失败时：

```text
do not append to events/*.jsonl
persist scheduler pending/terminal diagnostic
```

必需静态回归：

```text
test_only_formal_event_writer_can_append_events_stream
test_all_legacy_fallback_paths_emit_diagnostic_not_formal_event
```

### 7.2 Title-symbol path 改造

当 `ev.get("symbols")` 非空：

当前行为：

```text
emit immediately, detail_fetch_status = not_needed
```

新行为：

```text
create/update detail_retry_state[articleCode]
candidate_symbols = title symbols
symbol_extraction_source = title
symbol_validation_status = pending_detail_launch_anchor
detail_fetch_attempted = false
detail_fetch_status = pending_detail_required
next_detail_retry_at_ms = now_ms
```

该 article 后续进入现有 BAPI/detail fetch flow。若 BAPI 正文解析出 launch time：

```text
symbol_effective_launch_times_ms populated
exchangeInfo validation/onboard resolution runs
emit formal event only after validation passes
```

若 BAPI/detail 暂不可用：

```text
stay pending_detail_retry
do not formal emit title-only event
```

注意：`detail attempt mandatory` 不等于 `detail success mandatory`。title symbol 必须进入 detail/validation flow，并记录 detail attempt / manifest / failure class；但如果 detail/BAPI 暂时返回 HTTP 202、timeout 或 transient failure，而 exchangeInfo 已能提供严格身份与 onboard anchor，允许走受控 fallback。

### 7.2.1 Anchor provenance levels

正式 emit 的 anchor 来源分三层：

```text
Level A: detail-confirmed
  title/detail candidate
  + trusted BAPI/support detail
  + exact per-symbol launch time
  + exchangeInfo identity validation

Level B: exchangeInfo-confirmed fallback
  title exact contract symbol
  + detail attempt already recorded in request_manifest
  + detail temporarily unavailable / transient failure
  + exchangeInfo exact symbol/product metadata
  + onboardDate present and valid

Level C: unanchored title candidate
  title symbol only
  + no trusted detail time
  + no exchangeInfo onboardDate
```

Level A 与 Level B 可 formal emit；Level C 只能 scheduler pending，不得写 `events/*.jsonl`。

Level B 必须记录：

```text
launch_anchor_evidence_level = exchangeinfo_fallback
detail_fetch_status = pending_or_transient_failed
detail_confirmation_missing = true
symbol_identity_validation_status = validated_by_exchangeinfo
launch_anchor_validation_status = validated_exchangeinfo_onboard_anchor
```

Level B 不得伪装成 detail-confirmed clean parser evidence。Stage 1.5G/1.5H 后续如需分层，只能依据 `launch_anchor_evidence_level` 做分析。

### 7.3 Single-symbol 与 multi-symbol contract parity

single-symbol article 不再拥有比 multi-symbol 更宽松的 emit 条件。

统一模型：

```text
candidate_symbols = [symbol] 或 [symbol1, symbol2, ...]
candidate_symbol_set_hash applies to all candidate sets
symbol_effective_launch_times_ms required for every candidate
exchangeInfo status PENDING_TRADING / PRE_TRADING / TRADING 可用于 validation/onboard anchor
```

single-symbol formal event 可以保持 `stable_event_key = binance_<article>_<symbol>`，不强制使用 `MULTI` identity。但 readiness gate 必须共享同一套 validation 逻辑。

### 7.4 Missing detail / missing anchor terminal policy

如果达到 detail retry max age 仍无法获得 launch anchor：

第一版策略：

```text
status = terminal_non_consumable
terminal_failure_type = launch_anchor_unavailable
write detail_retry_terminal_diagnostics
do not write consumable events/*.jsonl
```

不采用：

```text
fallback title event -> events/*.jsonl
```

因为这正是 GRVT 事故链路。

### 7.5 Backward compatibility

历史 replay / smoke summary 可以继续记录非 formal diagnostics，但 1.5F runtime gate 只能消费满足 formal contract 的 rows。

如果必须保留旧 title-only event 行为用于非 1.5F 诊断，应写入独立 diagnostics stream，而不是 `events/*.jsonl` formal stream。

### 7.6 Detail scheduler capacity contract

强制 title-known article 进入 detail/validation flow 会显著增加 detail pipeline 负载。公告形态审计中 title 已含 symbol 的样本约占 69%，不能假设现有 retry budget 自动足够。

Detail scheduler 必须按 lane 调度：

```text
Lane 1: title-known, anchor-missing fresh articles
Lane 2: generic-title, symbol-missing fresh articles
Lane 3: recent transient retries
Lane 4: old transient backlog
```

最低调度要求：

```text
Lane 1 和 Lane 2 均有 first-attempt SLA。
旧 HTTP 202 / transient backlog 不得占满全部 per-poll budget。
title-known article 不得挤死 generic-title article。
generic-title article 不得被 title-known burst 挤死。
每个实际 HTTP request 必须对应 1 条 request_manifest row 和 attempt_count + 1。
```

必需测试：

```text
test_title_known_and_generic_title_both_receive_first_detail_attempt
test_title_known_burst_does_not_starve_generic_title
test_old_202_backlog_does_not_starve_grvt_like_article
```

### 7.7 Per-symbol anchor provenance and conflict handling

`launch_time_source` 不得继续作为单一字符串掩盖 per-symbol 差异。Formal row 至少包含：

```text
symbol_launch_time_candidates_ms = {
  SYMBOL: {
    bapi_article_body: int | null,
    exchangeinfo_onboard_date: int | null
  }
}
symbol_effective_launch_times_ms = {SYMBOL: int}
symbol_effective_launch_time_sources = {SYMBOL: source}
launch_anchor_validation_status = validated_detail_anchor | validated_exchangeinfo_onboard_anchor | validated_detail_exchangeinfo_consensus | conflict | missing
launch_anchor_disagreement_ms = {SYMBOL: int | null}
launch_anchor_comparison_status = {
  SYMBOL:
    single_source_detail
    single_source_exchangeinfo
    consensus
    conflict
}
```

若同一 symbol 的 candidate anchors 差异超过：

```text
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS = 60_000
```

则不得 formal emit 或 active admission，应进入：

```text
pending_anchor_conflict
```

### 7.8 Postponement / revision scope guard

Binance 公告可能包含 `Postpone`、`delayed`、`rescheduled`、Pre-Market、Pre-IPO、USD1/USDC、Equity/Index/Commodity 等形态。

第一版必须至少保证：

```text
postpone / delayed / rescheduled notice
-> 不得分类为新的 futures_contract_launch
-> 写 launch_schedule_revision diagnostic
-> 不自动修改已 active observation
-> 如果命中 pending event stable key，可进入 pending_anchor_revision_conflict
```

必需测试：

```text
test_postponement_notice_not_treated_as_new_launch
test_pending_launch_receives_postponement_revision_and_does_not_promote_old_anchor
test_usd1_usdc_title_symbols_still_follow_formal_anchor_contract
```

### 7.9 Pending revision identity rules

1.5D validated revision 唤醒 1.5F pending state 时，身份字段必须保持稳定：

Immutable：

```text
event_symbol_id
stable_event_symbol_key
source_article_id
symbol
first_seen_at_ms
```

Updatable：

```text
latest_source_event_id
latest_payload_hash
revision_seen_count
anchor candidates
resolved anchor
source validation fields
```

处理规则：

```text
same stable key + pending
-> upsert existing pending state
-> 不创建新 state
-> 不写第二条 accepted row

active/completed 收到 revision
-> 记录 diagnostic
-> 不修改 observation window
-> 不 reopen
```

## 8. 数据字段要求

### 8.1 Stage 1.5D formal event required fields

新增/收紧 contract：

```text
formal_event_contract_version
formal_event_consumable_by_stage1_5f
source_contract_status
symbol_identity_validation_status
symbol_effective_launch_times_ms
symbol_onboard_times_ms
symbol_launch_time_candidates_ms
symbol_effective_launch_time_sources
launch_anchor_validation_status
launch_anchor_disagreement_ms
launch_anchor_comparison_status
launch_anchor_evidence_level
detail_fetch_attempted
detail_fetch_status
detail_fetch_variant
detail_confirmation_missing
source_article_id
stable_event_key
event_id
parser_version
symbol_extraction_version
```

对 single-symbol title event，期望最终 row 示例：

```json
{
  "formal_event_contract_version": 1,
  "formal_event_consumable_by_stage1_5f": true,
  "source_contract_status": "formal_v1_valid",
  "source_article_id": "20536b05b2a34b87a3bae99c45d0dc91",
  "symbols": ["GRVTUSDT"],
  "symbol_extraction_source": "title",
  "detail_fetch_attempted": true,
  "detail_fetch_status": "success",
  "detail_fetch_variant": "bapi_article_detail_query",
  "detail_confirmation_missing": false,
  "symbol_identity_validation_status": "validated_by_exchangeinfo",
  "launch_anchor_validation_status": "validated_detail_exchangeinfo_consensus",
  "launch_anchor_evidence_level": "detail_confirmed",
  "symbol_launch_time_candidates_ms": {
    "GRVTUSDT": {
      "bapi_article_body": 1785501900000,
      "exchangeinfo_onboard_date": 1785501900000
    }
  },
  "symbol_effective_launch_times_ms": {"GRVTUSDT": 1785501900000},
  "symbol_effective_launch_time_sources": {"GRVTUSDT": "bapi_article_body"},
  "symbol_onboard_times_ms": {"GRVTUSDT": 1785501900000},
  "launch_anchor_disagreement_ms": {"GRVTUSDT": 0},
  "launch_anchor_comparison_status": {"GRVTUSDT": "consensus"}
}
```

Level B exchangeInfo fallback 示例必须显式标注：

```json
{
  "launch_anchor_evidence_level": "exchangeinfo_fallback",
  "detail_fetch_status": "pending_or_transient_failed",
  "detail_confirmation_missing": true,
  "symbol_identity_validation_status": "validated_by_exchangeinfo",
  "launch_anchor_validation_status": "validated_exchangeinfo_onboard_anchor",
  "symbol_effective_launch_time_sources": {"GRVTUSDT": "exchangeinfo_onboard_date"},
  "launch_anchor_disagreement_ms": {"GRVTUSDT": null},
  "launch_anchor_comparison_status": {"GRVTUSDT": "single_source_exchangeinfo"}
}
```

### 8.2 Stage 1.5F pending state fields

对新增/强化 pending path，state 至少记录：

```text
status
pending_reason
source_contract_status
source_article_id
stable_event_symbol_key
event_symbol_id
symbol
first_seen_at_ms
observation_anchor_ms
observation_anchor_candidates
next_admission_check_at_ms
anchor_resolution_started_at_ms
anchor_resolution_deadline_ms
anchor_resolution_retry_count
anchor_resolution_last_attempt_at_ms
pending_source_event_unvalidated
required_source_revision
capacity_defer_count
capacity_deferred_at_ms
next_capacity_check_at_ms
latest_source_event_id
latest_event_payload_hash
revision_seen_count
```

`capacity` pending 期间不得移动：

```text
observation_anchor_ms
observation_window_start_ms
clean/recovery delay calculation origin
```

否则系统容量延期会被错误解释为市场或交易所延迟，并导致 recovery window 被反复重置。

## 9. Watermark 与 evidence 边界

本 hotfix 不改变 1.5F bootstrap watermark 语义，但必须区分两种不同语义：

```text
Source-ingestion watermark:
  表示 event row 已被完整、持久化注册。
  pending state 也算 durable registration。
  一个 multi-symbol row 的所有 sibling 均 durable pending/accepted/rejected 后，source-ingestion watermark 可以推进一次。

Admission/accepted counters:
  pending 不计入 accepted。
  pending 不产生 clean evidence。
  pending 不计 observation started。
```

如果代码里只有一个 watermark 对象，implementation plan 必须明确该对象实际承担的是 source-ingestion watermark，不能再使用未经定义的 `accepted watermark` 表述。

要求：

```text
durable pending may advance source-ingestion watermark
pending must not advance accepted/admission counters
diagnostic-only / rejected unvalidated event 不产生 clean evidence
legacy GRVT rejected row 不回写为 clean
新 root 只对部署后新事件生效
```

对于 GRVT 事故：

```text
classification = missed_clean_evidence_due_to_title_anchor_gate_bug
clean_depth_evidence_pass = false
quarantine_recompute_allowed = only if Stage 1.5G legacy/quarantine policy explicitly supports it
```

本设计不补采、不伪造 12h clean window。

## 10. Fixture 与测试策略

### 10.1 必须冻结的 GRVT 证据

需要新增：

```text
tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_grvt_real_frozen_fixture.json
tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_grvt_real_frozen_fixture_metadata.json
tests/fixtures/external_signal_shadow/stage1_5f/grvt_title_gate/grvt_stage1_5d_unanchored_event.json
tests/fixtures/external_signal_shadow/stage1_5f/grvt_title_gate/grvt_exchangeinfo_before_launch.json
tests/fixtures/external_signal_shadow/stage1_5f/grvt_title_gate/grvt_exchangeinfo_after_launch.json
```

数据质量标注：

```text
server_runtime_evidence = original incident event/rejected rows
post_incident_official_bapi_frozen_payload = after-incident BAPI body used to validate parser capability
not_point_in_time_incident_payload = true
synthetic_exchangeinfo_before_launch = only if server did not capture prelaunch exchangeInfo raw snapshot
```

### 10.2 Stage 1.5F tests

必须新增：

```text
test_exchangeinfo_symbol_missing_before_future_anchor_returns_pending
test_anchor_missing_unvalidated_event_returns_pending_not_rejected
test_pending_unvalidated_event_recovers_from_validated_revision
test_budget_exceeded_defers_to_pending_capacity_not_terminal_rejected
test_exchangeinfo_symbol_missing_terminal_only_after_recovery_deadline
test_symbol_missing_at_anchor_stays_pending_within_recovery_window
test_symbol_appears_five_minutes_after_anchor_promotes_recovery
test_symbol_missing_after_recovery_deadline_becomes_terminal
test_pending_revision_upserts_existing_state_without_new_event_symbol_id
test_active_completed_revision_records_diagnostic_without_reopening_observation
```

必须增加参数化矩阵测试：

```text
anchor:
  None

exchangeInfo:
  unavailable
  available + symbol missing
  available + symbol present

budget:
  available
  exceeded

source contract:
  legacy_unvalidated_recoverable
  formal_v1_valid

now:
  first_seen
  after_15_minutes
  after_anchor_resolution_deadline
```

断言：

```text
anchor_resolution_deadline 前：
  所有组合均不得返回 terminal exchangeInfo-missing reason

deadline 后：
  只能返回 rejected_launch_anchor_unavailable_timeout
  不能返回 symbol_not_in_exchangeinfo
```

### 10.3 Stage 1.5D tests

必须新增：

```text
test_title_symbol_launch_article_enters_detail_required_pending_not_immediate_emit
test_grvt_title_symbol_requires_launch_anchor_before_formal_emit
test_single_symbol_title_bapi_body_extracts_launch_time_and_emits_validated_event
test_detail_retry_max_age_without_anchor_writes_non_consumable_diagnostic_not_event
test_all_event_append_paths_reject_unanchored_futures_launch_formal_emit
test_only_formal_event_writer_can_append_events_stream
test_title_known_and_generic_title_both_receive_first_detail_attempt
test_title_known_burst_does_not_starve_generic_title
test_old_202_backlog_does_not_starve_grvt_like_article
test_postponement_notice_not_treated_as_new_launch
test_pending_launch_receives_postponement_revision_and_does_not_promote_old_anchor
test_usd1_usdc_title_symbols_still_follow_formal_anchor_contract
```

### 10.4 Regression suite

每次部署前至少跑：

```text
GRVT title prelaunch tests
A827 BAPI table parser tests
93b5 multi-symbol all-or-none tests
POPMART prelaunch observation legacy tests
6cbb USD1 parser tests
Stage 1.5F pending/recovery tests
Stage 1.5G duplicate identity tests
```

## 11. Implementation Phasing

### Phase A：Stage 1.5F 防御层

优先级最高。

目标：

```text
即使 1.5D 仍产生 unanchored title event，1.5F 也不再 terminal hard reject。
```

改动范围：

```text
src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py
scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py
tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
```

完成标准：

```text
GRVT unanchored event -> pending_launch_anchor_missing
GRVT future anchor event -> pending_launch_time_in_future
symbol missing after anchor but within 900_000ms recovery window -> pending_exchangeinfo_symbol_not_visible_after_anchor
symbol missing after recovery deadline -> rejected_launch_symbol_not_visible_timeout
capacity exceeded -> pending_observation_capacity
no terminal rejected row for prelaunch/recovery-window exchangeInfo symbol missing
```

### Phase B：Stage 1.5D 源头收口

目标：

```text
1.5D 不再把 title-only symbol 作为 formal event 直接写给 1.5F。
```

改动范围：

```text
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py
src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py
tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py
```

完成标准：

```text
title symbol article -> scheduler pending_detail_required
BAPI/detail success + anchor validation -> formal emit
detail transient failure + strict exchangeInfo onboard anchor -> formal emit with launch_anchor_evidence_level = exchangeinfo_fallback
missing anchor timeout -> diagnostic only
events/*.jsonl contains no unanchored futures_contract_launch formal rows
all events/*.jsonl writes go through append_formal_futures_launch_event(...)
```

### Phase C：Deployment runbook 与 evidence sync

目标：

```text
部署前后检查能直接发现 title-symbol bypass 和 1.5F premature reject。
```

更新：

```text
docs/reviews/2026-08-01-stage1-5d-1-5f-title-anchor-gate-hotfix-deployment-review_CN.md
_project_context/source_upload generation logic if needed
```

不得继续覆盖旧 `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md` 作为本 hotfix 的主 runbook，以免原始审批结论与后续 hotfix 部署语义混淆。旧 review 可保留历史引用，新 runbook 使用独立日期文件。

## 12. 生产验收

部署后首轮检查：

```text
1.5D live_safety_gate_summary.decision = stage1_5d_runtime_gate_ready
1.5F stage1_5d_runtime_gate_decision = stage1_5d_runtime_gate_ready
block_new_event_admission = false
runtime_gate_diagnostic_count = 0
```

新 title-symbol launch event 出现时，必须按阶段验收。

Phase A compatibility root：

```text
1. legacy bad/unversioned event may reach 1.5F。
2. source_contract_status = legacy_unvalidated_recoverable。
3. 1.5F 建立 durable pending state。
4. 1.5F 不 active、不 accepted、不产生 clean/recovery evidence。
5. anchor missing / exchangeInfo missing / capacity exceeded 均不得写 terminal exchangeInfo-missing reason。
6. production Stage 1.5F code 不得存在 return "rejected", "symbol_not_in_exchangeinfo"。
```

Phase B strict root：

```text
1. 1.5D request_manifest 有 BAPI/detail attempt。
2. 1.5D scheduler 中该 article 不出现 detail_fetch_status=not_needed 的 immediate emit。
3. exchangeInfo identity 未验证且无允许 formal provenance -> 1.5D 不 emit formal event。
4. 1.5D events row 必须包含 formal_event_contract_version = 1 与 formal_event_consumable_by_stage1_5f = true。
5. 1.5D events row 必须包含 symbol_effective_launch_times_ms、symbol_launch_time_candidates_ms、symbol_effective_launch_time_sources、launch_anchor_validation_status、launch_anchor_comparison_status。
6. launch anchor 后 900_000ms recovery window 内 exchangeInfo 仍缺失时，1.5F 仍应 pending_exchangeinfo_symbol_not_visible_after_anchor。
7. 1.5F events_rejected 不得出现 prelaunch/recovery-window symbol_not_in_exchangeinfo。
8. launch anchor 到达且 symbol/product valid 后，1.5F 可以在 capacity check 通过时 promote active。
9. capacity 不足时进入 pending_observation_capacity，不写 rejected。
10. title-known 与 generic-title 新 article 均满足 first detail attempt SLA。
```

## 13. 风险与回滚

### 13.1 主要风险

```text
1. 1.5D 收紧 formal emit 后，detail/BAPI 短暂失败期间 event 会延迟输出。
2. title-known article 进入 detail pipeline 后，detail scheduler 负载上升，需要 lane/fairness 保护。
3. 1.5F pending 增加，summary 中 no_new_event 可能转为 pending_launch_anchor_missing / pending_exchangeinfo_symbol_not_visible_after_anchor。
4. 旧 tests 可能假设 title symbol 可立即 emit，需要按 formal evidence contract 更新。
5. Phase B 要求 exchangeInfo validation / formal provenance 后才 formal emit，可能使 GRVT 这类 launch 前 exchangeInfo 不可见的事件只能在 launch 附近输出，损失 2 分钟 clean-start SLA。这是 `coverage sacrifice for source integrity`，不得表述为 Phase B 一定能在 launch 前把事件交给 1.5F。
```

这些风险可接受，因为它们选择的是 safe no-op / pending，而不是错误 clean evidence 或永久误杀。

### 13.2 回滚策略

如果 Phase A 引入异常：

```text
停止新 1.5F root
保留 1.5D collector
回滚 1.5F 到上一版本只做 observation-disabled/no-new-admission
不得恢复 prelaunch hard reject 行为作为 clean evidence path
```

如果 Phase B 引入 1.5D event starvation：

```text
保留 raw_payloads/request_manifest/scheduler_state
暂停 1.5F new admission
修复 scheduler/detail retry
不得启用 title-only formal emit 快路径
```

## 14. 结论

本次 GRVT 事故的修复必须同时覆盖源头与下游：

```text
1. Stage 1.5F 先修：unanchored/future-anchor/recovery-window event 不得 hard reject。
2. Stage 1.5D 再修：title symbol 不得绕过 detail/BAPI 与 launch-anchor validation。
3. Formal event contract versioned/fail-closed，并由唯一 writer 写入 events stream。
4. GRVT fixture 固化：以后本地测试必须能复现并阻断同类 regression。
```

设计上两层同时定义，实施上分 Phase A / B / C，避免一次性重构过大，同时保证下一个真实 title-symbol 提前公告不会再次被 terminal rejected。
