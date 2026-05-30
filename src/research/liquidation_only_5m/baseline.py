from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import configs.base as cfg


@dataclass(frozen=True)
class LiquidationOnly5mEvent:
    symbol: str
    bar_start_ms: int
    liquidated_position_side: str  # "long" or "short"
    dominant_liquidation_side: str  # "long" or "short"
    continuation_trade_side: str  # "long" or "short"
    mean_reversion_trade_side: str  # "long" or "short"
    dominance_ratio: float


def classify_liquidation_only_5m_event(row: dict[str, Any]) -> LiquidationOnly5mEvent | None:
    symbol = row.get("symbol", "")
    if not symbol:
        return None

    # Get thresholds from configs/base.py
    is_major = symbol in ("BTC/USDT", "ETH/USDT")
    abs_threshold = (
        cfg.LIQUIDATION_ONLY_5M_MAJOR_ABS_THRESHOLD_USDT
        if is_major
        else cfg.LIQUIDATION_ONLY_5M_ALT_ABS_THRESHOLD_USDT
    )

    long_liq = float(row.get("long_liquidation_notional_5m_usdt") or 0.0)
    short_liq = float(row.get("short_liquidation_notional_5m_usdt") or 0.0)
    total_liq = long_liq + short_liq

    # Check absolute threshold
    if total_liq < abs_threshold:
        return None

    # Check relative score threshold
    rel_score = row.get("liquidation_relative_score")
    if rel_score is None or rel_score < cfg.LIQUIDATION_ONLY_5M_RELATIVE_SCORE_THRESHOLD:
        return None

    # Check reference count
    ref_count = row.get("liquidation_reference_count")
    required_ref_count = 2016  # 7 days of 5m bars
    if ref_count is None or ref_count < required_ref_count:
        return None

    # Check dominance ratio
    dominance_ratio = row.get("dominance_ratio")
    if dominance_ratio is None:
        dominance_ratio = max(long_liq, short_liq) / total_liq if total_liq > 0 else 0.0

    if dominance_ratio < cfg.LIQUIDATION_ONLY_5M_DOMINANCE_RATIO_MIN:
        return None

    # Classify event sides
    if long_liq > short_liq:
        dominant_side = "long"
        liquidated_side = "long"
        continuation_side = "short"
        reversion_side = "long"
    else:
        dominant_side = "short"
        liquidated_side = "short"
        continuation_side = "long"
        reversion_side = "short"

    return LiquidationOnly5mEvent(
        symbol=symbol,
        bar_start_ms=int(row["bar_start_ms"]),
        liquidated_position_side=liquidated_side,
        dominant_liquidation_side=dominant_side,
        continuation_trade_side=continuation_side,
        mean_reversion_trade_side=reversion_side,
        dominance_ratio=dominance_ratio,
    )
