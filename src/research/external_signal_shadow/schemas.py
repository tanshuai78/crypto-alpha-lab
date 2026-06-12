from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawSkillPayload:
    source: str
    source_skill: str
    fetched_at_ms: int
    raw_payload: dict[str, Any]
    available_at_ms: int | None = None
    data_quality: str = "unknown"

    def __post_init__(self) -> None:
        if not isinstance(self.fetched_at_ms, int):
            raise ValueError("fetched_at_ms must be an integer Unix ms timestamp")
        if self.available_at_ms is not None and not isinstance(self.available_at_ms, int):
            raise ValueError("available_at_ms must be an integer Unix ms timestamp")
        if not isinstance(self.raw_payload, dict):
            raise ValueError("raw_payload must be a dict")
        if self.available_at_ms is None:
            object.__setattr__(self, "available_at_ms", self.fetched_at_ms)
        object.__setattr__(self, "data_quality", self.data_quality.lower())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RawSkillPayload":
        return cls(**payload)


@dataclass(frozen=True)
class ConnectorRecord:
    status: str
    raw_payload_hash: str | None = None
    event: dict[str, Any] | None = None
    reject_reasons: tuple[str, ...] = field(default_factory=tuple)
    quarantine_reasons: tuple[str, ...] = field(default_factory=tuple)
