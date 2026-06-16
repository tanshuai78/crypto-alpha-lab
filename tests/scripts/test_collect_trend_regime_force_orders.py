import json

import pytest

from scripts.collect_trend_regime_force_orders import (
    RollingLiquidationAccumulator,
    build_force_order_raw_record,
    build_force_order_stream_url,
    parse_force_order_notional_event,
    rotate_force_order_raw_archive_if_needed,
    should_stop,
    write_liquidation_cache_json,
)


def test_build_force_order_stream_url_contains_all_symbols():
    url = build_force_order_stream_url(("BTC/USDT", "DOGE/USDT"))

    assert url.startswith("wss://fstream.binance.com/market/stream?streams=")
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
    assert "quantity" in result
    assert "average_price" in result
    assert "order_trade_time_ms" in result
    assert "source" in result
    assert "source_quality" in result
    assert "liquidation_notional_semantics" in result
    # SELL forced order = long liquidated
    assert result["side"] == "SELL"
    assert result["liquidation_side"] == "long_liquidation"


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
    assert result["liquidation_side"] == "short_liquidation"


def test_build_force_order_raw_record_has_required_fields():
    """build_force_order_raw_record must return dict with all required fields for JSONL append."""
    parsed = {
        "symbol": "BTC/USDT",
        "side": "SELL",
        "liquidation_side": "long_liquidation",
        "quantity": 0.5,
        "average_price": 60000.0,
        "notional_usdt": 30000.0,
        "timestamp_ms": 1716800000000,
        "order_trade_time_ms": 1716800000000,
        "source": "binance_forceorder_ws",
        "source_quality": "self_collected_partial_history",
        "liquidation_notional_semantics": "partial_snapshot_lower_bound",
    }
    record = build_force_order_raw_record(parsed)
    required = {
        "symbol",
        "side",
        "liquidation_side",
        "quantity",
        "average_price",
        "notional_usdt",
        "timestamp_ms",
        "order_trade_time_ms",
        "hour_bucket_ms",
        "hour_bucket_utc",
        "source",
        "source_quality",
        "liquidation_notional_semantics",
        "liquidation_bucket_semantics",
    }
    assert required.issubset(set(record.keys()))
    # hour_bucket_utc must be ISO-format string like '2024-05-27T10:00'
    assert "T" in record["hour_bucket_utc"]
    assert record["symbol"] == "BTC/USDT"
    assert record["liquidation_notional_semantics"] == "partial_snapshot_lower_bound"


def test_forceorder_raw_event_contains_required_research_fields():
    sample_payload = {
        "stream": "btcusdt@forceOrder",
        "data": {
            "e": "forceOrder",
            "E": 1716800000123,
            "o": {
                "s": "BTCUSDT",
                "S": "SELL",
                "ap": "60000.00",
                "q": "0.500",
                "z": "0.500",
                "T": 1716800000000,
            },
        },
    }
    parsed = parse_force_order_notional_event(sample_payload)
    assert parsed is not None
    record = build_force_order_raw_record(parsed, schema_version=1)

    REQUIRED_RAW_KEYS = {
        "schema_version",
        "source",
        "event_id",
        "symbol",
        "exchange_symbol",
        "event_time_ms",
        "trade_time_ms",
        "side",
        "liquidated_position_side",
        "liquidation_side",
        "price",
        "quantity",
        "notional_usdt",
        "raw_payload",
    }
    assert REQUIRED_RAW_KEYS.issubset(set(record.keys()))
    assert record["schema_version"] == 1
    assert record["symbol"] == "BTC/USDT"
    assert record["exchange_symbol"] == "BTCUSDT"
    assert record["event_time_ms"] == 1716800000123
    assert record["trade_time_ms"] == 1716800000000
    assert record["side"] == "SELL"
    assert record["liquidated_position_side"] == "long"
    assert record["price"] == 60000.0
    assert record["quantity"] == 0.5
    assert record["notional_usdt"] == 30000.0
    assert record["raw_payload"] == sample_payload


def test_raw_event_id_is_stable_for_same_exchange_event():
    sample_payload = {
        "stream": "btcusdt@forceOrder",
        "data": {
            "e": "forceOrder",
            "E": 1716800000123,
            "o": {
                "s": "BTCUSDT",
                "S": "SELL",
                "ap": "60000.00",
                "q": "0.500",
                "z": "0.500",
                "T": 1716800000000,
            },
        },
    }
    parsed_a = parse_force_order_notional_event(sample_payload)
    parsed_b = parse_force_order_notional_event(sample_payload)

    record_a = build_force_order_raw_record(parsed_a)
    record_b = build_force_order_raw_record(parsed_b)

    assert record_a["event_id"] == record_b["event_id"]
    assert record_a["event_id"] == "binance_forceorder_ws|BTC/USDT|1716800000123|1716800000000|SELL|60000.0|0.5"


def test_parse_args_accepts_raw_fsync_and_schema_version():
    from scripts.collect_trend_regime_force_orders import parse_args
    args = parse_args(["--raw-output", "x.jsonl", "--fsync-raw", "--raw-schema-version", "1"])
    assert args.fsync_raw is True
    assert args.raw_schema_version == 1


def test_parse_args_help_marks_raw_as_primary_archive(capsys):
    from scripts.collect_trend_regime_force_orders import parse_args

    with pytest.raises(SystemExit):
        parse_args(["--help"])

    captured = capsys.readouterr()
    assert "primary append-only archive" in captured.out
    assert "legacy compatibility cache" in captured.out


def test_rotate_force_order_raw_archive_if_needed_moves_full_raw_and_leaves_fresh_file(tmp_path):
    raw_path = tmp_path / "trend_regime_force_orders_raw.jsonl"
    backup_dir = tmp_path / "backup"
    payload = {"event_id": "evt-1", "symbol": "BTC/USDT"}
    raw_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = rotate_force_order_raw_archive_if_needed(
        raw_path,
        backup_dir=backup_dir,
        max_bytes=1,
    )

    assert result["rotated"] is True
    assert result["raw_path"] == str(raw_path)
    assert result["backup_dir"] == str(backup_dir)
    assert raw_path.exists()
    assert raw_path.read_text(encoding="utf-8") == ""
    backup_files = list(backup_dir.glob("trend_regime_force_orders_raw_*.jsonl"))
    assert len(backup_files) == 1
    assert backup_files[0].read_text(encoding="utf-8") == json.dumps(payload) + "\n"
    checksum_files = list(backup_dir.glob("trend_regime_force_orders_raw_*.jsonl.sha256"))
    assert len(checksum_files) == 1
    assert checksum_files[0].read_text(encoding="utf-8").strip().endswith(
        f"  {backup_files[0].name}"
    )


def test_rotate_force_order_raw_archive_if_needed_is_noop_below_threshold(tmp_path):
    raw_path = tmp_path / "trend_regime_force_orders_raw.jsonl"
    backup_dir = tmp_path / "backup"
    raw_path.write_text(json.dumps({"event_id": "evt-1"}) + "\n", encoding="utf-8")

    result = rotate_force_order_raw_archive_if_needed(
        raw_path,
        backup_dir=backup_dir,
        max_bytes=10_000,
    )

    assert result["rotated"] is False
    assert result["reason"] == "below_threshold"
    assert raw_path.exists()
    assert backup_dir.exists() is False
