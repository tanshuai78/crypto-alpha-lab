def build_smoke_summary(
    upstream_evidence: dict,
    heartbeats: list[dict],
    events: list[dict],
    request_manifest: list[dict],
    fixture_run: bool,
    debug_short_run: bool,
    observation_hours: float,
    counters: dict | None = None,
) -> dict:
    counters = counters or {}
    blockers = []

    # 1. Check upstream evidence
    if not upstream_evidence.get("upstream_evidence_valid", False):
        blockers.append("upstream_evidence_missing_or_invalid")
        if upstream_evidence.get("blockers"):
            blockers.extend(upstream_evidence["blockers"])

    # 2. Check client/polling health
    poll_count = len(heartbeats)
    success_count = sum(1 for h in heartbeats if h.get("poll_success", False))
    success_rate = (success_count / poll_count) if poll_count > 0 else 1.0

    if poll_count > 0 and success_rate < 0.95:
        blockers.append("poll_success_rate_too_low")

    for h in heartbeats:
        if h.get("source_format_drift") or h.get("schema_parse_error"):
            blockers.append("source_format_drift_detected")

    # Deduplicate blockers
    blockers = list(dict.fromkeys(blockers))

    # Determine decision
    if "upstream_evidence_missing_or_invalid" in blockers:
        decision = "stage1_5d_smoke_invalid"
        research_result_valid = False
        event_detection_validated = False
    elif blockers:
        decision = "stage1_5d_smoke_failed"
        research_result_valid = False
        event_detection_validated = False
    else:
        event_detected_and_found = False
        for e in events:
            if (
                e.get("event_type") == "futures_contract_launch"
                and e.get("first_futures_bar_status") == "found"
            ):
                event_detected_and_found = True
                break

        if event_detected_and_found:
            decision = "stage1_5d_event_detection_passed"
            research_result_valid = True
            event_detection_validated = True
        elif fixture_run or debug_short_run or observation_hours < 24.0:
            decision = "stage1_5d_smoke_observation_in_progress"
            research_result_valid = False
            event_detection_validated = False
        else:
            decision = "stage1_5d_operational_pass_event_detection_unvalidated"
            research_result_valid = True
            event_detection_validated = False

    return {
        "decision": decision,
        "blockers": blockers,
        "fixture_run": fixture_run,
        "debug_short_run": debug_short_run,
        "observation_hours": observation_hours,
        "research_result_valid": research_result_valid,
        "event_detection_validated": event_detection_validated,
        "poll_count": poll_count,
        "raw_futures_launch_article_count": counters.get(
            "raw_futures_launch_article_count", len(events)
        ),
        "symbol_parsed_event_count": counters.get(
            "symbol_parsed_event_count", sum(1 for e in events if e.get("symbols"))
        ),
        "symbol_parse_failed_count": counters.get(
            "symbol_parse_failed_count", sum(1 for e in events if not e.get("symbols"))
        ),
        "deduped_new_event_count": counters.get("deduped_new_event_count", len(events)),
        "new_futures_launch_event_count": counters.get("deduped_new_event_count", len(events)),
        "detail_fetch_attempted_count": counters.get(
            "detail_fetch_attempted_count",
            sum(1 for e in events if e.get("detail_fetch_attempted", False))
        ),
        "detail_fetch_success_count": counters.get(
            "detail_fetch_success_count",
            sum(1 for e in events if e.get("detail_fetch_status") == "success")
        ),
        "detail_fetch_failed_count": counters.get("detail_fetch_failed_count", 0),
        "detail_fetch_budget_deferred_count": counters.get("detail_fetch_budget_deferred_count", 0),
        "detail_fetch_url_rejected_count": counters.get("detail_fetch_url_rejected_count", 0),
        "detail_symbol_extracted_count": counters.get(
            "detail_symbol_extracted_count",
            sum(1 for e in events if e.get("symbol_extraction_source") == "detail" and e.get("symbols"))
        ),
        "detail_symbol_parse_failed_count": counters.get(
            "detail_symbol_parse_failed_count",
            sum(1 for e in events if e.get("symbol_extraction_source") == "detail" and not e.get("symbols"))
        ),
        "title_symbol_extracted_count": counters.get(
            "title_symbol_extracted_count",
            sum(1 for e in events if e.get("symbol_extraction_source") == "title")
        ),
        "symbol_empty_event_count": counters.get(
            "symbol_empty_event_count",
            sum(1 for e in events if not e.get("symbols"))
        ),
        "candidate_validation_pending_count": counters.get("candidate_validation_pending_count", 0),
        "candidate_validation_success_count": counters.get("candidate_validation_success_count", 0),
        "candidate_validation_expired_count": counters.get("candidate_validation_expired_count", 0),
        "u_settlement_symbol_extracted_count": counters.get("u_settlement_symbol_extracted_count", 0),
        "pre_launch_validation_deferred_count": counters.get("pre_launch_validation_deferred_count", 0),
        "detail_pending_retry_count": counters.get("detail_pending_retry_count", 0),
        "detail_empty_payload_count": counters.get("detail_empty_payload_count", 0),
        "detail_http_not_ready_count": counters.get("detail_http_not_ready_count", 0),
        "detail_terminal_failed_count": counters.get("detail_terminal_failed_count", 0),
        "detail_transient_timeout_count": counters.get("detail_transient_timeout_count", 0),
        "detail_budget_starved_count": counters.get("detail_budget_starved_count", 0),
        "detail_never_attempted_expired_count": counters.get("detail_never_attempted_expired_count", 0),
        "detail_first_attempt_sla_breach_count": counters.get("detail_first_attempt_sla_breach_count", 0),
        "detail_scheduler_pending_count": counters.get("detail_scheduler_pending_count", 0),
        "detail_scheduler_backoff_count": counters.get("detail_scheduler_backoff_count", 0),
        "detail_endpoint_degraded_count": counters.get("detail_endpoint_degraded_count", 0),
        "detail_endpoint_degraded_active": counters.get("detail_endpoint_degraded_active", 0),
        "detail_success_symbols_empty_count": counters.get("detail_success_symbols_empty_count", 0),
        "detail_degraded_recent_retry_count": counters.get("detail_degraded_recent_retry_count", 0),
        "detail_fetch_fallback_attempt_count": counters.get("detail_fetch_fallback_attempt_count", 0),
        "detail_fetch_fallback_success_count": counters.get("detail_fetch_fallback_success_count", 0),
        "detail_fetch_attempt_manifest_mismatch_count": counters.get(
            "detail_fetch_attempt_manifest_mismatch_count", 0
        ),
        "detail_retry_overdue_pending_count": counters.get("detail_retry_overdue_pending_count", 0),
        "detail_retry_overdue_attempted_count": counters.get("detail_retry_overdue_attempted_count", 0),
        "detail_retry_overdue_never_attempted_count": counters.get("detail_retry_overdue_never_attempted_count", 0),
        "detail_retry_due_timestamp_missing_count": counters.get("detail_retry_due_timestamp_missing_count", 0),
        "detail_attempt_manifest_mismatch_count": counters.get("detail_attempt_manifest_mismatch_count", 0),
        "detail_retry_oldest_overdue_ms": counters.get("detail_retry_oldest_overdue_ms", 0),
        "detail_retry_overdue_warn_active": counters.get("detail_retry_overdue_warn_active", False),
        "detail_retry_overdue_hard_warn_active": counters.get("detail_retry_overdue_hard_warn_active", False),
        "detail_retry_overdue_selected_total": counters.get("detail_retry_overdue_selected_total", 0),
        "detail_retry_overdue_deferred_total": counters.get("detail_retry_overdue_deferred_total", 0),
        "detail_retry_overdue_retry_cycle_total": counters.get("detail_retry_overdue_retry_cycle_total", 0),
        "bapi_detail_request_count": counters.get("bapi_detail_request_count", 0),
        "bapi_detail_success_count": counters.get("bapi_detail_success_count", 0),
        "bapi_detail_trusted_payload_count": counters.get("bapi_detail_trusted_payload_count", 0),
        "bapi_detail_schema_drift_count": counters.get("bapi_detail_schema_drift_count", 0),
        "bapi_detail_identity_mismatch_count": counters.get("bapi_detail_identity_mismatch_count", 0),
        "bapi_detail_rate_limited_count": counters.get("bapi_detail_rate_limited_count", 0),
        "bapi_to_support_fallback_count": counters.get("bapi_to_support_fallback_count", 0),
        "bapi_symbol_parse_success_count": counters.get("bapi_symbol_parse_success_count", 0),
        "bapi_symbol_validation_pending_count": counters.get("bapi_symbol_validation_pending_count", 0),
        "bapi_symbol_validation_success_count": counters.get("bapi_symbol_validation_success_count", 0),
        "support_fallback_success_count": counters.get("support_fallback_success_count", 0),
        "detail_http_manifest_mismatch_count": counters.get("detail_http_manifest_mismatch_count", 0),
        "bapi_payload_revision_count": counters.get("bapi_payload_revision_count", 0),
        "bapi_payload_hash_change_count": counters.get("bapi_payload_hash_change_count", 0),
        "bapi_detail_source_degraded": counters.get("bapi_detail_source_degraded", False),
        "support_detail_source_degraded": counters.get("support_detail_source_degraded", False),
        "all_detail_sources_degraded": counters.get("all_detail_sources_degraded", False),
        "multi_symbol_candidate_set_emission_enabled": counters.get("multi_symbol_candidate_set_emission_enabled", True),
        "multi_symbol_candidate_set_ready_count": counters.get("multi_symbol_candidate_set_ready_count", 0),
        "multi_symbol_candidate_set_pending_count": counters.get("multi_symbol_candidate_set_pending_count", 0),
        "multi_symbol_partial_emit_prevented_count": counters.get("multi_symbol_partial_emit_prevented_count", 0),
        "multi_symbol_full_emit_count": counters.get("multi_symbol_full_emit_count", 0),
        "multi_symbol_emission_registry_count": counters.get("multi_symbol_emission_registry_count", 0),
        "multi_symbol_candidate_set_hash_mismatch_count": counters.get("multi_symbol_candidate_set_hash_mismatch_count", 0),
        "multi_symbol_candidate_state_reset_prevented_count": counters.get("multi_symbol_candidate_state_reset_prevented_count", 0),
        "multi_symbol_validation_rejected_count": counters.get("multi_symbol_validation_rejected_count", 0),
        "strict_anchor_policy_rejected_count": counters.get("strict_anchor_policy_rejected_count", 0),
        "emitted_terminal_state_count": counters.get("emitted_terminal_state_count", 0),
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }
