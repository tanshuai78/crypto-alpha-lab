from configs import base
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    compute_coverage_metrics,
)


def test_compute_expected_snapshot_count_from_stage1_5f_config():
    metrics = compute_coverage_metrics(
        states=[{"event_symbol_id": "es1", "depth_snapshot_count": 684, "max_gap_ms": 300000}],
        request_manifest_rows=[],
        summary={},
    )
    assert metrics["expected_snapshot_count"] == 720
    assert metrics["min_snapshot_count_required"] == 684
    assert metrics["snapshot_interval_ms"] == 60000
    assert metrics["blockers"] == []


def test_compute_expected_snapshot_count_from_summary_config_snapshot():
    summary = {
        "observation_window_ms": 3_600_000,
        "snapshot_interval_ms": 30_000,
        "min_snapshot_coverage_ratio": 0.90,
    }
    metrics = compute_coverage_metrics(
        states=[{"event_symbol_id": "es1", "depth_snapshot_count": 115, "max_gap_ms": 120000}],
        request_manifest_rows=[],
        summary=summary,
    )
    assert metrics["expected_snapshot_count"] == 120
    assert metrics["min_snapshot_count_required"] == 114
    assert metrics["snapshot_interval_ms"] == 30000
    assert metrics["blockers"] == []


def test_coverage_only_checks_formal_completed_event_symbols_when_provided():
    metrics = compute_coverage_metrics(
        states=[
            {
                "event_symbol_id": "formal_es1",
                "status": "completed",
                "depth_snapshot_count": 718,
                "max_gap_ms": 60000,
            },
            {
                "event_symbol_id": "active_es2",
                "status": "active",
                "depth_snapshot_count": 1,
                "max_gap_ms": 60000,
            },
        ],
        request_manifest_rows=[],
        summary={"observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        event_symbol_ids={"formal_es1"},
    )
    assert metrics["min_snapshot_count_required"] == 684
    assert metrics["checked_event_symbol_ids"] == ["formal_es1"]
    assert metrics["blockers"] == []


def test_coverage_uses_latest_state_per_formal_event_symbol_id():
    metrics = compute_coverage_metrics(
        states=[
            {
                "event_symbol_id": "formal_es1",
                "status": "active",
                "depth_snapshot_count": 1,
                "max_gap_ms": 60000,
            },
            {
                "event_symbol_id": "formal_es1",
                "status": "completed",
                "depth_snapshot_count": 718,
                "max_gap_ms": 60000,
            },
        ],
        request_manifest_rows=[],
        summary={"observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        event_symbol_ids={"formal_es1"},
    )
    assert metrics["checked_event_symbol_ids"] == ["formal_es1"]
    assert metrics["blockers"] == []


def test_coverage_blocks_when_observation_config_missing(monkeypatch):
    monkeypatch.delattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS", raising=False)
    monkeypatch.delattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC", raising=False)

    metrics = compute_coverage_metrics(states=[], request_manifest_rows=[], summary={})
    assert "missing_stage1_5f_observation_config" in metrics["blockers"]


def test_coverage_fails_when_per_symbol_request_success_rate_is_low():
    rows = [
        {"event_symbol_id": "es1", "symbol": "A", "http_status": 200},
        {"event_symbol_id": "es1", "symbol": "A", "http_status": 500},
    ]
    metrics = compute_coverage_metrics(
        states=[{"event_symbol_id": "es1", "depth_snapshot_count": 684, "max_gap_ms": 300000}],
        request_manifest_rows=rows,
        summary={"observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
    )
    assert metrics["per_symbol_request_success_rate_min"] == 0.5
    assert "per_symbol_request_success_rate_below_threshold" in metrics["blockers"]


def test_coverage_blocks_completed_manifest_rows_without_symbol_key():
    rows = [
        {
            "requested_host": "fapi.binance.com",
            "requested_path": "/fapi/v1/depth",
            "http_status": 200,
        }
    ]
    metrics = compute_coverage_metrics(
        states=[
            {
                "event_symbol_id": "es1",
                "status": "completed",
                "depth_snapshot_count": 684,
                "max_gap_ms": 300000,
            }
        ],
        request_manifest_rows=rows,
        summary={"observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
    )
    assert "request_manifest_symbol_key_missing" in metrics["blockers"]


def make_healthy_snapshots(event_symbol_id="es1", symbol="A", count=20):
    snapshots = []
    for i in range(count):
        snapshots.append(
            {
                "event_symbol_id": event_symbol_id,
                "symbol": symbol,
                "fetched_at_ms": i * 60000,
                "best_bid": 100.0,
                "best_ask": 100.1,
                "mid_price": 100.05,
                "spread_bps": 10.0,
                "buy_slippage_bps": 5.0,
                "sell_slippage_bps": 5.0,
                "top_bid_depth_usdt": 1000.0,
                "top_ask_depth_usdt": 1000.0,
            }
        )
    return snapshots


def make_mixed_quality_snapshots(healthy=5, unhealthy=95):
    snapshots = []
    # Healthy ones
    for i in range(healthy):
        snapshots.append(
            {
                "event_symbol_id": "es1",
                "symbol": "A",
                "fetched_at_ms": i * 60000,
                "best_bid": 100.0,
                "best_ask": 100.1,
                "mid_price": 100.05,
                "spread_bps": 10.0,
                "buy_slippage_bps": 5.0,
                "sell_slippage_bps": 5.0,
                "top_bid_depth_usdt": 1000.0,
                "top_ask_depth_usdt": 1000.0,
            }
        )
    # Unhealthy ones (thin book, high slippage)
    for i in range(unhealthy):
        snapshots.append(
            {
                "event_symbol_id": "es1",
                "symbol": "A",
                "fetched_at_ms": (healthy + i) * 60000,
                "best_bid": 100.0,
                "best_ask": 102.0,
                "mid_price": 101.0,
                "spread_bps": 200.0,  # exceeds max spread bps p95 (100)
                "buy_slippage_bps": 180.0,
                "sell_slippage_bps": 180.0,
                "top_bid_depth_usdt": 100.0,  # below min top bid depth p05 (250)
                "top_ask_depth_usdt": 100.0,
            }
        )
    return snapshots


def test_depth_quality_computes_p05_p50_p95_and_capacity_ratio():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        compute_depth_quality_metrics,
    )
    snapshots = make_healthy_snapshots(event_symbol_id="es1", symbol="A", count=20)
    result = compute_depth_quality_metrics(snapshots)

    assert result["spread_bps_p50"] is not None
    assert result["spread_bps_p95"] is not None
    assert result["top_bid_depth_usdt_p05"] is not None
    assert result["top_ask_depth_usdt_p05"] is not None
    assert result["depth_capacity_ratio_to_risk_cap_p50"] is not None
    assert result["blockers"] == []


def test_depth_quality_fails_on_low_healthy_window_ratio():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        compute_depth_quality_metrics,
    )
    snapshots = make_mixed_quality_snapshots(healthy=5, unhealthy=95)
    result = compute_depth_quality_metrics(snapshots)
    assert result["healthy_window_ratio"] == 0.05
    assert "healthy_window_ratio_below_threshold" in result["blockers"]


def test_stage1_5g_depth_request_health_ignores_stage1_5d_announcement_detail_deferred_rows():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        compute_depth_request_health,
    )
    rows = [
        {
            "request_type": "announcement_detail_deferred",
            "source_article_id": "article1",
            "defer_count": 4,
            "latest_defer_reason": "detail_budget_exhausted",
            "symbol": "ALL",
        }
    ]

    health = compute_depth_request_health(request_manifest_rows=rows, completed_states=[])

    assert health.depth_request_manifest_rows_count == 0
    assert health.scheduler_diagnostic_rows_count == 1
    assert health.per_symbol_request_success_rate_min is None
    assert "request_manifest_symbol_key_missing" not in health.blockers


def test_budget_starved_terminal_failure_is_recovery_only_not_formal_evidence():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        classify_stage1_5d_terminal_failure,
    )
    event = {
        "event_type": "futures_contract_launch",
        "symbols": [],
        "symbol_parse_status": "terminal_failed",
        "terminal_failure_type": "detail_never_attempted_budget_starved",
    }

    assert classify_stage1_5d_terminal_failure(event) == "collection_failure"


def test_quarantined_depth_quality_computes_correctly():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        RawSnapshotQuarantineResult,
        compute_quarantined_depth_quality,
    )
    # 706 valid, 12 invalid
    valid_rows = make_healthy_snapshots(count=706)
    invalid_rows = []

    quarantine_result = RawSnapshotQuarantineResult(
        blockers=[],
        warnings=[],
        clean_depth_evidence_pass=False,
        quarantined_depth_evidence_pass=True,
        quarantine_candidate=True,
        observed_snapshot_count=718,
        expected_snapshot_count=720,
        invalid_book_row_count=12,
        invalid_book_minute_bucket_count=1,
        invalid_book_ratio=12/718,
        invalid_book_ratio_observed=12/718,
        valid_snapshot_count_after_quarantine=706,
        book_availability_ratio=706/720,
        book_unavailable_ratio=12/720,
        invalid_book_by_phase={},
        invalid_book_by_reason={},
        launch_warmup_invalid_row_count=12,
        launch_warmup_invalid_minute_bucket_count=1,
        midrun_invalid_book_count=0,
        midrun_invalid_minute_bucket_count=0,
        crossed_or_negative_book_count=0,
        schema_invalid_count=0,
        max_consecutive_invalid=12,
        max_consecutive_invalid_after_warmup=0,
        first_valid_book_latency_ms=660000,
        depth_quality_input_rows=valid_rows,
        quarantined_invalid_book_rows=invalid_rows,
    )

    quality = compute_quarantined_depth_quality(quarantine_result)
    assert quality["depth_quality_clean_mode_available"] is False
    assert quality["depth_quality_quarantined_mode_available"] is True
    assert quality["depth_quality_input_mode"] == "quarantined_valid_rows"
    assert quality["depth_quality_input_row_count"] == 706
    assert quality["excluded_invalid_book_row_count"] == 12
    assert quality["book_availability_quality"]["availability_ratio"] == 706/720


def test_metrics_per_symbol_coverage_failure_with_other_symbols_passing():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        build_stage1_5g_review_summary,
    )
    symbols = ["SYM1", "SYM2"]
    states = [
        {"event_symbol_id": "es_SYM1", "status": "completed", "depth_snapshot_count": 720, "max_gap_ms": 60000},
        {"event_symbol_id": "es_SYM2", "status": "completed", "depth_snapshot_count": 500, "max_gap_ms": 60000},
    ]
    accepted_events = [
        {"event_symbol_id": f"es_{s}", "symbol": s, "evidence_label": "announcement_and_launch_time", "watermark_version": 1, "watermark_max_seen_detected_at_ms": 1000, "symbol_effective_launch_times_ms": {s: 1_000_000}}
        for s in symbols
    ]
    snapshots = [
        {"event_symbol_id": "es_SYM1", "symbol": "SYM1", "fetched_at_ms": 1_000_000 + i * 60000, "best_bid": 100.0, "best_ask": 100.1, "mid_price": 100.05, "spread_bps": 10.0, "buy_slippage_bps": 5.0, "sell_slippage_bps": 5.0, "top_bid_depth_usdt": 1000.0, "top_ask_depth_usdt": 1000.0}
        for i in range(720)
    ] + [
        {"event_symbol_id": "es_SYM2", "symbol": "SYM2", "fetched_at_ms": 1_000_000 + i * 60000, "best_bid": 100.0, "best_ask": 100.1, "mid_price": 100.05, "spread_bps": 10.0, "buy_slippage_bps": 5.0, "sell_slippage_bps": 5.0, "top_bid_depth_usdt": 1000.0, "top_ask_depth_usdt": 1000.0}
        for i in range(500)
    ]
    request_rows = [
        {"request_type": "depth_snapshot", "event_symbol_id": f"es_{s}", "symbol": s, "http_status": 200}
        for s in symbols for _ in range(720 if s == "SYM1" else 500)
    ]

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 2, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000, "min_snapshot_coverage_ratio": 0.95},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=request_rows,
    )

    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "insufficient_depth_snapshot_count" in result["blockers"]


def test_metrics_per_symbol_max_gap_failure_with_other_symbols_passing():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        build_stage1_5g_review_summary,
    )
    symbols = ["SYM1", "SYM2"]
    states = [
        {"event_symbol_id": "es_SYM1", "status": "completed", "depth_snapshot_count": 720, "max_gap_ms": 60000},
        {"event_symbol_id": "es_SYM2", "status": "completed", "depth_snapshot_count": 720, "max_gap_ms": 700000},
    ]
    accepted_events = [
        {"event_symbol_id": f"es_{s}", "symbol": s, "evidence_label": "announcement_and_launch_time", "watermark_version": 1, "watermark_max_seen_detected_at_ms": 1000, "symbol_effective_launch_times_ms": {s: 1_000_000}}
        for s in symbols
    ]
    snapshots = [
        {"event_symbol_id": f"es_{s}", "symbol": s, "fetched_at_ms": 1_000_000 + i * 60000, "best_bid": 100.0, "best_ask": 100.1, "mid_price": 100.05, "spread_bps": 10.0, "buy_slippage_bps": 5.0, "sell_slippage_bps": 5.0, "top_bid_depth_usdt": 1000.0, "top_ask_depth_usdt": 1000.0}
        for s in symbols for i in range(720)
    ]
    request_rows = [
        {"request_type": "depth_snapshot", "event_symbol_id": f"es_{s}", "symbol": s, "http_status": 200}
        for s in symbols for _ in range(720)
    ]

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 2, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000, "min_snapshot_coverage_ratio": 0.95},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=request_rows,
    )

    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "snapshot_gap_exceeded" in result["blockers"]
