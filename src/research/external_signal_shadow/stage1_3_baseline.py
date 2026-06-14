from __future__ import annotations

import random

from research.external_signal_shadow.stage1_3_candidates import CandidateEvent


def sample_random_baseline_events(
    candidate_events: list[CandidateEvent],
    *,
    eligible_event_times_by_symbol: dict[str, list[int]],
    random_seed: int,
) -> list[CandidateEvent]:
    rng = random.Random(random_seed)
    candidate_times = {event.event_time_ms for event in candidate_events}
    sampled: list[CandidateEvent] = []
    for event in candidate_events:
        eligible = [
            timestamp
            for timestamp in eligible_event_times_by_symbol.get(event.symbol, [])
            if timestamp not in candidate_times
        ]
        if not eligible:
            continue
        sampled.append(
            CandidateEvent(
                candidate_name=f"random_baseline_for_{event.candidate_name}",
                symbol=event.symbol,
                event_time_ms=rng.choice(eligible),
                candidate_role="baseline",
                metadata={"baseline_type": "symbol_matched_random"},
            )
        )
    return sampled


def _hour_bucket(timestamp_ms: int) -> int:
    return (timestamp_ms // 3_600_000) % 24


def _eligible_by_hour(
    candidate_time_ms: int,
    eligible_times: list[int],
    candidate_times: set[int],
) -> list[int]:
    candidate_hour = _hour_bucket(candidate_time_ms)
    same_hour = [
        item for item in eligible_times
        if item not in candidate_times and _hour_bucket(item) == candidate_hour
    ]
    if same_hour:
        return same_hour
    near_hour = [
        item for item in eligible_times
        if item not in candidate_times and abs(_hour_bucket(item) - candidate_hour) <= 1
    ]
    return near_hour


def run_random_baseline_trials(
    candidate_events: list[CandidateEvent],
    *,
    eligible_event_times_by_symbol: dict[str, list[int]],
    trials: int,
    random_seed: int,
) -> dict:
    candidate_times = {event.event_time_ms for event in candidate_events}
    eligible_by_symbol_hour: dict[str, dict[int, list[int]]] = {}
    for symbol, times in eligible_event_times_by_symbol.items():
        per_hour: dict[int, list[int]] = {}
        for timestamp in times:
            if timestamp in candidate_times:
                continue
            per_hour.setdefault(_hour_bucket(timestamp), []).append(timestamp)
        eligible_by_symbol_hour[symbol] = per_hour

    all_trials: list[list[CandidateEvent]] = []
    insufficient = 0
    for trial_index in range(trials):
        sampled: list[CandidateEvent] = []
        rng = random.Random(random_seed + trial_index)
        for event in candidate_events:
            candidate_hour = _hour_bucket(event.event_time_ms)
            symbol_hours = eligible_by_symbol_hour.get(event.symbol, {})
            eligible = symbol_hours.get(candidate_hour, [])
            if not eligible:
                eligible = [
                    timestamp
                    for hour, values in symbol_hours.items()
                    if abs(hour - candidate_hour) <= 1
                    for timestamp in values
                ]
            if not eligible:
                insufficient += 1
                continue
            sampled.append(
                CandidateEvent(
                    candidate_name=f"random_baseline_for_{event.candidate_name}",
                    symbol=event.symbol,
                    event_time_ms=rng.choice(eligible),
                    candidate_role="baseline",
                    metadata={"baseline_type": "symbol_and_hour_matched_random"},
                )
            )
        all_trials.append(sampled)
    return {
        "random_baseline_trials": trials,
        "trials": all_trials,
        "baseline_sampling_insufficient_count": insufficient,
    }
