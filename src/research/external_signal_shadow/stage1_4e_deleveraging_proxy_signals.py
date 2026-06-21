import bisect
from collections import defaultdict

from configs import base
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    CANDIDATE_1H,
    CANDIDATE_15M,
    EVENT_DOWN_FLUSH,
    EVENT_UP_SQUEEZE,
    ProxyEvent,
)


def find_closest_row(sorted_rows: list[dict], time_key: str, target_ms: int, max_staleness: int) -> dict | None:
    if not sorted_rows:
        return None
    times = [r[time_key] for r in sorted_rows]
    idx = bisect.bisect_right(times, target_ms) - 1
    if idx < 0:
        return None
    closest = sorted_rows[idx]
    if target_ms - closest[time_key] <= max_staleness:
        return closest
    return None

def detect_deleveraging_proxy_events(
    *,
    oi_rows: list[dict],
    price_rows: list[dict],
    candidate_name: str,
    source_quality: dict,
    expected_symbols: tuple[str, ...],
) -> tuple[list[ProxyEvent], dict]:
    supported_by_symbol = source_quality.get(
        "candidate_window_supported_by_symbol", {}
    ).get(candidate_name, {})

    # If candidate is overall not supported, return empty
    supported_overall = source_quality.get("candidate_window_supported_overall", {}).get(candidate_name, True)
    if not supported_overall:
        return [], {"candidate_status": "data_unsupported"}

    # Define thresholds
    if candidate_name == CANDIDATE_15M:
        bucket_size = 15 * 60 * 1000
        price_threshold = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_PRICE_RETURN_THRESHOLD
        oi_drop_threshold = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_OI_DROP_THRESHOLD
        cooldown_ms = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_COOLDOWN_MS
        max_staleness = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MAX_OI_STALENESS_MS
    elif candidate_name == CANDIDATE_1H:
        bucket_size = 60 * 60 * 1000
        price_threshold = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_PRICE_RETURN_THRESHOLD
        oi_drop_threshold = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_OI_DROP_THRESHOLD
        cooldown_ms = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_COOLDOWN_MS
        max_staleness = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MAX_OI_STALENESS_MS
    else:
        raise ValueError(f"Invalid candidate_name: {candidate_name}")

    lag_ms = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_CONFIGURED_DATA_LAG_MS

    # Group and sort input rows
    oi_by_symbol = defaultdict(list)
    for r in oi_rows:
        if r["symbol"] in expected_symbols:
            oi_by_symbol[r["symbol"]].append(r)

    price_by_symbol = defaultdict(list)
    for r in price_rows:
        if r["symbol"] in expected_symbols:
            price_by_symbol[r["symbol"]].append(r)

    events = []
    cooldowns = {} # key: (symbol, label, direction) -> last_trigger_ms

    for symbol in expected_symbols:
        # Check symbol support
        if not supported_by_symbol.get(symbol, False):
            continue

        oi_sorted = sorted(oi_by_symbol[symbol], key=lambda x: x["timestamp_ms"])
        price_sorted = sorted(price_by_symbol[symbol], key=lambda x: x["bar_start_ms"])

        if not oi_sorted or not price_sorted:
            continue

        # Determine price bar interval for completeness check
        gaps = [price_sorted[i]["bar_start_ms"] - price_sorted[i-1]["bar_start_ms"] for i in range(1, len(price_sorted))]
        if gaps:
            gaps.sort()
            price_bar_interval_ms = gaps[len(gaps) // 2]
        else:
            price_bar_interval_ms = bucket_size # fallback

        expected_bars = bucket_size // price_bar_interval_ms

        min_time = min(oi_sorted[0]["timestamp_ms"], price_sorted[0]["bar_start_ms"])
        max_time = max(oi_sorted[-1]["timestamp_ms"], price_sorted[-1]["bar_start_ms"])

        # Align min/max time to bucket boundary
        start_bucket_ms = (min_time // bucket_size) * bucket_size
        end_bucket_ms = (max_time // bucket_size) * bucket_size

        # Find price index positions to speed up lookup
        price_times = [p["bar_start_ms"] for p in price_sorted]

        curr_time = start_bucket_ms
        while curr_time <= end_bucket_ms:
            b_start = curr_time
            b_end = curr_time + bucket_size

            # 1. Price check
            # Find price bars starting within [b_start, b_end)
            p_start_idx = bisect.bisect_left(price_times, b_start)
            p_end_idx = bisect.bisect_left(price_times, b_end)
            bucket_bars = price_sorted[p_start_idx:p_end_idx]

            # Price completeness check
            if expected_bars > 1:
                # If we expect multiple bars (e.g. 4 15m bars for 1h, or 15 1m bars for 15m), require exact count
                if len(bucket_bars) < expected_bars:
                    curr_time += bucket_size
                    continue
            else:
                if len(bucket_bars) < 1:
                    curr_time += bucket_size
                    continue

            # Price return
            first_bar = bucket_bars[0]
            last_bar = bucket_bars[-1]
            price_return = last_bar["close"] / first_bar["open"] - 1.0

            # 2. OI check
            oi_start_row = find_closest_row(oi_sorted, "timestamp_ms", b_start, max_staleness)
            oi_end_row = find_closest_row(oi_sorted, "timestamp_ms", b_end, max_staleness)

            if oi_start_row is None or oi_end_row is None:
                curr_time += bucket_size
                continue

            oi_start = oi_start_row["sumOpenInterest"]
            oi_end = oi_end_row["sumOpenInterest"]

            if oi_start <= 0:
                curr_time += bucket_size
                continue

            oi_change = (oi_end - oi_start) / oi_start

            # 3. Trigger conditions
            is_down_flush = (price_return <= -price_threshold) and (oi_change <= oi_drop_threshold)
            is_up_squeeze = (price_return >= price_threshold) and (oi_change <= oi_drop_threshold)

            if is_down_flush or is_up_squeeze:
                label = EVENT_DOWN_FLUSH if is_down_flush else EVENT_UP_SQUEEZE
                direction = 1 if is_down_flush else -1

                event_time_ms = b_end
                available_at_ms = b_end + lag_ms

                # Cooldown check
                cd_key = (symbol, label, direction)
                last_trig = cooldowns.get(cd_key, 0)
                if event_time_ms - last_trig >= cooldown_ms:
                    cooldowns[cd_key] = event_time_ms

                    event = ProxyEvent(
                        symbol=symbol,
                        candidate_name=candidate_name,
                        event_label=label,
                        signed_direction=direction,
                        bucket_start_ms=b_start,
                        bucket_end_ms=b_end,
                        event_time_ms=event_time_ms,
                        event_available_at_ms=available_at_ms,
                        entry_bar_start_ms=None,  # Set by replay module
                        price_return=price_return,
                        oi_change=oi_change,
                        oi_start=oi_start,
                        oi_end=oi_end,
                        source="oi_and_price_joint",
                        source_quality=oi_start_row.get("source_quality", "15m_aligned_tick")
                    )
                    events.append(event)

            curr_time += bucket_size

    # Sort events by time
    events.sort(key=lambda x: x.event_time_ms)
    return events, {"candidate_status": "data_supported" if events else "no_events_found"}
