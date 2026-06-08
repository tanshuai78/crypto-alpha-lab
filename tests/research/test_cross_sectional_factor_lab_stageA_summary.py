from __future__ import annotations

from research.cross_sectional_factor_lab.summary import decide_stageA_v1, summarize_rebalance_quality


def _passing_summary() -> dict:
    return {
        "performance": {
            "by_cost_scenario": {
                "base_30_bps_round_trip": {
                    "strategy_total_return_pct": 25.0,
                    "strategy_max_drawdown_pct": 10.0,
                },
                "stress_50_bps_round_trip": {
                    "strategy_total_return_pct": 10.0,
                },
                "crash_80_bps_round_trip": {
                    "strategy_total_return_pct": 2.0,
                },
            }
        },
        "benchmarks": {
            "btc_buy_and_hold_net_with_entry_exit_cost_pct": 15.0,
            "eth_buy_and_hold_net_with_entry_exit_cost_pct": 12.0,
            "universe_equal_weight_total_return_pct": 18.0,
            "universe_equal_weight_max_drawdown_pct": 9.0,
        },
        "concentration": {
            "max_single_symbol_positive_pnl_share": 0.20,
            "max_single_symbol_abs_pnl_share": 0.20,
            "max_single_month_positive_pnl_share": 0.20,
            "max_single_month_abs_pnl_share": 0.20,
        },
        "rebalance_quality": {
            "rebalance_count": 60,
            "insufficient_universe_count": 1,
            "median_selected_symbol_count": 10,
        },
    }


def test_stageA_v1_passes_when_all_gates_pass() -> None:
    assert decide_stageA_v1(_passing_summary()) == "stageA_v1_passed"


def test_stageA_v1_fails_when_base_cost_does_not_beat_equal_weight() -> None:
    summary = _passing_summary()
    summary["performance"]["by_cost_scenario"]["base_30_bps_round_trip"]["strategy_total_return_pct"] = 10.0

    assert decide_stageA_v1(summary) == "stageA_v1_failed"


def test_stageA_v1_fails_on_symbol_concentration() -> None:
    summary = _passing_summary()
    summary["concentration"]["max_single_symbol_positive_pnl_share"] = 0.50

    assert decide_stageA_v1(summary) == "stageA_v1_failed"


def test_concentration_handles_negative_total_pnl() -> None:
    summary = _passing_summary()
    summary["performance"]["by_cost_scenario"]["base_30_bps_round_trip"]["strategy_total_return_pct"] = -5.0
    summary["concentration"]["max_single_symbol_positive_pnl_share"] = 0.0
    summary["concentration"]["max_single_symbol_abs_pnl_share"] = 0.80

    assert decide_stageA_v1(summary) == "stageA_v1_failed"


def test_concentration_reports_abs_pnl_share() -> None:
    summary = _passing_summary()

    assert "max_single_symbol_abs_pnl_share" in summary["concentration"]
    assert "max_single_month_abs_pnl_share" in summary["concentration"]


def test_rebalance_quality_counts_insufficient_universe_ratio() -> None:
    quality = summarize_rebalance_quality(
        rebalance_count=100,
        insufficient_universe_count=5,
        selected_counts=[10, 10, 9],
        turnovers=[1.0, 0.5],
    )

    assert quality["insufficient_universe_ratio"] == 0.05
