"""Tests for Stage 1.6A sealed-export adapter persistence and independent consumer."""

import hashlib
import json

import pytest

import src.research.external_signal_shadow.stage1_6a_sealed_export_adapter as adapter
import src.research.external_signal_shadow.stage1_6a_sealed_export_adapter_storage as adapter_storage
from tests.research.external_signal_shadow.stage1_6a_sealed_export_adapter_test_support import (
    build_valid_historical_sealed_export,
    trusted_article,
)


def test_persistence_writes_exact_artifacts_precompletion_then_manifest_last(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)

    run_id = "run_persist_001"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id

    manifest_path = adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    assert manifest_path.is_file()
    assert (out_root / "completion_manifest.json").is_file()
    assert (out_root / "source_export_receipt.json").is_file()
    assert (out_root / "audit_candidate_manifest.json").is_file()
    assert (out_root / "parent_audit_outcomes.jsonl").is_file()
    assert (out_root / "detail_revisions.jsonl").is_file()
    assert (out_root / "semantic_extractions.jsonl").is_file()
    assert (out_root / "delisting_notices.jsonl").is_file()
    assert (out_root / "delisting_contracts.jsonl").is_file()
    assert (out_root / "stage1_6a_futures_delisting_source_audit_summary.json").is_file()

    # Pre-completion summary check
    summary_data = json.loads((out_root / "stage1_6a_futures_delisting_source_audit_summary.json").read_text(encoding="utf-8"))
    assert summary_data["audit_summary_state"] == "pre_completion"
    assert summary_data["source_audit_passed"] is False


def test_persistence_binds_actual_sealed_export_manifest_bytes(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000000000, grammar_pair=adapter.G2_GRAMMAR_PAIR)
    out_root = tmp_path / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / "manifest_binding"

    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id="manifest_binding",
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000000000,
    )

    expected = hashlib.sha256((export / "sealed_export_manifest.json").read_bytes()).hexdigest()
    receipt = json.loads((out_root / "source_export_receipt.json").read_text())
    candidate_manifest = json.loads((out_root / "audit_candidate_manifest.json").read_text())
    completion = json.loads((out_root / "completion_manifest.json").read_text())
    assert receipt["input_manifest_sha256"] == expected
    assert candidate_manifest["input_manifest_sha256"] == expected
    assert completion["input_manifest_sha256"] == expected


def test_persistence_emits_only_approved_exact_authority_schemas(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000000000, grammar_pair=adapter.G2_GRAMMAR_PAIR)
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / "exact_schema"

    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id="exact_schema",
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000000000,
    )

    receipt = json.loads((out_root / "source_export_receipt.json").read_text())
    outcome = json.loads((out_root / "parent_audit_outcomes.jsonl").read_text().splitlines()[0])
    revision = json.loads((out_root / "detail_revisions.jsonl").read_text().splitlines()[0])
    summary = json.loads((out_root / "stage1_6a_futures_delisting_source_audit_summary.json").read_text())
    completion = json.loads((out_root / "completion_manifest.json").read_text())

    assert set(receipt) == {
        "schema_version", "artifact_profile_version", "input_export_id", "input_manifest_sha256",
        "capture_mode", "source_profile_id", "historical_range_from_ms", "historical_range_to_ms",
        "historical_coverage_sha256", "capture_run_contract_sha256",
        "source_profile_probe_attestation_sha256", "consumed_artifacts",
    }
    assert set(outcome) == {
        "schema_version", "artifact_profile_version", "source_article_id", "capture_mode",
        "semantic_extracted_at_ms", "notice_lineage_first_detected_at_ms",
        "system_available_at_ms", "fact_available_at_ms", "capture_time_status",
        "point_in_time_replay_eligible", "risk_veto_candidate", "detail_authority_status",
        "selected_detail_revision_id", "source_integrity_parent_pass", "source_published_at_ms",
        "publication_time_status", "parent_declaration_status", "mapping_status",
        "classification_status", "eligible_child_count", "diagnostic_codes",
    }
    assert set(revision) == {
        "schema_version", "artifact_profile_version", "source_article_id", "detail_revision_id",
        "detail_raw_sha256", "raw_payload_relative_path", "t_detail_trusted_ms", "source_surface",
        "source_locale", "request_variant", "bapi_numeric_id", "detail_authority_status",
        "selected_for_parent",
    }
    assert set(summary) == {
        "schema_version", "artifact_profile_version", "audit_run_id", "source_export_receipt_sha256",
        "input_export_id", "input_manifest_sha256", "audit_metric_definition_version",
        "candidate_discovery_rule_version", "audit_candidate_manifest_sha256",
        "body_normalization_version", "semantic_extractor_version", "threshold_snapshot", "metrics",
        "available_at_policy_defined", "source_schema_integrity_passed", "sample_sufficiency_passed",
        "source_audit_evidence_candidate_passed", "audit_summary_state", "source_audit_passed",
        "allowed_next_action", "permitted_design_options", "authority_flags",
    }
    assert set(completion) == {
        "schema_version", "artifact_profile_version", "status", "audit_run_id",
        "source_export_receipt_sha256", "input_export_id", "input_manifest_sha256",
        "audit_metric_definition_version", "body_normalization_version", "semantic_extractor_version",
        "threshold_snapshot", "metrics", "available_at_policy_defined",
        "source_schema_integrity_passed", "sample_sufficiency_passed",
        "source_audit_evidence_candidate_passed", "source_audit_passed", "allowed_next_action",
        "permitted_design_options", "authority_flags", "authoritative_artifacts", "completed_at_ms",
    }
    assert receipt["schema_version"] == "stage1_6a_source_export_receipt_v1"
    assert outcome["schema_version"] == "stage1_6a_parent_audit_outcome_v1"
    assert revision["schema_version"] == "stage1_6a_detail_revision_projection_v1"
    assert summary["schema_version"] == "stage1_6a_source_audit_summary_v1"
    assert completion["schema_version"] == "stage1_6a_source_audit_completion_manifest_v1"
    assert all(set(item) == {"relative_path", "sha256", "byte_length"} for item in completion["authoritative_artifacts"])


def test_completed_consumer_rejects_coherently_rehashed_receipt_schema_tamper(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000000000, grammar_pair=adapter.G2_GRAMMAR_PAIR)
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / "receipt_tamper"
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id="receipt_tamper",
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000000000,
    )

    receipt_path = out_root / "source_export_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["unexpected"] = True
    receipt_bytes = json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8")
    receipt_path.write_bytes(receipt_bytes)

    completion_path = out_root / "completion_manifest.json"
    completion = json.loads(completion_path.read_text())
    receipt_tuple = next(x for x in completion["authoritative_artifacts"] if x["relative_path"] == "source_export_receipt.json")
    receipt_tuple["sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
    receipt_tuple["byte_length"] = len(receipt_bytes)
    completion_path.write_text(json.dumps(completion, indent=2, sort_keys=True))

    with pytest.raises(adapter.AdapterInputError, match="receipt_exact_schema_invalid"):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)


def test_completed_consumer_rejects_coherently_rehashed_summary_binding_tamper(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path)
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000000000, grammar_pair=adapter.G2_GRAMMAR_PAIR)
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / "summary_tamper"
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id="summary_tamper",
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000000000,
    )

    summary_path = out_root / "stage1_6a_futures_delisting_source_audit_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["source_export_receipt_sha256"] = "0" * 64
    summary_bytes = json.dumps(summary, indent=2, sort_keys=True).encode("utf-8")
    summary_path.write_bytes(summary_bytes)

    completion_path = out_root / "completion_manifest.json"
    completion = json.loads(completion_path.read_text())
    summary_tuple = next(x for x in completion["authoritative_artifacts"] if x["relative_path"] == "stage1_6a_futures_delisting_source_audit_summary.json")
    summary_tuple["sha256"] = hashlib.sha256(summary_bytes).hexdigest()
    summary_tuple["byte_length"] = len(summary_bytes)
    completion_path.write_text(json.dumps(completion, indent=2, sort_keys=True))

    with pytest.raises(adapter.AdapterInputError, match="summary_projection_mismatch"):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)


def test_precompletion_summary_has_only_fixed_nonfinal_pass_and_pending_action(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)

    run_id = "run_persist_002"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    loaded = adapter_storage.load_completed_adapter_audit(root, out_root, export)
    assert loaded["completion_manifest"]["status"] == "complete"
    assert loaded["summary"]["source_audit_passed"] is False
    assert loaded["summary"]["audit_summary_state"] == "pre_completion"


def test_partial_root_without_completion_manifest_is_nonconsumable(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)

    run_id = "run_partial_003"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    # Delete completion_manifest.json
    (out_root / "completion_manifest.json").unlink()
    with pytest.raises(adapter.AdapterInputError):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)


def test_completed_consumer_rejects_hash_shape_and_projection_tamper(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)

    run_id = "run_tamper_004"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    # Tamper with delisting_contracts.jsonl
    contracts_p = out_root / "delisting_contracts.jsonl"
    contracts_p.write_text("tampered_contracts\n", encoding="utf-8")

    with pytest.raises(adapter.AdapterInputError):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)


def test_completed_consumer_rejects_coherent_source_derived_artifact_tamper(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)

    run_id = "run_coherent_tamper_005"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    # Tamper with parent_audit_outcomes and update completion_manifest hash to match tampered file
    po_p = out_root / "parent_audit_outcomes.jsonl"
    lines = [json.loads(x) for x in po_p.read_text(encoding="utf-8").splitlines() if x.strip()]
    lines[0]["source_integrity_parent_pass"] = False
    tampered_bytes = ("\n".join(json.dumps(x) for x in lines) + "\n").encode("utf-8")
    po_p.write_bytes(tampered_bytes)
    tampered_sha = hashlib.sha256(tampered_bytes).hexdigest()

    manifest_p = out_root / "completion_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    for art in manifest["authoritative_artifacts"]:
        if art["relative_path"] == "parent_audit_outcomes.jsonl":
            art["sha256"] = tampered_sha
            art["byte_count"] = len(tampered_bytes)
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Completed consumer must re-reduce source bytes and detect that tampered parent outcome does not match source
    with pytest.raises(adapter.AdapterInputError):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)


def test_completed_consumer_rejects_boolean_and_action_tampered_together(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)

    run_id = "run_bool_tamper_006"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    manifest_p = out_root / "completion_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["source_audit_passed"] = not manifest["source_audit_passed"]
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(adapter.AdapterInputError):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)


def test_completed_consumer_ignores_only_semantic_extracted_at_ms_in_rebuild(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)

    run_id = "run_time_ignore_007"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    loaded = adapter_storage.load_completed_adapter_audit(root, out_root, export)
    assert loaded["completion_manifest"]["status"] == "complete"


def test_completed_consumer_rejects_candidate_summary_binding_threshold_and_flag_mismatch(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)

    run_id = "run_flag_tamper_008"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    manifest_p = out_root / "completion_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["authority_flags"]["live_trading_allowed"] = True
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(adapter.AdapterInputError):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)


def test_completed_consumer_rejects_missing_or_mutated_explicit_source_export(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)

    run_id = "run_missing_src_009"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    nonexistent_export = root / "data" / "external_signal_shadow" / "stage1_6b" / "historical_backfill" / "none" / "sealed_exports" / "none"
    with pytest.raises(adapter.AdapterInputError):
        adapter_storage.load_completed_adapter_audit(root, out_root, nonexistent_export)


def test_new_writer_rejects_g1_reduction(tmp_path):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G1_GRAMMAR_PAIR)
    run_id = "run_g1_reject_001"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    with pytest.raises(adapter.AdapterInputError, match="new_writer_requires_g2_grammar_pair"):
        adapter_storage.persist_adapter_audit(
            out_root,
            audit_run_id=run_id,
            snapshot=snapshot,
            reduction=reduction,
            semantic_extracted_at_ms=1700000050000,
        )
    assert not out_root.exists()


def _rehash_artifact_in_completion(out_root, rel_path: str, new_bytes: bytes) -> None:
    target_path = out_root / rel_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(new_bytes)
    completion_path = out_root / "completion_manifest.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    for art in completion["authoritative_artifacts"]:
        if art["relative_path"] == rel_path:
            art["sha256"] = hashlib.sha256(new_bytes).hexdigest()
            art["byte_length"] = len(new_bytes)
    completion_path.write_text(json.dumps(completion, indent=2, sort_keys=True), encoding="utf-8")


def test_completed_consumer_rejects_summary_completion_grammar_pair_mismatch(tmp_path, monkeypatch):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)
    run_id = "run_pair_mismatch"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    summary_path = out_root / "stage1_6a_futures_delisting_source_audit_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["body_normalization_version"] = "stage1_6a_bapi_body_tree_v1"
    summary["semantic_extractor_version"] = "stage1_6a_extractor_v1"
    summary_bytes = json.dumps(summary, indent=2, sort_keys=True).encode("utf-8")
    _rehash_artifact_in_completion(out_root, "stage1_6a_futures_delisting_source_audit_summary.json", summary_bytes)

    load_snapshot_calls = []
    real_load_snapshot = adapter_storage.load_verified_source_snapshot

    def spy_load_snapshot(*args, **kwargs):
        load_snapshot_calls.append(args)
        return real_load_snapshot(*args, **kwargs)

    monkeypatch.setattr(adapter_storage, "load_verified_source_snapshot", spy_load_snapshot)

    with pytest.raises(adapter.AdapterInputError, match="persisted_grammar_pair_mismatch"):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)

    assert len(load_snapshot_calls) == 0


def test_completed_consumer_rejects_unsupported_grammar_pair(tmp_path, monkeypatch):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)
    run_id = "run_unsupported_pair"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    for fn in ("stage1_6a_futures_delisting_source_audit_summary.json", "completion_manifest.json"):
        fp = out_root / fn
        data = json.loads(fp.read_text(encoding="utf-8"))
        data["body_normalization_version"] = "stage1_6a_bapi_body_tree_v99"
        data["semantic_extractor_version"] = "stage1_6a_extractor_v99"
        fp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    # Rehash summary into completion
    sum_bytes = (out_root / "stage1_6a_futures_delisting_source_audit_summary.json").read_bytes()
    _rehash_artifact_in_completion(out_root, "stage1_6a_futures_delisting_source_audit_summary.json", sum_bytes)

    load_snapshot_calls = []
    real_load_snapshot = adapter_storage.load_verified_source_snapshot

    def spy_load_snapshot(*args, **kwargs):
        load_snapshot_calls.append(args)
        return real_load_snapshot(*args, **kwargs)

    monkeypatch.setattr(adapter_storage, "load_verified_source_snapshot", spy_load_snapshot)

    with pytest.raises(adapter.AdapterInputError, match="unsupported_grammar_pair"):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)

    assert len(load_snapshot_calls) == 0


def test_completed_consumer_rejects_missing_grammar_pair_member(tmp_path, monkeypatch):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)
    run_id = "run_missing_pair_member"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    summary_path = out_root / "stage1_6a_futures_delisting_source_audit_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["body_normalization_version"] = ""
    summary_bytes = json.dumps(summary, indent=2, sort_keys=True).encode("utf-8")
    _rehash_artifact_in_completion(out_root, "stage1_6a_futures_delisting_source_audit_summary.json", summary_bytes)

    load_snapshot_calls = []
    real_load_snapshot = adapter_storage.load_verified_source_snapshot

    def spy_load_snapshot(*args, **kwargs):
        load_snapshot_calls.append(args)
        return real_load_snapshot(*args, **kwargs)

    monkeypatch.setattr(adapter_storage, "load_verified_source_snapshot", spy_load_snapshot)

    with pytest.raises(adapter.AdapterInputError, match="persisted_grammar_pair_missing"):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)

    assert len(load_snapshot_calls) == 0


def test_completed_consumer_rejects_semantic_extraction_pair_mismatch(tmp_path, monkeypatch):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)
    run_id = "run_sem_pair_mismatch"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    sem_p = out_root / "semantic_extractions.jsonl"
    rows = [json.loads(x) for x in sem_p.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows[0]["body_normalization_version"] = "stage1_6a_bapi_body_tree_v1"
    new_bytes = ("\n".join(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows) + "\n").encode("utf-8")
    _rehash_artifact_in_completion(out_root, "semantic_extractions.jsonl", new_bytes)

    load_snapshot_calls = []
    real_load_snapshot = adapter_storage.load_verified_source_snapshot

    def spy_load_snapshot(*args, **kwargs):
        load_snapshot_calls.append(args)
        return real_load_snapshot(*args, **kwargs)

    monkeypatch.setattr(adapter_storage, "load_verified_source_snapshot", spy_load_snapshot)

    with pytest.raises(adapter.AdapterInputError, match="persisted_grammar_pair_projection_mismatch"):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)

    assert len(load_snapshot_calls) == 0


def test_completed_consumer_rejects_contract_schedule_evidence_pair_mismatch(tmp_path, monkeypatch):
    root, export = build_valid_historical_sealed_export(tmp_path, article_specs=[trusted_article()])
    snapshot = adapter.load_verified_source_snapshot(root, export)
    reduction = adapter.reduce_verified_snapshot(snapshot, semantic_extracted_at_ms=1700000050000, grammar_pair=adapter.G2_GRAMMAR_PAIR)
    run_id = "run_contract_evidence_pair_mismatch"
    out_root = root / "data" / "external_signal_shadow" / "stage1_6a" / "sealed_export_source_audits" / run_id
    adapter_storage.persist_adapter_audit(
        out_root,
        audit_run_id=run_id,
        snapshot=snapshot,
        reduction=reduction,
        semantic_extracted_at_ms=1700000050000,
    )

    contracts_p = out_root / "delisting_contracts.jsonl"
    rows = [json.loads(x) for x in contracts_p.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows[0]["settlement_time"]["evidence"]["body_normalization_version"] = "stage1_6a_bapi_body_tree_v1"
    new_bytes = ("\n".join(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows) + "\n").encode("utf-8")
    _rehash_artifact_in_completion(out_root, "delisting_contracts.jsonl", new_bytes)

    load_snapshot_calls = []
    real_load_snapshot = adapter_storage.load_verified_source_snapshot

    def spy_load_snapshot(*args, **kwargs):
        load_snapshot_calls.append(args)
        return real_load_snapshot(*args, **kwargs)

    monkeypatch.setattr(adapter_storage, "load_verified_source_snapshot", spy_load_snapshot)

    with pytest.raises(adapter.AdapterInputError, match="persisted_grammar_pair_projection_mismatch"):
        adapter_storage.load_completed_adapter_audit(root, out_root, export)

    assert len(load_snapshot_calls) == 0


def test_select_persisted_grammar_pair_accepts_g1_and_g2():
    summary_g1 = {"body_normalization_version": "stage1_6a_bapi_body_tree_v1", "semantic_extractor_version": "stage1_6a_extractor_v1"}
    completion_g1 = dict(summary_g1)
    assert adapter_storage._select_persisted_grammar_pair(summary_g1, completion_g1) == adapter.G1_GRAMMAR_PAIR

    summary_g2 = {"body_normalization_version": "stage1_6a_bapi_body_tree_v2", "semantic_extractor_version": "stage1_6a_extractor_v2"}
    completion_g2 = dict(summary_g2)
    assert adapter_storage._select_persisted_grammar_pair(summary_g2, completion_g2) == adapter.G2_GRAMMAR_PAIR
