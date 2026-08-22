"""Guarded storage engine, strict path confinement, shared locking, and restart recovery for Stage 1.6B."""

import fcntl
import hashlib
import json
import os
import shutil
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from configs import base
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    SELECTED_CATALOG_ID,
    SELECTED_CATALOG_NAME,
    SOURCE_PROFILE_ID,
    CaptureMode,
    CaptureRunContract,
    ObserverCheckpointRecord,
    SealedExportManifest,
    TerminalStatusRecord,
    canonical_json,
    compute_export_id,
    compute_request_headers_profile_sha256,
    validate_observer_checkpoint_status_coverage,
)


class Stage16BStorageBlocked(RuntimeError):
    """Raised when storage admission check fails."""
    def __init__(self, blocker: str, detail: str = ""):
        self.blocker = blocker
        self.detail = detail
        super().__init__(f"storage_write_blocked:{blocker} - {detail}")


class RootWriterLockError(RuntimeError):
    """Raised when root writer lock cannot be acquired exclusively."""
    pass


class RootWriterLock:
    """Process-lifetime exclusive writer lock on a specific run root."""
    def __init__(self, run_root: Path):
        self.run_root = run_root
        self.lock_file_path = run_root / ".stage1_6b_writer.lock"
        self._fd: Optional[int] = None

    def acquire(self) -> None:
        self.run_root.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_file_path, os.O_RDWR | os.O_CREAT, 0o666)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            os.close(fd)
            raise RootWriterLockError(f"root_already_owned:{self.run_root}") from exc
        self._fd = fd

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def derive_shared_storage_lock_path(output_root: Path) -> Path:
    """Derive Stage 1.5 shared storage guard advisory lock path without importing Stage 1.5 production code."""
    resolved = output_root.resolve()
    target_ancestor = None
    for parent in resolved.parents:
        if parent.name == "external_signal_shadow" and parent.parent.name == "data":
            target_ancestor = parent
            break
    if target_ancestor is None:
        raise ValueError("output_root_missing_external_signal_shadow_ancestor")
    lock_dir = target_ancestor
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / ".stage1_5_storage_guard.lock"


def validate_probe_attestation_path(
    probe_path: Path,
    project_root: Optional[Path] = None,
) -> Path:
    """Strict path confinement for source profile probe attestation."""
    p_root = (project_root or Path.cwd()).resolve()
    allowed_parent = (p_root / "data" / "external_signal_shadow" / "stage1_6b" / "source_profile_attestations").resolve()
    resolved = probe_path.resolve()

    if not resolved.is_relative_to(allowed_parent):
        raise ValueError(f"invalid_probe_attestation_path: {probe_path} is not under {allowed_parent}")

    if resolved.name != "source_profile_probe_attestation.json":
        raise ValueError(f"invalid_probe_attestation_path: filename must be source_profile_probe_attestation.json, got {resolved.name}")

    if resolved.parent == allowed_parent:
        raise ValueError("invalid_probe_attestation_path: attestation must be inside <profile_sha256> subfolder")

    return resolved


def validate_run_root_path(
    run_root: Path,
    capture_mode: str,
    require_fresh: bool,
    project_root: Optional[Path] = None,
) -> Path:
    """Strict path confinement for historical and live run roots."""
    p_root = (project_root or Path.cwd()).resolve()
    family_folder = "historical_backfill" if capture_mode == CaptureMode.HISTORICAL_BACKFILL.value else "live_observation"
    allowed_parent = (p_root / "data" / "external_signal_shadow" / "stage1_6b" / family_folder).resolve()
    resolved = run_root.resolve()

    if not resolved.is_relative_to(allowed_parent):
        raise ValueError(f"invalid_root_family: {run_root} is not under {allowed_parent}")

    if resolved.parent != allowed_parent:
        raise ValueError(f"invalid_root_nesting: {run_root} must be a direct child of {allowed_parent}")

    if require_fresh and resolved.exists():
        raise ValueError(f"root_already_exists: {run_root}")

    if not require_fresh and not resolved.exists():
        raise ValueError(f"root_does_not_exist: {run_root}")

    return resolved


class Stage16BStorageGuard:
    """Narrow stdlib storage guard enforcing Stage 1.6B quota boundaries and shared host locking."""

    def __init__(
        self,
        output_root: Path,
        disk_usage_func: Optional[Callable[[Path], Any]] = None,
    ):
        self.output_root = output_root.resolve()
        self.disk_usage_func = disk_usage_func or shutil.disk_usage
        self.lock_file_path = derive_shared_storage_lock_path(self.output_root)

        # Stage 1.5 Host SSOT
        self.host_start_free_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES
        self.host_protected_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_RUNTIME_PROTECTED_RESERVE_BYTES
        self.host_ordinary_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_ORDINARY_CONTROL_PLANE_RESERVE_BYTES
        self.host_emergency_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES

        # Stage 1.6B Root SSOT
        self.root_max_bytes = base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_ROOT_MAX_BYTES
        self.root_ordinary_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES
        self.root_emergency_reserve_bytes = base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES
        self.terminal_write_set_max_peak_bytes = base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_TERMINAL_WRITE_SET_MAX_PEAK_BYTES

    def _acquire_shared_lock(self) -> int:
        fd = os.open(self.lock_file_path, os.O_RDWR | os.O_CREAT, 0o666)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd

    def _release_shared_lock(self, fd: int) -> None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _disk_usage_target(self) -> Path:
        target = self.output_root
        while not target.exists() and target != target.parent:
            target = target.parent
        return target

    def validate_startup_free_space(self) -> None:
        """Verify initial host free space is at least 8 GiB."""
        fd = self._acquire_shared_lock()
        try:
            du = self.disk_usage_func(self._disk_usage_target())
            host_free = getattr(du, "free", du[2] if isinstance(du, (tuple, list)) else du)
            if host_free < self.host_start_free_bytes:
                raise Stage16BStorageBlocked(
                    "host_start_free_space_insufficient",
                    f"Host free {host_free} < required {self.host_start_free_bytes}",
                )
        finally:
            self._release_shared_lock(fd)

    @contextmanager
    def admitted_write(
        self,
        write_class: str,
        persistent_delta_bytes: int,
        transient_peak_bytes: int,
        current_root_bytes: int,
    ):
        """Hold shared admission lock across one persistent write."""
        if transient_peak_bytes < max(0, persistent_delta_bytes):
            raise ValueError("transient_peak_bytes must be >= max(0, persistent_delta_bytes)")

        fd = self._acquire_shared_lock()
        try:
            du = self.disk_usage_func(self._disk_usage_target())
            host_free = getattr(du, "free", du[2] if isinstance(du, (tuple, list)) else du)
            host_free_after_peak = host_free - transient_peak_bytes
            root_after_peak = current_root_bytes + transient_peak_bytes

            if write_class == "normal_data":
                allowed_root = self.root_max_bytes - self.root_ordinary_reserve_bytes - self.root_emergency_reserve_bytes
                if root_after_peak > allowed_root:
                    raise Stage16BStorageBlocked(
                        "root_budget_exceeded",
                        f"root_after_peak {root_after_peak} > max normal {allowed_root}",
                    )
                min_host_free = self.host_protected_reserve_bytes + self.host_ordinary_reserve_bytes + self.host_emergency_reserve_bytes
                if host_free_after_peak < min_host_free:
                    raise Stage16BStorageBlocked(
                        "host_reserve_exceeded",
                        f"host_free_after_peak {host_free_after_peak} < min host {min_host_free}",
                    )

            elif write_class == "ordinary_control_plane":
                allowed_root = self.root_max_bytes - self.root_emergency_reserve_bytes
                if root_after_peak > allowed_root:
                    raise Stage16BStorageBlocked(
                        "root_budget_exceeded",
                        f"root_after_peak {root_after_peak} > max ordinary {allowed_root}",
                    )
                min_host_free = self.host_protected_reserve_bytes + self.host_emergency_reserve_bytes
                if host_free_after_peak < min_host_free:
                    raise Stage16BStorageBlocked(
                        "host_reserve_exceeded",
                        f"host_free_after_peak {host_free_after_peak} < min host {min_host_free}",
                    )

            elif write_class == "terminal_control_plane":
                if transient_peak_bytes > self.terminal_write_set_max_peak_bytes:
                    raise Stage16BStorageBlocked(
                        "terminal_peak_exceeded",
                        f"transient_peak {transient_peak_bytes} > terminal cap {self.terminal_write_set_max_peak_bytes}",
                    )
                if root_after_peak > self.root_max_bytes:
                    raise Stage16BStorageBlocked(
                        "root_budget_exceeded",
                        f"root_after_peak {root_after_peak} > root max {self.root_max_bytes}",
                    )
                if host_free_after_peak < self.host_protected_reserve_bytes:
                    raise Stage16BStorageBlocked(
                        "host_reserve_exceeded",
                        f"host_free_after_peak {host_free_after_peak} < protected {self.host_protected_reserve_bytes}",
                    )
            else:
                raise ValueError(f"Unknown write_class: {write_class}")
            yield
        finally:
            self._release_shared_lock(fd)

    def check_write_admission(
        self,
        write_class: str,
        persistent_delta_bytes: int,
        transient_peak_bytes: int,
        current_root_bytes: int,
    ) -> None:
        """Validate a prospective write without performing it."""
        with self.admitted_write(
            write_class=write_class,
            persistent_delta_bytes=persistent_delta_bytes,
            transient_peak_bytes=transient_peak_bytes,
            current_root_bytes=current_root_bytes,
        ):
            pass


# -----------------------------------------------------------------------------
# Guarded Writer Primitives
# -----------------------------------------------------------------------------

def write_content_addressed_raw_payload(
    run_root: Path,
    payload_bytes: bytes,
    subfolder: str,  # "index" or "detail/<article_id>"
    guard: Stage16BStorageGuard,
    current_root_bytes: int,
) -> Tuple[str, str, int]:
    """Guarded content-addressed raw payload write. Returns (sha256, relative_path, bytes_written)."""
    raw_sha = hashlib.sha256(payload_bytes).hexdigest()
    rel_path = f"raw_payloads/{subfolder}/{raw_sha}.bin"
    target_path = run_root / rel_path

    size = len(payload_bytes)
    with guard.admitted_write(
        write_class="normal_data",
        persistent_delta_bytes=size,
        transient_peak_bytes=size,
        current_root_bytes=current_root_bytes,
    ):
        if target_path.is_file():
            return raw_sha, rel_path, 0
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.parent / f".tmp_{uuid.uuid4().hex}.bin"
        temp_path.write_bytes(payload_bytes)
        os.replace(temp_path, target_path)

    return raw_sha, rel_path, size


def append_jsonl_record(
    run_root: Path,
    relative_path: str,
    record: Dict[str, Any],
    write_class: str,  # "normal_data" or "ordinary_control_plane"
    guard: Stage16BStorageGuard,
    current_root_bytes: int,
) -> int:
    """Guarded append of a JSONL record. Returns bytes added."""
    line = canonical_json(record) + "\n"
    encoded = line.encode("utf-8")
    size = len(encoded)

    with guard.admitted_write(
        write_class=write_class,
        persistent_delta_bytes=size,
        transient_peak_bytes=size,
        current_root_bytes=current_root_bytes,
    ):
        target_path = run_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "ab") as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())

    return size


def write_atomic_json(
    run_root: Path,
    relative_path: str,
    data_dict: Dict[str, Any],
    write_class: str,
    guard: Stage16BStorageGuard,
    current_root_bytes: int,
) -> int:
    """Guarded atomic JSON file write via temp file + rename. Returns persistent bytes delta."""
    content = canonical_json(data_dict) + "\n"
    encoded = content.encode("utf-8")
    new_size = len(encoded)

    target_path = run_root / relative_path
    old_size = target_path.stat().st_size if target_path.is_file() else 0
    persistent_delta = new_size - old_size

    with guard.admitted_write(
        write_class=write_class,
        persistent_delta_bytes=max(0, persistent_delta),
        transient_peak_bytes=max(new_size, persistent_delta),
        current_root_bytes=current_root_bytes,
    ):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.parent / f".tmp_{uuid.uuid4().hex}.json"
        with open(temp_path, "wb") as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, target_path)

    return persistent_delta


def write_observer_checkpoint(
    run_root: Path,
    checkpoint: ObserverCheckpointRecord,
    guard: Stage16BStorageGuard,
    current_root_bytes: int,
) -> int:
    """Guarded atomic checkpoint persistence."""
    return write_atomic_json(
        run_root=run_root,
        relative_path="observer_checkpoint.json",
        data_dict=checkpoint.to_dict(),
        write_class="ordinary_control_plane",
        guard=guard,
        current_root_bytes=current_root_bytes,
    )


def write_terminal_status(
    run_root: Path,
    terminal_status: TerminalStatusRecord,
    guard: Stage16BStorageGuard,
    current_root_bytes: int,
) -> int:
    """Guarded terminal status persistence."""
    return write_atomic_json(
        run_root=run_root,
        relative_path="terminal_status.json",
        data_dict=terminal_status.to_dict(),
        write_class="terminal_control_plane",
        guard=guard,
        current_root_bytes=current_root_bytes,
    )


def write_capture_run_contract(
    run_root: Path,
    contract: CaptureRunContract,
    guard: Stage16BStorageGuard,
    current_root_bytes: int,
) -> int:
    """Guarded run contract persistence."""
    return write_atomic_json(
        run_root=run_root,
        relative_path="capture_run_contract.json",
        data_dict=contract.to_dict(),
        write_class="ordinary_control_plane",
        guard=guard,
        current_root_bytes=current_root_bytes,
    )


def copy_probe_attestation_to_root(
    run_root: Path,
    attestation_source_path: Path,
    guard: Stage16BStorageGuard,
    current_root_bytes: int,
) -> int:
    """Guarded copy of probe attestation JSON into run root."""
    payload_bytes = attestation_source_path.read_bytes()
    size = len(payload_bytes)

    with guard.admitted_write(
        write_class="ordinary_control_plane",
        persistent_delta_bytes=size,
        transient_peak_bytes=size,
        current_root_bytes=current_root_bytes,
    ):
        target_path = run_root / "source_profile_probe_attestation.json"
        temp_path = run_root / f".tmp_{uuid.uuid4().hex}.json"
        temp_path.write_bytes(payload_bytes)
        os.replace(temp_path, target_path)

    return size


def _validate_reconcile_row(stream_rel: str, row: Dict[str, Any]) -> None:
    """Validate authoritative rows during bounded restart reconciliation preflight."""
    if stream_rel.startswith("list_captures/"):
        if row.get("schema_version") != "stage1_6b_list_capture_v2":
            raise ValueError("list_capture_v2_required")
        if row.get("source_profile_id") != SOURCE_PROFILE_ID:
            raise ValueError("list_capture_profile_mismatch")
        if row.get("selected_catalog_id") != SELECTED_CATALOG_ID or row.get("selected_catalog_name") != SELECTED_CATALOG_NAME:
            raise ValueError("list_capture_catalog_provenance_mismatch")
        if int(row.get("selected_catalog_total", 0)) < int(row.get("article_count", 0)):
            raise ValueError("list_capture_catalog_total_invalid")
    elif stream_rel == "article_discoveries.jsonl":
        if row.get("schema_version") != "stage1_6b_article_discovery_v2":
            raise ValueError("article_discovery_v2_required")
        if row.get("source_profile_id") != SOURCE_PROFILE_ID:
            raise ValueError("article_discovery_profile_mismatch")
        if row.get("source_catalog_id") != SELECTED_CATALOG_ID or row.get("source_catalog_name") != SELECTED_CATALOG_NAME:
            raise ValueError("article_discovery_catalog_provenance_mismatch")


def reconcile_and_load_checkpoint(
    run_root: Path,
    guard: Stage16BStorageGuard,
) -> Tuple[ObserverCheckpointRecord, int]:
    """Reconcile checkpoint against bounded committed stream offsets without scanning entire root."""
    chk_path = run_root / "observer_checkpoint.json"
    if not chk_path.is_file():
        raise ValueError("missing_checkpoint_file")

    data = json.loads(chk_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "stage1_6b_observer_checkpoint_v2":
        raise ValueError(f"checkpoint_schema_version_invalid: {data.get('schema_version')}")
    if data.get("source_profile_id") != SOURCE_PROFILE_ID:
        raise ValueError(f"checkpoint_profile_mismatch: {data.get('source_profile_id')} != {SOURCE_PROFILE_ID}")

    chk = ObserverCheckpointRecord(**data)

    # A bounded tail is the only uncommitted state permitted between polls.
    tail_limit = base.EXTERNAL_SIGNAL_STAGE1_6B_MAX_RAW_PAYLOAD_BYTES + 64 * 1024
    stream_offsets = dict(chk.stream_offsets)
    stream_last_hashes = dict(chk.stream_last_hashes)
    added_bytes = 0

    for stream_rel, offset in list(stream_offsets.items()):
        stream_p = run_root / stream_rel
        if not stream_p.is_file():
            if offset:
                raise ValueError("checkpoint_stream_missing")
            continue

        actual_size = stream_p.stat().st_size
        if offset < 0 or actual_size < offset:
            raise ValueError("checkpoint_stream_offset_invalid")
        if offset:
            expected_hash = stream_last_hashes.get(stream_rel)
            if not expected_hash:
                raise ValueError("checkpoint_prefix_hash_missing")
            if offset > tail_limit:
                prefix_start = offset - tail_limit
            else:
                prefix_start = 0
            with open(stream_p, "rb") as stream_file:
                stream_file.seek(offset - 1)
                if stream_file.read(1) != b"\n":
                    raise ValueError("checkpoint_stream_offset_not_line_boundary")
                stream_file.seek(prefix_start)
                prefix_tail = stream_file.read(offset - prefix_start)
            committed_lines = prefix_tail.rstrip(b"\n").splitlines()
            if not committed_lines or (prefix_start and b"\n" not in prefix_tail):
                raise ValueError("checkpoint_prefix_record_exceeds_bound")
            actual_hash = hashlib.sha256(committed_lines[-1]).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError("checkpoint_prefix_hash_mismatch")
            for line in committed_lines:
                try:
                    parsed_c = json.loads(line)
                    if isinstance(parsed_c, dict):
                        _validate_reconcile_row(stream_rel, parsed_c)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass

        tail_size = actual_size - offset
        if tail_size > tail_limit:
            raise ValueError("checkpoint_tail_exceeds_bound")
        if not tail_size:
            continue
        with open(stream_p, "rb") as stream_file:
            stream_file.seek(offset)
            tail_bytes = stream_file.read(tail_size)
        if not tail_bytes.endswith(b"\n"):
            raise ValueError("checkpoint_partial_jsonl_tail")
        tail_lines = tail_bytes.rstrip(b"\n").splitlines()
        try:
            for line in tail_lines:
                parsed = json.loads(line)
                if not isinstance(parsed, dict):
                    raise ValueError("checkpoint_tail_row_not_object")
                _validate_reconcile_row(stream_rel, parsed)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("checkpoint_malformed_jsonl_tail") from exc
        added_bytes += tail_size
        stream_offsets[stream_rel] = actual_size
        stream_last_hashes[stream_rel] = hashlib.sha256(tail_lines[-1]).hexdigest()

    reconciled_root_bytes = chk.accounted_root_bytes + added_bytes
    reconciled_chk = ObserverCheckpointRecord(
        schema_version=chk.schema_version,
        run_id=chk.run_id,
        capture_mode=chk.capture_mode,
        source_profile_id=chk.source_profile_id,
        source_profile_attestation_sha256=chk.source_profile_attestation_sha256,
        checkpoint_id=chk.checkpoint_id,
        prior_checkpoint_id=chk.prior_checkpoint_id,
        poll_seq=chk.poll_seq,
        monotonic_request_seq=chk.monotonic_request_seq,
        record_seq=chk.record_seq,
        accounted_root_bytes=reconciled_root_bytes,
        stream_offsets=stream_offsets,
        stream_last_hashes=stream_last_hashes,
        candidate_states=chk.candidate_states,
        heartbeat_at_ms=chk.heartbeat_at_ms,
        last_index_poll_status=chk.last_index_poll_status,
        last_index_poll_coverage=chk.last_index_poll_coverage,
    )

    return reconciled_chk, reconciled_root_bytes


def reconcile_and_write_checkpoint(
    run_root: Path,
    guard: Stage16BStorageGuard,
) -> Tuple[ObserverCheckpointRecord, int]:
    """Persist the reconciled restart state before a caller admits new network work."""
    checkpoint, root_bytes = reconcile_and_load_checkpoint(run_root, guard)
    checkpoint_id = hashlib.sha256(
        canonical_json(
            {
                "prior_checkpoint_id": checkpoint.checkpoint_id,
                "accounted_root_bytes": root_bytes,
                "stream_offsets": checkpoint.stream_offsets,
                "stream_last_hashes": checkpoint.stream_last_hashes,
            }
        ).encode("utf-8")
    ).hexdigest()
    reconciled = ObserverCheckpointRecord(
        schema_version=checkpoint.schema_version,
        run_id=checkpoint.run_id,
        capture_mode=checkpoint.capture_mode,
        source_profile_id=checkpoint.source_profile_id,
        source_profile_attestation_sha256=checkpoint.source_profile_attestation_sha256,
        checkpoint_id=checkpoint_id,
        prior_checkpoint_id=checkpoint.checkpoint_id,
        poll_seq=checkpoint.poll_seq,
        monotonic_request_seq=checkpoint.monotonic_request_seq,
        record_seq=checkpoint.record_seq,
        accounted_root_bytes=root_bytes,
        stream_offsets=checkpoint.stream_offsets,
        stream_last_hashes=checkpoint.stream_last_hashes,
        candidate_states=checkpoint.candidate_states,
        heartbeat_at_ms=checkpoint.heartbeat_at_ms,
        last_index_poll_status=checkpoint.last_index_poll_status,
        last_index_poll_coverage=checkpoint.last_index_poll_coverage,
    )
    delta = write_observer_checkpoint(run_root, reconciled, guard, root_bytes)
    return reconciled, root_bytes + delta


def write_historical_coverage(
    run_root: Path,
    coverage: Any,
    guard: Stage16BStorageGuard,
    current_root_bytes: int,
) -> int:
    """Guarded historical coverage persistence."""
    return write_atomic_json(
        run_root=run_root,
        relative_path="historical_coverage.json",
        data_dict=coverage.to_dict() if hasattr(coverage, "to_dict") else coverage,
        write_class="ordinary_control_plane",
        guard=guard,
        current_root_bytes=current_root_bytes,
    )


def historical_coverage_is_complete(coverage: Dict[str, Any]) -> bool:
    """Evaluate only the historical evidence clauses, never terminal/manifest state."""
    from_ms = coverage.get("from_ms")
    to_ms = coverage.get("to_ms")
    sweep_a = coverage.get("sweep_a") or {}
    sweep_b = coverage.get("sweep_b") or {}
    return bool(
        coverage.get("status") == "complete"
        and isinstance(from_ms, int)
        and isinstance(to_ms, int)
        and 0 < to_ms - from_ms <= 730 * 24 * 60 * 60 * 1000
        and sweep_a.get("reached_from_ms") is True
        and sweep_b.get("reached_from_ms") is True
        and sweep_a.get("page_failures") == []
        and sweep_b.get("page_failures") == []
        and sweep_a.get("transcript_hash")
        and sweep_a.get("transcript_hash") == sweep_b.get("transcript_hash")
        and coverage.get("candidate_terminal_count") == coverage.get("frozen_candidate_count")
        and coverage.get("pending_candidate_count") == 0
        and coverage.get("unattempted_candidate_count") == 0
        and coverage.get("final_checkpoint_valid") is True
    )



def seal_export(
    run_root: Path,
    guard: Stage16BStorageGuard,
    current_root_bytes: int,
) -> Tuple[Path, SealedExportManifest, int]:
    """Streamingly guarded copy of authoritative artifacts into sealed_exports/<export-id>/ with trailing manifest."""
    term_p = run_root / "terminal_status.json"
    if not term_p.is_file():
        raise ValueError("terminal_status_missing_or_failed: terminal_status.json not found")
    term_data = json.loads(term_p.read_text(encoding="utf-8"))
    if term_data.get("status") != "complete":
        raise ValueError(f"terminal_status_missing_or_failed: status is {term_data.get('status')}")

    chk_p = run_root / "observer_checkpoint.json"
    if not chk_p.is_file():
        raise ValueError("missing_checkpoint_file")
    chk_data = json.loads(chk_p.read_text(encoding="utf-8"))

    contract_p = run_root / "capture_run_contract.json"
    if not contract_p.is_file():
        raise ValueError("missing_contract_file")
    contract_data = json.loads(contract_p.read_text(encoding="utf-8"))

    capture_mode = contract_data["capture_mode"]
    source_profile_id = contract_data["source_profile_id"]
    checkpoint_id = chk_data["checkpoint_id"]
    term_sha256 = hashlib.sha256(term_p.read_bytes()).hexdigest()

    # Discover all authoritative files
    authoritative_files: List[Tuple[str, str, int]] = []
    excluded_prefixes = ["sealed_exports", ".stage1_6b_writer.lock", ".tmp_"]

    for root_dir, dirs, files in os.walk(run_root):
        rel_root = os.path.relpath(root_dir, run_root)
        if any(rel_root.startswith(ex) for ex in excluded_prefixes):
            continue
        for f in files:
            if any(f.startswith(ex) for ex in [".tmp_", ".stage1_6b_writer.lock"]):
                continue
            f_path = Path(root_dir) / f
            rel_f = str(f_path.relative_to(run_root))
            if any(rel_f.startswith(ex) for ex in excluded_prefixes):
                continue
            h = hashlib.sha256(f_path.read_bytes()).hexdigest()
            size = f_path.stat().st_size
            authoritative_files.append((rel_f, h, size))

    authoritative_files.sort(key=lambda x: x[0])

    # Compute export ID
    export_id = compute_export_id(
        capture_mode=capture_mode,
        source_profile_id=source_profile_id,
        checkpoint_id=checkpoint_id,
        ordered_authoritative_artifacts=authoritative_files,
    )

    export_dir = run_root / "sealed_exports" / export_id
    export_dir.mkdir(parents=True, exist_ok=True)

    bytes_added = 0
    # Streamingly copy each file with guard checks
    for rel_f, h, size in authoritative_files:
        src_f = run_root / rel_f
        dst_f = export_dir / rel_f
        with guard.admitted_write(
            write_class="normal_data",
            persistent_delta_bytes=size,
            transient_peak_bytes=size,
            current_root_bytes=current_root_bytes + bytes_added,
        ):
            dst_f.parent.mkdir(parents=True, exist_ok=True)
            tmp_dst = dst_f.parent / f".tmp_{uuid.uuid4().hex}"
            tmp_dst.write_bytes(src_f.read_bytes())
            os.replace(tmp_dst, dst_f)
        bytes_added += size

    # Handle historical coverage fields if present
    hist_cov_p = run_root / "historical_coverage.json"
    hist_range_from = None
    hist_range_to = None
    hist_cov_sha = None
    if hist_cov_p.is_file():
        cov_data = json.loads(hist_cov_p.read_text(encoding="utf-8"))
        hist_range_from = cov_data.get("from_ms")
        hist_range_to = cov_data.get("to_ms")
        hist_cov_sha = hashlib.sha256(hist_cov_p.read_bytes()).hexdigest()

    artifacts_dict_list = [
        {"relative_path": r, "sha256": h, "byte_count": s}
        for r, h, s in authoritative_files
    ]

    manifest = SealedExportManifest(
        schema_version="stage1_6b_sealed_export_v1",
        export_id=export_id,
        status="complete",
        capture_mode=capture_mode,
        source_profile_id=source_profile_id,
        request_headers_profile_sha256=compute_request_headers_profile_sha256(),
        checkpoint_id=checkpoint_id,
        terminal_status_sha256=term_sha256,
        historical_range_from_ms=hist_range_from,
        historical_range_to_ms=hist_range_to,
        historical_coverage_sha256=hist_cov_sha,
        authoritative_artifacts=artifacts_dict_list,
        sealed_at_ms=int(time.time() * 1000),
    )

    manifest_delta = write_atomic_json(
        run_root=export_dir,
        relative_path="sealed_export_manifest.json",
        data_dict=manifest.to_dict(),
        write_class="ordinary_control_plane",
        guard=guard,
        current_root_bytes=current_root_bytes + bytes_added,
    )
    bytes_added += manifest_delta

    return export_dir, manifest, bytes_added


def load_sealed_export(export_dir: Path) -> Dict[str, Any]:
    """Independent consumer verification of a sealed export bundle."""
    manifest_p = export_dir / "sealed_export_manifest.json"
    if not manifest_p.is_file():
        raise ValueError(f"sealed_export_manifest_missing in {export_dir}")

    manifest_data = json.loads(manifest_p.read_text(encoding="utf-8"))
    export_id = manifest_data.get("export_id")
    if export_dir.name != export_id:
        raise ValueError(f"export_id_directory_mismatch: {export_dir.name} != {export_id}")

    if manifest_data.get("status") != "complete":
        raise ValueError(f"export_status_not_complete: {manifest_data.get('status')}")

    if manifest_data.get("source_profile_id") != SOURCE_PROFILE_ID:
        raise ValueError(f"export_profile_mismatch: {manifest_data.get('source_profile_id')} != {SOURCE_PROFILE_ID}")

    # Verify all authoritative artifacts
    artifacts = manifest_data.get("authoritative_artifacts", [])
    if not artifacts:
        raise ValueError("export_has_zero_artifacts")

    for art in artifacts:
        rel_p = art["relative_path"]
        expected_sha = art["sha256"]
        expected_size = art["byte_count"]

        file_p = export_dir / rel_p
        if not file_p.is_file():
            raise ValueError(f"missing_authoritative_artifact: {rel_p}")
        if file_p.stat().st_size != expected_size:
            raise ValueError(f"artifact_size_mismatch: {rel_p}")
        actual_sha = hashlib.sha256(file_p.read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(f"artifact_hash_mismatch: {rel_p}")

    # V2 Checkpoint validation
    chk_p = export_dir / "observer_checkpoint.json"
    if chk_p.is_file():
        chk_data = json.loads(chk_p.read_text(encoding="utf-8"))
        if chk_data.get("schema_version") != "stage1_6b_observer_checkpoint_v2":
            raise ValueError("checkpoint_v2_schema_invalid")
        if chk_data.get("source_profile_id") != SOURCE_PROFILE_ID:
            raise ValueError("checkpoint_profile_mismatch")
        validate_observer_checkpoint_status_coverage(
            chk_data.get("last_index_poll_status", ""),
            chk_data.get("last_index_poll_coverage", ""),
        )

    # V2 List Captures validation
    list_captures_dir = export_dir / "list_captures"
    if list_captures_dir.is_dir():
        for lc_file in list_captures_dir.glob("*.jsonl"):
            for line in lc_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("schema_version") != "stage1_6b_list_capture_v2":
                    raise ValueError("list_capture_v2_provenance_invalid")
                if row.get("source_profile_id") != SOURCE_PROFILE_ID:
                    raise ValueError("list_capture_v2_provenance_invalid")
                if row.get("selected_catalog_id") != SELECTED_CATALOG_ID or row.get("selected_catalog_name") != SELECTED_CATALOG_NAME:
                    raise ValueError("list_capture_v2_provenance_invalid")
                if int(row.get("selected_catalog_total", 0)) < int(row.get("article_count", 0)):
                    raise ValueError("list_capture_v2_provenance_invalid")

    # V2 Article Discoveries validation
    ad_p = export_dir / "article_discoveries.jsonl"
    if ad_p.is_file():
        for line in ad_p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("schema_version") != "stage1_6b_article_discovery_v2":
                raise ValueError("article_discovery_v2_provenance_invalid")
            if row.get("source_profile_id") != SOURCE_PROFILE_ID:
                raise ValueError("article_discovery_v2_provenance_invalid")
            if row.get("source_catalog_id") != SELECTED_CATALOG_ID or row.get("source_catalog_name") != SELECTED_CATALOG_NAME:
                raise ValueError("article_discovery_v2_provenance_invalid")

    capture_mode = manifest_data.get("capture_mode")
    if capture_mode == CaptureMode.HISTORICAL_BACKFILL.value:
        cov_sha = manifest_data.get("historical_coverage_sha256")
        if not cov_sha:
            raise ValueError("historical_coverage_sha256_missing_for_historical_export")
        cov_p = export_dir / "historical_coverage.json"
        if not cov_p.is_file():
            raise ValueError("historical_coverage_missing_in_export")
        actual_cov_sha = hashlib.sha256(cov_p.read_bytes()).hexdigest()
        if actual_cov_sha != cov_sha:
            raise ValueError("historical_coverage_sha_mismatch")
        cov_data = json.loads(cov_p.read_text(encoding="utf-8"))
        if cov_data.get("schema_version") != "stage1_6b_historical_coverage_v2":
            raise ValueError("historical_coverage_v2_provenance_invalid")
        if cov_data.get("source_profile_id") != SOURCE_PROFILE_ID:
            raise ValueError("historical_coverage_v2_provenance_invalid")
        if cov_data.get("selected_catalog_id") != SELECTED_CATALOG_ID or cov_data.get("selected_catalog_name") != SELECTED_CATALOG_NAME:
            raise ValueError("historical_coverage_v2_provenance_invalid")
        if not all(k in cov_data for k in ["selected_catalog_total_historical_max", "selected_catalog_total_sweep_a_final", "selected_catalog_total_sweep_b_final"]):
            raise ValueError("historical_coverage_v2_provenance_invalid")
        for entry in cov_data.get("sweep_a_transcript", []) + cov_data.get("sweep_b_transcript", []):
            if not (isinstance(entry, (list, tuple)) and len(entry) == 4 and entry[1] == SELECTED_CATALOG_ID):
                raise ValueError("historical_coverage_v2_provenance_invalid")

        term_p = export_dir / "terminal_status.json"
        if not term_p.is_file():
            raise ValueError("historical_terminal_status_missing")
        term_data = json.loads(term_p.read_text(encoding="utf-8"))
        if manifest_data.get("terminal_status_sha256") != hashlib.sha256(term_p.read_bytes()).hexdigest():
            raise ValueError("terminal_status_sha_mismatch")
        if term_data.get("status") != "complete" or term_data.get("terminal_reason") != "historical_backfill_complete":
            raise ValueError("historical_terminal_status_not_complete")
        if cov_data.get("from_ms") != manifest_data.get("historical_range_from_ms"):
            raise ValueError("historical_range_from_mismatch")
        if cov_data.get("to_ms") != manifest_data.get("historical_range_to_ms"):
            raise ValueError("historical_range_to_mismatch")
        if not historical_coverage_is_complete(cov_data):
            raise ValueError("historical_coverage_completion_predicate_failed")
    elif capture_mode == CaptureMode.LIVE_OBSERVED.value:
        if manifest_data.get("historical_coverage_sha256") is not None:
            raise ValueError("live_export_must_have_null_historical_coverage_sha256")
        if manifest_data.get("historical_range_from_ms") is not None:
            raise ValueError("live_export_must_have_null_historical_range")

    return manifest_data
