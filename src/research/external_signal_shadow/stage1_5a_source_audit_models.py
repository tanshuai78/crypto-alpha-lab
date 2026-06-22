from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ExternalSignalSourceAuditDecision(Enum):
    PASSED = "source_audit_passed"
    SPARSE = "source_audit_sparse_inconclusive"
    FAILED = "source_audit_failed"
    OBSERVATION = "observation_only"


class ExternalSignalEventType(Enum):
    # Eligible for Replay
    DELISTING = "exchange_delisting_notice"
    FUTURES_LAUNCH = "futures_contract_launch"
    MARGIN_ENABLE = "margin_enablement"
    TRADING_PAIR_REMOVAL = "trading_pair_removal"
    TRADING_PAIR_ADDITION = "trading_pair_addition_for_existing_liquid_asset"
    EXCHANGE_STATUS = "major_exchange_status_event"

    # Observation-Only
    MAJOR_UNLOCK = "major_unlock_event"
    TOKEN_EMISSION = "large_scheduled_token_emission"
    NEW_COIN = "new_coin_listing"
    WHALE_DEPOSIT = "whale_deposit"


class TimestampQuality(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceProfile(Enum):
    GENERIC_JSON = "generic_json_announcement_rows"
    BINANCE_API_ROWS = "binance_official_announcements_like_rows"
    BINANCE_HTML = "binance_announcement_index_like_html"
    OKX_API_ROWS = "okx_official_announcements_like_rows"
    OKX_HTML = "okx_announcement_index_like_html"
    UNLOCK_ROWS = "unlock_calendar_like_rows"


class SourceStatus(Enum):
    HTML_TEXT_LOADED = "html_text_loaded"
    RAW_LOADED = "raw_loaded"
    NORMALIZED = "normalized"
    FAILED = "failed"


@dataclass
class RawSourcePayload:
    source_name: str
    source_profile: str
    source_url: str
    source_parent_url: str
    raw_payload_bytes: bytes
    collector_received_at_ms: int
    content_type: str = "application/json"
    file_path: Optional[str] = None


@dataclass
class NormalizedExternalEvent:
    event_id: str
    event_type: str
    symbol: str
    base_asset: str
    quote_asset: str
    venue: str
    source_name: str
    source_domain: str
    source_url: str
    source_parent_url: str
    source_published_at_ms: int
    event_time_ms: int
    available_at_ms: int
    collector_received_at_ms: int
    raw_payload_hash: str
    event_payload_hash: str
    raw_payload_size_bytes: int
    detail_url_available: bool
    source_integrity_level: str
    schema_version: str
    source_timestamp_quality: str
    historical_available_at_confidence: str
    edited_page_risk: bool
    hindsight_risk: bool
    magnitude: float
    base_asset_mapping_status: str
    trade_pair_mapping_status: str
    quarantine_reasons: List[str] = field(default_factory=list)
    replay_allowed: bool = False
    observation_only: bool = False


@dataclass
class SourceAuditFinding:
    rule_id: str
    severity: str  # "veto", "warning", "info"
    message: str
    field_name: Optional[str] = None
    finding_details: Optional[dict] = None
