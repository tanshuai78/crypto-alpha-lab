# External Signal Shadow Lab Stage 1.5C.1 Price Coverage Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** 为 Stage 1.5B 的 Binance external catalyst symbol events 扩展可审计的价格覆盖，区分 USD-M futures 可回放、futures launch 上市后可回放、spot proxy 仅观察、以及不可覆盖四类结果。

**Architecture:** 新增独立 `stage1_5c1_price_coverage_*` 模块和 runner。模块读取 Stage 1.5B normalized symbol event table，使用 Binance public readonly endpoints 获取 USD-M exchangeInfo 与 15m klines，并可选获取 spot 15m klines 作为 report-only fallback。Stage 1.5C.1 只解决 data coverage，不计算 forward return，不做 replay，不输出 alpha/paper/live 结论。

**Tech Stack:** Python 3.11、标准库 `urllib.request`、`configs/base.py`、JSON/JSONL、pytest、ruff、`PYTHONPATH=src:.`。

---

## 0. 执行边界

```text
decision = approved_with_major_required_fixes_absorbed
scope = price_coverage_expansion_only
source_stage_required = stage1_5b_event_table_ready
stage1_5c_current_blocker = no_market_pair_overlap_with_price_archive
network_access_mode = explicit_live_public_readonly_only
api_key_allowed = false
private_endpoint_allowed = false
price_join_allowed = true
forward_return_allowed = false
replay_allowed = false
random_baseline_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
execution_engine_allowed = false
```

Stage 1.5C.1 只能回答：

```text
Stage 1.5B 的 symbol events 中，有多少能找到对应的 Binance USD-M futures / spot 15m price history？
这些价格覆盖是否足以让 Stage 1.5C replay 重跑？
```

Stage 1.5C.1 不能回答：

```text
external catalyst 是否有效
futures launch / delisting 是否有 alpha
是否可以 paper/live
是否可以使用 spot proxy 当作 futures execution price
```

### 0.1 当前失败事实

当前 Stage 1.5C 真实 summary：

```text
stage1_5b_symbol_events = 194
allowed_event_type_events = 194
market_pair_existence_verified_count = 0
price_history_coverage_pass_count = 0
candidate_count_after_cooldown = 0
replay_result_primary_rows = 0
blockers = no_price_history_coverage / no_market_pair_overlap_with_price_archive
```

已确认现有 price archive 仅包含：

```text
BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT / DOGEUSDT
```

Stage 1.5B event table 包含 191 个 unique event symbols，且与上述 5 个主流币 0 交集。

### 0.2 关键语义修正

`futures_contract_launch` 与 `exchange_delisting_notice` 的价格覆盖规则不同：

```text
exchange_delisting_notice:
  anchor = notice_time_available_at
  desired source = Binance USD-M futures 15m klines
  required pre-event futures history = 30d if pair existed before notice
  replay eligibility = futures_pre_event_coverage_pass

futures_contract_launch:
  anchor = notice_time_available_at / launch announcement time
  futures pair may not exist before launch
  required futures coverage = post-launch entry/forward windows only
  pre-event 30d futures history is not required for launch event
  optional pre-event spot history = report-only spot proxy context
  replay eligibility = post_launch_futures_coverage_pass, not full pre-event futures history
```

Do not classify a futures launch as invalid merely because the USD-M contract did not exist 30d before launch.

---

## 1. Inputs / Outputs

### 1.1 Required inputs

Stage 1.5B normalized event table:

```text
data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl
```

Stage 1.5B summary:

```text
data/external_signal_shadow/stage1_5b/normalization_summary.json
```

Current Stage 1.5C summary, used only for context:

```text
data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json
```

### 1.2 Outputs

USD-M futures expanded kline archive:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/binance_um_futures_15m_event_symbols.jsonl
```

Optional spot proxy archive, report-only:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/binance_spot_15m_event_symbols_proxy.jsonl
```

Per-symbol/event coverage report:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/event_price_coverage_report.jsonl
```

Coverage-pass event table for clean Stage 1.5C rerun:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/external_catalyst_events_futures_coverage_pass.jsonl
```

Public request manifest for reproducibility:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/request_manifest.jsonl
```

Raw exchangeInfo cache for reproducibility:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/futures_exchange_info_raw.json
data/external_signal_shadow/stage1_5c1/price_coverage/spot_exchange_info_raw.json
```

Machine-readable summary:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json
```

Chinese review:

```text
docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-review_CN.md
```

---

## 2. Core Semantics

### 2.1 Event symbol normalization and validation

Stage 1.5B `symbol` is a research-normalized string, not proof that Binance has a USD-M market.

Stage 1.5C.1 must validate each event symbol against Binance USD-M `exchangeInfo` before requesting futures klines.

Output status values:

```text
futures_symbol_currently_verified
futures_symbol_current_exchangeinfo_not_found
historical_futures_existence_unknown
futures_symbol_invalid_format
futures_symbol_currently_not_trading
spot_symbol_verified_report_only
spot_symbol_not_found
```

Important semantic rule:

```text
Binance exchangeInfo is current-state evidence only.
It can prove a symbol is currently listed/trading.
It cannot prove the symbol never existed historically.
For delisting notices, current exchangeInfo missing must map to historical_futures_existence_unknown, not historically_not_tradable.
```

Suspicious symbols like `4USDTUSDT`, `BTCUSD1USDT`, `AAPLUSDT`, `BABAUSDT`, `AMDUSDT` must not crash the runner. They should be classified by validation output, not silently requested forever.

### 2.2 Public readonly HTTP policy

Network calls are allowed only when the runner receives:

```bash
--live-public-readonly
```

Without this flag, tests and smoke runs must use fixtures or cached payloads.

Hard boundaries:

```text
api_key_used = false
private_endpoint_used = false
order_endpoint_used = false
max_retries_per_request = configured
request_sleep_sec = configured
request_timeout_sec = configured
```

### 2.3 Kline request windows

For each event row, compute request window by event type.

For delisting notices:

```text
start_ms = available_at_ms - (pre_event_history_days + buffer_days) * 24h
end_ms = available_at_ms + max(entry_delay_hours + forward_window_hours) + buffer_days * 24h
```

For futures contract launch:

```text
start_ms = available_at_ms
end_ms = available_at_ms + max(entry_delay_hours + forward_window_hours) + buffer_days * 24h
```

Default values:

```text
pre_event_history_days = 30
post_event_buffer_days = 2
max_entry_delay_hours = 12
max_forward_window_hours = 24
```

Do not request future bars beyond current UTC minus one completed 15m bar.

### 2.4 Request range merging

Multiple events can share a symbol. The downloader should merge overlapping windows per symbol and source:

```text
merge key = source_type + symbol
merge if next.start_ms <= previous.end_ms + merge_gap_ms
```

This avoids excess public requests and reduces rate-limit risk.

### 2.5 Futures vs spot source semantics

Futures rows:

```json
{
  "symbol": "ARXUSDT",
  "bar_start_ms": 1782187200000,
  "bar_end_ms": 1782188100000,
  "open": 0.0,
  "high": 0.0,
  "low": 0.0,
  "close": 0.0,
  "quote_volume": 0.0,
  "source": "binance_um_futures_15m",
  "source_quality": "exchange_futures_kline_close_price_not_fill_price"
}
```

Spot proxy rows:

```json
{
  "symbol": "ARXUSDT",
  "bar_start_ms": 1782187200000,
  "open": 0.0,
  "high": 0.0,
  "low": 0.0,
  "close": 0.0,
  "quote_volume": 0.0,
  "source": "binance_spot_15m_proxy",
  "source_quality": "spot_price_proxy_report_only_not_futures_execution_price"
}
```

Spot proxy must never be mixed into the futures archive. It is report-only unless a later plan explicitly designs spot-proxy replay.

### 2.6 Market scope inference

`exchange_delisting_notice` is not automatically a USD-M futures event. It may be spot delisting, margin pair removal, futures delisting, or unknown.

Each event report must include:

```json
{
  "market_scope_inferred": "spot|um_futures|cross_market|unknown",
  "market_scope_source": "title_pattern|source_profile|manual_review|unknown",
  "futures_price_required": false,
  "futures_coverage_failure_does_not_invalidate_event_source": true
}
```

Rules:

```text
spot delisting:
  futures_price_required = false
  futures coverage failure does not invalidate the event source
  stage1_5c_rerun_candidate = false unless a later plan designs spot replay

um_futures delisting:
  futures_price_required = true
  require event-type-specific futures coverage

unknown market scope:
  coverage_status = market_scope_unknown
  stage1_5c_rerun_candidate = false
```

### 2.7 Kline pagination and not-matured semantics

Binance `/fapi/v1/klines` and `/api/v3/klines` have a max limit of 1500 rows. At 15m resolution, 30d requires about 2880 bars, so every implementation must paginate.

Pagination rule:

```text
while start_ms < end_ms:
  request limit <= EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_LIMIT
  next_start_ms = last_returned_bar_open_time + interval_ms
  stop if API returns empty rows or next_start_ms does not advance
```

If a requested event needs future bars that are not yet mature relative to current time, do not mark it failed. Mark it as not matured:

```json
{
  "futures_kline_status": "post_launch_futures_coverage_not_matured|future_bar_request_truncated",
  "rerun_after_ms": 0,
  "required_last_bar_end_ms": 0
}
```

### 2.8 Futures launch first-bar anchor

For `futures_contract_launch`, `available_at_ms` is announcement availability, not necessarily first tradable futures bar.

Stage 1.5C.1 must output:

```json
{
  "first_futures_bar_start_ms": 0,
  "first_futures_bar_after_available_at_ms": 0,
  "launch_price_anchor_status": "first_futures_bar_after_available_at|no_futures_bar_after_available_at|not_matured",
  "suggested_replay_anchor_ms": 0
}
```

Stage 1.5C rerun must use:

```text
entry_candidate_time_ms = max(
  available_at_ms + entry_delay,
  first_futures_bar_start_ms + entry_delay_after_launch
)
```

Do not compute launch entries before the first available futures bar.

### 2.9 Request manifest / raw cache / request budget

Every real public readonly run must be reproducible enough for review.

The runner must write `request_manifest.jsonl`. Each row must include at least:

```json
{
  "request_id": "...",
  "source_type": "futures|spot",
  "symbol": "ABCUSDT",
  "url_hash": "...",
  "start_ms": 0,
  "end_ms": 0,
  "http_status": 200,
  "row_count": 0,
  "retry_count": 0,
  "error": null,
  "fetched_at_ms": 0
}
```

Before live fetching, runner must dry-run estimate:

```text
estimated_symbol_count
estimated_window_count
estimated_kline_request_count
```

If the estimate exceeds configured request budget, stop before network calls:

```text
decision = stage1_5c1_price_coverage_invalid
blocker = request_budget_exceeded
```

### 2.10 Graceful network degradation

Bulk download must not crash on one symbol. Catch `urllib.error.URLError`, timeout, HTTP 429/5xx, and malformed payloads.

After retry budget is exhausted:

```text
futures_kline_status = futures_kline_partial
coverage_reject_reason = network_error_retry_budget_exhausted|rate_limited|malformed_kline_payload
```

The runner should finish and write summary/review with partial status.


### 2.11 Coverage classifications

Per event row output:

```json
{
  "symbol_event_id": "...",
  "event_type": "futures_contract_launch",
  "symbol": "ARXUSDT",
  "futures_symbol_status": "futures_symbol_currently_verified|futures_symbol_current_exchangeinfo_not_found|historical_futures_existence_unknown",
  "futures_kline_status": "post_launch_futures_coverage_pass|futures_pre_event_coverage_pass|post_launch_futures_coverage_not_matured|future_bar_request_truncated|futures_kline_not_found|futures_kline_partial|market_scope_unknown",
  "spot_proxy_status": "spot_proxy_available_report_only|spot_symbol_not_found|not_requested",
  "replay_price_source_allowed": "futures_only|none",
  "spot_proxy_replay_allowed": false,
  "stage1_5c_rerun_candidate": true,
  "coverage_reject_reason": null
}
```

Coverage pass rules:

```text
delisting futures pass:
  futures_symbol_verified
  pre-event futures history >= 30d
  entry and all forward windows complete

futures launch futures pass:
  futures_symbol_verified
  post-launch entry and all forward windows complete
  pre-event futures history not required
```

### 2.12 Summary decision

Allowed summary decisions:

```text
stage1_5c1_price_coverage_ready_for_1_5c_rerun
stage1_5c1_price_coverage_sparse_inconclusive
stage1_5c1_price_coverage_failed
stage1_5c1_price_coverage_invalid
```

Suggested gates:

```text
ready_for_1_5c_rerun:
  futures_coverage_pass_event_count >= 30
  futures_coverage_pass_event_days >= 10
  futures_coverage_pass_symbols >= 3
  spot_proxy_available_event_count must not affect readiness
  not_matured_event_count is reported separately, not counted as failed

sparse_inconclusive:
  futures_coverage_pass_event_count > 0
  but one or more density gates fail

failed:
  futures_coverage_pass_event_count == 0
  and all symbols were validly checked

invalid:
  Stage 1.5B input missing / network disabled without cache / parser error / exchangeInfo unavailable
```

No decision may imply alpha or trading readiness.

---

## 3. Config Constants

Add to `configs/base.py`:

```python
# ─── External Signal Shadow Lab Stage 1.5C.1: Price Coverage Expansion ─────

EXTERNAL_SIGNAL_STAGE1_5C1_BINANCE_FAPI_BASE_URL = "https://fapi.binance.com"
EXTERNAL_SIGNAL_STAGE1_5C1_BINANCE_SPOT_BASE_URL = "https://api.binance.com"
EXTERNAL_SIGNAL_STAGE1_5C1_FUTURES_EXCHANGE_INFO_PATH = "/fapi/v1/exchangeInfo"
EXTERNAL_SIGNAL_STAGE1_5C1_FUTURES_KLINES_PATH = "/fapi/v1/klines"
EXTERNAL_SIGNAL_STAGE1_5C1_SPOT_EXCHANGE_INFO_PATH = "/api/v3/exchangeInfo"
EXTERNAL_SIGNAL_STAGE1_5C1_SPOT_KLINES_PATH = "/api/v3/klines"

EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_INTERVAL = "15m"
EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_INTERVAL_MS = 15 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_LIMIT = 1500
EXTERNAL_SIGNAL_STAGE1_5C1_ALLOWED_FUTURES_QUOTE_ASSETS = ("USDT", "USDC")
EXTERNAL_SIGNAL_STAGE1_5C1_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_5C1_REQUEST_SLEEP_SEC = 0.2
EXTERNAL_SIGNAL_STAGE1_5C1_RETRY_BUDGET = 2
EXTERNAL_SIGNAL_STAGE1_5C1_MAX_KLINE_REQUESTS_PER_RUN = 500
EXTERNAL_SIGNAL_STAGE1_5C1_MAX_SYMBOLS_PER_RUN = 250

EXTERNAL_SIGNAL_STAGE1_5C1_PRE_EVENT_HISTORY_DAYS = 30
EXTERNAL_SIGNAL_STAGE1_5C1_POST_EVENT_BUFFER_DAYS = 2
EXTERNAL_SIGNAL_STAGE1_5C1_MERGE_GAP_MS = 6 * 60 * 60 * 1000

EXTERNAL_SIGNAL_STAGE1_5C1_MIN_RERUN_EVENT_COUNT = 30
EXTERNAL_SIGNAL_STAGE1_5C1_MIN_RERUN_EVENT_DAYS = 10
EXTERNAL_SIGNAL_STAGE1_5C1_MIN_RERUN_SYMBOLS = 3
```

---

## 4. Implementation Tasks

### Task 1: Add Stage 1.5C.1 Config Tests

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_config.py`

**Step 1: Write failing test**

```python
from configs import base


def test_stage1_5c1_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_BINANCE_FAPI_BASE_URL == "https://fapi.binance.com"
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_BINANCE_SPOT_BASE_URL == "https://api.binance.com"
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_FUTURES_EXCHANGE_INFO_PATH == "/fapi/v1/exchangeInfo"
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_FUTURES_KLINES_PATH == "/fapi/v1/klines"
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_SPOT_EXCHANGE_INFO_PATH == "/api/v3/exchangeInfo"
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_SPOT_KLINES_PATH == "/api/v3/klines"
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_INTERVAL == "15m"
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_INTERVAL_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_LIMIT == 1500
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_PRE_EVENT_HISTORY_DAYS == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_POST_EVENT_BUFFER_DAYS == 2
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_MIN_RERUN_EVENT_COUNT == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_MIN_RERUN_EVENT_DAYS == 10
    assert base.EXTERNAL_SIGNAL_STAGE1_5C1_MIN_RERUN_SYMBOLS == 3
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_config.py -q
```

Expected: fail because constants do not exist.

**Step 3: Add constants**

Append constants from Section 3 to `configs/base.py`.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_config.py -q
```

Expected: pass.

---

### Task 2: Add Models

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c1_price_coverage_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_models.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5c1_price_coverage_models import (
    PriceCoverageDecision,
    PriceCoverageEventReport,
    PriceKlineRow,
)


def test_price_kline_row_safety_fields():
    row = PriceKlineRow(
        symbol="ABCUSDT",
        bar_start_ms=1710000000000,
        bar_end_ms=1710000900000,
        open=1.0,
        high=1.1,
        low=0.9,
        close=1.05,
        quote_volume=1000000.0,
        source="binance_um_futures_15m",
        source_quality="exchange_futures_kline_close_price_not_fill_price",
    )
    assert row.api_key_used is False
    assert row.private_endpoint_used is False
    assert row.paper_trading_allowed is False
    assert row.live_trading_allowed is False


def test_event_report_defaults_no_replay_for_spot_proxy():
    report = PriceCoverageEventReport(
        symbol_event_id="e1",
        event_type="futures_contract_launch",
        symbol="ABCUSDT",
        futures_symbol_status="futures_symbol_not_found",
        futures_kline_status="futures_symbol_not_found",
        spot_proxy_status="spot_proxy_available_report_only",
        replay_price_source_allowed="none",
        stage1_5c_rerun_candidate=False,
        coverage_reject_reason="futures_symbol_not_found",
    )
    assert report.spot_proxy_replay_allowed is False
    assert report.alpha_interpretation_allowed is False


def test_decision_enum_values():
    assert PriceCoverageDecision.READY.value == "stage1_5c1_price_coverage_ready_for_1_5c_rerun"
    assert PriceCoverageDecision.SPARSE.value == "stage1_5c1_price_coverage_sparse_inconclusive"
    assert PriceCoverageDecision.FAILED.value == "stage1_5c1_price_coverage_failed"
    assert PriceCoverageDecision.INVALID.value == "stage1_5c1_price_coverage_invalid"
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_models.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement models**

Use `@dataclass` and `Enum`. Keep safety fields default false.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_models.py -q
```

Expected: pass.

---

### Task 3: Add Stage 1.5B Event Loader and Window Builder

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c1_price_coverage_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_loader.py`

**Step 1: Write failing tests**

```python
import json

from src.research.external_signal_shadow.stage1_5c1_price_coverage_loader import (
    build_event_request_window,
    load_stage1_5b_events,
    merge_symbol_windows,
)


def test_load_stage1_5b_events_keeps_allowed_event_types(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join([
        json.dumps({"symbol_event_id": "a", "event_type": "futures_contract_launch", "symbol": "ABCUSDT", "available_at_ms": 1}),
        json.dumps({"symbol_event_id": "b", "event_type": "unknown", "symbol": "XYZUSDT", "available_at_ms": 2}),
    ]) + "\n")
    rows = load_stage1_5b_events(path)
    assert [r["symbol_event_id"] for r in rows] == ["a"]


def test_delisting_window_requires_pre_event_history():
    event = {
        "symbol_event_id": "d1",
        "event_type": "exchange_delisting_notice",
        "symbol": "ABCUSDT",
        "available_at_ms": 100 * 24 * 3600_000,
    }
    w = build_event_request_window(event, now_ms=200 * 24 * 3600_000)
    assert w["start_ms"] < event["available_at_ms"] - 30 * 24 * 3600_000 + 1
    assert w["end_ms"] > event["available_at_ms"] + 36 * 3600_000


def test_futures_launch_window_starts_at_available_at_not_30d_before():
    event = {
        "symbol_event_id": "f1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 100 * 24 * 3600_000,
    }
    w = build_event_request_window(event, now_ms=200 * 24 * 3600_000)
    assert w["start_ms"] == event["available_at_ms"]
    assert w["event_type"] == "futures_contract_launch"


def test_merge_symbol_windows_merges_overlapping_ranges():
    windows = [
        {"source_type": "futures", "symbol": "ABCUSDT", "start_ms": 0, "end_ms": 1000},
        {"source_type": "futures", "symbol": "ABCUSDT", "start_ms": 1001, "end_ms": 2000},
        {"source_type": "futures", "symbol": "XYZUSDT", "start_ms": 0, "end_ms": 1000},
    ]
    merged = merge_symbol_windows(windows, merge_gap_ms=10)
    assert len(merged) == 2
    abc = [w for w in merged if w["symbol"] == "ABCUSDT"][0]
    assert abc["start_ms"] == 0
    assert abc["end_ms"] == 2000
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_loader.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement loader/window builder**

Functions:

```python
def load_jsonl(path: str | Path) -> list[dict]: ...
def load_stage1_5b_events(path: str | Path) -> list[dict]: ...
def build_event_request_window(event: dict, now_ms: int) -> dict: ...
def merge_symbol_windows(windows: list[dict], merge_gap_ms: int) -> list[dict]: ...
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_loader.py -q
```

Expected: pass.

---

### Task 4: Add Binance Public Client

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c1_price_coverage_client.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_client.py`

**Step 1: Write failing tests**

```python
import json
from unittest.mock import patch

from src.research.external_signal_shadow.stage1_5c1_price_coverage_client import (
    build_klines_url,
    filter_exchange_symbols,
    iter_kline_request_slices,
    next_start_after_kline_batch,
    parse_kline_array,
    public_get_json,
)


def test_build_futures_klines_url_contains_readonly_params():
    url = build_klines_url(
        base_url="https://fapi.binance.com",
        path="/fapi/v1/klines",
        symbol="ABCUSDT",
        interval="15m",
        start_ms=1,
        end_ms=2,
        limit=1500,
    )
    assert "symbol=ABCUSDT" in url
    assert "interval=15m" in url
    assert "startTime=1" in url
    assert "endTime=2" in url
    assert "limit=1500" in url
    assert "apiKey" not in url


def test_filter_exchange_symbols_only_trading_usdt_perpetuals():
    payload = {"symbols": [
        {"symbol": "ABCUSDT", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDT"},
        {"symbol": "DEFUSDT", "contractType": "CURRENT_QUARTER", "status": "TRADING", "quoteAsset": "USDT"},
        {"symbol": "OLDUSDT", "contractType": "PERPETUAL", "status": "SETTLING", "quoteAsset": "USDT"},
    ]}
    assert filter_exchange_symbols(payload, market_type="futures") == {"ABCUSDT"}


def test_parse_kline_array_to_normalized_row():
    raw = [1710000000000, "1.0", "1.2", "0.9", "1.1", "10", 1710000899999, "12345.6"]
    row = parse_kline_array(raw, symbol="ABCUSDT", source="binance_um_futures_15m")
    assert row["symbol"] == "ABCUSDT"
    assert row["bar_start_ms"] == 1710000000000
    assert row["bar_end_ms"] == 1710000900000
    assert row["open"] == 1.0
    assert row["quote_volume"] == 12345.6
    assert row["api_key_used"] is False


def test_public_get_json_requires_live_flag():
    with patch("urllib.request.urlopen") as urlopen:
        try:
            public_get_json("https://example.com", live_public_readonly=False)
        except PermissionError:
            pass
        else:
            raise AssertionError("expected PermissionError")
        urlopen.assert_not_called()


def test_filter_exchange_symbols_accepts_usdc_perpetuals():
    payload = {"symbols": [
        {"symbol": "ABCUSDC", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDC"},
    ]}
    assert filter_exchange_symbols(payload, market_type="futures") == {"ABCUSDC"}


def test_30d_15m_window_splits_into_multiple_kline_requests():
    slices = list(iter_kline_request_slices(0, 30 * 24 * 3600_000, interval_ms=900_000, limit=1500))
    assert len(slices) >= 2
    assert slices[0][0] == 0
    assert slices[-1][1] >= 30 * 24 * 3600_000


def test_kline_pagination_advances_by_last_open_time_plus_interval():
    assert next_start_after_kline_batch([[0], [900_000]], interval_ms=900_000) == 1_800_000


def test_public_get_json_returns_error_record_after_retry_budget():
    with patch("urllib.request.urlopen", side_effect=TimeoutError("boom")):
        result = public_get_json("https://example.com", live_public_readonly=True, timeout_sec=0.01, retry_budget=1, sleep_sec=0)
    assert result["ok"] is False
    assert result["error"]
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_client.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement client**

Use standard library only:

```python
urllib.request.Request
urllib.request.urlopen
urllib.parse.urlencode
```

Functions:

```python
def public_get_json(url: str, live_public_readonly: bool, timeout_sec: float, retry_budget: int, sleep_sec: float) -> object: ...
def build_klines_url(...): ...
def iter_kline_request_slices(start_ms: int, end_ms: int, interval_ms: int, limit: int) -> list[tuple[int, int]]: ...
def next_start_after_kline_batch(raw_rows: list[list], interval_ms: int) -> int: ...
def filter_exchange_symbols(exchange_info: dict, market_type: str) -> set[str]: ...
def parse_kline_array(raw: list, symbol: str, source: str) -> dict: ...
def build_request_manifest_row(...): ...
```

`public_get_json` must not raise raw network exceptions during batch mode. It should return a structured error payload after retry budget is exhausted so the runner can mark partial coverage and continue.

Do not add dependencies.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_client.py -q
```

Expected: pass.

---

### Task 5: Add Downloader / Coverage Builder

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c1_price_coverage_builder.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_builder.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5c1_price_coverage_builder import (
    build_event_coverage_report,
    compute_event_coverage_status,
    dedupe_kline_rows,
    summarize_coverage_reports,
)


def _bar(symbol, t):
    return {
        "symbol": symbol,
        "bar_start_ms": t,
        "bar_end_ms": t + 900_000,
        "open": 1.0,
        "high": 1.0,
        "low": 1.0,
        "close": 1.0,
        "quote_volume": 1000.0,
        "source": "binance_um_futures_15m",
    }


def test_dedupe_kline_rows_by_symbol_and_bar_start():
    rows = [_bar("ABCUSDT", 0), _bar("ABCUSDT", 0), _bar("ABCUSDT", 900_000)]
    deduped = dedupe_kline_rows(rows)
    assert len(deduped) == 2


def test_futures_launch_passes_with_post_launch_forward_coverage_only():
    event = {
        "symbol_event_id": "f1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 0,
    }
    bars = [_bar("ABCUSDT", i * 900_000) for i in range(0, 200)]
    status = compute_event_coverage_status(event, bars, futures_symbol_verified=True)
    assert status["futures_kline_status"] == "post_launch_futures_coverage_pass"
    assert status["stage1_5c_rerun_candidate"] is True


def test_delisting_requires_pre_event_history():
    event = {
        "symbol_event_id": "d1",
        "event_type": "exchange_delisting_notice",
        "symbol": "ABCUSDT",
        "available_at_ms": 30 * 24 * 3600_000,
    }
    bars = [_bar("ABCUSDT", i * 900_000) for i in range(0, 30 * 24 * 4 + 200)]
    status = compute_event_coverage_status(event, bars, futures_symbol_verified=True)
    assert status["futures_kline_status"] == "futures_pre_event_coverage_pass"
    assert status["stage1_5c_rerun_candidate"] is True


def test_symbol_not_found_report_is_not_replay_candidate():
    event = {"symbol_event_id": "x", "event_type": "exchange_delisting_notice", "symbol": "XYZUSDT", "available_at_ms": 0}
    report = build_event_coverage_report(event, futures_bars=[], spot_bars=[], futures_symbol_verified=False, spot_symbol_verified=False)
    assert report["futures_symbol_status"] == "futures_symbol_current_exchangeinfo_not_found"
    assert report["historical_futures_existence"] == "unknown"
    assert report["stage1_5c_rerun_candidate"] is False
    assert report["spot_proxy_replay_allowed"] is False


def test_recent_event_forward_window_not_matured_not_failed():
    event = {"symbol_event_id": "f_recent", "event_type": "futures_contract_launch", "symbol": "ABCUSDT", "available_at_ms": 100_000_000}
    status = compute_event_coverage_status(event, [], futures_symbol_verified=True, current_time_ms=101_000_000)
    assert status["futures_kline_status"] in {"post_launch_futures_coverage_not_matured", "future_bar_request_truncated"}
    assert status["rerun_after_ms"] is not None


def test_futures_launch_outputs_first_futures_bar_anchor():
    event = {"symbol_event_id": "f_anchor", "event_type": "futures_contract_launch", "symbol": "ABCUSDT", "available_at_ms": 0}
    bars = [_bar("ABCUSDT", 3_600_000), _bar("ABCUSDT", 4_500_000)]
    status = compute_event_coverage_status(event, bars, futures_symbol_verified=True)
    assert status["first_futures_bar_start_ms"] == 3_600_000
    assert status["launch_price_anchor_status"] == "first_futures_bar_after_available_at"
    assert status["suggested_replay_anchor_ms"] >= 3_600_000


def test_spot_proxy_available_does_not_make_summary_ready():
    summary = summarize_coverage_reports([{
        "stage1_5c_rerun_candidate": False,
        "spot_proxy_status": "spot_proxy_available_report_only",
        "event_day": "2026-01-01",
        "symbol": "ABCUSDT",
    }])
    assert summary["spot_proxy_available_event_count"] == 1
    assert summary["decision"] != "stage1_5c1_price_coverage_ready_for_1_5c_rerun"


def test_market_scope_unknown_blocks_rerun_candidate():
    event = {"symbol_event_id": "d_unknown", "event_type": "exchange_delisting_notice", "symbol": "ABCUSDT", "available_at_ms": 0, "title": "Binance Will Delist ABC"}
    report = build_event_coverage_report(event, futures_bars=[], spot_bars=[], futures_symbol_verified=True, spot_symbol_verified=False)
    assert report["market_scope_inferred"] in {"unknown", "spot", "um_futures", "cross_market"}
    if report["market_scope_inferred"] == "unknown":
        assert report["stage1_5c_rerun_candidate"] is False
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_builder.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement builder**

Functions:

```python
def dedupe_kline_rows(rows: list[dict]) -> list[dict]: ...
def infer_market_scope(event: dict) -> dict: ...
def compute_event_coverage_status(event: dict, futures_bars: list[dict], futures_symbol_verified: bool, current_time_ms: int | None = None) -> dict: ...
def build_event_coverage_report(event: dict, futures_bars: list[dict], spot_bars: list[dict], futures_symbol_verified: bool, spot_symbol_verified: bool) -> dict: ...
def summarize_coverage_reports(reports: list[dict]) -> dict: ...
def filter_futures_coverage_pass_events(events: list[dict], reports: list[dict]) -> list[dict]: ...
```

Keep delisting and futures launch coverage rules separate. Spot proxy rows must never set `stage1_5c_rerun_candidate = true`.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_builder.py -q
```

Expected: pass.

---

### Task 6: Add Runner CLI

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_5c1_price_coverage_expansion.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5c1_price_coverage_expansion.py`

**Step 1: Write failing runner tests**

```python
import json
from unittest.mock import patch

from scripts.external_signal_shadow.run_stage1_5c1_price_coverage_expansion import main


def test_runner_requires_live_flag_for_network(tmp_path):
    events = tmp_path / "events.jsonl"
    summary = tmp_path / "stage1_5b_summary.json"
    output = tmp_path / "futures.jsonl"
    report = tmp_path / "report.jsonl"
    out_summary = tmp_path / "summary.json"

    events.write_text(json.dumps({
        "symbol_event_id": "e1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 0,
    }) + "\n")
    summary.write_text(json.dumps({
        "decision": "stage1_5b_event_table_ready",
        "replay_allowed": False,
        "stage1_5c_replay_candidate_allowed": False,
    }))

    args = [
        "run_stage1_5c1_price_coverage_expansion.py",
        "--events-jsonl", str(events),
        "--stage1-5b-summary", str(summary),
        "--output-futures-jsonl", str(output),
        "--output-event-report-jsonl", str(report),
        "--output-summary", str(out_summary),
    ]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 2


def test_runner_with_mock_exchange_info_and_klines_writes_outputs(tmp_path):
    events = tmp_path / "events.jsonl"
    summary = tmp_path / "stage1_5b_summary.json"
    output = tmp_path / "futures.jsonl"
    report = tmp_path / "report.jsonl"
    out_summary = tmp_path / "summary.json"
    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()

    events.write_text(json.dumps({
        "symbol_event_id": "e1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 0,
    }) + "\n")
    summary.write_text(json.dumps({
        "decision": "stage1_5b_event_table_ready",
        "replay_allowed": False,
        "stage1_5c_replay_candidate_allowed": False,
    }))
    (mock_dir / "futures_exchange_info.json").write_text(json.dumps({
        "symbols": [{"symbol": "ABCUSDT", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDT"}]
    }))
    (mock_dir / "futures_ABCUSDT_0_136800000.json").write_text(json.dumps([
        [0, "1", "1", "1", "1", "1", 899999, "1000"],
        [900000, "1", "1", "1", "1", "1", 1799999, "1000"],
        [3600000, "1", "1", "1", "1", "1", 4499999, "1000"],
        [90000000, "1", "1", "1", "1", "1", 90899999, "1000"],
    ]))

    args = [
        "run_stage1_5c1_price_coverage_expansion.py",
        "--events-jsonl", str(events),
        "--stage1-5b-summary", str(summary),
        "--output-futures-jsonl", str(output),
        "--output-event-report-jsonl", str(report),
        "--output-summary", str(out_summary),
        "--mock-response-dir", str(mock_dir),
    ]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 0
    assert output.exists()
    assert report.exists()
    s = json.loads(out_summary.read_text())
    assert s["api_key_used"] is False
    assert s["private_endpoint_used"] is False
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5c1_price_coverage_expansion.py -q
```

Expected: fail because script does not exist.

**Step 3: Implement runner**

CLI:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5c1_price_coverage_expansion.py \
  --events-jsonl data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl \
  --stage1-5b-summary data/external_signal_shadow/stage1_5b/normalization_summary.json \
  --output-futures-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/binance_um_futures_15m_event_symbols.jsonl \
  --output-spot-proxy-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/binance_spot_15m_event_symbols_proxy.jsonl \
  --output-event-report-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/event_price_coverage_report.jsonl \
  --output-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --output-request-manifest-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/request_manifest.jsonl \
  --output-futures-coverage-pass-events-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/external_catalyst_events_futures_coverage_pass.jsonl \
  --live-public-readonly
```

Runner requirements:

```text
1. Assert Stage 1.5B ready.
2. Load Stage 1.5B events.
3. Fetch or load cached futures exchangeInfo and write `futures_exchange_info_raw.json`.
4. Validate symbols using current-state exchangeInfo only; do not infer historical non-existence.
5. Infer delisting market scope before requiring futures coverage.
6. Build, merge, and paginate futures request windows.
7. Dry-run request budget; stop with `request_budget_exceeded` before network if over budget.
8. Fetch futures klines where futures symbol exists, recording each request in `request_manifest.jsonl`.
9. Gracefully degrade failed symbols to `futures_kline_partial`; do not crash whole batch.
10. Optionally fetch spot klines when --include-spot-proxy is provided; write report-only spot archive.
11. Write normalized futures rows and optional spot proxy rows.
12. Write event coverage report JSONL.
13. Write `external_catalyst_events_futures_coverage_pass.jsonl` containing only `stage1_5c_rerun_candidate = true` and `replay_price_source_allowed = futures_only`.
14. Write summary JSON.
```

`--mock-response-dir` should allow tests to avoid network.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5c1_price_coverage_expansion.py -q
```

Expected: pass.

---

### Task 7: Add Review Generator

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_5c1_price_coverage_expansion.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_5c1_price_coverage_expansion.py`

**Step 1: Write failing review test**

```python
import json
from unittest.mock import patch

from scripts.external_signal_shadow.review_stage1_5c1_price_coverage_expansion import main


def test_review_states_coverage_only_and_no_alpha(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_sparse_inconclusive",
        "stage1_5b_symbol_events": 194,
        "futures_coverage_pass_event_count": 12,
        "spot_proxy_available_event_count": 40,
        "blockers": ["futures_coverage_density_insufficient"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    args = [
        "review_stage1_5c1_price_coverage_expansion.py",
        "--summary", str(summary),
        "--output-review", str(review),
    ]
    with patch("sys.argv", args):
        main()
    content = review.read_text()
    assert "Stage 1.5C.1" in content
    assert "coverage-only" in content
    assert "futures_coverage_density_insufficient" in content
    assert "paper_trading_allowed" in content
    assert "live_trading_allowed" in content
    assert "alpha_interpretation_allowed" in content
    for placeholder in ["TODO", "TBD", "placeholder", "FIXME"]:
        assert placeholder not in content
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5c1_price_coverage_expansion.py -q
```

Expected: fail because script does not exist.

**Step 3: Implement review generator**

Review sections:

```text
1. Decision
2. Stage 1.5C blocker being addressed
3. Futures coverage funnel
4. Spot proxy report-only funnel
5. Event type breakdown
6. Symbol validation failures
7. Safety boundaries
8. Allowed next action
```

Must explicitly state:

```text
Stage 1.5C.1 is coverage-only.
Spot proxy is report-only and not futures execution price.
No alpha / paper / live / execution claim is allowed.
Ready decision only permits rerunning Stage 1.5C with expanded futures archive.
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5c1_price_coverage_expansion.py -q
```

Expected: pass.

---

### Task 8: Real Public Readonly Smoke

**Step 1: Verify output data paths are gitignored**

```bash
git check-ignore -v data/external_signal_shadow/stage1_5c1/price_coverage/binance_um_futures_15m_event_symbols.jsonl
git check-ignore -v data/external_signal_shadow/stage1_5c1/price_coverage/binance_spot_15m_event_symbols_proxy.jsonl
git check-ignore -v data/external_signal_shadow/stage1_5c1/price_coverage/event_price_coverage_report.jsonl
git check-ignore -v data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json
git check-ignore -v data/external_signal_shadow/stage1_5c1/price_coverage/request_manifest.jsonl
git check-ignore -v data/external_signal_shadow/stage1_5c1/price_coverage/futures_exchange_info_raw.json
git check-ignore -v data/external_signal_shadow/stage1_5c1/price_coverage/spot_exchange_info_raw.json
git check-ignore -v data/external_signal_shadow/stage1_5c1/price_coverage/external_catalyst_events_futures_coverage_pass.jsonl
```

Expected: all ignored. If any path is not ignored, update `.gitignore` before running live smoke.

**Step 2: Run futures-only coverage expansion**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5c1_price_coverage_expansion.py \
  --events-jsonl data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl \
  --stage1-5b-summary data/external_signal_shadow/stage1_5b/normalization_summary.json \
  --output-futures-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/binance_um_futures_15m_event_symbols.jsonl \
  --output-event-report-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/event_price_coverage_report.jsonl \
  --output-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --output-request-manifest-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/request_manifest.jsonl \
  --output-futures-coverage-pass-events-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/external_catalyst_events_futures_coverage_pass.jsonl \
  --live-public-readonly
```

Expected:

```text
api_key_used = false
private_endpoint_used = false
stage1_5b_symbol_events = 194
futures_symbol_verified_count is present
futures_coverage_pass_event_count is present
```

**Step 3: Optionally run with spot proxy report-only**

Only if futures coverage is sparse and you want context:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5c1_price_coverage_expansion.py \
  --events-jsonl data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl \
  --stage1-5b-summary data/external_signal_shadow/stage1_5b/normalization_summary.json \
  --output-futures-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/binance_um_futures_15m_event_symbols.jsonl \
  --output-spot-proxy-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/binance_spot_15m_event_symbols_proxy.jsonl \
  --output-event-report-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/event_price_coverage_report.jsonl \
  --output-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --include-spot-proxy \
  --live-public-readonly
```

Spot proxy rows must be marked report-only.

**Step 4: Generate review**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_5c1_price_coverage_expansion.py \
  --summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --output-review docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-review_CN.md
```

**Step 5: Handoff gate before rerunning Stage 1.5C**

Only if summary decision is `stage1_5c1_price_coverage_ready_for_1_5c_rerun`, patch or verify Stage 1.5C coverage gate before rerun:

```text
futures_contract_launch:
  accept post_launch_futures_coverage_pass
  use first_futures_bar_start_ms / suggested_replay_anchor_ms
  do not require 30d pre-event futures history

exchange_delisting_notice:
  still require 30d pre-event futures history when market_scope_inferred = um_futures
  do not treat spot delisting futures coverage failure as event-source failure
```

Required Stage 1.5C handoff tests:

```text
test_stage1_5c_accepts_futures_launch_post_launch_coverage_without_30d_pre_history
test_stage1_5c_still_requires_delisting_pre_event_history
test_stage1_5c_uses_coverage_pass_event_table_for_rerun
test_spot_proxy_archive_is_not_accepted_as_replay_price_source
```

Then rerun Stage 1.5C using only the coverage-pass event table:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5c_external_catalyst_replay.py \
  --events-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/external_catalyst_events_futures_coverage_pass.jsonl \
  --stage1-5b-summary data/external_signal_shadow/stage1_5b/normalization_summary.json \
  --price-jsonl data/external_signal_shadow/stage1_5c1/price_coverage/binance_um_futures_15m_event_symbols.jsonl \
  --output-candidates-jsonl data/external_signal_shadow/stage1_5c/external_catalyst_replay_candidates.jsonl \
  --output-results-jsonl data/external_signal_shadow/stage1_5c/external_catalyst_replay_results.jsonl \
  --output-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json
```

Then regenerate Stage 1.5C review using the existing review script.

---

## 5. Verification Commands

Run Stage 1.5C.1 tests:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_config.py \
  tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_models.py \
  tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_loader.py \
  tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_client.py \
  tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_builder.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5c1_price_coverage_expansion.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5c1_price_coverage_expansion.py \
  -q
```

Run handoff tests:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5b_event_table_summary.py \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_loader.py \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_summary.py \
  -q
```

Run ruff:

```bash
PYTHONPATH=src:. uv run ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5c1_price_coverage_*.py \
  scripts/external_signal_shadow/*stage1_5c1* \
  tests/research/external_signal_shadow/test_stage1_5c1_price_coverage_*.py \
  tests/scripts/external_signal_shadow/*stage1_5c1*
```

---

## 6. Non-Goals / Guardrails

Do not add:

```text
forward return calculation
random baseline
paper trading
live trading
execution engine wiring
TradeIntent
position sizing
orderbook/depth claim
spot proxy replay claim
alpha confirmed claim
```

Do not classify futures launch as failed because it lacks 30d pre-launch futures history.

Do not write spot proxy rows into the futures archive.

Do not let spot proxy availability affect `stage1_5c1_price_coverage_ready_for_1_5c_rerun`.

Do not infer historical non-existence from current `exchangeInfo` missing.

Do not treat not-yet-matured recent events as coverage failure.

Do not use private endpoints, API keys, account endpoints, order endpoints, or wallet endpoints.

---

## 7. Git / Artifact Hygiene

Data artifacts should stay uncommitted by default:

```text
data/external_signal_shadow/stage1_5c1/price_coverage/*.jsonl
data/external_signal_shadow/stage1_5c1/price_coverage/*.json
```

Review docs may be committed:

```text
docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-review_CN.md
```

Do not commit automatically. End with:

```bash
git status --short
```

and list changed files for user review.

---

## 8. Expected Final Status

After implementation, one of these should be true:

```text
stage1_5c1_price_coverage_ready_for_1_5c_rerun
  -> rerun Stage 1.5C using expanded futures archive and coverage-pass event table only

stage1_5c1_price_coverage_sparse_inconclusive
  -> consider more sources / older events / spot proxy report-only analysis

stage1_5c1_price_coverage_failed
  -> Binance-only external catalyst event table has insufficient futures price coverage

stage1_5c1_price_coverage_invalid
  -> fix source audit input, exchangeInfo, cache, or network/config issue
```
