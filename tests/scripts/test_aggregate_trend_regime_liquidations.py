import json

import pytest

from scripts.aggregate_trend_regime_liquidations import (
    aggregate_raw_to_hourly,
    load_raw_jsonl,
    write_hourly_jsonl,
)


@pytest.fixture()
def raw_jsonl(tmp_path):
    records = [
        # BTC SELL (long liquidated) in hour 10
        {
            "symbol": "BTC/USDT",
            "side": "SELL",
            "liquidation_side": "long_liquidation",
            "notional_usdt": 1_000_000.0,
            "timestamp_ms": 1716800000000,
            "hour_bucket_ms": 1716800000000 // 3_600_000 * 3_600_000,
        },
        # BTC BUY (short liquidated) in hour 10
        {
            "symbol": "BTC/USDT",
            "side": "BUY",
            "liquidation_side": "short_liquidation",
            "notional_usdt": 500_000.0,
            "timestamp_ms": 1716800001000,
            "hour_bucket_ms": 1716800001000 // 3_600_000 * 3_600_000,
        },
        # BTC SELL (long liquidated) in hour 11
        {
            "symbol": "BTC/USDT",
            "side": "SELL",
            "liquidation_side": "long_liquidation",
            "notional_usdt": 200_000.0,
            "timestamp_ms": 1716803600000,
            "hour_bucket_ms": 1716803600000 // 3_600_000 * 3_600_000,
        },
        # ETH long liquidated hour 10
        {
            "symbol": "ETH/USDT",
            "side": "SELL",
            "liquidation_side": "long_liquidation",
            "notional_usdt": 300_000.0,
            "timestamp_ms": 1716800002000,
            "hour_bucket_ms": 1716800002000 // 3_600_000 * 3_600_000,
        },
    ]
    path = tmp_path / "raw.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records))
    return str(path)


def test_aggregate_produces_one_row_per_symbol_per_hour(raw_jsonl):
    rows = aggregate_raw_to_hourly(load_raw_jsonl(raw_jsonl))
    # Expect 3 rows: BTC@10, BTC@11, ETH@10
    assert len(rows) == 3


def test_aggregate_splits_long_and_short_notional(raw_jsonl):
    rows = aggregate_raw_to_hourly(load_raw_jsonl(raw_jsonl))
    hour_10 = 1716800000000 // 3_600_000 * 3_600_000
    btc_10 = next(r for r in rows if r["symbol"] == "BTC/USDT" and r["hour_bucket_ms"] == hour_10)
    assert btc_10["long_liquidation_notional_1h_usdt"] == pytest.approx(1_000_000.0)
    assert btc_10["short_liquidation_notional_1h_usdt"] == pytest.approx(500_000.0)
    assert btc_10["liquidation_notional_1h_usdt"] == pytest.approx(1_500_000.0)
    assert btc_10["long_liquidation_event_count"] == 1
    assert btc_10["short_liquidation_event_count"] == 1


def test_aggregate_sets_semantics_field(raw_jsonl):
    rows = aggregate_raw_to_hourly(load_raw_jsonl(raw_jsonl))
    hour_10 = 1716800000000 // 3_600_000 * 3_600_000
    btc_10 = next(r for r in rows if r["symbol"] == "BTC/USDT" and r["hour_bucket_ms"] == hour_10)
    assert btc_10["liquidation_source"] == "binance_forceorder_ws"
    assert btc_10["source_quality"] == "self_collected_partial_history"
    assert btc_10["liquidation_notional_semantics"] == "partial_snapshot_lower_bound"
    assert btc_10["liquidation_bucket_semantics"] == "utc_hour_floor_of_row_timestamp"


def test_write_and_load_round_trip(raw_jsonl, tmp_path):
    rows = aggregate_raw_to_hourly(load_raw_jsonl(raw_jsonl))
    out_path = str(tmp_path / "hourly.jsonl")
    write_hourly_jsonl(rows, out_path)
    loaded = load_raw_jsonl(out_path)
    assert len(loaded) == 3


def test_aggregate_raw_to_hourly_floors_non_hour_bucket_ms():
    records = [
        {
            "symbol": "BTC/USDT",
            "hour_bucket_ms": 1716852300000,  # explicit non-hour-aligned bucket
            "notional_usdt": 34000.0,
            "liquidation_side": "long_liquidation",
        }
    ]

    rows = aggregate_raw_to_hourly(records)

    assert rows[0]["hour_bucket_ms"] == 1716850800000


def test_aggregate_raw_to_hourly_with_audit_prefers_event_timestamp_over_stale_hour_bucket_ms():
    from scripts.aggregate_trend_regime_liquidations import aggregate_raw_to_hourly_with_audit

    records = [
        {
            "symbol": "BTC/USDT",
            "timestamp_ms": 1780001100000,
            "hour_bucket_ms": 1716852300000,
            "notional_usdt": 34000.0,
            "liquidation_side": "long_liquidation",
        }
    ]

    rows, audit = aggregate_raw_to_hourly_with_audit(records)

    assert rows[0]["hour_bucket_ms"] == 1779998400000
    assert audit["bucket_event_time_mismatch_count"] == 1


def test_aggregate_raw_to_hourly_with_audit_skips_missing_all_timestamps():
    from scripts.aggregate_trend_regime_liquidations import aggregate_raw_to_hourly_with_audit

    records = [
        {
            "symbol": "BTC/USDT",
            "notional_usdt": 34000.0,
            "liquidation_side": "long_liquidation",
        }
    ]

    rows, audit = aggregate_raw_to_hourly_with_audit(records)

    assert rows == []
    assert audit["missing_timestamp_count"] == 1


def test_aggregate_raw_to_bucket_rejects_unsupported_bucket():
    from scripts.aggregate_trend_regime_liquidations import aggregate_raw_to_bucket

    with pytest.raises(ValueError):
        aggregate_raw_to_bucket([], bucket="10m")


def test_aggregate_prefers_event_time_over_stale_hour_bucket():
    from scripts.aggregate_trend_regime_liquidations import aggregate_raw_to_bucket

    record_with_wrong_hour_bucket = {
        "symbol": "BTC/USDT",
        "event_time_ms": 1780000000000 + 5 * 60 * 1000,  # 1780000300000
        "hour_bucket_ms": 1716852300000,
        "notional_usdt": 34000.0,
        "liquidation_side": "long_liquidation",
    }
    # For 1h bucket, M+5m falls into 1780000000000 (computed from event_time_ms)
    rows = aggregate_raw_to_bucket([record_with_wrong_hour_bucket], bucket="1h")
    assert len(rows) == 1
    assert rows[0]["hour_bucket_ms"] == 1779998400000


def test_aggregate_raw_to_bucket_deduplicates_by_event_id():
    from scripts.aggregate_trend_regime_liquidations import aggregate_raw_to_bucket

    record = {
        "event_id": "evt_1",
        "symbol": "BTC/USDT",
        "event_time_ms": 1780000000000,
        "notional_usdt": 100000.0,
        "liquidation_side": "long_liquidation",
    }
    duplicate_of_record = {
        "event_id": "evt_1",
        "symbol": "BTC/USDT",
        "event_time_ms": 1780000000000,
        "notional_usdt": 100000.0,
        "liquidation_side": "long_liquidation",
    }
    rows = aggregate_raw_to_bucket([record, duplicate_of_record], bucket="1m")
    assert len(rows) == 1
    assert rows[0]["event_count_1m"] == 1
    assert rows[0]["total_liquidation_notional_1m_usdt"] == 100000.0


def test_aggregate_zero_fills_empty_1m_buckets_when_requested():
    from scripts.aggregate_trend_regime_liquidations import aggregate_raw_to_bucket

    records = [
        {
            "event_id": "evt_1",
            "symbol": "BTC/USDT",
            "event_time_ms": 1780000200000,  # Minute 0
            "notional_usdt": 100000.0,
            "liquidation_side": "long_liquidation",
        },
        {
            "event_id": "evt_2",
            "symbol": "BTC/USDT",
            "event_time_ms": 1780000320000,  # Minute 2
            "notional_usdt": 50000.0,
            "liquidation_side": "short_liquidation",
        },
    ]
    # We aggregate from Minute 0 to Minute 3. There should be 4 buckets: Minute 0, 1, 2, 3.
    # Minute 1 and 3 are empty and should be zero-filled.
    start_ms = 1780000200000
    end_ms = 1780000380000
    rows = aggregate_raw_to_bucket(
        records,
        bucket="1m",
        fill_empty_buckets=True,
        start_ms=start_ms,
        end_ms=end_ms,
        symbols=["BTC/USDT"],
    )
    # Total 4 minute bars expected
    assert len(rows) == 4

    # Minute 0: contains event
    m0 = next(r for r in rows if r["bar_start_ms"] == start_ms)
    assert m0["total_liquidation_notional_1m_usdt"] == 100000.0
    assert m0.get("filled_empty_bucket", False) is False

    # Minute 1: empty, should be zero-filled
    m1 = next(r for r in rows if r["bar_start_ms"] == start_ms + 60000)
    assert m1["total_liquidation_notional_1m_usdt"] == 0.0
    assert m1["long_liquidation_notional_1m_usdt"] == 0.0
    assert m1["short_liquidation_notional_1m_usdt"] == 0.0
    assert m1["event_count_1m"] == 0
    assert m1["filled_empty_bucket"] is True

    # Minute 2: contains event
    m2 = next(r for r in rows if r["bar_start_ms"] == start_ms + 120000)
    assert m2["total_liquidation_notional_1m_usdt"] == 50000.0
    assert m2.get("filled_empty_bucket", False) is False

    # Minute 3: empty, should be zero-filled
    m3 = next(r for r in rows if r["bar_start_ms"] == start_ms + 180000)
    assert m3["total_liquidation_notional_1m_usdt"] == 0.0
    assert m3["filled_empty_bucket"] is True


def test_aggregate_zero_fills_empty_5m_buckets_when_requested():
    from scripts.aggregate_trend_regime_liquidations import aggregate_raw_to_bucket

    records = [
        {
            "event_id": "evt_1",
            "symbol": "BTC/USDT",
            "event_time_ms": 1780000200000,  # 5m Bar 0
            "notional_usdt": 100000.0,
            "liquidation_side": "long_liquidation",
        }
    ]
    # We ask for a range spanning two 5-minute bars: Bar 0 and Bar 1.
    start_ms = 1780000200000
    end_ms = 1780000500000  # 5 minutes later
    rows = aggregate_raw_to_bucket(
        records,
        bucket="5m",
        fill_empty_buckets=True,
        start_ms=start_ms,
        end_ms=end_ms,
        symbols=["BTC/USDT"],
    )
    assert len(rows) == 2
    bar0 = next(r for r in rows if r["bar_start_ms"] == start_ms)
    assert bar0["total_liquidation_notional_5m_usdt"] == 100000.0

    bar1 = next(r for r in rows if r["bar_start_ms"] == start_ms + 300000)
    assert bar1["total_liquidation_notional_5m_usdt"] == 0.0
    assert bar1["event_count_5m"] == 0
    assert bar1["filled_empty_bucket"] is True


def test_parse_args_handles_zero_fill_options():
    from scripts.aggregate_trend_regime_liquidations import parse_args

    args = parse_args(
        [
            "--fill-empty-buckets",
            "--start-ms",
            "1780000200000",
            "--end-ms",
            "1780000380000",
            "--symbols",
            "BTC/USDT",
            "ETH/USDT",
        ]
    )
    assert args.fill_empty_buckets is True
    assert args.start_ms == 1780000200000
    assert args.end_ms == 1780000380000
    assert args.symbols == ["BTC/USDT", "ETH/USDT"]
