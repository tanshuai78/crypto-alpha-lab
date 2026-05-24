import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from execution.compat import build_legacy_entry_intent, build_legacy_entry_intent_adapter
from execution.execution_journal import ExecutionJournal
from execution.models import ExecutionLeg, TradeIntent
from execution.order_executor import OrderExecutor
from execution.order_state_machine import IntentState
from execution.preflight import PREFLIGHT_BLOCKER_PREFIXES, preflight_check


class FakeExchange:
    def __init__(self, *, supports_post_only=True, supports_reduce_only=True):
        self.supports_post_only = supports_post_only
        self.supports_reduce_only = supports_reduce_only
        self.orders = []
        self.create_order_result = None
        self.create_order_error = None
        self.fetch_order_result = None
        self.fetch_order_by_client_order_id_result = None
        self.cancel_order_result = {"status": "canceled"}
        self.cancel_order_error = None

    async def create_order(self, **kwargs):
        self.orders.append(kwargs)
        if self.create_order_error:
            raise self.create_order_error
        return self.create_order_result

    async def fetch_order(self, order_id, symbol):
        if isinstance(self.fetch_order_result, list):
            return self.fetch_order_result.pop(0)
        return self.fetch_order_result

    async def fetch_order_by_client_order_id(self, client_order_id, symbol):
        if isinstance(self.fetch_order_by_client_order_id_result, list):
            return self.fetch_order_by_client_order_id_result.pop(0)
        return self.fetch_order_by_client_order_id_result

    async def cancel_order(self, order_id, symbol):
        if self.cancel_order_error:
            raise self.cancel_order_error
        return self.cancel_order_result


def _count_rows(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0])


def make_intent() -> TradeIntent:
    leg_a = ExecutionLeg(
        exchange="okx",
        symbol="BTC/USDT:USDT",
        side="sell",
        type="limit",
        position_side="short",
        client_order_id="maker-1",
        time_in_force="GTC",
        reduce_only=False,
        post_only=True,
        price=100.0,
    )
    leg_b = ExecutionLeg(
        exchange="binance",
        symbol="BTC/USDT",
        side="buy",
        type="limit",
        position_side="long",
        client_order_id="hedge-1",
        time_in_force="IOC",
        reduce_only=False,
        post_only=False,
        price=100.0,
    )
    return TradeIntent(
        intent_id="intent-1",
        strategy_type="carry",
        leg_a=leg_a,
        leg_b=leg_b,
        target_base_qty=1.0,
        max_notional_usdt=100.0,
        execution_mode="maker_first",
        maker_leg_timeout_ms=50,
        taker_ioc_timeout_ms=50,
        expected_edge_bps=12.0,
        min_fill_ratio_for_hedge=0.005,
        dust_notional_threshold=20.0,
        rollback_reserve_bps=5.0,
        close_only_on_rollback=True,
        abort_on_partial_fill=True,
    )


def test_preflight_rejects_unsupported_post_only():
    intent = make_intent()
    exchanges = {
        "okx": FakeExchange(supports_post_only=False),
        "binance": FakeExchange(),
    }
    result = preflight_check(intent, exchanges)
    assert result.ok is False
    assert "post-only" in result.reason.lower()


def test_preflight_rejects_missing_exchange_with_taxonomy_and_diagnostics():
    intent = make_intent()
    result = preflight_check(intent, {"binance": FakeExchange()})

    assert result.ok is False
    assert result.blocker_code == "missing_dependency/exchange_client"
    assert result.diagnostics["exchange"] == "okx"
    assert result.blocker_code.split("/", 1)[0] in PREFLIGHT_BLOCKER_PREFIXES


def test_preflight_rejects_invalid_limit_price_with_taxonomy():
    invalid_leg = replace(make_intent().leg_a, price=0.0)
    intent = replace(make_intent(), leg_a=invalid_leg)
    result = preflight_check(intent, {"okx": FakeExchange(), "binance": FakeExchange()})

    assert result.ok is False
    assert result.blocker_code == "input_invalid/limit_price"
    assert result.diagnostics["client_order_id"] == "maker-1"
    assert result.blocker_code.split("/", 1)[0] in PREFLIGHT_BLOCKER_PREFIXES


def test_preflight_rejects_post_only_with_venue_capability_taxonomy():
    intent = make_intent()
    exchanges = {
        "okx": FakeExchange(supports_post_only=False),
        "binance": FakeExchange(),
    }

    result = preflight_check(intent, exchanges)

    assert result.ok is False
    assert result.blocker_code == "venue_capability/post_only_unsupported"
    assert result.diagnostics["exchange"] == "okx"
    assert result.diagnostics["client_order_id"] == "maker-1"
    assert result.blocker_code.split("/", 1)[0] in PREFLIGHT_BLOCKER_PREFIXES


@pytest.mark.asyncio
async def test_executor_rejects_unimplemented_execution_modes(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = replace(make_intent(), execution_mode="adaptive")
    executor = OrderExecutor(journal=journal)

    result = await executor.execute_intent(intent, {"okx": FakeExchange(), "binance": FakeExchange()})

    assert result.success is False
    assert result.state == IntentState.FAILED_SAFE
    assert "unsupported execution mode" in result.reason


@pytest.mark.asyncio
async def test_preflight_failure_has_no_side_effects(tmp_path: Path):
    db_path = tmp_path / "journal.db"
    journal = ExecutionJournal(db_path)
    intent = make_intent()
    exchanges = {"okx": FakeExchange(supports_post_only=False), "binance": FakeExchange()}

    executor = OrderExecutor(journal=journal)
    result = await executor.execute_intent(intent, exchanges)

    assert result.success is False
    assert journal.get_intent(intent.intent_id) is None
    assert exchanges["okx"].orders == []
    assert exchanges["binance"].orders == []
    assert _count_rows(db_path, "state_transitions") == 0
    assert _count_rows(db_path, "recovery_actions") == 0


@pytest.mark.asyncio
async def test_post_only_reject_does_not_downgrade_to_taker(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = make_intent()
    maker = FakeExchange()
    hedge = FakeExchange()
    maker.create_order_error = RuntimeError("post only order would be taker")

    executor = OrderExecutor(journal=journal)
    result = await executor.execute_intent(intent, {"okx": maker, "binance": hedge})

    assert result.success is False
    assert result.state == IntentState.FAILED_SAFE
    assert len(hedge.orders) == 0


@pytest.mark.asyncio
async def test_negative_net_edge_triggers_reduce_only_rollback(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = replace(make_intent(), expected_edge_bps=4.0, rollback_reserve_bps=5.0)

    maker = FakeExchange()
    hedge = FakeExchange()
    maker.create_order_result = {"id": "maker-order", "status": "open"}
    maker.fetch_order_result = {
        "id": "maker-order",
        "status": "closed",
        "filled": 1.0,
        "remaining": 0.0,
        "average": 100.0,
    }
    maker.cancel_order_result = {"status": "canceled"}
    maker.create_order_result = {"id": "maker-order", "status": "open"}

    executor = OrderExecutor(journal=journal)
    result = await executor.execute_intent(intent, {"okx": maker, "binance": hedge})

    assert result.success is False
    assert result.state == IntentState.FAILED_SAFE
    assert len(maker.orders) == 2
    rollback_order = maker.orders[-1]
    assert rollback_order["params"]["reduceOnly"] is True
    assert len(hedge.orders) == 0


@pytest.mark.asyncio
async def test_hedge_exception_triggers_reduce_only_rollback(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = replace(make_intent(), expected_edge_bps=20.0, rollback_reserve_bps=5.0)

    maker = FakeExchange()
    hedge = FakeExchange()
    maker.create_order_result = {"id": "maker-order", "status": "open"}
    maker.fetch_order_result = {
        "id": "maker-order",
        "status": "closed",
        "filled": 1.0,
        "remaining": 0.0,
        "average": 100.0,
    }
    hedge.create_order_error = RuntimeError("hedge create failed")

    executor = OrderExecutor(journal=journal)
    result = await executor.execute_intent(intent, {"okx": maker, "binance": hedge})

    assert result.success is False
    assert result.state == IntentState.FAILED_SAFE
    assert "hedge submission failed" in result.reason
    assert len(maker.orders) == 2
    rollback_order = maker.orders[-1]
    assert rollback_order["params"]["reduceOnly"] is True


@pytest.mark.asyncio
async def test_duplicate_intent_id_is_rejected_without_replay(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = make_intent()

    maker = FakeExchange()
    hedge = FakeExchange()
    maker.create_order_result = {"id": "maker-order", "status": "closed", "filled": 1.0, "average": 100.0}
    hedge.create_order_result = {"id": "hedge-order", "status": "closed", "filled": 1.0, "average": 100.0}

    executor = OrderExecutor(journal=journal)
    first = await executor.execute_intent(intent, {"okx": maker, "binance": hedge})
    second = await executor.execute_intent(intent, {"okx": maker, "binance": hedge})

    assert first.success is True
    assert second.success is False
    assert "duplicate intent_id" in second.reason
    assert len(maker.orders) == 1
    assert len(hedge.orders) == 1


@pytest.mark.asyncio
async def test_timeout_queries_remote_state_and_hedges(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = replace(make_intent(), expected_edge_bps=20.0)

    maker = FakeExchange()
    hedge = FakeExchange()
    maker.create_order_error = TimeoutError("request timed out")
    maker.fetch_order_by_client_order_id_result = {
        "id": "maker-timeout",
        "status": "closed",
        "filled": 1.0,
        "remaining": 0.0,
        "average": 99.9,
    }
    hedge.create_order_result = {
        "id": "hedge-order",
        "status": "closed",
        "filled": 1.0,
        "remaining": 0.0,
        "average": 100.0,
    }

    executor = OrderExecutor(journal=journal)
    result = await executor.execute_intent(intent, {"okx": maker, "binance": hedge})

    assert result.success is True
    assert result.state == IntentState.CLOSED
    assert len(hedge.orders) == 1


@pytest.mark.asyncio
async def test_abort_on_partial_fill_does_not_mark_intent_success(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = replace(make_intent(), expected_edge_bps=20.0, abort_on_partial_fill=True)

    maker = FakeExchange()
    hedge = FakeExchange()
    maker.create_order_result = {"id": "maker-order", "status": "open"}
    maker.fetch_order_result = {
        "id": "maker-order",
        "status": "closed",
        "filled": 1.0,
        "remaining": 0.0,
        "average": 100.0,
    }
    hedge.create_order_result = {
        "id": "hedge-order",
        "status": "closed",
        "filled": 0.3,
        "remaining": 0.7,
        "average": 100.0,
    }

    executor = OrderExecutor(journal=journal)
    result = await executor.execute_intent(intent, {"okx": maker, "binance": hedge})

    assert result.success is False
    assert result.state == IntentState.FAILED_SAFE
    assert "partial fill" in result.reason


@pytest.mark.asyncio
async def test_unknown_remote_state_escalates_after_retry_budget(tmp_path: Path):
    journal = ExecutionJournal(tmp_path / "journal.db")
    intent = make_intent()
    maker = FakeExchange()
    hedge = FakeExchange()
    maker.create_order_error = TimeoutError("request timed out")
    maker.fetch_order_by_client_order_id_result = [None, None, None, None]

    async def no_sleep(_delay):
        return None

    executor = OrderExecutor(
        journal=journal,
        sleep_fn=no_sleep,
        unknown_remote_retry_delays=(0, 0, 0),
        unknown_remote_max_age_sec=0,
    )
    result = await executor.execute_intent(intent, {"okx": maker, "binance": hedge})

    assert result.success is False
    assert result.state == IntentState.FAILED_SAFE
    assert "remote confirmation" in result.reason
    assert hedge.orders == []


def test_legacy_adapter_builds_explicit_trade_intent():
    intent = build_legacy_entry_intent(
        symbol="BTC/USDT",
        spot_exchange="binance",
        perp_exchange="okx",
        amount_usdt=1000.0,
        spot_price=50000.0,
        perp_price=50050.0,
        strategy_type="carry",
        intent_id="legacy-1",
    )

    assert intent.leg_a.post_only is True
    assert intent.leg_b.time_in_force == "IOC"
    assert intent.close_only_on_rollback is True


def test_legacy_adapter_report_keeps_bridge_diagnostics_outside_trade_intent():
    adapter = build_legacy_entry_intent_adapter(
        symbol="BTC/USDT",
        spot_exchange="binance",
        perp_exchange="okx",
        amount_usdt=1000.0,
        spot_price=50000.0,
        perp_price=50050.0,
        strategy_type="carry",
        intent_id="legacy-bridge-1",
    )

    assert adapter.ok is True
    assert adapter.intent is not None
    assert adapter.bridge_report["qty_unit"] == "base"
    assert adapter.bridge_report["notional_ccy"] == "USDT"
    assert adapter.bridge_report["leg_roles"] == {"leg_a": "maker_leg", "leg_b": "hedge_leg"}
    assert adapter.bridge_report["symbol_normalized"] == "BTC/USDT"
    assert not hasattr(adapter.intent, "bridge_report")
    assert not hasattr(adapter.intent, "adapter_diagnostics")


def test_legacy_adapter_returns_blocker_and_diagnostics_on_invalid_price():
    adapter = build_legacy_entry_intent_adapter(
        symbol="BTC/USDT",
        spot_exchange="binance",
        perp_exchange="okx",
        amount_usdt=1000.0,
        spot_price=0.0,
        perp_price=50050.0,
        strategy_type="carry",
        intent_id="legacy-bridge-invalid-price",
    )

    assert adapter.ok is False
    assert adapter.intent is None
    assert adapter.blocker_code == "input_invalid/spot_price"
    assert adapter.diagnostics["field"] == "spot_price"
    assert adapter.bridge_report == {}
