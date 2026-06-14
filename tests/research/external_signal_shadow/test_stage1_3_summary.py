from __future__ import annotations

from research.external_signal_shadow.stage1_3_summary import (
    decide_candidate,
    decide_stage1_3_summary,
)


def _candidate(**overrides: object) -> dict:
    data = {
        "candidate_name": "volume_spike_1h",
        "candidate_role": "primary",
        "event_count": 120,
        "symbols_with_events": 3,
        "event_days": 25,
        "max_single_symbol_event_share": 0.40,
        "max_single_day_event_share": 0.10,
        "top_5_positive_events_gross_profit_share": 0.20,
        "baseline_excess_net_bps": 5.0,
        "median_net_return_after_50bps": 1.0,
        "left_tail_p05_after_50bps_vs_baseline_bps": 0.0,
    }
    data.update(overrides)
    return data


def test_candidate_data_insufficient_when_event_count_below_gate() -> None:
    result = decide_candidate(_candidate(event_count=99))
    assert result["candidate_decision"] == "candidate_data_insufficient"


def test_candidate_fails_when_top5_positive_concentration_too_high() -> None:
    result = decide_candidate(_candidate(top_5_positive_events_gross_profit_share=0.50))
    assert result["candidate_decision"] == "candidate_failed"
    assert result["primary_blocker"] == "top5_positive_pnl_concentration_high"


def test_candidate_diagnostic_promising_does_not_unlock_live_smoke() -> None:
    result = decide_candidate(_candidate(median_net_return_after_50bps=0.0, baseline_excess_net_bps=3.0))
    assert result["candidate_decision"] == "candidate_diagnostic_promising"
    assert result["live_smoke_allowed"] is False


def test_stage1_3_summary_stops_when_all_primary_candidates_fail() -> None:
    summary = decide_stage1_3_summary(
        {
            "candidate_results": [
                _candidate(candidate_name="volume_spike_1h", baseline_excess_net_bps=-1.0),
                _candidate(candidate_name="relative_strength_vs_btc", baseline_excess_net_bps=-1.0),
                _candidate(candidate_name="volume_confirmed_relative_strength", event_count=0),
            ],
            "alpha_interpretation_allowed": False,
            "collector_expansion_allowed": False,
            "live_shadow_required_now": False,
        }
    )
    assert summary["next_action"] == "stop_gate_ticker_direction"
    assert summary["alpha_interpretation_allowed"] is False


def test_stage1_3_fixture_summary_requests_real_historical_replay_not_stop_direction() -> None:
    summary = decide_stage1_3_summary(
        {
            "fixture_run": True,
            "research_result_valid": False,
            "candidate_results": [
                _candidate(candidate_name="volume_spike_1h", event_count=0),
                _candidate(candidate_name="relative_strength_vs_btc", event_count=0),
                _candidate(candidate_name="volume_confirmed_relative_strength", event_count=0),
            ],
            "alpha_interpretation_allowed": False,
            "collector_expansion_allowed": False,
            "live_shadow_required_now": False,
        }
    )

    assert summary["decision"] == "stage1_3_fixture_smoke_completed"
    assert summary["next_action"] == "run_real_historical_bars_replay"
