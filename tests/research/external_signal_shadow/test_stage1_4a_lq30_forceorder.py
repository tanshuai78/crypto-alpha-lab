from research.external_signal_shadow.stage1_4a_lq30_forceorder import (
    load_forceorder_jsonl_files,
    normalize_derivatives_symbol,
    normalize_forceorder_row,
    parse_forceorder_rows,
)


def test_normalize_derivatives_symbol():
    assert normalize_derivatives_symbol("BTCUSDT") == "BTCUSDT"
    assert normalize_derivatives_symbol("BTC/USDT") == "BTCUSDT"
    assert normalize_derivatives_symbol("BTC/USDT:USDT") == "BTCUSDT"
    assert normalize_derivatives_symbol("ETH/USDT:USDT") == "ETHUSDT"
    assert normalize_derivatives_symbol("btcusdt") == "BTCUSDT"
    assert normalize_derivatives_symbol(None) is None


def test_normalize_flat_forceorder_row():
    row = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "price": "65000",
        "origQty": "0.25",
        "time": 1710000000000,
    }
    normalized = normalize_forceorder_row(row)
    assert normalized is not None
    assert normalized["symbol"] == "BTCUSDT"
    assert normalized["liquidation_side"] == "long_liquidation"
    assert normalized["price"] == 65000.0
    assert normalized["quantity"] == 0.25
    assert normalized["timestamp_ms"] == 1710000000000
    assert normalized["notional_usd"] == 16250.0
    assert normalized["notional_conversion_quality"] == "estimated_from_price_qty"
    assert normalized["notional_is_lower_bound"] is True
    assert normalized["schema_kind"] == "flat_forceorder"


def test_normalize_local_forceorder_archive_row():
    row = {
        "schema_version": 1,
        "source": "binance_forceorder_ws",
        "symbol": "BTC/USDT",
        "exchange_symbol": "BTCUSDT",
        "side": "SELL",
        "price": 73856.2,
        "quantity": 0.029,
        "timestamp_ms": 1780218439524,
    }
    normalized = normalize_forceorder_row(row)
    assert normalized is not None
    assert normalized["symbol"] == "BTCUSDT"
    assert normalized["liquidation_side"] == "long_liquidation"
    assert normalized["quantity"] == 0.029
    assert normalized["timestamp_ms"] == 1780218439524
    assert normalized["notional_usd"] == 73856.2 * 0.029


def test_normalize_nested_binance_forceorder_row():
    row = {
        "E": 1710000005000,
        "o": {
            "s": "ETHUSDT",
            "S": "BUY",
            "p": "3000",
            "q": "2",
            "T": 1710000001000,
        }
    }
    normalized = normalize_forceorder_row(row)
    assert normalized is not None
    assert normalized["symbol"] == "ETHUSDT"
    assert normalized["liquidation_side"] == "short_liquidation"
    assert normalized["price"] == 3000.0
    assert normalized["quantity"] == 2.0
    assert normalized["timestamp_ms"] == 1710000001000
    assert normalized["schema_kind"] == "nested_binance_forceorder"


def test_nested_forceorder_uses_E_if_o_T_missing():
    row = {
        "E": 1710000005000,
        "o": {
            "s": "ETHUSDT",
            "S": "BUY",
            "p": "3000",
            "q": "2",
        }
    }
    normalized = normalize_forceorder_row(row)
    assert normalized is not None
    assert normalized["timestamp_ms"] == 1710000005000


def test_parse_forceorder_rows():
    rows = [
        # Valid
        {"symbol": "BTCUSDT", "side": "SELL", "price": "65000", "origQty": "0.1", "time": 1710000000000},
        # Invalid fields
        {"symbol": "BTCUSDT", "side": "UNKNOWN", "price": "65000", "origQty": "0.1", "time": 1710000000000},
        # Unknown schema
        {"something": "else"},
        # Another valid for a non-expected symbol
        {"symbol": "SOLUSDT", "side": "BUY", "price": "150", "origQty": "1", "time": 1710000002000},
    ]
    result = parse_forceorder_rows(rows, {"BTCUSDT"})
    assert result["parsed_row_count"] == 1
    assert result["unknown_schema_count"] == 1
    assert result["missing_required_field_count"] == 1
    assert len(result["rows"]) == 1
    assert result["rows"][0]["symbol"] == "BTCUSDT"


def test_load_forceorder_jsonl_files(tmp_path):
    archive1 = tmp_path / "force_orders_1.jsonl"
    archive1.write_text(
        '{"symbol":"BTCUSDT","side":"SELL","price":"65000","origQty":"0.1","time":1710000000000}\n'
        '{"symbol":"BTCUSDT","side":"SELL","price":"65000","origQty":"0.1","time":1710000000000}\n'  # duplicate
        '{"symbol":"BTCUSDT","side":"BUY","price":"65100","origQty":"0.2","time":1710000001000}\n',
        encoding="utf-8",
    )

    archive2 = tmp_path / "force_orders_2.jsonl"
    archive2.write_text(
        'not-json\n'
        '{"symbol":"ETHUSDT","side":"BUY","price":"3000","origQty":"1.5","time":1710000002000}\n',
        encoding="utf-8",
    )

    result = load_forceorder_jsonl_files([str(archive1), str(archive2)])
    assert result["raw_line_count"] == 5
    assert result["invalid_json_line_count"] == 1
    assert result["invalid_json_line_ratio"] == 0.2
    assert result["duplicate_event_count"] == 1
    assert result["deduped_row_count"] == 3
    assert len(result["loaded_rows"]) == 3
    assert len(result["quarantined_invalid_lines"]) == 1
    assert result["quarantined_invalid_lines"][0] == "not-json"
