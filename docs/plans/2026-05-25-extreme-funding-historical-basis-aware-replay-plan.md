# Extreme Funding Historical Basis-Aware Replay Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**目标:** 为 `extreme_funding` 建立历史基差感知回放，把 settled funding 样本与 Binance spot close / futures mark close 对齐，让 Phase 1B/1C 能验证 `basis_absorption_ratio` 与 basis-aware shadow PnL，而不是继续停留在 funding-only 诊断。

**架构:** Phase 1A live watchlist 不改。新增 research-only 数据构建层：先从 `data/funding_settled/*.jsonl` 中筛出历史极端 funding 时间点，再按这些时间点定向拉取 Binance spot kline 与 USD-M futures mark-price kline，构造 `HistoricalBasisRow`，最后复用现有 `build_extreme_funding_candidate(...)` 与 `simulate_extreme_funding_shadow(...)` 输出审计报告。

**技术栈:** Python 3.11, pytest, dataclasses, Binance public REST, JSONL, `configs/base.py` SSOT, existing `src/research/extreme_funding_replay.py`, existing `src/strategies/extreme_funding/candidate_builder.py`, existing `src/strategies/extreme_funding/shadow_simulator.py`。不使用 private API，不导入 `src/execution/`。

---

## 1. 本轮边界

本计划只解决一个问题：

历史极端 funding 样本到底在真实 spot/perp 基差路径下，是否仍有净边际。

本轮包含：

- 定义 `HistoricalBasisRow`。
- 从 public spot kline close 与 futures mark-price kline close 计算 `basis_bps`。
- 按 funding settlement time 定向构建 basis path，不下载全量 1m 五年数据。
- 基于 basis-aware rows 跑 Phase 1B candidate replay。
- 基于 basis-aware path 跑 Phase 1C shadow replay。
- 输出 `reports/extreme_funding/` 与 `docs/reviews/` 审计结果。

本轮不包含：

- live trading。
- private key / account balance。
- `TradeIntent`。
- `src/execution/`。
- 真实 orderbook depth replay。
- maker fill rate replay。
- withdrawal / deposit status。

## 2. 数据与证据边界

当前已完成的 funding-only review 只能证明：

- Phase 1B/1C 框架能跑。
- funding-only 数据不会被误判成完整可交易 candidate。
- funding-minus-cost 中位数为负，不能证明策略有效。

本轮新增的 basis-aware replay 可以进一步验证：

- 入场时 `basis_bps` 是否已经吃掉 funding 收益。
- 持仓 1-3 个 settlement interval 后，basis widening / narrowing 对 PnL 的影响。
- `basis_absorbed`、`net_edge_below_min`、`funding_decay`、`basis_loss_halt` 等 blocker 的真实分布。

但本轮仍不能证明：

- 真实盘口深度足够。
- 真实滑点小于 10 bps。
- maker 成交率大于 70%。

因此 coverage 必须写成：

- `historical_basis_proxy_not_depth_aware`

不能写成：

- `live_ready`
- `execution_ready`
- `orderbook_aware`

## 3. 不变量

- 所有新增阈值必须在 `configs/base.py`。
- `basis_bps` 只能来自 `perp_mid_price / spot_mid_price - 1`。
- entry / holding basis 只能使用 `funding_time_ms` 之前或等于该时间点的最近 price close，禁止用 settlement 之后的未来 K 线 close。
- 每条 basis row 必须记录 `spot_price_time_ms`、`perp_price_time_ms`、`selected_price_time_ms` 与 `price_time_diff_ms`，用于审计 spot/perp close 对齐质量。
- funding path selection 与 shadow simulation 必须按 `symbol` 分组，禁止 DOGE entry 使用 XRP / ETH / BTC 的后续 row。
- 没有 spot/perp price path 时，summary 必须输出 `status="insufficient_basis_data"`。
- 有 basis path 但没有真实 depth 时，必须输出 `depth_source="static_min_capacity_proxy"`。
- 所有 candidate / shadow summary 必须输出 `depth_aware=false`，避免把 static depth proxy 误读成真实可成交容量。
- 新增模块不得导入 `src/execution`、`TradeIntent`、`apiKey`、`secret`、`balance`。
- 新增脚本只写 `reports/extreme_funding/`，不写 `data/`。
- 所有网络请求只访问 Binance public REST。

---

## Task 1: Baseline And Source Audit

**Files:**

- Read: `docs/roadmap.md`
- Read: `configs/base.py`
- Read: `src/research/extreme_funding_replay.py`
- Read: `src/strategies/extreme_funding/candidate_builder.py`
- Read: `src/strategies/extreme_funding/shadow_simulator.py`
- Read: `data/funding_settled/*.jsonl`

### Step 1: Verify clean worktree

Run:

```bash
git status --short
```

Expected:

```text
(no output)
```

### Step 2: Run current baseline

Run:

```bash
PYTHONPATH=src uv run pytest \
  tests/test_extreme_funding_config.py \
  tests/research/test_extreme_funding_replay.py \
  tests/strategies/test_extreme_funding_candidate_builder.py \
  tests/strategies/test_extreme_funding_shadow_simulator.py \
  tests/scripts/test_replay_extreme_funding_candidates.py \
  tests/scripts/test_simulate_extreme_funding_shadow.py \
  -q
make test
make smoke
```

Expected:

```text
PASS
configs OK
risk gate OK
```

### Step 3: Audit available funding rows

Run:

```bash
find data/funding_settled -maxdepth 1 -type f | sort
head -n 3 data/funding_settled/binance_DOGEUSDT_settled.jsonl
```

Expected:

- settled funding JSONL exists。
- records contain timestamp / funding rate fields already used by `src/research/extreme_funding_replay.py`。

---

## Task 2: Add Historical Basis Replay Config

**Files:**

- Modify: `configs/base.py`
- Modify: `tests/test_extreme_funding_config.py`

### Step 1: Write failing config test

Append to `tests/test_extreme_funding_config.py`:

```python
def test_extreme_funding_historical_basis_replay_config_values_are_defined():
    assert base.EXTREME_FUNDING_BASIS_REPLAY_INTERVAL == "1m"
    assert base.EXTREME_FUNDING_BASIS_REPLAY_ALIGNMENT_TOLERANCE_MS == 120_000
    assert base.EXTREME_FUNDING_BASIS_REPLAY_REQUEST_WINDOW_MS == 300_000
    assert base.EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC == 20.0
    assert base.EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC == 0.2
    assert base.EXTREME_FUNDING_BASIS_REPLAY_STATIC_DEPTH_MULTIPLIER == 2.0
    assert base.EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR == "reports/extreme_funding"
```

### Step 2: Verify failing test

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py::test_extreme_funding_historical_basis_replay_config_values_are_defined -q
```

Expected:

```text
FAIL AttributeError
```

### Step 3: Add config constants

Add near the existing Extreme Funding config block in `configs/base.py`:

```python
EXTREME_FUNDING_BASIS_REPLAY_INTERVAL = "1m"
# Kline interval used for historical basis replay alignment.

EXTREME_FUNDING_BASIS_REPLAY_ALIGNMENT_TOLERANCE_MS = 120_000
# Maximum absolute distance between funding settlement time and selected price proxy.

EXTREME_FUNDING_BASIS_REPLAY_REQUEST_WINDOW_MS = 300_000
# Public kline request window around each funding settlement. 300s keeps downloads small.

EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC = 20.0
# Public REST timeout for historical basis replay.

EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC = 0.2
# Sleep between public REST requests to avoid aggressive polling.

EXTREME_FUNDING_BASIS_REPLAY_STATIC_DEPTH_MULTIPLIER = 2.0
# Static depth proxy multiplier against RISK_MAX_SINGLE_POSITION_USDT.

EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR = "reports/extreme_funding"
# Audit output directory for historical basis-aware replay reports.
```

### Step 4: Verify config tests

Run:

```bash
PYTHONPATH=src uv run pytest tests/test_extreme_funding_config.py -q
```

Expected:

```text
PASS
```

---

## Task 3: Add Historical Basis Row Contract

**Files:**

- Create: `src/research/extreme_funding_basis_replay.py`
- Create: `tests/research/test_extreme_funding_basis_replay.py`

### Step 1: Write failing row contract tests

Create `tests/research/test_extreme_funding_basis_replay.py`:

```python
from src.research.extreme_funding_basis_replay import (
    HistoricalBasisRow,
    basis_bps_from_prices,
    build_historical_basis_row,
)


def test_basis_bps_from_prices_uses_perp_over_spot() -> None:
    assert basis_bps_from_prices(spot_mid_price=100.0, perp_mid_price=101.0) == 100.0


def test_build_historical_basis_row_sets_proxy_lineage() -> None:
    row = build_historical_basis_row(
        symbol="DOGE/USDT",
        funding_time_ms=1000,
        funding_rate=0.008,
        annualized_pct=650.0,
        spot_mid_price=100.0,
        perp_mid_price=100.10,
        selected_price_time_ms=1000,
    )

    assert isinstance(row, HistoricalBasisRow)
    assert row.basis_bps == 10.0
    assert row.spot_price_time_ms == 1000
    assert row.perp_price_time_ms == 1000
    assert row.selected_price_time_ms == 1000
    assert row.price_time_diff_ms == 0
    assert row.basis_source == "spot_close_vs_futures_mark_close"
    assert row.depth_source == "static_min_capacity_proxy"
    assert row.coverage_quality == "historical_basis_proxy_not_depth_aware"
```

### Step 2: Verify failing test

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/test_extreme_funding_basis_replay.py -q
```

Expected:

```text
FAIL ModuleNotFoundError
```

### Step 3: Implement row contract

Create `src/research/extreme_funding_basis_replay.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass

from configs.base import (
    EXTREME_FUNDING_BASIS_REPLAY_STATIC_DEPTH_MULTIPLIER,
    EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS,
    RISK_MAX_SINGLE_POSITION_USDT,
)


@dataclass(frozen=True)
class HistoricalBasisRow:
    symbol: str
    funding_time_ms: int
    funding_rate: float
    annualized_pct: float
    spot_mid_price: float
    perp_mid_price: float
    spot_price_time_ms: int
    perp_price_time_ms: int
    selected_price_time_ms: int
    price_time_diff_ms: int
    basis_bps: float
    basis_source: str
    depth_capacity_usdt: float
    depth_source: str
    coverage_quality: str

    def to_candidate_row(self) -> dict:
        row = asdict(self)
        row.update(
            {
                "timestamp_ms": self.funding_time_ms,
                "source_type": "historical_settled",
                "exchange": "binance",
                "direction": "neutral",
                "watch_level": "historical_settled_extreme",
                "annualized_funding_estimate_pct": self.annualized_pct,
                "funding_rate_per_interval": self.funding_rate,
                "expected_holding_intervals": EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS,
                "settlement_persistence": 1.0,
                "planned_notional_usdt": RISK_MAX_SINGLE_POSITION_USDT,
            }
        )
        return row


def basis_bps_from_prices(*, spot_mid_price: float, perp_mid_price: float) -> float:
    if spot_mid_price <= 0.0:
        raise ValueError("spot_mid_price must be positive")
    return round((perp_mid_price / spot_mid_price - 1.0) * 10_000.0, 10)


def build_historical_basis_row(
    *,
    symbol: str,
    funding_time_ms: int,
    funding_rate: float,
    annualized_pct: float,
    spot_mid_price: float,
    perp_mid_price: float,
    selected_price_time_ms: int | None = None,
    spot_price_time_ms: int | None = None,
    perp_price_time_ms: int | None = None,
) -> HistoricalBasisRow:
    spot_time = funding_time_ms if spot_price_time_ms is None else spot_price_time_ms
    perp_time = funding_time_ms if perp_price_time_ms is None else perp_price_time_ms
    selected_time = (
        max(spot_time, perp_time)
        if selected_price_time_ms is None
        else selected_price_time_ms
    )
    return HistoricalBasisRow(
        symbol=symbol,
        funding_time_ms=funding_time_ms,
        funding_rate=funding_rate,
        annualized_pct=annualized_pct,
        spot_mid_price=spot_mid_price,
        perp_mid_price=perp_mid_price,
        spot_price_time_ms=spot_time,
        perp_price_time_ms=perp_time,
        selected_price_time_ms=selected_time,
        price_time_diff_ms=abs(spot_time - perp_time),
        basis_bps=basis_bps_from_prices(
            spot_mid_price=spot_mid_price,
            perp_mid_price=perp_mid_price,
        ),
        basis_source="spot_close_vs_futures_mark_close",
        depth_capacity_usdt=(
            RISK_MAX_SINGLE_POSITION_USDT
            * EXTREME_FUNDING_BASIS_REPLAY_STATIC_DEPTH_MULTIPLIER
        ),
        depth_source="static_min_capacity_proxy",
        coverage_quality="historical_basis_proxy_not_depth_aware",
    )
```

### Step 4: Verify row tests

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/test_extreme_funding_basis_replay.py -q
```

Expected:

```text
PASS
```

---

## Task 4: Add Public Binance Kline Helpers

**Files:**

- Modify: `src/research/extreme_funding_basis_replay.py`
- Modify: `tests/research/test_extreme_funding_basis_replay.py`

### Step 1: Write failing URL/parser tests

Append to `tests/research/test_extreme_funding_basis_replay.py`:

```python
from src.research.extreme_funding_basis_replay import (
    binance_symbol_from_pair,
    build_binance_basis_kline_urls,
    parse_kline_close,
)


def test_binance_symbol_from_pair_removes_separator() -> None:
    assert binance_symbol_from_pair("DOGE/USDT") == "DOGEUSDT"


def test_build_binance_basis_kline_urls_uses_public_endpoints() -> None:
    urls = build_binance_basis_kline_urls(
        binance_symbol="DOGEUSDT",
        start_time_ms=1000,
        end_time_ms=2000,
    )

    assert urls["spot"].startswith("https://api.binance.com/api/v3/klines?")
    assert urls["futures_mark"].startswith(
        "https://fapi.binance.com/fapi/v1/markPriceKlines?"
    )
    assert "symbol=DOGEUSDT" in urls["spot"]
    assert "symbol=DOGEUSDT" in urls["futures_mark"]


def test_parse_kline_close_returns_close_time_and_close_price() -> None:
    close_time_ms, close_price = parse_kline_close([1000, "1", "2", "0.5", "1.5", "10", 1999])

    assert close_time_ms == 1999
    assert close_price == 1.5
```

### Step 2: Implement public helpers

Append to `src/research/extreme_funding_basis_replay.py`:

```python
from urllib.parse import urlencode

from configs.base import EXTREME_FUNDING_BASIS_REPLAY_INTERVAL


def binance_symbol_from_pair(pair: str) -> str:
    return pair.replace("/", "")


def build_binance_basis_kline_urls(
    *,
    binance_symbol: str,
    start_time_ms: int,
    end_time_ms: int,
) -> dict[str, str]:
    params = {
        "symbol": binance_symbol,
        "interval": EXTREME_FUNDING_BASIS_REPLAY_INTERVAL,
        "startTime": str(start_time_ms),
        "endTime": str(end_time_ms),
        "limit": "1000",
    }
    query = urlencode(params)
    return {
        "spot": f"https://api.binance.com/api/v3/klines?{query}",
        "futures_mark": f"https://fapi.binance.com/fapi/v1/markPriceKlines?{query}",
    }


def parse_kline_close(kline: list) -> tuple[int, float]:
    return int(kline[6]), float(kline[4])
```

### Step 3: Verify helper tests

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/test_extreme_funding_basis_replay.py -q
```

Expected:

```text
PASS
```

---

## Task 5: Add Funding Row Selection And Basis Joiner

**Files:**

- Modify: `src/research/extreme_funding_basis_replay.py`
- Modify: `tests/research/test_extreme_funding_basis_replay.py`

### Step 1: Write failing selection and join tests

Append to `tests/research/test_extreme_funding_basis_replay.py`:

```python
from src.research.extreme_funding_basis_replay import (
    join_funding_rows_with_basis_prices,
    select_basis_replay_funding_rows,
)


def test_select_basis_replay_funding_rows_keeps_extreme_and_following_path_rows() -> None:
    rows = [
        {"symbol": "DOGE/USDT", "funding_time_ms": 1, "funding_rate": 0.001, "annualized_pct": 10.0},
        {"symbol": "DOGE/USDT", "funding_time_ms": 2, "funding_rate": 0.010, "annualized_pct": 1095.0},
        {"symbol": "DOGE/USDT", "funding_time_ms": 3, "funding_rate": 0.004, "annualized_pct": 438.0},
        {"symbol": "DOGE/USDT", "funding_time_ms": 4, "funding_rate": 0.0001, "annualized_pct": 10.95},
    ]

    selected = select_basis_replay_funding_rows(
        rows,
        threshold_pct=100.0,
        max_following_intervals=2,
    )

    assert [row["funding_time_ms"] for row in selected] == [2, 3, 4]


def test_select_basis_replay_funding_rows_does_not_cross_symbols() -> None:
    rows = [
        {"symbol": "DOGE/USDT", "funding_time_ms": 1, "funding_rate": 0.002, "annualized_pct": 200.0},
        {"symbol": "XRP/USDT", "funding_time_ms": 2, "funding_rate": 0.0001, "annualized_pct": 10.0},
        {"symbol": "DOGE/USDT", "funding_time_ms": 3, "funding_rate": 0.0005, "annualized_pct": 50.0},
    ]

    selected = select_basis_replay_funding_rows(
        rows,
        threshold_pct=100.0,
        max_following_intervals=1,
    )

    assert [row["symbol"] for row in selected] == ["DOGE/USDT", "DOGE/USDT"]
    assert [row["funding_time_ms"] for row in selected] == [1, 3]


def test_join_funding_rows_with_basis_prices_builds_rows_within_tolerance() -> None:
    funding_rows = [
        {
            "symbol": "DOGE/USDT",
            "funding_time_ms": 10_000,
            "funding_rate": 0.008,
            "annualized_pct": 650.0,
        }
    ]

    result = join_funding_rows_with_basis_prices(
        funding_rows,
        spot_prices={10_000: 100.0},
        perp_prices={10_000: 101.0},
        tolerance_ms=120_000,
    )

    assert result["status"] == "ok"
    assert len(result["rows"]) == 1
    assert result["rows"][0].basis_bps == 100.0
    assert result["missing_basis_count"] == 0


def test_join_funding_rows_with_basis_prices_marks_missing_when_prices_absent() -> None:
    funding_rows = [
        {
            "symbol": "DOGE/USDT",
            "funding_time_ms": 10_000,
            "funding_rate": 0.008,
            "annualized_pct": 650.0,
        }
    ]

    result = join_funding_rows_with_basis_prices(
        funding_rows,
        spot_prices={},
        perp_prices={},
        tolerance_ms=120_000,
    )

    assert result["status"] == "insufficient_basis_data"
    assert result["rows"] == []
    assert result["missing_basis_count"] == 1


def test_join_uses_latest_price_at_or_before_funding_time_not_future_price() -> None:
    funding_rows = [
        {
            "symbol": "DOGE/USDT",
            "funding_time_ms": 10_000,
            "funding_rate": 0.008,
            "annualized_pct": 650.0,
        }
    ]

    result = join_funding_rows_with_basis_prices(
        funding_rows,
        spot_prices={9_999: 100.0, 10_001: 200.0},
        perp_prices={9_999: 101.0, 10_001: 202.0},
        tolerance_ms=120_000,
    )

    assert result["rows"][0].spot_mid_price == 100.0
    assert result["rows"][0].perp_mid_price == 101.0
```

### Step 2: Implement selection and joiner

Append to `src/research/extreme_funding_basis_replay.py`:

```python
from typing import Any
from collections import defaultdict


def select_basis_replay_funding_rows(
    funding_rows: list[dict[str, Any]],
    *,
    threshold_pct: float,
    max_following_intervals: int,
) -> list[dict[str, Any]]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in funding_rows:
        by_symbol[str(row["symbol"])].append(row)

    selected: list[dict[str, Any]] = []
    for symbol_rows in by_symbol.values():
        selected_indexes: set[int] = set()
        sorted_rows = sorted(symbol_rows, key=lambda row: int(row["funding_time_ms"]))
        for index, row in enumerate(sorted_rows):
            if float(row.get("annualized_pct", 0.0)) < threshold_pct:
                continue
            for offset in range(max_following_intervals + 1):
                path_index = index + offset
                if path_index < len(sorted_rows):
                    selected_indexes.add(path_index)
        selected.extend(sorted_rows[index] for index in sorted(selected_indexes))
    return sorted(selected, key=lambda row: (str(row["symbol"]), int(row["funding_time_ms"])))


def _latest_price_at_or_before(
    prices: dict[int, float],
    *,
    target_time_ms: int,
    tolerance_ms: int,
) -> tuple[int, float] | None:
    if not prices:
        return None
    candidates = [timestamp for timestamp in prices if timestamp <= target_time_ms]
    if not candidates:
        return None
    selected_time = max(candidates)
    if target_time_ms - selected_time > tolerance_ms:
        return None
    return selected_time, prices[selected_time]


def join_funding_rows_with_basis_prices(
    funding_rows: list[dict[str, Any]],
    *,
    spot_prices: dict[int, float],
    perp_prices: dict[int, float],
    tolerance_ms: int,
) -> dict[str, Any]:
    rows: list[HistoricalBasisRow] = []
    missing_basis_count = 0
    for funding in funding_rows:
        funding_time_ms = int(funding["funding_time_ms"])
        spot = _latest_price_at_or_before(
            spot_prices,
            target_time_ms=funding_time_ms,
            tolerance_ms=tolerance_ms,
        )
        perp = _latest_price_at_or_before(
            perp_prices,
            target_time_ms=funding_time_ms,
            tolerance_ms=tolerance_ms,
        )
        if spot is None or perp is None:
            missing_basis_count += 1
            continue
        rows.append(
            build_historical_basis_row(
                symbol=str(funding["symbol"]),
                funding_time_ms=funding_time_ms,
                funding_rate=float(funding["funding_rate"]),
                annualized_pct=float(funding["annualized_pct"]),
                spot_mid_price=spot[1],
                perp_mid_price=perp[1],
                spot_price_time_ms=spot[0],
                perp_price_time_ms=perp[0],
            )
        )
    return {
        "status": "ok" if rows else "insufficient_basis_data",
        "rows": rows,
        "missing_basis_count": missing_basis_count,
        "coverage_quality": (
            "historical_basis_proxy_not_depth_aware"
            if rows
            else "insufficient_basis_data"
        ),
    }
```

### Step 3: Verify selection and joiner tests

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/test_extreme_funding_basis_replay.py -q
```

Expected:

```text
PASS
```

---

## Task 6: Add Targeted Basis Dataset Builder

**Files:**

- Create: `scripts/build_extreme_funding_basis_replay_dataset.py`
- Create: `tests/scripts/test_build_extreme_funding_basis_replay_dataset.py`

### Step 1: Write failing dataset summary tests

Create `tests/scripts/test_build_extreme_funding_basis_replay_dataset.py`:

```python
from scripts.build_extreme_funding_basis_replay_dataset import (
    build_dataset_summary,
    parse_price_payload,
)
from src.research.extreme_funding_basis_replay import build_historical_basis_row


def test_parse_price_payload_turns_klines_into_close_time_price_map() -> None:
    payload = [[0, "1", "2", "0.5", "1.5", "10", 999]]

    assert parse_price_payload(payload) == {999: 1.5}


def test_parse_price_payload_reports_row_errors() -> None:
    prices, row_error_count = parse_price_payload([[0, "bad"]])

    assert prices == {}
    assert row_error_count == 1


def test_build_dataset_summary_marks_empty_input() -> None:
    summary = build_dataset_summary([], stats={"selected_funding_row_count": 0})

    assert summary["status"] == "no_threshold_rows_or_no_input"
    assert summary["basis_row_count"] == 0
    assert summary["coverage_quality"] == "insufficient_basis_data"
    assert summary["selected_funding_row_count"] == 0
    assert summary["has_basis_rows"] is False


def test_build_dataset_summary_marks_basis_proxy_rows() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=100.0,
            perp_mid_price=100.10,
            selected_price_time_ms=1000,
        )
    ]

    summary = build_dataset_summary(
        rows,
        stats={
            "selected_funding_row_count": 1,
            "request_count": 2,
            "fetch_error_count": 0,
            "spot_empty_count": 0,
            "futures_empty_count": 0,
            "alignment_miss_count": 0,
            "parse_error_count": 0,
            "row_error_count": 0,
            "symbols": ["DOGE/USDT"],
        },
    )

    assert summary["status"] == "ok"
    assert summary["basis_row_count"] == 1
    assert summary["coverage_quality"] == "historical_basis_proxy_not_depth_aware"
    assert summary["depth_aware"] is False
    assert summary["depth_source"] == "static_min_capacity_proxy"
    assert summary["max_price_time_diff_ms"] == 0
```

### Step 2: Implement dataset builder with injectable fetcher

Create `scripts/build_extreme_funding_basis_replay_dataset.py`:

```python
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from configs.base import (
    EXTREME_FUNDING_BASIS_REPLAY_ALIGNMENT_TOLERANCE_MS,
    EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC,
    EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR,
    EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC,
    EXTREME_FUNDING_BASIS_REPLAY_REQUEST_WINDOW_MS,
    EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
    EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
)
from src.research.extreme_funding_basis_replay import (
    HistoricalBasisRow,
    binance_symbol_from_pair,
    build_binance_basis_kline_urls,
    join_funding_rows_with_basis_prices,
    parse_kline_close,
    select_basis_replay_funding_rows,
)


Fetcher = Callable[[str, float], Any]


def fetch_json_url(url: str, timeout_sec: float) -> Any:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(url, timeout=timeout_sec) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep((attempt + 1) * 2.0)
    raise RuntimeError(f"fetch_json_url failed after retries: {last_error}") from last_error


def parse_price_payload(payload: list) -> tuple[dict[int, float], int]:
    prices: dict[int, float] = {}
    row_error_count = 0
    for kline in payload:
        try:
            close_time_ms, close_price = parse_kline_close(kline)
        except (IndexError, TypeError, ValueError):
            row_error_count += 1
            continue
        prices[close_time_ms] = close_price
    return prices, row_error_count


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_dataset_summary(
    rows: list[HistoricalBasisRow],
    *,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stats = stats or {}
    selected_count = int(stats.get("selected_funding_row_count", 0))
    if rows:
        status = "ok"
    elif selected_count == 0:
        status = "no_threshold_rows_or_no_input"
    else:
        status = "insufficient_basis_data"
    return {
        "status": status,
        "basis_row_count": len(rows),
        "has_basis_rows": bool(rows),
        "coverage_quality": (
            "historical_basis_proxy_not_depth_aware"
            if rows
            else "insufficient_basis_data"
        ),
        "depth_aware": False,
        "depth_source": "static_min_capacity_proxy" if rows else None,
        "max_price_time_diff_ms": (
            max(row.price_time_diff_ms for row in rows) if rows else None
        ),
        "selected_funding_row_count": selected_count,
        "missing_basis_count": int(stats.get("missing_basis_count", 0)),
        "spot_empty_count": int(stats.get("spot_empty_count", 0)),
        "futures_empty_count": int(stats.get("futures_empty_count", 0)),
        "fetch_error_count": int(stats.get("fetch_error_count", 0)),
        "parse_error_count": int(stats.get("parse_error_count", 0)),
        "row_error_count": int(stats.get("row_error_count", 0)),
        "alignment_miss_count": int(stats.get("alignment_miss_count", 0)),
        "request_count": int(stats.get("request_count", 0)),
        "symbols": list(stats.get("symbols", [])),
    }


def build_basis_rows_for_symbol(
    *,
    symbol: str,
    funding_rows: list[dict[str, Any]],
    fetcher: Fetcher = fetch_json_url,
) -> dict[str, Any]:
    selected_rows = select_basis_replay_funding_rows(
        funding_rows,
        threshold_pct=EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
        max_following_intervals=EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
    )
    rows: list[HistoricalBasisRow] = []
    stats: dict[str, Any] = {
        "selected_funding_row_count": len(selected_rows),
        "missing_basis_count": 0,
        "spot_empty_count": 0,
        "futures_empty_count": 0,
        "fetch_error_count": 0,
        "parse_error_count": 0,
        "row_error_count": 0,
        "alignment_miss_count": 0,
        "request_count": 0,
        "symbols": [symbol],
    }
    binance_symbol = binance_symbol_from_pair(symbol)
    for funding in selected_rows:
        funding_time_ms = int(funding["funding_time_ms"])
        half_window_ms = EXTREME_FUNDING_BASIS_REPLAY_REQUEST_WINDOW_MS // 2
        urls = build_binance_basis_kline_urls(
            binance_symbol=binance_symbol,
            start_time_ms=funding_time_ms - half_window_ms,
            end_time_ms=funding_time_ms + half_window_ms,
        )
        try:
            spot_payload = fetcher(urls["spot"], EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC)
            stats["request_count"] += 1
            time.sleep(EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC)
            perp_payload = fetcher(
                urls["futures_mark"],
                EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC,
            )
            stats["request_count"] += 1
            time.sleep(EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC)
        except Exception:
            stats["fetch_error_count"] += 1
            continue
        if not spot_payload:
            stats["spot_empty_count"] += 1
        if not perp_payload:
            stats["futures_empty_count"] += 1
        try:
            spot_prices, spot_row_errors = parse_price_payload(spot_payload)
            perp_prices, perp_row_errors = parse_price_payload(perp_payload)
        except Exception:
            stats["parse_error_count"] += 1
            continue
        stats["row_error_count"] += spot_row_errors + perp_row_errors
        joined = join_funding_rows_with_basis_prices(
            [funding],
            spot_prices=spot_prices,
            perp_prices=perp_prices,
            tolerance_ms=EXTREME_FUNDING_BASIS_REPLAY_ALIGNMENT_TOLERANCE_MS,
        )
        stats["missing_basis_count"] += int(joined["missing_basis_count"])
        if joined["missing_basis_count"]:
            stats["alignment_miss_count"] += 1
        rows.extend(joined["rows"])
    return {"rows": rows, "stats": stats}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build historical basis-aware replay rows.")
    parser.add_argument("--symbol", required=True, help="Pair format, for example DOGE/USDT")
    parser.add_argument("--funding-file", required=True)
    parser.add_argument(
        "--output",
        default=f"{EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR}/2026-05-25_basis_rows.jsonl",
    )
    parser.add_argument(
        "--summary-output",
        default=f"{EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR}/2026-05-25_basis_dataset_summary.json",
    )
    args = parser.parse_args()

    funding_rows = load_jsonl(Path(args.funding_file))
    dataset = build_basis_rows_for_symbol(symbol=args.symbol, funding_rows=funding_rows)
    rows = dataset["rows"]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row.__dict__, sort_keys=True) for row in rows),
        encoding="utf-8",
    )

    summary = build_dataset_summary(rows, stats=dataset["stats"])
    summary_output = Path(args.summary_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
```

### Step 3: Verify dataset builder tests

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_build_extreme_funding_basis_replay_dataset.py -q
```

Expected:

```text
PASS
```

---

## Task 7: Add Basis-Aware Candidate Replay

**Files:**

- Create: `scripts/replay_extreme_funding_basis_aware_candidates.py`
- Create: `tests/scripts/test_replay_extreme_funding_basis_aware_candidates.py`

### Step 1: Write failing candidate summary tests

Create `tests/scripts/test_replay_extreme_funding_basis_aware_candidates.py`:

```python
import json

from scripts.replay_extreme_funding_basis_aware_candidates import (
    build_basis_aware_candidate_summary,
    load_basis_rows_jsonl,
)
from src.research.extreme_funding_basis_replay import build_historical_basis_row


def test_basis_aware_candidate_summary_accepts_low_absorption_row() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=100.0,
            perp_mid_price=100.10,
            selected_price_time_ms=1000,
        )
    ]

    summary = build_basis_aware_candidate_summary(rows)

    assert summary["input_row_count"] == 1
    assert summary["candidate_count"] == 1
    assert summary["coverage_quality"] == "historical_basis_proxy_not_depth_aware"
    assert summary["depth_aware"] is False
    assert summary["depth_source"] == "static_min_capacity_proxy"
    assert summary["reject_reason_counts"] == {}


def test_basis_aware_candidate_summary_rejects_absorbed_basis() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=100.0,
            perp_mid_price=105.0,
            selected_price_time_ms=1000,
        )
    ]

    summary = build_basis_aware_candidate_summary(rows)

    assert summary["candidate_count"] == 0
    assert summary["reject_reason_counts"]["basis_absorbed"] == 1


def test_load_basis_rows_jsonl_round_trips_row(tmp_path) -> None:
    row = build_historical_basis_row(
        symbol="DOGE/USDT",
        funding_time_ms=1000,
        funding_rate=0.008,
        annualized_pct=650.0,
        spot_mid_price=100.0,
        perp_mid_price=100.10,
        selected_price_time_ms=1000,
    )
    path = tmp_path / "basis_rows.jsonl"
    path.write_text(json.dumps(row.__dict__, sort_keys=True) + "\n", encoding="utf-8")

    loaded = load_basis_rows_jsonl(path)

    assert loaded[0].basis_bps == row.basis_bps
```

### Step 2: Implement candidate replay script

Create `scripts/replay_extreme_funding_basis_aware_candidates.py`:

```python
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.research.extreme_funding_basis_replay import HistoricalBasisRow
from src.strategies.extreme_funding.candidate_builder import build_extreme_funding_candidate


def load_basis_rows_jsonl(path: str | Path) -> list[HistoricalBasisRow]:
    rows: list[HistoricalBasisRow] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(HistoricalBasisRow(**json.loads(line)))
    return rows


def build_basis_aware_candidate_summary(rows: list[HistoricalBasisRow]) -> dict:
    reject_counts: Counter[str] = Counter()
    candidate_count = 0
    for row in rows:
        decision = build_extreme_funding_candidate(row.to_candidate_row())
        if decision.accepted:
            candidate_count += 1
        else:
            reject_counts[decision.reject_reason or "unknown_reject"] += 1
    return {
        "input_row_count": len(rows),
        "candidate_count": candidate_count,
        "reject_reason_counts": dict(sorted(reject_counts.items())),
        "coverage_quality": (
            "historical_basis_proxy_not_depth_aware"
            if rows
            else "insufficient_basis_data"
        ),
        "depth_aware": False,
        "depth_source": "static_min_capacity_proxy" if rows else None,
        "status": "ok" if rows else "insufficient_basis_data",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay basis-aware extreme funding candidates.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = load_basis_rows_jsonl(args.input)
    summary = build_basis_aware_candidate_summary(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
```

### Step 3: Verify candidate replay tests

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_replay_extreme_funding_basis_aware_candidates.py -q
```

Expected:

```text
PASS
```

---

## Task 8: Add Basis-Aware Shadow Replay

**Files:**

- Create: `scripts/simulate_extreme_funding_basis_aware_shadow.py`
- Create: `tests/scripts/test_simulate_extreme_funding_basis_aware_shadow.py`

### Step 1: Write failing shadow summary tests

Create `tests/scripts/test_simulate_extreme_funding_basis_aware_shadow.py`:

```python
from scripts.simulate_extreme_funding_basis_aware_shadow import (
    build_basis_aware_shadow_summary,
)
from src.research.extreme_funding_basis_replay import build_historical_basis_row


def test_basis_aware_shadow_summary_outputs_net_pnl_when_basis_path_exists() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=100.0,
            perp_mid_price=100.10,
            selected_price_time_ms=1000,
        ),
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=2000,
            funding_rate=0.007,
            annualized_pct=600.0,
            spot_mid_price=100.0,
            perp_mid_price=100.05,
            selected_price_time_ms=2000,
        ),
    ]

    summary = build_basis_aware_shadow_summary(rows)

    assert summary["shadow_trade_count"] == 1
    assert summary["coverage_quality"] == "historical_basis_proxy_not_depth_aware"
    assert "median_net_pnl_bps" in summary
    assert "win_rate" in summary


def test_basis_aware_shadow_summary_does_not_cross_symbols() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=100.0,
            perp_mid_price=100.10,
            selected_price_time_ms=1000,
        ),
        build_historical_basis_row(
            symbol="XRP/USDT",
            funding_time_ms=1500,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=1.0,
            perp_mid_price=1.2,
            selected_price_time_ms=1500,
        ),
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=2000,
            funding_rate=0.007,
            annualized_pct=600.0,
            spot_mid_price=100.0,
            perp_mid_price=100.05,
            selected_price_time_ms=2000,
        ),
    ]

    summary = build_basis_aware_shadow_summary(rows)

    assert summary["shadow_trade_count"] == 1
    assert summary["symbols"] == ["DOGE/USDT"]


def test_basis_aware_shadow_summary_marks_empty_basis_path() -> None:
    summary = build_basis_aware_shadow_summary([])

    assert summary["shadow_trade_count"] == 0
    assert summary["status"] == "insufficient_basis_path"
```

### Step 2: Implement shadow replay script

Create `scripts/simulate_extreme_funding_basis_aware_shadow.py`:

```python
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from configs.base import (
    EXTREME_FUNDING_FEE_BPS,
    EXTREME_FUNDING_ROLLBACK_RESERVE_BPS,
    EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
    EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS,
    RISK_MAX_SINGLE_POSITION_USDT,
)
from src.research.extreme_funding_basis_replay import HistoricalBasisRow
from scripts.replay_extreme_funding_basis_aware_candidates import load_basis_rows_jsonl
from src.strategies.extreme_funding.shadow_simulator import (
    ExtremeFundingShadowPosition,
    simulate_extreme_funding_shadow,
)


def build_basis_aware_shadow_summary(rows: list[HistoricalBasisRow]) -> dict:
    if len(rows) < 2:
        return {
            "shadow_trade_count": 0,
            "coverage_quality": "insufficient_basis_data",
            "status": "insufficient_basis_path",
        }

    total_cost_bps = (
        EXTREME_FUNDING_FEE_BPS
        + EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS
        + EXTREME_FUNDING_ROLLBACK_RESERVE_BPS
    )
    pnl_values: list[float] = []
    exit_counts: dict[str, int] = {}
    symbols_seen: set[str] = set()
    rows_by_symbol: dict[str, list[HistoricalBasisRow]] = defaultdict(list)
    for row in rows:
        rows_by_symbol[row.symbol].append(row)

    for symbol, symbol_rows in rows_by_symbol.items():
        sorted_rows = sorted(symbol_rows, key=lambda row: row.funding_time_ms)
        for index, first in enumerate(sorted_rows[:-1]):
            path_rows = sorted_rows[
                index + 1 : index + 1 + EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS
            ]
            if not path_rows:
                continue
            symbols_seen.add(symbol)
            position = ExtremeFundingShadowPosition(
                symbol=first.symbol,
                side="long_spot_short_perp",
                entry_time_ms=first.funding_time_ms,
                entry_basis_bps=first.basis_bps,
                estimated_total_cost_bps=total_cost_bps,
                notional_usdt=RISK_MAX_SINGLE_POSITION_USDT,
                max_holding_intervals=EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
                coverage_quality="historical_basis_proxy_not_depth_aware",
            )
            result = simulate_extreme_funding_shadow(
                position,
                [
                    {
                        "funding_time_ms": row.funding_time_ms,
                        "funding_rate": row.funding_rate,
                        "basis_bps": row.basis_bps,
                        "annualized_pct": row.annualized_pct,
                    }
                    for row in path_rows
                ],
            )
            pnl_values.append(result.net_pnl_bps)
            exit_counts[result.exit_reason] = exit_counts.get(result.exit_reason, 0) + 1

    return {
        "shadow_trade_count": len(pnl_values),
        "median_net_pnl_bps": median(pnl_values) if pnl_values else 0.0,
        "mean_net_pnl_bps": mean(pnl_values) if pnl_values else 0.0,
        "win_rate": (
            sum(1 for value in pnl_values if value > 0.0) / len(pnl_values)
            if pnl_values
            else 0.0
        ),
        "exit_reason_counts": dict(sorted(exit_counts.items())),
        "coverage_quality": "historical_basis_proxy_not_depth_aware",
        "depth_aware": False,
        "depth_source": "static_min_capacity_proxy" if rows else None,
        "symbols": sorted(symbols_seen),
        "status": "ok" if pnl_values else "insufficient_basis_path",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate basis-aware extreme funding shadow replay.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = load_basis_rows_jsonl(args.input)
    summary = build_basis_aware_shadow_summary(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
```

### Step 3: Verify shadow replay tests

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_simulate_extreme_funding_basis_aware_shadow.py -q
```

Expected:

```text
PASS
```

---

## Task 9: Run Historical Basis-Aware Replay For Priority Symbols

**Files:**

- Generate: `reports/extreme_funding/2026-05-25_*basis*.json`
- Generate: `reports/extreme_funding/2026-05-25_*basis*.jsonl`

### Step 1: Build basis rows for DOGE and XRP first

Run:

```bash
PYTHONPATH=src uv run python scripts/build_extreme_funding_basis_replay_dataset.py \
  --symbol DOGE/USDT \
  --funding-file data/funding_settled/binance_DOGEUSDT_settled.jsonl \
  --output reports/extreme_funding/2026-05-25_basis_rows_DOGEUSDT.jsonl \
  --summary-output reports/extreme_funding/2026-05-25_basis_dataset_DOGEUSDT_summary.json

PYTHONPATH=src uv run python scripts/build_extreme_funding_basis_replay_dataset.py \
  --symbol XRP/USDT \
  --funding-file data/funding_settled/binance_XRPUSDT_settled.jsonl \
  --output reports/extreme_funding/2026-05-25_basis_rows_XRPUSDT.jsonl \
  --summary-output reports/extreme_funding/2026-05-25_basis_dataset_XRPUSDT_summary.json
```

Expected:

- If public API returns historical klines: `basis_row_count > 0`。
- If Binance rejects old kline ranges or local network fails: `status="insufficient_basis_data"` with explicit `fetch_error_count` / `spot_empty_count` / `futures_empty_count` / `alignment_miss_count` before final review。

### Step 2: Run candidate and shadow replay only when basis rows exist

Run for each symbol whose dataset summary has `basis_row_count > 0`:

```bash
PYTHONPATH=src uv run python scripts/replay_extreme_funding_basis_aware_candidates.py \
  --input reports/extreme_funding/2026-05-25_basis_rows_DOGEUSDT.jsonl \
  --output reports/extreme_funding/2026-05-25_basis_aware_candidate_DOGEUSDT_summary.json

PYTHONPATH=src uv run python scripts/simulate_extreme_funding_basis_aware_shadow.py \
  --input reports/extreme_funding/2026-05-25_basis_rows_DOGEUSDT.jsonl \
  --output reports/extreme_funding/2026-05-25_basis_aware_shadow_DOGEUSDT_summary.json
```

Expected:

- If `basis_row_count == 0`, do not force candidate/shadow conclusions。
- If `basis_row_count > 0`, candidate/shadow JSON must include `depth_aware=false` and `depth_source="static_min_capacity_proxy"`。

### Step 3: Extend to ADA / ETH / BTC only after DOGE/XRP works

Run the same command for:

- `ADA/USDT`
- `ETH/USDT`
- `BTC/USDT`

Expected:

- Do not expand symbol coverage before DOGE/XRP path is verified。

---

## Task 10: Add Final Review Artifact

**Files:**

- Create: `docs/reviews/2026-05-25-extreme-funding-historical-basis-aware-replay-review.md`
- Read: `reports/extreme_funding/2026-05-25_*basis*.json`
- Read: `reports/extreme_funding/2026-05-25_*basis*.jsonl`

### Step 1: Write review

Create `docs/reviews/2026-05-25-extreme-funding-historical-basis-aware-replay-review.md`:

```markdown
# Extreme Funding Historical Basis-Aware Replay 阶段性结论

## 1. 核心结论

本轮不是 live approval。

本轮只回答：

- settled funding 高发窗口里，入场基差是否已经吸收 funding 收益；
- basis path 是否导致 shadow PnL 从 funding-only 结论明显恶化；
- Extreme Funding 是否值得进入更细的 orderbook-aware replay。

## 2. 数据覆盖

- coverage_quality:
- symbols:
- basis_row_count:
- selected_funding_row_count:
- missing_basis_count:
- spot_empty_count:
- futures_empty_count:
- fetch_error_count:
- parse_error_count:
- row_error_count:
- alignment_miss_count:
- max_price_time_diff_ms:
- depth_source:
- depth_aware:

## 3. Candidate Replay

插入真实 `basis-aware candidate summary` JSON；禁止保留模板文字。

重点解释：

- candidate_count
- reject_reason_counts
- basis_absorbed 占比
- net_edge_below_min 占比
- depth_aware=false 的含义：本轮不是 orderbook-aware replay

## 4. Shadow Replay

插入真实 `basis-aware shadow summary` JSON；禁止保留模板文字。

重点解释：

- median_net_pnl_bps
- mean_net_pnl_bps
- win_rate
- exit_reason_counts

## 5. 决策

如果 `basis_row_count == 0`：

> 数据不足，不能判断策略有效或无效；下一步必须先修 historical basis data acquisition。

如果 `candidate_count == 0` 且 `basis_absorbed` 主导：

> 历史极端 funding 大多已被 basis 吸收，Extreme Funding 不进入 shadow/live，保留为 watchlist。

如果 `candidate_count > 0` 且 `median_net_pnl_bps > 20`：

> 进入 orderbook-aware replay，不进入 live。
```

### Step 2: Check no unresolved tokens

Run:

```bash
rg -n "粘贴|T[O]DO|T[B]D|PLAN_NEEDS_VALUE|UNRESOLVED" docs/reviews/2026-05-25-extreme-funding-historical-basis-aware-replay-review.md
```

Expected:

```text
(no output)
```

---

## Task 11: Full Verification

### Step 1: Run focused tests

Run:

```bash
PYTHONPATH=src uv run pytest \
  tests/test_extreme_funding_config.py \
  tests/research/test_extreme_funding_basis_replay.py \
  tests/scripts/test_build_extreme_funding_basis_replay_dataset.py \
  tests/scripts/test_replay_extreme_funding_basis_aware_candidates.py \
  tests/scripts/test_simulate_extreme_funding_basis_aware_shadow.py \
  -q
```

Expected:

```text
PASS
```

### Step 2: Run full verification

Run:

```bash
make test
make smoke
```

Expected:

```text
PASS
configs OK
risk gate OK
```

### Step 3: Safety grep

Run:

```bash
rg -n "src\\.execution|TradeIntent|apiKey|secret|private|balance" \
  src/research scripts/*basis* tests/research tests/scripts || true
```

Expected:

- No new private/execution dependency in basis replay modules。

---

## Recommended Execution Batches

执行时不要一次性跑完。按 3 个 batch 收口：

### Batch 1: Pure Functions And Data Contract

范围：

- Task 1
- Task 2
- Task 3
- Task 4
- Task 5

通过标准：

- `PYTHONPATH=src uv run pytest tests/research/test_extreme_funding_basis_replay.py -q` PASS。
- 不使用未来 close。
- funding selection 不跨 symbol。
- `basis_bps` 只由 `perp_mid_price / spot_mid_price - 1` 计算。

限制：

- 本 batch 不打 Binance API。

### Batch 2: Small-Scope Real Data Build

范围：

- Task 6
- Task 9 Step 1: DOGE + XRP only

判断规则：

- `basis_row_count > 0`: 继续 candidate / shadow replay。
- `basis_row_count == 0`: 停止扩展 ADA / ETH / BTC，先查看 `fetch_error_count`、`spot_empty_count`、`futures_empty_count`、`parse_error_count`、`row_error_count`、`alignment_miss_count`。

限制：

- DOGE / XRP 没跑通前，不扩大 symbol 覆盖。

### Batch 3: Replay And Review

范围：

- Task 7
- Task 8
- Task 10
- Task 11

通过标准：

- candidate summary 有 `candidate_count`、`reject_reason_counts`、`depth_aware=false`。
- shadow summary 有 `median_net_pnl_bps`、`win_rate`、`exit_reason_counts`、`depth_aware=false`。
- review 明确写：本轮不是 live approval，只能决定是否进入 orderbook-aware replay。

---

## Done Definition

本计划完成时必须满足：

- `HistoricalBasisRow` 存在并有测试。
- `basis_bps` 由 spot/perp price 计算，不由 funding rate 反推。
- funding rows 能按 settlement time 与 spot/perp price proxy 对齐，且不使用未来 close。
- funding row selection 与 shadow path 不跨 symbol。
- dataset builder 能定向拉取 Binance public spot/futures mark klines。
- dataset summary 能解释空结果来源：no threshold rows / fetch errors / empty payload / alignment misses。
- basis-aware candidate replay 能输出 candidate / reject reason 分布。
- candidate replay 和 shadow replay 都有 CLI，可读取 basis rows JSONL 并写出 summary JSON。
- basis-aware shadow replay 只在 basis path 存在时输出 `net_pnl_bps` / `win_rate`。
- 无数据时明确输出 `insufficient_basis_data`。
- 所有 basis-aware summary 明确输出 `depth_aware=false`。
- 所有新增配置在 `configs/base.py`。
- 所有测试通过。
- 无 execution/private API dependency。

---

## Execution Handoff

Plan complete and saved to:

`docs/plans/2026-05-25-extreme-funding-historical-basis-aware-replay-plan.md`

Two execution options:

1. **Subagent-Driven:** one fresh subagent per task, review between tasks.
2. **Inline Execution:** execute in this session using `superpowers:executing-plans`, with checkpoints after major tasks.
