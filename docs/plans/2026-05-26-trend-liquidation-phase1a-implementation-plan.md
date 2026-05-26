# Trend / Liquidation Phase 1A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `Trend / Liquidation Regime Scanner` 的 Phase 1A 观察与影子验证底座，用于识别方向性波动突破和清算延续机会，但不接入 `execution`。

**Architecture:** 本阶段拆成三层：`watch_event` 只负责发现波动/清算 regime，`TrendRegimeObservationStrategy` 只生成 observation-only `SignalCandidate`，`shadow replay` 只验证成本后方向性收益。所有阈值进入 `configs/base.py`，策略逻辑与执行逻辑保持隔离。

**Tech Stack:** Python 3.11, dataclasses, pytest, loguru, existing `SignalCandidate`, existing `configs/base.py`, JSONL evidence under `data/`, reports under `reports/trend_regime/`.

---

## 1. Review Adoption Summary

本版采纳两位 reviewer 的核心意见：

- 采纳：`run_trend_regime_poll_once(...)` 必须是 `async def`，避免在已运行事件循环内调用 `asyncio.run(...)`。
- 采纳：`replay_trend_regime_shadow.py` 必须从 raw market rows 调用 `classify_trend_regime_snapshot(...)` 自动发现 entry，不依赖输入行提前带有 `entry_price` / `direction`。
- 采纳：`expected_edge_bps` 不得用过去 1h return 伪装成未来 edge。Phase 1A 统一写 `expected_edge_bps=0.0`，并把过去涨跌幅放入 `metadata["past_move_bps"]`。
- 采纳：个人投资者默认参数收紧，减少方向性持仓暴露。默认持仓从 `48h` 改为 `12h`，成本从 `20 bps` 改为 `30 bps`，新增 `50 bps` stress cost。
- 采纳：限制 Phase 1A universe 到高流动性标的，并拆分 `major` 与 `large_alt` 阈值。
- 采纳：shadow summary 必须按 `regime` / `direction` / `symbol_tier` 分组，避免混合均值掩盖风险。

暂不采纳或后置：

- 暂不加入 `take_profit` / `trailing_stop`。Phase 1A 先用 `stop_loss` + `max_holding_hours` 做可复现基线，后续若 replay 有正期望再做 exit 复杂化。
- 暂不把 liquidation cascade 同时模拟 continuation 和 mean reversion。本阶段先验证 continuation 假设；若失败，再单独起反转假设计划。

---

## 2. Phase Boundary

本计划只做 Phase 1A，不做实盘：

- 不导入 `src/execution/`。
- 不读取 private API key。
- 不改 `RISK_LIVE_TRADING_ENABLED`。
- 不生成 `executable=True`。
- 不把方向性信号解释为套利信号。

Phase 1A 只回答：

- 市场是否出现 `vol_breakout` 或 `liquidation_cascade` regime。
- 这些 regime 是否能形成 observation-only `SignalCandidate`。
- 历史/影子模拟在 `30 bps` base cost 与 `50 bps` stress cost 下是否仍有正期望。

---

## 3. Files

- Modify: `configs/base.py`
- Create: `src/strategies/trend_regime/scanner.py`
- Create: `src/strategies/trend_regime/shadow_simulator.py`
- Create: `scripts/run_trend_regime_watchlist.py`
- Create: `scripts/replay_trend_regime_shadow.py`
- Test: `tests/test_trend_regime_config.py`
- Test: `tests/strategies/test_trend_regime_scanner.py`
- Test: `tests/strategies/test_trend_regime_shadow_simulator.py`
- Test: `tests/scripts/test_run_trend_regime_watchlist.py`
- Test: `tests/scripts/test_replay_trend_regime_shadow.py`

---

## 4. Data Contract

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
    "funding_state": "neutral",
    "data_age_sec": 5.0,
}
```

分类输出：

- `no_event`
- `vol_breakout_long`
- `vol_breakout_short`
- `liquidation_cascade_long`
- `liquidation_cascade_short`

术语约定：

- `liquidation_cascade_long` / `liquidation_cascade_short` 的后缀代表策略方向，不代表被清算仓位方向。
- 例如空头爆仓推动价格上涨，策略方向是顺势做多，因此是 `liquidation_cascade_long`。

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
    assert base.TREND_REGIME_WATCH_SYMBOLS == (
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "XRP/USDT",
        "DOGE/USDT",
    )
    assert base.TREND_REGIME_MAJOR_SYMBOLS == ("BTC/USDT", "ETH/USDT")
    assert base.TREND_REGIME_LARGE_ALT_SYMBOLS == ("SOL/USDT", "XRP/USDT", "DOGE/USDT")
    assert base.TREND_REGIME_VOL_BREAKOUT_MULTIPLIER == 2.5
    assert base.TREND_REGIME_MAX_HOLDING_HOURS == 12
    assert base.TREND_REGIME_STOP_LOSS_PCT == 1.5
    assert base.TREND_REGIME_MIN_1H_ABS_RETURN_PCT_MAJOR == 2.0
    assert base.TREND_REGIME_MIN_1H_ABS_RETURN_PCT_LARGE_ALT == 2.5
    assert base.TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_MAJOR == 1.5
    assert base.TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_LARGE_ALT == 2.0
    assert base.TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_MAJOR == 10_000_000.0
    assert base.TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_LARGE_ALT == 3_000_000.0
    assert base.TREND_REGIME_MIN_24H_VOLUME_USDT == 300_000_000.0
    assert base.TREND_REGIME_MAX_DATA_AGE_SEC == 30
    assert base.TREND_REGIME_OBSERVATION_COST_BPS == 30.0
    assert base.TREND_REGIME_STRESS_COST_BPS == 50.0
    assert base.TREND_REGIME_MAX_SLIPPAGE_BPS == 8.0
    assert base.TREND_REGIME_EVENT_LOG_JSONL == "trend_regime_watch_events.jsonl"
```

- [ ] **Step 2: Verify failing test**

Run:

```bash
PYTHONPATH=src uv run --with pytest pytest tests/test_trend_regime_config.py -q
```

Expected: FAIL with missing config attributes.

- [ ] **Step 3: Add config constants**

Replace the current Trend/Liquidation config block in `configs/base.py` with:

```python
# ─── Strategy: Trend / Liquidation Regime ────────────────────────────────────

TREND_REGIME_WATCH_SYMBOLS = (
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "DOGE/USDT",
)
# Phase 1A universe. Keep this narrow for personal-capital directional strategies.

TREND_REGIME_MAJOR_SYMBOLS = ("BTC/USDT", "ETH/USDT")
# Major symbols use slightly lower movement/liquidation thresholds.

TREND_REGIME_LARGE_ALT_SYMBOLS = ("SOL/USDT", "XRP/USDT", "DOGE/USDT")
# Large alt symbols need stronger movement/OI confirmation because noise is higher.

TREND_REGIME_VOL_BREAKOUT_MULTIPLIER = 2.5
# Current 1h volatility must exceed N x 30-day baseline to qualify as a vol breakout.

TREND_REGIME_MAX_HOLDING_HOURS = 12
# Maximum holding period. Shorter exposure is safer for personal directional trading.

TREND_REGIME_STOP_LOSS_PCT = 1.5
# Per-trade stop loss in percent of entry price. Hard stop, not trailing.

TREND_REGIME_MIN_1H_ABS_RETURN_PCT_MAJOR = 2.0
# Minimum absolute 1h return for BTC/ETH trend regime detection.

TREND_REGIME_MIN_1H_ABS_RETURN_PCT_LARGE_ALT = 2.5
# Minimum absolute 1h return for SOL/XRP/DOGE trend regime detection.

TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_MAJOR = 1.5
# Minimum absolute 1h OI change for BTC/ETH confirmation.

TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_LARGE_ALT = 2.0
# Minimum absolute 1h OI change for large alt confirmation.

TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_MAJOR = 10_000_000.0
# Minimum 1h liquidation notional for BTC/ETH liquidation-cascade classification.

TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_LARGE_ALT = 3_000_000.0
# Minimum 1h liquidation notional for SOL/XRP/DOGE liquidation-cascade classification.

TREND_REGIME_MIN_24H_VOLUME_USDT = 300_000_000.0
# Minimum 24h volume for Phase 1A trend observation.

TREND_REGIME_MAX_DATA_AGE_SEC = 30
# Maximum public-market-data age before rejecting the row as stale.

TREND_REGIME_OBSERVATION_COST_BPS = 30.0
# Base cost assumption for shadow validation, including fees and normal slippage.

TREND_REGIME_STRESS_COST_BPS = 50.0
# Stress cost assumption for liquidation/trend regimes where exits may slip.

TREND_REGIME_MAX_SLIPPAGE_BPS = 8.0
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
    TrendRegimeObservationStrategy,
    TrendRegimeWatchEvent,
    classify_trend_regime_snapshot,
    symbol_tier,
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
        "funding_state": "neutral",
        "data_age_sec": 5.0,
    }
    row.update(overrides)
    return row


def test_symbol_tier_classifies_major_and_large_alt():
    assert symbol_tier("BTC/USDT") == "major"
    assert symbol_tier("SOL/USDT") == "large_alt"
    assert symbol_tier("UNKNOWN/USDT") == "unsupported"


def test_classifies_vol_breakout_long():
    result = classify_trend_regime_snapshot(_snapshot())
    assert result.event is not None
    assert isinstance(result.event, TrendRegimeWatchEvent)
    assert result.event.regime == "vol_breakout_long"
    assert result.event.direction == "long"
    assert result.event.executable is False


def test_classifies_vol_breakout_short_with_stricter_short_metadata():
    result = classify_trend_regime_snapshot(_snapshot(return_1h_pct=-2.5, oi_change_1h_pct=3.0))
    assert result.event is not None
    assert result.event.regime == "vol_breakout_short"
    assert result.event.direction == "short"
    assert result.event.metadata["funding_state"] == "neutral"


def test_classifies_alt_liquidation_cascade_with_alt_threshold():
    result = classify_trend_regime_snapshot(
        _snapshot(
            symbol="DOGE/USDT",
            return_1h_pct=3.0,
            vol_1h_pct=4.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=-3.0,
            liquidation_notional_1h_usdt=3_500_000.0,
        )
    )
    assert result.event is not None
    assert result.event.regime == "liquidation_cascade_long"
    assert result.event.direction == "long"
    assert result.event.metadata["symbol_tier"] == "large_alt"


def test_rejects_unsupported_symbol_stale_and_illiquid_rows():
    unsupported = classify_trend_regime_snapshot(_snapshot(symbol="PEPE/USDT"))
    assert unsupported.reject_reason == "symbol_not_in_watchlist"

    stale = classify_trend_regime_snapshot(_snapshot(data_age_sec=120.0))
    assert stale.reject_reason == "api_stale"

    illiquid = classify_trend_regime_snapshot(_snapshot(volume_24h_usdt=100_000_000.0))
    assert illiquid.reject_reason == "volume_below_min"


def test_rejects_when_vol_or_return_is_not_large_enough():
    low_vol = classify_trend_regime_snapshot(_snapshot(vol_1h_pct=2.0, vol_baseline_30d_pct=1.0))
    assert low_vol.reject_reason == "vol_breakout_below_threshold"

    low_return = classify_trend_regime_snapshot(_snapshot(return_1h_pct=1.0))
    assert low_return.reject_reason == "return_below_min"


@pytest.mark.asyncio
async def test_observation_strategy_scan_returns_observation_signal_candidate():
    strategy = TrendRegimeObservationStrategy()
    signals = await strategy.scan(_snapshot())

    assert len(signals) == 1
    signal = signals[0]
    assert isinstance(signal, SignalCandidate)
    assert signal.strategy_type == "trend_regime"
    assert signal.direction == "long"
    assert signal.expected_edge_bps == 0.0
    assert signal.metadata["mode"] == "observation"
    assert signal.metadata["executable"] is False
    assert signal.metadata["edge_status"] == "unknown_until_shadow"
    assert signal.metadata["past_move_bps"] == 250.0


def test_should_exit_on_stop_loss_or_time_limit():
    strategy = TrendRegimeObservationStrategy()
    signal = SignalCandidate(
        strategy_type="trend_regime",
        symbol="BTC/USDT",
        direction="long",
        confidence=0.55,
        expected_edge_bps=0.0,
        entry_exchange="binance",
        hedge_exchange="binance",
        trigger_reason="vol_breakout_long",
        invalidation_reason="stop_loss_or_time_limit",
        max_holding_hours=12.0,
        stop_loss_pct=1.5,
        suggested_notional_usdt=500.0,
        metadata={"entry_price": 100000.0},
    )
    assert strategy.should_exit(signal, {}, 1.0, -1.6) == (True, "stop_loss_hit")
    assert strategy.should_exit(signal, {}, 13.0, 0.1) == (True, "max_holding_time_reached")
    assert strategy.should_exit(signal, {}, 1.0, 0.1) == (False, "hold")


def test_risk_check_blocks_execution_even_for_valid_observation_signal():
    strategy = TrendRegimeObservationStrategy()
    signal = SignalCandidate(
        strategy_type="trend_regime",
        symbol="BTC/USDT",
        direction="long",
        confidence=0.55,
        expected_edge_bps=0.0,
        entry_exchange="binance",
        hedge_exchange="binance",
        trigger_reason="vol_breakout_long",
        invalidation_reason="stop_loss_or_time_limit",
        max_holding_hours=12.0,
        stop_loss_pct=1.5,
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

- [ ] **Step 3: Implement scanner**

Create `src/strategies/trend_regime/scanner.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from configs.base import (
    RISK_MAX_SINGLE_POSITION_USDT,
    TREND_REGIME_LARGE_ALT_SYMBOLS,
    TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_LARGE_ALT,
    TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_MAJOR,
    TREND_REGIME_MAJOR_SYMBOLS,
    TREND_REGIME_MAX_DATA_AGE_SEC,
    TREND_REGIME_MAX_HOLDING_HOURS,
    TREND_REGIME_MAX_SLIPPAGE_BPS,
    TREND_REGIME_MIN_1H_ABS_RETURN_PCT_LARGE_ALT,
    TREND_REGIME_MIN_1H_ABS_RETURN_PCT_MAJOR,
    TREND_REGIME_MIN_24H_VOLUME_USDT,
    TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_LARGE_ALT,
    TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_MAJOR,
    TREND_REGIME_OBSERVATION_COST_BPS,
    TREND_REGIME_STOP_LOSS_PCT,
    TREND_REGIME_VOL_BREAKOUT_MULTIPLIER,
    TREND_REGIME_WATCH_SYMBOLS,
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


def symbol_tier(symbol: str) -> str:
    if symbol in TREND_REGIME_MAJOR_SYMBOLS:
        return "major"
    if symbol in TREND_REGIME_LARGE_ALT_SYMBOLS:
        return "large_alt"
    return "unsupported"


def _tier_thresholds(symbol: str) -> tuple[float, float, float]:
    tier = symbol_tier(symbol)
    if tier == "major":
        return (
            TREND_REGIME_MIN_1H_ABS_RETURN_PCT_MAJOR,
            TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_MAJOR,
            TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_MAJOR,
        )
    return (
        TREND_REGIME_MIN_1H_ABS_RETURN_PCT_LARGE_ALT,
        TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_LARGE_ALT,
        TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_LARGE_ALT,
    )


def classify_trend_regime_snapshot(row: dict[str, Any]) -> TrendRegimeClassification:
    symbol = str(row.get("symbol") or "")
    if not symbol:
        return TrendRegimeClassification(None, "missing_symbol")
    if symbol not in TREND_REGIME_WATCH_SYMBOLS:
        return TrendRegimeClassification(None, "symbol_not_in_watchlist")

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

    min_return_pct, min_oi_pct, min_liquidation_usdt = _tier_thresholds(symbol)
    vol_ratio = vol_1h_pct / vol_baseline_30d_pct
    if vol_ratio < TREND_REGIME_VOL_BREAKOUT_MULTIPLIER:
        return TrendRegimeClassification(None, "vol_breakout_below_threshold")
    if abs(return_1h_pct) < min_return_pct:
        return TrendRegimeClassification(None, "return_below_min")
    if abs(oi_change_1h_pct) < min_oi_pct:
        return TrendRegimeClassification(None, "oi_confirmation_below_min")

    direction = "long" if return_1h_pct > 0.0 else "short"
    if oi_change_1h_pct > 0.0:
        regime = f"vol_breakout_{direction}"
    elif liquidation_notional >= min_liquidation_usdt:
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
            "symbol_tier": symbol_tier(symbol),
            "funding_state": str(row.get("funding_state") or "unknown"),
            "estimated_cost_bps": TREND_REGIME_OBSERVATION_COST_BPS,
            "estimated_slippage_bps": slippage_bps,
        },
    )
    return TrendRegimeClassification(event, None)


class TrendRegimeObservationStrategy(BaseStrategy):
    strategy_type = "trend_regime"

    async def scan(self, market_data: dict[str, Any]) -> list[SignalCandidate]:
        result = classify_trend_regime_snapshot(market_data)
        if result.event is None:
            return []
        event = result.event
        past_move_bps = abs(event.return_1h_pct) * 100.0
        signal = SignalCandidate(
            strategy_type="trend_regime",
            symbol=event.symbol,
            direction=event.direction,
            confidence=0.55,
            expected_edge_bps=0.0,
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
                "past_move_bps": past_move_bps,
                "edge_status": "unknown_until_shadow",
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

Use the simulator contract from the first plan version, with these values updated in tests:

- `estimated_cost_bps=30.0`
- `max_holding_hours=12.0`
- `stop_loss_pct=1.5`

Additional tests must be included:

```python
def test_empty_path_returns_cost_loss_and_path_exhausted():
    ...


def test_short_stop_loss_uses_directional_pnl():
    ...
```

Verification command:

```bash
PYTHONPATH=src uv run --with pytest pytest tests/strategies/test_trend_regime_shadow_simulator.py -q
```

Commit:

```bash
git add src/strategies/trend_regime/shadow_simulator.py tests/strategies/test_trend_regime_shadow_simulator.py
git commit -m "test+feat: add trend regime shadow simulator"
```

---

## Task 4: Add Async Observation Daemon Skeleton

**Files:**
- Create: `scripts/run_trend_regime_watchlist.py`
- Test: `tests/scripts/test_run_trend_regime_watchlist.py`

Required contract changes from review:

- `run_trend_regime_poll_once(...)` must be `async def`.
- It must call `await strategy.scan(snapshot)`.
- It must not call `asyncio.run(...)` inside a running loop.

Test must include:

```python
@pytest.mark.asyncio
async def test_run_poll_once_returns_signals_and_rejects():
    result = await run_trend_regime_poll_once(...)
    assert len(result["signals"]) == 1
```

Implementation skeleton:

```python
async def run_trend_regime_poll_once(
    *,
    rows: list[dict[str, Any]],
    strategy: TrendRegimeObservationStrategy,
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
        signal = await strategy.scan(snapshot)
        signals.extend(signal)
    return {"signals": signals, "reject_reasons": reject_reasons, "snapshots": snapshots}
```

Verification command:

```bash
PYTHONPATH=src uv run --with pytest --with pytest-asyncio pytest tests/scripts/test_run_trend_regime_watchlist.py -q
```

Commit:

```bash
git add scripts/run_trend_regime_watchlist.py tests/scripts/test_run_trend_regime_watchlist.py
git commit -m "test+feat: add trend regime watchlist skeleton"
```

---

## Task 5: Add Raw-Row Shadow Replay Script

**Files:**
- Create: `scripts/replay_trend_regime_shadow.py`
- Test: `tests/scripts/test_replay_trend_regime_shadow.py`

Required contract changes from review:

- Replay input is raw market rows.
- Replay must call `classify_trend_regime_snapshot(row)` to discover entry points.
- Replay must use only later rows from the same `symbol`.
- Replay must not cross symbols.
- Replay must output grouped summaries by `regime`, `direction`, and `symbol_tier`.
- Replay must run both base cost (`TREND_REGIME_OBSERVATION_COST_BPS`) and stress cost (`TREND_REGIME_STRESS_COST_BPS`).

Required tests:

```python
def test_replay_discovers_entry_from_raw_rows():
    ...


def test_replay_does_not_cross_symbols():
    ...


def test_replay_uses_only_future_rows():
    ...


def test_replay_outputs_grouped_summary_by_regime_direction_and_tier():
    ...


def test_replay_outputs_base_and_stress_cost_summaries:
    ...
```

Core implementation shape:

```python
def build_shadow_summary(rows: list[dict], *, estimated_cost_bps: float) -> dict:
    results = []
    insufficient_path_count = 0
    for index, row in enumerate(rows):
        classification = classify_trend_regime_snapshot(row)
        if classification.event is None:
            continue
        event = classification.event
        path_rows = [
            item
            for item in rows[index + 1 :]
            if item.get("symbol") == event.symbol
            and int(item.get("timestamp_ms", 0)) > int(row["timestamp_ms"])
        ]
        if not path_rows:
            insufficient_path_count += 1
            continue
        position = TrendRegimeShadowPosition(
            symbol=event.symbol,
            direction=event.direction,
            entry_time_ms=int(row["timestamp_ms"]),
            entry_price=float(row["close_price"]),
            estimated_cost_bps=estimated_cost_bps,
            max_holding_hours=float(TREND_REGIME_MAX_HOLDING_HOURS),
            stop_loss_pct=float(TREND_REGIME_STOP_LOSS_PCT),
        )
        simulated = simulate_trend_regime_shadow(position, path_rows)
        results.append((event, simulated))
```

Verification command:

```bash
PYTHONPATH=src uv run --with pytest pytest tests/scripts/test_replay_trend_regime_shadow.py -q
```

Commit:

```bash
git add scripts/replay_trend_regime_shadow.py tests/scripts/test_replay_trend_regime_shadow.py
git commit -m "test+feat: add trend regime raw-row shadow replay"
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

- [ ] **Step 4: Commit final fixes if any**

If previous commands required small fixes:

```bash
git add <changed-files>
git commit -m "test: verify trend regime phase1a"
```

If no files changed, do not create an empty commit.

---

## Done Definition

This plan is complete when:

- Trend/Liquidation has explicit personal-capital-safe config in `configs/base.py`.
- `TrendRegimeObservationStrategy.scan(...)` returns observation-only `SignalCandidate` objects.
- `expected_edge_bps` is always `0.0` in Phase 1A candidates.
- `metadata["edge_status"] == "unknown_until_shadow"`.
- `risk_check(...)` blocks execution with `observation_only`.
- `should_exit(...)` supports stop loss and max holding time.
- Shadow simulator computes directional PnL for long and short paths after costs.
- Watchlist script uses async poll once and does not nest `asyncio.run(...)`.
- Replay script discovers entries from raw rows via classifier.
- Replay summary is grouped by `regime`, `direction`, and `symbol_tier`.
- Replay reports base cost and stress cost results.
- No new code imports `src/execution/`.
- Full test suite passes.

## Post-Implementation Review Gate

After implementation, do not treat this as live-ready. The next review must answer:

- `signal_count >= 20` in representative replay or observation window.
- `median_net_pnl_bps > 30` under base cost.
- `mean_net_pnl_bps > 40` under base cost.
- `win_rate > 55%` under base cost.
- stress cost `50 bps` still has `median_net_pnl_bps > 0`.
- `worst_trade_net_pnl_bps > -200`.
- `stop_loss_exit_rate < 35%`.
- Long and short are reported separately.
- `vol_breakout` and `liquidation_cascade` are reported separately.
- `major` and `large_alt` are reported separately.

If these are not satisfied, keep Trend/Liquidation in observation mode.
