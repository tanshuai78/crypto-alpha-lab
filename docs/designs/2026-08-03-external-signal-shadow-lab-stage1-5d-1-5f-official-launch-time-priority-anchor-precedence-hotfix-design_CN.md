# Stage 1.5D / 1.5F Official Schedule Priority Anchor Contract V2 Hotfix Design

```text
status = design_revised_after_second_external_review
scope = stage1_5d_1_5f_official_schedule_priority_anchor_contract_v2_hotfix
phase = phase_b_anchor_precedence_addendum
trigger_incident = 2026-08-03_gigadevusdt_exchangeinfo_onboarddate_earlier_than_official_launch_time
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

本版采纳两轮 external review 的 P0 反馈，并固定以下设计约束：

```text
1. 新 anchor precedence 语义必须升级为 formal_event_contract_version = 2。
2. 新增 anchor_precedence_policy = official_schedule_priority_v1。
3. 所有 anchor evidence / comparison / validation / revision 字段必须 per-symbol。
4. latest applicable official schedule 必须按 point-in-time as-of selection 选择，不允许离线后视替换。
5. exchangeInfo fallback 第一版永远不得生成 clean evidence。
6. evidence class after observation start must be monotonic non-increasing。
7. 1.5D 必须定义 schedule revision transport contract，不能只描述 1.5F 状态机。
8. active fallback contamination 第一版选择唯一行为：继续采集 diagnostic-only 到原 window end，不启动第二 observation。
9. 1.5F 必须持久化 anchor contract lineage，1.5G 必须验证 accepted/state/completed lineage hash。
10. anchor_revision_contaminated / malformed_anchor_contract / lineage_mismatch 一律 Stage 1.5G invalid，不进入 quarantine。
11. v1 compatibility 默认关闭，必须独立 diagnostic-only root，且不得与 v2 production rows 混用。
12. deployment glob bug 纳入 runbook regression gate。
```

## 1. 背景

Stage 1.5D 从 Binance 官方公告生成 `futures_contract_launch` event rows。Stage 1.5F 消费这些 rows，在可信 launch anchor 附近启动 live depth observation。此前 2026-08-01 `Title-Symbol Launch-Anchor Validation Gate` hotfix 已修复 single-symbol title event 在无 anchor、无 exchangeInfo validation 时被 1.5F 早期 terminal rejected 的问题。

2026-08-03 出现新的生产证据：

```text
article_id = e8bfd0c5adaf4d8a880bb1b7327107ef
symbol = GIGADEVUSDT
title = Binance Futures Will Launch GIGADEVUSDT USDⓈ-Margined Perpetual Contract (2026-08-03)
source_published_at_utc = 2026-08-03T02:30:09.135Z
official_schedule_anchor_utc = 2026-08-03T05:30:00Z
exchangeinfo_onboardDate_utc = 2026-08-03T02:00:00Z
```

生产 root 证据显示：

```text
1. Stage 1.5D 已通过 BAPI detail 请求抓到公告，HTTP 200。
2. Stage 1.5D 已写入 events/2026-08-03.jsonl。
3. Event row 标记 formal_event_contract_version = 1、source_contract_status = formal_v1_valid。
4. Event row 的 symbol_effective_launch_times_ms 使用 exchangeInfo onboardDate = 2026-08-03T02:00:00Z。
5. 官网正文 launch schedule 为 2026-08-03T05:30:00Z。
6. 1.5F 在 deployment glob 修正后回放该 event，并进入 pending_anchor_conflict。
```

该事故证明：仅修 title-symbol hard reject 不够。Stage 1.5D / 1.5F / 1.5G 必须升级 anchor contract，明确 official schedule、exchangeInfo onboardDate、schedule revision 与 1.5G evidence lineage 的语义关系。

## 2. 事故分层

本次 GIGADEV 暴露两个独立问题：

```text
A. Deployment checklist bug:
   1.5F --stage1-5d-events-glob 被写成 events/\*.jsonl，Python glob.glob() 匹配 0 个 files。

B. Anchor contract bug:
   1.5D formal v1 event 在 official schedule 存在时，仍把 exchangeInfo onboardDate 作为 effective observation anchor。
```

问题 A 已在 deployment checklist 修复，但必须加入 regression runbook：

```text
shell-expanded argv must not contain literal \*.jsonl
stage1_5d events glob must match >= 1 event file before 1.5F observer startup
```

问题 B 是本设计代码范围。它导致：

```text
official_schedule_anchor_ms = 1785735000000
exchangeinfo_onboardDate_ms = 1785722400000
anchor_disagreement_ms = 12,600,000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS = 60,000
1.5F status = pending_anchor_conflict
observation_anchor_ms = null
```

由于问题 A 导致 1.5F 延迟回放，GIGADEV 已错过当前 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS = 15min`。该事件只能作为 diagnostic / regression evidence，不能补成 clean 或 recovery 1.5G evidence。

## 3. 根因

### 3.1 formal v1 语义已经不足

旧 `formal_event_contract_version = 1` 的隐含语义近似为：

```text
all valid anchor candidates have equal priority
article/exchangeInfo disagreement > tolerance -> anchor conflict
```

本设计的新语义是：

```text
latest applicable official schedule as-of admission = primary observation anchor
exchangeInfo onboardDate = secondary validation/fallback metadata
official schedule 与 exchangeInfo onboardDate 不一致 = diagnostic，不是 blocking conflict
```

这两种语义不兼容，不能继续复用 v1。新 root 必须输出：

```text
formal_event_contract_version = 2
anchor_precedence_policy = official_schedule_priority_v1
```

### 3.2 exchangeInfo onboardDate 不是正式交易开始时间

`exchangeInfo onboardDate` 可能表示：

```text
1. Binance Futures 内部 symbol metadata 创建时间。
2. exchangeInfo API 开始暴露 symbol filters/contract metadata 的时间。
3. 交易所系统预配置时间。
4. 某些事件中接近真实 launch time 的 fallback 时间。
```

它可以早于、等于或晚于 official schedule。它适合用于 symbol identity / product metadata validation，不应在 latest applicable official schedule 明确时覆盖 observation anchor。

### 3.3 event-level scalar anchor evidence 会污染 multi-symbol article

multi-symbol article 可能出现：

```text
PYPLUSDT -> official schedule anchor，exchangeInfo disagreement
GSUSDT   -> official schedule anchor，exchangeInfo match
SMHUSDT  -> official schedule missing，exchangeInfo fallback
```

因此所有 anchor evidence / schedule revision metadata 必须 per-symbol。event-level 只能保存 aggregate summary，不能作为 symbol admission 权威。

### 3.4 1.5F 不能只相信 producer label

1.5F 必须重新验证 v2 row 内部一致性。如果 row 表示 `effective source = official_schedule_anchor`，则 effective anchor 必须等于 per-symbol official schedule anchor。任何 source label 与 anchor value 不一致都必须判定为 `malformed_anchor_contract`。

### 3.5 point-in-time 选择缺失会造成后视 clean

1.5G 离线审核不能使用 observation 之后才发布的 schedule revision 重新解释 admission 当时的 anchor。必须记录：

```text
anchor_contract_decision_at_ms
official_schedule_selection_as_of_ms
selected_official_schedule_revision_id
selected_official_schedule_available_at_ms
latest_known_revision_id_at_decision
```

选择函数必须是：

```text
select_latest_applicable_official_schedule(symbol, as_of_ms=anchor_contract_decision_at_ms)
```

且只能使用：

```text
revision.available_at_ms <= as_of_ms
```

### 3.6 fallback revision 生命周期缺失

如果 BAPI detail 暂时不可用，系统可能先生成 exchangeInfo fallback event。之后 BAPI detail 恢复，出现 official schedule。若不定义 revision transport、state mutation 和 lineage，系统可能发生后视 clean、重复 observation 或 accepted/state/completed 不一致。

### 3.7 official schedule 不是 original article 永远优先

Binance 可能发布：

```text
postpone
delayed
rescheduled
cancelled
updated launch time
```

最高优先级应是：

```text
latest applicable official schedule available to the system before anchor_contract_decision_at_ms
```

无法确认 applicability 时必须 fail closed。

## 4. 设计目标

必须实现：

```text
1. Stage 1.5D 新 root 输出 formal_event_contract_version = 2。
2. Stage 1.5D / 1.5F 共用 anchor contract validator。
3. latest applicable official schedule 以 point-in-time as-of 规则优先于 exchangeInfo onboardDate。
4. exchangeInfo onboardDate 与 official schedule 差异只产生 per-symbol diagnostic，不产生 blocking conflict。
5. 所有 anchor evidence / comparison / validation / revision 字段必须 per-symbol。
6. exchangeInfo fallback 第一版永远不得 clean，最多 recovery_validation_only / diagnostic。
7. evidence class after observation start must be monotonic non-increasing。
8. schedule revision 必须有 1.5D -> 1.5F transport contract、stable identity、watermark/idempotency 规则。
9. active fallback contamination 第一版固定为 diagnostic-only continuation to original window end。
10. 1.5F accepted/state/completed 必须持久化 anchor contract lineage hash。
11. Stage 1.5G 必须验证 lineage，并将 contamination / malformed / mismatch 判定为 invalid。
12. 旧 v1 rows 在新 live root 中默认 fail-closed，v1 compatibility 必须显式启用并使用独立 diagnostic-only root。
13. GIGADEV 冻结为 regression fixture。
14. deployment glob bug 纳入 runbook regression gate。
```

非目标：

```text
不改变 Stage 1.5G clean/quarantine 阈值。
不修改 Stage 1.5E execution feasibility。
不改变 depth snapshot cadence、window、coverage 阈值。
不扩大 EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS。
不把 GIGADEV 或其他历史错过事件补成 clean evidence。
不实现完整跨公告 schedule graph 数据库；第一版只处理明确 supersession。
不新增任何 trade signal、paper trading、live trading 或 execution permission。
```

## 5. Contract V2 核心不变量

### 5.1 Versioning

```text
INVARIANT: official_schedule_priority semantics require formal_event_contract_version = 2.
```

新 root 必须输出：

```text
formal_event_contract_version = 2
anchor_precedence_policy = official_schedule_priority_v1
source_contract_status = formal_v2_valid | malformed_anchor_contract | explicit_non_consumable
formal_event_consumable_by_stage1_5f = true | false
```

v1 与 v2 不得互换：

```text
v1 = legacy_equal_candidate_semantics
v2 = official_schedule_primary_semantics
```

### 5.2 Per-symbol fields

新 v2 row 必须使用 per-symbol 字段：

```text
symbol_official_schedule_anchor_ms: dict[str, int]
symbol_official_schedule_anchor_utc: dict[str, str]
symbol_exchangeinfo_onboard_date_ms: dict[str, int]
symbol_exchangeinfo_onboard_date_utc: dict[str, str]
symbol_effective_observation_anchor_ms: dict[str, int]
symbol_effective_observation_anchor_utc: dict[str, str]
symbol_effective_observation_anchor_sources: dict[str, str]
symbol_anchor_evidence_levels: dict[str, str]
symbol_anchor_comparison_statuses: dict[str, str]
symbol_anchor_disagreement_ms: dict[str, int | null]
symbol_anchor_disagreement_directions: dict[str, str]
symbol_anchor_validation_statuses: dict[str, str]
symbol_max_evidence_classes: dict[str, str]
symbol_anchor_provenance: dict[str, dict]
symbol_official_schedule_statuses: dict[str, str]
symbol_official_schedule_revision_ids: dict[str, str]
symbol_official_schedule_revision_available_at_ms: dict[str, int]
symbol_superseded_anchor_ms: dict[str, int | null]
symbol_effective_official_anchor_ms: dict[str, int | null]
```

Event-level 只允许保存派生汇总：

```text
event_anchor_aggregate_status: all_official_valid | mixed_official_and_fallback | has_missing | has_official_conflict | malformed
event_has_fallback_anchor: bool
event_has_official_conflict: bool
event_has_anchor_missing: bool
event_max_anchor_disagreement_ms: int | null
event_all_symbols_clean_eligible: bool
```

`event_all_symbols_clean_eligible` 非权威，symbol admission 必须以 `symbol_max_evidence_classes[symbol]` 为准。

### 5.3 Allowed enum values

```text
symbol_effective_observation_anchor_sources:
  official_schedule_anchor
  exchangeinfo_onboard_date
  none

symbol_anchor_evidence_levels:
  official_schedule
  exchangeinfo_fallback
  missing
  official_conflict
  malformed

symbol_anchor_comparison_statuses:
  article_exchangeinfo_match
  exchangeinfo_disagrees_with_official_schedule
  single_source_official_schedule
  single_source_exchangeinfo
  official_schedule_conflict
  missing
  malformed

symbol_anchor_disagreement_directions:
  exchangeinfo_earlier
  exchangeinfo_later
  none
  unknown

symbol_anchor_validation_statuses:
  valid_official
  valid_fallback
  conflict
  missing
  malformed

symbol_max_evidence_classes:
  clean_or_recovery
  recovery_validation_only
  diagnostic_only
  none

mapping_confidence:
  exact_single_symbol
  exact_per_symbol_row
  exact_all_symbols_statement
  ambiguous
```

Only these mapping confidence values are allowed. `ambiguous` cannot produce formal v2 consumable event.

### 5.4 Point-in-time official schedule priority

```text
INVARIANT: selected official schedule must be available at or before anchor_contract_decision_at_ms.
```

Required decision fields:

```text
anchor_contract_decision_at_ms
official_schedule_selection_as_of_ms
selected_official_schedule_revision_id
selected_official_schedule_available_at_ms
latest_known_revision_id_at_decision
```

Selection function:

```text
select_latest_applicable_official_schedule(symbol, as_of_ms=anchor_contract_decision_at_ms)
```

Allowed revision input:

```text
revision.available_at_ms <= anchor_contract_decision_at_ms
```

Future revisions may update lineage or mark contamination, but cannot retroactively replace the source-of-truth used at admission.

For each symbol:

```text
if valid latest applicable official schedule exists as of decision:
    effective_anchor = official_schedule_anchor_ms
    effective_anchor_source = official_schedule_anchor
    anchor_evidence_level = official_schedule
    max_evidence_class = clean_or_recovery
elif strict exchangeInfo fallback is valid:
    effective_anchor = exchangeinfo_onboardDate
    effective_anchor_source = exchangeinfo_onboard_date
    anchor_evidence_level = exchangeinfo_fallback
    max_evidence_class = recovery_validation_only
else:
    effective_anchor = none
    anchor_evidence_level = missing | conflict | malformed
    max_evidence_class = none
```

### 5.5 exchangeInfo fallback clean lock

```text
INVARIANT: exchangeinfo_fallback_clean_allowed = false.
```

Even if 1.5F sees fallback anchor within the 2-minute clean window:

```text
symbol_anchor_evidence_levels[symbol] = exchangeinfo_fallback
=> eligible_clean_start forbidden
=> max eligible class = eligible_recovery_only or diagnostic_only
=> Stage 1.5G clean_depth_evidence_pass = false
```

### 5.6 Evidence class monotonicity

```text
INVARIANT: once observation has started, max_evidence_class cannot increase.
```

Rules:

```text
pending fallback, not started + official revision arrives:
  may update to official schedule
  re-evaluate clean/recovery based on current time and official anchor

active/completed fallback + later matching official revision:
  anchor_value_later_confirmed = true
  max_evidence_class remains recovery_validation_only
  clean upgrade forbidden

active/completed fallback + later different official revision:
  observation_anchor_revision_contaminated = true
  max_evidence_class becomes none
  clean/recovery/quarantine evidence invalid
```

## 6. Official Schedule Anchor Validity

A time in official article text is not automatically a launch anchor. It must be valid and assignable.

### 6.1 Required provenance

Each official schedule anchor must carry per-symbol provenance:

```text
raw_time_text
timezone_text
parser_method
node_path
logical_block_id
payload_sha256
parser_version
mapping_method
mapping_confidence
schedule_text_context
official_schedule_revision_id
official_schedule_available_at_ms
supersedes_source_article_id
supersedes_anchor_ms
request_id
fetched_at_ms
request_manifest_path
point_in_time_status
```

### 6.2 Allowed mapping methods

Allowed:

```text
single_symbol_article_unique_futures_launch_time
multi_symbol_explicit_per_symbol_row
multi_symbol_explicit_all_contracts_launch_at_time
multi_symbol_table_row_matched_by_symbol
latest_applicable_official_revision
```

Forbidden:

```text
any UTC time in article body without futures launch context
funding settlement time
trading bot launch time
promotion start/end time
maintenance time
API update time
multi-symbol isolated time not proven to apply to all symbols
choosing earliest/latest time among multiple same-priority ambiguous times
```

If attribution is ambiguous:

```text
mapping_confidence = ambiguous
symbol_anchor_validation_statuses[symbol] = conflict | missing
symbol_anchor_evidence_levels[symbol] = official_conflict | missing
formal_event_consumable_by_stage1_5f = false for the affected symbol
```

For all-or-none multi-symbol formal emission, if any symbol has `official_conflict`, `missing` without strict fallback, or `malformed`, the batch cannot be fully consumable.

## 7. Stage 1.5D Design

### 7.1 Shared contract module

Create or extend a common module, for example:

```text
src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py
```

It must expose at least:

```text
select_latest_applicable_official_schedule(...)
resolve_primary_launch_anchor(...)
validate_launch_anchor_contract(...)
validate_formal_launch_event(...)
build_symbol_anchor_contract(...)
build_event_anchor_aggregate_status(...)
compute_anchor_contract_hash(...)
```

Both Stage 1.5D writer and Stage 1.5F validator must call this module. Builder, writer, and consumer must not implement independent anchor rules.

### 7.2 Formal writer fail-closed

Stage 1.5D `append_formal_futures_launch_event()` must validate contract v2 before writing consumable event rows.

Required behavior:

```text
valid v2 contract -> append events/*.jsonl with formal_event_consumable_by_stage1_5f = true
invalid/malformed anchor contract -> do not append consumable event row
invalid but diagnostically useful -> append diagnostics/non_consumable stream only
```

Thin append wrappers are not allowed.

### 7.3 Runtime gate capability

Stage 1.5D `live_safety_gate_summary.json` must expose:

```text
formal_event_contract_versions_supported = [2]
anchor_precedence_policy = official_schedule_priority_v1
shared_anchor_validator_enabled = true
formal_schedule_revision_contract_versions_supported = [1]
```

Stage 1.5F startup must validate these capabilities before accepting events from the root.

### 7.4 GIGADEV expected v2 row

Expected per-symbol fields:

```text
symbol = GIGADEVUSDT
formal_event_contract_version = 2
anchor_precedence_policy = official_schedule_priority_v1
anchor_contract_decision_at_ms = row_build_time_ms
official_schedule_selection_as_of_ms = anchor_contract_decision_at_ms
selected_official_schedule_revision_id.GIGADEVUSDT = <revision_id_available_at_decision>
selected_official_schedule_available_at_ms.GIGADEVUSDT <= anchor_contract_decision_at_ms
symbol_official_schedule_anchor_ms.GIGADEVUSDT = 1785735000000
symbol_exchangeinfo_onboard_date_ms.GIGADEVUSDT = 1785722400000
symbol_effective_observation_anchor_ms.GIGADEVUSDT = 1785735000000
symbol_effective_observation_anchor_sources.GIGADEVUSDT = official_schedule_anchor
symbol_anchor_evidence_levels.GIGADEVUSDT = official_schedule
symbol_anchor_comparison_statuses.GIGADEVUSDT = exchangeinfo_disagrees_with_official_schedule
symbol_anchor_disagreement_ms.GIGADEVUSDT = 12600000
symbol_anchor_disagreement_directions.GIGADEVUSDT = exchangeinfo_earlier
symbol_anchor_validation_statuses.GIGADEVUSDT = valid_official
symbol_max_evidence_classes.GIGADEVUSDT = clean_or_recovery
symbol_anchor_provenance.GIGADEVUSDT.mapping_confidence = exact_single_symbol
event_has_fallback_anchor = false
event_has_official_conflict = false
event_all_symbols_clean_eligible = true
```

Legacy aliases such as `symbol_effective_launch_times_ms` may exist, but must be derived from v2 fields and must not contradict v2 contract.

## 8. Schedule Revision Transport Contract

### 8.1 Revision event type

Stage 1.5D must emit schedule revisions through a formal transport artifact:

```text
event_type = futures_contract_launch_schedule_revision
formal_schedule_revision_contract_version = 1
```

Minimum required fields:

```text
source_article_id
supersedes_source_article_id
stable_schedule_identity
symbols
symbol_official_schedule_statuses
symbol_revised_anchor_ms
symbol_revised_anchor_utc
symbol_official_schedule_revision_ids
symbol_official_schedule_revision_available_at_ms
symbol_superseded_anchor_ms
revision_id
revision_payload_hash
revision_reason
anchor_precedence_policy
```

Stable identity:

```text
stable_schedule_identity = normalized_source_namespace | futures_contract_launch | original_source_article_id | symbol
```

### 8.2 Streams and replay

First version may use the same `events/*.jsonl` glob if and only if 1.5F routes by `event_type` before admission:

```text
futures_contract_launch -> launch event admission path
futures_contract_launch_schedule_revision -> schedule revision path, never new launch admission
```

Revision replay rules:

```text
revision_id + stable_schedule_identity are idempotency keys
revision rows update existing pending/active/completed state by stable_schedule_identity
revision rows must not create a new event_symbol_id
revision rows must survive restart and be replayed exactly once per state lineage
watermark must track revision identity separately from launch event identity
```

If implementation chooses a separate stream, e.g. `schedule_revisions/*.jsonl`, Stage 1.5F must receive an explicit glob and runtime gate must advertise the stream. The implementation plan must choose one approach and test it.

### 8.3 Producer scope boundary and follow-up

This design version defines the schedule revision transport contract, fail-closed writer semantics, replay/idempotency rules, and Stage 1.5F/1.5G consumer behavior. It does not by itself approve a broad Stage 1.5D automatic producer classifier for every Binance announcement shape.

```text
current_version_scope = revision_transport_and_consumer_ready
automatic_revision_producer_classifier = follow_up_required
deployment_blocker_for_v2_launch_rows = false
deployment_blocker_for_revision_auto_detection = true
```

A later Stage 1.5D producer rule addendum must define:

```text
1. What official Binance announcement text qualifies as futures_contract_launch_schedule_revision.
2. What announcement text is explicitly not a revision.
3. How supersedes_source_article_id is derived from official links, articleCode references, or unique point-in-time symbol+schedule matches.
4. When a revision is linked, orphaned, or ambiguous.
5. Which real Binance postpone/reschedule/cancel launch announcements are frozen as regression fixtures.
6. How multi-symbol revision announcements map per-symbol revised/superseded anchors.
7. How producer diagnostics are emitted when the original launch event is missing or ambiguous.
```

Until that addendum is implemented and tested, Stage 1.5D may only write schedule revision rows through explicitly constructed, validated `build_formal_schedule_revision_row(...)` artifacts. It must not infer `supersedes_source_article_id` from symbol alone.

Minimum producer invariants for the follow-up:

```text
revision by explicit official reference:
  if revision article links or names original articleCode/source_article_id:
    revision_link_status = linked
    supersedes_source_article_id = referenced original article

revision by unique point-in-time match:
  if same symbol + original official launch anchor uniquely identifies one prior launch event:
    revision_link_status = linked
    supersedes_source_article_id = unique original launch article

missing original:
  revision_link_status = orphaned
  no Stage 1.5F state mutation until stable_schedule_identity becomes unique

multiple candidates:
  revision_link_status = ambiguous
  diagnostic only
  no Stage 1.5F state mutation

forbidden:
  never set supersedes_source_article_id by symbol-only guess when multiple launch candidates exist
```

## 9. Stage 1.5F Design

### 9.1 Contract validation before admission

Before eligibility classification, 1.5F must call `validate_launch_anchor_contract(row, symbol)`.

If v2 row is internally inconsistent:

```text
source_contract_status = malformed_anchor_contract
formal_event_consumable_by_stage1_5f = false
status = diagnostic_only | pending_source_event_unvalidated
active admission forbidden
clean/recovery evidence forbidden
```

Examples of malformed:

```text
effective source = official_schedule_anchor but effective anchor != official schedule anchor
effective source = exchangeinfo_onboard_date while official schedule anchor exists and is valid
comparison status says match but disagreement_ms != 0
fallback source used but official schedule provenance exists and is valid
missing per-symbol evidence fields in v2 row
future revision used where revision_available_at_ms > anchor_contract_decision_at_ms
```

### 9.2 Anchor resolver behavior

For v2 official schedule anchor:

```text
observation_anchor_ms = symbol_effective_observation_anchor_ms[symbol]
observation_anchor_basis = official_schedule_anchor
observation_anchor_confidence = high
observation_anchor_conflict_active = false
```

exchangeInfo disagreement may populate diagnostics:

```text
exchangeinfo_official_schedule_disagreement_active = true
observation_anchor_disagreement_max_ms = symbol_anchor_disagreement_ms[symbol]
```

It must not return `pending_anchor_conflict` solely because exchangeInfo onboardDate differs from official schedule.

### 9.3 exchangeInfo fallback admission class

For fallback anchor:

```text
symbol_anchor_evidence_levels[symbol] = exchangeinfo_fallback
symbol_max_evidence_classes[symbol] = recovery_validation_only
```

1.5F classification:

```text
within clean window -> eligible_recovery_only, not eligible_clean_start
within recovery window -> eligible_recovery_only
outside recovery window -> rejected_launch_anchor_age_exceeded
```

Accepted rows must include:

```text
evidence_start_class = recovery_start
live_depth_evidence_basis = recovery_validation_only
clean_start_forbidden_reason = exchangeinfo_fallback_anchor
admission_max_evidence_class = recovery_validation_only
```

### 9.4 fallback -> official revision lifecycle

When fallback pending state receives official revision before observation starts:

```text
status starts pending_:
  update same stable_schedule_identity / stable_event_symbol_key
  do not create second state
  move primary anchor to official schedule if revision_available_at_ms <= current decision time
  re-evaluate clean/recovery based on current time and official anchor
```

When active observation started from fallback and official revision later differs:

```text
status = active_anchor_revision_contaminated
observation_anchor_revision_contaminated = true
anchor_revision_contamination_reason = fallback_anchor_replaced_by_official_schedule
continue current public-readonly collection until original observation_window_end_ms
do not start second observation
do not move observation_window_start_ms
do not write second accepted row
clean/recovery/quarantine evidence forbidden
final status = completed_anchor_revision_contaminated
Stage 1.5G = stage1_5g_depth_evidence_invalid
```

When completed observation receives later official revision:

```text
no reopen
no clean upgrade
anchor_revision_after_completion = true
Stage 1.5G = stage1_5g_depth_evidence_invalid
```

When fallback and later official anchor match after observation started:

```text
anchor_value_later_confirmed = true
max_evidence_class remains recovery_validation_only
clean upgrade forbidden
```

### 9.5 Lineage persistence

1.5F artifacts must persist anchor contract lineage:

```text
source_anchor_contract_hash
admission_anchor_contract_hash
latest_anchor_contract_hash
anchor_contract_version
anchor_precedence_policy
anchor_contract_decision_at_ms
admission_anchor_evidence_level
latest_anchor_evidence_level
admission_max_evidence_class
latest_max_evidence_class
anchor_contract_revision_count
observation_anchor_revision_contaminated
anchor_revision_contamination_reason
```

These fields must appear in:

```text
events_accepted row
observer_state pending/active/completed rows
completed/terminal state rows consumed by 1.5G
```

## 10. Stage 1.5G Compatibility Scope

Stage 1.5G must enter this hotfix scope only for anchor evidence semantics, not threshold changes.

Stage 1.5G must read:

```text
events_accepted
latest observer_state by event_symbol_id
completed state
```

It must validate:

```text
accepted anchor hash == state admission anchor hash
completed lineage hash matches latest state lineage
latest state contamination flags are honored
```

Invalid blockers:

```text
anchor_revision_contaminated -> stage1_5g_depth_evidence_invalid
malformed_anchor_contract -> stage1_5g_depth_evidence_invalid
anchor_contract_lineage_mismatch -> stage1_5g_depth_evidence_invalid
exchangeinfo_fallback with clean claim -> stage1_5g_depth_evidence_invalid
```

Quarantine is not allowed for anchor contract failures. Quarantine remains limited to raw orderbook quality issues after anchor contract is valid.

Do not change:

```text
snapshot count threshold
book availability threshold
max gap threshold
quarantine threshold
trade/paper/live flags
```

## 11. Legacy Compatibility Matrix

Default config:

```text
EXTERNAL_SIGNAL_STAGE1_5F_ALLOW_FORMAL_V1_COMPATIBILITY = False
```

Optional CLI, only for explicit diagnostic root:

```text
--allow-formal-v1-compatibility
--formal-v1-compatibility-reason <non-empty>
```

Required root suffix if enabled:

```text
_v1_compatibility_diagnostic_only
```

Rules:

```text
New v2 production root:
  v2 required for consumable rows.
  Missing v2 precedence fields -> malformed_anchor_contract.
  No active admission from malformed v2 rows.
  v1 rows non-consumable by default.

Old v1 root, read-only review:
  Preserve historical states.
  Do not reclassify as clean under v2 semantics.
  Do not migrate live state automatically.

v1 compatibility diagnostic-only root:
  explicit CLI required.
  clean forbidden.
  formal v2 claim forbidden.
  v1 and v2 production rows cannot mix in same live root.
  without provenance -> legacy_anchor_source_unknown.
  recovery/diagnostic only if identity, anchor, and provenance are defensible.

Existing old pending_anchor_conflict:
  no automatic migration.
  no automatic active promotion.
  optional future offline diagnostic report only.
```

## 12. Test Requirements

### 12.1 Point-in-time schedule selection tests

```text
test_future_revision_is_not_used_for_prior_admission
test_schedule_selection_uses_latest_revision_available_as_of_decision
test_offline_review_cannot_retroactively_replace_admission_anchor
```

### 12.2 Contract version tests

```text
test_v1_and_v2_anchor_semantics_are_not_interchangeable
test_new_root_rejects_v1_row_without_explicit_compatibility_policy
test_v2_official_anchor_disagreement_is_diagnostic
test_v1_legacy_conflict_row_is_not_reclassified_clean
```

### 12.3 Per-symbol contract tests

```text
test_multisymbol_mixed_official_and_fallback_keeps_per_symbol_evidence
test_event_level_aggregate_does_not_override_symbol_anchor_evidence
test_one_symbol_missing_anchor_blocks_all_or_none_consumable_emit
test_symbol_effective_anchor_must_equal_official_anchor_when_source_is_official
test_schedule_revision_metadata_is_per_symbol
```

### 12.4 1.5D builder tests

```text
test_official_schedule_anchor_overrides_earlier_exchangeinfo_onboard_date
test_official_schedule_anchor_overrides_later_exchangeinfo_onboard_date
test_exchangeinfo_onboard_date_used_only_when_official_schedule_missing
test_gigadev_fixture_emits_v2_official_schedule_anchor
test_anchor_disagreement_diagnostic_does_not_change_primary_anchor
test_official_anchor_requires_per_symbol_provenance
test_ambiguous_article_time_does_not_emit_consumable_formal_event
```

### 12.5 Schedule revision transport tests

```text
test_schedule_revision_reaches_existing_pending_state
test_revision_event_is_not_admitted_as_new_launch
test_revision_replay_is_idempotent
test_revision_survives_restart_and_watermark_replay
```

### 12.6 1.5F admission tests

```text
test_exchangeinfo_disagreement_with_official_schedule_does_not_create_anchor_conflict
test_official_anchor_future_event_enters_pending_launch_time_in_future
test_official_anchor_clean_window_event_becomes_eligible_clean_start
test_official_anchor_recovery_window_event_becomes_eligible_recovery_only
test_official_anchor_expired_event_rejects_anchor_age_exceeded
test_gigadev_fixture_does_not_enter_pending_anchor_conflict
test_exchangeinfo_fallback_inside_clean_window_is_recovery_only
test_malformed_anchor_contract_blocks_active_admission
```

### 12.7 Fallback revision and contamination tests

```text
test_pending_fallback_revision_moves_anchor_to_official
test_active_contaminated_observation_continues_diagnostic_only
test_active_contamination_does_not_start_second_observation
test_contaminated_window_start_never_moves
test_completed_contaminated_state_is_stage1_5g_invalid
test_matching_post_start_official_revision_does_not_upgrade_clean
test_unstarted_pending_fallback_can_upgrade_to_official
test_evidence_class_is_monotonic_after_observation_start
```

### 12.8 Stage 1.5G tests

```text
test_stage1_5g_uses_latest_state_for_anchor_contamination
test_anchor_contract_hash_mismatch_is_invalid
test_initial_clean_label_cannot_override_later_contamination
test_completed_state_preserves_admission_and_latest_anchor_contracts
test_exchangeinfo_fallback_blocks_clean_depth_evidence_pass
test_anchor_revision_contaminated_blocks_clean_and_recovery_evidence
test_v2_official_schedule_anchor_allows_existing_clean_thresholds
test_malformed_anchor_contract_is_invalid
```

### 12.9 v1 compatibility tests

```text
test_v1_compatibility_default_is_disabled
test_v1_row_is_nonconsumable_without_explicit_override
test_v1_compatibility_root_cannot_emit_clean_evidence
test_v1_and_v2_rows_cannot_mix_in_same_live_root
```

### 12.10 Deployment glob regression

```text
test_stage1_5f_deployment_events_glob_contains_no_literal_backslash
test_stage1_5f_deployment_events_glob_matches_event_files_before_startup
```

## 13. GIGADEV Regression Fixture

Freeze GIGADEV evidence:

```text
article_id = e8bfd0c5adaf4d8a880bb1b7327107ef
symbol = GIGADEVUSDT
official_schedule_anchor_ms = 1785735000000
exchangeinfo_onboardDate_ms = 1785722400000
disagreement_ms = 12600000
disagreement_direction = exchangeinfo_earlier
incident_class = exchangeinfo_onboarddate_earlier_than_official_schedule
expected_contract_version = 2
expected_primary_anchor_source = official_schedule_anchor
expected_no_anchor_conflict = true
expected_clean_evidence_for_historical_incident = false
```

Metadata must include:

```text
data_quality = production_incident_evidence + official_bapi_payload
not_clean_evidence_reason = missed_recovery_window_due_to_prior_deployment_and_anchor_precedence_bugs
request_id
fetched_at_ms
payload_sha256
fixture_sha256
request_manifest_path
parser_version
point_in_time_status
```

## 14. Production Acceptance

New root acceptance for the next comparable event:

```text
1. 1.5D runtime gate advertises formal_event_contract_versions_supported = [2].
2. 1.5D event row has formal_event_contract_version = 2.
3. anchor_precedence_policy = official_schedule_priority_v1.
4. All anchor evidence and revision fields are per-symbol.
5. If official schedule exists as of decision, effective observation anchor equals selected official schedule anchor.
6. exchangeInfo onboardDate mismatch is diagnostic only.
7. 1.5F does not enter pending_anchor_conflict solely due to exchangeInfo/official schedule disagreement.
8. exchangeInfo fallback cannot produce eligible_clean_start.
9. accepted/state/completed preserve anchor contract lineage hashes.
10. Stage 1.5G invalidates fallback clean claim, contamination, malformed contract, and lineage mismatch.
11. Deployment check confirms events/*.jsonl matches files and argv does not contain \*.jsonl.
```

GIGADEV historical root acceptance:

```text
expected = diagnostic regression only
allowed_next_action = fix_and_wait_for_next_live_event
clean_evidence_claim_allowed = false
```

## 15. Rollback

If v2 anchor contract causes unexpected active admissions or malformed source churn:

```text
1. Stop only the new Stage 1.5F root.
2. Keep Stage 1.5D read-only collector running only if runtime gate remains ready.
3. Preserve event rows, schedule revision rows, raw payloads, summaries, watermark, observer_state, event_batch_registry.
4. Do not delete old roots before evidence sync.
5. Revert code only after preserving failing fixtures.
6. No paper/live/execution state is affected because all execution flags remain false.
```

## 16. Decisions

```text
formal_event_contract_version = 2 is required.
anchor_precedence_policy = official_schedule_priority_v1 is required.
point-in-time official schedule selection is required.
official schedule priority is approved.
exchangeInfo secondary/fallback semantics are approved.
exchangeInfo disagreement with official schedule is diagnostic, not blocking conflict.
exchangeInfo fallback clean evidence is forbidden in first version.
evidence class after observation start is monotonic non-increasing.
schedule revision transport contract is required.
active fallback contamination continues diagnostic-only to original window end.
Stage 1.5G contamination/malformed/lineage mismatch are invalid, not quarantine.
v1 compatibility is disabled by default and isolated to diagnostic-only roots.
Old roots remain read-only and are not live-migrated.
```

## 17. Implementation Plan Gate

Implementation plan may be written only after this revised design is reviewed.

The implementation plan must include:

```text
1. shared stage1_5_launch_anchor_contract.py module
2. formal_event_contract_version = 2 and anchor_precedence_policy support
3. point-in-time schedule selection tests
4. schedule revision transport contract and replay/idempotency tests
5. v2 builder/writer fail-closed tests
6. 1.5F validator/admission tests
7. fallback revision contamination lifecycle tests
8. 1.5F -> 1.5G anchor lineage hash persistence
9. Stage 1.5G invalid blocker tests
10. v1 compatibility default-off and root isolation tests
11. deployment glob regression check
12. separate server deployment root suffix
13. explicit statement that GIGADEV cannot be backfilled as clean evidence
```
