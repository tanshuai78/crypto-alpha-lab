from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CandidateEvent:
    candidate_name: str
    symbol: str
    event_time_ms: int
    event_available_at_ms: int
    entry_bar_start_ms: int
    signed_direction: int  # +1 long diagnostic, -1 short diagnostic
    metadata: dict[str, Any]
