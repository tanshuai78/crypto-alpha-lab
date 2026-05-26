# Trend / Liquidation Phase 1A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `Trend / Liquidation Regime Scanner` 的 Phase 1A 观察与影子验证底座，用于识别方向性波动突破和清算延续机会，但不接入 `execution`。

**Architecture:** 本阶段拆成三层：`watch_event` 只负责发现波动/清算 regime，`SignalCandidate` 只在 observation mode 下表达可影子模拟方向，`shadow replay` 只验证成本后方向性收益。所有阈值进入 `configs/base.py`，策略逻辑与执行逻辑保持隔离。

**Tech Stack:** Python 3.11, dataclasses, pytest, loguru, existing `SignalCandidate`, existing `configs/base.py`, JSONL evidence under `data/`, reports under `reports/trend_regime/`.

---

## 1. 当前边界

本计划只做 Phase 1A，不做实盘：

- 不导入 `src/execution/`。
- 不读取 private API key。
- 不改 `RISK_LIVE_TRADING_ENABLED`。
- 不生成 `executable=True`。
- 不把方向性信号解释为套利信号。

Phase 1A 只回答三个问题：

- 市场是否出现 `vol_breakout` 或 `liquidation_cascade` regime。
- 这些 regime 是否能形成 observation-only `SignalCandidate`。
- 历史/影子模拟在扣除成本后是否有正期望迹象。

---

## 2. 文件结构

计划新增或修改这些文件：

- Modify: `configs/base.py`
  - 增加 Trend/Liquidation Phase 1A 的阈值、轮询、成本与验收配置。
- Create: `src/strategies/trend_regime/scanner.py`
  - 负责纯函数分类、watch event、`BaseStrategy` 子类、exit/risk gate。
- Create: `src/strategies/trend_regime/shadow_simulator.py`
  - 负责基于价格路径的 observation-only shadow PnL。
- Create: `scripts/run_trend_regime_watchlist.py`
  - 负责 observation daemon skeleton、JSONL evidence、heartbeat/reject summary。
- Create: `scripts/replay_trend_regime_shadow.py`
  - 负责读取历史 rows，跑 shadow summary，写 reports。
- Test: `tests/test_trend_regime_config.py`
- Test: `tests/strategies/test_trend_regime_scanner.py`
- Test: `tests/strategies/test_trend_regime_shadow_simulator.py`
- Test: `tests/scripts/test_run_trend_regime_watchlist.py`
- Test: `tests/scripts/test_replay_trend_regime_shadow.py`

---

## 3. 数据协议

Phase 1A 输入 row 使用最小字段：

```python
{
    "timestamp_ms": 1710000000000,
    "exchange": "binance",
    "symbol": "BTC/USDT",
    "close_price": 100000.0,
    "return_1h_pct": 2.5,
    "vol_1h_pct": 3.2,
    "vol_baseline_30d_pct": 1.2,
    "open_interest": 100000000.0,
    "oi_change_1h_pct": 4.0,
    "liquidation_notional_1h_usdt": 20000000.0,
    "volume_24h_usdt": 1000000000.0,
    "estimated_spread_bps": 4.0,
    "estimated_slippage_bps": 6.0,
    "data_age_sec": 5.0,
}
```

输出分类：

- `no_event`
- `vol_breakout_long`
- `vol_breakout_short`
- `liquidation_cascade_long`
- `liquidation_cascade_short`

方向规则：

- `return_1h_pct > 0` 且 `oi_change_1h_pct > 0`：`vol_breakout_long`
- `return_1h_pct < 0` 且 `oi_change_1h_pct > 0`：`vol_breakout_short`
- `return_1h_pct > 0` 且 `oi_change_1h_pct < 0` 且 liquidation 放大：`liquidation_cascade_long`
- `return_1h_pct < 0` 且 `oi_change_1h_pct < 0` 且 liquidation 放大：`liquidation_cascade_short`

---

## Task 1: Add Trend Regime Config

**Files:**
- Modify: `configs/base.py`
- Test: `tests/test_trend_regime_config.py`

- [ ] **Step 1: Write failing config test**

Create `tests/test_trend_regime_config.py`:

```python
from configs import base


def test_trend_regime_phase1a_config_values_are_defined():
    assert base.TREND_REGIME_VOL_BREAKOUT_MULTIPLIER == 2.0
    assert base.TREND_REGIME_MAX_HOLDING_HOURS == 48
    assert base.TREND_REGIME_STOP_LOSS_PCT == 2.0
    assert base.TREND_REGIME_MIN_1H_ABS_RETURN_PCT == 1.5
    assert base.TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT == 1.0
    assert base.TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT == 10_000_000.0
    assert base.TREND_REGIME_MIN_24H_VOLUME_USDT == 100_000_000.0
    assert base.TREND_REGIME_MAX_DATA_AGE_SEC == 60
    assert base.TREND_REGIME_OBSERVATION_COST_BPS == 20.0
    assert base.TREND_REGIME_MAX_SLIPPAGE_BPS == 10.0
    assert base.TREND_REGIME_EVENT_LOG_JSONL == "trend_regime_watch_events.jsonl"
```

- [ ] **Step 2: Verify failing test**

Run:

```bash
PYTHONPATH=src uv run --with pytest pytest tests/test_trend_regime_config.py -q
```

Expected: FAIL with missing config attributes.

- [ ] **Step 3: Add config constants**

Add under `# Strategy: Trend / Liquidation Regime` in `configs/base.py`:

```python
TREND_REGIME_MIN_1H_ABS_RETURN_PCT = 1.5
# Minimum absolute 1h return required before considering a trend/liquidation event.

TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT = 1.0
# Minimum absolute 1h open-interest change used to confirm directional regime pressure.

TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT = 10_000_000.0
# Minimum 1h liquidation notional used to classify liquidation-cascade regimes.

TREND_REGIME_MIN_24H_VOLUME_USDT = 100_000_000.0
# Minimum 24h volume for Phase 1A trend observation. Keeps the first scanner on liquid markets.

TREND_REGIME_MAX_DATA_AGE_SEC = 60
# Maximum public-market-data age before rejecting the row as stale.

TREND_REGIME_OBSERVATION_COST_BPS = 20.0
# Conservative cost assumption for shadow validation, including fees and slippage.

TREND_REGIME_MAX_SLIPPAGE_BPS = 10.0
# Maximum estimated slippage allowed for observation-only SignalCandidate creation.

TREND_REGIME_EVENT_LOG_JSONL = "trend_regime_watch_events.jsonl"
# Low-frequency JSONL evidence file for Phase 1A observation daemon.
```

- [ ] **Step 4: Verify config test passes**

Run:

```bash
PYTHONPATH=src uv run --with pytest pytest tests/test_trend_regime_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add configs/base.py tests/test_trend_regime_config.py
git commit -m "test+feat: add trend regime phase1a config"
```

---

## Task 2: Add Trend Regime Scanner Contract

**Files:**
- Create: `src/strategies/trend_regime/scanner.py`
- Test: `tests/strategies/test_trend_regime_scanner.py`

- [ ] **Step 1: Write failing scanner tests**

Create `tests/strategies/test_trend_regime_scanner.py`:

```python
import pytest

from src.strategies.base import SignalCandidate
from src.strategies.trend_regime.scanner import (
    TrendRegimeWatchEvent,
    TrendRegimeStrategy,
    classify_trend_regime_snapshot,
)


def _snapshot(**overrides):
    row = {
        "timestamp_ms": 1710000000000,
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "close_price": 100000.0,
        "return_1h_pct": 2.5,
        "vol_1h_pct": 3.0,
        "vol_baseline_30d_pct": 1.0,
        "open_interest": 100000000.0,
        "oi_change_1h_pct": 3.0,
        "liquidation_notional_1h_usdt": 0.0,
        "volume_24h_usdt": 1000000000.0,
        "estimated_spread_bps": 4.0,
        "estimated_slippage_bps": 6.0,
        "data_age_sec": 5.0,
    }
    row.update(overrides)
    return row


def test_classifies_vol_breakout_long():
    result = classify_trend_regime_snapshot(_snapshot())
    assert result.event is not None
    assert result.event.regime == "vol_breakout_long"
    assert result.event.direction == "long"
    assert result.event.executable is False


def test_classifies_vol_breakout_short():
    result = classify_trend_regime_snapshot(_snapshot(return_1h_pct=-2.5, oi_change_1h_pct=3.0))
    assert result.event is not None
    assert result.event.regime == "vol_breakout_short"
    assert result.event.direction == "short"


def test_classifies_liquidation_cascade_long():
    result = classify_trend_regime_snapshot(
        _snapshot(
            return_1h_pct=2.5,
            oi_change_1h_pct=-3.0,
            liquidation_notional_1h_usdt=20_000_000.0,
        )
    )
    assert result.event is not None
    assert result.event.regime == "liquidation_cascade_long"
    assert result.event.direction == "long"


def test_rejects_stale_or_illiquid_rows():
    stale = classify_trend_regime_snapshot(_snapshot(data_age_sec=120.0))
    assert stale.reject_reason == "api_stale"

    illiquid = classify_trend_regime_snapshot(_snapshot(volume_24h_usdt=10_000_000.0))
    assert illiquid.reject_reason == "volume_below_min"


def test_rejects_when_vol_breakout_is_not_large_enough():
    result = classify_trend_regime_snapshot(_snapshot(vol_1h_pct=1.5, vol_baseline_30d_pct=1.0))
    assert result.event is None
    assert result.reject_reason == "vol_breakout_below_threshold"


@pytest.mark.asyncio
async def test_strategy_scan_returns_observation_signal_candidate():
    strategy = TrendRegimeStrategy()
    signals = await strategy.scan(_snapshot())

    assert len(signals) == 1
    signal = signals[0]
    assert isinstance(signal, SignalCandidate)
    assert signal.strategy_type == "trend_regime"
    assert signal.direction == "long"
    assert signal.metadata["mode"] == "observation"
    assert signal.metadata["executable"] is False


def test_should_exit_on_stop_loss_or_time_limit():
    strategy = TrendRegimeStrategy()
    signal = SignalCandidate(
        strategy_type="trend_regime",
        symbol="BTC/USDT",
        direction="long",
        confidence=0.55,
        expected_edge_bps=30.0,
        entry_exchange="binance",
        hedge_exchange="binance",
        trigger_reason="vol_breakout_long",
        invalidation_reason="stop_loss_or_time_limit",
        max_holding_hours=48.0,
        stop_loss_pct=2.0,
        suggested_notional_usdt=500.0,
        metadata={"entry_price": 100000.0},
    )
    assert strategy.should_exit(signal, {}, 1.0, -2.1) == (True, "stop_loss_hit")
    assert strategy.should_exit(signal, {}, 49.0, 0.1) == (True, "max_holding_time_reached")
    assert strategy.should_exit(signal, {}, 1.0, 0.1) == (False, "hold")


def test_risk_check_blocks_execution_even_for_valid_observation_signal():
    strategy = TrendRegimeStrategy()
    signal = SignalCandidate(
        strategy_type="trend_regime",
        symbol="BTC/USDT",
        direction="long",
        confidence=0.55,
        expected_edge_bps=30.0,
        entry_exchange="binance",
        hedge_exchange="binance",
        trigger_reason="vol_breakout_long",
        invalidation_reason="stop_loss_or_time_limit",
        max_holding_hours=48.0,
        stop_loss_pct=2.0,
        suggested_notional_usdt=500.0,
        metadata={"mode": "observation", "executable": False},
    )
    assert strategy.risk_check(signal) == (False, "observation_only")
```

- [ ] **Step 2: Verify failing tests**

Run:

```bash
PYTHONPATH=src uv run --with pytest --with pytest-asyncio pytest tests/strategies/test_trend_regime_scanner.py -q
```

Expected: FAIL because `scanner.py` does not exist.

- [ ] **Step 3: Implement minimal scanner**

Create `src/strategies/trend_regime/scanner.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from configs.base import (
    RISK_MAX_SINGLE_POSITION_USDT,
    TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT,
    TREND_REGIME_MAX_DATA_AGE_SEC,
    TREND_REGIME_MAX_HOLDING_HOURS,
    TREND_REGIME_MAX_SLIPPAGE_BPS,
    TREND_REGIME_MIN_1H_ABS_RETURN_PCT,
    TREND_REGIME_MIN_24H_VOLUME_USDT,
    TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT,
    TREND_REGIME_OBSERVATION_COST_BPS,
    TREND_REGIME_STOP_LOSS_PCT,
    TREND_REGIME_VOL_BREAKOUT_MULTIPLIER,
)
from src.strategies.base import BaseStrategy, SignalCandidate


@dataclass(frozen=True)
class TrendRegimeWatchEvent:
    strategy_type: str
    symbol: str
    exchange: str
    regime: str
    direction: str
    vol_ratio: float
    return_1h_pct: float
    oi_change_1h_pct: float
    liquidation_notional_1h_usdt: float
    reason: str
    reject_reason: str | None
    executable: bool
    metadata: dict[str, Any]


@dataclass(frozen=True)
class TrendRegimeClassification:
    event: TrendRegimeWatchEvent | None
    reject_reason: str | None


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


def classify_trend_regime_snapshot(row: dict[str, Any]) -> TrendRegimeClassification:
    symbol = str(row.get("symbol") or "")
    if not symbol:
        return TrendRegimeClassification(None, "missing_symbol")

    data_age_sec = _number_or_none(row.get("data_age_sec"))
    if data_age_sec is None or data_age_sec > TREND_REGIME_MAX_DATA_AGE_SEC:
        return TrendRegimeClassification(None, "api_stale")

    volume_24h_usdt = _number_or_none(row.get("volume_24h_usdt"))
    if volume_24h_usdt is None or volume_24h_usdt < TREND_REGIME_MIN_24H_VOLUME_USDT:
        return TrendRegimeClassification(None, "volume_below_min")

    return_1h_pct = _number_or_none(row.get("return_1h_pct"))
    vol_1h_pct = _number_or_none(row.get("vol_1h_pct"))
    vol_baseline_30d_pct = _number_or_none(row.get("vol_baseline_30d_pct"))
    oi_change_1h_pct = _number_or_none(row.get("oi_change_1h_pct"))
    liquidation_notional = _number_or_none(row.get("liquidation_notional_1h_usdt")) or 0.0
    slippage_bps = _number_or_none(row.get("estimated_slippage_bps"))

    if return_1h_pct is None or vol_1h_pct is None or vol_baseline_30d_pct is None:
        return TrendRegimeClassification(None, "missing_price_or_vol")
    if oi_change_1h_pct is None:
        return TrendRegimeClassification(None, "missing_oi")
    if vol_baseline_30d_pct <= 0.0:
        return TrendRegimeClassification(None, "invalid_vol_baseline")
    if slippage_bps is None or slippage_bps > TREND_REGIME_MAX_SLIPPAGE_BPS:
        return TrendRegimeClassification(None, "slippage_above_max")

    vol_ratio = vol_1h_pct / vol_baseline_30d_pct
    if vol_ratio < TREND_REGIME_VOL_BREAKOUT_MULTIPLIER:
        return TrendRegimeClassification(None, "vol_breakout_below_threshold")
    if abs(return_1h_pct) < TREND_REGIME_MIN_1H_ABS_RETURN_PCT:
        return TrendRegimeClassification(None, "return_below_min")
    if abs(oi_change_1h_pct) < TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT:
        return TrendRegimeClassification(None, "oi_confirmation_below_min")

    direction = "long" if return_1h_pct > 0.0 else "short"
    if oi_change_1h_pct > 0.0:
        regime = f"vol_breakout_{direction}"
    elif liquidation_notional >= TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT:
        regime = f"liquidation_cascade_{direction}"
    else:
        return TrendRegimeClassification(None, "liquidation_not_confirmed")

    event = TrendRegimeWatchEvent(
        strategy_type="trend_regime",
        symbol=symbol,
        exchange=str(row.get("exchange") or "unknown"),
        regime=regime,
        direction=direction,
        vol_ratio=vol_ratio,
        return_1h_pct=return_1h_pct,
        oi_change_1h_pct=oi_change_1h_pct,
        liquidation_notional_1h_usdt=liquidation_notional,
        reason=regime,
        reject_reason=None,
        executable=False,
        metadata={
            "mode": "observation",
            "estimated_cost_bps": TREND_REGIME_OBSERVATION_COST_BPS,
            "estimated_slippage_bps": slippage_bps,
        },
    )
    return TrendRegimeClassification(event, None)


class TrendRegimeStrategy(BaseStrategy):
    strategy_type = "trend_regime"

    async def scan(self, market_data: dict[str, Any]) -> list[SignalCandidate]:
        result = classify_trend_regime_snapshot(market_data)
        if result.event is None:
            return []
        event = result.event
        signal = SignalCandidate(
            strategy_type="trend_regime",
            symbol=event.symbol,
            direction=event.direction,
            confidence=0.55,
            expected_edge_bps=max(abs(event.return_1h_pct) * 100 - TREND_REGIME_OBSERVATION_COST_BPS, 0.0),
            entry_exchange=event.exchange,
            hedge_exchange=event.exchange,
            trigger_reason=event.regime,
            invalidation_reason="stop_loss_or_time_limit",
            max_holding_hours=float(TREND_REGIME_MAX_HOLDING_HOURS),
            stop_loss_pct=float(TREND_REGIME_STOP_LOSS_PCT),
            suggested_notional_usdt=RISK_MAX_SINGLE_POSITION_USDT,
            metadata={
                **event.metadata,
                "executable": False,
                "regime": event.regime,
                "vol_ratio": event.vol_ratio,
                "return_1h_pct": event.return_1h_pct,
                "oi_change_1h_pct": event.oi_change_1h_pct,
            },
        )
        return [signal]

    def should_exit(
        self,
        signal: SignalCandidate,
        current_market: dict[str, Any],
        position_age_hours: float,
        unrealized_pnl_pct: float,
    ) -> tuple[bool, str]:
        if unrealized_pnl_pct <= -float(signal.stop_loss_pct):
            return True, "stop_loss_hit"
        if position_age_hours >= float(signal.max_holding_hours):
            return True, "max_holding_time_reached"
        return False, "hold"

    def risk_check(self, signal: SignalCandidate) -> tuple[bool, str]:
        if signal.strategy_type != self.strategy_type:
            return False, "wrong_strategy_type"
        if signal.suggested_notional_usdt > RISK_MAX_SINGLE_POSITION_USDT:
            return False, "position_size_above_limit"
        return False, "observation_only"
```

- [ ] **Step 4: Verify scanner tests pass**

Run:

```bash
PYTHONPATH=src uv run --with pytest --with pytest-asyncio pytest tests/strategies/test_trend_regime_scanner.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/strategies/trend_regime/scanner.py tests/strategies/test_trend_regime_scanner.py
git commit -m "test+feat: add trend regime phase1a scanner"
```

---

## Task 3: Add Trend Regime Shadow Simulator

**Files:**
- Create: `src/strategies/trend_regime/shadow_simulator.py`
- Test: `tests/strategies/test_trend_regime_shadow_simulator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/strategies/test_trend_regime_shadow_simulator.py`:

```python
from src.strategies.trend_regime.shadow_simulator import (
    TrendRegimeShadowPosition,
    simulate_trend_regime_shadow,
)


def test_long_shadow_pnl_subtracts_costs():
    position = TrendRegimeShadowPosition(
        symbol="BTC/USDT",
        direction="long",
        entry_time_ms=1000,
        entry_price=100.0,
        estimated_cost_bps=20.0,
        max_holding_hours=48.0,
        stop_loss_pct=2.0,
    )
    result = simulate_trend_regime_shadow(
        position,
        [{"timestamp_ms": 2000, "close_price": 103.0}],
    )
    assert result.net_pnl_bps == 280.0
    assert result.exit_reason == "path_exhausted"


def test_short_shadow_pnl_flips_direction():
    position = TrendRegimeShadowPosition(
        symbol="BTC/USDT",
        direction="short",
        entry_time_ms=1000,
        entry_price=100.0,
        estimated_cost_bps=20.0,
        max_holding_hours=48.0,
        stop_loss_pct=2.0,
    )
    result = simulate_trend_regime_shadow(
        position,
        [{"timestamp_ms": 2000, "close_price": 97.0}],
    )
    assert result.net_pnl_bps == 280.0


def test_shadow_exits_on_stop_loss():
    position = TrendRegimeShadowPosition(
        symbol="BTC/USDT",
        direction="long",
        entry_time_ms=1000,
        entry_price=100.0,
        estimated_cost_bps=20.0,
        max_holding_hours=48.0,
        stop_loss_pct=2.0,
    )
    result = simulate_trend_regime_shadow(
        position,
        [{"timestamp_ms": 2000, "close_price": 97.9}],
    )
    assert result.exit_reason == "stop_loss_hit"
    assert result.net_pnl_bps < 0.0


def test_shadow_exits_on_max_holding_time():
    position = TrendRegimeShadowPosition(
        symbol="BTC/USDT",
        direction="long",
        entry_time_ms=0,
        entry_price=100.0,
        estimated_cost_bps=20.0,
        max_holding_hours=1.0,
        stop_loss_pct=2.0,
    )
    result = simulate_trend_regime_shadow(
        position,
        [{"timestamp_ms": 3_600_000, "close_price": 101.0}],
    )
    assert result.exit_reason == "max_holding_time_reached"
```

- [ ] **Step 2: Verify failing tests**

Run:

```bash
PYTHONPATH=src uv run --with pytest pytest tests/strategies/test_trend_regime_shadow_simulator.py -q
```

Expected: FAIL because `shadow_simulator.py` does not exist.

- [ ] **Step 3: Implement simulator**

Create `src/strategies/trend_regime/shadow_simulator.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrendRegimeShadowPosition:
    symbol: str
    direction: str
    entry_time_ms: int
    entry_price: float
    estimated_cost_bps: float
    max_holding_hours: float
    stop_loss_pct: float


@dataclass(frozen=True)
class TrendRegimeShadowResult:
    symbol: str
    direction: str
    entry_time_ms: int
    exit_time_ms: int | None
    exit_price: float | None
    gross_pnl_bps: float
    net_pnl_bps: float
    exit_reason: str


def _gross_pnl_bps(direction: str, *, entry_price: float, exit_price: float) -> float:
    raw_return = ((exit_price - entry_price) / entry_price) * 10_000.0
    return raw_return if direction == "long" else -raw_return


def simulate_trend_regime_shadow(
    position: TrendRegimeShadowPosition,
    price_path: list[dict],
) -> TrendRegimeShadowResult:
    if not price_path:
        return TrendRegimeShadowResult(
            symbol=position.symbol,
            direction=position.direction,
            entry_time_ms=position.entry_time_ms,
            exit_time_ms=None,
            exit_price=None,
            gross_pnl_bps=0.0,
            net_pnl_bps=-position.estimated_cost_bps,
            exit_reason="path_exhausted",
        )

    last_row = price_path[-1]
    exit_reason = "path_exhausted"
    selected = last_row
    for row in price_path:
        exit_time_ms = int(row["timestamp_ms"])
        exit_price = float(row["close_price"])
        gross = _gross_pnl_bps(position.direction, entry_price=position.entry_price, exit_price=exit_price)
        age_hours = (exit_time_ms - position.entry_time_ms) / 3_600_000.0
        if gross <= -position.stop_loss_pct * 100.0:
            selected = row
            exit_reason = "stop_loss_hit"
            break
        if age_hours >= position.max_holding_hours:
            selected = row
            exit_reason = "max_holding_time_reached"
            break

    exit_time_ms = int(selected["timestamp_ms"])
    exit_price = float(selected["close_price"])
    gross = _gross_pnl_bps(position.direction, entry_price=position.entry_price, exit_price=exit_price)
    return TrendRegimeShadowResult(
        symbol=position.symbol,
        direction=position.direction,
        entry_time_ms=position.entry_time_ms,
        exit_time_ms=exit_time_ms,
        exit_price=exit_price,
        gross_pnl_bps=round(gross, 10),
        net_pnl_bps=round(gross - position.estimated_cost_bps, 10),
        exit_reason=exit_reason,
    )
```

- [ ] **Step 4: Verify simulator tests pass**

Run:

```bash
PYTHONPATH=src uv run --with pytest pytest tests/strategies/test_trend_regime_shadow_simulator.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/strategies/trend_regime/shadow_simulator.py tests/strategies/test_trend_regime_shadow_simulator.py
git commit -m "test+feat: add trend regime shadow simulator"
```

---

## Task 4: Add Observation Daemon Skeleton

**Files:**
- Create: `scripts/run_trend_regime_watchlist.py`
- Test: `tests/scripts/test_run_trend_regime_watchlist.py`

- [ ] **Step 1: Write failing tests**

Create `tests/scripts/test_run_trend_regime_watchlist.py`:

```python
import json

from scripts.run_trend_regime_watchlist import (
    append_jsonl,
    build_snapshot,
    summarize_reject_counts,
    run_trend_regime_poll_once,
)
from src.strategies.trend_regime.scanner import TrendRegimeStrategy


def test_build_snapshot_drops_unknown_fields():
    snapshot = build_snapshot({"symbol": "BTC/USDT", "return_1h_pct": 2.0, "private_key": "x"})
    assert snapshot["symbol"] == "BTC/USDT"
    assert "private_key" not in snapshot


def test_run_poll_once_returns_signals_and_rejects():
    result = run_trend_regime_poll_once(
        rows=[
            {
                "timestamp_ms": 1,
                "exchange": "binance",
                "symbol": "BTC/USDT",
                "close_price": 100000.0,
                "return_1h_pct": 2.5,
                "vol_1h_pct": 3.0,
                "vol_baseline_30d_pct": 1.0,
                "open_interest": 100000000.0,
                "oi_change_1h_pct": 3.0,
                "liquidation_notional_1h_usdt": 0.0,
                "volume_24h_usdt": 1000000000.0,
                "estimated_spread_bps": 4.0,
                "estimated_slippage_bps": 6.0,
                "data_age_sec": 5.0,
            },
            {
                "timestamp_ms": 1,
                "exchange": "binance",
                "symbol": "ETH/USDT",
                "close_price": 3000.0,
                "return_1h_pct": 0.1,
                "vol_1h_pct": 0.5,
                "vol_baseline_30d_pct": 1.0,
                "open_interest": 100000000.0,
                "oi_change_1h_pct": 0.1,
                "liquidation_notional_1h_usdt": 0.0,
                "volume_24h_usdt": 1000000000.0,
                "estimated_spread_bps": 4.0,
                "estimated_slippage_bps": 6.0,
                "data_age_sec": 5.0,
            },
        ],
        strategy=TrendRegimeStrategy(),
    )
    assert len(result["signals"]) == 1
    assert result["reject_reasons"] == ["vol_breakout_below_threshold"]


def test_append_jsonl_writes_record(tmp_path):
    path = tmp_path / "trend.jsonl"
    append_jsonl(path, {"type": "heartbeat", "signals": 0})
    assert json.loads(path.read_text(encoding="utf-8")) == {"signals": 0, "type": "heartbeat"}


def test_summarize_reject_counts():
    assert summarize_reject_counts(["a", "a", "b"]) == {"a": 2, "b": 1}
```

- [ ] **Step 2: Verify failing tests**

Run:

```bash
PYTHONPATH=src uv run --with pytest --with pytest-asyncio pytest tests/scripts/test_run_trend_regime_watchlist.py -q
```

Expected: FAIL because script does not exist.

- [ ] **Step 3: Implement daemon helper functions**

Create `scripts/run_trend_regime_watchlist.py`:

```python
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import argparse
import asyncio
import json

from loguru import logger

from configs.base import TREND_REGIME_EVENT_LOG_JSONL
from src.strategies.trend_regime.scanner import TrendRegimeStrategy, classify_trend_regime_snapshot


PUBLIC_TREND_SNAPSHOT_FIELDS = {
    "timestamp_ms",
    "exchange",
    "symbol",
    "close_price",
    "return_1h_pct",
    "vol_1h_pct",
    "vol_baseline_30d_pct",
    "open_interest",
    "oi_change_1h_pct",
    "liquidation_notional_1h_usdt",
    "volume_24h_usdt",
    "estimated_spread_bps",
    "estimated_slippage_bps",
    "data_age_sec",
}


def build_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    return {key: raw.get(key) for key in PUBLIC_TREND_SNAPSHOT_FIELDS}


def summarize_reject_counts(reasons: list[str]) -> dict[str, int]:
    return dict(Counter(reasons))


def append_jsonl(filepath: Path, data: dict[str, Any]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, sort_keys=True, default=str) + "\n")


async def _scan_one(strategy: TrendRegimeStrategy, snapshot: dict[str, Any]):
    return await strategy.scan(snapshot)


def run_trend_regime_poll_once(
    *,
    rows: list[dict[str, Any]],
    strategy: TrendRegimeStrategy,
) -> dict[str, Any]:
    signals = []
    reject_reasons = []
    snapshots = []
    for raw in rows:
        snapshot = build_snapshot(raw)
        snapshots.append(snapshot)
        classification = classify_trend_regime_snapshot(snapshot)
        if classification.reject_reason is not None:
            reject_reasons.append(classification.reject_reason)
            continue
        signal = asyncio.run(_scan_one(strategy, snapshot))
        signals.extend(signal)
    return {"signals": signals, "reject_reasons": reject_reasons, "snapshots": snapshots}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Trend/Liquidation Phase 1A watchlist skeleton.")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--once", action="store_true")
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    event_log_path = Path(args.data_root) / TREND_REGIME_EVENT_LOG_JSONL
    logger.info(f"trend_regime_watchlist_ready log={event_log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

- [ ] **Step 4: Verify script tests pass**

Run:

```bash
PYTHONPATH=src uv run --with pytest --with pytest-asyncio pytest tests/scripts/test_run_trend_regime_watchlist.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_trend_regime_watchlist.py tests/scripts/test_run_trend_regime_watchlist.py
git commit -m "test+feat: add trend regime watchlist skeleton"
```

---

## Task 5: Add Shadow Replay Script And Review Gate

**Files:**
- Create: `scripts/replay_trend_regime_shadow.py`
- Test: `tests/scripts/test_replay_trend_regime_shadow.py`

- [ ] **Step 1: Write failing tests**

Create `tests/scripts/test_replay_trend_regime_shadow.py`:

```python
import json

from scripts.replay_trend_regime_shadow import build_shadow_summary, load_rows_jsonl


def test_load_rows_jsonl_reads_records(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text(json.dumps({"symbol": "BTC/USDT"}) + "\n", encoding="utf-8")
    assert load_rows_jsonl(path) == [{"symbol": "BTC/USDT"}]


def test_build_shadow_summary_reports_positive_expectancy():
    rows = [
        {"timestamp_ms": 0, "symbol": "BTC/USDT", "direction": "long", "entry_price": 100.0},
        {"timestamp_ms": 3_600_000, "symbol": "BTC/USDT", "close_price": 103.0},
    ]
    summary = build_shadow_summary(rows, estimated_cost_bps=20.0)
    assert summary["shadow_trade_count"] == 1
    assert summary["mean_net_pnl_bps"] == 280.0
    assert summary["positive_expectancy"] is True
```

- [ ] **Step 2: Verify failing tests**

Run:

```bash
PYTHONPATH=src uv run --with pytest pytest tests/scripts/test_replay_trend_regime_shadow.py -q
```

Expected: FAIL because script does not exist.

- [ ] **Step 3: Implement replay script**

Create `scripts/replay_trend_regime_shadow.py`:

```python
from __future__ import annotations

from statistics import mean, median
from pathlib import Path
import argparse
import json

from configs.base import (
    TREND_REGIME_MAX_HOLDING_HOURS,
    TREND_REGIME_OBSERVATION_COST_BPS,
    TREND_REGIME_STOP_LOSS_PCT,
)
from src.strategies.trend_regime.shadow_simulator import (
    TrendRegimeShadowPosition,
    simulate_trend_regime_shadow,
)


def load_rows_jsonl(path: str | Path) -> list[dict]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    return [json.loads(line) for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_shadow_summary(rows: list[dict], *, estimated_cost_bps: float) -> dict:
    results = []
    for index, row in enumerate(rows):
        if "entry_price" not in row or "direction" not in row:
            continue
        path_rows = [item for item in rows[index + 1 :] if item.get("symbol") == row.get("symbol")]
        if not path_rows:
            continue
        position = TrendRegimeShadowPosition(
            symbol=str(row["symbol"]),
            direction=str(row["direction"]),
            entry_time_ms=int(row["timestamp_ms"]),
            entry_price=float(row["entry_price"]),
            estimated_cost_bps=estimated_cost_bps,
            max_holding_hours=float(TREND_REGIME_MAX_HOLDING_HOURS),
            stop_loss_pct=float(TREND_REGIME_STOP_LOSS_PCT),
        )
        results.append(simulate_trend_regime_shadow(position, path_rows))

    pnl = [item.net_pnl_bps for item in results]
    return {
        "shadow_trade_count": len(results),
        "mean_net_pnl_bps": mean(pnl) if pnl else 0.0,
        "median_net_pnl_bps": median(pnl) if pnl else 0.0,
        "win_rate": (sum(1 for value in pnl if value > 0.0) / len(pnl)) if pnl else 0.0,
        "positive_expectancy": bool(pnl and mean(pnl) > 0.0),
        "coverage_quality": "trend_regime_shadow_proxy",
        "live_approved": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay Trend/Liquidation shadow rows.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    summary = build_shadow_summary(
        load_rows_jsonl(args.input),
        estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify replay script tests pass**

Run:

```bash
PYTHONPATH=src uv run --with pytest pytest tests/scripts/test_replay_trend_regime_shadow.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/replay_trend_regime_shadow.py tests/scripts/test_replay_trend_regime_shadow.py
git commit -m "test+feat: add trend regime shadow replay"
```

---

## Task 6: Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run targeted tests**

Run:

```bash
PYTHONPATH=src uv run --with pytest --with pytest-asyncio pytest \
  tests/test_trend_regime_config.py \
  tests/strategies/test_trend_regime_scanner.py \
  tests/strategies/test_trend_regime_shadow_simulator.py \
  tests/scripts/test_run_trend_regime_watchlist.py \
  tests/scripts/test_replay_trend_regime_shadow.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run:

```bash
PYTHONPATH=src uv run --with pytest --with pytest-asyncio pytest -q
```

Expected: PASS.

- [ ] **Step 3: Confirm no execution imports**

Run:

```bash
rg -n "src\\.execution|from execution|import execution" src/strategies/trend_regime scripts/run_trend_regime_watchlist.py scripts/replay_trend_regime_shadow.py
```

Expected: no output.

- [ ] **Step 4: Commit any final fixes**

If previous commands required small fixes:

```bash
git add <changed-files>
git commit -m "test: verify trend regime phase1a"
```

If no files changed, do not create an empty commit.

---

## Done Definition

This plan is complete when:

- Trend/Liquidation has explicit config in `configs/base.py`.
- `TrendRegimeStrategy.scan(...)` returns observation-only `SignalCandidate` objects.
- `risk_check(...)` blocks execution with `observation_only`.
- `should_exit(...)` supports stop loss and max holding time.
- Shadow simulator computes directional PnL for long and short paths after costs.
- Watchlist script can write JSONL evidence and summarize rejects.
- Replay script can produce a shadow summary with `positive_expectancy`.
- No new code imports `src/execution/`.
- Full test suite passes.

## Post-Implementation Review Gate

After implementation, do not treat this as live-ready. The next review must answer:

- Did Phase 1A produce at least 5 signals in a representative replay or observation window?
- Is `mean_net_pnl_bps > 0` after `TREND_REGIME_OBSERVATION_COST_BPS=20`?
- Is `median_net_pnl_bps > 0`?
- Is `win_rate > 50%`?
- Are losses mainly from stop loss rather than data/logic errors?
- Is max adverse slippage still `<= 10 bps`?

If these are not satisfied, keep Trend/Liquidation in observation mode.

