from scripts.review_liquidation_shock_event_study import (
    evaluate_events,
    make_decision,
)


def test_evaluate_events_metrics():
    # Mock some evaluation results
    # 10 events:
    # 5m horizon: 8 expected direction, 2 opposite. Bias = 8 / 10 = 0.8
    # 10m horizon: 7 expected direction, 3 opposite. Bias = 0.7
    # 15m horizon: 4 expected direction, 6 opposite. Structural bias = max(4, 6) / 10 = 0.6
    eval_results = []
    for i in range(10):
        # 5m
        sign_5 = 1 if i < 8 else -1
        mm_5 = 1 if i < 6 else (-1 if i >= 8 else 0)
        dir_bps_5 = 15.0 if i < 8 else -15.0

        # 10m
        sign_10 = 1 if i < 7 else -1
        mm_10 = 1 if i < 5 else (-1 if i >= 7 else 0)
        dir_bps_10 = 20.0 if i < 7 else -20.0

        # 15m
        sign_15 = 1 if i < 4 else -1
        mm_15 = 1 if i < 3 else (-1 if i >= 4 else 0)
        dir_bps_15 = -5.0 if i >= 4 else 5.0

        eval_results.append(
            {
                "symbol": "BTC/USDT" if i < 5 else "ETH/USDT",
                "shock_bar_start_ms": 1716800000000 + i * 3600000,
                "expected_price_direction": "down",
                "bps_changes": {5: dir_bps_5, 10: dir_bps_10, 15: dir_bps_15},
                "directional_bps": {5: dir_bps_5, 10: dir_bps_10, 15: dir_bps_15},
                "sign_directions": {5: sign_5, 10: sign_10, 15: sign_15},
                "min_move_directions": {5: mm_5, 10: mm_10, 15: mm_15},
            }
        )

    # Total duration = (9 * 3600000) ms = 9 hours = 0.375 days
    summary = evaluate_events(eval_results, total_duration_days=10.0)

    assert summary["event_count"] == 10
    assert summary["events_per_24h"] == 1.0  # 10 / 10 = 1.0
    assert summary["symbol_distribution"] == {"BTC/USDT": 5, "ETH/USDT": 5}
    assert summary["directional_bias_by_horizon"][5] == 0.8
    assert summary["directional_bias_by_horizon"][10] == 0.7
    assert summary["directional_bias_by_horizon"][15] == 0.6

    # Min-move filtered bias:
    # 5m: successes=6, failures=2. Bias = 6 / 8 = 0.75
    # 10m: successes=5, failures=3. Bias = 5 / 8 = 0.625
    # 15m: successes=3, failures=6. Structural bias = max(3, 6) / 9 = 0.666...
    assert summary["minimum_move_filtered_direction_distribution"][5]["up"] == 6
    assert summary["minimum_move_filtered_direction_distribution"][5]["down"] == 2
    assert summary["minimum_move_filtered_direction_distribution"][5]["flat"] == 2
    assert summary["minimum_move_filtered_directional_bias"][5] == 0.75
    assert round(summary["minimum_move_filtered_directional_bias"][15], 3) == 0.667


def test_make_decision_rules():
    # Proceed path
    summary = {
        "event_count": 12,
        "events_per_24h": 1.5,
        "symbol_distribution": {"BTC/USDT": 6, "ETH/USDT": 6},
        "directional_bias_by_horizon": {5: 0.58, 10: 0.57, 15: 0.52},
        "minimum_move_filtered_directional_bias": {5: 0.59, 10: 0.58, 15: 0.51},
        "median_response_bps_by_horizon": {5: 5.0, 10: 6.0, 15: 1.0},
    }

    decision, reasons, failed_checks, next_action = make_decision(summary)
    assert decision == "continue_to_context_bucketing"
    assert len(failed_checks) == 0
    assert next_action == "proceed_to_context_bucketing"

    # Fail path: too few events
    summary["event_count"] = 5
    # Adjust symbol distribution so concentration doesn't fail
    summary["symbol_distribution"] = {"BTC/USDT": 2, "ETH/USDT": 3}
    decision, reasons, failed_checks, next_action = make_decision(summary)
    assert decision == "insufficient_event_density"
    assert any("event_count < 10" in x for x in failed_checks)
    assert next_action == "improve_data_or_event_density"

    # Fail path: no directional bias (bias < 0.55 on all horizons)
    summary["event_count"] = 12
    summary["symbol_distribution"] = {"BTC/USDT": 6, "ETH/USDT": 6}
    summary["directional_bias_by_horizon"] = {5: 0.51, 10: 0.52, 15: 0.49}
    decision, reasons, failed_checks, next_action = make_decision(summary)
    assert decision == "retire_liquidation_shock_event_study"
    assert any("no adjacent horizons passed criteria" in x for x in failed_checks)
    assert next_action == "stop_liquidation_shock_line"
