from src.research.external_signal_shadow.stage1_5a_source_audit_models import (
    ExternalSignalEventType,
    ExternalSignalSourceAuditDecision,
    NormalizedExternalEvent,
    SourceAuditFinding,
    TimestampQuality,
)
from src.research.external_signal_shadow.stage1_5a_source_audit_summary import (
    build_source_audit_summary,
)


def test_summary_contains_required_top_level_safety_flags():
    # GIVEN no events
    events = []
    metrics = {
        "timestamp_source_disagreement_count": 0,
        "source_format_drift_count": 0,
        "schema_quarantine_count": 0,
    }

    # WHEN
    summary = build_source_audit_summary(
        events=events,
        metrics=metrics,
        findings=[],
        fixture_run=True,
    )

    # THEN
    assert summary["stage"] == "external_signal_shadow_lab_stage1_5a"
    assert summary["scope"] == "historical_event_source_audit_only"
    assert summary["execution_engine_allowed"] is False
    assert summary["paper_trading_allowed"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["alpha_interpretation_allowed"] is False
    assert summary["historical_replay_allowed"] is False
    assert summary["live_smoke_allowed"] is False
    assert summary["source_resource_safety_required"] is True
    assert summary["event_type_mixing_allowed_for_replay_pass"] is False
    assert summary["post_hoc_group_selection_allowed"] is False

    # Decisions
    assert "overall_decision" in summary
    assert "source_decisions" in summary
    assert "event_type_decisions" in summary


def test_summary_fixture_run_marks_research_result_valid_false():
    summary = build_source_audit_summary([], {}, [], fixture_run=True)
    assert summary["research_result_valid"] is False


def test_summary_decision_passed_when_gates_pass():
    # GIVEN events that satisfy density gates
    # min global = 30, min primary = 20, min unique days = 20, min symbols = 3
    # let's generate 30 delisting events spread over 20 days across 3 symbols
    events = []
    base_time = 1710921600000
    for i in range(30):
        sym = f"SYM{i % 3}USDT"
        day_offset = i % 20
        evt_time = base_time + day_offset * 24 * 60 * 60 * 1000
        events.append(
            NormalizedExternalEvent(
                event_id=f"id-{i}",
                event_type=ExternalSignalEventType.DELISTING.value,
                symbol=sym,
                base_asset=f"SYM{i % 3}",
                quote_asset="USDT",
                venue="binance",
                source_name="binance_announcements",
                source_domain="binance.com",
                source_url="https://binance.com/announcement/1",
                source_parent_url="https://binance.com",
                source_published_at_ms=evt_time,
                event_time_ms=evt_time,
                available_at_ms=evt_time + 15 * 60 * 1000,
                collector_received_at_ms=evt_time + 15 * 60 * 1000,
                raw_payload_hash="raw-hash",
                event_payload_hash=f"event-hash-{i}",
                raw_payload_size_bytes=100,
                detail_url_available=True,
                source_integrity_level="full_detail",
                schema_version="v1",
                source_timestamp_quality=TimestampQuality.HIGH.value,
                historical_available_at_confidence="high",
                edited_page_risk=False,
                hindsight_risk=False,
                magnitude=1.0,
                base_asset_mapping_status="pass",
                trade_pair_mapping_status="pass",
                quarantine_reasons=[],
                replay_allowed=True,
                observation_only=False,
            )
        )

    metrics = {
        "timestamp_source_disagreement_count": 0,
        "source_format_drift_count": 0,
        "schema_quarantine_count": 0,
    }

    summary = build_source_audit_summary(events, metrics, [], fixture_run=False)
    assert summary["overall_decision"] == ExternalSignalSourceAuditDecision.PASSED.value
    assert summary["source_decisions"]["binance_announcements"]["decision"] == ExternalSignalSourceAuditDecision.PASSED.value
    assert summary["event_type_decisions"][ExternalSignalEventType.DELISTING.value] == ExternalSignalSourceAuditDecision.PASSED.value


def test_source_specific_veto_does_not_fail_unrelated_good_source():
    events = []
    base_time = 1710921600000
    for i in range(30):
        sym = f"SYM{i % 3}USDT"
        day_offset = i % 20
        evt_time = base_time + day_offset * 24 * 60 * 60 * 1000
        events.append(
            NormalizedExternalEvent(
                event_id=f"id-{i}",
                event_type=ExternalSignalEventType.DELISTING.value,
                symbol=sym,
                base_asset=f"SYM{i % 3}",
                quote_asset="USDT",
                venue="binance",
                source_name="good_binance",
                source_domain="binance.com",
                source_url="https://binance.com/announcement/1",
                source_parent_url="https://binance.com",
                source_published_at_ms=evt_time,
                event_time_ms=evt_time,
                available_at_ms=evt_time + 15 * 60 * 1000,
                collector_received_at_ms=evt_time + 15 * 60 * 1000,
                raw_payload_hash="raw-hash",
                event_payload_hash=f"event-hash-{i}",
                raw_payload_size_bytes=100,
                detail_url_available=True,
                source_integrity_level="full_detail",
                schema_version="v1",
                source_timestamp_quality=TimestampQuality.HIGH.value,
                historical_available_at_confidence="high",
                edited_page_risk=False,
                hindsight_risk=False,
                magnitude=1.0,
                base_asset_mapping_status="pass",
                trade_pair_mapping_status="pass",
                quarantine_reasons=[],
                replay_allowed=True,
                observation_only=False,
            )
        )

    findings = [
        SourceAuditFinding(
            rule_id="forbidden_payload",
            severity="veto",
            message="bad source has forbidden payload",
            finding_details={"source_name": "bad_source"},
        )
    ]

    summary = build_source_audit_summary(events, {}, findings, fixture_run=False)

    assert summary["source_decisions"]["good_binance"]["decision"] == ExternalSignalSourceAuditDecision.PASSED.value
    assert summary["overall_decision"] == ExternalSignalSourceAuditDecision.PASSED.value


def test_summary_includes_raw_cache_network_metadata():
    metrics = {
        "raw_cache_written": True,
        "raw_cache_path": "data/external_signal_shadow/stage1_5a/raw/20260622/binance",
        "network_result_not_deterministic": True,
        "collector_received_at_ms": 1710921605000,
    }

    summary = build_source_audit_summary([], metrics, [], fixture_run=False)

    assert summary["metrics"]["raw_cache_written"] is True
    assert summary["metrics"]["raw_cache_path"].endswith("/binance")
    assert summary["metrics"]["network_result_not_deterministic"] is True
    assert summary["metrics"]["collector_received_at_ms"] == 1710921605000


def test_summary_sparse_inconclusive_when_event_density_low():
    # Only 5 events (min required is 30)
    events = []
    base_time = 1710921600000
    for i in range(5):
        events.append(
            NormalizedExternalEvent(
                event_id=f"id-{i}",
                event_type=ExternalSignalEventType.DELISTING.value,
                symbol="BTCUSDT",
                base_asset="BTC",
                quote_asset="USDT",
                venue="binance",
                source_name="binance_announcements",
                source_domain="binance.com",
                source_url="https://binance.com/announcement/1",
                source_parent_url="https://binance.com",
                source_published_at_ms=base_time,
                event_time_ms=base_time,
                available_at_ms=base_time + 15 * 60 * 1000,
                collector_received_at_ms=base_time + 15 * 60 * 1000,
                raw_payload_hash="raw-hash",
                event_payload_hash=f"event-hash-{i}",
                raw_payload_size_bytes=100,
                detail_url_available=True,
                source_integrity_level="full_detail",
                schema_version="v1",
                source_timestamp_quality=TimestampQuality.HIGH.value,
                historical_available_at_confidence="high",
                edited_page_risk=False,
                hindsight_risk=False,
                magnitude=1.0,
                base_asset_mapping_status="pass",
                trade_pair_mapping_status="pass",
                quarantine_reasons=[],
                replay_allowed=True,
                observation_only=False,
            )
        )

    metrics = {
        "timestamp_source_disagreement_count": 0,
        "source_format_drift_count": 0,
        "schema_quarantine_count": 0,
    }

    summary = build_source_audit_summary(events, metrics, [], fixture_run=False)
    assert summary["overall_decision"] == ExternalSignalSourceAuditDecision.SPARSE.value


def test_summary_failed_when_forbidden_payload_exists():
    from src.research.external_signal_shadow.stage1_5a_source_audit_models import SourceAuditFinding
    findings = [
        SourceAuditFinding(
            rule_id="forbidden_payload",
            severity="veto",
            message="forbidden key found",
        )
    ]
    summary = build_source_audit_summary([], {}, findings, fixture_run=False)
    assert summary["overall_decision"] == ExternalSignalSourceAuditDecision.FAILED.value


def test_summary_failed_when_html_source_yields_zero_normalized_events():
    metrics = {
        "timestamp_source_disagreement_count": 0,
        "source_format_drift_count": 1,  # format drift happened
        "schema_quarantine_count": 0,
    }
    # No events
    summary = build_source_audit_summary([], metrics, [], fixture_run=False)
    assert summary["overall_decision"] == ExternalSignalSourceAuditDecision.FAILED.value
