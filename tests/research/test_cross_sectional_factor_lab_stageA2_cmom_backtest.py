from __future__ import annotations

from datetime import date, timedelta

from research.cross_sectional_factor_lab.backtest import run_stageA2_cmom_diagnostic


import math


def _synthetic_panel(symbols: int = 12, days: int = 430, include_benchmarks: bool = True) -> list[dict]:
    rows = []
    start = date(2025, 1, 1)
    names = [f"ALT{s:02d}USDT" for s in range(symbols)]
    if include_benchmarks:
        names = ["BTCUSDT", "ETHUSDT"] + names
    for s, symbol in enumerate(names):
        for i in range(days):
            dt = start + timedelta(days=i)
            price = 100.0 + i + s + 10.0 * math.sin(i * 0.1 + s)
            rows.append({
                "symbol": symbol,
                "date_utc": dt.isoformat(),
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "base_volume": 1_000_000.0,
                "quote_volume": 50_000_000.0,
            })
    return rows


def test_run_stageA2_cmom_diagnostic_returns_required_summary_shape() -> None:
    summary = run_stageA2_cmom_diagnostic(_synthetic_panel())

    assert summary["stage"] == "stageA2_cmom_diagnostic"
    assert summary["live_usage"] == "not_allowed"
    assert summary["paper_shadow_allowed"] is False
    assert "momentum_30d_skip_1d" in summary["factor_variants"]
    assert "cmom_14d_skip_1d" in summary["factor_variants"]
    assert "primary_comparison" in summary
    assert summary["can_promote_strategy"] is False


def test_run_stageA2_cmom_diagnostic_empty_rows_returns_data_unavailable() -> None:
    summary = run_stageA2_cmom_diagnostic([])

    assert summary["decision"] == "stageA2_cmom_data_unavailable"
    assert summary["primary_blocker"] == "empty_daily_bars"
    assert summary["live_usage"] == "not_allowed"
    assert summary["paper_shadow_allowed"] is False


def test_stageA2_cmom_data_unavailable_when_btc_eth_missing() -> None:
    summary = run_stageA2_cmom_diagnostic(_synthetic_panel(include_benchmarks=False))

    assert summary["decision"] == "stageA2_cmom_data_unavailable"
    assert summary["primary_blocker"] == "missing_btc_or_eth_benchmark"


def test_stageA2_cmom_data_unavailable_when_rebalance_count_below_gate() -> None:
    summary = run_stageA2_cmom_diagnostic(_synthetic_panel(days=100))

    assert summary["decision"] == "stageA2_cmom_data_unavailable"
    assert summary["primary_blocker"] == "insufficient_rebalance_count"


def test_stageA2_cmom_uses_same_btc_eth_base_benchmarks_for_both_variants() -> None:
    rows = _synthetic_panel()
    summary = run_stageA2_cmom_diagnostic(rows)

    mom = summary["factor_variants"]["momentum_30d_skip_1d"]
    cmom = summary["factor_variants"]["cmom_14d_skip_1d"]

    base_keys = [
        "btc_buy_and_hold_net_pct",
        "eth_buy_and_hold_net_pct",
        "universe_equal_weight_pct",
    ]
    for key in base_keys:
        assert mom["benchmarks"][key] == cmom["benchmarks"][key]

    assert mom["benchmarks"]["vs_btc_total_return_pct"] != cmom["benchmarks"]["vs_btc_total_return_pct"]


def test_stageA2_cmom_top5_is_diagnostic_only() -> None:
    summary = run_stageA2_cmom_diagnostic(_synthetic_panel())

    cmom = summary["factor_variants"]["cmom_14d_skip_1d"]
    assert "diagnostic_top5_performance" in cmom
    assert summary["decision"] != "strategy_confirmed"


def test_stageA2_cmom_reports_abs_symbol_and_month_concentration() -> None:
    summary = run_stageA2_cmom_diagnostic(_synthetic_panel())

    cmom = summary["factor_variants"]["cmom_14d_skip_1d"]
    assert "max_single_symbol_abs_pnl_share" in cmom["concentration"]
    assert "max_single_month_abs_pnl_share" in cmom["concentration"]


def test_stageA2_cmom_variant_does_not_raise_portfolio_sort_keyerror() -> None:
    summary = run_stageA2_cmom_diagnostic(_synthetic_panel())

    assert summary["decision"] != "stageA2_cmom_data_unavailable"
    assert "cmom_14d_skip_1d" in summary["factor_variants"]


def test_stageA2_cmom_concentration_handles_negative_total_pnl() -> None:
    summary = run_stageA2_cmom_diagnostic(_synthetic_panel())

    for variant in summary["factor_variants"].values():
        assert 0.0 <= variant["concentration"]["max_single_symbol_abs_pnl_share"] <= 1.0
        assert 0.0 <= variant["concentration"]["max_single_month_abs_pnl_share"] <= 1.0
