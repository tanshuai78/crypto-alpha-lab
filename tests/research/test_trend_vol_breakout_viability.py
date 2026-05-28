from typing import Any
import pytest

from src.research.trend_vol_breakout_viability import (
    VolBreakoutReviewThresholds,
    classify_vol_breakout_only_for_review,
)


def _row(**overrides: Any) -> dict[str, Any]:
    row = {
        "symbol": "BTC/USDT",
        "exchange": "binance",
        "timestamp_ms": 1710000000000,
        "data_age_sec": 0.0,
        "volume_24h_usdt": 1_000_000_000.0,
        "return_1h_pct": 2.5,
        "vol_1h_pct": 3.0,
        "vol_baseline_30d_pct": 1.0,
        "oi_change_1h_pct": 3.0,
        "estimated_slippage_bps": 4.0,
        "funding_state": "neutral",
        "liquidation_notional_1h_usdt": 0.0,
    }
    row.update(overrides)
    return row


def test_vol_breakout_accepts_long_continuation_with_positive_oi():
    result = classify_vol_breakout_only_for_review(_row())
    assert result.event is not None
    assert result.event.regime == "vol_breakout_long"


def test_vol_breakout_accepts_short_continuation_with_positive_oi():
    result = classify_vol_breakout_only_for_review(
        _row(return_1h_pct=-2.5, oi_change_1h_pct=3.0)
    )
    assert result.event is not None
    assert result.event.regime == "vol_breakout_short"


def test_vol_breakout_rejects_negative_oi_as_not_breakout_continuation():
    result = classify_vol_breakout_only_for_review(
        _row(return_1h_pct=-2.5, oi_change_1h_pct=-3.0)
    )
    assert result.event is None
    assert result.reject_reason == "oi_not_positive_for_vol_breakout"


def test_vol_breakout_reports_same_primary_breakout_gate():
    result = classify_vol_breakout_only_for_review(
        _row(vol_1h_pct=1.5, vol_baseline_30d_pct=1.0)
    )
    assert result.event is None
    assert result.reject_reason == "vol_breakout_below_threshold"


def test_vol_breakout_classifier_never_uses_liquidation_notional():
    low = classify_vol_breakout_only_for_review(_row(liquidation_notional_1h_usdt=0.0))
    high = classify_vol_breakout_only_for_review(_row(liquidation_notional_1h_usdt=999_999_999.0))
    assert low == high


def test_vol_breakout_classifier_accepts_explicit_threshold_overrides():
    thresholds = VolBreakoutReviewThresholds(
        name="custom",
        vol_multiplier=2.0,
        major_min_return_pct=1.5,
        large_alt_min_return_pct=2.0,
        major_min_oi_pct=1.0,
        large_alt_min_oi_pct=1.5,
        assumption_level="moderately_relaxed",
        eligible_for_redefinition=True,
    )
    result = classify_vol_breakout_only_for_review(
        _row(return_1h_pct=1.6, vol_1h_pct=2.1, vol_baseline_30d_pct=1.0, oi_change_1h_pct=1.1),
        thresholds=thresholds,
    )
    assert result.event is not None
