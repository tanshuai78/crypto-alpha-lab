from scripts.run_extreme_funding_watchlist import (
    build_snapshot,
    should_poll,
    summarize_reject_counts,
    binance_symbol_from_pair,
    build_binance_fapi_url,
    fetch_json_url,
)


def test_should_poll_respects_interval():
    assert should_poll(last_poll_ts=0.0, now_ts=10.0, interval_sec=10) is True
    assert should_poll(last_poll_ts=5.0, now_ts=10.0, interval_sec=10) is False


def test_summarize_reject_counts_counts_reasons():
    summary = summarize_reject_counts(["premium_below_threshold", "api_stale", "api_stale"])
    assert summary == {"premium_below_threshold": 1, "api_stale": 2}


def test_build_snapshot_requires_no_private_fields():
    raw = {
        "symbol": "DOGE/USDT",
        "exchange": "binance",
        "timestamp_ms": 1,
        "mark_price": 0.25,
        "index_price": 0.249,
        "premium_index": 0.001,
        "estimated_funding_rate": 0.0008,
        "next_funding_time_ms": 100,
        "open_interest": 1000.0,
        "oi_change_1h_pct": 1.0,
        "volume_24h_usdt": 100000000.0,
        "mark_data_age_sec": 1.0,
        "oi_data_age_sec": 1.0,
        "apiKey": "must_drop",
        "secret": "must_drop",
    }

    snapshot = build_snapshot(raw)

    assert snapshot["symbol"] == "DOGE/USDT"
    assert "apiKey" not in snapshot
    assert "secret" not in snapshot


def test_binance_symbol_from_pair_removes_separator():
    assert binance_symbol_from_pair("DOGE/USDT") == "DOGEUSDT"
    assert binance_symbol_from_pair("BTC/USDT") == "BTCUSDT"


def test_build_binance_fapi_url_encodes_query_params():
    url = build_binance_fapi_url(
        base_url="https://fapi.binance.com",
        path="/fapi/v1/openInterest",
        params={"symbol": "DOGEUSDT"},
    )

    assert url == "https://fapi.binance.com/fapi/v1/openInterest?symbol=DOGEUSDT"


import json
from io import BytesIO


class _FakeResponse:
    def __init__(self, payload: object):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return BytesIO(self._payload)

    def __exit__(self, exc_type, exc, tb):
        return False


def test_fetch_json_url_uses_injected_opener():
    calls = []

    def fake_opener(request, *, timeout):
        calls.append((request.full_url, timeout))
        return _FakeResponse({"ok": True})

    result = fetch_json_url("https://example.test/path", timeout_sec=2.5, opener=fake_opener)

    assert result == {"ok": True}
    assert calls == [("https://example.test/path", 2.5)]


