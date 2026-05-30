import os
from unittest.mock import patch

from scripts.fetch_liquidation_only_5m_history import main
from src.research.liquidation_only_5m.coinalyze_5m import (
    normalize_coinalyze_payload_5m,
    normalize_interval,
)


def test_normalize_interval_5m():
    assert normalize_interval("5m") == "5min"
    assert normalize_interval("5min") == "5min"


def test_normalize_coinalyze_payload_5m_keys():
    raw_payload = [
        {
            "symbol": "BTCUSDT_PERP.A",
            "history": [
                {
                    "t": 1716800100,  # seconds
                    "l": 50000.0,
                    "s": 30000.0,
                }
            ],
        }
    ]

    normalized = normalize_coinalyze_payload_5m(raw_payload, symbol="BTC/USDT")
    assert len(normalized) == 1
    row = normalized[0]

    assert row["symbol"] == "BTC/USDT"
    # aligned to 5m bucket (1716800100 is exactly 1716800100 // 300 * 300 = 1716800100)
    # 1716800100 * 1000 = 1716800100000
    assert row["bar_start_ms"] == 1716800100000
    assert row["long_liquidation_notional_5m_usdt"] == 50000.0
    assert row["short_liquidation_notional_5m_usdt"] == 30000.0
    assert row["total_liquidation_notional_5m_usdt"] == 80000.0
    assert row["liquidation_source"] == "third_party_historical"


def test_normalize_aligns_to_5m_bucket_boundaries():
    # 1716800123 seconds is 1716800123000 ms, should be aligned down to 1716800100000 ms (divisible by 300,000 ms)
    raw_payload = [
        {
            "t": 1716800123,
            "l": 100.0,
            "s": 200.0,
        }
    ]
    normalized = normalize_coinalyze_payload_5m(raw_payload, symbol="BTC/USDT")
    assert len(normalized) == 1
    assert normalized[0]["bar_start_ms"] == 1716800100000  # 1716800100 seconds


def test_fetch_5m_history_cli_runs(tmp_path):
    output_jsonl = tmp_path / "output_5m.jsonl"
    summary_output = tmp_path / "summary_5m.json"

    def mock_fetch(symbol, from_ts_sec, to_ts_sec, interval="5min", api_key=None):
        return [
            {
                "symbol": "BTCUSDT_PERP.A",
                "history": [{"t": 1716800100, "l": 1000.0, "s": 500.0}],
            }
        ], "api_ok_non_empty_rows"

    with patch.dict(os.environ, {"COINALYZE_API_KEY": "test_key"}):
        with patch(
            "scripts.fetch_liquidation_only_5m_history.fetch_historical_liquidations",
            side_effect=mock_fetch,
        ):
            argv = [
                "--symbols",
                "BTC/USDT",
                "--lookback-days",
                "2",
                "--output-jsonl",
                str(output_jsonl),
                "--summary-output",
                str(summary_output),
            ]
            exit_code = main(argv)
            assert exit_code == 0

    assert output_jsonl.exists()
    assert summary_output.exists()
