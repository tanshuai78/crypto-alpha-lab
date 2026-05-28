import os
from unittest.mock import patch
from typing import Any

from scripts.fetch_third_party_liquidation_history import (
    fetch_historical_liquidations,
    load_feasibility_audit,
    normalize_coinglass_payload,
)


def test_vendor_feasibility_summary_uses_fixture_not_real_network():
    summary = load_feasibility_audit()
    assert "vendor_candidates" in summary
    candidates = summary["vendor_candidates"]
    assert len(candidates) > 0
    coinglass = next(c for c in candidates if c["vendor"] == "coinglass")
    assert coinglass["requires_paid_plan"] is True
    assert coinglass["can_support_replay"] in [True, False]


def test_missing_api_key_degrades_gracefully():
    # Clear environment variables to simulate missing key
    with patch.dict(os.environ, {}, clear=True):
        res = fetch_historical_liquidations(symbol="BTC/USDT", start_ms=0, end_ms=0)
        assert res == []


def test_third_party_payload_is_normalized_to_forceorder_hourly_schema():
    raw_payload = [
        {
            "time": 1716800000000,
            "buyQty": 10.0,
            "sellQty": 20.0,
            "buyVolUsd": 300000.0,
            "sellVolUsd": 600000.0,
        },
    ]
    normalized = normalize_coinglass_payload(raw_payload, symbol="BTC/USDT")
    assert len(normalized) == 1
    row = normalized[0]
    assert row["symbol"] == "BTC/USDT"
    assert row["long_liquidation_notional_1h_usdt"] == 600000.0
    assert row["short_liquidation_notional_1h_usdt"] == 300000.0
    assert row["liquidation_source"] == "third_party_historical"
    assert row["liquidation_source_quality"] == "historical_vendor_dataset"
    assert row["vendor_name"] == "coinglass"
    assert row["vendor_granularity"] == "1h"
