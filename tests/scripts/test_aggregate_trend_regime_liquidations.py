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
            "liquidation_side": "long",
            "notional_usdt": 1_000_000.0,
            "timestamp_ms": 1716800000000,
            "hour_bucket_utc": "2024-05-27T10:00",
        },
        # BTC BUY (short liquidated) in hour 10
        {
            "symbol": "BTC/USDT",
            "side": "BUY",
            "liquidation_side": "short",
            "notional_usdt": 500_000.0,
            "timestamp_ms": 1716800001000,
            "hour_bucket_utc": "2024-05-27T10:00",
        },
        # BTC SELL (long liquidated) in hour 11
        {
            "symbol": "BTC/USDT",
            "side": "SELL",
            "liquidation_side": "long",
            "notional_usdt": 200_000.0,
            "timestamp_ms": 1716803600000,
            "hour_bucket_utc": "2024-05-27T11:00",
        },
        # ETH long liquidated hour 10
        {
            "symbol": "ETH/USDT",
            "side": "SELL",
            "liquidation_side": "long",
            "notional_usdt": 300_000.0,
            "timestamp_ms": 1716800002000,
            "hour_bucket_utc": "2024-05-27T10:00",
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
    btc_10 = next(
        r for r in rows if r["symbol"] == "BTC/USDT" and r["hour_bucket_utc"] == "2024-05-27T10:00"
    )
    assert btc_10["long_liquidation_notional_usdt"] == pytest.approx(1_000_000.0)
    assert btc_10["short_liquidation_notional_usdt"] == pytest.approx(500_000.0)
    assert btc_10["total_liquidation_notional_usdt"] == pytest.approx(1_500_000.0)
    assert btc_10["dominant_side"] == "long"  # long > short


def test_aggregate_sets_semantics_field(raw_jsonl):
    rows = aggregate_raw_to_hourly(load_raw_jsonl(raw_jsonl))
    btc_10 = next(
        r for r in rows if r["symbol"] == "BTC/USDT" and r["hour_bucket_utc"] == "2024-05-27T10:00"
    )
    assert "semantics" in btc_10
    assert btc_10["semantics"] == "forceOrder_aggregated_from_local_ws"


def test_write_and_load_round_trip(raw_jsonl, tmp_path):
    rows = aggregate_raw_to_hourly(load_raw_jsonl(raw_jsonl))
    out_path = str(tmp_path / "hourly.jsonl")
    write_hourly_jsonl(rows, out_path)
    loaded = load_raw_jsonl(out_path)
    assert len(loaded) == 3
