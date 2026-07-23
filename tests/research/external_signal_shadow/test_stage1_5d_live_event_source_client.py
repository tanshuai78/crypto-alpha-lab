from unittest.mock import patch

import pytest

from src.research.external_signal_shadow.stage1_5d_live_event_source_client import (
    build_announcement_list_url,
    fetch_public_json,
    fetch_public_payload,
    host_allowed,
    validate_announcement_detail_url,
    validate_url_allowlist,
    build_announcement_detail_fallback_urls,
    build_bapi_article_detail_url,
    validate_bapi_article_detail_url,
    fetch_public_bapi_article_detail,
    validate_bapi_article_detail_payload,
)



def test_host_allowlist_accepts_exact_and_subdomain():
    assert host_allowed("binance.com", ("binance.com",)) is True
    assert host_allowed("www.binance.com", ("binance.com",)) is True


def test_host_allowlist_rejects_suffix_spoofing():
    assert host_allowed("evilbinance.com", ("binance.com",)) is False
    assert host_allowed("binance.com.evil.com", ("binance.com",)) is False


def test_validate_url_rejects_disallowed_domain():
    with pytest.raises(ValueError, match="domain_not_allowed"):
        validate_url_allowlist("https://binance.com.evil.com/api", ("binance.com",))


def test_fetch_public_json_requires_live_flag():
    with patch("urllib.request.urlopen") as urlopen:
        with pytest.raises(PermissionError):
            fetch_public_json("https://www.binance.com/test", live_public_readonly=False)
        urlopen.assert_not_called()


def test_announcement_list_url_uses_configured_query_params():
    url = build_announcement_list_url(
        base_url="https://www.binance.com",
        path="/bapi/composite/v1/public/cms/article/list/query",
        query_params={"type": "1", "pageNo": "1", "pageSize": "50"},
    )
    assert url.startswith("https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?")
    assert "type=1" in url
    assert "pageNo=1" in url
    assert "pageSize=50" in url


def test_fetch_public_json_rejects_redirect_final_host_not_allowed():
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return "https://binance.com.evil.com/final"

        def read(self):
            return b'{"ok": true}'

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        with pytest.raises(ValueError, match="redirect_final_domain_not_allowed"):
            fetch_public_json("https://www.binance.com/test", live_public_readonly=True, timeout_sec=1.0)


def test_detail_url_non_https_rejected():
    with pytest.raises(ValueError, match="detail_url_scheme_not_allowed"):
        validate_announcement_detail_url("http://www.binance.com/en/support/announcement/abc")


def test_detail_url_non_allowlisted_host_rejected():
    with pytest.raises(ValueError, match="domain_not_allowed"):
        validate_announcement_detail_url("https://evil.com/en/support/announcement/abc")


def test_detail_url_localhost_rejected():
    with pytest.raises(ValueError):
        validate_announcement_detail_url("https://localhost/en/support/announcement/abc")


def test_detail_url_missing_marks_url_missing_without_crash():
    with pytest.raises(ValueError, match="detail_url_missing"):
        validate_announcement_detail_url("")


def test_detail_url_rejects_redirect_query_injection():
    with pytest.raises(ValueError, match="detail_url_query_not_allowed"):
        validate_announcement_detail_url("https://www.binance.com/en/support/announcement/abc?redirect=https://evil.com")


def test_fetch_public_payload_returns_raw_text_without_json_parse():
    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return "https://www.binance.com/en/support/announcement/abc"
        def read(self): return b"<html>BTCU and ETHU Perpetual Contracts</html>"

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload("https://www.binance.com/en/support/announcement/abc", live_public_readonly=True)

    assert result["ok"] is True
    assert result["payload"] == "<html>BTCU and ETHU Perpetual Contracts</html>"
    assert result["payload_size_bytes"] > 0


def test_detail_url_private_ip_rejected_even_if_allowlisted_for_test():
    with pytest.raises(ValueError, match="domain_not_allowed"):
        validate_announcement_detail_url(
            "https://10.0.0.1/en/support/announcement/abc",
            allowed_domains=("10.0.0.1",),
        )

    with pytest.raises(ValueError, match="domain_not_allowed"):
        validate_announcement_detail_url(
            "https://192.168.1.5/en/support/announcement/abc",
            allowed_domains=("192.168.1.5",),
        )


def test_fetch_public_payload_rejects_empty_body():
    class FakeResponse:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def geturl(self):
            return "https://www.binance.com/en/support/announcement/abc"
        def read(self):
            return b""

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload(
            "https://www.binance.com/en/support/announcement/abc",
            live_public_readonly=True,
        )

    assert result["ok"] is False
    assert result["http_status"] == 200
    assert result["payload_size_bytes"] == 0
    assert result["payload"] is None
    assert result["error"] == "empty_detail_payload"


def test_fetch_public_payload_treats_http_202_as_not_ready():
    class FakeResponse:
        status = 202
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def geturl(self):
            return "https://www.binance.com/en/support/announcement/abc"
        def read(self):
            return b""

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload(
            "https://www.binance.com/en/support/announcement/abc",
            live_public_readonly=True,
        )

    assert result["ok"] is False
    assert result["http_status"] == 202
    assert result["payload_size_bytes"] == 0
    assert result["payload"] is None
    assert result["error"] == "detail_payload_http_status_202"


def test_fetch_public_payload_treats_http_429_as_not_ready():
    class FakeResponse:
        status = 429
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def geturl(self):
            return "https://www.binance.com/en/support/announcement/abc"
        def read(self):
            return b"Too Many Requests"

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload(
            "https://www.binance.com/en/support/announcement/abc",
            live_public_readonly=True,
        )

    assert result["ok"] is False
    assert result["http_status"] == 429
    assert result["payload"] is None
    assert result["error"] == "detail_payload_http_status_429"


def test_fetch_public_payload_treats_http_503_as_not_ready():
    class FakeResponse:
        status = 503
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def geturl(self):
            return "https://www.binance.com/en/support/announcement/abc"
        def read(self):
            return b"Service Unavailable"

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        result = fetch_public_payload(
            "https://www.binance.com/en/support/announcement/abc",
            live_public_readonly=True,
        )

    assert result["ok"] is False
    assert result["http_status"] == 503
    assert result["payload"] is None
    assert result["error"] == "detail_payload_http_status_503"


def test_build_announcement_detail_fallback_urls_returns_allowlisted_detail_variants():
    urls = build_announcement_detail_fallback_urls(
        "https://www.binance.com/en/support/announcement/d0833e4ae9b542be90dbf3fe1c960c53"
    )
    assert "https://www.binance.com/en/support/announcement/detail/d0833e4ae9b542be90dbf3fe1c960c53" in urls
    assert urls[0].endswith("/announcement/d0833e4ae9b542be90dbf3fe1c960c53")
    assert len(urls) == len(set(urls))
    for url in urls:
        validate_announcement_detail_url(url)


def test_build_announcement_detail_fallback_urls_with_detail_primary():
    urls = build_announcement_detail_fallback_urls(
        "https://www.binance.com/en/support/announcement/detail/d0833e4ae9b542be90dbf3fe1c960c53"
    )
    assert "https://www.binance.com/en/support/announcement/d0833e4ae9b542be90dbf3fe1c960c53" in urls
    assert urls[0].endswith("/announcement/detail/d0833e4ae9b542be90dbf3fe1c960c53")
    assert len(urls) == len(set(urls))
    for url in urls:
        validate_announcement_detail_url(url)


def test_build_bapi_article_detail_url_requires_32_hex_code():
    with pytest.raises(ValueError, match="bapi_article_code_invalid"):
        build_bapi_article_detail_url("not-valid")


def test_build_bapi_article_detail_url_uses_query_param():
    url = build_bapi_article_detail_url("f43403ef11974998bc0f46420826577a")
    assert url == (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query"
        "?articleCode=f43403ef11974998bc0f46420826577a"
    )


def test_validate_bapi_article_detail_url_rejects_support_path():
    with pytest.raises(ValueError, match="bapi_detail_path_not_allowed"):
        validate_bapi_article_detail_url("https://www.binance.com/en/support/announcement/abc")


def test_validate_bapi_article_detail_url_requires_exact_www_binance_host():
    code = "f43403ef11974998bc0f46420826577a"
    path = "/bapi/composite/v1/public/cms/article/detail/query"
    with pytest.raises(ValueError):
        validate_bapi_article_detail_url(f"https://evil.binance.com{path}?articleCode={code}")


def test_validate_bapi_article_detail_url_rejects_userinfo_port_fragment_and_extra_query():
    code = "f43403ef11974998bc0f46420826577a"
    path = "/bapi/composite/v1/public/cms/article/detail/query"
    bad_urls = [
        f"https://user@www.binance.com{path}?articleCode={code}",
        f"https://www.binance.com:444{path}?articleCode={code}",
        f"https://www.binance.com{path}?articleCode={code}#frag",
        f"https://www.binance.com{path}?articleCode={code}&x=1",
    ]
    for url in bad_urls:
        with pytest.raises(ValueError):
            validate_bapi_article_detail_url(url)


def test_fetch_public_bapi_article_detail_requires_live_flag():
    with patch("urllib.request.urlopen") as urlopen:
        with pytest.raises(PermissionError):
            fetch_public_bapi_article_detail(
                "f43403ef11974998bc0f46420826577a",
                live_public_readonly=False,
            )
        urlopen.assert_not_called()


def test_fetch_public_bapi_article_detail_does_not_send_private_headers():
    captured = {}

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self):
            return "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=f43403ef11974998bc0f46420826577a"
        def read(self, n=-1):
            return b'{"code":"000000","data":{"code":"f43403ef11974998bc0f46420826577a","title":"x","body":"{}"}}'

    def fake_urlopen(req, timeout):
        captured.update(dict(req.header_items()))
        return FakeResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        fetch_public_bapi_article_detail(
            "f43403ef11974998bc0f46420826577a",
            live_public_readonly=True,
        )

    lowered = {k.lower(): v for k, v in captured.items()}
    assert "authorization" not in lowered
    assert "cookie" not in lowered
    assert "x-mbx-apikey" not in lowered


def test_bapi_response_read_is_bounded():
    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self):
            return "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=f43403ef11974998bc0f46420826577a"
        def read(self, n=-1):
            assert n == 101
            return b'{"code":"000000"}'

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES", 100):
        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            fetch_public_bapi_article_detail(
                "f43403ef11974998bc0f46420826577a",
                live_public_readonly=True,
            )


def test_bapi_response_above_max_bytes_is_rejected():
    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self):
            return "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=f43403ef11974998bc0f46420826577a"
        def read(self, n=-1):
            return b"x" * n

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES", 100):
        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            result = fetch_public_bapi_article_detail(
                "f43403ef11974998bc0f46420826577a",
                live_public_readonly=True,
            )
    assert result["ok"] is False
    assert result["error"] == "bapi_response_too_large"


def _trusted_payload(article_code="f43403ef11974998bc0f46420826577a", title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)"):
    return {
        "code": "000000",
        "data": {
            "code": article_code,
            "id": 280581,
            "title": title,
            "body": '{"node":"root","child":[{"node":"text","text":"Binance Futures will launch SHAZUSDT Perpetual Contracts"}]}',
        },
    }


def test_validate_bapi_payload_accepts_identity_and_title_match():
    result = validate_bapi_article_detail_payload(
        _trusted_payload(),
        requested_article_code="f43403ef11974998bc0f46420826577a",
        catalog_title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
    )
    assert result["payload_trusted"] is True
    assert result["data"]["code"] == "f43403ef11974998bc0f46420826577a"


def test_validate_bapi_payload_rejects_identity_mismatch():
    payload = _trusted_payload(article_code="d0833e4ae9b542be90dbf3fe1c960c53")
    result = validate_bapi_article_detail_payload(
        payload,
        requested_article_code="f43403ef11974998bc0f46420826577a",
        catalog_title=payload["data"]["title"],
    )
    assert result["payload_trusted"] is False
    assert result["error"] == "bapi_article_identity_mismatch"


def test_validate_bapi_payload_rejects_title_mismatch():
    result = validate_bapi_article_detail_payload(
        _trusted_payload(title="Unrelated announcement"),
        requested_article_code="f43403ef11974998bc0f46420826577a",
        catalog_title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
    )
    assert result["payload_trusted"] is False
    assert result["error"] == "bapi_article_title_mismatch"
    assert result["fallback_to_support_detail"] is True


def test_validate_bapi_payload_rejects_html_shell_or_login_body():
    payload = _trusted_payload()
    payload["data"]["body"] = "<html><title>Just a moment...</title></html>"
    result = validate_bapi_article_detail_payload(
        payload,
        requested_article_code="f43403ef11974998bc0f46420826577a",
        catalog_title=payload["data"]["title"],
    )
    assert result["payload_trusted"] is False
    assert result["error"] in {"bapi_waf_or_login_shell", "bapi_body_schema_drift"}
