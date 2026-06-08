from __future__ import annotations

from datetime import date, timedelta

from research.cross_sectional_factor_lab.backtest import run_stageA_v1_backtest


def _synthetic_panel() -> list[dict]:
    start = date(2025, 1, 1)
    rows = []
    # 90 days of data
    for i in range(90):
        day = start + timedelta(days=i)
        for rank, symbol in enumerate([f"ALT{x:02d}USDT" for x in range(12)]):
            close = 100.0 + i * (rank + 1)
            rows.append(
                {
                    "symbol": symbol,
                    "date_utc": day.isoformat(),
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "base_volume": 1.0,
                    "quote_volume": 25_000_000.0,
                }
            )
    return rows


def test_run_stageA_v1_backtest_returns_required_summary_shape() -> None:
    summary = run_stageA_v1_backtest(_synthetic_panel())

    assert summary["run_mode"] == "stageA_v1_momentum_backtest"
    assert summary["market"] == "binance_spot"
    assert summary["bias_label"] == "survivorship_bias_not_controlled"
    assert summary["primary_portfolio"] == "top10_equal_weight"
    assert "base_30_bps_round_trip" in summary["performance"]["by_cost_scenario"]
    assert "excess_performance" in summary
    assert "concentration" in summary
    assert "rebalance_quality" in summary


def test_run_stageA_v1_backtest_empty_rows_returns_data_unavailable() -> None:
    summary = run_stageA_v1_backtest([])

    assert summary["decision"] == "stageA_v1_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"


def test_short_synthetic_panel_fails_min_rebalance_count_gate() -> None:
    # 90 days yields around 8-9 weekly rebalances, which is < 50
    summary = run_stageA_v1_backtest(_synthetic_panel())

    assert summary["rebalance_quality"]["rebalance_count"] < 50
    assert summary["decision"] in {"stageA_v1_failed", "stageA_v1_data_unavailable"}
