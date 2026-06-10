# Cross-Sectional Factor Lab Stage A2.2 CMOM Diagnostic Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Stage A2.2 `14d CMOM vs 30d momentum` 诊断，判断论文式 two-week crypto momentum 是否明显优于当前 Stage A v1 的 30d momentum。

**Architecture:** 复用现有 Factor Lab Stage A 的 panel、portfolio、cost、benchmark 和数据下载逻辑；新增可配置 factor variant 回测路径，而不是复制整套 v1 backtest。A2.2 输出独立 summary/review，且只能给出 diagnostic next action，不允许产生 live-safe 或 paper-shadow 结论。

**Tech Stack:** Python 3.11, pandas, numpy, ccxt, pytest, ruff, existing `src/research/cross_sectional_factor_lab/*` modules.

---

## 0. 边界与当前事实

### 0.1 前置事实

已冻结结论：

```text
Stage A1: 30d momentum top10 weekly long-only failed.
Stage A2.1: regime/cash fallback reduces damage but no alpha.
```

A2.2 只回答：

```text
cmom_14d_skip_1d 是否明显优于 momentum_30d_skip_1d？
```

### 0.2 严禁范围扩张

本计划不允许实现：

```text
3d rebalance
BTC/alt regime filter
volume confirmation
volatility-adjusted momentum
funding/OI veto
on-chain factor
LightGBM
core-satellite portfolio
live scanner
paper shadow
```

### 0.3 完成证据

完成后必须生成：

```text
reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json
docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md
```

并运行：

```bash
PYTHONPATH=src uv run pytest -q tests/test_factor_lab_stageA2_cmom_config.py \
  tests/research/test_cross_sectional_factor_lab_cmom_factors.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_summary.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py \
  tests/scripts/test_run_factor_lab_stageA2_cmom_diagnostic.py

uv run ruff check configs/base.py \
  src/research/cross_sectional_factor_lab/factors.py \
  src/research/cross_sectional_factor_lab/backtest.py \
  src/research/cross_sectional_factor_lab/summary.py \
  scripts/run_factor_lab_stageA2_cmom_diagnostic.py \
  tests/test_factor_lab_stageA2_cmom_config.py \
  tests/research/test_cross_sectional_factor_lab_cmom_factors.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_summary.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py \
  tests/scripts/test_run_factor_lab_stageA2_cmom_diagnostic.py

PYTHONPATH=src uv run pytest -q
```

---

## Task 1: Add Stage A2.2 CMOM Config Constants

**Files:**
- Modify: `configs/base.py`
- Create: `tests/test_factor_lab_stageA2_cmom_config.py`

**Step 1: Write failing config tests**

Create `tests/test_factor_lab_stageA2_cmom_config.py`:

```python
import configs.base as cfg


def test_factor_lab_stageA2_cmom_config_exists() -> None:
    assert cfg.FACTOR_LAB_STAGEA2_CMOM_LOOKBACK_DAYS == 14
    assert cfg.FACTOR_LAB_STAGEA2_CMOM_SKIP_RECENT_DAYS == 1
    assert cfg.FACTOR_LAB_STAGEA2_CMOM_MIN_RETURN_DIFF_PCT == 10.0
    assert cfg.FACTOR_LAB_STAGEA2_CMOM_MAX_BTC_UNDERPERFORMANCE_PCT == 10.0


def test_factor_lab_stageA2_cmom_keeps_live_disabled() -> None:
    assert cfg.FACTOR_LAB_STAGEA2_CMOM_LIVE_SAFE is False
    assert cfg.FACTOR_LAB_STAGEA2_CMOM_PAPER_SHADOW_ALLOWED is False
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=src uv run pytest -q tests/test_factor_lab_stageA2_cmom_config.py
```

Expected: FAIL with missing config attributes.

**Step 3: Add minimal config**

Append near existing Stage A2 constants in `configs/base.py`:

```python
# Stage A2.2 CMOM diagnostic constants.
FACTOR_LAB_STAGEA2_CMOM_LOOKBACK_DAYS = 14
FACTOR_LAB_STAGEA2_CMOM_SKIP_RECENT_DAYS = 1
FACTOR_LAB_STAGEA2_CMOM_MIN_RETURN_DIFF_PCT = 10.0
FACTOR_LAB_STAGEA2_CMOM_MAX_BTC_UNDERPERFORMANCE_PCT = 10.0
FACTOR_LAB_STAGEA2_CMOM_LIVE_SAFE = False
FACTOR_LAB_STAGEA2_CMOM_PAPER_SHADOW_ALLOWED = False
FACTOR_LAB_STAGEA2_CMOM_VARIANTS = (
    "momentum_30d_skip_1d",
    "cmom_14d_skip_1d",
)
```

Do not change Stage A v1 thresholds.

**Step 4: Run test to verify it passes**

```bash
PYTHONPATH=src uv run pytest -q tests/test_factor_lab_stageA2_cmom_config.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add configs/base.py tests/test_factor_lab_stageA2_cmom_config.py
git commit -m "test(factor-lab): add stage A2 CMOM config contract"
```

---

## Task 2: Add 14d CMOM Factor With Absolute-Date Semantics

**Files:**
- Modify: `src/research/cross_sectional_factor_lab/factors.py`
- Create: `tests/research/test_cross_sectional_factor_lab_cmom_factors.py`

**Step 1: Write failing factor tests**

Create `tests/research/test_cross_sectional_factor_lab_cmom_factors.py`:

```python
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from research.cross_sectional_factor_lab.factors import (
    compute_cmom_14d_skip_1d,
    compute_rebalance_factor_frame,
)


def _rows(symbol: str, start: date, closes: list[float]) -> list[dict]:
    rows = []
    for i, close in enumerate(closes):
        dt = start + timedelta(days=i)
        rows.append({
            "symbol": symbol,
            "date_utc": pd.Timestamp(dt),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "base_volume": 1_000_000.0,
            "quote_volume": 50_000_000.0,
        })
    return rows


def test_cmom_14d_skip_1d_uses_t_minus_1_and_t_minus_15() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 15 + [150.0, 999.0]
    panel = pd.DataFrame(_rows("AAAUSDT", start, closes))

    rebalance_date = pd.Timestamp("2026-01-17")

    assert panel.loc[panel["date_utc"] == pd.Timestamp("2026-01-16"), "close"].item() == 150.0
    assert panel.loc[panel["date_utc"] == pd.Timestamp("2026-01-17"), "close"].item() == 999.0

    result = compute_cmom_14d_skip_1d(panel, "AAAUSDT", rebalance_date)

    assert result == 0.5


def test_cmom_14d_skip_1d_does_not_use_rebalance_day_close() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 15 + [100.0, 10_000.0]
    panel = pd.DataFrame(_rows("AAAUSDT", start, closes))

    result = compute_cmom_14d_skip_1d(panel, "AAAUSDT", pd.Timestamp("2026-01-17"))

    assert result == 0.0


def test_cmom_14d_requires_complete_absolute_daily_lookback() -> None:
    start = date(2026, 1, 1)
    rows = _rows("AAAUSDT", start, [100.0] * 17)
    rows = [row for row in rows if row["date_utc"] != pd.Timestamp("2026-01-08")]
    panel = pd.DataFrame(rows)

    result = compute_cmom_14d_skip_1d(panel, "AAAUSDT", pd.Timestamp("2026-01-17"))

    assert result is None


def test_rebalance_factor_frame_can_compute_cmom_variant() -> None:
    start = date(2026, 1, 1)
    # Need 31+ days so existing 30d liquidity/momentum infrastructure can coexist.
    rows = _rows("AAAUSDT", start, [100.0] * 20 + [120.0] * 20)
    panel = pd.DataFrame(rows)

    factors = compute_rebalance_factor_frame(
        panel,
        pd.Timestamp("2026-02-05"),
        factor_name="cmom_14d_skip_1d",
    )

    assert "cmom_14d_skip_1d" in factors.columns
    assert "momentum_30d_skip_1d" not in factors.columns
    assert len(factors) == 1
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_cmom_factors.py
```

Expected: FAIL because `compute_cmom_14d_skip_1d` and `factor_name` support do not exist.

**Step 3: Implement minimal factor support**

Modify `src/research/cross_sectional_factor_lab/factors.py`:

1. Add `compute_cmom_14d_skip_1d(panel, symbol, rebalance_date)` using:

```text
signal_asof_date = rebalance_date - 1 day
lookback_start_date = rebalance_date - 15 days
expected_days = 15
```

2. Extract shared helper if useful:

```python
def _compute_skip_return(panel, symbol, rebalance_date, lookback_days, skip_days) -> float | None:
    ...
```

3. Extend `compute_rebalance_factor_frame` signature:

```python
def compute_rebalance_factor_frame(
    panel: pd.DataFrame,
    rebalance_date: pd.Timestamp,
    *,
    factor_name: str = "momentum_30d_skip_1d",
) -> pd.DataFrame:
```

4. Allow only:

```python
if factor_name == "momentum_30d_skip_1d":
    value = compute_momentum_30d_skip_1d(...)
elif factor_name == "cmom_14d_skip_1d":
    value = compute_cmom_14d_skip_1d(...)
else:
    raise ValueError(f"unsupported factor_name: {factor_name}")
```

5. Preserve Stage A v1 default behavior exactly.

**Step 4: Run focused tests**

```bash
PYTHONPATH=src uv run pytest -q \
  tests/research/test_cross_sectional_factor_lab_cmom_factors.py \
  tests/research/test_cross_sectional_factor_lab_stageA_factors.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/cross_sectional_factor_lab/factors.py \
  tests/research/test_cross_sectional_factor_lab_cmom_factors.py
git commit -m "feat(factor-lab): add 14d CMOM factor diagnostic"
```

---

## Task 3: Extract Reusable Factor-Variant Backtest Summary

**Files:**
- Modify: `src/research/cross_sectional_factor_lab/backtest.py`
- Test: `tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py`

**Step 1: Write failing reusable backtest tests**

Create `tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py`:

```python
from __future__ import annotations

from datetime import date, timedelta

from research.cross_sectional_factor_lab.backtest import run_stageA2_cmom_diagnostic


def _synthetic_panel(symbols: int = 12, days: int = 100) -> list[dict]:
    rows = []
    start = date(2026, 1, 1)
    for s in range(symbols):
        symbol = f"S{s:02d}USDT"
        for i in range(days):
            dt = start + timedelta(days=i)
            price = 100.0 + i + s
            rows.append({
                "symbol": symbol,
                "date_utc": dt.isoformat(),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "base_volume": 1_000_000.0,
                "quote_volume": 50_000_000.0,
            })
    return rows


def test_run_stageA2_cmom_diagnostic_returns_required_summary_shape() -> None:
    summary = run_stageA2_cmom_diagnostic(_synthetic_panel())

    assert summary["stage"] == "stageA2_cmom_diagnostic"
    assert summary["live_usage"] == "not_allowed"
    assert summary["paper_shadow_allowed"] is False
    assert "momentum_30d_skip_1d" in summary["factor_variants"]
    assert "cmom_14d_skip_1d" in summary["factor_variants"]
    assert "primary_comparison" in summary
    assert summary["can_promote_strategy"] is False


def test_run_stageA2_cmom_diagnostic_empty_rows_returns_data_unavailable() -> None:
    summary = run_stageA2_cmom_diagnostic([])

    assert summary["decision"] == "stageA2_cmom_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"
    assert summary["live_usage"] == "not_allowed"
    assert summary["paper_shadow_allowed"] is False


def test_stageA2_cmom_uses_same_benchmark_for_both_variants() -> None:
    rows = _synthetic_panel()
    summary = run_stageA2_cmom_diagnostic(rows)

    mom = summary["factor_variants"]["momentum_30d_skip_1d"]
    cmom = summary["factor_variants"]["cmom_14d_skip_1d"]

    assert mom["benchmarks"] == cmom["benchmarks"]


def test_stageA2_cmom_top5_is_diagnostic_only() -> None:
    summary = run_stageA2_cmom_diagnostic(_synthetic_panel())

    cmom = summary["factor_variants"]["cmom_14d_skip_1d"]
    assert "diagnostic_top5_performance" in cmom
    assert summary["decision"] != "strategy_confirmed"
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py
```

Expected: FAIL because `run_stageA2_cmom_diagnostic` does not exist.

**Step 3: Implement reusable backtest path**

Modify `src/research/cross_sectional_factor_lab/backtest.py`:

1. Add internal function:

```python
def _run_factor_variant_backtest(panel: pd.DataFrame, factor_name: str) -> dict:
    ...
```

It should reuse Stage A v1 logic but call:

```python
compute_rebalance_factor_frame(panel, t_i, factor_name=factor_name)
build_equal_weight_targets(factors, top_n=10)
build_equal_weight_targets(factors, top_n=5)
universe_equal_weight_targets(factors)
```

2. Include for each variant:

```json
{
  "factor_name": "cmom_14d_skip_1d",
  "performance": {
    "base_30bps_total_return_pct": ...,
    "stress_50bps_total_return_pct": ...,
    "crash_80bps_total_return_pct": ...,
    "max_drawdown_pct": ...,
    "turnover_median": ...
  },
  "benchmarks": {
    "btc_buy_and_hold_net_pct": ...,
    "eth_buy_and_hold_net_pct": ...,
    "universe_equal_weight_pct": ...,
    "vs_btc_total_return_pct": ...,
    "vs_eth_total_return_pct": ...,
    "vs_universe_equal_weight_total_return_pct": ...
  },
  "concentration": {...},
  "rebalance_quality": {...},
  "diagnostic_top5_performance": {...}
}
```

3. Add public function:

```python
def run_stageA2_cmom_diagnostic(daily_bars: list[dict]) -> dict:
    ...
```

It should:

- return `stageA2_cmom_data_unavailable` for empty/load failure/insufficient rebalance dates;
- load and forward-fill panel exactly like Stage A v1;
- run variants `momentum_30d_skip_1d` and `cmom_14d_skip_1d`;
- call summary decision helper from Task 4;
- always set:

```python
"live_usage": "not_allowed"
"paper_shadow_allowed": False
"can_promote_strategy": False
"bias_label": "survivorship_bias_not_controlled"
```

4. Preserve `run_stageA_v1_backtest` behavior. Do not rewrite it unless extracting shared helpers is necessary and tested.

**Step 4: Run focused tests**

```bash
PYTHONPATH=src uv run pytest -q \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py \
  tests/research/test_cross_sectional_factor_lab_stageA_orchestrator.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/cross_sectional_factor_lab/backtest.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py
git commit -m "feat(factor-lab): add stage A2 CMOM diagnostic backtest"
```

---

## Task 4: Add CMOM Diagnostic Decision Logic

**Files:**
- Modify: `src/research/cross_sectional_factor_lab/summary.py`
- Test: `tests/research/test_cross_sectional_factor_lab_stageA2_cmom_summary.py`

**Step 1: Write failing summary tests**

Create `tests/research/test_cross_sectional_factor_lab_stageA2_cmom_summary.py`:

```python
from __future__ import annotations

from research.cross_sectional_factor_lab.summary import decide_stageA2_cmom


def _variant(return_pct: float, dd: float, vs_btc: float, vs_ew: float, top5_return: float, month_share: float = 0.20) -> dict:
    return {
        "performance": {
            "base_30bps_total_return_pct": return_pct,
            "max_drawdown_pct": dd,
        },
        "benchmarks": {
            "vs_btc_total_return_pct": vs_btc,
            "vs_universe_equal_weight_total_return_pct": vs_ew,
        },
        "diagnostic_top5_performance": {
            "strategy_total_return_pct": top5_return,
        },
        "concentration": {
            "max_single_month_positive_pnl_share": month_share,
        },
    }


def test_stageA2_cmom_proceeds_to_regime_gated_when_all_gates_pass() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-40.0, 50.0, -20.0, 2.0, -45.0),
            "cmom_14d_skip_1d": _variant(-25.0, 45.0, -8.0, 12.0, -26.0),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "proceed_to_regime_gated_cmom_design"
    assert decision["primary_comparison"]["cmom_beats_30d_after_30bps"] is True


def test_stageA2_cmom_runs_3d_failure_diagnostic_when_cmom_improves_but_path_still_bad() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-84.0, 84.0, -44.0, 0.5, -90.0),
            "cmom_14d_skip_1d": _variant(-65.0, 80.0, -25.0, 8.0, -66.0),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "run_3d_failure_diagnostic"


def test_stageA2_cmom_stops_price_only_momentum_when_cmom_does_not_improve() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-84.0, 84.0, -44.0, 0.5, -90.0),
            "cmom_14d_skip_1d": _variant(-82.0, 86.0, -42.0, 1.0, -88.0),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "stop_price_only_momentum"


def test_stageA2_cmom_does_not_promote_when_positive_month_concentration_too_high() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-40.0, 50.0, -20.0, 2.0, -45.0),
            "cmom_14d_skip_1d": _variant(-25.0, 45.0, -8.0, 12.0, -26.0, month_share=0.80),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] != "proceed_to_regime_gated_cmom_design"
```

**Step 2: Run test to verify it fails**

```bash
PYTHONPATH=src uv run pytest -q tests/research/test_cross_sectional_factor_lab_stageA2_cmom_summary.py
```

Expected: FAIL because `decide_stageA2_cmom` does not exist.

**Step 3: Implement decision helper**

Modify `src/research/cross_sectional_factor_lab/summary.py`:

```python
def decide_stageA2_cmom(summary: dict[str, Any]) -> dict[str, Any]:
    mom = summary["factor_variants"]["momentum_30d_skip_1d"]
    cmom = summary["factor_variants"]["cmom_14d_skip_1d"]
    ...
```

Compute:

```python
cmom_vs_30d_return_diff_pct = cmom_return - mom_return
cmom_vs_30d_drawdown_diff_pct = cmom_dd - mom_dd
cmom_vs_30d_vs_universe_ew_diff_pct = cmom_vs_ew - mom_vs_ew
cmom_beats_30d_after_30bps = return_diff >= cfg.FACTOR_LAB_STAGEA2_CMOM_MIN_RETURN_DIFF_PCT
cmom_top5_not_worse_than_top10 = cmom_top5_return >= cmom_return - 5.0
```

Decision:

```python
if all hard gates pass:
    next_action = "proceed_to_regime_gated_cmom_design"
elif cmom_beats_30d_after_30bps and cmom_vs_ew > mom_vs_ew:
    next_action = "run_3d_failure_diagnostic"
else:
    next_action = "stop_price_only_momentum"
```

Hard gates for regime-gated CMOM:

```text
return_diff >= 10 pct points
cmom_dd <= mom_dd
cmom_vs_ew > 0
cmom_vs_btc >= -10
cmom_top5_not_worse_than_top10 == true
cmom_month_share <= 0.30
```

Return:

```python
{
    "decision": "cmom_diagnostic_completed",
    "primary_comparison": {...},
    "next_action": next_action,
}
```

**Step 4: Wire helper into backtest**

In `run_stageA2_cmom_diagnostic`, call:

```python
stage_decision = decide_stageA2_cmom(summary)
summary.update(stage_decision)
```

For data unavailable summaries, do not call this helper.

**Step 5: Run focused tests**

```bash
PYTHONPATH=src uv run pytest -q \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_summary.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/cross_sectional_factor_lab/summary.py \
  src/research/cross_sectional_factor_lab/backtest.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_summary.py
git commit -m "feat(factor-lab): add stage A2 CMOM decision contract"
```

---

## Task 5: Add CLI Runner for Stage A2.2 CMOM Diagnostic

**Files:**
- Create: `scripts/run_factor_lab_stageA2_cmom_diagnostic.py`
- Create: `tests/scripts/test_run_factor_lab_stageA2_cmom_diagnostic.py`

**Step 1: Write failing CLI tests**

Create `tests/scripts/test_run_factor_lab_stageA2_cmom_diagnostic.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_factor_lab_stageA2_cmom_diagnostic import main


def test_stageA2_cmom_cli_empty_fixture_writes_data_unavailable(tmp_path: Path) -> None:
    fixture = tmp_path / "empty.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main(["--offline-sample", str(fixture), "--output", str(output)])

    assert result == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "stageA2_cmom_data_unavailable"
    assert summary["live_usage"] == "not_allowed"
    assert summary["paper_shadow_allowed"] is False


def test_stageA2_cmom_cli_fail_on_decision_returns_nonzero_for_data_unavailable(tmp_path: Path) -> None:
    fixture = tmp_path / "empty.json"
    output = tmp_path / "summary.json"
    fixture.write_text(json.dumps({"daily_bars": []}), encoding="utf-8")

    result = main([
        "--offline-sample", str(fixture),
        "--output", str(output),
        "--fail-on-stop",
    ])

    assert result == 1
```

**Step 2: Run tests to verify they fail**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_run_factor_lab_stageA2_cmom_diagnostic.py
```

Expected: FAIL because script does not exist.

**Step 3: Implement CLI by reusing Stage A v1 data-fetch helpers**

Create `scripts/run_factor_lab_stageA2_cmom_diagnostic.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from research.cross_sectional_factor_lab.backtest import run_stageA2_cmom_diagnostic
from scripts.run_factor_lab_stageA_v1_momentum import (
    get_ccxt_symbol,
    parse_binance_spot_klines_to_daily_bars,
    write_summary,
)
```

Required CLI args:

```text
--offline-sample
--output
--history-days default 540
--exchange default binance
--max-symbols optional
--fail-on-stop optional
```

Implementation requirements:

- Offline mode reads `daily_bars` and calls `run_stageA2_cmom_diagnostic`.
- Live network mode mirrors `run_factor_lab_stageA_v1_momentum.py` but calls `run_stageA2_cmom_diagnostic`.
- `--fail-on-stop` returns non-zero if:

```python
summary.get("next_action") == "stop_price_only_momentum"
summary.get("decision") == "stageA2_cmom_data_unavailable"
```

- Do not add any live trading behavior.

**Step 4: Run CLI tests**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_run_factor_lab_stageA2_cmom_diagnostic.py
```

Expected: PASS.

**Step 5: Run CLI smoke offline**

```bash
cat > /tmp/stageA2_cmom_empty.json <<'JSON'
{"daily_bars": []}
JSON
PYTHONPATH=src uv run python scripts/run_factor_lab_stageA2_cmom_diagnostic.py \
  --offline-sample /tmp/stageA2_cmom_empty.json \
  --output /tmp/stageA2_cmom_summary.json
cat /tmp/stageA2_cmom_summary.json
```

Expected: JSON contains `decision = stageA2_cmom_data_unavailable`.

**Step 6: Commit**

```bash
git add scripts/run_factor_lab_stageA2_cmom_diagnostic.py \
  tests/scripts/test_run_factor_lab_stageA2_cmom_diagnostic.py
git commit -m "feat(factor-lab): add stage A2 CMOM diagnostic runner"
```

---

## Task 6: Run Live Stage A2.2 Diagnostic and Generate Review

**Files:**
- Create: `reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json`
- Create: `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md`

**Step 1: Run live diagnostic**

```bash
PYTHONPATH=src uv run python scripts/run_factor_lab_stageA2_cmom_diagnostic.py \
  --output reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json
```

Expected:

```text
Summary written to reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json
Decision: cmom_diagnostic_completed
```

If network/API fails, do not fake results. Save the failure summary and write review as `data_failure`.

**Step 2: Inspect summary**

```bash
jq '{decision, next_action, primary_comparison, factor_variants: (.factor_variants | keys)}' \
  reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json
```

Expected keys:

```text
momentum_30d_skip_1d
cmom_14d_skip_1d
```

**Step 3: Generate review document**

Create `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` with sections:

```markdown
# Cross-Sectional Factor Lab Stage A2.2 CMOM Diagnostic Review

**日期**：2026-06-10
**阶段**：Stage A2.2
**输入报告**：reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json
**实盘状态**：live_usage = not_allowed；paper_shadow_allowed = false

## 1. 结论

- decision:
- next_action:
- can_promote_strategy: false

## 2. 30d momentum vs 14d CMOM

| factor | 30bps return | max DD | vs BTC | vs ETH | vs EW | top5 return | max month +PnL share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |

## 3. 诊断解释

Explain whether CMOM improved ranking quality or not.

## 4. 失效类型与归因

Use one of:
- data_failure
- structure_failure
- execution_cost_failure
- diagnostic_improvement_without_strategy_confirmation

## 5. 下一步

Use summary.next_action exactly.
```

**Step 4: Commit outputs**

```bash
git add reports/cross_sectional_factor_lab/stageA2_cmom_diagnostic_summary.json \
  docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md
git commit -m "docs(factor-lab): record stage A2 CMOM diagnostic result"
```

---

## Task 7: Final Verification and Cleanup

**Files:**
- Verify only; no expected edits unless tests reveal issues.

**Step 1: Run focused test suite**

```bash
PYTHONPATH=src uv run pytest -q tests/test_factor_lab_stageA2_cmom_config.py \
  tests/research/test_cross_sectional_factor_lab_cmom_factors.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_summary.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py \
  tests/scripts/test_run_factor_lab_stageA2_cmom_diagnostic.py
```

Expected: all pass.

**Step 2: Run Factor Lab regression tests**

```bash
PYTHONPATH=src uv run pytest -q $(rg --files tests | rg 'cross_sectional_factor_lab_stage|run_factor_lab_stageA|factor_lab_stageA' | sort)
```

Expected: all pass.

**Step 3: Run ruff**

```bash
uv run ruff check configs/base.py \
  src/research/cross_sectional_factor_lab/factors.py \
  src/research/cross_sectional_factor_lab/backtest.py \
  src/research/cross_sectional_factor_lab/summary.py \
  scripts/run_factor_lab_stageA2_cmom_diagnostic.py \
  tests/test_factor_lab_stageA2_cmom_config.py \
  tests/research/test_cross_sectional_factor_lab_cmom_factors.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_summary.py \
  tests/research/test_cross_sectional_factor_lab_stageA2_cmom_backtest.py \
  tests/scripts/test_run_factor_lab_stageA2_cmom_diagnostic.py
```

Expected: `All checks passed!`

**Step 4: Run full test suite**

```bash
PYTHONPATH=src uv run pytest -q
```

Expected: all pass.

**Step 5: Check worktree**

```bash
git status --short
```

Expected: clean.

**Step 6: Final handoff**

Report:

```text
- commit hashes
- summary decision
- next_action
- verification commands and pass counts
- whether Stage A2.3 is unlocked
```

Do not claim strategy validity. This is diagnostic only.

---

## Expected Final Interpretation Rules

After implementation, interpret results as follows:

### If `next_action = proceed_to_regime_gated_cmom_design`

Meaning:

```text
14d CMOM appears materially better than 30d momentum, but still not live-safe.
```

Next:

```text
Write Stage A2.3 regime-gated CMOM design.
```

### If `next_action = run_3d_failure_diagnostic`

Meaning:

```text
CMOM improved signal quality, but weekly holding path remains poor.
```

Next:

```text
Write a 3d rebalance diagnostic design, still not pass/fail strategy validation.
```

### If `next_action = stop_price_only_momentum`

Meaning:

```text
Price-only cross-sectional momentum does not provide enough alpha under current constraints.
```

Next:

```text
Pause exchange-only price momentum; decide between B-lite non-price factor feasibility or closing Factor Lab.
```
