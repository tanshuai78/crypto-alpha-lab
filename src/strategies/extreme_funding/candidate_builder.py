from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from configs.base import (
    EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO,
    EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS,
    EXTREME_FUNDING_FEE_BPS,
    EXTREME_FUNDING_MAX_HOLDING_HOURS,
    EXTREME_FUNDING_MAX_SLIPPAGE_BPS,
    EXTREME_FUNDING_MICRO_PERSISTENCE_MIN,
    EXTREME_FUNDING_MIN_EXPECTED_FUNDING_INCOME_BPS,
    EXTREME_FUNDING_MIN_NET_EDGE_BPS,
    EXTREME_FUNDING_ROLLBACK_RESERVE_BPS,
    EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS,
    EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
    RISK_MAX_SINGLE_POSITION_USDT,
)
from src.strategies.base import SignalCandidate

_ALLOWED_WATCH_LEVELS = {"watch_level_2", "watch_level_3", "historical_settled_extreme"}


@dataclass(frozen=True)
class ExtremeFundingCandidateDecision:
    accepted: bool
    candidate: SignalCandidate | None
    reject_reason: str | None
    metrics: dict[str, Any]


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


def _reject(reason: str, metrics: dict[str, Any]) -> ExtremeFundingCandidateDecision:
    return ExtremeFundingCandidateDecision(False, None, reason, metrics)


def _costs(row: dict[str, Any]) -> tuple[float, float, float, float]:
    fee_bps = _number_or_none(row.get("fee_bps"))
    slippage_bps = _number_or_none(row.get("slippage_bps"))
    rollback_reserve_bps = _number_or_none(row.get("rollback_reserve_bps"))
    fee_bps = EXTREME_FUNDING_FEE_BPS if fee_bps is None else fee_bps
    slippage_bps = EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS if slippage_bps is None else slippage_bps
    rollback_reserve_bps = (
        EXTREME_FUNDING_ROLLBACK_RESERVE_BPS
        if rollback_reserve_bps is None
        else rollback_reserve_bps
    )
    return fee_bps, slippage_bps, rollback_reserve_bps, fee_bps + slippage_bps + rollback_reserve_bps


def build_extreme_funding_candidate(row: dict[str, Any]) -> ExtremeFundingCandidateDecision:
    symbol = str(row.get("symbol") or "UNKNOWN")
    exchange = str(row.get("exchange") or "unknown")
    source_type = str(row.get("source_type") or "live_watch_event")
    watch_level = str(row.get("watch_level") or "")

    annualized_pct = _number_or_none(row.get("annualized_funding_estimate_pct"))
    micro_persistence = _number_or_none(row.get("micro_persistence"))
    settlement_persistence = _number_or_none(row.get("settlement_persistence"))
    funding_rate_per_interval = _number_or_none(row.get("funding_rate_per_interval"))
    basis_bps = _number_or_none(row.get("basis_bps"))
    depth_capacity_usdt = _number_or_none(row.get("depth_capacity_usdt"))
    planned_notional_usdt = _number_or_none(row.get("planned_notional_usdt")) or RISK_MAX_SINGLE_POSITION_USDT
    expected_intervals = int(
        _number_or_none(row.get("expected_holding_intervals"))
        or EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS
    )

    fee_bps, slippage_bps, rollback_reserve_bps, estimated_total_cost_bps = _costs(row)

    metrics: dict[str, Any] = {
        "symbol": symbol,
        "exchange": exchange,
        "source_type": source_type,
        "watch_level": watch_level,
        "annualized_funding_estimate_pct": annualized_pct,
        "micro_persistence": micro_persistence,
        "settlement_persistence": settlement_persistence,
        "expected_holding_intervals": expected_intervals,
        "fee_bps": fee_bps,
        "slippage_bps": slippage_bps,
        "rollback_reserve_bps": rollback_reserve_bps,
        "estimated_total_cost_bps": estimated_total_cost_bps,
    }

    if watch_level not in _ALLOWED_WATCH_LEVELS:
        return _reject("watch_level_too_weak", metrics)
    if annualized_pct is None or annualized_pct < EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT:
        return _reject("annualized_funding_below_trade_threshold", metrics)

    if source_type == "historical_settled":
        if settlement_persistence is None or settlement_persistence < 0.50:
            return _reject("settlement_persistence_below_min", metrics)
    elif micro_persistence is None or micro_persistence < EXTREME_FUNDING_MICRO_PERSISTENCE_MIN:
        return _reject("micro_persistence_below_min", metrics)

    if funding_rate_per_interval is None:
        return _reject("missing_funding_rate", metrics)
    if basis_bps is None:
        return _reject("missing_basis", metrics)

    expected_funding_income_bps = funding_rate_per_interval * expected_intervals * 10_000.0
    basis_cost_bps = max(basis_bps, 0.0)
    basis_absorption_ratio = (
        basis_cost_bps / expected_funding_income_bps
        if expected_funding_income_bps > 0.0
        else float("inf")
    )
    net_edge_bps = expected_funding_income_bps - basis_cost_bps - estimated_total_cost_bps

    metrics.update(
        {
            "funding_rate_per_interval": funding_rate_per_interval,
            "basis_bps": basis_bps,
            "basis_cost_bps": basis_cost_bps,
            "basis_absorption_ratio": basis_absorption_ratio,
            "expected_funding_income_bps": expected_funding_income_bps,
            "net_edge_bps": net_edge_bps,
            "depth_capacity_usdt": depth_capacity_usdt,
            "planned_notional_usdt": planned_notional_usdt,
        }
    )

    if expected_funding_income_bps < EXTREME_FUNDING_MIN_EXPECTED_FUNDING_INCOME_BPS:
        return _reject("expected_funding_income_below_min", metrics)
    if basis_absorption_ratio > EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO:
        return _reject("basis_absorbed", metrics)
    if net_edge_bps < EXTREME_FUNDING_MIN_NET_EDGE_BPS:
        return _reject("net_edge_below_min", metrics)
    if slippage_bps > EXTREME_FUNDING_MAX_SLIPPAGE_BPS:
        return _reject("slippage_above_max", metrics)
    if depth_capacity_usdt is None:
        return _reject("missing_depth_capacity", metrics)
    if depth_capacity_usdt < planned_notional_usdt * 2.0:
        return _reject("depth_capacity_insufficient", metrics)

    candidate = SignalCandidate(
        strategy_type="extreme_funding",
        symbol=symbol,
        direction=str(row.get("direction") or "neutral"),
        confidence=0.60,
        expected_edge_bps=round(net_edge_bps, 10),
        entry_exchange=exchange,
        hedge_exchange=exchange,
        trigger_reason="extreme_funding_basis_aware_candidate",
        invalidation_reason="funding_decay_or_basis_loss_halt",
        max_holding_hours=float(EXTREME_FUNDING_MAX_HOLDING_HOURS),
        stop_loss_pct=0.0,
        suggested_notional_usdt=min(planned_notional_usdt, RISK_MAX_SINGLE_POSITION_USDT),
        metadata={
            "mode": "observation",
            "executable": False,
            "coverage_quality": row.get("coverage_quality", "live_basis_aware_observation"),
            "source_type": source_type,
            "watch_level": watch_level,
            "basis_source": row.get("basis_source"),
            "basis_bps": basis_bps,
            "basis_absorption_ratio": round(basis_absorption_ratio, 10),
            "expected_funding_income_bps": round(expected_funding_income_bps, 10),
            "fee_bps": fee_bps,
            "slippage_bps": slippage_bps,
            "rollback_reserve_bps": rollback_reserve_bps,
            "estimated_total_cost_bps": estimated_total_cost_bps,
            "expected_holding_intervals": expected_intervals,
        },
    )
    return ExtremeFundingCandidateDecision(True, candidate, None, metrics)
