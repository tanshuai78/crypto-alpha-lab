from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
    EventSymbolState,
)
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_summary import (
    build_live_depth_observer_summary,
    compute_request_success_rate,
    derive_stage1_5f_decision,
)


def test_bootstrap_summary_never_marks_research_result_valid():
    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_bootstrap_watermark_only",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=False,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path=None,
        stage1_5e_context_missing=True,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=0,
        active_states=[],
        completed_states=[],
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[],
        heartbeat_rows=[],
    )
    assert summary.decision == "stage1_5f_observer_bootstrap_watermark_only"
    assert summary.research_result_valid is False
    assert summary.execution_feasibility_claim_allowed is False


def test_running_no_new_event_summary_is_not_research_valid():
    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_running_no_new_event",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=0,
        active_states=[],
        completed_states=[],
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[],
        heartbeat_rows=[],
    )
    assert summary.decision == "stage1_5f_observer_running_no_new_event"
    assert summary.research_result_valid is False


def test_depth_evidence_collected_requires_completed_observation():
    # Valid completed observation exists, request rate is healthy, etc.
    completed = [
        EventSymbolState(
            event_symbol_id="id1",
            event_id="e1",
            symbol="BTCUSDT",
            status="completed",
            research_result_valid=True,
        )
    ]
    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_depth_evidence_collected",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=1,
        active_states=[],
        completed_states=completed,
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[{"http_status": 200}], # success rate = 1.0
        heartbeat_rows=[{"poll_index": 1}],
    )
    assert summary.decision == "stage1_5f_observer_depth_evidence_collected"
    assert summary.research_result_valid is True
    # Still, compliance flags must be False
    assert summary.paper_trading_allowed is False
    assert summary.live_trading_allowed is False


def test_research_result_valid_requires_snapshot_time_coverage_not_only_count():
    # Completed but research_result_valid is False (fails coverage)
    completed = [
        EventSymbolState(
            event_symbol_id="id1",
            event_id="e1",
            symbol="BTCUSDT",
            status="completed",
            research_result_valid=False, # fails coverage check
        )
    ]
    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_depth_evidence_collected", # will be downgraded by derive_stage1_5f_decision
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=1,
        active_states=[],
        completed_states=completed,
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[{"http_status": 200}],
        heartbeat_rows=[{"poll_index": 1}],
    )
    # Since completed has no valid research result, it cannot claim depth_evidence_collected
    assert summary.decision != "stage1_5f_observer_depth_evidence_collected"
    assert summary.research_result_valid is False


def test_summary_never_allows_paper_live_execution_or_alpha():
    # Watermark test model defaults checking had this, let's verify that a generated summary enforces False regardless of input
    completed = [
        EventSymbolState(
            event_symbol_id="id1",
            event_id="e1",
            symbol="BTCUSDT",
            status="completed",
            research_result_valid=True,
        )
    ]
    built = build_live_depth_observer_summary(
        decision="stage1_5f_observer_depth_evidence_collected",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=1,
        active_states=[],
        completed_states=completed,
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[{"http_status": 200}],
        heartbeat_rows=[{"poll_index": 1}],
    )
    assert built.execution_feasibility_claim_allowed is False
    assert built.trade_signal_allowed is False
    assert built.paper_trading_allowed is False
    assert built.live_trading_allowed is False


def test_proxy_failed_state_does_not_block_observation_only_mode():
    # If stage1_5e has decision == proxy_failed, it should still allow observation bootstrapping and running (warning only)
    completed = [
        EventSymbolState(
            event_symbol_id="id1",
            event_id="e1",
            symbol="BTCUSDT",
            status="completed",
            research_result_valid=True,
        )
    ]
    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_depth_evidence_collected",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=True, # warning condition
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=1,
        active_states=[],
        completed_states=completed,
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[{"http_status": 200}],
        heartbeat_rows=[{"poll_index": 1}],
    )
    assert summary.decision == "stage1_5f_observer_depth_evidence_collected"
    assert summary.stage1_5e_context_suspicious is True


def test_summary_reports_pre_and_post_watermark_counts():
    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_running_no_new_event",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=10,
        post_watermark_events_accepted=2,
        active_states=[],
        completed_states=[],
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[],
        heartbeat_rows=[],
    )
    assert summary.pre_watermark_events_ignored == 10
    assert summary.post_watermark_events_accepted == 2


def test_summary_reports_exchangeinfo_and_budget_counts():
    # Verify that counts are correctly computed
    active = [EventSymbolState(event_symbol_id="id1", status="active")]
    expired = [EventSymbolState(event_symbol_id="id2", status="expired_without_depth")]
    failed = [EventSymbolState(event_symbol_id="id3", status="failed")]

    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_event_observation_in_progress",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=3,
        active_states=active,
        completed_states=[],
        expired_states=expired,
        failed_states=failed,
        request_manifest_rows=[],
        heartbeat_rows=[],
    )
    assert summary.active_observation_count == 1
    assert summary.expired_observation_count == 1
    assert summary.failed_observation_count == 1


def test_summary_reports_total_snapshots_from_all_states():
    active = [EventSymbolState(event_symbol_id="id1", status="active", depth_snapshot_count=3)]
    completed = [
        EventSymbolState(
            event_symbol_id="id2",
            status="completed",
            depth_snapshot_count=576,
            research_result_valid=True,
        )
    ]
    expired = [
        EventSymbolState(
            event_symbol_id="id3",
            status="expired_without_depth",
            depth_snapshot_count=12,
        )
    ]

    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_event_observation_in_progress",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=3,
        active_states=active,
        completed_states=completed,
        expired_states=expired,
        failed_states=[],
        request_manifest_rows=[{"http_status": 200}],
        heartbeat_rows=[],
    )

    assert summary.total_snapshots_collected == 591


def test_depth_evidence_collected_requires_request_success_rate_threshold():
    # Request success rate is 0.94 (below threshold 0.95)
    manifest = [{"http_status": 200}] * 94 + [{"http_status": 500}] * 6
    assert compute_request_success_rate(manifest) == 0.94

    decision = derive_stage1_5f_decision(
        base_decision="stage1_5f_observer_depth_evidence_collected",
        completed_count=1,
        active_count=0,
        success_rate=0.94,
        any_valid_research_result=True,
    )
    # Low request rate turns status to failed
    assert decision == "stage1_5f_observer_failed"


def test_low_request_success_rate_makes_observer_failed():
    # Test mapping inside build_live_depth_observer_summary
    completed = [
        EventSymbolState(
            event_symbol_id="id1",
            event_id="e1",
            symbol="BTCUSDT",
            status="completed",
            research_result_valid=True,
        )
    ]
    manifest = [{"http_status": 200}] * 90 + [{"http_status": 500}] * 10 # 90% success rate

    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_depth_evidence_collected",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=1,
        active_states=[],
        completed_states=completed,
        expired_states=[],
        failed_states=[],
        request_manifest_rows=manifest,
        heartbeat_rows=[{"poll_index": 1}],
    )
    assert summary.decision == "stage1_5f_observer_failed"
    assert summary.research_result_valid is False
    assert summary.blocker == "low_request_success_rate"


def test_summary_reports_heartbeat_count_and_last_heartbeat_at_ms():
    hbs = [
        {"poll_index": 0, "poll_at_ms": 1000},
        {"poll_index": 1, "poll_at_ms": 2000},
    ]
    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_running_no_new_event",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=5,
        post_watermark_events_accepted=0,
        active_states=[],
        completed_states=[],
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[],
        heartbeat_rows=hbs,
    )
    assert summary.heartbeat_count == 2
    assert summary.last_heartbeat_at_ms == 2000


def test_summary_includes_launch_gate_pending_and_bucket_gauges():
    pending = EventSymbolState(
        event_symbol_id="pending1",
        status="pending_launch_time_in_future",
        symbol="XYZUSDT",
        observation_anchor_ms=20_000,
    )
    active = EventSymbolState(
        event_symbol_id="active1",
        status="active",
        symbol="ABCUSDT",
        expected_snapshot_count=720,
        unique_snapshot_bucket_count=10,
        missing_snapshot_bucket_count=710,
        out_of_window_snapshot_row_count=2,
    )

    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_event_observation_in_progress",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=0,
        post_watermark_events_accepted=1,
        active_states=[active],
        completed_states=[],
        expired_states=[],
        failed_states=[],
        pending_states=[pending],
        request_manifest_rows=[],
        heartbeat_rows=[],
    ).to_dict()

    assert summary["pending_launch_observation_count"] == 1
    assert summary["pending_launch_time_in_future_count"] == 1
    assert summary["pending_launch_anchor_missing_count"] == 0
    assert summary["pending_anchor_conflict_count"] == 0
    assert summary["pending_observation_capacity_count"] == 0
    assert summary["active_expected_snapshot_count"] == 720
    assert summary["active_unique_snapshot_bucket_count"] == 10
    assert summary["active_missing_snapshot_bucket_count"] == 710
    assert summary["active_out_of_window_snapshot_row_count"] == 2


def test_summary_includes_terminal_hygiene_metrics():
    term_ignored = EventSymbolState(
        event_symbol_id="es-term",
        event_id="e-term",
        source_article_id="a-term",
        symbol="EBAYUSDT",
        detected_at_ms=1000,
        status="ignored_historical_anchor_pre_bootstrap",
        terminal_hygiene_id="term-1",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_at_ms=2000,
        terminal_ignored_revision_seen_count=3,
        consumable_by_stage1_5g=False,
    )
    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_running_no_new_event",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="dummy_d",
        stage1_5e_summary_path="dummy_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=2,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=0,
        post_watermark_events_accepted=0,
        active_states=[],
        completed_states=[],
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[],
        heartbeat_rows=[],
        terminal_ignored_states=[term_ignored],
        historical_anchor_newly_ignored_this_poll=1,
        bootstrap_watermark_missing_diagnostic_count=2,
        malformed_terminal_diagnostic_count=3,
    ).to_dict()

    assert summary["terminal_ignored_pre_bootstrap_anchor_count"] == 1
    assert summary["historical_anchor_ignored_count"] == 1
    assert summary["rejected_event_symbol_count"] == 0
    assert summary["historical_anchor_duplicate_suppressed_total"] == 0
    assert summary["rejected_missing_identity_count"] == 0
    assert summary["rejected_missing_reason_count"] == 0
    assert summary["rejection_hygiene_diagnostic_count"] == 5
    assert summary["terminal_ignored_revision_seen_count"] == 3
    assert summary["historical_anchor_newly_ignored_this_poll"] == 1
    assert summary["bootstrap_watermark_missing_diagnostic_count"] == 2
    assert summary["malformed_terminal_diagnostic_count"] == 3
