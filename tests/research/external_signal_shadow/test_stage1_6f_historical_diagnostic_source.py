"""Tests for Stage 1.6F historical diagnostic source verifiers (C input and market evidence)."""

import json
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    REQUIRED_C_AUTHORITATIVE_ARTIFACTS,
    MarketEvidenceInvalidError,
    SourceInvalidError,
    VerifiedCInput,
    VerifiedMarketEvidence,
    parse_audit_diagnostics,
    parse_candidate_manifest,
    parse_delisting_contracts,
    parse_delisting_notices,
    parse_detail_revisions,
    parse_parent_audit_outcomes,
    parse_receipt,
    parse_semantic_extractions,
    parse_strict_csv,
    parse_summary,
    verify_c_input,
    verify_market_evidence,
)
from tests.research.external_signal_shadow.stage1_6f_historical_diagnostic_test_support import (
    build_insufficient_completed_c_root,
    build_valid_completed_c_root,
    copy_market_evidence_package,
)


def test_verify_c_input_positive(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    verified = verify_c_input(project_root, completed_root, source_export)

    assert isinstance(verified, VerifiedCInput)
    assert verified.input_export_id
    assert verified.input_manifest_sha256
    assert verified.source_export_receipt_sha256

    # Exact 9 authoritative artifacts
    assert len(verified.authoritative_artifacts) == 9
    assert set(verified.retained_bytes.keys()) == set(REQUIRED_C_AUTHORITATIVE_ARTIFACTS)
    assert set(verified.retained_sha256.keys()) == set(REQUIRED_C_AUTHORITATIVE_ARTIFACTS)

    # Validate parsing helpers from retained bytes
    receipt = parse_receipt(verified)
    assert receipt["schema_version"] == "stage1_6a_source_export_receipt_v1"

    summary = parse_summary(verified)
    assert summary["schema_version"] == "stage1_6a_source_audit_summary_v1"

    candidate_manifest = parse_candidate_manifest(verified)
    assert "candidates" in candidate_manifest

    outcomes = parse_parent_audit_outcomes(verified)
    assert len(outcomes) > 0

    revisions = parse_detail_revisions(verified)
    assert len(revisions) > 0

    extractions = parse_semantic_extractions(verified)
    assert len(extractions) > 0

    notices = parse_delisting_notices(verified)
    assert len(notices) > 0

    contracts = parse_delisting_contracts(verified)
    assert len(contracts) > 0

    diagnostics = parse_audit_diagnostics(verified)
    assert isinstance(diagnostics, list)


def test_verify_c_input_rejects_nonexistent_paths(tmp_path: Path):
    nonexistent = tmp_path / "nonexistent"
    with pytest.raises(SourceInvalidError, match="source_invalid"):
        verify_c_input(tmp_path, nonexistent, nonexistent)


def test_verify_c_input_rejects_insufficient_source_audit(tmp_path: Path):
    project_root, completed_root, source_export = build_insufficient_completed_c_root(tmp_path)
    with pytest.raises(SourceInvalidError, match="source_invalid"):
        verify_c_input(project_root, completed_root, source_export)


def test_verify_c_input_rejects_missing_authoritative_artifact_in_manifest(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)

    # Mutate completion_manifest.json to drop one artifact
    manifest_p = completed_root / "completion_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["authoritative_artifacts"] = [
        art for art in manifest["authoritative_artifacts"]
        if art["relative_path"] != "delisting_contracts.jsonl"
    ]
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(SourceInvalidError, match="source_invalid"):
        verify_c_input(project_root, completed_root, source_export)


def test_verify_c_input_rejects_extra_authoritative_artifact_in_manifest(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)

    manifest_p = completed_root / "completion_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["authoritative_artifacts"].append({
        "relative_path": "extra_artifact.json",
        "sha256": "0" * 64,
        "byte_length": 10,
    })
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(SourceInvalidError, match="source_invalid"):
        verify_c_input(project_root, completed_root, source_export)


def test_verify_c_input_rejects_duplicate_authoritative_artifact_in_manifest(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)

    manifest_p = completed_root / "completion_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["authoritative_artifacts"].append(dict(manifest["authoritative_artifacts"][0]))
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(SourceInvalidError, match="source_invalid"):
        verify_c_input(project_root, completed_root, source_export)


def test_verify_c_input_rejects_path_traversal(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)

    manifest_p = completed_root / "completion_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["authoritative_artifacts"][0]["relative_path"] = "../traversal.json"
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(SourceInvalidError, match="source_invalid"):
        verify_c_input(project_root, completed_root, source_export)


def test_verify_c_input_rejects_post_loader_file_mutation(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)

    # Mutate one artifact file directly on disk after audit is persisted
    target_file = completed_root / "delisting_contracts.jsonl"
    target_file.write_bytes(target_file.read_bytes() + b"\n")

    with pytest.raises(SourceInvalidError, match="source_invalid"):
        verify_c_input(project_root, completed_root, source_export)


def test_verify_c_input_never_reopens_path_after_verification(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    verified = verify_c_input(project_root, completed_root, source_export)

    contracts_before = parse_delisting_contracts(verified)
    assert len(contracts_before) > 0

    # Delete the underlying file on disk completely
    (completed_root / "delisting_contracts.jsonl").unlink()

    # Parsing must still succeed from retained in-memory bytes without touching disk
    contracts_after = parse_delisting_contracts(verified)
    assert contracts_after == contracts_before


def test_verify_market_evidence_positive(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    verified = verify_market_evidence(pkg_dir)

    assert isinstance(verified, VerifiedMarketEvidence)
    assert verified.manifest_sha256 == "9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f"
    assert len(verified.csv_records) == 148
    assert len(verified.auxiliary_artifacts) == 6

    # Verify series parsed correctly
    reef_1h = verified.get_series("klines_1h", "REEFUSDT")
    assert reef_1h is not None
    assert len(reef_1h) > 0

    axl_1h = verified.get_series("klines_1h", "AXLUSDT")
    assert axl_1h is not None
    assert len(axl_1h) > 0

    reef_metrics = verified.get_series("metrics_5m", "REEFUSDT")
    assert reef_metrics is not None
    assert len(reef_metrics) > 0

    reef_funding = verified.get_series("funding_rate", "REEFUSDT")
    assert reef_funding is not None
    assert len(reef_funding) > 0

    reef_depth = verified.get_series("book_depth", "REEFUSDT")
    assert reef_depth is not None
    assert len(reef_depth) > 0

    reef_trades = verified.get_series("agg_trades", "REEFUSDT")
    assert reef_trades is not None
    assert len(reef_trades) > 0


def test_verify_market_evidence_rejects_coherent_package_mutation_unapproved_identity(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)

    # Coherent-package mutation: alter one CSV, update its hash and size in manifest
    manifest_p = pkg_dir / "gap02_evidence_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))

    first_art = manifest["artifacts"][0]
    csv_rec = first_art["csv_records"][0]
    csv_path = pkg_dir / csv_rec["relative_csv_path"]

    # Append a newline or dummy space
    new_bytes = csv_path.read_bytes() + b"\n"
    csv_path.write_bytes(new_bytes)

    import hashlib
    csv_rec["csv_sha256"] = hashlib.sha256(new_bytes).hexdigest()
    csv_rec["csv_size_bytes"] = len(new_bytes)

    # Save manifest: now it is self-consistent with files on disk, but manifest SHA256 has changed!
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(MarketEvidenceInvalidError, match="unapproved_market_evidence_identity"):
        verify_market_evidence(pkg_dir)


def test_verify_market_evidence_rejects_csv_hash_mismatch(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    manifest_p = pkg_dir / "gap02_evidence_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    csv_path = pkg_dir / manifest["artifacts"][0]["csv_records"][0]["relative_csv_path"]
    csv_path.write_bytes(csv_path.read_bytes() + b"X")

    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        verify_market_evidence(pkg_dir)


def test_verify_market_evidence_rejects_zip_hash_mismatch(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    manifest_p = pkg_dir / "gap02_evidence_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    zip_path = pkg_dir / manifest["artifacts"][0]["relative_zip_path"]
    zip_path.write_bytes(zip_path.read_bytes() + b"X")

    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        verify_market_evidence(pkg_dir)


def test_verify_market_evidence_rejects_byte_count_mismatch(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    manifest_p = pkg_dir / "gap02_evidence_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    csv_path = pkg_dir / manifest["artifacts"][0]["csv_records"][0]["relative_csv_path"]
    # Truncate by 1 byte
    csv_path.write_bytes(csv_path.read_bytes()[:-1])

    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        verify_market_evidence(pkg_dir)


def test_verify_market_evidence_rejects_missing_file(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    manifest_p = pkg_dir / "gap02_evidence_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    csv_path = pkg_dir / manifest["artifacts"][0]["csv_records"][0]["relative_csv_path"]
    csv_path.unlink()

    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        verify_market_evidence(pkg_dir)


def test_verify_market_evidence_rejects_duplicate_manifest_path(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    manifest_p = pkg_dir / "gap02_evidence_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["artifacts"].append(dict(manifest["artifacts"][0]))
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        verify_market_evidence(pkg_dir)


def test_verify_market_evidence_rejects_unlisted_extra_path(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    extra_file = pkg_dir / "unlisted_intruder.csv"
    extra_file.write_text("dummy", encoding="utf-8")

    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        verify_market_evidence(pkg_dir)


def test_verify_market_evidence_rejects_path_traversal(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    manifest_p = pkg_dir / "gap02_evidence_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["relative_zip_path"] = "../traversal.zip"
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        verify_market_evidence(pkg_dir)


def test_verify_market_evidence_rejects_symlink(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    manifest_p = pkg_dir / "gap02_evidence_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    csv_path = pkg_dir / manifest["artifacts"][0]["csv_records"][0]["relative_csv_path"]
    real_csv = csv_path.parent / "real_file.csv"
    csv_path.rename(real_csv)
    csv_path.symlink_to(real_csv)

    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        verify_market_evidence(pkg_dir)


def test_verify_market_evidence_rejects_auxiliary_artifact_hash_mismatch(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    aux_path = pkg_dir / "data_semantics_contract.json"
    aux_path.write_bytes(aux_path.read_bytes() + b" ")

    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        verify_market_evidence(pkg_dir)


def test_strict_csv_parser_validations():
    # 1. Invalid UTF-8
    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        parse_strict_csv(b"\xff\xfe\x00\x00", "klines_1h")

    # 2. Header mismatch (wrong column name)
    bad_header = b"open_time,wrong,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n1736294400000,1,1,1,1,1,1736297999999,1,1,1,1,0\n"
    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        parse_strict_csv(bad_header, "klines_1h")

    # 3. Non-finite numeric (NaN)
    nan_row = b"open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n1736294400000,NaN,1,1,1,1,1736297999999,1,1,1,1,0\n"
    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        parse_strict_csv(nan_row, "klines_1h")

    # 4. Non-finite numeric (Infinity)
    inf_row = b"open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n1736294400000,Infinity,1,1,1,1,1736297999999,1,1,1,1,0\n"
    with pytest.raises(MarketEvidenceInvalidError, match="market_evidence_invalid"):
        parse_strict_csv(inf_row, "klines_1h")

