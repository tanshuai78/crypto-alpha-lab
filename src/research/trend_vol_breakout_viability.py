from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from configs.base import (
    TREND_REGIME_MAX_DATA_AGE_SEC,
    TREND_REGIME_MAX_SLIPPAGE_BPS,
    TREND_REGIME_MIN_24H_VOLUME_USDT,
    TREND_REGIME_OBSERVATION_COST_BPS,
    TREND_REGIME_VOL_BREAKOUT_MULTIPLIER,
    TREND_REGIME_WATCH_SYMBOLS,
)
from src.strategies.trend_regime.scanner import (
    TrendRegimeClassification,
    TrendRegimeWatchEvent,
    _number_or_none,
    _tier_thresholds,
    symbol_tier,
)


@dataclass(frozen=True)
class VolBreakoutReviewThresholds:
    name: str
    vol_multiplier: float
    major_min_return_pct: float
    large_alt_min_return_pct: float
    major_min_oi_pct: float
    large_alt_min_oi_pct: float
    assumption_level: str
    eligible_for_redefinition: bool

    @classmethod
    def baseline_current(cls) -> VolBreakoutReviewThresholds:
        # baseline_current = (2.5, 2.0, 2.5, 1.5, 2.0)
        return cls(
            name="baseline_current",
            vol_multiplier=2.5,
            major_min_return_pct=2.0,
            large_alt_min_return_pct=2.5,
            major_min_oi_pct=1.5,
            large_alt_min_oi_pct=2.0,
            assumption_level="current_live_baseline",
            eligible_for_redefinition=True,
        )

    @classmethod
    def moderately_relaxed(cls) -> VolBreakoutReviewThresholds:
        # moderately_relaxed = (2.0, 1.5, 2.0, 1.0, 1.5)
        return cls(
            name="moderately_relaxed",
            vol_multiplier=2.0,
            major_min_return_pct=1.5,
            large_alt_min_return_pct=2.0,
            major_min_oi_pct=1.0,
            large_alt_min_oi_pct=1.5,
            assumption_level="candidate_redefinition_boundary",
            eligible_for_redefinition=True,
        )

    @classmethod
    def aggressive_relaxed(cls) -> VolBreakoutReviewThresholds:
        # aggressive_relaxed = (1.8, 1.2, 1.8, 0.8, 1.2)
        return cls(
            name="aggressive_relaxed",
            vol_multiplier=1.8,
            major_min_return_pct=1.2,
            large_alt_min_return_pct=1.8,
            major_min_oi_pct=0.8,
            large_alt_min_oi_pct=1.2,
            assumption_level="diagnostic_noise_boundary",
            eligible_for_redefinition=False,
        )


def classify_vol_breakout_only_for_review(
    row: dict[str, Any],
    *,
    thresholds: VolBreakoutReviewThresholds | None = None,
) -> TrendRegimeClassification:
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
    slippage_bps = _number_or_none(row.get("estimated_slippage_bps"))

    if return_1h_pct is None or vol_1h_pct is None or vol_baseline_30d_pct is None:
        return TrendRegimeClassification(None, "missing_price_or_vol")
    if oi_change_1h_pct is None:
        return TrendRegimeClassification(None, "missing_oi")
    if vol_baseline_30d_pct <= 0.0:
        return TrendRegimeClassification(None, "invalid_vol_baseline")
    if slippage_bps is None or slippage_bps > TREND_REGIME_MAX_SLIPPAGE_BPS:
        return TrendRegimeClassification(None, "slippage_above_max")

    tier = symbol_tier(symbol)

    # Determine thresholds to use
    if thresholds is not None:
        vol_multiplier = thresholds.vol_multiplier
        if tier == "major":
            min_return_pct = thresholds.major_min_return_pct
            min_oi_pct = thresholds.major_min_oi_pct
        else:
            min_return_pct = thresholds.large_alt_min_return_pct
            min_oi_pct = thresholds.large_alt_min_oi_pct
    else:
        vol_multiplier = TREND_REGIME_VOL_BREAKOUT_MULTIPLIER
        min_return_pct, min_oi_pct, _ = _tier_thresholds(symbol)

    vol_ratio = vol_1h_pct / vol_baseline_30d_pct
    if vol_ratio < vol_multiplier:
        return TrendRegimeClassification(None, "vol_breakout_below_threshold")
    if abs(return_1h_pct) < min_return_pct:
        return TrendRegimeClassification(None, "return_below_min")
    if abs(oi_change_1h_pct) < min_oi_pct:
        return TrendRegimeClassification(None, "oi_confirmation_below_min")

    direction = "long" if return_1h_pct > 0.0 else "short"
    if oi_change_1h_pct > 0.0:
        regime = f"vol_breakout_{direction}"
    else:
        return TrendRegimeClassification(None, "oi_not_positive_for_vol_breakout")

    event = TrendRegimeWatchEvent(
        strategy_type="trend_regime",
        symbol=symbol,
        exchange=str(row.get("exchange") or "unknown"),
        regime=regime,
        direction=direction,
        vol_ratio=vol_ratio,
        return_1h_pct=return_1h_pct,
        oi_change_1h_pct=oi_change_1h_pct,
        liquidation_notional_1h_usdt=0.0,  # Research-only vol breakout never uses liquidation
        reason=regime,
        reject_reason=None,
        executable=False,
        metadata={
            "mode": "observation",
            "symbol_tier": tier,
            "funding_state": str(row.get("funding_state") or "unknown"),
            "estimated_cost_bps": TREND_REGIME_OBSERVATION_COST_BPS,
            "estimated_slippage_bps": slippage_bps,
        },
    )
    return TrendRegimeClassification(event, None)
