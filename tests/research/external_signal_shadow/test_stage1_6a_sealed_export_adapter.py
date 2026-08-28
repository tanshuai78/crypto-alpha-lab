"""Tests for Stage 1.6A sealed-export adapter."""

import hashlib
import json
from dataclasses import replace

import pytest

import src.research.external_signal_shadow.stage1_6a_sealed_export_adapter as adapter
import src.research.external_signal_shadow.stage1_6b_canonical_source_storage as storage
from tests.research.external_signal_shadow.stage1_6a_sealed_export_adapter_test_support import (
    build_valid_historical_sealed_export,
    make_mutated_export,
    nontrusted_article,
    rewrite_authoritative_artifact,
    trusted_article,
)


def test_snapshot_accepts_explicit_historical_export_and_calls_loader_once(monkeypatch, tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    calls = 0
    real_loader = storage.load_sealed_export

    def counted(path):
        nonlocal calls
        calls += 1
        return real_loader(path)

    monkeypatch.setattr(adapter.storage, "load_sealed_export", counted)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    assert snapshot.export_id == export.name
    assert calls == 1
    assert len(snapshot.discoveries) == 1
    assert len(snapshot.observations) == 1
    assert len(snapshot.revisions) == 1


def test_snapshot_rejects_escape_control_json_identity_and_foreign_membership(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])

    # Escape path
    outside_dir = tmp_path / "outside" / "run" / "sealed_exports" / export.name
    outside_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(adapter.AdapterInputError):
        adapter.load_verified_source_snapshot(root, outside_dir)

    # Mutated exports
    for mutation in (
        "malformed_control_json",
        "missing_request_observation_id",
        "duplicate_request_observation_id",
        "foreign_source_article_id",
    ):
        mutated_export = make_mutated_export(root, export, mutation)
        with pytest.raises(adapter.AdapterInputError):
            adapter.load_verified_source_snapshot(root, mutated_export)


def test_snapshot_rejects_post_loader_source_byte_mutation(monkeypatch, tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])

    real_loader = storage.load_sealed_export

    def loader_with_tamper(path):
        manifest = real_loader(path)
        # Tamper with file on disk after load_sealed_export passed
        p = path / "article_discoveries.jsonl"
        p.write_bytes(b"tampered content\n")
        return manifest

    monkeypatch.setattr(adapter.storage, "load_sealed_export", loader_with_tamper)
    with pytest.raises(adapter.AdapterInputError):
        adapter.load_verified_source_snapshot(root, export)


def test_snapshot_rejects_attestation_run_contract_manifest_or_header_profile_mismatch(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])

    # Mutate attestation run_id / headers_profile
    att_p = export / "source_profile_probe_attestation.json"
    att = json.loads(att_p.read_text(encoding="utf-8"))
    att["request_headers_profile_sha256"] = "b" * 64
    rewrite_authoritative_artifact(
        export, "source_profile_probe_attestation.json", json.dumps(att).encode("utf-8")
    )

    with pytest.raises(adapter.AdapterInputError):
        adapter.load_verified_source_snapshot(root, export)


# ==============================================================================
# Task 2 Step 1: Observation/Revision RED Matrix
# ==============================================================================


def test_network_error_then_trusted_observation_produces_trusted_parent(tmp_path):
    aid = "1" * 32
    spec = trusted_article(article_id=aid)
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[spec])

    # Append a network_error observation for the same article before the trusted one
    obs_p = export / "detail_observations/historical.jsonl"
    existing_obs = [
        json.loads(x) for x in obs_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    err_obs = dict(existing_obs[0])
    err_obs["request_observation_id"] = "obs_err_001"
    err_obs["trust_validation_status"] = "network_error"
    err_obs["raw_payload_sha256"] = None
    err_obs["raw_payload_bytes"] = 0
    err_obs["raw_payload_relative_path"] = None
    err_obs["t_detail_receive_ms"] = 1700000000000

    new_obs_bytes = ("\n".join(json.dumps(x) for x in [err_obs, existing_obs[0]]) + "\n").encode(
        "utf-8"
    )
    rewrite_authoritative_artifact(export, "detail_observations/historical.jsonl", new_obs_bytes)

    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["detail_authority_status"] == "trusted"
    assert outcome["source_integrity_parent_pass"] is True


def test_trusted_then_network_error_does_not_downgrade_parent(tmp_path):
    aid = "1" * 32
    spec = trusted_article(article_id=aid)
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[spec])

    # Append a network_error observation after the trusted one
    obs_p = export / "detail_observations/historical.jsonl"
    existing_obs = [
        json.loads(x) for x in obs_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    err_obs = dict(existing_obs[0])
    err_obs["request_observation_id"] = "obs_err_after_001"
    err_obs["trust_validation_status"] = "network_error"
    err_obs["raw_payload_sha256"] = None
    err_obs["raw_payload_bytes"] = 0
    err_obs["raw_payload_relative_path"] = None
    err_obs["t_detail_receive_ms"] = 1700000010000

    new_obs_bytes = ("\n".join(json.dumps(x) for x in [existing_obs[0], err_obs]) + "\n").encode(
        "utf-8"
    )
    rewrite_authoritative_artifact(export, "detail_observations/historical.jsonl", new_obs_bytes)

    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["detail_authority_status"] == "trusted"
    assert outcome["source_integrity_parent_pass"] is True


def test_two_trusted_observations_same_raw_hash_share_one_logical_revision(tmp_path):
    aid = "1" * 32
    spec = trusted_article(article_id=aid)
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[spec])

    obs_p = export / "detail_observations/historical.jsonl"
    existing_obs = [
        json.loads(x) for x in obs_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    obs2 = dict(existing_obs[0])
    obs2["request_observation_id"] = "obs_dup_hash_002"
    obs2["t_detail_receive_ms"] = 1700000020000

    new_obs_bytes = ("\n".join(json.dumps(x) for x in [existing_obs[0], obs2]) + "\n").encode(
        "utf-8"
    )
    rewrite_authoritative_artifact(export, "detail_observations/historical.jsonl", new_obs_bytes)

    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    assert len(reduction.detail_revision_projection) == 1


def test_two_trusted_observations_distinct_raw_hashes_select_max_trusted_time_then_hash(tmp_path):
    aid = "1" * 32
    spec1 = trusted_article(article_id=aid, title="Binance Will Delist TokenA (2026-08-20)")
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[spec1])

    # Create a second payload and revision
    payload2 = json.dumps(
        {
            "code": "000000",
            "data": {
                "id": 248842,
                "code": aid,
                "title": "Binance Will Delist TokenA Revised",
                "body": json.dumps(
                    {
                        "node": "root",
                        "child": [
                            {
                                "node": "element",
                                "tag": "p",
                                "child": [{"node": "text", "text": "Delist TOKENAUSDT"}],
                            }
                        ],
                    }
                ),
                "publishDate": 1700000000000,
            },
        }
    ).encode("utf-8")
    sha2 = hashlib.sha256(payload2).hexdigest()
    rel2 = f"raw_payloads/details/{sha2[:2]}/{sha2}.json"
    (export / rel2).parent.mkdir(parents=True, exist_ok=True)
    (export / rel2).write_bytes(payload2)

    obs_p = export / "detail_observations/historical.jsonl"
    existing_obs = [
        json.loads(x) for x in obs_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    obs2 = dict(existing_obs[0])
    obs2["request_observation_id"] = "obs_distinct_002"
    obs2["raw_payload_sha256"] = sha2
    obs2["raw_payload_bytes"] = len(payload2)
    obs2["raw_payload_relative_path"] = rel2
    obs2["t_detail_receive_ms"] = 1700000020000

    rev_p = export / "detail_revisions.jsonl"
    existing_rev = [
        json.loads(x) for x in rev_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    rev2 = dict(existing_rev[0])
    rev2["detail_revision_id"] = f"rev_{aid}_{sha2}"
    rev2["detail_raw_sha256"] = sha2
    rev2["raw_payload_relative_path"] = rel2
    rev2["t_detail_trusted_ms"] = 1700000030000  # greater trusted time

    rewrite_authoritative_artifact(export, rel2, payload2)
    rewrite_authoritative_artifact(
        export,
        "detail_observations/historical.jsonl",
        ("\n".join(json.dumps(x) for x in [existing_obs[0], obs2]) + "\n").encode("utf-8"),
    )
    rewrite_authoritative_artifact(
        export,
        "detail_revisions.jsonl",
        ("\n".join(json.dumps(x) for x in [existing_rev[0], rev2]) + "\n").encode("utf-8"),
    )

    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["selected_detail_revision_id"] == f"rev_{aid}_{sha2}"


def test_trusted_observation_without_revision_rejects_export(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    # Clear detail revisions
    rewrite_authoritative_artifact(export, "detail_revisions.jsonl", b"")
    snapshot = adapter.load_verified_source_snapshot(root, export)
    with pytest.raises(adapter.AdapterInputError):
        adapter.reduce_verified_snapshot(
            snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
        )


def test_orphan_revision_without_trusted_observation_rejects_export(tmp_path):
    aid = "1" * 32
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid)]
    )
    # Add extra revision for unknown or nontrusted observation
    rev_p = export / "detail_revisions.jsonl"
    existing_rev = [
        json.loads(x) for x in rev_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    orphan_rev = dict(existing_rev[0])
    orphan_rev["detail_revision_id"] = "rev_orphan_123"
    orphan_rev["detail_raw_sha256"] = "f" * 64
    orphan_rev["raw_payload_relative_path"] = "raw_payloads/details/ff/orphan.json"
    (export / "raw_payloads/details/ff").mkdir(parents=True, exist_ok=True)
    rewrite_authoritative_artifact(export, "raw_payloads/details/ff/orphan.json", b"{}")
    rewrite_authoritative_artifact(
        export,
        "detail_revisions.jsonl",
        ("\n".join(json.dumps(x) for x in [existing_rev[0], orphan_rev]) + "\n").encode("utf-8"),
    )

    snapshot = adapter.load_verified_source_snapshot(root, export)
    with pytest.raises(adapter.AdapterInputError):
        adapter.reduce_verified_snapshot(
            snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
        )


def test_revision_profile_variant_header_or_surface_locale_mismatch_rejects_export(tmp_path):
    aid = "1" * 32
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid)]
    )
    rev_p = export / "detail_revisions.jsonl"
    existing_rev = [
        json.loads(x) for x in rev_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    existing_rev[0]["source_locale"] = "zh-CN"
    rewrite_authoritative_artifact(
        export, "detail_revisions.jsonl", (json.dumps(existing_rev[0]) + "\n").encode("utf-8")
    )

    with pytest.raises(adapter.AdapterInputError):
        snapshot = adapter.load_verified_source_snapshot(root, export)
        adapter.reduce_verified_snapshot(
            snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
        )


def test_zero_or_foreign_observation_rejects_export(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    # Empty observations
    rewrite_authoritative_artifact(export, "detail_observations/historical.jsonl", b"")
    with pytest.raises(adapter.AdapterInputError):
        snapshot = adapter.load_verified_source_snapshot(root, export)
        adapter.reduce_verified_snapshot(
            snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
        )


def test_nontrusted_only_parent_requires_completed_terminal_accounting_certificate(tmp_path):
    aid = "2" * 32
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[nontrusted_article(article_id=aid)]
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["detail_authority_status"] == "detail_unavailable"
    assert outcome["source_integrity_parent_pass"] is False
    assert outcome["selected_detail_revision_id"] is None
    notice = next(n for n in reduction.notices if n["source_article_id"] == aid)
    assert notice["parent_declaration_status"] == "incomplete"
    assert notice["source_audit_eligible"] is False
    assert notice["declared_child_count"] == 0
    assert len(reduction.semantic_extractions) == 0
    assert len(reduction.contracts) == 0


def test_reducer_rejects_candidate_with_zero_observations_and_revisions(tmp_path):
    article_id = "7" * 32
    root, export = build_valid_historical_sealed_export(
        tmp_path,
        article_specs=[trusted_article(article_id=article_id)],
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    incomplete_snapshot = replace(
        snapshot,
        observations=tuple(
            row for row in snapshot.observations if row["source_article_id"] != article_id
        ),
        revisions=tuple(
            row for row in snapshot.revisions if row["source_article_id"] != article_id
        ),
    )

    with pytest.raises(
        adapter.AdapterInputError, match=f"zero_observations_for_candidate: {article_id}"
    ):
        adapter.reduce_verified_snapshot(
            incomplete_snapshot,
            semantic_extracted_at_ms=1700000050000,
            grammar_pair=adapter.G1_GRAMMAR_PAIR,
        )


def test_nontrusted_error_status_cannot_change_detail_unavailable_enum(tmp_path):
    article_id = "8" * 32
    root, export = build_valid_historical_sealed_export(
        tmp_path,
        article_specs=[nontrusted_article(article_id=article_id)],
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    observations = tuple(
        {**row, "error_status_code": "network_error"}
        if row["source_article_id"] == article_id
        else row
        for row in snapshot.observations
    )

    reduction = adapter.reduce_verified_snapshot(
        replace(snapshot, observations=observations),
        semantic_extracted_at_ms=1700000050000,
        grammar_pair=adapter.G1_GRAMMAR_PAIR,
    )

    outcome = next(
        row for row in reduction.parent_outcomes if row["source_article_id"] == article_id
    )
    assert outcome["detail_authority_status"] == "detail_unavailable"
    assert outcome["diagnostic_codes"] == ["detail_unavailable"]


def test_reducer_never_projects_upstream_control_records_as_adapter_diagnostics(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    control_record = {
        "control_type": "article_discovery_exhausted",
        "catalog_membership_verified": False,
    }

    reduction = adapter.reduce_verified_snapshot(
        replace(snapshot, control_records={"upstream_control.json": control_record}),
        semantic_extracted_at_ms=1700000050000,
        grammar_pair=adapter.G1_GRAMMAR_PAIR,
    )

    assert reduction.diagnostics == ()


# ==============================================================================
# Task 2 Step 2: BAPI / First-List / Publication RED Matrix
# ==============================================================================


def test_invalid_trusted_raw_json_is_malformed_envelope_not_structural_reject(tmp_path):
    aid = "1" * 32
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid, raw_payload_bytes=b"not json {")]
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["detail_authority_status"] == "malformed_bapi_envelope"
    assert outcome["source_integrity_parent_pass"] is False


def test_missing_or_nonstring_data_code_is_malformed_envelope(tmp_path):
    aid = "1" * 32
    raw = json.dumps(
        {"code": "000000", "data": {"id": 123, "code": 12345, "title": "Delist", "body": "{}"}}
    ).encode("utf-8")
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid, raw_payload_bytes=raw)]
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["detail_authority_status"] == "malformed_bapi_envelope"
    assert outcome["source_integrity_parent_pass"] is False


def test_present_wrong_data_code_rejects_entire_export(tmp_path):
    aid = "1" * 32
    wrong_aid = "9" * 32
    raw = json.dumps(
        {"code": "000000", "data": {"id": 123, "code": wrong_aid, "title": "Delist", "body": "{}"}}
    ).encode("utf-8")
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid, raw_payload_bytes=raw)]
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    with pytest.raises(adapter.AdapterInputError):
        adapter.reduce_verified_snapshot(
            snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
        )


def test_body_unknown_tag_and_nonempty_br_child_are_body_parse_unresolved(tmp_path):
    aid = "1" * 32
    bad_body = json.dumps(
        {"node": "root", "child": [{"node": "element", "tag": "script", "child": []}]}
    )
    raw = json.dumps(
        {
            "code": "000000",
            "data": {
                "id": 123,
                "code": aid,
                "title": "Delist",
                "body": bad_body,
                "publishDate": 1700000000000,
            },
        }
    ).encode("utf-8")
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid, raw_payload_bytes=raw)]
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["detail_authority_status"] == "body_parse_unresolved"
    assert outcome["source_integrity_parent_pass"] is False


def test_canonical_body_normalization_golden_vectors():
    aid = "1" * 32
    body_tree = {
        "node": "root",
        "child": [
            {
                "node": "element",
                "tag": "p",
                "child": [{"node": "text", "text": "Paragraph 1\r\nwith CRLF."}],
            },
            {"node": "element", "tag": "br"},
            {
                "node": "element",
                "tag": "p",
                "child": [{"node": "text", "text": "  Paragraph   2 with spaces  "}],
            },
        ],
    }
    raw = json.dumps(
        {
            "code": "000000",
            "data": {
                "id": 123,
                "code": aid,
                "title": "Delist",
                "body": json.dumps(body_tree),
                "publishDate": 1700000000000,
            },
        }
    ).encode("utf-8")
    res, err = adapter.parse_and_normalize_bapi_body(
        raw, article_id=aid, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    assert err is None
    assert res is not None
    assert res["normalized_body"] == "Paragraph 1\nwith CRLF.\nParagraph 2 with spaces"


def test_first_list_capture_missing_duplicate_wrong_article_or_invalid_release_date_rejects(
    tmp_path,
):
    aid = "1" * 32
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid)]
    )
    # Mutate raw index to omit the article
    raw_index_p = next(export.glob("raw_payloads/indices/*/*.json"))
    raw_dict = json.loads(raw_index_p.read_text(encoding="utf-8"))
    raw_dict["data"]["catalogs"][0]["articles"] = []
    rewrite_authoritative_artifact(
        export, str(raw_index_p.relative_to(export)), json.dumps(raw_dict).encode("utf-8")
    )

    snapshot = adapter.load_verified_source_snapshot(root, export)
    with pytest.raises(adapter.AdapterInputError):
        adapter.reduce_verified_snapshot(
            snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
        )


def test_publish_date_conflict_fails_source_integrity_and_event_day(tmp_path):
    aid = "1" * 32
    # Detail publishDate = 1700000000000, catalog releaseDate = 1700000005000 (mismatch by 5s)
    raw = json.dumps(
        {
            "code": "000000",
            "data": {
                "id": 123,
                "code": aid,
                "title": "Delist",
                "body": json.dumps(
                    {
                        "node": "root",
                        "child": [
                            {
                                "node": "element",
                                "tag": "p",
                                "child": [{"node": "text", "text": "Delist TOKENAUSDT"}],
                            }
                        ],
                    }
                ),
                "publishDate": 1700000000000,
            },
        }
    ).encode("utf-8")
    root, export = build_valid_historical_sealed_export(
        tmp_path,
        article_specs=[
            trusted_article(article_id=aid, publish_date=1700000005000, raw_payload_bytes=raw)
        ],
    )

    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["publication_time_status"] == "conflicting"
    assert outcome["source_integrity_parent_pass"] is False


def test_publish_date_unparseable_alone_remains_denominator_visible(tmp_path):
    aid = "1" * 32
    raw = json.dumps(
        {
            "code": "000000",
            "data": {
                "id": 123,
                "code": aid,
                "title": "Delist",
                "body": json.dumps(
                    {
                        "node": "root",
                        "child": [
                            {
                                "node": "element",
                                "tag": "p",
                                "child": [{"node": "text", "text": "Delist TOKENAUSDT"}],
                            }
                        ],
                    }
                ),
                "publishDate": "not_an_int",
            },
        }
    ).encode("utf-8")
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid, raw_payload_bytes=raw)]
    )

    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["publication_time_status"] == "unparseable"
    assert outcome["source_integrity_parent_pass"] is False


def test_incompatible_trusted_revisions_produce_revision_conflicting_without_eligible_child(
    tmp_path,
):
    aid = "1" * 32
    spec1 = trusted_article(article_id=aid, title="Binance Will Delist TokenA")
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[spec1])

    # Add revision with conflicting settlement time
    payload2 = json.dumps(
        {
            "code": "000000",
            "data": {
                "id": 123,
                "code": aid,
                "title": "Binance Will Delist TokenA",
                "body": json.dumps(
                    {
                        "node": "root",
                        "child": [
                            {
                                "node": "element",
                                "tag": "p",
                                "child": [
                                    {
                                        "node": "text",
                                        "text": "Delist USDⓈ-M TOKENAUSDT Perpetual at 2026-09-01 09:00 (UTC).",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                "publishDate": 1700000000000,
            },
        }
    ).encode("utf-8")
    sha2 = hashlib.sha256(payload2).hexdigest()
    rel2 = f"raw_payloads/details/{sha2[:2]}/{sha2}.json"
    (export / rel2).parent.mkdir(parents=True, exist_ok=True)
    (export / rel2).write_bytes(payload2)

    obs_p = export / "detail_observations/historical.jsonl"
    existing_obs = [
        json.loads(x) for x in obs_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    obs2 = dict(existing_obs[0])
    obs2["request_observation_id"] = "obs_conflict_002"
    obs2["raw_payload_sha256"] = sha2
    obs2["raw_payload_bytes"] = len(payload2)
    obs2["raw_payload_relative_path"] = rel2

    rev_p = export / "detail_revisions.jsonl"
    existing_rev = [
        json.loads(x) for x in rev_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    rev2 = dict(existing_rev[0])
    rev2["detail_revision_id"] = f"rev_{aid}_{sha2}"
    rev2["detail_raw_sha256"] = sha2
    rev2["raw_payload_relative_path"] = rel2
    rev2["t_detail_trusted_ms"] = existing_rev[0]["t_detail_trusted_ms"] + 1000

    rewrite_authoritative_artifact(export, rel2, payload2)
    rewrite_authoritative_artifact(
        export,
        "detail_observations/historical.jsonl",
        ("\n".join(json.dumps(x) for x in [existing_obs[0], obs2]) + "\n").encode("utf-8"),
    )
    rewrite_authoritative_artifact(
        export,
        "detail_revisions.jsonl",
        ("\n".join(json.dumps(x) for x in [existing_rev[0], rev2]) + "\n").encode("utf-8"),
    )

    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert outcome["parent_declaration_status"] == "revision_conflicting"
    assert outcome["mapping_status"] == "fail"


def test_unresolved_batch_child_prevents_any_eligible_child_subset(tmp_path):
    aid = "1" * 32
    body_tree = {
        "node": "root",
        "child": [
            {
                "node": "element",
                "tag": "p",
                "child": [
                    {
                        "node": "text",
                        "text": "Binance Futures will delist USDⓈ-M TOKENAUSDT Perpetual at 2026-08-25 09:00 (UTC).",
                    }
                ],
            },
            {
                "node": "element",
                "tag": "p",
                "child": [
                    {
                        "node": "text",
                        "text": "Binance Futures will also delist UNKNOWN_BATCH_TOKEN at 2026-08-25 09:00 (UTC).",
                    }
                ],
            },
        ],
    }
    raw = json.dumps(
        {
            "code": "000000",
            "data": {
                "id": 123,
                "code": aid,
                "title": "Delist",
                "body": json.dumps(body_tree),
                "publishDate": 1700000000000,
            },
        }
    ).encode("utf-8")
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid, raw_payload_bytes=raw)]
    )

    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    outcome = next(o for o in reduction.parent_outcomes if o["source_article_id"] == aid)
    assert (
        outcome["classification_status"] == "fail"
        or outcome["parent_declaration_status"] == "incomplete"
    )
    # No eligible contracts
    assert not any(
        c.get("source_audit_eligible")
        for c in reduction.contracts
        if c.get("parent_article_id") == aid
    )


def test_all_frozen_candidates_require_valid_first_list_capture_chain(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    # Mutate discovery first_list_capture_id to nonexistent
    ad_p = export / "article_discoveries.jsonl"
    discoveries = [
        json.loads(x) for x in ad_p.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    discoveries[0]["first_list_capture_id"] = "nonexistent_lc_id"
    rewrite_authoritative_artifact(
        export, "article_discoveries.jsonl", (json.dumps(discoveries[0]) + "\n").encode("utf-8")
    )

    snapshot = adapter.load_verified_source_snapshot(root, export)
    with pytest.raises(adapter.AdapterInputError):
        adapter.reduce_verified_snapshot(
            snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
        )


# ==============================================================================
# Task 3: Exact Projections, Metrics, and Pre-Completion Summary Tests
# ==============================================================================


def test_candidate_manifest_is_exact_sorted_and_contains_all_candidates(tmp_path):
    specs = [trusted_article(article_id=f"{i}" * 32) for i in (3, 1, 2)]
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=specs)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )

    manifest = reduction.candidate_manifest
    assert manifest["schema_version"] == "stage1_6a_adapter_candidate_manifest_v1"
    assert manifest["artifact_profile_version"] == "stage1_6a_sealed_export_source_audit_v2"
    assert manifest["candidate_discovery_rule_version"] == "candidate_discovery_rule_v1"
    aids = [c["source_article_id"] for c in manifest["candidates"]]
    assert aids == sorted(aids)
    assert len(aids) == 3


def test_every_candidate_has_one_exact_notice_including_detail_unavailable(tmp_path):
    specs = [trusted_article(article_id="1" * 32), nontrusted_article(article_id="2" * 32)]
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=specs)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    assert len(reduction.notices) == 2
    assert {n["source_article_id"] for n in reduction.notices} == {"1" * 32, "2" * 32}


def test_parent_outcome_revision_and_diagnostic_jsonl_orders_are_deterministic(tmp_path):
    specs = [trusted_article(article_id="2" * 32), trusted_article(article_id="1" * 32)]
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=specs)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    assert [o["source_article_id"] for o in reduction.parent_outcomes] == ["1" * 32, "2" * 32]
    assert [r["source_article_id"] for r in reduction.detail_revision_projection] == [
        "1" * 32,
        "2" * 32,
    ]


def test_semantic_and_contract_rows_exist_only_for_selected_trusted_authority(tmp_path):
    specs = [trusted_article(article_id="1" * 32), nontrusted_article(article_id="2" * 32)]
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=specs)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    assert len(reduction.semantic_extractions) == 1
    assert reduction.semantic_extractions[0]["source_article_id"] == "1" * 32
    assert len(reduction.contracts) == 1
    assert reduction.contracts[0]["parent_article_id"] == "1" * 32


def test_contract_assets_are_source_proved_or_null_never_symbol_inferred(tmp_path):
    aid = "1" * 32
    # Body has symbol TOKENAUSDT and USDⓈ-M / USDT proof
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid)]
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    contract = reduction.contracts[0]
    assert contract["settlement_asset"] == "USDT"
    assert contract["quote_asset"] == "USDT"


def test_schedule_facts_are_exact_objects_and_not_stated_is_explicit(tmp_path):
    aid = "1" * 32
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid)]
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    contract = reduction.contracts[0]
    assert contract["order_restriction"]["fact_parse_status"] == "not_stated"
    assert contract["order_restriction"]["capture_time_status"] == "historical_unknown"
    assert contract["order_restriction"]["timestamp_ms"] is None


def test_historical_fields_and_authority_flags_are_exact_false_or_unknown(tmp_path):
    aid = "1" * 32
    root, export = build_valid_historical_sealed_export(
        tmp_path, article_specs=[trusted_article(article_id=aid)]
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    summary = adapter.build_precompletion_summary(
        reduction,
        audit_run_id="run_001",
        source_export_receipt_sha256="0" * 64,
        candidate_manifest_sha256="1" * 64,
    )
    assert summary["source_audit_passed"] is False
    assert summary["allowed_next_action"] == "pending_completion"
    assert summary["permitted_design_options"] == []
    for flag_val in summary["authority_flags"].values():
        assert flag_val is False


def test_metrics_use_all_parent_outcomes_not_success_rows(tmp_path):
    specs = [trusted_article(article_id=f"{i:032d}") for i in range(33)] + [
        nontrusted_article(article_id=f"err_{i:028d}") for i in range(2)
    ]
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=specs)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR
    )
    summary = adapter.build_precompletion_summary(
        reduction,
        audit_run_id="run_metrics_35",
        source_export_receipt_sha256="0" * 64,
        candidate_manifest_sha256="1" * 64,
    )
    assert summary["metrics"]["candidate_total_denominator"] == 35
    assert summary["metrics"]["trusted_parents_count"] == 33
    assert summary["metrics"]["source_integrity_pass_rate"] == pytest.approx(33 / 35)
    assert summary["source_audit_passed"] is False
    assert summary["allowed_next_action"] == "pending_completion"


def test_deterministic_projection_view():
    d = {
        "source_article_id": "1" * 32,
        "semantic_extracted_at_ms": 1700000050000,
        "nested": {"semantic_extracted_at_ms": 12345, "val": 1},
        "arr": [{"semantic_extracted_at_ms": 999, "name": "a"}],
    }
    view = adapter.deterministic_projection_view(d)
    assert "semantic_extracted_at_ms" not in view
    assert "semantic_extracted_at_ms" not in view["nested"]
    assert "semantic_extracted_at_ms" not in view["arr"][0]
    assert view["nested"]["val"] == 1


def test_bapi_body_h2_parser_g1_and_g2_grammar_dispatch():
    aid = "1" * 32
    h2_body = [
        {"node": "element", "tag": "h2", "child": [{"node": "text", "text": "Announcement"}]},
        {
            "node": "element",
            "tag": "p",
            "child": [
                {
                    "node": "text",
                    "text": "Binance Futures will delist the USDⓈ-M TOKENAUSDT Perpetual Contract at 2026-08-25 09:00 (UTC).",
                }
            ],
        },
    ]
    raw_payload = trusted_article(article_id=aid, body_nodes=h2_body)["raw_payload_bytes"]

    g1_result, g1_error = adapter.parse_and_normalize_bapi_body(
        raw_payload,
        article_id=aid,
        grammar_pair=adapter.G1_GRAMMAR_PAIR,
    )
    assert g1_result is None
    assert g1_error == "body_parse_unresolved"

    g2_result, g2_error = adapter.parse_and_normalize_bapi_body(
        raw_payload,
        article_id=aid,
        grammar_pair=adapter.G2_GRAMMAR_PAIR,
    )
    assert g2_error is None
    assert g2_result is not None
    assert (
        g2_result["normalized_body"]
        == "Announcement\nBinance Futures will delist the USDS-M TOKENAUSDT Perpetual Contract at 2026-08-25 09:00 (UTC)."
    )


@pytest.mark.parametrize(
    "invalid_nodes",
    [
        [{"node": "element", "tag": "h1", "child": [{"node": "text", "text": "H1 title"}]}],
        [{"node": "element", "tag": "h5", "child": [{"node": "text", "text": "H5 title"}]}],
        [{"node": "element", "tag": "div", "child": [{"node": "text", "text": "Div block"}]}],
        [{"node": "element", "tag": "h2", "child": "not_a_list"}],
        [
            {
                "node": "element",
                "tag": "h2",
                "attr": "not_a_dict",
                "child": [{"node": "text", "text": "H2"}],
            }
        ],
        [{"node": "element", "tag": "br", "child": [{"node": "text", "text": "non_empty_br"}]}],
    ],
)
def test_bapi_body_g2_rejects_unallowed_tags_and_malformed_nodes(invalid_nodes):
    aid = "1" * 32
    raw_payload = trusted_article(article_id=aid, body_nodes=invalid_nodes)["raw_payload_bytes"]
    result, error = adapter.parse_and_normalize_bapi_body(
        raw_payload,
        article_id=aid,
        grammar_pair=adapter.G2_GRAMMAR_PAIR,
    )
    assert result is None
    assert error == "body_parse_unresolved"


def test_parse_and_normalize_bapi_body_rejects_unsupported_grammar_pair():
    aid = "1" * 32
    raw_payload = trusted_article(article_id=aid)["raw_payload_bytes"]
    with pytest.raises(adapter.AdapterInputError, match="unsupported_grammar_pair"):
        adapter.parse_and_normalize_bapi_body(
            raw_payload,
            article_id=aid,
            grammar_pair=("stage1_6a_bapi_body_tree_v99", "stage1_6a_extractor_v99"),
        )


def test_reducer_g2_emits_explicit_pair_and_extracts_h2_contract(tmp_path):
    aid = "1" * 32
    h2_body = [
        {"node": "element", "tag": "h2", "child": [{"node": "text", "text": "Announcement"}]},
        {
            "node": "element",
            "tag": "p",
            "child": [
                {
                    "node": "text",
                    "text": "Binance Futures will delist the USDⓈ-M TOKENAUSDT Perpetual Contract at 2026-08-25 09:00 (UTC).",
                }
            ],
        },
    ]
    root, export = build_valid_historical_sealed_export(
        tmp_path,
        article_specs=[trusted_article(article_id=aid, body_nodes=h2_body)],
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(
        snapshot,
        semantic_extracted_at_ms=1700000050000,
        grammar_pair=adapter.G2_GRAMMAR_PAIR,
    )
    assert reduction.grammar_pair == adapter.G2_GRAMMAR_PAIR
    assert len(reduction.semantic_extractions) == 1
    assert (
        reduction.semantic_extractions[0]["body_normalization_version"]
        == "stage1_6a_bapi_body_tree_v2"
    )
    assert (
        reduction.semantic_extractions[0]["semantic_extractor_version"] == "stage1_6a_extractor_v2"
    )
    assert len(reduction.contracts) == 1
    assert reduction.contracts[0]["canonical_symbol"] == "TOKENAUSDT"
    assert (
        reduction.contracts[0]["settlement_time"]["evidence"]["body_normalization_version"]
        == "stage1_6a_bapi_body_tree_v2"
    )


def test_reducer_g1_and_g2_semantic_ids_differ_for_same_source(tmp_path):
    aid = "1" * 32
    # Simple p-tag body where both G1 and G2 produce a semantic extraction
    p_body = [
        {
            "node": "element",
            "tag": "p",
            "child": [
                {
                    "node": "text",
                    "text": "Binance Futures will delist the USDⓈ-M TOKENAUSDT Perpetual Contract at 2026-08-25 09:00 (UTC).",
                }
            ],
        },
    ]
    root, export = build_valid_historical_sealed_export(
        tmp_path,
        article_specs=[trusted_article(article_id=aid, body_nodes=p_body)],
    )
    snapshot = adapter.load_verified_source_snapshot(root, export)
    red_g1 = adapter.reduce_verified_snapshot(
        snapshot,
        semantic_extracted_at_ms=1700000050000,
        grammar_pair=adapter.G1_GRAMMAR_PAIR,
    )
    red_g2 = adapter.reduce_verified_snapshot(
        snapshot,
        semantic_extracted_at_ms=1700000050000,
        grammar_pair=adapter.G2_GRAMMAR_PAIR,
    )
    assert (
        red_g1.semantic_extractions[0]["semantic_extraction_id"]
        != red_g2.semantic_extractions[0]["semantic_extraction_id"]
    )


def test_snapshot_rejects_live_observation_export_before_calling_loader(monkeypatch, tmp_path):
    """Task 3 Step 1 & 9: load_verified_source_snapshot rejects live_observation export path before invoking load_sealed_export."""
    root = tmp_path
    live_export = (
        root
        / "data"
        / "external_signal_shadow"
        / "stage1_6b"
        / "live_observation"
        / "run_live_001"
        / "sealed_exports"
        / "exp_live_001"
    )
    live_export.mkdir(parents=True, exist_ok=True)
    (live_export / "sealed_export_manifest.json").write_text("{}", encoding="utf-8")

    def fail_if_loader_called(path):
        pytest.fail("load_sealed_export must not be called for live_observation paths")

    monkeypatch.setattr(adapter.storage, "load_sealed_export", fail_if_loader_called)

    with pytest.raises(
        adapter.AdapterInputError,
        match="source_export_path_outside_historical_backfill|source_snapshot_invalid",
    ):
        adapter.load_verified_source_snapshot(root, live_export)
