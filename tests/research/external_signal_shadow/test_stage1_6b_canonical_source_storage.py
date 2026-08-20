"""Unit and integration tests for Stage 1.6B strict roots, guarded writes, shared locking, and checkpoint recovery."""

import fcntl
import hashlib
import os
import shutil
from pathlib import Path

import pytest

import src.research.external_signal_shadow.stage1_6b_canonical_source_storage as storage
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    SOURCE_PROFILE_ID,
    CaptureMode,
    CaptureRunContract,
    ObserverCheckpointRecord,
    TerminalReason,
    TerminalStatusRecord,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import (
    RootWriterLock,
    RootWriterLockError,
    Stage16BStorageBlocked,
    Stage16BStorageGuard,
    append_jsonl_record,
    derive_shared_storage_lock_path,
    load_sealed_export,
    reconcile_and_load_checkpoint,
    seal_export,
    validate_probe_attestation_path,
    validate_run_root_path,
    write_atomic_json,
    write_capture_run_contract,
    write_content_addressed_raw_payload,
    write_observer_checkpoint,
    write_terminal_status,
)


def create_mock_disk_usage(total_gb=30, free_gb=20):
    total = total_gb * 1024 * 1024 * 1024
    free = free_gb * 1024 * 1024 * 1024
    used = total - free
    return lambda p: shutil._ntuple_diskusage(total, used, free)


def setup_test_hierarchy(base_tmp: Path):
    """Setup data/external_signal_shadow structure in a tmp directory."""
    data_dir = base_tmp / "data" / "external_signal_shadow" / "stage1_6b"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def test_derive_shared_storage_lock_path(tmp_path):
    """Verify derivation of shared lock path matches Stage 1.5 algorithm without importing Stage 1.5 production code."""
    ext_shadow = tmp_path / "data" / "external_signal_shadow"
    run_root = ext_shadow / "stage1_6b" / "live_observation" / "run_001"
    run_root.mkdir(parents=True, exist_ok=True)

    derived = derive_shared_storage_lock_path(run_root)
    expected = ext_shadow / ".stage1_5_storage_guard.lock"
    assert derived.resolve() == expected.resolve()

    # Rejection when ancestor is missing
    bad_root = tmp_path / "other" / "run_001"
    bad_root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="output_root_missing_external_signal_shadow_ancestor"):
        derive_shared_storage_lock_path(bad_root)


def test_cross_implementation_lock_equivalence(tmp_path):
    """Verify that Stage 1.6B lock helper uses the exact lock path as Stage 1.5 StorageGuard (test-only import)."""
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    ext_shadow = tmp_path / "data" / "external_signal_shadow"
    root_1_5d = ext_shadow / "stage1_5d" / "run_d"
    root_1_5f = ext_shadow / "stage1_5f" / "run_f"
    root_1_6b = ext_shadow / "stage1_6b" / "live_observation" / "run_b"
    for r in [root_1_5d, root_1_5f, root_1_6b]:
        r.mkdir(parents=True, exist_ok=True)

    guard_d = StorageGuard(output_root=root_1_5d, stage="1.5D", disk_usage_func=create_mock_disk_usage())
    lock_1_6b = derive_shared_storage_lock_path(root_1_6b)

    assert guard_d.lock_file_path.resolve() == lock_1_6b.resolve()


def test_cross_implementation_contention(tmp_path):
    """Verify that holding the shared lock by 1.6B blocks 1.5D/F and vice versa."""
    ext_shadow = tmp_path / "data" / "external_signal_shadow"
    root_1_6b = ext_shadow / "stage1_6b" / "live_observation" / "run_b"
    root_1_6b.mkdir(parents=True, exist_ok=True)

    lock_path = derive_shared_storage_lock_path(root_1_6b)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o666)
    fcntl.flock(fd, fcntl.LOCK_EX)

    # Attempting to acquire non-blocking lock from another descriptor should fail
    fd2 = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o666)
    with pytest.raises(BlockingIOError):
        fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)

    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    os.close(fd2)


def test_validate_probe_and_run_root_paths(tmp_path):
    """Verify strict path validation for probe attestations, historical backfill, and live observation."""
    stage1_6b_dir = setup_test_hierarchy(tmp_path)

    # Valid probe path
    probe_p = stage1_6b_dir / "source_profile_attestations" / "abc123sha" / "source_profile_probe_attestation.json"
    assert validate_probe_attestation_path(probe_p, project_root=tmp_path) == probe_p.resolve()

    # Invalid probe path (wrong file name or missing parent)
    with pytest.raises(ValueError, match="invalid_probe_attestation_path"):
        validate_probe_attestation_path(stage1_6b_dir / "other.json", project_root=tmp_path)

    # Valid fresh historical root
    hist_root = stage1_6b_dir / "historical_backfill" / "run_hist_1"
    assert validate_run_root_path(hist_root, capture_mode=CaptureMode.HISTORICAL_BACKFILL.value, require_fresh=True, project_root=tmp_path) == hist_root.resolve()

    # Reject non-fresh when require_fresh=True
    hist_root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="root_already_exists"):
        validate_run_root_path(hist_root, capture_mode=CaptureMode.HISTORICAL_BACKFILL.value, require_fresh=True, project_root=tmp_path)

    # Valid fresh live root
    live_root = stage1_6b_dir / "live_observation" / "run_live_1"
    assert validate_run_root_path(live_root, capture_mode=CaptureMode.LIVE_OBSERVED.value, require_fresh=True, project_root=tmp_path) == live_root.resolve()

    # Valid resume live root (when exists)
    live_root.mkdir(parents=True, exist_ok=True)
    assert validate_run_root_path(live_root, capture_mode=CaptureMode.LIVE_OBSERVED.value, require_fresh=False, project_root=tmp_path) == live_root.resolve()

    # Reject symlink escape or wrong family
    wrong_family = stage1_6b_dir / "historical_backfill" / "run_live_wrong"
    with pytest.raises(ValueError, match="invalid_root_family"):
        validate_run_root_path(wrong_family, capture_mode=CaptureMode.LIVE_OBSERVED.value, require_fresh=True, project_root=tmp_path)


def test_guarded_writer_quota_formulas(tmp_path):
    """Verify normal, ordinary, and terminal write quota checks and fail-closed behavior."""
    stage1_6b_dir = setup_test_hierarchy(tmp_path)
    run_root = stage1_6b_dir / "live_observation" / "run_quota"
    run_root.mkdir(parents=True, exist_ok=True)

    # Normal disk usage: 20 GB free
    guard = Stage16BStorageGuard(output_root=run_root, disk_usage_func=create_mock_disk_usage(30, 20))
    guard.validate_startup_free_space()

    # Normal write within quota succeeds
    guard.check_write_admission(write_class="normal_data", persistent_delta_bytes=1000, transient_peak_bytes=2000, current_root_bytes=0)

    # Normal write exceeding root max (minus reserves) fails
    # root max 256MB, ordinary 4MB, emergency 1MB -> max normal is 251MB
    with pytest.raises(Stage16BStorageBlocked, match="root_budget_exceeded"):
        guard.check_write_admission(write_class="normal_data", persistent_delta_bytes=252 * 1024 * 1024, transient_peak_bytes=252 * 1024 * 1024, current_root_bytes=0)

    # Terminal peak > 256 KiB fails
    with pytest.raises(Stage16BStorageBlocked, match="terminal_peak_exceeded"):
        guard.check_write_admission(write_class="terminal_control_plane", persistent_delta_bytes=100, transient_peak_bytes=300 * 1024, current_root_bytes=0)

    # Host start free space < 8 GB fails startup
    guard_low_disk = Stage16BStorageGuard(output_root=run_root, disk_usage_func=create_mock_disk_usage(30, 7))
    with pytest.raises(Stage16BStorageBlocked, match="host_start_free_space_insufficient"):
        guard_low_disk.validate_startup_free_space()


def test_atomic_writer_holds_shared_lock_until_replace(tmp_path, monkeypatch):
    """Verify shared storage admission remains held through the actual atomic rename."""
    stage1_6b_dir = setup_test_hierarchy(tmp_path)
    run_root = stage1_6b_dir / "live_observation" / "run_lock_during_write"
    run_root.mkdir(parents=True, exist_ok=True)
    guard = Stage16BStorageGuard(output_root=run_root, disk_usage_func=create_mock_disk_usage(30, 20))
    original_replace = storage.os.replace

    def replace_while_asserting_lock(source, destination):
        fd = os.open(guard.lock_file_path, os.O_RDWR | os.O_CREAT, 0o666)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)
        return original_replace(source, destination)

    monkeypatch.setattr(storage.os, "replace", replace_while_asserting_lock)
    write_atomic_json(
        run_root=run_root,
        relative_path="guarded.json",
        data_dict={"value": 1},
        write_class="ordinary_control_plane",
        guard=guard,
        current_root_bytes=0,
    )


def test_lifetime_writer_lock_ownership(tmp_path):
    """Verify exclusive lifetime root writer lock behavior."""
    stage1_6b_dir = setup_test_hierarchy(tmp_path)
    run_root = stage1_6b_dir / "live_observation" / "run_lock"
    run_root.mkdir(parents=True, exist_ok=True)

    lock1 = RootWriterLock(run_root)
    lock1.acquire()

    # Second lock on same root fails immediately
    lock2 = RootWriterLock(run_root)
    with pytest.raises(RootWriterLockError, match="root_already_owned"):
        lock2.acquire()

    # After lock1 releases, lock2 can acquire
    lock1.release()
    lock2.acquire()
    lock2.release()


def test_guarded_write_primitives_inventory(tmp_path):
    """Verify that content-addressed raw write, append JSONL, atomic JSON, checkpoint, and terminal status use guard."""
    stage1_6b_dir = setup_test_hierarchy(tmp_path)
    run_root = stage1_6b_dir / "live_observation" / "run_prim"
    run_root.mkdir(parents=True, exist_ok=True)

    guard = Stage16BStorageGuard(output_root=run_root, disk_usage_func=create_mock_disk_usage(30, 20))

    # 1. Raw payload write
    payload = b"{\"test\":\"data\"}"
    raw_sha, raw_rel_path, bytes_written = write_content_addressed_raw_payload(
        run_root=run_root,
        payload_bytes=payload,
        subfolder="index",
        guard=guard,
        current_root_bytes=0,
    )
    assert (run_root / raw_rel_path).is_file()
    assert bytes_written == len(payload)

    # Duplicate raw write returns existing without extra write
    raw_sha2, raw_rel_path2, bytes_written2 = write_content_addressed_raw_payload(
        run_root=run_root,
        payload_bytes=payload,
        subfolder="index",
        guard=guard,
        current_root_bytes=bytes_written,
    )
    assert bytes_written2 == 0
    assert raw_sha2 == raw_sha

    # 2. Append JSONL
    record = {"event": "test_list_capture", "val": 42}
    delta = append_jsonl_record(
        run_root=run_root,
        relative_path="list_captures/2026-08-20.jsonl",
        record=record,
        write_class="normal_data",
        guard=guard,
        current_root_bytes=bytes_written,
    )
    assert delta > 0

    # 3. Checkpoint
    chk = ObserverCheckpointRecord(
        schema_version="stage1_6b_observer_checkpoint_v1",
        run_id="run_prim",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256="att_sha",
        checkpoint_id="chk_001",
        prior_checkpoint_id=None,
        poll_seq=1,
        monotonic_request_seq=1,
        record_seq=1,
        accounted_root_bytes=bytes_written + delta,
        stream_offsets={"list_captures/2026-08-20.jsonl": delta},
        stream_last_hashes={"list_captures/2026-08-20.jsonl": "hash1"},
        candidate_states={},
        heartbeat_at_ms=1700000000000,
    )
    chk_delta = write_observer_checkpoint(run_root, chk, guard, current_root_bytes=bytes_written + delta)
    assert (run_root / "observer_checkpoint.json").is_file()

    # 4. Terminal status
    term = TerminalStatusRecord(
        schema_version="stage1_6b_terminal_status_v1",
        run_id="run_prim",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        status="complete",
        terminal_reason=TerminalReason.EPOCH_COMPLETE.value,
        final_checkpoint_id="chk_001",
        terminated_at_ms=1700000001000,
    )
    write_terminal_status(run_root, term, guard, current_root_bytes=bytes_written + delta + chk_delta)
    assert (run_root / "terminal_status.json").is_file()


def test_checkpoint_reconciliation_and_recovery(tmp_path):
    """Verify bounded-tail reconciliation on restart, detecting extra raw or JSONL appended bytes."""
    stage1_6b_dir = setup_test_hierarchy(tmp_path)
    run_root = stage1_6b_dir / "live_observation" / "run_rec"
    run_root.mkdir(parents=True, exist_ok=True)

    guard = Stage16BStorageGuard(output_root=run_root, disk_usage_func=create_mock_disk_usage(30, 20))

    # Setup contract
    contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id="run_rec",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256="att_sha",
        run_started_at_ms=1700000000000,
    )
    write_capture_run_contract(run_root, contract, guard, 0)

    # Initial checkpoint
    chk = ObserverCheckpointRecord(
        schema_version="stage1_6b_observer_checkpoint_v1",
        run_id="run_rec",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256="att_sha",
        checkpoint_id="chk_001",
        prior_checkpoint_id=None,
        poll_seq=1,
        monotonic_request_seq=1,
        record_seq=1,
        accounted_root_bytes=100,
        stream_offsets={"list_captures/2026-08-20.jsonl": 0},
        stream_last_hashes={},
        candidate_states={},
        heartbeat_at_ms=1700000000000,
    )
    write_observer_checkpoint(run_root, chk, guard, 100)

    # Append some JSONL record after checkpoint (simulating crash before next checkpoint)
    record = {"row": 1, "content": "test"}
    append_jsonl_record(run_root, "list_captures/2026-08-20.jsonl", record, "normal_data", guard, 200)

    # Reconcile and load checkpoint
    reconciled_chk, reconciled_root_bytes = reconcile_and_load_checkpoint(run_root, guard)
    assert reconciled_chk.stream_offsets["list_captures/2026-08-20.jsonl"] > 0
    assert reconciled_root_bytes > 100


def test_checkpoint_reconciliation_verifies_prefix_hash_and_reads_only_tail(tmp_path, monkeypatch):
    """A resume must validate the committed boundary without rereading the full JSONL stream."""
    stage1_6b_dir = setup_test_hierarchy(tmp_path)
    run_root = stage1_6b_dir / "live_observation" / "run_rec_prefix"
    run_root.mkdir(parents=True, exist_ok=True)
    guard = Stage16BStorageGuard(output_root=run_root, disk_usage_func=create_mock_disk_usage(30, 20))
    stream_rel = "list_captures/2026-08-20.jsonl"
    stream_path = run_root / stream_rel
    stream_path.parent.mkdir(parents=True)
    committed_line = b'{"committed":1}\n'
    tail_line = b'{"tail":2}\n'
    stream_path.write_bytes(committed_line + tail_line)

    chk = ObserverCheckpointRecord(
        schema_version="stage1_6b_observer_checkpoint_v1",
        run_id="run_rec_prefix",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256="att_sha",
        checkpoint_id="chk_001",
        prior_checkpoint_id=None,
        poll_seq=1,
        monotonic_request_seq=1,
        record_seq=1,
        accounted_root_bytes=100,
        stream_offsets={stream_rel: len(committed_line)},
        stream_last_hashes={stream_rel: hashlib.sha256(committed_line.rstrip(b"\n")).hexdigest()},
        candidate_states={},
        heartbeat_at_ms=1700000000000,
    )
    write_observer_checkpoint(run_root, chk, guard, 100)

    original_read_text = Path.read_text

    def reject_full_stream_read(path, *args, **kwargs):
        if path == stream_path:
            raise AssertionError("resume_must_not_read_entire_committed_stream")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", reject_full_stream_read)
    reconciled, _ = reconcile_and_load_checkpoint(run_root, guard)
    assert reconciled.stream_offsets[stream_rel] == len(committed_line + tail_line)
    assert reconciled.stream_last_hashes[stream_rel] == hashlib.sha256(tail_line.rstrip(b"\n")).hexdigest()

    bad_chk = ObserverCheckpointRecord(
        **{**chk.to_dict(), "stream_last_hashes": {stream_rel: "0" * 64}}
    )
    write_observer_checkpoint(run_root, bad_chk, guard, 100)
    with pytest.raises(ValueError, match="checkpoint_prefix_hash_mismatch"):
        reconcile_and_load_checkpoint(run_root, guard)



def test_seal_export_and_load_sealed_export(tmp_path):
    """Verify sealed export creation with streaming guarded copy and independent consumer verification."""
    stage1_6b_dir = setup_test_hierarchy(tmp_path)
    run_root = stage1_6b_dir / "live_observation" / "run_seal_ok"
    run_root.mkdir(parents=True, exist_ok=True)

    guard = Stage16BStorageGuard(output_root=run_root, disk_usage_func=create_mock_disk_usage(30, 20))

    # Setup run contract, attestation, raw payloads, records, checkpoint, terminal status
    contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id="run_seal_ok",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256="att_sha_123",
        run_started_at_ms=1700000000000,
    )
    b0 = write_capture_run_contract(run_root, contract, guard, 0)

    raw_sha, raw_rel, b1 = write_content_addressed_raw_payload(
        run_root, b"{\"test\":1}", "index", guard, b0
    )

    b2 = append_jsonl_record(
        run_root, "list_captures/2026-08-20.jsonl", {"raw_sha": raw_sha}, "normal_data", guard, b0 + b1
    )

    chk = ObserverCheckpointRecord(
        schema_version="stage1_6b_observer_checkpoint_v1",
        run_id="run_seal_ok",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256="att_sha_123",
        checkpoint_id="chk_final_1",
        prior_checkpoint_id=None,
        poll_seq=1,
        monotonic_request_seq=1,
        record_seq=1,
        accounted_root_bytes=b0 + b1 + b2,
        stream_offsets={},
        stream_last_hashes={},
        candidate_states={},
        heartbeat_at_ms=1700000000000,
    )
    b3 = write_observer_checkpoint(run_root, chk, guard, b0 + b1 + b2)

    term = TerminalStatusRecord(
        schema_version="stage1_6b_terminal_status_v1",
        run_id="run_seal_ok",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        status="complete",
        terminal_reason=TerminalReason.EPOCH_COMPLETE.value,
        final_checkpoint_id="chk_final_1",
        terminated_at_ms=1700000001000,
    )
    b4 = write_terminal_status(run_root, term, guard, b0 + b1 + b2 + b3)

    # Execute seal
    export_dir, manifest, added_bytes = seal_export(run_root, guard, b0 + b1 + b2 + b3 + b4)
    assert export_dir.is_dir()
    assert (export_dir / "sealed_export_manifest.json").is_file()

    # Load and verify export through independent consumer validator
    loaded = load_sealed_export(export_dir)
    assert loaded["export_id"] == manifest.export_id
    assert loaded["status"] == "complete"
    assert loaded["capture_mode"] == CaptureMode.LIVE_OBSERVED.value
    assert len(loaded["authoritative_artifacts"]) >= 4


def test_seal_export_rejects_incomplete_root(tmp_path):
    """Verify seal_export refuses to seal when terminal status is absent or failure."""
    stage1_6b_dir = setup_test_hierarchy(tmp_path)
    run_root = stage1_6b_dir / "live_observation" / "run_incomplete"
    run_root.mkdir(parents=True, exist_ok=True)

    guard = Stage16BStorageGuard(output_root=run_root, disk_usage_func=create_mock_disk_usage(30, 20))

    # Missing terminal status -> raises ValueError
    with pytest.raises(ValueError, match="terminal_status_missing_or_failed"):
        seal_export(run_root, guard, 0)
