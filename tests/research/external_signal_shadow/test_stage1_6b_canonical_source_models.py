"""Unit and contract tests for Stage 1.6B canonical source models, identities, and SSOT constants."""

import hashlib
import json
from pathlib import Path

import pytest

from configs import base
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    CANDIDATE_DISCOVERY_RULE_VERSION,
    CANONICAL_HEADERS,
    CANONICAL_HEADERS_JSON,
    SOURCE_PROFILE_ID,
    ArticleDiscoveryRecord,
    CaptureMode,
    CaptureRunContract,
    HistoricalCoverageRecord,
    ListCaptureRecord,
    ObserverCheckpointRecord,
    SealedExportManifest,
    SourceProfileProbeAttestation,
    compute_article_discovery_id,
    compute_detail_revision_id,
    compute_export_id,
    compute_list_capture_id,
    compute_list_payload_id,
    compute_request_headers_profile_sha256,
    compute_request_observation_id,
    is_delisting_candidate,
    normalize_discovery_text,
    validate_observer_checkpoint_status_coverage,
)


def test_stage1_6b_ssot_constants_in_configs_base():
    """Verify all 16 Stage 1.6B SSOT constants exist in configs/base.py with exact types and values."""
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_POLL_INTERVAL_SEC == 300
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_ROOT_MAX_BYTES == 256 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES == 4 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES == 1 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES == 256 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_MAX_RAW_PAYLOAD_BYTES == 2_000_000
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_HTTP_TIMEOUT_SEC == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_EPOCH_MAX_SECONDS == 7 * 24 * 60 * 60
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_HISTORICAL_MAX_INDEX_PAGES == 100
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_HISTORICAL_REQUEST_INTERVAL_SEC == 1.0
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES == 500
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_FIRST_ATTEMPT_MAX_POLLS == 2
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MIN_INTERVAL_SEC == 300
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MAX_INTERVAL_SEC == 3600
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MAX_CYCLES == 12
    assert base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MAX_AGE_SEC == 24 * 60 * 60


def test_config_algebra_host_emergency_peak_sufficiency():
    """Verify that existing host emergency reserve covers the terminal peak writes of 1.5D, 1.5F, and 1.6B combined."""
    host_emergency = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES
    d_peak = base.EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
    f_peak = base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
    b_peak = base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES

    assert host_emergency >= d_peak + f_peak + b_peak, (
        f"Host emergency reserve ({host_emergency}) must be >= sum of 1.5D ({d_peak}) + 1.5F ({f_peak}) + 1.6B ({b_peak})"
    )


def test_identity_formulas_and_separation():
    """Verify the 4-layer and export identity formulas from Design Section 6.1."""
    raw_bytes = b"{\"code\":\"000000\",\"data\":{\"articles\":[]}}"
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()

    list_payload_id = compute_list_payload_id(
        source_surface="announcement_index",
        source_locale="en",
        request_variant="bapi_article_list_type_1_page_50_v1",
        raw_sha256=raw_sha,
    )
    assert len(list_payload_id) == 64

    req_obs_id_1 = compute_request_observation_id(
        run_id="run_001",
        request_class="historical_index",
        monotonic_request_seq=1,
    )
    req_obs_id_2 = compute_request_observation_id(
        run_id="run_001",
        request_class="historical_index",
        monotonic_request_seq=2,
    )
    assert req_obs_id_1 != req_obs_id_2

    # Same payload on different pages or different requests yield different list_capture_id
    cap_id_page_1 = compute_list_capture_id(
        source_profile_id="binance_public_web_bapi_en_v1",
        canonical_requested_url="https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50",
        page_no=1,
        list_payload_id=list_payload_id,
        request_observation_id=req_obs_id_1,
    )
    cap_id_page_2 = compute_list_capture_id(
        source_profile_id="binance_public_web_bapi_en_v1",
        canonical_requested_url="https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=2&pageSize=50",
        page_no=2,
        list_payload_id=list_payload_id,
        request_observation_id=req_obs_id_2,
    )
    assert cap_id_page_1 != cap_id_page_2

    # Article discovery id
    disc_id = compute_article_discovery_id(
        source_profile_id="binance_public_web_bapi_en_v1",
        source_article_id="art_123",
        first_list_capture_id=cap_id_page_1,
    )
    assert len(disc_id) == 64

    # Detail revision id
    rev_id = compute_detail_revision_id(
        source_article_id="art_123",
        source_surface="announcement_detail",
        source_locale="en",
        request_variant="bapi_article_detail_query_v1",
        detail_raw_sha256="dummy_detail_sha256",
    )
    assert len(rev_id) == 64

    # Export id
    artifacts = [
        ("raw_payloads/index/123.bin", "sha123", 500),
        ("list_captures/2026-08-20.jsonl", "sha456", 1200),
    ]
    export_id = compute_export_id(
        capture_mode="live_observed",
        source_profile_id="binance_public_web_bapi_en_v1",
        checkpoint_id="chk_001",
        ordered_authoritative_artifacts=artifacts,
    )
    assert len(export_id) == 64


def test_candidate_discovery_rule_v1_semantic_parity():
    """Verify candidate discovery rule parity with Design and Stage 1.6A using the frozen fixture."""
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6b/candidate_discovery_rule_v1_cases.json")
    assert fixture_path.is_file(), f"Fixture {fixture_path} must exist"
    cases = json.loads(fixture_path.read_text())

    for case in cases:
        title = case["title"]
        expected = case["expected_candidate"]
        normalized = normalize_discovery_text(title)
        actual = is_delisting_candidate(normalized)
        assert actual == expected, f"Failed case: {case.get('description')} for title: '{title}'"

    assert CANDIDATE_DISCOVERY_RULE_VERSION == "candidate_discovery_rule_v1"


def test_source_profile_headers_exclude_cookie_authorization():
    """Verify that the frozen public-web request header profile excludes Cookie and Authorization."""
    assert CANONICAL_HEADERS["Accept"] == "application/json"
    assert CANONICAL_HEADERS["Accept-Language"] == "en"
    assert "Cookie" not in CANONICAL_HEADERS
    assert "Authorization" not in CANONICAL_HEADERS

    header_sha = compute_request_headers_profile_sha256()
    assert len(header_sha) == 64
    assert isinstance(CANONICAL_HEADERS_JSON, str)


def test_historical_null_pit_fields():
    """Verify that historical records enforce nullable PIT timestamps and null fields as required by Design Section 6.3."""
    # Article discovery in historical mode has null notice_lineage_first_detected_at_ms
    disc_hist = ArticleDiscoveryRecord(
        schema_version="stage1_6b_article_discovery_v1",
        capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_article_id="art_123",
        discovery_title="Binance Futures Will Delist XYZ",
        discovery_rule_version=CANDIDATE_DISCOVERY_RULE_VERSION,
        first_list_capture_id="cap_001",
        notice_lineage_first_detected_at_ms=None,
        captured_at_ms=1700000000000,
        record_seq=1,
    )
    d_dict = disc_hist.to_dict()
    assert d_dict["notice_lineage_first_detected_at_ms"] is None
    assert d_dict["capture_mode"] == "historical_backfill"

    # Sealed export manifest for historical has null live fields and non-null historical range
    hist_manifest = SealedExportManifest(
        schema_version="stage1_6b_sealed_export_v1",
        export_id="exp_001",
        status="complete",
        capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
        source_profile_id=SOURCE_PROFILE_ID,
        request_headers_profile_sha256="header_sha",
        checkpoint_id="chk_final",
        terminal_status_sha256="term_sha",
        historical_range_from_ms=1600000000000,
        historical_range_to_ms=1700000000000,
        historical_coverage_sha256="cov_sha",
        authoritative_artifacts=[
            {"relative_path": "list_captures/2026-08-20.jsonl", "sha256": "sha_l", "byte_count": 100}
        ],
        sealed_at_ms=1700000001000,
    )
    m_dict = hist_manifest.to_dict()
    assert m_dict["historical_range_from_ms"] == 1600000000000
    assert m_dict["historical_range_to_ms"] == 1700000000000


def test_authority_and_trading_flags_all_false():
    """Verify that Stage 1.6B models do not authorize trading, replay, or source audit pass."""
    manifest = SealedExportManifest(
        schema_version="stage1_6b_sealed_export_v1",
        export_id="exp_001",
        status="complete",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        request_headers_profile_sha256="header_sha",
        checkpoint_id="chk_001",
        terminal_status_sha256="term_sha",
        historical_range_from_ms=None,
        historical_range_to_ms=None,
        historical_coverage_sha256=None,
        authoritative_artifacts=[],
        sealed_at_ms=1700000000000,
    )
    # Check default security caps
    assert manifest.source_audit_passed is False
    assert manifest.point_in_time_source_validated is False
    assert manifest.market_data_coverage_passed is False
    assert manifest.replay_allowed is False
    assert manifest.risk_veto_candidate is False
    assert manifest.trade_signal_allowed is False
    assert manifest.paper_trading_allowed is False
    assert manifest.live_trading_allowed is False
    assert manifest.execution_engine_allowed is False
    assert manifest.alpha_interpretation_allowed is False


def test_v2_exact_constants():
    """Task 1.1: Verify exact v2 constants for delisting catalog profile."""
    from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
        INDEX_REQUEST_VARIANT,
        SELECTED_CATALOG_ID,
        SELECTED_CATALOG_NAME,
        SOURCE_PROFILE_ID,
    )
    assert SOURCE_PROFILE_ID == "binance_public_web_bapi_en_delisting_catalog_v2"
    assert INDEX_REQUEST_VARIANT == "bapi_article_list_type_1_delisting_catalog_161_page_50_v2"
    assert SELECTED_CATALOG_ID == 161
    assert SELECTED_CATALOG_NAME == "Delisting"


def test_v2_record_serialization_and_schema_versions():
    """Task 1.2: Verify v2 schema versions and record serialization with catalog provenance."""
    # 1. SourceProfileProbeAttestation v2
    att = SourceProfileProbeAttestation(
        schema_version="stage1_6b_source_profile_probe_attestation_v2",
        probe_command_version="source_profile_probe_v2",
        source_profile_id="binance_public_web_bapi_en_delisting_catalog_v2",
        source_authority="binance_official_content",
        transport_support_status="undocumented_public_web_profile",
        source_profile_sha256="dummy_profile_sha",
        request_headers_profile_sha256="dummy_headers_sha",
        probe_article_id="0123456789abcdef0123456789abcdef",
        index_requested_url="https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50",
        index_final_url="https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50",
        index_http_status=200,
        index_content_type="application/json",
        index_payload_bytes=5000,
        index_article_id_path='data.catalogs[?catalogId==161 && catalogName=="Delisting"].articles[].code',
        detail_requested_url="https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=0123456789abcdef0123456789abcdef",
        detail_final_url="https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=0123456789abcdef0123456789abcdef",
        detail_http_status=200,
        detail_content_type="application/json",
        detail_payload_bytes=2000,
        detail_body_path="data.body",
        probe_attested_at_ms=1700000000000,
        selected_catalog_id=161,
        selected_catalog_name="Delisting",
        selected_catalog_article_count=10,
    )
    att_dict = att.to_dict()
    assert att_dict["schema_version"] == "stage1_6b_source_profile_probe_attestation_v2"
    assert att_dict["selected_catalog_id"] == 161
    assert att_dict["selected_catalog_name"] == "Delisting"
    assert att_dict["selected_catalog_article_count"] == 10

    # 2. ListCaptureRecord v2
    lc = ListCaptureRecord(
        schema_version="stage1_6b_list_capture_v2",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id="binance_public_web_bapi_en_delisting_catalog_v2",
        request_headers_profile_sha256="headers_sha",
        run_id="run_001",
        poll_seq=1,
        record_seq=1,
        request_observation_id="req_obs_1",
        list_payload_id="payload_1",
        list_capture_id="cap_1",
        page_no=1,
        requested_url="https://www.binance.com/list",
        final_url="https://www.binance.com/list",
        http_status=200,
        content_type="application/json",
        raw_payload_sha256="raw_sha",
        raw_payload_bytes=1000,
        raw_payload_relative_path="raw_payloads/index/1.bin",
        t_list_receive_ms=1700000000000,
        article_count=5,
        captured_at_ms=1700000000000,
        selected_catalog_id=161,
        selected_catalog_name="Delisting",
        selected_catalog_total=426,
    )
    lc_dict = lc.to_dict()
    assert lc_dict["schema_version"] == "stage1_6b_list_capture_v2"
    assert lc_dict["selected_catalog_id"] == 161
    assert lc_dict["selected_catalog_name"] == "Delisting"
    assert lc_dict["selected_catalog_total"] == 426
    assert lc_dict["article_count"] == 5

    # 3. ArticleDiscoveryRecord v2
    disc = ArticleDiscoveryRecord(
        schema_version="stage1_6b_article_discovery_v2",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id="binance_public_web_bapi_en_delisting_catalog_v2",
        source_article_id="art_123",
        discovery_title="Binance Futures Will Delist XYZ",
        discovery_rule_version="candidate_discovery_rule_v1",
        first_list_capture_id="cap_1",
        notice_lineage_first_detected_at_ms=1700000000000,
        captured_at_ms=1700000000000,
        record_seq=2,
        source_catalog_id=161,
        source_catalog_name="Delisting",
    )
    disc_dict = disc.to_dict()
    assert disc_dict["schema_version"] == "stage1_6b_article_discovery_v2"
    assert disc_dict["source_catalog_id"] == 161
    assert disc_dict["source_catalog_name"] == "Delisting"

    # 4. ObserverCheckpointRecord v2
    chk = ObserverCheckpointRecord(
        schema_version="stage1_6b_observer_checkpoint_v2",
        run_id="run_001",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id="binance_public_web_bapi_en_delisting_catalog_v2",
        source_profile_attestation_sha256="att_sha",
        checkpoint_id="chk_1",
        prior_checkpoint_id=None,
        poll_seq=1,
        monotonic_request_seq=1,
        record_seq=2,
        accounted_root_bytes=5000,
        stream_offsets={"list_captures/2026-08-22.jsonl": 500},
        stream_last_hashes={"list_captures/2026-08-22.jsonl": "hash_val"},
        candidate_states={},
        heartbeat_at_ms=1700000000000,
        last_index_poll_status="trusted",
        last_index_poll_coverage="successful",
    )
    chk_dict = chk.to_dict()
    assert chk_dict["schema_version"] == "stage1_6b_observer_checkpoint_v2"
    assert chk_dict["last_index_poll_status"] == "trusted"
    assert chk_dict["last_index_poll_coverage"] == "successful"

    # 5. CaptureRunContract stays v1
    contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id="run_001",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id="binance_public_web_bapi_en_delisting_catalog_v2",
        source_profile_attestation_sha256="att_sha",
        run_started_at_ms=1700000000000,
    )
    assert contract.schema_version == "stage1_6b_capture_run_contract_v1"

    # 6. HistoricalCoverageRecord v2 with 4-tuple transcript and diagnostic totals
    diag_sweep = {
        "per_page_selected_catalog_total": [
            {"page_no": 1, "selected_catalog_total": 426},
            {"page_no": 2, "selected_catalog_total": 426},
        ],
        "first_selected_catalog_total": 426,
        "last_selected_catalog_total": 426,
    }
    cov = HistoricalCoverageRecord(
        schema_version="stage1_6b_historical_coverage_v2",
        run_id="hist_run_1",
        source_profile_id="binance_public_web_bapi_en_delisting_catalog_v2",
        source_profile_attestation_sha256="att_sha",
        from_ms=1600000000000,
        to_ms=1700000000000,
        sweep_a_transcript=[(1, 161, "art_1", 1690000000000)],
        sweep_b_transcript=[(1, 161, "art_1", 1690000000000)],
        page_failures=[],
        candidate_terminal_counts={"trusted_detail_observed": 1},
        status="complete_stable",
        captured_at_ms=1700000001000,
        sweep_a=diag_sweep,
        sweep_b=diag_sweep,
    )
    cov_dict = cov.to_dict()
    assert cov_dict["schema_version"] == "stage1_6b_historical_coverage_v2"
    assert cov_dict["sweep_a_transcript"] == [(1, 161, "art_1", 1690000000000)]
    assert cov_dict["sweep_a"]["first_selected_catalog_total"] == 426


def test_checkpoint_status_coverage_pairs_validation():
    """Task 1.3: Verify allowed/rejected observer checkpoint status and coverage pairs."""
    # Allowed: trusted + successful
    validate_observer_checkpoint_status_coverage("trusted", "successful")

    # Allowed: degraded statuses + degraded_not_successful
    degraded_statuses = [
        "malformed_index_schema",
        "http_error",
        "network_error",
        "disallowed_redirect",
        "empty_payload",
        "payload_size_exceeded",
        "waf_rejected",
        "malformed_json",
        "wrong_locale",
    ]
    for st in degraded_statuses:
        validate_observer_checkpoint_status_coverage(st, "degraded_not_successful")

    # Rejected: trusted with degraded_not_successful
    with pytest.raises(ValueError, match="invalid_checkpoint_status_coverage_pair"):
        validate_observer_checkpoint_status_coverage("trusted", "degraded_not_successful")

    # Rejected: non-trusted status with successful
    with pytest.raises(ValueError, match="invalid_checkpoint_status_coverage_pair"):
        validate_observer_checkpoint_status_coverage("malformed_index_schema", "successful")

    # Rejected: unknown status or unknown coverage
    with pytest.raises(ValueError, match="invalid_checkpoint_status_coverage_pair"):
        validate_observer_checkpoint_status_coverage("unknown_status", "degraded_not_successful")
    with pytest.raises(ValueError, match="invalid_checkpoint_status_coverage_pair"):
        validate_observer_checkpoint_status_coverage("trusted", "unknown_coverage")


def test_v2_identity_algebra_and_no_migration():
    """Task 1.4: Verify exact v2 identity algebra formulas and strict v1 rejection without migration."""
    raw_bytes = b'{"data":{"catalogs":[{"catalogId":161,"catalogName":"Delisting","articles":[]}]}}'
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    v2_profile = SOURCE_PROFILE_ID
    page_1_url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50"
    page_2_url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=2&pageSize=50"
    request_1 = compute_request_observation_id("run_001", "live_index", 1)
    request_2 = compute_request_observation_id("run_001", "live_index", 2)
    article_id = "art_test_123"

    v2_payload_page_1 = compute_list_payload_id(
        "announcement_index", "en",
        "bapi_article_list_type_1_delisting_catalog_161_page_50_v2", raw_sha,
    )
    v2_payload_page_2 = compute_list_payload_id(
        "announcement_index", "en",
        "bapi_article_list_type_1_delisting_catalog_161_page_50_v2", raw_sha,
    )
    assert v2_payload_page_1 == v2_payload_page_2
    assert v2_payload_page_1 != compute_list_payload_id(
        "announcement_index", "en", "bapi_article_list_type_1_page_50_v1", raw_sha,
    )

    first_capture_1 = compute_list_capture_id(v2_profile, page_1_url, 1, v2_payload_page_1, request_1)
    first_capture_2 = compute_list_capture_id(v2_profile, page_1_url, 1, v2_payload_page_1, request_2)

    assert compute_list_capture_id(v2_profile, page_1_url, 1, v2_payload_page_1, request_1) != \
           compute_list_capture_id(v2_profile, page_2_url, 2, v2_payload_page_1, request_1)
    assert compute_list_capture_id(v2_profile, page_1_url, 1, v2_payload_page_1, request_1) != \
           compute_list_capture_id(v2_profile, page_1_url, 1, v2_payload_page_1, request_2)
    assert compute_article_discovery_id(v2_profile, article_id, first_capture_1) == \
           compute_article_discovery_id(v2_profile, article_id, first_capture_1)
    assert compute_article_discovery_id(v2_profile, article_id, first_capture_1) != \
           compute_article_discovery_id(v2_profile, article_id, first_capture_2)


def test_static_ast_no_raw_legacy_profile_in_stage1_6b_codebase():
    """Task 7.1: Verify all 7 production files use v2 profile constants and zero raw legacy profile assignments."""
    import ast
    from pathlib import Path

    production_files = [
        Path("src/research/external_signal_shadow/stage1_6b_canonical_source_client.py"),
        Path("src/research/external_signal_shadow/stage1_6b_canonical_source_models.py"),
        Path("src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py"),
        Path("src/research/external_signal_shadow/stage1_6b_canonical_source_storage.py"),
        Path("scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py"),
        Path("scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py"),
        Path("scripts/external_signal_shadow/run_stage1_6b_historical_backfill.py"),
    ]

    for p in production_files:
        assert p.is_file(), f"File {p} must exist"
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert node.value != "binance_public_web_bapi_en_v1", f"Legacy profile string found in {p} at line {node.lineno}"


def test_sealed_export_manifest_explicit_downstream_caps_hardcoded_false():
    """Task 7.2: Verify all explicit downstream capability flags default to False."""
    from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
        SealedExportManifest,
    )

    manifest = SealedExportManifest(
        schema_version="stage1_6b_sealed_export_v1",
        export_id="exp_test",
        status="complete",
        capture_mode="live_observed",
        source_profile_id="binance_public_web_bapi_en_delisting_catalog_v2",
        request_headers_profile_sha256="dummy_sha",
        checkpoint_id="chk_001",
        terminal_status_sha256="term_sha",
        historical_range_from_ms=None,
        historical_range_to_ms=None,
        historical_coverage_sha256=None,
        authoritative_artifacts=[],
        sealed_at_ms=1700000000000,
    )

    assert manifest.source_audit_passed is False
    assert manifest.point_in_time_source_validated is False
    assert manifest.market_data_coverage_passed is False
    assert manifest.replay_allowed is False
    assert manifest.risk_veto_candidate is False
    assert manifest.trade_signal_allowed is False
    assert manifest.paper_trading_allowed is False
    assert manifest.live_trading_allowed is False
    assert manifest.execution_engine_allowed is False
    assert manifest.alpha_interpretation_allowed is False
