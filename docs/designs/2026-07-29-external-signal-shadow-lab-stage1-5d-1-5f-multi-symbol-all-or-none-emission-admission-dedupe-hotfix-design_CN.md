# Stage 1.5D / 1.5F Multi-Symbol Candidate-Set Emission and Admission Dedupe Hotfix Design

```text
status = design_revised_after_external_review
scope = stage1_5d_1_5f_multi_symbol_candidate_set_emission_admission_dedupe_hotfix
trigger_incident = 2026-07-29_93b5_partial_multisymbol_live_incident
implementation_allowed = false
implementation_plan_allowed = after_revised_design_review_only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

## 1. 背景

Stage 1.5D 当前职责是发现 Binance Futures launch 公告，解析 symbol 与 per-symbol launch/onboard time，并写入可被 Stage 1.5F 消费的 event rows。Stage 1.5F 再按 event-symbol 粒度决定是否进入 `pending_launch_time_in_future`、`active`、`completed` 或 terminal state，并采集 12h public depth observation。

2026-07-29 Binance 公告触发新的生产问题：

```text
articleCode = 93b5cd2280874d9cb4303827374b940d
title = Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-29)
expected_symbols = PYPLUSDT, GSUSDT, SMHUSDT
expected_launch_times_utc = 2026-07-29T09:00:00Z, 2026-07-29T09:05:00Z, 2026-07-29T09:10:00Z
```

BAPI detail parser 已经成功解析出三个 symbols 与 launch times，说明上一轮 A827 parser hotfix 生效。但 Stage 1.5D 在 `PYPLUSDT` 先进入 `TRADING`、其余两个仍为 `PENDING_TRADING` 时，提前 emit 了只包含 `PYPLUSDT` 的 event row。随后 `GSUSDT` 与 `SMHUSDT` 逐步可 emit 时，1.5D 又写出了包含子集/全集的后续 event rows。

Stage 1.5F 进一步把同一 article 下的 `PYPLUSDT` 接收了三次，产生三个 active observations，而 `GSUSDT` / `SMHUSDT` 没有按预期成为独立 pending/active symbols。

该 root 的 93b5 样本已经被 partial multi-symbol emission 与 duplicate admission 污染，不能作为 clean 1.5G evidence。

## 2. 生产触发证据

### 2.1 Stage 1.5D scheduler 状态

BAPI detail 成功，解析结果完整：

```json
{
  "candidate_symbols": ["PYPLUSDT", "GSUSDT", "SMHUSDT"],
  "symbol_validation_status": "pending_pre_trading",
  "pending_reason": "exchangeinfo_symbol_not_yet_visible",
  "last_bapi_detail_status": "success",
  "last_bapi_parser_status": "parsed",
  "symbol_launch_times_ms": {
    "PYPLUSDT": 1785315600000,
    "GSUSDT": 1785315900000,
    "SMHUSDT": 1785316200000
  },
  "symbol_effective_launch_times_ms": {
    "PYPLUSDT": 1785315600000,
    "GSUSDT": 1785315900000,
    "SMHUSDT": 1785316200000
  }
}
```

09:00 UTC 后，exchangeInfo 状态为：

```text
PYPLUSDT = TRADING
GSUSDT = PENDING_TRADING
SMHUSDT = PENDING_TRADING
```

1.5D 写出第一条错误 consumable event：

```json
{
  "source_article_id": "93b5cd2280874d9cb4303827374b940d",
  "symbols": ["PYPLUSDT"],
  "stable_event_key": "binance_93b5cd2280874d9cb4303827374b940d_PYPLUSDT",
  "symbol_extraction_source": "bapi_article_body",
  "symbol_validation_status": "validated",
  "symbol_effective_launch_times_ms": {
    "PYPLUSDT": 1785315600000,
    "GSUSDT": 1785315900000,
    "SMHUSDT": 1785316200000
  }
}
```

后续又出现同 article 的子集/全集 event rows：

```text
row 1: symbols = [PYPLUSDT], stable_event_key = ..._PYPLUSDT
row 2: symbols = [PYPLUSDT, GSUSDT], stable_event_key = ..._MULTI
row 3: symbols = [PYPLUSDT, GSUSDT, SMHUSDT], stable_event_key = ..._MULTI
```

### 2.2 Stage 1.5F admission 状态

Stage 1.5F accepted rows 中，同一 article-symbol `93b5...|PYPLUSDT` 被接受三次：

```text
accepted 1: symbol = PYPLUSDT, evidence_start_class = clean_start
accepted 2: symbol = PYPLUSDT, evidence_start_class = recovery_validation_only
accepted 3: symbol = PYPLUSDT, evidence_start_class = recovery_validation_only
```

summary 显示：

```text
post_watermark_events_accepted = 3
active_observation_count = 3
pending_launch_observation_count = 0
```

这不是 clean multi-symbol observation，而是 admission duplicate。

## 3. 根因

### 3.1 Stage 1.5D 允许 partial multi-symbol emission

当前 1.5D 有多处路径以如下条件 emit event：

```python
if validation_result["validated_symbols"]:
    normalize_live_event(..., symbols_override=validation_result["validated_symbols"])
    detail_retry_state.pop(code, None)
```

这对 single-symbol article 可接受，但对 multi-symbol article 是错误语义。`validated_symbols` 是当前 exchangeInfo 已进入 emittable status 的子集，不代表整篇公告的 candidate set 已经完整可交付给 1.5F。

代码中已经存在 `is_multi_symbol_article_ready_to_emit(...)` helper，但生产行为证明它没有作为所有 consumable emit path 的硬门禁，或者其语义错误地等价于“全部已 TRADING”。

### 3.2 Stage 1.5D partial emit 后丢失 article-level pending state

第一条 partial event emit 后，runner 执行 `detail_retry_state.pop(code, None)`。生产输出显示后续 scheduler state 可回退到：

```json
{
  "candidate_symbols": null,
  "symbol_validation_status": null,
  "pending_reason": "title_symbol_missing",
  "symbol_effective_launch_times_ms": null
}
```

这会丢失已解析的 article-level candidate set 与 launch times，使后续 poll 重新发现/重新解析/重新 emit，形成 revision-like event churn。

### 3.3 Stage 1.5D emission 幂等缺少 durable contract

即使 full candidate set emit 后，如果只依赖 `seen_event_ids` 进程内集合或 `detail_retry_state.pop(code)`，runner 重启后仍可能重新读取 announcement list、重新解析同一 article，并重复 append event row。

因此 1.5D 需要 durable emission registry 或 terminal scheduler state，不能只在内存里防重。

### 3.4 Stage 1.5D event identity 随子集变化

同一 article 在不同时间 emit 不同 symbol 子集时，`event_id` 与 `stable_event_key` 会变化：

```text
[PYPLUSDT] -> ..._PYPLUSDT
[PYPLUSDT, GSUSDT] -> ..._MULTI
[PYPLUSDT, GSUSDT, SMHUSDT] -> ..._MULTI with different event_id/detected_at
```

这让下游无法仅依赖 `event_id` 判断同一 article 的 revision 与 duplicate。

### 3.5 Stage 1.5F active/pending/completed 缺少 stable key 全状态去重

1.5F 当前已有：

```text
stable_event_symbol_key = event_type|source_article_id|symbol
```

这已经是 article-symbol 级身份，不应再新增第二套 canonical key。问题是当前 full-state dedupe 没有统一基于该 key 覆盖 active/pending/completed/terminal states，并且启动时没有检测同一 stable key 对应多个 `event_symbol_id` 的 collision。

### 3.6 Stage 1.5F 同一 row 内过早更新 watermark，导致 sibling symbols 被压掉

`flatten_event_symbols(event)` 会把一个 multi-symbol row 展开为多个 flat symbols。当前 runner 在第一个 flat symbol accepted 后立即执行：

```python
watermark = update_watermark_with_event(watermark, flat_event)
```

`update_watermark_with_event` 会把 `source_article_id` 加入 `seen_source_article_ids`。同一 row 的后续 sibling symbols 再进入 classify 时，`event_is_post_watermark` 会因为 `source_article_id` 已 seen 而返回 false。

同时 `delayed_launch_event_symbol_is_post_watermark` 目前只允许：

```text
symbol_extraction_source in {title_contract_symbol, detail_contract_symbol}
```

BAPI rows 使用 `bapi_article_body`，所以 delayed launch 例外不会救回 GS/SMH。这解释了为什么生产中只看到 PYPLUSDT 被重复 accepted，而不是三个 symbols 被完整 accepted/pending。

## 4. 设计目标

必须实现：

```text
1. Stage 1.5D multi-symbol article 默认 all-or-none candidate-set emission。
2. All-or-none 约束的是“整篇公告候选集合完整且每个 symbol 可验证/有 anchor”，不是“所有合约都已经 TRADING”。
3. 1.5D 必须在首个 launch 前尽早写出完整 article row，让 1.5F 按 per-symbol anchor pending→active。
4. 1.5D pending 状态必须持久保留完整 article candidate set、per-symbol launch/onboard/effective times、validation split 与下一次 validation 时间。
5. 所有 1.5D emit path 必须共享同一个 candidate-set readiness gate，不能只修 BAPI path。
6. 1.5D full emission 必须有 durable registry/terminal state，重启后不得重复 append。
7. 1.5F 必须升级现有 stable_event_symbol_key 为全状态幂等 key。
8. 1.5F 必须检测同一 stable key 对应多个 states 的 identity collision，不能 dict 覆盖掩盖污染。
9. 1.5F 对同一 multi-symbol event row 必须 batch-safe：处理完 row 内所有 symbols 并确认 durable 后再推进 watermark。
10. 旧污染 root 不回写、不清洗、不升级为 clean evidence。
```

非目标：

```text
不改变 Stage 1.5G clean/quarantine 阈值。
不补录 93b5 为 clean evidence。
不放宽 launch-time gated observation 的 anchor 规则。
不改变 BAPI transport trust 口径。
不允许 paper/live/execution/trade/alpha。
```

## 5. Stage 1.5D All-or-None Candidate-Set Emission Policy

### 5.1 Article-Level Candidate Set

1.5D 必须把 trusted parser 输出视为 article-level immutable candidate set：

```json
{
  "source_article_id": "93b5cd2280874d9cb4303827374b940d",
  "candidate_symbols_ordered": ["PYPLUSDT", "GSUSDT", "SMHUSDT"],
  "candidate_symbols_normalized": ["GSUSDT", "PYPLUSDT", "SMHUSDT"],
  "candidate_symbol_set_hash_version": 1,
  "candidate_symbol_set_hash": "sha256(canonical_json(candidate_symbols_normalized))",
  "symbol_launch_times_ms": {...},
  "symbol_effective_launch_times_ms": {...}
}
```

Hash 规范：

```text
normalize = strip + uppercase + unique + lexicographic sort
serialize = JSON UTF-8 with separators=(",", ":") and fixed ensure_ascii setting
hash = SHA256(serialized bytes)
```

`candidate_symbols_ordered` 保留公告顺序，用于 launch schedule 审计；`candidate_symbols_normalized` 用于身份和幂等。

同一 article 后续 poll 不允许把该状态重置为 `title_symbol_missing`，除非出现 hard identity mismatch 或 parser integrity failure。

### 5.2 Candidate-Set Readiness

新增统一判定：

```text
article_candidate_set_ready_to_emit =
  all candidate symbols are parsed from trusted article source
  AND all candidate symbols appear in exchangeInfo
  AND every candidate has allowed contractType / quoteAsset / marginAsset
  AND every candidate status is in validatable statuses:
      PENDING_TRADING, PRE_TRADING, TRADING
  AND every candidate has trusted effective launch time > 0
  AND no hard rejected symbol exists
```

禁止把 readiness 定义为：

```text
set(validated_symbols) == set(candidate_symbols)
all symbols are TRADING
```

正确流程：

```text
1.5D before first launch:
  symbols = [PYPLUSDT, GSUSDT, SMHUSDT]
  symbol_exchangeinfo_statuses = {
    PYPLUSDT: PENDING_TRADING,
    GSUSDT: PENDING_TRADING,
    SMHUSDT: PENDING_TRADING
  }
  emit one complete article row

1.5F:
  PYPLUSDT -> pending until 09:00, then active
  GSUSDT   -> pending until 09:05, then active
  SMHUSDT  -> pending until 09:10, then active
```

这保留最早 symbol 的 clean-start 机会。

### 5.3 Pending State Contract

candidate set 尚未 ready 时，scheduler state 必须写入：

```json
{
  "symbol_validation_status": "pending_candidate_set_readiness",
  "pending_reason": "multi_symbol_candidate_set_not_ready",
  "candidate_symbols": ["PYPLUSDT", "GSUSDT", "SMHUSDT"],
  "exchangeinfo_visible_symbols": ["PYPLUSDT", "GSUSDT"],
  "exchangeinfo_missing_symbols": ["SMHUSDT"],
  "hard_rejected_symbols": [],
  "symbol_exchangeinfo_statuses": {
    "PYPLUSDT": "PENDING_TRADING",
    "GSUSDT": "PENDING_TRADING"
  },
  "next_exchangeinfo_validation_at_ms": 0,
  "last_exchangeinfo_validation_at_ms": 0,
  "exchangeinfo_validation_attempt_count": 0
}
```

如果存在 hard rejected symbol：

```text
no consumable event
status = terminal_multi_symbol_candidate_validation_rejected
rejection_reasons_by_symbol persisted
consumable_by_stage1_5f = false
```

Hard reject 仅限：

```text
wrong contract type
wrong quote/margin asset
明确不允许的产品族
identity mismatch
trusted parser integrity conflict
超过 validation deadline 后仍不可验证
```

以下不允许 hard reject：

```text
symbol temporarily missing from exchangeInfo
PENDING_TRADING
PRE_TRADING
exchangeInfo temporarily unavailable
```

## 6. Stage 1.5D Durable Emission Contract

### 6.1 Full Emission Row

当 multi-symbol article 满足 candidate-set readiness 后，1.5D 只写一条 article-level consumable row：

```json
{
  "source_article_id": "93b5cd2280874d9cb4303827374b940d",
  "symbols": ["PYPLUSDT", "GSUSDT", "SMHUSDT"],
  "stable_event_key": "binance_93b5cd2280874d9cb4303827374b940d_MULTI",
  "multi_symbol_emission_mode": "all_or_none_candidate_set",
  "multi_symbol_candidate_set_hash": "...",
  "symbol_validation_status": "validated_candidate_set",
  "symbol_exchangeinfo_statuses": {
    "PYPLUSDT": "PENDING_TRADING",
    "GSUSDT": "PENDING_TRADING",
    "SMHUSDT": "PENDING_TRADING"
  }
}
```

禁止写出：

```text
[PYPLUSDT]
[PYPLUSDT, GSUSDT]
[PYPLUSDT, GSUSDT, SMHUSDT] as later duplicate revision for same candidate set
```

### 6.2 Emission ID

新增 durable emission identity：

```text
emission_id = sha256(
  identity_schema_version
  | normalized_source_namespace
  | event_type
  | source_article_id
  | candidate_symbol_set_hash
)
```

`normalized_source_namespace` 固定枚举：

```text
binance_futures_announcement
```

不能直接使用原始 `source_name`，避免历史命名漂移导致 identity 分裂。

### 6.3 Emission Registry / Terminal State

full emission 后不得简单 `detail_retry_state.pop(code)`。必须采用以下任一方案：

```text
方案 A: scheduler state 转为 terminal emitted_all_symbols
方案 B: append-only emitted_article_registry.jsonl
```

最小字段：

```json
{
  "status": "emitted_all_symbols",
  "source_article_id": "93b5cd2280874d9cb4303827374b940d",
  "candidate_symbol_set_hash": "...",
  "emission_id": "...",
  "emitted_at_ms": 0,
  "event_id": "...",
  "event_stream_path": "events/2026-07-29.jsonl",
  "parser_payload_hash": "..."
}
```

runner 启动时必须扫描已有 event stream 重建 emission index，避免 scheduler state 文件单独损坏或 crash window 导致重复 append。

Crash consistency：

```text
crash after event append before state write:
  startup scans events stream and rebuilds emitted index; no duplicate append

crash after state write before event append:
  startup detects missing event_stream row and reconciles by appending exactly once or emitting diagnostic requiring manual review
```

### 6.4 Candidate-Set Revision Conflict

同一 article 后续 payload 解析出不同 candidate set 时：

```text
status = terminal_candidate_set_revision_conflict
consumable_by_stage1_5f = false
automatic_reopen = false
manual_review_required = true
```

必须保留：

```text
original_candidate_set_hash
latest_candidate_set_hash
original_payload_hash
latest_payload_hash
revision_detected_at_ms
```

## 7. Stage 1.5F Stable Event-Symbol Key Contract

### 7.1 Reuse Existing Stable Key

不新增第二套 canonical identity。第一版升级现有：

```text
stable_event_symbol_key = event_type|source_article_id|symbol
```

为全状态 canonical key。

如果需要版本化，使用：

```text
stable_event_symbol_key_version = 2
stable_event_symbol_key = normalized_source_namespace|event_type|source_article_id|normalized_symbol
```

但 `normalized_source_namespace` 必须来自固定枚举，不能直接使用原始 `source_name`。

### 7.2 Full-State Index 与 Collision Detection

加载 `observer_state.jsonl` 时必须建立：

```text
stable_event_symbol_key -> list[states]
```

不能使用 dict 静默覆盖。

启动 invariant：

```text
count == 1:
  normal

count > 1:
  canonical_identity_collision = true
  block_new_admission = true
  do not choose winner
  do not delete existing state
  emit collision diagnostic
```

collision 覆盖：

```text
active + active
active + completed
pending + active
terminal + active
```

新 root 中：

```text
duplicate_active_article_symbol_count > 0
```

必须是 blocker，而不是普通 summary metric。

### 7.3 Admission Dedupe Order

admission 前顺序必须固定：

```text
1. exact event_symbol_id replay + same payload hash
   => silent no-op
   => do not increment duplicate revision counter

2. same stable_event_symbol_key and existing pending state
   => call/update pending revision path
   => update anchor/payload metadata if safe
   => do not create second state
   => do not write second accepted row

3. same stable_event_symbol_key and existing active/completed state
   => suppress admission
   => record duplicate_revision_seen
   => do not reopen observation

4. same stable_event_symbol_key and terminal state
   => first version no reopen
   => record terminal_revision_seen
   => do not upgrade to clean

5. unknown stable key
   => normal classify/admit
```

这避免把合法 pending revision 更新误判成 duplicate，也避免每 poll 正常重读 event stream 时 counter 持续上涨。

建议计数拆分：

```text
exact_event_replay_suppressed_total
duplicate_revision_admission_suppressed_total
canonical_identity_collision_total
terminal_revision_seen_total
```

## 8. Stage 1.5F Batch-Safe Watermark and Crash Recovery

对同一 source event row，1.5F 必须按 batch 处理所有 flattened symbols：

```text
1. read one original event row
2. compute event_batch_id and batch_candidate_set_hash
3. flatten symbols
4. classify every symbol using the same immutable pre-row watermark snapshot
5. compute every symbol decision
6. persist state / accepted / rejected / pending for each sibling
7. verify every sibling has durable state
8. write batch_registered state/diagnostic
9. update watermark once for the original event row
```

Watermark 语义：

```text
article row fully registered
```

不是：

```text
all sibling symbols accepted
```

只要每个 sibling 已进入 durable 状态即可更新 article watermark：

```text
accepted
pending_launch_time_in_future
pending_launch_anchor_missing
pending_anchor_conflict
pending_observation_capacity
rejected
ignored
diagnostic_terminal
```

### 8.1 Batch State

新增或持久化：

```json
{
  "event_batch_id": "sha256(source_article_id|event_id|candidate_symbol_set_hash)",
  "batch_symbol_count": 3,
  "batch_candidate_set_hash": "...",
  "batch_registration_status": "registered",
  "batch_registered_symbol_keys": [
    "futures_contract_launch|93b5...|PYPLUSDT",
    "futures_contract_launch|93b5...|GSUSDT",
    "futures_contract_launch|93b5...|SMHUSDT"
  ]
}
```

Crash recovery：

```text
crash after symbol 1 state write:
  restart sees durable state for symbol 1
  processes remaining symbols using same batch id
  no duplicate accepted row

crash after symbol 2 accepted row before watermark:
  restart reconciles accepted/state pair
  processes symbol 3
  updates watermark once after all durable

crash before watermark update:
  exact replay no-op for durable siblings
  watermark updates after batch complete
```

硬不变量：

```text
watermark update for first sibling cannot block later siblings from the same event row.
```

## 9. Per-Symbol Staggered Promotion Semantics

1.5D 完整 article row 可以早于首个 launch 进入 1.5F。1.5F 对每个 symbol 单独使用自己的 anchor：

```text
PYPLUSDT observation_anchor_ms = 1785315600000
GSUSDT   observation_anchor_ms = 1785315900000
SMHUSDT  observation_anchor_ms = 1785316200000
```

动态验收应按时间点检查：

```text
09:01 UTC:
  PYPLUSDT = active
  GSUSDT = pending_launch_time_in_future
  SMHUSDT = pending_launch_time_in_future

09:06 UTC:
  PYPLUSDT = active
  GSUSDT = active
  SMHUSDT = pending_launch_time_in_future

09:11 UTC:
  PYPLUSDT = active
  GSUSDT = active
  SMHUSDT = active
```

禁止把验收写成“一次检查必须 accepted_count == active_count == 3”。

## 10. Contaminated Root Handling

当前 root 中的 93b5 样本必须标记为污染：

```text
stage1_5d_root = live_event_source_continuous_20260728T061352Z_7d_bapi_table_runtime_gate_hotfix
stage1_5f_root = live_depth_observer_20260728T061749Z_7d_bapi_table_runtime_gate_hotfix
incident_label = partial_multisymbol_emit_and_duplicate_admission_contaminated
clean_depth_evidence_allowed = false
```

本 hotfix 不追溯删除服务器旧 rows。正确动作是：

```text
preserve raw evidence
exclude 93b5 current-root observations from clean 1.5G evidence
start new root after hotfix if no active observation should be preserved
```

停止旧 1.5F 前必须检查 active states grouped by `source_article_id`：

```text
全部 active 都属于 93b5 污染状态:
  可以停止旧 1.5F

存在其它可能有效 active observation:
  旧 root drain-only
  不再允许新 admission
  等其它 observation 完成后再停止
```

不能为了停止 duplicate PYPLUSDT 而截断同 root 内其它有效 12h observation。

## 11. Summary 与 Diagnostics

### 11.1 Stage 1.5D Summary

新增或派生以下字段：

```text
multi_symbol_candidate_set_emission_enabled
multi_symbol_candidate_set_ready_count
multi_symbol_candidate_set_pending_count
multi_symbol_partial_emit_prevented_count
multi_symbol_full_emit_count
multi_symbol_emission_registry_count
multi_symbol_candidate_set_hash_mismatch_count
multi_symbol_candidate_state_reset_prevented_count
multi_symbol_validation_rejected_count
```

### 11.2 Stage 1.5F Summary

新增或派生以下字段：

```text
stable_event_symbol_full_state_dedupe_enabled
exact_event_replay_suppressed_total
duplicate_revision_admission_suppressed_total
canonical_identity_collision_total
duplicate_active_article_symbol_count
batch_watermark_update_enabled
same_event_sibling_watermark_suppressed_count
partial_revision_after_acceptance_count
contaminated_event_symbol_count
block_new_admission_due_to_identity_collision
```

Diagnostics sample cap 必须沿用已有 sample-capped diagnostic 设计，不能产生新的无限增长流。

## 12. Required Tests

### 12.1 Stage 1.5D TDD

必须新增或修订测试：

```text
test_full_article_emits_before_first_launch_when_all_symbols_validatable
test_staggered_symbols_do_not_wait_until_all_trading
test_full_row_contains_per_symbol_pretrading_status
test_multi_symbol_article_does_not_emit_partial_event_when_only_one_symbol_trading
test_multi_symbol_article_retains_pending_symbols_and_launch_times_before_candidate_set_ready
test_multi_symbol_article_with_one_hard_rejected_symbol_does_not_emit_partial_event
test_list_poll_does_not_reset_pending_candidate_state_to_title_symbol_missing
test_93b5_staggered_launch_fixture_candidate_set_emission
test_full_emit_survives_restart_without_duplicate_append
test_full_emit_terminal_state_survives_compaction
test_existing_event_stream_rebuilds_emission_index
test_crash_after_event_append_before_state_write_does_not_duplicate
test_crash_after_state_write_before_event_append_reconciles_missing_event
test_candidate_set_revision_conflict_is_terminal
```

Fixture 必须覆盖 93b5 staggered status：

```text
pre-launch all symbols PENDING_TRADING and visible -> one full article row
09:00 PYPLUSDT TRADING, GSUSDT/SMHUSDT PENDING_TRADING -> no partial row
09:05 PYPLUSDT/GSUSDT TRADING, SMHUSDT PENDING_TRADING -> no partial row
09:10 all TRADING -> no duplicate full row for same candidate set
```

### 12.2 Stage 1.5F TDD

必须新增或修订测试：

```text
test_existing_stable_event_symbol_key_is_used_as_canonical_identity
test_source_name_alias_does_not_create_duplicate_identity
test_startup_detects_two_active_states_with_same_stable_key
test_startup_detects_active_and_completed_same_stable_key
test_identity_collision_blocks_new_admission
test_identity_collision_does_not_delete_existing_state
test_pending_revision_updates_existing_state
test_exact_row_replay_does_not_increment_revision_duplicate_counter
test_same_source_article_symbol_cannot_be_accepted_multiple_times_across_event_revisions
test_multi_symbol_event_row_processes_all_symbols_before_watermark_update
test_three_staggered_symbols_promote_at_their_own_anchor
test_crash_after_first_sibling_state_write_recovers_batch
test_crash_after_second_sibling_acceptance_recovers_remaining_symbol
test_crash_before_watermark_update_does_not_duplicate_accepted_rows
test_watermark_updates_once_after_all_siblings_durable
test_old_contaminated_root_is_not_stage1_5g_consumable
```

### 12.3 Regression Tests

必须保证：

```text
single-symbol title event still emits normally
historical pre-bootstrap terminal ignore remains idempotent
runtime gate ready/blocking behavior unchanged
A827 BAPI table parser fixture still passes
no pre-launch depth request occurs after early full article emission
```

## 13. Deployment Design

建议新 root suffix：

```text
7d_multisymbol_candidate_set_dedupe_hotfix
```

部署前必须确认旧 root 无需要保护的有效 active observation。若旧 1.5F 仍有 active duplicate observations，应按第 10 节先分组确认后再停止或 drain-only。

新 1.5D 启动必须继续写 runtime gate：

```text
--output-root data/external_signal_shadow/stage1_5d/live_event_source_continuous_<RUN_ID>_7d_multisymbol_candidate_set_dedupe_hotfix
--output-summary <same root>/binance_futures_launch_smoke_summary.json
```

新 1.5F 必须先 bootstrap 新 watermark，再使用同 root runtime gate 启动正常 observer：

```text
# bootstrap watermark
--stage1-5d-events-glob <new 1.5D root>/events/*.jsonl
--stage1-5d-runtime-gate <new 1.5D root>/live_safety_gate_summary.json
--output-root <new 1.5F root>
--bootstrap-watermark

# normal observer
--stage1-5d-events-glob <new 1.5D root>/events/*.jsonl
--stage1-5d-runtime-gate <new 1.5D root>/live_safety_gate_summary.json
--stage1-5e-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
--output-root <new 1.5F root>
--live-public-readonly
```

禁止回到 cross-root `--stage1-5d-summary` 作为 live gate。

## 14. Production Verification

对下一次 multi-symbol TradFi article，检查标准按时间分层。

### 14.1 1.5D Pre-Launch

```text
1. BAPI detail success and parser parsed symbols + launch times.
2. 所有 symbols 已出现在 exchangeInfo 且 status 属于 validatable statuses。
3. 1.5D events 中出现一条 full article row。
4. 没有任何子集 row。
5. emitted registry / terminal state 记录 emission_id。
```

### 14.2 1.5F Pre-Launch

```text
1. 1.5F 为每个 symbol 建立 durable pending/active state。
2. 同一 event row 的 sibling symbols 不被 watermark 压掉。
3. batch_registered 后 watermark 只更新一次。
```

### 14.3 Per-Symbol Launch

```text
at PYPLUSDT anchor:
  PYPLUSDT promoted active once
  GSUSDT/SMHUSDT remain pending

at GSUSDT anchor:
  GSUSDT promoted active once
  PYPLUSDT remains active
  SMHUSDT remains pending

at SMHUSDT anchor:
  SMHUSDT promoted active once
```

### 14.4 Dedupe

```text
exact_event_replay_suppressed_total may increase silently or as no-op metric
duplicate_revision_admission_suppressed_total must not grow every poll
canonical_identity_collision_total = 0 for new clean root
duplicate_active_article_symbol_count = 0
same_event_sibling_watermark_suppressed_count = 0
```

针对 93b5 当前 root，仅允许作为 bug regression fixture，不允许作为 clean 生产通过证据。

## 15. Done Definition

本 hotfix 完成条件：

```text
1. 所有 Required Tests 通过。
2. 代码 grep 证明所有 1.5D consumable emit path 都经过 candidate-set readiness gate。
3. 代码 grep 证明 1.5D full emission 有 durable registry 或 terminal state。
4. 代码 grep 证明 1.5F accepted/pending/admission path 都先查 stable_event_symbol_key 全状态 index。
5. 代码 grep 证明 1.5F batch watermark update 在 sibling durable registration 之后执行。
6. 93b5 fixture replay 在 pre-launch all symbols validatable 时写一条 full row。
7. 93b5 fixture replay 在 staggered TRADING visibility 下不会写 partial row。
8. 93b5 fixture replay 不重复 append full row after restart。
9. 1.5F fixture replay 对 full row 创建 PYPLUSDT/GSUSDT/SMHUSDT 三个 durable states，并按各自 anchor promotion。
10. runtime gate 仍为 same-root dependency，cross_root_upstream_summary_dependency=false。
11. 未改变任何 trade/paper/live/execution/alpha safety flags。
```
