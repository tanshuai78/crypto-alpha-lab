from configs import base


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    """Return numerator/denominator as float, or 0.0 if denominator is zero."""
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


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

    # Stage 1.1 specific logic
    minimal_connector_pass = False
    stage0_handoff_ready = False
    stage0_handoff_blockers: list[str] = []
    stage0_handoff_mode = "blocked"
    stage0_directional_replay_ready = False
    stage0_observation_handoff_ready = False

    if summary.get("source") == base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE:
        raw_count = summary.get("raw_payload_count", 0)
        emitted_count = summary.get("emitted_event_count", 0)

        minimal_connector_pass = (
            failure_type == "connector_completed"
            and raw_count >= base.EXTERNAL_SIGNAL_STAGE1_1_MIN_RAW_PAYLOADS
            and emitted_count >= base.EXTERNAL_SIGNAL_STAGE1_1_MIN_EMITTED_EVENTS
        )

        # price_mapping_failure takes priority over source_quality_failure
        if failure_type == "connector_completed":
            if summary.get("price_mapping_unavailable_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_PRICE_MAPPING_UNAVAILABLE_RATIO:
                failure_type = "price_mapping_failure"
                primary_blocker = "price_mapping_unavailable_high"
            elif summary.get("event_time_fallback_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_EVENT_TIME_FALLBACK_RATIO:
                failure_type = "source_quality_failure"
                primary_blocker = "event_time_unreliable"
            elif summary.get("duplicate_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_DUPLICATE_RATIO:
                failure_type = "source_quality_failure"
                primary_blocker = "duplicate_density_high"
            elif summary.get("unknown_event_type_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_UNKNOWN_EVENT_TYPE_RATIO:
                failure_type = "source_quality_failure"
                primary_blocker = "unknown_event_type_high"
            elif summary.get("missing_required_field_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_MISSING_REQUIRED_FIELD_RATIO:
                failure_type = "source_quality_failure"
                primary_blocker = "missing_required_fields_high"
            elif summary.get("single_symbol_dominance_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_SYMBOL_DOMINANCE_RATIO:
                failure_type = "source_quality_failure"
                primary_blocker = "single_symbol_dominance_high"
            elif summary.get("single_time_bucket_dominance_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_TIME_BUCKET_DOMINANCE_RATIO:
                failure_type = "source_quality_failure"
                primary_blocker = "single_time_bucket_dominance_high"


        # Handoff gate: accumulate blockers independently of connector failure.
        if failure_type not in ("connector_completed",):
            stage0_handoff_blockers.append(failure_type)
        if raw_count < base.EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_RAW_PAYLOADS:
            stage0_handoff_blockers.append("insufficient_raw_payloads")
        if emitted_count < base.EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_EMITTED_EVENTS:
            stage0_handoff_blockers.append("insufficient_emitted_events")
        if summary.get("unique_symbol_count", 0) < base.EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_UNIQUE_SYMBOLS:
            stage0_handoff_blockers.append("insufficient_unique_symbols")
        if summary.get("unique_event_time_bucket_count", 0) < base.EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_UNIQUE_TIME_BUCKETS:
            stage0_handoff_blockers.append("insufficient_unique_time_buckets")
        if summary.get("event_time_fallback_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_EVENT_TIME_FALLBACK_RATIO:
            if "source_quality_failure" not in stage0_handoff_blockers:
                stage0_handoff_blockers.append("event_time_unreliable")
        if summary.get("price_mapping_unavailable_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_PRICE_MAPPING_UNAVAILABLE_RATIO:
            if "price_mapping_failure" not in stage0_handoff_blockers:
                stage0_handoff_blockers.append("price_mapping_unavailable_high")
        if summary.get("rejected_payload_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_REJECTED_PAYLOAD_RATIO:
            stage0_handoff_blockers.append("rejected_payload_ratio_high")
        if summary.get("single_symbol_dominance_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_SYMBOL_DOMINANCE_RATIO:
            if "single_symbol_dominance_high" not in stage0_handoff_blockers:
                stage0_handoff_blockers.append("single_symbol_dominance_high")
        if summary.get("single_time_bucket_dominance_ratio", 0.0) > base.EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_TIME_BUCKET_DOMINANCE_RATIO:
            if "single_time_bucket_dominance_high" not in stage0_handoff_blockers:
                stage0_handoff_blockers.append("single_time_bucket_dominance_high")

        stage0_handoff_ready = len(stage0_handoff_blockers) == 0

        # Handoff mode: determine based on event counts.
        replay_eligible = summary.get("stage0_replay_eligible_event_count", 0)
        observation_only = summary.get("stage0_observation_only_event_count", 0)

        if not stage0_handoff_ready:
            stage0_handoff_mode = "blocked"
            stage0_directional_replay_ready = False
            stage0_observation_handoff_ready = False
        elif replay_eligible > 0:
            stage0_handoff_mode = "directional_replay"
            stage0_directional_replay_ready = True
            stage0_observation_handoff_ready = True
        elif observation_only > 0:
            stage0_handoff_mode = "observation_only"
            stage0_directional_replay_ready = False
            stage0_observation_handoff_ready = True
        else:
            stage0_handoff_mode = "blocked"
            stage0_directional_replay_ready = False
            stage0_observation_handoff_ready = False

    elif summary.get("source") == "gate_public_market_snapshot_collector":
        raw_count = summary.get("raw_payload_count", 0)
        emitted_count = summary.get("emitted_event_count", 0)
        price_mapping_unavailable_ratio = summary.get("price_mapping_unavailable_ratio", 0.0)

        minimal_connector_pass = (
            failure_type == "connector_completed"
            and raw_count >= 5
            and emitted_count >= 5
        )

        stage0_handoff_blockers = []
        if failure_type != "connector_completed":
            stage0_handoff_blockers.append(failure_type)
        if raw_count < 5:
            stage0_handoff_blockers.append("insufficient_raw_payloads")
        if emitted_count < 5:
            stage0_handoff_blockers.append("insufficient_emitted_events")
        if price_mapping_unavailable_ratio > 0.0:
            stage0_handoff_blockers.append("price_mapping_unavailable")

        stage0_handoff_ready = len(stage0_handoff_blockers) == 0

        if not stage0_handoff_ready:
            stage0_handoff_mode = "blocked"
            stage0_directional_replay_ready = False
            stage0_observation_handoff_ready = False
        else:
            stage0_handoff_mode = "observation_only"
            stage0_directional_replay_ready = False
            stage0_observation_handoff_ready = True

    if failure_type not in ("connector_completed",):
        decision = "external_signal_connector_stage1_failed"

    res: dict = {
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

    if summary.get("source") == base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE:
        res["minimal_connector_pass"] = minimal_connector_pass
        res["stage0_handoff_ready"] = stage0_handoff_ready
        res["stage0_handoff_blockers"] = stage0_handoff_blockers
        res["stage0_handoff_mode"] = stage0_handoff_mode
        res["stage0_directional_replay_ready"] = stage0_directional_replay_ready
        res["stage0_observation_handoff_ready"] = stage0_observation_handoff_ready
    elif summary.get("source") == "gate_public_market_snapshot_collector":
        res["minimal_connector_pass"] = minimal_connector_pass
        res["stage0_handoff_ready"] = stage0_handoff_ready
        res["stage0_handoff_blockers"] = stage0_handoff_blockers
        res["stage0_handoff_mode"] = stage0_handoff_mode
        res["stage0_directional_replay_ready"] = stage0_directional_replay_ready
        res["stage0_observation_handoff_ready"] = stage0_observation_handoff_ready
        res["event_density_alpha_valid"] = False
        res["triple_barrier_directional_order_allowed"] = False

    return res


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
