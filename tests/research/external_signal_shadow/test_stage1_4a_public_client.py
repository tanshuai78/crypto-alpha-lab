"""
tests/research/external_signal_shadow/test_stage1_4a_public_client.py
"""

import pytest

from research.external_signal_shadow.stage1_4a_public_client import build_binance_public_url


def test_build_binance_fapi_url_uses_public_base_and_query():
    url = build_binance_public_url("/fapi/v1/klines", {"symbol": "BTCUSDT", "limit": 10})
    assert url.startswith("https://fapi.binance.com/fapi/v1/klines")
    assert "symbol=BTCUSDT" in url
    assert "limit=10" in url


def test_private_or_account_paths_are_rejected():
    with pytest.raises(ValueError, match="forbidden"):
        build_binance_public_url("/fapi/v1/order")

    with pytest.raises(ValueError, match="forbidden"):
        build_binance_public_url("/fapi/v1/account")

    with pytest.raises(ValueError, match="forbidden"):
        build_binance_public_url("/fapi/v1/positionRisk")


def test_allowed_public_paths_pass():
    paths = [
        "/fapi/v1/fundingRate",
        "/futures/data/openInterestHist",
        "/fapi/v1/klines",
        "/fapi/v1/openInterest",
    ]
    for p in paths:
        url = build_binance_public_url(p)
        assert p in url


def test_public_client_does_not_require_or_accept_api_key():
    # Pass forbidden param -> should raise ValueError
    with pytest.raises(ValueError, match="Forbidden security parameter"):
        build_binance_public_url("/fapi/v1/klines", {"apiKey": "some_key"})

    # Pass forbidden header -> should raise ValueError
    with pytest.raises(ValueError, match="Forbidden security header"):
        build_binance_public_url("/fapi/v1/klines", headers={"X-MBX-APIKEY": "some_key"})
