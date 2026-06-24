import json
from unittest.mock import patch

from scripts.external_signal_shadow.review_stage1_5c_external_catalyst_replay import main


def test_review_states_research_only_and_no_alpha(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [],
        "cell_summaries": {
            "futures_contract_launch|long_attention|1h|G2_price_coverage_only": {
                "cell_decision": "stage1_5c_cell_failed",
                "cell_event_count": 40,
                "cell_event_days": 12,
                "cell_symbols_with_events": 4,
                "median_net_return_after_50bps_4h": -5.0,
                "blockers": ["median_net_return_after_50bps_not_positive"]
            }
        },
        "random_baseline_trials": 500,
        "blockers": ["median_net_return_after_50bps_not_positive"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "execution_engine_allowed": False,
    }))
    args = [
        "review_stage1_5c_external_catalyst_replay.py",
        "--summary", str(summary),
        "--output-review", str(review),
    ]
    with patch("sys.argv", args):
        main()
    content = review.read_text()
    assert "Stage 1.5C" in content
    assert "research-only" in content
    assert "paper_trading_allowed" in content
    assert "live_trading_allowed" in content
    assert "alpha_interpretation_allowed" in content
    assert "median_net_return_after_50bps_not_positive" in content
    assert "-5.0" in content or "-5" in content
    for placeholder in ["TODO", "TBD", "placeholder", "FIXME"]:
        assert placeholder not in content
