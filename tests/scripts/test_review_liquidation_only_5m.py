import json

from scripts.review_liquidation_only_5m import main, run_decision_engine


def test_decision_engine_rules():
    # Setup aggregate summary that fails (e.g. all returns are negative)
    summary = {
        1: {
            "continuation": {
                "event_count": 10,
                "median_cost_adjusted_bps": -5.0,
                "median_gross_bps": 10.0,
                "cost_adjusted_win_rate": 0.4,
                "worst_cost_adjusted_bps": -200.0,
                "event_share_per_symbol": {"BTC/USDT": 1.0},
            },
            "mean_reversion": {
                "event_count": 10,
                "median_cost_adjusted_bps": -15.0,
                "median_gross_bps": 0.0,
                "cost_adjusted_win_rate": 0.3,
                "worst_cost_adjusted_bps": -300.0,
                "event_share_per_symbol": {"BTC/USDT": 1.0},
            },
        },
        2: {
            "continuation": {
                "event_count": 10,
                "median_cost_adjusted_bps": -6.0,
                "median_gross_bps": 9.0,
                "cost_adjusted_win_rate": 0.39,
                "worst_cost_adjusted_bps": -220.0,
                "event_share_per_symbol": {"BTC/USDT": 1.0},
            },
            "mean_reversion": {
                "event_count": 10,
                "median_cost_adjusted_bps": -14.0,
                "median_gross_bps": 1.0,
                "cost_adjusted_win_rate": 0.32,
                "worst_cost_adjusted_bps": -320.0,
                "event_share_per_symbol": {"BTC/USDT": 1.0},
            },
        },
        3: {
            "continuation": {
                "event_count": 10,
                "median_cost_adjusted_bps": -7.0,
                "median_gross_bps": 8.0,
                "cost_adjusted_win_rate": 0.38,
                "worst_cost_adjusted_bps": -240.0,
                "event_share_per_symbol": {"BTC/USDT": 1.0},
            },
            "mean_reversion": {
                "event_count": 10,
                "median_cost_adjusted_bps": -13.0,
                "median_gross_bps": 2.0,
                "cost_adjusted_win_rate": 0.34,
                "worst_cost_adjusted_bps": -340.0,
                "event_share_per_symbol": {"BTC/USDT": 1.0},
            },
        },
    }

    decision, reasons = run_decision_engine(summary, total_events=10, span_days=8.0)
    assert decision == "retire_liquidation_only_5m_baseline"
    assert any("failed performance gates" in r for r in reasons) or any(
        "No hypothesis passed" in r for r in reasons
    )


def test_review_cli_runs(tmp_path):
    dataset_file = tmp_path / "dataset.jsonl"
    summary_file = tmp_path / "summary.json"
    review_file = tmp_path / "review.md"

    # Write a small dataset
    rows = [
        # History
        {
            "symbol": "BTC/USDT",
            "bar_start_ms": 1716800000000 + i * 300_000,
            "open_price": 60000.0,
            "high_price": 60100.0,
            "low_price": 59900.0,
            "close_price": 60050.0,
            "long_liquidation_notional_5m_usdt": 0.0,
            "short_liquidation_notional_5m_usdt": 0.0,
            "total_liquidation_notional_5m_usdt": 0.0,
            "liquidation_relative_score": 0.0,
            "liquidation_reference_count": 2016,
            "dominance_ratio": 0.0,
        }
        for i in range(2025)
    ]
    # Put one event in the middle (index 2017)
    rows[2017].update(
        {
            "short_liquidation_notional_5m_usdt": 1_000_000.0,
            "total_liquidation_notional_5m_usdt": 1_000_000.0,
            "liquidation_relative_score": 0.999,
            "dominance_ratio": 1.0,
        }
    )
    # Make the price after event go up to make continuation long win
    rows[2018]["open_price"] = 60000.0
    rows[2018]["close_price"] = 61000.0  # +1.6% return, easily beats cost
    rows[2019]["close_price"] = 61100.0
    rows[2020]["close_price"] = 61200.0

    with open(dataset_file, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    argv = [
        "--dataset-jsonl",
        str(dataset_file),
        "--summary-output",
        str(summary_file),
        "--review-output",
        str(review_file),
    ]

    exit_code = main(argv)
    assert exit_code == 0
    assert summary_file.exists()
    assert review_file.exists()
