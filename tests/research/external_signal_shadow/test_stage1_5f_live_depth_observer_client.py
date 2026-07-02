import time

import pytest

from configs import base
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_client import (
    build_depth_url,
    fetch_public_json,
    is_allowed_public_url,
    refresh_exchangeinfo_cache,
)


def test_depth_url_uses_configured_limit():
    url = build_depth_url("ABCUSDT", limit=base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_LIMIT)
    assert f"limit={base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_LIMIT}" in url
    assert "symbol=ABCUSDT" in url


def test_depth_url_uses_raw_u_settled_symbol_without_usdt_suffix():
    url = build_depth_url("BTCU", limit=base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_LIMIT)
    assert "symbol=BTCU" in url
    assert "BTCUUSDT" not in url


def test_exchangeinfo_refresh_respects_cadence():
    now = int(time.time() * 1000)
    prev = {
        "last_refreshed_ms": now - 10000,  # 10s ago
        "symbols": {"BTCUSDT"},
        "available": True,
    }
    # refresh cadence is 300s. Since 10s < 300s, it should not refresh and return prev as is.
    res = refresh_exchangeinfo_cache(now, prev, live_public_readonly=False)
    assert res["last_refreshed_ms"] == prev["last_refreshed_ms"]
    assert res["symbols"] == prev["symbols"]
    assert res["available"] == prev["available"]
    assert res["manifest_row"] is None


def test_exchangeinfo_cache_hit_does_not_rewrite_old_manifest_row():
    now = int(time.time() * 1000)
    prev = {
        "last_refreshed_ms": now - 10000,
        "symbols": {"BTCUSDT"},
        "available": True,
        "manifest_row": {
            "requested_path": "/fapi/v1/exchangeInfo",
            "http_status": 200,
            "fetched_at_ms": now - 10000,
        },
    }

    res = refresh_exchangeinfo_cache(now, prev, live_public_readonly=False)

    assert res["symbols"] == {"BTCUSDT"}
    assert res["available"] is True
    assert res.get("manifest_row") is None


def test_exchangeinfo_fetch_failure_marks_unavailable_not_empty_symbol_set(monkeypatch):
    def mock_urlopen(*args, **kwargs):
        raise Exception("Connection timeout")
    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    prev = {
        "last_refreshed_ms": 1000,
        "symbols": {"BTCUSDT"},
        "available": True,
    }

    # Force refresh by passing high now_ms
    now = 1000 + 301000
    res = refresh_exchangeinfo_cache(now, prev, live_public_readonly=True)
    assert res["available"] is False
    assert res["symbols"] == {"BTCUSDT"}  # symbols preserved
    assert res["last_refreshed_ms"] == 1000  # last successful refresh time preserved or now? Let's preserve old successful time.


def test_public_client_rejects_non_binance_host():
    assert is_allowed_public_url("https://fapi.binance.com/fapi/v1/depth?symbol=BTC") is True
    assert is_allowed_public_url("https://evil.host.com/fapi/v1/depth") is False
    assert is_allowed_public_url("http://fapi.binance.com/fapi/v1/depth") is False  # http forbidden


def test_public_client_does_not_accept_private_or_order_endpoint():
    # Only exchangeInfo and depth allowed
    assert is_allowed_public_url("https://fapi.binance.com/fapi/v1/depth") is True
    assert is_allowed_public_url("https://fapi.binance.com/fapi/v1/exchangeInfo") is True
    assert is_allowed_public_url("https://fapi.binance.com/fapi/v1/order") is False
    assert is_allowed_public_url("https://fapi.binance.com/fapi/v1/account") is False


def test_request_manifest_row_contains_requested_url_status_error_and_fetched_at(monkeypatch):
    class FakeResponse:
        url = "https://fapi.binance.com/fapi/v1/depth"
        status = 200
        def read(self):
            return b'{"ok": true}'
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())

    res = fetch_public_json("https://fapi.binance.com/fapi/v1/depth?symbol=ABC", live_public_readonly=True)
    assert res["ok"] is True
    manifest = res["manifest_row"]
    assert manifest["requested_host"] == "fapi.binance.com"
    assert manifest["requested_path"] == "/fapi/v1/depth"
    assert manifest["http_status"] == 200
    assert manifest["error"] is None
    assert manifest["fetched_at_ms"] > 0


def test_request_manifest_contains_payload_hash_and_size(monkeypatch):
    payload = b'{"hello": "world"}'
    class FakeResponse:
        url = "https://fapi.binance.com/fapi/v1/depth"
        status = 200
        def read(self):
            return payload
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())

    res = fetch_public_json("https://fapi.binance.com/fapi/v1/depth", live_public_readonly=True)
    manifest = res["manifest_row"]
    assert manifest["payload_size_bytes"] == len(payload)
    import hashlib
    expected_hash = hashlib.sha256(payload).hexdigest()
    assert manifest["response_payload_hash"] == expected_hash


def test_request_manifest_does_not_store_api_key_or_secret_fields(monkeypatch):
    class FakeResponse:
        url = "https://fapi.binance.com/fapi/v1/depth"
        status = 200
        def read(self):
            return b"{}"
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())

    # Even if we pass secret or key in URL (which is forbidden anyway), manifest should not store it
    url = "https://fapi.binance.com/fapi/v1/depth?signature=123&apiKey=456"
    res = fetch_public_json(url, live_public_readonly=True)
    manifest = res["manifest_row"]

    # The URL hashes are fine, but verify no plaintext api keys or signatures exist in manifest fields
    for k, v in manifest.items():
        if isinstance(v, str):
            assert "signature" not in v
            assert "apiKey" not in v


def test_runner_raises_if_network_called_without_live_flag():
    with pytest.raises(RuntimeError) as exc:
        fetch_public_json("https://fapi.binance.com/fapi/v1/depth", live_public_readonly=False)
    assert "disabled" in str(exc.value)


def test_fixture_mode_does_not_call_real_network():
    # If live_public_readonly is False, it raises RuntimeError instantly. This guarantees no network calls in fixture mode.
    with pytest.raises(RuntimeError):
        fetch_public_json("https://fapi.binance.com/fapi/v1/depth", live_public_readonly=False)


def test_stage1_5f_client_handles_http_400_for_invalid_u_settled_depth_request(monkeypatch):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_client import (
        fetch_depth_snapshot,
    )
    from urllib.error import HTTPError
    import io

    def mock_urlopen(*args, **kwargs):
        fp = io.BytesIO(b'{"code": -1121, "msg": "Invalid symbol."}')
        raise HTTPError(
            url="https://fapi.binance.com/fapi/v1/depth?symbol=BTCU",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=fp
        )

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    res = fetch_depth_snapshot("BTCU", live_public_readonly=True)

    assert res["ok"] is False
    assert res["error"] == "http_error_400"
    assert "Invalid symbol" in res["message"] or "Bad Request" in res["message"]
