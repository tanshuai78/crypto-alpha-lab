import math
import statistics

from src.research.external_signal_shadow.models import (
    CusumResult,
    ExternalSignalEvent,
    PriceBar,
)

_MS_PER_MINUTE = 60_000


def _fixed_threshold_log_return(fixed_threshold_bps: float) -> float:
    return fixed_threshold_bps / 10_000.0


def _log_returns_from_closes(closes: list[float]) -> list[float]:
    return [
        math.log(closes[index] / closes[index - 1])
        for index in range(1, len(closes))
    ]


def _completed_pre_event_bars(
    bars: list[PriceBar], event_time_ms: int
) -> list[PriceBar]:
    return [bar for bar in bars if bar.bar_end_ms <= event_time_ms]


def _post_event_bars(
    bars: list[PriceBar], event_time_ms: int, confirmation_window_min: int
) -> list[PriceBar]:
    window_end_ms = event_time_ms + confirmation_window_min * _MS_PER_MINUTE
    return [
        bar
        for bar in bars
        if bar.bar_start_ms > event_time_ms and bar.bar_start_ms <= window_end_ms
    ]


def _threshold(
    pre_event_bars: list[PriceBar],
    fixed_threshold_bps: float,
    vol_multiplier: float,
) -> tuple[float, float, str]:
    fixed_threshold = _fixed_threshold_log_return(fixed_threshold_bps)
    closes = [bar.close_price for bar in pre_event_bars[-61:]]
    returns = _log_returns_from_closes(closes)
    if len(returns) < 2:
        return fixed_threshold, 0.0, "fixed"
    rolling_vol = statistics.pstdev(returns)
    vol_threshold = vol_multiplier * rolling_vol
    if vol_threshold > fixed_threshold:
        return vol_threshold, rolling_vol, "vol"
    return fixed_threshold, rolling_vol, "fixed"


def _map_status(direction_hint: str, move_direction: str) -> tuple[str, str]:
    if direction_hint == "unknown" or direction_hint == "avoid":
        return "observe_only", move_direction
    if direction_hint == "both":
        return "confirmed", move_direction
    if direction_hint == move_direction:
        return "confirmed", move_direction
    return "adverse_confirm", move_direction


def confirm_event_with_cusum(
    event: ExternalSignalEvent,
    bars: list[PriceBar],
    *,
    fixed_threshold_bps: float,
    vol_multiplier: float,
    confirmation_window_min: int,
) -> CusumResult:
    if event.direction_hint in {"unknown", "avoid"}:
        return CusumResult(event_id=event.event_id, status="observe_only")

    symbol_bars = sorted(
        [bar for bar in bars if bar.symbol == event.symbol],
        key=lambda item: item.bar_start_ms,
    )
    pre_event_bars = _completed_pre_event_bars(symbol_bars, event.event_time_ms)
    if not pre_event_bars:
        return CusumResult(event_id=event.event_id, status="data_unavailable")

    threshold, rolling_vol, threshold_source = _threshold(
        pre_event_bars, fixed_threshold_bps, vol_multiplier
    )
    prev_close = pre_event_bars[-1].close_price
    s_pos = 0.0
    s_neg = 0.0

    post_bars = _post_event_bars(
        symbol_bars, event.event_time_ms, confirmation_window_min
    )
    if not post_bars:
        return CusumResult(
            event_id=event.event_id,
            status="data_unavailable",
            threshold_bps=threshold * 10_000,
            rolling_vol_bps=rolling_vol * 10_000,
            threshold_source=threshold_source,
        )

    for bar in post_bars:
        ret = math.log(bar.close_price / prev_close)
        prev_close = bar.close_price
        s_pos = max(0.0, s_pos + ret)
        s_neg = min(0.0, s_neg + ret)
        if s_pos > threshold:
            status, direction = _map_status(event.direction_hint, "long")
            return CusumResult(
                event_id=event.event_id,
                status=status,
                trigger_time_ms=bar.bar_start_ms,
                direction=direction,
                threshold_bps=threshold * 10_000,
                rolling_vol_bps=rolling_vol * 10_000,
                threshold_source=threshold_source,
            )
        if s_neg < -threshold:
            status, direction = _map_status(event.direction_hint, "short")
            return CusumResult(
                event_id=event.event_id,
                status=status,
                trigger_time_ms=bar.bar_start_ms,
                direction=direction,
                threshold_bps=threshold * 10_000,
                rolling_vol_bps=rolling_vol * 10_000,
                threshold_source=threshold_source,
            )

    return CusumResult(
        event_id=event.event_id,
        status="no_confirm",
        threshold_bps=threshold * 10_000,
        rolling_vol_bps=rolling_vol * 10_000,
        threshold_source=threshold_source,
    )
