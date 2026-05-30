from src.research.liquidation_only_5m.baseline import (
    classify_liquidation_only_5m_event,
)


def test_short_liquidation_maps_to_long_continuation_and_short_reversion():
    row = {
        "symbol": "BTC/USDT",
        "bar_start_ms": 1780000000000,
        "short_liquidation_notional_5m_usdt": 12_000_000.0,
        "long_liquidation_notional_5m_usdt": 500_000.0,
        "liquidation_relative_score": 0.997,
        "liquidation_reference_count": 2016,
        "dominance_ratio": 0.96,
    }

    event = classify_liquidation_only_5m_event(row)
    assert event is not None
    assert event.liquidated_position_side == "short"
    assert event.dominant_liquidation_side == "short"
    assert event.continuation_trade_side == "long"
    assert event.mean_reversion_trade_side == "short"
    assert event.dominance_ratio == 0.96


def test_long_liquidation_maps_to_short_continuation_and_long_reversion():
    row = {
        "symbol": "ETH/USDT",
        "bar_start_ms": 1780000000000,
        "short_liquidation_notional_5m_usdt": 10_000.0,
        "long_liquidation_notional_5m_usdt": 1_000_000.0,
        "liquidation_relative_score": 0.995,
        "liquidation_reference_count": 2016,
        "dominance_ratio": 0.99,
    }

    event = classify_liquidation_only_5m_event(row)
    assert event is not None
    assert event.liquidated_position_side == "long"
    assert event.dominant_liquidation_side == "long"
    assert event.continuation_trade_side == "short"
    assert event.mean_reversion_trade_side == "long"
    assert event.dominance_ratio == 0.99


def test_rejected_if_dominance_ratio_below_threshold():
    row = {
        "symbol": "BTC/USDT",
        "bar_start_ms": 1780000000000,
        "short_liquidation_notional_5m_usdt": 5_000_000.0,
        "long_liquidation_notional_5m_usdt": 4_000_000.0,
        "liquidation_relative_score": 0.997,
        "liquidation_reference_count": 2016,
        "dominance_ratio": 0.55,
    }
    event = classify_liquidation_only_5m_event(row)
    assert event is None


def test_rejected_if_absolute_notional_below_threshold():
    row = {
        "symbol": "BTC/USDT",
        "bar_start_ms": 1780000000000,
        "short_liquidation_notional_5m_usdt": 10_000.0,  # Below major threshold (e.g. 50k)
        "long_liquidation_notional_5m_usdt": 0.0,
        "liquidation_relative_score": 0.997,
        "liquidation_reference_count": 2016,
        "dominance_ratio": 1.0,
    }
    event = classify_liquidation_only_5m_event(row)
    assert event is None


def test_rejected_if_relative_score_below_threshold():
    row = {
        "symbol": "BTC/USDT",
        "bar_start_ms": 1780000000000,
        "short_liquidation_notional_5m_usdt": 1_000_000.0,
        "long_liquidation_notional_5m_usdt": 0.0,
        "liquidation_relative_score": 0.90,  # Below global threshold (e.g. 0.99)
        "liquidation_reference_count": 2016,
        "dominance_ratio": 1.0,
    }
    event = classify_liquidation_only_5m_event(row)
    assert event is None


def test_rejected_if_reference_count_insufficient():
    row = {
        "symbol": "BTC/USDT",
        "bar_start_ms": 1780000000000,
        "short_liquidation_notional_5m_usdt": 1_000_000.0,
        "long_liquidation_notional_5m_usdt": 0.0,
        "liquidation_relative_score": 0.997,
        "liquidation_reference_count": 1000,  # Below required 2016
        "dominance_ratio": 1.0,
    }
    event = classify_liquidation_only_5m_event(row)
    assert event is None
