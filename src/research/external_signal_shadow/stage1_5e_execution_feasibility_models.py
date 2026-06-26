from dataclasses import asdict, dataclass
from enum import Enum


class ExecutionFeasibilityDecision(str, Enum):
    READY_FOR_LIVE_DEPTH_OBSERVER = "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer"
    PROXY_FAILED = "stage1_5e_execution_feasibility_proxy_failed"
    INCONCLUSIVE_DEPTH_MISSING = "stage1_5e_execution_feasibility_inconclusive_depth_missing"
    INCONCLUSIVE_PENDING_STAGE1_5D = "stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d"
    INVALID = "stage1_5e_execution_feasibility_invalid"


@dataclass(frozen=True)
class ExecutionFeasibilityCandidate:
    symbol: str
    symbol_event_id: str
    event_type: str
    signed_mode: str
    entry_delay_hours: int
    filter_group: str
    entry_time_ms: int
    execution_engine_allowed: bool = False
    paper_trading_allowed: bool = False
    live_trading_allowed: bool = False
    alpha_interpretation_allowed: bool = False
    execution_feasibility_proven: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
