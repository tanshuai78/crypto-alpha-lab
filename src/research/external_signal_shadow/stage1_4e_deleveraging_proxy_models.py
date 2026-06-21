from dataclasses import dataclass

# Candidate Names
CANDIDATE_15M = "deleveraging_proxy_15m"
CANDIDATE_1H = "deleveraging_proxy_1h"

# Event Labels
EVENT_DOWN_FLUSH = "down_flush_deleveraging_proxy"
EVENT_UP_SQUEEZE = "up_squeeze_deleveraging_proxy"

# Decisions
DECISION_FAILED = "deleveraging_proxy_failed"
DECISION_INCONCLUSIVE = "deleveraging_proxy_inconclusive"
DECISION_SURVIVES = "deleveraging_proxy_survives_sensitivity_review"

# Secondary Status
SECONDARY_NONE = "none"
SECONDARY_PROMISING_SPARSE = "inconclusive_promising_sparse"

# Source Quality Semantics
SOURCE_OI_BINANCE_VISION = "binance_vision_metrics"
QUALITY_OI_HOURLY_SNAPSHOT = "exchange_reported_hourly_snapshot"
SOURCE_PRICE_BINANCE_KLINE = "binance_kline_normalized"
QUALITY_PRICE_CLOSE_PROXY = "close_price_proxy_not_fill_price"


@dataclass(frozen=True)
class ProxyEvent:
    symbol: str
    candidate_name: str
    event_label: str
    signed_direction: int
    bucket_start_ms: int
    bucket_end_ms: int
    event_time_ms: int
    event_available_at_ms: int
    entry_bar_start_ms: int | None
    price_return: float
    oi_change: float
    oi_start: float
    oi_end: float
    source: str
    source_quality: str
