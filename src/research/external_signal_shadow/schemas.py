from dataclasses import dataclass, field
from typing import Any

# Allowed values for each field_confidence key when data_quality == "manual_export".
FIELD_CONFIDENCE_ALLOWED: dict[str, set[str]] = {
    "event_time_ms": {"source_provided", "available_at_fallback"},
    "symbol": {"source_provided", "normalized", "missing"},
    "score": {"source_native", "manual_scaled", "missing"},
}

# Required provenance fields when data_quality == "manual_export".
_MANUAL_REQUIRED_FIELDS = (
    "source_vendor",
    "source_surface",
    "source_capture_method",
    "capture_id",
    "captured_by",
    "source_observed_at_ms",
    "manual_transform_version",
    "field_confidence",
)


@dataclass(frozen=True)
class RawSkillPayload:
    source: str
    source_skill: str
    fetched_at_ms: int
    raw_payload: dict[str, Any]
    available_at_ms: int | None = None
    data_quality: str = "unknown"
    source_vendor: str | None = None
    source_surface: str | None = None
    source_capture_method: str | None = None
    capture_id: str | None = None
    captured_by: str | None = None
    source_observed_at_ms: int | None = None
    manual_transform_version: str | None = None
    field_confidence: dict[str, str] | None = None

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

        if self.data_quality == "manual_export":
            self._validate_manual_provenance()

    def _validate_manual_provenance(self) -> None:
        from configs import base

        # 1. All required provenance fields must be present.
        for f in _MANUAL_REQUIRED_FIELDS:
            val = getattr(self, f, None)
            if val is None:
                raise ValueError(
                    f"{f} is required when data_quality is manual_export"
                )

        # 2. source_observed_at_ms must be int.
        if not isinstance(self.source_observed_at_ms, int):
            raise ValueError(
                "source_observed_at_ms int is required when data_quality is manual_export"
            )

        # 3. field_confidence must be a dict.
        if not isinstance(self.field_confidence, dict):
            raise ValueError(
                "field_confidence dict is required when data_quality is manual_export"
            )

        # 4. Validate source profile matches configs constants.
        profile_match = (
            self.source_vendor == base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_VENDOR
            and self.source_surface == base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SURFACE
            and self.source_capture_method == base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE_CAPTURE_METHOD
        )
        if not profile_match:
            raise ValueError(
                "source profile mismatch: source_vendor/surface/capture_method do not match "
                "the registered gate_marketanalysis_manual_export source profile"
            )

        # 5. Validate field_confidence values are in the allowed set.
        for key, val in self.field_confidence.items():
            allowed = FIELD_CONFIDENCE_ALLOWED.get(key)
            if allowed is not None and val not in allowed:
                raise ValueError(
                    f"field_confidence['{key}'] value '{val}' is not in allowed set {allowed}"
                )

        # 6. Validate available_at_fallback consistency.
        event_time_policy = self.raw_payload.get("metadata", {}).get("event_time_policy")
        fc_event_time = self.field_confidence.get("event_time_ms")

        if fc_event_time == "available_at_fallback":
            # Payload event_time_ms must equal available_at_ms.
            raw_event_time_ms = self.raw_payload.get("event_time_ms")
            if raw_event_time_ms != self.available_at_ms:
                raise ValueError(
                    "available_at_fallback: raw_payload.event_time_ms must equal available_at_ms "
                    f"(got {raw_event_time_ms} != {self.available_at_ms})"
                )
            if event_time_policy not in (None, "available_at_fallback"):
                raise ValueError(
                    "available_at_fallback: event_time_policy in metadata must be 'available_at_fallback' "
                    "when field_confidence[event_time_ms] == 'available_at_fallback'"
                )

        if event_time_policy == "available_at_fallback" and fc_event_time != "available_at_fallback":
            raise ValueError(
                "available_at_fallback: field_confidence[event_time_ms] must be 'available_at_fallback' "
                "when event_time_policy == 'available_at_fallback'"
            )

        # 7. score_interpretation_allowed must be False when present.
        if self.raw_payload.get("score_interpretation_allowed") is True:
            raise ValueError(
                "score_interpretation_allowed must be False for manual_export source payloads"
            )

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
