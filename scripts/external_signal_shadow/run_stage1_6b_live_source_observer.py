"""Live source observer runner for Stage 1.6B with lifetime writer lock and bounded epoch."""

import argparse
import datetime
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from configs import base
from src.research.external_signal_shadow.stage1_6b_canonical_source_client import (
    Stage16BCanonicalClient,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    SOURCE_PROFILE_ID,
    CaptureMode,
    CaptureRunContract,
    TerminalReason,
    TerminalStatusRecord,
    compute_request_headers_profile_sha256,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_observer import (
    Stage16BObserver,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import (
    RootWriterLock,
    Stage16BStorageGuard,
    copy_probe_attestation_to_root,
    reconcile_and_write_checkpoint,
    seal_export,
    validate_probe_attestation_path,
    validate_run_root_path,
    write_capture_run_contract,
    write_terminal_status,
)


class LiveObserverRunnerError(RuntimeError):
    """Raised when live observer runner encounters a fatal error."""
    pass


def run_live_source_observer(
    attestation_path: Path,
    live_public_readonly: bool,
    run_id: Optional[str] = None,
    resume: bool = False,
    max_polls: Optional[int] = None,
    max_seconds: Optional[int] = None,
    project_root: Optional[Path] = None,
    opener: Optional[Callable[..., Any]] = None,
    sleep_func: Optional[Callable[[float], None]] = None,
) -> Path:
    """Run Stage 1.6B live observation loop under lifetime writer lock."""
    if not live_public_readonly:
        raise ValueError("live_public_readonly_required: must explicitly supply --live-public-readonly")

    epoch_max_sec = base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_EPOCH_MAX_SECONDS
    if max_seconds is not None and max_seconds > epoch_max_sec:
        raise ValueError(f"max_seconds_exceeds_epoch_limit: {max_seconds} > {epoch_max_sec}")

    p_root = (project_root or Path.cwd()).resolve()
    run_started_at_ms = int(time.time() * 1000)

    # 1. Validate probe attestation
    validated_att_path = validate_probe_attestation_path(attestation_path, project_root=p_root)
    att_data = json.loads(validated_att_path.read_text(encoding="utf-8"))

    if att_data.get("source_profile_id") != SOURCE_PROFILE_ID:
        raise ValueError(f"attestation_profile_mismatch: {att_data.get('source_profile_id')} != {SOURCE_PROFILE_ID}")

    expected_headers_sha = compute_request_headers_profile_sha256()
    if att_data.get("request_headers_profile_sha256") != expected_headers_sha:
        raise ValueError("attestation_headers_sha_mismatch")

    if att_data.get("probe_attested_at_ms", 0) > run_started_at_ms:
        raise ValueError("probe_attested_in_future")

    att_sha256 = hashlib.sha256(validated_att_path.read_bytes()).hexdigest()

    # 2. Output root validation
    effective_run_id = run_id or f"live_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    run_root = p_root / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / effective_run_id
    validated_root = validate_run_root_path(
        run_root,
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        require_fresh=(not resume),
        project_root=p_root,
    )

    if not resume:
        validated_root.mkdir(parents=True, exist_ok=False)

    # 3. Lifetime Writer Lock acquisition before any mutable artifact or network call
    with RootWriterLock(validated_root):
        guard = Stage16BStorageGuard(output_root=validated_root)
        recovered_checkpoint = None
        recovered_root_bytes = None

        if not resume:
            guard.validate_startup_free_space()
            contract = CaptureRunContract(
                schema_version="stage1_6b_capture_run_contract_v1",
                run_id=effective_run_id,
                capture_mode=CaptureMode.LIVE_OBSERVED.value,
                source_profile_id=SOURCE_PROFILE_ID,
                source_profile_attestation_sha256=att_sha256,
                run_started_at_ms=run_started_at_ms,
            )
            write_capture_run_contract(validated_root, contract, guard, 0)
            copy_probe_attestation_to_root(validated_root, validated_att_path, guard, 0)
        else:
            # On resume: verify terminal_status is absent and sealed export is absent
            if (validated_root / "terminal_status.json").is_file():
                raise ValueError("cannot_resume_terminal_root")
            sealed_dir = validated_root / "sealed_exports"
            if sealed_dir.is_dir() and any(sealed_dir.iterdir()):
                raise ValueError("cannot_resume_sealed_root")

            contract_path = validated_root / "capture_run_contract.json"
            copied_attestation_path = validated_root / "source_profile_probe_attestation.json"
            if not contract_path.is_file() or not copied_attestation_path.is_file():
                raise ValueError("cannot_resume_missing_run_contract_or_attestation")
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            if (
                contract.get("run_id") != effective_run_id
                or contract.get("capture_mode") != CaptureMode.LIVE_OBSERVED.value
                or contract.get("source_profile_id") != SOURCE_PROFILE_ID
                or contract.get("source_profile_attestation_sha256") != att_sha256
                or hashlib.sha256(copied_attestation_path.read_bytes()).hexdigest() != att_sha256
            ):
                raise ValueError("cannot_resume_run_contract_or_attestation_mismatch")
            recovered_checkpoint, recovered_root_bytes = reconcile_and_write_checkpoint(validated_root, guard)

        client = Stage16BCanonicalClient(live_public_readonly=True, opener=opener)
        observer = Stage16BObserver(
            run_root=validated_root,
            run_id=effective_run_id,
            capture_mode=CaptureMode.LIVE_OBSERVED.value,
            source_profile_attestation_sha256=att_sha256,
            guard=guard,
            client=client,
            recovered_checkpoint=recovered_checkpoint,
            recovered_root_bytes=recovered_root_bytes,
        )

        poll_interval = base.EXTERNAL_SIGNAL_STAGE1_6B_LIVE_POLL_INTERVAL_SEC
        sleeper = sleep_func or time.sleep

        # Compute deadlines
        epoch_deadline_ms = run_started_at_ms + int(epoch_max_sec * 1000)
        max_sec_deadline_ms = run_started_at_ms + int(max_seconds * 1000) if max_seconds is not None else epoch_deadline_ms
        effective_deadline_ms = min(epoch_deadline_ms, max_sec_deadline_ms)

        polls_executed = 0
        terminal_reason = TerminalReason.EPOCH_COMPLETE.value

        while True:
            now_ms = int(time.time() * 1000)
            if now_ms >= effective_deadline_ms:
                if max_seconds is not None and max_seconds < epoch_max_sec:
                    terminal_reason = TerminalReason.TEST_BOUND.value
                else:
                    terminal_reason = TerminalReason.EPOCH_COMPLETE.value
                break

            observer.execute_poll(now_ms=now_ms)
            polls_executed += 1

            if max_polls is not None and polls_executed >= max_polls:
                terminal_reason = TerminalReason.TEST_BOUND.value
                break

            # Sleep until next poll interval
            sleep_sec = float(poll_interval)
            sleeper(sleep_sec)

        # 4. Write terminal status
        term_rec = TerminalStatusRecord(
            schema_version="stage1_6b_terminal_status_v1",
            run_id=effective_run_id,
            capture_mode=CaptureMode.LIVE_OBSERVED.value,
            source_profile_id=SOURCE_PROFILE_ID,
            status="complete",
            terminal_reason=terminal_reason,
            final_checkpoint_id=observer.prior_checkpoint_id,
            terminated_at_ms=int(time.time() * 1000),
        )
        write_terminal_status(validated_root, term_rec, guard, observer.accounted_root_bytes)

        # 5. Seal export
        seal_export(validated_root, guard, observer.accounted_root_bytes)

    return validated_root


def main():
    parser = argparse.ArgumentParser(description="Stage 1.6B Live Source Observer Runner")
    parser.add_argument("--source-profile-attestation", type=Path, required=True, help="Path to attested probe JSON")
    parser.add_argument("--live-public-readonly", action="store_true", default=False, help="Explicit readonly network permission")
    parser.add_argument("--run-id", type=str, default=None, help="Optional run ID")
    parser.add_argument("--resume", action="store_true", default=False, help="Resume existing unsealed run")
    parser.add_argument("--max-polls", type=int, default=None, help="Optional poll execution limit")
    parser.add_argument("--max-seconds", type=int, default=None, help="Optional time execution limit")
    parser.add_argument("--project-root", type=Path, default=None, help="Root path of the project")

    args = parser.parse_args()

    try:
        root_dir = run_live_source_observer(
            attestation_path=args.source_profile_attestation,
            live_public_readonly=args.live_public_readonly,
            run_id=args.run_id,
            resume=args.resume,
            max_polls=args.max_polls,
            max_seconds=args.max_seconds,
            project_root=args.project_root,
        )
        print(f"SUCCESS: Live observation finished at {root_dir}")
        sys.exit(0)
    except Exception as exc:
        print(f"FAILED: Live observation failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
