from dataclasses import asdict

from src.research.external_signal_shadow.models import ShadowOrder

REQUIRED_BRANCHES = (
    "no_cusum_all_accepted_events",
    "cusum_confirmed_events",
)


def summarize_branch_orders(orders: list[ShadowOrder]) -> dict:
    total_net_return_bps = sum(
        order.net_return_bps or 0.0
        for order in orders
        if order.exit_reason != "data_unavailable"
    )
    return {
        "shadow_order_count": len(orders),
        "take_profit_count": sum(
            1 for order in orders if order.exit_reason == "take_profit"
        ),
        "stop_loss_count": sum(
            1 for order in orders if order.exit_reason == "stop_loss"
        ),
        "vertical_barrier_count": sum(
            1 for order in orders if order.exit_reason == "vertical_barrier"
        ),
        "data_unavailable_count": sum(
            1 for order in orders if order.exit_reason == "data_unavailable"
        ),
        "total_net_return_bps": total_net_return_bps,
        "shadow_orders": [asdict(order) for order in orders],
    }


def decide_stage0_shadow_replay(summary: dict) -> dict:
    failure_type = "stage0_completed"
    decision = "external_signal_shadow_stage0_passed"
    primary_blocker = None

    if summary.get("events_total", 0) <= 0 or summary.get("price_bars_total", 0) <= 0:
        failure_type = "data_failure"
        primary_blocker = "missing_events_or_price_bars"
    elif summary.get("events_accepted", 0) <= 0:
        failure_type = "risk_guard_density_failure"
        primary_blocker = "no_accepted_events"
    elif not _required_branches_exist(summary):
        failure_type = "shadow_order_structure_failure"
        primary_blocker = "missing_required_branches"
    elif not _has_any_shadow_order(summary):
        failure_type = "shadow_order_structure_failure"
        primary_blocker = "no_shadow_orders"
    elif not _branch_semantics_valid(summary):
        failure_type = "shadow_order_structure_failure"
        primary_blocker = "missing_branch_semantics"
    elif summary.get("alpha_interpretation_allowed") is not False:
        failure_type = "shadow_order_structure_failure"
        primary_blocker = "alpha_interpretation_not_disabled"
    elif summary.get("parameter_policy") != "fixed_stage0_sanity_check_not_optimized":
        failure_type = "shadow_order_structure_failure"
        primary_blocker = "missing_parameter_policy"
    elif any(
        summary.get(flag) is not False
        for flag in ("live_trading_enabled", "external_api_enabled", "wallet_required")
    ):
        failure_type = "shadow_order_structure_failure"
        primary_blocker = "unsafe_runtime_flag"

    if failure_type != "stage0_completed":
        decision = "external_signal_shadow_stage0_failed"

    return {
        **summary,
        "decision": decision,
        "primary_blocker": primary_blocker,
        "failure_type": failure_type,
        "live_safe": False,
        "paper_shadow_allowed": False,
        "cusum_vs_no_cusum": _cusum_vs_no_cusum(summary),
    }


def _required_branches_exist(summary: dict) -> bool:
    branches = summary.get("branches", {})
    return all(branch in branches for branch in REQUIRED_BRANCHES)


def _has_any_shadow_order(summary: dict) -> bool:
    branches = summary.get("branches", {})
    return any(
        branches.get(branch, {}).get("shadow_order_count", 0) > 0
        for branch in REQUIRED_BRANCHES
    )


def _branch_semantics_valid(summary: dict) -> bool:
    semantics = summary.get("branch_semantics", {})
    return (
        semantics.get("no_cusum_all_accepted_events")
        == "baseline_control_not_strategy"
        and semantics.get("cusum_confirmed_events")
        == "confirmation_filtered_shadow_not_strategy"
    )


def _cusum_vs_no_cusum(summary: dict) -> dict:
    branches = summary.get("branches", {})
    no_cusum = branches.get("no_cusum_all_accepted_events", {})
    cusum = branches.get("cusum_confirmed_events", {})
    return {
        "no_cusum_shadow_order_count": no_cusum.get("shadow_order_count", 0),
        "cusum_shadow_order_count": cusum.get("shadow_order_count", 0),
        "interpretation": "diagnostic_only_not_alpha",
    }
