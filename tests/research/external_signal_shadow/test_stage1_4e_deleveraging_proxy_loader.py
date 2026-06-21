import json

import pytest

from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_loader import (
    get_data_source_semantics,
    load_json_or_jsonl_paths,
    normalize_funding_rows,
    normalize_oi_rows,
    normalize_price_rows,
)


@pytest.fixture
def temp_json_file(tmp_path):
    p = tmp_path / "test_data.json"
    data = [{"symbol": "BTCUSDT", "val": 123}]
    p.write_text(json.dumps(data))
    return str(p)

@pytest.fixture
def temp_jsonl_file(tmp_path):
    p = tmp_path / "test_data.jsonl"
    data = [{"symbol": "BTCUSDT", "val": 123}, {"symbol": "ETHUSDT", "val": 456}]
    p.write_text("\n".join(json.dumps(row) for row in data))
    return str(p)

def test_loader_supports_json_and_jsonl_inputs(temp_json_file, temp_jsonl_file):
    rows_json = load_json_or_jsonl_paths([temp_json_file])
    assert len(rows_json) == 1
    assert rows_json[0]["symbol"] == "BTCUSDT"

    rows_jsonl = load_json_or_jsonl_paths([temp_jsonl_file])
    assert len(rows_jsonl) == 2
    assert rows_jsonl[0]["symbol"] == "BTCUSDT"
    assert rows_jsonl[1]["symbol"] == "ETHUSDT"

def test_loader_normalizes_oi_timestamp_and_sum_open_interest():
    raw_oi = [
        {"symbol": "BTCUSDT", "timestamp": 1600000000000, "sumOpenInterest": "100.5", "sumOpenInterestValue": "5000000.0"},
        {"s": "ETHUSDT", "timestamp_ms": 1600000001000, "openInterest": 50.0, "sumOpenInterestValue": 250000.0},
        {"s": "SOLUSDT", "time": 1600000002000, "oi": 10.0},
    ]
    normalized = normalize_oi_rows(raw_oi)
    assert len(normalized) == 3
    assert normalized[0]["symbol"] == "BTCUSDT"
    assert normalized[0]["timestamp_ms"] == 1600000000000
    assert normalized[0]["sumOpenInterest"] == 100.5
    assert normalized[0]["sumOpenInterestValue"] == 5000000.0

    assert normalized[1]["symbol"] == "ETHUSDT"
    assert normalized[1]["timestamp_ms"] == 1600000001000
    assert normalized[1]["sumOpenInterest"] == 50.0
    assert normalized[1]["sumOpenInterestValue"] == 250000.0

    assert normalized[2]["symbol"] == "SOLUSDT"
    assert normalized[2]["timestamp_ms"] == 1600000002000
    assert normalized[2]["sumOpenInterest"] == 10.0
    assert normalized[2]["sumOpenInterestValue"] == 0.0

def test_loader_preserves_sum_open_interest_value_for_diagnostic_only():
    raw_oi = [
        {"symbol": "BTCUSDT", "timestamp": 1600000000000, "sumOpenInterest": 100.0, "sumOpenInterestValue": 12345.67}
    ]
    normalized = normalize_oi_rows(raw_oi)
    assert normalized[0]["sumOpenInterestValue"] == 12345.67

def test_loader_normalizes_price_open_high_low_close():
    raw_price = [
        {"symbol": "BTCUSDT", "bar_start_ms": 1600000000000, "open": "10.0", "high": 12.0, "low": 9.0, "close": "11.0", "quote_volume": "100000.0"},
        {"s": "ETHUSDT", "open_time": 1600000000000, "o": 20.0, "h": 22.0, "l": 18.0, "c": 21.0, "quote_volume": 50000.0},
    ]
    normalized = normalize_price_rows(raw_price)
    assert len(normalized) == 2
    assert normalized[0]["symbol"] == "BTCUSDT"
    assert normalized[0]["bar_start_ms"] == 1600000000000
    assert normalized[0]["open"] == 10.0
    assert normalized[0]["high"] == 12.0
    assert normalized[0]["low"] == 9.0
    assert normalized[0]["close"] == 11.0
    assert normalized[0]["quote_volume"] == 100000.0

    assert normalized[1]["symbol"] == "ETHUSDT"
    assert normalized[1]["bar_start_ms"] == 1600000000000
    assert normalized[1]["open"] == 20.0
    assert normalized[1]["high"] == 22.0
    assert normalized[1]["low"] == 18.0
    assert normalized[1]["close"] == 21.0
    assert normalized[1]["quote_volume"] == 50000.0

def test_loader_normalizes_funding_rows():
    raw_funding = [
        {"symbol": "BTCUSDT", "fundingTime": 1600000000000, "fundingRate": "0.0001"},
        {"s": "ETHUSDT", "funding_time_ms": 1600000000000, "funding_rate": 0.0002},
    ]
    normalized = normalize_funding_rows(raw_funding)
    assert len(normalized) == 2
    assert normalized[0]["symbol"] == "BTCUSDT"
    assert normalized[0]["funding_time_ms"] == 1600000000000
    assert normalized[0]["funding_rate"] == 0.0001

    assert normalized[1]["symbol"] == "ETHUSDT"
    assert normalized[1]["funding_time_ms"] == 1600000000000
    assert normalized[1]["funding_rate"] == 0.0002

def test_loader_outputs_source_and_source_quality_fields():
    semantics = get_data_source_semantics()
    assert semantics["oi_source"] == "binance_vision_metrics"
    assert semantics["oi_source_quality"] == "exchange_reported_hourly_snapshot"
    assert semantics["price_source"] == "binance_kline_normalized"
    assert semantics["price_source_quality"] == "close_price_proxy_not_fill_price"
    assert semantics["funding_source"] == "binance_settled_funding_rate"
    assert semantics["funding_source_quality"] == "settled_rate_not_realtime_prediction"
