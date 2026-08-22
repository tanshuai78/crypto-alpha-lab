"""Historical backfill runner for Stage 1.6B."""

import argparse
import datetime
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from configs import base
from src.research.external_signal_shadow.stage1_6b_canonical_source_client import (
    Stage16BCanonicalClient,
    extract_selected_delisting_catalog,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    CANDIDATE_DISCOVERY_RULE_VERSION,
    DETAIL_REQUEST_VARIANT,
    DETAIL_SOURCE_LOCALE,
    DETAIL_SOURCE_SURFACE,
    INDEX_REQUEST_VARIANT,
    INDEX_SOURCE_LOCALE,
    INDEX_SOURCE_SURFACE,
    SELECTED_CATALOG_ID,
    SELECTED_CATALOG_NAME,
    SOURCE_PROFILE_ID,
    ArticleDiscoveryRecord,
    CaptureMode,
    CaptureRunContract,
    DetailObservationRecord,
    DetailRevisionRecord,
    HistoricalCoverageRecord,
    ListCaptureRecord,
    ObserverCheckpointRecord,
    RequestClass,
    TerminalStatusRecord,
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
    copy_probe_attestation_to_root,
    historical_coverage_is_complete,
    seal_export,
    validate_probe_attestation_path,
    validate_run_root_path,
    write_capture_run_contract,
    write_content_addressed_raw_payload,
    write_historical_coverage,
    write_observer_checkpoint,
    write_terminal_status,
)


class HistoricalBackfillError(RuntimeError):
    """Raised when historical backfill encounters an unrecoverable failure."""
    pass


def run_historical_backfill(
    from_ms: int,
    to_ms: int,
    attestation_path: Path,
    live_public_readonly: bool,
    project_root: Optional[Path] = None,
    run_id: Optional[str] = None,
    opener: Optional[Callable[..., Any]] = None,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic_clock: Callable[[], float] = time.monotonic,
) -> Path:
    """Execute two-sweep historical backfill and produce sealed-export eligible root."""
    if not live_public_readonly:
        raise ValueError("live_public_readonly_required: must explicitly supply --live-public-readonly")

    if from_ms >= to_ms:
        raise ValueError(f"invalid_time_range: from_ms ({from_ms}) must be < to_ms ({to_ms})")

    max_span_ms = 730 * 24 * 3600 * 1000
    if (to_ms - from_ms) > max_span_ms:
        raise ValueError(f"range_exceeds_730_days: span {to_ms - from_ms} > {max_span_ms}")

    p_root = (project_root or Path.cwd()).resolve()
    run_started_at_ms = int(time.time() * 1000)

    # 1. Attestation verification
    validated_att_path = validate_probe_attestation_path(attestation_path, project_root=p_root)
    att_data = json.loads(validated_att_path.read_text(encoding="utf-8"))

    if att_data.get("schema_version") != "stage1_6b_source_profile_probe_attestation_v2":
        raise ValueError(f"attestation_schema_mismatch: {att_data.get('schema_version')}")

    if att_data.get("source_profile_id") != SOURCE_PROFILE_ID:
        raise ValueError(f"attestation_profile_mismatch: {att_data.get('source_profile_id')} != {SOURCE_PROFILE_ID}")

    expected_headers_sha = compute_request_headers_profile_sha256()
    if att_data.get("request_headers_profile_sha256") != expected_headers_sha:
        raise ValueError("attestation_headers_sha_mismatch")

    if att_data.get("probe_attested_at_ms", 0) > run_started_at_ms:
        raise ValueError("probe_attested_in_future")

    att_sha256 = hashlib.sha256(validated_att_path.read_bytes()).hexdigest()

    # 2. Output root validation & setup
    effective_run_id = run_id or f"hist_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    run_root = p_root / "data" / "external_signal_shadow" / "stage1_6b" / "historical_backfill" / effective_run_id
    validated_root = validate_run_root_path(run_root, capture_mode=CaptureMode.HISTORICAL_BACKFILL.value, require_fresh=True, project_root=p_root)
    validated_root.mkdir(parents=True, exist_ok=False)

    guard = Stage16BStorageGuard(output_root=validated_root)
    guard.validate_startup_free_space()

    root_bytes = 0
    contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id=effective_run_id,
        capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256=att_sha256,
        run_started_at_ms=run_started_at_ms,
    )
    root_bytes += write_capture_run_contract(validated_root, contract, guard, root_bytes)
    root_bytes += copy_probe_attestation_to_root(validated_root, validated_att_path, guard, root_bytes)

    client = Stage16BCanonicalClient(live_public_readonly=True, opener=opener)

    monotonic_request_seq = 0
    record_seq = 0
    last_request_at: Optional[float] = None
    all_discovered_articles: Dict[str, Dict[str, Any]] = {}
    page_failures: List[Dict[str, Any]] = []

    def _admit_next_request() -> None:
        """Keep historical backfill sequential and at least one second apart."""
        nonlocal last_request_at
        if last_request_at is not None:
            remaining = base.EXTERNAL_SIGNAL_STAGE1_6B_HISTORICAL_REQUEST_INTERVAL_SEC - (monotonic_clock() - last_request_at)
            if remaining > 0:
                sleeper(remaining)
        last_request_at = monotonic_clock()

    def _append_index_request_manifest(request_observation_id: str, page_no: int, result: Any) -> None:
        """Persist the one authoritative record for each historical index attempt."""
        nonlocal root_bytes
        row = {
            "schema_version": "stage1_6b_request_manifest_v1",
            "request_observation_id": request_observation_id,
            "run_id": effective_run_id,
            "poll_seq": 0,
            "monotonic_request_seq": monotonic_request_seq,
            "request_class": RequestClass.HISTORICAL_INDEX.value,
            "page_no": page_no,
            "requested_url": result.requested_url,
            "final_url": result.final_url,
            "http_status": result.http_status,
            "content_type": result.content_type,
            "raw_payload_bytes": result.raw_payload_bytes,
            "validation_status": result.trust_validation_status,
            "error_message": result.error_message,
            "captured_at_ms": result.t_receive_ms,
        }
        root_bytes += append_jsonl_record(
            run_root=validated_root,
            relative_path="request_manifest/historical.jsonl",
            record=row,
            write_class="normal_data",
            guard=guard,
            current_root_bytes=root_bytes,
        )

    def _write_final_checkpoint(status: str, coverage: str) -> str:
        """Commit the historical index manifest boundary before terminal status."""
        nonlocal root_bytes
        manifest_rel = "request_manifest/historical.jsonl"
        manifest_path = validated_root / manifest_rel
        stream_offsets: Dict[str, int] = {}
        stream_last_hashes: Dict[str, str] = {}
        if manifest_path.is_file():
            lines = manifest_path.read_bytes().splitlines()
            if lines:
                stream_offsets[manifest_rel] = manifest_path.stat().st_size
                stream_last_hashes[manifest_rel] = hashlib.sha256(lines[-1]).hexdigest()

        chk_seed = f"{effective_run_id}|0|{monotonic_request_seq}|{record_seq}|{root_bytes}"
        checkpoint_id = hashlib.sha256(chk_seed.encode("utf-8")).hexdigest()
        checkpoint = ObserverCheckpointRecord(
            schema_version="stage1_6b_observer_checkpoint_v2",
            run_id=effective_run_id,
            capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
            source_profile_id=SOURCE_PROFILE_ID,
            source_profile_attestation_sha256=att_sha256,
            checkpoint_id=checkpoint_id,
            prior_checkpoint_id=None,
            poll_seq=0,
            monotonic_request_seq=monotonic_request_seq,
            record_seq=record_seq,
            accounted_root_bytes=root_bytes,
            stream_offsets=stream_offsets,
            stream_last_hashes=stream_last_hashes,
            candidate_states={},
            heartbeat_at_ms=int(time.time() * 1000),
            last_index_poll_status=status,
            last_index_poll_coverage=coverage,
        )
        root_bytes += write_observer_checkpoint(validated_root, checkpoint, guard, root_bytes)
        return checkpoint_id

    def _execute_sweep(sweep_name: str) -> Tuple[List[Tuple[int, int, str, int]], bool, List[int]]:
        nonlocal monotonic_request_seq, record_seq, root_bytes
        transcript: List[Tuple[int, int, str, int]] = []
        seen_articles_in_sweep = set()
        reached_from = False
        sweep_totals: List[int] = []

        for page_no in range(1, base.EXTERNAL_SIGNAL_STAGE1_6B_HISTORICAL_MAX_INDEX_PAGES + 1):
            monotonic_request_seq += 1
            _admit_next_request()
            res = client.fetch_index_page(
                page_no=page_no,
                run_id=effective_run_id,
                request_class=RequestClass.HISTORICAL_INDEX.value,
                monotonic_request_seq=monotonic_request_seq,
            )

            req_obs_id = compute_request_observation_id(
                effective_run_id,
                RequestClass.HISTORICAL_INDEX.value,
                monotonic_request_seq,
            )
            _append_index_request_manifest(req_obs_id, page_no, res)

            if res.trust_validation_status != "trusted" or res.http_status != 200:
                page_failures.append({
                    "sweep": sweep_name,
                    "page_no": page_no,
                    "status": res.http_status,
                    "validation": res.trust_validation_status,
                    "error": res.error_message,
                })
                return transcript, False, sweep_totals

            catalog_res = extract_selected_delisting_catalog(res.raw_payload)
            articles = catalog_res.articles
            catalog_total = catalog_res.catalog_total
            sweep_totals.append(catalog_total)

            # Persist raw payload and list capture record
            raw_sha, rel_raw, b_written = write_content_addressed_raw_payload(
                run_root=validated_root,
                payload_bytes=res.raw_payload,
                subfolder="index",
                guard=guard,
                current_root_bytes=root_bytes,
            )
            root_bytes += b_written

            list_payload_id = compute_list_payload_id(
                INDEX_SOURCE_SURFACE,
                INDEX_SOURCE_LOCALE,
                INDEX_REQUEST_VARIANT,
                raw_sha,
            )
            list_cap_id = compute_list_capture_id(
                SOURCE_PROFILE_ID,
                res.requested_url,
                page_no,
                list_payload_id,
                req_obs_id,
            )

            record_seq += 1
            lc_rec = ListCaptureRecord(
                schema_version="stage1_6b_list_capture_v2",
                capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
                source_profile_id=SOURCE_PROFILE_ID,
                request_headers_profile_sha256=expected_headers_sha,
                run_id=effective_run_id,
                poll_seq=0,
                record_seq=record_seq,
                request_observation_id=req_obs_id,
                list_payload_id=list_payload_id,
                list_capture_id=list_cap_id,
                page_no=page_no,
                requested_url=res.requested_url,
                final_url=res.final_url,
                http_status=res.http_status,
                content_type=res.content_type,
                raw_payload_sha256=raw_sha,
                raw_payload_bytes=res.raw_payload_bytes,
                raw_payload_relative_path=rel_raw,
                t_list_receive_ms=res.t_receive_ms,
                article_count=len(articles),
                captured_at_ms=res.t_receive_ms,
                selected_catalog_id=SELECTED_CATALOG_ID,
                selected_catalog_name=SELECTED_CATALOG_NAME,
                selected_catalog_total=catalog_total,
            )
            delta_lc = append_jsonl_record(
                run_root=validated_root,
                relative_path=f"list_captures/{sweep_name}.jsonl",
                record=lc_rec.to_dict(),
                write_class="normal_data",
                guard=guard,
                current_root_bytes=root_bytes,
            )
            root_bytes += delta_lc

            for art in articles:
                aid = str(art.get("code") or art.get("id") or "")
                pub_time = int(art.get("releaseDate") or 0)
                title = str(art.get("title") or "")

                if aid in seen_articles_in_sweep:
                    # Duplicate article in sweep -> failure
                    page_failures.append({"sweep": sweep_name, "error": f"duplicate_article:{aid}"})
                    return transcript, False, sweep_totals

                seen_articles_in_sweep.add(aid)
                transcript.append((page_no, SELECTED_CATALOG_ID, aid, pub_time))

                if sweep_name == "sweep_a":
                    all_discovered_articles[aid] = {
                        "article": art,
                        "list_capture_id": list_cap_id,
                        "title": title,
                    }

                if pub_time <= from_ms:
                    reached_from = True

            if reached_from:
                break

            if page_no == base.EXTERNAL_SIGNAL_STAGE1_6B_HISTORICAL_MAX_INDEX_PAGES and not reached_from:
                # 100 pages reached without reaching from_ms
                return transcript, False, sweep_totals

        return transcript, reached_from, sweep_totals

    # 3. Sweep A
    transcript_a, sweep_a_ok, sweep_a_totals = _execute_sweep("sweep_a")
    if not sweep_a_ok or page_failures:
        is_drift = any(f.get("validation") == "malformed_index_schema" for f in page_failures)
        reason = "source_profile_schema_drift" if is_drift else "sweep_a_failed"
        cov = HistoricalCoverageRecord(
            schema_version="stage1_6b_historical_coverage_v2",
            run_id=effective_run_id,
            source_profile_id=SOURCE_PROFILE_ID,
            source_profile_attestation_sha256=att_sha256,
            from_ms=from_ms,
            to_ms=to_ms,
            sweep_a_transcript=transcript_a,
            sweep_b_transcript=[],
            page_failures=page_failures,
            candidate_terminal_counts={},
            status="failure",
            failure_reason=reason,
            captured_at_ms=int(time.time() * 1000),
            selected_catalog_id=SELECTED_CATALOG_ID,
            selected_catalog_name=SELECTED_CATALOG_NAME,
            selected_catalog_total_historical_max=max(sweep_a_totals) if sweep_a_totals else 0,
            selected_catalog_total_sweep_a_final=sweep_a_totals[-1] if sweep_a_totals else 0,
            selected_catalog_total_sweep_b_final=0,
        )
        root_bytes += write_historical_coverage(validated_root, cov, guard, root_bytes)
        checkpoint_status = page_failures[0].get("validation", "http_error") if page_failures else "http_error"
        final_checkpoint_id = _write_final_checkpoint(checkpoint_status, "degraded_not_successful")
        term = TerminalStatusRecord(
            schema_version="stage1_6b_terminal_status_v1",
            run_id=effective_run_id,
            capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
            source_profile_id=SOURCE_PROFILE_ID,
            status="failure",
            terminal_reason=reason,
            final_checkpoint_id=final_checkpoint_id,
            terminated_at_ms=int(time.time() * 1000),
        )
        write_terminal_status(validated_root, term, guard, root_bytes)
        if is_drift:
            raise HistoricalBackfillError("source_profile_schema_drift")
        return validated_root

    # 4. Sweep B
    transcript_b, sweep_b_ok, sweep_b_totals = _execute_sweep("sweep_b")
    all_totals = sweep_a_totals + sweep_b_totals
    hist_max = max(all_totals) if all_totals else 0
    sw_a_final = sweep_a_totals[-1] if sweep_a_totals else 0
    sw_b_final = sweep_b_totals[-1] if sweep_b_totals else 0

    if not sweep_b_ok or transcript_a != transcript_b:
        is_drift = any(f.get("validation") == "malformed_index_schema" for f in page_failures)
        reason = "source_profile_schema_drift" if is_drift else "sweep_b_mismatch"
        cov = HistoricalCoverageRecord(
            schema_version="stage1_6b_historical_coverage_v2",
            run_id=effective_run_id,
            source_profile_id=SOURCE_PROFILE_ID,
            source_profile_attestation_sha256=att_sha256,
            from_ms=from_ms,
            to_ms=to_ms,
            sweep_a_transcript=transcript_a,
            sweep_b_transcript=transcript_b,
            page_failures=page_failures or [{"error": "sweep_mismatch"}],
            candidate_terminal_counts={},
            status="failure",
            failure_reason=reason,
            captured_at_ms=int(time.time() * 1000),
            selected_catalog_id=SELECTED_CATALOG_ID,
            selected_catalog_name=SELECTED_CATALOG_NAME,
            selected_catalog_total_historical_max=hist_max,
            selected_catalog_total_sweep_a_final=sw_a_final,
            selected_catalog_total_sweep_b_final=sw_b_final,
        )
        root_bytes += write_historical_coverage(validated_root, cov, guard, root_bytes)
        checkpoint_status = page_failures[0].get("validation", "http_error") if page_failures else "http_error"
        final_checkpoint_id = _write_final_checkpoint(checkpoint_status, "degraded_not_successful")
        term = TerminalStatusRecord(
            schema_version="stage1_6b_terminal_status_v1",
            run_id=effective_run_id,
            capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
            source_profile_id=SOURCE_PROFILE_ID,
            status="failure",
            terminal_reason=reason,
            final_checkpoint_id=final_checkpoint_id,
            terminated_at_ms=int(time.time() * 1000),
        )
        write_terminal_status(validated_root, term, guard, root_bytes)
        if is_drift:
            raise HistoricalBackfillError("source_profile_schema_drift")
        return validated_root

    # 5. Candidate Extraction & Detail Fetches
    delisting_candidates = []
    for aid, item in all_discovered_articles.items():
        title = item["title"]
        if is_delisting_candidate(normalize_discovery_text(title)):
            delisting_candidates.append((aid, item))

            record_seq += 1
            now_art_ms = int(time.time() * 1000)
            disc_rec = ArticleDiscoveryRecord(
                schema_version="stage1_6b_article_discovery_v2",
                capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
                source_profile_id=SOURCE_PROFILE_ID,
                source_article_id=aid,
                discovery_title=title,
                discovery_rule_version=CANDIDATE_DISCOVERY_RULE_VERSION,
                first_list_capture_id=item["list_capture_id"],
                notice_lineage_first_detected_at_ms=None,  # Null for historical backfill
                captured_at_ms=now_art_ms,
                record_seq=record_seq,
                source_catalog_id=SELECTED_CATALOG_ID,
                source_catalog_name=SELECTED_CATALOG_NAME,
            )
            delta_d = append_jsonl_record(
                run_root=validated_root,
                relative_path="article_discoveries.jsonl",
                record=disc_rec.to_dict(),
                write_class="normal_data",
                guard=guard,
                current_root_bytes=root_bytes,
            )
            root_bytes += delta_d

    terminal_counts: Dict[str, int] = {"trusted_detail_observed": 0, "terminal_detail_failure": 0}

    if len(delisting_candidates) > base.EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES:
        cov = HistoricalCoverageRecord(
            schema_version="stage1_6b_historical_coverage_v2",
            run_id=effective_run_id,
            source_profile_id=SOURCE_PROFILE_ID,
            source_profile_attestation_sha256=att_sha256,
            from_ms=from_ms,
            to_ms=to_ms,
            sweep_a_transcript=transcript_a,
            sweep_b_transcript=transcript_b,
            page_failures=[],
            candidate_terminal_counts=terminal_counts,
            status="incomplete_candidate_capacity",
            captured_at_ms=int(time.time() * 1000),
            sweep_a={"reached_from_ms": sweep_a_ok, "page_failures": [], "transcript_hash": hashlib.sha256(json.dumps(transcript_a, separators=(",", ":")).encode("utf-8")).hexdigest()},
            sweep_b={"reached_from_ms": sweep_b_ok, "page_failures": [], "transcript_hash": hashlib.sha256(json.dumps(transcript_b, separators=(",", ":")).encode("utf-8")).hexdigest()},
            frozen_candidate_count=len(delisting_candidates),
            candidate_terminal_count=0,
            pending_candidate_count=len(delisting_candidates),
            unattempted_candidate_count=len(delisting_candidates),
            final_checkpoint_valid=False,
            selected_catalog_id=SELECTED_CATALOG_ID,
            selected_catalog_name=SELECTED_CATALOG_NAME,
            selected_catalog_total_historical_max=hist_max,
            selected_catalog_total_sweep_a_final=sw_a_final,
            selected_catalog_total_sweep_b_final=sw_b_final,
        )
        root_bytes += write_historical_coverage(validated_root, cov, guard, root_bytes)
        failure = TerminalStatusRecord(
            schema_version="stage1_6b_terminal_status_v1",
            run_id=effective_run_id,
            capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
            source_profile_id=SOURCE_PROFILE_ID,
            status="failure",
            terminal_reason="historical_candidate_capacity_incomplete",
            final_checkpoint_id=None,
            terminated_at_ms=int(time.time() * 1000),
        )
        write_terminal_status(validated_root, failure, guard, root_bytes)
        return validated_root

    for detail_cycle, (aid, item) in enumerate(delisting_candidates, start=1):
        monotonic_request_seq += 1
        _admit_next_request()
        res_det = client.fetch_article_detail(
            article_code=aid,
            run_id=effective_run_id,
            request_class=RequestClass.HISTORICAL_DETAIL.value,
            monotonic_request_seq=monotonic_request_seq,
        )

        det_raw_sha = ""
        det_rel_raw = ""
        if res_det.trust_validation_status == "trusted" and res_det.raw_payload:
            det_raw_sha, det_rel_raw, det_b_written = write_content_addressed_raw_payload(
                run_root=validated_root,
                payload_bytes=res_det.raw_payload,
                subfolder=f"detail/{aid}",
                guard=guard,
                current_root_bytes=root_bytes,
            )
            root_bytes += det_b_written
            terminal_counts["trusted_detail_observed"] += 1
        else:
            terminal_counts["terminal_detail_failure"] += 1

        req_obs_id_det = compute_request_observation_id(
            effective_run_id,
            RequestClass.HISTORICAL_DETAIL.value,
            monotonic_request_seq,
        )

        record_seq += 1
        now_det_ms = int(time.time() * 1000)
        det_obs = DetailObservationRecord(
            schema_version="stage1_6b_detail_observation_v1",
            capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
            source_profile_id=SOURCE_PROFILE_ID,
            request_headers_profile_sha256=expected_headers_sha,
            run_id=effective_run_id,
            poll_seq=detail_cycle,
            record_seq=record_seq,
            request_observation_id=req_obs_id_det,
            source_article_id=aid,
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
            captured_at_ms=now_det_ms,
        )
        delta_do = append_jsonl_record(
            run_root=validated_root,
            relative_path="detail_observations/historical.jsonl",
            record=det_obs.to_dict(),
            write_class="normal_data",
            guard=guard,
            current_root_bytes=root_bytes,
        )
        root_bytes += delta_do

        if res_det.trust_validation_status == "trusted":
            rev_id = compute_detail_revision_id(
                aid,
                DETAIL_SOURCE_SURFACE,
                DETAIL_SOURCE_LOCALE,
                DETAIL_REQUEST_VARIANT,
                det_raw_sha,
            )
            record_seq += 1
            rev_rec = DetailRevisionRecord(
                schema_version="stage1_6b_detail_revision_v1",
                capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
                source_profile_id=SOURCE_PROFILE_ID,
                source_article_id=aid,
                source_surface=DETAIL_SOURCE_SURFACE,
                source_locale=DETAIL_SOURCE_LOCALE,
                request_variant=DETAIL_REQUEST_VARIANT,
                detail_revision_id=rev_id,
                detail_raw_sha256=det_raw_sha,
                raw_payload_relative_path=det_rel_raw,
                t_detail_trusted_ms=res_det.t_receive_ms,
                t_raw_persisted_ms=now_det_ms,
                captured_at_ms=now_det_ms,
                record_seq=record_seq,
            )
            delta_rev = append_jsonl_record(
                run_root=validated_root,
                relative_path="detail_revisions.jsonl",
                record=rev_rec.to_dict(),
                write_class="normal_data",
                guard=guard,
                current_root_bytes=root_bytes,
            )
            root_bytes += delta_rev

    # 6. Final Checkpoint and Terminal Status
    final_chk_id = _write_final_checkpoint("trusted", "successful")

    # 7. Coverage
    transcript_a_hash = hashlib.sha256(json.dumps(transcript_a, separators=(",", ":")).encode("utf-8")).hexdigest()
    transcript_b_hash = hashlib.sha256(json.dumps(transcript_b, separators=(",", ":")).encode("utf-8")).hexdigest()
    cov = HistoricalCoverageRecord(
        schema_version="stage1_6b_historical_coverage_v2",
        run_id=effective_run_id,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256=att_sha256,
        from_ms=from_ms,
        to_ms=to_ms,
        sweep_a_transcript=transcript_a,
        sweep_b_transcript=transcript_b,
        page_failures=page_failures,
        candidate_terminal_counts=terminal_counts,
        status="complete",
        captured_at_ms=int(time.time() * 1000),
        sweep_a={"reached_from_ms": sweep_a_ok, "page_failures": [], "transcript_hash": transcript_a_hash},
        sweep_b={"reached_from_ms": sweep_b_ok, "page_failures": [], "transcript_hash": transcript_b_hash},
        frozen_candidate_count=len(delisting_candidates),
        candidate_terminal_count=sum(terminal_counts.values()),
        pending_candidate_count=0,
        unattempted_candidate_count=0,
        final_checkpoint_valid=False,
        selected_catalog_id=SELECTED_CATALOG_ID,
        selected_catalog_name=SELECTED_CATALOG_NAME,
        selected_catalog_total_historical_max=hist_max,
        selected_catalog_total_sweep_a_final=sw_a_final,
        selected_catalog_total_sweep_b_final=sw_b_final,
    )
    final_checkpoint_valid = json.loads((validated_root / "observer_checkpoint.json").read_text(encoding="utf-8")).get("checkpoint_id") == final_chk_id
    cov = HistoricalCoverageRecord(
        **{**cov.to_dict(), "final_checkpoint_valid": final_checkpoint_valid}
    )
    root_bytes += write_historical_coverage(validated_root, cov, guard, root_bytes)

    # 8. Terminal status
    if not historical_coverage_is_complete(cov.to_dict()):
        failure = TerminalStatusRecord(
            schema_version="stage1_6b_terminal_status_v1",
            run_id=effective_run_id,
            capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
            source_profile_id=SOURCE_PROFILE_ID,
            status="failure",
            terminal_reason="historical_completion_incomplete",
            final_checkpoint_id=final_chk_id,
            terminated_at_ms=int(time.time() * 1000),
        )
        write_terminal_status(validated_root, failure, guard, root_bytes)
        return validated_root

    term = TerminalStatusRecord(
        schema_version="stage1_6b_terminal_status_v1",
        run_id=effective_run_id,
        capture_mode=CaptureMode.HISTORICAL_BACKFILL.value,
        source_profile_id=SOURCE_PROFILE_ID,
        status="complete",
        terminal_reason="historical_backfill_complete",
        final_checkpoint_id=final_chk_id,
        terminated_at_ms=int(time.time() * 1000),
    )
    root_bytes += write_terminal_status(validated_root, term, guard, root_bytes)
    seal_export(validated_root, guard, root_bytes)

    return validated_root


def main():
    parser = argparse.ArgumentParser(description="Stage 1.6B Historical Backfill Runner")
    parser.add_argument("--from-ms", type=int, required=True, help="Oldest publication timestamp (UTC epoch ms)")
    parser.add_argument("--to-ms", type=int, required=True, help="Newest publication timestamp (UTC epoch ms)")
    parser.add_argument("--source-profile-attestation", type=Path, required=True, help="Path to attested probe JSON")
    parser.add_argument("--live-public-readonly", action="store_true", default=False, help="Explicit readonly network permission")
    parser.add_argument("--project-root", type=Path, default=None, help="Root path of the project")
    parser.add_argument("--run-id", type=str, default=None, help="Optional run ID")

    args = parser.parse_args()

    try:
        root_dir = run_historical_backfill(
            from_ms=args.from_ms,
            to_ms=args.to_ms,
            attestation_path=args.source_profile_attestation,
            live_public_readonly=args.live_public_readonly,
            project_root=args.project_root,
            run_id=args.run_id,
        )
        print(f"SUCCESS: Historical backfill completed at {root_dir}")
        sys.exit(0)
    except Exception as exc:
        print(f"FAILED: Historical backfill failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
