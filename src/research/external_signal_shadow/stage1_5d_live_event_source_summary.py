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
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }


