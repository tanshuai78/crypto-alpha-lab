from typing import Any

from scripts.review_trend_liquidation_cascade import (
    build_cascade_shadow_summary,
    build_data_source_comparison,
    build_route_decision_snapshot,
    run_cascade_sensitivity,
)
from src.research.trend_liquidation_cascade_review import (
    LiquidationCascadeReviewThresholds,
    classify_liquidation_cascade_for_review,
)


def _row(**overrides: Any) -> dict[str, Any]:
    row = {
        "timestamp_ms": 1710000000000,
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "close_price": 100000.0,
        "return_1h_pct": 2.5,
        "vol_1h_pct": 3.0,
        "vol_baseline_30d_pct": 1.0,
        "oi_change_1h_pct": -3.0,
        "volume_24h_usdt": 1_000_000_000.0,
        "estimated_slippage_bps": 4.0,
        "data_age_sec": 0.0,
        "long_liquidation_notional_1h_usdt": 0.0,
        "short_liquidation_notional_1h_usdt": 15_000_000.0,
    }
    row.update(overrides)
    return row


def test_data_source_comparison_reports_forceorder_partial_quality():
    comparison = build_data_source_comparison(coverage_hours=50.0, route_b_available=False)
    route_a = comparison["route_a"]
    assert route_a["available"] is True
    assert route_a["source_quality"] == "self_collected_partial_history"
    assert route_a["coverage_hours"] == 50.0
    assert route_a["liquidation_notional_semantics"] == "partial_snapshot_lower_bound"
    assert route_a["allowed_decisions_if_only_route_a"] == ["continue_data_route_upgrade"]


def test_data_source_comparison_reports_missing_third_party_as_upgrade_gap():
    comparison = build_data_source_comparison(coverage_hours=50.0, route_b_available=False)
    route_b = comparison["route_b"]
    assert route_b["available"] is False
    assert route_b["quality"] == "not_connected"


def test_data_source_comparison_includes_route_b_feasibility_candidates():
    feasibility = {
        "vendor_candidates": [
            {
                "vendor": "coinalyze",
                "api_access": "unavailable",
                "requires_paid_plan": False,
                "granularity": "1hour",
                "exchange_coverage": ["binance"],
                "symbol_coverage": ["BTC/USDT"],
                "historical_depth_days": 80,
                "can_support_replay": True,
                "blocker": "requires_coinalyze_api_key",
            }
        ]
    }
    comparison = build_data_source_comparison(
        coverage_hours=50.0,
        route_b_available=False,
        route_b_feasibility=feasibility,
    )
    route_b = comparison["route_b"]
    assert route_b["vendor_candidates"] == feasibility["vendor_candidates"]
    assert route_b["quality"] == "not_connected"


def test_data_source_comparison_keeps_routes_separate():
    comparison = build_data_source_comparison(coverage_hours=100.0, route_b_available=True, overlap_count=5)
    assert comparison["route_a"]["available"] is True
    assert comparison["route_b"]["available"] is True
    assert comparison["route_c"]["available"] is True


def test_route_a_short_partial_coverage_cannot_retire_strategy():
    comparison = build_data_source_comparison(coverage_hours=498.0, route_b_available=False)
    decision = build_route_decision_snapshot(comparison)
    assert decision == "route_b_unavailable_no_key"


def test_route_b_joined_rows_take_precedence_over_missing_env_key():
    comparison = build_data_source_comparison(
        coverage_hours=498.0,
        route_a_available=False,
        route_b_joined_count=2393,
        route_b_coverage_hours=1499.0,
    )
    decision = build_route_decision_snapshot(comparison, overlap_count=0, replay_median_net_pnl=0.0)
    assert comparison["route_b"]["available"] is True
    assert comparison["route_b"]["route_b_status"] == "api_ok_non_empty_rows"
    assert decision == "route_b_available_but_no_overlap"


def test_review_uses_route_b_hourly_history_when_provided(tmp_path):
    import json

    from scripts.review_trend_liquidation_cascade import main

    rows_file = tmp_path / "rows.jsonl"
    row_data = _row(timestamp_ms=1710000000000, symbol="BTC/USDT", close_price=100000.0)
    future_row = _row(timestamp_ms=1710000000000 + 3600000, symbol="BTC/USDT", close_price=101000.0)
    with open(rows_file, "w") as f:
        f.write(json.dumps(row_data) + "\n")
        f.write(json.dumps(future_row) + "\n")

    hourly_file = tmp_path / "hourly_b.jsonl"
    hourly_b_data = {
        "symbol": "BTC/USDT",
        "hour_bucket_ms": 1710000000000,
        "liquidation_notional_1h_usdt": 50000.0,
        "long_liquidation_notional_1h_usdt": 10000.0,
        "short_liquidation_notional_1h_usdt": 40000.0,
        "liquidation_source": "coinalyze_liquidation_history",
        "source_quality": "historical_vendor_dataset",
    }
    with open(hourly_file, "w") as f:
        f.write(json.dumps(hourly_b_data) + "\n")

    route_out = tmp_path / "route.json"
    summary_out = tmp_path / "summary.json"
    sensitivity_out = tmp_path / "sensitivity.json"

    argv = [
        "--rows-input", str(rows_file),
        "--third-party-hourly-input", str(hourly_file),
        "--route-summary-output", str(route_out),
        "--summary-output", str(summary_out),
        "--sensitivity-output", str(sensitivity_out),
    ]

    import os
    os.environ["COINALYZE_API_KEY"] = "mock_key"
    try:
        exit_code = main(argv)
        assert exit_code == 0
    finally:
        if "COINALYZE_API_KEY" in os.environ:
            del os.environ["COINALYZE_API_KEY"]

    with open(route_out) as f:
        comparison = json.load(f)

    assert comparison["route_b"]["available"] is True
    assert comparison["route_b"]["joined_count"] > 0


def test_data_source_comparison_marks_route_b_available_when_hourly_rows_exist():
    comparison = build_data_source_comparison(
        coverage_hours=50.0,
        route_b_joined_count=10,
        route_b_status="api_ok_non_empty_rows",
        route_b_coverage_hours=1499.0,
    )
    route_b = comparison["route_b"]
    assert route_b["available"] is True
    assert route_b["joined_count"] == 10
    assert route_b["source"] == "coinalyze_liquidation_history"
    assert route_b["quality"] == "historical_vendor_dataset"
    assert route_b["vendor"] == "coinalyze"
    assert route_b["route_b_status"] == "api_ok_non_empty_rows"
    assert route_b["coverage_hours"] == 1499.0


def test_route_c_available_only_when_route_a_and_route_b_overlap_on_symbol_hour():
    comp1 = build_data_source_comparison(
        coverage_hours=50.0,
        route_a_available=True,
        route_b_available=True,
        overlap_count=5,
    )
    assert comp1["route_c"]["available"] is True
    assert comp1["route_c"]["overlap_symbol_hour_count"] == 5

    comp2 = build_data_source_comparison(
        coverage_hours=50.0,
        route_a_available=True,
        route_b_available=True,
        overlap_count=0,
    )
    assert comp2["route_c"]["available"] is False
    assert comp2["route_c"]["overlap_symbol_hour_count"] == 0

    comp3 = build_data_source_comparison(
        coverage_hours=50.0,
        route_a_available=False,
        route_b_available=True,
        overlap_count=5,
    )
    assert comp3["route_c"]["available"] is False


def test_cascade_shadow_uses_only_accepted_entries():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT", close_price=100000.0),
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.2, vol_1h_pct=1.0),
        _row(timestamp_ms=3000, symbol="ETH/USDT", close_price=100.0, vol_1h_pct=1.0),
    ]
    summary = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12, hypothesis="continuation")
    assert summary["entry_event_count"] == 1
    assert summary["shadow_trade_count"] == 1
    assert summary["holding_hours"] == 12


def test_cascade_shadow_path_uses_same_symbol_and_future_only():
    rows = [
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=100000.0),
        # past row for BTC
        _row(timestamp_ms=1500, symbol="BTC/USDT", close_price=90000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
        # future row for BTC
        _row(timestamp_ms=2500, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
        # future row for ETH (cross-symbol)
        _row(timestamp_ms=2600, symbol="ETH/USDT", close_price=110.0, return_1h_pct=0.1, vol_1h_pct=1.0),
    ]
    summary = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12, hypothesis="continuation")
    assert summary["shadow_trade_count"] == 1
    assert summary["accepted_entries_with_path_count"] == 1


def test_cascade_outputs_dual_cost_and_holding_hours():
    # Tested through scripts execution or build_cascade_shadow_summary structures
    rows = [_row()]
    summary = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=4, hypothesis="continuation")
    assert "mean_net_pnl_bps" in summary
    assert "median_net_pnl_bps" in summary


def test_cascade_sensitivity_does_not_mutate_live_config():
    before = classify_liquidation_cascade_for_review(_row())
    run_cascade_sensitivity([_row()], threshold_sets=[LiquidationCascadeReviewThresholds.moderately_relaxed()])
    after = classify_liquidation_cascade_for_review(_row())
    assert before == after


def test_shadow_outputs_continuation_and_mean_reversion_separately():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT", close_price=100000.0),
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
    ]
    cont = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12, hypothesis="continuation")
    rev = build_cascade_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12, hypothesis="mean_reversion")

    # In continuation hypothesis: BUY pressure (short liq) -> Enter LONG -> Price goes to 101000 -> Profit
    assert cont["shadow_trade_count"] == 1
    assert cont["mean_net_pnl_bps"] > 0

    # In mean reversion hypothesis: BUY pressure -> Enter SHORT -> Price goes to 101000 -> Loss
    assert rev["shadow_trade_count"] == 1
    assert rev["mean_net_pnl_bps"] < 0


def test_review_route_b_only_keeps_route_a_unavailable_and_route_b_metadata(tmp_path, monkeypatch):
    import json

    from scripts.review_trend_liquidation_cascade import main

    rows_file = tmp_path / "rows.jsonl"
    row_data = _row(timestamp_ms=1710000000000, symbol="BTC/USDT", close_price=100000.0)
    future_row = _row(timestamp_ms=1710000000000 + 3600000, symbol="BTC/USDT", close_price=101000.0)
    with open(rows_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(row_data) + "\n")
        f.write(json.dumps(future_row) + "\n")

    hourly_file = tmp_path / "hourly_b.jsonl"
    with open(hourly_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "symbol": "BTC/USDT",
            "hour_bucket_ms": 1710000000000,
            "liquidation_notional_1h_usdt": 50000.0,
            "long_liquidation_notional_1h_usdt": 10000.0,
            "short_liquidation_notional_1h_usdt": 40000.0,
            "liquidation_source": "coinalyze_liquidation_history",
            "source_quality": "historical_vendor_dataset",
            "liquidation_notional_semantics": "vendor_reported_hourly_liquidation_notional",
        }) + "\n")
        f.write(json.dumps({
            "symbol": "BTC/USDT",
            "hour_bucket_ms": 1710000000000 + 3600000,
            "liquidation_notional_1h_usdt": 60000.0,
            "long_liquidation_notional_1h_usdt": 15000.0,
            "short_liquidation_notional_1h_usdt": 45000.0,
            "liquidation_source": "coinalyze_liquidation_history",
            "source_quality": "historical_vendor_dataset",
            "liquidation_notional_semantics": "vendor_reported_hourly_liquidation_notional",
        }) + "\n")

    route_out = tmp_path / "route.json"
    summary_out = tmp_path / "summary.json"
    sensitivity_out = tmp_path / "sensitivity.json"

    argv = [
        "--rows-input", str(rows_file),
        "--third-party-hourly-input", str(hourly_file),
        "--route-summary-output", str(route_out),
        "--summary-output", str(summary_out),
        "--sensitivity-output", str(sensitivity_out),
    ]

    monkeypatch.setenv("COINALYZE_API_KEY", "mock_key")
    exit_code = main(argv)
    assert exit_code == 0

    with open(route_out, encoding="utf-8") as f:
        comparison = json.load(f)
    with open(summary_out, encoding="utf-8") as f:
        summary = json.load(f)

    assert comparison["route_a"]["available"] is False
    assert comparison["route_a"]["joined_count"] == 0
    assert comparison["route_b"]["available"] is True
    assert comparison["route_b"]["coverage_hours"] == 1.0
    assert summary["liquidation_history_join_summary"]["route_b_join_details"]["liquidation_history_source"] == "coinalyze_liquidation_history"
    assert summary["liquidation_history_join_summary"]["route_b_join_details"]["liquidation_history_source_quality"] == "historical_vendor_dataset"
    assert summary["liquidation_history_join_summary"]["route_b_join_details"]["liquidation_notional_semantics"] == "vendor_reported_hourly_liquidation_notional"
