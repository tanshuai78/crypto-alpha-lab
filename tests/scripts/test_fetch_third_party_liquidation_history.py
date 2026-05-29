import os
from unittest.mock import patch
from typing import Any
import pytest

from scripts.fetch_third_party_liquidation_history import (
    fetch_historical_liquidations,
    load_feasibility_audit,
    normalize_coinalyze_payload,
    symbol_to_coinalyze_contract,
)


def test_load_feasibility_audit_reports_coinalyze_candidate():
    res = load_feasibility_audit()
    assert "vendor_candidates" in res
    candidates = res["vendor_candidates"]
    assert len(candidates) > 0
    candidate = next(c for c in candidates if c["vendor"] == "coinalyze")
    assert candidate["requires_paid_plan"] is False
    assert candidate["granularity"] == "1hour"


def test_missing_coinalyze_api_key_degrades_gracefully():
    with patch.dict(os.environ, {}, clear=True):
        payload, status = fetch_historical_liquidations(symbol="BTC/USDT", from_ts_sec=1716800000, to_ts_sec=1716803600)
        assert payload == []
        assert status == "no_api_key"


@patch("urllib.request.urlopen")
def test_fetch_uses_seconds_timestamps_and_convert_to_usd_true(mock_urlopen):
    import urllib.parse
    import io

    # Mock return value of urlopen
    mock_response = io.BytesIO(b"[]")
    mock_urlopen.return_value = mock_response

    with patch.dict(os.environ, {"COINALYZE_API_KEY": "test_key"}):
        fetch_historical_liquidations(
            symbol="BTC/USDT",
            from_ts_sec=1716800000,
            to_ts_sec=1716803600,
            interval="1hour",
        )

    assert mock_urlopen.call_count == 1
    req = mock_urlopen.call_args[0][0]

    if isinstance(req, str):
        url = req
    else:
        url = req.full_url

    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    assert query_params["symbols"][0] == "BTCUSDT_PERP.A"
    assert query_params["from"][0] == "1716800000"
    assert query_params["to"][0] == "1716803600"
    assert query_params["interval"][0] == "1hour"
    assert query_params["convert_to_usd"][0] == "true"
    
    if "api_key" in query_params:
        assert query_params["api_key"][0] == "test_key"
    else:
        assert req.get_header("api_key") == "test_key" or req.get_header("Api-key") == "test_key"


def test_normalize_coinalyze_payload_maps_l_and_s_to_hourly_schema():
    raw_payload = [
        {
            "t": 1716800000,  # seconds
            "l": 600000.0,    # long liquidation notional
            "s": 300000.0,    # short liquidation notional
        }
    ]
    normalized = normalize_coinalyze_payload(raw_payload, symbol="BTC/USDT")
    assert len(normalized) == 1
    row = normalized[0]
    assert row["symbol"] == "BTC/USDT"
    assert row["vendor_symbol"] == "BTCUSDT_PERP.A"
    assert row["hour_bucket_ms"] == 1716800000000
    assert row["long_liquidation_notional_1h_usdt"] == 600000.0
    assert row["short_liquidation_notional_1h_usdt"] == 300000.0
    assert row["total_liquidation_notional_1h_usdt"] == 900000.0
    assert row["liquidation_notional_1h_usdt"] == 900000.0
    assert row["liquidation_source"] == "third_party_historical"
    assert row["liquidation_source_quality"] == "historical_vendor_dataset"
    assert row["vendor_name"] == "coinalyze"
    assert row["vendor_granularity"] == "1hour"
    assert row["normalized_granularity"] == "1h"
    assert row["convert_to_usd"] is True
    assert row["timestamp_unit_source"] == "seconds"


def test_normalize_converts_vendor_t_seconds_to_hour_bucket_ms():
    raw_payload = [{"t": 123456, "l": 0, "s": 0}]
    normalized = normalize_coinalyze_payload(raw_payload, symbol="BTC/USDT")
    assert normalized[0]["hour_bucket_ms"] == 123456000


def test_normalize_handles_empty_history_as_zero_rows():
    assert normalize_coinalyze_payload([], symbol="BTC/USDT") == []
    assert normalize_coinalyze_payload(None, symbol="BTC/USDT") == []


def test_normalize_deduplicates_same_symbol_hour_by_sum():
    raw_payload = [
        {"t": 1716800000, "l": 100.0, "s": 50.0},
        {"t": 1716800000, "l": 200.0, "s": 150.0},
        {"t": 1716803600, "l": 50.0, "s": 10.0},
    ]
    normalized = normalize_coinalyze_payload(raw_payload, symbol="BTC/USDT")
    assert len(normalized) == 2

    normalized_sorted = sorted(normalized, key=lambda x: x["hour_bucket_ms"])

    assert normalized_sorted[0]["hour_bucket_ms"] == 1716800000000
    assert normalized_sorted[0]["long_liquidation_notional_1h_usdt"] == 300.0
    assert normalized_sorted[0]["short_liquidation_notional_1h_usdt"] == 200.0
    assert normalized_sorted[0]["total_liquidation_notional_1h_usdt"] == 500.0
    assert normalized_sorted[0]["liquidation_notional_1h_usdt"] == 500.0

    assert normalized_sorted[1]["hour_bucket_ms"] == 1716803600000
    assert normalized_sorted[1]["long_liquidation_notional_1h_usdt"] == 50.0
    assert normalized_sorted[1]["short_liquidation_notional_1h_usdt"] == 10.0


def test_symbol_to_coinalyze_contract_maps_watchlist_symbols_with_audited_source():
    res = symbol_to_coinalyze_contract("BTC/USDT")
    assert res["coinalyze_symbol"] == "BTCUSDT_PERP.A"
    assert res["input_symbol"] == "BTC/USDT"
    assert res["exchange"] == "binance"
    assert res["mapping_source"] == "supported_future_markets|static_fallback"


def test_build_route_b_hourly_summary_reports_symbol_and_time_coverage():
    from scripts.fetch_third_party_liquidation_history import build_route_b_hourly_summary
    
    rows = [
        {"symbol": "BTC/USDT", "hour_bucket_ms": 1716800000000, "total_liquidation_notional_1h_usdt": 100},
        {"symbol": "BTC/USDT", "hour_bucket_ms": 1716803600000, "total_liquidation_notional_1h_usdt": 200},
        {"symbol": "ETH/USDT", "hour_bucket_ms": 1716807200000, "total_liquidation_notional_1h_usdt": 300},
    ]
    summary = build_route_b_hourly_summary(rows)
    assert summary["symbol_count"] == 2
    assert summary["symbols"] == ["BTC/USDT", "ETH/USDT"]
    assert summary["row_count"] == 3
    assert summary["start_timestamp_ms"] == 1716800000000
    assert summary["end_timestamp_ms"] == 1716807200000
    assert summary["time_span_hours"] == 2
    assert summary["rows_per_symbol"] == {"BTC/USDT": 2, "ETH/USDT": 1}
    assert summary["deduplicated_rows_count"] == 3


def test_route_b_fetch_cli_aggregates_multiple_symbols_without_network_in_tests(tmp_path):
    from scripts.fetch_third_party_liquidation_history import main
    import json
    
    output_jsonl = tmp_path / "output.jsonl"
    summary_output = tmp_path / "summary.json"
    feasibility_output = tmp_path / "feasibility.json"
    
    def mock_fetch(symbol, from_ts_sec, to_ts_sec, interval="1hour", api_key=None):
        if symbol == "BTC/USDT":
            return [{"t": 1716800000, "l": 1000.0, "s": 500.0}], "api_ok_non_empty_rows"
        elif symbol == "ETH/USDT":
            return [{"t": 1716803600, "l": 2000.0, "s": 1500.0}], "api_ok_non_empty_rows"
        return [], "api_ok_empty_rows"

    with patch.dict(os.environ, {"COINALYZE_API_KEY": "test_key"}):
        with patch("scripts.fetch_third_party_liquidation_history.fetch_historical_liquidations", side_effect=mock_fetch):
            argv = [
                "--symbols", "BTC/USDT", "ETH/USDT",
                "--interval", "1hour",
                "--lookback-hours", "10",
                "--output-jsonl", str(output_jsonl),
                "--summary-output", str(summary_output),
                "--feasibility-output", str(feasibility_output),
            ]
            
            exit_code = main(argv)
            assert exit_code == 0
        
    assert output_jsonl.exists()
    assert summary_output.exists()
    assert feasibility_output.exists()
    
    with open(summary_output, "r") as f:
        summary_data = json.load(f)
        
    assert summary_data["vendor"] == "coinalyze"
    assert summary_data["route_b_status"] == "api_ok_non_empty_rows"
    assert summary_data["symbol_count"] == 2
    assert set(summary_data["symbols"]) == {"BTC/USDT", "ETH/USDT"}
    assert summary_data["row_count"] == 2
    assert summary_data["start_timestamp_ms"] == 1716800000000
    assert summary_data["end_timestamp_ms"] == 1716803600000
    assert summary_data["time_span_hours"] == 1
    assert summary_data["rows_per_symbol"] == {"BTC/USDT": 1, "ETH/USDT": 1}
    assert summary_data["coverage_quality"] == "historical_vendor_dataset"
    assert summary_data["deduplicated_rows_count"] == 2
    
    with open(feasibility_output, "r") as f:
        feasibility_data = json.load(f)
    assert "vendor_candidates" in feasibility_data
    
    with open(output_jsonl, "r") as f:
        jsonl_lines = [json.loads(line) for line in f if line.strip()]
        
    assert len(jsonl_lines) == 2
    for row in jsonl_lines:
        assert "symbol" in row
        assert "hour_bucket_ms" in row
        assert "total_liquidation_notional_1h_usdt" in row


def test_build_route_b_hourly_summary_reports_route_b_status():
    from scripts.fetch_third_party_liquidation_history import build_route_b_hourly_summary
    
    with patch.dict(os.environ, {}, clear=True):
        summary = build_route_b_hourly_summary([])
        assert summary["route_b_status"] == "no_api_key"
        
    with patch.dict(os.environ, {"COINALYZE_API_KEY": "test_key"}):
        summary = build_route_b_hourly_summary([])
        assert summary["route_b_status"] == "api_ok_empty_rows"
        
        summary_with_rows = build_route_b_hourly_summary([{"symbol": "BTC/USDT", "hour_bucket_ms": 1716800000000}])
        assert summary_with_rows["route_b_status"] == "api_ok_non_empty_rows"

    for status in ["api_auth_failed", "api_rate_limited", "no_api_key", "api_ok_empty_rows", "api_ok_non_empty_rows"]:
        summary = build_route_b_hourly_summary([], route_b_status=status)
        assert summary["route_b_status"] == status
