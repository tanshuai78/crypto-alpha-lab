import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_client import (
    Stage16EACapabilityClient,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_CORES,
    PROFILE_IDS,
    LayerAInput,
    canonical_json,
    compute_observation_id,
    compute_request_identity,
    reduce_layer_a,
    sha256_hex,
    stage1_6e_a_permissions,
    validate_response_schema,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_storage import (
    RootWriterLock,
    Stage16EAStorageGuard,
    Stage16EAStorageIntegrityError,
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

_RUN_ID_RE = re.compile(r"^stage1_6e_a_capability_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{32}$")
_STEP_A_KEYS = {
    "deployment_host_identity",
    "hostname",
    "project_root_realpath",
    "capability_root_parent_filesystem_st_dev",
    "shared_lock_filesystem_st_dev",
    "network_namespace_inode",
    "proxy_environment",
    "runtime_user_uid",
    "deployment_git_commit",
    "deployment_runtime_worktree_clean",
}


def _capability_paths(project_root: Path) -> tuple[Path, Path]:
    return (
        project_root / "data/external_signal_shadow/stage1_6e/capability_audits",
        project_root / "data/external_signal_shadow/.stage1_5_storage_guard.lock",
    )


def _validate_step_a_projection(projection: dict[str, Any]) -> None:
    if set(projection) != _STEP_A_KEYS:
        raise ValueError("step_a_projection_keys_mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", str(projection["deployment_host_identity"])):
        raise ValueError("step_a_projection_host_identity_invalid")
    if not isinstance(projection["hostname"], str) or not projection["hostname"]:
        raise ValueError("step_a_projection_hostname_invalid")
    if not isinstance(projection["project_root_realpath"], str) or not projection["project_root_realpath"]:
        raise ValueError("step_a_projection_project_root_invalid")
    if not all(isinstance(projection[key], int) and projection[key] >= 0 for key in (
        "capability_root_parent_filesystem_st_dev",
        "shared_lock_filesystem_st_dev",
        "network_namespace_inode",
        "runtime_user_uid",
    )):
        raise ValueError("step_a_projection_numeric_field_invalid")
    if projection["proxy_environment"] != "absent":
        raise ValueError("step_a_projection_proxy_environment_not_absent")
    if projection["deployment_runtime_worktree_clean"] is not True:
        raise ValueError("step_a_projection_worktree_not_clean")
    if not re.fullmatch(r"[0-9a-f]{40}", str(projection["deployment_git_commit"])):
        raise ValueError("step_a_projection_git_commit_invalid")


def get_vps_step_a_projection(project_root: Path) -> dict[str, Any]:
    proj = project_root.resolve(strict=True)
    audits_parent, shared_lock = _capability_paths(proj)
    if not audits_parent.is_dir():
        raise ValueError("capability_audits_parent_missing")
    if not shared_lock.is_file():
        raise ValueError("shared_storage_lock_missing")

    machine_id_path = Path("/etc/machine-id")
    if not machine_id_path.is_file():
        raise ValueError("machine_id_missing")
    deployment_host_id = sha256_hex(machine_id_path.read_bytes())

    # Proxy and auth env check
    proxy_vars = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy", "Authorization", "Cookie")
    proxy_env = "absent"
    for var in proxy_vars:
        if var in os.environ:
            proxy_env = "present"
            break

    netns_path = Path("/proc/self/ns/net")
    if not netns_path.exists():
        raise ValueError("network_namespace_missing")
    netns_inode = os.stat(netns_path).st_ino

    # Git commit
    commit = subprocess.check_output(
        ["git", "rev-parse", "--verify", "HEAD^{commit}"],
        cwd=str(proj),
        text=True,
    ).strip().lower()

    # Worktree clean check for configs, src, scripts
    diff1 = subprocess.run(["git", "diff", "--quiet", "--", "configs", "src", "scripts"], cwd=str(proj)).returncode == 0
    diff2 = subprocess.run(["git", "diff", "--cached", "--quiet", "--", "configs", "src", "scripts"], cwd=str(proj)).returncode == 0
    others = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "--", "configs", "src", "scripts"], cwd=str(proj), text=True).strip()
    worktree_clean = diff1 and diff2 and (len(others) == 0)

    return {
        "deployment_host_identity": deployment_host_id,
        "hostname": socket.gethostname(),
        "project_root_realpath": str(proj),
        "capability_root_parent_filesystem_st_dev": os.stat(audits_parent).st_dev,
        "shared_lock_filesystem_st_dev": os.stat(shared_lock).st_dev,
        "network_namespace_inode": netns_inode,
        "proxy_environment": proxy_env,
        "runtime_user_uid": os.geteuid(),
        "deployment_git_commit": commit,
        "deployment_runtime_worktree_clean": worktree_clean,
    }


def run_market_data_capability_audit(
    *,
    project_root: Path,
    capability_run_id: str,
    step_a_projection: dict[str, Any],
    live_public_readonly: bool = False,
    opener: Any = None,
    skip_env_checks_for_test: bool = False,
) -> dict[str, Any]:
    if not live_public_readonly:
        raise ValueError("Must specify live_public_readonly=True to authorize audit run")

    if not _RUN_ID_RE.match(capability_run_id):
        raise ValueError(f"capability_run_id does not match required grammar: {capability_run_id}")

    proj = Path(project_root).resolve(strict=True)
    audits_parent, shared_lock = _capability_paths(proj)
    _validate_step_a_projection(step_a_projection)
    if not audits_parent.is_dir():
        raise ValueError("capability_audits_parent_missing")
    if not shared_lock.is_file():
        raise ValueError("shared_storage_lock_missing")

    # Re-evaluate Step B environment against Step A
    if not skip_env_checks_for_test:
        current_proj = get_vps_step_a_projection(proj)
        _validate_step_a_projection(current_proj)
        if current_proj != step_a_projection:
            raise ValueError("step_b_environment_projection_mismatch")

    out_root = audits_parent / capability_run_id
    storage_guard = Stage16EAStorageGuard(output_root=out_root, shared_lock_path=shared_lock)
    storage_guard.validate_startup_free_space()
    # fresh root: mkdir(..., exist_ok=False)
    out_root.mkdir(parents=True, exist_ok=False)

    started_at_ms = int(time.time() * 1000)
    writer_lock = RootWriterLock(out_root, storage_guard=storage_guard)
    writer_lock.acquire()

    try:
        # Check root st_dev
        root_dev = os.stat(out_root).st_dev
        if root_dev != os.stat(audits_parent).st_dev or root_dev != os.stat(shared_lock).st_dev:
            raise RuntimeError("Filesystem st_dev mismatch between root, parent and shared lock")

        # Write execution_environment_attestation.json
        attestation = {
            "schema_version": "stage1_6e_a_execution_environment_attestation_v1",
            "deployment_host_identity": step_a_projection["deployment_host_identity"],
            "hostname": step_a_projection["hostname"],
            "project_root_realpath": step_a_projection["project_root_realpath"],
            "root_filesystem_st_dev": root_dev,
            "shared_lock_filesystem_st_dev": os.stat(shared_lock).st_dev,
            "network_namespace_inode": step_a_projection["network_namespace_inode"],
            "proxy_environment": step_a_projection["proxy_environment"],
            "runtime_user_uid": step_a_projection["runtime_user_uid"],
            "deployment_git_commit": step_a_projection["deployment_git_commit"],
            "deployment_runtime_worktree_clean": step_a_projection["deployment_runtime_worktree_clean"],
            "permissions": stage1_6e_a_permissions(),
        }
        att_sans_id = dict(attestation)
        attestation["execution_environment_id"] = sha256_hex(canonical_json(att_sans_id))
        write_atomic_json(
            out_root / "execution_environment_attestation.json",
            attestation,
            guard=storage_guard,
        )

        # Write 4 source profiles and attestations
        attestation_map: dict[str, str] = {}
        for pid in PROFILE_IDS:
            core = PROFILE_CORES[pid]
            p_sha = write_source_profile(out_root, pid, core, guard=storage_guard)
            attestation_map[pid] = p_sha
            p_att = {
                "schema_version": "stage1_6e_a_profile_attestation_v1",
                "capability_run_id": capability_run_id,
                "market_source_profile_id": pid,
                "profile_attestation_sha256": p_sha,
                "profile_attested_at_ms": started_at_ms,
                "permissions": stage1_6e_a_permissions(),
            }
            write_source_profile_attestation(out_root, pid, p_att, guard=storage_guard)

        client = Stage16EACapabilityClient(opener=opener)
        attempted_profiles: list[str] = []
        passed_profiles: list[str] = []
        profile_states: dict[str, str] = {pid: "capability_not_probed" for pid in PROFILE_IDS}
        observation_ids: dict[str, str | None] = {pid: None for pid in PROFILE_IDS}

        terminal_status_val = "complete"
        terminal_reason_val: str | None = None

        for seq, pid in enumerate(PROFILE_IDS, start=1):
            core = PROFILE_CORES[pid]
            attempted_profiles.append(pid)
            req_id = compute_request_identity(core)

            # Client fetch
            t_res = client.fetch(core, request_seq=seq)
            raw_sha: str | None = None
            raw_persisted = False
            raw_persist_failed = False

            if t_res.raw_body is not None:
                try:
                    raw_sha = write_raw_body(out_root, t_res.raw_body, guard=storage_guard)
                    raw_persisted = True
                except Exception:
                    raw_persist_failed = True

            # Parsing and schema validation if response body exists
            json_parsed = None
            json_parse_invalid = False
            schema_valid = False
            schema_invalid = False
            time_valid = False
            time_invalid = False

            if raw_persisted and t_res.raw_body is not None:
                try:
                    json_parsed = json.loads(t_res.raw_body.decode("utf-8"))
                except Exception:
                    json_parse_invalid = True

                if not json_parse_invalid and json_parsed is not None:
                    ok_schema, schema_err = validate_response_schema(core, json_parsed)
                    if ok_schema:
                        schema_valid = True
                        # For time validation: the required time fields are verified in schema check
                        time_valid = True
                    else:
                        schema_invalid = True

            layer_a_in = LayerAInput(
                profile_seq=seq,
                is_timeout=t_res.is_timeout,
                transport_error=t_res.transport_error,
                body_too_large=t_res.body_too_large,
                raw_persist_failed=raw_persist_failed,
                http_status=t_res.http_status,
                raw_persisted=raw_persisted,
                is_redirect=t_res.is_redirect,
                non_identity_encoding=t_res.non_identity_encoding,
                json_parse_invalid=json_parse_invalid,
                schema_invalid=schema_invalid,
                time_invalid=time_invalid,
                schema_valid=schema_valid,
                time_valid=time_valid,
            )

            outcome = reduce_layer_a(layer_a_in)
            profile_states[pid] = outcome.provisional_profile_status

            obs_id = compute_observation_id(
                capability_run_id=capability_run_id,
                market_source_profile_id=pid,
                profile_attestation_sha256=attestation_map[pid],
                probe_request_seq=seq,
                request_identity=req_id,
                outcome_kind=outcome.outcome_kind,
                http_status=t_res.http_status,
                raw_payload_persisted=outcome.raw_payload_persisted,
                raw_sha256=raw_sha,
                observed_bytes_lower_bound=t_res.observed_bytes_lower_bound,
            )
            observation_ids[pid] = obs_id

            obs_record = {
                "schema_version": "stage1_6e_a_capability_observation_v1",
                "market_capability_observation_id": obs_id,
                "capability_run_id": capability_run_id,
                "market_source_profile_id": pid,
                "profile_attestation_sha256": attestation_map[pid],
                "probe_request_seq": seq,
                "request_identity": req_id,
                "outcome_kind": outcome.outcome_kind,
                "local_observed_at_ms": int(time.time() * 1000),
                "http_status": t_res.http_status,
                "response_headers_subset": t_res.headers,
                "raw_payload_persisted": outcome.raw_payload_persisted,
                "raw_relative_path": f"raw/{raw_sha}.body" if raw_sha else None,
                "raw_sha256": raw_sha,
                "observed_bytes_lower_bound": t_res.observed_bytes_lower_bound,
                "payload_schema_status": outcome.payload_schema_status,
                "payload_time_status": outcome.payload_time_status,
                "profile_status": outcome.provisional_profile_status,
                "terminal_classification": outcome.terminal_classification,
                "permissions": stage1_6e_a_permissions(),
            }

            try:
                append_observation(out_root, obs_record, guard=storage_guard)
            except Exception:
                profile_states[pid] = "capability_failed"
                terminal_status_val = "failed"
                terminal_reason_val = "local_integrity_failed"
                break

            if outcome.provisional_profile_status == "capability_pass":
                passed_profiles.append(pid)
            else:
                intent = outcome.provisional_terminal_intent
                if intent.startswith("blocked:"):
                    terminal_status_val = "blocked"
                    terminal_reason_val = intent.split(":", 1)[1]
                elif intent.startswith("failed:"):
                    terminal_status_val = "failed"
                    terminal_reason_val = intent.split(":", 1)[1]
                break

        # Summary
        summary_payload = {
            "schema_version": "stage1_6e_a_capability_summary_v1",
            "capability_run_id": capability_run_id,
            "profile_states": profile_states,
            "observation_ids": observation_ids,
            "historical_retention_coverage": "not_evaluable",
            "event_market_coverage": "not_evaluable",
            "fee_coverage_status": "not_evaluated_in_stage1_6e_a",
            "permissions": stage1_6e_a_permissions(),
        }
        try:
            write_capability_summary(out_root, summary_payload, guard=storage_guard)
        except Exception as exc:
            terminal_status_val = "failed"
            terminal_reason_val = (
                "local_integrity_failed"
                if isinstance(exc, Stage16EAStorageIntegrityError)
                else "storage_write_blocked"
            )

        # Terminal status
        term_payload = {
            "schema_version": "stage1_6e_a_terminal_status_v1",
            "capability_run_id": capability_run_id,
            "status": terminal_status_val,
            "terminal_reason": terminal_reason_val,
            "started_at_ms": started_at_ms,
            "terminal_at_ms": int(time.time() * 1000),
            "profile_attestation_sha256_by_id": attestation_map,
            "attempted_profile_ids": attempted_profiles,
            "passed_profile_ids": passed_profiles,
            "accounted_root_bytes": sum(f.stat().st_size for f in out_root.rglob("*") if f.is_file()),
            "permissions": stage1_6e_a_permissions(),
        }
        try:
            write_terminal_status(out_root, term_payload, guard=storage_guard)
        except Exception as exc:
            raise RuntimeError("terminal_status_persistence_failed") from exc

        # Manifest if complete
        if terminal_status_val == "complete" and len(passed_profiles) == 4:
            manifest_payload_base = {
                "schema_version": "stage1_6e_a_manifest_v1",
                "capability_run_id": capability_run_id,
                "terminal_status_sha256": sha256_hex((out_root / "terminal_status.json").read_bytes()),
                "profile_attestation_sha256_by_id": attestation_map,
                "permissions": stage1_6e_a_permissions(),
            }
            try:
                write_manifest(out_root, manifest_payload_base, guard=storage_guard)
            except Exception as exc:
                raise RuntimeError("manifest_persistence_failed") from exc
            complete, blockers = verify_complete_bundle(out_root)
            if not complete:
                raise RuntimeError(f"complete_bundle_verification_failed:{','.join(blockers)}")

        return {
            "status": terminal_status_val,
            "terminal_reason": terminal_reason_val,
            "attempted_profiles_count": len(attempted_profiles),
            "passed_profiles_count": len(passed_profiles),
            "output_root": str(out_root),
        }

    finally:
        writer_lock.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1.6E-A Market-Data Source Capability Audit Runner")
    parser.add_argument("--step-a-preflight", action="store_true", help="Print Step A environment projection and exit")
    parser.add_argument("--live-public-readonly", action="store_true", help="Authorize read-only capability audit run")
    parser.add_argument("--run-id", type=str, help="Stage 1.6E-A run ID")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory path")
    parser.add_argument("--step-a-authorization", type=str, help="Path to Step A authorization JSON transcript")

    args = parser.parse_args()
    proj_root = Path(args.project_root).resolve(strict=True)

    if args.step_a_preflight:
        proj_data = get_vps_step_a_projection(proj_root)
        print(json.dumps(proj_data, indent=2, sort_keys=True))
        sys.exit(0)

    if not args.live_public_readonly:
        print("Error: --live-public-readonly is required to run capability audit", file=sys.stderr)
        sys.exit(1)

    if not args.run_id or not args.step_a_authorization:
        print("Error: --run-id and --step-a-authorization are required", file=sys.stderr)
        sys.exit(1)

    auth_path = Path(args.step_a_authorization)
    if not auth_path.is_file():
        print(f"Error: Step A authorization file not found: {auth_path}", file=sys.stderr)
        sys.exit(1)

    step_a_data = json.loads(auth_path.read_text(encoding="utf-8"))
    res = run_market_data_capability_audit(
        project_root=proj_root,
        capability_run_id=args.run_id,
        step_a_projection=step_a_data,
        live_public_readonly=True,
    )

    print(json.dumps(res, indent=2))
    if res["status"] != "complete":
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
