import hashlib
import json
import shutil

from research.external_signal_shadow.stage1_5d_schedule_revision_producer import (
    classify_revision_intent,
    is_schedule_revision_listing_candidate,
    link_schedule_revision_candidate,
    load_valid_formal_launch_identity_index,
)


def test_classify_revision_intent_identifies_plain_and_maintenance_as_not_revision():
    plain_text = "Binance Will Launch USD-M AIAUSDT Perpetual Contract at 2026-08-06 10:00 (UTC)."
    res_plain = classify_revision_intent(plain_text)
    assert res_plain["revision_intent"] == "not_revision"

    maint_text = "System maintenance on Binance Futures API endpoints scheduled for 2026-08-06 00:00 (UTC)."
    res_maint = classify_revision_intent(maint_text)
    assert res_maint["revision_intent"] == "not_revision"


def test_classify_revision_intent_identifies_rescheduled_and_ambiguous():
    resched_text = "Postponement of AIAUSDT USD-M Perpetual Contract Launch. The launch of AIAUSDT Perpetual Contract will be rescheduled to 2026-08-07 10:00 (UTC)."
    res_resched = classify_revision_intent(resched_text)
    assert res_resched["revision_intent"] == "rescheduled_with_new_anchor"

    ambig_text = "Postponement or cancellation of AIAUSDT contract launch. Launch is postponed and cancelled simultaneously."
    res_ambig = classify_revision_intent(ambig_text)
    assert res_ambig["revision_intent"] in ("ambiguous_revision_intent", "cancelled", "postponed_without_anchor")


def test_revision_listing_classifier_excludes_plain_launch_and_maintenance():
    assert is_schedule_revision_listing_candidate(
        "Postponement of AIAUSDT USD-M Perpetual Contract Launch"
    ) is True
    assert is_schedule_revision_listing_candidate(
        "Binance Futures Will Launch AIAUSDT USD-M Perpetual Contract"
    ) is False
    assert is_schedule_revision_listing_candidate("Binance Futures API System Maintenance") is False


def test_link_schedule_revision_candidate_out_of_scope_l4_symbol_only():
    candidate = {
        "source_article_id": "rev_l4",
        "symbol": "AIAUSDT",
        "link_level_candidate": "L4_symbol_only",
        "revision_intent": "rescheduled_with_new_anchor",
    }
    index_rows = [
        {
            "supersedes_source_article_id": "orig_1",
            "symbol": "AIAUSDT",
            "stable_schedule_identity": "binance|futures_contract_launch|orig_1|AIAUSDT",
            "original_source_published_at_ms": 1000,
            "formal_row_durable_at_ms": 1050,
        }
    ]
    res = link_schedule_revision_candidate(candidate, index_rows, available_at_ms=1500, lookback_days=14)
    assert res["link_status"] == "out_of_scope"


def test_link_schedule_revision_candidate_l1_l2_l3_success_and_ambiguous():
    # L1 exact article match
    cand_l1 = {
        "source_article_id": "rev_l1",
        "supersedes_source_article_id": "orig_1",
        "symbol": "AIAUSDT",
        "link_level_candidate": "L1_exact_article_id",
        "revision_intent": "rescheduled_with_new_anchor",
    }
    index_rows = [
        {
            "supersedes_source_article_id": "orig_1",
            "symbol": "AIAUSDT",
            "stable_schedule_identity": "binance|futures_contract_launch|orig_1|AIAUSDT",
            "original_source_published_at_ms": 1000,
            "formal_row_durable_at_ms": 1050,
        }
    ]
    res_l1 = link_schedule_revision_candidate(cand_l1, index_rows, available_at_ms=1500, lookback_days=14)
    assert res_l1["link_status"] == "linked"
    assert res_l1["target_index_row"]["supersedes_source_article_id"] == "orig_1"

    # Ambiguous duplicate match
    index_duplicate = [
        {
            "supersedes_source_article_id": "orig_1",
            "symbol": "AIAUSDT",
            "stable_schedule_identity": "binance|futures_contract_launch|orig_1|AIAUSDT",
            "original_source_published_at_ms": 1000,
            "formal_row_durable_at_ms": 1050,
        },
        {
            "supersedes_source_article_id": "orig_1",
            "symbol": "AIAUSDT",
            "stable_schedule_identity": "binance|futures_contract_launch|orig_1_dup|AIAUSDT",
            "original_source_published_at_ms": 1000,
            "formal_row_durable_at_ms": 1050,
        },
    ]
    res_dup = link_schedule_revision_candidate(cand_l1, index_duplicate, available_at_ms=1500, lookback_days=14)
    assert res_dup["link_status"] in ("ambiguous", "linked")


def test_link_schedule_revision_candidate_requires_prior_durable_launch_row():
    candidate = {
        "source_article_id": "rev_l1",
        "supersedes_source_article_id": "orig_1",
        "symbol": "AIAUSDT",
        "link_level_candidate": "L1_exact_article_id",
    }
    index_rows = [{
        "supersedes_source_article_id": "orig_1",
        "symbol": "AIAUSDT",
        "original_source_published_at_ms": 1_000,
        "formal_row_durable_at_ms": 1_600,
    }]

    result = link_schedule_revision_candidate(candidate, index_rows, available_at_ms=1_500)
    assert result["link_status"] == "orphaned"


def test_index_loader_accepts_only_hashed_explicit_snapshot(tmp_path):
    rows = [{
        "supersedes_source_article_id": "a" * 32,
        "symbol": "AIAUSDT",
        "original_source_published_at_ms": 1_000,
        "formal_row_durable_at_ms": 1_100,
        "source_root_id": "approved-root",
        "source_root_commit_sha": "abc123",
    }]
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({
        "schema_version": 1,
        "source_root_id": "approved-root",
        "commit_sha": "abc123",
        "rows": rows,
        "content_sha256": hashlib.sha256(canonical).hexdigest(),
    }))

    loaded, blockers = load_valid_formal_launch_identity_index(
        tmp_path / "missing-current.jsonl", as_of_ms=1_500, snapshot_path=snapshot
    )
    assert blockers == []
    assert loaded == rows

    rows[0]["source_root_commit_sha"] = "unexpected"
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    snapshot.write_text(json.dumps({
        "schema_version": 1,
        "source_root_id": "approved-root",
        "commit_sha": "abc123",
        "rows": rows,
        "content_sha256": hashlib.sha256(canonical).hexdigest(),
    }))
    _, blockers = load_valid_formal_launch_identity_index(
        tmp_path / "missing-current.jsonl", as_of_ms=1_500, snapshot_path=snapshot
    )
    assert blockers == ["snapshot_invalid:snapshot_row_commit_unapproved"]


def test_index_collision_blocks_revision_linking(tmp_path):
    index_path = tmp_path / "formal_launch_identity_index.jsonl"
    rows = [
        {
            "supersedes_source_article_id": "a" * 32,
            "symbol": "AIAUSDT",
            "stable_schedule_identity": "binance|futures_contract_launch|a|AIAUSDT",
            "source_anchor_contract_hash": "hash-a",
            "official_schedule_anchor_ms": 1_000,
            "event_id": "event-a",
        },
        {
            "supersedes_source_article_id": "a" * 32,
            "symbol": "AIAUSDT",
            "stable_schedule_identity": "binance|futures_contract_launch|a|AIAUSDT",
            "source_anchor_contract_hash": "hash-b",
            "official_schedule_anchor_ms": 1_000,
            "event_id": "event-a",
        },
    ]
    index_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    _, blockers = load_valid_formal_launch_identity_index(index_path, as_of_ms=2_000)

    assert blockers == ["index_collision"]


def test_restart_rebuilds_missing_current_root_identity_index(tmp_path):
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_event_anchor_contract_row,
        build_symbol_anchor_contract,
    )
    from research.external_signal_shadow.stage1_5d_schedule_revision_producer import (
        rebuild_missing_formal_launch_identity_index,
    )

    symbol = "AIAUSDT"
    contract = build_symbol_anchor_contract(
        symbol=symbol,
        official_schedule_anchor_ms=2_000,
        exchangeinfo_onboard_date_ms=2_000,
        anchor_contract_decision_at_ms=1_000,
        official_schedule_revision_id="original_schedule",
        official_schedule_available_at_ms=900,
        mapping_confidence="exact_single_symbol",
        provenance={
            "payload_sha256": "payload-hash",
            "parser_version": "test",
            "raw_time_text": "2026-08-08 10:00 (UTC)",
            "timezone_text": "UTC",
            "node_path": "body[0]",
            "logical_block_id": "launch",
            "schedule_text_context": "Launch Time",
            "mapping_method": "test",
        },
    )
    launch_row = build_formal_event_anchor_contract_row(
        base_event={
            "event_type": "futures_contract_launch",
            "source_article_id": "a" * 32,
            "source_published_at_ms": 800,
            "symbols": [symbol],
        },
        symbol_contracts={symbol: contract},
    )
    root = tmp_path / "data" / "external_signal_shadow" / "stage1_5d" / "test_output"
    events_dir = root / "events"
    events_dir.mkdir(parents=True)
    (events_dir / "2026-08-07.jsonl").write_text(json.dumps(launch_row) + "\n")
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    storage_guard = StorageGuard(
        output_root=root,
        stage="1.5D",
        disk_usage_func=lambda path: shutil._ntuple_diskusage(
            100 * 1024**3, 50 * 1024**3, 50 * 1024**3
        ),
    )

    rebuilt, diagnostics = rebuild_missing_formal_launch_identity_index(
        events_dir=events_dir,
        index_path=root / "formal_launch_identity_index.jsonl",
        source_root_id="current-root",
        commit_sha="abc123",
        storage_guard=storage_guard,
    )

    assert diagnostics == []
    assert rebuilt == 1
    index_rows = [json.loads(line) for line in (root / "formal_launch_identity_index.jsonl").read_text().splitlines()]
    assert index_rows[0]["supersedes_source_article_id"] == "a" * 32
    assert index_rows[0]["formal_row_durable_at_ms"] >= 800


def test_restart_rebuilds_emitted_revision_semantic_ids_from_event_stream(tmp_path):
    from research.external_signal_shadow.stage1_5d_schedule_revision_producer import (
        load_emitted_revision_semantic_ids,
    )

    events_dir = tmp_path / "events"
    events_dir.mkdir()
    rows = [
        {"event_type": "futures_contract_launch", "event_id": "launch"},
        {
            "event_type": "futures_launch_schedule_revision",
            "formal_schedule_revision_contract_version": 2,
            "revision_semantic_id": "revision-semantic-id",
        },
    ]
    (events_dir / "2026-08-07.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    assert load_emitted_revision_semantic_ids(events_dir) == {"revision-semantic-id"}


def test_emit_schedule_revision_batch_all_symbols_failure():
    from research.external_signal_shadow.stage1_5d_schedule_revision_producer import (
        emit_schedule_revision_batch,
    )

    batch_candidate = {
        "source_article_id": "rev_batch_1",
        "revision_intent": "rescheduled_with_new_anchor",
        "symbols": ["FOOUSDT", "BARUSDT"],
        "symbol_candidates": {
            "FOOUSDT": {"supersedes_source_article_id": "orig_foo", "revised_anchor_ms": 2000, "link_level_candidate": "L1_exact_article_id"},
            "BARUSDT": {"supersedes_source_article_id": "", "revised_anchor_ms": 2000, "link_level_candidate": "L4_symbol_only"}, # Invalid/unlinked!
        },
    }
    index_rows = [
        {"supersedes_source_article_id": "orig_foo", "symbol": "FOOUSDT", "stable_schedule_identity": "binance|futures_contract_launch|orig_foo|FOOUSDT", "original_source_published_at_ms": 1000, "formal_row_durable_at_ms": 1050},
    ]

    written_rows, batch_diag = emit_schedule_revision_batch(batch_candidate, index_rows, available_at_ms=1500, lookback_days=14)
    assert written_rows == []
    assert batch_diag["batch_status"] == "terminal_diagnostic"


def test_late_conflict_transport():
    from research.external_signal_shadow.stage1_5d_schedule_revision_producer import (
        emit_schedule_revision_batch,
    )

    batch_candidate = {
        "source_article_id": "rev_conflict_b",
        "revision_intent": "rescheduled_with_new_anchor",
        "symbols": ["FOOUSDT"],
        "symbol_candidates": {
            "FOOUSDT": {"supersedes_source_article_id": "orig_foo", "revised_anchor_ms": 3000, "link_level_candidate": "L1_exact_article_id"},
        },
        "is_late_conflict": True,
        "payload_sha256": "payload-conflict-b",
    }
    index_rows = [
        {"supersedes_source_article_id": "orig_foo", "symbol": "FOOUSDT", "stable_schedule_identity": "binance|futures_contract_launch|orig_foo|FOOUSDT", "original_source_published_at_ms": 1000, "formal_row_durable_at_ms": 1050},
    ]

    written_rows, batch_diag = emit_schedule_revision_batch(batch_candidate, index_rows, available_at_ms=1500, lookback_days=14)
    assert len(written_rows) == 1
    assert written_rows[0]["revision_intent"] == "rescheduled_with_new_anchor"
    assert batch_diag["is_late_conflict"] is True
