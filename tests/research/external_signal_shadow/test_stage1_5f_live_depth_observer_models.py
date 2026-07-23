from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
    DepthSnapshot,
    EventSymbolState,
    LiveDepthObserverDecision,
    LiveDepthObserverSummary,
    Watermark,
)


def test_decision_enum_values_are_exact():
    assert LiveDepthObserverDecision.BOOTSTRAP_WATERMARK_ONLY.value == "stage1_5f_observer_bootstrap_watermark_only"
    assert LiveDepthObserverDecision.RUNNING_NO_NEW_EVENT.value == "stage1_5f_observer_running_no_new_event"
    assert LiveDepthObserverDecision.EVENT_OBSERVATION_IN_PROGRESS.value == "stage1_5f_observer_event_observation_in_progress"
    assert LiveDepthObserverDecision.DEPTH_EVIDENCE_COLLECTED.value == "stage1_5f_observer_depth_evidence_collected"
    assert LiveDepthObserverDecision.INVALID.value == "stage1_5f_observer_invalid"
    assert LiveDepthObserverDecision.FAILED.value == "stage1_5f_observer_failed"


def test_watermark_model_requires_version():
    w = Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        seen_event_ids=["evt1"],
        seen_source_article_ids=["art1"],
        seen_stable_event_keys=["key1"],
        updated_at_ms=2000,
    )
    assert w.watermark_version == 1
    assert w.max_seen_detected_at_ms == 1000
    assert w.seen_event_ids == ["evt1"]


def test_event_symbol_state_contains_observation_window_fields():
    state = EventSymbolState(
        event_symbol_id="test_id",
        event_id="evt1",
        symbol="BTCUSDT",
        detected_at_ms=1000,
        observation_started_at_ms=2000,
        observation_window_end_ms=2000 + 12 * 3600 * 1000,
        status="active",
        depth_snapshot_count=0,
        last_snapshot_ms=0,
        max_gap_ms=0,
        coverage_ratio_pass=False,
        max_gap_pass=False,
        research_result_valid=False,
    )
    assert state.observation_window_end_ms == state.observation_started_at_ms + 12 * 3600 * 1000
    assert state.status == "active"


def test_depth_snapshot_contains_safety_and_metric_fields():
    snap = DepthSnapshot(
        event_symbol_id="test_id",
        symbol="BTCUSDT",
        fetched_at_ms=1000,
        exchange_time_ms=990,
        best_bid=100.0,
        best_ask=101.0,
        spread_bps=100.0,
        top_bid_depth_usdt=5000.0,
        top_ask_depth_usdt=5000.0,
        buy_slippage_bps=5.0,
        sell_slippage_bps=4.0,
        slippage_status="ok",
        depth_status="healthy",
    )
    assert snap.spread_bps == 100.0
    assert snap.buy_slippage_bps == 5.0
    assert snap.depth_status == "healthy"


def test_summary_defaults_never_allow_paper_live_execution_or_alpha():
    summary = LiveDepthObserverSummary(
        decision="stage1_5f_observer_invalid",
        bootstrap_watermark_allowed=False,
        live_depth_observation_allowed=False,
        stage1_5d_summary_path="dummy_path",
        stage1_5e_summary_path=None,
        stage1_5e_context_missing=True,
        stage1_5e_context_suspicious=False,
        watermark_present=False,
        watermark_version=None,
        max_seen_detected_at_ms=0,
        pre_watermark_events_ignored=0,
        post_watermark_events_accepted=0,
        active_observation_count=0,
        completed_observation_count=0,
        expired_observation_count=0,
        failed_observation_count=0,
        min_snapshot_count_required=576,
        total_snapshots_collected=0,
        request_success_rate=0.0,
        total_requests_made=0,
        failed_requests_count=0,
        consecutive_network_errors=0,
        max_consecutive_network_errors_seen=0,
        last_heartbeat_at_ms=0,
        heartbeat_count=0,
    )
    assert not summary.execution_feasibility_claim_allowed
    assert not summary.trade_signal_allowed
    assert not summary.paper_trading_allowed
    assert not summary.live_trading_allowed
    assert not summary.execution_engine_allowed
    assert not summary.alpha_interpretation_allowed
    assert not summary.research_result_valid


def test_event_symbol_state_uses_nullable_launch_anchor_fields():
    state = EventSymbolState(
        event_symbol_id="es1",
        event_id="e1",
        symbol="ABCUSDT",
        detected_at_ms=1_000,
        status="pending_launch_anchor_missing",
        observation_anchor_ms=None,
        observation_started_at_ms=None,
        first_depth_request_at_ms=None,
        first_healthy_snapshot_at_ms=None,
        observer_state_schema_version=2,
    )

    row = state.to_dict()
    assert row["observation_anchor_ms"] is None
    assert row["observation_started_at_ms"] is None
    assert row["first_depth_request_at_ms"] is None
    assert row["observer_state_schema_version"] == 2


def test_legacy_zero_timestamps_migrate_to_none_for_new_semantic_fields():
    row = {
        "event_symbol_id": "es1",
        "event_id": "e1",
        "symbol": "ABCUSDT",
        "status": "pending_launch_anchor_missing",
        "observation_anchor_ms": 0,
        "first_depth_request_at_ms": 0,
        "first_healthy_snapshot_at_ms": 0,
    }

    state = EventSymbolState.from_dict(row)

    assert state.observation_anchor_ms is None
    assert state.first_depth_request_at_ms is None
    assert state.first_healthy_snapshot_at_ms is None
