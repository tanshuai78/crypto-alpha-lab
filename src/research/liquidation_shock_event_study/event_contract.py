from __future__ import annotations

from dataclasses import dataclass

from configs.base import (
    LIQUIDATION_SHOCK_1M_ALT_ABS_THRESHOLD_USDT,
    LIQUIDATION_SHOCK_1M_DEDUP_BUCKET_MINUTES,
    LIQUIDATION_SHOCK_1M_DOMINANCE_RATIO_MIN,
    LIQUIDATION_SHOCK_1M_MAJOR_ABS_THRESHOLD_USDT,
    LIQUIDATION_SHOCK_1M_RELATIVE_SCORE_THRESHOLD,
    LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS,
)


@dataclass
class LiquidationShockEvent:
    symbol: str
    shock_bar_start_ms: int
    liquidated_position_side: str  # "long" or "short"
    dominant_liquidation_side: str  # "long" or "short"
    shock_notional_usdt: float
    relative_score: float
    relative_score_method: str
    reference_count: int
    required_reference_count: int
    dominance_ratio: float
    dedup_bucket_start_ms: int
    source_namespace: str = "liquidation_shock_event_study"

    @property
    def expected_price_direction(self) -> str:
        # Long liquidation is exchange selling -> downward price pressure
        # Short liquidation is exchange buying to cover -> upward price pressure
        if self.dominant_liquidation_side == "long":
            return "down"
        else:
            return "up"


def classify_liquidation_shock_event(
    symbol: str,
    bar_start_ms: int,
    long_liq: float,
    short_liq: float,
    relative_score: float,
    reference_count: int,
) -> LiquidationShockEvent | None:
    # 1. Reference check
    if reference_count < LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS:
        return None

    # 2. Relative score check
    if relative_score < LIQUIDATION_SHOCK_1M_RELATIVE_SCORE_THRESHOLD:
        return None

    # 3. Dominance calculation
    total_liq = long_liq + short_liq
    if total_liq <= 0.0:
        return None

    dominance_ratio = max(long_liq, short_liq) / total_liq
    if dominance_ratio < LIQUIDATION_SHOCK_1M_DOMINANCE_RATIO_MIN:
        return None

    dominant_side = "long" if long_liq >= short_liq else "short"
    shock_notional = long_liq if dominant_side == "long" else short_liq

    # 4. Absolute threshold check
    # Check if symbol is major or alt (Majors: BTC/USDT, ETH/USDT)
    is_major = symbol in ("BTC/USDT", "ETH/USDT", "BTCUSDT", "ETHUSDT")
    abs_threshold = (
        LIQUIDATION_SHOCK_1M_MAJOR_ABS_THRESHOLD_USDT
        if is_major
        else LIQUIDATION_SHOCK_1M_ALT_ABS_THRESHOLD_USDT
    )

    if shock_notional < abs_threshold:
        return None

    # 5. Calculate dedup bucket
    bucket_size_ms = LIQUIDATION_SHOCK_1M_DEDUP_BUCKET_MINUTES * 60 * 1000
    dedup_bucket_start_ms = (bar_start_ms // bucket_size_ms) * bucket_size_ms

    return LiquidationShockEvent(
        symbol=symbol,
        shock_bar_start_ms=bar_start_ms,
        liquidated_position_side=dominant_side,
        dominant_liquidation_side=dominant_side,
        shock_notional_usdt=shock_notional,
        relative_score=relative_score,
        relative_score_method="percentile_rank",
        reference_count=reference_count,
        required_reference_count=LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS,
        dominance_ratio=round(dominance_ratio, 4),
        dedup_bucket_start_ms=dedup_bucket_start_ms,
        source_namespace="liquidation_shock_event_study",
    )
