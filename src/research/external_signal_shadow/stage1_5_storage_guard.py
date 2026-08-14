"""Stage 1.5 Storage Guard and Lifecycle Resource Control TCB.

# ponytail: flock assumes local filesystem; NFS/SMB not supported; use per-root locks only if measured throughput requires them
"""

import fcntl
import os
import pathlib
import shutil
import time
from typing import Any, Callable, Dict, Literal, Optional

from configs import base

ArtifactClass = Literal["normal_data", "ordinary_control_plane", "terminal_control_plane"]


class StorageWriteBlocked(RuntimeError):
    def __init__(self, storage_guard: Any, result: Dict[str, Any]):
        self.storage_guard = storage_guard
        self.result = dict(result)
        self.storage_blocker = str(result.get("storage_blocker") or result.get("status") or "storage_write_blocked")
        super().__init__(f"storage_write_blocked:{self.storage_blocker}")


def require_storage_write(storage_guard: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    if result.get("status") != "ready" or not result.get("written", False):
        raise StorageWriteBlocked(storage_guard, result)
    return result


def terminal_write_set_peak_bytes(artifacts: list[bytes]) -> int:
    persistent_bytes = 0
    peak_bytes = 0
    for artifact in artifacts:
        peak_bytes = max(peak_bytes, persistent_bytes + len(artifact))
        persistent_bytes += len(artifact)
    return peak_bytes


class StorageGuard:
    def __init__(
        self,
        output_root: str | pathlib.Path,
        stage: Literal["1.5D", "1.5F"],
        disk_usage_func: Optional[Callable[[pathlib.Path], Any]] = None,
        terminal_write_set_peak_bytes: Optional[int] = None,
    ):
        self.output_root = pathlib.Path(output_root).resolve()
        self.stage = stage
        self._disk_usage_func = disk_usage_func or (lambda p: shutil.disk_usage(p))

        # Load limits based on stage
        if stage == "1.5D":
            self.root_max_bytes = base.EXTERNAL_SIGNAL_STAGE1_5D_ROOT_MAX_BYTES
            self.root_ordinary_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5D_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES
            self.root_emergency_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5D_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES
            self.terminal_write_set_cap_bytes = base.EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        elif stage == "1.5F":
            self.root_max_bytes = base.EXTERNAL_SIGNAL_STAGE1_5F_ROOT_MAX_BYTES
            self.root_ordinary_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5F_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES
            self.root_emergency_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5F_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES
            self.terminal_write_set_cap_bytes = base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        else:
            raise ValueError(f"Unsupported stage: {stage}")

        self.host_start_free_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES
        self.host_runtime_protected_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_RUNTIME_PROTECTED_RESERVE_BYTES
        self.host_ordinary_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_ORDINARY_CONTROL_PLANE_RESERVE_BYTES
        self.host_emergency_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES

        self.terminal_write_set_peak_bytes = (
            terminal_write_set_peak_bytes if terminal_write_set_peak_bytes is not None else self.terminal_write_set_cap_bytes
        )

        # Lock file setup
        lock_dir = pathlib.Path("data/external_signal_shadow").resolve()
        lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file_path = lock_dir / ".stage1_5_storage_guard.lock"

        self._accounted_root_bytes = 0
        self._scanned_at_ms = 0
        self._scan_root()

    def _acquire_lock(self):
        fd = os.open(self.lock_file_path, os.O_RDWR | os.O_CREAT, 0o666)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd

    def _release_lock(self, fd: int):
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _get_disk_free(self) -> int:
        parent = self.output_root
        while not parent.exists() and parent.parent != parent:
            parent = parent.parent
        usage = self._disk_usage_func(parent)
        return usage.free

    def _scan_root(self):
        total = 0
        if self.output_root.exists():
            for dirpath, _, filenames in os.walk(self.output_root):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
        self._accounted_root_bytes = total
        self._scanned_at_ms = int(time.time() * 1000)

    def scan_reconcile(self):
        fd = self._acquire_lock()
        try:
            self._scan_root()
        finally:
            self._release_lock(fd)

    def validate_startup(self) -> Dict[str, Any]:
        fd = self._acquire_lock()
        try:
            return self._status_snapshot_locked(enforce_start_free_bytes=True)
        finally:
            self._release_lock(fd)

    def status_snapshot(self) -> Dict[str, Any]:
        """Return current guarded storage facts without authorizing a write."""
        fd = self._acquire_lock()
        try:
            return self._status_snapshot_locked(enforce_start_free_bytes=False)
        finally:
            self._release_lock(fd)

    def _status_snapshot_locked(self, *, enforce_start_free_bytes: bool) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        self._scan_root()
        free_bytes = self._get_disk_free()

        if self.terminal_write_set_peak_bytes > self.terminal_write_set_cap_bytes:
            return self._storage_status(
                "blocked_start_terminal_peak_exceeded",
                f"terminal_write_set_peak_{self.terminal_write_set_peak_bytes}_exceeds_cap_{self.terminal_write_set_cap_bytes}",
                now_ms,
                free_bytes,
            )

        terminal_caps_total = (
            base.EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
            + base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        )
        if self.host_emergency_reserve_bytes < terminal_caps_total:
            return self._storage_status(
                "blocked_start_host_terminal_reserve",
                (
                    f"host_emergency_reserve_{self.host_emergency_reserve_bytes}_below_"
                    f"d_plus_f_terminal_caps_{terminal_caps_total}"
                ),
                now_ms,
                free_bytes,
            )

        if enforce_start_free_bytes and free_bytes < self.host_start_free_bytes:
            return self._storage_status(
                "blocked_start_free_space",
                f"free_bytes_{free_bytes}_below_start_threshold_{self.host_start_free_bytes}",
                now_ms,
                free_bytes,
            )

        if self._accounted_root_bytes >= self.root_max_bytes:
            return self._storage_status(
                "blocked_start_root_budget",
                f"root_bytes_{self._accounted_root_bytes}_exceeds_max_{self.root_max_bytes}",
                now_ms,
                free_bytes,
            )

        return self._storage_status("ready", None, now_ms, free_bytes)

    def _storage_status(
        self,
        status: str,
        blocker: str | None,
        now_ms: int,
        free_bytes: int,
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "storage_blocker": blocker,
            "storage_guard_status": status,
            "storage_guard_checked_at_ms": now_ms,
            "storage_free_bytes": free_bytes,
            "storage_root_bytes": self._accounted_root_bytes,
            "storage_root_scanned_at_ms": self._scanned_at_ms,
            "storage_root_max_bytes": self.root_max_bytes,
            "request_manifest_persistence_unknown": False,
            "storage_terminal_write_set_peak_bytes": self.terminal_write_set_peak_bytes,
            "storage_emergency_blocker_reserve_bytes": self.root_emergency_reserve_bytes,
        }

    def reserve_and_write(
        self,
        artifact_class: ArtifactClass,
        transient_peak_bytes: int,
        persistent_delta_bytes: int,
        write_func: Callable[[], Any],
    ) -> Dict[str, Any]:
        fd = self._acquire_lock()
        try:
            now_ms = int(time.time() * 1000)
            free_bytes = self._get_disk_free()

            if transient_peak_bytes < max(0, persistent_delta_bytes):
                transient_peak_bytes = max(0, persistent_delta_bytes)

            if (
                artifact_class == "terminal_control_plane"
                and transient_peak_bytes > self.terminal_write_set_cap_bytes
            ):
                return {
                    "status": "blocked_terminal_peak_exceeded",
                    "written": False,
                    "storage_blocker": (
                        f"terminal_peak_{transient_peak_bytes}_exceeds_cap_"
                        f"{self.terminal_write_set_cap_bytes}"
                    ),
                    "storage_guard_status": "blocked_terminal_peak_exceeded",
                    "storage_guard_checked_at_ms": now_ms,
                    "storage_free_bytes": free_bytes,
                    "storage_root_bytes": self._accounted_root_bytes,
                    "storage_root_scanned_at_ms": self._scanned_at_ms,
                    "storage_root_max_bytes": self.root_max_bytes,
                    "request_manifest_persistence_unknown": False,
                    "storage_terminal_write_set_peak_bytes": self.terminal_write_set_peak_bytes,
                    "storage_emergency_blocker_reserve_bytes": self.root_emergency_reserve_bytes,
                }

            # Check reservation limits according to artifact class
            if artifact_class == "normal_data":
                root_ok = (
                    (self._accounted_root_bytes + transient_peak_bytes)
                    <= (self.root_max_bytes - self.root_ordinary_reserve_bytes - self.root_emergency_reserve_bytes)
                )
                host_ok = (
                    (free_bytes - transient_peak_bytes)
                    >= (self.host_runtime_protected_reserve_bytes + self.host_ordinary_reserve_bytes + self.host_emergency_reserve_bytes)
                )
            elif artifact_class == "ordinary_control_plane":
                root_ok = (
                    (self._accounted_root_bytes + transient_peak_bytes)
                    <= (self.root_max_bytes - self.root_emergency_reserve_bytes)
                )
                host_ok = (
                    (free_bytes - transient_peak_bytes)
                    >= (self.host_runtime_protected_reserve_bytes + self.host_emergency_reserve_bytes)
                )
            elif artifact_class == "terminal_control_plane":
                root_ok = (self._accounted_root_bytes + transient_peak_bytes) <= self.root_max_bytes
                host_ok = (free_bytes - transient_peak_bytes) >= self.host_runtime_protected_reserve_bytes
            else:
                raise ValueError(f"Unknown artifact class: {artifact_class}")

            if not root_ok:
                return {
                    "status": "blocked_root_budget",
                    "written": False,
                    "storage_blocker": f"root_budget_exceeded_for_{artifact_class}",
                    "storage_guard_status": "blocked_root_budget",
                    "storage_guard_checked_at_ms": now_ms,
                    "storage_free_bytes": free_bytes,
                    "storage_root_bytes": self._accounted_root_bytes,
                    "storage_root_scanned_at_ms": self._scanned_at_ms,
                    "storage_root_max_bytes": self.root_max_bytes,
                    "request_manifest_persistence_unknown": False,
                    "storage_terminal_write_set_peak_bytes": self.terminal_write_set_peak_bytes,
                    "storage_emergency_blocker_reserve_bytes": self.root_emergency_reserve_bytes,
                }

            if not host_ok:
                return {
                    "status": "blocked_runtime_reserve",
                    "written": False,
                    "storage_blocker": f"host_runtime_reserve_exceeded_for_{artifact_class}",
                    "storage_guard_status": "blocked_runtime_reserve",
                    "storage_guard_checked_at_ms": now_ms,
                    "storage_free_bytes": free_bytes,
                    "storage_root_bytes": self._accounted_root_bytes,
                    "storage_root_scanned_at_ms": self._scanned_at_ms,
                    "storage_root_max_bytes": self.root_max_bytes,
                    "request_manifest_persistence_unknown": False,
                    "storage_terminal_write_set_peak_bytes": self.terminal_write_set_peak_bytes,
                    "storage_emergency_blocker_reserve_bytes": self.root_emergency_reserve_bytes,
                }

            # Directory creation and the write share the same reservation boundary.
            try:
                self.output_root.mkdir(parents=True, exist_ok=True)
                res = write_func()
            except OSError as exc:
                errno_value = exc.errno if exc.errno is not None else "unknown"
                return {
                    "status": "blocked_write_oserror",
                    "written": False,
                    "storage_blocker": f"write_oserror_errno_{errno_value}",
                    "storage_guard_status": "blocked_write_oserror",
                    "storage_guard_checked_at_ms": now_ms,
                    "storage_free_bytes": free_bytes,
                    "storage_root_bytes": self._accounted_root_bytes,
                    "storage_root_scanned_at_ms": self._scanned_at_ms,
                    "storage_root_max_bytes": self.root_max_bytes,
                    "request_manifest_persistence_unknown": False,
                    "storage_terminal_write_set_peak_bytes": self.terminal_write_set_peak_bytes,
                    "storage_emergency_blocker_reserve_bytes": self.root_emergency_reserve_bytes,
                }

            # Update accounted bytes
            self._accounted_root_bytes = max(0, self._accounted_root_bytes + persistent_delta_bytes)

            return {
                "status": "ready",
                "written": True,
                "write_result": res,
                "storage_blocker": None,
                "storage_guard_status": "ready",
                "storage_guard_checked_at_ms": now_ms,
                "storage_free_bytes": free_bytes,
                "storage_root_bytes": self._accounted_root_bytes,
                "storage_root_scanned_at_ms": self._scanned_at_ms,
                "storage_root_max_bytes": self.root_max_bytes,
                "request_manifest_persistence_unknown": False,
                "storage_terminal_write_set_peak_bytes": self.terminal_write_set_peak_bytes,
                "storage_emergency_blocker_reserve_bytes": self.root_emergency_reserve_bytes,
            }
        finally:
            self._release_lock(fd)

    def cleanup_owned_temp_files(self, process_instance_id: str):
        if not self.output_root.exists():
            return
        fd = self._acquire_lock()
        try:
            for dirpath, _, filenames in os.walk(self.output_root):
                for f in filenames:
                    if (f".atomic.{process_instance_id}.tmp" in f) or (f".compact.{process_instance_id}.tmp" in f):
                        fp = pathlib.Path(dirpath) / f
                        try:
                            fp.unlink(missing_ok=True)
                        except OSError:
                            pass
        finally:
            self._release_lock(fd)
