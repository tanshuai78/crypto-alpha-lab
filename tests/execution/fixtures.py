from __future__ import annotations

from execution.models import ExecutionLeg, TradeIntent


def make_execution_leg_fixture(
    *,
    exchange: str = "okx",
    symbol: str = "BTC/USDT:USDT",
    side: str = "sell",
    order_type: str = "limit",
    price: float = 50000.0,
    client_order_id: str = "intent-fixture-maker",
    position_side: str = "short",
    time_in_force: str = "GTC",
    reduce_only: bool = False,
    post_only: bool = True,
) -> ExecutionLeg:
    return ExecutionLeg(
        exchange=exchange,
        symbol=symbol,
        side=side,
        type=order_type,
        position_side=position_side,
        client_order_id=client_order_id,
        time_in_force=time_in_force,
        reduce_only=reduce_only,
        post_only=post_only,
        price=price,
    )


def make_trade_intent_fixture() -> TradeIntent:
    return TradeIntent(
        intent_id="intent-fixture-1",
        strategy_type="carry",
        leg_a=make_execution_leg_fixture(),
        leg_b=make_execution_leg_fixture(
            exchange="binance",
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            price=49950.0,
            client_order_id="intent-fixture-hedge",
            position_side="long",
            time_in_force="IOC",
            post_only=False,
        ),
        target_base_qty=0.02,
        max_notional_usdt=1000.0,
        execution_mode="maker_first",
        maker_leg_timeout_ms=5000,
        taker_ioc_timeout_ms=500,
        expected_edge_bps=12.0,
        min_fill_ratio_for_hedge=0.005,
        dust_notional_threshold=20.0,
        rollback_reserve_bps=5.0,
        close_only_on_rollback=True,
        abort_on_partial_fill=True,
    )


def _normalize_symbol(symbol: str) -> str:
    return symbol.replace(":USDT", "")


def describe_bridge_contract(intent: TradeIntent) -> dict:
    normalized_leg_a = _normalize_symbol(intent.leg_a.symbol)
    normalized_leg_b = _normalize_symbol(intent.leg_b.symbol)
    if normalized_leg_a != normalized_leg_b:
        raise ValueError("Bridge fixture expects both legs to share one normalized symbol")

    return {
        "symbol_normalized": normalized_leg_a,
        "leg_roles": {"leg_a": "maker_leg", "leg_b": "hedge_leg"},
        "qty_unit": "base",
        "notional_ccy": "USDT",
    }
