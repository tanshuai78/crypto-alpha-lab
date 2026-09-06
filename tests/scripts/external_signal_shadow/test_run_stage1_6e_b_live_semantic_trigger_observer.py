"""Tests for Stage 1.6E-B CLI runner and integration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

import scripts.external_signal_shadow.run_stage1_6e_b_live_semantic_trigger_observer as runner_module
import src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage as storage_module
from configs import base
from scripts.external_signal_shadow.run_stage1_6e_b_live_semantic_trigger_observer import (
    parse_args,
    run_observer,
)
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
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_CORES as E_A_PROFILE_CORES,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_IDS as E_A_PROFILE_IDS,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    stage1_6e_a_permissions,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    RootWriterLock as E_A_RootWriterLock,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    append_observation as e_a_append_observation,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    write_capability_summary as e_a_write_capability_summary,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    write_manifest as e_a_write_manifest,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    write_raw_body as e_a_write_raw_body,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    write_source_profile as e_a_write_source_profile,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    write_source_profile_attestation as e_a_write_source_profile_attestation,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    write_terminal_status as e_a_write_terminal_status,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer import (
    Stage16EBStructuralError,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    SourceConsumerCheckpoint,
    canonical_json,
    sha256_hex,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage import (
    write_atomic_json,
)


def _setup_mock_ea(tmp_path: Path) -> Path:
    run_id = "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"
    root = tmp_path / run_id
    root.mkdir(parents=True, exist_ok=True)

    # Writer lock
    writer_lock = E_A_RootWriterLock(root)
    writer_lock.acquire()

    # Environment attestation
    attestation = {
        "schema_version": "stage1_6e_a_execution_environment_attestation_v1",
        "deployment_host_identity": "0" * 64,
        "hostname": "test-vps",
        "project_root_realpath": str(tmp_path),
        "root_filesystem_st_dev": os.stat(root).st_dev,
        "shared_lock_filesystem_st_dev": os.stat(root).st_dev,
        "network_namespace_inode": 12345,
        "proxy_environment": "absent",
        "runtime_user_uid": os.geteuid(),
        "deployment_git_commit": "a" * 40,
        "deployment_runtime_worktree_clean": True,
        "permissions": stage1_6e_a_permissions(),
    }
    att_sans_id = dict(attestation)
    attestation["execution_environment_id"] = sha256_hex(canonical_json(att_sans_id))
    write_atomic_json(root / "execution_environment_attestation.json", attestation)

    # Profiles & Attestations
    attestation_map = {}
    for pid in E_A_PROFILE_IDS:
        core = E_A_PROFILE_CORES[pid]
        p_sha = e_a_write_source_profile(root, pid, core)
        attestation_map[pid] = p_sha
        p_att = {
            "schema_version": "stage1_6e_a_profile_attestation_v1",
            "capability_run_id": root.name,
            "market_source_profile_id": pid,
            "profile_attestation_sha256": p_sha,
            "profile_attested_at_ms": 1700000000000,
            "permissions": stage1_6e_a_permissions(),
        }
        e_a_write_source_profile_attestation(root, pid, p_att)

    # 4 observations with 2 unique raw payload bodies
    raw1 = b'{"msg":"response 1"}'
    raw2 = b'{"msg":"response 2"}'
    raw_sha1 = e_a_write_raw_body(root, raw1)
    raw_sha2 = e_a_write_raw_body(root, raw2)

    obs_ids = []
    for seq, pid in enumerate(E_A_PROFILE_IDS, start=1):
        r_sha = raw_sha1 if seq <= 2 else raw_sha2
        r_len = len(raw1) if seq <= 2 else len(raw2)
        obs_id = hashlib.sha256(f"obs_{seq}".encode()).hexdigest()
        obs_ids.append(obs_id)
        obs = {
            "schema_version": "stage1_6e_a_capability_observation_v1",
            "market_capability_observation_id": obs_id,
            "capability_run_id": root.name,
            "market_source_profile_id": pid,
            "profile_attestation_sha256": attestation_map[pid],
            "probe_request_seq": seq,
            "request_identity": "1" * 64,
            "outcome_kind": "response_persisted",
            "local_observed_at_ms": 1700000000000 + seq,
            "http_status": 200,
            "response_headers_subset": {
                "content-type": "application/json",
                "content-length": str(r_len),
                "content-encoding": None,
                "date": "Mon, 31 Aug 2026 08:00:00 GMT",
                "retry-after": None,
            },
            "raw_payload_persisted": True,
            "raw_relative_path": f"raw/{r_sha}.body",
            "raw_sha256": r_sha,
            "observed_bytes_lower_bound": r_len,
            "payload_schema_status": "verified",
            "payload_time_status": "verified",
            "profile_status": "capability_pass",
            "terminal_classification": "continue",
            "permissions": stage1_6e_a_permissions(),
        }
        e_a_append_observation(root, obs)

    # Capability summary
    summary = {
        "schema_version": "stage1_6e_a_capability_summary_v1",
        "capability_run_id": root.name,
        "profile_states": {pid: "capability_pass" for pid in E_A_PROFILE_IDS},
        "observation_ids": {pid: obs_ids[i] for i, pid in enumerate(E_A_PROFILE_IDS)},
        "historical_retention_coverage": "not_evaluable",
        "event_market_coverage": "not_evaluable",
        "fee_coverage_status": "not_evaluated_in_stage1_6e_a",
        "permissions": stage1_6e_a_permissions(),
    }
    e_a_write_capability_summary(root, summary)

    # Terminal status complete
    term = {
        "schema_version": "stage1_6e_a_terminal_status_v1",
        "capability_run_id": root.name,
        "status": "complete",
        "terminal_reason": None,
        "started_at_ms": 1700000000000,
        "terminal_at_ms": 1700000005000,
        "profile_attestation_sha256_by_id": attestation_map,
        "attempted_profile_ids": list(E_A_PROFILE_IDS),
        "passed_profile_ids": list(E_A_PROFILE_IDS),
        "accounted_root_bytes": 10000,
        "permissions": stage1_6e_a_permissions(),
    }
    e_a_write_terminal_status(root, term)

    # Manifest
    manifest_payload = {
        "schema_version": "stage1_6e_a_manifest_v1",
        "capability_run_id": root.name,
        "terminal_status_sha256": hashlib.sha256((root / "terminal_status.json").read_bytes()).hexdigest(),
        "profile_attestation_sha256_by_id": attestation_map,
        "permissions": stage1_6e_a_permissions(),
    }
    e_a_write_manifest(root, manifest_payload)
    return root


def _setup_mock_source(tmp_path: Path, run_id: str) -> Path:
    src_root = tmp_path / "mock_source"
    src_root.mkdir(parents=True, exist_ok=True)

    body_text = (
        "Binance Futures will close all positions and conduct automatic settlement on "
        "USDⓈ-M REEFUSDT Perpetual Contract at 2026-09-10 09:00 (UTC)."
    )
    body_tree = {
        "node": "root",
        "child": [{"node": "element", "tag": "p", "child": [{"node": "text", "text": body_text}]}],
    }
    raw_payload = {
        "code": "000000",
        "data": {
            "code": "art_1",
            "title": "Binance Will Delist REEFUSDT Perpetual Contract",
            "body": json.dumps(body_tree),
            "id": 12345,
            "publishDate": 1700000000000,
        },
    }
    raw_bytes = json.dumps(raw_payload).encode("utf-8")
    raw_sha = sha256_hex(raw_bytes)
    raw_rel = f"raw_payloads/detail/art_1/{raw_sha}.bin"
    raw_path = src_root / raw_rel
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw_bytes)

    probe_attest = {
        "schema_version": "stage1_6b_source_profile_probe_attestation_v1",
        "source_profile_id": SOURCE_PROFILE_ID,
        "probe_status": "success",
    }
    probe_bytes = canonical_json(probe_attest).encode("utf-8")
    probe_sha = sha256_hex(probe_bytes)
    (src_root / "source_profile_probe_attestation.json").write_bytes(probe_bytes)

    import time
    now_ts = int(time.time() * 1000)
    captured_at_ms = now_ts - 2000
    heartbeat_at_ms = now_ts

    contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id=run_id,
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256=probe_sha,
        run_started_at_ms=captured_at_ms - 100_000,
    )
    (src_root / "capture_run_contract.json").write_text(
        canonical_json(contract.to_dict()), encoding="utf-8"
    )

    date_str = datetime.fromtimestamp(captured_at_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
    obs_rel = f"detail_observations/{date_str}.jsonl"
    obs_path = src_root / obs_rel
    obs_path.parent.mkdir(parents=True, exist_ok=True)

    obs_rec = DetailObservationRecord(
        schema_version="stage1_6b_detail_observation_v1",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        request_headers_profile_sha256=probe_sha,
        run_id=run_id,
        poll_seq=1,
        record_seq=1,
        request_observation_id="req_obs_art_1_001",
        source_article_id="art_1",
        request_variant=DETAIL_REQUEST_VARIANT,
        requested_url="https://www.binance.com/bapi/composite/v1/public/cms/article/detail?articleId=art_1",
        final_url="https://www.binance.com/bapi/composite/v1/public/cms/article/detail?articleId=art_1",
        http_status=200,
        content_type="application/json",
        raw_payload_sha256=raw_sha,
        raw_payload_bytes=len(raw_bytes),
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
        source_article_id="art_1",
        source_surface=DETAIL_SOURCE_SURFACE,
        source_locale=DETAIL_SOURCE_LOCALE,
        request_variant=DETAIL_REQUEST_VARIANT,
        detail_raw_sha256=raw_sha,
    )
    rev_rec = DetailRevisionRecord(
        schema_version="stage1_6b_detail_revision_v1",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_article_id="art_1",
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
    rev_path = src_root / "detail_revisions.jsonl"
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
        accounted_root_bytes=len(raw_bytes) + obs_offset + rev_offset,
        stream_offsets={
            "detail_revisions.jsonl": rev_offset,
            obs_rel: obs_offset,
        },
        stream_last_hashes={
            "detail_revisions.jsonl": rev_last_hash,
            obs_rel: obs_last_hash,
        },
        candidate_states={
            "art_1": {"first_discovered_at_ms": captured_at_ms}
        },
        heartbeat_at_ms=heartbeat_at_ms,
        last_index_poll_status="trusted",
        last_index_poll_coverage="successful",
        pending_terminal_failure_reason=None,
    )
    chk_dict = chk_rec.to_dict()
    chk_dict["checkpoint_id"] = compute_live_v3_checkpoint_id(chk_dict)
    (src_root / "observer_checkpoint.json").write_text(
        canonical_json(chk_dict), encoding="utf-8"
    )

    return src_root


def _patch_runner_authority(monkeypatch: pytest.MonkeyPatch, e_a_root: Path) -> None:
    attestation = json.loads(
        (e_a_root / "execution_environment_attestation.json").read_text(encoding="utf-8")
    )
    projection = {
        "deployment_host_identity": attestation["deployment_host_identity"],
        "hostname": attestation["hostname"],
        "project_root_realpath": attestation["project_root_realpath"],
        "capability_root_parent_filesystem_st_dev": attestation["root_filesystem_st_dev"],
        "shared_lock_filesystem_st_dev": attestation["shared_lock_filesystem_st_dev"],
        "network_namespace_inode": attestation["network_namespace_inode"],
        "proxy_environment": attestation["proxy_environment"],
        "runtime_user_uid": attestation["runtime_user_uid"],
        "deployment_git_commit": attestation["deployment_git_commit"],
        "deployment_runtime_worktree_clean": attestation["deployment_runtime_worktree_clean"],
    }
    manifest_id = json.loads((e_a_root / "manifest.json").read_text(encoding="utf-8"))["manifest_id"]
    monkeypatch.setattr(runner_module, "get_vps_step_a_projection", lambda _: projection)
    monkeypatch.setattr(storage_module, "_AUTHORIZED_E_A_MANIFEST_ID", manifest_id)


def _runner_args(
    *,
    e_a_root: Path,
    source_root: Path,
    source_run_id: str,
    supervisor_root: Path,
    events_root: Path,
    shared_lock: Path,
) -> argparse.Namespace:
    return argparse.Namespace(
        e_a_root=str(e_a_root.resolve()),
        source_root=str(source_root.resolve()),
        source_run_id=source_run_id,
        e_b_supervisor_root=str(supervisor_root.resolve()),
        e_b_events_root=str(events_root.resolve()),
        deployment_git_commit="2" * 40,
        shared_storage_lock=str(shared_lock.resolve()),
        once=True,
        poll_interval_s=0.01,
    )


def test_cli_arg_parsing_and_validations():
    required_args = [
        "--e-a-root", "/data/ea",
        "--source-root", "/data/source",
        "--source-run-id", "stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef",
        "--e-b-supervisor-root", "/data/sup",
        "--e-b-events-root", "/data/events",
        "--deployment-git-commit", "a" * 40,
    ]
    ns = parse_args(required_args)
    assert ns.e_a_root == "/data/ea"
    assert ns.once is False
    with pytest.raises(SystemExit):
        parse_args([*required_args, "--expected-e-a-manifest-id", "f" * 64])
    with pytest.raises(SystemExit):
        parse_args([*required_args, "--allow-synthetic-env-for-testing"])

    # Relative path error
    with pytest.raises(ValueError, match="absolute_path_required"):
        run_observer(
            argparse.Namespace(
                e_a_root="relative/path",
                source_root="/data/source",
                source_run_id="stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef",
                e_b_supervisor_root="/data/sup",
                e_b_events_root="/data/events",
                deployment_git_commit="a" * 40,
                shared_storage_lock=None,
                once=True,
                poll_interval_s=1.0,
            )
        )

    # Bad source run ID format
    with pytest.raises(ValueError, match="invalid_source_run_id_format"):
        run_observer(
            argparse.Namespace(
                e_a_root="/data/ea",
                source_root="/data/source",
                source_run_id="invalid_run_id",
                e_b_supervisor_root="/data/sup",
                e_b_events_root="/data/events",
                deployment_git_commit="a" * 40,
                shared_storage_lock=None,
                once=True,
                poll_interval_s=1.0,
            )
        )

    # Bad git commit format
    with pytest.raises(ValueError, match="invalid_deployment_git_commit"):
        run_observer(
            argparse.Namespace(
                e_a_root="/data/ea",
                source_root="/data/source",
                source_run_id="stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef",
                e_b_supervisor_root="/data/sup",
                e_b_events_root="/data/events",
                deployment_git_commit="short_sha",
                shared_storage_lock=None,
                once=True,
                poll_interval_s=1.0,
            )
        )


def test_financial_safety_invariants(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(base, "RISK_LIVE_TRADING_ENABLED", True)
    with pytest.raises(RuntimeError, match="RISK_LIVE_TRADING_ENABLED must be False"):
        run_observer(
            argparse.Namespace(
                e_a_root="/data/ea",
                source_root="/data/source",
                source_run_id="stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef",
                e_b_supervisor_root="/data/sup",
                e_b_events_root="/data/events",
                deployment_git_commit="a" * 40,
                shared_storage_lock=None,
                once=True,
                poll_interval_s=1.0,
            )
        )


def test_runner_bootstrap_does_not_construct_public_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    ea_root = _setup_mock_ea(tmp_path)
    run_id = "stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef"
    source_root = _setup_mock_source(tmp_path, run_id)
    supervisor_root = tmp_path / "supervisor_bootstrap"
    events_root = tmp_path / "events_bootstrap"
    shared_lock = tmp_path / ".stage1_5_storage_guard.lock"
    shared_lock.touch()
    _patch_runner_authority(monkeypatch, ea_root)

    class ClientMustNotConstruct:
        def __init__(self) -> None:
            raise AssertionError("public client must not be constructed during bootstrap")

    monkeypatch.setattr(runner_module, "Stage16EBPublicClient", ClientMustNotConstruct)
    assert run_observer(
        _runner_args(
            e_a_root=ea_root,
            source_root=source_root,
            source_run_id=run_id,
            supervisor_root=supervisor_root,
            events_root=events_root,
            shared_lock=shared_lock,
        )
    ) == 0


def test_runner_e2e_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ea_root = _setup_mock_ea(tmp_path)
    run_id = "stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef"
    source_root = _setup_mock_source(tmp_path, run_id)

    sup_root = tmp_path / "supervisor"
    events_root = tmp_path / "events"
    shared_lock = tmp_path / ".stage1_5_storage_guard.lock"
    shared_lock.touch()

    # Pre-create consumer checkpoint at offset 0 so runner consumes the new revision
    src_chk_data = json.loads((source_root / "observer_checkpoint.json").read_text(encoding="utf-8"))
    src_chk_id = src_chk_data["checkpoint_id"]
    src_chk_sha = sha256_hex((source_root / "observer_checkpoint.json").read_bytes())

    sup_chk = SourceConsumerCheckpoint.create(
        supervisor_run_id="stage1_6e_b_supervisor_20260905T120000Z_0123456789abcdef0123456789abcdef",
        source_root_realpath=str(source_root.resolve()),
        source_checkpoint_id=src_chk_id,
        source_checkpoint_sha256=src_chk_sha,
        source_stream_offsets={"detail_revisions.jsonl": 0},
        source_stream_last_hashes={"detail_revisions.jsonl": None},
        detail_revisions_committed_offset=0,
        detail_revisions_last_line_sha256=None,
        last_consumed_detail_revision_record_seq=None,
        active_notice_event_key=None,
        active_event_id=None,
        updated_at_ms=1700000000000,
    )
    sup_root.mkdir(parents=True, exist_ok=True)
    write_atomic_json(sup_root / "source_consumer_checkpoint.json", sup_chk.to_dict())

    _patch_runner_authority(monkeypatch, ea_root)
    args = _runner_args(
        e_a_root=ea_root,
        source_root=source_root,
        source_run_id=run_id,
        supervisor_root=sup_root,
        events_root=events_root,
        shared_lock=shared_lock,
    )

    ret = run_observer(args)
    assert ret == 0

    assert (sup_root / "execution_environment_attestation.json").exists()
    assert (sup_root / "environment_authority_receipt.json").exists()
    assert (sup_root / "source_consumer_checkpoint.json").exists()
    assert (sup_root / "semantic_projections.jsonl").exists()
    assert (sup_root / "event_admissions.jsonl").exists()

    # Event root created
    active_events = list(events_root.iterdir())
    assert len(active_events) == 1
    event_dir = active_events[0]
    assert (event_dir / "event_contract.json").exists()
    assert (event_dir / "event_checkpoint.json").exists()
    assert (event_dir / "execution_environment_attestation.json").exists()
    assert (event_dir / "environment_authority_receipt.json").exists()


def test_runner_c5_recovery_from_uncreated_admission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ea_root = _setup_mock_ea(tmp_path)
    run_id = "stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef"
    source_root = _setup_mock_source(tmp_path, run_id)

    sup_root = tmp_path / "supervisor_c5_rec"
    events_root = tmp_path / "events_c5_rec"
    shared_lock = tmp_path / ".stage1_5_storage_guard.lock"
    shared_lock.touch()

    # 1. First run creates the admission, but simulate crash before event root creation
    src_chk_data = json.loads((source_root / "observer_checkpoint.json").read_text(encoding="utf-8"))
    src_chk_id = src_chk_data["checkpoint_id"]
    src_chk_sha = sha256_hex((source_root / "observer_checkpoint.json").read_bytes())

    sup_chk = SourceConsumerCheckpoint.create(
        supervisor_run_id="stage1_6e_b_supervisor_20260905T120000Z_0123456789abcdef0123456789abcdef",
        source_root_realpath=str(source_root.resolve()),
        source_checkpoint_id=src_chk_id,
        source_checkpoint_sha256=src_chk_sha,
        source_stream_offsets={"detail_revisions.jsonl": 0},
        source_stream_last_hashes={"detail_revisions.jsonl": None},
        detail_revisions_committed_offset=0,
        detail_revisions_last_line_sha256=None,
        last_consumed_detail_revision_record_seq=None,
        active_notice_event_key=None,
        active_event_id=None,
        updated_at_ms=1700000000000,
    )
    sup_root.mkdir(parents=True, exist_ok=True)
    write_atomic_json(sup_root / "source_consumer_checkpoint.json", sup_chk.to_dict())

    _patch_runner_authority(monkeypatch, ea_root)
    args = _runner_args(
        e_a_root=ea_root,
        source_root=source_root,
        source_run_id=run_id,
        supervisor_root=sup_root,
        events_root=events_root,
        shared_lock=shared_lock,
    )

    run_observer(args)

    # Delete event root to simulate crash immediately after admission persisted
    active_events = list(events_root.iterdir())
    assert len(active_events) == 1
    event_dir = active_events[0]
    import shutil
    shutil.rmtree(event_dir)

    # Reset consumer checkpoint active fields to None
    cur_chk = json.loads((sup_root / "source_consumer_checkpoint.json").read_text(encoding="utf-8"))
    cur_chk["active_notice_event_key"] = None
    cur_chk["active_event_id"] = None
    write_atomic_json(sup_root / "source_consumer_checkpoint.json", cur_chk)

    # Re-run: startup recovery detects C5, orchestrates creation
    ret = run_observer(args)
    assert ret == 0
    assert event_dir.exists()
    assert (event_dir / "event_contract.json").exists()


def test_runner_c6_recovery_from_existing_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ea_root = _setup_mock_ea(tmp_path)
    run_id = "stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef"
    source_root = _setup_mock_source(tmp_path, run_id)

    sup_root = tmp_path / "supervisor_c6_rec"
    events_root = tmp_path / "events_c6_rec"
    shared_lock = tmp_path / ".stage1_5_storage_guard.lock"
    shared_lock.touch()

    # Pre-create consumer checkpoint at offset 0
    src_chk_data = json.loads((source_root / "observer_checkpoint.json").read_text(encoding="utf-8"))
    src_chk_id = src_chk_data["checkpoint_id"]
    src_chk_sha = sha256_hex((source_root / "observer_checkpoint.json").read_bytes())

    sup_chk = SourceConsumerCheckpoint.create(
        supervisor_run_id="stage1_6e_b_supervisor_20260905T120000Z_0123456789abcdef0123456789abcdef",
        source_root_realpath=str(source_root.resolve()),
        source_checkpoint_id=src_chk_id,
        source_checkpoint_sha256=src_chk_sha,
        source_stream_offsets={"detail_revisions.jsonl": 0},
        source_stream_last_hashes={"detail_revisions.jsonl": None},
        detail_revisions_committed_offset=0,
        detail_revisions_last_line_sha256=None,
        last_consumed_detail_revision_record_seq=None,
        active_notice_event_key=None,
        active_event_id=None,
        updated_at_ms=1700000000000,
    )
    sup_root.mkdir(parents=True, exist_ok=True)
    write_atomic_json(sup_root / "source_consumer_checkpoint.json", sup_chk.to_dict())

    _patch_runner_authority(monkeypatch, ea_root)
    args = _runner_args(
        e_a_root=ea_root,
        source_root=source_root,
        source_run_id=run_id,
        supervisor_root=sup_root,
        events_root=events_root,
        shared_lock=shared_lock,
    )

    run_observer(args)

    # Event root exists, now clear active fields in consumer checkpoint (simulating crash before active checkpoint write)
    cur_chk = json.loads((sup_root / "source_consumer_checkpoint.json").read_text(encoding="utf-8"))
    saved_event_id = cur_chk["active_event_id"]
    cur_chk["active_notice_event_key"] = None
    cur_chk["active_event_id"] = None
    write_atomic_json(sup_root / "source_consumer_checkpoint.json", cur_chk)

    # Re-run: C6 startup recovery detects existing valid deterministic root, verifies controlled resume, activates checkpoint-only
    ret = run_observer(args)
    assert ret == 0

    reloaded_chk = json.loads((sup_root / "source_consumer_checkpoint.json").read_text(encoding="utf-8"))
    assert reloaded_chk["active_event_id"] == saved_event_id

    # A second C6 recovery must reject a tampered receipt before source/client work.
    reloaded_chk["active_notice_event_key"] = None
    reloaded_chk["active_event_id"] = None
    write_atomic_json(sup_root / "source_consumer_checkpoint.json", reloaded_chk)
    receipt_path = events_root / saved_event_id / "environment_authority_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["e_a_manifest_id"] = "f" * 64
    write_atomic_json(receipt_path, receipt)

    class ClientMustNotConstruct:
        def __init__(self) -> None:
            raise AssertionError("C6 validation must precede public client construction")

    monkeypatch.setattr(runner_module, "Stage16EBPublicClient", ClientMustNotConstruct)
    with pytest.raises(Stage16EBStructuralError, match="c6_receipt"):
        run_observer(args)


def test_runner_startup_recovery_blocks_c8_c9_terminal_bypasses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    ea_root = _setup_mock_ea(tmp_path)
    run_id = "stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef"
    source_root = _setup_mock_source(tmp_path, run_id)
    sup_root = tmp_path / "supervisor_terminal_recovery"
    events_root = tmp_path / "events_terminal_recovery"
    shared_lock = tmp_path / ".stage1_5_storage_guard.lock"
    shared_lock.touch()
    _patch_runner_authority(monkeypatch, ea_root)

    source_checkpoint = json.loads((source_root / "observer_checkpoint.json").read_text(encoding="utf-8"))
    write_atomic_json(
        sup_root / "source_consumer_checkpoint.json",
        SourceConsumerCheckpoint.create(
            supervisor_run_id="stage1_6e_b_supervisor_20260905T120000Z_0123456789abcdef0123456789abcdef",
            source_root_realpath=str(source_root.resolve()),
            source_checkpoint_id=source_checkpoint["checkpoint_id"],
            source_checkpoint_sha256=sha256_hex((source_root / "observer_checkpoint.json").read_bytes()),
            source_stream_offsets={"detail_revisions.jsonl": 0},
            source_stream_last_hashes={"detail_revisions.jsonl": None},
            detail_revisions_committed_offset=0,
            detail_revisions_last_line_sha256=None,
            last_consumed_detail_revision_record_seq=None,
            active_notice_event_key=None,
            active_event_id=None,
            updated_at_ms=1700000000000,
        ).to_dict(),
    )
    args = _runner_args(
        e_a_root=ea_root,
        source_root=source_root,
        source_run_id=run_id,
        supervisor_root=sup_root,
        events_root=events_root,
        shared_lock=shared_lock,
    )
    assert run_observer(args) == 0

    checkpoint_path = sup_root / "source_consumer_checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    event_id = checkpoint["active_event_id"]
    checkpoint["active_notice_event_key"] = None
    checkpoint["active_event_id"] = None
    write_atomic_json(checkpoint_path, checkpoint)
    event_dir = events_root / event_id

    class ClientMustNotConstruct:
        def __init__(self) -> None:
            raise AssertionError("terminal startup recovery must block before public client construction")

    monkeypatch.setattr(runner_module, "Stage16EBPublicClient", ClientMustNotConstruct)
    write_atomic_json(
        event_dir / "terminal_status.json",
        {"schema_version": "stage1_6e_b_terminal_status_v1", "status": "failed"},
    )
    with storage_module.RootWriterLock(event_dir, ".stage1_6e_b_event_writer.lock"):
        with pytest.raises(Stage16EBStructuralError, match="global_active_supervisor_state_invalid"):
            run_observer(args)

    write_atomic_json(
        event_dir / "terminal_status.json",
        {"schema_version": "stage1_6e_b_terminal_status_v1", "status": "complete"},
    )
    write_atomic_json(event_dir / "manifest.json", {"manifest_id": "corrupt"})
    with pytest.raises(Stage16EBStructuralError, match="global_active_supervisor_state_invalid"):
        run_observer(args)


def test_runner_c5_pre_root_equality_rejection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ea_root = _setup_mock_ea(tmp_path)
    run_id = "stage1_6b_live_source_20260904T120000Z_0123456789abcdef0123456789abcdef"
    source_root = _setup_mock_source(tmp_path, run_id)

    sup_root = tmp_path / "supervisor_c5_pre_fail"
    events_root = tmp_path / "events_c5_pre_fail"
    shared_lock = tmp_path / ".stage1_5_storage_guard.lock"
    shared_lock.touch()

    src_chk_data = json.loads((source_root / "observer_checkpoint.json").read_text(encoding="utf-8"))
    src_chk_id = src_chk_data["checkpoint_id"]
    src_chk_sha = sha256_hex((source_root / "observer_checkpoint.json").read_bytes())

    sup_chk = SourceConsumerCheckpoint.create(
        supervisor_run_id="stage1_6e_b_supervisor_20260905T120000Z_0123456789abcdef0123456789abcdef",
        source_root_realpath=str(source_root.resolve()),
        source_checkpoint_id=src_chk_id,
        source_checkpoint_sha256=src_chk_sha,
        source_stream_offsets={"detail_revisions.jsonl": 0},
        source_stream_last_hashes={"detail_revisions.jsonl": None},
        detail_revisions_committed_offset=0,
        detail_revisions_last_line_sha256=None,
        last_consumed_detail_revision_record_seq=None,
        active_notice_event_key=None,
        active_event_id=None,
        updated_at_ms=1700000000000,
    )
    sup_root.mkdir(parents=True, exist_ok=True)
    write_atomic_json(sup_root / "source_consumer_checkpoint.json", sup_chk.to_dict())

    _patch_runner_authority(monkeypatch, ea_root)
    args = _runner_args(
        e_a_root=ea_root,
        source_root=source_root,
        source_run_id=run_id,
        supervisor_root=sup_root,
        events_root=events_root,
        shared_lock=shared_lock,
    )

    # 1. First run creates event root and admission
    run_observer(args)
    active_events = list(events_root.iterdir())
    assert len(active_events) == 1
    event_dir = active_events[0]

    # 2. Simulate crash after admission: delete event root, reset consumer checkpoint active fields
    import shutil
    shutil.rmtree(event_dir)
    cur_chk = json.loads((sup_root / "source_consumer_checkpoint.json").read_text(encoding="utf-8"))
    cur_chk["active_notice_event_key"] = None
    cur_chk["active_event_id"] = None
    write_atomic_json(sup_root / "source_consumer_checkpoint.json", cur_chk)

    # 3. Mutate E-A execution environment attestation so PRE-ROOT equality check fails
    from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage import (
        Stage16EBStorageBlocked,
    )
    ea_att_path = ea_root / "execution_environment_attestation.json"
    ea_att_data = json.loads(ea_att_path.read_text(encoding="utf-8"))
    ea_att_data["deployment_host_identity"] = "mismatched_host_id_" + "0" * 45
    write_atomic_json(ea_att_path, ea_att_data)

    # 4. Re-run: C5 PRE-ROOT gate fails closed, zero event root created!
    with pytest.raises(Stage16EBStorageBlocked):
        run_observer(args)

    assert not event_dir.exists()
