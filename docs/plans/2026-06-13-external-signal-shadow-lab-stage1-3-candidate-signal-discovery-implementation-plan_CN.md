# External Signal Shadow Lab Stage 1.3 Candidate Signal Discovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 Stage 1.3 Candidate Signal Discovery：用历史 15m OHLCV 模拟 Gate ticker snapshot，预注册生成少数候选事件，并用随机 baseline / 成本 / 集中度 / 数据覆盖率快速判断 Gate ticker 派生方向是否值得继续。

**Architecture:** 在 `src/research/external_signal_shadow/` 下新增 Stage 1.3 研究模块，不改 execution、risk、strategy、live/paper 路径。流程为：历史 bar panel -> historical snapshot replay -> candidate events -> forward metrics -> random baseline -> summary decision -> review markdown。所有阈值进入 `configs/base.py`，所有候选规则预注册，不做参数搜索。

**Tech Stack:** Python 3.11、标准库、pytest、现有 `configs/base.py`、现有 External Signal Shadow Lab 模块。第一版不引入 pandas / numpy / ccxt / SDK / 网络访问。

---

## 全局约束

- 本计划只实现研究与回放，不接 paper/live。
- 不新增 collector，不联网，不调用 Gate/Binance API。
- 不生成订单、仓位、执行 intent、wallet payload。
- `_CN.md` 文档必须使用中文正文。
- implementation agent 不得自行提交；完成后等待用户确认。
- 所有新增阈值必须集中在 `configs/base.py`，并附注释。
- 所有导入统一使用 `PYTHONPATH=src` 下的 `from research.external_signal_shadow...`，不要使用 `from src.research...` 新增代码。
- `entry_delay_bars=1` 的语义固定为：事件可得后第一根完整 15m bar 的 open 入场；它是 1-based entry candidate，不表示再额外跳过一根完整 bar。
- Fixture run 只能证明 pipeline 可运行，不能证明候选信号有效；真实 Stage 1.3 research 需要 >=90 天历史 bars。

---

## Task 0：确认导入路径与现有状态

**Files:**
- Read: `src/research/external_signal_shadow/`
- Read: `tests/research/external_signal_shadow/`
- Read: `configs/base.py`

**Step 1：运行导入检查**

Run:

```bash
PYTHONPATH=src uv run python - <<'PY'
import importlib
for name in [
    'research.external_signal_shadow.models',
    'research.external_signal_shadow.gate_public_collector',
]:
    mod = importlib.import_module(name)
    print('IMPORT_OK', name, mod.__name__)
PY
```

Expected:

```text
IMPORT_OK research.external_signal_shadow.models ...
IMPORT_OK research.external_signal_shadow.gate_public_collector ...
```

**Step 2：确认工作区**

Run:

```bash
git status --short --branch
```

Expected:

```text
feature/external-signal-shadow-stage1
```

允许存在未提交 docs，但不要覆盖用户改动。

---

## Task 1：新增 Stage 1.3 配置常量

**Files:**
- Modify: `configs/base.py`
- Create: `tests/research/external_signal_shadow/test_stage1_3_config.py`

**Step 1：写失败测试**

Create `tests/research/external_signal_shadow/test_stage1_3_config.py`:

```python
from __future__ import annotations

from configs import base


def test_stage1_3_config_constants_are_registered() -> None:
    assert base.EXTERNAL_SIGNAL_STAGE1_3_VOLUME_SPIKE_THRESHOLD == 3.0
    assert base.EXTERNAL_SIGNAL_STAGE1_3_REL_STRENGTH_Z_THRESHOLD == 1.5
    assert base.EXTERNAL_SIGNAL_STAGE1_3_ROLLING_DAYS == 7
    assert base.EXTERNAL_SIGNAL_STAGE1_3_SAME_HOUR_MIN_SAMPLES == 5
    assert base.EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES == 48
    assert base.EXTERNAL_SIGNAL_STAGE1_3_SNAPSHOT_INTERVAL_MINUTES == 15
    assert base.EXTERNAL_SIGNAL_STAGE1_3_ONE_HOUR_BAR_COUNT == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_PREFERRED == 180
    assert base.EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_MIN == 90
    assert base.EXTERNAL_SIGNAL_STAGE1_3_CONFIGURED_DATA_LAG_MS == 60_000
    assert base.EXTERNAL_SIGNAL_STAGE1_3_ENTRY_DELAY_BARS == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_COUNT == 100
    assert base.EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_DAYS == 20
    assert base.EXTERNAL_SIGNAL_STAGE1_3_MIN_SYMBOLS_WITH_EVENTS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_SYMBOL_EVENT_SHARE == 0.50
    assert base.EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_DAY_EVENT_SHARE == 0.20
    assert base.EXTERNAL_SIGNAL_STAGE1_3_MAX_TOP5_POSITIVE_PNL_SHARE == 0.30
    assert base.EXTERNAL_SIGNAL_STAGE1_3_RANDOM_BASELINE_TRIALS == 500
    assert base.EXTERNAL_SIGNAL_STAGE1_3_RANDOM_SEED == 20260613
    assert base.EXTERNAL_SIGNAL_STAGE1_3_COST_SCENARIOS_ROUND_TRIP_BPS == (30.0, 50.0, 80.0)
    assert base.EXTERNAL_SIGNAL_STAGE1_3_MIN_BAR_COVERAGE_RATIO == 0.98


def test_stage1_3_runtime_boundaries_are_disabled() -> None:
    assert base.RISK_LIVE_TRADING_ENABLED is False
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_config.py -q
```

Expected: FAIL，提示常量不存在。

**Step 3：实现配置常量**

Modify `configs/base.py`，放在 Stage 1.2 配置之后，新增注释清楚的常量：

```python
# ─── External Signal Shadow Lab Stage 1.3 Candidate Discovery ────────────────

EXTERNAL_SIGNAL_STAGE1_3_VOLUME_SPIKE_THRESHOLD = 3.0
# Candidate A volume spike threshold. 3.0 means current 1h quote volume must be
# at least 3x the rolling same-hour median. Research-only; do not tune after results.

EXTERNAL_SIGNAL_STAGE1_3_REL_STRENGTH_Z_THRESHOLD = 1.5
# Candidate B relative-strength threshold in rolling std units. Safe range for
# pre-registered diagnostics: 1.0-2.5. Do not grid-search in Stage 1.3.

EXTERNAL_SIGNAL_STAGE1_3_ROLLING_DAYS = 7
# Rolling historical window length for volume and return baselines.

EXTERNAL_SIGNAL_STAGE1_3_SAME_HOUR_MIN_SAMPLES = 5
# Minimum same-hour historical samples required before volume_spike_1h can emit.

EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES = 48
# Minimum 1h relative-strength samples required before z-threshold evaluation.

EXTERNAL_SIGNAL_STAGE1_3_SNAPSHOT_INTERVAL_MINUTES = 15
# Historical snapshot interval. Matches Stage 1.3 replay granularity, not live cadence.

EXTERNAL_SIGNAL_STAGE1_3_ONE_HOUR_BAR_COUNT = 4
# Number of 15m bars used to construct a complete 1h observation window.

EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_PREFERRED = 180
# Preferred historical replay span. Longer improves event diversity.

EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_MIN = 90
# Minimum historical replay span before Stage 1.3 can run without data warning.

EXTERNAL_SIGNAL_STAGE1_3_CONFIGURED_DATA_LAG_MS = 60_000
# Synthetic availability lag added to historical bar close time to prevent same-bar fills.

EXTERNAL_SIGNAL_STAGE1_3_ENTRY_DELAY_BARS = 1
# Minimum complete 15m bars to wait after candidate event before evaluating entry.

EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_COUNT = 100
# Minimum candidate event count for data sufficiency.

EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_DAYS = 20
# Minimum distinct event days for data sufficiency.

EXTERNAL_SIGNAL_STAGE1_3_MIN_SYMBOLS_WITH_EVENTS = 3
# Minimum distinct symbols with candidate events.

EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_SYMBOL_EVENT_SHARE = 0.50
# Max share of events from one symbol. Prevents single-symbol overfit.

EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_DAY_EVENT_SHARE = 0.20
# Max share of events from one UTC day. Prevents one-day regime overfit.

EXTERNAL_SIGNAL_STAGE1_3_MAX_TOP5_POSITIVE_PNL_SHARE = 0.30
# Max gross profit contribution from top 5 positive events.

EXTERNAL_SIGNAL_STAGE1_3_RANDOM_BASELINE_TRIALS = 500
# Number of random baseline trials. Fixed for comparability.

EXTERNAL_SIGNAL_STAGE1_3_RANDOM_SEED = 20260613
# Fixed seed for reproducible random baseline generation.

EXTERNAL_SIGNAL_STAGE1_3_COST_SCENARIOS_ROUND_TRIP_BPS = (30.0, 50.0, 80.0)
# Round-trip cost scenarios: base, stress, crash. Research-only, not fee advice.

EXTERNAL_SIGNAL_STAGE1_3_MIN_BAR_COVERAGE_RATIO = 0.98
# Minimum 15m bar coverage per symbol before replay can be trusted.
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_config.py -q
```

Expected: PASS。

---

## Task 2：新增历史 bar 模型与 coverage gate

**Files:**
- Create: `src/research/external_signal_shadow/stage1_3_models.py`
- Create: `tests/research/external_signal_shadow/test_stage1_3_models.py`

**Step 1：写失败测试**

Create `tests/research/external_signal_shadow/test_stage1_3_models.py`:

```python
from __future__ import annotations

import pytest

from research.external_signal_shadow.stage1_3_models import HistoricalBar, compute_bar_coverage


MS_15M = 15 * 60 * 1000


def test_historical_bar_requires_complete_positive_ohlcv() -> None:
    bar = HistoricalBar(
        symbol="BTC_USDT",
        bar_start_ms=1_000,
        bar_end_ms=1_000 + MS_15M,
        open_price=100.0,
        high_price=110.0,
        low_price=90.0,
        close_price=105.0,
        quote_volume=1_000_000.0,
    )
    assert bar.symbol == "BTCUSDT"


def test_historical_bar_rejects_invalid_end_time() -> None:
    with pytest.raises(ValueError, match="bar_end_ms"):
        HistoricalBar("BTCUSDT", 1_000, 1_000, 1, 1, 1, 1, 1)


def test_historical_bar_rejects_inconsistent_ohlc() -> None:
    with pytest.raises(ValueError, match="high_price"):
        HistoricalBar("BTCUSDT", 0, MS_15M, 100, 99, 90, 100, 1)
    with pytest.raises(ValueError, match="low_price"):
        HistoricalBar("BTCUSDT", 0, MS_15M, 100, 110, 101, 100, 1)


def test_historical_bar_rejects_wrong_duration() -> None:
    with pytest.raises(ValueError, match="15m duration"):
        HistoricalBar("BTCUSDT", 0, 2 * MS_15M, 100, 100, 100, 100, 1)


def test_bar_coverage_ratio_counts_missing_15m_slots() -> None:
    bars = [
        HistoricalBar("BTCUSDT", 0, MS_15M, 1, 1, 1, 1, 1),
        HistoricalBar("BTCUSDT", MS_15M, 2 * MS_15M, 1, 1, 1, 1, 1),
        HistoricalBar("BTCUSDT", 3 * MS_15M, 4 * MS_15M, 1, 1, 1, 1, 1),
    ]
    coverage = compute_bar_coverage(bars, interval_ms=MS_15M)
    assert coverage["BTCUSDT"] == 0.75
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_models.py -q
```

Expected: FAIL，模块不存在。

**Step 3：实现最小模型**

Create `src/research/external_signal_shadow/stage1_3_models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from research.external_signal_shadow.models import normalize_symbol


STAGE1_3_BAR_INTERVAL_MS = 15 * 60 * 1000


@dataclass(frozen=True)
class HistoricalBar:
    symbol: str
    bar_start_ms: int
    bar_end_ms: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    quote_volume: float

    def __post_init__(self) -> None:
        if self.bar_end_ms <= self.bar_start_ms:
            raise ValueError("bar_end_ms must be greater than bar_start_ms")
        if self.bar_end_ms - self.bar_start_ms != STAGE1_3_BAR_INTERVAL_MS:
            raise ValueError("HistoricalBar must have 15m duration")
        for name in ("open_price", "high_price", "low_price", "close_price"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.high_price < max(self.open_price, self.close_price):
            raise ValueError("high_price must be >= open and close")
        if self.low_price > min(self.open_price, self.close_price):
            raise ValueError("low_price must be <= open and close")
        if self.low_price > self.high_price:
            raise ValueError("low_price must be <= high_price")
        if self.quote_volume < 0:
            raise ValueError("quote_volume must be non-negative")
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol) or "")


def group_bars_by_symbol(bars: list[HistoricalBar]) -> dict[str, list[HistoricalBar]]:
    grouped: dict[str, list[HistoricalBar]] = {}
    for bar in bars:
        grouped.setdefault(bar.symbol, []).append(bar)
    return {symbol: sorted(items, key=lambda item: item.bar_start_ms) for symbol, items in grouped.items()}


def compute_bar_coverage(bars: list[HistoricalBar], *, interval_ms: int) -> dict[str, float]:
    coverage: dict[str, float] = {}
    for symbol, items in group_bars_by_symbol(bars).items():
        if not items:
            coverage[symbol] = 0.0
            continue
        start = items[0].bar_start_ms
        end = items[-1].bar_end_ms
        expected = max(int((end - start) / interval_ms), 1)
        coverage[symbol] = len(items) / expected
    return coverage
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_models.py -q
```

Expected: PASS。

---

## Task 3：实现 Historical Snapshot Replay 时间口径

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_3_models.py`
- Create: `src/research/external_signal_shadow/stage1_3_replay.py`
- Create: `tests/research/external_signal_shadow/test_stage1_3_replay.py`

**Step 1：写失败测试**

Create `tests/research/external_signal_shadow/test_stage1_3_replay.py`:

```python
from __future__ import annotations

from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_replay import (
    build_one_hour_window,
    historical_available_at_ms,
    select_entry_bar,
)

MS_15M = 15 * 60 * 1000


def _bar(i: int, close: float = 100.0, volume: float = 1000.0) -> HistoricalBar:
    return HistoricalBar("BTCUSDT", i * MS_15M, (i + 1) * MS_15M, close, close, close, close, volume)


def test_historical_available_at_uses_bar_close_plus_lag() -> None:
    assert historical_available_at_ms(_bar(3), configured_lag_ms=60_000) == 4 * MS_15M + 60_000


def test_one_hour_window_uses_last_four_completed_15m_bars() -> None:
    bars = [_bar(i, close=100 + i, volume=10 + i) for i in range(6)]
    window = build_one_hour_window(bars, end_index=5, one_hour_bar_count=4)
    assert [bar.bar_start_ms for bar in window] == [2 * MS_15M, 3 * MS_15M, 4 * MS_15M, 5 * MS_15M]
    assert sum(bar.quote_volume for bar in window) == 10 + 2 + 10 + 3 + 10 + 4 + 10 + 5


def test_entry_delay_one_uses_first_complete_bar_after_event() -> None:
    bars = [_bar(i) for i in range(8)]
    event_time = 4 * MS_15M + 60_000
    entry = select_entry_bar(bars, event_time_ms=event_time, entry_delay_bars=1)
    # entry_delay_bars=1 is 1-based: first complete bar after event_time, not skip-one-more-bar.
    assert entry == bars[5]
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_replay.py -q
```

Expected: FAIL，模块/函数不存在。

**Step 3：实现 replay helpers**

Create `src/research/external_signal_shadow/stage1_3_replay.py`:

```python
from __future__ import annotations

from research.external_signal_shadow.stage1_3_models import HistoricalBar


def historical_available_at_ms(bar: HistoricalBar, *, configured_lag_ms: int) -> int:
    return bar.bar_end_ms + configured_lag_ms


def build_one_hour_window(
    bars: list[HistoricalBar],
    *,
    end_index: int,
    one_hour_bar_count: int,
) -> list[HistoricalBar]:
    start = end_index - one_hour_bar_count + 1
    if start < 0:
        return []
    return bars[start : end_index + 1]


def one_hour_quote_volume(window: list[HistoricalBar]) -> float:
    return sum(bar.quote_volume for bar in window)


def one_hour_return(window: list[HistoricalBar]) -> float | None:
    if len(window) < 2:
        return None
    first = window[0].open_price
    last = window[-1].close_price
    if first <= 0:
        return None
    return last / first - 1.0


def select_entry_bar(
    bars: list[HistoricalBar],
    *,
    event_time_ms: int,
    entry_delay_bars: int,
) -> HistoricalBar | None:
    if entry_delay_bars < 1:
        raise ValueError("entry_delay_bars must be >= 1")
    candidates = [bar for bar in bars if bar.bar_start_ms > event_time_ms]
    if len(candidates) < entry_delay_bars:
        return None
    return candidates[entry_delay_bars - 1]
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_replay.py -q
```

Expected: PASS。

---

## Task 4：实现候选事件生成

**Files:**
- Create: `src/research/external_signal_shadow/stage1_3_candidates.py`
- Create: `tests/research/external_signal_shadow/test_stage1_3_candidates.py`

**Step 1：写失败测试**

Create `tests/research/external_signal_shadow/test_stage1_3_candidates.py`:

```python
from __future__ import annotations

from research.external_signal_shadow.stage1_3_candidates import (
    CandidateEvent,
    detect_price_move_15m_baseline,
    detect_relative_strength_vs_btc,
    detect_volume_confirmed_relative_strength,
    detect_volume_spike_1h,
)
from research.external_signal_shadow.stage1_3_models import HistoricalBar

MS_15M = 15 * 60 * 1000


def _bar(symbol: str, i: int, close: float, volume: float) -> HistoricalBar:
    return HistoricalBar(symbol, i * MS_15M, (i + 1) * MS_15M, close, close, close, close, volume)


def test_volume_spike_excludes_current_window_from_same_hour_baseline() -> None:
    # 5 historical same-hour volumes at 100, current 1h volume at 400 => 4x spike.
    historical = [100.0] * 5
    event = detect_volume_spike_1h(
        symbol="ETHUSDT",
        current_1h_quote_volume=400.0,
        same_hour_historical_volumes=historical,
        event_time_ms=10_000,
        threshold=3.0,
        min_samples=5,
    )
    assert isinstance(event, CandidateEvent)
    assert event.candidate_name == "volume_spike_1h"


def test_relative_strength_uses_centered_z_score_without_future_data() -> None:
    event = detect_relative_strength_vs_btc(
        symbol="SOLUSDT",
        alt_1h_return=0.05,
        btc_1h_return=0.00,
        historical_spread_returns=[0.0] * 47 + [0.02],
        event_time_ms=10_000,
        z_threshold=1.5,
        min_samples=48,
    )
    assert event is not None
    assert event.candidate_name == "relative_strength_vs_btc"
    assert "historical_spread_center" in event.metadata
    assert "rolling_sigma" in event.metadata


def test_volume_confirmed_requires_both_conditions_same_window() -> None:
    volume = CandidateEvent("volume_spike_1h", "ETHUSDT", 10_000, "primary", {})
    rel = CandidateEvent("relative_strength_vs_btc", "ETHUSDT", 10_000, "primary", {})
    confirmed = detect_volume_confirmed_relative_strength(volume, rel)
    assert confirmed is not None
    assert confirmed.candidate_name == "volume_confirmed_relative_strength"


def test_price_move_15m_is_baseline_only_and_signed() -> None:
    event = detect_price_move_15m_baseline(
        symbol="DOGEUSDT",
        symbol_15m_return=-0.04,
        historical_15m_returns=[0.0] * 47 + [0.02],
        event_time_ms=10_000,
        z_threshold=1.5,
        min_samples=48,
    )
    assert event is not None
    assert event.candidate_role == "baseline"
    assert event.metadata["trigger_sign"] == -1
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_candidates.py -q
```

Expected: FAIL，模块不存在。

**Step 3：实现候选函数**

Create `src/research/external_signal_shadow/stage1_3_candidates.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median, pstdev
from typing import Any


@dataclass(frozen=True)
class CandidateEvent:
    candidate_name: str
    symbol: str
    event_time_ms: int
    candidate_role: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _safe_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return pstdev(values)


def detect_volume_spike_1h(
    *,
    symbol: str,
    current_1h_quote_volume: float,
    same_hour_historical_volumes: list[float],
    event_time_ms: int,
    threshold: float,
    min_samples: int,
) -> CandidateEvent | None:
    if len(same_hour_historical_volumes) < min_samples:
        return None
    baseline = median(same_hour_historical_volumes)
    if baseline <= 0:
        return None
    ratio = current_1h_quote_volume / baseline
    if ratio < threshold:
        return None
    return CandidateEvent(
        "volume_spike_1h",
        symbol,
        event_time_ms,
        "primary",
        {"volume_ratio": ratio, "baseline_volume": baseline},
    )


def detect_relative_strength_vs_btc(
    *,
    symbol: str,
    alt_1h_return: float,
    btc_1h_return: float,
    historical_spread_returns: list[float],
    event_time_ms: int,
    z_threshold: float,
    min_samples: int,
) -> CandidateEvent | None:
    if symbol.upper() == "BTCUSDT" or len(historical_spread_returns) < min_samples:
        return None
    spread = alt_1h_return - btc_1h_return
    historical_spread_center = median(historical_spread_returns)
    sigma = _safe_std(historical_spread_returns)
    if sigma <= 0:
        return None
    z_score = (spread - historical_spread_center) / sigma
    if z_score < z_threshold:
        return None
    return CandidateEvent(
        "relative_strength_vs_btc",
        symbol,
        event_time_ms,
        "primary",
        {
            "spread_return": spread,
            "historical_spread_center": historical_spread_center,
            "rolling_sigma": sigma,
            "z_score": z_score,
            "evaluation_modes": ("outright_long_alt", "relative_spread_observation"),
        },
    )


def detect_volume_confirmed_relative_strength(
    volume_event: CandidateEvent | None,
    relative_strength_event: CandidateEvent | None,
) -> CandidateEvent | None:
    if volume_event is None or relative_strength_event is None:
        return None
    if volume_event.symbol != relative_strength_event.symbol:
        return None
    if volume_event.event_time_ms != relative_strength_event.event_time_ms:
        return None
    return CandidateEvent(
        "volume_confirmed_relative_strength",
        volume_event.symbol,
        volume_event.event_time_ms,
        "primary",
        {
            "volume_metadata": volume_event.metadata,
            "relative_strength_metadata": relative_strength_event.metadata,
        },
    )


def detect_price_move_15m_baseline(
    *,
    symbol: str,
    symbol_15m_return: float,
    historical_15m_returns: list[float],
    event_time_ms: int,
    z_threshold: float,
    min_samples: int,
) -> CandidateEvent | None:
    if len(historical_15m_returns) < min_samples:
        return None
    sigma = _safe_std(historical_15m_returns)
    if sigma <= 0 or abs(symbol_15m_return) < z_threshold * sigma:
        return None
    return CandidateEvent(
        "price_move_15m",
        symbol,
        event_time_ms,
        "baseline",
        {"trigger_sign": 1 if symbol_15m_return > 0 else -1},
    )
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_candidates.py -q
```

Expected: PASS。

---

## Task 5：实现 forward metrics 与成本场景

**Files:**
- Create: `src/research/external_signal_shadow/stage1_3_metrics.py`
- Create: `tests/research/external_signal_shadow/test_stage1_3_metrics.py`

**Step 1：写失败测试**

Create `tests/research/external_signal_shadow/test_stage1_3_metrics.py`:

```python
from __future__ import annotations

from research.external_signal_shadow.stage1_3_metrics import compute_forward_metrics
from research.external_signal_shadow.stage1_3_models import HistoricalBar

MS_15M = 15 * 60 * 1000


def _bar(i: int, open_price: float, close_price: float, high: float | None = None, low: float | None = None) -> HistoricalBar:
    high_price = max(open_price, close_price) if high is None else high
    low_price = min(open_price, close_price) if low is None else low
    return HistoricalBar("ETHUSDT", i * MS_15M, (i + 1) * MS_15M, open_price, high_price, low_price, close_price, 1_000_000)


def test_forward_metrics_use_entry_delay_and_4h_terminal_return() -> None:
    bars = [_bar(i, 100 + i, 100 + i) for i in range(24)]
    event_time_ms = 4 * MS_15M + 60_000
    metrics = compute_forward_metrics(
        bars,
        event_time_ms=event_time_ms,
        entry_delay_bars=1,
        cost_round_trip_bps=50.0,
        signed_direction=1,
    )
    assert metrics["entry_bar_start_ms"] == 5 * MS_15M
    assert "terminal_return_4h_net_bps" in metrics
    assert metrics["cost_round_trip_bps"] == 50.0


def test_forward_15m_uses_entry_bar_close_not_next_bar_close() -> None:
    bars = [_bar(i, 100.0, 100.0) for i in range(24)]
    bars[5] = _bar(5, 100.0, 101.0)
    bars[6] = _bar(6, 100.0, 150.0)
    metrics = compute_forward_metrics(
        bars,
        event_time_ms=4 * MS_15M + 60_000,
        entry_delay_bars=1,
        cost_round_trip_bps=0.0,
        signed_direction=1,
    )
    assert round(metrics["forward_return_15m_net_bps"], 6) == 100.0


def test_mfe_mae_use_high_low_not_close_only() -> None:
    bars = [_bar(i, 100.0, 100.0) for i in range(24)]
    bars[5] = _bar(5, 100.0, 100.0, high=110.0, low=90.0)
    metrics = compute_forward_metrics(
        bars,
        event_time_ms=4 * MS_15M + 60_000,
        entry_delay_bars=1,
        cost_round_trip_bps=0.0,
        signed_direction=1,
    )
    assert metrics["mfe_4h_bps"] >= 1000.0
    assert metrics["mae_4h_bps"] <= -1000.0


def test_forward_metrics_returns_incomplete_when_forward_window_missing() -> None:
    bars = [_bar(i, 100, 100) for i in range(6)]
    metrics = compute_forward_metrics(
        bars,
        event_time_ms=4 * MS_15M + 60_000,
        entry_delay_bars=1,
        cost_round_trip_bps=50.0,
        signed_direction=1,
    )
    assert metrics["status"] == "forward_window_incomplete"
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_metrics.py -q
```

Expected: FAIL，模块不存在。

**Step 3：实现 metrics**

Create `src/research/external_signal_shadow/stage1_3_metrics.py`:

```python
from __future__ import annotations

from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_replay import select_entry_bar


def _return_bps(entry: float, exit_price: float, signed_direction: int) -> float:
    return signed_direction * (exit_price / entry - 1.0) * 10_000.0


def compute_forward_metrics(
    bars: list[HistoricalBar],
    *,
    event_time_ms: int,
    entry_delay_bars: int,
    cost_round_trip_bps: float,
    signed_direction: int,
) -> dict:
    entry = select_entry_bar(bars, event_time_ms=event_time_ms, entry_delay_bars=entry_delay_bars)
    if entry is None:
        return {"status": "entry_unavailable"}
    entry_index = bars.index(entry)
    required_exit_index = entry_index + 16  # 4h on 15m bars
    if required_exit_index >= len(bars):
        return {"status": "forward_window_incomplete", "entry_bar_start_ms": entry.bar_start_ms}
    forward = bars[entry_index : required_exit_index + 1]
    entry_price = entry.open_price
    terminal_15m = _return_bps(entry_price, bars[entry_index].close_price, signed_direction)
    terminal_1h = _return_bps(entry_price, bars[entry_index + 3].close_price, signed_direction)
    terminal_4h = _return_bps(entry_price, bars[required_exit_index].close_price, signed_direction)
    if signed_direction >= 0:
        favorable_path = [_return_bps(entry_price, bar.high_price, signed_direction) for bar in forward]
        adverse_path = [_return_bps(entry_price, bar.low_price, signed_direction) for bar in forward]
    else:
        favorable_path = [_return_bps(entry_price, bar.low_price, signed_direction) for bar in forward]
        adverse_path = [_return_bps(entry_price, bar.high_price, signed_direction) for bar in forward]
    return {
        "status": "ok",
        "entry_bar_start_ms": entry.bar_start_ms,
        "cost_round_trip_bps": cost_round_trip_bps,
        "forward_return_15m_net_bps": terminal_15m - cost_round_trip_bps,
        "forward_return_1h_net_bps": terminal_1h - cost_round_trip_bps,
        "terminal_return_4h_net_bps": terminal_4h - cost_round_trip_bps,
        "mfe_4h_bps": max(favorable_path) if favorable_path else 0.0,
        "mae_4h_bps": min(adverse_path) if adverse_path else 0.0,
    }
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_metrics.py -q
```

Expected: PASS。

---

## Task 6：实现 random baseline 生成规则

**Files:**
- Create: `src/research/external_signal_shadow/stage1_3_baseline.py`
- Create: `tests/research/external_signal_shadow/test_stage1_3_baseline.py`

**Step 1：写失败测试**

Create `tests/research/external_signal_shadow/test_stage1_3_baseline.py`:

```python
from __future__ import annotations

from research.external_signal_shadow.stage1_3_baseline import sample_random_baseline_events
from research.external_signal_shadow.stage1_3_candidates import CandidateEvent


def test_random_baseline_matches_event_count_and_symbol_distribution() -> None:
    candidates = [
        CandidateEvent("volume_spike_1h", "ETHUSDT", 1000, "primary", {}),
        CandidateEvent("volume_spike_1h", "ETHUSDT", 2000, "primary", {}),
        CandidateEvent("volume_spike_1h", "SOLUSDT", 3000, "primary", {}),
    ]
    eligible = {
        "ETHUSDT": [10_000, 20_000, 30_000, 40_000],
        "SOLUSDT": [10_000, 20_000, 30_000, 40_000],
    }
    sampled = sample_random_baseline_events(candidates, eligible_event_times_by_symbol=eligible, random_seed=1)
    assert len(sampled) == len(candidates)
    assert [event.symbol for event in sampled].count("ETHUSDT") == 2
    assert [event.symbol for event in sampled].count("SOLUSDT") == 1
    assert all(event.event_time_ms not in {1000, 2000, 3000} for event in sampled)
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_baseline.py -q
```

Expected: FAIL，模块不存在。

**Step 3：实现 baseline sampler**

Create `src/research/external_signal_shadow/stage1_3_baseline.py`:

```python
from __future__ import annotations

import random

from research.external_signal_shadow.stage1_3_candidates import CandidateEvent


def sample_random_baseline_events(
    candidate_events: list[CandidateEvent],
    *,
    eligible_event_times_by_symbol: dict[str, list[int]],
    random_seed: int,
) -> list[CandidateEvent]:
    rng = random.Random(random_seed)
    candidate_times = {event.event_time_ms for event in candidate_events}
    sampled: list[CandidateEvent] = []
    for event in candidate_events:
        eligible = [
            timestamp
            for timestamp in eligible_event_times_by_symbol.get(event.symbol, [])
            if timestamp not in candidate_times
        ]
        if not eligible:
            continue
        sampled.append(
            CandidateEvent(
                candidate_name=f"random_baseline_for_{event.candidate_name}",
                symbol=event.symbol,
                event_time_ms=rng.choice(eligible),
                candidate_role="baseline",
                metadata={"baseline_type": "symbol_matched_random"},
            )
        )
    return sampled
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_baseline.py -q
```

Expected: PASS。


---

## Task 6.5：实现 500 次 random baseline trials 与 hour-of-day matching

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_3_baseline.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_3_baseline.py`

**Step 1：追加失败测试**

Append to `tests/research/external_signal_shadow/test_stage1_3_baseline.py`:

```python

def test_random_baseline_runs_500_trials_and_reports_distribution() -> None:
    candidates = [CandidateEvent("volume_spike_1h", "ETHUSDT", 3_600_000, "primary", {})]
    eligible = {"ETHUSDT": [hour * 3_600_000 for hour in range(2, 24)]}
    result = run_random_baseline_trials(
        candidates,
        eligible_event_times_by_symbol=eligible,
        trials=500,
        random_seed=20260613,
    )
    assert result["random_baseline_trials"] == 500
    assert len(result["trials"]) == 500
    assert result["baseline_sampling_insufficient_count"] == 0


def test_random_baseline_matches_hour_of_day_when_available() -> None:
    candidate_time = 10 * 3_600_000
    candidates = [CandidateEvent("volume_spike_1h", "ETHUSDT", candidate_time, "primary", {})]
    eligible = {"ETHUSDT": [10 * 3_600_000 + 86_400_000, 12 * 3_600_000]}
    result = run_random_baseline_trials(
        candidates,
        eligible_event_times_by_symbol=eligible,
        trials=1,
        random_seed=1,
    )
    sampled = result["trials"][0][0]
    assert sampled.event_time_ms % 86_400_000 == candidate_time % 86_400_000


def test_random_baseline_reports_sampling_insufficient_when_no_bucket() -> None:
    candidates = [CandidateEvent("volume_spike_1h", "ETHUSDT", 10 * 3_600_000, "primary", {})]
    result = run_random_baseline_trials(
        candidates,
        eligible_event_times_by_symbol={"ETHUSDT": []},
        trials=3,
        random_seed=1,
    )
    assert result["baseline_sampling_insufficient_count"] == 3
```

**Step 2：更新 imports**

Modify the import line in `test_stage1_3_baseline.py`:

```python
from research.external_signal_shadow.stage1_3_baseline import (
    run_random_baseline_trials,
    sample_random_baseline_events,
)
```

**Step 3：实现 baseline trials**

Modify `src/research/external_signal_shadow/stage1_3_baseline.py`:

```python
def _hour_bucket(timestamp_ms: int) -> int:
    return (timestamp_ms // 3_600_000) % 24


def _eligible_by_hour(
    candidate_time_ms: int,
    eligible_times: list[int],
    candidate_times: set[int],
) -> list[int]:
    candidate_hour = _hour_bucket(candidate_time_ms)
    same_hour = [
        item for item in eligible_times
        if item not in candidate_times and _hour_bucket(item) == candidate_hour
    ]
    if same_hour:
        return same_hour
    near_hour = [
        item for item in eligible_times
        if item not in candidate_times and abs(_hour_bucket(item) - candidate_hour) <= 1
    ]
    return near_hour


def run_random_baseline_trials(
    candidate_events: list[CandidateEvent],
    *,
    eligible_event_times_by_symbol: dict[str, list[int]],
    trials: int,
    random_seed: int,
) -> dict:
    all_trials: list[list[CandidateEvent]] = []
    insufficient = 0
    for trial_index in range(trials):
        sampled: list[CandidateEvent] = []
        rng = random.Random(random_seed + trial_index)
        candidate_times = {event.event_time_ms for event in candidate_events}
        for event in candidate_events:
            eligible = _eligible_by_hour(
                event.event_time_ms,
                eligible_event_times_by_symbol.get(event.symbol, []),
                candidate_times,
            )
            if not eligible:
                insufficient += 1
                continue
            sampled.append(
                CandidateEvent(
                    candidate_name=f"random_baseline_for_{event.candidate_name}",
                    symbol=event.symbol,
                    event_time_ms=rng.choice(eligible),
                    candidate_role="baseline",
                    metadata={"baseline_type": "symbol_and_hour_matched_random"},
                )
            )
        all_trials.append(sampled)
    return {
        "random_baseline_trials": trials,
        "trials": all_trials,
        "baseline_sampling_insufficient_count": insufficient,
    }
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_baseline.py -q
```

Expected: PASS。

---

## Task 7：实现 candidate summary 和 decision gates

**Files:**
- Create: `src/research/external_signal_shadow/stage1_3_summary.py`
- Create: `tests/research/external_signal_shadow/test_stage1_3_summary.py`

**Step 1：写失败测试**

Create `tests/research/external_signal_shadow/test_stage1_3_summary.py`:

```python
from __future__ import annotations

from research.external_signal_shadow.stage1_3_summary import decide_candidate, decide_stage1_3_summary


def _candidate(**overrides: object) -> dict:
    data = {
        "candidate_name": "volume_spike_1h",
        "candidate_role": "primary",
        "event_count": 120,
        "symbols_with_events": 3,
        "event_days": 25,
        "max_single_symbol_event_share": 0.40,
        "max_single_day_event_share": 0.10,
        "top_5_positive_events_gross_profit_share": 0.20,
        "baseline_excess_net_bps": 5.0,
        "median_net_return_after_50bps": 1.0,
        "left_tail_p05_after_50bps_vs_baseline_bps": 0.0,
    }
    data.update(overrides)
    return data


def test_candidate_data_insufficient_when_event_count_below_gate() -> None:
    result = decide_candidate(_candidate(event_count=99))
    assert result["candidate_decision"] == "candidate_data_insufficient"


def test_candidate_fails_when_top5_positive_concentration_too_high() -> None:
    result = decide_candidate(_candidate(top_5_positive_events_gross_profit_share=0.50))
    assert result["candidate_decision"] == "candidate_failed"
    assert result["primary_blocker"] == "top5_positive_pnl_concentration_high"


def test_candidate_diagnostic_promising_does_not_unlock_live_smoke() -> None:
    result = decide_candidate(_candidate(median_net_return_after_50bps=0.0, baseline_excess_net_bps=3.0))
    assert result["candidate_decision"] == "candidate_diagnostic_promising"
    assert result["live_smoke_allowed"] is False


def test_stage1_3_summary_stops_when_all_primary_candidates_fail() -> None:
    summary = decide_stage1_3_summary(
        {
            "candidate_results": [
                _candidate(candidate_name="volume_spike_1h", baseline_excess_net_bps=-1.0),
                _candidate(candidate_name="relative_strength_vs_btc", baseline_excess_net_bps=-1.0),
                _candidate(candidate_name="volume_confirmed_relative_strength", event_count=0),
            ],
            "alpha_interpretation_allowed": False,
            "collector_expansion_allowed": False,
            "live_shadow_required_now": False,
        }
    )
    assert summary["next_action"] == "stop_gate_ticker_direction"
    assert summary["alpha_interpretation_allowed"] is False
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_summary.py -q
```

Expected: FAIL，模块不存在。

**Step 3：实现 summary decisions**

Create `src/research/external_signal_shadow/stage1_3_summary.py`:

```python
from __future__ import annotations

from configs import base

PRIMARY_CANDIDATES = {
    "volume_spike_1h",
    "relative_strength_vs_btc",
    "volume_confirmed_relative_strength",
}


def decide_candidate(candidate: dict) -> dict:
    result = dict(candidate)
    blocker = None
    decision = "candidate_promising_for_live_smoke"
    live_smoke_allowed = True

    if candidate.get("event_count", 0) < base.EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_COUNT:
        decision = "candidate_data_insufficient"
        blocker = "event_count_below_min"
    elif candidate.get("symbols_with_events", 0) < base.EXTERNAL_SIGNAL_STAGE1_3_MIN_SYMBOLS_WITH_EVENTS:
        decision = "candidate_data_insufficient"
        blocker = "symbols_with_events_below_min"
    elif candidate.get("event_days", 0) < base.EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_DAYS:
        decision = "candidate_data_insufficient"
        blocker = "event_days_below_min"
    elif candidate.get("max_single_symbol_event_share", 1.0) > base.EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_SYMBOL_EVENT_SHARE:
        decision = "candidate_failed"
        blocker = "single_symbol_event_share_high"
    elif candidate.get("max_single_day_event_share", 1.0) > base.EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_DAY_EVENT_SHARE:
        decision = "candidate_failed"
        blocker = "single_day_event_share_high"
    elif candidate.get("top_5_positive_events_gross_profit_share", 1.0) > base.EXTERNAL_SIGNAL_STAGE1_3_MAX_TOP5_POSITIVE_PNL_SHARE:
        decision = "candidate_failed"
        blocker = "top5_positive_pnl_concentration_high"
    elif candidate.get("baseline_excess_net_bps", 0.0) <= 0:
        decision = "candidate_failed"
        blocker = "no_positive_baseline_excess"
    elif candidate.get("median_net_return_after_50bps", 0.0) <= 0:
        decision = "candidate_diagnostic_promising"
        blocker = "median_net_return_not_positive"
        live_smoke_allowed = False

    if decision != "candidate_promising_for_live_smoke":
        live_smoke_allowed = False

    result["candidate_decision"] = decision
    result["primary_blocker"] = blocker
    result["live_smoke_allowed"] = live_smoke_allowed
    return result


def decide_stage1_3_summary(summary: dict) -> dict:
    decided = [decide_candidate(item) for item in summary.get("candidate_results", [])]
    primary = [item for item in decided if item.get("candidate_name") in PRIMARY_CANDIDATES]
    promising = [item for item in primary if item.get("candidate_decision") == "candidate_promising_for_live_smoke"]
    next_action = "proceed_to_24h_live_smoke_design" if promising else "stop_gate_ticker_direction"
    return {
        **summary,
        "candidate_results": decided,
        "decision": "stage1_3_candidate_signal_discovery_completed",
        "next_action": next_action,
        "alpha_interpretation_allowed": False,
        "collector_expansion_allowed": False,
        "live_shadow_required_now": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
    }
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_summary.py -q
```

Expected: PASS。

---

## Task 8：实现 orchestrator 骨架与 fixture replay

**Files:**
- Create: `src/research/external_signal_shadow/stage1_3_orchestrator.py`
- Create: `tests/research/external_signal_shadow/test_stage1_3_orchestrator.py`

**Step 1：写失败测试**

Create `tests/research/external_signal_shadow/test_stage1_3_orchestrator.py`:

```python
from __future__ import annotations

from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_orchestrator import run_stage1_3_candidate_discovery

MS_15M = 15 * 60 * 1000


def _bars(symbol: str, count: int) -> list[HistoricalBar]:
    rows: list[HistoricalBar] = []
    for i in range(count):
        close = 100.0 + i * 0.01
        volume = 1_000_000.0
        if symbol == "ETHUSDT" and i % 20 in {4, 5, 6, 7}:
            volume = 10_000_000.0
            close += 5.0
        rows.append(HistoricalBar(symbol, i * MS_15M, (i + 1) * MS_15M, close, close, close, close, volume))
    return rows


def test_stage1_3_orchestrator_returns_safe_summary_shape() -> None:
    bars = _bars("BTCUSDT", 240) + _bars("ETHUSDT", 240) + _bars("SOLUSDT", 240)
    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue="binance_proxy",
        venue_proxy_used=True,
    )
    assert summary["decision"] == "stage1_3_candidate_signal_discovery_completed"
    assert summary["alpha_interpretation_allowed"] is False
    assert summary["collector_expansion_allowed"] is False
    assert summary["historical_venue"] == "binance_proxy"
    assert summary["venue_proxy_used"] is True
    assert "candidate_results" in summary
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_orchestrator.py -q
```

Expected: FAIL，模块不存在。

**Step 3：实现最小 orchestrator**

Create `src/research/external_signal_shadow/stage1_3_orchestrator.py`:

```python
from __future__ import annotations

from collections import Counter

from configs import base
from research.external_signal_shadow.stage1_3_models import HistoricalBar, compute_bar_coverage, group_bars_by_symbol
from research.external_signal_shadow.stage1_3_summary import decide_stage1_3_summary


def _candidate_stub(name: str, role: str) -> dict:
    return {
        "candidate_name": name,
        "candidate_role": role,
        "event_count": 0,
        "symbols_with_events": 0,
        "event_days": 0,
        "max_single_symbol_event_share": 0.0,
        "max_single_day_event_share": 0.0,
        "top_5_positive_events_gross_profit_share": 0.0,
        "top_5_events_abs_pnl_share": 0.0,
        "baseline_excess_net_bps": 0.0,
        "median_net_return_after_50bps": 0.0,
    }


def run_stage1_3_candidate_discovery(
    bars: list[HistoricalBar],
    *,
    historical_venue: str,
    venue_proxy_used: bool,
) -> dict:
    interval_ms = base.EXTERNAL_SIGNAL_STAGE1_3_SNAPSHOT_INTERVAL_MINUTES * 60 * 1000
    coverage = compute_bar_coverage(bars, interval_ms=interval_ms)
    grouped = group_bars_by_symbol(bars)
    symbol_counts = Counter({symbol: len(items) for symbol, items in grouped.items()})
    summary = {
        "historical_venue": historical_venue,
        "venue_proxy_used": venue_proxy_used,
        "venue_proxy_risk": "gate_live_binance_history_mismatch" if venue_proxy_used else "none",
        "bar_coverage_ratio_by_symbol": coverage,
        "symbol_bar_count": dict(symbol_counts),
        "excluded_event_reason_counts": {},
        "rolling_baseline_insufficient_count": 0,
        "forward_window_incomplete_count": 0,
        "candidate_results": [
            _candidate_stub("volume_spike_1h", "primary"),
            _candidate_stub("relative_strength_vs_btc", "primary"),
            _candidate_stub("volume_confirmed_relative_strength", "primary"),
            _candidate_stub("price_move_15m", "baseline"),
            _candidate_stub("cross_symbol_rotation", "diagnostic"),
        ],
        "baseline_results": {},
        "alpha_interpretation_allowed": False,
        "collector_expansion_allowed": False,
        "live_shadow_required_now": False,
    }
    return decide_stage1_3_summary(summary)
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_orchestrator.py -q
```

Expected: PASS。

Note: This task creates a safe summary skeleton. Full candidate generation can be added inside the same orchestrator only after the tests in Tasks 2-7 pass.


---

## Task 8.5：把候选生成真正接入 orchestrator

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_3_orchestrator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_3_orchestrator.py`

**Step 1：追加失败测试**

Append to `tests/research/external_signal_shadow/test_stage1_3_orchestrator.py`:

```python

def test_stage1_3_orchestrator_generates_volume_spike_candidate_events() -> None:
    bars = _bars("BTCUSDT", 400) + _bars("ETHUSDT", 400) + _bars("SOLUSDT", 400)
    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue="binance_proxy",
        venue_proxy_used=True,
    )
    by_name = {item["candidate_name"]: item for item in summary["candidate_results"]}
    assert by_name["volume_spike_1h"]["candidate_role"] == "primary"
    assert by_name["volume_spike_1h"]["event_count"] > 0
    assert by_name["price_move_15m"]["candidate_role"] == "baseline"
    assert by_name["cross_symbol_rotation"]["candidate_role"] == "diagnostic"
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_orchestrator.py::test_stage1_3_orchestrator_generates_volume_spike_candidate_events -q
```

Expected: FAIL，因为 Task 8 skeleton 还没有生成真实候选。

**Step 3：在 orchestrator 中接入候选生成**

Modify `src/research/external_signal_shadow/stage1_3_orchestrator.py`：

- 对每个 symbol 的 15m bars 按时间排序。
- 对每个 `end_index >= ONE_HOUR_BAR_COUNT - 1` 构造完整 1h window。
- 使用 `historical_available_at_ms()` 生成 event time。
- 为 `volume_spike_1h` 维护 same-hour 历史 volume list；不足 `SAME_HOUR_MIN_SAMPLES` 时不生成事件，增加 `rolling_baseline_insufficient_count`。
- 为 `relative_strength_vs_btc` 使用同 timestamp 的 BTC 1h return；BTC 自身不生成该候选。
- 对同 symbol + same event_time 的 volume 和 relative strength 事件生成 `volume_confirmed_relative_strength`。
- 对 15m price move 生成 baseline-only `price_move_15m`。
- `cross_symbol_rotation` 第一版只输出 diagnostic stub，不单独生成晋级事件。

Minimal implementation outline:

```python
from collections import defaultdict
from research.external_signal_shadow.stage1_3_candidates import CandidateEvent


def _summarize_events(name: str, role: str, events: list[CandidateEvent]) -> dict:
    symbols = {event.symbol for event in events}
    event_days = {event.event_time_ms // 86_400_000 for event in events}
    symbol_counts = defaultdict(int)
    day_counts = defaultdict(int)
    for event in events:
        symbol_counts[event.symbol] += 1
        day_counts[event.event_time_ms // 86_400_000] += 1
    total = len(events)
    return {
        "candidate_name": name,
        "candidate_role": role,
        "event_count": total,
        "symbols_with_events": len(symbols),
        "event_days": len(event_days),
        "max_single_symbol_event_share": max(symbol_counts.values(), default=0) / total if total else 0.0,
        "max_single_day_event_share": max(day_counts.values(), default=0) / total if total else 0.0,
        "top_5_positive_events_gross_profit_share": 0.0,
        "top_5_events_abs_pnl_share": 0.0,
        "baseline_excess_net_bps": 0.0,
        "median_net_return_after_50bps": 0.0,
    }
```

Implementation must keep all final decisions conservative until Task 5 metrics and Task 6 baseline are fully wired. It is acceptable for `baseline_excess_net_bps` to remain `0.0` in this task; event counts must be real.

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_orchestrator.py -q
```

Expected: PASS。


---

## Task 8.6：把 forward metrics 与 500 次 baseline 接入 orchestrator

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_3_orchestrator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_3_orchestrator.py`

**Step 1：追加失败测试**

Append to `tests/research/external_signal_shadow/test_stage1_3_orchestrator.py`:

```python

def test_orchestrator_computes_forward_metrics_and_500_random_baseline_trials() -> None:
    bars = _bars("BTCUSDT", 500) + _bars("ETHUSDT", 500) + _bars("SOLUSDT", 500)
    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue="binance_proxy",
        venue_proxy_used=True,
    )
    by_name = {item["candidate_name"]: item for item in summary["candidate_results"]}
    volume = by_name["volume_spike_1h"]
    assert volume["random_baseline_trials"] == 500
    assert "baseline_primary_metric_median" in volume
    assert "candidate_vs_baseline_percentile" in volume
    assert "baseline_excess_net_bps" in volume
    assert "median_net_return_after_50bps" in volume
```

**Step 2：实现 event-level metrics 聚合**

Add helper functions in `stage1_3_orchestrator.py`:

```python
from statistics import median, quantiles
from research.external_signal_shadow.stage1_3_baseline import run_random_baseline_trials
from research.external_signal_shadow.stage1_3_metrics import compute_forward_metrics


def _safe_median(values: list[float]) -> float:
    return median(values) if values else 0.0


def _safe_p05(values: list[float]) -> float:
    if not values:
        return 0.0
    return sorted(values)[max(int(len(values) * 0.05) - 1, 0)]


def _summarize_metric_distribution(values: list[float]) -> dict:
    sorted_values = sorted(values)
    if not sorted_values:
        return {"median": 0.0, "p25": 0.0, "p75": 0.0}
    return {
        "median": _safe_median(sorted_values),
        "p25": sorted_values[int((len(sorted_values) - 1) * 0.25)],
        "p75": sorted_values[int((len(sorted_values) - 1) * 0.75)],
    }
```

For each candidate event:

- compute event metrics under 30/50/80 bps;
- use 50 bps `terminal_return_4h_net_bps` as primary metric;
- generate 500 random baseline trials with symbol/hour matching;
- compute each trial's median primary metric;
- compute `baseline_primary_metric_median`, p25, p75;
- compute `candidate_vs_baseline_percentile`;
- compute `baseline_excess_net_bps = candidate_primary_median - baseline_primary_metric_median`.

**Step 3：price_move_15m 必须使用 trigger_sign**

When evaluating `price_move_15m`, set:

```python
signed_direction = int(event.metadata.get("trigger_sign", 1))
```

For primary candidates, use:

```python
signed_direction = 1
```

For `relative_strength_vs_btc`, additionally report both:

```json
{
  "evaluation_mode": "outright_long_alt",
  "relative_spread_observation_reported": true
}
```

Gate for live smoke can only use `outright_long_alt` metrics. Relative spread observation is diagnostic only.

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_orchestrator.py::test_orchestrator_computes_forward_metrics_and_500_random_baseline_trials -q
```

Expected: PASS。

---

## Task 8.7：计算 candidate-level concentration 与 left-tail 指标

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_3_orchestrator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_3_orchestrator.py`

**Step 1：追加失败测试**

Append:

```python

def test_orchestrator_computes_top5_positive_pnl_share_from_event_pnl() -> None:
    bars = _bars("BTCUSDT", 500) + _bars("ETHUSDT", 500) + _bars("SOLUSDT", 500)
    summary = run_stage1_3_candidate_discovery(bars, historical_venue="binance_proxy", venue_proxy_used=True)
    volume = {item["candidate_name"]: item for item in summary["candidate_results"]}["volume_spike_1h"]
    assert "top_5_positive_events_gross_profit_share" in volume
    assert "top_5_events_abs_pnl_share" in volume
    assert "left_tail_p05_after_50bps_vs_baseline_bps" in volume
```

**Step 2：实现 concentration**

Event-level primary PnL definition:

```python
event_primary_pnl = terminal_return_4h_net_bps_after_50bps
```

Compute:

```python
positive_pnls = [max(value, 0.0) for value in event_primary_pnls]
positive_total = sum(positive_pnls)
top_5_positive_events_gross_profit_share = sum(sorted(positive_pnls, reverse=True)[:5]) / positive_total if positive_total else 0.0

abs_pnls = [abs(value) for value in event_primary_pnls]
abs_total = sum(abs_pnls)
top_5_events_abs_pnl_share = sum(sorted(abs_pnls, reverse=True)[:5]) / abs_total if abs_total else 0.0
```

If no positive PnL exists, `top_5_positive_events_gross_profit_share = 0.0` and `positive_event_count = 0`.

**Step 3：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_orchestrator.py::test_orchestrator_computes_top5_positive_pnl_share_from_event_pnl -q
```

Expected: PASS。

---

## Task 8.8：强制执行 data coverage / missing forward-window gate

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_3_orchestrator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_3_orchestrator.py`

**Step 1：追加失败测试**

Append:

```python

def test_bar_coverage_below_min_blocks_replay() -> None:
    interval = 15 * 60 * 1000
    bars = [
        HistoricalBar("BTCUSDT", 0, interval, 100, 100, 100, 100, 1),
        HistoricalBar("BTCUSDT", 2 * interval, 3 * interval, 100, 100, 100, 100, 1),
    ]
    summary = run_stage1_3_candidate_discovery(bars, historical_venue="binance_proxy", venue_proxy_used=True)
    assert summary["decision"] == "stage1_3_candidate_signal_discovery_failed"
    assert summary["primary_blocker"] == "bar_coverage_below_min"
    assert summary["next_action"] == "fix_data_or_stop"
```

**Step 2：实现 coverage blocking**

At the start of `run_stage1_3_candidate_discovery()` after coverage calculation:

```python
required_symbols = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"}
coverage_failures = {
    symbol: ratio
    for symbol, ratio in coverage.items()
    if symbol in required_symbols and ratio < base.EXTERNAL_SIGNAL_STAGE1_3_MIN_BAR_COVERAGE_RATIO
}
if coverage_failures:
    return {
        "decision": "stage1_3_candidate_signal_discovery_failed",
        "primary_blocker": "bar_coverage_below_min",
        "next_action": "fix_data_or_stop",
        "bar_coverage_ratio_by_symbol": coverage,
        "alpha_interpretation_allowed": False,
        "collector_expansion_allowed": False,
        "live_shadow_required_now": False,
    }
```

When metrics return `forward_window_incomplete`, exclude that event and increment `forward_window_incomplete_count`.

When rolling baseline is insufficient, do not emit an event and increment `rolling_baseline_insufficient_count`.

**Step 3：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow/test_stage1_3_orchestrator.py::test_bar_coverage_below_min_blocks_replay -q
```

Expected: PASS。

---

## Task 8.9：区分 fixture smoke 与 research-valid run

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_3_orchestrator.py`
- Modify: `scripts/run_external_signal_shadow_stage1_3_candidate_discovery.py`
- Modify: `tests/scripts/test_run_external_signal_shadow_stage1_3_candidate_discovery.py`

**Step 1：追加失败测试**

Append to CLI test:

```python

def test_stage1_3_fixture_run_marked_not_research_valid(tmp_path: Path) -> None:
    bars = tmp_path / "bars.jsonl"
    output = tmp_path / "summary.json"
    interval = 15 * 60 * 1000
    rows = []
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        for i in range(20):
            rows.append({
                "symbol": symbol,
                "bar_start_ms": i * interval,
                "bar_end_ms": (i + 1) * interval,
                "open_price": 100.0,
                "high_price": 101.0,
                "low_price": 99.0,
                "close_price": 100.0,
                "quote_volume": 1_000_000.0,
            })
    bars.write_text("\n".join(json.dumps(row) for row in rows))
    assert main(["--bars", str(bars), "--output", str(output), "--historical-venue", "binance_proxy", "--venue-proxy-used", "--fixture-run"]) == 0
    summary = json.loads(output.read_text())
    assert summary["fixture_run"] is True
    assert summary["research_result_valid"] is False
```

**Step 2：实现 CLI flag**

Add:

```python
parser.add_argument("--fixture-run", action="store_true")
```

Pass to orchestrator:

```python
fixture_run=args.fixture_run
```

Update orchestrator signature:

```python
def run_stage1_3_candidate_discovery(..., fixture_run: bool = False) -> dict:
```

Set summary fields:

```python
"fixture_run": fixture_run,
"research_result_valid": not fixture_run and history_days >= base.EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_MIN,
```

If `fixture_run=True`, review must state infrastructure-only.

**Step 3：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_external_signal_shadow_stage1_3_candidate_discovery.py::test_stage1_3_fixture_run_marked_not_research_valid -q
```

Expected: PASS。

---

## Task 9：实现 CLI 脚本

**Files:**
- Create: `scripts/run_external_signal_shadow_stage1_3_candidate_discovery.py`
- Create: `tests/scripts/test_run_external_signal_shadow_stage1_3_candidate_discovery.py`

**Step 1：写失败测试**

Create `tests/scripts/test_run_external_signal_shadow_stage1_3_candidate_discovery.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_external_signal_shadow_stage1_3_candidate_discovery import main


def test_stage1_3_cli_writes_summary_from_fixture(tmp_path: Path) -> None:
    bars = tmp_path / "bars.jsonl"
    output = tmp_path / "summary.json"
    rows = []
    interval = 15 * 60 * 1000
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        for i in range(20):
            rows.append(
                {
                    "symbol": symbol,
                    "bar_start_ms": i * interval,
                    "bar_end_ms": (i + 1) * interval,
                    "open_price": 100.0,
                    "high_price": 101.0,
                    "low_price": 99.0,
                    "close_price": 100.0,
                    "quote_volume": 1_000_000.0,
                }
            )
    bars.write_text("\n".join(json.dumps(row) for row in rows))
    result = main([
        "--bars", str(bars),
        "--output", str(output),
        "--historical-venue", "binance_proxy",
        "--venue-proxy-used",
    ])
    assert result == 0
    summary = json.loads(output.read_text())
    assert summary["alpha_interpretation_allowed"] is False
    assert summary["venue_proxy_used"] is True
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_external_signal_shadow_stage1_3_candidate_discovery.py -q
```

Expected: FAIL，脚本不存在。

**Step 3：实现 CLI**

Create `scripts/run_external_signal_shadow_stage1_3_candidate_discovery.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_orchestrator import run_stage1_3_candidate_discovery


def _load_bars(path: str) -> list[HistoricalBar]:
    bars: list[HistoricalBar] = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            bars.append(HistoricalBar(**json.loads(line)))
    return bars


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage 1.3 candidate signal discovery")
    parser.add_argument("--bars", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--historical-venue", choices=("gate", "binance_proxy"), required=True)
    parser.add_argument("--venue-proxy-used", action="store_true")
    args = parser.parse_args(argv)

    summary = run_stage1_3_candidate_discovery(
        _load_bars(args.bars),
        historical_venue=args.historical_venue,
        venue_proxy_used=args.venue_proxy_used,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_run_external_signal_shadow_stage1_3_candidate_discovery.py -q
```

Expected: PASS。

---

## Task 10：实现 Review 脚本

**Files:**
- Create: `scripts/review_external_signal_shadow_stage1_3_candidate_discovery.py`
- Create: `tests/scripts/test_review_external_signal_shadow_stage1_3_candidate_discovery.py`
- Create runtime output during manual run: `docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md`

**Step 1：写失败测试**

Create `tests/scripts/test_review_external_signal_shadow_stage1_3_candidate_discovery.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from scripts.review_external_signal_shadow_stage1_3_candidate_discovery import main


def test_stage1_3_review_script_writes_chinese_markdown(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_3_candidate_signal_discovery_completed",
        "next_action": "stop_gate_ticker_direction",
        "alpha_interpretation_allowed": False,
        "collector_expansion_allowed": False,
        "historical_venue": "binance_proxy",
        "venue_proxy_used": True,
        "fixture_run": True,
        "research_result_valid": False,
        "candidate_results": [
            {
                "candidate_name": "volume_spike_1h",
                "event_count": 120,
                "candidate_decision": "candidate_failed",
                "primary_blocker": "no_positive_baseline_excess",
                "symbols_with_events": 3,
                "event_days": 21,
                "baseline_excess_net_bps": -2.0,
                "median_net_return_after_50bps": -1.0,
                "left_tail_p05_after_50bps_vs_baseline_bps": -10.0,
                "top_5_positive_events_gross_profit_share": 0.25,
            }
        ],
    }))
    result = main(["--summary", str(summary), "--output", str(review)])
    assert result == 0
    text = review.read_text()
    assert "Stage 1.3 Candidate Signal Discovery Review" in text
    assert "不允许 alpha interpretation" in text
    assert "停止 Gate ticker snapshot 派生方向" in text
    assert "volume_spike_1h" in text
    assert "no_positive_baseline_excess" in text
    assert "fixture 数据" in text
    assert "不能推出信号有效性结论" in text
```

**Step 2：运行失败测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_review_external_signal_shadow_stage1_3_candidate_discovery.py -q
```

Expected: FAIL，脚本不存在。

**Step 3：实现 review script**

Create `scripts/review_external_signal_shadow_stage1_3_candidate_discovery.py`:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


def _candidate_table(summary: dict) -> str:
    rows = []
    for item in summary.get("candidate_results", []):
        rows.append(
            "| {name} | {count} | {decision} | {blocker} | {symbols} | {days} | {excess} | {median} | {tail} | {top5} |".format(
                name=item.get("candidate_name"),
                count=item.get("event_count"),
                decision=item.get("candidate_decision"),
                blocker=item.get("primary_blocker"),
                symbols=item.get("symbols_with_events"),
                days=item.get("event_days"),
                excess=item.get("baseline_excess_net_bps"),
                median=item.get("median_net_return_after_50bps"),
                tail=item.get("left_tail_p05_after_50bps_vs_baseline_bps"),
                top5=item.get("top_5_positive_events_gross_profit_share"),
            )
        )
    if not rows:
        return "无候选结果。"
    header = "| candidate | events | decision | blocker | symbols | days | excess_bps | median_50bps | left_tail_vs_baseline | top5_profit_share |"
    sep = "|---|---:|---|---|---:|---:|---:|---:|---:|---:|"
    return "\n".join([header, sep, *rows])


def _render(summary: dict) -> str:
    next_action = summary.get("next_action")
    if next_action == "stop_gate_ticker_direction":
        action_cn = "停止 Gate ticker snapshot 派生方向"
    elif next_action == "proceed_to_24h_live_smoke_design":
        action_cn = "只允许写 24h live smoke design，不允许 paper/live"
    else:
        action_cn = "仅允许一次性修订候选定义或停止"
    fixture_note = "本 review 基于 fixture 数据，不能推出信号有效性结论，只证明 pipeline 可运行。" if summary.get("fixture_run") else "本 review 基于历史 bars 输入；是否 research-valid 取决于 coverage/history_days。"
    return f"""# External Signal Shadow Lab Stage 1.3 Candidate Signal Discovery Review

## 1. 结论

- decision: `{summary.get('decision')}`
- next_action: `{next_action}`
- 中文动作：{action_cn}
- fixture_run: `{summary.get('fixture_run')}`
- research_result_valid: `{summary.get('research_result_valid')}`

{fixture_note}

## 2. 安全边界

- 不允许 alpha interpretation: `{summary.get('alpha_interpretation_allowed') is False}`
- 不允许扩 collector: `{summary.get('collector_expansion_allowed') is False}`
- 不要求立即 live shadow: `{summary.get('live_shadow_required_now') is False}`

## 3. 数据 venue

- historical_venue: `{summary.get('historical_venue')}`
- venue_proxy_used: `{summary.get('venue_proxy_used')}`

## 4. 候选结果

{_candidate_table(summary)}

## 5. 解释边界

本 review 不能推出任何实盘、paper trading 或自动交易结论。Stage 1.3 只判断预注册候选事件是否值得进入下一阶段研究。
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Stage 1.3 candidate discovery review")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    summary = json.loads(Path(args.summary).read_text())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4：运行测试**

Run:

```bash
PYTHONPATH=src uv run pytest tests/scripts/test_review_external_signal_shadow_stage1_3_candidate_discovery.py -q
```

Expected: PASS。

---

## Task 11：生成 fixture summary / review 证据

**Files:**
- Runtime output: `reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json`
- Runtime output: `docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md`

**Step 1：生成本地 fixture bars**

Run:

```bash
mkdir -p data/external_signal_shadow/fixtures
PYTHONPATH=src uv run python - <<'PY'
import json
from pathlib import Path
interval = 15 * 60 * 1000
rows = []
for symbol in ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'):
    for i in range(300):
        close = 100.0 + i * 0.01
        volume = 1_000_000.0
        rows.append({
            'symbol': symbol,
            'bar_start_ms': i * interval,
            'bar_end_ms': (i + 1) * interval,
            'open_price': close,
            'high_price': close * 1.001,
            'low_price': close * 0.999,
            'close_price': close,
            'quote_volume': volume,
        })
path = Path('data/external_signal_shadow/fixtures/stage1_3_fixture_bars.jsonl')
path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
print(path)
PY
```

Expected: writes fixture jsonl.

**Step 2：运行 Stage 1.3 CLI**

Run:

```bash
PYTHONPATH=src uv run python scripts/run_external_signal_shadow_stage1_3_candidate_discovery.py \
  --bars data/external_signal_shadow/fixtures/stage1_3_fixture_bars.jsonl \
  --output reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json \
  --historical-venue binance_proxy \
  --venue-proxy-used \
  --fixture-run
```

Expected: writes summary JSON. `alpha_interpretation_allowed` must be false, `fixture_run` must be true, and `research_result_valid` must be false.

**Step 3：生成 review**

Run:

```bash
PYTHONPATH=src uv run python scripts/review_external_signal_shadow_stage1_3_candidate_discovery.py \
  --summary reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json \
  --output docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md
```

Expected: writes Chinese review markdown. The review must clearly state this is fixture 数据 and cannot prove signal validity.

---

## Task 12：Focused tests、suite、ruff、全量 pytest

**Files:**
- All modified files

**Step 1：运行 Stage 1.3 focused tests**

Run:

```bash
PYTHONPATH=src uv run pytest \
  tests/research/external_signal_shadow/test_stage1_3_config.py \
  tests/research/external_signal_shadow/test_stage1_3_models.py \
  tests/research/external_signal_shadow/test_stage1_3_replay.py \
  tests/research/external_signal_shadow/test_stage1_3_candidates.py \
  tests/research/external_signal_shadow/test_stage1_3_metrics.py \
  tests/research/external_signal_shadow/test_stage1_3_baseline.py \
  tests/research/external_signal_shadow/test_stage1_3_summary.py \
  tests/research/external_signal_shadow/test_stage1_3_orchestrator.py \
  tests/scripts/test_run_external_signal_shadow_stage1_3_candidate_discovery.py \
  tests/scripts/test_review_external_signal_shadow_stage1_3_candidate_discovery.py \
  -q
```

Expected: all PASS.

**Step 2：运行 external signal suite**

Run:

```bash
PYTHONPATH=src uv run pytest tests/research/external_signal_shadow tests/research/test_external_signal_shadow_*.py tests/scripts/test_*external_signal_shadow* -q
```

Expected: all PASS.

**Step 3：运行 ruff**

Run:

```bash
PYTHONPATH=src uv run ruff check \
  src/research/external_signal_shadow \
  scripts/run_external_signal_shadow_stage1_3_candidate_discovery.py \
  scripts/review_external_signal_shadow_stage1_3_candidate_discovery.py \
  tests/research/external_signal_shadow \
  tests/scripts/test_run_external_signal_shadow_stage1_3_candidate_discovery.py \
  tests/scripts/test_review_external_signal_shadow_stage1_3_candidate_discovery.py
```

Expected: `All checks passed!`

**Step 4：运行全量 pytest**

Run:

```bash
PYTHONPATH=src uv run pytest -q
```

Expected: all PASS.

**Step 5：查看工作区**

Run:

```bash
git status --short --branch
```

Expected: only intended files changed / untracked.

---

## 完成标准

Stage 1.3 implementation 只有在以下条件同时满足时才算完成：

```text
focused tests pass
external signal suite pass
ruff pass
full pytest pass
summary JSON generated
Chinese review generated
alpha_interpretation_allowed = false
collector_expansion_allowed = false
live_shadow_required_now = false
paper/live untouched
```

完成后不要提交，等待用户确认。
