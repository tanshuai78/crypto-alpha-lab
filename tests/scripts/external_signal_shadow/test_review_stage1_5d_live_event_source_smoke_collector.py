import json
from unittest.mock import patch

from scripts.external_signal_shadow.review_stage1_5d_live_event_source_smoke_collector import main


def test_review_contains_decision_and_safety_flags(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_5d_smoke_observation_in_progress",
        "event_detection_validated": False,
        "fixture_run": True,
        "debug_short_run": True,
        "observation_hours": 0.0,
        "research_result_valid": False,
        "poll_count": 1,
        "new_futures_launch_event_count": 0,
        "raw_futures_launch_article_count": 2,
        "symbol_parsed_event_count": 1,
        "symbol_parse_failed_count": 1,
        "deduped_new_event_count": 1,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "blockers": [],
    }))
    args = ["review_stage1_5d_live_event_source_smoke_collector.py", "--summary", str(summary), "--output-review", str(review)]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 0
    text = review.read_text()
    assert "stage1_5d_smoke_observation_in_progress" in text
    assert "event_detection_validated" in text
    assert "research_result_valid" in text
    assert "raw_futures_launch_article_count" in text
    assert "symbol_parse_failed_count" in text
    assert "deduped_new_event_count" in text
    assert "paper_trading_allowed" in text
    for forbidden in ["TODO", "TBD", "placeholder", "FIXME"]:
        assert forbidden not in text
