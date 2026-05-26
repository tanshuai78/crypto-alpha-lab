from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from configs.base import (
    EXTREME_FUNDING_ANCHOR_ANNUALIZED_THRESHOLD_PCT,
    EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO,
    EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS,
    EXTREME_FUNDING_FEE_BPS,
    EXTREME_FUNDING_RESEARCH_BASIS_ABSORPTION_MAX_RATIO,
    EXTREME_FUNDING_RESEARCH_MIN_GROSS_FUNDING_BPS,
    EXTREME_FUNDING_ROLLBACK_RESERVE_BPS,
    EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS,
    EXTREME_FUNDING_TRADE_EXPECTED_HOLDING_INTERVALS,
)
from src.strategies.extreme_funding.candidate_builder import build_extreme_funding_candidate


@dataclass(frozen=True)
class ExtremeFundingAdmissionResult:
    anchor_event: bool
    research_shadow_admitted: bool
    trade_candidate_admitted: bool
    admission_layer: str
    reject_reason: str | None
    metrics: dict[str, Any]


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


def classify_extreme_funding_admission(row: dict[str, Any]) -> ExtremeFundingAdmissionResult:
    annualized_pct = _number_or_none(row.get("annualized_funding_estimate_pct"))
    funding_rate_per_interval = _number_or_none(row.get("funding_rate_per_interval"))
    basis_bps = _number_or_none(row.get("basis_bps"))

    expected_holding_intervals = int(
        _number_or_none(row.get("expected_holding_intervals"))
        or EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS
    )
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
    estimated_total_cost_bps = fee_bps + slippage_bps + rollback_reserve_bps

    gross_funding_bps = (
        funding_rate_per_interval * expected_holding_intervals * 10_000.0
        if funding_rate_per_interval is not None
        else None
    )
    basis_cost_bps = max(basis_bps, 0.0) if basis_bps is not None else None
    if gross_funding_bps is None or basis_cost_bps is None:
        basis_absorption_ratio = None
        net_edge_bps = None
    else:
        basis_absorption_ratio = (
            basis_cost_bps / gross_funding_bps if gross_funding_bps > 0.0 else float("inf")
        )
        net_edge_bps = gross_funding_bps - basis_cost_bps - estimated_total_cost_bps

    basis_path_intervals = int(_number_or_none(row.get("basis_path_intervals")) or 0)
    basis_snapshot_available = basis_bps is not None
    basis_path_available = basis_path_intervals >= 1
    assumption_level = (
        "conservative_1_interval"
        if expected_holding_intervals == EXTREME_FUNDING_TRADE_EXPECTED_HOLDING_INTERVALS
        else f"optimistic_{expected_holding_intervals}_intervals"
    )

    metrics: dict[str, Any] = {
        "annualized_funding_estimate_pct": annualized_pct,
        "funding_rate_per_interval": funding_rate_per_interval,
        "expected_holding_intervals": expected_holding_intervals,
        "gross_funding_bps": gross_funding_bps,
        "basis_bps": basis_bps,
        "basis_absorption_ratio": basis_absorption_ratio,
        "net_edge_bps": net_edge_bps,
        "estimated_total_cost_bps": estimated_total_cost_bps,
        "assumption_level": assumption_level,
        "basis_snapshot_available": basis_snapshot_available,
        "basis_path_available": basis_path_available,
        "basis_path_intervals": basis_path_intervals,
        "trade_blockers": [],
    }

    if funding_rate_per_interval is None:
        return ExtremeFundingAdmissionResult(
            False,
            False,
            False,
            "no_anchor",
            "missing_funding_rate",
            metrics,
        )

    if annualized_pct is None or annualized_pct < EXTREME_FUNDING_ANCHOR_ANNUALIZED_THRESHOLD_PCT:
        return ExtremeFundingAdmissionResult(
            False,
            False,
            False,
            "no_anchor",
            "anchor_threshold_not_met",
            metrics,
        )

    if funding_rate_per_interval <= 0.0:
        return ExtremeFundingAdmissionResult(
            False,
            False,
            False,
            "no_anchor",
            "non_positive_funding_rate",
            metrics,
        )

    if basis_bps is None:
        return ExtremeFundingAdmissionResult(
            True,
            False,
            False,
            "anchor_only",
            "missing_basis",
            metrics,
        )

    if gross_funding_bps is None or gross_funding_bps < EXTREME_FUNDING_RESEARCH_MIN_GROSS_FUNDING_BPS:
        return ExtremeFundingAdmissionResult(
            True,
            False,
            False,
            "anchor_only",
            "research_gross_funding_below_min",
            metrics,
        )

    if (
        basis_absorption_ratio is None
        or basis_absorption_ratio > EXTREME_FUNDING_RESEARCH_BASIS_ABSORPTION_MAX_RATIO
    ):
        return ExtremeFundingAdmissionResult(
            True,
            False,
            False,
            "anchor_only",
            "research_basis_absorbed",
            metrics,
        )

    trade_blockers: list[str] = []
    if expected_holding_intervals != EXTREME_FUNDING_TRADE_EXPECTED_HOLDING_INTERVALS:
        trade_blockers.append("trade_requires_conservative_one_interval")

    trade_decision = build_extreme_funding_candidate(row)
    if not trade_decision.accepted:
        if trade_decision.reject_reason == "net_edge_below_min":
            trade_blockers.append("research_only_net_edge_below_trade_gate")
        if trade_decision.reject_reason is not None:
            trade_blockers.append(trade_decision.reject_reason)
    metrics["trade_blockers"] = trade_blockers

    trade_candidate_admitted = (
        expected_holding_intervals == EXTREME_FUNDING_TRADE_EXPECTED_HOLDING_INTERVALS
        and trade_decision.accepted
    )
    if trade_candidate_admitted:
        return ExtremeFundingAdmissionResult(
            True,
            True,
            True,
            "trade_candidate",
            None,
            metrics,
        )

    reject_reason = trade_blockers[0] if trade_blockers else "trade_gate_not_passed"
    return ExtremeFundingAdmissionResult(
        True,
        True,
        False,
        "research_shadow",
        reject_reason,
        metrics,
    )
