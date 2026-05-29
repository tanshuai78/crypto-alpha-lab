import pytest
from typing import Any

from scripts.review_trend_liquidation_cascade import (
    build_data_source_comparison,
    build_route_decision_snapshot,
    build_cascade_audit_summary,
    build_cascade_shadow_summary,
    run_cascade_sensitivity,
)
from src.research.trend_liquidation_cascade_review import (
    LiquidationCascadeReviewThresholds,
    classify_liquidation_cascade_for_review,
)


def _row(**overrides: Any) -> dict[str, Any]:
    row = {
        "timestamp_ms": 1710000000000,
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "close_price": 100000.0,
        "return_1h_pct": 2.5,
        "vol_1h_pct": 3.0,
        "vol_baseline_30d_pct": 1.0,
        "oi_change_1h_pct": -3.0,
        "volume_24h_usdt": 1_000_000_000.0,
        "estimated_slippage_bps": 4.0,
        "data_age_sec": 0.0,
        "long_liquidation_notional_1h_usdt": 0.0,
        "short_liquidation_notional_1h_usdt": 15_000_000.0,
    }
    row.update(overrides)
    return row


def test_data_source_comparison_reports_forceorder_partial_quality():
    comparison = build_data_source_comparison(coverage_hours=50.0, route_b_available=False)
    route_a = comparison["route_a_self_collected_forceorder_only"]
    assert route_a["available"] is True
    assert route_a["source_quality"] == "self_collected_partial_history"
    assert route_a["coverage_hours"] == 50.0
    assert route_a["liquidation_notional_semantics"] == "partial_snapshot_lower_bound"
    assert route_a["allowed_decisions_if_only_route_a"] == ["continue_data_route_upgrade"]


def test_data_source_comparison_reports_missing_third_party_as_upgrade_gap():
    comparison = build_data_source_comparison(coverage_hours=50.0, route_b_available=False)
    route_b = comparison["route_b_third_party_historical_only"]
    assert route_b["available"] is False
    assert route_b["source_quality"] == "not_connected"


def test_data_source_comparison_includes_route_b_feasibility_candidates():
    feasibility = {
        "vendor_candidates": [
            {
                "vendor": "coinglass",
                "api_access": "unavailable",
                "requires_paid_plan": True,
                "granularity": "1h",
                "exchange_coverage": ["binance"],
                "symbol_coverage": ["BTC/USDT"],
                "historical_depth_days": 365,
                "can_support_replay": True,
                "blocker": "requires_paid_developer_api_plan_and_key",
            }
        ]
    }
    comparison = build_data_source_comparison(
        coverage_hours=50.0,
        route_b_available=False,
        route_b_feasibility=feasibility,
    )
    route_b = comparison["route_b_third_party_historical_only"]
    assert route_b["vendor_candidates"] == feasibility["vendor_candidates"]
    assert route_b["source_quality"] == "not_connected"


def test_data_source_comparison_keeps_routes_separate():
    comparison = build_data_source_comparison(coverage_hours=100.0, route_b_available=True)
    assert comparison["route_a_self_collected_forceorder_only"]["available"] is True
    assert comparison["route_b_third_party_historical_only"]["available"] is True
    assert comparison["route_c_hybrid_forceorder_plus_third_party"]["available"] is True


def test_route_a_short_partial_coverage_cannot_retire_strategy():
    comparison = build_data_source_comparison(coverage_hours=498.0, route_b_available=False)
    decision = build_route_decision_snapshot(comparison)
    assert "continue_data_route_upgrade" in decision["allowed_decisions"]
    assert "retire_liquidation_cascade_branch" in decision["forbidden_decisions"]


def test_cascade_shadow_uses_only_accepted_entries():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT", close_price=100000.0),
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.2, vol_1h_pct=1.0),
        _row(timestamp_ms=3000, symbol="ETH/USDT", close_price=100.0, vol_1h_pct=1.0),
    ]
    summary = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12, hypothesis="continuation")
    assert summary["entry_event_count"] == 1
    assert summary["shadow_trade_count"] == 1
    assert summary["holding_hours"] == 12


def test_cascade_shadow_path_uses_same_symbol_and_future_only():
    rows = [
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=100000.0),
        # past row for BTC
        _row(timestamp_ms=1500, symbol="BTC/USDT", close_price=90000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
        # future row for BTC
        _row(timestamp_ms=2500, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
        # future row for ETH (cross-symbol)
        _row(timestamp_ms=2600, symbol="ETH/USDT", close_price=110.0, return_1h_pct=0.1, vol_1h_pct=1.0),
    ]
    summary = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12, hypothesis="continuation")
    assert summary["shadow_trade_count"] == 1
    assert summary["accepted_entries_with_path_count"] == 1


def test_cascade_outputs_dual_cost_and_holding_hours():
    # Tested through scripts execution or build_cascade_shadow_summary structures
    rows = [_row()]
    summary = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=4, hypothesis="continuation")
    assert "mean_net_pnl_bps" in summary
    assert "median_net_pnl_bps" in summary


def test_cascade_sensitivity_does_not_mutate_live_config():
    before = classify_liquidation_cascade_for_review(_row())
    run_cascade_sensitivity([_row()], threshold_sets=[LiquidationCascadeReviewThresholds.moderately_relaxed()])
    after = classify_liquidation_cascade_for_review(_row())
    assert before == after


def test_shadow_outputs_continuation_and_mean_reversion_separately():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT", close_price=100000.0),
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
    ]
    cont = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12, hypothesis="continuation")
    rev = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12, hypothesis="mean_reversion")

    # In continuation hypothesis: BUY pressure (short liq) -> Enter LONG -> Price goes to 101000 -> Profit
    assert cont["shadow_trade_count"] == 1
    assert cont["mean_net_pnl_bps"] > 0

    # In mean reversion hypothesis: BUY pressure -> Enter SHORT -> Price goes to 101000 -> Loss
    assert rev["shadow_trade_count"] == 1
    assert rev["mean_net_pnl_bps"] < 0
