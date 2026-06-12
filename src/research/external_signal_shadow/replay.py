from dataclasses import asdict

from configs import base
from src.research.external_signal_shadow.cusum import confirm_event_with_cusum
from src.research.external_signal_shadow.models import (
    ExternalSignalEvent,
    PriceBar,
    ShadowOrder,
    price_bars_by_symbol,
)
from src.research.external_signal_shadow.risk_guard import evaluate_event_risk
from src.research.external_signal_shadow.triple_barrier import (
    build_shadow_order_with_triple_barrier,
)


def _direction_from_decision(direction: str) -> str | None:
    if direction in {"long", "short"}:
        return direction
    return None


def _build_order(
    event: ExternalSignalEvent,
    trigger_time_ms: int,
    bars: list[PriceBar],
    direction: str,
) -> ShadowOrder:
    return build_shadow_order_with_triple_barrier(
        event,
        trigger_time_ms,
        bars,
        direction=direction,
        take_profit_bps=base.EXTERNAL_SIGNAL_SHADOW_TAKE_PROFIT_BPS,
        stop_loss_bps=base.EXTERNAL_SIGNAL_SHADOW_STOP_LOSS_BPS,
        max_holding_minutes=base.EXTERNAL_SIGNAL_SHADOW_MAX_HOLDING_MINUTES,
        entry_delay_bars=base.EXTERNAL_SIGNAL_SHADOW_ENTRY_DELAY_BARS,
        cost_round_trip_bps=base.EXTERNAL_SIGNAL_SHADOW_COST_ROUND_TRIP_BPS,
    )


def _branch_summary(orders: list[ShadowOrder]) -> dict:
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
        "shadow_orders": [asdict(order) for order in orders],
    }


def run_stage0_shadow_replay(
    events: list[ExternalSignalEvent],
    bars: list[PriceBar],
) -> dict:
    grouped_bars = price_bars_by_symbol(bars)
    accepted_events: list[tuple[ExternalSignalEvent, str]] = []
    rejected = 0
    quarantined = 0

    for event in events:
        decision = evaluate_event_risk(event)
        if decision.risk_decision == "reject":
            rejected += 1
            continue
        if decision.risk_decision == "quarantine":
            quarantined += 1
            continue
        direction = _direction_from_decision(decision.allowed_shadow_direction)
        accepted_events.append((event, direction or "observe_only"))

    no_cusum_orders: list[ShadowOrder] = []
    cusum_orders: list[ShadowOrder] = []
    cusum_no_confirm_count = 0
    cusum_adverse_confirm_count = 0
    cusum_observe_only_count = 0

    for event, direction in accepted_events:
        symbol_bars = grouped_bars.get(event.symbol or "", [])
        if direction in {"long", "short"}:
            no_cusum_orders.append(
                _build_order(event, event.event_time_ms, symbol_bars, direction)
            )

        cusum_result = confirm_event_with_cusum(
            event,
            symbol_bars,
            fixed_threshold_bps=base.EXTERNAL_SIGNAL_SHADOW_CUSUM_FIXED_THRESHOLD_BPS,
            vol_multiplier=base.EXTERNAL_SIGNAL_SHADOW_CUSUM_VOL_MULTIPLIER,
            confirmation_window_min=base.EXTERNAL_SIGNAL_SHADOW_CUSUM_CONFIRMATION_WINDOW_MIN,
        )
        if cusum_result.status == "confirmed" and cusum_result.trigger_time_ms:
            cusum_orders.append(
                _build_order(
                    event,
                    cusum_result.trigger_time_ms,
                    symbol_bars,
                    cusum_result.direction or direction,
                )
            )
        elif cusum_result.status == "no_confirm":
            cusum_no_confirm_count += 1
        elif cusum_result.status == "adverse_confirm":
            cusum_adverse_confirm_count += 1
        elif cusum_result.status == "observe_only":
            cusum_observe_only_count += 1

    summary = {
        "mode": "fixture_only_stage0",
        "live_trading_enabled": False,
        "external_api_enabled": False,
        "wallet_required": False,
        "events_total": len(events),
        "price_bars_total": len(bars),
        "events_accepted": len(accepted_events),
        "events_rejected": rejected,
        "events_quarantined": quarantined,
        "cusum_no_confirm_count": cusum_no_confirm_count,
        "cusum_adverse_confirm_count": cusum_adverse_confirm_count,
        "cusum_observe_only_count": cusum_observe_only_count,
        "branches": {
            "no_cusum_all_accepted_events": _branch_summary(no_cusum_orders),
            "cusum_confirmed_events": _branch_summary(cusum_orders),
        },
        "branch_semantics": {
            "no_cusum_all_accepted_events": "baseline_control_not_strategy",
            "cusum_confirmed_events": "confirmation_filtered_shadow_not_strategy",
        },
        "parameter_policy": "fixed_stage0_sanity_check_not_optimized",
        "alpha_interpretation_allowed": False,
        "decision": "external_signal_shadow_stage0_passed",
        "primary_blocker": None,
    }
    if not events:
        summary["decision"] = "external_signal_shadow_stage0_failed"
        summary["primary_blocker"] = "no_events"
    elif not bars:
        summary["decision"] = "external_signal_shadow_stage0_failed"
        summary["primary_blocker"] = "no_price_bars"
    return summary
