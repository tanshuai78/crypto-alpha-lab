import json
from unittest.mock import patch

import pytest

from scripts.external_signal_shadow.run_stage1_5b_minimal_historical_event_table import main


def test_runner_writes_raw_normalized_and_summary(tmp_path):
    input_jsonl = tmp_path / "high_confidence.jsonl"
    audit_summary = tmp_path / "stage1_5a_summary.json"
    raw_out = tmp_path / "raw.jsonl"
    norm_out = tmp_path / "normalized.jsonl"
    summary_out = tmp_path / "summary.json"

    input_jsonl.write_text(json.dumps({
        "event_type_candidate": "futures_contract_launch",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "source_capture_method": "semi_auto_collector",
        "source_line": 1,
        "source_name": "binance_official_announcements",
        "source_url": "https://www.binance.com/bapi/x",
        "symbol": ["ABC"],
        "time": 1710921600000,
        "title": "Binance Futures Will Launch ABCUSDT Perpetual Contract",
        "url": "https://www.binance.com/en/support/announcement/x",
    }) + "\n")
    audit_summary.write_text(json.dumps({
        "overall_decision": "source_audit_passed",
        "research_result_valid": True,
        "source_decisions": {
            "binance_official_announcements_like_rows_source": {
                "decision": "source_audit_passed",
                "recommended_event_types_for_stage1_5b": ["futures_contract_launch"],
            }
        },
        "event_type_decisions": {"futures_contract_launch": "source_audit_passed"},
    }))

    args = [
        "run_stage1_5b_minimal_historical_event_table.py",
        "--input-jsonl", str(input_jsonl),
        "--stage1-5a-summary", str(audit_summary),
        "--output-raw-jsonl", str(raw_out),
        "--output-normalized-jsonl", str(norm_out),
        "--output-summary", str(summary_out),
    ]
    with patch("sys.argv", args):
        main()

    assert raw_out.exists()
    assert norm_out.exists()
    assert summary_out.exists()
    normalized = [json.loads(line) for line in norm_out.read_text().splitlines()]
    assert normalized[0]["symbol"] == "ABCUSDT"
    assert normalized[0]["replay_allowed"] is False
    assert normalized[0]["stage1_5c_review_pending"] is True
    assert normalized[0]["stage1_5c_replay_candidate_allowed"] is False
    assert normalized[0]["market_pair_existence_verified"] is False
    assert normalized[0]["price_history_coverage_verified"] is False
    assert normalized[0]["tradability_verified"] is False
    assert normalized[0]["directional_hypothesis"] == "undefined"
    assert normalized[0]["signed_direction"] is None


def test_runner_exits_nonzero_and_writes_failed_summary_when_stage1_5a_not_passed(tmp_path):
    input_jsonl = tmp_path / "high_confidence.jsonl"
    audit_summary = tmp_path / "stage1_5a_summary.json"
    raw_out = tmp_path / "raw.jsonl"
    norm_out = tmp_path / "normalized.jsonl"
    summary_out = tmp_path / "summary.json"

    input_jsonl.write_text(json.dumps({
        "event_type_candidate": "futures_contract_launch",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "source_capture_method": "semi_auto_collector",
        "source_line": 1,
        "source_name": "binance_official_announcements",
        "source_url": "https://www.binance.com/bapi/x",
        "symbol": ["ABC"],
        "time": 1710921600000,
        "title": "Binance Futures Will Launch ABCUSDT Perpetual Contract",
        "url": "https://www.binance.com/en/support/announcement/x",
    }) + "\n")
    audit_summary.write_text(json.dumps({
        "overall_decision": "source_audit_sparse_inconclusive",
        "research_result_valid": True,
        "source_decisions": {},
        "event_type_decisions": {},
    }))

    args = [
        "run_stage1_5b_minimal_historical_event_table.py",
        "--input-jsonl", str(input_jsonl),
        "--stage1-5a-summary", str(audit_summary),
        "--output-raw-jsonl", str(raw_out),
        "--output-normalized-jsonl", str(norm_out),
        "--output-summary", str(summary_out),
    ]
    with patch("sys.argv", args), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    summary = json.loads(summary_out.read_text())
    assert summary["decision"] == "stage1_5b_event_table_failed"
    assert "source_audit_not_passed" in summary["blockers"]


def test_runner_exits_nonzero_when_unsupported_event_type_is_present(tmp_path):
    input_jsonl = tmp_path / "high_confidence.jsonl"
    audit_summary = tmp_path / "stage1_5a_summary.json"
    raw_out = tmp_path / "raw.jsonl"
    norm_out = tmp_path / "normalized.jsonl"
    summary_out = tmp_path / "summary.json"

    input_jsonl.write_text(json.dumps({
        "event_type_candidate": "margin_enablement",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "source_capture_method": "semi_auto_collector",
        "source_line": 1,
        "source_name": "binance_official_announcements",
        "source_url": "https://www.binance.com/bapi/x",
        "symbol": ["ABC"],
        "time": 1710921600000,
        "title": "Binance Adds ABC to Margin",
        "url": "https://www.binance.com/en/support/announcement/x",
    }) + "\n")
    audit_summary.write_text(json.dumps({
        "overall_decision": "source_audit_passed",
        "research_result_valid": True,
        "source_decisions": {
            "binance_official_announcements_like_rows_source": {
                "decision": "source_audit_passed",
                "recommended_event_types_for_stage1_5b": ["futures_contract_launch"],
            }
        },
        "event_type_decisions": {"futures_contract_launch": "source_audit_passed"},
    }))

    args = [
        "run_stage1_5b_minimal_historical_event_table.py",
        "--input-jsonl", str(input_jsonl),
        "--stage1-5a-summary", str(audit_summary),
        "--output-raw-jsonl", str(raw_out),
        "--output-normalized-jsonl", str(norm_out),
        "--output-summary", str(summary_out),
    ]
    with patch("sys.argv", args), pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    summary = json.loads(summary_out.read_text())
    assert summary["decision"] == "stage1_5b_event_table_failed"
    assert any("unsupported_event_type" in blocker for blocker in summary["blockers"])
