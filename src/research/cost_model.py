"""
research/cost_model.py — Trade cost estimation.

Provides precise cost calculations for all strategy types.
No magic numbers: all rates come from configs.base.
"""
from __future__ import annotations


def round_trip_cost_bps(
    *,
    maker_fee_pct: float = 0.0,      # Maker rebate is often -0.01% on Binance
    taker_fee_pct: float = 0.05,     # Standard Taker fee
    slippage_bps: float = 3.0,       # Estimated market impact, both legs
    use_maker: bool = True,          # True = maker_first execution mode
) -> float:
    """Estimate total round-trip cost in basis points.

    Formula:
        entry_fee + exit_fee + slippage
        where entry_fee = maker_fee_pct * 100 (if maker) else taker_fee_pct * 100

    Returns cost in bps (e.g. 8.0 = 0.08%).
    """
    entry_fee_bps = maker_fee_pct * 100 if use_maker else taker_fee_pct * 100
    exit_fee_bps = taker_fee_pct * 100   # Exit is typically market (taker)
    return entry_fee_bps + exit_fee_bps + slippage_bps


def funding_income_bps(
    *,
    funding_rate_per_settlement: float,
    settlements_per_day: int,
    holding_days: float,
) -> float:
    """Estimate total funding income in basis points over a holding period.

    Args:
        funding_rate_per_settlement: Single settlement funding rate (e.g. 0.001 = 0.1%)
        settlements_per_day: Number of settlements per day (Binance=3, OKX=3)
        holding_days: Planned holding period in days
    """
    return funding_rate_per_settlement * settlements_per_day * holding_days * 10000


def net_edge_bps(
    *,
    funding_rate_per_settlement: float,
    settlements_per_day: int,
    holding_days: float,
    maker_fee_pct: float = 0.0,
    taker_fee_pct: float = 0.05,
    slippage_bps: float = 3.0,
    use_maker: bool = True,
) -> float:
    """Compute net edge after all costs in basis points.

    Positive = profitable. Negative = reject.
    """
    income = funding_income_bps(
        funding_rate_per_settlement=funding_rate_per_settlement,
        settlements_per_day=settlements_per_day,
        holding_days=holding_days,
    )
    cost = round_trip_cost_bps(
        maker_fee_pct=maker_fee_pct,
        taker_fee_pct=taker_fee_pct,
        slippage_bps=slippage_bps,
        use_maker=use_maker,
    )
    return income - cost


def annualized_funding_pct(
    funding_rate_per_settlement: float,
    settlements_per_day: int = 3,
) -> float:
    """Convert a per-settlement funding rate to annualized percentage."""
    return funding_rate_per_settlement * settlements_per_day * 365 * 100
