"""Data models, frozen constants, identity hashing functions, and enums for Stage 1.6B Canonical Official Source Capture."""

import hashlib
import json
import unicodedata
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Frozen Candidate Discovery Rule Version (copied from Stage 1.6A, independent contract)
CANDIDATE_DISCOVERY_RULE_VERSION = "candidate_discovery_rule_v1"

# Frozen Canonical Public-Web Profile Constants
SOURCE_PROFILE_ID = "binance_public_web_bapi_en_v1"
SOURCE_AUTHORITY = "binance_official_content"
TRANSPORT_SUPPORT_STATUS = "undocumented_public_web_profile"
BASE_URL = "https://www.binance.com"
ALLOWED_FINAL_HOST = "www.binance.com"

INDEX_PATH = "/bapi/composite/v1/public/cms/article/list/query"
INDEX_QUERY_TEMPLATE = "type=1&pageNo={page_no}&pageSize=50"
INDEX_SOURCE_SURFACE = "announcement_index"
INDEX_SOURCE_LOCALE = "en"
INDEX_REQUEST_VARIANT = "bapi_article_list_type_1_page_50_v1"

DETAIL_PATH = "/bapi/composite/v1/public/cms/article/detail/query"
DETAIL_QUERY_TEMPLATE = "articleCode={article_code}"
DETAIL_SOURCE_SURFACE = "announcement_detail"
DETAIL_SOURCE_LOCALE = "en"
DETAIL_REQUEST_VARIANT = "bapi_article_detail_query_v1"

REQUEST_HEADERS_PROFILE_VERSION = "stage1_6b_public_web_en_v1"
PROBE_COMMAND_VERSION = "source_profile_probe_v1"

CANONICAL_HEADERS: Dict[str, str] = {
    "Accept": "application/json",
    "Accept-Language": "en",
}

# Complete canonical header profile with explicit absence of Cookie and Authorization
CANONICAL_HEADER_PROFILE_DICT: Dict[str, Any] = {
    "Accept": "application/json",
    "Accept-Language": "en",
    "Authorization": None,
    "Cookie": None,
    "profile_version": REQUEST_HEADERS_PROFILE_VERSION,
}


def canonical_json(obj: Any) -> str:
    """Serialize data structure to deterministic, sorted, compact JSON string."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


CANONICAL_HEADERS_JSON = canonical_json(CANONICAL_HEADER_PROFILE_DICT)


def compute_request_headers_profile_sha256() -> str:
    """Compute SHA-256 fingerprint of the canonical request headers profile."""
    return hashlib.sha256(CANONICAL_HEADERS_JSON.encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class CaptureMode(str, Enum):
    HISTORICAL_BACKFILL = "historical_backfill"
    LIVE_OBSERVED = "live_observed"


class RequestClass(str, Enum):
    PROFILE_PROBE_INDEX = "profile_probe_index"
    PROFILE_PROBE_DETAIL = "profile_probe_detail"
    HISTORICAL_INDEX = "historical_index"
    HISTORICAL_DETAIL = "historical_detail"
    LIVE_INDEX = "live_index"
    LIVE_DETAIL = "live_detail"


class CandidateLane(str, Enum):
    LANE_A = "lane_a"
    LANE_B = "lane_b"


class TerminalReason(str, Enum):
    EPOCH_COMPLETE = "epoch_complete"
    OPERATOR_STOP = "operator_stop"
    TEST_BOUND = "test_bound"
    HISTORICAL_BACKFILL_COMPLETE = "historical_backfill_complete"
    STORAGE_EXHAUSTED = "storage_exhausted"
    DETAIL_FIRST_ATTEMPT_SLA_EXCEEDED = "detail_first_attempt_sla_exceeded"
    HTTP_FAILURE = "http_failure"
    TERMINAL_DETAIL_FAILURE = "terminal_detail_failure"
    PRECONDITION_FAILED = "precondition_failed"


# -----------------------------------------------------------------------------
# Identity Computations
# -----------------------------------------------------------------------------

def compute_list_payload_id(
    source_surface: str,
    source_locale: str,
    request_variant: str,
    raw_sha256: str,
) -> str:
    """Content identity for list raw bytes."""
    seed = f"{source_surface}|{source_locale}|{request_variant}|{raw_sha256}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def compute_request_observation_id(
    run_id: str,
    request_class: str,
    monotonic_request_seq: int,
) -> str:
    """Unique identity for a specific HTTP request attempt."""
    seed = f"{run_id}|{request_class}|{monotonic_request_seq}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def compute_list_capture_id(
    source_profile_id: str,
    canonical_requested_url: str,
    page_no: int,
    list_payload_id: str,
    request_observation_id: str,
) -> str:
    """Request observation identity for a specific list capture."""
    seed = f"{source_profile_id}|{canonical_requested_url}|{page_no}|{list_payload_id}|{request_observation_id}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def compute_article_discovery_id(
    source_profile_id: str,
    source_article_id: str,
    first_list_capture_id: str,
) -> str:
    """Identity for a discovered candidate article."""
    seed = f"{source_profile_id}|{source_article_id}|{first_list_capture_id}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def compute_detail_revision_id(
    source_article_id: str,
    source_surface: str,
    source_locale: str,
    request_variant: str,
    detail_raw_sha256: str,
) -> str:
    """Identity for canonical detail revision."""
    seed = f"{source_article_id}|{source_surface}|{source_locale}|{request_variant}|{detail_raw_sha256}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def compute_export_id(
    capture_mode: str,
    source_profile_id: str,
    checkpoint_id: str,
    ordered_authoritative_artifacts: List[Tuple[str, str, int]],
) -> str:
    """Identity for sealed export bundle derived from ordered artifact tuples (relative_path, sha256, byte_count)."""
    sorted_artifacts = sorted(ordered_authoritative_artifacts, key=lambda x: x[0])
    artifacts_json = canonical_json(sorted_artifacts)
    seed = f"{capture_mode}|{source_profile_id}|{checkpoint_id}|{artifacts_json}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------------
# Discovery Helpers
# -----------------------------------------------------------------------------

def normalize_discovery_text(text: str) -> str:
    """Normalize text using Unicode NFKC and casefold for robust match."""
    return unicodedata.normalize("NFKC", text).casefold()


def is_delisting_candidate(normalized_title: str) -> bool:
    """Determine if normalized title matches candidate_discovery_rule_v1."""
    return "binance futures" in normalized_title and "delist" in normalized_title


# -----------------------------------------------------------------------------
# Record Dataclasses
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ListCaptureRecord:
    schema_version: str
    capture_mode: str
    source_profile_id: str
    request_headers_profile_sha256: str
    run_id: str
    poll_seq: int
    record_seq: int
    request_observation_id: str
    list_payload_id: str
    list_capture_id: str
    page_no: int
    requested_url: str
    final_url: str
    http_status: int
    content_type: str
    raw_payload_sha256: str
    raw_payload_bytes: int
    raw_payload_relative_path: str
    t_list_receive_ms: int
    article_count: int
    captured_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArticleDiscoveryRecord:
    schema_version: str
    capture_mode: str
    source_profile_id: str
    source_article_id: str
    discovery_title: str
    discovery_rule_version: str
    first_list_capture_id: str
    notice_lineage_first_detected_at_ms: Optional[int]  # None for historical_backfill
    captured_at_ms: int
    record_seq: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DetailObservationRecord:
    schema_version: str
    capture_mode: str
    source_profile_id: str
    request_headers_profile_sha256: str
    run_id: str
    poll_seq: int
    record_seq: int
    request_observation_id: str
    source_article_id: str
    request_variant: str
    requested_url: str
    final_url: str
    http_status: int
    content_type: str
    raw_payload_sha256: Optional[str]
    raw_payload_bytes: Optional[int]
    raw_payload_relative_path: Optional[str]
    trust_validation_status: str  # e.g., "trusted", "waf_rejected", "empty_payload", "wrong_locale", "http_error"
    t_detail_receive_ms: int
    captured_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DetailRevisionRecord:
    schema_version: str
    capture_mode: str
    source_profile_id: str
    source_article_id: str
    source_surface: str
    source_locale: str
    request_variant: str
    detail_revision_id: str
    detail_raw_sha256: str
    raw_payload_relative_path: str
    t_detail_trusted_ms: int
    t_raw_persisted_ms: int
    captured_at_ms: int
    record_seq: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateState:
    source_article_id: str
    first_discovered_poll_seq: int
    first_discovered_at_ms: int
    lane: str  # "lane_a" or "lane_b"
    detail_attempt_count: int
    retry_cycle_count: int
    first_attempt_at_ms: Optional[int]
    last_attempt_at_ms: Optional[int]
    next_retry_at_ms: Optional[int]
    terminal_reason: Optional[str]  # e.g., "trusted_detail_observed", "terminal_detail_failure"
    trusted_detail_revision_id: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObserverCheckpointRecord:
    schema_version: str
    run_id: str
    capture_mode: str
    source_profile_id: str
    source_profile_attestation_sha256: str
    checkpoint_id: str
    prior_checkpoint_id: Optional[str]
    poll_seq: int
    monotonic_request_seq: int
    record_seq: int
    accounted_root_bytes: int
    stream_offsets: Dict[str, int]
    stream_last_hashes: Dict[str, str]
    candidate_states: Dict[str, Dict[str, Any]]
    heartbeat_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HistoricalCoverageRecord:
    schema_version: str
    run_id: str
    source_profile_id: str
    source_profile_attestation_sha256: str
    from_ms: int
    to_ms: int
    sweep_a_transcript: List[Tuple[int, str, int]]  # (page_no, source_article_id, source_published_at_ms)
    sweep_b_transcript: List[Tuple[int, str, int]]
    page_failures: List[Dict[str, Any]]
    candidate_terminal_counts: Dict[str, int]
    status: str  # "complete_stable", "incomplete_range", "incomplete_sweep_mismatch", "incomplete_page_failure"
    captured_at_ms: int
    sweep_a: Dict[str, Any] = field(default_factory=dict)
    sweep_b: Dict[str, Any] = field(default_factory=dict)
    frozen_candidate_count: int = 0
    candidate_terminal_count: int = 0
    pending_candidate_count: int = 0
    unattempted_candidate_count: int = 0
    final_checkpoint_valid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TerminalStatusRecord:
    schema_version: str
    run_id: str
    capture_mode: str
    source_profile_id: str
    status: str  # "complete" or "failure"
    terminal_reason: str
    final_checkpoint_id: Optional[str]
    terminated_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceProfileProbeAttestation:
    schema_version: str
    probe_command_version: str
    source_profile_id: str
    source_authority: str
    transport_support_status: str
    source_profile_sha256: str
    request_headers_profile_sha256: str
    probe_article_id: str
    index_requested_url: str
    index_final_url: str
    index_http_status: int
    index_content_type: str
    index_payload_bytes: int
    index_article_id_path: str
    detail_requested_url: str
    detail_final_url: str
    detail_http_status: int
    detail_content_type: str
    detail_payload_bytes: int
    detail_body_path: str
    probe_attested_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CaptureRunContract:
    schema_version: str
    run_id: str
    capture_mode: str
    source_profile_id: str
    source_profile_attestation_sha256: str
    run_started_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SealedExportManifest:
    schema_version: str
    export_id: str
    status: str  # "complete"
    capture_mode: str
    source_profile_id: str
    request_headers_profile_sha256: str
    checkpoint_id: str
    terminal_status_sha256: str
    historical_range_from_ms: Optional[int]
    historical_range_to_ms: Optional[int]
    historical_coverage_sha256: Optional[str]
    authoritative_artifacts: List[Dict[str, Any]]  # List of {"relative_path": ..., "sha256": ..., "byte_count": ...}
    sealed_at_ms: int

    # Explicit safety caps - ALL HARDCODED FALSE
    source_audit_passed: bool = False
    point_in_time_source_validated: bool = False
    market_data_coverage_passed: bool = False
    replay_allowed: bool = False
    risk_veto_candidate: bool = False
    trade_signal_allowed: bool = False
    paper_trading_allowed: bool = False
    live_trading_allowed: bool = False
    execution_engine_allowed: bool = False
    alpha_interpretation_allowed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
