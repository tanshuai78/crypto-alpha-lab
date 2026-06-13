from __future__ import annotations

import pytest

from research.external_signal_shadow.gate_public_collector import (
    GateTickerResult,
    build_gate_ticker_url,
    build_raw_wrapper_from_ticker,
    normalize_gate_pair_to_symbol,
    parse_gate_ticker_payload,
    reject_private_endpoint_path,
)


def test_gate_symbol_normalization() -> None:
    assert normalize_gate_pair_to_symbol("BTC_USDT") == "BTCUSDT"
    assert normalize_gate_pair_to_symbol("BTC/USDT") == "BTCUSDT"
    assert normalize_gate_pair_to_symbol("btcusdt") == "BTCUSDT"


def test_collector_builds_public_url_only() -> None:
    url = build_gate_ticker_url("https://api.gateio.ws/api/v4", "/spot/tickers", "BTC_USDT")
    assert url == "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT"


@pytest.mark.parametrize(
    "path",
    [
        "/spot/orders",
        "/wallet/withdrawals",
        "/spot/accounts",
        "/futures/usdt/positions",
        "/margin/accounts",
        "/spot/candlesticks",
    ],
)
def test_collector_rejects_private_or_unsupported_paths(path: str) -> None:
    with pytest.raises(ValueError):
        reject_private_endpoint_path(path)


def test_parse_rejects_response_pair_mismatch() -> None:
    payload = [{
        "currency_pair": "ETH_USDT",
        "last": "100",
        "base_volume": "1",
        "quote_volume": "100",
        "change_percentage": "0",
    }]
    with pytest.raises(ValueError, match="pair mismatch"):
        parse_gate_ticker_payload(payload, "BTC_USDT")


def test_collector_preserves_numeric_raw_strings_and_parse_status() -> None:
    payload = [{
        "currency_pair": "BTC_USDT",
        "last": "65000.1",
        "base_volume": "123.45",
        "quote_volume": "8000000",
        "change_percentage": "1.23",
    }]
    result = parse_gate_ticker_payload(payload, "BTC_USDT")
    assert result.symbol == "BTCUSDT"
    assert result.metadata["last_price_raw"] == "65000.1"
    assert result.metadata["last_price_parse_ok"] is True
    assert result.metadata["quote_volume_raw"] == "8000000"
    assert result.metadata["quote_volume_parse_ok"] is True


def test_collector_tracks_numeric_parse_failures() -> None:
    payload = [{
        "currency_pair": "BTC_USDT",
        "last": "not-a-number",
        "base_volume": "123.45",
        "quote_volume": "8000000",
        "change_percentage": "1.23",
    }]
    result = parse_gate_ticker_payload(payload, "BTC_USDT")
    assert result.metadata["last_price_parse_ok"] is False
    assert result.numeric_parse_failure_count == 1


def test_collector_builds_readonly_raw_wrapper() -> None:
    result = GateTickerResult(
        gate_pair="BTC_USDT",
        symbol="BTCUSDT",
        metadata={
            "last_price_raw": "65000.1",
            "last_price_parse_ok": True,
            "base_volume_raw": "123.45",
            "base_volume_parse_ok": True,
            "quote_volume_raw": "8000000",
            "quote_volume_parse_ok": True,
            "change_percentage_raw": "1.23",
            "change_percentage_parse_ok": True,
        },
        response_field_names=("currency_pair", "last", "base_volume", "quote_volume", "change_percentage"),
        numeric_parse_failure_count=0,
    )
    wrapper = build_raw_wrapper_from_ticker(
        result,
        fetched_at_ms=1781165880123,
        collector_run_id="gate_public_market_snapshot_20260612T120000Z",
        collector_run_started_at_ms=1781165880000,
        collector_run_finished_at_ms=1781165880123,
        snapshot_sequence_id=1,
        api_status_code=200,
        api_latency_ms=123,
        api_response_hash="abc123",
        api_endpoint="/spot/tickers",
        api_query={"currency_pair": "BTC_USDT"},
        api_url="https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT",
    )

    assert wrapper["source"] == "gate_public_market_snapshot_collector"
    assert wrapper["source_capture_method"] == "public_rest_snapshot"
    assert wrapper["data_quality"] == "api_snapshot"
    assert wrapper["available_at_ms"] == 1781165880123
    assert wrapper["raw_payload"]["event_type"] == "cex_market_snapshot"
    assert wrapper["raw_payload"]["direction_hint"] == "unknown"
    assert wrapper["raw_payload"]["metadata"]["event_time_policy"] == "available_at_fallback"
    assert wrapper["raw_payload"]["metadata"]["source_url"].endswith("currency_pair=BTC_USDT")
    assert wrapper["raw_payload"]["triple_barrier_directional_order_allowed"] is False
    assert wrapper["raw_payload"]["alpha_interpretation_allowed"] is False
    assert wrapper["schedule_generated"] is True
