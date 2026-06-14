from __future__ import annotations

from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_replay import (
    build_one_hour_window,
    historical_available_at_ms,
    select_entry_bar,
)

MS_15M = 15 * 60 * 1000


def _bar(i: int, close: float = 100.0, volume: float = 1000.0) -> HistoricalBar:
    return HistoricalBar("BTCUSDT", i * MS_15M, (i + 1) * MS_15M, close, close, close, close, volume)


def test_historical_available_at_uses_bar_close_plus_lag() -> None:
    assert historical_available_at_ms(_bar(3), configured_lag_ms=60_000) == 4 * MS_15M + 60_000


def test_one_hour_window_uses_last_four_completed_15m_bars() -> None:
    bars = [_bar(i, close=100 + i, volume=10 + i) for i in range(6)]
    window = build_one_hour_window(bars, end_index=5, one_hour_bar_count=4)
    assert [bar.bar_start_ms for bar in window] == [2 * MS_15M, 3 * MS_15M, 4 * MS_15M, 5 * MS_15M]
    assert sum(bar.quote_volume for bar in window) == 10 + 2 + 10 + 3 + 10 + 4 + 10 + 5


def test_entry_delay_one_uses_first_complete_bar_after_event() -> None:
    bars = [_bar(i) for i in range(8)]
    event_time = 4 * MS_15M + 60_000
    entry = select_entry_bar(bars, event_time_ms=event_time, entry_delay_bars=1)
    # entry_delay_bars=1 is 1-based: first complete bar after event_time, not skip-one-more-bar.
    assert entry == bars[5]
