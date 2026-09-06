"""Storage guard, file locks, atomic writers, and closed-tree verifier for Stage 1.6E-B."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
from pathlib import Path
from typing import Any

from configs import base
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_IDS as E_A_PROFILE_IDS,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    stage1_6e_a_permissions,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    verify_complete_bundle,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    EnvironmentAuthorityReceipt,
    canonical_json,
    sha256_hex,
    stage1_6e_b_permissions,
    validate_sha256,
)


class Stage16EBStorageBlocked(Exception):
    """Raised when storage limits or locks are breached."""
    pass


class GlobalSupervisorLock:
    def __init__(self, lock_path: Path | str):
        self.lock_path = Path(lock_path).resolve()
        self._fd: int | None = None

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            os.close(fd)
            raise Stage16EBStorageBlocked(f"lock_contention: {self.lock_path}") from exc
        self._fd = fd

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> GlobalSupervisorLock:
        self.acquire()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()


class RootWriterLock:
    def __init__(self, root_dir: Path, lock_filename: str):
        self.root_dir = Path(root_dir).resolve()
        self.lock_path = self.root_dir / lock_filename
        self._fd: int | None = None

    def acquire(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            os.close(fd)
            raise Stage16EBStorageBlocked(f"root_writer_lock_contention: {self.lock_path}") from exc
        self._fd = fd

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> RootWriterLock:
        self.acquire()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()


def write_atomic_bytes(target_path: Path, data: bytes) -> str:
    target_path = Path(target_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.parent / f".tmp_{target_path.name}_{os.getpid()}"
    fd = os.open(str(temp_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)

    os.replace(str(temp_path), str(target_path))
    read_back = target_path.read_bytes()
    if read_back != data:
        raise Stage16EBStorageBlocked(f"atomic_write_read_back_mismatch: {target_path}")
    return sha256_hex(data)


def write_atomic_json(target_path: Path, data: Any) -> str:
    payload = canonical_json(data).encode("utf-8")
    return write_atomic_bytes(target_path, payload)


def append_jsonl(target_path: Path, row: dict[str, Any]) -> str:
    target_path = Path(target_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    line = canonical_json(row) + "\n"
    line_bytes = line.encode("utf-8")

    fd = os.open(str(target_path), os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    try:
        os.write(fd, line_bytes)
        os.fsync(fd)
    finally:
        os.close(fd)

    # Read back last line to verify
    with target_path.open("rb") as f:
        f.seek(max(0, target_path.stat().st_size - len(line_bytes)))
        last_bytes = f.read()
        if last_bytes != line_bytes:
            raise Stage16EBStorageBlocked(f"append_jsonl_read_back_mismatch: {target_path}")
    return sha256_hex(line.strip().encode("utf-8"))


class Stage16EBStorageGuard:
    def __init__(
        self,
        supervisor_root: Path | None = None,
        event_root: Path | None = None,
        shared_lock_path: Path | str | None = None,
        disk_usage_func: Any = None,
    ):
        self.supervisor_root = Path(supervisor_root).resolve() if supervisor_root else None
        self.event_root = Path(event_root).resolve() if event_root else None
        self.shared_lock_path = Path(shared_lock_path).resolve() if shared_lock_path else None
        self._disk_usage_func = disk_usage_func or shutil.disk_usage

        self.host_start_free_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES
        self.host_protected_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_RUNTIME_PROTECTED_RESERVE_BYTES
        self.supervisor_max_bytes = base.EXTERNAL_SIGNAL_STAGE1_6E_B_SUPERVISOR_ROOT_MAX_BYTES
        self.event_max_bytes = base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ROOT_MAX_BYTES

    def _disk_usage_target(self) -> Path:
        target = self.event_root or self.supervisor_root or Path.cwd()
        while not target.exists() and target != target.parent:
            target = target.parent
        return target

    def _host_free_bytes(self) -> int:
        usage = self._disk_usage_func(self._disk_usage_target())
        free_val = getattr(usage, "free", None)
        if free_val is None:
            free_val = usage[2]
        return int(free_val)


    def _root_current_bytes(self, root: Path | None) -> int:
        if root is None or not root.exists():
            return 0
        return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())

    def validate_startup_free_space(self) -> None:
        free_bytes = self._host_free_bytes()
        if free_bytes < self.host_start_free_bytes:
            raise Stage16EBStorageBlocked(
                f"insufficient_host_startup_space: {free_bytes} < {self.host_start_free_bytes}"
            )

    def check_root_reserve_headroom(
        self,
        root: Path | None,
        projected_bytes: int,
        root_kind: str = "event",
    ) -> None:
        free_bytes = self._host_free_bytes()
        if free_bytes - projected_bytes < self.host_protected_reserve_bytes:
            raise Stage16EBStorageBlocked("host_protected_reserve_breached")

        target_root = root or (self.supervisor_root if root_kind == "supervisor" else self.event_root)
        curr = self._root_current_bytes(target_root)
        max_bytes = self.supervisor_max_bytes if root_kind == "supervisor" else self.event_max_bytes
        if curr + projected_bytes > max_bytes:
            raise Stage16EBStorageBlocked("root_budget_exceeded")

    def admitted_write(self, target_path: Path, data: bytes, root_kind: str) -> str:
        payload_size = len(data)
        free_bytes = self._host_free_bytes()
        if free_bytes - payload_size < self.host_protected_reserve_bytes:
            raise Stage16EBStorageBlocked("host_protected_reserve_breached")

        if root_kind == "supervisor":
            curr = self._root_current_bytes(self.supervisor_root)
            if curr + payload_size > self.supervisor_max_bytes:
                raise Stage16EBStorageBlocked("supervisor_root_budget_exceeded")
        elif root_kind == "event":
            curr = self._root_current_bytes(self.event_root)
            if curr + payload_size > self.event_max_bytes:
                raise Stage16EBStorageBlocked("root_budget_exceeded")
        else:
            raise ValueError(f"unknown_root_kind: {root_kind}")

        return write_atomic_bytes(target_path, data)


_AUTHORIZED_E_A_MANIFEST_ID = "e918b344b6781bbdb0cd005b3744acf3bb0d370e98ddd5c2973312dc974874b3"


def validate_e_a_runtime_gate(
    e_a_root: Path | str,
    *,
    step_a_projection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    e_a_root = Path(e_a_root).resolve()
    if not e_a_root.exists():
        raise Stage16EBStorageBlocked(f"e_a_root_missing: {e_a_root}")
    if e_a_root.is_symlink():
        raise Stage16EBStorageBlocked(f"e_a_root_is_symlink: {e_a_root}")

    # 1. Closed tree verification
    ok, errors = verify_complete_bundle(e_a_root)
    if not ok:
        raise Stage16EBStorageBlocked(f"e_a_bundle_invalid: {errors}")

    # 2. Manifest ID and SHA-256 verification
    manifest_path = e_a_root / "manifest.json"
    if manifest_path.is_symlink():
        raise Stage16EBStorageBlocked(f"manifest_is_symlink: {manifest_path}")
    manifest_bytes = manifest_path.read_bytes()
    manifest_data = json.loads(manifest_bytes.decode("utf-8"))
    manifest_id = manifest_data.get("manifest_id")
    if not isinstance(manifest_id, str) or not validate_sha256(manifest_id):
        raise Stage16EBStorageBlocked(f"e_a_manifest_id_invalid: {manifest_id}")

    if manifest_id != _AUTHORIZED_E_A_MANIFEST_ID:
        raise Stage16EBStorageBlocked(
            f"e_a_manifest_id_mismatch: expected {_AUTHORIZED_E_A_MANIFEST_ID}, got {manifest_id}"
        )

    manifest_sha = sha256_hex(manifest_bytes)

    # 3. Read environment attestation
    attest_path = e_a_root / "execution_environment_attestation.json"
    if attest_path.is_symlink():
        raise Stage16EBStorageBlocked(f"attestation_is_symlink: {attest_path}")
    attest_bytes = attest_path.read_bytes()
    attest_data = json.loads(attest_bytes.decode("utf-8"))
    attest_sha = sha256_hex(attest_bytes)

    # 4. PRE-ROOT EQUALITY GATE (if step_a_projection provided)
    if step_a_projection is not None:
        if step_a_projection.get("deployment_host_identity") != attest_data.get("deployment_host_identity"):
            raise Stage16EBStorageBlocked("pre_root_environment_mismatch: deployment_host_identity")
        if step_a_projection.get("project_root_realpath") != attest_data.get("project_root_realpath"):
            raise Stage16EBStorageBlocked("pre_root_environment_mismatch: project_root_realpath")
        if step_a_projection.get("network_namespace_inode") != attest_data.get("network_namespace_inode"):
            raise Stage16EBStorageBlocked("pre_root_environment_mismatch: network_namespace_inode")
        if (
            step_a_projection.get("proxy_environment") != "absent"
            or attest_data.get("proxy_environment") != "absent"
        ):
            raise Stage16EBStorageBlocked("pre_root_environment_mismatch: proxy_environment_not_absent")
        if (
            step_a_projection.get("deployment_runtime_worktree_clean") is not True
            or attest_data.get("deployment_runtime_worktree_clean") is not True
        ):
            raise Stage16EBStorageBlocked("pre_root_environment_mismatch: worktree_not_clean")
        if step_a_projection.get("capability_root_parent_filesystem_st_dev") != attest_data.get("root_filesystem_st_dev"):
            raise Stage16EBStorageBlocked("pre_root_environment_mismatch: capability_root_parent_filesystem_st_dev")
        if step_a_projection.get("shared_lock_filesystem_st_dev") != attest_data.get("shared_lock_filesystem_st_dev"):
            raise Stage16EBStorageBlocked("pre_root_environment_mismatch: shared_lock_filesystem_st_dev")

    # 5. Load 4 exact E-A profile and profile-attestation files from E-A root
    profile_cores: dict[str, dict[str, Any]] = {}
    profile_attestations: dict[str, str] = {}
    manifest_prof_att = dict(manifest_data.get("profile_attestation_sha256_by_id", {}))

    for pid in E_A_PROFILE_IDS:
        p_path = e_a_root / "source_profiles" / f"{pid}.json"
        pa_path = e_a_root / "source_profile_attestations" / f"{pid}.json"
        if not p_path.is_file() or p_path.is_symlink():
            raise Stage16EBStorageBlocked(f"e_a_profile_missing_or_symlink: {pid}")
        if not pa_path.is_file() or pa_path.is_symlink():
            raise Stage16EBStorageBlocked(f"e_a_profile_attestation_missing_or_symlink: {pid}")

        p_bytes = p_path.read_bytes()
        pa_bytes = pa_path.read_bytes()

        try:
            pa_data = json.loads(pa_bytes.decode("utf-8"))
        except Exception as exc:
            raise Stage16EBStorageBlocked(f"e_a_profile_attestation_corrupted: {pid}") from exc

        prof_att_sha = pa_data.get("profile_attestation_sha256")
        if (
            not isinstance(prof_att_sha, str)
            or not validate_sha256(prof_att_sha)
            or manifest_prof_att.get(pid) != prof_att_sha
        ):
            raise Stage16EBStorageBlocked(f"e_a_profile_attestation_hash_mismatch: {pid}")

        try:
            p_core = json.loads(p_bytes.decode("utf-8"))
        except Exception as exc:
            raise Stage16EBStorageBlocked(f"e_a_profile_corrupted: {pid}") from exc

        profile_cores[pid] = p_core
        profile_attestations[pid] = prof_att_sha

    return {
        "manifest_id": manifest_id,
        "manifest_sha256": manifest_sha,
        "manifest_bytes": manifest_bytes,
        "environment_attestation": attest_data,
        "environment_attestation_bytes": attest_bytes,
        "environment_attestation_sha256": attest_sha,
        "profile_cores": profile_cores,
        "profile_attestation_sha256_by_id": profile_attestations,
    }


def validate_post_root_equality(
    *,
    root: Path | str,
    lock_path: Path | str,
    step_a_projection: dict[str, Any],
    e_a_attestation: dict[str, Any],
) -> None:
    root = Path(root).resolve()
    lock_path = Path(lock_path).resolve()
    root_dev = os.stat(root).st_dev
    lock_dev = os.stat(lock_path).st_dev
    parent_dev = step_a_projection.get("capability_root_parent_filesystem_st_dev")
    ea_root_dev = e_a_attestation.get("root_filesystem_st_dev")
    ea_lock_dev = e_a_attestation.get("shared_lock_filesystem_st_dev")

    if not (root_dev == parent_dev == ea_root_dev == ea_lock_dev == lock_dev):
        raise Stage16EBStorageBlocked("post_root_filesystem_device_mismatch")


def write_e_b_execution_environment_attestation(
    *,
    root: Path | str,
    step_a_projection: dict[str, Any],
    deployment_git_commit: str,
    guard: Stage16EBStorageGuard | None = None,
    root_kind: str = "supervisor",
) -> tuple[dict[str, Any], str]:
    root = Path(root).resolve()
    target_file = root / "execution_environment_attestation.json"
    attestation_dict = {
        "schema_version": "stage1_6e_a_execution_environment_attestation_v1",
        "deployment_host_identity": step_a_projection["deployment_host_identity"],
        "hostname": step_a_projection["hostname"],
        "project_root_realpath": step_a_projection["project_root_realpath"],
        "root_filesystem_st_dev": os.stat(root).st_dev,
        "shared_lock_filesystem_st_dev": step_a_projection["shared_lock_filesystem_st_dev"],
        "network_namespace_inode": step_a_projection["network_namespace_inode"],
        "proxy_environment": step_a_projection["proxy_environment"],
        "runtime_user_uid": step_a_projection["runtime_user_uid"],
        "deployment_git_commit": deployment_git_commit,
        "deployment_runtime_worktree_clean": step_a_projection["deployment_runtime_worktree_clean"],
        "permissions": stage1_6e_a_permissions(),
    }
    attestation_dict["execution_environment_id"] = sha256_hex(canonical_json(attestation_dict))
    att_bytes = canonical_json(attestation_dict).encode("utf-8")
    if guard is not None:
        guard.admitted_write(target_file, att_bytes, root_kind=root_kind)
    else:
        write_atomic_bytes(target_file, att_bytes)
    read_back = target_file.read_bytes()
    read_back_sha = sha256_hex(read_back)
    return attestation_dict, read_back_sha


def write_environment_authority_receipt(
    *,
    root: Path | str,
    root_kind: str,
    e_a_manifest_id: str,
    e_a_manifest_sha256: str,
    e_a_environment_attestation_sha256: str,
    e_b_execution_environment_attestation_sha256: str,
    guard: Stage16EBStorageGuard | None = None,
) -> tuple[dict[str, Any], str]:
    root = Path(root).resolve()
    receipt = EnvironmentAuthorityReceipt.create(
        root_kind=root_kind,
        e_a_manifest_id=e_a_manifest_id,
        e_a_manifest_sha256=e_a_manifest_sha256,
        e_a_environment_attestation_sha256=e_a_environment_attestation_sha256,
        e_b_execution_environment_attestation_sha256=e_b_execution_environment_attestation_sha256,
    )
    receipt_data = receipt.to_dict()
    receipt_bytes = canonical_json(receipt_data).encode("utf-8")
    target_file = root / "environment_authority_receipt.json"
    if guard is not None:
        guard.admitted_write(target_file, receipt_bytes, root_kind=root_kind)
    else:
        write_atomic_bytes(target_file, receipt_bytes)
    read_back = target_file.read_bytes()
    read_back_sha = sha256_hex(read_back)
    return receipt_data, read_back_sha


def write_event_manifest(
    *,
    event_root: Path,
    event_id: str,
    coverage_status: str,
    event_contract_sha256: str,
    terminal_status_sha256: str,
    guard: Stage16EBStorageGuard | None = None,
) -> dict[str, Any]:
    event_root = Path(event_root).resolve()
    validate_sha256(event_id)
    validate_sha256(event_contract_sha256)
    validate_sha256(terminal_status_sha256)
    if coverage_status not in ("complete", "incomplete"):
        raise ValueError(f"invalid_coverage_status: {coverage_status}")

    files_list = []
    for root, _, files in os.walk(str(event_root)):
        for f in sorted(files):
            if f == "manifest.json" or f.startswith("temp_"):
                continue
            full_path = Path(root) / f
            if not full_path.is_file() or full_path.is_symlink():
                continue
            rel_path = full_path.relative_to(event_root).as_posix()
            data = full_path.read_bytes()
            files_list.append({
                "byte_count": len(data),
                "relative_path": rel_path,
                "sha256": sha256_hex(data),
            })

    files_list.sort(key=lambda x: x["relative_path"])

    manifest_content: dict[str, Any] = {
        "schema_version": "stage1_6e_b_event_manifest_v1",
        "event_id": event_id,
        "coverage_status": coverage_status,
        "terminal_status_sha256": terminal_status_sha256,
        "event_contract_sha256": event_contract_sha256,
        "authoritative_artifacts": files_list,
        "permissions": stage1_6e_b_permissions(),
    }
    manifest_id = sha256_hex(canonical_json(manifest_content))
    manifest_content["manifest_id"] = manifest_id

    if guard is not None:
        guard.admitted_write(
            event_root / "manifest.json",
            canonical_json(manifest_content).encode("utf-8"),
            root_kind="event",
        )
    else:
        write_atomic_json(event_root / "manifest.json", manifest_content)
    return manifest_content


def verify_event_closed_tree_manifest(event_root: Path) -> bool:
    event_root = Path(event_root).resolve()
    if event_root.is_symlink():
        raise ValueError("root_is_symlink")

    manifest_path = event_root / "manifest.json"
    if not manifest_path.exists() or manifest_path.is_symlink():
        raise ValueError("manifest_missing")

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_keys = {
        "schema_version",
        "event_id",
        "coverage_status",
        "terminal_status_sha256",
        "event_contract_sha256",
        "authoritative_artifacts",
        "permissions",
        "manifest_id",
    }
    if set(manifest_data.keys()) != expected_keys:
        raise ValueError(f"manifest_keys_mismatch: {set(manifest_data.keys()) ^ expected_keys}")

    manifest_id = manifest_data.get("manifest_id")
    raw_for_id = {k: v for k, v in manifest_data.items() if k != "manifest_id"}
    if sha256_hex(canonical_json(raw_for_id)) != manifest_id:
        raise ValueError("manifest_id_mismatch")

    if manifest_data["schema_version"] != "stage1_6e_b_event_manifest_v1":
        raise ValueError("invalid_manifest_schema_version")
    if manifest_data["coverage_status"] not in ("complete", "incomplete"):
        raise ValueError("invalid_manifest_coverage_status")
    if manifest_data["permissions"] != stage1_6e_b_permissions():
        raise ValueError("invalid_manifest_permissions")

    declared_files = {f["relative_path"]: f for f in manifest_data["authoritative_artifacts"]}
    actual_files = {}
    for root, _, files in os.walk(str(event_root)):
        for f in files:
            if f == "manifest.json" or f.startswith("temp_"):
                continue
            full_path = Path(root) / f
            if full_path.is_symlink():
                raise ValueError(f"symlink_in_tree: {full_path}")
            rel_path = full_path.relative_to(event_root).as_posix()
            actual_files[rel_path] = full_path

    if set(declared_files.keys()) != set(actual_files.keys()):
        raise ValueError(f"manifest_inventory_mismatch: {set(declared_files.keys()) ^ set(actual_files.keys())}")

    # Check ordering of declared files
    declared_paths = [f["relative_path"] for f in manifest_data["authoritative_artifacts"]]
    if declared_paths != sorted(declared_paths):
        raise ValueError("manifest_artifacts_not_sorted")

    for rel_path, meta in declared_files.items():
        actual_path = actual_files[rel_path]
        data = actual_path.read_bytes()
        if len(data) != meta["byte_count"]:
            raise ValueError(f"manifest_byte_count_mismatch: {rel_path}")
        if sha256_hex(data) != meta["sha256"]:
            raise ValueError(f"manifest_sha_mismatch: {rel_path}")

    # Terminal status validation
    if "terminal_status.json" not in declared_files:
        raise ValueError("terminal_status_not_in_manifest")
    if declared_files["terminal_status.json"]["sha256"] != manifest_data["terminal_status_sha256"]:
        raise ValueError("terminal_status_sha_mismatch")

    terminal_data = json.loads((event_root / "terminal_status.json").read_text(encoding="utf-8"))
    if terminal_data.get("status") != "complete":
        raise ValueError("manifest_only_allowed_for_complete_terminal")
    if terminal_data.get("coverage_status") != manifest_data["coverage_status"]:
        raise ValueError("terminal_and_manifest_coverage_mismatch")

    # Event contract validation
    if "event_contract.json" not in declared_files:
        raise ValueError("event_contract_not_in_manifest")
    if declared_files["event_contract.json"]["sha256"] != manifest_data["event_contract_sha256"]:
        raise ValueError("event_contract_sha_mismatch")

    return True


def probe_existing_event_writer_lock_stopped(event_dir: Path) -> bool:
    """Non-creating probe for existing .stage1_6e_b_event_writer.lock to verify writer is stopped.

    Opens existing lock file without O_CREAT/O_TRUNC/write, verifies it is regular
    and 0-byte, acquires non-blocking LOCK_EX, then unlocks and closes.
    Returns True if the lock was successfully acquired (meaning writer stopped),
    False if held, missing, symlink, non-zero size, or error.
    """
    lock_path = event_dir / ".stage1_6e_b_event_writer.lock"
    if lock_path.is_symlink() or not lock_path.is_file():
        return False
    try:
        if lock_path.stat().st_size != 0:
            return False
    except OSError:
        return False

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(lock_path), flags)
    except OSError:
        return False

    try:
        import stat
        stat_res = os.fstat(fd)
        if not stat.S_ISREG(stat_res.st_mode) or stat_res.st_size != 0:
            return False
        import fcntl
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            return False
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    finally:
        os.close(fd)
