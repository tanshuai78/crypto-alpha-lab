from src.strategies.extreme_funding.shadow_simulator import (
    ExtremeFundingShadowPosition,
    simulate_extreme_funding_shadow,
)


def _position(**overrides):
    position = {
        "symbol": "DOGE/USDT",
        "side": "long_spot_short_perp",
        "entry_time_ms": 1000,
        "entry_basis_bps": 10.0,
        "estimated_total_cost_bps": 26.0,
        "notional_usdt": 500.0,
        "max_holding_intervals": 3,
        "coverage_quality": "historical_basis_aware",
    }
    position.update(overrides)
    return ExtremeFundingShadowPosition(**position)


def test_shadow_simulator_counts_basis_narrowing_as_gain() -> None:
    result = simulate_extreme_funding_shadow(
        _position(),
        [{"funding_time_ms": 2000, "funding_rate": 0.008, "basis_bps": 5.0, "annualized_pct": 650.0}],
    )
    assert result.exit_reason == "path_exhausted"
    assert result.basis_change_bps == -5.0
    assert result.basis_loss_bps == 0.0
    assert result.net_pnl_bps == 59.0


def test_shadow_simulator_stops_on_basis_loss_halt() -> None:
    result = simulate_extreme_funding_shadow(
        _position(),
        [{"funding_time_ms": 2000, "funding_rate": 0.008, "basis_bps": 60.0, "annualized_pct": 650.0}],
    )
    assert result.exit_reason == "basis_loss_halt"
    assert result.basis_change_bps == 50.0
    assert result.basis_loss_bps == 50.0


def test_shadow_simulator_stops_on_funding_flip() -> None:
    result = simulate_extreme_funding_shadow(
        _position(),
        [{"funding_time_ms": 2000, "funding_rate": -0.0001, "basis_bps": 10.0, "annualized_pct": -10.0}],
    )
    assert result.exit_reason == "funding_flip"


def test_shadow_simulator_stops_on_funding_decay_after_counting_interval() -> None:
    result = simulate_extreme_funding_shadow(
        _position(),
        [{"funding_time_ms": 2000, "funding_rate": 0.0001, "basis_bps": 10.0, "annualized_pct": 10.0}],
    )
    assert result.exit_reason == "funding_decay"
    assert result.funding_income_bps == 1.0


def test_shadow_simulator_marks_funding_only_coverage_as_insufficient() -> None:
    result = simulate_extreme_funding_shadow(
        _position(entry_basis_bps=0.0, max_holding_intervals=1, coverage_quality="funding_only_insufficient_for_basis"),
        [{"funding_time_ms": 2000, "funding_rate": 0.008, "annualized_pct": 650.0}],
    )
    assert result.coverage_quality == "funding_only_insufficient_for_basis"
    assert result.notes == ["basis_path_missing"]
