import json

from scripts.build_liquidation_only_5m_dataset import build_aligned_dataset, main


def test_build_aligned_dataset_aligns_correctly():
    # Setup test rows
    price_rows = [
        {
            "symbol": "BTC/USDT",
            "timestamp_ms": 1716800100000,
            "open": 60000.0,
            "high": 60100.0,
            "low": 59900.0,
            "close": 60050.0,
        },
        {
            "symbol": "BTC/USDT",
            "timestamp_ms": 1716800400000,  # +5 min (300,000 ms)
            "open": 60050.0,
            "high": 60200.0,
            "low": 60000.0,
            "close": 60150.0,
        },
    ]

    liq_rows = [
        {
            "symbol": "BTC/USDT",
            "bar_start_ms": 1716800100000,
            "long_liquidation_notional_5m_usdt": 10000.0,
            "short_liquidation_notional_5m_usdt": 5000.0,
            "total_liquidation_notional_5m_usdt": 15000.0,
        }
        # Bar 1716800400000 is missing (implies zero liquidations)
    ]

    joined, audit = build_aligned_dataset(price_rows, liq_rows)

    assert len(joined) == 2
    assert audit["price_rows"] == 2
    assert audit["liquidation_rows"] == 1
    assert audit["joined_rows"] == 2
    assert audit["missing_liquidation_bar_count"] == 1

    # First row is joined
    assert joined[0]["symbol"] == "BTC/USDT"
    assert joined[0]["bar_start_ms"] == 1716800100000
    assert joined[0]["open_price"] == 60000.0
    assert joined[0]["close_price"] == 60050.0
    assert joined[0]["long_liquidation_notional_5m_usdt"] == 10000.0
    assert joined[0]["short_liquidation_notional_5m_usdt"] == 5000.0
    assert joined[0]["total_liquidation_notional_5m_usdt"] == 15000.0

    # Second row is joined with zero liquidations
    assert joined[1]["symbol"] == "BTC/USDT"
    assert joined[1]["bar_start_ms"] == 1716800400000
    assert joined[1]["open_price"] == 60050.0
    assert joined[1]["long_liquidation_notional_5m_usdt"] == 0.0
    assert joined[1]["short_liquidation_notional_5m_usdt"] == 0.0
    assert joined[1]["total_liquidation_notional_5m_usdt"] == 0.0


def test_build_dataset_cli_runs(tmp_path):
    liq_jsonl = tmp_path / "liq.jsonl"
    price_jsonl = tmp_path / "price.jsonl"
    output_jsonl = tmp_path / "output.jsonl"
    summary_json = tmp_path / "summary.json"

    # Write test data
    with open(liq_jsonl, "w") as f:
        f.write(
            json.dumps(
                {
                    "symbol": "BTC/USDT",
                    "bar_start_ms": 1716800100000,
                    "long_liquidation_notional_5m_usdt": 10000.0,
                    "short_liquidation_notional_5m_usdt": 5000.0,
                    "total_liquidation_notional_5m_usdt": 15000.0,
                }
            )
            + "\n"
        )

    with open(price_jsonl, "w") as f:
        f.write(
            json.dumps(
                {
                    "symbol": "BTC/USDT",
                    "timestamp_ms": 1716800100000,
                    "open": 60000.0,
                    "high": 60100.0,
                    "low": 59900.0,
                    "close": 60050.0,
                }
            )
            + "\n"
        )

    argv = [
        "--liquidation-jsonl",
        str(liq_jsonl),
        "--price-jsonl",
        str(price_jsonl),
        "--output-jsonl",
        str(output_jsonl),
        "--summary-output",
        str(summary_json),
    ]

    exit_code = main(argv)
    assert exit_code == 0
    assert output_jsonl.exists()
    assert summary_json.exists()
