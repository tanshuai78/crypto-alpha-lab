def decide_stage1_connector_summary(summary: dict) -> dict:
    decision = "external_signal_connector_stage1_passed"
    failure_type = "connector_completed"
    primary_blocker = None

    if _unsafe_flags(summary):
        failure_type = "safety_failure"
        primary_blocker = "unsafe_runtime_flag"
    elif summary.get("raw_payload_count", 0) <= 0:
        failure_type = "data_failure"
        primary_blocker = "missing_raw_payloads"
    elif summary.get("summary_accounting_ok") is not True:
        failure_type = "summary_accounting_failure"
        primary_blocker = "accounting_invariant_failed"
    elif not summary.get("output_file") or not summary.get("output_file_sha256"):
        failure_type = "replay_handoff_failure"
        primary_blocker = "missing_output_file_or_hash"
    elif summary.get("emitted_event_count", 0) <= 0:
        failure_type = "schema_failure"
        primary_blocker = "no_emitted_events"

    if failure_type != "connector_completed":
        decision = "external_signal_connector_stage1_failed"

    return {
        **summary,
        "decision": decision,
        "failure_type": failure_type,
        "primary_blocker": primary_blocker,
        "live_safe": False,
        "exchange_paper_trading_allowed": False,
        "execution_engine_allowed": False,
        "research_shadow_replay_allowed": True,
        "alpha_interpretation_allowed": False,
    }


def _unsafe_flags(summary: dict) -> bool:
    return any(
        summary.get(flag) is not expected
        for flag, expected in {
            "live_trading_enabled": False,
            "exchange_paper_trading_allowed": False,
            "execution_engine_allowed": False,
            "research_shadow_replay_allowed": True,
            "wallet_required": False,
        }.items()
    )
