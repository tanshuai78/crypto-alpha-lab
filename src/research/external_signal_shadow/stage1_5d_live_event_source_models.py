from dataclasses import dataclass
from enum import Enum


class LiveEventSourceDecision(Enum):
    OBSERVATION_IN_PROGRESS = "stage1_5d_smoke_observation_in_progress"
    OPERATIONAL_UNVALIDATED = "stage1_5d_operational_pass_event_detection_unvalidated"
    EVENT_DETECTION_PASSED = "stage1_5d_event_detection_passed"
    FAILED = "stage1_5d_smoke_failed"
    INVALID = "stage1_5d_smoke_invalid"


@dataclass(frozen=True)
class LiveFuturesLaunchEvent:
    event_id: str
    event_type: str
    source_name: str
    source_profile: str
    title: str
    symbols: tuple[str, ...]
    base_assets: tuple[str, ...]
    detected_at_ms: int
    available_at_ms: int
    source_published_at_ms: int | None = None
    source_published_at_ms_confidence: str = "low"
    published_time_source: str | None = None
    first_futures_bar_status: str = "not_yet_available"
    first_futures_bar_start_ms: int | None = None
    stage1_5c_research_context_label: str = "futures_launch_long_attention_12h_close_price_replay_only"
    signal_strength_score: float | None = None
    paper_trading_allowed: bool = False
    live_trading_allowed: bool = False
    execution_engine_allowed: bool = False
    alpha_interpretation_allowed: bool = False
    trade_signal_allowed: bool = False
    replay_context_label_only: bool = True


@dataclass(frozen=True)
class PollHeartbeat:
    poll_started_at_ms: int
    poll_completed_at_ms: int
    configured_poll_interval_sec: int
    poll_success: bool = True
    source_format_drift: bool = False
    schema_parse_error: bool = False
    heartbeat_gap: bool = False

    @property
    def poll_duration_ms(self) -> int:
        return self.poll_completed_at_ms - self.poll_started_at_ms
