import bisect
from collections import defaultdict

from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import ProxyEvent


def _build_price_index(price_bars: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for bar in price_bars:
        grouped[bar["symbol"]].append(bar)

    index = {}
    for symbol, bars in grouped.items():
        index[symbol] = sorted(bars, key=lambda x: x["bar_start_ms"])
    return index

def find_entry_bar(sorted_bars: list[dict], available_at_ms: int) -> dict | None:
    times = [b["bar_start_ms"] for b in sorted_bars]
    idx = bisect.bisect_left(times, available_at_ms)
    if idx < len(sorted_bars):
        return sorted_bars[idx]
    return None

def find_exit_bar(sorted_bars: list[dict], target_ms: int, max_gap_ms: int = 3600000) -> dict | None:
    times = [b["bar_start_ms"] for b in sorted_bars]
    idx = bisect.bisect_left(times, target_ms)

    candidates = []
    if idx < len(sorted_bars):
        candidates.append(sorted_bars[idx])
    if idx > 0:
        candidates.append(sorted_bars[idx - 1])

    if not candidates:
        return None

    closest = min(candidates, key=lambda x: abs(x["bar_start_ms"] - target_ms))
    if abs(closest["bar_start_ms"] - target_ms) <= max_gap_ms:
        return closest
    return None

def replay_deleveraging_proxy_events(events: list[ProxyEvent], price_bars: list[dict]) -> list[dict]:
    price_index = _build_price_index(price_bars)
    replayed_rows = []

    for event in events:
        sorted_bars = price_index.get(event.symbol)
        if not sorted_bars:
            continue

        entry_bar = find_entry_bar(sorted_bars, event.event_available_at_ms)
        if not entry_bar:
            # Skip if entry bar is not found
            continue

        entry_open = entry_bar["open"]
        if entry_open <= 0:
            continue

        entry_time_ms = entry_bar["bar_start_ms"]

        # Update event's entry_bar_start_ms in-place if possible (since frozen=True we don't mutate, but we output it in rows)
        for h in (1, 4, 12):
            target_exit_ms = entry_time_ms + h * 3600000
            exit_bar = find_exit_bar(sorted_bars, target_exit_ms)
            if not exit_bar:
                continue

            exit_close = exit_bar["close"]
            gross_return = (exit_close / entry_open - 1.0) * event.signed_direction
            gross_return_bps = gross_return * 10000.0

            replayed_rows.append({
                "symbol": event.symbol,
                "candidate_name": event.candidate_name,
                "event_label": event.event_label,
                "event_time_ms": event.event_time_ms,
                "entry_bar_start_ms": entry_time_ms,
                "entry_price": entry_open,
                "exit_price": exit_close,
                "signed_direction": event.signed_direction,
                "forward_window_hours": h,
                "gross_return_bps": gross_return_bps,
                "net_return_bps_after_30bps": gross_return_bps - 30.0,
                "net_return_bps_after_50bps": gross_return_bps - 50.0,
                "net_return_bps_after_80bps": gross_return_bps - 80.0,
            })

    return replayed_rows
