"""Unit and integration tests for source profile probe script."""

import io
import json
from pathlib import Path

import pytest

import scripts.external_signal_shadow.run_stage1_6b_source_profile_probe as probe_runner
from scripts.external_signal_shadow.run_stage1_6b_source_profile_probe import (
    run_source_profile_probe,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    SOURCE_PROFILE_ID,
    compute_request_headers_profile_sha256,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import (
    validate_probe_attestation_path,
    write_atomic_json,
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


def test_probe_requires_live_public_readonly(tmp_path):
    """Verify probe refuses to run and creates no output without explicit live_public_readonly flag."""
    with pytest.raises(ValueError, match="live_public_readonly_required"):
        run_source_profile_probe(
            probe_article_id="a" * 32,
            live_public_readonly=False,
            project_root=tmp_path,
        )

    # Assert no output was created under tmp_path
    att_dir = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "source_profile_attestations"
    assert not att_dir.exists()


def test_probe_validates_32_hex_article_id(tmp_path):
    """Verify probe rejects invalid or non-32-hex article ID."""
    with pytest.raises(ValueError, match="invalid_probe_article_id"):
        run_source_profile_probe(
            probe_article_id="invalid_short_id",
            live_public_readonly=True,
            project_root=tmp_path,
        )


def test_probe_execution_and_attestation_persistence(tmp_path):
    """Verify successful probe execution writes valid attestation with injected opener."""
    fix_dir = Path("tests/fixtures/external_signal_shadow/stage1_6b")
    index_json = fix_dir / "profile_probe_index_fixture.json"
    detail_json = fix_dir / "profile_probe_detail_fixture.json"
    assert index_json.is_file() and detail_json.is_file()

    index_bytes = index_json.read_bytes()
    detail_bytes = detail_json.read_bytes()

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_bytes, url=url)
        elif "article/detail/query" in url:
            return MockHTTPResponse(detail_bytes, url=url)
        raise ValueError(f"Unexpected url: {url}")

    article_id = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
    attestation_path = run_source_profile_probe(
        probe_article_id=article_id,
        live_public_readonly=True,
        project_root=tmp_path,
        opener=mock_opener,
    )

    # Validate returned path conforms to strict path confinement
    assert attestation_path.is_file()
    validated = validate_probe_attestation_path(attestation_path, project_root=tmp_path)
    assert validated == attestation_path.resolve()

    # Validate contents of attestation JSON
    data = json.loads(attestation_path.read_text())
    assert data["source_profile_id"] == SOURCE_PROFILE_ID
    assert data["request_headers_profile_sha256"] == compute_request_headers_profile_sha256()
    assert data["probe_article_id"] == article_id
    assert data["index_http_status"] == 200
    assert data["detail_http_status"] == 200
    assert data["probe_attested_at_ms"] > 0


def test_probe_persists_attestation_through_guarded_atomic_writer(tmp_path, monkeypatch):
    """Probe persistence must route through the Stage 1.6B guarded writer."""
    fix_dir = Path("tests/fixtures/external_signal_shadow/stage1_6b")
    index_bytes = (fix_dir / "profile_probe_index_fixture.json").read_bytes()
    detail_bytes = (fix_dir / "profile_probe_detail_fixture.json").read_bytes()
    calls = []

    def mock_opener(req, timeout=10.0):
        if "article/list/query" in req.get_full_url():
            return MockHTTPResponse(index_bytes, url=req.get_full_url())
        return MockHTTPResponse(detail_bytes, url=req.get_full_url())

    def guarded_writer(*args, **kwargs):
        calls.append((args, kwargs))
        return original_writer(*args, **kwargs)

    original_writer = write_atomic_json
    monkeypatch.setattr(probe_runner, "write_atomic_json", guarded_writer, raising=False)
    run_source_profile_probe(
        probe_article_id="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        live_public_readonly=True,
        project_root=tmp_path,
        opener=mock_opener,
    )
    assert len(calls) == 1
    assert calls[0][1]["write_class"] == "ordinary_control_plane"
