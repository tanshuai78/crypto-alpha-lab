import json

import scripts.external_signal_shadow.run_stage1_4b_lite_funding_oi_price_crowding_replay as runner_module
from scripts.external_signal_shadow.run_stage1_4b_lite_funding_oi_price_crowding_replay import main


def test_runner_writes_b_lite_summary(tmp_path):
    funding = tmp_path / "funding.json"
    funding.write_text(json.dumps([
        {"symbol": "BTCUSDT", "fundingTime": 1000, "fundingRate": 0.0001}
    ]), encoding="utf-8")

    oi = tmp_path / "oi.json"
    oi.write_text(json.dumps([
        {"symbol": "BTCUSDT", "timestamp": 1000, "sumOpenInterest": 100.0}
    ]), encoding="utf-8")

    price = tmp_path / "price.json"
    price.write_text(json.dumps([
        {"symbol": "BTCUSDT", "open_time": 1000, "close": 50000.0, "quote_volume": 10.0}
    ]), encoding="utf-8")

    summary_path = tmp_path / "summary.json"

    rc = main([
        "--funding-input", str(funding),
        "--oi-input", str(oi),
        "--price-input", str(price),
        "--output-summary", str(summary_path),
        "--fixture-run",
    ])

    assert rc == 0
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["liquidation_used"] is False
    assert summary["signed_replay_only"] is True
    assert summary["fixture_run"] is True
    assert summary["research_result_valid"] is False
    assert summary["decision"] == "crowding_lite_failed" # because we don't have enough data (density gate fails)
    assert summary["primary_blocker"] == "total_event_count_below_min"


def test_runner_accepts_random_baseline_trials_override(tmp_path, monkeypatch):
    funding = tmp_path / "funding.json"
    funding.write_text(json.dumps([
        {"symbol": "BTCUSDT", "fundingTime": 1000, "fundingRate": 0.0001}
    ]), encoding="utf-8")

    oi = tmp_path / "oi.json"
    oi.write_text(json.dumps([
        {"symbol": "BTCUSDT", "timestamp": 1000, "sumOpenInterest": 100.0}
    ]), encoding="utf-8")

    price = tmp_path / "price.json"
    price.write_text(json.dumps([
        {"symbol": "BTCUSDT", "open_time": 1000, "close": 50000.0, "quote_volume": 10.0}
    ]), encoding="utf-8")

    summary_path = tmp_path / "summary.json"
    seen = {"trials": []}

    def fake_random_baseline(candidate_events, price_bars, trials, random_seed):
        seen["trials"].append(trials)
        return {
            "random_baseline_trials": trials,
            "median_net_return_bps_after_50bps": 0.0,
            "baseline_sampling_failure_count": 0,
            "baseline_sampling_insufficient": False,
        }

    monkeypatch.setattr(runner_module, "compute_random_baseline_summary", fake_random_baseline)

    rc = main([
        "--funding-input", str(funding),
        "--oi-input", str(oi),
        "--price-input", str(price),
        "--output-summary", str(summary_path),
        "--fixture-run",
        "--random-baseline-trials", "7",
    ])

    assert rc == 0
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["random_baseline_trials"] == 7
    assert seen["trials"] == [7, 7, 7]
