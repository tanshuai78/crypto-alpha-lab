"""Live observation and reducer state machine for Stage 1.6B."""

import datetime
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from configs import base
from src.research.external_signal_shadow.stage1_6b_canonical_source_client import (
    Stage16BCanonicalClient,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    CANDIDATE_DISCOVERY_RULE_VERSION,
    DETAIL_REQUEST_VARIANT,
    DETAIL_SOURCE_LOCALE,
    DETAIL_SOURCE_SURFACE,
    INDEX_REQUEST_VARIANT,
    INDEX_SOURCE_LOCALE,
    INDEX_SOURCE_SURFACE,
    SOURCE_PROFILE_ID,
    ArticleDiscoveryRecord,
    CandidateLane,
    CandidateState,
    CaptureMode,
    DetailObservationRecord,
    DetailRevisionRecord,
    ListCaptureRecord,
    ObserverCheckpointRecord,
    RequestClass,
    canonical_json,
    compute_detail_revision_id,
    compute_list_capture_id,
    compute_list_payload_id,
    compute_request_headers_profile_sha256,
    compute_request_observation_id,
    is_delisting_candidate,
    normalize_discovery_text,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import (
    Stage16BStorageGuard,
    append_jsonl_record,
    reconcile_and_load_checkpoint,
    write_content_addressed_raw_payload,
    write_observer_checkpoint,
)


class ObserverSLAError(RuntimeError):
    """Raised when Lane A first-attempt SLA is exceeded."""
    pass


class ObserverCapacityError(RuntimeError):
    """Raised when candidate capacity limit is exceeded."""
    pass


class Stage16BObserver:
    """Process-local live observer reducer managing single-poll execution, Lane A/B candidate scheduling, and checkpointing."""

    def __init__(
        self,
        run_root: Path,
        run_id: str,
        capture_mode: str,
        source_profile_attestation_sha256: str,
        guard: Stage16BStorageGuard,
        client: Stage16BCanonicalClient,
        recovered_checkpoint: Optional[ObserverCheckpointRecord] = None,
        recovered_root_bytes: Optional[int] = None,
    ):
        self.run_root = run_root.resolve()
        self.run_id = run_id
        self.capture_mode = capture_mode
        self.source_profile_attestation_sha256 = source_profile_attestation_sha256
        self.guard = guard
        self.client = client
        self.headers_profile_sha256 = compute_request_headers_profile_sha256()

        # A runner may provide a state it reconciled under the lifetime writer lock.
        if recovered_checkpoint is not None:
            if recovered_root_bytes is None:
                raise ValueError("recovered_root_bytes_required")
            chk, root_bytes = recovered_checkpoint, recovered_root_bytes
        else:
            chk_file = self.run_root / "observer_checkpoint.json"
            if chk_file.is_file():
                chk, root_bytes = reconcile_and_load_checkpoint(self.run_root, self.guard)
            else:
                chk, root_bytes = None, None

        if chk is not None:
            self.poll_seq = chk.poll_seq
            self.monotonic_request_seq = chk.monotonic_request_seq
            self.record_seq = chk.record_seq
            self.accounted_root_bytes = root_bytes
            self.stream_offsets = dict(chk.stream_offsets)
            self.stream_last_hashes = dict(chk.stream_last_hashes)
            self.candidate_states: Dict[str, CandidateState] = {
                k: CandidateState(**v) for k, v in chk.candidate_states.items()
            }
            self.prior_checkpoint_id: Optional[str] = chk.checkpoint_id
        else:
            self.poll_seq = 0
            self.monotonic_request_seq = 0
            self.record_seq = 0
            self.accounted_root_bytes = 0
            self.stream_offsets: Dict[str, int] = {}
            self.stream_last_hashes: Dict[str, str] = {}
            self.candidate_states: Dict[str, CandidateState] = {}
            self.prior_checkpoint_id = None

    def _append_record(self, relative_path: str, record: Dict[str, Any], write_class: str) -> int:
        """Append one durable row and immediately record its committed boundary."""
        delta = append_jsonl_record(
            run_root=self.run_root,
            relative_path=relative_path,
            record=record,
            write_class=write_class,
            guard=self.guard,
            current_root_bytes=self.accounted_root_bytes,
        )
        stream_path = self.run_root / relative_path
        self.stream_offsets[relative_path] = stream_path.stat().st_size
        self.stream_last_hashes[relative_path] = hashlib.sha256(
            canonical_json(record).encode("utf-8")
        ).hexdigest()
        return delta

    def execute_poll(self, now_ms: Optional[int] = None) -> ObserverCheckpointRecord:
        """Execute one deterministic observation poll."""
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        today_str = datetime.datetime.fromtimestamp(now_ms / 1000.0, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        self.poll_seq += 1

        # 1. Check Lane A SLA
        for aid, cand in self.candidate_states.items():
            if cand.lane == CandidateLane.LANE_A.value and cand.detail_attempt_count == 0 and cand.terminal_reason is None:
                if (self.poll_seq - cand.first_discovered_poll_seq) >= base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_FIRST_ATTEMPT_MAX_POLLS:
                    raise ObserverSLAError(
                        f"detail_first_attempt_sla_exceeded: candidate {aid} discovered at poll {cand.first_discovered_poll_seq}, current poll {self.poll_seq}"
                    )

        # 2. Fetch exactly one index page
        self.monotonic_request_seq += 1
        req_obs_id_idx = compute_request_observation_id(
            self.run_id,
            RequestClass.LIVE_INDEX.value,
            self.monotonic_request_seq,
        )
        res_idx = self.client.fetch_index_page(
            page_no=1,
            run_id=self.run_id,
            request_class=RequestClass.LIVE_INDEX.value,
            monotonic_request_seq=self.monotonic_request_seq,
        )

        idx_raw_sha = ""
        idx_rel_raw = ""
        if res_idx.trust_validation_status == "trusted" and res_idx.raw_payload:
            idx_raw_sha, idx_rel_raw, raw_b_written = write_content_addressed_raw_payload(
                run_root=self.run_root,
                payload_bytes=res_idx.raw_payload,
                subfolder="index",
                guard=self.guard,
                current_root_bytes=self.accounted_root_bytes,
            )
            self.accounted_root_bytes += raw_b_written
        else:
            idx_raw_sha = hashlib.sha256(res_idx.raw_payload).hexdigest() if res_idx.raw_payload else ""

        list_payload_id = compute_list_payload_id(
            source_surface=INDEX_SOURCE_SURFACE,
            source_locale=INDEX_SOURCE_LOCALE,
            request_variant=INDEX_REQUEST_VARIANT,
            raw_sha256=idx_raw_sha,
        )
        list_capture_id = compute_list_capture_id(
            source_profile_id=SOURCE_PROFILE_ID,
            canonical_requested_url=res_idx.requested_url,
            page_no=1,
            list_payload_id=list_payload_id,
            request_observation_id=req_obs_id_idx,
        )

        article_count = 0
        articles_list: List[Dict[str, Any]] = []
        if res_idx.trust_validation_status == "trusted":
            try:
                data = json.loads(res_idx.raw_payload.decode("utf-8"))
                articles_list = data.get("data", {}).get("articles", [])
                article_count = len(articles_list)
            except Exception:
                pass

        self.record_seq += 1
        list_cap_rec = ListCaptureRecord(
            schema_version="stage1_6b_list_capture_v1",
            capture_mode=self.capture_mode,
            source_profile_id=SOURCE_PROFILE_ID,
            request_headers_profile_sha256=self.headers_profile_sha256,
            run_id=self.run_id,
            poll_seq=self.poll_seq,
            record_seq=self.record_seq,
            request_observation_id=req_obs_id_idx,
            list_payload_id=list_payload_id,
            list_capture_id=list_capture_id,
            page_no=1,
            requested_url=res_idx.requested_url,
            final_url=res_idx.final_url,
            http_status=res_idx.http_status,
            content_type=res_idx.content_type,
            raw_payload_sha256=idx_raw_sha,
            raw_payload_bytes=res_idx.raw_payload_bytes,
            raw_payload_relative_path=idx_rel_raw,
            t_list_receive_ms=res_idx.t_receive_ms,
            article_count=article_count,
            captured_at_ms=now_ms,
        )
        delta_lc = self._append_record(
            f"list_captures/{today_str}.jsonl",
            list_cap_rec.to_dict(),
            "normal_data",
        )
        self.accounted_root_bytes += delta_lc

        # 3. Derive candidates from index payload
        if res_idx.trust_validation_status == "trusted":
            for item in articles_list:
                aid = str(item.get("code") or item.get("id") or "")
                title = str(item.get("title") or "")
                if not aid or not title:
                    continue

                norm_title = normalize_discovery_text(title)
                if is_delisting_candidate(norm_title):
                    if aid not in self.candidate_states:
                        self.record_seq += 1
                        disc_rec = ArticleDiscoveryRecord(
                            schema_version="stage1_6b_article_discovery_v1",
                            capture_mode=self.capture_mode,
                            source_profile_id=SOURCE_PROFILE_ID,
                            source_article_id=aid,
                            discovery_title=title,
                            discovery_rule_version=CANDIDATE_DISCOVERY_RULE_VERSION,
                            first_list_capture_id=list_capture_id,
                            notice_lineage_first_detected_at_ms=now_ms if self.capture_mode == CaptureMode.LIVE_OBSERVED.value else None,
                            captured_at_ms=now_ms,
                            record_seq=self.record_seq,
                        )
                        delta_disc = self._append_record(
                            "article_discoveries.jsonl",
                            disc_rec.to_dict(),
                            "normal_data",
                        )
                        self.accounted_root_bytes += delta_disc

                        self.candidate_states[aid] = CandidateState(
                            source_article_id=aid,
                            first_discovered_poll_seq=self.poll_seq,
                            first_discovered_at_ms=now_ms,
                            lane=CandidateLane.LANE_A.value,
                            detail_attempt_count=0,
                            retry_cycle_count=0,
                            first_attempt_at_ms=None,
                            last_attempt_at_ms=None,
                            next_retry_at_ms=None,
                            terminal_reason=None,
                            trusted_detail_revision_id=None,
                        )

        # 4. Detail candidate selection
        lane_a = [
            c for c in self.candidate_states.values()
            if c.lane == CandidateLane.LANE_A.value and c.detail_attempt_count == 0 and c.terminal_reason is None
        ]
        lane_a.sort(key=lambda c: (c.first_discovered_poll_seq, c.source_article_id))

        selected: Optional[CandidateState] = None
        if lane_a:
            selected = lane_a[0]
        else:
            lane_b = [
                c for c in self.candidate_states.values()
                if c.lane == CandidateLane.LANE_B.value and c.terminal_reason is None and (c.next_retry_at_ms is not None and c.next_retry_at_ms <= now_ms)
            ]
            lane_b.sort(key=lambda c: (c.next_retry_at_ms or 0, c.first_discovered_poll_seq, c.source_article_id))
            if lane_b:
                selected = lane_b[0]

        # 5. Execute detail fetch if candidate selected
        if selected is not None:
            self.monotonic_request_seq += 1
            req_obs_id_det = compute_request_observation_id(
                self.run_id,
                RequestClass.LIVE_DETAIL.value,
                self.monotonic_request_seq,
            )
            res_det = self.client.fetch_article_detail(
                article_code=selected.source_article_id,
                run_id=self.run_id,
                request_class=RequestClass.LIVE_DETAIL.value,
                monotonic_request_seq=self.monotonic_request_seq,
            )

            det_raw_sha = ""
            det_rel_raw = ""
            if res_det.trust_validation_status == "trusted" and res_det.raw_payload:
                det_raw_sha, det_rel_raw, det_b_written = write_content_addressed_raw_payload(
                    run_root=self.run_root,
                    payload_bytes=res_det.raw_payload,
                    subfolder=f"detail/{selected.source_article_id}",
                    guard=self.guard,
                    current_root_bytes=self.accounted_root_bytes,
                )
                self.accounted_root_bytes += det_b_written
            else:
                det_raw_sha = hashlib.sha256(res_det.raw_payload).hexdigest() if res_det.raw_payload else ""

            self.record_seq += 1
            det_obs_rec = DetailObservationRecord(
                schema_version="stage1_6b_detail_observation_v1",
                capture_mode=self.capture_mode,
                source_profile_id=SOURCE_PROFILE_ID,
                request_headers_profile_sha256=self.headers_profile_sha256,
                run_id=self.run_id,
                poll_seq=self.poll_seq,
                record_seq=self.record_seq,
                request_observation_id=req_obs_id_det,
                source_article_id=selected.source_article_id,
                request_variant=DETAIL_REQUEST_VARIANT,
                requested_url=res_det.requested_url,
                final_url=res_det.final_url,
                http_status=res_det.http_status,
                content_type=res_det.content_type,
                raw_payload_sha256=det_raw_sha or None,
                raw_payload_bytes=res_det.raw_payload_bytes if res_det.raw_payload_bytes > 0 else None,
                raw_payload_relative_path=det_rel_raw or None,
                trust_validation_status=res_det.trust_validation_status,
                t_detail_receive_ms=res_det.t_receive_ms,
                captured_at_ms=now_ms,
            )
            delta_do = self._append_record(
                f"detail_observations/{today_str}.jsonl",
                det_obs_rec.to_dict(),
                "normal_data",
            )
            self.accounted_root_bytes += delta_do

            if res_det.trust_validation_status == "trusted":
                rev_id = compute_detail_revision_id(
                    source_article_id=selected.source_article_id,
                    source_surface=DETAIL_SOURCE_SURFACE,
                    source_locale=DETAIL_SOURCE_LOCALE,
                    request_variant=DETAIL_REQUEST_VARIANT,
                    detail_raw_sha256=det_raw_sha,
                )
                self.record_seq += 1
                rev_rec = DetailRevisionRecord(
                    schema_version="stage1_6b_detail_revision_v1",
                    capture_mode=self.capture_mode,
                    source_profile_id=SOURCE_PROFILE_ID,
                    source_article_id=selected.source_article_id,
                    source_surface=DETAIL_SOURCE_SURFACE,
                    source_locale=DETAIL_SOURCE_LOCALE,
                    request_variant=DETAIL_REQUEST_VARIANT,
                    detail_revision_id=rev_id,
                    detail_raw_sha256=det_raw_sha,
                    raw_payload_relative_path=det_rel_raw,
                    t_detail_trusted_ms=res_det.t_receive_ms,
                    t_raw_persisted_ms=now_ms,
                    captured_at_ms=now_ms,
                    record_seq=self.record_seq,
                )
                delta_rev = self._append_record(
                    "detail_revisions.jsonl",
                    rev_rec.to_dict(),
                    "normal_data",
                )
                self.accounted_root_bytes += delta_rev

                self.candidate_states[selected.source_article_id] = CandidateState(
                    source_article_id=selected.source_article_id,
                    first_discovered_poll_seq=selected.first_discovered_poll_seq,
                    first_discovered_at_ms=selected.first_discovered_at_ms,
                    lane=selected.lane,
                    detail_attempt_count=selected.detail_attempt_count + 1,
                    retry_cycle_count=selected.retry_cycle_count,
                    first_attempt_at_ms=selected.first_attempt_at_ms or now_ms,
                    last_attempt_at_ms=now_ms,
                    next_retry_at_ms=None,
                    terminal_reason="trusted_detail_observed",
                    trusted_detail_revision_id=rev_id,
                )
            else:
                new_retry_cycles = selected.retry_cycle_count + 1
                age_ms = now_ms - selected.first_discovered_at_ms
                if new_retry_cycles >= base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MAX_CYCLES or age_ms >= (base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MAX_AGE_SEC * 1000):
                    term_reason = "terminal_detail_failure"
                    next_retry = None
                else:
                    term_reason = None
                    interval_sec = min(
                        base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MAX_INTERVAL_SEC,
                        base.EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_RETRY_MIN_INTERVAL_SEC * (2 ** (new_retry_cycles - 1)),
                    )
                    next_retry = now_ms + int(interval_sec * 1000)

                self.candidate_states[selected.source_article_id] = CandidateState(
                    source_article_id=selected.source_article_id,
                    first_discovered_poll_seq=selected.first_discovered_poll_seq,
                    first_discovered_at_ms=selected.first_discovered_at_ms,
                    lane=CandidateLane.LANE_B.value,
                    detail_attempt_count=selected.detail_attempt_count + 1,
                    retry_cycle_count=new_retry_cycles,
                    first_attempt_at_ms=selected.first_attempt_at_ms or now_ms,
                    last_attempt_at_ms=now_ms,
                    next_retry_at_ms=next_retry,
                    terminal_reason=term_reason,
                    trusted_detail_revision_id=None,
                )

        # 6. Check pending candidate capacity
        non_terminal_count = sum(1 for c in self.candidate_states.values() if c.terminal_reason is None)
        if non_terminal_count > base.EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES:
            raise ObserverCapacityError(
                f"max_pending_detail_candidates_exceeded: {non_terminal_count} > {base.EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES}"
            )

        # 7. Append heartbeat
        heartbeat_rec = {
            "poll_seq": self.poll_seq,
            "monotonic_request_seq": self.monotonic_request_seq,
            "accounted_root_bytes": self.accounted_root_bytes,
            "heartbeat_at_ms": now_ms,
        }
        delta_hb = self._append_record(
            f"observer_heartbeats/{today_str}.jsonl",
            heartbeat_rec,
            "ordinary_control_plane",
        )
        self.accounted_root_bytes += delta_hb

        # 8. Checkpoint
        chk_seed = f"{self.run_id}|{self.poll_seq}|{self.monotonic_request_seq}|{self.record_seq}|{self.accounted_root_bytes}"
        checkpoint_id = hashlib.sha256(chk_seed.encode("utf-8")).hexdigest()

        chk_rec = ObserverCheckpointRecord(
            schema_version="stage1_6b_observer_checkpoint_v1",
            run_id=self.run_id,
            capture_mode=self.capture_mode,
            source_profile_id=SOURCE_PROFILE_ID,
            source_profile_attestation_sha256=self.source_profile_attestation_sha256,
            checkpoint_id=checkpoint_id,
            prior_checkpoint_id=self.prior_checkpoint_id,
            poll_seq=self.poll_seq,
            monotonic_request_seq=self.monotonic_request_seq,
            record_seq=self.record_seq,
            accounted_root_bytes=self.accounted_root_bytes,
            stream_offsets=self.stream_offsets,
            stream_last_hashes=self.stream_last_hashes,
            candidate_states={k: v.to_dict() for k, v in self.candidate_states.items()},
            heartbeat_at_ms=now_ms,
        )

        delta_chk = write_observer_checkpoint(
            run_root=self.run_root,
            checkpoint=chk_rec,
            guard=self.guard,
            current_root_bytes=self.accounted_root_bytes,
        )
        self.accounted_root_bytes += delta_chk
        self.prior_checkpoint_id = checkpoint_id

        return chk_rec
