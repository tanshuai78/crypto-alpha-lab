import contextlib
import fcntl
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterator

from configs import base
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_CORES,
    PROFILE_IDS,
    canonical_json,
    compute_profile_attestation_sha256,
    sha256_hex,
    stage1_6e_a_permissions,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_ENVIRONMENT_ATTESTATION_KEYS = {
    "schema_version", "execution_environment_id", "deployment_host_identity", "hostname",
    "project_root_realpath", "root_filesystem_st_dev", "shared_lock_filesystem_st_dev",
    "network_namespace_inode", "proxy_environment", "runtime_user_uid",
    "deployment_git_commit", "deployment_runtime_worktree_clean", "permissions",
}
_PROFILE_ATTESTATION_KEYS = {
    "schema_version", "capability_run_id", "market_source_profile_id",
    "profile_attestation_sha256", "profile_attested_at_ms", "permissions",
}
_OBSERVATION_KEYS = {
    "schema_version", "market_capability_observation_id", "capability_run_id",
    "market_source_profile_id", "profile_attestation_sha256", "probe_request_seq",
    "request_identity", "outcome_kind", "local_observed_at_ms", "http_status",
    "response_headers_subset", "raw_payload_persisted", "raw_relative_path", "raw_sha256",
    "observed_bytes_lower_bound", "payload_schema_status", "payload_time_status",
    "profile_status", "terminal_classification", "permissions",
}
_SUMMARY_KEYS = {
    "schema_version", "capability_run_id", "profile_states", "observation_ids",
    "historical_retention_coverage", "event_market_coverage", "fee_coverage_status", "permissions",
}
_TERMINAL_KEYS = {
    "schema_version", "capability_run_id", "status", "terminal_reason", "started_at_ms",
    "terminal_at_ms", "profile_attestation_sha256_by_id", "attempted_profile_ids",
    "passed_profile_ids", "accounted_root_bytes", "permissions",
}
_HEADER_KEYS = {"content-type", "content-length", "content-encoding", "date", "retry-after"}


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


class Stage16EAStorageBlocked(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Stage16EAStorageIntegrityError(IOError):
    pass


class RootWriterLock:
    def __init__(self, root_path: Path, storage_guard: "Stage16EAStorageGuard | None" = None):
        self._root_path = Path(root_path).resolve()
        self._lock_file_path = self._root_path / ".stage1_6e_a_writer.lock"
        self._storage_guard = storage_guard
        self._fd: int | None = None

    def acquire(self) -> None:
        if not self._lock_file_path.exists():
            if self._storage_guard is None:
                self._lock_file_path.touch(mode=0o600, exist_ok=True)
            else:
                with self._storage_guard.admitted_write(
                    write_class="ordinary_control_plane",
                    persistent_delta_bytes=0,
                    transient_peak_bytes=0,
                ):
                    self._lock_file_path.touch(mode=0o600, exist_ok=True)
        self._fd = os.open(str(self._lock_file_path), os.O_RDWR)
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            os.close(self._fd)
            self._fd = None
            raise BlockingIOError(f"Cannot acquire writer lock on {self._lock_file_path}") from exc

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None

    def __enter__(self) -> "RootWriterLock":
        self.acquire()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()


class Stage16EAStorageGuard:
    def __init__(
        self,
        output_root: Path | None = None,
        shared_lock_path: str | Path | None = None,
        disk_usage_func: Any = None,
    ):
        self.output_root = Path(output_root).resolve() if output_root is not None else None
        if shared_lock_path is None:
            if self.output_root is None:
                raise ValueError("output_root_or_shared_lock_path_required")
            shared_lock_path = self._derive_shared_lock_path(self.output_root)
        self._lock_path = Path(shared_lock_path).resolve()
        self._disk_usage_func = disk_usage_func or shutil.disk_usage

        self.host_start_free_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES
        self.host_protected_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_RUNTIME_PROTECTED_RESERVE_BYTES
        self.host_ordinary_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_ORDINARY_CONTROL_PLANE_RESERVE_BYTES
        self.host_emergency_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES
        self.root_max_bytes = base.EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_MAX_BYTES
        self.root_ordinary_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_ORDINARY_RESERVE_BYTES
        self.root_emergency_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_EMERGENCY_RESERVE_BYTES
        self.terminal_write_set_max_peak_bytes = base.EXTERNAL_SIGNAL_STAGE1_6E_A_TERMINAL_WRITE_SET_MAX_PEAK_BYTES

    @staticmethod
    def _derive_shared_lock_path(output_root: Path) -> Path:
        for parent in (output_root, *output_root.parents):
            if parent.name == "external_signal_shadow" and parent.parent.name == "data":
                return parent / ".stage1_5_storage_guard.lock"
        raise ValueError("output_root_missing_external_signal_shadow_ancestor")

    def _disk_usage_target(self) -> Path:
        target = self.output_root or self._lock_path.parent
        while not target.exists() and target != target.parent:
            target = target.parent
        return target

    def _current_root_bytes(self) -> int:
        if self.output_root is None or not self.output_root.exists():
            return 0
        return sum(path.stat().st_size for path in self.output_root.rglob("*") if path.is_file())

    def _host_free_bytes(self) -> int:
        usage = self._disk_usage_func(self._disk_usage_target())
        return int(getattr(usage, "free", usage[2]))

    @contextlib.contextmanager
    def acquire_shared_lock(self) -> Iterator[None]:
        if not self._lock_path.is_file():
            raise Stage16EAStorageBlocked("shared_storage_lock_missing")
        fd = os.open(str(self._lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def validate_startup_free_space(self) -> None:
        with self.acquire_shared_lock():
            required_emergency_reserve = (
                base.EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
                + base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
                + base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
                + self.terminal_write_set_max_peak_bytes
            )
            if self.host_emergency_reserve_bytes < required_emergency_reserve:
                raise Stage16EAStorageBlocked("shared_emergency_reserve_insufficient")
            if self._host_free_bytes() < self.host_start_free_bytes:
                raise Stage16EAStorageBlocked("host_start_free_space_insufficient")

    @contextlib.contextmanager
    def admitted_write(
        self,
        *,
        write_class: str,
        persistent_delta_bytes: int,
        transient_peak_bytes: int,
    ) -> Iterator[None]:
        if persistent_delta_bytes < 0 or transient_peak_bytes < persistent_delta_bytes:
            raise ValueError("invalid_write_size_projection")

        with self.acquire_shared_lock():
            root_after_peak = self._current_root_bytes() + transient_peak_bytes
            host_after_peak = self._host_free_bytes() - transient_peak_bytes
            if write_class == "normal_data":
                allowed_root = self.root_max_bytes - self.root_ordinary_reserve_bytes - self.root_emergency_reserve_bytes
                required_host = (
                    self.host_protected_reserve_bytes
                    + self.host_ordinary_reserve_bytes
                    + self.host_emergency_reserve_bytes
                )
            elif write_class == "ordinary_control_plane":
                allowed_root = self.root_max_bytes - self.root_emergency_reserve_bytes
                required_host = self.host_protected_reserve_bytes + self.host_emergency_reserve_bytes
            elif write_class == "terminal_control_plane":
                if transient_peak_bytes > self.terminal_write_set_max_peak_bytes:
                    raise Stage16EAStorageBlocked("terminal_peak_exceeded")
                allowed_root = self.root_max_bytes
                required_host = self.host_protected_reserve_bytes
            else:
                raise ValueError(f"unknown_write_class:{write_class}")

            if root_after_peak > allowed_root:
                raise Stage16EAStorageBlocked("root_budget_exceeded")
            if host_after_peak < required_host:
                raise Stage16EAStorageBlocked("host_reserve_exceeded")
            yield

    def check_write_admission(
        self,
        *,
        write_class: str,
        persistent_delta_bytes: int,
        transient_peak_bytes: int,
    ) -> None:
        with self.admitted_write(
            write_class=write_class,
            persistent_delta_bytes=persistent_delta_bytes,
            transient_peak_bytes=transient_peak_bytes,
        ):
            pass


def validate_capability_root_path(project_root: Path, run_id: str, candidate_path: Path) -> Path:
    proj = project_root.resolve(strict=True)
    expected_parent = (proj / "data/external_signal_shadow/stage1_6e/capability_audits").resolve()
    cand = candidate_path.resolve()
    if cand.parent != expected_parent:
        raise ValueError(f"Root parent {cand.parent} does not match expected {expected_parent}")
    if cand.name != run_id:
        raise ValueError(f"Root name {cand.name} does not match run_id {run_id}")
    return cand


def _write_atomic_bytes(
    target: Path,
    payload: bytes,
    *,
    guard: Stage16EAStorageGuard | None,
    write_class: str,
) -> str:
    existing_size = target.stat().st_size if target.exists() else 0
    persistent_delta = max(0, len(payload) - existing_size)
    admission = (
        guard.admitted_write(
            write_class=write_class,
            persistent_delta_bytes=persistent_delta,
            transient_peak_bytes=len(payload),
        )
        if guard is not None
        else contextlib.nullcontext()
    )
    with admission:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_fd, temp_path_str = tempfile.mkstemp(dir=target.parent, prefix="temp_", suffix=target.suffix)
        temp_path = Path(temp_path_str)
        try:
            with os.fdopen(temp_fd, "wb") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp_path, target)
            read_bytes = target.read_bytes()
            if read_bytes != payload:
                raise Stage16EAStorageIntegrityError(f"atomic_write_readback_mismatch:{target}")
            return sha256_hex(read_bytes)
        finally:
            temp_path.unlink(missing_ok=True)


def write_atomic_json(
    target_path: Path,
    data: dict[str, Any],
    *,
    guard: Stage16EAStorageGuard | None = None,
    write_class: str = "ordinary_control_plane",
) -> str:
    target = Path(target_path)
    json_bytes = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    return _write_atomic_bytes(target, json_bytes, guard=guard, write_class=write_class)


def write_source_profile(
    root: Path,
    profile_id: str,
    profile_core: dict[str, Any],
    *,
    guard: Stage16EAStorageGuard | None = None,
) -> str:
    target_file = root / "source_profiles" / f"{profile_id}.json"
    raw_bytes = canonical_json(profile_core)
    return _write_atomic_bytes(target_file, raw_bytes, guard=guard, write_class="ordinary_control_plane")


def write_source_profile_attestation(
    root: Path,
    profile_id: str,
    attestation_dict: dict[str, Any],
    *,
    guard: Stage16EAStorageGuard | None = None,
) -> str:
    target_dir = root / "source_profile_attestations"
    target_file = target_dir / f"{profile_id}.json"
    return write_atomic_json(target_file, attestation_dict, guard=guard)


def append_observation(
    root: Path,
    observation_dict: dict[str, Any],
    *,
    guard: Stage16EAStorageGuard | None = None,
) -> None:
    target_file = root / "capability_observations.jsonl"
    line_bytes = canonical_json(observation_dict) + b"\n"

    # Atomic append via tmp replace of whole file if exists
    existing_bytes = target_file.read_bytes() if target_file.exists() else b""
    new_bytes = existing_bytes + line_bytes

    _write_atomic_bytes(target_file, new_bytes, guard=guard, write_class="normal_data")


def write_raw_body(
    root: Path,
    raw_bytes: bytes,
    *,
    guard: Stage16EAStorageGuard | None = None,
) -> str:
    r_sha = sha256_hex(raw_bytes)
    target_file = root / "raw" / f"{r_sha}.body"

    if target_file.exists():
        return r_sha

    actual_sha = _write_atomic_bytes(target_file, raw_bytes, guard=guard, write_class="normal_data")
    if actual_sha != r_sha:
        raise Stage16EAStorageIntegrityError(f"raw_body_sha256_mismatch:{target_file}")
    return actual_sha


def write_capability_summary(
    root: Path,
    summary_dict: dict[str, Any],
    *,
    guard: Stage16EAStorageGuard | None = None,
) -> str:
    return write_atomic_json(root / "capability_summary.json", summary_dict, guard=guard)


def write_terminal_status(
    root: Path,
    terminal_dict: dict[str, Any],
    *,
    guard: Stage16EAStorageGuard | None = None,
) -> str:
    return write_atomic_json(
        root / "terminal_status.json",
        terminal_dict,
        guard=guard,
        write_class="terminal_control_plane",
    )


def write_manifest(
    root: Path,
    manifest_payload_base: dict[str, Any],
    *,
    guard: Stage16EAStorageGuard | None = None,
) -> str:
    # Build authoritative_artifacts strictly sorted by relative_path
    artifacts = []
    for file_path in root.rglob("*"):
        if file_path.is_file() and file_path.name != "manifest.json" and not file_path.name.startswith("temp_"):
            rel_path = str(file_path.relative_to(root))
            f_bytes = file_path.read_bytes()
            artifacts.append({
                "byte_count": len(f_bytes),
                "relative_path": rel_path,
                "sha256": sha256_hex(f_bytes),
            })

    artifacts.sort(key=lambda a: a["relative_path"])

    manifest_data = dict(manifest_payload_base)
    manifest_data["authoritative_artifacts"] = artifacts

    # manifest_id calculation (omitting manifest_id)
    manifest_data_sans_id = {k: v for k, v in manifest_data.items() if k != "manifest_id"}
    manifest_data["manifest_id"] = sha256_hex(canonical_json(manifest_data_sans_id))

    return write_atomic_json(root / "manifest.json", manifest_data, guard=guard, write_class="normal_data")


def verify_complete_bundle(root_path: str | Path) -> tuple[bool, list[str]]:
    root = Path(root_path).resolve()

    if root.is_symlink():
        return False, ["root_is_symlink"]

    manifest_file = root / "manifest.json"
    if not manifest_file.is_file() or manifest_file.is_symlink():
        return False, ["manifest_missing_or_symlink"]

    try:
        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception:
        return False, ["manifest_corrupted"]

    if not isinstance(manifest_data, dict):
        return False, ["manifest_invalid_structure"]

    expected_manifest_keys = {
        "schema_version",
        "manifest_id",
        "capability_run_id",
        "terminal_status_sha256",
        "profile_attestation_sha256_by_id",
        "authoritative_artifacts",
        "permissions",
    }
    if set(manifest_data.keys()) != expected_manifest_keys:
        return False, ["manifest_keys_mismatch"]

    manifest_sans_id = {key: value for key, value in manifest_data.items() if key != "manifest_id"}
    if manifest_data["manifest_id"] != sha256_hex(canonical_json(manifest_sans_id)):
        return False, ["manifest_id_mismatch"]
    if manifest_data["schema_version"] != "stage1_6e_a_manifest_v1":
        return False, ["manifest_schema_invalid"]
    if manifest_data["capability_run_id"] != root.name:
        return False, ["manifest_run_id_invalid"]
    if not _is_sha256(manifest_data["terminal_status_sha256"]):
        return False, ["manifest_terminal_status_sha256_invalid"]
    if manifest_data["permissions"] != stage1_6e_a_permissions():
        return False, ["manifest_permissions_invalid"]

    declared_artifacts = manifest_data["authoritative_artifacts"]
    if not isinstance(declared_artifacts, list):
        return False, ["authoritative_artifacts_not_list"]
    if any(not isinstance(row, dict) for row in declared_artifacts):
        return False, ["authoritative_artifact_invalid"]
    if any(set(row) != {"relative_path", "sha256", "byte_count"} for row in declared_artifacts):
        return False, ["authoritative_artifact_keys_mismatch"]

    rel_paths = [row["relative_path"] for row in declared_artifacts]
    if any(
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or path == "manifest.json"
        for path in rel_paths
    ):
        return False, ["authoritative_artifact_path_invalid"]
    if any(
        not _is_sha256(row["sha256"])
        or isinstance(row["byte_count"], bool)
        or not isinstance(row["byte_count"], int)
        or row["byte_count"] < 0
        for row in declared_artifacts
    ):
        return False, ["authoritative_artifact_metadata_invalid"]
    if len(rel_paths) != len(set(rel_paths)):
        return False, ["authoritative_artifacts_duplicate_path"]
    if rel_paths != sorted(rel_paths):
        return False, ["authoritative_artifacts_not_sorted"]

    disk_paths: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            return False, ["symlink_found_in_tree"]
        if path.is_file():
            disk_paths.add(str(path.relative_to(root)))
    if set(rel_paths) | {"manifest.json"} != disk_paths:
        return False, ["unmanifested_or_unexpected_files"]

    for artifact in declared_artifacts:
        path = root / artifact["relative_path"]
        if not path.is_file() or path.is_symlink():
            return False, [f"artifact_missing_or_symlink_{artifact['relative_path']}"]
        payload = path.read_bytes()
        if len(payload) != artifact["byte_count"] or sha256_hex(payload) != artifact["sha256"]:
            return False, [f"artifact_hash_or_size_mismatch_{artifact['relative_path']}"]

    required_paths = {
        "execution_environment_attestation.json",
        ".stage1_6e_a_writer.lock",
        "capability_observations.jsonl",
        "capability_summary.json",
        "terminal_status.json",
        *(f"source_profiles/{profile_id}.json" for profile_id in PROFILE_IDS),
        *(f"source_profile_attestations/{profile_id}.json" for profile_id in PROFILE_IDS),
    }
    if not required_paths.issubset(set(rel_paths)):
        return False, ["required_artifact_tree_mismatch"]
    if (root / ".stage1_6e_a_writer.lock").read_bytes() != b"":
        return False, ["writer_lock_bytes_invalid"]

    try:
        environment = json.loads((root / "execution_environment_attestation.json").read_text(encoding="utf-8"))
    except Exception:
        return False, ["execution_environment_attestation_corrupted"]
    if not isinstance(environment, dict) or set(environment) != _ENVIRONMENT_ATTESTATION_KEYS:
        return False, ["execution_environment_attestation_keys_mismatch"]
    environment_sans_id = {key: value for key, value in environment.items() if key != "execution_environment_id"}
    if (
        environment.get("schema_version") != "stage1_6e_a_execution_environment_attestation_v1"
        or environment.get("execution_environment_id") != sha256_hex(canonical_json(environment_sans_id))
        or not _is_sha256(environment.get("deployment_host_identity"))
        or not isinstance(environment.get("hostname"), str)
        or not environment["hostname"]
        or not isinstance(environment.get("project_root_realpath"), str)
        or not environment["project_root_realpath"]
        or any(
            isinstance(environment[key], bool) or not isinstance(environment[key], int) or environment[key] < 0
            for key in ("root_filesystem_st_dev", "shared_lock_filesystem_st_dev", "network_namespace_inode", "runtime_user_uid")
        )
        or environment["root_filesystem_st_dev"] != os.stat(root).st_dev
        or not isinstance(environment.get("deployment_git_commit"), str)
        or not _GIT_COMMIT_RE.fullmatch(environment["deployment_git_commit"])
        or environment.get("proxy_environment") != "absent"
        or environment.get("deployment_runtime_worktree_clean") is not True
        or environment.get("permissions") != stage1_6e_a_permissions()
    ):
        return False, ["execution_environment_attestation_invalid"]

    term_file = root / "terminal_status.json"
    try:
        term_data = json.loads(term_file.read_text(encoding="utf-8"))
    except Exception:
        return False, ["terminal_status_corrupted"]
    if not isinstance(term_data, dict) or set(term_data) != _TERMINAL_KEYS:
        return False, ["terminal_status_keys_mismatch"]
    if (
        term_data.get("schema_version") != "stage1_6e_a_terminal_status_v1"
        or term_data.get("capability_run_id") != root.name
        or term_data.get("status") != "complete"
        or term_data.get("terminal_reason") is not None
        or not all(isinstance(term_data[key], int) and not isinstance(term_data[key], bool) for key in (
            "started_at_ms", "terminal_at_ms", "accounted_root_bytes",
        ))
        or term_data.get("permissions") != stage1_6e_a_permissions()
    ):
        return False, ["terminal_status_not_complete"]
    if sha256_hex(term_file.read_bytes()) != manifest_data["terminal_status_sha256"]:
        return False, ["terminal_status_sha256_mismatch"]

    profile_sha_by_id: dict[str, str] = {}
    for profile_id in PROFILE_IDS:
        core_bytes = canonical_json(PROFILE_CORES[profile_id])
        profile_path = root / "source_profiles" / f"{profile_id}.json"
        if profile_path.read_bytes() != core_bytes:
            return False, ["source_profile_bytes_mismatch"]
        profile_sha_by_id[profile_id] = compute_profile_attestation_sha256(PROFILE_CORES[profile_id])
        try:
            attestation = json.loads(
                (root / "source_profile_attestations" / f"{profile_id}.json").read_text(encoding="utf-8")
            )
        except Exception:
            return False, ["profile_attestation_corrupted"]
        if (
            not isinstance(attestation, dict)
            or set(attestation) != _PROFILE_ATTESTATION_KEYS
            or attestation.get("schema_version") != "stage1_6e_a_profile_attestation_v1"
            or attestation.get("capability_run_id") != root.name
            or attestation.get("market_source_profile_id") != profile_id
            or attestation.get("profile_attestation_sha256") != profile_sha_by_id[profile_id]
            or isinstance(attestation.get("profile_attested_at_ms"), bool)
            or not isinstance(attestation.get("profile_attested_at_ms"), int)
            or attestation.get("permissions") != stage1_6e_a_permissions()
        ):
            return False, ["profile_attestation_invalid"]
    if manifest_data["profile_attestation_sha256_by_id"] != profile_sha_by_id:
        return False, ["manifest_profile_attestation_map_mismatch"]
    if term_data.get("profile_attestation_sha256_by_id") != profile_sha_by_id:
        return False, ["terminal_profile_attestation_map_mismatch"]

    try:
        observations = [json.loads(line) for line in (root / "capability_observations.jsonl").read_text().splitlines()]
        summary_data = json.loads((root / "capability_summary.json").read_text(encoding="utf-8"))
    except Exception:
        return False, ["complete_control_artifact_corrupted"]
    if len(observations) != len(PROFILE_IDS):
        return False, ["observation_count_invalid"]
    if any(not isinstance(row, dict) or set(row) != _OBSERVATION_KEYS for row in observations):
        return False, ["observation_keys_mismatch"]
    if [row.get("market_source_profile_id") for row in observations] != list(PROFILE_IDS):
        return False, ["observation_profile_order_invalid"]
    if any(
        row.get("schema_version") != "stage1_6e_a_capability_observation_v1"
        or row.get("capability_run_id") != root.name
        or row.get("profile_attestation_sha256") != profile_sha_by_id[row["market_source_profile_id"]]
        or row.get("probe_request_seq") != seq
        or not _is_sha256(row.get("market_capability_observation_id"))
        or not _is_sha256(row.get("request_identity"))
        or row.get("outcome_kind") != "response_persisted"
        or row.get("profile_status") != "capability_pass"
        or row.get("terminal_classification") != "continue"
        or row.get("raw_payload_persisted") is not True
        or not isinstance(row.get("raw_relative_path"), str)
        or not _is_sha256(row.get("raw_sha256"))
        or isinstance(row.get("local_observed_at_ms"), bool)
        or not isinstance(row.get("local_observed_at_ms"), int)
        or isinstance(row.get("observed_bytes_lower_bound"), bool)
        or not isinstance(row.get("observed_bytes_lower_bound"), int)
        or row.get("permissions") != stage1_6e_a_permissions()
        or not isinstance(row.get("response_headers_subset"), dict)
        or set(row["response_headers_subset"]) != _HEADER_KEYS
        or any(value is not None and not isinstance(value, str) for value in row["response_headers_subset"].values())
        for seq, row in enumerate(observations, start=1)
    ):
        return False, ["complete_observation_invalid"]
    raw_paths = {
        row.get("raw_relative_path")
        for row in observations
        if isinstance(row.get("raw_relative_path"), str)
    }
    if not raw_paths or any(path not in rel_paths or not path.startswith("raw/") for path in raw_paths):
        return False, ["raw_artifact_tree_mismatch"]
    if set(path for path in rel_paths if path.startswith("raw/")) != raw_paths:
        return False, ["raw_artifact_tree_mismatch"]
    for row in observations:
        if row["raw_relative_path"] != f"raw/{row['raw_sha256']}.body" or not _is_sha256(row["raw_sha256"]):
            return False, ["observation_raw_reference_invalid"]
        raw_path = root / row["raw_relative_path"]
        if sha256_hex(raw_path.read_bytes()) != row.get("raw_sha256"):
            return False, ["observation_raw_sha256_mismatch"]
    observation_ids = {
        profile_id: row["market_capability_observation_id"]
        for profile_id, row in zip(PROFILE_IDS, observations, strict=True)
    }
    if not isinstance(summary_data, dict) or set(summary_data) != _SUMMARY_KEYS:
        return False, ["capability_summary_keys_mismatch"]
    if (
        summary_data.get("schema_version") != "stage1_6e_a_capability_summary_v1"
        or summary_data.get("capability_run_id") != root.name
        or summary_data.get("profile_states") != {profile_id: "capability_pass" for profile_id in PROFILE_IDS}
        or summary_data.get("observation_ids") != observation_ids
        or summary_data.get("historical_retention_coverage") != "not_evaluable"
        or summary_data.get("event_market_coverage") != "not_evaluable"
        or summary_data.get("fee_coverage_status") != "not_evaluated_in_stage1_6e_a"
        or summary_data.get("permissions") != stage1_6e_a_permissions()
        or term_data.get("attempted_profile_ids") != list(PROFILE_IDS)
        or term_data.get("passed_profile_ids") != list(PROFILE_IDS)
    ):
        return False, ["complete_summary_or_terminal_invalid"]

    allowed_paths = required_paths | raw_paths
    if set(rel_paths) != allowed_paths:
        return False, ["authoritative_artifact_path_invalid"]

    return True, []
