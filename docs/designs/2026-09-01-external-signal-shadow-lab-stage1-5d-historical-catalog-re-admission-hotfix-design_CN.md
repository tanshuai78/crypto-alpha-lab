# Stage 1.5D Historical Catalog Re-admission Hotfix Design

**日期:** 2026-09-01
**状态:** design_revision_required
**Review Mode:** closure_confirmation
**适用范围:** External Signal Shadow Lab / Stage 1.5D live event source；Stage 1.5F 既有 gate consumer 兼容性
**实现计划许可:** false
**代码实施许可:** false
**部署许可:** false
**安全模式:** public-read-only；execution、paper trading、live trading、alpha interpretation 均保持禁用。

## 1. 结论

当前 1.5D root 允许曾经离开 active retry state、但未成功写成 formal event 的旧 catalog article 再次入队。历史 POPMART 和 UNITREE 文章因此被当作新 article，在从未获得 detail 请求的情况下过期，产生 `detail_never_attempted_budget_starved`。这是一个真实 collection failure；现有 runtime gate 将该 root 标记为 `DEGRADED`，1.5F 随之阻止新 observation admission，此保护行为正确。

本 Design 不修改 parser，也不补写任何历史或错过事件。它只将 article lifecycle 变为可持久化、可重启恢复、不可重新准入：

```text
first parser-trusted catalog poll
-> durably freeze catalog_bootstrap_cutoff_ms
-> mark every currently listed futures-launch article as bootstrap-preexisting terminal
-> no detail / no formal event / no 1.5F admission

later catalog poll
-> known non-consumable terminal article: skip
-> invalid publication time: persist article-local terminal, skip
-> valid publication time before cutoff: persist article-local terminal, skip
-> valid post-cutoff article: existing detail / anchor / exchangeInfo flow
```

真实 post-bootstrap candidate 若在既有 SLA/max-age 内从未收到首次 detail 请求，仍是 scheduler collection failure：其 terminal tombstone 必须持久化，且 gate 必须在重启后继续 `DEGRADED`。历史或时间无效文章则从未具备实时准入资格，只作 article-local rejection，不改变全局 gate。已完成 formal event 的 article 由现有 durable formal event/index 共同构成 catalog-admission completed identity；它不得在重复 catalog poll 或 restart 后重新获得 detail、candidate-validation ExchangeInfo、第二次 formal emission 或新的 `first_bar_queue` item。该 identity 不消费已存在的 downstream `first_bar_queue` item，也不管理其 Kline observation。

## 2. Confirmed Facts

### 2.1 Workspace source

1. `run_one_poll_cycle()` 会从每次 Binance catalog payload 分类 `futures_contract_launch` 文章，并将 `releaseDate` 传入 `source_published_at_ms`。
2. 1.5D runner 当前仅以进程内 `seen_event_ids` 与 active `detail_retry_state` 判断是否新 article。成功写入 formal event 才会进入 `seen_event_ids`。
3. 多个终态分支调用 `detail_retry_state.pop(code, None)`；`serialize_retry_articles()` 因而不会留下可用于下一次 poll 或重启拒绝该 article 的 durable lifecycle state。
4. `detail_retry_scheduler_state.json` 已经是受 StorageGuard 保护、原子写入的持久化状态；其 `articles[article_id]` schema 已有 `terminal_state`、`terminal_reason`、`terminal_at_ms`、`terminal_failure_type` 与 pre-HTTP `inflight_cycle` 字段。
5. 启动恢复代码会跳过 `terminal_state=true` 的 active retry 恢复，但当前 catalog admission 不检查已持久化 terminal article。
6. `select_detail_retry_attempts()` 已对 active candidate 保留 bounded first-attempt priority。此次问题不是将 retry fairness 改成更大预算，而是历史 article 本不应进入该候选集合。
7. runtime gate 已在 `scheduler_starved_expired_count > 0` 时返回 `stage1_5d_runtime_gate_degraded`。当前该计数来自进程内变量，重启会丢失已知 starvation 历史。
8. 1.5F 已将非 READY 的 1.5D runtime gate 解释为 `block_new_event_admission=true`；该 consumer 行为不在本次修改范围内。
9. catalog HTTP 有非空 response 不等于可信 catalog poll。既有 `run_one_poll_cycle()` 只有在 parser 未报告 `source_format_drift` 且未报告 `schema_parse_error` 时才将 `heartbeat.poll_success` 置为 `true`；该既有 parser verdict 是本次 bootstrap 唯一可用的 catalog 输入可信性边界。
10. formal launch event 先 append 到 `events/*.jsonl`，再 append `formal_launch_identity_index.jsonl`；当前 catalog admission 不读取该 durable completed identity，而仅依赖进程内 `seen_event_ids`。因此进程 restart 后同一已完成 article 可以重入。
11. 当前 scheduler loader 会对不完整 row 使用 `setdefault()`，serializer 会对多项值使用 `bool()`/`int()` coercion；这些行为不能用于 v3 resume preflight。
12. 当前 runtime static proof 已提供 clean protected worktree、完整 startup HEAD、受保护 manifest 和 `configs/base.py` 检查；v3 state 尚未将它们与 root 绑定。

### 2.2 Operator-supplied runtime evidence

下列事实来自 operator 在 VPS 上提供的现有 root 输出，Design session 未直接读取该 VPS 文件：

```text
D root:
data/external_signal_shadow/stage1_5d/
live_event_source_continuous_20260826T025236Z_
7d_detail_retry_cycle_active_root_recovery_hotfix

runtime gate reason:
scheduler_starved_expired_count_nonzero

historical terminal diagnostics:
fcdc949b45a644c78e341c88331a35ef  POPMARTUSDT  published 2026-07-23
3e662272597c44b7939f5db5c8c86d4f  UNITREEUSDT  published 2026-08-19

terminal_failure_type:
detail_never_attempted_budget_starved
```

该 evidence 证明当前 root 不可恢复为可消费 source root；Implementation Plan 必须在任何代码或 VPS 操作前重新捕获并 hash 这些 artifact。

### 2.3 Separate incident, explicitly out of scope

Article `6e9e9784397745f4a49d3f69b1cfebda` 已获得 BAPI detail response，但当前 parser 结果为 `no_symbols`，support fallback 多次为 HTTP 202 empty。它已有多次实际 detail attempt，故不是 `detail_never_attempted_budget_starved`。

该单文章 parser/source-shape coverage gap 不由历史重入造成；不得通过猜测、音译或人工映射 symbol 修复。它需要以冻结的官方原始 payload 为依据的独立 Design，且不在本次范围内。

## 3. Root Cause

现有 lifecycle 存在两个相互作用的缺口：

```text
terminal/non-consumable article
-> pop from active detail_retry_state
-> no durable terminal identity retained
-> subsequent catalog poll sees same code
-> code not in process-local seen_event_ids
-> treated as new article
-> consumes or waits for detail scheduling
-> may expire without first request
```

`seen_event_ids` 不能解决该问题，因为它只记录成功写出的 formal event，且仅存在于当前进程。历史 article 的 terminal diagnostic 既不是 active scheduler state，也不是 formal event，因此无法阻止重入。

使用 `detected_at_ms` 替代缺失的 `releaseDate` 同样不可接受：它会把“旧文章晚些出现在 rolling catalog”伪装成“刚发布的新文章”。

## 4. Scope And Non-Goals

### 4.1 In scope

1. 将现有 scheduler `articles` state 作为 active 与 non-consumable terminal article 的唯一 lifecycle store，并将既有 formal event + formal identity index 作为 formal-completed 的唯一 authority。
2. 为 fresh v3 root 建立一次性、可 read-back 的 catalog bootstrap cutoff。
3. 对 bootstrap-preexisting、历史后到和发布时间无效文章执行 article-local terminal rejection。
4. 使所有 non-consumable terminal article 在同一 root 生命周期内不可重新准入。
5. 从 durable terminal state 计算真实 starvation gate input，防止重启掩盖 collection failure。
6. 为上述行为增加最小、确定性的 synthetic regression coverage。
7. 规定旧 root 保留、新 D/F root bootstrap 的部署边界。
8. 保持 formal 后 `first_bar_queue` 的既有 in-memory owner、budget 和 Kline 行为；本 Design 不为该 downstream queue 增加 WAL、resume 或 exactly-once contract。

### 4.2 Explicit non-goals

- 修改 title/BAPI/support parser、Unicode/transliteration 规则、请求 URL、HTTP budget、retry threshold、anchor precedence 或 ExchangeInfo validation。
- 补采、补写、replay 或将已错过事件标记为实时 12h L2 evidence。
- 修改 formal event v2 schema、1.5F watermark/schema、1.5G/1.5H schema、schedule revision producer policy 或 storage limit。
- 通过重启、手动删除状态、清空计数、编辑 JSONL，或从 diagnostic 反向构造 v3 state，使当前 root 重新 READY。
- 建立独立 catalog database、queue、generic migration framework、服务或新外部依赖。
- 新增 writer lock、daemon、跨 root registry 或改变 one-root/one-process 的既有运维模型。
- 修改 execution、paper trading、live trading、execution engine 或 alpha authority。

## 5. Decisions And Rationale

### D-01: Reuse `articles` terminal state; do not create a second registry

`detail_retry_scheduler_state.json` 的 `articles` mapping 是 active 与 non-consumable terminal lifecycle 的 SSOT。formal completion 不伪装成 failure tombstone：它的 SSOT 是同 root 中已验证的 formal v2 event 与其完整 `formal_launch_identity_index.jsonl` projection。metadata version 从 `2` 升级为 `3`；scheduler state 中保留：

```text
articles[article_id]
  active retry article: terminal_state = false
  non-consumable terminal article: terminal_state = true
```

统一 admission consumed identity 为：

```text
durable_terminal_source_article_ids
UNION
durable_formal_completed_source_article_ids
```

不存在独立 `terminal_articles`、`completed_articles` 文件或 map。这样复用既有 StorageGuard、atomic writer、formal event/index、restart loader 与 audit path，避免新增 registry、双 writer 和跨文件一致性问题。

每个新增/更新 tombstone 至少包含下列已有字段：

```text
source_article_id
title
event_type = futures_contract_launch
source_published_at_ms = positive integer milliseconds | null
first_detected_at_ms
detail_http_request_count
terminal_state = true
terminal_reason
terminal_failure_type
terminal_at_ms
```

`detail_http_request_count` 必须反映实际请求数。bootstrap/historical/time-invalid rejection 均为 `0`；不得把 scheduler decision 伪装成 HTTP 请求。`source_published_at_ms` 绝不保存 invalid raw `releaseDate`；该 raw metadata 仅存在于已有 catalog/raw evidence，不复制进 lifecycle state。

### D-02: Bootstrap is a one-time parser-trusted admission boundary

仅当一次 poll 同时满足下列条件时，才是本 Design 所说的 `parser_trusted_catalog_poll`：

```text
cycle_res.heartbeat.poll_success is exactly true
  = existing parser reports source_format_drift == false
    and schema_parse_error == false

the parser-produced catalog article collection is a list
```

非空 HTTP body、HTTP 2xx、可 JSON decode，或 runner 已拿到 payload，均不足以构成 `parser_trusted_catalog_poll`。任何 parser drift/schema failure poll 都不得冻结 cutoff、terminalize catalog article、将 catalog row 加入 detail state，或将该 poll 的 event/queue result 用于后续处理；它只走既有 poll-failure 路径。

fresh v3 root 的首个 `parser_trusted_catalog_poll` 使用实际 `now_ms` 写入：

```text
catalog_bootstrap_cutoff_ms = now_ms
```

同一 trusted payload 中所有被已有 classifier 判定为 `futures_contract_launch` 的 article，均先写入：

```text
terminal_state = true
terminal_reason = catalog_bootstrap_preexisting
terminal_failure_type = null
terminal_at_ms = now_ms
detail_http_request_count = 0
```

该 scheduler checkpoint 必须 atomic write 且 read-back 成功，才可完成后续 poll 的 admission/scheduling。bootstrap poll 本身不进入后续 admission：runner 必须在 checkpoint read-back 后丢弃该 poll 的 `events` 与 `first_bar_queue` result，且不得将其赋回 persistent `first_bar_queue`。因此该 snapshot 的 article 不得 detail fetch、ExchangeInfo validation、Kline/first-bar request、formal emission 或进入 1.5F。

这比仅比较发布时间更严格：即使 source 的发布时间与首 poll 时间边界相邻，启动时已经出现的文章也不能被误称为 root 启动后实时发现。

### D-03: Later article admission uses publication time, never detection-time fallback

bootstrap 完成后的每个 classified futures-launch article，按下列不可交换 reducer 处理：

```text
0. code in durable_formal_completed_source_article_ids
   -> skip catalog/article admission only;
      preserve every existing same-source-article first_bar_queue item;
      zero new detail / candidate-validation ExchangeInfo /
      second formal emission / new first_bar_queue item

1. persisted articles[code].terminal_state == true
   -> skip catalog/article admission only;
      zero new detail / candidate-validation ExchangeInfo /
      formal emission / first_bar_queue item

2. releaseDate is not a positive integer millisecond timestamp
   or releaseDate > detected_at_ms
      + EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS
   -> persist terminal_reason = source_published_at_invalid
   -> zero detail request

3. releaseDate < catalog_bootstrap_cutoff_ms
   -> persist terminal_reason = historical_prebootstrap_catalog_article
   -> zero detail request

4. otherwise
   -> existing active detail / anchor / ExchangeInfo / formal path
```

Python `bool` is not a valid timestamp even though it is an `int` subclass. `source_published_at_ms` accepts only a positive non-boolean integer or `null`; an invalid raw value must not be copied, coerced, or rewritten to `detected_at_ms`, `available_at_ms`, or wall-clock fallback.

`EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS` is the sole authority for this comparison. Its v3 value is `30 * 1000`; it is a 1.5D catalog-clock tolerance, not a reuse of any 1.5F time contract. Equality at the bound is valid. A value greater by one millisecond is invalid. This bounded allowance prevents a small local/Binance clock difference from becoming a permanent false tombstone without permitting a materially future catalog row.

`source_published_at_invalid` and `historical_prebootstrap_catalog_article` are article-local, non-consumable terminal states. They generate one compact existing scheduler diagnostic record for audit but do not generate a formal-contract-invalid wrapper and do not change the 1.5D runtime gate.

### D-04: All non-consumable terminal states are durable tombstones

For every active-state destructive transition, the runner must first map the transition to exactly one of `durable formal-completed identity` or `durable non-consumable terminal`. The implementation must mechanically enumerate every `detail_retry_state.pop()`/equivalent removal and prove it has one of those two successors; no `at minimum` inventory is accepted.

The non-consumable terminal vocabulary is closed to:

```text
catalog_bootstrap_preexisting
historical_prebootstrap_catalog_article
source_published_at_invalid
detail_never_attempted_budget_starved
detail_unavailable_timeout
detail_retry_exhausted
candidate_validation_rejected
detail_source_url_rejected
detail_success_symbols_empty
```

For terminal rows, `terminal_reason` is exactly one member of that vocabulary; `terminal_failure_type` is `null` for the first three local-rejection reasons and equals `terminal_reason` for the remaining failure reasons. Formal-completed is not a terminal vocabulary value. The existing formal event/index schema remains authoritative; this Design only makes its source-article identity mandatory in catalog admission.

### D-05: Formal completion is a durable admission consumer

`durable_formal_completed_source_article_ids` is reconstructed read-only before any network/admission from the exact intersection of:

```text
1. valid formal v2 futures-launch event rows in events/*.jsonl; and
2. matching valid formal_launch_identity_index.jsonl rows for the same
   source_article_id, event_id, source_root_id and producer commit.
```

The event/index projection must contain one valid formal event and its complete expected per-symbol index row set for every formal-completed source article. A missing, malformed, duplicate, collisioned, mismatched, or provenance-inconsistent event/index row rejects v3 resume; V3 resume must not run the existing index-rebuild writer. For a fresh root, a formal transition is ordered as:

```text
durable inflight_cycle(formal_emission intent)
-> durable formal event
-> durable complete formal index projection
-> admission consumes the source_article_id forever in this root
```

If crash occurs before the complete index projection, the durable inflight intent remains and resume rejects rather than reconstructing/re-emitting. If both event and full index projection are durable, the source article is completed even if process termination occurred before a later scheduler cleanup write.

If the accepted crash state still has `inflight_cycle.operation="formal_emission"`, the completed projection must contain exactly the intent's `request_target.event_id` and exactly the same normalized ordered symbol set as `request_target.symbols`. Same `source_article_id` alone is insufficient. Any event-id or symbol-set difference rejects resume rather than cleaning the active row.

### D-06: Real starvation remains root-scoped collection failure

The gate input is redefined only in provenance, not in threshold:

```text
scheduler_starved_expired_count =
count(articles where
  terminal_state == true and
  terminal_failure_type == detail_never_attempted_budget_starved)
```

This count is derived from persisted v3 state on every loop and restart. It is not reset simply because a process restarts.

The distinction is intentional:

```text
historical/time-invalid article
  = never eligible for this root's real-time evidence
  = local rejection; gate unchanged

valid post-bootstrap article that never received its required first request
  = collector missed a real candidate
  = root-scoped collection failure; gate DEGRADED
```

The existing 1.5F root-level runtime gate consumer is unchanged. A future per-event health contract, if desired, requires a separate multi-module Design and is not authorized here.

## 6. Data, State And Temporal Contract

### 6.1 Scheduler state v3

```json
{
  "metadata_version": 3,
  "catalog_bootstrap_cutoff_ms": 1780000000000,
  "resume_provenance": {
    "root_id": "<canonical_root_id>",
    "scheduler_contract_version": 3,
    "producer_startup_head_sha": "<40-lowercase-hex>",
    "protected_tree_manifest_sha256": "<64-lowercase-hex>",
    "configs_base_sha256": "<64-lowercase-hex>"
  },
  "articles": {
    "article-id": {
      "source_article_id": "article-id",
      "source_published_at_ms": 1779999999000,
      "first_detected_at_ms": 1780000000000,
      "detail_http_request_count": 0,
      "terminal_state": true,
      "terminal_reason": "historical_prebootstrap_catalog_article",
      "terminal_failure_type": null,
      "terminal_at_ms": 1780000000000
    }
  },
  "endpoint_health": {}
}
```

The example is schema illustration only, not a fixture or runtime evidence. `EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION` in `configs/base.py` is the single authority for `metadata_version`, `scheduler_contract_version`, writer, loader, validator and tests; implementation changes its value from `2` to `3`. No runner/scheduler/test literal `3` is an alternate authority.

`resume_provenance` is written atomically with the first bootstrap checkpoint and is immutable for that root. Its exact values are:

```text
root_id = canonical_root_id(output_root)
scheduler_contract_version = EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION
producer_startup_head_sha = full lowercase 40-hex startup HEAD accepted by existing static proof
protected_tree_manifest_sha256 = canonical_manifest_sha256("1.5D_v3", PROTECTED_TREE_MANIFEST)
configs_base_sha256 = SHA256(raw bytes of repo_root/configs/base.py at startup)
```

`Stage1_5D_V3_ArticleLifecycleRecord` is validated before any existing loader/defaulting code may inspect a resumable root. It is a JSON object keyed by the exact lowercase 32-hex `source_article_id`; the key and `row.source_article_id` must match. Writer, validator, loader and test fixtures consume this one schema authority, not the legacy serializer's implementation-defined key set.

Every v3 article row has exactly the following required keys and no optional or unknown keys:

```text
source_article_id, title, source_detail_url_normalized, source_parent_url,
source_published_at_ms, detected_at_ms, first_detected_at_ms, event_type,
detail_work_type, catalog_id, catalog_title, symbol_extraction_source,
symbol_parse_failed_reason, pending_reason, source_published_at_ms_confidence,
detail_http_request_count, detail_retry_cycle_count, detail_fetch_attempt_count,
transient_detail_error_count, non_transient_detail_error_count, last_retry_at_ms,
next_detail_retry_at_ms, first_deferred_at_ms, last_deferred_at_ms,
last_deferred_manifest_at_ms, defer_count, terminal_state, terminal_failure_type,
candidate_symbols, symbol_derivation_method, symbol_validation_status,
symbol_launch_times_ms, symbol_onboard_times_ms,
symbol_effective_launch_times_ms, launch_time_source,
last_detail_failure_class, detail_retryable, last_bapi_detail_status,
last_bapi_payload_hash, last_bapi_parser_version, last_bapi_parser_status,
last_bapi_parser_failure_reason, last_bapi_parse_attempt_at_ms,
last_support_detail_status, last_support_failure_class, parsed_candidate_symbols,
candidate_provenance, launch_time_resolution_status, launch_anchor_policy,
required_launch_anchor_source, consumable_event_allowed,
symbol_launch_time_candidates_ms, launch_time_conflict_ms, status,
terminal_reason, terminal_at_ms, emission_id, candidate_symbol_set_hash,
candidate_symbol_set_hash_version, candidate_symbols_ordered,
candidate_symbols_normalized, event_id, event_stream_path, parser_payload_hash,
symbol_effective_launch_time_sources, exchangeinfo_visible_symbols,
exchangeinfo_missing_symbols, hard_rejected_symbols, symbol_exchangeinfo_statuses,
inflight_cycle, detail_budget_deferred_count, detail_fetch_attempted,
detail_fetch_status, detail_fetch_url_used, detail_fetch_variant,
detail_fetched_at_ms, detail_parse_status, detail_payload_hash,
detail_payload_trusted, exchangeinfo_validation_attempt_count,
exchangeinfo_validation_retryable, last_exchangeinfo_validation_at_ms,
next_exchangeinfo_validation_at_ms, quote_derivation_source, retry_count,
schedule_revision_producer_status
```

The exact field grammar is:

```text
source_article_id: exact lowercase 32-hex string matching its map key
title, source_detail_url_normalized, source_parent_url: string
event_type: exactly "futures_contract_launch"
source_published_at_ms: positive non-bool integer | null
detected_at_ms, first_detected_at_ms: positive non-bool integer
detail_http_request_count, detail_retry_cycle_count, detail_fetch_attempt_count,
transient_detail_error_count, non_transient_detail_error_count, last_retry_at_ms,
next_detail_retry_at_ms, last_deferred_manifest_at_ms, defer_count,
detail_budget_deferred_count, exchangeinfo_validation_attempt_count, retry_count:
  nonnegative non-bool integer
first_deferred_at_ms, last_deferred_at_ms, last_bapi_parse_attempt_at_ms,
terminal_at_ms, launch_time_conflict_ms, candidate_symbol_set_hash_version,
detail_fetched_at_ms, last_exchangeinfo_validation_at_ms,
next_exchangeinfo_validation_at_ms:
  nonnegative non-bool integer | null
terminal_state: exact bool
detail_retryable, consumable_event_allowed, detail_fetch_attempted,
detail_payload_trusted, exchangeinfo_validation_retryable:
  exact bool | null
candidate_symbols, parsed_candidate_symbols, candidate_symbols_ordered,
candidate_symbols_normalized, exchangeinfo_visible_symbols,
exchangeinfo_missing_symbols, hard_rejected_symbols:
  array of strings | null
symbol_launch_times_ms, symbol_onboard_times_ms, symbol_effective_launch_times_ms,
candidate_provenance, symbol_launch_time_candidates_ms,
symbol_effective_launch_time_sources, symbol_exchangeinfo_statuses:
  JSON object with string keys and JSON values | null
detail_work_type, catalog_id, catalog_title, symbol_extraction_source,
symbol_parse_failed_reason, pending_reason, source_published_at_ms_confidence,
terminal_failure_type, symbol_derivation_method, symbol_validation_status,
launch_time_source, last_detail_failure_class, last_bapi_detail_status,
last_bapi_payload_hash, last_bapi_parser_version, last_bapi_parser_status,
last_bapi_parser_failure_reason, last_support_detail_status,
last_support_failure_class, launch_time_resolution_status, launch_anchor_policy,
required_launch_anchor_source, status, terminal_reason, emission_id,
candidate_symbol_set_hash, event_id, event_stream_path, parser_payload_hash:
  string | null
detail_fetch_status, detail_fetch_url_used, detail_fetch_variant,
detail_parse_status, detail_payload_hash, quote_derivation_source,
schedule_revision_producer_status:
  string | null
inflight_cycle: null | exact intent object below
```

The required set is the exact durable V3 inventory: the previous serializer's 70 fields plus the 16 state-machine fields above, including the existing ExchangeInfo pending/retry fields. The implementation must mechanically derive and test this set from all scheduler-state writer/read sites and the earlier frozen ExchangeInfo pending contracts. `raw`, `symbols`, `payload_sha256`, `last_bapi_payload_sha256`, `symbol_launch_times_utc`, and `symbol_effective_launch_times_utc` are process-local/rederived aliases, not durable V3 article keys; they must not be serialized or required for preflight.

`inflight_cycle` is required-but-nullable: it is always serialized, never omitted. For `terminal_state=true`, `terminal_reason` and `terminal_at_ms` are non-null, `inflight_cycle` is null, and the D-04 reason/type relation must hold. For `terminal_state=false`, all three terminal fields are null and the row is active. Unknown keys, missing required keys, coercion, `setdefault`, malformed-row dropping, or best-effort repair reject the root. The implementation may load only the already validated bytes.

`inflight_cycle` is the existing field, repurposed as the v3 write-ahead side-effect intent and frozen as:

```json
{
  "operation": "detail_request | exchangeinfo_request | formal_emission",
  "cycle": 1,
  "request_ordinal": 1,
  "reserved_at_ms": 1780000000000,
  "symbol": null,
  "request_target": {},
  "request_identity": "<64-lowercase-hex>"
}
```

All seven keys are required and no additional key is allowed. `cycle`, `request_ordinal` and `reserved_at_ms` are positive non-bool integers. `symbol` is a canonical uppercase symbol string or null. `request_target` is an exact JSON object by operation:

```text
detail_request:
  symbol = null
  request_target = {
    "endpoint_kind": "bapi_article_detail_query" | "support_article_detail",
    "source_article_id": row.source_article_id,
    "detail_fetch_variant": "bapi_article_detail_query" | "primary" | "detail_path_fallback",
    "requested_url": non-empty exact active_url string passed to the HTTP client
  }

exchangeinfo_request:
  symbol = null
  request_target = {
    "endpoint": "/fapi/v1/exchangeInfo",
    "consumer_symbols": sorted non-empty unique uppercase symbol array
  }

formal_emission:
  symbol = null
  request_target = {
    "event_id": non-empty string,
    "symbols": sorted non-empty unique uppercase symbol array
  }
```

Each `request_target` has exactly the keys shown for its operation; unknown, missing, duplicate, unsorted or mismatched target values reject preflight. For `detail_request`, `bapi_article_detail_query` requires `detail_fetch_variant="bapi_article_detail_query"`; `support_article_detail` requires `detail_fetch_variant="primary"` or `"detail_path_fallback"`. `requested_url` is the exact `active_url` sent to the HTTP client before redirects; `final_url` belongs only to the post-request manifest/outcome. One BAPI or one support fallback URL is one intent and one request ordinal; a logical retry cycle never authorizes multiple URLs under one identity. `consumer_symbols` and `symbols` use bytewise ascending Python string order after canonical uppercase normalization.

An ExchangeInfo response used to transition an active scheduler candidate is one global HTTP request. Its intent is owned by the active source article that caused that candidate-validation cache miss and identifies all candidate `consumer_symbols`; later cache reads are not remote side effects and create no second scheduler intent. The runner must not combine more than one article's candidate set into one scheduler-owned ExchangeInfo intent. The post-formal `first_bar_queue` may separately use the existing root-local ExchangeInfo cache and Kline request path; it has no scheduler article row and is outside this Design's WAL contract.

Define `canonical_json_bytes(value)` exactly as UTF-8 bytes of `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Then:

```text
request_identity = SHA256(canonical_json_bytes({
  "source_article_id": row.source_article_id,
  "operation": operation,
  "cycle": cycle,
  "request_ordinal": request_ordinal,
  "symbol": symbol,
  "request_target": request_target
}))
```

The stored digest must equal this formula. An active row with an intent is resumable only under the Section 6.2/6.2.1 cross-artifact matrix; every other intent shape or identity mismatch is durability-compromised and rejects resume.

### 6.1.1 Endpoint health v3

`endpoint_health` is a required exact object, not an unchecked JSON map. Its top-level keys are exactly:

```text
recent_detail_attempt_results
detail_endpoint_degraded_until_ms
detail_endpoint_transient_error_rate
by_variant
endpoint_health_by_source
```

`recent_detail_attempt_results` is an array of at most `max(10, 2 * EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE)` values from:

```text
success
http_202_empty
http_200_empty_untrusted_payload
http_429
http_5xx
http_503
network_error
non_transient_error
```

`detail_endpoint_degraded_until_ms` is a nonnegative non-bool integer. `detail_endpoint_transient_error_rate` is a finite non-bool JSON number in `[0.0, 1.0]`. `by_variant` and `endpoint_health_by_source` are required objects and may be empty. Their allowed keys are respectively:

```text
by_variant:
  bapi_article_detail_query | support_article_detail | primary | detail_path_fallback

endpoint_health_by_source:
  bapi_article_detail_query | support_article_detail
```

Every present nested value has exactly the same three scalar/list keys and grammar as the top-level health sample fields. The writer initializes all five top-level keys in the first v3 bootstrap checkpoint. No defaulting, alias creation, coercion, malformed-entry dropping or unknown source/variant key is permitted during v3 resume preflight.

### 6.1.2 V3 cross-field semantic invariants

Every row and `endpoint_health` object that passes the Sections 6.1 and 6.1.1 key/type grammar must also pass all of these relations before loader/defaulting, mutation, diagnostic append or network:

1. **Candidate-set identity.** The four fields `candidate_symbols_ordered`, `candidate_symbols_normalized`, `candidate_symbol_set_hash_version` and `candidate_symbol_set_hash` are either all `null`, or all non-null. When non-null, `candidate_symbols_ordered` is a non-empty unique array whose every string equals `string.strip().upper()`; `candidate_symbols_normalized` is exactly `sorted(candidate_symbols_ordered)` in bytewise Python string order; `candidate_symbol_set_hash_version == 1`; and `candidate_symbol_set_hash` equals the exact existing `build_candidate_symbol_set_identity()` formula:

   ```text
   SHA256(UTF-8(json.dumps(
     candidate_symbols_normalized,
     ensure_ascii=True,
     separators=(",", ":")
   )))
   ```

   `candidate_symbols_ordered` preserves the source order; only the normalized array is the set identity and idempotency input.
2. **Detail request counters.** `detail_fetch_attempt_count == detail_http_request_count`. Both count actual detail HTTP requests. `detail_retry_cycle_count` is a distinct logical scheduling-cycle counter and is not required to equal either HTTP counter.
3. **Endpoint-health source mirror.** For each source in `bapi_article_detail_query` and `support_article_detail`, when that source key is present in both `endpoint_health_by_source` and `by_variant`, the two nested JSON records are exactly equal. The `primary` and `detail_path_fallback` variant keys have no corresponding source-mirror equality requirement.

Any violation is `stage1_5d_v3_resume_preflight_rejected`; it is never normalized, repaired, defaulted or admitted.

### 6.2 Fresh versus resumable root

```text
fresh v3 root
  = output_root does not exist at preflight
  -> create it once with mkdir(exist_ok=false)
  -> await first parser_trusted_catalog_poll

resumable v3 root
  = passes the exact read-only artifact preflight below
  -> restore active nonterminal articles; retain terminal tombstones

legacy/invalid root
  = every other existing output_root
  -> not eligible for v3 resume
  -> preserve; fail closed with no root mutation
```

The v3 root preflight runs immediately after CLI argument validation and before `StorageGuard` construction/cleanup, any `output_root.mkdir`, scheduler/payload/index load, formal-identity rebuild, stream-path creation, diagnostic append, runtime-gate/summary write, or network request. It performs the existing static runtime proof read-only, then validates root structure, v3 state semantics, D-05 formal-completed projection and `resume_provenance` against the current verified runtime. Rejection exits nonzero as `stage1_5d_v3_resume_preflight_rejected` and writes no artifact into the rejected root.

`output_summary_path` must resolve exactly to `output_root / binance_futures_launch_smoke_summary.json`. A resumable root is accepted only when all of the following are true:

```text
1. output_root is a real directory, not a symlink.
2. detail_retry_scheduler_state.json is a regular non-symlink file whose JSON has:
   metadata_version == 3 (integer, not bool),
   catalog_bootstrap_cutoff_ms as a positive integer (not bool),
   resume_provenance passing its exact Section 6.1 equality checks,
   articles as a semantically valid object under Stage1_5D_V3_ArticleLifecycleRecord,
   and endpoint_health passing the exact Section 6.1.1 schema.
3. Every direct child has exactly one of these names and the stated type:
   events/, raw_payloads/, heartbeats/, request_manifest/,
   detail_retry_scheduler_diagnostics/, detail_retry_terminal_diagnostics/,
   bapi_parse_results/ (directories),
   detail_retry_scheduler_state.json, formal_launch_identity_index.jsonl,
   revision_payload_versions.jsonl, live_safety_gate_summary.json,
   binance_futures_launch_smoke_summary.json (regular files).
4. Each stream directory contains only regular YYYY-MM-DD.jsonl files;
   raw_payloads/ may additionally contain only regular files at
   announcement_detail/<article-id>/<variant>.<sha256>.bin.
5. No inspected path is a symlink, device, FIFO, socket, or an unlisted file/directory.
```

An absent optional stream/file from the list is allowed, except a root containing any formal event requires its complete matching formal index projection. The read-only preflight then applies the Section 6.2.1 lifecycle-authority matrix to every `source_article_id`, before any admission reducer can apply its normal skip order. Any unlisted artifact, malformed path, v2 state, missing state, invalid cutoff, malformed row, unresolved or mismatched inflight intent, lifecycle-authority conflict, formal event/index mismatch, root-id/commit/manifest/config provenance mismatch, or invalid static proof rejects the root. No v2-to-v3 migration exists. In particular, terminal diagnostics in the current degraded root are evidence of an old lifecycle, not sufficient information to reconstruct a contemporaneous bootstrap boundary.

### 6.2.1 Lifecycle-authority exclusivity preflight

For each `source_article_id`, preflight derives only these three durable authorities:

```text
active row       = an articles[id] row with terminal_state == false
terminal row     = an articles[id] row with terminal_state == true
formal-completed = one complete valid D-05 event/index projection
```

The following matrix is exhaustive:

| Scheduler row | Formal projection | Result |
|---|---|---|
| terminal row | complete | invalid; reject resume |
| active row, `inflight_cycle=null` | complete | invalid; reject resume |
| active row, `detail_request` or `exchangeinfo_request` intent | complete | invalid; reject resume |
| active row, `formal_emission` intent whose event id and ordered symbols exactly equal the complete projection | complete | valid crash-after-completion state; consume formal identity and perform only cleanup |
| active row, `formal_emission` intent whose event id or ordered symbols differ from the projection | complete | invalid; reject resume |
| no scheduler row | complete | valid completed state; consume and skip |
| any scheduler row or no scheduler row | absent, malformed, duplicate, collisioned, or incomplete event/index projection | invalid when any formal event/index row for the article exists; reject resume |
| terminal row | no formal row | valid terminal state |
| active row, `inflight_cycle=null` | no formal row | valid resumable active state |
| active row, non-null intent | no formal row | unresolved intent; reject resume |
| no scheduler row | no formal row | valid only when no lifecycle artifact for that article exists |

The exact-identity `formal_emission` exception is the only state in which an active scheduler row and a complete formal projection may coexist. It represents a crash after event/index durability but before active-row cleanup. After preflight accepts that exact exception, recovery may perform only a guarded, read-back scheduler checkpoint that removes the active row; it performs no network request, formal write, diagnostic append or catalog admission. It never deletes, mutates or consumes an existing `first_bar_queue` item. If that cleanup checkpoint fails, the process stops and leaves the same exception for a later retry. No reducer priority may normalize, mask, delete, or silently prefer either half of an invalid combination.

### 6.3 Time semantics

```text
catalog_bootstrap_cutoff_ms
  = local observation time of first parser_trusted_catalog_poll for this fresh root.

source_published_at_ms
  = normalized valid Binance catalog releaseDate only:
    positive non-boolean integer milliseconds; otherwise null.

catalog releaseDate future bound
  = EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS
  = 30 * 1000 milliseconds in configs/base.py.
    releaseDate <= detected_at_ms + bound is eligible for normal admission;
    releaseDate > detected_at_ms + bound is source_published_at_invalid.

first_detected_at_ms
  = local first poll observation time; never a publication-time substitute.
```

This Design does not change `detected_at_ms`, `available_at_ms`, launch-anchor time, formal event time semantics, or 1.5F observation clock semantics for valid post-bootstrap articles.

## 7. Producer, Consumer And Artifact Impact Matrix

| Component | Change | Compatibility rule |
|---|---|---|
| 1.5D catalog admission writer | Adds v3 bootstrap/tombstone reducer | Only valid post-bootstrap articles enter existing detail path |
| 1.5D scheduler state writer/loader | Persists cutoff, lifecycle rows, `inflight_cycle` intents and resume provenance | v2 is not migrated or resumed as v3; v3 validates before loader coercion |
| 1.5D formal event/index | Supplies formal-completed source-article identity | Event/index must be a complete matching projection before v3 resume |
| 1.5D runtime gate producer | Derives starvation count from durable tombstones | Existing degraded decision and threshold unchanged |
| 1.5D diagnostics | Adds compact scheduler diagnostics for local rejections | No formal event or formal-contract-invalid record for local rejections |
| 1.5F loader/runtime-gate consumer | No source change | Existing non-READY rejection remains authoritative |
| 1.5G / 1.5H | No source, schema, or review-rule change | They receive no artifact from rejected articles |
| Parser and external detail sources | No change | 牛来USDT incident remains separately quarantined |

| Lifecycle state | Scheduler v3 authority | Formal event/index | D gate / F admission | Restart result |
|---|---|---|---|---|
| fresh/pre-bootstrap | cutoff absent | none | not READY; not F-eligible | await trusted poll |
| bootstrap/historical/publication-invalid | durable terminal | none | local only; not F-eligible | skip |
| active post-bootstrap | validated active row | none | normal existing D gate; not yet F-eligible | resume only without unresolved intent |
| real budget-starved/other failure terminal | durable terminal | none | starvation remains DEGRADED; not F-eligible | skip |
| formal-completed | no active candidate | complete matching formal event/index | existing valid D gate only; existing F path | consumed/skip |
| unresolved side-effect intent | durable `inflight_cycle` | incomplete or absent projection | not F-eligible | reject root before mutation/network |
| malformed/provenance-mismatched/legacy root | rejected | not trusted | not F-eligible | zero-side-effect rejection |

## 8. Failure Semantics, Persistence And Restart

### 8.1 Bootstrap failure reducer

```text
catalog request fails or parser_trusted_catalog_poll == false
-> no cutoff
-> no article admission
-> discard this poll's event/first-bar queue result
-> existing poll failure handling

parser_trusted_catalog_poll
-> build bootstrap tombstones
-> guarded state write + read-back fails
-> no detail/exchangeInfo/formal side effect for bootstrap candidates
-> existing storage fail-closed behavior

parser_trusted_catalog_poll
-> bootstrap state write + read-back succeeds
-> discard this poll's event/first-bar queue result
-> begin normal admission only from a later parser_trusted_catalog_poll
```

### 8.2 Terminalization reducer

```text
article becomes non-consumable terminal
-> write/update terminal tombstone through existing guarded state writer
-> read-back success
-> remove only from in-memory active selection
-> later poll/restart sees durable terminal identity and skips it
```

If a terminalization follows a remote/formal side effect, its prior durable intent remains on any final checkpoint failure and Section 8.3 rejects restart before re-admission. If terminalization is purely local and its checkpoint fails, the process must stop with no downstream side effect; it must not claim a terminal state, and a later process may re-evaluate the unchanged raw catalog row only under the Section 8.3 local-failure rule. Existing StorageGuard failure behavior remains the authority.

### 8.3 Mandatory lifecycle durability and crash recovery

Every scheduler-owned transition that can cause a remote detail request, candidate-validation ExchangeInfo request, or formal event/index write must first persist and read back the exact `inflight_cycle` intent while the row remains active. Only after this write-ahead checkpoint may that side effect occur. Completion is then one of:

```text
detail_request intent
-> durable request/raw-result and updated active row or D-04 terminal row
-> durable checkpoint with inflight_cycle=null

exchangeinfo_request intent
-> durable request manifest and article validation-outcome checkpoint
-> durable checkpoint with inflight_cycle=null

formal_emission intent
-> durable formal event
-> durable complete D-05 index projection
-> durable removal of the active scheduler row
-> formal-completed identity consumes the source article
```

For detail and candidate-validation ExchangeInfo, `request_target` and `request_identity` bind one possible remote request. The associated outcome must be durable before clearing that intent. Each BAPI or support fallback URL receives its own detail intent before its HTTP request. If any post-intent lifecycle/finalization write fails, the durable intent is deliberately not cleared. A subsequent resume rejects it before network or mutation, except `formal_emission` with an exactly matching complete D-05 event/index projection, which is already safely completed and is skipped without further side effects.

`first_bar_queue` begins only after formal emission and scheduler-row removal. Its optional ExchangeInfo cache miss and Kline request are existing downstream work, not article-scheduler transitions. A formal-completed catalog identity cannot remove, suppress or recreate this queue work. This Design makes no queue persistence, cross-restart completion, request identity or exactly-once claim for Kline. The old startup behavior that clears scheduler `inflight_cycle`, emits a diagnostic and continues is not authorized for v3.

Purely local bootstrap/historical/publication-invalid terminalization has no prior external or formal side effect. If its atomic checkpoint cannot be written/read back, the current process stops before creating any downstream side effect; a later process may re-evaluate the same raw catalog row because no lifecycle decision ever became durable. It may not coerce, infer, or claim that failed decision as durable.

### 8.4 Restart

```text
restart with valid v3 state
-> only validated active rows without unresolved side-effect intent resume under existing scheduler rules
-> terminal entries are not active candidates
-> formal-completed identities are not active candidates
-> accepted formal_emission crash-after-completion rows receive only the
   Section 6.2.1 no-network cleanup checkpoint before normal admission
-> existing in-memory first_bar_queue follows its unchanged process-lifetime behavior;
   it is neither reconstructed nor deleted by catalog admission
-> catalog admission checks persisted terminal entries before time/detail logic
-> durable real-starvation count keeps gate DEGRADED
```

The state must not evict tombstones during the root lifecycle. StorageGuard/root quota remains the outer fail-closed bound; no silent TTL or compaction is authorized.

### 8.5 Legacy or malformed root preflight

```text
output_root already exists
-> execute the Section 6.2 read-only preflight before every writer/helper

preflight rejects
-> exit stage1_5d_v3_resume_preflight_rejected
-> no mkdir, no StorageGuard cleanup, no scheduler/index/payload rebuild,
   no diagnostic, summary or runtime-gate write, and no network request

preflight accepts
-> only then construct StorageGuard and execute normal v3 resume startup
```

## 9. Acceptance Invariants

**INV-01 -- Trusted bootstrap isolation.** Only a `parser_trusted_catalog_poll` can freeze the bootstrap cutoff. Its classified futures-launch articles receive zero detail/ExchangeInfo/Kline/formal side effects, its event and first-bar queue result is discarded, and it cannot reach 1.5F.

**INV-02 -- Historical re-admission prevention.** A valid later catalog row with `releaseDate < catalog_bootstrap_cutoff_ms` becomes one durable article-local tombstone and has zero detail requests across repeated polls and restart.

**INV-03 -- No inferred publication time.** Missing, boolean, non-integer, non-positive, or `releaseDate > detected_at_ms + EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS` never fall back to detected/current time; they become durable local rejections with zero detail requests. Equality at the configured clock-skew bound is valid.

**INV-04 -- Local rejection does not poison root health.** Bootstrap, historical, and invalid-publication-time rejections do not increment `scheduler_starved_expired_count` or degrade the runtime gate by themselves.

**INV-05 -- Actual scheduler failure remains visible.** A valid post-bootstrap candidate which reaches `detail_never_attempted_budget_starved` creates a durable tombstone and keeps the gate `DEGRADED` after restart.

**INV-06 -- Terminal identity is non-reentrant.** No non-consumable terminal article is reselected, refetched, re-emitted, or reclassified as new in the same root lifecycle.

**INV-07 -- Fresh-root-only rollout.** The current v2 degraded D/F roots are not migrated, modified, replayed, or restored. An existing root is resumable only under the exact v3 preflight set in Section 6.2; every other existing root is rejected before side effects. v3 evidence starts from a distinct new D root and a distinct F bootstrap.

**INV-08 -- Existing valid path unchanged.** A valid post-bootstrap article still uses the exact existing detail, anchor, candidate-validation ExchangeInfo, formal v2, first-bar queue/Kline and 1.5F admission contracts. V3 only adds scheduler durability boundaries; it does not change downstream queue ownership.

**INV-09 -- Authority unchanged.** All execution, alpha, paper and live-trading permissions remain false. This Design creates no event replay, cost, alpha, execution or trading claim.

**INV-10 -- Formal-completion non-reentry.** A source article with a complete valid D-05 formal event/index projection is a consumed catalog-admission identity across repeated polls and restart; it receives no second detail, candidate-validation ExchangeInfo, formal event or new first-bar queue item. It does not delete or suppress an already queued downstream first-bar/Kline observation.

**INV-11 -- V3 lifecycle semantic integrity.** Every `articles[key]` row must pass the exact Sections 6.1 and 6.1.2 validator before any loader/defaulting logic. A malformed or cross-field-inconsistent row is never dropped, repaired, coerced or admitted.

**INV-12 -- Scheduler side-effect durability barrier.** No scheduler-owned detail, candidate-validation ExchangeInfo or formal side effect starts without its durable, read-back, exact-identity `inflight_cycle` intent. A post-intent incomplete transition is non-resumable, except a complete D-05 formal completion with exact event/symbol binding, which is already consumed and is skipped. A pre-side-effect local write failure creates no durable state or downstream side effect.

**INV-13 -- Resume provenance identity.** A resumable root must match its immutable v3 root id, scheduler contract version, producer HEAD, protected-tree manifest fingerprint and `configs/base.py` fingerprint under the current successful static proof before mutation or network.

**INV-14 -- Publication-time type stability.** `source_published_at_ms` is only a positive non-boolean integer or null. Invalid raw `releaseDate` values are never stored in that field or transformed into inferred time.

**INV-15 -- Serialized writer assumption.** The trusted deployment boundary is one semantic 1.5D writer per `output_root`; operator deployment/cutover is serialized. This Design does not add a lock subsystem.

**INV-16 -- Lifecycle authority exclusivity.** For one `source_article_id`, durable terminal and complete formal-completed authority are mutually exclusive. A complete formal projection may coexist only with its active `formal_emission` intent during crash cleanup; every other active/formal or incomplete-formal combination rejects in preflight before mutation or network.

**INV-17 -- Endpoint-health semantic integrity.** `endpoint_health` and every nested source/variant record pass the exact Section 6.1.1 grammar and Section 6.1.2 source-mirror relation before any scheduler selection, health calculation or defaulting logic. An invalid health state rejects v3 resume before mutation or network.

## 10. Evidence And Verification Strategy

All new tests are deterministic synthetic fixtures. No live `data/` tree, VPS state file, raw payload, secret, or generated observation artifact is committed.

Required RED-to-GREEN coverage:

1. A parser-trusted first snapshot contains historical-like POPMART/UNITREE rows: both become bootstrap tombstones; no detail, ExchangeInfo, Kline, formal event, persistent first-bar queue item, or 1.5F-eligible row exists; gate is otherwise READY.
2. Parser drift/schema-error polls, including nonempty HTTP payloads, leave cutoff absent and produce no bootstrap tombstone, detail state entry, or first-bar queue item.
3. A historical article appears only after bootstrap: it becomes `historical_prebootstrap_catalog_article`; repeated polls and simulated restart make zero detail or candidate-validation ExchangeInfo requests, including when the existing classifier supplies title-derived symbols; it creates no first-bar queue item.
4. Invalid `releaseDate` cases include absent, boolean, string, zero/negative and a value greater than `detected_at_ms + EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS`: each gets one `source_published_at_invalid` tombstone with `source_published_at_ms=null`. The exact boundary `releaseDate == detected_at_ms + skew_limit` is valid; `+ skew_limit + 1` is invalid. A separate valid post-bootstrap article is still selected within the existing first-attempt SLA.
5. A formal success followed by process restart and the same catalog article produces zero new detail, candidate-validation ExchangeInfo, formal event, first-bar queue item or F admission. A pre-existing first-bar queue item remains eligible for its normal in-process Kline check despite a later catalog duplicate. Crash after formal event but before index rejects; crash after complete index skips only catalog admission as formal-completed.
6. A valid post-bootstrap article retains current BAPI/detail, candidate-validation ExchangeInfo and formal v2 behavior. Each actual BAPI/support URL, candidate-validation ExchangeInfo request and formal emission has a durable read-back exact-identity `inflight_cycle` intent before its side effect; the three corresponding outcome checkpoints clear it only after their required durable artifacts exist. Detail fallback fixtures prove distinct requested URLs produce distinct identities. Crash fixtures cover every scheduler-owned operation before side effect, after side effect/before outcome checkpoint, and after outcome checkpoint. Only formal-emission after an exactly matching complete event/index projection is consumed; every other unresolved intent rejects with zero request/mutation. First-bar queue/Kline behavior is tested unchanged and separately from scheduler WAL.
7. A valid post-bootstrap article whose detail budget is genuinely unavailable until max age reaches terminal `detail_never_attempted_budget_starved`; the terminal state survives restart and the reconstructed gate remains `DEGRADED`.
8. Every active-state destructive transition is mechanically enumerated and maps exactly to formal-completed or one D-04 terminal reason; no raw `pop()` path is unclassified.
9. A mechanical writer/read inventory proves the exact V3 article key set covers the prior 70 serializer keys, the 16 enumerated state-machine keys and the frozen ExchangeInfo pending/retry fields, while excluding only the explicitly named process-local aliases. Malformed v3 rows cover map-key/source-id mismatch, every required-key omission, unknown key, wrong typed field family, string boolean, invalid integer, illegal terminal reason/type relation, absent `inflight_cycle`, invalid intent operation/target/identity and request-identity digest mismatch. Candidate-set corruption fixtures independently cover normalized-array mismatch, hash mismatch and version mismatch; a detail HTTP-counter alias mismatch rejects while a distinct retry-cycle count is accepted. Malformed endpoint health covers every missing/unknown top-level or nested key, invalid result enum, oversized sample array, invalid timestamp/rate, invalid source/variant key and a source-mirror mismatch. Each rejects before loader coercion, mutation or network, with an identical recursive pre/post artifact fingerprint.
10. Each existing v2/missing-cutoff/unlisted-artifact/provenance-mismatched root fails v3 resume preflight before `StorageGuard` construction, directory creation, state/index/payload load or rebuild, diagnostic/summary/gate write, and network request; a recursive pre/post artifact fingerprint is identical.
11. The Section 6.2.1 matrix is tested exactly: terminal plus complete formal, active-null plus complete formal, and active detail/ExchangeInfo intent plus complete formal each reject; active formal-emission intent plus a complete projection with exact event-id and symbol-set equality receives only its no-network cleanup checkpoint and then consumes; an event-id/symbol mismatch rejects; cleanup failure performs no second side effect; no scheduler row plus complete formal consumes; every incomplete event/index projection rejects. A local terminal write failure has no downstream side effect and can be re-evaluated on a later process.
12. A valid resumable v3 root containing only the Section 6.2 allowlisted artifact set, full provenance match, validated rows, validated endpoint health and matching formal projection restores active nonterminal state, retains terminal tombstones and consumes formal-completed identities without touching an existing first-bar queue item.
13. A closed-tree test proves the Section 6.2 allowlist equals all normal v3 persistent writer outputs, including the exact current `build_detail_payload_path()` grammar `raw_payloads/announcement_detail/<safe-article-id>/<variant>.<64-lowercase-hex>.bin` and the existing daily `raw_payloads/YYYY-MM-DD.jsonl` stream. Any newly discovered legitimate write surface stops implementation and returns to Design rather than extending the list ad hoc; no raw-payload naming migration is authorized.
14. A fresh D v3 root and fresh F bootstrap verify existing root binding/attestation, and prove no pre-bootstrap, terminal, incomplete, or formal-completed article starts an F observation.
15. Existing scheduler fairness, formal v2, F gate rejection, 1.5G integrity and storage-guard suites remain green.

Mechanical verification must include focused pytest suites, full relevant regression suite, `ruff check` for changed paths, `git diff --check`, and an explicit assertion that `RISK_LIVE_TRADING_ENABLED` remains `False`.

## 11. Rollout And Rollback

### 11.1 Preconditions

1. Preserve the current D/F roots and their diagnostics without restart, deletion, state editing, compaction or replay.
2. Implement only after this Design, Implementation Plan and implementation review are approved.
3. Deploy from a verified commit/worktree that does not alter the currently running worktree in place.
4. Confirm no active 1.5F observation depends on the old root before cutover.
5. Require the chosen new D v3 `output_root` to be absent at startup; do not reuse an empty, partial, legacy, or previously failed root.

### 11.2 Cutover

```text
verified patched code
-> start a new unique 1.5D v3 output root
-> wait for first parser-trusted catalog bootstrap and D READY preflight
-> start a new 1.5F root bootstrapped from that exact D root
-> verify D/F root IDs, static/runtime attestation and block_new_event_admission=false
-> wait only for a post-bootstrap valid new event
```

The 2026-08-30 牛来USDT event and every event that precedes the new bootstrap are not eligible for live observation under the new root.

### 11.3 Stop and rollback

If bootstrap state, storage guard, D gate, D/F root binding, or runtime attestation fails, stop the new pair and preserve its artifacts for diagnosis. Do not roll back by restarting the old degraded root or clearing its starvation evidence. A later clean retry requires another fresh D/F root.

## 12. Safety And Authority Boundary

```text
live_public_readonly = true
execution_feasibility_claim_allowed = false
alpha_interpretation_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

The only allowed claim after implementation is operational: a new root mechanically rejects pre-bootstrap/historical/unverifiable catalog articles and preserves real scheduler starvation failure across restart. It is not a claim of complete Binance coverage, tradability, alpha, execution feasibility, or profit.

## 13. Trust Boundary

This Design protects durable article lifecycle identity, v3 resume integrity and D-to-F admission only. It explicitly trusts the existing OS/filesystem atomic-replace/fsync semantics, StorageGuard behavior, Python/Git integrity, existing parser/ExchangeInfo/formal/F contracts, a local/Binance catalog clock difference no greater than `EXTERNAL_SIGNAL_STAGE1_5D_CATALOG_RELEASEDATE_MAX_CLOCK_SKEW_MS`, and serialized deployment with one semantic 1.5D writer per `output_root`.

It does not protect a compromised kernel/filesystem, malicious privileged operator, compromised Git/Python binary, third-party supply-chain compromise, Binance semantic falsification, the separate `6e9e...` parser/source-shape incident, new parser/transliteration logic, 1.5G/1.5H redesign, or any execution/trading system.

## 14. Open Questions

None that alter the implementation path.

The separate `6e9e9784397745f4a49d3f69b1cfebda` parser/source-shape incident remains intentionally deferred. It does not block this Design because this Design neither changes symbol extraction nor attempts to observe that already missed event.
