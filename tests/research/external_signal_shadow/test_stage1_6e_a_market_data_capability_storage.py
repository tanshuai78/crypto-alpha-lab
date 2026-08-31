import hashlib
import json
import os
import subprocess
import sys
import time

import pytest

from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_CORES,
    PROFILE_IDS,
    canonical_json,
    stage1_6e_a_permissions,
)


def _refresh_manifest_id(manifest: dict) -> None:
    sans_id = {key: value for key, value in manifest.items() if key != "manifest_id"}
    manifest["manifest_id"] = hashlib.sha256(canonical_json(sans_id)).hexdigest()


def test_root_writer_lock_mutual_exclusion(tmp_path):
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
        RootWriterLock,
    )

    root = tmp_path / "test_root"
    root.mkdir()

    lock_a = RootWriterLock(root)
    lock_b = RootWriterLock(root)

    lock_a.acquire()
    lock_file = root / ".stage1_6e_a_writer.lock"
    assert lock_file.is_file()
    assert lock_file.stat().st_size == 0
    assert hashlib.sha256(b"").hexdigest() == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    with pytest.raises(BlockingIOError):
        lock_b.acquire()

    lock_a.release()
    lock_b.acquire()
    lock_b.release()
    assert lock_file.read_bytes() == b""
    assert hashlib.sha256(lock_file.read_bytes()).hexdigest() == hashlib.sha256(b"").hexdigest()


def test_storage_guard_advisory_lock_cross_process(tmp_path):
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
        Stage16EAStorageGuard,
    )

    shared_lock = tmp_path / ".stage1_5_storage_guard.lock"
    guard = Stage16EAStorageGuard(shared_lock_path=shared_lock)

    # Spawn subprocess holding lock
    code = f"""
import fcntl, time, sys
from pathlib import Path
f = open("{shared_lock}", "w")
fcntl.flock(f.fileno(), fcntl.LOCK_EX)
sys.stdout.write("LOCKED\\n")
sys.stdout.flush()
time.sleep(0.5)
fcntl.flock(f.fileno(), fcntl.LOCK_UN)
f.close()
"""
    proc = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    try:
        ready = proc.stdout.readline()
        assert ready.strip() == "LOCKED"

        t0 = time.time()
        with guard.acquire_shared_lock():
            t1 = time.time()
            assert t1 - t0 >= 0.2  # Waited for release
    finally:
        proc.kill()
        proc.wait()


def test_storage_guard_interoperates_with_stage1_5_guard_in_both_directions(tmp_path):
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
        Stage16EAStorageGuard,
    )

    stage15_root = tmp_path / "data/external_signal_shadow/stage1_5d/live"
    stage15_root.mkdir(parents=True)
    stage16_root = tmp_path / "data/external_signal_shadow/stage1_6e/capability_audits/run"
    stage16_root.parent.mkdir(parents=True)

    # The child uses the actual Stage 1.5 guard implementation, not fcntl directly.
    child_code = """
import sys
import time
from pathlib import Path
from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

guard = StorageGuard(Path(sys.argv[1]), \"1.5D\")
fd = guard._acquire_lock()
print(\"LOCKED\", flush=True)
time.sleep(float(sys.argv[2]))
guard._release_lock(fd)
"""
    guard = Stage16EAStorageGuard(output_root=stage16_root)

    proc = subprocess.Popen(
        [sys.executable, "-c", child_code, str(stage15_root), "0.35"],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout.readline().strip() == "LOCKED"
        started = time.monotonic()
        with guard.acquire_shared_lock():
            assert time.monotonic() - started >= 0.20
    finally:
        proc.wait(timeout=2)

    started = time.monotonic()
    with guard.acquire_shared_lock():
        proc = subprocess.Popen(
            [sys.executable, "-c", child_code, str(stage15_root), "0"],
            stdout=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.25)
    try:
        assert proc.stdout.readline().strip() == "LOCKED"
        assert time.monotonic() - started >= 0.20
    finally:
        proc.wait(timeout=2)


def test_storage_guard_rejects_normal_write_outside_root_budget(tmp_path):
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
        Stage16EAStorageBlocked,
        Stage16EAStorageGuard,
    )

    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / ".stage1_5_storage_guard.lock").touch()
    guard = Stage16EAStorageGuard(
        output_root=root,
        shared_lock_path=tmp_path / ".stage1_5_storage_guard.lock",
        disk_usage_func=lambda _: (0, 0, 16 * 1024 * 1024 * 1024),
    )

    with pytest.raises(Stage16EAStorageBlocked, match="root_budget_exceeded"):
        guard.check_write_admission(
            write_class="normal_data",
            persistent_delta_bytes=16 * 1024 * 1024,
            transient_peak_bytes=16 * 1024 * 1024,
        )


def test_storage_guard_rejects_insufficient_shared_emergency_reserve(tmp_path, monkeypatch):
    from configs import base
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
        Stage16EAStorageBlocked,
        Stage16EAStorageGuard,
    )

    root = tmp_path / "root"
    root.mkdir()
    shared_lock = tmp_path / ".stage1_5_storage_guard.lock"
    shared_lock.touch()
    required = (
        base.EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        + base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        + base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        + base.EXTERNAL_SIGNAL_STAGE1_6E_A_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
    )
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES", required - 1)
    guard = Stage16EAStorageGuard(
        output_root=root,
        shared_lock_path=shared_lock,
        disk_usage_func=lambda _: (0, 0, 16 * 1024 * 1024 * 1024),
    )

    with pytest.raises(Stage16EAStorageBlocked, match="shared_emergency_reserve_insufficient"):
        guard.validate_startup_free_space()


def test_write_and_verify_complete_bundle(tmp_path):
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
        RootWriterLock,
        append_observation,
        verify_complete_bundle,
        write_atomic_json,
        write_capability_summary,
        write_manifest,
        write_raw_body,
        write_source_profile,
        write_source_profile_attestation,
        write_terminal_status,
    )

    root = tmp_path / "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"
    root.mkdir()

    # Writer lock
    writer_lock = RootWriterLock(root)
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
    attestation["execution_environment_id"] = hashlib.sha256(canonical_json(att_sans_id)).hexdigest()
    write_atomic_json(root / "execution_environment_attestation.json", attestation)

    # Profiles & Attestations
    attestation_map = {}
    for pid in PROFILE_IDS:
        core = PROFILE_CORES[pid]
        p_sha = write_source_profile(root, pid, core)
        attestation_map[pid] = p_sha
        p_att = {
            "schema_version": "stage1_6e_a_profile_attestation_v1",
            "capability_run_id": root.name,
            "market_source_profile_id": pid,
            "profile_attestation_sha256": p_sha,
            "profile_attested_at_ms": 1700000000000,
            "permissions": stage1_6e_a_permissions(),
        }
        write_source_profile_attestation(root, pid, p_att)

    # 4 observations with 2 unique raw payload bodies
    raw1 = b'{"msg":"response 1"}'
    raw2 = b'{"msg":"response 2"}'
    raw_sha1 = write_raw_body(root, raw1)
    raw_sha2 = write_raw_body(root, raw2)

    obs_ids = []
    for seq, pid in enumerate(PROFILE_IDS, start=1):
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
        append_observation(root, obs)

    # Capability summary
    summary = {
        "schema_version": "stage1_6e_a_capability_summary_v1",
        "capability_run_id": root.name,
        "profile_states": {pid: "capability_pass" for pid in PROFILE_IDS},
        "observation_ids": {pid: obs_ids[i] for i, pid in enumerate(PROFILE_IDS)},
        "historical_retention_coverage": "not_evaluable",
        "event_market_coverage": "not_evaluable",
        "fee_coverage_status": "not_evaluated_in_stage1_6e_a",
        "permissions": stage1_6e_a_permissions(),
    }
    write_capability_summary(root, summary)

    # Terminal status complete
    term = {
        "schema_version": "stage1_6e_a_terminal_status_v1",
        "capability_run_id": root.name,
        "status": "complete",
        "terminal_reason": None,
        "started_at_ms": 1700000000000,
        "terminal_at_ms": 1700000005000,
        "profile_attestation_sha256_by_id": attestation_map,
        "attempted_profile_ids": list(PROFILE_IDS),
        "passed_profile_ids": list(PROFILE_IDS),
        "accounted_root_bytes": 10000,
        "permissions": stage1_6e_a_permissions(),
    }
    write_terminal_status(root, term)

    # Manifest
    manifest_payload = {
        "schema_version": "stage1_6e_a_manifest_v1",
        "capability_run_id": root.name,
        "terminal_status_sha256": hashlib.sha256((root / "terminal_status.json").read_bytes()).hexdigest(),
        "profile_attestation_sha256_by_id": attestation_map,
        "permissions": stage1_6e_a_permissions(),
    }
    write_manifest(root, manifest_payload)

    # Verify complete bundle passes
    ok, blockers = verify_complete_bundle(root)
    assert ok is True
    assert blockers == []

    # Verify reject on extra unknown file
    extra = root / "unknown.txt"
    extra.write_text("rogue file")
    ok, blockers = verify_complete_bundle(root)
    assert ok is False
    assert "unmanifested_or_unexpected_files" in blockers
    extra.unlink()

    # A complete bundle must reject duplicate manifest paths and a missing required lock.
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    original_manifest = json.loads(json.dumps(manifest))
    manifest["authoritative_artifacts"].append(dict(manifest["authoritative_artifacts"][0]))
    manifest["authoritative_artifacts"].sort(key=lambda row: row["relative_path"])
    _refresh_manifest_id(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    ok, blockers = verify_complete_bundle(root)
    assert ok is False
    assert "authoritative_artifacts_duplicate_path" in blockers

    manifest = original_manifest
    manifest["authoritative_artifacts"].append(
        {
            "relative_path": "unknown.txt",
            "sha256": hashlib.sha256(b"rogue").hexdigest(),
            "byte_count": len(b"rogue"),
        }
    )
    manifest["authoritative_artifacts"].sort(key=lambda row: row["relative_path"])
    _refresh_manifest_id(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (root / "unknown.txt").write_bytes(b"rogue")
    ok, blockers = verify_complete_bundle(root)
    assert ok is False
    assert "authoritative_artifact_path_invalid" in blockers
    (root / "unknown.txt").unlink()

    manifest = original_manifest
    manifest["authoritative_artifacts"] = [
        row for row in manifest["authoritative_artifacts"] if row["relative_path"] != ".stage1_6e_a_writer.lock"
    ]
    _refresh_manifest_id(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (root / ".stage1_6e_a_writer.lock").unlink()
    ok, blockers = verify_complete_bundle(root)
    assert ok is False
    assert "unmanifested_or_unexpected_files" in blockers

    # Release lock
    writer_lock.release()
