from src.research.extreme_funding_basis_replay import build_historical_basis_row
from src.research.extreme_funding_parameter_sensitivity import (
    SensitivityParamSet,
    build_parameter_grid,
    run_candidate_sensitivity,
    run_shadow_sensitivity,
)


def _rows_for_sensitivity():
    return [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=90.0,
            spot_mid_price=100.0,
            perp_mid_price=100.10,
        ),
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=2000,
            funding_rate=0.007,
            annualized_pct=110.0,
            spot_mid_price=100.0,
            perp_mid_price=100.05,
        ),
    ]


def test_build_parameter_grid_cartesian_product_includes_basis_absorption() -> None:
    params = build_parameter_grid(
        annualized_grid=(80.0, 100.0),
        min_income_grid=(50.0,),
        max_slippage_grid=(10.0,),
        expected_intervals_grid=(1, 2),
        basis_absorption_grid=(0.30, 0.50),
    )
    assert len(params) == 8
    assert params[0].basis_absorption_max_ratio in {0.30, 0.50}


def test_candidate_sensitivity_outputs_assumption_level() -> None:
    rows = _rows_for_sensitivity()
    param_set = SensitivityParamSet(
        annualized_threshold_pct=80.0,
        min_expected_funding_income_bps=50.0,
        max_slippage_bps=10.0,
        expected_holding_intervals=1,
        basis_absorption_max_ratio=0.50,
    )

    summaries = run_candidate_sensitivity(rows, [param_set])

    assert len(summaries) == 1
    assert summaries[0]["param_set"]["assumption_level"] == "conservative_1_interval"
    assert summaries[0]["coverage_quality"] == "historical_basis_proxy_not_depth_aware"
    assert summaries[0]["depth_aware"] is False
    assert "admission_layer_counts" in summaries[0]
    assert "research_to_trade_blocker_counts" in summaries[0]
    assert "anchor_event_count" in summaries[0]
    assert "research_shadow_admitted_count" in summaries[0]
    assert "trade_candidate_count" in summaries[0]


def test_shadow_sensitivity_only_uses_research_shadow_rows() -> None:
    rows = _rows_for_sensitivity()
    params = [
        SensitivityParamSet(
            annualized_threshold_pct=120.0,
            min_expected_funding_income_bps=50.0,
            max_slippage_bps=10.0,
            expected_holding_intervals=1,
            basis_absorption_max_ratio=0.50,
        ),
        SensitivityParamSet(
            annualized_threshold_pct=80.0,
            min_expected_funding_income_bps=50.0,
            max_slippage_bps=10.0,
            expected_holding_intervals=1,
            basis_absorption_max_ratio=0.50,
        ),
    ]

    candidate_summaries = run_candidate_sensitivity(rows, params)
    shadow_summaries = run_shadow_sensitivity(rows, candidate_summaries)

    assert (
        shadow_summaries[0]["shadow_trade_count"]
        == candidate_summaries[0]["research_shadow_admitted_count"]
    )

    assert (
        shadow_summaries[1]["shadow_trade_count"]
        == candidate_summaries[1]["research_shadow_admitted_count"]
    )


def test_shadow_trade_count_never_exceeds_research_shadow_count() -> None:
    rows = _rows_for_sensitivity()
    params = [
        SensitivityParamSet(
            annualized_threshold_pct=80.0,
            min_expected_funding_income_bps=50.0,
            max_slippage_bps=10.0,
            expected_holding_intervals=2,
            basis_absorption_max_ratio=0.70,
        )
    ]

    candidate_summaries = run_candidate_sensitivity(rows, params)
    shadow_summaries = run_shadow_sensitivity(rows, candidate_summaries)

    assert (
        shadow_summaries[0]["shadow_trade_count"]
        <= shadow_summaries[0]["research_shadow_admitted_count"]
    )


def test_anchor_only_summary_counts_anchor_rows_separately_from_path_rows() -> None:
    rows = _rows_for_sensitivity()
    param_set = SensitivityParamSet(
        annualized_threshold_pct=100.0,
        min_expected_funding_income_bps=50.0,
        max_slippage_bps=10.0,
        expected_holding_intervals=1,
        basis_absorption_max_ratio=0.50,
    )
    summary = run_candidate_sensitivity(rows, [param_set])[0]
    assert summary["anchor_event_count"] >= summary["research_shadow_admitted_count"]
    assert summary["research_shadow_admitted_count"] >= summary["trade_candidate_count"]


def test_research_shadow_count_can_exceed_trade_candidate_count() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.003,
            annualized_pct=150.0,
            spot_mid_price=100.0,
            perp_mid_price=100.08,
        ),
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=2000,
            funding_rate=0.003,
            annualized_pct=160.0,
            spot_mid_price=100.0,
            perp_mid_price=100.06,
        ),
    ]
    param_set = SensitivityParamSet(
        annualized_threshold_pct=100.0,
        min_expected_funding_income_bps=50.0,
        max_slippage_bps=10.0,
        expected_holding_intervals=1,
        basis_absorption_max_ratio=0.50,
    )
    summary = run_candidate_sensitivity(rows, [param_set])[0]
    assert summary["research_shadow_admitted_count"] > summary["trade_candidate_count"]
