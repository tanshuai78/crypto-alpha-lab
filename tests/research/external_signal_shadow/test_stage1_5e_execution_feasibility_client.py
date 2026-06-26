from src.research.external_signal_shadow.stage1_5e_execution_feasibility_client import (
    build_depth_url,
    fetch_public_json,
    is_allowed_public_url,
)


def test_depth_url_uses_binance_fapi_public_endpoint():
    url = build_depth_url("ABCUSDT", limit=100)
    assert url.startswith("https://fapi.binance.com/fapi/v1/depth")
    assert "symbol=ABCUSDT" in url
    assert "limit=100" in url


def test_public_url_rejects_private_or_non_binance_hosts():
    assert is_allowed_public_url("https://fapi.binance.com/fapi/v1/depth?symbol=ABCUSDT")
    assert not is_allowed_public_url("https://evil-binance.com/fapi/v1/depth")
    assert not is_allowed_public_url("https://fapi.binance.com.evil.io/fapi/v1/depth")


def test_client_rejects_redirect_to_non_binance_host(monkeypatch):
    class FakeResponse:
        url = "https://evil.example.com/fapi/v1/depth"
        status = 200

        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(_request, timeout):
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = fetch_public_json("https://fapi.binance.com/fapi/v1/depth?symbol=ABCUSDT", live_public_readonly=True)
    assert result["ok"] is False
    assert result["error"] == "redirect_final_host_not_allowed"
