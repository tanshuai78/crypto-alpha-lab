from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_summary import (
    compute_concentration_metrics,
    decide_stage1_5c_replay_summary,
)


def test_concentration_uses_primary_forward_and_primary_cost_only():
    rows = [
        {"candidate_event_unit_id": "a", "symbol": "ABCUSDT", "event_time_ms": 0, "forward_window_hours": 4, "cost_bps": 50, "net_return_bps": 100},
        {"candidate_event_unit_id": "a", "symbol": "ABCUSDT", "event_time_ms": 0, "forward_window_hours": 12, "cost_bps": 50, "net_return_bps": 80},
        {"candidate_event_unit_id": "a", "symbol": "ABCUSDT", "event_time_ms": 0, "forward_window_hours": 4, "cost_bps": 80, "net_return_bps": 70},
        {"candidate_event_unit_id": "b", "symbol": "XYZUSDT", "event_time_ms": 86_400_000, "forward_window_hours": 4, "cost_bps": 50, "net_return_bps": -10},
    ]
    m = compute_concentration_metrics(rows, primary_forward_window_hours=4, primary_cost_bps=50)
    assert m["event_count"] == 2
    assert m["max_single_symbol_event_share"] == 0.5


def test_futures_launch_signed_modes_have_separate_density_gates():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "futures_launch_density": {
            "raw_symbol_event_count": 40,
            "signed_mode_count": {
                "futures_launch_long_attention_diagnostic": 40,
                "futures_launch_short_access_diagnostic": 40,
            },
            "do_not_sum_signed_modes_for_density_gate": True,
        },
        "cell_summaries": {
            "futures_contract_launch|long|1h|G2_price_coverage_only": {"cell_event_count": 40},
            "futures_contract_launch|short|1h|G2_price_coverage_only": {"cell_event_count": 40},
        },
    })
    assert summary["futures_launch_density"]["do_not_sum_signed_modes_for_density_gate"] is True


def test_no_mixed_event_type_top_level_pass_claim():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "mixed_event_type_aggregate_only": True,
        "cell_summaries": {},
    })
    assert summary["top_level_decision"] == "stage1_5c_replay_completed"
    assert summary["promising_cells"] == []
    assert "no_cell_level_promising_result" in summary["blockers"]


def test_summary_outputs_coverage_attrition_funnel():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "coverage_attrition_funnel": {
            "stage1_5b_symbol_events": 194,
            "allowed_event_type_events": 194,
            "market_pair_existence_verified_count": 50,
            "price_history_coverage_pass_count": 40,
            "liquidity_proxy_pass_count": 20,
            "candidate_count_after_cooldown": 18,
            "replay_result_primary_rows": 18,
            "coverage_reject_reason_counts": {"missing_entry_bar": 3},
        },
        "cell_summaries": {},
    })
    funnel = summary["coverage_attrition_funnel"]
    assert funnel["stage1_5b_symbol_events"] == 194
    assert funnel["price_history_coverage_pass_count"] == 40
    assert funnel["coverage_reject_reason_counts"]["missing_entry_bar"] == 3


def test_top_level_invalid_when_no_price_coverage():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "coverage_attrition_funnel": {
            "stage1_5b_symbol_events": 194,
            "allowed_event_type_events": 194,
            "market_pair_existence_verified_count": 0,
            "price_history_coverage_pass_count": 0,
            "liquidity_proxy_pass_count": 0,
            "candidate_count_after_cooldown": 0,
            "replay_result_primary_rows": 0,
            "coverage_reject_reason_counts": {"missing_price_history": 194},
        },
        "cell_summaries": {},
    })
    assert summary["top_level_decision"] == "stage1_5c_replay_invalid"
    assert summary["research_result_valid"] is False
    assert "no_price_history_coverage" in summary["blockers"]
    assert "no_replay_primary_rows" in summary["blockers"]


def test_concentration_metrics_uses_events_not_windows():
    rows = [
        {"symbol": "ABCUSDT", "event_time_ms": 0, "net_return_bps": 100, "signed_mode": "m"},
        {"symbol": "ABCUSDT", "event_time_ms": 0, "net_return_bps": 80, "signed_mode": "m"},
        {"symbol": "XYZUSDT", "event_time_ms": 86_400_000, "net_return_bps": -10, "signed_mode": "m"},
    ]
    m = compute_concentration_metrics(rows)
    assert m["max_single_symbol_event_share"] == 2 / 3
    assert m["max_single_day_event_share"] == 2 / 3


def test_decision_promising_requires_baseline_and_concentration_pass():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "event_count": 40,
        "event_days": 12,
        "symbols_with_events": 4,
        "primary_event_type_events": 30,
        "median_net_return_after_50bps_4h": 10.0,
        "baseline_excess_net_bps_4h": 5.0,
        "price_baseline_excess_net_bps_4h": 4.0,
        "left_tail_p05_after_50bps_4h": -20.0,
        "random_baseline_left_tail_p05_after_50bps_4h": -25.0,
        "top_5_positive_events_gross_profit_share": 0.20,
        "max_single_day_event_share": 0.20,
        "max_single_symbol_event_share": 0.30,
        "baseline_sampling_insufficient": False,
    })
    assert summary["cell_decision"] == "stage1_5c_cell_promising"
    assert summary["paper_trading_allowed"] is False
    assert summary["live_trading_allowed"] is False


def test_decision_failed_when_cost_after_median_negative():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "event_count": 40,
        "event_days": 12,
        "symbols_with_events": 4,
        "primary_event_type_events": 30,
        "median_net_return_after_50bps_4h": -1.0,
        "baseline_excess_net_bps_4h": 5.0,
        "price_baseline_excess_net_bps_4h": 4.0,
        "left_tail_p05_after_50bps_4h": -20.0,
        "random_baseline_left_tail_p05_after_50bps_4h": -25.0,
        "top_5_positive_events_gross_profit_share": 0.20,
        "max_single_day_event_share": 0.20,
        "max_single_symbol_event_share": 0.30,
        "baseline_sampling_insufficient": False,
    })
    assert summary["cell_decision"] == "stage1_5c_cell_failed"
    assert "median_net_return_after_50bps_not_positive" in summary["blockers"]
