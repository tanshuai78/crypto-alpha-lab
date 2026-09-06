"""Models, canonical identities, and validation schemas for Stage 1.6E-B."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

SHA256_REGEX = re.compile(r"^[0-9a-f]{64}$")


def validate_sha256(val: Any) -> str:
    if not isinstance(val, str) or not SHA256_REGEX.match(val):
        raise ValueError(f"sha256_invalid: {val}")
    return val


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str | bytes) -> str:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()


def stage1_6e_b_permissions() -> dict[str, bool]:
    return {
        "RISK_LIVE_TRADING_ENABLED": False,
        "execution_feasibility_claim_allowed": False,
        "net_cost_or_profit_claim_allowed": False,
        "replay_allowed": False,
        "alpha_interpretation_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "private_api_allowed": False,
        "authenticated_api_allowed": False,
        "order_api_allowed": False,
    }


def validate_permissions(perms: Any) -> dict[str, bool]:
    if not isinstance(perms, dict):
        raise ValueError("permissions_not_dict")
    expected = stage1_6e_b_permissions()
    if set(perms.keys()) != set(expected.keys()):
        raise ValueError("permissions_keys_mismatch")
    for k, v in perms.items():
        if type(v) is not bool or v is not False:
            raise ValueError(f"permission_not_false_bool: {k}={v}")
    return expected


# -----------------------------------------------------------------------------
# Environment Authority Receipt
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvironmentAuthorityReceipt:
    schema_version: str
    root_kind: str
    e_a_manifest_id: str
    e_a_manifest_sha256: str
    e_a_environment_attestation_sha256: str
    e_b_execution_environment_attestation_sha256: str
    permissions: dict[str, bool]
    receipt_id: str

    @classmethod
    def create(
        cls,
        *,
        root_kind: str,
        e_a_manifest_id: str,
        e_a_manifest_sha256: str,
        e_a_environment_attestation_sha256: str,
        e_b_execution_environment_attestation_sha256: str,
    ) -> EnvironmentAuthorityReceipt:
        if root_kind not in ("supervisor", "event"):
            raise ValueError(f"invalid_root_kind: {root_kind}")
        validate_sha256(e_a_manifest_id)
        validate_sha256(e_a_manifest_sha256)
        validate_sha256(e_a_environment_attestation_sha256)
        validate_sha256(e_b_execution_environment_attestation_sha256)

        base_dict = {
            "schema_version": "stage1_6e_b_environment_authority_receipt_v1",
            "root_kind": root_kind,
            "e_a_manifest_id": e_a_manifest_id,
            "e_a_manifest_sha256": e_a_manifest_sha256,
            "e_a_environment_attestation_sha256": e_a_environment_attestation_sha256,
            "e_b_execution_environment_attestation_sha256": e_b_execution_environment_attestation_sha256,
        }
        receipt_id = sha256_hex(canonical_json(base_dict))
        return cls(
            schema_version="stage1_6e_b_environment_authority_receipt_v1",
            root_kind=root_kind,
            e_a_manifest_id=e_a_manifest_id,
            e_a_manifest_sha256=e_a_manifest_sha256,
            e_a_environment_attestation_sha256=e_a_environment_attestation_sha256,
            e_b_execution_environment_attestation_sha256=e_b_execution_environment_attestation_sha256,
            permissions=stage1_6e_b_permissions(),
            receipt_id=receipt_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "root_kind": self.root_kind,
            "e_a_manifest_id": self.e_a_manifest_id,
            "e_a_manifest_sha256": self.e_a_manifest_sha256,
            "e_a_environment_attestation_sha256": self.e_a_environment_attestation_sha256,
            "e_b_execution_environment_attestation_sha256": self.e_b_execution_environment_attestation_sha256,
            "permissions": self.permissions,
            "receipt_id": self.receipt_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnvironmentAuthorityReceipt:
        expected_keys = {
            "schema_version",
            "root_kind",
            "e_a_manifest_id",
            "e_a_manifest_sha256",
            "e_a_environment_attestation_sha256",
            "e_b_execution_environment_attestation_sha256",
            "permissions",
            "receipt_id",
        }
        if set(data.keys()) != expected_keys:
            raise ValueError("receipt_keys_mismatch")
        if data["schema_version"] != "stage1_6e_b_environment_authority_receipt_v1":
            raise ValueError("receipt_schema_version_invalid")
        if data["root_kind"] not in ("supervisor", "event"):
            raise ValueError("receipt_root_kind_invalid")
        validate_sha256(data["e_a_manifest_id"])
        validate_sha256(data["e_a_manifest_sha256"])
        validate_sha256(data["e_a_environment_attestation_sha256"])
        validate_sha256(data["e_b_execution_environment_attestation_sha256"])
        validate_permissions(data["permissions"])
        validate_sha256(data["receipt_id"])

        base_dict = {
            "schema_version": data["schema_version"],
            "root_kind": data["root_kind"],
            "e_a_manifest_id": data["e_a_manifest_id"],
            "e_a_manifest_sha256": data["e_a_manifest_sha256"],
            "e_a_environment_attestation_sha256": data["e_a_environment_attestation_sha256"],
            "e_b_execution_environment_attestation_sha256": data["e_b_execution_environment_attestation_sha256"],
        }
        expected_id = sha256_hex(canonical_json(base_dict))
        if data["receipt_id"] != expected_id:
            raise ValueError("receipt_id_mismatch")

        return cls(
            schema_version=data["schema_version"],
            root_kind=data["root_kind"],
            e_a_manifest_id=data["e_a_manifest_id"],
            e_a_manifest_sha256=data["e_a_manifest_sha256"],
            e_a_environment_attestation_sha256=data["e_a_environment_attestation_sha256"],
            e_b_execution_environment_attestation_sha256=data["e_b_execution_environment_attestation_sha256"],
            permissions=stage1_6e_b_permissions(),
            receipt_id=data["receipt_id"],
        )


# -----------------------------------------------------------------------------
# Source Consumer Checkpoint
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceConsumerCheckpoint:
    schema_version: str
    supervisor_run_id: str
    source_root_realpath: str
    source_checkpoint_id: str
    source_checkpoint_sha256: str
    source_stream_offsets: dict[str, int]
    source_stream_last_hashes: dict[str, str]
    detail_revisions_committed_offset: int
    detail_revisions_last_line_sha256: str | None
    last_consumed_detail_revision_record_seq: int | None
    active_notice_event_key: str | None
    active_event_id: str | None
    updated_at_ms: int
    permissions: dict[str, bool]
    source_consumer_checkpoint_id: str

    @classmethod
    def create(
        cls,
        *,
        supervisor_run_id: str,
        source_root_realpath: str,
        source_checkpoint_id: str,
        source_checkpoint_sha256: str,
        source_stream_offsets: dict[str, int],
        source_stream_last_hashes: dict[str, str],
        detail_revisions_committed_offset: int,
        detail_revisions_last_line_sha256: str | None,
        last_consumed_detail_revision_record_seq: int | None,
        active_notice_event_key: str | None,
        active_event_id: str | None,
        updated_at_ms: int,
    ) -> SourceConsumerCheckpoint:
        validate_sha256(source_checkpoint_id)
        validate_sha256(source_checkpoint_sha256)
        if detail_revisions_committed_offset == 0:
            if detail_revisions_last_line_sha256 is not None:
                raise ValueError("bootstrap_last_line_must_be_null")
            if last_consumed_detail_revision_record_seq is not None:
                raise ValueError("bootstrap_record_seq_must_be_null")
        else:
            if detail_revisions_last_line_sha256 is None:
                raise ValueError("nonzero_offset_requires_last_line_hash")
            validate_sha256(detail_revisions_last_line_sha256)
            if not isinstance(last_consumed_detail_revision_record_seq, int) or last_consumed_detail_revision_record_seq <= 0:
                raise ValueError("nonzero_offset_requires_positive_record_seq")

        if active_notice_event_key is not None:
            validate_sha256(active_notice_event_key)
        if active_event_id is not None:
            validate_sha256(active_event_id)

        base_dict = {
            "schema_version": "stage1_6e_b_source_consumer_checkpoint_v1",
            "supervisor_run_id": supervisor_run_id,
            "source_root_realpath": source_root_realpath,
            "source_checkpoint_id": source_checkpoint_id,
            "source_checkpoint_sha256": source_checkpoint_sha256,
            "source_stream_offsets": source_stream_offsets,
            "source_stream_last_hashes": source_stream_last_hashes,
            "detail_revisions_committed_offset": detail_revisions_committed_offset,
            "detail_revisions_last_line_sha256": detail_revisions_last_line_sha256,
            "last_consumed_detail_revision_record_seq": last_consumed_detail_revision_record_seq,
            "active_notice_event_key": active_notice_event_key,
            "active_event_id": active_event_id,
            "updated_at_ms": updated_at_ms,
        }
        chk_id = sha256_hex(canonical_json(base_dict))
        return cls(
            schema_version="stage1_6e_b_source_consumer_checkpoint_v1",
            supervisor_run_id=supervisor_run_id,
            source_root_realpath=source_root_realpath,
            source_checkpoint_id=source_checkpoint_id,
            source_checkpoint_sha256=source_checkpoint_sha256,
            source_stream_offsets=source_stream_offsets,
            source_stream_last_hashes=source_stream_last_hashes,
            detail_revisions_committed_offset=detail_revisions_committed_offset,
            detail_revisions_last_line_sha256=detail_revisions_last_line_sha256,
            last_consumed_detail_revision_record_seq=last_consumed_detail_revision_record_seq,
            active_notice_event_key=active_notice_event_key,
            active_event_id=active_event_id,
            updated_at_ms=updated_at_ms,
            permissions=stage1_6e_b_permissions(),
            source_consumer_checkpoint_id=chk_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "supervisor_run_id": self.supervisor_run_id,
            "source_root_realpath": self.source_root_realpath,
            "source_checkpoint_id": self.source_checkpoint_id,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "source_stream_offsets": self.source_stream_offsets,
            "source_stream_last_hashes": self.source_stream_last_hashes,
            "detail_revisions_committed_offset": self.detail_revisions_committed_offset,
            "detail_revisions_last_line_sha256": self.detail_revisions_last_line_sha256,
            "last_consumed_detail_revision_record_seq": self.last_consumed_detail_revision_record_seq,
            "active_notice_event_key": self.active_notice_event_key,
            "active_event_id": self.active_event_id,
            "updated_at_ms": self.updated_at_ms,
            "permissions": self.permissions,
            "source_consumer_checkpoint_id": self.source_consumer_checkpoint_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceConsumerCheckpoint:
        expected_keys = {
            "schema_version",
            "supervisor_run_id",
            "source_root_realpath",
            "source_checkpoint_id",
            "source_checkpoint_sha256",
            "source_stream_offsets",
            "source_stream_last_hashes",
            "detail_revisions_committed_offset",
            "detail_revisions_last_line_sha256",
            "last_consumed_detail_revision_record_seq",
            "active_notice_event_key",
            "active_event_id",
            "updated_at_ms",
            "permissions",
            "source_consumer_checkpoint_id",
        }
        if set(data.keys()) != expected_keys:
            raise ValueError("consumer_checkpoint_keys_mismatch")
        return cls.create(
            supervisor_run_id=data["supervisor_run_id"],
            source_root_realpath=data["source_root_realpath"],
            source_checkpoint_id=data["source_checkpoint_id"],
            source_checkpoint_sha256=data["source_checkpoint_sha256"],
            source_stream_offsets=data["source_stream_offsets"],
            source_stream_last_hashes=data["source_stream_last_hashes"],
            detail_revisions_committed_offset=data["detail_revisions_committed_offset"],
            detail_revisions_last_line_sha256=data["detail_revisions_last_line_sha256"],
            last_consumed_detail_revision_record_seq=data["last_consumed_detail_revision_record_seq"],
            active_notice_event_key=data["active_notice_event_key"],
            active_event_id=data["active_event_id"],
            updated_at_ms=data["updated_at_ms"],
        )


# -----------------------------------------------------------------------------
# Delisting Semantic Projection
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class DelistingSemanticProjection:
    schema_version: str
    semantic_projection_id: str
    supervisor_run_id: str
    source_root_realpath: str
    source_checkpoint_id: str
    source_checkpoint_sha256: str
    source_article_id: str
    source_request_observation_id: str
    source_detail_revision_id: str
    source_detail_raw_sha256: str
    source_detail_raw_relative_path: str
    copied_source_raw_relative_path: str
    g2_body_normalization_version: str
    g2_semantic_extractor_version: str
    normalized_body_sha256: str | None
    semantic_projected_at_ms: int
    source_first_detected_at_ms: int
    source_detail_trusted_at_ms: int
    eligible_symbols_ordered: list[str]
    eligible_symbols_normalized: list[str]
    eligible_symbol_set_sha256: str | None
    effective_delist_time_ms: int | None
    eligibility_status: str
    blocker: str | None
    permissions: dict[str, bool]

    @classmethod
    def create(
        cls,
        *,
        supervisor_run_id: str,
        source_root_realpath: str,
        source_checkpoint_id: str,
        source_checkpoint_sha256: str,
        source_article_id: str,
        source_request_observation_id: str,
        source_detail_revision_id: str,
        source_detail_raw_sha256: str,
        source_detail_raw_relative_path: str,
        copied_source_raw_relative_path: str,
        g2_body_normalization_version: str,
        g2_semantic_extractor_version: str,
        normalized_body_sha256: str | None,
        source_first_detected_at_ms: int,
        source_detail_trusted_at_ms: int,
        eligible_symbols_ordered: list[str],
        effective_delist_time_ms: int | None,
        eligibility_status: str,
        blocker: str | None,
        semantic_projected_at_ms: int,
    ) -> DelistingSemanticProjection:
        validate_sha256(source_checkpoint_id)
        validate_sha256(source_checkpoint_sha256)
        validate_sha256(source_detail_raw_sha256)
        if normalized_body_sha256 is not None:
            validate_sha256(normalized_body_sha256)

        if eligibility_status not in ("eligible", "not_eligible"):
            raise ValueError(f"invalid_eligibility_status: {eligibility_status}")

        symbols_norm = sorted(list(set(eligible_symbols_ordered)))
        symbol_set_sha = sha256_hex(canonical_json(symbols_norm)) if symbols_norm else None

        if eligibility_status == "eligible":
            if blocker is not None:
                raise ValueError("eligible_blocker_must_be_null")
            if not (1 <= len(eligible_symbols_ordered) <= 3):
                raise ValueError("eligible_symbol_count_must_be_1_to_3")
            if effective_delist_time_ms is None or effective_delist_time_ms <= semantic_projected_at_ms:
                raise ValueError("eligible_requires_future_effective_delist_time")
        else:
            if blocker is None:
                raise ValueError("not_eligible_requires_blocker")
            effective_delist_time_ms = None

        # Stable projection ID excludes volatile semantic_projected_at_ms and permissions (Design follow-up P0-2)
        id_dict = {
            "schema_version": "stage1_6e_b_delisting_semantic_projection_v1",
            "supervisor_run_id": supervisor_run_id,
            "source_root_realpath": source_root_realpath,
            "source_checkpoint_id": source_checkpoint_id,
            "source_checkpoint_sha256": source_checkpoint_sha256,
            "source_article_id": source_article_id,
            "source_request_observation_id": source_request_observation_id,
            "source_detail_revision_id": source_detail_revision_id,
            "source_detail_raw_sha256": source_detail_raw_sha256,
            "source_detail_raw_relative_path": source_detail_raw_relative_path,
            "copied_source_raw_relative_path": copied_source_raw_relative_path,
            "g2_body_normalization_version": g2_body_normalization_version,
            "g2_semantic_extractor_version": g2_semantic_extractor_version,
            "normalized_body_sha256": normalized_body_sha256,
            "source_first_detected_at_ms": source_first_detected_at_ms,
            "source_detail_trusted_at_ms": source_detail_trusted_at_ms,
            "eligible_symbols_ordered": eligible_symbols_ordered,
            "eligible_symbols_normalized": symbols_norm,
            "eligible_symbol_set_sha256": symbol_set_sha,
            "effective_delist_time_ms": effective_delist_time_ms,
            "eligibility_status": eligibility_status,
            "blocker": blocker,
        }
        proj_id = sha256_hex(canonical_json(id_dict))

        return cls(
            schema_version="stage1_6e_b_delisting_semantic_projection_v1",
            semantic_projection_id=proj_id,
            supervisor_run_id=supervisor_run_id,
            source_root_realpath=source_root_realpath,
            source_checkpoint_id=source_checkpoint_id,
            source_checkpoint_sha256=source_checkpoint_sha256,
            source_article_id=source_article_id,
            source_request_observation_id=source_request_observation_id,
            source_detail_revision_id=source_detail_revision_id,
            source_detail_raw_sha256=source_detail_raw_sha256,
            source_detail_raw_relative_path=source_detail_raw_relative_path,
            copied_source_raw_relative_path=copied_source_raw_relative_path,
            g2_body_normalization_version=g2_body_normalization_version,
            g2_semantic_extractor_version=g2_semantic_extractor_version,
            normalized_body_sha256=normalized_body_sha256,
            semantic_projected_at_ms=semantic_projected_at_ms,
            source_first_detected_at_ms=source_first_detected_at_ms,
            source_detail_trusted_at_ms=source_detail_trusted_at_ms,
            eligible_symbols_ordered=eligible_symbols_ordered,
            eligible_symbols_normalized=symbols_norm,
            eligible_symbol_set_sha256=symbol_set_sha,
            effective_delist_time_ms=effective_delist_time_ms,
            eligibility_status=eligibility_status,
            blocker=blocker,
            permissions=stage1_6e_b_permissions(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "semantic_projection_id": self.semantic_projection_id,
            "supervisor_run_id": self.supervisor_run_id,
            "source_root_realpath": self.source_root_realpath,
            "source_checkpoint_id": self.source_checkpoint_id,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "source_article_id": self.source_article_id,
            "source_request_observation_id": self.source_request_observation_id,
            "source_detail_revision_id": self.source_detail_revision_id,
            "source_detail_raw_sha256": self.source_detail_raw_sha256,
            "source_detail_raw_relative_path": self.source_detail_raw_relative_path,
            "copied_source_raw_relative_path": self.copied_source_raw_relative_path,
            "g2_body_normalization_version": self.g2_body_normalization_version,
            "g2_semantic_extractor_version": self.g2_semantic_extractor_version,
            "normalized_body_sha256": self.normalized_body_sha256,
            "semantic_projected_at_ms": self.semantic_projected_at_ms,
            "source_first_detected_at_ms": self.source_first_detected_at_ms,
            "source_detail_trusted_at_ms": self.source_detail_trusted_at_ms,
            "eligible_symbols_ordered": self.eligible_symbols_ordered,
            "eligible_symbols_normalized": self.eligible_symbols_normalized,
            "eligible_symbol_set_sha256": self.eligible_symbol_set_sha256,
            "effective_delist_time_ms": self.effective_delist_time_ms,
            "eligibility_status": self.eligibility_status,
            "blocker": self.blocker,
            "permissions": self.permissions,
        }


def compute_notice_event_key(source_article_id: str) -> str:
    return sha256_hex(canonical_json({"source_article_id": str(source_article_id)}))


def compute_event_id(semantic_projection_id: str) -> str:
    validate_sha256(semantic_projection_id)
    return sha256_hex(
        canonical_json({
            "semantic_projection_id": semantic_projection_id,
            "schema_version": "stage1_6e_b_event_contract_v1",
        })
    )


# -----------------------------------------------------------------------------
# Event Admission
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class EventAdmission:
    schema_version: str
    admission_id: str
    semantic_projection_id: str
    notice_event_key: str
    event_id: str
    decision: str
    blocker: str | None
    active_event_id_at_decision: str | None
    decided_at_ms: int
    permissions: dict[str, bool]

    @classmethod
    def create(
        cls,
        *,
        semantic_projection_id: str,
        notice_event_key: str,
        event_id: str,
        decision: str,
        blocker: str | None,
        active_event_id_at_decision: str | None,
        decided_at_ms: int,
    ) -> EventAdmission:
        validate_sha256(semantic_projection_id)
        validate_sha256(notice_event_key)
        validate_sha256(event_id)
        if active_event_id_at_decision is not None:
            validate_sha256(active_event_id_at_decision)

        if decision not in ("admitted", "event_observation_capacity_blocked", "notice_already_observed"):
            raise ValueError(f"invalid_admission_decision: {decision}")

        base_dict = {
            "schema_version": "stage1_6e_b_event_admission_v1",
            "semantic_projection_id": semantic_projection_id,
            "notice_event_key": notice_event_key,
            "event_id": event_id,
            "decision": decision,
            "blocker": blocker,
            "active_event_id_at_decision": active_event_id_at_decision,
        }
        adm_id = sha256_hex(canonical_json(base_dict))
        return cls(
            schema_version="stage1_6e_b_event_admission_v1",
            admission_id=adm_id,
            semantic_projection_id=semantic_projection_id,
            notice_event_key=notice_event_key,
            event_id=event_id,
            decision=decision,
            blocker=blocker,
            active_event_id_at_decision=active_event_id_at_decision,
            decided_at_ms=decided_at_ms,
            permissions=stage1_6e_b_permissions(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "admission_id": self.admission_id,
            "semantic_projection_id": self.semantic_projection_id,
            "notice_event_key": self.notice_event_key,
            "event_id": self.event_id,
            "decision": self.decision,
            "blocker": self.blocker,
            "active_event_id_at_decision": self.active_event_id_at_decision,
            "decided_at_ms": self.decided_at_ms,
            "permissions": self.permissions,
        }


# -----------------------------------------------------------------------------
# Event Contract
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class EventContract:
    schema_version: str
    event_id: str
    supervisor_run_id: str
    semantic_projection_id: str
    semantic_projection_row_sha256: str
    admission_id: str
    admission_row_sha256: str
    source_article_id: str
    source_detail_revision_id: str
    source_detail_raw_sha256: str
    source_checkpoint_id: str
    source_checkpoint_sha256: str
    effective_delist_time_ms: int
    event_window_started_at_ms: int
    event_window_ends_at_ms: int
    window_duration_ms: int
    canonical_symbols_ordered: list[str]
    canonical_symbols_normalized: list[str]
    symbol_set_sha256: str
    expected_slot_count: int
    e_a_manifest_id: str
    e_a_manifest_sha256: str
    e_a_profile_attestation_sha256_by_id: dict[str, str]
    execution_environment_attestation_sha256: str
    storage_contract: dict[str, Any]
    permissions: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "supervisor_run_id": self.supervisor_run_id,
            "semantic_projection_id": self.semantic_projection_id,
            "semantic_projection_row_sha256": self.semantic_projection_row_sha256,
            "admission_id": self.admission_id,
            "admission_row_sha256": self.admission_row_sha256,
            "source_article_id": self.source_article_id,
            "source_detail_revision_id": self.source_detail_revision_id,
            "source_detail_raw_sha256": self.source_detail_raw_sha256,
            "source_checkpoint_id": self.source_checkpoint_id,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "effective_delist_time_ms": self.effective_delist_time_ms,
            "event_window_started_at_ms": self.event_window_started_at_ms,
            "event_window_ends_at_ms": self.event_window_ends_at_ms,
            "window_duration_ms": self.window_duration_ms,
            "canonical_symbols_ordered": self.canonical_symbols_ordered,
            "canonical_symbols_normalized": self.canonical_symbols_normalized,
            "symbol_set_sha256": self.symbol_set_sha256,
            "expected_slot_count": self.expected_slot_count,
            "e_a_manifest_id": self.e_a_manifest_id,
            "e_a_manifest_sha256": self.e_a_manifest_sha256,
            "e_a_profile_attestation_sha256_by_id": self.e_a_profile_attestation_sha256_by_id,
            "execution_environment_attestation_sha256": self.execution_environment_attestation_sha256,
            "storage_contract": self.storage_contract,
            "permissions": self.permissions,
        }


# -----------------------------------------------------------------------------
# Derived Event Profile Core
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class EventProfileCore:
    schema_version: str
    event_id: str
    source_article_id: str
    source_detail_revision_id: str
    canonical_symbol: str
    base_e_a_manifest_id: str
    base_e_a_profile_id: str
    base_e_a_profile_attestation_sha256: str
    base_e_a_profile_core_sha256: str
    event_max_raw_response_bytes: int
    http_profile_core: dict[str, Any]
    profile_attestation_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "source_article_id": self.source_article_id,
            "source_detail_revision_id": self.source_detail_revision_id,
            "canonical_symbol": self.canonical_symbol,
            "base_e_a_manifest_id": self.base_e_a_manifest_id,
            "base_e_a_profile_id": self.base_e_a_profile_id,
            "base_e_a_profile_attestation_sha256": self.base_e_a_profile_attestation_sha256,
            "base_e_a_profile_core_sha256": self.base_e_a_profile_core_sha256,
            "event_max_raw_response_bytes": self.event_max_raw_response_bytes,
            "http_profile_core": self.http_profile_core,
            "profile_attestation_sha256": self.profile_attestation_sha256,
        }


def derive_event_profile_core(
    *,
    event_id: str,
    source_article_id: str,
    source_detail_revision_id: str,
    canonical_symbol: str,
    base_e_a_manifest_id: str,
    base_e_a_profile_id: str,
    base_e_a_profile_attestation_sha256: str,
    base_e_a_profile_core: dict[str, Any],
) -> EventProfileCore:
    validate_sha256(event_id)
    validate_sha256(base_e_a_manifest_id)
    validate_sha256(base_e_a_profile_attestation_sha256)

    http_core = copy.deepcopy(base_e_a_profile_core)
    base_core_sha = sha256_hex(canonical_json(base_e_a_profile_core))
    base_attest_sha = base_e_a_profile_attestation_sha256

    if base_e_a_profile_id == "binance_usdm_rest_depth_v1":
        http_core["canonical_query"] = f"limit=100&symbol={canonical_symbol}"
        event_max_bytes = 262144
    elif base_e_a_profile_id == "binance_usdm_rest_premium_index_v1":
        http_core["canonical_query"] = f"symbol={canonical_symbol}"
        http_core["expected_response_schema"]["required_fields"]["symbol"] = f"literal_{canonical_symbol}"
        event_max_bytes = 32768
    elif base_e_a_profile_id == "binance_usdm_rest_funding_rate_v1":
        http_core["canonical_query"] = f"limit=1&symbol={canonical_symbol}"
        http_core["expected_response_schema"]["required_fields"]["symbol"] = f"literal_{canonical_symbol}"
        event_max_bytes = 32768
    elif base_e_a_profile_id == "binance_usdm_rest_open_interest_hist_5m_v1":
        http_core["canonical_query"] = f"limit=1&period=5m&symbol={canonical_symbol}"
        http_core["expected_response_schema"]["required_fields"]["symbol"] = f"literal_{canonical_symbol}"
        event_max_bytes = 32768
    else:
        raise ValueError(f"unsupported_base_profile_id: {base_e_a_profile_id}")

    http_core["max_raw_response_bytes"] = event_max_bytes

    base_dict = {
        "schema_version": "stage1_6e_b_event_profile_core_v1",
        "event_id": event_id,
        "source_article_id": source_article_id,
        "source_detail_revision_id": source_detail_revision_id,
        "canonical_symbol": canonical_symbol,
        "base_e_a_manifest_id": base_e_a_manifest_id,
        "base_e_a_profile_id": base_e_a_profile_id,
        "base_e_a_profile_attestation_sha256": base_attest_sha,
        "base_e_a_profile_core_sha256": base_core_sha,
        "event_max_raw_response_bytes": event_max_bytes,
        "http_profile_core": http_core,
    }
    attest_sha = sha256_hex(canonical_json(base_dict))
    return EventProfileCore(
        schema_version="stage1_6e_b_event_profile_core_v1",
        event_id=event_id,
        source_article_id=source_article_id,
        source_detail_revision_id=source_detail_revision_id,
        canonical_symbol=canonical_symbol,
        base_e_a_manifest_id=base_e_a_manifest_id,
        base_e_a_profile_id=base_e_a_profile_id,
        base_e_a_profile_attestation_sha256=base_attest_sha,
        base_e_a_profile_core_sha256=base_core_sha,
        event_max_raw_response_bytes=event_max_bytes,
        http_profile_core=http_core,
        profile_attestation_sha256=attest_sha,
    )


# -----------------------------------------------------------------------------
# Slot ID & Slot Intent
# -----------------------------------------------------------------------------


def compute_slot_id(
    *,
    event_id: str,
    base_e_a_profile_id: str,
    canonical_symbol: str,
    slot_family: str,
    slot_index: int,
    due_at_ms: int,
) -> str:
    validate_sha256(event_id)
    return sha256_hex(
        canonical_json({
            "event_id": event_id,
            "base_e_a_profile_id": base_e_a_profile_id,
            "canonical_symbol": canonical_symbol,
            "slot_family": slot_family,
            "slot_index": slot_index,
            "due_at_ms": due_at_ms,
        })
    )


@dataclass(frozen=True)
class SlotIntent:
    slot_id: str
    request_identity: str
    request_sequence: int
    base_e_a_profile_id: str
    canonical_symbol: str
    due_at_ms: int
    reserved_at_ms: int
    stage: str
    raw_sha256: str | None = None
    raw_relative_path: str | None = None
    raw_byte_count: int | None = None

    @classmethod
    def create(
        cls,
        *,
        slot_id: str,
        request_identity: str,
        request_sequence: int,
        base_e_a_profile_id: str,
        canonical_symbol: str,
        due_at_ms: int,
        reserved_at_ms: int,
        stage: str,
        raw_sha256: str | None = None,
        raw_relative_path: str | None = None,
        raw_byte_count: int | None = None,
    ) -> SlotIntent:
        validate_sha256(slot_id)
        validate_sha256(request_identity)
        if not isinstance(request_sequence, int) or request_sequence <= 0:
            raise ValueError(f"invalid_request_sequence: {request_sequence}")
        if stage not in ("prepared", "raw_persisted"):
            raise ValueError(f"invalid_slot_intent_stage: {stage}")
        if stage == "prepared":
            if raw_sha256 is not None or raw_relative_path is not None or raw_byte_count is not None:
                raise ValueError("prepared_intent_must_have_null_raw_fields")
        elif stage == "raw_persisted":
            if raw_sha256 is None or raw_relative_path is None or raw_byte_count is None:
                raise ValueError("raw_persisted_intent_must_have_raw_fields")
            validate_sha256(raw_sha256)
            if not isinstance(raw_byte_count, int) or raw_byte_count < 0:
                raise ValueError("invalid_raw_byte_count")
        return cls(
            slot_id=slot_id,
            request_identity=request_identity,
            request_sequence=request_sequence,
            base_e_a_profile_id=base_e_a_profile_id,
            canonical_symbol=canonical_symbol,
            due_at_ms=due_at_ms,
            reserved_at_ms=reserved_at_ms,
            stage=stage,
            raw_sha256=raw_sha256,
            raw_relative_path=raw_relative_path,
            raw_byte_count=raw_byte_count,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "request_identity": self.request_identity,
            "request_sequence": self.request_sequence,
            "base_e_a_profile_id": self.base_e_a_profile_id,
            "canonical_symbol": self.canonical_symbol,
            "due_at_ms": self.due_at_ms,
            "reserved_at_ms": self.reserved_at_ms,
            "stage": self.stage,
            "raw_sha256": self.raw_sha256,
            "raw_relative_path": self.raw_relative_path,
            "raw_byte_count": self.raw_byte_count,
        }


# -----------------------------------------------------------------------------
# Market Observation
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class MarketObservation:
    schema_version: str
    event_id: str
    slot_id: str
    slot_family: str
    slot_index: int
    due_at_ms: int
    dispatch_started_at_ms: int | None
    completed_at_ms: int
    canonical_symbol: str
    base_e_a_profile_id: str
    profile_attestation_sha256: str
    request_identity: str
    request_sequence: int | None
    outcome_kind: str
    http_status: int | None
    response_headers_subset: dict[str, str] | None
    raw_payload_persisted: bool
    raw_sha256: str | None
    raw_relative_path: str | None
    raw_byte_count: int | None
    schema_validation_status: str
    time_validation_status: str
    failure_reason: str | None
    permissions: dict[str, bool]

    @classmethod
    def create_verified(
        cls,
        *,
        event_id: str,
        slot_id: str,
        slot_family: str,
        slot_index: int,
        due_at_ms: int,
        dispatch_started_at_ms: int,
        completed_at_ms: int,
        canonical_symbol: str,
        base_e_a_profile_id: str,
        profile_attestation_sha256: str,
        request_identity: str,
        request_sequence: int,
        http_status: int,
        response_headers_subset: dict[str, str],
        raw_sha256: str,
        raw_relative_path: str,
        raw_byte_count: int,
    ) -> MarketObservation:
        validate_sha256(event_id)
        validate_sha256(slot_id)
        validate_sha256(profile_attestation_sha256)
        validate_sha256(raw_sha256)
        return cls(
            schema_version="stage1_6e_b_market_observation_v1",
            event_id=event_id,
            slot_id=slot_id,
            slot_family=slot_family,
            slot_index=slot_index,
            due_at_ms=due_at_ms,
            dispatch_started_at_ms=dispatch_started_at_ms,
            completed_at_ms=completed_at_ms,
            canonical_symbol=canonical_symbol,
            base_e_a_profile_id=base_e_a_profile_id,
            profile_attestation_sha256=profile_attestation_sha256,
            request_identity=request_identity,
            request_sequence=request_sequence,
            outcome_kind="response_verified",
            http_status=http_status,
            response_headers_subset=response_headers_subset,
            raw_payload_persisted=True,
            raw_sha256=raw_sha256,
            raw_relative_path=raw_relative_path,
            raw_byte_count=raw_byte_count,
            schema_validation_status="verified",
            time_validation_status="verified",
            failure_reason=None,
            permissions=stage1_6e_b_permissions(),
        )

    @classmethod
    def create_missed_deadline(
        cls,
        *,
        event_id: str,
        slot_id: str,
        slot_family: str,
        slot_index: int,
        due_at_ms: int,
        completed_at_ms: int,
        canonical_symbol: str,
        base_e_a_profile_id: str,
        profile_attestation_sha256: str,
        request_identity: str,
    ) -> MarketObservation:
        validate_sha256(event_id)
        validate_sha256(slot_id)
        validate_sha256(profile_attestation_sha256)
        return cls(
            schema_version="stage1_6e_b_market_observation_v1",
            event_id=event_id,
            slot_id=slot_id,
            slot_family=slot_family,
            slot_index=slot_index,
            due_at_ms=due_at_ms,
            dispatch_started_at_ms=None,
            completed_at_ms=completed_at_ms,
            canonical_symbol=canonical_symbol,
            base_e_a_profile_id=base_e_a_profile_id,
            profile_attestation_sha256=profile_attestation_sha256,
            request_identity=request_identity,
            request_sequence=None,
            outcome_kind="slot_missed_deadline",
            http_status=None,
            response_headers_subset=None,
            raw_payload_persisted=False,
            raw_sha256=None,
            raw_relative_path=None,
            raw_byte_count=None,
            schema_validation_status="not_applicable",
            time_validation_status="not_applicable",
            failure_reason="slot_missed_deadline",
            permissions=stage1_6e_b_permissions(),
        )

    @classmethod
    def create_unknown_after_restart(
        cls,
        *,
        event_id: str,
        slot_id: str,
        slot_family: str,
        slot_index: int,
        due_at_ms: int,
        completed_at_ms: int,
        canonical_symbol: str,
        base_e_a_profile_id: str,
        profile_attestation_sha256: str,
        request_identity: str,
        request_sequence: int,
        raw_payload_persisted: bool = False,
        raw_sha256: str | None = None,
        raw_relative_path: str | None = None,
        raw_byte_count: int | None = None,
    ) -> MarketObservation:
        validate_sha256(event_id)
        validate_sha256(slot_id)
        validate_sha256(profile_attestation_sha256)
        if not isinstance(request_sequence, int) or request_sequence <= 0:
            raise ValueError(f"invalid_request_sequence: {request_sequence}")
        if raw_payload_persisted:
            if raw_sha256 is None or raw_relative_path is None or raw_byte_count is None:
                raise ValueError("persisted_raw_requires_raw_fields")
            validate_sha256(raw_sha256)
        else:
            if raw_sha256 is not None or raw_relative_path is not None or raw_byte_count is not None:
                raise ValueError("non_persisted_raw_requires_null_raw_fields")

        return cls(
            schema_version="stage1_6e_b_market_observation_v1",
            event_id=event_id,
            slot_id=slot_id,
            slot_family=slot_family,
            slot_index=slot_index,
            due_at_ms=due_at_ms,
            dispatch_started_at_ms=None,
            completed_at_ms=completed_at_ms,
            canonical_symbol=canonical_symbol,
            base_e_a_profile_id=base_e_a_profile_id,
            profile_attestation_sha256=profile_attestation_sha256,
            request_identity=request_identity,
            request_sequence=request_sequence,
            outcome_kind="request_outcome_unknown_after_restart",
            http_status=None,
            response_headers_subset={},
            raw_payload_persisted=raw_payload_persisted,
            raw_sha256=raw_sha256,
            raw_relative_path=raw_relative_path,
            raw_byte_count=raw_byte_count,
            schema_validation_status="not_applicable",
            time_validation_status="not_applicable",
            failure_reason="request_outcome_unknown_after_restart",
            permissions=stage1_6e_b_permissions(),
        )

    @classmethod
    def create_failed_request(
        cls,
        *,
        event_id: str,
        slot_id: str,
        slot_family: str,
        slot_index: int,
        due_at_ms: int,
        dispatch_started_at_ms: int,
        completed_at_ms: int,
        canonical_symbol: str,
        base_e_a_profile_id: str,
        profile_attestation_sha256: str,
        request_identity: str,
        request_sequence: int,
        outcome_kind: str,
        http_status: int | None,
        failure_reason: str,
        raw_payload_persisted: bool = False,
        raw_sha256: str | None = None,
        raw_relative_path: str | None = None,
        raw_byte_count: int | None = None,
        schema_validation_status: str = "failed",
        time_validation_status: str = "failed",
    ) -> MarketObservation:
        validate_sha256(event_id)
        validate_sha256(slot_id)
        validate_sha256(profile_attestation_sha256)
        return cls(
            schema_version="stage1_6e_b_market_observation_v1",
            event_id=event_id,
            slot_id=slot_id,
            slot_family=slot_family,
            slot_index=slot_index,
            due_at_ms=due_at_ms,
            dispatch_started_at_ms=dispatch_started_at_ms,
            completed_at_ms=completed_at_ms,
            canonical_symbol=canonical_symbol,
            base_e_a_profile_id=base_e_a_profile_id,
            profile_attestation_sha256=profile_attestation_sha256,
            request_identity=request_identity,
            request_sequence=request_sequence,
            outcome_kind=outcome_kind,
            http_status=http_status,
            response_headers_subset=None,
            raw_payload_persisted=raw_payload_persisted,
            raw_sha256=raw_sha256,
            raw_relative_path=raw_relative_path,
            raw_byte_count=raw_byte_count,
            schema_validation_status=schema_validation_status,
            time_validation_status=time_validation_status,
            failure_reason=failure_reason,
            permissions=stage1_6e_b_permissions(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "slot_id": self.slot_id,
            "slot_family": self.slot_family,
            "slot_index": self.slot_index,
            "due_at_ms": self.due_at_ms,
            "dispatch_started_at_ms": self.dispatch_started_at_ms,
            "completed_at_ms": self.completed_at_ms,
            "canonical_symbol": self.canonical_symbol,
            "base_e_a_profile_id": self.base_e_a_profile_id,
            "profile_attestation_sha256": self.profile_attestation_sha256,
            "request_identity": self.request_identity,
            "request_sequence": self.request_sequence,
            "outcome_kind": self.outcome_kind,
            "http_status": self.http_status,
            "response_headers_subset": self.response_headers_subset,
            "raw_payload_persisted": self.raw_payload_persisted,
            "raw_sha256": self.raw_sha256,
            "raw_relative_path": self.raw_relative_path,
            "raw_byte_count": self.raw_byte_count,
            "schema_validation_status": self.schema_validation_status,
            "time_validation_status": self.time_validation_status,
            "failure_reason": self.failure_reason,
            "permissions": self.permissions,
        }


def validate_market_observation_dict(data: dict[str, Any]) -> bool:
    expected_keys = {
        "schema_version",
        "event_id",
        "slot_id",
        "slot_family",
        "slot_index",
        "due_at_ms",
        "dispatch_started_at_ms",
        "completed_at_ms",
        "canonical_symbol",
        "base_e_a_profile_id",
        "profile_attestation_sha256",
        "request_identity",
        "request_sequence",
        "outcome_kind",
        "http_status",
        "response_headers_subset",
        "raw_payload_persisted",
        "raw_sha256",
        "raw_relative_path",
        "raw_byte_count",
        "schema_validation_status",
        "time_validation_status",
        "failure_reason",
        "permissions",
    }
    if set(data.keys()) != expected_keys:
        raise ValueError("observation_keys_mismatch")
    validate_permissions(data["permissions"])
    validate_sha256(data["event_id"])
    validate_sha256(data["slot_id"])
    validate_sha256(data["profile_attestation_sha256"])

    outcome = data["outcome_kind"]
    allowed_outcomes = {
        "slot_missed_deadline",
        "response_verified",
        "request_timeout",
        "transport_error",
        "redirect_rejected",
        "http_response_invalid",
        "content_encoding_invalid",
        "raw_size_exceeded",
        "schema_validation_failed",
        "time_validation_failed",
        "request_outcome_unknown_after_restart",
    }
    if outcome not in allowed_outcomes:
        raise ValueError(f"unknown_outcome_kind: {outcome}")

    if outcome == "slot_missed_deadline":
        if data["dispatch_started_at_ms"] is not None:
            raise ValueError("missed_deadline_dispatch_must_be_null")
        if data["request_sequence"] is not None:
            raise ValueError("missed_deadline_sequence_must_be_null")
        if data["http_status"] is not None:
            raise ValueError("missed_deadline_http_status_must_be_null")
        if data["raw_payload_persisted"] is not False:
            raise ValueError("missed_deadline_raw_must_be_false")
        if data["schema_validation_status"] != "not_applicable":
            raise ValueError("missed_deadline_schema_must_be_not_applicable")
        if data["time_validation_status"] != "not_applicable":
            raise ValueError("missed_deadline_time_must_be_not_applicable")
    elif outcome == "request_outcome_unknown_after_restart":
        if data["dispatch_started_at_ms"] is not None:
            raise ValueError("unknown_after_restart_dispatch_must_be_null")
        if not isinstance(data["request_sequence"], int) or data["request_sequence"] <= 0:
            raise ValueError("unknown_after_restart_sequence_must_be_positive_int")
        if data["http_status"] is not None:
            raise ValueError("unknown_after_restart_http_must_be_null")
    elif outcome == "response_verified":
        if data["dispatch_started_at_ms"] is None:
            raise ValueError("verified_dispatch_required")
        if not isinstance(data["request_sequence"], int) or data["request_sequence"] <= 0:
            raise ValueError("verified_sequence_must_be_positive_int")
        if data["raw_payload_persisted"] is not True:
            raise ValueError("verified_raw_required")
        validate_sha256(data["raw_sha256"])
        if data["schema_validation_status"] != "verified":
            raise ValueError("verified_schema_must_be_verified")
        if data["time_validation_status"] != "verified":
            raise ValueError("verified_time_must_be_verified")
    else:
        # Other error outcomes
        if data["dispatch_started_at_ms"] is None:
            raise ValueError("error_dispatch_required")
        if not isinstance(data["request_sequence"], int) or data["request_sequence"] <= 0:
            raise ValueError("error_sequence_must_be_positive_int")

    if data["raw_payload_persisted"]:
        if data["raw_sha256"] is None or data["raw_relative_path"] is None or data["raw_byte_count"] is None:
            raise ValueError("persisted_raw_requires_raw_fields")
        validate_sha256(data["raw_sha256"])
    else:
        if data["raw_sha256"] is not None or data["raw_relative_path"] is not None or data["raw_byte_count"] is not None:
            raise ValueError("non_persisted_raw_requires_null_raw_fields")

    return True


# -----------------------------------------------------------------------------
# Event Checkpoint
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class EventCheckpoint:
    schema_version: str
    event_id: str
    event_contract_sha256: str
    profile_attestation_sha256_by_symbol_and_profile: dict[str, str]
    completed_slot_ids_ordered: list[str]
    last_observation_sha256: str | None
    accounted_root_bytes: int
    inflight_slot_intent: dict[str, Any] | None
    updated_at_ms: int
    permissions: dict[str, bool]

    @classmethod
    def create(
        cls,
        *,
        event_id: str,
        event_contract_sha256: str,
        profile_attestation_sha256_by_symbol_and_profile: dict[str, Any],
        completed_slot_ids_ordered: list[str],
        last_observation_sha256: str | None,
        accounted_root_bytes: int,
        inflight_slot_intent: dict[str, Any] | None,
        updated_at_ms: int,
    ) -> EventCheckpoint:
        validate_sha256(event_id)
        validate_sha256(event_contract_sha256)
        if last_observation_sha256 is not None:
            validate_sha256(last_observation_sha256)
        elif len(completed_slot_ids_ordered) > 0:
            raise ValueError("last_observation_sha256_required_when_completed_slots_non_empty")
        if completed_slot_ids_ordered != sorted(completed_slot_ids_ordered):
            raise ValueError("completed_slot_ids_not_lexicographic")

        return cls(
            schema_version="stage1_6e_b_event_checkpoint_v1",
            event_id=event_id,
            event_contract_sha256=event_contract_sha256,
            profile_attestation_sha256_by_symbol_and_profile=profile_attestation_sha256_by_symbol_and_profile,
            completed_slot_ids_ordered=completed_slot_ids_ordered,
            last_observation_sha256=last_observation_sha256,
            accounted_root_bytes=accounted_root_bytes,
            inflight_slot_intent=inflight_slot_intent,
            updated_at_ms=updated_at_ms,
            permissions=stage1_6e_b_permissions(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "event_contract_sha256": self.event_contract_sha256,
            "profile_attestation_sha256_by_symbol_and_profile": self.profile_attestation_sha256_by_symbol_and_profile,
            "completed_slot_ids_ordered": self.completed_slot_ids_ordered,
            "last_observation_sha256": self.last_observation_sha256,
            "accounted_root_bytes": self.accounted_root_bytes,
            "inflight_slot_intent": self.inflight_slot_intent,
            "updated_at_ms": self.updated_at_ms,
            "permissions": self.permissions,
        }


def validate_event_checkpoint_dict(data: dict[str, Any]) -> bool:
    expected_keys = {
        "schema_version",
        "event_id",
        "event_contract_sha256",
        "profile_attestation_sha256_by_symbol_and_profile",
        "completed_slot_ids_ordered",
        "last_observation_sha256",
        "accounted_root_bytes",
        "inflight_slot_intent",
        "updated_at_ms",
        "permissions",
    }
    if set(data.keys()) != expected_keys:
        raise ValueError("event_checkpoint_keys_mismatch")
    validate_permissions(data["permissions"])
    validate_sha256(data["event_id"])
    validate_sha256(data["event_contract_sha256"])
    slots = data["completed_slot_ids_ordered"]
    if not isinstance(slots, list):
        raise ValueError("completed_slot_ids_not_list")
    if slots != sorted(slots):
        raise ValueError("completed_slot_ids_not_lexicographic")
    if data["last_observation_sha256"] is not None:
        validate_sha256(data["last_observation_sha256"])
    elif len(slots) > 0:
        raise ValueError("last_observation_sha256_required_when_slots_non_empty")
    intent = data.get("inflight_slot_intent")
    if intent is not None:
        expected_intent_keys = {
            "slot_id",
            "request_identity",
            "request_sequence",
            "base_e_a_profile_id",
            "canonical_symbol",
            "due_at_ms",
            "reserved_at_ms",
            "stage",
            "raw_sha256",
            "raw_relative_path",
            "raw_byte_count",
        }
        if set(intent.keys()) != expected_intent_keys:
            raise ValueError("inflight_slot_intent_keys_mismatch")
        validate_sha256(intent["slot_id"])
        validate_sha256(intent["request_identity"])
        if not isinstance(intent["request_sequence"], int) or intent["request_sequence"] <= 0:
            raise ValueError("invalid_intent_request_sequence")
        if intent["stage"] not in ("prepared", "raw_persisted"):
            raise ValueError("invalid_intent_stage")
        if intent["stage"] == "prepared":
            if (
                intent["raw_sha256"] is not None
                or intent["raw_relative_path"] is not None
                or intent["raw_byte_count"] is not None
            ):
                raise ValueError("prepared_intent_raw_not_null")
        elif intent["stage"] == "raw_persisted":
            if (
                intent["raw_sha256"] is None
                or intent["raw_relative_path"] is None
                or intent["raw_byte_count"] is None
            ):
                raise ValueError("raw_persisted_intent_raw_missing")
            validate_sha256(intent["raw_sha256"])
            if not isinstance(intent["raw_byte_count"], int) or intent["raw_byte_count"] < 0:
                raise ValueError("invalid_intent_raw_byte_count")
    return True


# -----------------------------------------------------------------------------
# Terminal Status
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class EventTerminalStatus:
    schema_version: str
    event_id: str
    status: str
    coverage_status: str | None
    terminal_reason: str | None
    event_window_started_at_ms: int
    event_window_ends_at_ms: int
    terminal_at_ms: int
    expected_slot_count: int
    durable_slot_count: int
    successful_slot_count: int
    failed_slot_count: int
    missed_slot_count: int
    per_symbol_slot_counts: list[dict[str, Any]]
    accounted_root_bytes: int
    permissions: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "status": self.status,
            "coverage_status": self.coverage_status,
            "terminal_reason": self.terminal_reason,
            "event_window_started_at_ms": self.event_window_started_at_ms,
            "event_window_ends_at_ms": self.event_window_ends_at_ms,
            "terminal_at_ms": self.terminal_at_ms,
            "expected_slot_count": self.expected_slot_count,
            "durable_slot_count": self.durable_slot_count,
            "successful_slot_count": self.successful_slot_count,
            "failed_slot_count": self.failed_slot_count,
            "missed_slot_count": self.missed_slot_count,
            "per_symbol_slot_counts": self.per_symbol_slot_counts,
            "accounted_root_bytes": self.accounted_root_bytes,
            "permissions": self.permissions,
        }


@dataclass(frozen=True)
class EventManifest:
    schema_version: str
    event_id: str
    coverage_status: str
    terminal_status_sha256: str
    event_contract_sha256: str
    authoritative_artifacts: list[dict[str, Any]]
    permissions: dict[str, bool]
    manifest_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "coverage_status": self.coverage_status,
            "terminal_status_sha256": self.terminal_status_sha256,
            "event_contract_sha256": self.event_contract_sha256,
            "authoritative_artifacts": self.authoritative_artifacts,
            "permissions": self.permissions,
            "manifest_id": self.manifest_id,
        }


@dataclass(frozen=True)
class SupervisorTerminalStatus:
    schema_version: str
    supervisor_run_id: str
    status: str
    terminal_reason: str
    terminal_at_ms: int
    accounted_root_bytes: int
    permissions: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "supervisor_run_id": self.supervisor_run_id,
            "status": self.status,
            "terminal_reason": self.terminal_reason,
            "terminal_at_ms": self.terminal_at_ms,
            "accounted_root_bytes": self.accounted_root_bytes,
            "permissions": self.permissions,
        }
