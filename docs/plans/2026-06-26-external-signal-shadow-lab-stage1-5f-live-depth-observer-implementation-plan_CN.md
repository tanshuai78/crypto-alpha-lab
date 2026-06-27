# External Signal Shadow Lab Stage 1.5F Live Depth Observer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task. For every code task, write/extend tests before implementation.

**Date:** 2026-06-26  
**Status:** implementation_plan_draft  
**Design:** `docs/designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md`  
**Goal:** 将 Stage 1.5D live event-source 输出与 Binance USD-M public depth endpoint 串成一个可恢复、可审计、只观察真正新事件的 12h live depth evidence recorder。

---

## 0.1 Review Decision

```text
decision = approved_with_required_fixes_absorbed
must_fix_before_coding = absorbed
scope = live_depth_observation_only
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

本版 plan 已吸收的阻断修正：

```text
1. Stage 1.5E summary missing 只允许 bootstrap watermark，不允许正式 observation。
2. Stage 1.5D summary 必须验证 safety flags 和 source collector decision。
3. fixture inputs 拆分为 fixture-events / mock-response-dir，不再复用单一 --fixture-json。
4. post-watermark 判断支持 same detected_at_ms but unseen article/event。
5. request_manifest 必须记录 payload hash / payload size，且不能记录 secret。
6. Stage 1.5F 增加 MIN_REQUEST_SUCCESS_RATE 并用于 decision。
7. event_symbol_id 来源和 fallback 明确，保证重启稳定。
8. observer_state.jsonl 增加 startup compaction，避免长期无界增长。
9. heartbeat 字段、写入时机、summary 引用明确。
10. --live-public-readonly 在 client 层 hard gate，fixture mode 禁止真实网络。
11. snapshot gap 调整为 5min，并与 coverage ratio / poll interval 形成一致测试。
```

---

## 0. 执行边界

```text
decision = approved_with_required_fixes_absorbed
scope = live_depth_observation_only
source_stage = stage1_5d_live_event_source_smoke_collector
primary_event_type = futures_contract_launch
depth_source = Binance USD-M public depth endpoint
mode = public_readonly
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
SignalCandidate_allowed = false
TradeIntent_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
private_endpoint_allowed = false
api_key_allowed = false
order_endpoint_allowed = false
```

Stage 1.5F 只能回答：

```text
1. 是否只接受 watermark 之后的真实新 futures_contract_launch event-symbol？
2. 是否能为新 event-symbol 连续采集 12h public depth snapshots？
3. depth snapshot 的 spread / top depth / 500 USDT slippage proxy 是否可审计？
4. 是否能输出 Stage 1.5G Live Depth Evidence Review 所需的证据？
```

Stage 1.5F 不能回答：

```text
是否有 alpha
是否可以 paper/live
是否可以执行
是否 close-price replay 已被证明可成交
```

---

## 1. 输入 / 输出

### 1.1 Required Inputs

Stage 1.5D event source smoke outputs:

```text
data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl
data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json
```

Stage 1.5E evidence summary, used only as context and safety boundary:

```text
data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
```

If Stage 1.5E summary is missing, runner can still bootstrap `watermark` but must set:

```text
bootstrap_watermark allowed
live depth observation not allowed
stage1_5e_context_missing = true
execution_feasibility_claim_allowed = false
research_result_valid = false
non-bootstrap decision = stage1_5f_observer_invalid
non-bootstrap blocker = stage1_5e_context_missing_for_observation
```

Stage 1.5D summary must also be validated before non-bootstrap observation:

```text
stage1_5d decision not in {stage1_5d_smoke_invalid, stage1_5d_smoke_failed}
paper_trading_allowed == false
live_trading_allowed == false
execution_engine_allowed == false
alpha_interpretation_allowed == false
trade_signal_allowed == false if present
```

If Stage 1.5D summary is invalid or unsafe:

```text
decision = stage1_5f_observer_invalid
blocker = stage1_5d_summary_invalid_or_unsafe
```

### 1.2 Outputs

Artifact root:

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

Review:

```text
docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

---

## 2. Config Constants

### Task 1: Add Stage 1.5F config constants

- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py`

Add constants:

```python
EXTERNAL_SIGNAL_STAGE1_5F_BINANCE_FAPI_BASE_URL = "https://fapi.binance.com"
EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_PATH = "/fapi/v1/depth"
EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_PATH = "/fapi/v1/exchangeInfo"
EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_LIMIT = 100
EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS = 12 * 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC = 60
EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COVERAGE_RATIO = 0.80
EXTERNAL_SIGNAL_STAGE1_5F_MAX_SNAPSHOT_GAP_MS = 5 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS = 15 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ACTIVE_EVENT_SYMBOLS = 30
EXTERNAL_SIGNAL_STAGE1_5F_MAX_DEPTH_REQUESTS_PER_MINUTE = 60
EXTERNAL_SIGNAL_STAGE1_5F_MIN_REQUEST_SUCCESS_RATE = 0.95
EXTERNAL_SIGNAL_STAGE1_5F_MAX_CONSECUTIVE_NETWORK_ERRORS = 5
EXTERNAL_SIGNAL_STAGE1_5F_HTTP_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_REFRESH_SEC = 300
EXTERNAL_SIGNAL_STAGE1_5F_SLIPPAGE_NOTIONAL_USDT = 500.0
EXTERNAL_SIGNAL_STAGE1_5F_WATERMARK_VERSION = 1
```

Snapshot coverage formula:

```text
expected_snapshot_count =
  floor(EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS
        / (EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC * 1000))

min_snapshot_count =
  floor(expected_snapshot_count * EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COVERAGE_RATIO)

default:
  floor(12 * 3600 / 60 * 0.80) = 576
```

`EXTERNAL_SIGNAL_STAGE1_5F_MAX_SNAPSHOT_GAP_MS = 5min` allows short network jitter while still detecting material observation gaps.

Required tests:

```text
test_stage1_5f_config_constants_exist
test_depth_limit_large_enough_for_top_20_metrics
test_min_snapshot_count_computed_from_window_poll_interval_and_coverage_ratio
test_max_snapshot_gap_is_consistent_with_coverage_ratio_and_poll_interval
test_request_success_rate_threshold_exists
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_config.py -q
```

---

## 3. Models

### Task 2: Add model module

- Create: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py`

Implement lightweight dataclass / enum models:

```text
LiveDepthObserverDecision
Watermark
EventSymbolState
DepthSnapshot
RequestManifestRow
HeartbeatRow
LiveDepthObserverSummary
```

Allowed decisions:

```text
stage1_5f_observer_bootstrap_watermark_only
stage1_5f_observer_running_no_new_event
stage1_5f_observer_event_observation_in_progress
stage1_5f_observer_depth_evidence_collected
stage1_5f_observer_invalid
stage1_5f_observer_failed
```

Required tests:

```text
test_decision_enum_values_are_exact
test_watermark_model_requires_version
test_event_symbol_state_contains_observation_window_fields
test_depth_snapshot_contains_safety_and_metric_fields
test_summary_defaults_never_allow_paper_live_execution_or_alpha
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py -q
```

---

## 4. Watermark

### Task 3: Atomic watermark read/write and validation

- Create: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py`

Implement:

```text
load_watermark(path)
validate_watermark(data)
write_watermark_atomic(path, watermark)
bootstrap_watermark_from_stage1_5d_events(events)
event_is_post_watermark(event, watermark)
update_watermark_with_event(watermark, event)
```

Post-watermark rule:

```text
post_watermark if:
  detected_at_ms > max_seen_detected_at_ms
  OR detected_at_ms == max_seen_detected_at_ms
     AND event_id/source_article_id/stable_event_key not in seen sets

pre_watermark if:
  detected_at_ms < max_seen_detected_at_ms
  OR detected_at_ms == max_seen_detected_at_ms
     AND event_id/source_article_id/stable_event_key already seen
```

This handles multiple new articles discovered in the same poll with identical `detected_at_ms`.

Atomic write rule:

```text
write watermark.tmp
flush
fsync
os.replace(tmp, target)
fsync parent dir where supported
```

Corruption rule:

```text
invalid JSON / missing watermark_version / wrong field types -> corrupted_watermark
```

Required tests:

```text
test_watermark_write_is_atomic
test_corrupted_watermark_makes_observer_invalid
test_missing_watermark_requires_bootstrap_mode
test_bootstrap_watermark_does_not_start_observation_for_existing_events
test_new_event_after_watermark_is_detected_as_post_watermark
test_pre_watermark_event_is_counted_as_ignored_not_rejected_failure
test_event_same_detected_at_but_unseen_article_is_post_watermark
test_event_same_detected_at_and_seen_article_is_pre_watermark
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_watermark.py -q
```

---

## 5. Stage 1.5D Event Loader

### Task 4: Load and flatten Stage 1.5D events

- Create: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`

Implement:

```text
iter_stage1_5d_event_rows(events_glob)
flatten_event_symbols(event_row)
make_event_symbol_id(event_id, symbol)
classify_event_symbol_eligibility(row, now_ms, watermark, exchangeinfo_state, budget_state)
validate_stage1_5d_summary(summary_path)
```

`event_symbol_id` stability rules:

```text
primary event_id source:
  event_row["event_id"]

fallback if event_id is missing:
  sha256(source_name + source_article_id + source_detail_url_normalized + source_published_at_ms + symbol)

event_symbol_id:
  sha256(normalized_event_id + "|" + symbol)

output format:
  lowercase hex sha256
  length = 64
  charset = [0-9a-f]
```

The fallback is allowed only for observation identity, not for claiming upstream event integrity.

Eligibility rules:

```text
event_type must be futures_contract_launch
event must be post-watermark
event_age_ms <= EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS
symbol must be present
symbol must be in current exchangeInfo, unless exchangeInfo is unavailable
```

If exchangeInfo unavailable:

```text
observation_status = pending_exchangeinfo_unavailable
```

Rejected / ignored event-symbol rows must include:

```json
{
  "event_symbol_id": "...",
  "symbol": "ABCUSDT",
  "rejection_reason": "pre_watermark|wrong_event_type|age_exceeded|symbol_missing|symbol_not_in_exchangeinfo|exchangeinfo_unavailable|budget_exceeded",
  "depth_observation_started": false
}
```

`pre_watermark` is an ignored historical baseline row, not a failure.

Required tests:

```text
test_only_futures_contract_launch_is_eligible
test_event_age_gate_skips_old_event
test_symbol_not_in_current_exchangeinfo_is_skipped_not_failed
test_exchangeinfo_unavailable_keeps_event_pending_not_symbol_not_found
test_multiple_symbols_are_flattened_to_event_symbol_rows
test_event_symbol_id_is_stable
test_event_symbol_id_is_stable_across_restarts_with_same_input
test_event_symbol_id_fallback_is_stable_when_event_id_missing
test_stage1_5f_rejects_invalid_stage1_5d_summary
test_stage1_5f_rejects_stage1_5d_summary_with_trading_flag_true
test_rejected_event_rows_include_rejection_reason
test_pre_watermark_rejection_reason_is_ignored_not_failure
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py -q
```

---

## 6. ExchangeInfo and Public Client

### Task 5: Add public Binance USD-M client

- Create: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py`

Implement:

```text
build_binance_fapi_url(path, params)
build_depth_url(symbol, limit)
build_exchangeinfo_url()
fetch_public_json(url, timeout_sec)
parse_exchangeinfo_symbols(payload)
refresh_exchangeinfo_cache(now_ms, previous_cache)
fetch_depth_snapshot(symbol)
```

Network hard gate:

```text
fetch_public_json(..., live_public_readonly=False) must raise RuntimeError
fixture/mock mode must never call real network
```

Safety requirements:

```text
host must be fapi.binance.com or allowed Binance host
no API key
no private endpoint
no order endpoint
request manifest row written for each public request
```

Request manifest row must include:

```json
{
  "requested_host": "fapi.binance.com",
  "requested_path": "/fapi/v1/depth",
  "requested_url_hash": "...",
  "final_url_hash": "...",
  "http_status": 200,
  "payload_size_bytes": 0,
  "response_payload_hash": "...",
  "retry_count": 0,
  "error": null,
  "fetched_at_ms": 0
}
```

Do not persist API keys, secrets, or full query strings that may contain sensitive parameters.

`exchangeInfo` cache:

```text
refresh every EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_REFRESH_SEC
temporary fetch failure -> exchangeinfo_status = unavailable / stale
do not mark symbol missing from one failed refresh
```

Required tests:

```text
test_depth_url_uses_configured_limit
test_exchangeinfo_refresh_respects_cadence
test_exchangeinfo_fetch_failure_marks_unavailable_not_empty_symbol_set
test_public_client_rejects_non_binance_host
test_public_client_does_not_accept_private_or_order_endpoint
test_request_manifest_row_contains_requested_url_status_error_and_fetched_at
test_request_manifest_contains_payload_hash_and_size
test_request_manifest_does_not_store_api_key_or_secret_fields
test_runner_raises_if_network_called_without_live_flag
test_fixture_mode_does_not_call_real_network
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py -q
```

---

## 7. Depth Metrics

### Task 6: Compute spread, top-depth, and 500 USDT slippage proxy

- Create: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_metrics.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_metrics.py`

Implement:

```text
parse_depth_payload(symbol, payload, fetched_at_ms)
compute_mid_price(best_bid, best_ask)
compute_spread_bps(best_bid, best_ask)
compute_top_notional(levels, n)
walk_book_for_quote_notional(levels, notional_usdt)
compute_buy_sell_slippage_for_notional(snapshot, notional_usdt)
```

Slippage formula:

```text
buy_vwap = walk asks until cumulative quote >= 500 USDT
buy_slippage_bps = (buy_vwap / mid_price - 1) * 10_000

sell_vwap = walk bids until cumulative quote >= 500 USDT
sell_slippage_bps = (1 - sell_vwap / mid_price) * 10_000
```

If depth cannot fill 500 USDT:

```text
slippage_status = insufficient_depth
slippage_bps = null
```

Required tests:

```text
test_depth_snapshot_computes_spread_and_top_depth
test_buy_slippage_uses_ask_vwap_vs_mid_price
test_sell_slippage_uses_bid_vwap_vs_mid_price
test_slippage_for_500usdt_marks_insufficient_depth
test_empty_book_marks_depth_status_invalid
test_zero_price_book_marks_depth_status_invalid
test_depth_timestamp_quality_local_fetch_time_only_when_exchange_time_missing
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_metrics.py -q
```

---

## 8. State Machine and Resume

### Task 7: Implement observation state machine

- Create: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`

Implement:

```text
load_latest_state_by_event_symbol_id(observer_state_jsonl)
compact_observer_state_jsonl(observer_state_jsonl)
start_observation(event_symbol_row, now_ms)
resume_observations(states, now_ms)
record_depth_snapshot(state, snapshot)
finalize_observation_if_due(state, now_ms, snapshots)
compute_snapshot_time_coverage(state, snapshots)
```

Resume rules:

```text
active + now < observation_window_end_ms -> resume without changing start/end
active + now >= end -> complete if coverage passes, otherwise expired_without_depth
terminal -> do not restart
```

State compaction policy:

```text
On startup:
  read observer_state.jsonl
  keep only latest row per event_symbol_id
  write compacted state to observer_state.compacted.tmp
  atomic rename to observer_state.jsonl
  backup original to observer_state.YYYYMMDD_HHMMSS.jsonl.bak
```

This keeps resume cost bounded during multi-week server runs.

Snapshot coverage:

```text
depth_snapshot_count >= min_snapshot_count_required
first_snapshot_ms <= observer_started_at_ms + 2 * poll_interval_ms
last_snapshot_ms >= observation_window_end_ms - 2 * poll_interval_ms
max_observed_snapshot_gap_ms <= EXTERNAL_SIGNAL_STAGE1_5F_MAX_SNAPSHOT_GAP_MS
```

Required tests:

```text
test_restart_resumes_active_observation_without_resetting_window
test_restart_expires_old_active_observation_without_enough_snapshots
test_observation_completes_after_12h_and_min_snapshot_count
test_research_result_valid_requires_snapshot_time_coverage_not_only_count
test_terminal_observation_is_not_restarted
test_startup_compacts_observer_state_to_latest_row_per_event_symbol
test_state_compaction_writes_backup_before_replace
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py -q
```

---

## 9. Request Budget

### Task 8: Implement request budget precheck

- Add to: `stage1_5f_live_depth_observer_state.py` or new `stage1_5f_live_depth_observer_budget.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_budget.py`

Implement:

```text
estimate_requests_per_min(active_count, depth_requests_per_symbol_per_poll, poll_interval_sec, exchangeinfo_refresh_requests_per_min)
can_start_new_observation(active_count, estimated_requests_per_min)
classify_budget_status(...)
```

Rules:

```text
active_count >= EXTERNAL_SIGNAL_STAGE1_5F_MAX_ACTIVE_EVENT_SYMBOLS -> skip new event-symbol
estimated_requests_per_min > EXTERNAL_SIGNAL_STAGE1_5F_MAX_DEPTH_REQUESTS_PER_MINUTE -> skip new event-symbol
active observation exceeding live budget -> failed_rate_limit_budget_exceeded
```

Required tests:

```text
test_new_event_skipped_when_request_budget_full
test_active_symbols_cannot_exceed_max_active_event_symbols
test_estimated_requests_per_min_accounts_for_poll_interval
test_exchangeinfo_refresh_request_budget_is_included
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_budget.py -q
```

---

## 10. Storage

### Task 9: Add storage helpers and daily rotation

- Create: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py`

Implement:

```text
build_daily_path(root, stream_name, timestamp_ms)
append_jsonl(path, row)
write_json(path, data)
read_jsonl(path)
write_watermark_atomic delegated from watermark module
```

Required streams:

```text
events_accepted/YYYYMMDD.jsonl
events_rejected/YYYYMMDD.jsonl
depth_snapshots/YYYYMMDD/{event_symbol_id}.jsonl
request_manifest/YYYYMMDD.jsonl
heartbeat/YYYYMMDD.jsonl
observer_state.jsonl
live_depth_observer_summary.json
```

Required tests:

```text
test_build_daily_path_uses_utc_date
test_append_jsonl_preserves_existing_rows
test_depth_snapshot_path_is_per_event_symbol_id
test_storage_does_not_write_outside_output_root
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_storage.py -q
```

---

## 11. Summary

### Task 10: Add summary generator

- Create: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`

Implement:

```text
build_live_depth_observer_summary(...)
compute_request_success_rate(request_manifest_rows)
compute_spread_slippage_distribution(depth_snapshots)
derive_stage1_5f_decision(...)
```

Decision rules:

```text
bootstrap_watermark_only:
  watermark initialized and no historical events promoted

running_no_new_event:
  healthy polling, watermark initialized, no post-watermark eligible event

event_observation_in_progress:
  active_observation_count > 0 and no completed observation yet

depth_evidence_collected:
  completed_observation_count >= 1
  min snapshot count and time coverage pass
  request success rate >= EXTERNAL_SIGNAL_STAGE1_5F_MIN_REQUEST_SUCCESS_RATE
  safety flags false

invalid:
  missing input path, corrupted watermark, forbidden fields, schema corruption

failed:
  repeated depth failures, rate budget exceeded, active events expired without usable depth
```

Required tests:

```text
test_bootstrap_summary_never_marks_research_result_valid
test_running_no_new_event_summary_is_not_research_valid
test_depth_evidence_collected_requires_completed_observation
test_research_result_valid_requires_snapshot_time_coverage_not_only_count
test_summary_never_allows_paper_live_execution_or_alpha
test_proxy_failed_state_does_not_block_observation_only_mode
test_summary_reports_pre_and_post_watermark_counts
test_summary_reports_exchangeinfo_and_budget_counts
test_depth_evidence_collected_requires_request_success_rate_threshold
test_low_request_success_rate_makes_observer_failed
test_summary_reports_heartbeat_count_and_last_heartbeat_at_ms
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py -q
```

---

## 12. Runner CLI

### Task 11: Add observer runner

- Create: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

CLI:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob 'data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl' \
  --stage1-5d-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --stage1-5e-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json \
  --output-root data/external_signal_shadow/stage1_5f/live_depth_observer \
  --bootstrap-watermark \
  --live-public-readonly
```

Modes:

```text
--bootstrap-watermark:
  create watermark from existing events and exit
  do not start observation

--max-polls N:
  bounded smoke run

--max-seconds N:
  bounded server run

--live-public-readonly:
  required for network calls

--fixture-events-jsonl:
  event fixture input

--mock-response-dir:
  fixture/mock HTTP response directory for depth and exchangeInfo payloads
  no real network allowed
```

Runner must:

```text
1. Validate safety flags.
2. Validate Stage 1.5D summary.
3. Validate Stage 1.5E summary; missing summary permits bootstrap only.
4. Load or bootstrap watermark.
5. Load Stage 1.5D events and classify event-symbols.
6. Load/compact/resume observer state.
7. Refresh exchangeInfo using cache cadence.
8. Start eligible new observations only if budget allows.
9. Fetch public depth for active observations.
10. Append snapshots / request manifest / heartbeat / state.
11. Write summary every poll.
```

Heartbeat:

```text
write one heartbeat row at the end of every poll, even when no events exist
```

Heartbeat fields:

```json
{
  "poll_index": 0,
  "poll_at_ms": 0,
  "active_count": 0,
  "completed_count": 0,
  "last_error": null,
  "budget_status": "ok",
  "watermark_updated_at_ms": 0
}
```

Required tests:

```text
test_runner_bootstrap_watermark_does_not_fetch_depth
test_runner_requires_live_public_readonly_for_network
test_missing_stage1_5e_summary_allows_bootstrap_only
test_missing_stage1_5e_summary_blocks_observation_run
test_runner_fixture_events_do_not_require_network
test_runner_fixture_depth_payload_used_without_live_public_readonly
test_runner_mock_response_dir_keeps_network_disabled
test_runner_resumes_active_observation_from_state
test_runner_skips_pre_watermark_events
test_runner_starts_post_watermark_event_observation
test_runner_writes_summary_each_poll
test_runner_writes_heartbeat_every_poll_including_no_event_polls
test_private_endpoint_or_api_key_usage_is_forbidden
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py -q
```

---

## 13. Review Generator

### Task 12: Add review generator

- Create: `scripts/external_signal_shadow/review_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_5f_live_depth_observer.py`

Review must include:

```text
Decision
Watermark / bootstrap status
Pre-watermark ignored count
Post-watermark accepted count
Active / completed / expired observations
Depth snapshot coverage
Spread / top depth / slippage proxy distributions
Request health / rate limit / network error counts
Safety flags
Allowed next action
Why execution feasibility is still not proven
```

No placeholders:

```text
TODO
TBD
placeholder
FIXME
```

Required tests:

```text
test_review_contains_decision_and_safety_flags
test_review_states_close_price_replay_execution_feasibility_still_unproven
test_review_has_no_placeholders
test_review_reports_watermark_and_snapshot_coverage
test_review_reports_allowed_next_action_stage1_5g_only_when_depth_evidence_collected
```

Verification:

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5f_live_depth_observer.py -q
```

---

## 14. Fixture and Short Live Smoke

### Task 13: Add fixtures and smoke commands

Fixtures:

```text
tests/fixtures/external_signal_shadow/stage1_5f/stage1_5d_events_existing_history.jsonl
tests/fixtures/external_signal_shadow/stage1_5f/stage1_5d_events_post_watermark_new_event.jsonl
tests/fixtures/external_signal_shadow/stage1_5f/mock_responses/binance_depth_payload_healthy.json
tests/fixtures/external_signal_shadow/stage1_5f/mock_responses/binance_depth_payload_insufficient_depth.json
tests/fixtures/external_signal_shadow/stage1_5f/mock_responses/binance_exchangeinfo_payload.json
```

Fixture smoke command:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --fixture-events-jsonl tests/fixtures/external_signal_shadow/stage1_5f/stage1_5d_events_existing_history.jsonl \
  --mock-response-dir tests/fixtures/external_signal_shadow/stage1_5f/mock_responses \
  --output-root data/external_signal_shadow/stage1_5f/fixture_smoke \
  --bootstrap-watermark \
  --max-polls 1
```

Short live smoke command:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob 'data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl' \
  --stage1-5d-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --stage1-5e-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json \
  --output-root data/external_signal_shadow/stage1_5f/live_depth_observer \
  --max-polls 3 \
  --live-public-readonly
```

Short live smoke expected:

```text
If watermark already exists and no new event:
  decision = stage1_5f_observer_running_no_new_event
  research_result_valid = false

If new post-watermark event appears:
  decision = stage1_5f_observer_event_observation_in_progress
  research_result_valid = false until 12h coverage completes
```

---

## 15. Full Verification

Run targeted tests:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/scripts/external_signal_shadow/test_*stage1_5f* \
  -q
```

Run lint:

```bash
PYTHONPATH=src:. uv run ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_*.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  scripts/external_signal_shadow/review_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/scripts/external_signal_shadow/test_*stage1_5f*
```

Safety grep:

```bash
rg -n "from .*TradeIntent|TradeIntent\\(|from .*SignalCandidate|SignalCandidate\\(|order_endpoint\\s*=\\s*True|account_endpoint\\s*=\\s*True|private_ws|apiKey\\s*=|api_key\\s*=|secret\\s*=" \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_*.py \
  scripts/external_signal_shadow/*stage1_5f* \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  tests/scripts/external_signal_shadow/test_*stage1_5f*
```

Expected:

```text
pytest: all pass
ruff: all pass
safety grep: 0 hits, except literal safety flag names inside tests/docs if explicitly allowed
```

---

## 16. Server Deployment Notes

Server run should use `tmux`:

```bash
cd "${PROJECT_ROOT:-/root/crypto-alpha-lab}"
. .venv/bin/activate
tmux new -s stage1_5f_depth_observer
```

If the server project path is not `/root/crypto-alpha-lab`, set:

```bash
export PROJECT_ROOT=/actual/path/to/crypto-alpha-lab
```

Bootstrap watermark first:

```bash
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob 'data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl' \
  --stage1-5d-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --stage1-5e-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json \
  --output-root data/external_signal_shadow/stage1_5f/live_depth_observer \
  --bootstrap-watermark \
  --live-public-readonly
```

Then run observer:

```bash
PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  --stage1-5d-events-glob 'data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl' \
  --stage1-5d-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --stage1-5e-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json \
  --output-root data/external_signal_shadow/stage1_5f/live_depth_observer \
  --max-seconds 43200 \
  --live-public-readonly
```

Detach:

```text
Ctrl-b
d
```

Check:

```bash
tmux capture-pane -t stage1_5f_depth_observer -p | tail -n 80
cat data/external_signal_shadow/stage1_5f/live_depth_observer/live_depth_observer_summary.json
find data/external_signal_shadow/stage1_5f/live_depth_observer/depth_snapshots -type f | tail
```

---

## 17. Completion Criteria

Implementation is complete only when:

```text
1. All Stage 1.5F targeted tests pass.
2. Ruff passes on all touched files.
3. Fixture bootstrap proves historical events are not promoted.
4. Fixture post-watermark event starts observation.
5. Corrupted watermark produces invalid decision.
6. Restart/resume tests prove 12h window is not reset.
7. Depth metrics tests prove VWAP vs mid_price slippage formula.
8. Summary/review never allows paper/live/execution/alpha.
9. Short live smoke writes summary and does not use private endpoints.
10. Docs/review clearly states execution feasibility remains unproven until Stage 1.5G.
```

Allowed next action after implementation:

```text
If no new event:
  continue server observer.

If at least one event-symbol completes 12h with valid snapshot coverage:
  write Stage 1.5G Live Depth Evidence Review plan.

If observer fails:
  debug Stage 1.5F source/depth/watermark/storage path.
```
