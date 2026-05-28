from typing import Any
import pytest

from src.research.trend_liquidation_cascade_review import (
    LiquidationCascadeReviewThresholds,
    classify_liquidation_cascade_for_review,
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
        "oi_change_1h_pct": -3.0,
        "estimated_slippage_bps": 4.0,
        "funding_state": "neutral",
        "liquidation_notional_1h_usdt": 15_000_000.0,
        "long_liquidation_notional_1h_usdt": 0.0,
        "short_liquidation_notional_1h_usdt": 15_000_000.0,
    }
    row.update(overrides)
    return row


def test_short_liquidation_pressure_maps_to_continuation_long_and_mean_reversion_short():
    result = classify_liquidation_cascade_for_review(_row())
    assert result.event is not None
    assert result.event.regime == "liquidation_cascade"
    assert result.event.direction == "long"  # Continuation is long
    assert result.event.metadata["continuation_direction"] == "long"
    assert result.event.metadata["mean_reversion_direction"] == "short"
    assert result.event.metadata["liquidation_side"] == "short_liquidation"
    assert result.event.metadata["force_order_side"] == "BUY"


def test_long_liquidation_pressure_maps_to_continuation_short_and_mean_reversion_long():
    result = classify_liquidation_cascade_for_review(
        _row(
            return_1h_pct=-2.5,
            long_liquidation_notional_1h_usdt=15_000_000.0,
            short_liquidation_notional_1h_usdt=0.0,
        )
    )
    assert result.event is not None
    assert result.event.regime == "liquidation_cascade"
    assert result.event.direction == "short"  # Continuation is short
    assert result.event.metadata["continuation_direction"] == "short"
    assert result.event.metadata["mean_reversion_direction"] == "long"
    assert result.event.metadata["liquidation_side"] == "long_liquidation"
    assert result.event.metadata["force_order_side"] == "SELL"


def test_classifier_rejects_negative_return_negative_oi_without_long_liquidation_pressure():
    result = classify_liquidation_cascade_for_review(
        _row(
            return_1h_pct=-2.5,
            long_liquidation_notional_1h_usdt=10_000.0,  # Below threshold
            short_liquidation_notional_1h_usdt=0.0,
        )
    )
    assert result.event is None
    assert result.reject_reason == "liquidation_not_confirmed"


def test_cascade_classifier_rejects_missing_liquidation_proxy():
    result = classify_liquidation_cascade_for_review(
        _row(
            long_liquidation_notional_1h_usdt=None,
            short_liquidation_notional_1h_usdt=None,
        )
    )
    assert result.event is None
    assert result.reject_reason == "missing_liquidation_fields"


def test_cascade_classifier_rejects_large_move_without_liquidation_confirmation():
    # If liquidation notional is 0 or missing, should reject
    result = classify_liquidation_cascade_for_review(
        _row(
            long_liquidation_notional_1h_usdt=0.0,
            short_liquidation_notional_1h_usdt=0.0,
        )
    )
    assert result.event is None
    assert result.reject_reason == "liquidation_not_confirmed"


def test_cascade_classifier_supports_explicit_threshold_overrides():
    thresholds = LiquidationCascadeReviewThresholds(
        name="custom",
        vol_multiplier=2.0,
        major_min_return_pct=1.5,
        large_alt_min_return_pct=2.0,
        major_min_oi_pct=1.0,
        large_alt_min_oi_pct=1.5,
        major_min_liq_usdt=100_000.0,
        large_alt_min_liq_usdt=150_000.0,
        assumption_level="custom",
        eligible_for_redefinition=True,
    )
    result = classify_liquidation_cascade_for_review(
        _row(
            return_1h_pct=1.6,
            vol_1h_pct=2.1,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=-1.1,
            short_liquidation_notional_1h_usdt=120_000.0,
        ),
        thresholds=thresholds,
    )
    assert result.event is not None
