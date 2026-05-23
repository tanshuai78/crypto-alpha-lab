from __future__ import annotations

from dataclasses import replace
import asyncio
import time
from typing import Any

from loguru import logger

try:
    from configs.base import (
        EXECUTION_DUST_FILL_RATIO,
        EXECUTION_DUST_NOTIONAL_THRESHOLD_USDT,
        EXECUTION_JOURNAL_PATH,
        EXECUTION_UNKNOWN_REMOTE_MAX_AGE_SEC,
        EXECUTION_UNKNOWN_REMOTE_RETRY_DELAYS_SEC,
    )
except ModuleNotFoundError:
    from configs.base import (  # type: ignore[no-redef]
        EXECUTION_DUST_FILL_RATIO,
        EXECUTION_DUST_NOTIONAL_THRESHOLD_USDT,
        EXECUTION_JOURNAL_PATH,
        EXECUTION_UNKNOWN_REMOTE_MAX_AGE_SEC,
        EXECUTION_UNKNOWN_REMOTE_RETRY_DELAYS_SEC,
    )

from .execution_journal import ExecutionJournal
from .models import ExecutionLeg, ExecutionOutcome, TradeIntent
from .order_state_machine import IntentState, IntentStateMachine
from .preflight import preflight_check


class OrderExecutor:
    def __init__(
        self,
        journal: ExecutionJournal | None = None,
        sleep_fn=asyncio.sleep,
        unknown_remote_retry_delays: tuple[float, ...] = EXECUTION_UNKNOWN_REMOTE_RETRY_DELAYS_SEC,
        unknown_remote_max_age_sec: float = EXECUTION_UNKNOWN_REMOTE_MAX_AGE_SEC,
    ):
        self.journal = journal or ExecutionJournal(EXECUTION_JOURNAL_PATH)
        self.sleep_fn = sleep_fn
        self.unknown_remote_retry_delays = tuple(unknown_remote_retry_delays)
        self.unknown_remote_max_age_sec = unknown_remote_max_age_sec

    async def execute_intent(self, intent: TradeIntent, exchanges: dict[str, Any]) -> ExecutionOutcome:
        preflight = preflight_check(intent, exchanges)
        if not preflight.ok:
            return ExecutionOutcome(False, IntentState.FAILED_SAFE, preflight.reason, intent.intent_id)

        existing = self.journal.get_intent(intent.intent_id)
        if existing is not None:
            return ExecutionOutcome(False, IntentState.FAILED_SAFE, "duplicate intent_id", intent.intent_id)

        self.journal.record_intent(intent)
        machine = IntentStateMachine()

        if intent.execution_mode != "maker_first":
            reason = f"unsupported execution mode: {intent.execution_mode}"
            self.journal.transition_state(intent.intent_id, IntentState.FAILED_SAFE, reason)
            return ExecutionOutcome(False, IntentState.FAILED_SAFE, reason, intent.intent_id)

        try:
            return await self._execute_maker_first(intent, exchanges, machine)
        except Exception as exc:
            logger.exception("Execution failure")
            self.journal.transition_state(intent.intent_id, IntentState.FAILED_SAFE, str(exc))
            return ExecutionOutcome(False, IntentState.FAILED_SAFE, str(exc), intent.intent_id)

    async def _execute_maker_first(
        self,
        intent: TradeIntent,
        exchanges: dict[str, Any],
        machine: IntentStateMachine,
    ) -> ExecutionOutcome:
        maker_exchange = exchanges[intent.leg_a.exchange]
        hedge_exchange = exchanges[intent.leg_b.exchange]

        maker_order = await self._submit_primary_leg(intent, maker_exchange, machine)
        if maker_order is None:
            reason = "maker timeout with no remote confirmation"
            if machine.state == IntentState.UNKNOWN_REMOTE_STATE:
                machine.transition(IntentState.FAILED_SAFE)
            return ExecutionOutcome(False, IntentState.FAILED_SAFE, reason, intent.intent_id)

        filled_qty = float(maker_order.get("filled", 0.0) or 0.0)
        avg_price = float(maker_order.get("average") or intent.leg_a.price or 0.0)
        order_id = maker_order.get("id")

        if filled_qty <= 0:
            self.journal.transition_state(intent.intent_id, IntentState.CLOSED, "maker leg closed without fill")
            return ExecutionOutcome(False, IntentState.CLOSED, "maker leg not filled", intent.intent_id)

        self.journal.record_fill(intent.intent_id, order_id, filled_qty, avg_price, maker_order)

        net_edge = self._compute_net_edge_after_friction_bps(intent, avg_price, intent.leg_a.price or avg_price)
        if net_edge <= 0:
            await self._rollback_leg(intent, maker_exchange, intent.leg_a, filled_qty)
            machine.transition(IntentState.ROLLBACK_SENT)
            self.journal.transition_state(intent.intent_id, IntentState.ROLLBACK_SENT, "net edge after friction <= 0")
            machine.transition(IntentState.FAILED_SAFE)
            self.journal.transition_state(intent.intent_id, IntentState.FAILED_SAFE, "rollback completed after net edge breach")
            return ExecutionOutcome(
                False,
                IntentState.FAILED_SAFE,
                "net edge after friction <= 0",
                intent.intent_id,
                filled_qty_leg_a=filled_qty,
                net_edge_after_friction_bps=net_edge,
            )

        try:
            hedge_order = await self._submit_leg(
                hedge_exchange, intent.intent_id, "leg_b", intent.leg_b, filled_qty
            )
        except Exception as exc:
            await self._rollback_leg(intent, maker_exchange, intent.leg_a, filled_qty)
            machine.transition(IntentState.ROLLBACK_SENT)
            self.journal.transition_state(intent.intent_id, IntentState.ROLLBACK_SENT, "hedge submit exception forced rollback")
            machine.transition(IntentState.FAILED_SAFE)
            reason = f"hedge submission failed: {exc}"
            self.journal.transition_state(intent.intent_id, IntentState.FAILED_SAFE, reason)
            return ExecutionOutcome(
                False,
                IntentState.FAILED_SAFE,
                reason,
                intent.intent_id,
                filled_qty_leg_a=filled_qty,
                net_edge_after_friction_bps=net_edge,
            )
        machine.transition(IntentState.HEDGE_SENT)
        self.journal.transition_state(intent.intent_id, IntentState.HEDGE_SENT, "hedge leg sent")

        hedge_filled = float(hedge_order.get("filled", 0.0) or 0.0)
        hedge_avg_price = float(hedge_order.get("average") or intent.leg_b.price or 0.0)
        self.journal.record_fill(intent.intent_id, hedge_order.get("id"), hedge_filled, hedge_avg_price, hedge_order)

        residual_qty = abs(filled_qty - hedge_filled)
        residual_notional = residual_qty * max(hedge_avg_price or intent.leg_b.price or 0.0, 0.0)
        dust_ratio = residual_qty / max(filled_qty, 1e-9)
        is_dust = (
            dust_ratio <= max(intent.min_fill_ratio_for_hedge, EXECUTION_DUST_FILL_RATIO)
            and residual_notional <= max(intent.dust_notional_threshold, EXECUTION_DUST_NOTIONAL_THRESHOLD_USDT)
        )

        if hedge_filled + 1e-9 >= filled_qty or is_dust:
            machine.transition(IntentState.HEDGED)
            self.journal.transition_state(intent.intent_id, IntentState.HEDGED, "hedge leg matched maker exposure")
            machine.transition(IntentState.CLOSED)
            self.journal.transition_state(intent.intent_id, IntentState.CLOSED, "intent closed")
            if is_dust and residual_qty > 0:
                self.journal.record_recovery_action(
                    intent.intent_id,
                    "DUST_EXPOSURE",
                    f"Residual qty={residual_qty:.8f}, notional={residual_notional:.4f}",
                )
            return ExecutionOutcome(
                True,
                IntentState.CLOSED,
                "intent hedged successfully",
                intent.intent_id,
                filled_qty_leg_a=filled_qty,
                filled_qty_leg_b=hedge_filled,
                net_edge_after_friction_bps=net_edge,
                dust_exposure=is_dust and residual_qty > 0,
            )

        if intent.abort_on_partial_fill:
            await self._rollback_leg(intent, maker_exchange, intent.leg_a, residual_qty)
            machine.transition(IntentState.ROLLBACK_SENT)
            self.journal.transition_state(intent.intent_id, IntentState.ROLLBACK_SENT, "hedge partial fill forced rollback")
            machine.transition(IntentState.FAILED_SAFE)
            self.journal.transition_state(intent.intent_id, IntentState.FAILED_SAFE, "rollback completed after hedge partial fill")
            return ExecutionOutcome(
                False,
                IntentState.FAILED_SAFE,
                "hedge partial fill exceeded dust limits",
                intent.intent_id,
                filled_qty_leg_a=filled_qty,
                filled_qty_leg_b=hedge_filled,
                net_edge_after_friction_bps=net_edge,
            )

        machine.transition(IntentState.CLOSED)
        self.journal.transition_state(intent.intent_id, IntentState.CLOSED, "partial hedge accepted")
        return ExecutionOutcome(
            True,
            IntentState.CLOSED,
            "partial hedge accepted",
            intent.intent_id,
            filled_qty_leg_a=filled_qty,
            filled_qty_leg_b=hedge_filled,
            net_edge_after_friction_bps=net_edge,
        )

    async def _submit_primary_leg(
        self,
        intent: TradeIntent,
        exchange: Any,
        machine: IntentStateMachine,
    ) -> dict[str, Any] | None:
        try:
            order = await self._submit_leg(exchange, intent.intent_id, "leg_a", intent.leg_a, intent.target_base_qty)
            machine.transition(IntentState.MAKER_SENT)
            self.journal.transition_state(intent.intent_id, IntentState.MAKER_SENT, "maker leg sent")
            if str(order.get("status", "")).lower() != "closed":
                order = await self._refresh_or_cancel_primary_leg(intent, exchange, order, machine)
            return order
        except TimeoutError:
            machine.transition(IntentState.UNKNOWN_REMOTE_STATE)
            self.journal.transition_state(intent.intent_id, IntentState.UNKNOWN_REMOTE_STATE, "maker create timeout")
            order = await self._recover_unknown_remote_state(intent, exchange)
            if order:
                return order
            self.journal.transition_state(intent.intent_id, IntentState.FAILED_SAFE, "maker timeout with no remote confirmation")
            return None

    async def _recover_unknown_remote_state(self, intent: TradeIntent, exchange: Any) -> dict[str, Any] | None:
        if not hasattr(exchange, "fetch_order_by_client_order_id"):
            return None

        start = time.monotonic()
        for delay in (0.0,) + self.unknown_remote_retry_delays:
            if delay > 0:
                await self.sleep_fn(delay)
            order = await exchange.fetch_order_by_client_order_id(
                intent.leg_a.client_order_id,
                intent.leg_a.symbol,
            )
            if order:
                self.journal.record_order(
                    intent_id=intent.intent_id,
                    order_id=order.get("id"),
                    leg_name="leg_a",
                    exchange=intent.leg_a.exchange,
                    symbol=intent.leg_a.symbol,
                    side=intent.leg_a.side,
                    order_type=intent.leg_a.type,
                    client_order_id=intent.leg_a.client_order_id,
                    status=str(order.get("status", "recovered")),
                    reduce_only=intent.leg_a.reduce_only,
                    post_only=intent.leg_a.post_only,
                    raw=order,
                )
                return order
            if time.monotonic() - start > self.unknown_remote_max_age_sec:
                break
        return None

    async def _refresh_or_cancel_primary_leg(
        self,
        intent: TradeIntent,
        exchange: Any,
        order: dict[str, Any],
        machine: IntentStateMachine,
    ) -> dict[str, Any]:
        order_id = order.get("id")
        refreshed = await exchange.fetch_order(order_id, intent.leg_a.symbol)
        status = str(refreshed.get("status", "")).lower()
        if status == "closed":
            return refreshed

        filled = float(refreshed.get("filled", 0.0) or 0.0)
        if filled > 0:
            machine.transition(IntentState.MAKER_PARTIAL)
            self.journal.transition_state(intent.intent_id, IntentState.MAKER_PARTIAL, "maker partially filled")

        machine.transition(IntentState.CANCEL_PENDING)
        self.journal.transition_state(intent.intent_id, IntentState.CANCEL_PENDING, "canceling maker remainder")
        try:
            await exchange.cancel_order(order_id, intent.leg_a.symbol)
        except Exception:
            if hasattr(exchange, "fetch_order"):
                return await exchange.fetch_order(order_id, intent.leg_a.symbol)
            raise
        return refreshed

    async def _submit_leg(
        self,
        exchange: Any,
        intent_id: str,
        leg_name: str,
        leg: ExecutionLeg,
        qty: float,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if leg.reduce_only:
            params["reduceOnly"] = True
        if leg.post_only:
            params["postOnly"] = True
        if leg.time_in_force:
            params["timeInForce"] = leg.time_in_force

        kwargs: dict[str, Any] = {
            "symbol": leg.symbol,
            "type": leg.type,
            "side": leg.side,
            "amount": qty,
            "params": params,
        }
        if leg.price is not None:
            kwargs["price"] = leg.price

        order = await exchange.create_order(**kwargs)
        self.journal.record_order(
            intent_id=intent_id,
            order_id=order.get("id"),
            leg_name=leg_name,
            exchange=leg.exchange,
            symbol=leg.symbol,
            side=leg.side,
            order_type=leg.type,
            client_order_id=leg.client_order_id,
            status=str(order.get("status", "submitted")),
            reduce_only=leg.reduce_only,
            post_only=leg.post_only,
            raw=order,
        )
        return order

    async def _rollback_leg(
        self,
        intent: TradeIntent,
        exchange: Any,
        source_leg: ExecutionLeg,
        qty: float,
    ) -> None:
        rollback_leg = replace(
            source_leg,
            side=source_leg.opposite_side(),
            type="market",
            time_in_force="IOC",
            reduce_only=True,
            post_only=False,
            price=None,
            client_order_id=f"{source_leg.client_order_id}-rollback",
        )
        await self._submit_leg(exchange, intent.intent_id, "rollback", rollback_leg, qty)
        self.journal.record_recovery_action(
            intent.intent_id,
            "ROLLBACK",
            f"Rollback qty={qty:.8f} on {source_leg.exchange}",
        )

    def _compute_net_edge_after_friction_bps(
        self,
        intent: TradeIntent,
        filled_price: float,
        expected_price: float,
    ) -> float:
        if expected_price <= 0:
            return -intent.rollback_reserve_bps
        price_slippage_bps = abs(filled_price - expected_price) / expected_price * 10000
        return intent.expected_edge_bps - price_slippage_bps - intent.rollback_reserve_bps
