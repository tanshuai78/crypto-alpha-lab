# Stage 1.5D Multiple TradFi Symbol Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 Stage 1.5D 对 `Multiple USDⓈ-Margined TradFi Perpetual Contracts` 这类 `symbols=[]` futures launch 公告的漏采问题，并保留可复核 detail payload 证据。

**Architecture:** 保持现有分层：parser 只做纯解析与 normalization，runner/client 负责 public-readonly detail fetch，storage 负责 detail payload 持久化，summary 负责 counters 汇总。detail fallback 只在 `event_type=futures_contract_launch` 且 title extraction 得到空 symbols 时触发；transient failure 进入 `pending_retry`，不能被 dedupe 永久吞掉。`pending_retry` 只存在 runner 内存状态中，不写入 `events/*.jsonl`；只有 `parsed` 或 `terminal_failed` 才能进入 events stream。

**Tech Stack:** Python 3.12, pytest, stdlib `urllib`, JSONL storage, existing `configs/base.py` constants, existing Stage 1.5D client/parser/runner modules.

---

## 0. Preconditions And Safety Boundaries

**Files:**
- Read: `docs/designs/2026-06-30-external-signal-shadow-lab-stage1-5d-multiple-tradfi-symbol-extraction-design_CN.md`
- Read: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Read: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Read: `configs/base.py`

**Hard boundaries:**

```text
scope = stage1_5d_parser_enhancement_only
server_deployment = out_of_scope
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

Do not deploy to server or restart current 1.5D / 1.5F processes as part of this implementation. Local tests only.

**Verification before coding:**

Run:

```bash
rg -n "Multiple USD|TradFi|extract_futures_launch_symbols|run_one_poll_cycle|symbol_parse_failed_count" \
  src/research/external_signal_shadow \
  scripts/external_signal_shadow \
  tests/research/external_signal_shadow \
  tests/scripts/external_signal_shadow
```

Expected: current parser title-only behavior is visible; existing tests mention current `symbols=[]` case.

---

## Task 1: Add Stage 1.5D Detail Fallback Config Constants

**Files:**
- Modify: `configs/base.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`

**Step 1: Write failing config test**

Add assertions to `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`:

```python
def test_stage1_5d_detail_fallback_config_constants_exist():
    from configs import base

    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_REQUEST_TIMEOUT_SEC == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC == 3600
```

**Step 2: Run failing test**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py::test_stage1_5d_detail_fallback_config_constants_exist -q
```

Expected: FAIL because constants do not exist.

**Step 3: Implement config constants**

Add near existing Stage 1.5D constants in `configs/base.py`:

```python
EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS = 30
# Maximum symbols extracted from one announcement detail payload. Prevents malformed pages from creating huge symbol lists.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL = 3
# Maximum announcement detail fallback requests per poll. Keeps list polling stable and bounded.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_REQUEST_TIMEOUT_SEC = 10.0
# Network timeout for announcement detail fallback requests.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES = 3
# Maximum retry attempts across polls for transient detail fallback failures.

EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC = 3600
# Maximum age for retrying a pending detail fallback before marking terminal failed.
```

**Step 4: Verify**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py::test_stage1_5d_detail_fallback_config_constants_exist -q
```

Expected: PASS.

---

## Task 2: Add Parser Version Constants And Mandatory Diagnostics

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Write failing tests for mandatory diagnostics**

Add tests:

```python
def test_normalize_event_adds_symbol_extraction_diagnostics_for_title_symbols():
    row = normalize_live_event(
        raw={"title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract", "code": "abc"},
        source_parent_url="https://www.binance.com/en/support/announcement",
        detected_at_ms=10_000,
        source_published_at_ms=1_000,
        source_published_at_ms_confidence="medium",
    )

    assert row["symbols"] == ("ABCUSDT",)
    assert row["symbol_extraction_source"] == "title"
    assert row["detail_fetch_attempted"] is False
    assert row["detail_fetch_status"] == "not_needed"
    assert row["symbol_parse_failed_reason"] is None
    assert row["symbol_parse_status"] == "parsed"
    assert row["parser_version"] == "stage1_5d_symbol_extraction_v2"
    assert row["symbol_extraction_version"] == 2


def test_normalize_event_adds_terminal_failed_diagnostics_when_no_symbols_without_detail():
    row = normalize_live_event(
        raw={"title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts", "code": "tradfi"},
        source_parent_url="https://www.binance.com/en/support/announcement",
        detected_at_ms=10_000,
        source_published_at_ms=1_000,
        source_published_at_ms_confidence="medium",
    )

    assert row["symbols"] == ()
    assert row["symbol_extraction_source"] == "none"
    assert row["detail_fetch_attempted"] is False
    assert row["detail_fetch_status"] == "not_needed"
    assert row["symbol_parse_failed_reason"] == "symbol_missing_no_detail_attempted"
    assert row["symbol_parse_status"] == "terminal_failed"
```

**Step 2: Run failing tests**

Run:

```bash
PYTHONPATH=src:. pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_normalize_event_adds_symbol_extraction_diagnostics_for_title_symbols \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_normalize_event_adds_terminal_failed_diagnostics_when_no_symbols_without_detail \
  -q
```

Expected: FAIL because diagnostic fields do not exist.

**Step 3: Implement minimal parser constants and diagnostic defaults**

In `stage1_5d_live_event_source_parser.py`, add:

```python
SYMBOL_EXTRACTION_VERSION = 2
PARSER_VERSION = "stage1_5d_symbol_extraction_v2"
```

Modify `normalize_live_event()` to accept optional arguments:

```python
def normalize_live_event(
    raw: dict,
    source_parent_url: str,
    detected_at_ms: int,
    source_published_at_ms: int,
    source_published_at_ms_confidence: str,
    symbols_override: list[str] | tuple[str, ...] | None = None,
    extraction_metadata: dict | None = None,
) -> dict:
```

Rules:

```text
normalize_live_event() is only called when emitting a final event row.
runner must not call normalize_live_event() to create a pre-detail pending_retry row.
symbols_override is not None -> use override symbols.
metadata provided -> merge it.
no symbols and no metadata -> terminal_failed/symbol_missing_no_detail_attempted, but only for final emitted rows.
symbols from title -> parsed/title/not_needed.
```

**Step 4: Verify parser tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: PASS.

---

## Task 3: Add Detail Payload Symbol Extraction Helper

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Write failing unit tests**

Add tests:

```python
def test_extract_symbols_from_multiple_tradfi_detail_text():
    detail = "Contracts: AAPLUSDT, MSFTUSDT and NVDAUSDT USDⓈ-Margined Perpetual Contracts"
    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["AAPLUSDT", "MSFTUSDT", "NVDAUSDT"]


def test_extract_symbols_from_nested_detail_payload():
    detail = {
        "data": {
            "body": [
                {"type": "table", "rows": [["AMDUSDT"], ["QCOMUSDT"], ["USARUSDT"]]},
                {"text": "Ignore BTC, include only futures pairs"},
            ]
        }
    }
    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == ["AMDUSDT", "QCOMUSDT", "USARUSDT"]


def test_detail_extraction_preserves_order_dedupes_and_caps():
    detail = "AAAUSDT BBBUSDT AAAUSDT CCCUSDT DDDUSDT"
    assert extract_symbols_from_detail_payload(detail, max_symbols=3) == ["AAAUSDT", "BBBUSDT", "CCCUSDT"]


def test_detail_extraction_does_not_match_standalone_usdt():
    detail = "The contract is margined and settled in USDT. No concrete symbol appears here."
    assert extract_symbols_from_detail_payload(detail, max_symbols=30) == []
```

**Step 2: Run failing tests**

Run:

```bash
PYTHONPATH=src:. pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_extract_symbols_from_multiple_tradfi_detail_text \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_extract_symbols_from_nested_detail_payload \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_detail_extraction_preserves_order_dedupes_and_caps \
  -q
```

Expected: FAIL because `extract_symbols_from_detail_payload` does not exist.

**Step 3: Implement helper**

Add pure helper:

```python
def extract_symbols_from_detail_payload(payload: object, max_symbols: int) -> list[str]:
    """Extract futures contract symbols from nested Binance detail payload or raw text."""
```

Implementation requirements:

```text
1. Recursively walk dict/list/tuple values.
2. Treat str as searchable text.
3. Use regex \b([A-Z0-9]{2,30}USDT|[A-Z0-9]{2,30}USDC)\b.
4. Deduplicate while preserving order.
5. Stop at max_symbols.
6. Return [] for unsupported payload types.
```

**Step 4: Verify parser tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: PASS.

---

## Task 4: Add Detail URL Validation In Client Layer

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_client.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py`

**Step 1: Write failing URL safety tests**

Add tests:

```python
import pytest

from src.research.external_signal_shadow.stage1_5d_live_event_source_client import validate_announcement_detail_url


def test_detail_url_non_https_rejected():
    with pytest.raises(ValueError, match="detail_url_scheme_not_allowed"):
        validate_announcement_detail_url("http://www.binance.com/en/support/announcement/abc")


def test_detail_url_non_allowlisted_host_rejected():
    with pytest.raises(ValueError, match="domain_not_allowed"):
        validate_announcement_detail_url("https://evil.com/en/support/announcement/abc")


def test_detail_url_localhost_rejected():
    with pytest.raises(ValueError):
        validate_announcement_detail_url("https://localhost/en/support/announcement/abc")


def test_detail_url_missing_marks_url_missing_without_crash():
    with pytest.raises(ValueError, match="detail_url_missing"):
        validate_announcement_detail_url("")


def test_detail_url_rejects_redirect_query_injection():
    with pytest.raises(ValueError, match="detail_url_query_not_allowed"):
        validate_announcement_detail_url("https://www.binance.com/en/support/announcement/abc?redirect=https://evil.com")
```

If existing client tests already cover generic allowlist, keep these detail-specific tests because the allowed path/query is narrower.

**Step 2: Run failing tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py -q
```

Expected: FAIL for new missing function.

**Step 3: Implement detail URL validator**

Add:

```python
def validate_announcement_detail_url(url: str, allowed_domains: tuple[str, ...] | None = None) -> None:
```

Rules:

```text
url non-empty
scheme == https
host passes existing host_allowed()
host is not localhost / 127.0.0.1 / ::1
path contains /support/announcement/
no file:// or private IP host
```

Use stdlib `ipaddress` for private IP checks where hostname is an IP literal.

**Step 4: Verify client tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py -q
```

Expected: PASS.

---

## Task 5: Add Detail Payload Storage Path

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py`

**Step 1: Write failing storage test**

Add:

```python
def test_build_detail_payload_path_under_announcement_detail(tmp_path):
    path = build_detail_payload_path(tmp_path, timestamp_ms=1710000000000, source_article_id="abc123", suffix="json")
    assert path.parent.name == "2024-03-09"
    assert path.parent.parent.name == "announcement_detail"
    assert path.parent.parent.parent.name == "raw_payloads"
    assert path.name == "abc123.json"
```

**Step 2: Run failing test**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py::test_build_detail_payload_path_under_announcement_detail -q
```

Expected: FAIL because helper does not exist.

**Step 3: Implement helper**

Add:

```python
def build_detail_payload_path(root: str | Path, timestamp_ms: int, source_article_id: str, suffix: str = "json") -> Path:
```

Rules:

```text
root/raw_payloads/announcement_detail/YYYY-MM-DD/{safe_article_id}.{suffix}
safe_article_id = alnum, dash, underscore only; fallback to sha256 if unsafe/missing
suffix allowlist = json/html/txt
```

**Step 4: Verify storage tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py -q
```

Expected: PASS.

---

## Task 6: Add Detail Payload Persistence Utility

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py`

**Step 1: Write failing persistence test**

Add:

```python
def test_write_detail_payload_persists_payload_and_returns_hash(tmp_path):
    result = write_detail_payload(
        root=tmp_path,
        timestamp_ms=1710000000000,
        source_article_id="abc123",
        payload={"data": {"body": "ABCUSDT"}},
    )

    assert result["payload_size_bytes"] > 0
    assert len(result["payload_sha256"]) == 64
    path = result["payload_path"]
    assert path.endswith("abc123.json")
    assert (tmp_path / path).exists() or Path(path).exists()


def test_write_detail_payload_handles_bytes_payload(tmp_path):
    result = write_detail_payload(
        root=tmp_path,
        timestamp_ms=1710000000000,
        source_article_id="abc123",
        payload=b"AMDUSDT QCOMUSDT",
    )

    assert result["payload_path"].endswith("abc123.txt")
    assert len(result["payload_sha256"]) == 64
```

Adjust path assertion based on whether implementation returns relative or absolute path. Prefer relative-to-output-root for manifest readability.

**Step 2: Run failing test**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py::test_write_detail_payload_persists_payload_and_returns_hash -q
```

Expected: FAIL because helper does not exist.

**Step 3: Implement helper**

Add:

```python
def write_detail_payload(root: str | Path, timestamp_ms: int, source_article_id: str, payload: object) -> dict:
```

Rules:

```text
1. JSON-serializable payload -> .json with json.dumps(sort_keys=True).
2. str payload that appears html -> .html, else .txt.
3. bytes payload -> decode utf-8 with replacement and store .txt unless implementation has stronger type info.
4. Return payload_path, payload_size_bytes, payload_sha256.
5. Parent directories created automatically.
```

**Step 4: Verify storage tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py -q
```

Expected: PASS.

---

## Task 7: Support Detail Metadata In Normalization

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Write failing tests for detail override**

Add:

```python
def test_normalize_event_uses_detail_symbols_override():
    row = normalize_live_event(
        raw={"title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts", "code": "tradfi"},
        source_parent_url="https://www.binance.com/en/support/announcement",
        detected_at_ms=10_000,
        source_published_at_ms=1_000,
        source_published_at_ms_confidence="medium",
        symbols_override=["AMDUSDT", "QCOMUSDT"],
        extraction_metadata={
            "symbol_extraction_source": "detail",
            "detail_fetch_attempted": True,
            "detail_fetch_status": "success",
            "symbol_parse_failed_reason": None,
            "symbol_parse_status": "parsed",
        },
    )

    assert row["symbols"] == ("AMDUSDT", "QCOMUSDT")
    assert row["base_assets"] == ("AMD", "QCOM")
    assert row["symbol_extraction_source"] == "detail"
    assert row["symbol_parse_status"] == "parsed"
    assert row["stable_event_key"] == "binance_tradfi_MULTI"
    assert len(row["event_id"]) == 64


def test_multi_symbol_detail_event_id_is_stable_across_symbol_order():
    raw = {"title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts", "code": "tradfi"}
    kwargs = {
        "raw": raw,
        "source_parent_url": "https://www.binance.com/en/support/announcement",
        "detected_at_ms": 10_000,
        "source_published_at_ms": 1_000,
        "source_published_at_ms_confidence": "medium",
        "extraction_metadata": {
            "symbol_extraction_source": "detail",
            "detail_fetch_attempted": True,
            "detail_fetch_status": "success",
            "symbol_parse_failed_reason": None,
            "symbol_parse_status": "parsed",
        },
    }
    a = normalize_live_event(symbols_override=["AMDUSDT", "QCOMUSDT", "USARUSDT"], **kwargs)
    b = normalize_live_event(symbols_override=["USARUSDT", "AMDUSDT", "QCOMUSDT"], **kwargs)

    assert a["stable_event_key"] == "binance_tradfi_MULTI"
    assert b["stable_event_key"] == "binance_tradfi_MULTI"
    assert a["event_id"] == b["event_id"]
```

**Step 2: Run failing test**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_normalize_event_uses_detail_symbols_override -q
```

Expected: FAIL until Task 2 implementation supports overrides correctly.

**Step 3: Implement normalization override cleanly**

Make sure:

```text
symbols_override affects symbols/base_assets/stable_event_key/event_id.
metadata fields are always present.
no metadata can override safety flags.
empty override still terminal_failed unless metadata explicitly pending_retry/terminal_failed.

stable_event_key / event_id multi-symbol rule:
  if len(symbols) == 0:
    stable_event_key = binance_{code}_UNKNOWN
    event_id = sha256(stable_event_key)
  if len(symbols) == 1:
    stable_event_key = binance_{code}_{symbol}
    event_id = sha256(stable_event_key)
  if len(symbols) > 1:
    stable_event_key = binance_{code}_MULTI
    event_id = sha256(f"{stable_event_key}|{','.join(sorted(symbols))}")

Do not split multi-symbol article rows in Stage 1.5D. Stage 1.5F will flatten event row symbols into event-symbols by hashing event_id|symbol.
```

**Step 4: Verify parser tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: PASS.

---

## Task 8: Add Detail Fallback State And Retry Semantics In Runner

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing transient retry test**

Add test with patched `fetch_public_json`:

```python
def test_detail_fetch_transient_failure_does_not_permanently_dedup_article(tmp_path):
    # poll 1: list payload has TradFi article, detail fetch fails
    # poll 2: same list article, detail fetch succeeds with AMDUSDT
    # expected: events file contains one parsed AMDUSDT event, not permanent symbols=[] miss
```

Implementation sketch:

```python
calls = {"detail": 0}

def fake_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
    if "article/list/query" in url:
        return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "payload_size_bytes": 100, "error": None}
    if "/support/announcement/tradfi" in url:
        calls["detail"] += 1
        if calls["detail"] == 1:
            return {"ok": False, "payload": None, "final_url": url, "http_status": 503, "payload_size_bytes": 0, "error": "temporary"}
        return {"ok": True, "payload": {"body": "AMDUSDT QCOMUSDT"}, "final_url": url, "http_status": 200, "payload_size_bytes": 20, "error": None}
```

Assertions:

```text
summary["detail_fetch_failed_count"] >= 1
summary["detail_fetch_success_count"] >= 1
events jsonl has exactly one tradfi article row with symbols ["AMDUSDT", "QCOMUSDT"]
no duplicate parsed tradfi row
poll 1 detail 503 does not emit a terminal_failed TradFi row
```

**Step 2: Run failing test**

Run:

```bash
PYTHONPATH=src:. pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_detail_fetch_transient_failure_does_not_permanently_dedup_article -q
```

Expected: FAIL because detail fallback/retry does not exist.

**Step 3: Implement runner state**

In `main()`, add:

```python
detail_retry_state = {}
terminal_event_ids = set()
```

Do not add pending retry rows to `seen_event_ids` as terminal success. Recommended approach:

```text
1. For every futures launch article, build normalized event candidate.
2. If title symbols present: emit/dedupe normally.
3. If symbols empty: attempt detail fallback subject to budget/retry/max-age.
4. If detail status parsed: emit event and mark seen_event_ids.
5. If pending_retry: do not append any row to `events/<date>.jsonl`; keep `retry_state` only. A future diagnostic stream may be designed separately, but is out of scope for this implementation.
6. If terminal_failed: append event with symbols=[] and mark seen_event_ids to avoid endless retries.
```

Keep implementation minimal: no new stream required unless needed by tests. Summary counters must still count pending/failed attempts.

**Step 4: Verify transient retry test**

Run:

```bash
PYTHONPATH=src:. pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_detail_fetch_transient_failure_does_not_permanently_dedup_article -q
```

Expected: PASS.

**Step 5: Add max-age expiry test**

Add:

```python
def test_detail_max_age_expired_marks_terminal_failed(tmp_path):
    # poll 1 creates pending_retry for a symbols=[] futures launch article.
    # later poll occurs after EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC.
    # expected: terminal_failed row is emitted exactly once with symbols=[].
```

Patch time or use controlled `detected_at_ms`/config so the retry state exceeds max age.

Assertions:

```text
events jsonl contains one TradFi row
row["symbols"] == []
row["symbol_parse_status"] == "terminal_failed"
row["symbol_parse_failed_reason"] in {"detail_retry_max_age_exceeded", "detail_retry_exhausted"}
summary["detail_symbol_parse_failed_count"] >= 1
```

Run:

```bash
PYTHONPATH=src:. pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_detail_max_age_expired_marks_terminal_failed -q
```

Expected: FAIL before implementation, PASS after retry max-age logic.

---

## Task 9: Add Detail Fetch Budget Deferred Retry Test

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing test**

Add:

```python
def test_detail_budget_deferred_retries_next_poll(tmp_path):
    # Fixture/list payload has two symbols=[] futures launch articles.
    # Patch config EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL = 1.
    # max-polls=2.
    # Expected: both detail pages eventually fetched across two polls.
```

Assertions:

```text
summary["detail_fetch_budget_deferred_count"] >= 1
summary["detail_fetch_success_count"] == 2
events jsonl has two parsed detail rows
```

**Step 2: Run failing test**

Run:

```bash
PYTHONPATH=src:. pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_detail_budget_deferred_retries_next_poll -q
```

Expected: FAIL until budget logic exists.

**Step 3: Implement per-poll detail budget**

Use config:

```python
detail_budget_remaining = base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL
```

When exhausted:

```text
detail_fetch_status = budget_deferred
symbol_parse_status = pending_retry
increment detail_fetch_budget_deferred_count
retry in later poll
```

**Step 4: Verify**

Run the test again. Expected: PASS.

---

## Task 10: Add Detail Payload Persistence And Manifest Integration In Runner

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing manifest/payload test**

Add:

```python
def test_detail_request_manifest_and_payload_are_written(tmp_path):
    # One symbols=[] TradFi article, detail payload contains AMDUSDT.
    # Run max-polls=1 with live_public_readonly and patched fetch.
```

Assertions:

```text
request_manifest contains source_type == "announcement_detail"
manifest row has payload_sha256, payload_size_bytes, parser_version, symbol_extraction_version
raw_payloads/announcement_detail/YYYY-MM-DD/*.json exists
persisted payload contains AMDUSDT
```

**Step 2: Run failing test**

Run:

```bash
PYTHONPATH=src:. pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_detail_request_manifest_and_payload_are_written -q
```

Expected: FAIL.

**Step 3: Implement manifest/payload persistence**

In runner detail fetch path:

```text
1. Validate initial detail URL before fetch.
2. Fetch detail URL via fetch_public_json.
3. After fetch_public_json returns, validate fetch_result["final_url"] with validate_announcement_detail_url().
4. If final_url is invalid:
   - do not parse payload
   - do not persist payload as trusted detail evidence
   - emit terminal_failed diagnostic
   - detail_fetch_status = final_url_not_allowlisted
   - increment detail_fetch_url_rejected_count
5. On valid success, call write_detail_payload(output_root, now_ms, source_article_id, payload).
6. Add payload_sha256/payload_size_bytes/payload_path/parser_version/symbol_extraction_version to request_manifest row.
7. Append request_manifest row before parsing result or immediately after fetch result.
```

**Step 4: Verify**

Run test again. Expected: PASS.

---

## Task 11: Add Detail URL Failure Tests In Runner

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing runner tests**

Add:

```python
def test_detail_url_missing_marks_url_missing_without_crash(tmp_path): ...
def test_detail_url_not_allowlisted_marks_terminal_failed_without_network(tmp_path): ...
def test_detail_redirect_to_non_allowlisted_host_rejected(tmp_path): ...
# This must validate fetch_result["final_url"] after fetch, not only the initially requested URL.
```

For non-allowlisted URL, construct raw article with `code` or parent URL causing unsafe detail URL if practical; otherwise patch validator to raise and assert runner handles it.

Assertions:

```text
rc == 0
summary["detail_fetch_url_rejected_count"] >= 1
symbol_parse_failed_count >= 1
event diagnostic detail_fetch_status == url_missing, url_not_allowlisted, or final_url_not_allowlisted
```

**Step 2: Run failing tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -k "detail_url" -q
```

Expected: FAIL until runner handles URL errors.

**Step 3: Implement safe URL handling**

Before fetch:

```text
1. Validate URL.
2. If missing/invalid: no network call.
3. Emit terminal_failed diagnostic.
4. Increment detail_fetch_url_rejected_count where applicable.
```

**Step 4: Verify**

Run URL tests. Expected: PASS.

---

## Task 12: Add Summary Counters

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing summary test**

Add:

```python
def test_summary_includes_detail_fallback_counters():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True}],
        events=[],
        request_manifest=[],
        fixture_run=True,
        debug_short_run=True,
        observation_hours=0.0,
        counters={
            "detail_fetch_attempted_count": 2,
            "detail_fetch_success_count": 1,
            "detail_fetch_failed_count": 1,
            "detail_fetch_budget_deferred_count": 1,
            "detail_fetch_url_rejected_count": 0,
            "detail_symbol_extracted_count": 1,
            "detail_symbol_parse_failed_count": 1,
            "title_symbol_extracted_count": 3,
            "symbol_empty_event_count": 1,
        },
    )

    assert summary["detail_fetch_attempted_count"] == 2
    assert summary["detail_symbol_extracted_count"] == 1
    assert summary["title_symbol_extracted_count"] == 3
```

**Step 2: Run failing test**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py::test_summary_includes_detail_fallback_counters -q
```

Expected: FAIL because fields are missing.

**Step 3: Implement summary fields**

Add fields with `counters.get(name, default)` for all required counters.

Default values should be computed from events where practical:

```text
title_symbol_extracted_count = count events with symbol_extraction_source == title
detail_symbol_extracted_count = count events with symbol_extraction_source == detail and symbols
symbol_empty_event_count = count futures launch events with no symbols
```

**Step 4: Wire runner counters**

In runner, initialize and update:

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

Pass them into `build_smoke_summary(counters=...)`.

**Step 5: Verify summary tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py -q
```

Expected: PASS.

---

## Task 13: Update Existing Runner Count Test For New Detail Behavior

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Context:** Existing `test_runner_dedupes_repeated_fixture_polls_and_splits_counts` currently expects the `Multiple TradFi` row to remain symbol failed. After detail fallback, fixture mode without detail payload must still not call network and should classify as pending/failed according to fixture semantics.

**Step 1: Decide fixture behavior explicitly**

Use this rule:

```text
fixture-json list payload without detail fixture -> detail_fetch_status = fixture_missing, symbol_parse_status = pending_retry for that poll; no live network call.
```

For a short fixture smoke, summary may show `detail_fetch_failed_count` or a dedicated fixture_missing count only if implemented. The event should not become parsed unless fixture includes detail payload.

**Step 2: Update test assertions**

Ensure the test asserts:

```text
no live network called
raw_futures_launch_article_count remains correct
symbol_parsed_event_count only counts title-parsed rows
symbol_parse_failed_count or symbol_empty_event_count reflects missing detail
```

Because `pending_retry` rows must not be emitted to `events/*.jsonl`, update expected `deduped_new_event_count` to count only parsed or terminal_failed emitted rows, and document this in the test comment.

**Step 3: Run runner tests**

Run:

```bash
PYTHONPATH=src:. pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py -q
```

Expected: PASS.

---

## Task 14: Add Fixture With Detail Payload Support If Needed

**Files:**
- Modify: `tests/fixtures/external_signal_shadow/stage1_5d/binance_futures_launch_fixture.json` OR create a new fixture file
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Prefer in-test fixture first**

Use tmp_path JSON in tests unless a reusable fixture is clearly cleaner.

Recommended fixture shape:

```json
{
  "data": {
    "catalogs": [{
      "articles": [{
        "code": "tradfi",
        "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
        "releaseDate": 1710000000000,
        "detailPayload": {
          "body": "AMDUSDT QCOMUSDT USARUSDT"
        }
      }]
    }]
  }
}
```

Implementation can read `detailPayload` only in fixture mode; live mode must fetch from detail URL.

**Step 2: Add test**

```python
def test_runner_fixture_detail_payload_extracts_multiple_tradfi_symbols_without_network(tmp_path): ...
```

Assertions:

```text
summary detail_symbol_extracted_count == 1
events row symbols == ["AMDUSDT", "QCOMUSDT", "USARUSDT"]
request_manifest may include source_type fixture_detail or announcement_detail with file URL, but no real network
```

**Step 3: Verify**

Run:

```bash
PYTHONPATH=src:. pytest tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_runner_fixture_detail_payload_extracts_multiple_tradfi_symbols_without_network -q
```

Expected: PASS.

---

## Task 15: Full Stage 1.5D Regression Test Suite

**Files:**
- No code changes unless tests expose regressions.

**Step 1: Run focused Stage 1.5D tests**

Run:

```bash
PYTHONPATH=src:. pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: PASS.

**Step 2: Add explicit 1.5F legacy-row compatibility test**

Add to `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`:

```python
def test_stage1_5f_loader_accepts_legacy_1_5d_event_rows_without_symbol_extraction_diagnostics(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(json.dumps({
        "event_id": "legacy-event",
        "event_type": "futures_contract_launch",
        "symbols": ["ABCUSDT"],
        "detected_at_ms": 1_000,
        "source_article_id": "abc",
    }) + "\n")

    rows = list(iter_stage1_5d_event_rows(str(events)))
    flattened = list(flatten_event_symbols(rows[0]))

    assert flattened[0]["symbol"] == "ABCUSDT"
    assert make_event_symbol_id(rows[0], "ABCUSDT")
```

Reason: current server artifacts and older local artifacts do not have `symbol_extraction_source`, `parser_version`, or `symbol_parse_status`; 1.5F must remain backward compatible.

**Step 3: Run adjacent 1.5F loader/observer tests**

Because 1.5F consumes 1.5D event rows, run:

```bash
PYTHONPATH=src:. pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Expected: PASS.

---

## Task 16: Safety Grep

**Files:**
- No code changes unless unsafe hits appear.

**Step 1: Run safety grep**

Run:

```bash
rg -n "apiKey\s*=|api_key\s*=|secret\s*=|from .*TradeIntent|TradeIntent\(|from .*SignalCandidate|SignalCandidate\(|order_endpoint\s*=\s*True|private_ws" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d*
```

Expected: no unsafe hits. Explicit safety fields like `api_key_allowed = false` are acceptable if they appear.

**Step 2: Run import grep**

Run:

```bash
rg -n "TradeIntent|SignalCandidate|order_endpoint|account_endpoint|private_ws|paper_trading_allowed\s*=\s*True|live_trading_allowed\s*=\s*True|execution_engine_allowed\s*=\s*True" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d*
```

Expected: no unsafe true/import hits.

**Step 3: Run HTTP/trading-call safety grep**

Run:

```bash
rg -n "create_order|cancel_order|fetch_balance|withdraw|transfer|requests\.post|httpx\.post|ccxt|wallet|private_key|signed_tx|raw_tx|order_request|swap_request" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d*
```

Expected: no unsafe hits. This Stage 1.5D patch should use existing stdlib urllib client only and must not introduce trading libraries or POST/order/account primitives.

---

## Task 17: Local Smoke Commands

**Files:**
- No code changes unless command reveals a bug.

**Step 1: Run fixture smoke with title-only symbol**

Run existing fixture smoke or create tmp fixture. Example:

```bash
PYTHONPATH=src:. python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  --fixture-json tests/fixtures/external_signal_shadow/stage1_5d/binance_futures_launch_fixture.json \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-root data/external_signal_shadow/stage1_5d/local_fixture_detail_test \
  --output-summary data/external_signal_shadow/stage1_5d/local_fixture_detail_test/binance_futures_launch_smoke_summary.json \
  --max-polls 1
```

Expected:

```text
rc = 0
summary exists
no live network required if fixture-json used
```

If local `data/` upstream summaries are missing, create temporary upstream summary JSON files under a local ignored directory such as `data/external_signal_shadow/stage1_5d/local_fixture_detail_test/upstream_mock/` using the same minimal fields from `_write_valid_upstream()` in `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`. Do not let CI depend on private local `data/` artifacts.

**Step 2: Inspect summary**

Run:

```bash
cat data/external_signal_shadow/stage1_5d/local_fixture_detail_test/binance_futures_launch_smoke_summary.json 2>/dev/null || true
find data/external_signal_shadow/stage1_5d/local_fixture_detail_test -maxdepth 4 -type f | sort | tail -n 30
```

Expected: detail counters present if fixture triggers detail fallback.

---

## Task 18: Review Document Update

**Files:**
- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

**Step 1: Update known issue section**

Update `## 9.3 已知问题与非阻断修复项` after implementation:

```text
status = fixed_locally_pending_server_rollout
fixed_by = Stage 1.5D Multiple TradFi Symbol Extraction
server_current_run_affected = false unless deployed/restarted
rollout_recommendation = start a new 1.5D output root after deployment
```

**Step 2: Add deployment note**

Add explicit note:

```text
Do not deploy into an existing 7d output root. After server rollout, start a new Stage 1.5D run with a fresh output-root and bootstrap a matching Stage 1.5F observer.
```

**Step 3: Verify docs grep**

Run:

```bash
rg -n "Multiple TradFi|symbol extraction|fixed_locally|fresh output-root|detail payload" \
  docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md
```

Expected: updated review section is present.

---

## Final Verification Checklist

Run all:

```bash
PYTHONPATH=src:. pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_client.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_storage.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q

rg -n "apiKey\s*=|api_key\s*=|secret\s*=|from .*TradeIntent|TradeIntent\(|from .*SignalCandidate|SignalCandidate\(|order_endpoint\s*=\s*True|private_ws" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d*

rg -n "create_order|cancel_order|fetch_balance|withdraw|transfer|requests\.post|httpx\.post|ccxt|wallet|private_key|signed_tx|raw_tx|order_request|swap_request" \
  src/research/external_signal_shadow/stage1_5d_*.py \
  scripts/external_signal_shadow/*stage1_5d*
```

Expected:

```text
pytest = all selected tests pass
safety grep = no unsafe hits
```

## Completion Criteria

```text
1. Detail payload is persisted for every detail fallback attempt.
2. Manifest includes payload_sha256 / payload_size_bytes / parser_version / symbol_extraction_version.
3. Every futures_contract_launch row has mandatory symbol extraction diagnostics.
4. Transient detail failures remain retryable and are not swallowed by dedupe.
5. Detail URL safety gate rejects unsafe URLs and redirect final host drift.
6. Summary includes required title/detail/failure counters.
7. Existing title-only path behavior remains unchanged.
8. No server deployment or process restart is performed by this local implementation.
9. No paper/live/execution/alpha claim is introduced.
10. This patch cannot be used to prove execution feasibility, alpha validity, historical 12h entry fillability, or readiness for paper/live trading.
```
