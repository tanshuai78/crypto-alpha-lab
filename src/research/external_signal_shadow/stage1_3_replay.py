from __future__ import annotations

from research.external_signal_shadow.stage1_3_models import HistoricalBar


def historical_available_at_ms(bar: HistoricalBar, *, configured_lag_ms: int) -> int:
    return bar.bar_end_ms + configured_lag_ms


def build_one_hour_window(
    bars: list[HistoricalBar],
    *,
    end_index: int,
    one_hour_bar_count: int,
) -> list[HistoricalBar]:
    start = end_index - one_hour_bar_count + 1
    if start < 0:
        return []
    return bars[start : end_index + 1]


def one_hour_quote_volume(window: list[HistoricalBar]) -> float:
    return sum(bar.quote_volume for bar in window)


def one_hour_return(window: list[HistoricalBar]) -> float | None:
    if len(window) < 2:
        return None
    first = window[0].open_price
    last = window[-1].close_price
    if first <= 0:
        return None
    return last / first - 1.0


def select_entry_bar(
    bars: list[HistoricalBar],
    *,
    event_time_ms: int,
    entry_delay_bars: int,
) -> HistoricalBar | None:
    if entry_delay_bars < 1:
        raise ValueError("entry_delay_bars must be >= 1")
    candidates = [bar for bar in bars if bar.bar_start_ms > event_time_ms]
    if len(candidates) < entry_delay_bars:
        return None
    return candidates[entry_delay_bars - 1]
