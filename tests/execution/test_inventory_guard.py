from execution.inventory_guard import GuardStatus, InventoryGuard
from execution.models import ExecutionLeg, TradeIntent


def test_inventory_guard_thresholds():
    guard = InventoryGuard()

    healthy = guard.assess(spot_qty=1.0, spot_mark=100.0, perp_qty=0.99, perp_mark=100.0)
    assert healthy.status == GuardStatus.HEALTHY

    warning = guard.assess(spot_qty=1.0, spot_mark=100.0, perp_qty=0.93, perp_mark=100.0)
    assert warning.status == GuardStatus.WARNING

    paused = guard.assess(spot_qty=1.0, spot_mark=100.0, perp_qty=0.85, perp_mark=100.0)
    assert paused.status == GuardStatus.PAUSED

    force = guard.assess(spot_qty=1.0, spot_mark=100.0, perp_qty=0.75, perp_mark=100.0)
    assert force.status == GuardStatus.FORCE_DELEVERAGING


def test_inventory_guard_stays_in_recovery_until_explicit_clear():
    guard = InventoryGuard()

    guard.assess(spot_qty=1.0, spot_mark=100.0, perp_qty=0.75, perp_mark=100.0)
    recovery = guard.assess(
        spot_qty=1.0,
        spot_mark=100.0,
        perp_qty=1.0,
        perp_mark=100.0,
        orphan_intent_count=0,
        unknown_remote_count=0,
    )
    assert recovery.status == GuardStatus.RECOVERY

    cleared = guard.clear_recovery(
        inventory_ok_count=3,
        min_inventory_ok_count=3,
        orphan_intent_count=0,
        unknown_remote_count=0,
    )
    assert cleared is True
    final = guard.assess(spot_qty=1.0, spot_mark=100.0, perp_qty=1.0, perp_mark=100.0)
    assert final.status == GuardStatus.HEALTHY


def test_recovery_blocks_new_entries_but_allows_reduce_only_intents():
    guard = InventoryGuard()
    guard.assess(spot_qty=1.0, spot_mark=100.0, perp_qty=0.75, perp_mark=100.0)

    entry_intent = TradeIntent(
        intent_id="entry",
        strategy_type="carry",
        leg_a=ExecutionLeg("okx", "BTC/USDT:USDT", "sell", "limit", "short", "a", "GTC", False, True, 100.0),
        leg_b=ExecutionLeg("binance", "BTC/USDT", "buy", "limit", "long", "b", "IOC", False, False, 100.0),
        target_base_qty=1.0,
        max_notional_usdt=100.0,
        execution_mode="maker_first",
        maker_leg_timeout_ms=1000,
        taker_ioc_timeout_ms=500,
        expected_edge_bps=12.0,
        min_fill_ratio_for_hedge=0.005,
        dust_notional_threshold=20.0,
        rollback_reserve_bps=5.0,
        close_only_on_rollback=True,
        abort_on_partial_fill=True,
    )
    reduce_only_intent = TradeIntent(
        intent_id="exit",
        strategy_type="close",
        leg_a=ExecutionLeg("okx", "BTC/USDT:USDT", "buy", "market", "short", "ra", "IOC", True, False, None),
        leg_b=ExecutionLeg("binance", "BTC/USDT", "sell", "market", "long", "rb", "IOC", True, False, None),
        target_base_qty=1.0,
        max_notional_usdt=100.0,
        execution_mode="maker_first",
        maker_leg_timeout_ms=1000,
        taker_ioc_timeout_ms=500,
        expected_edge_bps=0.0,
        min_fill_ratio_for_hedge=0.005,
        dust_notional_threshold=20.0,
        rollback_reserve_bps=5.0,
        close_only_on_rollback=True,
        abort_on_partial_fill=True,
    )

    assert guard.allow_intent(entry_intent) is False
    assert guard.allow_intent(reduce_only_intent) is True


def test_recovery_cannot_clear_while_unknown_remote_state_remains():
    guard = InventoryGuard()
    guard.assess(spot_qty=1.0, spot_mark=100.0, perp_qty=0.75, perp_mark=100.0)

    cleared = guard.clear_recovery(
        inventory_ok_count=3,
        min_inventory_ok_count=3,
        orphan_intent_count=0,
        unknown_remote_count=1,
    )

    assert cleared is False
    recovery = guard.assess(
        spot_qty=1.0,
        spot_mark=100.0,
        perp_qty=1.0,
        perp_mark=100.0,
        orphan_intent_count=0,
        unknown_remote_count=1,
    )
    assert recovery.status == GuardStatus.RECOVERY
    assert "unresolved journal state" in recovery.reason
    assert guard.allow_intent(entry_intent := TradeIntent(
        intent_id="entry-unknown-remote",
        strategy_type="carry",
        leg_a=ExecutionLeg("okx", "BTC/USDT:USDT", "sell", "limit", "short", "a2", "GTC", False, True, 100.0),
        leg_b=ExecutionLeg("binance", "BTC/USDT", "buy", "limit", "long", "b2", "IOC", False, False, 100.0),
        target_base_qty=1.0,
        max_notional_usdt=100.0,
        execution_mode="maker_first",
        maker_leg_timeout_ms=1000,
        taker_ioc_timeout_ms=500,
        expected_edge_bps=12.0,
        min_fill_ratio_for_hedge=0.005,
        dust_notional_threshold=20.0,
        rollback_reserve_bps=5.0,
        close_only_on_rollback=True,
        abort_on_partial_fill=True,
    )) is False
