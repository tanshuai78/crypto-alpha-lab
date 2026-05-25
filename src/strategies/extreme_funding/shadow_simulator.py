from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from configs.base import (
    EXTREME_FUNDING_SHADOW_BASIS_LOSS_HALT_RATIO,
    EXTREME_FUNDING_SHADOW_EXIT_ANNUALIZED_BELOW_PCT,
)


@dataclass(frozen=True)
class ExtremeFundingShadowPosition:
    symbol: str
    side: str
    entry_time_ms: int
    entry_basis_bps: float
    estimated_total_cost_bps: float
    notional_usdt: float
    max_holding_intervals: int
    coverage_quality: str


@dataclass(frozen=True)
class ExtremeFundingShadowResult:
    symbol: str
    side: str
    closed: bool
    exit_reason: str
    intervals_held: int
    funding_income_bps: float
    basis_change_bps: float
    basis_loss_bps: float
    estimated_total_cost_bps: float
    net_pnl_bps: float
    coverage_quality: str
    notes: list[str]


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:
        return None
    return result


def simulate_extreme_funding_shadow(
    position: ExtremeFundingShadowPosition,
    path: list[dict[str, Any]],
) -> ExtremeFundingShadowResult:
    funding_income_bps = 0.0
    basis_change_bps = 0.0
    notes: list[str] = []
    exit_reason = "path_exhausted"
    intervals_held = 0

    for row in path:
        if intervals_held >= position.max_holding_intervals:
            exit_reason = "max_holding_intervals_reached"
            break

        funding_rate = _number_or_none(row.get("funding_rate")) or 0.0
        funding_income_bps += funding_rate * 10_000.0
        intervals_held += 1

        basis_bps = _number_or_none(row.get("basis_bps"))
        if basis_bps is None:
            if "basis_path_missing" not in notes:
                notes.append("basis_path_missing")
            basis_bps = position.entry_basis_bps

        basis_change_bps = basis_bps - position.entry_basis_bps
        basis_loss_bps = max(basis_change_bps, 0.0)

        if funding_rate < 0.0:
            exit_reason = "funding_flip"
            break

        annualized_pct = _number_or_none(row.get("annualized_pct"))
        if annualized_pct is not None and annualized_pct < EXTREME_FUNDING_SHADOW_EXIT_ANNUALIZED_BELOW_PCT:
            exit_reason = "funding_decay"
            break

        if (
            funding_income_bps > 0.0
            and basis_loss_bps > funding_income_bps * EXTREME_FUNDING_SHADOW_BASIS_LOSS_HALT_RATIO
        ):
            exit_reason = "basis_loss_halt"
            break

    if intervals_held >= position.max_holding_intervals and exit_reason == "path_exhausted":
        exit_reason = "max_holding_intervals_reached"

    net_pnl_bps = funding_income_bps - basis_change_bps - position.estimated_total_cost_bps
    return ExtremeFundingShadowResult(
        symbol=position.symbol,
        side=position.side,
        closed=True,
        exit_reason=exit_reason,
        intervals_held=intervals_held,
        funding_income_bps=round(funding_income_bps, 10),
        basis_change_bps=round(basis_change_bps, 10),
        basis_loss_bps=round(max(basis_change_bps, 0.0), 10),
        estimated_total_cost_bps=position.estimated_total_cost_bps,
        net_pnl_bps=round(net_pnl_bps, 10),
        coverage_quality=position.coverage_quality,
        notes=notes,
    )
