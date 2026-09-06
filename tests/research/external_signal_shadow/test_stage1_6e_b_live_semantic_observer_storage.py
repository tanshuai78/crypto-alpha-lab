"""Tests for Stage 1.6E-B storage guard, locks, atomic writers, and E-A gate."""

import json
from pathlib import Path

import pytest

import src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage as storage_module
from configs import base
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    sha256_hex,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage import (
    GlobalSupervisorLock,
    RootWriterLock,
    Stage16EBStorageBlocked,
    Stage16EBStorageGuard,
    append_jsonl,
    probe_existing_event_writer_lock_stopped,
    validate_e_a_runtime_gate,
    verify_event_closed_tree_manifest,
    write_atomic_bytes,
    write_atomic_json,
    write_event_manifest,
)


def test_locks_acquisition_and_contention(tmp_path: Path):
    lock_file = tmp_path / ".test_supervisor.lock"
    lock1 = GlobalSupervisorLock(lock_file)
    lock1.acquire()

    # Second lock on same file must raise contention
    lock2 = GlobalSupervisorLock(lock_file)
    with pytest.raises(Stage16EBStorageBlocked, match="lock_contention"):
        lock2.acquire()

    lock1.release()
    # Now lock2 can acquire
    lock2.acquire()
    lock2.release()


def test_root_writer_lock_inside_root(tmp_path: Path):
    root_dir = tmp_path / "event_root"
    root_dir.mkdir()
    lock = RootWriterLock(root_dir, ".stage1_6e_b_event_writer.lock")
    with lock:
        assert (root_dir / ".stage1_6e_b_event_writer.lock").exists()
        lock2 = RootWriterLock(root_dir, ".stage1_6e_b_event_writer.lock")
        with pytest.raises(Stage16EBStorageBlocked, match="root_writer_lock_contention"):
            lock2.acquire()


def test_atomic_writers_and_jsonl(tmp_path: Path):
    json_path = tmp_path / "test.json"
    data = {"hello": "world", "num": 123}
    write_atomic_json(json_path, data)
    assert json_path.exists()
    assert json_path.read_text().strip() == '{"hello":"world","num":123}'

    # Bytes
    bytes_path = tmp_path / "test.bin"
    raw = b"binary_content_12345"
    sha = write_atomic_bytes(bytes_path, raw)
    assert bytes_path.read_bytes() == raw
    assert len(sha) == 64

    # JSONL
    jsonl_path = tmp_path / "test.jsonl"
    append_jsonl(jsonl_path, {"row": 1})
    append_jsonl(jsonl_path, {"row": 2})
    lines = [line.strip() for line in jsonl_path.read_text().splitlines() if line.strip()]
    assert len(lines) == 2
    assert lines[0] == '{"row":1}'
    assert lines[1] == '{"row":2}'


def test_storage_guard_budget_and_admitted_write(tmp_path: Path):
    shared_lock = tmp_path / ".stage1_5_storage_guard.lock"
    shared_lock.touch()

    # Mock disk usage: enough host space
    class MockUsage:
        free = 10 * 1024 * 1024 * 1024  # 10 GiB

    guard = Stage16EBStorageGuard(
        supervisor_root=tmp_path / "supervisor",
        event_root=tmp_path / "event",
        shared_lock_path=shared_lock,
        disk_usage_func=lambda _: MockUsage(),
    )
    guard.validate_startup_free_space()

    # Writing within limit
    target_file = tmp_path / "event" / "test.txt"
    guard.admitted_write(target_file, b"data", root_kind="event")
    assert target_file.read_bytes() == b"data"

    # Exceeding root limit
    big_payload = b"x" * (base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ROOT_MAX_BYTES + 10)
    with pytest.raises(Stage16EBStorageBlocked, match="root_budget_exceeded"):
        guard.admitted_write(target_file, big_payload, root_kind="event")


def test_event_manifest_closed_tree(tmp_path: Path):
    event_dir = tmp_path / "event_1"
    event_dir.mkdir()

    contract_bytes = b'{"a":1}'
    (event_dir / "event_contract.json").write_bytes(contract_bytes)
    contract_sha = sha256_hex(contract_bytes)

    event_id = "e" * 64
    terminal_bytes = json.dumps({
        "status": "complete",
        "coverage_status": "complete",
        "event_id": event_id,
    }).encode("utf-8")
    (event_dir / "terminal_status.json").write_bytes(terminal_bytes)
    terminal_sha = sha256_hex(terminal_bytes)

    manifest_dict = write_event_manifest(
        event_root=event_dir,
        event_id=event_id,
        coverage_status="complete",
        event_contract_sha256=contract_sha,
        terminal_status_sha256=terminal_sha,
    )

    manifest_path = event_dir / "manifest.json"
    assert manifest_path.exists()
    assert manifest_dict["coverage_status"] == "complete"

    # Verify complete closed tree passes
    assert verify_event_closed_tree_manifest(event_dir) is True

    # Tamper: add untracked file
    (event_dir / "untracked.tmp").write_text("evil")
    with pytest.raises(ValueError, match="manifest_inventory_mismatch"):
        verify_event_closed_tree_manifest(event_dir)


def test_validate_e_a_runtime_gate_missing_or_corrupt(tmp_path: Path):
    non_existent = tmp_path / "non_existent_ea_root"
    with pytest.raises(Stage16EBStorageBlocked, match="e_a_root_missing"):
        validate_e_a_runtime_gate(non_existent)

    empty_dir = tmp_path / "empty_ea_root"
    empty_dir.mkdir()
    with pytest.raises(Stage16EBStorageBlocked, match="e_a_bundle_invalid"):
        validate_e_a_runtime_gate(empty_dir)


class MockOpenerAllSuccess:
    def __init__(self):
        self.calls = []

    def open(self, req, timeout=10.0):
        url = req.full_url
        self.calls.append(url)

        class Resp:
            def __init__(self, body):
                self.status = 200
                self.headers = {"Content-Type": "application/json"}
                self._body = body
                self._pos = 0

            def read(self, amt=None):
                if amt is None:
                    return self._body
                res = self._body[self._pos : self._pos + amt]
                self._pos += len(res)
                return res

            def close(self):
                pass

        if "depth" in url:
            body = b'{"lastUpdateId":100,"E":1700000000100,"T":1700000000000,"bids":[["60000.00","1.000"]],"asks":[["60010.00","1.000"]]}'
        elif "premiumIndex" in url:
            body = b'{"symbol":"BTCUSDT","markPrice":"60000.00","indexPrice":"59995.00","estimatedSettlePrice":"60000.00","lastFundingRate":"0.00010000","interestRate":"0.00010000","nextFundingTime":1700000000000,"time":1700000000000}'
        elif "fundingRate" in url:
            body = b'[{"symbol":"BTCUSDT","fundingRate":"0.00010000","fundingTime":1700000000000,"markPrice":"60000.00","rateType":"Regular"}]'
        elif "openInterestHist" in url:
            body = b'[{"symbol":"BTCUSDT","sumOpenInterest":"1000.000","sumOpenInterestValue":"60000000.00","timestamp":1700000000000}]'
        else:
            body = b'{}'
        return Resp(body)


def _build_canonical_ea_bundle(tmp_path: Path) -> tuple[Path, dict]:
    import os

    from scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit import (
        run_market_data_capability_audit,
    )

    proj = tmp_path / "mock_project"
    proj.mkdir(parents=True, exist_ok=True)
    audits_parent = proj / "data/external_signal_shadow/stage1_6e/capability_audits"
    audits_parent.mkdir(parents=True, exist_ok=True)
    shared_lock = proj / "data/external_signal_shadow/.stage1_5_storage_guard.lock"
    shared_lock.touch()

    step_a_proj = {
        "deployment_host_identity": "0" * 64,
        "hostname": "test-vps",
        "project_root_realpath": str(proj.resolve()),
        "capability_root_parent_filesystem_st_dev": os.stat(audits_parent).st_dev,
        "shared_lock_filesystem_st_dev": os.stat(shared_lock).st_dev,
        "network_namespace_inode": 12345,
        "proxy_environment": "absent",
        "runtime_user_uid": os.geteuid(),
        "deployment_git_commit": "a" * 40,
        "deployment_runtime_worktree_clean": True,
    }

    run_id = "stage1_6e_a_capability_20260903T073227Z_c431d5be400aabe216f15c6bf6bee48f"
    res = run_market_data_capability_audit(
        project_root=proj,
        capability_run_id=run_id,
        step_a_projection=step_a_proj,
        live_public_readonly=True,
        opener=MockOpenerAllSuccess(),
        skip_env_checks_for_test=True,
    )
    return Path(res["output_root"]), step_a_proj


def test_validate_e_a_runtime_gate_canonical_bundle_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    ea_root, step_a_proj = _build_canonical_ea_bundle(tmp_path)
    manifest_data = json.loads((ea_root / "manifest.json").read_text(encoding="utf-8"))
    manifest_id = manifest_data["manifest_id"]

    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
        PROFILE_IDS as E_A_PROFILE_IDS,
    )

    monkeypatch.setattr(storage_module, "_AUTHORIZED_E_A_MANIFEST_ID", manifest_id)
    info = validate_e_a_runtime_gate(ea_root, step_a_projection=step_a_proj)
    assert info["manifest_id"] == manifest_id
    assert len(info["profile_cores"]) == 4
    for pid in E_A_PROFILE_IDS:
        assert pid in info["profile_cores"]
        assert pid in info["profile_attestation_sha256_by_id"]


def test_validate_e_a_runtime_gate_pre_root_equality_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    ea_root, step_a_proj = _build_canonical_ea_bundle(tmp_path)
    manifest_data = json.loads((ea_root / "manifest.json").read_text(encoding="utf-8"))
    manifest_id = manifest_data["manifest_id"]

    # 1. Manifest ID mismatch
    monkeypatch.setattr(storage_module, "_AUTHORIZED_E_A_MANIFEST_ID", "f" * 64)
    with pytest.raises(Stage16EBStorageBlocked, match="e_a_manifest_id_mismatch"):
        validate_e_a_runtime_gate(ea_root, step_a_projection=step_a_proj)
    monkeypatch.setattr(storage_module, "_AUTHORIZED_E_A_MANIFEST_ID", manifest_id)

    # 2. Host identity mismatch
    bad_proj = dict(step_a_proj, deployment_host_identity="1" * 64)
    with pytest.raises(Stage16EBStorageBlocked, match="pre_root_environment_mismatch"):
        validate_e_a_runtime_gate(ea_root, step_a_projection=bad_proj)

    # 3. Project root realpath mismatch
    bad_proj = dict(step_a_proj, project_root_realpath="/wrong/path")
    with pytest.raises(Stage16EBStorageBlocked, match="pre_root_environment_mismatch"):
        validate_e_a_runtime_gate(ea_root, step_a_projection=bad_proj)

    # 4. Netns inode mismatch
    bad_proj = dict(step_a_proj, network_namespace_inode=99999)
    with pytest.raises(Stage16EBStorageBlocked, match="pre_root_environment_mismatch"):
        validate_e_a_runtime_gate(ea_root, step_a_projection=bad_proj)

    # 5. Proxy environment not absent
    bad_proj = dict(step_a_proj, proxy_environment="present")
    with pytest.raises(Stage16EBStorageBlocked, match="pre_root_environment_mismatch"):
        validate_e_a_runtime_gate(ea_root, step_a_projection=bad_proj)

    # 6. Worktree not clean
    bad_proj = dict(step_a_proj, deployment_runtime_worktree_clean=False)
    with pytest.raises(Stage16EBStorageBlocked, match="pre_root_environment_mismatch"):
        validate_e_a_runtime_gate(ea_root, step_a_projection=bad_proj)

    # 7. capability_root_parent_filesystem_st_dev mismatch
    bad_proj = dict(step_a_proj, capability_root_parent_filesystem_st_dev=-999)
    with pytest.raises(Stage16EBStorageBlocked, match="pre_root_environment_mismatch"):
        validate_e_a_runtime_gate(ea_root, step_a_projection=bad_proj)

    # 8. shared_lock_filesystem_st_dev mismatch
    bad_proj = dict(step_a_proj, shared_lock_filesystem_st_dev=-999)
    with pytest.raises(Stage16EBStorageBlocked, match="pre_root_environment_mismatch"):
        validate_e_a_runtime_gate(ea_root, step_a_projection=bad_proj)


def test_post_root_equality_and_attestation_receipt(tmp_path: Path):
    from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage import (
        validate_post_root_equality,
        write_e_b_execution_environment_attestation,
        write_environment_authority_receipt,
    )

    ea_root, step_a_proj = _build_canonical_ea_bundle(tmp_path)
    ea_attest_data = json.loads((ea_root / "execution_environment_attestation.json").read_text(encoding="utf-8"))

    e_b_root = tmp_path / "mock_eb_root"
    e_b_root.mkdir()
    lock_file = e_b_root / ".test.lock"
    lock_file.touch()

    # Success case
    validate_post_root_equality(
        root=e_b_root,
        lock_path=lock_file,
        step_a_projection=step_a_proj,
        e_a_attestation=ea_attest_data,
    )

    # Mismatch case: fake projection with different dev
    bad_proj = dict(step_a_proj, capability_root_parent_filesystem_st_dev=999999)
    with pytest.raises(Stage16EBStorageBlocked, match="post_root_filesystem_device_mismatch"):
        validate_post_root_equality(
            root=e_b_root,
            lock_path=lock_file,
            step_a_projection=bad_proj,
            e_a_attestation=ea_attest_data,
        )

    # Write E-B attestation: verifies E-B builds its own attestation
    attest_dict, attest_sha = write_e_b_execution_environment_attestation(
        root=e_b_root,
        step_a_projection=step_a_proj,
        deployment_git_commit="c" * 40,
        root_kind="supervisor",
    )
    assert attest_dict["schema_version"] == "stage1_6e_a_execution_environment_attestation_v1"
    assert attest_dict["deployment_git_commit"] == "c" * 40
    assert (e_b_root / "execution_environment_attestation.json").is_file()
    assert sha256_hex((e_b_root / "execution_environment_attestation.json").read_bytes()) == attest_sha

    # Write receipt: binds exact read-back SHA values
    ea_attest_sha = sha256_hex((ea_root / "execution_environment_attestation.json").read_bytes())
    manifest_bytes = (ea_root / "manifest.json").read_bytes()
    ea_manifest_sha = sha256_hex(manifest_bytes)
    ea_manifest_id = json.loads(manifest_bytes.decode("utf-8"))["manifest_id"]

    receipt_dict, receipt_sha = write_environment_authority_receipt(
        root=e_b_root,
        root_kind="supervisor",
        e_a_manifest_id=ea_manifest_id,
        e_a_manifest_sha256=ea_manifest_sha,
        e_a_environment_attestation_sha256=ea_attest_sha,
        e_b_execution_environment_attestation_sha256=attest_sha,
    )
    assert receipt_dict["schema_version"] == "stage1_6e_b_environment_authority_receipt_v1"
    assert receipt_dict["root_kind"] == "supervisor"
    assert (e_b_root / "environment_authority_receipt.json").is_file()
    assert sha256_hex((e_b_root / "environment_authority_receipt.json").read_bytes()) == receipt_sha


def test_probe_existing_event_writer_lock_stopped(tmp_path: Path):
    event_dir = tmp_path / "event_1"
    event_dir.mkdir(parents=True, exist_ok=True)
    lock_path = event_dir / ".stage1_6e_b_event_writer.lock"

    # 1. Missing lock file -> returns False, does NOT create it
    assert not probe_existing_event_writer_lock_stopped(event_dir)
    assert not lock_path.exists()

    # 2. Symlink lock file -> returns False
    real_lock = tmp_path / "real_lock"
    real_lock.touch()
    lock_path.symlink_to(real_lock)
    assert not probe_existing_event_writer_lock_stopped(event_dir)
    lock_path.unlink()

    # 3. Nonzero byte size -> returns False
    lock_path.write_bytes(b"non-zero-lock-content")
    assert not probe_existing_event_writer_lock_stopped(event_dir)
    lock_path.unlink()

    # 4. Regular 0-byte lock, but currently held -> returns False
    lock_path.touch()
    with RootWriterLock(event_dir, ".stage1_6e_b_event_writer.lock"):
        assert not probe_existing_event_writer_lock_stopped(event_dir)

    # 5. Regular 0-byte lock, unheld -> returns True, file unchanged
    stat_before = lock_path.stat()
    assert probe_existing_event_writer_lock_stopped(event_dir)
    stat_after = lock_path.stat()
    assert stat_after.st_size == 0
    assert stat_after.st_ino == stat_before.st_ino

