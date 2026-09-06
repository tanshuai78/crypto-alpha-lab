"""Tests for Stage 1.6E-B 1.6D source consumer and boundary validation."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    DETAIL_REQUEST_VARIANT,
    DETAIL_SOURCE_LOCALE,
    DETAIL_SOURCE_SURFACE,
    SOURCE_PROFILE_ID,
    CaptureMode,
    CaptureRunContract,
    DetailObservationRecord,
    DetailRevisionRecord,
    ObserverCheckpointRecord,
    compute_detail_revision_id,
    compute_live_v3_checkpoint_id,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    canonical_json,
    sha256_hex,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_source import (
    Stage16EBOrphanOrAmbiguousLiveRevision,
    Stage16EBRawPathHashOrProfileMismatch,
    Stage16EBSourceCheckpointInvalid,
    Stage16EBSourceConsumer,
    Stage16EBSourceError,
)


def _setup_canonical_1_6d_source(
    root_dir: Path,
    run_id: str,
    captured_at_ms: int,
    heartbeat_at_ms: int,
    article_id: str = "10001",
    payload_content: bytes = b'{"code":"000000","data":{"id":10001,"title":"Notice"}}',
) -> tuple[dict, DetailRevisionRecord, DetailObservationRecord, str]:
    """Builds a canonical 1.6D source directory using canonical models and serializers."""
    root_dir.mkdir(parents=True, exist_ok=True)
    raw_sha = sha256_hex(payload_content)
    raw_rel = f"raw_payloads/detail/{article_id}/{raw_sha}.bin"
    raw_path = root_dir / raw_rel
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload_content)

    probe_attest = {
        "schema_version": "stage1_6b_source_profile_probe_attestation_v1",
        "source_profile_id": SOURCE_PROFILE_ID,
        "probe_status": "success",
    }
    probe_bytes = canonical_json(probe_attest).encode("utf-8")
    probe_sha = sha256_hex(probe_bytes)
    (root_dir / "source_profile_probe_attestation.json").write_bytes(probe_bytes)

    contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id=run_id,
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256=probe_sha,
        run_started_at_ms=captured_at_ms - 100_000,
    )
    (root_dir / "capture_run_contract.json").write_text(
        canonical_json(contract.to_dict()), encoding="utf-8"
    )

    date_str = datetime.fromtimestamp(captured_at_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
    obs_rel = f"detail_observations/{date_str}.jsonl"
    obs_path = root_dir / obs_rel
    obs_path.parent.mkdir(parents=True, exist_ok=True)

    obs_rec = DetailObservationRecord(
        schema_version="stage1_6b_detail_observation_v1",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        request_headers_profile_sha256=probe_sha,
        run_id=run_id,
        poll_seq=1,
        record_seq=1,
        request_observation_id=f"req_obs_{article_id}_001",
        source_article_id=article_id,
        request_variant=DETAIL_REQUEST_VARIANT,
        requested_url=f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail?articleId={article_id}",
        final_url=f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail?articleId={article_id}",
        http_status=200,
        content_type="application/json",
        raw_payload_sha256=raw_sha,
        raw_payload_bytes=len(payload_content),
        raw_payload_relative_path=raw_rel,
        trust_validation_status="trusted",
        t_detail_receive_ms=captured_at_ms,
        captured_at_ms=captured_at_ms,
    )
    obs_line = canonical_json(obs_rec.to_dict()) + "\n"
    obs_path.write_text(obs_line, encoding="utf-8")
    obs_offset = len(obs_line.encode("utf-8"))
    obs_last_hash = sha256_hex(obs_line.strip().encode("utf-8"))

    rev_id = compute_detail_revision_id(
        source_article_id=article_id,
        source_surface=DETAIL_SOURCE_SURFACE,
        source_locale=DETAIL_SOURCE_LOCALE,
        request_variant=DETAIL_REQUEST_VARIANT,
        detail_raw_sha256=raw_sha,
    )
    rev_rec = DetailRevisionRecord(
        schema_version="stage1_6b_detail_revision_v1",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_article_id=article_id,
        source_surface=DETAIL_SOURCE_SURFACE,
        source_locale=DETAIL_SOURCE_LOCALE,
        request_variant=DETAIL_REQUEST_VARIANT,
        detail_revision_id=rev_id,
        detail_raw_sha256=raw_sha,
        raw_payload_relative_path=raw_rel,
        t_detail_trusted_ms=captured_at_ms,
        t_raw_persisted_ms=captured_at_ms,
        captured_at_ms=captured_at_ms,
        record_seq=1,
    )
    rev_path = root_dir / "detail_revisions.jsonl"
    rev_line = canonical_json(rev_rec.to_dict()) + "\n"
    rev_path.write_text(rev_line, encoding="utf-8")
    rev_offset = len(rev_line.encode("utf-8"))
    rev_last_hash = sha256_hex(rev_line.strip().encode("utf-8"))

    chk_rec = ObserverCheckpointRecord(
        schema_version="stage1_6b_observer_checkpoint_v3",
        run_id=run_id,
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256=probe_sha,
        checkpoint_id="",
        prior_checkpoint_id=None,
        poll_seq=1,
        monotonic_request_seq=1,
        record_seq=1,
        accounted_root_bytes=len(payload_content) + obs_offset + rev_offset,
        stream_offsets={
            "detail_revisions.jsonl": rev_offset,
            obs_rel: obs_offset,
        },
        stream_last_hashes={
            "detail_revisions.jsonl": rev_last_hash,
            obs_rel: obs_last_hash,
        },
        candidate_states={
            article_id: {
                "source_article_id": article_id,
                "first_discovered_poll_seq": 1,
                "first_discovered_at_ms": captured_at_ms,
                "lane": "lane_a",
                "detail_attempt_count": 1,
                "retry_cycle_count": 0,
                "first_attempt_at_ms": captured_at_ms,
                "last_attempt_at_ms": captured_at_ms,
                "next_retry_at_ms": None,
                "terminal_reason": "trusted_detail_observed",
                "trusted_detail_revision_id": rev_id,
            }
        },
        heartbeat_at_ms=heartbeat_at_ms,
        last_index_poll_status="trusted",
        last_index_poll_coverage="successful",
        pending_terminal_failure_reason=None,
    )
    chk_dict = chk_rec.to_dict()
    chk_id = compute_live_v3_checkpoint_id(chk_dict)
    chk_dict["checkpoint_id"] = chk_id
    (root_dir / "observer_checkpoint.json").write_text(
        canonical_json(chk_dict), encoding="utf-8"
    )

    return chk_dict, rev_rec, obs_rec, obs_rel


def test_source_selection_rejects_relative_or_invalid(tmp_path: Path):
    with pytest.raises(Stage16EBSourceError, match="absolute_path_required"):
        Stage16EBSourceConsumer(
            authorized_source_root="relative/path",
            authorized_run_id="run_1",
            consumer_checkpoint_path=tmp_path / "chk.json",
        )

    with pytest.raises(Stage16EBSourceError, match="source_root_missing"):
        Stage16EBSourceConsumer(
            authorized_source_root=tmp_path / "missing",
            authorized_run_id="run_1",
            consumer_checkpoint_path=tmp_path / "chk.json",
        )


def test_source_snapshot_validation_canonical_success(tmp_path: Path):
    source_dir = tmp_path / "source_run_1"
    run_id = "run_1"
    now_ms = 1_725_500_000_000
    heartbeat_ms = now_ms - 10_000

    chk_dict, rev_rec, obs_rec, obs_rel = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=heartbeat_ms
    )

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )

    snapshot = consumer.poll_and_validate_source_snapshot(current_time_ms=now_ms)
    assert snapshot.is_ready is True
    assert snapshot.checkpoint["run_id"] == run_id
    assert snapshot.checkpoint_id == chk_dict["checkpoint_id"]


def test_checkpoint_complete_map_unrelated_stream_missing_fails(tmp_path: Path):
    source_dir = tmp_path / "source_run_unrelated_missing"
    run_id = "run_unrelated"
    now_ms = 1_725_500_000_000

    chk_dict, _, _, _ = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    # Add an unrelated stream in offsets/last_hashes but do NOT create the file
    chk_dict["stream_offsets"]["article_catalog_observations/2026-09-05.jsonl"] = 500
    chk_dict["stream_last_hashes"]["article_catalog_observations/2026-09-05.jsonl"] = "0" * 64
    chk_dict["checkpoint_id"] = compute_live_v3_checkpoint_id(chk_dict)
    (source_dir / "observer_checkpoint.json").write_text(canonical_json(chk_dict), encoding="utf-8")

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )
    with pytest.raises(Stage16EBSourceCheckpointInvalid, match="checkpoint_stream_missing"):
        consumer.poll_and_validate_source_snapshot(current_time_ms=now_ms)


def test_checkpoint_stream_boundary_not_newline_fails(tmp_path: Path):
    source_dir = tmp_path / "source_run_boundary"
    run_id = "run_boundary"
    now_ms = 1_725_500_000_000

    chk_dict, _, _, _ = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    # Mutate offset to point inside a line instead of ending at \n
    chk_dict["stream_offsets"]["detail_revisions.jsonl"] -= 5
    chk_dict["checkpoint_id"] = compute_live_v3_checkpoint_id(chk_dict)
    (source_dir / "observer_checkpoint.json").write_text(canonical_json(chk_dict), encoding="utf-8")

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )
    with pytest.raises(Stage16EBSourceCheckpointInvalid, match="offset_not_line_boundary"):
        consumer.poll_and_validate_source_snapshot(current_time_ms=now_ms)


def test_checkpoint_stream_last_hash_mismatch_fails(tmp_path: Path):
    source_dir = tmp_path / "source_run_hash_mismatch"
    run_id = "run_hash_mismatch"
    now_ms = 1_725_500_000_000

    chk_dict, _, _, _ = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    chk_dict["stream_last_hashes"]["detail_revisions.jsonl"] = "f" * 64
    chk_dict["checkpoint_id"] = compute_live_v3_checkpoint_id(chk_dict)
    (source_dir / "observer_checkpoint.json").write_text(canonical_json(chk_dict), encoding="utf-8")

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )
    with pytest.raises(Stage16EBSourceCheckpointInvalid, match="prefix_hash_mismatch"):
        consumer.poll_and_validate_source_snapshot(current_time_ms=now_ms)


def test_linkage_unique_trusted_observation_success(tmp_path: Path):
    source_dir = tmp_path / "source_run_linkage"
    run_id = "run_linkage"
    now_ms = 1_725_500_000_000

    chk_dict, rev_rec, obs_rec, _ = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )

    linked_obs, raw_bytes = consumer.link_and_verify_detail_revision(
        revision=rev_rec.to_dict(),
        current_checkpoint=chk_dict,
    )
    assert linked_obs["request_observation_id"] == obs_rec.request_observation_id
    assert linked_obs["source_article_id"] == rev_rec.source_article_id
    assert sha256_hex(raw_bytes) == rev_rec.detail_raw_sha256


def test_linkage_zero_candidates_fails_as_orphan_no_raw_read(tmp_path: Path):
    source_dir = tmp_path / "source_run_zero_cands"
    run_id = "run_zero"
    now_ms = 1_725_500_000_000

    chk_dict, rev_rec, obs_rec, obs_rel = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    # Corrupt observation status in daily stream so 0 candidates match
    obs_dict = obs_rec.to_dict()
    obs_dict["trust_validation_status"] = "waf_rejected"
    new_line = canonical_json(obs_dict) + "\n"
    (source_dir / obs_rel).write_text(new_line, encoding="utf-8")
    chk_dict["stream_offsets"][obs_rel] = len(new_line.encode("utf-8"))
    chk_dict["stream_last_hashes"][obs_rel] = sha256_hex(new_line.strip().encode("utf-8"))
    chk_dict["checkpoint_id"] = compute_live_v3_checkpoint_id(chk_dict)
    (source_dir / "observer_checkpoint.json").write_text(canonical_json(chk_dict), encoding="utf-8")

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )
    with pytest.raises(Stage16EBOrphanOrAmbiguousLiveRevision, match="orphan_or_ambiguous_live_revision: found 0"):
        consumer.link_and_verify_detail_revision(
            revision=rev_rec.to_dict(),
            current_checkpoint=chk_dict,
        )


def test_linkage_multiple_candidates_fails_as_ambiguous_no_raw_read(tmp_path: Path):
    source_dir = tmp_path / "source_run_mult_cands"
    run_id = "run_mult"
    now_ms = 1_725_500_000_000

    chk_dict, rev_rec, obs_rec, obs_rel = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    # Write two identical matching observations into daily stream
    obs_line = canonical_json(obs_rec.to_dict()) + "\n"
    double_lines = obs_line + obs_line
    (source_dir / obs_rel).write_text(double_lines, encoding="utf-8")
    chk_dict["stream_offsets"][obs_rel] = len(double_lines.encode("utf-8"))
    chk_dict["stream_last_hashes"][obs_rel] = sha256_hex(obs_line.strip().encode("utf-8"))
    chk_dict["checkpoint_id"] = compute_live_v3_checkpoint_id(chk_dict)
    (source_dir / "observer_checkpoint.json").write_text(canonical_json(chk_dict), encoding="utf-8")

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )
    with pytest.raises(Stage16EBOrphanOrAmbiguousLiveRevision, match="orphan_or_ambiguous_live_revision: found 2"):
        consumer.link_and_verify_detail_revision(
            revision=rev_rec.to_dict(),
            current_checkpoint=chk_dict,
        )


def test_linkage_daily_stream_not_committed_fails(tmp_path: Path):
    source_dir = tmp_path / "source_run_uncommitted_day"
    run_id = "run_uncommitted"
    now_ms = 1_725_500_000_000

    chk_dict, rev_rec, _, obs_rel = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    # Remove daily observation stream from stream_offsets
    del chk_dict["stream_offsets"][obs_rel]
    del chk_dict["stream_last_hashes"][obs_rel]
    chk_dict["checkpoint_id"] = compute_live_v3_checkpoint_id(chk_dict)
    (source_dir / "observer_checkpoint.json").write_text(canonical_json(chk_dict), encoding="utf-8")

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )
    with pytest.raises(Stage16EBSourceCheckpointInvalid, match="daily_observation_stream_not_committed"):
        consumer.link_and_verify_detail_revision(
            revision=rev_rec.to_dict(),
            current_checkpoint=chk_dict,
        )


def test_linkage_physical_raw_missing_fails(tmp_path: Path):
    source_dir = tmp_path / "source_run_raw_missing"
    run_id = "run_raw_missing"
    now_ms = 1_725_500_000_000

    chk_dict, rev_rec, _, _ = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    raw_path = source_dir / rev_rec.raw_payload_relative_path
    raw_path.unlink()

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )
    with pytest.raises(Stage16EBRawPathHashOrProfileMismatch, match="raw_missing_or_symlink"):
        consumer.link_and_verify_detail_revision(
            revision=rev_rec.to_dict(),
            current_checkpoint=chk_dict,
        )


def test_linkage_physical_raw_symlink_fails(tmp_path: Path):
    source_dir = tmp_path / "source_run_raw_symlink"
    run_id = "run_raw_symlink"
    now_ms = 1_725_500_000_000

    chk_dict, rev_rec, _, _ = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    raw_path = source_dir / rev_rec.raw_payload_relative_path
    real_raw = tmp_path / "external_real_raw.bin"
    real_raw.write_bytes(raw_path.read_bytes())
    raw_path.unlink()
    raw_path.symlink_to(real_raw)

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )
    with pytest.raises(Stage16EBRawPathHashOrProfileMismatch, match="raw_missing_or_symlink"):
        consumer.link_and_verify_detail_revision(
            revision=rev_rec.to_dict(),
            current_checkpoint=chk_dict,
        )


def test_linkage_physical_raw_hash_mismatch_fails(tmp_path: Path):
    source_dir = tmp_path / "source_run_raw_hash"
    run_id = "run_raw_hash"
    now_ms = 1_725_500_000_000

    chk_dict, rev_rec, _, _ = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )
    raw_path = source_dir / rev_rec.raw_payload_relative_path
    raw_path.write_bytes(b"corrupted_bytes_that_do_not_match_sha")

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=tmp_path / "consumer_checkpoint.json",
    )
    with pytest.raises(Stage16EBRawPathHashOrProfileMismatch, match="raw_payload_hash_mismatch"):
        consumer.link_and_verify_detail_revision(
            revision=rev_rec.to_dict(),
            current_checkpoint=chk_dict,
        )
