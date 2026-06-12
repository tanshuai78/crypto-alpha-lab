from src.research.external_signal_shadow.models import ShadowOrder


def _order(event_id: str, exit_reason: str, net_return_bps: float):
    return ShadowOrder(
        shadow_order_id=f"{event_id}:long:1",
        event_id=event_id,
        symbol="BTCUSDT",
        token_address=None,
        direction="long",
        entry_time_ms=1,
        entry_price=100.0,
        take_profit_price=101.5,
        stop_loss_price=99.0,
        vertical_barrier_time_ms=2,
        cost_round_trip_bps=50.0,
        status="closed",
        exit_time_ms=2,
        exit_price=101.5,
        exit_reason=exit_reason,
        gross_return_bps=150.0,
        net_return_bps=net_return_bps,
        max_adverse_excursion_bps=0.0,
        max_favorable_excursion_bps=150.0,
    )


def _valid_summary(**overrides):
    summary = {
        "mode": "fixture_only_stage0",
        "live_trading_enabled": False,
        "external_api_enabled": False,
        "wallet_required": False,
        "events_total": 3,
        "price_bars_total": 30,
        "events_accepted": 2,
        "events_rejected": 1,
        "events_quarantined": 0,
        "branches": {
            "no_cusum_all_accepted_events": {
                "shadow_order_count": 3,
                "take_profit_count": 1,
                "stop_loss_count": 1,
                "vertical_barrier_count": 1,
                "shadow_orders": [],
            },
            "cusum_confirmed_events": {
                "shadow_order_count": 1,
                "take_profit_count": 1,
                "stop_loss_count": 0,
                "vertical_barrier_count": 0,
                "shadow_orders": [],
            },
        },
        "branch_semantics": {
            "no_cusum_all_accepted_events": "baseline_control_not_strategy",
            "cusum_confirmed_events": "confirmation_filtered_shadow_not_strategy",
        },
        "parameter_policy": "fixed_stage0_sanity_check_not_optimized",
        "alpha_interpretation_allowed": False,
    }
    summary.update(overrides)
    return summary


def test_stage0_summary_passes_when_pipeline_runs_and_orders_exist():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    decision = decide_stage0_shadow_replay(_valid_summary())

    assert decision["decision"] == "external_signal_shadow_stage0_passed"
    assert decision["failure_type"] == "stage0_completed"


def test_stage0_summary_fails_when_no_accepted_events():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    decision = decide_stage0_shadow_replay(_valid_summary(events_accepted=0))

    assert decision["decision"] == "external_signal_shadow_stage0_failed"
    assert decision["failure_type"] == "risk_guard_density_failure"


def test_stage0_summary_fails_when_no_price_bars():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    decision = decide_stage0_shadow_replay(_valid_summary(price_bars_total=0))

    assert decision["decision"] == "external_signal_shadow_stage0_failed"
    assert decision["failure_type"] == "data_failure"


def test_stage0_summary_classifies_data_failure():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    decision = decide_stage0_shadow_replay(_valid_summary(events_total=0))

    assert decision["failure_type"] == "data_failure"


def test_stage0_summary_classifies_structure_failure_when_no_shadow_orders():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    summary = _valid_summary()
    summary["branches"]["no_cusum_all_accepted_events"]["shadow_order_count"] = 0
    summary["branches"]["cusum_confirmed_events"]["shadow_order_count"] = 0

    decision = decide_stage0_shadow_replay(summary)

    assert decision["failure_type"] == "shadow_order_structure_failure"


def test_stage0_summary_never_marks_live_safe():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    decision = decide_stage0_shadow_replay(_valid_summary())

    assert decision["live_safe"] is False
    assert decision["paper_shadow_allowed"] is False


def test_stage0_summary_reports_cusum_vs_no_cusum_comparison():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    decision = decide_stage0_shadow_replay(_valid_summary())

    assert "cusum_vs_no_cusum" in decision


def test_stage0_summary_passes_even_when_net_return_negative_if_pipeline_valid():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    decision = decide_stage0_shadow_replay(_valid_summary(total_net_return_bps=-10_000))

    assert decision["decision"] == "external_signal_shadow_stage0_passed"


def test_stage0_summary_does_not_use_pnl_as_alpha_decision():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    positive = decide_stage0_shadow_replay(_valid_summary(total_net_return_bps=10_000))
    negative = decide_stage0_shadow_replay(_valid_summary(total_net_return_bps=-10_000))

    assert positive["decision"] == negative["decision"]


def test_stage0_summary_requires_branch_semantics():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    summary = _valid_summary(branch_semantics={})
    decision = decide_stage0_shadow_replay(summary)

    assert decision["failure_type"] == "shadow_order_structure_failure"


def test_stage0_summary_requires_parameter_policy_and_no_alpha_interpretation():
    from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay

    decision = decide_stage0_shadow_replay(
        _valid_summary(alpha_interpretation_allowed=True)
    )

    assert decision["decision"] == "external_signal_shadow_stage0_failed"


def test_summarize_branch_orders_counts_outcomes():
    from src.research.external_signal_shadow.summary import summarize_branch_orders

    summary = summarize_branch_orders(
        [
            _order("a", "take_profit", 100.0),
            _order("b", "stop_loss", -150.0),
            _order("c", "vertical_barrier", -20.0),
        ]
    )

    assert summary["shadow_order_count"] == 3
    assert summary["take_profit_count"] == 1
    assert summary["stop_loss_count"] == 1
    assert summary["vertical_barrier_count"] == 1
    assert summary["total_net_return_bps"] == -70.0
