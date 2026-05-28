from __future__ import annotations

from typing import Any


def build_data_source_comparison(
    coverage_hours: float,
    *,
    route_b_available: bool = False,
    route_a_available: bool = True,
) -> dict[str, Any]:
    route_a = {
        "available": route_a_available,
        "source_quality": "self_collected_partial_history" if route_a_available else "not_connected",
        "coverage_hours": coverage_hours if route_a_available else 0.0,
        "liquidation_notional_semantics": "partial_snapshot_lower_bound",
        "allowed_decisions_if_only_route_a": ["continue_data_route_upgrade"],
    }

    route_b = {
        "available": route_b_available,
        "source_quality": "historical_vendor_dataset" if route_b_available else "not_connected",
        "coverage_hours": 0.0,  # Placeholder for Route B coverage
    }

    if route_a_available and route_b_available:
        route_c = {
            "available": True,
            "source_quality": "hybrid_reconstructed_history",
        }
    else:
        route_c = {
            "available": False,
            "reason": "requires_route_b_and_route_a",
        }

    return {
        "route_a_self_collected_forceorder_only": route_a,
        "route_b_third_party_historical_only": route_b,
        "route_c_hybrid_forceorder_plus_third_party": route_c,
    }


def build_route_decision_snapshot(comparison: dict[str, Any]) -> dict[str, Any]:
    route_a = comparison["route_a_self_collected_forceorder_only"]
    route_b = comparison["route_b_third_party_historical_only"]

    # Decision constraints
    # If only Route A is available and coverage is less than 720h, we cannot retire
    if route_a["available"] and not route_b["available"] and route_a["coverage_hours"] < 720.0:
        return {
            "allowed_decisions": ["continue_data_route_upgrade"],
            "forbidden_decisions": ["retire_liquidation_cascade_branch"],
        }

    return {
        "allowed_decisions": [
            "retain_for_phase1b_review",
            "continue_data_route_upgrade",
            "retire_liquidation_cascade_branch",
        ],
        "forbidden_decisions": [],
    }
