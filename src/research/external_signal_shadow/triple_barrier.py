from src.research.external_signal_shadow.models import (
    ExternalSignalEvent,
    PriceBar,
    ShadowOrder,
)

_MS_PER_MINUTE = 60_000


def _candidate_bars(bars: list[PriceBar], trigger_time_ms: int) -> list[PriceBar]:
    return sorted(
        [bar for bar in bars if bar.bar_start_ms > trigger_time_ms],
        key=lambda item: item.bar_start_ms,
    )


def _data_unavailable_order(
    event: ExternalSignalEvent,
    direction: str,
    cost_round_trip_bps: float,
) -> ShadowOrder:
    return ShadowOrder(
        shadow_order_id=f"{event.event_id}:data_unavailable",
        event_id=event.event_id,
        symbol=event.symbol,
        token_address=event.token_address,
        direction=direction,
        entry_time_ms=None,
        entry_price=None,
        take_profit_price=None,
        stop_loss_price=None,
        vertical_barrier_time_ms=None,
        cost_round_trip_bps=cost_round_trip_bps,
        status="data_unavailable",
        exit_reason="data_unavailable",
    )


def _barrier_prices(
    entry_price: float, direction: str, take_profit_bps: float, stop_loss_bps: float
) -> tuple[float, float]:
    if direction == "long":
        return (
            entry_price * (1 + take_profit_bps / 10_000),
            entry_price * (1 - stop_loss_bps / 10_000),
        )
    return (
        entry_price * (1 - take_profit_bps / 10_000),
        entry_price * (1 + stop_loss_bps / 10_000),
    )


def _gross_return_bps(entry_price: float, exit_price: float, direction: str) -> float:
    if direction == "long":
        return (exit_price / entry_price - 1) * 10_000
    return (entry_price - exit_price) / entry_price * 10_000


def _mae_mfe_bps(
    entry_price: float, direction: str, bars: list[PriceBar]
) -> tuple[float, float]:
    max_high = max(bar.high_price for bar in bars)
    min_low = min(bar.low_price for bar in bars)
    if direction == "long":
        return (
            max(0.0, (entry_price - min_low) / entry_price * 10_000),
            max(0.0, (max_high - entry_price) / entry_price * 10_000),
        )
    return (
        max(0.0, (max_high - entry_price) / entry_price * 10_000),
        max(0.0, (entry_price - min_low) / entry_price * 10_000),
    )


def build_shadow_order_with_triple_barrier(
    event: ExternalSignalEvent,
    trigger_time_ms: int,
    bars: list[PriceBar],
    *,
    direction: str,
    take_profit_bps: float,
    stop_loss_bps: float,
    max_holding_minutes: int,
    entry_delay_bars: int,
    cost_round_trip_bps: float,
) -> ShadowOrder:
    symbol_bars = [bar for bar in bars if bar.symbol == event.symbol]
    candidate_bars = _candidate_bars(symbol_bars, trigger_time_ms)
    if entry_delay_bars < 1 or len(candidate_bars) < entry_delay_bars:
        return _data_unavailable_order(event, direction, cost_round_trip_bps)

    entry_bar = candidate_bars[entry_delay_bars - 1]
    entry_price = entry_bar.open_price
    vertical_barrier_time_ms = (
        entry_bar.bar_start_ms + max_holding_minutes * _MS_PER_MINUTE
    )
    take_profit_price, stop_loss_price = _barrier_prices(
        entry_price, direction, take_profit_bps, stop_loss_bps
    )
    evaluation_bars = [
        bar
        for bar in candidate_bars[entry_delay_bars - 1 :]
        if bar.bar_start_ms < vertical_barrier_time_ms
    ]
    if not evaluation_bars:
        return _data_unavailable_order(event, direction, cost_round_trip_bps)

    exit_reason = "vertical_barrier"
    exit_price = evaluation_bars[-1].close_price
    exit_time_ms = vertical_barrier_time_ms
    used_bars = evaluation_bars

    for index, bar in enumerate(evaluation_bars):
        if direction == "long":
            stop_hit = bar.low_price <= stop_loss_price
            take_hit = bar.high_price >= take_profit_price
        else:
            stop_hit = bar.high_price >= stop_loss_price
            take_hit = bar.low_price <= take_profit_price

        if stop_hit:
            exit_reason = "stop_loss"
            exit_price = stop_loss_price
            exit_time_ms = bar.bar_start_ms
            used_bars = evaluation_bars[: index + 1]
            break
        if take_hit:
            exit_reason = "take_profit"
            exit_price = take_profit_price
            exit_time_ms = bar.bar_start_ms
            used_bars = evaluation_bars[: index + 1]
            break

    gross_return_bps = _gross_return_bps(entry_price, exit_price, direction)
    mae_bps, mfe_bps = _mae_mfe_bps(entry_price, direction, used_bars)

    return ShadowOrder(
        shadow_order_id=f"{event.event_id}:{direction}:{entry_bar.bar_start_ms}",
        event_id=event.event_id,
        symbol=event.symbol,
        token_address=event.token_address,
        direction=direction,
        entry_time_ms=entry_bar.bar_start_ms,
        entry_price=entry_price,
        take_profit_price=take_profit_price,
        stop_loss_price=stop_loss_price,
        vertical_barrier_time_ms=vertical_barrier_time_ms,
        cost_round_trip_bps=cost_round_trip_bps,
        status="closed",
        exit_time_ms=exit_time_ms,
        exit_price=exit_price,
        exit_reason=exit_reason,
        gross_return_bps=round(gross_return_bps, 10),
        net_return_bps=round(gross_return_bps - cost_round_trip_bps, 10),
        max_adverse_excursion_bps=round(mae_bps, 10),
        max_favorable_excursion_bps=round(mfe_bps, 10),
    )
