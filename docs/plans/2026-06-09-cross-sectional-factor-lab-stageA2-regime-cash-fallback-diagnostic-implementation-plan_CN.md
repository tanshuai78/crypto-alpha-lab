# Cross-Sectional Factor Lab Stage A2 Regime/Cash Fallback Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Stage A2 Round 1 的 regime/cash fallback 诊断，判断 Stage A v1 的 long-only alt rotation 是否应该在弱势 regime 下空仓。

**Architecture:** 复用 Stage A v1 的 daily panel、30d momentum、weekly rebalance、top10 equal-weight、30/50/80 bps 成本和 benchmark 逻辑；新增一个 regime exposure 层，分别测试 `regime_none`、`btc_ma20_cash`、`alt_universe_20d_return_cash`。本轮只做诊断，不接 live/paper，不做 3d、14d、volume、funding/OI、on-chain 或模型融合。

**Tech Stack:** Python 3.11, pandas, numpy, pytest, ruff, ccxt, Binance public spot kline API.

---

## 0. Scope Lock

本计划只实现：

```text
Stage A2 Round 1 = regime_cash_fallback_only
```

允许的三组变体：

```text
regime_none
btc_ma20_cash
alt_universe_20d_return_cash
```

本计划禁止实现：

```text
3d rebalance
14d momentum
volume confirmation
volatility-adjusted momentum
funding/OI veto
on-chain factors
LightGBM
BTC/ETH core + alt satellite
paper trading
live trading
```

如果某个 regime filter 看起来改善结果，只能写入 diagnostic summary 和 review；不得修改阈值追结果。

---

## 1. Required Fixes Incorporated

这版计划已经吸收 review feedback 中的硬修正：

```text
1. Stage A2 继承 rebalance_count >= 50 的有效样本门槛。
2. BTC/ETH benchmark 使用 first rebalance open 到 last valid exit open，和策略 open-to-open 周期一致。
3. alt_universe_20d_return_cash 增加 coverage gate 和 min valid symbols gate。
4. regime_filter 同时输出 rebalance period share 和 days share。
5. concentration 同时输出 positive PnL share 和 abs PnL share。
6. regime_none 的 drawdown reduction 固定为 0.0，不通过双跑间接计算。
7. review 生成脚本输出 failure taxonomy，不默认跳到 B-lite。
8. weekly exit date 统一封装，避免脚本内散落 timedelta(days=7)。
```

---

## 2. File Map

### Create

- `src/research/cross_sectional_factor_lab/regime.py`
  - Stage A2 regime 信号计算。
  - 只允许使用 `rebalance_date - 1 day` 及更早数据。
  - 输出 alt universe coverage diagnostics。

- `src/research/cross_sectional_factor_lab/stageA2.py`
  - Stage A2 Round 1 回测和 summary 组装。
  - 单独计算真实 universe equal-weight benchmark。
  - benchmark 使用 open-to-open 口径。

- `scripts/run_factor_lab_stageA2_regime_cash_fallback.py`
  - Stage A2 CLI。
  - 支持 `--offline-sample` 与 live Binance spot fetch。
  - 输出 `reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json`。

- `tests/research/test_cross_sectional_factor_lab_stageA2_regime.py`
- `tests/research/test_cross_sectional_factor_lab_stageA2_backtest.py`
- `tests/research/test_cross_sectional_factor_lab_stageA2_summary.py`
- `tests/scripts/test_run_factor_lab_stageA2_regime_cash_fallback.py`
- `tests/test_factor_lab_stageA2_config.py`
- `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-regime-cash-fallback-review_CN.md`

### Modify

- `configs/base.py`
  - 新增 Stage A2 配置阈值。

- `src/research/cross_sectional_factor_lab/summary.py`
  - 新增 Stage A2 decision helpers。

### Reuse

- `src/research/cross_sectional_factor_lab/panel.py`
- `src/research/cross_sectional_factor_lab/factors.py`
- `src/research/cross_sectional_factor_lab/portfolio.py`
- `src/research/cross_sectional_factor_lab/backtest.py`
- `scripts/run_factor_lab_stageA_v1_momentum.py`

---

## 3. Config Contract

新增配置必须进入 `configs/base.py`，不得写成脚本内隐藏常量。

```python
# ─── Strategy: Cross-Sectional Factor Lab Stage A2 ─────────────────────────

FACTOR_LAB_STAGEA2_BTC_MA_DAYS = 20
# BTC regime filter lookback. Uses BTC close from t-20 through t-1.

FACTOR_LAB_STAGEA2_ALT_UNIVERSE_RETURN_DAYS = 20
# Alt universe regime filter lookback. Uses t-21 through t-1.

FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_COVERAGE_RATIO = 0.80
# Minimum share of eligible symbols with valid 20d returns for alt universe regime.

FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_SYMBOLS = FACTOR_LAB_STAGEA_PRIMARY_TOP_N
# Minimum valid symbol count for alt universe regime decision.

FACTOR_LAB_STAGEA2_MIN_DRAWDOWN_REDUCTION_PCT = 30.0
# Minimum max drawdown reduction versus regime_none baseline.

FACTOR_LAB_STAGEA2_MAX_CASH_DAYS_SHARE = 0.60
# Mostly-cash filters cannot unlock Stage A2 Round 2.

FACTOR_LAB_STAGEA2_MAX_BENCHMARK_UNDERPERFORMANCE_PCT = 10.0
# Strategy may not underperform BTC or ETH by more than 10 percentage points under base 30 bps cost.

FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT = FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT
# Stage A2 inherits Stage A v1 minimum effective rebalance sample size.

FACTOR_LAB_STAGEA2_ALLOWED_VARIANTS = (
    "regime_none",
    "btc_ma20_cash",
    "alt_universe_20d_return_cash",
)
# Only these Stage A2 Round 1 variants are allowed.
```

---

## 4. Task 1: Add Stage A2 Config Tests And Constants

**Files:**

- Modify: `configs/base.py`
- Create: `tests/test_factor_lab_stageA2_config.py`

- [ ] **Step 1: Write failing config tests**

Create `tests/test_factor_lab_stageA2_config.py`:

```python
import configs.base as cfg


def test_stageA2_regime_config_values_are_locked():
    assert cfg.FACTOR_LAB_STAGEA2_BTC_MA_DAYS == 20
    assert cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_RETURN_DAYS == 20
    assert cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_COVERAGE_RATIO == 0.80
    assert cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_SYMBOLS == cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N
    assert cfg.FACTOR_LAB_STAGEA2_MIN_DRAWDOWN_REDUCTION_PCT == 30.0
    assert cfg.FACTOR_LAB_STAGEA2_MAX_CASH_DAYS_SHARE == 0.60
    assert cfg.FACTOR_LAB_STAGEA2_MAX_BENCHMARK_UNDERPERFORMANCE_PCT == 10.0
    assert cfg.FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT == cfg.FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT


def test_stageA2_allowed_variants_are_narrowed_to_round1_scope():
    assert cfg.FACTOR_LAB_STAGEA2_ALLOWED_VARIANTS == (
        "regime_none",
        "btc_ma20_cash",
        "alt_universe_20d_return_cash",
    )
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/test_factor_lab_stageA2_config.py
```

Expected:

```text
FAILED tests/test_factor_lab_stageA2_config.py::test_stageA2_regime_config_values_are_locked
AttributeError: module 'configs.base' has no attribute 'FACTOR_LAB_STAGEA2_BTC_MA_DAYS'
```

- [ ] **Step 3: Add constants to `configs/base.py`**

Append after Stage A v1 config block:

```python

# ─── Strategy: Cross-Sectional Factor Lab Stage A2 ─────────────────────────

FACTOR_LAB_STAGEA2_BTC_MA_DAYS = 20
# BTC regime filter lookback. Uses BTC close from t-20 through t-1.

FACTOR_LAB_STAGEA2_ALT_UNIVERSE_RETURN_DAYS = 20
# Alt universe regime filter lookback. Uses t-21 through t-1.

FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_COVERAGE_RATIO = 0.80
# Minimum share of eligible symbols with valid 20d returns for alt universe regime.

FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_SYMBOLS = FACTOR_LAB_STAGEA_PRIMARY_TOP_N
# Minimum valid symbol count for alt universe regime decision.

FACTOR_LAB_STAGEA2_MIN_DRAWDOWN_REDUCTION_PCT = 30.0
# Minimum max drawdown reduction versus regime_none baseline.

FACTOR_LAB_STAGEA2_MAX_CASH_DAYS_SHARE = 0.60
# Mostly-cash filters cannot unlock Stage A2 Round 2.

FACTOR_LAB_STAGEA2_MAX_BENCHMARK_UNDERPERFORMANCE_PCT = 10.0
# Maximum allowed underperformance versus BTC/ETH buy-and-hold in percentage points.

FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT = FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT
# Stage A2 inherits Stage A v1 minimum effective rebalance sample size.

FACTOR_LAB_STAGEA2_ALLOWED_VARIANTS = (
    "regime_none",
    "btc_ma20_cash",
    "alt_universe_20d_return_cash",
)
# Only these Stage A2 Round 1 variants are allowed.
```

- [ ] **Step 4: Run config tests and verify pass**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/test_factor_lab_stageA2_config.py
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit Task 1**

```bash
git add configs/base.py tests/test_factor_lab_stageA2_config.py
git commit -m "config(factor-lab): add stage A2 regime defaults"
```

---

## 5. Task 2: Implement Regime Signal Module

**Files:**

- Create: `src/research/cross_sectional_factor_lab/regime.py`
- Test: `tests/research/test_cross_sectional_factor_lab_stageA2_regime.py`

### Regime Semantics

```text
rebalance_date = t
signal_asof_date = t - 1 day
BTC MA20 window = [t-20, t-1]
alt universe return window = [t-21, t-1]
```

`alt_universe_20d_return_cash` must not be decided by a tiny valid subset. It requires:

```text
symbols_with_valid_20d_return / eligible_symbols_count >= 0.80
symbols_with_valid_20d_return >= FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_SYMBOLS
```

- [ ] **Step 1: Write failing regime tests**

Create `tests/research/test_cross_sectional_factor_lab_stageA2_regime.py`:

```python
from datetime import date, timedelta

import pandas as pd

from research.cross_sectional_factor_lab.regime import (
    compute_alt_universe_20d_return_regime,
    compute_btc_ma20_regime,
    decide_stageA2_regime_exposure,
)


def _daily_row(symbol: str, dt: date, close: float) -> dict:
    return {
        "symbol": symbol,
        "date_utc": pd.Timestamp(dt),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "base_volume": 1_000_000.0,
        "quote_volume": 50_000_000.0,
    }


def _alt_rows(symbols: list[str], start: date, days: int, start_close: float, end_close: float) -> list[dict]:
    rows = []
    for i in range(days):
        dt = start + timedelta(days=i)
        close = start_close
        if dt == date(2026, 1, 30):
            close = end_close
        for symbol in symbols:
            rows.append(_daily_row(symbol, dt, close))
    return rows


def test_btc_ma20_uses_t_minus_1_and_excludes_rebalance_day_close():
    start = date(2026, 1, 1)
    rows = []
    for i in range(31):
        dt = start + timedelta(days=i)
        close = 100.0
        if dt == date(2026, 1, 30):
            close = 150.0
        if dt == date(2026, 1, 31):
            close = 1.0
        rows.append(_daily_row("BTCUSDT", dt, close))
    panel = pd.DataFrame(rows)

    assert compute_btc_ma20_regime(panel, pd.Timestamp("2026-01-31")) is True


def test_btc_ma20_returns_false_when_required_history_missing():
    panel = pd.DataFrame([_daily_row("BTCUSDT", date(2026, 1, 30), 150.0)])

    assert compute_btc_ma20_regime(panel, pd.Timestamp("2026-01-31")) is False


def test_alt_universe_20d_return_returns_true_with_valid_positive_coverage():
    symbols = [f"ALT{i:02d}USDT" for i in range(10)]
    panel = pd.DataFrame(_alt_rows(symbols, date(2026, 1, 10), 22, 100.0, 120.0))

    result = compute_alt_universe_20d_return_regime(
        panel,
        pd.Timestamp("2026-01-31"),
        eligible_symbols=symbols,
    )

    assert result.allow_exposure is True
    assert result.eligible_symbols_count == 10
    assert result.symbols_with_valid_20d_return == 10
    assert result.coverage_ratio == 1.0


def test_alt_universe_regime_returns_false_when_coverage_below_min():
    valid_symbols = [f"ALT{i:02d}USDT" for i in range(7)]
    all_symbols = valid_symbols + ["MISS1USDT", "MISS2USDT", "MISS3USDT"]
    panel = pd.DataFrame(_alt_rows(valid_symbols, date(2026, 1, 10), 22, 100.0, 120.0))

    result = compute_alt_universe_20d_return_regime(
        panel,
        pd.Timestamp("2026-01-31"),
        eligible_symbols=all_symbols,
    )

    assert result.allow_exposure is False
    assert result.symbols_with_valid_20d_return == 7
    assert result.coverage_ratio == 0.7


def test_alt_universe_regime_requires_min_valid_symbol_count():
    symbols = [f"ALT{i:02d}USDT" for i in range(9)]
    panel = pd.DataFrame(_alt_rows(symbols, date(2026, 1, 10), 22, 100.0, 120.0))

    result = compute_alt_universe_20d_return_regime(
        panel,
        pd.Timestamp("2026-01-31"),
        eligible_symbols=symbols,
    )

    assert result.allow_exposure is False
    assert result.symbols_with_valid_20d_return == 9


def test_alt_universe_20d_return_ignores_rebalance_day_pump():
    rows = []
    for i in range(22):
        dt = date(2026, 1, 10) + timedelta(days=i)
        close = 100.0
        if dt == date(2026, 1, 30):
            close = 90.0
        if dt == date(2026, 1, 31):
            close = 999.0
        for symbol in [f"ALT{j:02d}USDT" for j in range(10)]:
            rows.append(_daily_row(symbol, dt, close))
    panel = pd.DataFrame(rows)

    result = compute_alt_universe_20d_return_regime(
        panel,
        pd.Timestamp("2026-01-31"),
        eligible_symbols=[f"ALT{j:02d}USDT" for j in range(10)],
    )

    assert result.allow_exposure is False


def test_decide_stageA2_regime_exposure_rejects_unknown_variant():
    panel = pd.DataFrame([_daily_row("BTCUSDT", date(2026, 1, 1), 100.0)])

    try:
        decide_stageA2_regime_exposure(
            "volume_filter",
            panel,
            pd.Timestamp("2026-01-31"),
            eligible_symbols=("AAAUSDT",),
        )
    except ValueError as exc:
        assert "unsupported Stage A2 variant" in str(exc)
    else:
        raise AssertionError("unknown variant should raise ValueError")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA2_regime.py
```

Expected:

```text
ModuleNotFoundError: No module named 'research.cross_sectional_factor_lab.regime'
```

- [ ] **Step 3: Create `regime.py`**

Create `src/research/cross_sectional_factor_lab/regime.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

import pandas as pd

import configs.base as cfg
from research.cross_sectional_factor_lab.universe import normalize_symbol


@dataclass(frozen=True)
class AltUniverseRegimeResult:
    allow_exposure: bool
    eligible_symbols_count: int
    symbols_with_valid_20d_return: int
    coverage_ratio: float
    universe_return_20d: float | None
    included_btc_eth: bool


def _symbol_close_on(panel: pd.DataFrame, symbol: str, dt: pd.Timestamp) -> float | None:
    normalized = normalize_symbol(symbol)
    rows = panel[(panel["symbol"] == normalized) & (panel["date_utc"] == dt)]
    if rows.empty:
        return None
    close = float(rows["close"].iloc[0])
    return close if close > 0 else None


def compute_btc_ma20_regime(panel: pd.DataFrame, rebalance_date: pd.Timestamp) -> bool:
    signal_asof_date = rebalance_date - timedelta(days=1)
    ma_start = rebalance_date - timedelta(days=cfg.FACTOR_LAB_STAGEA2_BTC_MA_DAYS)
    btc = panel[panel["symbol"] == "BTCUSDT"]
    window = btc[(btc["date_utc"] >= ma_start) & (btc["date_utc"] <= signal_asof_date)]
    if window["date_utc"].nunique() < cfg.FACTOR_LAB_STAGEA2_BTC_MA_DAYS:
        return False
    asof_close = _symbol_close_on(panel, "BTCUSDT", signal_asof_date)
    if asof_close is None:
        return False
    return asof_close > float(window["close"].mean())


def compute_alt_universe_20d_return_regime(
    panel: pd.DataFrame,
    rebalance_date: pd.Timestamp,
    eligible_symbols: Iterable[str],
) -> AltUniverseRegimeResult:
    normalized_symbols = tuple(normalize_symbol(symbol) for symbol in eligible_symbols)
    eligible_count = len(normalized_symbols)
    included_btc_eth = "BTCUSDT" in normalized_symbols or "ETHUSDT" in normalized_symbols
    if eligible_count == 0:
        return AltUniverseRegimeResult(False, 0, 0, 0.0, None, included_btc_eth)

    signal_asof_date = rebalance_date - timedelta(days=1)
    lookback_start_date = rebalance_date - timedelta(days=cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_RETURN_DAYS + 1)
    returns: list[float] = []
    for symbol in normalized_symbols:
        start_close = _symbol_close_on(panel, symbol, lookback_start_date)
        asof_close = _symbol_close_on(panel, symbol, signal_asof_date)
        if start_close is None or asof_close is None:
            continue
        returns.append((asof_close / start_close) - 1.0)

    valid_count = len(returns)
    coverage_ratio = valid_count / eligible_count if eligible_count else 0.0
    universe_return = float(sum(returns) / valid_count) if valid_count else None
    coverage_ok = coverage_ratio >= cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_COVERAGE_RATIO
    count_ok = valid_count >= cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_SYMBOLS
    allow = bool(coverage_ok and count_ok and universe_return is not None and universe_return > 0.0)
    return AltUniverseRegimeResult(allow, eligible_count, valid_count, coverage_ratio, universe_return, included_btc_eth)


def decide_stageA2_regime_exposure(
    variant: str,
    panel: pd.DataFrame,
    rebalance_date: pd.Timestamp,
    eligible_symbols: Iterable[str],
) -> tuple[bool, AltUniverseRegimeResult | None]:
    if variant == "regime_none":
        return True, None
    if variant == "btc_ma20_cash":
        return compute_btc_ma20_regime(panel, rebalance_date), None
    if variant == "alt_universe_20d_return_cash":
        result = compute_alt_universe_20d_return_regime(panel, rebalance_date, eligible_symbols)
        return result.allow_exposure, result
    raise ValueError(f"unsupported Stage A2 variant: {variant}")
```

- [ ] **Step 4: Run regime tests and verify pass**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA2_regime.py
```

Expected:

```text
7 passed
```

- [ ] **Step 5: Commit Task 2**

```bash
git add src/research/cross_sectional_factor_lab/regime.py tests/research/test_cross_sectional_factor_lab_stageA2_regime.py
git commit -m "feat(factor-lab): add stage A2 regime signals"
```

---

## 6. Task 3: Add Stage A2 Summary Decision Helpers

**Files:**

- Modify: `src/research/cross_sectional_factor_lab/summary.py`
- Test: `tests/research/test_cross_sectional_factor_lab_stageA2_summary.py`

### Variant Decision Contract

Possible decisions:

```text
regime_filter_data_insufficient
regime_filter_promising
regime_filter_reduces_damage_but_no_alpha
regime_filter_failed
```

Data is insufficient when:

```text
rebalance_quality.rebalance_count < FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT
```

A non-baseline variant is `regime_filter_promising` only if all conditions hold:

```text
rebalance_count >= 50
max_drawdown_vs_v1_reduction_pct >= 30.0
base_30bps_total_return_pct > universe_equal_weight_pct
base_30bps_total_return_pct >= btc_buy_and_hold_net_pct - 10.0
base_30bps_total_return_pct >= eth_buy_and_hold_net_pct - 10.0
cash_days_share <= 0.60
max_single_month_positive_pnl_share <= 0.30
```

- [ ] **Step 1: Write failing summary tests**

Create `tests/research/test_cross_sectional_factor_lab_stageA2_summary.py`:

```python
import configs.base as cfg
from research.cross_sectional_factor_lab.summary import decide_stageA2_round1, decide_stageA2_variant


def _variant(
    variant: str,
    drawdown_reduction: float,
    strategy_return: float,
    rebalance_count: int | None = None,
    ew_return: float = -20.0,
    btc_return: float = -10.0,
    eth_return: float = -15.0,
    cash_days_share: float = 0.40,
    month_share: float = 0.20,
) -> dict:
    return {
        "variant": variant,
        "regime_filter": {
            "cash_days_share": cash_days_share,
            "mostly_cash_strategy": cash_days_share > 0.60,
        },
        "performance": {
            "base_30bps_total_return_pct": strategy_return,
            "max_drawdown_vs_v1_reduction_pct": drawdown_reduction,
        },
        "benchmarks": {
            "btc_buy_and_hold_net_pct": btc_return,
            "eth_buy_and_hold_net_pct": eth_return,
            "universe_equal_weight_pct": ew_return,
        },
        "concentration": {
            "max_single_month_positive_pnl_share": month_share,
        },
        "rebalance_quality": {
            "rebalance_count": rebalance_count if rebalance_count is not None else cfg.FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT,
            "insufficient_universe_count": 0,
            "insufficient_universe_ratio": 0.0,
            "median_selected_symbol_count": 10.0,
            "turnover_median": 0.5,
        },
    }


def test_stageA2_variant_data_insufficient_when_rebalance_count_below_gate():
    variant = _variant("btc_ma20_cash", 35.0, -5.0, rebalance_count=10)

    assert decide_stageA2_variant(variant) == "regime_filter_data_insufficient"


def test_stageA2_variant_promising_requires_all_gates():
    variant = _variant("btc_ma20_cash", 35.0, -5.0)

    assert decide_stageA2_variant(variant) == "regime_filter_promising"


def test_stageA2_variant_reduces_damage_but_no_alpha_when_benchmark_gate_fails():
    variant = _variant("btc_ma20_cash", 35.0, -30.0, ew_return=-40.0, btc_return=-10.0, eth_return=-15.0)

    assert decide_stageA2_variant(variant) == "regime_filter_reduces_damage_but_no_alpha"


def test_stageA2_variant_reduces_damage_but_no_alpha_when_mostly_cash():
    variant = _variant("alt_universe_20d_return_cash", 40.0, -5.0, cash_days_share=0.75)

    assert decide_stageA2_variant(variant) == "regime_filter_reduces_damage_but_no_alpha"


def test_stageA2_variant_failed_when_drawdown_reduction_is_too_small():
    variant = _variant("alt_universe_20d_return_cash", 20.0, -5.0)

    assert decide_stageA2_variant(variant) == "regime_filter_failed"


def test_stageA2_round1_cannot_unlock_round2_with_insufficient_rebalances():
    variants = [
        {**_variant("btc_ma20_cash", 35.0, -5.0, rebalance_count=10), "decision": "regime_filter_data_insufficient"},
    ]

    decision = decide_stageA2_round1(variants)

    assert decision["winner_variant"] is None
    assert decision["can_enter_stageA2_round2"] is False


def test_stageA2_round1_unlocks_round2_only_for_non_baseline_promising_variant():
    variants = [
        {**_variant("regime_none", 0.0, -84.0), "decision": "regime_filter_failed"},
        {**_variant("btc_ma20_cash", 35.0, -5.0), "decision": "regime_filter_promising"},
    ]

    decision = decide_stageA2_round1(variants)

    assert decision["winner_variant"] == "btc_ma20_cash"
    assert decision["can_enter_stageA2_round2"] is True
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA2_summary.py
```

Expected:

```text
ImportError: cannot import name 'decide_stageA2_variant'
```

- [ ] **Step 3: Add decision helpers to `summary.py`**

Append to `src/research/cross_sectional_factor_lab/summary.py`:

```python

def decide_stageA2_variant(variant_summary: dict[str, Any]) -> str:
    rebalance_quality = variant_summary.get("rebalance_quality", {})
    rebalance_count = int(rebalance_quality.get("rebalance_count", 0))
    if rebalance_count < cfg.FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT:
        return "regime_filter_data_insufficient"

    performance = variant_summary["performance"]
    benchmarks = variant_summary["benchmarks"]
    regime_filter = variant_summary["regime_filter"]
    concentration = variant_summary["concentration"]

    drawdown_reduction = performance["max_drawdown_vs_v1_reduction_pct"]
    strategy_return = performance["base_30bps_total_return_pct"]
    ew_return = benchmarks["universe_equal_weight_pct"]
    btc_return = benchmarks["btc_buy_and_hold_net_pct"]
    eth_return = benchmarks["eth_buy_and_hold_net_pct"]
    cash_days_share = regime_filter["cash_days_share"]
    month_share = concentration["max_single_month_positive_pnl_share"]

    if drawdown_reduction < cfg.FACTOR_LAB_STAGEA2_MIN_DRAWDOWN_REDUCTION_PCT:
        return "regime_filter_failed"

    benchmark_floor = cfg.FACTOR_LAB_STAGEA2_MAX_BENCHMARK_UNDERPERFORMANCE_PCT
    passes_alpha = strategy_return > ew_return
    passes_btc = strategy_return >= btc_return - benchmark_floor
    passes_eth = strategy_return >= eth_return - benchmark_floor
    passes_cash = cash_days_share <= cfg.FACTOR_LAB_STAGEA2_MAX_CASH_DAYS_SHARE
    passes_month_concentration = (
        month_share <= cfg.FACTOR_LAB_STAGEA_MAX_SINGLE_MONTH_PNL_CONTRIBUTION_SHARE
    )

    if passes_alpha and passes_btc and passes_eth and passes_cash and passes_month_concentration:
        return "regime_filter_promising"

    return "regime_filter_reduces_damage_but_no_alpha"


def decide_stageA2_round1(variant_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    promising = [
        item
        for item in variant_summaries
        if item.get("variant") != "regime_none"
        and item.get("decision") == "regime_filter_promising"
        and item.get("rebalance_quality", {}).get("rebalance_count", 0) >= cfg.FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT
    ]
    if not promising:
        return {"winner_variant": None, "can_enter_stageA2_round2": False}
    winner = max(
        promising,
        key=lambda item: (
            item["performance"]["max_drawdown_vs_v1_reduction_pct"],
            item["performance"]["base_30bps_total_return_pct"],
        ),
    )
    return {"winner_variant": winner["variant"], "can_enter_stageA2_round2": True}
```

- [ ] **Step 4: Run summary tests and verify pass**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA2_summary.py
```

Expected:

```text
7 passed
```

- [ ] **Step 5: Commit Task 3**

```bash
git add src/research/cross_sectional_factor_lab/summary.py tests/research/test_cross_sectional_factor_lab_stageA2_summary.py
git commit -m "feat(factor-lab): add stage A2 regime decisions"
```

---

## 7. Task 4: Implement Stage A2 Backtest Orchestrator

**Files:**

- Create: `src/research/cross_sectional_factor_lab/stageA2.py`
- Test: `tests/research/test_cross_sectional_factor_lab_stageA2_backtest.py`

### Backtest Semantics

For each weekly rebalance date:

```text
entry = rebalance_date open
exit = next weekly rebalance date open
cash gross return = 0.0
cash still pays transition turnover cost
```

`regime_none` must have:

```text
max_drawdown_vs_v1_reduction_pct = 0.0 exactly
```

- [ ] **Step 1: Write failing backtest tests**

Create `tests/research/test_cross_sectional_factor_lab_stageA2_backtest.py`:

```python
from datetime import date, timedelta

from research.cross_sectional_factor_lab.stageA2 import (
    compound_returns_pct,
    max_drawdown_pct,
    next_weekly_exit_date,
    run_stageA2_regime_cash_fallback_diagnostic,
)


def _row(symbol: str, dt: date, close: float, quote_volume: float = 100_000_000.0) -> dict:
    return {
        "symbol": symbol,
        "date_utc": dt.isoformat(),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "base_volume": 1_000_000.0,
        "quote_volume": quote_volume,
    }


def _synthetic_rows(days: int = 430) -> list[dict]:
    start = date(2025, 1, 1)
    symbols = ["BTCUSDT", "ETHUSDT"] + [f"ALT{i:02d}USDT" for i in range(12)]
    rows = []
    for i in range(days):
        dt = start + timedelta(days=i)
        rows.append(_row("BTCUSDT", dt, 100.0 + i * 0.2))
        rows.append(_row("ETHUSDT", dt, 90.0 + i * 0.1))
        for j, symbol in enumerate(symbols[2:]):
            close = 50.0 + i * (0.05 + j * 0.002)
            rows.append(_row(symbol, dt, close))
    return rows


def test_next_weekly_exit_date_centralizes_weekly_period():
    assert next_weekly_exit_date(__import__("pandas").Timestamp("2026-01-05")) == __import__("pandas").Timestamp("2026-01-12")


def test_compound_returns_pct_handles_empty_and_simple_returns():
    assert compound_returns_pct([]) == 0.0
    assert round(compound_returns_pct([0.10, -0.10]), 4) == -1.0


def test_max_drawdown_pct_uses_compounded_equity_curve():
    assert round(max_drawdown_pct([0.10, -0.20, 0.05]), 4) == 20.0


def test_stageA2_empty_rows_returns_data_unavailable_summary():
    summary = run_stageA2_regime_cash_fallback_diagnostic([])

    assert summary["decision"] == "stageA2_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"
    assert summary["live_usage"] == "not_allowed"


def test_stageA2_summary_contains_three_locked_variants():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())

    assert [item["variant"] for item in summary["variants"]] == [
        "regime_none",
        "btc_ma20_cash",
        "alt_universe_20d_return_cash",
    ]


def test_regime_none_drawdown_reduction_is_exactly_zero():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())
    baseline = next(item for item in summary["variants"] if item["variant"] == "regime_none")

    assert baseline["performance"]["max_drawdown_vs_v1_reduction_pct"] == 0.0


def test_stageA2_variant_reports_period_and_day_shares():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())
    variant = next(item for item in summary["variants"] if item["variant"] == "btc_ma20_cash")
    regime_filter = variant["regime_filter"]

    assert 0.0 <= regime_filter["cash_rebalance_period_share"] <= 1.0
    assert 0.0 <= regime_filter["cash_days_share"] <= 1.0
    assert regime_filter["cash_rebalance_period_share"] == regime_filter["cash_days_share"]
    assert round(regime_filter["cash_days_share"] + regime_filter["alt_exposure_days_share"], 6) == 1.0


def test_stageA2_concentration_reports_abs_pnl_share():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())
    baseline = next(item for item in summary["variants"] if item["variant"] == "regime_none")

    assert "max_single_symbol_abs_pnl_share" in baseline["concentration"]
    assert "max_single_month_abs_pnl_share" in baseline["concentration"]


def test_stageA2_universe_equal_weight_benchmark_is_not_regime_none_top10():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())
    baseline = next(item for item in summary["variants"] if item["variant"] == "regime_none")

    assert round(baseline["benchmarks"]["universe_equal_weight_pct"], 8) != round(
        baseline["performance"]["base_30bps_total_return_pct"], 8
    )


def test_benchmark_uses_first_rebalance_open_and_last_exit_open():
    rows = _synthetic_rows()
    summary = run_stageA2_regime_cash_fallback_diagnostic(rows)

    assert summary["benchmark_price_policy"] == "first_rebalance_open_to_last_valid_exit_open"


def test_stageA2_top_level_keeps_live_and_paper_disabled():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())

    assert summary["live_usage"] == "not_allowed"
    assert summary["paper_shadow_allowed"] is False
    assert summary["bias_label"] == "survivorship_bias_not_controlled"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA2_backtest.py
```

Expected:

```text
ModuleNotFoundError: No module named 'research.cross_sectional_factor_lab.stageA2'
```

- [ ] **Step 3: Implement `stageA2.py`**

Create `src/research/cross_sectional_factor_lab/stageA2.py` with these public functions and semantics:

```python
from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

import configs.base as cfg
from research.cross_sectional_factor_lab.backtest import (
    apply_turnover_cost,
    compute_strategy_period_return,
    compute_turnover,
    universe_equal_weight_targets,
)
from research.cross_sectional_factor_lab.factors import compute_rebalance_factor_frame
from research.cross_sectional_factor_lab.panel import forward_fill_close_by_symbol, load_daily_panel
from research.cross_sectional_factor_lab.portfolio import build_equal_weight_targets, eligible_monday_rebalance_dates
from research.cross_sectional_factor_lab.regime import AltUniverseRegimeResult, decide_stageA2_regime_exposure
from research.cross_sectional_factor_lab.summary import decide_stageA2_round1, decide_stageA2_variant, summarize_rebalance_quality


def next_weekly_exit_date(rebalance_date: pd.Timestamp) -> pd.Timestamp:
    return rebalance_date + timedelta(days=7)


def compound_returns_pct(returns: list[float]) -> float:
    if not returns:
        return 0.0
    return float(np.prod([1.0 + r for r in returns]) - 1.0) * 100.0


def max_drawdown_pct(returns: list[float]) -> float:
    if not returns:
        return 0.0
    equity = np.array([1.0] + list(np.cumprod([1.0 + r for r in returns])))
    peaks = np.maximum.accumulate(equity)
    drawdowns = np.where(peaks > 0, (peaks - equity) / peaks, 0.0)
    return float(np.max(drawdowns)) * 100.0


def _positive_and_abs_concentration(contributions: dict[str, float]) -> tuple[float, float]:
    positives = [v for v in contributions.values() if v > 0]
    positive_total = sum(positives)
    positive_share = max(positives) / positive_total if positive_total > 0 and positives else 0.0
    absolutes = [abs(v) for v in contributions.values()]
    abs_total = sum(absolutes)
    abs_share = max(absolutes) / abs_total if abs_total > 0 and absolutes else 0.0
    return float(positive_share), float(abs_share)


def _benchmark_open_to_open_net_pct(
    panel: pd.DataFrame,
    symbol: str,
    start_date: pd.Timestamp,
    exit_date: pd.Timestamp,
    round_trip_cost_bps: float = 30.0,
) -> float:
    data = panel[panel["symbol"] == symbol]
    start = data[data["date_utc"] == start_date]
    end = data[data["date_utc"] == exit_date]
    if start.empty or end.empty:
        return 0.0
    gross = (float(end["open"].iloc[0]) / float(start["open"].iloc[0])) - 1.0
    return (gross - round_trip_cost_bps / 10000.0) * 100.0


def _universe_equal_weight_benchmark_pct(panel: pd.DataFrame, rebalance_dates: list[pd.Timestamp]) -> float:
    previous_weights: dict[str, float] = {}
    returns: list[float] = []
    for rebalance_date in rebalance_dates:
        exit_date = next_weekly_exit_date(rebalance_date)
        if panel[panel["date_utc"] == exit_date].empty:
            continue
        factors = compute_rebalance_factor_frame(panel, rebalance_date)
        targets = universe_equal_weight_targets(factors)
        weights = dict(zip(targets["symbol"], targets["target_weight"])) if not targets.empty else {}
        gross_return = compute_strategy_period_return(panel, weights, rebalance_date, exit_date)
        if gross_return is None:
            continue
        turnover = compute_turnover(previous_weights, weights)
        returns.append(apply_turnover_cost(gross_return, turnover, 30.0))
        previous_weights = weights
    return compound_returns_pct(returns)


def _empty_alt_diagnostics() -> dict[str, Any]:
    return {
        "eligible_symbols_count": 0,
        "symbols_with_valid_20d_return": 0,
        "coverage_ratio": 0.0,
        "included_btc_eth": False,
    }


def _alt_diagnostics(result: AltUniverseRegimeResult | None) -> dict[str, Any]:
    if result is None:
        return _empty_alt_diagnostics()
    return {
        "eligible_symbols_count": result.eligible_symbols_count,
        "symbols_with_valid_20d_return": result.symbols_with_valid_20d_return,
        "coverage_ratio": result.coverage_ratio,
        "included_btc_eth": result.included_btc_eth,
    }


def _run_variant(
    panel: pd.DataFrame,
    rebalance_dates: list[pd.Timestamp],
    variant: str,
    baseline_drawdown_pct: float,
    btc_return_pct: float,
    eth_return_pct: float,
    universe_equal_weight_pct: float,
) -> dict[str, Any]:
    previous_weights: dict[str, float] = {}
    returns_30: list[float] = []
    returns_50: list[float] = []
    returns_80: list[float] = []
    exposed_returns: list[float] = []
    cash_returns: list[float] = []
    turnovers: list[float] = []
    selected_counts: list[int] = []
    insufficient_universe_count = 0
    cash_period_count = 0
    symbol_contrib: dict[str, float] = {}
    month_contrib: dict[str, float] = {}
    latest_alt_result: AltUniverseRegimeResult | None = None

    for rebalance_date in rebalance_dates:
        exit_date = next_weekly_exit_date(rebalance_date)
        if panel[panel["date_utc"] == exit_date].empty:
            continue
        factors = compute_rebalance_factor_frame(panel, rebalance_date)
        if len(factors) < cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N:
            insufficient_universe_count += 1
        selected_counts.append(min(len(factors), cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N))

        targets = build_equal_weight_targets(factors, top_n=cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N)
        alt_weights = dict(zip(targets["symbol"], targets["target_weight"])) if not targets.empty else {}
        eligible_symbols = tuple(factors["symbol"].tolist()) if not factors.empty else ()
        is_exposed, alt_result = decide_stageA2_regime_exposure(variant, panel, rebalance_date, eligible_symbols)
        if alt_result is not None:
            latest_alt_result = alt_result
        weights = alt_weights if is_exposed else {}
        if not is_exposed:
            cash_period_count += 1

        gross_return = compute_strategy_period_return(panel, weights, rebalance_date, exit_date)
        if gross_return is None:
            continue
        turnover = compute_turnover(previous_weights, weights)
        turnovers.append(turnover)

        net_30 = apply_turnover_cost(gross_return, turnover, 30.0)
        returns_30.append(net_30)
        returns_50.append(apply_turnover_cost(gross_return, turnover, 50.0))
        returns_80.append(apply_turnover_cost(gross_return, turnover, 80.0))
        if is_exposed:
            exposed_returns.append(net_30)
        else:
            cash_returns.append(net_30)

        month = rebalance_date.strftime("%Y-%m")
        month_contrib[month] = month_contrib.get(month, 0.0) + net_30
        for symbol, weight in weights.items():
            symbol_contrib[symbol] = symbol_contrib.get(symbol, 0.0) + net_30 * weight
        previous_weights = weights

    total_30 = compound_returns_pct(returns_30)
    dd = max_drawdown_pct(returns_30)
    if variant == "regime_none":
        dd_reduction = 0.0
    else:
        dd_reduction = ((baseline_drawdown_pct - dd) / baseline_drawdown_pct * 100.0) if baseline_drawdown_pct > 0 else 0.0
    cash_share = float(cash_period_count / len(returns_30)) if returns_30 else 0.0
    symbol_pos, symbol_abs = _positive_and_abs_concentration(symbol_contrib)
    month_pos, month_abs = _positive_and_abs_concentration(month_contrib)

    summary = {
        "variant": variant,
        "regime_filter": {
            "filtered_rebalance_share": cash_share,
            "cash_rebalance_period_share": cash_share,
            "alt_exposure_rebalance_period_share": 1.0 - cash_share if returns_30 else 0.0,
            "cash_days_share": cash_share,
            "alt_exposure_days_share": 1.0 - cash_share if returns_30 else 0.0,
            "strategy_return_when_exposed": compound_returns_pct(exposed_returns),
            "strategy_return_when_cash": compound_returns_pct(cash_returns),
            "mostly_cash_strategy": cash_share > cfg.FACTOR_LAB_STAGEA2_MAX_CASH_DAYS_SHARE,
        },
        "alt_universe_regime_diagnostics": _alt_diagnostics(latest_alt_result),
        "performance": {
            "base_30bps_total_return_pct": total_30,
            "stress_50bps_total_return_pct": compound_returns_pct(returns_50),
            "crash_80bps_total_return_pct": compound_returns_pct(returns_80),
            "max_drawdown_pct": dd,
            "max_drawdown_vs_v1_reduction_pct": dd_reduction,
            "turnover_median": float(np.median(turnovers)) if turnovers else 0.0,
        },
        "benchmarks": {
            "btc_buy_and_hold_net_pct": btc_return_pct,
            "eth_buy_and_hold_net_pct": eth_return_pct,
            "universe_equal_weight_pct": universe_equal_weight_pct,
            "vs_btc_total_return_pct": total_30 - btc_return_pct,
            "vs_eth_total_return_pct": total_30 - eth_return_pct,
            "vs_universe_equal_weight_total_return_pct": total_30 - universe_equal_weight_pct,
        },
        "concentration": {
            "max_single_symbol_positive_pnl_share": symbol_pos,
            "max_single_symbol_abs_pnl_share": symbol_abs,
            "max_single_month_positive_pnl_share": month_pos,
            "max_single_month_abs_pnl_share": month_abs,
        },
        "rebalance_quality": summarize_rebalance_quality(len(returns_30), insufficient_universe_count, selected_counts, turnovers),
    }
    summary["decision"] = decide_stageA2_variant(summary)
    return summary


def run_stageA2_regime_cash_fallback_diagnostic(daily_bars: list[dict]) -> dict[str, Any]:
    base = {
        "run_mode": "stageA2_regime_cash_fallback_diagnostic",
        "scope": "regime_cash_fallback_only",
        "live_usage": "not_allowed",
        "paper_shadow_allowed": False,
        "bias_label": "survivorship_bias_not_controlled",
        "benchmark_price_policy": "first_rebalance_open_to_last_valid_exit_open",
        "period_share_note": "weekly_equal_length_periods_make_period_share_equal_day_share_in_round1",
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
    }
    if not daily_bars:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": "empty_daily_bars", "variants": []}
    try:
        panel = load_daily_panel(daily_bars)
    except Exception as exc:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": f"load_panel_failed: {exc}", "variants": []}
    if panel.empty:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": "empty_daily_bars", "variants": []}

    panel, ffill_count = forward_fill_close_by_symbol(panel)
    rebalance_dates = eligible_monday_rebalance_dates(panel["date_utc"].unique())
    if not rebalance_dates:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": "insufficient_rebalance_dates", "variants": []}
    valid_exit_dates = [next_weekly_exit_date(dt) for dt in rebalance_dates if not panel[panel["date_utc"] == next_weekly_exit_date(dt)].empty]
    if not valid_exit_dates:
        return {**base, "decision": "stageA2_data_unavailable", "primary_blocker": "no_complete_rebalance_periods", "variants": []}

    start_date = rebalance_dates[0]
    last_exit_date = valid_exit_dates[-1]
    btc_return = _benchmark_open_to_open_net_pct(panel, "BTCUSDT", start_date, last_exit_date)
    eth_return = _benchmark_open_to_open_net_pct(panel, "ETHUSDT", start_date, last_exit_date)
    ew_return = _universe_equal_weight_benchmark_pct(panel, rebalance_dates)

    regime_none = _run_variant(panel, rebalance_dates, "regime_none", 0.0, btc_return, eth_return, ew_return)
    baseline_drawdown = regime_none["performance"]["max_drawdown_pct"]
    variants = [regime_none]
    for variant in ("btc_ma20_cash", "alt_universe_20d_return_cash"):
        variants.append(_run_variant(panel, rebalance_dates, variant, baseline_drawdown, btc_return, eth_return, ew_return))

    round1 = decide_stageA2_round1(variants)
    return {
        **base,
        "decision": "stageA2_round1_completed",
        "primary_blocker": None,
        "ffill_count": ffill_count,
        "variants": variants,
        "winner_variant": round1["winner_variant"],
        "can_enter_stageA2_round2": round1["can_enter_stageA2_round2"],
    }
```

- [ ] **Step 4: Run backtest tests and verify pass**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA2_backtest.py
```

Expected:

```text
11 passed
```

- [ ] **Step 5: Commit Task 4**

```bash
git add src/research/cross_sectional_factor_lab/stageA2.py tests/research/test_cross_sectional_factor_lab_stageA2_backtest.py
git commit -m "feat(factor-lab): add stage A2 regime diagnostic backtest"
```

---

## 8. Task 5: Add Stage A2 CLI

**Files:**

- Create: `scripts/run_factor_lab_stageA2_regime_cash_fallback.py`
- Test: `tests/scripts/test_run_factor_lab_stageA2_regime_cash_fallback.py`

### CLI Contract

Offline mode:

```bash
PYTHONPATH=src uv run python scripts/run_factor_lab_stageA2_regime_cash_fallback.py \
  --offline-sample tests/fixtures/factor_lab/stageA2_sample_payload.json \
  --output reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json
```

Live mode:

```bash
PYTHONPATH=src uv run python scripts/run_factor_lab_stageA2_regime_cash_fallback.py \
  --output reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json
```

`--fail-on-decision` returns non-zero only when:

```text
summary["decision"] != "stageA2_round1_completed"
```

- [ ] **Step 1: Write failing CLI tests**

Create `tests/scripts/test_run_factor_lab_stageA2_regime_cash_fallback.py`:

```python
import json
from pathlib import Path

from scripts.run_factor_lab_stageA2_regime_cash_fallback import main


def test_stageA2_cli_empty_fixture_writes_data_unavailable_summary(tmp_path: Path):
    fixture = tmp_path / "empty.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main(["--offline-sample", str(fixture), "--output", str(output)])

    assert result == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "stageA2_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"
    assert summary["live_usage"] == "not_allowed"


def test_stageA2_cli_fail_on_decision_returns_nonzero_for_unavailable_data(tmp_path: Path):
    fixture = tmp_path / "empty.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main([
        "--offline-sample",
        str(fixture),
        "--output",
        str(output),
        "--fail-on-decision",
    ])

    assert result == 1


def test_stageA2_cli_rejects_unsupported_exchange(tmp_path: Path):
    output = tmp_path / "summary.json"

    result = main(["--exchange", "okx", "--output", str(output)])

    assert result == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "stageA2_data_unavailable"
    assert summary["primary_blocker"] == "unsupported_exchange: okx"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_run_factor_lab_stageA2_regime_cash_fallback.py
```

Expected:

```text
ModuleNotFoundError: No module named 'scripts.run_factor_lab_stageA2_regime_cash_fallback'
```

- [ ] **Step 3: Create CLI script**

Create `scripts/run_factor_lab_stageA2_regime_cash_fallback.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import ccxt
from loguru import logger

from research.cross_sectional_factor_lab.stageA2 import run_stageA2_regime_cash_fallback_diagnostic
from research.cross_sectional_factor_lab.universe import filter_stage0_universe, normalize_symbol
from scripts.run_factor_lab_stageA_v1_momentum import get_ccxt_symbol, parse_binance_spot_klines_to_daily_bars


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Factor Lab Stage A2 regime/cash fallback diagnostic.")
    parser.add_argument("--offline-sample", help="Path to offline daily bars JSON fixture")
    parser.add_argument("--output", required=True, help="Path to write summary JSON")
    parser.add_argument("--history-days", type=int, default=540, help="Required history days")
    parser.add_argument("--exchange", default="binance", help="Exchange ID; only binance is supported")
    parser.add_argument("--max-symbols", type=int, help="Optional maximum eligible symbols for live fetch")
    parser.add_argument("--fail-on-decision", action="store_true", help="Return non-zero if diagnostic cannot complete")
    return parser.parse_args(argv)


def _unavailable_summary(market: str, blocker: str) -> dict[str, Any]:
    return {
        "run_mode": "stageA2_regime_cash_fallback_diagnostic",
        "scope": "regime_cash_fallback_only",
        "market": market,
        "bias_label": "survivorship_bias_not_controlled",
        "live_usage": "not_allowed",
        "paper_shadow_allowed": False,
        "decision": "stageA2_data_unavailable",
        "primary_blocker": blocker,
        "variants": [],
        "winner_variant": None,
        "can_enter_stageA2_round2": False,
    }


def write_summary(summary: dict[str, Any], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fetch_live_binance_daily_bars(args: argparse.Namespace) -> list[dict[str, Any]]:
    client = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})
    client.load_markets()
    spot_symbols = [m["symbol"] for m in client.markets.values() if m["active"] and m["spot"] and m.get("quote") == "USDT"]
    audit = filter_stage0_universe(spot_symbols)
    eligible = list(audit.eligible_symbols)
    if args.max_symbols:
        eligible = eligible[: args.max_symbols]
    since_ms = client.milliseconds() - (args.history_days + 35) * 86400 * 1000
    daily_bars: list[dict[str, Any]] = []
    for idx, normalized in enumerate(eligible):
        ccxt_symbol = get_ccxt_symbol(client, normalize_symbol(normalized))
        if not ccxt_symbol:
            logger.warning(f"Could not map symbol {normalized} to CCXT")
            continue
        logger.info(f"[{idx + 1}/{len(eligible)}] Fetching {normalized}")
        klines = client.publicGetKlines({"symbol": normalize_symbol(normalized), "interval": "1d", "startTime": since_ms, "limit": 1000})
        daily_bars.extend(parse_binance_spot_klines_to_daily_bars(normalized, klines))
        time.sleep(0.1)
    return daily_bars


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.offline_sample:
        try:
            fixture = json.loads(Path(args.offline_sample).read_text(encoding="utf-8"))
        except Exception as exc:
            summary = _unavailable_summary("binance_spot", f"read_fixture_failed: {exc}")
            write_summary(summary, args.output)
            return 1 if args.fail_on_decision else 0
        summary = run_stageA2_regime_cash_fallback_diagnostic(fixture.get("daily_bars", []))
    else:
        if args.exchange.lower() != "binance":
            summary = _unavailable_summary(f"{args.exchange}_spot", f"unsupported_exchange: {args.exchange}")
            write_summary(summary, args.output)
            return 1 if args.fail_on_decision else 0
        try:
            summary = run_stageA2_regime_cash_fallback_diagnostic(_fetch_live_binance_daily_bars(args))
        except Exception as exc:
            summary = _unavailable_summary("binance_spot", f"live_fetch_failed: {exc}")
    write_summary(summary, args.output)
    logger.info(f"Summary written to {args.output}")
    logger.info(f"Decision: {summary.get('decision')}")
    if args.fail_on_decision and summary.get("decision") != "stageA2_round1_completed":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run CLI tests and verify pass**

Run:

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_run_factor_lab_stageA2_regime_cash_fallback.py
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit Task 5**

```bash
git add scripts/run_factor_lab_stageA2_regime_cash_fallback.py tests/scripts/test_run_factor_lab_stageA2_regime_cash_fallback.py
git commit -m "feat(factor-lab): add stage A2 regime diagnostic CLI"
```

---

## 9. Task 6: Run Stage A2 Diagnostic And Write Review

**Files:**

- Generate: `reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json`
- Create: `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-regime-cash-fallback-review_CN.md`

- [ ] **Step 1: Run live Stage A2 diagnostic**

Run:

```bash
PYTHONPATH=src uv run python scripts/run_factor_lab_stageA2_regime_cash_fallback.py \
  --output reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json
```

Expected:

```text
Summary written to reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json
Decision: stageA2_round1_completed
```

- [ ] **Step 2: Inspect summary decision fields**

Run:

```bash
jq '{decision, winner_variant, can_enter_stageA2_round2, live_usage, paper_shadow_allowed, bias_label, benchmark_price_policy}' \
  reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json
```

Expected shape:

```json
{
  "decision": "stageA2_round1_completed",
  "winner_variant": null,
  "can_enter_stageA2_round2": false,
  "live_usage": "not_allowed",
  "paper_shadow_allowed": false,
  "bias_label": "survivorship_bias_not_controlled",
  "benchmark_price_policy": "first_rebalance_open_to_last_valid_exit_open"
}
```

`winner_variant` and `can_enter_stageA2_round2` depend on measured results; do not force them.

- [ ] **Step 3: Inspect variant table**

Run:

```bash
jq '.variants[] | {
  variant,
  decision,
  rebalances: .rebalance_quality.rebalance_count,
  cash_period_share: .regime_filter.cash_rebalance_period_share,
  cash_days_share: .regime_filter.cash_days_share,
  total_return_30bps: .performance.base_30bps_total_return_pct,
  max_drawdown: .performance.max_drawdown_pct,
  drawdown_reduction: .performance.max_drawdown_vs_v1_reduction_pct,
  vs_btc: .benchmarks.vs_btc_total_return_pct,
  vs_eth: .benchmarks.vs_eth_total_return_pct,
  vs_ew: .benchmarks.vs_universe_equal_weight_total_return_pct,
  max_month_positive_share: .concentration.max_single_month_positive_pnl_share,
  max_month_abs_share: .concentration.max_single_month_abs_pnl_share,
  alt_coverage: .alt_universe_regime_diagnostics.coverage_ratio
}' reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json
```

Expected: three JSON objects for `regime_none`, `btc_ma20_cash`, `alt_universe_20d_return_cash`.

- [ ] **Step 4: Generate review document from measured summary**

Run:

```bash
PYTHONPATH=src uv run python - <<'PY'
import json
from pathlib import Path

summary_path = Path("reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json")
review_path = Path("docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-regime-cash-fallback-review_CN.md")
summary = json.loads(summary_path.read_text(encoding="utf-8"))

def pct(value):
    return f"{float(value):.2f}%"

def classify_failure(summary):
    if summary.get("decision") != "stageA2_round1_completed":
        return "data_failure", summary.get("primary_blocker", "diagnostic_not_completed")
    variants = summary.get("variants", [])
    if any(v.get("decision") == "regime_filter_data_insufficient" for v in variants):
        return "data_failure", "rebalance_count_below_stageA2_minimum"
    if not variants:
        return "data_failure", "missing_variant_results"
    if not summary.get("can_enter_stageA2_round2"):
        reasons = []
        for item in variants:
            if item["variant"] == "regime_none":
                continue
            if item["performance"]["max_drawdown_vs_v1_reduction_pct"] < 30.0:
                reasons.append(f"{item['variant']}:drawdown_reduction_insufficient")
            if item["benchmarks"]["vs_universe_equal_weight_total_return_pct"] <= 0:
                reasons.append(f"{item['variant']}:no_excess_vs_universe_equal_weight")
            if item["regime_filter"]["cash_days_share"] > 0.60:
                reasons.append(f"{item['variant']}:mostly_cash")
        return "structure_failure", ", ".join(reasons) if reasons else "no_promising_regime_variant"
    return "confirmed_next_action", "enter_stageA2_round2_design_gate_only"

failure_type, failure_reason = classify_failure(summary)
rows = []
for item in summary.get("variants", []):
    rows.append(
        "| {variant} | {decision} | {rebalance} | {ret} | {dd} | {dd_red} | {cash} | {vs_btc} | {vs_eth} | {vs_ew} |".format(
            variant=item["variant"],
            decision=item["decision"],
            rebalance=item["rebalance_quality"]["rebalance_count"],
            ret=pct(item["performance"]["base_30bps_total_return_pct"]),
            dd=pct(item["performance"]["max_drawdown_pct"]),
            dd_red=pct(item["performance"]["max_drawdown_vs_v1_reduction_pct"]),
            cash=pct(item["regime_filter"]["cash_days_share"] * 100.0),
            vs_btc=pct(item["benchmarks"]["vs_btc_total_return_pct"]),
            vs_eth=pct(item["benchmarks"]["vs_eth_total_return_pct"]),
            vs_ew=pct(item["benchmarks"]["vs_universe_equal_weight_total_return_pct"]),
        )
    )

if summary.get("can_enter_stageA2_round2"):
    next_step = "允许写 Stage A2 Round 2 design；第一优先级为 3d rebalance diagnostic，但仍不得接 live 或 paper shadow。"
else:
    next_step = "暂停 Stage A exchange-only momentum line 的扩展；先做 closure decision：1. 是否执行 A2.2 3d diagnostic；2. 是否转向 B-lite 非价格因子可行性；3. 是否关闭当前 Factor Lab 路线。"

review = f"""# Cross-Sectional Factor Lab Stage A2 Regime/Cash Fallback Review

**日期**：2026-06-10  
**阶段**：Stage A2 Round 1  
**范围**：regime_cash_fallback_only  
**输入报告**：reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json  
**实盘状态**：live_usage = {summary.get('live_usage')}；paper_shadow_allowed = {summary.get('paper_shadow_allowed')}  

## 1. 结论

- `decision`: `{summary.get('decision')}`
- `winner_variant`: `{summary.get('winner_variant')}`
- `can_enter_stageA2_round2`: `{summary.get('can_enter_stageA2_round2')}`
- `failure_type`: `{failure_type}`
- `failure_reason`: `{failure_reason}`

## 2. 三组变体结果

| variant | decision | rebalances | 30bps return | max DD | DD reduction | cash days | vs BTC | vs ETH | vs EW |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

## 3. 失效类型与归因

- `data_failure`: 数据不足、有效 rebalance 数不足、诊断未完成。
- `density_failure`: 本轮不适用；Stage A2 不是事件密度研究。
- `structure_failure`: regime filter 未能同时降低回撤、保持相对 benchmark 表现、避免 mostly-cash。
- `execution_cost_failure`: 若 30/50/80 bps 成本场景下改善只在低成本成立，应归入该类。
- `confirmed_next_action`: 只有 `can_enter_stageA2_round2 = true` 时成立。

本次归类：`{failure_type}`，原因：`{failure_reason}`。

## 4. 口径说明

- benchmark 使用 `{summary.get('benchmark_price_policy')}`。
- Stage A2 Round 1 是 weekly equal-length period，因此 `cash_rebalance_period_share` 与 `cash_days_share` 等价。
- 当前 universe 仍是 current tradable universe，存在 survivorship bias。
- 结果不能进入实盘，不能作为 paper shadow 准入依据。

## 5. 下一步

{next_step}
"""

review_path.parent.mkdir(parents=True, exist_ok=True)
review_path.write_text(review, encoding="utf-8")
print(f"Written: {review_path}")
PY
```

Expected:

```text
Written: docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-regime-cash-fallback-review_CN.md
```

- [ ] **Step 5: Commit Task 6**

```bash
git add reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-regime-cash-fallback-review_CN.md
git commit -m "research(factor-lab): record stage A2 regime diagnostic"
```

---

## 10. Task 7: Full Verification

- [ ] **Step 1: Run focused Stage A2 tests**

```bash
PYTHONPATH=src uv run pytest -q \
  tests/test_factor_lab_stageA2_config.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_regime.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_summary.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_backtest.py \
  tests/scripts/test_run_factor_lab_stageA2_regime_cash_fallback.py
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 2: Run Stage A regression tests**

```bash
PYTHONPATH=src uv run pytest -q \
  tests/research/test_cross_sectional_factor_lab_stage0_*.py \
  tests/research/test_cross_sectional_factor_lab_stageA*.py \
  tests/scripts/test_run_factor_lab_stageA_v1_momentum.py \
  tests/scripts/test_run_factor_lab_stageA2_regime_cash_fallback.py
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 3: Run ruff on changed files**

```bash
uv run ruff check \
  configs/base.py \
  src/research/cross_sectional_factor_lab/regime.py \
  src/research/cross_sectional_factor_lab/stageA2.py \
  src/research/cross_sectional_factor_lab/summary.py \
  scripts/run_factor_lab_stageA2_regime_cash_fallback.py \
  tests/test_factor_lab_stageA2_config.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_regime.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_summary.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_backtest.py \
  tests/scripts/test_run_factor_lab_stageA2_regime_cash_fallback.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 4: Run full test suite**

```bash
PYTHONPATH=src uv run pytest -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 5: Confirm git status is clean after final commit**

```bash
git status --short
```

Expected:

```text
(no output)
```

---

## 11. Completion Criteria

This plan is complete only when all are true:

```text
Stage A2 config constants are in configs/base.py.
Regime functions use only t-1 and earlier data.
Alt universe regime has coverage gate and min valid symbol gate.
Unknown variants raise ValueError.
Cash periods earn zero gross return and still pay transition turnover cost.
Benchmark uses open-to-open price policy.
regime_none drawdown reduction is exactly 0.0.
Variant decision includes rebalance_count >= 50 gate.
Summary includes period shares and day shares.
Summary includes positive and abs concentration shares.
Summary includes failure taxonomy in review.
CLI writes reports/cross_sectional_factor_lab/stageA2_regime_cash_fallback_summary.json.
Focused tests pass.
Stage A regression tests pass.
Ruff passes on changed files.
Full pytest passes.
No live or paper trading path is enabled.
```
