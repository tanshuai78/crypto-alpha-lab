from src.strategies.extreme_funding.admission import classify_extreme_funding_admission


def _row(**overrides):
    row = {
        "source_type": "historical_settled",
        "symbol": "DOGE/USDT",
        "exchange": "binance",
        "watch_level": "historical_settled_extreme",
        "annualized_funding_estimate_pct": 120.0,
        "funding_rate_per_interval": 0.003,
        "expected_holding_intervals": 1,
        "settlement_persistence": 0.60,
        "basis_bps": 8.0,
        "fee_bps": 8.0,
        "slippage_bps": 8.0,
        "rollback_reserve_bps": 10.0,
        "depth_capacity_usdt": 2000.0,
        "planned_notional_usdt": 500.0,
        "basis_path_intervals": 2,
    }
    row.update(overrides)
    return row


def test_classifies_anchor_event_without_trade_candidate():
    result = classify_extreme_funding_admission(_row(funding_rate_per_interval=0.001))
    assert result.anchor_event is True
    assert result.research_shadow_admitted is False
    assert result.trade_candidate_admitted is False
    assert result.admission_layer == "anchor_only"
    assert result.metrics["gross_funding_bps"] == 10.0


def test_research_shadow_admission_allows_lower_gross_funding_than_trade_gate():
    result = classify_extreme_funding_admission(_row(funding_rate_per_interval=0.003))
    assert result.anchor_event is True
    assert result.research_shadow_admitted is True
    assert result.trade_candidate_admitted is False
    assert result.admission_layer == "research_shadow"
    assert "expected_funding_income_below_min" in result.metrics["trade_blockers"]


def test_trade_candidate_requires_one_interval_and_net_edge_gate():
    result = classify_extreme_funding_admission(
        _row(
            annualized_funding_estimate_pct=650.0,
            funding_rate_per_interval=0.008,
            expected_holding_intervals=1,
        )
    )
    assert result.anchor_event is True
    assert result.research_shadow_admitted is True
    assert result.trade_candidate_admitted is True
    assert result.admission_layer == "trade_candidate"


def test_two_interval_assumption_is_marked_optimistic_only():
    result = classify_extreme_funding_admission(
        _row(
            annualized_funding_estimate_pct=650.0,
            funding_rate_per_interval=0.008,
            expected_holding_intervals=2,
        )
    )
    assert result.research_shadow_admitted is True
    assert result.trade_candidate_admitted is False
    assert result.admission_layer == "research_shadow"
    assert result.metrics["assumption_level"] == "optimistic_2_intervals"
    assert "trade_requires_conservative_one_interval" in result.metrics["trade_blockers"]


def test_research_shadow_admission_does_not_emit_signal_candidate():
    result = classify_extreme_funding_admission(_row(funding_rate_per_interval=0.003))
    assert result.research_shadow_admitted is True
    assert result.trade_candidate_admitted is False
    assert "signal_candidate" not in result.metrics


def test_trade_candidate_requires_conservative_one_interval():
    result = classify_extreme_funding_admission(
        _row(
            annualized_funding_estimate_pct=650.0,
            funding_rate_per_interval=0.008,
            expected_holding_intervals=2,
        )
    )
    assert result.trade_candidate_admitted is False
    assert result.reject_reason == "trade_requires_conservative_one_interval"


def test_research_admitted_records_trade_blocker():
    result = classify_extreme_funding_admission(
        _row(
            annualized_funding_estimate_pct=150.0,
            funding_rate_per_interval=0.006,
            basis_bps=5.0,
        )
    )
    assert result.research_shadow_admitted is True
    assert result.trade_candidate_admitted is False
    assert "research_only_net_edge_below_trade_gate" in result.metrics["trade_blockers"]


def test_missing_funding_or_basis_is_classified_safely():
    missing_funding = classify_extreme_funding_admission(_row(funding_rate_per_interval=None))
    assert missing_funding.anchor_event is False
    assert missing_funding.admission_layer == "no_anchor"
    assert missing_funding.reject_reason == "missing_funding_rate"

    missing_basis = classify_extreme_funding_admission(_row(basis_bps=None))
    assert missing_basis.anchor_event is True
    assert missing_basis.admission_layer == "anchor_only"
    assert missing_basis.reject_reason == "missing_basis"
