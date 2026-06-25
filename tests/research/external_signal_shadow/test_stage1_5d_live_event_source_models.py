from src.research.external_signal_shadow.stage1_5d_live_event_source_models import (
    LiveEventSourceDecision,
    LiveFuturesLaunchEvent,
    PollHeartbeat,
)


def test_decision_enum_values():
    assert LiveEventSourceDecision.OBSERVATION_IN_PROGRESS.value == "stage1_5d_smoke_observation_in_progress"
    assert LiveEventSourceDecision.OPERATIONAL_UNVALIDATED.value == "stage1_5d_operational_pass_event_detection_unvalidated"
    assert LiveEventSourceDecision.EVENT_DETECTION_PASSED.value == "stage1_5d_event_detection_passed"
    assert LiveEventSourceDecision.FAILED.value == "stage1_5d_smoke_failed"
    assert LiveEventSourceDecision.INVALID.value == "stage1_5d_smoke_invalid"


def test_live_event_defaults_are_non_trading():
    event = LiveFuturesLaunchEvent(
        event_id="e1",
        event_type="futures_contract_launch",
        source_name="binance_official_announcements",
        source_profile="binance_official_announcements_like_rows",
        title="Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract",
        symbols=("ABCUSDT",),
        base_assets=("ABC",),
        detected_at_ms=1000,
        available_at_ms=1000,
    )
    assert event.paper_trading_allowed is False
    assert event.live_trading_allowed is False
    assert event.execution_engine_allowed is False
    assert event.alpha_interpretation_allowed is False
    assert event.trade_signal_allowed is False
    assert event.replay_context_label_only is True


def test_heartbeat_has_poll_timing_fields():
    hb = PollHeartbeat(
        poll_started_at_ms=1000,
        poll_completed_at_ms=1100,
        configured_poll_interval_sec=60,
    )
    assert hb.poll_duration_ms == 100
    assert hb.configured_poll_interval_sec == 60
