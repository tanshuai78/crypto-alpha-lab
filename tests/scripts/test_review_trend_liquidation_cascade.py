from typing import Any
import pytest

from scripts.review_trend_liquidation_cascade import (
    build_data_source_comparison,
    build_route_decision_snapshot,
)


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


def test_data_source_comparison_keeps_routes_separate():
    comparison = build_data_source_comparison(coverage_hours=100.0, route_b_available=True)
    assert comparison["route_a_self_collected_forceorder_only"]["available"] is True
    assert comparison["route_b_third_party_historical_only"]["available"] is True
    # Hybrid is now possible if both are active
    assert comparison["route_c_hybrid_forceorder_plus_third_party"]["available"] is True


def test_route_a_short_partial_coverage_cannot_retire_strategy():
    comparison = build_data_source_comparison(coverage_hours=498.0, route_b_available=False)
    decision = build_route_decision_snapshot(comparison)
    assert "continue_data_route_upgrade" in decision["allowed_decisions"]
    assert "retire_liquidation_cascade_branch" in decision["forbidden_decisions"]
