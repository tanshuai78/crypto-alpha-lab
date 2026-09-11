import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    build_stage1_5g_review_summary,
    load_stage1_5g_inputs,
    verify_source_evidence_manifest,
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
    assert result["decision"] == "stage1_5g_depth_evidence_clean_pass"
    assert result["allowed_next_action"] == "write_stage1_5h_design_or_shadow_simulator_design"
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
    source_root = tmp_path / "stage1_5f_root"
    source_root.mkdir()
    (source_root / "SHA256SUMS").write_text(
        f"{'0' * 64}  {(source_root / 'SHA256SUMS').resolve()}\n",
        encoding="utf-8",
    )
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
        output_root=source_root,
    )
    assert result["config_version"] == "configs/base.py:EXTERNAL_SIGNAL_STAGE1_5G_*"
    assert result["stage1_5f_output_root"] == str(source_root)
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
    assert result["decision"] != "stage1_5g_depth_evidence_clean_pass"
    assert result["decision"] != "stage1_5g_depth_evidence_quarantined_pass"



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
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        build_stage1_5g_review_summary,
    )

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
    assert result["decision"] == "stage1_5g_depth_evidence_clean_pass"



def test_stage1_5g_blocks_completed_formal_evidence_with_unkeyed_depth_manifest():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        build_stage1_5g_review_summary,
    )

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


def make_skhy_quarantine_fixture():
    launch_ms = 1_000_000
    snapshots = make_depth_snapshots(event_symbol_id="es1", symbol="SKHYUSDT", count=718)
    for i, s in enumerate(snapshots):
        s["fetched_at_ms"] = launch_ms + i * 60_000
    for i in range(11):
        snapshots[i].update({
            "best_bid": None,
            "best_ask": None,
            "mid_price": None,
            "spread_bps": None,
            "depth_status": "invalid",
            "slippage_status": "invalid_depth",
            "top_bid_depth_usdt": 0.0,
            "top_ask_depth_usdt": 0.0,
            "buy_slippage_bps": None,
            "sell_slippage_bps": None,
        })
    snapshots[320].update({
        "best_bid": None,
        "best_ask": None,
        "mid_price": None,
        "spread_bps": None,
        "depth_status": "invalid",
        "slippage_status": "invalid_depth",
        "top_bid_depth_usdt": 0.0,
        "top_ask_depth_usdt": 0.0,
        "buy_slippage_bps": None,
        "sell_slippage_bps": None,
    })
    return launch_ms, snapshots



def test_skhyusdt_quarantine_candidate_allows_design_only_not_execution():
    launch_ms, snapshots = make_skhy_quarantine_fixture()
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "status": "completed",
            "depth_snapshot_count": 718,
            "max_gap_ms": 60_000,
            "observation_started_at_ms": launch_ms,
        }],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        snapshots=snapshots,
        request_manifest_rows=[{
            "request_type": "depth_snapshot",
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "http_status": 200,
        } for _ in range(718)],
    )

    assert result["decision"] == "stage1_5g_depth_evidence_quarantined_pass"
    assert result["allowed_next_action"] == "write_stage1_5h_design_only"
    assert result["clean_depth_evidence_pass"] is False
    assert result["quarantined_depth_evidence_pass"] is True
    assert result["execution_feasibility_claim_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False
    assert result["quarantine"]["formal_completed_symbol_count"] == 1
    assert result["quarantine"]["aggregate_observed_snapshot_count"] == 718
    assert result["quarantine"]["per_symbol_expected_snapshot_count"] == 720
    assert result["quarantine"]["per_symbol_expected_snapshot_count"] == result["coverage_metrics"]["expected_snapshot_count"]
    assert result["quarantine"]["aggregate_invalid_book_ratio"] == 12 / 718
    assert result["quarantine"]["aggregate_book_availability_ratio"] >= 0.98
    assert result["quarantine"]["midrun_invalid_book_count"] == 1
    assert "depth_quality_input_rows" not in result["quarantine"]
    assert "quarantined_invalid_book_rows" not in result["quarantine"]


def test_two_midrun_invalid_books_keep_depth_evidence_invalid():
    launch_ms, snapshots = make_skhy_quarantine_fixture()
    snapshots[400].update(snapshots[320])
    snapshots[400]["fetched_at_ms"] = launch_ms + 400 * 60_000

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "status": "completed", "depth_snapshot_count": 718, "max_gap_ms": 60_000}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        snapshots=snapshots,
        request_manifest_rows=[{"request_type": "depth_snapshot", "event_symbol_id": "es1", "symbol": "SKHYUSDT", "http_status": 200} for _ in range(718)],
    )

    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "midrun_invalid_book_count_exceeded" in result["blockers"]


def test_quarantine_cannot_promote_observation_only_evidence_to_quarantined_pass():
    launch_ms, snapshots = make_skhy_quarantine_fixture()
    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "status": "completed", "depth_snapshot_count": 718, "max_gap_ms": 60_000}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "evidence_label": "launch_time_only",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        snapshots=snapshots,
        request_manifest_rows=[{"request_type": "depth_snapshot", "event_symbol_id": "es1", "symbol": "SKHYUSDT", "http_status": 200} for _ in range(718)],
    )

    assert result["decision"] != "stage1_5g_depth_evidence_quarantined_pass"
    assert result["formal_announcement_and_launch_count"] == 0
    assert result.get("quarantined_depth_evidence_pass") is not True


def test_quarantine_expected_snapshot_count_missing_does_not_fallback_to_observed_rows(monkeypatch):
    from configs import base

    monkeypatch.delattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS", raising=False)
    monkeypatch.delattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC", raising=False)
    launch_ms, snapshots = make_skhy_quarantine_fixture()

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 1},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "status": "completed", "depth_snapshot_count": 718, "max_gap_ms": 60_000}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "event_id": "ev1",
            "symbol": "SKHYUSDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        snapshots=snapshots,
        request_manifest_rows=[{"request_type": "depth_snapshot", "event_symbol_id": "es1", "symbol": "SKHYUSDT", "http_status": 200} for _ in range(718)],
    )

    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "missing_stage1_5f_observation_config" in result["blockers"] or "expected_snapshot_count_missing" in result["blockers"]
    assert result.get("quarantined_depth_evidence_pass") is not True


def test_chinese_review_includes_quarantine_section_for_quarantined_pass():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        generate_stage1_5g_chinese_review,
    )

    markdown = generate_stage1_5g_chinese_review({
        "decision": "stage1_5g_depth_evidence_quarantined_pass",
        "allowed_next_action": "write_stage1_5h_design_only",
        "evidence_scope": "single_event",
        "event_family_conclusion_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "execution_feasibility_claim_allowed": False,
        "blockers": [],
        "warnings": ["not_clean_depth_evidence"],
        "formal_announcement_and_launch_count": 1,
        "evidence_label_counts": {"announcement_and_launch_time": 1},
        "coverage_metrics": {},
        "raw_integrity": {"invalid_book_count": 12},
        "depth_quality": {},
        "quarantine": {
            "invalid_book_row_count": 12,
            "book_availability_ratio": 0.9806,
            "first_valid_book_latency_ms": 660000,
            "max_consecutive_invalid": 11,
            "max_consecutive_invalid_after_warmup": 1,
            "execution_availability_claim": "partial_not_clean",
        },
    })

    assert "Quarantine" in markdown or "隔离" in markdown
    assert "write_stage1_5h_design_only" in markdown
    assert "formal_completed_symbol_count" in markdown


def test_chinese_review_includes_per_symbol_table_for_multi_symbol_quarantine():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        generate_stage1_5g_chinese_review,
    )

    markdown = generate_stage1_5g_chinese_review({
        "decision": "stage1_5g_depth_evidence_quarantined_pass",
        "allowed_next_action": "write_stage1_5h_design_only",
        "evidence_scope": "event_family",
        "event_family_conclusion_allowed": True,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "execution_feasibility_claim_allowed": False,
        "blockers": [],
        "warnings": [],
        "formal_announcement_and_launch_count": 2,
        "evidence_label_counts": {"announcement_and_launch_time": 2},
        "coverage_metrics": {},
        "raw_integrity": {},
        "depth_quality": {},
        "quarantine": {
            "formal_completed_symbol_count": 2,
            "aggregate_invalid_book_row_count": 2,
            "aggregate_book_availability_ratio": 0.99,
            "per_symbol_quarantine_metrics": {
                "es1": {"observed_snapshot_count": 720, "valid_snapshot_count_after_quarantine": 719, "invalid_book_row_count": 1, "book_availability_ratio": 0.998, "first_valid_book_latency_ms": 60000, "quarantined_depth_evidence_pass": True},
                "es2": {"observed_snapshot_count": 720, "valid_snapshot_count_after_quarantine": 719, "invalid_book_row_count": 1, "book_availability_ratio": 0.998, "first_valid_book_latency_ms": 60000, "quarantined_depth_evidence_pass": True},
            },
        },
    })

    assert "逐币 Quarantine 明细" in markdown
    assert "es1" in markdown
    assert "es2" in markdown



def test_decision_aggregate_camouflage_one_symbol_insufficient_snapshots():
    symbols = [f"SYM{i}" for i in range(5)]
    states = [
        {"event_symbol_id": f"es_{s}", "status": "completed", "depth_snapshot_count": 720 if s != "SYM4" else 650, "max_gap_ms": 60000}
        for s in symbols
    ]
    accepted_events = [
        {
            "event_symbol_id": f"es_{s}",
            "symbol": s,
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {s: 1_000_000},
        }
        for s in symbols
    ]
    snapshots = []
    for s in symbols:
        cnt = 720 if s != "SYM4" else 650
        for i in range(cnt):
            snapshots.append({
                "event_symbol_id": f"es_{s}",
                "symbol": s,
                "fetched_at_ms": 1_000_000 + i * 60000,
                "best_bid": 100.0,
                "best_ask": 100.1,
                "mid_price": 100.05,
                "spread_bps": 10.0,
                "buy_slippage_bps": 5.0,
                "sell_slippage_bps": 5.0,
                "top_bid_depth_usdt": 1000.0,
                "top_ask_depth_usdt": 1000.0,
            })
    request_rows = [
        {"request_type": "depth_snapshot", "event_symbol_id": f"es_{s}", "symbol": s, "http_status": 200}
        for s in symbols for _ in range(720 if s != "SYM4" else 650)
    ]

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 5, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000, "min_snapshot_coverage_ratio": 0.95},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=request_rows,
    )

    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "insufficient_depth_snapshot_count" in result["blockers"]


def test_decision_aggregate_camouflage_invalid_rows_concentrated_in_one_symbol():
    symbols = [f"SYM{i}" for i in range(5)]
    states = [
        {"event_symbol_id": f"es_{s}", "status": "completed", "depth_snapshot_count": 718, "max_gap_ms": 60000}
        for s in symbols
    ]
    accepted_events = [
        {
            "event_symbol_id": f"es_{s}",
            "symbol": s,
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {s: 1_000_000},
        }
        for s in symbols
    ]
    snapshots = []
    for s in symbols:
        for i in range(718):
            row = {
                "event_symbol_id": f"es_{s}",
                "symbol": s,
                "fetched_at_ms": 1_000_000 + i * 60000,
                "best_bid": 100.0,
                "best_ask": 100.1,
                "mid_price": 100.05,
                "spread_bps": 10.0,
                "buy_slippage_bps": 5.0,
                "sell_slippage_bps": 5.0,
                "top_bid_depth_usdt": 1000.0,
                "top_ask_depth_usdt": 1000.0,
            }
            # Add 2 midrun invalid rows only to SYM0
            if s == "SYM0" and i in (100, 200):
                row.update({"best_bid": None, "best_ask": None, "spread_bps": None})
            snapshots.append(row)

    request_rows = [
        {"request_type": "depth_snapshot", "event_symbol_id": f"es_{s}", "symbol": s, "http_status": 200}
        for s in symbols for _ in range(718)
    ]

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 5, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000, "min_snapshot_coverage_ratio": 0.95},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=request_rows,
    )

    # SYM0 has 2 midrun invalid rows exceeding limit 1 -> must fail
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "per_symbol_quarantine_gate_failed" in result["blockers"] or "midrun_invalid_book_count_exceeded" in result["blockers"]


def seal_disposable_stage1_5f_source_root(root: Path) -> None:
    baseline_dir = os.environ.get("STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR")
    if not baseline_dir:
        path_file = Path(".git/plan-execution/20260910T072434Z/path.txt")
        if path_file.exists():
            baseline_dir = path_file.read_text().strip()
    command = Path(baseline_dir).joinpath(
        "runbook_sha256sums_sealing_command.sh"
    ).read_text(encoding="utf-8")
    subprocess.run(
        ["sh", "-c", command],
        env={**os.environ, "LOCAL_EVIDENCE_ROOT": str(root)},
        check=True,
    )
    ok, _, blockers = verify_source_evidence_manifest(root)
    assert ok is True, f"manifest verification failed: {blockers}"


def test_seal_disposable_stage1_5f_source_root_matches_runbook_command():
    baseline_dir = os.environ.get("STAGE1_5G_RUNTIME_ATTESTATION_GATE_BASELINE_DIR", ".git/plan-execution/20260910T072434Z")
    saved_sha = Path(baseline_dir, "runbook_sha256sums_sealing_command.sha256").read_text().strip()
    runbook_text = Path("docs/ops/2026-09-03-stage1-5d-1-5f-vps-deployment-and-operations-runbook_CN.md").read_text(encoding="utf-8")
    matches = [line for line in runbook_text.splitlines(keepends=True) if 'find "$LOCAL_EVIDENCE_ROOT" -type f -exec shasum -a 256' in line]
    assert len(matches) == 1
    assert hashlib.sha256(matches[0].encode("utf-8")).hexdigest() == saved_sha


def make_canonical_stage1_5f_source_root(
    root: Path,
    *,
    summary_overrides: dict | None = None,
    contract_overrides: dict | None = None,
    omit_contract: bool = False,
    seal: bool = True,
) -> Path:
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        write_live_depth_observer_summary_atomically,
        write_observer_root_contract_atomically,
    )
    from src.research.external_signal_shadow.safety import canonical_json_dumps
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    if not any(anc.name == "external_signal_shadow" and anc.parent.name == "data" for anc in [root] + list(root.parents)):
        root = root / "data" / "external_signal_shadow" / "stage1_5f_source"
    root.mkdir(parents=True, exist_ok=True)
    guard = StorageGuard(output_root=root, stage="1.5F")

    contract_sha = "0" * 64
    if not omit_contract:
        source_d_root_id = "0" * 64
        root_facts = {
            "consumer_process_instance_id": "11111111-2222-3333-4444-555555555555",
            "consumer_root_id": "a" * 64,
            "consumer_startup_commit_sha": "b" * 40,
            "consumer_runtime_manifest_sha256": "c" * 64,
            "consumer_static_attestation_verified": True,
            "source_stage1_5d_output_root_id": source_d_root_id,
            "source_stage1_5d_events_root_id": source_d_root_id,
            "source_stage1_5d_runtime_gate_root_id": source_d_root_id,
        }
        if contract_overrides:
            root_facts.update(contract_overrides)
        contract = write_observer_root_contract_atomically(
            str(root),
            "v2_production",
            reason="runtime_start",
            storage_guard=guard,
            source_binding_facts=root_facts,
        )
        contract_sha = hashlib.sha256(canonical_json_dumps(contract).encode("utf-8")).hexdigest()

    summary_dict = {
        "decision": "stage1_5f_observer_depth_evidence_collected",
        "bootstrap_watermark_allowed": False,
        "live_depth_observation_allowed": True,
        "stage1_5d_summary_path": "stage1_5d.json",
        "stage1_5e_summary_path": "stage1_5e.json",
        "stage1_5e_context_missing": False,
        "stage1_5e_context_suspicious": False,
        "watermark_present": True,
        "watermark_version": 1,
        "max_seen_detected_at_ms": 1000,
        "pre_watermark_events_ignored": 0,
        "post_watermark_events_accepted": 1,
        "active_observation_count": 0,
        "completed_observation_count": 1,
        "expired_observation_count": 0,
        "failed_observation_count": 0,
        "observation_window_ms": 300_000,
        "snapshot_interval_ms": 60_000,
        "min_snapshot_count_required": 5,
        "total_snapshots_collected": 5,
        "request_success_rate": 1.0,
        "total_requests_made": 5,
        "failed_requests_count": 0,
        "consecutive_network_errors": 0,
        "max_consecutive_network_errors_seen": 0,
        "last_heartbeat_at_ms": 2_000_000,
        "heartbeat_count": 1,
        "consumer_process_instance_id": "11111111-2222-3333-4444-555555555555",
        "consumer_process_started_at_ms": 1_000_000,
        "consumer_root_id": "a" * 64,
        "consumer_startup_commit_sha": "b" * 40,
        "consumer_root_contract_sha256": contract_sha,
        "consumer_runtime_manifest_sha256": "c" * 64,
        "consumer_static_attestation_verified": True,
        "consumer_runtime_attestation_verified": True,
        "consumer_runtime_attestation_compromised": False,
    }
    if summary_overrides:
        summary_dict.update(summary_overrides)
    write_live_depth_observer_summary_atomically(
        root / "live_depth_observer_summary.json",
        summary_dict,
        storage_guard=guard,
    )

    (root / "watermark.json").write_text(json.dumps({
        "watermark_version": 1,
        "max_seen_detected_at_ms": 1000,
        "seen_event_ids": ["ev1"],
    }), encoding="utf-8")

    (root / "observer_state.jsonl").write_text(json.dumps({
        "event_symbol_id": "es1",
        "symbol": "BTCUSDT",
        "status": "completed",
        "depth_snapshot_count": 5,
    }) + "\n", encoding="utf-8")

    (root / "events_accepted").mkdir(parents=True, exist_ok=True)
    (root / "events_accepted" / "2026-09-08.jsonl").write_text(json.dumps({
        "event_symbol_id": "es1",
        "symbol": "BTCUSDT",
        "event_id": "ev1",
        "source_article_id": "art1",
        "evidence_label": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
    }) + "\n", encoding="utf-8")

    (root / "events_rejected").mkdir(parents=True, exist_ok=True)
    (root / "events_rejected" / "empty.jsonl").write_text("", encoding="utf-8")

    (root / "depth_snapshots" / "BTCUSDT").mkdir(parents=True, exist_ok=True)
    (root / "depth_snapshots" / "BTCUSDT" / "snapshots.jsonl").write_text("\n".join(
        json.dumps({
            "event_symbol_id": "es1",
            "symbol": "BTCUSDT",
            "fetched_at_ms": 1_000_000 + i * 60_000,
            "best_bid": 100.0,
            "best_ask": 100.1,
            "mid_price": 100.05,
            "spread_bps": 10.0,
            "buy_slippage_bps": 5.0,
            "sell_slippage_bps": 5.0,
            "top_bid_depth_usdt": 1000.0,
            "top_ask_depth_usdt": 1000.0,
        }) for i in range(5)
    ) + "\n", encoding="utf-8")

    (root / "request_manifest").mkdir(parents=True, exist_ok=True)
    (root / "request_manifest" / "2026-09-08.jsonl").write_text("\n".join(
        json.dumps({
            "request_type": "depth_snapshot",
            "event_symbol_id": "es1",
            "symbol": "BTCUSDT",
            "http_status": 200,
        }) for _ in range(5)
    ) + "\n", encoding="utf-8")

    (root / "heartbeat").mkdir(parents=True, exist_ok=True)
    (root / "heartbeat" / "2026-09-08.jsonl").write_text(json.dumps({
        "poll_at_ms": 2_000_000,
        "active_observation_count": 0,
    }) + "\n", encoding="utf-8")

    if seal:
        seal_disposable_stage1_5f_source_root(root)
    return root


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("consumer_runtime_attestation_verified", False, "source_runtime_attestation_unverified"),
        ("consumer_runtime_attestation_verified", "false", "source_runtime_attestation_verified_field_invalid"),
        ("consumer_runtime_attestation_compromised", True, "source_runtime_attestation_compromised"),
        ("consumer_runtime_attestation_compromised", "false", "source_runtime_attestation_compromised_field_invalid"),
    ],
)
def test_runtime_gate_boolean_precedence(tmp_path, field, value, expected):
    root = make_canonical_stage1_5f_source_root(tmp_path / "root", summary_overrides={field: value})
    bundle = load_stage1_5g_inputs(root)
    result = build_stage1_5g_review_summary(
        summary=bundle.summary,
        watermark=bundle.watermark,
        states=bundle.states,
        accepted_events=bundle.accepted_events,
        snapshots=bundle.snapshots,
        request_manifest_rows=bundle.request_manifest_rows,
        output_root=root,
        loader_blockers=bundle.loader_blockers,
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert result["blockers"] == [expected]


def test_runtime_gate_canonical_root_passes(tmp_path):
    root = make_canonical_stage1_5f_source_root(tmp_path / "root")
    bundle = load_stage1_5g_inputs(root)
    result = build_stage1_5g_review_summary(
        summary=bundle.summary,
        watermark=bundle.watermark,
        states=bundle.states,
        accepted_events=bundle.accepted_events,
        snapshots=bundle.snapshots,
        request_manifest_rows=bundle.request_manifest_rows,
        output_root=root,
        loader_blockers=bundle.loader_blockers,
    )
    assert result["decision"] in ("stage1_5g_depth_evidence_quarantined_pass", "stage1_5g_depth_evidence_clean_pass")
    assert result["blockers"] == []


def test_runtime_gate_static_cases(tmp_path):
    r1 = make_canonical_stage1_5f_source_root(
        tmp_path / "r1",
        summary_overrides={"consumer_static_attestation_verified": False},
        contract_overrides={"consumer_static_attestation_verified": False},
    )
    b1 = load_stage1_5g_inputs(r1)
    res1 = build_stage1_5g_review_summary(
        summary=b1.summary, watermark=b1.watermark, states=b1.states,
        accepted_events=b1.accepted_events, snapshots=b1.snapshots,
        request_manifest_rows=b1.request_manifest_rows, output_root=r1,
        loader_blockers=b1.loader_blockers,
    )
    assert res1["decision"] == "stage1_5g_depth_evidence_invalid"
    assert res1["blockers"] == ["source_static_attestation_unverified"]

    r2 = make_canonical_stage1_5f_source_root(
        tmp_path / "r2",
        summary_overrides={"consumer_static_attestation_verified": False},
        contract_overrides={"consumer_static_attestation_verified": True},
    )
    b2 = load_stage1_5g_inputs(r2)
    res2 = build_stage1_5g_review_summary(
        summary=b2.summary, watermark=b2.watermark, states=b2.states,
        accepted_events=b2.accepted_events, snapshots=b2.snapshots,
        request_manifest_rows=b2.request_manifest_rows, output_root=r2,
        loader_blockers=b2.loader_blockers,
    )
    assert res2["decision"] == "stage1_5g_depth_evidence_invalid"
    assert res2["blockers"] == ["source_runtime_attestation_contract_summary_binding_invalid"]

    r3 = make_canonical_stage1_5f_source_root(
        tmp_path / "r3",
        summary_overrides={"consumer_static_attestation_verified": "true"},
    )
    b3 = load_stage1_5g_inputs(r3)
    res3 = build_stage1_5g_review_summary(
        summary=b3.summary, watermark=b3.watermark, states=b3.states,
        accepted_events=b3.accepted_events, snapshots=b3.snapshots,
        request_manifest_rows=b3.request_manifest_rows, output_root=r3,
        loader_blockers=b3.loader_blockers,
    )
    assert res3["decision"] == "stage1_5g_depth_evidence_invalid"
    assert res3["blockers"] == ["source_static_attestation_field_invalid"]

    r4 = make_canonical_stage1_5f_source_root(
        tmp_path / "r4",
        contract_overrides={"consumer_static_attestation_verified": 1},
    )
    b4 = load_stage1_5g_inputs(r4)
    res4 = build_stage1_5g_review_summary(
        summary=b4.summary, watermark=b4.watermark, states=b4.states,
        accepted_events=b4.accepted_events, snapshots=b4.snapshots,
        request_manifest_rows=b4.request_manifest_rows, output_root=r4,
        loader_blockers=b4.loader_blockers,
    )
    assert res4["decision"] == "stage1_5g_depth_evidence_invalid"
    assert res4["blockers"] == ["source_static_attestation_field_invalid"]


def test_runtime_gate_binding_cases(tmp_path):
    r1 = make_canonical_stage1_5f_source_root(
        tmp_path / "r1",
        summary_overrides={"consumer_process_started_at_ms": None},
    )
    b1 = load_stage1_5g_inputs(r1)
    res1 = build_stage1_5g_review_summary(
        summary=b1.summary, watermark=b1.watermark, states=b1.states,
        accepted_events=b1.accepted_events, snapshots=b1.snapshots,
        request_manifest_rows=b1.request_manifest_rows, output_root=r1,
        loader_blockers=b1.loader_blockers,
    )
    assert res1["blockers"] == ["source_runtime_attestation_contract_summary_binding_invalid"]

    r2 = make_canonical_stage1_5f_source_root(
        tmp_path / "r2",
        summary_overrides={"consumer_process_started_at_ms": 0},
    )
    b2 = load_stage1_5g_inputs(r2)
    res2 = build_stage1_5g_review_summary(
        summary=b2.summary, watermark=b2.watermark, states=b2.states,
        accepted_events=b2.accepted_events, snapshots=b2.snapshots,
        request_manifest_rows=b2.request_manifest_rows, output_root=r2,
        loader_blockers=b2.loader_blockers,
    )
    assert res2["blockers"] == ["source_runtime_attestation_contract_summary_binding_invalid"]

    r3 = make_canonical_stage1_5f_source_root(
        tmp_path / "r3",
        summary_overrides={"consumer_process_started_at_ms": True},
    )
    b3 = load_stage1_5g_inputs(r3)
    res3 = build_stage1_5g_review_summary(
        summary=b3.summary, watermark=b3.watermark, states=b3.states,
        accepted_events=b3.accepted_events, snapshots=b3.snapshots,
        request_manifest_rows=b3.request_manifest_rows, output_root=r3,
        loader_blockers=b3.loader_blockers,
    )
    assert res3["blockers"] == ["source_runtime_attestation_contract_summary_binding_invalid"]

    r4 = make_canonical_stage1_5f_source_root(
        tmp_path / "r4",
        summary_overrides={"consumer_process_started_at_ms": 3_000_000, "last_heartbeat_at_ms": 2_000_000},
    )
    b4 = load_stage1_5g_inputs(r4)
    res4 = build_stage1_5g_review_summary(
        summary=b4.summary, watermark=b4.watermark, states=b4.states,
        accepted_events=b4.accepted_events, snapshots=b4.snapshots,
        request_manifest_rows=b4.request_manifest_rows, output_root=r4,
        loader_blockers=b4.loader_blockers,
    )
    assert res4["blockers"] == ["source_runtime_attestation_contract_summary_binding_invalid"]

    r5 = make_canonical_stage1_5f_source_root(
        tmp_path / "r5",
        summary_overrides={"consumer_process_instance_id": "NOT-A-UUID"},
    )
    b5 = load_stage1_5g_inputs(r5)
    res5 = build_stage1_5g_review_summary(
        summary=b5.summary, watermark=b5.watermark, states=b5.states,
        accepted_events=b5.accepted_events, snapshots=b5.snapshots,
        request_manifest_rows=b5.request_manifest_rows, output_root=r5,
        loader_blockers=b5.loader_blockers,
    )
    assert res5["blockers"] == ["source_runtime_attestation_contract_summary_binding_invalid"]

    r6 = make_canonical_stage1_5f_source_root(
        tmp_path / "r6",
        summary_overrides={"consumer_root_contract_sha256": "0" * 64},
    )
    b6 = load_stage1_5g_inputs(r6)
    res6 = build_stage1_5g_review_summary(
        summary=b6.summary, watermark=b6.watermark, states=b6.states,
        accepted_events=b6.accepted_events, snapshots=b6.snapshots,
        request_manifest_rows=b6.request_manifest_rows, output_root=r6,
        loader_blockers=b6.loader_blockers,
    )
    assert res6["blockers"] == ["source_runtime_attestation_contract_summary_binding_invalid"]

    r7 = make_canonical_stage1_5f_source_root(
        tmp_path / "r7",
        contract_overrides={"source_stage1_5d_output_root_id": "1" * 64},
    )
    b7 = load_stage1_5g_inputs(r7)
    res7 = build_stage1_5g_review_summary(
        summary=b7.summary, watermark=b7.watermark, states=b7.states,
        accepted_events=b7.accepted_events, snapshots=b7.snapshots,
        request_manifest_rows=b7.request_manifest_rows, output_root=r7,
        loader_blockers=b7.loader_blockers,
    )
    assert res7["blockers"] == ["source_runtime_attestation_contract_summary_binding_invalid"]


def test_runtime_gate_root_contract_missing_or_corrupt(tmp_path):
    r1 = make_canonical_stage1_5f_source_root(tmp_path / "r1", omit_contract=True)
    b1 = load_stage1_5g_inputs(r1)
    res1 = build_stage1_5g_review_summary(
        summary=b1.summary, watermark=b1.watermark, states=b1.states,
        accepted_events=b1.accepted_events, snapshots=b1.snapshots,
        request_manifest_rows=b1.request_manifest_rows, output_root=r1,
        loader_blockers=b1.loader_blockers,
    )
    assert res1["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "source_runtime_attestation_root_contract_missing_or_unreadable" in res1["blockers"]


def test_runtime_gate_historical_compromised_root_fails():
    root = Path("data/external_signal_shadow/local_evidence/20260902T105158Z_stage1_5f")
    bundle = load_stage1_5g_inputs(root)
    result = build_stage1_5g_review_summary(
        summary=bundle.summary,
        watermark=bundle.watermark,
        states=bundle.states,
        accepted_events=bundle.accepted_events,
        snapshots=bundle.snapshots,
        request_manifest_rows=bundle.request_manifest_rows,
        output_root=root,
        loader_blockers=bundle.loader_blockers,
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "source_runtime_attestation_compromised" in result["blockers"]
    assert "source_runtime_attestation_unverified" in result["blockers"]


def test_runtime_gate_zero_reducer_calls_on_authority_failure(tmp_path, monkeypatch):
    import src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review as g_module
    call_counts = {"integrity": 0, "coverage": 0, "raw_integrity": 0, "raw_quarantine": 0}

    def mock_integrity(*args, **kwargs):
        call_counts["integrity"] += 1
        raise AssertionError("integrity reducer should not be called")

    def mock_coverage(*args, **kwargs):
        call_counts["coverage"] += 1
        raise AssertionError("coverage reducer should not be called")

    def mock_raw_integrity(*args, **kwargs):
        call_counts["raw_integrity"] += 1
        raise AssertionError("raw integrity reducer should not be called")

    def mock_raw_quarantine(*args, **kwargs):
        call_counts["raw_quarantine"] += 1
        raise AssertionError("raw quarantine reducer should not be called")

    monkeypatch.setattr(g_module, "validate_evidence_integrity", mock_integrity)
    monkeypatch.setattr(g_module, "compute_coverage_metrics", mock_coverage)
    monkeypatch.setattr(g_module, "validate_raw_snapshot_integrity", mock_raw_integrity)
    monkeypatch.setattr(g_module, "compute_raw_snapshot_quarantine_metrics", mock_raw_quarantine)

    root = make_canonical_stage1_5f_source_root(
        tmp_path / "root",
        summary_overrides={"consumer_runtime_attestation_verified": False},
    )
    bundle = load_stage1_5g_inputs(root)
    result = build_stage1_5g_review_summary(
        summary=bundle.summary,
        watermark=bundle.watermark,
        states=bundle.states,
        accepted_events=bundle.accepted_events,
        snapshots=bundle.snapshots,
        request_manifest_rows=bundle.request_manifest_rows,
        output_root=root,
        loader_blockers=bundle.loader_blockers,
    )
    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert call_counts == {"integrity": 0, "coverage": 0, "raw_integrity": 0, "raw_quarantine": 0}
