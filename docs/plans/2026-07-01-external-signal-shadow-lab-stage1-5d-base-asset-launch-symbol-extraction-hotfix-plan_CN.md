# Stage 1.5D Base-Asset Launch Symbol Extraction Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 Binance futures launch 标题/详情只出现 base asset（例如 `BTCU and ETHU`）时 Stage 1.5D 仍输出 `symbols=[]`，导致 Stage 1.5F 无法启动 live depth observation 的漏采问题。

**Architecture:** 在现有 Stage 1.5D detail fallback 之上增加一个更窄的 base-asset-only fallback。优先抽取原文完整 `XXXUSDT/XXXUSDC`；只有在 futures launch 且 title/detail 明确处于 `USDⓈ-Margined/USDS-Margined/USD-M ... Perpetual Contract(s)` 语境、且没有完整合约 symbol 时，才生成 base-derived candidate。base-derived candidate 必须经 Binance USD-M public `exchangeInfo` 验证存在后才 emit parsed event；未验证候选不能伪装成普通 detail extraction。detail fetch 必须支持 raw JSON/HTML/TXT 持久化；事件时间语义必须保留第一次发现时间，不能用 detail 成功时间伪造新事件。

**Tech Stack:** Python 3.12, pytest, stdlib `urllib`, existing Stage 1.5D parser/client/storage/runner, JSONL artifacts, `configs/base.py` centralized thresholds.

---

## 0. Root Cause And Safety Boundaries

**Observed production symptom:**

```text
releaseDate = 2026-06-30T14:45:02.782Z
code = 25da4614ffff435fa28544b27fd33a39
title = Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)
Stage 1.5D event row symbols = []
Stage 1.5F post_watermark_events_accepted = 0
```

**Confirmed local reproduction:**

```text
extract_futures_launch_symbols(title) -> []
extract_symbols_from_detail_payload("BTCU and ETHU Perpetual Contracts") -> []
extract_symbols_from_detail_payload("BTCUUSDT and ETHUUSDT Perpetual Contracts") -> ["BTCUUSDT", "ETHUUSDT"]
```

**Root cause:**

```text
current extraction only matches full contract symbols ending in USDT/USDC.
BTCU / ETHU are base assets, not full contract symbols.
The current design intentionally avoided base_asset_plus_quote guessing, but this live Binance title shows a legitimate launch format that requires a bounded base-asset fallback.
```

**Safety boundaries:**

```text
scope = Stage 1.5D event-source symbol extraction only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
server_deployment = out_of_scope until local tests and review pass
```

This hotfix must not use current orderbook to prove historical feasibility. It only creates correct event-symbol rows so Stage 1.5F can observe future/live depth.


## Review Feedback Disposition

```text
decision = revised_for_required_fixes
validation_model = Stage 1.5D validates base-derived symbols with Binance USD-M public exchangeInfo before emitting parsed events
base_derived_symbols_unvalidated_emit_allowed = false
```

采纳的必须修正项：

```text
1. base-derived symbols must not be labeled as ordinary detail extraction.
2. USDⓈ/USDS/USD-M context alone is insufficient; derived candidates require exchangeInfo validation.
3. USDS-Margined / USDS-M / USD-Margined / USD-M variants must be accepted case-insensitively.
4. base-asset fallback must scan only short launch candidate windows, not whole HTML/detail pages.
5. emitted events need first_detected/detail_fetched/symbol_resolved/latency fields.
6. all 6 detail terminal/success detected_at_ms branches must preserve first_detected_at_ms.
7. detail fetch raw-payload change must be isolated to detail URL only; announcement list fetch remains JSON.
8. private IP validator fix remains required and the planned control-flow fix is valid.
```

Rejected/modified item：

```text
1. Do not use quote_derivation_source=unverified for emitted parsed events.
   Reason: Stage 1.5D is the event-symbol producer. Pushing unverified symbols downstream can cause avoidable 1.5F noise.
   Chosen path: validate derived candidate in 1.5D with public exchangeInfo; otherwise keep pending_validation or terminal_failed.
```

---

## Task 1: Add Failing Parser Test For BTCU/ETHU Base-Asset-Only Launch Title

**Files:**
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`
- Modify later: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`

**Step 1: Add failing tests**

Add:

```python
def test_extract_base_assets_from_usds_margined_launch_title():
    title = "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)"

    assert extract_futures_launch_base_assets(title) == ["BTCU", "ETHU"]


def test_base_asset_fallback_builds_unvalidated_usdt_candidates_in_usds_margined_launch_context():
    title = "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)"

    result = derive_symbol_candidates_from_base_assets_in_launch_context(title, max_symbols=30)

    assert result["symbols"] == ["BTCUUSDT", "ETHUUSDT"]
    assert result["symbol_extraction_source"] == "title_base_asset_derived"
    assert result["symbol_derivation_method"] == "base_asset_plus_quote"
    assert result["quote_derivation_source"] == "explicit_usdt_context"
    assert result["symbol_validation_status"] == "unverified"


def test_base_asset_fallback_does_not_derive_from_non_launch_or_risk_text():
    title = "Update on the Collateral Ratio Under Portfolio Margin and the Leverage & Margin Tiers of USDⓈ-M Perpetual Contracts"

    assert derive_symbol_candidates_from_base_assets_in_launch_context(title, max_symbols=30)["symbols"] == []


def test_base_asset_fallback_accepts_usds_margined_ascii_variant():
    title = "Binance Futures Will Launch USDS-Margined BTCU and ETHU Perpetual Contracts"

    assert derive_symbol_candidates_from_base_assets_in_launch_context(title, max_symbols=30)["symbols"] == ["BTCUUSDT", "ETHUUSDT"]


def test_base_asset_fallback_is_case_insensitive_for_launch_context():
    title = "Binance futures will launch usds-margined BTCU and ETHU perpetual contracts"

    assert derive_symbol_candidates_from_base_assets_in_launch_context(title, max_symbols=30)["symbols"] == ["BTCUUSDT", "ETHUUSDT"]
```

**Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_extract_base_assets_from_usds_margined_launch_title \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_base_asset_fallback_builds_unvalidated_usdt_candidates_in_usds_margined_launch_context \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_base_asset_fallback_does_not_derive_from_non_launch_or_risk_text \
  -q
```

Expected: FAIL because helper functions do not exist.

---

## Task 2: Implement Conservative Base-Asset Extraction Helpers

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Rules:**

Only derive candidates if all gates pass:

```text
1. classify_event_type(text) == futures_contract_launch, case-insensitive.
2. text has a short candidate launch window containing launch/will launch, a USDⓈ/USDS/USD-M margin phrase, and Perpetual Contract(s).
3. supported margin phrases include USDⓈ-Margined, USDⓈ-M, USDS-Margined, USDS-M, USD-Margined, USD-M, case-insensitive.
4. existing full-symbol extraction returned []. Full `XXXUSDT/XXXUSDC` always wins.
5. extracted token is uppercase alnum, 2-20 chars.
6. token is not a stopword: BINANCE, FUTURES, WILL, LAUNCH, USD, USDT, USDC, USDS, MARGINED, PERPETUAL, CONTRACT, CONTRACTS, AND, MULTIPLE, TRADFI, TIME, SETTLEMENT, ASSET, UNDERLYING, MARGIN, TIER, WARNING.
7. base fallback scans only candidate windows <= 500 chars, never the full joined HTML/detail page.
```

For explicit USDⓈ/USDS/USD-M context, the parser may build candidate `BASE + "USDT"`, but this is only an unvalidated candidate. It must not be emitted as parsed until Binance USD-M public `exchangeInfo` confirms the candidate symbol exists.

**Implementation sketch:**

```python
BASE_ASSET_STOPWORDS = {...}


def extract_futures_launch_base_assets(text: str) -> list[str]:
    if classify_event_type(text) != "futures_contract_launch":
        return []
    if extract_futures_launch_symbols(text):
        return []
    if not _has_usds_margined_launch_context(text):
        return []

    # Prefer phrase between "USDⓈ-Margined" and "Perpetual".
    segment = _extract_between_margin_and_perpetual(text)
    tokens = re.findall(r"\b[A-Z][A-Z0-9]{1,19}\b", segment)
    return _dedupe([t for t in tokens if t not in BASE_ASSET_STOPWORDS])


def derive_symbol_candidates_from_base_assets_in_launch_context(text: str, max_symbols: int) -> dict:
    bases = extract_futures_launch_base_assets(text)
    symbols = [f"{base}USDT" for base in bases[:max_symbols]]
    return {
        "symbols": symbols,
        "symbol_extraction_source": "title_base_asset_derived",
        "symbol_derivation_method": "base_asset_plus_quote" if symbols else None,
        "quote_derivation_source": "explicit_usdt_context" if symbols else None,
        "symbol_validation_status": "unverified" if symbols else None,
    }
```

**Step 2: Verify parser tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: PASS.

---

## Task 3: Extend Detail Payload Extraction With Base-Asset Fallback

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Add failing tests**

Add:

```python
def test_detail_base_asset_fallback_derives_symbols_when_detail_has_base_assets_only():
    detail = {
        "data": {
            "body": "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts."
        }
    }

    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["BTCUUSDT", "ETHUUSDT"]


def test_detail_prefers_full_symbols_over_base_asset_fallback():
    detail = "Binance Futures will launch USDⓈ-Margined BTCUUSDT and ETHUUSDT Perpetual Contracts."

    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["BTCUUSDT", "ETHUUSDT"]


def test_base_asset_fallback_ignores_tokens_outside_launch_sentence_window():
    detail = """
    Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts.
    Risk Warning: PORTFOLIO MARGIN TIER SETTLEMENT ASSET LEVERAGE COLLATERAL RATIO.
    """

    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["BTCUUSDT", "ETHUUSDT"]


def test_base_asset_fallback_ignores_table_labels_launch_time_settlement_asset():
    detail = """
    Launch Time: 2026-07-01
    Underlying Asset: BTCU and ETHU
    Settlement Asset: USDT
    Margin Tier: Portfolio Margin update
    """

    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == []
```

**Step 2: Implement**

Modify `extract_symbols_from_detail_payload()` or add a companion helper `extract_symbol_candidates_from_detail_payload()`:

```text
1. First pass: existing full-symbol regex over all text snippets. Full-symbol regex may scan the whole bounded detail payload.
2. If full symbols found, return them with:
   symbol_extraction_source = detail
   symbol_derivation_method = none
   symbol_validation_status = validated_by_exact_text
3. If no full symbols are found, identify candidate windows only. A candidate window must be <= 500 chars and contain launch/will launch, USDⓈ/USDS/USD-M margin phrase, and Perpetual Contract(s).
4. Run base-asset derivation only on those candidate windows, not on the full joined HTML page.
5. If title is available, include title as the first candidate window so JSON detail bodies that omit the headline still preserve context.
6. Return derived candidates with:
   symbol_extraction_source = detail_base_asset_derived
   symbol_derivation_method = base_asset_plus_quote
   quote_derivation_source = explicit_usdt_context
   symbol_validation_status = unverified
```

Bound full-symbol scan text length to avoid pathological pages:

```text
max_joined_text_chars = 100_000
max_base_derivation_window_chars = 500
```

Do not derive base assets from generic table labels such as `Launch Time`, `Underlying Asset`, `Settlement Asset`, `Risk Warning`, `Margin Tier` unless they are inside a valid launch candidate window.

**Step 3: Verify**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: PASS.


---

## Task 4: Validate Base-Derived Candidates With Binance USD-M ExchangeInfo Before Emit

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Rule:**

```text
full XXXUSDT/XXXUSDC exact text matches may be emitted as parsed without extra derivation validation.
base-derived candidates must be confirmed by Binance USD-M public exchangeInfo before emitting parsed event rows.
If exchangeInfo is temporarily unavailable, keep the article in pending_validation / retry state; do not emit parsed symbols.
If exchangeInfo confirms candidate missing after retry/max-age, emit terminal_failed with symbol_validation_status=rejected.
```

**Required emitted metadata for validated base-derived symbols:**

```json
{
  "symbol_extraction_source": "detail_base_asset_derived",
  "symbol_derivation_method": "base_asset_plus_quote",
  "quote_derivation_source": "exchange_info",
  "symbol_validation_status": "validated",
  "symbol_parse_status": "parsed"
}
```

For title-only base derivation, use:

```json
{
  "symbol_extraction_source": "title_base_asset_derived",
  "symbol_derivation_method": "base_asset_plus_quote",
  "quote_derivation_source": "exchange_info",
  "symbol_validation_status": "validated",
  "symbol_parse_status": "parsed"
}
```

**Step 1: Add failing tests**

Add:

```python
def test_base_asset_derived_symbol_requires_exchange_info_validation(tmp_path):
    # list/detail yields BTCUUSDT and ETHUUSDT candidates from BTCU/ETHU base assets.
    # fake exchangeInfo contains BTCUUSDT and ETHUUSDT.
    # assert emitted event has symbols and symbol_validation_status == "validated".
    # assert symbol_extraction_source == "detail_base_asset_derived".


def test_base_asset_derived_symbol_not_emitted_when_exchange_info_missing(tmp_path):
    # list/detail yields BTCUUSDT and ETHUUSDT candidates.
    # fake exchangeInfo does not contain them.
    # assert no parsed event with symbols is emitted.
    # assert terminal or pending diagnostic uses symbol_validation_status == "rejected" or pending_validation.
```

**Step 2: Implement exchangeInfo validation**

Use existing public-readonly `fetch_public_json()` for Binance USD-M `exchangeInfo`. This is not a detail page, so it remains JSON.

Implementation requirements:

```text
1. Compute active_symbols once per poll before both first_bar_queue checks and detail_retry_state validation.
2. active_symbols is a read-only per-poll cache shared by both consumers; neither first_bar nor detail validation may mutate it.
3. Do not independently fetch exchangeInfo twice in the same poll for first_bar and base-derived validation.
4. Treat exchangeInfo network failure as transient pending_validation, not terminal parse failure on first attempt.
5. Only validate candidate symbols against USD-M perpetual TRADING symbols.
6. Do not query private endpoints or account endpoints.
7. Keep request manifest rows for exchangeInfo validation and reuse the same manifest evidence if exchangeInfo was fetched once for the poll.
```

Required ordering inside runner poll loop:

```text
1. Fetch and parse announcement list.
2. Build/refresh per-poll active_symbols cache from exchangeInfo if either first_bar_queue or base-derived validation needs it.
3. Process detail_retry_state base-derived validation using active_symbols.
4. Process first_bar_queue using the same active_symbols.
```

If implementation chooses to move existing first_bar exchangeInfo fetch earlier, preserve current first_bar behavior and tests.

**Step 3: Verify runner tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: PASS.
---

## Task 5: Fix Live Detail Fetch To Persist Raw JSON/HTML/TXT, Not Only JSON

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Problem:**

Current live detail fallback uses `fetch_public_json()`, which does `json.loads(content)`. Binance support article detail pages may be HTML. A JSON-only detail fetch can fail even when useful detail text is available.

**Step 1: Add client test for raw text fetch**

Add a new helper test:

```python
def test_fetch_public_payload_returns_raw_text_without_json_parse():
    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return "https://www.binance.com/en/support/announcement/abc"
        def read(self): return b"<html>BTCU and ETHU Perpetual Contracts</html>"

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload("https://www.binance.com/en/support/announcement/abc", live_public_readonly=True)

    assert result["ok"] is True
    assert result["payload"] == "<html>BTCU and ETHU Perpetual Contracts</html>"
    assert result["payload_size_bytes"] > 0
```

**Step 2: Implement `fetch_public_payload()`**

In client module, add public-readonly raw payload fetch:

```python
def fetch_public_payload(url: str, live_public_readonly: bool, timeout_sec: float = 10.0, retry_budget: int = 0) -> dict:
    """Fetch public readonly payload as text, without forcing JSON parse."""
```

Requirements:

```text
1. Require live_public_readonly.
2. Reuse allowlist host validation.
3. Revalidate final_url host.
4. Return raw decoded text payload.
5. Return payload_size_bytes, http_status, final_url, error.
6. Do not parse JSON.
```

Do not replace `fetch_public_json()` for announcement list, exchangeInfo, fapi, or kline endpoints.

Forbidden:

```text
Do not switch the announcement list query endpoint to fetch_public_payload().
The list endpoint must continue to use fetch_public_json() so schema/row_count behavior remains unchanged.
```

**Step 3: Update runner detail path**

In `run_stage1_5d_live_event_source_smoke_collector.py`, for detail URL only:

```text
use fetch_public_payload(), not fetch_public_json()
```

Fixture `detailPayload` still works as dict/string/bytes.

**Step 4: Add runner test with HTML detail payload**

Add:

```python
def test_runner_live_detail_html_payload_extracts_base_asset_symbols(tmp_path):
    # list payload has BTCU/ETHU title with no full symbols
    # fake detail fetch returns html text containing same title
    # fake exchangeInfo contains BTCUUSDT and ETHUUSDT
    # expected event symbols = ["BTCUUSDT", "ETHUUSDT"]
    # expected payload_path endswith .html or .txt


def test_announcement_list_fetch_still_uses_fetch_public_json_not_raw_payload(tmp_path):
    # mock fetch_public_json for article/list/query and exchangeInfo
    # mock fetch_public_payload only for support/announcement detail URL
    # assert list query was never sent to fetch_public_payload
```

**Step 5: Verify**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: PASS.

---

## Task 6: Preserve First Detection Timestamp For Detail-Retry Emitted Events

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Problem:**

When detail retry succeeds later, current runner emits `detected_at_ms=now_ms`. That shifts event time forward and can distort Stage 1.5F age gate / watermark semantics.

**Rule:**

For all events emitted from `detail_retry_state`, `detected_at_ms` and `first_detected_at_ms` must equal `state["first_detected_at_ms"]`. Terminal failed rows should also preserve `first_detected_at_ms`.

Every detail-resolution emitted row must include:

```json
{
  "first_detected_at_ms": 0,
  "detail_fetched_at_ms": null,
  "symbol_resolved_at_ms": null,
  "symbol_resolution_latency_ms": null
}
```

For detail success with symbols:

```text
detail_fetched_at_ms = fetch attempt timestamp
symbol_resolved_at_ms = timestamp when symbol parsing/validation completes
symbol_resolution_latency_ms = symbol_resolved_at_ms - first_detected_at_ms
```

Stage 1.5F age gate must continue to use `first_detected_at_ms` / `detected_at_ms`, not `symbol_resolved_at_ms`.

**Step 1: Add failing test**

Add:

```python
def test_detail_retry_success_preserves_first_detected_at_ms(tmp_path):
    # poll 1: list sees article, detail returns 503
    # poll 2: same article, detail succeeds
    # assert emitted event["detected_at_ms"] equals first poll detected_at_ms, not second poll time
    # assert first_detected_at_ms == detected_at_ms
    # assert detail_fetched_at_ms >= first_detected_at_ms
    # assert symbol_resolved_at_ms >= detail_fetched_at_ms
    # assert symbol_resolution_latency_ms >= 0


def test_detail_terminal_failed_paths_preserve_first_detected_at_ms(tmp_path):
    # cover at least max-retries or max-age terminal branch
    # assert terminal failed event detected_at_ms == first_detected_at_ms
```

Use monkeypatch/time or compare against first heartbeat `poll_started_at_ms`.

**Step 2: Implement**

Replace all 6 `detected_at_ms=now_ms` occurrences inside the `detail_retry_state` processing block with:

```python
detected_at_ms=state["first_detected_at_ms"]
```

Required branches:

```text
1. max-age expiry terminal path
2. max-retries exhausted terminal path
3. URL missing/not_allowlisted terminal path
4. final_url redirect rejection terminal path
5. detail success with symbols path
6. detail success but symbols empty terminal path
```

Also add metadata fields in every branch:

```text
first_detected_at_ms
symbol_resolved_at_ms
detail_fetched_at_ms when a detail request was attempted, else null
symbol_resolution_latency_ms when symbol_resolved_at_ms exists, else null
```

Do not change title-symbol normal path except adding optional compatibility-safe diagnostics if desired.

**Step 3: Verify runner tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: PASS.

---

## Task 7: Add Manifest Rows For Failed Detail Requests

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Goal:** Make detail failures auditable, not only counted.

**Step 1: Add failing test**

Add:

```python
def test_failed_detail_request_writes_manifest_error_row(tmp_path):
    # detail fetch returns ok=false, http_status=503, error="temporary"
    # assert request_manifest has source_type announcement_detail, http_status 503, error temporary,
    # payload_size_bytes 0, response_payload_hash/payload_sha256 null or absent by documented choice
```

**Step 2: Implement manifest append helper**

Add local helper inside runner or storage:

```python
def _append_detail_request_manifest(...):
    ...
```

Required fields for every detail attempt:

```text
request_id
source_type = announcement_detail|fixture_detail
symbol = ALL
url
final_url
http_status
error
fetched_at_ms
payload_size_bytes
payload_sha256 = null when no payload
payload_path = null when no payload
parser_version
symbol_extraction_version
```

**Step 3: Verify**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: PASS.

---

## Task 8: Fix Private IP URL Validator Bug And Add Tests

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py`

**Problem:**

The current private IP check can swallow its own `ValueError("domain_not_allowed")` inside `except ValueError: pass`.

**Step 1: Add failing tests**

Add:

```python
def test_detail_url_private_ip_rejected_even_if_allowlisted_for_test():
    with pytest.raises(ValueError, match="domain_not_allowed"):
        validate_announcement_detail_url(
            "https://10.0.0.1/en/support/announcement/abc",
            allowed_domains=("10.0.0.1",),
        )

    with pytest.raises(ValueError, match="domain_not_allowed"):
        validate_announcement_detail_url(
            "https://192.168.1.5/en/support/announcement/abc",
            allowed_domains=("192.168.1.5",),
        )
```

**Step 2: Implement**

Use separate parsing control flow:

```python
try:
    ip = ipaddress.ip_address(host)
except ValueError:
    ip = None

if ip is not None and (ip.is_private or ip.is_loopback):
    raise ValueError("domain_not_allowed")
```

**Step 3: Verify**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py -q
```

Expected: PASS.

---

## Task 9: Add End-To-End Regression For The Observed BTCU/ETHU Event

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Add failing end-to-end test**

Add:

```python
def test_runner_observed_btcu_ethu_launch_emits_event_symbols_from_base_asset_detail(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "25da4614ffff435fa28544b27fd33a39",
                    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    # fake detail fetch returns HTML or text containing same title.
    # expected one event row with symbols ["BTCUUSDT", "ETHUUSDT"].
```

Assertions:

```text
summary.detail_fetch_attempted_count >= 1
summary.detail_symbol_extracted_count == 1
event.symbols contains BTCUUSDT and ETHUUSDT
event.symbol_extraction_source == detail_base_asset_derived
event.symbol_derivation_method == base_asset_plus_quote
event.quote_derivation_source == exchange_info
event.symbol_validation_status == validated
event.symbol_parse_status == parsed
event.trade_signal_allowed == false
event.event_id is stable across repeated polls with the same validated symbol set
```

**Event ID note:**

```text
UNKNOWN terminal rows and validated MULTI parsed rows may have different event_id values because they represent different terminal extraction states.
However, for the same validated symbol set, event_id must be stable across restarts and repeated polls by hashing sorted symbols.
The end-to-end test must assert stable event_id for repeated validated BTCUUSDT/ETHUUSDT extraction.
```

**Step 2: Verify full focused suite**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: PASS.

---

## Task 10: Update Review/Ops Notes For Current 7d Server Run

**Files:**
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

Add a subsection under known issues:

```text
Issue: BTCU/ETHU base-asset-only futures launch symbols=[]
observed_at = 2026-06-30T14:45:02.782Z
article_code = 25da4614ffff435fa28544b27fd33a39
server_effect = 1.5D wrote one post-watermark event row with symbols=[]; 1.5F did not accept it and collected no depth snapshots.
root_cause = current parser only recognizes full XXXUSDT/XXXUSDC, not base-asset-only launch names.
status = hotfix planned locally; current server 7d run cannot retroactively recover 12h depth evidence for this event.
```

Deployment note:

```text
After local hotfix passes review, deploy code to server and start a fresh Stage 1.5D output root plus matching Stage 1.5F output root.
Do not mutate existing 7d artifacts.
```

---

## Task 11: Safety Grep And Final Verification

**Files:**
- No code edits.

Run focused tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Run safety grep:

```bash
rg -n "apiKey\s*=|api_key\s*=|secret\s*=|from .*TradeIntent|TradeIntent\(|from .*SignalCandidate|SignalCandidate\(|order_endpoint\s*=\s*True|private_ws|create_order|cancel_order|fetch_balance|withdraw|transfer|requests\.post|httpx\.post|ccxt|wallet|private_key|signed_tx|raw_tx|order_request|swap_request" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d* \
  tests/research/external_signal_shadow/test_stage1_5d_*.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
```

Expected:

```text
pytest focused suite passes
safety grep has no unsafe hits
```

---

## Completion Criteria

```text
1. Observed BTCU/ETHU title is covered by parser and runner regression tests.
2. Base-asset fallback only activates under explicit futures launch + USDⓈ/USDS/USD-M margined + Perpetual context in short candidate windows.
3. Detail full-symbol extraction remains preferred over base-asset derivation and is labeled `symbol_extraction_source=detail` with `symbol_derivation_method=none`.
4. Base-derived events are labeled `detail_base_asset_derived` or `title_base_asset_derived` with `symbol_derivation_method=base_asset_plus_quote`.
5. Base-derived symbols are emitted as parsed only after Binance USD-M public exchangeInfo validation.
6. Live detail fetch can persist JSON/HTML/TXT raw payload evidence without changing announcement list JSON fetch behavior.
7. Detail emitted events preserve first_detected_at_ms and include detail_fetched_at_ms, symbol_resolved_at_ms, and symbol_resolution_latency_ms.
8. Failed detail requests are manifest-auditable.
9. Private IP detail URLs are rejected even if accidentally allowlisted in tests/config.
10. 1.5F legacy row compatibility remains green.
11. Persisted event rows must never contain `symbol_validation_status=unverified`; unverified is allowed only in in-memory candidate state or non-event diagnostics.
12. No trading/paper/execution/alpha flags are enabled.
```

## Explicit Non-Claims

This hotfix still does not prove:

```text
execution feasibility
alpha validity
paper trading readiness
live trading readiness
historical 12h depth availability for already missed BTCU/ETHU event
```

It only reduces Stage 1.5D false negatives so future Stage 1.5F live depth observations can start when similar launch events appear.
