from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import ExecutionLeg, TradeIntent


@dataclass(frozen=True)
class LegacyEntryIntentAdapterResult:
    ok: bool
    intent: TradeIntent | None = None
    blocker_code: str = ""
    diagnostics: dict[str, Any] | None = None
    bridge_report: dict[str, Any] | None = None


def build_legacy_entry_intent(
    *,
    symbol: str,
    spot_exchange: str,
    perp_exchange: str,
    amount_usdt: float,
    spot_price: float,
    perp_price: float,
    strategy_type: str,
    intent_id: str,
    maker_leg_timeout_ms: int = 5000,
    taker_ioc_timeout_ms: int = 500,
    expected_edge_bps: float = 10.0,
    rollback_reserve_bps: float = 5.0,
    min_fill_ratio_for_hedge: float = 0.005,
    dust_notional_threshold: float = 20.0,
) -> TradeIntent:
    target_base_qty = amount_usdt / max(perp_price, 1e-9)
    leg_a = ExecutionLeg(
        exchange=perp_exchange,
        symbol=symbol,
        side="sell",
        type="limit",
        position_side="short",
        client_order_id=f"{intent_id}-maker",
        time_in_force="GTC",
        reduce_only=False,
        post_only=True,
        price=perp_price,
    )
    leg_b = ExecutionLeg(
        exchange=spot_exchange,
        symbol=symbol,
        side="buy",
        type="limit",
        position_side="long",
        client_order_id=f"{intent_id}-hedge",
        time_in_force="IOC",
        reduce_only=False,
        post_only=False,
        price=spot_price,
    )
    return TradeIntent(
        intent_id=intent_id,
        strategy_type=strategy_type,
        leg_a=leg_a,
        leg_b=leg_b,
        target_base_qty=target_base_qty,
        max_notional_usdt=amount_usdt,
        execution_mode="maker_first",
        maker_leg_timeout_ms=maker_leg_timeout_ms,
        taker_ioc_timeout_ms=taker_ioc_timeout_ms,
        expected_edge_bps=expected_edge_bps,
        min_fill_ratio_for_hedge=min_fill_ratio_for_hedge,
        dust_notional_threshold=dust_notional_threshold,
        rollback_reserve_bps=rollback_reserve_bps,
        close_only_on_rollback=True,
        abort_on_partial_fill=True,
    )


def build_legacy_entry_intent_adapter(
    *,
    symbol: str,
    spot_exchange: str,
    perp_exchange: str,
    amount_usdt: float,
    spot_price: float,
    perp_price: float,
    strategy_type: str,
    intent_id: str,
    maker_leg_timeout_ms: int = 5000,
    taker_ioc_timeout_ms: int = 500,
    expected_edge_bps: float = 10.0,
    rollback_reserve_bps: float = 5.0,
    min_fill_ratio_for_hedge: float = 0.005,
    dust_notional_threshold: float = 20.0,
) -> LegacyEntryIntentAdapterResult:
    if amount_usdt <= 0:
        return LegacyEntryIntentAdapterResult(
            ok=False,
            blocker_code="input_invalid/amount_usdt",
            diagnostics={"field": "amount_usdt", "value": amount_usdt},
            bridge_report={},
        )
    if spot_price <= 0:
        return LegacyEntryIntentAdapterResult(
            ok=False,
            blocker_code="input_invalid/spot_price",
            diagnostics={"field": "spot_price", "value": spot_price},
            bridge_report={},
        )
    if perp_price <= 0:
        return LegacyEntryIntentAdapterResult(
            ok=False,
            blocker_code="input_invalid/perp_price",
            diagnostics={"field": "perp_price", "value": perp_price},
            bridge_report={},
        )

    intent = build_legacy_entry_intent(
        symbol=symbol,
        spot_exchange=spot_exchange,
        perp_exchange=perp_exchange,
        amount_usdt=amount_usdt,
        spot_price=spot_price,
        perp_price=perp_price,
        strategy_type=strategy_type,
        intent_id=intent_id,
        maker_leg_timeout_ms=maker_leg_timeout_ms,
        taker_ioc_timeout_ms=taker_ioc_timeout_ms,
        expected_edge_bps=expected_edge_bps,
        rollback_reserve_bps=rollback_reserve_bps,
        min_fill_ratio_for_hedge=min_fill_ratio_for_hedge,
        dust_notional_threshold=dust_notional_threshold,
    )
    bridge_report = {
        "symbol_normalized": symbol,
        "leg_roles": {"leg_a": "maker_leg", "leg_b": "hedge_leg"},
        "qty_unit": "base",
        "notional_ccy": "USDT",
        "spot_exchange": spot_exchange,
        "perp_exchange": perp_exchange,
    }
    return LegacyEntryIntentAdapterResult(
        ok=True,
        intent=intent,
        diagnostics={},
        bridge_report=bridge_report,
    )
