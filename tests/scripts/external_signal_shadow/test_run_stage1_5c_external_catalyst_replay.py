import json
from unittest.mock import patch

from scripts.external_signal_shadow.run_stage1_5c_external_catalyst_replay import (
    _make_baseline_candidate_from_event,
    main,
)


def test_runner_debug_override_marks_research_invalid(tmp_path):
    event_path = tmp_path / "events.jsonl"
    stage1_5b_summary = tmp_path / "stage1_5b_summary.json"
    price_path = tmp_path / "price.jsonl"
    candidates_out = tmp_path / "candidates.jsonl"
    results_out = tmp_path / "results.jsonl"
    summary_out = tmp_path / "summary.json"

    stage1_5b_summary.write_text(json.dumps({
        "decision": "stage1_5b_event_table_ready",
        "replay_allowed": False,
        "stage1_5c_replay_candidate_allowed": False,
    }))
    event_path.write_text(json.dumps({
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "event_time_ms": 30 * 24 * 3600 * 1000,
        "available_at_ms": 30 * 24 * 3600 * 1000,
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "replay_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "directional_hypothesis": "undefined",
        "signed_direction": None,
    }) + "\n")
    bars = []
    for i in range(30 * 24 * 4 + 120):
        bars.append({
            "symbol": "ABCUSDT",
            "bar_start_ms": i * 900_000,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "quote_volume": 100_000_000,
        })
    price_path.write_text("\n".join(json.dumps(b) for b in bars) + "\n")

    args = [
        "run_stage1_5c_external_catalyst_replay.py",
        "--events-jsonl", str(event_path),
        "--stage1-5b-summary", str(stage1_5b_summary),
        "--price-jsonl", str(price_path),
        "--output-candidates-jsonl", str(candidates_out),
        "--output-results-jsonl", str(results_out),
        "--output-summary", str(summary_out),
        "--random-baseline-trials", "10",
    ]
    with patch("sys.argv", args):
        main()

    summary = json.loads(summary_out.read_text())
    assert summary["baseline_trials_override_used"] is True
    assert summary["research_result_valid"] is False
    assert summary["top_level_decision"] == "stage1_5c_replay_completed"
    assert summary["promising_cells"] == []
    assert summary["paper_trading_allowed"] is False
    assert summary["live_trading_allowed"] is False


def test_make_baseline_candidate_uses_real_entry_bar_open():
    event = {
        "symbol": "ABCUSDT",
        "event_type": "random_baseline_event",
        "signed_direction": 1,
        "event_time_ms": 0,
        "available_at_ms": 0,
    }
    price_index = {
        "ABCUSDT": [
            {"bar_start_ms": 0, "open": 100.0},
            {"bar_start_ms": 3_600_000, "open": 123.0},
            {"bar_start_ms": 18_000_000, "open": 130.0},
        ]
    }
    candidate = _make_baseline_candidate_from_event(
        event,
        price_index,
        entry_delay_hours=1,
        signed_mode="random_baseline",
    )
    assert candidate is not None
    assert candidate.entry_bar_start_ms == 3_600_000
    assert candidate.entry_price == 123.0
