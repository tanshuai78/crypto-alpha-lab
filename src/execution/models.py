from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExecutionLeg:
    exchange: str
    symbol: str
    side: str
    type: str
    position_side: str
    client_order_id: str
    time_in_force: str
    reduce_only: bool
    post_only: bool
    price: Optional[float] = None

    def opposite_side(self) -> str:
        if self.side == "buy":
            return "sell"
        if self.side == "sell":
            return "buy"
        raise ValueError(f"Unsupported side: {self.side}")


@dataclass(frozen=True)
class TradeIntent:
    intent_id: str
    strategy_type: str
    leg_a: ExecutionLeg
    leg_b: ExecutionLeg
    target_base_qty: float
    max_notional_usdt: float
    execution_mode: str
    maker_leg_timeout_ms: int
    taker_ioc_timeout_ms: int
    expected_edge_bps: float
    min_fill_ratio_for_hedge: float
    dust_notional_threshold: float
    rollback_reserve_bps: float
    close_only_on_rollback: bool
    abort_on_partial_fill: bool
    status: str = "CREATED"

    def __post_init__(self) -> None:
        if not self.close_only_on_rollback:
            raise ValueError("close_only_on_rollback must remain True")
        if self.target_base_qty <= 0:
            raise ValueError("target_base_qty must be positive")
        if self.max_notional_usdt <= 0:
            raise ValueError("max_notional_usdt must be positive")


@dataclass
class ExecutionOutcome:
    success: bool
    state: object
    reason: str
    intent_id: str
    filled_qty_leg_a: float = 0.0
    filled_qty_leg_b: float = 0.0
    net_edge_after_friction_bps: float = 0.0
    dust_exposure: bool = False
