import pytest
from src.research.liquidation_shock_event_study.event_contract import LiquidationShockEvent
from src.research.liquidation_shock_event_study.shock_detection import (
    detect_shocks,
    deduplicate_events,
)


def test_detect_shocks_insufficient_lookback():
    # Only 100 bars (requires 1440)
    aligned_rows = [
        {
            "symbol": "BTC/USDT",
            "bar_start_ms": 1716800000000 + i * 60000,
            "open_price": 60000.0,
            "high_price": 60000.0,
            "low_price": 60000.0,
            "close_price": 60000.0,
            "long_liquidation_notional_1m_usdt": 60000.0 if i == 99 else 0.0,
            "short_liquidation_notional_1m_usdt": 0.0,
            "total_liquidation_notional_1m_usdt": 60000.0 if i == 99 else 0.0,
        }
        for i in range(100)
    ]

    events = detect_shocks(aligned_rows)
    assert len(events) == 0  # No events because lookback < 1440


def test_detect_shocks_successful_detection():
    # 1440 bars of zeros, then 1 shock bar
    aligned_rows = [
        {
            "symbol": "BTC/USDT",
            "bar_start_ms": 1716800000000 + i * 60000,
            "open_price": 60000.0,
            "high_price": 60000.0,
            "low_price": 60000.0,
            "close_price": 60000.0,
            "long_liquidation_notional_1m_usdt": 0.0,
            "short_liquidation_notional_1m_usdt": 0.0,
            "total_liquidation_notional_1m_usdt": 0.0,
        }
        for i in range(1440)
    ]

    # Add shock bar
    aligned_rows.append({
        "symbol": "BTC/USDT",
        "bar_start_ms": 1716800000000 + 1440 * 60000,
        "open_price": 60000.0,
        "high_price": 60000.0,
        "low_price": 60000.0,
        "close_price": 60000.0,
        "long_liquidation_notional_1m_usdt": 60000.0,
        "short_liquidation_notional_1m_usdt": 0.0,
        "total_liquidation_notional_1m_usdt": 60000.0,
    })

    events = detect_shocks(aligned_rows)
    assert len(events) == 1
    ev = events[0]
    assert ev.symbol == "BTC/USDT"
    assert ev.liquidated_position_side == "long"
    assert ev.shock_notional_usdt == 60000.0
    assert ev.relative_score == 1.0  # Since it is larger than all 1440 zeros
    assert ev.expected_price_direction == "down"


def test_deduplicate_events_order_invariant():
    # Construct multiple events within the same 5m bucket
    # Bucket starts at 1716800000000
    ev1 = LiquidationShockEvent(
        symbol="BTC/USDT",
        shock_bar_start_ms=1716800000000,
        liquidated_position_side="long",
        dominant_liquidation_side="long",
        shock_notional_usdt=60000.0,
        relative_score=0.995,
        relative_score_method="percentile_rank",
        reference_count=1440,
        required_reference_count=1440,
        dominance_ratio=1.0,
        dedup_bucket_start_ms=1716800000000,
    )
    ev2 = LiquidationShockEvent(
        symbol="BTC/USDT",
        shock_bar_start_ms=1716800120000,  # +2 minutes
        liquidated_position_side="long",
        dominant_liquidation_side="long",
        shock_notional_usdt=80000.0,  # Max notional
        relative_score=0.998,
        relative_score_method="percentile_rank",
        reference_count=1440,
        required_reference_count=1440,
        dominance_ratio=1.0,
        dedup_bucket_start_ms=1716800000000,
    )
    ev3 = LiquidationShockEvent(
        symbol="BTC/USDT",
        shock_bar_start_ms=1716800240000,  # +4 minutes
        liquidated_position_side="long",
        dominant_liquidation_side="long",
        shock_notional_usdt=70000.0,
        relative_score=0.996,
        relative_score_method="percentile_rank",
        reference_count=1440,
        required_reference_count=1440,
        dominance_ratio=1.0,
        dedup_bucket_start_ms=1716800000000,
    )

    # Test with different order of inputs
    res1 = deduplicate_events([ev1, ev2, ev3])
    res2 = deduplicate_events([ev3, ev2, ev1])

    assert len(res1) == 1
    assert len(res2) == 1
    assert res1[0].shock_bar_start_ms == ev2.shock_bar_start_ms
    assert res2[0].shock_bar_start_ms == ev2.shock_bar_start_ms
    assert res1[0].shock_notional_usdt == 80000.0
