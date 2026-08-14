import time

from configs import base
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
    LiveDepthObserverSummary,
)


def compute_request_success_rate(request_manifest_rows: list) -> float:
    if not request_manifest_rows:
        return 1.0
    successes = sum(
        1 for r in request_manifest_rows
        if (r.get("http_status") if isinstance(r, dict) else getattr(r, "http_status", 0)) == 200
    )
    return successes / len(request_manifest_rows)


def derive_stage1_5f_decision(
    base_decision: str,
    completed_count: int,
    active_count: int,
    success_rate: float,
    any_valid_research_result: bool
) -> str:
    if base_decision in ("stage1_5f_observer_invalid", "stage1_5f_observer_failed"):
        return base_decision

    if success_rate < 0.95:
        return "stage1_5f_observer_failed"

    if base_decision == "stage1_5f_observer_depth_evidence_collected":
        if completed_count == 0 or not any_valid_research_result:
            if active_count > 0:
                return "stage1_5f_observer_event_observation_in_progress"
            else:
                return "stage1_5f_observer_running_no_new_event"
        return "stage1_5f_observer_depth_evidence_collected"

    return base_decision


def build_live_depth_observer_summary(
    decision: str,
    bootstrap_watermark_allowed: bool,
    live_depth_observation_allowed: bool,
    stage1_5d_summary_path: str,
    stage1_5e_summary_path: str | None,
    stage1_5e_context_missing: bool,
    stage1_5e_context_suspicious: bool,
    watermark_present: bool,
    watermark_version: int | None,
    max_seen_detected_at_ms: int,
    pre_watermark_events_ignored: int,
    post_watermark_events_accepted: int,
    active_states: list,
    completed_states: list,
    expired_states: list,
    failed_states: list,
    request_manifest_rows: list,
    heartbeat_rows: list,
    pending_states: list | None = None,
    terminal_states: list | None = None,
    terminal_ignored_states: list | None = None,
    terminal_state_hits_this_poll: int = 0,
    historical_anchor_newly_ignored_this_poll: int = 0,
    bootstrap_watermark_missing_diagnostic_count: int = 0,
    malformed_terminal_diagnostic_count: int = 0,
    runtime_gate_context: dict | None = None,
) -> LiveDepthObserverSummary:

    pending_states = pending_states or []
    runtime_gate_context = runtime_gate_context or {}
    active_count = len(active_states)
    completed_count = len(completed_states)
    expired_count = len(expired_states)
    failed_count = len(failed_states)

    success_rate = compute_request_success_rate(request_manifest_rows)
    total_reqs = len(request_manifest_rows)
    failed_reqs = total_reqs - sum(
        1 for r in request_manifest_rows
        if (r.get("http_status") if isinstance(r, dict) else getattr(r, "http_status", 0)) == 200
    )

    consec_errors = 0
    max_consec_seen = 0
    for r in request_manifest_rows:
        status = r.get("http_status") if isinstance(r, dict) else getattr(r, "http_status", 0)
        if status != 200:
            consec_errors += 1
            if consec_errors > max_consec_seen:
                max_consec_seen = consec_errors
        else:
            consec_errors = 0

    min_req_count = int(
        (base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS // (base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC * 1000))
        * base.EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COVERAGE_RATIO
    )

    any_valid = any(
        (s.research_result_valid if hasattr(s, "research_result_valid") else s.get("research_result_valid", False))
        for s in completed_states
    )
    total_snapshots = sum(
        (s.depth_snapshot_count if hasattr(s, "depth_snapshot_count") else s.get("depth_snapshot_count", 0))
        for s in active_states + completed_states + expired_states + failed_states
    )
    pending_launch_count = len([s for s in pending_states if getattr(s, "status", "").startswith("pending_")])
    pending_future_count = len([s for s in pending_states if getattr(s, "status", "") == "pending_launch_time_in_future"])
    pending_missing_count = len([s for s in pending_states if getattr(s, "status", "") == "pending_launch_anchor_missing"])
    pending_conflict_count = len([s for s in pending_states if getattr(s, "status", "") == "pending_anchor_conflict"])
    pending_capacity_count = len([s for s in pending_states if getattr(s, "status", "") == "pending_observation_capacity"])
    active_expected_snapshot_count = sum(
        (s.expected_snapshot_count if hasattr(s, "expected_snapshot_count") else s.get("expected_snapshot_count", 0))
        for s in active_states
    )
    active_unique_bucket_count = sum(
        (s.unique_snapshot_bucket_count if hasattr(s, "unique_snapshot_bucket_count") else s.get("unique_snapshot_bucket_count", 0))
        for s in active_states
    )
    active_missing_bucket_count = sum(
        (s.missing_snapshot_bucket_count if hasattr(s, "missing_snapshot_bucket_count") else s.get("missing_snapshot_bucket_count", 0))
        for s in active_states
    )
    active_out_of_window_count = sum(
        (s.out_of_window_snapshot_row_count if hasattr(s, "out_of_window_snapshot_row_count") else s.get("out_of_window_snapshot_row_count", 0))
        for s in active_states
    )
    active_anchor_revision_contaminated_count = sum(
        1
        for s in active_states
        if (s.status if hasattr(s, "status") else s.get("status")) == "active_anchor_revision_contaminated"
    )
    completed_anchor_revision_contaminated_count = sum(
        1
        for s in completed_states
        if (s.status if hasattr(s, "status") else s.get("status")) == "completed_anchor_revision_contaminated"
    )
    anchor_contract_revision_count = sum(
        (s.anchor_contract_revision_count if hasattr(s, "anchor_contract_revision_count") else s.get("anchor_contract_revision_count", 0))
        for s in active_states + completed_states + pending_states + expired_states + failed_states
    )
    anchor_contract_lineage_mismatch_count = sum(
        1
        for s in active_states + completed_states + pending_states + expired_states + failed_states
        if (s.observation_anchor_revision_contaminated if hasattr(s, "observation_anchor_revision_contaminated") else s.get("observation_anchor_revision_contaminated", False))
    )

    all_terminal_states = terminal_states if terminal_states is not None else (terminal_ignored_states or [])
    term_ignored_states = [
        s for s in all_terminal_states
        if (s.status if hasattr(s, "status") else s.get("status")) == "ignored_historical_anchor_pre_bootstrap"
    ]
    rejected_states = [
        s for s in all_terminal_states
        if (s.status if hasattr(s, "status") else s.get("status")) == "rejected"
    ]
    terminal_ignored_pre_bootstrap_anchor_count = len([
        s for s in term_ignored_states
        if (s.status if hasattr(s, "status") else s.get("status")) == "ignored_historical_anchor_pre_bootstrap"
    ])
    rejected_event_symbol_count = len(rejected_states)
    historical_anchor_duplicate_suppressed_total = sum(
        (s.duplicate_suppressed_count if hasattr(s, "duplicate_suppressed_count") else s.get("duplicate_suppressed_count", 0))
        for s in term_ignored_states
    )
    rejected_event_symbol_duplicate_suppressed_total = sum(
        (s.duplicate_suppressed_count if hasattr(s, "duplicate_suppressed_count") else s.get("duplicate_suppressed_count", 0))
        for s in rejected_states
    )
    terminal_ignored_revision_seen_count = sum(
        (s.terminal_ignored_revision_seen_count if hasattr(s, "terminal_ignored_revision_seen_count") else s.get("terminal_ignored_revision_seen_count", 0))
        for s in term_ignored_states
    )
    rejected_missing_identity_count = sum(
        1 for s in rejected_states
        if not ((s.event_id if hasattr(s, "event_id") else s.get("event_id")) or (s.source_article_id if hasattr(s, "source_article_id") else s.get("source_article_id")))
    )
    rejected_missing_reason_count = sum(
        1 for s in rejected_states
        if not (s.terminal_reason if hasattr(s, "terminal_reason") else s.get("terminal_reason"))
    )
    rejection_hygiene_diagnostic_count = bootstrap_watermark_missing_diagnostic_count + malformed_terminal_diagnostic_count

    final_decision = derive_stage1_5f_decision(
        base_decision=decision,
        completed_count=completed_count,
        active_count=active_count,
        success_rate=success_rate,
        any_valid_research_result=any_valid,
    )

    blocker = None
    if final_decision == "stage1_5f_observer_failed":
        if success_rate < 0.95:
            blocker = "low_request_success_rate"
        elif max_consec_seen >= base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_CONSECUTIVE_NETWORK_ERRORS:
            blocker = "max_consecutive_network_errors_exceeded"
        else:
            blocker = "observation_failed"
    elif final_decision == "stage1_5f_observer_invalid":
        if stage1_5e_context_missing and live_depth_observation_allowed:
            blocker = "stage1_5e_context_missing_for_observation"
        else:
            blocker = "observer_invalid"

    heartbeat_count = len(heartbeat_rows)
    last_hb_at = 0
    if heartbeat_rows:
        last_hb = heartbeat_rows[-1]
        last_hb_at = last_hb.get("poll_at_ms") if isinstance(last_hb, dict) else getattr(last_hb, "poll_at_ms", 0)

    res_valid = (final_decision == "stage1_5f_observer_depth_evidence_collected" and any_valid)

    return LiveDepthObserverSummary(
        decision=final_decision,
        bootstrap_watermark_allowed=bootstrap_watermark_allowed,
        live_depth_observation_allowed=live_depth_observation_allowed,
        stage1_5d_summary_path=stage1_5d_summary_path,
        stage1_5e_summary_path=stage1_5e_summary_path,
        stage1_5e_context_missing=stage1_5e_context_missing,
        stage1_5e_context_suspicious=stage1_5e_context_suspicious,
        watermark_present=watermark_present,
        watermark_version=watermark_version,
        max_seen_detected_at_ms=max_seen_detected_at_ms,
        pre_watermark_events_ignored=pre_watermark_events_ignored,
        post_watermark_events_accepted=post_watermark_events_accepted,
        active_observation_count=active_count,
        completed_observation_count=completed_count,
        expired_observation_count=expired_count,
        failed_observation_count=failed_count,
        min_snapshot_count_required=min_req_count,
        total_snapshots_collected=total_snapshots,
        request_success_rate=success_rate,
        total_requests_made=total_reqs,
        failed_requests_count=failed_reqs,
        consecutive_network_errors=consec_errors,
        max_consecutive_network_errors_seen=max_consec_seen,
        last_heartbeat_at_ms=last_hb_at,
        heartbeat_count=heartbeat_count,
        pending_launch_observation_count=pending_launch_count,
        pending_launch_time_in_future_count=pending_future_count,
        pending_launch_anchor_missing_count=pending_missing_count,
        pending_anchor_conflict_count=pending_conflict_count,
        pending_observation_capacity_count=pending_capacity_count,
        active_expected_snapshot_count=active_expected_snapshot_count,
        active_unique_snapshot_bucket_count=active_unique_bucket_count,
        active_missing_snapshot_bucket_count=active_missing_bucket_count,
        active_out_of_window_snapshot_row_count=active_out_of_window_count,
        terminal_ignored_pre_bootstrap_anchor_count=terminal_ignored_pre_bootstrap_anchor_count,
        historical_anchor_ignored_count=terminal_ignored_pre_bootstrap_anchor_count,
        rejected_event_symbol_count=rejected_event_symbol_count,
        historical_anchor_duplicate_suppressed_total=historical_anchor_duplicate_suppressed_total,
        rejected_event_symbol_duplicate_suppressed_total=rejected_event_symbol_duplicate_suppressed_total,
        rejected_missing_identity_count=rejected_missing_identity_count,
        rejected_missing_reason_count=rejected_missing_reason_count,
        rejection_hygiene_diagnostic_count=rejection_hygiene_diagnostic_count,
        terminal_ignored_revision_seen_count=terminal_ignored_revision_seen_count,
        terminal_state_hits_this_poll=terminal_state_hits_this_poll,
        historical_anchor_newly_ignored_this_poll=historical_anchor_newly_ignored_this_poll,
        bootstrap_watermark_missing_diagnostic_count=bootstrap_watermark_missing_diagnostic_count,
        malformed_terminal_diagnostic_count=malformed_terminal_diagnostic_count,
        multi_symbol_candidate_set_event_rows_count=int(runtime_gate_context.get("multi_symbol_candidate_set_event_rows_count", 0)),
        multi_symbol_candidate_symbol_rows_admitted_count=int(runtime_gate_context.get("multi_symbol_candidate_symbol_rows_admitted_count", 0)),
        multi_symbol_candidate_symbol_rows_rejected_count=int(runtime_gate_context.get("multi_symbol_candidate_symbol_rows_rejected_count", 0)),
        multi_symbol_candidate_symbol_rows_pending_count=int(runtime_gate_context.get("multi_symbol_candidate_symbol_rows_pending_count", 0)),
        duplicate_suppressed_count=int(runtime_gate_context.get("duplicate_suppressed_count", 0)),
        identity_collision_blocked_count=int(runtime_gate_context.get("identity_collision_blocked_count", 0)),
        active_anchor_revision_contaminated_count=active_anchor_revision_contaminated_count,
        completed_anchor_revision_contaminated_count=completed_anchor_revision_contaminated_count,
        anchor_contract_revision_count=anchor_contract_revision_count,
        anchor_contract_lineage_mismatch_count=anchor_contract_lineage_mismatch_count,
        schedule_revision_registry_orphan_count=int(runtime_gate_context.get("schedule_revision_registry_orphan_count", 0)),
        schedule_revision_registry_ambiguous_count=int(runtime_gate_context.get("schedule_revision_registry_ambiguous_count", 0)),
        stage1_5d_gate_mode=runtime_gate_context.get("stage1_5d_gate_mode", "unknown"),
        stage1_5d_runtime_gate_path=runtime_gate_context.get("stage1_5d_runtime_gate_path", ""),
        stage1_5d_runtime_gate_decision=runtime_gate_context.get("stage1_5d_runtime_gate_decision", ""),
        stage1_5d_runtime_gate_last_validated_at_ms=runtime_gate_context.get("stage1_5d_runtime_gate_last_validated_at_ms"),
        stage1_5d_runtime_gate_stale=bool(runtime_gate_context.get("stage1_5d_runtime_gate_stale", False)),
        stage1_5d_runtime_gate_invalid_count=int(runtime_gate_context.get("stage1_5d_runtime_gate_invalid_count", 0)),
        cross_root_upstream_summary_dependency=bool(runtime_gate_context.get("cross_root_upstream_summary_dependency", False)),
        historical_stage1_5d_gate_reason=runtime_gate_context.get("historical_stage1_5d_gate_reason", ""),
        block_new_event_admission=bool(runtime_gate_context.get("block_new_event_admission", False)),
        runtime_gate_diagnostic_count=int(runtime_gate_context.get("runtime_gate_diagnostic_count", 0)),
        execution_feasibility_claim_allowed=False,
        trade_signal_allowed=False,
        paper_trading_allowed=False,
        live_trading_allowed=False,
        execution_engine_allowed=False,
        alpha_interpretation_allowed=False,
        research_result_valid=res_valid,
        blocker=blocker,
        summary_generated_at_ms=int(time.time() * 1000),
        consumer_process_instance_id=str(runtime_gate_context.get("consumer_process_instance_id", "")),
        consumer_root_id=str(runtime_gate_context.get("consumer_root_id", "")),
        consumer_startup_commit_sha=str(runtime_gate_context.get("consumer_startup_commit_sha", "")),
        consumer_root_contract_sha256=str(runtime_gate_context.get("consumer_root_contract_sha256", "")),
        consumer_runtime_manifest_sha256=str(runtime_gate_context.get("consumer_runtime_manifest_sha256", "")),
        consumer_static_attestation_verified=bool(runtime_gate_context.get("consumer_static_attestation_verified", False)),
        consumer_runtime_attestation_verified=bool(runtime_gate_context.get("consumer_runtime_attestation_verified", False)),
        consumer_runtime_attestation_compromised=bool(runtime_gate_context.get("consumer_runtime_attestation_compromised", False)),
        storage_guard_status=str(runtime_gate_context.get("storage_guard_status", "")),
        storage_guard_checked_at_ms=runtime_gate_context.get("storage_guard_checked_at_ms"),
        storage_free_bytes=runtime_gate_context.get("storage_free_bytes"),
        storage_root_bytes=runtime_gate_context.get("storage_root_bytes"),
        storage_root_scanned_at_ms=runtime_gate_context.get("storage_root_scanned_at_ms"),
        storage_root_max_bytes=runtime_gate_context.get("storage_root_max_bytes"),
        storage_terminal_write_set_peak_bytes=runtime_gate_context.get("storage_terminal_write_set_peak_bytes"),
        storage_emergency_blocker_reserve_bytes=runtime_gate_context.get("storage_emergency_blocker_reserve_bytes"),
        storage_blocker=runtime_gate_context.get("storage_blocker"),
    )
