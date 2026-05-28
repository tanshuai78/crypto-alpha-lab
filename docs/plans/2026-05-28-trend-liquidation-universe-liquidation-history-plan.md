# Trend / Liquidation Universe 对齐与 Liquidation 历史覆盖 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 Trend / Liquidation historical replay 的两个数据面缺口：`universe` 与 `TREND_REGIME_WATCH_SYMBOLS` 对齐，并把本地 Binance `forceOrder` 事件沉淀成可回放的小时级 liquidation proxy。

**Architecture:** 不接 execution，不改变 live trading 开关，不降低策略阈值。`forceOrder` WebSocket 不是完整清算成交明细，本计划只把它作为 `partial_snapshot_lower_bound` 下限代理使用；采集器新增 raw JSONL 归档，聚合器按 `symbol + utc hour` 输出方向拆分后的 hourly proxy，历史 replay 再按 `symbol + hour_bucket_ms` 回填 `liquidation_notional_1h_usdt` 并显式标注 source quality。

**Tech Stack:** Python 3.11, pytest, JSONL, Binance `forceOrder` WebSocket, existing `configs/base.py`, existing Trend Regime scanner and replay scripts.

---

## 1. 决策边界

本计划只解决数据覆盖问题，不做策略放宽。

- 不修改 `TREND_REGIME_VOL_BREAKOUT_MULTIPLIER = 2.5`。
- 不修改 `TREND_REGIME_MIN_1H_ABS_RETURN_PCT_MAJOR = 2.0`。
- 不修改 `TREND_REGIME_MIN_1H_ABS_RETURN_PCT_LARGE_ALT = 2.5`。
- 不修改 `TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_*`。
- 不引入第三方清算数据源作为主路径。
- 不把本轮 replay 结果解释成 live approval。
- 不把 Binance `forceOrder` 聚合值解释为市场完整 1h liquidation volume。

`forceOrder` 语义必须固定为：

```json
{
  "liquidation_source": "binance_forceorder_ws",
  "source_quality": "self_collected_partial_history",
  "liquidation_notional_semantics": "partial_snapshot_lower_bound",
  "liquidation_bucket_semantics": "utc_hour_floor_of_row_timestamp"
}
```

第三方数据源（例如 Coinglass/CryptoQuant）只作为后续可选补洞方案。若未来接入，必须单独标注 `liquidation_source="third_party"` 和 `source_quality`，不得和本地自采数据无标记混用。

---

## 2. 当前问题

上一轮 review 给出的两个 next actions 是正确的：

1. `data/trend_regime_historical_rows.jsonl` 中包含 `ADA/USDT`，但 `ADA/USDT` 不在 `TREND_REGIME_WATCH_SYMBOLS`，导致 `symbol_not_in_watchlist=499`，污染 reject summary。
2. 当前 historical rows 中 `liquidation_notional_1h_usdt` 全部为 `None`，所以 `liquidation_coverage_ratio=0.0`，`liquidation_cascade_*` 分支无法被验证。

根因：

- `build_trend_regime_market_rows.py` 当前默认已经使用 `TREND_REGIME_WATCH_SYMBOLS`，但旧历史文件是用包含 `ADA/USDT` 的参数生成的。
- `collect_trend_regime_force_orders.py` 当前只写滚动 1h cache：`data/trend_regime_liquidation_cache.json`，没有保留 raw event 历史，所以无法回填 replay。
- `forceOrder` 只提供 partial snapshot，下游必须把 liquidation notional 当作 lower-bound proxy，而不是完整 liquidation volume。

---

## 3. Files

- Modify: `configs/base.py`
- Modify: `scripts/collect_trend_regime_force_orders.py`
- Modify: `scripts/replay_trend_regime_shadow.py`
- Create: `scripts/aggregate_trend_regime_liquidations.py`
- Modify: `tests/scripts/test_collect_trend_regime_force_orders.py`
- Modify: `tests/scripts/test_build_trend_regime_market_rows.py`
- Modify: `tests/scripts/test_replay_trend_regime_shadow.py`
- Create: `tests/scripts/test_aggregate_trend_regime_liquidations.py`
- Modify: `docs/ops/trend_liquidation_phase1a_server_CN.md`
- Create: `docs/reviews/2026-05-28-trend-liquidation-universe-liquidation-history-review.md`

---

### Task 1: Add Config Paths And Universe Diagnostics

**Files:**
- Modify: `configs/base.py`
- Modify: `tests/scripts/test_build_trend_regime_market_rows.py`
- Modify: `tests/scripts/test_replay_trend_regime_shadow.py`
- Modify: `scripts/replay_trend_regime_shadow.py`

**Step 1: Add config constants**

In `configs/base.py`, under Trend / Liquidation Regime config, add:

```python
TREND_REGIME_FORCE_ORDER_RAW_JSONL = "trend_regime_force_orders_raw.jsonl"
# Raw Binance forceOrder events collected locally for replayable liquidation proxy history.

TREND_REGIME_LIQUIDATION_HOURLY_JSONL = "trend_regime_liquidation_hourly.jsonl"
# Hourly symbol-level liquidation proxy derived from local forceOrder raw events.
```

**Step 2: Write regression test for default universe**

Add to `tests/scripts/test_build_trend_regime_market_rows.py`:

```python
from configs.base import TREND_REGIME_WATCH_SYMBOLS
from scripts.build_trend_regime_market_rows import parse_args


def test_market_rows_default_symbols_match_trend_watchlist():
    args = parse_args([])

    assert tuple(args.symbols) == tuple(TREND_REGIME_WATCH_SYMBOLS)
```

Expected: PASS if current default remains correct.

**Step 3: Write failing test for non-watchlist vs missing-symbol split**

Add to `tests/scripts/test_replay_trend_regime_shadow.py`:

```python
def test_historical_replay_splits_missing_symbol_from_non_watchlist_rows():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT"),
        _row(timestamp_ms=2000, symbol="ADA/USDT"),
        _row(timestamp_ms=3000, symbol=""),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["missing_symbol_row_count"] == 1
    assert summary["non_watchlist_row_count"] == 1
    assert summary["non_watchlist_symbols"] == ["ADA/USDT"]
```

**Step 4: Run tests to verify failure**

Run from repo root:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_build_trend_regime_market_rows.py tests/scripts/test_replay_trend_regime_shadow.py
```

Expected: FAIL only on missing new diagnostic fields.

**Step 5: Implement replay diagnostics**

In `scripts/replay_trend_regime_shadow.py`, import `TREND_REGIME_WATCH_SYMBOLS` and add:

```python
def _universe_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    watch = set(TREND_REGIME_WATCH_SYMBOLS)
    missing_symbol_count = 0
    non_watchlist_count = 0
    non_watchlist_symbols: set[str] = set()

    for row in rows:
        symbol = str(row.get("symbol") or "")
        if not symbol:
            missing_symbol_count += 1
        elif symbol not in watch:
            non_watchlist_count += 1
            non_watchlist_symbols.add(symbol)

    return {
        "missing_symbol_row_count": missing_symbol_count,
        "non_watchlist_row_count": non_watchlist_count,
        "non_watchlist_symbols": sorted(non_watchlist_symbols),
    }
```

Add these fields into `build_shadow_summary(...)`.

**Step 6: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_build_trend_regime_market_rows.py tests/scripts/test_replay_trend_regime_shadow.py
```

Expected: PASS.

**Step 7: Commit**

```bash
git add configs/base.py scripts/replay_trend_regime_shadow.py tests/scripts/test_build_trend_regime_market_rows.py tests/scripts/test_replay_trend_regime_shadow.py
git commit -m "test: lock trend replay universe diagnostics"
```

---

### Task 2: Persist Raw ForceOrder Events With Direction

**Files:**
- Modify: `scripts/collect_trend_regime_force_orders.py`
- Modify: `tests/scripts/test_collect_trend_regime_force_orders.py`

**Step 1: Write failing parser test for side and order fields**

Update `test_parse_force_order_notional_event_from_combined_stream_payload` so parsed output includes:

```python
assert parsed is not None
assert parsed["symbol"] == "BTCUSDT"
assert parsed["event_time_ms"] == 1710000000123
assert parsed["order_trade_time_ms"] == 1710000000456
assert parsed["side"] == "SELL"
assert parsed["liquidation_side"] == "long_liquidation"
assert parsed["quantity"] == 0.288
assert parsed["average_price"] == 39021.0
assert parsed["notional_usdt"] == 11238.048
```

Use payload:

```python
message = {
    "stream": "btcusdt@forceOrder",
    "data": {
        "e": "forceOrder",
        "E": 1710000000123,
        "o": {
            "s": "BTCUSDT",
            "S": "SELL",
            "T": 1710000000456,
            "ap": "39021.00",
            "z": "0.288",
        },
    },
}
```

Direction mapping:

- `SELL` => `long_liquidation`
- `BUY` => `short_liquidation`

**Step 2: Write failing raw record test**

Add:

```python
def test_build_force_order_raw_record_marks_partial_semantics():
    record = build_force_order_raw_record(
        symbol="BTCUSDT",
        event_time_ms=1710003599999,
        order_trade_time_ms=1710003599998,
        side="SELL",
        quantity=0.5,
        average_price=65000.0,
        notional_usdt=32500.0,
    )

    expected_hour = 1710003599999 // 3_600_000 * 3_600_000
    assert record["hour_bucket_ms"] == expected_hour
    assert record["liquidation_side"] == "long_liquidation"
    assert record["liquidation_notional_semantics"] == "partial_snapshot_lower_bound"
    assert record["source"] == "binance_forceorder_ws"
    assert record["source_quality"] == "self_collected_partial_history"
```

**Step 3: Write failing append JSONL test**

Add:

```python
def test_append_force_order_raw_jsonl_writes_one_line(tmp_path):
    path = tmp_path / "raw.jsonl"
    record = build_force_order_raw_record(
        symbol="BTCUSDT",
        event_time_ms=1710000000000,
        order_trade_time_ms=1710000000000,
        side="BUY",
        quantity=1.0,
        average_price=10.0,
        notional_usdt=10.0,
    )

    append_force_order_raw_jsonl(path, record)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["liquidation_side"] == "short_liquidation"
```

**Step 4: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_collect_trend_regime_force_orders.py
```

Expected: FAIL because parser/raw helpers do not yet expose these fields.

**Step 5: Implement parser dict output**

Change `parse_force_order_notional_event(...)` to return `dict[str, Any] | None`:

```python
def liquidation_side_from_order_side(side: str) -> str:
    normalized = side.upper()
    if normalized == "SELL":
        return "long_liquidation"
    if normalized == "BUY":
        return "short_liquidation"
    return "unknown"
```

Return:

```python
return {
    "symbol": symbol,
    "event_time_ms": event_time_ms,
    "order_trade_time_ms": order_trade_time_ms,
    "side": side,
    "liquidation_side": liquidation_side_from_order_side(side),
    "quantity": quantity,
    "average_price": price,
    "notional_usdt": round(quantity * price, 10),
}
```

Use `order.get("T")` for `order_trade_time_ms`; fall back to `event_time_ms`.

**Step 6: Implement raw record helpers**

Add:

```python
def hour_bucket_ms(timestamp_ms: int) -> int:
    return timestamp_ms // 3_600_000 * 3_600_000


def build_force_order_raw_record(
    *,
    symbol: str,
    event_time_ms: int,
    order_trade_time_ms: int,
    side: str,
    quantity: float,
    average_price: float,
    notional_usdt: float,
) -> dict[str, Any]:
    return {
        "event_time_ms": int(event_time_ms),
        "order_trade_time_ms": int(order_trade_time_ms),
        "hour_bucket_ms": hour_bucket_ms(int(event_time_ms)),
        "symbol": str(symbol).upper(),
        "side": str(side).upper(),
        "liquidation_side": liquidation_side_from_order_side(str(side)),
        "quantity": float(quantity),
        "average_price": float(average_price),
        "notional_usdt": float(notional_usdt),
        "source": "binance_forceorder_ws",
        "source_quality": "self_collected_partial_history",
        "liquidation_notional_semantics": "partial_snapshot_lower_bound",
    }
```

Add:

```python
def append_force_order_raw_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
```

**Step 7: Wire collector and bind `raw_output_path`**

In `parse_args(...)`, add:

```python
parser.add_argument("--raw-output", default=f"data/{TREND_REGIME_FORCE_ORDER_RAW_JSONL}")
```

Import `TREND_REGIME_FORCE_ORDER_RAW_JSONL`.

At the start of `run_collector(...)`, after `output_path = Path(args.output)`, add:

```python
raw_output_path = Path(args.raw_output)
```

When parsed event exists:

```python
accumulator.add_event(
    parsed["symbol"],
    event_time_ms=int(parsed["event_time_ms"]),
    notional_usdt=float(parsed["notional_usdt"]),
)
record = build_force_order_raw_record(**parsed)
try:
    append_force_order_raw_jsonl(raw_output_path, record)
except Exception as exc:
    logger.warning("force_order_raw_append_error reason={}", exc)
```

This explicitly fixes the potential `NameError` for `raw_output_path`.

**Step 8: Add small collector smoke test**

Add a test that constructs `argparse.Namespace` with `raw_output` and calls a helper-free path if available. If full WebSocket mocking is too large, at minimum assert `parse_args(["--raw-output", "x.jsonl"]).raw_output == "x.jsonl"` and raw helper writes successfully. Do not mock network unless the implementation already has an injectable WebSocket seam.

**Step 9: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_collect_trend_regime_force_orders.py
```

Expected: PASS.

**Step 10: Commit**

```bash
git add configs/base.py scripts/collect_trend_regime_force_orders.py tests/scripts/test_collect_trend_regime_force_orders.py
git commit -m "feat: persist directional trend force order events"
```

---

### Task 3: Add Directional Hourly Liquidation Aggregator

**Files:**
- Create: `scripts/aggregate_trend_regime_liquidations.py`
- Create: `tests/scripts/test_aggregate_trend_regime_liquidations.py`

**Step 1: Write failing tests**

Create `tests/scripts/test_aggregate_trend_regime_liquidations.py`:

```python
import json

from scripts.aggregate_trend_regime_liquidations import (
    aggregate_force_order_records,
    hour_bucket_ms,
    load_force_order_raw_jsonl,
    write_hourly_liquidation_jsonl,
)


def test_hour_bucket_matches_row_close_time_semantics():
    assert hour_bucket_ms(1710003599999) == 1710000000000


def test_aggregate_force_order_records_groups_by_symbol_hour_and_direction():
    rows = [
        {
            "symbol": "BTCUSDT",
            "hour_bucket_ms": 1710000000000,
            "liquidation_side": "long_liquidation",
            "notional_usdt": 10.0,
        },
        {
            "symbol": "BTCUSDT",
            "hour_bucket_ms": 1710000000000,
            "liquidation_side": "short_liquidation",
            "notional_usdt": 20.0,
        },
        {
            "symbol": "BTCUSDT",
            "hour_bucket_ms": 1710000000000,
            "liquidation_side": "long_liquidation",
            "notional_usdt": 5.0,
        },
    ]

    aggregated = aggregate_force_order_records(rows)

    assert aggregated == [
        {
            "symbol": "BTCUSDT",
            "hour_bucket_ms": 1710000000000,
            "liquidation_notional_1h_usdt": 35.0,
            "long_liquidation_notional_1h_usdt": 15.0,
            "short_liquidation_notional_1h_usdt": 20.0,
            "long_liquidation_event_count": 2,
            "short_liquidation_event_count": 1,
            "event_count": 3,
            "liquidation_source": "binance_forceorder_ws",
            "source_quality": "self_collected_partial_history",
            "liquidation_notional_semantics": "partial_snapshot_lower_bound",
            "liquidation_bucket_semantics": "utc_hour_floor_of_row_timestamp",
        }
    ]
```

Add round-trip test:

```python
def test_load_and_write_hourly_liquidation_jsonl_round_trip(tmp_path):
    raw = tmp_path / "raw.jsonl"
    out = tmp_path / "hourly.jsonl"
    raw.write_text(
        json.dumps(
            {
                "symbol": "BTCUSDT",
                "hour_bucket_ms": 1710000000000,
                "liquidation_side": "long_liquidation",
                "notional_usdt": 10.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = load_force_order_raw_jsonl(raw)
    hourly = aggregate_force_order_records(rows)
    write_hourly_liquidation_jsonl(out, hourly)

    decoded = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert decoded[0]["liquidation_notional_1h_usdt"] == 10.0
    assert decoded[0]["long_liquidation_notional_1h_usdt"] == 10.0
```

**Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_aggregate_trend_regime_liquidations.py
```

Expected: FAIL because script does not exist.

**Step 3: Implement script**

Create `scripts/aggregate_trend_regime_liquidations.py` with:

```python
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from configs.base import (
    TREND_REGIME_FORCE_ORDER_RAW_JSONL,
    TREND_REGIME_LIQUIDATION_HOURLY_JSONL,
)


def hour_bucket_ms(timestamp_ms: int) -> int:
    return timestamp_ms // 3_600_000 * 3_600_000


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def load_force_order_raw_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    p = Path(path)
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def aggregate_force_order_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, int], dict[str, float | int]] = defaultdict(
        lambda: {
            "long_notional": 0.0,
            "short_notional": 0.0,
            "long_count": 0,
            "short_count": 0,
        }
    )
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        hour = int(_number_or_none(row.get("hour_bucket_ms")) or 0)
        side = str(row.get("liquidation_side") or "")
        notional = _number_or_none(row.get("notional_usdt"))
        if not symbol or hour <= 0 or notional is None or notional <= 0.0:
            continue
        key = (symbol, hour)
        if side == "long_liquidation":
            buckets[key]["long_notional"] = float(buckets[key]["long_notional"]) + notional
            buckets[key]["long_count"] = int(buckets[key]["long_count"]) + 1
        elif side == "short_liquidation":
            buckets[key]["short_notional"] = float(buckets[key]["short_notional"]) + notional
            buckets[key]["short_count"] = int(buckets[key]["short_count"]) + 1

    output: list[dict[str, Any]] = []
    for (symbol, hour), value in sorted(buckets.items(), key=lambda item: (item[0][1], item[0][0])):
        long_notional = float(value["long_notional"])
        short_notional = float(value["short_notional"])
        long_count = int(value["long_count"])
        short_count = int(value["short_count"])
        output.append(
            {
                "symbol": symbol,
                "hour_bucket_ms": hour,
                "liquidation_notional_1h_usdt": round(long_notional + short_notional, 10),
                "long_liquidation_notional_1h_usdt": round(long_notional, 10),
                "short_liquidation_notional_1h_usdt": round(short_notional, 10),
                "long_liquidation_event_count": long_count,
                "short_liquidation_event_count": short_count,
                "event_count": long_count + short_count,
                "liquidation_source": "binance_forceorder_ws",
                "source_quality": "self_collected_partial_history",
                "liquidation_notional_semantics": "partial_snapshot_lower_bound",
                "liquidation_bucket_semantics": "utc_hour_floor_of_row_timestamp",
            }
        )
    return output


def write_hourly_liquidation_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate trend forceOrder raw events to hourly liquidation proxy JSONL")
    parser.add_argument("--input", default=f"data/{TREND_REGIME_FORCE_ORDER_RAW_JSONL}")
    parser.add_argument("--output", default=f"data/{TREND_REGIME_LIQUIDATION_HOURLY_JSONL}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raw = load_force_order_raw_jsonl(args.input)
    hourly = aggregate_force_order_records(raw)
    write_hourly_liquidation_jsonl(args.output, hourly)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_aggregate_trend_regime_liquidations.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/aggregate_trend_regime_liquidations.py tests/scripts/test_aggregate_trend_regime_liquidations.py
git commit -m "feat: aggregate directional trend liquidation proxy"
```

---

### Task 4: Join Hourly Liquidation Proxy Into Historical Replay

**Files:**
- Modify: `scripts/replay_trend_regime_shadow.py`
- Modify: `tests/scripts/test_replay_trend_regime_shadow.py`

**Step 1: Write failing join test**

Add to `tests/scripts/test_replay_trend_regime_shadow.py`:

```python
from scripts.replay_trend_regime_shadow import apply_hourly_liquidation_history


def test_apply_hourly_liquidation_history_fills_matching_symbol_hour_with_semantics():
    hour = 1710003599999 // 3_600_000 * 3_600_000
    rows = [
        _row(timestamp_ms=1710003599999, symbol="BTC/USDT", liquidation_notional_1h_usdt=None),
        _row(timestamp_ms=1710003599999, symbol="ETH/USDT", liquidation_notional_1h_usdt=None),
    ]
    hourly = [
        {
            "symbol": "BTCUSDT",
            "hour_bucket_ms": hour,
            "liquidation_notional_1h_usdt": 12_000_000.0,
            "long_liquidation_notional_1h_usdt": 7_000_000.0,
            "short_liquidation_notional_1h_usdt": 5_000_000.0,
            "liquidation_source": "binance_forceorder_ws",
            "source_quality": "self_collected_partial_history",
            "liquidation_notional_semantics": "partial_snapshot_lower_bound",
            "liquidation_bucket_semantics": "utc_hour_floor_of_row_timestamp",
        }
    ]

    filled, summary = apply_hourly_liquidation_history(rows, hourly)

    assert filled[0]["liquidation_notional_1h_usdt"] == 12_000_000.0
    assert filled[0]["long_liquidation_notional_1h_usdt"] == 7_000_000.0
    assert filled[0]["short_liquidation_notional_1h_usdt"] == 5_000_000.0
    assert filled[0]["liquidation_notional_semantics"] == "partial_snapshot_lower_bound"
    assert filled[1]["liquidation_notional_1h_usdt"] is None
    assert summary["liquidation_rows_joined_count"] == 1
    assert summary["liquidation_notional_semantics"] == "partial_snapshot_lower_bound"
```

**Step 2: Write failing optional-loader test**

Add:

```python
from scripts.replay_trend_regime_shadow import load_optional_jsonl


def test_load_optional_jsonl_returns_empty_for_missing_file(tmp_path):
    assert load_optional_jsonl(tmp_path / "missing.jsonl") == []
```

**Step 3: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_replay_trend_regime_shadow.py
```

Expected: FAIL because helpers do not exist or fields are missing.

**Step 4: Implement join helper**

In `scripts/replay_trend_regime_shadow.py`, add:

```python
def _symbol_key(symbol: str) -> str:
    return symbol.replace("/", "").upper()


def _hour_bucket_ms(timestamp_ms: int) -> int:
    return timestamp_ms // 3_600_000 * 3_600_000


def apply_hourly_liquidation_history(
    rows: list[dict[str, Any]],
    hourly_liquidations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lookup: dict[tuple[str, int], dict[str, Any]] = {}
    raw_start_values: list[int] = []
    for item in hourly_liquidations:
        symbol = _symbol_key(str(item.get("symbol") or ""))
        hour = int(_number_or_none(item.get("hour_bucket_ms")) or 0)
        if symbol and hour > 0:
            lookup[(symbol, hour)] = item
            raw_start_values.append(hour)

    joined = 0
    output: list[dict[str, Any]] = []
    for row in rows:
        patched = dict(row)
        symbol = _symbol_key(str(row.get("symbol") or ""))
        ts_ms = int(_number_or_none(row.get("timestamp_ms")) or 0)
        existing = _number_or_none(row.get("liquidation_notional_1h_usdt"))
        match = lookup.get((symbol, _hour_bucket_ms(ts_ms))) if symbol and ts_ms > 0 else None
        if existing is None and match is not None:
            notional = _number_or_none(match.get("liquidation_notional_1h_usdt"))
            if notional is not None:
                patched["liquidation_notional_1h_usdt"] = notional
                patched["long_liquidation_notional_1h_usdt"] = _number_or_none(match.get("long_liquidation_notional_1h_usdt")) or 0.0
                patched["short_liquidation_notional_1h_usdt"] = _number_or_none(match.get("short_liquidation_notional_1h_usdt")) or 0.0
                patched["liquidation_source"] = str(match.get("liquidation_source") or "binance_forceorder_ws")
                patched["liquidation_source_quality"] = str(match.get("source_quality") or "unknown")
                patched["liquidation_notional_semantics"] = str(match.get("liquidation_notional_semantics") or "partial_snapshot_lower_bound")
                patched["liquidation_bucket_semantics"] = str(match.get("liquidation_bucket_semantics") or "utc_hour_floor_of_row_timestamp")
                joined += 1
        output.append(patched)

    raw_start_ms = min(raw_start_values) if raw_start_values else 0
    raw_end_ms = max(raw_start_values) if raw_start_values else 0
    duration_hours = (raw_end_ms - raw_start_ms) / 3_600_000.0 if raw_end_ms > raw_start_ms else 0.0
    return output, {
        "liquidation_history_input_count": len(hourly_liquidations),
        "liquidation_rows_joined_count": joined,
        "liquidation_history_source": "binance_forceorder_ws" if hourly_liquidations else "none",
        "liquidation_history_source_quality": "self_collected_partial_history" if hourly_liquidations else "missing",
        "liquidation_notional_semantics": "partial_snapshot_lower_bound" if hourly_liquidations else "missing",
        "liquidation_bucket_semantics": "utc_hour_floor_of_row_timestamp",
        "liquidation_raw_start_ms": raw_start_ms,
        "liquidation_raw_end_ms": raw_end_ms,
        "liquidation_raw_duration_hours": round(duration_hours, 10),
    }
```

**Step 5: Add optional loader with file existence guard**

Add:

```python
def load_optional_jsonl(path: str | Path) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return load_rows_jsonl(p)
```

**Step 6: Add CLI arg and join summary**

In `parse_args(...)`, add:

```python
parser.add_argument("--liquidation-hourly-jsonl", default="")
```

Before `build_dual_cost_summary(rows)`:

```python
hourly = load_optional_jsonl(args.liquidation_hourly_jsonl)
rows, join_summary = apply_hourly_liquidation_history(rows, hourly)
summary = build_dual_cost_summary(rows)
summary["liquidation_history_join_summary"] = join_summary
```

**Step 7: Ensure summary exposes ratio**

`build_shadow_summary(...)` must explicitly include `liquidation_coverage_ratio`. If it currently relies on audit internals, keep it at top level:

```python
total_audit_rows = (
    audit["rows_with_liquidation_notional_count"]
    + audit["rows_missing_liquidation_notional_count"]
)
coverage_ratio = (
    round(audit["rows_with_liquidation_notional_count"] / total_audit_rows, 10)
    if total_audit_rows > 0
    else 0.0
)
summary["liquidation_coverage_ratio"] = coverage_ratio
```

**Step 8: Run tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_replay_trend_regime_shadow.py tests/scripts/test_aggregate_trend_regime_liquidations.py
```

Expected: PASS.

**Step 9: Commit**

```bash
git add scripts/replay_trend_regime_shadow.py tests/scripts/test_replay_trend_regime_shadow.py
git commit -m "feat: join partial liquidation proxy into trend replay"
```

---

### Task 5: Update Server Guide For Raw And Hourly Artifacts

**Files:**
- Modify: `docs/ops/trend_liquidation_phase1a_server_CN.md`

**Step 1: Update forceOrder container command**

Add `--raw-output`:

```bash
docker run -d --name trend-forceorder \
  --restart always \
  --memory="512m" \
  -v /root/crypto-alpha-lab/data:/app/data \
  -v /root/crypto-alpha-lab/logs:/app/logs \
  crypto-alpha-lab:latest \
  python scripts/collect_trend_regime_force_orders.py \
    --output data/trend_regime_liquidation_cache.json \
    --raw-output data/trend_regime_force_orders_raw.jsonl \
    --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT
```

**Step 2: Add hourly aggregation command**

Add:

```bash
docker exec trend-forceorder \
  python scripts/aggregate_trend_regime_liquidations.py \
    --input data/trend_regime_force_orders_raw.jsonl \
    --output data/trend_regime_liquidation_hourly.jsonl
```

**Step 3: Add replay command with liquidation proxy**

Add:

```bash
PYTHONPATH=src uv run python scripts/replay_trend_regime_shadow.py \
  --input data/trend_regime_historical_rows_watchlist.jsonl \
  --liquidation-hourly-jsonl data/trend_regime_liquidation_hourly.jsonl \
  --output reports/trend_regime/2026-05-28_historical_replay_dual_cost_summary.json
```

**Step 4: Add pullback commands**

Add:

```bash
mkdir -p data/trend_regime

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_force_orders_raw.jsonl \
  data/trend_regime/

rsync -avzP \
  root@47.82.4.85:/root/crypto-alpha-lab/data/trend_regime_liquidation_hourly.jsonl \
  data/trend_regime/
```

Use relative local paths in docs. Do not hardcode `/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab` in new commands.

**Step 5: Add semantic warning**

Add an explicit note:

```markdown
`trend_regime_liquidation_hourly.jsonl` is a partial lower-bound proxy from Binance `forceOrder` WebSocket snapshots. It is not full market liquidation volume.
```

**Step 6: Verify no placeholders**

Run:

```bash
rg -n "TODO|TBD|待补|占位|PLAN_NEEDS_VALUE|UNRESOLVED" docs/ops/trend_liquidation_phase1a_server_CN.md
```

Expected: no output.

**Step 7: Commit**

```bash
git add docs/ops/trend_liquidation_phase1a_server_CN.md
git commit -m "docs: document trend liquidation proxy artifacts"
```

---

### Task 6: Rerun Replay And Write Review

**Files:**
- Create: `docs/reviews/2026-05-28-trend-liquidation-universe-liquidation-history-review.md`
- Create/Modify: `reports/trend_regime/2026-05-28_historical_replay_dual_cost_summary.json`

**Step 1: Regenerate historical rows with aligned universe**

Run from repo root:

```bash
PYTHONPATH=src uv run python scripts/build_trend_regime_market_rows.py \
  --output data/trend_regime_historical_rows_watchlist.jsonl \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --kline-limit 800 \
  --oi-limit 500
```

Expected:

- `ADA/USDT` absent.
- replay summary later reports `non_watchlist_row_count == 0`.

**Step 2: Aggregate local forceOrder history**

Run:

```bash
PYTHONPATH=src uv run python scripts/aggregate_trend_regime_liquidations.py \
  --input data/trend_regime_force_orders_raw.jsonl \
  --output data/trend_regime_liquidation_hourly.jsonl
```

Expected:

- If raw file exists: hourly JSONL rows generated.
- If raw file is missing/empty: command exits cleanly and outputs empty hourly file.

**Step 3: Rerun replay**

Run:

```bash
PYTHONPATH=src uv run python scripts/replay_trend_regime_shadow.py \
  --input data/trend_regime_historical_rows_watchlist.jsonl \
  --liquidation-hourly-jsonl data/trend_regime_liquidation_hourly.jsonl \
  --output reports/trend_regime/2026-05-28_historical_replay_dual_cost_summary.json
```

Expected summary checks:

- `base.non_watchlist_row_count == 0`
- `stress.non_watchlist_row_count == 0`
- `liquidation_history_join_summary.liquidation_notional_semantics == "partial_snapshot_lower_bound"` when hourly input exists
- `base.liquidation_coverage_ratio` is explicit
- `liquidation_raw_duration_hours` is explicit

**Step 4: Write review**

Create `docs/reviews/2026-05-28-trend-liquidation-universe-liquidation-history-review.md` with:

```markdown
# Trend / Liquidation Universe + Liquidation History Review

**Date:** 2026-05-28
**Input rows:** `data/trend_regime_historical_rows_watchlist.jsonl`
**Liquidation hourly:** `data/trend_regime_liquidation_hourly.jsonl`
**Replay summary:** `reports/trend_regime/2026-05-28_historical_replay_dual_cost_summary.json`

## 1. Universe Alignment

- `missing_symbol_row_count`: <paste exact value>
- `non_watchlist_row_count`: <paste exact value>
- `non_watchlist_symbols`: <paste exact value>
- Decision: pass/fail

## 2. Liquidation Proxy Coverage

- `liquidation_history_input_count`: <paste exact value>
- `liquidation_rows_joined_count`: <paste exact value>
- `liquidation_coverage_ratio`: <paste exact value>
- `liquidation_history_source`: <paste exact value>
- `liquidation_history_source_quality`: <paste exact value>
- `liquidation_notional_semantics`: <paste exact value>
- `liquidation_raw_start_ms`: <paste exact value>
- `liquidation_raw_end_ms`: <paste exact value>
- `liquidation_raw_duration_hours`: <paste exact value>

Important: local `forceOrder` data is `partial_snapshot_lower_bound`, not full liquidation volume.

## 3. Replay Outcome

- `entry_event_count`: <paste exact value>
- `classification_reject_counts`: <paste exact JSON>
- `shadow_trade_count`: <paste exact value>
- `base.mean_net_pnl_bps`: <paste exact value>
- `stress.mean_net_pnl_bps`: <paste exact value>

## 4. Decision

Allowed decisions:

- `keep_observation_only`
- `continue_liquidation_data_collection`
- `continue_partial_liquidation_collection`
- `liquidation_history_insufficient_partial_source`
- `eligible_for_phase1b_review`

No live approval is allowed from this review.
```

**Step 5: Verify placeholders removed**

Run:

```bash
rg -n "paste exact|TODO|TBD|待补|占位|PLAN_NEEDS_VALUE|UNRESOLVED" docs/reviews/2026-05-28-trend-liquidation-universe-liquidation-history-review.md
```

Expected: no output.

**Step 6: Run full focused tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_collect_trend_regime_force_orders.py \
  tests/scripts/test_aggregate_trend_regime_liquidations.py \
  tests/scripts/test_build_trend_regime_market_rows.py \
  tests/scripts/test_replay_trend_regime_shadow.py \
  tests/strategies/test_trend_regime_scanner.py
```

Expected: PASS.

**Step 7: Commit review artifacts only**

Do not commit runtime `data/*.jsonl` artifacts. If a tiny fixture is needed for tests, place it under `tests/fixtures/trend_regime/`.

Commit:

```bash
git add \
  reports/trend_regime/2026-05-28_historical_replay_dual_cost_summary.json \
  docs/reviews/2026-05-28-trend-liquidation-universe-liquidation-history-review.md
git commit -m "research: review trend liquidation proxy coverage"
```

---

## 4. Done Definition

本计划完成后必须满足：

- `TREND_REGIME_WATCH_SYMBOLS` 是 Trend historical rows 默认 universe 的唯一来源。
- replay summary 明确输出 `missing_symbol_row_count`、`non_watchlist_row_count` 与 `non_watchlist_symbols`。
- `collect_trend_regime_force_orders.py` 同时写滚动 cache 和 raw JSONL。
- raw forceOrder 事件保留 `side`、`liquidation_side`、`quantity`、`average_price`、`order_trade_time_ms`。
- hourly aggregation 输出 `long_liquidation_notional_1h_usdt`、`short_liquidation_notional_1h_usdt` 与总 `liquidation_notional_1h_usdt`。
- 所有 liquidation artifacts 标注 `liquidation_notional_semantics="partial_snapshot_lower_bound"`。
- historical replay 可以按 `symbol + hour_bucket_ms` 回填 liquidation proxy。
- replay summary 明确输出 liquidation history join summary、coverage ratio、raw coverage duration。
- 如果 liquidation coverage 仍不足，review 必须输出 `continue_liquidation_data_collection` 或 `continue_partial_liquidation_collection`，不能把 liquidation 分支误判为无效。
- 所有 focused tests 通过。

---

## 5. Review Gate

本轮不以 `shadow_trade_count > 0` 作为唯一成功标准。

通过本轮数据链路修复的最低条件：

- `missing_symbol_row_count == 0`
- `non_watchlist_row_count == 0`
- `liquidation_history_join_summary` 存在
- `liquidation_notional_semantics` 明确为 `partial_snapshot_lower_bound` 或 `missing`
- `liquidation_coverage_ratio` 可解释
- `liquidation_raw_duration_hours` 可解释
- `classification_reject_counts` 可解释
- focused tests PASS

进入 `eligible_for_phase1b_review` 的最低条件仍沿用上一轮：

- `signal_count >= 20`
- `median_net_pnl_bps > 30`
- `mean_net_pnl_bps > 40`
- `win_rate > 55%`
- `worst_trade_net_pnl_bps > -200`
- `stop_loss_exit_rate < 35%`
- `stress cost 50 bps` 下 `median_net_pnl_bps > 0`
- 至少一个 `regime × direction × symbol_tier` 子类通过，不允许只看混合均值

决策规则：

```text
if non_watchlist_row_count > 0 or missing_symbol_row_count > 0:
    keep_observation_only

elif liquidation_coverage_ratio == 0:
    continue_liquidation_data_collection

elif liquidation_raw_duration_hours < 72:
    continue_partial_liquidation_collection

elif liquidation_source_quality == self_collected_partial_history
     and liquidation_cascade sample remains too small:
    liquidation_history_insufficient_partial_source

elif profitability gates pass:
    eligible_for_phase1b_review

else:
    keep_observation_only
```

---

## 6. Execution Handoff

Plan complete and saved to `docs/plans/2026-05-28-trend-liquidation-universe-liquidation-history-plan.md`.

Two execution options:

**1. Subagent-Driven (this session)** - Dispatch fresh subagent per task, review between tasks, fast iteration.

**2. Parallel Session (separate)** - Open new session with `executing-plans`, batch execution with checkpoints.

Which approach?
