from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from configs.base import (
    EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC,
    EXTREME_FUNDING_MICRO_PERSISTENCE_WINDOW_MIN,
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


def compute_micro_persistence(values: list[float], *, threshold_pct: float) -> float:
    if not values:
        return 0.0
    above = sum(1 for value in values if value >= threshold_pct)
    return above / len(values)


class ExtremeFundingWatchlistScanner:
    def __init__(self) -> None:
        self._history: dict[str, deque[tuple[int, float]]] = defaultdict(deque)

    def append_observation(self, symbol: str, *, timestamp_ms: int, annualized_pct: float) -> None:
        self._history[symbol].append((timestamp_ms, annualized_pct))
        self._prune_history(symbol, now_ms=timestamp_ms)

    def get_window_values(self, symbol: str, *, now_ms: int) -> list[float]:
        self._prune_history(symbol, now_ms=now_ms)
        return [value for _, value in self._history[symbol]]

    def _prune_history(self, symbol: str, *, now_ms: int) -> None:
        cutoff_ms = now_ms - EXTREME_FUNDING_MICRO_PERSISTENCE_WINDOW_MIN * 60_000
        while self._history[symbol] and self._history[symbol][0][0] < cutoff_ms:
            self._history[symbol].popleft()
