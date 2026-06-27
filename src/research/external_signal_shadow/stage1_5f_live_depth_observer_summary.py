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
) -> LiveDepthObserverSummary:

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
        execution_feasibility_claim_allowed=False,
        trade_signal_allowed=False,
        paper_trading_allowed=False,
        live_trading_allowed=False,
        execution_engine_allowed=False,
        alpha_interpretation_allowed=False,
        research_result_valid=res_valid,
        blocker=blocker,
        summary_generated_at_ms=int(time.time() * 1000),
    )
