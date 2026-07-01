# Stage 1.5D Multiple TradFi Symbol Extraction Design

## Decision

```text
decision = revised_for_review
scope = stage1_5d_parser_enhancement_only
target_issue = Multiple USDⓈ-Margined TradFi Perpetual Contracts symbols=[]
blocking_current_1_5d_1_5f = false
server_deployment_required_immediately = false
```

本设计只修复 Stage 1.5D live event-source collector 的一个 `false_negative`：部分 Binance Futures `Multiple USDⓈ-Margined TradFi Perpetual Contracts` 公告标题本身不包含具体 `XXXUSDT` / `XXXUSDC`，当前 parser 只能从 title 抽 symbol，因此会输出 `symbols=[]`，导致 Stage 1.5F 不会对这些 event-symbol 启动 12h live depth observation。

本设计不改变任何交易、安全或研究结论边界：

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

## Review Feedback Disposition

本轮设计审查的 6 条必须修正项全部采纳。

```text
1. detail payload persistence = required
2. diagnostic fields = mandatory for every futures_contract_launch row
3. transient detail failure must remain retryable and must not be swallowed by dedupe
4. detail URL allowlist = hard safety gate
5. detail summary counters = required
6. detail fallback configs = formal configs/base.py constants
```

采纳理由：这 6 条都直接影响可审计性、重试语义或安全边界，不属于过度工程。尤其是第 3 条，如果不处理，第一次 detail fetch 失败后文章可能被 dedupe 永久标记为已处理，修复会失去实际作用。

## Background

当前 Stage 1.5D parser 的 symbol extraction 逻辑位于：

```text
src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py
```

核心行为：

```python
def extract_futures_launch_symbols(title: str) -> list[str]:
    matches = re.findall(r"\b([A-Z0-9]+USDT|[A-Z0-9]+USDC)\b", title)
    return list(dict.fromkeys(matches))
```

该逻辑对普通标题有效：

```text
Binance Futures Will Launch USDⓈ-Margined CAPUSDT Perpetual Contract
=> symbols = ["CAPUSDT"]
```

但对以下标题无效：

```text
Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts
=> symbols = []
```

原因是具体合约名称通常在 announcement detail body/table 中，而不是 list title 中。

## Problem Statement

当前问题不是错误采集，而是漏采：

```text
failure_mode = false_negative
effect = Stage 1.5D 识别出 futures_contract_launch 文章，但 symbols=[]
downstream_effect = Stage 1.5F 没有 event-symbol，无法启动 live depth observation
```

这不会导致交易风险，因为 Stage 1.5D / 1.5F 均不允许交易、paper 或 execution。但它会降低 live depth evidence 的覆盖率，尤其是多合约 TradFi launch 事件。

## Design Goals

```text
1. Preserve existing title-only parser behavior for normal single/multi-symbol titles.
2. Add a bounded detail extraction path only when title extraction returns empty for a futures launch article.
3. Extract XXXUSDT / XXXUSDC symbols from persisted article detail payload/body/table.
4. Persist detail payload and record detail request audit evidence in request_manifest.
5. Never crash the poll loop if detail fetch or detail parsing fails.
6. Keep all outputs explicit: parsed, pending_retry, terminal_failed, detail_fetch_failed, detail_parse_failed.
7. Keep transient detail failures retryable; do not let dedupe permanently swallow them.
8. Do not reinterpret this as alpha, execution feasibility, or trading readiness.
```

## Non-Goals

```text
1. Do not backfill historical 1.5F live depth evidence from old events.
2. Do not use current order book to prove old 12h entry feasibility.
3. Do not change Stage 1.5F watermark semantics.
4. Do not change Stage 1.5C / 1.5E research decisions.
5. Do not add private endpoints, API keys, account endpoints, order endpoints, or websocket trading paths.
6. Do not make paper/live/execution/alpha claims.
```

## Options Considered

### Option A: Title-Only Parser, No Change

Keep current behavior and accept `symbols=[]` for `Multiple TradFi` titles.

Pros:

```text
1. No code change.
2. No additional network request.
3. No new schema drift surface.
```

Cons:

```text
1. Continues to miss multi-symbol TradFi futures launch events.
2. Makes Stage 1.5F event-symbol coverage incomplete.
3. Makes "no new accepted event" harder to interpret because some launches may exist but remain symbol-empty.
```

Decision: rejected. The current `false_negative` is already observed and easy to test.

### Option B: Regex Guess From Title

Infer TradFi symbols from human words in title or fixed mapping.

Pros:

```text
1. No detail request.
2. Simple implementation.
```

Cons:

```text
1. Fragile and unsafe.
2. Requires maintaining ad hoc mappings.
3. Can create wrong symbols and wrong depth observation targets.
```

Decision: rejected. Wrong symbol extraction is worse than no symbol extraction.

### Option C: Detail-Only Fallback Extraction

Keep title regex as primary path. If `event_type=futures_contract_launch` and `symbols=[]`, fetch the Binance article detail payload/page and extract `XXXUSDT` / `XXXUSDC` from structured body/text.

Pros:

```text
1. Minimal blast radius.
2. Preserves existing normal path.
3. Fixes observed false-negative.
4. Keeps request audit trail and payload evidence explicit.
5. Allows transient failures to retry instead of becoming permanent misses.
```

Cons:

```text
1. Adds bounded public-readonly detail request.
2. Requires parser to tolerate detail schema drift.
3. Requires payload storage and retry state.
4. May still fail if Binance renders detail content differently.
```

Decision: recommended.

## Proposed Architecture

Add a small detail extraction path behind the existing parser:

```text
announcement list payload
  -> parse articles
  -> classify_event_type(title)
  -> extract symbols from title
  -> if symbols found: current normalize_live_event path with title diagnostics
  -> if symbols empty and title/detail_url eligible:
       validate detail URL hard safety gate
       fetch article detail via public-readonly client
       persist raw detail payload under raw_payloads/announcement_detail
       parse detail body/table/text
       extract XXXUSDT / XXXUSDC
       normalize event with extracted symbols and mandatory diagnostics
       record detail manifest row with payload hash/version fields
  -> if transient detail failure:
       keep pending_retry state and allow later poll retry
  -> if terminal detail failure:
       emit explicit symbol_parse_failed_reason
```

The title parser remains the source of truth for ordinary cases. The detail fallback only activates when all of these are true:

```text
event_type == futures_contract_launch
extract_futures_launch_symbols(title) == []
source_article_id/code is present
source_detail_url_normalized is allowlisted Binance support URL
live_public_readonly == true OR fixture/mock detail payload is provided
```

Fixture mode must not call live network. In fixture mode, tests should pass detail content through fixture data or a mock response layer.

## Detail Extraction Rules

The detail parser should accept a conservative set of inputs:

```text
1. dict payload containing nested strings/lists/dicts
2. raw html/text string
3. table-like fields containing contract names
```

Extraction rule:

```text
regex = \b([A-Z0-9]{2,30}USDT|[A-Z0-9]{2,30}USDC)\b
dedupe = preserve first occurrence order
max_symbols_per_article = configured cap
```

Required config in `configs/base.py`:

```text
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS = 30
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL = 3
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_REQUEST_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES = 3
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC = 3600
```

The cap prevents malformed pages from producing huge symbol lists. Retry and max-age constants make transient failure handling auditable instead of hidden in implementation details.

## Detail URL Safety Gate

Detail fallback introduces an outbound URL fetch path, so URL validation is a hard safety gate.

Required rules:

```text
scheme == https
host in exact_allowlist or configured suffix allowlist already used by Stage 1.5D
path/query matches Binance announcement/detail support endpoints
redirect final_url must be revalidated against the same allowlist
file:// is rejected
localhost is rejected
127.0.0.1 / ::1 is rejected
private IP ranges are rejected
non-https URLs are rejected
missing URL does not crash and marks detail_fetch_status = url_missing
```

This is not primarily capital risk, but it prevents SSRF-style drift where the collector is coerced into fetching non-research URLs.

## Event Output Changes

Existing fields remain unchanged:

```text
event_id
event_type
title
symbols
base_assets
source_article_id
source_detail_url_normalized
stable_event_key
safety flags
```

Add mandatory diagnostic fields for every `futures_contract_launch` event row:

```json
{
  "symbol_extraction_source": "title|detail|none",
  "detail_fetch_attempted": false,
  "detail_fetch_status": "not_needed|success|network_error|schema_drift|parse_failed|fixture_missing|budget_deferred|url_missing|url_not_allowlisted|final_url_not_allowlisted",
  "symbol_parse_failed_reason": null,
  "symbol_parse_status": "parsed|pending_retry|terminal_failed",
  "parser_version": "stage1_5d_symbol_extraction_v2",
  "symbol_extraction_version": 2
}
```

Rules:

```text
symbols from title:
  symbol_extraction_source = title
  detail_fetch_attempted = false
  detail_fetch_status = not_needed
  symbol_parse_failed_reason = null
  symbol_parse_status = parsed

symbols from detail:
  symbol_extraction_source = detail
  detail_fetch_attempted = true
  detail_fetch_status = success
  symbol_parse_failed_reason = null
  symbol_parse_status = parsed

network_error:
  symbols = []
  detail_fetch_status = network_error
  symbol_parse_failed_reason = detail_fetch_failed
  symbol_parse_status = pending_retry

budget_deferred:
  symbols = []
  detail_fetch_status = budget_deferred
  symbol_parse_failed_reason = detail_budget_deferred
  symbol_parse_status = pending_retry

fixture_missing:
  symbols = []
  detail_fetch_status = fixture_missing
  symbol_parse_failed_reason = detail_fixture_missing
  symbol_parse_status = pending_retry

schema_drift or parse_failed:
  symbols = []
  detail_fetch_status = schema_drift|parse_failed
  symbol_parse_failed_reason = detail_schema_or_parse_failed
  symbol_parse_status = terminal_failed

empty_detail_symbols:
  symbols = []
  symbol_extraction_source = none
  symbol_parse_failed_reason = symbol_missing_after_detail
  symbol_parse_status = terminal_failed

url_missing, url_not_allowlisted, or final_url_not_allowlisted:
  symbols = []
  detail_fetch_status = url_missing|url_not_allowlisted|final_url_not_allowlisted
  symbol_parse_failed_reason = detail_url_invalid
  symbol_parse_status = terminal_failed
```

## Request Manifest And Detail Payload Persistence

Every detail request must be written to `request_manifest` with:

```json
{
  "source_type": "announcement_detail",
  "symbol": "ALL",
  "url": "...",
  "final_url": "...",
  "http_status": 200,
  "row_count": 0,
  "payload_size_bytes": 0,
  "payload_sha256": "...",
  "parser_version": "stage1_5d_symbol_extraction_v2",
  "symbol_extraction_version": 2,
  "error": null,
  "fetched_at_ms": 0
}
```

The full detail payload must also be persisted for review:

```text
detail_payload_persistence = required
storage_path = raw_payloads/announcement_detail/YYYYMMDD/{source_article_id_or_hash}.json|html|txt
```

Reason: the core evidence for this fix is the actual detail body/table that contained candidate `XXXUSDT` / `XXXUSDC` strings. A manifest row with only size/status/hash is not sufficient to review whether the parser extracted the right symbols, missed symbols, or matched irrelevant text.

Disk cost is controlled by scope:

```text
Only persist detail payloads for symbols=[] futures_contract_launch fallback attempts.
These events are rare relative to announcement list polls.
```

## Error Handling

Detail extraction is best-effort and must never break the poll loop.

```text
detail network error -> event kept with symbols=[] and pending_retry
detail request budget full -> event kept with symbols=[] and pending_retry
fixture detail missing -> event kept with symbols=[] and pending_retry
detail schema drift -> event kept with symbols=[] and terminal_failed
detail parser exception -> caught; event kept with symbols=[] and terminal_failed
empty detail symbols -> event kept with symbols=[] and terminal_failed
url missing/not allowlisted -> event kept with symbols=[] and terminal_failed
```

Heartbeat should remain `poll_success=true` if the announcement list fetch and schema parse succeeded. Detail fetch failures are per-event enrichment failures, not source list failures.

## Dedupe And Retry Semantics

Detail enrichment status must be tracked separately from article/event dedupe.

Hard rule:

```text
An article with symbol_parse_status = pending_retry must not be treated as a terminally processed symbol extraction.
```

Required behavior:

```text
network_error -> retry in later polls until max retries or max age
budget_deferred -> retry in the next eligible poll
fixture_missing -> retry in fixture/mock contexts only if fixture later provides detail payload
success after prior failure -> emit parsed event-symbol once
terminal_failed -> no further retry after final state is recorded
```

This prevents the main regression: first poll fails detail fetch, article ID enters `seen_event_ids`, and later healthy detail pages are never parsed.

`pending_retry` rows must not be written to `events/*.jsonl`. They stay in runner retry state until they become either `parsed` or `terminal_failed`.

## Stable Event Key And Event ID Semantics

Stage 1.5D keeps article-level rows with a `symbols` list. It does not split multi-symbol articles into multiple event rows; Stage 1.5F performs event-symbol flattening by hashing `event_id|symbol`.

Required key rules:

```text
if len(symbols) == 0:
  stable_event_key = binance_{source_article_id}_UNKNOWN
  event_id = sha256(stable_event_key)

if len(symbols) == 1:
  stable_event_key = binance_{source_article_id}_{symbol}
  event_id = sha256(stable_event_key)

if len(symbols) > 1:
  stable_event_key = binance_{source_article_id}_MULTI
  event_id = sha256(f"{stable_event_key}|{','.join(sorted(symbols))}")
```

Reason: using only the first symbol makes event identity depend on symbol order, while splitting rows risks article-level dedupe deleting sibling symbols.


## Summary Counters

Existing counters remain required:

```text
raw_futures_launch_article_count
symbol_parsed_event_count
symbol_parse_failed_count
deduped_new_event_count
```

The detail fallback adds required summary counters:

```text
detail_fetch_attempted_count
detail_fetch_success_count
detail_fetch_failed_count
detail_fetch_budget_deferred_count
detail_fetch_url_rejected_count
detail_symbol_extracted_count
detail_symbol_parse_failed_count
title_symbol_extracted_count
symbol_empty_event_count
```

These counters are required because the review question after this patch is not only "did 1.5D run", but "did detail fallback actually recover symbol-empty futures launch rows".

## Safety Boundaries

This feature is public-readonly only:

```text
allowed_hosts = existing Stage 1.5D Binance allowlist
detail_url_scheme_required = https
redirect_final_host_revalidation_required = true
private_api_allowed = false
api_key_allowed = false
order_endpoint_allowed = false
private_ws_allowed = false
```

No strategy or execution object may be imported:

```text
SignalCandidate_allowed = false
TradeIntent_allowed = false
execution_engine_allowed = false
```

## Deployment Semantics

Local code changes do not affect current server processes until deployed and restarted.

Recommended rollout:

```text
1. Implement and test locally.
2. Do not interrupt current 1.5D / 1.5F 7d run.
3. After tests pass, either:
   A. wait for current run to finish, then deploy; or
   B. deploy and start a new Stage 1.5D output root plus matching Stage 1.5F bootstrap.
4. Never mix old and new parser outputs in the same output root when evaluating parser behavior.
```

## Test Strategy

Required unit tests:

```text
test_extract_symbols_from_multiple_tradfi_detail_text
test_extract_symbols_from_nested_detail_payload
test_detail_extraction_preserves_order_and_dedupes
test_detail_extraction_caps_symbol_count
test_regular_single_symbol_title_parser_unchanged
```

Required collector/runner tests:

```text
test_multiple_tradfi_launch_uses_detail_symbols_when_title_has_none
test_detail_fetch_failure_marks_symbol_parse_failed_without_crashing
test_detail_request_manifest_written
test_fixture_mode_does_not_call_live_detail_network
test_empty_detail_symbols_remain_symbol_parse_failed
test_detail_fetch_transient_failure_does_not_permanently_dedup_article
test_detail_budget_deferred_retries_next_poll
test_detail_success_after_prior_failure_emits_event_symbols_once
test_detail_url_non_https_rejected
test_detail_url_non_allowlisted_host_rejected
test_detail_redirect_to_non_allowlisted_host_rejected
test_detail_url_missing_marks_url_missing_without_crash
test_detail_payload_is_persisted_for_review
test_detail_summary_counters_are_emitted
```

Required safety grep:

```bash
rg -n "apiKey\\s*=|api_key\\s*=|secret\\s*=|from .*TradeIntent|TradeIntent\\(|from .*SignalCandidate|SignalCandidate\\(|order_endpoint\\s*=\\s*True|private_ws" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d*
```

Expected: no unsafe hits. Explicit `*_allowed = false` fields are allowed.

## Acceptance Criteria

```text
1. Existing Stage 1.5D parser tests still pass.
2. Existing Stage 1.5D runner tests still pass.
3. Multiple TradFi fixture with detail body produces non-empty symbols.
4. Detail fetch failure produces explicit diagnostic fields and does not crash.
5. Transient detail fetch failure remains retryable and is not permanently swallowed by dedupe.
6. Request manifest includes announcement_detail request rows with payload_sha256 / payload_size_bytes / parser_version / symbol_extraction_version.
7. Detail payload is persisted under raw_payloads/announcement_detail for review.
8. Fixture/mock tests prove no live network is called without live-public-readonly.
9. Detail URL validation rejects non-https, non-allowlisted host, redirect to non-allowlisted host, missing URL, localhost, private IP, and file URL.
10. Detail summary counters are emitted.
11. All safety flags remain false.
12. No execution, paper, live, or alpha claim is introduced.
```

## Open Questions For Implementation Plan

```text
1. Should detail fallback be implemented in collector only, or should normalize_live_event accept an optional detail_symbols parameter?
2. Should schema_drift / parse_failed be terminal_failed immediately, or retryable until max retries?
3. Should detail fetch be attempted for every symbols=[] futures launch, or only titles containing "Multiple" / "TradFi"?
```

Recommended defaults:

```text
1. Add optional detail_symbols to normalize_live_event or a small enrichment wrapper; avoid mixing network into parser.
2. Treat network_error / budget_deferred as retryable; treat url_missing / url_not_allowlisted / final_url_not_allowlisted / empty_detail_symbols / schema_drift / parse_failed as terminal.
3. Attempt detail fetch for every futures_contract_launch with symbols=[], because that is the actual failure condition.
```
