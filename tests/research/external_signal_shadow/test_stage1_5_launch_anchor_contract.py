import hashlib
import json
from pathlib import Path

from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
    build_formal_event_anchor_contract_row,
    build_formal_schedule_revision_row,
    build_symbol_anchor_contract,
    compute_admission_anchor_contract_hash,
    compute_latest_anchor_contract_hash,
    select_latest_applicable_official_schedule,
    validate_launch_anchor_contract,
    validate_schedule_revision_contract,
)


def test_gigadev_anchor_contract_v2_fixture_metadata_loads_and_hashes_match():
    root = Path("tests/fixtures/external_signal_shadow/stage1_5d/gigadev_anchor_contract_v2")
    meta = json.loads((root / "gigadev_fixture_metadata.json").read_text())
    payload_bytes = (root / "gigadev_bapi_article_detail_real_frozen_fixture.json").read_bytes()

    assert meta["article_id"] == "e8bfd0c5adaf4d8a880bb1b7327107ef"
    assert meta["symbol"] == "GIGADEVUSDT"
    assert meta["official_schedule_anchor_ms"] == 1785735000000
    assert meta["exchangeinfo_onboardDate_ms"] == 1785722400000
    assert meta["expected_contract_version"] == 2
    assert meta["expected_primary_anchor_source"] == "official_schedule_anchor"
    assert meta["expected_clean_evidence_for_historical_incident"] is False
    assert hashlib.sha256(payload_bytes).hexdigest() == meta["payload_sha256"]
    assert meta["payload_sha256"] == meta["manifest_payload_sha256"]
    assert meta["fixture_sha256"]
    assert meta["request_url_sha256"]
    assert meta["payload_trusted"] is True
    assert meta["http_status"] == 200
    assert meta["parser_version"] == "stage1_5d_symbol_extraction_v3"


def test_anchor_contract_single_source_of_truth_imports():
    from research.external_signal_shadow import stage1_5_launch_anchor_contract as anchor_contract
    from research.external_signal_shadow import stage1_5_launch_event_contract as legacy_contract

    assert legacy_contract.validate_launch_anchor_contract is anchor_contract.validate_launch_anchor_contract
    assert legacy_contract.build_symbol_anchor_contract is anchor_contract.build_symbol_anchor_contract


def test_new_anchor_contract_tests_do_not_import_via_src_namespace():
    bad_prefix = "from " + "src.research.external_signal_shadow"
    paths = [Path("tests/research/external_signal_shadow/test_stage1_5_launch_anchor_contract.py")]
    for path in paths:
        assert bad_prefix not in path.read_text()


def test_symbol_builder_returns_symbol_contract_not_event_row():
    contract = build_symbol_anchor_contract(
        symbol="GIGADEVUSDT",
        official_schedule_anchor_ms=1785735000000,
        exchangeinfo_onboard_date_ms=1785722400000,
        anchor_contract_decision_at_ms=1785726000000,
        official_schedule_revision_id="gigadev_rev_1",
        official_schedule_available_at_ms=1785724209135,
        mapping_confidence="exact_single_symbol",
        provenance={
            "payload_sha256": "sha",
            "parser_version": "test",
            "raw_time_text": "2026-08-03 05:30 (UTC)",
            "timezone_text": "UTC",
            "node_path": "body[0]",
            "logical_block_id": "block-1",
            "schedule_text_context": "Launch Time",
            "mapping_method": "single_symbol_article_unique_futures_launch_time",
        },
    )

    assert contract["symbol"] == "GIGADEVUSDT"
    assert "formal_event_contract_version" not in contract
    assert contract["effective_observation_anchor_ms"] == 1785735000000


def test_event_row_builder_wraps_symbol_contracts_and_validator_accepts_row():
    symbol_contract = build_symbol_anchor_contract(
        symbol="GIGADEVUSDT",
        official_schedule_anchor_ms=1785735000000,
        exchangeinfo_onboard_date_ms=1785722400000,
        anchor_contract_decision_at_ms=1785726000000,
        official_schedule_revision_id="gigadev_rev_1",
        official_schedule_available_at_ms=1785724209135,
        mapping_confidence="exact_single_symbol",
        provenance={
            "payload_sha256": "sha",
            "parser_version": "test",
            "raw_time_text": "2026-08-03 05:30 (UTC)",
            "timezone_text": "UTC",
            "node_path": "body[0]",
            "logical_block_id": "block-1",
            "schedule_text_context": "Launch Time",
            "mapping_method": "single_symbol_article_unique_futures_launch_time",
        },
    )
    row = build_formal_event_anchor_contract_row(
        base_event={"event_type": "futures_contract_launch", "source_article_id": "e8bfd0c5adaf4d8a880bb1b7327107ef", "symbols": ["GIGADEVUSDT"]},
        symbol_contracts={"GIGADEVUSDT": symbol_contract},
    )

    res = validate_launch_anchor_contract(row, "GIGADEVUSDT", compatibility_mode=False)
    assert row["formal_event_contract_version"] == 2
    assert res["valid"] is True
    assert res["effective_observation_anchor_ms"] == 1785735000000


def test_latest_cancelled_revision_blocks_old_schedule():
    revisions = [
        {"revision_id": "r1", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
        {"revision_id": "r2", "symbol": "ABCUSDT", "available_at_ms": 4000, "anchor_ms": None, "status": "cancelled", "supersedes_revision_id": "r1"},
    ]
    selected = select_latest_applicable_official_schedule("ABCUSDT", revisions, as_of_ms=4500)
    assert selected["status"] == "cancelled"
    assert selected["effective_official_anchor_ms"] is None
    assert selected["consumable"] is False


def test_latest_postponed_revision_without_new_anchor_is_pending():
    revisions = [
        {"revision_id": "r1", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
        {"revision_id": "r2", "symbol": "ABCUSDT", "available_at_ms": 4000, "anchor_ms": None, "status": "postponed", "supersedes_revision_id": "r1"},
    ]
    selected = select_latest_applicable_official_schedule("ABCUSDT", revisions, as_of_ms=4500)
    assert selected["status"] == "postponed_without_anchor"
    assert selected["pending_reason"] == "pending_schedule_revision"
    assert selected["consumable"] is False


def test_equal_available_at_conflicting_revisions_fail_closed():
    revisions = [
        {"revision_id": "r1", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
        {"revision_id": "r2", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 9000, "status": "scheduled"},
    ]
    selected = select_latest_applicable_official_schedule("ABCUSDT", revisions, as_of_ms=1000)
    assert selected["status"] == "official_schedule_conflict"
    assert selected["consumable"] is False


def test_revision_id_is_not_used_to_resolve_semantic_conflict():
    revisions = [
        {"revision_id": "z", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
        {"revision_id": "a", "symbol": "ABCUSDT", "available_at_ms": 1000, "anchor_ms": 9000, "status": "scheduled"},
    ]
    assert select_latest_applicable_official_schedule("ABCUSDT", revisions, as_of_ms=1000)["status"] == "official_schedule_conflict"


def test_official_anchor_requires_full_mapping_provenance():
    # Missing node_path in provenance -> validation fails
    symbol_contract = build_symbol_anchor_contract(
        symbol="ABCUSDT",
        official_schedule_anchor_ms=1785735000000,
        exchangeinfo_onboard_date_ms=None,
        anchor_contract_decision_at_ms=1785726000000,
        official_schedule_revision_id="rev_1",
        official_schedule_available_at_ms=1785724209135,
        mapping_confidence="exact_single_symbol",
        provenance={"raw_time_text": "2026-08-03 05:30 (UTC)"},  # Missing node_path etc.
    )
    row = build_formal_event_anchor_contract_row(
        base_event={"event_type": "futures_contract_launch", "source_article_id": "abc-123", "symbols": ["ABCUSDT"]},
        symbol_contracts={"ABCUSDT": symbol_contract},
    )
    res = validate_launch_anchor_contract(row, "ABCUSDT", compatibility_mode=False)
    assert res["valid"] is False
    assert "official_schedule_provenance_missing" in res["blockers"]


def test_source_admission_latest_hashes_have_distinct_contracts():
    symbol_contract = build_symbol_anchor_contract(
        symbol="XYZUSDT",
        official_schedule_anchor_ms=1000000,
        exchangeinfo_onboard_date_ms=None,
        anchor_contract_decision_at_ms=500000,
        official_schedule_revision_id="r1",
        official_schedule_available_at_ms=400000,
        mapping_confidence="exact_single_symbol",
        provenance={"payload_sha256": "p1"},
    )
    src_hash = symbol_contract["source_anchor_contract_hash"]
    adm_hash = compute_admission_anchor_contract_hash(
        source_anchor_contract_hash=src_hash,
        admission_snapshot={"admission_at_ms": 600000, "observation_anchor_ms": 1000000, "evidence_start_class": "clean_start", "admission_max_evidence_class": "clean_or_recovery"},
    )
    latest_hash = compute_latest_anchor_contract_hash(
        previous_latest_anchor_contract_hash=adm_hash,
        revision_application_id="app-1",
        latest_contract=symbol_contract,
    )

    assert src_hash != adm_hash
    assert adm_hash != latest_hash
    assert src_hash != latest_hash


def test_hash_changes_when_revision_status_changes():
    rev1 = [
        {"revision_id": "r1", "symbol": "XYZUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
    ]
    rev2 = [
        {"revision_id": "r1", "symbol": "XYZUSDT", "available_at_ms": 1000, "anchor_ms": 5000, "status": "scheduled"},
        {"revision_id": "r2", "symbol": "XYZUSDT", "available_at_ms": 2000, "anchor_ms": 9000, "status": "rescheduled"},
    ]

    sel1 = select_latest_applicable_official_schedule("XYZUSDT", rev1, as_of_ms=1500)
    sel2 = select_latest_applicable_official_schedule("XYZUSDT", rev2, as_of_ms=2500)

    c1 = build_symbol_anchor_contract(
        symbol="XYZUSDT",
        official_schedule_anchor_ms=sel1["effective_official_anchor_ms"],
        exchangeinfo_onboard_date_ms=None,
        anchor_contract_decision_at_ms=1500,
        official_schedule_revision_id=sel1["revision_id"],
        official_schedule_available_at_ms=sel1["available_at_ms"],
        mapping_confidence="exact_single_symbol",
        provenance={"payload_sha256": "p1"},
    )
    c2 = build_symbol_anchor_contract(
        symbol="XYZUSDT",
        official_schedule_anchor_ms=sel2["effective_official_anchor_ms"],
        exchangeinfo_onboard_date_ms=None,
        anchor_contract_decision_at_ms=2500,
        official_schedule_revision_id=sel2["revision_id"],
        official_schedule_available_at_ms=sel2["available_at_ms"],
        mapping_confidence="exact_single_symbol",
        provenance={"payload_sha256": "p2"},
    )

    assert c1["source_anchor_contract_hash"] != c2["source_anchor_contract_hash"]


def test_latest_hash_links_previous_hash_and_revision():
    h_prev = "previous_hash_123"
    h_rev = compute_latest_anchor_contract_hash(
        previous_latest_anchor_contract_hash=h_prev,
        revision_application_id="rev_app_456",
        latest_contract={"symbol": "ABCUSDT", "effective_observation_anchor_ms": 9999},
    )
    h_rev2 = compute_latest_anchor_contract_hash(
        previous_latest_anchor_contract_hash="different_prev_hash",
        revision_application_id="rev_app_456",
        latest_contract={"symbol": "ABCUSDT", "effective_observation_anchor_ms": 9999},
    )
    assert h_rev != h_rev2


def test_formal_schedule_revision_contract_validates_required_transport_shape():
    row = build_formal_schedule_revision_row(
        source_article_id="revision-article",
        supersedes_source_article_id="orig-article",
        symbol="ABCUSDT",
        revised_anchor_ms=2_000,
        superseded_anchor_ms=1_000,
        revision_id="rev-1",
        revision_semantic_id="rev-1",
        revision_application_id="rev-1",
        revision_payload_version_id="payload-v1",
        revision_observation_id="obs-1",
        revision_payload_hash="payload-hash",
        revision_available_at_ms=1_500,
        revision_reason="rescheduled",
        provenance={"payload_sha256": "payload-hash", "parser_version": "test"},
    )

    res = validate_schedule_revision_contract(row)
    assert row["event_type"] == "futures_contract_launch_schedule_revision"
    assert row["formal_schedule_revision_contract_version"] == 2
    assert row["stable_schedule_identity"] == "binance|futures_contract_launch|orig-article|ABCUSDT"
    assert res["valid"] is True


def test_formal_schedule_revision_contract_blocks_missing_provenance():
    row = build_formal_schedule_revision_row(
        source_article_id="revision-article",
        supersedes_source_article_id="orig-article",
        symbol="ABCUSDT",
        revised_anchor_ms=2_000,
        superseded_anchor_ms=1_000,
        revision_id="rev-1",
        revision_semantic_id="rev-1",
        revision_application_id="rev-1",
        revision_payload_version_id="payload-v1",
        revision_observation_id="obs-1",
        revision_payload_hash="payload-hash",
        revision_available_at_ms=1_500,
        revision_reason="rescheduled",
        provenance={},
    )

    res = validate_schedule_revision_contract(row)
    assert res["valid"] is False
    assert "revision_provenance_missing" in res["blockers"]


def test_ko_rddt_and_aia_fixture_metadata_assertions():
    ko_root = Path("tests/fixtures/external_signal_shadow/stage1_5f/ko_rddt_formal_v2_lineage")
    ko_event = json.loads((ko_root / "ko_rddt_stage1_5d_event.json").read_text())
    ko_meta = json.loads((ko_root / "ko_rddt_metadata.json").read_text())

    assert ko_event["source_article_id"] == "307687ad279e42e6909ee1be8c472b50"
    assert ko_event["symbols"] == ["KOUSDT", "RDDTUSDT"]
    assert ko_event["formal_event_contract_version"] == 2
    assert ko_event["source_contract_status"] == "formal_v2_valid"
    assert ko_meta["data_quality"] == "server_observed_formal_v2_event_row"
    assert ko_meta["not_a_raw_bapi_payload"] is True

    aia_meta_file = Path("tests/fixtures/external_signal_shadow/stage1_5d/schedule_revision_producer/aia_postponement_metadata.json")
    assert aia_meta_file.exists()
    aia_meta = json.loads(aia_meta_file.read_text())
    assert aia_meta["source_article_id"] == "a9f0566c85b54e30a63f1092e45d61f7"
    assert aia_meta["producer_enablement_blocker"] is True


def test_formal_schedule_revision_contract_explicit_intent_and_link_status():
    import pytest

    # Non-linked revision must raise AssertionError
    with pytest.raises(AssertionError, match="only linked revisions"):
        build_formal_schedule_revision_row(
            source_article_id="rev_1",
            supersedes_source_article_id="orig_1",
            symbol="ABCUSDT",
            revision_intent="rescheduled_with_new_anchor",
            link_status="orphaned",
            revised_anchor_ms=2000,
            superseded_anchor_ms=1000,
            revision_id="sem_1",
            revision_semantic_id="sem_1",
            revision_application_id="sem_1",
            revision_payload_version_id="payload-v1",
            revision_observation_id="obs-1",
            revision_payload_hash="hash_1",
            revision_available_at_ms=1500,
            provenance={"payload_sha256": "hash_1", "parser_version": "v1"},
        )

    # Cancelled revision must have cancelled status and null revised anchor
    cancelled = build_formal_schedule_revision_row(
        source_article_id="rev_cancel",
        supersedes_source_article_id="orig_1",
        symbol="ABCUSDT",
        revision_intent="cancelled",
        link_status="linked",
        revised_anchor_ms=None,
        superseded_anchor_ms=1000,
        revision_id="sem_cancel",
        revision_semantic_id="sem_cancel",
        revision_application_id="sem_cancel",
        revision_payload_version_id="payload-v1",
        revision_observation_id="obs-1",
        revision_payload_hash="hash_cancel",
        revision_available_at_ms=1500,
        provenance={"payload_sha256": "hash_cancel", "parser_version": "v1"},
    )
    assert cancelled["symbol_official_schedule_statuses"]["ABCUSDT"] == "cancelled"
    assert cancelled["symbol_revised_anchor_ms"]["ABCUSDT"] is None
    assert cancelled["revision_application_id"] == "sem_cancel"

    val = validate_schedule_revision_contract(cancelled)
    assert val["valid"] is True


def test_formal_schedule_revision_v2_rejects_missing_or_unequal_identity_fields():
    row = build_formal_schedule_revision_row(
        source_article_id="revision-article",
        supersedes_source_article_id="orig-article",
        symbol="ABCUSDT",
        revised_anchor_ms=2_000,
        revision_id="rev-1",
        revision_semantic_id="rev-1",
        revision_application_id="rev-1",
        revision_payload_version_id="payload-v1",
        revision_observation_id="obs-1",
        revision_payload_hash="payload-hash",
        revision_available_at_ms=1_500,
        provenance={"payload_sha256": "payload-hash", "parser_version": "test"},
    )
    row["revision_application_id"] = "different"
    result = validate_schedule_revision_contract(row)
    assert result["valid"] is False
    assert "revision_identity_mismatch" in result["blockers"]

    row = dict(row, revision_application_id="rev-1", revision_payload_version_id="")
    result = validate_schedule_revision_contract(row)
    assert result["valid"] is False
    assert "revision_payload_version_id_missing" in result["blockers"]
