# Cross-Sectional Factor Lab Stage A v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Stage A v1 Binance spot momentum backtest: `momentum_30d_skip_1d`, weekly Monday UTC rebalance, top 10 equal-weight, 30/50/80 bps round-trip cost scenarios, and benchmark/concentration reporting.

**Architecture:** Add small, auditable research modules under `src/research/cross_sectional_factor_lab/` for panel loading, factor calculation, portfolio construction, cost/benchmark accounting, and summary decision logic. Add one CLI script to run either deterministic offline fixtures or live Binance public data, outputting only summary JSON and review-ready artifacts. Stage A v1 remains research-only and must not touch strategy execution, live scanner, or risk live switches.

**Tech Stack:** Python 3.11, `pandas`, `numpy`, `ccxt`, `pytest`, `ruff`.

---

## 0. Scope Contract

### Facts

- Stage 0 decision allows only `Binance spot` `price_volume_fast_track`.
- Current implementation base is `feature/factor-lab-stage0`; do not start Stage A v1 from `main` unless Stage 0 has first been merged.
- `usdt_perp`, `funding_veto`, `oi_veto`, `C1 entry block`, `LightGBM`, `on-chain`, `paper shadow`, and live trading are out of scope.
- All thresholds must live in `configs/base.py`.
- All Stage A v1 results must include `survivorship_bias_not_controlled`.

### Assumptions

- Stage A daily panel uses `pandas`.
- Data rows are UTC daily bars.
- Live mode can use public Binance spot API without API keys.
- Offline fixture mode is required for deterministic tests.
- Stage A v1 continues on `feature/factor-lab-stage0` to keep Stage 0 modules available and avoid another branch unless explicitly requested by the user.

### Completion Gate

The implementation is complete only when:

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_*.py tests/scripts/test_run_factor_lab_stageA_v1_momentum.py
uv run pytest
uv run ruff check configs/base.py src/research/cross_sectional_factor_lab scripts/run_factor_lab_stageA_v1_momentum.py tests/research tests/scripts
```

Expected:

```text
all selected tests pass
full pytest passes
ruff passes
```

---

## Task 1: Add Stage A Config And `pandas`

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `configs/base.py`
- Create: `tests/test_factor_lab_stageA_config.py`

**Step 1: Write failing config tests**

Create `tests/test_factor_lab_stageA_config.py`:

```python
from __future__ import annotations

import configs.base as cfg


def test_factor_lab_stageA_core_config_exists() -> None:
    assert cfg.FACTOR_LAB_STAGEA_HISTORY_DAYS == 540
    assert cfg.FACTOR_LAB_STAGEA_MOMENTUM_LOOKBACK_DAYS == 30
    assert cfg.FACTOR_LAB_STAGEA_SKIP_RECENT_DAYS == 1
    assert cfg.FACTOR_LAB_STAGEA_REBALANCE_WEEKDAY_UTC == 0
    assert cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N == 10
    assert cfg.FACTOR_LAB_STAGEA_DIAGNOSTIC_TOP_N == 5


def test_factor_lab_stageA_cost_config_matches_design() -> None:
    assert cfg.FACTOR_LAB_STAGEA_COST_SCENARIOS_ROUND_TRIP_BPS == (30.0, 50.0, 80.0)
    assert cfg.FACTOR_LAB_STAGEA_OPTIMISTIC_DIAGNOSTIC_PER_LEG_BPS == 10.0


def test_factor_lab_stageA_decision_gates_exist() -> None:
    assert cfg.FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT == 50
    assert cfg.FACTOR_LAB_STAGEA_MAX_DRAWDOWN_VS_EW_MULTIPLIER == 1.25
    assert cfg.FACTOR_LAB_STAGEA_MAX_SINGLE_SYMBOL_PNL_CONTRIBUTION_SHARE == 0.35
    assert cfg.FACTOR_LAB_STAGEA_MAX_SINGLE_MONTH_PNL_CONTRIBUTION_SHARE == 0.30
    assert cfg.FACTOR_LAB_STAGEA_MAX_INSUFFICIENT_UNIVERSE_RATIO == 0.10
```

**Step 2: Run the failing test**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/test_factor_lab_stageA_config.py
```

Expected:

```text
FAIL because FACTOR_LAB_STAGEA_* constants are missing.
```

**Step 3: Add `pandas` dependency**

Run:

```bash
uv add "pandas>=2.2.0"
```

Expected:

```text
pyproject.toml and uv.lock updated.
```

**Step 4: Add constants**

Modify `configs/base.py`, after the Stage 0 section:

```python
# ─── Strategy: Cross-Sectional Factor Lab Stage A v1 ─────────────────────────

FACTOR_LAB_STAGEA_HISTORY_DAYS = 540
# Number of complete UTC daily bars used by Stage A v1.

FACTOR_LAB_STAGEA_MOMENTUM_LOOKBACK_DAYS = 30
# Momentum lookback excluding the skipped recent day.

FACTOR_LAB_STAGEA_SKIP_RECENT_DAYS = 1
# Number of most recent complete daily bars skipped before signal calculation.

FACTOR_LAB_STAGEA_REBALANCE_WEEKDAY_UTC = 0
# Monday in Python weekday convention. Rebalance is Monday 00:00 UTC.

FACTOR_LAB_STAGEA_PRIMARY_TOP_N = 10
# Primary long-only equal-weight portfolio size.

FACTOR_LAB_STAGEA_DIAGNOSTIC_TOP_N = 5
# Diagnostic-only concentrated portfolio size. Not used for primary pass/fail.

FACTOR_LAB_STAGEA_COST_SCENARIOS_ROUND_TRIP_BPS = (30.0, 50.0, 80.0)
# Base/stress/crash round-trip cost scenarios for weekly spot rotation.

FACTOR_LAB_STAGEA_OPTIMISTIC_DIAGNOSTIC_PER_LEG_BPS = 10.0
# Optimistic maker-like per-leg cost, diagnostic only and not part of primary decision.

FACTOR_LAB_STAGEA_MIN_30D_MEDIAN_QUOTE_VOLUME_USDT = FACTOR_LAB_STAGE0_MIN_30D_MEDIAN_QUOTE_VOLUME_USDT
# Point-in-time rolling 30d median quote volume gate for Stage A.

FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT = 50
# Minimum effective weekly rebalance count for a valid 540d backtest.

FACTOR_LAB_STAGEA_MAX_DRAWDOWN_VS_EW_MULTIPLIER = 1.25
# Strategy max drawdown must not exceed equal-weight drawdown by more than this multiplier.

FACTOR_LAB_STAGEA_MAX_SINGLE_SYMBOL_PNL_CONTRIBUTION_SHARE = 0.35
# Maximum allowed share of total PnL contribution from one symbol.

FACTOR_LAB_STAGEA_MAX_SINGLE_MONTH_PNL_CONTRIBUTION_SHARE = 0.30
# Maximum allowed share of total PnL contribution from one calendar month.

FACTOR_LAB_STAGEA_MAX_INSUFFICIENT_UNIVERSE_RATIO = 0.10
# Maximum allowed fraction of rebalance dates with fewer than top-N eligible symbols.
```

**Step 5: Run config tests**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/test_factor_lab_stageA_config.py
```

Expected:

```text
PASS
```

**Step 6: Commit**

```bash
git add pyproject.toml uv.lock configs/base.py tests/test_factor_lab_stageA_config.py
git commit -m "feat(factor-lab): add stage A v1 config"
```

---

## Task 2: Add Deterministic Stage A Fixture

**Files:**
- Create: `tests/fixtures/factor_lab/stageA_v1_sample_panel.json`

**Step 1: Create fixture**

Create `tests/fixtures/factor_lab/stageA_v1_sample_panel.json` with deterministic rows:

```json
{
  "daily_bars": [
    {"symbol": "AAAUSDT", "date_utc": "2026-01-01", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "base_volume": 1000.0, "quote_volume": 25000000.0},
    {"symbol": "AAAUSDT", "date_utc": "2026-01-02", "open": 101.0, "high": 102.0, "low": 100.0, "close": 101.0, "base_volume": 1000.0, "quote_volume": 26000000.0},
    {"symbol": "BBBUSDT", "date_utc": "2026-01-01", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "base_volume": 1000.0, "quote_volume": 25000000.0},
    {"symbol": "BBBUSDT", "date_utc": "2026-01-02", "open": 99.0, "high": 100.0, "low": 98.0, "close": 99.0, "base_volume": 1000.0, "quote_volume": 26000000.0}
  ]
}
```

Then extend the file during later tests with generated synthetic rows inside test code when 31+ days are required. Do not hand-write hundreds of fixture rows.

**Step 2: Commit**

```bash
git add tests/fixtures/factor_lab/stageA_v1_sample_panel.json
git commit -m "test(factor-lab): add stage A sample panel fixture"
```

---

## Task 3: Implement Daily Panel Loading

**Files:**
- Create: `src/research/cross_sectional_factor_lab/panel.py`
- Create: `tests/research/test_cross_sectional_factor_lab_stageA_panel.py`

**Step 1: Write failing tests**

Create tests:

```python
from __future__ import annotations

import pandas as pd
import pytest

from research.cross_sectional_factor_lab.panel import forward_fill_close_by_symbol, load_daily_panel


def test_load_daily_panel_normalizes_schema_and_sorts() -> None:
    rows = [
        {"symbol": "bbb/usdt", "date_utc": "2026-01-02", "open": 2, "high": 3, "low": 1, "close": 2, "base_volume": 1, "quote_volume": 30_000_000},
        {"symbol": "AAA/USDT", "date_utc": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 1, "base_volume": 1, "quote_volume": 25_000_000},
    ]

    panel = load_daily_panel(rows)

    assert list(panel.columns) == [
        "symbol",
        "date_utc",
        "open",
        "high",
        "low",
        "close",
        "base_volume",
        "quote_volume",
    ]
    assert panel.iloc[0]["symbol"] == "AAAUSDT"
    assert panel.iloc[0]["date_utc"] == pd.Timestamp("2026-01-01")


def test_load_daily_panel_rejects_non_positive_close() -> None:
    rows = [{"symbol": "AAAUSDT", "date_utc": "2026-01-01", "open": 1, "high": 1, "low": 1, "close": 0, "base_volume": 1, "quote_volume": 1}]

    with pytest.raises(ValueError, match="close"):
        load_daily_panel(rows)


def test_forward_fill_close_by_symbol_does_not_cross_symbols() -> None:
    panel = pd.DataFrame(
        [
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-01-01"), "close": 100.0},
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-01-02"), "close": None},
            {"symbol": "BBBUSDT", "date_utc": pd.Timestamp("2026-01-01"), "close": 200.0},
            {"symbol": "BBBUSDT", "date_utc": pd.Timestamp("2026-01-02"), "close": None},
        ]
    )

    filled, ffill_count = forward_fill_close_by_symbol(panel)

    assert ffill_count == 2
    assert filled.loc[filled["symbol"] == "AAAUSDT", "close"].iloc[-1] == 100.0
    assert filled.loc[filled["symbol"] == "BBBUSDT", "close"].iloc[-1] == 200.0
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_panel.py
```

Expected:

```text
FAIL because panel.py does not exist.
```

**Step 3: Implement `panel.py`**

```python
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from research.cross_sectional_factor_lab.universe import normalize_symbol

REQUIRED_DAILY_COLUMNS = (
    "symbol",
    "date_utc",
    "open",
    "high",
    "low",
    "close",
    "base_volume",
    "quote_volume",
)


def load_daily_panel(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows))
    missing = [col for col in REQUIRED_DAILY_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"missing daily panel columns: {missing}")

    frame = frame.loc[:, list(REQUIRED_DAILY_COLUMNS)].copy()
    frame["symbol"] = frame["symbol"].map(normalize_symbol)
    frame["date_utc"] = pd.to_datetime(frame["date_utc"], utc=False)

    for col in ("open", "high", "low", "close", "base_volume", "quote_volume"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    if frame[["open", "high", "low", "close"]].isna().any().any():
        raise ValueError("daily panel contains non-numeric OHLC values")
    if (frame["close"] <= 0).any():
        raise ValueError("daily panel contains non-positive close values")

    frame = frame.sort_values(["symbol", "date_utc"]).reset_index(drop=True)
    return frame


def forward_fill_close_by_symbol(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    result = frame.sort_values(["symbol", "date_utc"]).copy()
    before = result["close"].isna().sum()
    result["close"] = result.groupby("symbol")["close"].ffill()
    after = result["close"].isna().sum()
    return result, int(before - after)
```

Do not forward-fill `open` prices. Missing entry or exit `open` must drop the affected period.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_panel.py
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add src/research/cross_sectional_factor_lab/panel.py tests/research/test_cross_sectional_factor_lab_stageA_panel.py
git commit -m "feat(factor-lab): add stage A daily panel loader"
```

---

## Task 4: Implement Momentum And Liquidity Factors

**Files:**
- Create: `src/research/cross_sectional_factor_lab/factors.py`
- Create: `tests/research/test_cross_sectional_factor_lab_stageA_factors.py`

**Step 1: Write failing tests**

Create tests covering off-by-one:

```python
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from research.cross_sectional_factor_lab.factors import (
    compute_momentum_30d_skip_1d,
    compute_rebalance_factor_frame,
)


def _rows(symbol: str, start: date, closes: list[float], quote_volume: float = 25_000_000.0) -> list[dict]:
    return [
        {
            "symbol": symbol,
            "date_utc": start + timedelta(days=i),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "base_volume": 1.0,
            "quote_volume": quote_volume,
        }
        for i, close in enumerate(closes)
    ]


def test_momentum_30d_skip_1d_uses_t_minus_1_and_t_minus_31() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 31 + [150.0, 999.0]
    panel = pd.DataFrame(_rows("AAAUSDT", start, closes))
    assert panel.loc[panel["date_utc"] == pd.Timestamp("2026-02-01"), "close"].item() == 150.0
    assert panel.loc[panel["date_utc"] == pd.Timestamp("2026-02-02"), "close"].item() == 999.0

    result = compute_momentum_30d_skip_1d(
        panel=panel,
        symbol="AAAUSDT",
        rebalance_date=pd.Timestamp("2026-02-02"),
    )

    assert result == pytest.approx(0.5)


def test_momentum_does_not_use_rebalance_day_close() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 31 + [150.0, 10_000.0]
    panel = pd.DataFrame(_rows("AAAUSDT", start, closes))

    result = compute_momentum_30d_skip_1d(
        panel=panel,
        symbol="AAAUSDT",
        rebalance_date=pd.Timestamp("2026-02-02"),
    )

    assert result == pytest.approx(0.5)


def test_momentum_requires_31_prior_daily_bars() -> None:
    panel = pd.DataFrame(_rows("AAAUSDT", date(2026, 1, 1), [100.0] * 30))

    result = compute_momentum_30d_skip_1d(
        panel=panel,
        symbol="AAAUSDT",
        rebalance_date=pd.Timestamp("2026-01-31"),
    )

    assert result is None


def test_rebalance_factor_frame_applies_point_in_time_liquidity_gate() -> None:
    start = date(2026, 1, 1)
    panel = pd.DataFrame(
        _rows("AAAUSDT", start, [100.0] * 31 + [150.0], quote_volume=25_000_000.0)
        + _rows("BBBUSDT", start, [100.0] * 31 + [160.0], quote_volume=1_000_000.0)
    )

    frame = compute_rebalance_factor_frame(panel=panel, rebalance_date=pd.Timestamp("2026-02-01"))

    assert set(frame["symbol"]) == {"AAAUSDT"}


def test_late_listed_symbol_is_excluded_until_it_has_required_lookback() -> None:
    start = date(2026, 1, 1)
    mature = _rows("AAAUSDT", start, [100.0] * 31 + [150.0], quote_volume=25_000_000.0)
    late = _rows("LATEUSDT", date(2026, 1, 20), [100.0] * 10 + [200.0], quote_volume=25_000_000.0)
    panel = pd.DataFrame(mature + late)

    frame = compute_rebalance_factor_frame(panel=panel, rebalance_date=pd.Timestamp("2026-02-01"))

    assert "AAAUSDT" in set(frame["symbol"])
    assert "LATEUSDT" not in set(frame["symbol"])


def test_symbol_missing_one_lookback_day_is_excluded() -> None:
    start = date(2026, 1, 1)
    rows = _rows("AAAUSDT", start, [100.0] * 31 + [150.0], quote_volume=25_000_000.0)
    rows = [row for row in rows if row["date_utc"] != date(2026, 1, 2)]
    panel = pd.DataFrame(rows)

    frame = compute_rebalance_factor_frame(panel=panel, rebalance_date=pd.Timestamp("2026-02-01"))

    assert "AAAUSDT" not in set(frame["symbol"])


def test_liquidity_rolling_window_requires_30_prior_days() -> None:
    panel = pd.DataFrame(_rows("AAAUSDT", date(2026, 1, 15), [100.0] * 20, quote_volume=25_000_000.0))

    frame = compute_rebalance_factor_frame(panel=panel, rebalance_date=pd.Timestamp("2026-02-01"))

    assert frame.empty
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_factors.py
```

Expected:

```text
FAIL because factors.py does not exist.
```

**Step 3: Implement `factors.py`**

Implementation requirements:

- Import thresholds from `configs/base.py`.
- Use `pd.Timestamp` for dates.
- `compute_momentum_30d_skip_1d` must use:
  - `signal_asof_date = rebalance_date - 1 day`
  - `lookback_start_date = rebalance_date - 31 days`
- Use absolute UTC date lookup, not row-index offsets. A symbol with missing daily bars or a later listing must be excluded until exact `t-1`, exact `t-31`, and the full 30d liquidity window exist.
- `compute_rebalance_factor_frame` must compute:
  - `momentum_30d_skip_1d`
  - `rolling_30d_median_quote_volume_usdt`
  - `signal_asof_date`
  - `lookback_start_date`
  - `eligible_for_rank`

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_factors.py
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add src/research/cross_sectional_factor_lab/factors.py tests/research/test_cross_sectional_factor_lab_stageA_factors.py
git commit -m "feat(factor-lab): add stage A momentum factors"
```

---

## Task 5: Implement Rebalance Calendar And Portfolio Construction

**Files:**
- Create: `src/research/cross_sectional_factor_lab/portfolio.py`
- Create: `tests/research/test_cross_sectional_factor_lab_stageA_portfolio.py`

**Step 1: Write failing tests**

Create tests:

```python
from __future__ import annotations

import pandas as pd

from research.cross_sectional_factor_lab.portfolio import (
    build_equal_weight_targets,
    eligible_monday_rebalance_dates,
)


def test_first_rebalance_after_momentum_and_liquidity_warmup() -> None:
    dates = pd.date_range("2026-01-01", "2026-02-28", freq="D")

    rebalances = eligible_monday_rebalance_dates(dates)

    assert rebalances[0] >= pd.Timestamp("2026-02-02")
    assert all(dt.weekday() == 0 for dt in rebalances)


def test_no_positions_before_warmup_complete() -> None:
    dates = pd.date_range("2026-01-01", "2026-01-20", freq="D")

    assert eligible_monday_rebalance_dates(dates) == []


def test_build_equal_weight_targets_selects_top10_primary() -> None:
    frame = pd.DataFrame(
        {
            "symbol": [f"ALT{i:02d}USDT" for i in range(12)],
            "momentum_30d_skip_1d": list(range(12)),
        }
    )

    targets = build_equal_weight_targets(frame, top_n=10)

    assert len(targets) == 10
    assert targets["target_weight"].sum() == 1.0
    assert "ALT11USDT" in set(targets["symbol"])
    assert "ALT00USDT" not in set(targets["symbol"])


def test_build_equal_weight_targets_marks_insufficient_universe() -> None:
    frame = pd.DataFrame({"symbol": ["AAAUSDT"], "momentum_30d_skip_1d": [0.1]})

    targets = build_equal_weight_targets(frame, top_n=10)

    assert targets.empty
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_portfolio.py
```

Expected:

```text
FAIL because portfolio.py does not exist.
```

**Step 3: Implement `portfolio.py`**

Implementation requirements:

- `eligible_monday_rebalance_dates(dates)` uses `FACTOR_LAB_STAGEA_REBALANCE_WEEKDAY_UTC`.
- Warm-up uses `max(FACTOR_LAB_STAGEA_MOMENTUM_LOOKBACK_DAYS + FACTOR_LAB_STAGEA_SKIP_RECENT_DAYS, 30)`.
- `build_equal_weight_targets` returns empty frame when `len(frame) < top_n`.
- Tie-break by `symbol` after momentum descending for deterministic output.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_portfolio.py
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add src/research/cross_sectional_factor_lab/portfolio.py tests/research/test_cross_sectional_factor_lab_stageA_portfolio.py
git commit -m "feat(factor-lab): add stage A portfolio construction"
```

---

## Task 6: Implement Cost And Benchmark Accounting

**Files:**
- Create: `src/research/cross_sectional_factor_lab/backtest.py`
- Create: `tests/research/test_cross_sectional_factor_lab_stageA_backtest.py`

**Step 1: Write failing tests**

Create tests:

```python
from __future__ import annotations

import pandas as pd
import pytest

from research.cross_sectional_factor_lab.backtest import (
    apply_turnover_cost,
    compute_benchmark_buy_and_hold_net,
    compute_strategy_period_return,
    compute_turnover,
    universe_equal_weight_targets,
)


def test_turnover_is_sum_abs_target_minus_previous_weight() -> None:
    prev = {"AAAUSDT": 0.5, "BBBUSDT": 0.5}
    target = {"CCCUSDT": 0.5, "DDDUSDT": 0.5}

    assert compute_turnover(prev, target) == pytest.approx(2.0)


def test_apply_turnover_cost_uses_one_way_cost_from_round_trip() -> None:
    after_cost = apply_turnover_cost(gross_return=0.10, turnover=2.0, round_trip_cost_bps=30.0)

    assert after_cost == pytest.approx(0.10 - 0.003)


def test_btc_eth_buy_and_hold_applies_entry_exit_cost() -> None:
    net = compute_benchmark_buy_and_hold_net(
        start_open=100.0,
        end_close=120.0,
        round_trip_cost_bps=30.0,
    )

    assert net < 0.20


def test_universe_equal_weight_uses_same_point_in_time_eligible_universe() -> None:
    eligible = pd.DataFrame({"symbol": ["AAAUSDT", "BBBUSDT"]})

    targets = universe_equal_weight_targets(eligible)

    assert set(targets["symbol"]) == {"AAAUSDT", "BBBUSDT"}
    assert targets["target_weight"].sum() == pytest.approx(1.0)


def test_strategy_period_return_uses_rebalance_open_to_next_rebalance_open() -> None:
    panel = pd.DataFrame(
        [
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-02"), "open": 100.0, "close": 999.0},
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-09"), "open": 110.0, "close": 1.0},
        ]
    )

    result = compute_strategy_period_return(
        panel=panel,
        weights={"AAAUSDT": 1.0},
        entry_date=pd.Timestamp("2026-02-02"),
        exit_date=pd.Timestamp("2026-02-09"),
    )

    assert result == pytest.approx(0.10)


def test_does_not_use_rebalance_day_close_for_entry() -> None:
    panel = pd.DataFrame(
        [
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-02"), "open": 100.0, "close": 10_000.0},
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-09"), "open": 100.0, "close": 1.0},
        ]
    )

    result = compute_strategy_period_return(
        panel=panel,
        weights={"AAAUSDT": 1.0},
        entry_date=pd.Timestamp("2026-02-02"),
        exit_date=pd.Timestamp("2026-02-09"),
    )

    assert result == pytest.approx(0.0)


def test_final_period_without_available_exit_open_is_dropped() -> None:
    panel = pd.DataFrame(
        [{"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-02-02"), "open": 100.0, "close": 120.0}]
    )

    result = compute_strategy_period_return(
        panel=panel,
        weights={"AAAUSDT": 1.0},
        entry_date=pd.Timestamp("2026-02-02"),
        exit_date=pd.Timestamp("2026-02-09"),
    )

    assert result is None
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_backtest.py
```

Expected:

```text
FAIL because backtest.py does not exist.
```

**Step 3: Implement `backtest.py`**

Implementation requirements:

- `compute_turnover(previous_weights, target_weights)` returns sum absolute weight changes.
- `apply_turnover_cost(gross_return, turnover, round_trip_cost_bps)` uses `one_way_cost_bps = round_trip_cost_bps / 2`.
- `compute_benchmark_buy_and_hold_net` applies one-way entry cost and one-way exit cost.
- `universe_equal_weight_targets` uses the same eligible frame as the strategy ranking universe.
- `compute_strategy_period_return` uses `open` on `entry_date` and `open` on `exit_date`; it must not use rebalance-day close. If the exit open is unavailable, return `None` and drop the final incomplete period.
- Close prices may be forward-filled per symbol for factor continuity diagnostics, but execution prices (`open` on entry/exit dates) must never be forward-filled. Track any ffill count in summary if ffill is used.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_backtest.py
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add src/research/cross_sectional_factor_lab/backtest.py tests/research/test_cross_sectional_factor_lab_stageA_backtest.py
git commit -m "feat(factor-lab): add stage A cost and benchmark accounting"
```

---

## Task 7: Implement Summary And Decision Gates

**Files:**
- Create: `src/research/cross_sectional_factor_lab/summary.py`
- Create: `tests/research/test_cross_sectional_factor_lab_stageA_summary.py`

**Step 1: Write failing tests**

Create tests:

```python
from __future__ import annotations

from research.cross_sectional_factor_lab.summary import decide_stageA_v1, summarize_rebalance_quality


def _passing_summary() -> dict:
    return {
        "performance": {
            "by_cost_scenario": {
                "base_30_bps_round_trip": {
                    "strategy_total_return_pct": 25.0,
                    "strategy_max_drawdown_pct": 10.0,
                },
                "stress_50_bps_round_trip": {
                    "strategy_total_return_pct": 10.0,
                },
                "crash_80_bps_round_trip": {
                    "strategy_total_return_pct": 2.0,
                },
            }
        },
        "benchmarks": {
            "btc_buy_and_hold_net_with_entry_exit_cost_pct": 15.0,
            "eth_buy_and_hold_net_with_entry_exit_cost_pct": 12.0,
            "universe_equal_weight_total_return_pct": 18.0,
            "universe_equal_weight_max_drawdown_pct": 9.0,
        },
        "concentration": {
            "max_single_symbol_positive_pnl_share": 0.20,
            "max_single_symbol_abs_pnl_share": 0.20,
            "max_single_month_positive_pnl_share": 0.20,
            "max_single_month_abs_pnl_share": 0.20,
        },
        "rebalance_quality": {
            "rebalance_count": 60,
            "insufficient_universe_count": 1,
            "median_selected_symbol_count": 10,
        },
    }


def test_stageA_v1_passes_when_all_gates_pass() -> None:
    assert decide_stageA_v1(_passing_summary()) == "stageA_v1_passed"


def test_stageA_v1_fails_when_base_cost_does_not_beat_equal_weight() -> None:
    summary = _passing_summary()
    summary["performance"]["by_cost_scenario"]["base_30_bps_round_trip"]["strategy_total_return_pct"] = 10.0

    assert decide_stageA_v1(summary) == "stageA_v1_failed"


def test_stageA_v1_fails_on_symbol_concentration() -> None:
    summary = _passing_summary()
    summary["concentration"]["max_single_symbol_positive_pnl_share"] = 0.50

    assert decide_stageA_v1(summary) == "stageA_v1_failed"


def test_concentration_handles_negative_total_pnl() -> None:
    summary = _passing_summary()
    summary["performance"]["by_cost_scenario"]["base_30_bps_round_trip"]["strategy_total_return_pct"] = -5.0
    summary["concentration"]["max_single_symbol_positive_pnl_share"] = 0.0
    summary["concentration"]["max_single_symbol_abs_pnl_share"] = 0.80

    assert decide_stageA_v1(summary) == "stageA_v1_failed"


def test_concentration_reports_abs_pnl_share() -> None:
    summary = _passing_summary()

    assert "max_single_symbol_abs_pnl_share" in summary["concentration"]
    assert "max_single_month_abs_pnl_share" in summary["concentration"]


def test_rebalance_quality_counts_insufficient_universe_ratio() -> None:
    quality = summarize_rebalance_quality(
        rebalance_count=100,
        insufficient_universe_count=5,
        selected_counts=[10, 10, 9],
        turnovers=[1.0, 0.5],
    )

    assert quality["insufficient_universe_ratio"] == 0.05
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_summary.py
```

Expected:

```text
FAIL because summary.py does not exist.
```

**Step 3: Implement `summary.py`**

Implementation requirements:

- Decision uses only `base_30_bps_round_trip` for hard benchmark outperformance.
- `stress_50_bps_round_trip` must not be deeply negative. Define “significantly failed” as total return `< 0`.
- `crash_80_bps_round_trip` must be present but not a pass/fail gate.
- Use config thresholds from `configs/base.py`.
- Concentration summary must report both positive PnL share and absolute PnL share:
  - `max_single_symbol_positive_pnl_share`
  - `max_single_symbol_abs_pnl_share`
  - `max_single_month_positive_pnl_share`
  - `max_single_month_abs_pnl_share`
  - `pnl_contribution_denominator`
- Positive PnL gates use positive PnL share. Any large absolute PnL concentration must be disclosed and may fail the decision if it is extreme.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_summary.py
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add src/research/cross_sectional_factor_lab/summary.py tests/research/test_cross_sectional_factor_lab_stageA_summary.py
git commit -m "feat(factor-lab): add stage A summary decision gates"
```

---

## Task 8: Implement Offline Backtest Orchestrator

**Files:**
- Modify: `src/research/cross_sectional_factor_lab/backtest.py`
- Create: `tests/research/test_cross_sectional_factor_lab_stageA_orchestrator.py`

**Step 1: Write failing tests**

Create tests:

```python
from __future__ import annotations

from datetime import date, timedelta

from research.cross_sectional_factor_lab.backtest import run_stageA_v1_backtest


def _synthetic_panel() -> list[dict]:
    start = date(2025, 1, 1)
    rows = []
    for i in range(90):
        day = start + timedelta(days=i)
        for rank, symbol in enumerate([f"ALT{x:02d}USDT" for x in range(12)]):
            close = 100.0 + i * (rank + 1)
            rows.append(
                {
                    "symbol": symbol,
                    "date_utc": day.isoformat(),
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "base_volume": 1.0,
                    "quote_volume": 25_000_000.0,
                }
            )
    return rows


def test_run_stageA_v1_backtest_returns_required_summary_shape() -> None:
    summary = run_stageA_v1_backtest(_synthetic_panel())

    assert summary["run_mode"] == "stageA_v1_momentum_backtest"
    assert summary["market"] == "binance_spot"
    assert summary["bias_label"] == "survivorship_bias_not_controlled"
    assert summary["primary_portfolio"] == "top10_equal_weight"
    assert "base_30_bps_round_trip" in summary["performance"]["by_cost_scenario"]
    assert "excess_performance" in summary
    assert "concentration" in summary
    assert "rebalance_quality" in summary


def test_run_stageA_v1_backtest_empty_rows_returns_data_unavailable() -> None:
    summary = run_stageA_v1_backtest([])

    assert summary["decision"] == "stageA_v1_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"


def test_short_synthetic_panel_fails_min_rebalance_count_gate() -> None:
    summary = run_stageA_v1_backtest(_synthetic_panel())

    assert summary["rebalance_quality"]["rebalance_count"] < 50
    assert summary["decision"] in {"stageA_v1_failed", "stageA_v1_data_unavailable"}
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_orchestrator.py
```

Expected:

```text
FAIL because run_stageA_v1_backtest is missing.
```

**Step 3: Implement orchestrator**

Implementation requirements:

- Compose `load_daily_panel`, `eligible_monday_rebalance_dates`, `compute_rebalance_factor_frame`, `build_equal_weight_targets`, cost scenarios, benchmarks, concentration, and decision.
- If input rows are empty, return a minimal `stageA_v1_data_unavailable` summary with `primary_blocker = "empty_daily_bars"`.
- Return a JSON-serializable dict.
- Include `top5_equal_weight` diagnostic summary separately, but do not use it in `decision`.
- Do not run 3d rebalance inside Stage A v1. The first Stage A2 robustness item is `3d_rebalance_diagnostic`.
- Do not fetch live data in this function.

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA_orchestrator.py
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add src/research/cross_sectional_factor_lab/backtest.py tests/research/test_cross_sectional_factor_lab_stageA_orchestrator.py
git commit -m "feat(factor-lab): add stage A offline backtest orchestrator"
```

---

## Task 9: Add CLI With Offline Fixture Mode

**Files:**
- Create: `scripts/run_factor_lab_stageA_v1_momentum.py`
- Create: `tests/scripts/test_run_factor_lab_stageA_v1_momentum.py`

**Step 1: Write failing CLI tests**

Create tests:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_factor_lab_stageA_v1_momentum import main


def test_cli_empty_fixture_writes_data_unavailable_summary(tmp_path) -> None:
    fixture = tmp_path / "fixture.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main(["--offline-sample", str(fixture), "--output", str(output)])

    assert result == 0
    assert output.exists()
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "stageA_v1_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"


def test_cli_summary_marks_not_live_safe(tmp_path) -> None:
    fixture = tmp_path / "fixture.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    main(["--offline-sample", str(fixture), "--output", str(output)])

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["live_usage"] == "not_allowed"


def test_cli_fail_on_decision_returns_nonzero_for_data_unavailable(tmp_path) -> None:
    fixture = tmp_path / "fixture.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main(["--offline-sample", str(fixture), "--output", str(output), "--fail-on-decision"])

    assert result == 1
```

**Step 2: Run failing tests**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_run_factor_lab_stageA_v1_momentum.py
```

Expected:

```text
FAIL because CLI script does not exist.
```

**Step 3: Implement CLI**

CLI args:

```text
--offline-sample PATH
--output PATH
--history-days 540
--exchange binance
--max-symbols optional
--fail-on-decision optional
```

Offline mode:

```text
read JSON fixture;
if daily_bars is empty, write stageA_v1_data_unavailable with primary_blocker=empty_daily_bars;
call run_stageA_v1_backtest(fixture["daily_bars"]);
write summary JSON;
return 0.
```

Live mode:

```text
use public ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}});
load markets;
apply spot USDT filters from Stage 0 universe logic;
fetch 540 complete UTC daily OHLCV bars per eligible symbol;
write summary JSON;
return 0 when summary is written.
```

Do not use `EXCHANGES` or private API keys.

Exit code policy:

```text
Default mode returns 0 when a valid summary file is written, even if decision = stageA_v1_failed.
Reason: a failed strategy is a valid research outcome, not a script crash.

If --fail-on-decision is set:
  return 1 for stageA_v1_failed or stageA_v1_data_unavailable;
  return 0 only for stageA_v1_passed.
```

**Step 4: Verify**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_run_factor_lab_stageA_v1_momentum.py
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add scripts/run_factor_lab_stageA_v1_momentum.py tests/scripts/test_run_factor_lab_stageA_v1_momentum.py
git commit -m "feat(factor-lab): add stage A momentum CLI"
```

---

## Task 10: Run Stage A v1 And Write Review

**Files:**
- Create or update: `reports/cross_sectional_factor_lab/stageA_v1_momentum_summary.json`
- Create: `docs/reviews/2026-06-08-cross-sectional-factor-lab-stageA-v1-review_CN.md`

**Step 1: Run live Stage A v1 audit/backtest**

Run:

```bash
PYTHONPATH=src uv run python scripts/run_factor_lab_stageA_v1_momentum.py \
  --exchange binance \
  --history-days 540 \
  --output reports/cross_sectional_factor_lab/stageA_v1_momentum_summary.json
```

Expected:

```text
summary JSON written
decision is one of stageA_v1_passed | stageA_v1_failed | stageA_v1_data_unavailable
live_usage = not_allowed
bias_label = survivorship_bias_not_controlled
```

**Step 2: Inspect summary**

Run:

```bash
jq '{decision, bias_label, live_usage, primary_portfolio, cost_scenarios_round_trip_bps, excess_performance, concentration, rebalance_quality}' \
  reports/cross_sectional_factor_lab/stageA_v1_momentum_summary.json
```

Expected:

```text
fields are present and populated
```

**Step 3: Write review**

Create `docs/reviews/2026-06-08-cross-sectional-factor-lab-stageA-v1-review_CN.md` with sections:

```text
1. 核心结论
2. 数据与偏差
3. 主组合结果：top10_equal_weight
4. 成本场景：30 / 50 / 80 bps
5. Benchmark 对比
6. 集中度审计
7. 诊断组合：top5_equal_weight
8. 失败类型或通过限制
9. 下一步动作
```

Decision language:

```text
stageA_v1_passed -> 只允许进入 Stage A2 robustness plan，不允许 live/paper
stageA_v1_failed -> 写 failure review，不允许调参宣布通过
stageA_v1_data_unavailable -> 修数据源或缩小 universe
```

**Step 4: Commit**

```bash
git add reports/cross_sectional_factor_lab/stageA_v1_momentum_summary.json docs/reviews/2026-06-08-cross-sectional-factor-lab-stageA-v1-review_CN.md
git commit -m "research(factor-lab): add stage A v1 momentum review"
```

---

## Task 11: Final Verification

**Files:**
- All files touched by Tasks 1-10.

**Step 1: Run focused tests**

```bash
PYTHONPATH=src uv run pytest -q \
  tests/test_factor_lab_stageA_config.py \
  tests/research/test_cross_sectional_factor_lab_stageA_panel.py \
  tests/research/test_cross_sectional_factor_lab_stageA_factors.py \
  tests/research/test_cross_sectional_factor_lab_stageA_portfolio.py \
  tests/research/test_cross_sectional_factor_lab_stageA_backtest.py \
  tests/research/test_cross_sectional_factor_lab_stageA_summary.py \
  tests/research/test_cross_sectional_factor_lab_stageA_orchestrator.py \
  tests/scripts/test_run_factor_lab_stageA_v1_momentum.py
```

Expected:

```text
PASS
```

**Step 2: Run full tests**

```bash
uv run pytest
```

Expected:

```text
PASS
```

**Step 3: Run ruff**

```bash
uv run ruff check configs/base.py src/research/cross_sectional_factor_lab scripts/run_factor_lab_stageA_v1_momentum.py tests/research tests/scripts tests/test_factor_lab_stageA_config.py
```

Expected:

```text
All checks passed
```

**Step 4: Inspect git status**

```bash
git status --short
```

Expected:

```text
clean, except for intentionally uncommitted files if user requested no commit
```

---

## Handoff Notes

1. Do not merge this branch to `main` after Stage A v1 implementation unless the user explicitly asks.
2. Do not convert a passing Stage A v1 into live or paper trading.
3. If Stage A v1 fails, do not tune parameters in the same implementation branch. Write a failure review first.
4. If Stage A v1 passes, next allowed document is:

```text
docs/plans/YYYY-MM-DD-cross-sectional-factor-lab-stageA2-robustness-plan_CN.md
```

5. Stage A2 first required robustness item is `3d_rebalance_diagnostic`, because Stage A v1 only tests weekly rebalance and cannot distinguish weak momentum from overly slow rebalance cadence.
6. Keep `C1 entry block` as diagnostic-only until C1 receives separate 30d forward or orderbook-aware validation.
