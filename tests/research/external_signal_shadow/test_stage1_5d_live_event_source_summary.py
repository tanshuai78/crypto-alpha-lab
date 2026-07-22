from src.research.external_signal_shadow.stage1_5d_live_event_source_summary import (
    build_smoke_summary,
)


def test_short_live_smoke_is_observation_in_progress_not_operational_pass():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True, "heartbeat_gap": False}],
        events=[],
        request_manifest=[],
        fixture_run=False,
        debug_short_run=True,
        observation_hours=0.05,
    )
    assert summary["decision"] == "stage1_5d_smoke_observation_in_progress"
    assert summary["event_detection_validated"] is False
    assert summary["research_result_valid"] is False


def test_fixture_zero_event_smoke_marks_research_result_valid_false():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True, "heartbeat_gap": False}],
        events=[],
        request_manifest=[],
        fixture_run=True,
        debug_short_run=True,
        observation_hours=0.0,
    )
    assert summary["decision"] == "stage1_5d_smoke_observation_in_progress"
    assert summary["fixture_run"] is True
    assert summary["research_result_valid"] is False


def test_zero_event_24h_stable_polling_is_operational_unvalidated():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True, "heartbeat_gap": False} for _ in range(24)],
        events=[],
        request_manifest=[],
        fixture_run=False,
        debug_short_run=False,
        observation_hours=24.0,
    )
    assert summary["decision"] == "stage1_5d_operational_pass_event_detection_unvalidated"
    assert summary["event_detection_validated"] is False
    assert summary["research_result_valid"] is True


def test_event_detection_passed_requires_event_and_first_bar_status():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True, "heartbeat_gap": False}],
        events=[{"event_type": "futures_contract_launch", "symbol_parse_status": "parsed", "first_futures_bar_status": "found"}],
        request_manifest=[],
        fixture_run=False,
        debug_short_run=False,
        observation_hours=1.0,
    )
    assert summary["decision"] == "stage1_5d_event_detection_passed"
    assert summary["event_detection_validated"] is True
    assert summary["research_result_valid"] is True


def test_summary_splits_raw_symbol_failed_and_deduped_counts():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True, "heartbeat_gap": False}],
        events=[
            {"event_id": "e1", "event_type": "futures_contract_launch", "symbols": ["ABCUSDT"], "first_futures_bar_status": "not_yet_available"},
            {"event_id": "e2", "event_type": "futures_contract_launch", "symbols": [], "first_futures_bar_status": "not_yet_available"},
        ],
        request_manifest=[],
        fixture_run=True,
        debug_short_run=True,
        observation_hours=0.0,
        counters={
            "raw_futures_launch_article_count": 4,
            "symbol_parsed_event_count": 2,
            "symbol_parse_failed_count": 2,
            "deduped_new_event_count": 2,
        },
    )
    assert summary["raw_futures_launch_article_count"] == 4
    assert summary["symbol_parsed_event_count"] == 2
    assert summary["symbol_parse_failed_count"] == 2
    assert summary["deduped_new_event_count"] == 2
    assert summary["new_futures_launch_event_count"] == 2


def test_upstream_invalid_makes_smoke_invalid():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": False, "blockers": ["missing"]},
        heartbeats=[],
        events=[],
        request_manifest=[],
        fixture_run=False,
        debug_short_run=False,
        observation_hours=0.0,
    )
    assert summary["decision"] == "stage1_5d_smoke_invalid"
    assert "upstream_evidence_missing_or_invalid" in summary["blockers"]


def test_summary_includes_detail_fallback_counters():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True}],
        events=[],
        request_manifest=[],
        fixture_run=True,
        debug_short_run=True,
        observation_hours=0.0,
        counters={
            "detail_fetch_attempted_count": 2,
            "detail_fetch_success_count": 1,
            "detail_fetch_failed_count": 1,
            "detail_fetch_budget_deferred_count": 1,
            "detail_fetch_url_rejected_count": 0,
            "detail_symbol_extracted_count": 1,
            "detail_symbol_parse_failed_count": 1,
            "title_symbol_extracted_count": 3,
            "symbol_empty_event_count": 1,
            "candidate_validation_pending_count": 5,
            "candidate_validation_success_count": 4,
            "candidate_validation_expired_count": 3,
            "u_settlement_symbol_extracted_count": 2,
            "pre_launch_validation_deferred_count": 1,
            "detail_pending_retry_count": 3,
            "detail_empty_payload_count": 1,
            "detail_http_not_ready_count": 2,
            "detail_terminal_failed_count": 1,
            "detail_transient_timeout_count": 4,
            "detail_degraded_recent_retry_count": 5,
            "detail_fetch_fallback_attempt_count": 6,
            "detail_fetch_fallback_success_count": 7,
            "detail_fetch_attempt_manifest_mismatch_count": 0,
        },
    )

    assert summary["detail_fetch_attempted_count"] == 2
    assert summary["detail_symbol_extracted_count"] == 1
    assert summary["title_symbol_extracted_count"] == 3
    assert summary["candidate_validation_pending_count"] == 5
    assert summary["candidate_validation_success_count"] == 4
    assert summary["candidate_validation_expired_count"] == 3
    assert summary["u_settlement_symbol_extracted_count"] == 2
    assert summary["pre_launch_validation_deferred_count"] == 1
    assert summary["detail_pending_retry_count"] == 3
    assert summary["detail_empty_payload_count"] == 1
    assert summary["detail_http_not_ready_count"] == 2
    assert summary["detail_terminal_failed_count"] == 1
    assert summary["detail_transient_timeout_count"] == 4
    assert summary["detail_degraded_recent_retry_count"] == 5
    assert summary["detail_fetch_fallback_attempt_count"] == 6
    assert summary["detail_fetch_fallback_success_count"] == 7
    assert summary["detail_fetch_attempt_manifest_mismatch_count"] == 0


def test_summary_includes_detail_retry_overdue_diagnostics():
    summary = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True}],
        events=[],
        request_manifest=[],
        fixture_run=True,
        debug_short_run=True,
        observation_hours=0.0,
        counters={
            "detail_retry_overdue_pending_count": 1,
            "detail_retry_overdue_attempted_count": 1,
            "detail_retry_overdue_never_attempted_count": 0,
            "detail_retry_due_timestamp_missing_count": 0,
            "detail_attempt_manifest_mismatch_count": 0,
            "detail_retry_oldest_overdue_ms": 70 * 60 * 1000,
            "detail_retry_overdue_warn_active": True,
            "detail_retry_overdue_hard_warn_active": False,
            "detail_retry_overdue_selected_total": 1,
            "detail_retry_overdue_deferred_total": 2,
            "detail_retry_overdue_retry_cycle_total": 1,
        },
    )
    assert summary["detail_retry_overdue_pending_count"] == 1
    assert summary["detail_retry_overdue_attempted_count"] == 1
    assert summary["detail_retry_overdue_never_attempted_count"] == 0
    assert summary["detail_retry_due_timestamp_missing_count"] == 0
    assert summary["detail_attempt_manifest_mismatch_count"] == 0
    assert summary["detail_retry_oldest_overdue_ms"] == 70 * 60 * 1000
    assert summary["detail_retry_overdue_warn_active"] is True
    assert summary["detail_retry_overdue_hard_warn_active"] is False
    assert summary["detail_retry_overdue_selected_total"] == 1
    assert summary["detail_retry_overdue_deferred_total"] == 2
    assert summary["detail_retry_overdue_retry_cycle_total"] == 1


def test_overdue_pending_summary_is_current_gauge_not_cumulative_counter():
    summary1 = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True}],
        events=[],
        request_manifest=[],
        fixture_run=True,
        debug_short_run=True,
        observation_hours=0.0,
        counters={"detail_retry_overdue_pending_count": 1},
    )
    summary2 = build_smoke_summary(
        upstream_evidence={"upstream_evidence_valid": True, "blockers": []},
        heartbeats=[{"poll_success": True}],
        events=[],
        request_manifest=[],
        fixture_run=True,
        debug_short_run=True,
        observation_hours=0.0,
        counters={"detail_retry_overdue_pending_count": 1},
    )
    assert summary1["detail_retry_overdue_pending_count"] == 1
    assert summary2["detail_retry_overdue_pending_count"] == 1
