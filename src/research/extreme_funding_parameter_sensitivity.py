from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import mean, median

from configs.base import (
    EXTREME_FUNDING_FEE_BPS,
    EXTREME_FUNDING_ROLLBACK_RESERVE_BPS,
    EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
    EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS,
    RISK_MAX_SINGLE_POSITION_USDT,
)
from src.research.extreme_funding_basis_replay import HistoricalBasisRow
from src.strategies.extreme_funding.candidate_builder import (
    ExtremeFundingCandidateThresholds,
    build_extreme_funding_candidate,
)
from src.strategies.extreme_funding.shadow_simulator import (
    ExtremeFundingShadowPosition,
    simulate_extreme_funding_shadow,
)


@dataclass(frozen=True)
class SensitivityParamSet:
    annualized_threshold_pct: float
    min_expected_funding_income_bps: float
    max_slippage_bps: float
    expected_holding_intervals: int
    basis_absorption_max_ratio: float


def _assumption_level(expected_holding_intervals: int) -> str:
    if expected_holding_intervals <= 1:
        return "conservative_1_interval"
    return "optimistic_2_intervals"


def build_parameter_grid(
    *,
    annualized_grid: tuple[float, ...],
    min_income_grid: tuple[float, ...],
    max_slippage_grid: tuple[float, ...],
    expected_intervals_grid: tuple[int, ...],
    basis_absorption_grid: tuple[float, ...],
) -> list[SensitivityParamSet]:
    params: list[SensitivityParamSet] = []
    for annualized in annualized_grid:
        for min_income in min_income_grid:
            for max_slippage in max_slippage_grid:
                for expected_intervals in expected_intervals_grid:
                    for basis_absorption in basis_absorption_grid:
                        params.append(
                            SensitivityParamSet(
                                annualized_threshold_pct=float(annualized),
                                min_expected_funding_income_bps=float(min_income),
                                max_slippage_bps=float(max_slippage),
                                expected_holding_intervals=int(expected_intervals),
                                basis_absorption_max_ratio=float(basis_absorption),
                            )
                        )
    return params


def _param_set_dict(param_set: SensitivityParamSet) -> dict:
    return {
        "annualized_threshold_pct": param_set.annualized_threshold_pct,
        "min_expected_funding_income_bps": param_set.min_expected_funding_income_bps,
        "max_slippage_bps": param_set.max_slippage_bps,
        "expected_holding_intervals": param_set.expected_holding_intervals,
        "basis_absorption_max_ratio": param_set.basis_absorption_max_ratio,
        "assumption_level": _assumption_level(param_set.expected_holding_intervals),
    }


def run_candidate_sensitivity(
    rows: list[HistoricalBasisRow],
    param_sets: list[SensitivityParamSet],
) -> list[dict]:
    summaries: list[dict] = []
    for param_set in param_sets:
        thresholds = ExtremeFundingCandidateThresholds(
            annualized_threshold_pct=param_set.annualized_threshold_pct,
            min_expected_funding_income_bps=param_set.min_expected_funding_income_bps,
            max_slippage_bps=param_set.max_slippage_bps,
            expected_holding_intervals=param_set.expected_holding_intervals,
            min_net_edge_bps=30.0,
            basis_absorption_max_ratio=param_set.basis_absorption_max_ratio,
        )

        reject_counts: Counter[str] = Counter()
        accepted_indexes: list[int] = []

        for index, row in enumerate(rows):
            decision = build_extreme_funding_candidate(
                row.to_candidate_row(),
                thresholds=thresholds,
            )
            if decision.accepted:
                accepted_indexes.append(index)
            else:
                reject_counts[decision.reject_reason or "unknown_reject"] += 1

        candidate_count = len(accepted_indexes)
        summary = {
            "param_set": _param_set_dict(param_set),
            "input_row_count": len(rows),
            "candidate_count": candidate_count,
            "candidate_rate": (candidate_count / len(rows)) if rows else 0.0,
            "reject_reason_counts": dict(sorted(reject_counts.items())),
            "top_reject_reason": (
                reject_counts.most_common(1)[0][0] if reject_counts else None
            ),
            "coverage_quality": (
                "historical_basis_proxy_not_depth_aware"
                if rows
                else "insufficient_basis_data"
            ),
            "depth_aware": False,
            "depth_source": "static_min_capacity_proxy" if rows else None,
            "status": "ok" if rows else "insufficient_basis_data",
            "accepted_row_indexes": accepted_indexes,
        }
        summaries.append(summary)
    return summaries


def run_shadow_sensitivity(
    rows: list[HistoricalBasisRow],
    candidate_summaries: list[dict],
) -> list[dict]:
    total_cost_bps = (
        EXTREME_FUNDING_FEE_BPS
        + EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS
        + EXTREME_FUNDING_ROLLBACK_RESERVE_BPS
    )

    rows_by_symbol: dict[str, list[HistoricalBasisRow]] = defaultdict(list)
    for row in rows:
        rows_by_symbol[row.symbol].append(row)
    for symbol in rows_by_symbol:
        rows_by_symbol[symbol].sort(key=lambda item: item.funding_time_ms)

    summaries: list[dict] = []
    for candidate_summary in candidate_summaries:
        accepted_indexes = list(candidate_summary.get("accepted_row_indexes", []))
        results = []
        exit_counts: Counter[str] = Counter()

        for index in accepted_indexes:
            entry = rows[index]
            symbol_rows = rows_by_symbol.get(entry.symbol, [])
            path_rows = [
                row
                for row in symbol_rows
                if row.funding_time_ms > entry.funding_time_ms
            ][:EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS]

            position = ExtremeFundingShadowPosition(
                symbol=entry.symbol,
                side="long_spot_short_perp",
                entry_time_ms=entry.funding_time_ms,
                entry_basis_bps=entry.basis_bps,
                estimated_total_cost_bps=total_cost_bps,
                notional_usdt=RISK_MAX_SINGLE_POSITION_USDT,
                max_holding_intervals=EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
                coverage_quality="historical_basis_proxy_not_depth_aware",
            )

            simulated = simulate_extreme_funding_shadow(
                position,
                [
                    {
                        "funding_time_ms": row.funding_time_ms,
                        "funding_rate": row.funding_rate,
                        "basis_bps": row.basis_bps,
                        "annualized_pct": row.annualized_pct,
                    }
                    for row in path_rows
                ],
            )
            results.append(simulated)
            exit_counts[simulated.exit_reason] += 1

        pnl_values = [result.net_pnl_bps for result in results]
        shadow_trade_count = len(results)
        summaries.append(
            {
                "param_set": candidate_summary["param_set"],
                "candidate_count": int(candidate_summary.get("candidate_count", 0)),
                "shadow_trade_count": shadow_trade_count,
                "median_net_pnl_bps": median(pnl_values) if pnl_values else 0.0,
                "mean_net_pnl_bps": mean(pnl_values) if pnl_values else 0.0,
                "win_rate": (
                    (sum(1 for value in pnl_values if value > 0.0) / len(pnl_values))
                    if pnl_values
                    else 0.0
                ),
                "exit_reason_counts": dict(sorted(exit_counts.items())),
                "coverage_quality": (
                    "historical_basis_proxy_not_depth_aware"
                    if rows
                    else "insufficient_basis_data"
                ),
                "depth_aware": False,
                "depth_source": "static_min_capacity_proxy" if rows else None,
                "status": "ok" if rows else "insufficient_basis_data",
            }
        )
    return summaries


def build_sensitivity_report(
    rows: list[HistoricalBasisRow],
    param_sets: list[SensitivityParamSet],
) -> dict:
    candidate = run_candidate_sensitivity(rows, param_sets)
    shadow = run_shadow_sensitivity(rows, candidate)
    return {
        "status": "ok" if rows else "insufficient_basis_data",
        "coverage_quality": (
            "historical_basis_proxy_not_depth_aware"
            if rows
            else "insufficient_basis_data"
        ),
        "depth_aware": False,
        "candidate_summaries": candidate,
        "shadow_summaries": shadow,
    }
