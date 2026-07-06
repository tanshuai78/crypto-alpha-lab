import pytest
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    validate_evidence_integrity,
    EvidenceIntegrityResult,
)


def test_validator_accepts_announcement_and_launch_time_post_watermark():
    event = {
        "event_symbol_id": "es1",
        "symbol": "DATAIPUSDT",
        "source_article_id": "a1",
        "evidence_label": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
    }
    result = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert result.blockers == []
    assert result.evidence_label_counts["announcement_and_launch_time"] == 1
    assert result.formal_announcement_and_launch_count == 1
    assert result.formal_completed_event_symbol_ids == {"es1"}


def test_validator_blocks_missing_evidence_label():
    event = {
        "event_symbol_id": "es1",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
    }
    result = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert "missing_evidence_label" in result.blockers


def test_recovery_validation_only_cannot_count_as_formal_evidence():
    event = {
        "event_symbol_id": "es1",
        "symbol": "ETHUSD1",
        "evidence_label": "recovery_validation_only",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
    }
    result = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert result.formal_announcement_and_launch_count == 0
    assert result.evidence_label_counts["recovery_validation_only"] == 1


def test_validator_blocks_watermark_mismatch():
    event = {
        "event_symbol_id": "es1",
        "evidence_label": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 999,
        "watermark_version": 1,
    }
    result = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert "watermark_max_seen_detected_at_ms_mismatch" in result.blockers


def test_validator_blocks_missing_watermark():
    result = validate_evidence_integrity(
        accepted_events=[{"event_symbol_id": "es1", "evidence_label": "announcement_and_launch_time"}],
        watermark={},
        states=[],
        snapshots=[],
        summary={},
    )
    assert "missing_or_unreadable_watermark" in result.blockers


def test_validator_blocks_summary_state_count_mismatch():
    result = validate_evidence_integrity(
        accepted_events=[
            {
                "event_symbol_id": "es1",
                "evidence_label": "announcement_and_launch_time",
                "watermark_max_seen_detected_at_ms": 1000,
                "watermark_version": 1,
            }
        ],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "active"}],
        snapshots=[],
        summary={"completed_observation_count": 1},
    )
    assert "summary_state_count_mismatch" in result.blockers


def test_validator_blocks_completed_state_without_snapshots():
    result = validate_evidence_integrity(
        accepted_events=[
            {
                "event_symbol_id": "es1",
                "evidence_label": "announcement_and_launch_time",
                "watermark_max_seen_detected_at_ms": 1000,
                "watermark_version": 1,
            }
        ],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        snapshots=[],
        summary={"completed_observation_count": 1},
    )
    assert "completed_state_without_snapshots" in result.blockers


def test_validator_blocks_completed_state_snapshot_count_mismatch():
    result = validate_evidence_integrity(
        accepted_events=[
            {
                "event_symbol_id": "es1",
                "evidence_label": "announcement_and_launch_time",
                "watermark_max_seen_detected_at_ms": 1000,
                "watermark_version": 1,
            }
        ],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed", "depth_snapshot_count": 700}],
        snapshots=[{"event_symbol_id": "es1"} for _ in range(20)],
        summary={"completed_observation_count": 1},
    )
    assert "state_snapshot_count_mismatch" in result.blockers


def test_raw_snapshot_integrity_blocks_crossed_book():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_raw_snapshot_integrity,
    )
    snapshots = [
        {
            "event_symbol_id": "es1",
            "symbol": "A",
            "fetched_at_ms": 1,
            "best_bid": 101.0,
            "best_ask": 100.0,
            "mid_price": 100.5,
            "spread_bps": -1.0,
        }
    ]
    result = validate_raw_snapshot_integrity(snapshots)
    assert "invalid_book" in result.blockers


def test_raw_snapshot_integrity_blocks_non_monotonic_time_per_event_symbol():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_raw_snapshot_integrity,
    )
    snapshots = [
        {
            "event_symbol_id": "es1",
            "symbol": "A",
            "fetched_at_ms": 2,
            "best_bid": 100.0,
            "best_ask": 101.0,
            "mid_price": 100.5,
            "spread_bps": 100.0,
        },
        {
            "event_symbol_id": "es1",
            "symbol": "A",
            "fetched_at_ms": 1,
            "best_bid": 100.0,
            "best_ask": 101.0,
            "mid_price": 100.5,
            "spread_bps": 100.0,
        },
    ]
    result = validate_raw_snapshot_integrity(snapshots)
    assert "non_monotonic_timestamp" in result.blockers


def test_raw_snapshot_integrity_blocks_symbol_event_symbol_mapping_conflict():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_raw_snapshot_integrity,
    )
    snapshots = [
        {
            "event_symbol_id": "es1",
            "symbol": "A",
            "fetched_at_ms": 1,
            "best_bid": 100.0,
            "best_ask": 101.0,
            "mid_price": 100.5,
            "spread_bps": 100.0,
        },
        {
            "event_symbol_id": "es1",
            "symbol": "B",
            "fetched_at_ms": 2,
            "best_bid": 100.0,
            "best_ask": 101.0,
            "mid_price": 100.5,
            "spread_bps": 100.0,
        },
    ]
    result = validate_raw_snapshot_integrity(snapshots)
    assert "symbol_event_symbol_id_mapping_conflict" in result.blockers


def test_raw_snapshot_integrity_blocks_jsonl_parse_error_from_loader():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_raw_snapshot_integrity,
    )
    result = validate_raw_snapshot_integrity(
        snapshots=[],
        parse_error_count=1,
        total_jsonl_line_count=100,
    )
    assert "jsonl_parse_error" in result.blockers
    assert result.jsonl_parse_error_ratio == 0.01
