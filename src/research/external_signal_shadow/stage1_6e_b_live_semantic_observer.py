"""Stage 1.6E-B semantic reducer, admission authority, and supervisor."""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

from configs import base
from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter import (
    G2_GRAMMAR_PAIR,
    AdapterInputError,
    parse_and_normalize_bapi_body,
    parse_utc_timestamp_ms,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_IDS as E_A_PROFILE_IDS,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_client import (
    ScheduledSlot,
    Stage16EBPublicClient,
    generate_event_slots,
    validate_event_response_schema,
    validate_event_response_time,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    DelistingSemanticProjection,
    EnvironmentAuthorityReceipt,
    EventAdmission,
    EventCheckpoint,
    EventContract,
    EventProfileCore,
    EventTerminalStatus,
    MarketObservation,
    SlotIntent,
    SourceConsumerCheckpoint,
    canonical_json,
    compute_event_id,
    compute_notice_event_key,
    derive_event_profile_core,
    sha256_hex,
    stage1_6e_b_permissions,
    validate_event_checkpoint_dict,
    validate_market_observation_dict,
    validate_sha256,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_source import (
    Stage16EBSourceConsumer,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage import (
    RootWriterLock,
    Stage16EBStorageBlocked,
    Stage16EBStorageGuard,
    append_jsonl,
    probe_existing_event_writer_lock_stopped,
    validate_post_root_equality,
    verify_event_closed_tree_manifest,
    write_atomic_bytes,
    write_atomic_json,
    write_e_b_execution_environment_attestation,
    write_environment_authority_receipt,
    write_event_manifest,
)


@dataclasses.dataclass(frozen=True)
class C5WorkItem:
    """In-memory handoff contract for pending deterministic event root creation."""

    projection: DelistingSemanticProjection
    admission: EventAdmission
    deterministic_event_root: Path


class Stage16EBStructuralError(Exception):
    """Raised on upstream structural lineage corruption or data mismatch."""
    pass


class Stage16EBSemanticReducer:

    def __init__(self) -> None:
        self.grammar_pair = G2_GRAMMAR_PAIR

    def reduce_detail_revision(
        self,
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
        source_first_detected_at_ms: int,
        source_detail_trusted_at_ms: int,
        semantic_projected_at_ms: int,
        raw_bytes: bytes,
    ) -> DelistingSemanticProjection:
        try:
            parsed_bapi, parse_err = parse_and_normalize_bapi_body(
                raw_bytes,
                article_id=source_article_id,
                grammar_pair=self.grammar_pair,
            )
        except AdapterInputError as exc:
            raise Stage16EBStructuralError(str(exc)) from exc

        if parse_err is not None or parsed_bapi is None:
            return DelistingSemanticProjection.create(
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
                g2_body_normalization_version=self.grammar_pair[0],
                g2_semantic_extractor_version=self.grammar_pair[1],
                normalized_body_sha256=None,
                source_first_detected_at_ms=source_first_detected_at_ms,
                source_detail_trusted_at_ms=source_detail_trusted_at_ms,
                eligible_symbols_ordered=[],
                effective_delist_time_ms=None,
                eligibility_status="not_eligible",
                blocker=parse_err or "body_parse_unresolved",
                semantic_projected_at_ms=semantic_projected_at_ms,
            )

        norm_body = parsed_bapi["normalized_body"]
        norm_sha = parsed_bapi["normalized_body_sha256"]

        # Parse settlement time
        settle_match = re.search(
            r"(?:conduct automatic settlement|automatic settlement|close all positions and delist|will delist)[^\n\.\;]*?at\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*\(UTC\)",
            norm_body,
            re.IGNORECASE,
        )
        if not settle_match:
            return DelistingSemanticProjection.create(
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
                g2_body_normalization_version=self.grammar_pair[0],
                g2_semantic_extractor_version=self.grammar_pair[1],
                normalized_body_sha256=norm_sha,
                source_first_detected_at_ms=source_first_detected_at_ms,
                source_detail_trusted_at_ms=source_detail_trusted_at_ms,
                eligible_symbols_ordered=[],
                effective_delist_time_ms=None,
                eligibility_status="not_eligible",
                blocker="settlement_time_missing",
                semantic_projected_at_ms=semantic_projected_at_ms,
            )

        settle_ts = parse_utc_timestamp_ms(settle_match.group(1))
        if settle_ts is None or settle_ts <= semantic_projected_at_ms:
            return DelistingSemanticProjection.create(
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
                g2_body_normalization_version=self.grammar_pair[0],
                g2_semantic_extractor_version=self.grammar_pair[1],
                normalized_body_sha256=norm_sha,
                source_first_detected_at_ms=source_first_detected_at_ms,
                source_detail_trusted_at_ms=source_detail_trusted_at_ms,
                eligible_symbols_ordered=[],
                effective_delist_time_ms=None,
                eligibility_status="not_eligible",
                blocker="settlement_time_in_past",
                semantic_projected_at_ms=semantic_projected_at_ms,
            )

        # Extract USD-M perpetual symbols ending in USDT or USDC
        symbol_candidates = re.findall(
            r"\b([A-Z0-9]{2,10}(?:USDT|USDC))\b",
            norm_body + " " + parsed_bapi["title"],
        )


        seen_syms = set()
        eligible_symbols = []
        for s in symbol_candidates:
            s_clean = s.strip().upper()
            if (
                s_clean not in seen_syms
                and len(s_clean) >= 3
                and s_clean not in {"THE", "ALL", "AND", "PERPETUAL", "FUTURES", "CONTRACT"}
            ):
                if s_clean.endswith("USDT") or s_clean.endswith("USDC"):
                    seen_syms.add(s_clean)
                    eligible_symbols.append(s_clean)

        if len(eligible_symbols) == 0:
            return DelistingSemanticProjection.create(
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
                g2_body_normalization_version=self.grammar_pair[0],
                g2_semantic_extractor_version=self.grammar_pair[1],
                normalized_body_sha256=norm_sha,
                source_first_detected_at_ms=source_first_detected_at_ms,
                source_detail_trusted_at_ms=source_detail_trusted_at_ms,
                eligible_symbols_ordered=[],
                effective_delist_time_ms=None,
                eligibility_status="not_eligible",
                blocker="zero_eligible_symbols",
                semantic_projected_at_ms=semantic_projected_at_ms,
            )

        if len(eligible_symbols) > 3:
            return DelistingSemanticProjection.create(
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
                g2_body_normalization_version=self.grammar_pair[0],
                g2_semantic_extractor_version=self.grammar_pair[1],
                normalized_body_sha256=norm_sha,
                source_first_detected_at_ms=source_first_detected_at_ms,
                source_detail_trusted_at_ms=source_detail_trusted_at_ms,
                eligible_symbols_ordered=eligible_symbols,
                effective_delist_time_ms=None,
                eligibility_status="not_eligible",
                blocker="symbol_count_exceeds_three",
                semantic_projected_at_ms=semantic_projected_at_ms,
            )

        return DelistingSemanticProjection.create(
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
            g2_body_normalization_version=self.grammar_pair[0],
            g2_semantic_extractor_version=self.grammar_pair[1],
            normalized_body_sha256=norm_sha,
            source_first_detected_at_ms=source_first_detected_at_ms,
            source_detail_trusted_at_ms=source_detail_trusted_at_ms,
            eligible_symbols_ordered=eligible_symbols,
            effective_delist_time_ms=settle_ts,
            eligibility_status="eligible",
            blocker=None,
            semantic_projected_at_ms=semantic_projected_at_ms,
        )


class Stage16EBSupervisor:
    def __init__(
        self,
        supervisor_root: Path | str,
        events_root: Path | str,
        e_a_root: Path | str,
        guard: Stage16EBStorageGuard | None = None,
    ):
        self.supervisor_root = Path(supervisor_root).resolve()
        self.events_root = Path(events_root).resolve()
        self.e_a_root = Path(e_a_root).resolve()
        self.guard = guard
        self.reducer = Stage16EBSemanticReducer()
        self.supervisor_run_id = self.supervisor_root.name
        self.source_detail_raw_dir = self.supervisor_root / "source_detail_raw"
        self._projections_path = self.supervisor_root / "semantic_projections.jsonl"
        self._admissions_path = self.supervisor_root / "event_admissions.jsonl"
        self._checkpoint_path = self.supervisor_root / "source_consumer_checkpoint.json"

    def initialize_supervisor_root(
        self,
        *,
        step_a_projection: dict[str, Any],
        deployment_git_commit: str,
        e_a_manifest_id: str,
        e_a_manifest_sha256: str,
        e_a_attestation_sha256: str,
        e_a_attestation: dict[str, Any],
    ) -> None:
        if self.supervisor_root.is_symlink():
            raise Stage16EBStructuralError("supervisor_root_is_symlink")
        self.supervisor_root.mkdir(parents=True, exist_ok=True)
        self.source_detail_raw_dir.mkdir(parents=True, exist_ok=True)

        lock_path = self.supervisor_root / ".stage1_6e_b_supervisor_writer.lock"
        if not lock_path.exists():
            lock_path.touch()

        # POST-ROOT filesystem equality gate
        validate_post_root_equality(
            root=self.supervisor_root,
            lock_path=lock_path,
            step_a_projection=step_a_projection,
            e_a_attestation=e_a_attestation,
        )

        attest_file = self.supervisor_root / "execution_environment_attestation.json"
        if not attest_file.exists():
            _, e_b_attest_sha = write_e_b_execution_environment_attestation(
                root=self.supervisor_root,
                step_a_projection=step_a_projection,
                deployment_git_commit=deployment_git_commit,
                guard=self.guard,
                root_kind="supervisor",
            )
        else:
            e_b_attest_sha = sha256_hex(attest_file.read_bytes())

        receipt_file = self.supervisor_root / "environment_authority_receipt.json"
        if not receipt_file.exists():
            write_environment_authority_receipt(
                root=self.supervisor_root,
                root_kind="supervisor",
                e_a_manifest_id=e_a_manifest_id,
                e_a_manifest_sha256=e_a_manifest_sha256,
                e_a_environment_attestation_sha256=e_a_attestation_sha256,
                e_b_execution_environment_attestation_sha256=e_b_attest_sha,
                guard=self.guard,
            )

    def get_active_event_id(self) -> str | None:
        if not self._checkpoint_path.exists():
            return None
        try:
            chk_dict = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
            return chk_dict.get("active_event_id")
        except Exception:
            return None

    def get_active_event_root(self) -> Path | None:
        active_id = self.get_active_event_id()
        if active_id is None:
            return None
        event_dir = self.events_root / active_id
        if not event_dir.exists() or event_dir.is_symlink():
            return None
        return event_dir

    def step_source_stream(
        self,
        consumer: Stage16EBSourceConsumer,
        current_time_ms: int,
    ) -> C5WorkItem | None:
        snapshot = consumer.poll_and_validate_source_snapshot(current_time_ms)
        if not snapshot.is_ready:
            return None

        src_chk = snapshot.checkpoint
        offsets = src_chk["stream_offsets"]
        hashes = src_chk["stream_last_hashes"]
        target_offset = offsets["detail_revisions.jsonl"]

        chk_path = self._checkpoint_path
        if not chk_path.exists():
            # FRESH BOOTSTRAP: write checkpoint at current boundary and return None
            last_line_sha = None
            last_seq = None
            if target_offset > 0:
                last_line_sha = hashes["detail_revisions.jsonl"]
                rev_file = consumer.authorized_source_root / "detail_revisions.jsonl"
                with open(rev_file, "rb") as f:
                    f.seek(0)
                    committed_rev_bytes = f.read(target_offset)
                last_line = committed_rev_bytes.rstrip(b"\r\n").splitlines()[-1]
                last_rev_data = json.loads(last_line.decode("utf-8"))
                last_seq = int(last_rev_data["record_seq"])

            boot_chk = SourceConsumerCheckpoint.create(
                supervisor_run_id=self.supervisor_run_id,
                source_root_realpath=str(consumer.authorized_source_root.resolve()),
                source_checkpoint_id=snapshot.checkpoint_id,
                source_checkpoint_sha256=snapshot.checkpoint_sha256,
                source_stream_offsets=offsets,
                source_stream_last_hashes=hashes,
                detail_revisions_committed_offset=target_offset,
                detail_revisions_last_line_sha256=last_line_sha,
                last_consumed_detail_revision_record_seq=last_seq,
                active_notice_event_key=None,
                active_event_id=None,
                updated_at_ms=current_time_ms,
            )
            write_atomic_json(self._checkpoint_path, boot_chk.to_dict())
            return None

        # Suffix consumption
        curr_consumer_chk = SourceConsumerCheckpoint.from_dict(
            json.loads(chk_path.read_text(encoding="utf-8"))
        )
        from_offset = curr_consumer_chk.detail_revisions_committed_offset
        if target_offset < from_offset:
            raise Stage16EBStructuralError("source_stream_rollback_detected")

        if target_offset == from_offset:
            return None

        revs = consumer.read_new_detail_revisions(from_offset, target_offset)
        c5_item: C5WorkItem | None = None

        for rev in revs:
            linked_obs, raw_bytes = consumer.link_and_verify_detail_revision(rev, src_chk)
            raw_sha = rev["detail_raw_sha256"]
            dest_raw = self.source_detail_raw_dir / f"{raw_sha}.bin"
            if not dest_raw.exists():
                write_atomic_bytes(dest_raw, raw_bytes)

            proj = self.reducer.reduce_detail_revision(
                supervisor_run_id=self.supervisor_run_id,
                source_root_realpath=str(consumer.authorized_source_root.resolve()),
                source_checkpoint_id=snapshot.checkpoint_id,
                source_checkpoint_sha256=snapshot.checkpoint_sha256,
                source_article_id=str(rev["source_article_id"]),
                source_request_observation_id=linked_obs["request_observation_id"],
                source_detail_revision_id=str(rev["detail_revision_id"]),
                source_detail_raw_sha256=raw_sha,
                source_detail_raw_relative_path=str(rev["raw_payload_relative_path"]),
                copied_source_raw_relative_path=f"source_detail_raw/{raw_sha}.bin",
                source_first_detected_at_ms=int(linked_obs["captured_at_ms"]),
                source_detail_trusted_at_ms=int(rev["t_detail_trusted_ms"]),
                semantic_projected_at_ms=current_time_ms,
                raw_bytes=raw_bytes,
            )
            append_jsonl(self._projections_path, proj.to_dict())

            active_id = self.get_active_event_id()
            adm = self.evaluate_notice_admission(
                semantic_projection_id=proj.semantic_projection_id,
                source_article_id=proj.source_article_id,
                decided_at_ms=current_time_ms,
                active_event_id=active_id,
            )
            append_jsonl(self._admissions_path, adm.to_dict())

            if adm.decision == "admitted" and c5_item is None:
                c5_item = C5WorkItem(
                    projection=proj,
                    admission=adm,
                    deterministic_event_root=self.events_root / adm.event_id,
                )

        last_rev = revs[-1]
        last_seq = int(last_rev["record_seq"])
        last_line_sha = hashes["detail_revisions.jsonl"]

        updated_chk = SourceConsumerCheckpoint.create(
            supervisor_run_id=self.supervisor_run_id,
            source_root_realpath=str(consumer.authorized_source_root.resolve()),
            source_checkpoint_id=snapshot.checkpoint_id,
            source_checkpoint_sha256=snapshot.checkpoint_sha256,
            source_stream_offsets=offsets,
            source_stream_last_hashes=hashes,
            detail_revisions_committed_offset=target_offset,
            detail_revisions_last_line_sha256=last_line_sha,
            last_consumed_detail_revision_record_seq=last_seq,
            active_notice_event_key=curr_consumer_chk.active_notice_event_key,
            active_event_id=curr_consumer_chk.active_event_id,
            updated_at_ms=current_time_ms,
        )
        write_atomic_json(self._checkpoint_path, updated_chk.to_dict())

        return c5_item

    def evaluate_notice_admission(
        self,
        *,
        semantic_projection_id: str,
        source_article_id: str,
        decided_at_ms: int,
        active_event_id: str | None,
    ) -> EventAdmission:
        notice_key = compute_notice_event_key(source_article_id)
        event_id = compute_event_id(semantic_projection_id)

        if active_event_id is not None:
            return EventAdmission.create(
                semantic_projection_id=semantic_projection_id,
                notice_event_key=notice_key,
                event_id=event_id,
                decision="event_observation_capacity_blocked",
                blocker="active_event_exists",
                active_event_id_at_decision=active_event_id,
                decided_at_ms=decided_at_ms,
            )

        return EventAdmission.create(
            semantic_projection_id=semantic_projection_id,
            notice_event_key=notice_key,
            event_id=event_id,
            decision="admitted",
            blocker=None,
            active_event_id_at_decision=None,
            decided_at_ms=decided_at_ms,
        )

    def create_event_root_dir(self, c5_item: C5WorkItem) -> tuple[Path, RootWriterLock]:
        event_dir = c5_item.deterministic_event_root
        if event_dir.exists():
            raise Stage16EBStructuralError(f"event_root_already_exists: {event_dir}")
        event_dir.mkdir(parents=True, exist_ok=False)
        lock = RootWriterLock(event_dir, ".stage1_6e_b_event_writer.lock")
        lock.acquire()
        return event_dir, lock

    def populate_and_activate_event_root(
        self,
        *,
        c5_item: C5WorkItem,
        lock: RootWriterLock,
        step_a_projection: dict[str, Any],
        deployment_git_commit: str,
        e_a_gate_info: dict[str, Any],
        start_time_ms: int | None = None,
    ) -> None:
        event_dir = c5_item.deterministic_event_root
        admission = c5_item.admission
        projection = c5_item.projection

        e_a_manifest_id = e_a_gate_info["manifest_id"]
        e_a_manifest_sha256 = e_a_gate_info["manifest_sha256"]
        e_a_attestation_sha256 = e_a_gate_info["environment_attestation_sha256"]
        e_a_profile_cores = e_a_gate_info["profile_cores"]
        e_a_profile_attestation_sha256_by_id = e_a_gate_info[
            "profile_attestation_sha256_by_id"
        ]

        # 1. Execution environment attestation (E-B's own)
        _, e_b_attest_sha = write_e_b_execution_environment_attestation(
            root=event_dir,
            step_a_projection=step_a_projection,
            deployment_git_commit=deployment_git_commit,
            guard=self.guard,
            root_kind="event",
        )

        # 2. Authority receipt
        write_environment_authority_receipt(
            root=event_dir,
            root_kind="event",
            e_a_manifest_id=e_a_manifest_id,
            e_a_manifest_sha256=e_a_manifest_sha256,
            e_a_environment_attestation_sha256=e_a_attestation_sha256,
            e_b_execution_environment_attestation_sha256=e_b_attest_sha,
            guard=self.guard,
        )

        # 3. Profile attestations for each symbol
        profile_dir = event_dir / "profile_attestations"
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_attestation_map = {}

        for sym in projection.eligible_symbols_ordered:
            for base_pid in E_A_PROFILE_IDS:
                if base_pid not in e_a_profile_cores:
                    raise Stage16EBStructuralError(f"missing_e_a_profile_core: {base_pid}")
                derived = derive_event_profile_core(
                    event_id=admission.event_id,
                    source_article_id=projection.source_article_id,
                    source_detail_revision_id=projection.source_detail_revision_id,
                    canonical_symbol=sym,
                    base_e_a_manifest_id=e_a_manifest_id,
                    base_e_a_profile_id=base_pid,
                    base_e_a_profile_attestation_sha256=e_a_profile_attestation_sha256_by_id[base_pid],
                    base_e_a_profile_core=e_a_profile_cores[base_pid],
                )
                p_path = profile_dir / f"{sym}.{base_pid}.json"
                write_atomic_json(p_path, derived.to_dict())
                profile_attestation_map[f"{sym}:{base_pid}"] = derived.profile_attestation_sha256

        # 4. Event contract
        expected_slots = len(projection.eligible_symbols_ordered) * 1586
        contract = EventContract(
            schema_version="stage1_6e_b_event_contract_v1",
            event_id=admission.event_id,
            supervisor_run_id=projection.supervisor_run_id,
            semantic_projection_id=projection.semantic_projection_id,
            semantic_projection_row_sha256=sha256_hex(canonical_json(projection.to_dict()).encode("utf-8")),
            admission_id=admission.admission_id,
            admission_row_sha256=sha256_hex(canonical_json(admission.to_dict()).encode("utf-8")),
            source_article_id=projection.source_article_id,
            source_detail_revision_id=projection.source_detail_revision_id,
            source_detail_raw_sha256=projection.source_detail_raw_sha256,
            source_checkpoint_id=projection.source_checkpoint_id,
            source_checkpoint_sha256=projection.source_checkpoint_sha256,
            effective_delist_time_ms=projection.effective_delist_time_ms or 0,
            event_window_started_at_ms=projection.semantic_projected_at_ms,
            event_window_ends_at_ms=projection.semantic_projected_at_ms + base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_WINDOW_MS,
            window_duration_ms=base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_WINDOW_MS,
            canonical_symbols_ordered=projection.eligible_symbols_ordered,
            canonical_symbols_normalized=projection.eligible_symbols_normalized,
            symbol_set_sha256=projection.eligible_symbol_set_sha256 or "",
            expected_slot_count=expected_slots,
            e_a_manifest_id=e_a_manifest_id,
            e_a_manifest_sha256=e_a_manifest_sha256,
            e_a_profile_attestation_sha256_by_id=e_a_profile_attestation_sha256_by_id,
            execution_environment_attestation_sha256=e_b_attest_sha,
            storage_contract={
                "event_root_max_bytes": base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ROOT_MAX_BYTES,
                "event_ordinary_reserve_bytes": base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ORDINARY_RESERVE_BYTES,
                "event_emergency_reserve_bytes": base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_EMERGENCY_RESERVE_BYTES,
            },
            permissions=stage1_6e_b_permissions(),
        )
        contract_sha = write_atomic_json(event_dir / "event_contract.json", contract.to_dict())

        # 5. Initial empty event checkpoint
        chk = EventCheckpoint.create(
            event_id=admission.event_id,
            event_contract_sha256=contract_sha,
            profile_attestation_sha256_by_symbol_and_profile=profile_attestation_map,
            completed_slot_ids_ordered=[],
            last_observation_sha256=None,
            accounted_root_bytes=1000,
            inflight_slot_intent=None,
            updated_at_ms=projection.semantic_projected_at_ms if start_time_ms is None else start_time_ms,
        )
        write_atomic_json(event_dir / "event_checkpoint.json", chk.to_dict())

        # 6. Release creation writer lock
        lock.release()

        # 7. Atomically record active fields in consumer checkpoint
        if self._checkpoint_path.exists():
            curr_chk = SourceConsumerCheckpoint.from_dict(
                json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
            )
            updated_chk = dataclasses.replace(
                curr_chk,
                active_notice_event_key=admission.notice_event_key,
                active_event_id=admission.event_id,
                updated_at_ms=projection.semantic_projected_at_ms,
            )
            write_atomic_json(self._checkpoint_path, updated_chk.to_dict())

    def check_startup_recovery(
        self,
        current_time_ms: int,
        *,
        step_a_projection: dict[str, Any],
        e_a_gate_info: dict[str, Any],
        deployment_git_commit: str,
    ) -> tuple[str, C5WorkItem | None]:
        if not self._checkpoint_path.exists():
            return "CLEAN", None
        curr_chk = SourceConsumerCheckpoint.from_dict(
            json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
        )
        if curr_chk.active_event_id is not None:
            if self.try_release_terminal_capacity(current_time_ms):
                return "CLEAN", None
            event_dir = self.events_root / curr_chk.active_event_id
            if not event_dir.exists() or event_dir.is_symlink():
                raise Stage16EBStructuralError(
                    f"global_active_supervisor_state_invalid: active_event_dir_missing: {curr_chk.active_event_id}"
                )
            if (event_dir / "terminal_status.json").exists() or (event_dir / "manifest.json").exists():
                raise Stage16EBStructuralError(
                    "global_active_supervisor_state_invalid: active_event_already_terminal_or_has_manifest"
                )
            return "ACTIVE", None

        # active_event_id is None, active_notice_event_key must also be None
        if curr_chk.active_notice_event_key is not None:
            raise Stage16EBStructuralError(
                "global_active_supervisor_state_invalid: active_notice_event_key_without_active_event_id"
            )

        if not self._admissions_path.exists():
            return "CLEAN", None

        admitted_rows: list[EventAdmission] = []
        for line in self._admissions_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("decision") == "admitted":
                admitted_rows.append(EventAdmission(**row))

        nonterminal_admissions: list[EventAdmission] = []
        for adm in admitted_rows:
            event_dir = self.events_root / adm.event_id
            term_file = event_dir / "terminal_status.json"
            manifest_file = event_dir / "manifest.json"
            if event_dir.is_symlink():
                raise Stage16EBStructuralError(
                    "global_active_supervisor_state_invalid: terminal_event_root_is_symlink"
                )
            if term_file.exists() or manifest_file.exists():
                if not term_file.is_file() or term_file.is_symlink():
                    raise Stage16EBStructuralError(
                        "global_active_supervisor_state_invalid: terminal_status_missing_or_symlink"
                    )
                try:
                    terminal_data = json.loads(term_file.read_text(encoding="utf-8"))
                except Exception as exc:
                    raise Stage16EBStructuralError(
                        "global_active_supervisor_state_invalid: terminal_status_invalid"
                    ) from exc
                if terminal_data.get("schema_version") != "stage1_6e_b_terminal_status_v1":
                    raise Stage16EBStructuralError(
                        "global_active_supervisor_state_invalid: terminal_status_schema_invalid"
                    )
                if terminal_data.get("status") == "complete":
                    if not manifest_file.is_file() or manifest_file.is_symlink():
                        raise Stage16EBStructuralError(
                            "global_active_supervisor_state_invalid: complete_terminal_manifest_missing"
                        )
                    try:
                        verify_event_closed_tree_manifest(event_dir)
                    except Exception as exc:
                        raise Stage16EBStructuralError(
                            "global_active_supervisor_state_invalid: complete_terminal_manifest_invalid"
                        ) from exc
                    continue
                if terminal_data.get("status") == "failed":
                    if manifest_file.exists() or not probe_existing_event_writer_lock_stopped(event_dir):
                        raise Stage16EBStructuralError(
                            "global_active_supervisor_state_invalid: failed_terminal_capacity_not_released"
                        )
                    continue
                raise Stage16EBStructuralError(
                    "global_active_supervisor_state_invalid: terminal_status_unknown"
                )
            nonterminal_admissions.append(adm)

        if not nonterminal_admissions:
            return "CLEAN", None

        if len(nonterminal_admissions) > 1:
            raise Stage16EBStructuralError(
                "global_active_supervisor_state_invalid: multiple_nonterminal_admitted_events"
            )

        target_adm = nonterminal_admissions[0]
        if not self._projections_path.exists():
            raise Stage16EBStructuralError(
                "global_active_supervisor_state_invalid: semantic_projections_missing"
            )

        target_proj: DelistingSemanticProjection | None = None
        for line in self._projections_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            p_data = json.loads(line)
            if p_data.get("semantic_projection_id") == target_adm.semantic_projection_id:
                target_proj = DelistingSemanticProjection(**p_data)
                break

        if target_proj is None:
            raise Stage16EBStructuralError(
                f"global_active_supervisor_state_invalid: missing_projection_for_admission: {target_adm.semantic_projection_id}"
            )

        event_dir = self.events_root / target_adm.event_id
        if not event_dir.exists():
            # C5: uncreated admission
            return "C5_PENDING", C5WorkItem(
                projection=target_proj,
                admission=target_adm,
                deterministic_event_root=event_dir,
            )

        # C6: deterministic root exists, controlled-resume validation
        self._validate_c6_controlled_resume(
            event_dir=event_dir,
            admission=target_adm,
            projection=target_proj,
            step_a_projection=step_a_projection,
            e_a_gate_info=e_a_gate_info,
            deployment_git_commit=deployment_git_commit,
        )
        updated_chk = dataclasses.replace(
            curr_chk,
            active_notice_event_key=target_adm.notice_event_key,
            active_event_id=target_adm.event_id,
            updated_at_ms=current_time_ms,
        )
        write_atomic_json(self._checkpoint_path, updated_chk.to_dict())
        return "C6_RECOVERED", None

    def _validate_c6_controlled_resume(
        self,
        *,
        event_dir: Path,
        admission: EventAdmission,
        projection: DelistingSemanticProjection,
        step_a_projection: dict[str, Any],
        e_a_gate_info: dict[str, Any],
        deployment_git_commit: str,
    ) -> None:
        if not event_dir.exists() or event_dir.is_symlink():
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_event_root_missing_or_symlink")
        if (event_dir / "terminal_status.json").exists() or (event_dir / "manifest.json").exists():
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_terminal_or_manifest_present")

        attest_file = event_dir / "execution_environment_attestation.json"
        receipt_file = event_dir / "environment_authority_receipt.json"
        if not attest_file.is_file() or attest_file.is_symlink():
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_attestation_missing")
        if not receipt_file.is_file() or receipt_file.is_symlink():
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_receipt_missing")
        try:
            attest_bytes = attest_file.read_bytes()
            attest_data = json.loads(attest_bytes.decode("utf-8"))
        except Exception as exc:
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_attestation_invalid") from exc
        for key in (
            "deployment_host_identity",
            "hostname",
            "project_root_realpath",
            "network_namespace_inode",
            "proxy_environment",
            "runtime_user_uid",
            "deployment_runtime_worktree_clean",
        ):
            if attest_data.get(key) != step_a_projection.get(key):
                raise Stage16EBStructuralError(
                    f"global_active_supervisor_state_invalid: c6_attestation_{key}_mismatch"
                )
        attest_for_id = dict(attest_data)
        execution_environment_id = attest_for_id.pop("execution_environment_id", None)
        if (
            attest_data.get("deployment_git_commit") != deployment_git_commit
            or attest_data.get("permissions") != e_a_gate_info["environment_attestation"].get("permissions")
            or execution_environment_id != sha256_hex(canonical_json(attest_for_id).encode("utf-8"))
        ):
            raise Stage16EBStructuralError(
                "global_active_supervisor_state_invalid: c6_attestation_mismatch"
            )
        try:
            validate_post_root_equality(
                root=event_dir,
                lock_path=event_dir / ".stage1_6e_b_event_writer.lock",
                step_a_projection=step_a_projection,
                e_a_attestation=e_a_gate_info["environment_attestation"],
            )
        except Exception as exc:
            raise Stage16EBStructuralError(
                "global_active_supervisor_state_invalid: c6_post_root_environment_mismatch"
            ) from exc
        e_b_attestation_sha256 = sha256_hex(attest_bytes)
        try:
            receipt = EnvironmentAuthorityReceipt.from_dict(
                json.loads(receipt_file.read_text(encoding="utf-8"))
            )
        except Exception as exc:
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_receipt_invalid") from exc
        if (
            receipt.root_kind != "event"
            or receipt.e_a_manifest_id != e_a_gate_info["manifest_id"]
            or receipt.e_a_manifest_sha256 != e_a_gate_info["manifest_sha256"]
            or receipt.e_a_environment_attestation_sha256
            != e_a_gate_info["environment_attestation_sha256"]
            or receipt.e_b_execution_environment_attestation_sha256 != e_b_attestation_sha256
        ):
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_receipt_mismatch")

        contract_file = event_dir / "event_contract.json"
        if not contract_file.is_file() or contract_file.is_symlink():
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_contract_missing")
        contract_dict = json.loads(contract_file.read_text(encoding="utf-8"))
        if contract_dict.get("event_id") != admission.event_id:
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_event_id_mismatch")
        if contract_dict.get("source_detail_raw_sha256") != projection.source_detail_raw_sha256:
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_raw_sha_mismatch")
        if contract_dict.get("event_window_started_at_ms") != projection.semantic_projected_at_ms:
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_event_time_mismatch")
        if (
            contract_dict.get("semantic_projection_id") != projection.semantic_projection_id
            or contract_dict.get("semantic_projection_row_sha256")
            != sha256_hex(canonical_json(projection.to_dict()).encode("utf-8"))
            or contract_dict.get("admission_id") != admission.admission_id
            or contract_dict.get("admission_row_sha256")
            != sha256_hex(canonical_json(admission.to_dict()).encode("utf-8"))
            or contract_dict.get("source_article_id") != projection.source_article_id
            or contract_dict.get("source_detail_revision_id") != projection.source_detail_revision_id
            or contract_dict.get("source_checkpoint_id") != projection.source_checkpoint_id
            or contract_dict.get("source_checkpoint_sha256") != projection.source_checkpoint_sha256
            or contract_dict.get("effective_delist_time_ms") != projection.effective_delist_time_ms
            or contract_dict.get("event_window_ends_at_ms")
            != projection.semantic_projected_at_ms + base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_WINDOW_MS
            or contract_dict.get("window_duration_ms") != base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_WINDOW_MS
            or contract_dict.get("canonical_symbols_ordered") != projection.eligible_symbols_ordered
            or contract_dict.get("canonical_symbols_normalized") != projection.eligible_symbols_normalized
            or contract_dict.get("symbol_set_sha256") != projection.eligible_symbol_set_sha256
            or contract_dict.get("e_a_manifest_id") != e_a_gate_info["manifest_id"]
            or contract_dict.get("e_a_manifest_sha256") != e_a_gate_info["manifest_sha256"]
            or contract_dict.get("e_a_profile_attestation_sha256_by_id")
            != e_a_gate_info["profile_attestation_sha256_by_id"]
            or contract_dict.get("execution_environment_attestation_sha256") != e_b_attestation_sha256
        ):
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_contract_mismatch")

        profile_attestation_map: dict[str, str] = {}
        for symbol in projection.eligible_symbols_ordered:
            for profile_id in E_A_PROFILE_IDS:
                profile_file = event_dir / "profile_attestations" / f"{symbol}.{profile_id}.json"
                if not profile_file.is_file() or profile_file.is_symlink():
                    raise Stage16EBStructuralError(
                        "global_active_supervisor_state_invalid: c6_profile_attestation_missing"
                    )
                try:
                    profile_data = json.loads(profile_file.read_text(encoding="utf-8"))
                    profile = EventProfileCore(**profile_data)
                except Exception as exc:
                    raise Stage16EBStructuralError(
                        "global_active_supervisor_state_invalid: c6_profile_attestation_invalid"
                    ) from exc
                profile_for_hash = profile.to_dict()
                profile_for_hash.pop("profile_attestation_sha256")
                if (
                    profile.event_id != admission.event_id
                    or profile.source_article_id != projection.source_article_id
                    or profile.source_detail_revision_id != projection.source_detail_revision_id
                    or profile.canonical_symbol != symbol
                    or profile.base_e_a_manifest_id != e_a_gate_info["manifest_id"]
                    or profile.base_e_a_profile_id != profile_id
                    or profile.base_e_a_profile_attestation_sha256
                    != e_a_gate_info["profile_attestation_sha256_by_id"][profile_id]
                    or profile.base_e_a_profile_core_sha256
                    != sha256_hex(canonical_json(e_a_gate_info["profile_cores"][profile_id]).encode("utf-8"))
                    or profile.profile_attestation_sha256
                    != sha256_hex(canonical_json(profile_for_hash).encode("utf-8"))
                ):
                    raise Stage16EBStructuralError(
                        "global_active_supervisor_state_invalid: c6_profile_attestation_mismatch"
                    )
                profile_attestation_map[f"{symbol}:{profile_id}"] = profile.profile_attestation_sha256

        chk_file = event_dir / "event_checkpoint.json"
        if not chk_file.is_file() or chk_file.is_symlink():
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_checkpoint_missing")
        try:
            checkpoint_data = json.loads(chk_file.read_text(encoding="utf-8"))
            validate_event_checkpoint_dict(checkpoint_data)
        except Exception as exc:
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_checkpoint_invalid") from exc
        if (
            checkpoint_data["event_id"] != admission.event_id
            or checkpoint_data["event_contract_sha256"] != sha256_hex(contract_file.read_bytes())
            or checkpoint_data["profile_attestation_sha256_by_symbol_and_profile"] != profile_attestation_map
        ):
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_checkpoint_mismatch")

        source_raw_file = self.source_detail_raw_dir / f"{projection.source_detail_raw_sha256}.bin"
        if not source_raw_file.is_file() or source_raw_file.is_symlink():
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_source_raw_missing")
        if sha256_hex(source_raw_file.read_bytes()) != projection.source_detail_raw_sha256:
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_source_raw_mismatch")

        lock = RootWriterLock(event_dir, ".stage1_6e_b_event_writer.lock")
        try:
            lock.acquire()
            lock.release()
        except Exception as exc:
            raise Stage16EBStructuralError("global_active_supervisor_state_invalid: c6_lock_ownership_failed") from exc

    def try_release_terminal_capacity(self, current_time_ms: int) -> bool:
        active_id = self.get_active_event_id()
        if active_id is None:
            return False
        event_dir = self.events_root / active_id
        if not event_dir.exists() or event_dir.is_symlink():
            return False
        term_path = event_dir / "terminal_status.json"
        if not term_path.exists() or term_path.is_symlink():
            return False
        try:
            term_dict = json.loads(term_path.read_text(encoding="utf-8"))
            if term_dict.get("schema_version") != "stage1_6e_b_terminal_status_v1":
                return False
            term_status = term_dict.get("status")
        except Exception:
            return False

        manifest_path = event_dir / "manifest.json"
        if term_status == "complete":
            if not manifest_path.exists() or manifest_path.is_symlink():
                return False
            try:
                verify_event_closed_tree_manifest(event_dir)
            except Exception:
                return False
            self._release_active_event_capacity(current_time_ms)
            return True

        if term_status == "failed":
            if manifest_path.exists():
                return False
            if not probe_existing_event_writer_lock_stopped(event_dir):
                return False
            self._release_active_event_capacity(current_time_ms)
            return True

        return False

    def _release_active_event_capacity(self, current_time_ms: int) -> None:
        if self._checkpoint_path.exists():
            curr_chk = SourceConsumerCheckpoint.from_dict(
                json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
            )
            updated_chk = dataclasses.replace(
                curr_chk,
                active_notice_event_key=None,
                active_event_id=None,
                updated_at_ms=current_time_ms,
            )
            write_atomic_json(self._checkpoint_path, updated_chk.to_dict())



class Stage16EBEventObserver:
    """Live event observer executing sequential slots with WAL idempotency."""

    def __init__(
        self,
        event_root: Path,
        client: Stage16EBPublicClient,
        guard: Stage16EBStorageGuard | None = None,
    ) -> None:
        self.event_root = Path(event_root).resolve()
        self.client = client
        self.guard = guard
        self._writer_lock = RootWriterLock(self.event_root, ".stage1_6e_b_event_writer.lock")
        self.contract: EventContract | None = None
        self.profile_cores: dict[str, EventProfileCore] = {}
        self.slots: list[ScheduledSlot] = []
        self.checkpoint: EventCheckpoint | None = None
        self.observations: list[MarketObservation] = []
        self._next_request_seq: int = 1
        self._observations_path = self.event_root / "observations.jsonl"
        self._checkpoint_path = self.event_root / "event_checkpoint.json"

    def close(self) -> None:
        self._writer_lock.release()

    def __enter__(self) -> Stage16EBEventObserver:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def resume_and_validate(self) -> None:
        if self.event_root.is_symlink():
            raise Stage16EBStructuralError("event_root_is_symlink")
        if not self.event_root.exists():
            raise Stage16EBStructuralError(f"event_root_not_found: {self.event_root}")

        # Acquire lock
        self._writer_lock.acquire()

        # Terminal or manifest presence check: if either exists, cannot resume observation
        if (self.event_root / "terminal_status.json").exists():
            raise Stage16EBStructuralError("event_already_has_terminal_status")
        if (self.event_root / "manifest.json").exists():
            raise Stage16EBStructuralError("event_already_has_manifest")

        # Read event_contract.json
        contract_path = self.event_root / "event_contract.json"
        if not contract_path.exists():
            raise Stage16EBStructuralError("event_contract_missing")
        contract_dict = json.loads(contract_path.read_text(encoding="utf-8"))
        if contract_dict.get("schema_version") != "stage1_6e_b_event_contract_v1":
            raise Stage16EBStructuralError("event_contract_schema_invalid")
        validate_sha256(contract_dict["event_id"])
        if contract_dict["permissions"] != stage1_6e_b_permissions():
            raise Stage16EBStructuralError("event_contract_permissions_invalid")

        self.contract = EventContract(**contract_dict)

        # Read profile attestations
        profile_dir = self.event_root / "profile_attestations"
        if not profile_dir.exists():
            raise Stage16EBStructuralError("profile_attestations_dir_missing")

        self.profile_cores = {}
        for sym in self.contract.canonical_symbols_ordered:
            for pid in E_A_PROFILE_IDS:
                p_file = profile_dir / f"{sym}.{pid}.json"
                if not p_file.exists():
                    raise Stage16EBStructuralError(f"profile_attestation_missing: {p_file}")
                p_dict = json.loads(p_file.read_text(encoding="utf-8"))
                p_core = EventProfileCore(**p_dict)
                self.profile_cores[f"{sym}:{pid}"] = p_core

        # Generate deterministic scheduled slots
        self.slots = generate_event_slots(self.contract, self.profile_cores)

        # Read checkpoint
        if not self._checkpoint_path.exists():
            raise Stage16EBStructuralError("event_checkpoint_missing")
        chk_dict = json.loads(self._checkpoint_path.read_text(encoding="utf-8"))
        validate_event_checkpoint_dict(chk_dict)
        if chk_dict["event_id"] != self.contract.event_id:
            raise Stage16EBStructuralError("checkpoint_event_id_mismatch")
        contract_sha = sha256_hex(contract_path.read_bytes())
        if chk_dict["event_contract_sha256"] != contract_sha:
            raise Stage16EBStructuralError("checkpoint_contract_sha_mismatch")

        self.checkpoint = EventCheckpoint(**chk_dict)

        # Read observations if present
        self.observations = []
        if self._observations_path.exists():
            lines = self._observations_path.read_text(encoding="utf-8").splitlines()
            prev_seq = 0
            for line in lines:
                if not line.strip():
                    continue
                obs_dict = json.loads(line)
                validate_market_observation_dict(obs_dict)
                if obs_dict["event_id"] != self.contract.event_id:
                    raise Stage16EBStructuralError("observation_event_id_mismatch")
                seq = obs_dict.get("request_sequence")
                if seq is not None:
                    if seq != prev_seq + 1:
                        raise Stage16EBStructuralError(f"request_sequence_not_strictly_increasing: {seq} vs {prev_seq}")
                    prev_seq = seq
                    self._next_request_seq = max(self._next_request_seq, seq + 1)
                if obs_dict.get("raw_payload_persisted"):
                    raw_rel = obs_dict["raw_relative_path"]
                    raw_file = self.event_root / raw_rel
                    if not raw_file.is_file() or raw_file.is_symlink():
                        raise Stage16EBStructuralError(f"persisted_raw_file_missing: {raw_rel}")
                    raw_bytes = raw_file.read_bytes()
                    if len(raw_bytes) != obs_dict["raw_byte_count"] or sha256_hex(raw_bytes) != obs_dict["raw_sha256"]:
                        raise Stage16EBStructuralError(f"persisted_raw_hash_or_size_mismatch: {raw_rel}")
                self.observations.append(MarketObservation(**obs_dict))

        # Reconcile WAL
        self._reconcile_wal()

    def _reconcile_wal(self) -> None:
        assert self.contract is not None
        assert self.checkpoint is not None

        obs_slot_ids = [obs.slot_id for obs in self.observations]
        chk_slot_ids = list(self.checkpoint.completed_slot_ids_ordered)
        intent = self.checkpoint.inflight_slot_intent

        if (
            len(obs_slot_ids) == len(chk_slot_ids) + 1
            and sorted(obs_slot_ids[:-1]) == chk_slot_ids
            and obs_slot_ids[-1] not in chk_slot_ids
        ):
            # Observation one ahead of checkpoint: roll-forward
            last_obs = self.observations[-1]
            last_sha = sha256_hex(canonical_json(last_obs.to_dict()).encode("utf-8"))
            new_chk_slots = sorted(chk_slot_ids + [last_obs.slot_id])
            self.checkpoint = EventCheckpoint.create(
                event_id=self.contract.event_id,
                event_contract_sha256=self.checkpoint.event_contract_sha256,
                profile_attestation_sha256_by_symbol_and_profile=self.checkpoint.profile_attestation_sha256_by_symbol_and_profile,
                completed_slot_ids_ordered=new_chk_slots,
                last_observation_sha256=last_sha,
                accounted_root_bytes=self.checkpoint.accounted_root_bytes,
                inflight_slot_intent=None,
                updated_at_ms=self.checkpoint.updated_at_ms,
            )
            write_atomic_json(self._checkpoint_path, self.checkpoint.to_dict())
            intent = None
            chk_slot_ids = new_chk_slots
        elif len(obs_slot_ids) < len(chk_slot_ids) or len(obs_slot_ids) > len(chk_slot_ids) + 1:
            raise Stage16EBStructuralError("checkpoint_observations_mismatch")
        elif sorted(obs_slot_ids) != chk_slot_ids:
            raise Stage16EBStructuralError("checkpoint_observations_slot_id_mismatch")

        if intent is not None:
            intent_slot_id = intent["slot_id"]
            intent_stage = intent["stage"]
            if intent_slot_id in obs_slot_ids:
                # Intent has matching durable observation: checkpoint-only clear
                self.checkpoint = EventCheckpoint.create(
                    event_id=self.contract.event_id,
                    event_contract_sha256=self.checkpoint.event_contract_sha256,
                    profile_attestation_sha256_by_symbol_and_profile=self.checkpoint.profile_attestation_sha256_by_symbol_and_profile,
                    completed_slot_ids_ordered=chk_slot_ids,
                    last_observation_sha256=self.checkpoint.last_observation_sha256,
                    accounted_root_bytes=self.checkpoint.accounted_root_bytes,
                    inflight_slot_intent=None,
                    updated_at_ms=self.checkpoint.updated_at_ms,
                )
                write_atomic_json(self._checkpoint_path, self.checkpoint.to_dict())
            else:
                slot_obj = next((s for s in self.slots if s.slot_id == intent_slot_id), None)
                if slot_obj is None:
                    raise Stage16EBStructuralError(f"intent_slot_not_in_schedule: {intent_slot_id}")
                attest_sha = self.profile_cores[f"{slot_obj.canonical_symbol}:{slot_obj.base_e_a_profile_id}"].profile_attestation_sha256

                if intent_stage == "prepared":
                    obs = MarketObservation.create_unknown_after_restart(
                        event_id=self.contract.event_id,
                        slot_id=intent_slot_id,
                        slot_family=slot_obj.slot_family,
                        slot_index=slot_obj.slot_index,
                        due_at_ms=slot_obj.due_at_ms,
                        completed_at_ms=intent.get("reserved_at_ms", slot_obj.due_at_ms),
                        canonical_symbol=slot_obj.canonical_symbol,
                        base_e_a_profile_id=slot_obj.base_e_a_profile_id,
                        profile_attestation_sha256=attest_sha,
                        request_identity=intent["request_identity"],
                        request_sequence=intent["request_sequence"],
                        raw_payload_persisted=False,
                    )
                    append_jsonl(self._observations_path, obs.to_dict())
                    self.observations.append(obs)
                    obs_sha = sha256_hex(canonical_json(obs.to_dict()).encode("utf-8"))
                    new_slots = sorted(chk_slot_ids + [obs.slot_id])
                    self.checkpoint = EventCheckpoint.create(
                        event_id=self.contract.event_id,
                        event_contract_sha256=self.checkpoint.event_contract_sha256,
                        profile_attestation_sha256_by_symbol_and_profile=self.checkpoint.profile_attestation_sha256_by_symbol_and_profile,
                        completed_slot_ids_ordered=new_slots,
                        last_observation_sha256=obs_sha,
                        accounted_root_bytes=self.checkpoint.accounted_root_bytes,
                        inflight_slot_intent=None,
                        updated_at_ms=intent.get("reserved_at_ms", slot_obj.due_at_ms),
                    )
                    write_atomic_json(self._checkpoint_path, self.checkpoint.to_dict())
                elif intent_stage == "raw_persisted":
                    raw_rel = intent.get("raw_relative_path")
                    raw_file = self.event_root / raw_rel if raw_rel else None
                    if (
                        raw_file
                        and raw_file.is_file()
                        and not raw_file.is_symlink()
                        and len(raw_file.read_bytes()) == intent.get("raw_byte_count")
                        and sha256_hex(raw_file.read_bytes()) == intent.get("raw_sha256")
                    ):
                        obs = MarketObservation.create_unknown_after_restart(
                            event_id=self.contract.event_id,
                            slot_id=intent_slot_id,
                            slot_family=slot_obj.slot_family,
                            slot_index=slot_obj.slot_index,
                            due_at_ms=slot_obj.due_at_ms,
                            completed_at_ms=intent.get("reserved_at_ms", slot_obj.due_at_ms),
                            canonical_symbol=slot_obj.canonical_symbol,
                            base_e_a_profile_id=slot_obj.base_e_a_profile_id,
                            profile_attestation_sha256=attest_sha,
                            request_identity=intent["request_identity"],
                            request_sequence=intent["request_sequence"],
                            raw_payload_persisted=True,
                            raw_sha256=intent["raw_sha256"],
                            raw_relative_path=intent["raw_relative_path"],
                            raw_byte_count=intent["raw_byte_count"],
                        )
                        append_jsonl(self._observations_path, obs.to_dict())
                        self.observations.append(obs)
                        obs_sha = sha256_hex(canonical_json(obs.to_dict()).encode("utf-8"))
                        new_slots = sorted(chk_slot_ids + [obs.slot_id])
                        self.checkpoint = EventCheckpoint.create(
                            event_id=self.contract.event_id,
                            event_contract_sha256=self.checkpoint.event_contract_sha256,
                            profile_attestation_sha256_by_symbol_and_profile=self.checkpoint.profile_attestation_sha256_by_symbol_and_profile,
                            completed_slot_ids_ordered=new_slots,
                            last_observation_sha256=obs_sha,
                            accounted_root_bytes=self.checkpoint.accounted_root_bytes,
                            inflight_slot_intent=None,
                            updated_at_ms=intent.get("reserved_at_ms", slot_obj.due_at_ms),
                        )
                        write_atomic_json(self._checkpoint_path, self.checkpoint.to_dict())
                    else:
                        self.write_failed_terminal("local_integrity_failed", intent.get("reserved_at_ms", slot_obj.due_at_ms))
                        raise Stage16EBStorageBlocked("local_integrity_failed")

    def step_slot(self, slot: ScheduledSlot, current_time_ms: int) -> MarketObservation:
        assert self.contract is not None
        assert self.checkpoint is not None

        if slot.slot_id in self.checkpoint.completed_slot_ids_ordered:
            existing = next(o for o in self.observations if o.slot_id == slot.slot_id)
            return existing

        attest_sha = self.profile_cores[f"{slot.canonical_symbol}:{slot.base_e_a_profile_id}"].profile_attestation_sha256

        # 1. Deadline check
        if current_time_ms >= slot.due_at_ms + base.EXTERNAL_SIGNAL_STAGE1_6E_B_SLOT_DEADLINE_MS:
            obs = MarketObservation.create_missed_deadline(
                event_id=self.contract.event_id,
                slot_id=slot.slot_id,
                slot_family=slot.slot_family,
                slot_index=slot.slot_index,
                due_at_ms=slot.due_at_ms,
                completed_at_ms=current_time_ms,
                canonical_symbol=slot.canonical_symbol,
                base_e_a_profile_id=slot.base_e_a_profile_id,
                profile_attestation_sha256=attest_sha,
                request_identity=slot.request_identity,
            )
            append_jsonl(self._observations_path, obs.to_dict())
            self.observations.append(obs)
            obs_sha = sha256_hex(canonical_json(obs.to_dict()).encode("utf-8"))
            new_completed = sorted(self.checkpoint.completed_slot_ids_ordered + [slot.slot_id])
            self.checkpoint = EventCheckpoint.create(
                event_id=self.contract.event_id,
                event_contract_sha256=self.checkpoint.event_contract_sha256,
                profile_attestation_sha256_by_symbol_and_profile=self.checkpoint.profile_attestation_sha256_by_symbol_and_profile,
                completed_slot_ids_ordered=new_completed,
                last_observation_sha256=obs_sha,
                accounted_root_bytes=self.checkpoint.accounted_root_bytes,
                inflight_slot_intent=None,
                updated_at_ms=current_time_ms,
            )
            write_atomic_json(self._checkpoint_path, self.checkpoint.to_dict())
            return obs

        # 2. Within deadline: prepare intent
        req_seq = self._next_request_seq
        self._next_request_seq += 1

        intent = SlotIntent.create(
            slot_id=slot.slot_id,
            request_identity=slot.request_identity,
            request_sequence=req_seq,
            base_e_a_profile_id=slot.base_e_a_profile_id,
            canonical_symbol=slot.canonical_symbol,
            due_at_ms=slot.due_at_ms,
            reserved_at_ms=current_time_ms,
            stage="prepared",
        )

        if self.guard is not None:
            self.guard.check_root_reserve_headroom(self.event_root, 10000, root_kind="event")

        self.checkpoint = EventCheckpoint.create(
            event_id=self.contract.event_id,
            event_contract_sha256=self.checkpoint.event_contract_sha256,
            profile_attestation_sha256_by_symbol_and_profile=self.checkpoint.profile_attestation_sha256_by_symbol_and_profile,
            completed_slot_ids_ordered=self.checkpoint.completed_slot_ids_ordered,
            last_observation_sha256=self.checkpoint.last_observation_sha256,
            accounted_root_bytes=self.checkpoint.accounted_root_bytes,
            inflight_slot_intent=intent.to_dict(),
            updated_at_ms=current_time_ms,
        )
        write_atomic_json(self._checkpoint_path, self.checkpoint.to_dict())

        # 3. HTTP Request
        profile = self.profile_cores[f"{slot.canonical_symbol}:{slot.base_e_a_profile_id}"]
        core = profile.http_profile_core
        fetch_res = self.client.fetch(core)
        dispatch_started_at_ms = current_time_ms
        completed_at_ms = current_time_ms + 50

        if fetch_res.outcome_kind != "response_verified" or fetch_res.raw_body is None:
            obs = MarketObservation(
                schema_version="stage1_6e_b_market_observation_v1",
                event_id=self.contract.event_id,
                slot_id=slot.slot_id,
                slot_family=slot.slot_family,
                slot_index=slot.slot_index,
                due_at_ms=slot.due_at_ms,
                dispatch_started_at_ms=dispatch_started_at_ms,
                completed_at_ms=completed_at_ms,
                canonical_symbol=slot.canonical_symbol,
                base_e_a_profile_id=slot.base_e_a_profile_id,
                profile_attestation_sha256=attest_sha,
                request_identity=slot.request_identity,
                request_sequence=req_seq,
                outcome_kind=fetch_res.outcome_kind,
                http_status=fetch_res.http_status,
                response_headers_subset=fetch_res.headers_subset,
                raw_payload_persisted=False,
                raw_sha256=None,
                raw_relative_path=None,
                raw_byte_count=None,
                schema_validation_status="not_applicable",
                time_validation_status="not_applicable",
                failure_reason=fetch_res.failure_reason,
                permissions=stage1_6e_b_permissions(),
            )
            append_jsonl(self._observations_path, obs.to_dict())
            self.observations.append(obs)
            obs_sha = sha256_hex(canonical_json(obs.to_dict()).encode("utf-8"))
            new_completed = sorted(self.checkpoint.completed_slot_ids_ordered + [slot.slot_id])
            self.checkpoint = EventCheckpoint.create(
                event_id=self.contract.event_id,
                event_contract_sha256=self.checkpoint.event_contract_sha256,
                profile_attestation_sha256_by_symbol_and_profile=self.checkpoint.profile_attestation_sha256_by_symbol_and_profile,
                completed_slot_ids_ordered=new_completed,
                last_observation_sha256=obs_sha,
                accounted_root_bytes=self.checkpoint.accounted_root_bytes,
                inflight_slot_intent=None,
                updated_at_ms=completed_at_ms,
            )
            write_atomic_json(self._checkpoint_path, self.checkpoint.to_dict())
            return obs

        # 4. Success response received: persist raw body
        raw_sha = sha256_hex(fetch_res.raw_body)
        raw_rel = f"raw/{raw_sha}.body"
        raw_file = self.event_root / raw_rel

        if self.guard is not None:
            self.guard.admitted_write(raw_file, fetch_res.raw_body, root_kind="event")
        else:
            write_atomic_bytes(raw_file, fetch_res.raw_body)

        raw_intent = SlotIntent.create(
            slot_id=slot.slot_id,
            request_identity=slot.request_identity,
            request_sequence=req_seq,
            base_e_a_profile_id=slot.base_e_a_profile_id,
            canonical_symbol=slot.canonical_symbol,
            due_at_ms=slot.due_at_ms,
            reserved_at_ms=current_time_ms,
            stage="raw_persisted",
            raw_sha256=raw_sha,
            raw_relative_path=raw_rel,
            raw_byte_count=len(fetch_res.raw_body),
        )
        self.checkpoint = EventCheckpoint.create(
            event_id=self.contract.event_id,
            event_contract_sha256=self.checkpoint.event_contract_sha256,
            profile_attestation_sha256_by_symbol_and_profile=self.checkpoint.profile_attestation_sha256_by_symbol_and_profile,
            completed_slot_ids_ordered=self.checkpoint.completed_slot_ids_ordered,
            last_observation_sha256=self.checkpoint.last_observation_sha256,
            accounted_root_bytes=self.checkpoint.accounted_root_bytes,
            inflight_slot_intent=raw_intent.to_dict(),
            updated_at_ms=current_time_ms,
        )
        write_atomic_json(self._checkpoint_path, self.checkpoint.to_dict())

        # 5. Schema & time validation
        try:
            parsed_json = json.loads(fetch_res.raw_body.decode("utf-8"))
            json_ok = True
        except Exception:
            json_ok = False
            parsed_json = None

        if not json_ok or parsed_json is None:
            outcome_kind = "schema_validation_failed"
            schema_status = "failed"
            time_status = "not_applicable"
            reason = "schema_validation_failed"
        else:
            ok_schema, _ = validate_event_response_schema(core["expected_response_schema"], parsed_json)
            if not ok_schema:
                outcome_kind = "schema_validation_failed"
                schema_status = "failed"
                time_status = "not_applicable"
                reason = "schema_validation_failed"
            else:
                ok_time, _ = validate_event_response_time(core.get("payload_time_semantics", {}), parsed_json)
                if not ok_time:
                    outcome_kind = "time_validation_failed"
                    schema_status = "verified"
                    time_status = "failed"
                    reason = "time_validation_failed"
                else:
                    outcome_kind = "response_verified"
                    schema_status = "verified"
                    time_status = "verified"
                    reason = None

        obs = MarketObservation(
            schema_version="stage1_6e_b_market_observation_v1",
            event_id=self.contract.event_id,
            slot_id=slot.slot_id,
            slot_family=slot.slot_family,
            slot_index=slot.slot_index,
            due_at_ms=slot.due_at_ms,
            dispatch_started_at_ms=dispatch_started_at_ms,
            completed_at_ms=completed_at_ms,
            canonical_symbol=slot.canonical_symbol,
            base_e_a_profile_id=slot.base_e_a_profile_id,
            profile_attestation_sha256=attest_sha,
            request_identity=slot.request_identity,
            request_sequence=req_seq,
            outcome_kind=outcome_kind,
            http_status=fetch_res.http_status,
            response_headers_subset=fetch_res.headers_subset,
            raw_payload_persisted=True,
            raw_sha256=raw_sha,
            raw_relative_path=raw_rel,
            raw_byte_count=len(fetch_res.raw_body),
            schema_validation_status=schema_status,
            time_validation_status=time_status,
            failure_reason=reason,
            permissions=stage1_6e_b_permissions(),
        )
        append_jsonl(self._observations_path, obs.to_dict())
        self.observations.append(obs)
        obs_sha = sha256_hex(canonical_json(obs.to_dict()).encode("utf-8"))
        new_completed = sorted(self.checkpoint.completed_slot_ids_ordered + [slot.slot_id])
        self.checkpoint = EventCheckpoint.create(
            event_id=self.contract.event_id,
            event_contract_sha256=self.checkpoint.event_contract_sha256,
            profile_attestation_sha256_by_symbol_and_profile=self.checkpoint.profile_attestation_sha256_by_symbol_and_profile,
            completed_slot_ids_ordered=new_completed,
            last_observation_sha256=obs_sha,
            accounted_root_bytes=self.checkpoint.accounted_root_bytes,
            inflight_slot_intent=None,
            updated_at_ms=completed_at_ms,
        )
        write_atomic_json(self._checkpoint_path, self.checkpoint.to_dict())
        return obs

    def finalize_terminal(self, current_time_ms: int) -> EventTerminalStatus:
        assert self.contract is not None
        assert self.checkpoint is not None

        if len(self.observations) != self.contract.expected_slot_count:
            raise Stage16EBStructuralError(f"cannot_finalize_terminal: observations {len(self.observations)} != expected {self.contract.expected_slot_count}")

        expected = self.contract.expected_slot_count
        durable = len(self.observations)
        successful = sum(1 for o in self.observations if o.outcome_kind == "response_verified")
        missed = sum(1 for o in self.observations if o.outcome_kind == "slot_missed_deadline")
        failed = durable - successful - missed

        coverage_status = "complete" if successful == expected else "incomplete"

        per_symbol_counts = []
        for sym in self.contract.canonical_symbols_ordered:
            sym_obs = [o for o in self.observations if o.canonical_symbol == sym]
            sym_succ = sum(1 for o in sym_obs if o.outcome_kind == "response_verified")
            sym_miss = sum(1 for o in sym_obs if o.outcome_kind == "slot_missed_deadline")
            sym_fail = len(sym_obs) - sym_succ - sym_miss
            per_symbol_counts.append({
                "canonical_symbol": sym,
                "expected_slot_count": 1586,
                "successful_slot_count": sym_succ,
                "failed_slot_count": sym_fail,
                "missed_slot_count": sym_miss,
            })

        term = EventTerminalStatus(
            schema_version="stage1_6e_b_terminal_status_v1",
            event_id=self.contract.event_id,
            status="complete",
            coverage_status=coverage_status,
            terminal_reason=None,
            event_window_started_at_ms=self.contract.event_window_started_at_ms,
            event_window_ends_at_ms=self.contract.event_window_ends_at_ms,
            terminal_at_ms=current_time_ms,
            expected_slot_count=expected,
            durable_slot_count=durable,
            successful_slot_count=successful,
            failed_slot_count=failed,
            missed_slot_count=missed,
            per_symbol_slot_counts=per_symbol_counts,
            accounted_root_bytes=self.checkpoint.accounted_root_bytes,
            permissions=stage1_6e_b_permissions(),
        )
        term_sha = write_atomic_json(self.event_root / "terminal_status.json", term.to_dict())

        # Write manifest
        contract_sha = sha256_hex((self.event_root / "event_contract.json").read_bytes())
        write_event_manifest(
            event_root=self.event_root,
            event_id=self.contract.event_id,
            coverage_status=coverage_status,
            event_contract_sha256=contract_sha,
            terminal_status_sha256=term_sha,
            guard=self.guard,
        )

        # Verify closed tree
        verify_event_closed_tree_manifest(self.event_root)
        return term

    def write_failed_terminal(self, reason: str, current_time_ms: int) -> EventTerminalStatus:
        if reason not in ("storage_write_blocked", "local_integrity_failed"):
            raise ValueError(f"invalid_terminal_failed_reason: {reason}")

        expected = self.contract.expected_slot_count if self.contract else 0
        durable = len(self.observations)
        successful = sum(1 for o in self.observations if o.outcome_kind == "response_verified")
        missed = sum(1 for o in self.observations if o.outcome_kind == "slot_missed_deadline")
        failed = durable - successful - missed

        per_symbol_counts = []
        if self.contract:
            for sym in self.contract.canonical_symbols_ordered:
                sym_obs = [o for o in self.observations if o.canonical_symbol == sym]
                sym_succ = sum(1 for o in sym_obs if o.outcome_kind == "response_verified")
                sym_miss = sum(1 for o in sym_obs if o.outcome_kind == "slot_missed_deadline")
                sym_fail = len(sym_obs) - sym_succ - sym_miss
                per_symbol_counts.append({
                    "canonical_symbol": sym,
                    "expected_slot_count": 1586,
                    "successful_slot_count": sym_succ,
                    "failed_slot_count": sym_fail,
                    "missed_slot_count": sym_miss,
                })

        term = EventTerminalStatus(
            schema_version="stage1_6e_b_terminal_status_v1",
            event_id=self.contract.event_id if self.contract else "0" * 64,
            status="failed",
            coverage_status=None,
            terminal_reason=reason,
            event_window_started_at_ms=self.contract.event_window_started_at_ms if self.contract else 0,
            event_window_ends_at_ms=self.contract.event_window_ends_at_ms if self.contract else 0,
            terminal_at_ms=current_time_ms,
            expected_slot_count=expected,
            durable_slot_count=durable,
            successful_slot_count=successful,
            failed_slot_count=failed,
            missed_slot_count=missed,
            per_symbol_slot_counts=per_symbol_counts,
            accounted_root_bytes=self.checkpoint.accounted_root_bytes if self.checkpoint else 0,
            permissions=stage1_6e_b_permissions(),
        )
        write_atomic_json(self.event_root / "terminal_status.json", term.to_dict())
        return term
