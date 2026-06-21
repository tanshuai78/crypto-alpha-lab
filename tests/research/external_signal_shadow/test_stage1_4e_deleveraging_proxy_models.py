from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    CANDIDATE_1H,
    CANDIDATE_15M,
    DECISION_FAILED,
    DECISION_INCONCLUSIVE,
    DECISION_SURVIVES,
    EVENT_DOWN_FLUSH,
    EVENT_UP_SQUEEZE,
    QUALITY_OI_HOURLY_SNAPSHOT,
    QUALITY_PRICE_CLOSE_PROXY,
    SECONDARY_NONE,
    SECONDARY_PROMISING_SPARSE,
    SOURCE_OI_BINANCE_VISION,
    SOURCE_PRICE_BINANCE_KLINE,
    ProxyEvent,
)


def test_models_define_candidate_and_decision_enums():
    assert CANDIDATE_15M == "deleveraging_proxy_15m"
    assert CANDIDATE_1H == "deleveraging_proxy_1h"
    assert EVENT_DOWN_FLUSH == "down_flush_deleveraging_proxy"
    assert EVENT_UP_SQUEEZE == "up_squeeze_deleveraging_proxy"
    assert DECISION_FAILED == "deleveraging_proxy_failed"
    assert DECISION_INCONCLUSIVE == "deleveraging_proxy_inconclusive"
    assert DECISION_SURVIVES == "deleveraging_proxy_survives_sensitivity_review"
    assert SECONDARY_NONE == "none"
    assert SECONDARY_PROMISING_SPARSE == "inconclusive_promising_sparse"


def test_models_define_source_quality_semantics():
    assert SOURCE_OI_BINANCE_VISION == "binance_vision_metrics"
    assert QUALITY_OI_HOURLY_SNAPSHOT == "exchange_reported_hourly_snapshot"
    assert SOURCE_PRICE_BINANCE_KLINE == "binance_kline_normalized"
    assert QUALITY_PRICE_CLOSE_PROXY == "close_price_proxy_not_fill_price"


def test_proxy_event_dataclass_instantiation():
    event = ProxyEvent(
        symbol="BTCUSDT",
        candidate_name=CANDIDATE_15M,
        event_label=EVENT_DOWN_FLUSH,
        signed_direction=1,
        bucket_start_ms=1600000000000,
        bucket_end_ms=1600000900000,
        event_time_ms=1600000900000,
        event_available_at_ms=1600001200000,
        entry_bar_start_ms=1600001200000,
        price_return=-0.025,
        oi_change=-0.04,
        oi_start=1000.0,
        oi_end=960.0,
        source="oi_and_price_joint",
        source_quality="15m_aligned_tick",
    )
    assert event.symbol == "BTCUSDT"
    assert event.price_return == -0.025
    assert event.source_quality == "15m_aligned_tick"
