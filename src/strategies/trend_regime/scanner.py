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
