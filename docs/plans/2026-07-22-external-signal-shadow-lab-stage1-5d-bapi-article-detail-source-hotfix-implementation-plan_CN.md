# Stage 1.5D BAPI Article Detail Source Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a first-party public-readonly Binance web BAPI article detail source before the existing support detail fallback, so no-symbol futures launch announcements can be parsed from official announcement body when support detail paths return HTTP 202 shell.

**Architecture:** Keep 1.5D as public-readonly evidence collection only. Add BAPI detail as a new source transport with strict trusted-payload validation, source-specific health, append-only raw payload storage, context-aware symbol extraction, and explicit launch-time preservation. Preserve all existing support detail fallback, 202/degraded retry, overdue scheduler, 1.5F watermark, and age-gate behavior.

**Tech Stack:** Python stdlib `urllib`, JSONL artifacts, `configs/base.py`, pytest, existing `src/research/external_signal_shadow/stage1_5d_*` modules, existing `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` runner.

---

## 0. Non-Negotiable Boundaries

本计划只允许实现 1.5D source access hotfix。

必须保持：

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

禁止：

```text
private endpoint
login cookie
Authorization header
X-MBX-APIKEY
account/session state
paper/live/execution code path
old event backfill into 1.5F formal evidence
```

术语约束：

```text
content_provenance = binance_official_announcement
source_transport = binance_first_party_public_web_bapi_undocumented
```

禁止在代码、summary、review 中写：

```text
official supported API
stable public API
documented endpoint
```

## 0.1 Review Amendments That Override Later Task Text

The following amendments are blocking requirements. If a later task appears weaker or ambiguous, follow this section.

### A. Formal 1.5F Evidence Chain Must Close

This hotfix is not complete if it only extracts `symbols`.

Required data chain:

```text
BAPI body
-> extracted_text
-> symbols
-> per-symbol launch times
-> exchangeInfo validation
-> symbol_effective_launch_times_ms
-> 1.5D event row
-> 1.5F formal accepted row
```

BAPI parser output must include:

```json
{
  "extracted_text": "...",
  "symbols": ["..."],
  "candidate_provenance": [...]
}
```

`extracted_text` must be passed through the same launch-time extraction path used by support detail text. Do not create a BAPI-only launch-time parser unless a failing test proves the existing parser cannot handle BAPI text.

Required tests:

```text
test_bapi_body_reuses_existing_launch_time_parser
test_bapi_multiple_contract_article_extracts_per_symbol_launch_times
test_new_post_watermark_bapi_event_can_reach_1_5f_formal_acceptance
```

Fixtures for launch-time tests must preserve schedule/time text, not only a simplified symbol sentence.

### B. Variant Count Must Not Delete Existing Fallbacks

Default:

```text
EXTERNAL_SIGNAL_STAGE1_5D_MAX_DETAIL_SOURCE_VARIANTS_PER_CYCLE = 4
```

Reason:

```text
BAPI + primary support + detail-path support + zh-CN support = 4 possible variants.
```

If the current code only builds two support variants, the implementation may keep the current fallback set, but the config must not prevent all design-approved variants when budget allows.

Actual HTTP requests are still constrained by:

```text
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FALLBACK_MAX_URLS_PER_ARTICLE
```

Required tests:

```text
test_bapi_failure_can_reach_all_existing_support_variants_when_budget_allows
test_http_budget_exhaustion_defers_remaining_variant_without_deleting_it
```

### C. Source-Specific Health Must Drive Scheduler Eligibility

The logical article cycle may be selected if at least one detail source is currently usable.

Do not let legacy global `endpoint_degraded_until_ms` suppress BAPI if BAPI source health is clean.

Required scheduler state fields:

```text
all_detail_sources_degraded
bapi_detail_source_degraded
support_detail_source_degraded
```

Rules:

```text
support degraded only -> BAPI cycle still eligible
BAPI degraded only -> support fallback cycle still eligible
BAPI degraded AND support degraded -> use existing bounded degraded policy
```

Required runner tests:

```text
test_support_global_legacy_degraded_state_cannot_block_healthy_bapi_cycle
test_bapi_degraded_and_support_healthy_still_selects_article_cycle
test_all_sources_degraded_uses_existing_bounded_degraded_policy
```

### D. exchangeInfo Validation-Pending Needs Its Own Queue

If BAPI body is parsed but exchangeInfo is not yet visible, do not re-fetch BAPI every poll.

Persist per article:

```text
detail_parse_status = parsed
parsed_candidate_symbols = [...]
per_symbol_validation_state = {...}
next_exchangeinfo_validation_at_ms
last_exchangeinfo_validation_at_ms
exchangeinfo_validation_attempt_count
exchangeinfo_validation_max_age_ms
exchangeinfo_validation_terminal_reason
exchangeinfo_validation_retryable = true
detail_retryable = false
```

Cadence must come from `configs/base.py`. Add constants if existing pending validation configs cannot express this cleanly:

```text
EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_RETRY_INTERVAL_SEC
EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_MAX_AGE_SEC
```

Required tests:

```text
test_validation_pending_reenters_exchangeinfo_validation_queue
test_validation_pending_survives_restart
test_validation_pending_does_not_refetch_bapi
test_validation_pending_times_out_to_non_consumable_diagnostic
```

### E. Multi-Symbol Validation Is All-Or-None In First Version

For one article body with multiple parsed symbols:

```text
all candidates exchangeInfo validated -> emit full event once
any candidate pending -> emit no consumable event
```

Persist:

```text
already_emitted_symbols
pending_symbols
parsed_candidate_symbols
per_symbol_validation_state
```

Required tests:

```text
test_partial_exchangeinfo_visibility_does_not_emit_incomplete_multi_symbol_event
test_later_full_visibility_emits_once_without_duplicate_symbols
```

### F. Trusted Payload URL/Title/Resource Rules

Hard reject:

```text
data.code != requested articleCode
final host != www.binance.com
userinfo present
non-default port present
fragment present
query contains anything except one articleCode
payload is not JSON object
response too large
```

Title mismatch is not identity mismatch. It must produce:

```text
bapi_article_title_mismatch
payload_trusted = false
fallback_to_support_detail = true
```

Title normalization must use:

```text
HTML unescape
Unicode NFKC
casefold
collapse whitespace
normalize common punctuation
```

### G. Resource Limits Must Be Enforced, Not Merely Configured

Required tests:

```text
test_bapi_response_read_is_bounded
test_bapi_response_above_max_bytes_is_rejected
test_bapi_json_depth_limit
test_bapi_json_node_count_limit
test_bapi_extracted_text_limit
test_bapi_symbol_candidate_limit
test_bapi_redirect_final_host_revalidated
test_bapi_redirect_count_is_bounded
```

Implementation must use bounded reads:

```python
response.read(max_bytes + 1)
```

Do not read an unbounded response into memory and then check its size.

Request headers should include:

```text
Accept: application/json
Accept-Encoding: identity
```

Still forbidden:

```text
Cookie
Authorization
X-MBX-APIKEY
```

### H. Symbol Extraction Must Be Segment-Based

Do not classify an entire large text node as legal just because it contains one launch phrase.

Required algorithm:

```text
identify launch schedule/list/table segment
extract symbols only inside that local segment
record segment_start/end
record local_text_span
record event_phrase_distance
record section classification
```

Required tests:

```text
test_single_large_node_does_not_capture_disclaimer_symbol
test_symbol_must_be_within_launch_context_span
test_real_frozen_fixture_preserves_expected_schedule_structure
```

### I. Raw Payload Hash Must Use Original Response Bytes

Append-only writer must accept:

```text
raw_bytes
parsed_payload
content_type
http_status
detail_fetch_variant
```

Persist hashes:

```text
raw_payload_sha256
canonical_json_sha256 optional
```

All responses with bytes should be saved, including:

```text
trusted success
schema drift
identity mismatch
non-000000 API code
HTTP non-200 with body
```

Metrics:

```text
bapi_payload_revision_count
bapi_payload_hash_change_count
```

### J. Per-Article Per-Source Failure State Is Required

Persist:

```json
{
  "detail_source_state": {
    "bapi_article_detail_query": {
      "retryable": false,
      "terminal_reason": "bapi_article_illegal_parameter",
      "last_failure_class": "...",
      "attempt_count": 1
    },
    "support_article_detail": {
      "retryable": true
    }
  }
}
```

Classification requirements:

```text
400 illegal parameter -> BAPI article-specific terminal, support can continue
404 -> BAPI article-specific terminal, support can continue
429 -> BAPI transient + BAPI breaker
5xx/timeout -> BAPI transient + BAPI breaker
schema drift -> BAPI source failure + audit
identity mismatch -> integrity failure + alert, support can continue
response too large -> safety failure
```

### K. Manifest / Counter Audit Contract

Invariant:

```text
each actual HTTP request
= exactly one request_manifest row
= detail_http_request_count increment by 1
```

Logical cycle remains separate:

```text
detail_retry_cycle_count != detail_http_request_count
```

Required tests:

```text
test_bapi_manifest_contains_required_audit_fields
test_actual_http_request_count_matches_manifest_rows
test_logical_cycle_count_remains_separate_from_http_count
```

### L. Old Event Boundary Must Cross 1.5F

Two test families are required:

```text
historical f434/d083 frozen fixture:
  parser can recover body/symbols
  watermark/age gate prevents formal 1.5F accepted evidence

synthetic post-watermark article:
  BAPI body extracts symbol + launch time
  exchangeInfo validates
  1.5D emits event
  1.5F formally accepts
```

---

## 1. Preflight: Confirm Current Code Shape

**Files:**
- Read: `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
- Read: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Read: `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- Read: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Read: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Read: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Read: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Inspect exact integration points**

Run:

```bash
grep -n "fetch_public_payload\|build_announcement_detail_fallback_urls\|update_detail_endpoint_health\|request_manifest\|detail_http_requests_remaining" \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
```

Expected:

```text
Existing runner performs support detail fallback inside one logical detail retry cycle.
Existing runner uses detail_http_requests_remaining separately from detail_budget_remaining.
```

**Step 2: Confirm no uncommitted code changes will be overwritten**

Run:

```bash
git status --short
```

Expected:

```text
Only intentional docs changes should be dirty before implementation starts.
If src/scripts/tests/configs are dirty from unrelated work, stop and ask before editing.
```

---

## 2. Add Config Constants

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`

**Step 1: Write failing config test**

Add:

```python
def test_stage1_5d_bapi_article_detail_source_config():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_DETAIL_PATH == "/bapi/composite/v1/public/cms/article/detail/query"
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_CODE_PATTERN == r"^[0-9a-fA-F]{32}$"
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES >= 500_000
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_JSON_DEPTH >= 20
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_NODE_COUNT >= 10_000
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_EXTRACTED_TEXT_CHARS >= 100_000
    assert (
        base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_SYMBOL_CANDIDATES
        == base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MAX_DETAIL_SOURCE_VARIANTS_PER_CYCLE >= 4
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_RETRY_INTERVAL_SEC > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_MAX_AGE_SEC >= 12 * 60 * 60
```

**Step 2: Run failing test**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py::test_stage1_5d_bapi_article_detail_source_config -q
```

Expected: FAIL because constants do not exist.

**Step 3: Add constants**

Add near existing Stage 1.5D detail constants in `configs/base.py`:

```python
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_DETAIL_PATH = "/bapi/composite/v1/public/cms/article/detail/query"
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_CODE_PATTERN = r"^[0-9a-fA-F]{32}$"
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES = 2_000_000
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_JSON_DEPTH = 32
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_NODE_COUNT = 50_000
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_EXTRACTED_TEXT_CHARS = 300_000
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_SYMBOL_CANDIDATES = EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS
EXTERNAL_SIGNAL_STAGE1_5D_MAX_DETAIL_SOURCE_VARIANTS_PER_CYCLE = 4
EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_RETRY_INTERVAL_SEC = 60
EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_MAX_AGE_SEC = EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_MAX_TOTAL_SEC
```

**Step 4: Run test**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py::test_stage1_5d_bapi_article_detail_source_config -q
```

Expected: PASS.

---

## 3. Add BAPI Detail Client and URL Guard

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py`

**Step 1: Write failing client tests**

Before writing tests, confirm URL builder compatibility:

```bash
grep -n "def build_announcement_list_url" src/research/external_signal_shadow/stage1_5d_live_event_source_client.py
```

Expected:

```text
The helper builds a URL with urllib.parse.urlencode query params and can safely be reused for articleCode.
If not, implement a dedicated BAPI URL builder instead of changing list URL behavior.
```

Add tests:

```python
def test_build_bapi_article_detail_url_requires_32_hex_code():
    with pytest.raises(ValueError, match="bapi_article_code_invalid"):
        build_bapi_article_detail_url("not-valid")


def test_build_bapi_article_detail_url_uses_query_param():
    url = build_bapi_article_detail_url("f43403ef11974998bc0f46420826577a")
    assert url == (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query"
        "?articleCode=f43403ef11974998bc0f46420826577a"
    )


def test_validate_bapi_article_detail_url_rejects_support_path():
    with pytest.raises(ValueError, match="bapi_detail_path_not_allowed"):
        validate_bapi_article_detail_url("https://www.binance.com/en/support/announcement/abc")


def test_fetch_public_bapi_article_detail_requires_live_flag():
    with patch("urllib.request.urlopen") as urlopen:
        with pytest.raises(PermissionError):
            fetch_public_bapi_article_detail(
                "f43403ef11974998bc0f46420826577a",
                live_public_readonly=False,
            )
        urlopen.assert_not_called()


def test_fetch_public_bapi_article_detail_does_not_send_private_headers():
    captured = {}

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self):
            return "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=f43403ef11974998bc0f46420826577a"
        def read(self, n=-1):
            return b'{"code":"000000","data":{"code":"f43403ef11974998bc0f46420826577a","title":"x","body":"{}"}}'

    def fake_urlopen(req, timeout):
        captured.update(dict(req.header_items()))
        return FakeResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        fetch_public_bapi_article_detail(
            "f43403ef11974998bc0f46420826577a",
            live_public_readonly=True,
        )

    lowered = {k.lower(): v for k, v in captured.items()}
    assert "authorization" not in lowered
    assert "cookie" not in lowered
    assert "x-mbx-apikey" not in lowered


def test_bapi_response_read_is_bounded():
    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self):
            return "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=f43403ef11974998bc0f46420826577a"
        def read(self, n=-1):
            assert n == 101
            return b"{}"

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES", 100):
        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            fetch_public_bapi_article_detail(
                "f43403ef11974998bc0f46420826577a",
                live_public_readonly=True,
            )


def test_bapi_response_above_max_bytes_is_rejected():
    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self):
            return "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=f43403ef11974998bc0f46420826577a"
        def read(self, n=-1):
            return b"x" * n

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES", 100):
        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            result = fetch_public_bapi_article_detail(
                "f43403ef11974998bc0f46420826577a",
                live_public_readonly=True,
            )
    assert result["ok"] is False
    assert result["error"] == "bapi_response_too_large"
```

**Step 2: Run failing tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py -q
```

Expected: FAIL on missing BAPI helper functions.

**Step 3: Implement helpers**

Add imports and functions:

```python
import re


def build_bapi_article_detail_url(article_code: str) -> str:
    pattern = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_CODE_PATTERN", r"^[0-9a-fA-F]{32}$")
    if not article_code or not re.match(pattern, article_code):
        raise ValueError("bapi_article_code_invalid")
    base_url = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_BASE_URL", "https://www.binance.com")
    path = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_DETAIL_PATH", "/bapi/composite/v1/public/cms/article/detail/query")
    return build_announcement_list_url(base_url, path, {"articleCode": article_code})


def validate_bapi_article_detail_url(url: str, allowed_domains: tuple[str, ...] | None = None) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("bapi_detail_url_scheme_not_allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("domain_not_allowed")
    if allowed_domains is None:
        allowed_domains = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_DOMAINS", ("binance.com", "www.binance.com"))
    if not host_allowed(host, allowed_domains):
        raise ValueError("domain_not_allowed")
    expected_path = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_DETAIL_PATH", "/bapi/composite/v1/public/cms/article/detail/query")
    if parsed.path != expected_path:
        raise ValueError("bapi_detail_path_not_allowed")
    params = urllib.parse.parse_qs(parsed.query)
    codes = params.get("articleCode") or []
    if len(codes) != 1:
        raise ValueError("bapi_article_code_missing")
    pattern = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_CODE_PATTERN", r"^[0-9a-fA-F]{32}$")
    if not re.match(pattern, codes[0]):
        raise ValueError("bapi_article_code_invalid")
```

Implement `fetch_public_bapi_article_detail(...)` as a JSON-specific fetch that:

```text
requires live_public_readonly
builds URL from articleCode
validates requested and final URL
uses only User-Agent / Accept / Accept-Encoding headers
rejects response larger than EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES
returns ok/payload/raw_bytes/final_url/http_status/payload_size_bytes/error
```

Read response bytes with:

```python
raw_bytes = response.read(max_response_bytes + 1)
if len(raw_bytes) > max_response_bytes:
    return {"ok": False, "error": "bapi_response_too_large", ...}
```

Do not call unbounded `response.read()`.

**Step 4: Run client tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py -q
```

Expected: PASS.

---

## 4. Add Trusted Payload Validation

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py`

**Step 1: Write failing validator tests**

Add:

```python
def _trusted_payload(article_code="f43403ef11974998bc0f46420826577a", title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)"):
    return {
        "code": "000000",
        "data": {
            "code": article_code,
            "id": 280581,
            "title": title,
            "body": '{"node":"root","child":[{"node":"text","text":"Binance Futures will launch SHAZUSDT Perpetual Contracts"}]}',
        },
    }


def test_validate_bapi_payload_accepts_identity_and_title_match():
    result = validate_bapi_article_detail_payload(
        _trusted_payload(),
        requested_article_code="f43403ef11974998bc0f46420826577a",
        catalog_title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
    )
    assert result["payload_trusted"] is True
    assert result["data"]["code"] == "f43403ef11974998bc0f46420826577a"


def test_validate_bapi_payload_rejects_identity_mismatch():
    payload = _trusted_payload(article_code="d0833e4ae9b542be90dbf3fe1c960c53")
    result = validate_bapi_article_detail_payload(
        payload,
        requested_article_code="f43403ef11974998bc0f46420826577a",
        catalog_title=payload["data"]["title"],
    )
    assert result["payload_trusted"] is False
    assert result["error"] == "bapi_article_identity_mismatch"


def test_validate_bapi_payload_rejects_title_mismatch():
    result = validate_bapi_article_detail_payload(
        _trusted_payload(title="Unrelated announcement"),
        requested_article_code="f43403ef11974998bc0f46420826577a",
        catalog_title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
    )
    assert result["payload_trusted"] is False
    assert result["error"] == "bapi_article_title_mismatch"
    assert result["fallback_to_support_detail"] is True


def test_validate_bapi_payload_rejects_html_shell_or_login_body():
    payload = _trusted_payload()
    payload["data"]["body"] = "<html><title>Just a moment...</title></html>"
    result = validate_bapi_article_detail_payload(
        payload,
        requested_article_code="f43403ef11974998bc0f46420826577a",
        catalog_title=payload["data"]["title"],
    )
    assert result["payload_trusted"] is False
    assert result["error"] in {"bapi_waf_or_login_shell", "bapi_body_schema_drift"}
```

**Step 2: Run failing tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py -q
```

Expected: FAIL on missing validator.

**Step 3: Implement validator**

Implement:

```python
import html
import unicodedata


def normalize_title_for_match(title: str) -> str:
    text = html.unescape(title or "")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("–", "-").replace("—", "-")
    return " ".join(text.casefold().split())


def validate_bapi_article_detail_payload(payload: object, *, requested_article_code: str, catalog_title: str | None = None) -> dict:
    if not isinstance(payload, dict):
        return {"payload_trusted": False, "error": "bapi_payload_schema_invalid"}
    if payload.get("code") != "000000":
        return {"payload_trusted": False, "error": "bapi_api_code_non_000000"}
    data = payload.get("data")
    if not isinstance(data, dict):
        return {"payload_trusted": False, "error": "bapi_payload_schema_invalid"}
    if data.get("code") != requested_article_code:
        return {"payload_trusted": False, "error": "bapi_article_identity_mismatch"}
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return {"payload_trusted": False, "error": "bapi_payload_schema_invalid"}
    if catalog_title and normalize_title_for_match(title) != normalize_title_for_match(catalog_title):
        return {
            "payload_trusted": False,
            "error": "bapi_article_title_mismatch",
            "fallback_to_support_detail": True,
        }
    body = data.get("body") or data.get("contentJson")
    if body is None:
        return {"payload_trusted": False, "error": "bapi_body_missing"}
    if isinstance(body, str) and any(marker in body.lower() for marker in ("just a moment", "captcha", "login", "cloudflare")):
        return {"payload_trusted": False, "error": "bapi_waf_or_login_shell"}
    return {"payload_trusted": True, "error": None, "data": data}
```

URL trust must be validated by the client result before payload trust is considered true:

```text
final_host == www.binance.com
no userinfo
no fragment
no non-default port
query == exactly one articleCode
```

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py -q
```

Expected: PASS.

---

## 5. Add BAPI Body Parser With Provenance

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Write failing parser tests**

Add:

```python
def test_bapi_body_json_tree_text_extraction_records_context():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": '{"node":"root","child":[{"node":"text","text":"Binance Futures will launch SHAZUSDT and SOFIUSDT USDⓈ-Margined Perpetual Contracts."}]}',
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SHAZUSDT", "SOFIUSDT"]
    assert result["symbol_extraction_source"] == "bapi_article_body"
    assert result["evidence_source"] == "official_article_body_confirmed"
    assert result["detail_transport"] == "bapi_article_detail_query"
    assert result["content_provenance"] == "binance_official_announcement"
    assert result["source_transport"] == "binance_first_party_public_web_bapi_undocumented"
    assert result["candidate_provenance"][0]["body_node_path"]
    assert result["candidate_provenance"][0]["event_phrase_match"] is True
    assert "extracted_text" in result


def test_raw_unparsed_bapi_body_string_is_not_parsed():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": "SHAZUSDT SOFIUSDT appears but this is not recognized JSON tree",
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == []
    assert result["symbol_parse_status"] == "not_attempted"
    assert result["symbol_parse_failed_reason"] == "bapi_body_schema_drift"


def test_unrelated_valid_symbol_in_bapi_disclaimer_is_ignored():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": '{"node":"root","child":[{"node":"text","text":"Risk warning: BTCUSDT may be volatile."}]}',
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == []


def test_bapi_body_reuses_existing_launch_time_parser():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": '{"node":"root","child":[{"node":"text","text":"Binance Futures will launch SHAZUSDT USDⓈ-Margined Perpetual Contract at 2026-07-21 13:30 (UTC)."}]}',
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SHAZUSDT"]
    assert result["symbol_launch_times_ms"]["SHAZUSDT"] == 1784631000000


def test_single_large_node_does_not_capture_disclaimer_symbol():
    payload = {
        "code": "000000",
        "data": {
            "code": "f43403ef11974998bc0f46420826577a",
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
            "body": '{"node":"root","child":[{"node":"text","text":"Binance Futures will launch SHAZUSDT USDⓈ-Margined Perpetual Contract at 2026-07-21 13:30 (UTC). Risk warning: BTCUSDT may be volatile."}]}',
        },
    }
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SHAZUSDT"]
```

**Step 2: Run failing parser tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: FAIL on missing BAPI parser.

**Step 3: Implement parser helpers**

Add helpers:

```text
extract_text_nodes_from_bapi_body(body, max_depth, max_nodes) -> list[dict]
extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols, title=None) -> dict
extract_launch_context_segments(text_nodes) -> list[dict]
```

Implementation requirements:

```text
Only parse body/contentJson if it is a JSON tree or dict/list already.
Recognize text nodes from keys like text/content only when within JSON tree.
Record node path for each candidate.
Filter candidate windows to launch context, will launch segment, contract list/table/list item.
Extract symbols only inside local launch segments, not from entire article/body node.
Ignore risk warning, disclaimer, footer, related articles, URLs, examples.
Return bapi_body_schema_drift if schema not recognized.
Return extracted_text for downstream launch-time parser.
Reuse existing extract_symbol_launch_times_ms(extracted_text, symbols).
```

Recommended minimal context filter:

```python
LEGAL_CONTEXT_RE = re.compile(r"launch|will\s+launch|perpetual\s+contracts?|usdⓈ-margined|usd-margined|usds-margined", re.IGNORECASE)
BLOCKED_CONTEXT_RE = re.compile(r"risk warning|disclaimer|footer|related articles|http://|https://", re.IGNORECASE)
```

Candidate provenance must include:

```text
body_node_path
segment_start
segment_end
local_text_span
event_phrase_distance
parser_context
section_classification
```

**Step 4: Run parser tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: PASS.

---

## 6. Add Append-Only BAPI Raw Payload Storage

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py`

**Step 1: Write failing storage tests**

Add:

```python
def test_write_detail_payload_append_only_includes_variant_timestamp_hash(tmp_path):
    result1 = write_detail_payload_append_only(
        root=tmp_path,
        timestamp_ms=1710000000000,
        source_article_id="f43403ef11974998bc0f46420826577a",
        detail_fetch_variant="bapi_article_detail_query",
        raw_bytes=b'{"data":{"body":"SHAZUSDT"}}',
        parsed_payload={"data": {"body": "SHAZUSDT"}},
        content_type="application/json",
        http_status=200,
    )
    result2 = write_detail_payload_append_only(
        root=tmp_path,
        timestamp_ms=1710000060000,
        source_article_id="f43403ef11974998bc0f46420826577a",
        detail_fetch_variant="bapi_article_detail_query",
        raw_bytes=b'{"data":{"body":"SOFIUSDT"}}',
        parsed_payload={"data": {"body": "SOFIUSDT"}},
        content_type="application/json",
        http_status=200,
    )
    assert result1["payload_path"] != result2["payload_path"]
    assert "f43403ef11974998bc0f46420826577a" in result1["payload_path"]
    assert "bapi_article_detail_query" in result1["payload_path"]
    assert (tmp_path / result1["payload_path"]).exists()
    assert (tmp_path / result2["payload_path"]).exists()


def test_write_detail_payload_append_only_rejects_bad_variant(tmp_path):
    with pytest.raises(ValueError, match="detail_fetch_variant_invalid"):
        write_detail_payload_append_only(
            root=tmp_path,
            timestamp_ms=1710000000000,
            source_article_id="abc",
            detail_fetch_variant="../bad",
            raw_bytes=b'{"x":1}',
            parsed_payload={"x": 1},
            content_type="application/json",
            http_status=200,
        )
```

**Step 2: Run failing storage tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py -q
```

Expected: FAIL on missing `write_detail_payload_append_only`.

**Step 3: Implement append-only writer**

Add function without breaking existing `write_detail_payload` tests:

```python
def write_detail_payload_append_only(root, timestamp_ms, source_article_id, detail_fetch_variant, raw_bytes, parsed_payload=None, content_type=None, http_status=None):
    # Hash raw_bytes exactly as received from the network.
    # Path: raw_payloads/announcement_detail/<articleCode>/<timestamp_ms>.<variant>.<raw_sha256>.<suffix>
```

Required behavior:

```text
safe articleCode or hashed fallback
safe variant: alnum/_/- only
atomic write via temp path then rename
same hash dedup allowed
never overwrite different hash revision
return payload_path/payload_size_bytes/raw_payload_sha256/canonical_json_sha256
```

Do not compute the audit hash from `json.dumps(parsed_payload)`. Canonical JSON hash is optional and separate from `raw_payload_sha256`.

**Step 4: Run storage tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py -q
```

Expected: PASS.

---

## 7. Split BAPI and Support Endpoint Health

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

**Step 1: Write failing health tests**

Add:

```python
def test_support_202_degraded_state_does_not_suppress_bapi_detail():
    now = 100_000
    health = update_detail_endpoint_health_by_source(
        {},
        now_ms=now,
        source="support_article_detail",
        result_code="http_202_empty",
        degraded_rate_threshold=0.8,
        degraded_min_sample=1,
        degraded_backoff_sec=900,
    )
    assert is_detail_source_degraded(health, "support_article_detail", now + 1) is True
    assert is_detail_source_degraded(health, "bapi_article_detail_query", now + 1) is False


def test_bapi_degraded_state_does_not_disable_support_fallback():
    now = 100_000
    health = update_detail_endpoint_health_by_source(
        {},
        now_ms=now,
        source="bapi_article_detail_query",
        result_code="http_503",
        degraded_rate_threshold=0.8,
        degraded_min_sample=1,
        degraded_backoff_sec=900,
    )
    assert is_detail_source_degraded(health, "bapi_article_detail_query", now + 1) is True
    assert is_detail_source_degraded(health, "support_article_detail", now + 1) is False


def test_bapi_illegal_parameter_is_article_specific_terminal_not_support_terminal():
    state = classify_detail_source_failure(
        source="bapi_article_detail_query",
        http_status=400,
        error="bapi_api_code_non_000000",
    )
    assert state["retryable"] is False
    assert state["terminal_reason"]
    assert state["support_fallback_allowed"] is True


def test_bapi_429_is_transient_and_updates_bapi_breaker_only():
    state = classify_detail_source_failure(
        source="bapi_article_detail_query",
        http_status=429,
        error="bapi_http_non_200",
    )
    assert state["retryable"] is True
    assert state["breaker_source"] == "bapi_article_detail_query"


def test_bapi_identity_mismatch_is_integrity_failure_with_support_fallback():
    state = classify_detail_source_failure(
        source="bapi_article_detail_query",
        http_status=200,
        error="bapi_article_identity_mismatch",
    )
    assert state["retryable"] is False
    assert state["integrity_alert"] is True
    assert state["support_fallback_allowed"] is True
```

**Step 2: Run failing health tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py -q
```

Expected: FAIL on missing helpers.

**Step 3: Implement source-specific health helpers**

Add:

```text
update_detail_endpoint_health_by_source(endpoint_health, now_ms, source, result_code, ...)
is_detail_source_degraded(endpoint_health, source, now_ms)
summarize_detail_source_health(endpoint_health, now_ms) -> {
    "bapi_detail_source_degraded": bool,
    "support_detail_source_degraded": bool,
    "all_detail_sources_degraded": bool,
}
classify_detail_source_failure(source, http_status, error) -> dict
```

Persist under:

```json
{
  "endpoint_health_by_source": {
    "bapi_article_detail_query": {...},
    "support_article_detail": {...}
  }
}
```

Backward compatibility:

```text
Keep existing endpoint_health and by_variant fields readable.
Do not delete legacy endpoint_health keys.
New source-specific state is authoritative for BAPI/support suppression.
Legacy `detail_endpoint_degraded_until_ms` remains for backward diagnostics only and must not suppress a healthy BAPI source.
```

**Step 4: Run scheduler tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py -q
```

Expected: PASS.

---

## 8. Integrate BAPI Source Into Runner

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Add fixture helper in tests**

Add local helper near existing fake fetch helpers:

```python
def _bapi_detail_payload(article_code, title, body_text):
    body = json.dumps({
        "node": "root",
        "child": [{"node": "text", "text": body_text}],
    })
    return {
        "code": "000000",
        "data": {
            "code": article_code,
            "id": 280581,
            "title": title,
            "body": body,
        },
    }
```

**Step 2: Write failing runner tests**

Add tests:

```text
test_no_symbol_title_uses_bapi_detail_before_support_fallback
test_bapi_detail_failure_falls_back_to_support_detail_paths
test_bapi_success_skips_support_and_respects_total_http_budget
test_bapi_and_support_requests_each_write_manifest_rows
test_bapi_manifest_contains_required_audit_fields
test_actual_http_request_count_matches_manifest_rows
test_logical_cycle_count_remains_separate_from_http_count
test_support_202_degraded_state_does_not_suppress_bapi_detail_in_runner
test_bapi_degraded_state_does_not_disable_support_fallback_in_runner
test_support_global_legacy_degraded_state_cannot_block_healthy_bapi_cycle
test_bapi_degraded_and_support_healthy_still_selects_article_cycle
test_all_sources_degraded_uses_existing_bounded_degraded_policy
test_detail_parsed_exchangeinfo_not_visible_enters_pending_validation_without_bapi_refetch
test_validation_pending_reenters_exchangeinfo_validation_queue
test_validation_pending_survives_restart
test_validation_pending_does_not_refetch_bapi
test_validation_pending_times_out_to_non_consumable_diagnostic
test_partial_exchangeinfo_visibility_does_not_emit_incomplete_multi_symbol_event
test_later_full_visibility_emits_once_without_duplicate_symbols
test_bapi_failure_can_reach_all_existing_support_variants_when_budget_allows
test_http_budget_exhaustion_defers_remaining_variant_without_deleting_it
test_pre_hotfix_article_fixture_not_consumable_by_stage1_5f
test_new_post_watermark_bapi_event_can_reach_1_5f_formal_acceptance
test_new_root_does_not_import_old_scheduler_pending_state
```

Minimum assertion set for `test_no_symbol_title_uses_bapi_detail_before_support_fallback`:

```python
manifest_rows = _read_jsonl_files(output_root / "request_manifest")
bapi_rows = [r for r in manifest_rows if r.get("detail_fetch_variant") == "bapi_article_detail_query"]
support_rows = [r for r in manifest_rows if r.get("detail_fetch_variant") in {"primary", "detail_path_fallback"}]
assert len(bapi_rows) == 1
assert support_rows == []
assert bapi_rows[0]["payload_trusted"] is True
assert bapi_rows[0]["source_transport"] == "binance_first_party_public_web_bapi_undocumented"

events = _read_jsonl_files(output_root / "events")
assert events[0]["symbols"] == ["SHAZUSDT", "SOFIUSDT"]
assert events[0]["symbol_launch_times_ms"]
assert events[0]["symbol_effective_launch_times_ms"]
assert events[0]["evidence_source"] == "official_article_body_confirmed"
assert events[0]["detail_transport"] == "bapi_article_detail_query"
assert events[0]["trade_signal_allowed"] is False
assert events[0]["paper_trading_allowed"] is False
assert events[0]["live_trading_allowed"] is False
assert events[0]["execution_engine_allowed"] is False
```

**Step 3: Run failing runner tests**

Run selected tests first:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_no_symbol_title_uses_bapi_detail_before_support_fallback \
  -q
```

Expected: FAIL because runner does not call BAPI.

**Step 4: Implement runner integration**

Modify the detail fetch section so one logical cycle evaluates source variants in order:

```text
source variant 1: bapi_article_detail_query
source variants 2..N: existing support fallback URLs
```

Runner invariants:

```text
detail_budget_remaining decreases once per logical article cycle.
detail_http_requests_remaining decreases once per actual HTTP request.
MAX_DETAIL_SOURCE_VARIANTS_PER_CYCLE caps BAPI + support variants.
Source variant count does not replace HTTP budget; it only caps variant traversal order.
BAPI trusted success ends cycle and skips support.
BAPI failure writes manifest and falls through to support unless HTTP budget exhausted.
Support degraded does not suppress BAPI.
BAPI degraded does not suppress support fallback.
Legacy global support degraded does not suppress BAPI when BAPI source health is usable.
All detail sources degraded uses the existing bounded degraded policy.
Old support fallback still classifies 202 as support_detail_http_202_empty / retryable.
```

Recommended minimal refactor:

```text
Create small internal helper in runner:
attempt_detail_source_variant(...)

Do not rewrite the whole runner.
Keep existing support path handling intact as much as possible.
```

Event metadata for BAPI success:

```python
{
    "evidence_source": "official_article_body_confirmed",
    "detail_transport": "bapi_article_detail_query",
    "symbol_extraction_source": "bapi_article_body",
    "content_provenance": "binance_official_announcement",
    "source_transport": "binance_first_party_public_web_bapi_undocumented",
    "detail_fetch_variant": "bapi_article_detail_query",
    "detail_payload_trusted": True,
    "symbol_validation_status": "validated_by_exchangeinfo",
}
```

If BAPI parsed symbols but exchangeInfo does not yet show them:

```python
state["detail_parse_status"] = "parsed"
state["parsed_candidate_symbols"] = parsed_symbols
state["symbol_validation_status"] = "pending_exchangeinfo_visibility"
state["pending_reason"] = "exchangeinfo_symbol_not_yet_visible"
state["detail_fetch_status"] = "success"
state["detail_retryable"] = False
state["exchangeinfo_validation_retryable"] = True
state["next_exchangeinfo_validation_at_ms"] = now_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_RETRY_INTERVAL_SEC * 1000
state["last_exchangeinfo_validation_at_ms"] = now_ms
state["exchangeinfo_validation_attempt_count"] = state.get("exchangeinfo_validation_attempt_count", 0) + 1
```

Do not re-fetch BAPI in that state; retry exchangeInfo validation only.

Multi-symbol articles use all-or-none emission in first version:

```text
If any parsed candidate remains pending exchangeInfo visibility, emit no consumable event.
When all candidates validate later, emit the full article event exactly once.
```

The BAPI parser's `extracted_text` must flow into existing launch-time handling:

```python
state["symbol_launch_times_ms"] = extraction_res.get("symbol_launch_times_ms", {})
effective_launch = build_effective_launch_times(
    symbols=extraction_res["symbols"],
    symbol_onboard_times_ms=state["symbol_onboard_times_ms"],
    symbol_launch_times_ms=state["symbol_launch_times_ms"],
)
state["symbol_effective_launch_times_ms"] = effective_launch["symbol_effective_launch_times_ms"]
```

**Step 5: Run runner tests incrementally**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_no_symbol_title_uses_bapi_detail_before_support_fallback \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_bapi_detail_failure_falls_back_to_support_detail_paths \
  -q
```

Expected: PASS.

Then run all 1.5D runner tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: PASS.

---

## 9. Add Summary Metrics

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing summary test**

Add:

```python
def test_summary_includes_bapi_detail_source_metrics():
    summary = build_smoke_summary(
        events=[],
        request_manifest=[],
        heartbeat_rows=[],
        counters={
            "bapi_detail_request_count": 1,
            "bapi_detail_success_count": 1,
            "bapi_detail_trusted_payload_count": 1,
            "bapi_symbol_parse_success_count": 1,
            "bapi_symbol_validation_success_count": 1,
        },
        # keep existing required args exactly as current helper expects
    )
    assert summary["bapi_detail_request_count"] == 1
    assert summary["bapi_detail_success_count"] == 1
    assert summary["bapi_detail_trusted_payload_count"] == 1
    assert summary["bapi_symbol_parse_success_count"] == 1
    assert summary["bapi_symbol_validation_success_count"] == 1
```

Use the exact existing `build_smoke_summary` signature from the current test file.

**Step 2: Add metrics in summary builder**

Add keys:

```python
"bapi_detail_request_count": counters.get("bapi_detail_request_count", 0),
"bapi_detail_success_count": counters.get("bapi_detail_success_count", 0),
"bapi_detail_trusted_payload_count": counters.get("bapi_detail_trusted_payload_count", 0),
"bapi_detail_schema_drift_count": counters.get("bapi_detail_schema_drift_count", 0),
"bapi_detail_identity_mismatch_count": counters.get("bapi_detail_identity_mismatch_count", 0),
"bapi_detail_rate_limited_count": counters.get("bapi_detail_rate_limited_count", 0),
"bapi_to_support_fallback_count": counters.get("bapi_to_support_fallback_count", 0),
"bapi_symbol_parse_success_count": counters.get("bapi_symbol_parse_success_count", 0),
"bapi_symbol_validation_pending_count": counters.get("bapi_symbol_validation_pending_count", 0),
"bapi_symbol_validation_success_count": counters.get("bapi_symbol_validation_success_count", 0),
"support_fallback_success_count": counters.get("support_fallback_success_count", 0),
"detail_http_manifest_mismatch_count": counters.get("detail_http_manifest_mismatch_count", 0),
"bapi_payload_revision_count": counters.get("bapi_payload_revision_count", 0),
"bapi_payload_hash_change_count": counters.get("bapi_payload_hash_change_count", 0),
```

If long-running summary metrics must survive process restart, derive cumulative BAPI request/success/fallback/revision counts from request manifest and persisted scheduler state rather than process-local counters only.

**Step 3: Run summary tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py -q
```

Expected: PASS.

---

## 10. Regression Fixtures

**Files:**
- Create: `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_f434_fixture.json`
- Create: `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_d0833_fixture.json`
- Create: `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_6cbb_fixture.json`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Create frozen and minimized fixtures**

Fixture source must be explicit.

Required fixture classes:

```text
real_frozen_fixture:
  captured from live BAPI discovery response and committed as static test data;
  no pytest live network calls.

minimized_synthetic_fixture:
  hand-minimized from discovery evidence;
  must include data_quality = manually_constructed_minimal_fixture.
```

At least one fixture must preserve a real or real-structured launch schedule/time section, not just a simplified symbol sentence.

Example fixture shape:

```json
{
  "data_quality": "manually_constructed_minimal_fixture",
  "source_basis": "2026-07-22 BAPI discovery evidence; symbol list and title copied from observed response",
  "code": "000000",
  "data": {
    "code": "f43403ef11974998bc0f46420826577a",
    "id": 280581,
    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
    "body": "{\"node\":\"root\",\"child\":[{\"node\":\"text\",\"text\":\"Binance Futures will launch SHAZUSDT USDⓈ-Margined Perpetual Contract at 2026-07-21 13:30 (UTC), SOFIUSDT USDⓈ-Margined Perpetual Contract at 2026-07-21 13:45 (UTC), PANWUSDT USDⓈ-Margined Perpetual Contract at 2026-07-21 14:00 (UTC), and PENGUSDT USDⓈ-Margined Perpetual Contract at 2026-07-21 14:15 (UTC).\"}]}"
  }
}
```

**Step 2: Add fixture replay tests**

Add:

```python
def test_bapi_f434_fixture_extracts_expected_symbols():
    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_f434_fixture.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SHAZUSDT", "SOFIUSDT", "PANWUSDT", "PENGUSDT"]
    assert set(result["symbol_launch_times_ms"]) == {"SHAZUSDT", "SOFIUSDT", "PANWUSDT", "PENGUSDT"}


def test_bapi_d0833_fixture_extracts_expected_symbols():
    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_d0833_fixture.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["GEVUSDT", "VRTUSDT", "SNOWUSDT", "APPUSDT"]


def test_bapi_6cbb_fixture_extracts_spcxusd1():
    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_6cbb_fixture.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"] == ["SPCXUSD1"]


def test_real_frozen_fixture_preserves_expected_schedule_structure():
    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_f434_real_frozen_fixture.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, max_symbols=30)
    assert result["symbols"]
    assert result["extracted_text"]
    assert "UTC" in result["extracted_text"]
```

**Step 3: Run parser fixture tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: PASS.

---

## 11. Cross-Stage 1.5F Admission Tests

**Files:**
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Test: existing 1.5F loader/admission test file discovered by `find tests -type f | grep stage1_5f`

**Step 1: Identify 1.5F admission/loader entrypoint**

Run:

```bash
grep -RIn "events_accepted\\|pre_watermark\\|age_exceeded\\|live_depth_evidence_basis\\|formal" \
  tests/research/external_signal_shadow tests/scripts/external_signal_shadow | grep stage1_5f | head -n 120
```

Expected:

```text
Find the existing 1.5F loader/admission test pattern that reads 1.5D event rows and writes events_accepted/events_rejected.
```

**Step 2: Add historical fixture rejection test**

Use f434/d083 frozen fixture to prove parser recovery does not weaken formal evidence boundaries:

```text
1. Generate a recovered 1.5D event row from old article fixture.
2. Feed it into the existing 1.5F admission path with current watermark/age settings.
3. Assert it is not written to events_accepted.
4. Assert rejection reason is pre_watermark or age_exceeded, depending on fixture timestamps.
```

Required test name:

```text
test_pre_hotfix_bapi_recovered_article_does_not_become_formal_1_5f_evidence
```

**Step 3: Add synthetic post-watermark formal acceptance test**

Create a synthetic article that is post-watermark and has:

```text
trusted BAPI body
symbol list
per-symbol launch time
exchangeInfo validation success
symbol_effective_launch_times_ms
all safety flags false
```

Feed the generated 1.5D event into 1.5F admission.

Required assertions:

```text
events_accepted row exists
live_depth_evidence_basis = announcement_and_launch_time
announcement_time_capture_evidence_allowed = true
launch_time_depth_evidence_allowed = true
depth_observation_started = true or active_observation_count increments, depending on current 1.5F test fixture
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

Required test name:

```text
test_new_post_watermark_bapi_event_can_reach_1_5f_formal_acceptance
```

**Step 4: Run cross-stage tests**

Run only the new/modified tests first:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_pre_hotfix_bapi_recovered_article_does_not_become_formal_1_5f_evidence \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_new_post_watermark_bapi_event_can_reach_1_5f_formal_acceptance \
  -q
```

Expected: PASS.

---

## 12. Safety and Regression Verification

**Files:**
- All modified files.

**Step 1: Run targeted 1.5D suite**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: PASS.

**Step 2: Run existing 1.5F/1.5G guard tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review.py \
  -q
```

Expected: PASS. If any file does not exist in the current repo, document the missing file and run the available 1.5F/1.5G tests discovered by:

```bash
find tests -type f | grep -E 'stage1_5f|stage1_5g' | sort
```

**Step 3: Production safety grep**

Run:

```bash
grep -RInE 'paper_trading_allowed[[:space:]]*[:=][[:space:]]*True|live_trading_allowed[[:space:]]*[:=][[:space:]]*True|execution_engine_allowed[[:space:]]*[:=][[:space:]]*True|trade_signal_allowed[[:space:]]*[:=][[:space:]]*True' \
  configs src scripts || true
```

Expected: no output.

Run:

```bash
grep -RInE '\bAuthorization\b|X-MBX-APIKEY|Cookie|apiKey|secret' \
  src/research/external_signal_shadow scripts/external_signal_shadow configs/base.py || true
```

Expected: no new BAPI detail code sends private/auth/account headers. Existing unrelated config references must be manually confirmed as unrelated.

**Step 4: Static diff check**

Run:

```bash
git diff --check
```

Expected: no output.

---

## 13. Deployment Plan After Code Review

Do not deploy until implementation code review passes.

**Files:**
- Update if needed: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

**Step 1: Use a new root suffix**

New deployment root suffix must be:

```text
_7d_bapi_article_detail_source_hotfix
```

Do not write new scheduler semantics into old roots:

```text
_7d_detail_endpoint_fallback_hotfix
_7d_detail_retry_overdue_starvation_hotfix
```

**Step 2: Stop old tmux sessions explicitly**

Use session names actually present in `tmux ls`. Minimum kill list should include old and new names:

```bash
tmux kill-session -t stage1_5d_continuous_7d_detail_endpoint_fallback_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5d_continuous_7d_detail_retry_overdue_starvation_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5d_continuous_7d_bapi_article_detail_source_hotfix 2>/dev/null || true

tmux kill-session -t stage1_5f_live_depth_observer_7d_detail_endpoint_fallback_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_observer_7d_detail_retry_overdue_starvation_hotfix 2>/dev/null || true
tmux kill-session -t stage1_5f_live_depth_observer_7d_bapi_article_detail_source_hotfix 2>/dev/null || true
```

**Step 3: Start new 1.5D and 1.5F sessions**

Use the same reviewed command pattern from the 1.5F review doc, changing only root suffix and tmux names.

**Step 4: Immediate smoke checks**

Run after first 2-3 polls:

```bash
export STAGE1_5D_EVENTS_OUT="$(find data/external_signal_shadow/stage1_5d -maxdepth 1 -type d -name 'live_event_source_continuous_*_7d_bapi_article_detail_source_hotfix' | sort | tail -n 1)"
export STAGE1_5F_OUT="$(find data/external_signal_shadow/stage1_5f -maxdepth 1 -type d -name 'live_depth_observer_*_7d_bapi_article_detail_source_hotfix' | sort | tail -n 1)"

date -u
tmux ls
ps -ef | grep -E "run_stage1_5d_live_event_source_smoke_collector|run_stage1_5f_live_depth_observer" | grep -v grep

cat "$STAGE1_5D_EVENTS_OUT/binance_futures_launch_smoke_summary.json" 2>/dev/null | .venv/bin/python -m json.tool || true
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" 2>/dev/null | .venv/bin/python -m json.tool || true
```

**Step 5: BAPI-specific smoke checks**

Run:

```bash
find "$STAGE1_5D_EVENTS_OUT/request_manifest" -type f 2>/dev/null \
  -exec grep -HIn 'announcement_detail_bapi\|bapi_article_detail_query\|bapi_to_support_fallback' {} \; | tail -n 80

.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ['STAGE1_5D_EVENTS_OUT'])
summary_path = root / 'binance_futures_launch_smoke_summary.json'
print('summary_exists', summary_path.exists())
if summary_path.exists():
    s = json.loads(summary_path.read_text())
    for k in [
        'bapi_detail_request_count',
        'bapi_detail_success_count',
        'bapi_detail_trusted_payload_count',
        'bapi_to_support_fallback_count',
        'bapi_symbol_parse_success_count',
        'bapi_symbol_validation_success_count',
        'detail_endpoint_degraded_active',
    ]:
        print(k, s.get(k))
PY
```

Expected:

```text
No crashes.
Summary parses as JSON.
BAPI fields exist.
If no new no-symbol event appears, bapi counts may remain 0; that is acceptable.
```

**Step 6: Regression-only old article probe**

Old articles may be used only as parser/source smoke, not as formal 1.5F evidence.

If using a manual probe, write output under a clearly separate root:

```text
data/external_signal_shadow/stage1_5d_probe/bapi_article_detail_source_<timestamp>
```

Never merge probe output into production 1.5D/1.5F roots.

---

## 14. Completion Criteria

Implementation is complete only when all are true:

```text
1. All targeted 1.5D tests pass.
2. Available 1.5F/1.5G guard tests pass.
3. No BAPI test performs live network calls.
4. BAPI trusted success emits official_article_body_confirmed + bapi_article_detail_query metadata.
5. BAPI trusted success preserves extracted_text, symbol_launch_times_ms, and symbol_effective_launch_times_ms.
6. New post-watermark BAPI event can reach formal 1.5F accepted evidence.
7. Historical recovered fixtures cannot become formal 1.5F evidence.
8. BAPI failure falls back to support detail path.
9. Support 202 degraded does not suppress BAPI detail.
10. BAPI degraded does not suppress support fallback.
11. All detail sources degraded uses existing bounded degraded policy.
12. exchangeInfo validation-pending survives restart, does not refetch BAPI, and times out to non-consumable diagnostics.
13. Multi-symbol articles emit all-or-none and never duplicate symbols after later full validation.
14. Raw BAPI payload storage is append-only and hashes original response bytes.
15. Each actual HTTP request maps to exactly one request_manifest row and one detail_http_request_count increment.
16. No BAPI pytest test performs live network calls.
17. No paper/live/execution/trade flags become true.
```

---

## 15. Commit Guidance

Use small commits:

```bash
git add configs/base.py tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py
git commit -m "config: add stage1.5d bapi detail source limits"

git add src/research/external_signal_shadow/stage1_5d_live_event_source_client.py tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py
git commit -m "feat: add stage1.5d bapi article detail client"

git add src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py tests/fixtures/external_signal_shadow/stage1_5d/*bapi_article_detail*.json
git commit -m "feat: parse stage1.5d bapi article body with provenance"

git add src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py
git commit -m "feat: store stage1.5d detail payloads append-only"

git add src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py
git commit -m "feat: split stage1.5d detail source health"

git add scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py
git commit -m "feat: prefer bapi article detail source in stage1.5d"
```

If implementation is done in one session and review prefers fewer commits, squash only after tests and review pass. Do not amend existing unrelated commits unless explicitly requested.
