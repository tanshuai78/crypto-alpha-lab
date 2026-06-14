from __future__ import annotations

import json
from pathlib import Path

from scripts.review_external_signal_shadow_stage1_3_candidate_discovery import main


def test_stage1_3_review_script_writes_chinese_markdown(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_3_fixture_smoke_completed",
        "next_action": "run_real_historical_bars_replay",
        "alpha_interpretation_allowed": False,
        "collector_expansion_allowed": False,
        "historical_venue": "binance_proxy",
        "venue_proxy_used": True,
        "fixture_run": True,
        "research_result_valid": False,
        "candidate_results": [
            {
                "candidate_name": "volume_spike_1h",
                "event_count": 120,
                "candidate_decision": "candidate_failed",
                "primary_blocker": "no_positive_baseline_excess",
                "symbols_with_events": 3,
                "event_days": 21,
                "baseline_excess_net_bps": -2.0,
                "median_net_return_after_50bps": -1.0,
                "left_tail_p05_after_50bps_vs_baseline_bps": -10.0,
                "top_5_positive_events_gross_profit_share": 0.25,
            }
        ],
    }))
    result = main(["--summary", str(summary), "--output", str(review)])
    assert result == 0
    text = review.read_text()
    assert "Stage 1.3 Candidate Signal Discovery Review" in text
    assert "不允许 alpha interpretation" in text
    assert "运行真实历史 bars replay" in text
    assert "volume_spike_1h" in text
    assert "no_positive_baseline_excess" in text
    assert "fixture 数据" in text
    assert "不能推出信号有效性结论" in text
