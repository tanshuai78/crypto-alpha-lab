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
        unique_starts = {item.bar_start_ms for item in items}
        coverage[symbol] = len(unique_starts) / expected
    return coverage


def find_duplicate_bar_starts(bars: list[HistoricalBar]) -> dict[str, list[int]]:
    duplicates: dict[str, list[int]] = {}
    for symbol, items in group_bars_by_symbol(bars).items():
        seen: set[int] = set()
        duplicate_starts: set[int] = set()
        for item in items:
            if item.bar_start_ms in seen:
                duplicate_starts.add(item.bar_start_ms)
            seen.add(item.bar_start_ms)
        if duplicate_starts:
            duplicates[symbol] = sorted(duplicate_starts)
    return duplicates
