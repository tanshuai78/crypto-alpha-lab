from datetime import date, timedelta

import pandas as pd

from research.cross_sectional_factor_lab.stageA2 import (
    compound_returns_pct,
    max_drawdown_pct,
    run_stageA2_regime_cash_fallback_diagnostic,
)


def _row(symbol: str, dt: date, close: float, quote_volume: float = 100_000_000.0) -> dict:
    return {
        "symbol": symbol,
        "date_utc": dt.isoformat(),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "base_volume": 1_000_000.0,
        "quote_volume": quote_volume,
    }


def _synthetic_rows(days: int = 140) -> list[dict]:
    start = date(2026, 1, 1)
    symbols = ["BTCUSDT", "ETHUSDT"] + [f"ALT{i:02d}USDT" for i in range(12)]
    rows = []
    for i in range(days):
        dt = start + timedelta(days=i)
        btc = 100.0 + i * 0.2
        eth = 100.0 + i * 0.1
        rows.append(_row("BTCUSDT", dt, btc))
        rows.append(_row("ETHUSDT", dt, eth))
        for j, symbol in enumerate(symbols[2:]):
            close = 50.0 + i * (0.05 + j * 0.002)
            rows.append(_row(symbol, dt, close))
    return rows


def test_compound_returns_pct_handles_empty_and_simple_returns():
    assert compound_returns_pct([]) == 0.0
    assert round(compound_returns_pct([0.10, -0.10]), 4) == -1.0


def test_max_drawdown_pct_uses_compounded_equity_curve():
    assert round(max_drawdown_pct([0.10, -0.20, 0.05]), 4) == 20.0


def test_stageA2_empty_rows_returns_data_unavailable_summary():
    summary = run_stageA2_regime_cash_fallback_diagnostic([])

    assert summary["run_mode"] == "stageA2_regime_cash_fallback_diagnostic"
    assert summary["decision"] == "stageA2_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"
    assert summary["live_usage"] == "not_allowed"


def test_stageA2_summary_contains_three_locked_variants():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())

    assert summary["scope"] == "regime_cash_fallback_only"
    assert [item["variant"] for item in summary["variants"]] == [
        "regime_none",
        "btc_ma20_cash",
        "alt_universe_20d_return_cash",
    ]


def test_stageA2_variant_reports_cash_and_exposure_shares():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())
    variant = next(item for item in summary["variants"] if item["variant"] == "btc_ma20_cash")

    regime_filter = variant["regime_filter"]
    assert 0.0 <= regime_filter["filtered_rebalance_share"] <= 1.0
    assert 0.0 <= regime_filter["cash_days_share"] <= 1.0
    assert 0.0 <= regime_filter["alt_exposure_days_share"] <= 1.0
    assert round(regime_filter["cash_days_share"] + regime_filter["alt_exposure_days_share"], 6) == 1.0


def test_stageA2_universe_equal_weight_benchmark_is_not_regime_none_top10():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())
    baseline = next(item for item in summary["variants"] if item["variant"] == "regime_none")

    assert "universe_equal_weight_pct" in baseline["benchmarks"]
    assert round(
        baseline["benchmarks"]["universe_equal_weight_pct"], 8
    ) != round(
        baseline["performance"]["base_30bps_total_return_pct"], 8
    )


def test_stageA2_top_level_keeps_live_and_paper_disabled():
    summary = run_stageA2_regime_cash_fallback_diagnostic(_synthetic_rows())

    assert summary["live_usage"] == "not_allowed"
    assert summary["paper_shadow_allowed"] is False
    assert summary["bias_label"] == "survivorship_bias_not_controlled"
