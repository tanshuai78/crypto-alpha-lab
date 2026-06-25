from unittest.mock import patch

import pytest

from src.research.external_signal_shadow.stage1_5d_live_event_source_client import (
    build_announcement_list_url,
    fetch_public_json,
    host_allowed,
    validate_url_allowlist,
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
