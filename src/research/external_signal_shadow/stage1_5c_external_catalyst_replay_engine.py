from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_models import (
    ExternalCatalystReplayResult,
)
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_quality import (
    find_first_bar_at_or_after,
)


def compute_signed_net_return_bps(
    entry_price: float,
    exit_price: float,
    signed_direction: int,
    cost_bps: int
) -> float:
    if entry_price <= 0:
        return 0.0
    long_gross = (exit_price / entry_price - 1.0) * 10000.0
    signed_gross = long_gross * signed_direction
    return round(signed_gross - cost_bps, 6)


def replay_candidates(
    candidates,
    price_index,
    forward_windows_hours,
    cost_scenarios_bps
) -> list[ExternalCatalystReplayResult]:
    res = []
    for c in candidates:
        if not c.replay_allowed:
            continue
        symbol_bars = price_index.get(c.symbol, [])
        for window in forward_windows_hours:
            exit_target_ms = c.entry_bar_start_ms + window * 3600_000
            exit_bar = find_first_bar_at_or_after(symbol_bars, exit_target_ms)
            if not exit_bar:
                continue

            long_gross = round((exit_bar["open"] / c.entry_price - 1.0) * 10000.0, 6)
            signed_gross = round(long_gross * c.signed_direction, 6)

            for cost in cost_scenarios_bps:
                net_ret = round(signed_gross - cost, 6)
                res.append(ExternalCatalystReplayResult(
                    symbol_event_id=c.symbol_event_id,
                    event_type=c.event_type,
                    signed_mode=c.signed_mode,
                    signed_direction=c.signed_direction,
                    symbol=c.symbol,
                    entry_delay_hours=c.entry_delay_hours,
                    forward_window_hours=window,
                    cost_bps=cost,
                    entry_price=c.entry_price,
                    exit_price=exit_bar["open"],
                    long_gross_return_bps=long_gross,
                    signed_gross_return_bps=signed_gross,
                    net_return_bps=net_ret,
                    forward_window_complete=True,
                ))
    return res
