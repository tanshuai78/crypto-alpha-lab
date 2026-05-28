from typing import Any
import pytest

from scripts.review_trend_vol_breakout_viability import (
    build_vol_breakout_audit_summary,
    build_vol_breakout_shadow_summary,
    run_vol_breakout_sensitivity,
)
from src.research.trend_vol_breakout_viability import (
    VolBreakoutReviewThresholds,
    classify_vol_breakout_only_for_review,
)


def _row(**overrides: Any) -> dict[str, Any]:
    row = {
        "timestamp_ms": 1710000000000,
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "close_price": 100000.0,
        "return_1h_pct": 2.5,
        "vol_1h_pct": 3.0,
        "vol_baseline_30d_pct": 1.0,
        "oi_change_1h_pct": 3.0,
        "volume_24h_usdt": 1_000_000_000.0,
        "estimated_slippage_bps": 4.0,
        "data_age_sec": 0.0,
    }
    row.update(overrides)
    return row


def test_vol_breakout_audit_summary_counts_only_breakout_events():
    rows = [
        _row(symbol="BTC/USDT"),
        _row(symbol="ETH/USDT", vol_1h_pct=1.0, vol_baseline_30d_pct=1.0),
    ]

    summary = build_vol_breakout_audit_summary(rows)

    assert summary["input_row_count"] == 2
    assert summary["entry_event_count"] == 1
    assert summary["entry_event_count_by_regime"] == {"vol_breakout_long": 1}
    assert summary["classification_reject_counts"]["vol_breakout_below_threshold"] == 1


def test_vol_breakout_shadow_summary_uses_only_accepted_breakout_entries():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT", close_price=100000.0),
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.2, vol_1h_pct=1.0),
        _row(timestamp_ms=3000, symbol="ETH/USDT", close_price=100.0, vol_1h_pct=1.0),
    ]

    summary = build_vol_breakout_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12)

    assert summary["entry_event_count"] == 1
    assert summary["shadow_trade_count"] == 1
    assert summary["holding_hours"] == 12


def test_shadow_path_uses_same_symbol_and_future_only():
    rows = [
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=100000.0),
        _row(timestamp_ms=1500, symbol="BTC/USDT", close_price=90000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
        _row(timestamp_ms=2500, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
        _row(timestamp_ms=2600, symbol="ETH/USDT", close_price=110.0, return_1h_pct=0.1, vol_1h_pct=1.0),
    ]

    summary = build_vol_breakout_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12)

    assert summary["shadow_trade_count"] == 1
    assert summary["accepted_entries_with_path_count"] == 1


def test_shadow_trade_count_never_exceeds_entry_event_count():
    summary = build_vol_breakout_shadow_summary([_row()], estimated_cost_bps=30.0, holding_hours=12)
    assert summary["shadow_trade_count"] <= summary["entry_event_count"]


def test_vol_breakout_sensitivity_reports_baseline_moderate_and_aggressive_sets():
    rows = [
        _row(symbol="BTC/USDT", return_1h_pct=2.2, vol_1h_pct=2.7, vol_baseline_30d_pct=1.0, oi_change_1h_pct=1.8),
        _row(symbol="BTC/USDT", timestamp_ms=2000, close_price=101000.0, return_1h_pct=0.2, vol_1h_pct=1.0),
    ]

    summaries = run_vol_breakout_sensitivity(
        rows,
        threshold_sets=[
            VolBreakoutReviewThresholds.baseline_current(),
            VolBreakoutReviewThresholds.moderately_relaxed(),
            VolBreakoutReviewThresholds.aggressive_relaxed(),
        ],
    )

    assert [item["threshold_set_name"] for item in summaries] == [
        "baseline_current",
        "moderately_relaxed",
        "aggressive_relaxed",
    ]
    assert summaries[2]["assumption_level"] == "diagnostic_noise_boundary"
    assert summaries[2]["eligible_for_redefinition"] is False


def test_sensitivity_does_not_mutate_live_config_thresholds():
    before = classify_vol_breakout_only_for_review(_row())
    run_vol_breakout_sensitivity([_row()], threshold_sets=[VolBreakoutReviewThresholds.moderately_relaxed()])
    after = classify_vol_breakout_only_for_review(_row())
    assert before == after
