# Stage 1.5D Title Contract Symbol and Transient Detail Retry Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 Stage 1.5D 对 `ETHUSD1` 这类标题内 raw futures contract symbol 的漏抽，并防止 Binance detail `HTTP 202 + empty body` 被过早写成 terminal failed。

**Architecture:** 复用已有 `candidate_symbols + exchangeInfo` 验证通道，把 title 中的 raw contract candidates 先送入 exchangeInfo validation；只有 title 无法给出 candidate 时才进入 detail fallback。detail transient unavailable 不再受 3 次 max retry 直接终态化，而是按 transient max-age 持续 pending retry，并通过 request manifest / counters 审计。

**Tech Stack:** Python 3.12, pytest, stdlib `urllib`, existing Stage 1.5D parser/client/runner/storage, Binance USD-M public `exchangeInfo`, JSONL artifacts, `configs/base.py`.

---

## 0. Current Root Cause

Observed live server output:

```text
23c9b8e88309409cbcd8509af0b78d10
title = Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)
symbols = []
detail_fetch_status = retry_exhausted
symbol_parse_status = terminal_failed

d2acaa91c14e4cc598aaee1017efc1ac
title = Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)
symbols = []
detail_fetch_status = retry_exhausted
symbol_parse_status = terminal_failed

request_manifest detail rows:
http_status = 202
payload_size_bytes = 0
payload_trusted = false
error = detail_payload_http_status_202
```

Root causes:

1. `extract_futures_launch_symbols()` only accepts `XXXUSDT` / `XXXUSDC`, so `ETHUSD1` is treated as no-symbol even though it is in the title.
2. The runner sends no-symbol rows to detail fallback. If Binance detail keeps returning `202 + empty`, the current `retry_count >= EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES` path emits `terminal_failed` after only a few attempts.
3. `HTTP 202 + empty` is transient evidence, not terminal parser evidence. It should remain pending until a transient max-age expires.
4. `configs/base.py` currently allows `("USDT", "USDC", "U")` but not `USD1`, so `ETHUSD1` would be rejected by structured exchangeInfo validation unless config is explicitly updated.
5. The runner currently increments `state["retry_count"] += 1` before fetch. This line must be removed/replaced; otherwise transient and non-transient retry counters conflict.

Non-goals:

1. Do not mark already missed 2026-07-02 events as valid 12h live depth evidence.
2. Do not add any paper/live trading or execution behavior.
3. Do not weaken exchangeInfo validation for raw symbols.
4. Do not use this hotfix to create official 12h live depth evidence for already-watermarked 2026-07-02/2026-07-03 rows.

Safety boundary:

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

---

## Task 1: Parser title contract candidate extraction

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

### Step 1: Write failing parser tests

Add tests:

```python
def test_title_extracts_raw_contract_symbol_candidate_ethusd1():
    title = "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)"

    result = extract_symbol_candidates_from_title(title, max_symbols=30)

    assert result["symbols"] == ["ETHUSD1"]
    assert result["symbol_extraction_source"] == "title_contract_symbol"
    assert result["symbol_derivation_method"] == "none"
    assert result["symbol_validation_status"] == "requires_exchange_info_validation"


def test_title_prefers_exact_usdt_usdc_symbols_as_parsed_title_symbols():
    title = "Binance Futures Will Launch USDⓈ-Margined CAPUSDT Perpetual Contract (2026-06-27)"

    result = extract_symbol_candidates_from_title(title, max_symbols=30)

    assert result["symbols"] == ["CAPUSDT"]
    assert result["symbol_extraction_source"] == "title"
    assert result["symbol_validation_status"] == "validated_by_exact_text"


def test_title_contract_candidate_does_not_collect_generic_words():
    title = "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)"

    result = extract_symbol_candidates_from_title(title, max_symbols=30)

    assert result["symbols"] == []


def test_title_candidate_extraction_only_scans_margin_to_perpetual_segment():
    title = "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract; Risk Warning ABCDEF"

    result = extract_contract_symbol_candidates_from_title(title, max_symbols=30)

    assert result == ["ETHUSD1"]


def test_title_candidate_rejects_usds_margined_generic_title_without_symbol():
    title = "Binance Futures Will Launch Multiple USDS-Margined TradFi Perpetual Contracts (2026-07-02)"

    assert extract_contract_symbol_candidates_from_title(title, max_symbols=30) == []


def test_title_candidate_rejects_date_and_generic_words():
    title = "Binance Futures Will Launch USDⓈ-Margined Perpetual Contract (2026-07-03)"

    assert extract_contract_symbol_candidates_from_title(title, max_symbols=30) == []
```

### Step 2: Run tests and confirm fail

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_title_extracts_raw_contract_symbol_candidate_ethusd1 \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_title_prefers_exact_usdt_usdc_symbols_as_parsed_title_symbols \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_title_contract_candidate_does_not_collect_generic_words \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_title_candidate_extraction_only_scans_margin_to_perpetual_segment \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_title_candidate_rejects_usds_margined_generic_title_without_symbol \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py::test_title_candidate_rejects_date_and_generic_words \
  -q
```

Expected:

```text
FAIL because extract_symbol_candidates_from_title is missing
```

### Step 3: Implement title-specific candidate extraction

Do not call `extract_contract_symbol_candidates_from_detail_text(title, max_symbols)` from title extraction. Detail helper is tuned for body/table windows; title extraction must use a narrower title-specific segment.

Add function:

```python
def extract_contract_symbol_candidates_from_title(title: str, max_symbols: int) -> list[str]:
    if classify_event_type(title) != "futures_contract_launch":
        return []

    margin = re.search(r"(?:USDⓈ|USDS|USD)-Margined|(?:USDⓈ|USDS|USD)-M", title, re.IGNORECASE)
    perp = re.search(r"perpetual\s+contracts?", title, re.IGNORECASE)
    launch = re.search(r"will\s+launch|launch", title, re.IGNORECASE)
    if not margin or not perp or not launch:
        return []
    if margin.end() >= perp.start():
        return []

    segment = title[margin.end():perp.start()]
    tokens = re.findall(r"\b[A-Z][A-Z0-9]{1,29}\b", segment)
    out = []
    for token in tokens:
        if token in CONTRACT_SYMBOL_CANDIDATE_STOPWORDS:
            continue
        if token.isdigit():
            continue
        if re.fullmatch(r"\d{4}|\d{2}|\d{8}", token):
            continue
        out.append(token)
        if len(out) >= max_symbols:
            break
    return _dedupe(out)
```

Add wrapper:

```python
def extract_symbol_candidates_from_title(title: str, max_symbols: int) -> dict:
    exact_symbols = extract_futures_launch_symbols(title)[:max_symbols]
    if exact_symbols:
        return {
            "symbols": exact_symbols,
            "symbol_extraction_source": "title",
            "symbol_derivation_method": "none",
            "quote_derivation_source": None,
            "symbol_validation_status": "validated_by_exact_text",
            "symbol_launch_times_ms": {},
        }

    raw_candidates = extract_contract_symbol_candidates_from_title(title, max_symbols)
    if raw_candidates:
        return {
            "symbols": raw_candidates,
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_derivation_method": "none",
            "quote_derivation_source": "exchange_info",
            "symbol_validation_status": "requires_exchange_info_validation",
            "symbol_launch_times_ms": {},
        }

    return {
        "symbols": [],
        "symbol_extraction_source": None,
        "symbol_derivation_method": None,
        "quote_derivation_source": None,
        "symbol_validation_status": None,
        "symbol_launch_times_ms": {},
    }
```

Implementation notes:

1. Do not mark `ETHUSD1` parsed without exchangeInfo validation.
2. Do not derive `ETHUSD1USDT`.
3. Keep existing `extract_futures_launch_symbols()` behavior unchanged for `XXXUSDT` / `XXXUSDC`.

### Step 4: Verify parser tests pass

Run the command from Step 2.

Expected:

```text
6 passed
```

---

## Task 2: Config allows USD1 explicitly

**Files:**

- Modify: `configs/base.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`

### Step 1: Write failing config test

Add:

```python
def test_stage1_5d_allows_usd1_futures_assets_for_exchangeinfo_validated_contracts():
    assert "USD1" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS
    assert "USD1" in base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS
```

### Step 2: Run and confirm fail

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py::test_stage1_5d_allows_usd1_futures_assets_for_exchangeinfo_validated_contracts \
  -q
```

Expected:

```text
FAIL because USD1 is absent from both allowlists
```

### Step 3: Add USD1 to centralized config

Modify `configs/base.py`:

```python
EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS = ("USDT", "USDC", "U", "USD1")
EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS = ("USDT", "USDC", "U", "USD1")
```

Reason:

```text
ETHUSD1 is valid only after exchangeInfo confirms symbol=ETHUSD1 with quoteAsset/marginAsset USD1.
USD1 must be centrally configured; runner must not implicitly bypass validation.
```

### Step 4: Verify config test passes

Run command from Step 2.

Expected:

```text
1 passed
```

---

## Task 3: Runner validates title contract candidates before detail fetch

**Files:**

- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

### Step 1: Write failing runner test for ETHUSD1 TRADING title path

Add test:

```python
def test_runner_validates_title_contract_symbol_ethusd1_without_detail_fetch(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "23c9b8e88309409cbcd8509af0b78d10",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)",
                    "releaseDate": 1782989104900,
                }]
            }]
        }
    }
    exchange_info = {
        "symbols": [{
            "symbol": "ETHUSD1",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "quoteAsset": "USD1",
            "marginAsset": "USD1",
            "onboardDate": 1782989000000,
        }]
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        if "klines" in url:
            return {"ok": True, "payload": [], "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    detail_calls = {"count": 0}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        raise AssertionError("title contract symbol path must not fetch detail")

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    parsed = [r for r in events if r.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10"]
    assert len(parsed) == 1
    assert parsed[0]["symbols"] == ["ETHUSD1"] or parsed[0]["symbols"] == ("ETHUSD1",)
    assert parsed[0]["symbol_parse_status"] == "parsed"
    assert parsed[0]["symbol_extraction_source"] == "title_contract_symbol"
    assert parsed[0]["symbol_validation_status"] == "validated"
    assert parsed[0]["detail_fetch_attempted"] is False
    assert parsed[0]["detail_fetch_status"] == "not_needed"
    assert detail_calls["count"] == 0
```

### Step 2: Write failing runner test for title candidate pending without detail fetch

Add test:

```python
def test_runner_title_contract_symbol_pre_trading_stays_pending_without_detail_fetch(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "23c9b8e88309409cbcd8509af0b78d10",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)",
                    "releaseDate": 1782989104900,
                }]
            }]
        }
    }
    exchange_info = {
        "symbols": [{
            "symbol": "ETHUSD1",
            "contractType": "PERPETUAL",
            "status": "PENDING_TRADING",
            "quoteAsset": "USD1",
            "marginAsset": "USD1",
            "onboardDate": 1783069200000,
        }]
    }

    detail_calls = {"count": 0}

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        raise AssertionError("pending title candidate must not fetch detail")

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(row.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10" for row in events)
    assert detail_calls["count"] == 0
```

### Step 3: Write failing restart-safe pending test

Add test:

```python
def test_title_contract_candidate_pending_survives_process_restart_without_detail_fetch(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "23c9b8e88309409cbcd8509af0b78d10",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)",
                    "releaseDate": 1782989104900,
                }]
            }]
        }
    }
    pending_exchange_info = {"symbols": []}
    trading_exchange_info = {
        "symbols": [{
            "symbol": "ETHUSD1",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "quoteAsset": "USD1",
            "marginAsset": "USD1",
            "onboardDate": 1782989000000,
        }]
    }
    detail_calls = {"count": 0}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        raise AssertionError("title candidate restart path must not fetch detail")

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)

    def run_once(exchange_info):
        def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
            if "article/list/query" in url:
                return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
            if "exchangeInfo" in url:
                return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
            if "klines" in url:
                return {"ok": True, "payload": [], "final_url": url, "http_status": 200, "error": None}
            raise AssertionError(url)

        args = [
            "run_stage1_5d_live_event_source_smoke_collector.py",
            "--live-public-readonly",
            "--stage1-5c1-summary", str(c1),
            "--stage1-5c-summary", str(c),
            "--output-root", str(output_root),
            "--output-summary", str(summary),
            "--max-polls", "1",
            "--poll-interval-sec", "0",
        ]
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    return main()

    assert run_once(pending_exchange_info) == 0
    assert _read_jsonl_files(output_root / "events") == []

    assert run_once(trading_exchange_info) == 0
    events = _read_jsonl_files(output_root / "events")
    parsed = [r for r in events if r.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10"]
    assert len(parsed) == 1
    assert parsed[0]["symbols"] == ["ETHUSD1"] or parsed[0]["symbols"] == ("ETHUSD1",)
    assert detail_calls["count"] == 0
```

### Step 4: Run and confirm fail

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_runner_validates_title_contract_symbol_ethusd1_without_detail_fetch \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_runner_title_contract_symbol_pre_trading_stays_pending_without_detail_fetch \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_title_contract_candidate_pending_survives_process_restart_without_detail_fetch \
  -q
```

Expected:

```text
FAIL because runner sends ETHUSD1 title to detail fallback
```

### Step 5: Implement runner title candidate path

1. Import parser function:

```python
from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
    ...
    extract_symbol_candidates_from_title,
)
```

2. In the `else` branch where `ev.get("symbols")` is false, before creating normal detail retry state, call:

```python
title_candidate_res = extract_symbol_candidates_from_title(raw_art.get("title") or "", max_symbols)
```

3. If `title_candidate_res["symbol_validation_status"] == "requires_exchange_info_validation"`:

Create `state` with:

```python
state = {
    "raw": raw_art,
    "first_detected_at_ms": now_ms,
    "retry_count": 0,
    "detail_fetch_attempt_count": 0,
    "transient_detail_error_count": 0,
    "non_transient_detail_error_count": 0,
    "last_retry_at_ms": 0,
    "source_published_at_ms_confidence": ev["source_published_at_ms_confidence"],
    "candidate_symbols": title_candidate_res["symbols"],
    "symbol_extraction_source": title_candidate_res["symbol_extraction_source"],
    "symbol_derivation_method": title_candidate_res["symbol_derivation_method"],
    "quote_derivation_source": "exchange_info",
    "symbol_validation_status": "pending_exchangeinfo_missing",
    "symbol_launch_times_ms": title_candidate_res.get("symbol_launch_times_ms", {}),
    "symbol_onboard_times_ms": {},
    "detail_fetch_attempted": False,
    "detail_fetch_status": "not_needed",
}
```

4. Validate candidates immediately with existing `validate_candidate_symbols_against_exchangeinfo()` helper.

5. If validated:

Emit parsed event with:

```python
"symbol_extraction_source": "title_contract_symbol"
"symbol_derivation_method": "none"
"quote_derivation_source": "exchange_info"
"symbol_validation_status": "validated"
"detail_fetch_attempted": False
"detail_fetch_status": "not_needed"
"symbol_parse_failed_reason": None
"symbol_parse_status": "parsed"
```

6. If pending:

Store state in `detail_retry_state` but do not fetch detail. The existing `"candidate_symbols" in state` branch will revalidate in later polls and `continue` before detail fetch.

Process restart behavior:

```text
Do not depend on in-memory state for correctness.
If process restarts after a pending title candidate, the next announcement list poll must reconstruct the same title candidate from the title and revalidate through exchangeInfo.
```

7. If rejected:

Emit terminal event with explicit `exchange_info_*` reason. Do not fall through to detail fetch.

### Step 6: Verify runner tests pass

Run the command from Step 4.

Expected:

```text
3 passed
```

---

## Task 4: Transient detail 202/empty must not terminal by max retries

**Files:**

- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify: `configs/base.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

### Step 1: Add config

Add to `configs/base.py`:

```python
# Transient detail responses such as Binance HTTP 202 + empty body are not terminal parser failures.
EXTERNAL_SIGNAL_STAGE1_5D_TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC = 86400
```

Reason:

```text
Binance detail pages can remain HTTP 202 + empty for hours.
Sparse event source means a 24h pending window is operationally acceptable.
This does not create trading permission or live evidence by itself.
```

Add config test:

```python
def test_stage1_5d_transient_detail_fetch_max_age_config():
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC == 86400
```

### Step 2: Write failing retry test

Add test:

```python
def test_transient_detail_http_202_does_not_terminal_fail_by_max_retries(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
                    "releaseDate": 1782980108049,
                }]
            }]
        }
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {
            "ok": False,
            "payload": None,
            "requested_url": url,
            "final_url": url,
            "http_status": 202,
            "payload_size_bytes": 0,
            "row_count": None,
            "error": "detail_payload_http_status_202",
        }

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "5",
        "--poll-interval-sec", "0",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES", 3):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(
        row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and row.get("symbol_parse_status") == "terminal_failed"
        for row in events
    )
    s = json.loads(summary.read_text())
    assert s["detail_pending_retry_count"] >= 1
    assert s["detail_http_not_ready_count"] >= 1
    assert s["detail_terminal_failed_count"] == 0
    assert s["detail_transient_timeout_count"] == 0
```

Also add an expiry-specific test:

```python
def test_transient_detail_max_age_terminal_is_detail_unavailable_not_symbol_empty(tmp_path):
    # Same fixture as HTTP 202 test, but patch:
    # EXTERNAL_SIGNAL_STAGE1_5D_TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC = 0
    # Run max-polls=2.
    # Expected: one terminal row with terminal_failure_type=detail_unavailable_timeout.
    # Expected summary: detail_transient_timeout_count == 1.
    # Expected summary: detail_symbol_parse_failed_count == 0 and symbol_empty_event_count == 0 for this path.
```

### Step 3: Run and confirm fail

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py::test_transient_detail_http_202_does_not_terminal_fail_by_max_retries \
  -q
```

Expected:

```text
FAIL because current retry_count reaches retry_exhausted and emits terminal_failed
```

### Step 4: Implement transient retry state separation

Modify state initialization to include:

```python
"detail_fetch_attempt_count": 0,
"transient_detail_error_count": 0,
"non_transient_detail_error_count": 0,
```

Modify detail fetch attempt:

```python
state["detail_fetch_attempt_count"] += 1
state["last_retry_at_ms"] = now_ms
detail_fetch_attempted_count += 1
```

Do not increment `state["retry_count"]` before knowing the error category.

Required code deletion:

```python
# Remove this pre-fetch increment from the current runner:
state["retry_count"] += 1
```

This is currently near the detail fetch attempt block. Leaving it in place will keep triggering the old `retry_exhausted` path for transient HTTP 202 rows.

Modify max retry check:

```python
if state.get("non_transient_detail_error_count", 0) >= max_retries_limit and "candidate_symbols" not in state:
    ...
```

Modify transient error branch:

```python
if is_transient_detail_fetch_error(fetch_res):
    state["transient_detail_error_count"] = state.get("transient_detail_error_count", 0) + 1
    detail_pending_retry_count += 1
    continue
```

Modify non-transient error branch:

```python
state["non_transient_detail_error_count"] = state.get("non_transient_detail_error_count", 0) + 1
state["retry_count"] = state["non_transient_detail_error_count"]
```

Add transient max-age:

```python
has_transient_detail_errors = state.get("transient_detail_error_count", 0) > 0
if has_transient_detail_errors and not has_candidate_symbols:
    transient_max_age = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC", 86400)
    expire = age_sec > transient_max_age
else:
    expire = age_sec > max_age_limit
```

Terminal reason for transient max age:

```python
"detail_fetch_status": "transient_detail_max_age_exceeded"
"symbol_parse_failed_reason": "transient_detail_max_age_exceeded"
"terminal_failure_type": "detail_unavailable_timeout"
```

Counter rule:

```text
Transient detail timeout must not increment:
- detail_symbol_parse_failed_count
- symbol_empty_event_count

It may increment:
- detail_terminal_failed_count
- detail_transient_timeout_count
```

### Step 5: Verify retry test passes

Run command from Step 3.

Expected:

```text
1 passed
```

---

## Task 5: Summary and manifest audit fields

**Files:**

- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`

### Step 1: Ensure counters are present

Required summary fields:

```text
detail_pending_retry_count
detail_empty_payload_count
detail_http_not_ready_count
detail_terminal_failed_count
detail_transient_timeout_count
```

Some fields already exist from the previous hotfix; `detail_transient_timeout_count` is new and must be added in runner counters and `build_smoke_summary()`.

### Step 2: Add/adjust summary test

Add assertions that transient 202 increments:

```python
assert summary["detail_pending_retry_count"] >= 1
assert summary["detail_http_not_ready_count"] >= 1
assert summary["detail_terminal_failed_count"] == 0
assert summary["detail_transient_timeout_count"] == 0
```

### Step 3: Manifest must remain untrusted for 202 empty

Existing manifest expected fields:

```json
{
  "http_status": 202,
  "payload_size_bytes": 0,
  "payload_sha256": null,
  "payload_path": null,
  "payload_trusted": false,
  "response_payload_size_bytes": 0,
  "error": "detail_payload_http_status_202"
}
```

Keep this unchanged.

---

## Task 6: Review documentation update

**Files:**

- Modify: `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md`

### Step 1: Update current known issue section

Add:

```text
2026-07-02 live incident:
- ETHUSD1 title event exposed title raw contract symbol gap.
- Multiple TradFi and ETHUSD1 exposed Binance detail HTTP 202 + empty persistence.
- Fix target is future events only; already-watermarked/terminal rows are recovery validation only.
- It is forbidden to use reparsed 23c9... or d2ac... rows as official 12h live depth evidence.
```

### Step 2: Update monitoring commands

Clarify:

```text
binance_futures_launch_smoke_summary.json is written when 1.5D exits; do not rely on it during active 7d run.
During active run, use heartbeats/events/request_manifest.
```

### Step 3: Add post-hotfix verification command

Add command:

```bash
python - <<'PY'
import glob, json, os
rows = []
for p in glob.glob(os.path.join(os.environ["STAGE1_5D_EVENTS_OUT"], "events", "*.jsonl")):
    for line in open(p):
        if line.strip():
            r = json.loads(line)
            if r.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10":
                rows.append(r)
print(rows[-3:])
PY
```

---

## Task 7: Verification

Run targeted tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Run Stage 1.5F compatibility tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_*.py \
  -q
```

Run external signal suite:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow tests/scripts/external_signal_shadow -q
```

Run full suite before deployment:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest -q
```

Safety grep:

```bash
rg -n "create_order|cancel_order|fetch_balance|withdraw|transfer|requests\\.post|httpx\\.post|ccxt|wallet|private_key|signed_tx|raw_tx|order_request|swap_request|apiKey|secret|TradeIntent|SignalCandidate|private_ws" \
  src/research/external_signal_shadow \
  scripts/external_signal_shadow
```

Expected:

```text
No unsafe hits, except harmless comments if any.
```

---

## Completion Criteria

1. `ETHUSD1` title produces `symbols=["ETHUSD1"]` after exchangeInfo validation.
2. `ETHUSD1` title path does not require detail payload fetch.
3. `Multiple TradFi` without title symbols still uses detail fallback.
4. Repeated `HTTP 202 + empty` detail responses do not terminal fail via `DETAIL_FETCH_MAX_RETRIES`.
5. Transient detail failures remain auditable via request manifest and summary counters.
6. `payload_trusted=false`, `payload_path=null`, and `payload_sha256=null` remain true for 202/empty detail rows.
7. No paper/live trading/execution/alpha flags become enabled.
8. Existing Stage 1.5F loader/depth client tests still pass.
9. Review doc explains that already-watermarked 2026-07-02 events are recovery validation only.
10. Reparsing already terminal/watermarked rows such as `23c9b8e88309409cbcd8509af0b78d10` or `d2acaa91c14e4cc598aaee1017efc1ac` must not be labeled valid 12h live depth evidence.
11. Official Stage 1.5F live depth evidence must come from a new Stage 1.5D output root, a new Stage 1.5F output root, and post-bootstrap post-watermark event-symbols.

---

## Execution Handoff

Plan complete and saved to:

```text
docs/plans/2026-07-02-external-signal-shadow-lab-stage1-5d-title-contract-symbol-and-transient-detail-retry-hotfix-plan_CN.md
```

Recommended execution mode:

```text
TDD implementation in this session after user approval.
```

---

## Actual Changes and Verification Results

### 1. Files Modified
- [configs/base.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/configs/base.py): Centralized allowed futures margin/quote asset lists (`USD1` added) and defined `EXTERNAL_SIGNAL_STAGE1_5D_TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC = 86400`.
- [src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py): Added `extract_contract_symbol_candidates_from_title` and `extract_symbol_candidates_from_title`.
- [src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py): Included `detail_transient_timeout_count` in build smoke summary structure.
- [scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py):
  - Pre-fetch candidate extraction from title segment.
  - Skip detail fallback for title candidates and route them directly to exchangeInfo validation.
  - Track transient fetch error counts and enforce transient max-age limit.
  - Log details and count statistics appropriately.

### 2. Tests Added and Executed
- [tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py): Added 6 title parser candidate extraction test cases.
- [tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py): Added tests for new config keys and `USD1` presence.
- [tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py): Added test for `detail_transient_timeout_count` inclusion.
- [tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py](file:///Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py): Added 3 runner tests for title candidates, and 2 runner tests for transient detail retry/timeout.

### 3. Verification Evidence
Fresh verification after the counter/doc follow-up fix:
```text
Stage 1.5D affected suite: 91 passed in 7.23s
Stage 1.5F compatibility suite: 80 passed in 0.07s
External signal suite: 666 passed in 15.23s
Full repository suite: 1406 passed in 68.72s
git diff --check: clean
```
Safety grep only matched existing `configs/base.py` comment examples for optional API key config; no runtime trading/private API call path was introduced.
