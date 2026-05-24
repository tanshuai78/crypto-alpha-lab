from scripts.run_extreme_funding_watchlist import (
    build_snapshot,
    should_poll,
    summarize_reject_counts,
    binance_symbol_from_pair,
    build_binance_fapi_url,
    fetch_json_url,
    find_premium_item,
    parse_open_interest,
    OpenInterestWindow,
    build_raw_snapshot_from_public_data,
    run_watchlist_poll_once,
    parse_args,
    classify_loop_exception,
)
from strategies.extreme_funding.scanner import ExtremeFundingWatchlistScanner


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


def test_find_premium_item_returns_matching_symbol():
    items = [
        {"symbol": "BTCUSDT", "markPrice": "100.0"},
        {"symbol": "DOGEUSDT", "markPrice": "0.25"},
    ]

    assert find_premium_item(items, "DOGEUSDT") == {"symbol": "DOGEUSDT", "markPrice": "0.25"}


def test_find_premium_item_returns_none_when_missing():
    assert find_premium_item([{"symbol": "BTCUSDT"}], "DOGEUSDT") is None


def test_parse_open_interest_returns_float():
    assert parse_open_interest({"openInterest": "12345.67"}) == 12345.67


def test_open_interest_window_returns_none_until_lookback_exists():
    window = OpenInterestWindow(lookback_sec=3600)
    window.append("DOGE/USDT", timestamp_ms=0, open_interest=100.0)

    assert window.change_pct("DOGE/USDT", now_ms=10 * 60_000, current_open_interest=110.0) is None


def test_open_interest_window_calculates_change_against_oldest_retained_value():
    window = OpenInterestWindow(lookback_sec=3600)
    window.append("DOGE/USDT", timestamp_ms=0, open_interest=100.0)
    window.append("DOGE/USDT", timestamp_ms=3600 * 1000, open_interest=110.0)

    assert window.change_pct("DOGE/USDT", now_ms=3600 * 1000, current_open_interest=110.0) == 10.0


def test_build_raw_snapshot_from_public_data_maps_public_fields():
    premium_item = {
        "symbol": "DOGEUSDT",
        "markPrice": "0.2500",
        "indexPrice": "0.2490",
        "lastFundingRate": "0.0008",
        "nextFundingTime": "123456789",
    }

    raw = build_raw_snapshot_from_public_data(
        pair="DOGE/USDT",
        exchange="binance",
        timestamp_ms=1000,
        premium_item=premium_item,
        open_interest=12345.0,
        oi_change_1h_pct=2.5,
        mark_data_age_sec=1.0,
        oi_data_age_sec=2.0,
    )

    assert raw["symbol"] == "DOGE/USDT"
    assert raw["exchange"] == "binance"
    assert raw["mark_price"] == 0.25
    assert raw["index_price"] == 0.249
    assert raw["premium_index"] == (0.25 - 0.249) / 0.249
    assert raw["estimated_funding_rate"] == 0.0008
    assert raw["next_funding_time_ms"] == 123456789
    assert raw["open_interest"] == 12345.0
    assert raw["oi_change_1h_pct"] == 2.5


def _premium_payload():
    return [
        {
            "symbol": "DOGEUSDT",
            "markPrice": "0.2600",
            "indexPrice": "0.2500",
            "lastFundingRate": "0.0008",
            "nextFundingTime": "123456789",
        }
    ]


def test_run_watchlist_poll_once_rejects_until_persistence_warmup_complete():
    scanner = ExtremeFundingWatchlistScanner()
    oi_window = OpenInterestWindow(lookback_sec=3600)
    oi_payloads = {"DOGEUSDT": {"openInterest": "1000"}}

    result = None
    for second in (0, 60, 120, 180, 240):
        result = run_watchlist_poll_once(
            pairs=("DOGE/USDT",),
            scanner=scanner,
            oi_window=oi_window,
            timestamp_ms=second * 1000,
            premium_payload=_premium_payload(),
            oi_payloads=oi_payloads,
            oi_data_age_sec=1.0,
        )

    assert result["events"] == []
    assert result["reject_reasons"] == ["micro_persistence_warmup"]


def test_run_watchlist_poll_once_emits_after_warmup_and_persistence():
    scanner = ExtremeFundingWatchlistScanner()
    oi_window = OpenInterestWindow(lookback_sec=3600)
    oi_payloads = {"DOGEUSDT": {"openInterest": "1000"}}

    for second in (0, 60, 120, 180, 240):
        run_watchlist_poll_once(
            pairs=("DOGE/USDT",),
            scanner=scanner,
            oi_window=oi_window,
            timestamp_ms=second * 1000,
            premium_payload=_premium_payload(),
            oi_payloads=oi_payloads,
            oi_data_age_sec=1.0,
        )

    result = run_watchlist_poll_once(
        pairs=("DOGE/USDT",),
        scanner=scanner,
        oi_window=oi_window,
        timestamp_ms=300 * 1000,
        premium_payload=_premium_payload(),
        oi_payloads=oi_payloads,
        oi_data_age_sec=1.0,
    )

    assert len(result["events"]) == 1
    assert result["events"][0].level in {"watch_level_1", "watch_level_2", "watch_level_3"}


def test_run_watchlist_poll_once_calculates_oi_change_before_append():
    scanner = ExtremeFundingWatchlistScanner()
    oi_window = OpenInterestWindow(lookback_sec=3600)
    oi_window.append("DOGE/USDT", timestamp_ms=0, open_interest=100.0)

    result = run_watchlist_poll_once(
        pairs=("DOGE/USDT",),
        scanner=scanner,
        oi_window=oi_window,
        timestamp_ms=3600 * 1000,
        premium_payload=_premium_payload(),
        oi_payloads={"DOGEUSDT": {"openInterest": "110"}},
        oi_data_age_sec=1.0,
    )

    assert result["snapshots"][0]["oi_change_1h_pct"] == 10.0


from json import JSONDecodeError
from urllib.error import URLError


def test_parse_args_defaults_to_bounded_local_dry_run():
    args = parse_args([])

    assert args.forever is False
    assert args.max_iterations == 3
    assert args.data_root == "data"
    assert args.once is False


def test_parse_args_once_sets_single_fast_iteration():
    args = parse_args(["--once"])

    assert args.once is True
    assert args.max_iterations == 1
    assert args.poll_interval_sec == 0.0


def test_classify_loop_exception_separates_url_json_and_schema_errors():
    assert classify_loop_exception(URLError("offline"))[0] == "watchlist_url_error"
    assert classify_loop_exception(JSONDecodeError("bad", "{", 0))[0] == "watchlist_json_error"
    assert classify_loop_exception(KeyError("markPrice"))[0] == "watchlist_schema_error"







