import json
import os

import pytest

from scripts.external_signal_shadow.review_stage1_4e_deleveraging_proxy_sensitivity_review import (
    main,
)


@pytest.fixture
def temp_summary_and_review(tmp_path):
    summary_path = tmp_path / "summary.json"
    review_path = tmp_path / "review.md"

    # Mock summary JSON
    summary_data = {
        "deleveraging_proxy_15m": {
            "candidate_name": "deleveraging_proxy_15m",
            "decision": "deleveraging_proxy_survives_sensitivity_review",
            "secondary_status": "none",
            "events_detected_count": 120,
            "distinct_days_count": 25,
            "replayed_median_bps_1h": 5.0,
            "replayed_median_bps_4h": 12.0,
            "replayed_median_bps_12h": -2.0,
            "random_baseline_trials": 500,
            "random_baseline_4h_median_bps": 2.0,
            "baseline_sampling_failure_count": 0,
            "price_baseline_4h_median_bps": 1.0,
            "deleveraging_proxy_only": True,
            "liquidation_used": False,
            "force_order_used": False,
            "vendor_data_used": False,
            "liquidation_claim_allowed": False,
            "full_composite_claim_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "not_b_lite_restart": True,
            "previous_b_lite_crowding_only_branch_stopped": True,
            "stage1_5_allowed_only_as_filter": True,
            "fixture_run": False,
            "research_result_valid": True,
            "source_quality_summary": {
                "oi_source_quality": "exchange_reported_hourly_snapshot",
                "price_source_quality": "close_price_proxy_not_fill_price",
                "oi_data_granularity_minutes": 5.0,
                "price_data_granularity_minutes": 1.0,
                "oi_history_days": 180.0,
                "price_history_days": 180.0,
                "candidate_window_supported": True,
                "research_result_valid": True
            }
        },
        "deleveraging_proxy_1h": {
            "candidate_name": "deleveraging_proxy_1h",
            "decision": "deleveraging_proxy_failed",
            "secondary_status": "none",
            "events_detected_count": 10,
            "distinct_days_count": 5,
            "replayed_median_bps_1h": -1.0,
            "replayed_median_bps_4h": -5.0,
            "replayed_median_bps_12h": -10.0,
            "random_baseline_trials": 500,
            "random_baseline_4h_median_bps": 2.0,
            "baseline_sampling_failure_count": 0,
            "price_baseline_4h_median_bps": 1.0,
            "deleveraging_proxy_only": True,
            "liquidation_used": False,
            "force_order_used": False,
            "vendor_data_used": False,
            "liquidation_claim_allowed": False,
            "full_composite_claim_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "not_b_lite_restart": True,
            "previous_b_lite_crowding_only_branch_stopped": True,
            "stage1_5_allowed_only_as_filter": True,
            "fixture_run": False,
            "research_result_valid": True,
            "source_quality_summary": {
                "oi_source_quality": "exchange_reported_hourly_snapshot",
                "price_source_quality": "close_price_proxy_not_fill_price",
                "oi_data_granularity_minutes": 60.0,
                "price_data_granularity_minutes": 1.0,
                "oi_history_days": 180.0,
                "price_history_days": 180.0,
                "candidate_window_supported": True,
                "research_result_valid": True
            }
        }
    }

    summary_path.write_text(json.dumps(summary_data, indent=2))
    return str(summary_path), str(review_path)

def test_review_says_survives_only_allows_external_catalyst_filter_not_primary_signal(temp_summary_and_review):
    summary, review = temp_summary_and_review

    sys_args = [
        "--summary", summary,
        "--output-review", review,
    ]
    main(sys_args)

    assert os.path.exists(review)
    content = open(review, "r").read()


    # Core review assertions
    assert "deleveraging proxy sensitivity review" in content.lower() or "deleveraging proxy 敏感性审查" in content
    assert "not b-lite restart" in content.lower() or "不是 b-lite 重启" in content
    assert "stage 1.5" in content.lower()
    assert "filter" in content.lower() or "过滤器" in content
    assert "primary signal" in content.lower() or "主信号" in content
    assert "liquidation" in content.lower() or "清算" in content
    assert "forceorder" in content.lower() or "强制委托" in content or "force_order" in content.lower()


def test_review_does_not_call_invalid_real_result_conditionally_passed(tmp_path):
    summary_path = tmp_path / "summary.json"
    review_path = tmp_path / "review.md"
    summary_data = {
        "deleveraging_proxy_15m": {
            "decision": "deleveraging_proxy_inconclusive",
            "events_detected_count": 0,
            "distinct_days_count": 0,
            "replayed_median_bps_4h": 0.0,
            "random_baseline_4h_median_bps": 0.0,
            "price_baseline_4h_median_bps": 0.0,
            "research_result_valid": False,
            "research_result_notes": ["insufficient_history_duration"],
        },
        "deleveraging_proxy_1h": {
            "decision": "deleveraging_proxy_inconclusive",
            "events_detected_count": 0,
            "distinct_days_count": 0,
            "replayed_median_bps_4h": 0.0,
            "random_baseline_4h_median_bps": 0.0,
            "price_baseline_4h_median_bps": 0.0,
            "research_result_valid": False,
            "research_result_notes": ["insufficient_history_duration"],
        },
    }
    summary_path.write_text(json.dumps(summary_data), encoding="utf-8")

    main(["--summary", str(summary_path), "--output-review", str(review_path)])

    content = review_path.read_text(encoding="utf-8")
    assert "research_result_valid=false" in content
    assert "insufficient_history_duration" in content
    assert "条件通过" not in content
