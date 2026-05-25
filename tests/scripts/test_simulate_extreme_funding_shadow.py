from scripts.simulate_extreme_funding_shadow import build_shadow_replay_summary


def test_shadow_replay_summary_uses_funding_minus_cost_names_for_funding_only() -> None:
    segments = [
        {
            "symbol": "DOGE/USDT",
            "start_ms": 1000,
            "row_count": 1,
            "funding_income_bps": 80.0,
            "coverage_quality": "funding_only_insufficient_for_basis",
        }
    ]
    summary = build_shadow_replay_summary(segments)
    assert summary["shadow_trade_count"] == 1
    assert summary["median_funding_minus_cost_bps"] == 54.0
    assert summary["positive_funding_minus_cost_rate"] == 1.0
    assert "median_net_pnl_bps" not in summary
    assert "win_rate" not in summary
    assert summary["coverage_quality"] == "funding_only_insufficient_for_basis"
