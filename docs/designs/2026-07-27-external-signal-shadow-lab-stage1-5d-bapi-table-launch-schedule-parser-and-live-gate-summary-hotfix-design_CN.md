# Stage 1.5D BAPI Table Launch Schedule Parser and Runtime Gate Hotfix Design

```text
status = design_revised_after_external_review
scope = stage1_5d_bapi_table_launch_schedule_parser_hotfix_plus_stage1_5d_runtime_gate
primary_fix = bapi_article_body_table_aware_symbol_and_launch_time_extraction
companion_fix = dedicated_stage1_5d_runtime_gate_for_stage1_5f
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

Stage 1.5D 当前职责是从 Binance Futures announcement list 中发现 futures contract launch 公告，解析 symbol 与 per-symbol launch/onboard time，写入 1.5D consumable event rows，供 Stage 1.5F 决定是否启动 12h public depth observation。

已完成的 BAPI detail source hotfix 解决了旧 support detail path 长期 `HTTP 202 empty` 的问题：当标题无法解析 symbol 时，1.5D 会优先请求 Binance first-party public-readonly web BAPI detail endpoint：

```text
GET /bapi/composite/v1/public/cms/article/detail/query?articleCode=<articleCode>
```

该 endpoint 的 transport 必须继续按以下口径描述：

```text
content_provenance = binance_official_announcement
source_transport = binance_first_party_public_web_bapi_undocumented
```

不能称为 official supported API、documented API 或 Binance 承诺稳定的 public API。

2026-07-27 新公告暴露出新的 parser 缺口：BAPI detail 请求成功，payload trusted，但 parser 返回 `symbols=[]`，导致 1.5D 没有 emit consumable event，1.5F 没有进入 accepted/rejected/pending state。

同时，运维中暴露出 Stage 1.5D -> Stage 1.5F 接口缺口：1.5D continuous runner 通常在 7d runner 结束时才写 `binance_futures_launch_smoke_summary.json`，但 1.5F 启动时需要 safety gate artifact。当前线上只能让 1.5F 使用旧 root 的 baseline summary，这形成 cross-root dependency，不能作为长期接口。

本 design 将两类问题放在同一份 hotfix 中描述，但实现和提交必须拆分：

```text
Task A commit: BAPI table/list launch schedule parser hotfix
Task B commit: dedicated Stage 1.5D runtime gate + Stage 1.5F validator hotfix
```

两个 task 必须可独立 rollback。

## 2. 触发证据

### 2.1 A827 公告事实

```text
articleCode = a827177a387e4ebea830110ba222ca48
title = Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-27)
list_releaseDate_ms = 1785143762441
list_release_utc = 2026-07-27T09:16:02.441Z
expected_symbols = TMFUSDT, TBTUSDT, BITOUSDT
expected_launch_times_utc = 2026-07-27T13:30:00Z, 2026-07-27T13:35:00Z, 2026-07-27T13:40:00Z
```

Server-side Stage 1.5D scheduler evidence:

```text
article_in_scheduler = true
detail_http_request_count = 31
detail_retry_cycle_count = 15
candidate_symbols = null
symbol_effective_launch_times_ms = null
last_detail_failure_class = http_202_empty
```

Request manifest aggregate:

```text
bapi_article_detail_query = 15 rows
primary support detail = 15 rows
detail_path_fallback = 1 row
HTTP 200 = 15 rows
HTTP 202 = 16 rows
payload_trusted true = 15 BAPI rows
```

Parser reproduction from saved BAPI payload showed:

```json
{
  "symbols": [],
  "symbol_launch_times_ms": {},
  "symbol_extraction_source": "none",
  "extracted_text_prefix": "... Binance Futures will launch the following perpetual contract(s) as below:\n2026-07-27 13:30 (UTC):\nTMFUSDT\n Perpetual Contract\n2026-07-27 13:35 (UTC):\nTBTUSDT\n Perpetual Contract\n2026-07-27 13:40 (UTC):\nBITOUSDT\n Perpetual Contract ..."
}
```

Conclusion:

```text
network/BAPI health = not root cause
support HTTP 202 = downstream fallback symptom
Stage 1.5F admission = not root cause
root cause = BAPI body parser cannot parse separated/table schedule structure
```

### 2.2 Runtime gate interface fact

1.5D current root is launched with:

```text
--output-summary data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix/binance_futures_launch_smoke_summary.json
--max-seconds 604800
```

During the 7d run this file may not exist yet:

```text
ls: cannot access .../binance_futures_launch_smoke_summary.json: No such file or directory
```

1.5F currently validates `--stage1-5d-summary` only at startup via `validate_stage1_5d_summary(...)`. The existing validator is too broad for a live runtime gate: it uses a denylist for invalid/failed decisions and would accept unknown decisions if safety flags are false. Therefore the runtime gate must not reuse this validator.

## 3. Required Preflight Evidence Capture

Before implementation, freeze the real A827 BAPI payload as a fixture or immutable local artifact.

Required metadata:

```text
articleCode = a827177a387e4ebea830110ba222ca48
raw_payload_sha256 = <sha256 of server raw BAPI bytes/json artifact>
fixture_sha256 = <sha256 of committed fixture>
parser_version_before = stage1_5d_symbol_extraction_v2
symbol_extraction_version_before = 2
current_parser_output_symbols = []
current_parser_output_symbol_launch_times_ms = {}
```

Fixture requirement:

```text
path = tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json
```

The fixture must preserve enough original structure to independently validate the bug:

```text
JSON node hierarchy
node order
symbol cells/nodes
launch time cells/nodes
launch header
separated schedule block
any duplicated desktop/mobile section if present
disclaimer/footer section if present
```

A pure manually reconstructed text snippet is insufficient for the primary regression test. If a minimized fixture is also added, it must be explicitly labeled:

```json
{
  "data_quality": "manually_minimized_from_real_bapi_payload",
  "source_fixture": "bapi_article_detail_a827_real_frozen_fixture.json"
}
```

## 4. Root Causes

### 4.1 Parser root cause

Current `extract_symbol_candidates_from_bapi_article_payload()` works on local text segments and requires the same segment/window to contain both launch context and symbol. A827 places context, time, symbol and contract label across separated lines or table-like cells:

```text
Binance Futures will launch the following perpetual contract(s) as below:
2026-07-27 13:30 (UTC):
TMFUSDT
Perpetual Contract
2026-07-27 13:35 (UTC):
TBTUSDT
Perpetual Contract
2026-07-27 13:40 (UTC):
BITOUSDT
Perpetual Contract
```

It also contains table-like content:

```text
USDⓈ-M Perpetual Contract
TMFUSDT
TBTUSDT
BITOUSDT
Launch Time
2026-07-27 13:30 (UTC)
2026-07-27 13:35 (UTC)
2026-07-27 13:40 (UTC)
```

The parser excludes symbol-only nodes such as `TMFUSDT`, so BAPI success becomes parser no-match.

### 4.2 Diagnostic masking root cause

After BAPI trusted parser no-match, runner falls back to support detail. Support detail returns `HTTP 202 empty`, and scheduler state ends with:

```text
last_detail_failure_class = http_202_empty
```

This masks the true earlier state:

```text
last_bapi_detail_status = success
last_bapi_parser_status = no_symbols
```

### 4.3 Runtime gate root cause

`binance_futures_launch_smoke_summary.json` currently mixes two incompatible meanings:

```text
1. final 1.5D smoke/research summary written at runner end
2. live startup gate consumed by 1.5F before observing depth
```

For a 7d continuous runner, final summary may be absent until the process ends. A separate runtime gate is required.

## 5. Design Goals

### 5.1 Parser goals

```text
1. Parse separated schedule blocks from trusted BAPI article body.
2. Parse table-like launch schedule blocks while preserving node order and provenance.
3. Emit symbols only when launch context is explicit and local enough.
4. Emit per-symbol launch times only when mapping is unambiguous.
5. Keep all symbols subject to exchangeInfo validation.
6. Enforce article-level all-or-none for multi-symbol events across all paths.
7. Forbid article releaseDate / legacy max-age fallback as clean launch anchor for BAPI multi-contract schedules.
8. Preserve BAPI parser diagnostics even if later support fallback returns 202.
9. Avoid high-frequency repeated parsing of identical BAPI no-match payloads.
```

### 5.2 Runtime gate goals

```text
1. 1.5D writes a dedicated current-root runtime gate file.
2. 1.5F validates the runtime gate with a dedicated allowlist validator.
3. Runtime gate is same-root bound to --stage1-5d-events-glob.
4. Runtime gate has explicit lifecycle states and freshness checks.
5. Gate stale/degraded blocks new event admission only; existing active depth observations continue.
6. Historical baseline summary override remains possible only through an explicit emergency flag and reason.
```

## 6. Non-Goals

```text
1. No trade signal, paper trading, live trading, private API, order placement or execution engine.
2. No change to 1.5G thresholds.
3. No retroactive promotion of A827 to clean evidence.
4. No deletion of support fallback.
5. No exchangeInfo delta derived candidate path in this hotfix.
6. No full table semantic engine beyond the minimum needed to parse real Binance launch schedule structures safely.
```

## 7. Parser Design

### 7.1 Versioning

This is an observable semantic parser change. Update versions:

```text
PARSER_VERSION = stage1_5d_symbol_extraction_v3
SYMBOL_EXTRACTION_VERSION = 3
launch_schedule_parser_version = stage1_5d_bapi_launch_schedule_v1
```

Record these in:

```text
event rows
scheduler state
request manifest rows
diagnostics
raw fixture metadata
```

### 7.2 Text/node extraction model

The BAPI parser must output internal structured candidates, not only final symbols:

```text
extracted_text
logical_lines[]
text_nodes[] with node_path, text, normalized_text, order_index
candidate_provenance[]
```

A logical line means a non-empty normalized line after HTML unescape, Unicode normalization and whitespace collapse. `N` lookahead values apply to logical lines, not raw blank-separated lines.

### 7.3 Candidate sources

The parser should collect candidates from multiple methods before reconciling:

```text
existing_segment_candidates
separated_schedule_candidates
table_structure_candidates
```

Do not stop after the old segment parser finds symbols, because it may find symbols without reliable launch times.

### 7.4 Separated schedule extraction

Recognize local blocks:

```text
<YYYY-MM-DD HH:MM (UTC)>:
<SYMBOL>
Perpetual Contract
```

Rules:

```text
1. Time line must include explicit UTC.
2. Symbol must appear within EXTERNAL_SIGNAL_STAGE1_5D_BAPI_SCHEDULE_LINE_LOOKAHEAD logical lines after the time line.
3. Contract label must appear within the same local launch block.
4. Provenance records time_node_path, symbol_node_path, contract_context_node_path, raw_time_text, timezone_text and parser_method.
5. Candidate limit exceeded => candidate_limit_exceeded diagnostic and consumable_event_allowed = false.
```

### 7.5 Table-like launch schedule extraction

Recognize blocks containing:

```text
USDⓈ-M Perpetual Contract
<symbol list>
Launch Time
<time list>
```

Minimum safe pairing conditions:

```text
same logical launch block
unique symbol set
unique time list
symbol_count == time_count
explicit UTC on every time
monotonic non-decreasing time order
no duplicate desktop/mobile ambiguity unless duplicate blocks are byte/text-equivalent
no disclaimer/footer contamination
```

When conditions fail:

```text
parser_status = launch_schedule_ambiguous | launch_time_missing | candidate_limit_exceeded
consumable_event_allowed = false
no event row emitted
no article_release_date fallback
no legacy_max_age fallback
```

### 7.6 Reconciliation

Reconcile all candidate sources into:

```json
{
  "symbols": ["TMFUSDT", "TBTUSDT", "BITOUSDT"],
  "symbol_launch_times_ms": {
    "TMFUSDT": 1785159000000,
    "TBTUSDT": 1785159300000,
    "BITOUSDT": 1785159600000
  },
  "symbol_launch_time_candidates_ms": {},
  "launch_time_resolution_status": "resolved",
  "launch_time_conflict_ms": 0,
  "candidate_provenance": []
}
```

Conflict rules:

```text
same symbol and all candidate times agree within EXTERNAL_SIGNAL_STAGE1_5D_MAX_LAUNCH_TIME_DISAGREEMENT_MS:
  select time and record all candidate methods

candidate times disagree beyond threshold:
  parser_status = launch_time_conflict
  consumable_event_allowed = false

symbols found but no reliable per-symbol launch time and no exchangeInfo onboardDate:
  parser_status = launch_time_missing
  consumable_event_allowed = false
```

### 7.7 Context filtering

Do not use global full-text symbol regex as a consumable source. Extraction must be bounded to launch blocks.

Allowed context examples:

```text
will launch
following perpetual contract(s)
USDⓈ-M Perpetual Contract
Launch Time
Perpetual Contract
```

Blocked context examples:

```text
risk warning
disclaimer
terms and conditions
related articles
footer
```

If one large node contains both launch section and disclaimer, split into logical blocks and only parse the launch block.

## 8. Output Contract

For A827 real frozen fixture, expected parser output after this hotfix:

```json
{
  "symbols": ["TMFUSDT", "TBTUSDT", "BITOUSDT"],
  "symbol_parse_status": "parsed",
  "symbol_parse_confidence": "exact_article_text",
  "symbol_validation_status": "unverified",
  "symbol_extraction_source": "bapi_article_body",
  "symbol_derivation_method": "none",
  "detail_transport": "bapi_article_detail_query",
  "launch_schedule_parser_version": "stage1_5d_bapi_launch_schedule_v1",
  "launch_time_resolution_status": "resolved",
  "symbol_launch_times_ms": {
    "TMFUSDT": 1785159000000,
    "TBTUSDT": 1785159300000,
    "BITOUSDT": 1785159600000
  }
}
```

After exchangeInfo all-or-none validation, event row must include:

```text
symbols = [TMFUSDT, TBTUSDT, BITOUSDT]
symbol_validation_status = validated_by_exchangeinfo
symbol_launch_times_ms populated for all symbols
symbol_effective_launch_times_ms populated for all symbols
launch_time_source = detail | exchange_info | mixed_detail_exchange_info
detail_fetch_status = success
detail_fetch_variant = bapi_article_detail_query
detail_payload_trusted = true
content_provenance = binance_official_announcement
source_transport = binance_first_party_public_web_bapi_undocumented
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

## 9. Multi-Symbol All-Or-None Contract

First version uses article-level all-or-none for multi-symbol BAPI launch articles.

Emit condition:

```text
candidate_count > 0
validated_count == candidate_count
pending_count == 0
rejected_count == 0
per-symbol launch anchor is available for every candidate from detail parser or exchangeInfo onboardDate
```

Non-emit conditions:

```text
only subset validated
any symbol pending exchangeInfo
any symbol rejected by exchangeInfo
candidate_limit_exceeded
launch time missing/conflict/ambiguous
timezone missing
```

Non-emit behavior:

```text
retain complete candidate_symbols
retain parsed_candidate_symbols
retain per-symbol validation state
retain per-symbol launch time candidate diagnostics
continue pending/retry according to exchangeInfo validation state machine
do not pop article scheduler state
do not write partial event row
```

This contract applies to:

```text
first BAPI parse path
pending exchangeInfo revalidation path
restart recovery path
manual replay path if added later
```

## 10. Launch Anchor Safety Contract

For BAPI multi-contract schedule articles, `article_releaseDate` and legacy max-age fallback are forbidden as consumable launch anchors.

Allowed effective launch anchor sources:

```text
parsed per-symbol launch time from trusted article body
validated exchangeInfo onboardDate
```

Forbidden for clean/recovery admission:

```text
article releaseDate as launch time
first_detected_at_ms + detail_fetch_max_age as launch time
synthetic launch time inferred from parser timeout
truncated candidate set
ambiguous table ordering
```

If no safe anchor exists:

```text
symbol_parse_status = parsed
launch_time_resolution_status = unresolved
consumable_event_allowed = false
scheduler/audit diagnostic only
no 1.5F consumable event row
```

## 11. Scheduler and Diagnostics

Persist source-specific BAPI parser state so support fallback 202 cannot hide root cause:

```text
last_bapi_detail_status = success | failure | not_attempted
last_bapi_payload_hash
last_bapi_parser_version
last_bapi_parser_status = parsed | no_symbols | launch_time_missing | launch_schedule_ambiguous | launch_time_conflict | candidate_limit_exceeded | schema_drift
last_bapi_parser_failure_reason
last_bapi_parse_attempt_at_ms
last_support_detail_status
last_support_failure_class
bapi_parser_no_symbol_count
bapi_parser_table_schedule_success_count
bapi_parser_separated_schedule_success_count
bapi_parser_launch_time_missing_count
bapi_parser_conflict_count
bapi_to_support_fallback_count
bapi_trusted_parser_no_match_to_support_fallback_count
```

No-match dedup rule:

```text
same articleCode
same last_bapi_payload_hash
same last_bapi_parser_version
last_bapi_parser_status = no_symbols
```

Under this condition, do not high-frequency re-fetch/re-parse BAPI on every normal retry cycle. Re-attempt is allowed only when:

```text
payload revision hash changes
parser version changes
low-frequency schema drift recheck is due
operator explicit replay is invoked
```

Support fallback remains allowed but bounded and must record:

```text
fallback_reason = bapi_trusted_parser_no_match
```

All new state fields must survive serializer round-trip and restart.

## 12. Dedicated Stage 1.5D Runtime Gate

### 12.1 File and CLI contract

Add a separate current-root artifact:

```text
$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json
```

Add a dedicated 1.5F CLI:

```text
--stage1-5d-runtime-gate "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json"
```

Keep existing `--stage1-5d-summary` for final historical smoke summaries only. It must not silently act as a runtime gate.

Emergency legacy override requires explicit flags:

```text
--allow-historical-stage1-5d-safety-gate
--historical-stage1-5d-gate-reason "<operator reason>"
```

When override is used, 1.5F summary must record:

```text
stage1_5d_gate_mode = historical_baseline_safety_gate
cross_root_upstream_summary_dependency = true
historical_stage1_5d_gate_reason = <reason>
```

### 12.2 Runtime gate state machine

Allowed decisions:

```text
stage1_5d_runtime_gate_initializing
stage1_5d_runtime_gate_ready
stage1_5d_runtime_gate_degraded
stage1_5d_runtime_gate_stopped
stage1_5d_runtime_gate_failed
```

Only this decision allows new 1.5F event admission:

```text
stage1_5d_runtime_gate_ready
```

Lifecycle:

```text
INITIALIZING:
  runner started
  upstream evidence or first poll not yet complete
  block new 1.5F admission

READY:
  upstream evidence valid
  at least one successful poll
  heartbeat persisted
  live_public_readonly = true
  all safety flags false
  allow new 1.5F admission

DEGRADED:
  runner alive but source unhealthy or consecutive poll failures exceed threshold
  block new 1.5F admission
  existing active observations continue

STOPPED:
  runner ended normally
  block new 1.5F admission
  existing active observations continue until terminal

FAILED:
  fatal blocker or corrupt state
  block new 1.5F admission
  existing active observations continue only if their own data path remains healthy
```

### 12.3 Runtime gate required fields

```json
{
  "runtime_gate_schema_version": 1,
  "decision": "stage1_5d_runtime_gate_ready",
  "source_root": "<canonical current 1.5D output root>",
  "run_id": "<derived from root or explicit>",
  "events_stream_relative_path": "events/*.jsonl",
  "runner_started_at_ms": 0,
  "generated_at_ms": 0,
  "last_heartbeat_at_ms": 0,
  "last_successful_poll_at_ms": 0,
  "poll_count": 0,
  "successful_poll_count": 0,
  "consecutive_poll_failure_count": 0,
  "upstream_evidence_valid": false,
  "fixture_run": false,
  "live_public_readonly": true,
  "fatal_blockers": [],
  "trade_signal_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "alpha_interpretation_allowed": false,
  "execution_feasibility_claim_allowed": false
}
```

For `poll_count = 0`, success-rate fields must be `null` or absent. Do not emit `request_success_rate = 1.0` with no denominator.

### 12.4 Atomic write

Runtime gate writes must be atomic:

```text
write same-directory temp file
flush/fsync if available
os.replace(temp, live_safety_gate_summary.json)
```

1.5F must reject truncated/corrupt JSON as gate invalid and emit diagnostic.

### 12.5 Dedicated validator

Add a dedicated validator:

```text
validate_stage1_5d_runtime_gate(gate_path, expected_events_glob, now_ms)
```

Validation must require:

```text
runtime_gate_schema_version == 1
decision == stage1_5d_runtime_gate_ready
source_root canonical equals root derived from --stage1-5d-events-glob
events_stream_relative_path matches the events glob suffix
fixture_run is false
live_public_readonly is true
upstream_evidence_valid is true
poll_count >= 1
successful_poll_count >= 1
last_heartbeat_at_ms > 0
last_successful_poll_at_ms > 0
generated_at_ms freshness <= EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_STALENESS_SEC
consecutive_poll_failure_count <= EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_CONSECUTIVE_FAILURES
all safety flags exactly false and present
fatal_blockers == []
```

Unknown decision values must fail closed.

### 12.6 Periodic 1.5F revalidation

1.5F must revalidate runtime gate at startup and periodically during the poll loop.

Config:

```text
EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_STALENESS_SEC
EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_REVALIDATION_INTERVAL_SEC
EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_CONSECUTIVE_FAILURES
```

When runtime gate is stale/degraded/invalid:

```text
block_new_event_admission = true
continue_existing_active_depth_observations = true
do_not_delete_pending_state = true
emit_runtime_gate_diagnostic = true
```

This prevents upstream failure from creating new blind observations while preserving already-started 12h evidence windows.

## 13. A827 Evidence Boundary

A827 must not be used as clean evidence after this hotfix.

Known times:

```text
earliest_launch_utc = 2026-07-27T13:30:00Z
manual diagnosis time ~= 2026-07-27T15:11:03Z
```

Expected outcomes:

```text
Scenario A: A827 already existed before a new 1.5F root bootstrap
expected = ignored_historical_anchor_pre_bootstrap
clean_start = false
recovery_start = false
no depth clean claim

Scenario B: existing 1.5F root receives late-resolved A827 after bootstrap but beyond recovery start window
expected = rejected_launch_anchor_age_exceeded
clean_start = false
recovery_start = false
no depth clean claim
```

A827 is mandatory as parser regression fixture, but optional as live production recovery evidence because the announcement list may no longer expose it in the current polling window.

## 14. Tests Required Before Implementation Completion

### 14.1 Preflight fixture tests

```text
test_a827_real_frozen_fixture_hash_matches_expected
test_a827_current_v2_parser_reproduces_no_symbols_before_hotfix
```

### 14.2 Parser unit tests

```text
test_bapi_separated_launch_schedule_extracts_a827_symbols_and_launch_times
test_bapi_table_launch_schedule_extracts_symbol_time_pairs
test_bapi_table_launch_schedule_symbol_time_count_mismatch_is_diagnostic
test_bapi_table_parser_does_not_capture_disclaimer_symbols
test_bapi_duplicate_mobile_desktop_equivalent_blocks_dedupes_safely
test_bapi_duplicate_conflicting_blocks_fail_closed
test_bapi_existing_f434_d0833_6cbb_fixtures_still_pass
test_parser_versions_increment_to_v3
```

### 14.3 Runner parser integration tests

```text
test_a827_bapi_table_article_emits_consumable_multi_symbol_event_after_all_exchangeinfo_validation
test_multi_symbol_one_of_three_validated_does_not_emit_partial_event
test_multi_symbol_pending_state_preserves_all_candidates
test_multi_symbol_all_three_later_validate_emits_once
test_multi_symbol_restart_does_not_duplicate_or_drop_symbols
test_bapi_parser_no_symbol_preserves_bapi_diagnostic_even_if_support_fallback_202
test_bapi_success_does_not_continue_to_support_fallback_after_symbols_parsed
test_bapi_same_hash_same_parser_no_symbols_dedupes_high_frequency_retry
test_bapi_parser_version_change_allows_reparse_of_same_payload_hash
test_bapi_multi_contract_missing_launch_time_does_not_use_article_release_date_anchor
test_bapi_multi_contract_missing_launch_time_does_not_use_legacy_max_age_anchor
```

### 14.4 A827 late evidence boundary tests

```text
test_a827_pre_bootstrap_late_fixture_is_ignored_historical_anchor_pre_bootstrap
test_a827_post_bootstrap_late_resolved_fixture_is_rejected_launch_anchor_age_exceeded
test_a827_late_fixture_never_marks_clean_or_recovery_start
```

### 14.5 Runtime gate tests

```text
test_stage1_5d_continuous_writes_runtime_gate_initializing_at_startup
test_stage1_5d_runtime_gate_becomes_ready_after_first_successful_poll
test_stage1_5d_runtime_gate_atomic_write_rejects_truncated_json
test_stage1_5f_accepts_ready_runtime_gate_same_root
test_stage1_5f_rejects_runtime_gate_unknown_decision
test_stage1_5f_rejects_runtime_gate_initializing_degraded_stopped_failed
test_stage1_5f_rejects_runtime_gate_if_any_safety_field_missing_or_true
test_stage1_5f_rejects_runtime_gate_if_source_root_mismatch_events_glob
test_stage1_5f_rejects_runtime_gate_if_stale
test_stage1_5f_periodic_gate_revalidation_blocks_new_admission_but_continues_active_observation
test_historical_summary_override_requires_explicit_flag_and_reason
test_stage1_5d_final_smoke_summary_path_remains_available_after_runner_exit
```

## 15. Deployment Order

Required deployment sequence:

```text
1. Deploy Task A code to server and start a new 1.5D root.
2. Verify A827 frozen fixture parser tests locally before deployment.
3. Start new 1.5D root; it writes INITIALIZING runtime gate.
4. Verify upstream evidence and first successful poll.
5. Confirm runtime gate transitions to READY.
6. Bootstrap a new 1.5F root.
7. Start 1.5F with --stage1-5d-runtime-gate pointing to the same current 1.5D root.
8. Verify root equality, gate freshness, and periodic revalidation diagnostics.
```

A827 live recovery is not a mandatory production acceptance criterion. Mandatory acceptance criteria are:

```text
A827 real frozen fixture parser regression passes
runtime gate same-root/freshness tests pass
new 1.5D root emits READY runtime gate after first successful poll
new 1.5F root accepts only same-root READY runtime gate
next fresh table-structured Binance announcement reaches 1.5F pending/accepted according to launch gate rules
```

## 16. Production Verification Commands

After deployment, verify current-root binding:

```bash
python3 - <<'PY'
import json, pathlib, os
stage1_5d = pathlib.Path(os.environ['STAGE1_5D_EVENTS_OUT']).resolve()
stage1_5f = pathlib.Path(os.environ['STAGE1_5F_OUT']).resolve()
gate = json.loads((stage1_5d / 'live_safety_gate_summary.json').read_text())
summary = json.loads((stage1_5f / 'live_depth_observer_summary.json').read_text())
print({
    'gate_decision': gate.get('decision'),
    'gate_source_root': gate.get('source_root'),
    'stage1_5d_root': str(stage1_5d),
    'same_root_gate': pathlib.Path(gate.get('source_root', '')).resolve() == stage1_5d,
    'stage1_5d_gate_mode': summary.get('stage1_5d_gate_mode'),
    'cross_root_upstream_summary_dependency': summary.get('cross_root_upstream_summary_dependency'),
})
PY
```

Verify A827 parser fixture locally:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  -k 'a827 or bapi_table or launch_schedule' -q
```

Verify no unsafe permissions:

```bash
rg -n \
'paper_trading_allowed\s*[:=]\s*True|live_trading_allowed\s*[:=]\s*True|execution_engine_allowed\s*[:=]\s*True|trade_signal_allowed\s*[:=]\s*True' \
configs src scripts
```

Expected result: no production code match.

## 17. Rollback

Parser rollback:

```text
Revert Task A commit only.
BAPI transport and support fallback remain.
Risk: future table/list launch schedule articles may again be missed.
```

Runtime gate rollback:

```text
Revert Task B commit only.
1.5F may temporarily use historical baseline summary only with explicit override flag and documented reason.
Risk: cross-root safety gate dependency returns, but no trading/execution permissions are opened.
```

Old roots remain read-only. Do not rewrite old 1.5D/1.5F/1.5G evidence to make A827 look clean.
