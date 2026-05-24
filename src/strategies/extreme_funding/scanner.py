from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from configs.base import (
    EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC,
    EXTREME_FUNDING_MAX_OI_DATA_AGE_SEC,
    EXTREME_FUNDING_MICRO_PERSISTENCE_WINDOW_MIN,
    EXTREME_FUNDING_MICRO_PERSISTENCE_MIN,
    EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_WEAK,
    EXTREME_FUNDING_OI_CONFIRMATION_MIN_CHANGE_1H_PCT,
    EXTREME_FUNDING_OI_STRONG_CONFIRMATION_MIN_CHANGE_1H_PCT,
    EXTREME_FUNDING_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
    EXTREME_FUNDING_STRONG_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
    EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
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

    def classify(self, snapshot: dict[str, Any]) -> ExtremeFundingClassification:
        prelim = classify_extreme_funding_snapshot(snapshot)
        if prelim.reject_reason != "premium_below_threshold":
            return prelim

        symbol = str(snapshot["symbol"])
        timestamp_ms = int(snapshot["timestamp_ms"])
        annualized_pct = snapshot.get("premium_annualized_estimate_pct")
        if annualized_pct is None:
            annualized_pct = premium_to_naive_annualized_pct(float(snapshot["premium_index"]))
        annualized_pct = float(annualized_pct)

        self.append_observation(symbol, timestamp_ms=timestamp_ms, annualized_pct=annualized_pct)
        window_values = self.get_window_values(symbol, now_ms=timestamp_ms)
        micro_persistence = compute_micro_persistence(
            window_values,
            threshold_pct=EXTREME_FUNDING_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
        )
        if len(window_values) < 2 or micro_persistence < EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_WEAK:
            return ExtremeFundingClassification(None, "micro_persistence_below_threshold")

        oi_status = "ok"
        oi_change_1h_pct = snapshot.get("oi_change_1h_pct")
        oi_data_age_sec = float(snapshot.get("oi_data_age_sec", 0.0))
        if oi_change_1h_pct is None:
            oi_status = "missing"
        elif oi_data_age_sec > EXTREME_FUNDING_MAX_OI_DATA_AGE_SEC:
            oi_status = "stale"
        else:
            oi_change_1h_pct = float(oi_change_1h_pct)

        level = "watch_level_1"
        if (
            annualized_pct >= EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT
            and micro_persistence >= EXTREME_FUNDING_MICRO_PERSISTENCE_MIN
            and oi_status == "ok"
            and oi_change_1h_pct is not None
            and oi_change_1h_pct >= EXTREME_FUNDING_OI_STRONG_CONFIRMATION_MIN_CHANGE_1H_PCT
        ):
            level = "watch_level_3"
        elif (
            annualized_pct >= EXTREME_FUNDING_STRONG_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT
            and micro_persistence >= EXTREME_FUNDING_MICRO_PERSISTENCE_MIN
            and oi_status == "ok"
            and oi_change_1h_pct is not None
            and oi_change_1h_pct >= EXTREME_FUNDING_OI_CONFIRMATION_MIN_CHANGE_1H_PCT
        ):
            level = "watch_level_2"

        event = ExtremeFundingWatchEvent(
            strategy_type="extreme_funding",
            symbol=symbol,
            exchange=str(snapshot.get("exchange", "unknown")),
            level=level,
            premium_annualized_estimate_pct=annualized_pct,
            micro_persistence=micro_persistence,
            oi_change_1h_pct=None if oi_change_1h_pct is None else float(oi_change_1h_pct),
            reason="premium_persistent",
            reject_reason=None,
            executable=False,
            metadata={
                "mode": "observation",
                "estimate_type": "naive_premium_annualization",
                "not_settled_funding": True,
                "oi_status": oi_status,
            },
        )
        return ExtremeFundingClassification(event, None)

    async def scan(self, market_data: dict[str, Any]) -> list[ExtremeFundingWatchEvent]:
        result = self.classify(market_data)
        return [result.event] if result.event is not None else []


def premium_to_naive_annualized_pct(
    premium_index: float,
    funding_intervals_per_day: int = 3,
) -> float:
    return premium_index * funding_intervals_per_day * 365 * 100
