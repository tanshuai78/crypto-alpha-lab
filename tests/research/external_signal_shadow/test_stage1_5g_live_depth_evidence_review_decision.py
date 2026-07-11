import pytest
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    build_stage1_5g_review_summary,
)


def make_depth_snapshots(
    *,
    event_symbol_id="es1",
    symbol="BTC/USDT",
    count=700,
    best_bid=100.0,
    best_ask=100.1,
    mid_price=100.05,
    spread_bps=10.0,
    buy_slippage_bps=5.0,
    sell_slippage_bps=5.0,
    top_bid_depth_usdt=1000.0,
    top_ask_depth_usdt=1000.0,
):
    return [
        {
            "event_symbol_id": event_symbol_id,
            "symbol": symbol,
            "fetched_at_ms": i * 60000,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": mid_price,
            "spread_bps": spread_bps,
            "buy_slippage_bps": buy_slippage_bps,
            "sell_slippage_bps": sell_slippage_bps,
            "top_bid_depth_usdt": top_bid_depth_usdt,
            "top_ask_depth_usdt": top_ask_depth_usdt,
        }
        for i in range(count)
    ]


def test_decision_not_ready_without_completed_observation():
    summary = {"completed_observation_count": 0, "post_watermark_events_accepted": 0}
    result = build_stage1_5g_review_summary(
        summary=summary,
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 0},
        states=[],
        accepted_events=[],
        snapshots=[],
        request_manifest_rows=[],
    )
    assert result["decision"] == "stage1_5g_not_ready_no_completed_observation"
    assert result["allowed_next_action"] == "continue_observation"


def test_missing_watermark_is_invalid_not_not_ready():
    summary = {"completed_observation_count": 0, "post_watermark_events_accepted": 0}
    result = build_stage1_5g_review_summary(
        summary=summary,
        watermark={},
        states=[],
        accepted_events=[],
        snapshots=[],
        request_manifest_rows=[],
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "missing_or_unreadable_watermark" in result["blockers"]


def test_loader_parse_error_is_invalid():
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 0},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 0},
        states=[],
        accepted_events=[],
        snapshots=[],
        request_manifest_rows=[],
        loader_blockers=["jsonl_parse_error"],
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "jsonl_parse_error" in result["blockers"]


def build_fixture_review_summary(
    evidence_label="announcement_and_launch_time",
    state_status="completed",
    good_depth=True,
    request_manifest_rows=None,
):
    summary = {"completed_observation_count": 1 if state_status == "completed" else 0}
    watermark = {"watermark_version": 1, "max_seen_detected_at_ms": 1000}
    states = [
        {
            "event_symbol_id": "es1",
            "symbol": "BTC/USDT",
            "status": state_status,
            "depth_snapshot_count": 700 if good_depth else 100,
            "max_gap_ms": 60000,
        }
    ]
    accepted_events = [
        {
            "event_symbol_id": "es1",
            "symbol": "BTC/USDT",
            "evidence_label": evidence_label,
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
        }
    ]

    # Create mock snapshots. The row count must match state.depth_snapshot_count.
    if good_depth:
        snapshots = make_depth_snapshots(count=700)
    else:
        snapshots = make_depth_snapshots(
            count=100,
            best_ask=102.0,
            mid_price=101.0,
            spread_bps=200.0,
            buy_slippage_bps=180.0,
            sell_slippage_bps=180.0,
            top_bid_depth_usdt=100.0,
            top_ask_depth_usdt=100.0,
        )

    if request_manifest_rows is None:
        manifest = [{"event_symbol_id": "es1", "http_status": 200}]
    else:
        manifest = request_manifest_rows

    return build_stage1_5g_review_summary(
        summary=summary,
        watermark=watermark,
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=manifest,
    )


def test_launch_time_only_is_observation_only_even_with_good_depth():
    result = build_fixture_review_summary(evidence_label="launch_time_only", good_depth=True)
    assert result["decision"] == "stage1_5g_depth_evidence_observation_only"
    assert result["allowed_next_action"] == "continue_observation"


def test_recovery_validation_only_is_excluded_from_formal_evidence():
    result = build_fixture_review_summary(evidence_label="recovery_validation_only", good_depth=True)
    # The decision should be observation_only because formal evidence count is 0
    assert result["decision"] == "stage1_5g_depth_evidence_observation_only"
    assert result["evidence_label_counts"]["recovery_validation_only"] == 1
    assert result["formal_announcement_and_launch_count"] == 0


def test_valid_single_announcement_and_launch_time_allows_only_stage1_5h_design():
    result = build_fixture_review_summary(evidence_label="announcement_and_launch_time", good_depth=True)
    assert result["decision"] == "stage1_5g_depth_evidence_sufficient_for_stage1_5h_plan"
    assert result["allowed_next_action"] == "write_stage1_5h_shadow_execution_simulator_design"
    assert result["evidence_scope"] == "single_event"
    assert result["event_family_conclusion_allowed"] is False
    assert result["trade_signal_allowed"] is False


def test_live_depth_evidence_basis_alias_can_drive_formal_completed_evidence():
    summary = {"completed_observation_count": 1}
    watermark = {"watermark_version": 1, "max_seen_detected_at_ms": 1000}
    result = build_stage1_5g_review_summary(
        summary=summary,
        watermark=watermark,
        states=[
            {
                "event_symbol_id": "es1",
                "symbol": "SKHYUSDT",
                "status": "completed",
                "depth_snapshot_count": 700,
                "max_gap_ms": 60000,
            }
        ],
        accepted_events=[
            {
                "event_symbol_id": "es1",
                "event_id": "ev1",
                "symbol": "SKHYUSDT",
                "live_depth_evidence_basis": "announcement_and_launch_time",
                "watermark_version": 1,
                "watermark_max_seen_detected_at_ms": 1000,
            }
        ],
        snapshots=make_depth_snapshots(event_symbol_id="es1", symbol="SKHYUSDT", count=700),
        request_manifest_rows=[
            {
                "request_type": "depth_snapshot",
                "event_symbol_id": "es1",
                "event_id": "ev1",
                "symbol": "SKHYUSDT",
                "http_status": 200,
            }
        ],
    )

    assert "missing_evidence_label" not in result["blockers"]
    assert result["formal_announcement_and_launch_count"] == 1
    assert result["event_level_decisions"][0]["evidence_label"] == "announcement_and_launch_time"


def test_summary_includes_audit_replay_fields_for_sufficient_decision(tmp_path):
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[
            {
                "event_symbol_id": "es1",
                "symbol": "BTC/USDT",
                "status": "completed",
                "depth_snapshot_count": 700,
                "max_gap_ms": 60000,
            }
        ],
        accepted_events=[
            {
                "event_symbol_id": "es1",
                "event_id": "ev1",
                "symbol": "BTC/USDT",
                "source_article_id": "article1",
                "evidence_label": "announcement_and_launch_time",
                "watermark_version": 1,
                "watermark_max_seen_detected_at_ms": 1000,
            }
        ],
        snapshots=make_depth_snapshots(count=700),
        request_manifest_rows=[{"event_symbol_id": "es1", "http_status": 200}],
        output_root=tmp_path / "stage1_5f_root",
    )
    assert result["config_version"] == "configs/base.py:EXTERNAL_SIGNAL_STAGE1_5G_*"
    assert result["stage1_5f_output_root"] == str(tmp_path / "stage1_5f_root")
    assert result["watermark_max_seen_detected_at_ms"] == 1000
    assert result["reviewed_event_symbols"] == ["es1"]
    assert result["event_level_decisions"] == [
        {
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "BTC/USDT",
            "source_article_id": "article1",
            "evidence_label": "announcement_and_launch_time",
            "state_status": "completed",
            "depth_snapshot_count": 700,
            "formal_completed": True,
        }
    ]


def test_invalid_summary_includes_audit_replay_fields():
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 0},
        watermark={},
        states=[],
        accepted_events=[],
        snapshots=[],
        request_manifest_rows=[],
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert result["config_version"] == "configs/base.py:EXTERNAL_SIGNAL_STAGE1_5G_*"
    assert result["watermark_max_seen_detected_at_ms"] is None
    assert result["reviewed_event_symbols"] == []
    assert result["event_level_decisions"] == []


def test_accepted_but_active_announcement_and_launch_time_does_not_trigger_sufficient():
    result = build_fixture_review_summary(
        evidence_label="announcement_and_launch_time",
        state_status="active",
        good_depth=True,
    )
    assert result["decision"] != "stage1_5g_depth_evidence_sufficient_for_stage1_5h_plan"


def test_completed_observation_without_request_manifest_is_invalid():
    result = build_fixture_review_summary(
        evidence_label="announcement_and_launch_time",
        state_status="completed",
        good_depth=True,
        request_manifest_rows=[],
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "missing_request_manifest_for_completed_observation" in result["blockers"]


def build_fixture_review_summary_with_events(labels, source_article_ids, good_depth=True):
    # This builds a multi-event summary
    summary = {"completed_observation_count": len(labels)}
    watermark = {"watermark_version": 1, "max_seen_detected_at_ms": 1000}
    states = []
    accepted_events = []
    snapshots = []

    for i, (label, article_id) in enumerate(zip(labels, source_article_ids)):
        es_id = f"es_{i}"
        states.append(
            {
                "event_symbol_id": es_id,
                "symbol": f"SYM_{i}",
                "status": "completed",
                "depth_snapshot_count": 700 if good_depth else 100,
                "max_gap_ms": 60000,
            }
        )
        accepted_events.append(
            {
                "event_symbol_id": es_id,
                "symbol": f"SYM_{i}",
                "evidence_label": label,
                "source_article_id": article_id,
                "watermark_version": 1,
                "watermark_max_seen_detected_at_ms": 1000,
            }
        )
        if good_depth:
            snapshots.extend(make_depth_snapshots(event_symbol_id=es_id, symbol=f"SYM_{i}", count=700))
        else:
            snapshots.extend(
                make_depth_snapshots(
                    event_symbol_id=es_id,
                    symbol=f"SYM_{i}",
                    count=100,
                    best_ask=102.0,
                    mid_price=101.0,
                    spread_bps=200.0,
                    buy_slippage_bps=180.0,
                    sell_slippage_bps=180.0,
                    top_bid_depth_usdt=100.0,
                    top_ask_depth_usdt=100.0,
                )
            )

    manifest = [{"event_symbol_id": st["event_symbol_id"], "http_status": 200} for st in states]

    return build_stage1_5g_review_summary(
        summary=summary,
        watermark=watermark,
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=manifest,
    )


def test_event_family_scope_requires_three_symbols_and_two_articles():
    result = build_fixture_review_summary_with_events(
        labels=["announcement_and_launch_time", "announcement_and_launch_time", "announcement_and_launch_time"],
        source_article_ids=["a1", "a1", "a2"],
        good_depth=True,
    )
    assert result["event_family_conclusion_allowed"] is True
    assert result["evidence_scope"] == "event_family"


def test_decision_invalid_on_coverage_failure():
    # Scenario 5: coverage failure (too low snapshot count)
    result = build_fixture_review_summary(
        evidence_label="announcement_and_launch_time",
        state_status="completed",
        good_depth=False,  # fails coverage count
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "insufficient_depth_snapshot_count" in result["blockers"]


def test_decision_invalid_on_raw_snapshot_invalid():
    # Scenario 6: raw snapshot invalid ( crossed book in snapshots )
    summary = {"completed_observation_count": 1}
    watermark = {"watermark_version": 1, "max_seen_detected_at_ms": 1000}
    states = [
        {
            "event_symbol_id": "es1",
            "symbol": "BTC/USDT",
            "status": "completed",
            "depth_snapshot_count": 700,
            "max_gap_ms": 60000,
        }
    ]
    accepted_events = [
        {
            "event_symbol_id": "es1",
            "symbol": "BTC/USDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
        }
    ]
    snapshots = make_depth_snapshots(
        count=700,
        best_bid=105.0,
        best_ask=100.0,  # crossed book
        mid_price=102.5,
        spread_bps=-50.0,
    )
    manifest = [{"event_symbol_id": "es1", "http_status": 200}]

    result = build_stage1_5g_review_summary(
        summary=summary,
        watermark=watermark,
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=manifest,
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "invalid_book" in result["blockers"]


def test_decision_observation_only_on_thin_book_or_high_slippage():
    # Scenario 7: thin book / high slippage
    summary = {"completed_observation_count": 1}
    watermark = {"watermark_version": 1, "max_seen_detected_at_ms": 1000}
    states = [
        {
            "event_symbol_id": "es1",
            "symbol": "BTC/USDT",
            "status": "completed",
            "depth_snapshot_count": 700,
            "max_gap_ms": 60000,
        }
    ]
    accepted_events = [
        {
            "event_symbol_id": "es1",
            "symbol": "BTC/USDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
        }
    ]
    # Snapshot spread exceeds max spread bps (100) or slippage exceeds max
    snapshots = make_depth_snapshots(
        count=700,
        buy_slippage_bps=200.0,  # high slippage
        sell_slippage_bps=200.0,
    )
    manifest = [{"event_symbol_id": "es1", "http_status": 200}]

    result = build_stage1_5g_review_summary(
        summary=summary,
        watermark=watermark,
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=manifest,
    )
    assert result["decision"] == "stage1_5g_depth_evidence_observation_only"
    assert "buy_slippage_p95_above_threshold" in result["blockers"]


def test_decision_invalid_on_per_symbol_request_success_failure():
    # Scenario 8: per-symbol request success failure
    result = build_fixture_review_summary(
        evidence_label="announcement_and_launch_time",
        state_status="completed",
        good_depth=True,
        request_manifest_rows=[
            {"event_symbol_id": "es1", "http_status": 200},
            {"event_symbol_id": "es1", "http_status": 500},
        ],
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "per_symbol_request_success_rate_below_threshold" in result["blockers"]


def test_stage1_5g_accepts_completed_formal_evidence_with_symbol_keyed_manifest():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import build_stage1_5g_review_summary

    snapshots = make_depth_snapshots(event_symbol_id="es1", symbol="ETHUSD1", count=700)

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{
            "event_symbol_id": "es1",
            "symbol": "ETHUSD1",
            "status": "completed",
            "depth_snapshot_count": 700,
            "max_gap_ms": 60000,
        }],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "ETHUSD1",
            "source_article_id": "article1",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
        }],
        snapshots=snapshots,
        request_manifest_rows=[
            {
                "request_type": "depth_snapshot",
                "audit_metadata_version": 1,
                "event_symbol_id": "es1",
                "event_id": "ev1",
                "symbol": "ETHUSD1",
                "requested_path": "/fapi/v1/depth",
                "http_status": 200,
            }
        ],
    )

    assert "request_manifest_symbol_key_missing" not in result["blockers"]
    assert result["decision"] == "stage1_5g_depth_evidence_sufficient_for_stage1_5h_plan"


def test_stage1_5g_blocks_completed_formal_evidence_with_unkeyed_depth_manifest():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import build_stage1_5g_review_summary

    snapshots = make_depth_snapshots(event_symbol_id="es1", symbol="ETHUSD1", count=700)

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{
            "event_symbol_id": "es1",
            "symbol": "ETHUSD1",
            "status": "completed",
            "depth_snapshot_count": 700,
            "max_gap_ms": 60000,
        }],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "ETHUSD1",
            "source_article_id": "article1",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
        }],
        snapshots=snapshots,
        request_manifest_rows=[
            {
                "request_type": "depth_snapshot",
                "requested_path": "/fapi/v1/depth",
                "http_status": 200,
            }
        ],
    )
    assert "request_manifest_symbol_key_missing" in result["blockers"]
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
