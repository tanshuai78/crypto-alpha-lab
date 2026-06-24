from unittest.mock import patch

from src.research.external_signal_shadow.stage1_5c1_price_coverage_client import (
    build_klines_url,
    filter_exchange_symbols,
    iter_kline_request_slices,
    next_start_after_kline_batch,
    parse_kline_array,
    public_get_json,
)


def test_build_futures_klines_url_contains_readonly_params():
    url = build_klines_url(
        base_url="https://fapi.binance.com",
        path="/fapi/v1/klines",
        symbol="ABCUSDT",
        interval="15m",
        start_ms=1,
        end_ms=2,
        limit=1500,
    )
    assert "symbol=ABCUSDT" in url
    assert "interval=15m" in url
    assert "startTime=1" in url
    assert "endTime=2" in url
    assert "limit=1500" in url
    assert "apiKey" not in url


def test_filter_exchange_symbols_only_trading_usdt_perpetuals():
    payload = {"symbols": [
        {"symbol": "ABCUSDT", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDT"},
        {"symbol": "DEFUSDT", "contractType": "CURRENT_QUARTER", "status": "TRADING", "quoteAsset": "USDT"},
        {"symbol": "OLDUSDT", "contractType": "PERPETUAL", "status": "SETTLING", "quoteAsset": "USDT"},
    ]}
    assert filter_exchange_symbols(payload, market_type="futures") == {"ABCUSDT"}


def test_parse_kline_array_to_normalized_row():
    raw = [1710000000000, "1.0", "1.2", "0.9", "1.1", "10", 1710000899999, "12345.6"]
    row = parse_kline_array(raw, symbol="ABCUSDT", source="binance_um_futures_15m")
    assert row["symbol"] == "ABCUSDT"
    assert row["bar_start_ms"] == 1710000000000
    assert row["bar_end_ms"] == 1710000900000
    assert row["open"] == 1.0
    assert row["quote_volume"] == 12345.6
    assert row["api_key_used"] is False


def test_public_get_json_requires_live_flag():
    with patch("urllib.request.urlopen") as urlopen:
        try:
            public_get_json("https://example.com", live_public_readonly=False)
        except PermissionError:
            pass
        else:
            raise AssertionError("expected PermissionError")
        urlopen.assert_not_called()


def test_filter_exchange_symbols_accepts_usdc_perpetuals():
    payload = {"symbols": [
        {"symbol": "ABCUSDC", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDC"},
    ]}
    assert filter_exchange_symbols(payload, market_type="futures") == {"ABCUSDC"}


def test_30d_15m_window_splits_into_multiple_kline_requests():
    slices = list(iter_kline_request_slices(0, 30 * 24 * 3600_000, interval_ms=900_000, limit=1500))
    assert len(slices) >= 2
    assert slices[0][0] == 0
    assert slices[-1][1] >= 30 * 24 * 3600_000


def test_kline_pagination_advances_by_last_open_time_plus_interval():
    assert next_start_after_kline_batch([[0], [900_000]], interval_ms=900_000) == 1_800_000


def test_public_get_json_returns_error_record_after_retry_budget():
    with patch("urllib.request.urlopen", side_effect=TimeoutError("boom")):
        result = public_get_json("https://example.com", live_public_readonly=True, timeout_sec=0.01, retry_budget=1, sleep_sec=0)
    assert result["ok"] is False
    assert result["error"]
