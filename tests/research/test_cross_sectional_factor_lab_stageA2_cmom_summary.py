from __future__ import annotations

from research.cross_sectional_factor_lab.summary import decide_stageA2_cmom


def _variant(
    return_pct: float,
    dd: float,
    vs_btc: float,
    vs_eth: float,
    vs_ew: float,
    top5_return: float,
    stress_return: float | None = None,
    month_share: float = 0.20,
    abs_month_share: float = 0.20,
    rebalance_count: int = 77,
) -> dict:
    return {
        "performance": {
            "base_30bps_total_return_pct": return_pct,
            "stress_50bps_total_return_pct": stress_return if stress_return is not None else return_pct - 2.0,
            "max_drawdown_pct": dd,
        },
        "benchmarks": {
            "vs_btc_total_return_pct": vs_btc,
            "vs_eth_total_return_pct": vs_eth,
            "vs_universe_equal_weight_total_return_pct": vs_ew,
        },
        "diagnostic_top5_performance": {
            "strategy_total_return_pct": top5_return,
        },
        "concentration": {
            "max_single_symbol_positive_pnl_share": 0.20,
            "max_single_symbol_abs_pnl_share": 0.20,
            "max_single_month_positive_pnl_share": month_share,
            "max_single_month_abs_pnl_share": abs_month_share,
        },
        "rebalance_quality": {
            "rebalance_count": rebalance_count,
        },
    }


def test_stageA2_cmom_proceeds_to_regime_gated_diagnostic_when_all_gates_pass() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-40.0, 50.0, -20.0, -18.0, 2.0, -45.0),
            "cmom_14d_skip_1d": _variant(-25.0, 45.0, -8.0, -6.0, 12.0, -26.0),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "proceed_to_regime_gated_cmom_diagnostic_design"
    assert decision["primary_comparison"]["cmom_beats_30d_after_30bps"] is True


def test_stageA2_cmom_does_not_proceed_when_eth_gate_fails() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-40.0, 50.0, -20.0, -18.0, 2.0, -45.0),
            "cmom_14d_skip_1d": _variant(-25.0, 45.0, -8.0, -20.0, 12.0, -26.0),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "run_3d_failure_diagnostic"


def test_stageA2_cmom_runs_3d_failure_diagnostic_only_when_improvement_is_material() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-84.0, 84.0, -44.0, -26.0, 0.5, -90.0),
            "cmom_14d_skip_1d": _variant(-65.0, 80.0, -25.0, -12.0, 8.0, -70.0, month_share=0.40),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "run_3d_failure_diagnostic"


def test_stageA2_cmom_stops_when_improvement_is_only_small_damage_reduction() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-84.0, 84.0, -44.0, -26.0, 0.5, -90.0),
            "cmom_14d_skip_1d": _variant(-73.0, 85.0, -33.0, -20.0, 2.0, -88.0, month_share=0.60),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "stop_price_only_momentum"


def test_stageA2_cmom_stops_price_only_momentum_when_cmom_does_not_improve() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-84.0, 84.0, -44.0, -26.0, 0.5, -90.0),
            "cmom_14d_skip_1d": _variant(-82.0, 86.0, -42.0, -24.0, 1.0, -88.0),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "stop_price_only_momentum"


def test_stageA2_cmom_does_not_promote_when_positive_month_concentration_too_high() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-40.0, 50.0, -20.0, -18.0, 2.0, -45.0),
            "cmom_14d_skip_1d": _variant(-25.0, 45.0, -8.0, -6.0, 12.0, -26.0, month_share=0.80),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "stop_price_only_momentum"


def test_stageA2_cmom_does_not_promote_when_50bps_stress_fails() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-40.0, 50.0, -20.0, -18.0, 2.0, -45.0),
            "cmom_14d_skip_1d": _variant(-25.0, 45.0, -8.0, -6.0, 12.0, -26.0, stress_return=-70.0),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["next_action"] == "run_3d_failure_diagnostic"


def test_stageA2_cmom_data_unavailable_when_rebalance_count_below_gate() -> None:
    summary = {
        "factor_variants": {
            "momentum_30d_skip_1d": _variant(-40.0, 50.0, -20.0, -18.0, 2.0, -45.0, rebalance_count=10),
            "cmom_14d_skip_1d": _variant(-25.0, 45.0, -8.0, -6.0, 12.0, -26.0, rebalance_count=10),
        }
    }

    decision = decide_stageA2_cmom(summary)

    assert decision["decision"] == "stageA2_cmom_data_unavailable"
    assert decision["primary_blocker"] == "insufficient_rebalance_count"
