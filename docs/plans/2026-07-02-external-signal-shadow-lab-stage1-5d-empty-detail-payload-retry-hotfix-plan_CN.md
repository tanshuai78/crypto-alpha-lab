# Stage 1.5D Empty Detail Payload Retry Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 Stage 1.5D 在 Binance announcement detail 返回 `HTTP 202 + 0 bytes` 时误判为成功并写入 `symbols=[] terminal_failed` 的问题。

**Architecture:** `fetch_public_payload()` 必须把非 200 或空 body 视为 transient detail unavailable，而不是 success。Stage 1.5D runner 遇到该状态时只写 request manifest / 保留 retry state，不写 terminal event、不加入 seen ids，并允许后续 poll 重试；后续 detail 成功后再 emit 一条 `symbols != []` event。

**Tech Stack:** Python stdlib `urllib`, pytest, JSONL artifacts, Binance public-readonly announcement/detail endpoints。

---

## 0. 背景与根因

服务器 live 证据：

```json
{
  "source_type": "announcement_detail",
  "http_status": 202,
  "payload_size_bytes": 0,
  "payload_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "error": null,
  "url": "https://www.binance.com/en/support/announcement/d2acaa91c14e4cc598aaee1017efc1ac",
  "final_url": "https://www.binance.com/en/support/announcement/d2acaa91c14e4cc598aaee1017efc1ac"
}
```

对应 Stage 1.5D event：

```json
{
  "source_article_id": "d2acaa91c14e4cc598aaee1017efc1ac",
  "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
  "symbols": [],
  "detail_fetch_status": "success",
  "symbol_parse_failed_reason": "detail_symbols_empty",
  "symbol_parse_status": "terminal_failed"
}
```

官方页面实际存在 symbols：

```text
STRCUSDT
CATUSDT
TXNUSDT
FLEXUSDT
TERUSDT
TTWOUSDT
KSTRUSDT
BSPUSDT
```

根因：

```text
fetch_public_payload() 当前把 HTTP 202 + empty body 当成 ok=True。
runner 随后保存 0 bytes payload，parser 从空文本得到 symbols=[]，并把事件写成 terminal_failed。
这会永久吞掉本应重试的 post-watermark futures launch event。
```

目标语义：

```text
HTTP 202 或 payload_size_bytes == 0
= detail temporarily unavailable / empty_detail_payload
= pending_retry
!= success
!= terminal_failed
```

Runner error taxonomy:

```text
transient_detail_unavailable:
  http_status in {202, 408, 425, 429, 500, 502, 503, 504}
  error == empty_detail_payload
  error startswith detail_payload_http_status_202
  error startswith detail_payload_http_status_408
  error startswith detail_payload_http_status_425
  error startswith detail_payload_http_status_429
  error startswith detail_payload_http_status_5

terminal_or_policy_controlled_detail_unavailable:
  url_missing
  url_not_allowlisted
  final_url_not_allowlisted
  http_status in {400, 401, 403, 404}

Minimum acceptable rule:
  all non-200 responses return ok=false
  202/empty/429/5xx keep pending_retry
  400/401/403/404 never become success and never persist trusted payload; whether they retry until max age or terminal-fail immediately must be explicit in runner tests
```

Manifest payload semantics:

```text
payload_sha256 = only for trusted, non-empty, persisted detail payloads
payload_path = only for trusted, non-empty, persisted detail payloads
payload_trusted = false for empty/non-200 responses
response_payload_size_bytes = raw response body size, may be 0
response_payload_sha256 = optional raw response hash; if included for empty body, it must not be confused with payload_sha256
```

Execution order:

```text
1. Run/add the July 2 parser regression first to confirm parser handles normal detail body text.
2. Fix client semantics: only HTTP 200 + non-empty body can be success.
3. Fix runner transient retry semantics and manifest fields.
4. Verify same-process retry and process-restart retry.
5. Add summary counters.
6. Run 1.5F regression and safety grep.
7. Update docs.
```

安全边界：

```text
scope = stage1_5d_detail_fetch_retry_semantics_only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

---

## Task 1: Client rejects empty / not-ready detail payload

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py`

### Step 1: Write failing tests

Add tests near existing `fetch_public_payload` tests:

```python
def test_fetch_public_payload_rejects_empty_body():
    class FakeResponse:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def geturl(self):
            return "https://www.binance.com/en/support/announcement/abc"
        def read(self):
            return b""

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload(
            "https://www.binance.com/en/support/announcement/abc",
            live_public_readonly=True,
        )

    assert result["ok"] is False
    assert result["http_status"] == 200
    assert result["payload_size_bytes"] == 0
    assert result["payload"] is None
    assert result["error"] == "empty_detail_payload"


def test_fetch_public_payload_treats_http_202_as_not_ready():
    class FakeResponse:
        status = 202
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def geturl(self):
            return "https://www.binance.com/en/support/announcement/abc"
        def read(self):
            return b""

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload(
            "https://www.binance.com/en/support/announcement/abc",
            live_public_readonly=True,
        )

    assert result["ok"] is False
    assert result["http_status"] == 202
    assert result["payload_size_bytes"] == 0
    assert result["payload"] is None
    assert result["error"] == "detail_payload_http_status_202"


def test_fetch_public_payload_treats_http_429_as_not_ready():
    class FakeResponse:
        status = 429
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def geturl(self):
            return "https://www.binance.com/en/support/announcement/abc"
        def read(self):
            return b"Too Many Requests"

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload(
            "https://www.binance.com/en/support/announcement/abc",
            live_public_readonly=True,
        )

    assert result["ok"] is False
    assert result["http_status"] == 429
    assert result["payload"] is None
    assert result["error"] == "detail_payload_http_status_429"


def test_fetch_public_payload_treats_http_503_as_not_ready():
    class FakeResponse:
        status = 503
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def geturl(self):
            return "https://www.binance.com/en/support/announcement/abc"
        def read(self):
            return b"Service Unavailable"

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload(
            "https://www.binance.com/en/support/announcement/abc",
            live_public_readonly=True,
        )

    assert result["ok"] is False
    assert result["http_status"] == 503
    assert result["payload"] is None
    assert result["error"] == "detail_payload_http_status_503"
```

### Step 2: Run tests and confirm fail

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py::test_fetch_public_payload_rejects_empty_body \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py::test_fetch_public_payload_treats_http_202_as_not_ready \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py::test_fetch_public_payload_treats_http_429_as_not_ready \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py::test_fetch_public_payload_treats_http_503_as_not_ready \
  -q
```

Expected before fix: fail because current implementation returns `ok=True`.

### Step 3: Implement minimal client fix

In `fetch_public_payload()` after reading `raw_bytes` and before returning success:

```python
status_code = getattr(response, "status", 200)
raw_bytes = response.read()

if status_code != 200:
    return {
        "ok": False,
        "payload": None,
        "requested_url": url,
        "final_url": final_url,
        "requested_host": requested_host,
        "final_host": urllib.parse.urlparse(final_url).hostname or "",
        "redirect_count": redirect_count,
        "http_status": status_code,
        "payload_size_bytes": len(raw_bytes),
        "row_count": None,
        "error": f"detail_payload_http_status_{status_code}",
    }

if len(raw_bytes) == 0:
    return {
        "ok": False,
        "payload": None,
        "requested_url": url,
        "final_url": final_url,
        "requested_host": requested_host,
        "final_host": urllib.parse.urlparse(final_url).hostname or "",
        "redirect_count": redirect_count,
        "http_status": status_code,
        "payload_size_bytes": 0,
        "row_count": None,
        "error": "empty_detail_payload",
    }

content = raw_bytes.decode("utf-8")
```

Do not change `fetch_public_json()` list endpoint behavior in this task. The announcement list query must continue to use JSON fetch; only announcement detail fetch uses `fetch_public_payload()`.

### Step 4: Run tests and confirm pass

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  -q
```

Expected: all client tests pass.

---

## Task 2: Runner keeps empty detail fetch in pending retry state

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

### Step 1: Write failing integration test

Add a test using mocked `fetch_public_payload()` returning `ok=False`, `error="empty_detail_payload"`, `http_status=202`, `payload_size_bytes=0` for a `Multiple USDⓈ-Margined TradFi` title.

Expected assertions:

```python
def test_empty_detail_payload_keeps_article_pending_retry_without_terminal_event(tmp_path):
    # Arrange one list payload with a futures launch article whose title has no symbols.
    # Mock fetch_public_payload to return ok=False, error=empty_detail_payload, http_status=202.
    # Run collector for one short poll.

    # Assert no events/*.jsonl terminal_failed row exists for the article.
    # Assert request_manifest has a detail row with error=empty_detail_payload and payload_size_bytes=0.
    # Assert summary does not count this as symbol_parse_failed terminal failure.
```

Use existing runner tests as template. Concrete expected event assertion:

```python
events = read_jsonl_files(output_root / "events")
assert not any(
    row.get("source_article_id") == article_id
    and row.get("symbol_parse_status") == "terminal_failed"
    for row in events
)
```

Concrete manifest assertion. Do not use `detail_rows[-1]` without filtering by the expected error/article/url; multi-poll tests can create several detail rows.

```python
manifest = read_jsonl_files(output_root / "request_manifest")
empty_rows = [
    r for r in manifest
    if r.get("source_type") == "announcement_detail"
    and r.get("error") == "empty_detail_payload"
    and article_id in (r.get("url") or "")
]
assert len(empty_rows) >= 1
assert empty_rows[-1]["http_status"] == 202
assert empty_rows[-1]["payload_size_bytes"] == 0
assert empty_rows[-1]["response_payload_size_bytes"] == 0
assert empty_rows[-1].get("payload_path") in (None, "")
assert empty_rows[-1].get("payload_sha256") in (None, "")
assert empty_rows[-1].get("payload_trusted") is False
```

Add two transient status variants:

```python
def test_detail_http_429_keeps_pending_retry_without_terminal_event(tmp_path):
    # Mock fetch_public_payload with ok=False, http_status=429, error=detail_payload_http_status_429.
    # Assert no terminal_failed event, manifest has error, retry remains possible.


def test_detail_http_503_keeps_pending_retry_without_terminal_event(tmp_path):
    # Mock fetch_public_payload with ok=False, http_status=503, error=detail_payload_http_status_503.
    # Assert no terminal_failed event, manifest has error, retry remains possible.
```

Add one non-success terminal/policy status variant:

```python
def test_detail_http_404_does_not_emit_success_or_persist_payload(tmp_path):
    # Mock fetch_public_payload with ok=False, http_status=404, error=detail_payload_http_status_404.
    # Assert no parsed success event.
    # Assert no trusted payload_path/payload_sha256.
    # If implementation chooses retry-until-max-age for 404, assert no terminal event on first attempt.
    # If implementation chooses immediate terminal for 404, assert explicit terminal reason detail_payload_http_status_404.
    # In either case: never symbols parsed, never detail_fetch_status=success.
```

### Step 2: Run test and confirm fail

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_empty_detail_payload_keeps_article_pending_retry_without_terminal_event \
  -q
```

Expected before fix: fail because current runner can write terminal_failed after empty payload is treated as success, or does not write the expected manifest error row.

### Step 3: Implement runner error handling

In the `else` branch where `fetch_res["ok"]` is false for detail fetch:

Required behavior:

```text
1. append request_manifest row:
   source_type = announcement_detail
   http_status = fetch_res["http_status"]
   payload_size_bytes = fetch_res["payload_size_bytes"] or 0
   payload_sha256 = None
   payload_path = None
   error = fetch_res["error"]
   fetched_at_ms = now_ms
   parser_version = PARSER_VERSION
   symbol_extraction_version = SYMBOL_EXTRACTION_VERSION

2. increment detail_fetch_failed_count.
3. if error is transient_detail_unavailable:
   keep detail_retry_state[code]
   do not append events/*.jsonl
   do not add event_id to seen_event_ids
   do not add source_article_id to terminal seen set
   do not call detail_retry_state.pop(code, None)
   continue
```

Transient classification helper may be local to runner:

```python
TRANSIENT_DETAIL_HTTP_STATUSES = {202, 408, 425, 429, 500, 502, 503, 504}

def is_transient_detail_fetch_error(fetch_res: dict) -> bool:
    error = fetch_res.get("error") or ""
    status = fetch_res.get("http_status")
    if error == "empty_detail_payload":
        return True
    if status in TRANSIENT_DETAIL_HTTP_STATUSES:
        return True
    if error.startswith("detail_payload_http_status_5"):
        return True
    return False
```

Do not persist a 0-byte detail payload as trusted detail evidence. The manifest is enough audit evidence for the failed attempt.

Required manifest fields for failed detail attempts:

```json
{
  "source_type": "announcement_detail",
  "http_status": 202,
  "payload_size_bytes": 0,
  "response_payload_size_bytes": 0,
  "payload_sha256": null,
  "payload_path": null,
  "payload_trusted": false,
  "error": "detail_payload_http_status_202"
}
```

### Step 4: Run test and confirm pass

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_empty_detail_payload_keeps_article_pending_retry_without_terminal_event \
  -q
```

Expected: pass.

---

## Task 3: Retry survives poll/restart and later emits symbols once

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` only if needed
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

### Step 1: Write failing retry test

Add test:

```python
def test_empty_detail_payload_retries_and_success_later_emits_symbols_once(tmp_path):
    # Poll 1 detail fetch returns ok=False empty_detail_payload / http_status=202.
    # Poll 2 detail fetch returns ok=True with payload text containing STRCUSDT CATUSDT.
    # exchangeInfo includes STRCUSDT and CATUSDT as TRADING PERPETUAL USDT.

    # Assert no terminal_failed row for poll 1.
    # Assert exactly one parsed event row after poll 2.
    # Assert symbols == ["STRCUSDT", "CATUSDT"] or contains both.
    # Assert detail_fetch_status == "success" and symbol_parse_status == "parsed".
```

This test verifies same-process retry state. It must also indirectly verify that the first failed attempt did not call `detail_retry_state.pop(code, None)`: poll 2 can only emit parsed symbols if retry state survived poll 1.

Add a second explicit process-restart test:

```python
def test_empty_detail_retry_survives_process_restart_by_not_marking_seen(tmp_path):
    # Run 1 against output_root:
    #   list payload includes article
    #   detail returns ok=False, http_status=202, error=detail_payload_http_status_202
    #   assert no events row for article
    #   assert manifest has failure
    #
    # Run 2 against the same output_root, simulating process restart:
    #   list payload includes same article
    #   detail returns ok=True with text containing STRCUSDT CATUSDT
    #   exchangeInfo includes STRCUSDT/CATUSDT if the runner path requires it
    #
    # Assert exactly one parsed event row exists after run 2.
```

The restart test is blocking. In-memory retry is not enough: after process restart, the article must not be permanently missed because no terminal event / seen id was written during the empty-detail attempt.

If the runner does not currently support multiple polls cleanly in one test, run `main()` twice against the same `output_root` with fixture/mock state, preserving files.

### Step 2: Run test and confirm fail/pass

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_empty_detail_payload_retries_and_success_later_emits_symbols_once \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_empty_detail_retry_survives_process_restart_by_not_marking_seen \
  -q
```

Expected after Task 2: likely pass or reveal missing retry persistence. If fail, fix only retry-state behavior needed for this case.

### Step 3: Ensure no duplicate events

Add assertion:

```python
parsed_rows = [
    row for row in events
    if row.get("source_article_id") == article_id
    and row.get("symbol_parse_status") == "parsed"
]
assert len(parsed_rows) == 1
```

---

## Task 4: Parser regression for July 2 TradFi detail body

**Files:**
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

### Step 1: Add direct parser test

```python
def test_detail_extracts_july_2_tradfi_usdt_symbols_from_body_text():
    detail_text = """
    Binance Futures will launch the following perpetual contract(s) as below:
    2026-07-02 09:15 (UTC): STRCUSDT Perpetual Contract
    2026-07-02 09:20 (UTC): CATUSDT Perpetual Contract
    2026-07-02 09:25 (UTC): TXNUSDT Perpetual Contract
    2026-07-02 09:30 (UTC): FLEXUSDT Perpetual Contract
    2026-07-02 09:35 (UTC): TERUSDT Perpetual Contract
    2026-07-02 09:40 (UTC): TTWOUSDT Perpetual Contract
    2026-07-02 09:45 (UTC): KSTRUSDT Perpetual Contract
    2026-07-02 09:50 (UTC): BSPUSDT Perpetual Contract
    """
    result = extract_symbol_candidates_from_detail_payload(
        detail_text,
        max_symbols=30,
        title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
    )

    assert result["symbol_extraction_source"] == "detail"
    assert result["symbol_validation_status"] == "validated_by_exact_text"
    assert result["symbols"] == [
        "STRCUSDT",
        "CATUSDT",
        "TXNUSDT",
        "FLEXUSDT",
        "TERUSDT",
        "TTWOUSDT",
        "KSTRUSDT",
        "BSPUSDT",
    ]
```

### Step 2: Run parser tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  -q
```

Expected: pass. If it fails, fix parser before touching runner.

---

## Task 5: Summary and diagnostics counters stay truthful

**Files:**
- Modify if needed: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

### Required semantics

For empty detail / HTTP 202 transient attempts:

```text
detail_fetch_attempted_count += 1
detail_fetch_failed_count += 1
detail_pending_retry_count += 1
detail_empty_payload_count += 1 when error == empty_detail_payload or payload_size_bytes == 0
detail_http_not_ready_count += 1 when status in {202, 408, 425, 429, 500, 502, 503, 504}
symbol_parse_failed_count must not increment as terminal parse failure
symbol_empty_event_count must not increment
candidate_validation_pending_count may remain unchanged unless candidates were extracted
research_result_valid remains false until normal completion criteria
```

Required summary fields:

```json
{
  "detail_pending_retry_count": 0,
  "detail_empty_payload_count": 0,
  "detail_http_not_ready_count": 0,
  "detail_terminal_failed_count": 0
}
```

If `detail_fetch_failed_count` grows, review must be able to distinguish transient pending from terminal failure.

### Step 1: Add summary assertion in runner test

After empty-detail poll:

```python
summary = json.loads(summary_path.read_text())
assert summary["detail_fetch_attempted_count"] >= 1
assert summary["detail_fetch_failed_count"] >= 1
assert summary["detail_pending_retry_count"] >= 1
assert summary["detail_empty_payload_count"] >= 1
assert summary.get("symbol_empty_event_count", 0) == 0
assert summary.get("symbol_parse_failed_count", 0) == 0
```

### Step 2: Run summary and runner tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: pass.

---

## Task 6: 1.5F regression: no change to consumer safety

**Files:**
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py`
- Optional Test: existing 1.5F loader/runner tests if available

### Step 1: Run relevant existing 1.5F tests

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py \
  -q
```

Expected: pass. This hotfix must not alter 1.5F behavior directly.

### Step 2: Confirm expected operational behavior

```text
1.5F still ignores symbols=[] events.
1.5F accepts only post-watermark event-symbols with non-empty symbols.
No paper/live/trading flags change.
```

---

## Task 7: Review documentation update

**Files:**
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`
- Modify: `docs/strategy_specs/2026-06-21-external-signal-shadow-lab-external-catalyst-events-filter-branch-brief_CN.md` if needed

### Step 1: Add incident note

Add a short subsection under the known issues / hotfix background:

```text
2026-07-02 incident: Binance announcement detail returned HTTP 202 + 0-byte body.
Old behavior: treated as success, persisted empty payload, emitted symbols=[] terminal_failed.
Fixed behavior: treats as transient detail unavailable, writes manifest failure, keeps pending_retry, no terminal event.
```

### Step 2: Add monitoring command

Add command to identify empty detail payload incidents:

```bash
python - <<'PY'
import json, os
from pathlib import Path
root = Path(os.environ["STAGE1_5D_EVENTS_OUT"])
for path in sorted((root / "request_manifest").glob("*.jsonl")):
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("source_type") == "announcement_detail" and row.get("payload_size_bytes") == 0:
            print(json.dumps(row, ensure_ascii=False))
PY
```

---

## Task 8: Verification suite

Run targeted suite:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_client.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Run external signal full suite:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow \
  tests/scripts/external_signal_shadow \
  -q
```

Run full repo if time permits:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q
```

Safety grep:

```bash
rg -n "apiKey\s*=|api_key\s*=|secret\s*=|from .*TradeIntent|TradeIntent\(|from .*SignalCandidate|SignalCandidate\(|order_endpoint\s*=\s*True|private_ws|create_order|cancel_order|fetch_balance|withdraw|transfer|requests\.post|httpx\.post|ccxt|wallet|private_key|signed_tx|raw_tx|order_request|swap_request" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d* \
  configs/base.py \
  tests/research/external_signal_shadow/test_stage1_5d_* \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py
```

Expected: no unsafe hits except existing harmless config comments if any.

---

## Task 9: Server rollout notes after local review passes

Do not deploy during implementation unless explicitly requested.

After local tests pass and review accepts the hotfix:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab

rsync -avzP \
  --exclude='data' \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='.ruff_cache' \
  --exclude='.pytest_cache' \
  --exclude='__pycache__' \
  /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/ \
  root@47.82.4.85:/root/crypto-alpha-lab/
```

Server validation:

```bash
cd /root/crypto-alpha-lab
source .venv/bin/activate

PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Recommended live restart:

```text
Default formal observation:
1. Stop current Stage 1.5D u_hotfix tmux session.
2. Start a new Stage 1.5D output root with suffix _7d_empty_detail_retry_hotfix.
3. Start a new Stage 1.5F output root with suffix _7d_empty_detail_retry_hotfix.
4. Bootstrap the new Stage 1.5F root from the new Stage 1.5D root.
5. Only events after this new watermark count as formal 12h live depth evidence.

Recovery validation for the already-seen d2acaa... article:
1. Use a separate output root containing recovery_validation in the name.
2. This may validate parser/retry behavior and symbol extraction.
3. It must not be labeled valid 12h live depth evidence because the event already occurred and the initial 12h window may be partially missed.
4. Do not mix recovery_validation artifacts into the formal Stage 1.5F evidence root.
```

Immediate target validation after rollout:

```bash
export ARTICLE_ID="d2acaa91c14e4cc598aaee1017efc1ac"
export STAGE1_5D_EVENTS_OUT="<new_1_5d_output_root>"
export STAGE1_5F_OUT="<new_1_5f_output_root>"

grep -Rh -- "$ARTICLE_ID" "$STAGE1_5D_EVENTS_OUT"/events/*.jsonl 2>/dev/null | python -m json.tool
cat "$STAGE1_5F_OUT/live_depth_observer_summary.json" | python -m json.tool
find "$STAGE1_5F_OUT/events_accepted" -type f 2>/dev/null | xargs wc -l 2>/dev/null || true
find "$STAGE1_5F_OUT/depth_snapshots" -type f 2>/dev/null | sort | tail -n 20
```

Expected if detail becomes available:

```json
"symbols": ["STRCUSDT", "CATUSDT", "TXNUSDT", "FLEXUSDT", "TERUSDT", "TTWOUSDT", "KSTRUSDT", "BSPUSDT"],
"symbol_extraction_source": "detail",
"symbol_validation_status": "validated_by_exact_text",
"symbol_parse_status": "parsed"
```

Expected if Binance continues returning 202/empty:

```text
No terminal_failed event for this article.
request_manifest shows empty_detail_payload / detail_payload_http_status_202 attempts.
collector keeps retrying until configured retry / age policy decides otherwise.
```

---

## Completion Criteria

1. `fetch_public_payload()` returns `ok=False` for HTTP 202 detail response.
2. `fetch_public_payload()` returns `ok=False` for 200 with empty body.
3. `fetch_public_payload()` returns `ok=False` for HTTP 429 and 503 detail responses.
4. HTTP 202 / empty / 429 / 5xx detail failures are classified as transient pending retry in runner.
5. HTTP 404 detail failure never becomes success and never persists trusted payload; terminal vs retry-until-max-age behavior is explicit and tested.
6. Empty detail payload does not persist 0-byte payload as trusted detail evidence.
7. Empty detail manifest rows have no `payload_path`, no trusted `payload_sha256`, and include `payload_trusted=false`.
8. Empty detail payload does not emit `symbols=[] terminal_failed` event.
9. Empty detail payload does not add terminal event id to `seen_event_ids`.
10. Same-process retry can later emit exactly one parsed event with symbols.
11. Process-restart retry can later emit exactly one parsed event with symbols from the same output root.
12. July 2 TradFi body text parser extracts all eight expected symbols.
13. Summary includes `detail_pending_retry_count`, `detail_empty_payload_count`, and `detail_http_not_ready_count`.
14. 1.5F still ignores `symbols=[]` and uses normal post-watermark non-empty event-symbol flow.
15. Targeted tests pass.
16. External signal suite passes or any unrelated failures are documented with evidence.
17. Safety grep has no unsafe trading/private API hits.
18. Review doc records the 202/empty-detail incident, monitoring command, and formal-vs-recovery rollout distinction.
