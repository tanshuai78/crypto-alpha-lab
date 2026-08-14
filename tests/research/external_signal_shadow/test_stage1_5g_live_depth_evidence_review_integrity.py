import json

from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    load_stage1_5g_inputs,
    validate_evidence_integrity,
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


def test_state_loader_uses_physical_last_row(tmp_path):
    rows = [
        {"event_symbol_id": "es1", "status": "pending_launch_time_in_future", "updated_at_ms": 3_000},
        {"event_symbol_id": "es1", "status": "active", "updated_at_ms": 2_000},
        # Durable append order, not producer timestamps, defines the latest state.
        {"event_symbol_id": "es1", "status": "completed", "depth_snapshot_count": 3, "updated_at_ms": 1_000},
    ]
    (tmp_path / "observer_state.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    bundle = load_stage1_5g_inputs(tmp_path)

    assert len(bundle.states) == 1
    assert bundle.states[0]["event_symbol_id"] == "es1"
    assert bundle.states[0]["status"] == "completed"


def test_validator_accepts_live_depth_evidence_basis_alias_from_stage1_5f():
    event = {
        "event_symbol_id": "es1",
        "symbol": "SKHYUSDT",
        "source_article_id": "a1",
        "live_depth_evidence_basis": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
    }
    result = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed", "depth_snapshot_count": 1}],
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert "missing_evidence_label" not in result.blockers
    assert result.evidence_label_counts["announcement_and_launch_time"] == 1
    assert result.formal_announcement_and_launch_count == 1
    assert result.formal_completed_event_symbol_ids == {"es1"}


def test_validator_accepts_event_watermark_before_current_watermark():
    event = {
        "event_symbol_id": "es1",
        "symbol": "SKHYUSDT",
        "source_article_id": "a1",
        "live_depth_evidence_basis": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
    }
    result = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 2000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed", "depth_snapshot_count": 1}],
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert "watermark_max_seen_detected_at_ms_mismatch" not in result.blockers
    assert result.formal_announcement_and_launch_count == 1


def test_validator_accepts_stage1_5f_accepted_row_without_event_watermark_fields():
    event = {
        "event_symbol_id": "es1",
        "symbol": "KOUSDT",
        "source_article_id": "a1",
        "live_depth_evidence_basis": "launch_time_only",
    }
    result = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 2000, "watermark_version": 1},
        states=[{"event_symbol_id": "es1", "status": "completed", "depth_snapshot_count": 1}],
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert "watermark_version_mismatch" not in result.blockers
    assert "watermark_max_seen_detected_at_ms_mismatch" not in result.blockers


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
        "watermark_max_seen_detected_at_ms": 1001,
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


def test_validator_compares_summary_completed_count_against_latest_state_only():
    states = [
        {"event_symbol_id": "es1", "status": "active", "updated_at_ms": 1000},
        {"event_symbol_id": "es1", "status": "completed", "depth_snapshot_count": 1, "updated_at_ms": 2000},
        {"event_symbol_id": "es1", "status": "completed", "depth_snapshot_count": 1, "updated_at_ms": 3000},
    ]
    result = validate_evidence_integrity(
        accepted_events=[
            {
                "event_symbol_id": "es1",
                "evidence_label": "launch_time_only",
                "watermark_max_seen_detected_at_ms": 1000,
                "watermark_version": 1,
            }
        ],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=states,
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert "summary_state_count_mismatch" not in result.blockers


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


def test_raw_snapshot_integrity_accepts_stage1_5f_snapshot_without_mid_price():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_raw_snapshot_integrity,
    )
    snapshots = [
        {
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "fetched_at_ms": 1,
            "best_bid": 100.0,
            "best_ask": 101.0,
            "spread_bps": 100.0,
            "top_bid_depth_usdt": 1000.0,
            "top_ask_depth_usdt": 1000.0,
        }
    ]
    result = validate_raw_snapshot_integrity(snapshots)
    assert "invalid_book" not in result.blockers
    assert result.invalid_book_count == 0


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


def test_stage1_5g_uses_latest_state_for_anchor_contamination():
    from research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_evidence_integrity,
    )
    event = {
        "event_symbol_id": "es1",
        "symbol": "ABCUSDT",
        "source_article_id": "a1",
        "evidence_label": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
        "admission_anchor_contract_hash": "hash_adm_1",
    }
    # Multiple state rows: active first, then contaminated state
    states = [
        {"event_symbol_id": "es1", "status": "active", "admission_anchor_contract_hash": "hash_adm_1", "updated_at_ms": 1000},
        {"event_symbol_id": "es1", "status": "active_anchor_revision_contaminated", "observation_anchor_revision_contaminated": True, "admission_anchor_contract_hash": "hash_adm_1", "updated_at_ms": 2000},
    ]
    res = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=states,
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert "anchor_revision_contaminated" in res.blockers


def test_anchor_contract_hash_mismatch_is_invalid():
    from research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_evidence_integrity,
    )
    event = {
        "event_symbol_id": "es1",
        "symbol": "ABCUSDT",
        "source_article_id": "a1",
        "evidence_label": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
        "admission_anchor_contract_hash": "hash_accepted",
    }
    states = [
        {"event_symbol_id": "es1", "status": "completed", "admission_anchor_contract_hash": "hash_different", "updated_at_ms": 1000},
    ]
    res = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=states,
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert "anchor_contract_lineage_mismatch" in res.blockers


def test_exchangeinfo_fallback_blocks_clean_depth_evidence_pass():
    from research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_evidence_integrity,
    )
    event = {
        "event_symbol_id": "es1",
        "symbol": "ABCUSDT",
        "source_article_id": "a1",
        "evidence_label": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
        "anchor_evidence_level": "exchangeinfo_fallback",
        "effective_observation_anchor_source": "exchangeinfo_onboard_date",
    }
    states = [
        {"event_symbol_id": "es1", "status": "completed", "updated_at_ms": 1000},
    ]
    res = validate_evidence_integrity(
        [event],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=states,
        snapshots=[{"event_symbol_id": "es1"}],
        summary={"completed_observation_count": 1},
    )
    assert "exchangeinfo_fallback_anchor" in res.blockers


def test_validator_requires_formal_v2_lineage_fields():
    from research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_evidence_integrity,
    )

    base_event = {
        "event_symbol_id": "es_v2",
        "symbol": "KOUSDT",
        "source_article_id": "307687ad279e42e6909ee1be8c472b50",
        "evidence_label": "announcement_and_launch_time",
        "watermark_max_seen_detected_at_ms": 1000,
        "watermark_version": 1,
        "formal_event_contract_version": 2,
        "source_contract_status": "formal_v2_valid",
        "launch_anchor_evidence_level": "official_schedule",
        "effective_observation_anchor_source": "official_schedule_anchor",
        "anchor_precedence_policy": "official_schedule_priority_v1",
        "source_anchor_contract_hash": "source-hash",
        "admission_anchor_contract_hash": "admission-hash",
    }
    base_state = {
        "event_symbol_id": "es_v2",
        "status": "completed",
        "depth_snapshot_count": 1,
        "formal_event_contract_version": 2,
        "source_contract_status": "formal_v2_valid",
        "launch_anchor_evidence_level": "official_schedule",
        "effective_observation_anchor_source": "official_schedule_anchor",
        "source_article_id": "307687ad279e42e6909ee1be8c472b50",
        "anchor_contract_version": 2,
        "anchor_precedence_policy": "official_schedule_priority_v1",
        "source_anchor_contract_hash": "source-hash",
        "admission_anchor_contract_hash": "admission-hash",
        "latest_anchor_contract_hash": "latest-hash",
        "latest_anchor_evidence_level": "official_schedule",
        "latest_max_evidence_class": "clean_or_recovery",
        "observation_anchor_revision_contaminated": False,
    }

    # Clean v2 passes
    res_clean = validate_evidence_integrity(
        [dict(base_event)],
        watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
        states=[dict(base_state)],
        snapshots=[{"event_symbol_id": "es_v2"}],
        summary={"completed_observation_count": 1},
    )
    assert "formal_v2_lineage_incomplete_or_mismatch" not in res_clean.blockers
    assert res_clean.formal_announcement_and_launch_count == 1

    # Every v2 lineage component is required and must agree across rows.
    for field in (
        "source_article_id",
        "formal_event_contract_version",
        "source_contract_status",
        "launch_anchor_evidence_level",
        "effective_observation_anchor_source",
        "anchor_precedence_policy",
        "source_anchor_contract_hash",
        "admission_anchor_contract_hash",
    ):
        bad_event = dict(base_event)
        bad_event[field] = "" if isinstance(base_event[field], str) else None
        res_bad = validate_evidence_integrity(
            [bad_event],
            watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
            states=[dict(base_state)],
            snapshots=[{"event_symbol_id": "es_v2"}],
            summary={"completed_observation_count": 1},
        )
        assert "formal_v2_lineage_incomplete_or_mismatch" in res_bad.blockers
        assert res_bad.formal_announcement_and_launch_count == 0

    for field, value in (
        ("anchor_contract_version", None),
        ("anchor_precedence_policy", "wrong_policy"),
        ("source_anchor_contract_hash", "wrong-source-hash"),
        ("admission_anchor_contract_hash", "wrong-admission-hash"),
        ("latest_anchor_evidence_level", "exchangeinfo_fallback"),
        ("latest_max_evidence_class", "degraded"),
        ("observation_anchor_revision_contaminated", True),
    ):
        bad_state = dict(base_state)
        bad_state[field] = value
        res_bad = validate_evidence_integrity(
            [dict(base_event)],
            watermark={"max_seen_detected_at_ms": 1000, "watermark_version": 1},
            states=[bad_state],
            snapshots=[{"event_symbol_id": "es_v2"}],
            summary={"completed_observation_count": 1},
        )
        assert "formal_v2_lineage_incomplete_or_mismatch" in res_bad.blockers
        assert res_bad.formal_announcement_and_launch_count == 0


def test_formal_v2_lineage_requires_completed_hash_to_match_latest():
    from research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        _validate_formal_v2_lineage,
    )

    event = {
        "formal_event_contract_version": 2,
        "source_contract_status": "formal_v2_valid",
        "launch_anchor_evidence_level": "official_schedule",
        "effective_observation_anchor_source": "official_schedule_anchor",
        "source_article_id": "article",
        "anchor_precedence_policy": "official_schedule_priority_v1",
        "source_anchor_contract_hash": "source-hash",
        "admission_anchor_contract_hash": "admission-hash",
    }
    latest = {
        "anchor_contract_version": 2,
        "anchor_precedence_policy": "official_schedule_priority_v1",
        "source_anchor_contract_hash": "source-hash",
        "admission_anchor_contract_hash": "admission-hash",
        "latest_anchor_evidence_level": "official_schedule",
        "latest_max_evidence_class": "clean_or_recovery",
        "latest_anchor_contract_hash": "latest-hash",
        "observation_anchor_revision_contaminated": False,
    }
    completed = dict(latest, latest_anchor_contract_hash="completed-hash")

    assert _validate_formal_v2_lineage(event, latest, completed) == (
        False,
        "formal_v2_lineage_incomplete_or_mismatch",
    )
