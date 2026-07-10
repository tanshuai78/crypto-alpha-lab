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
Stage 1.5D 的 detail retry queue 没有公平调度和 backoff。
每轮 detail fetch 预算只有 3 个，但长期被 3 个旧 HTTP 202 empty detail article 占满。
新的 post-watermark TradFi futures launch article 进入 retry state 后，1 小时内从未获得一次 detail fetch attempt。
最后被 detail_fetch_max_age 终态化为 symbols=[] / terminal_failed。
```

因此修复目标不是“补某一篇 2026-07-09 TradFi 公告”，而是修复 Stage 1.5D 的 detail fallback 调度语义，防止旧 pending detail 请求饿死新事件。

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
  新进入 detail_retry_state 的 post-watermark futures launch article 必须尽快获得至少一次 detail_fetch_attempt。

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
```

### 6.2 非目标

```text
不补采已经错过的 2026-07-09 12h formal evidence。
不把旧 terminal_failed root 改造成正式 evidence root。
不放宽 exchangeInfo validation。
不增加 private endpoint / API key / order endpoint。
不改变 1.5F age gate / watermark 规则。
```

---

## 7. 推荐解决方案

推荐方案：**fair scheduler + transient backoff + never-attempted protection + manifest diagnostics**。

### 7.1 Fair Scheduler

detail_retry_state 不能按 dict 插入顺序直接消费。

每轮应先构建 eligible queue：

```text
eligible_states =
  detail_retry_state rows where now_ms >= next_detail_retry_at_ms
```

排序建议：

```text
1. detail_fetch_attempt_count == 0 优先
2. first_detected_at_ms 较新且 post-watermark article 优先
3. last_retry_at_ms 较早优先
4. transient_detail_error_count 较少优先
```

最低可接受版本：

```text
未尝试过 detail fetch 的 article 优先于已经多次 HTTP 202 的 article。
```

这样可保证新事件至少获得一次 detail fetch attempt。

### 7.2 Transient Backoff

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

### 7.3 Never-Attempted Protection

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

### 7.4 Budget Deferred Manifest

当 article 因预算不足未被 fetch，应写 request_manifest 诊断行：

```json
{
  "request_type": "announcement_detail_deferred",
  "source_type": "announcement_detail",
  "source_article_id": "84ad610bdd284699bc451b7baaa0ff7d",
  "url": "https://www.binance.com/en/support/announcement/84ad610bdd284699bc451b7baaa0ff7d",
  "fetched_at_ms": null,
  "deferred_at_ms": 0,
  "defer_reason": "detail_budget_exhausted",
  "detail_fetch_attempt_count": 0,
  "detail_budget_per_poll": 3,
  "pending_queue_size": 0,
  "eligible_queue_size": 0,
  "parser_version": "stage1_5d_symbol_extraction_v2",
  "symbol_extraction_version": 2
}
```

这个 manifest 不代表网络请求，只代表调度决策。字段名必须明确为 `deferred`，避免和真实 fetch 混淆。

### 7.5 Request Manifest Schema Cleanup

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

### 10.5 post-watermark TradFi regression

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
3. 启动新的 1.5D root，例如：
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

---

## 12. Completion Criteria

本设计完成后的实现必须满足：

```text
1. 旧 HTTP 202 detail article 不再永久占用全部 detail budget。
2. 新 post-watermark no-symbol futures article 至少获得一次 detail fetch attempt。
3. detail_fetch_attempt_count == 0 的 article 不会被写成 detail_retry_max_age_exceeded terminal_failed。
4. request_manifest 能按 source_article_id 审计 detail fetch / defer / transient / terminal 状态。
5. Stage 1.5F 不需要放宽任何 eligibility rule。
6. 所有安全开关仍为 false。
7. 测试覆盖 old backlog + new article fairness、never-attempted expiry、transient backoff、manifest schema。
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
