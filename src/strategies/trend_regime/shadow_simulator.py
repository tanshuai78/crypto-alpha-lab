from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TrendRegimeShadowPosition:
    symbol: str
    direction: str
    entry_time_ms: int
    entry_price: float
    estimated_cost_bps: float
    max_holding_hours: float
    stop_loss_pct: float
    regime: str
    symbol_tier: str


@dataclass(frozen=True)
class TrendRegimeShadowResult:
    symbol: str
    direction: str
    regime: str
    symbol_tier: str
    exit_reason: str
    entry_time_ms: int
    exit_time_ms: int
    entry_price: float
    exit_price: float
    holding_hours: float
    gross_pnl_pct: float
    estimated_cost_bps: float
    net_pnl_bps: float


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _gross_pnl_pct(direction: str, entry_price: float, exit_price: float) -> float:
    if direction == "long":
        return (exit_price / entry_price - 1.0) * 100.0
    return (entry_price - exit_price) / entry_price * 100.0


def simulate_trend_regime_shadow(
    position: TrendRegimeShadowPosition,
    price_path: list[dict[str, Any]],
) -> TrendRegimeShadowResult:
    exit_reason = "path_exhausted"
    exit_time_ms = position.entry_time_ms
    exit_price = position.entry_price
    holding_hours = 0.0

    for row in price_path:
        timestamp_ms = int(_number_or_none(row.get("timestamp_ms")) or 0)
        close_price = _number_or_none(row.get("close_price"))
        if close_price is None or timestamp_ms <= position.entry_time_ms:
            continue

        holding_hours = (timestamp_ms - position.entry_time_ms) / 3_600_000.0
        gross_pnl_pct = _gross_pnl_pct(position.direction, position.entry_price, close_price)

        exit_time_ms = timestamp_ms
        exit_price = close_price

        if gross_pnl_pct <= -float(position.stop_loss_pct):
            exit_reason = "stop_loss_hit"
            break
        if holding_hours >= float(position.max_holding_hours):
            exit_reason = "max_holding_time_reached"
            break

    gross_pnl_pct = _gross_pnl_pct(position.direction, position.entry_price, exit_price)
    net_pnl_bps = gross_pnl_pct * 100.0 - position.estimated_cost_bps

    return TrendRegimeShadowResult(
        symbol=position.symbol,
        direction=position.direction,
        regime=position.regime,
        symbol_tier=position.symbol_tier,
        exit_reason=exit_reason,
        entry_time_ms=position.entry_time_ms,
        exit_time_ms=exit_time_ms,
        entry_price=position.entry_price,
        exit_price=exit_price,
        holding_hours=round(holding_hours, 10),
        gross_pnl_pct=round(gross_pnl_pct, 10),
        estimated_cost_bps=position.estimated_cost_bps,
        net_pnl_bps=round(net_pnl_bps, 10),
    )
