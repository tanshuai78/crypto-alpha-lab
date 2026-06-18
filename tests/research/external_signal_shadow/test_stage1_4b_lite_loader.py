import json

import pytest

from research.external_signal_shadow.stage1_4b_lite_loader import (
    load_funding_rows,
    load_oi_rows,
    load_price_rows,
)


def test_load_funding_rows_json(tmp_path):
    data = [
        {"symbol": "BTCUSDT", "fundingTime": 1000, "fundingRate": 0.0001},
        {"symbol": "ETHUSDT", "fundingTime": 2000, "fundingRate": "0.0002"}, # string rate should parse
    ]
    p = tmp_path / "funding.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    rows = load_funding_rows(str(p))
    assert len(rows) == 2
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["fundingTime"] == 1000
    assert rows[0]["fundingRate"] == 0.0001
    assert rows[1]["symbol"] == "ETHUSDT"
    assert rows[1]["fundingTime"] == 2000
    assert rows[1]["fundingRate"] == 0.0002


def test_load_funding_rows_jsonl(tmp_path):
    lines = (
        '{"s": "BTCUSDT", "t": 1000, "r": 0.0001}\n'
        '{"symbol": "ETHUSDT", "fundingTime": 2000, "fundingRate": 0.0002}\n'
    )
    p = tmp_path / "funding.jsonl"
    p.write_text(lines, encoding="utf-8")

    rows = load_funding_rows(str(p))
    assert len(rows) == 2
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["fundingTime"] == 1000
    assert rows[0]["fundingRate"] == 0.0001
    assert rows[1]["symbol"] == "ETHUSDT"


def test_load_funding_invalid(tmp_path):
    p = tmp_path / "invalid.json"
    p.write_text(json.dumps([{"symbol": "BTCUSDT"}]), encoding="utf-8") # missing fundingTime/fundingRate
    with pytest.raises(ValueError):
        load_funding_rows(str(p))


def test_load_oi_rows_json(tmp_path):
    data = [
        {"symbol": "BTCUSDT", "timestamp": 1000, "sumOpenInterest": 100.5},
        {"s": "ETHUSDT", "t": 2000, "oi": "200.5"},
    ]
    p = tmp_path / "oi.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    rows = load_oi_rows(str(p))
    assert len(rows) == 2
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["timestamp_ms"] == 1000
    assert rows[0]["sumOpenInterest"] == 100.5
    assert rows[1]["symbol"] == "ETHUSDT"
    assert rows[1]["timestamp_ms"] == 2000
    assert rows[1]["sumOpenInterest"] == 200.5


def test_load_oi_invalid(tmp_path):
    p = tmp_path / "invalid.json"
    p.write_text(json.dumps([{"symbol": "BTCUSDT", "timestamp": 1000}]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_oi_rows(str(p))


def test_load_price_rows_json(tmp_path):
    data = [
        {"symbol": "BTCUSDT", "open_time": 1000, "open": 49000.0, "close": 50000.0, "quote_volume": 1000000.0},
        {"s": "ETHUSDT", "t": 2000, "o": "2950.0", "c": "3000.0", "v": "500000.0"},
    ]
    p = tmp_path / "price.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    rows = load_price_rows(str(p))
    assert len(rows) == 2
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["bar_start_ms"] == 1000
    assert rows[0]["open_price"] == 49000.0
    assert rows[0]["close_price"] == 50000.0
    assert rows[0]["quote_volume"] == 1000000.0
    assert rows[1]["symbol"] == "ETHUSDT"
    assert rows[1]["bar_start_ms"] == 2000
    assert rows[1]["open_price"] == 2950.0
    assert rows[1]["close_price"] == 3000.0
    assert rows[1]["quote_volume"] == 500000.0


def test_load_price_rows_list_format(tmp_path):
    # kline format: [timestamp, open, high, low, close, volume]
    data = [
        [1000, 49000.0, 51000.0, 48000.0, 50000.0, 20.0],
        [2000, 3000.0, 3100.0, 2900.0, 3050.0, 100.0],
    ]
    p = tmp_path / "price_list.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    # When loading lists, symbol must be supplied or determined
    rows = load_price_rows(str(p), default_symbol="BTCUSDT")
    assert len(rows) == 2
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["bar_start_ms"] == 1000
    assert rows[0]["open_price"] == 49000.0
    assert rows[0]["close_price"] == 50000.0
    assert rows[0]["quote_volume"] == 20.0 # wait, quote volume or base volume? List klines standard CCXT has volume.
    # In list klines, index 5 is volume. If the code requires quote_volume, we can treat volume as quote_volume,
    # or if we need quote_volume specifically, wait, kline index 5 is base volume, index 7 is quote asset volume if standard binance.
    # But CCXT standard only returns [time, open, high, low, close, volume].
    # Let's map volume to quote_volume or base volume. Let's make sure it handles both list index 5 or index 7.
    # Let's implement it robustly.
