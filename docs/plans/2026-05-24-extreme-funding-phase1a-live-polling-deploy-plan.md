# Extreme Funding Phase 1A.5 Live Polling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect the completed Phase 1A watchlist scanner to Binance public USD-M endpoints, keep the scanner observation-only, persist low-frequency evidence for 24h review, and prepare a server run recipe without touching execution.

**Architecture:** `ExtremeFundingWatchlistScanner` remains the pure classification core. `scripts/run_extreme_funding_watchlist.py` becomes a public-data daemon wrapper: fetch public premium/mark data every 10s, fetch OI only every 60s through a cache, assemble whitelisted snapshots, run one polling pass, write JSONL watch/heartbeat evidence, and log typed API errors. No `SignalCandidate`, no `TradeIntent`, no private API config, no live trading.

**Tech Stack:** Python 3.11, pytest, standard-library `urllib.request`, `configs/base.py` as SSOT, `loguru` logging, Binance USD-M public REST endpoints only.

---

## Scope

This plan is **Phase 1A.5 only**.

It includes:

- Public Binance USD-M `premiumIndex` polling.
- Public Binance USD-M `openInterest` polling with 60s cache and 180s max age.
- Timestamp-windowed OI 1h change calculation.
- Scanner warm-up guard to avoid 1-minute false alerts.
- Explicit premium/source lineage to prevent treating mark-index premium as settled funding.
- Low-frequency JSONL evidence for watch events and heartbeat summaries.
- Bounded local `--once` dry run and server operation document.

It excludes:

- Phase 1B basis absorption.
- Phase 1B `SignalCandidate` creation.
- Phase 1C shadow position simulation.
- Any private endpoints, balances, API keys, or order placement.
- Any change to `risk.limits.RiskLimits.live_trading_enabled`.
- Any actual server installation. This plan only creates the run command and ops document.

---

## Review Feedback Disposition

- Adopted: OI cache + age prevents 10s OI over-polling and alert flicker.
- Adopted: `find_premium_item()` must support both list payload and single-symbol dict payload.
- Adopted: OI change must be calculated before appending current OI.
- Adopted: 5-minute persistence warm-up prevents early false watch events.
- Adopted: mark-index premium is explicitly labeled as `premium_source="mark_price_minus_index_price"`; `lastFundingRate` is not treated as settled or future funding.
- Adopted: `--once` avoids 30s local dry-run delay.
- Adopted: API exceptions get typed log categories.
- Adopted: `--data-root` now writes JSONL evidence instead of being a no-op.

---

## File Structure

- Modify: `configs/base.py`
- Modify: `src/strategies/extreme_funding/scanner.py`
- Modify: `scripts/run_extreme_funding_watchlist.py`
- Modify: `tests/test_extreme_funding_config.py`
- Modify: `tests/strategies/test_extreme_funding_scanner.py`
- Modify: `tests/scripts/test_run_extreme_funding_watchlist.py`
- Create: `docs/ops/extreme_funding_watchlist_server.md`

---

### Task 1: Baseline And Scope Guard

**Files:**
- Read: `AGENTS.md`
- Read: `docs/roadmap.md`
- Read: `configs/base.py`
- Read: `src/strategies/extreme_funding/scanner.py`
- Read: `scripts/run_extreme_funding_watchlist.py`

- [ ] **Step 1: Confirm current worktree**

Run:

```bash
git status --short
```

Expected: no uncommitted implementation changes from this plan. User-owned docs/research changes must not be touched.

- [ ] **Step 2: Run current tests**

Run:

```bash
make test
```

Expected: PASS.

- [ ] **Step 3: Run smoke checks**

Run:

```bash
make smoke
```

Expected: PASS with `configs OK` and `risk gate OK`.

- [ ] **Step 4: Confirm no execution/private imports in watchlist script**

Run:

```bash
rg -n "execution|TradeIntent|RiskLimits|apiKey|secret|password" scripts/run_extreme_funding_watchlist.py
```

Expected: no output.

- [ ] **Step 5: Commit**

No commit for this task unless baseline files changed.

---

### Task 2: Add Phase 1A.5 Config Constants

**Files:**
- Modify: `configs/base.py`
- Modify: `tests/test_extreme_funding_config.py`

- [ ] **Step 1: Write the failing config test**

Append to `tests/test_extreme_funding_config.py`:

```python
def test_extreme_funding_phase1a_live_polling_config_constants_exist():
    assert base.EXTREME_FUNDING_BINANCE_FAPI_BASE_URL == "https://fapi.binance.com"
    assert base.EXTREME_FUNDING_HTTP_TIMEOUT_SEC == 10.0
    assert base.EXTREME_FUNDING_LOCAL_DRY_RUN_MAX_ITERATIONS == 3
    assert base.EXTREME_FUNDING_OI_CHANGE_LOOKBACK_SEC == 3600
    assert base.EXTREME_FUNDING_LOOP_ERROR_BACKOFF_SEC == 5.0
    assert base.EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_COVERAGE_SEC == 300
    assert base.EXTREME_FUNDING_EVENT_LOG_JSONL == "extreme_funding_watch_events.jsonl"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py::test_extreme_funding_phase1a_live_polling_config_constants_exist -v
```

Expected: FAIL with missing `EXTREME_FUNDING_BINANCE_FAPI_BASE_URL`.

- [ ] **Step 3: Add constants to `configs/base.py`**

Append below existing `EXTREME_FUNDING_MAX_OI_DATA_AGE_SEC`:

```python
EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_COVERAGE_SEC = 300
# Minimum timestamp coverage before emitting a Phase 1A watch event.
# 300s = 5 minutes. Prevents startup false positives from 1-2 samples.

EXTREME_FUNDING_BINANCE_FAPI_BASE_URL = "https://fapi.binance.com"
# Binance USD-M futures public REST base URL used by Phase 1A observation daemon.

EXTREME_FUNDING_HTTP_TIMEOUT_SEC = 10.0
# Timeout for each public REST request. Keep conservative to avoid hanging the daemon.

EXTREME_FUNDING_LOCAL_DRY_RUN_MAX_ITERATIONS = 3
# Default bounded local dry-run loop count when --once is not used.

EXTREME_FUNDING_OI_CHANGE_LOOKBACK_SEC = 3600
# Lookback window for open-interest change confirmation.

EXTREME_FUNDING_LOOP_ERROR_BACKOFF_SEC = 5.0
# Sleep duration after a recoverable polling-loop error.

EXTREME_FUNDING_EVENT_LOG_JSONL = "extreme_funding_watch_events.jsonl"
# Low-frequency JSONL evidence file under --data-root. Do not write raw 10s market data.
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py::test_extreme_funding_phase1a_live_polling_config_constants_exist -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add configs/base.py tests/test_extreme_funding_config.py
git commit -m "feat: add extreme funding live polling config"
```

---

### Task 3: Add Persistence Warm-Up Gate

**Files:**
- Modify: `src/strategies/extreme_funding/scanner.py`
- Modify: `tests/strategies/test_extreme_funding_scanner.py`

- [ ] **Step 1: Write failing warm-up tests**

Append to `tests/strategies/test_extreme_funding_scanner.py`:

```python
def test_classify_rejects_until_micro_persistence_warmup_complete():
    scanner = ExtremeFundingWatchlistScanner()
    for second in (0, 60, 120, 180, 240):
        result = scanner.classify(
            _snapshot(
                timestamp_ms=second * 1000,
                premium_annualized_estimate_pct=60.0,
                oi_change_1h_pct=1.0,
            )
        )

    assert result.event is None
    assert result.reject_reason == "micro_persistence_warmup"


def test_classify_emits_after_micro_persistence_warmup_complete():
    scanner = ExtremeFundingWatchlistScanner()
    for second in (0, 60, 120, 180, 240):
        scanner.classify(
            _snapshot(
                timestamp_ms=second * 1000,
                premium_annualized_estimate_pct=60.0,
                oi_change_1h_pct=1.0,
            )
        )

    result = scanner.classify(
        _snapshot(
            timestamp_ms=300 * 1000,
            premium_annualized_estimate_pct=60.0,
            oi_change_1h_pct=1.0,
        )
    )

    assert result.event is not None
    assert result.event.level == "watch_level_2"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py::test_classify_rejects_until_micro_persistence_warmup_complete tests/strategies/test_extreme_funding_scanner.py::test_classify_emits_after_micro_persistence_warmup_complete -v
```

Expected: FAIL because the current scanner emits after two high samples.

- [ ] **Step 3: Implement timestamp coverage helper**

Add import in `src/strategies/extreme_funding/scanner.py`:

```python
from configs.base import EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_COVERAGE_SEC
```

Add method to `ExtremeFundingWatchlistScanner`:

```python
    def get_window_coverage_ms(self, symbol: str, *, now_ms: int) -> int:
        self._prune_history(symbol, now_ms=now_ms)
        if len(self._history[symbol]) < 2:
            return 0
        return self._history[symbol][-1][0] - self._history[symbol][0][0]
```

Then in `classify()`, after `window_values` is built and before persistence threshold checks:

```python
        coverage_ms = self.get_window_coverage_ms(symbol, now_ms=timestamp_ms)
        if coverage_ms < EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_COVERAGE_SEC * 1000:
            return ExtremeFundingClassification(None, "micro_persistence_warmup")
```

Keep `micro_persistence_below_threshold` for windows that are warm but fail the ratio.

- [ ] **Step 4: Update old tests that expected 2-sample alert**

If any existing scanner test expected a watch event before 5 minutes, change its fixture timestamps to cover at least `0..300s`.

- [ ] **Step 5: Run scanner tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/strategies/extreme_funding/scanner.py tests/strategies/test_extreme_funding_scanner.py
git commit -m "feat: add extreme funding persistence warmup"
```

---

### Task 4: Add Binance Public Symbol, URL, And JSON Fetch Helpers

**Files:**
- Modify: `scripts/run_extreme_funding_watchlist.py`
- Modify: `tests/scripts/test_run_extreme_funding_watchlist.py`

- [ ] **Step 1: Write failing helper tests**

Append to `tests/scripts/test_run_extreme_funding_watchlist.py`:

```python
import json
from io import BytesIO

from scripts.run_extreme_funding_watchlist import (
    binance_symbol_from_pair,
    build_binance_fapi_url,
    fetch_json_url,
)


class _FakeResponse:
    def __init__(self, payload: object):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return BytesIO(self._payload)

    def __exit__(self, exc_type, exc, tb):
        return False


def test_binance_symbol_from_pair_removes_separator():
    assert binance_symbol_from_pair("DOGE/USDT") == "DOGEUSDT"
    assert binance_symbol_from_pair("BTC/USDT") == "BTCUSDT"


def test_build_binance_fapi_url_encodes_query_params():
    url = build_binance_fapi_url(
        base_url="https://fapi.binance.com",
        path="/fapi/v1/openInterest",
        params={"symbol": "DOGEUSDT"},
    )

    assert url == "https://fapi.binance.com/fapi/v1/openInterest?symbol=DOGEUSDT"


def test_fetch_json_url_uses_injected_opener():
    calls = []

    def fake_opener(request, *, timeout):
        calls.append((request.full_url, timeout))
        return _FakeResponse({"ok": True})

    result = fetch_json_url("https://example.test/path", timeout_sec=2.5, opener=fake_opener)

    assert result == {"ok": True}
    assert calls == [("https://example.test/path", 2.5)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py::test_binance_symbol_from_pair_removes_separator tests/scripts/test_run_extreme_funding_watchlist.py::test_build_binance_fapi_url_encodes_query_params tests/scripts/test_run_extreme_funding_watchlist.py::test_fetch_json_url_uses_injected_opener -v
```

Expected: FAIL with missing helper imports.

- [ ] **Step 3: Implement helpers**

Add to `scripts/run_extreme_funding_watchlist.py`:

```python
import json
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UrlOpen = Callable[..., Any]


def binance_symbol_from_pair(pair: str) -> str:
    return pair.replace("/", "")


def build_binance_fapi_url(*, base_url: str, path: str, params: dict[str, str] | None = None) -> str:
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    if not params:
        return f"{normalized_base}{normalized_path}"
    return f"{normalized_base}{normalized_path}?{urlencode(params)}"


def fetch_json_url(url: str, *, timeout_sec: float, opener: UrlOpen = urlopen) -> Any:
    request = Request(url, headers={"User-Agent": "crypto-alpha-lab/phase1a-watchlist"})
    with opener(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run the same pytest command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_extreme_funding_watchlist.py tests/scripts/test_run_extreme_funding_watchlist.py
git commit -m "feat: add binance public fetch helpers"
```

---

### Task 5: Add Binance Payload Adapters With Source Lineage

**Files:**
- Modify: `scripts/run_extreme_funding_watchlist.py`
- Modify: `tests/scripts/test_run_extreme_funding_watchlist.py`

- [ ] **Step 1: Write failing adapter tests**

Append to `tests/scripts/test_run_extreme_funding_watchlist.py`:

```python
from scripts.run_extreme_funding_watchlist import (
    find_premium_item,
    parse_open_interest,
    build_raw_snapshot_from_public_data,
)


def test_find_premium_item_returns_matching_symbol_from_list_payload():
    items = [
        {"symbol": "BTCUSDT", "markPrice": "100.0"},
        {"symbol": "DOGEUSDT", "markPrice": "0.25"},
    ]

    assert find_premium_item(items, "DOGEUSDT") == {"symbol": "DOGEUSDT", "markPrice": "0.25"}


def test_find_premium_item_accepts_single_symbol_dict_payload():
    payload = {"symbol": "DOGEUSDT", "markPrice": "0.25"}
    assert find_premium_item(payload, "DOGEUSDT") == payload


def test_find_premium_item_rejects_wrong_single_symbol_dict_payload():
    payload = {"symbol": "BTCUSDT", "markPrice": "100000"}
    assert find_premium_item(payload, "DOGEUSDT") is None


def test_parse_open_interest_returns_float():
    assert parse_open_interest({"openInterest": "12345.67"}) == 12345.67


def test_build_raw_snapshot_from_public_data_labels_premium_and_funding_sources():
    premium_item = {
        "symbol": "DOGEUSDT",
        "markPrice": "0.2500",
        "indexPrice": "0.2490",
        "lastFundingRate": "0.0008",
        "nextFundingTime": "123456789",
    }

    raw = build_raw_snapshot_from_public_data(
        pair="DOGE/USDT",
        exchange="binance",
        timestamp_ms=1000,
        premium_item=premium_item,
        open_interest=12345.0,
        oi_change_1h_pct=2.5,
        mark_data_age_sec=1.0,
        oi_data_age_sec=2.0,
    )

    expected_premium = (0.25 - 0.249) / 0.249
    assert raw["premium_index"] == expected_premium
    assert raw["raw_mark_index_premium"] == expected_premium
    assert raw["premium_source"] == "mark_price_minus_index_price"
    assert raw["last_funding_rate"] == 0.0008
    assert raw["estimated_funding_rate"] == 0.0008
    assert raw["funding_rate_source"] == "binance_lastFundingRate"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py::test_find_premium_item_returns_matching_symbol_from_list_payload tests/scripts/test_run_extreme_funding_watchlist.py::test_find_premium_item_accepts_single_symbol_dict_payload tests/scripts/test_run_extreme_funding_watchlist.py::test_find_premium_item_rejects_wrong_single_symbol_dict_payload tests/scripts/test_run_extreme_funding_watchlist.py::test_parse_open_interest_returns_float tests/scripts/test_run_extreme_funding_watchlist.py::test_build_raw_snapshot_from_public_data_labels_premium_and_funding_sources -v
```

Expected: FAIL with missing adapter functions.

- [ ] **Step 3: Implement adapters**

Add to `scripts/run_extreme_funding_watchlist.py`:

```python
def find_premium_item(payload: list[dict] | dict, binance_symbol: str) -> dict | None:
    if isinstance(payload, dict):
        return payload if payload.get("symbol") == binance_symbol else None
    for item in payload:
        if item.get("symbol") == binance_symbol:
            return item
    return None


def parse_open_interest(payload: dict) -> float:
    return float(payload["openInterest"])


def build_raw_snapshot_from_public_data(
    *,
    pair: str,
    exchange: str,
    timestamp_ms: int,
    premium_item: dict,
    open_interest: float | None,
    oi_change_1h_pct: float | None,
    mark_data_age_sec: float,
    oi_data_age_sec: float,
) -> dict:
    mark_price = float(premium_item["markPrice"])
    index_price = float(premium_item["indexPrice"])
    raw_mark_index_premium = (mark_price - index_price) / index_price if index_price > 0 else 0.0
    last_funding_rate = float(premium_item.get("lastFundingRate", 0.0))
    return {
        "symbol": pair,
        "exchange": exchange,
        "timestamp_ms": timestamp_ms,
        "mark_price": mark_price,
        "index_price": index_price,
        "premium_index": raw_mark_index_premium,
        "raw_mark_index_premium": raw_mark_index_premium,
        "premium_source": "mark_price_minus_index_price",
        "last_funding_rate": last_funding_rate,
        "estimated_funding_rate": last_funding_rate,
        "funding_rate_source": "binance_lastFundingRate",
        "next_funding_time_ms": int(premium_item.get("nextFundingTime", 0)),
        "open_interest": open_interest,
        "oi_change_1h_pct": oi_change_1h_pct,
        "volume_24h_usdt": None,
        "mark_data_age_sec": mark_data_age_sec,
        "oi_data_age_sec": oi_data_age_sec,
    }
```

- [ ] **Step 4: Extend public snapshot whitelist**

Add these keys to `PUBLIC_SNAPSHOT_FIELDS` in `scripts/run_extreme_funding_watchlist.py`:

```python
"raw_mark_index_premium",
"premium_source",
"last_funding_rate",
"funding_rate_source",
```

- [ ] **Step 5: Run tests to verify they pass**

Run the same pytest command from Step 2.

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_extreme_funding_watchlist.py tests/scripts/test_run_extreme_funding_watchlist.py
git commit -m "feat: add binance public payload adapters"
```

---

### Task 6: Add Open Interest Window And Cache

**Files:**
- Modify: `scripts/run_extreme_funding_watchlist.py`
- Modify: `tests/scripts/test_run_extreme_funding_watchlist.py`

- [ ] **Step 1: Write failing OI window/cache tests**

Append to `tests/scripts/test_run_extreme_funding_watchlist.py`:

```python
from scripts.run_extreme_funding_watchlist import (
    OpenInterestWindow,
    should_refresh_oi,
    oi_data_age_sec,
)


def test_open_interest_window_returns_none_until_lookback_exists():
    window = OpenInterestWindow(lookback_sec=3600)
    window.append("DOGE/USDT", timestamp_ms=0, open_interest=100.0)

    assert window.change_pct("DOGE/USDT", now_ms=10 * 60_000, current_open_interest=110.0) is None


def test_oi_change_uses_previous_lookback_value_before_appending_current():
    window = OpenInterestWindow(lookback_sec=3600)
    window.append("DOGE/USDT", timestamp_ms=0, open_interest=100.0)

    change = window.change_pct(
        "DOGE/USDT",
        now_ms=3600 * 1000,
        current_open_interest=110.0,
    )

    assert change == 10.0


def test_should_refresh_oi_respects_poll_interval():
    assert should_refresh_oi(last_fetch_ts=None, now_ts=100.0, interval_sec=60) is True
    assert should_refresh_oi(last_fetch_ts=50.0, now_ts=100.0, interval_sec=60) is False
    assert should_refresh_oi(last_fetch_ts=40.0, now_ts=100.0, interval_sec=60) is True


def test_oi_data_age_sec_uses_last_fetch_timestamp():
    assert oi_data_age_sec(last_fetch_ts=None, now_ts=100.0) == 999999.0
    assert oi_data_age_sec(last_fetch_ts=40.0, now_ts=100.0) == 60.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py::test_open_interest_window_returns_none_until_lookback_exists tests/scripts/test_run_extreme_funding_watchlist.py::test_oi_change_uses_previous_lookback_value_before_appending_current tests/scripts/test_run_extreme_funding_watchlist.py::test_should_refresh_oi_respects_poll_interval tests/scripts/test_run_extreme_funding_watchlist.py::test_oi_data_age_sec_uses_last_fetch_timestamp -v
```

Expected: FAIL with missing `OpenInterestWindow` and OI cache helpers.

- [ ] **Step 3: Implement OI window and cache helpers**

Add to `scripts/run_extreme_funding_watchlist.py`:

```python
from collections import defaultdict, deque


def should_refresh_oi(*, last_fetch_ts: float | None, now_ts: float, interval_sec: int) -> bool:
    return last_fetch_ts is None or now_ts - last_fetch_ts >= interval_sec


def oi_data_age_sec(*, last_fetch_ts: float | None, now_ts: float) -> float:
    if last_fetch_ts is None:
        return 999999.0
    return now_ts - last_fetch_ts


class OpenInterestWindow:
    def __init__(self, *, lookback_sec: int) -> None:
        self._lookback_ms = lookback_sec * 1000
        self._history: dict[str, deque[tuple[int, float]]] = defaultdict(deque)

    def append(self, symbol: str, *, timestamp_ms: int, open_interest: float) -> None:
        self._history[symbol].append((timestamp_ms, open_interest))
        self._prune(symbol, now_ms=timestamp_ms)

    def change_pct(self, symbol: str, *, now_ms: int, current_open_interest: float) -> float | None:
        self._prune(symbol, now_ms=now_ms)
        if not self._history[symbol]:
            return None
        oldest_ts, oldest_value = self._history[symbol][0]
        if now_ms - oldest_ts < self._lookback_ms or oldest_value <= 0:
            return None
        return ((current_open_interest - oldest_value) / oldest_value) * 100

    def _prune(self, symbol: str, *, now_ms: int) -> None:
        cutoff_ms = now_ms - self._lookback_ms
        while len(self._history[symbol]) > 1 and self._history[symbol][1][0] <= cutoff_ms:
            self._history[symbol].popleft()
```

- [ ] **Step 4: Run tests to verify they pass**

Run the same pytest command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_extreme_funding_watchlist.py tests/scripts/test_run_extreme_funding_watchlist.py
git commit -m "feat: add open interest window and cache helpers"
```

---

### Task 7: Add JSONL Evidence Writer

**Files:**
- Modify: `scripts/run_extreme_funding_watchlist.py`
- Modify: `tests/scripts/test_run_extreme_funding_watchlist.py`

- [ ] **Step 1: Write failing JSONL test**

Append to `tests/scripts/test_run_extreme_funding_watchlist.py`:

```python
from scripts.run_extreme_funding_watchlist import append_jsonl


def test_append_jsonl_writes_one_sorted_record(tmp_path):
    path = tmp_path / "events.jsonl"

    append_jsonl(path, {"type": "heartbeat", "events": 0})

    assert path.read_text(encoding="utf-8").strip() == '{"events": 0, "type": "heartbeat"}'
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py::test_append_jsonl_writes_one_sorted_record -v
```

Expected: FAIL with missing `append_jsonl`.

- [ ] **Step 3: Implement `append_jsonl()`**

Add to `scripts/run_extreme_funding_watchlist.py`:

```python
from pathlib import Path


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py::test_append_jsonl_writes_one_sorted_record -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_extreme_funding_watchlist.py tests/scripts/test_run_extreme_funding_watchlist.py
git commit -m "feat: add extreme funding jsonl evidence writer"
```

---

### Task 8: Add One Polling Pass With Warm-Up And Correct OI Semantics

**Files:**
- Modify: `scripts/run_extreme_funding_watchlist.py`
- Modify: `tests/scripts/test_run_extreme_funding_watchlist.py`

- [ ] **Step 1: Write failing single-pass tests**

Append to `tests/scripts/test_run_extreme_funding_watchlist.py`:

```python
from strategies.extreme_funding.scanner import ExtremeFundingWatchlistScanner
from scripts.run_extreme_funding_watchlist import run_watchlist_poll_once


def _premium_payload():
    return [
        {
            "symbol": "DOGEUSDT",
            "markPrice": "0.2600",
            "indexPrice": "0.2500",
            "lastFundingRate": "0.0008",
            "nextFundingTime": "123456789",
        }
    ]


def test_run_watchlist_poll_once_rejects_until_persistence_warmup_complete():
    scanner = ExtremeFundingWatchlistScanner()
    oi_window = OpenInterestWindow(lookback_sec=3600)
    oi_payloads = {"DOGEUSDT": {"openInterest": "1000"}}

    result = None
    for second in (0, 60, 120, 180, 240):
        result = run_watchlist_poll_once(
            pairs=("DOGE/USDT",),
            scanner=scanner,
            oi_window=oi_window,
            timestamp_ms=second * 1000,
            premium_payload=_premium_payload(),
            oi_payloads=oi_payloads,
            oi_data_age_sec=1.0,
        )

    assert result["events"] == []
    assert result["reject_reasons"] == ["micro_persistence_warmup"]


def test_run_watchlist_poll_once_emits_after_warmup_and_persistence():
    scanner = ExtremeFundingWatchlistScanner()
    oi_window = OpenInterestWindow(lookback_sec=3600)
    oi_payloads = {"DOGEUSDT": {"openInterest": "1000"}}

    for second in (0, 60, 120, 180, 240):
        run_watchlist_poll_once(
            pairs=("DOGE/USDT",),
            scanner=scanner,
            oi_window=oi_window,
            timestamp_ms=second * 1000,
            premium_payload=_premium_payload(),
            oi_payloads=oi_payloads,
            oi_data_age_sec=1.0,
        )

    result = run_watchlist_poll_once(
        pairs=("DOGE/USDT",),
        scanner=scanner,
        oi_window=oi_window,
        timestamp_ms=300 * 1000,
        premium_payload=_premium_payload(),
        oi_payloads=oi_payloads,
        oi_data_age_sec=1.0,
    )

    assert len(result["events"]) == 1
    assert result["events"][0].level in {"watch_level_1", "watch_level_2", "watch_level_3"}


def test_run_watchlist_poll_once_calculates_oi_change_before_append():
    scanner = ExtremeFundingWatchlistScanner()
    oi_window = OpenInterestWindow(lookback_sec=3600)
    oi_window.append("DOGE/USDT", timestamp_ms=0, open_interest=100.0)

    result = run_watchlist_poll_once(
        pairs=("DOGE/USDT",),
        scanner=scanner,
        oi_window=oi_window,
        timestamp_ms=3600 * 1000,
        premium_payload=_premium_payload(),
        oi_payloads={"DOGEUSDT": {"openInterest": "110"}},
        oi_data_age_sec=1.0,
    )

    assert result["snapshots"][0]["oi_change_1h_pct"] == 10.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py::test_run_watchlist_poll_once_rejects_until_persistence_warmup_complete tests/scripts/test_run_extreme_funding_watchlist.py::test_run_watchlist_poll_once_emits_after_warmup_and_persistence tests/scripts/test_run_extreme_funding_watchlist.py::test_run_watchlist_poll_once_calculates_oi_change_before_append -v
```

Expected: FAIL with missing `run_watchlist_poll_once`.

- [ ] **Step 3: Implement `run_watchlist_poll_once()`**

Add to `scripts/run_extreme_funding_watchlist.py`:

```python
from strategies.extreme_funding.scanner import ExtremeFundingWatchlistScanner


def run_watchlist_poll_once(
    *,
    pairs: tuple[str, ...],
    scanner: ExtremeFundingWatchlistScanner,
    oi_window: OpenInterestWindow,
    timestamp_ms: int,
    premium_payload: list[dict] | dict,
    oi_payloads: dict[str, dict],
    oi_data_age_sec: float,
) -> dict[str, Any]:
    events = []
    reject_reasons = []
    snapshots = []

    for pair in pairs:
        binance_symbol = binance_symbol_from_pair(pair)
        premium_item = find_premium_item(premium_payload, binance_symbol)
        if premium_item is None:
            reject_reasons.append("missing_premium")
            continue

        oi_payload = oi_payloads.get(binance_symbol)
        open_interest = parse_open_interest(oi_payload) if oi_payload else None
        oi_change = None
        if open_interest is not None:
            # Calculate against the previous retained value before appending current OI.
            oi_change = oi_window.change_pct(
                pair,
                now_ms=timestamp_ms,
                current_open_interest=open_interest,
            )
            oi_window.append(pair, timestamp_ms=timestamp_ms, open_interest=open_interest)

        raw = build_raw_snapshot_from_public_data(
            pair=pair,
            exchange="binance",
            timestamp_ms=timestamp_ms,
            premium_item=premium_item,
            open_interest=open_interest,
            oi_change_1h_pct=oi_change,
            mark_data_age_sec=0.0,
            oi_data_age_sec=oi_data_age_sec if oi_payload else 999999.0,
        )
        snapshot = build_snapshot(raw)
        snapshots.append(snapshot)
        result = scanner.classify(snapshot)
        if result.event is not None:
            events.append(result.event)
        elif result.reject_reason is not None:
            reject_reasons.append(result.reject_reason)

    return {"events": events, "reject_reasons": reject_reasons, "snapshots": snapshots}
```

- [ ] **Step 4: Run tests to verify they pass**

Run the same pytest command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_extreme_funding_watchlist.py tests/scripts/test_run_extreme_funding_watchlist.py
git commit -m "feat: add extreme funding polling pass"
```

---

### Task 9: Add CLI Parser, OI Cache Loop, And Typed Error Classification

**Files:**
- Modify: `scripts/run_extreme_funding_watchlist.py`
- Modify: `tests/scripts/test_run_extreme_funding_watchlist.py`

- [ ] **Step 1: Write failing parser and error tests**

Append to `tests/scripts/test_run_extreme_funding_watchlist.py`:

```python
from json import JSONDecodeError
from urllib.error import URLError

from scripts.run_extreme_funding_watchlist import parse_args, classify_loop_exception


def test_parse_args_defaults_to_bounded_local_dry_run():
    args = parse_args([])

    assert args.forever is False
    assert args.max_iterations == 3
    assert args.data_root == "data"
    assert args.once is False


def test_parse_args_once_sets_single_fast_iteration():
    args = parse_args(["--once"])

    assert args.once is True
    assert args.max_iterations == 1
    assert args.poll_interval_sec == 0.0


def test_classify_loop_exception_separates_url_json_and_schema_errors():
    assert classify_loop_exception(URLError("offline"))[0] == "watchlist_url_error"
    assert classify_loop_exception(JSONDecodeError("bad", "{", 0))[0] == "watchlist_json_error"
    assert classify_loop_exception(KeyError("markPrice"))[0] == "watchlist_schema_error"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py::test_parse_args_defaults_to_bounded_local_dry_run tests/scripts/test_run_extreme_funding_watchlist.py::test_parse_args_once_sets_single_fast_iteration tests/scripts/test_run_extreme_funding_watchlist.py::test_classify_loop_exception_separates_url_json_and_schema_errors -v
```

Expected: FAIL with missing `parse_args` or `classify_loop_exception`.

- [ ] **Step 3: Implement parser and typed error classification**

Add to `scripts/run_extreme_funding_watchlist.py`:

```python
import argparse
import asyncio
import time
from json import JSONDecodeError
from pathlib import Path
from urllib.error import HTTPError, URLError
from loguru import logger

from configs.base import (
    EXTREME_FUNDING_BINANCE_FAPI_BASE_URL,
    EXTREME_FUNDING_EVENT_LOG_JSONL,
    EXTREME_FUNDING_HEARTBEAT_INTERVAL_SEC,
    EXTREME_FUNDING_HTTP_TIMEOUT_SEC,
    EXTREME_FUNDING_LOCAL_DRY_RUN_MAX_ITERATIONS,
    EXTREME_FUNDING_LOOP_ERROR_BACKOFF_SEC,
    EXTREME_FUNDING_MARK_DATA_POLL_INTERVAL_SEC,
    EXTREME_FUNDING_OI_CHANGE_LOOKBACK_SEC,
    EXTREME_FUNDING_OI_POLL_INTERVAL_SEC,
    EXTREME_FUNDING_WATCH_SYMBOLS,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 1A extreme funding watchlist daemon.")
    parser.add_argument("--forever", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=EXTREME_FUNDING_LOCAL_DRY_RUN_MAX_ITERATIONS)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--poll-interval-sec", type=float, default=float(EXTREME_FUNDING_MARK_DATA_POLL_INTERVAL_SEC))
    args = parser.parse_args(argv)
    if args.once:
        args.max_iterations = 1
        args.poll_interval_sec = 0.0
    return args


def classify_loop_exception(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, HTTPError):
        return "watchlist_http_error", f"status={exc.code} detail={exc.reason}"
    if isinstance(exc, URLError):
        return "watchlist_url_error", f"detail={exc.reason}"
    if isinstance(exc, JSONDecodeError):
        return "watchlist_json_error", f"detail={exc}"
    if isinstance(exc, KeyError):
        return "watchlist_schema_error", f"missing={exc}"
    return "watchlist_loop_error", f"type={type(exc).__name__} detail={exc}"
```

- [ ] **Step 4: Implement OI cache helper inside `main()`**

In `main()`, keep an `oi_payload_cache: dict[str, dict] = {}` and `last_oi_fetch_ts: float | None = None`.

Only refresh OI when:

```python
should_refresh_oi(
    last_fetch_ts=last_oi_fetch_ts,
    now_ts=now_ts,
    interval_sec=EXTREME_FUNDING_OI_POLL_INTERVAL_SEC,
)
```

Pass cached payloads to `run_watchlist_poll_once()` and pass:

```python
oi_age = oi_data_age_sec(last_fetch_ts=last_oi_fetch_ts, now_ts=now_ts)
```

This is the guard against watch level flicker: skipped OI cycles reuse cached OI as long as `oi_age <= EXTREME_FUNDING_MAX_OI_DATA_AGE_SEC` in the scanner.

- [ ] **Step 5: Implement bounded loop without final sleep**

At loop tail:

```python
iteration += 1
if not args.forever and iteration >= args.max_iterations:
    break
await asyncio.sleep(args.poll_interval_sec)
```

- [ ] **Step 6: Write heartbeat and watch events to JSONL**

Inside `main()`:

```python
event_log_path = Path(args.data_root) / EXTREME_FUNDING_EVENT_LOG_JSONL
```

For each watch event:

```python
append_jsonl(event_log_path, {"type": "watch_event", "event": event.__dict__})
```

For each heartbeat:

```python
append_jsonl(
    event_log_path,
    {
        "type": "heartbeat_summary",
        "timestamp_ms": now_ms,
        "events": len(result["events"]),
        "reject_counts": summarize_reject_counts(result["reject_reasons"]),
        "oi_data_age_sec": oi_age,
    },
)
```

- [ ] **Step 7: Run parser/error tests**

Run the same pytest command from Step 2.

Expected: PASS.

- [ ] **Step 8: Confirm no execution/private imports**

Run:

```bash
rg -n "execution|TradeIntent|RiskLimits|apiKey|secret|password" scripts/run_extreme_funding_watchlist.py
```

Expected: no output.

- [ ] **Step 9: Commit**

```bash
git add scripts/run_extreme_funding_watchlist.py tests/scripts/test_run_extreme_funding_watchlist.py
git commit -m "feat: add extreme funding watchlist cli loop"
```

---

### Task 10: Add Server Operation Document

**Files:**
- Create: `docs/ops/extreme_funding_watchlist_server.md`

- [ ] **Step 1: Create server operation document**

Create `docs/ops/extreme_funding_watchlist_server.md`:

```markdown
# Extreme Funding Watchlist Server Operation

## Purpose

Run Phase 1A.5 in observation-only mode. This daemon reads only Binance public endpoints and emits watchlist events, heartbeats, reject summaries, and JSONL evidence. It must not read private keys, balances, or execution state.

## Local One-Shot Dry Run

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --once
```

Expected:

- Process exits after one polling pass.
- No private API key required.
- JSONL evidence is written under `data/extreme_funding_watch_events.jsonl`.
- No imports from `execution`.

## Local Bounded Dry Run

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --max-iterations 3
```

Expected:

- Process exits after 3 iterations.
- OI is fetched through a 60s cache, not every 10s loop.
- Watch events may remain absent during the 5-minute persistence warm-up.

## Server Run Command

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --forever --data-root data
```

## systemd Example

```ini
[Unit]
Description=crypto-alpha-lab extreme funding watchlist
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/crypto-alpha-lab
Environment=PYTHONPATH=src
ExecStart=/usr/bin/env uv run python scripts/run_extreme_funding_watchlist.py --forever --data-root data
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 24h Review Checklist

- Total iterations.
- `watchlist_http_error`, `watchlist_url_error`, `watchlist_json_error`, `watchlist_schema_error` counts.
- `api_stale` count.
- `missing_premium` count.
- `micro_persistence_warmup` count.
- `watch_level_1/2/3` event count.
- Symbols that triggered events.
- Whether `oi_status` is mostly `ok`, `missing`, or `stale`.
- JSONL file size and latest heartbeat timestamp.

## Safety Boundary

This daemon is not allowed to:

- Import `execution`.
- Emit `SignalCandidate`.
- Create `TradeIntent`.
- Read API keys.
- Place orders.
```

- [ ] **Step 2: Run markdown existence check**

Run:

```bash
test -f docs/ops/extreme_funding_watchlist_server.md
```

Expected: exit code 0.

- [ ] **Step 3: Commit**

```bash
git add docs/ops/extreme_funding_watchlist_server.md
git commit -m "docs: add extreme funding watchlist server operation guide"
```

---

### Task 11: Full Verification And Local Dry Run

**Files:**
- Verify: all changed files

- [ ] **Step 1: Run script tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_extreme_funding_watchlist.py -v
```

Expected: PASS.

- [ ] **Step 2: Run scanner tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/strategies/test_extreme_funding_scanner.py -v
```

Expected: PASS.

- [ ] **Step 3: Run config tests**

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py -v
```

Expected: PASS.

- [ ] **Step 4: Run full tests**

Run:

```bash
make test
```

Expected: PASS.

- [ ] **Step 5: Run smoke checks**

Run:

```bash
make smoke
```

Expected: PASS.

- [ ] **Step 6: Run one-shot public dry run**

Run:

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --once
```

Expected:

- Process exits after one polling pass.
- No private API key required.
- No execution import or order placement.
- Logs show heartbeat, reject summary, watch events, or typed API errors.
- `data/extreme_funding_watch_events.jsonl` contains at least one heartbeat summary if the pass reaches heartbeat write.

- [ ] **Step 7: Confirm no execution/private imports**

Run:

```bash
rg -n "execution|TradeIntent|RiskLimits|apiKey|secret|password" scripts/run_extreme_funding_watchlist.py
```

Expected: no output.

- [ ] **Step 8: Commit docs plan if updated**

If only this plan file changed:

```bash
git add docs/plans/2026-05-24-extreme-funding-phase1a-live-polling-deploy-plan.md
git commit -m "docs: refine extreme funding live polling plan"
```

---

## Done Definition

This phase is done when:

- Binance premium payloads can be fetched from public REST.
- `find_premium_item()` supports both all-symbol list payloads and single-symbol dict payloads.
- Binance OI can be fetched from public REST and reused through a 60s cache.
- OI age is passed into the scanner so level 2/3 alerts do not flicker between OI refreshes.
- OI 1h change is computed before appending current OI.
- Scanner warm-up prevents watch events before 5 minutes of timestamp coverage.
- Mark-index premium and `lastFundingRate` source lineage are explicit.
- The daemon can run `--once` without private credentials.
- The daemon writes low-frequency JSONL evidence for watch events and heartbeats.
- Typed API errors are logged separately.
- The daemon never imports `execution`, `RiskLimits`, `TradeIntent`, or private API config.
- `make test` passes.
- `make smoke` passes.
- Server operation document exists.

---

## Not Done In This Plan

- No Phase 1B basis absorption.
- No `SignalCandidate`.
- No shadow position simulator.
- No live trading.
- No remote server installation.
- No private Binance or OKX endpoints.
- No raw 10s market-data persistence.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-24-extreme-funding-phase1a-live-polling-deploy-plan.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Choose an execution approach before modifying `src` or the polling script.
