from dataclasses import dataclass
from enum import Enum


class ExternalCatalystReplayTopLevelDecision(Enum):
    COMPLETED = "stage1_5c_replay_completed"
    INVALID = "stage1_5c_replay_invalid"


class ExternalCatalystReplayCellDecision(Enum):
    PROMISING = "stage1_5c_cell_promising"
    SPARSE = "stage1_5c_cell_sparse_inconclusive"
    FAILED = "stage1_5c_cell_failed"
    INVALID = "stage1_5c_cell_invalid"


@dataclass
class ExternalCatalystReplayCandidate:
    symbol_event_id: str
    event_type: str
    signed_mode: str
    signed_direction: int
    symbol: str
    event_time_ms: int
    available_at_ms: int
    entry_delay_hours: int
    entry_candidate_time_ms: int
    entry_bar_start_ms: int
    entry_price: float
    price_history_coverage_verified: bool
    market_pair_existence_verified: bool
    liquidity_proxy_verified: bool
    close_price_replay_only: bool = True
    execution_feasibility_unknown: bool = True
    replay_allowed: bool = True
    paper_trading_allowed: bool = False
    live_trading_allowed: bool = False
    short_execution_intent_allowed: bool = False
    execution_engine_allowed: bool = False


@dataclass
class ExternalCatalystReplayResult:
    symbol_event_id: str
    event_type: str
    signed_mode: str
    signed_direction: int
    symbol: str
    entry_delay_hours: int
    forward_window_hours: int
    cost_bps: int
    entry_price: float
    exit_price: float
    long_gross_return_bps: float
    signed_gross_return_bps: float
    net_return_bps: float
    forward_window_complete: bool
