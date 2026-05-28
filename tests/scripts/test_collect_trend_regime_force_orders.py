import json

from scripts.collect_trend_regime_force_orders import (
    RollingLiquidationAccumulator,
    build_force_order_raw_record,
    build_force_order_stream_url,
    parse_force_order_notional_event,
    should_stop,
    write_liquidation_cache_json,
)


def test_build_force_order_stream_url_contains_all_symbols():
    url = build_force_order_stream_url(("BTC/USDT", "DOGE/USDT"))

    assert url.startswith("wss://fstream.binance.com/stream?streams=")
    assert "btcusdt@forceOrder" in url
    assert "dogeusdt@forceOrder" in url


def test_parse_force_order_notional_event_from_combined_stream_payload():
    message = {
        "stream": "btcusdt@forceOrder",
        "data": {
            "e": "forceOrder",
            "E": 1710000000123,
            "o": {
                "s": "BTCUSDT",
                "ap": "39021.00",
                "z": "0.288",
            },
        },
    }

    parsed = parse_force_order_notional_event(message)

    assert parsed is not None
    assert parsed["symbol"] == "BTC/USDT"
    assert parsed["timestamp_ms"] == 1710000000123
    assert parsed["notional_usdt"] == 11238.048


def test_parse_force_order_notional_event_returns_none_for_non_force_order():
    message = {"stream": "btcusdt@aggTrade", "data": {"e": "aggTrade"}}

    parsed = parse_force_order_notional_event(message)

    assert parsed is None


def test_rolling_liquidation_accumulator_prunes_out_of_window():
    acc = RollingLiquidationAccumulator(window_ms=3_600_000)
    acc.add_event("BTCUSDT", event_time_ms=1_000, notional_usdt=10.0)
    acc.add_event("BTCUSDT", event_time_ms=2_000, notional_usdt=20.0)

    # now moves beyond first event by > 1h, first event should be pruned
    totals = acc.snapshot_totals(now_ms=3_601_001)

    assert totals["BTCUSDT"] == 20.0


def test_write_liquidation_cache_json_writes_plain_symbol_map(tmp_path):
    output = tmp_path / "trend_regime_liquidation_cache.json"

    write_liquidation_cache_json(output, {"BTCUSDT": 10.5, "DOGEUSDT": 22.0})

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == {"BTCUSDT": 10.5, "DOGEUSDT": 22.0}


def test_should_stop_handles_finite_and_infinite_runtime():
    assert should_stop(start_ts=100.0, now_ts=102.0, max_seconds=1) is True
    assert should_stop(start_ts=100.0, now_ts=100.5, max_seconds=1) is False
    assert should_stop(start_ts=100.0, now_ts=500.0, max_seconds=0) is False


def test_parse_force_order_event_returns_dict_with_side():
    """parse_force_order_notional_event must return a dict with 'side' key."""
    raw = {
        "o": {
            "s": "BTCUSDT",
            "S": "SELL",  # SELL forced = long position liquidated
            "q": "0.5",
            "ap": "60000",
            "T": 1716800000000,
        }
    }
    result = parse_force_order_notional_event(raw)
    assert result is not None
    assert "side" in result
    assert "notional_usdt" in result
    assert "liquidation_side" in result
    # SELL forced order = long liquidated
    assert result["side"] == "SELL"
    assert result["liquidation_side"] == "long"


def test_parse_force_order_buy_side_is_short_liquidation():
    """BUY forced order = short position was liquidated."""
    raw = {
        "o": {
            "s": "ETHUSDT",
            "S": "BUY",
            "q": "10",
            "ap": "3000",
            "T": 1716800000000,
        }
    }
    result = parse_force_order_notional_event(raw)
    assert result is not None
    assert result["side"] == "BUY"
    assert result["liquidation_side"] == "short"


def test_build_force_order_raw_record_has_required_fields():
    """build_force_order_raw_record must return dict with all required fields for JSONL append."""
    parsed = {
        "symbol": "BTC/USDT",
        "side": "SELL",
        "liquidation_side": "long",
        "notional_usdt": 30000.0,
        "timestamp_ms": 1716800000000,
    }
    record = build_force_order_raw_record(parsed)
    required = {
        "symbol",
        "side",
        "liquidation_side",
        "notional_usdt",
        "timestamp_ms",
        "hour_bucket_utc",
    }
    assert required.issubset(set(record.keys()))
    # hour_bucket_utc must be ISO-format string like '2024-05-27T10:00'
    assert "T" in record["hour_bucket_utc"]
    assert record["symbol"] == "BTC/USDT"
