from dataclasses import dataclass, field
from enum import Enum


class PriceCoverageDecision(Enum):
    READY = "stage1_5c1_price_coverage_ready_for_1_5c_rerun"
    SPARSE = "stage1_5c1_price_coverage_sparse_inconclusive"
    FAILED = "stage1_5c1_price_coverage_failed"
    INVALID = "stage1_5c1_price_coverage_invalid"


@dataclass
class PriceKlineRow:
    symbol: str
    bar_start_ms: int
    bar_end_ms: int
    open: float
    high: float
    low: float
    close: float
    quote_volume: float
    source: str
    source_quality: str

    # Hard safety fields
    api_key_used: bool = field(default=False, init=False)
    private_endpoint_used: bool = field(default=False, init=False)
    paper_trading_allowed: bool = field(default=False, init=False)
    live_trading_allowed: bool = field(default=False, init=False)


@dataclass
class PriceCoverageEventReport:
    symbol_event_id: str
    event_type: str
    symbol: str
    futures_symbol_status: str
    futures_kline_status: str
    spot_proxy_status: str
    replay_price_source_allowed: str
    stage1_5c_rerun_candidate: bool
    coverage_reject_reason: str | None = None

    # Hard safety fields
    spot_proxy_replay_allowed: bool = field(default=False, init=False)
    alpha_interpretation_allowed: bool = field(default=False, init=False)
