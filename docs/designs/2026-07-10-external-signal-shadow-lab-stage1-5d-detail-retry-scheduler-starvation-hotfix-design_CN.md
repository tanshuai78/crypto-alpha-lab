# Stage 1.5D Detail Retry Scheduler Starvation Hotfix Design

**日期:** 2026-07-10  
**状态:** design_draft  
**适用分支:** External Signal Shadow Lab / Stage 1.5D Live Event Source Smoke Collector  
**问题类型:** live bug / detail fallback scheduler starvation  

---

## 0. 一句话结论

本次问题不是 Stage 1.5F 漏采，也不是 Binance 官网公告未被抓到。

真实根因是：

```text
Stage 1.5D 的 detail retry queue 没有有界公平调度、持久化 scheduler state 和 backoff。
每轮 detail fetch 预算只有 3 个，但长期被 3 个旧 HTTP 202 empty detail article 占满。
新的 no-symbol TradFi futures launch article 进入 retry state 后，1 小时内从未获得一次 detail fetch attempt。
最后被 detail_fetch_max_age 终态化为 symbols=[] / terminal_failed。
```

因此修复目标不是“补某一篇 2026-07-09 TradFi 公告”，而是修复 Stage 1.5D 的 detail fallback 调度语义，防止旧 pending detail 请求饿死新检测到的 no-symbol futures article。

---

## 0.1 Review Feedback Disposition

本轮 review 的 9 条 required fixes 全部采纳。

```text
1. 调度公平性必须有有界 first-attempt SLA，而不是只靠排序。
2. detail retry scheduler state 必须能跨进程重启恢复。
3. 1.5D scheduler 不依赖 1.5F post-watermark；1.5D 内部只使用 newly_detected_no_symbol_futures_article 语义。
4. announcement_detail_deferred manifest 必须限流或聚合，不能每轮无限写 JSONL。
5. budget_starved 是 collection failure，不得污染 symbol parse failure counters。
6. max-age failure taxonomy 拆成 never_attempted / attempted_transient / success_but_symbols_empty / validation_rejected。
7. 增加 endpoint-level degraded circuit breaker，避免 detail endpoint 全局 202 时吞光 budget。
8. 新 root 部署边界写硬，不修旧 artifacts，不把 missed event 当 formal evidence。
9. implementation plan 必须补 Stage 1.5G / review 兼容测试。
```

采纳理由：这些要求都直接影响 live evidence 的可审计性、重启后的行为一致性、下游 1.5F/1.5G 解释边界，不属于过度工程。

---

## 1. 现场证据

2026-07-09 官网出现：

```text
Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-09)
source_article_id = 84ad610bdd284699bc451b7baaa0ff7d
published_utc = 2026-07-09T10:15:09.544Z
```

Stage 1.5D 证据：

```text
raw_hits = 63
event_hits = 1
detected_utc = 2026-07-09T10:16:08.202Z
symbols = []
symbol_parse_status = terminal_failed
symbol_extraction_source = none
detail_fetch_status = max_age_exceeded
symbol_parse_failed_reason = detail_retry_max_age_exceeded
detail_fetch_attempted = False
detail_fetched_at_ms = None
symbol_resolution_latency_ms = 3636247
```

request manifest 证据：

```text
manifest_rows = 79800
article_manifest_rows for 84ad610bdd284699bc451b7baaa0ff7d = 0
```

同时最近 manifest 中每轮都有旧 detail 请求：

```text
https://www.binance.com/en/support/announcement/d2acaa91c14e4cc598aaee1017efc1ac -> HTTP 202 / empty
https://www.binance.com/en/support/announcement/ba04ce1272df4bdf8d2595ccb0e1954b -> HTTP 202 / empty
https://www.binance.com/en/support/announcement/88ea4a4f9f0b4ad4b7b308195c026fe4 -> HTTP 202 / empty
```

Stage 1.5D summary 证据：

```text
symbol_parse_failed_count = 1579
detail_symbol_parse_failed_count = 1579
symbol_empty_event_count = 1579
detail_pending_retry_count = 3
detail_terminal_failed_count = 1600
detail_transient_timeout_count = 21
```

结论：

```text
2026-07-09 article 不是 detail parser 解析失败。
它没有任何 detail request manifest row。
它在终态失败前没有被真正 fetch 过。
```

---

## 2. Stage 1.5D 的设计原理

Stage 1.5D 是 live event-source smoke collector。

它的任务是验证：

```text
Binance official announcements 是否能被稳定轮询；
futures_contract_launch 是否能被及时识别；
公告中的 symbol 是否能被稳定抽取；
无法从 title 抽 symbol 时，是否能通过 detail fallback 补充；
最终是否能产出可供 Stage 1.5F 使用的 event-symbol evidence。
```

Stage 1.5D 不做：

```text
trade signal
paper trading
live trading
execution engine
position sizing
alpha confirmed claim
execution feasibility claim
```

Stage 1.5D 与 Stage 1.5F 的关系：

```text
1.5D 负责把 external event 变成 parsed event row。
1.5F 只消费 1.5D 已经解析出 symbols 的 post-watermark event-symbol。
如果 1.5D 输出 symbols=[]，1.5F 不能采盘口，因为没有明确 symbol。
```

因此，这次 1.5F 不采集是正确行为；错误发生在 1.5D 没有给出可用 symbol。

术语边界：

```text
post-watermark:
  1.5F 的消费边界，由 1.5F watermark 判断。

newly_detected_no_symbol_futures_article:
  1.5D scheduler 内部概念，表示当前 1.5D root 中新检测到、event_type=futures_contract_launch、title 无法抽 symbol、尚未 parsed/terminal 的 article。

1.5D scheduler 不得读取或依赖 1.5F watermark 文件。
```

---

## 3. 原始 Detail Fallback 设计

Stage 1.5D 的原始事件解析路径：

```text
announcement list poll
-> parse catalog articles
-> classify futures_contract_launch
-> title symbol extraction
-> if title symbols found:
     emit parsed event
-> if title symbols missing:
     put article into detail_retry_state
-> per poll process detail_retry_state with bounded budget
-> fetch detail page
-> parse detail payload/body/table
-> extract contract symbols
-> validate through exchangeInfo when needed
-> emit parsed event or terminal_failed
```

原设计中的安全边界：

```text
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL = 3
```

含义：

```text
每轮 poll 最多抓 3 篇 announcement detail。
这样可以限制 Binance public endpoint 压力，避免 detail fallback 拖垮主公告列表轮询。
```

原设计中的 retry 语义：

```text
HTTP 202 / empty body / 429 / 5xx
=> transient detail unavailable
=> 保留 pending retry
=> 不立即 terminal_failed
```

这个设计方向是对的，但缺少一个关键约束：

```text
有限 detail budget 下，retry queue 必须公平调度。
```

---

## 4. 问题如何发生

当前 runner 的 detail retry loop 近似行为：

```text
for code, state in detail_retry_state.items():
    if expired:
        terminal_failed
        continue
    if candidate_symbols:
        validate exchangeInfo
        continue
    if detail_budget_remaining <= 0:
        budget_deferred
        continue
    detail_budget_remaining -= 1
    fetch detail
```

这个行为有三个隐含问题。

### 4.1 Queue 顺序固定

`detail_retry_state` 是进程内 dict。

旧 pending article 先进入 dict，后续每轮都会排在前面。只要前 3 个旧 article 还在 pending，它们就持续拿到全部 detail budget。

结果：

```text
new article enters detail_retry_state
but detail_budget_remaining is already 0
new article stays budget_deferred silently
next poll repeats same order
new article still cannot fetch
```

### 4.2 HTTP 202 旧请求没有 backoff

旧 article 每轮返回：

```text
http_status = 202
error = detail_payload_http_status_202
payload_size_bytes = 0
```

这种响应已经证明 Binance detail 暂时不可用。但当前设计没有让这些旧请求进入较长 backoff，因此它们每分钟继续抢占 detail budget。

### 4.3 Never-attempted event 可以过期成 terminal_failed

2026-07-09 article 的最终状态是：

```text
detail_fetch_attempted = False
detail_fetched_at_ms = None
request_manifest rows for article = 0
detail_fetch_status = max_age_exceeded
symbol_parse_status = terminal_failed
```

这违反了证据语义：

```text
没有 fetch 过 detail，就不能说 detail parse failed。
没有 fetch 过 detail，也不能把 symbols=[] 当成 article 内容证据。
```

它应该被标记为：

```text
detail_budget_starved
pending_budget_deferred
```

而不是：

```text
terminal_failed / detail_retry_max_age_exceeded
```

---

## 5. 影响范围

直接影响：

```text
post-watermark futures launch article 可能被 1.5D 误写成 symbols=[] terminal_failed。
Stage 1.5F 因缺少 symbols 无法启动 live depth observation。
```

不会直接造成：

```text
trade signal
paper trading
live trading
execution
position exposure
```

但会造成研究层面的损失：

```text
错过 live depth evidence 采集窗口；
post-watermark event 被旧 retry backlog 吞掉；
review 误以为没有新 event，而实际是 1.5D terminal_failed。
```

这是 evidence pipeline bug，不是 execution risk bug。

---

## 6. 设计目标

### 6.1 必须保证的新不变量

```text
Invariant 1:
  新进入 detail_retry_state 的 newly_detected_no_symbol_futures_article 必须在有界时间内获得首次 detail_fetch_attempt。

Invariant 2:
  HTTP 202 / empty body / 429 / 5xx 的旧 transient article 必须 backoff，不能每轮抢占全部 detail budget。

Invariant 3:
  detail_fetch_attempt_count == 0 的 article 不允许因 max_age_exceeded 写 terminal_failed。

Invariant 4:
  budget deferred 必须可审计，不能静默等待直到过期。

Invariant 5:
  terminal_failed 必须区分：
    detail_fetch_attempted_but_failed
    detail_never_attempted_budget_starved
    detail_success_but_symbols_empty
    candidate_validation_rejected

Invariant 6:
  修复不改变 Stage 1.5F watermark 语义，不允许用旧 missed event 伪造 formal 12h live evidence。

Invariant 7:
  scheduler state 必须可重启恢复，重启不能把旧 HTTP 202 article 重新当成无限抢 budget 的新 article。

Invariant 8:
  budget_starved 是 collector/scheduler collection failure，不得计入 symbol_empty 或 parser failure 统计。
```

### 6.2 First-Attempt 有界保证

只写排序建议不够。修复后必须满足可测试 SLA：

```text
If EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL > 0
and article is eligible
and detail_fetch_attempt_count == 0,
then it must receive first detail fetch attempt within:
  EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS
or
  EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS
```

建议新增配置：

```text
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS = 3
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS = 10 * 60 * 1000
```

实现上应拆成两个队列：

```text
never_attempted queue:
  round-robin / aging score
  目标是满足 first-attempt SLA。

attempted_transient queue:
  使用 backoff 和 endpoint degraded 状态控制重试频率。
```

不能继续依赖：

```text
dict insertion order
simple sort only
```

### 6.3 非目标

```text
不补采已经错过的 2026-07-09 12h formal evidence。
不把旧 terminal_failed root 改造成正式 evidence root。
不放宽 exchangeInfo validation。
不增加 private endpoint / API key / order endpoint。
不改变 1.5F age gate / watermark 规则。
```

---

## 7. 推荐解决方案

推荐方案：**bounded fair scheduler + scheduler state persistence + transient backoff + endpoint degraded circuit breaker + never-attempted protection + manifest diagnostics**。

### 7.1 Bounded Fair Scheduler

detail_retry_state 不能按 dict 插入顺序直接消费。

每轮应先构建 eligible queue：

```text
eligible_states =
  detail_retry_state rows where now_ms >= next_detail_retry_at_ms
```

调度必须先满足 first-attempt SLA，再处理旧 transient retry。

推荐排序仅作为 tie-breaker：

```text
1. detail_fetch_attempt_count == 0 优先
2. first_detected_at_ms 较早、defer_count 较高、接近 SLA breach 的 never-attempted article 优先
3. last_retry_at_ms 较早优先
4. transient_detail_error_count 较少优先
```

最低可接受版本必须保证：

```text
未尝试过 detail fetch 的 article 在 max_first_attempt_delay_polls / max_first_attempt_delay_ms 内获得一次 fetch attempt。
```

这能同时防止两类饥饿：

```text
旧 HTTP 202 article 饿死新 article。
持续新 article 进入时，较老 never-attempted article 被反向饿死。
```

### 7.2 Scheduler State Persistence

调度状态不能只存在进程内。

必须持久化或可重建以下字段：

```text
source_article_id
first_detected_at_ms
detail_fetch_attempt_count
transient_detail_error_count
non_transient_detail_error_count
last_retry_at_ms
next_detail_retry_at_ms
first_deferred_at_ms
last_deferred_at_ms
defer_count
terminal_state
terminal_failure_type
```

可选实现：

```text
方案 A:
  写 detail_retry_scheduler_state.json 或 detail_retry_state.jsonl。

方案 B:
  从 raw_payloads + request_manifest + events 重建 state。
```

最低要求：

```text
restart 后 old HTTP 202 article 仍处于 backoff。
restart 后 never-attempted article 仍受 first-attempt SLA 保护。
restart 后不会重复写 terminal_failed。
restart 后不会把旧 transient article 重新当作新事件抢占全部 budget。
```

### 7.3 Transient Backoff

当 detail fetch 返回 transient error：

```text
HTTP 202
empty_detail_payload
HTTP 429
HTTP 5xx
network timeout
```

state 应更新：

```json
{
  "transient_detail_error_count": 1,
  "last_retry_at_ms": 0,
  "next_detail_retry_at_ms": 0,
  "detail_fetch_status": "detail_payload_http_status_202"
}
```

backoff 可以先用简单确定性规则：

```text
next_detail_retry_delay_sec =
  min(3600, 60 * 2 ** min(transient_detail_error_count, 5))
```

阈值仍应来自 `configs/base.py`，不能硬编码在 `src/`。

建议新增配置：

```text
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC = 60
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC = 3600
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_NEVER_ATTEMPTED_MAX_DEFER_SEC = 10 * 60
```

### 7.4 Endpoint-Level Degraded Circuit Breaker

仅做 per-article backoff 不够。如果 Binance detail endpoint 整体进入 `HTTP 202 + empty body` 模式，多个 article 都会 transient failed。

需要维护 endpoint-level health：

```text
detail_endpoint_recent_attempt_count
detail_endpoint_recent_202_empty_count
detail_endpoint_transient_error_rate
detail_endpoint_consecutive_202_empty_count
detail_endpoint_degraded_until_ms
```

建议新增配置：

```text
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD = 0.80
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE = 5
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC = 15 * 60
```

规则：

```text
If recent detail attempts have HTTP 202 / empty rate >= threshold:
  mark detail endpoint degraded
  reduce old attempted_transient retry frequency
  preserve first-attempt SLA for never_attempted articles if budget allows
  emit endpoint_degraded diagnostic
```

注意：

```text
endpoint degraded 不应禁止新 article 的首次 attempt。
它只降低旧 transient article 的重复请求频率。
```

### 7.5 Never-Attempted Protection

现有逻辑允许：

```text
detail_fetch_attempt_count == 0
age_sec >= EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC
=> terminal_failed
```

修复后应改为：

```text
if detail_fetch_attempt_count == 0 and age_sec >= max_age:
    do not emit terminal_failed
    mark state/detail diagnostics as detail_budget_starved
    keep pending or emit non-terminal diagnostic artifact
```

如果为了防止内存状态无限增长，需要终止，也只能写：

```text
terminal_failure_type = detail_never_attempted_budget_starved
detail_fetch_status = budget_starved
symbol_parse_failed_reason = detail_never_attempted_budget_starved
```

并且 review / 1.5G 必须把它解释为：

```text
data collection failure
not parser evidence
not symbol empty evidence
```

### 7.6 Budget Deferred Manifest Compaction

当 article 因预算不足未被 fetch，应记录 scheduler diagnostic，但不能每轮每 article 写一行 JSONL。

不可接受：

```text
每 poll 对每个 pending article 写一行 announcement_detail_deferred。
```

可接受方案：

```text
方案 A:
  每个 source_article_id 只写 first_deferred row，后续 defer_count / last_deferred_at_ms 存入 scheduler_state。

方案 B:
  每 N 分钟最多写一行 compacted deferred snapshot。

方案 C:
  只在 heartbeat / summary 中输出 aggregate counters，并在 scheduler_state 保存 per-article deferred state。
```

推荐 compacted 字段：

```json
{
  "request_type": "announcement_detail_deferred",
  "source_type": "announcement_detail",
  "source_article_id": "84ad610bdd284699bc451b7baaa0ff7d",
  "url": "https://www.binance.com/en/support/announcement/84ad610bdd284699bc451b7baaa0ff7d",
  "first_deferred_at_ms": 0,
  "last_deferred_at_ms": 0,
  "defer_count": 17,
  "latest_defer_reason": "detail_budget_exhausted",
  "detail_fetch_attempt_count": 0,
  "detail_budget_per_poll": 3,
  "pending_queue_size": 0,
  "eligible_queue_size": 0,
  "parser_version": "stage1_5d_symbol_extraction_v2",
  "symbol_extraction_version": 2
}
```

这个 manifest 不代表网络请求，只代表调度决策。字段名必须明确为 `deferred`，避免和真实 fetch 混淆。

### 7.7 Request Manifest Schema Cleanup

当前 manifest 中没有 `request_type`，导致诊断脚本只能看到：

```text
request_type_counts = Counter({"unknown": 79800})
```

修复后 Stage 1.5D request manifest 至少应区分：

```text
announcement_list
announcement_detail
announcement_detail_deferred
exchange_info
first_futures_bar_klines
```

并增加：

```text
source_article_id
request_scope
audit_metadata_version
```

这样 review 能直接判断某篇 article 是否：

```text
never_attempted
deferred
attempted_transient
attempted_success
attempted_terminal
```

Stage 1.5G / review 侧必须把：

```text
announcement_detail_deferred
```

解释为 scheduler decision，不是 HTTP request failure。

### 7.8 Summary Counters

新增独立 counters：

```text
detail_budget_deferred_count
detail_budget_starved_count
detail_never_attempted_expired_count
detail_first_attempt_sla_breach_count
detail_scheduler_pending_count
detail_scheduler_backoff_count
detail_endpoint_degraded_count
detail_endpoint_degraded_active
```

明确禁止：

```text
budget_starved 不得计入 symbol_empty_event_count。
budget_starved 不得计入 detail_symbol_parse_failed_count。
budget_starved 不得计入 detail_success_symbols_empty_count。
announcement_detail_deferred 不得计入 failed HTTP request。
```

原因：

```text
budget_starved 说明 collector 调度失败；
它不是公告内容无 symbol，也不是 parser 无法抽 symbol。
```

---

## 8. 状态机语义

建议把 detail fallback article 状态显式拆成：

```text
pending_initial
pending_budget_deferred
pending_transient_backoff
pending_candidate_validation
parsed
terminal_failed_fetch_attempted
terminal_failed_parser_empty
terminal_failed_validation_rejected
terminal_failed_budget_starved
```

其中：

```text
pending_* 不写 events/*.jsonl。
parsed 才写 symbols != [] event row。
terminal_failed_* 可以写 events/*.jsonl，但必须带 terminal_failure_type。
```

特别约束：

```text
terminal_failed_budget_starved 不能被解释为公告没有 symbol。
它只能说明 collector 调度失败。
```

### 8.1 Max-Age Failure Taxonomy

`detail_retry_max_age_exceeded` 必须拆分，不得继续作为所有失败共用原因。

```text
A. detail_never_attempted_budget_starved
   没有任何 detail request。
   collection failure / scheduler failure。

B. detail_transient_timeout
   至少有一次 detail request，但长期 HTTP 202 / 429 / 5xx / timeout。
   endpoint unavailable evidence。

C. detail_success_symbols_empty
   detail fetch 成功，payload trusted，parser 确实抽不到 symbol。
   parser/content evidence。

D. candidate_validation_rejected
   detail 或 title 抽出 candidates，但 exchangeInfo 明确拒绝。
   validation evidence。
```

对应字段：

```text
terminal_failure_type =
  detail_never_attempted_budget_starved
  detail_transient_timeout
  detail_success_symbols_empty
  candidate_validation_rejected
```

只有 `detail_success_symbols_empty` 才能接近“公告内容没有可用 symbol”的证据。A/B/D 都不能被解释为 symbol-empty content evidence。

---

## 9. 与 Stage 1.5F 的关系

Stage 1.5F 不需要为本 bug 放宽规则。

Stage 1.5F 应继续只接受：

```text
symbol_parse_status = parsed
symbols != []
post-watermark event-symbol
age gate pass or delayed-launch launch-time age pass
```

Stage 1.5D 修复后，新的 1.5F root 应从新的 1.5D root bootstrap watermark。

旧 root 中已经写出的：

```text
symbols=[]
terminal_failed
detail_fetch_attempted=False
detail_fetch_status=max_age_exceeded
```

只能作为：

```text
recovery_validation_only
data_failure_evidence
```

不能作为 formal 12h live depth evidence。

### 9.1 Stage 1.5G / Review Compatibility

本 hotfix 会改变 request manifest 语义，因此 implementation plan 必须补 1.5G / review 兼容测试。

最低要求：

```text
1. budget_starved 不被解释为 symbol_empty_event。
2. announcement_detail_deferred 不被当作 HTTP request failure。
3. request_type 能区分真实 request 与 scheduler decision。
4. old unkeyed / unknown request_manifest 不能通过 formal audit。
5. terminal_failure_type = detail_never_attempted_budget_starved 的 event 只能进入 collection_failure / recovery_validation，不得进入 formal evidence。
```

---

## 10. 测试要求

后续 implementation plan 至少需要覆盖以下测试。

### 10.1 新事件不被旧 HTTP 202 backlog 饿死

场景：

```text
detail_retry_state contains old A/B/C with transient HTTP 202 history
new D enters detail_retry_state with detail_fetch_attempt_count = 0
detail_budget_per_poll = 3
```

期望：

```text
D receives one detail fetch attempt within the poll or next eligible poll
old A/B/C do not monopolize all budget
```

新增测试：

```text
test_never_attempted_article_receives_first_attempt_within_sla
test_continuous_new_articles_do_not_starve_older_never_attempted_article
```

### 10.2 never-attempted 不允许 max_age terminal_failed

场景：

```text
detail_fetch_attempt_count = 0
age_sec > EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC
```

期望：

```text
no symbols=[] terminal_failed with detail_retry_max_age_exceeded
diagnostic = detail_budget_starved or pending_budget_deferred
```

### 10.3 transient backoff 生效

场景：

```text
article A returns HTTP 202
next poll happens before next_detail_retry_at_ms
```

期望：

```text
A is skipped
detail budget can be used by other eligible articles
```

新增测试：

```text
test_old_202_backoff_survives_restart_and_new_article_gets_attempt
```

### 10.4 request_manifest 可审计

期望字段：

```text
request_type
source_article_id
audit_metadata_version
url
http_status
error
defer_reason
detail_fetch_attempt_count
```

### 10.5 scheduler state survives restart

场景：

```text
old A/B/C already returned HTTP 202 and have next_detail_retry_at_ms in future
process restarts
new D enters as never_attempted article
```

期望：

```text
old A/B/C remain in backoff
D receives first detail fetch attempt
no duplicate terminal_failed rows
```

### 10.6 newly detected TradFi regression

场景：

```text
title = Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-09)
title symbols = []
detail body later contains contract symbols
```

期望：

```text
detail fetch is attempted
detail symbols are parsed or kept pending transient
never silently expires without attempt
```

### 10.7 Stage 1.5G / review compatibility tests

必须覆盖：

```text
budget_starved 不被解释为 symbol_empty_event。
announcement_detail_deferred 不被当成 HTTP request failure。
request_type 可区分真实 HTTP request 与 scheduler decision。
old unknown request_type manifest 不得通过 formal audit。
```

---

## 11. 运行与部署原则

修复完成后不应复用旧 1.5D output root。

原因：

```text
旧 root 已经包含大量 terminal_failed / budget-starved-like evidence。
这些 artifacts 会污染新的 watermark 和 seen ids。
```

建议部署顺序：

```text
1. 保留旧 1.5D / 1.5F root 作为 bug evidence。
2. 本地测试通过后同步服务器。
3. 启动新的 1.5D root，并使用新的 scheduler metadata version，例如：
   live_event_source_continuous_YYYYMMDDTHHMMSSZ_7d_detail_retry_scheduler_hotfix
4. 用新 1.5D root bootstrap 新 1.5F root。
5. 等待新的 post-watermark futures launch event。
```

已经错过的 2026-07-09 event 只能用于：

```text
bug regression
recovery_validation
parser/retry correctness check
```

不能声明：

```text
formal 12h live depth evidence
```

硬边界：

```text
旧 root 的 terminal_failed rows 不允许人工改写成 parsed rows。
修复后重新解析出的 2026-07-09 symbols 不允许作为 formal 12h live depth evidence。
旧 root 只能用于 regression/recovery_validation。
新 1.5F root 必须从新 1.5D root bootstrap watermark。
```

---

## 12. Completion Criteria

本设计完成后的实现必须满足：

```text
1. 旧 HTTP 202 detail article 不再永久占用全部 detail budget。
2. 新 no-symbol futures article 至少获得一次 detail fetch attempt。
3. first-attempt SLA 有配置、有测试，并覆盖持续新 article 进入场景。
4. scheduler state 能跨重启恢复，旧 HTTP 202 backoff 不会因重启失效。
5. detail_fetch_attempt_count == 0 的 article 不会被写成 detail_retry_max_age_exceeded terminal_failed。
6. request_manifest 能按 source_article_id 审计 detail fetch / defer / transient / terminal 状态，且 deferred diagnostics 不无限写爆。
7. budget_starved 有独立 counters，不污染 symbol_empty / parser failure counters。
8. endpoint-level degraded circuit breaker 有配置和测试。
9. Stage 1.5F 不需要放宽任何 eligibility rule。
10. Stage 1.5G / review 能正确区分 scheduler decision 与 HTTP request。
11. 所有安全开关仍为 false。
12. 测试覆盖 old backlog + new article fairness、restart persistence、never-attempted expiry、transient backoff、endpoint degraded、manifest schema、1.5G compatibility。
```

---

## 13. 后续文档

确认本设计后，下一步应写：

```text
docs/plans/2026-07-10-external-signal-shadow-lab-stage1-5d-detail-retry-scheduler-starvation-hotfix-plan_CN.md
```

该 implementation plan 应使用 TDD 顺序：

```text
1. 先写 scheduler fairness failing tests。
2. 再写 never-attempted max-age failing tests。
3. 再写 transient backoff tests。
4. 再补 request_manifest schema tests。
5. 最后实现 runner / config / docs 修改。
```

安全边界保持：

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```
