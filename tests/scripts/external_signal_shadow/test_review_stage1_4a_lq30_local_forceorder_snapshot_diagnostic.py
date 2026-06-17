import json

from scripts.external_signal_shadow.review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic import (
    main,
)


def test_lq30_review_renders_truth_level_and_next_action(tmp_path):
    summary_data = {
        "decision": "liquidation_diagnostic_weak",
        "next_action": "continue_accumulating_but_do_not_wait_for_90d",
        "liquidation_source_truth_level": "local_force_order_snapshot_rows_not_complete_tape",
        "complete_liquidation_tape_claim_allowed": False,
        "full_composite_claim_allowed": False,
        "alpha_interpretation_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "density_report": {
            "raw_history_days": 1.2,
            "liquidation_history_days": 1.2,
            "symbols_with_events": 2,
            "event_days": 1,
            "max_single_symbol_event_share": 0.8,
            "max_single_day_event_share": 1.0,
            "top_1_day_notional_share": 1.0,
            "top_3_days_notional_share": 1.0,
            "top_1_symbol_notional_share": 0.8,
        },
        "overlap_report": {
            "alignment_overlap_available": True,
            "data_alignment_overlap_window_count_15m": 5,
            "stress_condition_overlap_window_count_15m": 2,
            "data_alignment_overlap_event_days": 1,
            "stress_condition_overlap_event_days": 1,
            "symbols_with_alignment_overlap": 2,
            "alignment_policy": {
                "funding": "asof_latest_before_bucket_end_minus_lag",
                "oi": "asof_latest_before_bucket_end_with_staleness_limit",
                "price": "bucket_exact_or_covering"
            }
        },
        "imbalance_distribution": {
            "long_short_imbalance_distribution_15m": {"long_ratio": 0.6, "short_ratio": 0.4},
            "long_short_imbalance_distribution_1h": {"long_ratio": 0.6, "short_ratio": 0.4},
            "long_liquidation_notional_total": 6000.0,
            "short_liquidation_notional_total": 4000.0,
        },
        "source_quality_report": {
            "raw_row_count": 10,
            "raw_history_days": 1.2,
            "raw_recent_event_count_24h": 5,
            "duplicate_event_count": 0,
            "invalid_json_line_count": 0,
            "invalid_json_line_ratio": 0.0,
            "missing_timestamp_count": 0,
            "expected_symbol_coverage": 5,
            "actual_symbol_coverage": 2,
            "rotation_fragment_count": 0,
            "collector_gap_verifiable": False,
            "archive_gap_observations": "event_sparse_stream_cannot_prove_uptime"
        }
    }

    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps(summary_data), encoding="utf-8")

    review = tmp_path / "review.md"
    rc = main(["--summary", str(summary), "--output-review", str(review)])
    assert rc == 0
    assert review.exists()

    text = review.read_text(encoding="utf-8")
    assert "local_force_order_snapshot_rows_not_complete_tape" in text
    assert "complete_liquidation_tape_claim_allowed" in text
    assert "diagnostic-only" in text
    assert "SELL = long liquidation" in text
    assert "BUY = short liquidation" in text
    assert "notional = price * quantity" in text
    assert "source_quality_report" in text
    assert "asof_latest_before_bucket_end_minus_lag" in text
