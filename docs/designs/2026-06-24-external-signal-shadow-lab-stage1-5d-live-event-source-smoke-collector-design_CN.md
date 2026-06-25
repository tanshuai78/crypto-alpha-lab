# External Signal Shadow Lab Stage 1.5D Live Event-Source Smoke Collector Design

**Date:** 2026-06-24  
**Status:** design_draft  
**Owner:** External Signal Shadow Lab  
**Depends on:** Stage 1.5A / 1.5B / 1.5C / 1.5C.1  

---


## 0. Upstream Evidence Gate

Stage 1.5D implementation is allowed only if the following upstream evidence exists and matches expected decisions:

```text
required_upstream_evidence:
  - docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-review_CN.md
  - docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-review_CN.md
  - data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json
  - data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json

required_decisions:
  - Stage 1.5C.1 decision == stage1_5c1_price_coverage_ready_for_1_5c_rerun
  - Stage 1.5C rerun top_level_decision == stage1_5c_replay_completed
  - Stage 1.5C rerun research_result_valid == true
  - promising_cells contains futures_contract_launch long_attention 12h cells
  - paper_trading_allowed == false
  - live_trading_allowed == false
  - execution_engine_allowed == false
  - alpha_interpretation_allowed == false
```

If any evidence is missing or contradicts the expected values, Stage 1.5D status must be:

```text
design_blocked_pending_stage1_5c_rerun_evidence
```

and no implementation plan should be written.

---

## 1. 背景与结论

Stage 1.5C.1 已经修复 price coverage 问题，并把 Stage 1.5C 从 `no_price_history_coverage` 推进到真实 replay。

最新 Stage 1.5C 结论：

```text
top_level_decision = stage1_5c_replay_completed
research_result_valid = true
promising_cells = [
  futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay,
  futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only
]
liquidity_proxy_pass_count = 0
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
execution_engine_allowed = false
```

这说明：

```text
Binance futures_contract_launch 在 close-price replay 下有一个值得继续观察的 12h delayed long_attention 结构。
但它还没有通过执行可行性验证，不能进入 paper/live。
```

Stage 1.5D 的任务不是继续调 replay，也不是上线策略，而是验证：

```text
真实运行中，我们能否稳定、及时、可审计地采集 Binance futures launch 公告？
```

---

## 2. Scope / Non-Scope

### 2.1 Scope

Stage 1.5D 只做 live event-source smoke collector：

```text
source = Binance official announcements public endpoints
primary_event_type = futures_contract_launch
mode = live public readonly polling
output = append-only JSONL evidence
purpose = source latency / parser stability / schema drift / dedupe / first-futures-bar observation
```

它回答：

```text
公告源是否可访问？
轮询能否稳定运行？
公告检测延迟是多少？
标题解析是否稳定？
symbol extraction 是否稳定？
是否能识别 futures_contract_launch？
是否能记录 first_futures_bar_start_ms？
是否能产出可供后续 shadow/replay 对齐的 live event rows？
```

### 2.2 Non-Scope

Stage 1.5D 明确不做：

```text
forward return calculation
replay
random baseline
paper trading
live trading
shadow trading
order placement
position sizing
execution feasibility claim
alpha confirmed claim
liquidity/depth pass claim
```

禁止输出：

```text
TradeIntent
SignalCandidate for execution
paper/live recommendation
buy/sell instruction
position size
```

---

## 3. Safety Boundary

Summary / review 顶层必须包含：

```json
{
  "stage": "stage1_5d_live_event_source_smoke_collector",
  "scope": "live_event_source_smoke_only",
  "api_key_used": false,
  "private_endpoint_used": false,
  "order_endpoint_used": false,
  "wallet_endpoint_used": false,
  "execution_engine_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "alpha_interpretation_allowed": false,
  "replay_allowed": false,
  "execution_feasibility_claim_allowed": false
}
```

Network calls must be public readonly only. No API key. No account endpoint. No websocket order stream. No exchange private API.

---

## 4. Source Strategy

### 4.1 Primary Source

Primary source remains Binance official announcement-like source already audited in Stage 1.5A:

```text
source_name = binance_official_announcements
source_profile = binance_official_announcements_like_rows
allowed_domain = binance.com / www.binance.com
```

Preferred source mode:

```text
public announcement list endpoint or official announcement HTML/index source
```

The collector must store raw payload hash and normalized extracted record hash.

### 4.2 Domain Allowlist / Redirect Safety

Allowed host rule:

```text
host == binance.com
or host.endswith(".binance.com")
```

Reject:

```text
evilbinance.com
binance.com.evil.com
any redirect whose final host fails allowlist
```

For every fetch, store:

```json
{
  "requested_url": "...",
  "final_url": "...",
  "requested_host": "...",
  "final_host": "...",
  "redirect_count": 0,
  "domain_allowlist_passed": true
}
```

Redirect final URL must pass the same allowlist as the requested URL.

### 4.3 Event Type Filter

Stage 1.5D only tracks:

```text
futures_contract_launch
```

It may observe but must not promote:

```text
exchange_delisting_notice
new_coin_listing
major_unlock_event
whale_deposit
margin_enablement
unknown
```

Non-primary event types can be counted as `ignored_event_type_count`, but they do not enter the smoke event table.

---

## 5. Timing Semantics

### 5.1 Required Timestamps

Each detected event row must include:

```json
{
  "collector_received_at_ms": 0,
  "detected_at_ms": 0,
  "source_published_at_ms": 0,
  "available_at_ms": 0,
  "available_at_policy": "detected_at_ms_or_source_published_at_plus_conservative_lag",
  "detection_delay_ms": 0,
  "poll_started_at_ms": 0,
  "poll_completed_at_ms": 0
}
```

Definitions:

```text
source_published_at_ms = timestamp reported by Binance source, if available
detected_at_ms = local collector time when the event first appears in normalized output
collector_received_at_ms = local time when raw payload was fetched
available_at_ms = max(detected_at_ms, source_published_at_ms + configured conservative lag)
detection_delay_ms = detected_at_ms - source_published_at_ms, only if source_published_at_ms exists
```

`available_at_ms` must never be earlier than `detected_at_ms`.

Source-published time confidence must be explicit:

```json
{
  "source_published_at_ms_confidence": "high|medium|low",
  "source_published_at_raw": "...",
  "published_time_source": "api_field|html_field|inferred|missing",
  "source_updated_at_ms": null,
  "edited_page_risk": false,
  "historical_delay_comparison_allowed": false
}
```

If `source_published_at_ms_confidence = low` or timestamp source is missing/unreliable:

```text
available_at_ms = detected_at_ms
historical_delay_comparison_allowed = false
```

### 5.2 Conservative Delay Policy

Use Stage 1.5A / 1.5B conservative delay semantics as the default:

```text
primary_announcement_delay_ms = 15m
```

But live collector records both:

```text
source_published_at_ms_plus_15m
detected_at_ms
```

This lets future review distinguish:

```text
historical replay assumption
actual live detection latency
```

---

## 6. Event Row Schema

Append-only normalized live event row:

```json
{
  "event_id": "sha256(source_detail_url + source_published_at_ms + symbols)",
  "event_type": "futures_contract_launch",
  "source_name": "binance_official_announcements",
  "source_profile": "binance_official_announcements_like_rows",
  "source_parent_url": "...",
  "source_detail_url": "...",
  "title": "Binance Futures Will Launch USDⓈ-Margined XXXUSDT Perpetual Contract",
  "raw_payload_hash": "...",
  "event_payload_hash": "...",
  "source_published_at_ms": 0,
  "detected_at_ms": 0,
  "available_at_ms": 0,
  "detection_delay_ms": 0,
  "symbols": ["XXXUSDT"],
  "base_assets": ["XXX"],
  "symbol_parse_status": "parsed|ambiguous|missing",
  "market_scope_inferred": "um_futures",
  "first_futures_bar_start_ms": null,
  "first_futures_bar_status": "not_checked|found|not_yet_available|not_found_after_timeout",
  "stage1_5c_research_context_label": "futures_launch_long_attention_12h_close_price_replay_only",
  "signal_strength_score": null,
  "trade_signal_allowed": false,
  "replay_context_label_only": true,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "alpha_interpretation_allowed": false
}
```

Important: `stage1_5c_research_context_label` is a label only. It must not become an entry signal or `SignalCandidate`.

---

## 7. Dedupe / Revision Semantics

Do not dedupe only by `source_published_at_ms`; Binance article timestamps can change.

Each event should include:

```json
{
  "source_article_id": "parsed_binance_article_code_or_null",
  "source_detail_url_normalized": "...",
  "stable_event_key": "sha256(source_detail_url_normalized|title_normalized|base_assets)",
  "event_revision_hash": "sha256(full_normalized_record)"
}
```

Dedupe order:

```text
source_article_id if present
else source_detail_url_normalized if present
else stable_event_key
```

`event_revision_hash` detects article updates. It must not be the primary dedupe key.

---

## 8. First Futures Bar Observation

Because Stage 1.5C.1 fixed `futures_contract_launch` anchor semantics, Stage 1.5D must attempt to observe first futures bar timing.

For each new `futures_contract_launch` event:

```text
1. Extract symbols from announcement.
2. Poll Binance USD-M klines / exchangeInfo for each symbol.
3. Identify first 15m futures bar at or after detected_at_ms / source_published_at_ms.
4. Record first_futures_bar_start_ms.
5. Do not replay or trade from this value.
```

Status values:

```text
not_checked
found
not_yet_available
not_found_after_timeout
symbol_not_in_exchangeinfo_currently
network_error
```

Timeout policy should be conservative and config-driven, for example:

```text
first_bar_observation_timeout_hours = 24
first_bar_poll_interval_sec = 60
```

First-bar observation must not block announcement polling.

Required collector state machine split:

```text
announcement_poll_loop:
  poll source
  parse raw
  dedupe event
  append normalized event
  enqueue first-bar observation
  update heartbeat
  update summary

first_futures_bar_observer_queue:
  check exchangeInfo / klines for queued symbols
  update first_futures_bar_status
  respect per-poll bounded first_bar_check_budget
  never block announcement_poll_loop
```

If no async runtime is used, implementation must still enforce:

```text
per_poll_first_bar_check_budget <= configured limit
announcement polling continues even when first-bar observation fails or times out
```

---

## 9. Collector Operating Modes

### 8.1 Smoke Mode

Default mode:

```text
--mode smoke
--poll-interval-sec 60
--max-seconds 0
--live-public-readonly
```

Smoke mode writes:

Collector must record poll timing quality:

```json
{
  "configured_poll_interval_sec": 60,
  "actual_poll_interval_median_sec": null,
  "actual_poll_interval_p95_sec": null,
  "poll_duration_ms": 0,
  "poll_schedule_drift_ms": 0
}
```

This separates source delay from local collector lag.

Smoke mode writes:

```text
heartbeat JSONL
raw payload cache metadata
normalized event JSONL
source status summary
```

### 8.2 Backfill / Dry-Run Mode

For tests and parser checks:

```text
--mode dry-run
--input-fixture-jsonl / html / json
--live-public-readonly false
```

Dry-run must not touch network.

---

## 10. Output Artifacts

Proposed artifact paths:

```text
data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_raw_payloads.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_events.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_heartbeats.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_request_manifest.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json
```

Review document:

```text
docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md
```

Data files should stay gitignored by default. Review docs may be committed.

---

## 11. Storage / Rotation / Retention Policy

Stage 1.5D is long-running and must not write unbounded JSONL files.

First-pass retention policy:

```text
jsonl_rotation = daily
max_raw_payload_bytes_per_day = configured
max_heartbeat_rows_per_day = configured
raw_payload_retention_days = 14-30
request_manifest_retention_days = 30
heartbeat_retention_days = 30
normalized_event_rows_retention = indefinite
summary_review_retention = indefinite
```

If a rotation or size limit is hit, collector should fail safe:

```text
collector_status = storage_rotation_required|storage_budget_exceeded
new network polling may pause
existing files must not be truncated silently
```

Data artifacts stay gitignored. Review summaries may be committed.

---

## 12. Source Quality Metrics

Summary must report:

```json
{
  "poll_count": 0,
  "poll_success_count": 0,
  "poll_error_count": 0,
  "http_error_count": 0,
  "schema_parse_error_count": 0,
  "source_format_drift_count": 0,
  "duplicate_event_count": 0,
  "new_futures_launch_event_count": 0,
  "symbol_parse_success_count": 0,
  "symbol_parse_ambiguous_count": 0,
  "first_futures_bar_found_count": 0,
  "first_futures_bar_not_yet_available_count": 0,
  "median_detection_delay_ms": null,
  "p95_detection_delay_ms": null,
  "collector_uptime_ratio": 0.0,
  "heartbeat_gap_count": 0
}
```

Zero new events during a short window is not automatically failure. This is a sparse event source.

---

## 13. Decision Taxonomy

Stage 1.5D must separate collector health from actual event detection.

Allowed decisions:

```text
stage1_5d_operational_pass_event_detection_unvalidated
stage1_5d_event_detection_passed
stage1_5d_smoke_failed
stage1_5d_smoke_invalid
```

Meaning:

```text
operational_pass_event_detection_unvalidated:
  collector ran reliably, but no futures launch event occurred during observation window

event_detection_passed:
  at least one live futures launch event was detected, parsed, deduped, timestamped, and first-bar observation reached found/not_yet_available state

smoke_failed:
  public source was reachable but collector stability, parser, heartbeat, or source-quality gates failed

smoke_invalid:
  safety boundary violation, forbidden payload, domain/redirect failure, missing manifest, or private endpoint/API key detected
```

Zero-event smoke cannot be labeled `event_detection_passed`.

---

## 14. Smoke Pass / Fail Criteria

### 11.1 Operational Pass

A smoke run can pass operationally even with zero events if:

```text
observation_hours >= configured_min_observation_hours
poll_success_rate >= 0.95
schema_parse_error_count == 0
source_format_drift_count == 0
forbidden_payload_count == 0
heartbeat_gap_count <= configured_max_gap_count
api_key_used = false
private_endpoint_used = false
```

### 11.2 Event Detection Pass

If events occur, event detection passes only if:

```text
symbol_parse_success_rate >= 0.95
source_detail_url_present_rate >= 0.95
raw_payload_hash_present_rate = 1.0
available_at_ms_present_rate = 1.0
first_futures_bar_status is found or not_yet_available with rerun_after_ms
```

### 11.3 Fail / Invalid

Invalid if:

```text
private endpoint used
api key detected
forbidden payload detected
source domain not allowed
parser silently returns zero records after raw source has changed shape
request manifest missing
heartbeat missing for long gaps without explanation
```

---

## 15. Relationship With Execution Feasibility Audit

Stage 1.5D should run before execution feasibility audit because it answers whether the live event source is stable enough to observe.

Recommended sequence:

```text
1. Implement Stage 1.5D live event-source smoke collector.
2. Run for at least 7 days, preferably 14 days.
3. In parallel, write Execution Feasibility Data Audit Plan.
4. After live events or stable collector evidence exists, run execution feasibility audit around detected or historical launch windows.
5. Only if both pass, design later shadow observation. No paper/live before that.
```

Execution feasibility audit must separately check:

```text
spread_bps
top_0_5pct_depth_usdt
top_1pct_depth_usdt
slippage_estimate_bps_for_500usdt
15m quote volume around 12h entry
entry-window depth collapse
orderbook availability
```

---

## 16. Recommended Implementation Split

Do not implement everything as one script blob. Suggested modules:

```text
src/research/external_signal_shadow/stage1_5d_live_event_source_models.py
src/research/external_signal_shadow/stage1_5d_live_event_source_client.py
src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py
src/research/external_signal_shadow/stage1_5d_live_event_source_collector.py
src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
scripts/external_signal_shadow/review_stage1_5d_live_event_source_smoke_collector.py
```

Implementation plan must use TDD and include tests for:

```text
no network without --live-public-readonly
forbidden payload veto
source domain allowlist
symbol extraction from Binance futures launch title
duplicate event dedupe
available_at_ms never before detected_at_ms
heartbeat gap detection
zero-event operational pass
first futures bar status transitions
summary/review safety flags
design requires Stage 1.5C rerun promising evidence
zero-event smoke can only be operational pass, not event detection pass
available_at_ms uses detected_at_ms when source time confidence is low
redirect final domain must pass allowlist
poll schedule drift is reported
dedupe uses stable article id or normalized detail URL, not timestamp only
first-bar observer does not block announcement poll loop
raw payload rotation policy is enforced
research context label does not create SignalCandidate or TradeIntent
```

---

## 17. Decision

```text
decision = design_ready_for_implementation_plan_after_required_evidence_gate
next_action = write_stage1_5d_live_event_source_smoke_collector_implementation_plan
scope = live_event_source_smoke_only
upstream_evidence_required = true
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```
