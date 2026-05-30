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
