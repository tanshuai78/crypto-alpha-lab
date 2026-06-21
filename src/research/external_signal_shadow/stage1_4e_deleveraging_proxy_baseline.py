import bisect
import random
from collections import defaultdict

from configs import base
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    CANDIDATE_1H,
    CANDIDATE_15M,
    EVENT_DOWN_FLUSH,
    EVENT_UP_SQUEEZE,
    ProxyEvent,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_replay import (
    replay_deleveraging_proxy_events,
)


def _hour_bucket(timestamp_ms: int) -> int:
    return (timestamp_ms // 3_600_000) % 24

def build_candidate_population(price_bars: list[dict], candidate_events: list[ProxyEvent]) -> dict[str, list[int]]:
    candidate_times = {event.event_time_ms for event in candidate_events}

    grouped = defaultdict(list)
    for bar in price_bars:
        symbol = bar.get("symbol")
        if symbol:
            grouped[symbol].append(bar)

    population = {}
    for symbol, bars in grouped.items():
        sorted_bars = sorted(bars, key=lambda x: x["bar_start_ms"])
        if not sorted_bars:
            population[symbol] = []
            continue

        last_t = sorted_bars[-1]["bar_start_ms"]
        eligible = []
        for idx in range(len(sorted_bars)):
            t = sorted_bars[idx]["bar_start_ms"]
            # Exclude candidate times
            if t in candidate_times:
                continue
            # Ensure enough forward data (at least 12h + 1h tolerance)
            if last_t - t < 13 * 3600 * 1000:
                continue
            eligible.append(t)
        population[symbol] = eligible
    return population

def sample_symbol_hour_matched_random_baseline(
    candidate_events: list[ProxyEvent],
    eligible_times_by_symbol: dict[str, list[int]],
    trials: int,
    random_seed: int,
) -> list[list[ProxyEvent]]:
    eligible_by_symbol_hour = {}
    for symbol, times in eligible_times_by_symbol.items():
        per_hour = defaultdict(list)
        for t in times:
            per_hour[_hour_bucket(t)].append(t)
        eligible_by_symbol_hour[symbol] = per_hour

    lag_ms = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_CONFIGURED_DATA_LAG_MS
    all_trials = []

    for trial_idx in range(trials):
        rng = random.Random(random_seed + trial_idx)
        trial_events = []

        for event in candidate_events:
            candidate_hour = _hour_bucket(event.event_time_ms)
            symbol_hours = eligible_by_symbol_hour.get(event.symbol, {})
            eligible = symbol_hours.get(candidate_hour, [])

            if not eligible:
                # Fallback to adjacent hours
                eligible = [
                    t for hour, times_list in symbol_hours.items()
                    if abs(hour - candidate_hour) <= 1 or abs(hour - candidate_hour) == 23
                    for t in times_list
                ]

            if not eligible:
                continue

            sampled_t = rng.choice(eligible)
            event_available_at_ms = sampled_t + lag_ms

            trial_events.append(ProxyEvent(
                symbol=event.symbol,
                candidate_name=event.candidate_name,
                event_label=event.event_label,
                signed_direction=event.signed_direction,
                bucket_start_ms=sampled_t - (event.bucket_end_ms - event.bucket_start_ms),
                bucket_end_ms=sampled_t,
                event_time_ms=sampled_t,
                event_available_at_ms=event_available_at_ms,
                entry_bar_start_ms=None,
                price_return=event.price_return,
                oi_change=event.oi_change,
                oi_start=event.oi_start,
                oi_end=event.oi_end,
                source=event.source,
                source_quality=event.source_quality
            ))

        all_trials.append(trial_events)

    return all_trials

def compute_random_baseline_summary(
    candidate_events: list[ProxyEvent],
    price_bars: list[dict],
    trials: int,
    random_seed: int,
) -> dict:
    if not candidate_events:
        return {
            "random_baseline_trials": trials,
            "median_net_return_bps_after_50bps": 0.0,
            "median_net_return_bps_after_50bps_1h": 0.0,
            "median_net_return_bps_after_50bps_4h": 0.0,
            "median_net_return_bps_after_50bps_12h": 0.0,
            "left_tail_net_return_bps_after_50bps_4h": 0.0,
            "baseline_sampling_failure_count": 0,
            "baseline_sampling_insufficient": False,
        }

    population = build_candidate_population(price_bars, candidate_events)
    trial_runs = sample_symbol_hour_matched_random_baseline(
        candidate_events,
        population,
        trials,
        random_seed
    )

    all_net_returns_1h = []
    all_net_returns_4h = []
    all_net_returns_12h = []
    failure_count = 0

    for trial in trial_runs:
        if len(trial) < len(candidate_events):
            failure_count += (len(candidate_events) - len(trial))

        replayed = replay_deleveraging_proxy_events(trial, price_bars)
        for r in replayed:
            win = r["forward_window_hours"]
            net_bps = r["net_return_bps_after_50bps"]
            if win == 1:
                all_net_returns_1h.append(net_bps)
            elif win == 4:
                all_net_returns_4h.append(net_bps)
            elif win == 12:
                all_net_returns_12h.append(net_bps)

    def get_median(lst):
        if not lst:
            return 0.0
        lst.sort()
        n = len(lst)
        if n % 2 == 1:
            return float(lst[n // 2])
        else:
            return float((lst[n // 2 - 1] + lst[n // 2]) / 2.0)

    median_1h = get_median(all_net_returns_1h)
    median_4h = get_median(all_net_returns_4h)
    median_12h = get_median(all_net_returns_12h)

    return {
        "random_baseline_trials": trials,
        "median_net_return_bps_after_50bps": median_4h, # default to 4h
        "median_net_return_bps_after_50bps_1h": median_1h,
        "median_net_return_bps_after_50bps_4h": median_4h,
        "median_net_return_bps_after_50bps_12h": median_12h,
        "left_tail_net_return_bps_after_50bps_4h": compute_left_tail(
            all_net_returns_4h,
            base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_LEFT_TAIL_PERCENTILE,
        ),
        "baseline_sampling_failure_count": failure_count,
        "baseline_sampling_insufficient": (failure_count > 0),
    }

def compute_price_move_baseline(
    price_bars: list[dict],
    candidate_name: str,
    expected_symbols: tuple[str, ...],
) -> list[ProxyEvent]:
    if candidate_name == CANDIDATE_15M:
        bucket_size = 15 * 60 * 1000
        price_threshold = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_PRICE_RETURN_THRESHOLD
        cooldown_ms = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_COOLDOWN_MS
    elif candidate_name == CANDIDATE_1H:
        bucket_size = 60 * 60 * 1000
        price_threshold = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_PRICE_RETURN_THRESHOLD
        cooldown_ms = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_COOLDOWN_MS
    else:
        raise ValueError(f"Invalid candidate_name: {candidate_name}")

    lag_ms = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_CONFIGURED_DATA_LAG_MS

    price_by_symbol = defaultdict(list)
    for r in price_bars:
        if r["symbol"] in expected_symbols:
            price_by_symbol[r["symbol"]].append(r)

    events = []
    cooldowns = {} # key: (symbol, label, direction) -> last_trigger_ms

    for symbol in expected_symbols:
        sorted_bars = sorted(price_by_symbol[symbol], key=lambda x: x["bar_start_ms"])
        if not sorted_bars:
            continue

        # Determine price bar interval for completeness check
        gaps = [sorted_bars[i]["bar_start_ms"] - sorted_bars[i-1]["bar_start_ms"] for i in range(1, len(sorted_bars))]
        if gaps:
            gaps.sort()
            price_bar_interval_ms = gaps[len(gaps) // 2]
        else:
            price_bar_interval_ms = bucket_size

        expected_bars = bucket_size // price_bar_interval_ms

        min_time = sorted_bars[0]["bar_start_ms"]
        max_time = sorted_bars[-1]["bar_start_ms"]

        start_bucket_ms = (min_time // bucket_size) * bucket_size
        end_bucket_ms = (max_time // bucket_size) * bucket_size

        price_times = [p["bar_start_ms"] for p in sorted_bars]

        curr_time = start_bucket_ms
        while curr_time <= end_bucket_ms:
            b_start = curr_time
            b_end = curr_time + bucket_size

            # Find price bars starting within [b_start, b_end)
            p_start_idx = bisect.bisect_left(price_times, b_start)
            p_end_idx = bisect.bisect_left(price_times, b_end)
            bucket_bars = sorted_bars[p_start_idx:p_end_idx]

            # Price completeness check
            if expected_bars > 1:
                if len(bucket_bars) < expected_bars:
                    curr_time += bucket_size
                    continue
            else:
                if len(bucket_bars) < 1:
                    curr_time += bucket_size
                    continue

            first_bar = bucket_bars[0]
            last_bar = bucket_bars[-1]
            price_return = last_bar["close"] / first_bar["open"] - 1.0

            is_down_flush = (price_return <= -price_threshold)
            is_up_squeeze = (price_return >= price_threshold)

            if is_down_flush or is_up_squeeze:
                label = EVENT_DOWN_FLUSH if is_down_flush else EVENT_UP_SQUEEZE
                direction = 1 if is_down_flush else -1

                event_time_ms = b_end
                available_at_ms = b_end + lag_ms

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
                        entry_bar_start_ms=None,
                        price_return=price_return,
                        oi_change=0.0,
                        oi_start=0.0,
                        oi_end=0.0,
                        source="price_only_baseline",
                        source_quality="close_price_proxy_not_fill_price"
                    )
                    events.append(event)

            curr_time += bucket_size

    events.sort(key=lambda x: x.event_time_ms)
    return events

def compute_left_tail(values: list[float], percentile: int = 5) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = min(len(sorted_vals) - 1, max(0, int(len(sorted_vals) * percentile / 100.0)))
    return float(sorted_vals[idx])
