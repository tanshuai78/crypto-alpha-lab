import random

from configs import base
from research.external_signal_shadow.stage1_4b_lite_models import CandidateEvent
from research.external_signal_shadow.stage1_4b_lite_replay import (
    _build_price_index,
    replay_candidate_events_with_index,
)


def _hour_bucket(timestamp_ms: int) -> int:
    return (timestamp_ms // 3_600_000) % 24


def build_candidate_population(price_bars: list[dict], candidate_events: list[CandidateEvent]) -> dict[str, list[int]]:
    candidate_times = {event.event_time_ms for event in candidate_events}

    grouped: dict[str, list[dict]] = {}
    for bar in price_bars:
        symbol = bar.get("symbol")
        if symbol:
            grouped.setdefault(symbol, []).append(bar)

    population: dict[str, list[int]] = {}
    for symbol, bars in grouped.items():
        sorted_bars = sorted(bars, key=lambda x: int(x["bar_start_ms"]))
        eligible = []
        for idx in range(len(sorted_bars)):
            if idx + 18 >= len(sorted_bars):
                continue
            t = int(sorted_bars[idx]["bar_start_ms"])
            if t in candidate_times:
                continue
            eligible.append(t)
        population[symbol] = eligible
    return population


def sample_symbol_hour_matched_random_baseline(
    candidate_events: list[CandidateEvent],
    eligible_times_by_symbol: dict[str, list[int]],
    trials: int,
    random_seed: int,
) -> list[list[CandidateEvent]]:
    eligible_by_symbol_hour: dict[str, dict[int, list[int]]] = {}
    for symbol, times in eligible_times_by_symbol.items():
        per_hour: dict[int, list[int]] = {}
        for t in times:
            per_hour.setdefault(_hour_bucket(t), []).append(t)
        eligible_by_symbol_hour[symbol] = per_hour

    all_trials: list[list[CandidateEvent]] = []

    for trial_idx in range(trials):
        rng = random.Random(random_seed + trial_idx)
        trial_events: list[CandidateEvent] = []

        for event in candidate_events:
            candidate_hour = _hour_bucket(event.event_time_ms)
            symbol_hours = eligible_by_symbol_hour.get(event.symbol, {})

            eligible = symbol_hours.get(candidate_hour, [])

            if not eligible:
                eligible = [
                    t for hour, times_list in symbol_hours.items()
                    if abs(hour - candidate_hour) <= 1 or abs(hour - candidate_hour) == 23
                    for t in times_list
                ]

            if not eligible:
                continue

            sampled_t = rng.choice(eligible)
            event_available_at_ms = sampled_t + 15 * 60 * 1000
            entry_bar_start_ms = sampled_t + 30 * 60 * 1000

            trial_events.append(CandidateEvent(
                candidate_name=event.candidate_name,
                symbol=event.symbol,
                event_time_ms=sampled_t,
                event_available_at_ms=event_available_at_ms,
                entry_bar_start_ms=entry_bar_start_ms,
                signed_direction=event.signed_direction,
                metadata={"baseline_type": "symbol_and_hour_matched_random", "original_event_time": event.event_time_ms}
            ))

        all_trials.append(trial_events)

    return all_trials


def compute_random_baseline_summary(
    candidate_events: list[CandidateEvent],
    price_bars: list[dict],
    trials: int,
    random_seed: int,
) -> dict:
    if not candidate_events:
        return {
            "random_baseline_trials": trials,
            "median_net_return_bps_after_50bps": 0.0,
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

    all_net_returns = []
    failure_count = 0
    price_index = _build_price_index(price_bars)
    replay_cache: dict[tuple[str, int, int], dict | None] = {}

    for trial in trial_runs:
        if len(trial) < len(candidate_events):
            failure_count += (len(candidate_events) - len(trial))

        results = replay_candidate_events_with_index(
            trial,
            price_index=price_index,
            replay_cache=replay_cache,
        )
        for r in results:
            all_net_returns.append(r["terminal_return_4h_net_bps_after_50bps"])

    if all_net_returns:
        all_net_returns.sort()
        n = len(all_net_returns)
        if n % 2 == 1:
            median_val = all_net_returns[n // 2]
        else:
            median_val = (all_net_returns[n // 2 - 1] + all_net_returns[n // 2]) / 2.0
    else:
        median_val = 0.0

    return {
        "random_baseline_trials": trials,
        "median_net_return_bps_after_50bps": median_val,
        "baseline_sampling_failure_count": failure_count,
        "baseline_sampling_insufficient": (failure_count > 0),
    }


def compute_price_move_1h_baseline(
    price_bars: list[dict],
    default_symbols: list[str],
) -> list[CandidateEvent]:
    grouped: dict[str, list[dict]] = {}
    for bar in price_bars:
        symbol = bar.get("symbol")
        if symbol:
            grouped.setdefault(symbol, []).append(bar)

    events = []
    threshold = base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_BASELINE_1H_RETURN_PCT

    for symbol in default_symbols:
        bars = grouped.get(symbol, [])
        if len(bars) < 5:
            continue
        sorted_bars = sorted(bars, key=lambda x: int(x["bar_start_ms"]))

        for idx in range(4, len(sorted_bars)):
            bar = sorted_bars[idx]
            bar_start_ms = int(bar["bar_start_ms"])
            close_price = float(bar["close_price"])

            prev_bar = sorted_bars[idx - 4]
            prev_close = float(prev_bar["close_price"])
            if prev_close <= 0:
                continue

            return_1h = (close_price - prev_close) / prev_close

            if abs(return_1h) >= threshold:
                signed_direction = 1 if return_1h > 0 else -1

                if idx + 18 >= len(sorted_bars):
                    continue

                event_available_at_ms = bar_start_ms + 15 * 60 * 1000
                entry_bar_start_ms = bar_start_ms + 30 * 60 * 1000

                events.append(CandidateEvent(
                    candidate_name="price_move_1h_baseline",
                    symbol=symbol,
                    event_time_ms=bar_start_ms,
                    event_available_at_ms=event_available_at_ms,
                    entry_bar_start_ms=entry_bar_start_ms,
                    signed_direction=signed_direction,
                    metadata={"price_1h_return": return_1h}
                ))

    cooldown_ms = base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_EVENT_COOLDOWN_HOURS * 3600 * 1000
    last_triggered = {}
    filtered_events = []

    events.sort(key=lambda x: x.event_time_ms)

    for event in events:
        key = (event.symbol, event.signed_direction)
        last_t = last_triggered.get(key)
        if last_t is None or event.event_time_ms - last_t >= cooldown_ms:
            filtered_events.append(event)
            last_triggered[key] = event.event_time_ms

    return filtered_events
