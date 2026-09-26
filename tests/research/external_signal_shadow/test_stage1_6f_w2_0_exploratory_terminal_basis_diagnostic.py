"""Tests for Stage 1.6F-W2-0 exploratory terminal basis diagnostic.

Covers:
- Task 1 admission authority gates, external audit/receipt bindings, and single declared mutations.
- Task 2 verified row materialization, reducer, complete 41/27 ledgers, endpoint validation, and classifications.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import src.research.external_signal_shadow.stage1_6f_w2_0_exploratory_terminal_basis_diagnostic as w2_0_diag
import src.research.external_signal_shadow.stage1_6f_w2_evidence_source as w2_source
from tests.research.external_signal_shadow.stage1_6f_w2_0_test_support import (
    EXTERNAL_AUDIT_SHA,
    FROZEN_20_FALSE_FLAGS,
    HISTORICAL_RECEIPT_SHA,
    W2_CANDIDATE_MANIFEST_SHA,
    create_canonical_w2_0_mirror,
)

# ─── Task 1: Admission & Authority Tests ─────────────────────────────────────


def test_admission_canonical_positive(tmp_path: Path) -> None:
    """Canonical mirror with exact authorities must pass admission cleanly."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()

    admission = w2_0_diag.admit_w2_0_inputs(**kwargs)
    assert admission.candidate_run_id == "w2_candidate_run_20260925_001"
    assert admission.outcome_inspection_status == "outcome_seen"
    assert admission.audit_verdict == "complete"
    assert admission.candidate_manifest_sha256 == W2_CANDIDATE_MANIFEST_SHA
    assert admission.external_audit_sha256 == EXTERNAL_AUDIT_SHA
    assert admission.historical_receipt_sha256 == HISTORICAL_RECEIPT_SHA


def test_admission_rejects_design_sha_mutation(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()
    kwargs["w2_0_design_sha"] = "0" * 64

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:w2_0_design_sha_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_plan_sha_mutation(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()
    kwargs["w2_0_plan_sha"] = "0" * 64

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:w2_0_plan_sha_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_network_auth_sha_mutation(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()
    kwargs["w2_network_auth_sha"] = "0" * 64

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:w2_network_auth_sha_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_manifest_sha_mutation(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()
    kwargs["candidate_manifest_sha"] = "0" * 64

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:candidate_manifest_sha_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_audit_sha_mutation(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()
    kwargs["external_audit_sha"] = "0" * 64

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:external_audit_sha_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_audit_verdict_mutation(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()

    mut_audit = tmp_path / "mutated_audit.md"
    content = mirror.external_audit_path.read_text(encoding="utf-8")
    mutated_content = content.replace("Verdict: `complete`", "Verdict: `incomplete`")
    assert mutated_content != content
    mut_audit.write_text(mutated_content, encoding="utf-8")
    mut_sha = hashlib.sha256(mut_audit.read_bytes()).hexdigest()

    kwargs["external_audit_path"] = mut_audit
    kwargs["external_audit_sha"] = mut_sha

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:audit_verdict_not_complete"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_receipt_sha_mutation(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()
    kwargs["historical_receipt_sha"] = "0" * 64

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:historical_receipt_sha_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_receipt_run_id_mismatch(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()

    mut_receipt = tmp_path / "mutated_receipt.json"
    receipt_data = json.loads(mirror.historical_receipt_path.read_text(encoding="utf-8"))
    receipt_data["candidate_run_id"] = "forged_run_id"
    mut_receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
    mut_sha = hashlib.sha256(mut_receipt.read_bytes()).hexdigest()

    kwargs["historical_receipt_path"] = mut_receipt
    kwargs["historical_receipt_sha"] = mut_sha

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:receipt_run_id_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_receipt_manifest_mismatch(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()

    mut_receipt = tmp_path / "mutated_receipt.json"
    receipt_data = json.loads(mirror.historical_receipt_path.read_text(encoding="utf-8"))
    receipt_data["final_manifest_sha256"] = "0" * 64
    mut_receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
    mut_sha = hashlib.sha256(mut_receipt.read_bytes()).hexdigest()

    kwargs["historical_receipt_path"] = mut_receipt
    kwargs["historical_receipt_sha"] = mut_sha

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:receipt_manifest_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_receipt_audit_mismatch(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()

    mut_receipt = tmp_path / "mutated_receipt.json"
    receipt_data = json.loads(mirror.historical_receipt_path.read_text(encoding="utf-8"))
    receipt_data["completion_audit_review_artifact_sha256"] = "0" * 64
    mut_receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
    mut_sha = hashlib.sha256(mut_receipt.read_bytes()).hexdigest()

    kwargs["historical_receipt_path"] = mut_receipt
    kwargs["historical_receipt_sha"] = mut_sha

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:receipt_audit_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_receipt_issued_status_mismatch(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()

    mut_receipt = tmp_path / "mutated_receipt.json"
    receipt_data = json.loads(mirror.historical_receipt_path.read_text(encoding="utf-8"))
    receipt_data["outcome_inspection_status"] = "outcome_seen"
    mut_receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
    mut_sha = hashlib.sha256(mut_receipt.read_bytes()).hexdigest()

    kwargs["historical_receipt_path"] = mut_receipt
    kwargs["historical_receipt_sha"] = mut_sha

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:receipt_issued_status_not_not_seen"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


def test_admission_rejects_receipt_forbidden_key(tmp_path: Path) -> None:
    mirror = create_canonical_w2_0_mirror(tmp_path)
    kwargs = mirror.get_admission_kwargs()

    mut_receipt = tmp_path / "mutated_receipt.json"
    receipt_data = json.loads(mirror.historical_receipt_path.read_text(encoding="utf-8"))
    receipt_data["extra_forbidden_key"] = "bad"
    mut_receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
    mut_sha = hashlib.sha256(mut_receipt.read_bytes()).hexdigest()

    kwargs["historical_receipt_path"] = mut_receipt
    kwargs["historical_receipt_sha"] = mut_sha

    with pytest.raises(w2_0_diag.W20AdmissionError, match="STOP=w2_0_admission_invalid:receipt_keys_mismatch"):
        w2_0_diag.admit_w2_0_inputs(**kwargs)


# ─── Task 2: Materialization, Reducer & Invariant Tests ───────────────────────


def _load_canonical_w2_evidence(mirror) -> w2_source.VerifiedW2Evidence:
    """Helper to run strict reader on canonical mirror."""
    return w2_source.load_verified_w2_evidence(
        project_root=mirror.project_root,
        candidate_root=mirror.candidate_root,
        approved_design_path=mirror.w2_design_path,
        approved_design_sha=mirror.w2_design_sha,
        approved_plan_path=mirror.w2_plan_path,
        approved_plan_sha=mirror.w2_plan_sha,
        network_authorization_path=mirror.w2_network_auth_path,
        network_authorization_sha=mirror.w2_network_auth_sha,
    )


def test_canonical_materialization_and_reducer(tmp_path: Path) -> None:
    """Full canonical integration: admission -> strict reader -> materializer -> reducer."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    admission = w2_0_diag.admit_w2_0_inputs(**mirror.get_admission_kwargs())
    verified_w2 = _load_canonical_w2_evidence(mirror)

    # 1. Materialize verified rows
    verified_rows = w2_0_diag.materialize_verified_w2_rows(verified_w2=verified_w2)
    assert len(verified_rows.rows_by_physical_id) == len(verified_w2.physical_source_objects)

    # 2. Interior row proof: verify at least one identity has C[0] and C[-1] as interior rows
    # (neither the 0th nor the 23rd row of that day's physical CSV), proving rows come from
    # materialized parsed_rows map rather than manifest first_row/last_row.
    found_interior = False
    for denom in verified_w2.denominator_records:
        if denom["temporal_status"] == "window_defined":
            _, comp = w2_source.compute_w2_grid_points(denom["window_start_ms"], denom["window_end_ms"])
            if len(comp) > 0:
                t_first, t_last = comp[0], comp[-1]
                # Check hour of day
                h_first = (t_first // 3600000) % 24
                h_last = (t_last // 3600000) % 24
                if 0 < h_first < 23 and 0 < h_last < 23:
                    found_interior = True
                    break
    assert found_interior, "Expected at least one canonical identity with interior complete bar timestamps"

    # 3. Compute diagnostic result
    result = w2_0_diag.compute_w2_0_exploratory_terminal_basis(
        verified_w2=verified_w2,
        verified_rows=verified_rows,
        admission=admission,
    )

    # 4. Verify 41 contracts and 27 parents conservation
    assert len(result.contract_records) == 41
    assert len(result.parent_records) == 27

    # Count statuses
    contract_statuses = [c.status for c in result.contract_records]
    assert contract_statuses.count("exploratory_described") == 29
    assert contract_statuses.count("diagnostic_incomplete:temporal_unproven") == 10
    assert contract_statuses.count("diagnostic_incomplete:no_complete_bars") == 2

    parent_statuses = [p.status for p in result.parent_records]
    assert parent_statuses.count("exploratory_described") == 19
    assert parent_statuses.count("diagnostic_incomplete:temporal_unproven") == 6
    assert parent_statuses.count("diagnostic_incomplete:no_complete_bars") == 2

    # 5. Check summary metrics and research classification
    assert result.summary.outcome_inspection_status == "outcome_seen"
    assert result.summary.research_classification == "exploratory_only"
    assert result.summary.perp_index_summary.metric_evidence_status == "exploratory_described"
    assert result.summary.mark_index_summary.metric_evidence_status == "exploratory_described"
    assert result.summary.perp_index_summary.n_parent_exploratory_described == 19
    assert result.summary.mark_index_summary.n_parent_exploratory_described == 19

    # 6. Verify 20 authority flags exact match
    assert result.authority_flags == FROZEN_20_FALSE_FLAGS


def test_materialization_rejects_validator_failure(tmp_path: Path, monkeypatch) -> None:
    """Declared monkeypatch makes production validate_w2_zip_and_csv reject -> STOP."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    verified_w2 = _load_canonical_w2_evidence(mirror)

    # Monkeypatch validate_w2_zip_and_csv to simulate validator rejection
    def _mock_validate(zip_path, csv_path, url):
        raise w2_source.W2EvidenceSourceError("w2_root_invalid:csv_invalid:simulated_corrupt")

    monkeypatch.setattr(w2_0_diag, "validate_w2_zip_and_csv", _mock_validate)

    with pytest.raises(
        w2_0_diag.W20MaterializationError,
        match="STOP=w2_0_candidate_row_materialization_invalid:production_validator_rejected",
    ):
        w2_0_diag.materialize_verified_w2_rows(verified_w2=verified_w2)


def test_reducer_endpoint_coverage_gap_mutation(tmp_path: Path) -> None:
    """Removing one C[0] row from verified rows produces diagnostic_incomplete:endpoint_coverage_gap without global STOP."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    admission = w2_0_diag.admit_w2_0_inputs(**mirror.get_admission_kwargs())
    verified_w2 = _load_canonical_w2_evidence(mirror)
    verified_rows = w2_0_diag.materialize_verified_w2_rows(verified_w2=verified_w2)

    # Find the first complete contract and remove C[0] from its klines rows
    target_contract = None
    target_c0 = None
    for denom in verified_w2.denominator_records:
        if denom["temporal_status"] == "window_defined":
            _, comp = w2_source.compute_w2_grid_points(denom["window_start_ms"], denom["window_end_ms"])
            if len(comp) > 0:
                target_contract = denom
                target_c0 = comp[0]
                break
    assert target_contract is not None

    # Mutate verified_rows by filtering out target_c0 for this contract's physical objects
    mut_rows_map = dict(verified_rows.rows_by_physical_id)
    # Find logical records for this contract
    c_sym = target_contract["canonical_symbol"]
    mutated_any = False
    for log_rec in verified_w2.logical_archive_records:
        proj = log_rec["matrix_record_projection_v1"]
        if proj["canonical_symbol"] == c_sym and proj["metric"] == "klines_1h":
            pid = log_rec["physical_source_object_id"]
            orig_rows = mut_rows_map[pid]
            filtered = tuple(r for r in orig_rows if r["open_time"] != target_c0)
            if len(filtered) < len(orig_rows):
                mut_rows_map[pid] = filtered
                mutated_any = True
                break
    assert mutated_any

    mutated_verified_rows = w2_0_diag.W20VerifiedRows(rows_by_physical_id=mut_rows_map)

    # Pass to production reducer: must NOT crash, must preserve 41 contracts
    result = w2_0_diag.compute_w2_0_exploratory_terminal_basis(
        verified_w2=verified_w2,
        verified_rows=mutated_verified_rows,
        admission=admission,
    )
    assert len(result.contract_records) == 41
    # Check that this contract is now endpoint_coverage_gap
    contract_rec = [c for c in result.contract_records if c.canonical_symbol == c_sym][0]
    assert contract_rec.status == "diagnostic_incomplete:endpoint_coverage_gap"


def test_reducer_duplicate_timestamp_mutation(tmp_path: Path) -> None:
    """Appending a duplicate open_time row to verified rows produces diagnostic_incomplete:duplicate_timestamp."""
    mirror = create_canonical_w2_0_mirror(tmp_path)
    admission = w2_0_diag.admit_w2_0_inputs(**mirror.get_admission_kwargs())
    verified_w2 = _load_canonical_w2_evidence(mirror)
    verified_rows = w2_0_diag.materialize_verified_w2_rows(verified_w2=verified_w2)

    # Find the first complete contract
    target_contract = None
    target_c0 = None
    for denom in verified_w2.denominator_records:
        if denom["temporal_status"] == "window_defined":
            _, comp = w2_source.compute_w2_grid_points(denom["window_start_ms"], denom["window_end_ms"])
            if len(comp) > 0:
                target_contract = denom
                target_c0 = comp[0]
                break
    assert target_contract is not None

    # Mutate verified_rows by appending a duplicate row with target_c0 open_time
    mut_rows_map = dict(verified_rows.rows_by_physical_id)
    c_sym = target_contract["canonical_symbol"]
    mutated = False
    for log_rec in verified_w2.logical_archive_records:
        proj = log_rec["matrix_record_projection_v1"]
        if proj["canonical_symbol"] == c_sym and proj["metric"] == "klines_1h":
            pid = log_rec["physical_source_object_id"]
            orig_rows = list(mut_rows_map[pid])
            matching = [r for r in orig_rows if r["open_time"] == target_c0]
            assert len(matching) == 1
            # Append duplicate row
            dup_row = dict(matching[0])
            dup_row["close"] = matching[0]["close"] + 1.0  # slight difference
            orig_rows.append(dup_row)
            mut_rows_map[pid] = tuple(orig_rows)
            mutated = True
            break
    assert mutated

    mutated_verified_rows = w2_0_diag.W20VerifiedRows(rows_by_physical_id=mut_rows_map)

    # Pass to production reducer
    result = w2_0_diag.compute_w2_0_exploratory_terminal_basis(
        verified_w2=verified_w2,
        verified_rows=mutated_verified_rows,
        admission=admission,
    )
    assert len(result.contract_records) == 41
    assert len(result.parent_records) == 27
    contract_rec = [c for c in result.contract_records if c.canonical_symbol == c_sym][0]
    assert contract_rec.status == "diagnostic_incomplete:duplicate_timestamp"



def test_pure_arithmetic_and_field_exclusion() -> None:
    """Pure arithmetic helper test: formula is exact, and forbidden price direction/PnL fields are absent."""
    # Test formula: 10_000 * (close - index) / index
    perp_close = 105.0
    index_close = 100.0
    basis = w2_0_diag.calculate_basis_bps(price=perp_close, index_price=index_close)
    assert basis == 500.0

    # delta_abs_basis_bps: abs(last) - abs(first)
    # If first was 500 bps and last was 100 bps, delta is 100 - 500 = -400 (shrunk toward 0)
    delta = w2_0_diag.calculate_delta_abs_basis(basis_first=500.0, basis_last=100.0)
    assert delta == -400.0

    # Ensure dataclasses exclude raw OHLC, open, high, low, return, PnL, signal, direction
    c_fields = {f.name for f in w2_0_diag.W20ContractRecord.__dataclass_fields__.values()}
    forbidden = {"open", "high", "low", "ohlc", "return", "pnl", "direction", "signal", "order", "cost", "fee"}
    assert not (c_fields & forbidden), f"Forbidden fields found in W20ContractRecord: {c_fields & forbidden}"


def test_nearest_rank_quantiles() -> None:
    """Quantile calculation follows exact nearest-rank formula rank = ceil(p*n)."""
    # 19 values from 1 to 19
    values = [float(i) for i in range(1, 20)]
    q25 = w2_0_diag.compute_nearest_rank_quantile(values, 0.25)
    # rank = ceil(0.25 * 19) = ceil(4.75) = 5 -> value 5.0
    assert q25 == 5.0

    q75 = w2_0_diag.compute_nearest_rank_quantile(values, 0.75)
    # rank = ceil(0.75 * 19) = ceil(14.25) = 15 -> value 15.0
    assert q75 == 15.0

    med = w2_0_diag.compute_median(values)
    assert med == 10.0


def test_classification_reducer() -> None:
    """Research classification reducer logic according to Design §1."""
    # If either metric has >= 1 descriptor -> exploratory_only
    assert w2_0_diag.reduce_research_classification(n_perp_descriptors=1, n_mark_descriptors=0) == "exploratory_only"
    assert w2_0_diag.reduce_research_classification(n_perp_descriptors=0, n_mark_descriptors=1) == "exploratory_only"
    assert w2_0_diag.reduce_research_classification(n_perp_descriptors=19, n_mark_descriptors=19) == "exploratory_only"

    # Both 0 -> evidence_insufficient
    assert w2_0_diag.reduce_research_classification(n_perp_descriptors=0, n_mark_descriptors=0) == "evidence_insufficient"
