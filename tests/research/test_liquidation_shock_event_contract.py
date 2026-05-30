from src.research.liquidation_shock_event_study.event_contract import (
    LiquidationShockEvent,
    classify_liquidation_shock_event,
)


def test_liquidation_shock_event_properties():
    event = LiquidationShockEvent(
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
        source_namespace="liquidation_shock_event_study",
    )

    assert event.symbol == "BTC/USDT"
    # Long liquidation is exchange selling -> downward price pressure (Short trade direction)
    assert event.expected_price_direction == "down"


def test_classify_liquidation_shock_event_long_liquidation():
    # Long liquidation -> downward pressure
    event = classify_liquidation_shock_event(
        symbol="BTC/USDT",
        bar_start_ms=1716800000000,
        long_liq=60000.0,
        short_liq=0.0,
        relative_score=0.995,
        reference_count=1440,
    )
    assert event is not None
    assert event.liquidated_position_side == "long"
    assert event.dominant_liquidation_side == "long"
    assert event.expected_price_direction == "down"
    assert event.dominance_ratio == 1.0


def test_classify_liquidation_shock_event_short_liquidation():
    # Short liquidation -> upward pressure
    event = classify_liquidation_shock_event(
        symbol="BTC/USDT",
        bar_start_ms=1716800000000,
        long_liq=0.0,
        short_liq=60000.0,
        relative_score=0.995,
        reference_count=1440,
    )
    assert event is not None
    assert event.liquidated_position_side == "short"
    assert event.dominant_liquidation_side == "short"
    assert event.expected_price_direction == "up"
    assert event.dominance_ratio == 1.0


def test_classify_liquidation_shock_event_mixed_fails_dominance():
    # Mixed, dominance ratio = 50k / 80k = 0.625 < 0.70 (fails dominance)
    event = classify_liquidation_shock_event(
        symbol="BTC/USDT",
        bar_start_ms=1716800000000,
        long_liq=50000.0,
        short_liq=30000.0,
        relative_score=0.995,
        reference_count=1440,
    )
    assert event is None


def test_classify_liquidation_shock_event_below_absolute_threshold():
    # BTC/USDT threshold is 50,000. 49,900 is below.
    event = classify_liquidation_shock_event(
        symbol="BTC/USDT",
        bar_start_ms=1716800000000,
        long_liq=49900.0,
        short_liq=0.0,
        relative_score=0.995,
        reference_count=1440,
    )
    assert event is None


def test_classify_liquidation_shock_event_below_relative_score():
    # relative score is 0.98 < 0.99 threshold
    event = classify_liquidation_shock_event(
        symbol="BTC/USDT",
        bar_start_ms=1716800000000,
        long_liq=60000.0,
        short_liq=0.0,
        relative_score=0.98,
        reference_count=1440,
    )
    assert event is None


def test_classify_liquidation_shock_event_insufficient_reference():
    # reference count is 1000 < 1440 threshold
    event = classify_liquidation_shock_event(
        symbol="BTC/USDT",
        bar_start_ms=1716800000000,
        long_liq=60000.0,
        short_liq=0.0,
        relative_score=0.995,
        reference_count=1000,
    )
    assert event is None
