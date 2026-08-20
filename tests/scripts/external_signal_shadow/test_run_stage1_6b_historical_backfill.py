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
        schema_version="stage1_6b_source_profile_probe_attestation_v1",
        probe_command_version="source_profile_probe_v1",
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
        index_article_id_path="data.articles[].code",
        detail_requested_url="https://www.binance.com/detail",
        detail_final_url="https://www.binance.com/detail",
        detail_http_status=200,
        detail_content_type="application/json",
        detail_payload_bytes=100,
        detail_body_path="data.body",
        probe_attested_at_ms=attested_at_ms,
    )
    att_path.write_text(json.dumps(att.to_dict()))
    return att_path


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


def test_historical_backfill_sweep_parity_and_completion(tmp_path):
    """Verify two matching sequential sweeps cover range, fetch detail, and write complete status."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)

    art_code = "c" * 32
    index_payload = json.dumps({
        "code": "000000",
        "data": {
            "articles": [
                {
                    "code": art_code,
                    "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
                    "releaseDate": 1500  # <= from_ms (2000) so single page covers from_ms
                }
            ]
        }
    }).encode("utf-8")

    detail_payload = json.dumps({
        "code": "000000",
        "data": {
            "code": art_code,
            "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
            "body": "<p>Content</p>",
            "releaseDate": 1500
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
        from_ms=2000,
        to_ms=5000,
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
    assert cov_data["status"] == "complete"
    assert len(cov_data["sweep_a_transcript"]) == 1
    assert cov_data["sweep_a_transcript"] == cov_data["sweep_b_transcript"]

    exports = list((run_root / "sealed_exports").glob("*/sealed_export_manifest.json"))
    assert len(exports) == 1
    loaded = load_sealed_export(exports[0].parent)
    assert loaded["capture_mode"] == "historical_backfill"
    assert loaded["historical_coverage_sha256"] is not None

    exported_coverage = exports[0].parent / "historical_coverage.json"
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
    index_payload = json.dumps({
        "code": "000000",
        "data": {"articles": [
            {"code": article_ids[0], "title": "Binance Futures Will Delist A", "releaseDate": 1500},
            {"code": article_ids[1], "title": "Binance Futures Will Delist B", "releaseDate": 1500},
        ]},
    }).encode("utf-8")
    detail_payload = json.dumps({"code": "000000", "data": {"body": "trusted"}}).encode("utf-8")
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
        from_ms=2000,
        to_ms=5000,
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
    index_payload = json.dumps({
        "code": "000000",
        "data": {"articles": [
            {
                "code": f"{index:032x}",
                "title": "Binance Futures Will Delist Capacity Test",
                "releaseDate": 1500,
            }
            for index in range(501)
        ]},
    }).encode("utf-8")
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
        from_ms=2000,
        to_ms=5000,
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
