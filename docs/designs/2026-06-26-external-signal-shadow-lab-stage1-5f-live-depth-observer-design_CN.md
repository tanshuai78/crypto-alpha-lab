# External Signal Shadow Lab Stage 1.5F Live Depth Observer Design

**Date:** 2026-06-26  
**Status:** design_draft  
**Owner:** External Signal Shadow Lab  
**Depends on:** Stage 1.5D / Stage 1.5E  

---

## 0. 设计结论

Stage 1.5F 的目标不是把 Stage 1.5C 的 close-price replay 推向交易，而是补齐一个关键证据缺口：

```text
当 Binance futures_contract_launch 真实新事件发生时，
我们能否从事件检测后开始，连续采集 12h 的 public orderbook/depth 证据，
用于判断 close-price replay 是否可能只是盘口幻觉？
```

当前 Stage 1.5E 的正式结论仍是：

```text
decision = stage1_5e_execution_feasibility_proxy_failed
execution_feasibility_proven = false
historical_orderbook_depth_available = false
live_depth_snapshot_available = false / manual-only
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

因此 Stage 1.5F 只能是：

```text
scope = live_depth_observation_only
purpose = collect execution-feasibility evidence for future review
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

---

## 1. 背景

Stage 1.5D 已经验证了 Binance announcement collector 的基础链路，并能解析 `futures_contract_launch` 事件。

Stage 1.5E 发现：

```text
1. futures launch 12h close-price replay 在部分 cell 上出现过 promising 结构；
2. 但历史 Kline 代理显示 entry 附近波动很大；
3. 本地历史 orderbook archive 与这批小币没有 symbol overlap；
4. 因此无法证明当时真实 bid/ask spread、depth、slippage 是否可接受。
```

近期服务器手工实验已经证明：

```text
1. 可以从 Stage 1.5D event JSONL 扁平化出 symbol-level live depth candidates；
2. 可以调用 Binance public depth endpoint 抓当前盘口；
3. 但当前手工抓到的是历史公告对应 symbol 的当前盘口，不是公告后 12h 当时盘口。
```

Stage 1.5F 要把这个手工链路正式化，并避免两个混淆：

```text
historical_backfill_confusion:
  把 collector 首次看到的历史公告误当作实时新事件。

execution_claim_confusion:
  把当前盘口 observation 误当作历史 replay 可成交证明。
```

---

## 2. Scope / Non-Scope

### 2.1 Scope

Stage 1.5F 只做 live depth observer：

```text
input = Stage 1.5D live event-source smoke outputs
primary_event_type = futures_contract_launch
source = Binance official announcements
depth_source = Binance USD-M public depth endpoint
mode = public readonly
observation_window = 12h per eligible event-symbol
output = append-only depth snapshots + request manifest + observer summary
```

它回答：

```text
是否能只接收真正新事件？
是否能为每个新 event-symbol 建立 12h observation task？
是否能稳定采集 bid/ask/depth/slippage proxy？
是否能记录请求失败、rate limit、symbol not found、empty book？
是否能输出后续 Stage 1.5G execution-feasibility review 所需的数据？
```

### 2.2 Non-Scope

Stage 1.5F 不做：

```text
replay
forward return calculation
random baseline
strategy signal generation
position sizing
paper trading
live trading
shadow execution
order placement
execution engine integration
alpha confirmed claim
```

禁止输出：

```text
SignalCandidate
TradeIntent
buy/sell instruction
position size
entry recommendation
paper/live readiness
```

---

## 3. Upstream Evidence Gate

Stage 1.5F implementation plan 允许启动的最低证据：

```text
required:
  - Stage 1.5D source collector can produce futures_contract_launch event rows.
  - Stage 1.5E live depth one-shot path has been manually smoke-tested.
  - Stage 1.5E still does not prove execution feasibility.
  - all safety flags remain false.
```

Stage 1.5F 不要求 Stage 1.5E `ready_for_live_depth_observer`，因为当前项目的现实目标是补证据，而不是证明已通过。

但是 review 必须写明：

```text
stage1_5f_started_from_proxy_failed_state = true
reason = collect_missing_live_depth_evidence
execution_feasibility_claim_allowed = false
```

---

## 4. Event Eligibility

### 4.1 只允许真正新事件

Stage 1.5F 必须引入 watermark，不能直接消费 Stage 1.5D 当前 events 目录里的全部历史事件。

首次启动时：

```text
bootstrap_mode = establish_watermark_only
```

行为：

```text
1. 读取已有 Stage 1.5D event rows；
2. 记录最大 detected_at_ms / source_article_id / event_id；
3. 不为已有历史事件启动 12h depth observation；
4. 写入 watermark file；
5. 后续只接受 watermark 之后首次出现的新 event-symbol。
```

允许的 watermark keys：

```json
{
  "watermark_created_at_ms": 0,
  "max_seen_detected_at_ms": 0,
  "seen_event_ids": [],
  "seen_source_article_ids": [],
  "seen_stable_event_keys": []
}
```

### 4.2 Event Age Gate

即使是新出现的 event row，也必须检查 age：

```text
event_age_ms = observer_detected_at_ms - detected_at_ms
```

默认规则：

```text
event_age_ms <= EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS
```

建议默认：

```text
EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS = 15 * 60 * 1000
```

超过 age gate 的事件：

```text
observation_status = skipped_event_too_old
depth_observation_started = false
```

### 4.3 Event Type Gate

只允许：

```text
event_type = futures_contract_launch
```

其他类型：

```text
observation_status = skipped_unsupported_event_type
```

### 4.4 Symbol Gate

每个 event row 可能包含多个 symbols。Stage 1.5F 必须按 symbol 拆分：

```text
event_symbol_id = sha256(event_id + symbol)
```

如果 symbol 不在 Binance USD-M current exchangeInfo 中：

```text
depth_observation_started = false
observation_status = skipped_symbol_not_in_current_um_futures_exchangeinfo
```

注意：current exchangeInfo 只能证明当前可查，不证明历史存在或不存在。

---

## 5. Observation State Machine

每个 eligible event-symbol 进入独立状态机：

```text
pending_depth_observation
active_depth_observation
completed_12h_observation
expired_without_depth
failed_rate_limit_budget_exceeded
failed_symbol_unavailable
failed_too_many_network_errors
```

状态字段：

```json
{
  "event_symbol_id": "...",
  "event_id": "...",
  "symbol": "ABCUSDT",
  "event_type": "futures_contract_launch",
  "source_article_id": "...",
  "source_detail_url_normalized": "...",
  "event_detected_at_ms": 0,
  "observer_started_at_ms": 0,
  "observation_window_end_ms": 0,
  "last_depth_fetch_at_ms": null,
  "depth_snapshot_count": 0,
  "network_error_count": 0,
  "rate_limit_error_count": 0,
  "observation_status": "active_depth_observation"
}
```

Completion rule:

```text
completed_12h_observation if:
  now_ms >= observation_window_end_ms
  and depth_snapshot_count >= configured minimum snapshot count
```

建议默认：

```text
EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS = 12 * 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC = 60
EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COUNT_FOR_VALID_OBSERVATION = 240
```

如果用 300s cadence，则 min snapshot count 应调整为 100 左右。该阈值必须在 `configs/base.py`。

---

## 6. Depth Metrics

每次 depth fetch 输出一条 snapshot row。

### 6.1 Raw Depth Fields

```json
{
  "event_symbol_id": "...",
  "symbol": "ABCUSDT",
  "depth_fetched_at_ms": 0,
  "requested_url": "...",
  "http_status": 200,
  "best_bid_price": 0.0,
  "best_bid_qty": 0.0,
  "best_ask_price": 0.0,
  "best_ask_qty": 0.0,
  "bid_levels_count": 0,
  "ask_levels_count": 0,
  "raw_payload_hash": "...",
  "depth_timestamp_quality": "local_fetch_time_only"
}
```

如果 Binance response 不包含可审计 exchange timestamp：

```text
depth_snapshot_age_ms = null
depth_timestamp_quality = local_fetch_time_only
```

不得伪造 exchange snapshot age。

### 6.2 Derived Metrics

```text
mid_price = (best_bid_price + best_ask_price) / 2
spread_bps = (best_ask_price - best_bid_price) / mid_price * 10_000
top_1_bid_notional_usdt = best_bid_price * best_bid_qty
top_1_ask_notional_usdt = best_ask_price * best_ask_qty
top_5_bid_notional_usdt = sum(price * qty for first 5 bid levels)
top_5_ask_notional_usdt = sum(price * qty for first 5 ask levels)
top_20_bid_notional_usdt = sum(price * qty for first 20 bid levels)
top_20_ask_notional_usdt = sum(price * qty for first 20 ask levels)
```

Slippage proxy for 500 USDT notional:

```text
buy_slippage_bps_for_500usdt
sell_slippage_bps_for_500usdt
```

Rules:

```text
If book depth cannot fill 500 USDT:
  slippage_status = insufficient_depth
  slippage_bps = null

If best bid/ask missing:
  depth_status = empty_or_invalid_book
```

---

## 7. Decision Taxonomy

Stage 1.5F summary allowed decisions:

```text
stage1_5f_observer_bootstrap_watermark_only
stage1_5f_observer_running_no_new_event
stage1_5f_observer_event_observation_in_progress
stage1_5f_observer_depth_evidence_collected
stage1_5f_observer_invalid
stage1_5f_observer_failed
```

Decision rules:

```text
bootstrap_watermark_only:
  first run established watermark
  no historical event was promoted into depth observation

running_no_new_event:
  observer is healthy
  no eligible new event-symbol after watermark

event_observation_in_progress:
  at least one eligible new event-symbol is active
  12h window not complete yet

depth_evidence_collected:
  at least one event-symbol completed 12h observation
  min snapshot count passed
  request success rate passed
  safety flags false

invalid:
  missing Stage 1.5D input path
  missing watermark outside bootstrap mode
  forbidden private / execution field detected
  output schema corrupted

failed:
  repeated source read failures
  repeated depth fetch failures above threshold
  request budget exceeded
  no snapshots for active event-symbols after observation window
```

No Stage 1.5F decision may permit paper/live/execution.

---

## 8. Summary Schema

Top-level summary:

```json
{
  "stage": "stage1_5f_live_depth_observer",
  "decision": "stage1_5f_observer_running_no_new_event",
  "research_result_valid": false,
  "stage1_5f_started_from_proxy_failed_state": true,
  "execution_feasibility_claim_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "alpha_interpretation_allowed": false,
  "private_endpoint_used": false,
  "api_key_used": false,
  "order_endpoint_used": false,
  "watermark_initialized": true,
  "new_event_symbol_count": 0,
  "active_observation_count": 0,
  "completed_observation_count": 0,
  "depth_snapshot_count": 0,
  "request_success_rate": null,
  "median_spread_bps": null,
  "p95_spread_bps": null,
  "median_buy_slippage_bps_for_500usdt": null,
  "p95_buy_slippage_bps_for_500usdt": null,
  "median_sell_slippage_bps_for_500usdt": null,
  "p95_sell_slippage_bps_for_500usdt": null,
  "blockers": [],
  "allowed_next_action": "continue_live_depth_observation"
}
```

`research_result_valid` can be true only when:

```text
completed_observation_count >= 1
and each completed observation has enough snapshots
and request success rate passes
and safety flags are false
```

Even then, it means only:

```text
live_depth_evidence_valid_for_review = true
```

It does not mean:

```text
execution_feasibility_proven = true
```

Execution feasibility must be judged by a later Stage 1.5G review.

---

## 9. Storage Layout

Recommended artifact root:

```text
data/external_signal_shadow/stage1_5f/live_depth_observer/
```

Files:

```text
watermark.json
observer_state.jsonl
events_accepted/YYYYMMDD.jsonl
events_rejected/YYYYMMDD.jsonl
depth_snapshots/YYYYMMDD/{event_symbol_id}.jsonl
request_manifest/YYYYMMDD.jsonl
heartbeat/YYYYMMDD.jsonl
live_depth_observer_summary.json
```

Retention:

```text
raw depth payload cache: optional, max 14 days
normalized depth snapshots: retain indefinitely
request_manifest: retain indefinitely
summary/review: commit as decision artifacts
data JSONL: do not commit by default
```

---

## 10. Request Budget / Rate Limit

Stage 1.5F must enforce request budgets:

```text
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ACTIVE_EVENT_SYMBOLS = 30
EXTERNAL_SIGNAL_STAGE1_5F_MAX_DEPTH_REQUESTS_PER_MINUTE = 60
EXTERNAL_SIGNAL_STAGE1_5F_MAX_CONSECUTIVE_NETWORK_ERRORS = 5
EXTERNAL_SIGNAL_STAGE1_5F_HTTP_TIMEOUT_SEC = 10.0
```

If budget exceeded:

```text
observation_status = failed_rate_limit_budget_exceeded
```

The observer must fail closed:

```text
do not increase cadence automatically
do not add private endpoints
do not add websocket trading streams
do not use API keys
```

---

## 11. Server Operation Model

Stage 1.5F should run on the server, not on a laptop:

```text
tmux session = stage1_5f_depth_observer
working dir = /root/crypto-alpha-lab
python = /root/crypto-alpha-lab/.venv/bin/python
mode = public readonly
```

Expected run model:

```text
1. Stage 1.5D continues polling announcement source.
2. Stage 1.5F reads Stage 1.5D event JSONL.
3. Stage 1.5F ignores pre-watermark historical events.
4. When a truly new futures launch event appears, Stage 1.5F starts 12h depth collection.
5. Stage 1.5F writes normalized depth snapshots and summary.
```

Stage 1.5F must not depend on manual flatten commands as its production path. Manual flattening remains only a debug/smoke method.

---

## 12. Review Requirements

Stage 1.5F review must answer:

```text
1. Was the observer running and healthy?
2. Was watermark initialized correctly?
3. Did it avoid promoting historical announcements?
4. Were any truly new futures launch event-symbols observed?
5. Did each observed symbol complete 12h depth collection?
6. What were spread/depth/slippage proxy distributions?
7. Were request failures or rate limits material?
8. Does this create enough evidence for Stage 1.5G execution feasibility review?
```

Review must explicitly state:

```text
close_price_replay_execution_feasibility_still_unproven
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

---

## 13. Implementation Plan Must Cover

The Stage 1.5F implementation plan must include at least:

```text
Task 1: configs/base.py constants
Task 2: models for watermark, event-symbol state, depth snapshot, summary
Task 3: loader for Stage 1.5D event JSONL
Task 4: watermark bootstrap and dedupe
Task 5: event eligibility and age gate
Task 6: Binance public depth client with request manifest
Task 7: depth metrics and slippage proxy
Task 8: observer state machine
Task 9: storage layout and daily rotation
Task 10: summary generator
Task 11: runner CLI
Task 12: review generator
Task 13: fixture smoke and short live smoke
```

Required tests:

```text
test_bootstrap_watermark_does_not_start_observation_for_existing_events
test_new_event_after_watermark_starts_observation
test_event_age_gate_skips_old_event
test_only_futures_contract_launch_is_eligible
test_symbol_not_in_current_exchangeinfo_is_skipped_not_failed
test_depth_snapshot_computes_spread_and_top_depth
test_slippage_for_500usdt_marks_insufficient_depth
test_depth_request_manifest_is_written
test_observation_completes_after_12h_and_min_snapshot_count
test_summary_never_allows_paper_live_execution_or_alpha
test_proxy_failed_state_does_not_block_observation_only_mode
test_private_endpoint_or_api_key_usage_is_forbidden
```

---

## 14. Final Boundary

Stage 1.5F is a data acquisition and evidence-building stage.

It can produce:

```text
live_depth_evidence_collected
```

It cannot produce:

```text
execution_feasibility_proven
alpha_confirmed
paper_ready
live_ready
```

If Stage 1.5F succeeds, the next valid step is:

```text
Stage 1.5G Live Depth Evidence Review
```

Stage 1.5G may compare:

```text
1. close-price replay assumptions
2. actual live spread/depth/slippage proxy
3. event detection delay
4. first futures bar timing
5. whether the futures launch structure survives execution friction
```

Only Stage 1.5G can decide whether the observed live depth evidence is strong enough to continue research.

