from research.external_signal_shadow.stage1_4b_lite_summary import (
    compute_concentration_stats,
    decide_candidate_family_summary,
    decide_stage1_4b_lite_summary,
)


def test_compute_concentration_stats():
    # We pass events and their replay rows
    events = [
        {"symbol": "BTCUSDT", "event_time_ms": 1000},
        {"symbol": "BTCUSDT", "event_time_ms": 2000},
        {"symbol": "ETHUSDT", "event_time_ms": 3000 + 86400000}, # different day
        {"symbol": "SOLUSDT", "event_time_ms": 4000},
    ]

    # replay_rows: we mock them with different terminal returns (bps)
    replay_rows = [
        {"symbol": "BTCUSDT", "event_time_ms": 1000, "terminal_return_4h_net_bps_after_50bps": 100.0},
        {"symbol": "BTCUSDT", "event_time_ms": 2000, "terminal_return_4h_net_bps_after_50bps": 200.0},
        {"symbol": "ETHUSDT", "event_time_ms": 3000 + 86400000, "terminal_return_4h_net_bps_after_50bps": -50.0}, # negative
        {"symbol": "SOLUSDT", "event_time_ms": 4000, "terminal_return_4h_net_bps_after_50bps": 300.0},
    ]

    stats = compute_concentration_stats(events, replay_rows)
    # total events = 4
    # symbol BTCUSDT has 2/4 = 0.50 max share
    assert stats["max_single_symbol_event_share"] == 0.50
    # Day 0 (ts < 86400000) has 3 events (1000, 2000, 4000) -> 3/4 = 0.75 max share
    assert stats["max_single_day_event_share"] == 0.75

    # Positive gross profit events: 100, 200, 300. sum = 600.
    # Top 5 positive events (we only have 3 positive ones):
    # Sort positive: 300, 200, 100. Top 5 sum = 600.
    # Share of top 5 in positive = 600 / 600 = 1.0 (in actual test we have 3 positive so it is 1.0)
    # Let's verify top_5_positive_events_gross_profit_share is calculated
    assert stats["top_5_positive_events_gross_profit_share"] == 1.0

    # Abs PNL: 100, 200, 50, 300. sum = 650.
    # Top 5 abs: 300, 200, 100, 50. sum = 650.
    # Share = 650 / 650 = 1.0
    assert stats["top_5_abs_pnl_share"] == 1.0


def test_decide_candidate_family_summary_failed_no_excess():
    # Candidate family decision
    # If candidate median return <= baseline return, it is failed
    cand_summary = {
        "candidate_name": "oi_expansion_trend_confirmation",
        "event_count": 120,
        "event_days": 25,
        "symbols_count": 4,
        "median_net_return_bps": 10.0,
        "random_baseline_median_bps": 15.0, # beats candidate
        "price_move_baseline_median_bps": 5.0,
        "max_single_symbol_event_share": 0.30,
        "max_single_day_event_share": 0.10,
        "top_5_positive_events_gross_profit_share": 0.20,
    }
    res = decide_candidate_family_summary(cand_summary)
    assert res["decision"] == "crowding_lite_weak"
    assert res["blocker"] == "no_positive_random_baseline_excess"


def test_decide_candidate_family_summary_failed_on_density_gate():
    cand_summary = {
        "candidate_name": "oi_expansion_trend_confirmation",
        "event_count": 20,
        "event_days": 5,
        "symbols_count": 1,
        "median_net_return_bps": 25.0,
        "random_baseline_median_bps": 5.0,
        "price_move_baseline_median_bps": 5.0,
        "max_single_symbol_event_share": 0.20,
        "max_single_day_event_share": 0.10,
        "top_5_positive_events_gross_profit_share": 0.20,
    }
    res = decide_candidate_family_summary(cand_summary)
    assert res["decision"] == "crowding_lite_failed"
    assert res["blocker"] == "candidate_event_count_below_min"


def test_decide_candidate_family_summary_promising():
    cand_summary = {
        "candidate_name": "oi_expansion_trend_confirmation",
        "event_count": 120,
        "event_days": 25,
        "symbols_count": 4,
        "median_net_return_bps": 20.0,
        "random_baseline_median_bps": 15.0,
        "price_move_baseline_median_bps": 10.0,
        "max_single_symbol_event_share": 0.30,
        "max_single_day_event_share": 0.10,
        "top_5_positive_events_gross_profit_share": 0.20,
    }
    res = decide_candidate_family_summary(cand_summary)
    assert res["decision"] == "crowding_lite_promising"
    assert res["blocker"] is None


def test_decide_stage1_4b_lite_summary_overall():
    summary_data = {
        "fixture_run": False,
        "total_events": 150,
        "total_days": 25,
        "total_symbols": 4,
        "max_single_symbol_event_share": 0.30,
        "max_single_day_event_share": 0.10,
        "top_5_positive_events_gross_profit_share": 0.20,
        "candidates": {
            "oi_expansion_trend_confirmation": {
                "decision": "crowding_lite_promising",
                "blocker": None,
            },
            "funding_oi_crowding_unwind": {
                "decision": "crowding_lite_failed",
                "blocker": "no_positive_baseline_excess",
            },
            "oi_contraction_after_price_flush": {
                "decision": "crowding_lite_failed",
                "blocker": "density_gate_insufficient",
            }
        }
    }
    res = decide_stage1_4b_lite_summary(summary_data)
    assert res["decision"] == "crowding_lite_promising"
    assert res["next_action"] == "prepare_stage1_4c_joint_decision_review"
    assert res["liquidation_used"] is False
    assert res["stage1_4b_full_composite_allowed"] is False


def test_decide_stage1_4b_lite_summary_weak_when_no_promising_but_not_all_failed():
    summary_data = {
        "fixture_run": False,
        "total_events": 150,
        "total_days": 25,
        "total_symbols": 4,
        "max_single_symbol_event_share": 0.30,
        "max_single_day_event_share": 0.10,
        "top_5_positive_events_gross_profit_share": 0.20,
        "candidates": {
            "oi_expansion_trend_confirmation": {
                "decision": "crowding_lite_weak",
                "blocker": "median_net_return_not_positive",
            },
            "funding_oi_crowding_unwind": {
                "decision": "crowding_lite_failed",
                "blocker": "no_positive_baseline_excess",
            },
            "oi_contraction_after_price_flush": {
                "decision": "crowding_lite_failed",
                "blocker": "density_gate_insufficient",
            }
        }
    }
    res = decide_stage1_4b_lite_summary(summary_data)
    assert res["decision"] == "crowding_lite_weak"
    assert res["next_action"] == "keep_as_secondary_track_only"
