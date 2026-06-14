from __future__ import annotations

from research.external_signal_shadow.stage1_3_metrics import (
    compute_forward_metrics,
    compute_forward_metrics_from_entry_index,
)
from research.external_signal_shadow.stage1_3_models import HistoricalBar

MS_15M = 15 * 60 * 1000


def _bar(i: int, open_price: float, close_price: float, high: float | None = None, low: float | None = None) -> HistoricalBar:
    high_price = max(open_price, close_price) if high is None else high
    low_price = min(open_price, close_price) if low is None else low
    return HistoricalBar("ETHUSDT", i * MS_15M, (i + 1) * MS_15M, open_price, high_price, low_price, close_price, 1_000_000)


def test_forward_metrics_use_entry_delay_and_4h_terminal_return() -> None:
    bars = [_bar(i, 100.0 + i, 100.0 + i) for i in range(24)]
    event_time_ms = 4 * MS_15M + 60_000
    metrics = compute_forward_metrics(
        bars,
        event_time_ms=event_time_ms,
        entry_delay_bars=1,
        cost_round_trip_bps=50.0,
        signed_direction=1,
    )
    assert metrics["entry_bar_start_ms"] == 5 * MS_15M
    assert "terminal_return_4h_net_bps" in metrics
    assert metrics["cost_round_trip_bps"] == 50.0


def test_forward_15m_uses_entry_bar_close_not_next_bar_close() -> None:
    bars = [_bar(i, 100.0, 100.0) for i in range(24)]
    bars[5] = _bar(5, 100.0, 101.0)
    bars[6] = _bar(6, 100.0, 150.0)
    metrics = compute_forward_metrics(
        bars,
        event_time_ms=4 * MS_15M + 60_000,
        entry_delay_bars=1,
        cost_round_trip_bps=0.0,
        signed_direction=1,
    )
    assert round(metrics["forward_return_15m_net_bps"], 6) == 100.0


def test_mfe_mae_use_high_low_not_close_only() -> None:
    bars = [_bar(i, 100.0, 100.0) for i in range(24)]
    bars[5] = _bar(5, 100.0, 100.0, high=110.0, low=90.0)
    metrics = compute_forward_metrics(
        bars,
        event_time_ms=4 * MS_15M + 60_000,
        entry_delay_bars=1,
        cost_round_trip_bps=0.0,
        signed_direction=1,
    )
    assert metrics["mfe_4h_bps"] >= 999.9
    assert metrics["mae_4h_bps"] <= -999.9


def test_forward_metrics_returns_incomplete_when_forward_window_missing() -> None:
    bars = [_bar(i, 100, 100) for i in range(6)]
    metrics = compute_forward_metrics(
        bars,
        event_time_ms=4 * MS_15M + 60_000,
        entry_delay_bars=1,
        cost_round_trip_bps=50.0,
        signed_direction=1,
    )
    assert metrics["status"] == "forward_window_incomplete"


def test_forward_metrics_from_entry_index_matches_event_time_entry() -> None:
    bars = [_bar(i, 100.0 + i, 100.0 + i) for i in range(24)]
    from_event_time = compute_forward_metrics(
        bars,
        event_time_ms=4 * MS_15M + 60_000,
        entry_delay_bars=1,
        cost_round_trip_bps=50.0,
        signed_direction=1,
    )

    from_index = compute_forward_metrics_from_entry_index(
        bars,
        entry_index=5,
        cost_round_trip_bps=50.0,
        signed_direction=1,
    )

    assert from_index == from_event_time
