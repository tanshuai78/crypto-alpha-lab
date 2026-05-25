from src.strategies.base import SignalCandidate
from src.strategies.extreme_funding.candidate_builder import (
    ExtremeFundingCandidateThresholds,
    build_extreme_funding_candidate,
)


def _complete_row(**overrides):
    row = {
        "timestamp_ms": 1710000000000,
        "source_type": "live_watch_event",
        "symbol": "DOGE/USDT",
        "exchange": "binance",
        "direction": "neutral",
        "annualized_funding_estimate_pct": 650.0,
        "funding_rate_per_interval": 0.008,
        "expected_holding_intervals": 1,
        "basis_bps": 10.0,
        "basis_source": "spot_perp_mid",
        "fee_bps": 8.0,
        "slippage_bps": 8.0,
        "rollback_reserve_bps": 10.0,
        "depth_capacity_usdt": 2000.0,
        "planned_notional_usdt": 500.0,
        "micro_persistence": 0.80,
        "settlement_persistence": 0.50,
        "watch_level": "watch_level_3",
        "coverage_quality": "live_basis_aware_observation",
    }
    row.update(overrides)
    return row


def test_build_candidate_accepts_complete_basis_aware_row() -> None:
    decision = build_extreme_funding_candidate(_complete_row())

    assert decision.accepted is True
    assert decision.reject_reason is None
    assert isinstance(decision.candidate, SignalCandidate)
    assert decision.candidate.strategy_type == "extreme_funding"
    assert decision.candidate.symbol == "DOGE/USDT"
    assert decision.candidate.direction == "neutral"
    assert decision.candidate.expected_edge_bps == 44.0
    assert decision.candidate.metadata["mode"] == "observation"
    assert decision.candidate.metadata["executable"] is False
    assert decision.candidate.metadata["estimated_total_cost_bps"] == 26.0
    assert decision.candidate.metadata["basis_absorption_ratio"] == 0.125


def test_candidate_rejects_weak_watch_level() -> None:
    decision = build_extreme_funding_candidate(_complete_row(watch_level="watch_level_1"))
    assert decision.accepted is False
    assert decision.reject_reason == "watch_level_too_weak"


def test_candidate_rejects_low_micro_persistence_for_live_row() -> None:
    decision = build_extreme_funding_candidate(_complete_row(micro_persistence=0.50))
    assert decision.accepted is False
    assert decision.reject_reason == "micro_persistence_below_min"


def test_candidate_rejects_low_settlement_persistence_for_historical_row() -> None:
    decision = build_extreme_funding_candidate(
        _complete_row(
            source_type="historical_settled",
            watch_level="historical_settled_extreme",
            micro_persistence=None,
            settlement_persistence=0.20,
        )
    )
    assert decision.accepted is False
    assert decision.reject_reason == "settlement_persistence_below_min"


def test_candidate_rejects_annualized_below_trade_threshold() -> None:
    decision = build_extreme_funding_candidate(_complete_row(annualized_funding_estimate_pct=80.0))
    assert decision.accepted is False
    assert decision.reject_reason == "annualized_funding_below_trade_threshold"


def test_candidate_rejects_missing_basis() -> None:
    row = _complete_row()
    row.pop("basis_bps")
    decision = build_extreme_funding_candidate(row)
    assert decision.accepted is False
    assert decision.reject_reason == "missing_basis"


def test_candidate_rejects_basis_absorbed() -> None:
    decision = build_extreme_funding_candidate(_complete_row(basis_bps=50.0))
    assert decision.accepted is False
    assert decision.reject_reason == "basis_absorbed"


def test_candidate_rejects_net_edge_below_min() -> None:
    decision = build_extreme_funding_candidate(_complete_row(funding_rate_per_interval=0.006, basis_bps=10.0))
    assert decision.accepted is False
    assert decision.reject_reason == "net_edge_below_min"


def test_candidate_rejects_expected_funding_income_below_min() -> None:
    decision = build_extreme_funding_candidate(
        _complete_row(
            annualized_funding_estimate_pct=120.0,
            funding_rate_per_interval=0.0049,
            basis_bps=0.0,
        )
    )
    assert decision.accepted is False
    assert decision.reject_reason == "expected_funding_income_below_min"


def test_candidate_rejects_slippage_above_max() -> None:
    decision = build_extreme_funding_candidate(_complete_row(slippage_bps=12.0))
    assert decision.accepted is False
    assert decision.reject_reason == "slippage_above_max"


def test_candidate_rejects_missing_depth_capacity() -> None:
    row = _complete_row()
    row.pop("depth_capacity_usdt")
    decision = build_extreme_funding_candidate(row)
    assert decision.accepted is False
    assert decision.reject_reason == "missing_depth_capacity"


def test_candidate_rejects_depth_capacity_insufficient() -> None:
    decision = build_extreme_funding_candidate(_complete_row(depth_capacity_usdt=600.0, planned_notional_usdt=500.0))
    assert decision.accepted is False
    assert decision.reject_reason == "depth_capacity_insufficient"


def test_candidate_builder_accepts_explicit_threshold_overrides() -> None:
    row = _complete_row(annualized_funding_estimate_pct=90.0)
    thresholds = ExtremeFundingCandidateThresholds(
        annualized_threshold_pct=80.0,
        min_expected_funding_income_bps=50.0,
        max_slippage_bps=10.0,
        expected_holding_intervals=1,
        min_net_edge_bps=30.0,
        basis_absorption_max_ratio=0.50,
    )
    decision = build_extreme_funding_candidate(row, thresholds=thresholds)
    assert decision.accepted is True
    assert decision.reject_reason is None


def test_candidate_builder_default_behavior_unchanged_without_overrides() -> None:
    row = _complete_row(annualized_funding_estimate_pct=90.0)
    decision = build_extreme_funding_candidate(row)
    assert decision.accepted is False
    assert decision.reject_reason == "annualized_funding_below_trade_threshold"


def test_candidate_builder_threshold_override_does_not_mutate_global_defaults() -> None:
    row = _complete_row(annualized_funding_estimate_pct=90.0)
    thresholds = ExtremeFundingCandidateThresholds(
        annualized_threshold_pct=80.0,
        min_expected_funding_income_bps=50.0,
        max_slippage_bps=10.0,
        expected_holding_intervals=1,
        min_net_edge_bps=30.0,
        basis_absorption_max_ratio=0.50,
    )
    overridden = build_extreme_funding_candidate(row, thresholds=thresholds)
    default_after = build_extreme_funding_candidate(row)
    assert overridden.accepted is True
    assert default_after.accepted is False
    assert default_after.reject_reason == "annualized_funding_below_trade_threshold"
