"""Tests for Stage 1.6F diagnostic storage: atomic bundle writer and read-only reviewer core."""

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    compute_descriptive_metrics,
    reconstruct_denominator,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    verify_c_input,
    verify_market_evidence,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_storage import (
    REQUIRED_BUNDLE_NON_MANIFEST_ARTIFACTS,
    DiagnosticStorageError,
    load_diagnostic_bundle,
    write_diagnostic_bundle,
)
from tests.research.external_signal_shadow.stage1_6f_historical_diagnostic_test_support import (
    build_valid_completed_c_root,
    copy_market_evidence_package,
)


def _prepare_sample_bundle_data(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    verified_c = verify_c_input(project_root, completed_root, source_export)
    pkg_dir = copy_market_evidence_package(tmp_path)
    verified_market = verify_market_evidence(pkg_dir)

    denominator = reconstruct_denominator(verified_c)
    # Compute metrics for first row
    first_row = denominator[0]
    matched_controls = ["AXLUSDT", "AKTUSDT", "REZUSDT"]
    first_row = dataclasses.replace(
        first_row,
        match_status="matched",
        selected_controls=tuple(matched_controls),
    )
    denominator[0] = first_row
    metrics = compute_descriptive_metrics(
        symbol=first_row.symbol,
        t_pub_ms=first_row.t_pub_ms or 1736928006723,
        t_settle_ms=first_row.t_settle_ms,
        selected_controls=matched_controls,
        verified_market=verified_market,
        parent_article_id=first_row.parent_article_id,
        contract_id=first_row.contract_id,
        ineligibility_reasons=first_row.ineligibility_reasons,
    )
    return verified_c, verified_market, denominator, metrics


def test_write_and_load_diagnostic_bundle_positive(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)

    out_root = tmp_path / "output_bundle_001"
    manifest_p = write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    assert manifest_p.is_file()
    assert manifest_p.name == "stage1_6f_diagnostic_bundle_manifest.json"

    # Verify all non-manifest artifacts exist
    for rel_p in REQUIRED_BUNDLE_NON_MANIFEST_ARTIFACTS:
        assert (out_root / rel_p).is_file()

    # Load and verify bundle
    bundle = load_diagnostic_bundle(out_root)
    assert bundle["manifest"]["schema_version"] == "stage1_6f_diagnostic_bundle_manifest_v1"
    assert bundle["manifest"]["bundle_state"] == "diagnostic_incomplete"
    assert len(bundle["denominator"]) == len(denominator)
    assert len(bundle["diagnostics"]) == len(metrics)
    assert bundle["summary"]["schema_version"] == "stage1_6f_historical_mechanism_diagnostic_v1"
    assert bundle["receipt"]["input_export_id"] == verified_c.input_export_id


def test_write_diagnostic_bundle_rejects_existing_completed_root(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    out_root = tmp_path / "output_bundle_002"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    # Attempt to write again to the same completed root must fail
    with pytest.raises(DiagnosticStorageError, match="output_root_already_completed"):
        write_diagnostic_bundle(
            output_root=out_root,
            verified_c=verified_c,
            verified_market=verified_market,
            denominator_rows=denominator,
            diagnostic_metrics=metrics,
            bundle_state="diagnostic_incomplete",
        )


def test_load_diagnostic_bundle_rejects_missing_manifest(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    out_root = tmp_path / "output_bundle_003"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    # Delete manifest to simulate pre-manifest crash or partial root
    (out_root / "stage1_6f_diagnostic_bundle_manifest.json").unlink()

    with pytest.raises(DiagnosticStorageError, match="bundle_manifest_missing"):
        load_diagnostic_bundle(out_root)


def test_load_diagnostic_bundle_rejects_hash_mismatch_after_manifest(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    out_root = tmp_path / "output_bundle_004"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    # Mutate summary on disk after manifest publication
    summary_p = out_root / "stage1_6f_diagnostic_summary.json"
    summary_p.write_bytes(summary_p.read_bytes() + b"\n")

    with pytest.raises(DiagnosticStorageError, match="bundle_artifact_hash_mismatch"):
        load_diagnostic_bundle(out_root)


def test_load_diagnostic_bundle_rejects_extra_manifest_artifact(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    out_root = tmp_path / "output_bundle_005"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    manifest_p = out_root / "stage1_6f_diagnostic_bundle_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["artifacts"].append({
        "relative_path": "extra.json",
        "sha256": "0" * 64,
        "byte_length": 10,
    })
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(DiagnosticStorageError, match="bundle_manifest_invalid"):
        load_diagnostic_bundle(out_root)


def test_load_diagnostic_bundle_rejects_duplicate_manifest_artifact(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    out_root = tmp_path / "output_bundle_006"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    manifest_p = out_root / "stage1_6f_diagnostic_bundle_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["artifacts"].append(dict(manifest["artifacts"][0]))
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(DiagnosticStorageError, match="bundle_manifest_invalid"):
        load_diagnostic_bundle(out_root)


def test_load_diagnostic_bundle_rejects_unknown_bundle_state(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    out_root = tmp_path / "output_bundle_007"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    manifest_p = out_root / "stage1_6f_diagnostic_bundle_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["bundle_state"] = "unauthorized_state_completed"
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(DiagnosticStorageError, match="bundle_manifest_invalid"):
        load_diagnostic_bundle(out_root)


def test_load_diagnostic_bundle_rejects_non_false_authority_flag(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    out_root = tmp_path / "output_bundle_008"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    manifest_p = out_root / "stage1_6f_diagnostic_bundle_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    manifest["authority_flags"]["live_trading_allowed"] = True
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(DiagnosticStorageError, match="permission_or_side_effect_violation"):
        load_diagnostic_bundle(out_root)


def test_load_diagnostic_bundle_rejects_missing_record_provenance(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    out_root = tmp_path / "output_bundle_009"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    # Mutate denominator row by dropping market_evidence_manifest_sha256
    denom_p = out_root / "stage1_6f_event_denominator.jsonl"
    lines = [json.loads(x) for x in denom_p.read_text(encoding="utf-8").splitlines() if x.strip()]
    lines[0].pop("market_evidence_manifest_sha256")
    new_data = ("\n".join(json.dumps(x) for x in lines) + "\n").encode("utf-8")
    denom_p.write_bytes(new_data)

    # Update manifest so hash matches new file, but provenance validation fails
    manifest_p = out_root / "stage1_6f_diagnostic_bundle_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    for art in manifest["artifacts"]:
        if art["relative_path"] == "stage1_6f_event_denominator.jsonl":
            art["sha256"] = hashlib.sha256(new_data).hexdigest()
            art["byte_length"] = len(new_data)
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(DiagnosticStorageError, match="record_provenance_contract_invalid"):
        load_diagnostic_bundle(out_root)


@pytest.mark.parametrize("missing_field", [
    "parent_article_id",
    "contract_id",
    "symbol",
    "original_interval",
    "controls_or_exclusion_reasons",
])
def test_load_diagnostic_bundle_rejects_missing_metric_provenance_and_linkage(tmp_path: Path, missing_field: str):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    out_root = tmp_path / f"output_bundle_missing_{missing_field}"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    # Mutate metric row by dropping the required field
    diag_p = out_root / "stage1_6f_metric_diagnostics.jsonl"
    lines = [json.loads(x) for x in diag_p.read_text(encoding="utf-8").splitlines() if x.strip()]
    lines[0].pop(missing_field, None)
    new_data = ("\n".join(json.dumps(x) for x in lines) + "\n").encode("utf-8")
    diag_p.write_bytes(new_data)

    # Update manifest to match byte length and hash
    manifest_p = out_root / "stage1_6f_diagnostic_bundle_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    for art in manifest["artifacts"]:
        if art["relative_path"] == "stage1_6f_metric_diagnostics.jsonl":
            art["sha256"] = hashlib.sha256(new_data).hexdigest()
            art["byte_length"] = len(new_data)
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(DiagnosticStorageError, match="record_provenance_contract_invalid"):
        load_diagnostic_bundle(out_root)


def test_load_diagnostic_bundle_rejects_cross_contract_rebind(tmp_path: Path):
    verified_c, verified_market, denominator, metrics = _prepare_sample_bundle_data(tmp_path)
    assert len(denominator) >= 2, "Need at least two denominator rows for cross-contract test"
    row_0 = denominator[0]
    row_1 = denominator[1]
    out_root = tmp_path / "output_bundle_cross_rebind"

    write_diagnostic_bundle(
        output_root=out_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=denominator,
        diagnostic_metrics=metrics,
        bundle_state="diagnostic_incomplete",
    )

    # Rebind the first metric row (belonging to row_0) to row_1's identity
    diag_p = out_root / "stage1_6f_metric_diagnostics.jsonl"
    lines = [json.loads(x) for x in diag_p.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert lines[0]["contract_id"] == row_0.contract_id
    lines[0]["parent_article_id"] = row_1.parent_article_id
    lines[0]["contract_id"] = row_1.contract_id
    lines[0]["symbol"] = row_1.symbol
    new_data = ("\n".join(json.dumps(x) for x in lines) + "\n").encode("utf-8")
    diag_p.write_bytes(new_data)

    # Update manifest so hashes and byte lengths match
    manifest_p = out_root / "stage1_6f_diagnostic_bundle_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8"))
    for art in manifest["artifacts"]:
        if art["relative_path"] == "stage1_6f_metric_diagnostics.jsonl":
            art["sha256"] = hashlib.sha256(new_data).hexdigest()
            art["byte_length"] = len(new_data)
    manifest_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with pytest.raises(DiagnosticStorageError, match="record_provenance_contract_invalid"):
        load_diagnostic_bundle(out_root)

