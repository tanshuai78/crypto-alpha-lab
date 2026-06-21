import json
import os

import pytest

from scripts.external_signal_shadow.run_stage1_4e_deleveraging_proxy_sensitivity_review import (
    main,
)

# Multiples of 900000 (15m)
T_START = 1600000200000
T_END = T_START + 900000

@pytest.fixture
def temp_archives(tmp_path):
    oi_path = tmp_path / "oi.jsonl"
    price_path = tmp_path / "price.jsonl"
    funding_path = tmp_path / "funding.jsonl"
    summary_path = tmp_path / "summary.json"

    # Minimal valid data for 15m candidate
    oi_data = [
        {"symbol": "BTCUSDT", "timestamp_ms": T_START, "sumOpenInterest": 100.0, "sumOpenInterestValue": 100.0},
        {"symbol": "BTCUSDT", "timestamp_ms": T_END, "sumOpenInterest": 95.0, "sumOpenInterestValue": 95.0},
    ]
    price_data = [
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 100.0, "low": 97.0, "close": 97.0},
        # Need future bars for 1h/4h/12h replay to find entry and exit
        {"symbol": "BTCUSDT", "bar_start_ms": T_END, "open": 97.0, "high": 97.0, "low": 97.0, "close": 97.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 900000, "open": 97.0, "high": 97.0, "low": 97.0, "close": 97.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 3600000, "open": 97.0, "high": 97.0, "low": 97.0, "close": 97.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 14400000, "open": 97.0, "high": 97.0, "low": 97.0, "close": 97.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 43200000, "open": 97.0, "high": 97.0, "low": 97.0, "close": 97.0},
    ]
    funding_data = [
        {"symbol": "BTCUSDT", "fundingTime": T_START, "fundingRate": 0.0001},
    ]

    oi_path.write_text("\n".join(json.dumps(r) for r in oi_data))
    price_path.write_text("\n".join(json.dumps(r) for r in price_data))
    funding_path.write_text("\n".join(json.dumps(r) for r in funding_data))

    return str(oi_path), str(price_path), str(funding_path), str(summary_path)

def test_runner_cli_runs_e2e_pipeline_and_produces_json(temp_archives):
    oi, price, funding, summary = temp_archives

    # Run command e2e via main
    sys_args = [
        "--oi-archive", oi,
        "--price-archive", price,
        "--funding-archive", funding,
        "--output-summary", summary,
        "--random-baseline-trials", "10",
        "--fixture-run",
    ]
    main(sys_args)

    assert os.path.exists(summary)
    with open(summary, "r") as f:
        data = json.load(f)

    assert "deleveraging_proxy_15m" in data
    assert "deleveraging_proxy_1h" in data

    # 15m candidate details
    c15m = data["deleveraging_proxy_15m"]
    assert c15m["fixture_run"] is True
    assert c15m["deleveraging_proxy_only"] is True
    assert c15m["liquidation_used"] is False
    assert c15m["not_b_lite_restart"] is True
    assert c15m["baseline_trials_override_used"] is True
    assert c15m["research_result_valid"] is False
    assert c15m["decision"] == "deleveraging_proxy_inconclusive"
    assert c15m["funding_context_summary"]["funding_rows_loaded"] == 1
    assert c15m["funding_context_summary"]["funding_context_used"] is True
