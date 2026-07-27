# Stage 1.5D BAPI Table Launch Schedule Parser and Live Gate Summary Hotfix Design

```text
status = design_draft
scope = stage1_5d_bapi_table_launch_schedule_parser_hotfix_plus_live_gate_summary
primary_fix = bapi_article_body_table_aware_symbol_and_launch_time_extraction
companion_fix = running_live_safety_gate_summary_for_stage1_5f_startup
implementation_allowed = false
implementation_plan_allowed = after_design_review_only
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

不能称为官方稳定 API、documented API 或受 Binance 明确承诺的 public API。

2026-07-27 新公告暴露出新的 parser 缺口：BAPI detail 请求已经成功，payload 也被判定为 trusted，但 parser 仍返回 `symbols=[]`，导致 1.5D 未 emit consumable event，1.5F 没有进入 accepted/rejected/pending state。

同时，运维过程中还暴露出另一个 Stage 1.5D -> Stage 1.5F 接口缺口：1.5D continuous runner 当前通常在 7d runner 结束时才写 `binance_futures_launch_smoke_summary.json`，但 1.5F 启动时必须读取 `--stage1-5d-summary` 作为 safety gate。二者生命周期不匹配，导致当前 1.5F 只能接入旧 root 的 baseline summary。

本 design 将二者放在同一份 hotfix 中描述，但实施上必须拆成两个独立任务：

```text
Task A: BAPI table/list launch schedule parser hotfix
Task B: Stage 1.5D running live safety gate summary hotfix
```

## 2. 触发证据

### 2.1 新公告事实

```text
articleCode = a827177a387e4ebea830110ba222ca48
title = Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-27)
list_releaseDate_ms = 1785143762441
list_release_utc = 2026-07-27T09:16:02.441Z
expected_symbols = TMFUSDT, TBTUSDT, BITOUSDT
expected_launch_times_utc = 2026-07-27T13:30:00Z, 2026-07-27T13:35:00Z, 2026-07-27T13:40:00Z
```

Server-side Stage 1.5D evidence:

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

Raw BAPI payload files exist under:

```text
raw_payloads/announcement_detail/a827177a387e4ebea830110ba222ca48/*.bapi_article_detail_query.*.json
```

Parser reproduction from saved BAPI payload:

```json
{
  "symbols": [],
  "symbol_launch_times_ms": {},
  "symbol_extraction_source": "none",
  "extracted_text_prefix": "... Binance Futures will launch the following perpetual contract(s) as below:\n2026-07-27 13:30 (UTC):\nTMFUSDT\n Perpetual Contract\n2026-07-27 13:35 (UTC):\nTBTUSDT\n Perpetual Contract\n2026-07-27 13:40 (UTC):\nBITOUSDT\n Perpetual Contract ..."
}
```

因此根因不在 network、BAPI health、HTTP 202 retry scheduler 或 1.5F admission。根因在 BAPI body parser。

### 2.2 Live gate summary 接口事实

1.5D 当前启动命令显式传入：

```text
--output-summary data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix/binance_futures_launch_smoke_summary.json
--max-seconds 604800
```

但运行中检查：

```text
ls: cannot access .../binance_futures_launch_smoke_summary.json: No such file or directory
```

代码中 summary 写入位于 runner 收尾阶段：

```text
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
-> build_smoke_summary(...)
-> json.dump(summary, output_summary_path)
```

这意味着：7d continuous runner 运行中，current root 可能没有 `binance_futures_launch_smoke_summary.json`。

1.5F 启动时会强制校验 `--stage1-5d-summary`：

```text
validate_stage1_5d_summary(args.stage1_5d_summary)
```

校验字段包括：

```text
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
trade_signal_allowed = false
```

当前线上为让 1.5F 启动，只能使用旧 baseline summary：

```text
--stage1-5d-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json
```

这不是 1.5F 主逻辑 bug，但会造成 cross-root evidence dependency：

```text
1.5F event rows input = current 20260724 1.5D root
1.5F safety gate summary = historical 20260627 1.5D root
```

该状态可临时接受，但不应长期保留。

## 3. 根因

### 3.1 Parser 根因

当前 `extract_symbol_candidates_from_bapi_article_payload()` 对 BAPI body 的处理以 text node / segment 为局部单位，并要求同一 segment 同时包含：

```text
launch / will launch / perpetual contract / USDⓈ-margined 等上下文
和
XXXUSDT / XXXUSDC / XXXUSD1 symbol
```

但 `a827...` 公告结构为：

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

也包含 table-like block：

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

symbol、launch time、context 位于不同 text nodes / lines / table cells。当前 parser 的局部上下文过滤会把 `TMFUSDT` 这种单独 symbol line 排除。

### 3.2 State/diagnostic 掩盖根因

BAPI success 后 parser 未产出 symbols，runner 继续 fallback 到 support detail URL；support detail 返回 `HTTP 202 empty`，最后 scheduler state 显示：

```text
last_detail_failure_class = http_202_empty
```

这容易误导排查方向，使人以为仍是 202/retry 问题。实际上 BAPI source health 已连续 success。

### 3.3 Live gate summary 根因

`binance_futures_launch_smoke_summary.json` 同时承担了两个不同语义：

```text
1. 结束后 smoke/review summary，总结 1.5D 运行结果。
2. 1.5F 启动前 safety gate artifact，证明 1.5D 上游不会打开交易/执行/信号权限。
```

对于 short smoke run，这两个语义可以共用一个文件。对于 7d continuous run，它们不应继续共用同一个“结束后才写”的 summary。

## 4. 设计目标

### 4.1 Parser hotfix 目标

```text
1. 从 BAPI trusted body 的 full extracted text 中识别 separated launch schedule block。
2. 支持 date/time line -> symbol line -> perpetual contract line 的结构。
3. 支持 table-like block：symbol row/list 与 launch time row/list 分离的结构。
4. 输出完整 symbols 与 per-symbol symbol_launch_times_ms。
5. 所有 symbols 仍必须通过 exchangeInfo validation，不能绕过现有 validation gate。
6. BAPI parser 成功后不得继续 fallback 到 support detail。
7. BAPI parser 失败时必须输出明确 parse failure diagnostic，不能只被后续 support 202 掩盖。
8. 不回填旧事件为 formal 1.5F clean evidence。
```

### 4.2 Live safety gate summary 目标

```text
1. 1.5D continuous runner 启动后立即写入一个 current-root running safety gate summary。
2. running safety gate summary 必须可被 1.5F validate_stage1_5d_summary 接受。
3. running safety gate summary 必须周期性原子刷新，至少包含 last_heartbeat_at_ms / poll_count / request_success fields。
4. 结束后仍可写完整 binance_futures_launch_smoke_summary.json，不改变最终 review summary 语义。
5. 1.5F 启动时可以接入 current 1.5D root 的 safety gate，不再依赖 historical 20260627 root。
```

## 5. 非目标

```text
1. 不允许任何 trade signal、paper trading、live trading 或 execution engine。
2. 不改变 1.5F watermark / launch gate / terminal hygiene 核心语义。
3. 不改变 1.5G clean/quarantine/invalid 阈值。
4. 不将 a827... 事件补写成 clean evidence；该事件已经错过 clean start window，只能作为 parser regression / recovery evidence。
5. 不删除 support detail fallback；BAPI schema drift 或 source failure 时仍保留 fallback。
6. 不把 exchangeInfo delta 推导等同于 detail-confirmed event。
7. 不把 BAPI transport 描述为 official supported API。
```

## 6. Parser 设计

### 6.1 输入与保留不变量

输入仍为 BAPI article detail payload：

```text
payload.data.body / payload.data.contentJson
```

必须继续保留现有安全边界：

```text
MAX_RESPONSE_BYTES
MAX_JSON_DEPTH
MAX_NODE_COUNT
MAX_EXTRACTED_TEXT_CHARS
MAX_SYMBOL_CANDIDATES
payload_trusted identity checks
append-only raw payload storage
request_manifest per HTTP request audit row
```

### 6.2 新增 extraction 层级

Parser 应按优先级执行：

```text
1. Existing local segment extraction
2. New separated schedule extraction
3. New table-like launch schedule extraction
4. No symbols -> explicit parser no-match diagnostic
```

#### 6.2.1 Separated schedule extraction

识别如下局部 block：

```text
<YYYY-MM-DD HH:MM (UTC)>:
<SYMBOL>
Perpetual Contract
```

规则：

```text
1. 在 full_extracted_text 中按 line 切分并保留原始顺序。
2. 找到 date/time line 后，在后续 N 行内寻找 1 个 symbol。
3. symbol 后 N 行内必须出现 Perpetual Contract / USDⓈ-M Perpetual Contract / USD-M Perpetual Contract 等合约上下文。
4. 生成 symbol -> nearest preceding date/time。
5. 若 symbol 数超过 max_symbols，截断并输出 truncated diagnostic。
```

`N` 第一版建议为 4 行，配置化为：

```text
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_SCHEDULE_LINE_LOOKAHEAD = 4
```

#### 6.2.2 Table-like launch schedule extraction

识别如下结构：

```text
USDⓈ-M Perpetual Contract
<SYMBOL_1>
<SYMBOL_2>
...
Launch Time
<TIME_1>
<TIME_2>
...
```

规则：

```text
1. 在 launch context block 内寻找 symbol list。
2. 在相同 block 内寻找 Launch Time label 后的 date/time list。
3. 若 symbol_count == time_count，则按顺序配对。
4. 若 symbol_count != time_count，则只输出 symbols，launch_times 进入 partial/missing diagnostic，不得伪造时间。
5. 若存在 separated schedule extraction 的 per-symbol time，则优先使用 separated schedule time。
6. 若 table time 与 separated time 冲突，输出 launch_time_conflict diagnostic，优先选择距离 symbol 最近的 separated schedule time。
```

### 6.3 Context filtering

不能退化成“全文正则抓所有 `XXXUSDT`”。必须保留局部 launch context。

允许 context block：

```text
will launch
following perpetual contract(s)
USDⓈ-M Perpetual Contract
Launch Time
Perpetual Contract
```

禁止 context：

```text
risk warning
disclaimer
terms and conditions
related articles
footer
```

若同一个大 text node 同时包含 launch block 和 disclaimer，必须按 line/window 切分，只在 launch block 内提取 symbol。

## 7. 输出契约

BAPI parser 对 `a827...` 的期望输出：

```json
{
  "symbols": ["TMFUSDT", "TBTUSDT", "BITOUSDT"],
  "symbol_extraction_source": "bapi_article_body",
  "symbol_derivation_method": "none",
  "symbol_validation_status": "validated_by_exact_text",
  "detail_transport": "bapi_article_detail_query",
  "symbol_launch_times_ms": {
    "TMFUSDT": 1785159000000,
    "TBTUSDT": 1785159300000,
    "BITOUSDT": 1785159600000
  },
  "candidate_provenance": [
    {
      "symbol": "TMFUSDT",
      "parser_context": "bapi_separated_launch_schedule",
      "event_phrase_match": true,
      "section_classification": "launch_schedule_block"
    }
  ]
}
```

After exchangeInfo validation, 1.5D event row must include:

```text
symbols = [TMFUSDT, TBTUSDT, BITOUSDT]
symbol_launch_times_ms populated per symbol
symbol_effective_launch_times_ms populated per symbol
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

If parser extracts symbols but exchangeInfo does not yet validate all symbols, existing validation-pending semantics apply. Do not emit incomplete multi-symbol event unless current architecture has explicit per-symbol idempotent emission. First version remains all-or-none for article-level multi-symbol event emission.

## 8. Scheduler and diagnostics updates

BAPI success with parser no-match must not be hidden by later support 202.

Add or persist fields in scheduler state / diagnostic counters:

```text
last_bapi_detail_status = success | failure | not_attempted
last_bapi_parser_status = parsed | no_symbols | launch_time_missing | schema_drift
last_bapi_parser_failure_reason = bapi_launch_schedule_no_symbol_match | null
bapi_parser_no_symbol_count
bapi_parser_table_schedule_success_count
bapi_parser_separated_schedule_success_count
bapi_parser_launch_time_missing_count
bapi_parser_conflict_count
```

Fallback behavior:

```text
BAPI trusted + parser parsed symbols:
  emit or validation-pending; do not support fallback.

BAPI trusted + parser no symbols:
  allow support fallback, but scheduler state must preserve last_bapi_parser_status = no_symbols.

BAPI untrusted / schema drift / identity mismatch:
  existing failure taxonomy and support fallback remain.
```

## 9. Live safety gate summary design

### 9.1 File contract

Add a running summary written inside current 1.5D output root:

```text
live_safety_gate_summary.json
```

The existing final summary path remains:

```text
binance_futures_launch_smoke_summary.json
```

`live_safety_gate_summary.json` must be atomically rewritten at startup and after each poll, or at minimum after each heartbeat write.

Minimum fields:

```json
{
  "decision": "stage1_5d_smoke_running",
  "summary_type": "live_safety_gate",
  "source_root": "<current 1.5D output root>",
  "poll_count": 0,
  "last_heartbeat_at_ms": 0,
  "last_successful_poll_at_ms": 0,
  "request_success_rate": 1.0,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "alpha_interpretation_allowed": false,
  "trade_signal_allowed": false,
  "research_result_valid": false,
  "live_public_readonly": true
}
```

`validate_stage1_5d_summary()` already rejects only `stage1_5d_smoke_invalid` / `stage1_5d_smoke_failed` and unsafe fields. Therefore `decision = stage1_5d_smoke_running` should be accepted if all safety flags remain false.

### 9.2 Deployment wiring

Future 1.5F startup should prefer current root live safety gate:

```bash
--stage1-5d-summary "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json"
```

Fallback to historical baseline summary is allowed only as an explicit emergency override and must be documented:

```text
stage1_5d_summary_mode = historical_baseline_safety_gate
cross_root_upstream_summary_dependency = true
```

### 9.3 Why not overwrite final summary continuously

Do not continuously overwrite `binance_futures_launch_smoke_summary.json` with partial data unless compatibility review confirms all downstream readers can distinguish running summary from final smoke review. Separate `live_safety_gate_summary.json` avoids confusing running safety gate with final evidence summary.

## 10. Evidence boundaries

The `a827...` event should not be retroactively promoted to clean 1.5F evidence after this fix.

Reason:

```text
earliest_launch_utc = 2026-07-27T13:30:00Z
manual diagnosis time ~= 2026-07-27T15:11:03Z
clean start window already likely exceeded
```

Allowed post-fix use:

```text
parser regression fixture
BAPI body schedule extraction test
recovery_validation_only if 1.5F later sees event after clean SLA
```

Disallowed:

```text
manual insertion into events_accepted as clean evidence
backfilled 12h depth clean pass
using current depth to represent missed launch-time depth window
```

## 11. Test plan requirements

### 11.1 Parser unit tests

Required tests:

```text
test_bapi_separated_launch_schedule_extracts_a827_symbols_and_launch_times
test_bapi_table_launch_schedule_extracts_symbol_time_pairs
test_bapi_table_launch_schedule_symbol_time_count_mismatch_is_diagnostic
test_bapi_table_parser_does_not_capture_disclaimer_symbols
test_bapi_existing_f434_d0833_6cbb_fixtures_still_pass
```

Fixtures:

```text
tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_fixture.json
```

The fixture should be a frozen raw BAPI payload or minimally redacted payload preserving the real body/table structure. If manually minimized, it must include metadata:

```json
"data_quality": "manually_minimized_from_real_bapi_payload"
```

### 11.2 Runner integration tests

Required tests:

```text
test_a827_bapi_table_article_emits_consumable_multi_symbol_event_after_exchangeinfo_validation
test_bapi_parser_no_symbol_preserves_bapi_diagnostic_even_if_support_fallback_202
test_bapi_success_does_not_continue_to_support_fallback_after_symbols_parsed
test_a827_late_recovery_event_not_marked_clean_for_stage1_5f
```

### 11.3 Live gate summary tests

Required tests:

```text
test_stage1_5d_continuous_writes_live_safety_gate_summary_at_startup
test_stage1_5d_live_safety_gate_summary_refreshes_after_poll
test_stage1_5f_accepts_current_root_live_safety_gate_summary
test_stage1_5f_rejects_live_safety_gate_summary_if_any_safety_flag_true
test_stage1_5d_final_smoke_summary_path_remains_available_after_runner_exit
```

## 12. Production verification

After deployment, use a new root suffix to keep old artifacts read-only:

```text
1.5D root suffix = 7d_bapi_table_schedule_live_gate_summary_hotfix
1.5F root suffix = 7d_bapi_table_schedule_live_gate_summary_hotfix
```

Minimum production checks:

```bash
export ARTICLE_ID="a827177a387e4ebea830110ba222ca48"
export SYMBOL_RE="TMFUSDT|TBTUSDT|BITOUSDT"

ls -lh "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json"
cat "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" | python3 -m json.tool | grep -E \
"decision|summary_type|source_root|poll_count|last_heartbeat_at_ms|trade_signal_allowed|paper_trading_allowed|live_trading_allowed|execution_engine_allowed|alpha_interpretation_allowed"

find "$STAGE1_5D_EVENTS_OUT/events" -type f 2>/dev/null \
  -exec grep -HIn "$ARTICLE_ID\|TMFUSDT\|TBTUSDT\|BITOUSDT" {} \; | tail -n 80 || true

find "$STAGE1_5F_OUT/observer_state.jsonl" -type f 2>/dev/null \
  -exec grep -HIn "$ARTICLE_ID\|TMFUSDT\|TBTUSDT\|BITOUSDT" {} \; | tail -n 80 || true
```

Expected parser regression result:

```text
A827 payload parser returns all 3 symbols and all 3 launch times.
```

Expected production behavior for old missed A827 event:

```text
not clean evidence
possibly rejected/recovery-only depending 1.5F launch gate age rules
```

Expected behavior for next fresh matching announcement:

```text
1.5D emits event row with symbols + launch times.
1.5F either pending_launch_time_in_future or starts after anchor.
No pre-launch depth requests.
No trade/paper/live/execution flags.
```

## 13. Rollback

Parser rollback:

```text
Revert parser extraction additions; BAPI trusted payload storage and existing fallback remain.
Risk = multi-contract table events may again be missed, but safety flags remain false.
```

Live gate summary rollback:

```text
1.5F can temporarily use historical baseline stage1_5d_summary again.
Must document cross_root_upstream_summary_dependency = true.
```

No rollback path may enable private API, paper trading, live trading, execution engine, or alpha interpretation.
