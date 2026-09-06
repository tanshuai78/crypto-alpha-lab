#!/usr/bin/env python3
"""Stage 1.6E-B Live Semantic Trigger and Event-Level Market-Data Observer CLI Runner."""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from configs import base
from scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit import (
    get_vps_step_a_projection,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer import (
    C5WorkItem,
    Stage16EBEventObserver,
    Stage16EBSupervisor,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_client import (
    Stage16EBPublicClient,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    stage1_6e_b_permissions,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_source import (
    Stage16EBSourceConsumer,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage import (
    GlobalSupervisorLock,
    Stage16EBStorageGuard,
    validate_e_a_runtime_gate,
    validate_post_root_equality,
)

_SOURCE_RUN_ID_RE = re.compile(r"^stage1_6b_live_source_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{32}$")
_GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 1.6E-B Live Semantic Trigger and Event Market-Data Observer runner."
    )
    parser.add_argument("--e-a-root", required=True, help="Path to E-A audit root directory.")
    parser.add_argument("--source-root", required=True, help="Path to 1.6D live source root directory.")
    parser.add_argument("--source-run-id", required=True, help="Authorized 1.6D live source run ID.")
    parser.add_argument("--e-b-supervisor-root", required=True, help="Path to E-B supervisor root directory.")
    parser.add_argument("--e-b-events-root", required=True, help="Path to E-B events directory.")
    parser.add_argument("--deployment-git-commit", required=True, help="40-hex deployment commit SHA.")
    parser.add_argument("--shared-storage-lock", default=None, help="Path to shared storage guard lock.")
    parser.add_argument("--once", action="store_true", default=False)
    parser.add_argument("--poll-interval-s", type=float, default=1.0)
    return parser.parse_args(argv)


def orchestrate_c5_event_creation(
    *,
    c5_item: C5WorkItem,
    supervisor: Stage16EBSupervisor,
    canonical_project_root: Path,
    e_a_root: Path,
    deployment_git_commit: str,
) -> Path:
    """Runner is the single C5 orchestration owner for deterministic fresh event roots."""
    # 1. Fresh Step-A projection for each fresh-root gate
    event_step_a = get_vps_step_a_projection(canonical_project_root)

    # 2. Verify exact E-A authority and PRE-ROOT equality
    e_a_gate_info = validate_e_a_runtime_gate(
        e_a_root=e_a_root,
        step_a_projection=event_step_a,
    )

    # 3. Dedicated supervisor root creation (only mkdir owner, acquires/retains writer lock)
    event_dir, lock = supervisor.create_event_root_dir(c5_item)
    try:
        # 4. POST-ROOT filesystem equality gate
        validate_post_root_equality(
            root=event_dir,
            lock_path=event_dir / ".stage1_6e_b_event_writer.lock",
            step_a_projection=event_step_a,
            e_a_attestation=e_a_gate_info["environment_attestation"],
        )

        # 5. Populate and activate
        supervisor.populate_and_activate_event_root(
            c5_item=c5_item,
            lock=lock,
            step_a_projection=event_step_a,
            deployment_git_commit=deployment_git_commit,
            e_a_gate_info=e_a_gate_info,
        )
    except Exception:
        lock.release()
        raise

    return event_dir


def run_observer(args: argparse.Namespace) -> int:
    # 0. Invariant assertion
    if base.RISK_LIVE_TRADING_ENABLED is not False:
        raise RuntimeError("RISK_LIVE_TRADING_ENABLED must be False")
    perms = stage1_6e_b_permissions()
    if not all(v is False for v in perms.values()):
        raise RuntimeError("All Stage 1.6E-B permissions must be False")

    # 1. Path and project root validations
    canonical_project_root = Path(__file__).resolve().parents[2]
    if not canonical_project_root.is_dir() or canonical_project_root.is_symlink():
        raise ValueError(f"canonical_project_root_invalid: {canonical_project_root}")
    if not (canonical_project_root / "configs" / "base.py").is_file():
        raise ValueError(f"canonical_project_root_missing_configs: {canonical_project_root}")
    if Path.cwd().resolve(strict=True) != canonical_project_root:
        raise ValueError(f"working_directory_must_be_canonical_project_root: {Path.cwd()} vs {canonical_project_root}")

    e_a_root = Path(args.e_a_root)
    source_root = Path(args.source_root)
    supervisor_root = Path(args.e_b_supervisor_root)
    events_root = Path(args.e_b_events_root)

    for name, p in [
        ("e_a_root", e_a_root),
        ("source_root", source_root),
        ("e_b_supervisor_root", supervisor_root),
        ("e_b_events_root", events_root),
    ]:
        if not p.is_absolute():
            raise ValueError(f"absolute_path_required: {name} ({p})")
        if p.is_symlink():
            raise ValueError(f"symlink_forbidden: {name} ({p})")

    if not _SOURCE_RUN_ID_RE.match(args.source_run_id):
        raise ValueError(f"invalid_source_run_id_format: {args.source_run_id}")

    if not _GIT_COMMIT_RE.match(args.deployment_git_commit):
        raise ValueError(f"invalid_deployment_git_commit: {args.deployment_git_commit}")

    if args.shared_storage_lock is not None:
        shared_lock = Path(args.shared_storage_lock)
        if not shared_lock.is_absolute():
            raise ValueError(f"absolute_path_required: shared_storage_lock ({shared_lock})")
        if shared_lock.is_symlink():
            raise ValueError(f"symlink_forbidden: shared_storage_lock ({shared_lock})")
    else:
        shared_lock = supervisor_root.parent / ".stage1_5_storage_guard.lock"

    # 2. Step-A projection and E-A Runtime Gate before any source or client operation
    supervisor_step_a = get_vps_step_a_projection(canonical_project_root)
    e_a_gate_info = validate_e_a_runtime_gate(
        e_a_root=e_a_root,
        step_a_projection=supervisor_step_a,
    )

    # 3. Storage Guard preflight
    guard = Stage16EBStorageGuard(
        shared_lock_path=shared_lock,
        supervisor_root=supervisor_root,
        event_root=events_root,
    )
    guard.validate_startup_free_space()

    # 4. Supervisor and components initialization
    supervisor = Stage16EBSupervisor(
        supervisor_root=supervisor_root,
        events_root=events_root,
        e_a_root=e_a_root,
        guard=guard,
    )

    source_consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_root,
        authorized_run_id=args.source_run_id,
        consumer_checkpoint_path=supervisor_root / "source_consumer_checkpoint.json",
    )

    public_client: Stage16EBPublicClient | None = None

    supervisor_lock_path = supervisor_root.parent / ".stage1_6e_b_supervisor.lock"
    with GlobalSupervisorLock(supervisor_lock_path):
        supervisor.initialize_supervisor_root(
            step_a_projection=supervisor_step_a,
            deployment_git_commit=args.deployment_git_commit,
            e_a_manifest_id=e_a_gate_info["manifest_id"],
            e_a_manifest_sha256=e_a_gate_info["manifest_sha256"],
            e_a_attestation_sha256=e_a_gate_info["environment_attestation_sha256"],
            e_a_attestation=e_a_gate_info["environment_attestation"],
        )

        # Startup recovery
        now_ms = int(time.time() * 1000)
        rec_status, c5_rec = supervisor.check_startup_recovery(
            now_ms,
            step_a_projection=supervisor_step_a,
            e_a_gate_info=e_a_gate_info,
            deployment_git_commit=args.deployment_git_commit,
        )
        if rec_status == "C5_PENDING" and c5_rec is not None:
            orchestrate_c5_event_creation(
                c5_item=c5_rec,
                supervisor=supervisor,
                canonical_project_root=canonical_project_root,
                e_a_root=e_a_root,
                deployment_git_commit=args.deployment_git_commit,
            )

        while True:
            now_ms = int(time.time() * 1000)

            # 1. Step source stream if no active event
            if supervisor.get_active_event_id() is None:
                c5_item = supervisor.step_source_stream(source_consumer, current_time_ms=now_ms)
                if c5_item is not None:
                    orchestrate_c5_event_creation(
                        c5_item=c5_item,
                        supervisor=supervisor,
                        canonical_project_root=canonical_project_root,
                        e_a_root=e_a_root,
                        deployment_git_commit=args.deployment_git_commit,
                    )

            # 2. Check if active event exists & observe
            active_event_dir = supervisor.get_active_event_root()
            if active_event_dir is not None:
                if public_client is None:
                    public_client = Stage16EBPublicClient()
                with Stage16EBEventObserver(active_event_dir, public_client, guard=guard) as observer:
                    observer.resume_and_validate()
                    # Step due slots
                    for slot in observer.slots:
                        if observer.checkpoint and slot.slot_id not in observer.checkpoint.completed_slot_ids_ordered:
                            if now_ms >= slot.due_at_ms:
                                observer.step_slot(slot, current_time_ms=now_ms)

                    # Finalize if complete
                    if observer.checkpoint and observer.contract:
                        if len(observer.checkpoint.completed_slot_ids_ordered) == observer.contract.expected_slot_count:
                            observer.finalize_terminal(current_time_ms=now_ms)

                supervisor.try_release_terminal_capacity(now_ms)

            if args.once:
                break
            time.sleep(args.poll_interval_s)

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run_observer(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
