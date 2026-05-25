import json

from scripts.replay_extreme_funding_candidates import build_candidate_replay_summary


def test_candidate_replay_summary_marks_funding_only_rows_as_missing_basis(tmp_path) -> None:
    path = tmp_path / "binance_doge_settled.jsonl"
    path.write_text(
        json.dumps(
            {
                "symbol": "DOGE/USDT",
                "funding_time_ms": 1000,
                "funding_rate": 0.008,
                "mark_price": 0.2,
                "annualized_pct": 650.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary = build_candidate_replay_summary([path], threshold_pct=100.0)
    assert summary["input_file_count"] == 1
    assert summary["segments_seen"] == 1
    assert summary["has_threshold_segments"] is True
    assert summary["status"] == "ok"
    assert summary["candidate_count"] == 0
    assert summary["reject_reason_counts"] == {"missing_basis": 1}
    assert summary["coverage_quality"] == "funding_only_insufficient_for_basis"


def test_candidate_replay_summary_marks_empty_input() -> None:
    summary = build_candidate_replay_summary([], threshold_pct=100.0)
    assert summary["input_file_count"] == 0
    assert summary["segments_seen"] == 0
    assert summary["candidate_count"] == 0
    assert summary["has_threshold_segments"] is False
    assert summary["status"] == "no_threshold_segments_or_no_input"
