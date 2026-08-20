"""Unit tests for Stage 1.6B canonical source client."""

import ast
import io
import json
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_6b_canonical_source_client import (
    ClientValidationError,
    Stage16BCanonicalClient,
    validate_request_url_and_headers,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    RequestClass,
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


def test_validate_request_url_and_headers():
    """Verify strict URL and header validation."""
    valid_url = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50"
    headers = {"Accept": "application/json", "Accept-Language": "en"}
    req = validate_request_url_and_headers(valid_url, headers)
    assert req.get_full_url() == valid_url

    # Scheme not HTTPS
    with pytest.raises(ClientValidationError, match="https_required"):
        validate_request_url_and_headers("http://www.binance.com/test", headers)

    # Disallowed host
    with pytest.raises(ClientValidationError, match="disallowed_host"):
        validate_request_url_and_headers("https://api.binance.com/test", headers)

    # Forbidden headers
    with pytest.raises(ClientValidationError, match="forbidden_header"):
        validate_request_url_and_headers(valid_url, {"Accept": "application/json", "Cookie": "session=123"})


def test_client_index_and_detail_fetch(tmp_path):
    """Verify index and detail fetch using injected opener."""
    index_data = json.dumps({"code": "000000", "data": {"articles": [{"code": "a" * 32, "title": "Test"}]}}).encode("utf-8")
    detail_data = json.dumps({"code": "000000", "data": {"code": "a" * 32, "title": "Test", "body": "Content"}}).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_data, url=url)
        elif "article/detail/query" in url:
            return MockHTTPResponse(detail_data, url=url)
        raise ValueError(f"Unexpected url: {url}")

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)

    # Index fetch
    res_index = client.fetch_index_page(page_no=1, run_id="run_1", request_class=RequestClass.HISTORICAL_INDEX.value, monotonic_request_seq=1)
    assert res_index.http_status == 200
    assert res_index.raw_payload_bytes == len(index_data)
    assert res_index.trust_validation_status == "trusted"

    # Detail fetch
    res_detail = client.fetch_article_detail(article_code="a" * 32, run_id="run_1", request_class=RequestClass.HISTORICAL_DETAIL.value, monotonic_request_seq=2)
    assert res_detail.http_status == 200
    assert res_detail.raw_payload_bytes == len(detail_data)
    assert res_detail.trust_validation_status == "trusted"


def test_client_requires_live_public_readonly_flag():
    """Verify that client cannot be instantiated or execute without live_public_readonly=True."""
    with pytest.raises(ValueError, match="live_public_readonly_required"):
        Stage16BCanonicalClient(live_public_readonly=False)


def test_client_rejects_payload_exceeding_max_bytes():
    """Verify rejection when payload exceeds 2,000,000 bytes SSOT cap."""
    large_body = b"x" * 2_000_001

    def mock_opener(req, timeout=10.0):
        return MockHTTPResponse(large_body)

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener)
    res = client.fetch_index_page(page_no=1, run_id="run_1", request_class=RequestClass.HISTORICAL_INDEX.value, monotonic_request_seq=1)
    assert res.trust_validation_status == "payload_size_exceeded"


def test_client_rejects_waf_and_empty():
    """Verify rejection on HTML/WAF or empty response body."""
    waf_body = b"<html><head><title>Cloudflare WAF Block</title></head><body>Block</body></html>"

    def mock_opener_waf(req, timeout=10.0):
        return MockHTTPResponse(waf_body, headers={"Content-Type": "text/html"})

    client_waf = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener_waf)
    res_waf = client_waf.fetch_index_page(page_no=1, run_id="run_1", request_class=RequestClass.HISTORICAL_INDEX.value, monotonic_request_seq=1)
    assert res_waf.trust_validation_status in ["waf_rejected", "malformed_json"]

    def mock_opener_empty(req, timeout=10.0):
        return MockHTTPResponse(b"")

    client_empty = Stage16BCanonicalClient(live_public_readonly=True, opener=mock_opener_empty)
    res_empty = client_empty.fetch_index_page(page_no=1, run_id="run_1", request_class=RequestClass.HISTORICAL_INDEX.value, monotonic_request_seq=2)
    assert res_empty.trust_validation_status == "empty_payload"


def test_static_forbid_third_party_http_libraries():
    """Verify that client implementation imports only urllib and standard library modules."""
    client_src = Path("src/research/external_signal_shadow/stage1_6b_canonical_source_client.py").read_text()
    tree = ast.parse(client_src)

    forbidden = ["requests", "httpx", "aiohttp", "urllib3", "socket"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                for f in forbidden:
                    assert f not in name.name, f"Forbidden import: {name.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for f in forbidden:
                    assert f not in node.module, f"Forbidden import from: {node.module}"
