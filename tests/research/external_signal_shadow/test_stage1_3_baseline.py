from __future__ import annotations

from research.external_signal_shadow.stage1_3_baseline import (
    run_random_baseline_trials,
    sample_random_baseline_events,
)
from research.external_signal_shadow.stage1_3_candidates import CandidateEvent


def test_random_baseline_matches_event_count_and_symbol_distribution() -> None:
    candidates = [
        CandidateEvent("volume_spike_1h", "ETHUSDT", 1000, "primary", {}),
        CandidateEvent("volume_spike_1h", "ETHUSDT", 2000, "primary", {}),
        CandidateEvent("volume_spike_1h", "SOLUSDT", 3000, "primary", {}),
    ]
    eligible = {
        "ETHUSDT": [10_000, 20_000, 30_000, 40_000],
        "SOLUSDT": [10_000, 20_000, 30_000, 40_000],
    }
    sampled = sample_random_baseline_events(candidates, eligible_event_times_by_symbol=eligible, random_seed=1)
    assert len(sampled) == len(candidates)
    assert [event.symbol for event in sampled].count("ETHUSDT") == 2
    assert [event.symbol for event in sampled].count("SOLUSDT") == 1
    assert all(event.event_time_ms not in {1000, 2000, 3000} for event in sampled)


def test_random_baseline_runs_500_trials_and_reports_distribution() -> None:
    candidates = [CandidateEvent("volume_spike_1h", "ETHUSDT", 3_600_000, "primary", {})]
    eligible = {"ETHUSDT": [hour * 3_600_000 for hour in range(2, 24)]}
    result = run_random_baseline_trials(
        candidates,
        eligible_event_times_by_symbol=eligible,
        trials=500,
        random_seed=20260613,
    )
    assert result["random_baseline_trials"] == 500
    assert len(result["trials"]) == 500
    assert result["baseline_sampling_insufficient_count"] == 0


def test_random_baseline_matches_hour_of_day_when_available() -> None:
    candidate_time = 10 * 3_600_000
    candidates = [CandidateEvent("volume_spike_1h", "ETHUSDT", candidate_time, "primary", {})]
    eligible = {"ETHUSDT": [10 * 3_600_000 + 86_400_000, 12 * 3_600_000]}
    result = run_random_baseline_trials(
        candidates,
        eligible_event_times_by_symbol=eligible,
        trials=1,
        random_seed=1,
    )
    sampled = result["trials"][0][0]
    assert sampled.event_time_ms % 86_400_000 == candidate_time % 86_400_000


def test_random_baseline_reports_sampling_insufficient_when_no_bucket() -> None:
    candidates = [CandidateEvent("volume_spike_1h", "ETHUSDT", 10 * 3_600_000, "primary", {})]
    result = run_random_baseline_trials(
        candidates,
        eligible_event_times_by_symbol={"ETHUSDT": []},
        trials=3,
        random_seed=1,
    )
    assert result["baseline_sampling_insufficient_count"] == 3
