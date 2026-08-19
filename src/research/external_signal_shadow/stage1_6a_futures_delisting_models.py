"""
Stage 1.6A USD-M Futures Delisting Data Models, Enums, and Identity Functions.
Design Reference: docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

STAGE1_6A_MODELS_VERSION = "stage1_6a_models_v1"
CANDIDATE_DISCOVERY_RULE_VERSION = "candidate_discovery_rule_v1"
CANDIDATE_RECALL_PROBE_VERSION = "candidate_recall_probe_v1"
SEMANTIC_EXTRACTOR_VERSION = "stage1_6a_extractor_v1"
BODY_NORMALIZATION_VERSION = "stage1_6a_norm_v1"
AUDIT_METRIC_DEFINITION_VERSION = "stage1_6a_audit_metric_v1"
SEMANTIC_AUTHORITY_LOCALE = "en"
SEMANTIC_AUTHORITY_VARIANT = "canonical_binance_english_detail"


class CaptureMode(str, Enum):
    HISTORICAL_BACKFILL = "historical_backfill"
    LIVE_OBSERVED = "live_observed"


class SourceSurface(str, Enum):
    ANNOUNCEMENT_INDEX = "announcement_index"
    ANNOUNCEMENT_DETAIL = "announcement_detail"


class FactParseStatus(str, Enum):
    PRESENT = "present"
    NOT_STATED = "not_stated"
    UNPARSEABLE = "unparseable"
    CONFLICTING = "conflicting"
    OUT_OF_SCOPE = "out_of_scope"


class CaptureTimeStatus(str, Enum):
    PRESENT = "present"
    HISTORICAL_UNKNOWN = "historical_unknown"
    NOT_OBSERVED = "not_observed"


class MarginFamily(str, Enum):
    USD_M = "USD_M"
    COIN_M = "COIN_M"
    UNKNOWN = "unknown"


class ContractType(str, Enum):
    PERPETUAL = "PERPETUAL"
    DELIVERY = "DELIVERY"
    UNKNOWN = "unknown"


class UnderlyingFamily(str, Enum):
    CRYPTO_ASSET = "crypto_asset"
    TRADFI_EQUITY = "tradfi_equity"
    COMMODITY = "commodity"
    UNKNOWN = "unknown"


class OrderRestrictionType(str, Enum):
    REDUCE_ONLY_ONLY = "reduce_only_only"
    NO_NEW_POSITIONS = "no_new_positions"
    NO_NEW_ORDERS = "no_new_orders"
    UNKNOWN = "unknown"


class EvidenceLocationKind(str, Enum):
    NORMALIZED_TEXT_SPAN = "normalized_text_span"
    JSON_POINTER = "json_pointer"
    DOM_PATH = "dom_path"


def compute_list_capture_id(
    source_surface: str,
    source_locale: str,
    request_variant: str,
    list_raw_sha256: str,
) -> str:
    seed = f"{source_surface}|{source_locale}|{request_variant}|{list_raw_sha256}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def compute_detail_revision_id(
    source_article_id: str,
    source_surface: str,
    source_locale: str,
    request_variant: str,
    detail_raw_sha256: str,
) -> str:
    seed = f"{source_article_id}|{source_surface}|{source_locale}|{request_variant}|{detail_raw_sha256}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def compute_semantic_extraction_id(
    detail_revision_id: str,
    semantic_extractor_version: str,
    body_normalization_version: str,
    canonical_fact_fingerprint: str,
) -> str:
    seed = (
        f"{detail_revision_id}|{semantic_extractor_version}|"
        f"{body_normalization_version}|{canonical_fact_fingerprint}"
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def compute_delisting_contract_id(
    source_article_id: str,
    detail_revision_id: str,
    canonical_symbol: str,
    margin_family: str,
    contract_type: str,
    underlying_family: str,
) -> str:
    seed = (
        f"{source_article_id}|{detail_revision_id}|{canonical_symbol}|"
        f"{margin_family}|{contract_type}|{underlying_family}"
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def canonical_json_fingerprint(data: Any) -> str:
    """Produces deterministic canonical JSON string for fingerprinting."""
    canonical_str = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidencePointer:
    detail_revision_id: str
    detail_raw_sha256: str
    semantic_extraction_id: str
    semantic_extractor_version: str
    body_normalization_version: str
    location_kind: str
    location_value: str
    normalized_body_utf8_byte_start: int
    normalized_body_utf8_byte_end: int
    excerpt: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleFact:
    fact_parse_status: str
    capture_time_status: str
    timestamp_ms: Optional[int] = None
    order_restriction_type: Optional[str] = None
    source_detail_revision_id: Optional[str] = None
    source_semantic_extraction_id: Optional[str] = None
    fact_available_at_ms: Optional[int] = None  # Explicit nullable timestamp per P1-A
    evidence: Optional[EvidencePointer] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.evidence:
            res["evidence"] = self.evidence.to_dict()
        return res


@dataclass(frozen=True)
class CandidateDiscoveryItem:
    source_article_id: str
    title: str
    first_list_capture_id: str
    notice_lineage_first_detected_at_ms: Optional[int]
    capture_mode: str = CaptureMode.HISTORICAL_BACKFILL.value
    discovery_rule_version: str = CANDIDATE_DISCOVERY_RULE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditCandidateManifest:
    manifest_id: str
    discovery_rule_version: str
    items: List[CandidateDiscoveryItem]
    manifest_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "discovery_rule_version": self.discovery_rule_version,
            "items": [item.to_dict() for item in self.items],
            "manifest_sha256": self.manifest_sha256,
        }


@dataclass(frozen=True)
class DelistingContract:
    contract_id: str
    parent_article_id: str
    detail_revision_id: str
    canonical_symbol: str
    margin_family: str
    contract_type: str
    underlying_family: str
    is_in_scope: bool
    source_audit_eligible: bool
    settlement_time: Optional[ScheduleFact] = None
    order_restriction: Optional[ScheduleFact] = None
    last_trading_time: Optional[ScheduleFact] = None
    delisting_complete_time: Optional[ScheduleFact] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "contract_id": self.contract_id,
            "parent_article_id": self.parent_article_id,
            "detail_revision_id": self.detail_revision_id,
            "canonical_symbol": self.canonical_symbol,
            "margin_family": self.margin_family,
            "contract_type": self.contract_type,
            "underlying_family": self.underlying_family,
            "is_in_scope": self.is_in_scope,
            "source_audit_eligible": self.source_audit_eligible,
        }
        if self.settlement_time:
            res["settlement_time"] = self.settlement_time.to_dict()
        if self.order_restriction:
            res["order_restriction"] = self.order_restriction.to_dict()
        if self.last_trading_time:
            res["last_trading_time"] = self.last_trading_time.to_dict()
        if self.delisting_complete_time:
            res["delisting_complete_time"] = self.delisting_complete_time.to_dict()
        return res
