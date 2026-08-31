import hashlib
import os
from pathlib import Path

import pytest


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


def _step_a_projection(project_root: Path) -> dict:
    audits_parent = project_root / "data/external_signal_shadow/stage1_6e/capability_audits"
    shared_lock = project_root / "data/external_signal_shadow/.stage1_5_storage_guard.lock"
    return {
        "deployment_host_identity": "0" * 64,
        "hostname": "test-vps",
        "project_root_realpath": str(project_root.resolve()),
        "capability_root_parent_filesystem_st_dev": os.stat(audits_parent).st_dev,
        "shared_lock_filesystem_st_dev": os.stat(shared_lock).st_dev,
        "network_namespace_inode": 0,
        "proxy_environment": "absent",
        "runtime_user_uid": os.geteuid(),
        "deployment_git_commit": "0" * 40,
        "deployment_runtime_worktree_clean": True,
    }


def _prepare_project_root(project_root: Path) -> None:
    (project_root / "data/external_signal_shadow/stage1_6e/capability_audits").mkdir(parents=True)
    shared_lock = project_root / "data/external_signal_shadow/.stage1_5_storage_guard.lock"
    shared_lock.touch()


def test_step_a_preflight_no_network_and_no_root(tmp_path, monkeypatch):
    import scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit as runner

    original_is_file = Path.is_file
    original_read_bytes = Path.read_bytes
    monkeypatch.setattr(
        Path,
        "is_file",
        lambda path: True if path == Path("/etc/machine-id") else original_is_file(path),
    )
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda path: b"test-machine-id" if path == Path("/etc/machine-id") else original_read_bytes(path),
    )
    original_stat = os.stat
    monkeypatch.setattr(
        runner.os,
        "stat",
        lambda path, *args, **kwargs: (
            type("Stat", (), {"st_ino": 12345})()
            if str(path) == "/proc/self/ns/net"
            else original_stat(path, *args, **kwargs)
        ),
    )
    proj = runner.get_vps_step_a_projection(project_root=Path("."))
    assert "deployment_host_identity" in proj
    assert "hostname" in proj
    assert "project_root_realpath" in proj
    assert "capability_root_parent_filesystem_st_dev" in proj
    assert "shared_lock_filesystem_st_dev" in proj
    assert proj["proxy_environment"] == "absent"
    assert isinstance(proj["deployment_runtime_worktree_clean"], bool)
    assert len(proj["deployment_git_commit"]) == 40


def test_step_a_requires_preexisting_parent_without_creating_it(tmp_path):
    from scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit import (
        get_vps_step_a_projection,
    )

    with pytest.raises(ValueError, match="capability_audits_parent_missing"):
        get_vps_step_a_projection(project_root=tmp_path)

    assert not (tmp_path / "data").exists()


def test_step_a_hashes_machine_id_raw_bytes_without_stripping(monkeypatch):
    import scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit as runner

    original_read_bytes = Path.read_bytes
    original_is_file = Path.is_file

    def fake_read_bytes(path: Path) -> bytes:
        if path == Path("/etc/machine-id"):
            return b"machine-id-with-newline\n"
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fake_read_bytes)
    monkeypatch.setattr(
        Path,
        "is_file",
        lambda path: True if path == Path("/etc/machine-id") else original_is_file(path),
    )
    original_stat = os.stat
    monkeypatch.setattr(
        runner.os,
        "stat",
        lambda path, *args, **kwargs: (
            type("Stat", (), {"st_ino": 12345})()
            if str(path) == "/proc/self/ns/net"
            else original_stat(path, *args, **kwargs)
        ),
    )
    projection = runner.get_vps_step_a_projection(project_root=Path("."))

    assert projection["deployment_host_identity"] == hashlib.sha256(
        b"machine-id-with-newline\n"
    ).hexdigest()


def test_step_a_requires_network_namespace_before_root_or_network(tmp_path, monkeypatch):
    import scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit as runner

    _prepare_project_root(tmp_path)
    original_is_file = Path.is_file
    original_exists = Path.exists
    monkeypatch.setattr(
        Path,
        "is_file",
        lambda path: True if path == Path("/etc/machine-id") else original_is_file(path),
    )
    original_read_bytes = Path.read_bytes
    monkeypatch.setattr(
        Path,
        "read_bytes",
        lambda path: b"test-machine-id" if path == Path("/etc/machine-id") else original_read_bytes(path),
    )
    monkeypatch.setattr(
        Path,
        "exists",
        lambda path: False if str(path) == "/proc/self/ns/net" else original_exists(path),
    )

    with pytest.raises(ValueError, match="network_namespace_missing"):
        runner.get_vps_step_a_projection(project_root=tmp_path)

    assert not (tmp_path / "data/external_signal_shadow/stage1_6e/capability_audits" / "new-root").exists()


def test_runner_full_successful_run(tmp_path):
    from scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit import (
        run_market_data_capability_audit,
    )
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
        verify_complete_bundle,
    )

    # Set up project structure
    project_root = tmp_path
    _prepare_project_root(project_root)
    audits_parent = project_root / "data/external_signal_shadow/stage1_6e/capability_audits"

    run_id = "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"

    step_a_proj = _step_a_projection(project_root)

    opener = MockOpenerAllSuccess()
    res = run_market_data_capability_audit(
        project_root=project_root,
        capability_run_id=run_id,
        step_a_projection=step_a_proj,
        live_public_readonly=True,
        opener=opener,
        skip_env_checks_for_test=True,
    )

    assert res["status"] == "complete"
    assert res["passed_profiles_count"] == 4

    out_root = audits_parent / run_id
    ok, blockers = verify_complete_bundle(out_root)
    assert ok is True, blockers
    assert blockers == []


def test_runner_rejects_preexisting_root_fail_closed(tmp_path):
    from scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit import (
        run_market_data_capability_audit,
    )

    project_root = tmp_path
    _prepare_project_root(project_root)
    audits_parent = project_root / "data/external_signal_shadow/stage1_6e/capability_audits"

    run_id = "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"
    existing_root = audits_parent / run_id
    existing_root.mkdir()

    step_a_proj = _step_a_projection(project_root)

    opener = MockOpenerAllSuccess()
    with pytest.raises(FileExistsError):
        run_market_data_capability_audit(
            project_root=project_root,
            capability_run_id=run_id,
            step_a_projection=step_a_proj,
            live_public_readonly=True,
            opener=opener,
            skip_env_checks_for_test=True,
        )
    assert len(opener.calls) == 0


def test_runner_rejects_incomplete_step_a_projection_before_root_or_network(tmp_path, monkeypatch):
    import scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit as runner

    _prepare_project_root(tmp_path)
    run_id = "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"
    opener = MockOpenerAllSuccess()
    monkeypatch.setattr(runner, "get_vps_step_a_projection", lambda _: _step_a_projection(tmp_path))

    with pytest.raises(ValueError, match="step_a_projection_keys_mismatch"):
        runner.run_market_data_capability_audit(
            project_root=tmp_path,
            capability_run_id=run_id,
            step_a_projection={},
            live_public_readonly=True,
            opener=opener,
        )

    assert not (tmp_path / "data/external_signal_shadow/stage1_6e/capability_audits" / run_id).exists()
    assert opener.calls == []


def test_runner_rejects_proxy_environment_before_root_or_network(tmp_path):
    from scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit import (
        run_market_data_capability_audit,
    )

    _prepare_project_root(tmp_path)
    run_id = "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"
    projection = _step_a_projection(tmp_path)
    projection["proxy_environment"] = "present"
    opener = MockOpenerAllSuccess()

    with pytest.raises(ValueError, match="step_a_projection_proxy_environment_not_absent"):
        run_market_data_capability_audit(
            project_root=tmp_path,
            capability_run_id=run_id,
            step_a_projection=projection,
            live_public_readonly=True,
            opener=opener,
        )

    assert not (tmp_path / "data/external_signal_shadow/stage1_6e/capability_audits" / run_id).exists()
    assert opener.calls == []


def test_runner_summary_write_failure_persists_failed_terminal(tmp_path, monkeypatch):
    import scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit as runner

    _prepare_project_root(tmp_path)
    run_id = "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"

    def fail_summary(*args, **kwargs):
        raise OSError("summary write blocked")

    monkeypatch.setattr(runner, "write_capability_summary", fail_summary)
    result = runner.run_market_data_capability_audit(
        project_root=tmp_path,
        capability_run_id=run_id,
        step_a_projection=_step_a_projection(tmp_path),
        live_public_readonly=True,
        opener=MockOpenerAllSuccess(),
        skip_env_checks_for_test=True,
    )

    terminal = (tmp_path / "data/external_signal_shadow/stage1_6e/capability_audits" / run_id / "terminal_status.json").read_text()
    assert result["status"] == "failed"
    assert result["terminal_reason"] == "storage_write_blocked"
    assert '"status": "failed"' in terminal
    assert '"terminal_reason": "storage_write_blocked"' in terminal


def test_runner_summary_readback_failure_persists_integrity_terminal(tmp_path, monkeypatch):
    import scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit as runner
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
        Stage16EAStorageIntegrityError,
    )

    _prepare_project_root(tmp_path)
    run_id = "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"
    monkeypatch.setattr(
        runner,
        "write_capability_summary",
        lambda *args, **kwargs: (_ for _ in ()).throw(Stage16EAStorageIntegrityError("readback")),
    )
    result = runner.run_market_data_capability_audit(
        project_root=tmp_path,
        capability_run_id=run_id,
        step_a_projection=_step_a_projection(tmp_path),
        live_public_readonly=True,
        opener=MockOpenerAllSuccess(),
        skip_env_checks_for_test=True,
    )

    assert result["status"] == "failed"
    assert result["terminal_reason"] == "local_integrity_failed"


def test_runner_terminal_write_failure_leaves_root_unsealed(tmp_path, monkeypatch):
    import scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit as runner

    _prepare_project_root(tmp_path)
    run_id = "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"
    monkeypatch.setattr(
        runner,
        "write_terminal_status",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("terminal write blocked")),
    )

    with pytest.raises(RuntimeError, match="terminal_status_persistence_failed"):
        runner.run_market_data_capability_audit(
            project_root=tmp_path,
            capability_run_id=run_id,
            step_a_projection=_step_a_projection(tmp_path),
            live_public_readonly=True,
            opener=MockOpenerAllSuccess(),
            skip_env_checks_for_test=True,
        )

    root = tmp_path / "data/external_signal_shadow/stage1_6e/capability_audits" / run_id
    assert not (root / "terminal_status.json").exists()
    assert not (root / "manifest.json").exists()


def test_runner_rejects_invalid_sealed_bundle_after_manifest(tmp_path, monkeypatch):
    import scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit as runner

    _prepare_project_root(tmp_path)
    run_id = "stage1_6e_a_capability_20260831T080000Z_0123456789abcdef0123456789abcdef"
    monkeypatch.setattr(runner, "verify_complete_bundle", lambda _: (False, ["fixture_invalid"]))

    with pytest.raises(RuntimeError, match="complete_bundle_verification_failed"):
        runner.run_market_data_capability_audit(
            project_root=tmp_path,
            capability_run_id=run_id,
            step_a_projection=_step_a_projection(tmp_path),
            live_public_readonly=True,
            opener=MockOpenerAllSuccess(),
            skip_env_checks_for_test=True,
        )
