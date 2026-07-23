# Stage 1.5D BAPI Article Detail Source Hotfix Design

```text
status = design_draft_revised_after_review
scope = stage1_5d_bapi_article_detail_source_hotfix
design_owner = human_research_owner
implementation_allowed = false
implementation_plan_allowed = after_design_review_only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

## 1. 背景

Stage 1.5D 当前通过 Binance announcement list BAPI 发现 futures launch 公告，并在标题无法直接解析 symbol 时请求公告详情页。

现有 support detail path 包括：

```text
https://www.binance.com/en/support/announcement/{articleCode}
https://www.binance.com/en/support/announcement/detail/{articleCode}
https://www.binance.com/zh-CN/support/announcement/detail/{articleCode}
```

近期线上观察显示，多篇 `Multiple USDⓈ-Margined TradFi Perpetual Contracts` 公告在这些 support detail path 上长期返回：

```text
http_status = 202
payload_size_bytes = 0 或仅 HTML shell
payload_trusted = false
error = detail_payload_http_status_202
```

这导致正文不可解析，1.5D 无法从 detail 中提取 symbol，1.5F 无法启动正式 depth observation。

已完成的 `detail_retry_overdue_starvation_hotfix` 解决的是 scheduler starvation：

```text
degraded 结束后，overdue article 能获得有界 retry slot；
未选中的 article 有明确 deferred reason；
detail_unavailable_timeout 不污染 1.5F consumable event stream。
```

但该修复不能让 Binance support detail path 必然返回正文。它只是把 202 问题从“卡死/不可审计”降级为“可审计的数据源不可用”。

## 2. Discovery 结果

独立 BAPI discovery 实验证明，Binance 存在 first-party public-readonly web BAPI article detail JSON endpoint：

```text
GET https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=<ARTICLE_CODE>
```

术语必须严格区分：

```text
content_provenance = binance_official_announcement
source_transport = binance_first_party_public_web_bapi_undocumented
```

禁止表述：

```text
official supported API
stable public API
documented endpoint
```

允许表述：

```text
first-party public-readonly web endpoint
official announcement content
operationally undocumented and schema-unstable transport
```

该 endpoint 对以下 202 问题文章返回 `200 + JSON + official article title/body`：

```text
articleCode = f43403ef11974998bc0f46420826577a
title = Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)
body symbols = SHAZUSDT, SOFIUSDT, PANWUSDT, PENGUSDT

articleCode = d0833e4ae9b542be90dbf3fe1c960c53
title = Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-10)
body symbols = GEVUSDT, VRTUSDT, SNOWUSDT, APPUSDT

articleCode = 6cbb1b11a9c843949624cf2eacaac8b4
title = Binance Futures Will Launch USDⓈ-Margined SPCXUSD1 Perpetual Contract (2026-07-20)
body symbols = SPCXUSD1
```

实测返回结构包括：

```text
top_level.code = 000000
data.code = <requested articleCode>
data.id = numeric article id
data.title = article title
data.body = article body string
data.contentJson = optional structured content
```

最小 header 检查：

```text
no_headers -> 200
User-Agent only -> 200
web_headers -> 200
```

因此该 endpoint 当前不需要 login cookie、API key、private endpoint 或账户态 token。但它仍然是未文档化 web transport，必须按 schema-unstable source 处理。

## 3. 目标

本 hotfix design 的目标是：

```text
当 title 无法解析 symbol 时，优先使用 Binance first-party public-readonly web BAPI article detail JSON 获取公告正文，
从官方公告正文中提取 symbols，再用 exchangeInfo 验证，
降低 support detail path HTTP 202 empty 对 formal 1.5F evidence 的影响。
```

非目标：

```text
不改变 1.5F depth observer 行为。
不改变 1.5G evidence threshold。
不允许任何 trade/paper/live/execution/alpha claim。
不使用 private cookie/API key/登录态。
不删除现有 support detail fallback 和 overdue scheduler。
不把 BAPI transport 等同于 Binance 官方承诺的稳定 API。
```

## 4. 新 detail source 顺序

修订后的 1.5D detail source 顺序应为：

```text
1. announcement list BAPI 获取 articleCode/title/releaseDate。
2. 若 title 可直接解析并通过 exchangeInfo 验证，则不需要 detail。
3. 若 title 无法解析 symbol，则优先请求：
   /bapi/composite/v1/public/cms/article/detail/query?articleCode=<ARTICLE_CODE>
4. 若 BAPI detail JSON 返回可信 body，则从 body 中提取 symbol candidate。
5. 所有 candidate symbols 必须经过 exchangeInfo validation。
6. 若 BAPI detail 失败、空 body、schema drift、非 200、非 000000、identity mismatch、title mismatch，则回退到现有 support detail path fallback。
7. 若 support detail fallback 仍失败，则继续使用现有 bounded retry / degraded / overdue diagnostics。
```

BAPI 成功后可以跳过 support fallback，但必须同时满足：

```text
payload_trusted = true
article identity matched
article title matched or high-confidence normalized match
parser_context legal
symbol candidates parsed
exchangeInfo validated or explicitly pending_exchangeinfo_visibility
```

## 5. 为什么旧 202 修复必须保留

现有 202 修复和本 BAPI source hotfix 解决的问题不同，必须继续保留。

```text
BAPI source hotfix:
  解决“优先数据源选错，support detail path 202 但 BAPI detail 可用”的问题。

202 / retry / overdue hotfix:
  解决“所有 detail source 都失败时，scheduler 不得卡死、不得污染正式事件流、必须可审计”的问题。
```

因此 BAPI detail 失败后仍必须回到旧 1.5D 详情页面请求路径：

```text
BAPI detail failed
-> support announcement URL fallback
-> source-specific endpoint health / degraded circuit breaker
-> bounded overdue retry
-> scheduler diagnostics
-> terminal diagnostics when max age exceeded
```

不能因为新增 BAPI 就删除或绕过旧的 degraded/retry 保护。

## 6. Evidence 强度与 Transport 分层

证据必须拆成二维，不能把 transport 可访问性当成内容权威性。

内容证据 ranking：

```text
official_article_body_confirmed
> official_title_exact_symbol_confirmed
> exchangeinfo_delta_assisted_candidate
```

Transport/source channel：

```text
bapi_article_detail_query
support_article_detail
title_only
exchangeinfo_delta
```

BAPI detail 和 support detail 如果都成功，它们提供的是同级别的 `official_article_body_confirmed` 内容证据；BAPI 不是内容上更权威，只是当前 transport 更可访问。

推荐输出字段：

```text
evidence_source = official_article_body_confirmed
detail_transport = bapi_article_detail_query
symbol_extraction_source = bapi_article_body
symbol_validation_status = validated_by_exchangeinfo
source_profile = binance_official_announcements_like_rows
content_provenance = binance_official_announcement
source_transport = binance_first_party_public_web_bapi_undocumented
```

若只靠 exchangeInfo delta 推导，不得写成 detail-confirmed：

```text
evidence_source = exchangeinfo_delta_assisted_candidate
detail_transport = exchangeinfo_delta
symbol_extraction_source = exchangeinfo_delta
symbol_validation_status = derived_candidate
```

## 7. Trusted BAPI Payload Contract

BAPI response 必须满足全部 trusted 条件，才允许进入 symbol parser：

```text
final_url host == www.binance.com
http_status == 200
top-level payload is JSON object
top-level code == 000000
data is JSON object
data.code == requested articleCode
data.title exists
data.title normalized/high-confidence matches catalog/list title when available
data.body or recognized structured content exists
payload is not captcha/WAF/login page/HTML shell
compressed and decompressed payload size within configured caps
```

硬失败 error class：

```text
bapi_article_identity_mismatch
bapi_article_title_mismatch
bapi_payload_schema_invalid
bapi_body_missing
bapi_final_host_invalid
bapi_response_too_large
bapi_payload_not_json
bapi_waf_or_login_shell
```

其中 identity mismatch 必须 hard reject，不允许 fallback parser 从不匹配文章中提取 symbol。

## 8. Parser 要求

BAPI detail body 当前通常是 JSON string，结构近似：

```json
{
  "node": "root",
  "child": [ ... text nodes ... ]
}
```

允许 parser mode：

```text
structured_json_tree:
  body/contentJson 可解析为 JSON tree；递归提取 node=text 的 text 字段。

recognized_sanitized_html:
  仅当 body 被明确识别为公告正文 HTML 时，strip script/style/tags 后提取 visible text。
```

禁止 parser mode：

```text
raw_unparsed_body_string
raw_html_with_scripts
unknown_schema_best_effort
```

如果 body 不是 `structured_json_tree` 或 `recognized_sanitized_html`：

```text
error = bapi_body_schema_drift
symbol_parse_status = not_attempted
fallback_to_support_detail = true
```

不得因为 body 字符串里出现 `XXXUSDT` 就直接解析。原因是 raw body 可能包含 URL、风险提示、相关文章、footer、示例或非正文文本。

## 9. Symbol Context / Provenance 要求

Symbol parser 必须携带上下文，而不是只输出 symbol 字符串。

每个 candidate 至少记录：

```text
parser_context
body_node_path
text_span
event_phrase_match
candidate_confidence
symbol_extraction_source
content_provenance
source_transport
```

允许上下文：

```text
launch schedule row
will launch segment
contract list/table/list item
formal announcement body paragraph
```

禁止上下文：

```text
disclaimer
risk warning
footer
related articles
URL
example text
generic educational text
```

exchangeInfo validation 只能验证“这个 symbol 在交易所存在或即将存在”，不能单独证明“这个 symbol 属于这篇公告”。因此：

```text
exchangeInfo alone cannot promote unrelated symbols to confirmed event symbols.
```

## 10. exchangeInfo Validation 与 Pending Visibility

BAPI body 解析出的 symbols 必须继续经过 exchangeInfo validation。

最低要求：

```text
symbol exists in Binance futures exchangeInfo
contractType in allowed contract types
quoteAsset / marginAsset in allowed assets
status in validatable/emittable statuses
if PENDING_TRADING, preserve pending/pre-trading semantics
```

如果正文已解析出 candidate，但 exchangeInfo 暂时不可见，状态必须与 detail fetch 分离：

```text
detail_parse_status = parsed
parsed_candidate_symbols = [ ... ]
symbol_validation_status = pending_exchangeinfo_visibility
pending_reason = exchangeinfo_symbol_not_yet_visible
```

后续只应重试 exchangeInfo validation，不应重复请求 BAPI detail，除非 payload hash/version policy 明确要求重新采集。

需要拆分 cadence：

```text
detail_source_retry
exchangeinfo_validation_retry
```

## 11. Endpoint Health 与 Failure Classification

第一版必须拆分 BAPI 与 support detail health。不能让 support 202 degraded 抑制 BAPI detail，也不能让 BAPI degraded 禁用 support fallback。

推荐状态：

```json
{
  "endpoint_health_by_source": {
    "bapi_article_detail_query": {
      "detail_endpoint_degraded_until_ms": 0,
      "recent_attempt_results": []
    },
    "support_article_detail": {
      "detail_endpoint_degraded_until_ms": 0,
      "recent_attempt_results": []
    }
  }
}
```

failure class 第一版至少包括：

```text
bapi_http_non_200
bapi_api_code_non_000000
bapi_payload_schema_invalid
bapi_article_identity_mismatch
bapi_article_title_mismatch
bapi_body_missing
bapi_body_schema_drift
bapi_response_too_large
support_detail_http_202_empty
support_detail_http_non_200
support_detail_empty_untrusted_payload
support_detail_schema_drift
```

持久化字段必须按 source/variant 区分：

```text
bapi_detail_failure_count
bapi_detail_last_failure_class
bapi_detail_next_retry_at_ms
bapi_detail_degraded_until_ms
support_detail_failure_count
support_detail_last_failure_class
support_detail_next_retry_at_ms
support_detail_degraded_until_ms
```

## 12. Budget 与 Retry Cycle 不变量

BAPI + support fallback 必须共享总 HTTP request budget：

```text
DETAIL_HTTP_REQUEST_BUDGET_PER_POLL
MAX_DETAIL_SOURCE_VARIANTS_PER_CYCLE
```

不变量：

```text
1 scheduler logical retry cycle may contain multiple source variant HTTP requests.
Each BAPI/support request consumes one HTTP budget unit.
BAPI trusted success ends the logical cycle and skips support fallback.
request_manifest rows are written per actual HTTP request.
detail_retry_cycle_count != detail_http_request_count by design.
```

不得因为新增 BAPI source 绕过已有 HTTP budget、degraded circuit breaker 或 overdue retry slot 保护。

## 13. Request Manifest 要求

新增 BAPI detail 请求必须写入 `request_manifest/*.jsonl`。

成功示例：

```json
{
  "request_type": "announcement_detail_bapi",
  "source_type": "announcement_detail_bapi",
  "detail_fetch_variant": "bapi_article_detail_query",
  "source_article_id": "<articleCode>",
  "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=<articleCode>",
  "final_url": "...",
  "http_status": 200,
  "api_code": "000000",
  "payload_trusted": true,
  "payload_size_bytes": 112299,
  "payload_sha256": "...",
  "payload_path": "raw_payloads/announcement_detail/...",
  "parser_version": "stage1_5d_symbol_extraction_v2",
  "symbol_extraction_version": 2
}
```

失败也必须写 manifest：

```json
{
  "request_type": "announcement_detail_bapi",
  "detail_fetch_variant": "bapi_article_detail_query",
  "http_status": 400,
  "api_code": "000002",
  "error": "bapi_api_code_non_000000",
  "payload_trusted": false
}
```

## 14. Raw Payload 要求

成功响应必须保存原始 JSON payload，而不是只保存 body text。

原因：

```text
1. 保留 title/body/id/code 等完整上下文。
2. 允许审计 payload hash。
3. 允许未来 parser 版本重放。
4. 防止只保存提取结果造成不可复核。
```

Raw payload 必须 append-only，不能按 articleCode 覆盖旧文件。

推荐路径：

```text
raw_payloads/announcement_detail/<articleCode>/<fetched_at_ms>.<variant>.<sha256>.json
```

或 flat path：

```text
raw_payloads/announcement_detail/<articleCode>.<variant>.<fetched_at_ms>.<sha256>.json
```

不变量：

```text
append_only = true
atomic_write = true
same_hash_dedup_allowed = true
different_hash_revision_preserved = true
```

Summary 需要记录：

```text
bapi_payload_revision_count
bapi_payload_hash_change_count
```

## 15. URL / Resource / Parser Limits

配置必须来自 `configs/base.py`，不得在 `src/` 或 `scripts/` 里硬编码。

articleCode：

```text
regex = ^[0-9a-fA-F]{32}$
```

必须限制：

```text
final host
redirect chain
compressed response bytes
decompressed response bytes
JSON depth
JSON node count
extracted text chars
symbol candidate count
```

建议新增配置：

```text
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_JSON_DEPTH
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_NODE_COUNT
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_EXTRACTED_TEXT_CHARS
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_SYMBOL_CANDIDATES
EXTERNAL_SIGNAL_STAGE1_5D_MAX_DETAIL_SOURCE_VARIANTS_PER_CYCLE
```

禁止发送：

```text
Cookie
Authorization
X-MBX-APIKEY
account/session/private headers
```

## 16. Old Event Boundary

`f434`、`d0833`、`6cbb` 可以作为 parser/recovery/regression fixtures，但旧事件不能被新 root 回填成 formal 1.5F evidence。

不变量：

```text
pre-hotfix missed article can validate parser but not become formal 1.5F evidence
new root does not import old scheduler pending state
1.5F watermark and age gate unchanged
no live network in pytest; use captured payload fixtures
```

若旧 article 被重新解析，只能写入 parser diagnostic 或 recovery audit，不得进入 1.5F consumable event stream。

## 17. Metrics

Summary/diagnostics 至少新增：

```text
bapi_detail_request_count
bapi_detail_success_count
bapi_detail_trusted_payload_count
bapi_detail_schema_drift_count
bapi_detail_identity_mismatch_count
bapi_detail_rate_limited_count
bapi_to_support_fallback_count
bapi_symbol_parse_success_count
bapi_symbol_validation_pending_count
bapi_symbol_validation_success_count
support_fallback_success_count
detail_http_manifest_mismatch_count
```

这些指标只用于 source health 和 parser audit，不允许被解释为 alpha 或 execution feasibility。

## 18. Safety Boundaries

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

本 hotfix 只改善 official announcement detail source access，不产生任何交易结论。

如果任何 downstream code 尝试发出：

```text
SignalCandidate
TradeIntent
order intent
paper/live flag
execution_feasibility_claim
alpha_interpretation
```

Stage 1.5D 必须 safe no-op 并 hard blocker。

## 19. Required Tests

implementation plan 至少应包含以下测试：

```text
test_bapi_article_detail_query_returns_trusted_payload_fixture
test_no_symbol_title_uses_bapi_detail_before_support_fallback
test_bapi_detail_symbols_are_exchangeinfo_validated
test_bapi_detail_failure_falls_back_to_support_detail_paths
test_bapi_detail_manifest_records_variant_and_payload_hash
test_bapi_body_json_tree_text_extraction
test_bapi_detail_does_not_require_private_cookie_or_api_key
test_support_detail_202_existing_retry_path_remains_available
test_bapi_detail_schema_drift_is_non_terminal_and_auditable
test_support_202_degraded_state_does_not_suppress_bapi_detail
test_bapi_degraded_state_does_not_disable_support_fallback
test_bapi_identity_mismatch_hard_rejects
test_bapi_title_mismatch_falls_back_or_rejects_without_symbol_parse
test_raw_unparsed_body_string_is_not_parsed
test_unrelated_valid_symbol_in_disclaimer_is_ignored
test_symbol_candidate_records_node_path_and_parser_context
test_exchangeinfo_alone_cannot_promote_unrelated_symbol
test_detail_parsed_exchangeinfo_not_visible_enters_pending_validation_without_bapi_refetch
test_bapi_success_skips_support_and_respects_total_http_budget
test_bapi_and_support_requests_each_write_manifest_rows
test_pre_hotfix_article_fixture_not_consumable_by_stage1_5f
test_new_root_does_not_import_old_scheduler_pending_state
```

Regression fixtures should include captured payloads for:

```text
f43403ef11974998bc0f46420826577a -> SHAZUSDT/SOFIUSDT/PANWUSDT/PENGUSDT
d0833e4ae9b542be90dbf3fe1c960c53 -> GEVUSDT/VRTUSDT/SNOWUSDT/APPUSDT
6cbb1b11a9c843949624cf2eacaac8b4 -> SPCXUSD1
```

Tests must not call live Binance endpoints.

## 20. Deployment Expectations

本 hotfix 应使用新 root suffix，避免与 overdue starvation hotfix root 混写：

```text
_7d_bapi_article_detail_source_hotfix
```

旧 root 只读保留，不回填 formal evidence。

部署后验收：

```text
1. 1.5D request_manifest contains announcement_detail_bapi rows.
2. New no-symbol articles can parse symbols from BAPI body when BAPI trusted payload is available.
3. support detail HTTP 202 remains observable only as fallback, not primary path.
4. BAPI health and support health are separately visible.
5. 1.5F only consumes symbol-validated event rows.
6. No paper/live/execution flags become true.
```

## 21. Open Questions Resolved

```text
1. BAPI detail success 是否等同于 support detail success？
   结论：内容证据同级，transport 不同。两者都是 official_article_body_confirmed，但 BAPI 是 undocumented web BAPI transport。

2. 是否立即拆分 BAPI endpoint health 与 support endpoint health？
   结论：必须第一版拆分。support 202 degraded 不得抑制 BAPI，BAPI degraded 也不得禁用 support fallback。

3. 是否允许 BAPI 成功后跳过 support fallback？
   结论：允许，但仅在 trusted payload、identity match、title match、parser context 合法、symbols validated 或 pending_validation 明确成立时允许。

4. 是否保留原 202 retry / overdue hotfix？
   结论：必须保留。BAPI 失败后仍需要旧 fallback 和 bounded retry 保护。

5. 是否允许 exchangeInfo delta assisted symbol resolution？
   结论：可作为独立弱证据设计，不属于本 hotfix 的 detail-confirmed path；不得把 exchangeInfo delta 推导直接等同于 official_article_body_confirmed。
```

## 22. Design Decision

```text
decision = stage1_5d_bapi_article_detail_source_design_ready_for_review
allowed_next_action = review_stage1_5d_bapi_article_detail_source_design
implementation_plan_allowed = false_until_review_passes
implementation_allowed = false
```
