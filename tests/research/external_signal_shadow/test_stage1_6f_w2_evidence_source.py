"""Tests for stage1_6f_w2_evidence_source.py.

Invariants: INV-W2E01, INV-W2E02, INV-W2E03, INV-W2E10, INV-W2E13.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

import src.research.external_signal_shadow.stage1_6f_w2_evidence_source as source
from tests.research.external_signal_shadow.stage1_6f_w2_test_support import (
    ALL_URLS_SHA256,
    B_SOURCE_EXPORT_RELATIVE,
    C_COMPLETED_ROOT_RELATIVE,
    CANONICAL_002_RELATIVE_PATH,
    COVERAGE_MATRIX_RELATIVE,
    FETCH_URLS_SHA256,
    REUSE_URLS_SHA256,
    W2_DESIGN_PATH,
    W2_DESIGN_SHA,
    W2_PLAN_PATH,
    W2_PLAN_SHA,
    CanonicalW2Root,
    build_canonical_w2_root_fixture,
    create_canonical_project_mirror,
    create_test_network_authorization,
    mutate_mirror_file,
)


@pytest.fixture(scope="module")
def canonical_mirror(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("canonical_w2_mirror")
    return create_canonical_project_mirror(base)


@pytest.fixture
def canonical_w2_inputs(canonical_mirror: Path, tmp_path: Path) -> Dict[str, Any]:
    auth_path = tmp_path / "test_w2_network_auth.json"
    auth_file, auth_sha = create_test_network_authorization(
        auth_path,
        run_id="w2_test_run_001",
    )
    return {
        "project_root": canonical_mirror,
        "c_completed_root": canonical_mirror / C_COMPLETED_ROOT_RELATIVE,
        "b_source_export": canonical_mirror / B_SOURCE_EXPORT_RELATIVE,
        "canonical_002_root": canonical_mirror / CANONICAL_002_RELATIVE_PATH,
        "coverage_matrix": canonical_mirror / COVERAGE_MATRIX_RELATIVE,
        "approved_design_path": canonical_mirror / W2_DESIGN_PATH,
        "approved_design_sha": W2_DESIGN_SHA,
        "approved_plan_path": canonical_mirror / W2_PLAN_PATH,
        "approved_plan_sha": W2_PLAN_SHA,
        "network_authorization_path": auth_file,
        "network_authorization_sha": auth_sha,
    }


def test_w2_request_set_is_exact_and_outcome_blind(canonical_w2_inputs: Dict[str, Any]):
    authority = source.derive_w2_authority_inputs(**canonical_w2_inputs)
    request_set = source.derive_w2_request_set(authority)
    assert (len(authority.denominator_records), authority.distinct_parent_count) == (41, 27)
    assert (authority.window_defined_count, authority.window_parent_count) == (31, 21)
    assert authority.settlement_time_unproven_count == 10
    assert (len(request_set.logical_records), len(request_set.physical_records)) == (180, 180)
    assert (len(request_set.reuse_ids), len(request_set.fetch_ids)) == (9, 171)
    assert request_set.all_urls_sha256 == ALL_URLS_SHA256
    assert request_set.reuse_urls_sha256 == REUSE_URLS_SHA256
    assert request_set.fetch_urls_sha256 == FETCH_URLS_SHA256
    assert not hasattr(request_set, "prices")
    assert not hasattr(request_set, "ohlc")
    assert not hasattr(request_set, "basis")


def test_w2_temporal_or_url_mutation_fails_closed(
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    # Mutate matrix URL to evil host
    mirror_root = canonical_w2_inputs["project_root"]
    matrix_file = mirror_root / COVERAGE_MATRIX_RELATIVE
    original_bytes = matrix_file.read_bytes()
    try:
        mutate_mirror_file(matrix_file, original_bytes.replace(b"indexPriceKlines", b"evilHostKlines", 1))
        with pytest.raises(source.W2EvidenceSourceError, match="STOP=w2_request_set_mismatch"):
            source.derive_w2_authority_inputs(**canonical_w2_inputs)
    finally:
        mutate_mirror_file(matrix_file, original_bytes)


def test_w2_network_authorization_validation_fails_closed(
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    authority = source.derive_w2_authority_inputs(**canonical_w2_inputs)
    request_set = source.derive_w2_request_set(authority)

    # 1. Valid authorization passes
    auth_dict = source.validate_w2_network_authorization(
        authorization_path=canonical_w2_inputs["network_authorization_path"],
        authorization_sha256=canonical_w2_inputs["network_authorization_sha"],
        design_path=canonical_w2_inputs["approved_design_path"],
        design_sha256=canonical_w2_inputs["approved_design_sha"],
        plan_path=canonical_w2_inputs["approved_plan_path"],
        plan_sha256=canonical_w2_inputs["approved_plan_sha"],
        run_id="w2_test_run_001",
        request_set=request_set,
    )
    assert auth_dict["schema_version"] == "stage1_6f_w2_network_authorization_v1"

    # 2. Mutated permission flag (live_trading_allowed=True) fails closed
    bad_auth_path = tmp_path / "bad_auth.json"
    bad_flags = dict(source.W2_13_FALSE_FLAGS)
    bad_flags["live_trading_allowed"] = True
    create_test_network_authorization(
        bad_auth_path,
        run_id="w2_test_run_001",
        permission_flags=bad_flags,
    )
    with pytest.raises(source.W2EvidenceSourceError, match="STOP=w2_network_authorization_invalid"):
        source.validate_w2_network_authorization(
            authorization_path=bad_auth_path,
            authorization_sha256="wrong_sha",
            design_path=canonical_w2_inputs["approved_design_path"],
            design_sha256=canonical_w2_inputs["approved_design_sha"],
            plan_path=canonical_w2_inputs["approved_plan_path"],
            plan_sha256=canonical_w2_inputs["approved_plan_sha"],
            run_id="w2_test_run_001",
            request_set=request_set,
        )


@pytest.fixture
def canonical_w2_root(canonical_w2_inputs: Dict[str, Any], tmp_path: Path) -> CanonicalW2Root:
    return build_canonical_w2_root_fixture(tmp_path, canonical_w2_inputs)


def test_strict_reader_accepts_canonical_w2_gaps_root(canonical_w2_root: CanonicalW2Root):
    verified = source.load_verified_w2_evidence(**canonical_w2_root.authority_kwargs)
    assert verified.candidate_root_state == "collection_terminal_with_evidence_gaps"
    assert len(verified.denominator_records) == 41
    assert len(verified.logical_archive_records) == 180
    assert len(verified.physical_source_objects) == 180
    assert len(verified.metric_window_coverages) == 123


@pytest.mark.parametrize("mutation,stop", [
    ("extra_manifest_key", "w2_root_invalid:manifest_keys"),
    ("forged_url", "w2_root_invalid:physical_url"),
    ("http_bool", "w2_root_invalid:http_status_type"),
    ("wrong_member", "w2_root_invalid:zip_member_name"),
    ("header_only_csv", "w2_root_invalid:csv_invalid"),
    ("duplicate_open_time", "w2_root_invalid:hour_grid"),
    ("root_state_all_complete", "w2_root_invalid:candidate_root_state"),
])
def test_strict_reader_rejects_single_point_mutations(canonical_w2_root: CanonicalW2Root, mutation: str, stop: str):
    mutated = canonical_w2_root.single_point_mutation(mutation)
    with pytest.raises(source.W2EvidenceSourceError, match=stop):
        source.load_verified_w2_evidence(**mutated.authority_kwargs)


def test_w2_coverage_grid_truncation_and_boundaries():
    # AIA / PORT3 truncation: window_start truncated by t_pub
    G, C = source.compute_w2_grid_points(1726563600000, 1726646400000)
    assert len(G) == 23
    assert len(C) == 23

    # Empty complete-bar grid: e.g. 30 min window (1800000 ms)
    G_short, C_short = source.compute_w2_grid_points(1726560000000, 1726561800000)
    assert G_short == (1726560000000,)
    assert C_short == ()

    # Exact boundary inclusion/exclusion: a <= t < b
    G_exact, C_exact = source.compute_w2_grid_points(3600000, 7200000)
    assert G_exact == (3600000,)
    assert C_exact == (3600000,)

    # UTC crossing: across midnight
    G_cross, C_cross = source.compute_w2_grid_points(82800000, 93600000)
    assert G_cross == (82800000, 86400000, 90000000)
    assert C_cross == (82800000, 86400000, 90000000)


def test_w2_coverage_temporal_unproven_and_physical_failure(canonical_w2_root: CanonicalW2Root):
    coverages = canonical_w2_root.manifest["metric_window_coverages"]
    assert len(coverages) == 123

    unproven_covs = [c for c in coverages if c["raw_open_grid_status"] == "temporal_unproven"]
    assert len(unproven_covs) == 30
    for c in unproven_covs:
        assert c["complete_bar_status"] == "temporal_unproven"
        assert c["expected_open_count"] is None
        assert c["observed_open_count"] is None
        assert c["missing_open_count"] is None
        assert c["expected_complete_bar_count"] is None
        assert c["observed_complete_bar_count"] is None
        assert c["missing_complete_bar_count"] is None
        assert c["zero_index_close_count"] is None
        assert c["logical_archive_record_ids"] == []

    not_proven_covs = [c for c in coverages if c["raw_open_grid_status"] == "not_proven"]
    assert len(not_proven_covs) == 87
    for c in not_proven_covs:
        assert c["complete_bar_status"] == "not_proven"
        assert isinstance(c["expected_open_count"], int)
        assert c["observed_open_count"] is None
        assert c["missing_open_count"] is None
        assert isinstance(c["expected_complete_bar_count"], int)
        assert c["observed_complete_bar_count"] is None
        assert c["missing_complete_bar_count"] is None
        assert c["zero_index_close_count"] is None
        assert len(c["logical_archive_record_ids"]) > 0

    observed_covs = [c for c in coverages if c["raw_open_grid_status"] == "observed"]
    assert len(observed_covs) == 6
    for c in observed_covs:
        assert c["complete_bar_status"] == "no_complete_bars"
        assert isinstance(c["expected_open_count"], int)
        assert isinstance(c["observed_open_count"], int)
        assert isinstance(c["missing_open_count"], int)
        assert isinstance(c["expected_complete_bar_count"], int)
        assert isinstance(c["observed_complete_bar_count"], int)
        assert isinstance(c["missing_complete_bar_count"], int)
        if c["metric"] == "index_price_1h":
            assert isinstance(c["zero_index_close_count"], int)
        else:
            assert c["zero_index_close_count"] is None
        assert len(c["logical_archive_record_ids"]) > 0


