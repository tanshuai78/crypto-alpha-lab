# Stage 1.5D Schedule Revision Producer Rules Design

**日期:** 2026-08-04  
**关联主设计:** `docs/designs/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-launch-time-priority-anchor-precedence-hotfix-design_CN.md`  
**关联实现计划:** `docs/plans/2026-08-03-external-signal-shadow-lab-stage1-5d-1-5f-official-schedule-priority-anchor-contract-v2-hotfix-implementation-plan_CN.md`  
**范围:** Stage 1.5D automatic schedule revision producer classifier only  
**状态:** design draft

---

## 1. 当前结论

```text
decision = stage1_5d_schedule_revision_producer_rules_ready_for_review
scope = stage1_5d_revision_detection_linking_and_formal_row_emission
consumer_contract_already_exists = true
automatic_revision_producer_classifier = design_defined_pending_implementation
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

Stage 1.5D / 1.5F official schedule priority v2 已经具备：

```text
1. formal_event_contract_version = 2 launch row。
2. formal_schedule_revision_contract_version = 1 transport row。
3. Stage 1.5F schedule revision registry / idempotency / state contamination 处理。
4. Stage 1.5G anchor lineage invalidation。
```

但当前仍缺少 Stage 1.5D 自动 producer 规则：什么 Binance 官方公告能被识别为 `futures_contract_launch_schedule_revision`，如何关联原始 launch article，以及什么时候必须 fail closed。

本设计只补 producer classifier，不改变 v2 transport / 1.5F consumer / 1.5G reviewer 的既有 contract。

---

## 2. 问题背景

上一轮 v2 修复解决了 GIGADEV 类问题：official launch time 必须优先于 exchangeInfo onboardDate。该修复同时预留了 schedule revision transport：

```text
event_type = futures_contract_launch_schedule_revision
formal_schedule_revision_contract_version = 1
```

但是主设计明确留下 follow-up：

```text
automatic_revision_producer_classifier = follow_up_required
```

如果没有 producer 规则，系统遇到 Binance 后续发布的 postpone / reschedule / cancel 公告时只能做到两件事之一：

```text
1. 不产生 revision row，1.5F 无法更新 pending/active/completed lineage。
2. 过度宽松地按 symbol 推断 revision，可能把无关公告错误关联到旧 launch event。
```

第二种风险更高。错误 revision 会污染 12h depth evidence，可能把原本 clean 的 observation 标成 contaminated，或更严重地错误修改观察 anchor。

---

## 3. 设计目标

```text
P0: 定义哪些 Binance 官方公告可成为 schedule revision。
P0: 定义 linked / orphaned / ambiguous 三类关联结果。
P0: 定义 supersedes_source_article_id 的证据优先级。
P0: 明确 symbol-only 推断的禁用边界。
P0: 支持 single-symbol 和 multi-symbol revision。
P0: 所有不确定情况 fail closed，只写 diagnostic，不写 formal revision row。
```

成功标准：

```text
1. 只有 linked revision 能调用 build_formal_schedule_revision_row(...)。
2. orphaned / ambiguous revision 只写 diagnostic，不进入 events/*.jsonl formal revision path。
3. 一个 revision article 中任一 symbol 关联不确定时，该 symbol 不写 formal row。
4. multi-symbol revision 可以对已 linked 的 symbols 分别写 per-symbol formal revision row；不要求全批 all-or-none。
5. 不改变任何交易、安全、执行权限。
```

---

## 4. 非目标

```text
1. 不实现新 exchange 私有 API。
2. 不启用 paper/live/execution/alpha。
3. 不改变 formal_schedule_revision_contract_version = 1 的字段契约。
4. 不重写 Stage 1.5F schedule revision registry。
5. 不把 spot/margin/delisting/leverage adjustment 公告纳入本轮 revision producer。
6. 不允许仅凭 symbol 相同就自动关联原始 launch article。
```

---

## 5. Revision 公告分类规则

### 5.1 可纳入 revision classifier 的公告范围

必须同时满足：

```text
source_name = binance_official_announcements
source_profile = binance_official_announcements_like_rows
announcement_category = futures / USDⓈ-M / COIN-M launch related
article is public official Binance announcement
text references futures contract launch schedule lifecycle
```

允许的 revision intent：

```text
rescheduled_with_new_anchor:
  Binance Futures Will Reschedule/Postpone/Delay the Launch of <SYMBOL> ... to <NEW_TIME>
  Binance Futures Will Launch <SYMBOL> ... at <NEW_TIME> instead of <OLD_TIME>

postponed_without_anchor:
  Binance Futures Will Postpone the Launch of <SYMBOL> Perpetual Contract
  no new launch time is provided

cancelled:
  Binance Futures Will Cancel/Not Proceed with the Launch of <SYMBOL> Perpetual Contract
```

允许的关键词族：

```text
reschedule_keywords = reschedule, re-schedule, delay, delayed, postpone to, postponed to, will launch at, instead of
postpone_keywords = postpone, postponed, delay, delayed
cancel_keywords = cancel, cancelled, will not launch, not proceed
```

关键词只用于候选识别，不能单独证明可发 formal row。formal row 还必须通过第 6 章 linking 规则。

### 5.2 明确不属于 revision 的公告

以下公告即使含有同一 symbol，也不得产生 schedule revision：

```text
1. 新 futures contract launch 公告。
2. spot / margin / earn / options 上线公告。
3. futures delisting / settlement / delivery / trading pair removal 公告。
4. leverage and margin tier update。
5. funding rate cap / tick size / min notional / risk parameter update。
6. trading competition / promotion / fee discount。
7. maintenance / API / websocket / system upgrade。
8. post-launch reminder / recap / generic product notice。
```

这些情况如被 parser 识别为疑似 revision，应写 diagnostic：

```text
diagnostic_type = schedule_revision_candidate_rejected_non_launch_revision_scope
```

---

## 6. supersedes_source_article_id 关联规则

### 6.1 关联状态

每个 revision candidate 的每个 symbol 必须被分类为：

```text
linked:
  已确定唯一原始 launch article。

orphaned:
  找不到可关联的原始 launch article。

ambiguous:
  找到多个可能原始 launch article，或证据冲突。

out_of_scope:
  公告不是 futures launch schedule revision。
```

只有 `linked` 允许写 formal revision row。其余状态只写 diagnostic。

### 6.2 证据优先级

`supersedes_source_article_id` 的证据优先级从高到低：

```text
L1 explicit_source_article_id:
  revision article body 中明确链接或引用原始 articleCode/source_article_id。
  这是最高可信来源。

L2 explicit_original_title_or_url:
  revision article body 中包含原始公告 URL、标题、或可唯一反查到 source_article_id 的 canonical slug。

L3 unique_symbol_original_schedule_match:
  revision article 给出 symbol + superseded_anchor_ms / original launch time，且本地 Stage 1.5D state/events 中只有一个原始 launch row 同时满足：
    same symbol
    same event_type = futures_contract_launch
    original official schedule anchor == superseded_anchor_ms
    source_published_at_ms <= revision_available_at_ms
    article age within configured revision lookback window

L4 unique_symbol_pending_match_without_old_anchor:
  revision article 只给 symbol 和 postponed/cancelled intent，无 superseded anchor；本地只有一个 pending/known original launch article for same symbol within lookback window。
  仅允许对 postponed_without_anchor/cancelled 使用。
```

禁止规则：

```text
1. 不能只凭 symbol 相同关联。
2. 不能使用 future event row 作为 original。
3. 不能用 lexical revision_id 排序解决语义冲突。
4. 不能跨 event family 关联，例如 delisting notice 不能 supersede launch notice。
5. 不能把同一 revision article 同一 symbol 同时关联到多个 original。
```

### 6.3 lookback window

默认 lookback 从 config 读取：

```text
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_LOOKBACK_DAYS = 14
```

安全边界：

```text
min = 1 day
recommended = 14 days
max = 30 days
```

超过 lookback 的候选不写 formal row，写 diagnostic：

```text
diagnostic_type = schedule_revision_original_outside_lookback
```

---

## 7. 时间锚点解析规则

### 7.1 revised_anchor_ms

`revised_anchor_ms` 来源优先级：

```text
1. revision article body 中明确的新 launch time。
2. revision article table 中 per-symbol launch time。
3. title 中明确的新 launch date/time。
```

必须保留 provenance：

```text
raw_time_text
timezone_text
node_path
logical_block_id
schedule_text_context
payload_sha256
parser_version
mapping_method
```

### 7.2 superseded_anchor_ms

`superseded_anchor_ms` 来源优先级：

```text
1. revision article body 显式旧 launch time。
2. linked original launch row 的 symbol_official_schedule_anchor_ms。
3. linked original launch row 的 symbol_effective_observation_anchor_ms，前提是 source = official_schedule_anchor。
```

如果原始 launch row 只有 exchangeInfo fallback anchor：

```text
superseded_anchor_ms may be null
revision_reason must reflect fallback_original_anchor_unknown
max_evidence_class remains diagnostic/recovery only
```

### 7.3 status 到 anchor 映射

```text
rescheduled_with_new_anchor:
  symbol_official_schedule_statuses[symbol] = rescheduled
  symbol_revised_anchor_ms[symbol] = parsed new anchor

postponed_without_anchor:
  symbol_official_schedule_statuses[symbol] = postponed_without_anchor
  symbol_revised_anchor_ms[symbol] = null

cancelled:
  symbol_official_schedule_statuses[symbol] = cancelled
  symbol_revised_anchor_ms[symbol] = null
```

---

## 8. Formal row emission rules

### 8.1 Per-symbol formal row

当前 `build_formal_schedule_revision_row(...)` 是 single-symbol transport row。因此 multi-symbol revision article 必须拆成 per-symbol formal rows：

```text
one revision article + three symbols -> up to three formal revision rows
```

每个 symbol 独立做 linking 和 validation。

### 8.2 Linked-only formal emission

```text
if link_status == linked and validate_schedule_revision_contract(row).valid:
    append_formal_schedule_revision(...)
else:
    append schedule_revision_producer_diagnostic only
```

必须写入的 diagnostic 类型：

```text
schedule_revision_candidate_orphaned
schedule_revision_candidate_ambiguous
schedule_revision_candidate_out_of_scope
schedule_revision_candidate_missing_revised_anchor
schedule_revision_candidate_missing_symbol
schedule_revision_candidate_contract_invalid
schedule_revision_original_outside_lookback
```

### 8.3 Idempotency

Producer 应使用稳定 revision identity：

```text
revision_id = sha256(source_article_id | symbol | revision_intent | revised_anchor_ms | supersedes_source_article_id | revision_payload_hash)
stable_schedule_identity = binance|futures_contract_launch|supersedes_source_article_id|symbol
```

同一 revision row 重复出现时：

```text
same revision_id + same stable_schedule_identity -> suppress duplicate
same stable_schedule_identity + different revision_id -> emit new revision row if later available_at_ms and linked
same available_at_ms + conflicting revised_anchor_ms -> ambiguous diagnostic, no formal row
```

---

## 9. State dependencies

Stage 1.5D producer 需要可查询以下本地状态：

```text
1. current run events/*.jsonl launch rows。
2. detail_retry_scheduler_state.json candidate state。
3. optional historical index of prior Stage 1.5D launch rows under current safe lookback。
```

最小实现可以只用 current root + configured fixture/history index，不要求扫描全部 `data/` 历史 root。

如果 state 不足以唯一关联：

```text
link_status = orphaned or ambiguous
do not emit formal revision row
```

---

## 10. Multi-symbol revision semantics

multi-symbol revision article 可能出现三种情况：

```text
all_symbols_same_new_anchor:
  body says launch of A, B, C postponed to one time.
  mapping_method = exact_all_symbols_statement.

per_symbol_new_anchor:
  body/table gives A -> T1, B -> T2, C -> T3.
  mapping_method = exact_per_symbol_row.

partial_revision:
  body revises only A while original launch article had A, B, C.
  emit only A if linked; B/C unaffected.
```

失败边界：

```text
1. If symbol list cannot be parsed -> no formal rows.
2. If one symbol ambiguous -> only that symbol diagnostic; other linked symbols may emit.
3. If text says "all aforementioned contracts" but original symbol set is ambiguous -> diagnostic only.
```

---

## 11. Runtime gate and summary additions

Stage 1.5D runtime gate should expose producer capability only after implementation:

```text
schedule_revision_producer_enabled = true
schedule_revision_producer_policy = linked_only_v1
schedule_revision_linked_emit_count
schedule_revision_orphaned_diagnostic_count
schedule_revision_ambiguous_diagnostic_count
schedule_revision_out_of_scope_count
```

Until implementation:

```text
schedule_revision_producer_enabled = false
```

This must not block normal v2 launch row consumption.

---

## 12. Tests and fixtures

Required fixtures:

```text
1. Real or frozen Binance postponement fixture:
   a9f0566c85b54e30a63f1092e45d61f7 / AIAUSDT postpone notice.

2. Synthetic linked reschedule fixture:
   original launch article + revision article explicitly referencing original articleCode.

3. Synthetic orphan fixture:
   revision article has symbol but no matching original within lookback.

4. Synthetic ambiguous fixture:
   two original launch candidates with same symbol in lookback and no explicit reference.

5. Multi-symbol revision fixture:
   A/B/C with one linked, one orphaned, one ambiguous.
```

Required tests:

```text
test_postponement_notice_classified_as_schedule_revision_candidate
test_explicit_article_reference_links_supersedes_source_article_id
test_symbol_only_without_unique_original_is_ambiguous_no_formal_row
test_orphan_revision_writes_diagnostic_only
test_multi_symbol_revision_emits_only_linked_symbols
test_cancelled_revision_builds_null_revised_anchor
test_rescheduled_revision_requires_new_anchor
test_duplicate_revision_id_suppressed
test_runtime_gate_reports_revision_producer_counters
```

---

## 13. Deployment and safety

Deployment sequence:

```text
1. Implement producer classifier behind linked_only_v1 policy.
2. Run targeted Stage 1.5D producer tests and existing v2 contract tests.
3. Deploy with new root suffix only after tests pass.
4. First live run should treat revision formal rows as read-only observer metadata; no paper/live/execution changes.
```

Safety invariants:

```text
1. Producer uncertainty never creates formal revision row.
2. No symbol-only supersedes inference.
3. Revision row never creates a new Stage 1.5F event_symbol_id.
4. Existing v2 launch row path remains valid even if producer disabled.
5. All safety flags remain false.
```

---

## 14. Open questions for implementation plan

```text
Q1: Should the first implementation maintain a small current-root launch index only, or also read a curated historical index file?
Q2: Should orphaned/ambiguous diagnostics be written to diagnostics/*.jsonl only, or also summary counters?
Q3: Should a cancelled revision contaminate active observation immediately, or mark terminal cancellation only if observation has not started?
```

Recommended defaults:

```text
Q1: current root + optional explicit fixture/history index only.
Q2: both diagnostics/*.jsonl and summary/runtime gate counters.
Q3: no automatic cancellation of already active/completed observations; mark contamination/invalid lineage for 1.5G.
```
