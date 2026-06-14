from __future__ import annotations

from typing import Any

from configs import base
from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_replay import select_entry_bar

MS_15M = 15 * 60 * 1000


def compute_forward_metrics(
    bars: list[HistoricalBar],
    *,
    event_time_ms: int,
    entry_delay_bars: int,
    cost_round_trip_bps: float,
    signed_direction: int,
) -> dict[str, Any]:
    # Ensure sorted bars
    sorted_bars = sorted(bars, key=lambda b: b.bar_start_ms)
    entry_bar = select_entry_bar(sorted_bars, event_time_ms=event_time_ms, entry_delay_bars=entry_delay_bars)
    if not entry_bar:
        return {"status": "forward_window_incomplete"}

    try:
        idx = sorted_bars.index(entry_bar)
    except ValueError:
        return {"status": "forward_window_incomplete"}

    return compute_forward_metrics_from_entry_index(
        sorted_bars,
        entry_index=idx,
        cost_round_trip_bps=cost_round_trip_bps,
        signed_direction=signed_direction,
    )


def compute_forward_metrics_from_entry_index(
    sorted_bars: list[HistoricalBar],
    *,
    entry_index: int,
    cost_round_trip_bps: float,
    signed_direction: int,
) -> dict[str, Any]:
    if entry_index < 0 or entry_index >= len(sorted_bars):
        return {"status": "forward_window_incomplete"}

    entry_bar = sorted_bars[entry_index]

    window_len = base.EXTERNAL_SIGNAL_STAGE1_3_FORWARD_4H_BAR_COUNT
    if len(sorted_bars) - entry_index < window_len:
        return {"status": "forward_window_incomplete"}

    window = sorted_bars[entry_index : entry_index + window_len]

    # Verify contiguous timestamps
    for i, bar in enumerate(window):
        expected_start = entry_bar.bar_start_ms + i * MS_15M
        if bar.bar_start_ms != expected_start:
            return {"status": "forward_window_incomplete"}

    entry_open = entry_bar.open_price
    if entry_open <= 0:
        return {"status": "forward_window_incomplete"}

    # 15m return (entry bar close vs entry bar open)
    entry_close = entry_bar.close_price
    raw_return_15m = (entry_close / entry_open) - 1.0
    if signed_direction == -1:
        raw_return_15m = -raw_return_15m
    forward_return_15m_net_bps = raw_return_15m * 10000.0 - cost_round_trip_bps

    # 4h terminal return
    last_close = window[-1].close_price
    raw_return_4h = (last_close / entry_open) - 1.0
    if signed_direction == -1:
        raw_return_4h = -raw_return_4h
    terminal_return_4h_net_bps = raw_return_4h * 10000.0 - cost_round_trip_bps

    # MFE / MAE (gross of fees, direction-aware)
    if signed_direction == 1:
        mfe_val = max(bar.high_price for bar in window)
        mae_val = min(bar.low_price for bar in window)
        mfe_4h_bps = ((mfe_val / entry_open) - 1.0) * 10000.0
        mae_4h_bps = ((mae_val / entry_open) - 1.0) * 10000.0
    else:
        # short side: favorable is price going down, adverse is price going up
        mfe_val = min(bar.low_price for bar in window)
        mae_val = max(bar.high_price for bar in window)
        mfe_4h_bps = (1.0 - (mfe_val / entry_open)) * 10000.0
        mae_4h_bps = (1.0 - (mae_val / entry_open)) * 10000.0

    return {
        "status": "success",
        "entry_bar_start_ms": entry_bar.bar_start_ms,
        "entry_open_price": entry_open,
        "exit_close_price": last_close,
        "forward_return_15m_net_bps": forward_return_15m_net_bps,
        "terminal_return_4h_net_bps": terminal_return_4h_net_bps,
        "mfe_4h_bps": mfe_4h_bps,
        "mae_4h_bps": mae_4h_bps,
        "cost_round_trip_bps": cost_round_trip_bps,
        "signed_direction": signed_direction,
    }
