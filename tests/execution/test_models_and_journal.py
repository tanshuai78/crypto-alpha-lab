from pathlib import Path

import pytest

from execution.execution_journal import ExecutionJournal
from execution.models import ExecutionLeg, TradeIntent
from execution.order_state_machine import IntentState, IntentStateMachine
from tests.execution.fixtures import (
    describe_bridge_contract,
    make_execution_leg_fixture,
    make_trade_intent_fixture,
)


def make_leg(
    exchange: str,
    symbol: str,
    side: str,
    client_order_id: str,
    *,
    order_type: str = "limit",
    price: float = 100.0,
    reduce_only: bool = False,
    post_only: bool = False,
    time_in_force: str = "GTC",
) -> ExecutionLeg:
    return ExecutionLeg(
        exchange=exchange,
        symbol=symbol,
        side=side,
        type=order_type,
        position_side="long" if side == "buy" else "short",
        client_order_id=client_order_id,
        time_in_force=time_in_force,
        reduce_only=reduce_only,
        post_only=post_only,
        price=price,
    )


def make_intent() -> TradeIntent:
    return TradeIntent(
        intent_id="intent-1",
        strategy_type="carry",
        leg_a=make_leg("okx", "BTC/USDT:USDT", "sell", "maker-1", post_only=True),
        leg_b=make_leg("binance", "BTC/USDT", "buy", "hedge-1", time_in_force="IOC"),
        target_base_qty=0.01,
        max_notional_usdt=1000.0,
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


def test_trade_intent_enforces_close_only_on_rollback():
    with pytest.raises(ValueError):
        TradeIntent(
            intent_id="intent-2",
            strategy_type="mr",
            leg_a=make_leg("okx", "ETH/USDT:USDT", "sell", "a"),
            leg_b=make_leg("binance", "ETH/USDT", "buy", "b"),
            target_base_qty=0.1,
            max_notional_usdt=500.0,
            execution_mode="maker_first",
            maker_leg_timeout_ms=1000,
            taker_ioc_timeout_ms=500,
            expected_edge_bps=10.0,
            min_fill_ratio_for_hedge=0.005,
            dust_notional_threshold=20.0,
            rollback_reserve_bps=5.0,
            close_only_on_rollback=False,
            abort_on_partial_fill=True,
        )


def test_state_machine_rejects_invalid_transition():
    machine = IntentStateMachine()
    assert machine.state == IntentState.CREATED
    machine.transition(IntentState.MAKER_SENT)
    with pytest.raises(ValueError):
        machine.transition(IntentState.HEDGED)


def test_execution_journal_persists_active_intents(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = make_intent()

    journal.record_intent(intent)
    journal.record_order(
        intent.intent_id,
        order_id="ord-1",
        leg_name="leg_a",
        exchange=intent.leg_a.exchange,
        symbol=intent.leg_a.symbol,
        side=intent.leg_a.side,
        order_type=intent.leg_a.type,
        client_order_id=intent.leg_a.client_order_id,
        status="open",
        reduce_only=False,
        post_only=True,
    )
    journal.transition_state(intent.intent_id, IntentState.MAKER_SENT, "maker placed")

    active = journal.list_active_intents()
    assert len(active) == 1
    assert active[0]["intent_id"] == intent.intent_id

    journal.transition_state(intent.intent_id, IntentState.CLOSED, "done")
    active = journal.list_active_intents()
    assert active == []


def test_execution_journal_can_fetch_existing_intent(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = make_intent()

    journal.record_intent(intent)
    stored = journal.get_intent(intent.intent_id)

    assert stored is not None
    assert stored["intent_id"] == intent.intent_id


def test_journal_records_state_transition_reasons_and_recovery_actions(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = make_intent()

    journal.record_intent(intent)
    journal.transition_state(intent.intent_id, IntentState.MAKER_SENT, "maker leg submitted")
    journal.transition_state(intent.intent_id, IntentState.UNKNOWN_REMOTE_STATE, "maker timeout")
    journal.record_recovery_action(intent.intent_id, "REMOTE_QUERY", "fetch by client order id")

    transitions = journal.list_state_transitions(intent.intent_id)
    recovery_actions = journal.list_recovery_actions(intent.intent_id)

    assert transitions[-1]["to_state"] == IntentState.UNKNOWN_REMOTE_STATE.value
    assert transitions[-1]["reason"] == "maker timeout"
    assert recovery_actions[0]["action"] == "REMOTE_QUERY"
    assert recovery_actions[0]["details"] == "fetch by client order id"


def test_active_intent_restart_snapshot_exposes_unknown_and_open_states(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = make_intent()

    journal.record_intent(intent)
    journal.transition_state(intent.intent_id, IntentState.UNKNOWN_REMOTE_STATE, "maker timeout")

    snapshot = journal.build_restart_snapshot()

    assert any(row["intent_id"] == intent.intent_id for row in snapshot["active_intents"])
    assert any(row["status"] == IntentState.UNKNOWN_REMOTE_STATE.value for row in snapshot["active_intents"])
    assert "generated_at" in snapshot


def test_trade_intent_fixture_exposes_required_v4_fields():
    intent = make_trade_intent_fixture()
    assert intent.intent_id
    assert intent.leg_a.exchange
    assert intent.leg_b.exchange
    assert intent.target_base_qty > 0
    assert intent.max_notional_usdt > 0
    assert intent.close_only_on_rollback is True


def test_execution_leg_fixture_keeps_side_and_price_contract():
    leg = make_execution_leg_fixture()
    assert leg.side in {"buy", "sell"}
    if leg.type == "limit":
        assert leg.price and leg.price > 0


def test_trade_intent_fixture_locks_qty_and_notional_units():
    intent = make_trade_intent_fixture()
    contract = describe_bridge_contract(intent)
    assert contract["qty_unit"] == "base"
    assert contract["notional_ccy"] == "USDT"


def test_trade_intent_fixture_exposes_stable_leg_roles_and_normalized_symbol():
    intent = make_trade_intent_fixture()
    contract = describe_bridge_contract(intent)
    assert contract["leg_roles"] == {"leg_a": "maker_leg", "leg_b": "hedge_leg"}
    assert contract["symbol_normalized"]
