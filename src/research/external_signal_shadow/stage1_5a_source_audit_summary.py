import datetime
from collections import Counter

from configs import base
from src.research.external_signal_shadow.stage1_5a_source_audit_models import (
    ExternalSignalEventType,
    ExternalSignalSourceAuditDecision,
    TimestampQuality,
)


def build_source_audit_summary(
    events, metrics, findings, fixture_run=False
) -> dict:
    if metrics is None:
        metrics = {}
    disagreement_count = metrics.get("timestamp_source_disagreement_count", 0)
    format_drift_count = metrics.get("source_format_drift_count", 0)
    quarantine_count = metrics.get("schema_quarantine_count", 0)

    # 1. Basic Counts
    total_events = len(events)
    unique_days_set = set()
    symbols_set = set()
    source_names_set = set()

    for e in events:
        if e.source_published_at_ms:
            dt = datetime.datetime.utcfromtimestamp(e.source_published_at_ms / 1000)
            unique_days_set.add(dt.strftime("%Y-%m-%d"))
        if e.symbol:
            symbols_set.add(e.symbol)
        if e.source_name:
            source_names_set.add(e.source_name)

    # If format drift happened and no events were successfully parsed, add source_name to sources set
    # to make sure we report decisions for it.
    # We can infer source_name from findings or parameters if needed, but let's default to reporting
    # on sources found in events.

    # Base rates
    source_integrity_pass = 0
    trade_pair_mapping_pass = 0
    timestamp_quality_high_medium = 0
    forbidden_payload_count = 0
    payload_too_large_count = 0
    json_depth_exceeded_count = 0
    disallowed_domain_count = 0
    schema_parse_error_count = 0
    source_format_drift_finding_count = 0

    for f in findings:
        if f.rule_id == "forbidden_payload":
            forbidden_payload_count += 1
        elif f.rule_id == "payload_too_large":
            payload_too_large_count += 1
        elif f.rule_id == "json_depth_exceeded":
            json_depth_exceeded_count += 1
        elif f.rule_id == "disallowed_domain":
            disallowed_domain_count += 1
        elif f.rule_id == "schema_parse_error":
            schema_parse_error_count += 1
        elif f.rule_id == "source_format_drift":
            source_format_drift_finding_count += 1

    format_drift_count = max(format_drift_count, source_format_drift_finding_count)

    for e in events:
        if not e.quarantine_reasons:
            source_integrity_pass += 1
        if e.trade_pair_mapping_status == "pass":
            trade_pair_mapping_pass += 1
        if e.source_timestamp_quality in (
            TimestampQuality.HIGH.value,
            TimestampQuality.MEDIUM.value,
        ):
            timestamp_quality_high_medium += 1

    source_integrity_rate = (
        source_integrity_pass / total_events if total_events > 0 else 0.0
    )
    trade_pair_mapping_rate = (
        trade_pair_mapping_pass / total_events if total_events > 0 else 0.0
    )
    timestamp_quality_ratio = (
        timestamp_quality_high_medium / total_events if total_events > 0 else 0.0
    )

    # 2. Per-source decisions
    source_decisions = {}
    finding_sources = {
        f.finding_details.get("source_name")
        for f in findings
        if f.finding_details and f.finding_details.get("source_name")
    }
    all_sources = sorted(source_names_set | finding_sources)
    if not all_sources and format_drift_count > 0:
        all_sources = ["unknown_source"]

    for src in all_sources:
        src_events = [e for e in events if e.source_name == src]
        src_findings = [
            f
            for f in findings
            if f.finding_details and f.finding_details.get("source_name") == src
        ]
        src_total = len(src_events)

        src_primary_events = [
            e
            for e in src_events
            if e.event_type
            in base.EXTERNAL_SIGNAL_STAGE1_5A_ELIGIBLE_EVENT_TYPES_FOR_STAGE1_5B
        ]
        src_primary_count = len(src_primary_events)

        src_days = set()
        src_syms = set()
        src_high_med_ts = 0
        src_integrity_pass = 0
        src_mapping_pass = 0

        for e in src_events:
            if e.source_published_at_ms:
                dt = datetime.datetime.utcfromtimestamp(
                    e.source_published_at_ms / 1000
                )
                src_days.add(dt.strftime("%Y-%m-%d"))
            if e.symbol:
                src_syms.add(e.symbol)
            if e.source_timestamp_quality in (
                TimestampQuality.HIGH.value,
                TimestampQuality.MEDIUM.value,
            ):
                src_high_med_ts += 1
            if not e.quarantine_reasons:
                src_integrity_pass += 1
            if e.trade_pair_mapping_status == "pass":
                src_mapping_pass += 1

        src_integrity_rate = (
            src_integrity_pass / src_total if src_total > 0 else 0.0
        )
        src_mapping_rate = src_mapping_pass / src_total if src_total > 0 else 0.0
        src_ts_ratio = src_high_med_ts / src_total if src_total > 0 else 0.0

        # Safety check on this source
        source_has_veto = (
            any(f.severity == "veto" for f in src_findings)
            or (
                not src_findings
                and src_total == 0
                and format_drift_count > 0
                and src == "unknown_source"
            )
        )

        if source_has_veto:
            src_decision = ExternalSignalSourceAuditDecision.FAILED.value
        else:
            density_passed = (
                src_total >= base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_HISTORICAL_EVENTS_FOUND
                and src_primary_count
                >= base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_PRIMARY_EVENT_TYPE_EVENTS
                and len(src_days)
                >= base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_UNIQUE_EVENT_DAYS
                and len(src_syms)
                >= base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_SYMBOLS_WITH_EVENTS
            )
            quality_passed = (
                src_integrity_rate
                >= base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_SOURCE_INTEGRITY_PASS_RATE
                and src_mapping_rate
                >= base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_TRADE_PAIR_MAPPING_PASS_RATE
                and src_ts_ratio
                >= base.EXTERNAL_SIGNAL_STAGE1_5A_MIN_TIMESTAMP_HIGH_OR_MEDIUM_RATIO
            )

            if density_passed and quality_passed:
                src_decision = ExternalSignalSourceAuditDecision.PASSED.value
            else:
                src_decision = (
                    ExternalSignalSourceAuditDecision.SPARSE.value
                )

        source_decisions[src] = {
            "decision": src_decision,
            "recommended_event_types_for_stage1_5b": [
                et.value
                for et in ExternalSignalEventType
                if et.value
                in base.EXTERNAL_SIGNAL_STAGE1_5A_ELIGIBLE_EVENT_TYPES_FOR_STAGE1_5B
                and src_decision
                == ExternalSignalSourceAuditDecision.PASSED.value
            ]
            if src_decision == ExternalSignalSourceAuditDecision.PASSED.value
            else [],
        }

    # 3. Per-event-type decisions
    event_type_decisions = {}
    for et in ExternalSignalEventType:
        et_val = et.value
        if et_val in base.EXTERNAL_SIGNAL_STAGE1_5A_OBSERVATION_ONLY_EVENT_TYPES:
            event_type_decisions[et_val] = (
                ExternalSignalSourceAuditDecision.OBSERVATION.value
            )
        else:
            # Gating check on this event type across all sources
            et_events = [e for e in events if e.event_type == et_val]
            et_total = len(et_events)

            et_days = set()
            et_syms = set()
            et_high_med_ts = 0
            et_integrity_pass = 0
            et_mapping_pass = 0

            for e in et_events:
                if e.source_published_at_ms:
                    dt = datetime.datetime.utcfromtimestamp(
                        e.source_published_at_ms / 1000
                    )
                    et_days.add(dt.strftime("%Y-%m-%d"))
                if e.symbol:
                    et_syms.add(e.symbol)
                if e.source_timestamp_quality in (
                    TimestampQuality.HIGH.value,
                    TimestampQuality.MEDIUM.value,
                ):
                    et_high_med_ts += 1
                if not e.quarantine_reasons:
                    et_integrity_pass += 1
                if e.trade_pair_mapping_status == "pass":
                    et_mapping_pass += 1

            et_integrity_rate = (
                et_integrity_pass / et_total if et_total > 0 else 0.0
            )
            et_mapping_rate = (
                et_mapping_pass / et_total if et_total > 0 else 0.0
            )
            et_ts_ratio = et_high_med_ts / et_total if et_total > 0 else 0.0

            has_veto = (
                any(
                    f.severity == "veto"
                    for f in findings
                    if f.finding_details
                    and f.finding_details.get("event_type") == et_val
                )
            )

            if has_veto:
                et_decision = ExternalSignalSourceAuditDecision.FAILED.value
            else:
                density_passed = (
                    et_total >= 20  # min count for single event type
                    and len(et_days) >= 15
                    and len(et_syms) >= 2
                )
                quality_passed = (
                    et_integrity_rate >= 0.90
                    and et_mapping_rate >= 0.90
                    and et_ts_ratio >= 0.90
                )

                if density_passed and quality_passed:
                    et_decision = (
                        ExternalSignalSourceAuditDecision.PASSED.value
                    )
                else:
                    et_decision = (
                        ExternalSignalSourceAuditDecision.SPARSE.value
                    )

            event_type_decisions[et_val] = et_decision

    # 4. Overall decision
    unattributed_veto = any(
        f.severity == "veto" and not (f.finding_details or {}).get("source_name")
        for f in findings
    )
    has_global_veto = (
        forbidden_payload_count > 0
        or disallowed_domain_count > 0
        or payload_too_large_count > 0
        or json_depth_exceeded_count > 0
        or schema_parse_error_count > 0
        or format_drift_count > 0
    )

    if unattributed_veto and has_global_veto:
        overall_decision = ExternalSignalSourceAuditDecision.FAILED.value
    else:
        # At least one source passed, and at least one eligible event type passed
        any_source_passed = any(
            sd["decision"] == ExternalSignalSourceAuditDecision.PASSED.value
            for sd in source_decisions.values()
        )
        any_eligible_et_passed = any(
            event_type_decisions[et.value]
            == ExternalSignalSourceAuditDecision.PASSED.value
            for et in ExternalSignalEventType
            if et.value
            in base.EXTERNAL_SIGNAL_STAGE1_5A_ELIGIBLE_EVENT_TYPES_FOR_STAGE1_5B
        )

        if any_source_passed and any_eligible_et_passed:
            overall_decision = ExternalSignalSourceAuditDecision.PASSED.value
        elif has_global_veto and not any_source_passed:
            overall_decision = ExternalSignalSourceAuditDecision.FAILED.value
        else:
            overall_decision = (
                ExternalSignalSourceAuditDecision.SPARSE.value
            )

    # 5. Timestamp quality distribution
    ts_qualities = [e.source_timestamp_quality for e in events]
    ts_dist = dict(Counter(ts_qualities))

    summary = {
        "stage": "external_signal_shadow_lab_stage1_5a",
        "scope": "historical_event_source_audit_only",
        "execution_engine_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "historical_replay_allowed": False,
        "live_smoke_allowed": False,
        "source_resource_safety_required": True,
        "event_type_mixing_allowed_for_replay_pass": False,
        "post_hoc_group_selection_allowed": False,
        "overall_decision": overall_decision,
        "source_decisions_required": True,
        "event_type_decisions_required": True,
        "research_result_valid": not fixture_run,
        "metrics": {
            "historical_events_found": total_events,
            "unique_event_days": len(unique_days_set),
            "symbols_with_events": len(symbols_set),
            "source_integrity_pass_rate": source_integrity_rate,
            "trade_pair_mapping_pass_rate": trade_pair_mapping_rate,
            "timestamp_quality_high_or_medium_ratio": timestamp_quality_ratio,
            "forbidden_payload_count": forbidden_payload_count,
            "payload_too_large_count": payload_too_large_count,
            "json_depth_exceeded_count": json_depth_exceeded_count,
            "disallowed_domain_count": disallowed_domain_count,
            "schema_parse_error_count": schema_parse_error_count,
            "timestamp_source_disagreement_count": disagreement_count,
            "source_format_drift_count": format_drift_count,
            "schema_quarantine_count": quarantine_count,
            "timestamp_quality_distribution": ts_dist,
            "raw_cache_written": bool(metrics.get("raw_cache_written", False)),
            "raw_cache_path": metrics.get("raw_cache_path", ""),
            "network_result_not_deterministic": bool(
                metrics.get("network_result_not_deterministic", False)
            ),
            "collector_received_at_ms": metrics.get("collector_received_at_ms"),
        },
        "source_decisions": source_decisions,
        "event_type_decisions": event_type_decisions,
    }

    return summary
