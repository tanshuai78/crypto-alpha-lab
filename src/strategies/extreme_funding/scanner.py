from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from configs.base import (
    EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC,
    EXTREME_FUNDING_WATCH_SYMBOLS,
)


@dataclass(frozen=True)
class ExtremeFundingWatchEvent:
    strategy_type: str
    symbol: str
    exchange: str
    level: str
    premium_annualized_estimate_pct: float
    micro_persistence: float
    oi_change_1h_pct: float | None
    reason: str
    reject_reason: str | None
    executable: bool
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ExtremeFundingClassification:
    event: ExtremeFundingWatchEvent | None
    reject_reason: str | None


def classify_extreme_funding_snapshot(snapshot: dict[str, Any]) -> ExtremeFundingClassification:
    symbol = snapshot.get("symbol")
    if not symbol:
        return ExtremeFundingClassification(None, "missing_symbol")
    if symbol not in EXTREME_FUNDING_WATCH_SYMBOLS:
        return ExtremeFundingClassification(None, "symbol_not_in_watchlist")
    if snapshot.get("timestamp_ms") is None:
        return ExtremeFundingClassification(None, "missing_timestamp")
    if snapshot.get("premium_index") is None:
        return ExtremeFundingClassification(None, "missing_premium")
    if float(snapshot.get("mark_data_age_sec", 0.0)) > EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC:
        return ExtremeFundingClassification(None, "api_stale")
    return ExtremeFundingClassification(None, "premium_below_threshold")
