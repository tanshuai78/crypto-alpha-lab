import json

import pytest

from src.research.external_signal_shadow.stage1_5b_event_table_loader import (
    assert_stage1_5a_audit_passed,
    load_high_confidence_candidate_rows,
)


def test_load_high_confidence_candidate_rows_rejects_non_reviewed_rows(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "event_type_candidate": "futures_contract_launch",
        "manual_review_status": "review_rejected",
        "manual_review_required": True,
        "symbol": ["ABC"],
        "time": 1710921600000,
        "title": "Binance Futures Will Launch ABCUSDT",
        "url": "https://www.binance.com/en/support/announcement/x",
        "source_url": "https://www.binance.com/bapi/x",
        "source_name": "binance_official_announcements",
        "source_capture_method": "semi_auto_collector",
    }) + "\n")

    with pytest.raises(ValueError, match="manual_review_status"):
        load_high_confidence_candidate_rows(path)


def test_load_rejects_row_missing_time_field(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "event_type_candidate": "futures_contract_launch",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "symbol": ["ABC"],
        "title": "Binance Futures Will Launch ABCUSDT",
        "url": "https://www.binance.com/en/support/announcement/x",
        "source_url": "https://www.binance.com/bapi/x",
        "source_name": "binance_official_announcements",
        "source_capture_method": "semi_auto_collector",
    }) + "\n")

    with pytest.raises(ValueError, match="time"):
        load_high_confidence_candidate_rows(path)


def test_load_rejects_row_missing_url_field(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "event_type_candidate": "futures_contract_launch",
        "manual_review_required": True,
        "manual_review_status": "reviewed_high_confidence",
        "symbol": ["ABC"],
        "time": 1710921600000,
        "title": "Binance Futures Will Launch ABCUSDT",
        "source_url": "https://www.binance.com/bapi/x",
        "source_name": "binance_official_announcements",
        "source_capture_method": "semi_auto_collector",
    }) + "\n")

    with pytest.raises(ValueError, match="url"):
        load_high_confidence_candidate_rows(path)


def test_assert_stage1_5a_audit_passed_rejects_sparse_summary(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({
        "overall_decision": "source_audit_sparse_inconclusive",
        "research_result_valid": True,
        "source_decisions": {},
        "event_type_decisions": {},
    }))

    with pytest.raises(ValueError, match="source_audit_passed"):
        assert_stage1_5a_audit_passed(summary)


def test_assert_stage1_5a_audit_passed_returns_allowed_event_types(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({
        "overall_decision": "source_audit_passed",
        "research_result_valid": True,
        "source_decisions": {
            "binance_official_announcements_like_rows_source": {
                "decision": "source_audit_passed",
                "recommended_event_types_for_stage1_5b": [
                    "exchange_delisting_notice",
                    "futures_contract_launch",
                ],
            }
        },
        "event_type_decisions": {
            "exchange_delisting_notice": "source_audit_passed",
            "futures_contract_launch": "source_audit_passed",
            "margin_enablement": "source_audit_sparse_inconclusive",
        },
    }))

    allowed = assert_stage1_5a_audit_passed(summary)
    assert allowed == {"exchange_delisting_notice", "futures_contract_launch"}


def test_allowed_event_types_are_intersection_of_config_and_stage1_5a_recommendations(tmp_path):
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({
        "overall_decision": "source_audit_passed",
        "research_result_valid": True,
        "source_decisions": {
            "binance_official_announcements_like_rows_source": {
                "decision": "source_audit_passed",
                "recommended_event_types_for_stage1_5b": [
                    "futures_contract_launch",
                    "margin_enablement",
                ],
            }
        },
        "event_type_decisions": {
            "futures_contract_launch": "source_audit_passed",
            "margin_enablement": "source_audit_passed",
        },
    }))

    allowed = assert_stage1_5a_audit_passed(summary)
    assert allowed == {"futures_contract_launch"}
