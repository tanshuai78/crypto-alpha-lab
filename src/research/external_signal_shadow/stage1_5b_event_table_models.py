from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class EventTableDecision(Enum):
    READY = "stage1_5b_event_table_ready"
    SPARSE = "stage1_5b_event_table_sparse_inconclusive"
    FAILED = "stage1_5b_event_table_failed"


@dataclass
class ArticleEventRow:
    article_event_id: str
    stage1_5a_source_line: int
    source_name: str
    source_profile: str
    source_capture_method: str
    source_url: str
    source_detail_url: str
    source_domain: str
    title: str
    event_type: str
    source_published_at_ms: int
    event_time_ms: int
    available_at_ms: int
    available_at_policy: str
    symbols: List[str]
    symbol_count: int
    manual_review_status: str
    input_payload_hash: str
    article_payload_hash: str
    notice_time_ms: int
    effective_time_ms: Optional[int]
    effective_time_parse_status: str
    directional_hypothesis: str = "undefined"
    signed_direction: Optional[float] = None
    long_allowed: bool = False
    short_allowed: bool = False
    replay_allowed: bool = False
    stage1_5c_review_pending: bool = True
    stage1_5c_input_allowed: bool = True
    stage1_5c_replay_candidate_allowed: bool = False
    stage1_5c_requires_price_coverage_check: bool = True
    stage1_5c_requires_filter_group_assignment: bool = True
    stage1_5c_requires_baseline_evaluation: bool = True


@dataclass
class SymbolEventRow:
    symbol_event_id: str
    article_event_id: str
    event_type: str
    symbol: str
    base_asset: str
    quote_asset: str
    venue: str
    source_name: str
    source_profile: str
    source_detail_url: str
    source_parent_url: str
    title: str
    source_published_at_ms: int
    event_time_ms: int
    notice_time_ms: int
    effective_time_ms: Optional[int]
    effective_time_parse_status: str
    available_at_ms: int
    available_at_policy: str
    event_payload_hash: str
    source_quality: str
    source_audit_decision: str
    event_type_audit_decision: str
    stage1_5a_source_key: str
    stage1_5a_review_path: str
    stage1_5a_summary_path: str
    manual_review_status: str
    symbol_normalization_method: str
    market_pair_existence_verified: bool = False
    price_history_coverage_verified: bool = False
    tradability_verified: bool = False
    directional_hypothesis: str = "undefined"
    signed_direction: Optional[float] = None
    long_allowed: bool = False
    short_allowed: bool = False
    context_labels_allowed: bool = False
    replay_allowed: bool = False
    stage1_5c_review_pending: bool = True
    stage1_5c_input_allowed: bool = True
    stage1_5c_replay_candidate_allowed: bool = False
    paper_trading_allowed: bool = False
    live_trading_allowed: bool = False
