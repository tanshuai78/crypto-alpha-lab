"""Contract tests for stage1_6f_candidate_w1_descriptive_diagnostic.py.

Invariants: INV-CA04, INV-CA05, INV-CA06, INV-CA08, INV-CA11, INV-CA12.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import (
    CANONICAL_CANDIDATE_RELATIVE_PATH,
    EXACT_EXPECTED_13_FALSE_MAPPING,
    bind_candidate_publication_authority,
    bind_verified_candidate_c_authority,
    load_verified_candidate_evidence,
)
from src.research.external_signal_shadow.stage1_6f_candidate_w1_descriptive_diagnostic import (
    EXPECTED_19_METRIC_HORIZON_TUPLES,
    CandidateW1DiagnosticResult,
    compute_candidate_w1_descriptive_diagnostic,
)
from tests.research.external_signal_shadow.stage1_6f_candidate_w1_test_support import (
    B_SOURCE_EXPORT_RELATIVE,
    C_COMPLETED_ROOT_RELATIVE,
    FROZEN_EXPANSION_DESIGN_PATH,
    FROZEN_EXPANSION_DESIGN_SHA,
    FROZEN_EXPANSION_PLAN_PATH,
    FROZEN_EXPANSION_PLAN_SHA,
    FROZEN_NETWORK_AUTH_PATH,
    FROZEN_NETWORK_AUTH_SHA,
    create_canonical_project_mirror,
    load_canonical_verified_c_input,
)


@pytest.fixture(scope="module")
def canonical_mirror(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("canonical_mirror_w1")
    return create_canonical_project_mirror(base)


@pytest.fixture(scope="module")
def candidate_w1_result(canonical_mirror: Path) -> CandidateW1DiagnosticResult:
    """Run full candidate W1 descriptive reducer once on canonical mirror."""
    verified_candidate = load_verified_candidate_evidence(
        project_root=canonical_mirror,
        candidate_root=canonical_mirror / CANONICAL_CANDIDATE_RELATIVE_PATH,
        approved_design_path=canonical_mirror / FROZEN_EXPANSION_DESIGN_PATH,
        approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
        approved_plan_path=canonical_mirror / FROZEN_EXPANSION_PLAN_PATH,
        approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
        network_authorization_path=canonical_mirror / FROZEN_NETWORK_AUTH_PATH,
        network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
    )
    verified_c = load_canonical_verified_c_input(canonical_mirror)
    c_auth = bind_verified_candidate_c_authority(
        verified_candidate=verified_candidate,
        verified_c=verified_c,
        completed_root=canonical_mirror / C_COMPLETED_ROOT_RELATIVE,
        source_export=canonical_mirror / B_SOURCE_EXPORT_RELATIVE,
    )
    pub_auth = bind_candidate_publication_authority(
        verified_candidate=verified_candidate,
        verified_c=verified_c,
    )
    return compute_candidate_w1_descriptive_diagnostic(
        verified_candidate=verified_candidate,
        verified_c=verified_c,
        c_authority=c_auth,
        publication_authority=pub_auth,
    )


def test_candidate_w1_cardinality_and_tuples(candidate_w1_result: CandidateW1DiagnosticResult):
    """Assert exactly 41 denominator rows and 779 metric records across 19 tuples."""
    assert len(candidate_w1_result.denominator_rows) == 41
    assert len(candidate_w1_result.metric_records) == 41 * 19  # 779
    assert len(EXPECTED_19_METRIC_HORIZON_TUPLES) == 19

    # Assert deterministic denominator ordering by (parent_article_id, contract_id, canonical_symbol)
    denom_keys = [
        (d.parent_article_id, d.contract_id, d.canonical_symbol)
        for d in candidate_w1_result.denominator_rows
    ]
    assert denom_keys == sorted(denom_keys)

    # Assert 41 symbols match cohort
    symbols = [d.canonical_symbol for d in candidate_w1_result.denominator_rows]
    assert "REEFUSDT" not in symbols
    assert len(set(symbols)) == 41

    # Check each of the 19 tuples has exactly 41 records split between descriptive_only and diagnostic_incomplete
    records_by_tuple: Dict[tuple, List[Any]] = {}
    for r in candidate_w1_result.metric_records:
        tup = (r.metric_name, r.horizon)
        if tup not in records_by_tuple:
            records_by_tuple[tup] = []
        records_by_tuple[tup].append(r)

    assert set(records_by_tuple.keys()) == set(EXPECTED_19_METRIC_HORIZON_TUPLES)
    for tup, recs in records_by_tuple.items():
        assert len(recs) == 41
        for rec in recs:
            assert rec.status in {"descriptive_only", "diagnostic_incomplete"}
            if rec.status == "descriptive_only":
                assert rec.gate_failures == []
                assert isinstance(rec.descriptors, dict) and len(rec.descriptors) > 0
            else:
                assert rec.descriptors == {}
                assert len(rec.gate_failures) > 0


def test_candidate_w1_time_rules_and_notes(candidate_w1_result: CandidateW1DiagnosticResult):
    """Assert exact note literals, complete bar rules, and time constraints."""
    expected_notes = {
        "hourly_bar_observation": "hourly_bar_open_time_in_window_observation_only",
        "price_path": "coarse_complete_post_publication_bar_close_proxy",
        "perp_index_basis": "perp_index_reference_basis_only",
        "mark_index_basis": "non_tradable_reference_only",
        "funding_observations": "discrete_observations_only_no_carry_pnl",
        "open_interest": "raw_open_interest_observation_only",
        "visible_depth_proxy": "visible_discrete_depth_proxy_only_no_slippage",
        "agg_trade_observations": "exchange_label_only_not_aggressor_inference",
    }

    for rec in candidate_w1_result.metric_records:
        if rec.status == "descriptive_only":
            assert rec.descriptors.get("note") == expected_notes[rec.metric_name]

            # Price path: no return_bps or control-related fields
            if rec.metric_name == "price_path":
                assert "return_bps" not in rec.descriptors
                assert "control" not in str(rec.descriptors)
                assert "bar_close_change_bps" in rec.descriptors
                assert rec.descriptors["bar_count"] >= 2

            # H1 hourly_bar_observation has no price_change_bps
            if rec.metric_name == "hourly_bar_observation":
                assert "price_change_bps" not in rec.descriptors
                assert "bar_close_change_bps" not in rec.descriptors


def test_candidate_w1_source_family_audits(candidate_w1_result: CandidateW1DiagnosticResult):
    """Assert source_family_audits sorting, fields, and logical record ID union."""
    for rec in candidate_w1_result.metric_records:
        audits = rec.source_family_audits
        assert len(audits) >= 1
        # Check sorted lexicographically by family_name
        family_names = [a["family_name"] for a in audits]
        assert family_names == sorted(family_names)

        # Multi-family basis metrics must have exactly 2 family audits
        if rec.metric_name in {"perp_index_basis", "mark_index_basis"}:
            assert len(audits) == 2

        # Check union of logical record IDs
        expected_union = sorted({lid for a in audits for lid in a["logical_record_ids"]})
        assert rec.source_logical_archive_record_ids == expected_union

        # Check each audit item has exact required keys
        expected_audit_keys = {
            "family_name",
            "coverage_status",
            "coverage_reason",
            "logical_record_ids",
            "timestamp_field",
            "first_observed_ms",
            "last_observed_ms",
            "row_count",
            "duplicate_count",
            "conflict_count",
            "gap_count",
        }
        for a in audits:
            assert set(a.keys()) == expected_audit_keys
            if a["row_count"] > 0:
                assert a["first_observed_ms"] is not None
                assert a["last_observed_ms"] is not None
                assert a["first_observed_ms"] <= a["last_observed_ms"]
            else:
                assert a["first_observed_ms"] is None
                assert a["last_observed_ms"] is None


def test_candidate_w1_zero_price_denominator_and_gate_failures():
    """Verify zero price denominator mutation yields diagnostic_incomplete and exact failure."""
    from src.research.external_signal_shadow.stage1_6f_candidate_w1_descriptive_diagnostic import (
        reduce_price_path_metric,
    )

    # When first_complete_bar_close is 0.0
    mock_bars = [
        {"open_time": 1000, "close_time": 1000 + 3600000 - 1, "close": 0.0},
        {"open_time": 1000 + 3600000, "close_time": 1000 + 7200000 - 1, "close": 10.0},
    ]
    status, descriptors, failures = reduce_price_path_metric(
        bars=mock_bars,
        coverage_admissible=True,
    )
    assert status == "diagnostic_incomplete"
    assert descriptors == {}
    assert failures == ["zero_price_path_denominator"]


def test_candidate_w1_pit_and_authority_invariants(candidate_w1_result: CandidateW1DiagnosticResult):
    """Assert PIT fields and authority flags on all denominator and metric records."""
    expected_flags = EXACT_EXPECTED_13_FALSE_MAPPING

    for denom in candidate_w1_result.denominator_rows:
        assert denom.publication_time_authority == "parent_audit_outcomes.source_published_at_ms_selected_trusted_bapi_publishDate"
        assert denom.point_in_time_source_validated is False
        assert denom.capture_time_status == "historical_unknown"
        assert denom.system_available_at_ms is None
        assert denom.fact_available_at_ms is None
        assert denom.authority_flags == expected_flags
        assert denom.eligibility_passed is True
        assert denom.ineligibility_reasons == []

    for rec in candidate_w1_result.metric_records:
        assert rec.publication_time_authority == "parent_audit_outcomes.source_published_at_ms_selected_trusted_bapi_publishDate"
        assert rec.point_in_time_source_validated is False
        assert rec.capture_time_status == "historical_unknown"
        assert rec.system_available_at_ms is None
        assert rec.fact_available_at_ms is None
        assert rec.authority_flags == expected_flags


def test_candidate_w1_numeric_finiteness(candidate_w1_result: CandidateW1DiagnosticResult):
    """Assert all descriptor numbers are finite without NaN or Infinity."""
    for rec in candidate_w1_result.metric_records:
        if rec.status == "descriptive_only":
            for k, v in rec.descriptors.items():
                if isinstance(v, (int, float)):
                    assert not isinstance(v, bool)
                    assert math.isfinite(v)
                elif isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        if isinstance(sub_v, (int, float)):
                            assert not isinstance(sub_v, bool)
                            assert math.isfinite(sub_v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            for sub_k, sub_v in item.items():
                                if isinstance(sub_v, (int, float)):
                                    assert not isinstance(sub_v, bool)
                                    assert math.isfinite(sub_v)
