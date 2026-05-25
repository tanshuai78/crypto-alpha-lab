from scripts.simulate_extreme_funding_basis_aware_shadow import (
    build_basis_aware_shadow_summary,
)
from src.research.extreme_funding_basis_replay import build_historical_basis_row


def test_basis_aware_shadow_summary_outputs_net_pnl_when_basis_path_exists() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=100.0,
            perp_mid_price=100.10,
            selected_price_time_ms=1000,
        ),
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=2000,
            funding_rate=0.007,
            annualized_pct=600.0,
            spot_mid_price=100.0,
            perp_mid_price=100.05,
            selected_price_time_ms=2000,
        ),
    ]

    summary = build_basis_aware_shadow_summary(rows)

    assert summary["shadow_trade_count"] == 1
    assert summary["coverage_quality"] == "historical_basis_proxy_not_depth_aware"
    assert "median_net_pnl_bps" in summary
    assert "win_rate" in summary


def test_basis_aware_shadow_summary_does_not_cross_symbols() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=100.0,
            perp_mid_price=100.10,
            selected_price_time_ms=1000,
        ),
        build_historical_basis_row(
            symbol="XRP/USDT",
            funding_time_ms=1500,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=1.0,
            perp_mid_price=1.2,
            selected_price_time_ms=1500,
        ),
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=2000,
            funding_rate=0.007,
            annualized_pct=600.0,
            spot_mid_price=100.0,
            perp_mid_price=100.05,
            selected_price_time_ms=2000,
        ),
    ]

    summary = build_basis_aware_shadow_summary(rows)

    assert summary["shadow_trade_count"] == 1
    assert summary["symbols"] == ["DOGE/USDT"]


def test_basis_aware_shadow_summary_marks_empty_basis_path() -> None:
    summary = build_basis_aware_shadow_summary([])

    assert summary["shadow_trade_count"] == 0
    assert summary["status"] == "insufficient_basis_path"
