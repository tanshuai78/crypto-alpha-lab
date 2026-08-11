from dataclasses import asdict, dataclass
from enum import Enum


class LiveDepthObserverDecision(str, Enum):
    BOOTSTRAP_WATERMARK_ONLY = "stage1_5f_observer_bootstrap_watermark_only"
    RUNNING_NO_NEW_EVENT = "stage1_5f_observer_running_no_new_event"
    EVENT_OBSERVATION_IN_PROGRESS = "stage1_5f_observer_event_observation_in_progress"
    DEPTH_EVIDENCE_COLLECTED = "stage1_5f_observer_depth_evidence_collected"
    INVALID = "stage1_5f_observer_invalid"
    FAILED = "stage1_5f_observer_failed"


@dataclass(frozen=True)
class Watermark:
    watermark_version: int = 1
    max_seen_detected_at_ms: int = 0
    seen_event_ids: list[str] = None
    seen_source_article_ids: list[str] = None
    seen_stable_event_keys: list[str] = None
    updated_at_ms: int = 0
    watermark_schema_version: int = 1
    bootstrap_max_seen_detected_at_ms: int | None = None
    bootstrap_created_at_ms: int | None = None
    bootstrap_source_root: str = ""
    bootstrap_root_id: str = ""

    def __post_init__(self):
        # Handle frozen list defaults
        if self.seen_event_ids is None:
            object.__setattr__(self, "seen_event_ids", [])
        if self.seen_source_article_ids is None:
            object.__setattr__(self, "seen_source_article_ids", [])
        if self.seen_stable_event_keys is None:
            object.__setattr__(self, "seen_stable_event_keys", [])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class EventSymbolState:
    event_symbol_id: str
    event_id: str = ""
    symbol: str = ""
    detected_at_ms: int = 0
    observation_started_at_ms: int | None = None
    observation_window_end_ms: int | None = None
    status: str = "active"  # active, completed, expired, failed, pending_*
    depth_snapshot_count: int = 0
    last_snapshot_ms: int = 0
    max_gap_ms: int = 0
    coverage_ratio_pass: bool = False
    max_gap_pass: bool = False
    research_result_valid: bool = False

    # Launch Gate & Anchor Fields (Schema Version 3)
    observer_state_schema_version: int = 3
    source_contract_status: str | None = None
    pending_source_event_unvalidated: bool = False
    required_source_revision: str | None = None
    pending_reason: str | None = None
    anchor_resolution_started_at_ms: int | None = None
    anchor_resolution_deadline_ms: int | None = None
    anchor_resolution_retry_count: int = 0
    anchor_resolution_last_attempt_at_ms: int | None = None
    legacy_source_revision_wait_started_at_ms: int | None = None
    legacy_source_revision_wait_deadline_ms: int | None = None
    symbol_visibility_deadline_ms: int | None = None
    capacity_deferred_at_ms: int | None = None
    next_capacity_check_at_ms: int | None = None
    observation_anchor_ms: int | None = None
    observation_anchor_basis: str = ""
    observation_anchor_confidence: str = ""
    observation_anchor_candidates: dict | None = None
    observation_anchor_disagreement_max_ms: int = 0
    observation_anchor_conflict_active: bool = False
    observation_admitted_at_ms: int | None = None
    observation_window_start_ms: int | None = None
    first_depth_request_at_ms: int | None = None
    first_depth_request_latency_ms: int | None = None
    first_healthy_snapshot_at_ms: int | None = None
    first_valid_book_latency_ms: int | None = None
    market_valid_book_latency_after_first_request_ms: int | None = None
    evidence_start_class: str = ""
    source_article_id: str = ""
    stable_event_symbol_key: str = ""
    stable_event_key: str = ""
    latest_source_event_id: str = ""
    latest_event_payload_hash: str = ""
    revision_seen_count: int = 1
    event_batch_id: str = ""
    batch_candidate_set_hash: str = ""
    batch_symbol_count: int | None = None
    batch_registration_status: str = ""
    acceptance_id: str = ""
    acceptance_state: str = ""
    first_seen_at_ms: int | None = None
    announcement_capture_time_ms: int | None = None
    next_admission_check_at_ms: int | None = None
    next_anchor_resolution_at_ms: int | None = None
    last_anchor_resolution_at_ms: int | None = None
    anchor_resolution_started_at_ms: int | None = None
    anchor_resolution_deadline_ms: int | None = None
    last_anchor_resolution_sources: list[str] | None = None
    bootstrap_watermark_max_seen_detected_at_ms: int | None = None
    admission_watermark_at_first_seen_ms: int | None = None
    announcement_capture_post_bootstrap_watermark: bool | None = None
    launch_anchor_post_bootstrap_watermark: bool | None = None
    capacity_defer_count: int = 0
    anchor_resolution_attempt_count: int = 0
    pending_terminal_reason: str = ""
    expected_snapshot_count: int = 0
    unique_snapshot_bucket_count: int = 0
    duplicate_snapshot_row_count: int = 0
    out_of_window_snapshot_row_count: int = 0
    missing_snapshot_bucket_count: int = 0
    pre_start_expected_snapshot_count: int = 0
    pre_start_missing_snapshot_count: int = 0
    coverage_ratio: float = 0.0
    clean_start_sla_pass: bool = False
    clean_evidence_start_allowed: bool = False
    attempted_snapshot_count: int = 0
    successful_http_snapshot_count: int = 0
    valid_book_snapshot_count: int = 0
    empty_book_snapshot_count: int = 0
    invalid_book_snapshot_count: int = 0

    # Terminal Hygiene Fields
    terminal_hygiene_id: str = ""
    terminal_status: str = ""
    terminal_reason: str = ""
    terminal_at_ms: int | None = None
    consumable_by_stage1_5g: bool | None = None
    source_event_payload_hash: str = ""
    terminal_ignored_revision_seen_count: int = 0
    duplicate_suppressed_count: int = 0
    last_duplicate_seen_at_ms: int | None = None
    diagnostic_sample_reserved: bool = False
    diagnostic_expected: bool = False
    diagnostic_emitted: bool = False
    terminal_audit_type: str = ""
    terminal_audit_row: dict | None = None

    # Lineage and Contamination Fields (Schema V3)
    source_detail_url_normalized: str = ""
    source_published_at_ms: int | None = None
    formal_event_contract_version: int | None = None
    formal_event_consumable_by_stage1_5f: bool | None = None
    symbol_identity_validation_status: str | None = None
    launch_anchor_evidence_level: str | None = None
    effective_observation_anchor_source: str | None = None
    launch_anchor_validation_status: str | None = None
    source_anchor_contract_hash: str = ""
    admission_anchor_contract_hash: str = ""
    latest_anchor_contract_hash: str = ""
    anchor_contract_version: int | None = None
    anchor_precedence_policy: str = ""
    anchor_contract_decision_at_ms: int | None = None
    admission_anchor_evidence_level: str = ""
    latest_anchor_evidence_level: str = ""
    admission_max_evidence_class: str = ""
    latest_max_evidence_class: str = ""
    anchor_contract_revision_count: int = 0
    applied_schedule_revision_ids: list[str] | None = None
    observation_anchor_revision_contaminated: bool = False
    anchor_revision_contamination_reason: str = ""

    def __post_init__(self):
        if self.observation_anchor_candidates is None:
            object.__setattr__(self, "observation_anchor_candidates", {})
        if self.last_anchor_resolution_sources is None:
            object.__setattr__(self, "last_anchor_resolution_sources", [])
        if self.applied_schedule_revision_ids is None:
            object.__setattr__(self, "applied_schedule_revision_ids", [])

        nullable_ts_fields = (
            "observation_anchor_ms",
            "first_depth_request_at_ms",
            "first_healthy_snapshot_at_ms",
            "first_seen_at_ms",
            "announcement_capture_time_ms",
            "next_admission_check_at_ms",
            "next_anchor_resolution_at_ms",
            "last_anchor_resolution_at_ms",
            "anchor_resolution_started_at_ms",
            "anchor_resolution_deadline_ms",
            "bootstrap_watermark_max_seen_detected_at_ms",
            "admission_watermark_at_first_seen_ms",
            "terminal_at_ms",
            "last_duplicate_seen_at_ms",
        )
        for field in nullable_ts_fields:
            if getattr(self, field) == 0:
                object.__setattr__(self, field, None)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        clean_data = dict(data)
        nullable_ts_fields = (
            "observation_anchor_ms",
            "first_depth_request_at_ms",
            "first_healthy_snapshot_at_ms",
            "first_seen_at_ms",
            "announcement_capture_time_ms",
            "next_admission_check_at_ms",
            "next_anchor_resolution_at_ms",
            "last_anchor_resolution_at_ms",
            "anchor_resolution_started_at_ms",
            "anchor_resolution_deadline_ms",
            "bootstrap_watermark_max_seen_detected_at_ms",
            "admission_watermark_at_first_seen_ms",
            "terminal_at_ms",
            "last_duplicate_seen_at_ms",
        )
        for field in nullable_ts_fields:
            if clean_data.get(field) == 0:
                clean_data[field] = None
        return cls(**{k: v for k, v in clean_data.items() if k in cls.__dataclass_fields__})



@dataclass(frozen=True)
class DepthSnapshot:
    event_symbol_id: str
    symbol: str
    fetched_at_ms: int
    exchange_time_ms: int | None = None
    best_bid: float | None = None
    best_ask: float | None = None
    spread_bps: float | None = None
    top_bid_depth_usdt: float = 0.0
    top_ask_depth_usdt: float = 0.0
    buy_slippage_bps: float | None = None
    sell_slippage_bps: float | None = None
    slippage_status: str = "ok"  # e.g., "ok", "insufficient_depth", "invalid_depth"
    depth_status: str = "healthy"  # e.g., "healthy", "invalid"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class RequestManifestRow:
    requested_host: str
    requested_path: str = ""
    requested_url_hash: str = ""
    final_url_hash: str = ""
    http_status: int = 0
    payload_size_bytes: int = 0
    response_payload_hash: str = ""
    retry_count: int = 0
    error: str | None = None
    fetched_at_ms: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class HeartbeatRow:
    poll_index: int
    poll_at_ms: int = 0
    active_count: int = 0
    completed_count: int = 0
    last_error: str | None = None
    budget_status: str = "ok"
    watermark_updated_at_ms: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class LiveDepthObserverSummary:
    decision: str
    bootstrap_watermark_allowed: bool
    live_depth_observation_allowed: bool
    stage1_5d_summary_path: str
    stage1_5e_summary_path: str | None
    stage1_5e_context_missing: bool
    stage1_5e_context_suspicious: bool
    watermark_present: bool
    watermark_version: int | None
    max_seen_detected_at_ms: int
    pre_watermark_events_ignored: int
    post_watermark_events_accepted: int
    active_observation_count: int
    completed_observation_count: int
    expired_observation_count: int
    failed_observation_count: int
    min_snapshot_count_required: int
    total_snapshots_collected: int
    request_success_rate: float
    total_requests_made: int
    failed_requests_count: int
    consecutive_network_errors: int
    max_consecutive_network_errors_seen: int
    last_heartbeat_at_ms: int
    heartbeat_count: int
    pending_launch_observation_count: int = 0
    pending_launch_time_in_future_count: int = 0
    pending_launch_anchor_missing_count: int = 0
    pending_anchor_conflict_count: int = 0
    pending_observation_capacity_count: int = 0
    active_expected_snapshot_count: int = 0
    active_unique_snapshot_bucket_count: int = 0
    active_missing_snapshot_bucket_count: int = 0
    active_out_of_window_snapshot_row_count: int = 0
    terminal_ignored_pre_bootstrap_anchor_count: int = 0
    historical_anchor_ignored_count: int = 0
    rejected_event_symbol_count: int = 0
    historical_anchor_duplicate_suppressed_total: int = 0
    rejected_event_symbol_duplicate_suppressed_total: int = 0
    rejected_missing_identity_count: int = 0
    rejected_missing_reason_count: int = 0
    rejection_hygiene_diagnostic_count: int = 0
    terminal_ignored_revision_seen_count: int = 0
    terminal_state_hits_this_poll: int = 0
    historical_anchor_newly_ignored_this_poll: int = 0
    bootstrap_watermark_missing_diagnostic_count: int = 0
    malformed_terminal_diagnostic_count: int = 0
    multi_symbol_candidate_set_event_rows_count: int = 0
    multi_symbol_candidate_symbol_rows_admitted_count: int = 0
    multi_symbol_candidate_symbol_rows_rejected_count: int = 0
    multi_symbol_candidate_symbol_rows_pending_count: int = 0
    duplicate_suppressed_count: int = 0
    identity_collision_blocked_count: int = 0
    active_anchor_revision_contaminated_count: int = 0
    completed_anchor_revision_contaminated_count: int = 0
    anchor_contract_revision_count: int = 0
    anchor_contract_lineage_mismatch_count: int = 0
    schedule_revision_registry_orphan_count: int = 0
    schedule_revision_registry_ambiguous_count: int = 0
    stage1_5d_gate_mode: str = "unknown"
    stage1_5d_runtime_gate_path: str = ""
    stage1_5d_runtime_gate_decision: str = ""
    stage1_5d_runtime_gate_last_validated_at_ms: int | None = None
    stage1_5d_runtime_gate_stale: bool = False
    stage1_5d_runtime_gate_invalid_count: int = 0
    cross_root_upstream_summary_dependency: bool = False
    historical_stage1_5d_gate_reason: str = ""
    block_new_event_admission: bool = False
    runtime_gate_diagnostic_count: int = 0
    # L0/L1 Risk & Compliance controls hard-gates:
    execution_feasibility_claim_allowed: bool = False
    trade_signal_allowed: bool = False
    paper_trading_allowed: bool = False
    live_trading_allowed: bool = False
    execution_engine_allowed: bool = False
    alpha_interpretation_allowed: bool = False
    research_result_valid: bool = False
    blocker: str | None = None
    summary_generated_at_ms: int = 0
    consumer_process_instance_id: str = ""
    consumer_root_id: str = ""
    consumer_startup_commit_sha: str = ""
    consumer_root_contract_sha256: str = ""
    consumer_runtime_manifest_sha256: str = ""
    consumer_static_attestation_verified: bool = False
    consumer_runtime_attestation_verified: bool = False
    consumer_runtime_attestation_compromised: bool = False

    def to_dict(self) -> dict:

        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
