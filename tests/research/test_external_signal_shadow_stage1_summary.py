def _summary(**overrides):
    payload = {
        "raw_payload_count": 3,
        "emitted_event_count": 1,
        "deduped_payload_count": 1,
        "quarantined_payload_count": 1,
        "rejected_payload_count": 0,
        "summary_accounting_ok": True,
        "live_trading_enabled": False,
        "exchange_paper_trading_allowed": False,
        "execution_engine_allowed": False,
        "research_shadow_replay_allowed": True,
        "wallet_required": False,
        "output_file": "events.jsonl",
        "output_file_sha256": "abc",
        "latency_p50_ms": 1000,
        "latency_p95_ms": 2000,
    }
    payload.update(overrides)
    return payload


def test_stage1_summary_passes_infrastructure_even_without_pnl():
    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    result = decide_stage1_connector_summary(_summary())

    assert result["decision"] == "external_signal_connector_stage1_passed"
    assert result["failure_type"] == "connector_completed"
    assert result["live_safe"] is False


def test_stage1_summary_fails_when_accounting_not_conservative():
    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    result = decide_stage1_connector_summary(_summary(summary_accounting_ok=False))

    assert result["decision"] == "external_signal_connector_stage1_failed"
    assert result["failure_type"] == "summary_accounting_failure"


def test_stage1_summary_fails_when_execution_flags_are_unsafe():
    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    result = decide_stage1_connector_summary(_summary(exchange_paper_trading_allowed=True))

    assert result["failure_type"] == "safety_failure"


def test_stage1_summary_prioritizes_safety_failure():
    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    result = decide_stage1_connector_summary(
        _summary(exchange_paper_trading_allowed=True, emitted_event_count=0)
    )

    assert result["failure_type"] == "safety_failure"


def test_stage1_summary_fails_when_no_events_emitted():
    from src.research.external_signal_shadow.connector_summary import (
        decide_stage1_connector_summary,
    )

    result = decide_stage1_connector_summary(_summary(emitted_event_count=0, raw_payload_count=1, deduped_payload_count=0, quarantined_payload_count=1))

    assert result["failure_type"] == "schema_failure"
