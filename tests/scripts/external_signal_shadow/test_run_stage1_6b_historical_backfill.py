"""Unit and integration tests for historical backfill runner."""

import hashlib
import io
import json

import pytest

from scripts.external_signal_shadow.run_stage1_6b_historical_backfill import (
    run_historical_backfill,
)
from scripts.external_signal_shadow.run_stage1_6b_source_profile_probe import (
    compute_source_profile_sha256,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    SOURCE_PROFILE_ID,
    SourceProfileProbeAttestation,
    canonical_json,
    compute_request_headers_profile_sha256,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import (
    load_sealed_export,
)


class MockHTTPResponse:
    def __init__(self, body_bytes: bytes, status: int = 200, headers: dict = None, url: str = "https://www.binance.com"):
        self._body = io.BytesIO(body_bytes)
        self.status = status
        self.code = status
        self.headers = headers or {"Content-Type": "application/json"}
        self.url = url

    def read(self, amt=None):
        return self._body.read(amt)

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def geturl(self):
        return self.url

    def close(self):
        pass


def setup_valid_attestation(tmp_path, attested_at_ms=1000):
    p_sha = compute_source_profile_sha256()
    att_dir = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "source_profile_attestations" / p_sha
    att_dir.mkdir(parents=True, exist_ok=True)
    att_path = att_dir / "source_profile_probe_attestation.json"

    att = SourceProfileProbeAttestation(
        schema_version="stage1_6b_source_profile_probe_attestation_v2",
        probe_command_version="source_profile_probe_v2",
        source_profile_id=SOURCE_PROFILE_ID,
        source_authority="binance_official_content",
        transport_support_status="undocumented_public_web_profile",
        source_profile_sha256=p_sha,
        request_headers_profile_sha256=compute_request_headers_profile_sha256(),
        probe_article_id="a" * 32,
        index_requested_url="https://www.binance.com/index",
        index_final_url="https://www.binance.com/index",
        index_http_status=200,
        index_content_type="application/json",
        index_payload_bytes=100,
        index_article_id_path='data.catalogs[?catalogId==161 && catalogName=="Delisting"].articles[].code',
        detail_requested_url="https://www.binance.com/detail",
        detail_final_url="https://www.binance.com/detail",
        detail_http_status=200,
        detail_content_type="application/json",
        detail_payload_bytes=100,
        detail_body_path="data.body",
        probe_attested_at_ms=attested_at_ms,
        selected_catalog_id=161,
        selected_catalog_name="Delisting",
        selected_catalog_article_count=1,
    )
    att_path.write_text(json.dumps(att.to_dict()))
    return att_path


def test_historical_backfill_rejects_v1_probe_attestation_pre_network(tmp_path):
    """Task 3.4: Historical runner rejects v1 probe attestation before client/opener construction."""
    p_sha = compute_source_profile_sha256()
    att_dir = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "source_profile_attestations" / p_sha
    att_dir.mkdir(parents=True, exist_ok=True)
    att_path = att_dir / "source_profile_probe_attestation.json"

    # Syntactically valid v1 attestation
    att_v1 = {
        "schema_version": "stage1_6b_source_profile_probe_attestation_v1",
        "probe_command_version": "source_profile_probe_v1",
        "source_profile_id": "binance_public_web_bapi_en_v1",
        "source_authority": "binance_official_content",
        "transport_support_status": "undocumented_public_web_profile",
        "source_profile_sha256": "dummy_sha",
        "request_headers_profile_sha256": compute_request_headers_profile_sha256(),
        "probe_article_id": "a" * 32,
        "index_requested_url": "https://www.binance.com/index",
        "index_final_url": "https://www.binance.com/index",
        "index_http_status": 200,
        "index_content_type": "application/json",
        "index_payload_bytes": 100,
        "index_article_id_path": "data.articles[].code",
        "detail_requested_url": "https://www.binance.com/detail",
        "detail_final_url": "https://www.binance.com/detail",
        "detail_http_status": 200,
        "detail_content_type": "application/json",
        "detail_payload_bytes": 100,
        "detail_body_path": "data.body",
        "probe_attested_at_ms": 1000,
    }
    att_path.write_text(json.dumps(att_v1))

    opener_called = []

    def mock_opener(req, timeout=10.0):
        opener_called.append(req)
        return MockHTTPResponse(b"{}")

    with pytest.raises(ValueError, match="attestation"):
        run_historical_backfill(
            from_ms=1600000000000,
            to_ms=1610000000000,
            attestation_path=att_path,
            live_public_readonly=True,
            project_root=tmp_path,
            opener=mock_opener,
        )

    assert len(opener_called) == 0
    hist_root = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "historical_backfill"
    assert not hist_root.exists()


def test_historical_backfill_requires_live_public_readonly(tmp_path):
    """Verify historical backfill refuses to execute without explicit live_public_readonly flag."""
    att_path = setup_valid_attestation(tmp_path)
    with pytest.raises(ValueError, match="live_public_readonly_required"):
        run_historical_backfill(
            from_ms=1000,
            to_ms=2000,
            attestation_path=att_path,
            live_public_readonly=False,
            project_root=tmp_path,
        )


def test_historical_backfill_range_validation(tmp_path):
    """Verify 730-day maximum range limit and from_ms < to_ms."""
    att_path = setup_valid_attestation(tmp_path)

    # from_ms >= to_ms
    with pytest.raises(ValueError, match="invalid_time_range"):
        run_historical_backfill(
            from_ms=2000,
            to_ms=1000,
            attestation_path=att_path,
            live_public_readonly=True,
            project_root=tmp_path,
        )

    # > 730 days
    ms_731_days = 731 * 24 * 3600 * 1000
    with pytest.raises(ValueError, match="range_exceeds_730_days"):
        run_historical_backfill(
            from_ms=0,
            to_ms=ms_731_days,
            attestation_path=att_path,
            live_public_readonly=True,
            project_root=tmp_path,
        )


def make_hist_index_payload(articles, catalog_total=426):
    return json.dumps({
        "code": "000000",
        "data": {
            "catalogs": [
                {
                    "catalogId": 161,
                    "catalogName": "Delisting",
                    "total": max(catalog_total, len(articles)),
                    "articles": articles,
                }
            ]
        }
    }).encode("utf-8")


def test_historical_backfill_sweep_parity_and_completion(tmp_path):
    """Verify two matching sequential sweeps cover range, fetch detail, and write complete status."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)

    art_code = "c" * 32
    index_payload = make_hist_index_payload([
        {
            "code": art_code,
            "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
            "releaseDate": 1590000000000  # <= from_ms (1600000000000) so single page covers from_ms
        }
    ], catalog_total=426)

    detail_payload = json.dumps({
        "code": "000000",
        "data": {
            "code": art_code,
            "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
            "body": "<p>Content</p>",
            "releaseDate": 1590000000000
        }
    }).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        elif "article/detail/query" in url:
            return MockHTTPResponse(detail_payload, url=url)
        raise ValueError(f"Unexpected url {url}")

    run_root = run_historical_backfill(
        from_ms=1600000000000,
        to_ms=1610000000000,
        attestation_path=att_path,
        live_public_readonly=True,
        project_root=tmp_path,
        opener=mock_opener,
        run_id="run_hist_success",
    )

    assert run_root.is_dir()
    term_file = run_root / "terminal_status.json"
    assert term_file.is_file()
    term_data = json.loads(term_file.read_text())
    assert term_data["status"] == "complete"
    assert term_data["terminal_reason"] == "historical_backfill_complete"

    cov_file = run_root / "historical_coverage.json"
    assert cov_file.is_file()
    cov_data = json.loads(cov_file.read_text())
    assert cov_data["schema_version"] == "stage1_6b_historical_coverage_v2"
    assert cov_data["status"] == "complete"
    assert cov_data["selected_catalog_id"] == 161
    assert cov_data["selected_catalog_name"] == "Delisting"
    assert cov_data["selected_catalog_total_historical_max"] == 426
    assert cov_data["selected_catalog_total_sweep_a_final"] == 426
    assert cov_data["selected_catalog_total_sweep_b_final"] == 426
    assert len(cov_data["sweep_a_transcript"]) == 1
    # 4-tuple check: (page_no, catalog_id, code, releaseDate)
    assert cov_data["sweep_a_transcript"][0] == [1, 161, art_code, 1590000000000]
    assert cov_data["sweep_a_transcript"] == cov_data["sweep_b_transcript"]

    manifest_path = run_root / "request_manifest" / "historical.jsonl"
    manifest_rows = [json.loads(line) for line in manifest_path.read_text().splitlines()]
    assert len(manifest_rows) == 2
    assert [row["request_class"] for row in manifest_rows] == ["historical_index", "historical_index"]
    assert [row["monotonic_request_seq"] for row in manifest_rows] == [1, 2]
    assert len({row["request_observation_id"] for row in manifest_rows}) == 2
    checkpoint = json.loads((run_root / "observer_checkpoint.json").read_text())
    assert checkpoint["stream_offsets"]["request_manifest/historical.jsonl"] == manifest_path.stat().st_size
    assert checkpoint["stream_last_hashes"]["request_manifest/historical.jsonl"] == hashlib.sha256(
        canonical_json(manifest_rows[-1]).encode("utf-8")
    ).hexdigest()

    exports = list((run_root / "sealed_exports").glob("*/sealed_export_manifest.json"))
    assert len(exports) == 1
    loaded = load_sealed_export(exports[0].parent)
    assert loaded["capture_mode"] == "historical_backfill"
    assert loaded["historical_coverage_sha256"] is not None

    exported_coverage = exports[0].parent / "historical_coverage.json"
    original_coverage = exported_coverage.read_bytes()
    original_manifest = exports[0].read_bytes()
    wrong_profile_coverage = json.loads(original_coverage)
    wrong_profile_coverage["source_profile_id"] = "binance_public_web_bapi_en_v1"
    exported_coverage.write_text(json.dumps(wrong_profile_coverage), encoding="utf-8")
    wrong_profile_manifest = json.loads(original_manifest)
    coverage_sha = hashlib.sha256(exported_coverage.read_bytes()).hexdigest()
    wrong_profile_manifest["historical_coverage_sha256"] = coverage_sha
    for artifact in wrong_profile_manifest["authoritative_artifacts"]:
        if artifact["relative_path"] == "historical_coverage.json":
            artifact["sha256"] = coverage_sha
            artifact["byte_count"] = exported_coverage.stat().st_size
    exports[0].write_text(json.dumps(wrong_profile_manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="historical_coverage_v2_provenance_invalid"):
        load_sealed_export(exports[0].parent)
    exported_coverage.write_bytes(original_coverage)
    exports[0].write_bytes(original_manifest)

    tampered_coverage = json.loads(exported_coverage.read_text())
    tampered_coverage["candidate_terminal_count"] = 0
    exported_coverage.write_text(json.dumps(tampered_coverage), encoding="utf-8")
    manifest_path = exports[0]
    tampered_manifest = json.loads(manifest_path.read_text())
    coverage_sha = hashlib.sha256(exported_coverage.read_bytes()).hexdigest()
    tampered_manifest["historical_coverage_sha256"] = coverage_sha
    for artifact in tampered_manifest["authoritative_artifacts"]:
        if artifact["relative_path"] == "historical_coverage.json":
            artifact["sha256"] = coverage_sha
            artifact["byte_count"] = exported_coverage.stat().st_size
    manifest_path.write_text(json.dumps(tampered_manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="historical_coverage_completion_predicate_failed"):
        load_sealed_export(exports[0].parent)


def test_historical_backfill_serializes_detail_cycles_and_request_interval(tmp_path):
    """Historical mode makes one request at a time and preserves the frozen 1-second interval."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)
    article_ids = ["d" * 32, "e" * 32]
    index_payload = make_hist_index_payload([
        {"code": article_ids[0], "title": "Binance Futures Will Delist A", "releaseDate": 1590000000000},
        {"code": article_ids[1], "title": "Binance Futures Will Delist B", "releaseDate": 1590000000000},
    ])
    detail_payload = json.dumps({"code": "000000", "data": {"code": article_ids[0], "title": "Delist A", "body": "trusted", "releaseDate": 1590000000000}}).encode("utf-8")
    request_order = []
    clock = [0.0]
    sleep_calls = []

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        request_order.append(url)
        return MockHTTPResponse(index_payload if "article/list/query" in url else detail_payload, url=url)

    def fake_sleep(seconds):
        sleep_calls.append(seconds)
        clock[0] += seconds

    run_historical_backfill(
        from_ms=1600000000000,
        to_ms=1610000000000,
        attestation_path=att_path,
        live_public_readonly=True,
        project_root=tmp_path,
        opener=mock_opener,
        run_id="run_hist_serial",
        sleeper=fake_sleep,
        monotonic_clock=lambda: clock[0],
    )

    assert ["article/list/query" in url for url in request_order] == [True, True, False, False]
    assert sleep_calls == [1.0, 1.0, 1.0]


def test_historical_backfill_rejects_candidate_capacity_before_detail_requests(tmp_path):
    """A frozen candidate set over the configured cap is terminal, not a bulk detail burst."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)
    index_payload = make_hist_index_payload([
        {
            "code": f"{index:032x}",
            "title": "Binance Futures Will Delist Capacity Test",
            "releaseDate": 1590000000000,
        }
        for index in range(501)
    ], catalog_total=600)
    detail_calls = []
    clock = [0.0]

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/detail/query" in url:
            detail_calls.append(url)
        return MockHTTPResponse(index_payload, url=url)

    def fake_sleep(seconds):
        clock[0] += seconds

    run_root = run_historical_backfill(
        from_ms=1600000000000,
        to_ms=1610000000000,
        attestation_path=att_path,
        live_public_readonly=True,
        project_root=tmp_path,
        opener=mock_opener,
        run_id="run_hist_capacity",
        sleeper=fake_sleep,
        monotonic_clock=lambda: clock[0],
    )

    assert detail_calls == []
    assert json.loads((run_root / "terminal_status.json").read_text())["status"] == "failure"
    assert not (run_root / "sealed_exports").exists()


def test_historical_backfill_schema_drift_rejection_and_no_sealed_export(tmp_path):
    """Task 5.2: Malformed selected catalog in historical sweep writes terminal failure and produces no export."""
    from scripts.external_signal_shadow.run_stage1_6b_historical_backfill import (
        HistoricalBackfillError,
    )
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)

    malformed_index = json.dumps({
        "code": "000000",
        "data": {
            "catalogs": [
                {"catalogId": 999, "catalogName": "WrongCatalog", "articles": [], "total": 0}
            ]
        },
    }).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        return MockHTTPResponse(malformed_index, url=req.get_full_url())

    with pytest.raises(HistoricalBackfillError, match="source_profile_schema_drift"):
        run_historical_backfill(
            from_ms=1600000000000,
            to_ms=1610000000000,
            attestation_path=att_path,
            live_public_readonly=True,
            project_root=tmp_path,
            opener=mock_opener,
            run_id="run_hist_drift",
        )

    run_root = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "historical_backfill" / "run_hist_drift"
    assert run_root.is_dir()
    term_data = json.loads((run_root / "terminal_status.json").read_text())
    assert term_data["status"] == "failure"
    assert term_data["terminal_reason"] == "source_profile_schema_drift"

    cov_data = json.loads((run_root / "historical_coverage.json").read_text())
    assert cov_data["status"] == "failure"
    assert cov_data["failure_reason"] == "source_profile_schema_drift"

    manifest_path = run_root / "request_manifest" / "historical.jsonl"
    manifest_rows = [json.loads(line) for line in manifest_path.read_text().splitlines()]
    assert len(manifest_rows) == 1
    assert manifest_rows[0]["request_class"] == "historical_index"
    assert manifest_rows[0]["validation_status"] == "malformed_index_schema"
    checkpoint = json.loads((run_root / "observer_checkpoint.json").read_text())
    assert checkpoint["stream_offsets"]["request_manifest/historical.jsonl"] == manifest_path.stat().st_size

    assert not (run_root / "sealed_exports").exists()


def test_historical_backfill_total_diagnostics_fluctuation_allowed(tmp_path):
    """Task 5.3: Total fluctuation across sweeps is recorded in diagnostics and does not fail completeness."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)
    art_code = "f" * 32
    detail_payload = json.dumps({"code": "000000", "data": {"code": art_code, "title": "Delist", "body": "ok", "releaseDate": 1590000000000}}).encode("utf-8")

    sweep_call = [0]

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            sweep_call[0] += 1
            # Sweep A has total=426, Sweep B has total=425
            total = 426 if sweep_call[0] == 1 else 425
            return MockHTTPResponse(
                make_hist_index_payload([{"code": art_code, "title": "Binance Futures Will Delist Token", "releaseDate": 1590000000000}], catalog_total=total),
                url=url,
            )
        return MockHTTPResponse(detail_payload, url=url)

    run_root = run_historical_backfill(
        from_ms=1600000000000,
        to_ms=1610000000000,
        attestation_path=att_path,
        live_public_readonly=True,
        project_root=tmp_path,
        opener=mock_opener,
        run_id="run_hist_diag",
    )

    cov_data = json.loads((run_root / "historical_coverage.json").read_text())
    assert cov_data["status"] == "complete"
    assert cov_data["selected_catalog_total_historical_max"] == 426
    assert cov_data["selected_catalog_total_sweep_a_final"] == 426
    assert cov_data["selected_catalog_total_sweep_b_final"] == 425
