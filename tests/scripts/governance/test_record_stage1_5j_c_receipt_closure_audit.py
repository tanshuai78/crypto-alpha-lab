"""Contract and lifecycle tests for Stage 1.5J-C Receipt Closure Evidence Recorder.

Tier: recorder_contract_unit_only.
Proves no raw/provenance/domain/verifier claim.
Derives canonical validation fixtures strictly from real repository and validation files (L1 Rule 15).
"""

from __future__ import annotations

import ast
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

RECORDER_SCRIPT = Path("scripts/governance/record_stage1_5j_c_receipt_closure_audit.py")

PARENT_DESIGN_PATH = "docs/designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md"
PARENT_DESIGN_SHA = "32d5130806489c0848748060835a7c0fb8f1715a3f9fb6b479c2f02cff5d4e45"

PARENT_R1_PLAN_PATH = "docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md"
PARENT_R1_PLAN_SHA = "827d1bbcabdd02f1d9d566752f1185e2e7aef49bb2a236660c8fc6a621d0ebe3"

DELTA_DESIGN_PATH = "docs/designs/2026-10-25-external-signal-shadow-lab-stage1-5j-c-receipt-closure-lifecycle-design-delta_CN.md"
DELTA_DESIGN_SHA = "da901f94fd441f3070c744cacf6337dd1d181e8ecae5f2076c62e1e8c76b584d"

DELTA_PLAN_PATH = "docs/plans/2026-10-25-external-signal-shadow-lab-stage1-5j-c-receipt-closure-lifecycle-implementation-plan_CN.md"
DELTA_PLAN_SHA = "3dc23e936bc5d5ab02f9977ed8e025377e38e0c0a64642486fd62b7144818fca"

RUN_ID = "stage1_5j_c_launch_time_path_feasibility_20261024T102858Z"
CANONICAL_VAL_ROOT = Path("/private/tmp/stage1_5j_c_launch_time_path_feasibility_20261024T102858Z")
CANONICAL_VAL_AUTH_DIR = Path(".git/plan-execution/stage1_5j_c/827d1bbcabdd02f1d9d566752f1185e2e7aef49bb2a236660c8fc6a621d0ebe3") / RUN_ID

MANIFEST_SHA = "d9b91fd5544e0c7299b06b0e9f7fba152d001c6b8224443d8b0cbe6ec0c8f2ab"
SUMMARY_SHA = "c48f4a40f82e6c6f9ff5f8f4a59fbd5861458c2bf4c656ce5cce6674f4aa2e3b"
REVIEW_SHA = "4e372da9b9390028f066c0e0af77891d79f5a9ad10652ddfb0c2483b6ce4c469"

REPORT_REL_PATH = "evidence/receipt_closure_audit_report.md"


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _file_seal(rel_path: str, b: bytes) -> dict[str, Any]:
    return {
        "relative_path": rel_path,
        "sha256": _sha256_bytes(b),
        "size_bytes": len(b),
    }


def _dump_canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _build_test_environment(tmp_path: Path, recorder_source_bytes: bytes | None = None) -> dict[str, Any]:
    """Construct an isolated test fixture environment in tmp_path derived from canonical upstream sources (P1-01)."""
    proj = tmp_path / "repo"
    proj.mkdir(parents=True)

    # 1. Scripts dir and recorder
    rec_script = proj / "scripts/governance/record_stage1_5j_c_receipt_closure_audit.py"
    rec_script.parent.mkdir(parents=True, exist_ok=True)
    if recorder_source_bytes is None:
        if RECORDER_SCRIPT.exists():
            recorder_source_bytes = RECORDER_SCRIPT.read_bytes()
        else:
            recorder_source_bytes = b"# test recorder\n"
    rec_script.write_bytes(recorder_source_bytes)
    rec_sha = _sha256_bytes(recorder_source_bytes)

    # 2. Documents (derived by copying real documents from repo)
    for doc_path in (PARENT_DESIGN_PATH, PARENT_R1_PLAN_PATH, DELTA_DESIGN_PATH, DELTA_PLAN_PATH):
        dest = proj / doc_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(doc_path), dest)

    parent_des_bytes = (proj / PARENT_DESIGN_PATH).read_bytes()
    parent_plan_bytes = (proj / PARENT_R1_PLAN_PATH).read_bytes()
    delta_des_bytes = (proj / DELTA_DESIGN_PATH).read_bytes()
    delta_plan_bytes = (proj / DELTA_PLAN_PATH).read_bytes()

    parent_des_seal = _file_seal(PARENT_DESIGN_PATH, parent_des_bytes)
    parent_plan_seal = _file_seal(PARENT_R1_PLAN_PATH, parent_plan_bytes)
    delta_des_seal = _file_seal(DELTA_DESIGN_PATH, delta_des_bytes)
    delta_plan_seal = _file_seal(DELTA_PLAN_PATH, delta_plan_bytes)

    # 3. Validation authority directory (derived by copying real canonical files)
    auth_dir = proj / f".git/plan-execution/stage1_5j_c/{parent_plan_seal['sha256']}/{RUN_ID}"
    auth_dir.mkdir(parents=True, exist_ok=True)
    ev_dir = auth_dir / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)

    val_auth_files = [
        "user_receipt_generation_approval.txt",
        "user_receipt_generation_approval.txt.sha256",
        "authorization_release.json",
        "authorization_release.json.sha256",
        "run_authorization.json",
    ]
    for fn in val_auth_files:
        shutil.copy2(CANONICAL_VAL_AUTH_DIR / fn, auth_dir / fn)

    u_app_bytes = (auth_dir / "user_receipt_generation_approval.txt").read_bytes()
    val_u_app_seal = _file_seal("user_receipt_generation_approval.txt", u_app_bytes)

    rel_bytes = (auth_dir / "authorization_release.json").read_bytes()
    val_rel_seal = _file_seal("authorization_release.json", rel_bytes)

    run_auth_bytes = (auth_dir / "run_authorization.json").read_bytes()
    val_run_auth_seal = _file_seal("run_authorization.json", run_auth_bytes)

    # 4. Copy producer lifecycle evidence from real directory
    shutil.copy2(CANONICAL_VAL_AUTH_DIR / "evidence/producer_lifecycle_evidence.json", ev_dir / "producer_lifecycle_evidence.json")
    shutil.copy2(CANONICAL_VAL_AUTH_DIR / "evidence/producer_lifecycle_evidence.json.sha256", ev_dir / "producer_lifecycle_evidence.json.sha256")

    # 5. Validation root (copy real triplet from CANONICAL_VAL_ROOT to tmp_path)
    val_root = tmp_path / "val_root"
    val_root.mkdir(parents=True, exist_ok=True)
    for fn in ("manifest.json", "summary.json", "review_CN.md"):
        shutil.copy2(CANONICAL_VAL_ROOT / fn, val_root / fn)

    m_bytes = (val_root / "manifest.json").read_bytes()
    s_bytes = (val_root / "summary.json").read_bytes()
    r_bytes = (val_root / "review_CN.md").read_bytes()

    m_sha = _sha256_bytes(m_bytes)
    s_sha = _sha256_bytes(s_bytes)
    r_sha = _sha256_bytes(r_bytes)

    # Update final_root in producer_lifecycle_evidence to point to val_root
    prod_ev = json.loads((ev_dir / "producer_lifecycle_evidence.json").read_text())
    prod_ev["final_root"] = str(val_root)
    prod_ev_bytes = _dump_canonical_json_bytes(prod_ev)
    (ev_dir / "producer_lifecycle_evidence.json").write_bytes(prod_ev_bytes)
    (ev_dir / "producer_lifecycle_evidence.json.sha256").write_text(
        f"{_sha256_bytes(prod_ev_bytes)}  producer_lifecycle_evidence.json\n"
    )

    # Build report text
    report_text = "closure_verdict=receipt_closure_audited\n# Stage 1.5J-C Audit Report\nAll checks passed.\n"
    report_bytes = report_text.encode("utf-8")
    report_sha = _sha256_bytes(report_bytes)

    # Build payload object
    payload_obj = {
        "artifact_kind": "validation_only",
        "audit_payload_schema_version": 1,
        "manifest_sha256": m_sha,
        "receipt_root_absolute_path": str(val_root),
        "recorder_delta_design": delta_des_seal,
        "recorder_implementation_plan": delta_plan_seal,
        "recorder_relative_path": "scripts/governance/record_stage1_5j_c_receipt_closure_audit.py",
        "recorder_source_sha256": rec_sha,
        "report_relative_path": REPORT_REL_PATH,
        "report_sha256": report_sha,
        "report_utf8": report_text,
        "review_sha256": r_sha,
        "run_id": RUN_ID,
        "summary_sha256": s_sha,
        "validation_authorization_release": val_rel_seal,
        "validation_design": parent_des_seal,
        "validation_plan": parent_plan_seal,
        "validation_run_authorization": val_run_auth_seal,
        "validation_user_receipt_generation_approval": val_u_app_seal,
        "verdict": "receipt_closure_audited",
        "verifier_relative_path": "scripts/governance/verify_stage1_5j_c_receipt_schema.py",
        "verifier_source_sha256": "ef05b213a2955b4a5c89a0153be40f25067f637d4f28f9ac4df63a7d0df2effe",
    }
    payload_bytes = _dump_canonical_json_bytes(payload_obj)
    payload_sha = _sha256_bytes(payload_bytes)

    # 6. Recording authority files in auth_dir (15 lines exact)
    rec_approval_lines = [
        "operation=record_stage1_5j_c_receipt_closure_audit_once",
        f"run_id={RUN_ID}",
        f"validation_receipt_root_absolute_path={val_root}",
        f"report_relative_path={REPORT_REL_PATH}",
        f"audit_decision_payload_sha256={payload_sha}",
        f"validation_design_relative_path={PARENT_DESIGN_PATH}",
        f"validation_design_sha256={parent_des_seal['sha256']}",
        f"validation_plan_relative_path={PARENT_R1_PLAN_PATH}",
        f"validation_plan_sha256={parent_plan_seal['sha256']}",
        f"recorder_delta_design_relative_path={DELTA_DESIGN_PATH}",
        f"recorder_delta_design_sha256={delta_des_seal['sha256']}",
        f"recorder_implementation_plan_relative_path={DELTA_PLAN_PATH}",
        f"recorder_implementation_plan_sha256={delta_plan_seal['sha256']}",
        "recorder_relative_path=scripts/governance/record_stage1_5j_c_receipt_closure_audit.py",
        f"recorder_source_sha256={rec_sha}",
    ]
    rec_app_bytes = "\n".join(rec_approval_lines).encode("utf-8") + b"\n"
    (auth_dir / "user_audit_recording_approval.txt").write_bytes(rec_app_bytes)
    (auth_dir / "user_audit_recording_approval.txt.sha256").write_text(
        f"{_sha256_bytes(rec_app_bytes)}  user_audit_recording_approval.txt\n"
    )

    rec_release_obj = {
        "alpha_claim_allowed": False,
        "audit_decision_payload_sha256": payload_sha,
        "consumer_promotion_allowed": False,
        "execution_allowed": False,
        "live_trading_allowed": False,
        "network_allowed": False,
        "paper_trading_allowed": False,
        "receipt_regeneration_allowed": False,
        "recorder": _file_seal("scripts/governance/record_stage1_5j_c_receipt_closure_audit.py", recorder_source_bytes),
        "recorder_delta_design": delta_des_seal,
        "recorder_implementation_plan": delta_plan_seal,
        "release_schema_version": 1,
        "release_state": "user_message_verified_and_released",
        "report_relative_path": REPORT_REL_PATH,
        "run_id": RUN_ID,
        "signal_allowed": False,
        "user_audit_recording_approval": _file_seal("user_audit_recording_approval.txt", rec_app_bytes),
        "validation_design": parent_des_seal,
        "validation_plan": parent_plan_seal,
        "validation_receipt_root_absolute_path": str(val_root),
    }
    rec_rel_bytes = _dump_canonical_json_bytes(rec_release_obj)
    (auth_dir / "audit_recording_release.json").write_bytes(rec_rel_bytes)
    (auth_dir / "audit_recording_release.json.sha256").write_text(
        f"{_sha256_bytes(rec_rel_bytes)}  audit_recording_release.json\n"
    )

    # Write payload file outside repo
    payload_file = tmp_path / "payload.json"
    payload_file.write_bytes(payload_bytes)

    return {
        "proj": proj,
        "auth_dir": auth_dir,
        "ev_dir": ev_dir,
        "val_root": val_root,
        "payload_file": payload_file,
        "payload_obj": payload_obj,
        "payload_bytes": payload_bytes,
        "payload_sha": payload_sha,
        "report_bytes": report_bytes,
        "rec_script": rec_script,
    }


def _run_recorder(proj: Path, payload_path: Path, extra_args: list[str] | None = None, env_override: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    script = proj / "scripts/governance/record_stage1_5j_c_receipt_closure_audit.py"
    args = [sys.executable, str(script), str(payload_path)]
    if extra_args:
        args.extend(extra_args)
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    return subprocess.run(
        args,
        cwd=str(proj),
        capture_output=True,
        text=True,
        env=env,
    )


# ---------------------------------------------------------------------------
# Task 1 & Finding Remediation Tests
# ---------------------------------------------------------------------------


def test_recorder_single_positional_payload_and_help(tmp_path: Path) -> None:
    """Recorder must accept exactly one positional payload; reject extra args or flags."""
    env = _build_test_environment(tmp_path)
    proj = env["proj"]
    payload_file = env["payload_file"]

    p_help = subprocess.run(
        [sys.executable, str(env["rec_script"]), "--help"],
        cwd=str(proj),
        capture_output=True,
        text=True,
    )
    assert p_help.returncode == 0
    assert "usage:" in p_help.stdout.lower()

    p_no_arg = subprocess.run(
        [sys.executable, str(env["rec_script"])],
        cwd=str(proj),
        capture_output=True,
        text=True,
    )
    assert p_no_arg.returncode != 0

    p_extra = _run_recorder(proj, payload_file, ["extra_arg"])
    assert p_extra.returncode != 0

    p_flag = _run_recorder(proj, payload_file, ["--override", "1"])
    assert p_flag.returncode != 0


def test_recorder_rejects_non_canonical_or_symlink_payload(tmp_path: Path) -> None:
    """Payload must be a non-symlink regular file, canonical JSON, with exact key set."""
    env = _build_test_environment(tmp_path)
    proj = env["proj"]

    sym_payload = tmp_path / "sym_payload.json"
    os.symlink(env["payload_file"], sym_payload)
    p_sym = _run_recorder(proj, sym_payload)
    assert p_sym.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_symlink_or_escape" in (p_sym.stderr + p_sym.stdout)

    bad_json = tmp_path / "bad_json.json"
    bad_json.write_text(json.dumps(env["payload_obj"], indent=2) + "\n")
    p_bad_json = _run_recorder(proj, bad_json)
    assert p_bad_json.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_payload_mismatch" in (p_bad_json.stderr + p_bad_json.stdout)

    bad_obj = dict(env["payload_obj"])
    del bad_obj["verdict"]
    bad_key_file = tmp_path / "bad_key.json"
    bad_key_file.write_bytes(_dump_canonical_json_bytes(bad_obj))
    p_key = _run_recorder(proj, bad_key_file)
    assert p_key.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_payload_mismatch" in (p_key.stderr + p_key.stdout)

    bad_extra_obj = dict(env["payload_obj"])
    bad_extra_obj["extra_field"] = "bad"
    bad_extra_file = tmp_path / "bad_extra.json"
    bad_extra_file.write_bytes(_dump_canonical_json_bytes(bad_extra_obj))
    p_extra = _run_recorder(proj, bad_extra_file)
    assert p_extra.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_payload_mismatch" in (p_extra.stderr + p_extra.stdout)


def test_recorder_rejects_report_projection_mismatch(tmp_path: Path) -> None:
    """Report must project verdict on line 1 and report_utf8 SHA must match report_sha256."""
    env = _build_test_environment(tmp_path)
    proj = env["proj"]

    bad_obj = dict(env["payload_obj"])
    bad_report = "# Bad Report Header\nclosure_verdict=receipt_closure_audited\n"
    bad_obj["report_utf8"] = bad_report
    bad_obj["report_sha256"] = _sha256_bytes(bad_report.encode("utf-8"))
    bad_file = tmp_path / "bad_proj.json"
    bad_file.write_bytes(_dump_canonical_json_bytes(bad_obj))

    p = _run_recorder(proj, bad_file)
    assert p.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_payload_mismatch" in (p.stderr + p.stdout)

    bad_obj2 = dict(env["payload_obj"])
    bad_report2 = "closure_verdict=receipt_closure_audited\nclosure_verdict=receipt_closure_incomplete\n"
    bad_obj2["report_utf8"] = bad_report2
    bad_obj2["report_sha256"] = _sha256_bytes(bad_report2.encode("utf-8"))
    bad_file2 = tmp_path / "bad_proj2.json"
    bad_file2.write_bytes(_dump_canonical_json_bytes(bad_obj2))

    p2 = _run_recorder(proj, bad_file2)
    assert p2.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_payload_mismatch" in (p2.stderr + p2.stdout)


def test_recorder_p0_02_strict_authority_identity_binding(tmp_path: Path) -> None:
    """P0-02: Recorder must strictly verify frozen Plan/Design SHAs, 15 approval lines, and lifecycle evidence fields."""
    env = _build_test_environment(tmp_path)
    proj = env["proj"]
    auth_dir = env["auth_dir"]

    # 1. Tamper recorder_implementation_plan_sha256 in user_audit_recording_approval.txt
    orig_app = (auth_dir / "user_audit_recording_approval.txt").read_bytes()
    bad_app_text = orig_app.decode("utf-8").replace(f"recorder_implementation_plan_sha256={DELTA_PLAN_SHA}", f"recorder_implementation_plan_sha256={'a' * 64}")
    bad_app_bytes = bad_app_text.encode("utf-8")
    (auth_dir / "user_audit_recording_approval.txt").write_bytes(bad_app_bytes)
    (auth_dir / "user_audit_recording_approval.txt.sha256").write_text(f"{_sha256_bytes(bad_app_bytes)}  user_audit_recording_approval.txt\n")

    # Update release seal for approval
    rel_obj = json.loads((auth_dir / "audit_recording_release.json").read_text())
    rel_obj["user_audit_recording_approval"]["sha256"] = _sha256_bytes(bad_app_bytes)
    bad_rel_bytes = _dump_canonical_json_bytes(rel_obj)
    (auth_dir / "audit_recording_release.json").write_bytes(bad_rel_bytes)
    (auth_dir / "audit_recording_release.json.sha256").write_text(f"{_sha256_bytes(bad_rel_bytes)}  audit_recording_release.json\n")

    # Recorder currently ignores this line and returns 0! It MUST reject!
    p = _run_recorder(proj, env["payload_file"])
    assert p.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_authority_mismatch" in (p.stderr + p.stdout)


def test_recorder_p0_01_rejects_s0_plus_t_s_and_symlink_final(tmp_path: Path) -> None:
    """P0-01: Recorder must reject S0 + T_S as S3, and reject report/sidecar symlinks."""
    env = _build_test_environment(tmp_path)
    proj = env["proj"]
    ev_dir = env["ev_dir"]

    # 1. Probe S0 + T_S: staging for sidecar exists while R does not exist -> must be S3
    staging_s_name = f".receipt_closure_audit_report.sha256.{env['payload_sha']}.staging"
    stg_s = ev_dir / staging_s_name
    expected_sidecar_bytes = f"{env['payload_obj']['report_sha256']}  receipt_closure_audit_report.md\n".encode("utf-8")
    stg_s.write_bytes(expected_sidecar_bytes)

    p_s0_ts = _run_recorder(proj, env["payload_file"])
    assert p_s0_ts.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_target_exists_mismatch" in (p_s0_ts.stderr + p_s0_ts.stdout)

    stg_s.unlink()

    # 2. Probe Symlink Final: replace receipt_closure_audit_report.md with a symlink to outside
    ext_file = tmp_path / "ext_report.md"
    ext_file.write_bytes(env["report_bytes"])
    report_target = ev_dir / "receipt_closure_audit_report.md"
    os.symlink(ext_file, report_target)

    p_sym = _run_recorder(proj, env["payload_file"])
    assert p_sym.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_symlink_or_escape" in (p_sym.stderr + p_sym.stdout)


def test_recorder_s0_to_s2_lifecycle_and_idempotency(tmp_path: Path) -> None:
    """Recorder must transition S0 -> S2 on first run, and remain idempotent S2 -> S2."""
    env = _build_test_environment(tmp_path)
    proj = env["proj"]
    ev_dir = env["ev_dir"]
    report_file = ev_dir / "receipt_closure_audit_report.md"
    sidecar_file = ev_dir / "receipt_closure_audit_report.md.sha256"

    # Pre-state: S0
    assert set(p.name for p in ev_dir.iterdir()) == {
        "producer_lifecycle_evidence.json",
        "producer_lifecycle_evidence.json.sha256",
    }

    # S0 -> S2
    p1 = _run_recorder(proj, env["payload_file"])
    assert p1.returncode == 0, f"Recorder failed: {p1.stderr}\n{p1.stdout}"
    assert report_file.exists()
    assert sidecar_file.exists()
    assert report_file.read_bytes() == env["report_bytes"]

    stat_r1 = report_file.stat()
    stat_s1 = sidecar_file.stat()

    # S2 -> S2 idempotent
    p2 = _run_recorder(proj, env["payload_file"])
    assert p2.returncode == 0, f"Idempotent run failed: {p2.stderr}\n{p2.stdout}"

    stat_r2 = report_file.stat()
    stat_s2 = sidecar_file.stat()
    assert stat_r1.st_ino == stat_r2.st_ino
    assert stat_r1.st_mtime_ns == stat_r2.st_mtime_ns
    assert stat_s1.st_ino == stat_s2.st_ino
    assert stat_s1.st_mtime_ns == stat_s2.st_mtime_ns


def test_recorder_p1_02_all_s4_and_s1_recoveries(tmp_path: Path) -> None:
    """P1-02: Test all 4 legal S4 combinations (S0+T_R, S1+T_R, S1+T_S, S2+T_S) and legal S1."""
    env = _build_test_environment(tmp_path)
    proj = env["proj"]
    ev_dir = env["ev_dir"]
    report_file = ev_dir / "receipt_closure_audit_report.md"
    sidecar_file = ev_dir / "receipt_closure_audit_report.md.sha256"

    stg_r_name = f".receipt_closure_audit_report.{env['payload_sha']}.staging"
    stg_s_name = f".receipt_closure_audit_report.sha256.{env['payload_sha']}.staging"
    stg_r = ev_dir / stg_r_name
    stg_s = ev_dir / stg_s_name
    sidecar_bytes = f"{env['payload_obj']['report_sha256']}  receipt_closure_audit_report.md\n".encode("utf-8")

    # Variant A: S0 + T_R -> cleans T_R, publishes R and S -> S2
    stg_r.write_bytes(env["report_bytes"])
    p_a = _run_recorder(proj, env["payload_file"])
    assert p_a.returncode == 0
    assert not stg_r.exists()
    assert report_file.exists()
    assert sidecar_file.exists()

    # Clean up for next variant
    report_file.unlink()
    sidecar_file.unlink()

    # Variant B: S1 (L + R) -> publishes S -> S2
    report_file.write_bytes(env["report_bytes"])
    p_b = _run_recorder(proj, env["payload_file"])
    assert p_b.returncode == 0
    assert sidecar_file.exists()

    sidecar_file.unlink()

    # Variant C: S1 + T_R -> cleans T_R, publishes S -> S2
    stg_r.write_bytes(env["report_bytes"])
    p_c = _run_recorder(proj, env["payload_file"])
    assert p_c.returncode == 0
    assert not stg_r.exists()
    assert sidecar_file.exists()

    sidecar_file.unlink()

    # Variant D: S1 + T_S -> cleans T_S, publishes S -> S2
    stg_s.write_bytes(sidecar_bytes)
    p_d = _run_recorder(proj, env["payload_file"])
    assert p_d.returncode == 0
    assert not stg_s.exists()
    assert sidecar_file.exists()

    # Variant E: S2 + T_S -> cleans T_S, retains S2
    stg_s.write_bytes(sidecar_bytes)
    p_e = _run_recorder(proj, env["payload_file"])
    assert p_e.returncode == 0
    assert not stg_s.exists()
    assert report_file.exists()
    assert sidecar_file.exists()


def test_recorder_p1_02_illegal_staging_mismatch(tmp_path: Path) -> None:
    """P1-02: Staging with mismatched payload hash or wrong bytes must fail as S3 without deletion."""
    env = _build_test_environment(tmp_path)
    proj = env["proj"]
    ev_dir = env["ev_dir"]

    # Wrong bytes in T_R
    stg_r_name = f".receipt_closure_audit_report.{env['payload_sha']}.staging"
    stg_r = ev_dir / stg_r_name
    stg_r.write_bytes(b"corrupted bytes\n")

    p = _run_recorder(proj, env["payload_file"])
    assert p.returncode != 0
    assert "STOP=stage1_5j_c_audit_recording_target_exists_mismatch" in (p.stderr + p.stdout)
    assert stg_r.exists()  # Not deleted!


def test_recorder_lock_contention(tmp_path: Path) -> None:
    """When evidence directory lock is held by another process, recorder must fail closed."""
    env = _build_test_environment(tmp_path)
    proj = env["proj"]
    ev_dir = env["ev_dir"]

    dfd = os.open(str(ev_dir), os.O_RDONLY)
    try:
        fcntl.flock(dfd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        p = _run_recorder(proj, env["payload_file"])
        assert p.returncode != 0
        assert "STOP=stage1_5j_c_audit_recording_lock_unavailable" in (p.stderr + p.stdout)
    finally:
        fcntl.flock(dfd, fcntl.LOCK_UN)
        os.close(dfd)


def test_recorder_p1_02_fsync_failure_injection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P1-02: Injected file and directory fsync failure must raise persistence_failure STOP."""
    from scripts.governance import record_stage1_5j_c_receipt_closure_audit as rec

    env = _build_test_environment(tmp_path)
    monkeypatch.setattr(rec, "__file__", str(env["proj"] / "scripts/governance/record_stage1_5j_c_receipt_closure_audit.py"))
    monkeypatch.chdir(env["proj"])
    monkeypatch.setattr(sys, "argv", ["record_stage1_5j_c_receipt_closure_audit.py", str(env["payload_file"])])

    def _failing_fsync(fd: int) -> None:
        raise OSError("Injected disk error")

    monkeypatch.setattr(os, "fsync", _failing_fsync)
    with pytest.raises(RuntimeError, match="STOP=stage1_5j_c_audit_recording_persistence_failure"):
        rec.main()


def test_recorder_p1_02_final_collision_rejection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P1-02: Target collision during os.link must fail closed with collision STOP."""
    from scripts.governance import record_stage1_5j_c_receipt_closure_audit as rec

    env = _build_test_environment(tmp_path)
    monkeypatch.setattr(rec, "__file__", str(env["proj"] / "scripts/governance/record_stage1_5j_c_receipt_closure_audit.py"))
    monkeypatch.chdir(env["proj"])
    monkeypatch.setattr(sys, "argv", ["record_stage1_5j_c_receipt_closure_audit.py", str(env["payload_file"])])

    def _colliding_link(src: str, dst: str) -> None:
        raise FileExistsError(f"File exists: {dst}")

    monkeypatch.setattr(os, "link", _colliding_link)
    with pytest.raises(RuntimeError, match="STOP=stage1_5j_c_audit_recording_target_exists_mismatch:collision"):
        rec.main()


def test_recorder_ast_isolation() -> None:
    """Recorder module body AST must not import forbidden modules."""
    assert RECORDER_SCRIPT.exists()

    source = RECORDER_SCRIPT.read_text()
    tree = ast.parse(source)

    forbidden = {
        "research",
        "scripts.external_signal_shadow",
        "verify_stage1_5j_c_receipt_schema",
        "zipfile",
        "csv",
        "urllib",
        "requests",
        "http",
        "socket",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    if alias.name == f or alias.name.startswith(f + "."):
                        pytest.fail(f"Forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod_name = node.module or ""
            for f in forbidden:
                if mod_name == f or mod_name.startswith(f + "."):
                    pytest.fail(f"Forbidden import from: {mod_name}")
